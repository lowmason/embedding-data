'''The TRI preflight script: the header listing and the E7/E8 measures, on synthetic files.

Every CSV here is made up, with an invented numbered header and made-up D&B numbers. The
header cells only resemble what EPA may deliver, because nobody has read the real files yet.
'''

import copy
import csv
import importlib.util
import io
import itertools
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest
from tri_fixtures import seed_codes_bundle

from embedding_data import manifest, tri_codes, tri_layout, tri_raw

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'preflight_tri.py'
PROCESSED = date(2025, 11, 5)
WINDOW = (2022, 2023, 2024)
BOM = b'\xef\xbb\xbf'
NINE_DIGITS = re.compile(r'[0-9]{9}')

CELLS = {
    'year': '1. YEAR', 'trifd': '2. TRIFD', 'dcn': '3. DOCUMENT CONTROL NUMBER',
    'form': '4. FORM TYPE', 'state': '5. ST', 'facility': '6. FACILITY NAME',
    'federal': '7. FEDERAL FACILITY', 'primary': '8. PRIMARY NAICS', 'naics2': '9. NAICS 2',
    'naics3': '10. NAICS 3', 'naics4': '11. NAICS 4', 'naics5': '12. NAICS 5',
    'naics6': '13. NAICS 6', 'parent': '14. PARENT CO NAME', 'dnb': '15. PARENT CO DB NUM',
    'standardized': '16. STANDARDIZED PARENT COMPANY',
}
FOREIGN_CELLS = {
    'foreign': '17. FOREIGN PARENT CO NAME', 'foreign_dnb': '18. FOREIGN PARENT CO DB NUM',
    'foreign_standardized': '19. STANDARDIZED FOREIGN PARENT COMPANY',
}
ALL_CELLS = {**CELLS, **FOREIGN_CELLS}
OTHER_CELLS = [CELLS[name] for name in ('naics2', 'naics3', 'naics4', 'naics5', 'naics6')]
FIELD_CELLS = {
    'reporting_year': CELLS['year'], 'trifd': CELLS['trifd'],
    'document_control_number': CELLS['dcn'], 'form_type': CELLS['form'],
    'state': CELLS['state'], 'federal': CELLS['federal'], 'primary_naics': CELLS['primary'],
    'parent_name': CELLS['parent'], 'parent_dnb': CELLS['dnb'],
    'standardized_parent': CELLS['standardized'],
}
FOREIGN_FIELD_CELLS = {
    'foreign_parent_name': FOREIGN_CELLS['foreign'],
    'foreign_parent_dnb': FOREIGN_CELLS['foreign_dnb'],
    'standardized_foreign_parent': FOREIGN_CELLS['foreign_standardized'],
}
VALUES = {'form_r': ['R'], 'form_a': ['A'], 'federal_yes': ['YES'], 'federal_no': ['NO'],
          'no_parent': ['', 'NA'], 'no_dnb': ['', 'NA']}
VALID = ('111110', '111120', '111130')
NOT_2022 = ('123456', '234567', '999999')
DCNS = itertools.count(1)


def header(year):
    return list(CELLS.values()) + (list(FOREIGN_CELLS.values()) if year >= 2023 else [])


HEADER_2022 = header(2022)


def record(year, trifd, form='R', **fields):
    '''One CSV record as {header cell: value}. A field that is not given reads as blank.'''
    values = {'year': str(year), 'trifd': trifd, 'form': form, 'state': 'OH', 'federal': 'NO',
              'primary': VALID[0], 'dcn': f'DCN{next(DCNS):07d}',
              'facility': f'Plant {trifd}', **fields}
    return {ALL_CELLS[name]: value for name, value in values.items()}


def fy(year, trifd, primaries=VALID[:1], **fields):
    '''One facility-year: a form row for each primary code in the list.'''
    return [record(year, trifd, primary=primary, **fields) for primary in primaries]


def csv_bytes(year, records, *, bom=False, terminator='\r\n'):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=header(year), restval='', lineterminator=terminator)
    writer.writeheader()
    writer.writerows(records)
    content = stream.getvalue().encode('utf-8')
    return BOM + content if bom else content


def calm(year, *, blank_standardized=False):
    '''Two valid facility-years that name a parent, so that no stop or ask holds.'''
    names = ('', '') if blank_standardized else ('ALPHA INC', 'BETA INC')
    return (fy(year, f'T{year}01', parent='ALPHA', standardized=names[0], dnb='500000001')
            + fy(year, f'T{year}02', parent='BETA', standardized=names[1], dnb='500000002'))


def known_2022():
    '''3 facility-years, 5 forms. One primary conflict, one code outside NAICS 2022.'''
    return [
        record(2022, 'T22001', 'R', parent='ACME CORP', dnb='123456789',
               standardized='ACME HOLDINGS', naics2=VALID[1], state='OH'),
        record(2022, 'T22001', 'A', parent='ACME CORP', dnb='123456789',
               standardized='ACME HOLDINGS', state='OH'),
        record(2022, 'T22002', 'R', parent='NA', dnb='NA', standardized='BETA GROUP',
               naics3=VALID[2], state='PA', federal='YES'),
        record(2022, 'T22002', 'R', primary=VALID[1], parent='NA', dnb='NA',
               standardized='BETA GROUP', state='PA', federal='YES'),
        record(2022, 'T22003', 'A', primary=NOT_2022[0], parent='GAMMA LLC', dnb='987654321',
               naics2=VALID[1], state='OH'),
    ]


def known_2023():
    '''10 facility-years: 4 valid, 1 missing, 2 in conflict and 3 outside NAICS 2022.'''
    rows = []
    rows += fy(2023, 'T23V01', parent='DELTA INC', standardized='DELTA INC', dnb='111111111')
    rows += fy(2023, 'T23V02', parent='NA', standardized='EPSILON CO')
    rows += fy(2023, 'T23V03', parent='ZETA LP', dnb='700000001')
    rows += fy(2023, 'T23V04', parent='OMEGA', dnb='666666666')
    rows += fy(2023, 'T23M01', ('',), standardized='ETA CO', dnb='NA')
    rows += fy(2023, 'T23C01', VALID[:2], parent='THETA', standardized='THETA INC')
    rows += fy(2023, 'T23C02', VALID[1:], parent='IOTA', dnb='333333333')
    rows += fy(2023, 'T23N01', NOT_2022[:1], parent='KAPPA', dnb='444444444')
    rows += fy(2023, 'T23N02', NOT_2022[1:2], parent='LAMBDA', standardized='LAMBDA')
    rows += fy(2023, 'T23N03', NOT_2022[2:], dnb='555555555')
    return rows


def known_2024():
    '''6 valid facility-years. Two standardized names have two D&B numbers, one D&B number
    has two standardized names. The first facility name holds a Windows-1252 byte pair.'''
    rows = []
    rows += fy(2024, 'T24A01', facility='CAFE CAFE', parent='MU', standardized='MU CORP',
               dnb='800000001')
    rows += fy(2024, 'T24A02', parent='MU', standardized='MU CORP', dnb='800000002')
    rows += fy(2024, 'T24A03', parent='XI', standardized='XI CORP', dnb='800000003')
    rows += fy(2024, 'T24A04', parent='XI', standardized='XI CORP', dnb='800000004')
    rows += fy(2024, 'T24A05', parent='NU', standardized='NU A', dnb='900000001')
    rows += fy(2024, 'T24A06', parent='NU', standardized='NU B', dnb='900000001')
    return rows


@dataclass
class Env:
    data_dir: Path
    scratch: Path
    run: str | None = None
    pin: str | None = None


@pytest.fixture(scope='module')
def codes(tmp_path_factory):
    '''One real Stage 4 bundle for the module: its directory, run, pin and node IDs.'''
    root = tmp_path_factory.mktemp('tri-preflight-codes')
    run, pin = seed_codes_bundle(root / 'data', root / 'originals')
    nodes = tri_codes.select_nodes(root / 'data', run, codes_outputs_sha256=pin).node_ids
    for code in VALID:
        assert tri_codes.NODE_PREFIX + code in nodes
    for code in NOT_2022:
        assert tri_codes.NODE_PREFIX + code not in nodes
    return root / 'data' / 'derived' / 'codes' / run, run, pin


