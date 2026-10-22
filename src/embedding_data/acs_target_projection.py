'''Supported canonical membership and deterministic workplace county/MSA allocation.'''

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from embedding_data.acs_mapping_contract import factor_key
from embedding_data.acs_mapping_io import safe_path
from embedding_data.acs_target_contract import (
    AUXILIARY_KEYS,
    PRODUCTS,
    RESIDUAL_SCHEMA,
    SELECTED_NODE_FRAMES,
    Product,
    observed_counterpart,
)
from embedding_data.acs_target_estimation import (
    DENOMINATOR_KEYS,
    PAIR_KEYS,
    AggregateSet,
    _native_wide_schema,
    _OrderedAggregateReader,
    _spill_native_long,
)
from embedding_data.acs_target_membership import FAMILY_INPUTS, FamilyRows, _diagnostic
from embedding_data.acs_target_weights import WEIGHT_NAMES
from embedding_data.ipums_parity import compare_ordered

COMPONENT_KEYS = ['component_year', 'replicate']
ALLOCATION_FLAGS = [
    'flag_geographic_allocation', 'allocation_conditional_sampling_se',
    'allocation_error_unquantified', 'mapping_uncertainty_unquantified',
    'population2020', 'puma2020', 'county_composition2022', 'county_inventory2025',
    'msa_delineation_July_2023',
]
COVERAGE_COLUMN = '_canonical_native_coverage'


def _product_diagnostics(frame, product):
    return frame.with_columns(
        pl.lit(getattr(product, name)).alias(name) for name in
        ('family', 'dimension', 'base_universe', 'evidence_policy', 'view', 'product_id'))


def _supported_members(frame, dimension, table):
    kind = {'industry': 'naics_national_industry', 'occupation': 'soc_detailed'}[dimension]
    system, vintage, level = SELECTED_NODE_FRAMES[kind]
    if table['node_id'].n_unique() != table.height:
        raise ValueError('duplicate selected node identity')
    supported = table.filter((pl.col('system') == system) & (pl.col('vintage') == vintage)
                             & (pl.col('level') == level)).select(
        pl.col('node_id').alias(dimension + '_canonical_scalar_node_id'))
    return frame.join(supported.lazy(), on=dimension + '_canonical_scalar_node_id',
                      how='semi', maintain_order='left')


def _coverage_baselines(frame, product):
    annual = frame.group_by(*DENOMINATOR_KEYS, 'YEAR').agg(
        pl.len().cast(pl.UInt64).alias('native_coverage_n'),
        pl.col('PERWT').sum().cast(pl.Float64).alias('native_coverage_mass'))\
        .rename({'YEAR': 'component_year'})
    pooled = frame.group_by(DENOMINATOR_KEYS).agg(
        pl.len().cast(pl.UInt64).alias('native_coverage_n'),
        pl.col('PERWT').sum().cast(pl.Float64).alias('native_coverage_mass'))\
        .with_columns(pl.lit(0, dtype=pl.Int64).alias('component_year'))
    grid = frame.select(DENOMINATOR_KEYS).unique().join(
        pl.LazyFrame({'component_year': [0, *product.years]}), how='cross')
    baseline = grid.join(pl.concat([annual, pooled], how='diagonal'),
        on=[*DENOMINATOR_KEYS, 'component_year'], how='left', validate='1:1').with_columns(
            pl.col('native_coverage_n').fill_null(0),
            pl.col('native_coverage_mass').fill_null(0.))
    return baseline.sort([*DENOMINATOR_KEYS, 'component_year']).group_by(DENOMINATOR_KEYS).agg(
        pl.struct('component_year', 'native_coverage_n', 'native_coverage_mass')
            .alias(COVERAGE_COLUMN))


