'''TRI facility-years: the reduction, eligibility, owner keys, validator and year report.'''

import json
from dataclasses import replace

import polars as pl
import pytest
from tri_fixtures import rows_frame

from embedding_data.tri_codes import NODE_PREFIX
from embedding_data.tri_facility_years import (
    CONTRACT,
    EXCLUSIONS,
    PRIVATE,
    TABLE_SCHEMA,
    TERRITORIES,
    public,
    reduce,
    validate_facility_years,
    year_report,
)
from embedding_data.tri_layout import HeaderLayout, load_layouts

LAYOUTS = load_layouts()
# Real NAICS 2022 codes stand for the selected national-industry nodes.
CODES = ('325199', '311111', '212311')
NODES = frozenset(NODE_PREFIX + code for code in CODES)
# Synthetic rows: made-up facilities, parents and D&B numbers, never EPA data.


def form(trifd: str = 'T1', year: int = 2023, **fields: str) -> dict:
    '''One synthetic form row: Form R, not federal, in Texas, with one valid primary code.'''
    row = dict(year=year, reporting_year=str(year), trifd=trifd, form_type='R', federal='NO',
               state='TX', primary_naics='325199')
    return {**row, **fields}


def run(records: list[dict], layouts: dict[int, HeaderLayout] = LAYOUTS,
        nodes: frozenset[str] = NODES) -> pl.DataFrame:
    return reduce(rows_frame(records), layouts, nodes)


def reduce_one(records: list[dict], **options) -> dict:
    '''The one facility-year of the records.'''
    frame = run(records, **options)
    assert frame.height == 1
    return frame.row(0, named=True)


def with_values(year: int, **sets: set[str]) -> dict[int, HeaderLayout]:
    '''The production layouts, with some value sets of one year replaced.'''
    layout = LAYOUTS[year]
    values = {**layout.values, **{name: frozenset(items) for name, items in sets.items()}}
    return {**LAYOUTS, year: replace(layout, values=values)}


def with_unmapped(year: int, *fields: str) -> dict[int, HeaderLayout]:
    '''The production layouts, with some fields of one year left unmapped.'''
    layout = LAYOUTS[year]
    return {**LAYOUTS, year: replace(layout, columns={**layout.columns, **dict.fromkeys(fields)})}


def test_contract_exclusions_and_schemas_are_the_documented_ones():
    assert CONTRACT == 'tri-facility-years-v1'
    assert EXCLUSIONS == ('naics_missing', 'naics_conflict', 'naics_not_2022', 'parent_conflict',
                          'federal')
    assert TERRITORIES == ('AS', 'GU', 'MP', 'PR', 'VI')
    assert list(TABLE_SCHEMA.items()) == [
        ('reporting_year', pl.Int64), ('trifd', pl.String), ('n_forms', pl.UInt64),
        ('n_form_r', pl.UInt64), ('n_form_a', pl.UInt64),
        ('primary_naics_values', pl.List(pl.String)), ('other_naics_values', pl.List(pl.String)),
        ('naics_2022_node_id', pl.String), ('parent_names', pl.List(pl.String)),
        ('foreign_parent_names', pl.List(pl.String)), ('federal_values', pl.List(pl.String)),
        ('state_values', pl.List(pl.String)), ('flag_parent_mixed_blank', pl.Boolean),
        ('owner_key', pl.String), ('exclusion_reason', pl.String)]
    assert list(PRIVATE.items()) == [
        ('_candidate_key', pl.String), ('_membership_keys', pl.List(pl.String)),
        ('_dnb_key', pl.String), ('_reported_names', pl.List(pl.String)),
        ('_usable_dnb', pl.List(pl.String))]


def test_form_r_and_form_a_rows_reduce_to_one_facility_year():
    # three rows of T1 in 2023 (two R, one A), primary ' 325199', '325199', '325199'
    row = reduce_one([form(primary_naics=' 325199'),
                      form(form_type='A', primary_naics='325199'),
                      form(primary_naics='325199')])
    assert (row['n_forms'], row['n_form_r'], row['n_form_a']) == (3, 2, 1)
    assert row['primary_naics_values'] == ['325199']
    assert row['naics_2022_node_id'] == 'naics:2022:national_industry:325199'


def test_reduce_returns_the_table_then_the_private_columns_in_stated_dtypes():
    frame = run([form(standardized_parent='ACME')])
    assert isinstance(frame, pl.DataFrame)
    assert list(frame.schema.items()) == list(TABLE_SCHEMA.items()) + list(PRIVATE.items())


def test_reduce_groups_by_year_and_trifd_and_sorts_by_them():
    records = [form('T2'), form('T10', 2024), form('T1', 2023), form('T10'), form('T2', 2022),
               form('T1', 2023, form_type='A')]
    frame = run(records)
    assert frame.select('reporting_year', 'trifd').rows() == [
        (2022, 'T2'), (2023, 'T1'), (2023, 'T10'), (2023, 'T2'), (2024, 'T10')]
    assert frame.schema['reporting_year'] == pl.Int64
    assert frame['n_forms'].to_list() == [1, 2, 1, 1, 1]
    assert run(records[::-1]).equals(frame)


def test_a_padded_trifd_is_its_own_facility_year_and_keeps_its_padding():
    frame = run([form('T1'), form(' T1'), form('T1 ')])
    assert frame['trifd'].to_list() == [' T1', 'T1', 'T1 ']
    assert frame['owner_key'].to_list() == ['facility: T1', 'facility:T1', 'facility:T1 ']


