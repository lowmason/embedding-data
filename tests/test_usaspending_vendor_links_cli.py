'''The Stage 14 command group so far: subaward and SAM.gov extract acquisition and import,
their JSON line, exit codes and fixed failure line.'''

import json
import os
import subprocess
import sys

import httpx
import pytest
import typer
from vendor_link_fixtures import (  # noqa: F401
    EXTRACT_NAME,
    FAKE_KEY,
    MONTH,
    NAME,
    FakeSam,
    FakeUsaspending,
    extract_answer,
    extract_name,
    install_sam,
    install_usaspending,
    no_live_sam,
    sample_extract,
    sample_zip,
)

from embedding_data import (
    manifest,
    paths,
    sam_access,
    sam_raw,
    usaspending_raw,
    usaspending_vendor_links,
)

SECRET = 'EIN 123456789 at 1 Main St, key FAKEKEYfake0123456789ABCDEFghij'


def failure_line(command, reason):
    return (f'USAspending vendor links {command} failed: {reason}; run -; '
            'path raw/usaspending/subcontracts')


def acquire_arguments(data_directory, fiscal_year='2025', snapshot='2026-11-20'):
    return ['acquire-subawards', fiscal_year, '--snapshot', snapshot, '--data-dir',
            str(data_directory)]


def import_arguments(data_directory, file, fiscal_year='2025', snapshot='2026-11-20'):
    return ['import-subawards', fiscal_year, str(file), '--snapshot', snapshot, '--data-dir',
            str(data_directory)]


def original_file(tmp_path, name=NAME):
    file = tmp_path / 'downloads' / name
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(sample_zip())
    return file


def test_acquire_and_import_print_one_json_line(cli_runner, data_directory, tmp_path,
                                                monkeypatch):
    install_usaspending(monkeypatch, FakeUsaspending())
    acquired = cli_runner.invoke(usaspending_vendor_links.app,
                                 acquire_arguments(data_directory))
    assert acquired.exit_code == 0, acquired.output
    expected = {'path': f'raw/usaspending/subcontracts/2026-11-20/FY2025/{NAME}'}
    assert acquired.stdout == json.dumps(expected, sort_keys=True) + '\n'
    assert acquired.stderr == ''
    file = original_file(tmp_path, 'FY2024_Subawards.zip')
    imported = cli_runner.invoke(usaspending_vendor_links.app,
                                 import_arguments(data_directory, file, '2024'))
    assert imported.exit_code == 0, imported.output
    expected = {'path': 'raw/usaspending/subcontracts/2026-11-20/FY2024/FY2024_Subawards.zip'}
    assert imported.stdout == json.dumps(expected, sort_keys=True) + '\n'
    assert imported.stderr == ''
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [(entry.path, entry.client) for entry in entries] == [
        (f'usaspending/subcontracts/2026-11-20/FY2025/{NAME}', 'httpx'),
        ('usaspending/subcontracts/2026-11-20/FY2024/FY2024_Subawards.zip', 'manual-import')]


def test_import_failure_prints_only_the_fixed_line(cli_runner, data_directory, tmp_path):
    file = original_file(tmp_path)
    result = cli_runner.invoke(usaspending_vendor_links.app, [
        'import-subawards', '2023', str(file), '--snapshot', '2026-11-20',
        '--data-dir', str(data_directory)])
    assert result.exit_code == 2
    assert result.output.strip() == ('USAspending vendor links import-subawards failed: '
                                     'validation; run -; path raw/usaspending/subcontracts')


@pytest.mark.parametrize('error, reason', [
    (ValueError(SECRET), 'validation'),
    (json.JSONDecodeError(SECRET, SECRET, 0), 'validation'),
    (FileNotFoundError(2, SECRET, SECRET), 'filesystem'),
    (PermissionError(13, SECRET, SECRET), 'filesystem'),
    (httpx.ConnectError(SECRET), 'network'),
    (httpx.HTTPStatusError(SECRET, request=httpx.Request('GET', 'https://example.test'),
                           response=httpx.Response(403)), 'network'),
    (RuntimeError(SECRET), 'unexpected'),
    (KeyError(SECRET), 'unexpected'),
    (AssertionError(SECRET), 'unexpected'),
], ids=['value', 'json', 'missing_file', 'permission', 'connect', 'status', 'runtime', 'key',
        'assertion'])
