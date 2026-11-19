'''The Stage 5 TRI commands `acquire` and `import-file`: output, failure line and offline use.'''

import io
import json
from functools import partial
from pathlib import Path

import httpx
import pytest
from target_fixtures import forbid_external_access

from embedding_data import tri_parent_links, tri_raw
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
