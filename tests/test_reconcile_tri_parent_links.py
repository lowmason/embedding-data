'''The independent TRI parent-link reconciler, on the V12 fixture bundle and on small CSV files.

The script is loaded by path. The V12 chain gives a real bundle. Each tampered copy changes one
recomputed quantity, gets a fresh detached pin and must make its own checks unequal and no
other. Each refusal case must print only its fixed reason and exit 2.
'''

import ast
import contextlib
import functools
import importlib.util
import io
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest
from tri_fixtures import (
    V12_DATE,
    V12_DNB,
    production_layout,
    run_tri_v12,
    seed_codes_bundle,
    tri_row,
    v12_rows,
    write_tri_csv,
)

from embedding_data import manifest, target_io, tri_bundle, tri_layout, tri_raw
from embedding_data.tri_bundle import FILES

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'reconcile_tri_parent_links.py'
BUNDLES = Path('derived/epa_tri/parent-links')
NODE = 'naics:2022:national_industry:'
NODES = {code: NODE + code
         for code in ('324110', '325110', '325120', '325199', '325211', '331110')}
DATE = '2025-11-05'
CHECKS = ('facility_years', 'eligibility', 'marginals', 'support', 'targets',
          'parent_industries', 'n_owners', 'owners_by_year', 'rows_by_form_type',
          'facility_years_by_reason', 'year_counts', 'sensitivity_cells', 'owner_key_changes',
          'partial_owners')
DNB_LABEL = 'numerator:dnb_key_sensitivity:true'
FEDERAL_LABEL = 'numerator:federal_sensitivity:true'


@functools.cache
def load_script():
    assert SCRIPT.is_file(), 'independent reconciler is missing'
    spec = importlib.util.spec_from_file_location('reconcile_tri_parent_links', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Script:
    '''Loads the script on first use, so a missing script fails each test, not collection.'''

    def __getattr__(self, name):
        return getattr(load_script(), name)


reconcile = _Script()


def run_text(result, run_id=None, pin=None, data_dir=None):
    '''Run the reconciler in process and return its status and its whole standard output.'''
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        status = reconcile.main([
            '--data-dir', str(data_dir or result['data_dir']),
            '--run', run_id or result['first'].name,
            '--outputs-sha256', pin or result['first_pin']])
    return status, out.getvalue()


def run(result, run_id=None, pin=None, data_dir=None):
    '''Run the reconciler in process and return its status and its single JSON line, parsed.'''
    status, text = run_text(result, run_id, pin, data_dir)
    lines = text.splitlines()
    assert len(lines) == 1
    return status, json.loads(lines[0])


def repin(directory: Path) -> str:
    '''Rewrite the bundle inventory of `directory` and return its new detached pin.'''
    target_io.write_json(directory / 'outputs.json', target_io.inventory(directory, list(FILES)))
    return manifest.sha256_file(directory / 'outputs.json')


def repinned_copy(result, name, change):
    '''A copy of the first bundle under a new run name, changed, with a fresh detached pin.'''
    directory = result['first'].parent / name
    shutil.copytree(result['first'], directory)
    change(directory)
    return directory.name, repin(directory)


@pytest.fixture(scope='module')
def chain(tmp_path_factory):
    '''One V12 chain for the module. Its external-access guards end when it returns.'''
    with pytest.MonkeyPatch.context() as patch:
        return run_tri_v12(tmp_path_factory.mktemp('reconcile_tri'), patch)


# Plan tests.

def test_reconciler_layout_equals_the_committed_layout():
    assert reconcile.LAYOUT == tri_layout.layouts_json(tri_layout.load_layouts())['years']


def test_reconciler_imports_no_embedding_data_module():
    tree = ast.parse(SCRIPT.read_text())
    assert not [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                and 'embedding_data' in ast.unparse(n)]


def test_reconciler_reports_equal_on_the_v12_bundle(tmp_path, monkeypatch):
    result = run_tri_v12(tmp_path, monkeypatch)
    status, line = run(result)
    assert status == 0
    assert line['equal'] is True
    assert line['refused'] is False


def test_reconciler_detects_a_changed_count(tmp_path, monkeypatch):
    result = run_tri_v12(tmp_path, monkeypatch)

    def add_one(directory):
        file = directory / 'tri_parent_link_marginals.parquet'
        frame = pl.read_parquet(file)
        frame.with_columns(
            pl.when(pl.int_range(pl.len()).eq(0)).then(pl.col('n_owners').add(1))
            .otherwise(pl.col('n_owners')).cast(frame.schema['n_owners']).alias('n_owners')
        ).write_parquet(file)

    run_id, pin = repinned_copy(result, 'changed_count', add_one)
    status, line = run(result, run_id, pin)
    assert status == 1
    assert line['equal'] is False
    assert line['marginals_equal'] is False


def test_reconciler_refuses_a_wrong_pin(tmp_path, monkeypatch):
    result = run_tri_v12(tmp_path, monkeypatch)
    status, line = run(result, pin='0' * 64)
    assert status == 2
    assert line['refused'] is True
    assert line['equal'] is False


# The whole V12 bundle.

def unequal_checks(line: dict) -> set[str]:
    '''The checks that the line reports unequal, once it reports exactly the expected checks.'''
    assert {key for key in line if key.endswith('_equal')} == {name + '_equal' for name in CHECKS}
    return {name for name in CHECKS if line[name + '_equal'] is not True}


def test_every_check_is_equal_on_the_v12_bundle(chain):
    status, line = run(chain)
    assert status == 0
    assert unequal_checks(line) == set()
    assert line['n_owners'] == {'dnb': 9, 'federal': 8, 'headline': 8}
    assert line['rows'] == {'facility_years': 21, 'marginals': 8, 'parent_industries': 12,
                            'support': 8, 'targets': 8}
    assert {key: value for key, value in line.items() if key.endswith('_differing')} == {
        'eligibility_differing': 0, 'facility_years_differing': 0, 'marginals_differing': 0,
        'parent_industries_differing': 0, 'support_differing': 0, 'targets_differing': 0}


def test_the_second_v12_bundle_is_equal_too(chain):
    status, line = run(chain, chain['second'].name, chain['second_pin'])
    assert status == 0
    assert line['equal'] is True


def test_the_script_runs_as_a_program_with_each_exit_status(chain):
    def program(run_id, pin):
        command = [sys.executable, str(SCRIPT), '--data-dir', str(chain['data_dir']),
                   '--run', run_id, '--outputs-sha256', pin]
        return subprocess.run(command, capture_output=True, text=True, check=False)

    equal = program(chain['first'].name, chain['first_pin'])
    assert (equal.returncode, equal.stderr) == (0, '')
    assert json.loads(equal.stdout)['equal'] is True
    run_id, pin = repinned_copy(chain, 'program_unequal', cell(
        'tri_parent_link_support', 'j_owners', lambda value: value + 1))
    unequal = program(run_id, pin)
    assert (unequal.returncode, unequal.stderr) == (1, '')
    refused = program(chain['first'].name, '0' * 64)
    assert (refused.returncode, refused.stderr) == (2, '')
    assert json.loads(refused.stdout) == {'equal': False, 'reason': 'detached pin differs',
                                          'refused': True}


def test_reconciler_imports_only_the_standard_library_and_polars():
    tree = ast.parse(SCRIPT.read_text())
    modules = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
               for alias in node.names}
    modules |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert {name.split('.')[0] for name in modules} - set(sys.stdlib_module_names) == {'polars'}


