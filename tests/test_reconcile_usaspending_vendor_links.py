'''The independent vendor-link reconciler, on copies of the V12 bundle and on small typed inputs.

The V12 chain is built once for the module. Each bundle test copies its data directory into its
own `tmp_path`, so a tamper changes only that copy. A tamper rewrites one bundle file, records
the file's new hash in `outputs.json` and takes the new detached pin, so the reconciler trusts the
changed file and must find the change by recomputing. Fixture results show software readiness,
never benchmarks.
'''

import ast
import codecs
import contextlib
import copy
import csv
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest
from vendor_link_fixtures import (  # noqa: F401
    V12_EXTRACT_MEMBER,
    V12_MEMBER,
    V12_PRIME_A,
    V12_RUNS,
    no_live_sam,
    run_vendor_link_v12,
)

from embedding_data import vendor_link_layouts

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'reconcile_usaspending_vendor_links.py'
_SPEC = importlib.util.spec_from_file_location('reconcile_usaspending_vendor_links', SCRIPT)
reconcile = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(reconcile)

RUN = V12_RUNS[0]
BUNDLES = Path('derived/usaspending/vendor-links')
# The V12 chain, built once for the module by `v12_template`.
TEMPLATE = {}


@pytest.fixture(scope='module', autouse=True)
def v12_template(tmp_path_factory):
    '''Build the V12 chain once. Tests copy its data directory and never change it.'''
    with pytest.MonkeyPatch.context() as patches:
        TEMPLATE.update(run_vendor_link_v12(tmp_path_factory.mktemp('reconcile-v12'), patches))
    yield
    TEMPLATE.clear()


def sha256(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def copy_v12(tmp_path: Path) -> Path:
    '''A copy of the V12 data directory under `tmp_path`, with the first run's bundle.'''
    data_dir = tmp_path / 'data'
    shutil.copytree(TEMPLATE['data_dir'], data_dir)
    return data_dir


def bundle(data_dir: Path) -> Path:
    return data_dir / BUNDLES / RUN


def run_main(data_dir: Path, pin: str, run: str = RUN) -> tuple[int, dict, str]:
    '''Call the reconciler in-process. Return its exit status, its one JSON line parsed, and
    the line itself.'''
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        status = reconcile.main(['--data-dir', str(data_dir), '--run', run,
                                 '--outputs-sha256', pin])
    lines = out.getvalue().splitlines()
    assert len(lines) == 1
    return status, json.loads(lines[0]), lines[0]


def rewrite(data_dir: Path, name: str, write) -> str:
    '''Rewrite one bundle file with `write(file)`, record its new hash, size and row count in
    `outputs.json`, and return the new detached pin.'''
    directory = bundle(data_dir)
    file = directory / name
    write(file)
    outputs = directory / 'outputs.json'
    inventory = json.loads(outputs.read_text())
    record = inventory[name]
    record['sha256'] = sha256(file)
    record['size'] = file.stat().st_size
    if name.endswith('.parquet'):
        record['rows'] = pl.read_parquet(file).height
    outputs.write_text(json.dumps(inventory, indent=1, sort_keys=True) + '\n')
    return sha256(outputs)


def tamper_table(data_dir: Path, table: str, change) -> str:
    '''Replace a table with `change(frame)` and return the new pin.'''
    def write(file):
        change(pl.read_parquet(file)).write_parquet(file)
    return rewrite(data_dir, f'{table}.parquet', write)


def tamper_json(data_dir: Path, name: str, change) -> str:
    '''Change a JSON file of the bundle in place with `change(document)`; return the new pin.'''
    def write(file):
        document = json.loads(file.read_text())
        change(document)
        file.write_text(json.dumps(document, indent=1, sort_keys=True) + '\n')
    return rewrite(data_dir, name, write)


def add_one(column: str, row: int = 0):
    '''A table change: add 1 to one cell of an unsigned count column.'''
    def change(frame):
        values = frame[column].to_list()
        values[row] += 1
        return frame.with_columns(pl.Series(column, values, dtype=frame.schema[column]))
    return change


def false_checks(result: dict) -> list[str]:
    return sorted(name for name, passed in result['checks'].items() if passed is not True)


# ---- plan tests

def test_reconciler_registries_equal_the_committed_json():
    assert reconcile.SUBAWARD_HEADERS == json.loads(vendor_link_layouts.SUBAWARD_FILE.read_text())
    assert reconcile.EXTRACT_LAYOUT == json.loads(vendor_link_layouts.EXTRACT_FILE.read_text())


def test_reconciler_imports_no_embedding_data_module():
    tree = ast.parse(SCRIPT.read_text())
    assert not [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                and 'embedding_data' in ast.unparse(n)]


def test_reconciler_reports_equal_on_the_v12_bundle(tmp_path, monkeypatch):
    # exit 0
    data_dir = copy_v12(tmp_path)
    status, result, _line = run_main(data_dir, TEMPLATE['first_pin'])
    assert status == 0
    assert result['equal'] is True
    assert false_checks(result) == []


def test_reconciler_detects_a_changed_count(tmp_path, monkeypatch):
    # copy the bundle, add 1 to one s_suppliers, rewrite outputs.json; the new pin: exit 1
    data_dir = copy_v12(tmp_path)
    pin = tamper_table(data_dir, 'vendor_link_support', add_one('s_suppliers'))
    status, result, _line = run_main(data_dir, pin)
    assert status == 1
    assert result['equal'] is False
    assert false_checks(result) == ['support.s_suppliers']


def test_reconciler_refuses_a_wrong_pin(tmp_path, monkeypatch):
    # exit 2
    data_dir = copy_v12(tmp_path)
    status, result, _line = run_main(data_dir, '0' * 64)
    assert status == 2
    assert result['equal'] is False
    assert result['reason'] == 'detached pin differs'


# ---- strengthening tests: independence and output

def test_reconciler_imports_only_the_standard_library_and_polars():
    tree = ast.parse(SCRIPT.read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            imported.add(node.module.split('.')[0])
    assert imported - set(sys.stdlib_module_names) == {'polars'}


def test_reconciler_records_its_independence():
    text = ' '.join(reconcile.__doc__.split())
    assert 'It imports no `embedding_data` module' in text
    assert 'without reading the build modules or their tests' in text


def test_output_is_one_sorted_json_line_with_no_uei(tmp_path, monkeypatch):
    # Every made-up UEI of the fixture starts with `V12`; the run ID is lower case.
    equal = copy_v12(tmp_path / 'equal')
    unequal = copy_v12(tmp_path / 'unequal')
    refused_copy = copy_v12(tmp_path / 'refused')
    pins = (TEMPLATE['first_pin'],
            tamper_table(unequal, 'vendor_link_pairs', change_cell('prime_uei')),
            '0' * 64)
    for data_dir, pin, expected in zip((equal, unequal, refused_copy), pins, (0, 1, 2),
                                       strict=True):
        status, result, line = run_main(data_dir, pin)
        assert status == expected
        assert line == json.dumps(result, sort_keys=True)
        assert 'V12' not in line
        # The raw files hold a D&B Open Data stand-in at every restricted position.
        assert 'SENTINEL' not in line
    assert result['status'] == 'refused'


def test_an_unexpected_error_prints_a_fixed_reason(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError(f'row {V12_PRIME_A}')

    monkeypatch.setattr(reconcile, 'tally_extract', fail)
    status, result, line = run_main(copy_v12(tmp_path), TEMPLATE['first_pin'])
    assert status == 2
    assert result['reason'] == 'reconciliation failed'
    assert 'V12' not in line


def test_the_command_line_exit_codes(tmp_path):
    def run(data_dir, pin):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), '--data-dir', str(data_dir), '--run', RUN,
             '--outputs-sha256', pin], capture_output=True, text=True, check=False)
        assert completed.stderr == ''
        (line,) = completed.stdout.splitlines()
        return completed.returncode, json.loads(line)

    equal = copy_v12(tmp_path / 'equal')
    unequal = copy_v12(tmp_path / 'unequal')
    pin = tamper_table(unequal, 'vendor_link_marginals', add_one('n_buyers'))
    assert run(equal, TEMPLATE['first_pin'])[0] == 0
    status, result = run(unequal, pin)
    assert (status, false_checks(result)) == (1, ['marginals.n_buyers'])
    status, result = run(equal, 'f' * 64)
    assert (status, result['reason']) == (2, 'detached pin differs')