def test_the_primary_code_is_stripped_distinct_sorted_and_never_blank():
    row = reduce_one([form(primary_naics='  325199'), form(primary_naics='325199 '),
                      form(primary_naics='311111'), form(primary_naics=''),
                      form(primary_naics='   ')])
    assert row['primary_naics_values'] == ['311111', '325199']


@pytest.mark.parametrize('field', ['naics_2', 'naics_3', 'naics_4', 'naics_5', 'naics_6'])
def test_each_secondary_code_field_is_collected_stripped(field):
    assert reduce_one([form(**{field: ' 325110 '})])['other_naics_values'] == ['325110']


def test_secondary_codes_are_distinct_and_sorted_across_fields_and_forms():
    row = reduce_one([form(naics_2='325120', naics_3='325110', naics_4=''),
                      form(naics_2='325110', naics_5='  ', naics_6='311111')])
    assert row['other_naics_values'] == ['311111', '325110', '325120']


def test_a_facility_year_without_secondary_codes_or_parents_has_empty_lists():
    row = reduce_one([form()])
    assert row['other_naics_values'] == []
    assert row['parent_names'] == []
    assert row['foreign_parent_names'] == []
    assert row['_reported_names'] == []
    assert row['_usable_dnb'] == []


def test_parent_names_are_stripped_distinct_sorted_and_case_sensitive():
    row = reduce_one([form(standardized_parent=' beta'), form(standardized_parent='Acme '),
                      form(standardized_parent='ACME'), form(standardized_parent='Acme'),
                      form(standardized_parent='na'), form(standardized_parent='Acme  Corp')])
    assert row['parent_names'] == ['ACME', 'Acme', 'Acme  Corp', 'beta', 'na']


@pytest.mark.parametrize('field, column', [
    ('standardized_parent', 'parent_names'),
    ('standardized_foreign_parent', 'foreign_parent_names'),
    ('parent_name', '_reported_names')])
@pytest.mark.parametrize('absent', ['', '   ', 'NA', ' NA ', '\tNA'])
def test_blank_and_no_parent_strings_are_never_a_name(field, column, absent):
    row = reduce_one([form(**{field: absent}), form(**{field: 'Beta'})])
    assert row[column] == ['Beta']
    assert reduce_one([form(**{field: absent})])[column] == []


@pytest.mark.parametrize('field, column', [
    ('standardized_foreign_parent', 'foreign_parent_names'),
    ('parent_name', '_reported_names')])
def test_foreign_and_reported_names_are_stripped_distinct_and_sorted(field, column):
    row = reduce_one([form(**{field: ' Zed'}), form(**{field: 'Alpha '}), form(**{field: 'Zed'}),
                      form(**{field: 'alpha'})])
    assert row[column] == ['Alpha', 'Zed', 'alpha']


def test_foreign_parent_names_are_empty_for_2022():
    # The reader reads the unmapped 2022 foreign field as ''.
    frame = run([form('T1', 2022), form('T1', 2023, standardized_foreign_parent='ACME ABROAD'),
                 form('T1', 2024, standardized_foreign_parent=' NA ')])
    assert frame['foreign_parent_names'].to_list() == [[], ['ACME ABROAD'], []]


def test_federal_and_state_values_are_distinct_sorted_and_as_delivered():
    row = reduce_one([form(federal='YES', state='TX'), form(federal='NO', state=' TX'),
                      form(federal='YES', state='OK'), form(state=''), form(state='TX')])
    assert row['federal_values'] == ['NO', 'YES']
    assert row['state_values'] == ['', ' TX', 'OK', 'TX']


@pytest.mark.parametrize('parents, flag', [
    (['Acme Corp', 'NA'], True),
    (['NA', 'Acme Corp'], True),
    (['Acme Corp', ''], True),
    (['Acme Corp', '   '], True),
    (['Acme Corp', ' NA '], True),
    (['Acme Corp', 'Acme Corp', 'NA'], True),
    (['Acme Corp', 'Beta Inc', 'NA'], True),
    (['Acme Corp'], False),
    (['Acme Corp', 'Acme Corp'], False),
    (['Acme Corp', 'Beta Inc'], False),
    (['NA'], False),
    (['NA', 'NA'], False),
    ([''], False),
    (['NA', ''], False)])
def test_mixed_blank_flag_needs_a_named_row_and_a_no_parent_row(parents, flag):
    row = reduce_one([form(standardized_parent=parent) for parent in parents])
    assert row['flag_parent_mixed_blank'] is flag


def test_mixed_blank_keeps_the_named_parent_and_flags():
    row = reduce_one([form(standardized_parent='Acme Corp'), form(standardized_parent='NA')])
    assert row['owner_key'] == 'parent:Acme Corp'
    assert row['flag_parent_mixed_blank'] is True
    assert row['parent_names'] == ['Acme Corp']
    assert row['exclusion_reason'] is None


@pytest.mark.parametrize('values', [['YES', 'NO', 'NO'], ['NO', 'YES', 'NO'],
                                    ['NO', 'NO', 'YES'], ['YES'], ['YES', 'YES']])
def test_any_federal_form_makes_the_facility_year_federal(values):
    row = reduce_one([form(federal=value) for value in values])
    assert row['exclusion_reason'] == 'federal'
    assert row['owner_key'] is None
    assert row['federal_values'] == sorted(set(values))


def test_no_federal_form_leaves_the_facility_year_eligible():
    row = reduce_one([form(federal='NO'), form(federal='NO')])
    assert row['exclusion_reason'] is None
    assert row['federal_values'] == ['NO']


