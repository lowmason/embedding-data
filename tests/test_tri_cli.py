'''The five Stage 5 TRI commands: output, failure line, offline use and exit codes.'''

import io
import json
import subprocess
import sys
from datetime import date
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import dotenv
import httpx
import polars as pl
import pytest
from target_fixtures import forbid_external_access
from tri_fixtures import (
    module_file,
    seed_codes_bundle,
    seed_tri_files,
    subprocess_modules,
    tri_row,
)
from typer.main import get_command

from embedding_data import (
    code_build,
    ita_summary,
    manifest,
    tri_bundle,
    tri_parent_links,
    tri_raw,
    tri_reader,
)
from embedding_data.tri_bundle import TABLES, run_directory
from embedding_data.tri_parent_links import app

PAGE = Path(__file__).parent / 'fixtures/epa_tri/basic_data_files.html'
RAW = 'raw/epa_tri/basic'
SECRET = 'DUNS 123456789 at 1 Main St'


def serve(monkeypatch, page_status: int = 200, file_body: bytes | None = None) -> None:
    '''Serve the fixture page, and file_body or a synthetic body for every other URL.'''
    def respond(request):
        if str(request.url) == tri_raw.PAGE_URL:
            return httpx.Response(page_status, stream=httpx.ByteStream(PAGE.read_bytes()))
        body = f'synthetic {request.url.path}\n'.encode() if file_body is None else file_body
        return httpx.Response(200, headers={'Content-Length': str(len(body))},
                              stream=httpx.ByteStream(body))

    monkeypatch.setattr(tri_raw, 'make_client', partial(
        tri_raw.make_client, transport=httpx.MockTransport(respond)))


def failure(command: str, reason: str) -> str:
    return f'TRI parent links {command} failed: {reason}; run -; path {RAW}\n'


def import_arguments(file: Path, data_directory: Path, year: str = '2023',
                     processed_as_of: str = '2025-11-05') -> list[str]:
    return ['import-file', year, str(file), '--processed-as-of', processed_as_of,
            '--data-dir', str(data_directory)]


def test_acquire_and_import_print_one_json_line(cli_runner, data_directory, monkeypatch,
                                                tmp_path):
    serve(monkeypatch)
    acquired = cli_runner.invoke(app, ['acquire', '--data-dir', str(data_directory)])
    assert acquired.exit_code == 0, acquired.output
    assert acquired.stderr == ''
    assert acquired.stdout == json.dumps([
        f'raw/epa_tri/basic/{y}/2025-11-05/{y}_us.csv' for y in (2022, 2023, 2024)
    ]) + '\n'

    original = tmp_path / 'download (1).csv'
    original.write_bytes(b'synthetic import\n')
    imported = cli_runner.invoke(app, import_arguments(
        original, data_directory, processed_as_of='2026-06-01'))
    assert imported.exit_code == 0, imported.output
    assert imported.stderr == ''
    assert imported.stdout == (
        json.dumps('raw/epa_tri/basic/2023/2026-06-01/2023_us.csv') + '\n')


def test_import_failure_prints_only_the_fixed_line(cli_runner, data_directory, tmp_path):
    file = tmp_path / 'download.csv'
    file.write_bytes(b'synthetic import\n')
    result = cli_runner.invoke(tri_parent_links.app, [
        'import-file', '2021', str(file), '--processed-as-of', '2025-11-05',
        '--data-dir', str(data_directory)])
    assert result.exit_code == 2
    assert result.output.strip() == (
        'TRI parent links import-file failed: validation; run -; path raw/epa_tri/basic')


# Additional coverage beyond the plan tests.

@pytest.mark.parametrize('processed_as_of', ['2025-13-01', 'November 5, 2025'])
def test_a_bad_processed_as_of_date_is_a_validation_failure(cli_runner, data_directory,
                                                            tmp_path, processed_as_of):
    file = tmp_path / 'download.csv'
    file.write_bytes(b'synthetic import\n')
    result = cli_runner.invoke(app, import_arguments(
        file, data_directory, processed_as_of=processed_as_of))
    assert result.exit_code == 2
    assert result.stderr == failure('import-file', 'validation')
    assert result.stdout == ''
    assert not data_directory.exists()