def test_counts_on_the_v12_bundle(tmp_path, monkeypatch):
    # The fixture's own design (tests/test_vendor_link_v12.py), not real data.
    _status, result, _line = run_main(copy_v12(tmp_path), TEMPLATE['first_pin'])
    assert result['counts'] == {'reports': 36, 'usable': 30, 'pairs': 24, 'firms': 23,
                                'cells': 7, 'targets': 14, 'marginals': 6,
                                'unreadable_lines': 0, 'malformed_read_codes': 0}
    assert result['differing'] == {}
    assert result['run'] == RUN
    assert result['status'] == 'equal'


# ---- tamper tests: each compared quantity, changed in a copy of the bundle

# The tables' key columns and compared columns, written here apart from the script.
TABLE_COLUMNS = {
    'vendor_link_pairs': ('pairs', ('prime_uei', 'sub_uei'), (
        'n_reports', 'n_fy2024', 'n_fy2025', 'n_fy2026', 'prime_status', 'sub_status',
        'prime_node_id', 'sub_node_id', 'flag_intra_group', 'pair_status', 'amount_sum')),
    'vendor_link_support': ('support', ('unit_a', 'unit_b'), (
        's_suppliers', 'b_buyers', 'l_pairs', 'l_fy2024', 'l_fy2025', 'l_fy2026',
        's_including_intra_group', 'b_including_intra_group', 'l_including_intra_group',
        'amount_sum', 'n_reports')),
    'vendor_link_marginals': ('marginals', ('node_id',), (
        'n_suppliers', 'n_buyers', 'n_supplier_pairs', 'n_buyer_pairs', 'n_suppliers_partial',
        'n_buyers_partial', 'n_suppliers_including_intra_group',
        'n_buyers_including_intra_group')),
    'vendor_links': ('targets', ('unit_a', 'unit_b', 'measure'), (
        'source', 'family', 'unit_a_type', 'unit_b_type', 'value', 'se', 'se_method',
        'n_unweighted', 'n_weighted', 'sample_set', 'vintage', 'universe', 'flags')),
}
ORDERED_TABLES = ('vendor_link_pairs', 'vendor_link_support', 'vendor_link_marginals')


def changed(value, dtype):
    '''Another value of the same type.'''
    if dtype == pl.Boolean:
        return not value
    if dtype == pl.String:
        return (value or '') + 'x'
    if dtype == pl.Float64:
        return (value or 0.0) + 0.5
    if isinstance(dtype, pl.Decimal):
        return value + Decimal('0.01')
    if isinstance(dtype, pl.List):
        return [*value, 'extra']
    return value + 1


def change_cell(column: str, row: int = 0, change=changed):
    '''A table change: one cell of `column` gets `change(value, dtype)`, in the column's type.'''
    def tamper(frame):
        dtype = frame.schema[column]
        values = frame[column].to_list()
        values[row] = change(values[row], dtype)
        return frame.with_columns(pl.Series(column, values, dtype=dtype))
    return tamper


CELL_CASES = [pytest.param(table, column, f'{prefix}.{column}', id=f'{prefix}.{column}')
              for table, (prefix, _key, columns) in TABLE_COLUMNS.items() for column in columns]
KEY_CASES = [pytest.param(table, column, f'{prefix}.rows', id=f'{prefix}.key.{column}')
             for table, (prefix, key, _columns) in TABLE_COLUMNS.items() for column in key]


@pytest.mark.parametrize(('table', 'column', 'flag'), CELL_CASES + KEY_CASES)
def test_a_changed_cell_is_flagged(tmp_path, table, column, flag):
    data_dir = copy_v12(tmp_path)
    pin = tamper_table(data_dir, table, change_cell(column))
    status, result, _line = run_main(data_dir, pin)
    assert (status, false_checks(result)) == (1, [flag])
    assert set(result['differing']) == {flag}


ROW_CHANGES = {
    'dropped': lambda frame: frame.slice(1),
    'repeated': lambda frame: pl.concat([frame, frame.head(1)]),
    'reordered': lambda frame: frame.reverse(),
}
ROW_CASES = [pytest.param(table, change, f'{TABLE_COLUMNS[table][0]}.rows',
                          id=f'{TABLE_COLUMNS[table][0]}.{name}')
             for table in TABLE_COLUMNS for name, change in ROW_CHANGES.items()
             if name != 'reordered' or table in ORDERED_TABLES]


@pytest.mark.parametrize(('table', 'change', 'flag'), ROW_CASES)
def test_a_missing_extra_or_moved_row_is_flagged(tmp_path, table, change, flag):
    data_dir = copy_v12(tmp_path)
    pin = tamper_table(data_dir, table, change)
    status, result, _line = run_main(data_dir, pin)
    assert (status, false_checks(result)) == (1, [flag])


SCHEMA_CASES = [
    pytest.param('vendor_link_pairs', lambda frame: frame.with_columns(
        pl.col('n_reports').cast(pl.Int64)), ['pairs.schema'], id='pairs.signed'),
    pytest.param('vendor_link_pairs', lambda frame: frame.with_columns(
        pl.col('amount_sum').cast(pl.Decimal(38, 3))), ['pairs.schema'], id='pairs.scale'),
    pytest.param('vendor_link_pairs', lambda frame: frame.drop('amount_sum'),
                 ['pairs.amount_sum', 'pairs.schema'], id='pairs.dropped'),
    pytest.param('vendor_link_support', lambda frame: frame.with_columns(
        pl.col('l_pairs').cast(pl.Int64)), ['support.schema'], id='support.signed'),
    pytest.param('vendor_link_support', lambda frame: frame.select(reversed(frame.columns)),
                 ['support.schema'], id='support.column_order'),
    pytest.param('vendor_link_marginals', lambda frame: frame.with_columns(
        pl.col('n_buyers').cast(pl.UInt32)), ['marginals.schema'], id='marginals.narrow'),
    pytest.param('vendor_links', lambda frame: frame.with_columns(
        pl.col('n_unweighted').cast(pl.Int64)), ['targets.schema'], id='targets.signed'),
    pytest.param('vendor_links', lambda frame: frame.drop('unit_b'),
                 ['targets.rows', 'targets.schema'], id='targets.no_key'),
]


@pytest.mark.parametrize(('table', 'change', 'flags'), SCHEMA_CASES)
def test_a_changed_schema_is_flagged(tmp_path, table, change, flags):
    data_dir = copy_v12(tmp_path)
    pin = tamper_table(data_dir, table, change)
    status, result, _line = run_main(data_dir, pin)
    assert (status, false_checks(result)) == (1, flags)


def test_floats_are_compared_within_the_tolerance(tmp_path, monkeypatch):
    near = copy_v12(tmp_path / 'near')
    far = copy_v12(tmp_path / 'far')
    pin = tamper_table(near, 'vendor_links',
                       change_cell('value', change=lambda value, dtype: value + 1e-14))
    assert run_main(near, pin)[0] == 0
    pin = tamper_table(far, 'vendor_links',
                       change_cell('value', change=lambda value, dtype: value - 1e-10))
    status, result, _line = run_main(far, pin)
    assert (status, false_checks(result)) == (1, ['targets.value'])


def at(document, path):
    for step in path:
        document = document[step]
    return document


def bump(*path, by=1):
    '''A JSON change: add `by` to the number at `path`.'''
    def change(document):
        *parents, last = path
        at(document, parents)[last] += by
    return change


def delete(*path):
    def change(document):
        *parents, last = path
        del at(document, parents)[last]
    return change


def put(*path, value):
    def change(document):
        *parents, last = path
        at(document, parents)[last] = value
    return change


