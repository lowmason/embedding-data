'''The TRI header layout model: strict parsing, the JSON round trip and the loader.'''

import copy
import inspect
import json
from pathlib import Path

import pytest

from embedding_data import tri_layout
from embedding_data.tri_layout import (
    DIAGNOSTIC_FIELDS,
    FOREIGN_FIELDS,
    LAYOUT_VERSION,
    REQUIRED_FIELDS,
    VALUE_SETS,
    HeaderLayout,
    layouts_json,
    load_layouts,
    parse_layouts,
)

# Synthetic header rows and values: made up for the tests, never EPA's.
HEADER = ['YEAR', 'TRIFD', 'DCN', 'FORM', 'ST', 'FACILITY', 'FED', 'NAICS1', 'NAICS2', 'NAICS3',
          'NAICS4', 'NAICS5', 'NAICS6', 'PARENT', 'PARENT_DNB', 'STD_PARENT', 'FOREIGN',
          'FOREIGN_DNB', 'STD_FOREIGN']
OTHER = ['NAICS2', 'NAICS3', 'NAICS4', 'NAICS5', 'NAICS6']
COLUMN_ORDER = ['reporting_year', 'trifd', 'document_control_number', 'form_type', 'state',
                'federal', 'primary_naics', 'other_naics', 'parent_name', 'parent_dnb',
                'standardized_parent', 'foreign_parent_name', 'foreign_parent_dnb',
                'standardized_foreign_parent']
SCALAR = {
    'reporting_year': 'YEAR', 'trifd': 'TRIFD', 'document_control_number': 'DCN',
    'form_type': 'FORM', 'state': 'ST', 'federal': 'FED', 'primary_naics': 'NAICS1',
    'parent_name': 'PARENT', 'parent_dnb': 'PARENT_DNB', 'standardized_parent': 'STD_PARENT',
    'foreign_parent_name': 'FOREIGN', 'foreign_parent_dnb': 'FOREIGN_DNB',
    'standardized_foreign_parent': 'STD_FOREIGN',
}


def year_object(year):
    '''One valid year of the layout JSON. The value lists are deliberately unsorted.'''
    columns = dict(SCALAR)
    if year == 2022:
        columns.update({field: None for field in FOREIGN_FIELDS})
    columns['other_naics'] = list(OTHER)
    return {
        'header': list(HEADER),
        'columns': {field: columns[field] for field in COLUMN_ORDER},
        'values': {
            'form_r': ['R', 'R1'], 'form_a': ['A'], 'federal_yes': ['YES', 'Y'],
            'federal_no': ['NO'], 'no_parent': ['NA', '', 'N/A'], 'no_dnb': ['NA', ''],
        },
    }


def document():
    return {'version': LAYOUT_VERSION,
            'years': {str(year): year_object(year) for year in (2022, 2023, 2024)}}


def year_of(value, year='2022'):
    return value['years'][year]


def set_column(field, cell, year='2022'):
    def edit(value):
        year_of(value, year)['columns'][field] = cell
    return edit


def set_values(name, entries, year='2022'):
    def edit(value):
        year_of(value, year)['values'][name] = entries
    return edit


def drop_key(section, key, year='2022'):
    def edit(value):
        del year_of(value, year)[section][key]
    return edit


def rename_year(old, new):
    def edit(value):
        value['years'][new] = value['years'].pop(old)
    return edit


def add_header_cell(cell):
    def edit(value):
        year_of(value)['header'].append(cell)
    return edit


def with_other_naics(cells):
    def edit(value):
        year_of(value)['header'].extend(cell for cell in cells if cell not in HEADER)
        year_of(value)['columns']['other_naics'] = cells
    return edit