@pytest.fixture
def home(tmp_path):
    '''A data root with no codes bundle, for the commands that need none.'''
    return Env(tmp_path / 'data', tmp_path / 'scratch')


@pytest.fixture
def env(tmp_path, codes):
    bundle, run, pin = codes
    shutil.copytree(bundle, tmp_path / 'data' / 'derived' / 'codes' / run)
    return Env(tmp_path / 'data', tmp_path / 'scratch', run, pin)


@pytest.fixture(scope='module')
def script():
    assert SCRIPT.is_file(), 'preflight script is missing'
    spec = importlib.util.spec_from_file_location('preflight_tri', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def import_years(env, contents, processed=PROCESSED):
    env.scratch.mkdir(parents=True, exist_ok=True)
    for year, content in contents.items():
        original = env.scratch / f'original-{year}.csv'
        original.write_bytes(content)
        tri_raw.import_file(env.data_dir, year, original, processed_as_of=processed)


def stage(env, rows_by_year, *, bom=(), terminators=()):
    '''Import one synthetic file for each year in rows_by_year.'''
    import_years(env, {
        year: csv_bytes(year, rows, bom=year in bom,
                        terminator='\n' if year in terminators else '\r\n')
        for year, rows in rows_by_year.items()
    })


def calm_window(**replaced):
    rows = {year: calm(year) for year in WINDOW}
    rows.update({int(year[1:]): value for year, value in replaced.items()})
    return rows


def draft_document(unmapped=None, values=None):
    '''A draft layout over the invented headers. `unmapped` maps a year to fields set null.'''
    years = {}
    for year in WINDOW:
        columns = dict(FIELD_CELLS)
        columns.update({field: None for field in FOREIGN_FIELD_CELLS})
        if year >= 2023:
            columns.update(FOREIGN_FIELD_CELLS)
        columns['other_naics'] = list(OTHER_CELLS)
        columns.update({field: None for field in (unmapped or {}).get(year, ())})
        years[str(year)] = {'header': header(year), 'columns': columns,
                            'values': copy.deepcopy(values or VALUES)}
    return {'version': 'tri-headers-v1', 'years': years}


class Report(dict):
    '''A parsed report that keeps the one line the script printed.'''

    text = ''


def invoke(script, capsys, env, command, *argv, expect=0, processed=PROCESSED):
    status = script.main([command, '--data-dir', str(env.data_dir),
                          '--processed-as-of', processed.isoformat(), *map(str, argv)])
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert len(lines) == 1 and captured.err == '', captured
    report = Report(json.loads(lines[0]))
    report.text = lines[0]
    assert lines[0] == json.dumps(json.loads(lines[0]), sort_keys=True)
    assert status == expect, lines[0]
    return report


def run_headers(script, capsys, env, **options):
    return invoke(script, capsys, env, 'headers', **options)


def measure_arguments(env, layout, codes_run=None, pin=None):
    return ['--layout', layout, '--codes-run', codes_run or env.run,
            '--codes-outputs-sha256', pin or env.pin]


def write_layout(env, document, name='layout.json'):
    env.scratch.mkdir(parents=True, exist_ok=True)
    file = env.scratch / name
    file.write_text(json.dumps(document))
    return file


def run_measure(script, capsys, env, draft=None, *, layout=None, codes_run=None, pin=None,
                **options):
    layout = layout or write_layout(env, draft or draft_document())
    return invoke(script, capsys, env, 'measure', *measure_arguments(
        env, layout, codes_run, pin), **options)


# headers


def staged_headers(home):
    '''Three files: a quoted newline and a blank line, a BOM, and bad bytes in one line.'''
    first = [record(2022, 'T1', facility='Plant\nOne'), record(2022, 'T2'), record(2022, 'T3')]
    second = [record(2023, 'T1', facility='CAFÉ'), record(2023, 'T2')]
    third = [record(2024, f'T{n}', facility='CAFE CAFE' if n == 2 else f'Plant {n}')
             for n in range(1, 5)]
    import_years(home, {
        2022: csv_bytes(2022, first) + b'\r\n',
        2023: csv_bytes(2023, second, bom=True),
        2024: csv_bytes(2024, third).replace(b'CAFE', b'CAF\xe9'),
    })


def test_headers_prints_exact_rows_bom_and_utf8_counts(script, capsys, home):
    staged_headers(home)
    report = run_headers(script, capsys, home)
    assert report['2022']['header'] == HEADER_2022
    assert report['2023']['bom'] is True
    assert report['2024']['invalid_utf8_lines'] == 1
    assert sorted(report) == ['2022', '2023', '2024']
    assert [report[year]['bom'] for year in ('2022', '2024')] == [False, False]
    assert [report[year]['invalid_utf8_lines'] for year in ('2022', '2023')] == [0, 0]
    # The BOM is not part of the first header cell.
    assert report['2023']['header'] == header(2023)
    assert report['2024']['header'] == header(2024)


def test_headers_prints_the_path_hash_and_record_count(script, capsys, home):
    staged_headers(home)
    report = run_headers(script, capsys, home)
    raw = home.data_dir / 'raw'
    for year, records in (('2022', 3), ('2023', 2), ('2024', 4)):
        file = raw / f'epa_tri/basic/{year}/2025-11-05/tri_basic_{year}_US.csv'
        assert report[year]['path'] == file.relative_to(home.data_dir).as_posix()
        assert report[year]['sha256'] == manifest.sha256_file(file)
        assert report[year]['records'] == records
    assert str(home.data_dir) not in report.text


def test_headers_prints_hint_lists_of_header_cells(script, capsys, home):
    staged_headers(home)
    report = run_headers(script, capsys, home)
    assert report['2022']['hints'] == {
        'reporting_year': ['1. YEAR'], 'trifd': ['2. TRIFD'],
        'document_control_number': ['3. DOCUMENT CONTROL NUMBER'],
        'form_type': ['4. FORM TYPE'], 'state': ['5. ST'],
        'federal': ['7. FEDERAL FACILITY'], 'primary_naics': ['8. PRIMARY NAICS'],
        'other_naics': OTHER_CELLS, 'parent_name': ['14. PARENT CO NAME'],
        'parent_dnb': ['15. PARENT CO DB NUM'],
        'standardized_parent': ['16. STANDARDIZED PARENT COMPANY'],
        'foreign_parent_name': [], 'foreign_parent_dnb': [],
        'standardized_foreign_parent': [],
    }
    foreign = report['2023']['hints']
    assert foreign['foreign_parent_name'] == ['17. FOREIGN PARENT CO NAME']
    assert foreign['foreign_parent_dnb'] == ['18. FOREIGN PARENT CO DB NUM']
    assert foreign['standardized_foreign_parent'] == [
        '19. STANDARDIZED FOREIGN PARENT COMPANY']
    # A foreign cell is never a hint for the U.S. parent.
    assert foreign['parent_name'] == ['14. PARENT CO NAME']
    assert foreign['standardized_parent'] == ['16. STANDARDIZED PARENT COMPANY']


@pytest.mark.parametrize('cell, normalized', [
    ('1. YEAR', 'YEAR'),
    ('16.PARENT_CO_DB_NUM', 'PARENT CO DB NUM'),
    ('  23.   Federal  Facility ', 'FEDERAL FACILITY'),
    ('federal facility', 'FEDERAL FACILITY'),
    ('Parent_Co_Name', 'PARENT CO NAME'),
    ('9. NAICS 2', 'NAICS 2'),
    ('NAICS 2. EXTRA', 'NAICS 2. EXTRA'),
    ('2022 YEAR', '2022 YEAR'),
    ('12. 3. X', '3. X'),
    ('PRIMARY NAICS', 'PRIMARY NAICS'),
    ('. YEAR', '. YEAR'),
    ('1 YEAR', '1 YEAR'),
    ('1.YEAR', 'YEAR'),
])
def test_normalize_reads_a_header_cell_for_the_hint_match(script, cell, normalized):
    assert script.normalize(cell) == normalized


def test_headers_hints_match_the_normalized_cell_exactly(script, capsys, home):
    odd = ['16.parent_co_db_num', '  4.   Form  Type ', 'NAICS 2. EXTRA', '9. NAICS 7',
           '25. STREET', '26. ST ABBREVIATION', 'YEAR OF REPORT', '2. TRIFD 2']
    first = {cell: '' for cell in odd}
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=odd, lineterminator='\r\n')
    writer.writeheader()
    writer.writerow(first)
    content = stream.getvalue().encode()
    import_years(home, {year: content for year in WINDOW})
    hints = run_headers(script, capsys, home)['2022']['hints']
    assert hints['parent_dnb'] == ['16.parent_co_db_num']
    assert hints['form_type'] == ['  4.   Form  Type ']
    assert hints['other_naics'] == []
    assert hints['state'] == []
    assert hints['reporting_year'] == []
    assert hints['trifd'] == []


