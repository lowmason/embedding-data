'''Raw summaries to two verified, replay-equal Stage 10 bundles, with external access blocked.

Fixture results show software readiness. They are never benchmarks.
'''

import json

import polars as pl
from ita_establishment_fixtures import FIXTURE_BASIS, run_establishment_v12

from embedding_data import ita_co_ownership, ita_references

NODE = 'naics:2022:national_industry:'
COMMAND_MODULE = 'src/embedding_data/ita_establishment_targets.py'


def test_ita_establishment_raw_to_target_offline(tmp_path, monkeypatch):
    result = run_establishment_v12(tmp_path, monkeypatch)
    for name in ('first', 'replay'):
        verified = result[name + '_verification']
        assert verified['outputs_sha256'] == result[name + '_pin']
        assert verified['reproduction'] == {'basis': FIXTURE_BASIS, 'source_records': 'equal',
                                            'v1': 'equal', 'v2': 'equal'}
    assert result['comparison']['equal'] is True
    assert result['comparison']['trust_established'] is False
    first = result['first']
    assert first.parent == result['replay'].parent
    assert first.is_relative_to(result['data_dir'])

    pairs = pl.read_parquet(first / 'ita_text_pairs.parquet')
    codes = pl.read_parquet(first / 'ita_text_pair_codes.parquet')

    def keys(condition):
        return set(pairs.filter(condition)['description_key'])

    assert 'soybean farming' in keys(pl.col('flag_copied_title_any'))
    assert 'wholesale -- see type of product' in keys(pl.col('flag_copied_index_any'))
    assert 'n/a' in keys(pl.col('flag_placeholder'))
    assert pairs.filter(pl.col('pair_kind').eq('unknown_employer')).height >= 1
    assert pairs.filter(pl.col('n_records_ein_padded').gt(0)).height >= 1
    headline = pairs.filter(pl.col('flag_headline')).select('pair_id')
    context = codes.join(headline, on='pair_id').filter(pl.col('flag_headline_basis').not_())
    assert context.height >= 1
    assert pairs.filter(pl.col('flag_headline_codes_conflict')).height >= 1

    targets = pl.read_parquet(first / 'ita_co_ownership.parquet')
    cell = targets.filter(pl.col('unit_a').eq(NODE + '238220'),
                          pl.col('unit_b').eq(NODE + '722511'))
    assert ita_co_ownership.PADDED_LABEL in cell['flags'].item()

    links = pl.read_parquet(first / 'ita_establishment_links.parquet')
    assert {'confirmed_same_id', 'confirmed_changed_id', 'conflict'} <= set(links['status'])

    inputs = json.loads((first / 'inputs.json').read_text())
    raw = {citation['path'] for citation in inputs['raw']}
    titles = {'references/naics/' + url.rsplit('/', 1)[1]
              for url in ita_references.TITLE_FILES.values()}
    indexes = {f'references/naics/{vintage}_fixture_index.xlsx' for vintage in (2012, 2017, 2022)}
    assert len(titles) == 3
    assert titles | indexes <= raw
    assert COMMAND_MODULE in inputs['software']['files']