YEARS = ('join_coverage', 'by_fiscal_year')
REPORT_CASES = [
    ('report.reports.total.by_status', bump('reports', 'total', 'by_status', 'usable')),
    ('report.reports.2024.by_status',
     bump('reports', 'by_file_year', '2024', 'by_status', 'uei_unusable')),
    ('report.reports.2025.by_status',
     bump('reports', 'by_file_year', '2025', 'by_status', 'action_date_invalid')),
    ('report.reports.2026.by_status',
     bump('reports', 'by_file_year', '2026', 'by_status', 'outside_window')),
    ('report.firms.all', bump('firms', 'all', 'eligible')),
    ('report.firms.all', put('firms', 'all', 'malformed_code', value=0)),
    ('report.firms.prime', bump('firms', 'prime', 'not_in_sam')),
    ('report.firms.subcontractor', bump('firms', 'subcontractor', 'naics_conflict')),
    ('report.firms.last_update_invalid', bump('firms', 'last_update_invalid')),
    ('report.pairs', bump('pairs', 'intra_group')),
    ('report.pairs', bump('pairs', 'total')),
    ('report.pairs', delete('pairs')),
    ('report.n_pairs', bump('n_pairs', 'including_intra_group')),
    ('report.n_buyers', bump('n_buyers', 'eligible')),
    ('report.n_suppliers', bump('n_suppliers', 'including_intra_group')),
    ('report.cells_only_intra_group', bump('cells_only_intra_group')),
    ('report.join_coverage.prime', bump('join_coverage', 'prime', 'eligible')),
    ('report.join_coverage.subcontractor', bump('join_coverage', 'subcontractor', 'total')),
    ('report.join_coverage.subcontractor',
     bump('join_coverage', 'subcontractor', 'share', by=1e-9)),
    ('report.join_coverage.2024.prime', bump(*YEARS, '2024', 'prime', 'total')),
    ('report.join_coverage.2024.subcontractor',
     bump(*YEARS, '2024', 'subcontractor', 'eligible')),
    ('report.join_coverage.2025.prime', bump(*YEARS, '2025', 'prime', 'share', by=1e-9)),
    ('report.join_coverage.2025.subcontractor',
     bump(*YEARS, '2025', 'subcontractor', 'total')),
    ('report.join_coverage.2026.prime', bump(*YEARS, '2026', 'prime', 'eligible')),
    ('report.join_coverage.2026.subcontractor',
     delete(*YEARS, '2026', 'subcontractor', 'share')),
    ('report.trigger.naics_not_2022', bump('trigger', 'naics_not_2022')),
    ('report.trigger.with_code', bump('trigger', 'with_code')),
    ('report.trigger.share', bump('trigger', 'share', by=1e-9)),
    ('report.trigger.2024', bump('trigger', 'by_fiscal_year', '2024', 'with_code')),
    ('report.trigger.2025', bump('trigger', 'by_fiscal_year', '2025', 'share', by=1e-9)),
    ('report.trigger.2026', bump('trigger', 'by_fiscal_year', '2026', 'naics_not_2022')),
    ('report.extract.unreadable_lines', bump('extract', 'unreadable_lines')),
    ('report.extract.unreadable_firms',
     bump('extract', 'unreadable_firms', 'subcontractor')),
    ('report.extract.unreadable_firms_not_in_sam',
     bump('extract', 'unreadable_firms_not_in_sam', 'all')),
    ('report.extract.last_update_invalid_rows',
     bump('extract', 'last_update_by_year', 'invalid')),
]


@pytest.mark.parametrize(('flag', 'change'), [
    pytest.param(flag, change, id=f'{flag}-{number}')
    for number, (flag, change) in enumerate(REPORT_CASES)])
def test_a_changed_report_count_is_flagged(tmp_path, flag, change):
    data_dir = copy_v12(tmp_path)
    pin = tamper_json(data_dir, 'report.json', change)
    status, result, _line = run_main(data_dir, pin)
    assert (status, false_checks(result)) == (1, [flag])


def test_a_report_section_that_is_gone_is_flagged_not_refused(tmp_path, monkeypatch):
    data_dir = copy_v12(tmp_path)
    pin = tamper_json(data_dir, 'report.json', delete('trigger', 'by_fiscal_year'))
    status, result, _line = run_main(data_dir, pin)
    assert (status, false_checks(result)) == (
        1, ['report.trigger.2024', 'report.trigger.2025', 'report.trigger.2026'])


def test_trigger_and_coverage_are_compared_by_named_counts(tmp_path, monkeypatch):
    # Default 14 gives the trigger a by-fiscal-year part, so no literal dict is compared. A
    # share within the tolerance is equal.
    data_dir = copy_v12(tmp_path)

    def change(report):
        report['trigger']['by_fiscal_year']['2025']['note'] = 1
        report['join_coverage']['prime']['note'] = 1
        report['join_coverage']['prime']['share'] += 1e-14
        report['trigger']['share'] -= 1e-14

    pin = tamper_json(data_dir, 'report.json', change)
    status, result, _line = run_main(data_dir, pin)
    assert (status, false_checks(result)) == (0, [])


INPUT_CASES = [
    ('inputs.registries', put('registries', 'extract_layout', 'field_count', value=141)),
    ('inputs.registries', put('registries', 'subaward_headers', 'years', '2025',
                              'date_format', value='%Y/%m/%d')),
    ('inputs.registries', delete('registries')),
    ('inputs.selection', put('snapshot', value='2026-11-21')),
    ('inputs.selection', put('sam_month', value='2026-10')),
    ('inputs.selection', put('window', value=[2024, 2025])),
]


@pytest.mark.parametrize(('flag', 'change'), [
    pytest.param(flag, change, id=f'{flag}-{number}')
    for number, (flag, change) in enumerate(INPUT_CASES)])
def test_a_changed_input_record_is_flagged(tmp_path, flag, change):
    data_dir = copy_v12(tmp_path)
    pin = tamper_json(data_dir, 'inputs.json', change)
    status, result, _line = run_main(data_dir, pin)
    assert (status, false_checks(result)) == (1, [flag])


def test_the_universe_is_filled_from_the_raw_paths(tmp_path, monkeypatch):
    # The universe names the snapshot of the subaward paths and the month of the extract path.
    data_dir = copy_v12(tmp_path)
    universe = pl.read_parquet(bundle(data_dir) / 'vendor_links.parquet')['universe'][0]
    assert 'snapshot 2026-11-20,' in universe and 'extract of 2026-11.' in universe

    def change(frame):
        return frame.with_columns(pl.col('universe').str.replace('2026-11-20', '2026-11-21'))

    pin = tamper_table(data_dir, 'vendor_links', change)
    status, result, _line = run_main(data_dir, pin)
    assert (status, false_checks(result)) == (1, ['targets.universe'])


def raw_entries(data_dir: Path) -> dict:
    return json.loads((bundle(data_dir) / 'inputs.json').read_text())['raw']


def rewrite_member(file: Path, edit) -> None:
    '''Rewrite the one member of a raw ZIP with `edit(text)`.'''
    with zipfile.ZipFile(file) as archive:
        (name,) = archive.namelist()
        text = archive.read(name).decode('utf-8')
    with zipfile.ZipFile(file, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, edit(text).encode('utf-8'))


def reseal_extract(data_dir: Path, edit) -> str:
    '''Change the raw extract, record its new SHA-256 in `inputs.json`, return the new pin.'''
    file = data_dir / 'raw' / raw_entries(data_dir)['extract']['path']
    rewrite_member(file, edit)
    return tamper_json(data_dir, 'inputs.json', put('raw', 'extract', 'sha256',
                                                    value=sha256(file)))


def insert_line(line: str):
    def edit(text):
        lines = text.split('\r\n')
        return '\r\n'.join([lines[0], line, *lines[1:]])
    return edit


def test_a_skipped_extract_line_counts_and_gives_its_firm_nothing(tmp_path, monkeypatch):
    # Owner, 2026-11-19: a line with the wrong field count is skipped and counted. The line here
    # has 143 fields and the UEI of the fixture's not-in-SAM firm, which stays not in SAM.
    data_dir = copy_v12(tmp_path)
    fields = [''] * 143
    fields[0], fields[9], fields[32], fields[-1] = 'V12NOTSAM005', '20250115', '541511', '!end'
    pin = reseal_extract(data_dir, insert_line('|'.join(fields)))
    status, result, _line = run_main(data_dir, pin)
    assert (status, false_checks(result)) == (1, [
        'report.extract.unreadable_firms', 'report.extract.unreadable_firms_not_in_sam',
        'report.extract.unreadable_lines'])
    assert result['counts']['unreadable_lines'] == 1


