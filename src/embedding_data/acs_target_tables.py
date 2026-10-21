'''Assemble the fixed ACS products within one authenticated source scan lifetime.'''

import shutil
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from embedding_data import ipums_parity, target_io
from embedding_data.acs_mapping_io import safe_path
from embedding_data.acs_target_contract import (
    AUXILIARY_KEYS,
    AUXILIARY_SCHEMAS,
    CELL_KEY_COLUMNS,
    PRODUCTS,
    RESIDUAL_SCHEMA,
    STAT_KEY_COLUMNS,
    TARGET_TABLES,
    _validate_key_order,
    _validation_partitions,
    observed_counterpart,
    validate_cross_tables,
)
from embedding_data.acs_target_estimation import _aggregate_native_spilled, _spill_estimates
from embedding_data.acs_target_inputs import SelectedTargets
from embedding_data.acs_target_membership import family_rows
from embedding_data.acs_target_projection import _allocate_area_mix_spilled, canonical_rows
from embedding_data.acs_target_rules import read_rules
from embedding_data.acs_target_units import build_units
from embedding_data.acs_target_weights import weighted_source
from embedding_data.target_contract import TARGET_KEY_COLUMNS, TARGET_SCHEMA, write_targets

TABLES = (*TARGET_TABLES, *AUXILIARY_SCHEMAS)
_ASSEMBLY_ROW_GROUP_SIZE = 16384
_ASSEMBLY_PREFIXES = {
    **{name: ['source', 'family', 'unit_a_type', 'unit_a'] for name in TARGET_TABLES},
    'target_units': ['unit_type', 'unit'],
    'target_support': ['view', 'source', 'family', 'unit_a_type', 'unit_a'],
    'replicate_estimates': ['view', 'source', 'family', 'unit_a_type', 'unit_a'],
    'eligibility_diagnostics': ['source', 'profile', 'delivery_id', 'source_parquet_sha256',
                                'sample_id', 'component_year'],
    'allocation_residuals': ['source', 'family', 'workplace_unit_type', 'workplace_unit',
                             'code_unit_type', 'code_unit'],
}


@dataclass(frozen=True)
class _TableFragment:
    name: str
    path: Path
    schema: tuple
    rows: int


def _table_layout(name):
    if name in TARGET_TABLES:
        return TARGET_SCHEMA, TARGET_KEY_COLUMNS
    return AUXILIARY_SCHEMAS[name], AUXILIARY_KEYS[name]


def _sink_table_fragment(name, frame, destination):
    schema, keys = _table_layout(name)
    actual_schema = tuple(frame.collect_schema().items())
    if actual_schema != tuple(schema.items()):
        raise ValueError(name + ': fragment schema differs')
    safe_path(destination)
    with destination.open('xb') as output:
        frame.sort(keys, nulls_last=False).sink_parquet(
            output, row_group_size=_ASSEMBLY_ROW_GROUP_SIZE, statistics=True,
            maintain_order=True, engine='streaming')
    rows = pl.scan_parquet(destination).select(pl.len()).collect().item()
    return _TableFragment(name, destination, actual_schema, rows)


def _assemble_table_spilled(name, fragments, workspace):
    schema, keys = _table_layout(name)
    safe_path(workspace)
    directory = workspace / name
    safe_path(directory)
    directory.mkdir()
    try:
        for record in fragments:
            safe_path(record.path)
            if record.name != name or record.schema != tuple(schema.items()):
                raise ValueError(name + ': mismatched fragment descriptor')
        frames = [pl.scan_parquet(record.path, use_statistics=True) for record in fragments]
        source = pl.concat(frames) if frames else pl.LazyFrame(schema=schema)
        prefix = _ASSEMBLY_PREFIXES[name]
        registry = directory / 'prefixes.parquet'
        # Only actual aggregate prefixes are deduplicated; source rows stay untouched.
        with registry.open('xb') as output:
            source.select(prefix).unique().sort(prefix, nulls_last=False).sink_parquet(
                output, maintain_order=True, engine='streaming')
        paths = []
        for batch in pl.scan_parquet(registry).collect_batches(
            chunk_size=1024, maintain_order=True, lazy=True, engine='streaming'
        ):
            for values in batch.iter_rows():
                predicate = pl.all_horizontal([
                    pl.col(key).eq_missing(pl.lit(value, dtype=schema[key]))
                    for key, value in zip(prefix, values, strict=True)])
                path = directory / f'range-{len(paths):08d}.parquet'
                _sink_table_fragment(name, source.filter(predicate), path)
                paths.append(path)
        if not paths:
            path = directory / 'empty.parquet'
            _sink_table_fragment(name, pl.LazyFrame(schema=schema), path)
            paths.append(path)
        # Disjoint leading prefixes make explicit range concatenation globally ordered.
        return pl.concat([pl.scan_parquet(path) for path in paths])
    except BaseException:
        shutil.rmtree(directory)
        raise


