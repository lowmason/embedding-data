'''The Stage 14 registry model, the committed SAM.gov extract layout and the production
subaward header registry.

The refusal tests build one defective registry per case from a valid one and match the
exact message, so a refusal at the wrong check fails the test. The values below are
synthetic and made up. The committed extract layout is checked against the findings file's
Task 1 record, copied here as a literal. The production subaward registry is checked only
for its window years and its UEI columns, because its header cells are the measured ones.
'''

import copy
import dataclasses
import inspect
import json
import re
import warnings
from pathlib import Path

import pytest
from vendor_link_fixtures import no_live_sam  # noqa: F401

from embedding_data import vendor_link_layouts

REQUIRED = ('prime_uei', 'sub_uei', 'action_date', 'amount', 'subaward_type')
OPTIONAL = ('prime_parent_uei', 'sub_parent_uei', 'report_id', 'subaward_naics', 'prime_naics')
FIELDS = REQUIRED + OPTIONAL
YEARS = ('2024', '2025', '2026')
EXTRACT_REQUIRED = ('uei', 'registration_status', 'last_update_date', 'primary_naics',
                    'naics_code_string')
EXTRACT_FIELDS = EXTRACT_REQUIRED + ('evs_source',)
ALL_ASCII_WHITESPACE = ' \t\n\r\x0b\x0c'
PRODUCTION = {
    'version': 'sam-extract-layout-v1',
    'layout': 'SAM Master Extract Mapping v6.0 Public File V2 Layout',
    'member_pattern': r'SAM_PUBLIC_UTF-8_MONTHLY_V2_[0-9]{8}_[0-9a-f]{32}\.dat',
    'encoding': 'utf-8',
    'delimiter': '|',
    'field_count': 142,
    'bof_prefix': 'BOF PUBLIC V2 00000000 ',
    'eof_prefix': 'EOF PUBLIC V2 00000000 ',
    'record_end': '!end',
    'date_format': '%Y%m%d',
    'positions': {'uei': 1, 'registration_status': 6, 'last_update_date': 10,
                  'primary_naics': 33, 'naics_code_string': 35, 'evs_source': 122},
    'evs_dnb': ['D&B'],
    'restricted_positions': [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22],
}


def exactly(message):
    return pytest.raises(ValueError, match=rf'\A{re.escape(message)}\Z')


def subaward_year(tag, *, unmapped=(), date_format='%Y-%m-%d'):
    '''One valid year entry. An unmapped field has no header cell and a null column.'''
    cells = {field: f'{tag}_{field}' for field in FIELDS}
    return {
        'member_pattern': rf'{tag}_subawards_[0-9]+\.csv',
        'header': [f'{tag}_other',
                   *(cell for field, cell in cells.items() if field not in unmapped)],
        'date_format': date_format,
        'columns': {field: None if field in unmapped else cell
                    for field, cell in cells.items()},
    }


def subaward_value():
    '''A fresh valid registry: the years differ in every field and in the optional columns.'''
    return {
        'version': 'usaspending-subaward-headers-v1',
        'years': {
            '2024': subaward_year('a24'),
            '2025': subaward_year('b25', unmapped=('prime_parent_uei', 'report_id'),
                                  date_format='%m/%d/%Y'),
            '2026': subaward_year('c26', unmapped=('sub_parent_uei', 'subaward_naics',
                                                   'prime_naics'), date_format='%Y%m%d'),
        },
    }


def extract_value():
    '''A fresh valid layout, small enough to place every field apart from the others.'''
    return {
        'version': 'sam-extract-layout-v1',
        'layout': 'Synthetic layout v1',
        'member_pattern': r'SYNTH_[0-9]{8}\.dat',
        'encoding': 'utf-8',
        'delimiter': '|',
        'field_count': 30,
        'bof_prefix': 'BOF SYNTH ',
        'eof_prefix': 'EOF SYNTH ',
        'record_end': '!end',
        'date_format': '%Y%m%d',
        'positions': {'uei': 1, 'registration_status': 3, 'last_update_date': 5,
                      'primary_naics': 7, 'naics_code_string': 9, 'evs_source': 11},
        'evs_dnb': ['D&B', 'X&Y'],
        'restricted_positions': [2, 4, 6],
    }


def subaward_with(edit):
    value = subaward_value()
    edit(value)
    return value


def extract_with(edit):
    value = extract_value()
    edit(value)
    return value


def entry(change):
    '''An edit that changes one year's entry in place.'''
    return lambda years, year: change(years[year])


def column(field, cell):
    return entry(lambda item: item['columns'].update({field: cell}))


def same_cell(first, second):
    '''Map two fields to the one header cell that holds `action_date`.'''
    def change(item):
        cell = item['columns']['action_date']
        item['columns'].update({first: cell, second: cell})

    return entry(change)


