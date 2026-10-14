import httpx
import pytest
from geography_fixtures import seed_geography_tree
from typer.testing import CliRunner

from embedding_data import cli
from embedding_data import geography_references as gr

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('network or credential access prohibited')

    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', forbidden)
    monkeypatch.setattr(cli.acs_benchmark_extract, 'load_dotenv', forbidden)
    monkeypatch.setattr(cli.cps_benchmark_extract, 'load_dotenv', forbidden)
    monkeypatch.delenv('IPUMS_API_KEY', raising=False)


@pytest.mark.parametrize('command', [['acquire'], ['import-reference'], ['build']])
def test_geography_help(tmp_path, command):
    result = CliRunner().invoke(
        cli.app, ['geography', *command, '--data-dir', str(tmp_path), '--help'])
    assert result.exit_code == 0
    assert 'Usage' in result.output


def test_cached_cli_and_offline_build(tmp_path, monkeypatch):
    registry = seed_geography_tree(tmp_path)
    monkeypatch.setattr(gr, 'REGISTRY', registry)
    runner = CliRunner()
    acquired = runner.invoke(cli.app, ['geography', 'acquire', '--data-dir', str(tmp_path)])
    assert acquired.exit_code == 0
    result = runner.invoke(cli.app, ['geography', 'build', 'cli_fixture',
                                   '--data-dir', str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / 'derived/geography/cli_fixture/outputs.json').exists()
    repeat = runner.invoke(cli.app, ['geography', 'build', 'cli_fixture',
                                   '--data-dir', str(tmp_path)])
    assert repeat.exit_code == 2
    assert 'already exists' in repeat.output


def test_missing_reference_is_actionable_without_traceback(tmp_path):
    result = CliRunner().invoke(
        cli.app, ['geography', 'build', 'missing', '--data-dir', str(tmp_path)])
    assert result.exit_code == 2
    assert 'missing manifested geography originals' in result.output
    assert 'Traceback' not in result.output


@pytest.mark.parametrize('kind', ['counties_2025', 'states_2025'])
def test_malformed_original_is_concise_exit_two(tmp_path, monkeypatch, kind):
    from dataclasses import replace

    from embedding_data import manifest

    original = tmp_path / ('broken.zip' if kind == 'counties_2025' else 'broken.xlsx')
    original.write_bytes(b'not an archive')
    registry = dict(gr.REGISTRY)
    registry[kind] = replace(registry[kind], sha256=manifest.sha256_file(original),
                             size=original.stat().st_size, fixture=True)
    monkeypatch.setattr(gr, 'REGISTRY', registry)
    result = CliRunner().invoke(cli.app, ['geography', 'import-reference', kind, str(original),
                                        '--data-dir', str(tmp_path)])
    assert result.exit_code == 2
    assert 'No such command' not in result.output
    assert 'Traceback' not in result.output
    assert result.output.strip()
    assert not gr.reference_path(tmp_path, registry[kind]).exists()
