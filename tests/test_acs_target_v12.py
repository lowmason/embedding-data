'''Genuine raw-chain software readiness with measured external-access guards.'''

import json

import polars as pl
import pytest

def test_counted_guards_intercept_every_seam(tmp_path, monkeypatch):
    from acs_target_fixtures import install_counted_guards

    counts = {'network': 0, 'environment_file': 0, 'live_client': 0}
    probes = install_counted_guards(monkeypatch, counts)
    for category, probe in probes:
        before = counts.copy()
        with pytest.raises(AssertionError, match='offline ACS targets'):
            probe()
        assert counts[category] == before[category] + 1
        assert all(counts[key] == before[key] for key in counts if key != category)
    assert all(value > 0 for value in counts.values())
    from embedding_data import geography_references

    before = counts['live_client']
    with pytest.raises(AssertionError, match='offline ACS targets'):
        geography_references.make_client()
    assert counts['live_client'] == before + 1


def test_raw_to_all_four_acs_families_is_offline_and_replayable(tmp_path, monkeypatch):
    from acs_target_fixtures import run_acs_target_v12

    from embedding_data import acs_target_bundle as bundle

    result = run_acs_target_v12(tmp_path / 'data', monkeypatch)
    targets = pl.read_parquet(result['first'] / 'targets_observed.parquet')
    assert set(targets['family']) == {
        'staffing_pattern', 'area_mix', 'commuting_flow', 'migration_flow'}
    canonical = pl.read_parquet(result['first'] / 'targets_canonical.parquet')
    assert 'naics:2022:national_industry:811192' in set(canonical['unit_b']) | set(
        canonical['unit_a'])
    assert 'soc:2018:detailed:11-1021' in set(canonical['unit_b'])
    assert result['external_access_counts'] == {
        'network': 0, 'environment_file': 0, 'live_client': 0}
    for name in ('first', 'replay'):
        control = json.loads(result[name + '_control'].read_text())
        assert result[name + '_verification']['status'] == 'verified'
        assert result[name + '_verification']['outputs_sha256'] == control['outputs_sha256']
    compared = bundle.compare_runs(
        result['first'], result['replay'], data_dir=result['data_dir'],
        mapping_run=result['mapping_run'], expected_mapping_outputs_sha256=result['mapping_pin'])
    assert compared['equal'] is True
    assert result['external_access_counts'] == {
        'network': 0, 'environment_file': 0, 'live_client': 0}
    source = pl.read_parquet(result['data_dir'] / 'derived/acs/core/usa_1.parquet')
    assert source.schema['QMIGRAT1'] == pl.Int64
    assert source.filter(pl.col('YEAR') == 2023)['QMIGRAT1'].null_count() > 0
    assert set(source.filter(pl.col('YEAR') == 2024)['QMIGRAT1']) == {0, 4}


def test_shared_contract_extension_preserves_independent_ita_chain(tmp_path, monkeypatch):
    from target_fixtures import run_ita_v12

    from embedding_data.ita_target_build import verify_bundle

    data_dir = tmp_path / 'ita-data'
    directory = run_ita_v12(data_dir, monkeypatch)
    assert verify_bundle(directory, data_dir)['input_rows'] == 21


@pytest.mark.parametrize('value,status', [(None, 'unavailable'), ('0', 'nonallocation'),
                                        ('4', 'allocated')])
def test_production_string_migration_evidence_preserves_raw_diagnostics(value, status):
    from acs_target_fixtures import membership_frame, membership_rules, membership_units

    from embedding_data.acs_target_contract import PRODUCTS
    from embedding_data.acs_target_membership import family_rows

    year = 2023 if value is None else 2024
    frame = membership_frame([{'QMIGRAT1': value, 'acs_component_year': year,
                              'acs_sample_id': f'us{year}a'}])
    product = next(p for p in PRODUCTS if p.view == 'observed'
        and p.family == 'migration_flow' and p.evidence_policy == 'sensitivity'
        and p.years == (2023, 2024) and p.base_universe == 'civilian_employed')
    rows = family_rows(frame, product, membership_rules(), membership_units())
    assert rows.members.collect().height == 1
    diagnostics = rows.diagnostics.collect().filter(
        (pl.col('partition_kind') == 'evidence') & (pl.col('variable') == 'QMIGRAT1'))
    assert diagnostics.select('raw_dtype', 'raw_value', 'evidence_status').rows() == [
        ('String', value, status)]