def canonical_rows(rows: FamilyRows, nodes: dict[str, pl.DataFrame]) -> FamilyRows:
    '''Restrict used dimensions to authenticated supported scalars before reaggregation.'''
    if rows.product.view != 'observed' or rows.product.family not in {
            'staffing_pattern', 'area_mix'}:
        raise ValueError('canonical projection requires observed staffing or area mixes')
    observed = observed_counterpart(rows.product)
    product = next(p for p in PRODUCTS if p.view == 'canonical'
                   and observed_counterpart(p) == observed)
    dimensions, _ = FAMILY_INPUTS[(product.family, product.dimension)]
    frame = rows.members
    if product.family == 'staffing_pattern':
        baseline = _supported_members(frame, 'industry', nodes['naics']).with_columns(
            pl.lit('naics_national_industry').alias('unit_a_type'),
            pl.col('industry_canonical_scalar_node_id').alias('unit_a'))
    else:
        baseline = frame
    coverage = _coverage_baselines(baseline, product)
    for dimension in dimensions:
        frame = _supported_members(frame, dimension, nodes[
            'naics' if dimension == 'industry' else 'soc'])
        if product.evidence_policy == 'strict':
            schema = frame.collect_schema()
            prohibited = [dimension + '_flag_vintage_crosswalk',
                          dimension + '_source_allocated',
                          'flag_source_' + dimension + '_recoded']
            frame = frame.filter(~pl.any_horizontal(
                pl.col(name).fill_null(False) for name in prohibited if name in schema))
        side = 'a' if product.family == 'staffing_pattern' and dimension == 'industry' else 'b'
        frame = frame.with_columns(
            pl.lit('naics_national_industry' if dimension == 'industry' else 'soc_detailed')
                .alias('unit_' + side + '_type'),
            pl.col(dimension + '_canonical_scalar_node_id').alias('unit_' + side))
    identity = ['source_parquet_sha256', 'source_row']
    lost = rows.members.join(frame.select(identity), on=identity, how='anti')
    diagnostics = [_product_diagnostics(rows.diagnostics, product),
        _diagnostic(lost, product, partition='coverage',
                    reason=pl.lit('canonical_unsupported_or_policy_excluded'))]
    # Denominator losses retain a category-level key only in aggregate diagnostic fields.
    denominator_lost = baseline.join(frame.select(identity), on=identity, how='anti')\
        .with_columns(pl.col('unit_a').alias('_canonical_denominator'),
                      pl.lit(None, dtype=pl.String).alias('_evidence__canonical_denominator'))
    diagnostics.append(_diagnostic(denominator_lost, product, partition='coverage',
        reason=pl.lit('canonical_denominator_loss'), variable='_canonical_denominator'))
    members = frame.join(coverage, on=DENOMINATOR_KEYS, how='left', validate='m:1',
                         maintain_order='left')
    return FamilyRows(members, pl.concat(diagnostics).sort(
        AUXILIARY_KEYS['eligibility_diagnostics'], nulls_last=False), product)


def _require_clean(frame, expression, message):
    if frame.select(expression.any()).collect().item():
        raise ValueError(message)


def _allocation_relations(factors, counties):
    required = {'factor_key', 'area_type', 'state_fips', 'area_code', 'county_geoid',
                'county_node_id', 'factor'}
    if not required.issubset(factors.columns):
        raise ValueError('county factors required; residence MSA factors are unsupported')
    factors = factors.filter(pl.col('area_type') == 'work_migration')
    if factors.is_empty():
        raise ValueError('work/migration county factors required')
    if counties['county_id'].n_unique() != counties.height:
        raise ValueError('duplicate county membership')
    for row in factors.select('factor_key', 'area_type', 'state_fips', 'area_code').unique()\
            .iter_rows(named=True):
        if row['factor_key'] != factor_key(row['area_type'], row['state_fips'], row['area_code']):
            raise ValueError('invalid workplace factor key')
    if factors.select(pl.struct('factor_key', 'county_node_id').is_duplicated().any()).item():
        raise ValueError('duplicate county factor relationship')
    if factors.filter(pl.col('factor').is_null() | ~pl.col('factor').is_finite()
                      | pl.col('factor').lt(0) | pl.col('factor').gt(1)).height:
        raise ValueError('invalid county factor')
    sums = factors.group_by('factor_key').agg(pl.col('factor').sum())
    if sums.filter((pl.col('factor') - 1.).abs() > 1e-12).height:
        raise ValueError('missing positive-factor coverage')
    relations = factors.join(counties, left_on='county_node_id', right_on='county_id',
                             how='left', validate='m:1', suffix='_reference')
    if relations.filter(pl.col('county_geoid_reference').is_null()
        | pl.col('county_geoid').ne(pl.col('county_geoid_reference'))
        | pl.col('county_node_id').ne(pl.concat_str(
            pl.lit('geography:2025:county:'), pl.col('county_geoid')))).height:
        raise ValueError('unknown county or contradictory selected membership')
    invalid_cbsa = ((pl.col('cbsa_type').is_not_null() & (
        ~pl.col('cbsa_type').is_in(['metropolitan', 'micropolitan'])
        | pl.col('cbsa_id').ne(pl.concat_str(pl.lit('geography:2023:cbsa:'),
                                            pl.col('cbsa_code'))).fill_null(True)
        | pl.col('cbsa_vintage').ne(2023).fill_null(True)))
        | (pl.col('cbsa_type').is_null() & pl.col('cbsa_id').is_not_null()))
    if relations.filter(invalid_cbsa).height:
        raise ValueError('unknown CBSA or untyped county membership')
    return relations.with_columns(pl.concat_str(pl.lit('geography:2020:work_migration_puma:'),
        pl.col('state_fips'), pl.col('area_code')).alias('origin_workplace_unit')).lazy()


def _ordered_reduce(frame, keys, order, values):
    ordered = frame.sort([*keys, *order])
    return ordered.with_columns(
        pl.col(name).cum_sum().over(keys, order_by=order).alias(name) for name in values)\
        .unique(subset=keys, keep='last', maintain_order=True)