def test_headers_normalizes_a_hint_phrase_like_a_cell(script, capsys, home, monkeypatch):
    monkeypatch.setitem(script.HINTS, 'state', ('Province_Code', ' 9. Region  Name'))
    cells = ['1. PROVINCE CODE', 'region name', 'PROVINCE_CODE_2']
    stream = io.StringIO()
    csv.writer(stream, lineterminator='\r\n').writerows([cells, ['a', 'b', 'c']])
    content = stream.getvalue().encode()
    import_years(home, {year: content for year in WINDOW})
    hints = run_headers(script, capsys, home)['2022']['hints']
    assert hints['state'] == ['1. PROVINCE CODE', 'region name']


def test_headers_exits_2_with_no_file_under_the_snapshot_date(script, capsys, home):
    staged_headers(home)
    report = run_headers(script, capsys, home, expect=2, processed=date(2025, 11, 6))
    assert report == {'ok': False, 'reason': 'raw files cannot be selected'}


def test_headers_refuses_an_unrecorded_file(script, capsys, home):
    staged_headers(home)
    other = date(2025, 12, 1)
    for year in WINDOW:
        directory = tri_raw.snapshot_dir(home.data_dir, year, other)
        directory.mkdir(parents=True)
        (directory / tri_raw.file_name(year)).write_bytes(b'YEAR\n')
    report = run_headers(script, capsys, home, expect=2, processed=other)
    assert report == {'ok': False, 'reason': 'raw files cannot be selected'}


def test_headers_refuses_a_file_that_changed_after_it_was_recorded(script, capsys, home):
    staged_headers(home)
    with tri_raw.raw_path(home.data_dir, 2023, PROCESSED).open('ab') as stream:
        stream.write(b'extra\r\n')
    report = run_headers(script, capsys, home, expect=2)
    assert report == {'ok': False, 'reason': 'raw files cannot be selected'}


def test_headers_refuses_a_file_that_cannot_be_decoded(script, capsys, home):
    import_years(home, {year: csv_bytes(year, [record(year, 'T1')]) for year in WINDOW[:2]})
    bad = csv_bytes(2024, [record(2024, 'T1', facility='CAFE')]).replace(b'CAFE', b'CAF\x81')
    import_years(home, {2024: bad})
    report = run_headers(script, capsys, home, expect=2)
    assert report == {'ok': False, 'reason': 'a line cannot be decoded'}


def test_headers_refuses_a_file_without_a_header_row(script, capsys, home):
    import_years(home, {year: csv_bytes(year, [record(year, 'T1')]) for year in WINDOW[:2]})
    import_years(home, {2024: b'\r\n'})
    report = run_headers(script, capsys, home, expect=2)
    assert report == {'ok': False, 'reason': 'file has no header row'}


def test_headers_refuses_a_field_beyond_the_csv_limit(script, capsys, home):
    import_years(home, {year: csv_bytes(year, [record(year, 'T1')]) for year in WINDOW[:2]})
    big = csv_bytes(2024, [record(2024, 'T1', facility='X' * 200_000)])
    import_years(home, {2024: big})
    report = run_headers(script, capsys, home, expect=2)
    assert report == {'ok': False, 'reason': 'file is not valid CSV'}


def test_headers_counts_an_invalid_byte_in_the_header_line_and_decodes_it(script, capsys, home):
    cells = ['1. YEAR', '2. TRIFD', '3. CAFE']
    content = ('\r\n'.join([','.join(cells), '2022,T1,x', '']).encode()).replace(
        b'CAFE', b'CAF\xe9')
    import_years(home, {year: content for year in WINDOW})
    report = run_headers(script, capsys, home)
    assert report['2022']['invalid_utf8_lines'] == 1
    assert report['2022']['header'] == ['1. YEAR', '2. TRIFD', '3. CAF\u00e9']
    assert report['2022']['records'] == 1


# measure


def test_measure_counts_a_small_known_window(script, capsys, env):
    # 2022: 3 facilities, 5 forms (R and A), one primary conflict, one code outside 2022.
    stage(env, {2022: known_2022(), 2023: known_2023(), 2024: known_2024()}, bom=(2023,),
          terminators=(2024,))
    report = run_measure(script, capsys, env)
    first = report['years']['2022']
    assert first['rows'] == 5
    assert first['facility_years'] == 3
    assert first['naics_valid'] == 1
    assert first['naics_missing'] == 0
    assert report['years']['2022']['naics_not_2022'] == 1
    assert report['years']['2022']['naics_conflict'] == 1
    assert report['years']['2022']['case_a'] == 1
    assert (first['case_b'], first['case_c']) == (1, 1)
    assert report['stops'] == []
    assert report['ok'] is True
    assert sorted(report['years']) == ['2022', '2023', '2024']


def test_measure_counts_each_naics_class_with_distinct_numbers(script, capsys, env):
    stage(env, {2022: known_2022(), 2023: known_2023(), 2024: known_2024()}, bom=(2023,))
    years = run_measure(script, capsys, env)['years']
    second = years['2023']
    assert second['rows'] == 12
    assert second['facility_years'] == 10
    assert second['naics_valid'] == 4
    assert second['naics_missing'] == 1
    assert second['naics_conflict'] == 2
    assert second['naics_not_2022'] == 3
    assert years['2024']['facility_years'] == 6
    assert years['2024']['naics_valid'] == 6
    assert (years['2024']['naics_missing'], years['2024']['naics_conflict'],
            years['2024']['naics_not_2022']) == (0, 0, 0)


def test_measure_counts_the_parent_cases_and_fills(script, capsys, env):
    stage(env, {2022: known_2022(), 2023: known_2023(), 2024: known_2024()})
    years = run_measure(script, capsys, env)['years']
    second = years['2023']
    assert (second['case_a'], second['case_b'], second['case_c']) == (2, 4, 5)
    assert second['fill'] == {
        'parent_name': {'facility_years': 7, 'rows': 9},
        'standardized_parent': {'facility_years': 5, 'rows': 6},
        'parent_dnb': {'facility_years': 6, 'rows': 7},
    }
    assert (second['standardized_compared'], second['standardized_differs']) == (3, 1)
    first = years['2022']
    assert first['fill'] == {
        'parent_name': {'facility_years': 2, 'rows': 3},
        'standardized_parent': {'facility_years': 2, 'rows': 4},
        'parent_dnb': {'facility_years': 2, 'rows': 3},
    }
    assert (first['standardized_compared'], first['standardized_differs']) == (1, 1)


def test_measure_counts_names_with_more_than_one_dnb_number_and_the_reverse(
        script, capsys, env):
    stage(env, {2022: known_2022(), 2023: known_2023(), 2024: known_2024()})
    years = run_measure(script, capsys, env)['years']
    assert years['2024']['standardized_with_many_dnb'] == 2
    assert years['2024']['dnb_with_many_standardized'] == 1
    assert years['2023']['standardized_with_many_dnb'] == 0
    assert years['2022']['dnb_with_many_standardized'] == 0
    assert years['2024']['standardized_compared'] == 6
    assert years['2024']['standardized_differs'] == 6


