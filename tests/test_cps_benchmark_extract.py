import gzip
import json
from pathlib import Path
import tomllib
from unittest.mock import patch

import polars as pl
import pytest
import typer
from typer.main import get_command

from embedding_data import cps_benchmark_extract as benchmark


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
def run_cli(cli_app, cli_runner, output_directory, dotenv_path):
    dotenv_path.write_text('IPUMS_API_KEY=dotenv-test-key\n')

    def invoke_cli(arguments, *, catalog=None, download=None):
        with (
            patch.object(benchmark, 'DOTENV_PATH', dotenv_path),
            patch.object(benchmark, 'IpumsApiClient', autospec=True) as client_factory,
        ):
            client = client_factory.return_value
            client.get_all_sample_info.return_value = SAMPLE_CATALOG if catalog is None else catalog
            client.submit_extract.side_effect = lambda extract: setattr(extract, '_id', 123)
            client.download_extract.side_effect = download
            result = cli_runner.invoke(cli_app, [*arguments, '--out', str(output_directory)])
        return result, client_factory

    return invoke_cli


def test_default_paths_point_to_project_root(cli_app):
    command = get_command(cli_app)
    with command.make_context('benchmark', ['--dry-run']) as context:
        assert context.params['out'] == PROJECT_ROOT / 'data/raw/cps'
        assert context.params['start'] == '2025-01'
    assert benchmark.DOTENV_PATH == PROJECT_ROOT / '.env'


def test_inline_dependencies_include_cli_and_dotenv():
    source = Path(benchmark.__file__).read_text()
    metadata_block = source.split('# /// script\n', 1)[1].split('# ///', 1)[0]
    metadata = tomllib.loads('\n'.join(line.removeprefix('# ') for line in metadata_block.splitlines()))
    dependencies = {dependency.split('>=', 1)[0] for dependency in metadata['dependencies']}

    assert 'typer' in dependencies
    assert 'python-dotenv' in dependencies


def test_help_describes_cps_options(cli_app, cli_runner):
    result = cli_runner.invoke(cli_app, ['--help'])

    assert result.exit_code == 0, result.output
    assert 'IPUMS CPS extracts' in result.output
    assert '--start' in result.output


def test_dry_run_loads_key_and_writes_monthly_and_asec_definitions(run_cli, output_directory):
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
        definition = json.loads((output_directory / name / 'extract.json').read_text())
        assert list(definition['samples']) == samples
        assert definition['collection'] == 'cps'
        assert definition['dataQualityFlags']


def test_monthly_start_option_filters_catalog(run_cli, output_directory):
    result, _ = run_cli(['monthly', '--start', '2026-08', '--dry-run'])

    assert result.exit_code == 0, result.output
    definition = json.loads((output_directory / 'monthly/extract.json').read_text())
    assert list(definition['samples']) == ['cps2026_08b', 'cps2026_09s']
    assert not (output_directory / 'asec').exists()


def test_exported_key_takes_precedence(run_cli, output_directory, monkeypatch):
    monkeypatch.setenv('IPUMS_API_KEY', 'environment-test-key')
    result, client_factory = run_cli(['asec', '--dry-run'])

    assert result.exit_code == 0, result.output
    client_factory.assert_called_once_with('environment-test-key')
    assert (output_directory / 'asec/extract.json').exists()


@pytest.mark.parametrize('contents', [None, 'IPUMS_API_KEY=\n'], ids=['missing', 'empty'])
def test_missing_or_empty_key_fails_even_for_dry_run(run_cli, output_directory, dotenv_path, contents):
    if contents is None:
        dotenv_path.unlink()
    else:
        dotenv_path.write_text(contents)
    result, client_factory = run_cli(['--dry-run'])

    assert result.exit_code == 1, result.output
    assert 'IPUMS_API_KEY' in result.output
    assert str(dotenv_path) in result.output
    client_factory.assert_not_called()
    assert not output_directory.exists()


def test_unknown_extract_fails_before_loading_catalog(run_cli, output_directory):
    result, client_factory = run_cli(['unknown', '--dry-run'])

    assert result.exit_code == 2, result.output
    assert 'unknown extract(s): unknown' in result.output
    client_factory.assert_not_called()
    assert not output_directory.exists()


def test_empty_catalog_reports_missing_samples(run_cli, output_directory):
    result, _ = run_cli(['monthly', '--dry-run'], catalog={})

    assert result.exit_code == 1, result.output
    assert 'monthly: no matching samples' in result.output
    assert not output_directory.exists()


def test_downloads_are_converted_with_zero_padded_census_codes(run_cli, output_directory):
    def download_fixture(extract, *, download_dir):
        if download_dir.name == 'monthly':
            csv = 'IND,OCC\n170,20\n'
        else:
            csv = 'IND,OCC,INDLY,OCCLY,INCWAGE_CPIU_2010\n170,20,770,30,12.5\n'
        with gzip.open(download_dir / 'cps_00123.csv.gz', 'wt') as csv_file:
            csv_file.write(csv)

    result, _ = run_cli(['monthly', 'asec'], download=download_fixture)

    assert result.exit_code == 0, result.output
    for name, expected in (
        ('monthly', ('0170', '0020')),
        ('asec', ('0170', '0020', '0770', '0030', 12.5)),
    ):
        extract_directory = output_directory / name
        data = pl.read_parquet(extract_directory / 'cps_00123.parquet')
        assert data.row(0) == expected
        assert not (extract_directory / 'cps_00123.csv').exists()
        assert (extract_directory / 'cps_00123.csv.gz').exists()
