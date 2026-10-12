import gzip
import hashlib
import json
from itertools import count
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest
import typer
from typer.main import get_command

from embedding_data import cps_benchmark_extract as benchmark
from embedding_data import manifest, paths

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CATALOG = {
    'cps2024_12b': 'December 2024 Basic Monthly',
    'cps2025_01s': 'January 2025 Supplement',
    'cps2025_01b': 'January 2025 Basic Monthly',
    'cps2025_03s': 'March 2025 ASEC',
    'cps2024_03s': 'March 2024 ASEC',
    'cps2026_03s': 'March 2026 ASEC',
    'cps2026_08b': 'August 2026 Basic Monthly',
    'cps2026_09s': 'September 2026 Supplement',
}


@pytest.fixture
def cli_app():
    app = getattr(benchmark, 'app', None)
    assert isinstance(app, typer.Typer)
    return app


@pytest.fixture
def run_cli(cli_app, cli_runner, data_directory, dotenv_path):
    dotenv_path.write_text('IPUMS_API_KEY=dotenv-test-key\n')

    def invoke_cli(arguments, *, catalog=None, download=None):
        extract_ids = count(123)
        with (
            patch.object(benchmark, 'DOTENV_PATH', dotenv_path),
            patch.object(benchmark, 'IpumsApiClient', autospec=True) as client_factory,
        ):
            client = client_factory.return_value
            client.get_all_sample_info.return_value = (
                SAMPLE_CATALOG if catalog is None else catalog
            )
            client.submit_extract.side_effect = (
                lambda extract: setattr(extract, '_id', next(extract_ids))
            )
            client.download_extract.side_effect = download
            result = cli_runner.invoke(
                cli_app, [*arguments, '--data-dir', str(data_directory)]
            )
        return result, client_factory

    return invoke_cli


def preview(data_directory, name):
    return json.loads((data_directory / 'preview/cps' / name / 'extract.json').read_text())


def write_delivery(extract, *, download_dir):
    '''Fake IPUMS delivery: the data file and codebook, named for the extract number.'''
    name = f'cps_{extract.extract_id:05d}'
    if download_dir.parent.name == 'monthly':
        csv = 'IND,OCC\n170,20\n'
    else:
        csv = 'IND,OCC,INDLY,OCCLY,INCWAGE_CPIU_2010\n170,20,770,30,12.5\n'
    with gzip.open(download_dir / f'{name}.csv.gz', 'wt') as csv_file:
        csv_file.write(csv)
    (download_dir / f'{name}.xml').write_text('<codeBook/>\n')


def test_default_paths_point_to_project_root(cli_app):
    command = get_command(cli_app)
    with command.make_context('benchmark', ['--dry-run']) as context:
        assert context.params['data_dir'] == PROJECT_ROOT / 'data'
        assert context.params['start'] == '2025-01'
    assert benchmark.DOTENV_PATH == PROJECT_ROOT / '.env'


def test_help_describes_cps_options(cli_app, cli_runner):
    result = cli_runner.invoke(cli_app, ['--help'])

    assert result.exit_code == 0, result.output
    assert 'IPUMS CPS extracts' in result.output
    assert '--start' in result.output


def test_dry_run_loads_key_and_writes_monthly_and_asec_definitions(run_cli, data_directory):
    result, client_factory = run_cli(['--dry-run'])

    assert result.exit_code == 0, result.output
    client_factory.assert_called_once_with('dotenv-test-key')
    client_factory.return_value.get_all_sample_info.assert_called_once_with('cps')
    client_factory.return_value.submit_extract.assert_not_called()
    expected_samples = {
        'monthly': ['cps2025_01b', 'cps2026_08b', 'cps2026_09s'],
        'asec': ['cps2025_03s', 'cps2026_03s'],
    }
    for name, samples in expected_samples.items():
        definition = preview(data_directory, name)
        assert list(definition['samples']) == samples
        assert definition['collection'] == 'cps'
        assert definition['dataQualityFlags']
    assert not (data_directory / 'raw').exists()


def test_monthly_start_option_filters_catalog(run_cli, data_directory):
    result, _ = run_cli(['monthly', '--start', '2026-08', '--dry-run'])

    assert result.exit_code == 0, result.output
    assert list(preview(data_directory, 'monthly')['samples']) == ['cps2026_08b', 'cps2026_09s']
    assert not (data_directory / 'preview/cps/asec').exists()


