'''Tests for the Census list readers and the NAICS candidate sets of the CPS job flows.'''

from pathlib import Path

import polars as pl
import pytest
from cps_flow_fixtures import (
    INDUSTRY_PREAMBLE,
    INDUSTRY_SHEET,
    OCCUPATION_PREAMBLE,
    OCCUPATION_SHEET,
    industry_list_workbook,
    occupation_list_workbook,
    tree_frames,
)

from embedding_data import ipums_references
from embedding_data.cps_flow_lists import (
    ListRow,
    membership_types,
    naics_candidates,
    read_industry_list,
    read_occupation_list,
)

CLASSIFICATION = Path(__file__).parent / 'fixtures' / 'acs_mapping' / 'classification'
INDUSTRY_FIRST_ROW = len(INDUSTRY_PREAMBLE) + 1
OCCUPATION_FIRST_ROW = len(OCCUPATION_PREAMBLE) + 1
INDUSTRY_LOCATOR = f'census_industry_2022:{INDUSTRY_SHEET}!B:E:row='
OCCUPATION_LOCATOR = f'census_occupation_2018:{OCCUPATION_SHEET}!B:D:row='


def industry_row(code, expression, title='A title'):
    return [None, title, None, code, expression]


def occupation_row(code, token, title='A title'):
    return [None, title, code, token]


def industry_rows(file, rows):
    industry_list_workbook(file, rows)
    return read_industry_list(file)


def occupation_rows(file, rows):
    occupation_list_workbook(file, rows)
    return read_occupation_list(file)


def test_industry_reader_collapses_section_and_whitespace_duplicates(tmp_path):
    section = ['Construction', None, None, '0770', '23']
    detail = industry_row('0770', '23', 'Construction (incidental cleaning)')
    first = industry_row('7570', '55', 'Management of companies and enterprises')
    second = industry_row('7570', '55 ', 'Management of companies and enterprises ')
    rows = industry_rows(tmp_path / 'list.xlsx', [section, detail, first, second])
    assert rows == [
        ListRow('0770', 'Construction (incidental cleaning)', '23',
                f'{INDUSTRY_LOCATOR}{INDUSTRY_FIRST_ROW + 1}'),
        ListRow('7570', 'Management of companies and enterprises', '55',
                f'{INDUSTRY_LOCATOR}{INDUSTRY_FIRST_ROW + 2}')]


def test_industry_reader_returns_266_codes_from_268_rows(tmp_path):
    plain = [industry_row(f'{1000 + i:04d}', '111') for i in range(264)]
    rows = [industry_row('7570', '55'), *plain, industry_row('7570', '55'),
            ['Construction', None, None, '0770', '23'], industry_row('0770', '23')]
    assert len(rows) == 268
    result = industry_rows(tmp_path / 'list.xlsx', rows)
    codes = [row.code for row in result]
    assert len(codes) == 266 and codes == sorted(set(codes))


def test_industry_reader_keeps_the_military_and_unemployed_rows(tmp_path):
    military = ['9670', '9680', '9690', '9770', '9780', '9790', '9870']
    rows = industry_rows(tmp_path / 'list.xlsx', [
        *[industry_row(code, 'pt. 92811') for code in military],
        industry_row('9920', '  ', 'Unemployed, last worked 5 years ago')])
    by_code = {row.code: row for row in rows}
    assert [by_code[code].expression for code in military] == ['pt. 92811'] * 7
    assert by_code['9920'].expression is None


def test_industry_reader_sorts_and_strips_the_code_title_and_expression(tmp_path):
    rows = industry_rows(tmp_path / 'list.xlsx', [
        industry_row(' 0190 ', ' 1131, 1132 ', ' Forestry except logging  '),
        industry_row('0170', '111', 'Crop production')])
    assert [(row.code, row.title, row.expression) for row in rows] == [
        ('0170', 'Crop production', '111'),
        ('0190', 'Forestry except logging', '1131, 1132')]


def test_industry_reader_ignores_rows_without_a_four_digit_code(tmp_path):
    rows = industry_rows(tmp_path / 'list.xlsx', [
        ['Agriculture', None, None, '0170-0490', '11-21'], industry_row('170', '111'),
        industry_row('01700', '111'), industry_row('01A0', '111'), industry_row(None, '111'),
        industry_row('0170', '111')])
    assert [row.code for row in rows] == ['0170']


