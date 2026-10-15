import json

import polars as pl
import pytest

from embedding_data import target_io

def test_inventory_round_trip_retains_order(tmp_path):
    pl.DataFrame({'z': [1], 'a': ['001']}).write_parquet(tmp_path / 'rows.parquet')
    (tmp_path / 'requests').mkdir()
    (tmp_path / 'requests/batch_00000.csv').write_text('1,Street,City,AL,00001\n')
    names = ['requests/batch_00000.csv', 'rows.parquet']
    expected = target_io.inventory(tmp_path, names)
    target_io.write_json(tmp_path / 'outputs.json', expected)
    loaded = json.loads((tmp_path / 'outputs.json').read_text())
    target_io.verify_inventory(tmp_path, loaded, set(names))
    assert loaded['rows.parquet']['columns'] == ['z', 'a']
    loaded['rows.parquet']['columns'].reverse()
    with pytest.raises(ValueError):
        target_io.verify_inventory(tmp_path, loaded, set(names))


@pytest.mark.parametrize('name', ['', '../escape', '/absolute', 'a//b', 'a/../b'])
def test_unsafe_inventory_paths_fail(tmp_path, name):
    with pytest.raises(ValueError):
        target_io.inventory(tmp_path, [name])


@pytest.mark.parametrize('name', ['', '../escape', '/absolute', 'a.b', 'a/b'])
def test_unsafe_run_names_fail(tmp_path, name):
    with pytest.raises(ValueError):
        target_io.stage(tmp_path / 'runs', name, tmp_path)


def test_stage_exclusive_and_symlinks_fail(tmp_path):
    final, staging = target_io.stage(tmp_path / 'runs', 'safe_1', tmp_path)
    assert staging.is_dir() and not final.exists()
    with pytest.raises(ValueError):
        target_io.stage(tmp_path / 'runs', 'safe_1', tmp_path)
    (tmp_path / 'alias').symlink_to(tmp_path / 'runs', target_is_directory=True)
    with pytest.raises(ValueError):
        target_io.stage(tmp_path / 'alias', 'other', tmp_path)
    final.mkdir()
    with pytest.raises(ValueError):
        target_io.stage(tmp_path / 'runs', 'safe_1', tmp_path)


def test_inventory_rejects_symlink_and_extra_file(tmp_path):
    (tmp_path / 'a').write_text('a')
    expected = target_io.inventory(tmp_path, ['a'])
    (tmp_path / 'b').symlink_to(tmp_path / 'a')
    with pytest.raises(ValueError):
        target_io.inventory(tmp_path, ['b'])
    with pytest.raises(ValueError):
        target_io.verify_inventory(tmp_path, expected, {'a'})
