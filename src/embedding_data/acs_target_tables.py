'''Assemble the fixed ACS products within one authenticated source scan lifetime.'''

from pathlib import Path

import polars as pl

from embedding_data import target_io
from embedding_data.acs_target_contract import (
    AUXILIARY_KEYS,
    AUXILIARY_SCHEMAS,
    CELL_KEY_COLUMNS,
    PRODUCTS,
    RESIDUAL_SCHEMA,
    STAT_KEY_COLUMNS,
    TARGET_TABLES,
    observed_counterpart,
    validate_cross_tables,
)
from embedding_data.acs_target_estimation import aggregate_native, estimate
from embedding_data.acs_target_inputs import SelectedTargets
from embedding_data.acs_target_membership import family_rows
from embedding_data.acs_target_projection import allocate_area_mix, canonical_rows
from embedding_data.acs_target_rules import read_rules
from embedding_data.acs_target_units import build_units
from embedding_data.acs_target_weights import weighted_source
from embedding_data.target_contract import TARGET_KEY_COLUMNS, TARGET_SCHEMA, write_targets

TABLES = (*TARGET_TABLES, *AUXILIARY_SCHEMAS)


def derive_tables(
    selected: SelectedTargets, scratch: Path
) -> dict[str, pl.DataFrame | pl.LazyFrame]:
    '''Materialize bounded native aggregates before releasing the exact-weight scan.'''
    units = build_units(selected)
    rules = {profile: read_rules(source) for profile, source in selected.upstream.sources.items()}
    nodes = {
        system: pl.read_parquet(selected.upstream.codes[system + '_nodes'])
        for system in ('naics', 'soc')
    }
    factors = pl.read_parquet(selected.tables['puma_county_factors'])
    counties = pl.read_parquet(selected.upstream.geography['county_reference'])
    outputs = {name: [] for name in TABLES if name != 'target_units'}
    with weighted_source(selected, scratch) as source:
        for product in PRODUCTS:
            if product.view != 'observed':
                continue
            rows = family_rows(source.frame, product, rules['acs/core'], units)
            native = aggregate_native(rows)
            derived = [(native, pl.DataFrame(schema=RESIDUAL_SCHEMA).lazy())]
            counterparts = [
                p for p in PRODUCTS if p.view != 'observed' and observed_counterpart(p) == product
            ]
            for projected in counterparts:
                if projected.view == 'canonical':
                    derived.append(
                        (
                            aggregate_native(canonical_rows(rows, nodes)),
                            pl.DataFrame(schema=RESIDUAL_SCHEMA).lazy(),
                        )
                    )
                else:
                    derived.append(allocate_area_mix(native, factors, counties, projected))
            for aggregates, residuals in derived:
                _validate_aggregate_denominators(aggregates)
                estimates = estimate(aggregates)
                target = {
                    'observed': 'targets_observed',
                    'canonical': 'targets_canonical',
                    'allocated_county': 'targets_allocated_area_mix',
                    'allocated_msa': 'targets_allocated_area_mix',
                }[aggregates.product.view]
                # Estimator plans are lazy; only aggregate outputs cross the source lifetime.
                frames = pl.collect_all(
                    [
                        estimates['targets'],
                        estimates['support'],
                        estimates['replicates'],
                        aggregates.diagnostics,
                        residuals,
                    ]
                )
                for name, frame in zip(
                    (
                        target,
                        'target_support',
                        'replicate_estimates',
                        'eligibility_diagnostics',
                        'allocation_residuals',
                    ),
                    frames,
                    strict=True,
                ):
                    outputs[name].append(frame)
    tables = {'target_units': units}
    for name, frames in outputs.items():
        schema = TARGET_SCHEMA if name in TARGET_TABLES else AUXILIARY_SCHEMAS[name]
        keys = TARGET_KEY_COLUMNS if name in TARGET_TABLES else AUXILIARY_KEYS[name]
        tables[name] = (pl.concat(frames) if frames else pl.DataFrame(schema=schema)).sort(
            keys, nulls_last=False
        )
    return {name: tables[name] for name in TABLES}


def write_tables(staging: Path, tables: dict[str, pl.DataFrame | pl.LazyFrame]) -> dict:
    '''Validate before writing and again on the exact serialized ordered tables.'''
    from embedding_data.acs_mapping_io import safe_path

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
            frame.sink_parquet(destination)
    serialized = {name: pl.read_parquet(staging / (name + '.parquet')) for name in TABLES}
    validate_complete_tables(serialized)
    for name in TABLES:
        expected = tables[name]
        if isinstance(expected, pl.LazyFrame):
            expected = expected.collect()
        if not serialized[name].equals(expected):
            raise ValueError(name + ': serialized table differs')
    return {name: target_io.file_record(staging / (name + '.parquet')) for name in TABLES}


def validate_complete_tables(tables):
    '''Add whole-bundle annual/measure and denominator closure to shared schemas.'''
    validate_cross_tables(tables, PRODUCTS)
    support = tables['target_support']
    if isinstance(support, pl.LazyFrame):
        support = support.collect()
    cells = support.filter(pl.col('record_kind').eq('cell'))
    annual = cells.group_by(STAT_KEY_COLUMNS).agg(
        pl.col('component_year').n_unique().alias('_components'), pl.col('pool_divisor').first()
    )
    if annual.filter(pl.col('_components').ne(pl.col('pool_divisor') + 1)).height:
        raise ValueError('complete annual support components required')
    paired = cells.group_by(*CELL_KEY_COLUMNS, 'component_year').agg(
        pl.col('measure').n_unique().alias('_measures')
    )
    if paired.filter(pl.col('_measures').ne(2)).height:
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
        if groups.filter(error > tolerance).height:
            raise ValueError('support denominator does not close')
    replicate = tables['replicate_estimates']
    if isinstance(replicate, pl.LazyFrame):
        replicate = replicate.collect()
    for native in (True, False):
        native_views = pl.col('view').is_in(['observed', 'canonical'])
        cell_subset = cells.filter(native_views if native else ~native_views)
        replicate_subset = replicate.filter(native_views if native else ~native_views)
        _check_denominator_sums(cell_subset, [*denominator_keys, 'component_year'],
            'cell_weight_sum_exact' if native else 'cell_mass',
            'denominator_weight_sum_exact' if native else 'denominator_mass', native=native)
        _check_denominator_sums(replicate_subset, [*denominator_keys, 'replicate'],
            'numerator_sum_exact' if native else 'numerator',
            'denominator_sum_exact' if native else 'denominator', native=native)
    for name in TARGET_TABLES:
        frame = tables[name]
        if isinstance(frame, pl.LazyFrame):
            frame = frame.collect()
        if not frame.equals(frame.sort(TARGET_KEY_COLUMNS, nulls_last=False)):
            raise ValueError('target ordered key sort differs')


def _check_denominator_sums(frame, keys, numerator, denominator, *, native):
    lf = frame.lazy() if isinstance(frame, pl.DataFrame) else frame
    if native:
        scale = lf.select(pl.max_horizontal([
            pl.col(name).str.split('.').list.get(1, null_on_oob=True).str.len_chars()
            for name in (numerator, denominator)]).max()).collect().item() or 0
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
    _check_denominator_sums(joined, keys, column, '_denominator', native=native)
