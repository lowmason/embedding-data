'''Stage 14 report, firm and pair statuses.

Every frame here is synthetic: small typed frames in `SUBAWARD_SCHEMA` and `EXTRACT_SCHEMA`
with made-up 12-character UEIs and no name or address values. The node set holds four real
NAICS 2022 national-industry codes. Each refusal matches the exact message (`\\A...\\Z`), so a
refusal at the wrong check fails.
'''

import dataclasses
import json
import random
import re
from datetime import date
from decimal import Decimal

import polars as pl
import pytest
from vendor_link_fixtures import (  # noqa: F401
    TEST_EXTRACT_LAYOUT,
    TEST_SUBAWARD_LAYOUTS,
    no_live_sam,
)

from embedding_data import usaspending_raw, vendor_link_layouts, vendor_link_pairs
from embedding_data.vendor_link_codes import NODE_PREFIX
from embedding_data.vendor_link_pairs import (
    AMOUNT_PATTERN,
    AMOUNT_TYPE,
    CODE_PATTERN,
    DNB_CUTOFF,
    FIRM_SCHEMA,
    FIRM_STATUSES,
    PAIR_SCHEMA,
    PAIR_STATUSES,
    REPORT_STATUSES,
    SUBCONTRACT,
    UEI_PATTERN,
    WINDOW,
    check_subaward_types,
    count_malformed,
    firms,
    pairs,
    report_counts,
    reports,
    subaward_types,
    validate_pairs,
)
from embedding_data.vendor_link_readers import EXTRACT_SCHEMA, SUBAWARD_SCHEMA

LAYOUTS = TEST_SUBAWARD_LAYOUTS
EXTRACT = TEST_EXTRACT_LAYOUT
CODES = ('541511', '541512', '236220', '336411')
NODE_IDS = frozenset(NODE_PREFIX + code for code in CODES)
MEMBER = 'Contracts_Subawards_1.csv'
PRIME = 'AAAAAAAAAAA1'
SUB = 'BBBBBBBBBBB2'
FIRM = 'CCCCCCCCCCC3'
OTHER = 'DDDDDDDDDDD4'
PARENT = 'EEEEEEEEEEE5'
REPORT_COLUMNS = {'prime': pl.String, 'sub': pl.String, 'prime_parent': pl.String,
                  'sub_parent': pl.String, 'action': pl.Date, 'fiscal_year': pl.Int64,
                  'amount_value': pl.Decimal(38, 2), 'report_status': pl.String}
NBSP = '\xa0'


def exactly(message):
    return pytest.raises(ValueError, match=rf'\A{re.escape(message)}\Z')


def report(**fields):
    '''One subaward row: a usable FY2024 report from PRIME to SUB unless `fields` say
    otherwise.'''
    return {'file_year': 2024, 'member': MEMBER, 'prime_uei': PRIME, 'prime_parent_uei': '',
            'sub_uei': SUB, 'sub_parent_uei': '', 'action_date': '2024-01-05', 'amount': '',
            'subaward_type': 'sub-contract', 'report_id': '', 'subaward_naics': '',
            'prime_naics': ''} | fields


def rows_of(*records):
    '''The rows as a lazy frame in `SUBAWARD_SCHEMA`. Each row gets its own record number
    and, unless it names one, its own digest.'''
    numbered = [{'record': index, 'row_digest': f'{index:064x}'} | record
                for index, record in enumerate(records, start=1)]
    return pl.LazyFrame(numbered, schema=SUBAWARD_SCHEMA)


def reported_of(*records, layouts=LAYOUTS):
    return reports(rows_of(*records), layouts)


def usable_of(*records, layouts=LAYOUTS):
    return reported_of(*records, layouts=layouts).filter(pl.col('report_status') == 'usable')


def extract_row(uei, *, update='20240101', code='541511', string=None, status='A', evs=''):
    '''One extract row in delivered form. The code string defaults to the code plus a flag.'''
    return {'uei': uei, 'registration_status': status, 'last_update_date': update,
            'primary_naics': code, 'naics_code_string': f'{code}Y' if string is None else string,
            'evs_source': evs}


def extract_of(rows):
    return pl.DataFrame([{'line': line} | row for line, row in enumerate(rows, start=2)],
                        schema=EXTRACT_SCHEMA)


def firm_table_of(records, rows, *, layouts=LAYOUTS, layout=EXTRACT):
    return firms(usable_of(*records, layouts=layouts), extract_of(rows), layout, NODE_IDS)


def firm_of(uei, rows, *, layout=EXTRACT):
    '''The firm row of `uei`, the prime of one usable report whose subcontractor has no
    extract row.'''
    table = firm_table_of([report(prime_uei=uei, sub_uei=OTHER)], rows, layout=layout)
    return table.filter(pl.col('uei') == uei).row(0, named=True)


def pair_table_of(records, rows, *, layouts=LAYOUTS):
    usable = usable_of(*records, layouts=layouts)
    return pairs(usable, firms(usable, extract_of(rows), EXTRACT, NODE_IDS))


def counts_of(records, rows, *, layouts=LAYOUTS, layout=EXTRACT):
    reported = reported_of(*records, layouts=layouts)
    usable = reported.filter(pl.col('report_status') == 'usable')
    extract = extract_of(rows)
    firm_table = firms(usable, extract, layout, NODE_IDS)
    pair_table = pairs(usable, firm_table)
    return report_counts(reported, firm_table, pair_table, extract, layouts, layout, NODE_IDS)


def with_columns(layouts, **columns):
    '''The layouts with the given logical fields remapped in every year.'''
    return {year: dataclasses.replace(layout, columns=layout.columns | columns)
            for year, layout in layouts.items()}


def set_value(table, row, column, value):
    '''`table` with one cell replaced, in the column's own type.'''
    index = pl.int_range(pl.len())
    replaced = pl.when(index == row).then(pl.lit(value, dtype=table.schema[column]))
    return table.with_columns(replaced.otherwise(pl.col(column)).alias(column))


# ---- constants

def test_the_module_constants():
    assert vendor_link_pairs.CONTRACT == 'vendor-link-pairs-v1'
    assert vendor_link_pairs.WHITESPACE is vendor_link_layouts.WHITESPACE
    assert vendor_link_pairs.WHITESPACE == ' \t\n\r\x0b\x0c'
    assert UEI_PATTERN == r'^[A-Z0-9]{12}$'
    assert CODE_PATTERN == r'^[0-9]{6}$'
    assert AMOUNT_PATTERN == r'^-?[0-9]{1,36}(\.[0-9]{1,2})?$'
    assert AMOUNT_TYPE == pl.Decimal(38, 2)
    assert DNB_CUTOFF == date(2022, 4, 4)
    assert SUBCONTRACT == 'sub-contract'
    assert WINDOW == (2024, 2025, 2026) == usaspending_raw.WINDOW
    assert REPORT_STATUSES == ('uei_unusable', 'action_date_invalid', 'outside_window',
                               'usable')
    assert FIRM_STATUSES == ('not_in_sam', 'dnb_era_record', 'naics_missing',
                             'naics_conflict', 'naics_not_2022', 'eligible')
    assert PAIR_STATUSES == ('self_link', 'intra_group', 'prime_ineligible', 'sub_ineligible',
                             'eligible')
    assert list(FIRM_SCHEMA.items()) == [
        ('uei', pl.String), ('is_prime', pl.Boolean), ('is_sub', pl.Boolean),
        ('firm_status', pl.String), ('node_id', pl.String), ('n_extract_rows', pl.UInt64),
        ('flag_mixed_blank', pl.Boolean), ('flag_last_update_invalid', pl.Boolean),
        ('flag_code_not_in_string', pl.Boolean)]
    assert list(PAIR_SCHEMA.items()) == [
        ('prime_uei', pl.String), ('sub_uei', pl.String), ('n_reports', pl.UInt64),
        ('n_fy2024', pl.UInt64), ('n_fy2025', pl.UInt64), ('n_fy2026', pl.UInt64),
        ('prime_status', pl.String), ('sub_status', pl.String), ('prime_node_id', pl.String),
        ('sub_node_id', pl.String), ('flag_intra_group', pl.Boolean),
        ('pair_status', pl.String), ('amount_sum', pl.Decimal(38, 2))]


# ---- subaward type

def test_subaward_types_counts_each_delivered_value():
    frame = rows_of(report(), report(file_year=2026), report(subaward_type=' sub-contract'),
                    report(subaward_type='sub-grant'))
    counts = subaward_types(frame)
    assert counts == {' sub-contract': 1, 'sub-contract': 2, 'sub-grant': 1}
    assert list(counts) == sorted(counts)
    assert all(type(count) is int for count in counts.values())
    assert subaward_types(rows_of()) == {}


def test_a_sub_grant_row_fails():
    with exactly('subaward type is not sub-contract'):
        check_subaward_types(rows_of(report(), report(subaward_type='sub-grant')))


@pytest.mark.parametrize('value', [' sub-contract', 'sub-contract\t', 'Sub-Contract',
                                   'SUB-CONTRACT', 'sub contract', '', None])
def test_the_subaward_type_is_compared_as_delivered(value):
    with exactly('subaward type is not sub-contract'):
        check_subaward_types(rows_of(report(), report(subaward_type=value), report()))


def test_sub_contract_rows_pass_the_type_check():
    assert check_subaward_types(rows_of(report(), report(file_year=2025))) is None
    assert check_subaward_types(rows_of()) is None


# ---- report statuses

