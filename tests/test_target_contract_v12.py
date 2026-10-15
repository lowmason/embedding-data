import importlib
import json
from pathlib import Path

import polars as pl
from target_fixtures import run_ita_v12

from embedding_data import ita_assignment_prepare as preparation
from embedding_data.ita_target_build import verify_bundle

def test_ita_raw_to_target_contract_offline(tmp_path, monkeypatch):
    modules = preparation.FROZEN_MODULES + preparation.TARGET_MODULES
    assert len(preparation.module_hashes(modules)) == len(set(modules))
    assert all(Path(importlib.import_module('embedding_data.' + name).__file__).is_file()
               for name in modules)
    bundle = run_ita_v12(tmp_path, monkeypatch)
    report = verify_bundle(bundle, tmp_path)
    assert report['input_rows'] == 21
    assert report['selected_year_partition'] == {
        'source': 12, 'unassigned_geography': 3,
        'assigned_excluded_industry': 4, 'eligible': 5}
    assert pl.read_parquet(bundle / 'ita_area_mix.parquet').height == 3
    inputs = json.loads((bundle / 'inputs.json').read_text())
    raw = inputs['raw']
    assert raw == sorted(raw, key=lambda item: item['path'])
    assert len({item['path'] for item in raw}) == len(raw)
    assert sum('summary/' in item['path'] and item['path'].endswith(('.csv', '.zip'))
               for item in raw) == 10
    assert sum(item['path'].endswith('Dictionary.pdf') or
               item['path'].endswith('dictionary.pdf') for item in raw) == 2
    source = pl.read_parquet(tmp_path / inputs['canonical']['path'])
    raw_names = {item['path'] for item in raw}
    assert set(source['source_file'].unique().to_list()) <= raw_names
    selected_names = set(source.filter(pl.col('year_filing_for').eq(2023))
                         ['source_file'].unique().to_list())
    assert {item['path'] for item in inputs['target_source_files']} == selected_names
    assert inputs['acquisition']['start'] in raw
    assert inputs['acquisition']['completion'] in raw
    assert inputs['acquisition']['options']['benchmark_id'] == '7'
    assert {'targets_cli', 'cli'} <= inputs['software']['implementation'].keys()
    frame = pl.read_parquet(bundle / 'ita_county_assignments.parquet')
    assert frame.select(source.columns).equals(source)
    assert frame['source_row'].to_list() == list(range(21))
    assert frame.filter(pl.col('year_filing_for').eq(2023))['id'].to_list()[:2] == [23001, 23001]
