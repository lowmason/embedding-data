import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import polars as pl
from code_fixtures import write_xlsx

from embedding_data import code_references
from embedding_data.classification_tables import naics_tables
from embedding_data.ita_index_references import (
    CROSS_REFERENCE,
    IndexReference,
)
from embedding_data.target_inputs import CANONICAL_SCHEMA

UPSTREAM = Path(__file__).parent / 'fixtures/acs_mapping/upstream'

STRUCTURE_KINDS = ('naics_2012', 'naics_2017', 'naics_2022')

# Official sheet names and headers, as the Census index files deliver them.
INDEX_LAYOUT = {
    2012: ('2012NAICS', ('NAICS12', 'INDEX ITEM DESCRIPTION')),
    2017: ('2017NAICS', ('NAICS17', 'INDEX ITEM DESCRIPTION')),
    2022: ('2022NAICS', ('NAICS22', 'INDEX ITEM DESCRIPTION')),
}

# Real six-digit leaves of each vintage, any nonempty entries, then two cross-references.
# The first leaf is valid in that vintage only. One entry text sits under two codes in each
# vintage, entries are not in sorted order, and one cross-reference entry has a trailing space.
INDEX_ROWS = {
    2012: [
        ('517110', 'Telephone carriers, wired'),
        ('111110', 'Soybean farming'),
        ('111120', 'Soybean farming'),
        (CROSS_REFERENCE, 'Laboratories (see specific type)'),
        (CROSS_REFERENCE, 'Wholesale -- see type of product '),
    ],
    2017: [
        ('517311', 'Telephone carriers, wired'),
        ('111110', 'Soybean farming'),
        ('111120', 'Soybean farming'),
        (CROSS_REFERENCE, 'Laboratories (see specific type)'),
        (CROSS_REFERENCE, 'Wholesale -- see type of product '),
    ],
    2022: [
        ('517111', 'Telephone carriers, wired'),
        ('111110', 'Soybean farming'),
        ('111120', 'Soybean farming'),
        (CROSS_REFERENCE, 'Laboratories (see specific type)'),
        (CROSS_REFERENCE, 'Wholesale -- see type of product '),
    ],
}


def import_stage4_originals(
    data_dir: Path, directory: Path, kinds: tuple[str, ...] | None = None
) -> None:
    '''Import the committed exact public Stage 4 originals, after authenticating each.'''
    records = json.loads((UPSTREAM / 'provenance.json').read_text())['originals']
    unknown = set(kinds or ()).difference(record['kind'] for record in records)
    if unknown:
        raise ValueError(f'unknown Stage 4 original kinds: {sorted(unknown)}')
    directory.mkdir(parents=True, exist_ok=True)
    with ZipFile(UPSTREAM / 'stage4-originals.zip') as archive:
        for record in records:
            body = archive.read(record['path'])
            assert len(body) == record['size']
            assert hashlib.sha256(body).hexdigest() == record['sha256']
            if kinds is None or record['kind'] in kinds:
                file = directory / Path(record['path']).name
                file.write_bytes(body)
                code_references.import_reference(data_dir, record['kind'], file)


def seed_structure_titles(data_dir: Path, directory: Path) -> None:
    '''Import the 2012, 2017 and 2022 structure originals that `read_titles` reads.'''
    import_stage4_originals(data_dir, directory, STRUCTURE_KINDS)


def write_index_workbook(
    file: Path, sheet: str, header: tuple[str, str], rows: list[tuple[str, str]]
) -> None:
    '''Write an index workbook whose cells keep their leading and trailing spaces.

    `write_xlsx` writes a plain inline string, and readers trim its edge whitespace. Other
    fixtures rely on that, so this helper marks every string as preserved after the write.
    '''
    write_xlsx(file, [list(header), *[list(row) for row in rows]], sheet=sheet)
    with ZipFile(file) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    sheet_part = 'xl/worksheets/sheet1.xml'
    parts[sheet_part] = parts[sheet_part].replace(b'<t>', b'<t xml:space="preserve">')
    with ZipFile(file, 'w') as archive:
        for name, body in parts.items():
            archive.writestr(name, body)


def fixture_index_registry(
    directory: Path, rows: dict[int, list[tuple[str, str]]] = INDEX_ROWS
) -> dict[str, IndexReference]:
    '''Write one index workbook per vintage and register it with its real size and hash.'''
    registry = {}
    for vintage, vintage_rows in rows.items():
        sheet, header = INDEX_LAYOUT[vintage]
        name = f'{vintage}_fixture_index.xlsx'
        file = directory / 'naics' / name
        file.parent.mkdir(parents=True, exist_ok=True)
        write_index_workbook(file, sheet, header, vintage_rows)
        kind = f'naics_index_{vintage}'
        registry[kind] = IndexReference(
            kind=kind,
            vintage=vintage,
            url=f'https://fixture.test/naics/{name}',
            relative=f'naics/{name}',
            sheet=sheet,
            header=header,
            sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
            size=file.stat().st_size,
            expected_rows=len(vintage_rows),
            expected_cross_references=sum(code == CROSS_REFERENCE for code, _ in vintage_rows),
        )
    return registry


NAICS_SECTOR_RANGES = ('31-33', '44-45', '48-49')
NAICS_LEVELS = ('sector', 'subsector', 'industry_group', 'industry', 'national_industry')
UNRESOLVED_STATUSES = (
    'invalid_native_code',
    'unknown_vintage_candidates',
    'unknown_vintage_unmapped',
)