@pytest.mark.parametrize('prime, sub, date_, status', [
    ('', 'BBBBBBBBBBB2', '2024-01-05', 'uei_unusable'),
    ('AAAAAAAAAAA1', 'bbbbbbbbbbb2', '2024-01-05', 'uei_unusable'),
    ('AAAAAAAAAAA1', 'BBBBBBBBBBB2', '2024-02-30', 'action_date_invalid'),
    ('', 'BBBBBBBBBBB2', '', 'uei_unusable'),
    ('AAAAAAAAAAA1', 'BBBBBBBBBBB2', '2023-09-30', 'outside_window'),
    ('AAAAAAAAAAA1', 'BBBBBBBBBBB2', '2023-10-01', 'usable')])
def test_report_statuses_follow_the_spec_order(prime, sub, date_, status):
    frame = reported_of(report(prime_uei=prime, sub_uei=sub, action_date=date_)).collect()
    assert frame['report_status'].to_list() == [status]


@pytest.mark.parametrize('fields', [
    {'prime_uei': '', 'action_date': '2026-10-01'},
    {'sub_uei': 'bbbbbbbbbbb2', 'action_date': '2023-09-30'},
    {'prime_uei': 'AAAA', 'action_date': 'not a date'},
    {'sub_uei': '', 'action_date': ''}])
def test_an_unusable_uei_wins_over_a_later_report_status(fields):
    frame = reported_of(report(**fields)).collect()
    assert frame['report_status'].to_list() == ['uei_unusable']


BAD_UEIS = ['', '   ', 'AAAAAAAAAAA', 'AAAAAAAAAAA12', 'aaaaaaaaaaa1', 'AAAAAA AAAAA',
            'AAAAAAAAAAÉ1', 'AAAAAAAAAA-1', NBSP + 'AAAAAAAAAAA1', 'AAAAAAAAAAA1' + NBSP,
            'AAAAAAAAAAA1\x1f']


@pytest.mark.parametrize('side', ['prime_uei', 'sub_uei'])
@pytest.mark.parametrize('value', BAD_UEIS)
def test_a_blank_or_malformed_uei_on_either_side_is_unusable(side, value):
    frame = reported_of(report(**{side: value})).collect()
    assert frame['report_status'].to_list() == ['uei_unusable']


@pytest.mark.parametrize('pad', list(' \t\n\r\x0b\x0c'))
def test_ueis_are_stripped_of_the_ascii_whitespace_set(pad):
    frame = reported_of(report(prime_uei=f'{pad}{PRIME}{pad}', sub_uei=f'{pad}{pad}{SUB}'))
    row = frame.collect().row(0, named=True)
    assert (row['prime'], row['sub'], row['report_status']) == (PRIME, SUB, 'usable')
    assert row['prime_uei'] == f'{pad}{PRIME}{pad}'


def test_reports_keeps_every_row_and_adds_the_status_columns():
    frame = rows_of(report(prime_uei=''), report(), report(), report(action_date='x'),
                    report(file_year=2025, action_date='2025-02-01'),
                    report(file_year=2026, action_date='2027-01-01'))
    result = reports(frame, LAYOUTS)
    assert isinstance(result, pl.LazyFrame)
    out = result.collect()
    assert list(out.schema.items()) == [*SUBAWARD_SCHEMA.items(), *REPORT_COLUMNS.items()]
    assert out.select(*SUBAWARD_SCHEMA).equals(frame.collect())
    assert out['report_status'].to_list() == ['uei_unusable', 'usable', 'usable',
                                              'action_date_invalid', 'usable',
                                              'outside_window']
    empty = reports(rows_of(), LAYOUTS).collect()
    assert list(empty.schema.items()) == list(out.schema.items())
    assert empty.height == 0


@pytest.mark.parametrize('text, action', [
    ('2024-01-05', date(2024, 1, 5)), (' 2024-01-05\t', date(2024, 1, 5)),
    ('\x0b2024-01-05\x0c\r\n', date(2024, 1, 5)), ('2024-02-29', date(2024, 2, 29)),
    ('2024-1-5', None), ('+2024-01-05', None), ('2024/01/05', None), ('', None),
    ('   ', None), ('2024-02-30', None), ('2023-02-29', None), ('2024-01-05' + NBSP, None),
    ('20240105', None), ('2024-01-05T00:00', None)])
def test_an_action_date_is_valid_only_when_it_round_trips(text, action):
    row = reported_of(report(action_date=text)).collect().row(0, named=True)
    assert row['action'] == action
    if action is None:
        assert (row['fiscal_year'], row['report_status']) == (None, 'action_date_invalid')
    else:
        assert (row['fiscal_year'], row['report_status']) == (2024, 'usable')


DATE_FORMATS = {2024: '%Y-%m-%d', 2025: '%m/%d/%Y', 2026: '%d.%m.%Y'}
DATED_LAYOUTS = {year: dataclasses.replace(layout, date_format=DATE_FORMATS[year])
                 for year, layout in LAYOUTS.items()}


def test_each_file_year_reads_dates_with_its_own_format():
    texts = ('2025-01-05', '01/05/2025', '05.01.2025')
    records = [report(file_year=year, action_date=text) for year in WINDOW for text in texts]
    out = reported_of(*records, layouts=DATED_LAYOUTS).collect()
    valid = out.filter(pl.col('action').is_not_null())
    assert valid.select('file_year', 'action_date', 'action').rows() == [
        (2024, '2025-01-05', date(2025, 1, 5)), (2025, '01/05/2025', date(2025, 1, 5)),
        (2026, '05.01.2025', date(2025, 1, 5))]
    assert out['report_status'].value_counts().sort('report_status').rows() == [
        ('action_date_invalid', 6), ('usable', 3)]


def test_fiscal_year_boundaries():
    records = [report(action_date='2024-09-30'), report(action_date='2024-10-01')]
    out = reported_of(*records).collect()
    assert out['fiscal_year'].to_list() == [2024, 2025]
    assert out['report_status'].to_list() == ['usable', 'usable']
    counts = counts_of(records, [])
    assert counts['usable_by_fiscal_year'] == {'2024': 1, '2025': 1, '2026': 0}
    assert counts['reports']['by_file_year']['2024']['outside_file_year'] == 1
    assert counts['reports']['by_file_year']['2025']['rows'] == 0


@pytest.mark.parametrize('text, fiscal_year, status', [
    ('2023-09-30', 2023, 'outside_window'), ('2023-10-01', 2024, 'usable'),
    ('2024-01-01', 2024, 'usable'), ('2024-09-30', 2024, 'usable'),
    ('2024-10-01', 2025, 'usable'), ('2024-12-31', 2025, 'usable'),
    ('2025-09-30', 2025, 'usable'), ('2025-10-01', 2026, 'usable'),
    ('2026-09-30', 2026, 'usable'), ('2026-10-01', 2027, 'outside_window'),
    ('2019-05-01', 2019, 'outside_window')])
def test_the_window_has_a_lower_and_an_upper_bound(text, fiscal_year, status):
    row = reported_of(report(action_date=text)).collect().row(0, named=True)
    assert (row['fiscal_year'], row['report_status']) == (fiscal_year, status)


@pytest.mark.parametrize('field, column', [('prime_parent_uei', 'prime_parent'),
                                           ('sub_parent_uei', 'sub_parent')])
@pytest.mark.parametrize('text, parent', [
    (PARENT, PARENT), (f' {PARENT}\t', PARENT), (f'\x0b{PARENT}\x0c', PARENT), ('', None),
    ('   ', None), (PARENT.lower(), None), (PARENT[:-1], None), (PARENT + '6', None),
    (PARENT + NBSP, None)])
def test_parent_ueis_are_stripped_and_null_unless_usable(field, column, text, parent):
    row = reported_of(report(**{field: text})).collect().row(0, named=True)
    other = 'sub_parent' if column == 'prime_parent' else 'prime_parent'
    assert (row[column], row[other], row['report_status']) == (parent, None, 'usable')


DIGITS = '1' * 36


@pytest.mark.parametrize('text, value', [
    ('100.50', '100.50'), ('-20', '-20.00'), (' 5 ', '5.00'), ('\t0.5\x0c', '0.50'),
    ('007', '7.00'), ('-0.01', '-0.01'), (DIGITS, DIGITS + '.00'),
    (DIGITS + '.99', DIGITS + '.99'), ('1,000', None), ('', None), ('1.234', None),
    ('.5', None), ('5.', None), ('+5', None), ('1e3', None), ('1' * 37, None),
    ('$5', None), ('5' + NBSP, None), ('- 5', None), ('--5', None), ('5-', None)])
def test_an_amount_parses_only_when_it_matches_the_pattern(text, value):
    out = reported_of(report(amount=text)).collect()
    assert out.schema['amount_value'] == AMOUNT_TYPE
    parsed = out['amount_value'][0]
    assert (None if parsed is None else str(parsed)) == value
    assert out['report_status'].to_list() == ['usable']


# ---- corporate groups

ELIGIBLE_ROWS = [extract_row(PRIME, code='236220'), extract_row(SUB, code='541511')]
GROUP_PARENTS = {'sub_parent_is_prime': {'sub_parent_uei': PRIME},
                 'prime_parent_is_sub': {'prime_parent_uei': SUB},
                 'equal_parents': {'prime_parent_uei': PARENT, 'sub_parent_uei': PARENT}}


@pytest.mark.parametrize('condition', ['sub_parent_is_prime', 'prime_parent_is_sub',
                                       'equal_parents'])