def test_loading_the_script_imports_no_embedding_data_module():
    code = ('import importlib.util, json, sys\n'
            f'spec = importlib.util.spec_from_file_location("reconcile", {str(SCRIPT)!r})\n'
            'spec.loader.exec_module(importlib.util.module_from_spec(spec))\n'
            'print(json.dumps(sorted(name for name in sys.modules\n'
            '                        if name.startswith("embedding_data"))))\n')
    done = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
                          check=True)
    assert json.loads(done.stdout) == []


def test_the_output_line_holds_no_name_trifd_or_dnb_number(chain):
    secrets = set(V12_DNB)
    for year, rows in v12_rows().items():
        columns = production_layout(year).columns
        for field in ('trifd', 'parent_name', 'standardized_parent',
                      'standardized_foreign_parent'):
            if columns[field] is not None:
                secrets |= {row[columns[field]] for row in rows} - {'', 'NA'}
    assert {'T101', 'Alder Holdings', 'Birch Holding SA', V12_DNB[0]} <= secrets
    run_id, pin = repinned_copy(chain, 'private_unequal', cell(
        'tri_facility_years', 'parent_names', lambda value: [*value, 'Zz']))
    texts = [run_text(chain)[1], run_text(chain, run_id, pin)[1],
             run_text(chain, pin='0' * 64)[1]]
    for text in texts:
        assert not [secret for secret in secrets if secret in text]


def test_an_unexpected_error_prints_a_fixed_reason_and_no_text(chain, monkeypatch):
    def boom(*args, **kwargs):
        raise ValueError('T101 Alder Holdings ' + V12_DNB[0])

    monkeypatch.setattr(load_script(), 'recompute', boom)
    status, text = run_text(chain)
    assert status == 2
    assert json.loads(text) == {'equal': False, 'reason': 'unexpected', 'refused': True}
    assert 'T101' not in text and V12_DNB[0] not in text


def test_select_nodes_reads_the_national_industries_of_the_cited_codes_bundle(chain):
    inputs = json.loads((chain['first'] / 'inputs.json').read_text())
    nodes = reconcile.select_nodes(chain['data_dir'], inputs)
    assert len(nodes) == 1012
    assert all(node == NODE + code and len(code) == 6 for code, node in nodes.items())
    assert '32511' not in nodes
    assert nodes['325110'] == NODE + '325110'


# Tampered copies: each recomputed quantity is compared.

FY, MARGINALS, SUPPORT = ('tri_facility_years', 'tri_parent_link_marginals',
                          'tri_parent_link_support')
TARGETS, INDUSTRIES = 'tri_parent_links', 'tri_parent_industries'


def plus_one(value):
    return value + 1


def cell(table, column, change, row=0):
    '''A change that replaces one cell of a bundle table and keeps the table's schema.'''
    def apply(directory):
        file = directory / f'{table}.parquet'
        frame = pl.read_parquet(file)
        rows = frame.to_dicts()
        rows[row][column] = change(rows[row][column])
        pl.DataFrame(rows, schema=frame.schema).write_parquet(file)
    return apply


def whole(table, change):
    '''A change that replaces a whole bundle table with `change(table)`.'''
    def apply(directory):
        file = directory / f'{table}.parquet'
        change(pl.read_parquet(file)).write_parquet(file)
    return apply


def in_report(*path, change=plus_one):
    '''A change that replaces one value of `report.json`, found by its key path.'''
    def apply(directory):
        file = directory / 'report.json'
        report = json.loads(file.read_text())
        *parents, last = path
        holder = report
        for key in parents:
            holder = holder[key]
        holder[last] = change(holder[last])
        target_io.write_json(file, report)
    return apply


def report_change(change):
    def apply(directory):
        file = directory / 'report.json'
        report = json.loads(file.read_text())
        change(report)
        target_io.write_json(file, report)
    return apply