@pytest.mark.parametrize('command, operation', [('acquire-subawards', 'acquire'),
                                                ('import-subawards', 'import_file')])
def test_failure_reason_follows_the_exception_type_and_hides_its_text(
        cli_runner, data_directory, tmp_path, monkeypatch, command, operation, error, reason):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(usaspending_raw, operation, fail)
    arguments = (acquire_arguments(data_directory) if command == 'acquire-subawards'
                 else import_arguments(data_directory, original_file(tmp_path)))
    result = cli_runner.invoke(usaspending_vendor_links.app, arguments)
    assert result.exit_code == 2
    assert result.stdout == ''
    assert result.stderr == failure_line(command, reason) + '\n'
    assert SECRET not in result.output


@pytest.mark.parametrize('snapshot', ['not-a-date', '2026-13-45', '2026-02-30', ''])
def test_a_bad_snapshot_date_fails_as_validation_before_any_work(
        cli_runner, data_directory, tmp_path, snapshot):
    for arguments in (acquire_arguments(data_directory, snapshot=snapshot),
                      import_arguments(data_directory, original_file(tmp_path),
                                       snapshot=snapshot)):
        result = cli_runner.invoke(usaspending_vendor_links.app, arguments)
        assert result.exit_code == 2
        assert result.stderr == failure_line(arguments[0], 'validation') + '\n'
    assert not data_directory.exists()


def test_acquire_refuses_a_year_outside_the_window_as_validation(cli_runner, data_directory):
    result = cli_runner.invoke(usaspending_vendor_links.app,
                               acquire_arguments(data_directory, '2023'))
    assert result.exit_code == 2
    assert result.stderr == failure_line('acquire-subawards', 'validation') + '\n'


def test_a_missing_network_patch_fails_instead_of_reaching_the_network(cli_runner,
                                                                       data_directory):
    result = cli_runner.invoke(usaspending_vendor_links.app, acquire_arguments(data_directory))
    assert result.exit_code == 2
    assert result.stderr == failure_line('acquire-subawards', 'unexpected') + '\n'


@pytest.mark.parametrize('drop', ['--data-dir', '--snapshot'])
def test_every_command_requires_an_explicit_data_root_and_snapshot(
        cli_runner, data_directory, tmp_path, drop):
    for arguments in (acquire_arguments(data_directory, '2023'),
                      import_arguments(data_directory, tmp_path / 'absent.zip', '2023')):
        index = arguments.index(drop)
        result = cli_runner.invoke(usaspending_vendor_links.app,
                                   arguments[:index] + arguments[index + 2:])
        assert result.exit_code == 2
        assert drop in result.output


def test_invoke_prints_one_sorted_json_line_and_returns_the_result(capsys):
    result = usaspending_vendor_links._invoke(
        'acquire-subawards', usaspending_vendor_links.NO_RUN, 'somewhere',
        lambda: {'b': 1, 'a': [2, 3]})
    assert result == {'b': 1, 'a': [2, 3]}
    assert capsys.readouterr() == ('{"a": [2, 3], "b": 1}\n', '')


def test_invoke_failure_exits_two_with_only_the_fixed_line(capsys):
    def fail():
        raise OSError(SECRET)

    with pytest.raises(typer.Exit) as stopped:
        usaspending_vendor_links._invoke('import-subawards', 'run_7', 'some/path', fail)
    assert stopped.value.exit_code == 2
    assert capsys.readouterr() == (
        '', 'USAspending vendor links import-subawards failed: filesystem; run run_7; '
        'path some/path\n')


