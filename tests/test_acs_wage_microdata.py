'''The wage microdata command group: its surface, argument wiring, exit codes and failure line.'''

import json
import subprocess
import sys

import httpx
import polars as pl
import pytest
from acs_wage_fixtures import copy_template, wage_mapping
from target_fixtures import forbid_external_access
from typer.main import get_command

from embedding_data import (
    acs_mapping_bundle,
    acs_wage_bundle,
    acs_wage_inputs,
    acs_wage_microdata,
    code_build,
    geography_build,
    manifest,
    target_io,
)
from embedding_data.acs_wage_microdata import app

COMMANDS = ('build', 'verify', 'compare-runs')
OPERATIONS = {'build': 'build', 'verify': 'verify_bundle', 'compare-runs': 'compare_runs'}
MAPPING_PIN = '1' * 64
OUTPUTS_PIN = '2' * 64
CODES_PIN = '3' * 64
SECRET = 'INCWAGE 123456 in row 7'


@pytest.fixture(scope='module')
def template(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patches:
        yield wage_mapping(tmp_path_factory.mktemp('wage-command-template'), patches)


@pytest.fixture
def chain(template, tmp_path):
    return copy_template(template, tmp_path)


@pytest.fixture(autouse=True)
def attempts(monkeypatch):
    '''Deny every external seam in every test. The list holds each attempt that was made.'''
    import dotenv

    forbid_external_access(monkeypatch)
    made = []

    def forbidden(*args, **kwargs):
        made.append('an external seam')
        raise AssertionError('a wage command reached the network, an env file or a builder')

    for owner, name in ((httpx.Client, '__init__'), (httpx.AsyncClient, '__init__'),
                        (dotenv, 'dotenv_values'), (code_build, 'build'),
                        (geography_build, 'build'), (acs_mapping_bundle, 'build')):
        monkeypatch.setattr(owner, name, forbidden)
    return made


def command_arguments(command):
    '''Every argument of one command except `--data-dir`. All values differ from each other.'''
    return {
        'build': ['r1', '--mapping-run', 'mapping_run', '--mapping-outputs-sha256', MAPPING_PIN,
                  '--codes-run', 'codes_run', '--codes-outputs-sha256', CODES_PIN],
        'verify': ['r1', '--outputs-sha256', OUTPUTS_PIN],
        'compare-runs': ['r1', 'r2'],
    }[command]


def invoke(runner, command, data_dir, arguments=None):
    if arguments is None:
        arguments = command_arguments(command)
    return runner.invoke(app, [command, *arguments, '--data-dir', str(data_dir)])


def run_path(data_dir, run_id):
    return data_dir / 'derived' / 'acs' / 'wage-microdata' / run_id


def expected_failure(command, data_dir, reason):
    '''The exact stderr of one failed command.'''
    if command == 'compare-runs':
        run_id = 'r1,r2'
        path = f'{run_path(data_dir, "r1")},{run_path(data_dir, "r2")}'
    else:
        run_id, path = 'r1', run_path(data_dir, 'r1')
    return f'ACS wage microdata {command} failed: {reason}; run {run_id}; path {path}\n'


def forbid_operations(monkeypatch):
    # pytest.fail raises a BaseException, which the command guard does not catch.
    def forbidden(*args, **kwargs):
        pytest.fail('a refused command reached a bundle function')

    for name in OPERATIONS.values():
        monkeypatch.setattr(acs_wage_bundle, name, forbidden)


def test_exactly_three_commands(cli_runner):
    assert [command.name for command in app.registered_commands] == list(COMMANDS)
    assert app.registered_groups == []
    assert sorted(get_command(app).commands) == sorted(COMMANDS)
    result = cli_runner.invoke(app, ['--help'])
    assert result.exit_code == 0, result.output
    for command in COMMANDS:
        assert command in result.stdout


@pytest.mark.parametrize('argv', [[command, *command_arguments(command)]
                                  for command in COMMANDS], ids=COMMANDS)
def test_data_dir_is_required(cli_runner, data_directory, monkeypatch, argv):
    forbid_operations(monkeypatch)
    result = cli_runner.invoke(app, argv)
    assert result.exit_code == 2, result.output
    assert 'Missing option' in result.output
    assert '--data-dir' in result.output
    assert not data_directory.exists()


def recorder(calls, name, result):
    def record(*args, **kwargs):
        calls.append((name, args, kwargs))
        return result

    return record


def test_options_reach_the_bundle_functions(cli_runner, monkeypatch, tmp_path):
    calls = []
    # Keys out of sorted order, so the printed line shows `sort_keys`.
    built = {'run_id': 'r1', 'outputs_sha256': OUTPUTS_PIN, 'directory': 'published'}
    verified = {'run_id': 'r1', 'rows': 3, 'headline_rows': 2, 'codes_run': 'codes_run'}
    compared = {'table': {}, 'equal': True, 'trust_established': False}
    for name, result in zip(OPERATIONS.values(), (built, verified, compared), strict=True):
        monkeypatch.setattr(acs_wage_bundle, name, recorder(calls, name, result))

    outputs = {command: invoke(cli_runner, command, tmp_path) for command in COMMANDS}

    for command, result in outputs.items():
        assert result.exit_code == 0, (command, result.output)
        assert result.stderr == ''
    for command, result in zip(COMMANDS, (built, verified, compared), strict=True):
        assert outputs[command].stdout == json.dumps(result, sort_keys=True) + '\n'
    assert outputs['build'].stdout.startswith('{"directory": ')
    assert calls == [
        ('build', (tmp_path, 'r1'),
         {'mapping_run': 'mapping_run', 'mapping_outputs_sha256': MAPPING_PIN,
          'codes_run': 'codes_run', 'codes_outputs_sha256': CODES_PIN}),
        ('verify_bundle', (run_path(tmp_path, 'r1'), tmp_path),
         {'expected_outputs_sha256': OUTPUTS_PIN}),
        ('compare_runs', (run_path(tmp_path, 'r1'), run_path(tmp_path, 'r2')), {}),
    ]


def test_build_failure_prints_only_the_fixed_line(cli_runner, monkeypatch, tmp_path):
    def fail(*args, **kwargs):
        raise ValueError(SECRET)

    monkeypatch.setattr(acs_wage_bundle, 'build', fail)
    result = invoke(cli_runner, 'build', tmp_path)
    assert result.exit_code == 2
    assert result.stderr == ('ACS wage microdata build failed: validation; run r1; '
                             f'path {tmp_path}/derived/acs/wage-microdata/r1\n')
    assert '123456' not in result.output


def test_compare_runs_exits_1_when_unequal(cli_runner, monkeypatch, tmp_path):
    compared = {'equal': False, 'report_equal': False, 'table': {}, 'trust_established': False}
    monkeypatch.setattr(acs_wage_bundle, 'compare_runs', lambda first, second: compared)
    result = invoke(cli_runner, 'compare-runs', tmp_path)
    assert result.exit_code == 1
    assert type(result.exception) is SystemExit
    assert result.stdout == json.dumps(compared, sort_keys=True) + '\n'
    assert result.stderr == ''


def test_top_level_cli_does_not_register_the_group():
    from embedding_data import cli

    assert all(command.callback.__module__ != acs_wage_microdata.__name__
               for command in cli.app.registered_commands)
    assert all(group.typer_instance is not app for group in cli.app.registered_groups)
    names = set(get_command(cli.app).commands)
    assert not any('wage' in name for name in names)
    assert not set(COMMANDS) & names


def test_module_runs_with_python_m(tmp_path):
    result = subprocess.run(
        [sys.executable, '-m', 'embedding_data.acs_wage_microdata', '--help'],
        capture_output=True, text=True, cwd=tmp_path, check=False)
    assert result.returncode == 0, result.stderr
    for command in COMMANDS:
        assert command in result.stdout


def test_software_files_cover_loaded_modules(tmp_path):
    probe = ('import sys, embedding_data.acs_wage_microdata; '
             'print("\\n".join(sorted(sys.modules)))')
    loaded = set(subprocess.run([sys.executable, '-c', probe], check=True, cwd=tmp_path,
                                capture_output=True, text=True).stdout.split())
    assert not loaded & {'dotenv', 'ipumspy'}
    files = {'src/embedding_data/' + (name.partition('.')[2] or '__init__') + '.py'
             for name in loaded if name.partition('.')[0] == 'embedding_data'}
    assert 'src/embedding_data/acs_wage_microdata.py' in files
    assert {*files, 'pyproject.toml', 'uv.lock'} == set(acs_wage_inputs.SOFTWARE_FILES)
    assert len(set(acs_wage_inputs.SOFTWARE_FILES)) == len(acs_wage_inputs.SOFTWARE_FILES)


def succeeded(result, command):
    '''The parsed JSON of a command that printed exactly one sorted line and nothing else.'''
    assert result.exit_code == 0, (command, result.output)
    assert result.stderr == ''
    assert result.stdout.count('\n') == 1
    value = json.loads(result.stdout)
    assert result.stdout == json.dumps(value, sort_keys=True) + '\n'
    return value


def build_arguments(chain, run_id):
    return [run_id, '--mapping-run', chain['mapping_run'], '--mapping-outputs-sha256',
            chain['mapping_outputs_sha256'], '--codes-run', chain['codes_run'],
            '--codes-outputs-sha256', chain['codes_outputs_sha256']]


def test_real_commands_touch_no_network_env_or_builder(cli_runner, chain, attempts):
    data_dir = chain['data_dir']
    first = succeeded(invoke(cli_runner, 'build', data_dir, build_arguments(chain, 'first')),
                      'build first')
    verified = succeeded(invoke(cli_runner, 'verify', data_dir,
                                ['first', '--outputs-sha256', first['outputs_sha256']]),
                         'verify')
    replay = succeeded(invoke(cli_runner, 'build', data_dir, build_arguments(chain, 'replay')),
                       'build replay')
    compared = succeeded(invoke(cli_runner, 'compare-runs', data_dir, ['first', 'replay']),
                         'compare-runs')

    assert first['directory'] == str(run_path(data_dir, 'first'))
    assert replay['directory'] == str(run_path(data_dir, 'replay'))
    assert verified['run_id'] == 'first'
    assert verified['outputs_sha256'] == first['outputs_sha256']
    assert verified['mapping_run'] == chain['mapping_run']
    assert compared['equal'] is True
    assert compared['trust_established'] is False
    assert attempts == []


def edit_first_row(directory):
    '''Rewrite the first row's AGE in the bundle's table, keeping its schema.'''
    file = directory / 'acs_wage_persons.parquet'
    first = pl.int_range(pl.len()) == 0
    pl.read_parquet(file).with_columns(
        pl.when(first).then(pl.col('AGE') + 1).otherwise(pl.col('AGE')).alias('AGE')
    ).write_parquet(file)


def rehash(directory):
    '''Rewrite a bundle's inventory after an edit, and return the new detached pin.'''
    target_io.write_json(directory / 'outputs.json',
                         target_io.inventory(directory, list(acs_wage_bundle.FILES)))
    return manifest.sha256_file(directory / 'outputs.json')


def test_a_rehashed_edit_fails_verify_and_compares_unequal(cli_runner, chain):
    data_dir = chain['data_dir']
    for run_id in ('first', 'replay'):
        succeeded(invoke(cli_runner, 'build', data_dir, build_arguments(chain, run_id)),
                  f'build {run_id}')
    edit_first_row(run_path(data_dir, 'first'))
    pin = rehash(run_path(data_dir, 'first'))

    verify = invoke(cli_runner, 'verify', data_dir, ['first', '--outputs-sha256', pin])
    assert verify.exit_code == 2
    assert verify.stdout == ''
    assert verify.stderr == (
        'ACS wage microdata verify failed: validation; run first; '
        f'path {run_path(data_dir, "first")}\n')

    compare = invoke(cli_runner, 'compare-runs', data_dir, ['first', 'replay'])
    assert compare.exit_code == 1
    assert type(compare.exception) is SystemExit
    assert compare.stderr == ''
    assert '"equal": false' in compare.stdout
    value = json.loads(compare.stdout)
    assert value['equal'] is False
    assert value['table']['values_equal'] is False
    assert value['trust_established'] is False


@pytest.mark.parametrize('command', COMMANDS)
def test_every_command_prints_only_the_fixed_failure_line(cli_runner, data_directory,
                                                           monkeypatch, command):
    def fail(*args, **kwargs):
        raise ValueError(SECRET)

    monkeypatch.setattr(acs_wage_bundle, OPERATIONS[command], fail)
    result = invoke(cli_runner, command, data_directory)
    assert result.exit_code == 2
    assert type(result.exception) is SystemExit
    assert result.stderr == expected_failure(command, data_directory, 'validation')
    assert result.stdout == ''


@pytest.mark.parametrize('error,reason', [
    (ValueError(SECRET), 'validation'),
    (FileNotFoundError(2, SECRET), 'filesystem'),
    (PermissionError(13, SECRET), 'filesystem'),
    (RuntimeError(SECRET), 'unexpected'),
    (KeyError(SECRET), 'unexpected'),
    (pl.exceptions.ComputeError(SECRET), 'unexpected'),
    (subprocess.CalledProcessError(128, ['git', SECRET]), 'unexpected'),
    (httpx.ConnectError(SECRET), 'unexpected'),
], ids=['value', 'missing_file', 'permission', 'runtime', 'key', 'polars', 'git', 'httpx'])
def test_failure_reason_follows_the_exception_type(cli_runner, data_directory, monkeypatch,
                                                   error, reason):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(acs_wage_bundle, 'build', fail)
    result = invoke(cli_runner, 'build', data_directory)
    assert result.exit_code == 2
    assert result.stderr == expected_failure('build', data_directory, reason)
    assert '123456' not in result.output


@pytest.mark.parametrize('command,arguments', [
    ('build', ['../escape', '--mapping-run', 'mapping_run', '--mapping-outputs-sha256',
               MAPPING_PIN, '--codes-run', 'codes_run', '--codes-outputs-sha256', CODES_PIN]),
    ('verify', ['../escape', '--outputs-sha256', OUTPUTS_PIN]),
    ('compare-runs', ['../escape', 'r2']),
], ids=COMMANDS)
def test_unsafe_run_id_gives_the_fixed_line(cli_runner, data_directory, monkeypatch, command,
                                           arguments):
    for name in ('verify_bundle', 'compare_runs'):
        monkeypatch.setattr(acs_wage_bundle, name, lambda *args, **kwargs: pytest.fail(
            'an unsafe run ID reached the bundle'))
    result = invoke(cli_runner, command, data_directory, arguments)
    assert result.exit_code == 2
    if command == 'compare-runs':
        run_id = '../escape,r2'
        path = f'{run_path(data_directory, "../escape")},{run_path(data_directory, "r2")}'
    else:
        run_id, path = '../escape', run_path(data_directory, '../escape')
    assert result.stderr == (
        f'ACS wage microdata {command} failed: validation; run {run_id}; path {path}\n')
    assert result.stdout == ''
    assert not data_directory.exists()


@pytest.mark.parametrize('command,arguments', [
    ('build', ['--mapping-run', 'mapping_run', '--mapping-outputs-sha256', MAPPING_PIN,
               '--codes-run', 'codes_run', '--codes-outputs-sha256', CODES_PIN]),
    ('build', ['r1', '--mapping-outputs-sha256', MAPPING_PIN,
               '--codes-run', 'codes_run', '--codes-outputs-sha256', CODES_PIN]),
    ('build', ['r1', '--mapping-run', 'mapping_run',
               '--codes-run', 'codes_run', '--codes-outputs-sha256', CODES_PIN]),
    ('build', ['r1', '--mapping-run', 'mapping_run', '--mapping-outputs-sha256', MAPPING_PIN,
               '--codes-outputs-sha256', CODES_PIN]),
    ('build', ['r1', '--mapping-run', 'mapping_run', '--mapping-outputs-sha256', MAPPING_PIN,
               '--codes-run', 'codes_run']),
    ('verify', ['r1']),
    ('verify', ['--outputs-sha256', OUTPUTS_PIN]),
    ('compare-runs', ['r1']),
], ids=['build_run_id', 'build_mapping_run', 'build_mapping_pin', 'build_codes_run',
        'build_codes_pin', 'verify_pin', 'verify_run_id', 'compare_second'])
def test_each_required_argument_fails_before_work(cli_runner, data_directory, monkeypatch,
                                                  command, arguments):
    forbid_operations(monkeypatch)
    result = invoke(cli_runner, command, data_directory, arguments)
    assert result.exit_code == 2, result.output
    assert 'Missing' in result.output
    assert not data_directory.exists()


@pytest.mark.parametrize('command', ['verify', 'compare-runs'])
def test_offline_commands_reach_the_real_refusals(cli_runner, data_directory, attempts,
                                                  command):
    # The real functions run under the offline guard: a loaded `.env` or a constructed
    # client would raise AssertionError and print `unexpected`, not `validation`.
    result = invoke(cli_runner, command, data_directory)
    assert result.exit_code == 2
    assert result.stderr == expected_failure(command, data_directory, 'validation')
    assert result.stdout == ''
    assert attempts == []
    assert not data_directory.exists()


def tree_snapshot(root):
    '''Every path under root, with the bytes of each file and None for each directory.'''
    return sorted((path.relative_to(root).as_posix(), path.read_bytes() if path.is_file()
                   else None) for path in root.rglob('*'))


@pytest.mark.parametrize('occupied', ['r1.part', 'r1'], ids=['staging', 'final'])
def test_build_failure_keeps_occupied_run_paths(cli_runner, data_directory, occupied):
    # The real build refuses an occupied name before it reads anything. The failure must
    # leave a killed run's staging and a published bundle exactly as they were.
    root = data_directory / 'derived' / 'acs' / 'wage-microdata'
    (root / occupied).mkdir(parents=True)
    (root / occupied / 'kept.txt').write_bytes(b'owner evidence\n')
    before = tree_snapshot(root)
    result = invoke(cli_runner, 'build', data_directory)
    assert result.exit_code == 2
    assert result.stderr == expected_failure('build', data_directory, 'validation')
    assert result.stdout == ''
    assert tree_snapshot(root) == before


def test_app_disables_pretty_exceptions_and_locals():
    assert app.pretty_exceptions_enable is False
    assert app.pretty_exceptions_show_locals is False