def test_acquire_failure_prints_only_the_fixed_line(cli_runner, data_directory, monkeypatch):
    serve(monkeypatch, page_status=500)
    result = cli_runner.invoke(app, ['acquire', '--data-dir', str(data_directory)])
    assert result.exit_code == 2
    assert result.stderr == failure('acquire', 'network')
    assert result.stdout == ''
    assert not data_directory.exists()


def test_an_empty_download_is_a_validation_failure(cli_runner, data_directory, monkeypatch):
    serve(monkeypatch, file_body=b'')
    result = cli_runner.invoke(app, ['acquire', '--data-dir', str(data_directory)])
    assert result.exit_code == 2
    assert result.stderr == failure('acquire', 'validation')
    assert result.stdout == ''
    assert [path for path in data_directory.rglob('*') if not path.is_dir()] == []


@pytest.mark.parametrize('error,reason', [
    (ValueError(SECRET), 'validation'),
    # Both an OSError and a ValueError: validation is checked first.
    (io.UnsupportedOperation(SECRET), 'validation'),
    (FileExistsError(17, SECRET), 'filesystem'),
    (PermissionError(13, SECRET), 'filesystem'),
    (httpx.ConnectError(SECRET), 'network'),
    (httpx.RemoteProtocolError(SECRET), 'network'),
    (httpx.HTTPStatusError(SECRET, request=httpx.Request('GET', 'https://example.test'),
                           response=httpx.Response(500)), 'network'),
    (RuntimeError(SECRET), 'unexpected'),
    (KeyError(SECRET), 'unexpected'),
], ids=['value', 'unsupported', 'exists', 'permission', 'connect', 'protocol', 'status',
        'runtime', 'key'])
def test_failure_reason_follows_the_exception_type(cli_runner, data_directory, monkeypatch,
                                                   tmp_path, error, reason):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(tri_raw, 'acquire', fail)
    monkeypatch.setattr(tri_raw, 'import_file', fail)
    file = tmp_path / 'download.csv'
    for command, arguments in (
            ('acquire', ['acquire', '--data-dir', str(data_directory)]),
            ('import-file', import_arguments(file, data_directory))):
        result = cli_runner.invoke(app, arguments)
        assert result.exit_code == 2
        assert type(result.exception) is SystemExit
        assert result.stderr == failure(command, reason)
        assert result.stdout == ''
        assert '123456789' not in result.output


@pytest.mark.parametrize('arguments', [
    ['acquire'],
    ['import-file', '2023', 'download.csv', '--processed-as-of', '2025-11-05'],
], ids=['acquire', 'import-file'])
def test_commands_require_an_explicit_data_dir(cli_runner, monkeypatch, arguments):
    # pytest.fail raises a BaseException, which the command guard does not catch.
    def forbidden(*args, **kwargs):
        pytest.fail('a command without --data-dir reached tri_raw')

    monkeypatch.setattr(tri_raw, 'acquire', forbidden)
    monkeypatch.setattr(tri_raw, 'import_file', forbidden)
    result = cli_runner.invoke(app, arguments)
    assert result.exit_code == 2
    assert 'Missing option' in result.output
    assert '--data-dir' in result.output


def test_import_file_opens_no_connection(cli_runner, data_directory, monkeypatch, tmp_path):
    forbid_external_access(monkeypatch)

    def forbidden(*args, **kwargs):
        raise AssertionError('import-file constructed an HTTP client')

    monkeypatch.setattr(tri_raw, 'make_client', forbidden)
    monkeypatch.setattr(httpx.Client, '__init__', forbidden)
    original = tmp_path / 'download.csv'
    original.write_bytes(b'synthetic import\n')
    result = cli_runner.invoke(app, import_arguments(original, data_directory))
    assert result.exit_code == 0, result.output
    assert result.stdout == (
        json.dumps('raw/epa_tri/basic/2023/2025-11-05/2023_us.csv') + '\n')