def test_industry_reader_takes_the_title_from_the_row_that_has_one(tmp_path):
    rows = industry_rows(tmp_path / 'list.xlsx', [
        industry_row('0770', '23', None), industry_row('0770', '23', 'Construction'),
        industry_row('0770', '23', None)])
    assert rows[0].title == 'Construction'
    assert rows[0].locator == f'{INDUSTRY_LOCATOR}{INDUSTRY_FIRST_ROW + 1}'


def test_industry_reader_agrees_on_titles_after_whitespace_collapse(tmp_path):
    rows = industry_rows(tmp_path / 'list.xlsx', [
        industry_row('0770', '23', 'Support  activities '),
        industry_row('0770', '23', 'Support activities')])
    assert rows[0].title == 'Support  activities'


@pytest.mark.parametrize('first,second', [
    (industry_row('1270', '3118 exc. 311811'), industry_row('1270', '3118')),
    (industry_row('9920', None), industry_row('9920', '23')),
    (industry_row('1270', '23', 'One title'), industry_row('1270', '23', 'Another title'))])
def test_industry_reader_refuses_a_code_whose_rows_disagree(tmp_path, first, second):
    industry_list_workbook(tmp_path / 'list.xlsx', [first, second])
    with pytest.raises(ValueError):
        read_industry_list(tmp_path / 'list.xlsx')


def test_industry_reader_refuses_a_code_with_no_title(tmp_path):
    industry_list_workbook(tmp_path / 'list.xlsx', [industry_row('0770', '23', None)])
    with pytest.raises(ValueError):
        read_industry_list(tmp_path / 'list.xlsx')


def test_industry_reader_refuses_a_list_with_no_data_rows(tmp_path):
    industry_list_workbook(tmp_path / 'list.xlsx', [['Agriculture', None, None, '0170-0490']])
    with pytest.raises(ValueError):
        read_industry_list(tmp_path / 'list.xlsx')


@pytest.mark.parametrize('sheet', ['Fixture', '2022 Census Ind Code List'])
def test_industry_reader_requires_the_exact_sheet_name(tmp_path, sheet):
    industry_list_workbook(tmp_path / 'list.xlsx', [industry_row('0170', '111')], sheet=sheet)
    with pytest.raises(ValueError):
        read_industry_list(tmp_path / 'list.xlsx')


def test_industry_reader_agrees_with_parse_industry_list():
    file = CLASSIFICATION / 'census_industry_2022.xlsx'
    rows = read_industry_list(file)
    assert len(rows) == 266
    assert [row.code for row in rows] == sorted(row.code for row in rows)
    reference = ipums_references.parse_industry_list(file, 2022)
    ours = [(row.code, row.title) for row in rows if row.code != '9920']
    assert ours == sorted(reference.iter_rows())
    unemployed = next(row for row in rows if row.code == '9920')
    assert unemployed.expression is None


def test_industry_reader_reads_the_real_expressions_of_the_fixture_workbook():
    rows = {row.code: row for row in
            read_industry_list(CLASSIFICATION / 'census_industry_2022.xlsx')}
    assert sum(' exc. ' in (row.expression or '') for row in rows.values()) == 19
    assert rows['0770'].expression == '23'
    assert {rows[code].expression for code in
            ['9670', '9680', '9690', '9770', '9780', '9790', '9870']} == {'pt. 92811'}
    assert rows['6481'].expression == '5131 exc. 51311'


def test_occupation_reader_reads_x_and_none_tokens(tmp_path):
    rows = occupation_rows(tmp_path / 'list.xlsx', [
        occupation_row('0010', '11-1011', 'Chief executives'),
        occupation_row('1100', '13-20XX', 'Financial specialists'),
        occupation_row('8990', '51-4XXX', 'Metalworkers'),
        occupation_row('9830', 'none', 'Military, rank not specified')])
    assert rows == [
        ListRow('0010', 'Chief executives', '11-1011',
                f'{OCCUPATION_LOCATOR}{OCCUPATION_FIRST_ROW}'),
        ListRow('1100', 'Financial specialists', '13-20XX',
                f'{OCCUPATION_LOCATOR}{OCCUPATION_FIRST_ROW + 1}'),
        ListRow('8990', 'Metalworkers', '51-4XXX',
                f'{OCCUPATION_LOCATOR}{OCCUPATION_FIRST_ROW + 2}'),
        ListRow('9830', 'Military, rank not specified', 'none',
                f'{OCCUPATION_LOCATOR}{OCCUPATION_FIRST_ROW + 3}')]


