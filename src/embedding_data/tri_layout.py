'''The header layout of the EPA TRI basic data files, one record for each window year.

A layout names the exact header row of a year's file and maps each logical field to one
header cell. It also lists the delivered strings that stand for a form type, a federal
flag, "no parent" and "no D&B number". The committed file `tri_layouts.json` holds the
production layout, which the preflight measures and the build reads. `parse_layouts`
checks a layout strictly. Every failure raises `ValueError` with a fixed message.
'''

import json
from dataclasses import dataclass
from pathlib import Path

from embedding_data.tri_raw import WINDOW

LAYOUT_VERSION = 'tri-headers-v1'
PRODUCTION_FILE = Path(__file__).with_name('tri_layouts.json')
# The build needs each of these.
REQUIRED_FIELDS = ('reporting_year', 'trifd', 'form_type', 'federal', 'primary_naics',
                   'parent_dnb', 'standardized_parent')
DIAGNOSTIC_FIELDS = ('document_control_number', 'state', 'parent_name')
# Null for 2022, nullable for 2023 and 2024.
FOREIGN_FIELDS = ('foreign_parent_name', 'foreign_parent_dnb', 'standardized_foreign_parent')
NO_FOREIGN_YEARS = (2022,)
VALUE_SETS = ('form_r', 'form_a', 'federal_yes', 'federal_no', 'no_parent', 'no_dnb')
OTHER_NAICS = 'other_naics'
OTHER_NAICS_MAX = 5
COLUMN_ORDER = ('reporting_year', 'trifd', 'document_control_number', 'form_type', 'state',
                'federal', 'primary_naics', OTHER_NAICS, 'parent_name', 'parent_dnb',
                'standardized_parent', *FOREIGN_FIELDS)
SCALAR_FIELDS = tuple(field for field in COLUMN_ORDER if field != OTHER_NAICS)


@dataclass(frozen=True)
class HeaderLayout:
    year: int
    header: tuple[str, ...]
    columns: dict[str, str | None]
    other_naics: tuple[str, ...]
    values: dict[str, frozenset[str]]

    @property
    def missing(self) -> tuple[str, ...]:
        '''The unmapped diagnostic and foreign fields, then `other_naics` when it is short.'''
        unmapped = tuple(field for field in DIAGNOSTIC_FIELDS + FOREIGN_FIELDS
                         if self.columns[field] is None)
        short = (OTHER_NAICS,) if len(self.other_naics) < OTHER_NAICS_MAX else ()
        return unmapped + short


def _object(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f'{label}: not an object')
    return value


def _strings(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f'{label}: not a list of strings')
    return value


def _header(value: object, label: str) -> tuple[str, ...]:
    cells = _strings(value, f'{label} header')
    if any(not cell.strip() for cell in cells) or len(set(cells)) != len(cells):
        raise ValueError(f'{label}: header cells must be nonblank and unique')
    return tuple(cells)


def _columns(entry: dict, header: tuple[str, ...], label: str) -> tuple[dict, tuple]:
    raw = _object(entry.get('columns'), f'{label} columns')
    if set(raw) != set(COLUMN_ORDER):
        raise ValueError(f'{label}: columns must name exactly the logical fields')
    columns = {}
    for field in SCALAR_FIELDS:
        cell = raw[field]
        if cell is not None and cell not in header:
            raise ValueError(f'{label}: {field} is not a header cell')
        columns[field] = cell
    for field in REQUIRED_FIELDS:
        if columns[field] is None:
            raise ValueError(f'{label}: required field {field} is not mapped')
    other = _strings(raw[OTHER_NAICS], f'{label} {OTHER_NAICS}')
    if len(other) > OTHER_NAICS_MAX or len(set(other)) != len(other):
        raise ValueError(f'{label}: {OTHER_NAICS} holds up to five distinct cells')
    if not set(other) <= set(header):
        raise ValueError(f'{label}: {OTHER_NAICS} names a cell that is not in the header')
    return columns, tuple(other)


def _values(entry: dict, label: str) -> dict[str, frozenset[str]]:
    raw = _object(entry.get('values'), f'{label} values')
    if set(raw) != set(VALUE_SETS):
        raise ValueError(f'{label}: values must name exactly the value sets')
    values = {name: frozenset(_strings(raw[name], f'{label} {name}')) for name in VALUE_SETS}
    if not values['form_r'] or not values['form_a'] or values['form_r'] & values['form_a']:
        raise ValueError(f'{label}: form_r and form_a must be nonempty and disjoint')
    if not values['federal_yes'] or values['federal_yes'] & values['federal_no']:
        raise ValueError(f'{label}: federal_yes must be nonempty and disjoint from federal_no')
    for name in ('no_parent', 'no_dnb'):
        if any(entry != entry.strip() for entry in values[name]):
            raise ValueError(f'{label}: {name} entries must equal their own strip')
    return values


def _year(year: int, value: object) -> HeaderLayout:
    label = str(year)
    entry = _object(value, label)
    header = _header(entry.get('header'), label)
    columns, other_naics = _columns(entry, header, label)
    if year in NO_FOREIGN_YEARS and any(columns[field] is not None for field in FOREIGN_FIELDS):
        raise ValueError(f'{label}: foreign fields must be null')
    return HeaderLayout(year, header, columns, other_naics, _values(entry, label))


def parse_layouts(value: dict) -> dict[int, HeaderLayout]:
    '''The checked layout of each window year. Any failed check raises `ValueError`.'''
    document = _object(value, 'layout')
    if document.get('version') != LAYOUT_VERSION:
        raise ValueError('layout version differs')
    years = _object(document.get('years'), 'layout years')
    if set(years) != {str(year) for year in WINDOW}:
        raise ValueError('layout years differ from the window')
    return {year: _year(year, years[str(year)]) for year in WINDOW}


def layouts_json(layouts: dict[int, HeaderLayout]) -> dict:
    '''The JSON object of layouts, with sorted value lists, so that parsing it returns them.'''
    years = {}
    for year in sorted(layouts):
        layout = layouts[year]
        columns = {
            field: list(layout.other_naics) if field == OTHER_NAICS else layout.columns[field]
            for field in COLUMN_ORDER
        }
        years[str(year)] = {
            'header': list(layout.header),
            'columns': columns,
            'values': {name: sorted(layout.values[name]) for name in VALUE_SETS},
        }
    return {'version': LAYOUT_VERSION, 'years': years}


def load_layouts(file: Path = PRODUCTION_FILE) -> dict[int, HeaderLayout]:
    '''Read and check the committed production layout.'''
    if not file.is_file():
        raise ValueError('production header layout is not recorded')
    return parse_layouts(json.loads(file.read_text()))