# The commands `build`, `verify` and `compare-runs` (Task 10).

COMMANDS = ('acquire', 'import-file', 'build', 'verify', 'compare-runs')
DAY = date(2025, 11, 5)
OTHER_DAY = date(2025, 12, 1)
# Made-up D&B numbers that no command may print.
NUMBERS = ('918273645', '936271845', '954637281', '963728154')
CODES_PIN = '1' * 64
OUTPUTS_PIN = '2' * 64
BUNDLES = 'derived/epa_tri/parent-links'


def bundle_path(run_id: str) -> str:
    return f'{BUNDLES}/{run_id}'


def bundle_failure(command: str, reason: str, run_id: str = 'run_1', path: str | None = None):
    path = bundle_path(run_id) if path is None else path
    return f'TRI parent links {command} failed: {reason}; run {run_id}; path {path}\n'


def window_rows(extra: bool = False) -> dict[int, list[dict[str, str]]]:
    '''Two multi-industry parents in three years. `extra` adds a 2024 facility of Pine.'''
    pine = dict(standardized_parent='Pine Holdings', parent_name='Pine Holdings LLC',
                parent_dnb=NUMBERS[0])
    pine_b = dict(pine, parent_dnb=NUMBERS[1])
    rock = dict(standardized_parent='Rock Inc', parent_name='Rock Incorporated',
                parent_dnb=NUMBERS[2])
    rows = {
        2022: [
            tri_row(2022, 'T001', primary_naics='325110', state='TX', **pine),
            tri_row(2022, 'T002', primary_naics='325120', state='TX', **pine_b),
            tri_row(2022, 'T006', primary_naics='324110', state='LA', **rock),
            tri_row(2022, 'T007', primary_naics='325110', state='LA', **rock),
        ],
        2023: [
            tri_row(2023, 'T001', primary_naics='325110', state='TX', **pine),
            tri_row(2023, 'T002', primary_naics='562211', state='TX', **pine_b),
            tri_row(2023, 'T006', primary_naics='324110', state='LA', **rock),
            tri_row(2023, 'T007', primary_naics='325110', state='LA', **rock),
        ],
        2024: [
            tri_row(2024, 'T001', primary_naics='325110', state='TX', **pine),
            tri_row(2024, 'T002', primary_naics='325120', state='TX', **pine_b),
            tri_row(2024, 'T006', primary_naics='324110', state='LA', **rock),
            tri_row(2024, 'T007', primary_naics='325110', state='LA', **rock),
        ],
    }
    if extra:
        rows[2024].append(tri_row(2024, 'T008', primary_naics='325211', state='NJ', **pine))
    return rows


@pytest.fixture(scope='module')
def seeded(tmp_path_factory):
    '''One data root with two snapshots of raw files and the published runs `first` and `other`.

    The two runs build from different rows, so their tables differ and both still verify.
    '''
    root = tmp_path_factory.mktemp('tri_cli')
    data_dir = root / 'data'
    codes_run, codes_pin = seed_codes_bundle(data_dir, root / 'codes-originals')
    seed_tri_files(data_dir, root / 'originals', window_rows(), DAY)
    seed_tri_files(data_dir, root / 'other-originals', window_rows(extra=True), OTHER_DAY)
    state = SimpleNamespace(data_dir=data_dir, codes_run=codes_run, codes_pin=codes_pin)
    state.first = tri_bundle.build(data_dir, 'first', codes_run=codes_run,
                                   codes_outputs_sha256=codes_pin, processed_as_of=DAY)
    state.other = tri_bundle.build(data_dir, 'other', codes_run=codes_run,
                                   codes_outputs_sha256=codes_pin, processed_as_of=OTHER_DAY)
    return state


def invoke(runner, command, data_dir, *arguments):
    return runner.invoke(app, [command, *arguments, '--data-dir', str(data_dir)])


def build_arguments(run_id, state, day=DAY):
    return [run_id, '--codes-run', state.codes_run, '--codes-outputs-sha256', state.codes_pin,
            '--processed-as-of', day.isoformat()]