def test_layout_json_round_trip():
    layouts = parse_layouts(document())
    rendered = layouts_json(layouts)
    assert parse_layouts(rendered) == layouts
    assert parse_layouts(json.loads(json.dumps(rendered))) == layouts
    assert rendered['version'] == 'tri-headers-v1'
    assert list(rendered['years']) == ['2022', '2023', '2024']
    first = rendered['years']['2022']
    assert list(first) == ['header', 'columns', 'values']
    assert first['header'] == HEADER
    assert list(first['columns']) == COLUMN_ORDER
    assert first['columns']['other_naics'] == OTHER
    assert first['columns']['foreign_parent_dnb'] is None
    assert rendered['years']['2023']['columns']['foreign_parent_dnb'] == 'FOREIGN_DNB'
    assert list(first['values']) == list(VALUE_SETS)
    # Sets have no order, so the rendering sorts each list.
    assert first['values'] == {
        'form_r': ['R', 'R1'], 'form_a': ['A'], 'federal_yes': ['Y', 'YES'],
        'federal_no': ['NO'], 'no_parent': ['', 'N/A', 'NA'], 'no_dnb': ['', 'NA'],
    }


def test_layouts_json_renders_the_years_in_order_whatever_the_argument_order():
    layouts = parse_layouts(document())
    reversed_layouts = dict(reversed(list(layouts.items())))
    assert list(reversed_layouts) == [2024, 2023, 2022]
    assert list(layouts_json(reversed_layouts)['years']) == ['2022', '2023', '2024']


def test_parse_layouts_builds_typed_layouts():
    layouts = parse_layouts(document())
    assert sorted(layouts) == [2022, 2023, 2024]
    layout = layouts[2023]
    assert isinstance(layout, HeaderLayout)
    assert layout.year == 2023
    assert layout.header == tuple(HEADER)
    assert layout.columns == {**SCALAR}
    assert layout.other_naics == tuple(OTHER)
    assert layout.values['federal_yes'] == frozenset({'YES', 'Y'})
    assert layout.values['no_parent'] == frozenset({'', 'NA', 'N/A'})
    assert layouts[2022].columns['standardized_foreign_parent'] is None


def test_constants_name_the_contract_fields():
    assert REQUIRED_FIELDS == ('reporting_year', 'trifd', 'form_type', 'federal',
                               'primary_naics', 'parent_dnb', 'standardized_parent')
    assert DIAGNOSTIC_FIELDS == ('document_control_number', 'state', 'parent_name')
    assert FOREIGN_FIELDS == ('foreign_parent_name', 'foreign_parent_dnb',
                              'standardized_foreign_parent')
    assert VALUE_SETS == ('form_r', 'form_a', 'federal_yes', 'federal_no', 'no_parent',
                          'no_dnb')