no_primary = [form(primary_naics='')]
two_primaries = [form(primary_naics='325199'), form(primary_naics='311111')]
primary_999999 = [form(primary_naics='999999')]
two_parents = [form(standardized_parent='ACME'), form(standardized_parent='BETA')]
federal_form = [form(federal='YES')]
no_primary_and_federal = [form(primary_naics='', federal='YES')]
two_primaries_two_parents = [form(primary_naics='325199', standardized_parent='ACME'),
                             form(primary_naics='311111', standardized_parent='BETA')]
bad_code_two_parents = [form(primary_naics='999999', standardized_parent='ACME'),
                        form(primary_naics='999999', standardized_parent='BETA')]
two_parents_federal = [form(standardized_parent='ACME', federal='YES'),
                       form(standardized_parent='BETA')]


@pytest.mark.parametrize('rows, reason', [
    (no_primary, 'naics_missing'), (two_primaries, 'naics_conflict'),
    (primary_999999, 'naics_not_2022'), (two_parents, 'parent_conflict'),
    (federal_form, 'federal'), (no_primary_and_federal, 'naics_missing'),
    (two_primaries_two_parents, 'naics_conflict'), (bad_code_two_parents, 'naics_not_2022'),
    (two_parents_federal, 'parent_conflict')])
def test_exclusion_reasons_follow_the_spec_order(rows, reason):
    row = reduce_one(rows)
    assert row['exclusion_reason'] == reason
    assert row['owner_key'] is None
    assert (row['naics_2022_node_id'] is not None) == (reason in ('parent_conflict', 'federal'))


@pytest.mark.parametrize('rows, reason', [
    ([form(primary_naics='', standardized_parent='ACME'),
      form(primary_naics='', standardized_parent='BETA')], 'naics_missing'),
    ([form(primary_naics='325199', federal='YES'),
      form(primary_naics='311111')], 'naics_conflict'),
    ([form(primary_naics='999999', federal='YES')], 'naics_not_2022'),
    ([form(primary_naics='999999'), form(primary_naics='888888')], 'naics_conflict'),
    ([form(primary_naics='   '), form(primary_naics='')], 'naics_missing'),
    ([form(standardized_parent='ACME'), form(standardized_parent='ACME', federal='NO')], None),
    ([form(standardized_parent='NA'), form(standardized_parent='')], None)])
def test_exclusion_reason_is_the_first_failing_rule_and_null_when_none_fails(rows, reason):
    assert reduce_one(rows)['exclusion_reason'] == reason


def test_an_eligible_facility_year_keeps_its_node_and_parent_owner_key():
    row = reduce_one([form(primary_naics='311111', standardized_parent='ACME')])
    assert row['exclusion_reason'] is None
    assert row['naics_2022_node_id'] == 'naics:2022:national_industry:311111'
    assert row['owner_key'] == 'parent:ACME'


@pytest.mark.parametrize('primary, node', [
    ('325199', NODE_PREFIX + '325199'), (' 311111 ', NODE_PREFIX + '311111'),
    ('999999', None), ('', None), ('32519', None), ('3251990', None), ('32519A', None),
    ('325 199', None), ('325199\n', NODE_PREFIX + '325199')])
def test_the_node_id_is_the_prefixed_primary_code_when_it_is_a_six_digit_selected_node(
        primary, node):
    short = NODE_PREFIX + '32519'
    long = NODE_PREFIX + '3251990'
    lettered = NODE_PREFIX + '32519A'
    spaced = NODE_PREFIX + '325 199'
    odd_nodes = NODES | {short, long, lettered, spaced}
    row = reduce_one([form(primary_naics=primary)], nodes=odd_nodes)
    assert row['naics_2022_node_id'] == node
    assert row['exclusion_reason'] == (None if node else (
        'naics_missing' if primary == '' else 'naics_not_2022'))


def test_a_valid_code_outside_the_selected_nodes_is_not_a_2022_code():
    nodes = frozenset({NODE_PREFIX + '311111'})
    assert reduce_one([form(primary_naics='325199')], nodes=nodes)[
        'exclusion_reason'] == 'naics_not_2022'
    assert reduce_one([form(primary_naics='311111')], nodes=nodes)[
        'exclusion_reason'] is None


def test_no_node_id_without_exactly_one_primary_value():
    assert reduce_one(no_primary)['naics_2022_node_id'] is None
    assert reduce_one(two_primaries)['naics_2022_node_id'] is None


@pytest.mark.parametrize('rows, candidate, membership', [
    ([form()], 'facility:T1', ['facility:T1']),
    ([form(standardized_parent='NA'), form(standardized_parent='')], 'facility:T1',
     ['facility:T1']),
    ([form(standardized_parent='ACME'), form(standardized_parent=' ACME ')], 'parent:ACME',
     ['parent:ACME']),
    ([form(standardized_parent='ACME'), form(standardized_parent='NA')], 'parent:ACME',
     ['parent:ACME']),
    ([form(standardized_parent='BETA'), form(standardized_parent='ACME')], None,
     ['parent:ACME', 'parent:BETA']),
    ([form(standardized_parent='C'), form(standardized_parent='A'),
      form(standardized_parent='B')], None, ['parent:A', 'parent:B', 'parent:C'])])
def test_candidate_and_membership_keys(rows, candidate, membership):
    row = reduce_one(rows)
    assert row['_candidate_key'] == candidate
    assert row['_membership_keys'] == membership