def one_sorted_line(result):
    '''The parsed single JSON line of stdout, which must be printed with sorted keys.'''
    assert result.stdout.count('\n') == 1
    value = json.loads(result.stdout)
    assert result.stdout == json.dumps(value, sort_keys=True) + '\n'
    return value


def no_publication(data_dir, run_id):
    root = data_dir / BUNDLES
    return not (root / run_id).exists() and not (root / (run_id + '.part')).exists()


def test_help_lists_exactly_five_commands(cli_runner):
    assert [command.name for command in app.registered_commands] == list(COMMANDS)
    assert sorted(get_command(app).commands) == sorted(COMMANDS)
    result = cli_runner.invoke(app, ['--help'])
    assert result.exit_code == 0, result.output
    for command in COMMANDS:
        assert command in result.stdout


def test_build_verify_and_compare_print_one_sorted_json_line(cli_runner, seeded):
    built = invoke(cli_runner, 'build', seeded.data_dir, *build_arguments('printed', seeded))
    assert built.exit_code == 0, built.output
    assert built.stderr == ''
    published = one_sorted_line(built)
    pin = manifest.sha256_file(seeded.data_dir / BUNDLES / 'printed' / 'outputs.json')
    assert published == {'directory': bundle_path('printed'), 'outputs_sha256': pin,
                         'run_id': 'printed'}

    verified = invoke(cli_runner, 'verify', seeded.data_dir, 'printed', '--outputs-sha256', pin)
    assert verified.exit_code == 0, verified.output
    assert verified.stderr == ''
    report = json.loads((seeded.data_dir / BUNDLES / 'printed' / 'report.json').read_text())
    assert one_sorted_line(verified) == {
        'outputs_sha256': pin, 'processed_as_of': '2025-11-05', 'run_id': 'printed',
        'rows': {name: report['tables'][name]['rows'] for name in TABLES}}

    compared = invoke(cli_runner, 'compare-runs', seeded.data_dir, 'first', 'printed')
    assert compared.exit_code == 0, compared.output
    assert compared.stderr == ''
    result = one_sorted_line(compared)
    assert result['equal'] is True
    assert result['report_equal'] is True
    assert result['trust_established'] is False
    assert list(result['tables']) == sorted(TABLES)
    for output in (built, verified, compared):
        assert str(seeded.data_dir) not in output.output
        assert not any(number in output.output for number in NUMBERS)


def test_build_failure_prints_only_the_fixed_line(cli_runner, seeded):
    arguments = build_arguments('bad', seeded)
    arguments[arguments.index('--codes-outputs-sha256') + 1] = CODES_PIN
    result = invoke(cli_runner, 'build', seeded.data_dir, *arguments)
    assert result.exit_code == 2
    assert result.output.strip() == ('TRI parent links build failed: validation; '
                                     'run bad; path derived/epa_tri/parent-links/bad')
    assert result.stderr == bundle_failure('build', 'validation', 'bad')
    assert result.stdout == ''
    assert no_publication(seeded.data_dir, 'bad')


def test_unequal_compare_exits_1(cli_runner, seeded):
    # Two published bundles of different rows: both verify, and the comparison is unequal.
    for run in (seeded.first, seeded.other):
        verified = invoke(cli_runner, 'verify', seeded.data_dir, run['run_id'],
                          '--outputs-sha256', run['outputs_sha256'])
        assert verified.exit_code == 0, verified.output
    result = invoke(cli_runner, 'compare-runs', seeded.data_dir, 'first', 'other')
    assert result.exit_code == 1
    assert type(result.exception) is SystemExit
    assert result.stderr == ''
    compared = one_sorted_line(result)
    assert compared['equal'] is False
    assert compared['trust_established'] is False
    assert any(table['values_equal'] is False for table in compared['tables'].values())