def test_each_corporate_group_condition(condition):
    table = pair_table_of([report(**GROUP_PARENTS[condition])], ELIGIBLE_ROWS)
    assert table.select('flag_intra_group', 'pair_status').rows() == [(True, 'intra_group')]


def test_blank_parents_form_no_group():
    for parents in ({}, {'prime_parent_uei': '  ', 'sub_parent_uei': '\t'},
                    {'prime_parent_uei': '', 'sub_parent_uei': ''}):
        table = pair_table_of([report(**parents)], ELIGIBLE_ROWS)
        assert table.select('flag_intra_group', 'pair_status').rows() == [(False, 'eligible')]


def test_a_null_prime_parent_column_disables_two_conditions():
    layouts = with_columns(LAYOUTS, prime_parent_uei=None)
    cases = [({'prime_parent_uei': SUB}, False),
             ({'prime_parent_uei': PARENT, 'sub_parent_uei': PARENT}, False),
             ({'sub_parent_uei': PRIME}, True)]
    for parents, flag in cases:
        assert reported_of(report(**parents), layouts=layouts).collect()['prime_parent'][0] is None
        table = pair_table_of([report(**parents)], ELIGIBLE_ROWS, layouts=layouts)
        assert table['flag_intra_group'].to_list() == [flag]
        assert pair_table_of([report(**parents)], ELIGIBLE_ROWS)['flag_intra_group'][0]


def test_a_null_sub_parent_column_disables_two_conditions():
    layouts = with_columns(LAYOUTS, sub_parent_uei=None)
    cases = [({'sub_parent_uei': PRIME}, False),
             ({'prime_parent_uei': PARENT, 'sub_parent_uei': PARENT}, False),
             ({'prime_parent_uei': SUB}, True)]
    for parents, flag in cases:
        assert reported_of(report(**parents), layouts=layouts).collect()['sub_parent'][0] is None
        table = pair_table_of([report(**parents)], ELIGIBLE_ROWS, layouts=layouts)
        assert table['flag_intra_group'].to_list() == [flag]
        assert pair_table_of([report(**parents)], ELIGIBLE_ROWS)['flag_intra_group'][0]


def test_an_unmapped_parent_column_counts_only_in_its_own_year():
    layouts = dict(LAYOUTS) | with_columns({2025: LAYOUTS[2025]}, prime_parent_uei=None)
    records = [report(file_year=year, action_date='2025-01-05', prime_parent_uei=SUB)
               for year in WINDOW]
    out = reported_of(*records, layouts=layouts).collect()
    assert out['prime_parent'].to_list() == [SUB, None, SUB]


@pytest.mark.parametrize('first', [True, False])
def test_one_group_report_makes_the_pair_intra_group(first):
    grouped = report(sub_parent_uei=PRIME, action_date='2024-03-01')
    plain = report(action_date='2024-02-01')
    records = [grouped, plain] if first else [plain, grouped]
    table = pair_table_of(records, ELIGIBLE_ROWS)
    assert table.select('n_reports', 'flag_intra_group', 'pair_status').rows() == [
        (2, True, 'intra_group')]


@pytest.mark.parametrize('parents, flag', [
    ({'sub_parent_uei': SUB}, False), ({'prime_parent_uei': PRIME}, False),
    ({'prime_parent_uei': PRIME, 'sub_parent_uei': SUB}, False),
    ({'prime_parent_uei': PARENT, 'sub_parent_uei': OTHER}, False),
    ({'prime_parent_uei': 'not-a-uei', 'sub_parent_uei': 'not-a-uei'}, False),
    ({'prime_parent_uei': PARENT.lower(), 'sub_parent_uei': PARENT.lower()}, False),
    ({'sub_parent_uei': PRIME.lower()}, False), ({'prime_parent_uei': SUB.lower()}, False),
    ({'prime_parent_uei': f' {PARENT}', 'sub_parent_uei': f'{PARENT}\t'}, True),
    ({'sub_parent_uei': f'\t{PRIME}\n'}, True), ({'prime_parent_uei': f'{SUB} '}, True)])
def test_a_group_needs_usable_parents_that_match_the_other_side(parents, flag):
    table = pair_table_of([report(**parents)], ELIGIBLE_ROWS)
    assert table.select('flag_intra_group', 'pair_status').rows() == [
        (flag, 'intra_group' if flag else 'eligible')]


# ---- firm statuses

none = []
updated_2022_04_03 = [extract_row(FIRM, update='20220403')]
evs_dnb = [extract_row(FIRM, evs='D&B')]
invalid_update = [extract_row(FIRM, update='20220431')]
blank_code = [extract_row(FIRM, code='')]
two_codes = [extract_row(FIRM, code='541511'), extract_row(FIRM, code='541512')]
code_517311 = [extract_row(FIRM, code='517311')]
updated_2022_04_04 = [extract_row(FIRM, update='20220404')]
agreeing_rows = [extract_row(FIRM), extract_row(FIRM)]
blank_and_coded_rows = [extract_row(FIRM, code=''), extract_row(FIRM)]


@pytest.mark.parametrize('rows, status', [
    (none, 'not_in_sam'), (updated_2022_04_03, 'dnb_era_record'),
    (evs_dnb, 'dnb_era_record'), (invalid_update, 'dnb_era_record'),
    (blank_code, 'naics_missing'), (two_codes, 'naics_conflict'),
    (code_517311, 'naics_not_2022'), (updated_2022_04_04, 'eligible'),
    (agreeing_rows, 'eligible'), (blank_and_coded_rows, 'eligible')])
def test_firm_statuses_follow_the_spec_order(rows, status):
    assert firm_of(FIRM, rows)['firm_status'] == status


@pytest.mark.parametrize('rows, status', [
    ([extract_row(FIRM, update='20220403', code='')], 'dnb_era_record'),
    ([extract_row(FIRM, evs='D&B'), extract_row(FIRM, code='541512')], 'dnb_era_record'),
    ([extract_row(FIRM, update='', code='517311')], 'dnb_era_record'),
    ([extract_row(FIRM, code='517311'), extract_row(FIRM, code='517312')], 'naics_conflict'),
    ([extract_row(FIRM, code='541511'), extract_row(FIRM, code='517311')], 'naics_conflict')])
def test_an_earlier_firm_status_wins(rows, status):
    assert firm_of(FIRM, rows)['firm_status'] == status


@pytest.mark.parametrize('dnb_row', [extract_row(FIRM, update='20220403'),
                                     extract_row(FIRM, evs='D&B'), extract_row(FIRM, update='')])
@pytest.mark.parametrize('first', [True, False])
def test_one_dnb_era_row_makes_the_firm_a_dnb_era_record(dnb_row, first):
    rows = [dnb_row, extract_row(FIRM)] if first else [extract_row(FIRM), dnb_row]
    assert firm_of(FIRM, rows)['firm_status'] == 'dnb_era_record'


@pytest.mark.parametrize('text, status, invalid', [
    ('20220404', 'eligible', False), (' 20220404\t', 'eligible', False),
    ('\x0b20220405\x0c', 'eligible', False), ('20991231', 'eligible', False),
    ('20220403', 'dnb_era_record', False), ('20000101', 'dnb_era_record', False),
    ('', 'dnb_era_record', True), ('   ', 'dnb_era_record', True),
    ('2022-04-05', 'dnb_era_record', True), ('20220431', 'dnb_era_record', True),
    ('20220405' + NBSP, 'dnb_era_record', True), ('2022045', 'dnb_era_record', True)])
def test_a_last_update_date_must_round_trip_and_reach_the_cutoff(text, status, invalid):
    firm = firm_of(FIRM, [extract_row(FIRM, update=text)])
    assert (firm['firm_status'], firm['flag_last_update_invalid']) == (status, invalid)


def test_the_last_update_date_uses_the_layout_date_format():
    layout = dataclasses.replace(EXTRACT, date_format='%m/%d/%Y')
    cases = [('04/04/2022', 'eligible'), ('04/03/2022', 'dnb_era_record'),
             ('20220404', 'dnb_era_record')]
    for text, status in cases:
        assert firm_of(FIRM, [extract_row(FIRM, update=text)], layout=layout)[
            'firm_status'] == status


@pytest.mark.parametrize('evs, status', [
    ('D&B', 'dnb_era_record'), (' D&B\t', 'dnb_era_record'), ('\x0bD&B\x0c', 'dnb_era_record'),
    ('d&b', 'eligible'), ('SAM', 'eligible'), ('', 'eligible'), ('D&B' + NBSP, 'eligible'),
    ('D&B2', 'eligible')])
def test_the_evs_rule_strips_and_compares_with_the_layout_set(evs, status):
    assert firm_of(FIRM, [extract_row(FIRM, evs=evs)])['firm_status'] == status


def test_the_evs_values_come_from_the_layout():
    layout = dataclasses.replace(EXTRACT, evs_dnb=frozenset({'DNB', 'OD'}))
    for evs, status in [('DNB', 'dnb_era_record'), ('OD', 'dnb_era_record'),
                        ('D&B', 'eligible')]:
        assert firm_of(FIRM, [extract_row(FIRM, evs=evs)], layout=layout)['firm_status'] == status


def test_the_evs_rule_needs_a_mapped_evs_source():
    layout = dataclasses.replace(EXTRACT, positions=EXTRACT.positions | {'evs_source': None})
    assert firm_of(FIRM, [extract_row(FIRM, evs='D&B')], layout=layout)['firm_status'] == (
        'eligible')


