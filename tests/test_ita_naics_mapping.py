import polars as pl
import pytest
from code_fixtures import pair_sheet, titles, toy_reference_tables
from hypothesis import given
from hypothesis import strategies as st
from polars.testing import assert_frame_equal

from embedding_data import ita_naics_mapping as mapping
from embedding_data.classification_tables import naics_tables
from embedding_data.naics_relationships import parse_concordance

@pytest.fixture
def references():
    return toy_reference_tables()


def keys(rows):
    return pl.DataFrame(
        rows, schema={'naics_code': pl.String, 'naics_year': pl.Int64}, orient='row'
    )


def test_states_provenance_and_canonical_outputs(references):
    source = keys(
        [
            (None, 2012),
            (None, None),
            ('111111', 2022),
            ('111112', 2012),
            ('111113', 2012),
            ('111113', None),
            ('999999', None),
            ('111111', None),
        ]
    )
    out = mapping.build_lookup(source, *references)
    rows = {(r['naics_code'], r['naics_year']): r for r in out.to_dicts()}
    assert rows[(None, 2012)]['naics_mapping_status'] == 'missing_code'
    assert rows[(None, None)]['flag_naics_unresolved'] is False
    assert rows[('111111', 2022)]['naics_mapping_status'] == 'native_2022'
    assert rows[('111111', 2022)]['naics_2022_code'] == '111111'
    assert rows[('111112', 2012)]['naics_mapping_status'] == 'concorded'
    assert rows[('111112', 2012)]['naics_2022_candidates'] == ['111112', '111113']
    assert rows[('111112', 2012)]['flag_naics_crosswalked'] is True
    assert rows[('111112', 2012)]['flag_naics_ambiguous'] is True
    assert rows[('111113', 2012)]['naics_mapping_status'] == 'invalid_native_code'
    assert rows[('111113', 2012)]['naics_matching_vintages'] == [2022]
    unknown = rows[('111113', None)]
    assert unknown['naics_mapping_status'] == 'unknown_vintage_candidates'
    assert unknown['naics_2022_candidates'] == ['111113']
    assert unknown['naics_2022_code'] is None
    assert unknown['naics_2022_node_id'] is None
    assert unknown['flag_naics_unresolved'] is True
    assert rows[('999999', None)]['naics_mapping_status'] == 'unknown_vintage_unmapped'
    assert rows[('111111', None)]['naics_matching_vintages'] == [2012, 2017, 2022]
    assert rows[('111111', None)]['naics_2022_candidates'] == ['111111', '111112', '111113']
    assert out.schema == mapping.LOOKUP_SCHEMA
    for name in [
        'naics_matching_vintages',
        'naics_2022_candidates',
        'flag_naics_crosswalked',
        'flag_naics_ambiguous',
        'flag_naics_unresolved',
    ]:
        assert out[name].null_count() == 0
    assert rows[('111112', 2012)]['naics_deepest_common_node_id'] == 'naics:2022:industry:11111'


@pytest.mark.parametrize(
    'code,year',
    [('11111', 2012), ('１１１１１１', 2012), ('ABCDEF', 2012), ('111111', 2025), (None, 2007)],
)
def test_bad_source_keys_fail(references, code, year):
    with pytest.raises(ValueError):
        mapping.build_lookup(keys([(code, year)]), *references)


def recode_references(cross_sector=False):
    native = []
    bridges = []
    for vintage in (2002, 2007, 2012, 2017, 2022):
        raw = titles(vintage, ('111111',))
        if vintage == 2022:
            raw = titles(vintage, ('111112',))
            if cross_sector:
                raw = pl.concat(
                    [
                        raw,
                        pl.DataFrame(
                            {
                                'vintage': [vintage] * 5,
                                'code': ['21', '211', '2111', '21111', '211111'],
                                'title': ['Fixture'] * 5,
                            },
                            schema=raw.schema,
                        ),
                    ]
                )
        nodes, _, paths = naics_tables(raw, vintage)
        native.append(nodes)
        if vintage == 2022:
            canonical_paths = paths
    for a, b in zip((2002, 2007, 2012, 2017), (2007, 2012, 2017, 2022)):
        pairs = [('111111', '111112' if b == 2022 else '111111')]
        if b == 2022 and cross_sector:
            pairs.append(('111111', '211111'))
        bridges.append(parse_concordance(pair_sheet(a, b, pairs), a, b, f'{a}_{b}.xlsx'))
    return pl.concat(native), pl.concat(bridges), canonical_paths