def test_offline_commands_open_no_connection(cli_runner, seeded, data_directory, monkeypatch,
                                             tmp_path):
    forbid_external_access(monkeypatch)

    def forbidden(*args, **kwargs):
        raise AssertionError('an offline command reached outside')

    monkeypatch.setattr(httpx.Client, '__init__', forbidden)
    monkeypatch.setattr(httpx.AsyncClient, '__init__', forbidden)
    monkeypatch.setattr(tri_raw, 'make_client', forbidden)
    monkeypatch.setattr(tri_raw, 'acquire', forbidden)
    monkeypatch.setattr(dotenv, 'dotenv_values', forbidden)
    monkeypatch.setattr(code_build, 'build', forbidden)
    monkeypatch.setattr(ita_summary, 'build_summary_table', forbidden)
    original = tmp_path / 'download.csv'
    original.write_bytes(b'synthetic import\n')
    imported = cli_runner.invoke(app, import_arguments(original, data_directory))
    built = invoke(cli_runner, 'build', seeded.data_dir, *build_arguments('offline', seeded))
    pin = one_sorted_line(built)['outputs_sha256']
    verified = invoke(cli_runner, 'verify', seeded.data_dir, 'offline', '--outputs-sha256', pin)
    compared = invoke(cli_runner, 'compare-runs', seeded.data_dir, 'first', 'offline')
    for command, result in (('import-file', imported), ('build', built), ('verify', verified),
                            ('compare-runs', compared)):
        assert result.exit_code == 0, (command, result.output)
        assert result.stderr == ''


def test_command_module_loads_no_dotenv_or_ipumspy():
    loaded = subprocess_modules('embedding_data.tri_parent_links', prefix=None)
    assert 'embedding_data.tri_bundle' in loaded
    assert 'dotenv' not in loaded and 'ipumspy' not in loaded
    assert not any(name.startswith(('dotenv.', 'ipumspy.')) for name in loaded)


def test_software_files_equal_the_command_import_closure():
    closure = {module_file(module)
               for module in subprocess_modules('embedding_data.tri_parent_links')}
    assert set(tri_bundle.SOFTWARE_FILES) == closure | {
        'src/embedding_data/tri_layouts.json', 'pyproject.toml', 'uv.lock'}


# Additional coverage beyond the plan tests.

def forbid_bundle_operations(monkeypatch):
    # pytest.fail raises a BaseException, which the command guard does not catch.
    def forbidden(*args, **kwargs):
        pytest.fail('a refused command reached the bundle')

    for name in ('build', 'verify_bundle', 'compare_runs'):
        monkeypatch.setattr(tri_bundle, name, forbidden)


def recorder(calls, name, result):
    def record(*args, **kwargs):
        calls.append((name, args, kwargs))
        return result

    return record


def test_commands_wire_arguments_and_print_data_relative_paths(cli_runner, data_directory,
                                                               monkeypatch):
    calls = []
    # Keys out of sorted order, so the printed lines show `sort_keys`.
    built = {'run_id': 'run_1', 'directory': str(run_directory(data_directory, 'run_1')),
             'outputs_sha256': OUTPUTS_PIN}
    verified = {'run_id': 'run_1', 'outputs_sha256': OUTPUTS_PIN,
                'processed_as_of': date(2025, 11, 5), 'rows': {'b': 2, 'a': 1}}
    compared = {'equal': True, 'tables': {}, 'report_equal': True, 'trust_established': False}
    for name, result in (('build', built), ('verify_bundle', verified),
                         ('compare_runs', compared)):
        monkeypatch.setattr(tri_bundle, name, recorder(calls, name, result))

    outputs = {
        'build': invoke(cli_runner, 'build', data_directory, 'run_1', '--codes-run',
                        'codes_run', '--codes-outputs-sha256', CODES_PIN,
                        '--processed-as-of', '2025-11-05'),
        'verify': invoke(cli_runner, 'verify', data_directory, 'run_1', '--outputs-sha256',
                         OUTPUTS_PIN),
        'compare-runs': invoke(cli_runner, 'compare-runs', data_directory, 'run_1', 'run_2'),
    }

    for command, result in outputs.items():
        assert result.exit_code == 0, (command, result.output)
        assert result.stderr == ''
    assert outputs['build'].stdout == json.dumps({
        'directory': bundle_path('run_1'), 'outputs_sha256': OUTPUTS_PIN, 'run_id': 'run_1',
    }, sort_keys=True) + '\n'
    # The date is printed as an ISO string.
    assert outputs['verify'].stdout == json.dumps({
        'outputs_sha256': OUTPUTS_PIN, 'processed_as_of': '2025-11-05',
        'rows': {'a': 1, 'b': 2}, 'run_id': 'run_1',
    }, sort_keys=True) + '\n'
    assert outputs['compare-runs'].stdout == json.dumps(compared, sort_keys=True) + '\n'
    assert calls == [
        ('build', (data_directory, 'run_1'),
         {'codes_run': 'codes_run', 'codes_outputs_sha256': CODES_PIN,
          'processed_as_of': date(2025, 11, 5)}),
        ('verify_bundle', (run_directory(data_directory, 'run_1'), data_directory),
         {'expected_outputs_sha256': OUTPUTS_PIN}),
        ('compare_runs', (run_directory(data_directory, 'run_1'),
                          run_directory(data_directory, 'run_2')), {}),
    ]