def _destination_aggregates(contributions, input_support=None):
    keys = [*PAIR_KEYS, *COMPONENT_KEYS]
    order = ['origin_workplace_unit', 'county_node_id']
    masses = _ordered_reduce(contributions, keys, order, ['mass', 'fractional_support_mass'])
    support = contributions if input_support is None else input_support
    counts = support.unique(subset=[*keys, 'origin_workplace_unit']).group_by(keys).agg(
        pl.col('n_unweighted').sum())
    flags = support.group_by(keys).agg(pl.col('flags').list.explode(
        keep_nulls=False, empty_as_null=False).unique().sort())
    counts = counts.join(flags, on=keys, validate='1:1')
    cells = masses.select(*keys, 'mass', 'fractional_support_mass').join(
        counts, on=keys, validate='1:1').with_columns(
            pl.lit(None, dtype=pl.String).alias('sum_exact'))
    denominator_keys = [*DENOMINATOR_KEYS, *COMPONENT_KEYS]
    denominators = _ordered_reduce(cells, denominator_keys,
        ['unit_b_type', 'unit_b'], ['mass', 'fractional_support_mass', 'n_unweighted'])
    flags = cells.group_by(denominator_keys).agg(pl.col('flags').list.explode(
        keep_nulls=False, empty_as_null=False).unique().sort())
    return cells, denominators.select(*denominator_keys, 'mass', 'fractional_support_mass',
        'n_unweighted', 'sum_exact').join(flags, on=denominator_keys, validate='1:1')


def _check_conservation(expected, actual, keys):
    compared = expected.select(*keys, pl.col('mass').alias('_expected')).join(
        actual.select(*keys, pl.col('mass').alias('_actual')), on=keys, how='full',
        coalesce=True, validate='1:1')
    _require_clean(compared, pl.col('_expected').is_null() | pl.col('_actual').is_null()
        | ~pl.col('_expected').is_finite() | ~pl.col('_actual').is_finite()
        | ((pl.col('_actual') - pl.col('_expected')).abs()
           > 1e-8 + 1e-12 * pl.col('_expected').abs()), 'allocation mass conservation failed')


def _residuals(contributions, product):
    keys = ['origin_workplace_unit', 'unit_b_type', 'unit_b', *COMPONENT_KEYS, 'residual_type']
    reduced = _ordered_reduce(contributions, keys, ['county_node_id'],
                              ['mass', 'fractional_support_mass'])
    frame = reduced.with_columns(
        pl.lit('acs').alias('source'), pl.lit(product.family).alias('family'),
        pl.lit('work_migration_puma').alias('workplace_unit_type'),
        pl.col('origin_workplace_unit').alias('workplace_unit'),
        pl.col('unit_b_type').alias('code_unit_type'), pl.col('unit_b').alias('code_unit'),
        pl.lit(product.sample_set).alias('sample_set'), pl.lit(product.vintage).alias('vintage'),
        pl.lit(product.base_universe + ':' + product.evidence_policy).alias('universe'),
        pl.lit(product.product_id).alias('product_id'),
        pl.lit(product.pool_divisor, dtype=pl.UInt8).alias('pool_divisor'),
        (pl.col('mass') / product.pool_divisor).alias('weighted_mass'),
        pl.col('n_unweighted').alias('n_input_support'))
    return frame.select(pl.col(name).cast(dtype) for name, dtype in RESIDUAL_SCHEMA.items())\
        .sort(list(RESIDUAL_SCHEMA)[:13])


