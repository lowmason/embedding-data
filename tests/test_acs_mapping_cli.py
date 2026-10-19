'''Separate five-command offline module surface.'''

import pytest
from typer.testing import CliRunner

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    from acs_mapping_fixtures import forbid_external_access

    forbid_external_access(monkeypatch)


def test_help_has_exact_commands(tmp_path, monkeypatch):
    from acs_mapping_fixtures import forbid_external_access

    from embedding_data.acs_mapping import app

    forbid_external_access(monkeypatch)
    result = CliRunner().invoke(app, ['--help'])
    assert result.exit_code == 0
    for name in ('acquire-references', 'import-reference', 'build', 'verify', 'compare-runs'):
        assert name in result.stdout


def test_validation_errors_are_safe(tmp_path):
    from embedding_data.acs_mapping import app

    result = CliRunner().invoke(app, ['verify', 'absent', '--outputs-sha256', '0' * 64,
                                    '--data-dir', str(tmp_path)])
    assert result.exit_code == 2
    assert 'Traceback' not in result.output


def test_exact_five_command_registration():
    from embedding_data.acs_mapping import app

    assert {command.name for command in app.registered_commands} == {
        'acquire-references', 'import-reference', 'build', 'verify', 'compare-runs'}


def test_parser_exception_never_exposes_person_values(tmp_path, monkeypatch):
    from embedding_data import acs_mapping_bundle
    from embedding_data.acs_mapping import app

    def fail(*args, **kwargs):
        raise ValueError('PRIVATE_PERSON_VALUE')

    monkeypatch.setattr(acs_mapping_bundle, 'verify_bundle', fail)
    result = CliRunner().invoke(app, ['verify', 'test', '--outputs-sha256', '0' * 64,
                                    '--data-dir', str(tmp_path)])
    assert result.exit_code == 2
    assert 'PRIVATE_PERSON_VALUE' not in result.output
    assert 'Traceback' not in result.output


def test_comparison_mismatch_exits_one(tmp_path, monkeypatch):
    from embedding_data import acs_mapping_bundle
    from embedding_data.acs_mapping import app

    monkeypatch.setattr(acs_mapping_bundle, 'compare_runs', lambda *args: {'equal': False})
    result = CliRunner().invoke(app, ['compare-runs', 'one', 'two',
                                    '--data-dir', str(tmp_path)])
    assert result.exit_code == 1


def test_cached_reference_acquisition_has_no_http(tmp_path, monkeypatch):
    import json

    from acs_mapping_fixtures import seed_mapping_references

    from embedding_data.acs_mapping import app

    reference = seed_mapping_references(tmp_path, monkeypatch)
    for _ in range(2):
        result = CliRunner().invoke(app, ['acquire-references', reference.reference_id,
                                        '--data-dir', str(reference.data_dir)])
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout)['receipt_sha256'] == reference.receipt_sha256


def test_import_returns_only_public_metadata(tmp_path, monkeypatch):
    from acs_mapping_fixtures import seed_mapping_references

    from embedding_data.acs_mapping import app

    reference = seed_mapping_references(tmp_path, monkeypatch)
    kind, original = next(iter(reference.originals.items()))
    result = CliRunner().invoke(app, ['import-reference', 'new_reference', kind, str(original),
                                    '--data-dir', str(reference.data_dir)])
    assert result.exit_code == 0, result.output


def test_build_forwards_all_external_selection_pins(tmp_path, monkeypatch):
    import json

    from embedding_data import acs_mapping_bundle
    from embedding_data.acs_mapping import app

    received = {}
    def build(data_dir, run_id, request, reference_id, **kwargs):
        received.update(root=data_dir, run_id=run_id, request=request,
                        reference_id=reference_id, **kwargs)
        return {'run_id': run_id, 'directory': str(tmp_path), 'outputs_sha256': 'f' * 64}

    monkeypatch.setattr(acs_mapping_bundle, 'build', build)
    options = {
        '--references': 'reference', '--references-sha256': '1' * 64,
        '--codes-run': 'codes', '--codes-outputs-sha256': '2' * 64,
        '--geography-run': 'geography', '--geography-outputs-sha256': '3' * 64,
        '--ipums-run': 'ipums', '--ipums-outputs-sha256': '4' * 64,
        '--ipums-references-sha256': '5' * 64, '--data-dir': str(tmp_path),
    }
    result = CliRunner().invoke(app, ['build', 'mapping',
        *[item for pair in options.items() for item in pair]])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)['outputs_sha256'] == 'f' * 64
    assert received['request'].codes_outputs_sha256 == '2' * 64
    assert received['request'].geography_outputs_sha256 == '3' * 64
    assert received['request'].ipums_outputs_sha256 == '4' * 64
    assert received['request'].ipums_references_receipt_sha256 == '5' * 64
    assert received['expected_reference_receipt_sha256'] == '1' * 64
    assert received['root'] == tmp_path


def test_shared_reference_seed_preserves_strict_constructor_guard(tmp_path, monkeypatch):
    import httpx
    from acs_mapping_fixtures import seed_mapping_references

    seed_mapping_references(tmp_path, monkeypatch)
    with pytest.raises(AssertionError, match='offline ACS mapping'):
        httpx.Client(transport=httpx.MockTransport(lambda request: None))