def test_candidate_and_membership_keys_exist_for_an_excluded_facility_year():
    row = reduce_one([form(primary_naics='', standardized_parent='ACME')])
    assert row['exclusion_reason'] == 'naics_missing'
    assert row['owner_key'] is None
    assert row['_candidate_key'] == 'parent:ACME'
    assert row['_membership_keys'] == ['parent:ACME']


def test_owner_key_is_the_candidate_key_only_for_an_eligible_facility_year():
    frame = run([form('T1', standardized_parent='ACME'), form('T2', federal='YES',
                                                              standardized_parent='ACME'),
                 form('T3', primary_naics='999999')])
    assert frame['_candidate_key'].to_list() == ['parent:ACME', 'parent:ACME', 'facility:T3']
    assert frame['owner_key'].to_list() == ['parent:ACME', None, None]


def test_no_parent_strings_never_share_a_key():
    # T1 and T2 both give a no_parent string in 2023
    frame = run([form('T1', standardized_parent='NA'), form('T2', standardized_parent='NA')])
    keys = frame['owner_key'].to_list()
    assert keys == ['facility:T1', 'facility:T2']


def test_blank_standardized_parents_never_share_a_key():
    frame = run([form('T1', standardized_parent=''), form('T2', standardized_parent='  ')])
    assert frame['owner_key'].to_list() == ['facility:T1', 'facility:T2']


def test_facilities_with_the_same_exact_parent_name_share_a_key_and_others_do_not():
    frame = run([form('T1', standardized_parent='ACME'), form('T2', standardized_parent='ACME'),
                 form('T3', standardized_parent='Acme')])
    assert frame['owner_key'].to_list() == ['parent:ACME', 'parent:ACME', 'parent:Acme']


@pytest.mark.parametrize('numbers, usable, key', [
    ([], [], 'facility:T1'),
    ([''], [], 'facility:T1'),
    (['   '], [], 'facility:T1'),
    (['NA'], [], 'facility:T1'),
    ([' NA '], [], 'facility:T1'),
    (['NA', 'NA'], [], 'facility:T1'),
    (['001234567'], ['001234567'], 'dnb:001234567'),
    ([' 001234567 '], ['001234567'], 'dnb:001234567'),
    (['001234567', '001234567'], ['001234567'], 'dnb:001234567'),
    (['001234567', ' 001234567'], ['001234567'], 'dnb:001234567'),
    (['NA', '001234567'], ['001234567'], 'dnb:001234567'),
    (['001234567', ''], ['001234567'], 'dnb:001234567'),
    (['001234567', '009876543'], ['001234567', '009876543'], 'facility:T1'),
    (['009876543', '001234567', 'NA'], ['001234567', '009876543'], 'facility:T1')])
def test_dnb_key_needs_exactly_one_usable_number(numbers, usable, key):
    row = reduce_one([form(parent_dnb=number) for number in numbers] or [form()])
    assert row['_usable_dnb'] == usable
    assert row['_dnb_key'] == key


def test_the_dnb_key_does_not_depend_on_exclusion_or_the_parent():
    frame = run([form('T1', primary_naics='', parent_dnb='001234567'),
                 form('T2', federal='YES', parent_dnb='001234568', standardized_parent='ACME')])
    assert frame['exclusion_reason'].to_list() == ['naics_missing', 'federal']
    assert frame['_dnb_key'].to_list() == ['dnb:001234567', 'dnb:001234568']


def test_reported_names_are_a_separate_diagnostic_from_the_standardized_parent():
    row = reduce_one([form(parent_name=' Acme Inc ', standardized_parent='ACME'),
                      form(parent_name='NA', standardized_parent='ACME'),
                      form(parent_name='Acme Inc', standardized_parent='NA')])
    assert row['_reported_names'] == ['Acme Inc']
    assert row['parent_names'] == ['ACME']


ODD_SETS = dict(form_r={'RR'}, form_a={'AA'}, federal_yes={'Y'}, federal_no={'N'},
                no_parent={'NONE'}, no_dnb={'0'})


def test_each_year_reads_its_own_registered_strings():
    layouts = with_values(2024, **ODD_SETS)
    frame = run([
        form('T1', 2023, standardized_parent='NA', parent_dnb='NA'),
        form('T2', 2023, standardized_parent='NONE', parent_dnb='0'),
        form('T1', 2024, form_type='AA', federal='N', standardized_parent='NONE', parent_dnb='0'),
        form('T2', 2024, form_type='RR', federal='Y', standardized_parent='NA', parent_dnb='NA'),
    ], layouts)
    assert frame['n_form_r'].to_list() == [1, 1, 0, 1]
    assert frame['n_form_a'].to_list() == [0, 0, 1, 0]
    assert frame['parent_names'].to_list() == [[], ['NONE'], [], ['NA']]
    assert frame['_usable_dnb'].to_list() == [[], ['0'], [], ['NA']]
    assert frame['exclusion_reason'].to_list() == [None, None, None, 'federal']


@pytest.mark.parametrize('year, fields, message', [
    (2024, dict(form_type='R'), 'unregistered form type'),
    (2023, dict(form_type='RR'), 'unregistered form type'),
    (2024, dict(federal='NO'), 'unregistered federal value'),
    (2023, dict(federal='Y'), 'unregistered federal value')])
def test_a_value_registered_for_another_year_fails(year, fields, message):
    layouts = with_values(2024, **ODD_SETS)
    good = dict(form_type='RR', federal='N') if year == 2024 else {}
    with pytest.raises(ValueError, match=f'^{message}$'):
        run([form('T0', year, **good), form('T1', year, **{**good, **fields})], layouts)