def allocate_area_mix(
    native: AggregateSet, county_factors: pl.DataFrame, counties: pl.DataFrame, product: Product,
) -> tuple[AggregateSet, pl.LazyFrame]:
    '''Allocate raw workplace masses; counts and fractional support remain distinct.'''
    if (product.family != 'area_mix' or product.view not in {'allocated_county', 'allocated_msa'}
        or native.product.view != 'observed'
        or observed_counterpart(product) != native.product):
        raise ValueError('only corresponding observed workplace area mixes can be allocated')
    relations = _allocation_relations(county_factors, counties)
    source = native.cells.rename({'unit_a': 'origin_workplace_unit'})
    _require_clean(source, pl.col('unit_a_type').ne('work_migration_puma'),
                   'work/migration workplace geography required')
    missing = source.select('origin_workplace_unit').unique().join(
        relations.select('origin_workplace_unit').unique(), on='origin_workplace_unit', how='anti')
    if missing.select(pl.len()).collect().item():
        raise ValueError('missing positive-factor workplace coverage')
    contributions = source.join(relations, on='origin_workplace_unit', how='inner').filter(
        pl.col('factor') > 0).with_columns(
            (pl.col('sum_exact').cast(pl.Float64) * pl.col('factor')).alias('mass'),
            (pl.col('n_unweighted') * pl.col('factor')).alias('fractional_support_mass'),
            pl.concat_list('flags', pl.lit(ALLOCATION_FLAGS),
                pl.when(pl.col('factor') < 1).then(pl.lit('flag_fractional_split'))
                  .otherwise(None)).list.drop_nulls().list.unique().list.sort()
                .alias('flags'),
            pl.col('county_node_id').alias('unit_a'), pl.lit('county').alias('unit_a_type'))
    native_keys = ['origin_workplace_unit', 'unit_b_type', 'unit_b', *COMPONENT_KEYS]
    source_mass = source.with_columns(pl.col('sum_exact').cast(pl.Float64).alias('mass'))
    county_mass = _ordered_reduce(contributions, native_keys, ['county_node_id'], ['mass'])
    _check_conservation(source_mass, county_mass, native_keys)
    county_cells, county_denominators = _destination_aggregates(contributions)
    diagnostics = _product_diagnostics(native.diagnostics, product)
    empty = pl.DataFrame(schema=RESIDUAL_SCHEMA).lazy()
    if product.view == 'allocated_county':
        return AggregateSet(county_cells, county_denominators, diagnostics, product), empty
    metro = contributions.filter(pl.col('cbsa_type') == 'metropolitan').with_columns(
        pl.col('cbsa_id').alias('unit_a'), pl.lit('cbsa').alias('unit_a_type'))
    # County mass is reduced first; MSA input counts still deduplicate native workplaces.
    metro_counties = county_cells.rename({'unit_a': 'county_node_id'}).join(
        counties.select(pl.col('county_id').alias('county_node_id'), 'cbsa_id', 'cbsa_type')
            .lazy(), on='county_node_id', how='left', validate='m:1').filter(
                pl.col('cbsa_type') == 'metropolitan').with_columns(
                    pl.col('cbsa_id').alias('unit_a'), pl.lit('cbsa').alias('unit_a_type'),
                    pl.col('county_node_id').alias('origin_workplace_unit'))
    cells, denominators = _destination_aggregates(metro_counties, metro)
    residual = contributions.filter(pl.col('cbsa_type').ne('metropolitan').fill_null(True))\
        .with_columns(pl.when(pl.col('cbsa_type') == 'micropolitan').then(
            pl.lit('micropolitan')).otherwise(pl.lit('no_cbsa')).alias('residual_type'))
    totals_keys = ['unit_b_type', 'unit_b', *COMPONENT_KEYS]
    expected = _ordered_reduce(county_cells, totals_keys, ['unit_a'], ['mass'])
    residual_total = _residuals(residual, product)
    actual = pl.concat([cells.select(*totals_keys, 'unit_a', 'mass'),
        residual_total.select(pl.col('code_unit_type').alias('unit_b_type'),
            pl.col('code_unit').alias('unit_b'), *COMPONENT_KEYS,
            pl.concat_str('workplace_unit', 'residual_type').alias('unit_a'),
            (pl.col('weighted_mass') * product.pool_divisor).alias('mass'))])
    actual = _ordered_reduce(actual, totals_keys, ['unit_a'], ['mass'])
    _check_conservation(expected, actual, totals_keys)
    return AggregateSet(cells, denominators, diagnostics, product), residual_total


_MASS_COLUMNS = [f'_mass_{r}' for r in range(81)]


def _sink_projection(frame, directory, label):
    path = directory / (label + '.parquet')
    safe_path(path)
    with path.open('xb') as stream:
        frame.sink_parquet(stream)
    return pl.scan_parquet(path)


def _projection_native_artifacts(native, root, directory, batch_size):
    root = Path(root)
    safe_path(root)
    if not root.is_dir() or root.name != 'native-' + native.product.product_id:
        raise ValueError('native wide root must be the exact completed native product directory')
    binding = directory / 'binding'
    binding.mkdir()
    frames = {}
    common_scale = None
    for label, keys in [('cells', PAIR_KEYS), ('denominators', DENOMINATOR_KEYS)]:
        parts = []
        for component in ('annual', 'pooled'):
            path = root / f'{label}-{component}.parquet'
            safe_path(path)
            if not path.is_file():
                raise ValueError('missing native wide aggregate file')
            frame = pl.scan_parquet(path)
            schema = frame.collect_schema()
            weight = schema.get('PERWT')
            if not isinstance(weight, pl.Decimal) or weight.precision != 38:
                raise ValueError('invalid native wide Decimal schema')
            if common_scale is None:
                common_scale = weight.scale
            expected = _native_wide_schema(keys, common_scale)
            if list(schema.items()) != list(expected.items()):
                raise ValueError('native wide ordered schema or scale mismatch')
            grain = [*keys, 'component_year']
            _require_clean(frame, pl.any_horizontal(pl.col(k).is_null() for k in grain)
                | pl.struct(grain).is_duplicated()
                | ~pl.col('component_year').is_in(native.product.years if component == 'annual'
                                                  else [0]), 'invalid native wide grain')
            parts.append(frame)
        wide = pl.concat(parts)
        reconstructed = _spill_native_long(wide, keys, native.product, binding,
            'binding-' + label, batch_size, common_scale)
        comparison = compare_ordered(getattr(native, label), reconstructed)
        if not comparison['schema_equal'] or not comparison['values_equal']:
            raise ValueError('native wide artifacts do not match supplied native aggregates')
        frames[label] = reconstructed
    return frames


