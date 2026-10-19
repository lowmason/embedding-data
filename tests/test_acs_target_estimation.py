from math import sqrt

import polars as pl
import pytest
from acs_target_fixtures import estimate_case, estimation_rows, weights

from embedding_data.acs_target_contract import validate_auxiliary
from embedding_data.acs_target_estimation import aggregate_native, estimate, replicate_se
from embedding_data.target_contract import validate_targets

def record(point='10', *, year=2023, a='industry', b='A', overrides=None):
    return {'year': year, 'a': a, 'b': b, **weights(point, overrides)}


def cell(result, table='targets', measure='forward_share', b='A', year=0):
    lf = result[table].filter(pl.col('unit_b').eq('feature:acs_occupation_category:' + b)
                              & pl.col('measure').eq(measure))
    if table == 'support':
        lf = lf.filter(pl.col('component_year').eq(year))
    return lf


def test_ratio_of_pooled_totals_and_interior_replicate_covariance():
    result = estimate_case([record('10', overrides={37: '30'}), record('30', b='B'),
                            record('100', year=2024), record('100', year=2024, b='B')])
    a = cell(result).row(0, named=True)
    assert a['value'] == pytest.approx(11 / 24, rel=0, abs=1e-12)
    assert a['n_weighted'] == 55.0
    assert a['n_unweighted'] == 2
    assert a['se'] == pytest.approx(1 / (24 * sqrt(20)), rel=0, abs=1e-12)
    replicates = cell(result, 'replicates')
    assert replicates['replicate'].to_list() == list(range(1, 81))
    assert replicates.filter(pl.col('replicate').eq(37))['estimate'].item() == 0.5
    total = cell(result, measure='annual_average_total').row(0, named=True)
    assert total['value'] == 55
    assert total['se'] == pytest.approx(sqrt(5))
    assert cell(result, 'replicates', 'annual_average_total').filter(
        pl.col('replicate').eq(37))['estimate'].item() == 65
    for name, auxiliary in [('target_support', 'support'), ('replicate_estimates', 'replicates')]:
        validate_auxiliary(name, result[auxiliary])
    validate_targets(result['targets'])


def test_declared_divisor_and_exact_decimal_contributions():
    result = estimate_case([record('0.1'), record('0.2')])
    pooled = cell(result, 'support', 'annual_average_total').row(0, named=True)
    assert pooled['cell_weight_sum_exact'] == '0.3'
    assert pooled['cell_mass'] == 0.15
    assert pooled['n_unweighted'] == 2
    absent = cell(result, 'support', 'annual_average_total', year=2024).row(0, named=True)
    assert absent['cell_weight_sum_exact'] == '0'
    assert absent['n_unweighted'] == 0
    assert absent['cell_mass'] == 0
    annual = estimate_case([record('0.3', year=2024)], years=(2024,), pool_divisor=1)
    assert cell(annual, measure='annual_average_total')['value'].item() == 0.3


def test_split_positions_preserves_masses_shares_and_uncertainty():
    whole = estimate_case([record('0.3', overrides={1: '0.9', 37: '-0.6', 80: '1.5'}),
                           record('0.4', b='B')])
    split = estimate_case([record('0.1', overrides={1: '0.3', 37: '-0.2', 80: '0.5'}),
                           record('0.2', overrides={1: '0.6', 37: '-0.4', 80: '1.0'}),
                           record('0.4', b='B')])
    for measure in ['annual_average_total', 'forward_share']:
        assert cell(whole, measure=measure).select('value', 'se', 'n_weighted').equals(
            cell(split, measure=measure).select('value', 'se', 'n_weighted'))
        assert cell(split, measure=measure)['n_unweighted'].item() == 2


def test_zero_full_denominator_retains_defined_replicate_and_support():
    result = estimate_case([record('0', overrides={37: '2'})])
    assert result['targets'].is_empty()
    status = result['support'].filter(pl.col('record_kind').eq('denominator_status'))
    assert status['component_year'].to_list() == [0, 2023]
    assert status['point_status'].unique().to_list() == ['nonpositive_denominator']
    audit = cell(result, 'support').row(0, named=True)
    assert audit['se_status'] == 'undefined_point'
    reps = cell(result, 'replicates')
    assert reps.height == 80
    assert reps.filter(pl.col('replicate').eq(37))['estimate'].item() == 1
    assert reps.filter(pl.col('replicate').eq(1))['status'].item() == 'zero_denominator'
    validate_auxiliary('target_support', result['support'])
    validate_auxiliary('replicate_estimates', result['replicates'])


