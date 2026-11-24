'''Tests for the CPS value classes, the monthly panel and the person-month links.'''

import polars as pl
import pytest

from embedding_data import cps_flow_linkage
from embedding_data.cps_flow_linkage import (
    LINK_COLUMNS,
    classify_codes,
    count_value_classes,
    link_counts,
    monthly_links,
    monthly_panel,
)

INDUSTRY, OCCUPATION = 'cps_industry_category', 'cps_occupation_category'
UNIT_ROWS = [
    (INDUSTRY, '0170', 'mapped'), (INDUSTRY, '1370', 'mapped'),
    (INDUSTRY, '9920', 'no_naics_equivalent'), (INDUSTRY, '9890', 'special_military'),
    (OCCUPATION, '0010', 'mapped'), (OCCUPATION, '0020', 'mapped'),
    (OCCUPATION, '9830', 'no_soc_equivalent'), (OCCUPATION, '9840', 'special_military')]
MESSAGE_PARTS = ('0170', '1234', '9840', '9890', '9920', '9830', '170')


def units() -> pl.DataFrame:
    return pl.DataFrame(UNIT_ROWS, schema=['unit_type', 'code', 'status'], orient='row')


def codes(ind: list, occ: list | None = None, year: list | None = None) -> pl.LazyFrame:
    '''A small typed frame of delivered codes.'''
    return pl.LazyFrame({
        'YEAR': year or [2025] * len(ind), 'IND': ind,
        'OCC': occ or ['0010'] * len(ind)},
        schema={'YEAR': pl.Int64, 'IND': pl.String, 'OCC': pl.String})


def classes(frame: pl.LazyFrame, field: str, dimension: str) -> list:
    return classify_codes(frame, field, dimension, units()).collect()[f'{field}_class'].to_list()


def test_each_value_class_per_field():
    frame = codes(['0170', '0000', '9890'], ['9840', '0010', '0000'])
    assert classes(frame, 'IND', 'industry') == ['mapped', 'not_in_universe', 'special']
    assert classes(frame, 'OCC', 'occupation') == ['special', 'mapped', 'not_in_universe']
    with pytest.raises(ValueError):
        classes(codes(['9840']), 'IND', 'industry')
    with pytest.raises(ValueError):
        classes(codes(['1234']), 'IND', 'industry')
    with pytest.raises(ValueError):
        classes(codes(['0170'], ['1234']), 'OCC', 'occupation')


def test_a_special_belongs_to_its_own_dimension_only():
    with pytest.raises(ValueError):
        classes(codes(['0170'], ['9890']), 'OCC', 'occupation')
    with pytest.raises(ValueError):
        classes(codes(['9840']), 'IND', 'industry')


def test_a_code_on_the_other_dimension_list_fails():
    with pytest.raises(ValueError):
        classes(codes(['0170'], ['0170']), 'OCC', 'occupation')
    with pytest.raises(ValueError):
        classes(codes(['0010']), 'IND', 'industry')


@pytest.mark.parametrize('value', ['170', ' 170', '0170 '])
def test_unpadded_code_is_unparseable(value):
    with pytest.raises(ValueError):
        classes(codes(['0170', value]), 'IND', 'industry')


@pytest.mark.parametrize('value', ['', '00170', '17O0', '0170\n', None, '0000 ', ' 9890'])
def test_other_malformed_or_null_codes_are_unparseable(value):
    with pytest.raises(ValueError):
        classes(codes(['0170', value]), 'IND', 'industry')


def test_delivered_no_equivalent_statuses_fail():
    with pytest.raises(ValueError):
        classes(codes(['9920']), 'IND', 'industry')
    with pytest.raises(ValueError):
        classes(codes(['0170'], ['9830']), 'OCC', 'occupation')


def test_each_failure_has_a_fixed_message_without_the_value():
    for value in ('1234', '170', '9920'):
        with pytest.raises(ValueError) as caught:
            classes(codes([value]), 'IND', 'industry')
        assert not any(part in str(caught.value) for part in MESSAGE_PARTS)
    assert str(pytest.raises(ValueError, classes, codes(['1234']), 'IND', 'industry')
               .value) != str(pytest.raises(ValueError, classes, codes(['9920']), 'IND',
                                            'industry').value)


