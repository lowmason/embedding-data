'''The Stage 14 preflight script: the E4 and E5 data checks `headers` and `measure`.

Every raw file is synthetic. `seed_raw` writes the subaward ZIPs and the extract with the
invented test registries and imports them into a `tmp_path` data root, and each case that
needs other bytes writes and imports them itself. The UEIs, amounts and report IDs are made
up. `DNB_SENTINEL` stands in for D&B Open Data, and no other value is a name or an address.
The tests load the script from its file and patch `load_extract_layout` to
`TEST_EXTRACT_LAYOUT`. Reports and refusals are compared exactly. Fixture results show
software readiness only.
'''

import codecs
import csv
import dataclasses
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import polars as pl
import pytest
from vendor_link_fixtures import (  # noqa: F401
    DNB_SENTINEL,
    TEST_EXTRACT_LAYOUT,
    TEST_SUBAWARD_LAYOUTS,
    extract_line,
    no_live_sam,
    seed_codes_bundle,
    seed_raw,
    subaward_record,
    zip_bytes,
)

from embedding_data import (
    manifest,
    paths,
    sam_raw,
    usaspending_raw,
    vendor_link_codes,
    vendor_link_layouts,
    vendor_link_pairs,
    vendor_link_readers,
)

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'preflight_usaspending_sam.py'
WINDOW = (2024, 2025, 2026)
SNAPSHOT = date(2026, 11, 20)
MONTH = '2026-11'
OTHER_MONTH = '2026-10'
MEMBER = 'Contracts_Subawards_1.csv'
MEMBER_2 = 'Contracts_Subawards_2.csv'
EXTRACT_MEMBER = 'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261102.dat'
OTHER_MEMBER = 'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261002.dat'
EXTRACT_ZIP = 'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261102.ZIP'
OTHER_ZIP = 'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261002.ZIP'
BOF = 'BOF FIXTURE V2 00000000 20261102 0000000 0000000'
EOF = 'EOF FIXTURE V2 00000000 20261102 0000000 0000000'
HEADER_2024 = TEST_SUBAWARD_LAYOUTS[2024].header
HEADERS = {year: TEST_SUBAWARD_LAYOUTS[year].header for year in WINDOW}
P1, P2, S1, S2 = 'PRIME0000001', 'PRIME0000002', 'SUBAW0000001', 'SUBAW0000002'
OTHER, OTHER_2 = 'OTHER0000009', 'OTHER0000008'
UEIS = (P1, P2, S1, S2, OTHER, OTHER_2)
AMOUNTS = ('4817.23', '9031.77', '1,250.00', '77.10', '310.00', '5511.42')
REPORT_ID = 'RPT-7731-X'
MISMATCH_CELL = 'MISMATCH-CELL-ALPHA'
NO_MALFORMED = {'read_rows': 0, 'unread_rows': 0}
# The cells that each hint matches in the 2024 and 2026 test headers, in header order.
HINT_CELLS = {
    'prime_uei': (['prime_awardee_uei', 'prime_awardee_parent_uei'],) * 2,
    'prime_parent_uei': (['prime_awardee_parent_uei'],) * 2,
    'sub_uei': (['subawardee_uei', 'subawardee_parent_uei'],) * 2,
    'sub_parent_uei': (['subawardee_parent_uei'],) * 2,
    'action_date': (['subaward_action_date', 'subaward_action_date_fiscal_year',
                     'prime_award_base_action_date'],) * 2,
    'amount': (['prime_award_amount', 'subaward_amount'],) * 2,
    'subaward_type': (['subaward_type', 'subawardee_business_types'],) * 2,
    'report_id': (['subaward_report_id', 'subaward_fsrs_report_id',
                   'subaward_fsrs_report_year'],
                  ['subaward_report_id', 'subaward_fsrs_report_month',
                   'subaward_fsrs_report_id', 'subaward_fsrs_report_year']),
    'subaward_naics': (['prime_award_naics_code', 'prime_award_naics_description',
                        'subaward_naics'],
                       ['prime_award_naics_code', 'prime_award_naics_description']),
    'prime_naics': (['prime_award_naics_code', 'prime_award_naics_description',
                     'subaward_naics'],
                    ['prime_award_naics_code', 'prime_award_naics_description']),
}