def test_a_skipped_line_of_a_firm_with_a_readable_row(tmp_path, monkeypatch):
    # The firm keeps its readable row and its status; only the unreadable counts move.
    data_dir = copy_v12(tmp_path)
    fields = [''] * 141
    fields[0], fields[-1] = 'V12SUBAWA001', '!end'
    pin = reseal_extract(data_dir, insert_line('|'.join(fields)))
    status, result, _line = run_main(data_dir, pin)
    assert (status, false_checks(result)) == (1, [
        'report.extract.unreadable_firms', 'report.extract.unreadable_lines'])


def test_a_skipped_line_of_a_firm_on_no_usable_report(tmp_path, monkeypatch):
    data_dir = copy_v12(tmp_path)
    pin = reseal_extract(data_dir, insert_line('V12UNREAD001|20250115'))
    status, result, _line = run_main(data_dir, pin)
    assert (status, false_checks(result)) == (1, ['report.extract.unreadable_lines'])


# ---- refusals: exit 2 with a fixed reason

def refused(data_dir: Path, pin: str, run: str = RUN) -> str:
    status, result, line = run_main(data_dir, pin, run)
    assert status == 2
    assert (result['equal'], result['status']) == (False, 'refused')
    assert 'checks' not in result
    assert 'V12' not in line
    return result['reason']


def test_refuses_an_unsafe_or_absent_run(tmp_path, monkeypatch):
    data_dir = copy_v12(tmp_path)
    pin = TEMPLATE['first_pin']
    assert refused(data_dir, pin, f'../vendor-links/{RUN}') == 'unsafe run ID'
    assert refused(data_dir, pin, '.hidden') == 'unsafe run ID'
    assert refused(data_dir, pin, 'absent') == 'detached pin differs'


def test_a_wrong_pin_is_checked_before_the_inventory_is_read(tmp_path, monkeypatch):
    data_dir = copy_v12(tmp_path)
    (bundle(data_dir) / 'outputs.json').write_text('{')
    assert refused(data_dir, TEMPLATE['first_pin']) == 'detached pin differs'


@pytest.mark.parametrize('name', [
    'vendor_links.parquet', 'vendor_link_pairs.parquet', 'inputs.json', 'report.json'])
def test_refuses_a_bundle_file_that_differs_from_its_inventory(tmp_path, name):
    data_dir = copy_v12(tmp_path)
    file = bundle(data_dir) / name
    file.write_bytes(file.read_bytes() + b'\n')
    assert refused(data_dir, TEMPLATE['first_pin']) == 'bundle file differs from its inventory'


@pytest.mark.parametrize('change', [
    pytest.param(lambda inventory: inventory.pop('report.json'), id='missing'),
    pytest.param(lambda inventory: inventory.update({'extra.json': {'sha256': '0'}}),
                 id='extra'),
])
def test_refuses_an_inventory_of_other_files(tmp_path, change):
    data_dir = copy_v12(tmp_path)
    outputs = bundle(data_dir) / 'outputs.json'
    inventory = json.loads(outputs.read_text())
    change(inventory)
    outputs.write_text(json.dumps(inventory))
    assert refused(data_dir, sha256(outputs)) == 'bundle inventory is malformed'


def test_refuses_a_bundle_json_file_that_is_not_json(tmp_path, monkeypatch):
    data_dir = copy_v12(tmp_path)
    pin = rewrite(data_dir, 'report.json', lambda file: file.write_text('{'))
    assert refused(data_dir, pin) == 'bundle file is malformed'


@pytest.mark.parametrize('role', ['subawards', 'extract'])
def test_refuses_a_changed_raw_file(tmp_path, role):
    data_dir = copy_v12(tmp_path)
    entries = raw_entries(data_dir)
    entry = entries['subawards'][1] if role == 'subawards' else entries['extract']
    file = data_dir / 'raw' / entry['path']
    file.write_bytes(file.read_bytes() + b'\0')
    assert refused(data_dir, TEMPLATE['first_pin']) == 'raw file differs from inputs.json'


def test_refuses_a_recorded_raw_hash_that_differs(tmp_path, monkeypatch):
    data_dir = copy_v12(tmp_path)
    pin = tamper_json(data_dir, 'inputs.json', put('raw', 'subawards', 2, 'sha256',
                                                   value='0' * 64))
    assert refused(data_dir, pin) == 'raw file differs from inputs.json'


def subaward_path(year: int, snapshot: str = '2026-11-20') -> str:
    return (f'usaspending/subcontracts/{snapshot}/FY{year}/'
            f'FY{year}_Contracts_Subawards_fixture.zip')


MALFORMED_INPUTS = [
    pytest.param(put('raw', 'subawards', 0, 'path', value='../' + subaward_path(2024)),
                 id='parent'),
    pytest.param(put('raw', 'subawards', 0, 'path', value='/' + subaward_path(2024)),
                 id='absolute'),
    pytest.param(put('raw', 'subawards', 0, 'path', value=subaward_path(2025)), id='repeated'),
    pytest.param(put('raw', 'subawards', 0, 'path', value=subaward_path(2023)), id='year'),
    pytest.param(put('raw', 'subawards', 0, 'path', value=subaward_path(2024, '2026-11-21')),
                 id='snapshots'),
    pytest.param(lambda inputs: inputs['raw']['subawards'].pop(), id='missing'),
    pytest.param(lambda inputs: inputs['raw']['subawards'].append(
        dict(inputs['raw']['subawards'][1])), id='four entries'),
    pytest.param(put('raw', 'extract', 'path', value='sam/entity-extract/x.ZIP'),
                 id='extract'),
    pytest.param(delete('raw', 'extract', 'sha256'), id='extract_hash'),
    pytest.param(put('raw', value=[]), id='raw'),
    pytest.param(put('codes', 'run_id', value='../codes'), id='codes_run'),
    pytest.param(delete('codes', 'outputs', 'naics_nodes.parquet'), id='codes_record'),
]


@pytest.mark.parametrize('change', MALFORMED_INPUTS)
def test_refuses_malformed_recorded_inputs(tmp_path, change):
    data_dir = copy_v12(tmp_path)
    pin = tamper_json(data_dir, 'inputs.json', change)
    assert refused(data_dir, pin) == 'recorded inputs are malformed'


def codes_directory(data_dir: Path) -> Path:
    inputs = json.loads((bundle(data_dir) / 'inputs.json').read_text())
    return data_dir / 'derived' / 'codes' / inputs['codes']['run_id']


def test_refuses_a_codes_bundle_that_the_pins_do_not_authenticate(tmp_path, monkeypatch):
    pinned = copy_v12(tmp_path / 'pinned')
    pin = tamper_json(pinned, 'inputs.json', put('codes', 'outputs_sha256', value='0' * 64))
    assert refused(pinned, pin) == 'codes pin differs'
    changed_outputs = copy_v12(tmp_path / 'outputs')
    outputs = codes_directory(changed_outputs) / 'outputs.json'
    outputs.write_bytes(outputs.read_bytes() + b'\n')
    assert refused(changed_outputs, TEMPLATE['first_pin']) == 'codes pin differs'
    nodes_reason = 'codes nodes differ from the recorded inventory'
    changed_nodes = copy_v12(tmp_path / 'nodes')
    nodes = codes_directory(changed_nodes) / 'naics_nodes.parquet'
    nodes.write_bytes(nodes.read_bytes() + b'\0')
    assert refused(changed_nodes, TEMPLATE['first_pin']) == nodes_reason
    record = copy_v12(tmp_path / 'record')
    pin = tamper_json(record, 'inputs.json', put('codes', 'outputs', 'naics_nodes.parquet',
                                                 'sha256', value='0' * 64))
    assert refused(record, pin) == nodes_reason


