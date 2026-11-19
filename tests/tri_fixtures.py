'''Shared fixtures for the TRI parent-links tests.

`seed_codes_bundle` builds a real Stage 4 codes bundle. The other helpers write synthetic
TRI basic data files, with made-up values, under the production header layout.
'''

import csv
import io
from datetime import date
from functools import cache
from pathlib import Path

import ita_establishment_fixtures as establishment
import ita_fixtures
import polars as pl

from embedding_data import code_build, ita_summary, manifest, tri_layout, tri_raw, tri_reader

BYTE_ORDER_MARK = b'\xef\xbb\xbf'
FORM_SETS = {'R': 'form_r', 'A': 'form_a'}


def seed_codes_bundle(data_dir: Path, directory: Path) -> tuple[str, str]:
    '''Build a real Stage 4 bundle from the committed fixtures and return its run and pin.

    The raw ITA releases, the Stage 2 summary and the exact public Stage 4 originals are
    seeded first, because `code_build.build` reads all three. `directory` receives the
    original files before they are imported into `data_dir`.
    '''
    for year, rows in establishment.golden_releases().items():
        ita_fixtures.write_release(data_dir, year, ita_fixtures.year_file(year, rows))
    ita_summary.build_summary_table(data_dir)
    establishment.import_stage4_originals(data_dir, directory)
    bundle = code_build.build(data_dir, establishment.CODES_RUN)
    return establishment.CODES_RUN, manifest.sha256_file(bundle / 'outputs.json')


@cache
def production_layout(year: int) -> tri_layout.HeaderLayout:
    return tri_layout.load_layouts()[year]


def _cell(layout: tri_layout.HeaderLayout, field: str) -> str:
    '''The header cell that a field of `READ_SCHEMA` reads, in the layout of one year.'''
    if field == 'year' or field not in tri_reader.READ_SCHEMA:
        raise ValueError(f'{field} is not a field of a TRI row')
    if field.startswith('naics_'):
        position = int(field.removeprefix('naics_')) - 2
        cell = layout.other_naics[position] if position < len(layout.other_naics) else None
    else:
        cell = layout.columns[field]
    if cell is None:
        raise ValueError(f'{field} is not mapped in {layout.year}')
    return cell


def _registered(layout: tri_layout.HeaderLayout, name: str) -> str:
    '''The first sorted string that the layout registers under a value-set name.'''
    return sorted(layout.values[name])[0]


def tri_row(year: int, trifd: str, **fields: str | bool) -> dict[str, str]:
    '''A full row, keyed by every header cell of the production layout of `year`.

    A cell that no field maps to is `''`. `reporting_year` is `str(year)`, and the form is
    `R` and the federal flag false unless the keywords say otherwise. `form='R'` or `'A'`
    and `federal=True` or `False` stand for the first sorted registered value. The other
    keywords are the logical fields of `READ_SCHEMA`, except `year`. A field that the layout
    of `year` does not map raises `ValueError`.
    '''
    layout = production_layout(year)
    fields = dict(fields)
    if 'form' not in fields and 'form_type' not in fields:
        fields['form'] = 'R'
    fields.setdefault('federal', False)
    values = {'reporting_year': str(year), 'trifd': trifd}
    for name, value in fields.items():
        if name == 'form':
            name, value = 'form_type', _registered(layout, FORM_SETS[value])
        elif name == 'federal' and isinstance(value, bool):
            value = _registered(layout, 'federal_yes' if value else 'federal_no')
        values[name] = value
    row = dict.fromkeys(layout.header, '')
    for name, value in values.items():
        row[_cell(layout, name)] = value
    return row


def write_tri_csv(file: Path, year: int, rows: list[dict[str, str]], *, bom: bool = False,
                  newline: str = '\n', encoding: str = 'utf-8') -> None:
    '''Write the production header of `year` and the rows as one TRI CSV file.

    `bom` puts the UTF-8 byte order mark first. `newline` ends each record, and `encoding`
    encodes the text, so `cp1252` writes a Windows-1252 file.
    '''
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=production_layout(year).header,
                            lineterminator=newline)
    writer.writeheader()
    writer.writerows(rows)
    mark = BYTE_ORDER_MARK if bom else b''
    Path(file).write_bytes(mark + buffer.getvalue().encode(encoding))


def seed_tri_files(data_dir: Path, directory: Path, rows: dict[int, list[dict[str, str]]],
                   processed_as_of: date) -> dict[int, Path]:
    '''Write each year's file under `directory` and import it into the raw tree of `data_dir`.'''
    directory.mkdir(parents=True, exist_ok=True)
    imported = {}
    for year, year_rows in rows.items():
        original = directory / tri_raw.file_name(year)
        write_tri_csv(original, year, year_rows)
        imported[year] = tri_raw.import_file(
            data_dir, year, original, processed_as_of=processed_as_of)
    return imported


def rows_frame(records: list[dict]) -> pl.LazyFrame:
    '''The records as a lazy frame in `READ_SCHEMA`.

    Each record gives `year` and any fields to set. An unset string field is `''`.
    '''
    unknown = {name for record in records for name in record} - set(tri_reader.READ_SCHEMA)
    if unknown:
        raise ValueError(f'not fields of READ_SCHEMA: {sorted(unknown)}')
    columns = {
        name: [record['year'] if name == 'year' else record.get(name, '') for record in records]
        for name in tri_reader.READ_SCHEMA
    }
    return pl.DataFrame(columns, schema=tri_reader.READ_SCHEMA).lazy()
