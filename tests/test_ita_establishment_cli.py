'''The Stage 10 command group: its surface, argument wiring, exit codes and failure line.'''

import json
import subprocess
import sys

import httpx
import polars as pl
import pytest
from target_fixtures import forbid_external_access
from typer.main import get_command

from embedding_data import (
    code_build,
    geography_build,
    ita_establishment_bundle,
    ita_establishment_targets,
    ita_index_references,
    ita_summary,
    osha_benchmark_download,
)
from embedding_data.ita_establishment_targets import app

COMMANDS = ('acquire-references', 'import-reference', 'build', 'verify', 'compare-runs')
OPERATIONS = {
    'acquire-references': (ita_index_references, 'acquire'),
    'import-reference': (ita_index_references, 'import_reference'),
    'build': (ita_establishment_bundle, 'build'),
    'verify': (ita_establishment_bundle, 'verify_bundle'),
    'compare-runs': (ita_establishment_bundle, 'compare_runs'),
}
CODES_PIN = '1' * 64
OUTPUTS_PIN = '2' * 64
SECRET = 'EIN 123456789 at 1 Main St'
REFERENCES = 'raw/references/naics'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    forbid_external_access(monkeypatch)

    def forbidden(*args, **kwargs):
        raise AssertionError('a Stage 10 command reached the network or an upstream builder')

    monkeypatch.setattr(osha_benchmark_download, 'make_client', forbidden)
    monkeypatch.setattr(ita_index_references, 'make_client', forbidden)
    monkeypatch.setattr(httpx.Client, '__init__', forbidden)
    monkeypatch.setattr(httpx.AsyncClient, '__init__', forbidden)
    monkeypatch.setattr(ita_summary, 'build_summary_table', forbidden)
    monkeypatch.setattr(code_build, 'build', forbidden)
    monkeypatch.setattr(geography_build, 'build', forbidden)


def original_file(data_directory):
    return data_directory.parent / 'downloads' / '2022_NAICS_Index_File.xlsx'


def command_arguments(command, data_directory):
    '''Every argument of one command except `--data-dir`.'''
    return {
        'acquire-references': [],
        'import-reference': ['naics_index_2022', str(original_file(data_directory))],
        'build': ['run_1', '--codes-run', 'codes_run', '--codes-outputs-sha256', CODES_PIN],
        'verify': ['run_1', '--outputs-sha256', OUTPUTS_PIN],
        'compare-runs': ['run_1', 'run_2'],
    }[command]


def invoke(runner, command, data_directory, arguments=None):
    if arguments is None:
        arguments = command_arguments(command, data_directory)
    return runner.invoke(app, [command, *arguments, '--data-dir', str(data_directory)])


def forbid_operations(monkeypatch):
    # pytest.fail raises a BaseException, which the command guard does not catch.
    def forbidden(*args, **kwargs):
        pytest.fail('a refused command reached a module function')

    for module, name in OPERATIONS.values():
        monkeypatch.setattr(module, name, forbidden)


def run_path(data_directory, run_id):
    return data_directory / 'derived' / 'osha' / 'establishment-targets' / run_id


def expected_failure(command, data_directory, reason):
    '''The exact stderr of one failed command.'''
    if command in ('acquire-references', 'import-reference'):
        run_id, path = '-', REFERENCES
    elif command == 'compare-runs':
        run_id = 'run_1,run_2'
        path = f'{run_path(data_directory, "run_1")},{run_path(data_directory, "run_2")}'
    else:
        run_id, path = 'run_1', run_path(data_directory, 'run_1')
    return f'ITA establishment {command} failed: {reason}; run {run_id}; path {path}\n'


def test_help_lists_exactly_five_commands(cli_runner):
    assert [command.name for command in app.registered_commands] == list(COMMANDS)
    assert sorted(get_command(app).commands) == sorted(COMMANDS)
    result = cli_runner.invoke(app, ['--help'])
    assert result.exit_code == 0, result.output
    for command in COMMANDS:
        assert command in result.stdout


@pytest.mark.parametrize('command', COMMANDS)
def test_data_dir_is_required(cli_runner, data_directory, monkeypatch, command):
    forbid_operations(monkeypatch)
    result = cli_runner.invoke(app, [command, *command_arguments(command, data_directory)])
    assert result.exit_code == 2, result.output
    assert 'Missing option' in result.output
    assert '--data-dir' in result.output
    assert not data_directory.exists()


def recorder(calls, name, result):
    def record(*args, **kwargs):
        calls.append((name, args, kwargs))
        return result

    return record