def year_cases():
    '''Every per-year defect as (id, edit(years, year), message template, draft allows it).'''
    label = 'subaward year {year}'
    cases = [
        ('entry_list', lambda years, year: years.update({year: []}),
         label + ' is not an object', False),
        ('entry_missing_key', entry(lambda item: item.pop('header')),
         label + ' keys differ', False),
        ('entry_extra_key', entry(lambda item: item.update(note='x')),
         label + ' keys differ', False),
        ('member_pattern_not_text', entry(lambda item: item.update(member_pattern=5)),
         label + ' member pattern is not text', False),
        ('member_pattern_invalid', entry(lambda item: item.update(member_pattern='(')),
         label + ' member pattern does not compile', False),
        ('header_string', entry(lambda item: item.update(header='abc')),
         label + ' header is not a list of text', False),
        ('header_number_cell', entry(lambda item: item['header'].append(5)),
         label + ' header is not a list of text', False),
        ('header_empty_cell', entry(lambda item: item['header'].append('')),
         label + ' header has a blank cell', False),
        ('header_space_cell', entry(lambda item: item['header'].append('  ')),
         label + ' header has a blank cell', False),
        ('header_whitespace_cell',
         entry(lambda item: item['header'].append(ALL_ASCII_WHITESPACE)),
         label + ' header has a blank cell', False),
        ('header_repeats', entry(lambda item: item['header'].append(item['header'][0])),
         label + ' header has a repeated cell', False),
        ('date_format_not_text', entry(lambda item: item.update(date_format=5)),
         label + ' date format is not text', False),
        ('date_format_without_day', entry(lambda item: item.update(date_format='%Y-%m')),
         label + ' date format does not round-trip', False),
        ('date_format_without_month', entry(lambda item: item.update(date_format='%Y-%d')),
         label + ' date format does not round-trip', False),
        ('date_format_without_year', entry(lambda item: item.update(date_format='%m/%d')),
         label + ' date format does not round-trip', False),
        ('date_format_empty', entry(lambda item: item.update(date_format='')),
         label + ' date format does not round-trip', False),
        ('date_format_stray_percent', entry(lambda item: item.update(date_format='%')),
         label + ' date format does not round-trip', False),
        ('columns_list', entry(lambda item: item.update(columns=[])),
         label + ' columns is not an object', False),
        ('columns_missing_field', entry(lambda item: item['columns'].pop('report_id')),
         label + ' columns keys differ', False),
        ('columns_extra_field', entry(lambda item: item['columns'].update(extra='x')),
         label + ' columns keys differ', False),
    ]
    for field in FIELDS:
        template = label + f' column {field} is not a header cell'
        cases.append((f'cell_not_in_header_{field}', column(field, 'nowhere'), template,
                      False))
    template = label + ' column prime_uei is not a header cell'
    cases += [
        ('cell_other_case', entry(lambda item: item['columns'].update(
            prime_uei=item['columns']['prime_uei'].upper())), template, False),
        ('cell_padded', entry(lambda item: item['columns'].update(
            prime_uei=' ' + item['columns']['prime_uei'])), template, False),
        ('cell_number', column('prime_uei', 5), template, False),
    ]
    for first, second in (('prime_uei', 'sub_uei'), ('report_id', 'subaward_naics'),
                          ('prime_uei', 'prime_naics'), ('prime_parent_uei', 'sub_parent_uei')):
        cases.append((f'twice_{first}_{second}', same_cell(first, second),
                      label + ' maps a header cell twice', False))
    for field in REQUIRED:
        cases.append((f'required_{field}', column(field, None),
                      label + f' column {field} is not mapped', True))
    cases.append(('no_parent',
                  entry(lambda item: item['columns'].update(prime_parent_uei=None,
                                                            sub_parent_uei=None)),
                  label + ' maps no parent UEI column', True))
    return cases


ROOT_CASES = [
    ('none', None, 'subaward registry is not an object'),
    ('list', [], 'subaward registry is not an object'),
    ('version_other',
     subaward_with(lambda v: v.update(version='usaspending-subaward-headers-v2')),
     'subaward registry version differs'),
    ('version_padded',
     subaward_with(lambda v: v.update(version='usaspending-subaward-headers-v1 ')),
     'subaward registry version differs'),
    ('version_missing', subaward_with(lambda v: v.pop('version')),
     'subaward registry version differs'),
    ('keys_extra', subaward_with(lambda v: v.update(note='x')),
     'subaward registry keys differ'),
    ('keys_years_missing', subaward_with(lambda v: v.pop('years')),
     'subaward registry keys differ'),
    ('years_list', subaward_with(lambda v: v.update(years=[])),
     'subaward registry years differ from the window'),
    ('years_empty', subaward_with(lambda v: v.update(years={})),
     'subaward registry years differ from the window'),
    ('years_missing_2026', subaward_with(lambda v: v['years'].pop('2026')),
     'subaward registry years differ from the window'),
    ('years_extra_2027',
     subaward_with(lambda v: v['years'].update({'2027': v['years']['2026']})),
     'subaward registry years differ from the window'),
    ('years_2023_for_2024',
     subaward_with(lambda v: v['years'].update({'2023': v['years'].pop('2024')})),
     'subaward registry years differ from the window'),
    ('years_integer_keys',
     subaward_with(lambda v: v.update(years={int(k): e for k, e in v['years'].items()})),
     'subaward registry years differ from the window'),
]
YEAR_CASES = year_cases()


