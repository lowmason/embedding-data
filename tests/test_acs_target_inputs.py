'''Authentication boundaries for Stage 9's pinned Stage 8 consumption.'''

import json
import shutil
import sys
from dataclasses import asdict, replace

import pytest
from acs_mapping_fixtures import forbid_external_access
from acs_target_fixtures import authenticated_mapping

from embedding_data import acs_mapping_inputs, manifest, target_io
from embedding_data import acs_target_inputs as target_inputs

@pytest.fixture(scope='module')
def mapping_template(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patches:
        yield authenticated_mapping(tmp_path_factory.mktemp('target-input-template'), patches)


@pytest.fixture
def mapped(tmp_path, monkeypatch, mapping_template):
    forbid_external_access(monkeypatch)
    data_dir = tmp_path / 'data'
    shutil.copytree(mapping_template['data_dir'], data_dir)
    return mapping_template | {'data_dir': data_dir,
                               'mapping': data_dir / 'derived/acs/mapping/mapping'}


def select(fixture, **changes):
    arguments = {'expected_mapping_outputs_sha256': fixture['mapping_outputs_sha256'],
                 'request': fixture['request']} | changes
    return target_inputs.select_targets(fixture['data_dir'], 'mapping', **arguments)


def repin(fixture, mutate):
    directory = fixture['mapping']
    file = directory / 'inputs.json'
    recorded = json.loads(file.read_text())
    mutate(recorded)
    target_io.write_json(file, recorded)
    names = [path.name for path in directory.iterdir() if path.name != 'outputs.json']
    target_io.write_json(directory / 'outputs.json', target_io.inventory(directory, names))
    return manifest.sha256_file(directory / 'outputs.json')


def test_wrong_mapping_pin_is_rejected(mapped):
    with pytest.raises(ValueError, match='checksum|pin'):
        select(mapped, expected_mapping_outputs_sha256='0' * 64)


@pytest.mark.parametrize('field', asdict(acs_mapping_inputs.SelectionRequest(*(['x'] * 7))))
def test_every_explicit_request_field_is_bound(mapped, field):
    original = getattr(mapped['request'], field)
    changed = '0' * 64 if field.endswith('sha256') else original + '_other'
    with pytest.raises((ValueError, OSError)):
        select(mapped, request=replace(mapped['request'], **{field: changed}))


@pytest.mark.parametrize('defect', ['request', 'provenance', 'source_hash', 'source_count',
                                   'definition', 'ddi', 'raw', 'rules', 'frames', 'software'])
def test_self_consistent_inventory_cannot_rewrite_mapping_semantics(mapped, defect):
    def mutate(data):
        source = data['sources']['acs/core']
        if defect == 'request':
            data['selected_upstreams']['request']['ipums_references_receipt_sha256'] = '0' * 64
        elif defect == 'provenance':
            data['selected_upstreams']['provenance']['codes']['run_id'] = 'other'
        elif defect == 'source_hash':
            source['parquet_record']['sha256'] = '0' * 64
        elif defect == 'source_count':
            source['parquet_record']['rows'] += 1
        elif defect in {'definition', 'ddi'}:
            source[defect] = {}
        elif defect == 'raw':
            source['raw_citations'] = []
        elif defect == 'rules':
            data['rules']['classification'] = 'other'
        elif defect == 'frames':
            data['frames']['population_year'] = 2022
        else:
            data['software']['dependencies']['polars'] = 'other'
    pin = repin(mapped, mutate)
    with pytest.raises(ValueError):
        select(mapped, expected_mapping_outputs_sha256=pin)


def test_selected_core_and_all_eight_physical_paths_are_preserved(mapped):
    selected = select(mapped)
    upstream = acs_mapping_inputs.select_inputs(mapped['data_dir'], mapped['request'])
    assert selected.upstream.sources['acs/core'] == upstream.sources['acs/core']
    assert selected.tables == {name: mapped['mapping'] / (name + '.parquet') for name in (
        'acs_code_lookup', 'acs_area_lookup', 'puma_county_factors', 'puma_msa_factors',
        'puma_msa_coverage', 'acs_core_canonical', 'acs_five_year_canonical',
        'acs_vintage_canonical')}
    recorded = json.loads((mapped['mapping'] / 'inputs.json').read_text())
    assert selected.provenance['mapping']['software'] == recorded['software']
    assert selected.provenance['mapping']['outputs_sha256'] == mapped['mapping_outputs_sha256']
    assert selected.provenance['selected_upstreams']['provenance'] == upstream.provenance
    selected.verify()


@pytest.mark.parametrize('location', ['companion', 'upstream'])
def test_later_physical_mutation_is_detected(mapped, location):
    selected = select(mapped)
    file = (selected.tables['acs_core_canonical'] if location == 'companion'
            else selected.upstream.sources['acs/core'].parquet)
    file.write_bytes(file.read_bytes() + b'changed')
    with pytest.raises(ValueError):
        selected.verify()


@pytest.mark.parametrize('identity', ['files', 'dependencies', 'python_full'])
def test_stage9_software_snapshot_is_rechecked(mapped, monkeypatch, identity):
    selected = select(mapped)
    original = target_inputs.freeze_target_software
    def drift():
        snapshot = original()
        snapshot[identity] = {'changed': 'changed'}
        return snapshot
    monkeypatch.setattr(target_inputs, 'freeze_target_software', drift)
    with pytest.raises(ValueError, match='software'):
        selected.verify()


def test_stage9_freeze_has_literal_complete_checkpoint_inventory():
    snapshot = target_inputs.freeze_target_software()
    assert snapshot['python_full'] == sys.version
    assert set(snapshot['files']) == set(acs_mapping_inputs.SOFTWARE_FILES) | {
        'src/embedding_data/target_contract.py', 'src/embedding_data/acs_target_contract.py',
        'src/embedding_data/acs_target_inputs.py',
        'src/embedding_data/acs_target_rules.py',
        'src/embedding_data/acs_target_units.py',
        'src/embedding_data/acs_target_weights.py',
        'src/embedding_data/acs_target_membership.py', 'pyproject.toml', 'uv.lock'}
    assert snapshot['dependencies']['polars']


def test_nonselected_replay_cannot_supply_a_missing_mapping_file(mapped):
    shutil.copytree(mapped['mapping'], mapped['mapping'].with_name('replay'))
    (mapped['mapping'] / 'acs_core_canonical.parquet').unlink()
    with pytest.raises((ValueError, OSError)):
        select(mapped)


def test_mutable_selected_metadata_is_not_an_authority(mapped):
    selected = select(mapped)
    selected.upstream.sources['acs/core'].parquet_record['rows'] += 1
    with pytest.raises(ValueError):
        selected.verify()


def test_exact_inherited_d5_diagnostic_survives_in_target_provenance(tmp_path, monkeypatch):
    name = acs_mapping_inputs.CLI_FILE
    context = {
        'family': 'geography', 'run_id': acs_mapping_inputs.HISTORICAL_GEOGRAPHY_RUN,
        'outputs_sha256': acs_mapping_inputs.HISTORICAL_GEOGRAPHY_PIN,
        'stage7_run_id': 'fixture_ipums', 'stage7_outputs_sha256': 'a' * 64,
        'stage7_software': {'files': {name: {'sha256': acs_mapping_inputs.EXECUTING_CLI_SHA256}}},
        'stage8_software': {'files': {name: {'sha256': acs_mapping_inputs.EXECUTING_CLI_SHA256}}},
    }
    diagnostic = acs_mapping_inputs._historical_cli_compatibility(
        name, acs_mapping_inputs.HISTORICAL_CLI_SHA256,
        acs_mapping_inputs.EXECUTING_CLI_SHA256, context)
    assert diagnostic['rule'] == 'stage8-owner-d5-historical-geography-cli'
    original = acs_mapping_inputs._reference_bundle
    def authenticated_with_diagnostic(*args, **kwargs):
        files, provenance = original(*args, **kwargs)
        # Real temporary bundles use current software. Inject only the existing
        # diagnostic at the authenticated seam to exercise Stage 9 propagation.
        if args[1] == 'geography':
            provenance['software_compatibility'] = [diagnostic]
        return files, provenance
    monkeypatch.setattr(acs_mapping_inputs, '_reference_bundle', authenticated_with_diagnostic)
    fixture = authenticated_mapping(tmp_path, monkeypatch)
    selected = select(fixture)
    assert selected.provenance['selected_upstreams']['provenance']['geography'][
        'software_compatibility'] == [diagnostic]
    selected.verify()


def test_software_drift_during_selection_is_detected(mapped, monkeypatch):
    original = target_inputs.freeze_target_software
    calls = 0
    def drift():
        nonlocal calls
        calls += 1
        snapshot = original()
        if calls > 1:
            snapshot['python_full'] = 'changed'
        return snapshot
    monkeypatch.setattr(target_inputs, 'freeze_target_software', drift)
    with pytest.raises(ValueError, match='software'):
        select(mapped)


def test_input_drift_during_selection_is_detected(mapped, monkeypatch):
    original = target_inputs._mapping_snapshot
    calls = 0
    def mutate(*args):
        nonlocal calls
        result = original(*args)
        calls += 1
        if calls == 1:
            file = result[2]['acs_core_canonical']
            file.write_bytes(file.read_bytes() + b'changed')
        return result
    monkeypatch.setattr(target_inputs, '_mapping_snapshot', mutate)
    with pytest.raises(ValueError):
        select(mapped)


def test_external_pin_is_checked_before_mapping_json_is_parsed(mapped):
    (mapped['mapping'] / 'inputs.json').write_text('{invalid')
    with pytest.raises(ValueError, match='detached inventory checksum'):
        select(mapped, expected_mapping_outputs_sha256='0' * 64)


def test_valid_alternate_upstream_cannot_be_mixed_with_selected_mapping(mapped):
    request = mapped['request']
    original = mapped['data_dir'] / 'derived/codes' / request.codes_run
    alternate = original.with_name(request.codes_run + '_other')
    shutil.copytree(original, alternate)
    file = alternate / 'inputs.json'
    inputs = json.loads(file.read_text())
    inputs['run_id'] = alternate.name
    target_io.write_json(file, inputs)
    names = [path.name for path in alternate.iterdir() if path.name != 'outputs.json']
    target_io.write_json(alternate / 'outputs.json', target_io.inventory(alternate, names))
    other = replace(request, codes_run=alternate.name,
                    codes_outputs_sha256=manifest.sha256_file(alternate / 'outputs.json'))
    acs_mapping_inputs.select_inputs(mapped['data_dir'], other).verify()
    with pytest.raises(ValueError, match='explicit request'):
        select(mapped, request=other)