@pytest.mark.parametrize('rows, status, node_id', [
    ([extract_row(FIRM, code=' 541511\t')], 'eligible', NODE_PREFIX + '541511'),
    ([extract_row(FIRM, code='\x0b236220\x0c')], 'eligible', NODE_PREFIX + '236220'),
    ([extract_row(FIRM, code=' 336411'), extract_row(FIRM, code='336411\r')], 'eligible',
     NODE_PREFIX + '336411'),
    ([extract_row(FIRM, code='   ')], 'naics_missing', None),
    ([extract_row(FIRM, code='\t\n')], 'naics_missing', None),
    ([extract_row(FIRM, code=''), extract_row(FIRM, code=' ')], 'naics_missing', None),
    ([extract_row(FIRM, code='517311')], 'naics_not_2022', None),
    ([extract_row(FIRM, code='000000')], 'naics_not_2022', None),
    ([extract_row(FIRM, code='541511'), extract_row(FIRM, code='541512')], 'naics_conflict',
     None),
    ([extract_row(FIRM, update='20200101')], 'dnb_era_record', None),
    ([], 'not_in_sam', None)])
def test_codes_are_stripped_and_only_an_eligible_firm_gets_a_node(rows, status, node_id):
    firm = firm_of(FIRM, rows)
    assert (firm['firm_status'], firm['node_id']) == (status, node_id)


def test_padded_ueis_join_after_the_strip_and_lower_case_is_unusable():
    records = [report(prime_uei=' ABC123DEF456 ', sub_uei=SUB),
               report(prime_uei='abc123def456', sub_uei=SUB)]
    assert reported_of(*records).collect()['report_status'].to_list() == ['usable',
                                                                          'uei_unusable']
    rows = [extract_row('ABC123DEF456  ', code='236220'),
            extract_row('abc123def456', code='236220'), extract_row(SUB)]
    table = firm_table_of(records, rows)
    assert table['uei'].to_list() == ['ABC123DEF456', SUB]
    firm = table.row(0, named=True)
    assert (firm['firm_status'], firm['n_extract_rows']) == ('eligible', 1)


def test_a_lower_case_extract_uei_never_joins():
    firm = firm_of(FIRM, [extract_row(FIRM.lower())])
    assert (firm['firm_status'], firm['n_extract_rows']) == ('not_in_sam', 0)


def test_the_extract_uei_is_stripped_of_the_whitespace_set_only():
    firm = firm_of(FIRM, [extract_row(f'\t{FIRM}\x0b'), extract_row(f'\x0c{FIRM}\r\n')])
    assert (firm['firm_status'], firm['n_extract_rows']) == ('eligible', 2)
    firm = firm_of(FIRM, [extract_row(FIRM + NBSP)])
    assert (firm['firm_status'], firm['n_extract_rows']) == ('not_in_sam', 0)


def test_the_firm_table_has_one_sorted_row_per_usable_uei():
    ueis = [f'F{number:011d}' for number in range(40)]
    records = [report(prime_uei=ueis[n], sub_uei=ueis[n + 20]) for n in range(20)]
    records.append(report(prime_uei=ueis[25], sub_uei=ueis[3]))
    records.append(report(prime_uei=OTHER, sub_uei=ueis[0], action_date='2023-01-01'))
    random.Random(7).shuffle(records)
    rows = [extract_row(ueis[n]) for n in range(1, 40, 2)] + [extract_row(ueis[5])] * 2
    table = firm_table_of(records, rows)
    assert list(table.schema.items()) == list(FIRM_SCHEMA.items())
    assert table['uei'].to_list() == ueis
    roles = {uei: (is_prime, is_sub) for uei, is_prime, is_sub
             in table.select('uei', 'is_prime', 'is_sub').iter_rows()}
    assert roles[ueis[0]] == (True, False)
    assert roles[ueis[21]] == (False, True)
    assert roles[ueis[3]] == (True, True)
    assert roles[ueis[25]] == (True, True)
    counts = dict(table.select('uei', 'n_extract_rows').iter_rows())
    assert (counts[ueis[0]], counts[ueis[1]], counts[ueis[5]]) == (0, 1, 3)
    empty = firm_table_of([], rows)
    assert list(empty.schema.items()) == list(FIRM_SCHEMA.items())
    assert empty.height == 0


@pytest.mark.parametrize('rows, flag', [
    ([extract_row(FIRM, code=''), extract_row(FIRM)], True),
    ([extract_row(FIRM), extract_row(FIRM, code='  ')], True),
    ([extract_row(FIRM, code=''), extract_row(FIRM, code='541511'),
      extract_row(FIRM, code='541512')], True),
    ([extract_row(FIRM, code='', update='20200101'), extract_row(FIRM)], True),
    ([extract_row(FIRM), extract_row(FIRM)], False),
    ([extract_row(FIRM, code='')], False),
    ([extract_row(FIRM, code=''), extract_row(FIRM, code='')], False),
    ([extract_row(FIRM)], False), ([], False)])
def test_the_mixed_blank_flag(rows, flag):
    assert firm_of(FIRM, rows)['flag_mixed_blank'] is flag


@pytest.mark.parametrize('rows, flag', [
    ([extract_row(FIRM, string='541511Y~236220N')], False),
    ([extract_row(FIRM, string='236220N~541511Y')], False),
    ([extract_row(FIRM, string='X541511Y')], False),
    ([extract_row(FIRM, string='236220Y'), extract_row(FIRM, string='541511Y')], False),
    ([extract_row(FIRM, code='', string='541511Y'), extract_row(FIRM, string='236220Y')],
     False),
    ([extract_row(FIRM, string='236220Y')], True),
    ([extract_row(FIRM, string='5415111Y')], True),
    ([extract_row(FIRM, string='15415110')], True),
    ([extract_row(FIRM, string='')], True),
    ([extract_row(FIRM, code='517311', string='236220Y')], True),
    ([extract_row(FIRM, code='541511', string='236220Y'),
      extract_row(FIRM, code='541512', string='236220Y')], False),
    ([extract_row(FIRM, code='', string='236220Y')], False),
    ([extract_row(FIRM, update='20200101', string='236220Y')], False),
    ([], False)])
def test_the_code_not_in_string_flag(rows, flag):
    assert firm_of(FIRM, rows)['flag_code_not_in_string'] is flag


def test_the_last_update_flag_is_false_without_extract_rows():
    firm = firm_of(FIRM, [])
    assert (firm['flag_last_update_invalid'], firm['flag_mixed_blank']) == (False, False)


# ---- malformed codes

def test_malformed_code_on_a_read_firm_fails_and_elsewhere_is_counted():
    records = [report(subaward_naics='54151A', prime_naics='541511')]
    usable = usable_of(*records)
    read = extract_of([extract_row(PRIME, code='54151A'), extract_row(SUB)])
    assert count_malformed(usable, read, EXTRACT) == {'read_rows': 1, 'unread_rows': 0}
    with exactly('malformed primary NAICS code'):
        firms(usable, read, EXTRACT, NODE_IDS)
    elsewhere = [extract_row(PRIME, code='236220', string='54151A~236220Y'), extract_row(SUB),
                 extract_row(OTHER, code='54151A')]
    assert count_malformed(usable, extract_of(elsewhere), EXTRACT) == {'read_rows': 0,
                                                                       'unread_rows': 1}
    table = firms(usable, extract_of(elsewhere), EXTRACT, NODE_IDS)
    assert table['firm_status'].to_list() == ['eligible', 'eligible']
    counts = counts_of(records, elsewhere)
    assert counts['extract']['malformed_unread_rows'] == 1
    assert counts['extract']['primary_codes']['malformed'] == 1
    assert counts['reports']['by_file_year']['2024']['subaward_naics_equal_prime'] == {
        'both': 1, 'equal': 0}
    dnb = [extract_row(PRIME, code='236220'), extract_row(SUB, code='54151A', update='20220403')]
    assert count_malformed(usable, extract_of(dnb), EXTRACT) == {'read_rows': 0,
                                                                 'unread_rows': 1}
    table = firms(usable, extract_of(dnb), EXTRACT, NODE_IDS)
    assert dict(table.select('uei', 'firm_status').iter_rows()) == {
        PRIME: 'eligible', SUB: 'dnb_era_record'}


@pytest.mark.parametrize('code', ['54151A', '5415', '5415111', '54-151', '541 511',
                                  '５４１５１１', '541511' + NBSP,
                                  NBSP, '\x1f'])
def test_a_malformed_code_on_a_read_firm_fails(code):
    usable = usable_of(report(prime_uei=FIRM, sub_uei=OTHER))
    for rows in ([extract_row(FIRM, code=code)],
                 [extract_row(FIRM), extract_row(FIRM, code=code)]):
        extract = extract_of(rows)
        assert count_malformed(usable, extract, EXTRACT) == {'read_rows': 1, 'unread_rows': 0}
        with exactly('malformed primary NAICS code'):
            firms(usable, extract, EXTRACT, NODE_IDS)


