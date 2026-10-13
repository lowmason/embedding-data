import datetime
import hashlib
import shlex
from functools import partial
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

import httpx
import polars as pl
import pytest
import typer
from typer.main import get_command

from embedding_data import manifest, paths
from embedding_data import osha_benchmark_download as osha

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_NAME = 'ITA_Case_Detail_Data_2025_through_08-31-2026.csv'
PARQUET_NAME = CSV_NAME.replace('.csv', '.parquet')
DICTIONARY_NAME = 'case_detail_data_dictionary_2026.pdf'
PDF_BYTES = b'%PDF-1.6 fixture'

# One delivered row in miniature: a 4-digit ZIP that lost its leading zero upstream,
# an EIN with a leading zero, OSHA's 00-9900 placeholder SOC, an Int32-overflowing
# hours total, and a narrative mixing a Windows-1252 apostrophe with a UTF-8 one.
CSV_BYTES = (
    b'ID,ein,zip_code,naics_code,Size,total_hours_worked,date_of_incident,'
    b'date_of_death,time_of_incident,SOC_code,SOC_probability,'
    b'Unexpected_NAICS_SOC_Combo,New_nar_what_happened\r\n'
    b'1669828,012345678,2134,622110,22,5050596989,6/9/2025,,5:00,00-9900,0.91495013,'
    b'Y?,didn\x92t see the resident\xe2\x80\x99s cane\r\n'
)


@pytest.fixture
def cli_app():
    app = getattr(osha, 'app', None)
    assert isinstance(app, typer.Typer)
    return app


def streamed(body, content_length=None):
    '''A response whose body arrives over the transport, as it does from the network.'''
    length = len(body) if content_length is None else content_length
    return httpx.Response(
        200, headers={'Content-Length': str(length)}, stream=httpx.ByteStream(body)
    )


def osha_server(request):
    '''Serve the two files, refusing non-browser user agents as OSHA's CDN does.'''
    if not request.headers['User-Agent'].startswith('Mozilla/5.0'):
        return httpx.Response(403, html='<h1>403 ERROR</h1>')
    if request.url == osha.CSV_URL:
        return streamed(CSV_BYTES)
    if request.url == osha.DICTIONARY_URL:
        return streamed(PDF_BYTES)
    return httpx.Response(404)


def no_requests(request):
    raise AssertionError(f'unexpected request for {request.url}')


@pytest.fixture
def run_cli(cli_app, cli_runner, data_directory):
    def invoke_cli(handler=osha_server, data_dir=None):
        client_factory = partial(osha.make_client, transport=httpx.MockTransport(handler))
        with patch.object(osha, 'make_client', client_factory):
            return cli_runner.invoke(cli_app, ['--data-dir', str(data_dir or data_directory)])

    return invoke_cli


def test_default_data_root_is_under_project_root(cli_app):
    command = get_command(cli_app)
    with command.make_context('osha', []) as context:
        assert context.params['data_dir'] == PROJECT_ROOT / 'data'


def test_production_client_uses_http2_and_browser_user_agent():
    # Building the real client fails if the h2 extra is missing; nothing is requested.
    with osha.make_client() as client:
        assert client.headers['User-Agent'] == osha.USER_AGENT
        assert client.follow_redirects


def test_downloads_both_files_to_raw_and_writes_typed_parquet_to_derived(
    run_cli, data_directory,
):
    result = run_cli()

    assert result.exit_code == 0, result.output
    raw = data_directory / 'raw/osha'
    assert (raw / CSV_NAME).read_bytes() == CSV_BYTES
    assert (raw / DICTIONARY_NAME).read_bytes() == PDF_BYTES
    assert sorted(path.name for path in raw.iterdir()) == sorted([CSV_NAME, DICTIONARY_NAME])
    derived = data_directory / 'derived/osha'
    assert sorted(path.name for path in derived.iterdir()) == [PARQUET_NAME]

    data = pl.read_parquet(derived / PARQUET_NAME)
    assert data.schema == {
        'ID': pl.Int64,
        'ein': pl.String,
        'zip_code': pl.String,
        'naics_code': pl.String,
        'Size': pl.Int64,
        'total_hours_worked': pl.Int64,
        'date_of_incident': pl.Date,
        'date_of_death': pl.Date,
        'time_of_incident': pl.Time,
        'SOC_code': pl.String,
        'SOC_probability': pl.Float64,
        'Unexpected_NAICS_SOC_Combo': pl.String,
        'New_nar_what_happened': pl.String,
    }
    assert data.row(0) == (
        1669828, '012345678', '2134', '622110', 22, 5050596989,
        datetime.date(2025, 6, 9), None, datetime.time(5, 0),
        '00-9900', 0.91495013, 'Y?', 'didn’t see the resident’s cane',
    )