def test_measure_counts_value_sets_as_delivered(script, capsys, env):
    stage(env, {2022: known_2022(), 2023: known_2023(), 2024: known_2024()})
    years = run_measure(script, capsys, env)['years']
    first = years['2022']
    assert first['form_type'] == {'A': 2, 'R': 3}
    assert first['federal'] == {'NO': 3, 'YES': 2}
    assert first['state'] == {'OH': 3, 'PA': 2}
    assert years['2023']['form_type'] == {'R': 12}


def test_measure_counts_a_value_that_differs_only_in_padding_separately(script, capsys, env):
    rows = calm(2022) + [
        record(2022, 'T3', ' R', state='oh', federal='No'),
        record(2022, 'T4', 'R', state='OH ', federal=''),
        record(2022, 'T5', 'R', state='', federal=' NO'),
    ]
    stage(env, calm_window(y2022=rows))
    first = run_measure(script, capsys, env)['years']['2022']
    assert first['form_type'] == {' R': 1, 'R': 4}
    assert first['state'] == {'': 1, 'OH': 2, 'OH ': 1, 'oh': 1}
    assert first['federal'] == {'': 1, ' NO': 1, 'NO': 2, 'No': 1}


def test_measure_counts_secondary_naics_fill_by_cell(script, capsys, env):
    stage(env, {2022: known_2022(), 2023: known_2023(), 2024: known_2024()})
    years = run_measure(script, capsys, env)['years']
    assert years['2022']['other_naics_fill'] == {
        '9. NAICS 2': 2, '10. NAICS 3': 1, '11. NAICS 4': 0, '12. NAICS 5': 0,
        '13. NAICS 6': 0}
    assert set(years['2023']['other_naics_fill'].values()) == {0}


def test_measure_counts_secondary_naics_fill_after_stripping(script, capsys, env):
    rows = calm(2023) + [record(2023, 'T3', naics4='  ', naics5=' 111110 ', naics6='111110')]
    stage(env, calm_window(y2023=rows))
    fill = run_measure(script, capsys, env)['years']['2023']['other_naics_fill']
    assert fill['11. NAICS 4'] == 0
    assert fill['12. NAICS 5'] == 1
    assert fill['13. NAICS 6'] == 1


def test_measure_counts_document_control_number_uniqueness(script, capsys, env):
    rows = calm(2022) + [
        record(2022, 'T3', dcn='D1'), record(2022, 'T4', dcn='D1'),
        record(2022, 'T5', dcn='D2'), record(2022, 'T6', dcn=''),
        record(2022, 'T7', dcn='  '), record(2022, 'T8', dcn='D3'),
        record(2022, 'T9', dcn='D3'), record(2022, 'T10', dcn='D3'),
        record(2022, 'T11', dcn=' D2 '),
    ]
    stage(env, calm_window(y2022=rows))
    years = run_measure(script, capsys, env)['years']
    assert years['2022']['document_control_number'] == {
        'blank': 2, 'distinct': 5, 'repeated': 3}
    assert years['2023']['document_control_number'] == {
        'blank': 0, 'distinct': 2, 'repeated': 0}


def test_measure_counts_invalid_utf8_lines_and_reads_a_bom(script, capsys, env):
    stage(env, {2022: known_2022(), 2023: known_2023()}, bom=(2023,))
    import_years(env, {2024: csv_bytes(2024, known_2024()).replace(b'CAFE', b'CAF\xe9')})
    years = run_measure(script, capsys, env)['years']
    assert [years[year]['invalid_utf8_lines'] for year in ('2022', '2023', '2024')] == [0, 0, 1]


def test_measure_lists_the_parent_fields_each_year_maps(script, capsys, env):
    stage(env, {2022: known_2022(), 2023: known_2023(), 2024: known_2024()})
    unmapped = {2023: ['parent_name']}
    years = run_measure(script, capsys, env, draft_document(unmapped))['years']
    assert years['2022']['parent_fields'] == {
        'parent_name': '14. PARENT CO NAME', 'parent_dnb': '15. PARENT CO DB NUM',
        'standardized_parent': '16. STANDARDIZED PARENT COMPANY',
        'foreign_parent_name': None, 'foreign_parent_dnb': None,
        'standardized_foreign_parent': None,
    }
    assert years['2023']['parent_fields']['parent_name'] is None
    assert years['2023']['parent_fields']['foreign_parent_dnb'] == '18. FOREIGN PARENT CO DB NUM'


def test_measure_lists_the_most_frequent_stripped_parent_values(script, capsys, env):
    rows = known_2022() + [
        record(2022, 'T4', parent=' ACME CORP ', standardized='ACME HOLDINGS '),
        record(2022, 'T5', parent=' ', standardized=' '),
        record(2022, 'T6', parent='', standardized=''),
    ]
    stage(env, calm_window(y2022=rows))
    first = run_measure(script, capsys, env)['years']['2022']
    # Most frequent first. Equal counts follow the order of the stripped values.
    assert first['parent_name_top'] == [
        ['ACME CORP', 3], ['', 2], ['NA', 2], ['GAMMA LLC', 1]]
    assert first['standardized_parent_top'] == [
        ['', 3], ['ACME HOLDINGS', 3], ['BETA GROUP', 2]]


def test_measure_caps_the_frequent_value_lists_at_twenty(script, capsys, env):
    rows = []
    names = {f'D{n:02d}': 23 - n for n in range(1, 23)}
    names['D23'] = 3
    for name, count in names.items():
        rows += [record(2022, f'T{name}-{i}', parent=name, standardized=name, dnb=name)
                 for i in range(count)]
    stage(env, calm_window(y2022=rows))
    first = run_measure(script, capsys, env)['years']['2022']
    expected = [[f'D{n:02d}', 23 - n] for n in range(1, 21)]
    assert first['parent_name_top'] == expected
    assert first['standardized_parent_top'] == expected
    assert first['parent_dnb_not_nine_digits_top'] == expected
    assert len(first['parent_name_top']) == 20


def test_measure_prints_only_dnb_values_that_are_not_nine_ascii_digits(script, capsys, env):
    odd = ['NA', ' NA', 'NA', '', '12345678', '1234567890', '12-345-6789', '٠١٢٣٤٥٦٧٨',
           '１２３４５６７８９']
    nine = ['123456789', ' 123456789 ', '012345678', '999999999', '123456789\t']
    rows = [record(2022, f'T{n}', dnb=value) for n, value in enumerate(odd + nine)]
    stage(env, calm_window(y2022=rows + calm(2022)))
    report = run_measure(script, capsys, env)
    assert report['years']['2022']['parent_dnb_not_nine_digits_top'] == [
        ['NA', 3], ['', 1], ['12-345-6789', 1], ['12345678', 1], ['1234567890', 1],
        ['٠١٢٣٤٥٦٧٨', 1], ['１２３４５６７８９', 1]]
    # '1234567890' holds a nine-digit run, so look for each value as a whole JSON string.
    for value in nine + ['500000001', '500000002']:
        assert json.dumps(value.strip()) not in report.text


def test_measure_exits_0_and_records_its_inputs_when_no_stop_holds(script, capsys, env):
    stage(env, calm_window())
    report = run_measure(script, capsys, env)
    assert report['stops'] == []
    assert report['asks'] == []
    assert report['ok'] is True
    assert report['inputs']['processed_as_of'] == '2025-11-05'
    assert report['inputs']['codes_run'] == env.run
    assert report['inputs']['codes_outputs_sha256'] == env.pin
    for year in WINDOW:
        file = tri_raw.raw_path(env.data_dir, year, PROCESSED)
        assert report['inputs']['files'][str(year)] == {
            'path': file.relative_to(env.data_dir).as_posix(),
            'sha256': manifest.sha256_file(file)}


STOP_FIELDS = {'no_primary': 'primary_naics', 'no_federal': 'federal',
               'no_standardized': 'standardized_parent'}


