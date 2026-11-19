'''Pinned Stage 8 and Stage 4 input selection for the ACS wage microdata.'''

import json
import platform
import shutil
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from importlib.metadata import version

import pytest
from acs_mapping_fixtures import forbid_external_access
from acs_wage_fixtures import copy_template, wage_mapping

from embedding_data import (
    acs_mapping_bundle,
    ipums_ddi,
    ita_establishment_inputs,
    manifest,
    paths,
    target_io,
)
from embedding_data import acs_wage_inputs as inputs
from embedding_data import acs_wage_rules as rules

LISTED = [(name, code) for name, labels in rules.DDI_LABELS.items() for code in labels]


@pytest.fixture(scope='module')
def template(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patches:
        yield wage_mapping(tmp_path_factory.mktemp('wage-input-template'), patches)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    forbid_external_access(monkeypatch)


@pytest.fixture(name='fixture')
def copied_template(template, tmp_path):
    return copy_template(template, tmp_path)


def select(fixture, **changes):
    arguments = {
        name: fixture[name]
        for name in ('mapping_run', 'mapping_outputs_sha256', 'codes_run', 'codes_outputs_sha256')
    } | changes
    return inputs.select_wage_inputs(fixture['data_dir'], arguments.pop('mapping_run'),
                                     **arguments)


def forbidden(*args, **kwargs):
    raise AssertionError('a selected file was read before its detached pin was checked')


def mapping_dir(fixture):
    return fixture['data_dir'] / 'derived/acs/mapping' / fixture['mapping_run']


def codes_dir(fixture, run=None):
    return fixture['data_dir'] / 'derived/codes' / (run or fixture['codes_run'])


def ddi_with(labels: dict) -> dict:
    return {'variables': [
        {'name': name, 'categories': [{'value': code, 'label': label}
                                      for code, label in categories.items()]}
        for name, categories in labels.items()]}


def reserialize(file):
    '''Rewrite a JSON file with the same content in other bytes, and return its new hash.'''
    file.write_text(json.dumps(json.loads(file.read_text())) + '\n')
    return manifest.sha256_file(file)


def repin(directory, mutate):
    '''Edit a run's inputs.json, rewrite its inventory and return the new detached pin.'''
    file = directory / 'inputs.json'
    recorded = json.loads(file.read_text())
    mutate(recorded)
    target_io.write_json(file, recorded)
    names = [path.name for path in directory.iterdir() if path.name != 'outputs.json']
    target_io.write_json(directory / 'outputs.json', target_io.inventory(directory, names))
    return manifest.sha256_file(directory / 'outputs.json')


def test_inventory_names_match_stages_8_and_4():
    assert inputs.MAPPING_FILES == set(acs_mapping_bundle.FILES)
    assert inputs.CODES_FILES == ita_establishment_inputs.INVENTORY_NAMES


def test_selects_the_pinned_mapping_codes_and_ddi(fixture):
    selected = select(fixture)
    assert selected.core == (
        fixture['data_dir'] / 'derived/acs/mapping/mapping/acs_core_canonical.parquet')
    assert selected.labels == rules.DDI_LABELS
    assert set(selected.provenance) == {'mapping', 'codes', 'ddi'}


def test_selection_records_the_runs_pins_tables_and_verified_ddi(fixture):
    selected = select(fixture)
    mapping, codes = mapping_dir(fixture), codes_dir(fixture)
    recorded = json.loads((mapping / 'inputs.json').read_text())
    [cited] = [citation for citation in recorded['sources']['acs/core']['raw_citations']
               if citation['path'].endswith('.xml')]
    assert (selected.mapping_run, selected.mapping_outputs_sha256, selected.codes_run,
            selected.codes_outputs_sha256) == tuple(fixture[name] for name in (
                'mapping_run', 'mapping_outputs_sha256', 'codes_run', 'codes_outputs_sha256'))
    assert selected.naics_nodes == codes / 'naics_nodes.parquet'
    assert selected.naics_edges == codes / 'naics_edges.parquet'
    assert selected.ddi == fixture['data_dir'] / 'raw' / cited['path']
    assert selected.provenance == {
        'mapping': {'run_id': 'mapping', 'outputs_sha256': fixture['mapping_outputs_sha256'],
                    'outputs': json.loads((mapping / 'outputs.json').read_text())},
        'codes': {'run_id': fixture['codes_run'],
                  'outputs_sha256': fixture['codes_outputs_sha256'],
                  'outputs': json.loads((codes / 'outputs.json').read_text())},
        'ddi': cited,
    }
    assert cited['sha256'] == manifest.sha256_file(selected.ddi)
    selected.verify()


def test_wrong_mapping_pin_is_refused_before_inputs_are_read(fixture, monkeypatch):
    monkeypatch.setattr(inputs, 'read_json', forbidden)
    with pytest.raises(ValueError, match='detached inventory checksum differs'):
        select(fixture, mapping_outputs_sha256='0' * 64)


@pytest.mark.parametrize('edit', ['append_byte_to_core', 'add_extra_file', 'remove_report'])
def test_changed_mapping_inventory_is_refused(fixture, edit):
    directory = mapping_dir(fixture)
    if edit == 'append_byte_to_core':
        core = directory / 'acs_core_canonical.parquet'
        core.write_bytes(core.read_bytes() + b'\0')
    elif edit == 'add_extra_file':
        (directory / 'extra.json').write_text('{}\n')
    else:
        (directory / 'report.json').unlink()
    with pytest.raises(ValueError, match='inventory'):
        select(fixture)


def test_codes_selection_must_equal_the_mapping_request(fixture):
    # A valid copy under another name has the same pin, so only the request can refuse it.
    shutil.copytree(codes_dir(fixture), codes_dir(fixture, 'other'))
    with pytest.raises(ValueError, match='codes selection differs from the mapping run'):
        select(fixture, codes_run='other')


def test_codes_pin_must_equal_the_mapping_request(fixture):
    pin = reserialize(codes_dir(fixture) / 'outputs.json')
    with pytest.raises(ValueError, match='codes selection differs from the mapping run'):
        select(fixture, codes_outputs_sha256=pin)


def test_wrong_codes_pin_is_refused(fixture):
    reserialize(codes_dir(fixture) / 'outputs.json')
    with pytest.raises(ValueError, match='detached inventory checksum differs'):
        select(fixture)


@pytest.mark.parametrize('edit', ['append_byte_to_nodes', 'add_extra_file'])
def test_changed_codes_inventory_is_refused(fixture, edit):
    directory = codes_dir(fixture)
    if edit == 'append_byte_to_nodes':
        nodes = directory / 'naics_nodes.parquet'
        nodes.write_bytes(nodes.read_bytes() + b'\0')
    else:
        (directory / 'extra.json').write_text('{}\n')
    with pytest.raises(ValueError, match='inventory'):
        select(fixture)


def test_changed_ddi_bytes_are_refused(fixture):
    ddi = select(fixture).ddi
    ddi.write_bytes(ddi.read_bytes() + b'\n')
    with pytest.raises(ValueError, match='changed since it was downloaded'):
        select(fixture)


@pytest.mark.parametrize('count', [0, 2])
def test_the_mapping_run_must_cite_exactly_one_core_ddi(fixture, count):
    def mutate(recorded):
        source = recorded['sources']['acs/core']
        [ddi] = [c for c in source['raw_citations'] if c['path'].endswith('.xml')]
        others = [c for c in source['raw_citations'] if c != ddi]
        source['raw_citations'] = others + [ddi] * count
    pin = repin(mapping_dir(fixture), mutate)
    with pytest.raises(ValueError, match='does not cite one core DDI'):
        select(fixture, mapping_outputs_sha256=pin)


def test_selection_refuses_a_delivered_ddi_with_a_changed_label(fixture, monkeypatch):
    original = ipums_ddi.read_ddi

    def relabeled(file):
        ddi = original(file)
        for variable in ddi['variables']:
            for category in variable['categories']:
                if (variable['name'], category['value']) == ('CLASSWKRD', '22'):
                    category['label'] = 'Private'
        return ddi

    monkeypatch.setattr(ipums_ddi, 'read_ddi', relabeled)
    with pytest.raises(ValueError, match='delivered DDI labels differ'):
        select(fixture)


def test_confirm_labels_refuses_one_changed_label():
    labels = deepcopy(rules.DDI_LABELS)
    labels['CLASSWKRD']['22'] = 'Private'
    with pytest.raises(ValueError, match='delivered DDI labels differ'):
        inputs.confirm_labels(ddi_with(labels))


@pytest.mark.parametrize('change', ['relabel', 'recase', 'remove'])
@pytest.mark.parametrize(('name', 'code'), LISTED)
def test_confirm_labels_refuses_any_changed_or_missing_listed_label(name, code, change):
    labels = deepcopy(rules.DDI_LABELS)
    if change == 'relabel':
        labels[name][code] += ' (other)'
    elif change == 'recase':
        labels[name][code] = labels[name][code].upper()
    else:
        del labels[name][code]
    with pytest.raises(ValueError, match='delivered DDI labels differ'):
        inputs.confirm_labels(ddi_with(labels))


@pytest.mark.parametrize('name', list(rules.DDI_LABELS))
def test_confirm_labels_refuses_a_missing_variable(name):
    labels = {other: codes for other, codes in rules.DDI_LABELS.items() if other != name}
    with pytest.raises(ValueError, match='delivered DDI labels differ'):
        inputs.confirm_labels(ddi_with(labels))


def test_confirm_labels_returns_a_copy_of_the_listed_labels():
    before = deepcopy(rules.DDI_LABELS)
    ddi = ddi_with({'AGE': {}, **{name: {'00': 'N/A', **codes}
                                  for name, codes in rules.DDI_LABELS.items()}})
    labels = inputs.confirm_labels(ddi)
    assert labels == before
    labels['CLASSWKRD']['22'] = 'Private'
    labels['WKSWORK2'].clear()
    assert rules.DDI_LABELS == before


@pytest.mark.parametrize('run_id', ['../mapping', '', '.hidden', 'a/b'])
def test_unsafe_run_ids_are_refused(fixture, run_id):
    with pytest.raises(ValueError, match='unsafe selected run ID'):
        select(fixture, mapping_run=run_id)


@pytest.mark.parametrize(('argument', 'value', 'message'), [
    ('codes_run', '../fixture_codes', 'unsafe selected run ID'),
    ('codes_run', '.hidden', 'unsafe selected run ID'),
    ('mapping_outputs_sha256', 'uppercase', 'invalid detached checksum'),
    ('codes_outputs_sha256', 'uppercase', 'invalid detached checksum'),
    ('codes_outputs_sha256', '0' * 63, 'invalid detached checksum'),
])
def test_unsafe_codes_run_and_malformed_pins_are_refused(fixture, monkeypatch, argument, value,
                                                         message):
    value = fixture[argument].upper() if value == 'uppercase' else value
    monkeypatch.setattr(inputs, 'read_json', forbidden)
    with pytest.raises(ValueError, match=message):
        select(fixture, **{argument: value})


def test_symlinked_mapping_directory_is_refused(fixture, tmp_path):
    directory = mapping_dir(fixture)
    moved = directory.rename(tmp_path / 'elsewhere')
    directory.symlink_to(moved, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        select(fixture)


@pytest.mark.parametrize('parent', ['derived/acs/mapping', 'derived/codes'])
def test_symlinked_run_parent_is_refused(fixture, tmp_path, parent):
    directory = fixture['data_dir'] / parent
    moved = directory.rename(tmp_path / 'elsewhere')
    directory.symlink_to(moved, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        select(fixture)


def test_verify_detects_a_change_after_selection(fixture):
    selected = select(fixture)
    selected.core.write_bytes(selected.core.read_bytes() + b'\0')
    with pytest.raises(ValueError, match='selected inputs changed'):
        selected.verify()


def test_verify_refuses_an_edited_selection(fixture):
    selected = select(fixture)
    selected.provenance['ddi']['size'] += 1
    with pytest.raises(ValueError, match='selected inputs changed'):
        selected.verify()


def test_selection_compares_its_two_snapshots(fixture, monkeypatch):
    original = inputs._snapshot
    taken = []

    def drifting(*args):
        taken.append(original(*args))
        return replace(taken[-1], labels={}) if len(taken) > 1 else taken[-1]

    monkeypatch.setattr(inputs, '_snapshot', drifting)
    with pytest.raises(ValueError, match='selected inputs changed during validation'):
        select(fixture)
    assert len(taken) == 2


def test_read_json_is_strict(tmp_path):
    file = tmp_path / 'value.json'
    for text in ('{"a": 1, "a": 2}', '{"a": NaN}', '[{"a": 1}]'):
        file.write_text(text)
        with pytest.raises(ValueError):
            inputs.read_json(file)


@pytest.mark.parametrize('number', ['Infinity', '-Infinity', '1e999', '-1e999'])
def test_read_json_refuses_every_non_finite_number(tmp_path, number):
    file = tmp_path / 'value.json'
    file.write_text('{"a": {"b": [' + number + ']}}')
    with pytest.raises(ValueError, match='non-finite JSON number'):
        inputs.read_json(file)


def test_read_json_returns_the_object(tmp_path):
    file = tmp_path / 'value.json'
    file.write_text('{"a": {"b": [1, 2.5, -1e300]}, "c": null}', encoding='utf-8')
    assert inputs.read_json(file) == {'a': {'b': [1, 2.5, -1e300]}, 'c': None}


def test_freeze_software_records_files_python_dependencies_and_lock():
    snapshot = inputs.freeze_software()
    assert set(snapshot) == {'files', 'python', 'python_full', 'implementation',
                             'dependencies', 'uv_lock_sha256'}
    assert snapshot['files'] == {name: target_io.file_record(paths.PROJECT_ROOT / name)
                                 for name in inputs.SOFTWARE_FILES}
    assert snapshot['python'] == platform.python_version()
    assert snapshot['python_full'] == sys.version
    assert snapshot['implementation'] == platform.python_implementation()
    assert snapshot['dependencies']['polars'] == version('polars')
    assert snapshot['uv_lock_sha256'] == manifest.sha256_file(paths.PROJECT_ROOT / 'uv.lock')


def test_software_files_list_every_module_the_import_loads():
    probe = 'import sys, embedding_data.acs_wage_inputs; print("\\n".join(sorted(sys.modules)))'
    loaded = set(subprocess.run([sys.executable, '-c', probe], check=True, capture_output=True,
                                text=True).stdout.split())
    assert not loaded & {'dotenv', 'ipumspy'}
    files = {'src/embedding_data/' + (name.partition('.')[2] or '__init__') + '.py'
             for name in loaded if name.partition('.')[0] == 'embedding_data'}
    assert 'src/embedding_data/acs_wage_inputs.py' in files
    assert files | {'pyproject.toml', 'uv.lock'} <= set(inputs.SOFTWARE_FILES)
    assert len(set(inputs.SOFTWARE_FILES)) == len(inputs.SOFTWARE_FILES)
