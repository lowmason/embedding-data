import json

import polars as pl
import pytest
from target_fixtures import acquired_tree, forbid_external_access

from embedding_data import ita_assignment_prepare as preparation
from embedding_data import ita_target_build as builder
from embedding_data import manifest, target_io
from embedding_data.target_contract import TARGET_SCHEMA

def test_build_manifest_and_cached_replay(tmp_path, monkeypatch):
    prepared = acquired_tree(tmp_path, monkeypatch)
    forbid_external_access(monkeypatch)
    before = {p: manifest.sha256_file(p) for p in tmp_path.rglob('*') if p.is_file()}
    first = builder.build(tmp_path, prepared.directory.name, 'first')
    second = builder.build(tmp_path, prepared.directory.name, 'second')
    names = {'ita_county_assignments.parquet', 'ita_area_mix.parquet',
             'county_denominators.parquet', 'target_flag_counts.parquet',
             'inputs.json', 'report.json', 'outputs.json'}
    assert {p.name for p in first.iterdir()} == names
    assert pl.read_parquet(first / 'ita_area_mix.parquet').schema == TARGET_SCHEMA
    for name in names:
        if name.endswith('.parquet'):
            assert pl.read_parquet(first / name).equals(pl.read_parquet(second / name))
    assert builder.verify_bundle(first, tmp_path)['selected_year_partition']['eligible'] == 5
    outputs = json.loads((first / 'outputs.json').read_text())
    assert set(outputs) == names - {'outputs.json'}
    for name in names:
        if name.endswith('.parquet'):
            assert {'sha256', 'size', 'rows', 'schema', 'columns'} <= outputs[name].keys()
    a, b = [json.loads((p / 'inputs.json').read_text()) for p in (first, second)]
    for inputs in (a, b):
        inputs.pop('target_run_id')
        inputs['execution'].pop('created_at')
    assert a == b
    assert (first / 'report.json').read_bytes() == (second / 'report.json').read_bytes()
    assert all(manifest.sha256_file(p) == digest for p, digest in before.items())


@pytest.mark.parametrize('year,run_id', [(2022, 'bad'), (2023, '../bad'), (2023, 'a.part')])
def test_reject_unsafe_options_before_input_access(tmp_path, year, run_id):
    with pytest.raises(ValueError):
        builder.build(tmp_path, 'missing', run_id, year=year)
    assert not list(tmp_path.rglob('*'))


@pytest.mark.parametrize('defect', ['source', 'canonical', 'bundle', 'request', 'catalog',
                                  'receipt', 'response', 'completion', 'software'])
def test_build_refuses_changed_inputs(tmp_path, monkeypatch, defect):
    checkout = None
    if defect == 'software':
        checkout = copy_execution_checkout(tmp_path / 'execution', monkeypatch)
    prepared = acquired_tree(tmp_path, monkeypatch)
    forbid_external_access(monkeypatch)
    from embedding_data import ita_assignment_acquire as acquisition
    evidence = acquisition.read_evidence(tmp_path, prepared)
    files = {'source': prepared.selected.summary, 'canonical': prepared.selected.canonical,
             'bundle': prepared.selected.canonical.parent / 'outputs.json',
             'request': prepared.batches[0],
             'catalog': tmp_path / 'raw' / evidence.provenance['catalogs'][0]['path'],
             'receipt': tmp_path / 'raw' / evidence.provenance['receipts'][0]['path'],
             'response': tmp_path / 'raw' / evidence.provenance['responses'][0]['path'],
             'completion': tmp_path / 'raw' / evidence.provenance['completion']['path']}
    if defect == 'software':
        file = checkout / 'src/embedding_data/ita_assignment.py'
        file.write_bytes(file.read_bytes() + b'\n# Changed assignment implementation.\n')
        with pytest.raises(ValueError, match='frozen preparation validation failed'):
            acquisition.acquire(tmp_path, prepared.directory.name)
    elif defect == 'completion':
        files[defect].unlink()
    else:
        file = files[defect]
        file.write_bytes(file.read_bytes() + b'changed')
    with pytest.raises((ValueError, OSError, KeyError)):
        builder.build(tmp_path, prepared.directory.name, 'rejected')
    assert not (tmp_path / 'derived/targets/rejected').exists()