def test_the_check_runs_on_every_row_whatever_is_read_later():
    frame = codes(['0170', '1234'], ['0010', '0010'])
    checked = classify_codes(frame, 'IND', 'industry', units())
    with pytest.raises(ValueError):
        checked.select('OCC').collect()
    with pytest.raises(ValueError):
        checked.filter(pl.col('IND') == '0170').collect()
    with pytest.raises(ValueError):
        checked.head(1).collect()


def test_class_column_follows_the_input_columns():
    frame = codes(['0170'], ['0010'])
    assert classify_codes(frame, 'IND', 'industry', units()).collect_schema().names() == [
        'YEAR', 'IND', 'OCC', 'IND_class']


def test_value_class_counts_by_field_file_and_year():
    frame = codes(['0170', '0000', '9890', '9890', '0170', '9890'],
                  ['0010', '9840', '0020', '0000', '9840', '9840'],
                  [2025, 2025, 2025, 2026, 2026, 2026])
    fields = {'IND': 'industry', 'OCC': 'occupation'}
    assert count_value_classes(frame, 'monthly', fields, units()) == {
        'monthly/IND': {'mapped': 2, 'not_in_universe': 1, 'special': 3,
                        'special_by_year': {'2025': 1, '2026': 2}},
        'monthly/OCC': {'mapped': 2, 'not_in_universe': 1, 'special': 3,
                        'special_by_year': {'2025': 1, '2026': 2}}}
    assert list(count_value_classes(frame, 'asec', {'IND': 'industry'}, units())) == ['asec/IND']


def test_value_class_counts_with_no_special_are_zero():
    found = count_value_classes(codes(['0170']), 'monthly', {'IND': 'industry'}, units())
    assert found == {'monthly/IND': {'mapped': 1, 'not_in_universe': 0, 'special': 0,
                                     'special_by_year': {}}}


def test_value_class_counts_refuse_a_failing_value():
    with pytest.raises(ValueError):
        count_value_classes(codes(['0170', '1234']), 'monthly', {'IND': 'industry'}, units())


# The monthly panel and the links.

SCHEMA = {
    'YEAR': pl.Int64, 'MONTH': pl.Int64, 'CPSIDV': pl.Int64, 'CPSID': pl.Int64,
    'CPSIDP': pl.Int64, 'MISH': pl.Int64, 'EMPSTAT': pl.Int64, 'IND': pl.String,
    'OCC': pl.String, 'QEMPSTAT': pl.Int64, 'QIND': pl.Int64, 'QOCC': pl.Int64,
    'EMPSAME': pl.Int64, 'ACTSAME': pl.Int64, 'ASECFLAG': pl.Int64, 'LNKFW1MWT': pl.Float64}


def person(year: int, month: int, cpsidv: int, mish: int, **fields) -> dict:
    '''One monthly row; `CPSIDP` follows `CPSIDV` unless it is given.'''
    row = {
        'YEAR': year, 'MONTH': month, 'CPSIDV': cpsidv, 'CPSID': cpsidv * 10,
        'CPSIDP': cpsidv, 'MISH': mish, 'EMPSTAT': 10, 'IND': '0170', 'OCC': '0010',
        'QEMPSTAT': 0, 'QIND': 0, 'QOCC': 0, 'EMPSAME': 2, 'ACTSAME': 1, 'ASECFLAG': None,
        'LNKFW1MWT': 1.5}
    return {**row, **fields}


def frame(*rows: dict) -> pl.LazyFrame:
    return pl.LazyFrame(list(rows), schema=SCHEMA)


def links_of(*rows: dict) -> pl.DataFrame:
    return monthly_links(monthly_panel(frame(*rows))).collect()


