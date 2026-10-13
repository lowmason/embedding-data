from datetime import date
from pathlib import Path

import polars as pl
import pytest
from code_fixtures import toy_reference_tables

from embedding_data import filing_rules as fr

@pytest.fixture
def filing_fixture():
    structures, relations, paths = toy_reference_tables()
    listed = {
        'designated_2012': ['111111'],
        'designated_2017': ['111112'],
        'partially_exempt_2007': ['111112'],
    }
    tables = fr.rule_tables(listed, structures, relations, {k: f'{k}.htm' for k in listed})
    return structures, relations, tables['membership']


def test_final_appendix_a_is_bounded_before_b():
    html = """<html><pre>Discussion of Appendix A to Subpart E of Part 1904
9999........... Preamble example
Appendix A to Subpart E of Part 1904--Designated Industries
NAICS Industry
11............. Fixture agriculture
31-33.......... Fixture manufacturing
Appendix B to Subpart E of Part 1904--Other Submission
9999........... Must not enter Appendix A
</pre></html>"""
    assert fr.parse_rule(html, 'designated_2017', expected_count=2) == ['11', '31-33']
    with pytest.raises(ValueError, match='count'):
        fr.parse_rule(html, 'designated_2017')


@pytest.mark.parametrize(
    'html',
    [
        '<html><title>Request Access</title></html>',
        '<html><pre>Appendix A to Subpart E of Part 1904\n11...... A\n11...... B</pre></html>',
    ],
)
def test_challenge_or_duplicate_list_refused(html):
    with pytest.raises(ValueError):
        fr.parse_rule(html, 'designated_2012', expected_count=2)


def test_bounded_bridge_preserves_mixed_predecessors_and_whole_exemptions():
    predecessors = {
        '517110': {'517110', '517510', '518111'},
        '517911': {'517310'},
        '517919': {'518111', '517910'},
        '519130': {'518112', '519110'},
        '541110': {'541110'},
    }
    bits = fr.legacy_membership(
        {'517911', '517919', '519130'}, {'517310', '518111', '518112'}, predecessors
    )
    assert bits['517110'] == ([False, True], True)
    assert bits['517911'] == ([True], True)
    assert bits['517919'] == ([True], True)
    assert bits['519130'] == ([True], True)
    assert bits['541110'] == ([False], False)
    with pytest.raises(ValueError, match='predecessor'):
        fr.legacy_membership(set(), {'518111'}, {'517110': set()})



FIXTURES = Path(__file__).parent / 'fixtures' / 'codes'


def test_original_format_page_break_and_appendix_boundary():
    html = (FIXTURES / 'filing_2023_excerpt.htm').read_text()
    assert fr.parse_rule(html, 'designated_2017', expected_count=2) == ['11', '31-33']


@pytest.mark.parametrize('row', ['11......', '11X...... Broken', '１１...... Broken'])
def test_malformed_original_rows_fail(row):
    html = f'<pre>Appendix A to Subpart E of Part 1904\n{row}\n</pre>'
    with pytest.raises(ValueError, match='row'):
        fr.parse_rule(html, 'designated_2017', expected_count=1)


def test_missing_row_count_fails():
    with pytest.raises(ValueError, match='count'):
        fr.parse_rule(
            '<pre>Appendix A to Subpart B of Part 1904\n11...... A</pre>',
            'partially_exempt_2007',
            expected_count=2,
        )


def test_native_expansion_overlap_and_dates():
    structures, _, _ = toy_reference_tables()
    table = fr.expand_rule(['11', '11111'], 'designated_2012', structures, 'rule.htm')
    assert table['code'].to_list() == ['111111', '111112']
    assert table.schema == fr.RULE_SCHEMA
    assert table['effective_from'].to_list() == [date(2017, 1, 1)] * 2
    assert table['effective_to'].to_list() == [date(2023, 12, 31)] * 2
    opened = fr.expand_rule(['11'], 'designated_2017', structures, 'rule.htm')
    assert opened['effective_from'].to_list() == [date(2024, 1, 1)] * 2
    assert opened['effective_to'].to_list() == [None, None]


@pytest.mark.parametrize('codes', [[], ['99'], ['11', '11'], ['5173']])
def test_strict_expansion_rejects_invalid_nodes(codes):
    structures, _, _ = toy_reference_tables()
    with pytest.raises(ValueError):
        fr.expand_rule(codes, 'partially_exempt_2007', structures, 'rule.htm')


