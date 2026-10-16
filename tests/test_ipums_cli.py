'''Offline CLI paths run real synthetic evidence with forbidden network/auth boundaries.'''

import json

import pytest
import test_ipums_verification_run as run_tests
from typer.testing import CliRunner

from embedding_data import cli, ipums_cli, ipums_references, ipums_verification_run, manifest

complete_inputs = run_tests.complete_inputs


def test_cli_measure_verify_compare_and_cached_acquire_are_offline(complete_inputs):
    root, selection = complete_inputs
    runner = CliRunner()
    for name in ('first', 'second'):
        result = runner.invoke(cli.app, ['ipums', 'measure', name, '--references', 'references',
                                        '--selection', str(selection), '--data-dir', str(root)])
        assert result.exit_code == 0, result.output
        directory = ipums_verification_run.run_directory(root, name)
        pin = manifest.sha256_file(directory / 'outputs.json')
        assert pin in result.output
        result = runner.invoke(cli.app, ['ipums', 'verify', name, '--outputs-sha256', pin,
                                        '--data-dir', str(root)])
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)['status'] == 'verified'
    result = runner.invoke(cli.app, ['ipums', 'compare-runs', 'first', 'second',
                                    '--data-dir', str(root)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)['equal'] is True
    result = runner.invoke(cli.app, ['ipums', 'acquire-references', 'references',
                                    '--census-env-file', str(root / 'must-not-read.env'),
                                    '--data-dir', str(root)])
    assert result.exit_code == 0, result.output


def test_cli_import_does_not_construct_clients_or_load_dotenv(complete_inputs, tmp_path):
    root, _ = complete_inputs
    file = root / 'raw/references/ipums-verification/references/usa_samples.html'
    result = CliRunner().invoke(cli.app, ['ipums', 'import-reference', 'imported', 'usa_samples',
                                        str(file), '--data-dir', str(tmp_path / 'import-root')])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize('error', [ValueError('SENSITIVE_PERSON_VALUE'),
                                   KeyError('SENSITIVE_PERSON_VALUE'),
                                   OSError('SENSITIVE_PERSON_VALUE'),
                                   EOFError('SENSITIVE_PERSON_VALUE')])
def test_cli_errors_never_echo_parser_microdata(tmp_path, monkeypatch, error):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(ipums_verification_run, 'measure', fail)
    result = CliRunner().invoke(ipums_cli.app, ['measure', 'run', '--references', 'refs',
                                              '--selection', str(tmp_path / 'selection.json'),
                                              '--data-dir', str(tmp_path)])
    assert result.exit_code == 2
    assert 'SENSITIVE_PERSON_VALUE' not in result.output
    assert 'Traceback' not in result.output


def test_cli_acquisition_passes_only_explicit_env_path(tmp_path, monkeypatch):
    received = []
    def acquire(root, reference_id, *, census_env_file=None):
        received.append((root, reference_id, census_env_file))
        return root / reference_id
    monkeypatch.setattr(ipums_references, 'acquire', acquire)
    file = tmp_path / 'explicit.env'
    result = CliRunner().invoke(ipums_cli.app, ['acquire-references', 'refs', '--data-dir',
                                              str(tmp_path), '--census-env-file', str(file)])
    assert result.exit_code == 0, result.output
    assert received == [(tmp_path, 'refs', file)]


def test_cli_fidelity_failure_names_only_delivery_and_preserves_staging(complete_inputs):
    import polars as pl
    root, selection = complete_inputs
    file = next(root.glob('derived/acs/core/*.parquet'))
    pl.read_parquet(file).head(1).write_parquet(file)
    result = CliRunner().invoke(cli.app, ['ipums', 'measure', 'bad', '--references', 'references',
                                        '--selection', str(selection), '--data-dir', str(root)])
    assert result.exit_code == 2
    assert 'usa_1' in result.output
    assert 'Traceback' not in result.output