@pytest.mark.parametrize('token', ['13-2054', '13-205X', '13-20XX', '13-2XXX', 'none'])
def test_occupation_reader_accepts_each_token_shape(tmp_path, token):
    rows = occupation_rows(tmp_path / 'list.xlsx', [occupation_row('1100', token)])
    assert rows[0].expression == token


@pytest.mark.parametrize('token', [
    '13-2X54', '13-XXXX', '13-205x', '13-2054X', '1320XX', 'None', 'NONE', '13-20', None])
def test_occupation_reader_refuses_a_token_of_another_shape(tmp_path, token):
    occupation_list_workbook(tmp_path / 'list.xlsx', [occupation_row('1100', token)])
    with pytest.raises(ValueError):
        read_occupation_list(tmp_path / 'list.xlsx')


def test_occupation_reader_refuses_a_duplicate_code(tmp_path):
    occupation_list_workbook(tmp_path / 'list.xlsx', [
        occupation_row('1100', '13-2051'), occupation_row('1100', '13-2051')])
    with pytest.raises(ValueError):
        read_occupation_list(tmp_path / 'list.xlsx')


def test_occupation_reader_refuses_a_duplicate_code_after_padding(tmp_path):
    occupation_list_workbook(tmp_path / 'list.xlsx', [
        occupation_row('1100', '13-2051'), occupation_row(' 1100', '13-2052')])
    with pytest.raises(ValueError):
        read_occupation_list(tmp_path / 'list.xlsx')


def test_occupation_reader_refuses_a_row_with_no_title(tmp_path):
    occupation_list_workbook(tmp_path / 'list.xlsx', [occupation_row('1100', '13-2051', None)])
    with pytest.raises(ValueError):
        read_occupation_list(tmp_path / 'list.xlsx')


def test_occupation_reader_sorts_strips_and_skips_other_rows(tmp_path):
    rows = occupation_rows(tmp_path / 'list.xlsx', [
        ['Management:', None, '0010-0440', '11-0000'], occupation_row(' 0020 ', ' 11-1021 ',
                                                                         ' General  managers '),
        occupation_row('10', '11-1011'), occupation_row('0010', '11-1011', 'Chief executives')])
    assert [(row.code, row.title, row.expression) for row in rows] == [
        ('0010', 'Chief executives', '11-1011'), ('0020', 'General  managers', '11-1021')]


def test_occupation_reader_refuses_a_list_with_no_data_rows(tmp_path):
    occupation_list_workbook(tmp_path / 'list.xlsx', [[None, 'Management:', '0010-0440']])
    with pytest.raises(ValueError):
        read_occupation_list(tmp_path / 'list.xlsx')


@pytest.mark.parametrize('sheet', ['Fixture', '2018 Census Occ Code List '])
def test_occupation_reader_requires_the_exact_sheet_name(tmp_path, sheet):
    occupation_list_workbook(tmp_path / 'list.xlsx', [occupation_row('1100', '13-2051')],
                             sheet=sheet)
    with pytest.raises(ValueError):
        read_occupation_list(tmp_path / 'list.xlsx')


def test_occupation_reader_reads_the_fixture_workbook():
    rows = read_occupation_list(CLASSIFICATION / 'census_occupation_2018.xlsx')
    assert len(rows) == 570
    assert [row.code for row in rows] == sorted(row.code for row in rows)
    tokens = [row.expression for row in rows]
    assert sum('X' in token for token in tokens) == 38
    assert {row.code for row in rows if row.expression == 'none'} == {'9830', '9920'}


def test_the_kind_names_the_locator(tmp_path):
    industry_list_workbook(tmp_path / 'i.xlsx', [industry_row('0170', '111')])
    occupation_list_workbook(tmp_path / 'o.xlsx', [occupation_row('1100', '13-2051')])
    assert read_industry_list(tmp_path / 'i.xlsx', 'other')[0].locator.startswith(
        f'other:{INDUSTRY_SHEET}!')
    assert read_occupation_list(tmp_path / 'o.xlsx', 'other')[0].locator.startswith(
        f'other:{OCCUPATION_SHEET}!')