def test_national_industries_come_from_the_pinned_nodes(tmp_path, monkeypatch):
    data_dir = copy_v12(tmp_path)
    inputs = json.loads((bundle(data_dir) / 'inputs.json').read_text())
    nodes = reconcile.national_industries(data_dir, inputs)
    assert len(nodes) == 1012
    assert nodes['541511'] == 'naics:2022:national_industry:541511'
    # Only national industries: the five-digit industry 54151 is not one.
    assert '54151' not in nodes and '517311' not in nodes


def test_national_industries_filter_on_system_vintage_and_level(tmp_path):
    directory = tmp_path / 'derived' / 'codes' / 'codes_run'
    directory.mkdir(parents=True)
    nodes = directory / 'naics_nodes.parquet'
    pl.DataFrame({
        'node_id': ['naics:2022:national_industry:541511', 'naics:2017:national_industry:517311',
                    'naics:2022:industry:54151', 'soc:2022:national_industry:111111'],
        'system': ['naics', 'naics', 'naics', 'soc'],
        'vintage': [2022, 2017, 2022, 2022],
        'level': ['national_industry', 'national_industry', 'industry', 'national_industry'],
        'code': ['541511', '517311', '54151', '111111'],
        'title': ['a', 'b', 'c', 'd'],
    }).write_parquet(nodes)
    record = {'sha256': sha256(nodes), 'size': nodes.stat().st_size}
    outputs = directory / 'outputs.json'
    outputs.write_text(json.dumps({'naics_nodes.parquet': record}))
    inputs = {'codes': {'run_id': 'codes_run', 'outputs_sha256': sha256(outputs),
                        'outputs': {'naics_nodes.parquet': record}}}
    assert reconcile.national_industries(tmp_path, inputs) == {
        '541511': 'naics:2022:national_industry:541511'}


def test_a_malformed_code_on_a_read_firm_is_flagged(tmp_path, monkeypatch):
    # The build fails on such a firm, so a bundle beside such an extract cannot be equal.
    data_dir = copy_v12(tmp_path)

    def edit(text):
        lines = text.split('\r\n')
        for number, line in enumerate(lines):
            fields = line.split('|')
            if fields[0] == 'V12SUBAWC003':
                fields[32] = '54151X'
                lines[number] = '|'.join(fields)
        return '\r\n'.join(lines)

    pin = reseal_extract(data_dir, edit)
    status, result, _line = run_main(data_dir, pin)
    assert status == 1
    assert 'firms.no_malformed_read_code' in false_checks(result)
    assert result['counts']['malformed_read_codes'] == 1


# ---- direct tests: the value rules on small typed inputs

GOOD = 'ABCDEFGH1234'
OTHER = 'ZYXWVUTS9876'
ISO = '%Y-%m-%d'
UNUSABLE = ('uei_unusable', None, None, None)
INVALID = ('action_date_invalid', None, None, None)
OUTSIDE = ('outside_window', None, None, None)


@pytest.mark.parametrize(('prime', 'sub', 'action', 'expected'), [
    ('', OTHER, '2024-01-15', UNUSABLE),
    (GOOD, '', '2024-01-15', UNUSABLE),
    (GOOD.lower(), OTHER, '2024-01-15', UNUSABLE),
    (GOOD, OTHER.lower(), '2024-01-15', UNUSABLE),
    (GOOD, OTHER[:11], '2024-01-15', UNUSABLE),
    (GOOD + 'A', OTHER, '2024-01-15', UNUSABLE),
    (GOOD[:11] + '-', OTHER, '2024-01-15', UNUSABLE),
    (' ' + GOOD, OTHER, '2024-01-15', UNUSABLE),
    (GOOD, OTHER + ' ', '2024-01-15', UNUSABLE),
    (GOOD[:11] + '١', OTHER, '2024-01-15', UNUSABLE),
    ('', OTHER, 'not a date', UNUSABLE),
    (f' \t\n{GOOD}\r\x0b\x0c', f'\t{OTHER} ', '2024-01-15', ('usable', GOOD, OTHER, 2024)),
    ('0012345678AB', OTHER, '2024-01-15', ('usable', '0012345678AB', OTHER, 2024)),
    (GOOD, OTHER, '', INVALID),
    (GOOD, OTHER, '   ', INVALID),
    (GOOD, OTHER, '2024-02-30', INVALID),
    (GOOD, OTHER, '2024-2-3', INVALID),
    (GOOD, OTHER, '20240203', INVALID),
    (GOOD, OTHER, '2024/02/03', INVALID),
    (GOOD, OTHER, ' 2024-02-03\t', ('usable', GOOD, OTHER, 2024)),
    (GOOD, OTHER, '2023-09-30', OUTSIDE),
    (GOOD, OTHER, '2023-10-01', ('usable', GOOD, OTHER, 2024)),
    (GOOD, OTHER, '2024-09-30', ('usable', GOOD, OTHER, 2024)),
    (GOOD, OTHER, '2024-10-01', ('usable', GOOD, OTHER, 2025)),
    (GOOD, OTHER, '2024-12-31', ('usable', GOOD, OTHER, 2025)),
    (GOOD, OTHER, '2025-01-01', ('usable', GOOD, OTHER, 2025)),
    (GOOD, OTHER, '2026-09-30', ('usable', GOOD, OTHER, 2026)),
    (GOOD, OTHER, '2026-10-01', OUTSIDE),
    (GOOD, OTHER, '2030-05-05', OUTSIDE),
])
def test_report_status(prime, sub, action, expected):
    assert reconcile.classify_report(prime, sub, action, ISO) == expected


@pytest.mark.parametrize(('value', 'expected'), [
    ('', None), ('   ', None), ('1.234', None), ('1e5', None), ('1.', None), ('.5', None),
    ('+5', None), ('1,000.00', None), ('--1', None), ('1' * 37, None), ('12 .00', None),
    ('0.0١', None),
    ('-12.50', Decimal('-12.50')), (' 7\t', Decimal('7')), ('-0.5', Decimal('-0.5')),
    ('1' * 36 + '.99', Decimal('1' * 36 + '.99')),
])
def test_amount(value, expected):
    assert reconcile.parse_amount(value) == expected


@pytest.mark.parametrize(('prime_parent', 'sub_parent', 'expected'), [
    (None, GOOD, True),                         # the subcontractor's parent is the prime
    (OTHER, None, True),                        # the prime's parent is the subcontractor
    ('', GOOD, True),
    (OTHER, '', True),
    ('PARENTUEI001', 'PARENTUEI001', True),     # both parents present and equal
    (' PARENTUEI001', 'PARENTUEI001\t', True),  # parents are stripped
    ('PARENTUEI001', 'PARENTUEI002', False),    # different valid parents
    ('parentuei001', 'parentuei001', False),    # equal but malformed
    ('   ', '\t', False),                       # blank after stripping
    ('', '', False),
    (None, None, False),                        # both parent fields unmapped
    (GOOD, OTHER, False),                       # each firm is its own parent
    (GOOD.lower(), OTHER.lower(), False),
])
def test_group_conditions(prime_parent, sub_parent, expected):
    assert reconcile.group_shown(GOOD, OTHER, prime_parent, sub_parent) is expected


def test_dates_round_trip_through_the_format():
    assert reconcile.parse_date(' 20250115 ', '%Y%m%d') == date(2025, 1, 15)
    assert reconcile.parse_date('2025115', '%Y%m%d') is None
    assert reconcile.parse_date('20251332', '%Y%m%d') is None
    assert reconcile.parse_date('', '%Y%m%d') is None
    assert reconcile.parse_date('2025-01-15', '%Y%m%d') is None
    assert reconcile.fiscal_year(date(2025, 9, 30)) == 2025
    assert reconcile.fiscal_year(date(2025, 10, 1)) == 2026


REGISTRY = reconcile.SUBAWARD_HEADERS
LAYOUT_2025 = REGISTRY['years']['2025']
HEADER = LAYOUT_2025['header']


def record(**fields) -> list[str]:
    '''A full subaward row in the committed header order; every other cell is empty.'''
    row = [''] * len(HEADER)
    columns = LAYOUT_2025['columns']
    for field, value in ({'subaward_type': 'sub-contract'} | fields).items():
        row[HEADER.index(columns[field])] = value
    return row


