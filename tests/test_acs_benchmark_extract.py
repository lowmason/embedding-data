import dataclasses
import gzip
import hashlib
import json
from datetime import datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest
import typer
from typer.main import get_command

from embedding_data import acs_benchmark_extract as benchmark
from embedding_data import manifest, paths

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_CSV = 'INDNAICS,OCCSOC,INCWAGE_CPIU_2010\n31M,1110XX,12.5\n'
pytestmark = pytest.mark.usefixtures('cli_runner')


def cli_app():
    app = getattr(benchmark, 'app', None)
    assert isinstance(app, typer.Typer)
    return app


def tree(root):
    '''Every file under root with its bytes, to prove a run left them untouched.'''
    return {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}


def write_delivery(extract, *, download_dir):
    '''Fake IPUMS delivery: the data file and codebook, named for the extract number.'''
    name = f'usa_{extract.extract_id:05d}'
    with gzip.open(download_dir / f'{name}.csv.gz', 'wt') as csv_file:
        csv_file.write(FIXTURE_CSV)
    (download_dir / f'{name}.xml').write_text('<codeBook/>\n')


@pytest.fixture
def run_live(cli_runner, data_directory, dotenv_path):
    '''Run the ACS command for real against a fake IPUMS client that numbers the extract.'''
    dotenv_path.write_text('IPUMS_API_KEY=dotenv-test-key\n')

    def invoke(arguments=(), *, extract_id=123, download=write_delivery, wait=None):
        with (
            patch.object(benchmark, 'DOTENV_PATH', dotenv_path),
            patch.object(benchmark, 'IpumsApiClient', autospec=True) as client_factory,
        ):
            client = client_factory.return_value
            client.submit_extract.side_effect = lambda extract: setattr(extract, '_id', extract_id)
            client.wait_for_extract.side_effect = wait
            client.download_extract.side_effect = download
            result = cli_runner.invoke(
                cli_app(), [*arguments, '--data-dir', str(data_directory)]
            )
        return result, client_factory

    return invoke


def test_default_paths_point_to_project_root():
    command = get_command(cli_app())
    with command.make_context('benchmark', ['--dry-run']) as context:
        assert context.params['data_dir'] == PROJECT_ROOT / 'data'
    assert benchmark.DOTENV_PATH == PROJECT_ROOT / '.env'


def test_help_describes_the_benchmark(cli_runner):
    result = cli_runner.invoke(cli_app(), ['--help'])

    assert result.exit_code == 0, result.output
    assert 'IPUMS USA extracts' in result.output


def test_dry_run_defaults_to_core_without_credentials(cli_runner, data_directory):
    result = cli_runner.invoke(cli_app(), ['--dry-run', '--data-dir', str(data_directory)])

    assert result.exit_code == 0, result.output
    definition = json.loads((data_directory / 'preview/acs/core/extract.json').read_text())
    assert set(definition['samples']) == {'us2023a', 'us2024a'}
    assert definition['dataFormat'] == 'csv'
    assert definition['dataQualityFlags']
    assert not (data_directory / 'raw').exists()


def test_dry_run_accepts_multiple_extracts(cli_runner, data_directory):
    result = cli_runner.invoke(
        cli_app(),
        ['core', 'vintage', 'five_year', '--dry-run', '--data-dir', str(data_directory)],
    )

    assert result.exit_code == 0, result.output
    for name, samples in benchmark.SAMPLE_SETS.items():
        preview = data_directory / 'preview/acs' / name / 'extract.json'
        assert set(json.loads(preview.read_text())['samples']) == set(samples), name


def test_unknown_extract_exits_before_writing_files(cli_runner, data_directory):
    result = cli_runner.invoke(
        cli_app(), ['unknown', '--dry-run', '--data-dir', str(data_directory)],
    )

    assert result.exit_code == 2, result.output
    assert 'unknown extract(s): unknown' in result.output
    assert not data_directory.exists()


@pytest.mark.parametrize('contents', [None, 'IPUMS_API_KEY=\n'], ids=['missing', 'empty'])
def test_missing_or_empty_key_exits_with_dotenv_instructions(
    cli_runner, data_directory, dotenv_path, contents,
):
    app = cli_app()
    if contents is not None:
        dotenv_path.write_text(contents)
    with patch.object(benchmark, 'DOTENV_PATH', dotenv_path):
        result = cli_runner.invoke(app, ['--data-dir', str(data_directory)])

    assert result.exit_code == 1, result.output
    assert 'IPUMS_API_KEY' in result.output
    assert str(dotenv_path) in result.output
    assert not data_directory.exists()


