'''The independent Stage 10 reconciler, on the V12 fixture bundle and on small typed rows.'''

import ast
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest
from ita_establishment_fixtures import run_establishment_v12

from embedding_data import ita_verification, manifest, target_io
from embedding_data.ita_establishment_bundle import FILES

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'reconcile_stage10.py'
FORBIDDEN = {'ita_co_ownership', 'ita_area_mix', 'ita_establishment_records',
             'ita_establishment_links', 'ita_text_pairs'}
NODE = 'naics:2022:national_industry:'
FIXTURE_EINS = ('012345678', '123456789', '23456789', '023456789', '345678912')


def load_script():
    assert SCRIPT.is_file(), 'independent reconciler is missing'
    spec = importlib.util.spec_from_file_location('reconcile_stage10', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def chain(tmp_path_factory):
    '''One V12 chain for the module. External access stays blocked while its tests run.'''
    with pytest.MonkeyPatch.context() as monkeypatch:
        yield run_establishment_v12(tmp_path_factory.mktemp('reconcile'), monkeypatch)


@pytest.fixture
def script():
    return load_script()


def reconcile(script, capsys, check, chain, directory=None, pin=None):
    '''Run one subcommand and return its status, its single JSON line and that line parsed.'''
    directory = directory or chain['first']
    status = script.main([check, '--data-dir', str(chain['data_dir']), '--run', directory.name,
                          '--outputs-sha256', pin or chain['first_pin']])
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    return status, lines[0], json.loads(lines[0])


def tampered_copy(chain, name, change):
    '''A copy of the first bundle under a new run name, changed, with a fresh inventory pin.'''
    directory = chain['first'].parent / name
    shutil.copytree(chain['first'], directory)
    change(directory)
    target_io.write_json(directory / 'outputs.json', target_io.inventory(directory, list(FILES)))
    return directory, manifest.sha256_file(directory / 'outputs.json')


def edit_json(name, change):
    def apply(directory):
        value = json.loads((directory / name).read_text())
        change(value)
        target_io.write_json(directory / name, value)
    return apply


def bump_first(name, column):
    def apply(directory):
        file = directory / (name + '.parquet')
        frame = pl.read_parquet(file)
        frame.with_columns(
            pl.when(pl.int_range(pl.len()).eq(0)).then(pl.col(column).add(1))
            .otherwise(pl.col(column)).cast(frame.schema[column]).alias(column)
        ).write_parquet(file)
    return apply


def row(script, **changes):
    '''One canonical row in the script's column order: an eligible record unless changed.'''
    record = {
        'year_filing_for': 2023,
        'ein': '123456789',
        'naics_mapping_status': 'native_2022',
        'naics_2022_node_id': NODE + '238220',
        'flag_naics_crosswalked': False,
        'flag_naics_ambiguous': False,
        'flag_naics_unresolved': False,
        **changes,
    }
    return tuple(record[column] for column in script.COLUMNS)


def test_reconcile_co_ownership_matches_fixture(script, chain, capsys):
    status, line, result = reconcile(script, capsys, 'co-ownership', chain)
    assert status == 0
    assert result['equal'] is True
    assert result['N_equal'] and result['marginals_equal'] and result['cells_equal']
    report = json.loads((chain['first'] / 'report.json').read_text())
    assert result['N'] == {'bundle': report['co_ownership']['N'],
                           'independent': report['co_ownership']['N']}
    assert result['N']['independent'] > 0
    targets = pl.read_parquet(chain['first'] / 'ita_co_ownership.parquet')
    assert result['n_cells'] == {'bundle': targets.height, 'independent': targets.height}
    assert targets.height > 0


def test_reconcile_detects_difference(script, chain, capsys, monkeypatch):
    real = script.read_canonical
    dropped = []

    def drop_one(file):
        for values in real(file):
            named = dict(zip(script.COLUMNS, values, strict=True))
            if (not dropped and named['ein'] == '123456789' and named['year_filing_for'] == 2023
                    and named['naics_2022_node_id'] == NODE + '238220'):
                dropped.append(values)
                continue
            yield values

    monkeypatch.setattr(script, 'read_canonical', drop_one)
    status, line, result = reconcile(script, capsys, 'co-ownership', chain)
    assert len(dropped) == 1
    assert status == 1
    assert result['equal'] is False
    assert result['cells_equal'] is False
    assert result['marginals_equal'] is False
    assert not any(ein in line for ein in FIXTURE_EINS)


def test_reconcile_stage3_matches_fixture(script, chain, capsys):
    status, line, result = reconcile(script, capsys, 'stage3', chain)
    assert status == 0
    assert result == {'check': 'stage3', 'run': chain['first'].name, 'equal': True,
                      'v1_equal': True, 'v2_equal': True, 'v1_differences': [],
                      'v2_differences': []}


def test_reconciler_is_independent():
    tree = ast.parse(SCRIPT.read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or '')
            imported.update(f'{node.module}.{alias.name}' for alias in node.names)
    assert imported
    assert not {part for name in imported for part in name.split('.')} & FORBIDDEN


# Additional coverage beyond the plan tests.

def test_reconciler_loads_no_stage10_builder():
    code = '\n'.join([
        'import importlib.util, json, sys',
        'spec = importlib.util.spec_from_file_location("reconcile_stage10", sys.argv[1])',
        'spec.loader.exec_module(importlib.util.module_from_spec(spec))',
        'print(json.dumps(sorted(name for name in sys.modules)))',
    ])
    completed = subprocess.run([sys.executable, '-c', code, str(SCRIPT)], capture_output=True,
                               text=True, check=True)
    loaded = set(json.loads(completed.stdout))
    assert 'embedding_data.ita_verification' in loaded
    assert not {f'embedding_data.{name}' for name in FORBIDDEN} & loaded


EIN_CASES = {
    'nine_digits': ('123456789', ('123456789', False)),
    'edge_whitespace': (' 123456789\t', ('123456789', False)),
    'hyphen': ('12-3456789', ('123456789', False)),
    'eight_digits_padded': ('23456789', ('023456789', True)),
    'eight_digits_hyphen_and_spaces': (' 2-3456789 ', ('023456789', True)),
    'zero_filled_then_same_digit_test': ('11111111', ('011111111', True)),
    'seven_digits': ('1234567', None),
    'ten_digits': ('1234567890', None),
    'trailing_letter': ('12345678A', None),
    'leading_letter': ('A12345678', None),
    'inner_space': ('1234 56789', None),
    'fullwidth_digits': ('１２３４５６７８９', None),
    'empty': ('', None),
    'blank': ('   ', None),
    'null': (None, None),
    'same_digit': ('999999999', None),
    'zero_filled_same_digit': ('00000000', None),
}


@pytest.mark.parametrize('case', EIN_CASES)
def test_ein_normalization(script, case):
    value, expected = EIN_CASES[case]
    assert script.normalize_ein(value) == expected


ELIGIBILITY_CASES = {
    'year_2023': ({}, '123456789'),
    'year_2024': ({'year_filing_for': 2024}, '123456789'),
    'year_2025': ({'year_filing_for': 2025}, '123456789'),
    'hyphenated_ein': ({'ein': '12-3456789'}, '123456789'),
    'year_2022': ({'year_filing_for': 2022}, None),
    'year_2026': ({'year_filing_for': 2026}, None),
    'status_concorded': ({'naics_mapping_status': 'concorded'}, None),
    'null_node': ({'naics_2022_node_id': None}, None),
    'crosswalked': ({'flag_naics_crosswalked': True}, None),
    'crosswalked_null': ({'flag_naics_crosswalked': None}, None),
    'ambiguous': ({'flag_naics_ambiguous': True}, None),
    'ambiguous_null': ({'flag_naics_ambiguous': None}, None),
    'unresolved': ({'flag_naics_unresolved': True}, None),
    'unresolved_null': ({'flag_naics_unresolved': None}, None),
    'padded_ein': ({'ein': '23456789'}, None),
    'unusable_ein': ({'ein': ''}, None),
    'null_ein': ({'ein': None}, None),
    'same_digit_ein': ({'ein': '999999999'}, None),
}


@pytest.mark.parametrize('case', ELIGIBILITY_CASES)
def test_eligibility(script, case):
    changes, expected = ELIGIBILITY_CASES[case]
    assert script.eligible_employer(row(script, **changes)) == expected


def test_counts_follow_the_estimand(script):
    a, b, c = NODE + '238220', NODE + '722511', NODE + '332312'
    rows = [
        # Employer 1: a and b in 2023, a again in 2024. One count each in n(a), n(b) and J.
        row(script, ein='100000001', naics_2022_node_id=a),
        row(script, ein='100000001', naics_2022_node_id=b),
        row(script, ein='100000001', naics_2022_node_id=a, year_filing_for=2024),
        # Employer 2: a and b together in 2023 and in 2024. Still one count in J(a,b).
        row(script, ein='100000002', naics_2022_node_id=a),
        row(script, ein='100000002', naics_2022_node_id=b),
        row(script, ein='100000002', naics_2022_node_id=a, year_filing_for=2024),
        row(script, ein='100000002', naics_2022_node_id=b, year_filing_for=2024),
        # Employer 3: a in 2023 and c in 2024 only, so no same-year co-presence.
        row(script, ein='100000003', naics_2022_node_id=a),
        row(script, ein='100000003', naics_2022_node_id=c, year_filing_for=2024),
        # Employer 4: one industry filed twice, once under a hyphenated EIN.
        row(script, ein='100000004', naics_2022_node_id=c),
        row(script, ein='10-0000004', naics_2022_node_id=c),
        # A padded EIN and an ineligible record add nothing.
        row(script, ein='10000005', naics_2022_node_id=a),
        row(script, ein='10000005', naics_2022_node_id=c),
        row(script, ein='100000003', naics_2022_node_id=c, flag_naics_crosswalked=True),
    ]
    employers, marginals, cells = script.count(rows)
    assert employers == 4
    assert marginals == {a: 3, b: 2, c: 2}
    assert cells == {(a, b): 2, (b, a): 2}


BUNDLE_CASES = {
    'report_N': (edit_json('report.json', lambda report: report['co_ownership'].update(
        N=report['co_ownership']['N'] + 1)), 'N_equal'),
    'marginal': (bump_first('co_ownership_marginals', 'n_employers'), 'marginals_equal'),
    'cell': (bump_first('ita_co_ownership', 'n_unweighted'), 'cells_equal'),
}


@pytest.mark.parametrize('case', BUNDLE_CASES)
def test_reconcile_detects_bundle_difference(script, chain, capsys, case):
    change, flag = BUNDLE_CASES[case]
    directory, pin = tampered_copy(chain, 'bundle_' + case, change)
    status, line, result = reconcile(script, capsys, 'co-ownership', chain, directory, pin)
    assert status == 1
    assert result['equal'] is False
    assert result[flag] is False
    assert sum(not result[name] for name in ('N_equal', 'marginals_equal', 'cells_equal')) == 1


@pytest.mark.parametrize('check', ['co-ownership', 'stage3'])
def test_reconcile_refuses_wrong_pin_before_reading(script, chain, capsys, monkeypatch, check):
    def forbidden(*args, **kwargs):
        raise AssertionError('a bundle input was read before the pin was checked')

    monkeypatch.setattr(script, 'read_canonical', forbidden)
    monkeypatch.setattr(ita_verification, 'description_report', forbidden)
    monkeypatch.setattr(ita_verification, 'link_report', forbidden)
    status, line, result = reconcile(script, capsys, check, chain, pin='0' * 64)
    assert status == 1
    assert result == {'check': check, 'run': chain['first'].name, 'equal': False,
                      'reason': 'detached pin differs'}


def change_unpinned_report(directory):
    (directory / 'report.json').write_text(
        (directory / 'report.json').read_text().replace('"pending"', '"changed"'))


def unpinned_copy(chain, name):
    directory = chain['first'].parent / name
    shutil.copytree(chain['first'], directory)
    change_unpinned_report(directory)
    return directory, chain['first_pin']


SELECTION_CASES = {
    'co-ownership_unpinned_report': ('co-ownership', unpinned_copy,
                                     'bundle file differs from its inventory'),
    'stage3_unpinned_report': ('stage3', unpinned_copy, 'bundle file differs from its inventory'),
    'co-ownership_canonical': ('co-ownership', lambda chain, name: tampered_copy(
        chain, name, edit_json('inputs.json', lambda inputs: inputs['canonical'].update(
            sha256='0' * 64))), 'selected table differs from inputs.json'),
    'stage3_summary': ('stage3', lambda chain, name: tampered_copy(
        chain, name, edit_json('inputs.json', lambda inputs: inputs['source_parquet'].update(
            sha256='0' * 64))), 'selected table differs from inputs.json'),
}


@pytest.mark.parametrize('case', SELECTION_CASES)
def test_reconcile_refuses_unauthenticated_inputs(script, chain, capsys, case):
    check, prepare, reason = SELECTION_CASES[case]
    directory, pin = prepare(chain, 'selection_' + case)
    status, line, result = reconcile(script, capsys, check, chain, directory, pin)
    assert status == 1
    assert result == {'check': check, 'run': directory.name, 'equal': False, 'reason': reason}


def test_reconcile_stage3_detects_v1_difference(script, chain, capsys, monkeypatch):
    real = ita_verification.description_report

    def bumped(summary, titles):
        frame = real(summary, titles)
        return frame.with_columns(
            pl.when(pl.col('year_filing_for').eq(2023)).then(pl.col('n_repeat_excess').add(1))
            .otherwise(pl.col('n_repeat_excess')).alias('n_repeat_excess'))

    monkeypatch.setattr(ita_verification, 'description_report', bumped)
    status, line, result = reconcile(script, capsys, 'stage3', chain)
    assert status == 1
    assert result['v1_equal'] is False
    assert result['v2_equal'] is True
    assert result['v1_differences'] == [[2023, 'n_repeat_excess']]


def test_reconcile_stage3_detects_v2_difference(script, chain, capsys, monkeypatch):
    real = ita_verification.link_report

    def bumped(summary, base, later):
        counts = dict(real(summary, base, later))
        # The one pair that is not consecutive.
        if (base, later) == (2023, 2025):
            counts['n_address_matches_different_id'] += 1
        return counts

    monkeypatch.setattr(ita_verification, 'link_report', bumped)
    status, line, result = reconcile(script, capsys, 'stage3', chain)
    assert status == 1
    assert result['v1_equal'] is True
    assert result['v2_equal'] is False
    assert result['v2_differences'] == [['2023-2025', 'n_address_matches_different_id']]


@pytest.mark.parametrize(('pinned', 'expected'), [(True, 0), (False, 1)])
def test_script_exit_status(chain, pinned, expected):
    pin = chain['first_pin'] if pinned else '0' * 64
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), 'co-ownership', '--data-dir', str(chain['data_dir']),
         '--run', chain['first'].name, '--outputs-sha256', pin],
        capture_output=True, text=True)
    assert completed.returncode == expected
    lines = completed.stdout.splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])['equal'] is (expected == 0)