def _spill_product_outputs(aggregates, residuals, workspace):
    _validate_aggregate_denominators(aggregates)
    directory = workspace / aggregates.product.product_id
    safe_path(directory)
    directory.mkdir()
    try:
        estimates = _spill_estimates(aggregates, directory)
        target = {
            'observed': 'targets_observed',
            'canonical': 'targets_canonical',
            'allocated_county': 'targets_allocated_area_mix',
            'allocated_msa': 'targets_allocated_area_mix',
        }[aggregates.product.view]
        records = []
        for name, frame in [
            (target, estimates['targets']),
            ('target_support', estimates['support']),
            ('replicate_estimates', estimates['replicates']),
            ('eligibility_diagnostics', aggregates.diagnostics),
            ('allocation_residuals', residuals),
        ]:
            records.append(_sink_table_fragment(name, frame, directory / (name + '.parquet')))
        # Every returned scan now reads its compact durable file, not estimator shards.
        shutil.rmtree(directory / ('estimates-' + aggregates.product.product_id))
        return records
    except BaseException:
        shutil.rmtree(directory)
        raise


def derive_tables(
    selected: SelectedTargets, scratch: Path
) -> dict[str, pl.DataFrame | pl.LazyFrame]:
    '''Finish one product's aggregate work before retaining only durable output scans.'''
    safe_path(scratch)
    directory = scratch / 'target-assembly'
    safe_path(directory)
    directory.mkdir()
    try:
        work, output, ranges = [directory / name for name in ('work', 'outputs', 'ranges')]
        for child in (work, output, ranges):
            child.mkdir()
        units = build_units(selected)
        rules = {profile: read_rules(source)
                 for profile, source in selected.upstream.sources.items()}
        nodes = {system: pl.read_parquet(selected.upstream.codes[system + '_nodes'])
                 for system in ('naics', 'soc')}
        factors = pl.read_parquet(selected.tables['puma_county_factors'])
        counties = pl.read_parquet(selected.upstream.geography['county_reference'])
        outputs = {name: [] for name in TABLES}
        unit_record = _sink_table_fragment('target_units', units.lazy(),
                                           output / 'target_units.parquet')
        with weighted_source(selected, scratch) as source:
            for product in PRODUCTS:
                if product.view != 'observed':
                    continue
                rows = family_rows(source.frame, product, rules['acs/core'], units)
                product_work = work / product.product_id
                safe_path(product_work)
                product_work.mkdir()
                try:
                    native = _aggregate_native_spilled(rows, product_work)
                    for record in _spill_product_outputs(
                        native, pl.LazyFrame(schema=RESIDUAL_SCHEMA), output
                    ):
                        outputs[record.name].append(record)
                    for projected in PRODUCTS:
                        if (projected.view == 'observed'
                            or observed_counterpart(projected) != product):
                            continue
                        projected_work = product_work / projected.product_id
                        safe_path(projected_work)
                        projected_work.mkdir()
                        try:
                            if projected.view == 'canonical':
                                aggregates = _aggregate_native_spilled(
                                    canonical_rows(rows, nodes), projected_work)
                                residuals = pl.LazyFrame(schema=RESIDUAL_SCHEMA)
                            else:
                                aggregates, residuals = _allocate_area_mix_spilled(
                                    native, factors, counties, projected, projected_work,
                                    native_wide_root=(
                                        product_work / ('native-' + product.product_id)))
                            for record in _spill_product_outputs(aggregates, residuals, output):
                                outputs[record.name].append(record)
                        finally:
                            shutil.rmtree(projected_work)
                finally:
                    shutil.rmtree(product_work)
        tables = {'target_units': pl.scan_parquet(unit_record.path)}
        for name in TABLES:
            if name != 'target_units':
                tables[name] = _assemble_table_spilled(name, outputs[name], ranges)
        return {name: tables[name] for name in TABLES}
    except BaseException:
        shutil.rmtree(directory)
        raise