def year_params():
    params = []
    for year in YEARS:
        for case_id, edit, template, soft in YEAR_CASES:
            value = subaward_value()
            edit(value['years'], year)
            params.append(pytest.param(value, template.format(year=year), soft,
                                       id=f'{year}-{case_id}'))
    return params


YEAR_PARAMS = year_params()
SUBAWARD_REFUSALS = [pytest.param(value, message, id=case_id)
                     for case_id, value, message in ROOT_CASES]
SUBAWARD_REFUSALS += [pytest.param(param.values[0], param.values[1], id=param.id)
                      for param in YEAR_PARAMS]
DRAFT_REFUSALS = [pytest.param(param.values[0], param.values[1], id=param.id)
                  for param in YEAR_PARAMS if not param.values[2]]
DRAFT_ALLOWED = [pytest.param(param.values[0], id=param.id)
                 for param in YEAR_PARAMS if param.values[2]]


def extract_cases():
    '''Every extract-layout defect as (id, value, message).'''
    label = 'extract layout'
    cases = [
        ('none', None, f'{label} is not an object'),
        ('list', [], f'{label} is not an object'),
        ('string', 'x', f'{label} is not an object'),
        ('version_other', extract_with(lambda v: v.update(version='sam-extract-layout-v2')),
         f'{label} version differs'),
        ('version_padded', extract_with(lambda v: v.update(version='sam-extract-layout-v1 ')),
         f'{label} version differs'),
        ('version_missing', extract_with(lambda v: v.pop('version')),
         f'{label} version differs'),
        ('keys_extra', extract_with(lambda v: v.update(note='x')), f'{label} keys differ'),
        ('keys_record_end_missing', extract_with(lambda v: v.pop('record_end')),
         f'{label} keys differ'),
        ('name_number', extract_with(lambda v: v.update(layout=5)),
         f'{label} name is not text'),
        ('name_empty', extract_with(lambda v: v.update(layout='')), f'{label} name is blank'),
        ('name_spaces', extract_with(lambda v: v.update(layout='   ')),
         f'{label} name is blank'),
        ('name_whitespace', extract_with(lambda v: v.update(layout=ALL_ASCII_WHITESPACE)),
         f'{label} name is blank'),
        ('encoding_ascii', extract_with(lambda v: v.update(encoding='ascii')),
         f'{label} encoding differs'),
        ('encoding_upper_case', extract_with(lambda v: v.update(encoding='UTF-8')),
         f'{label} encoding differs'),
        ('encoding_padded', extract_with(lambda v: v.update(encoding='utf-8 ')),
         f'{label} encoding differs'),
        ('encoding_null', extract_with(lambda v: v.update(encoding=None)),
         f'{label} encoding differs'),
        ('delimiter_number', extract_with(lambda v: v.update(delimiter=5)),
         f'{label} delimiter is not text'),
        ('delimiter_empty', extract_with(lambda v: v.update(delimiter='')),
         f'{label} delimiter is not one character'),
        ('delimiter_two', extract_with(lambda v: v.update(delimiter='||')),
         f'{label} delimiter is not one character'),
        ('delimiter_padded', extract_with(lambda v: v.update(delimiter=' |')),
         f'{label} delimiter is not one character'),
        ('field_count_zero', extract_with(lambda v: v.update(field_count=0)),
         f'{label} field count is below 1'),
        ('field_count_negative', extract_with(lambda v: v.update(field_count=-1)),
         f'{label} field count is below 1'),
        ('field_count_text', extract_with(lambda v: v.update(field_count='30')),
         f'{label} field count is not an integer'),
        ('field_count_true', extract_with(lambda v: v.update(field_count=True)),
         f'{label} field count is not an integer'),
        ('field_count_float', extract_with(lambda v: v.update(field_count=30.0)),
         f'{label} field count is not an integer'),
        ('field_count_one', extract_with(lambda v: v.update(field_count=1)),
         f'{label} position registration_status is outside 1..field_count'),
        ('positions_list', extract_with(lambda v: v.update(positions=[])),
         f'{label} positions is not an object'),
        ('positions_missing_key', extract_with(lambda v: v['positions'].pop('evs_source')),
         f'{label} positions keys differ'),
        ('positions_extra_key', extract_with(lambda v: v['positions'].update(extra=2)),
         f'{label} positions keys differ'),
    ]
    for field in EXTRACT_FIELDS:
        cases += [
            (f'position_text_{field}',
             extract_with(lambda v, f=field: v['positions'].update({f: '1'})),
             f'{label} position {field} is not an integer'),
            (f'position_zero_{field}',
             extract_with(lambda v, f=field: v['positions'].update({f: 0})),
             f'{label} position {field} is outside 1..field_count'),
            (f'position_past_the_end_{field}',
             extract_with(lambda v, f=field: v['positions'].update({f: 31})),
             f'{label} position {field} is outside 1..field_count'),
            (f'restricted_{field}',
             extract_with(lambda v, f=field: v['restricted_positions'].append(
                 v['positions'][f])),
             f'{label} field {field} maps a restricted position'),
        ]
    cases += [
        ('position_true_uei', extract_with(lambda v: v['positions'].update(uei=True)),
         f'{label} position uei is not an integer'),
        ('position_float_uei', extract_with(lambda v: v['positions'].update(uei=1.0)),
         f'{label} position uei is not an integer'),
        ('position_negative_uei', extract_with(lambda v: v['positions'].update(uei=-1)),
         f'{label} position uei is outside 1..field_count'),
    ]
    for first, second in (('uei', 'registration_status'), ('primary_naics', 'evs_source'),
                          ('last_update_date', 'naics_code_string')):
        cases.append((
            f'twice_{first}_{second}',
            extract_with(lambda v, a=first, b=second: v['positions'].update(
                {a: 20, b: 20})),
            f'{label} maps a position twice'))
    for field in EXTRACT_REQUIRED:
        cases.append((f'required_{field}',
                      extract_with(lambda v, f=field: v['positions'].update({f: None})),
                      f'{label} field {field} is not mapped'))
    cases += [
        ('required_two_null', extract_with(lambda v: v['positions'].update(
            uei=None, registration_status=None)),
         f'{label} field uei is not mapped'),
        ('required_and_evs_source_null', extract_with(lambda v: v['positions'].update(
            uei=None, evs_source=None)),
         f'{label} field uei is not mapped'),
        ('restricted_number', extract_with(lambda v: v.update(restricted_positions=12)),
         f'{label} restricted positions are not a list of integers'),
        ('restricted_text', extract_with(lambda v: v.update(restricted_positions=['12'])),
         f'{label} restricted positions are not a list of integers'),
        ('restricted_true', extract_with(lambda v: v.update(restricted_positions=[True])),
         f'{label} restricted positions are not a list of integers'),
        ('evs_dnb_string', extract_with(lambda v: v.update(evs_dnb='D&B')),
         f'{label} D&B EVS values are not a list of text'),
        ('evs_dnb_number', extract_with(lambda v: v.update(evs_dnb=[1])),
         f'{label} D&B EVS values are not a list of text'),
        ('evs_dnb_without_source',
         extract_with(lambda v: v['positions'].update(evs_source=None)),
         f'{label} lists D&B EVS values without an EVS source'),
        ('bof_number', extract_with(lambda v: v.update(bof_prefix=5)),
         f'{label} BOF prefix is not text'),
        ('bof_empty', extract_with(lambda v: v.update(bof_prefix='')),
         f'{label} BOF prefix is blank'),
        ('bof_spaces', extract_with(lambda v: v.update(bof_prefix='   ')),
         f'{label} BOF prefix is blank'),
        ('bof_whitespace', extract_with(lambda v: v.update(bof_prefix=ALL_ASCII_WHITESPACE)),
         f'{label} BOF prefix is blank'),
        ('eof_number', extract_with(lambda v: v.update(eof_prefix=5)),
         f'{label} EOF prefix is not text'),
        ('eof_empty', extract_with(lambda v: v.update(eof_prefix='')),
         f'{label} EOF prefix is blank'),
        ('eof_spaces', extract_with(lambda v: v.update(eof_prefix='   ')),
         f'{label} EOF prefix is blank'),
        ('eof_whitespace', extract_with(lambda v: v.update(eof_prefix=ALL_ASCII_WHITESPACE)),
         f'{label} EOF prefix is blank'),
        ('prefixes_equal', extract_with(lambda v: v.update(eof_prefix=v['bof_prefix'])),
         f'{label} BOF and EOF prefixes are equal'),
        ('record_end_number', extract_with(lambda v: v.update(record_end=5)),
         f'{label} record end is not text'),
        ('record_end_empty', extract_with(lambda v: v.update(record_end='')),
         f'{label} record end is blank'),
        ('record_end_spaces', extract_with(lambda v: v.update(record_end='  ')),
         f'{label} record end is blank'),
        ('record_end_whitespace',
         extract_with(lambda v: v.update(record_end=ALL_ASCII_WHITESPACE)),
         f'{label} record end is blank'),
        ('member_pattern_number', extract_with(lambda v: v.update(member_pattern=5)),
         f'{label} member pattern is not text'),
        ('member_pattern_invalid', extract_with(lambda v: v.update(member_pattern='(')),
         f'{label} member pattern does not compile'),
        ('date_format_number', extract_with(lambda v: v.update(date_format=5)),
         f'{label} date format is not text'),
        ('date_format_without_day', extract_with(lambda v: v.update(date_format='%Y%m')),
         f'{label} date format does not round-trip'),
        ('date_format_without_month', extract_with(lambda v: v.update(date_format='%Y%d')),
         f'{label} date format does not round-trip'),
        ('date_format_without_year', extract_with(lambda v: v.update(date_format='%m%d')),
         f'{label} date format does not round-trip'),
        ('date_format_empty', extract_with(lambda v: v.update(date_format='')),
         f'{label} date format does not round-trip'),
        ('date_format_stray_percent', extract_with(lambda v: v.update(date_format='%')),
         f'{label} date format does not round-trip'),
    ]
    return cases