REFUSALS = {
    'wrong_version': lambda value: value.update(version='tri-headers-v0'),
    'no_version': lambda value: value.pop('version'),
    'no_years': lambda value: value.pop('years'),
    'a_year_is_missing': lambda value: value['years'].pop('2023'),
    'a_year_is_extra': lambda value: value['years'].update(
        {'2025': copy.deepcopy(year_of(value, '2024'))}),
    'a_year_is_replaced': rename_year('2024', '2021'),
    'a_year_key_is_not_a_number': rename_year('2023', 'next'),
    'a_year_is_not_an_object': lambda value: value['years'].update({'2023': []}),
    'no_header': lambda value: year_of(value).pop('header'),
    'header_is_not_a_list': lambda value: year_of(value).update(header=5),
    'header_has_an_empty_cell': lambda value: year_of(value)['header'].__setitem__(5, ''),
    'header_has_a_blank_cell': lambda value: year_of(value)['header'].__setitem__(5, '  '),
    'header_has_a_non_string_cell': lambda value: year_of(value)['header'].__setitem__(5, 7),
    'header_repeats_a_cell': add_header_cell('FACILITY'),
    'a_mapped_column_is_not_a_header_cell': set_column('state', 'NO SUCH CELL'),
    'a_diagnostic_column_is_not_a_header_cell': set_column('parent_name', 'NO SUCH CELL'),
    'a_foreign_column_is_not_a_header_cell': set_column(
        'foreign_parent_name', 'NO SUCH CELL', '2023'),
    'a_mapped_column_is_not_a_string': set_column('state', 7),
    'a_mapped_column_differs_in_case_from_its_cell': set_column('trifd', 'trifd'),
    'a_mapped_column_has_padding': set_column('state', 'ST '),
    'other_naics_cell_is_not_a_header_cell': set_column('other_naics', ['NAICS2', 'NO SUCH']),
    'other_naics_is_not_a_list': set_column('other_naics', 5),
    'other_naics_has_six_cells': with_other_naics(OTHER + ['NAICS7']),
    'other_naics_repeats_a_cell': with_other_naics(['NAICS2', 'NAICS3', 'NAICS2']),
    'a_column_key_is_missing': drop_key('columns', 'state'),
    'other_naics_key_is_missing': drop_key('columns', 'other_naics'),
    'a_column_key_is_unknown': set_column('primary_naic', 'NAICS1'),
    'a_value_set_is_unknown': set_values('federal_maybe', ['MAYBE']),
    'columns_is_not_an_object': lambda value: year_of(value).update(columns=5),
    'values_is_not_an_object': lambda value: year_of(value).update(values=5),
    'a_value_set_is_not_a_list': set_values('form_r', 5),
    'a_value_is_not_a_string': set_values('form_r', ['R', 1]),
    'form_r_is_empty': set_values('form_r', []),
    'form_a_is_empty': set_values('form_a', []),
    'form_r_and_form_a_overlap': set_values('form_a', ['A', 'R1']),
    'federal_yes_is_empty': set_values('federal_yes', []),
    'federal_yes_and_federal_no_overlap': set_values('federal_no', ['NO', 'Y']),
    'no_parent_has_a_padded_entry': set_values('no_parent', ['', 'NA ']),
    'no_parent_has_a_blank_entry': set_values('no_parent', [' ', 'NA']),
    'no_dnb_has_a_padded_entry': set_values('no_dnb', ['', ' NA']),
    'no_dnb_has_a_tab_entry': set_values('no_dnb', ['NA\t']),
}


@pytest.mark.parametrize('edit', list(REFUSALS))
def test_parse_layouts_refuses(edit):
    value = document()
    REFUSALS[edit](value)
    with pytest.raises(ValueError):
        parse_layouts(value)


@pytest.mark.parametrize('year', ['2022', '2023', '2024'])
@pytest.mark.parametrize('field', REQUIRED_FIELDS)
def test_parse_layouts_refuses_an_unmapped_required_field(field, year):
    value = document()
    set_column(field, None, year)(value)
    with pytest.raises(ValueError):
        parse_layouts(value)


@pytest.mark.parametrize('field', FOREIGN_FIELDS)
def test_parse_layouts_refuses_a_foreign_field_in_2022(field):
    value = document()
    set_column(field, SCALAR[field])(value)
    with pytest.raises(ValueError):
        parse_layouts(value)


@pytest.mark.parametrize('year', ['2022', '2023', '2024'])
@pytest.mark.parametrize('name', VALUE_SETS)
def test_parse_layouts_refuses_a_missing_value_set(name, year):
    value = document()
    drop_key('values', name, year)(value)
    with pytest.raises(ValueError):
        parse_layouts(value)


@pytest.mark.parametrize('year', ['2022', '2023', '2024'])
def test_parse_layouts_checks_every_year(year):
    value = document()
    set_values('form_a', [], year)(value)
    with pytest.raises(ValueError):
        parse_layouts(value)


@pytest.mark.parametrize('value', [[], 'tri-headers-v1', None, {'version': LAYOUT_VERSION}])
def test_parse_layouts_refuses_a_document_that_is_not_an_object_with_years(value):
    with pytest.raises(ValueError):
        parse_layouts(value)


