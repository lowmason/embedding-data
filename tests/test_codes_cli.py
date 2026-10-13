import httpx
import polars as pl
import pytest
from code_fixtures import seed_code_tree
from polars.testing import assert_frame_equal
from typer.testing import CliRunner

from embedding_data import cli, code_references

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('network or credential access prohibited')

    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', forbidden)
    monkeypatch.setattr(cli.acs_benchmark_extract, 'load_dotenv', forbidden)
    monkeypatch.setattr(cli.cps_benchmark_extract, 'load_dotenv', forbidden)
    monkeypatch.delenv('IPUMS_API_KEY', raising=False)
    monkeypatch.delenv('BLS_CONTACT_EMAIL', raising=False)


@pytest.mark.parametrize('command', [[], ['acquire'], ['import-reference'], ['build']])
def test_command_help(tmp_path, command):
    arguments = ['codes', *command]
    if command:
        arguments += ['--data-dir', str(tmp_path)]
    result = CliRunner().invoke(cli.app, [*arguments, '--help'])
    assert result.exit_code == 0, result.output


def test_cli_offline_builds_actual_originals_twice(tmp_path, monkeypatch):
    registry = seed_code_tree(tmp_path)
    monkeypatch.setattr(code_references, 'REGISTRY', registry)
    for run in ['first', 'second']:
        result = CliRunner().invoke(cli.app, ['codes', 'build', run, '--data-dir', str(tmp_path)])
        assert result.exit_code == 0, result.output
    root = tmp_path / 'derived/codes'
    for file in (root / 'first').glob('*.parquet'):
        assert_frame_equal(pl.read_parquet(file), pl.read_parquet(root / 'second' / file.name))
    result = CliRunner().invoke(cli.app, ['codes', 'build', 'first', '--data-dir', str(tmp_path)])
    assert result.exit_code == 2
    assert 'exists' in result.output
    assert 'Traceback' not in result.output


@pytest.mark.parametrize(
    'command, expected',
    [
        (['build', 'missing'], 'is not recorded'),
        (['build', '../escape'], 'run ID'),
        (['acquire'], 'BLS_CONTACT_EMAIL'),
        (['import-reference', 'unknown', 'absent.xlsx'], 'unknown registered'),
    ],
)
def test_clean_cli_errors(tmp_path, command, expected):
    result = CliRunner().invoke(cli.app, ['codes', *command, '--data-dir', str(tmp_path)])
    assert result.exit_code == 2, result.output
    assert expected in result.output
    assert 'Traceback' not in result.output


def test_cached_acquire_and_identical_import_are_offline(tmp_path, monkeypatch):
    registry = seed_code_tree(tmp_path)
    monkeypatch.setattr(code_references, 'REGISTRY', registry)
    runner = CliRunner()
    result = runner.invoke(cli.app, ['codes', 'acquire', '--data-dir', str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert len(result.output.splitlines()) == len(registry)
    result = runner.invoke(cli.app, [
        'codes', 'import-reference', 'soc_2018', str(tmp_path / 'originals/soc.xlsx'),
        '--data-dir', str(tmp_path),
    ])
    assert result.exit_code == 0, result.output
    assert str(code_references.reference_path(tmp_path, registry['soc_2018'])) in result.output


def test_invalid_workbook_import_exits_cleanly_without_publication(tmp_path):
    original = tmp_path / 'saved.xlsx'
    original.write_text('<html>Access denied</html>')
    result = CliRunner().invoke(cli.app, [
        'codes', 'import-reference', 'naics_2022', str(original),
        '--data-dir', str(tmp_path),
    ])
    assert result.exit_code == 2, repr(result.exception)
    assert 'calamine' in result.output.lower()
    assert 'Traceback' not in result.output
    assert not code_references.reference_path(
        tmp_path, code_references.REGISTRY['naics_2022']
    ).exists()
    assert not (tmp_path / 'raw/manifest.jsonl').exists()
    assert not (tmp_path / 'derived/codes').exists()