def test_constants_and_typer_settings():
    module = usaspending_vendor_links
    assert module.NO_RUN == '-'
    assert module.SUBAWARDS == 'raw/usaspending/subcontracts'
    assert module.EXTRACTS == 'raw/sam/entity-extract/public-monthly-v2'
    assert module.app.pretty_exceptions_enable is False
    assert module.app.pretty_exceptions_show_locals is False


def test_module_runs_with_python_m_and_lists_its_commands(tmp_path):
    result = subprocess.run(
        [sys.executable, '-m', 'embedding_data.usaspending_vendor_links', '--help'],
        capture_output=True, text=True, cwd=tmp_path, check=False)
    assert result.returncode == 0, result.stderr
    for command in ('acquire-subawards', 'import-subawards'):
        assert command in result.stdout


def test_importing_the_command_module_loads_no_credential_or_ipums_library(tmp_path):
    result = subprocess.run(
        [sys.executable, '-c',
         'import sys; import embedding_data.usaspending_vendor_links; '
         "print('dotenv' in sys.modules, 'ipumspy' in sys.modules)"],
        capture_output=True, text=True, cwd=tmp_path, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'False False'


# --- SAM.gov extract commands


EXTRACT_DIRECTORY = 'raw/sam/entity-extract/public-monthly-v2'


def sam_failure_line(command, reason):
    return (f'USAspending vendor links {command} failed: {reason}; run -; '
            f'path {EXTRACT_DIRECTORY}')


def sam_acquire_arguments(data_directory, month=MONTH, *options):
    return ['acquire-sam-extract', '--month', month, '--data-dir', str(data_directory),
            *options]


def sam_import_arguments(data_directory, file, month=MONTH):
    return ['import-sam-extract', str(file), '--month', month, '--data-dir', str(data_directory)]


def extract_original(tmp_path, month='2026-10'):
    file = tmp_path / 'downloads' / extract_name(month)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(sample_extract(month))
    return file


def test_sam_acquire_and_import_print_one_json_line(cli_runner, data_directory, tmp_path,
                                                    monkeypatch):
    install_sam(monkeypatch, FakeSam(extract_answer()))
    monkeypatch.setenv('SAM_API_KEY', FAKE_KEY)
    acquired = cli_runner.invoke(usaspending_vendor_links.app,
                                 sam_acquire_arguments(data_directory))
    assert acquired.exit_code == 0, acquired.output
    expected = {'path': f'{EXTRACT_DIRECTORY}/2026-11/{EXTRACT_NAME}'}
    assert acquired.stdout == json.dumps(expected, sort_keys=True) + '\n'
    assert acquired.stderr == ''
    imported = cli_runner.invoke(usaspending_vendor_links.app, sam_import_arguments(
        data_directory, extract_original(tmp_path), '2026-10'))
    assert imported.exit_code == 0, imported.output
    expected = {'path': f'{EXTRACT_DIRECTORY}/2026-10/{extract_name("2026-10")}'}
    assert imported.stdout == json.dumps(expected, sort_keys=True) + '\n'
    assert imported.stderr == ''
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [(entry.path, entry.client) for entry in entries] == [
        (f'sam/entity-extract/public-monthly-v2/2026-11/{EXTRACT_NAME}', 'httpx'),
        (f'sam/entity-extract/public-monthly-v2/2026-10/{extract_name("2026-10")}',
         'manual-import')]


SAM_FAILURES = [
    (ValueError(SECRET), 'validation'),
    (FileNotFoundError(2, SECRET, SECRET), 'filesystem'),
    (httpx.ConnectError(SECRET), 'network'),
    (RuntimeError(SECRET), 'unexpected'),
]


@pytest.mark.parametrize('error, reason', SAM_FAILURES,
                         ids=['value', 'missing_file', 'connect', 'runtime'])
@pytest.mark.parametrize('command, operation', [('acquire-sam-extract', 'acquire'),
                                                ('import-sam-extract', 'import_file')])
def test_sam_failure_reason_follows_the_exception_type_and_hides_its_text(
        cli_runner, data_directory, tmp_path, monkeypatch, command, operation, error, reason):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(sam_raw, operation, fail)
    monkeypatch.setenv('SAM_API_KEY', FAKE_KEY)
    arguments = (sam_acquire_arguments(data_directory) if command == 'acquire-sam-extract'
                 else sam_import_arguments(data_directory, extract_original(tmp_path)))
    result = cli_runner.invoke(usaspending_vendor_links.app, arguments)
    assert result.exit_code == 2
    assert result.stdout == ''
    assert result.stderr == sam_failure_line(command, reason) + '\n'
    assert SECRET not in result.output


def test_acquire_sam_extract_passes_the_key_options_and_the_key(cli_runner, data_directory,
                                                                tmp_path, monkeypatch):
    seen = []

    def read(**options):
        seen.append(options)
        return FAKE_KEY

    def acquire(data_dir, month, *, credential):
        seen.append((data_dir, month, credential))
        return sam_raw.month_dir(data_dir, month) / EXTRACT_NAME

    monkeypatch.setattr(sam_access, 'read_credential', read)
    monkeypatch.setattr(sam_raw, 'acquire', acquire)
    env_file = tmp_path / 'sam.env'
    result = cli_runner.invoke(usaspending_vendor_links.app, sam_acquire_arguments(
        data_directory, MONTH, '--env-file', str(env_file), '--prompt'))
    assert result.exit_code == 0, result.output
    result = cli_runner.invoke(usaspending_vendor_links.app,
                               sam_acquire_arguments(data_directory))
    assert result.exit_code == 0, result.output
    assert seen == [{'env_file': env_file, 'prompt': True}, (data_directory, MONTH, FAKE_KEY),
                    {'env_file': None, 'prompt': False}, (data_directory, MONTH, FAKE_KEY)]


def test_import_sam_extract_reads_no_key_and_makes_no_client(cli_runner, data_directory,
                                                             tmp_path, monkeypatch):
    def forbidden(**options):
        raise AssertionError('read the key')

    monkeypatch.setattr(sam_access, 'read_credential', forbidden)
    monkeypatch.setenv('SAM_API_KEY', FAKE_KEY)
    result = cli_runner.invoke(usaspending_vendor_links.app, sam_import_arguments(
        data_directory, extract_original(tmp_path), '2026-10'))
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize('month', ['2026-13', '11/2026', ''])
def test_a_bad_month_fails_as_validation_before_the_key_is_read(
        cli_runner, data_directory, tmp_path, monkeypatch, month):
    asked = []

    def read(**options):
        asked.append(options)
        return FAKE_KEY

    monkeypatch.setattr(sam_access, 'read_credential', read)
    for arguments in (sam_acquire_arguments(data_directory, month),
                      sam_import_arguments(data_directory, extract_original(tmp_path), month)):
        result = cli_runner.invoke(usaspending_vendor_links.app, arguments)
        assert result.exit_code == 2
        assert result.stderr == sam_failure_line(arguments[0], 'validation') + '\n'
    assert asked == []
    assert not data_directory.exists()


def test_prompt_without_a_terminal_fails_as_validation_before_any_request(
        cli_runner, data_directory, monkeypatch):
    server = install_sam(monkeypatch, FakeSam(extract_answer()))
    result = cli_runner.invoke(usaspending_vendor_links.app,
                               sam_acquire_arguments(data_directory, MONTH, '--prompt'))
    assert result.exit_code == 2
    assert result.stderr == sam_failure_line('acquire-sam-extract', 'validation') + '\n'
    assert server.requests == []
    assert not data_directory.exists()


def test_a_missing_sam_patch_fails_closed_instead_of_reaching_the_network(
        cli_runner, data_directory, monkeypatch):
    # The guard's AssertionError is inside the protected scope, so it becomes the fixed error.
    monkeypatch.setenv('SAM_API_KEY', FAKE_KEY)
    result = cli_runner.invoke(usaspending_vendor_links.app,
                               sam_acquire_arguments(data_directory))
    assert result.exit_code == 2
    assert result.stderr == sam_failure_line('acquire-sam-extract', 'validation') + '\n'
    assert not paths.manifest_path(data_directory).exists()


@pytest.mark.parametrize('drop', ['--data-dir', '--month'])
def test_sam_commands_require_an_explicit_data_root_and_month(cli_runner, data_directory,
                                                              tmp_path, drop):
    for arguments in (sam_acquire_arguments(data_directory),
                      sam_import_arguments(data_directory, tmp_path / 'absent.ZIP')):
        index = arguments.index(drop)
        result = cli_runner.invoke(usaspending_vendor_links.app,
                                   arguments[:index] + arguments[index + 2:])
        assert result.exit_code == 2
        assert drop in result.output


def test_module_lists_the_sam_commands(tmp_path):
    result = subprocess.run(
        [sys.executable, '-m', 'embedding_data.usaspending_vendor_links', '--help'],
        capture_output=True, text=True, cwd=tmp_path, check=False)
    assert result.returncode == 0, result.stderr
    for command in ('acquire-sam-extract', 'import-sam-extract'):
        assert command in result.stdout


# Runs both import commands in a fresh interpreter where every dotenv import is refused and no
# HTTP client can be built, then reports what was attempted.
OFFLINE_IMPORTS = """
import json
import os
import sys


class RefuseDotenv:
    attempts = []

    def find_spec(self, name, path=None, target=None):
        if name.partition('.')[0] == 'dotenv':
            RefuseDotenv.attempts.append(name)
            raise ImportError('dotenv refused')
        return None


sys.meta_path.insert(0, RefuseDotenv())
import httpx


def no_client(*args, **kwargs):
    raise AssertionError('HTTP client constructed')


httpx.Client.__init__ = no_client
from typer.testing import CliRunner

from embedding_data import usaspending_vendor_links

data_dir, extract, month, subawards = sys.argv[1:]
before = dict(os.environ)
runner = CliRunner()
codes = [runner.invoke(usaspending_vendor_links.app, arguments).exit_code for arguments in (
    ['import-sam-extract', extract, '--month', month, '--data-dir', data_dir],
    ['import-subawards', '2025', subawards, '--snapshot', '2026-11-20', '--data-dir', data_dir])]
print(json.dumps({'codes': codes, 'dotenv_imports': RefuseDotenv.attempts,
                  'dotenv_loaded': 'dotenv' in sys.modules,
                  'environ_unchanged': dict(os.environ) == before}))
"""


def test_import_commands_load_no_environment_file(data_directory, tmp_path):
    # dotenv cannot even be imported, so a wrong version that loads an env file fails here
    # without ever reading one.
    environment = {name: value for name, value in os.environ.items()
                   if name not in ('SAM_API_KEY', 'IPUMS_API_KEY')}
    result = subprocess.run(
        [sys.executable, '-c', OFFLINE_IMPORTS, str(data_directory),
         str(extract_original(tmp_path, MONTH)), MONTH, str(original_file(tmp_path))],
        capture_output=True, text=True, cwd=tmp_path, env=environment, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {'codes': [0, 0], 'dotenv_imports': [],
                                         'dotenv_loaded': False, 'environ_unchanged': True}
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [entry.client for entry in entries] == ['manual-import', 'manual-import']


def test_importing_the_command_module_loads_no_census_access_module(tmp_path):
    result = subprocess.run(
        [sys.executable, '-c',
         'import sys; import embedding_data.usaspending_vendor_links; '
         "print('embedding_data.sam_access' in sys.modules, "
         "'embedding_data.ipums_census_access' in sys.modules, 'dotenv' in sys.modules)"],
        capture_output=True, text=True, cwd=tmp_path, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'True False False'