def test_every_value_of_a_multi_value_set_counts():
    layouts = with_values(2023, form_r={'R', 'R2'}, form_a={'A', 'A2'}, federal_yes={'YES', 'Y'},
                          federal_no={'NO', 'N'}, no_parent={'NA', 'NONE', 'N/A'},
                          no_dnb={'NA', '0'})
    row = reduce_one([form(form_type=value) for value in ('R', 'R2', 'A', 'A2', 'A2')],
                     layouts=layouts)
    assert (row['n_forms'], row['n_form_r'], row['n_form_a']) == (5, 2, 3)
    row = reduce_one([form(federal='N'), form(federal='Y')], layouts=layouts)
    assert row['exclusion_reason'] == 'federal'
    assert row['federal_values'] == ['N', 'Y']
    row = reduce_one([form(standardized_parent=value, parent_dnb='0')
                      for value in ('NA', 'NONE', 'N/A', 'ACME')], layouts=layouts)
    assert row['parent_names'] == ['ACME']
    assert row['flag_parent_mixed_blank'] is True
    assert row['_usable_dnb'] == []
    assert reduce_one([form(parent_dnb='NA'), form(parent_dnb='0')],
                      layouts=layouts)['_usable_dnb'] == []


@pytest.mark.parametrize('records, message', [
    ([form(trifd='')], 'blank trifd'),
    ([form(trifd='   ')], 'blank trifd'),
    ([form('T1'), form(trifd=' \t')], 'blank trifd'),
    ([form(form_type='X')], 'unregistered form type'),
    ([form(form_type='')], 'unregistered form type'),
    ([form(form_type='r')], 'unregistered form type'),
    ([form(form_type=' R')], 'unregistered form type'),
    ([form(), form(), form(form_type='X')], 'unregistered form type'),
    ([form(federal='')], 'unregistered federal value'),
    ([form(federal='yes')], 'unregistered federal value'),
    ([form(federal=' NO')], 'unregistered federal value'),
    ([form(federal='MAYBE')], 'unregistered federal value'),
    ([form(), form(federal='NO'), form(federal='UNKNOWN')], 'unregistered federal value')])
def test_unregistered_values_and_blank_trifd_fail(records, message):
    with pytest.raises(ValueError, match=f'^{message}$'):
        run(records)


def test_a_year_without_a_layout_fails():
    layouts = {year: layout for year, layout in LAYOUTS.items() if year != 2024}
    run([form('T1', 2022), form('T1', 2023)], layouts)
    with pytest.raises(ValueError, match='^no layout for year$'):
        run([form('T1', 2022), form('T1', 2024)], layouts)


def test_public_table_keeps_no_dnb_or_reported_names():
    frame = run([form(standardized_parent='ACME', parent_name='Reported Name',
                      parent_dnb='001234567')])
    assert list(public(frame).schema.items()) == list(TABLE_SCHEMA.items())
    assert list(frame.schema.items()) == list(TABLE_SCHEMA.items()) + list(PRIVATE.items())
    text = str(public(frame).to_dicts())
    assert '001234567' not in text
    assert 'Reported Name' not in text
    assert public(frame).equals(frame.select(list(TABLE_SCHEMA)))


def test_an_empty_input_gives_the_exact_empty_schema():
    frame = run([])
    assert frame.height == 0
    assert list(frame.schema.items()) == list(TABLE_SCHEMA.items()) + list(PRIVATE.items())
    validate_facility_years(public(frame), 0)
    assert year_report(rows_frame([]), frame, LAYOUTS) == {}


# --- the validator

VALID_RECORDS = [
    form('T1', standardized_parent='ACME'),
    form('T2'),
    form('T2', form_type='A'),
    form('T3', primary_naics=''),
    form('T4', standardized_parent='ACME'),
    form('T4', standardized_parent='BETA'),
    form('T5', federal='YES'),
    form('T6', primary_naics='325199'),
    form('T6', primary_naics='311111'),
    form('T7', primary_naics='999999'),
]


def valid_table() -> pl.DataFrame:
    return public(run(VALID_RECORDS))


def test_the_validator_accepts_a_table_with_every_exclusion_reason():
    table = valid_table()
    assert table['exclusion_reason'].to_list() == [
        None, None, 'naics_missing', 'parent_conflict', 'federal', 'naics_conflict',
        'naics_not_2022']
    validate_facility_years(table, len(VALID_RECORDS))


def swap_columns(table: pl.DataFrame) -> pl.DataFrame:
    names = table.columns
    return table.select(names[1], names[0], *names[2:])


def set_value(table: pl.DataFrame, trifd: str, column: str, value) -> pl.DataFrame:
    '''The table with one cell of the facility-year `trifd` replaced.'''
    dtype = TABLE_SCHEMA[column]
    return table.with_columns(
        pl.when(pl.col('trifd') == trifd).then(pl.lit(value, dtype=dtype))
        .otherwise(pl.col(column)).alias(column))