@pytest.mark.parametrize('year', WINDOW)
@pytest.mark.parametrize('stop', ['no_primary', 'no_federal', 'no_standardized',
                                  'standardized_always_blank'])
def test_measure_reports_each_stop_and_exits_1(stop, year, script, capsys, env):
    rows = calm_window()
    unmapped = {}
    if stop == 'standardized_always_blank':
        rows[year] = calm(year, blank_standardized=True)
    else:
        unmapped = {year: [STOP_FIELDS[stop]]}
    stage(env, rows)
    report = run_measure(script, capsys, env, draft_document(unmapped), expect=1)
    assert report['stops'] == [{'reason': stop, 'year': year}]
    assert report['ok'] is False
    assert report['asks'] == []


def test_measure_reports_every_stop_of_a_year(script, capsys, env):
    stage(env, calm_window())
    unmapped = {2022: ['primary_naics', 'federal', 'standardized_parent'], 2024: ['federal']}
    report = run_measure(script, capsys, env, draft_document(unmapped), expect=1)
    assert report['stops'] == [
        {'reason': 'no_federal', 'year': 2022}, {'reason': 'no_primary', 'year': 2022},
        {'reason': 'no_standardized', 'year': 2022}, {'reason': 'no_federal', 'year': 2024}]


def test_measure_leaves_the_measures_of_a_missing_field_null(script, capsys, env):
    stage(env, calm_window())
    unmapped = {2023: ['primary_naics', 'standardized_parent', 'federal']}
    years = run_measure(script, capsys, env, draft_document(unmapped), expect=1)['years']
    third = years['2023']
    for key in ('naics_valid', 'naics_missing', 'naics_conflict', 'naics_not_2022', 'federal',
                'case_a', 'case_b', 'case_c', 'standardized_compared', 'standardized_differs',
                'standardized_parent_top', 'standardized_with_many_dnb',
                'dnb_with_many_standardized'):
        assert third[key] is None, key
    assert third['fill']['standardized_parent'] is None
    assert third['facility_years'] == 2
    assert third['fill']['parent_name'] == {'facility_years': 2, 'rows': 2}
    assert years['2022']['naics_valid'] == 2


def test_measure_does_not_stop_when_no_facility_year_reports_a_parent(script, capsys, env):
    rows = fy(2023, 'T1') + fy(2023, 'T2', parent='NA') + fy(2023, 'T3', parent=' ')
    stage(env, calm_window(y2023=rows))
    report = run_measure(script, capsys, env)
    assert report['stops'] == []
    assert report['ok'] is True
    assert report['years']['2023']['fill']['parent_name'] == {'facility_years': 0, 'rows': 0}


def test_measure_stops_when_no_facility_year_that_reports_a_parent_has_a_standardized_name(
        script, capsys, env):
    rows = (fy(2023, 'T1', parent='ALPHA') + fy(2023, 'T2', parent='BETA', standardized='NA')
            + fy(2023, 'T3', parent='NA', standardized=''))
    stage(env, calm_window(y2023=rows))
    report = run_measure(script, capsys, env, expect=1)
    assert report['stops'] == [{'reason': 'standardized_always_blank', 'year': 2023}]
    assert report['years']['2023']['case_b'] == 2
    assert report['years']['2023']['case_a'] == 0


def test_measure_does_not_stop_when_one_reporting_facility_year_has_a_standardized_name(
        script, capsys, env):
    rows = (fy(2023, 'T1', parent='ALPHA') + fy(2023, 'T2', parent='BETA')
            + fy(2023, 'T3', parent='GAMMA', standardized='GAMMA INC'))
    stage(env, calm_window(y2023=rows))
    report = run_measure(script, capsys, env)
    assert report['stops'] == []


def test_measure_treats_a_standardized_name_of_a_mixed_facility_year_as_filled(
        script, capsys, env):
    rows = (fy(2023, 'T1', parent='ALPHA') + fy(2023, 'T1', parent='NA', standardized='ALPHA')
            + fy(2023, 'T2', parent='BETA'))
    stage(env, calm_window(y2023=rows))
    third = run_measure(script, capsys, env)['years']['2023']
    assert (third['case_a'], third['case_b']) == (0, 1)


def test_measure_asks_about_an_unmapped_parent_name_and_leaves_its_measures_null(
        script, capsys, env):
    rows = (fy(2023, 'T1', parent='ALPHA', dnb='500000001')
            + fy(2023, 'T2', parent='BETA', dnb='500000002'))
    stage(env, calm_window(y2023=rows))
    report = run_measure(script, capsys, env, draft_document({2023: ['parent_name']}))
    assert report['stops'] == []
    assert report['asks'] == [{'reason': 'parent_name_unmapped', 'year': 2023}]
    third = report['years']['2023']
    for key in ('case_a', 'case_b', 'standardized_compared', 'standardized_differs',
                'parent_name_top'):
        assert third[key] is None, key
    assert third['fill']['parent_name'] is None
    assert third['case_c'] == 2
    assert report['years']['2022']['case_a'] == 0
    assert report['ok'] is True


def test_measure_does_not_stop_on_an_unmapped_parent_name_with_no_standardized_names(
        script, capsys, env):
    rows = calm(2023, blank_standardized=True)
    stage(env, calm_window(y2023=rows))
    report = run_measure(script, capsys, env, draft_document({2023: ['parent_name']}))
    assert report['stops'] == []


@pytest.mark.parametrize('field', ['reporting_year', 'trifd', 'form_type', 'parent_dnb'])
def test_measure_asks_about_a_missing_column_and_exits_0(field, script, capsys, env):
    stage(env, calm_window())
    report = run_measure(script, capsys, env, draft_document({2023: [field]}))
    assert report['asks'] == [{'reason': f'no_{field}', 'year': 2023}]
    assert report['stops'] == []
    assert report['ok'] is True
    third = report['years']['2023']
    if field == 'form_type':
        assert third['form_type'] is None
        assert report['years']['2022']['form_type'] == {'R': 2}
    if field == 'parent_dnb':
        for key in ('parent_dnb_not_nine_digits_top', 'case_c', 'standardized_with_many_dnb',
                    'dnb_with_many_standardized'):
            assert third[key] is None, key
        assert third['fill']['parent_dnb'] is None
        assert third['case_a'] == 0
        assert report['years']['2022']['case_c'] == 0


def test_measure_leaves_the_facility_year_measures_null_without_a_trifd_column(
        script, capsys, env):
    stage(env, calm_window())
    report = run_measure(script, capsys, env, draft_document({2023: ['trifd']}))
    third = report['years']['2023']
    for key in ('facility_years', 'naics_valid', 'naics_not_2022', 'case_a', 'case_c',
                'standardized_differs'):
        assert third[key] is None, key
    assert third['rows'] == 2
    assert third['fill']['standardized_parent'] == {'facility_years': None, 'rows': 2}
    assert third['form_type'] == {'R': 2}
    assert report['years']['2022']['facility_years'] == 2


def test_measure_does_not_stop_on_a_standardized_blank_year_without_a_trifd_column(
        script, capsys, env):
    stage(env, calm_window(y2023=calm(2023, blank_standardized=True)))
    report = run_measure(script, capsys, env, draft_document({2023: ['trifd']}))
    assert report['stops'] == []


def test_measure_keeps_a_blank_trifd_out_of_the_facility_years(script, capsys, env):
    rows = calm(2022) + fy(2022, '') + fy(2022, '  ') + fy(2022, 'T3') + fy(2022, ' T3')
    stage(env, calm_window(y2022=rows))
    first = run_measure(script, capsys, env)['years']['2022']
    assert first['rows'] == 6
    assert first['rows_without_trifd'] == 2
    assert first['facility_years'] == 4


def fixed_window(year, not_2022, *, conflicts=1, missing=1, total=100):
    '''100 facility-years. Valid ones have 3 forms and outside ones 2, so that rows and
    facility-years give different shares.'''
    rows = []
    for index in range(total):
        if index < not_2022:
            primaries = (NOT_2022[0],) * 2
        elif index < not_2022 + conflicts:
            primaries = VALID[:2]
        elif index < not_2022 + conflicts + missing:
            primaries = ('',)
        else:
            primaries = (VALID[0],) * 3
        rows += fy(year, f'T{index:05d}', primaries, parent='P', standardized='P')
    return rows