TAMPERED = {
    # The facility-year reduction.
    'fy_n_forms': (cell(FY, 'n_forms', plus_one), {'facility_years'}),
    'fy_n_form_r': (cell(FY, 'n_form_r', plus_one), {'facility_years'}),
    'fy_n_form_a': (cell(FY, 'n_form_a', plus_one), {'facility_years'}),
    'fy_primary': (cell(FY, 'primary_naics_values', lambda v: [*v, '325120']),
                   {'facility_years'}),
    'fy_other': (cell(FY, 'other_naics_values', lambda v: [*v, '325120']), {'facility_years'}),
    'fy_parents': (cell(FY, 'parent_names', lambda v: [*v, 'Zz']), {'facility_years'}),
    'fy_foreign': (cell(FY, 'foreign_parent_names', lambda v: [*v, 'Zz']), {'facility_years'}),
    'fy_federal_values': (cell(FY, 'federal_values', lambda v: ['YES']), {'facility_years'}),
    'fy_state_values': (cell(FY, 'state_values', lambda v: ['OK']), {'facility_years'}),
    'fy_mixed_blank': (cell(FY, 'flag_parent_mixed_blank', lambda v: not v),
                       {'facility_years'}),
    'fy_trifd': (cell(FY, 'trifd', lambda v: v + 'X'), {'facility_years', 'eligibility'}),
    'fy_year': (cell(FY, 'reporting_year', plus_one), {'facility_years', 'eligibility'}),
    # Eligibility.
    'fy_node': (cell(FY, 'naics_2022_node_id', lambda v: None), {'eligibility'}),
    'fy_owner_key': (cell(FY, 'owner_key', lambda v: 'facility:T101'), {'eligibility'}),
    'fy_exclusion_reason': (cell(FY, 'exclusion_reason', lambda v: 'federal'),
                            {'eligibility'}),
    # Order, row counts and schemas.
    'fy_order': (whole(FY, lambda f: f.reverse()), {'facility_years', 'eligibility'}),
    'fy_missing_row': (whole(FY, lambda f: f.head(-1)), {'facility_years', 'eligibility'}),
    'fy_schema': (whole(FY, lambda f: f.with_columns(pl.col('n_forms').cast(pl.Int64))),
                  {'facility_years'}),
    'marginals_order': (whole(MARGINALS, lambda f: f.reverse()), {'marginals'}),
    'marginals_missing_row': (whole(MARGINALS, lambda f: f.head(-1)), {'marginals'}),
    'marginals_schema': (whole(MARGINALS, lambda f: f.with_columns(
        pl.col('n_owners').cast(pl.Int64))), {'marginals'}),
    'marginals_column_order': (whole(MARGINALS, lambda f: f.select(reversed(f.columns))),
                               {'marginals'}),
    'support_order': (whole(SUPPORT, lambda f: f.reverse()), {'support'}),
    'support_extra_row': (whole(SUPPORT, lambda f: pl.concat([f, f.tail(1)])), {'support'}),
    'support_schema': (whole(SUPPORT, lambda f: f.with_columns(
        pl.col('j_owners').cast(pl.Int64))), {'support'}),
    'support_extra_column': (whole(SUPPORT, lambda f: f.with_columns(
        pl.lit(1, dtype=pl.UInt64).alias('extra'))), {'support'}),
    'industries_order': (whole(INDUSTRIES, lambda f: f.reverse()), {'parent_industries'}),
    'industries_missing_row': (whole(INDUSTRIES, lambda f: f.head(-1)), {'parent_industries'}),
    'industries_schema': (whole(INDUSTRIES, lambda f: f.with_columns(
        pl.col('n_facilities').cast(pl.Int64))), {'parent_industries'}),
    'targets_missing_row': (whole(TARGETS, lambda f: f.head(-1)), {'targets'}),
    'targets_repeated_row': (whole(TARGETS, lambda f: pl.concat([f, f.head(1)])), {'targets'}),
    # The target rows.
    'targets_value': (cell(TARGETS, 'value', lambda v: v / 2), {'targets'}),
    'targets_value_last_bit': (cell(TARGETS, 'value', lambda v: math.nextafter(v, 2.0)),
                               {'targets'}),
    'targets_se': (cell(TARGETS, 'se', lambda v: 0.0), {'targets'}),
    'targets_n_unweighted': (cell(TARGETS, 'n_unweighted', plus_one), {'targets'}),
    'targets_n_weighted': (cell(TARGETS, 'n_weighted', lambda v: v + 1.0), {'targets'}),
    # Equal numbers of another type: 1 is not 1.0.
    'targets_n_weighted_integer': (whole(TARGETS, lambda f: f.with_columns(
        pl.col('n_weighted').cast(pl.Int64))), {'targets'}),
    'targets_flags': (cell(TARGETS, 'flags', lambda v: v[:-1]), {'targets'}),
    'targets_unit_a': (cell(TARGETS, 'unit_a', lambda v: NODE + '111110'), {'targets'}),
    'targets_unit_b': (cell(TARGETS, 'unit_b', lambda v: NODE + '111110'), {'targets'}),
    **{f'targets_{column}': (cell(TARGETS, column, lambda v: v + 'x'), {'targets'})
       for column in ('source', 'family', 'unit_a_type', 'unit_b_type', 'measure', 'se_method',
                      'sample_set', 'vintage', 'universe')},
    # The marginals.
    **{f'marginals_{column}': (cell(MARGINALS, column, plus_one), {'marginals'})
       for column in ('n_owners', 'n_parent_owners', 'n_multi_industry_owners', 'n_facilities',
                      'n_facility_years', 'n_owners_dnb', 'n_owners_including_federal',
                      'n_owners_partial')},
    'marginals_node_id': (cell(MARGINALS, 'node_id', lambda v: NODE + '111110'), {'marginals'}),
    # The support, the yearly j and both sensitivities.
    **{f'support_{column}': (cell(SUPPORT, column, plus_one), {'support'})
       for column in ('j_owners', 'j_2022', 'j_2023', 'j_2024', 'j_dnb', 'j_including_federal')},
    'support_unit_a': (cell(SUPPORT, 'unit_a', lambda v: NODE + '111110'), {'support'}),
    'support_unit_b': (cell(SUPPORT, 'unit_b', lambda v: NODE + '111110'), {'support'}),
    # The O8 table.
    **{f'industries_{column}': (cell(INDUSTRIES, column, plus_one), {'parent_industries'})
       for column in ('n_facilities', 'n_facility_years', 'f_2022', 'f_2023', 'f_2024')},
    'industries_parent_name': (cell(INDUSTRIES, 'parent_name', lambda v: v + 'x'),
                               {'parent_industries'}),
    'industries_node_id': (cell(INDUSTRIES, 'node_id', lambda v: NODE + '111110'),
                           {'parent_industries'}),
    # The report.
    **{f'report_n_owners_{key}': (in_report('n_owners', key), {'n_owners'})
       for key in ('headline', 'dnb', 'federal')},
    **{f'report_owners_by_year_{key}': (in_report('owners_by_year', '2023', key),
                                        {'owners_by_year'})
       for key in ('headline', 'dnb', 'federal')},
    **{f'report_rows_by_form_type_{key}': (
        in_report('by_year', '2022', 'rows_by_form_type', key), {'rows_by_form_type'})
       for key in ('form_r', 'form_a')},
    **{f'report_reason_{key}': (in_report('by_year', '2023', 'facility_years_by_reason', key),
                                {'facility_years_by_reason'})
       for key in ('eligible', 'naics_missing', 'naics_conflict', 'naics_not_2022',
                   'parent_conflict', 'federal')},
    **{f'report_year_{key}': (in_report('by_year', '2024', key), {'year_counts'})
       for key in ('rows', 'facility_years', 'mixed_blank', 'with_foreign_parent',
                   'with_secondary_codes')},
    **{f'report_{key}': (in_report(key), {'sensitivity_cells'})
       for key in ('cells_only_dnb', 'cells_only_federal')},
    'report_owner_key_changes': (in_report('owner_key_changes'), {'owner_key_changes'}),
    'report_partial_owners': (in_report('partial_owners'), {'partial_owners'}),
    'report_partial_owners_as_true': (in_report('partial_owners', change=lambda v: True),
                                      {'partial_owners'}),
    'report_extra_year': (report_change(lambda r: r['by_year'].update({'2021': {}})),
                          {'rows_by_form_type', 'facility_years_by_reason', 'year_counts'}),
    'report_no_by_year': (report_change(lambda r: r.pop('by_year')),
                          {'rows_by_form_type', 'facility_years_by_reason', 'year_counts'}),
}


@pytest.mark.parametrize('name', sorted(TAMPERED))
def test_each_recomputed_quantity_is_compared(chain, name):
    change, flipped = TAMPERED[name]
    run_id, pin = repinned_copy(chain, 'tampered_' + name, change)
    status, line = run(chain, run_id, pin)
    assert status == 1
    assert line['equal'] is False
    assert line['refused'] is False
    assert unequal_checks(line) == flipped


def test_differing_counts_name_the_rows_that_differ(chain):
    run_id, pin = repinned_copy(chain, 'counted', cell(FY, 'n_forms', plus_one, row=2))
    status, line = run(chain, run_id, pin)
    assert status == 1
    assert (line['facility_years_differing'], line['eligibility_differing']) == (1, 0)
    run_id, pin = repinned_copy(chain, 'counted_targets',
                                whole(TARGETS, lambda f: pl.concat([f, f.head(2)])))
    assert run(chain, run_id, pin)[1]['targets_differing'] == 2


def test_target_rows_are_compared_by_cell_not_by_position(chain):
    run_id, pin = repinned_copy(chain, 'targets_reordered', whole(TARGETS, lambda f: f.reverse()))
    status, line = run(chain, run_id, pin)
    assert status == 0
    assert line['equal'] is True


# Refusals.

def data_copy(chain, tmp_path):
    '''A copy of the chain's data root and the first bundle's directory in it.'''
    data_dir = tmp_path / 'data'
    shutil.copytree(chain['data_dir'], data_dir, symlinks=True)
    return data_dir, data_dir / BUNDLES / chain['first'].name


def edit_json(file: Path, change) -> None:
    value = json.loads(file.read_text())
    change(value)
    target_io.write_json(file, value)


def with_inputs(chain, name, change):
    '''A re-pinned bundle copy whose `inputs.json` is changed.'''
    run_id, pin = repinned_copy(chain, 'refused_' + name,
                                lambda directory: edit_json(directory / 'inputs.json', change))
    return chain['data_dir'], run_id, pin