def load_script():
    spec = importlib.util.spec_from_file_location('preflight_usaspending_sam', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def script():
    return load_script()


@pytest.fixture
def invoke(script, capsys, monkeypatch):
    '''Run the script with the test extract layout; return its status, stdout and stderr.'''
    monkeypatch.setattr(vendor_link_layouts, 'load_extract_layout', lambda: TEST_EXTRACT_LAYOUT)

    def call(argv):
        status = script.main(argv)
        out, err = capsys.readouterr()
        return status, out, err
    return call


@pytest.fixture
def run(invoke):
    '''Run the script, check its exit status and its one JSON line, and return the report.'''
    def call(argv, code=0):
        status, out, err = invoke(argv)
        assert (status, err) == (code, '')
        assert out.count('\n') == 1 and out.endswith('\n')
        return json.loads(out)
    return call


@pytest.fixture(scope='module')
def codes(tmp_path_factory):
    root = tmp_path_factory.mktemp('codes')
    run_id, pin = seed_codes_bundle(root / 'data', root / 'originals')
    return root / 'data' / 'derived' / 'codes' / run_id, run_id, pin


@pytest.fixture
def data_dir(tmp_path, codes):
    '''A fresh data root that holds a copy of the codes bundle and nothing else.'''
    bundle, run_id, _ = codes
    root = tmp_path / 'data'
    shutil.copytree(bundle, root / 'derived' / 'codes' / run_id)
    return root


def report(prime, sub, action, amount='', *, year=2024, **fields):
    values = {'prime_uei': prime, 'sub_uei': sub, 'action_date': action, 'amount': amount,
              'subaward_type': 'sub-contract'} | fields
    return subaward_record(TEST_SUBAWARD_LAYOUTS[year], **values)


def window_reports(**changes):
    '''Five FY2024 reports: three usable, one with a blank prime UEI, one outside the window.

    `changes` maps a row index to field values that replace the row's.
    '''
    rows = [dict(prime=P1, sub=S1, action='2024-03-01', amount='4817.23',
                 report_id=REPORT_ID),
            dict(prime=P2, sub=S2, action='2024-04-01', amount='9031.77'),
            dict(prime=P1, sub=S2, action='2024-05-01', amount='1,250.00'),
            dict(prime='', sub=S1, action='2024-03-01', amount='77.10'),
            dict(prime=P1, sub=S1, action='2022-05-01')]
    for index, values in changes.items():
        rows[int(index.removeprefix('row'))] |= values
    return [report(**row) for row in rows]


def firm(uei, code, *, status='A', update='20250115', evs='SAM', layout=TEST_EXTRACT_LAYOUT):
    fields = {'uei': uei, 'registration_status': status, 'last_update_date': update,
              'primary_naics': code, 'naics_code_string': f'{code}Y'}
    if layout.positions['evs_source'] is not None:
        fields['evs_source'] = evs
    return extract_line(layout, **fields)


def window_firms(changes=None):
    '''P1, P2 and S1 with 2022 codes, S2 not in SAM.gov, and OTHER, on no report, with a
    malformed code. `changes` replaces codes, and a None code drops the UEI.'''
    codes = {P1: '541511', P2: '541512', S1: '236220', OTHER: '5415X1'} | (changes or {})
    return [firm(uei, code) for uei, code in codes.items() if code is not None]


def raw_args(data_dir, *, snapshot=SNAPSHOT, month=MONTH):
    return ['--data-dir', str(data_dir), '--snapshot', snapshot.isoformat(),
            '--sam-month', month]


def seed(data_dir, tmp_path, *, reports=None, years=None, firms=None,
         layouts=TEST_SUBAWARD_LAYOUTS, extract_layout=TEST_EXTRACT_LAYOUT,
         extract_member=EXTRACT_MEMBER):
    '''Seed the known window and return the raw arguments.

    FY2024 holds `reports` (the window reports by default), FY2025 one report with a date
    in another format and FY2026 none. `years` replaces whole years, and None drops one.
    '''
    subawards = {2024: {MEMBER: window_reports() if reports is None else reports},
                 2025: {MEMBER: [report(P1, S1, '2024/12/01', '310.00', year=2025)]},
                 2026: {MEMBER: []}} | (years or {})
    seed_raw(data_dir, tmp_path / 'originals',
             {year: members for year, members in subawards.items() if members is not None},
             window_firms() if firms is None else firms, snapshot=SNAPSHOT, month=MONTH,
             subaward_layouts=layouts, extract_layout=extract_layout,
             extract_member=extract_member)
    return raw_args(data_dir)


def draft(*unmapped, layouts=TEST_SUBAWARD_LAYOUTS):
    '''The test registry with each `(year, field)` of `unmapped` left null.'''
    layouts = dict(layouts)
    for year, field in unmapped:
        layouts[year] = dataclasses.replace(layouts[year],
                                            columns=layouts[year].columns | {field: None})
    return layouts


def write_registry(tmp_path, layouts=TEST_SUBAWARD_LAYOUTS):
    file = tmp_path / 'registry.json'
    file.write_text(json.dumps(vendor_link_layouts.subaward_layouts_json(layouts)))
    return file


def measure_args(raw, registry, codes, *, pin=None):
    _, run_id, codes_pin = codes
    return [*raw, '--registry', str(registry), '--codes-run', run_id,
            '--codes-outputs-sha256', codes_pin if pin is None else pin]


@pytest.fixture
def seeded(data_dir, tmp_path):
    return seed(data_dir, tmp_path)


@pytest.fixture
def measured(seeded, tmp_path, codes):
    return measure_args(seeded, write_registry(tmp_path), codes)


def csv_bytes(records, *, bom=False):
    text = io.StringIO()
    csv.writer(text, lineterminator='\r\n').writerows(records)
    return (codecs.BOM_UTF8 if bom else b'') + text.getvalue().encode('utf-8')


def import_subawards(data_dir, tmp_path, year, members):
    '''Import a ZIP of exact member bytes as the file of `year` under `SNAPSHOT`.'''
    file = tmp_path / 'custom' / f'FY{year}_custom.zip'
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(zip_bytes(members))
    usaspending_raw.import_file(data_dir, year, file, snapshot=SNAPSHOT)
    return file


def import_extract(data_dir, tmp_path, body, member=OTHER_MEMBER):
    '''Import an extract ZIP with one member of exact bytes under `OTHER_MONTH`.'''
    file = tmp_path / 'custom' / OTHER_ZIP
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(zip_bytes({member: body}))
    sam_raw.import_file(data_dir, file, month=OTHER_MONTH)


def extract_body(lines, *, bof=BOF, eof=EOF):
    return '\r\n'.join([bof, *lines, eof]).encode('utf-8')


def build_counts(data_dir, layouts, codes, scratch):
    '''The report counts of the seeded window, from the build's own chain of functions.'''
    _, run_id, pin = codes
    node_ids = vendor_link_codes.select_nodes(data_dir, run_id, codes_outputs_sha256=pin).node_ids
    files = usaspending_raw.select_files(data_dir, SNAPSHOT)
    extract = vendor_link_readers.read_extract(sam_raw.select_extract(data_dir, MONTH),
                                               TEST_EXTRACT_LAYOUT)
    rows = vendor_link_readers.read_subawards(files, layouts, scratch).rows
    reported = vendor_link_pairs.reports(rows, layouts)
    usable = reported.filter(pl.col('report_status') == 'usable')
    firms = vendor_link_pairs.firms(usable, extract, TEST_EXTRACT_LAYOUT, node_ids)
    pairs = vendor_link_pairs.pairs(usable, firms)
    counts = vendor_link_pairs.report_counts(reported, firms, pairs, extract, layouts,
                                             TEST_EXTRACT_LAYOUT, node_ids)
    return json.loads(json.dumps(counts))


def sha256_of(tmp_path, year):
    name = f'FY{year}_Contracts_Subawards_fixture.zip'
    return manifest.sha256_file(tmp_path / 'originals' / name)


def tree(root):
    '''Every path under `root` and `root` itself: kind, size, modification time, file hash.'''
    entries = {}
    for path in sorted([root, *root.rglob('*')]):
        stat = path.lstat()
        entries[path.relative_to(root).as_posix()] = (
            path.is_dir(), stat.st_size, stat.st_mtime_ns,
            manifest.sha256_file(path) if path.is_file() else None)
    return entries


def assert_no_row_values(text):
    for value in (*UEIS, *AMOUNTS, REPORT_ID, DNB_SENTINEL):
        assert value not in text


# ---- plan tests

def test_headers_prints_exact_rows_members_and_hints(run, seeded):
    report = run(['headers', *seeded])
    assert report['subawards']['2024']['members'][0]['header'] == list(HEADER_2024)
    assert report['extract']['bof_matches'] is True


def test_measure_counts_a_small_known_window(run, measured):
    # 2024: 5 rows (one blank UEI, one outside window), 2 firms per role, one not in SAM
    report = run(['measure', *measured])
    assert report['e4']['reports']['by_file_year']['2024']['by_status'] == {
        'uei_unusable': 1, 'action_date_invalid': 0, 'outside_window': 1, 'usable': 3}
    assert report['e5']['join_coverage']['subcontractor'] == {'eligible': 1, 'total': 2,
                                                              'share': 0.5}


STOP_CASES = {
    'no_sub_uei': ({'layouts': draft((2024, 'sub_uei'))}, 'no_sub_uei_2024'),
    'no_parent_columns': ({'layouts': draft((2025, 'prime_parent_uei'),
                                            (2025, 'sub_parent_uei'))},
                          'no_parent_columns_2025'),
    'malformed_read_code': ({'firms': window_firms({P1: '54151A'})}, 'malformed_read_codes'),
}


@pytest.mark.parametrize('stop', ['no_sub_uei', 'no_parent_columns', 'malformed_read_code'])
def test_measure_reports_each_stop_and_exits_1(stop, run, data_dir, tmp_path, codes):
    changes, expected = STOP_CASES[stop]
    raw = seed(data_dir, tmp_path, firms=changes.get('firms'))
    registry = write_registry(tmp_path, changes.get('layouts', TEST_SUBAWARD_LAYOUTS))
    report = run(['measure', *measure_args(raw, registry, codes)], code=1)
    assert (report['stops'], report['asks'], report['ok']) == ([expected], [], False)


ASK_CASES = {
    'above_one_percent': ({'firms': window_firms({P2: '517311'})},
                          'trigger_above_one_percent'),
    'low_coverage': ({'firms': window_firms({S1: None})}, 'low_coverage_subcontractor'),
    'sub_grant_value': ({'reports': window_reports(row1={'subaward_type': 'sub-grant'})},
                        'subaward_type_not_sub_contract'),
}


@pytest.mark.parametrize('ask', ['above_one_percent', 'low_coverage', 'sub_grant_value'])
def test_measure_asks_and_exits_0(ask, run, data_dir, tmp_path, codes):
    changes, expected = ASK_CASES[ask]
    raw = seed(data_dir, tmp_path, **changes)
    report = run(['measure', *measure_args(raw, write_registry(tmp_path), codes)])
    assert (report['stops'], report['asks'], report['ok']) == ([], [expected], True)


def test_output_holds_no_uei_or_dnb_value(invoke, seeded, measured):
    # no fixture UEI and no DNB_SENTINEL in either subcommand's output
    for argv in (['headers', *seeded], ['measure', *measured]):
        status, out, err = invoke(argv)
        assert status == 0
        assert_no_row_values(out + err)


def test_preflight_writes_nothing_under_the_data_root(run, data_dir, seeded, measured):
    before = tree(data_dir)
    run(['headers', *seeded])
    run(['measure', *measured])
    assert tree(data_dir) == before


def test_preflight_refuses_an_unrecorded_file(invoke, data_dir, tmp_path, codes):
    raw = seed(data_dir, tmp_path, years={2026: None})
    stray = usaspending_raw.snapshot_dir(data_dir, SNAPSHOT, 2026) / 'FY2026_unrecorded.zip'
    stray.parent.mkdir(parents=True)
    stray.write_bytes(zip_bytes({MEMBER: csv_bytes([HEADERS[2026]])}))
    for argv in (['headers', *raw],
                 ['measure', *measure_args(raw, write_registry(tmp_path), codes)]):
        status, out, err = invoke(argv)
        assert (status, err, json.loads(out)) == (
            2, '', {'reason': 'raw file is not recorded', 'refused': True})


# ---- headers

def expected_hints(column):
    return {field: list(cells[column]) for field, cells in HINT_CELLS.items()}


def test_headers_prints_each_year_and_the_extract_exactly(run, seeded, tmp_path):
    report = run(['headers', *seeded])
    assert sorted(report) == ['extract', 'stops', 'subawards']
    assert report['stops'] == []
    records = {2024: 5, 2025: 1, 2026: 0}
    for year in WINDOW:
        assert report['subawards'][str(year)] == {
            'path': f'raw/usaspending/subcontracts/2026-11-20/FY{year}/'
                    f'FY{year}_Contracts_Subawards_fixture.zip',
            'sha256': sha256_of(tmp_path, year),
            'members': [{'name': MEMBER, 'header': list(HEADERS[year]), 'bom': False,
                         'utf8_valid': True, 'records': records[year], 'ragged': 0,
                         'cells': 30}],
            'header_mismatch': False,
            'header_not_names': False,
            'hints': expected_hints(year == 2026),
        }
    assert report['extract'] == {
        'path': f'raw/sam/entity-extract/public-monthly-v2/2026-11/{EXTRACT_ZIP}',
        'sha256': manifest.sha256_file(tmp_path / 'originals' / EXTRACT_ZIP),
        'member': EXTRACT_MEMBER, 'data_lines': 4, 'field_counts': {'40': 4},
        'bof_matches': True, 'eof_matches': True, 'record_end_matches': 4, 'bof': BOF,
        'eof': EOF,
        'shapes': {
            'uei': [{'count': 4, 'shape': 'AAAAA9999999'}],
            'registration_status': [{'count': 4, 'shape': 'A'}],
            'last_update_date': [{'count': 4, 'shape': '99999999'}],
            'primary_naics': [{'count': 3, 'shape': '999999'}, {'count': 1, 'shape': '9999A9'}],
            'naics_code_string': [{'count': 3, 'shape': '999999A'},
                                  {'count': 1, 'shape': '9999A9A'}],
            'evs_source': [{'count': 4, 'shape': 'AAA'}],
        },
        'tallies': {'registration_status': {'A': 4}, 'evs_source': {'SAM': 4}},
    }


@pytest.mark.parametrize('field', list(HINT_CELLS))
def test_each_hint_lists_the_cells_that_hold_every_keyword(field, run, seeded):
    hints = {year: run(['headers', *seeded])['subawards'][year]['hints'][field]
             for year in ('2024', '2026')}
    assert hints == {'2024': HINT_CELLS[field][0], '2026': HINT_CELLS[field][1]}


def with_cell(year, cell):
    '''The test header of `year` with its `description` cell replaced by `cell`.'''
    return [cell if name == 'description' else name for name in HEADERS[year]]


def zq_header(cell):
    '''Twenty-nine lower-case names with `cell` at index 12. No other output text holds a
    `zq`: hashes, paths, keys and the test headers have none.'''
    names = [f'zqname_{index:02d}' for index in range(29)]
    return [*names[:12], cell, *names[12:]]


def assert_cells_withheld(text, *headers):
    '''No non-empty cell of `headers` appears in the JSON `text`, escaped as JSON escapes it.'''
    for header in headers:
        for cell in header:
            assert not cell or json.dumps(cell)[1:-1] not in text


# Cells that are not lower-case snake_case names: an upper-case letter first or last, a
# digit or `_` first, a `-`, a space or a non-ASCII letter inside, an empty cell, a trailing
# line break, and the UEI, amount and date of a data row.
NOT_NAMES = ['Zqcell', 'zqcelL', '1zqcell', '_zqcell', 'zq-cell', 'zq cell', '', 'zqcellé',
             'zqcell\n', 'PRIME0000001', '4817.23', '2024-03-01']


@pytest.mark.parametrize('cell', NOT_NAMES, ids=[repr(cell) for cell in NOT_NAMES])
def test_a_header_cell_that_is_not_a_lower_case_name_withholds_the_year(cell, run, data_dir,
                                                                        tmp_path):
    raw = seed(data_dir, tmp_path, years={2025: None})
    import_subawards(data_dir, tmp_path, 2025, {
        MEMBER: csv_bytes([zq_header(cell), report(P1, S1, '2024-12-01', year=2025)])})
    report_ = run(['headers', *raw], code=1)
    assert report_['subawards']['2025']['members'] == [
        {'name': MEMBER, 'header': None, 'bom': False, 'utf8_valid': True, 'records': 1,
         'ragged': 0, 'cells': 30}]
    assert (report_['subawards']['2025']['header_mismatch'],
            report_['subawards']['2025']['header_not_names'],
            report_['subawards']['2025']['hints']) == (False, True, None)
    assert report_['stops'] == ['headers_not_names_2025']
    text = json.dumps(report_)
    assert_cells_withheld(text, zq_header(cell))
    assert 'zq' not in text.lower()
    assert_no_row_values(text)


@pytest.mark.parametrize('cell', ['description_2', 'd', 'a_1_b'])
def test_a_lower_case_name_with_digits_and_underscores_is_printed(cell, run, data_dir,
                                                                  tmp_path):
    raw = seed(data_dir, tmp_path, years={2025: None})
    import_subawards(data_dir, tmp_path, 2025, {MEMBER: csv_bytes([with_cell(2025, cell)])})
    report_ = run(['headers', *raw])
    assert report_['subawards']['2025']['members'][0]['header'] == with_cell(2025, cell)
    assert (report_['subawards']['2025']['header_not_names'],
            report_['subawards']['2025']['hints'], report_['stops']) == (
        False, expected_hints(0), [])


@pytest.mark.parametrize('year', WINDOW)
def test_a_single_member_whose_first_record_is_a_data_row_is_withheld(year, run, data_dir,
                                                                       tmp_path):
    raw = seed(data_dir, tmp_path, years={year: None})
    data_row = [S2, '5511.42', '2026-02-14']
    import_subawards(data_dir, tmp_path, year, {
        MEMBER: csv_bytes([data_row, [P2, '310.00', '2025-11-03']])})
    report_ = run(['headers', *raw], code=1)
    assert report_['subawards'][str(year)] == {
        'path': f'raw/usaspending/subcontracts/2026-11-20/FY{year}/FY{year}_custom.zip',
        'sha256': manifest.sha256_file(tmp_path / 'custom' / f'FY{year}_custom.zip'),
        'members': [{'name': MEMBER, 'header': None, 'bom': False, 'utf8_valid': True,
                     'records': 1, 'ragged': 0, 'cells': 3}],
        'header_mismatch': False, 'header_not_names': True, 'hints': None}
    assert report_['stops'] == [f'headers_not_names_{year}']
    text = json.dumps(report_)
    assert_cells_withheld(text, data_row)
    assert '2025-11-03' not in text
    assert_no_row_values(text)


def test_members_whose_lower_case_names_differ_withhold_only_for_the_mismatch(run, data_dir,
                                                                              tmp_path):
    raw = seed(data_dir, tmp_path, years={2025: None})
    alpha, beta = zq_header('zqcell_alpha'), zq_header('zqcell_beta')
    import_subawards(data_dir, tmp_path, 2025, {MEMBER: csv_bytes([alpha]),
                                                MEMBER_2: csv_bytes([beta])})
    report_ = run(['headers', *raw], code=1)
    member = {'header': None, 'bom': False, 'utf8_valid': True, 'records': 0, 'ragged': 0,
              'cells': 30}
    assert report_['subawards']['2025']['members'] == [
        {'name': MEMBER} | member, {'name': MEMBER_2} | member]
    assert (report_['subawards']['2025']['header_mismatch'],
            report_['subawards']['2025']['header_not_names'],
            report_['subawards']['2025']['hints'], report_['stops']) == (
        True, False, None, ['headers_differ_2025'])
    text = json.dumps(report_)
    assert_cells_withheld(text, alpha, beta)
    assert 'zq' not in text.lower()


def test_identical_upper_case_headers_are_withheld_as_not_names(run, data_dir, tmp_path):
    raw = seed(data_dir, tmp_path, years={2025: None})
    upper = [cell.upper() for cell in zq_header('zqcell')]
    import_subawards(data_dir, tmp_path, 2025, {MEMBER: csv_bytes([upper]),
                                                MEMBER_2: csv_bytes([upper])})
    report_ = run(['headers', *raw], code=1)
    assert [member['header'] for member in report_['subawards']['2025']['members']] == [
        None, None]
    assert (report_['subawards']['2025']['header_mismatch'],
            report_['subawards']['2025']['header_not_names'],
            report_['subawards']['2025']['hints'], report_['stops']) == (
        False, True, None, ['headers_not_names_2025'])
    assert 'zq' not in json.dumps(report_).lower()


def test_identical_member_headers_are_printed(run, data_dir, tmp_path):
    raw = seed(data_dir, tmp_path, years={2024: None})
    import_subawards(data_dir, tmp_path, 2024, {
        MEMBER: csv_bytes([HEADER_2024, report(P1, S1, '2024-03-01')]),
        MEMBER_2: csv_bytes([HEADER_2024, report(P2, S2, '2024-04-01'),
                             report(P1, S2, '2024-05-01')], bom=True)})
    report_ = run(['headers', *raw])
    year = report_['subawards']['2024']
    assert year['members'] == [
        {'name': MEMBER, 'header': list(HEADER_2024), 'bom': False, 'utf8_valid': True,
         'records': 1, 'ragged': 0, 'cells': 30},
        {'name': MEMBER_2, 'header': list(HEADER_2024), 'bom': True, 'utf8_valid': True,
         'records': 2, 'ragged': 0, 'cells': 30}]
    assert (year['header_mismatch'], year['header_not_names'], year['hints'],
            report_['stops']) == (False, False, expected_hints(0), [])


@pytest.mark.parametrize('year', WINDOW)
def test_a_year_whose_members_differ_prints_no_header_cell(year, run, data_dir, tmp_path):
    raw = seed(data_dir, tmp_path, years={year: None})
    data_row = report(P2, S2, '2024-06-30', '5511.42', year=year,
                      cell_description=MISMATCH_CELL)
    import_subawards(data_dir, tmp_path, year, {
        MEMBER: csv_bytes([HEADERS[year], report(P1, S1, '2024-03-01', year=year)]),
        MEMBER_2: csv_bytes([[*data_row, DNB_SENTINEL], data_row])})
    status_report = run(['headers', *raw], code=1)
    assert status_report['subawards'][str(year)]['members'] == [
        {'name': MEMBER, 'header': None, 'bom': False, 'utf8_valid': True, 'records': 1,
         'ragged': 0, 'cells': 30},
        {'name': MEMBER_2, 'header': None, 'bom': False, 'utf8_valid': True, 'records': 1,
         'ragged': 1, 'cells': 31}]
    assert status_report['subawards'][str(year)]['header_mismatch'] is True
    # The data row is also not a header of names.
    assert status_report['subawards'][str(year)]['header_not_names'] is True
    assert status_report['subawards'][str(year)]['hints'] is None
    assert status_report['stops'] == [f'headers_differ_{year}', f'headers_not_names_{year}']
    text = json.dumps(status_report)
    assert MISMATCH_CELL not in text
    assert_no_row_values(text)


def test_two_years_whose_members_differ_stop_in_year_order(run, data_dir, tmp_path):
    # 2024: a header beside a data row of as many cells; 2026: a header beside an empty member
    raw = seed(data_dir, tmp_path, years={2024: None, 2026: None})
    import_subawards(data_dir, tmp_path, 2026, {MEMBER: csv_bytes([HEADERS[2026]]),
                                                MEMBER_2: b''})
    import_subawards(data_dir, tmp_path, 2024, {
        MEMBER: csv_bytes([HEADER_2024]),
        MEMBER_2: csv_bytes([report(P1, S1, '2024-03-01')])})
    report_ = run(['headers', *raw], code=1)
    # By rule and then by year: the 2024 data row is also not a header of names.
    assert report_['stops'] == ['headers_differ_2024', 'headers_differ_2026',
                                'headers_not_names_2024']
    assert [report_['subawards'][year]['header_not_names'] for year in ('2024', '2025', '2026')
            ] == [True, False, False]
    member = {'header': None, 'bom': False, 'utf8_valid': True, 'records': 0, 'ragged': 0}
    assert report_['subawards']['2024']['members'] == [
        {'name': MEMBER, 'cells': 30} | member, {'name': MEMBER_2, 'cells': 30} | member]
    assert report_['subawards']['2026']['members'] == [
        {'name': MEMBER, 'cells': 30} | member, {'name': MEMBER_2, 'cells': None} | member]
    assert [report_['subawards'][year]['header_mismatch'] for year in ('2024', '2025', '2026')
            ] == [True, False, True]


def test_a_year_of_one_empty_member_has_no_header_and_no_hints(run, data_dir, tmp_path):
    raw = seed(data_dir, tmp_path, years={2026: None})
    import_subawards(data_dir, tmp_path, 2026, {MEMBER: b''})
    report_ = run(['headers', *raw])
    assert report_['subawards']['2026']['members'] == [
        {'name': MEMBER, 'header': None, 'bom': False, 'utf8_valid': True, 'records': 0,
         'ragged': 0, 'cells': None}]
    assert (report_['subawards']['2026']['header_mismatch'],
            report_['subawards']['2026']['header_not_names'],
            report_['subawards']['2026']['hints'], report_['stops']) == (False, False, None, [])


def shape_lines(**columns):
    '''One extract line for each position of the value lists, with made-up UEIs.'''
    defaults = {'registration_status': 'A', 'last_update_date': '20250115',
                'primary_naics': '541511', 'naics_code_string': '541511Y', 'evs_source': 'SAM'}
    count = len(next(iter(columns.values())))
    return [extract_line(TEST_EXTRACT_LAYOUT, uei=f'SHAPE{index:07d}',
                         **(defaults | {field: values[index]
                                        for field, values in columns.items()}))
            for index in range(count)]


def test_extract_shapes_keep_the_ten_most_frequent_by_count_then_shape(run, data_dir, tmp_path):
    codes = ['541511'] * 3 + ['54151A'] * 2 + ['5', '54', '541', '5415', '54151', '5415111',
                                               'X', 'XY', 'XYZ', 'X5']
    raw = seed(data_dir, tmp_path, firms=shape_lines(primary_naics=codes))
    shapes = run(['headers', *raw])['extract']['shapes']['primary_naics']
    assert shapes == [
        {'count': 3, 'shape': '999999'}, {'count': 2, 'shape': '99999A'},
        {'count': 1, 'shape': '9'}, {'count': 1, 'shape': '99'}, {'count': 1, 'shape': '999'},
        {'count': 1, 'shape': '9999'}, {'count': 1, 'shape': '99999'},
        {'count': 1, 'shape': '9999999'}, {'count': 1, 'shape': 'A'},
        {'count': 1, 'shape': 'A9'}]


def test_shapes_map_letters_and_digits_and_tallies_keep_delivered_values(run, data_dir,
                                                                         tmp_path):
    raw = seed(data_dir, tmp_path, firms=shape_lines(
        registration_status=['A', 'A', ' A', 'É', 'x-1', '٣'],
        evs_source=['SAM', 'D&B', '', 'SAM', ' SAM', 'SAM']))
    extract = run(['headers', *raw])['extract']
    assert extract['shapes']['registration_status'] == [
        {'count': 3, 'shape': 'A'}, {'count': 1, 'shape': ' A'}, {'count': 1, 'shape': '9'},
        {'count': 1, 'shape': 'A-9'}]
    assert extract['shapes']['evs_source'] == [
        {'count': 3, 'shape': 'AAA'}, {'count': 1, 'shape': ''}, {'count': 1, 'shape': ' AAA'},
        {'count': 1, 'shape': 'A&A'}]
    assert extract['tallies'] == {
        'registration_status': {'A': 2, ' A': 1, 'É': 1, 'x-1': 1, '٣': 1},
        'evs_source': {'SAM': 3, 'D&B': 1, '': 1, ' SAM': 1}}


def test_an_unmapped_evs_source_has_no_shapes_and_no_tally(run, data_dir, tmp_path,
                                                           monkeypatch):
    layout = dataclasses.replace(
        TEST_EXTRACT_LAYOUT, positions=TEST_EXTRACT_LAYOUT.positions | {'evs_source': None},
        evs_dnb=frozenset())
    raw = seed(data_dir, tmp_path, firms=[firm(P1, '541511', layout=layout)],
               extract_layout=layout)
    monkeypatch.setattr(vendor_link_layouts, 'load_extract_layout', lambda: layout)
    extract = run(['headers', *raw])['extract']
    assert sorted(extract['shapes']) == ['last_update_date', 'naics_code_string',
                                         'primary_naics', 'registration_status', 'uei']
    assert extract['tallies'] == {'registration_status': {'A': 1}, 'evs_source': None}


FRAMING_CASES = {
    'wrong field count': ([firm(P1, '541511'), firm(P2, '541512') + '|extra'], BOF,
                          {'field_counts': {'40': 1, '41': 1}, 'record_end_matches': 1,
                           'bof_matches': True, 'bof': BOF}),
    'missing record end': ([firm(P1, '541511'), firm(P2, '541512').removesuffix('!end')],
                           BOF,
                           {'field_counts': {'40': 2}, 'record_end_matches': 1,
                            'bof_matches': True, 'bof': BOF}),
    'missing extract framing': ([firm(P1, '541511'), firm(P2, '541512')],
                                'XOF FIXTURE V2 00000000 20261002',
                                {'field_counts': {'40': 2}, 'record_end_matches': 2,
                                 'bof_matches': False}),
}


@pytest.mark.parametrize('message', list(FRAMING_CASES))
def test_headers_prints_the_summary_of_an_extract_that_the_build_refuses(
        message, invoke, run, data_dir, tmp_path, codes):
    lines, bof, summary = FRAMING_CASES[message]
    seed(data_dir, tmp_path)
    import_extract(data_dir, tmp_path, extract_body(lines, bof=bof))
    raw = raw_args(data_dir, month=OTHER_MONTH)
    extract = run(['headers', *raw])['extract']
    assert extract == {
        'path': f'raw/sam/entity-extract/public-monthly-v2/2026-10/{OTHER_ZIP}',
        'sha256': manifest.sha256_file(tmp_path / 'custom' / OTHER_ZIP),
        'member': OTHER_MEMBER, 'data_lines': 2, 'eof_matches': True, 'eof': EOF,
        'shapes': None, 'tallies': None} | summary
    status, out, err = invoke(['measure', *measure_args(raw, write_registry(tmp_path), codes)])
    assert (status, err, json.loads(out)) == (2, '', {'reason': message, 'refused': True})


# ---- measure

def test_measure_prints_the_counts_of_the_build_functions(run, measured, data_dir, tmp_path,
                                                         codes):
    report_ = run(['measure', *measured])
    expected = build_counts(data_dir, TEST_SUBAWARD_LAYOUTS, codes, tmp_path / 'expected')
    assert sorted(report_) == ['asks', 'e4', 'e5', 'ok', 'stops']
    assert (report_['stops'], report_['asks'], report_['ok']) == ([], [], True)
    assert report_['e4']['reports'] == expected['reports']
    assert report_['e5'] == {'firms': expected['firms'],
                             'join_coverage': expected['join_coverage'],
                             'trigger': expected['trigger'], 'extract': expected['extract'],
                             'malformed': {'read_rows': 0, 'unread_rows': 1}}
    assert report_['e5']['join_coverage']['prime'] == {'eligible': 2, 'total': 2, 'share': 1.0}
    assert report_['e5']['firms']['subcontractor']['not_in_sam'] == 1
    assert report_['e5']['trigger']['with_code'] == 3


def test_measure_e4_holds_the_registry_types_and_shapes(run, measured):
    e4 = run(['measure', *measured])['e4']
    assert sorted(e4) == ['columns', 'headers', 'reports', 'shapes', 'subaward_types']
    assert e4['headers'] == {str(year): list(HEADERS[year]) for year in WINDOW}
    assert e4['columns'] == {str(year): dict(TEST_SUBAWARD_LAYOUTS[year].columns)
                             for year in WINDOW}
    assert e4['subaward_types'] == {'2024': {'sub-contract': 5}, '2025': {'sub-contract': 1},
                                    '2026': {}}
    assert e4['shapes'] == {
        'action_date': {'2024': [{'count': 5, 'shape': '9999-99-99'}],
                        '2025': [{'count': 1, 'shape': '9999/99/99'}], '2026': []},
        'amount': {'2024': [{'count': 2, 'shape': '9999.99'}, {'count': 1, 'shape': ''},
                            {'count': 1, 'shape': '9,999.99'}, {'count': 1, 'shape': '99.99'}],
                   '2025': [{'count': 1, 'shape': '999.99'}], '2026': []}}


def test_unmapped_type_and_amount_columns_ask_and_are_not_tallied(run, data_dir, tmp_path,
                                                                  codes):
    raw = seed(data_dir, tmp_path, years={2026: {MEMBER: [
        report(P1, S1, '2026-01-05', '18.00', year=2026, subaward_type='sub-grant')]}})
    registry = write_registry(tmp_path, draft((2026, 'subaward_type'), (2026, 'amount')))
    report_ = run(['measure', *measure_args(raw, registry, codes)])
    assert report_['asks'] == ['no_subaward_type_2026', 'no_amount_2026']
    assert report_['e4']['subaward_types']['2026'] is None
    assert report_['e4']['shapes']['amount']['2026'] is None
    assert report_['e4']['shapes']['action_date']['2026'] == [{'count': 1,
                                                                'shape': '9999-99-99'}]


def test_a_malformed_read_code_skips_the_firm_counts(run, data_dir, tmp_path, codes):
    firms = window_firms({P1: '54151A'}) + [firm(OTHER_2, '12345')]
    raw = seed(data_dir, tmp_path, firms=firms)
    report_ = run(['measure', *measure_args(raw, write_registry(tmp_path), codes)], code=1)
    assert sorted(report_['e5']) == ['extract', 'malformed']
    assert report_['e5']['malformed'] == {'read_rows': 1, 'unread_rows': 2}
    assert report_['e5']['extract']['primary_codes']['malformed'] == 3
    assert report_['e5']['extract']['malformed_unread_rows'] == 2
    assert report_['e4']['reports']['by_file_year']['2024']['by_status']['usable'] == 3
    assert (report_['stops'], report_['ok']) == (['malformed_read_codes'], False)


def test_a_malformed_code_only_on_a_non_usable_report_does_not_stop(run, data_dir, tmp_path,
                                                                   codes):
    # OTHER_2 is the subcontractor of the outside-window report only, so no build step reads
    # its code
    raw = seed(data_dir, tmp_path, reports=window_reports(row4={'sub': OTHER_2}),
               firms=window_firms({OTHER_2: '12345'}))
    report_ = run(['measure', *measure_args(raw, write_registry(tmp_path), codes)])
    assert report_['e5']['malformed'] == {'read_rows': 0, 'unread_rows': 2}
    assert (report_['stops'], report_['ok']) == ([], True)


@pytest.mark.parametrize('field, year', [('prime_uei', 2026), ('action_date', 2025)])
def test_measure_stops_on_an_unmapped_required_column(field, year, run, seeded, tmp_path,
                                                      codes):
    registry = write_registry(tmp_path, draft((year, field)))
    report_ = run(['measure', *measure_args(seeded, registry, codes)], code=1)
    assert (report_['stops'], report_['ok']) == ([f'no_{field}_{year}'], False)


@pytest.mark.parametrize('field', ['prime_parent_uei', 'sub_parent_uei'])
def test_one_parent_column_does_not_stop(field, run, seeded, tmp_path, codes):
    registry = write_registry(tmp_path, draft((2024, field)))
    report_ = run(['measure', *measure_args(seeded, registry, codes)])
    assert (report_['stops'], report_['asks'], report_['ok']) == ([], [], True)


def test_measure_asks_about_low_prime_coverage(run, data_dir, tmp_path, codes):
    raw = seed(data_dir, tmp_path, firms=window_firms({P1: None, P2: None}))
    report_ = run(['measure', *measure_args(raw, write_registry(tmp_path), codes)])
    assert (report_['stops'], report_['asks'], report_['ok']) == (
        [], ['low_coverage_prime'], True)


def test_measure_asks_about_an_unmapped_amount_column(run, seeded, tmp_path, codes):
    registry = write_registry(tmp_path, draft((2025, 'amount')))
    report_ = run(['measure', *measure_args(seeded, registry, codes)])
    assert (report_['stops'], report_['asks']) == ([], ['no_amount_2025'])


# ---- stop and ask rules

@pytest.mark.parametrize('year', WINDOW)
@pytest.mark.parametrize('field', ['prime_uei', 'sub_uei', 'action_date'])
def test_each_unmapped_required_column_is_a_stop(script, field, year):
    assert script.measure_stops(draft((year, field)), NO_MALFORMED) == [f'no_{field}_{year}']


@pytest.mark.parametrize('year', WINDOW)
def test_no_parent_column_in_a_year_is_a_stop(script, year):
    layouts = draft((year, 'prime_parent_uei'), (year, 'sub_parent_uei'))
    assert script.measure_stops(layouts, NO_MALFORMED) == [f'no_parent_columns_{year}']


@pytest.mark.parametrize('field', ['prime_parent_uei', 'sub_parent_uei'])
def test_one_parent_column_in_each_year_is_no_stop(script, field):
    layouts = draft(*((year, field) for year in WINDOW))
    assert script.measure_stops(layouts, NO_MALFORMED) == []


@pytest.mark.parametrize('malformed, stops', [
    ({'read_rows': 1, 'unread_rows': 0}, ['malformed_read_codes']),
    ({'read_rows': 0, 'unread_rows': 5}, []),
    (NO_MALFORMED, [])])
def test_only_malformed_read_codes_stop(script, malformed, stops):
    assert script.measure_stops(TEST_SUBAWARD_LAYOUTS, malformed) == stops


def test_stops_are_listed_by_rule_then_year(script):
    layouts = draft((2026, 'prime_uei'), (2024, 'action_date'), (2025, 'sub_uei'),
                    (2024, 'sub_uei'), (2026, 'prime_parent_uei'), (2026, 'sub_parent_uei'),
                    (2025, 'prime_parent_uei'), (2025, 'sub_parent_uei'))
    assert script.measure_stops(layouts, {'read_rows': 2, 'unread_rows': 0}) == [
        'no_prime_uei_2026', 'no_sub_uei_2024', 'no_sub_uei_2025', 'no_action_date_2024',
        'no_parent_columns_2025', 'no_parent_columns_2026', 'malformed_read_codes']


def e5_of(trigger=0.0, prime=1.0, subcontractor=1.0, *, by_year=None):
    return {'trigger': {'share': trigger,
                        'by_fiscal_year': {'2024': {'share': by_year}}},
            'join_coverage': {'prime': {'share': prime},
                              'subcontractor': {'share': subcontractor}}}


@pytest.mark.parametrize('e5, asks', [
    (e5_of(trigger=0.01), []),
    (e5_of(trigger=0.0100001), ['trigger_above_one_percent']),
    (e5_of(trigger=None), []),
    (e5_of(trigger=0.0, by_year=0.5), []),
    (e5_of(prime=0.5), []),
    (e5_of(prime=0.4999), ['low_coverage_prime']),
    (e5_of(prime=None), []),
    (e5_of(subcontractor=0.5), []),
    (e5_of(subcontractor=0.4999), ['low_coverage_subcontractor']),
    (e5_of(subcontractor=None), []),
    ({'extract': {}, 'malformed': {'read_rows': 1, 'unread_rows': 0}}, []),
], ids=['trigger_at_one_percent', 'trigger_above', 'trigger_none', 'trigger_by_year_only',
        'prime_at_half', 'prime_below', 'prime_none', 'sub_at_half', 'sub_below', 'sub_none',
        'no_firm_counts'])
def test_trigger_and_coverage_asks(script, e5, asks):
    assert script.measure_asks(TEST_SUBAWARD_LAYOUTS, e5, False) == asks


@pytest.mark.parametrize('year', WINDOW)
@pytest.mark.parametrize('field', ['subaward_type', 'amount'])
def test_each_unmapped_type_or_amount_column_is_an_ask(script, field, year):
    assert script.measure_asks(draft((year, field)), e5_of(), False) == [f'no_{field}_{year}']


def test_another_delivered_type_is_an_ask(script):
    assert script.measure_asks(TEST_SUBAWARD_LAYOUTS, e5_of(), True) == [
        'subaward_type_not_sub_contract']


def test_asks_are_listed_by_rule_then_year(script):
    layouts = draft((2026, 'subaward_type'), (2025, 'amount'), (2024, 'amount'),
                    (2024, 'subaward_type'))
    assert script.measure_asks(layouts, e5_of(0.5, 0.1, 0.2), True) == [
        'trigger_above_one_percent', 'low_coverage_prime', 'low_coverage_subcontractor',
        'no_subaward_type_2024', 'no_subaward_type_2026', 'no_amount_2024', 'no_amount_2025',
        'subaward_type_not_sub_contract']


# ---- refusals

def raise_text(*args, **kwargs):
    raise ValueError(f'{P1} {DNB_SENTINEL} 4817.23')


def runtime_text(*args, **kwargs):
    raise RuntimeError(f'{P1} {DNB_SENTINEL} 4817.23')


def changed_subaward_file(data_dir, tmp_path, monkeypatch, script):
    raw = seed(data_dir, tmp_path)
    file = usaspending_raw.select_files(data_dir, SNAPSHOT)[2025]
    file.write_bytes(file.read_bytes() + b'\0')
    return raw, None, None


def missing_subaward_year(data_dir, tmp_path, monkeypatch, script):
    return seed(data_dir, tmp_path, years={2025: None}), None, None


def unrecorded_extract(data_dir, tmp_path, monkeypatch, script):
    seed(data_dir, tmp_path)
    directory = sam_raw.month_dir(data_dir, OTHER_MONTH)
    directory.mkdir(parents=True)
    (directory / OTHER_ZIP).write_bytes(zip_bytes({OTHER_MEMBER: extract_body([])}))
    return raw_args(data_dir, month=OTHER_MONTH), None, None


def changed_extract(data_dir, tmp_path, monkeypatch, script):
    raw = seed(data_dir, tmp_path)
    file = sam_raw.select_extract(data_dir, MONTH)
    file.write_bytes(file.read_bytes() + b'\0')
    return raw, None, None


def month_out_of_range(data_dir, tmp_path, monkeypatch, script):
    seed(data_dir, tmp_path)
    return raw_args(data_dir, month='2026-13'), None, None


def symlinked_snapshot(data_dir, tmp_path, monkeypatch, script):
    seed(data_dir, tmp_path)
    root = data_dir / 'raw' / 'usaspending' / 'subcontracts'
    (root / '2026-11-21').symlink_to(root / SNAPSHOT.isoformat(), target_is_directory=True)
    return raw_args(data_dir, snapshot=date(2026, 11, 21)), None, None


def symlinked_month(data_dir, tmp_path, monkeypatch, script):
    seed(data_dir, tmp_path)
    sam_raw.month_dir(data_dir, OTHER_MONTH).symlink_to(sam_raw.month_dir(data_dir, MONTH),
                                                        target_is_directory=True)
    return raw_args(data_dir, month=OTHER_MONTH), None, None


def missing_registry(data_dir, tmp_path, monkeypatch, script):
    return seed(data_dir, tmp_path), tmp_path / 'absent.json', None


def registry_not_json(data_dir, tmp_path, monkeypatch, script):
    file = tmp_path / 'registry.json'
    file.write_text('{"version": ')
    return seed(data_dir, tmp_path), file, None


def registry_not_utf8(data_dir, tmp_path, monkeypatch, script):
    file = tmp_path / 'registry.json'
    file.write_bytes(b'{"version": "\xff"}')
    return seed(data_dir, tmp_path), file, None


def registry_of_another_version(data_dir, tmp_path, monkeypatch, script):
    file = write_registry(tmp_path)
    file.write_text(file.read_text().replace('headers-v1', 'headers-v2'))
    return seed(data_dir, tmp_path), file, None


def unreadable_extract_layout(data_dir, tmp_path, monkeypatch, script):
    raw = seed(data_dir, tmp_path)
    monkeypatch.setattr(vendor_link_layouts, 'load_extract_layout', raise_text)
    return raw, None, None


def wrong_codes_pin(data_dir, tmp_path, monkeypatch, script):
    return seed(data_dir, tmp_path), None, '0' * 64


def changed_header(data_dir, tmp_path, monkeypatch, script):
    layout = TEST_SUBAWARD_LAYOUTS[2024]
    header = tuple('subaward_description' if cell == 'description' else cell
                   for cell in layout.header)
    registry = write_registry(tmp_path, TEST_SUBAWARD_LAYOUTS | {
        2024: dataclasses.replace(layout, header=header)})
    return seed(data_dir, tmp_path), registry, None


def ragged_record(data_dir, tmp_path, monkeypatch, script):
    rows = window_reports()
    rows[2] = [*rows[2], DNB_SENTINEL]
    return seed(data_dir, tmp_path, reports=rows), None, None


def subaward_not_utf8(data_dir, tmp_path, monkeypatch, script):
    raw = seed(data_dir, tmp_path, years={2024: None})
    body = csv_bytes([HEADER_2024, report(P1, S1, '2024-03-01', 'BADBYTE')])
    import_subawards(data_dir, tmp_path, 2024, {MEMBER: body.replace(b'BADBYTE', b'\xff')})
    return raw, None, None


def unclosed_quote(data_dir, tmp_path, monkeypatch, script):
    raw = seed(data_dir, tmp_path, years={2024: None})
    body = csv_bytes([HEADER_2024]) + f'"{P1},{S1},{DNB_SENTINEL}\r\n'.encode('utf-8')
    import_subawards(data_dir, tmp_path, 2024, {MEMBER: body})
    return raw, None, None


def readme_member(data_dir, tmp_path, monkeypatch, script):
    raw = seed(data_dir, tmp_path, years={2024: None})
    import_subawards(data_dir, tmp_path, 2024, {
        MEMBER: csv_bytes([HEADER_2024, report(P1, S1, '2024-03-01')]),
        'readme.txt': b'About this download\r\n'})
    return raw, None, None


def extra_extract_field(data_dir, tmp_path, monkeypatch, script):
    firms = window_firms() + [firm(OTHER_2, '541511') + '|' + DNB_SENTINEL]
    return seed(data_dir, tmp_path, firms=firms), None, None


def no_record_end(data_dir, tmp_path, monkeypatch, script):
    firms = window_firms() + [firm(OTHER_2, '541511').removesuffix('!end') + DNB_SENTINEL]
    return seed(data_dir, tmp_path, firms=firms), None, None


def no_bof(data_dir, tmp_path, monkeypatch, script):
    seed(data_dir, tmp_path)
    import_extract(data_dir, tmp_path, extract_body(window_firms(), bof=DNB_SENTINEL))
    return raw_args(data_dir, month=OTHER_MONTH), None, None


def other_extract_member(data_dir, tmp_path, monkeypatch, script):
    member = 'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261102.txt'
    return seed(data_dir, tmp_path, extract_member=member), None, None


def extract_not_utf8(data_dir, tmp_path, monkeypatch, script):
    seed(data_dir, tmp_path)
    body = extract_body([firm(P1, '541511'), firm(P2, 'BADBYTE')])
    import_extract(data_dir, tmp_path, body.replace(b'BADBYTE', b'\xff'))
    return raw_args(data_dir, month=OTHER_MONTH), None, None


def subaward_reader_error(data_dir, tmp_path, monkeypatch, script):
    raw = seed(data_dir, tmp_path)
    monkeypatch.setattr(vendor_link_readers, 'subaward_headers', runtime_text)
    monkeypatch.setattr(vendor_link_readers, 'read_subawards', runtime_text)
    return raw, None, None


def extract_reader_error(data_dir, tmp_path, monkeypatch, script):
    raw = seed(data_dir, tmp_path)
    monkeypatch.setattr(vendor_link_readers, 'read_extract', raise_text)
    return raw, None, None


def unexpected_error(data_dir, tmp_path, monkeypatch, script):
    raw = seed(data_dir, tmp_path)
    monkeypatch.setattr(script, 'hints', raise_text)
    monkeypatch.setattr(vendor_link_pairs, 'reports', raise_text)
    return raw, None, None


def scratch_under_the_data_root(data_dir, tmp_path, monkeypatch, script):
    raw = seed(data_dir, tmp_path)
    scratch = data_dir / 'derived' / 'scratch'
    scratch.mkdir()
    monkeypatch.setattr(tempfile, 'tempdir', str(scratch))
    return raw, None, None


BOTH, MEASURE = ('headers', 'measure'), ('measure',)
REFUSALS = [
    (changed_subaward_file, BOTH, 'raw file changed'),
    (missing_subaward_year, BOTH, 'missing or extra raw file'),
    (unrecorded_extract, BOTH, 'raw file is not recorded'),
    (changed_extract, BOTH, 'raw file changed'),
    (month_out_of_range, BOTH, 'month is not YYYY-MM'),
    (symlinked_snapshot, BOTH, 'subaward files are refused'),
    (symlinked_month, BOTH, 'extract is refused'),
    (missing_registry, MEASURE, 'subaward registry is unreadable'),
    (registry_not_json, MEASURE, 'subaward registry is unreadable'),
    (registry_not_utf8, MEASURE, 'subaward registry is unreadable'),
    (registry_of_another_version, MEASURE, 'subaward registry is unreadable'),
    (unreadable_extract_layout, BOTH, 'extract layout is unreadable'),
    (wrong_codes_pin, MEASURE, 'codes bundle is refused'),
    (changed_header, MEASURE, 'changed header'),
    (ragged_record, MEASURE, 'ragged subaward record'),
    (subaward_not_utf8, MEASURE, 'subaward file is not UTF-8'),
    (unclosed_quote, BOTH, 'malformed subaward CSV'),
    (readme_member, MEASURE, 'unexpected ZIP member'),
    (extra_extract_field, MEASURE, 'wrong field count'),
    (no_record_end, MEASURE, 'missing record end'),
    (no_bof, MEASURE, 'missing extract framing'),
    (other_extract_member, BOTH, 'unexpected extract member'),
    (extract_not_utf8, BOTH, 'extract is not UTF-8'),
    (subaward_reader_error, BOTH, 'subaward file is unreadable'),
    (extract_reader_error, BOTH, 'extract is unreadable'),
    (unexpected_error, BOTH, 'unexpected error'),
    (scratch_under_the_data_root, MEASURE, 'scratch is under the data root'),
]


@pytest.mark.parametrize('prepare, command, reason', [
    pytest.param(prepare, command, reason, id=f'{prepare.__name__}-{command}')
    for prepare, commands, reason in REFUSALS for command in commands])
def test_each_refusal_prints_only_its_fixed_reason(prepare, command, reason, invoke, data_dir,
                                                   tmp_path, codes, monkeypatch, script):
    raw, registry, pin = prepare(data_dir, tmp_path, monkeypatch, script)
    if command == 'headers':
        argv = ['headers', *raw]
    else:
        registry = write_registry(tmp_path) if registry is None else registry
        argv = ['measure', *measure_args(raw, registry, codes, pin=pin)]
    before = tree(data_dir)
    status, out, err = invoke(argv)
    assert (status, err, out) == (
        2, '', json.dumps({'reason': reason, 'refused': True}, sort_keys=True) + '\n')
    assert_no_row_values(out)
    assert tree(data_dir) == before


RAW_OPTIONS = ('--data-dir', '--snapshot', '--sam-month')
MEASURE_OPTIONS = ('--registry', '--codes-run', '--codes-outputs-sha256')


@pytest.mark.parametrize('command, option', [
    *(('headers', option) for option in RAW_OPTIONS),
    *(('measure', option) for option in RAW_OPTIONS + MEASURE_OPTIONS)])
def test_each_option_is_required(command, option, script, seeded, tmp_path, codes,
                                 monkeypatch, capsys):
    # A default data root would point at the real tree, so the test moves it out of reach.
    monkeypatch.setattr(paths, 'DATA_DIR', tmp_path / 'nowhere')
    monkeypatch.setattr(vendor_link_layouts, 'load_extract_layout', lambda: TEST_EXTRACT_LAYOUT)
    argv = (['headers', *seeded] if command == 'headers'
            else ['measure', *measure_args(seeded, write_registry(tmp_path), codes)])
    index = argv.index(option)
    del argv[index:index + 2]
    with pytest.raises(SystemExit) as exit_:
        script.main(argv)
    out, err = capsys.readouterr()
    assert (exit_.value.code, out) == (2, '')
    assert f'the following arguments are required: {option}' in err


# ---- scratch and isolation

def test_measure_reads_in_a_removed_scratch_outside_the_data_root(run, measured, data_dir,
                                                                  monkeypatch):
    seen = []
    real = vendor_link_readers.read_subawards

    def spy(files, layouts, scratch):
        seen.append(scratch)
        return real(files, layouts, scratch)

    monkeypatch.setattr(vendor_link_readers, 'read_subawards', spy)
    run(['measure', *measured])
    (scratch,) = seen
    assert scratch.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
    assert not scratch.resolve().is_relative_to(data_dir.resolve())
    assert not scratch.exists()


OFFLINE = """
import importlib.util
import json
import sys

import httpx

sys.path.insert(0, sys.argv[1])
import vendor_link_fixtures
from embedding_data import sam_access, vendor_link_layouts


def refuse(*args, **kwargs):
    raise AssertionError('refused')


vendor_link_layouts.load_extract_layout = lambda: vendor_link_fixtures.TEST_EXTRACT_LAYOUT
httpx.Client.__init__ = refuse
httpx.AsyncClient.__init__ = refuse
sam_access.read_credential = refuse
spec = importlib.util.spec_from_file_location('preflight', sys.argv[2])
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)
codes = [script.main(argv) for argv in json.loads(sys.argv[3])]
loaded = [name for name in ('dotenv', 'ipumspy') if name in sys.modules]
print(json.dumps({'codes': codes, 'loaded': loaded}))
"""


def test_the_script_loads_no_dotenv_reads_no_key_and_opens_no_client(seeded, measured,
                                                                     tmp_path):
    env = {name: value for name, value in os.environ.items()
           if name not in ('SAM_API_KEY', 'IPUMS_API_KEY')}
    argvs = [['headers', *seeded], ['measure', *measured]]
    result = subprocess.run(
        [sys.executable, '-c', OFFLINE, str(Path(__file__).parent), str(SCRIPT),
         json.dumps(argvs)], capture_output=True, text=True, env=env, cwd=tmp_path, check=False)
    assert (result.returncode, result.stderr) == (0, '')
    assert json.loads(result.stdout.splitlines()[-1]) == {'codes': [0, 0], 'loaded': []}
