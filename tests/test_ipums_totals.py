from decimal import Decimal

import polars as pl
import pytest

from embedding_data.ipums_totals import acs_employment, compare_levels, cps_employment

def test_acs_civilian_annual_average_and_diagnostics():
    frame = pl.DataFrame({'YEAR': [2023] * 7 + [2024], 'STATEFIP': ['01'] * 8,
                          'AGE': [30, 30, 30, 30, 15, 30, 30, 30],
                          'EMPSTAT': [1] * 8, 'EMPSTATD': [10, 11, 12, 13, 10, 14, 99, 10],
                          'PERWT': [Decimal(v) for v in ['20', '30', '50', '900', '800',
                                                         '700', '600', '140']],
                          'QEMPSTAT': [1] * 8})
    result = acs_employment(frame.lazy())
    annual = result.filter(pl.col('period').eq('annual')).sort('year')
    assert annual['measured'].to_list() == [100.0, 140.0]
    assert annual['state_fips'].to_list() == ['01', '01']
    assert annual['unexpected_status_rows'].to_list() == [1, 0]
    assert annual['unexpected_statuses'].to_list() == [
        [{'field': 'EMPSTATD', 'value': '99'}], []]
    assert result.filter(pl.col('period').eq('annual_average'))['measured'].item() == 120
    assert annual['eligible_rows'].to_list() == [3, 1]


def cps_frame():
    return pl.DataFrame({'YEAR': [2025] * 5, 'MONTH': [9] * 5, 'AGE': [16, 30, 30, 30, 15],
                         'EMPSTAT': [10, 12, 20, 1, 10],
                         'WTFINL': [Decimal(v) for v in ['750', '1250', '99', '999', '888']]})


def reference(levels):
    return levels.select('year', 'month', 'period', 'period_start', 'period_end', 'period_years',
                         'universe', 'geography_basis', 'geography_scope').with_columns(
        published=pl.lit(1.9), units=pl.lit('thousands of persons'),
        footnotes=pl.lit('[{"text":"mutable snapshot"}]'))


def test_cps_universe_and_thousands_comparison():
    levels = cps_employment(cps_frame().lazy())
    assert levels['measured'].item() == 2000
    result = compare_levels(levels, reference(levels), ['year', 'month'])
    assert result['published'].item() == 1900
    assert result['gap'].item() == 100
    assert result['relative_gap'].item() == 100 / 1900
    assert result['comparison_status'].item() == 'matched'
    assert result['footnotes'].item() == '[{"text":"mutable snapshot"}]'


@pytest.mark.parametrize(('value', 'reason'), [(0.0, 'zero_published'),
                                               (None, 'missing_published')])
def test_zero_missing_and_unmatched_levels(value, reason):
    levels = cps_employment(cps_frame().lazy())
    published = reference(levels).with_columns(published=pl.lit(value, dtype=pl.Float64))
    result = compare_levels(levels, published, ['year', 'month'])
    assert result['relative_gap'].item() is None
    assert result['relative_gap_reason'].item() == reason
    unmatched = compare_levels(levels, published.with_columns(month=pl.lit(10, dtype=pl.Int64)),
                               ['year', 'month'])
    assert set(unmatched['comparison_status']) == {'measured_only', 'published_only'}
    assert unmatched['relative_gap'].null_count() == 2


@pytest.mark.parametrize('column', ['period', 'universe', 'geography_basis', 'geography_scope'])
def test_incompatible_metadata_prevents_gap(column):
    levels = cps_employment(cps_frame().lazy())
    published = reference(levels).with_columns(pl.lit('incompatible').alias(column))
    result = compare_levels(levels, published, ['year', 'month'])
    assert result['comparison_status'].item() == 'incompatible_metadata'
    assert result['gap'].item() is None
    with pytest.raises(ValueError, match='metadata'):
        compare_levels(levels, published.drop(column), ['year', 'month'])