def recite(data_dir: Path, bundle: Path, year: int, change) -> str:
    '''Rewrite one raw file of a data copy, cite its new bytes in `inputs.json` and re-pin.'''
    inputs = json.loads((bundle / 'inputs.json').read_text())
    entry = next(entry for entry in inputs['raw'] if entry['path'].split('/')[2] == str(year))
    raw = data_dir / 'raw' / entry['path']
    raw.write_bytes(change(raw.read_bytes()))
    entry.update(sha256=manifest.sha256_file(raw), size=raw.stat().st_size)
    target_io.write_json(bundle / 'inputs.json', inputs)
    return repin(bundle)


def raw_entry(inputs: dict, year: int) -> dict:
    return next(entry for entry in inputs['raw'] if entry['path'].split('/')[2] == str(year))


def codes_directory(data_dir: Path, bundle: Path) -> Path:
    run_id = json.loads((bundle / 'inputs.json').read_text())['codes']['run_id']
    return data_dir / 'derived' / 'codes' / run_id


def link_elsewhere(path: Path, elsewhere: Path) -> None:
    '''Move `path` to `elsewhere` and leave a symbolic link to it in its place.'''
    elsewhere.parent.mkdir(parents=True, exist_ok=True)
    path.rename(elsewhere)
    path.symlink_to(elsewhere)


REFUSALS = {}


def refusal(case):
    REFUSALS[case.__name__] = case
    return case


@refusal
def missing_data_dir(chain, tmp_path):
    return (tmp_path / 'absent', chain['first'].name, chain['first_pin'],
            'data directory is missing')


@refusal
def unsafe_run_id(chain, tmp_path):
    return (chain['data_dir'], '../parent-links/' + chain['first'].name, chain['first_pin'],
            'unsafe run id')


@refusal
def malformed_pin(chain, tmp_path):
    return chain['data_dir'], chain['first'].name, chain['first_pin'].upper(), 'malformed pin'


@refusal
def missing_bundle(chain, tmp_path):
    return chain['data_dir'], 'absent_run', chain['first_pin'], 'bundle is missing'


@refusal
def wrong_pin(chain, tmp_path):
    return chain['data_dir'], chain['first'].name, chain['second_pin'], 'detached pin differs'