@pytest.mark.parametrize('build, message', [
    (lambda table: table.with_columns(extra=pl.lit(1)), 'schema differs'),
    (lambda table: table.drop('state_values'), 'schema differs'),
    (swap_columns, 'schema differs'),
    (lambda table: table.with_columns(pl.col('n_forms').cast(pl.Int64)), 'schema differs'),
    (lambda table: table.with_columns(pl.col('reporting_year').cast(pl.Int32)),
     'schema differs'),
    (lambda table: table.with_columns(pl.col('parent_names').cast(pl.List(pl.Categorical))),
     'schema differs'),
    (lambda table: table.reverse(), 'key not unique and sorted'),
    (lambda table: table.with_columns(trifd=pl.lit('T1')), 'key not unique and sorted'),
    (lambda table: table.with_columns(pl.col('trifd').replace('T1', None)),
     'key not unique and sorted'),
    (lambda table: set_value(table, 'T1', 'n_forms', 2), 'n_forms differ from source rows'),
    (lambda table: table.head(6), 'n_forms differ from source rows'),
    (lambda table: pl.concat([table, table.tail(1)]), 'key not unique and sorted'),
    (lambda table: set_value(set_value(table, 'T1', 'n_forms', 2), 'T2', 'n_forms', 1),
     'n_forms not the sum of form types'),
    (lambda table: set_value(table, 'T1', 'n_form_r', 2), 'n_forms not the sum of form types'),
    (lambda table: set_value(table, 'T2', 'n_form_a', 0), 'n_forms not the sum of form types'),
    (lambda table: set_value(table, 'T3', 'owner_key', 'facility:T3'),
     'owner_key and exclusion_reason disagree'),
    (lambda table: set_value(table, 'T5', 'owner_key', 'facility:T5'),
     'owner_key and exclusion_reason disagree'),
    (lambda table: set_value(table, 'T1', 'owner_key', None),
     'owner_key and exclusion_reason disagree'),
    (lambda table: set_value(table, 'T2', 'owner_key', None),
     'owner_key and exclusion_reason disagree'),
    (lambda table: set_value(table, 'T3', 'exclusion_reason', 'other'),
     'unknown exclusion reason'),
    (lambda table: set_value(table, 'T3', 'naics_2022_node_id', NODE_PREFIX + '325199'),
     'node ID and exclusion_reason disagree'),
    (lambda table: set_value(table, 'T6', 'naics_2022_node_id', NODE_PREFIX + '325199'),
     'node ID and exclusion_reason disagree'),
    (lambda table: set_value(table, 'T7', 'naics_2022_node_id', NODE_PREFIX + '325199'),
     'node ID and exclusion_reason disagree'),
    (lambda table: set_value(table, 'T1', 'naics_2022_node_id', None),
     'node ID and exclusion_reason disagree'),
    (lambda table: set_value(table, 'T4', 'naics_2022_node_id', None),
     'node ID and exclusion_reason disagree'),
    (lambda table: set_value(table, 'T5', 'naics_2022_node_id', None),
     'node ID and exclusion_reason disagree')])
def test_the_validator_catches_each_broken_clause(build, message):
    with pytest.raises(ValueError, match=f'^{message}$'):
        validate_facility_years(build(valid_table()), len(VALID_RECORDS))


@pytest.mark.parametrize('source_rows', [len(VALID_RECORDS) - 1, len(VALID_RECORDS) + 1, 0])
def test_validator_catches_lost_or_multiplied_rows(source_rows):
    with pytest.raises(ValueError, match='^n_forms differ from source rows$'):
        validate_facility_years(valid_table(), source_rows)


def test_the_validator_checks_the_year_before_the_trifd_in_the_sort():
    table = public(run([form('T9', 2022), form('T1', 2023)]))
    validate_facility_years(table, 2)
    with pytest.raises(ValueError, match='^key not unique and sorted$'):
        validate_facility_years(table.reverse(), 2)


# --- the year report

def report_rows() -> list[dict]:
    return [
        # F1: two forms, one parent, a foreign parent and a secondary code.
        form('F1', standardized_parent='ACME', parent_name='Acme', parent_dnb='900000001',
             standardized_foreign_parent='ACME ABROAD', naics_2='325110'),
        form('F1', standardized_parent='ACME', parent_name='Acme', parent_dnb='900000001',
             standardized_foreign_parent='ACME ABROAD'),
        # F2: the reported parent is NA but EPA names one (case a), in Puerto Rico.
        form('F2', form_type='A', standardized_parent='ACME', parent_name='NA',
             parent_dnb='900000001', state='PR'),
        # F3: a named reported parent and no standardized name (case b), one D&B number
        # and no standardized name (case c), in Guam.
        form('F3', parent_name='Zed Corp', parent_dnb='900000004', state='GU'),
        # F4: federal, in the District of Columbia.
        form('F4', federal='YES', standardized_parent='NA', parent_name='NA', parent_dnb='NA',
             state='DC'),
        # F5: one form names the parent and the other gives a no-parent string.
        form('F5', standardized_parent='BETA', parent_name='Beta', parent_dnb='900000003',
             state='VI'),
        form('F5', form_type='A', standardized_parent='NA', parent_name='NA', parent_dnb='NA',
             state='VI'),
        # F6: no primary code.
        form('F6', primary_naics='', state='MP'),
        # F7: a code outside the nodes and two D&B numbers for one name.
        form('F7', primary_naics='999999', standardized_parent='GAMMA', parent_name='Gamma',
             parent_dnb='900000001', state='AS'),
        form('F7', primary_naics='999999', standardized_parent='GAMMA', parent_name='Gamma',
             parent_dnb='900000004', state='AS'),
        # F8: two primary codes, and one form with no D&B number.
        form('F8', primary_naics='325199', standardized_parent='DELTA', parent_name='Delta',
             parent_dnb='900000005'),
        form('F8', primary_naics='311111', standardized_parent='DELTA', parent_name='Delta',
             parent_dnb=''),
        # F9: two parents.
        form('F9', standardized_parent='P1', parent_name='P1'),
        form('F9', standardized_parent='P2', parent_name='P2'),
        # Two facilities of 2022, a year with a layout that maps no foreign parent.
        form('G1', 2022, standardized_parent='ACME', parent_name='Acme', parent_dnb='900000009'),
        form('G2', 2022, form_type='A', standardized_parent='NA', parent_name='Whoever',
             parent_dnb='NA', naics_3='325120'),
    ]


