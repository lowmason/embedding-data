'''Complete aggregate assembly and numeric cross-table consistency.'''

import polars as pl
import pytest
from acs_target_fixtures import target_runs as _target_runs  # noqa: F401

from embedding_data import acs_target_tables as tables
from embedding_data.acs_target_contract import PRODUCTS, validate_cross_tables

def _all_products_and_typed_allocated_views(target_runs):
    frames = {
        name: pl.read_parquet(target_runs['first'] / (name + '.parquet')) for name in tables.TABLES
    }
    validate_cross_tables(frames, PRODUCTS)
    support = frames['target_support']
    assert set(support['view']) == {'observed', 'canonical', 'allocated_county', 'allocated_msa'}
    allocated = frames['targets_allocated_area_mix']
    assert set(allocated['unit_a_type']) == {'county', 'cbsa'}
    assert support.filter(pl.col('view').eq('allocated_county'))[
        'unit_a_type'
    ].unique().to_list() == ['county']
    assert support.filter(pl.col('view').eq('allocated_msa'))[
        'unit_a_type'
    ].unique().to_list() == ['cbsa']


def _cross_table_reconciliation_rejects_inconsistent_statistics(target_runs, change):
    frames = {
        name: pl.read_parquet(target_runs['first'] / (name + '.parquet')) for name in tables.TABLES
    }
    if change == 'denominator':
        name, column = 'target_support', 'denominator_mass'
    elif change == 'replicate':
        name, column = 'replicate_estimates', 'estimate'
    elif change == 'target':
        name, column = 'targets_observed', 'value'
    elif change == 'missing_se':
        name, column = 'target_support', 'se_reason'
    elif change == 'orphan':
        frames['target_support'] = frames['target_support'].with_columns(
            pl.lit('feature:acs_industry_category:orphan').alias('unit_b')
        )
        name = None
    elif change == 'duplicate':
        row = (
            frames['targets_observed']
            .head(1)
            .with_columns(pl.lit(['size_gate_pending', 'variant']).alias('flags'))
        )
        frames['targets_observed'] = pl.concat([frames['targets_observed'], row])
        name = None
    elif change == 'duplicate_se':
        row = frames['targets_observed'].head(1).with_columns(
            pl.lit('none').alias('se_method'), pl.lit(None, dtype=pl.Float64).alias('se'))
        frames['targets_observed'] = pl.concat([frames['targets_observed'], row])
        name = None
    elif change == 'missing_measure':
        for name in (*tables.TARGET_TABLES, 'target_support', 'replicate_estimates'):
            frames[name] = frames[name].filter(pl.col('measure').eq('forward_share'))
        name = None
    elif change == 'missing_support':
        frames['target_support'] = frames['target_support'].filter(pl.col('component_year').ne(0))
        name = None
    else:
        frames['replicate_estimates'] = frames['replicate_estimates'].filter(
            pl.col('replicate').ne(37)
        )
        name = None
    if name:
        expr = pl.lit('fabricated') if column == 'se_reason' else pl.col(column) + 0.125
        frames[name] = frames[name].with_columns(expr.alias(column))
    with pytest.raises(ValueError):
        tables.validate_complete_tables(frames)


def _complete_bundle_requires_annual_components(target_runs):
    frames = {
        name: pl.read_parquet(target_runs['first'] / (name + '.parquet')) for name in tables.TABLES
    }
    frames['target_support'] = frames['target_support'].filter(pl.col('component_year').eq(0))
    with pytest.raises(ValueError, match='annual|component'):
        tables.validate_complete_tables(frames)


def _strict_annual_migration_keeps_out_of_period_source_diagnostics(target_runs):
    from embedding_data.acs_target_contract import validate_auxiliary

    diagnostics = pl.read_parquet(target_runs['first'] / 'eligibility_diagnostics.parquet')
    product = next(
        p for p in PRODUCTS if p.family == 'migration_flow' and p.evidence_policy == 'strict'
    )
    annual = diagnostics.filter(pl.col('product_id').eq(product.product_id))
    excluded = annual.filter(
        pl.col('component_year').eq(2023) & pl.col('partition_kind').eq('first_exclusion')
    )
    assert set(excluded['reason']) == {'outside_declared_period'}
    assert (
        annual.filter(
            pl.col('component_year').eq(2023) & pl.col('partition_kind').eq('evidence')
        ).height
        > 0
    )
    invalid = annual.with_columns(pl.lit(2025, dtype=pl.Int64).alias('component_year'))
    with pytest.raises(ValueError, match='year'):
        validate_auxiliary('eligibility_diagnostics', invalid)