@refusal
def linked_outputs(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    link_elsewhere(bundle / 'outputs.json', tmp_path / 'elsewhere' / 'outputs.json')
    return data_dir, bundle.name, chain['first_pin'], 'bundle is missing'


@refusal
def linked_bundle(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    link_elsewhere(bundle, tmp_path / 'elsewhere' / bundle.name)
    return data_dir, bundle.name, chain['first_pin'], 'bundle is missing'


@refusal
def changed_bundle_file(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    (bundle / 'report.json').write_text('{}')
    return data_dir, bundle.name, chain['first_pin'], 'bundle file differs from its inventory'


@refusal
def linked_bundle_file(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    link_elsewhere(bundle / 'tri_parent_links.parquet', tmp_path / 'elsewhere' / 'links.parquet')
    return data_dir, bundle.name, chain['first_pin'], 'bundle file differs from its inventory'


@refusal
def inventory_lacks_a_file(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    edit_json(bundle / 'outputs.json', lambda value: value.pop('report.json'))
    pin = manifest.sha256_file(bundle / 'outputs.json')
    return data_dir, bundle.name, pin, 'bundle inventory differs'


@refusal
def inventory_names_another_file(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    edit_json(bundle / 'outputs.json',
              lambda value: value.update({'extra.json': value['report.json']}))
    pin = manifest.sha256_file(bundle / 'outputs.json')
    return data_dir, bundle.name, pin, 'bundle inventory differs'


@refusal
def inputs_not_an_object(chain, tmp_path):
    def change(directory):
        (directory / 'inputs.json').write_text('[]')
    run_id, pin = repinned_copy(chain, 'refused_inputs_list', change)
    return chain['data_dir'], run_id, pin, 'bundle json is not an object'


@refusal
def changed_raw_byte(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    raw = data_dir / 'raw' / raw_entry(json.loads((bundle / 'inputs.json').read_text()),
                                       2023)['path']
    body = raw.read_bytes()
    raw.write_bytes(body.replace(b'Birch', b'Birck', 1))
    assert raw.stat().st_size == len(body)
    return data_dir, bundle.name, chain['first_pin'], 'raw file differs from its citation'


@refusal
def missing_raw_file(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    inputs = json.loads((bundle / 'inputs.json').read_text())
    (data_dir / 'raw' / raw_entry(inputs, 2024)['path']).unlink()
    return data_dir, bundle.name, chain['first_pin'], 'raw file differs from its citation'


@refusal
def linked_raw_file(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    inputs = json.loads((bundle / 'inputs.json').read_text())
    link_elsewhere(data_dir / 'raw' / raw_entry(inputs, 2022)['path'],
                   tmp_path / 'elsewhere' / '2022_us.csv')
    return data_dir, bundle.name, chain['first_pin'], 'raw path is unsafe'


@refusal
def linked_raw_file_inside_the_tree(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    inputs = json.loads((bundle / 'inputs.json').read_text())
    link_elsewhere(data_dir / 'raw' / raw_entry(inputs, 2022)['path'],
                   data_dir / 'raw' / 'epa_tri' / 'moved_2022_us.csv')
    return data_dir, bundle.name, chain['first_pin'], 'raw path is unsafe'


@refusal
def linked_raw_directory(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    link_elsewhere(data_dir / 'raw' / 'epa_tri' / 'basic' / '2022',
                   tmp_path / 'elsewhere' / '2022')
    return data_dir, bundle.name, chain['first_pin'], 'raw path is unsafe'


def raw_path(path, chain, name):
    def change(inputs):
        raw_entry(inputs, 2022)['path'] = path
    return (*with_inputs(chain, name, change), 'raw path is unsafe')


@refusal
def raw_path_climbs(chain, tmp_path):
    return raw_path('epa_tri/basic/2022/2025-11-05/../2025-11-05/2022_us.csv', chain, 'climbs')


@refusal
def raw_path_ends_in_a_parent(chain, tmp_path):
    return raw_path('epa_tri/basic/2022/2025-11-05/..', chain, 'parent')


@refusal
def raw_path_of_another_snapshot(chain, tmp_path):
    return raw_path('epa_tri/basic/2022/2025-12-01/2022_us.csv', chain, 'snapshot')


@refusal
def raw_path_of_another_source(chain, tmp_path):
    return raw_path('epa_tri/other/2022/2025-11-05/2022_us.csv', chain, 'source')


@refusal
def raw_path_absolute(chain, tmp_path):
    return raw_path('/epa_tri/basic/2022/2025-11-05/2022_us.csv', chain, 'absolute')


def window_case(change, chain, name, reason='raw citations differ from the window'):
    return (*with_inputs(chain, name, change), reason)


@refusal
def raw_year_outside_window(chain, tmp_path):
    def change(inputs):
        raw_entry(inputs, 2022)['path'] = 'epa_tri/basic/2021/2025-11-05/2022_us.csv'
    return window_case(change, chain, 'outside')


@refusal
def raw_year_repeated(chain, tmp_path):
    def change(inputs):
        inputs['raw'][1] = dict(inputs['raw'][0])
    return window_case(change, chain, 'repeated')


@refusal
def raw_citation_dropped(chain, tmp_path):
    return window_case(lambda inputs: inputs['raw'].pop(), chain, 'dropped')


@refusal
def raw_citation_malformed(chain, tmp_path):
    def change(inputs):
        inputs['raw'][0] = 'epa_tri/basic/2022/2025-11-05/2022_us.csv'
    return window_case(change, chain, 'malformed', 'raw citation is malformed')


@refusal
def window_differs(chain, tmp_path):
    return window_case(lambda inputs: inputs['window'].pop(), chain, 'window', 'window differs')


@refusal
def snapshot_date_compact(chain, tmp_path):
    return window_case(lambda inputs: inputs.update(processed_as_of='20251105'), chain,
                       'compact', 'snapshot date is malformed')


@refusal
def snapshot_date_not_a_date(chain, tmp_path):
    return window_case(lambda inputs: inputs.update(processed_as_of='2025-13-05'), chain,
                       'not_a_date', 'snapshot date is malformed')


@refusal
def changed_codes_pin(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    outputs = codes_directory(data_dir, bundle) / 'outputs.json'
    outputs.write_bytes(outputs.read_bytes() + b'\n')
    return data_dir, bundle.name, chain['first_pin'], 'codes pin differs'


@refusal
def linked_codes_outputs(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    link_elsewhere(codes_directory(data_dir, bundle) / 'outputs.json',
                   tmp_path / 'elsewhere' / 'codes-outputs.json')
    return data_dir, bundle.name, chain['first_pin'], 'codes bundle is missing'


@refusal
def changed_codes_nodes(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    nodes = codes_directory(data_dir, bundle) / 'naics_nodes.parquet'
    pl.read_parquet(nodes).head(-1).write_parquet(nodes)
    return data_dir, bundle.name, chain['first_pin'], 'codes nodes differ from their inventory'


@refusal
def codes_inventory_differs(chain, tmp_path):
    def change(inputs):
        inputs['codes']['outputs']['naics_nodes.parquet']['size'] += 1
    return window_case(change, chain, 'codes_inventory', 'codes inventory differs')


@refusal
def unsafe_codes_run(chain, tmp_path):
    def change(inputs):
        inputs['codes']['run_id'] = '../codes/' + inputs['codes']['run_id']
    return window_case(change, chain, 'codes_run', 'unsafe codes run id')


@refusal
def missing_codes_bundle(chain, tmp_path):
    def change(inputs):
        inputs['codes']['run_id'] = 'absent_codes'
    return window_case(change, chain, 'codes_missing', 'codes bundle is missing')


@refusal
def malformed_codes_citation(chain, tmp_path):
    return window_case(lambda inputs: inputs.update(codes='fixture_codes'), chain,
                       'codes_malformed', 'codes citation is malformed')


@refusal
def codes_nodes_repeat_a_code(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    directory = codes_directory(data_dir, bundle)
    nodes = directory / 'naics_nodes.parquet'
    frame = pl.read_parquet(nodes)
    again = frame.filter(pl.col('level') == 'national_industry').head(1).with_columns(
        pl.lit(NODE + 'again').alias('node_id'))
    pl.concat([frame, again]).write_parquet(nodes)
    edit_json(directory / 'outputs.json', lambda value: value.update({
        'naics_nodes.parquet': {'sha256': manifest.sha256_file(nodes),
                                'size': nodes.stat().st_size}}))

    def cite(inputs):
        inputs['codes']['outputs'] = json.loads((directory / 'outputs.json').read_text())
        inputs['codes']['outputs_sha256'] = manifest.sha256_file(directory / 'outputs.json')
    edit_json(bundle / 'inputs.json', cite)
    return data_dir, bundle.name, repin(bundle), 'codes nodes repeat a code'


@refusal
def changed_header(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    cell_name = production_layout(2023).columns['standardized_parent'].encode()
    pin = recite(data_dir, bundle, 2023,
                 lambda body: body.replace(cell_name, b'17. RENAMED PARENT CELL', 1))
    return data_dir, bundle.name, pin, 'raw header differs from the layout'


@refusal
def reporting_year_differs(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    pin = recite(data_dir, bundle, 2022, lambda body: body.replace(b'\n2022,', b'\n2021,', 1))
    return data_dir, bundle.name, pin, 'raw reporting year differs from its file'


@refusal
def row_width_differs(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    pin = recite(data_dir, bundle, 2024, lambda body: body + b'2024,T999\n')
    return data_dir, bundle.name, pin, 'raw row width differs from the header'


@refusal
def undecodable_raw_line(chain, tmp_path):
    data_dir, bundle = data_copy(chain, tmp_path)
    pin = recite(data_dir, bundle, 2024, lambda body: body + b'2024,T\x81\n')
    return data_dir, bundle.name, pin, 'raw line is neither UTF-8 nor Windows-1252'


@pytest.mark.parametrize('name', sorted(REFUSALS))
def test_each_untrusted_input_is_refused(chain, tmp_path, name):
    data_dir, run_id, pin, reason = REFUSALS[name](chain, tmp_path)
    status, line = run(chain, run_id, pin, data_dir)
    assert status == 2
    assert line == {'equal': False, 'reason': reason, 'refused': True}


def test_rewritten_raw_bytes_with_the_same_rows_still_reconcile(chain, tmp_path):
    # A byte order mark and CRLF line endings change the bytes, not the rows.
    data_dir, bundle = data_copy(chain, tmp_path)
    pin = recite(data_dir, bundle, 2022,
                 lambda body: b'\xef\xbb\xbf' + body.replace(b'\n', b'\r\n'))
    status, line = run(chain, bundle.name, pin, data_dir)
    assert status == 0
    assert line['equal'] is True


# The reconciler agrees with a build from files in every delivered encoding.

def test_reconciler_agrees_with_a_build_from_bom_crlf_and_windows_1252_files(
        tmp_path, monkeypatch):
    from target_fixtures import forbid_external_access

    forbid_external_access(monkeypatch)
    data_dir = tmp_path / 'data'
    codes_run, codes_pin = seed_codes_bundle(data_dir, tmp_path / 'codes-originals')
    rows = v12_rows()
    parent = production_layout(2023).columns['standardized_parent']
    for row in rows[2023]:
        row[parent] = {'Birch Corp': 'Birch Café', 'Holly Co': 'Holly’s Co'}.get(
            row[parent], row[parent])
    originals = tmp_path / 'originals'
    originals.mkdir()
    for year, options in ((2022, {'bom': True, 'newline': '\r\n'}),
                          (2023, {'encoding': 'cp1252'}), (2024, {})):
        file = originals / tri_raw.file_name(year)
        write_tri_csv(file, year, rows[year], **options)
        if year == 2024:
            # One line in Windows-1252 and another in UTF-8, both spelling one parent.
            lines = file.read_bytes().split(b'\n')
            first = next(i for i, line in enumerate(lines)
                         if b',T105,' in line and b',Cedar Inc,' in line)
            second = next(i for i, line in enumerate(lines) if b',T106,' in line)
            lines[first] = lines[first].replace(b',Cedar Inc,', ',Cédar Inc,'.encode('cp1252'))
            lines[second] = lines[second].replace(b',Cedar Inc,', ',Cédar Inc,'.encode())
            file.write_bytes(b'\n'.join(lines))
        tri_raw.import_file(data_dir, year, file, processed_as_of=V12_DATE)
    published = tri_bundle.build(data_dir, 'encodings', codes_run=codes_run,
                                 codes_outputs_sha256=codes_pin, processed_as_of=V12_DATE)
    status, line = run({'data_dir': data_dir}, 'encodings', published['outputs_sha256'],
                       data_dir)
    assert status == 0, line
    assert line['equal'] is True
    names = pl.read_parquet(Path(published['directory']) / 'tri_parent_industries.parquet')
    assert {'Birch Café', 'Holly’s Co', 'Cédar Inc'} <= set(names['parent_name'])


# Reading the raw files.

def test_decoded_lines_drop_a_byte_order_mark_at_the_start_only():
    stream = io.BytesIO(b'\xef\xbb\xbfa\r\n\xef\xbb\xbfb\n')
    assert list(reconcile.decoded_lines(stream)) == ['a\r\n', '﻿b\n']


def test_decoded_lines_fall_back_to_windows_1252_line_by_line():
    stream = io.BytesIO('Café\n'.encode() + 'Café\n'.encode('cp1252') + b'x\x93y\x94\n')
    assert list(reconcile.decoded_lines(stream)) == ['Café\n', 'Café\n', 'x“y”\n']


def test_decoded_lines_strip_the_mark_before_decoding_and_return_to_utf8():
    stream = io.BytesIO(b'\xef\xbb\xbf' + 'Café\n'.encode('cp1252') + 'naïve\n'.encode())
    assert list(reconcile.decoded_lines(stream)) == ['Café\n', 'naïve\n']


def test_decoded_lines_refuse_a_line_outside_both_encodings():
    with pytest.raises(reconcile.Refused, match='neither UTF-8 nor Windows-1252'):
        list(reconcile.decoded_lines(io.BytesIO(b'a\n\x81\n')))


def test_read_forms_reads_a_file_with_a_byte_order_mark_and_crlf_endings(tmp_path):
    file = tmp_path / '2022.csv'
    write_tri_csv(file, 2022, [
        tri_row(2022, 'T1', primary_naics='325110', state='TX', standardized_parent='Alder'),
        tri_row(2022, 'T2', primary_naics='331110', state='OH', form='A')],
        bom=True, newline='\r\n')
    forms = list(reconcile.read_forms(file, 2022))
    assert [(form.trifd, form.form_type, form.state, form.primary_naics) for form in forms] == [
        ('T1', 'R', 'TX', '325110'), ('T2', 'A', 'OH', '331110')]
    assert forms[0].standardized_parent == 'Alder'
    assert forms[0].standardized_foreign_parent is None


def test_read_forms_reads_windows_1252_values(tmp_path):
    file = tmp_path / '2023.csv'
    write_tri_csv(file, 2023, [tri_row(2023, 'T1', primary_naics='325110',
                                       standardized_parent='Café Holdings',
                                       standardized_foreign_parent='Société SA')],
                  encoding='cp1252')
    (form,) = reconcile.read_forms(file, 2023)
    assert (form.standardized_parent, form.standardized_foreign_parent) == (
        'Café Holdings', 'Société SA')


def test_read_forms_skips_an_empty_line(tmp_path):
    file = tmp_path / '2024.csv'
    write_tri_csv(file, 2024, [tri_row(2024, 'T1', primary_naics='325110')])
    file.write_bytes(file.read_bytes() + b'\n')
    write_tri_csv(tmp_path / 'more.csv', 2024, [tri_row(2024, 'T2', primary_naics='325110')])
    file.write_bytes(file.read_bytes() + (tmp_path / 'more.csv').read_bytes().split(b'\n', 1)[1])
    assert [form.trifd for form in reconcile.read_forms(file, 2024)] == ['T1', 'T2']


# The recomputation, on small typed rows.

def recomputed(tmp_path, rows: dict[int, list[dict]]):
    files = {}
    for year, year_rows in rows.items():
        files[year] = tmp_path / f'{year}.csv'
        write_tri_csv(files[year], year, year_rows)
    return reconcile.recompute(files, NODES, DATE)


def facility_years(result) -> dict:
    return {(row[0], row[1]): dict(zip(reconcile.FACILITY_COLUMNS, row, strict=True))
            for row in result.facility_years}


def marginals(result) -> dict:
    return {row[0].removeprefix(NODE): dict(zip(reconcile.MARGINAL_SCHEMA, row, strict=True))
            for row in result.marginals}


def support(result) -> dict:
    return {(row[0].removeprefix(NODE), row[1].removeprefix(NODE)):
            dict(zip(reconcile.SUPPORT_SCHEMA, row, strict=True)) for row in result.support}


def targets(result) -> dict:
    return {(a.removeprefix(NODE), b.removeprefix(NODE)):
            dict(zip(reconcile.TARGET_VALUES, row, strict=True))
            for (a, b), row in result.targets.items()}


def owned(year, trifd, code, parent, **fields):
    return tri_row(year, trifd, primary_naics=code, standardized_parent=parent, **fields)


def test_forms_reduce_to_one_facility_year_with_counts_by_form_type(tmp_path):
    result = recomputed(tmp_path, {2022: [
        owned(2022, 'T1', ' 325110', 'P', state='TX', naics_2='325120'),
        owned(2022, 'T1', '325110 ', 'P', state='LA', naics_2=' 331110', naics_3='', form='A'),
        owned(2022, 'T1', '325110', 'P', state='TX'),
    ]})
    item = facility_years(result)[(2022, 'T1')]
    assert (item['n_forms'], item['n_form_r'], item['n_form_a']) == (3, 2, 1)
    assert item['primary_naics_values'] == ('325110',)
    assert item['other_naics_values'] == (' 331110', '325120')
    assert item['state_values'] == ('LA', 'TX')
    assert item['federal_values'] == ('NO',)
    assert (item['naics_2022_node_id'], item['owner_key'], item['exclusion_reason']) == (
        NODE + '325110', 'parent:P', None)
    report = result.report
    assert report['rows_by_form_type'] == {'2022': {'form_a': 1, 'form_r': 2}}
    assert report['year_counts'] == {'2022': {
        'rows': 3, 'facility_years': 1, 'mixed_blank': 0, 'with_foreign_parent': 0,
        'with_secondary_codes': 1}}


def test_a_blank_primary_code_is_no_code(tmp_path):
    result = recomputed(tmp_path, {2023: [
        owned(2023, 'T1', '   ', 'P'), owned(2023, 'T2', '', 'P'),
        owned(2023, 'T3', '', 'P'), owned(2023, 'T3', '325110', 'P')]})
    years = facility_years(result)
    assert years[(2023, 'T1')]['exclusion_reason'] == 'naics_missing'
    assert years[(2023, 'T1')]['primary_naics_values'] == ()
    assert years[(2023, 'T2')]['exclusion_reason'] == 'naics_missing'
    assert years[(2023, 'T3')]['exclusion_reason'] is None


def test_exclusion_reasons_are_checked_in_the_spec_order(tmp_path):
    def two_parents(trifd, *codes, federal=False):
        return [owned(2023, trifd, code, parent, federal=federal)
                for code, parent in zip(codes, ('Elm', 'Fir'), strict=True)]

    result = recomputed(tmp_path, {2023: [
        *two_parents('T1', '', '', federal=True),
        *two_parents('T2', '325110', '325120', federal=True),
        *two_parents('T3', '336111', '336111', federal=True),
        *two_parents('T4', '325110', '325110', federal=True),
        owned(2023, 'T5', '325110', 'Elm', federal=True),
        owned(2023, 'T6', '325110', 'Elm'),
    ]})
    years = facility_years(result)
    assert [(years[(2023, trifd)]['exclusion_reason'], years[(2023, trifd)]['naics_2022_node_id'],
             years[(2023, trifd)]['owner_key']) for trifd in ('T1', 'T2', 'T3', 'T4', 'T5', 'T6')
            ] == [('naics_missing', None, None), ('naics_conflict', None, None),
                  ('naics_not_2022', None, None), ('parent_conflict', NODE + '325110', None),
                  ('federal', NODE + '325110', None), (None, NODE + '325110', 'parent:Elm')]
    assert result.report['facility_years_by_reason'] == {'2023': {
        'eligible': 1, 'naics_missing': 1, 'naics_conflict': 1, 'naics_not_2022': 1,
        'parent_conflict': 1, 'federal': 1}}


def test_any_federal_form_makes_the_facility_year_federal(tmp_path):
    result = recomputed(tmp_path, {2022: [
        owned(2022, 'T1', '325110', 'P', federal=False),
        owned(2022, 'T1', '325110', 'P', federal=True),
        owned(2022, 'T2', '325110', 'P', federal=False),
        owned(2022, 'T3', '325110', 'P', federal=True),
        owned(2022, 'T3', '325110', 'P', federal=False)]})
    years = facility_years(result)
    assert years[(2022, 'T1')]['exclusion_reason'] == 'federal'
    assert years[(2022, 'T1')]['federal_values'] == ('NO', 'YES')
    assert years[(2022, 'T2')]['exclusion_reason'] is None
    assert years[(2022, 'T3')]['exclusion_reason'] == 'federal'
    # A blank state cell is no state value.
    assert years[(2022, 'T2')]['state_values'] == ()


def test_standardized_names_are_stripped_and_no_parent_strings_and_blanks_are_absent(tmp_path):
    result = recomputed(tmp_path, {2023: [
        owned(2023, 'T1', '325110', ' Alder '), owned(2023, 'T1', '325110', 'NA'),
        owned(2023, 'T1', '325110', ''),
        owned(2023, 'T2', '325110', 'NA'), owned(2023, 'T2', '325110', ' NA '),
        owned(2023, 'T3', '325110', ''), owned(2023, 'T3', '325110', 'Birch'),
        owned(2023, 'T4', '325110', 'Cedar'), owned(2023, 'T4', '325110', 'Cedar'),
    ]})
    years = facility_years(result)
    assert [(years[(2023, trifd)]['parent_names'], years[(2023, trifd)]['flag_parent_mixed_blank'],
             years[(2023, trifd)]['owner_key']) for trifd in ('T1', 'T2', 'T3', 'T4')] == [
        (('Alder',), True, 'parent:Alder'), ((), False, 'facility:T2'),
        (('Birch',), True, 'parent:Birch'), (('Cedar',), False, 'parent:Cedar')]
    assert result.report['year_counts']['2023']['mixed_blank'] == 2


def test_foreign_parent_names_are_read_from_2023_only(tmp_path):
    result = recomputed(tmp_path, {
        2022: [owned(2022, 'T1', '325110', 'P')],
        2023: [owned(2023, 'T1', '325110', 'P', standardized_foreign_parent=' Birch SA '),
               owned(2023, 'T1', '325110', 'P', standardized_foreign_parent='NA'),
               owned(2023, 'T1', '325110', 'P', standardized_foreign_parent=''),
               owned(2023, 'T2', '325110', 'P', standardized_foreign_parent='NA')]})
    years = facility_years(result)
    assert years[(2022, 'T1')]['foreign_parent_names'] == ()
    assert years[(2023, 'T1')]['foreign_parent_names'] == ('Birch SA',)
    assert years[(2023, 'T2')]['foreign_parent_names'] == ()
    assert result.report['year_counts']['2023']['with_foreign_parent'] == 1


def test_facilities_with_no_parent_never_share_an_owner(tmp_path):
    result = recomputed(tmp_path, {2023: [
        owned(2023, 'T1', '325110', 'NA'), owned(2023, 'T2', '325110', 'NA'),
        owned(2023, 'T3', '325120', ''), owned(2023, 'T4', '325120', 'P')]})
    assert result.targets == {}
    assert marginals(result)['325110']['n_owners'] == 2
    assert marginals(result)['325110']['n_parent_owners'] == 0
    assert marginals(result)['325120']['n_owners'] == 2
    assert marginals(result)['325120']['n_parent_owners'] == 1
    assert result.report['n_owners']['headline'] == 4


def test_same_year_co_presence_counts_each_owner_once_in_both_directions(tmp_path):
    result = recomputed(tmp_path, {
        2022: [owned(2022, 'T1', '325110', 'P'), owned(2022, 'T2', '325120', 'P'),
               owned(2022, 'T4', '325110', 'Q')],
        2023: [owned(2023, 'T1', '325110', 'P'), owned(2023, 'T2', '325120', 'P'),
               owned(2023, 'T3', '325120', 'P')]})
    # No form gives a D&B number, so each facility is its own D&B owner and j_dnb is 0.
    assert support(result) == {
        ('325110', '325120'): {'unit_a': NODE + '325110', 'unit_b': NODE + '325120',
                               'j_owners': 1, 'j_2022': 1, 'j_2023': 1, 'j_2024': 0,
                               'j_dnb': 0, 'j_including_federal': 1},
        ('325120', '325110'): {'unit_a': NODE + '325120', 'unit_b': NODE + '325110',
                               'j_owners': 1, 'j_2022': 1, 'j_2023': 1, 'j_2024': 0,
                               'j_dnb': 0, 'j_including_federal': 1}}
    values = {cell: row['value'] for cell, row in targets(result).items()}
    assert values == {('325110', '325120'): 0.5, ('325120', '325110'): 1.0}
    rows = marginals(result)
    assert (rows['325110']['n_owners'], rows['325120']['n_owners']) == (2, 1)
    assert (rows['325120']['n_facilities'], rows['325120']['n_facility_years']) == (2, 3)
    assert (rows['325110']['n_multi_industry_owners'],
            rows['325120']['n_multi_industry_owners']) == (1, 1)


def test_a_cross_year_pair_gives_no_cell(tmp_path):
    result = recomputed(tmp_path, {2022: [owned(2022, 'T1', '325110', 'P')],
                                   2024: [owned(2024, 'T2', '325120', 'P')]})
    assert result.targets == {} and result.support == []
    rows = marginals(result)
    assert (rows['325110']['n_owners'], rows['325120']['n_owners']) == (1, 1)
    assert (rows['325110']['n_multi_industry_owners'],
            rows['325120']['n_multi_industry_owners']) == (0, 0)
    assert result.report['owners_by_year'] == {
        '2022': {'headline': 1, 'dnb': 1, 'federal': 1},
        '2024': {'headline': 1, 'dnb': 1, 'federal': 1}}


def test_target_rows_carry_the_spec_metadata(tmp_path):
    result = recomputed(tmp_path, {2023: [
        owned(2023, 'T1', '325110', 'P', parent_dnb='111111111'),
        owned(2023, 'T2', '325120', 'P', parent_dnb='111111111')]})
    row = targets(result)[('325110', '325120')]
    assert row == {
        'source': 'epa_tri', 'family': 'tri_parent_links',
        'unit_a_type': 'naics_national_industry', 'unit_b_type': 'naics_national_industry',
        'measure': 'owner_share', 'value': 1.0, 'se': None, 'se_method': 'none',
        'n_unweighted': 1, 'n_weighted': 1.0, 'sample_set': 'tri_basic_ry2022_2024',
        'vintage': 'naics=2022', 'universe': reconcile.UNIVERSE.format(date=DATE),
        'flags': ('size_gate_pending',)}
    assert type(row['n_unweighted']) is int and type(row['n_weighted']) is float
    assert 'forms processed as of 2025-11-05. TRI is' in row['universe']
    assert 'reporting years 2022–2024' in row['universe']


def test_the_dnb_key_needs_exactly_one_usable_number(tmp_path):
    result = recomputed(tmp_path, {2023: [
        # One usable number after stripping, beside a "no D&B number" string: one D&B owner.
        owned(2023, 'T1', '325110', 'P', parent_dnb=' 111111111'),
        owned(2023, 'T1', '325110', 'P', parent_dnb='NA'),
        owned(2023, 'T2', '325120', 'Q', parent_dnb='111111111 '),
        # Two usable numbers: the facility is its own D&B owner.
        owned(2023, 'T3', '324110', 'R', parent_dnb='222222222'),
        owned(2023, 'T3', '324110', 'R', parent_dnb='333333333'),
        owned(2023, 'T4', '325211', 'R', parent_dnb='222222222'),
    ]})
    cells = support(result)
    assert cells[('324110', '325211')]['j_owners'] == 1
    assert cells[('324110', '325211')]['j_dnb'] == 0
    assert DNB_LABEL in targets(result)[('324110', '325211')]['flags']
    assert ('325110', '325120') not in cells
    assert result.report['sensitivity_cells'] == {'cells_only_dnb': 2, 'cells_only_federal': 0}
    assert result.report['n_owners'] == {'headline': 3, 'dnb': 3, 'federal': 3}
    rows = marginals(result)
    assert (rows['325110']['n_owners_dnb'], rows['324110']['n_owners_dnb']) == (1, 1)


def test_a_usable_dnb_number_groups_facilities_with_no_standardized_name(tmp_path):
    # Case (c): the D&B sensitivity reads the D&B field alone.
    result = recomputed(tmp_path, {2024: [
        owned(2024, 'T1', '325110', 'NA', parent_dnb='555555555'),
        owned(2024, 'T2', '325120', '', parent_dnb='555555555')]})
    assert result.targets == {}
    assert result.report['n_owners'] == {'headline': 2, 'dnb': 1, 'federal': 2}
    assert result.report['owners_by_year']['2024'] == {'headline': 2, 'dnb': 1, 'federal': 2}
    assert result.report['sensitivity_cells']['cells_only_dnb'] == 2


def test_the_federal_sensitivity_adds_only_federal_exclusions(tmp_path):
    result = recomputed(tmp_path, {2023: [
        owned(2023, 'T1', '324110', 'Q'), owned(2023, 'T2', '325211', 'Q'),
        owned(2023, 'T3', '324110', 'U'), owned(2023, 'T4', '325211', 'U', federal=True),
        owned(2023, 'T5', '325110', 'V'), owned(2023, 'T6', '331110', 'V', federal=True),
        owned(2023, 'T7', '325199', 'W'), owned(2023, 'T8', '325120', 'W'),
        owned(2023, 'T8', '325120', 'X'),
    ]})
    cells = support(result)
    assert (cells[('324110', '325211')]['j_owners'],
            cells[('324110', '325211')]['j_including_federal']) == (1, 2)
    assert FEDERAL_LABEL in targets(result)[('324110', '325211')]['flags']
    assert ('325110', '331110') not in cells
    rows = marginals(result)
    assert (rows['325211']['n_owners'], rows['325211']['n_owners_including_federal']) == (1, 2)
    # A node that only a federal facility-year reaches is not a headline marginal row.
    assert '331110' not in rows and '325120' not in rows
    assert result.report['sensitivity_cells'] == {'cells_only_dnb': 0, 'cells_only_federal': 2}
    # No form gives a D&B number: the five eligible facilities are five D&B owners.
    assert result.report['n_owners'] == {'headline': 4, 'dnb': 5, 'federal': 4}


def test_partial_owners_need_a_non_federal_exclusion_in_the_same_year(tmp_path):
    result = recomputed(tmp_path, {
        2022: [owned(2022, 'T15', '325120', 'P'), owned(2022, 'T4', '', 'Q')],
        2023: [
            owned(2023, 'T1', '325110', 'P'), owned(2023, 'T2', '', 'P'),
            owned(2023, 'T16', '324110', 'P'),
            owned(2023, 'T3', '325120', 'Q'),
            owned(2023, 'T5', '324110', 'R'), owned(2023, 'T6', '324110', 'R', federal=True),
            owned(2023, 'T7', '325199', 'S'),
            owned(2023, 'T8', '325199', 'S'), owned(2023, 'T8', '325199', 'X'),
            owned(2023, 'T9', '331110', 'V'),
            owned(2023, 'T10', '331110', 'V'), owned(2023, 'T10', '325110', 'W'),
            owned(2023, 'T11', '325211', 'Z'), owned(2023, 'T12', '336111', 'Z'),
            owned(2023, 'T13', '325211', 'Y'),
            owned(2023, 'T14', '325110', 'Y'), owned(2023, 'T14', '325120', 'Y'),
        ]})
    years = facility_years(result)
    assert years[(2023, 'T8')]['exclusion_reason'] == 'parent_conflict'
    assert years[(2023, 'T10')]['exclusion_reason'] == 'naics_conflict'
    partial = {code: row['n_owners_partial'] for code, row in marginals(result).items()}
    # P is partial in two industries and still counts once among the partial owners.
    assert partial == {'324110': 1, '325110': 1, '325120': 0, '325199': 1, '325211': 2,
                       '331110': 0}
    assert result.report['partial_owners'] == 4


def test_the_parent_industry_table_covers_parent_keyed_eligible_facility_years(tmp_path):
    result = recomputed(tmp_path, {
        2022: [owned(2022, 'T1', '325110', 'P')],
        2023: [owned(2023, 'T1', '325110', 'P'), owned(2023, 'T2', '325110', 'P'),
               owned(2023, 'T4', '324110', 'NA'), owned(2023, 'T5', '324110', 'P', federal=True)],
        2024: [owned(2024, 'T3', '325120', 'P')]})
    columns = reconcile.INDUSTRY_SCHEMA
    assert [dict(zip(columns, row, strict=True)) for row in result.parent_industries] == [
        {'parent_name': 'P', 'node_id': NODE + '325110', 'n_facilities': 2,
         'n_facility_years': 3, 'f_2022': 1, 'f_2023': 2, 'f_2024': 0},
        {'parent_name': 'P', 'node_id': NODE + '325120', 'n_facilities': 1,
         'n_facility_years': 1, 'f_2022': 0, 'f_2023': 0, 'f_2024': 1}]


def test_owner_key_changes_count_facilities_with_two_headline_keys(tmp_path):
    result = recomputed(tmp_path, {
        2022: [owned(2022, 'T1', '325110', 'P'), owned(2022, 'T2', '325110', 'P'),
               owned(2022, 'T3', '325110', 'NA')],
        2023: [owned(2023, 'T1', '325110', 'Q'), owned(2023, 'T2', '', 'Q')],
        2024: [owned(2024, 'T3', '325110', 'P'), owned(2024, 'T2', '325110', 'P')]})
    assert result.report['owner_key_changes'] == 2
