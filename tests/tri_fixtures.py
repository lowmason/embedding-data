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
    if field not in tri_reader.READ_SCHEMA:
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


def subprocess_modules(name: str, *, prefix: str | None = 'embedding_data') -> set[str]:
    '''The names in `sys.modules` after a fresh `sys.executable` process imports `name`.

    Only the names that start with `prefix` are kept, unless `prefix` is None.
    '''
    import json
    import subprocess
    import sys

    code = ('import importlib, json, sys\n'
            f'importlib.import_module({name!r})\n'
            'print(json.dumps(sorted(sys.modules)))\n')
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
                            check=True)
    loaded = set(json.loads(result.stdout))
    return loaded if prefix is None else {module for module in loaded
                                          if module.startswith(prefix)}


def module_file(module: str) -> str:
    '''The repository-relative source file of a module of the `embedding_data` package.'''
    if module == 'embedding_data':
        return 'src/embedding_data/__init__.py'
    if not module.startswith('embedding_data.'):
        raise ValueError(f'{module} is not a module of embedding_data')
    return 'src/embedding_data/' + module.removeprefix('embedding_data.') + '.py'


V12_DATE = date(2025, 11, 5)
V12_RUNS = ('v12_first', 'v12_second')
# Made-up D&B numbers, nine digits each. None belongs to a real company.
_V12_NUMBERS = {
    'alder': '482910573', 'alder_b': '482910584', 'birch': '593021684', 'cedar': '604132795',
    'dogwood': '715243806', 'elm': '826354917', 'fir': '937465028', 'fern': '148576139',
    'holly': '259687240', 'iris': '360798351', 'juniper': '471809462',
}
V12_DNB = tuple(_V12_NUMBERS.values())