def test_each_download_is_recorded_with_its_url_hash_and_client(run_cli, data_directory):
    result = run_cli()

    assert result.exit_code == 0, result.output
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [(entry.path, entry.source_url) for entry in entries] == [
        (f'osha/{DICTIONARY_NAME}', osha.DICTIONARY_URL),
        (f'osha/{CSV_NAME}', osha.CSV_URL),
    ]
    for entry, body in zip(entries, [PDF_BYTES, CSV_BYTES], strict=True):
        assert entry.sha256 == hashlib.sha256(body).hexdigest()
        assert entry.size == len(body)
        assert (entry.client, entry.client_version) == ('httpx', version('httpx'))
        assert (entry.collection, entry.extract_number, entry.samples) == (None, None, ())
        assert entry.proxies == ()
        retrieved_at = datetime.datetime.fromisoformat(entry.retrieved_at)
        assert retrieved_at.utcoffset() == datetime.timedelta(0)


def test_existing_raw_files_are_neither_downloaded_nor_recorded_again(run_cli, data_directory):
    raw = data_directory / 'raw/osha'
    raw.mkdir(parents=True)
    (raw / CSV_NAME).write_bytes(CSV_BYTES)
    (raw / DICTIONARY_NAME).write_bytes(PDF_BYTES)

    result = run_cli(no_requests)

    assert result.exit_code == 0, result.output
    assert (data_directory / 'derived/osha' / PARQUET_NAME).exists()
    assert manifest.read_manifest(paths.manifest_path(data_directory)) == []


def test_unrecorded_existing_raw_files_are_reported_but_not_recorded(run_cli, data_directory):
    raw = data_directory / 'raw/osha'
    raw.mkdir(parents=True)
    (raw / CSV_NAME).write_bytes(CSV_BYTES)
    (raw / DICTIONARY_NAME).write_bytes(PDF_BYTES)

    result = run_cli(no_requests)

    assert result.exit_code == 0, result.output
    warnings = [line for line in result.stderr.splitlines() if 'warning' in line]
    assert len(warnings) == 2
    for name, line in zip([DICTIONARY_NAME, CSV_NAME], warnings, strict=True):
        assert name in line
        assert 'uv run --locked python -m embedding_data.raw_backfill' in line
    assert 'warning' not in result.stdout
    assert manifest.read_manifest(paths.manifest_path(data_directory)) == []


def test_the_suggested_backfill_command_quotes_the_data_root(run_cli, tmp_path):
    data_dir = tmp_path / 'my data'
    raw = data_dir / 'raw/osha'
    raw.mkdir(parents=True)
    (raw / CSV_NAME).write_bytes(CSV_BYTES)
    (raw / DICTIONARY_NAME).write_bytes(PDF_BYTES)

    result = run_cli(no_requests, data_dir=data_dir)

    assert result.exit_code == 0, result.output
    warnings = result.stderr.splitlines()
    assert len(warnings) == 2
    for line in warnings:
        command = line.partition('to record it, run ')[2]
        assert command.startswith(osha.BACKFILL_COMMAND)
        assert shlex.split(command)[-2:] == ['--data-dir', str(data_dir)]


def test_only_the_existing_raw_file_missing_from_the_manifest_is_reported(
    run_cli, data_directory,
):
    raw = data_directory / 'raw/osha'
    raw.mkdir(parents=True)
    (raw / CSV_NAME).write_bytes(CSV_BYTES)
    (raw / DICTIONARY_NAME).write_bytes(PDF_BYTES)
    manifest_path = paths.manifest_path(data_directory)
    recorded = manifest.describe_file(
        raw / DICTIONARY_NAME,
        manifest_path.parent,
        retrieved_at=datetime.datetime.now(datetime.UTC),
        client='httpx',
        client_version=version('httpx'),
        source_url=osha.DICTIONARY_URL,
    )
    manifest.append_entries(manifest_path, [recorded])

    result = run_cli(no_requests)

    assert result.exit_code == 0, result.output
    assert CSV_NAME in result.stderr
    assert DICTIONARY_NAME not in result.stderr
    assert manifest.read_manifest(manifest_path) == [recorded]