def write_tables(staging: Path, tables: dict[str, pl.DataFrame | pl.LazyFrame]) -> dict:
    '''Validate before writing and again on the exact serialized ordered tables.'''
    validate_complete_tables(tables)
    for name in TABLES:
        destination = staging / (name + '.parquet')
        safe_path(destination)
        if destination.exists():
            raise FileExistsError(destination)
        if name in TARGET_TABLES:
            write_targets(tables[name], destination)
        else:
            frame = tables[name]
            if isinstance(frame, pl.DataFrame):
                frame = frame.lazy()
            with destination.open('xb') as output:
                frame.sink_parquet(output, maintain_order=True, engine='streaming')
    serialized = {name: pl.scan_parquet(staging / (name + '.parquet')) for name in TABLES}
    validate_complete_tables(serialized)
    for name in TABLES:
        expected = tables[name]
        if isinstance(expected, pl.DataFrame):
            expected = expected.lazy()
        parity = ipums_parity.compare_ordered(expected, serialized[name])
        if (not parity['schema_equal'] or not parity['values_equal']
                or parity['expected_rows'] != parity['actual_rows']):
            raise ValueError(name + ': serialized table differs')
    return {name: target_io.file_record(staging / (name + '.parquet')) for name in TABLES}


def validate_complete_tables(tables):
    '''Add whole-bundle annual/measure and denominator closure to shared schemas.'''
    validate_cross_tables(tables, PRODUCTS)
    support = tables['target_support']
    replicate = tables['replicate_estimates']
    support = support.lazy() if isinstance(support, pl.DataFrame) else support
    replicate = replicate.lazy() if isinstance(replicate, pl.DataFrame) else replicate
    native_views = pl.col('view').is_in(['observed', 'canonical'])
    native_scales = (
        _denominator_scale(support.filter(native_views & pl.col('record_kind').eq('cell')),
                           'cell_weight_sum_exact', 'denominator_weight_sum_exact'),
        _denominator_scale(replicate.filter(native_views),
                           'numerator_sum_exact', 'denominator_sum_exact'))
    for support_part, replicate_part in _validation_partitions([support, replicate]):
        _validate_complete_partition(support_part, replicate_part, native_scales)
    for name in TARGET_TABLES:
        _validate_key_order(tables[name], TARGET_KEY_COLUMNS, 'target ordered key sort differs')