def test_singleton_historical_recode():
    row = mapping.build_lookup(keys([('111111', 2012)]), *recode_references()).row(0, named=True)
    assert row['naics_2022_code'] == '111112'
    assert row['naics_2022_node_id'] == 'naics:2022:national_industry:111112'
    assert row['flag_naics_crosswalked'] is True
    assert row['flag_naics_unresolved'] is False


def test_cross_sector_candidates_have_no_common_ancestor():
    row = mapping.build_lookup(keys([('111111', 2017)]), *recode_references(True)).row(
        0, named=True
    )
    assert row['naics_2022_candidates'] == ['111112', '211111']
    assert row['naics_deepest_common_node_id'] is None


@pytest.mark.parametrize('corruption', ['missing_path', 'missing_node', 'missing_bridge'])
def test_corrupt_reference_is_build_error(references, corruption):
    structures, relations, paths = references
    if corruption == 'missing_path':
        paths = paths.filter(pl.col('node_id').ne('naics:2022:national_industry:111113'))
    elif corruption == 'missing_node':
        structures = structures.filter(pl.col('node_id').ne('naics:2022:national_industry:111113'))
    else:
        relations = relations.filter(pl.col('target_code').ne('111113'))
    with pytest.raises(ValueError):
        mapping.build_lookup(keys([('111113', None)]), structures, relations, paths)


def test_duplicate_and_incompatible_keys(references):
    with pytest.raises(ValueError):
        mapping.build_lookup(keys([('111111', 2012)] * 2), *references)
    with pytest.raises(ValueError):
        mapping.build_lookup(
            keys([('111111', 2012)]).with_columns(pl.col('naics_year').cast(pl.Int32)), *references
        )


@given(st.permutations(range(6)))
def test_enrichment_preserves_current_order_and_multiplicity(order):
    source = keys(
        [
            ('111111', 2012),
            ('111111', 2012),
            ('111113', None),
            (None, None),
            ('999999', None),
            ('111111', 2022),
        ]
    )
    source = source.with_columns(pl.Series('flag_source', [True, True, False, None, True, False]))
    source = source[list(order)]
    lookup = mapping.build_lookup(
        source.select('naics_code', 'naics_year').unique(), *toy_reference_tables()
    )
    enriched = mapping.enrich(source.lazy(), lookup).collect()
    assert_frame_equal(enriched.select(source.columns), source)
    assert enriched.columns == [*source.columns, *mapping.MAPPING_SCHEMA]
    assert enriched['naics_mapping_status'].null_count() == 0


@pytest.mark.parametrize('problem', ['duplicate', 'conflict', 'unmatched', 'temporary', 'output'])
def test_bad_join_inputs_fail(references, problem):
    source = keys([('111111', 2012)])
    lookup = mapping.build_lookup(source, *references)
    if problem == 'duplicate':
        lookup = pl.concat([lookup, lookup])
    elif problem == 'conflict':
        lookup = pl.concat(
            [lookup, lookup.with_columns(naics_mapping_status=pl.lit('missing_code'))]
        )
    elif problem == 'unmatched':
        lookup = lookup.clear()
    else:
        name = '_code_row' if problem == 'temporary' else 'naics_2022_code'
        source = source.with_columns(pl.lit('collision').alias(name))
    with pytest.raises(ValueError):
        mapping.enrich(source.lazy(), lookup)


def test_empty_keys_and_source(references):
    lookup = mapping.build_lookup(keys([]), *references)
    assert lookup.schema == mapping.LOOKUP_SCHEMA
    assert mapping.enrich(keys([]).lazy(), lookup).collect().is_empty()