def test_exported_key_takes_precedence(run_cli, data_directory, monkeypatch):
    monkeypatch.setenv('IPUMS_API_KEY', 'environment-test-key')
    result, client_factory = run_cli(['asec', '--dry-run'])

    assert result.exit_code == 0, result.output
    client_factory.assert_called_once_with('environment-test-key')
    assert (data_directory / 'preview/cps/asec/extract.json').exists()


@pytest.mark.parametrize('contents', [None, 'IPUMS_API_KEY=\n'], ids=['missing', 'empty'])
def test_missing_or_empty_key_fails_even_for_dry_run(
    run_cli, data_directory, dotenv_path, contents,
):
    if contents is None:
        dotenv_path.unlink()
    else:
        dotenv_path.write_text(contents)
    result, client_factory = run_cli(['--dry-run'])

    assert result.exit_code == 1, result.output
    assert 'IPUMS_API_KEY' in result.output
    assert str(dotenv_path) in result.output
    client_factory.assert_not_called()
    assert not data_directory.exists()


def test_unknown_extract_fails_before_loading_catalog(run_cli, data_directory):
    result, client_factory = run_cli(['unknown', '--dry-run'])

    assert result.exit_code == 2, result.output
    assert 'unknown extract(s): unknown' in result.output
    client_factory.assert_not_called()
    assert not data_directory.exists()


def test_empty_catalog_reports_missing_samples(run_cli, data_directory):
    result, _ = run_cli(['monthly', '--dry-run'], catalog={})

    assert result.exit_code == 1, result.output
    assert 'monthly: no matching samples' in result.output
    assert not data_directory.exists()


def test_deliveries_convert_outside_raw_with_zero_padded_census_codes(run_cli, data_directory):
    result, _ = run_cli(['monthly', 'asec'], download=write_delivery)

    assert result.exit_code == 0, result.output
    for name, extract_name, expected in (
        ('monthly', 'cps_00123', ('0170', '0020')),
        ('asec', 'cps_00124', ('0170', '0020', '0770', '0030', 12.5)),
    ):
        derived = data_directory / 'derived/cps' / name
        assert sorted(path.name for path in derived.iterdir()) == [f'{extract_name}.parquet']
        assert pl.read_parquet(derived / f'{extract_name}.parquet').row(0) == expected
        extract_directory = data_directory / 'raw/cps' / name / extract_name
        assert sorted(path.name for path in extract_directory.iterdir()) == [
            f'{extract_name}.csv.gz', f'{extract_name}.xml', 'extract.json',
        ]
    assert list((data_directory / 'raw').rglob('*.parquet')) == []


def test_every_delivered_file_is_recorded_with_its_samples(run_cli, data_directory):
    result, _ = run_cli(['monthly', 'asec'], download=write_delivery)

    assert result.exit_code == 0, result.output
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [(entry.path, entry.extract_number) for entry in entries] == [
        ('cps/monthly/cps_00123/cps_00123.csv.gz', 123),
        ('cps/monthly/cps_00123/cps_00123.xml', 123),
        ('cps/monthly/cps_00123/extract.json', 123),
        ('cps/asec/cps_00124/cps_00124.csv.gz', 124),
        ('cps/asec/cps_00124/cps_00124.xml', 124),
        ('cps/asec/cps_00124/extract.json', 124),
    ]
    for entry in entries:
        delivered = data_directory / 'raw' / entry.path
        assert entry.sha256 == hashlib.sha256(delivered.read_bytes()).hexdigest()
        assert entry.collection == 'cps'
    assert [entry.samples for entry in entries[::3]] == [
        ('cps2025_01b', 'cps2026_08b', 'cps2026_09s'),
        ('cps2025_03s', 'cps2026_03s'),
    ]


def test_the_api_key_reaches_no_file_and_no_output(run_cli, data_directory):
    result, _ = run_cli(['monthly', 'asec'], download=write_delivery)

    assert result.exit_code == 0, result.output
    assert 'dotenv-test-key' not in result.output
    for path in data_directory.rglob('*'):
        if path.is_file():
            assert b'dotenv-test-key' not in path.read_bytes(), path


@pytest.mark.parametrize('start', ['2024-12', '2020-01'])
@pytest.mark.parametrize('mode', [[], ['--dry-run']], ids=['live', 'dry-run'])
def test_a_start_before_january_2025_is_refused_before_the_key_is_read(
    run_cli, data_directory, start, mode,
):
    result, client_factory = run_cli(['monthly', '--start', start, *mode])

    assert result.exit_code == 2, result.output
    assert f'{start} is before 2025-01' in result.output
    client_factory.assert_not_called()
    assert not data_directory.exists()