@pytest.mark.parametrize(
    'environment_key', [None, 'environment-test-key'], ids=['dotenv', 'environment'],
)
def test_dotenv_key_is_loaded_with_environment_taking_precedence(
    run_live, monkeypatch, environment_key,
):
    if environment_key is not None:
        monkeypatch.setenv('IPUMS_API_KEY', environment_key)

    result, client_factory = run_live()

    assert result.exit_code == 0, result.output
    client_factory.assert_called_once_with(environment_key or 'dotenv-test-key')


def test_delivery_gets_its_own_raw_directory_and_converts_outside_raw(
    run_live, data_directory,
):
    result, _ = run_live()

    assert result.exit_code == 0, result.output
    extract_directory = data_directory / 'raw/acs/core/usa_00123'
    assert sorted(path.name for path in extract_directory.iterdir()) == [
        'extract.json', 'usa_00123.csv.gz', 'usa_00123.xml',
    ]
    definition = json.loads((extract_directory / 'extract.json').read_text())
    assert list(definition['samples']) == ['us2023a', 'us2024a']
    derived = data_directory / 'derived/acs/core'
    assert sorted(path.name for path in derived.iterdir()) == ['usa_00123.parquet']
    assert pl.read_parquet(derived / 'usa_00123.parquet').row(0) == ('31M', '1110XX', 12.5)
    raw_files = [path for path in (data_directory / 'raw').rglob('*') if path.is_file()]
    assert [path for path in raw_files if path.suffix in {'.parquet', '.csv'}] == []


def test_every_delivered_file_is_recorded_in_the_raw_manifest(run_live, data_directory):
    result, _ = run_live()

    assert result.exit_code == 0, result.output
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [entry.path for entry in entries] == [
        'acs/core/usa_00123/extract.json',
        'acs/core/usa_00123/usa_00123.csv.gz',
        'acs/core/usa_00123/usa_00123.xml',
    ]
    for entry in entries:
        delivered = data_directory / 'raw' / entry.path
        assert entry.sha256 == hashlib.sha256(delivered.read_bytes()).hexdigest()
        assert entry.size == delivered.stat().st_size
        assert (entry.collection, entry.extract_number) == ('usa', 123)
        assert entry.samples == ('us2023a', 'us2024a')
        assert (entry.client, entry.client_version) == ('ipumspy', version('ipumspy'))
        assert (entry.source_url, entry.proxies) == (None, ())
        assert datetime.fromisoformat(entry.retrieved_at).utcoffset() == timedelta(0)


def test_a_second_run_leaves_the_earlier_delivery_untouched(run_live, data_directory):
    first, _ = run_live(extract_id=123)
    assert first.exit_code == 0, first.output
    earlier = tree(data_directory / 'raw/acs/core/usa_00123')
    parquet = data_directory / 'derived/acs/core/usa_00123.parquet'
    converted = (parquet.read_bytes(), parquet.stat().st_mtime_ns)

    second, _ = run_live(extract_id=124)

    assert second.exit_code == 0, second.output
    assert tree(data_directory / 'raw/acs/core/usa_00123') == earlier
    assert (parquet.read_bytes(), parquet.stat().st_mtime_ns) == converted
    assert (data_directory / 'derived/acs/core/usa_00124.parquet').exists()
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [entry.extract_number for entry in entries] == [123] * 3 + [124] * 3


def test_an_existing_extract_directory_is_never_overwritten(run_live, data_directory):
    first, _ = run_live(extract_id=123)
    assert first.exit_code == 0, first.output
    before = tree(data_directory)

    second, client_factory = run_live(extract_id=123)

    assert isinstance(second.exception, FileExistsError), second.output
    client_factory.return_value.download_extract.assert_not_called()
    assert tree(data_directory) == before


def assert_not_delivered(data_directory):
    '''A failed delivery leaves no extract directory, no record, and no Parquet.'''
    assert not (data_directory / 'raw/acs/core/usa_00123').exists()
    assert not paths.manifest_path(data_directory).exists()
    assert not (data_directory / 'derived').exists()


def test_a_failed_wait_leaves_no_delivery(run_live, data_directory):
    result, _ = run_live(wait=RuntimeError('extract failed'))

    assert isinstance(result.exception, RuntimeError), result.output
    assert_not_delivered(data_directory)


def test_a_dropped_download_leaves_its_partial_file_in_staging(run_live, data_directory):
    def drop_connection(extract, *, download_dir):
        (download_dir / 'usa_00123.csv.gz').write_bytes(b'\x1f\x8b truncated')
        raise ConnectionError('connection dropped')

    result, _ = run_live(download=drop_connection)

    assert isinstance(result.exception, ConnectionError), result.output
    assert_not_delivered(data_directory)
    assert (data_directory / 'raw/acs/core/usa_00123.part/usa_00123.csv.gz').exists()


