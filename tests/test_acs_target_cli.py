'''Offline standalone Stage9 command contract.'''

import json
from dataclasses import asdict
from pathlib import Path

import pytest
from typer.testing import CliRunner

from embedding_data.acs_mapping_contract import SelectionRequest

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    from acs_mapping_fixtures import forbid_external_access

    forbid_external_access(monkeypatch)


def options(tmp_path):
    return {'--data-dir': str(tmp_path), '--mapping-run': 'mapping',
            '--mapping-outputs-sha256': '1' * 64}


def build_options(tmp_path):
    return options(tmp_path) | {
        '--codes-run': 'codes', '--codes-outputs-sha256': '2' * 64,
        '--geography-run': 'geography', '--geography-outputs-sha256': '3' * 64,
        '--ipums-run': 'ipums', '--ipums-outputs-sha256': '4' * 64,
        '--ipums-references-sha256': '5' * 64}


def invoke(command, arguments, opts):
    from embedding_data.acs_targets import app

    return CliRunner().invoke(app, [command, *arguments,
        *[item for pair in opts.items() for item in pair]])


def test_exact_help_surface_and_frozen_top_level():
    import hashlib

    from embedding_data.acs_targets import app

    assert {command.name for command in app.registered_commands} == {
        'build', 'verify', 'compare-runs'}
    result = CliRunner().invoke(app, ['--help'])
    assert result.exit_code == 0
    assert all(name in result.stdout for name in ('build', 'verify', 'compare-runs'))
    file = Path(__file__).parents[1] / 'src/embedding_data/cli.py'
    assert hashlib.sha256(file.read_bytes()).hexdigest() == (
        '32a86b3d07bf112fabc1edb01fd10a966e840c185642e55d00f35dfd435220b3')


@pytest.mark.parametrize('command,arguments', [
    ('build', ['run']), ('verify', ['run']), ('compare-runs', ['one', 'two'])])
def test_each_required_option_fails_before_work(tmp_path, monkeypatch, command, arguments):
    from embedding_data import acs_target_bundle as bundle

    def forbidden(*args, **kwargs):
        pytest.fail('missing explicit option reached bundle work')

    for name in ('build', 'verify_bundle', 'compare_runs', 'run_directory'):
        monkeypatch.setattr(bundle, name, forbidden)
    opts = build_options(tmp_path) if command == 'build' else options(tmp_path)
    if command == 'verify':
        opts['--outputs-sha256'] = '6' * 64
    for missing in opts:
        result = invoke(command, arguments, {k: v for k, v in opts.items() if k != missing})
        assert result.exit_code == 2, (missing, result.output)


def test_build_forwards_complete_request(tmp_path, monkeypatch):
    from embedding_data import acs_target_bundle as bundle

    received = {}

    def build(data_dir, run_id, mapping_run, **kwargs):
        received.update(data_dir=data_dir, run_id=run_id, mapping_run=mapping_run, **kwargs)
        return {'run_id': run_id, 'outputs_sha256': '6' * 64}

    monkeypatch.setattr(bundle, 'build', build)
    result = invoke('build', ['run'], build_options(tmp_path))
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)['outputs_sha256'] == '6' * 64
    assert received == {'data_dir': tmp_path, 'run_id': 'run', 'mapping_run': 'mapping',
        'expected_mapping_outputs_sha256': '1' * 64,
        'request': SelectionRequest('codes', '2' * 64, 'geography', '3' * 64,
                                    'ipums', '4' * 64, '5' * 64)}
    assert len(asdict(received['request'])) == 7


def test_verify_forwards_detached_and_mapping_pins(tmp_path, monkeypatch):
    from embedding_data import acs_target_bundle as bundle

    received = {}

    def verify(directory, data_dir, **kwargs):
        received.update(directory=directory, data_dir=data_dir, **kwargs)
        return {'status': 'verified'}

    monkeypatch.setattr(bundle, 'verify_bundle', verify)
    result = invoke('verify', ['run'], options(tmp_path) | {'--outputs-sha256': '6' * 64})
    assert result.exit_code == 0, result.output
    assert received == {'directory': bundle.run_directory(tmp_path, 'run'), 'data_dir': tmp_path,
        'mapping_run': 'mapping', 'expected_mapping_outputs_sha256': '1' * 64,
        'expected_outputs_sha256': '6' * 64}


@pytest.mark.parametrize('tables_equal,report_equal', [(True, True), (False, True),
                                                     (True, False)])
def test_compare_forwards_identity_and_exit_status(tmp_path, monkeypatch, tables_equal,
                                                   report_equal):
    from embedding_data import acs_target_bundle as bundle

    equal = tables_equal and report_equal

    def compare(first, second, **kwargs):
        assert first == bundle.run_directory(tmp_path, 'one')
        assert second == bundle.run_directory(tmp_path, 'two')
        assert kwargs == {'data_dir': tmp_path, 'mapping_run': 'mapping',
                          'expected_mapping_outputs_sha256': '1' * 64}
        return {'equal': equal, 'tables': {'targets_observed': {
            'values_equal': tables_equal, 'schema_equal': True}},
            'substantive_report_equal': report_equal}

    monkeypatch.setattr(bundle, 'compare_runs', compare)
    result = invoke('compare-runs', ['one', 'two'], options(tmp_path))
    assert result.exit_code == (0 if equal else 1), result.output
    assert json.loads(result.stdout)['equal'] is equal


@pytest.mark.parametrize('command,operation,arguments', [
    ('build', 'build', ['run']), ('verify', 'verify_bundle', ['run']),
    ('compare-runs', 'compare_runs', ['one', 'two'])])
def test_errors_have_fixed_safe_diagnostic(tmp_path, monkeypatch, command, operation, arguments):
    from embedding_data import acs_target_bundle as bundle

    def fail(*args, **kwargs):
        raise ValueError('PRIVATE_PERSON_VALUE')

    monkeypatch.setattr(bundle, operation, fail)
    opts = build_options(tmp_path) if command == 'build' else options(tmp_path)
    if command == 'verify':
        opts['--outputs-sha256'] = '6' * 64
    result = invoke(command, arguments, opts)
    assert result.exit_code == 2
    assert result.output.strip() == 'ACS target validation failed.'