def test_measure_does_not_ask_at_exactly_one_percent(script, capsys, env):
    # 1 outside code, 1 conflict and 1 missing in 100: only the outside code counts.
    rows = fixed_window(2022, 1)
    assert len({row[CELLS['trifd']] for row in rows}) == 100
    stage(env, calm_window(y2022=rows))
    report = run_measure(script, capsys, env)
    first = report['years']['2022']
    assert (first['facility_years'], first['naics_not_2022']) == (100, 1)
    assert (first['naics_conflict'], first['naics_missing'], first['naics_valid']) == (1, 1, 97)
    assert report['asks'] == []
    assert report['ok'] is True


def test_measure_asks_above_one_percent_and_exits_0(script, capsys, env):
    rows = fixed_window(2022, 2)
    assert len({row[CELLS['trifd']] for row in rows}) == 100
    stage(env, calm_window(y2022=rows))
    report = run_measure(script, capsys, env)
    assert report['asks'] == [{'facility_years': 100, 'naics_not_2022': 2,
                               'reason': 'naics_not_2022_above_1_percent', 'year': 2022}]
    assert report['stops'] == []
    assert report['ok'] is True


def test_measure_asks_just_above_one_percent(script, capsys, env):
    # 2 outside codes in 199 facility-years is 1.005%.
    rows = fixed_window(2022, 2, total=199)
    assert len({row[CELLS['trifd']] for row in rows}) == 199
    stage(env, calm_window(y2022=rows))
    report = run_measure(script, capsys, env)
    assert report['asks'] == [{'facility_years': 199, 'naics_not_2022': 2,
                               'reason': 'naics_not_2022_above_1_percent', 'year': 2022}]


def test_measure_asks_in_each_year_that_is_above_one_percent(script, capsys, env):
    stage(env, {2022: calm(2022), 2023: fixed_window(2023, 2), 2024: fixed_window(2024, 2)})
    report = run_measure(script, capsys, env)
    assert [(ask['year'], ask['naics_not_2022']) for ask in report['asks']] == [
        (2023, 2), (2024, 2)]


def test_measure_does_not_ask_when_there_is_no_facility_year(script, capsys, env):
    stage(env, calm_window(y2022=[]))
    report = run_measure(script, capsys, env)
    assert report['years']['2022']['facility_years'] == 0
    assert report['asks'] == []


def test_measure_accepts_a_draft_with_null_columns_and_empty_value_sets(script, capsys, env):
    stage(env, calm_window())
    sets = {name: [] for name in VALUES}
    report = run_measure(script, capsys, env, draft_document(
        {2022: ['state', 'document_control_number', 'parent_name']}, sets))
    assert report['years']['2022']['state'] is None
    assert report['years']['2022']['document_control_number'] is None
    assert report['years']['2023']['state'] == {'OH': 2}
    # An empty value set still leaves a blank cell unfilled.
    assert report['years']['2023']['fill']['standardized_parent'] == {
        'facility_years': 2, 'rows': 2}


def test_measure_reads_a_blank_cell_as_absent_even_when_no_set_lists_it(script, capsys, env):
    rows = calm(2022) + fy(2022, 'T3', parent='ALPHA') + fy(2022, 'T4', dnb=' ')
    stage(env, calm_window(y2022=rows))
    sets = {**VALUES, 'no_parent': [], 'no_dnb': []}
    first = run_measure(script, capsys, env, draft_document(values=sets))['years']['2022']
    assert first['fill']['standardized_parent'] == {'facility_years': 2, 'rows': 2}
    assert first['fill']['parent_dnb'] == {'facility_years': 2, 'rows': 2}


def test_measure_reads_a_draft_with_absent_column_and_value_entries(script, capsys, env):
    stage(env, calm_window())
    document = draft_document()
    for year in WINDOW:
        columns = document['years'][str(year)]['columns']
        document['years'][str(year)]['columns'] = {
            field: columns[field] for field in ('primary_naics', 'federal', 'trifd',
                                                'standardized_parent')}
        document['years'][str(year)]['values'] = {'no_parent': ['', 'NA']}
    report = run_measure(script, capsys, env, document)
    assert report['stops'] == []
    assert report['years']['2023']['state'] is None
    assert report['years']['2023']['other_naics_fill'] == {}
    assert [ask['reason'] for ask in report['asks'] if ask['year'] == 2023] == [
        'no_form_type', 'no_parent_dnb', 'no_reporting_year', 'parent_name_unmapped']


def test_measure_reads_a_draft_year_with_no_columns_object(script, capsys, env):
    stage(env, calm_window())
    document = draft_document()
    del year_entry(document, 2022)['columns']
    del year_entry(document, 2023)['values']
    report = run_measure(script, capsys, env, document, expect=1)
    assert [stop['reason'] for stop in report['stops']] == [
        'no_federal', 'no_primary', 'no_standardized']
    assert {stop['year'] for stop in report['stops']} == {2022}
    assert report['years']['2022']['rows'] == 2
    assert report['years']['2022']['facility_years'] is None
    assert report['years']['2023']['facility_years'] == 2


def test_measure_accepts_the_strict_committed_format(script, capsys, env):
    stage(env, calm_window())
    strict = tri_layout.layouts_json(tri_layout.parse_layouts(draft_document()))
    report = run_measure(script, capsys, env, json.loads(json.dumps(strict)))
    assert report['ok'] is True
    assert report['years']['2023']['fill']['standardized_parent'] == {
        'facility_years': 2, 'rows': 2}


def test_measure_reads_the_year_of_each_file_not_another(script, capsys, env):
    rows = calm_window(y2023=known_2023())
    stage(env, rows)
    years = run_measure(script, capsys, env)['years']
    assert [years[year]['rows'] for year in ('2022', '2023', '2024')] == [2, 12, 2]


def test_measure_strips_primary_codes_and_reads_a_blank_as_absent(script, capsys, env):
    rows = (fy(2022, 'T1', (VALID[0], f' {VALID[0]} ')) + fy(2022, 'T2', ('  ',))
            + fy(2022, 'T3', ('', VALID[1])) + fy(2022, 'T4', (VALID[0], VALID[1]))
            + fy(2022, 'T5', (f' {NOT_2022[0]}', NOT_2022[0], '')))
    stage(env, calm_window(y2022=rows))
    first = run_measure(script, capsys, env)['years']['2022']
    assert first['facility_years'] == 5
    assert (first['naics_valid'], first['naics_missing'], first['naics_conflict'],
            first['naics_not_2022']) == (2, 1, 1, 1)


def test_measure_compares_padded_values_with_the_none_strings_after_stripping(
        script, capsys, env):
    rows = [record(2022, 'T1', parent=' NA ', standardized='NA ', dnb=' NA'),
            record(2022, 'T2', parent='\tNA', standardized=' NA', dnb='NA\t')]
    stage(env, calm_window(y2022=rows))
    first = run_measure(script, capsys, env)['years']['2022']
    assert first['fill'] == {
        'parent_name': {'facility_years': 0, 'rows': 0},
        'standardized_parent': {'facility_years': 0, 'rows': 0},
        'parent_dnb': {'facility_years': 0, 'rows': 0},
    }
    assert (first['case_a'], first['case_b'], first['case_c']) == (0, 0, 0)


def test_measure_judges_a_parent_by_no_parent_strings_and_a_dnb_number_by_its_own(
        script, capsys, env):
    sets = {**VALUES, 'no_parent': ['', 'NONE'], 'no_dnb': ['', 'UNKNOWN']}
    # Three facility-years hold NONE in all three cells, one holds UNKNOWN, one holds names.
    rows = [record(2022, f'T{n}', parent='NONE', standardized='NONE', dnb='NONE')
            for n in range(1, 4)]
    rows += [record(2022, 'T4', parent='UNKNOWN', standardized='UNKNOWN', dnb='UNKNOWN'),
             record(2022, 'T5', parent='ALPHA', standardized='ALPHA', dnb='500000001')]
    stage(env, calm_window(y2022=rows))
    first = run_measure(script, capsys, env, draft_document(values=sets))['years']['2022']
    assert first['fill'] == {
        'parent_name': {'facility_years': 2, 'rows': 2},
        'standardized_parent': {'facility_years': 2, 'rows': 2},
        'parent_dnb': {'facility_years': 4, 'rows': 4},
    }