def test_unread_malformed_codes_are_counted_and_never_fail():
    dnb_firm, evs_firm = 'GGGGGGGGGGG6', 'HHHHHHHHHHH7'
    records = [report(prime_uei=FIRM, sub_uei=SUB), report(prime_uei=FIRM, sub_uei=dnb_firm),
               report(prime_uei=FIRM, sub_uei=evs_firm),
               report(prime_uei=OTHER, sub_uei=SUB, action_date='2023-09-30')]
    rows = [extract_row(FIRM), extract_row(SUB), extract_row(OTHER, code='54151A'),
            extract_row(PARENT, code='5415'), extract_row(dnb_firm, code='54151A'),
            extract_row(dnb_firm, update='20220101'),
            extract_row(evs_firm, code='54151A', evs='D&B')]
    usable = usable_of(*records)
    assert count_malformed(usable, extract_of(rows), EXTRACT) == {'read_rows': 0,
                                                                  'unread_rows': 4}
    table = firms(usable, extract_of(rows), EXTRACT, NODE_IDS)
    assert dict(table.select('uei', 'firm_status').iter_rows()) == {
        FIRM: 'eligible', SUB: 'eligible', dnb_firm: 'dnb_era_record',
        evs_firm: 'dnb_era_record'}
    counts = counts_of(records, rows)
    assert counts['extract']['malformed_unread_rows'] == 4
    assert counts['extract']['primary_codes']['malformed'] == 4


def test_count_malformed_counts_rows_not_firms():
    usable = usable_of(report(prime_uei=FIRM, sub_uei=OTHER))
    rows = [extract_row(FIRM, code='54151A'), extract_row(FIRM, code='5415'),
            extract_row(PARENT, code='54151A'), extract_row(PARENT, code='x')]
    assert count_malformed(usable, extract_of(rows), EXTRACT) == {'read_rows': 2,
                                                                  'unread_rows': 2}
    assert count_malformed(usable_of(), extract_of(rows), EXTRACT) == {'read_rows': 0,
                                                                       'unread_rows': 4}


# ---- pair statuses

same_uei = ([report(sub_uei=PRIME)], [extract_row(PRIME, code='236220')])
group = ([report(sub_parent_uei=PRIME)], ELIGIBLE_ROWS)
prime_not_in_sam = ([report()], [extract_row(SUB)])
sub_conflict = ([report()], [extract_row(PRIME, code='236220'), extract_row(SUB, code='541511'),
                             extract_row(SUB, code='541512')])
both_eligible = ([report()], ELIGIBLE_ROWS)
self_link_in_group = ([report(sub_uei=PRIME, sub_parent_uei=PRIME)],
                      [extract_row(PRIME, code='236220')])


@pytest.mark.parametrize('case, status', [
    (same_uei, 'self_link'), (group, 'intra_group'), (prime_not_in_sam, 'prime_ineligible'),
    (sub_conflict, 'sub_ineligible'), (both_eligible, 'eligible'),
    (self_link_in_group, 'self_link')])
def test_pair_statuses_follow_the_spec_order(case, status):
    records, rows = case
    assert pair_table_of(records, rows)['pair_status'].to_list() == [status]


@pytest.mark.parametrize('records, rows, status', [
    ([report(sub_parent_uei=PRIME)], [extract_row(SUB)], 'intra_group'),
    ([report(prime_parent_uei=SUB)], [], 'intra_group'),
    ([report(sub_uei=PRIME)], [], 'self_link'),
    ([report()], [], 'prime_ineligible'),
    ([report()], [extract_row(PRIME, update='20200101'), extract_row(SUB, code='')],
     'prime_ineligible')])
def test_an_earlier_pair_status_wins(records, rows, status):
    assert pair_table_of(records, rows)['pair_status'].to_list() == [status]


@pytest.mark.parametrize('records, rows, flag, status', [
    ([report(sub_uei=PRIME, sub_parent_uei=PRIME)], [], True, 'self_link'),
    ([report(sub_uei=PRIME, prime_parent_uei=PRIME)], [], True, 'self_link'),
    ([report(sub_uei=PRIME)], [], False, 'self_link'),
    ([report(sub_parent_uei=PRIME)], [], True, 'intra_group'),
    ([report()], [], False, 'prime_ineligible'),
    ([report()], [extract_row(PRIME, code='236220')], False, 'sub_ineligible'),
    ([report()], ELIGIBLE_ROWS, False, 'eligible')])
def test_the_group_flag_is_recorded_for_every_pair(records, rows, flag, status):
    table = pair_table_of(records, rows)
    assert table.select('flag_intra_group', 'pair_status').rows() == [(flag, status)]


def test_a_pair_counts_its_usable_reports_by_their_own_fiscal_year():
    records = [report(file_year=2024, action_date='2024-01-05'),
               report(file_year=2024, action_date='2024-10-01'),
               report(file_year=2025, action_date='2025-11-01'),
               report(file_year=2026, action_date='2026-02-01'),
               report(file_year=2026, action_date='2026-03-01'),
               report(file_year=2025, action_date='2025-01-01'),
               report(file_year=2024, action_date='2023-09-30'),
               report(file_year=2025, prime_uei='')]
    table = pair_table_of(records, ELIGIBLE_ROWS)
    assert table.select('n_reports', 'n_fy2024', 'n_fy2025', 'n_fy2026').rows() == [
        (6, 1, 2, 3)]


def test_duplicate_rows_are_kept_and_counted_in_the_pair():
    copy = report(row_digest='d' * 64)
    assert reported_of(copy, copy, report()).collect().height == 3
    table = pair_table_of([copy, copy, report()], ELIGIBLE_ROWS)
    assert table.select('n_reports', 'n_fy2024').rows() == [(3, 3)]


def test_amount_sum_keeps_cents_and_skips_unparseable_amounts():
    records = [report(amount=amount) for amount in ('100.50', '-20', '1,000', '')]
    table = pair_table_of(records, ELIGIBLE_ROWS)
    assert table.schema['amount_sum'] == AMOUNT_TYPE
    assert table['amount_sum'].to_list() == [Decimal('80.50')]
    assert str(table['amount_sum'][0]) == '80.50'
    counts = counts_of(records, ELIGIBLE_ROWS)
    assert counts['reports']['total']['amount_unparseable'] == 2


def test_a_pair_whose_amounts_all_fail_sums_to_zero():
    records = [report(amount='n/a'), report(amount=''),
               report(sub_uei=FIRM, amount='1.005'), report(sub_uei=FIRM, amount='0.01')]
    table = pair_table_of(records, ELIGIBLE_ROWS)
    assert [str(value) for value in table['amount_sum']] == ['0.00', '0.01']


def test_pair_node_ids_and_statuses_come_from_each_firm():
    cases = [
        ([extract_row(PRIME, code='236220'), extract_row(SUB, code='541511')],
         (NODE_PREFIX + '236220', NODE_PREFIX + '541511', 'eligible', 'eligible', 'eligible')),
        ([extract_row(PRIME, code='236220'), extract_row(SUB, code='517311')],
         (NODE_PREFIX + '236220', None, 'eligible', 'naics_not_2022', 'sub_ineligible')),
        ([extract_row(SUB, code='541511')],
         (None, NODE_PREFIX + '541511', 'not_in_sam', 'eligible', 'prime_ineligible')),
        ([extract_row(PRIME, code=''), extract_row(SUB, update='')],
         (None, None, 'naics_missing', 'dnb_era_record', 'prime_ineligible'))]
    for rows, expected in cases:
        table = pair_table_of([report()], rows)
        assert table.select('prime_node_id', 'sub_node_id', 'prime_status', 'sub_status',
                            'pair_status').rows() == [expected]


def test_padded_ueis_form_one_pair_and_one_group():
    records = [report(prime_uei=f' {PRIME}', sub_uei=f'{SUB}\t'), report(),
               report(prime_uei=f'\x0b{PRIME}', sub_uei=f'{PRIME} '),
               report(prime_uei=f'{PRIME}\r\n', sub_uei=FIRM, sub_parent_uei=PRIME)]
    table = pair_table_of(records, ELIGIBLE_ROWS + [extract_row(FIRM, code='541512')])
    assert table.select('prime_uei', 'sub_uei', 'n_reports', 'flag_intra_group',
                        'pair_status').rows() == [
        (PRIME, PRIME, 1, False, 'self_link'), (PRIME, SUB, 2, False, 'eligible'),
        (PRIME, FIRM, 1, True, 'intra_group')]


def test_the_pair_table_has_sorted_unique_keys_in_its_schema():
    primes = [f'P{number:011d}' for number in range(6)]
    subs = [f'S{number:011d}' for number in range(6)]
    records = [report(prime_uei=prime, sub_uei=sub) for prime in primes for sub in subs]
    records += records[:5]
    random.Random(11).shuffle(records)
    table = pair_table_of(records, [])
    assert list(table.schema.items()) == list(PAIR_SCHEMA.items())
    assert table.select('prime_uei', 'sub_uei').rows() == [
        (prime, sub) for prime in primes for sub in subs]
    assert table['n_reports'].sum() == 41
    empty = pair_table_of([], [])
    assert list(empty.schema.items()) == list(PAIR_SCHEMA.items())
    assert empty.height == 0


# ---- validate_pairs

VALID_RECORDS = [report(), report(file_year=2025, action_date='2025-03-01'),
                 report(sub_uei=PRIME), report(sub_uei=FIRM, sub_parent_uei=PRIME),
                 report(prime_uei=OTHER), report(sub_uei=PARENT),
                 report(file_year=2026, action_date='2026-03-01')]
VALID_ROWS = [extract_row(PRIME, code='236220'), extract_row(SUB, code='541511'),
              extract_row(FIRM, code='541512')]


