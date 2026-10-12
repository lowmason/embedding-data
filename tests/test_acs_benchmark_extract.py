import gzip
import json
import os
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest
import typer
from typer.main import get_command

from embedding_data import acs_benchmark_extract as benchmark

PROJECT_ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.usefixtures('cli_runner')


def cli_app():
    app = getattr(benchmark, 'app', None)
    assert isinstance(app, typer.Typer)
    return app


def test_default_paths_point_to_project_root():
    command = get_command(cli_app())
    with command.make_context('benchmark', ['--dry-run']) as context:
        assert context.params['out'] == PROJECT_ROOT / 'data/raw/acs'
    assert benchmark.DOTENV_PATH == PROJECT_ROOT / '.env'


def test_help_describes_the_benchmark(cli_runner):
    result = cli_runner.invoke(cli_app(), ['--help'])

    assert result.exit_code == 0, result.output
    assert 'IPUMS USA extracts' in result.output


def test_dry_run_defaults_to_core_without_credentials(cli_runner, output_directory):
    result = cli_runner.invoke(
        cli_app(), ['--dry-run', '--out', str(output_directory)],
    )

    assert result.exit_code == 0, result.output
    definition = json.loads((output_directory / 'core/extract.json').read_text())
    assert set(definition['samples']) == {'us2023a', 'us2024a'}
    assert definition['dataFormat'] == 'csv'
    assert definition['dataQualityFlags']


def test_dry_run_accepts_multiple_extracts(cli_runner, output_directory):
    result = cli_runner.invoke(
        cli_app(),
        ['core', 'vintage', 'five_year', '--dry-run', '--out', str(output_directory)],
    )

    assert result.exit_code == 0, result.output
    for name, samples in benchmark.SAMPLE_SETS.items():
        definition = json.loads((output_directory / name / 'extract.json').read_text())
        assert set(definition['samples']) == set(samples), name


def test_unknown_extract_exits_before_writing_files(cli_runner, output_directory):
    result = cli_runner.invoke(
        cli_app(), ['unknown', '--dry-run', '--out', str(output_directory)],
    )

    assert result.exit_code == 2, result.output
    assert 'unknown extract(s): unknown' in result.output
    assert not output_directory.exists()


@pytest.mark.parametrize('contents', [None, 'IPUMS_API_KEY=\n'], ids=['missing', 'empty'])
def test_missing_or_empty_key_exits_with_dotenv_instructions(
    cli_runner, output_directory, dotenv_path, contents,
):
    app = cli_app()
    if contents is not None:
        dotenv_path.write_text(contents)
    with patch.object(benchmark, 'DOTENV_PATH', dotenv_path):
        result = cli_runner.invoke(app, ['--out', str(output_directory)])

    assert result.exit_code == 1, result.output
    assert 'IPUMS_API_KEY' in result.output
    assert str(dotenv_path) in result.output
    assert not output_directory.exists()


@pytest.mark.parametrize(
    'environment_key', [None, 'environment-test-key'], ids=['dotenv', 'environment'],
)
def test_dotenv_key_is_loaded_with_environment_taking_precedence(
    cli_runner, output_directory, dotenv_path, environment_key,
):
    app = cli_app()
    dotenv_path.write_text('IPUMS_API_KEY=dotenv-test-key\n')

    os.environ.pop('IPUMS_API_KEY', None)
    if environment_key is not None:
        os.environ['IPUMS_API_KEY'] = environment_key
    expected_key = environment_key or 'dotenv-test-key'
    with (
        patch.object(benchmark, 'DOTENV_PATH', dotenv_path),
        patch.object(benchmark, 'IpumsApiClient', autospec=True) as client_factory,
    ):
        client = client_factory.return_value
        client.submit_extract.side_effect = lambda extract: setattr(extract, '_id', 123)

        def download_fixture(extract, *, download_dir):
            assert extract.extract_id == 123
            with gzip.open(download_dir / 'usa_00123.csv.gz', 'wt') as csv_file:
                csv_file.write('INDNAICS,OCCSOC,INCWAGE_CPIU_2010\n31M,1110XX,12.5\n')

        client.download_extract.side_effect = download_fixture
        result = cli_runner.invoke(app, ['--out', str(output_directory)])

    assert result.exit_code == 0, result.output
    client_factory.assert_called_once_with(expected_key)
    extract_directory = output_directory / 'core'
    data = pl.read_parquet(extract_directory / 'usa_00123.parquet')
    assert data.row(0) == ('31M', '1110XX', 12.5)
    assert not (extract_directory / 'usa_00123.csv').exists()
    assert (extract_directory / 'usa_00123.csv.gz').exists()