def naics_ancestors(code: str) -> list[str]:
    '''The codes of a 2022 NAICS code and its ancestors, root first.

    A two-digit prefix inside a sector range names the range (`33` is `31-33`).
    '''
    if '-' in code:
        return [code]
    prefix = int(code[:2])
    sector = next(
        (r for r in NAICS_SECTOR_RANGES if int(r[:2]) <= prefix <= int(r[-2:])), code[:2]
    )
    return [sector, *(code[:width] for width in range(3, len(code) + 1))]


def naics_reference(codes: list[str]) -> tuple[pl.DataFrame, pl.DataFrame]:
    '''The 2022 `naics_nodes` and `code_paths` frames for the codes and all their ancestors.'''
    wanted = sorted({ancestor for code in codes for ancestor in naics_ancestors(code)})
    titles = pl.DataFrame(
        {
            'vintage': [2022] * len(wanted),
            'code': wanted,
            'title': [f'Fixture {code}' for code in wanted],
        },
        schema={'vintage': pl.Int64, 'code': pl.String, 'title': pl.String},
    )
    nodes, _, code_paths = naics_tables(titles, 2022)
    return nodes, code_paths


def _node_id(code: str) -> str:
    level = NAICS_LEVELS[len(naics_ancestors(code)) - 1]
    return f'naics:2022:{level}:{code}'


def _deepest_common(candidates: list[str]) -> str | None:
    common = None
    for group in zip(*(naics_ancestors(code) for code in candidates)):
        if len(set(group)) != 1:
            break
        common = group[0]
    if common is None:
        return None
    return _node_id(common)


def _mapping(
    code: str | None,
    year: int | None,
    status: str,
    matching: list[int],
    candidates: list[str],
) -> dict:
    scalar = candidates[0] if year is not None and len(candidates) == 1 else None
    return {
        'naics_code': code,
        'naics_year': year,
        'naics_mapping_status': status,
        'naics_matching_vintages': matching,
        'naics_2022_candidates': candidates,
        'naics_2022_code': scalar,
        'naics_2022_node_id': _node_id(scalar) if scalar else None,
        'naics_deepest_common_node_id': _deepest_common(candidates) if candidates else None,
        'flag_naics_crosswalked': bool(candidates) and any(v != 2022 for v in matching),
        'flag_naics_ambiguous': len(candidates) > 1,
        'flag_naics_unresolved': status in UNRESOLVED_STATUSES,
    }


def native(code: str) -> dict:
    '''A native 2022 code. It is assumed to be a leaf of the 2022 structure only.'''
    return _mapping(code, 2022, 'native_2022', [2022], [code])


def crosswalked(code: str, year: int | None, candidates: list[str]) -> dict:
    '''A code of an older vintage with its 2022 candidates, or of an unknown vintage.

    A known year is assumed to be the only vintage that lists the code. An unknown year is
    assumed to be listed by 2012 and 2017.
    '''
    if year == 2022 or not candidates:
        raise ValueError('a crosswalked code needs an older or unknown vintage and candidates')
    status = 'unknown_vintage_candidates' if year is None else 'concorded'
    matching = [2012, 2017] if year is None else [year]
    return _mapping(code, year, status, matching, sorted(set(candidates)))


def unresolved(code: str | None, year: int | None) -> dict:
    '''A code with no 2022 candidate: missing, invalid for its vintage, or unmapped.'''
    if code is None:
        status = 'missing_code'
    elif year is not None:
        status = 'invalid_native_code'
    else:
        status = 'unknown_vintage_unmapped'
    return _mapping(code, year, status, [], [])


CANONICAL_DEFAULTS = {
    'year_filing_for': 2023,
    'establishment_name': 'Plant',
    'company_name': 'Acme',
    'ein': '123456789',
    'street_address': '1 Main St',
    'city': 'Town',
    'state': 'MA',
    'zip_code': '02134',
    'naics_year_from_dictionary': False,
    'industry_description': 'Steel',
    'establishment_type': 1,
    'size': 2,
    'size_class': 2,
    'annual_average_employees': 100,
    'total_hours_worked': 200_000,
    'flag_employment': False,
    'flag_hours_per_employee': False,
    'flag_below_filing_size': False,
    'flag_naics_year_unknown': False,
    'source_file': 'osha/fixture.csv',
    **native('332312'),
    'filing_industry_status': 'determinate',
    'flag_outside_filing_industry': False,
    'flag_outside_filing_rule': False,
    'flag_filing_rule_label_bridged': False,
    'flag_filing_reference_ambiguous': False,
}


def canonical_frame(rows: list[dict]) -> pl.LazyFrame:
    '''Canonical records in the given order, each row overriding the defaults.

    Without an override, `id` is the position plus 1 and `establishment_id` is 100 plus the
    position. Mapping fields come from `native`, `crosswalked` and `unresolved` rows.
    '''
    records = []
    for position, row in enumerate(rows):
        unknown = sorted(set(row) - set(CANONICAL_SCHEMA))
        if unknown:
            raise ValueError(f'unknown canonical columns: {unknown}')
        records.append(
            {
                **CANONICAL_DEFAULTS,
                'id': position + 1,
                'establishment_id': 100 + position,
                **row,
            }
        )
    return pl.DataFrame(records, schema=CANONICAL_SCHEMA).lazy()