def test_the_failure_path_is_the_data_relative_run_directory(data_directory):
    assert run_directory(data_directory, 'run_1').relative_to(
        data_directory).as_posix() == bundle_path('run_1')


@pytest.mark.parametrize('command,arguments,run_id,path', [
    ('build', ['run_1', '--codes-run', 'codes_run', '--codes-outputs-sha256', CODES_PIN,
               '--processed-as-of', '2025-11-05'], 'run_1', bundle_path('run_1')),
    ('verify', ['run_1', '--outputs-sha256', OUTPUTS_PIN], 'run_1', bundle_path('run_1')),
    ('compare-runs', ['run_1', 'run_2'], 'run_1,run_2',
     f'{bundle_path("run_1")},{bundle_path("run_2")}'),
], ids=['build', 'verify', 'compare-runs'])
@pytest.mark.parametrize('error,reason', [
    (ValueError(SECRET), 'validation'),
    (io.UnsupportedOperation(SECRET), 'validation'),
    (FileNotFoundError(2, SECRET), 'filesystem'),
    (PermissionError(13, SECRET), 'filesystem'),
    (httpx.ConnectError(SECRET), 'network'),
    (RuntimeError(SECRET), 'unexpected'),
    (pl.exceptions.ComputeError(SECRET), 'unexpected'),
    (KeyError(SECRET), 'unexpected'),
], ids=['value', 'unsupported', 'missing_file', 'permission', 'connect', 'runtime', 'polars',
        'key'])
def test_every_command_prints_only_the_fixed_failure_line(
        cli_runner, data_directory, monkeypatch, command, arguments, run_id, path, error,
        reason):
    def fail(*args, **kwargs):
        raise error

    for name in ('build', 'verify_bundle', 'compare_runs'):
        monkeypatch.setattr(tri_bundle, name, fail)
    result = invoke(cli_runner, command, data_directory, *arguments)
    assert result.exit_code == 2
    assert type(result.exception) is SystemExit
    assert result.stderr == bundle_failure(command, reason, run_id, path)
    assert result.stdout == ''
    assert '123456789' not in result.output
    assert not data_directory.exists()


def test_a_polars_error_while_reading_a_raw_file_prints_only_the_unexpected_line(
        cli_runner, seeded, monkeypatch):
    def fail(*args, **kwargs):
        raise pl.exceptions.ComputeError(SECRET)

    monkeypatch.setattr(tri_reader, 'read_window', fail)
    built = invoke(cli_runner, 'build', seeded.data_dir, *build_arguments('unread', seeded))
    assert built.exit_code == 2
    assert built.stderr == bundle_failure('build', 'unexpected', 'unread')
    assert built.stdout == ''
    assert no_publication(seeded.data_dir, 'unread')
    verified = invoke(cli_runner, 'verify', seeded.data_dir, 'first', '--outputs-sha256',
                      seeded.first['outputs_sha256'])
    assert verified.exit_code == 2
    assert verified.stderr == bundle_failure('verify', 'unexpected', 'first')
    assert verified.stdout == ''
    for result in (built, verified):
        assert '123456789' not in result.output
        assert 'DUNS' not in result.output
        assert 'Main St' not in result.output