EXTRACT_REFUSALS = [pytest.param(value, message, id=case_id)
                    for case_id, value, message in extract_cases()]
EXTRACT_ACCEPTED = [
    pytest.param(lambda v: None, id='the_valid_layout'),
    pytest.param(lambda v: v['positions'].update(uei=1, evs_source=30), id='bounds'),
    pytest.param(lambda v: v.update(field_count=11), id='field_count_at_the_highest_position'),
    pytest.param(lambda v: v['positions'].update(evs_source=None) or v.update(evs_dnb=[]),
                 id='no_evs_source'),
    pytest.param(lambda v: v.update(evs_dnb=[]), id='evs_source_without_dnb_values'),
    pytest.param(lambda v: v.update(restricted_positions=[]), id='no_restricted_positions'),
    pytest.param(lambda v: v.update(record_end=None), id='no_record_end'),
    pytest.param(lambda v: v.update(delimiter='\t'), id='delimiter_tab'),
    pytest.param(lambda v: v.update(delimiter=' '), id='delimiter_space'),
    pytest.param(lambda v: v.update(bof_prefix='\xa0'), id='prefix_of_a_no_break_space'),
    pytest.param(lambda v: v.update(layout='\xa0'), id='name_of_a_no_break_space'),
    pytest.param(lambda v: v.update(record_end='\xa0'), id='record_end_of_a_no_break_space'),
    pytest.param(lambda v: v.update(eof_prefix=v['bof_prefix'] + 'x'),
                 id='one_prefix_extends_the_other'),
    pytest.param(lambda v: v.update(eof_prefix=v['bof_prefix'].lower()),
                 id='prefixes_differ_by_case'),
    pytest.param(lambda v: v.update(eof_prefix=v['bof_prefix'].rstrip()),
                 id='prefixes_differ_by_padding'),
]