def test_a_delivery_without_its_codebook_is_not_moved_into_place(run_live, data_directory):
    def omit_codebook(extract, *, download_dir):
        write_delivery(extract, download_dir=download_dir)
        (download_dir / 'usa_00123.xml').unlink()

    result, _ = run_live(download=omit_codebook)

    assert isinstance(result.exception, FileNotFoundError), result.output
    assert 'usa_00123.xml' in str(result.exception)
    assert_not_delivered(data_directory)
    assert (data_directory / 'raw/acs/core/usa_00123.part/usa_00123.csv.gz').exists()


def test_a_failure_to_hash_the_delivery_leaves_it_in_staging(run_live, data_directory):
    with patch.object(manifest, 'describe_file', side_effect=OSError('read error')):
        result, _ = run_live()

    assert isinstance(result.exception, OSError), result.output
    assert_not_delivered(data_directory)
    assert (data_directory / 'raw/acs/core/usa_00123.part/usa_00123.csv.gz').exists()


@pytest.mark.parametrize(
    'manifest_line',
    [
        json.dumps(
            dataclasses.asdict(
                manifest.ManifestEntry(
                    path='acs/core/usa_00123/extract.json',
                    sha256='0' * 64,
                    size=0,
                    retrieved_at='2026-01-01T00:00:00+00:00',
                    client='ipumspy',
                    client_version='0',
                )
            )
        ),
        'not json',
    ],
    ids=['already-recorded', 'malformed'],
)
def test_a_manifest_that_refuses_the_delivery_leaves_it_in_staging(
    run_live, data_directory, manifest_line,
):
    manifest_path = paths.manifest_path(data_directory)
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(manifest_line + '\n')
    recorded = manifest_path.read_bytes()

    result, _ = run_live()

    assert isinstance(result.exception, ValueError), result.output
    assert not (data_directory / 'raw/acs/core/usa_00123').exists()
    assert (data_directory / 'raw/acs/core/usa_00123.part/usa_00123.csv.gz').exists()
    assert manifest_path.read_bytes() == recorded
    assert not (data_directory / 'derived').exists()


def test_only_the_three_expected_files_are_recorded(run_live, data_directory):
    def deliver_with_finder_metadata(extract, *, download_dir):
        write_delivery(extract, download_dir=download_dir)
        (download_dir / '.DS_Store').write_bytes(b'\x00\x00\x00\x01Bud1')

    result, _ = run_live(download=deliver_with_finder_metadata)

    assert result.exit_code == 0, result.output
    assert (data_directory / 'raw/acs/core/usa_00123/.DS_Store').exists()
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [entry.path for entry in entries] == [
        'acs/core/usa_00123/extract.json',
        'acs/core/usa_00123/usa_00123.csv.gz',
        'acs/core/usa_00123/usa_00123.xml',
    ]


def test_an_interrupted_delivery_of_the_same_extract_is_left_alone(run_live, data_directory):
    staging = data_directory / 'raw/acs/core/usa_00123.part'
    staging.mkdir(parents=True)
    (staging / 'extract.json').write_text('{}\n')
    before = tree(data_directory)

    result, client_factory = run_live()

    assert isinstance(result.exception, FileExistsError), result.output
    assert 'usa_00123.part' in str(result.exception)
    client_factory.return_value.wait_for_extract.assert_not_called()
    client_factory.return_value.download_extract.assert_not_called()
    assert tree(data_directory) == before
    assert_not_delivered(data_directory)


def test_the_api_key_reaches_no_file_and_no_output(run_live, data_directory):
    result, _ = run_live()

    assert result.exit_code == 0, result.output
    assert 'dotenv-test-key' not in result.output
    for path, contents in tree(data_directory).items():
        assert b'dotenv-test-key' not in contents, path


def test_convert_only_validates_set_names_before_credentials(cli_runner, tmp_path):
    with (
        patch.object(benchmark, 'DOTENV_PATH', tmp_path / 'absent.env'),
        patch.object(benchmark, 'load_dotenv', side_effect=AssertionError('dotenv loaded')),
        patch.object(benchmark, 'IpumsApiClient', side_effect=AssertionError('client created')),
    ):
        result = cli_runner.invoke(benchmark.app, [
            'unknown', '--convert-only', '--data-dir', str(tmp_path),
        ])
    assert result.exit_code == 2, result.output
    assert 'unknown extract(s): unknown' in result.output
    assert list(tmp_path.iterdir()) == []
