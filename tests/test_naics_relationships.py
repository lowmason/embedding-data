import polars as pl
import pytest
from code_fixtures import pair_sheet

from embedding_data import naics_relationships as nr

def test_split_merge_degrees_and_reverse_candidates():
    pairs = [('111111', '111111'), ('111111', '111112'), ('111112', '111112')]
    out = nr.parse_concordance(pair_sheet(2012, 2017, pairs), 2012, 2017, 'fixture.xls')
    assert out['link_type'].to_list() == ['1:m', 'm:m', 'm:1']
    assert nr.candidates(out, 2012, '111111', 2017) == ['111111', '111112']
    assert nr.candidates(out, 2017, '111112', 2012) == ['111111', '111112']


def test_two_hops_and_equal_codes_do_not_shortcut():
    a = nr.parse_concordance(pair_sheet(2012, 2017, [('111111', '111111')]), 2012, 2017, 'a.xls')
    b = nr.parse_concordance(
        pair_sheet(2017, 2022, [('111111', '111111'), ('111111', '111112')]), 2017, 2022, 'b.xls'
    )
    assert nr.candidates(pl.concat([a, b]), 2012, '111111', 2022) == ['111111', '111112']
    with pytest.raises(ValueError, match='bridge'):
        nr.candidates(a, 2012, '111111', 2022)


def test_full_reshuffle_recode_and_duplicates():
    pairs = [
        ('111111', '111111'),
        ('111111', '111112'),
        ('111112', '111111'),
        ('111112', '111112'),
    ]
    out = nr.parse_concordance(pair_sheet(2012, 2017, pairs + pairs), 2012, 2017, 'x.xls')
    assert out.height == 4
    assert out['link_type'].to_list() == ['m:m'] * 4
    assert out.equals(
        nr.parse_concordance(pair_sheet(2012, 2017, pairs[::-1]), 2012, 2017, 'x.xls')
    )
    recode = nr.parse_concordance(
        pair_sheet(2017, 2022, [('111111', '111112')]), 2017, 2022, 'x.xls'
    )
    assert recode['link_type'].to_list() == ['1:1']
    assert nr.candidates(recode, 2022, '111112', 2017) == ['111111']


def test_complete_chain_and_monotonic_reverse_traversal():
    from code_fixtures import toy_reference_tables

    structures, relations, paths = toy_reference_tables()
    nr.validate_relationships(relations, structures)
    assert nr.candidates(relations, 2002, '111111', 2022) == ['111111', '111112', '111113']
    assert nr.candidates(relations, 2022, '111113', 2002) == ['111111', '111112']
    assert nr.candidates(relations, 2012, '111111', 2012) == ['111111']
    assert nr.candidates(relations, 2012, '111112', 2017) == ['111112']
    assert paths.height > 0


@pytest.mark.parametrize('code', [None, '', '11111', 'abcdef', '１１１１１１'])
def test_rejects_incomplete_or_invalid_endpoints(code):
    with pytest.raises(ValueError, match='endpoint'):
        nr.parse_concordance(pair_sheet(2012, 2017, [(code, '111111')]), 2012, 2017, 'x.xls')


@pytest.mark.parametrize('side', ['source_code', 'target_code'])
def test_rejects_unknown_endpoint_and_incomplete_coverage(side):
    from code_fixtures import toy_reference_tables

    structures, relations, _ = toy_reference_tables()
    bad = relations.with_columns(
        pl.when(pl.int_range(pl.len()).eq(0))
        .then(pl.lit('999999'))
        .otherwise(pl.col(side))
        .alias(side)
    )
    with pytest.raises(ValueError, match='endpoint|coverage'):
        nr.validate_relationships(bad, structures)
    incomplete = relations.filter(~(pl.col('source_vintage').eq(2002) & pl.col(side).eq('111112')))
    with pytest.raises(ValueError, match='coverage'):
        nr.validate_relationships(incomplete, structures)


def test_rejects_corrupted_degree_classification():
    from code_fixtures import toy_reference_tables

    structures, relations, _ = toy_reference_tables()
    bad = relations.with_columns(
        pl.when(pl.col('link_type').eq('1:m'))
        .then(pl.lit('1:1'))
        .otherwise(pl.col('link_type'))
        .alias('link_type')
    )
    with pytest.raises(ValueError, match='degree'):
        nr.validate_relationships(bad, structures)


@pytest.mark.parametrize(
    'corruption,match',
    [
        ('duplicate', 'duplicate'),
        ('bridge', 'bridge'),
        ('null', 'null'),
        ('provenance', 'provenance'),
        ('schema', 'schema'),
    ],
)
def test_rejects_corrupt_relationship_table(corruption, match):
    from code_fixtures import toy_reference_tables

    structures, relations, _ = toy_reference_tables()
    if corruption == 'duplicate':
        relations = pl.concat([relations, relations.head(1)])
    elif corruption == 'bridge':
        relations = relations.filter(pl.col('source_vintage').ne(2002))
    elif corruption == 'null':
        relations = relations.with_columns(source_file=pl.lit(None, dtype=pl.String))
    elif corruption == 'provenance':
        relations = relations.with_columns(source_file=pl.lit(' '))
    else:
        relations = relations.with_columns(source_vintage=pl.col('source_vintage').cast(pl.Int32))
    with pytest.raises(ValueError, match=match):
        nr.validate_relationships(relations, structures)


def test_rejects_unsupported_vintage():
    with pytest.raises(ValueError, match='vintage'):
        nr.candidates(pl.DataFrame(), 1997, '111111', 2022)