def test_the_module_constants():
    assert vendor_link_layouts.SUBAWARD_VERSION == 'usaspending-subaward-headers-v1'
    assert vendor_link_layouts.EXTRACT_VERSION == 'sam-extract-layout-v1'
    assert vendor_link_layouts.SUBAWARD_REQUIRED == REQUIRED
    assert vendor_link_layouts.SUBAWARD_OPTIONAL == OPTIONAL
    assert vendor_link_layouts.EXTRACT_REQUIRED == EXTRACT_REQUIRED
    assert vendor_link_layouts.EXTRACT_OPTIONAL == ('evs_source',)


def test_the_registry_files_sit_beside_the_module():
    folder = Path(vendor_link_layouts.__file__).parent
    assert vendor_link_layouts.SUBAWARD_FILE == folder / 'usaspending_subaward_headers.json'
    assert vendor_link_layouts.EXTRACT_FILE == folder / 'sam_extract_layout.json'


def test_the_loaders_default_to_the_registry_files():
    subaward = inspect.signature(vendor_link_layouts.load_subaward_layouts)
    extract = inspect.signature(vendor_link_layouts.load_extract_layout)
    assert subaward.parameters['file'].default == vendor_link_layouts.SUBAWARD_FILE
    assert extract.parameters['file'].default == vendor_link_layouts.EXTRACT_FILE


def test_parse_subaward_layouts_builds_one_layout_per_window_year():
    layouts = vendor_link_layouts.parse_subaward_layouts(subaward_value())
    assert list(layouts) == [2024, 2025, 2026]
    assert layouts[2025] == vendor_link_layouts.SubawardLayout(
        year=2025, member_pattern=r'b25_subawards_[0-9]+\.csv',
        header=('b25_other', 'b25_prime_uei', 'b25_sub_uei', 'b25_action_date', 'b25_amount',
                'b25_subaward_type', 'b25_sub_parent_uei', 'b25_subaward_naics',
                'b25_prime_naics'),
        date_format='%m/%d/%Y',
        columns={'prime_uei': 'b25_prime_uei', 'sub_uei': 'b25_sub_uei',
                 'action_date': 'b25_action_date', 'amount': 'b25_amount',
                 'subaward_type': 'b25_subaward_type', 'prime_parent_uei': None,
                 'sub_parent_uei': 'b25_sub_parent_uei', 'report_id': None,
                 'subaward_naics': 'b25_subaward_naics', 'prime_naics': 'b25_prime_naics'})
    assert isinstance(layouts[2025].header, tuple)


