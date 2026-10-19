'''Supported canonical membership and deterministic workplace county/MSA allocation.'''

import polars as pl

from embedding_data.acs_mapping_contract import factor_key
from embedding_data.acs_target_contract import (
    AUXILIARY_KEYS,
    PRODUCTS,
    RESIDUAL_SCHEMA,
    SELECTED_NODE_FRAMES,
    Product,
    observed_counterpart,
)
from embedding_data.acs_target_estimation import DENOMINATOR_KEYS, PAIR_KEYS, AggregateSet
from embedding_data.acs_target_membership import FAMILY_INPUTS, FamilyRows, _diagnostic

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
