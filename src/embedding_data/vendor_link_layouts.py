'''The Stage 14 registries: the subaward CSV headers and the SAM.gov extract layout.

Two committed JSON files record what the build may read. The subaward registry holds, for
each window year, the member-name pattern, the exact header row and the header cell of each
logical field. The extract layout holds the field count, the framing and the 1-based
position of each field the build reads, and the positions of the D&B Open Data fields that
no mapped field may use. This module parses, checks and writes both. It reads no raw file
and no credential. Every refusal is a `ValueError` with a fixed message.
'''

import json
import re
import warnings
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from embedding_data.usaspending_raw import WINDOW

SUBAWARD_VERSION = 'usaspending-subaward-headers-v1'
EXTRACT_VERSION = 'sam-extract-layout-v1'
SUBAWARD_FILE = Path(__file__).with_name('usaspending_subaward_headers.json')
EXTRACT_FILE = Path(__file__).with_name('sam_extract_layout.json')
SUBAWARD_REQUIRED = ('prime_uei', 'sub_uei', 'action_date', 'amount', 'subaward_type')
SUBAWARD_OPTIONAL = ('prime_parent_uei', 'sub_parent_uei', 'report_id', 'subaward_naics',
                     'prime_naics')
SUBAWARD_FIELDS = SUBAWARD_REQUIRED + SUBAWARD_OPTIONAL
PARENT_FIELDS = ('prime_parent_uei', 'sub_parent_uei')
EXTRACT_REQUIRED = ('uei', 'registration_status', 'last_update_date', 'primary_naics',
                    'naics_code_string')
EXTRACT_OPTIONAL = ('evs_source',)
EXTRACT_FIELDS = EXTRACT_REQUIRED + EXTRACT_OPTIONAL
EXTRACT_KEYS = ('version', 'layout', 'member_pattern', 'encoding', 'delimiter', 'field_count',
                'bof_prefix', 'eof_prefix', 'record_end', 'date_format', 'positions',
                'evs_dnb', 'restricted_positions')
ENCODING = 'utf-8'
WHITESPACE = ' \t\n\r\x0b\x0c'
PROBE_DATE = date(2024, 2, 29)


@dataclass(frozen=True)
class SubawardLayout:
    year: int
    member_pattern: str
    header: tuple[str, ...]
    date_format: str
    columns: dict[str, str | None]

    @property
    def missing(self) -> tuple[str, ...]:
        '''The optional fields that the registry leaves unmapped, in registry order.'''
        return tuple(field for field in SUBAWARD_OPTIONAL if self.columns[field] is None)


@dataclass(frozen=True)
class ExtractLayout:
    layout: str
    member_pattern: str
    encoding: str
    delimiter: str
    field_count: int
    bof_prefix: str
    eof_prefix: str
    record_end: str | None
    date_format: str
    positions: dict[str, int | None]
    evs_dnb: frozenset[str]
    restricted_positions: frozenset[int]


def _blank(text: str) -> bool:
    return not text.strip(WHITESPACE)


def _object(value, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f'{label} is not an object')
    return value


def _keys(value: dict, keys: tuple[str, ...], label: str) -> None:
    if set(value) != set(keys):
        raise ValueError(f'{label} keys differ')


def _text(value, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f'{label} is not text')
    return value


def _whole(value, label: str) -> int:
    if type(value) is not int:
        raise ValueError(f'{label} is not an integer')
    return value


def _check_pattern(pattern, label: str) -> None:
    _text(pattern, f'{label} member pattern')
    try:
        re.compile(pattern)
    except re.error as error:
        raise ValueError(f'{label} member pattern does not compile') from error


def _check_date_format(date_format, label: str) -> None:
    '''Refuse a format that does not carry a whole date through `strftime` and `strptime`.'''
    _text(date_format, f'{label} date format')
    try:
        with warnings.catch_warnings(action='ignore', category=DeprecationWarning):
            parsed = datetime.strptime(PROBE_DATE.strftime(date_format), date_format).date()
    except ValueError:
        parsed = None
    if parsed != PROBE_DATE:
        raise ValueError(f'{label} date format does not round-trip')