@pytest.mark.parametrize('processed_as_of', ['2025-13-01', 'November 5, 2025', ''])
def test_a_bad_build_date_is_a_validation_failure_before_any_work(
        cli_runner, data_directory, monkeypatch, processed_as_of):
    forbid_bundle_operations(monkeypatch)
    result = invoke(cli_runner, 'build', data_directory, 'run_1', '--codes-run', 'codes_run',
                    '--codes-outputs-sha256', CODES_PIN, '--processed-as-of', processed_as_of)
    assert result.exit_code == 2
    assert result.stderr == bundle_failure('build', 'validation')
    assert result.stdout == ''
    assert not data_directory.exists()


@pytest.mark.parametrize('command,arguments,run_id,path', [
    ('build', ['../escape', '--codes-run', 'codes_run', '--codes-outputs-sha256', CODES_PIN,
               '--processed-as-of', '2025-11-05'], '../escape', f'{BUNDLES}/../escape'),
    ('verify', ['../escape', '--outputs-sha256', OUTPUTS_PIN], '../escape',
     f'{BUNDLES}/../escape'),
    ('compare-runs', ['../escape', 'run_2'], '../escape,run_2',
     f'{BUNDLES}/../escape,{bundle_path("run_2")}'),
    ('compare-runs', ['run_1', 'a b'], 'run_1,a b', f'{bundle_path("run_1")},{BUNDLES}/a b'),
], ids=['build', 'verify', 'compare-first', 'compare-second'])
def test_an_unsafe_run_id_gives_the_fixed_line_and_writes_nothing(
        cli_runner, data_directory, command, arguments, run_id, path):
    result = invoke(cli_runner, command, data_directory, *arguments)
    assert result.exit_code == 2
    assert result.stderr == bundle_failure(command, 'validation', run_id, path)
    assert result.stdout == ''
    assert not data_directory.exists()


@pytest.mark.parametrize('command,arguments', [
    ('build', ['--codes-run', 'codes_run', '--codes-outputs-sha256', CODES_PIN,
               '--processed-as-of', '2025-11-05']),
    ('build', ['run_1', '--codes-outputs-sha256', CODES_PIN, '--processed-as-of',
               '2025-11-05']),
    ('build', ['run_1', '--codes-run', 'codes_run', '--processed-as-of', '2025-11-05']),
    ('build', ['run_1', '--codes-run', 'codes_run', '--codes-outputs-sha256', CODES_PIN]),
    ('verify', ['run_1']),
    ('verify', ['--outputs-sha256', OUTPUTS_PIN]),
    ('compare-runs', ['run_1']),
], ids=['build_run_id', 'build_codes_run', 'build_codes_pin', 'build_date', 'verify_pin',
        'verify_run_id', 'compare_second'])
def test_each_required_argument_fails_before_work(cli_runner, data_directory, monkeypatch,
                                                  command, arguments):
    forbid_bundle_operations(monkeypatch)
    result = invoke(cli_runner, command, data_directory, *arguments)
    assert result.exit_code == 2, result.output
    assert 'Missing' in result.output
    assert not data_directory.exists()


