'''Read the Census industry and occupation code lists and expand their NAICS expressions.'''

import re
from dataclasses import dataclass
from pathlib import Path

import fastexcel
import polars as pl

from embedding_data.acs_code_references import parse_membership_expression

INDUSTRY_SHEET = '2022 Census Ind Code List '
OCCUPATION_SHEET = '2018 Census Occ Code List'
CODE = re.compile(r'\d{4}')
SOC_TOKEN = re.compile(r'\d{2}-\d{4}|\d{2}-\d{3}X|\d{2}-\d{2}XX|\d{2}-\dXXX|none')
MARKER = re.compile(r'\b(?:Part of|Pts\.|pt\.)\s+')
FINEST_LEVEL = 'national_industry'
SECTOR_SPELLINGS = [('31,32,33', '31-33'), ('44,45', '44-45'), ('48,49', '48-49')]


@dataclass(frozen=True)
class ListRow:
    '''One Census list code with its stripped title and its NAICS expression or SOC token.'''

    code: str
    title: str
    expression: str | None
    locator: str


def _sheet_rows(file: Path, sheet: str) -> list[tuple]:
    workbook = fastexcel.read_excel(file.read_bytes())
    if sheet not in workbook.sheet_names:
        raise ValueError(f'Census list sheet absent: {sheet!r}')
    frame = workbook.load_sheet(sheet, header_row=None, dtypes='string').to_polars()
    return list(frame.iter_rows())


def _cell(row: tuple, index: int) -> str | None:
    value = row[index].strip() if index < len(row) and row[index] is not None else None
    return value or None


def _collapse(text: str) -> str:
    return ' '.join(text.split())


def read_industry_list(file: Path, kind: str = 'census_industry_2022') -> list[ListRow]:
    '''Return one row for each four-digit code, sorted, from the 2022 industry list.

    A code may sit on a section row with no title and on a detail row, or on two rows that
    differ only in padding. The rows of one code must agree on the expression and, once
    whitespace is collapsed, on the title.
    '''
    found: dict[str, list] = {}
    for number, row in enumerate(_sheet_rows(file, INDUSTRY_SHEET), 1):
        code = _cell(row, 3)
        if code is None or not CODE.fullmatch(code):
            continue
        title, expression = _cell(row, 1), _cell(row, 4)
        entry = found.setdefault(code, [expression, None, None])
        if entry[0] != expression:
            raise ValueError(f'industry code {code} has rows with different expressions')
        if title is None:
            continue
        if entry[1] is None:
            entry[1] = title
            entry[2] = f'{kind}:{INDUSTRY_SHEET}!B:E:row={number}'
        elif _collapse(entry[1]) != _collapse(title):
            raise ValueError(f'industry code {code} has rows with different titles')
    if not found:
        raise ValueError('the industry list has no data rows')
    if any(entry[1] is None for entry in found.values()):
        raise ValueError('an industry code has no title')
    return [ListRow(code, entry[1], entry[0], entry[2]) for code, entry in sorted(found.items())]


def read_occupation_list(file: Path, kind: str = 'census_occupation_2018') -> list[ListRow]:
    '''Return one row for each four-digit code, sorted, from the 2018 occupation list.

    The expression is the SOC token: a detailed code, a code with one to three trailing `X`
    positions, or `none`. A duplicate code or any other token shape fails.
    '''
    found: dict[str, ListRow] = {}
    for number, row in enumerate(_sheet_rows(file, OCCUPATION_SHEET), 1):
        code = _cell(row, 2)
        if code is None or not CODE.fullmatch(code):
            continue
        title, token = _cell(row, 1), _cell(row, 3)
        if code in found:
            raise ValueError(f'occupation code {code} appears twice')
        if title is None:
            raise ValueError(f'occupation code {code} has no title')
        if token is None or not SOC_TOKEN.fullmatch(token):
            raise ValueError(f'occupation code {code} has an unsupported SOC token')
        found[code] = ListRow(code, title, token,
                              f'{kind}:{OCCUPATION_SHEET}!B:D:row={number}')
    if not found:
        raise ValueError('the occupation list has no data rows')
    return [found[code] for code in sorted(found)]


def naics_candidates(expression: str, nodes: pl.DataFrame, paths: pl.DataFrame) -> list[str]:
    '''Expand a NAICS expression to its national industries, through the Stage 4 tables.'''
    return parse_membership_expression(expression, nodes, paths)


def membership_types(expression: str, nodes: pl.DataFrame) -> list[str]:
    '''Return every membership type of the expression's positive clause, sorted.

    The types are `part` (a marker is present), `several` (two or more codes), `whole` (one
    unmarked national industry) and `group` (a code above the finest level). An `exc.`
    clause adds no type. `several` counts the codes as written, so `Part of 44, 45` is
    `several`. The levels read `31, 32, 33`, `44, 45` and `48, 49` as the one sector each
    spells, as the candidate parser does, so those rows are also `group`.
    '''
    if not isinstance(expression, str):
        raise ValueError('unsupported membership expression')
    clauses = expression.strip().split(' exc. ')
    if len(clauses) not in (1, 2):
        raise ValueError('unsupported membership expression')
    positive = clauses[0]
    marked = MARKER.search(positive) is not None
    written = [token.strip() for token in re.split(r',|\s+and\s+', MARKER.sub('', positive))]
    listed = ','.join(written)
    for spelling, sector in SECTOR_SPELLINGS:
        listed = f',{listed},'.replace(f',{spelling},', f',{sector},')[1:-1]
    tokens = listed.split(',')
    levels = dict(zip(nodes['code'], nodes['level']))
    if not all(token in levels for token in tokens):
        raise ValueError('unsupported membership expression: unknown code')
    types = set()
    if marked:
        types.add('part')
    if len(written) >= 2:
        types.add('several')
    if len(written) == 1 and not marked and levels[tokens[0]] == FINEST_LEVEL:
        types.add('whole')
    if any(levels[token] != FINEST_LEVEL for token in tokens):
        types.add('group')
    return sorted(types)