def test_measure_keeps_what_any_form_of_a_facility_year_says(script, capsys, env):
    # The first form has a standardized name and a D&B number, the second form has neither.
    rows = (fy(2023, 'T1', parent='ALPHA', standardized='ALPHA INC', dnb='500000009')
            + fy(2023, 'T1', parent='ALPHA') + fy(2023, 'T2', parent='BETA'))
    stage(env, calm_window(y2023=rows))
    third = run_measure(script, capsys, env)['years']['2023']
    assert third['fill'] == {
        'parent_name': {'facility_years': 2, 'rows': 3},
        'standardized_parent': {'facility_years': 1, 'rows': 1},
        'parent_dnb': {'facility_years': 1, 'rows': 1},
    }
    assert (third['case_a'], third['case_b'], third['case_c']) == (0, 1, 0)


def test_measure_decides_whether_a_facility_year_differs_from_all_of_its_forms(
        script, capsys, env):
    def forms(trifd, *names):
        return [row for name in names for row in fy(2022, trifd, parent='A', standardized=name)]

    # T1 and T2: one form agrees and one differs, in each order. T3: two forms differ. T4: the
    # form with no standardized name is not compared. T5: the names differ only in case.
    rows = (forms('T1', 'A', 'B') + forms('T2', 'B', 'A') + forms('T3', 'B', 'C')
            + forms('T4', 'A', '') + forms('T5', 'a'))
    stage(env, calm_window(y2022=rows))
    first = run_measure(script, capsys, env)['years']['2022']
    assert (first['standardized_compared'], first['standardized_differs']) == (5, 4)


def test_measure_counts_names_and_numbers_only_for_forms_that_have_both(script, capsys, env):
    rows = (
        # A name with one usable number and one unusable number has one number.
        fy(2022, 'T1', standardized='RHO', dnb='700000001') + fy(2022, 'T2', standardized='RHO',
                                                                dnb='NA')
        # A blank name with two numbers pairs no number.
        + fy(2022, 'T3', standardized='', dnb='700000002')
        + fy(2022, 'T4', standardized='', dnb='700000003')
        + fy(2022, 'T5', standardized='NA', dnb='700000004')
        # One number under a name, one number under the same name written with padding.
        + fy(2022, 'T6', standardized='SIGMA', dnb='700000005')
        + fy(2022, 'T7', standardized=' SIGMA ', dnb=' 700000005')
    )
    stage(env, calm_window(y2022=rows))
    first = run_measure(script, capsys, env)['years']['2022']
    assert first['standardized_with_many_dnb'] == 0
    assert first['dnb_with_many_standardized'] == 0


# refusals


def draft_edit(edit):
    def apply(document):
        edit(document)
        return document
    return apply


def year_entry(document, year=2023):
    return document['years'][str(year)]


def renamed(old, new):
    def edit(document):
        document['years'][new] = document['years'].pop(old)
    return edit


def set_header(document, year=2023):
    return year_entry(document, year)['header']


def swap_header_cells(document):
    cells = set_header(document)
    cells[0], cells[1] = cells[1], cells[0]


def rename_header_cell(document):
    set_header(document)[4] = '5. STATE'
    year_entry(document)['columns']['state'] = '5. STATE'


DRAFT_REFUSALS = {
    'wrong_version': (lambda d: d.update(version='tri-headers-v0'), 'layout version differs'),
    'no_version': (lambda d: d.pop('version'), 'layout version differs'),
    'no_years': (lambda d: d.pop('years'), 'layout years differ from the window'),
    'missing_year': (lambda d: d['years'].pop('2023'), 'layout years differ from the window'),
    'extra_year': (lambda d: d['years'].update({'2025': year_entry(d)}),
                   'layout years differ from the window'),
    'replaced_year': (renamed('2024', '2021'), 'layout years differ from the window'),
    'year_key_not_a_number': (renamed('2024', 'next'), 'layout years differ from the window'),
    'year_not_an_object': (lambda d: d['years'].update({'2023': []}), 'layout year is malformed'),
    'no_header': (lambda d: year_entry(d).pop('header'),
                  'layout header is not a list of distinct nonblank cells'),
    'header_not_a_list': (lambda d: year_entry(d).update(header='a,b'),
                          'layout header is not a list of distinct nonblank cells'),
    'header_blank_cell': (lambda d: set_header(d).__setitem__(5, ' '),
                          'layout header is not a list of distinct nonblank cells'),
    'header_empty_cell': (lambda d: set_header(d).__setitem__(5, ''),
                          'layout header is not a list of distinct nonblank cells'),
    'header_non_string_cell': (lambda d: set_header(d).__setitem__(5, 5),
                               'layout header is not a list of distinct nonblank cells'),
    'header_repeated_cell': (lambda d: set_header(d).__setitem__(5, set_header(d)[4]),
                             'layout header is not a list of distinct nonblank cells'),
    'columns_not_an_object': (lambda d: year_entry(d).update(columns=[]),
                              'layout year is malformed'),
    'values_not_an_object': (lambda d: year_entry(d).update(values=[]),
                             'layout year is malformed'),
    'unknown_column': (lambda d: year_entry(d)['columns'].update(primary_naic='x'),
                       'layout names an unknown field'),
    'unknown_value_set': (lambda d: year_entry(d)['values'].update(maybe=['x']),
                          'layout names an unknown field'),
    'value_set_not_a_list': (lambda d: year_entry(d)['values'].update(no_dnb='NA'),
                             'layout year is malformed'),
    'value_not_a_string': (lambda d: year_entry(d)['values'].update(no_dnb=['NA', 3]),
                           'layout year is malformed'),
    'column_not_a_string': (lambda d: year_entry(d)['columns'].update(state=3),
                            'layout maps a cell that is not in the header'),
    'column_not_a_header_cell': (lambda d: year_entry(d)['columns'].update(state='NO CELL'),
                                 'layout maps a cell that is not in the header'),
    'required_column_not_a_header_cell': (
        lambda d: year_entry(d, 2024)['columns'].update(primary_naics='NO CELL'),
        'layout maps a cell that is not in the header'),
    'other_naics_cell_not_a_header_cell': (
        lambda d: year_entry(d)['columns'].update(other_naics=['9. NAICS 2', 'NO CELL']),
        'layout maps a cell that is not in the header'),
    'other_naics_not_a_list': (lambda d: year_entry(d)['columns'].update(other_naics='x'),
                               'layout year is malformed'),
    'header_cells_swapped': (swap_header_cells, 'layout header differs from the file header'),
    'header_cell_renamed': (rename_header_cell, 'layout header differs from the file header'),
    'header_cell_added': (lambda d: set_header(d).append('99. EXTRA'),
                          'layout header differs from the file header'),
    'header_cell_dropped': (lambda d: (set_header(d).pop(),
                                       year_entry(d)['columns'].update(
                                           standardized_foreign_parent=None)),
                            'layout header differs from the file header'),
}


@pytest.mark.parametrize('name', list(DRAFT_REFUSALS))
def test_measure_refuses_a_draft_layout_it_cannot_use(name, script, capsys, env):
    stage(env, calm_window())
    edit, reason = DRAFT_REFUSALS[name]
    document = draft_document()
    edit(document)
    report = run_measure(script, capsys, env, document, expect=2)
    assert report == {'ok': False, 'reason': reason}