def test_the_layouts_are_frozen():
    subaward = vendor_link_layouts.parse_subaward_layouts(subaward_value())[2024]
    extract = vendor_link_layouts.parse_extract_layout(extract_value())
    with pytest.raises(dataclasses.FrozenInstanceError):
        subaward.date_format = '%Y'
    with pytest.raises(dataclasses.FrozenInstanceError):
        extract.field_count = 1


def test_subaward_layout_json_round_trip():
    value = subaward_value()
    layouts = vendor_link_layouts.parse_subaward_layouts(value)
    written = vendor_link_layouts.subaward_layouts_json(layouts)
    assert written == value
    assert vendor_link_layouts.parse_subaward_layouts(written) == layouts
    assert json.loads(json.dumps(written)) == written


def test_extract_layout_json_round_trip():
    value = extract_value()
    layout = vendor_link_layouts.parse_extract_layout(value)
    written = vendor_link_layouts.extract_layout_json(layout)
    assert written == value
    assert vendor_link_layouts.parse_extract_layout(written) == layout
    assert json.loads(json.dumps(written)) == written
    assert layout.evs_dnb == frozenset({'D&B', 'X&Y'})
    assert layout.restricted_positions == frozenset({2, 4, 6})


def test_extract_layout_json_lists_the_sets_in_sorted_order():
    value = extract_value()
    value['restricted_positions'] = [20, 15, 2]
    value['evs_dnb'] = ['E', 'C', 'A', 'D', 'B']
    written = vendor_link_layouts.extract_layout_json(
        vendor_link_layouts.parse_extract_layout(value))
    assert written['restricted_positions'] == [2, 15, 20]
    assert written['evs_dnb'] == ['A', 'B', 'C', 'D', 'E']


@pytest.mark.parametrize('value, message', SUBAWARD_REFUSALS)
def test_parse_subaward_layouts_refuses(value, message):
    with exactly(message):
        vendor_link_layouts.parse_subaward_layouts(copy.deepcopy(value))


@pytest.mark.parametrize('value, message', DRAFT_REFUSALS)
def test_a_draft_registry_is_refused_by_every_other_check(value, message):
    with exactly(message):
        vendor_link_layouts.parse_subaward_layouts(copy.deepcopy(value), draft=True)


@pytest.mark.parametrize('value', DRAFT_ALLOWED)
def test_draft_allows_null_required_columns(value):
    layouts = vendor_link_layouts.parse_subaward_layouts(copy.deepcopy(value), draft=True)
    assert sorted(layouts) == [2024, 2025, 2026]


def test_a_draft_registry_can_leave_every_required_column_null():
    value = subaward_value()
    for item in value['years'].values():
        item['columns'].update(dict.fromkeys(REQUIRED), prime_parent_uei=None,
                               sub_parent_uei=None)
    layouts = vendor_link_layouts.parse_subaward_layouts(value, draft=True)
    assert all(layout.columns[field] is None for layout in layouts.values()
               for field in REQUIRED)
    assert layouts[2024].missing == ('prime_parent_uei', 'sub_parent_uei')
    written = vendor_link_layouts.subaward_layouts_json(layouts)
    assert written == value
    assert vendor_link_layouts.parse_subaward_layouts(written, draft=True) == layouts


def test_a_null_prime_parent_is_listed_as_missing():
    value = subaward_value()
    value['years']['2024']['columns']['prime_parent_uei'] = None
    layouts = vendor_link_layouts.parse_subaward_layouts(value)
    assert layouts[2024].missing == ('prime_parent_uei',)
    assert layouts[2024].columns['sub_parent_uei'] == 'a24_sub_parent_uei'


def test_missing_lists_only_unmapped_optional_fields_in_registry_order():
    layouts = vendor_link_layouts.parse_subaward_layouts(subaward_value())
    assert layouts[2024].missing == ()
    assert layouts[2025].missing == ('prime_parent_uei', 'report_id')
    assert layouts[2026].missing == ('sub_parent_uei', 'subaward_naics', 'prime_naics')


def test_either_parent_column_alone_is_enough():
    value = subaward_value()
    columns = value['years']['2024']['columns']
    columns['prime_parent_uei'] = None
    only_sub = vendor_link_layouts.parse_subaward_layouts(copy.deepcopy(value))
    columns.update(prime_parent_uei='a24_prime_parent_uei', sub_parent_uei=None)
    only_prime = vendor_link_layouts.parse_subaward_layouts(copy.deepcopy(value))
    assert only_sub[2024].missing == ('prime_parent_uei',)
    assert only_prime[2024].missing == ('sub_parent_uei',)