def valid_table():
    '''Five pairs, one in each pair status, from seven usable reports, in key order:
    self_link, eligible, intra_group, sub_ineligible, prime_ineligible.'''
    table = pair_table_of(VALID_RECORDS, VALID_ROWS)
    assert table['pair_status'].to_list() == ['self_link', 'eligible', 'intra_group',
                                              'sub_ineligible', 'prime_ineligible']
    return table


def test_validate_pairs_accepts_the_pair_table():
    assert validate_pairs(valid_table(), 7) is None
    assert validate_pairs(pair_table_of([], []), 0) is None


def test_validate_pairs_catches_lost_or_multiplied_reports():
    table = valid_table()
    with exactly('pair reports differ from the usable reports'):
        validate_pairs(table.slice(1), 7)
    counts = ['n_reports', 'n_fy2024', 'n_fy2025', 'n_fy2026']
    multiplied = table.with_columns(pl.col(column) * 2 for column in counts)
    with exactly('pair reports differ from the usable reports'):
        validate_pairs(multiplied, 7)
    for usable_reports in (6, 8):
        with exactly('pair reports differ from the usable reports'):
            validate_pairs(table, usable_reports)


def _breaks():
    '''Each break as a function of the valid table, with the message it must raise.'''
    schema = 'pair table schema differs'
    keys = 'pair keys are not unique and sorted'
    years = 'pair fiscal-year counts differ from its reports'
    unknown = 'pair table holds an unknown status'
    rule = 'pair status differs from its rule'
    nodes = 'pair node IDs differ from the firm statuses'
    return {
        'reversed_columns': (lambda t: t.select(reversed(t.columns)), schema),
        'int_reports': (lambda t: t.with_columns(pl.col('n_reports').cast(pl.Int64)), schema),
        'float_amount': (lambda t: t.with_columns(pl.col('amount_sum').cast(pl.Float64)),
                         schema),
        'missing_column': (lambda t: t.drop('amount_sum'), schema),
        'extra_column': (lambda t: t.with_columns(extra=pl.lit(1)), schema),
        'duplicate_key': (lambda t: pl.concat([t.head(1), t]), keys),
        'unsorted_key': (lambda t: t.reverse(), keys),
        'swapped_rows': (lambda t: pl.concat([t.slice(1, 1), t.slice(0, 1), t.slice(2)]), keys),
        'fy2024_count': (lambda t: set_value(set_value(t, 1, 'n_fy2024', 2), 4, 'n_fy2024', 0),
                         years),
        'fy2025_count': (lambda t: set_value(set_value(t, 1, 'n_fy2025', 0), 4, 'n_fy2025', 1),
                         years),
        'fy2026_count': (lambda t: set_value(set_value(t, 1, 'n_fy2026', 0), 4, 'n_fy2026', 1),
                         years),
        'pair_status': (lambda t: set_value(t, 1, 'pair_status', 'unknown'), unknown),
        'null_pair_status': (lambda t: set_value(t, 1, 'pair_status', None), unknown),
        'prime_status': (lambda t: set_value(t, 4, 'prime_status', 'unknown'), unknown),
        'sub_status': (lambda t: set_value(t, 3, 'sub_status', None), unknown),
        'self_as_group': (lambda t: set_value(t, 0, 'pair_status', 'intra_group'), rule),
        'group_as_eligible': (lambda t: set_value(t, 2, 'pair_status', 'eligible'), rule),
        'group_flag_lost': (lambda t: set_value(t, 2, 'flag_intra_group', False), rule),
        'group_flag_added': (lambda t: set_value(t, 1, 'flag_intra_group', True), rule),
        'prime_as_sub': (lambda t: set_value(t, 4, 'pair_status', 'sub_ineligible'), rule),
        'sub_as_eligible': (lambda t: set_value(t, 3, 'pair_status', 'eligible'), rule),
        'eligible_as_prime': (lambda t: set_value(t, 1, 'pair_status', 'prime_ineligible'),
                              rule),
        'prime_firm_changed': (lambda t: set_value(set_value(t, 1, 'prime_status', 'not_in_sam'),
                                                   1, 'prime_node_id', None), rule),
        'sub_firm_changed': (lambda t: set_value(set_value(t, 1, 'sub_status', 'naics_missing'),
                                                 1, 'sub_node_id', None), rule),
        'prime_node_missing': (lambda t: set_value(t, 1, 'prime_node_id', None), nodes),
        'prime_node_extra': (lambda t: set_value(t, 4, 'prime_node_id', NODE_PREFIX + '541511'),
                             nodes),
        'sub_node_missing': (lambda t: set_value(t, 1, 'sub_node_id', None), nodes),
        'sub_node_extra': (lambda t: set_value(t, 3, 'sub_node_id', NODE_PREFIX + '541511'),
                           nodes),
    }


@pytest.mark.parametrize('name', list(_breaks()))
def test_validate_pairs_rejects(name):
    change, message = _breaks()[name]
    with exactly(message):
        validate_pairs(change(valid_table()), 7)


# ---- report counts

KNOWN = {
    'P1': 'AAAAAAAAAAA1', 'P2': 'AAAAAAAAAAA2', 'S1': 'BBBBBBBBBBB1', 'S2': 'BBBBBBBBBBB2',
    'S3': 'BBBBBBBBBBB3', 'S4': 'BBBBBBBBBBB4', 'S5': 'BBBBBBBBBBB5', 'B1': 'CCCCCCCCCCC1',
    'X1': 'DDDDDDDDDDD1', 'G1': 'EEEEEEEEEEE1'}


def known(year, prime, sub, action_date, **fields):
    return report(file_year=year, prime_uei=KNOWN.get(prime, prime),
                  sub_uei=KNOWN.get(sub, sub), action_date=action_date, **fields)


COPY = {'row_digest': 'a' * 64}
KNOWN_RECORDS = [
    known(2024, 'P1', 'S1', '2024-01-05', amount='10.25', report_id='R1',
          subaward_naics='541511', prime_naics='236220', **COPY),
    known(2024, 'P1', 'S1', '2024-01-05', amount='10.25', report_id='R1',
          subaward_naics='541511', prime_naics='236220', **COPY),
    known(2024, 'P2', 'S2', '2024-10-01', amount='1,000'),
    known(2024, '', 'S1', '2024-01-05'),
    known(2024, 'P1', 'G1', '2023-09-30'),
    known(2025, 'P1', 'S3', '2025-03-01', amount='-5'),
    known(2025, 'B1', 'S4', '2025-04-01'),
    known(2025, 'P1', 'S1', 'bad'),
    known(2025, 'P1', 'S1', '2025-01-05', **COPY),
    known(2026, 'P1', 'B1', '2026-01-15', amount='7'),
    known(2026, 'B1', 'S5', '2026-02-01'),
    known(2026, 'B1', 'S1', '2026-09-30', sub_parent_uei=KNOWN['B1']),
    known(2026, 'P1', 'B1', '2026-10-01'),
    known(2026, 'P1', 'P1', '2026-03-01')]
KNOWN_ROWS = [
    extract_row(KNOWN['P1'], code='236220'),
    extract_row(KNOWN['S1'], code=''), extract_row(KNOWN['S1'], code='541511'),
    extract_row(KNOWN['S2'], code='517311', string='236220Y'),
    extract_row(KNOWN['S3'], code='541511'), extract_row(KNOWN['S3'], code='541512'),
    extract_row(KNOWN['S4'], code=''),
    extract_row(KNOWN['S5'], update='', code='54151A'),
    extract_row(KNOWN['B1'], code='541512', status='E'),
    extract_row(KNOWN['X1'], code='5415'),
    extract_row(KNOWN['G1'], code='54151A')]


NO_TRIGGER = {'naics_not_2022': 0, 'with_code': 0, 'share': None}


def tally(statuses, **counts):
    return {status: counts.get(status, 0) for status in statuses}


def test_report_counts_partitions_sum_to_their_totals():
    counts = counts_of(KNOWN_RECORDS, KNOWN_ROWS)
    sections = [*counts['reports']['by_file_year'].values(), counts['reports']['total']]
    assert list(counts['reports']['by_file_year']) == ['2024', '2025', '2026']
    for section in sections:
        assert set(section['by_status']) == set(REPORT_STATUSES)
        assert sum(section['by_status'].values()) == section['rows']
        assert sum(section['by_month'].values()) <= section['rows']
    total = counts['reports']['total']
    for key in ('rows', 'duplicate_rows', 'outside_file_year', 'amount_unparseable'):
        assert sum(section[key] for section in sections[:3]) == total[key]
    for status in REPORT_STATUSES:
        assert sum(section['by_status'][status] for section in sections[:3]) == (
            total['by_status'][status])
    assert sum(counts['usable_by_fiscal_year'].values()) == total['by_status']['usable']
    firm_table = firms(usable_of(*KNOWN_RECORDS), extract_of(KNOWN_ROWS), EXTRACT, NODE_IDS)
    for role, column in (('prime', 'is_prime'), ('subcontractor', 'is_sub')):
        assert set(counts['firms'][role]) == set(FIRM_STATUSES)
        assert sum(counts['firms'][role].values()) == firm_table[column].sum()
    assert sum(counts['firms']['all'].values()) == firm_table.height
    pair_tally = {key: value for key, value in counts['pairs'].items() if key != 'total'}
    assert set(pair_tally) == set(PAIR_STATUSES)
    assert sum(pair_tally.values()) == counts['pairs']['total']
    extract = counts['extract']
    codes = extract['primary_codes']
    assert codes['blank'] + codes['well_formed'] + codes['malformed'] == extract['rows']
    assert codes['in_2022'] <= codes['well_formed']
    assert sum(extract['by_registration_status'].values()) == extract['rows']
    assert sum(extract['last_update_by_year'].values()) == extract['rows']
    assert sum(extract['evs_source'].values()) == extract['rows']
    assert sum(extract['rows_per_uei'].values()) == len({row['uei'] for row in KNOWN_ROWS})