def _persist_native_vectors(frame, keys, product, directory, label, batch_size):
    '''Validate complete long keys once and pivot only bounded aggregate batches.'''
    schema = frame.collect_schema()
    required = {'sum_exact': pl.String, 'n_unweighted': pl.UInt64,
                'flags': pl.List(pl.String), 'fractional_support_mass': pl.Float64}
    if any(schema.get(k) != v for k, v in required.items()):
        raise ValueError('invalid native aggregate value schema')
    scale = frame.select(pl.col('sum_exact').str.extract(r'\.(\d+)$', 1)
                         .str.len_chars().max()).collect().item() or 0
    if scale > 38:
        raise ValueError('invalid native Decimal scale')
    reader = _OrderedAggregateReader(frame, keys, product)
    paths = []
    batch = []
    wide_schema = _native_wide_schema(keys, scale)

    def flush():
        bounded = pl.concat(batch).lazy() if batch else pl.LazyFrame(schema=schema)
        _require_clean(bounded,
            pl.col('sum_exact').is_null() | pl.col('n_unweighted').is_null()
            | pl.col('flags').is_null()
            | pl.col('flags').list.eval(pl.element().is_null()).list.any()
            | pl.col('flags').ne(pl.col('flags').list.unique().list.sort())
            | pl.col('fractional_support_mass').ne(pl.col('n_unweighted').cast(pl.Float64))
                .fill_null(True), 'invalid native aggregate values')
        grain = [*keys, 'component_year']
        consistency = bounded.group_by(grain).agg(
            *[pl.col(name).n_unique().alias(name)
              for name in ('n_unweighted', 'flags', 'fractional_support_mass')])
        _require_clean(consistency, pl.any_horizontal(pl.col(n).ne(1) for n in
            ('n_unweighted', 'flags', 'fractional_support_mass')),
            'native support must be identical across replicates')
        wide = bounded.group_by(grain).agg(
            *[pl.col('sum_exact').filter(pl.col('replicate').eq(r)).first()
                .cast(pl.Decimal(38, scale)).alias(name)
              for r, name in enumerate(WEIGHT_NAMES)],
            pl.col('n_unweighted').first(), pl.col('flags').first()).select(
                pl.col(name).cast(dtype) for name, dtype in wide_schema.items())
        paths.append(_sink_projection(wide.sort(grain), directory,
                                      f'{label}-native-{len(paths):08d}'))
        batch.clear()

    try:
        while (group := reader.next_group()) is not None:
            batch.append(group[1])
            if len(batch) == batch_size:
                flush()
        if batch or not paths:
            flush()
    finally:
        reader.release()
    return pl.concat(paths)


def _validate_native_vectors(cells, denominators, product):
    for frame, keys in [(cells, PAIR_KEYS), (denominators, DENOMINATOR_KEYS)]:
        _require_clean(frame, pl.any_horizontal(pl.col(name).is_null() for name in WEIGHT_NAMES),
                       'null native weight')
        annual = frame.filter(pl.col('component_year').ne(0)).group_by(keys).agg(
            *[pl.col(name).sum().alias(name) for name in WEIGHT_NAMES],
            pl.col('n_unweighted').sum(),
            pl.col('flags').list.explode(keep_nulls=False, empty_as_null=False).unique().sort())
        pooled = frame.filter(pl.col('component_year').eq(0))
        _exact_native_closure(annual, pooled, keys)
    _require_clean(cells, pl.col('PERWT').lt(0), 'negative full cell mass')
    _require_clean(cells, pl.col('unit_a_type').ne('work_migration_puma'),
                   'work/migration workplace geography required')
    grain = [*DENOMINATOR_KEYS, 'component_year']
    totals = cells.group_by(grain).agg(
        *[pl.col(name).sum().alias(name) for name in WEIGHT_NAMES],
        pl.col('n_unweighted').sum(),
        pl.col('flags').list.explode(keep_nulls=False, empty_as_null=False).unique().sort())
    _exact_native_closure(totals, denominators, grain)


def _exact_native_closure(expected, actual, keys):
    # The pinned engine panics on an empty full join with Decimal comparisons.
    if (expected.select(pl.len()).collect().item() == 0
            and actual.select(pl.len()).collect().item() == 0):
        return
    values = [*WEIGHT_NAMES, 'n_unweighted', 'flags']
    joined = expected.select(*keys, *values).join(
        actual.select(*keys, *values), on=keys, how='full', coalesce=True,
        suffix='_actual', validate='1:1')
    _require_clean(joined, pl.any_horizontal(
        pl.col(name).is_null() | pl.col(name + '_actual').is_null()
        | pl.col(name).ne(pl.col(name + '_actual')) for name in values),
        'native denominator or component closure failed')


