'''The Stage 14 command group so far: subaward acquisition and import, their JSON line, exit
codes and fixed failure line.'''

import json
import subprocess
import sys

import httpx
import pytest
import typer
from vendor_link_fixtures import (  # noqa: F401
    NAME,
    FakeUsaspending,
    install_usaspending,
    no_live_sam,
    sample_zip,
)

from embedding_data import manifest, paths, usaspending_raw, usaspending_vendor_links

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
