'''The independent CPS job-flow reconciler, on seeded bundles that the production `build` writes.

The script is loaded by path and run through `main(argv)`. Each tampered copy of a seeded data
root changes one recomputed quantity, gets a fresh detached pin, and must make its own check
unequal and no other. Each refusal prints one fixed line to stderr, nothing to stdout, and exits 2.
'''

import ast
import contextlib
import functools
import importlib.util
import io
import json
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import polars as pl
import pytest
from cps_flow_fixtures import (
    JOB_FLOW_CPSID,
    JOB_FLOW_CPSIDV,
    V12_RUNS,
    job_flow_rows,
    no_live_clients,  # noqa: F401
    run_cps_flow_v12,
    seed_upstreams,
)

from embedding_data import manifest, target_io
from embedding_data.cps_flow_bundle import FILES, build, run_directory

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'reconcile_cps_job_flows.py'
CHECKS = ('value_classes', 'x_residuals', 'links', 'guards', 'eligibility', 'targets', 'asec_se')
RUN = 'first'
FAILURE = 'CPS job flows reconcile failed: '
SOURCE_EXCEPTION = 'empsame_in_mish_1_or_5'


@functools.cache
def load_script():
    assert SCRIPT.is_file(), 'independent reconciler is missing'
    spec = importlib.util.spec_from_file_location('reconcile_cps_job_flows', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Script:
    '''Loads the script on first use, so a missing script fails each test, not collection.'''

    def __getattr__(self, name):
        return getattr(load_script(), name)


reconcile = _Script()


def run(data_dir: Path, pin: str, run_id: str = RUN) -> tuple[int, str, str]:
    '''Run the reconciler in process; return its status, standard output and standard error.'''
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = reconcile.main(['--data-dir', str(data_dir), '--run', run_id,
                                 '--outputs-sha256', pin])
    return status, out.getvalue(), err.getvalue()


def result_of(data_dir: Path, pin: str, run_id: str = RUN) -> tuple[int, dict]:
    status, out, err = run(data_dir, pin, run_id)
    assert err == ''
    lines = out.splitlines()
    assert len(lines) == 1
    result = json.loads(lines[0])
    assert lines[0] == json.dumps(result, sort_keys=True)
    assert set(result) == {'checks', 'equal'}
    assert set(result['checks']) == set(CHECKS)
    return status, result


def seeded_build(root: Path, changes: dict | None = None) -> SimpleNamespace:
    rows, people = job_flow_rows(changes)
    seeded = seed_upstreams(root, monthly=rows, asec=people)
    result = build(seeded.data_dir, RUN, seeded.request)
    return SimpleNamespace(data_dir=seeded.data_dir, directory=Path(result['directory']),
                           pin=result['outputs_sha256'])


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    '''One seeded data root with the published run `first`, shared by the module.'''
    return seeded_build(tmp_path_factory.mktemp('reconcile_cps_job_flows'))


@pytest.fixture(scope='module')
def negative_replicate(tmp_path_factory):
    '''A build whose ASEC origins of A1 have a negative replicate-7 total, and no null weight.

    A1 is the only eligible ASEC person with industry origin 0170 and occupation origin 0010,
    so replicate 7 has a nonpositive denominator in both dimensions. E9's weight is no longer
    null, so the null-weight reasons count zero.
    '''
    return seeded_build(tmp_path_factory.mktemp('negative_replicate'),
                        {'A1': {'REPWTP7': '-90000.0000'}, 'E9': {'LNKFW1MWT': '1.0000'}})


def tampered(built, tmp_path: Path, change: Callable[[Path], None]) -> tuple[Path, str]:
    '''A copy of the data root whose bundle `change` edits, repinned; the root and new pin.'''
    data_dir = tmp_path / 'data'
    shutil.copytree(built.data_dir, data_dir, symlinks=True)
    directory = run_directory(data_dir, RUN)
    change(directory)
    target_io.write_json(directory / 'outputs.json', target_io.inventory(directory, list(FILES)))
    return data_dir, manifest.sha256_file(directory / 'outputs.json')


def edit_row(table: str, where: Callable[[dict], bool], change: Callable[[dict], None]):
    '''Change the first row of a bundle table for which `where` holds, keeping the schema.'''
    def apply(directory: Path) -> None:
        file = directory / f'{table}.parquet'
        frame = pl.read_parquet(file)
        rows = frame.to_dicts()
        change(next(row for row in rows if where(row)))
        pl.DataFrame(rows, schema=frame.schema).write_parquet(file)
    return apply


def edit_report(change: Callable[[dict], None]):
    def apply(directory: Path) -> None:
        report = json.loads((directory / 'report.json').read_text())
        change(report)
        target_io.write_json(directory / 'report.json', report)
    return apply


def add(column: str, amount):
    def change(row: dict) -> None:
        row[column] += amount
    return change


def put(column: str, value):
    def change(row: dict) -> None:
        row[column] = value
    return change


def drop_last(column: str):
    def change(row: dict) -> None:
        row[column] = row[column][:-1]
    return change


def bump_report(*keys: str):
    '''Add one to the report value at `keys`; the first key of a dict when a key is None.'''
    def change(report: dict) -> None:
        document = report
        for key in keys[:-1]:
            document = document[next(iter(document)) if key is None else key]
        document[keys[-1]] += 1
    return edit_report(change)


def both(*changes: Callable[[Path], None]) -> Callable[[Path], None]:
    '''Apply each bundle change in turn.'''
    def apply(directory: Path) -> None:
        for change in changes:
            change(directory)
    return apply


def topic(name: str, reason: str | None = None) -> Callable[[dict], bool]:
    return lambda row: row['topic'] == name and reason in (None, row['reason'])


MONTHLY = ('monthly_ee:strict', 'monthly_ee:sensitivity', 'monthly_ue:strict',
           'monthly_ue:sensitivity')
ASEC = 'asec_retro:sensitivity'


def is_x(row: dict) -> bool:
    return 'x_residual' in row['membership_types']


# Each mutation: the check it must break, and the change to one bundle file.
MUTATIONS = {
    # targets: the target rows and the support rows of the point estimates.
    'average_total_value': ('targets', edit_row(
        'cps_job_flows', lambda row: row['measure'] == 'average_total', add('value', 1.0))),
    'forward_share_value': ('targets', edit_row(
        'cps_job_flows', lambda row: row['measure'] == 'forward_share', add('value', -0.25))),
    'n_unweighted': ('targets', edit_row(
        'cps_job_flows', lambda row: row['universe'] == ASEC, add('n_unweighted', 1))),
    'n_weighted': ('targets', edit_row(
        'cps_job_flows', lambda row: row['measure'] == 'forward_share',
        add('n_weighted', 1.0))),
    'flags': ('targets', edit_row(
        'cps_job_flows', lambda row: row['universe'] in MONTHLY,
        put('flags', ['size_gate_pending']))),
    'bootstrap_se_method': ('targets', edit_row(
        'cps_job_flows', lambda row: row['se_method'] == 'bootstrap',
        put('se_method', 'none'))),
    'support_cell_mass': ('targets', edit_row(
        'cps_flow_support', lambda row: row['kind'] == 'cell', add('mass', 1.0))),
    'support_denominator_count': ('targets', edit_row(
        'cps_flow_support', lambda row: row['kind'] == 'denominator',
        add('n_unweighted', 1))),
    # guards: the two guard columns, the guard counts and the usable-guard shares.
    'guard_industry': ('guards', edit_row(
        'cps_linked_pairs', lambda row: row['guard_industry'] == 'changed',
        put('guard_industry', 'same'))),
    'guard_occupation': ('guards', edit_row(
        'cps_linked_pairs', lambda row: row['guard_occupation'] == 'unusable',
        put('guard_occupation', 'same'))),
    'guard_count': ('guards', edit_row(
        'cps_flow_diagnostics', topic('guard', 'changed'), add('count', 1))),
    'noise_after_duty_change': ('guards', edit_row(
        'cps_flow_diagnostics', topic('guard', 'noise_after_duty_change'), add('count', 1))),
    'usable_guard_share': ('guards', edit_report(
        lambda report: report['usable_guard_share'].update({'monthly_ee:industry': 0.5}))),
    # The source exceptions: panel rows in MISH 1 or 5 with EMPSAME 1 or 2 (controller ruling).
    'source_exception_row': ('guards', edit_row(
        'cps_flow_diagnostics', topic('guard', SOURCE_EXCEPTION), add('count', 1))),
    'source_exception_report': ('guards', bump_report('guard_source_exceptions',
                                                      SOURCE_EXCEPTION)),
    # A count of links, not rows, gives 0: no one-month link has MISH 1 or 5 at its later month.
    'source_exception_as_links': ('guards', both(
        edit_row('cps_flow_diagnostics', topic('guard', SOURCE_EXCEPTION), put('count', 0)),
        edit_report(lambda report: report['guard_source_exceptions'].update(
            {SOURCE_EXCEPTION: 0})))),
    # x_residuals: the occupation registry rows and the cross-check counts.
    'x_candidate': ('x_residuals', edit_row(
        'cps_category_units', is_x, drop_last('candidates'))),
    'x_candidate_node_ids': ('x_residuals', edit_row(
        'cps_category_units', is_x, drop_last('candidate_node_ids'))),
    'x_cross_check': ('x_residuals', edit_row(
        'cps_category_units', lambda row: row['x_cross_check'] == 'strict_subset',
        put('x_cross_check', 'equal'))),
    'claimed_soc_candidates': ('x_residuals', edit_row(
        'cps_category_units', lambda row: row['code'] == '0020'
        and row['unit_type'] == 'cps_occupation_category', drop_last('candidates'))),
    'x_categories': ('x_residuals', bump_report('x_categories', 'equal')),
    # links: the linked pairs, the link and weight counts.
    'link_type': ('links', edit_row(
        'cps_linked_pairs', lambda row: row['link_type'] == 'one_month',
        put('link_type', 'two_month'))),
    'source_row': ('links', edit_row(
        'cps_linked_pairs', lambda row: True, add('source_row_b', 1))),
    'weight_a': ('links', edit_row(
        'cps_linked_pairs', lambda row: row['weight_status'] == 'positive',
        add('weight_a', 0.0001))),
    'links_count': ('links', edit_row(
        'cps_flow_diagnostics', topic('links'), add('count', 1))),
    'weight_count': ('links', edit_row(
        'cps_flow_diagnostics', topic('weight'), add('count', 1))),
    'report_linkage': ('links', bump_report('linkage', 'one_month', None, 'cpsidv')),
    'report_weights': ('links', bump_report('weights', 'positive')),
    # asec_se: the ASEC SEs, their methods and their replicate rows.
    'asec_se': ('asec_se', edit_row(
        'cps_job_flows', lambda row: row['universe'] == ASEC and row['se'] is not None,
        add('se', 1.0))),
    'asec_se_method': ('asec_se', edit_row(
        'cps_job_flows', lambda row: row['universe'] == ASEC and row['se'] is not None,
        put('se_method', 'none'))),
    'asec_replicate': ('asec_se', edit_row(
        'cps_flow_replicates', lambda row: row['product'] == 'asec_retro',
        add('numerator', 1.0))),
    'asec_replicate_status': ('asec_se', edit_row(
        'cps_flow_replicates', lambda row: row['product'] == 'asec_retro',
        put('status', 'denominator_nonpositive'))),
    # value_classes: class counts, specials, the V11 summary and the registry.
    'value_class_count': ('value_classes', bump_report('value_classes', 'monthly/IND',
                                                       'mapped')),
    'value_class_diagnostics': ('value_classes', edit_row(
        'cps_flow_diagnostics', topic('value_class'), add('count', 1))),
    'specials': ('value_classes', bump_report('specials', 'monthly/IND/2025')),
    'v11': ('value_classes', bump_report('v11', 'unparseable_values')),
    'registry_status': ('value_classes', edit_row(
        'cps_category_units', lambda row: row['status'] == 'no_naics_equivalent',
        put('status', 'mapped'))),
    'special_label': ('value_classes', edit_row(
        'cps_category_units', lambda row: row['status'] == 'special_military',
        put('label', 'Military'))),
    # eligibility: the funnels and each link's products.
    'funnel_count': ('eligibility', edit_row(
        'cps_flow_diagnostics', topic('funnel'), add('count', 1))),
    'report_funnels': ('eligibility', bump_report('funnels', 'asec_retro:industry',
                                                  'eligible')),
    'products': ('eligibility', edit_row(
        'cps_linked_pairs', lambda row: bool(row['products']), put('products', []))),
}


# Plan tests.

def test_script_imports_no_embedding_data_module():
    tree = ast.parse(SCRIPT.read_text())
    assert not [node for node in ast.walk(tree)
                if isinstance(node, (ast.Import, ast.ImportFrom))
                and 'embedding_data' in ast.unparse(node)]


def test_reconciler_is_equal_on_a_seeded_build(built):
    status, result = result_of(built.data_dir, built.pin)
    assert result == {'checks': dict.fromkeys(CHECKS, True), 'equal': True}
    assert status == 0


@pytest.mark.parametrize('name', MUTATIONS)
def test_each_check_detects_its_mutation(built, tmp_path, name):
    check, change = MUTATIONS[name]
    data_dir, pin = tampered(built, tmp_path, change)
    status, result = result_of(data_dir, pin)
    assert result['checks'] == {other: other != check for other in CHECKS}
    assert result['equal'] is False
    assert status == 1


def test_a_changed_bootstrap_se_leaves_the_result_equal(built, tmp_path):
    data_dir, pin = tampered(built, tmp_path, edit_row(
        'cps_job_flows', lambda row: row['se_method'] == 'bootstrap', add('se', 1.0)))
    status, result = result_of(data_dir, pin)
    assert result == {'checks': dict.fromkeys(CHECKS, True), 'equal': True}
    assert status == 0


def test_exit_codes_for_equal_unequal_and_error(built, tmp_path):
    assert result_of(built.data_dir, built.pin)[0] == 0
    data_dir, pin = tampered(built, tmp_path, MUTATIONS['average_total_value'][1])
    assert result_of(data_dir, pin)[0] == 1
    refusals = {
        'detached pin differs': (built.data_dir, '0' * 64, RUN),
        'bundle is missing': (built.data_dir, built.pin, 'absent_run'),
        'malformed pin': (built.data_dir, 'not-a-pin', RUN),
        'unsafe run id': (built.data_dir, built.pin, '../first'),
        'data directory is missing': (tmp_path / 'absent', built.pin, RUN),
    }
    for reason, (root, pin, run_id) in refusals.items():
        assert run(root, pin, run_id) == (2, '', FAILURE + reason + '\n')


# Refusals of untrusted inputs.

def delivery_file(data_dir: Path, set_name: str, suffix: str) -> Path:
    return data_dir / 'raw/cps' / set_name / f'cps_0000{1 if set_name == "monthly" else 2}' / (
        f'cps_0000{1 if set_name == "monthly" else 2}{suffix}')


@pytest.mark.parametrize('target', ['monthly_csv', 'asec_ddi', 'soc_nodes', 'occupation_list'])
def test_a_changed_upstream_file_is_refused(built, tmp_path, target):
    data_dir = tmp_path / 'data'
    shutil.copytree(built.data_dir, data_dir, symlinks=True)
    files = {
        'monthly_csv': delivery_file(data_dir, 'monthly', '.csv.gz'),
        'asec_ddi': delivery_file(data_dir, 'asec', '.xml'),
        'soc_nodes': data_dir / 'derived/codes/stage4_fixture_codes/soc_nodes.parquet',
        'occupation_list': next((data_dir / 'raw/references/acs-mapping').rglob('*.xlsx')),
    }
    with files[target].open('ab') as stream:
        stream.write(b'\0')
    status, out, err = run(data_dir, built.pin)
    assert (status, out) == (2, '')
    assert err.startswith(FAILURE) and err.count('\n') == 1


def test_an_unexpected_error_prints_a_fixed_reason_and_no_text(built, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError(f'row content {JOB_FLOW_CPSIDV + 1}')

    monkeypatch.setattr(load_script(), 'monthly_panel', fail)
    assert run(built.data_dir, built.pin) == (2, '', FAILURE + 'unexpected\n')


# The undefined replicate share, and reasons that count zero.

def test_reconciler_is_equal_with_a_nonpositive_replicate_denominator(negative_replicate):
    directory = negative_replicate.directory
    targets = pl.read_parquet(directory / 'cps_job_flows.parquet')
    undefined = targets.filter(pl.col('universe') == 'asec_retro:sensitivity',
                               pl.col('measure') == 'forward_share', pl.col('se').is_null())
    assert undefined.height == 2
    assert set(undefined['se_method']) == {'none'}
    report = json.loads((directory / 'report.json').read_text())
    assert report['weights']['null'] == 0
    status, result = result_of(negative_replicate.data_dir, negative_replicate.pin)
    assert result == {'checks': dict.fromkeys(CHECKS, True), 'equal': True}
    assert status == 0


def test_a_changed_undefined_replicate_list_is_detected(negative_replicate, tmp_path):
    data_dir, pin = tampered(negative_replicate, tmp_path, edit_row(
        'cps_flow_support', lambda row: row['product'] == 'asec_retro'
        and row['kind'] == 'undefined_share', put('replicates', [7, 8])))
    status, result = result_of(data_dir, pin)
    assert result['checks'] == {other: other != 'asec_se' for other in CHECKS}
    assert status == 1


# The guard source exceptions: monthly panel rows, not links (controller ruling, 2026-11-24).

def test_source_exceptions_count_substantive_empsame_in_mish_1_or_5():
    panel = pl.DataFrame({'MISH': [1, 5, 1, 5, 2, 4, 6, 8, 1, 5],
                          'EMPSAME': [1, 2, 96, 97, 1, 2, 1, 2, None, 99]})
    assert reconcile.source_exceptions(panel) == 2


# Earlier-month rows in MISH 1 or 5 that a count of links would miss or that the value set
# leaves out. The seeded case already has one linked MISH 1 row and one unlinked MISH 5 row.
SOURCE_EXCEPTION_CHANGES = {
    'U4': {'CPSIDV': JOB_FLOW_CPSIDV + 900, 'EMPSAME': 2},  # MISH 1, its own CPSIDV: no link
    'U1': {'EMPSAME': 1},  # MISH 1, unemployed at the earlier month: a row all the same
    'L1': {'EMPSAME': 2},  # MISH 1, the earlier row of the two-month link
    'E15': {'EMPSAME': 1},  # MISH 5, the earlier row of a 2026 one-month link
    'U2': {'EMPSAME': 97},  # MISH 1, not a substantive answer
}


def test_source_exceptions_count_panel_rows_not_links(tmp_path):
    variant = seeded_build(tmp_path, SOURCE_EXCEPTION_CHANGES)
    status, result = result_of(variant.data_dir, variant.pin)
    assert result == {'checks': dict.fromkeys(CHECKS, True), 'equal': True}
    assert status == 0
    diagnostics = pl.read_parquet(variant.directory / 'cps_flow_diagnostics.parquet')
    published = diagnostics.filter(pl.col('topic') == 'guard',
                                   pl.col('reason') == SOURCE_EXCEPTION)['count'].to_list()
    report = json.loads((variant.directory / 'report.json').read_text())
    assert published == [report['guard_source_exceptions'][SOURCE_EXCEPTION]] == [6]
    pairs = pl.read_parquet(variant.directory / 'cps_linked_pairs.parquet')
    assert pairs.filter(pl.col('mish_b').is_in([1, 5])).height == 0
    data_dir, pin = tampered(variant, tmp_path / 'tampered', MUTATIONS['source_exception_row'][1])
    status, result = result_of(data_dir, pin)
    assert result['checks'] == {other: other != 'guards' for other in CHECKS}
    assert status == 1


# The V12 chain: the committed full Census lists, the full Stage 4 trees and real Stage 7 and 8
# bundles.

@pytest.mark.slow
def test_reconciler_is_equal_on_both_v12_chain_bundles(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    result = run_cps_flow_v12(data_dir, monkeypatch)
    units = pl.read_parquet(Path(result['first']['directory']) / 'cps_category_units.parquet')
    x_rows = units.filter(pl.col('membership_types').list.contains('x_residual'))
    assert x_rows.height == 38
    for key in V12_RUNS:
        status, checks = result_of(data_dir, result[key]['outputs_sha256'], V12_RUNS[key])
        assert checks == {'checks': dict.fromkeys(CHECKS, True), 'equal': True}
        assert status == 0
    assert result['external_access_counts'] == {'network': 0, 'environment_file': 0,
                                                'live_client': 0}


# The program, its imports and its output.

def test_the_script_runs_as_a_program(built):
    done = subprocess.run(
        [sys.executable, str(SCRIPT), '--data-dir', str(built.data_dir), '--run', RUN,
         '--outputs-sha256', built.pin], capture_output=True, text=True, check=False)
    assert done.returncode == 0
    assert json.loads(done.stdout) == {'checks': dict.fromkeys(CHECKS, True), 'equal': True}
    assert done.stderr == ''


def test_script_imports_only_the_standard_library_polars_and_fastexcel():
    tree = ast.parse(SCRIPT.read_text())
    modules = {alias.name.split('.')[0] for node in ast.walk(tree)
               if isinstance(node, ast.Import) for alias in node.names}
    modules |= {node.module.split('.')[0] for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)}
    assert modules - set(sys.stdlib_module_names) == {'polars', 'fastexcel'}


def test_loading_the_script_imports_no_embedding_data_module():
    code = ('import importlib.util, json, sys\n'
            f'spec = importlib.util.spec_from_file_location("reconcile", {str(SCRIPT)!r})\n'
            'spec.loader.exec_module(importlib.util.module_from_spec(spec))\n'
            'print(json.dumps(sorted(m for m in sys.modules if "embedding_data" in m)))\n')
    done = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
                          check=True)
    assert json.loads(done.stdout) == []


def test_the_output_line_holds_no_identifier(built):
    status, out, _ = run(built.data_dir, built.pin)
    assert status == 0
    for number in (JOB_FLOW_CPSIDV, JOB_FLOW_CPSID):
        assert str(number)[:6] not in out