def _float_native_vectors(frame):
    expressions = []
    for name, mass in zip(WEIGHT_NAMES, _MASS_COLUMNS, strict=True):
        exact = pl.col(name).cast(pl.String).str.replace(r'(\.\d*?)0+$', '${1}')\
            .str.replace(r'\.$', '').replace('-0', '0')
        expressions.append(exact.cast(pl.Float64).alias(mass))
    return frame.select(*PAIR_KEYS, 'component_year', *expressions,
        'n_unweighted', 'flags',
        pl.col('n_unweighted').cast(pl.Float64).alias('fractional_support_mass'))


def _wide_destination(contributions, input_support=None):
    keys = [*PAIR_KEYS, 'component_year']
    masses = _ordered_reduce(contributions, keys,
        ['origin_workplace_unit', 'county_node_id'], [*_MASS_COLUMNS, 'fractional_support_mass'])
    support = contributions if input_support is None else input_support
    counts = support.unique(subset=[*keys, 'origin_workplace_unit']).group_by(keys).agg(
        pl.col('n_unweighted').sum(),
        pl.col('flags').list.explode(keep_nulls=False, empty_as_null=False).unique().sort())
    return masses.select(*keys, *_MASS_COLUMNS, 'fractional_support_mass').join(
        counts, on=keys, validate='1:1')


def _wide_denominators(cells):
    keys = [*DENOMINATOR_KEYS, 'component_year']
    reduced = _ordered_reduce(cells, keys, ['unit_b_type', 'unit_b'],
        [*_MASS_COLUMNS, 'fractional_support_mass', 'n_unweighted'])
    flags = cells.group_by(keys).agg(pl.col('flags').list.explode(
        keep_nulls=False, empty_as_null=False).unique().sort())
    return reduced.select(*keys, *_MASS_COLUMNS, 'fractional_support_mass',
                          'n_unweighted').join(flags, on=keys, validate='1:1')


def _wide_conservation(expected, actual, keys):
    joined = expected.select(*keys, *_MASS_COLUMNS).join(
        actual.select(*keys, *_MASS_COLUMNS), on=keys, how='full', coalesce=True,
        suffix='_actual', validate='1:1')
    _require_clean(joined, pl.any_horizontal(
        pl.col(name).is_null() | pl.col(name + '_actual').is_null()
        | ~pl.col(name).is_finite() | ~pl.col(name + '_actual').is_finite()
        | ((pl.col(name + '_actual') - pl.col(name)).abs()
           > 1e-8 + 1e-12 * pl.col(name).abs()) for name in _MASS_COLUMNS),
        'allocation mass conservation failed')


def _unpivot_projection(frame, keys):
    index = [name for name in frame.collect_schema() if name not in _MASS_COLUMNS]
    return frame.unpivot(on=_MASS_COLUMNS, index=index, variable_name='_r', value_name='mass')\
        .with_columns(pl.col('_r').str.strip_prefix('_mass_').cast(pl.UInt8).alias('replicate'))\
        .drop('_r').sort([*keys, 'component_year', 'replicate'])


def _spill_projected_long(wide, keys, directory, label, batch_size):
    registry = _sink_projection(wide.select(keys).unique().sort(keys), directory, label + '-keys')
    paths = []
    offset = 0
    while True:
        batch = registry.slice(offset, batch_size).collect()
        if batch.is_empty() and paths:
            break
        selected = wide.join(batch.lazy(), on=keys, how='semi')
        long = _unpivot_projection(selected, keys).with_columns(
            pl.lit(None, dtype=pl.String).alias('sum_exact'))
        columns = [*keys, *COMPONENT_KEYS, 'mass', 'fractional_support_mass', 'n_unweighted']
        columns += ['flags', 'sum_exact'] if label == 'cells' else ['sum_exact', 'flags']
        _append_projection_fragment(paths, long.select(columns), directory,
            f'{label}-long-{len(paths):08d}', [*keys, *COMPONENT_KEYS])
        if batch.height < batch_size:
            break
        offset += batch_size
    return _projection_fragment_scan(paths)


def _wide_residuals(contributions, product):
    keys = ['origin_workplace_unit', 'unit_b_type', 'unit_b', 'component_year', 'residual_type']
    reduced = _ordered_reduce(contributions, keys, ['county_node_id'],
                              [*_MASS_COLUMNS, 'fractional_support_mass'])
    return reduced.select(*keys, *_MASS_COLUMNS, 'fractional_support_mass',
                          'n_unweighted', 'flags')


def _spill_residual_long(wide, product, directory, batch_size):
    if wide.select(pl.len()).collect().item() == 0:
        return _sink_projection(pl.LazyFrame(schema=RESIDUAL_SCHEMA), directory, 'residual-empty')
    # residual_type follows replicate in the serialized key, so batch by its preceding prefix.
    keys = ['origin_workplace_unit', 'unit_b_type', 'unit_b']
    registry = _sink_projection(wide.select(keys).unique().sort(keys), directory, 'residual-keys')
    paths = []
    offset = 0
    while True:
        batch = registry.slice(offset, batch_size).collect()
        if batch.is_empty() and paths:
            break
        selected = wide.join(batch.lazy(), on=keys, how='semi')
        long = _unpivot_projection(selected, keys)
        # Reduction is already complete; _residuals only supplies the frozen serialization.
        serialized = _residuals(long.with_columns(
            pl.lit('').alias('county_node_id')), product).sort(
                AUXILIARY_KEYS['allocation_residuals'])
        _append_projection_fragment(paths, serialized, directory,
            f'residual-long-{len(paths):08d}', AUXILIARY_KEYS['allocation_residuals'])
        if batch.height < batch_size:
            break
        offset += batch_size
    return _projection_fragment_scan(paths)