def test_float_weights_rejected_and_missing_weight_not_zero():
    with pytest.raises(ValueError, match='Decimal'):
        cps_employment(cps_frame().with_columns(pl.col('WTFINL').cast(pl.Float64)).lazy())
    levels = cps_employment(cps_frame().with_columns(
        pl.when(pl.col('EMPSTAT').eq(10)).then(None).otherwise(pl.col('WTFINL')).alias('WTFINL')
    ).lazy())
    assert levels['measured'].item() is None
    assert levels['missing_weight_rows'].item() == 1


def test_duplicate_comparison_keys_rejected():
    levels = cps_employment(cps_frame().lazy())
    with pytest.raises(ValueError, match='unique'):
        compare_levels(levels, pl.concat([reference(levels)] * 2), ['year', 'month'])


def test_acs_territory_scope_zero_and_missing_year_components():
    frame = pl.DataFrame({'YEAR': [2023, 2025, 2023], 'STATEFIP': [1, 1, 72],
                          'AGE': [30, 30, 30], 'EMPSTAT': [1, 1, 2],
                          'EMPSTATD': [10, 10, 20], 'PERWT': [Decimal(100)] * 3})
    result = acs_employment(frame.lazy())
    pooled = result.filter(pl.col('period').eq('annual_average'))
    assert pooled['period_years'].to_list() == [[2023, 2025], [2023, 2025]]
    assert pooled['observed_years'].to_list() == [[2023, 2025], [2023]]
    assert pooled['measured'].to_list() == [100, None]
    annual_pr = result.filter(pl.col('state_fips').eq('72').and_(pl.col('period').eq('annual')))
    assert annual_pr['measured'].item() == 0
    assert pooled['geography_scope'].to_list() == ['50_states_dc', 'outside_50_states_dc']
    published = pooled.rename({'measured': 'published'}).select(
        'state_fips', 'period', 'period_start', 'period_end', 'period_years', 'universe',
        'geography_basis', 'geography_scope', 'published', 'units')
    comparison = compare_levels(pooled, published, ['state_fips', 'period'])
    assert comparison['comparison_status'].to_list() == ['matched', 'outside_scope']
    assert comparison['gap'].to_list() == [0, None]


def test_cps_reproducibility_and_empty_schema():
    original = cps_frame()
    first = cps_employment(original.lazy())
    assert first.equals(cps_employment(original.reverse().lazy()))
    partitioned = pl.concat([original[:2], original[2:]], rechunk=False)
    assert first.equals(cps_employment(partitioned.lazy()))
    empty = cps_employment(original.clear().lazy())
    assert empty.height == 0
    assert first.schema == empty.schema == {
        'year': pl.Int64, 'month': pl.Int64, 'state_fips': pl.String,
        'period': pl.String, 'period_start': pl.Int64, 'period_end': pl.Int64,
        'period_years': pl.List(pl.Int64), 'observed_years': pl.List(pl.Int64),
        'missing_years': pl.List(pl.Int64),
        'units': pl.String, 'universe': pl.String, 'geography_basis': pl.String,
        'geography_scope': pl.String, 'weight': pl.String, 'measured': pl.Float64,
        'weight_sum_exact': pl.String, 'annual_divisor': pl.UInt32,
        'rows': pl.UInt64, 'eligible_rows': pl.UInt64, 'missing_weight_rows': pl.UInt64,
        'unexpected_status_rows': pl.UInt64, 'military_rows': pl.UInt64,
        'under16_rows': pl.UInt64, 'missing_age_rows': pl.UInt64,
        'unexpected_statuses': pl.List(pl.Struct({'field': pl.String, 'value': pl.String})),
    }


def test_comparison_component_years_are_required_and_must_match():
    levels = cps_employment(cps_frame().lazy())
    published = reference(levels).with_columns(period_years=pl.lit([2024]))
    assert compare_levels(levels, published, ['year', 'month'])['gap'].item() is None


@pytest.mark.parametrize('month', [0, 13, None])
def test_invalid_or_missing_cps_period_fails(month):
    with pytest.raises(ValueError, match='period|month'):
        cps_employment(cps_frame().with_columns(MONTH=pl.lit(month, dtype=pl.Int64)).lazy())


