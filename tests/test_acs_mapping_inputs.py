import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from acs_mapping_fixtures import seed_selected_inputs

from embedding_data import acs_mapping_inputs as mapping_inputs
from embedding_data import manifest, paths, target_io
from embedding_data.acs_mapping_inputs import select_inputs

@pytest.fixture
def seeded(tmp_path, monkeypatch):
    return seed_selected_inputs(tmp_path, monkeypatch)


def test_selects_three_acs_deliveries_and_retains_unresolved_status(seeded):
    selected = select_inputs(seeded.data_dir, seeded.request)
    assert set(selected.sources) == {'acs/core', 'acs/five_year', 'acs/vintage'}
    assert selected.provenance['ipums']['measurement_status'] == 'unresolved'
    assert len(selected.codes) == 12
    assert selected.sources['acs/core'].definition == seeded.sources['acs/core']['definition']
    json.dumps(selected.provenance)
    selected.verify()


@pytest.mark.parametrize('pin', ['codes_outputs_sha256', 'geography_outputs_sha256',
                                 'ipums_outputs_sha256', 'ipums_references_receipt_sha256'])
def test_wrong_upstream_pin_is_rejected(seeded, pin):
    with pytest.raises(ValueError, match='detached'):
        select_inputs(seeded.data_dir, replace(seeded.request, **{pin: '0' * 64}))


@pytest.mark.parametrize('family', ['codes', 'geography', 'ipums'])
@pytest.mark.parametrize('defect', ['hash', 'size', 'schema', 'count', 'raw', 'extra', 'empty',
                                   'version', 'run', 'duplicate_json', 'malformed_json'])
def test_selected_bundles_reject_defects(seeded, family, defect):
    root = seeded.data_dir
    directory = root / ('derived/ipums/verification' if family == 'ipums'
                        else f'derived/{family}') / getattr(seeded.request, f'{family}_run')
    request = seeded.request
    if defect in {'extra', 'empty'}:
        file = directory / 'unexpected'
        file.mkdir() if defect == 'empty' else file.write_text('extra')
    elif defect == 'raw':
        raw = next(root.glob('raw/acs/core/*/*.xml'))
        raw.write_text(raw.read_text() + 'changed')
    elif defect in {'hash', 'size', 'schema', 'count'}:
        inventory = json.loads((directory / 'outputs.json').read_text())
        name = next(n for n in inventory if n.endswith('.parquet'))
        if defect == 'hash':
            inventory[name]['sha256'] = '0' * 64
        elif defect == 'size':
            inventory[name]['size'] += 1
        else:
            report_file = directory / ('inputs.json' if family == 'ipums' else 'report.json')
            report = json.loads(report_file.read_text())
            recorded = report['aggregate_contracts' if family == 'ipums' else 'tables'][name]
            recorded['rows' if defect == 'count' else 'schema'] = -1 if defect == 'count' else {}
            target_io.write_json(report_file, report)
            inventory[report_file.name] = target_io.file_record(report_file)
        target_io.write_json(directory / 'outputs.json', inventory)
    else:
        file = directory / 'inputs.json'
        data = json.loads(file.read_text())
        if defect in {'version', 'run'}:
            key = 'run_id' if defect == 'run' else (
                'format_version' if family == 'ipums' else 'schema_version')
            data[key] = 'wrong'
            target_io.write_json(file, data)
        elif defect == 'duplicate_json':
            file.write_text('{"run_id":"a","run_id":"b"}')
        else:
            file.write_text('{')
        inventory = json.loads((directory / 'outputs.json').read_text())
        inventory['inputs.json'] = target_io.file_record(file)
        target_io.write_json(directory / 'outputs.json', inventory)
    request = replace(request, **{f'{family}_outputs_sha256':
                                  manifest.sha256_file(directory / 'outputs.json')})
    with pytest.raises((ValueError, OSError)):
        select_inputs(root, request)


def test_unrelated_manifest_append_is_allowed(seeded):
    selected = select_inputs(seeded.data_dir, seeded.request)
    file = seeded.data_dir / 'raw/unrelated.txt'
    file.write_text('unrelated')
    manifest.append_entries(paths.manifest_path(seeded.data_dir), [manifest.describe_file(
        file, seeded.data_dir / 'raw', retrieved_at=datetime.now(UTC),
        client='fixture', client_version='1')])
    selected.verify()


def test_revalidation_detects_software_and_dependency_mutation(seeded, monkeypatch):
    selected = select_inputs(seeded.data_dir, seeded.request)
    original = mapping_inputs.freeze_software
    def drift():
        result = original()
        result['dependencies']['polars'] = 'changed'
        return result
    monkeypatch.setattr(mapping_inputs, 'freeze_software', drift)
    with pytest.raises(ValueError, match='software'):
        selected.verify()


