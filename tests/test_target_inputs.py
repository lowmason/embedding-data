import json
from datetime import UTC, datetime

import polars as pl
import pytest
from target_fixtures import seed_inputs

from embedding_data import ita_summary, manifest, paths
from embedding_data.target_inputs import select

def test_selected_inputs_verify_without_rebuilding(tmp_path, monkeypatch):
    selected = seed_inputs(tmp_path)
    before = selected.canonical.read_bytes()
    monkeypatch.setattr(ita_summary, 'build_summary_table',
                        lambda *a, **k: pytest.fail('production source rebuilt'))
    selected.verify(tmp_path)
    assert selected.canonical.read_bytes() == before
    assert len(pl.scan_parquet(selected.canonical).collect_schema()) == 38
    assert pl.scan_parquet(selected.canonical).select(pl.len()).collect().item() == 21
    raw = {r['path'] for r in selected.provenance['raw']}
    assert 'osha/summary/summary_data_dictionary.pdf' in raw
    assert 'osha/summary/ITA_Data_Dictionary.pdf' in raw


@pytest.mark.parametrize('defect', [
    'detached_hash', 'file_hash', 'size', 'missing_file', 'extra_file',
    'schema', 'row_count', 'raw_bytes', 'source_hash', 'source_order',
    'canonical_order', 'native_flags', 'native_node_level', 'geography_edge',
])
def test_selected_input_defects_are_refused(tmp_path, defect):
    from target_fixtures import corrupt_selected

    selected = seed_inputs(tmp_path)
    corrupt_selected(tmp_path, selected, defect)
    with pytest.raises((ValueError, FileNotFoundError)):
        selected.verify(tmp_path)


def test_fixture_checksums_required(tmp_path):
    seed_inputs(tmp_path)
    with pytest.raises(ValueError, match='checksum'):
        select(tmp_path, 'fixture_codes', 'fixture_geography')


def test_unrelated_manifest_append_is_allowed(tmp_path):
    selected = seed_inputs(tmp_path)
    file = tmp_path / 'raw/unrelated.txt'
    file.write_text('unrelated')
    entry = manifest.describe_file(file, tmp_path / 'raw',
                                  retrieved_at=datetime(2026, 10, 14, tzinfo=UTC),
                                  client='fixture', client_version='1')
    manifest.append_entries(paths.manifest_path(tmp_path), [entry])
    selected.verify(tmp_path)


def test_cited_entry_change_is_refused(tmp_path):
    selected = seed_inputs(tmp_path)
    file = paths.manifest_path(tmp_path)
    entries = [json.loads(line) for line in file.read_text().splitlines()]
    entries[0]['client'] = 'changed'
    file.write_text(''.join(json.dumps(entry) + '\n' for entry in entries))
    with pytest.raises(ValueError):
        selected.verify(tmp_path)


@pytest.mark.parametrize('change', [
    {'naics_mapping_status': 'concorded'},
    {'naics_2022_candidates': ['111111', '111111']},
    {'naics_2022_candidates': ['111112', '111111']},
    {'naics_year': None},
    {'naics_2022_node_id': None},
    {'flag_naics_unresolved': None},
])
def test_native_validator_rejects_inconsistent_all_year_rows(change):
    from code_fixtures import titles

    from embedding_data.classification_tables import naics_tables
    from embedding_data.target_inputs import CANONICAL_SCHEMA, validate_native

    nodes, _, _ = naics_tables(titles(2022, ('111111', '111112')), 2022)
    row = dict.fromkeys(CANONICAL_SCHEMA)
    row.update(year_filing_for=2025, naics_code='111111', naics_year=2022,
               naics_mapping_status='native_2022', naics_matching_vintages=[2022],
               naics_2022_candidates=['111111'], naics_2022_code='111111',
               naics_2022_node_id='naics:2022:national_industry:111111',
               flag_naics_crosswalked=False, flag_naics_ambiguous=False,
               flag_naics_unresolved=False)
    validate_native(pl.DataFrame([row], schema=CANONICAL_SCHEMA).lazy(), nodes)
    row.update(change)
    with pytest.raises(ValueError):
        validate_native(pl.DataFrame([row], schema=CANONICAL_SCHEMA).lazy(), nodes)
