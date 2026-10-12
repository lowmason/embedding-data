import json
import os
from pathlib import Path
import tomllib
from unittest.mock import patch

from typer.main import get_command

from embedding_data import acs_benchmark_extract as acs_extract
from embedding_data import cli
from embedding_data import cps_benchmark_extract as cps_extract


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CATALOG = {
    'cps2025_01b': 'January 2025 Basic Monthly',
    'cps2026_08b': 'August 2026 Basic Monthly',
    'cps2026_09s': 'September 2026 Supplement',
}


def test_console_script_points_to_cli_app():
    pyproject = tomllib.loads((PROJECT_ROOT / 'pyproject.toml').read_text())

    assert pyproject['project']['scripts']['embedding-data'] == 'embedding_data.cli:app'


def test_extract_commands_are_registered():
    command = get_command(cli.app)

    assert {'acs', 'cps'} <= set(getattr(command, 'commands', {}))


def test_tracebacks_hide_local_variables():
    assert cli.app.pretty_exceptions_show_locals is False


def test_cps_help_describes_cps_options(cli_runner):
    result = cli_runner.invoke(cli.app, ['cps', '--help'])

    assert result.exit_code == 0, result.output
    assert 'IPUMS CPS extracts' in result.output
    assert '--start' in result.output


def test_acs_help_describes_acs_benchmark(cli_runner):
    result = cli_runner.invoke(cli.app, ['acs', '--help'])

    assert result.exit_code == 0, result.output
    assert 'IPUMS USA extracts' in result.output


def test_cps_dry_run_reaches_cps_module(cli_runner, output_directory, dotenv_path):
    dotenv_path.write_text('IPUMS_API_KEY=dotenv-test-key\n')
    arguments = ['cps', 'monthly', '--start', '2026-08', '--dry-run', '--out', str(output_directory)]
    with (
        patch.object(cps_extract, 'DOTENV_PATH', dotenv_path),
        patch.object(cps_extract, 'IpumsApiClient', autospec=True) as client_factory,
    ):
        client_factory.return_value.get_all_sample_info.return_value = SAMPLE_CATALOG
        result = cli_runner.invoke(cli.app, arguments)

    assert result.exit_code == 0, result.output
    client_factory.assert_called_once_with('dotenv-test-key')
    client_factory.return_value.submit_extract.assert_not_called()
    definition = json.loads((output_directory / 'monthly/extract.json').read_text())
    assert list(definition['samples']) == ['cps2026_08b', 'cps2026_09s']


def test_acs_dry_run_neither_reads_key_nor_creates_client(cli_runner, output_directory, dotenv_path):
    dotenv_path.write_text('IPUMS_API_KEY=dotenv-test-key\n')
    with (
        patch.object(acs_extract, 'DOTENV_PATH', dotenv_path),
        patch.object(acs_extract, 'IpumsApiClient', autospec=True) as client_factory,
    ):
        result = cli_runner.invoke(cli.app, ['acs', '--dry-run', '--out', str(output_directory)])

        assert 'IPUMS_API_KEY' not in os.environ

    assert result.exit_code == 0, result.output
    client_factory.assert_not_called()
    definition = json.loads((output_directory / 'core/extract.json').read_text())
    assert set(definition['samples']) == {'us2023a', 'us2024a'}