def test_null_status_is_diagnostic_and_null_metadata_is_not_comparable():
    levels = cps_employment(cps_frame().with_columns(
        EMPSTAT=pl.lit(None, dtype=pl.Int64)).lazy())
    assert levels['unexpected_status_rows'].item() == 5
    assert levels['unexpected_statuses'].to_list() == [[{'field': 'EMPSTAT', 'value': None}]]
    assert levels['measured'].item() == 0
    published = reference(levels).with_columns(universe=pl.lit(None, dtype=pl.String))
    assert compare_levels(levels, published, ['year', 'month'])['comparison_status'].item() == (
        'incompatible_metadata')


def test_partial_state_annual_average_is_missing_not_reweighted():
    frame = pl.DataFrame({'YEAR': [2023, 2024], 'STATEFIP': ['01', '02'],
                          'AGE': [30, 30], 'EMPSTAT': [1, 1], 'EMPSTATD': [10, 10],
                          'PERWT': [Decimal(100), Decimal(140)]})
    pooled = acs_employment(frame.lazy()).filter(pl.col('period').eq('annual_average'))
    assert pooled['measured'].to_list() == [None, None]
    assert pooled['annual_divisor'].to_list() == [2, 2]
    assert pooled['period_years'].to_list() == [[2023, 2024], [2023, 2024]]
    assert pooled['missing_years'].to_list() == [[2024], [2023]]


def test_published_only_rows_keep_canonical_context_and_original_units():
    measured = cps_employment(cps_frame().lazy())
    published = reference(measured)
    result = compare_levels(measured.clear(), published, ['year', 'month'])
    assert result['units'].item() == 'persons'
    assert result['period'].item() == 'monthly'
    assert result['universe'].item() == 'civilian_noninstitutional_employed_age_16_plus'
    assert result['published_original_units'].item() == 'thousands of persons'


@pytest.mark.parametrize('general_status', [99, None])
def test_acs_unexpected_general_status_retains_field_and_value(general_status):
    frame = pl.DataFrame({'YEAR': [2023, 2023], 'STATEFIP': ['01', '01'],
                          'AGE': [30, 30], 'EMPSTAT': [general_status, 1],
                          'EMPSTATD': [10, 10],
                          'PERWT': [Decimal('900.0000'), Decimal('100.0001')]},
                         schema_overrides={'EMPSTAT': pl.Int64})
    result = acs_employment(frame.lazy())
    assert result['unexpected_status_rows'].to_list() == [1, 1]
    value = None if general_status is None else '99'
    assert result['unexpected_statuses'].to_list() == [
        [{'field': 'EMPSTAT', 'value': value}], [{'field': 'EMPSTAT', 'value': value}]]
    assert result['eligible_rows'].to_list() == [1, 1]
    assert result['measured'].to_list() == [100.0001, 100.0001]
    assert result['weight_sum_exact'].to_list() == ['100.0001', '100.0001']


def test_acs_status_diagnostics_distinguish_both_fields_and_count_rows_once():
    frame = pl.DataFrame({'YEAR': [2023, 2023, 2024], 'STATEFIP': ['01'] * 3,
                          'AGE': [30] * 3, 'EMPSTAT': [99, 1, None],
                          'EMPSTATD': [99, None, 10], 'PERWT': [Decimal('100')] * 3})
    result = acs_employment(frame.lazy())
    annual = result.filter(pl.col('period').eq('annual')).sort('year')
    assert annual['unexpected_status_rows'].to_list() == [2, 1]
    assert annual['unexpected_statuses'].to_list() == [
        [{'field': 'EMPSTAT', 'value': '99'}, {'field': 'EMPSTATD', 'value': None},
         {'field': 'EMPSTATD', 'value': '99'}], [{'field': 'EMPSTAT', 'value': None}]]
    pooled = result.filter(pl.col('period').eq('annual_average'))
    assert pooled['unexpected_status_rows'].item() == 3
    assert pooled['unexpected_statuses'].to_list() == [[
        {'field': 'EMPSTAT', 'value': None}, {'field': 'EMPSTAT', 'value': '99'},
        {'field': 'EMPSTATD', 'value': None}, {'field': 'EMPSTATD', 'value': '99'}]]
    assert result['eligible_rows'].to_list() == [0, 0, 0]
    assert result['measured'].to_list() == [0, 0, 0]