def test_complete_membership_and_definite_projection(filing_fixture):
    structures, relations, membership = filing_fixture
    assert membership.schema == fr.MEMBERSHIP_SCHEMA
    assert membership.height == 6
    assert membership['membership_candidates'].to_list() == [
        [True],
        [False],
        [False],
        [True],
        [False],
        [True],
    ]
    listed = {
        'designated_2012': ['111111'],
        'designated_2017': ['111112'],
        'partially_exempt_2007': ['111112'],
    }
    tables = fr.rule_tables(listed, structures, relations, {k: 'rule.htm' for k in listed})
    assert tables['rules'].height == 3
    assert tables['labels'].schema == fr.LABEL_SCHEMA
    assert not tables['labels']['flag_rule_label_legacy'].any()
    fr.validate_membership(membership, structures)
    with pytest.raises(ValueError, match='coverage'):
        fr.validate_membership(membership.slice(1), structures)


def test_unknown_original_label_refused():
    structures, relations, _ = toy_reference_tables()
    with pytest.raises(ValueError):
        fr.rule_tables(
            {'partially_exempt_2007': ['5199']},
            structures,
            relations,
            {'partially_exempt_2007': 'rule.htm'},
        )


def test_legacy_labels_preserve_all_incoming_paths():
    from embedding_data.classification_tables import naics_tables

    structures, relations, _ = toy_reference_tables()
    old_codes = ['51', '517', '5173', '51731', '517310', '5174', '51741', '517410']
    old, _, _ = naics_tables(
        pl.DataFrame({'vintage': [2002] * len(old_codes), 'code': old_codes, 'title': old_codes}),
        2002,
    )
    structures = pl.concat([structures, old])
    bridge = pl.DataFrame(
        {
            'source_vintage': [2002] * 3,
            'target_vintage': [2007] * 3,
            'source_code': ['517310', '517410', '517310'],
            'target_code': ['111111', '111111', '111112'],
        }
    )
    listed = {
        'designated_2012': ['111111'],
        'designated_2017': ['111112'],
        'partially_exempt_2007': ['5173'],
    }
    tables = fr.rule_tables(listed, structures, bridge, {k: 'rule.htm' for k in listed})
    exemption = tables['membership'].filter(pl.col('rule_id').eq('partially_exempt_2007'))
    assert exemption['membership_candidates'].to_list() == [[False, True], [True]]
    assert exemption['flag_rule_label_bridged'].to_list() == [True, True]
    label = tables['labels'].filter(pl.col('listed_code').eq('5173')).row(0, named=True)
    assert label['label_vintage'] == 2002
    assert label['flag_rule_label_legacy'] is True
    assert tables['rules'].filter(pl.col('rule_id').eq('partially_exempt_2007'))[
        'code'
    ].to_list() == ['111112']
    with pytest.raises(ValueError, match='bridge'):
        fr.rule_tables(listed, structures, bridge.head(2), {k: 'rule.htm' for k in listed})
    listed['partially_exempt_2007'].append('11')
    overridden = fr.rule_tables(listed, structures, bridge, {k: 'rule.htm' for k in listed})
    assert overridden['membership'].filter(pl.col('rule_id').eq('partially_exempt_2007'))[
        'membership_candidates'
    ].to_list() == [[True], [True]]


@pytest.mark.parametrize('source', ['', '   '])
def test_membership_provenance_refused(filing_fixture, source):
    structures, _, membership = filing_fixture
    with pytest.raises(ValueError, match='provenance'):
        fr.validate_membership(
            membership.with_columns(pl.lit(source).alias('source_file')), structures
        )


@pytest.mark.parametrize('column,value', [
    ('vintage', 2022), ('effective_from', date(2020, 1, 1)),
    ('effective_to', date(2025, 1, 1)), ('code', '999999'),
    ('membership_candidates', []), ('membership_candidates', [True, False]),
    ('membership_candidates', [False, True]), ('flag_rule_label_bridged', None),
])
def test_invalid_membership_fields_refused(filing_fixture, column, value):
    structures, _, membership = filing_fixture
    changed = membership.with_columns(pl.lit(value, dtype=membership.schema[column]).alias(column))
    with pytest.raises(ValueError):
        fr.validate_membership(changed, structures)


def test_rule_tables_deterministic_under_input_order():
    structures, relations, _ = toy_reference_tables()
    listed = {'designated_2012': ['11', '11111'], 'designated_2017': ['111112'],
              'partially_exempt_2007': ['111112']}
    sources = {k: 'rule.htm' for k in listed}
    forward = fr.rule_tables(listed, structures, relations, sources)
    reverse = fr.rule_tables({k: list(reversed(v)) for k, v in reversed(list(listed.items()))},
                             structures.reverse(), relations.reverse(), sources)
    assert all(forward[k].equals(reverse[k]) for k in forward)