def test_measure_refuses_a_draft_that_is_not_json_or_not_an_object(script, capsys, env):
    stage(env, calm_window())
    for content in ('{"version": ', '[]', '"tri-headers-v1"', '', 'null'):
        env.scratch.mkdir(parents=True, exist_ok=True)
        file = env.scratch / 'bad.json'
        file.write_text(content)
        report = run_measure(script, capsys, env, layout=file, expect=2)
        assert report == {'ok': False, 'reason': 'layout file cannot be read'}


def test_measure_refuses_a_missing_layout_file(script, capsys, env):
    stage(env, calm_window())
    report = run_measure(script, capsys, env, layout=env.scratch / 'absent.json', expect=2)
    assert report == {'ok': False, 'reason': 'layout file cannot be read'}


@pytest.mark.parametrize('command', ['headers', 'measure'])
def test_the_commands_refuse_when_a_year_has_no_recorded_file(command, script, capsys, env):
    stage(env, {2022: calm(2022), 2023: calm(2023)})
    argv = measure_arguments(env, write_layout(env, draft_document())) if (
        command == 'measure') else []
    report = invoke(script, capsys, env, command, *argv, expect=2)
    assert report == {'ok': False, 'reason': 'raw files cannot be selected'}


def test_measure_refuses_an_unknown_codes_run(script, capsys, env):
    stage(env, calm_window())
    report = run_measure(script, capsys, env, codes_run='no-such-run', expect=2)
    assert report == {'ok': False, 'reason': 'codes nodes cannot be selected'}


def test_measure_refuses_a_wrong_codes_pin(script, capsys, env):
    stage(env, calm_window())
    report = run_measure(script, capsys, env, pin='0' * 64, expect=2)
    assert report == {'ok': False, 'reason': 'codes nodes cannot be selected'}


def test_measure_refuses_a_codes_pin_that_is_not_a_checksum(script, capsys, env):
    stage(env, calm_window())
    report = run_measure(script, capsys, env, pin='abc', expect=2)
    assert report == {'ok': False, 'reason': 'codes nodes cannot be selected'}


def test_measure_refuses_a_record_with_the_wrong_number_of_fields(script, capsys, env):
    stage(env, {2022: calm(2022), 2023: calm(2023)})
    short = csv_bytes(2024, calm(2024)).replace(b'ALPHA,', b'')
    import_years(env, {2024: short})
    report = run_measure(script, capsys, env, expect=2)
    assert report == {'ok': False, 'reason': 'a record has the wrong number of fields'}


def test_measure_refuses_a_record_with_too_many_fields(script, capsys, env):
    stage(env, {2022: calm(2022), 2023: calm(2023)})
    long = csv_bytes(2024, calm(2024)).replace(b'ALPHA,', b'ALPHA,EXTRA,')
    import_years(env, {2024: long})
    report = run_measure(script, capsys, env, expect=2)
    assert report == {'ok': False, 'reason': 'a record has the wrong number of fields'}


def test_measure_refuses_a_file_that_cannot_be_decoded(script, capsys, env):
    stage(env, {2022: calm(2022), 2023: calm(2023)})
    bad = csv_bytes(2024, [record(2024, 'T1', facility='CAFE')]).replace(b'CAFE', b'CAF\x8d')
    import_years(env, {2024: bad})
    report = run_measure(script, capsys, env, expect=2)
    assert report == {'ok': False, 'reason': 'a line cannot be decoded'}


@pytest.mark.parametrize('error', [RuntimeError, KeyError, ZeroDivisionError])
def test_an_unexpected_error_prints_only_its_type(error, script, capsys, env, monkeypatch):
    stage(env, calm_window())

    def explode(*args, **kwargs):
        raise error('secret 123456789 row text')

    monkeypatch.setattr(script, 'measure_year', explode)
    report = run_measure(script, capsys, env, expect=2)
    assert report == {'ok': False, 'reason': f'unexpected error: {error.__name__}'}


def test_both_commands_require_an_explicit_data_directory(script, capsys):
    for argv in (['headers', '--processed-as-of', '2025-11-05'],
                 ['measure', '--processed-as-of', '2025-11-05', '--layout', 'x',
                  '--codes-run', 'r', '--codes-outputs-sha256', '0' * 64]):
        with pytest.raises(SystemExit) as raised:
            script.main(argv)
        assert raised.value.code == 2
    capsys.readouterr()


def test_both_commands_require_a_snapshot_date(script, capsys, tmp_path):
    for argv in (['headers', '--data-dir', str(tmp_path)],
                 ['headers', '--data-dir', str(tmp_path), '--processed-as-of', '2025-13-45']):
        with pytest.raises(SystemExit) as raised:
            script.main(argv)
        assert raised.value.code == 2
    capsys.readouterr()


def test_measure_requires_a_layout_and_the_codes_pin(script, capsys, tmp_path):
    base = ['measure', '--data-dir', str(tmp_path), '--processed-as-of', '2025-11-05']
    for extra in ([], ['--layout', 'x'], ['--layout', 'x', '--codes-run', 'r'],
                  ['--layout', 'x', '--codes-outputs-sha256', '0' * 64],
                  ['--codes-run', 'r', '--codes-outputs-sha256', '0' * 64]):
        with pytest.raises(SystemExit) as raised:
            script.main(base + extra)
        assert raised.value.code == 2
    capsys.readouterr()


# safety


def test_no_nine_digit_value_is_printed_by_any_command_or_refusal(script, capsys, env):
    stage(env, {2022: known_2022(), 2023: known_2023(), 2024: known_2024()}, bom=(2023,))
    nine = {value for rows in (known_2022(), known_2023(), known_2024()) for row in rows
            for value in row.values() if NINE_DIGITS.fullmatch(value.strip())}
    assert len(nine) == 13
    texts = [run_headers(script, capsys, env).text, run_measure(script, capsys, env).text,
             run_measure(script, capsys, env, pin='0' * 64, expect=2).text,
             run_measure(script, capsys, env, draft_document(
                 {2022: ['primary_naics']}), expect=1).text]
    for text in texts:
        for value in nine:
            assert value not in text
            assert json.dumps(value) not in text


def test_the_commands_write_nothing_under_the_data_root_or_scratch(script, capsys, env):
    stage(env, calm_window())
    layout = write_layout(env, draft_document())

    def snapshot():
        root = env.data_dir.parent
        return {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}

    before = snapshot()
    run_headers(script, capsys, env)
    run_measure(script, capsys, env, layout=layout)
    run_measure(script, capsys, env, layout=layout, pin='0' * 64, expect=2)
    assert snapshot() == before


def test_the_commands_use_no_network(script, capsys, env, monkeypatch):
    import socket

    import httpx

    def refuse(*args, **kwargs):
        raise AssertionError('network use')

    monkeypatch.setattr(socket.socket, 'connect', refuse)
    monkeypatch.setattr(httpx.Client, 'send', refuse)
    monkeypatch.setattr(tri_raw, 'make_client', refuse)
    stage(env, calm_window())
    run_headers(script, capsys, env)
    assert run_measure(script, capsys, env)['ok'] is True


def test_the_script_runs_as_a_program_and_exits_with_its_status(env):
    stage(env, calm_window())
    layout = write_layout(env, draft_document({2023: ['federal']}))
    argv = [sys.executable, str(SCRIPT), 'measure', '--data-dir', str(env.data_dir),
            '--processed-as-of', '2025-11-05', *map(str, measure_arguments(env, layout))]
    stopped = subprocess.run(argv, capture_output=True, text=True, check=False)
    assert stopped.returncode == 1
    assert json.loads(stopped.stdout)['stops'] == [{'reason': 'no_federal', 'year': 2023}]
    refused = subprocess.run([*argv[:-1], '0' * 64], capture_output=True, text=True,
                             check=False)
    assert refused.returncode == 2
    assert json.loads(refused.stdout) == {'ok': False, 'reason': 'codes nodes cannot be selected'}
    headers = subprocess.run(
        [sys.executable, str(SCRIPT), 'headers', '--data-dir', str(env.data_dir),
         '--processed-as-of', '2025-11-05'], capture_output=True, text=True, check=False)
    assert headers.returncode == 0
    assert json.loads(headers.stdout)['2022']['records'] == 2