@pytest.mark.parametrize('change', ['frames', 'citation', 'source', 'dependency'])
def test_repinned_upstream_semantics_are_checked(seeded, change):
    family = 'geography' if change == 'frames' else 'codes'
    directory = seeded.data_dir / f'derived/{family}' / getattr(seeded.request, f'{family}_run')
    file = directory / 'inputs.json'
    data = json.loads(file.read_text())
    if change == 'frames':
        data['reference_frames']['administrative'] = '2020'
    elif change == 'citation':
        data['raw'][0]['sha256'] = '0' * 64
    elif change == 'source':
        data['source_parquet']['sha256'] = '0' * 64
    else:
        data['dependencies']['polars'] = 'changed'
    target_io.write_json(file, data)
    inventory = json.loads((directory / 'outputs.json').read_text())
    inventory['inputs.json'] = target_io.file_record(file)
    target_io.write_json(directory / 'outputs.json', inventory)
    request = replace(seeded.request, **{f'{family}_outputs_sha256':
                       manifest.sha256_file(directory / 'outputs.json')})
    with pytest.raises(ValueError):
        select_inputs(seeded.data_dir, request)


@pytest.mark.parametrize('field,value', [('codes_run', '../escape'),
                                        ('geography_run', 'alternate'),
                                        ('codes_outputs_sha256', None)])
def test_alternate_and_unsafe_selections_fail(seeded, field, value):
    with pytest.raises((ValueError, OSError)):
        select_inputs(seeded.data_dir, replace(seeded.request, **{field: value}))


def test_revalidation_detects_input_mutation(seeded):
    selected = select_inputs(seeded.data_dir, seeded.request)
    file = selected.sources['acs/core'].parquet
    file.write_bytes(file.read_bytes() + b'changed')
    with pytest.raises(ValueError):
        selected.verify()


def test_selected_source_metadata_cannot_be_mutated_silently(seeded):
    selected = select_inputs(seeded.data_dir, seeded.request)
    selected.sources['acs/core'].parquet_record['rows'] += 1
    with pytest.raises(ValueError):
        selected.verify()


def test_full_bundle_paths_cannot_use_symlinked_ancestors(seeded):
    directory = seeded.data_dir / 'derived/codes'
    moved = seeded.data_dir / 'original-codes'
    directory.rename(moved)
    directory.symlink_to(moved)
    with pytest.raises(ValueError):
        select_inputs(seeded.data_dir, seeded.request)


def test_mutation_during_selection_is_detected(seeded, monkeypatch):
    original = mapping_inputs._select_snapshot
    calls = 0
    def mutate(*args):
        nonlocal calls
        result = original(*args)
        calls += 1
        if calls == 1:
            file = result[0]['acs/core'].parquet
            file.write_bytes(file.read_bytes() + b'changed')
        return result
    monkeypatch.setattr(mapping_inputs, '_select_snapshot', mutate)
    with pytest.raises(ValueError):
        select_inputs(seeded.data_dir, seeded.request)


def test_software_mutation_during_selection_is_detected(seeded, monkeypatch):
    original = mapping_inputs.freeze_software
    calls = 0
    def drift():
        nonlocal calls
        result = original()
        calls += 1
        if calls > 1:
            result['dependencies']['polars'] = 'changed'
        return result
    monkeypatch.setattr(mapping_inputs, 'freeze_software', drift)
    with pytest.raises(ValueError, match='software'):
        select_inputs(seeded.data_dir, seeded.request)


@pytest.mark.parametrize('defect', ['duplicate_weights', 'malformed_weights', 'report_version'])
def test_all_stage7_json_is_strict_and_versioned(seeded, defect):
    directory = seeded.data_dir / 'derived/ipums/verification' / seeded.request.ipums_run
    if defect == 'report_version':
        file = directory / 'report.json'
        report = json.loads(file.read_text())
        report['format_version'] = 'wrong'
        target_io.write_json(file, report)
    else:
        file = directory / 'weight_rules.json'
        file.write_text('{"x":1,"x":2}' if defect == 'duplicate_weights' else '{')
    inventory = json.loads((directory / 'outputs.json').read_text())
    inventory[file.name] = target_io.file_record(file)
    target_io.write_json(directory / 'outputs.json', inventory)
    request = replace(seeded.request, ipums_outputs_sha256=manifest.sha256_file(
        directory / 'outputs.json'))
    with pytest.raises(ValueError):
        select_inputs(seeded.data_dir, request)