def _header(cells, label: str) -> tuple[str, ...]:
    if not isinstance(cells, list) or not all(isinstance(cell, str) for cell in cells):
        raise ValueError(f'{label} header is not a list of text')
    if any(_blank(cell) for cell in cells):
        raise ValueError(f'{label} header has a blank cell')
    if len(set(cells)) != len(cells):
        raise ValueError(f'{label} header has a repeated cell')
    return tuple(cells)


def _columns(columns, header: tuple[str, ...], label: str, draft: bool) -> dict:
    _object(columns, f'{label} columns')
    _keys(columns, SUBAWARD_FIELDS, f'{label} columns')
    for field in SUBAWARD_FIELDS:
        cell = columns[field]
        if cell is not None and (not isinstance(cell, str) or cell not in header):
            raise ValueError(f'{label} column {field} is not a header cell')
    mapped = [columns[field] for field in SUBAWARD_FIELDS if columns[field] is not None]
    if len(set(mapped)) != len(mapped):
        raise ValueError(f'{label} maps a header cell twice')
    if not draft:
        for field in SUBAWARD_REQUIRED:
            if columns[field] is None:
                raise ValueError(f'{label} column {field} is not mapped')
        if all(columns[field] is None for field in PARENT_FIELDS):
            raise ValueError(f'{label} maps no parent UEI column')
    return {field: columns[field] for field in SUBAWARD_FIELDS}


def _parse_year(year: int, item, draft: bool) -> SubawardLayout:
    label = f'subaward year {year}'
    _object(item, label)
    _keys(item, ('member_pattern', 'header', 'date_format', 'columns'), label)
    _check_pattern(item['member_pattern'], label)
    header = _header(item['header'], label)
    _check_date_format(item['date_format'], label)
    columns = _columns(item['columns'], header, label, draft)
    return SubawardLayout(year, item['member_pattern'], header, item['date_format'], columns)


def parse_subaward_layouts(value: dict, *, draft: bool = False) -> dict[int, SubawardLayout]:
    '''Check a subaward registry value and return its layout for each window year.

    A draft may leave required columns and both parent columns null. The preflight alone
    uses it. Every other check still applies.
    '''
    label = 'subaward registry'
    _object(value, label)
    if value.get('version') != SUBAWARD_VERSION:
        raise ValueError(f'{label} version differs')
    _keys(value, ('version', 'years'), label)
    years = value['years']
    if not isinstance(years, dict) or set(years) != {str(year) for year in WINDOW}:
        raise ValueError(f'{label} years differ from the window')
    return {year: _parse_year(year, years[str(year)], draft) for year in WINDOW}


def subaward_layouts_json(layouts: dict[int, SubawardLayout]) -> dict:
    '''The registry value of `layouts`, so that parsing it returns `layouts`.'''
    return {
        'version': SUBAWARD_VERSION,
        'years': {
            str(year): {'member_pattern': layout.member_pattern,
                        'header': list(layout.header),
                        'date_format': layout.date_format,
                        'columns': dict(layout.columns)}
            for year, layout in sorted(layouts.items())},
    }


def load_subaward_layouts(file: Path = SUBAWARD_FILE) -> dict[int, SubawardLayout]:
    try:
        text = file.read_text(encoding='utf-8')
    except FileNotFoundError as error:
        raise ValueError('production subaward header registry is not recorded') from error
    return parse_subaward_layouts(json.loads(text))


def _positions(positions, field_count: int, label: str) -> dict[str, int | None]:
    _object(positions, f'{label} positions')
    _keys(positions, EXTRACT_FIELDS, f'{label} positions')
    for field in EXTRACT_FIELDS:
        position = positions[field]
        if position is None:
            continue
        _whole(position, f'{label} position {field}')
        if not 1 <= position <= field_count:
            raise ValueError(f'{label} position {field} is outside 1..field_count')
    mapped = [positions[field] for field in EXTRACT_FIELDS if positions[field] is not None]
    if len(set(mapped)) != len(mapped):
        raise ValueError(f'{label} maps a position twice')
    for field in EXTRACT_REQUIRED:
        if positions[field] is None:
            raise ValueError(f'{label} field {field} is not mapped')
    return {field: positions[field] for field in EXTRACT_FIELDS}