def report(prime=GOOD, sub=OTHER, action='2025-03-01', amount='10.00', **fields) -> list[str]:
    return record(prime_uei=prime, sub_uei=sub, action_date=action, amount=amount, **fields)


def tally(*records, year=2025, registry=REGISTRY):
    return reconcile.tally_reports([(year, list(records))], registry)


def test_reports_are_tallied_by_pair_and_counted_by_status():
    result = tally(report(amount='10.00'), report(amount='10.00'),
                   report(action='2025-11-10', amount='bad'), report(amount=' -2.25 '),
                   report(prime=''), report(action='2025-02-30'), report(action='2026-10-01'),
                   report(prime=OTHER, sub=GOOD, action='2024-12-31'))
    assert result.by_status['2025'] == {'usable': 5, 'uei_unusable': 1,
                                        'action_date_invalid': 1, 'outside_window': 1}
    assert result.by_status['total'] == result.by_status['2025']
    pair = result.pairs[(GOOD, OTHER)]
    # Duplicates count: a pair counts once, but every report adds to its counts.
    assert (pair.n_reports, pair.by_year, pair.amount) == (4, [0, 3, 1], Decimal('17.75'))
    assert pair.intra_group is False
    back = result.pairs[(OTHER, GOOD)]
    assert (back.n_reports, back.by_year) == (1, [0, 1, 0])
    assert set(result.pairs) == {(GOOD, OTHER), (OTHER, GOOD)}


def test_amounts_sum_exactly():
    # Two amounts of 36 digits and two decimals, beyond the default 28-digit context.
    big = '9' * 36 + '.99'
    pair = tally(report(amount=big), report(amount=big), report(amount='0.01')).pairs[
        (GOOD, OTHER)]
    assert pair.amount == Decimal('1' + '9' * 36 + '.99')


def test_a_pair_whose_amounts_all_fail_sums_to_zero():
    pair = tally(report(amount=''), report(amount='1.234')).pairs[(GOOD, OTHER)]
    assert (pair.n_reports, pair.amount) == (2, Decimal(0))


def test_one_report_of_a_pair_is_enough_for_a_group():
    result = tally(report(), report(sub_parent_uei=GOOD), report())
    assert result.pairs[(GOOD, OTHER)].intra_group is True
    # A group shown on an unusable report does not count.
    result = tally(report(), report(action='2023-09-30', prime_parent_uei=OTHER))
    assert result.pairs[(GOOD, OTHER)].intra_group is False


def test_an_unmapped_parent_field_disables_only_its_conditions():
    registry = copy.deepcopy(REGISTRY)
    registry['years']['2025']['columns']['prime_parent_uei'] = None
    shown = tally(report(sub_parent_uei=GOOD), registry=registry).pairs[(GOOD, OTHER)]
    assert shown.intra_group is True
    hidden = tally(report(prime_parent_uei=OTHER), registry=registry).pairs[(GOOD, OTHER)]
    assert hidden.intra_group is False
    equal = tally(report(prime_parent_uei='PARENTUEI001', sub_parent_uei='PARENTUEI001'),
                  registry=registry).pairs[(GOOD, OTHER)]
    assert equal.intra_group is False


@pytest.mark.parametrize('kind', [' sub-contract', 'sub-contract ', 'Sub-Contract', 'sub-grant',
                                  ''])
def test_any_other_subaward_type_is_refused(kind):
    with pytest.raises(reconcile.Refused, match='^subaward type differs$'):
        tally(report(), report(subaward_type=kind))
    # The type is checked on an unusable report too.
    with pytest.raises(reconcile.Refused, match='^subaward type differs$'):
        tally(report(prime='', subaward_type=kind))


def test_reports_count_under_their_own_fiscal_year_and_file_year():
    result = reconcile.tally_reports([
        (2024, [report(action='2024-03-01'), report(prime='')]),
        (2026, [report(action='2025-09-15'), report(action='2026-03-01')])], REGISTRY)
    assert result.by_status['2024'] == {'usable': 1, 'uei_unusable': 1}
    assert result.by_status['2026'] == {'usable': 2}
    assert result.by_status['total'] == {'usable': 3, 'uei_unusable': 1}
    assert result.pairs[(GOOD, OTHER)].by_year == [1, 1, 1]


MEMBER = V12_MEMBER


def csv_bytes(rows, header=HEADER, bom=False) -> bytes:
    text = io.StringIO()
    csv.writer(text, lineterminator='\r\n').writerows([header, *rows])
    return (codecs.BOM_UTF8 if bom else b'') + text.getvalue().encode('utf-8')