def test_header_cells_are_matched_as_exact_text():
    value = subaward_value()
    item = value['years']['2024']
    item['header'] += ['A24_PRIME_UEI', ' a24_prime_uei', '\xa0']
    layouts = vendor_link_layouts.parse_subaward_layouts(value)
    assert layouts[2024].header[-3:] == ('A24_PRIME_UEI', ' a24_prime_uei', '\xa0')
    item['columns']['prime_uei'] = 'A24_PRIME_UEI'
    mapped = vendor_link_layouts.parse_subaward_layouts(value)
    assert mapped[2024].columns['prime_uei'] == 'A24_PRIME_UEI'


def test_a_date_format_without_a_year_is_refused_without_a_warning():
    value = subaward_value()
    value['years']['2025']['date_format'] = '%m/%d'
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        with exactly('subaward year 2025 date format does not round-trip'):
            vendor_link_layouts.parse_subaward_layouts(value)
    value = extract_value()
    value['date_format'] = '%m%d'
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        with exactly('extract layout date format does not round-trip'):
            vendor_link_layouts.parse_extract_layout(value)


def test_parse_does_not_keep_the_registry_value_it_was_given():
    value = subaward_value()
    layouts = vendor_link_layouts.parse_subaward_layouts(value)
    value['years']['2024']['columns']['prime_uei'] = 'changed'
    value['years']['2024']['header'].append('changed')
    assert layouts[2024].columns['prime_uei'] == 'a24_prime_uei'
    assert 'changed' not in layouts[2024].header


def test_parse_extract_layout_does_not_keep_the_value_it_was_given():
    value = extract_value()
    layout = vendor_link_layouts.parse_extract_layout(value)
    value['positions']['uei'] = 2
    value['restricted_positions'].append(12)
    assert layout.positions['uei'] == 1
    assert 12 not in layout.restricted_positions


@pytest.mark.parametrize('value, message', EXTRACT_REFUSALS)
def test_parse_extract_layout_refuses(value, message):
    with exactly(message):
        vendor_link_layouts.parse_extract_layout(copy.deepcopy(value))


@pytest.mark.parametrize('edit', EXTRACT_ACCEPTED)
def test_parse_extract_layout_accepts_and_keeps_every_value(edit):
    value = extract_value()
    edit(value)
    layout = vendor_link_layouts.parse_extract_layout(copy.deepcopy(value))
    assert vendor_link_layouts.extract_layout_json(layout) == value


def test_an_extract_without_an_evs_source_has_no_position_for_it():
    value = extract_value()
    value['positions']['evs_source'] = None
    value['evs_dnb'] = []
    layout = vendor_link_layouts.parse_extract_layout(value)
    assert layout.positions['evs_source'] is None
    assert layout.evs_dnb == frozenset()


def test_the_extract_prefixes_keep_their_trailing_space():
    layout = vendor_link_layouts.parse_extract_layout(extract_value())
    assert layout.bof_prefix == 'BOF SYNTH '
    assert layout.eof_prefix == 'EOF SYNTH '


def test_load_subaward_layouts_refuses_a_missing_file(tmp_path):
    with exactly('production subaward header registry is not recorded'):
        vendor_link_layouts.load_subaward_layouts(tmp_path / 'absent.json')


def test_load_subaward_layouts_reads_the_given_file(tmp_path):
    file = tmp_path / 'headers.json'
    file.write_text(json.dumps(subaward_value()))
    assert (vendor_link_layouts.load_subaward_layouts(file)
            == vendor_link_layouts.parse_subaward_layouts(subaward_value()))


def test_load_subaward_layouts_is_not_a_draft_load(tmp_path):
    value = subaward_value()
    value['years']['2025']['columns']['amount'] = None
    file = tmp_path / 'headers.json'
    file.write_text(json.dumps(value))
    with exactly('subaward year 2025 column amount is not mapped'):
        vendor_link_layouts.load_subaward_layouts(file)


def test_load_extract_layout_reads_the_given_file(tmp_path):
    file = tmp_path / 'layout.json'
    file.write_text(json.dumps(extract_value()))
    layout = vendor_link_layouts.load_extract_layout(file)
    assert layout == vendor_link_layouts.parse_extract_layout(extract_value())
    assert layout.field_count == 30


def test_load_extract_layout_checks_the_file(tmp_path):
    value = extract_value()
    value['encoding'] = 'ascii'
    file = tmp_path / 'layout.json'
    file.write_text(json.dumps(value))
    with exactly('extract layout encoding differs'):
        vendor_link_layouts.load_extract_layout(file)


def test_production_extract_layout_keeps_clear_of_dnb_positions():
    layout = vendor_link_layouts.load_extract_layout()
    mapped = {p for p in layout.positions.values() if p is not None}
    assert layout.restricted_positions and not mapped & layout.restricted_positions