def v12_rows() -> dict[int, list[dict[str, str]]]:
    '''The synthetic rows of the V12 chain, by reporting year, with every required case.

    - Multi-form: T101 files a Form R and a Form A, both naming Alder, in 2022.
    - Same-year pair: Birch owns T103 (324110) and T104 (325211) in 2023.
    - D&B grouping differs: Alder's T102 reports another D&B number than T101, so Alder
      owns 325110 and 325120 in 2022 and 2023, but the D&B keys split them.
    - Primary-code conflict: T111's two forms give 325110 and 325120 in 2022.
    - Parent conflict: T109's two forms name Elm and Fir in 2023. Elm's T110 is eligible in
      the same industry, so Elm is a partial owner.
    - Mixed blank: Cedar's T105 has a Form R that names Cedar and a Form A that gives `NA`.
    - Self-owned: T112 gives `NA` as its parent in every year.
    - Federal: Iris's T113 is federal in 2023. Holly's pair in 325110 and 324110 gains Iris in
      the federal sensitivity.
    - Code outside NAICS 2022: Juniper's T120 gives 336111, a 2017 code.
    - Cross-year non-pair: Dogwood owns 562211 in 2022 and 562910 in 2024, never together.
    - RY2023 foreign parent: Birch's T103 names one in 2023.
    '''
    def owner(name: str, number: str, reported: str) -> dict[str, str]:
        return dict(standardized_parent=name, parent_name=reported,
                    parent_dnb=_V12_NUMBERS[number])

    alder = owner('Alder Holdings', 'alder', 'Alder Holdings LLC')
    alder_b = dict(alder, parent_dnb=_V12_NUMBERS['alder_b'])
    birch = owner('Birch Corp', 'birch', 'Birch Corporation')
    cedar = owner('Cedar Inc', 'cedar', 'Cedar Incorporated')
    dogwood = owner('Dogwood Ltd', 'dogwood', 'Dogwood Limited')
    elm = owner('Elm Group', 'elm', 'Elm Group Inc')
    fir = owner('Fir Group', 'fir', 'Fir Group Inc')
    fern = owner('Fern Partners', 'fern', 'Fern Partners LP')
    holly = owner('Holly Co', 'holly', 'Holly Company')
    iris = owner('Iris Works', 'iris', 'Iris Works Inc')
    juniper = owner('Juniper Brands', 'juniper', 'Juniper Brands Inc')
    alone = dict(standardized_parent='NA', parent_name='NA', parent_dnb='NA')
    return {
        2022: [
            tri_row(2022, 'T101', primary_naics='325110', state='TX', **alder),
            tri_row(2022, 'T101', primary_naics='325110', state='TX', form='A', **alder),
            tri_row(2022, 'T102', primary_naics='325120', state='TX', **alder_b),
            tri_row(2022, 'T107', primary_naics='562211', state='OH', **dogwood),
            tri_row(2022, 'T111', primary_naics='325110', state='LA', **fern),
            tri_row(2022, 'T111', primary_naics='325120', state='LA', **fern),
            tri_row(2022, 'T112', primary_naics='331110', state='OH', **alone),
        ],
        2023: [
            tri_row(2023, 'T101', primary_naics='325110', state='TX', **alder),
            tri_row(2023, 'T102', primary_naics='325120', state='TX', **alder_b),
            tri_row(2023, 'T103', primary_naics='324110', state='LA',
                    standardized_foreign_parent='Birch Holding SA', **birch),
            tri_row(2023, 'T104', primary_naics='325211', state='NJ', **birch),
            tri_row(2023, 'T109', primary_naics='325110', state='MI', **elm),
            tri_row(2023, 'T109', primary_naics='325110', state='MI', **fir),
            tri_row(2023, 'T110', primary_naics='325110', state='MI', **elm),
            tri_row(2023, 'T113', primary_naics='325110', state='TX', federal=True, **iris),
            tri_row(2023, 'T114', primary_naics='324110', state='LA', **iris),
            tri_row(2023, 'T116', primary_naics='325110', state='LA', **holly),
            tri_row(2023, 'T117', primary_naics='324110', state='LA', **holly),
            tri_row(2023, 'T120', primary_naics='336111', state='MI', **juniper),
            tri_row(2023, 'T112', primary_naics='331110', state='OH', **alone),
        ],
        2024: [
            tri_row(2024, 'T105', primary_naics='325199', state='TX', **cedar),
            tri_row(2024, 'T105', primary_naics='325199', state='TX', form='A', **alone),
            tri_row(2024, 'T106', primary_naics='331110', state='TX', **cedar),
            tri_row(2024, 'T108', primary_naics='562910', state='OH', **dogwood),
            tri_row(2024, 'T112', primary_naics='331110', state='OH', **alone),
        ],
    }


def run_tri_v12(tmp_path: Path, monkeypatch) -> dict:
    '''Synthetic raw TRI files to two verified, replay-equal bundles, with external access blocked.

    The guards go in first, so seeding, both builds, both verifications and the comparison
    run under them. The returned dict holds `data_dir`, the `first` and `second` bundle
    directories, their detached pins, both verification results and the comparison.
    '''
    import httpx
    from target_fixtures import forbid_external_access

    from embedding_data import tri_bundle

    def no_client(*args, **kwargs):
        raise AssertionError('the V12 fixture chain attempted external access')

    forbid_external_access(monkeypatch)
    monkeypatch.setattr(httpx.Client, '__init__', no_client)
    monkeypatch.setattr(httpx.AsyncClient, '__init__', no_client)
    data_dir = tmp_path / 'data'
    codes_run, codes_pin = seed_codes_bundle(data_dir, tmp_path / 'codes-originals')
    seed_tri_files(data_dir, tmp_path / 'originals', v12_rows(), V12_DATE)
    result = {'data_dir': data_dir}
    for name, run_id in zip(('first', 'second'), V12_RUNS, strict=True):
        published = tri_bundle.build(
            data_dir, run_id, codes_run=codes_run, codes_outputs_sha256=codes_pin,
            processed_as_of=V12_DATE)
        result[name] = Path(published['directory'])
        result[name + '_pin'] = published['outputs_sha256']
        result[name + '_verification'] = tri_bundle.verify_bundle(
            result[name], data_dir, expected_outputs_sha256=published['outputs_sha256'])
    result['comparison'] = tri_bundle.compare_runs(result['first'], result['second'])
    return result