def test_undefined_ratio_se_does_not_disable_total():
    result = estimate_case([record('10', overrides={37: '0'}),
                           record('10', b='B', overrides={37: '0'})])
    point = cell(result).row(0, named=True)
    assert point['value'] == 0.5
    assert point['se'] is None and point['se_method'] == 'none'
    statuses = result['support'].filter(pl.col('unit_b').eq(point['unit_b'])
                                         & pl.col('measure').eq('forward_share'))
    assert statuses['undefined_replicates'].to_list() == [[37]] * 3
    assert statuses['se_status'].to_list() == ['undefined_replicates'] * 3
    assert all(reason is not None for reason in statuses['se_reason'])
    assert cell(result, measure='annual_average_total')['se'].item() == pytest.approx(sqrt(1.25))


@pytest.mark.parametrize('a,b,expected', [('-10', '5', 2.0), ('10', '-15', -2.0)])
def test_signed_replicate_ratios_are_unclipped(a, b, expected):
    result = estimate_case([record('10', overrides={37: a}),
                           record('10', b='B', overrides={37: b})])
    r = cell(result, 'replicates').filter(pl.col('replicate').eq(37)).row(0, named=True)
    assert r['estimate'] == expected and r['status'] == 'defined'
    assert r['denominator'] == (float(a) + float(b)) / 2


def test_all_replicate_positions_contribute():
    result = estimate_case([record('10', overrides={1: '12', 37: '14', 80: '16'})])
    assert cell(result, measure='annual_average_total')['se'].item() == pytest.approx(sqrt(0.7))


def test_no_densification_and_zero_cell_with_defined_total_se():
    result = estimate_case([record('0', overrides={37: '1'}), record('10', b='B'),
                           record('20', a='other', b='C')])
    assert result['targets'].height == 4
    assert cell(result, 'support', 'annual_average_total')['point_status'].unique().item() == (
        'no_positive_cell_mass')
    assert (cell(result, 'support', 'annual_average_total')['se_status'].unique().item()
            == 'defined')
    assert result['replicates'].height == 3 * 2 * 80


def test_aggregation_materializes_inside_source_lifetime_and_preserves_raw_sums(tmp_path):
    rows = estimation_rows([record('0.1'), record('0.2', year=2024)])
    path = tmp_path / 'members.parquet'
    rows.members.collect().write_parquet(path)
    from dataclasses import replace
    aggregates = aggregate_native(replace(rows, members=pl.scan_parquet(path)))
    path.unlink()
    pooled = aggregates.cells.filter(pl.col('component_year').eq(0)
                                     & pl.col('replicate').eq(0)).collect()
    assert pooled['sum_exact'].item() == '0.3'
    assert estimate(aggregates)['targets'].collect().height == 2


def test_empty_members_have_typed_empty_outputs():
    result = estimate(aggregate_native(estimation_rows([])))
    assert all(lf.collect().is_empty() for lf in result.values())
    validate_targets(result['targets'])
    validate_auxiliary('target_support', result['support'])
    validate_auxiliary('replicate_estimates', result['replicates'])


@pytest.mark.parametrize('mutation', ['missing', 'null', 'float', 'outside_year', 'negative_full'])
def test_invalid_weights_and_members_fail(mutation):
    from dataclasses import replace
    rows = estimation_rows([record()])
    if mutation == 'missing':
        members = rows.members.drop('REPWTP37')
    elif mutation == 'null':
        members = rows.members.with_columns(
            pl.lit(None, dtype=pl.Decimal(38, 0)).alias('REPWTP37'))
    elif mutation == 'float':
        members = rows.members.with_columns(pl.lit(float('inf')).alias('PERWT'))
    elif mutation == 'outside_year':
        members = rows.members.with_columns(pl.lit(2022).alias('YEAR'))
    else:
        members = rows.members.with_columns(pl.lit(-1).cast(pl.Decimal(38, 0)).alias('PERWT'))
    with pytest.raises(ValueError):
        estimate(aggregate_native(replace(rows, members=members)))