def test_report_counts_on_a_known_window():
    counts = counts_of(KNOWN_RECORDS, KNOWN_ROWS)
    assert counts['usable_by_fiscal_year'] == {'2024': 2, '2025': 4, '2026': 4}
    assert counts['firms'] == {
        'prime': tally(FIRM_STATUSES, not_in_sam=1, eligible=2),
        'subcontractor': tally(FIRM_STATUSES, dnb_era_record=1, naics_missing=1,
                               naics_conflict=1, naics_not_2022=1, eligible=3),
        'all': tally(FIRM_STATUSES, not_in_sam=1, dnb_era_record=1, naics_missing=1,
                     naics_conflict=1, naics_not_2022=1, eligible=3),
        'mixed_blank': 1, 'last_update_invalid': 1, 'code_not_in_string': 1}
    assert counts['pairs'] == tally(PAIR_STATUSES, self_link=1, intra_group=1,
                                    prime_ineligible=1, sub_ineligible=3, eligible=2) | {
        'total': 8}
    assert counts['join_coverage'] == {
        'prime': {'eligible': 2, 'total': 3, 'share': 2 / 3},
        'subcontractor': {'eligible': 3, 'total': 7, 'share': 3 / 7},
        'by_fiscal_year': {
            '2024': {'prime': {'eligible': 1, 'total': 1, 'share': 1.0},
                     'subcontractor': {'eligible': 1, 'total': 1, 'share': 1.0}},
            '2025': {'prime': {'eligible': 2, 'total': 3, 'share': 2 / 3},
                     'subcontractor': {'eligible': 1, 'total': 4, 'share': 0.25}},
            '2026': {'prime': {'eligible': 2, 'total': 2, 'share': 1.0},
                     'subcontractor': {'eligible': 3, 'total': 4, 'share': 0.75}}}}
    assert counts['trigger'] == {
        'naics_not_2022': 1, 'with_code': 5, 'share': 0.2,
        'by_fiscal_year': {'2024': {'naics_not_2022': 0, 'with_code': 2, 'share': 0.0},
                           '2025': {'naics_not_2022': 1, 'with_code': 5, 'share': 0.2},
                           '2026': {'naics_not_2022': 0, 'with_code': 3, 'share': 0.0}}}
    assert counts['extract'] == {
        'rows': 11, 'by_registration_status': {'A': 10, 'E': 1},
        'rows_per_uei': {'1': 7, '2': 2, '3+': 0},
        'last_update_by_year': {'2024': 10, 'invalid': 1}, 'evs_source': {'': 11},
        'primary_codes': {'blank': 2, 'well_formed': 6, 'in_2022': 5, 'malformed': 3},
        'malformed_unread_rows': 3}
    assert counts['missing_fields'] == {
        'subawards': {'2024': [], '2025': [], '2026': ['subaward_naics']}, 'extract': []}


def test_report_sections_on_a_known_window():
    sections = counts_of(KNOWN_RECORDS, KNOWN_ROWS)['reports']
    no_ueis = {'prime': 0, 'sub': 0}
    assert sections['by_file_year']['2024'] == {
        'rows': 5,
        'by_status': tally(REPORT_STATUSES, uei_unusable=1, outside_window=1, usable=3),
        'duplicate_rows': 1, 'outside_file_year': 2, 'amount_unparseable': 1,
        'blank_uei': {'prime': 1, 'sub': 0}, 'malformed_uei': no_ueis,
        'by_month': {'2023-09': 1, '2024-01': 3, '2024-10': 1}, 'distinct_report_ids': 1,
        'subaward_naics_equal_prime': {'both': 2, 'equal': 0}}
    assert sections['by_file_year']['2025'] == {
        'rows': 4, 'by_status': tally(REPORT_STATUSES, action_date_invalid=1, usable=3),
        'duplicate_rows': 1, 'outside_file_year': 0, 'amount_unparseable': 2,
        'blank_uei': no_ueis, 'malformed_uei': no_ueis,
        'by_month': {'2025-01': 1, '2025-03': 1, '2025-04': 1}, 'distinct_report_ids': 0,
        'subaward_naics_equal_prime': {'both': 0, 'equal': 0}}
    assert sections['by_file_year']['2026'] == {
        'rows': 5, 'by_status': tally(REPORT_STATUSES, outside_window=1, usable=4),
        'duplicate_rows': 0, 'outside_file_year': 1, 'amount_unparseable': 3,
        'blank_uei': no_ueis, 'malformed_uei': no_ueis,
        'by_month': {'2026-01': 1, '2026-02': 1, '2026-03': 1, '2026-09': 1, '2026-10': 1},
        'distinct_report_ids': 0, 'subaward_naics_equal_prime': None}
    assert sections['total'] == {
        'rows': 14,
        'by_status': tally(REPORT_STATUSES, uei_unusable=1, action_date_invalid=1,
                           outside_window=2, usable=10),
        'duplicate_rows': 2, 'outside_file_year': 3, 'amount_unparseable': 6,
        'blank_uei': {'prime': 1, 'sub': 0}, 'malformed_uei': no_ueis,
        'by_month': {'2023-09': 1, '2024-01': 3, '2024-10': 1, '2025-01': 1, '2025-03': 1,
                     '2025-04': 1, '2026-01': 1, '2026-02': 1, '2026-03': 1, '2026-09': 1,
                     '2026-10': 1},
        'distinct_report_ids': 1, 'subaward_naics_equal_prime': None}


def test_duplicates_count_in_the_file_year_of_the_later_copy():
    a, b, c = 'a' * 64, 'b' * 64, 'c' * 64
    records = [report(file_year=2025, row_digest=a), report(file_year=2024, row_digest=a),
               report(file_year=2026, row_digest=b), report(file_year=2024, row_digest=b),
               report(file_year=2024, row_digest=b), report(file_year=2026, row_digest=c),
               report(file_year=2026, row_digest=c), report(file_year=2026, row_digest=c),
               report(file_year=2025)]
    sections = counts_of(records, [])['reports']
    assert {year: section['duplicate_rows']
            for year, section in sections['by_file_year'].items()} == {
        '2024': 1, '2025': 1, '2026': 3}
    assert sections['total']['duplicate_rows'] == 5


def test_outside_file_year_and_months_count_every_valid_date():
    records = [report(file_year=2024, action_date='2024-10-01'),
               report(file_year=2024, action_date='2023-09-30'),
               report(file_year=2024, action_date='2024-02-30'),
               report(file_year=2024, prime_uei='', action_date='2023-12-01'),
               report(file_year=2024, prime_uei='', action_date='2024-11-01'),
               report(file_year=2025, action_date=' 2024-09-30 '),
               report(file_year=2026, action_date='2026-01-01')]
    sections = counts_of(records, [])['reports']
    years = sections['by_file_year']
    assert [years[year]['outside_file_year'] for year in ('2024', '2025', '2026')] == [3, 1, 0]
    assert years['2024']['by_month'] == {'2023-09': 1, '2023-12': 1, '2024-10': 1,
                                         '2024-11': 1}
    assert years['2025']['by_month'] == {'2024-09': 1}
    assert sections['total']['outside_file_year'] == 4


def test_blank_and_malformed_uei_counts_by_side():
    records = [report(prime_uei=''), report(prime_uei='   '), report(sub_uei=''),
               report(prime_uei='bad'), report(sub_uei='bbbbbbbbbbb2'), report(sub_uei='BBBB'),
               report(prime_uei='', sub_uei='x'), report(prime_uei=NBSP), report(),
               report(prime_uei=f' {PRIME}\t')]
    total = counts_of(records, [])['reports']['total']
    assert (total['blank_uei'], total['malformed_uei']) == ({'prime': 3, 'sub': 1},
                                                            {'prime': 2, 'sub': 3})


def test_amount_unparseable_counts_usable_rows_only():
    records = [report(amount='1,000'), report(amount=''), report(amount='5'),
               report(prime_uei='', amount='bad'), report(action_date='2023-01-01', amount='x'),
               report(action_date='x', amount='x'),
               report(file_year=2025, action_date='2025-01-01', amount='1.234')]
    sections = counts_of(records, [])['reports']
    assert sections['by_file_year']['2024']['amount_unparseable'] == 2
    assert sections['by_file_year']['2025']['amount_unparseable'] == 1
    assert sections['total']['amount_unparseable'] == 3