def test_naics_candidates_expand_each_membership_type():
    naics, _, paths = tree_frames()
    every_311 = ['311411', '311811', '311812', '311813', '311830']
    assert naics_candidates('311811', naics, paths) == ['311811']
    assert naics_candidates('Part of 311', naics, paths) == every_311
    assert naics_candidates('3118 exc. 311811', naics, paths) == [
        '311812', '311813', '311830']
    assert naics_candidates('Part of 31, 32, 33', naics, paths) == [
        *every_311, '333242', '333415']
    assert naics_candidates('3332, 3334', naics, paths) == ['333242', '333415']
    with pytest.raises(ValueError):
        naics_candidates('not a code', naics, paths)


def test_naics_candidates_handle_markers_lists_and_exclusion_lists():
    naics, _, paths = tree_frames()
    assert naics_candidates('pt. 211120', naics, paths) == ['211120']
    assert naics_candidates('Pts. 3114, 3332', naics, paths) == ['311411', '333242']
    assert naics_candidates('3114 and 3332', naics, paths) == ['311411', '333242']
    assert naics_candidates('3118 exc. 311811, 311812', naics, paths) == [
        '311813', '311830']
    assert naics_candidates(' 311811 ', naics, paths) == ['311811']


@pytest.mark.parametrize('expression', [
    '311811 exc. 311812', '3118 exc. 211120', '3118 exc. 3118', '3118 exc. 311811 exc. 311812'])
def test_naics_candidates_refuse_an_exclusion_outside_the_scope(expression):
    naics, _, paths = tree_frames()
    with pytest.raises(ValueError):
        naics_candidates(expression, naics, paths)


def test_membership_types_keep_every_type():
    naics, _, _ = tree_frames()
    assert membership_types('311811', naics) == ['whole']
    assert membership_types('311', naics) == ['group']
    assert membership_types('Part of 311', naics) == ['group', 'part']
    assert membership_types('3332, 3334, Part of 333', naics) == ['group', 'part', 'several']
    assert membership_types('311811, 311812', naics) == ['several']
    assert membership_types('3118 exc. 311811', naics) == ['group']


def test_membership_types_cover_each_marker_and_separator():
    naics, _, _ = tree_frames()
    assert membership_types('pt. 311811', naics) == ['part']
    assert membership_types('Pts. 311811, 311812', naics) == ['part', 'several']
    assert membership_types('311811 and 311812', naics) == ['several']
    assert membership_types('311811,311812', naics) == ['several']
    assert membership_types('311811 ,311812', naics) == ['several']
    assert membership_types('311811, pt. 311812', naics) == ['part', 'several']
    assert membership_types('Part of 31, 32, 33', naics) == ['group', 'part']
    assert membership_types(' 311811 ', naics) == ['whole']


def test_membership_types_read_a_sector_spelled_as_its_subsectors():
    naics, _, _ = tree_frames()
    extra = pl.DataFrame([
        dict(node_id=f'naics:2022:sector:{code}', system='naics', vintage=2022,
             level='sector', code=code, title=code) for code in ['44-45', '48-49']])
    nodes = pl.concat([naics, extra])
    for spelling in ['31, 32, 33', '31,32,33', '31 and 32 and 33']:
        assert membership_types(spelling, nodes) == ['group']
    assert membership_types('44, 45', nodes) == ['group']
    assert membership_types('48 and 49', nodes) == ['group']
    assert membership_types('44, 45, 48, 49', nodes) == ['group', 'several']
    assert membership_types('311811, 31, 32, 33', nodes) == ['group', 'several']
    with pytest.raises(ValueError):
        membership_types('31, 32', nodes)


def test_membership_types_say_group_for_each_level_above_the_finest():
    naics, _, _ = tree_frames()
    for code in ['31-33', '311', '3118', '31181']:
        assert membership_types(code, naics) == ['group']
    assert membership_types('311811, 31181', naics) == ['group', 'several']


def test_membership_types_take_the_types_of_the_positive_clause_only():
    naics, _, _ = tree_frames()
    assert membership_types('3118 exc. 311811, 311812', naics) == ['group']
    assert membership_types('311811, 311812 exc. 311812', naics) == ['several']
    assert membership_types('Part of 311 exc. 311811', naics) == ['group', 'part']


@pytest.mark.parametrize('expression', [
    'not a code', '3118,', ',3118', '999999', '3118 exc. 311811 exc. 311812', '',
    '311811-311813'])
def test_membership_types_refuse_what_they_cannot_read(expression):
    naics, _, _ = tree_frames()
    with pytest.raises(ValueError):
        membership_types(expression, naics)


def test_membership_types_refuse_a_missing_expression():
    naics, _, _ = tree_frames()
    with pytest.raises(ValueError):
        membership_types(None, naics)
