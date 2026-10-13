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
