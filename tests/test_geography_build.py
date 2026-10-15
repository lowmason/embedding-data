import json

import polars as pl
import pytest
from geography_fixtures import seed_geography_tree
from polars.testing import assert_frame_equal

from embedding_data import geography_build as gb
from embedding_data import geography_references as gr
from embedding_data import manifest

def test_full_bundle_exact_inventory_and_repeatability(tmp_path):
    registry = seed_geography_tree(tmp_path)
    one = gb.build(tmp_path, 'fixture_one', registry=registry)
    original_hashes = {f.name: manifest.sha256_file(f) for f in one.iterdir()}
    two = gb.build(tmp_path, 'fixture_two', registry=registry)
    assert {f.name: manifest.sha256_file(f) for f in one.iterdir()} == original_hashes
    expected = {name + '.parquet' for name in gb.SCHEMAS} | {'inputs.json', 'report.json'}
    assert {f.name for f in one.iterdir()} == expected | {'outputs.json'}
    inventory = json.loads((one / 'outputs.json').read_text())
    assert set(inventory) == expected
    for name, entry in inventory.items():
        assert entry == {'sha256': manifest.sha256_file(one / name),
                         'size': (one / name).stat().st_size}
    for name, schema in gb.SCHEMAS.items():
        a = pl.read_parquet(one / (name + '.parquet'))
        b = pl.read_parquet(two / (name + '.parquet'))
        assert a.schema == schema
        assert_frame_equal(a, b)
    inputs = json.loads((one / 'inputs.json').read_text())
    assert inputs['fixture'] is True
    assert inputs['schema_version'] == 'geography-v1'
    assert len(inputs['raw']) == 4
    assert 'src/embedding_data/geography_cli.py' in inputs['implementation']
    assert set(inputs['reference_frames']) == {'administrative', 'omb', 'hud'}
    report = json.loads((one / 'report.json').read_text())
    assert report['non_cbsa_counties'] == 1
    assert report['multi_state_cbsas'] == 1
    assert report['tables']['hud_zip_county.parquet']['rows'] == 12
    assert report['tables']['hud_zip_lookup.parquet']['rows'] == 9
    assert report['source_scope_exclusions']['county_rows'] == 1
    assert report['source_scope_exclusions']['membership_rows'] == 1


@pytest.mark.parametrize('run_id', ['../escape', 'bad/name', '', '.hidden', 'unicode_é'])
def test_unsafe_run_id_fails_before_build(tmp_path, run_id):
    with pytest.raises(ValueError, match='run ID'):
        gb.build(tmp_path, run_id)


@pytest.mark.parametrize('suffix', ['', '.part'])
def test_occupied_name_preserves_existing_bytes(tmp_path, suffix):
    registry = seed_geography_tree(tmp_path)
    occupied = tmp_path / 'derived/geography' / ('occupied' + suffix)
    occupied.mkdir(parents=True)
    (occupied / 'keep').write_bytes(b'unchanged')
    with pytest.raises(ValueError):
        gb.build(tmp_path, 'occupied', registry=registry)
    assert (occupied / 'keep').read_bytes() == b'unchanged'


def test_missing_input_never_acquires(tmp_path, monkeypatch):
    registry = seed_geography_tree(tmp_path)
    gr.reference_path(tmp_path, registry['cbsa_2023']).unlink()
    monkeypatch.setattr(gr, 'acquire', lambda *a, **k: pytest.fail('offline build acquired'))
    with pytest.raises((ValueError, FileNotFoundError)):
        gb.build(tmp_path, 'missing', registry=registry)
    assert not (tmp_path / 'derived/geography/missing').exists()


@pytest.mark.parametrize('defect', ['original', 'destination'])
def test_final_integrity_check_refuses_mid_build_changes(tmp_path, monkeypatch, defect):
    registry = seed_geography_tree(tmp_path)
    final = tmp_path / 'derived/geography/changed'
    write = gb.write_json

    def mutate(file, payload):
        write(file, payload)
        if file.name == 'outputs.json':
            if defect == 'original':
                gr.reference_path(tmp_path, registry['cbsa_2023']).write_bytes(b'changed')
            else:
                final.mkdir()
                (final / 'competitor').write_bytes(b'preserve')

    monkeypatch.setattr(gb, 'write_json', mutate)
    with pytest.raises(ValueError):
        gb.build(tmp_path, 'changed', registry=registry)
    assert not (final / 'geography_nodes.parquet').exists()
    assert (tmp_path / 'derived/geography/changed.part').exists()
    if defect == 'destination':
        assert (final / 'competitor').read_bytes() == b'preserve'