def test_occupied_names_and_verified_output_tampering(tmp_path, monkeypatch):
    prepared = acquired_tree(tmp_path, monkeypatch)
    forbid_external_access(monkeypatch)
    bundle = builder.build(tmp_path, prepared.directory.name, 'first')
    before = target_io.inventory(bundle, list(builder.OUTPUT_NAMES))
    for name in ('first', 'interrupted'):
        if name == 'interrupted':
            (bundle.parent / 'interrupted.part').mkdir()
        with pytest.raises(ValueError, match='exists'):
            builder.build(tmp_path, prepared.directory.name, name)
    assert target_io.inventory(bundle, list(builder.OUTPUT_NAMES)) == before
    (bundle / 'report.json').write_text('{}')
    with pytest.raises(ValueError):
        builder.verify_bundle(bundle, tmp_path)


def test_estimator_change_requires_only_new_target_inventory(tmp_path, monkeypatch):
    checkout = copy_execution_checkout(tmp_path / 'execution', monkeypatch)
    prepared = acquired_tree(tmp_path, monkeypatch)
    first = builder.build(tmp_path, prepared.directory.name, 'first')
    file = checkout / 'src/embedding_data/ita_area_mix.py'
    original_hash = manifest.sha256_file(file)
    file.write_bytes(file.read_bytes() + b'\n# Changed estimator implementation.\n')
    assert manifest.sha256_file(file) != original_hash
    preparation.check_preparation(tmp_path, prepared.directory.name)
    second = builder.build(tmp_path, prepared.directory.name, 'second')
    assert json.loads((first / 'inputs.json').read_text())['software'] != json.loads(
        (second / 'inputs.json').read_text())['software']


@pytest.mark.parametrize('mutation', ['source', 'unrelated_manifest'])
def test_final_publication_rechecks_pins_without_pinning_whole_manifest(
        tmp_path, monkeypatch, mutation):
    from datetime import UTC, datetime

    prepared = acquired_tree(tmp_path, monkeypatch)
    forbid_external_access(monkeypatch)
    original = builder._verify

    def change_after_verification(directory, data_dir):
        result = original(directory, data_dir)
        if mutation == 'source':
            source = prepared.selected.summary
            source.write_bytes(source.read_bytes() + b'changed')
        else:
            unrelated = tmp_path / 'raw/unrelated.txt'
            unrelated.write_text('unrelated manifested original')
            entry = manifest.describe_file(unrelated, tmp_path / 'raw',
                retrieved_at=datetime.now(UTC), client='fixture', client_version='1')
            manifest.append_entries(tmp_path / 'raw/manifest.jsonl', [entry])
        return result

    monkeypatch.setattr(builder, '_verify', change_after_verification)
    if mutation == 'source':
        with pytest.raises(ValueError):
            builder.build(tmp_path, prepared.directory.name, 'boundary')
        assert not (tmp_path / 'derived/targets/boundary').exists()
        assert (tmp_path / 'derived/targets/boundary.part').exists()
    else:
        bundle = builder.build(tmp_path, prepared.directory.name, 'boundary')
        monkeypatch.setattr(builder, '_verify', original)
        assert builder.verify_bundle(bundle, tmp_path)['input_rows'] == 21


def test_no_eligible_records_refuses_empty_target(tmp_path, monkeypatch):
    import target_fixtures

    original = target_fixtures.golden_source_rows
    def excluded():
        rows = original()
        for row in rows[2023]:
            row['state'] = 'PR'
        return rows
    monkeypatch.setattr(target_fixtures, 'golden_source_rows', excluded)
    prepared = acquired_tree(tmp_path, monkeypatch)
    forbid_external_access(monkeypatch)
    with pytest.raises(ValueError, match='no eligible 2023'):
        builder.build(tmp_path, prepared.directory.name, 'empty')
    assert not (tmp_path / 'derived/targets/empty').exists()


@pytest.mark.parametrize('defect', ['native_flags', 'native_node_level', 'index_fanout',
                                  'response_fanout'])