EXPECTED_2022 = {
    'rows': 2, 'rows_by_form_type': {'form_r': 1, 'form_a': 1}, 'facility_years': 2,
    'facility_years_by_reason': {'eligible': 2, 'naics_missing': 0, 'naics_conflict': 0,
                                 'naics_not_2022': 0, 'parent_conflict': 0, 'federal': 0},
    'with_parent': 1, 'with_usable_dnb': 1, 'names_with_several_dnb': 0,
    'dnb_with_several_names': 0, 'mixed_blank': 0, 'with_foreign_parent': 0,
    'with_secondary_codes': 1, 'in_territories': 0, 'case_a': 0, 'case_b': 1, 'case_c': 0,
    'missing_fields': ['foreign_parent_name', 'foreign_parent_dnb',
                       'standardized_foreign_parent']}
EXPECTED_2023 = {
    'rows': 14, 'rows_by_form_type': {'form_r': 12, 'form_a': 2}, 'facility_years': 9,
    'facility_years_by_reason': {'eligible': 4, 'naics_missing': 1, 'naics_conflict': 1,
                                 'naics_not_2022': 1, 'parent_conflict': 1, 'federal': 1},
    'with_parent': 6, 'with_usable_dnb': 6, 'names_with_several_dnb': 1,
    'dnb_with_several_names': 1, 'mixed_blank': 1, 'with_foreign_parent': 1,
    'with_secondary_codes': 1, 'in_territories': 5, 'case_a': 1, 'case_b': 1, 'case_c': 1,
    'missing_fields': []}


def report_for(records: list[dict], layouts: dict[int, HeaderLayout] = LAYOUTS) -> dict:
    rows = rows_frame(records)
    return year_report(rows, reduce(rows, layouts, NODES), layouts)


def test_year_report_counts_cases_a_b_c_and_partitions():
    report = report_for(report_rows())
    assert report == {'2022': EXPECTED_2022, '2023': EXPECTED_2023}
    for counts in report.values():
        assert sum(counts['facility_years_by_reason'].values()) == counts['facility_years']
        assert sum(counts['rows_by_form_type'].values()) == counts['rows']
        assert set(counts['facility_years_by_reason']) == {'eligible', *EXCLUSIONS}


def test_year_report_missing_fields_are_the_layout_missing_fields():
    report = report_for(report_rows())
    assert report['2022']['missing_fields'] == list(LAYOUTS[2022].missing)
    assert report['2023']['missing_fields'] == list(LAYOUTS[2023].missing)


def test_year_report_holds_only_counts_and_no_name_or_dnb_number():
    report = report_for(report_rows())
    text = json.dumps(report)
    for secret in ('9000000', 'ACME', 'Acme', 'Zed', 'BETA', 'GAMMA', 'DELTA', 'Whoever'):
        assert secret not in text

    def leaves(value):
        if isinstance(value, dict):
            for item in value.values():
                yield from leaves(item)
        elif isinstance(value, list):
            yield from (leaf for item in value for leaf in leaves(item))
        else:
            yield value

    for leaf in leaves(report):
        assert type(leaf) in (int, str, type(None))


@pytest.mark.parametrize('unmapped, nulls', [
    (('parent_name',), ('case_a', 'case_b')),
    (('state',), ('in_territories',)),
    (('state', 'parent_name'), ('case_a', 'case_b', 'in_territories'))])
def test_year_report_counts_are_null_when_the_year_leaves_the_field_unmapped(unmapped, nulls):
    layouts = with_unmapped(2023, *unmapped)
    # The reader reads an unmapped field as ''.
    records = [{**row, **dict.fromkeys(unmapped, '')} if row['year'] == 2023 else row
               for row in report_rows()]
    report = report_for(records, layouts)
    assert report['2022'] == EXPECTED_2022
    expected = {**EXPECTED_2023, **dict.fromkeys(nulls),
                'missing_fields': list(layouts[2023].missing)}
    assert report['2023'] == expected


def test_year_report_in_territories_counts_each_territory_but_not_dc():
    states = ['AS', 'GU', 'MP', 'PR', 'VI', 'DC', 'TX', 'XX']
    records = [form(f'T{n}', state=state) for n, state in enumerate(states)]
    assert report_for(records)['2023']['in_territories'] == 5
    assert report_for([form('T1', state='DC'), form('T1', state='TX'),
                       form('T2', state='PR'), form('T2', state='TX')])['2023'][
                           'in_territories'] == 1


def test_year_report_counts_a_facility_year_once_however_many_territory_forms_it_has():
    records = [form('T1', state='PR'), form('T1', state='GU'), form('T1', state='PR')]
    assert report_for(records)['2023']['in_territories'] == 1


def test_year_report_counts_a_facility_year_once_however_many_distinct_values_it_has():
    # T1 has two secondary codes on one form, and two forms that differ in the foreign parent,
    # the parent and the D&B number. T2 has none of them.
    records = [
        form('T1', naics_2='325110', naics_3='325120', standardized_foreign_parent='ACME ABROAD',
             standardized_parent='ACME', parent_dnb='900000001'),
        form('T1', standardized_foreign_parent='ZED ABROAD', standardized_parent='BETA',
             parent_dnb='900000002'),
        form('T2'),
    ]
    counts = report_for(records)['2023']
    assert counts['facility_years'] == 2
    assert counts['with_secondary_codes'] == 1
    assert counts['with_foreign_parent'] == 1
    assert counts['with_parent'] == 1
    assert counts['with_usable_dnb'] == 1


