import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from code_fixtures import write_xlsx

from embedding_data import code_references
from embedding_data.ita_index_references import (
    CROSS_REFERENCE,
    IndexReference,
)

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