def test_report_ids_and_naics_equality_follow_the_mapped_fields():
    records = [report(report_id='R1'), report(report_id=' R1 '), report(report_id='R2'),
               report(report_id=''), report(report_id='   '),
               report(file_year=2025, report_id='R1'),
               report(subaward_naics='541511', prime_naics='541511'),
               report(subaward_naics=' 541511', prime_naics='541511\t'),
               report(subaward_naics='541511', prime_naics='236220'),
               report(subaward_naics='541511', prime_naics=''),
               report(subaward_naics='', prime_naics='236220'),
               report(prime_uei='', subaward_naics='236220', prime_naics='236220'),
               report(file_year=2026, report_id='R9', subaward_naics='541511',
                      prime_naics='541511')]
    sections = counts_of(records, [])['reports']
    years = sections['by_file_year']
    assert [years[year]['distinct_report_ids'] for year in ('2024', '2025', '2026')] == [
        2, 1, 1]
    assert sections['total']['distinct_report_ids'] == 3
    assert years['2024']['subaward_naics_equal_prime'] == {'both': 4, 'equal': 3}
    assert years['2025']['subaward_naics_equal_prime'] == {'both': 0, 'equal': 0}
    assert years['2026']['subaward_naics_equal_prime'] is None
    assert sections['total']['subaward_naics_equal_prime'] is None
    mapped = dict(LAYOUTS) | with_columns({2026: LAYOUTS[2026]},
                                          subaward_naics='subaward_fsrs_report_month')
    sections = counts_of(records, [], layouts=mapped)['reports']
    assert sections['by_file_year']['2026']['subaward_naics_equal_prime'] == {'both': 1,
                                                                             'equal': 1}
    assert sections['total']['subaward_naics_equal_prime'] == {'both': 5, 'equal': 4}
    unmapped = dict(mapped) | with_columns({2025: mapped[2025]}, report_id=None,
                                           prime_naics=None)
    sections = counts_of(records, [], layouts=unmapped)['reports']
    assert sections['by_file_year']['2025']['distinct_report_ids'] is None
    assert sections['by_file_year']['2024']['distinct_report_ids'] == 2
    assert sections['total']['distinct_report_ids'] is None
    assert sections['by_file_year']['2025']['subaward_naics_equal_prime'] is None
    assert sections['by_file_year']['2026']['subaward_naics_equal_prime'] == {'both': 1,
                                                                             'equal': 1}
    assert sections['total']['subaward_naics_equal_prime'] is None


def test_the_missing_fields_are_listed_by_year():
    layouts = dict(LAYOUTS) | with_columns({2025: LAYOUTS[2025]}, report_id=None,
                                           prime_parent_uei=None)
    layout = dataclasses.replace(EXTRACT, positions=EXTRACT.positions | {'evs_source': None},
                                 evs_dnb=frozenset())
    counts = counts_of([], [], layouts=layouts, layout=layout)
    assert counts['missing_fields'] == {
        'subawards': {'2024': [], '2025': ['prime_parent_uei', 'report_id'],
                      '2026': ['subaward_naics']},
        'extract': ['evs_source']}
    assert counts['extract']['evs_source'] is None


def test_extract_counts_strip_and_tally_every_row():
    rows = [extract_row(FIRM, status='A', update='20240101', code='541511', evs='D&B'),
            extract_row(FIRM, status=' A\t', update=' 20231231', code='', evs=' D&B '),
            extract_row(f' {FIRM}', status='E', update='', code='517311', evs='SAM'),
            extract_row(OTHER, status='E', update='20220101', code='54151A'),
            extract_row(OTHER, status='E', update='2022-01-01', code='  '),
            extract_row(OTHER, status='', update='20211231', code=' 336411 '),
            extract_row(PARENT, code='336411'),
            extract_row(PRIME, code='5415' + NBSP)]
    extract = counts_of([], rows)['extract']
    assert extract == {
        'rows': 8, 'by_registration_status': {'': 1, 'A': 4, 'E': 3},
        'rows_per_uei': {'1': 2, '2': 0, '3+': 2},
        'last_update_by_year': {'2021': 1, '2022': 1, '2023': 1, '2024': 3, 'invalid': 2},
        'evs_source': {'': 5, 'D&B': 2, 'SAM': 1},
        'primary_codes': {'blank': 2, 'well_formed': 4, 'in_2022': 3, 'malformed': 2},
        'malformed_unread_rows': 2}


def test_join_coverage_counts_distinct_ueis_in_each_role_and_fiscal_year():
    p1, p2, s1, s2, b1 = 'AAAAAAAAAAA1', 'AAAAAAAAAAA2', 'BBBBBBBBBBB1', 'BBBBBBBBBBB2', FIRM
    records = [report(prime_uei=p1, sub_uei=s1), report(prime_uei=f' {p1}', sub_uei=f'{s1}\t'),
               report(prime_uei=p2, sub_uei=s2),
               report(file_year=2025, prime_uei=p1, sub_uei=b1, action_date='2025-10-01'),
               report(file_year=2025, prime_uei=b1, sub_uei=s2, action_date='2025-10-02'),
               report(prime_uei=p2, sub_uei=b1, action_date='2023-01-01')]
    rows = [extract_row(p1, code='236220'), extract_row(s1), extract_row(b1, code='541512')]
    coverage = counts_of(records, rows)['join_coverage']
    assert coverage['prime'] == {'eligible': 2, 'total': 3, 'share': 2 / 3}
    assert coverage['subcontractor'] == {'eligible': 2, 'total': 3, 'share': 2 / 3}
    assert coverage['by_fiscal_year'] == {
        '2024': {'prime': {'eligible': 1, 'total': 2, 'share': 0.5},
                 'subcontractor': {'eligible': 1, 'total': 2, 'share': 0.5}},
        '2025': {'prime': {'eligible': 0, 'total': 0, 'share': None},
                 'subcontractor': {'eligible': 0, 'total': 0, 'share': None}},
        '2026': {'prime': {'eligible': 2, 'total': 2, 'share': 1.0},
                 'subcontractor': {'eligible': 1, 'total': 2, 'share': 0.5}}}


def test_the_trigger_pools_roles_and_counts_firms_with_a_code():
    both, other = FIRM, 'FFFFFFFFFFF6'
    records = [report(prime_uei=both, sub_uei=SUB), report(prime_uei=PRIME, sub_uei=both),
               report(prime_uei=PRIME, sub_uei=OTHER), report(prime_uei=PRIME, sub_uei=PARENT),
               report(prime_uei=PRIME, sub_uei=other)]
    rows = [extract_row(both, code='517311'), extract_row(PRIME, code='236220'),
            extract_row(SUB, code='541511'), extract_row(SUB, code='541512'),
            extract_row(OTHER, code=''), extract_row(PARENT, update='20200101')]
    counts = counts_of(records, rows)
    pooled = {'naics_not_2022': 1, 'with_code': 3, 'share': 1 / 3}
    assert counts['trigger'] == pooled | {
        'by_fiscal_year': {'2024': pooled, '2025': NO_TRIGGER, '2026': NO_TRIGGER}}
    assert counts_of([], [])['trigger'] == NO_TRIGGER | {
        'by_fiscal_year': dict.fromkeys(('2024', '2025', '2026'), NO_TRIGGER)}


def test_the_trigger_is_split_by_the_reports_own_fiscal_year():
    a1, a2, b1 = PRIME, 'AAAAAAAAAAA2', FIRM
    s1, s2, s3 = SUB, 'BBBBBBBBBBB3', 'BBBBBBBBBBB4'
    records = [report(prime_uei=a1, sub_uei=s1, action_date='2024-01-05'),
               report(prime_uei=a1, sub_uei=b1, action_date='2024-10-01'),
               report(file_year=2025, prime_uei=b1, sub_uei=s2, action_date='2025-03-01'),
               report(file_year=2025, prime_uei=a2, sub_uei=s1, action_date='2025-04-01'),
               report(file_year=2026, prime_uei=a1, sub_uei=s3, action_date='2026-01-01'),
               report(file_year=2026, prime_uei=s1, sub_uei=b1, action_date='2026-02-01'),
               report(prime_uei='', sub_uei=s2, action_date='2024-02-01')]
    rows = [extract_row(a1, code='236220'), extract_row(b1, code='541512'),
            extract_row(s1, code='517311'), extract_row(s2, code='541511'),
            extract_row(s2, code='541512'), extract_row(s3, code='')]
    trigger = counts_of(records, rows)['trigger']
    assert {key: trigger[key] for key in ('naics_not_2022', 'with_code', 'share')} == {
        'naics_not_2022': 1, 'with_code': 4, 'share': 0.25}
    assert trigger['by_fiscal_year'] == {
        '2024': {'naics_not_2022': 1, 'with_code': 2, 'share': 0.5},
        '2025': {'naics_not_2022': 1, 'with_code': 4, 'share': 0.25},
        '2026': {'naics_not_2022': 1, 'with_code': 3, 'share': 1 / 3}}


def test_report_and_extract_counts_do_not_need_the_firm_and_pair_tables():
    reported = reported_of(*KNOWN_RECORDS)
    extract = extract_of(KNOWN_ROWS)
    full = counts_of(KNOWN_RECORDS, KNOWN_ROWS)
    partial = report_counts(reported, pl.DataFrame(schema=FIRM_SCHEMA),
                            pl.DataFrame(schema=PAIR_SCHEMA), extract, LAYOUTS, EXTRACT,
                            NODE_IDS)
    for key in ('reports', 'usable_by_fiscal_year', 'extract', 'missing_fields'):
        assert partial[key] == full[key]
    assert partial['trigger'] == NO_TRIGGER | {
        'by_fiscal_year': dict.fromkeys(('2024', '2025', '2026'), NO_TRIGGER)}
    assert partial['pairs']['total'] == 0


def test_report_counts_hold_no_uei_and_dump_as_strict_json():
    counts = counts_of(KNOWN_RECORDS, KNOWN_ROWS)
    text = json.dumps(counts, sort_keys=True, allow_nan=False)
    assert json.loads(text) == counts
    for uei in KNOWN.values():
        assert uei not in text
    assert 'R1' not in text