def test_aggregate_overflow_bound_and_unsupported_precision_fail():
    with pytest.raises(ValueError, match='overflow'):
        aggregate_native(estimation_rows([record('9' * 38), record('9' * 38)]))
    with pytest.raises(ValueError, match='precision'):
        aggregate_native(estimation_rows([record('0.' + '0' * 37 + '1')]))


@pytest.mark.parametrize('full,reps', [(float('inf'), (1.0,) * 80),
                                     (1., (float('nan'),) * 80), (1., (1.,) * 79)])
def test_replicate_se_rejects_invalid_numeric_inputs(full, reps):
    with pytest.raises(ValueError):
        replicate_se(full, reps)


def test_replicate_se_undefined_and_signed_inputs():
    assert replicate_se(1., (None,) + (1.,) * 79) is None
    assert replicate_se(1., (-1.,) + (1.,) * 79) == pytest.approx(sqrt(0.2))


def test_negative_weight_record_is_not_deleted_when_full_cell_mass_is_valid():
    result = estimate_case([record('-2'), record('12')])
    total = cell(result, measure='annual_average_total').row(0, named=True)
    assert total['n_unweighted'] == 2
    assert total['value'] == 5


def test_mapping_flags_union_and_exact_large_sum_survive():
    a = record('10000000000000000000000000000.1') | {'flags': ['mapped', 'size_gate_pending']}
    b = record('0.2') | {'flags': ['imputed', 'size_gate_pending']}
    result = estimate_case([a, b])
    assert cell(result, 'support')['cell_weight_sum_exact'].item() == (
        '10000000000000000000000000000.3')
    assert cell(result)['flags'].item().to_list() == ['imputed', 'mapped', 'size_gate_pending']


def test_estimate_rechecks_aggregate_join_uniqueness_and_complete_replicates():
    from dataclasses import replace
    aggregates = aggregate_native(estimation_rows([record()]))
    with pytest.raises(ValueError, match='duplicate'):
        estimate(replace(aggregates, denominators=pl.concat(
            [aggregates.denominators, aggregates.denominators])))
    with pytest.raises(ValueError, match='incomplete'):
        estimate(replace(aggregates, cells=aggregates.cells.filter(pl.col('replicate').ne(37))))


def test_allocated_raw_mass_and_fractional_support_consumption():
    from dataclasses import replace

    from embedding_data.acs_target_contract import PRODUCTS

    aggregates = aggregate_native(estimation_rows([record('20')]))
    product = next(p for p in PRODUCTS if p.view == 'allocated_county'
                   and p.dimension == 'industry' and p.base_universe == 'civilian_employed'
                   and p.evidence_policy == 'strict')
    cells = aggregates.cells.with_columns(
        pl.col('sum_exact').cast(pl.Float64).alias('mass'),
        pl.lit(None, dtype=pl.String).alias('sum_exact'),
        (pl.col('fractional_support_mass') * 0.25).alias('fractional_support_mass'),
        pl.lit('county').alias('unit_a_type'),
        pl.lit('geography:2025:county:01001').alias('unit_a'),
        pl.lit('acs_industry_category').alias('unit_b_type'),
        pl.lit('feature:acs_industry_category:A').alias('unit_b'))
    denominators = aggregates.denominators.with_columns(
        pl.col('sum_exact').cast(pl.Float64).alias('mass'),
        pl.lit(None, dtype=pl.String).alias('sum_exact'),
        (pl.col('fractional_support_mass') * 0.25).alias('fractional_support_mass'),
        pl.lit('county').alias('unit_a_type'),
        pl.lit('geography:2025:county:01001').alias('unit_a'))
    result = {k: v.collect() for k, v in estimate(replace(
        aggregates, product=product, cells=cells, denominators=denominators)).items()}
    total = result['targets'].filter(pl.col('measure').eq('annual_average_total'))
    assert total['value'].item() == 10
    assert total['n_unweighted'].item() == 1
    pooled = result['support'].filter(pl.col('component_year').eq(0))
    assert pooled['fractional_support_mass'].to_list() == [0.25, 0.25]
    assert pooled['cell_weight_sum_exact'].null_count() == 2
    assert result['replicates']['numerator'].unique().item() == 10
    validate_auxiliary('target_support', result['support'])
    validate_auxiliary('replicate_estimates', result['replicates'])