def _restricted(value, positions: dict[str, int | None], label: str) -> frozenset[int]:
    if not isinstance(value, list) or any(type(item) is not int for item in value):
        raise ValueError(f'{label} restricted positions are not a list of integers')
    restricted = frozenset(value)
    for field in EXTRACT_FIELDS:
        if positions[field] in restricted:
            raise ValueError(f'{label} field {field} maps a restricted position')
    return restricted


def _evs_dnb(value, positions: dict[str, int | None], label: str) -> frozenset[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f'{label} D&B EVS values are not a list of text')
    if value and positions['evs_source'] is None:
        raise ValueError(f'{label} lists D&B EVS values without an EVS source')
    return frozenset(value)


def _prefixes(bof, eof, label: str) -> None:
    for name, prefix in (('BOF', bof), ('EOF', eof)):
        if _blank(_text(prefix, f'{label} {name} prefix')):
            raise ValueError(f'{label} {name} prefix is blank')
    if bof == eof:
        raise ValueError(f'{label} BOF and EOF prefixes are equal')


def parse_extract_layout(value: dict) -> ExtractLayout:
    '''Check an extract-layout value and return it as an `ExtractLayout`.'''
    label = 'extract layout'
    _object(value, label)
    if value.get('version') != EXTRACT_VERSION:
        raise ValueError(f'{label} version differs')
    _keys(value, EXTRACT_KEYS, label)
    if _blank(_text(value['layout'], f'{label} name')):
        raise ValueError(f'{label} name is blank')
    if value['encoding'] != ENCODING:
        raise ValueError(f'{label} encoding differs')
    if len(_text(value['delimiter'], f'{label} delimiter')) != 1:
        raise ValueError(f'{label} delimiter is not one character')
    field_count = _whole(value['field_count'], f'{label} field count')
    if field_count < 1:
        raise ValueError(f'{label} field count is below 1')
    positions = _positions(value['positions'], field_count, label)
    restricted = _restricted(value['restricted_positions'], positions, label)
    evs_dnb = _evs_dnb(value['evs_dnb'], positions, label)
    _prefixes(value['bof_prefix'], value['eof_prefix'], label)
    record_end = value['record_end']
    if record_end is not None and _blank(_text(record_end, f'{label} record end')):
        raise ValueError(f'{label} record end is blank')
    _check_pattern(value['member_pattern'], label)
    _check_date_format(value['date_format'], label)
    return ExtractLayout(
        layout=value['layout'], member_pattern=value['member_pattern'],
        encoding=value['encoding'], delimiter=value['delimiter'], field_count=field_count,
        bof_prefix=value['bof_prefix'], eof_prefix=value['eof_prefix'],
        record_end=record_end, date_format=value['date_format'], positions=positions,
        evs_dnb=evs_dnb, restricted_positions=restricted)


def extract_layout_json(layout: ExtractLayout) -> dict:
    '''The layout value of `layout`, with its two sets as sorted lists.'''
    return {
        'version': EXTRACT_VERSION,
        'layout': layout.layout,
        'member_pattern': layout.member_pattern,
        'encoding': layout.encoding,
        'delimiter': layout.delimiter,
        'field_count': layout.field_count,
        'bof_prefix': layout.bof_prefix,
        'eof_prefix': layout.eof_prefix,
        'record_end': layout.record_end,
        'date_format': layout.date_format,
        'positions': dict(layout.positions),
        'evs_dnb': sorted(layout.evs_dnb),
        'restricted_positions': sorted(layout.restricted_positions),
    }


def load_extract_layout(file: Path = EXTRACT_FILE) -> ExtractLayout:
    return parse_extract_layout(json.loads(file.read_text(encoding='utf-8')))