def test_the_panel_adds_source_row_and_month_index():
    panel = monthly_panel(frame(
        person(2025, 1, 1, 1), person(2025, 12, 2, 2), person(2026, 1, 3, 3))).collect()
    assert panel.columns == [*SCHEMA, 'source_row', 'month_index']
    assert panel.schema['source_row'] == pl.UInt64
    assert panel['source_row'].to_list() == [0, 1, 2]
    assert panel['month_index'].to_list() == [2025 * 12, 2025 * 12 + 11, 2026 * 12]
    assert panel.height == 3


def test_a_row_with_a_valid_edge_value_passes():
    rows = [person(2025, 1, 1, 1), person(2025, 1, 2, 8), person(2026, 9, 3, 4, ASECFLAG=2)]
    assert monthly_panel(frame(*rows)).collect().height == 3


@pytest.mark.parametrize('field, value', [
    ('YEAR', 2024), ('ASECFLAG', 1), ('CPSIDV', None), ('MISH', None), ('EMPSTAT', None),
    ('MISH', 0), ('MISH', 9), ('YEAR', None), ('MONTH', None)])
def test_each_panel_refusal(field, value):
    rows = [person(2025, 2, 1, 1), person(2025, 2, 2, 1, **{field: value})]
    with pytest.raises(ValueError) as caught:
        monthly_panel(frame(*rows))
    assert 'CPSIDV 1' not in str(caught.value)


def test_each_panel_refusal_has_its_own_message():
    bad = [{'YEAR': 2024}, {'ASECFLAG': 1}, {'CPSIDV': None}, {'MISH': 9}]
    seen = set()
    for fields in bad:
        with pytest.raises(ValueError) as caught:
            monthly_panel(frame(person(2025, 2, 1, 1, **fields)))
        seen.add(str(caught.value))
    assert len(seen) == 4


def test_pre_2025_sample_is_refused_and_no_december_pair_forms():
    december = person(2024, 12, 7, 3)
    january = person(2025, 1, 7, 4)
    with pytest.raises(ValueError):
        monthly_panel(frame(december, january))
    links = links_of(january, person(2025, 2, 7, 5))
    assert '2024-12' not in links['month_a'].to_list()
    assert links.height == 0


def test_duplicate_cpsidv_within_a_month_fails():
    with pytest.raises(ValueError):
        monthly_panel(frame(person(2025, 2, 5, 1), person(2025, 2, 5, 2, CPSIDP=99)))


def test_the_same_cpsidv_in_different_months_or_years_is_not_a_repeat():
    rows = [person(2025, 1, 5, 1), person(2025, 2, 5, 2), person(2026, 1, 5, 5)]
    assert monthly_panel(frame(*rows)).collect().height == 3


def test_asecflag_one_is_refused_and_null_or_two_pass():
    with pytest.raises(ValueError):
        monthly_panel(frame(person(2025, 2, 1, 1, ASECFLAG=1)))
    rows = [person(2025, 2, 1, 1), person(2025, 2, 2, 1, ASECFLAG=2)]
    assert monthly_panel(frame(*rows)).collect().height == 2


def test_the_panel_check_runs_at_the_call():
    with pytest.raises(ValueError):
        monthly_panel(frame(person(2024, 12, 1, 1)))


def test_one_month_link_carries_the_columns_of_both_months():
    earlier = person(2025, 2, 9, 1, CPSID=90, CPSIDP=91, EMPSTAT=10, IND='0170', OCC='0010',
                     QEMPSTAT=1, QIND=2, QOCC=3, EMPSAME=1, ACTSAME=2)
    later = person(2025, 3, 9, 2, CPSID=95, CPSIDP=96, EMPSTAT=12, IND='1370', OCC='0020',
                   QEMPSTAT=4, QIND=5, QOCC=6, EMPSAME=96, ACTSAME=97)
    other = person(2025, 3, 3, 1)
    links = links_of(other, earlier, later)
    assert links.columns == list(LINK_COLUMNS)
    assert len(LINK_COLUMNS) == 24
    assert links.rows(named=True) == [{
        'CPSIDV': 9, 'CPSID': 90, 'source_row_a': 1, 'source_row_b': 2, 'month_a': '2025-02',
        'month_b': '2025-03', 'link_type': 'one_month', 'mish_a': 1, 'mish_b': 2,
        'empstat_a': 10, 'empstat_b': 12, 'ind_a': '0170', 'ind_b': '1370', 'occ_a': '0010',
        'occ_b': '0020', 'qempstat_a': 1, 'qempstat_b': 4, 'qind_a': 2, 'qind_b': 5,
        'qocc_a': 3, 'qocc_b': 6, 'empsame_b': 96, 'actsame_b': 97, 'cpsidp_a': 91}]
    assert links.schema['source_row_a'] == pl.UInt64


