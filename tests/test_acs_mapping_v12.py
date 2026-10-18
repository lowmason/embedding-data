'''Authenticated raw conversion, upstream selection and offline mapping replay.'''

import json
from pathlib import Path

import polars as pl
from acs_mapping_fixtures import run_acs_mapping_v12

def test_complete_raw_to_mapping_bundle_and_replay(tmp_path, monkeypatch):
    from embedding_data.acs_mapping_bundle import compare_runs, verify_bundle

    runs = run_acs_mapping_v12(tmp_path / 'mapping-data', monkeypatch)
    assert all(isinstance(value, Path) for value in runs.values())
    source = pl.read_parquet(next(runs['data_dir'].glob('derived/acs/core/*.parquet')))
    assert source.unique().height < source.height
    result = compare_runs(runs['first'], runs['replay'])
    assert result['equal'] is True
    assert set(result['tables']) == {
        'acs_code_lookup', 'acs_area_lookup', 'puma_county_factors',
        'puma_msa_factors', 'puma_msa_coverage', 'acs_core_canonical',
        'acs_five_year_canonical', 'acs_vintage_canonical'}
    assert all(item['values_equal'] for item in result['tables'].values())
    assert result['substantive_report_equal'] is True
    for name in ('first', 'replay'):
        pin = json.loads(runs[name + '_control'].read_text())['outputs_sha256']
        verified = verify_bundle(runs[name], runs['data_dir'], expected_outputs_sha256=pin)
        assert verified['status'] == 'verified'