def test_build_rejects_semantic_contradictions(tmp_path, monkeypatch, defect):
    from target_fixtures import corrupt_selected

    from embedding_data import ita_assignment_acquire as acquisition

    prepared = acquired_tree(tmp_path, monkeypatch)
    forbid_external_access(monkeypatch)
    if defect.startswith('native'):
        corrupt_selected(tmp_path, prepared.selected, defect)
    elif defect == 'index_fanout':
        frame = pl.read_parquet(prepared.source_index)
        pl.concat([frame, frame.head(1)]).write_parquet(prepared.source_index)
    else:
        evidence = acquisition.read_evidence(tmp_path, prepared)
        response = tmp_path / 'raw' / evidence.provenance['responses'][0]['path']
        first_row = response.read_bytes().splitlines(keepends=True)[0]
        response.write_bytes(response.read_bytes() + first_row)
    with pytest.raises(ValueError):
        builder.build(tmp_path, prepared.directory.name, 'contradiction')
    assert not (tmp_path / 'derived/targets/contradiction').exists()


@pytest.mark.parametrize('table', ['ita_county_assignments', 'ita_area_mix',
                                 'county_denominators', 'target_flag_counts'])
def test_verifier_rejects_reinventoried_semantic_tampering(tmp_path, monkeypatch, table):
    prepared = acquired_tree(tmp_path, monkeypatch)
    forbid_external_access(monkeypatch)
    bundle = builder.build(tmp_path, prepared.directory.name, 'verified')
    file = bundle / (table + '.parquet')
    frame = pl.read_parquet(file)
    if table == 'ita_county_assignments':
        changed = frame.with_columns(pl.lit(False).alias('flag_request_incomplete'))
        # This fixture has complete requests, so contradict recorded Census evidence instead.
        changed = changed.with_columns(pl.lit('No_Match').alias('geocode_status'))
    elif table == 'ita_area_mix':
        changed = frame.with_columns(pl.col('value').mul(0.5))
    elif table == 'county_denominators':
        changed = frame.reverse()
    else:
        changed = frame.with_columns(pl.col('n').add(1))
    changed.write_parquet(file)
    target_io.write_json(bundle / 'outputs.json',
                         target_io.inventory(bundle, list(builder.OUTPUT_NAMES)))
    with pytest.raises(ValueError):
        builder.verify_bundle(bundle, tmp_path)


def copy_execution_checkout(directory, monkeypatch):
    import importlib
    import shutil
    import subprocess

    from embedding_data import paths

    # Git exports repository-local context to hooks; isolate the fixture and provenance.
    local_names = subprocess.check_output(
        ['git', 'rev-parse', '--local-env-vars'], text=True).splitlines()
    for name in local_names:
        monkeypatch.delenv(name, raising=False)
    source_root = paths.PROJECT_ROOT
    shutil.copytree(source_root / 'src/embedding_data', directory / 'src/embedding_data',
                    ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('pyproject.toml', 'uv.lock'):
        shutil.copyfile(source_root / name, directory / name)
    for args in [('init', '-q'), ('add', '.'),
                 ('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                  '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'Fixture implementation')]:
        subprocess.run(['git', *args], cwd=directory, check=True, capture_output=True)
    modules = preparation.FROZEN_MODULES + preparation.TARGET_MODULES + ('geography_cli',)
    for name in modules:
        module = importlib.import_module('embedding_data.' + name)
        file = directory / 'src/embedding_data' / (name + '.py')
        monkeypatch.setattr(module, '__file__', str(file))
    monkeypatch.setattr(paths, 'PROJECT_ROOT', directory)
    return directory


def test_execution_checkout_isolates_hook_git_environment(tmp_path, monkeypatch):
    import os
    import subprocess

    outer = tmp_path / 'outer'
    outer.mkdir()
    local_names = subprocess.check_output(
        ['git', 'rev-parse', '--local-env-vars'], text=True).splitlines()
    clean_env = {key: value for key, value in os.environ.items() if key not in local_names}
    subprocess.run(['git', 'init', '-q', str(outer)], check=True, env=clean_env)
    monkeypatch.setenv('GIT_DIR', str(outer / '.git'))
    monkeypatch.setenv('GIT_INDEX_FILE', str(outer / '.git/index'))
    copied = copy_execution_checkout(tmp_path / 'execution', monkeypatch)
    assert (copied / '.git').is_dir()
    assert subprocess.check_output(
        ['git', 'config', '--get', 'core.bare'], cwd=outer, env=clean_env,
        text=True).strip() == 'false'