def test_missing_identity_and_duplicate_membership_refused(filing_fixture):
    structures, _, membership = filing_fixture
    with pytest.raises(ValueError, match='identity'):
        fr.validate_membership(
            membership.filter(pl.col('rule_id').ne('designated_2012')), structures
        )
    with pytest.raises(ValueError, match='duplicate'):
        fr.validate_membership(pl.concat([membership, membership.head(1)]), structures)


@pytest.mark.parametrize(
    'size,code,vintage,status,industry,overall',
    [
        (None, '111111', 2012, 'missing_size', None, None),
        (1, None, None, 'not_applicable_below_size', None, True),
        (2, None, 2012, 'missing_code', None, None),
        (2, '999999', 2012, 'invalid_native_code', None, None),
        (3, '999999', None, 'unknown_vintage_unmapped', None, None),
    ],
)
def test_filing_status_precedence(filing_fixture, size, code, vintage, status, industry, overall):
    structures, relations, rules = filing_fixture
    assert fr.evaluate(2022, code, vintage, size, structures, relations, rules) == {
        'filing_industry_status': status,
        'flag_outside_filing_industry': industry,
        'flag_outside_filing_rule': overall,
        'flag_filing_rule_label_bridged': False,
        'flag_filing_reference_ambiguous': False,
    }


@pytest.mark.parametrize(
    'size,status,outside',
    [
        (2, 'determinate', True),
        (3, 'candidate_disagreement', None),
    ],
)
def test_reference_ambiguity_can_survive_final_unanimity(filing_fixture, size, status, outside):
    structures, relations, membership = filing_fixture
    selected = pl.col('rule_id').eq('partially_exempt_2007').and_(pl.col('code').eq('111112'))
    membership = membership.with_columns(
        membership_candidates=pl.when(selected)
        .then(pl.lit([False, True], dtype=pl.List(pl.Boolean)))
        .otherwise(pl.col('membership_candidates')),
        flag_rule_label_bridged=selected,
    )
    result = fr.evaluate(2022, '111112', 2012, size, structures, relations, membership)
    assert result['filing_industry_status'] == status
    assert result['flag_outside_filing_industry'] is outside
    assert result['flag_filing_reference_ambiguous'] is True
    assert result['flag_filing_rule_label_bridged'] is True


@pytest.mark.parametrize(
    'size,code,vintage,outside',
    [
        (2, '111111', 2012, False),
        (2, '111112', 2012, True),
        (2, '111112', None, None),
        (3, '111111', 2012, False),
        (3, '111112', 2012, True),
        (2, '111112', 2017, None),
    ],
)
def test_candidate_unanimity(filing_fixture, size, code, vintage, outside):
    structures, relations, membership = filing_fixture
    result = fr.evaluate(2022, code, vintage, size, structures, relations, membership)
    assert result['flag_outside_filing_industry'] is outside
    assert result['filing_industry_status'] == (
        'candidate_disagreement' if outside is None else 'determinate'
    )


def test_large_size_only_traverses_exemption(filing_fixture):
    structures, relations, membership = filing_fixture
    relations = relations.filter(pl.col('source_vintage').ne(2012))
    assert (
        fr.evaluate(2023, '111111', 2012, 3, structures, relations, membership)[
            'flag_outside_filing_industry'
        ]
        is False
    )
    with pytest.raises(ValueError, match='bridge'):
        fr.evaluate(2023, '111111', 2012, 2, structures, relations, membership)


def test_boundary_years_use_nominal_submission_date(filing_fixture):
    structures, relations, membership = filing_fixture
    from code_fixtures import pair_sheet

    from embedding_data.naics_relationships import parse_concordance, validate_relationships

    identity = parse_concordance(pair_sheet(2012, 2017, [
        ('111111', '111111'), ('111112', '111112'),
    ]), 2012, 2017, 'identity.xlsx')
    relations = pl.concat([relations.filter(pl.col('source_vintage').ne(2012)), identity])
    validate_relationships(relations, structures)
    for year, outside in [(2022, False), (2023, True)]:
        assert (
            fr.evaluate(year, '111111', 2012, 2, structures, relations, membership)[
                'flag_outside_filing_industry'
            ]
            is outside
        )