ACCEPTED = {
    'no_other_naics': set_column('other_naics', []),
    'five_other_naics': with_other_naics(OTHER),
    'one_other_naics': set_column('other_naics', ['NAICS6']),
    'empty_federal_no': set_values('federal_no', []),
    'empty_no_parent': set_values('no_parent', []),
    'empty_no_dnb': set_values('no_dnb', []),
    'blank_only_no_parent': set_values('no_parent', ['']),
    'no_diagnostic_fields': lambda value: [
        set_column(field, None)(value) for field in DIAGNOSTIC_FIELDS],
    'unmapped_foreign_fields_in_2023': lambda value: [
        set_column(field, None, '2023')(value) for field in FOREIGN_FIELDS],
    'one_foreign_field_in_2024': lambda value: [
        set_column(field, None, '2024')(value) for field in FOREIGN_FIELDS[1:]],
    'an_inner_space_in_a_value': set_values('no_parent', ['N A', 'NOT AVAILABLE']),
    'an_unmapped_header_cell': add_header_cell('EXTRA'),
    'header_cells_that_differ_in_case': add_header_cell('facility'),
    'header_cells_that_differ_in_padding': add_header_cell('FACILITY '),
}


@pytest.mark.parametrize('edit', list(ACCEPTED))
def test_parse_layouts_accepts_the_boundary_cases(edit):
    value = document()
    ACCEPTED[edit](value)
    layouts = parse_layouts(value)
    assert parse_layouts(layouts_json(layouts)) == layouts


def test_unmapped_diagnostic_fields_are_listed_as_missing():
    layouts = parse_layouts(document())
    assert layouts[2023].missing == ()
    assert layouts[2022].missing == FOREIGN_FIELDS
    # The other two diagnostic fields stay mapped, so each field is listed on its own.
    for field in DIAGNOSTIC_FIELDS:
        value = document()
        set_column(field, None, '2023')(value)
        assert parse_layouts(value)[2023].missing == (field,)


@pytest.mark.parametrize('field', FOREIGN_FIELDS)
def test_an_unmapped_foreign_field_is_listed_as_missing(field):
    value = document()
    set_column(field, None, '2024')(value)
    assert parse_layouts(value)[2024].missing == (field,)


@pytest.mark.parametrize('cells', [[], ['NAICS2'], OTHER[:4]])
def test_a_short_other_naics_is_listed_as_missing(cells):
    value = document()
    set_column('other_naics', cells, '2023')(value)
    assert parse_layouts(value)[2023].missing == ('other_naics',)


def test_missing_lists_diagnostic_then_foreign_then_other_naics():
    value = document()
    for field in (*DIAGNOSTIC_FIELDS, *FOREIGN_FIELDS):
        set_column(field, None, '2024')(value)
    set_column('other_naics', ['NAICS2'], '2024')(value)
    assert parse_layouts(value)[2024].missing == (
        'document_control_number', 'state', 'parent_name', 'foreign_parent_name',
        'foreign_parent_dnb', 'standardized_foreign_parent', 'other_naics')


def test_load_layouts_reads_a_file(tmp_path):
    file = tmp_path / 'layouts.json'
    file.write_text(json.dumps(document()))
    assert load_layouts(file) == parse_layouts(document())


def test_load_layouts_refuses_a_missing_file(tmp_path):
    with pytest.raises(ValueError, match='^production header layout is not recorded$'):
        load_layouts(tmp_path / 'absent.json')
    with pytest.raises(ValueError, match='^production header layout is not recorded$'):
        load_layouts(tmp_path)


def test_load_layouts_refuses_a_file_that_is_not_json(tmp_path):
    file = tmp_path / 'layouts.json'
    file.write_text('{"version": ')
    with pytest.raises(ValueError):
        load_layouts(file)


def test_load_layouts_refuses_an_invalid_layout(tmp_path):
    value = document()
    value['version'] = 'other'
    file = tmp_path / 'layouts.json'
    file.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        load_layouts(file)


def test_the_production_file_sits_beside_the_module():
    assert tri_layout.PRODUCTION_FILE == Path(tri_layout.__file__).with_name('tri_layouts.json')
    default = inspect.signature(load_layouts).parameters['file'].default
    assert default == tri_layout.PRODUCTION_FILE


def test_production_layout_covers_the_window():
    layouts = tri_layout.load_layouts()
    assert sorted(layouts) == [2022, 2023, 2024]
    assert all(layout.columns['standardized_parent'] for layout in layouts.values())