def test_production_extract_layout_holds_the_values_of_the_findings():
    layout = vendor_link_layouts.load_extract_layout()
    assert vendor_link_layouts.extract_layout_json(layout) == PRODUCTION
    assert layout.restricted_positions == frozenset(range(12, 23))
    assert layout.evs_dnb == frozenset({'D&B'})
    assert layout.positions == PRODUCTION['positions']


def test_production_extract_layout_text_is_the_canonical_json():
    layout = vendor_link_layouts.load_extract_layout()
    canonical = json.dumps(vendor_link_layouts.extract_layout_json(layout), indent=2,
                           sort_keys=True) + '\n'
    assert vendor_link_layouts.EXTRACT_FILE.read_text(encoding='utf-8') == canonical


def test_production_subaward_registry_covers_the_window():
    layouts = vendor_link_layouts.load_subaward_layouts()
    assert sorted(layouts) == [2024, 2025, 2026]
    assert all(layout.columns['prime_uei'] and layout.columns['sub_uei']
               for layout in layouts.values())


# The one member of the first real public monthly V2 UTF-8 extract ZIP, seen in 2026: the
# month's date, an underscore, 32 lower-case hex characters and `.dat`. The registry fits only
# this form on purpose, so a name of any other form fails closed. Each refused name differs
# from the real member in one place.
REAL_MEMBER = 'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261005_897fa9aa54ba4f0fa78f34a447e93956.dat'
HEAD, DATE, HEX = 'SAM_PUBLIC_UTF-8_MONTHLY_V2_', '20261005', '897fa9aa54ba4f0fa78f34a447e93956'
STEM = REAL_MEMBER.removesuffix('.dat')

MATCHED_MEMBERS = {
    'the_real_member': REAL_MEMBER,
    'another_date_and_every_hex_digit': f'{HEAD}20260105_{"0123456789abcdef" * 2}.dat',
}

REFUSED_MEMBERS = {
    'unsuffixed_utf8_form': f'{HEAD}{DATE}.dat',
    'ascii_form': f'SAM_PUBLIC_MONTHLY_V2_{DATE}_{HEX}.dat',
    'ascii_unsuffixed_form': 'SAM_PUBLIC_MONTHLY_V2_20200414.dat',
    'unsuffixed_upper_case_extension': f'{HEAD}{DATE}.DAT',
    'ascii_unsuffixed_upper_case_extension': 'SAM_PUBLIC_MONTHLY_V2_20200414.DAT',
    'upper_case_extension': f'{STEM}.DAT',
    'mixed_case_extension': f'{STEM}.Dat',
    'underscore_for_the_dot': f'{STEM}_dat',
    'zip_extension': f'{STEM}.ZIP',
    'no_extension': STEM,
    'hex_of_31_characters': f'{HEAD}{DATE}_{HEX[:-1]}.dat',
    'hex_of_33_characters': f'{STEM}0.dat',
    'empty_hex': f'{HEAD}{DATE}_.dat',
    'upper_case_hex': f'{HEAD}{DATE}_{HEX.upper()}.dat',
    'non_hex_letter': f'{HEAD}{DATE}_{HEX[:-1]}g.dat',
    'date_of_7_digits': f'{HEAD}{DATE[:-1]}_{HEX}.dat',
    'date_of_9_digits': f'{HEAD}{DATE}0_{HEX}.dat',
    'date_with_a_letter': f'{HEAD}{DATE[:-1]}a_{HEX}.dat',
    'no_underscore_before_hex': f'{HEAD}{DATE}{HEX}.dat',
    'daily_extract': f'SAM_PUBLIC_UTF-8_DAILY_V2_{DATE}_{HEX}.dat',
    'version_3': f'SAM_PUBLIC_UTF-8_MONTHLY_V3_{DATE}_{HEX}.dat',
    'doubled_encoding_tag': f'SAM_PUBLIC_UTF-8_UTF-8_MONTHLY_V2_{DATE}_{HEX}.dat',
    'lower_case_prefix': REAL_MEMBER.replace('SAM_PUBLIC', 'sam_public'),
    'nested_path': f'dir/{REAL_MEMBER}',
    'leading_character': f'x{REAL_MEMBER}',
    'trailing_character': f'{REAL_MEMBER}x',
    'trailing_extension': f'{REAL_MEMBER}.bak',
}


@pytest.mark.parametrize('name', MATCHED_MEMBERS.values(), ids=MATCHED_MEMBERS.keys())
def test_production_member_pattern_matches_the_member_names(name):
    layout = vendor_link_layouts.load_extract_layout()
    assert re.fullmatch(layout.member_pattern, name)


@pytest.mark.parametrize('name', REFUSED_MEMBERS.values(), ids=REFUSED_MEMBERS.keys())
def test_production_member_pattern_refuses_other_names(name):
    layout = vendor_link_layouts.load_extract_layout()
    assert not re.fullmatch(layout.member_pattern, name)