@pytest.mark.parametrize('command,arguments', [
    ('build', ['run_1', '--codes-run', 'codes_run', '--codes-outputs-sha256', CODES_PIN,
               '--processed-as-of', '2025-11-05']),
    ('verify', ['run_1', '--outputs-sha256', OUTPUTS_PIN]),
    ('compare-runs', ['run_1', 'run_2']),
], ids=['build', 'verify', 'compare-runs'])
def test_data_dir_is_required(cli_runner, monkeypatch, tmp_path, command, arguments):
    forbid_bundle_operations(monkeypatch)
    monkeypatch.chdir(tmp_path)
    result = cli_runner.invoke(app, [command, *arguments])
    assert result.exit_code == 2
    assert 'Missing option' in result.output
    assert '--data-dir' in result.output
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('command,arguments,run_id,path', [
    ('verify', ['run_1', '--outputs-sha256', OUTPUTS_PIN], 'run_1', bundle_path('run_1')),
    ('compare-runs', ['run_1', 'run_2'], 'run_1,run_2',
     f'{bundle_path("run_1")},{bundle_path("run_2")}'),
], ids=['verify', 'compare-runs'])
def test_verify_and_compare_refuse_an_empty_data_root_with_a_validation_line(
        cli_runner, data_directory, command, arguments, run_id, path):
    result = invoke(cli_runner, command, data_directory, *arguments)
    assert result.exit_code == 2
    assert result.stderr == bundle_failure(command, 'validation', run_id, path)
    assert result.stdout == ''
    assert no_publication(data_directory, 'run_1')


def tree_snapshot(root):
    '''Every path under root, with the bytes of each file and None for each directory.'''
    return sorted((path.relative_to(root).as_posix(), path.read_bytes() if path.is_file()
                   else None) for path in root.rglob('*'))


@pytest.mark.parametrize('occupied', ['run_1.part', 'run_1'], ids=['staging', 'final'])
def test_build_failure_keeps_occupied_run_paths(cli_runner, data_directory, occupied):
    root = data_directory / BUNDLES
    (root / occupied).mkdir(parents=True)
    (root / occupied / 'kept.txt').write_bytes(b'owner evidence\n')
    before = tree_snapshot(root)
    result = invoke(cli_runner, 'build', data_directory, 'run_1', '--codes-run', 'codes_run',
                    '--codes-outputs-sha256', CODES_PIN, '--processed-as-of', '2025-11-05')
    assert result.exit_code == 2
    assert result.stderr == bundle_failure('build', 'validation')
    assert result.stdout == ''
    assert tree_snapshot(root) == before


def test_verify_refuses_a_wrong_pin_and_compare_refuses_a_missing_run(cli_runner, seeded):
    verified = invoke(cli_runner, 'verify', seeded.data_dir, 'first', '--outputs-sha256',
                      OUTPUTS_PIN)
    assert verified.exit_code == 2
    assert verified.stderr == bundle_failure('verify', 'validation', 'first')
    compared = invoke(cli_runner, 'compare-runs', seeded.data_dir, 'first', 'absent')
    assert compared.exit_code == 2
    assert compared.stderr == bundle_failure(
        'compare-runs', 'validation', 'first,absent',
        f'{bundle_path("first")},{bundle_path("absent")}')
    assert compared.stdout == ''


def test_compare_unequal_exits_1_outside_the_failure_guard(cli_runner, data_directory,
                                                           monkeypatch):
    compared = {'equal': False, 'report_equal': False, 'tables': {},
                'trust_established': False}
    monkeypatch.setattr(tri_bundle, 'compare_runs', lambda first, second: compared)
    result = invoke(cli_runner, 'compare-runs', data_directory, 'run_1', 'run_2')
    assert result.exit_code == 1
    assert type(result.exception) is SystemExit
    assert result.exception.code == 1
    assert result.stdout == json.dumps(compared, sort_keys=True) + '\n'
    assert result.stderr == ''


def test_top_level_cli_does_not_register_the_tri_commands():
    from embedding_data import cli

    assert all(command.callback.__module__ != tri_parent_links.__name__
               for command in cli.app.registered_commands)
    assert all(group.typer_instance is not app for group in cli.app.registered_groups)
    assert not {'build', 'verify', 'compare-runs', 'import-file'} & set(
        get_command(cli.app).commands)


def test_app_disables_pretty_exceptions_and_locals():
    assert app.pretty_exceptions_enable is False
    assert app.pretty_exceptions_show_locals is False


def test_module_runs_with_python_m(tmp_path):
    result = subprocess.run(
        [sys.executable, '-m', 'embedding_data.tri_parent_links', '--help'],
        capture_output=True, text=True, cwd=tmp_path, check=False)
    assert result.returncode == 0, result.stderr
    for command in COMMANDS:
        assert command in result.stdout