def test_recorded_raw_files_are_not_reported(run_cli, data_directory):
    first = run_cli()
    assert first.exit_code == 0, first.output
    assert 'warning' not in first.output

    second = run_cli(no_requests)

    assert second.exit_code == 0, second.output
    assert 'exists, keeping it as delivered' in second.stdout
    assert second.stderr == ''
    assert 'raw_backfill' not in second.output


def test_a_missing_raw_file_with_a_record_is_not_downloaded_again(run_cli, data_directory):
    raw = data_directory / 'raw/osha'
    raw.mkdir(parents=True)
    csv_path = raw / CSV_NAME
    csv_path.write_bytes(CSV_BYTES)
    manifest_path = paths.manifest_path(data_directory)
    recorded = manifest.describe_file(
        csv_path,
        manifest_path.parent,
        retrieved_at=datetime.datetime.now(datetime.UTC),
        client='httpx',
        client_version=version('httpx'),
        source_url=osha.CSV_URL,
    )
    manifest.append_entries(manifest_path, [recorded])
    before = manifest_path.read_bytes()
    csv_path.unlink()

    # The dictionary is absent and unrecorded too, yet nothing is requested.
    result = run_cli(no_requests)

    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, SystemExit), result.exception
    assert CSV_NAME in result.stderr
    assert f'{recorded.sha256[:12]}...' in result.stderr
    assert 'will not re-download' in result.stderr
    assert list(raw.iterdir()) == []
    assert manifest_path.read_bytes() == before
    assert not (data_directory / 'derived').exists()


def test_a_second_run_neither_downloads_nor_reconverts(run_cli, data_directory):
    first = run_cli()
    assert first.exit_code == 0, first.output
    parquet = data_directory / 'derived/osha' / PARQUET_NAME
    converted = (parquet.read_bytes(), parquet.stat().st_mtime_ns)
    recorded = paths.manifest_path(data_directory).read_bytes()

    second = run_cli(no_requests)

    assert second.exit_code == 0, second.output
    assert 'not converting again' in second.output
    assert (parquet.read_bytes(), parquet.stat().st_mtime_ns) == converted
    assert paths.manifest_path(data_directory).read_bytes() == recorded


def test_refused_download_leaves_no_file(tmp_path):
    destination = tmp_path / CSV_NAME
    refusing = httpx.MockTransport(lambda request: httpx.Response(403))

    with osha.make_client(transport=refusing) as client, pytest.raises(httpx.HTTPStatusError):
        osha.download(client, osha.CSV_URL, destination)

    assert list(tmp_path.iterdir()) == []


def test_truncated_download_leaves_no_file(tmp_path):
    destination = tmp_path / CSV_NAME
    truncating = httpx.MockTransport(lambda request: streamed(b'ID\r\n', content_length=100))

    with osha.make_client(transport=truncating) as client, pytest.raises(httpx.HTTPError):
        osha.download(client, osha.CSV_URL, destination)

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        (b'plain ascii\r\n', 'plain ascii\r\n'),
        (b'resident\xe2\x80\x99s\r\n', 'resident’s\r\n'),
        (b'didn\x92t\r\n', 'didn’t\r\n'),
        (b'Garc\xeda, \x93quoted\x94 \x96 dash\r\n', 'García, “quoted” – dash\r\n'),
        (b'didn\x92t see the resident\xe2\x80\x99s cane', 'didn’t see the resident’s cane'),
    ],
    ids=['ascii', 'utf8', 'cp1252', 'cp1252-accents-and-punctuation', 'mixed-in-one-line'],
)
def test_decode_line_reads_utf8_and_windows_1252(raw, expected):
    assert osha.decode_line(raw) == expected


def test_decode_line_fails_on_a_byte_undefined_in_windows_1252():
    with pytest.raises(UnicodeDecodeError):
        osha.decode_line(b'neither UTF-8 nor cp1252: \x81\r\n')


def test_conversion_fails_on_an_unparseable_typed_value(tmp_path):
    csv_path = tmp_path / 'raw' / CSV_NAME
    csv_path.parent.mkdir()
    csv_path.write_bytes(b'ID,date_of_incident\r\n1,2025-06-09\r\n')
    derived = tmp_path / 'derived'

    with pytest.raises(pl.exceptions.InvalidOperationError):
        osha.csv_to_parquet(csv_path, derived / PARQUET_NAME)

    assert sorted(path.name for path in csv_path.parent.iterdir()) == [CSV_NAME]
    assert list(derived.iterdir()) == []