@pytest.mark.parametrize(
    'year,code,vintage,size,match',
    [
        (None, '111111', 2012, 2, 'year'),
        (2022, '１１１１１１', 2012, 2, 'malformed'),
        (2022, '111111', 2007, 2, 'vintage'),
        (2022, '111111', 2012, 4, 'size'),
        (2010, '111111', 2012, 2, 'period'),
    ],
)
def test_evaluator_rejects_incompatible_inputs(filing_fixture, year, code, vintage, size, match):
    with pytest.raises(ValueError, match=match):
        fr.evaluate(year, code, vintage, size, *filing_fixture)


def test_correlated_unknown_vintages_and_join_preservation(filing_fixture):
    from code_fixtures import pair_sheet

    from embedding_data.naics_relationships import parse_concordance, validate_relationships

    structures, relations, membership = filing_fixture
    swapped = parse_concordance(
        pair_sheet(
            2012,
            2017,
            [
                ('111111', '111112'),
                ('111112', '111111'),
            ],
        ),
        2012,
        2017,
        'swap.xlsx',
    )
    relations = pl.concat([relations.filter(pl.col('source_vintage').ne(2012)), swapped])
    validate_relationships(relations, structures)
    membership = membership.with_columns(
        membership_candidates=pl.when(pl.col('rule_id').eq('partially_exempt_2007'))
        .then(pl.when(pl.col('code').eq('111111')).then(pl.lit([True])).otherwise(pl.lit([False])))
        .otherwise(pl.col('membership_candidates')),
    )
    keys = pl.DataFrame(
        [(2022, '111111', None, 2), (2022, None, None, None)], schema=fr.FILING_KEYS, orient='row'
    )
    lookup = fr.build_filing_lookup(keys, structures, relations, membership)
    assert lookup.schema == fr.FILING_LOOKUP_SCHEMA
    source = pl.concat([keys, keys.head(1)]).with_columns(
        annual_average_employees=pl.Series([25, 1000, 250]),
        flag_below_filing_size=False,
        flag_naics_year_unknown=True,
        flag_naics_mapping_unresolved=True,
    )
    result = fr.add_filing_flags(source.lazy(), lookup).collect()
    assert result.select(source.columns).equals(source)
    assert result.height == 3
    assert result['flag_outside_filing_rule'].to_list() == [True, None, True]
    assert result['filing_industry_status'].to_list() == [
        'determinate',
        'missing_size',
        'determinate',
    ]
    assert result['flag_outside_filing_rule'].dtype == pl.Boolean
    assert result['flag_filing_reference_ambiguous'].null_count() == 0
    assert result['flag_filing_rule_label_bridged'].null_count() == 0
    assert lookup.equals(fr.build_filing_lookup(keys.reverse(), structures, relations, membership))
    with pytest.raises(ValueError, match='duplicate'):
        fr.build_filing_lookup(pl.concat([keys, keys]), structures, relations, membership)
    with pytest.raises(ValueError, match='duplicate'):
        fr.add_filing_flags(source.lazy(), pl.concat([lookup, lookup]))
    with pytest.raises(ValueError, match='missing'):
        fr.add_filing_flags(source.lazy(), lookup.filter(pl.col('naics_code').is_null()))
    with pytest.raises(ValueError, match='collision'):
        fr.add_filing_flags(result.lazy(), lookup)
    with pytest.raises(ValueError, match='coverage'):
        fr.build_filing_lookup(keys, structures, relations, membership.slice(1))


def test_unknown_singleton_and_all_out_candidates(filing_fixture):
    structures, relations, membership = filing_fixture
    membership = membership.with_columns(
        membership_candidates=pl.when(pl.col('rule_id').eq('partially_exempt_2007'))
        .then(pl.lit([True]))
        .otherwise(pl.col('membership_candidates')),
    )
    for code, vintage in [('111113', None), ('111112', 2017)]:
        result = fr.evaluate(2022, code, vintage, 2, structures, relations, membership)
        assert result['filing_industry_status'] == 'determinate'
        assert result['flag_outside_filing_industry'] is True


def test_cartesian_candidate_possibilities_and_all_in(filing_fixture):
    structures, relations, membership = filing_fixture
    all_in = membership.with_columns(
        membership_candidates=pl.when(pl.col('rule_id').str.starts_with('designated_'))
        .then(pl.lit([True])).otherwise(pl.lit([False])),
    )
    assert fr.evaluate(2022, '111112', 2017, 2, structures, relations, all_in)[
        'flag_outside_filing_industry'
    ] is False
    # Reverse candidates are paired independently within this one native interpretation.
    assert fr.evaluate(2022, '111112', 2017, 2, structures, relations, membership)[
        'flag_outside_filing_industry'
    ] is None