def test_one_month_link_needs_mish_plus_one_and_refuses_4_to_5():
    assert links_of(person(2025, 2, 1, 1), person(2025, 3, 1, 2)).height == 1
    assert links_of(person(2025, 2, 1, 4), person(2025, 3, 1, 5)).height == 0
    assert links_of(person(2025, 2, 1, 8), person(2025, 3, 1, 1)).height == 0


@pytest.mark.parametrize('earlier, later, forms', [
    (1, 2, True), (2, 3, True), (3, 4, True), (4, 5, False), (5, 6, True), (6, 7, True),
    (7, 8, True), (8, 1, False), (1, 1, False), (2, 1, False), (1, 3, False), (3, 2, False),
    (5, 7, False), (8, 5, False)])
def test_every_mish_pair_in_adjacent_months(earlier, later, forms):
    links = links_of(person(2025, 4, 1, earlier), person(2025, 5, 1, later))
    assert links.height == int(forms)


@pytest.mark.parametrize('first, second', [
    ((2025, 1), (2025, 3)), ((2025, 1), (2026, 1)), ((2025, 3), (2025, 2)),
    ((2025, 1), (2025, 11)), ((2025, 11), (2026, 1)),
    ((2026, 9), (2026, 11)), ((2025, 8), (2025, 10))])
def test_no_other_gap_forms_a_link(first, second):
    for rise in (1, 2):
        rows = [person(*first, 1, 1), person(*second, 1, 1 + rise)]
        assert links_of(*rows).height == 0


def test_the_year_boundary_links():
    links = links_of(person(2025, 12, 1, 2), person(2026, 1, 1, 3))
    assert links['month_a'].to_list() == ['2025-12']
    assert links['month_b'].to_list() == ['2026-01']
    assert links['link_type'].to_list() == ['one_month']


def test_adjacent_months_around_the_october_gap_link():
    assert links_of(person(2025, 8, 1, 1), person(2025, 9, 1, 2))['month_b'].to_list() == [
        '2025-09']
    assert links_of(person(2025, 11, 1, 1), person(2025, 12, 1, 2))['month_b'].to_list() == [
        '2025-12']


def test_september_to_november_two_month_link():
    links = links_of(person(2025, 9, 4, 1), person(2025, 11, 4, 3))
    assert links['link_type'].to_list() == ['two_month']
    assert links['month_a'].to_list() == ['2025-09']
    assert links['month_b'].to_list() == ['2025-11']
    assert links['mish_a'].to_list() == [1]
    assert links['mish_b'].to_list() == [3]


def test_the_two_month_link_has_no_four_eight_exclusion():
    links = links_of(person(2025, 9, 4, 4), person(2025, 11, 4, 6))
    assert links['link_type'].to_list() == ['two_month']


def test_september_to_november_mish_plus_one_forms_no_link():
    rows = [person(2025, 9, 4, 1), person(2025, 11, 4, 2)]
    assert links_of(*rows).height == 0
    counts = link_counts(monthly_panel(frame(*rows)))
    assert counts.rows(named=True) == [{
        'month_a': '2025-09', 'month_b': '2025-11', 'link_type': 'two_month', 'cpsidv': 0,
        'cpsidp': 0, 'other_gap_matches': 1}]