def _allocate_area_mix_spilled(
    native: AggregateSet, county_factors: pl.DataFrame, counties: pl.DataFrame, product: Product,
    workspace: Path, *, native_wide_root: Path | None = None, batch_size: int = 128,
) -> tuple[AggregateSet, pl.LazyFrame]:
    '''Persist wide aggregate stages; final scans live until caller removes workspace.'''
    if (product.family != 'area_mix' or product.view not in {'allocated_county', 'allocated_msa'}
        or native.product.view != 'observed'
        or observed_counterpart(product) != native.product):
        raise ValueError('only corresponding observed workplace area mixes can be allocated')
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
        raise ValueError('batch_size must be a positive integer')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', product.product_id):
        raise ValueError('unsafe projection product ID')
    workspace = Path(workspace)
    safe_path(workspace)
    if not workspace.is_dir():
        raise ValueError('projection workspace must be an existing directory')
    directory = workspace / ('projection-' + product.product_id)
    safe_path(directory)
    directory.mkdir()
    try:
        relations = _allocation_relations(county_factors, counties)
        sources = ({name: getattr(native, name) for name in ('cells', 'denominators')}
            if native_wide_root is None else
            _projection_native_artifacts(native, native_wide_root, directory, batch_size))
        vectors = {label: _persist_native_vectors(sources[label], keys, native.product,
                    directory, label, batch_size)
                   for label, keys in [('cells', PAIR_KEYS), ('denominators', DENOMINATOR_KEYS)]}
        if native_wide_root is not None:
            shutil.rmtree(directory / 'binding')
        _validate_native_vectors(vectors['cells'], vectors['denominators'], native.product)
        if vectors['cells'].select(pl.len()).collect().item() == 0:
            return _empty_projection(native, product, directory)
        source = _sink_projection(_float_native_vectors(vectors['cells']).rename(
            {'unit_a': 'origin_workplace_unit'}), directory, 'source')
        missing = source.select('origin_workplace_unit').unique().join(
            relations.select('origin_workplace_unit').unique(),
            on='origin_workplace_unit', how='anti')
        if missing.select(pl.len()).collect().item():
            raise ValueError('missing positive-factor workplace coverage')
        contributions = source.join(relations, on='origin_workplace_unit', how='inner')\
            .filter(pl.col('factor') > 0).with_columns(
                *[(pl.col(name) * pl.col('factor')).alias(name) for name in _MASS_COLUMNS],
                (pl.col('n_unweighted') * pl.col('factor')).alias('fractional_support_mass'),
                pl.concat_list('flags', pl.lit(ALLOCATION_FLAGS),
                    pl.when(pl.col('factor') < 1).then(pl.lit('flag_fractional_split'))
                      .otherwise(None)).list.drop_nulls().list.unique().list.sort().alias('flags'),
                pl.col('county_node_id').alias('unit_a'), pl.lit('county').alias('unit_a_type'))
        contributions = _sink_projection(contributions, directory, 'contributions')
        origin_keys = ['origin_workplace_unit', 'unit_b_type', 'unit_b', 'component_year']
        county_mass = _ordered_reduce(contributions, origin_keys,
                                      ['county_node_id'], _MASS_COLUMNS)
        _wide_conservation(source, county_mass, origin_keys)
        cells = _sink_projection(_wide_destination(contributions), directory, 'county-cells')
        if product.view == 'allocated_msa':
            metro = contributions.filter(pl.col('cbsa_type') == 'metropolitan').with_columns(
                pl.col('cbsa_id').alias('unit_a'), pl.lit('cbsa').alias('unit_a_type'))
            metro_counties = cells.rename({'unit_a': 'county_node_id'}).join(
                counties.select(pl.col('county_id').alias('county_node_id'),
                                'cbsa_id', 'cbsa_type').lazy(),
                on='county_node_id', how='left', validate='m:1')\
                .filter(pl.col('cbsa_type') == 'metropolitan').with_columns(
                    pl.col('cbsa_id').alias('unit_a'), pl.lit('cbsa').alias('unit_a_type'),
                    pl.col('county_node_id').alias('origin_workplace_unit'))
            msa = _sink_projection(_wide_destination(metro_counties, metro),
                                   directory, 'msa-cells')
            residual = contributions.filter(
                pl.col('cbsa_type').ne('metropolitan').fill_null(True))\
                .with_columns(pl.when(pl.col('cbsa_type') == 'micropolitan').then(
                    pl.lit('micropolitan')).otherwise(pl.lit('no_cbsa')).alias('residual_type'))
            residual = _sink_projection(_wide_residuals(residual, product),
                                        directory, 'residual-wide')
            residuals = _spill_residual_long(residual, product, directory, batch_size)
            totals_keys = ['unit_b_type', 'unit_b', 'component_year']
            expected = _ordered_reduce(cells, totals_keys, ['unit_a'], _MASS_COLUMNS)
            actual = pl.concat([msa.select(*totals_keys, 'unit_a', *_MASS_COLUMNS),
                _residual_conservation_vectors(residuals, product)])
            actual = _ordered_reduce(actual, totals_keys, ['unit_a'], _MASS_COLUMNS)
            _wide_conservation(expected, actual, totals_keys)
            cells = msa
            if cells.select(pl.len()).collect().item() == 0:
                return _empty_projection(native, product, directory, residuals=residuals)
        else:
            residuals = _sink_projection(pl.LazyFrame(schema=RESIDUAL_SCHEMA),
                                        directory, 'residual-empty')
        denominators = _sink_projection(_wide_denominators(cells), directory, 'denominators')
        _wide_conservation(_wide_denominators(cells), denominators,
                           [*DENOMINATOR_KEYS, 'component_year'])
        cells = _spill_projected_long(cells, PAIR_KEYS, directory, 'cells', batch_size)
        denominators = _spill_projected_long(denominators, DENOMINATOR_KEYS, directory,
                                              'denominators', batch_size)
        diagnostics = _sink_projection(_product_diagnostics(native.diagnostics, product),
                                       directory, 'diagnostics')
        return AggregateSet(cells, denominators, diagnostics, product), residuals
    except BaseException:
        shutil.rmtree(directory)
        raise


