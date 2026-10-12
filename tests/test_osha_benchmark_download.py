import datetime
from functools import partial
from pathlib import Path
from unittest.mock import patch

import httpx
import polars as pl
import pytest
import typer
from typer.main import get_command

from embedding_data import osha_benchmark_download as osha

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_NAME = 'ITA_Case_Detail_Data_2025_through_08-31-2026.csv'
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


@pytest.fixture
def run_cli(cli_app, cli_runner, output_directory):
    def invoke_cli(handler=osha_server):
        client_factory = partial(osha.make_client, transport=httpx.MockTransport(handler))
        with patch.object(osha, 'make_client', client_factory):
            return cli_runner.invoke(cli_app, ['--out', str(output_directory)])

    return invoke_cli


def test_default_output_is_raw_osha_under_project_root(cli_app):
    command = get_command(cli_app)
    with command.make_context('osha', []) as context:
        assert context.params['out'] == PROJECT_ROOT / 'data/raw/osha'


def test_production_client_uses_http2_and_browser_user_agent():
    # Building the real client fails if the h2 extra is missing; nothing is requested.
    with osha.make_client() as client:
        assert client.headers['User-Agent'] == osha.USER_AGENT
        assert client.follow_redirects


def test_downloads_both_files_and_writes_typed_parquet(run_cli, output_directory):
    result = run_cli()

    assert result.exit_code == 0, result.output
    assert (output_directory / CSV_NAME).read_bytes() == CSV_BYTES
    assert (output_directory / DICTIONARY_NAME).read_bytes() == PDF_BYTES
    assert sorted(path.name for path in output_directory.iterdir()) == sorted(
        [CSV_NAME, DICTIONARY_NAME, CSV_NAME.replace('.csv', '.parquet')]
    )

    data = pl.read_parquet(output_directory / CSV_NAME.replace('.csv', '.parquet'))
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


def test_existing_raw_files_are_not_downloaded_again(run_cli, output_directory):
    output_directory.mkdir()
    (output_directory / CSV_NAME).write_bytes(CSV_BYTES)
    (output_directory / DICTIONARY_NAME).write_bytes(PDF_BYTES)

    def no_requests(request):
        raise AssertionError(f'unexpected request for {request.url}')

    result = run_cli(no_requests)

    assert result.exit_code == 0, result.output
    assert (output_directory / CSV_NAME.replace('.csv', '.parquet')).exists()


def test_refused_download_leaves_no_file(output_directory):
    output_directory.mkdir()
    destination = output_directory / CSV_NAME
    refusing = httpx.MockTransport(lambda request: httpx.Response(403))

    with osha.make_client(transport=refusing) as client, pytest.raises(httpx.HTTPStatusError):
        osha.download(client, osha.CSV_URL, destination)

    assert list(output_directory.iterdir()) == []


def test_truncated_download_leaves_no_file(output_directory):
    output_directory.mkdir()
    destination = output_directory / CSV_NAME
    truncating = httpx.MockTransport(lambda request: streamed(b'ID\r\n', content_length=100))

    with osha.make_client(transport=truncating) as client, pytest.raises(httpx.HTTPError):
        osha.download(client, osha.CSV_URL, destination)

    assert list(output_directory.iterdir()) == []


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


def test_conversion_fails_on_an_unparseable_typed_value(output_directory):
    output_directory.mkdir()
    csv_path = output_directory / CSV_NAME
    csv_path.write_bytes(b'ID,date_of_incident\r\n1,2025-06-09\r\n')

    with pytest.raises(pl.exceptions.InvalidOperationError):
        osha.csv_to_parquet(csv_path)

    assert sorted(path.name for path in output_directory.iterdir()) == [CSV_NAME]