def test_complete_validation_requires_native_annual_records():
    from test_acs_target_contract import valid_tables

    with pytest.raises(ValueError, match='annual|component'):
        tables.validate_complete_tables(valid_tables())


def test_complete_assembly_and_adversarial_cross_table_invariants(target_runs):
    _all_products_and_typed_allocated_views(target_runs)
    for change in (
        'denominator',
        'replicate',
        'target',
        'missing_se',
        'orphan',
        'duplicate',
        'missing_support',
        'missing_replicate',
        'duplicate_se',
        'missing_measure',
    ):
        _cross_table_reconciliation_rejects_inconsistent_statistics(target_runs, change)
    _complete_bundle_requires_annual_components(target_runs)
    _strict_annual_migration_keeps_out_of_period_source_diagnostics(target_runs)


def test_coherently_wrong_native_denominator_is_rejected():
    from test_acs_target_contract import frame, valid_tables

    from embedding_data.acs_target_contract import STAT_KEY_COLUMNS

    frames = valid_tables()
    # All scalar points and SEs agree with the replacement denominator, but the
    # identified numerator cells supply only half of that invented denominator.
    target = frames['targets_observed'].row(0, named=True)
    target['value'] = 0.5
    total = target | {'measure': 'annual_average_total', 'value': 25.0}
    frames['targets_observed'] = pl.DataFrame(
        [total, target], schema=frames['targets_observed'].schema)
    original = frames['target_support'].row(0, named=True)
    support = []
    for measure in ('annual_average_total', 'forward_share'):
        for year in (0, 2023, 2024):
            pooled = year == 0
            support.append(original | {'measure': measure, 'component_year': year,
                'n_unweighted': 2 if pooled else 1,
                'denominator_n_unweighted': 2 if pooled else 1,
                'cell_weight_sum_exact': '50' if pooled else '25',
                'denominator_weight_sum_exact': '100' if pooled else '50',
                'cell_mass': 25.0 if pooled else 12.5,
                'denominator_mass': 50.0 if pooled else 25.0,
                'fractional_support_mass': 2.0 if pooled else 1.0,
                'denominator_fractional_support_mass': 2.0 if pooled else 1.0})
    frames['target_support'] = frame('target_support', support).sort(
        [*STAT_KEY_COLUMNS, 'record_kind', 'component_year'], nulls_last=False)
    reps = frames['replicate_estimates']
    frames['replicate_estimates'] = pl.concat([
        reps.with_columns(pl.lit(measure).alias('measure'),
            pl.lit(50.0).alias('denominator'), pl.lit('100').alias('denominator_sum_exact'),
            pl.lit(25.0 if measure == 'annual_average_total' else 0.5).alias('estimate'))
        for measure in ('annual_average_total', 'forward_share')]).sort(
            [*STAT_KEY_COLUMNS, 'replicate'])
    with pytest.raises(ValueError, match='denominator'):
        tables.validate_complete_tables(frames)


@pytest.mark.parametrize('component,replicate', [(0, 0), (2023, 0), (2023, 37), (2024, 80)])
def test_internal_native_denominator_closure_covers_annual_replicates(component, replicate):
    from dataclasses import replace

    from acs_target_fixtures import estimation_rows, weights

    from embedding_data.acs_target_estimation import aggregate_native

    native = aggregate_native(estimation_rows([
        {'year': year, 'a': 'a', 'b': 'b', **weights('10')} for year in (2023, 2024)]))
    broken = native.denominators.with_columns(pl.when(
        pl.col('component_year').eq(component) & pl.col('replicate').eq(replicate))
        .then(pl.lit('21' if component == 0 else '11'))
        .otherwise(pl.col('sum_exact')).alias('sum_exact'))
    with pytest.raises(ValueError, match='denominator'):
        tables._validate_aggregate_denominators(replace(native, denominators=broken))


def test_native_and_both_allocated_views_close_for_all_components():
    from acs_target_fixtures import projection_case

    from embedding_data.acs_target_projection import allocate_area_mix

    fixture = projection_case()
    tables._validate_aggregate_denominators(fixture['native'])
    for view in ('county_product', 'msa_product'):
        allocated, _ = allocate_area_mix(fixture['native'], fixture['factors'],
                                         fixture['counties'], fixture[view])
        tables._validate_aggregate_denominators(allocated)