def test_commands_wire_arguments(cli_runner, data_directory, monkeypatch):
    calls = []
    registry = ita_index_references.REGISTRY
    acquired = [ita_index_references.reference_path(data_directory, reference)
                for reference in registry.values()]
    imported = ita_index_references.reference_path(data_directory,
                                                   registry['naics_index_2022'])
    # Keys out of sorted order, so the printed line shows `sort_keys`.
    built = {'run_id': 'run_1', 'outputs_sha256': OUTPUTS_PIN, 'directory': 'published'}
    verified = {'run_id': 'run_1', 'rows': {'b': 2, 'a': 1}, 'outputs_sha256': OUTPUTS_PIN}
    compared = {'tables': {}, 'equal': True, 'trust_established': False}
    for (module, name), result in zip(OPERATIONS.values(),
                                      (acquired, imported, built, verified, compared),
                                      strict=True):
        monkeypatch.setattr(module, name, recorder(calls, name, result))

    outputs = {command: invoke(cli_runner, command, data_directory) for command in COMMANDS}

    for command, result in outputs.items():
        assert result.exit_code == 0, (command, result.output)
        assert result.stderr == ''
    assert outputs['acquire-references'].stdout == json.dumps([
        'raw/references/naics/2012_NAICS_Index_File.xls',
        'raw/references/naics/2017_NAICS_Index_File.xlsx',
        'raw/references/naics/2022_NAICS_Index_File.xlsx',
    ]) + '\n'
    assert outputs['import-reference'].stdout == (
        '"raw/references/naics/2022_NAICS_Index_File.xlsx"\n')
    for command, result in (('build', built), ('verify', verified), ('compare-runs', compared)):
        assert outputs[command].stdout == json.dumps(result, sort_keys=True) + '\n'
    assert outputs['build'].stdout.startswith('{"directory": ')
    assert calls == [
        ('acquire', (data_directory,), {}),
        ('import_reference',
         (data_directory, 'naics_index_2022', original_file(data_directory)), {}),
        ('build', (data_directory, 'run_1'),
         {'codes_run': 'codes_run', 'codes_outputs_sha256': CODES_PIN}),
        ('verify_bundle', (run_path(data_directory, 'run_1'), data_directory),
         {'expected_outputs_sha256': OUTPUTS_PIN}),
        ('compare_runs',
         (run_path(data_directory, 'run_1'), run_path(data_directory, 'run_2')), {}),
    ]