def test_year_report_counts_only_rows_with_both_a_name_and_a_usable_dnb():
    records = [
        form('T1', standardized_parent='ACME', parent_dnb='900000001'),
        form('T2', standardized_parent='ACME', parent_dnb='NA'),
        form('T3', standardized_parent='ACME', parent_dnb=''),
        form('T4', standardized_parent='NA', parent_dnb='900000001'),
        form('T5', standardized_parent='', parent_dnb='900000002'),
        form('T6', standardized_parent='BETA', parent_dnb='900000002'),
    ]
    counts = report_for(records)['2023']
    assert counts['names_with_several_dnb'] == 0
    assert counts['dnb_with_several_names'] == 0


def test_year_report_counts_distinct_names_and_numbers_not_rows():
    pairs = ([('ACME', '900000001')] * 3 + [('ACME', '900000002')] * 2
             + [('BETA', '900000003')] * 4 + [('BETA', '900000004'), ('BETA', '900000005')]
             + [('CHI', '900000006'), ('PSI', '900000006'), ('OMEGA', '900000006')]
             + [('CHI', '900000007'), ('PSI', '900000007')] * 2)
    records = [form(f'T{n}', standardized_parent=name, parent_dnb=number)
               for n, (name, number) in enumerate(pairs)]
    counts = report_for(records)['2023']
    assert counts['names_with_several_dnb'] == 4
    assert counts['dnb_with_several_names'] == 2


def test_year_report_counts_each_year_on_its_own_and_ignores_other_years():
    records = [form('T1', 2022, standardized_parent='ACME', parent_dnb='900000001'),
               form('T1', 2023, standardized_parent='ACME', parent_dnb='900000002'),
               form('T2', 2024, standardized_parent='BETA', parent_dnb='900000002')]
    report = report_for(records)
    assert list(report) == ['2022', '2023', '2024']
    for counts in report.values():
        assert counts['rows'] == 1
        assert counts['facility_years'] == 1
        assert counts['names_with_several_dnb'] == 0
        assert counts['dnb_with_several_names'] == 0


def test_year_report_reads_each_years_own_registered_strings():
    layouts = with_values(2024, **ODD_SETS)
    report = report_for([
        form('T1', 2023, standardized_parent='NONE', parent_dnb='0'),
        form('T1', 2024, form_type='AA', federal='Y', standardized_parent='NONE', parent_dnb='0'),
        form('T2', 2024, form_type='RR', federal='N', standardized_parent='NA', parent_dnb='NA'),
    ], layouts)
    # In 2023 `NONE` and `0` are values. In 2024 they stand for no parent and no number.
    assert (report['2023']['with_parent'], report['2023']['with_usable_dnb']) == (1, 1)
    counts = report['2024']
    assert counts['rows_by_form_type'] == {'form_r': 1, 'form_a': 1}
    assert counts['facility_years_by_reason'] == {
        'eligible': 1, 'naics_missing': 0, 'naics_conflict': 0, 'naics_not_2022': 0,
        'parent_conflict': 0, 'federal': 1}
    assert (counts['with_parent'], counts['with_usable_dnb']) == (1, 1)


@pytest.mark.parametrize('parents, case_a, case_b', [
    # reported, standardized
    ([('NA', 'ACME')], 1, 0),
    ([('', 'ACME')], 1, 0),
    ([('Acme', 'ACME')], 0, 0),
    ([('Acme', 'NA')], 0, 1),
    ([('Acme', '')], 0, 1),
    ([('NA', 'NA')], 0, 0),
    ([('', '')], 0, 0),
    ([('Acme', 'ACME'), ('NA', 'NA')], 0, 0),
    ([('NA', 'ACME'), ('Acme', 'NA')], 0, 0)])
def test_year_report_cases_a_and_b(parents, case_a, case_b):
    records = [form('T1', parent_name=reported, standardized_parent=name)
               for reported, name in parents]
    counts = report_for(records)['2023']
    assert (counts['case_a'], counts['case_b']) == (case_a, case_b)


@pytest.mark.parametrize('numbers, parent, case_c', [
    (['900000001'], '', 1),
    (['900000001', '900000001'], '', 1),
    (['900000001', 'NA'], '', 1),
    (['900000001'], 'NA', 1),
    (['900000001'], 'ACME', 0),
    (['900000001', '900000002'], '', 0),
    (['NA'], '', 0),
    ([''], '', 0)])
def test_year_report_case_c(numbers, parent, case_c):
    records = [form('T1', parent_dnb=number, standardized_parent=parent) for number in numbers]
    counts = report_for(records)['2023']
    assert counts['case_c'] == case_c
    assert counts['with_usable_dnb'] == (1 if any(n not in ('NA', '') for n in numbers) else 0)


def test_year_report_for_a_year_without_a_layout_fails():
    layouts = {year: layout for year, layout in LAYOUTS.items() if year != 2024}
    rows = rows_frame([form('T1', 2022), form('T1', 2024)])
    frame = reduce(rows_frame([form('T1', 2022)]), layouts, NODES)
    with pytest.raises(ValueError, match='^no layout for year$'):
        year_report(rows, frame, layouts)