def _empty_projection(native, product, directory, *, residuals=None):
    frames = {}
    for label, keys in [('cells', PAIR_KEYS), ('denominators', DENOMINATOR_KEYS)]:
        schema = {**{key: pl.String for key in keys}, 'component_year': pl.Int64,
                  'replicate': pl.UInt8, 'mass': pl.Float64,
                  'fractional_support_mass': pl.Float64, 'n_unweighted': pl.UInt64}
        schema.update({'flags': pl.List(pl.String), 'sum_exact': pl.String} if label == 'cells'
                      else {'sum_exact': pl.String, 'flags': pl.List(pl.String)})
        frames[label] = _sink_projection(pl.LazyFrame(schema=schema), directory, label + '-empty')
    diagnostics = _sink_projection(_product_diagnostics(native.diagnostics, product),
                                   directory, 'diagnostics')
    if residuals is None:
        residuals = _sink_projection(pl.LazyFrame(schema=RESIDUAL_SCHEMA),
                                        directory, 'residual-empty')
    return AggregateSet(frames['cells'], frames['denominators'], diagnostics, product), residuals


def _residual_conservation_vectors(residuals, product):
    if residuals.select(pl.len()).collect().item() == 0:
        # Avoid the pinned optimizer's empty Parquet group-by statistics panic.
        return pl.LazyFrame(schema={'unit_b_type': pl.String, 'unit_b': pl.String,
            'component_year': pl.Int64, 'unit_a': pl.String,
            **{name: pl.Float64 for name in _MASS_COLUMNS}})
    return residuals.group_by('workplace_unit', 'code_unit_type', 'code_unit',
        'component_year', 'residual_type').agg(
            *[(pl.col('weighted_mass').filter(pl.col('replicate').eq(r)).first()
                * product.pool_divisor).alias(name) for r, name in enumerate(_MASS_COLUMNS)])\
        .select(pl.col('code_unit_type').alias('unit_b_type'),
            pl.col('code_unit').alias('unit_b'), 'component_year',
            pl.concat_str('workplace_unit', 'residual_type').alias('unit_a'), *_MASS_COLUMNS)


@dataclass(frozen=True)
class _ProjectionFragment:
    path: Path
    first_key: tuple | None
    last_key: tuple | None
    row_count: int
    schema: tuple


def _append_projection_fragment(fragments, frame, directory, label, keys):
    scan = _sink_projection(frame, directory, label)
    count, first, last = scan.select(pl.len(), pl.struct(keys).first().alias('first'),
                                    pl.struct(keys).last().alias('last')).collect().row(0)
    fragment = _ProjectionFragment(directory / (label + '.parquet'),
        tuple(first.values()) if count else None, tuple(last.values()) if count else None,
        count, tuple(scan.collect_schema().items()))
    if fragments:
        previous = fragments[-1]
        if previous.schema != fragment.schema or (previous.row_count and count
                and previous.last_key >= fragment.first_key):
            raise ValueError(
                'projection fragments require matching schemas and disjoint ordered keys')
    fragments.append(fragment)


def _projection_fragment_scan(fragments):
    return pl.concat([pl.scan_parquet(fragment.path) for fragment in fragments])