def test_canonical_baseline_counts_and_unpooled_mass_are_preserved():
    from dataclasses import replace

    from embedding_data.acs_target_contract import PRODUCTS

    aggregates = aggregate_native(estimation_rows([record('20')]))
    product = next(p for p in PRODUCTS if p.view == 'canonical'
                   and p.family == 'staffing_pattern')
    keys = [pl.lit('naics_national_industry').alias('unit_a_type'),
            pl.lit('naics:2022:national_industry:111110').alias('unit_a')]
    cells = aggregates.cells.with_columns(
        *keys, pl.lit('soc_detailed').alias('unit_b_type'),
        pl.lit('soc:2018:detailed:11-1011').alias('unit_b'))
    denominators = aggregates.denominators.with_columns(
        *keys, pl.lit(5, dtype=pl.UInt64).alias('native_coverage_n'),
        pl.lit(40.).alias('native_coverage_mass'))
    result = estimate(replace(aggregates, product=product,
                              cells=cells, denominators=denominators))
    support = result['support'].collect()
    assert support['native_coverage_n'].to_list() == [5] * 6
    assert support['native_coverage_mass'].to_list() == [20.] * 6
    validate_auxiliary('target_support', support)


def test_every_output_defers_aggregate_evaluation_and_se_vectors_are_bounded(monkeypatch):
    from dataclasses import replace

    import embedding_data.acs_target_estimation as module

    aggregates = aggregate_native(estimation_rows([record('10'), record('30', b='B')]))
    reads = []
    vector_lengths = []
    original_se = module.replicate_se

    def observe_aggregate(frame):
        reads.append(frame.height)
        return frame

    def observe_se(full, replicates):
        vector_lengths.append(len(replicates))
        return original_se(full, replicates)

    monkeypatch.setattr(module, 'replicate_se', observe_se)
    aggregates = replace(aggregates, cells=aggregates.cells.map_batches(
        observe_aggregate, streamable=True))
    result = estimate(aggregates)
    assert not vector_lengths, 'SE finalization must wait for output collection'
    for name in ('targets', 'support', 'replicates'):
        previous_reads = len(reads)
        assert not result[name].collect().is_empty()
        assert len(reads) > previous_reads, f'{name} lost its deferred aggregate dependency'
    assert vector_lengths and set(vector_lengths) == {80}


def test_canonical_internal_baseline_is_consumed_before_source_lifetime_ends(tmp_path):

    from embedding_data.acs_target_contract import PRODUCTS
    from embedding_data.acs_target_membership import FamilyRows

    rows = estimation_rows([record('10', year=2023)])
    product = next(p for p in PRODUCTS if p.view == 'canonical'
                   and p.family == rows.product.family
                   and p.base_universe == rows.product.base_universe
                   and p.evidence_policy == rows.product.evidence_policy)
    coverage_type = pl.List(pl.Struct({'component_year': pl.Int64,
        'native_coverage_n': pl.UInt64, 'native_coverage_mass': pl.Float64}))
    metadata = [{'component_year': 0, 'native_coverage_n': 3, 'native_coverage_mass': 90.},
                {'component_year': 2023, 'native_coverage_n': 1, 'native_coverage_mass': 10.},
                {'component_year': 2024, 'native_coverage_n': 2, 'native_coverage_mass': 80.}]
    source = tmp_path / 'source.parquet'
    rows.members.with_columns(pl.lit(metadata, dtype=coverage_type)
        .alias('_canonical_native_coverage')).collect().write_parquet(source)
    canonical = FamilyRows(pl.scan_parquet(source), rows.diagnostics, product)
    aggregates = aggregate_native(canonical)
    source.unlink()
    baseline = aggregates.denominators.filter(pl.col('replicate') == 0).collect()
    assert dict(baseline.select('component_year', 'native_coverage_n').rows()) == {
        0: 3, 2023: 1, 2024: 2}
    support = estimate(aggregates)['support'].filter(pl.col('measure') == 'forward_share')\
        .collect()
    assert dict(support.select('component_year', 'native_coverage_mass').rows()) == {
        0: 45., 2023: 5., 2024: 40.}
    assert support.filter(pl.col('component_year') == 2024)['n_unweighted'].item() == 0