def write_zip(file: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(file, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return file


def records_of(file: Path) -> list[list[str]]:
    return list(reconcile.subaward_records(file, LAYOUT_2025))


def test_every_csv_member_is_read_and_a_bom_is_removed(tmp_path):
    second = MEMBER.replace('_1.csv', '_2.csv')
    file = write_zip(tmp_path / 'a.zip', {MEMBER: csv_bytes([report()], bom=True),
                                          second: csv_bytes([report(), report(prime='')])})
    assert records_of(file) == [report(), report(), report(prime='')]


def test_quoted_values_and_a_long_field_are_read(tmp_path):
    row = report()
    row[HEADER.index('subaward_description')] = 'a, "quoted"\r\nline ' + 'x' * 200_000
    file = write_zip(tmp_path / 'a.zip', {MEMBER: csv_bytes([row])})
    # A small limit shows that the reader raises the limit and then puts it back.
    previous = csv.field_size_limit(1000)
    try:
        assert records_of(file) == [row]
        assert csv.field_size_limit() == 1000
    finally:
        csv.field_size_limit(previous)


@pytest.mark.parametrize(('members', 'reason'), [
    pytest.param({MEMBER: csv_bytes([report()]), 'readme.txt': b'x'},
                 'raw member is unexpected', id='stray member'),
    pytest.param({MEMBER.replace('.csv', '.CSV'): csv_bytes([report()])},
                 'raw member is unexpected', id='member case'),
    pytest.param({'x' + MEMBER: csv_bytes([report()])},
                 'raw member is unexpected', id='member prefix'),
    pytest.param({MEMBER + '.bak': csv_bytes([report()])},
                 'raw member is unexpected', id='member suffix'),
    pytest.param({MEMBER: csv_bytes([report()], header=[HEADER[1], HEADER[0], *HEADER[2:]])},
                 'subaward header differs', id='reordered header'),
    pytest.param({MEMBER: csv_bytes([report()], header=[*HEADER[:-1], 'renamed'])},
                 'subaward header differs', id='header'),
    pytest.param({MEMBER: csv_bytes([report()], header=HEADER[:-1])},
                 'subaward header differs', id='short header'),
    pytest.param({MEMBER: b''}, 'subaward header differs', id='empty member'),
    pytest.param({MEMBER: csv_bytes([report()[:-1]])},
                 'subaward record is unreadable', id='short record'),
    pytest.param({MEMBER: csv_bytes([[*report(), '']])},
                 'subaward record is unreadable', id='long record'),
    pytest.param({MEMBER: csv_bytes([]) + b'\r\n'},
                 'subaward record is unreadable', id='blank line'),
    pytest.param({MEMBER: csv_bytes([]) + b'"a"b' + b',' * (len(HEADER) - 1) + b'\r\n'},
                 'subaward record is unreadable', id='bad quoting'),
    pytest.param({MEMBER: csv_bytes([report(amount='\x00')]).replace(b'\x00', b'\xff')},
                 'subaward record is unreadable', id='not UTF-8'),
])
def test_unreadable_subaward_members_are_refused(tmp_path, members, reason):
    file = write_zip(tmp_path / 'a.zip', members)
    with pytest.raises(reconcile.Refused, match=f'^{reason}$'):
        records_of(file)


def test_a_file_that_is_no_zip_is_refused(tmp_path):
    file = tmp_path / 'a.zip'
    file.write_bytes(b'not a zip')
    with pytest.raises(reconcile.Refused, match='^subaward record is unreadable$'):
        records_of(file)
    with pytest.raises(reconcile.Refused, match='^extract line is unreadable$'):
        list(reconcile.extract_text(file, reconcile.EXTRACT_LAYOUT))


# ---- direct tests: the extract reader and the firm rules

LAYOUT = reconcile.EXTRACT_LAYOUT
BOF = LAYOUT['bof_prefix'] + '20261102 0000003 0000009\r\n'
EOF = LAYOUT['eof_prefix'] + '20261102 0000003 0000009'
NODES = {'541511': 'naics:2022:national_industry:541511',
         '541512': 'naics:2022:national_industry:541512'}


def extract_line(uei=GOOD, code='541511', update='20250115', evs='SAM', count=None,
                 end='!end', registration='A') -> str:
    '''A data line with its CRLF: the given fields at their registered positions.'''
    values = [''] * (LAYOUT['field_count'] if count is None else count)
    values[-1] = end
    for field, value in (('uei', uei), ('primary_naics', code), ('last_update_date', update),
                         ('evs_source', evs), ('registration_status', registration)):
        index = LAYOUT['positions'][field] - 1
        if index < len(values):
            values[index] = value
    return LAYOUT['delimiter'].join(values) + '\r\n'


def read_extract(*lines, wanted=frozenset({GOOD, OTHER}), layout=LAYOUT):
    return reconcile.tally_extract([BOF, *lines, EOF], layout, set(wanted))


def firm(*lines, uei=GOOD, layout=LAYOUT):
    result = read_extract(*lines, layout=layout)
    return reconcile.classify_firm(result.firms.get(uei), NODES)


@pytest.mark.parametrize('count', [141, 143, 155, 1])
def test_a_line_with_the_wrong_field_count_is_skipped_and_counted(count):
    result = read_extract(extract_line(count=count, update=''), extract_line(OTHER))
    assert result.unreadable_lines == 1
    assert result.unreadable_ueis == {GOOD}
    assert GOOD not in result.firms
    assert set(result.firms) == {OTHER}
    # A skipped line is no row: its blank date is not counted.
    assert result.invalid_date_rows == 0


def test_a_skipped_line_of_an_unwanted_uei_is_counted_only():
    result = read_extract(extract_line('NOTWANTED001', count=143),
                          extract_line(f' {GOOD} ', count=12))
    assert (result.unreadable_lines, result.unreadable_ueis) == (2, {GOOD})


def test_framing_lines_are_checked_and_their_counts_are_not_record_counts():
    # The framing counts say 3 and 9 records; the member holds 2 data lines.
    result = read_extract(extract_line(), extract_line(OTHER))
    assert set(result.firms) == {GOOD, OTHER}
    assert result.unreadable_lines == 0


@pytest.mark.parametrize('lines', [
    pytest.param([], id='empty'),
    pytest.param([BOF], id='no EOF'),
    pytest.param([BOF, extract_line()], id='data last'),
    pytest.param([extract_line(), EOF], id='no BOF'),
    pytest.param(['BOF PUBLIC V3 00000000 20261102\r\n', EOF], id='other BOF'),
    pytest.param([BOF, extract_line(), 'EOF FIXTURE V2 00000000 20261102'], id='other EOF'),
    pytest.param(['﻿' + BOF, EOF], id='BOM'),
])
def test_bad_framing_is_refused(lines):
    with pytest.raises(reconcile.Refused, match='^extract framing differs$'):
        list(reconcile.data_lines(lines, LAYOUT))


def test_framing_alone_is_an_empty_extract():
    assert list(reconcile.data_lines([BOF, EOF], LAYOUT)) == []
    assert list(reconcile.data_lines([BOF, 'a\r\n', EOF], LAYOUT)) == ['a']
    # Only the CRLF line end is removed; a CR or LF before it stays in the last field.
    assert list(reconcile.data_lines([BOF, 'a\r\r\n', 'b\n\r\n', EOF], LAYOUT)) == [
        'a\r', 'b\n']


@pytest.mark.parametrize('end', ['', '!END', '!end ', 'end'])
def test_a_line_with_the_right_count_but_no_record_end_is_refused(end):
    with pytest.raises(reconcile.Refused, match='^extract record end differs$'):
        read_extract(extract_line(end=end))


def test_only_crlf_ends_an_extract_line(tmp_path):
    line = extract_line().replace('SAM', 'S\nA\rM')
    file = write_zip(tmp_path / 'e.zip', {V12_EXTRACT_MEMBER: (BOF + line + EOF).encode()})
    lines = list(reconcile.extract_text(file, LAYOUT))
    assert lines == [BOF, line, EOF]
    assert reconcile.tally_extract(lines, LAYOUT, {GOOD}).unreadable_lines == 0


@pytest.mark.parametrize(('members', 'reason'), [
    pytest.param({V12_EXTRACT_MEMBER: (BOF + EOF).encode(), 'other.dat': b''},
                 'raw member is unexpected', id='two members'),
    pytest.param({'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261102.dat': (BOF + EOF).encode()},
                 'raw member is unexpected', id='name'),
    pytest.param({V12_EXTRACT_MEMBER + '.bak': (BOF + EOF).encode()},
                 'raw member is unexpected', id='member suffix'),
    pytest.param({V12_EXTRACT_MEMBER: (BOF + 'a\xffb\r\n').encode('latin-1') + EOF.encode()},
                 'extract line is unreadable', id='not UTF-8'),
])
def test_unreadable_extract_members_are_refused(tmp_path, members, reason):
    file = write_zip(tmp_path / 'e.zip', members)
    with pytest.raises(reconcile.Refused, match=f'^{reason}$'):
        list(reconcile.extract_text(file, LAYOUT))


@pytest.mark.parametrize(('lines', 'expected'), [
    pytest.param([], ('not_in_sam', None), id='no row'),
    pytest.param([extract_line(OTHER)], ('not_in_sam', None), id='other UEI'),
    pytest.param([extract_line(f' {GOOD}\t')], ('eligible', NODES['541511']), id='padded UEI'),
    pytest.param([extract_line(update='20220403')], ('dnb_era_record', None), id='day before'),
    pytest.param([extract_line(update='20220404')], ('eligible', NODES['541511']),
                 id='cutoff day'),
    pytest.param([extract_line(update='')], ('dnb_era_record', None), id='blank date'),
    pytest.param([extract_line(update='20251332')], ('dnb_era_record', None), id='bad date'),
    pytest.param([extract_line(update=' 20250115 ')], ('eligible', NODES['541511']),
                 id='padded date'),
    pytest.param([extract_line(evs='D&B')], ('dnb_era_record', None), id='EVS D&B'),
    pytest.param([extract_line(evs=' D&B\t')], ('dnb_era_record', None), id='EVS padded'),
    pytest.param([extract_line(evs='d&b')], ('eligible', NODES['541511']), id='EVS case'),
    pytest.param([extract_line(), extract_line(update='20200101')], ('dnb_era_record', None),
                 id='one old row'),
    pytest.param([extract_line(update='20200101'), extract_line()], ('dnb_era_record', None),
                 id='old row first'),
    pytest.param([extract_line(registration='E')], ('eligible', NODES['541511']),
                 id='expired only'),
    pytest.param([extract_line(), extract_line(evs='D&B')], ('dnb_era_record', None),
                 id='one D&B row'),
    pytest.param([extract_line(code='')], ('naics_missing', None), id='blank code'),
    pytest.param([extract_line(code=' \t ')], ('naics_missing', None), id='spaces code'),
    pytest.param([extract_line(code=''), extract_line(code='')], ('naics_missing', None),
                 id='two blank rows'),
    pytest.param([extract_line(), extract_line(code='541512')], ('naics_conflict', None),
                 id='conflict'),
    pytest.param([extract_line(code=''), extract_line(code='541512')],
                 ('eligible', NODES['541512']), id='mixed blank'),
    pytest.param([extract_line(), extract_line(code=' 541511 ')],
                 ('eligible', NODES['541511']), id='agreeing rows'),
    pytest.param([extract_line(code='517311')], ('naics_not_2022', None), id='not 2022'),
    pytest.param([extract_line(code='517311'), extract_line(code='541511')],
                 ('naics_conflict', None), id='conflict before not 2022'),
    pytest.param([extract_line(code='54151A')], ('malformed_code', None), id='malformed'),
    pytest.param([extract_line(code='5415111')], ('malformed_code', None), id='seven digits'),
    pytest.param([extract_line(code='54151')], ('malformed_code', None), id='five digits'),
    pytest.param([extract_line(code='٥٤١٥١١')],
                 ('malformed_code', None), id='Arabic-Indic digits'),
    pytest.param([extract_line(code='54151A'), extract_line(code='')],
                 ('malformed_code', None), id='malformed beside blank'),
    pytest.param([extract_line(code='54151A', update='20200101')], ('dnb_era_record', None),
                 id='malformed on a D&B-era firm'),
    pytest.param([extract_line(code='54151A'), extract_line(evs='D&B')],
                 ('dnb_era_record', None), id='malformed beside a D&B row'),
])
def test_firm_status(lines, expected):
    assert firm(*lines) == expected


def test_the_evs_rule_applies_only_when_the_layout_maps_the_field():
    layout = copy.deepcopy(LAYOUT)
    del layout['positions']['evs_source']
    assert firm(extract_line(evs='D&B'), layout=layout) == ('eligible', NODES['541511'])


def test_invalid_dates_are_counted_on_every_readable_row():
    result = read_extract(extract_line(update=''), extract_line('NOTWANTED001', update='2025'),
                          extract_line(OTHER), extract_line('NOTWANTED002', count=3, update=''))
    assert result.invalid_date_rows == 2
    # Pass 2 keeps rows only for the wanted UEIs.
    assert set(result.firms) == {GOOD, OTHER}
    assert result.firms[GOOD].date_invalid is True
    assert result.firms[OTHER].date_invalid is False


@pytest.mark.parametrize(('prime', 'sub', 'intra', 'statuses', 'expected'), [
    (GOOD, GOOD, True, ('eligible', 'eligible'), 'self_link'),
    (GOOD, GOOD, False, ('not_in_sam', 'not_in_sam'), 'self_link'),
    (GOOD, OTHER, True, ('not_in_sam', 'eligible'), 'intra_group'),
    (GOOD, OTHER, False, ('dnb_era_record', 'not_in_sam'), 'prime_ineligible'),
    (GOOD, OTHER, False, ('eligible', 'naics_conflict'), 'sub_ineligible'),
    (GOOD, OTHER, False, ('eligible', 'eligible'), 'eligible'),
])
def test_pair_status(prime, sub, intra, statuses, expected):
    assert reconcile.classify_pair(prime, sub, intra, *statuses) == expected


# ---- direct tests: the estimates on typed pair rows

def pair(prime, sub, prime_node, sub_node, *, intra=False, years=(1, 0, 0), amount='1.00'):
    '''A pair row in the pair table's column order. A null node makes that firm ineligible.'''
    prime_status = 'eligible' if prime_node else 'not_in_sam'
    sub_status = 'eligible' if sub_node else 'not_in_sam'
    status = reconcile.classify_pair(prime, sub, intra, prime_status, sub_status)
    return (prime, sub, sum(years), *years, prime_status, sub_status, prime_node, sub_node,
            intra, status, Decimal(amount))


def run_estimates(*rows):
    return reconcile.estimates({(row[0], row[1]): row for row in rows}, 'U')


def test_the_sensitivity_admits_only_group_pairs_of_two_eligible_firms():
    result = run_estimates(
        pair('PRIMEA000001', 'SUBA00000001', 'd1', 's1'),
        pair('PRIMEB000002', 'SUBA00000001', 'd2', 's1', intra=True),
        pair('PRIMEC000003', 'SUBB00000002', None, 's1', intra=True),
        pair('SELF00000004', 'SELF00000004', 's1', 's1', intra=True))
    assert set(result['support']) == {('s1', 'd1')}
    assert result['summary'] == {
        'n_pairs': {'eligible': 1, 'including_intra_group': 2},
        'n_buyers': {'eligible': 1, 'including_intra_group': 2},
        'n_suppliers': {'eligible': 1, 'including_intra_group': 1},
        'cells_only_intra_group': 1}
    # The buyer industry d2 is seen only through a group pair, so it has no marginal row.
    assert set(result['marginals']) == {('s1',), ('d1',)}
    assert result['marginals'][('s1',)] == ('s1', 1, 0, 1, 0, 0, 0, 1, 0)


def test_support_counts_shares_and_labels():
    result = run_estimates(
        pair('PRIMEA000001', 'SUBA00000001', 'd', 's', years=(1, 2, 0), amount='5.50'),
        pair('PRIMEA000001', 'SUBB00000002', 'd', 's', years=(0, 0, 1), amount='-1.25'),
        pair('PRIMEB000002', 'SUBA00000001', 'd', 's', years=(0, 1, 0)),
        pair('PRIMEC000003', 'SUBC00000003', 'd', 't'),
        pair('PRIMED000004', 'SUBD00000004', 'e', 's', intra=True),
        pair('PRIMEE000005', 'SUBA00000001', None, 's'),
        pair('PRIMEA000001', 'SUBE00000005', 'd', None))
    assert result['support'][('s', 'd')] == (
        's', 'd', 2, 2, 3, 1, 2, 1, 2, 2, 3, Decimal('5.25'), 5)
    assert result['support'][('t', 'd')][2:5] == (1, 1, 1)
    targets = result['targets']
    supplier = targets[('s', 'd', 'supplier_share')]
    assert supplier[7:12] == (1.0, None, 'none', 2, 2.0)
    assert supplier[15] == ['size_gate_pending']
    buyer = targets[('s', 'd', 'buyer_share')]
    assert buyer[7] == 2 / 3
    assert buyer[15] == ['size_gate_pending']
    assert targets[('t', 'd', 'buyer_share')][7] == 1 / 3
    assert len(targets) == 4
    # Supplier s: SUBA and SUBB; SUBA has a prime_ineligible pair. Buyer d: PRIMEA has a
    # sub_ineligible pair. Supplier s's group pair adds SUBD under the sensitivity only.
    assert result['marginals'][('s',)] == ('s', 2, 0, 3, 0, 1, 0, 3, 0)
    assert result['marginals'][('d',)] == ('d', 0, 3, 0, 4, 0, 1, 0, 3)
    assert result['summary']['cells_only_intra_group'] == 1


def test_the_label_follows_each_measure_s_own_count():
    both = run_estimates(
        pair('PRIMEA000001', 'SUBA00000001', 'd', 's'),
        pair('PRIMEB000002', 'SUBB00000002', 'd', 's', intra=True))
    label = 'numerator:intra_group_sensitivity:true'
    assert both['targets'][('s', 'd', 'supplier_share')][15] == [label, 'size_gate_pending']
    assert both['targets'][('s', 'd', 'buyer_share')][15] == [label, 'size_gate_pending']
    one_side = run_estimates(
        pair('PRIMEA000001', 'SUBA00000001', 'd', 's'),
        pair('PRIMEA000001', 'SUBB00000002', 'd', 's', intra=True))
    assert one_side['targets'][('s', 'd', 'supplier_share')][15] == [label, 'size_gate_pending']
    assert one_side['targets'][('s', 'd', 'buyer_share')][15] == ['size_gate_pending']


def test_partial_counts_need_exactly_the_excluding_status():
    # SUBA's other pair is intra_group with an ineligible prime, not prime_ineligible.
    result = run_estimates(
        pair('PRIMEA000001', 'SUBA00000001', 'd', 's'),
        pair('PRIMEB000002', 'SUBA00000001', None, 's', intra=True),
        pair('PRIMEA000001', 'SUBB00000002', 'd', None, intra=True))
    assert result['marginals'][('s',)][5] == 0
    assert result['marginals'][('d',)][6] == 0


def test_the_diagonal_cell_is_emitted():
    result = run_estimates(pair('PRIMEA000001', 'SUBA00000001', 'x', 'x'))
    assert set(result['targets']) == {('x', 'x', 'supplier_share'), ('x', 'x', 'buyer_share')}


def test_a_zero_denominator_share_is_null():
    assert reconcile.share(0, 0) is None
    assert reconcile.share(1, 4) == 0.25