def test_links_sort_by_source_rows_and_never_multiply():
    rows = [person(2025, 3, 2, 2), person(2025, 3, 1, 2), person(2025, 2, 2, 1),
            person(2025, 2, 1, 1), person(2025, 4, 1, 3)]
    links = links_of(*rows)
    assert links['CPSIDV'].to_list() == [1, 2, 1]
    assert links['source_row_a'].to_list() == [1, 2, 3]
    assert links['source_row_b'].to_list() == [4, 0, 1]
    assert links['link_type'].to_list() == ['one_month'] * 3


def test_link_counts_report_cpsidv_and_cpsidp_by_month_pair():
    rows = [
        person(2025, 2, 1, 1, CPSIDP=11), person(2025, 3, 1, 2, CPSIDP=12),
        person(2025, 2, 2, 1, CPSIDP=21), person(2025, 3, 2, 2, CPSIDP=21),
        person(2025, 4, 2, 3, CPSIDP=22), person(2025, 4, 3, 1, CPSIDP=21)]
    counts = link_counts(monthly_panel(frame(*rows)))
    assert counts.columns == list(cps_flow_linkage.COUNT_COLUMNS)
    assert counts.rows(named=True) == [
        {'month_a': '2025-02', 'month_b': '2025-03', 'link_type': 'one_month', 'cpsidv': 2,
         'cpsidp': 1, 'other_gap_matches': 0},
        {'month_a': '2025-03', 'month_b': '2025-04', 'link_type': 'one_month', 'cpsidv': 1,
         'cpsidp': 0, 'other_gap_matches': 0}]
    assert counts.schema['cpsidv'] == pl.Int64


def test_the_cpsidp_count_applies_the_mish_rule_and_needs_no_cpsidv_match():
    rows = [person(2025, 2, 1, 4, CPSIDP=7), person(2025, 3, 1, 5, CPSIDP=7),
            person(2025, 2, 2, 1, CPSIDP=8), person(2025, 3, 3, 2, CPSIDP=8)]
    counts = link_counts(monthly_panel(frame(*rows))).row(0, named=True)
    assert (counts['cpsidv'], counts['cpsidp'], counts['other_gap_matches']) == (0, 1, 1)


def test_other_gap_matches_count_failed_cpsidv_matches_in_candidate_month_pairs():
    rows = [person(2025, 2, 1, 4), person(2025, 3, 1, 5),
            person(2025, 2, 2, 8), person(2025, 3, 2, 1),
            person(2025, 2, 3, 1), person(2025, 3, 3, 2),
            person(2025, 2, 4, 1), person(2025, 3, 4, 3),
            person(2025, 5, 3, 4)]
    counts = link_counts(monthly_panel(frame(*rows)))
    first = counts.row(0, named=True)
    assert (first['month_a'], first['cpsidv'], first['other_gap_matches']) == ('2025-02', 1, 3)
    assert counts.height == 1


def test_link_counts_list_each_candidate_month_pair_present_in_the_panel():
    rows = [person(2025, 8, 1, 1), person(2025, 9, 1, 2), person(2025, 11, 1, 3),
            person(2025, 12, 1, 4), person(2025, 12, 2, 2), person(2026, 1, 2, 3)]
    counts = link_counts(monthly_panel(frame(*rows)))
    assert counts.select('month_a', 'month_b', 'link_type').rows() == [
        ('2025-08', '2025-09', 'one_month'), ('2025-09', '2025-11', 'two_month'),
        ('2025-11', '2025-12', 'one_month'), ('2025-12', '2026-01', 'one_month')]
    assert counts['cpsidv'].to_list() == [1, 0, 1, 1]
    assert counts['other_gap_matches'].to_list() == [0, 1, 0, 0]
    only_gap = link_counts(monthly_panel(frame(person(2025, 9, 1, 1), person(2025, 11, 2, 1))))
    assert only_gap['link_type'].to_list() == ['two_month']
    assert link_counts(monthly_panel(frame(person(2025, 1, 1, 1), person(2025, 3, 1, 3)))
                       ).height == 0


def test_link_counts_of_an_empty_panel_are_empty():
    counts = link_counts(monthly_panel(frame()))
    assert counts.height == 0
    assert counts.columns == list(cps_flow_linkage.COUNT_COLUMNS)
