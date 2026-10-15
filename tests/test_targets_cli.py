import pytest
from target_fixtures import acquired_tree, forbid_external_access

from embedding_data.cli import app

@pytest.mark.parametrize('command', ['prepare-ita', 'acquire-ita', 'build-ita'])
def test_targets_command_help(cli_runner, command, tmp_path, monkeypatch):
    forbid_external_access(monkeypatch)
    result = cli_runner.invoke(app, ['targets', command, '--help'])
    assert result.exit_code == 0
    assert '--data-dir' in result.stdout


def test_build_cli_success_and_safe_error(cli_runner, tmp_path, monkeypatch):
    prepared = acquired_tree(tmp_path, monkeypatch)
    forbid_external_access(monkeypatch)
    args = ['targets', 'build-ita', prepared.directory.name, 'cli', '--data-dir', str(tmp_path)]
    result = cli_runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    result = cli_runner.invoke(app, args)
    assert result.exit_code == 1
    assert 'ITA target build failed:' in result.output
    assert 'Exact A' not in result.output and 'Fixture Town' not in result.output


def test_prepare_and_acquire_cli_explicit_root(cli_runner, tmp_path, monkeypatch):
    from target_fixtures import census_client, seed_inputs

    from embedding_data import ita_assignment_acquire as acquisition

    forbid_external_access(monkeypatch)
    selected = seed_inputs(tmp_path)
    args = ['targets', 'prepare-ita', 'cli_inputs', '--codes-run', 'fixture_codes',
            '--geography-run', 'fixture_geography', '--data-dir', str(tmp_path),
            '--codes-outputs-sha256', selected.provenance['codes']['outputs_sha256'],
            '--geography-outputs-sha256', selected.provenance['geography']['outputs_sha256']]
    result = cli_runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    calls = []
    with monkeypatch.context() as mock_acquisition:
        mock_acquisition.setattr(acquisition, 'make_client', lambda: census_client(calls))
        result = cli_runner.invoke(app, ['targets', 'acquire-ita', 'cli_inputs',
                                         '--data-dir', str(tmp_path)])
        assert result.exit_code == 0, result.output
    assert any(call['method'] == 'POST' for call in calls)
    for command_args in [args, ['targets', 'acquire-ita', 'missing', '--data-dir', str(tmp_path)],
                         ['targets', 'build-ita', 'cli_inputs', 'bad', '--year', '2022',
                          '--data-dir', str(tmp_path)]]:
        result = cli_runner.invoke(app, command_args)
        assert result.exit_code == 1
        assert 'failed:' in result.output
        assert 'Exact A' not in result.output and 'Fixture Town' not in result.output