def _validate_complete_partition(support, replicate, native_scales):
    '''Reconcile complete-a denominators without collecting whole published tables.'''
    cells = support.filter(pl.col('record_kind').eq('cell'))
    annual = cells.group_by(STAT_KEY_COLUMNS).agg(
        pl.col('component_year').n_unique().alias('_components'), pl.col('pool_divisor').first()
    )
    if annual.filter(pl.col('_components').ne(pl.col('pool_divisor') + 1)).select(
            pl.len()).collect().item():
        raise ValueError('complete annual support components required')
    paired = cells.group_by(*CELL_KEY_COLUMNS, 'component_year').agg(
        pl.col('measure').n_unique().alias('_measures')
    )
    if paired.filter(pl.col('_measures').ne(2)).select(pl.len()).collect().item():
        raise ValueError('both measures require matching annual/pooled support')
    denominator_keys = [name for name in STAT_KEY_COLUMNS if name not in {'unit_b', 'unit_b_type'}]
    for column, denominator in [
        ('n_unweighted', 'denominator_n_unweighted'),
        ('fractional_support_mass', 'denominator_fractional_support_mass'),
    ]:
        groups = cells.group_by(*denominator_keys, 'component_year').agg(
            pl.col(column).sum().alias('_sum'), pl.col(denominator).first().alias('_expected')
        )
        error = (pl.col('_sum') - pl.col('_expected')).abs()
        tolerance = (
            pl.lit(0) if column == 'n_unweighted' else 1e-8 + 1e-12 * pl.col('_expected').abs()
        )
        if groups.filter(error > tolerance).select(pl.len()).collect().item():
            raise ValueError('support denominator does not close')
    for native in (True, False):
        native_views = pl.col('view').is_in(['observed', 'canonical'])
        cell_subset = cells.filter(native_views if native else ~native_views)
        replicate_subset = replicate.filter(native_views if native else ~native_views)
        _check_denominator_sums(cell_subset, [*denominator_keys, 'component_year'],
            'cell_weight_sum_exact' if native else 'cell_mass',
            'denominator_weight_sum_exact' if native else 'denominator_mass', native=native,
            scale=native_scales[0] if native else None)
        _check_denominator_sums(replicate_subset, [*denominator_keys, 'replicate'],
            'numerator_sum_exact' if native else 'numerator',
            'denominator_sum_exact' if native else 'denominator', native=native,
            scale=native_scales[1] if native else None)


def _denominator_scale(lf, numerator, denominator):
    return lf.select(pl.max_horizontal([
        pl.col(name).str.split('.').list.get(1, null_on_oob=True).str.len_chars()
        for name in (numerator, denominator)]).max()).collect().item() or 0


def _check_denominator_sums(frame, keys, numerator, denominator, *, native, scale=None):
    lf = frame.lazy() if isinstance(frame, pl.DataFrame) else frame
    if native:
        scale = _denominator_scale(lf, numerator, denominator) if scale is None else scale
        dtype = pl.Decimal(38, scale)
        groups = lf.group_by(keys).agg(
            pl.col(numerator).cast(dtype).sum().alias('_sum'),
            pl.col(denominator).cast(dtype).first().alias('_expected'),
            pl.col(denominator).n_unique().alias('_versions'))
        invalid = pl.col('_sum').ne(pl.col('_expected'))
    else:
        # The same typed code order used by allocation fixes Float64 reduction order.
        ordered = lf.sort([*keys, 'unit_b_type', 'unit_b']).with_columns(
            pl.col(numerator).cum_sum().over(keys, order_by=['unit_b_type', 'unit_b'])
            .alias('_cumulative'))
        groups = ordered.group_by(keys).agg(pl.col('_cumulative').last().alias('_sum'),
            pl.col(denominator).first().alias('_expected'),
            pl.col(denominator).n_unique().alias('_versions'))
        invalid = (pl.col('_sum') - pl.col('_expected')).abs().gt(
            1e-8 + 1e-12 * pl.col('_expected').abs())
    invalid = invalid | pl.col('_expected').is_null() | pl.col('_versions').ne(1)
    if groups.select(invalid.any()).collect().item():
        raise ValueError('identified cell sums differ from denominator')


def _validate_aggregate_denominators(aggregates):
    keys = ['unit_a_type', 'unit_a', 'component_year', 'replicate']
    native = aggregates.product.view in {'observed', 'canonical'}
    column = 'sum_exact' if native else 'mass'
    denominators = aggregates.denominators.select(*keys, pl.col(column).alias('_denominator'))
    joined = aggregates.cells.join(denominators, on=keys, how='left', validate='m:1')
    scale = _denominator_scale(joined, column, '_denominator') if native else None
    for (part,) in _validation_partitions([joined], ['unit_a_type', 'unit_a']):
        _check_denominator_sums(part, keys, column, '_denominator', native=native, scale=scale)