def test_failure_message_is_fixed(cli_runner, data_directory, monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError(SECRET)

    monkeypatch.setattr(ita_establishment_bundle, 'build', fail)
    result = invoke(cli_runner, 'build', data_directory)
    assert result.exit_code == 2
    assert result.stderr == (
        'ITA establishment build failed: validation; run run_1; '
        f'path {run_path(data_directory, "run_1")}\n')
    assert '123456789' not in result.output


def test_compare_unequal_exits_1(cli_runner, data_directory, monkeypatch):
    compared = {'equal': False, 'report_equal': False, 'tables': {},
                'trust_established': False}
    monkeypatch.setattr(ita_establishment_bundle, 'compare_runs',
                        lambda first, second: compared)
    result = invoke(cli_runner, 'compare-runs', data_directory)
    assert result.exit_code == 1
    assert type(result.exception) is SystemExit
    assert result.stdout == json.dumps(compared, sort_keys=True) + '\n'
    assert result.stderr == ''


# Additional coverage beyond the plan tests.

@pytest.mark.parametrize('command', COMMANDS)
def test_every_command_prints_only_the_fixed_failure_line(cli_runner, data_directory,
                                                           monkeypatch, command):
    def fail(*args, **kwargs):
        raise ValueError(SECRET)

    module, name = OPERATIONS[command]
    monkeypatch.setattr(module, name, fail)
    result = invoke(cli_runner, command, data_directory)
    assert result.exit_code == 2
    assert type(result.exception) is SystemExit
    assert result.stderr == expected_failure(command, data_directory, 'validation')
    assert result.stdout == ''


@pytest.mark.parametrize('error,reason', [
    (ValueError(SECRET), 'validation'),
    (FileNotFoundError(2, SECRET), 'filesystem'),
    (PermissionError(13, SECRET), 'filesystem'),
    (httpx.ConnectError(SECRET), 'network'),
    (httpx.HTTPStatusError(SECRET, request=httpx.Request('GET', 'https://example.test'),
                           response=httpx.Response(403)), 'network'),
    (RuntimeError(SECRET), 'unexpected'),
    (subprocess.CalledProcessError(128, ['git', SECRET]), 'unexpected'),
    (pl.exceptions.ComputeError(SECRET), 'unexpected'),
    (KeyError(SECRET), 'unexpected'),
], ids=['value', 'missing_file', 'permission', 'connect', 'status', 'runtime', 'git',
        'polars', 'key'])
def test_failure_reason_follows_the_exception_type(cli_runner, data_directory, monkeypatch,
                                                   error, reason):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(ita_index_references, 'acquire', fail)
    result = invoke(cli_runner, 'acquire-references', data_directory)
    assert result.exit_code == 2
    assert result.stderr == expected_failure('acquire-references', data_directory, reason)
    assert '123456789' not in result.output


@pytest.mark.parametrize('command,arguments', [
    ('build', ['../escape', '--codes-run', 'codes_run', '--codes-outputs-sha256', CODES_PIN]),
    ('verify', ['../escape', '--outputs-sha256', OUTPUTS_PIN]),
    ('compare-runs', ['../escape', 'run_2']),
], ids=['build', 'verify', 'compare-runs'])
def test_unsafe_run_id_gives_the_fixed_line(cli_runner, data_directory, monkeypatch, command,
                                           arguments):
    for name in ('verify_bundle', 'compare_runs'):
        monkeypatch.setattr(ita_establishment_bundle, name, lambda *args, **kwargs: pytest.fail(
            'an unsafe run ID reached the bundle'))
    result = invoke(cli_runner, command, data_directory, arguments)
    assert result.exit_code == 2
    if command == 'compare-runs':
        run_id = '../escape,run_2'
        path = f'{run_path(data_directory, "../escape")},{run_path(data_directory, "run_2")}'
    else:
        run_id, path = '../escape', run_path(data_directory, '../escape')
    assert result.stderr == (
        f'ITA establishment {command} failed: validation; run {run_id}; path {path}\n')
    assert not data_directory.exists()


@pytest.mark.parametrize('command,arguments', [
    ('build', ['run_1', '--codes-outputs-sha256', CODES_PIN]),
    ('build', ['run_1', '--codes-run', 'codes_run']),
    ('build', ['--codes-run', 'codes_run', '--codes-outputs-sha256', CODES_PIN]),
    ('verify', ['run_1']),
    ('verify', ['--outputs-sha256', OUTPUTS_PIN]),
    ('import-reference', ['naics_index_2022']),
    ('compare-runs', ['run_1']),
], ids=['build_codes_run', 'build_codes_pin', 'build_run_id', 'verify_pin', 'verify_run_id',
        'import_file', 'compare_second'])
def test_each_required_argument_fails_before_work(cli_runner, data_directory, monkeypatch,
                                                  command, arguments):
    forbid_operations(monkeypatch)
    result = invoke(cli_runner, command, data_directory, arguments)
    assert result.exit_code == 2, result.output
    assert 'Missing' in result.output
    assert not data_directory.exists()


@pytest.mark.parametrize('command,arguments', [
    ('import-reference', ['naics_index_1997', 'missing.xlsx']),
    ('build', ['.hidden', '--codes-run', 'codes_run', '--codes-outputs-sha256', CODES_PIN]),
    ('verify', ['run_1', '--outputs-sha256', OUTPUTS_PIN]),
    ('compare-runs', ['run_1', 'run_2']),
], ids=['import-reference', 'build', 'verify', 'compare-runs'])
def test_offline_commands_reach_the_real_refusals(cli_runner, data_directory, command,
                                                  arguments):
    # The real functions run under the offline guard: a loaded `.env` or a constructed
    # client would raise AssertionError and print `unexpected`, not `validation`.
    result = invoke(cli_runner, command, data_directory, arguments)
    assert result.exit_code == 2
    assert result.stderr.startswith(f'ITA establishment {command} failed: validation; run ')
    assert result.stdout == ''
    assert not data_directory.exists()


def test_top_level_cli_does_not_register_stage_10():
    from embedding_data import cli

    assert all(command.callback.__module__ != ita_establishment_targets.__name__
               for command in cli.app.registered_commands)
    assert all(group.typer_instance is not app for group in cli.app.registered_groups)
    assert not set(COMMANDS) & set(get_command(cli.app).commands)


def test_app_disables_pretty_exceptions_and_locals():
    assert app.pretty_exceptions_enable is False
    assert app.pretty_exceptions_show_locals is False


def test_module_runs_with_python_m(tmp_path):
    result = subprocess.run(
        [sys.executable, '-m', 'embedding_data.ita_establishment_targets', '--help'],
        capture_output=True, text=True, cwd=tmp_path, check=False)
    assert result.returncode == 0, result.stderr
    for command in COMMANDS:
        assert command in result.stdout
