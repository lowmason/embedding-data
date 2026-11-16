import dataclasses
import json
import random
import re
import subprocess
import sys

import polars as pl
import pytest
from ita_establishment_fixtures import canonical_frame, naics_reference

from embedding_data import ita_establishment_links
from embedding_data.ita_establishment_expected import V2_COLUMNS, YEAR_PAIRS
from embedding_data.ita_establishment_links import (
    LINK_SCHEMA,
    LINKS_VERSION,
    REASONS,
    STATUSES,
    Links,
    build_links,
    distinct_records,
    validate_links,
)
from embedding_data.ita_establishment_records import SOURCE_COLUMNS, keyed_records, text_keys
from embedding_data.ita_index_references import INDEX_SCHEMA
from embedding_data.ita_text_pairs import build_pairs
from embedding_data.ita_verification import link_report

TITLES = pl.DataFrame(
    [(2022, '332312', 'Fabricated Structural Metal Manufacturing')],
    schema={'vintage': pl.Int64, 'code': pl.String, 'title': pl.String},
    orient='row',
)
INDEX = pl.DataFrame([(2022, '332312', 'Steel mill')], schema=INDEX_SCHEMA, orient='row')
KEYS = text_keys(TITLES, INDEX)
PAIR = (2023, 2024)


def rec(year, establishment_id, tag, **overrides):
    '''One canonical record whose name and street carry the tag, so two tags never share a
    tuple.'''
    return {
        'year_filing_for': year,
        'establishment_id': establishment_id,
        'establishment_name': f'Plant {tag}',
        'street_address': f'{tag} Main St',
        **overrides,
    }


class Rows:
    '''Records in source-row order. `add` returns the source row of the new record.'''

    def __init__(self):
        self.rows = []

    def add(self, *args, **overrides):
        self.rows.append(rec(*args, **overrides))
        return len(self.rows) - 1


def keyed(rows):
    return keyed_records(canonical_frame(rows), KEYS)


def build(rows):
    return build_links(keyed(rows))


def pair_rows(result, pair=PAIR):
    '''The link rows of one year pair, by base row.'''
    frame = result.links.collect().filter(
        pl.col('base_year').eq(pair[0]).and_(pl.col('later_year').eq(pair[1]))
    )
    return {row['base_row']: row for row in frame.to_dicts()}


def true_reasons(row):
    return {reason for reason in REASONS if row[reason]}


def v2_row(result, pair=PAIR):
    frame = result.v2.filter(
        pl.col('base_year').eq(pair[0]).and_(pl.col('later_year').eq(pair[1])))
    assert frame.height == 1
    return frame.select(V2_COLUMNS).row(0, named=True)


def stage3(rows, pair=PAIR):
    report = link_report(canonical_frame(rows).select(SOURCE_COLUMNS), *pair)
    return {column: report[column] for column in V2_COLUMNS}


def message(text):
    return '^' + re.escape(text) + '$'


# Base 2023 and later 2024 records with every shape the V2 table distinguishes.
ORACLE = Rows()
ORACLE.add(2023, 1, 'same', ein='100000001')
ORACLE.add(2024, 1, 'same', ein='100000001')
ORACLE.add(2023, 2, 'duplicate', ein='100000002', id=900)
ORACLE.add(2023, 2, 'duplicate', ein='100000002', id=900)
ORACLE.add(2024, 2, 'duplicate', ein='100000002', id=901)
ORACLE.add(2024, 2, 'duplicate', ein='100000002', id=901)
ORACLE.add(2023, None, 'null-base', ein='100000003', id=902)
ORACLE.add(2023, None, 'null-base', ein='100000003', id=902)
ORACLE.add(2024, None, 'null-later-a', ein='100000003')
ORACLE.add(2024, None, 'null-later-b', id=903)
ORACLE.add(2024, None, 'null-later-b', id=903)
ORACLE.add(2024, None, 'null-later-c')
ORACLE.add(2023, 4, 'competing-base-a', ein='100000004')
ORACLE.add(2023, 4, 'competing-base-b', ein='100000004')
ORACLE.add(2024, 4, 'competing-base-a', ein='100000004')
ORACLE.add(2023, 5, 'competing-later', ein='100000005')
ORACLE.add(2024, 5, 'competing-later', ein='100000005')
ORACLE.add(2024, 5, 'competing-later-b', ein='100000005')
ORACLE.add(2023, 6, 'padded', ein='23456786')
ORACLE.add(2024, 6, 'padded', ein='023456786')
ORACLE.add(2023, 16, 'padded-both', ein='23456716')
ORACLE.add(2024, 16, 'padded-both', ein='23456716')
ORACLE.add(2023, 7, 'unknown-ein', ein=None)
ORACLE.add(2024, 7, 'unknown-ein', ein='100000007')
ORACLE.add(2023, 17, 'unknown-later-ein', ein='100000017')
ORACLE.add(2024, 17, 'unknown-later-ein', ein='111111111')
ORACLE.add(2023, 8, 'ein-conflict', ein='100000008')
ORACLE.add(2024, 8, 'ein-conflict', ein='200000008')
ORACLE.add(2023, 9, 'base-null-address', ein='100000009', zip_code=None)
ORACLE.add(2024, 9, 'base-null-address', ein='100000009')
ORACLE.add(2023, 10, 'later-null-address', ein='100000010')
ORACLE.add(2024, 10, 'later-null-address', ein='100000010', street_address='')
ORACLE.add(2023, 11, 'changed', ein='100000011')
ORACLE.add(2024, 111, 'changed', ein='100000011')
ORACLE.add(2023, 12, 'null-collision', ein='100000012')
ORACLE.add(2023, None, 'null-collision', ein='100000012')
ORACLE.add(2024, 112, 'null-collision', ein='100000012')
ORACLE.add(2023, 13, 'raw-spelling', ein='12-3456713')
ORACLE.add(2024, 13, 'raw-spelling', ein='123456713')
ORACLE.add(2023, 14, 'relocated', ein='100000014')
ORACLE.add(2024, 14, 'relocated', ein='100000014', street_address='14 New Rd')
ORACLE.add(2023, 15, 'reappears', ein='100000015')
ORACLE.add(2024, 115, 'reappears', ein='100000015')
ORACLE.add(2024, 15, 'reappears-elsewhere', ein='100000099')
ORACLE.add(2023, 18, 'padded-changed', ein='23456718')
ORACLE.add(2024, 118, 'padded-changed', ein='23456718')
ORACLE.add(2023, 19, 'nameless', ein='100000019', establishment_name='')
ORACLE.add(2024, 119, 'nameless', ein='100000019', establishment_name='')
ORACLE.add(2023, 20, 'competing-collision', ein='100000020')
ORACLE.add(2023, 21, 'competing-collision', ein='100000020', id=950)
ORACLE.add(2023, 21, 'competing-other', ein='100000021')
ORACLE.add(2024, 120, 'competing-collision', ein='100000020')
ORACLE.add(2023, 22, 'padded-collision', ein='023456722')
ORACLE.add(2023, 23, 'padded-collision', ein='23456722')
ORACLE.add(2024, 122, 'padded-collision', ein='023456722')


def test_v2_counts_equal_stage3_link_report():
    frame = canonical_frame(ORACLE.rows)
    expected = link_report(frame.select(SOURCE_COLUMNS), 2023, 2024)
    result = build_links(keyed_records(frame, KEYS))
    assert v2_row(result) == {column: expected[column] for column in V2_COLUMNS}


def test_oracle_fixture_counts():
    '''Pin the fixture's 2023 -> 2024 counts, so a fixture edit that drops a shape shows.'''
    expected = {
        'n_cohort_ids': 22,
        'n_raw_reappeared': 14,
        'n_unique_cohort_ids': 20,
        'n_reappeared': 12,
        'n_same_ein_address': 3,
        'n_same_ein_address_including_padded': 5,
        'n_same_raw_ein_address': 3,
        'n_reappeared_ein_unknown': 2,
        'n_reappeared_ein_conflict': 2,
        'n_reappeared_address_conflict': 3,
        'n_base_missing_id_rows': 3,
        'n_later_missing_id_rows': 4,
        'n_unique_address_matches': 5,
        'n_address_matches_different_id': 2,
    }
    assert stage3(ORACLE.rows) == expected
    assert v2_row(build(ORACLE.rows)) == expected


def test_v2_frame_has_every_pair_in_order_with_stage3_counts():
    rows = [*ORACLE.rows,
            rec(2025, 1, 'same', ein='100000001'),
            rec(2025, 5, 'competing-later', ein='100000005'),
            rec(2025, 211, 'changed', ein='100000011'),
            rec(2025, None, 'null-2025'),
            rec(2022, 1, 'same', ein='100000001')]
    result = build(rows)
    assert result.v2.columns == ['base_year', 'later_year', *V2_COLUMNS]
    assert set(result.v2.dtypes) == {pl.Int64}
    assert result.v2.select('base_year', 'later_year').rows() == list(YEAR_PAIRS)
    for pair in YEAR_PAIRS:
        assert v2_row(result, pair) == stage3(rows, pair), pair
    assert set(v2_row(result, (2016, 2017)).values()) == {0}
    assert v2_row(result, (2023, 2025))['n_reappeared'] == 2


# Weighted pools: mostly usable values, so links confirm, with every unusable spelling too.
POOLS = {
    'establishment_id': {None: 1, **dict.fromkeys(range(1, 17), 1)},
    'ein': {'123456789': 5, '12-3456789': 2, ' 123456789 ': 1, '23456789': 2, '023456789': 2,
            '987654321': 3, None: 2, '': 1, '111111111': 1, 'abc': 1},
    'establishment_name': {'Plant': 8, 'plant ': 3, 'Mill': 7, '': 2},
    'street_address': {'1 Main St': 9, '2 Oak Ave': 9, '': 2},
    'zip_code': {'02134': 12, '2134': 3, '99999': 3, None: 2},
}


def random_rows(seed):
    '''Records over small pools, so IDs, tuples and whole rows repeat by chance.'''
    rng = random.Random(seed)
    rows = []
    for _ in range(60):
        if rows and rng.random() < 0.15:
            rows.append(dict(rng.choice(rows)))
            continue
        row = {'year_filing_for': rng.choice((2022, 2023, 2024, 2025)), 'id': rng.randint(1, 3)}
        for column, pool in POOLS.items():
            row[column] = rng.choices(list(pool), weights=list(pool.values()))[0]
        rows.append(row)
    return rows


def test_v2_counts_equal_stage3_link_report_on_random_records():
    for seed in range(16):
        rows = random_rows(seed)
        result = build(rows)
        for pair in YEAR_PAIRS:
            assert v2_row(result, pair) == stage3(rows, pair), (seed, pair)
        validate_links(result.links, keyed(rows))


# One base 2023 record for each status, with its successors in 2024.
PRECEDENCE = Rows()
P_MISSING = PRECEDENCE.add(2023, None, 'missing')
P_AMBIGUOUS_A = PRECEDENCE.add(2023, 2, 'ambiguous-a')
P_AMBIGUOUS_B = PRECEDENCE.add(2023, 2, 'ambiguous-b')
P_CONFLICT = PRECEDENCE.add(2023, 3, 'conflict', ein='300000003')
PRECEDENCE.add(2024, 3, 'conflict-renamed', ein='300000003', street_address='conflict Main St')
PRECEDENCE.add(2024, 33, 'conflict', ein='300000003')
P_SAME = PRECEDENCE.add(2023, 4, 'same', ein='400000004')
P_SAME_LATER = PRECEDENCE.add(2024, 4, 'same', ein='400000004')
P_CHANGED = PRECEDENCE.add(2023, 5, 'changed', ein='500000005')
P_CHANGED_LATER = PRECEDENCE.add(2024, 55, 'changed', ein='500000005')
P_WEAKER = PRECEDENCE.add(2023, 6, 'weaker', ein=None)
P_WEAKER_LATER = PRECEDENCE.add(2024, 6, 'weaker', ein='600000006')
P_NONE = PRECEDENCE.add(2023, 7, 'none', ein='700000007')


def test_status_precedence():
    rows = pair_rows(build(PRECEDENCE.rows))
    observed = {
        base: (row['status'], row['later_row'], row['later_establishment_id'], true_reasons(row))
        for base, row in rows.items()
    }
    assert observed == {
        P_MISSING: ('missing_id', None, None, set()),
        P_AMBIGUOUS_A: ('ambiguous_id', None, None, set()),
        P_AMBIGUOUS_B: ('ambiguous_id', None, None, set()),
        P_CONFLICT: ('conflict', None, None, set()),
        P_SAME: ('confirmed_same_id', P_SAME_LATER, 4, set()),
        P_CHANGED: ('confirmed_changed_id', P_CHANGED_LATER, 55, set()),
        P_WEAKER: ('weaker_same_id', P_WEAKER_LATER, 6, {'reason_ein_unknown'}),
        P_NONE: ('no_candidate', None, None, set()),
    }


def test_null_ids_are_missing_before_ambiguous():
    rows = [rec(2023, None, 'a'), rec(2023, None, 'b'), rec(2024, None, 'a')]
    assert {row['status'] for row in pair_rows(build(rows)).values()} == {'missing_id'}


def test_competing_base_id_is_ambiguous_even_when_its_twin_would_confirm():
    rows = [
        rec(2023, 8, 'twin', ein='800000008'),
        rec(2023, 8, 'twin-b', ein='800000008'),
        rec(2024, 8, 'twin', ein='800000008'),
    ]
    links = pair_rows(build(rows))
    assert {base: (row['status'], row['later_row']) for base, row in links.items()} == {
        0: ('ambiguous_id', None),
        1: ('ambiguous_id', None),
    }


def conflict_report(result, pair=PAIR):
    return result.report['pairs'][f'{pair[0]}-{pair[1]}']


def test_conflict_two_successors():
    rows = Rows()
    base = rows.add(2023, 3, 'conflict', ein='300000003')
    rows.add(2024, 3, 'conflict-renamed', ein='300000003', street_address='conflict Main St')
    rows.add(2024, 33, 'conflict', ein='300000003')
    result = build(rows.rows)
    link = pair_rows(result)[base]
    assert (link['status'], link['later_row'], link['later_establishment_id']) == (
        'conflict', None, None)
    assert true_reasons(link) == set()
    report = conflict_report(result)
    assert report['v2']['n_same_ein_address'] == 1
    assert report['v2']['n_address_matches_different_id'] == 1
    assert report['statuses']['conflict'] == 1
    assert (report['n_conflict_with_same_link'], report['n_conflict_with_changed_link'],
            report['n_conflict_both_links']) == (1, 1, 1)
    assert (report['v2']['n_same_ein_address'] - report['statuses']['confirmed_same_id']
            == report['n_conflict_with_same_link'])
    assert (report['v2']['n_address_matches_different_id']
            - report['statuses']['confirmed_changed_id'] == report['n_conflict_with_changed_link'])


def test_conflict_shared_successor():
    rows = Rows()
    same = rows.add(2023, 1, 'first', ein='100000001', street_address='shared Main St')
    changed = rows.add(2023, 2, 'second', ein='100000001', street_address='shared Main St')
    rows.add(2024, 1, 'second', ein='100000001', street_address='shared Main St')
    result = build(rows.rows)
    links = pair_rows(result)
    assert {base: (row['status'], row['later_row'], row['later_establishment_id'])
            for base, row in links.items()} == {
        same: ('conflict', None, None),
        changed: ('conflict', None, None),
    }
    report = conflict_report(result)
    assert report['statuses']['conflict'] == 2
    assert (report['n_conflict_with_same_link'], report['n_conflict_with_changed_link'],
            report['n_conflict_both_links']) == (1, 1, 0)
    assert (report['v2']['n_same_ein_address'] - report['statuses']['confirmed_same_id']
            == report['n_conflict_with_same_link'])
    assert (report['v2']['n_address_matches_different_id']
            - report['statuses']['confirmed_changed_id'] == report['n_conflict_with_changed_link'])


def test_weaker_link_does_not_share_a_successor():
    rows = Rows()
    weaker = rows.add(2023, 1, 'first', ein=None, street_address='shared Main St')
    changed = rows.add(2023, 2, 'second', ein='100000001', street_address='shared Main St')
    later = rows.add(2024, 1, 'second', ein='100000001', street_address='shared Main St')
    links = pair_rows(build(rows.rows))
    assert {base: (row['status'], row['later_row']) for base, row in links.items()} == {
        weaker: ('weaker_same_id', later),
        changed: ('confirmed_changed_id', later),
    }


def test_same_id_tuple_match_stays_confirmed_same_id():
    rows = [rec(2023, 1, 'same', ein='100000001'), rec(2024, 1, 'same', ein='100000001')]
    result = build(rows)
    assert pair_rows(result)[0]['status'] == 'confirmed_same_id'
    assert v2_row(result)['n_unique_address_matches'] == 1
    assert v2_row(result)['n_address_matches_different_id'] == 0


def test_exact_duplicates_collapse_only_for_links():
    rows = [rec(2023, 1, 'twin', id=900), rec(2023, 1, 'twin', id=900)]
    links = pair_rows(build(rows))
    assert list(links) == [0]
    assert links[0]['base_rows'] == [0, 1]
    nodes, code_paths = naics_reference(['332312'])
    pairs = build_pairs(keyed(rows), nodes, code_paths)
    assert pairs.pairs.collect()['n_records'].to_list() == [2]
    assert pairs.members.collect().height == 2


def test_duplicates_with_nulls_collapse():
    rows = [
        rec(2023, None, 'twin', ein=None, zip_code=None, id=900),
        rec(2023, None, 'twin', ein=None, zip_code=None, id=900),
        rec(2023, None, 'twin', ein=None, zip_code=None, id=901),
    ]
    links = pair_rows(build(rows))
    assert {base: row['base_rows'] for base, row in links.items()} == {0: [0, 1], 2: [2]}


def test_weaker_reasons():
    rows = Rows()
    ambiguous = rows.add(2023, 1, 'ambiguous', ein='100000001')
    rows.add(2024, 1, 'ambiguous', ein=None)
    rows.add(2024, 1, 'ambiguous-moved', ein='100000001')
    unknown = rows.add(2023, 2, 'unknown', ein=None)
    unknown_later = rows.add(2024, 2, 'unknown', ein='100000002')
    moved = rows.add(2023, 3, 'moved', ein='23456783')
    moved_later = rows.add(2024, 3, 'moved', ein='023456783', street_address='3 New Rd')
    links = pair_rows(build(rows.rows))
    observed = {base: (row['status'], row['later_row'], true_reasons(row))
                for base, row in links.items() if row['status'] == 'weaker_same_id'}
    assert observed == {
        ambiguous: ('weaker_same_id', None, {'reason_later_id_ambiguous'}),
        unknown: ('weaker_same_id', unknown_later, {'reason_ein_unknown'}),
        moved: ('weaker_same_id', moved_later,
                {'reason_ein_reconstructed', 'reason_address_conflict'}),
    }
    assert links[ambiguous]['later_establishment_id'] is None


@pytest.mark.parametrize(
    ('base', 'later', 'reasons'),
    [
        pytest.param({'ein': None}, {}, {'reason_ein_unknown'}, id='base-ein-null'),
        pytest.param({}, {'ein': None}, {'reason_ein_unknown'}, id='later-ein-null'),
        pytest.param({'ein': '111111111'}, {}, {'reason_ein_unknown'}, id='base-ein-unusable'),
        pytest.param({'ein': '23456789'}, {'ein': '023456789'}, {'reason_ein_reconstructed'},
                     id='base-padded'),
        pytest.param({'ein': '023456789'}, {'ein': '23456789'}, {'reason_ein_reconstructed'},
                     id='later-padded'),
        pytest.param({'ein': '23456789'}, {'ein': '23456789'}, {'reason_ein_reconstructed'},
                     id='both-padded'),
        pytest.param({'ein': '123456789'}, {'ein': '987654321'}, {'reason_ein_conflict'},
                     id='ein-conflict'),
        pytest.param({'zip_code': None}, {}, {'reason_address_incomplete'},
                     id='base-address-null'),
        pytest.param({}, {'street_address': ''}, {'reason_address_incomplete'},
                     id='later-address-null'),
        pytest.param({}, {'street_address': '9 Other Rd'}, {'reason_address_conflict'},
                     id='address-conflict'),
        pytest.param({'ein': None, 'zip_code': None}, {},
                     {'reason_ein_unknown', 'reason_address_incomplete'}, id='unknown-incomplete'),
        pytest.param({'ein': '987654321'}, {'street_address': '9 Other Rd'},
                     {'reason_ein_conflict', 'reason_address_conflict'}, id='both-conflicts'),
    ],
)
def test_each_reason_from_each_side(base, later, reasons):
    rows = [rec(2023, 1, 'site', **base), rec(2024, 1, 'site', **later)]
    link = pair_rows(build(rows))[0]
    assert (link['status'], link['later_row'], link['later_establishment_id']) == (
        'weaker_same_id', 1, 1)
    assert true_reasons(link) == reasons


def test_relocation_is_weaker_not_conflict():
    rows = [rec(2023, 1, 'site', ein='100000001'),
            rec(2024, 1, 'site', ein='100000001', street_address='9 New Rd')]
    link = pair_rows(build(rows))[0]
    assert (link['status'], link['later_row']) == ('weaker_same_id', 1)
    assert true_reasons(link) == {'reason_address_conflict'}


def test_flag_id_reappears_elsewhere():
    rows = Rows()
    reappears = rows.add(2023, 1, 'reappears', ein='100000001')
    successor = rows.add(2024, 11, 'reappears', ein='100000001')
    rows.add(2024, 1, 'elsewhere', ein='100000099')
    alone = rows.add(2023, 2, 'alone', ein='100000002')
    rows.add(2024, 22, 'alone', ein='100000002')
    weaker = rows.add(2023, 3, 'weaker', ein=None)
    rows.add(2024, 3, 'weaker')
    links = pair_rows(build(rows.rows))
    observed = {base: (row['status'], row['later_row'], row['flag_id_reappears_elsewhere'])
                for base, row in links.items() if base in (reappears, alone, weaker)}
    assert observed == {
        reappears: ('confirmed_changed_id', successor, True),
        alone: ('confirmed_changed_id', 4, False),
        weaker: ('weaker_same_id', 6, False),
    }
    assert true_reasons(links[reappears]) == set()


def test_later_row_is_the_smallest_source_row_of_the_successor():
    rows = [
        rec(2024, 1, 'site', id=900),
        rec(2023, 1, 'site'),
        rec(2024, 1, 'site', id=900),
        rec(2023, 2, 'moved', ein='200000002'),
        rec(2024, 22, 'moved', ein='200000002', id=901),
        rec(2024, 22, 'moved', ein='200000002', id=901),
    ]
    links = pair_rows(build_links(keyed(rows).reverse()))
    assert {base: (row['status'], row['later_row']) for base, row in links.items()} == {
        1: ('confirmed_same_id', 0),
        3: ('confirmed_changed_id', 4),
    }


def test_2023_links_to_2025_without_2024():
    rows = [rec(2023, 1, 'skips', ein='100000001'), rec(2025, 1, 'skips', ein='100000001'),
            rec(2024, 2, 'other'), rec(2023, 3, 'gap'), rec(2024, 3, 'gap')]
    result = build(rows)
    links = result.links.collect()
    assert set(links.select('base_year', 'later_year').unique().rows()) == {
        (2023, 2024), (2023, 2025), (2024, 2025)}
    assert pair_rows(result, (2023, 2024))[0]['status'] == 'no_candidate'
    assert pair_rows(result, (2023, 2024))[3]['status'] == 'confirmed_same_id'
    assert pair_rows(result, (2023, 2025))[3]['status'] == 'no_candidate'
    assert (pair_rows(result, (2023, 2025))[0]['status'],
            pair_rows(result, (2023, 2025))[0]['later_row']) == ('confirmed_same_id', 1)


def test_reasons_stay_false_off_weaker_when_the_later_id_is_ambiguous():
    rows = Rows()
    changed = rows.add(2023, 1, 'changed', ein='100000001')
    successor = rows.add(2024, 11, 'changed', ein='100000001')
    rows.add(2024, 1, 'elsewhere-a')
    rows.add(2024, 1, 'elsewhere-b')
    ambiguous = rows.add(2023, 2, 'ambiguous-a')
    twin = rows.add(2023, 2, 'ambiguous-b')
    rows.add(2024, 2, 'ambiguous-a', ein=None)
    rows.add(2024, 2, 'ambiguous-c')
    links = pair_rows(build(rows.rows))
    observed = {base: (row['status'], row['later_row'], true_reasons(row),
                       row['flag_id_reappears_elsewhere'])
                for base, row in links.items() if base in (changed, ambiguous, twin)}
    assert observed == {
        changed: ('confirmed_changed_id', successor, set(), True),
        ambiguous: ('ambiguous_id', None, set(), False),
        twin: ('ambiguous_id', None, set(), False),
    }


def test_other_years_never_supply_a_candidate():
    rows = [rec(2023, 1, 'site'), rec(2022, 1, 'site'), rec(2025, 1, 'site')]
    assert pair_rows(build(rows))[0]['status'] == 'no_candidate'


def test_null_padded_flag_counts_as_padded():
    rows = [rec(2023, 1, 'site'), rec(2024, 1, 'site'), rec(2024, 2, 'other')]
    records = keyed(rows).with_columns(
        flag_ein_padded=pl.when(pl.col('source_row').eq(0)).then(None)
        .otherwise(pl.col('flag_ein_padded'))
    )
    link = pair_rows(build_links(records))[0]
    assert (link['status'], true_reasons(link)) == ('weaker_same_id', {'reason_ein_reconstructed'})
    distinct = distinct_records(records, 2023).collect()
    assert distinct['flag_ein_padded'].to_list() == [True]
    assert distinct['tuple_eligible'].to_list() == [False]


def test_contract_constants():
    assert LINKS_VERSION == 'ita-establishment-links-v1'
    assert STATUSES == ('missing_id', 'ambiguous_id', 'conflict', 'confirmed_same_id',
                        'confirmed_changed_id', 'weaker_same_id', 'no_candidate')
    assert REASONS == ('reason_later_id_ambiguous', 'reason_ein_unknown',
                       'reason_ein_reconstructed', 'reason_ein_conflict',
                       'reason_address_incomplete', 'reason_address_conflict')
    assert list(LINK_SCHEMA.items()) == [
        ('base_year', pl.Int64),
        ('later_year', pl.Int64),
        ('base_row', pl.UInt64),
        ('base_rows', pl.List(pl.UInt64)),
        ('later_row', pl.UInt64),
        ('base_establishment_id', pl.Int64),
        ('later_establishment_id', pl.Int64),
        ('status', pl.String),
        *[(reason, pl.Boolean) for reason in REASONS],
        ('flag_id_reappears_elsewhere', pl.Boolean),
    ]


def test_links_is_a_frozen_dataclass():
    assert [field.name for field in dataclasses.fields(Links)] == ['links', 'v2', 'report']
    result = build(PRECEDENCE.rows)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.report = {}
    assert isinstance(result.links, pl.LazyFrame)
    assert list(result.links.collect_schema().items()) == list(LINK_SCHEMA.items())


DISTINCT_COLUMNS = [
    ('base_row', pl.UInt64),
    ('source_rows', pl.List(pl.UInt64)),
    ('establishment_id', pl.Int64),
    ('ein', pl.String),
    ('ein_key', pl.String),
    ('flag_ein_padded', pl.Boolean),
    ('name_key', pl.String),
    ('address_key', pl.String),
    ('id_unique', pl.Boolean),
    ('tuple_eligible', pl.Boolean),
]


def test_distinct_records_collapse_and_sort():
    rows = [
        rec(2023, 1, 'twin', id=900),
        rec(2024, 1, 'twin', id=900),
        rec(2023, 2, 'other'),
        rec(2023, 1, 'twin', id=900),
    ]
    distinct = distinct_records(keyed(rows).reverse(), 2023).collect()
    assert list(distinct.schema.items()) == DISTINCT_COLUMNS
    assert distinct.select('base_row', 'source_rows', 'establishment_id', 'name_key').rows() == [
        (0, [0, 3], 1, 'plant twin'),
        (2, [2], 2, 'plant other'),
    ]


def test_id_unique_rule():
    rows = [
        rec(2023, 1, 'unique'),
        rec(2023, 2, 'competing-a'),
        rec(2023, 2, 'competing-b'),
        rec(2023, None, 'null'),
        rec(2023, 3, 'twin', id=900),
        rec(2023, 3, 'twin', id=900),
        rec(2024, 1, 'next-year'),
    ]
    distinct = distinct_records(keyed(rows), 2023).collect()
    assert dict(distinct.select('base_row', 'id_unique').rows()) == {
        0: True, 1: False, 2: False, 3: False, 4: True}


TUPLE_CASES = {
    'eligible': ([rec(2023, 1, 'site')], True),
    'twin-rows': ([rec(2023, 1, 'site', id=900), rec(2023, 1, 'site', id=900)], True),
    'competing-id': ([rec(2023, 1, 'site'), rec(2023, 1, 'other')], False),
    'null-id': ([rec(2023, None, 'site')], False),
    'ein-null': ([rec(2023, 1, 'site', ein=None)], False),
    'ein-unusable': ([rec(2023, 1, 'site', ein='000000000')], False),
    'padded': ([rec(2023, 1, 'site', ein='23456789')], False),
    'address-null': ([rec(2023, 1, 'site', city='')], False),
    'name-empty': ([rec(2023, 1, 'site', establishment_name=None)], False),
    'collides-with-null-id': ([rec(2023, 1, 'site'), rec(2023, None, 'site')], False),
    'collides-with-competing-id': (
        [rec(2023, 1, 'site'), rec(2023, 2, 'site'), rec(2023, 2, 'other')], False),
    'collides-with-padded': (
        [rec(2023, 1, 'site', ein='023456789'), rec(2023, 2, 'site', ein='23456789')], False),
    'collides-with-unique-id': ([rec(2023, 1, 'site'), rec(2023, 2, 'site')], False),
    'other-year-shares-tuple': ([rec(2023, 1, 'site'), rec(2024, 2, 'site')], True),
    'other-tuple': ([rec(2023, 1, 'site'), rec(2023, None, 'other')], True),
}


@pytest.mark.parametrize('case', list(TUPLE_CASES))
def test_tuple_eligible_rule(case):
    rows, eligible = TUPLE_CASES[case]
    distinct = distinct_records(keyed(rows), 2023).collect()
    assert distinct.filter(pl.col('base_row').eq(0))['tuple_eligible'].to_list() == [eligible]


def test_links_are_sorted_whatever_the_record_order():
    forward = build(ORACLE.rows)
    backward = build_links(keyed(ORACLE.rows).reverse())
    links = forward.links.collect()
    assert links.equals(links.sort('base_year', 'later_year', 'base_row'))
    assert links['base_rows'].to_list() == links['base_rows'].list.sort().to_list()
    assert backward.links.collect().equals(links)
    assert backward.v2.equals(forward.v2)
    assert backward.report == forward.report


def test_links_cover_each_base_record_once_per_pair():
    result = build(ORACLE.rows)
    links = result.links.collect()
    for base_year, later_year in YEAR_PAIRS:
        expected = distinct_records(keyed(ORACLE.rows), base_year).collect()['base_row']
        observed = links.filter(
            pl.col('base_year').eq(base_year).and_(pl.col('later_year').eq(later_year))
        )['base_row']
        assert observed.to_list() == expected.to_list()


def test_report_counts_statuses_and_conflicts():
    result = build(PRECEDENCE.rows)
    assert list(result.report) == ['pairs']
    assert list(result.report['pairs']) == [f'{s}-{t}' for s, t in YEAR_PAIRS]
    pair = result.report['pairs']['2023-2024']
    assert list(pair) == ['base_year', 'later_year', 'n_base_records', 'v2', 'statuses',
                          'n_conflict_with_same_link', 'n_conflict_with_changed_link',
                          'n_conflict_both_links']
    assert (pair['base_year'], pair['later_year'], pair['n_base_records']) == (2023, 2024, 8)
    assert pair['v2'] == v2_row(result)
    assert pair['statuses'] == {
        'missing_id': 1, 'ambiguous_id': 2, 'conflict': 1, 'confirmed_same_id': 1,
        'confirmed_changed_id': 1, 'weaker_same_id': 1, 'no_candidate': 1,
    }
    assert (pair['n_conflict_with_same_link'], pair['n_conflict_with_changed_link'],
            pair['n_conflict_both_links']) == (1, 1, 1)
    later = result.report['pairs']['2024-2025']
    assert later['n_base_records'] == 5
    assert later['statuses']['no_candidate'] == 5
    empty = result.report['pairs']['2016-2017']
    assert empty['n_base_records'] == 0
    assert set(empty['statuses'].values()) == {0}
    assert set(empty['v2'].values()) == {0}
    assert json.loads(json.dumps(result.report)) == result.report


@pytest.mark.parametrize(
    ('field', 'nested'),
    [
        pytest.param('n_conflict_with_same_link', None, id='same-link-identity'),
        pytest.param('n_conflict_with_changed_link', None, id='changed-link-identity'),
        pytest.param('n_base_records', None, id='partition'),
        pytest.param('n_same_ein_address', 'v2', id='same-count'),
        pytest.param('n_address_matches_different_id', 'v2', id='changed-count'),
        pytest.param('weaker_same_id', 'statuses', id='status-count'),
    ],
)
def test_report_identities_fail_the_build(field, nested):
    pair = build(PRECEDENCE.rows).report['pairs']['2023-2024']
    ita_establishment_links._check_pair_report(pair)
    broken = json.loads(json.dumps(pair))
    (broken[nested] if nested else broken)[field] += 1
    with pytest.raises(ValueError, match=message('link report identities do not hold')):
        ita_establishment_links._check_pair_report(broken)


def test_build_fails_when_an_identity_does_not_hold(monkeypatch):
    original = ita_establishment_links._link_pair

    def miscounted(base, later, pair):
        links, report = original(base, later, pair)
        return links, {**report,
                       'n_conflict_with_same_link': report['n_conflict_with_same_link'] + 1}

    monkeypatch.setattr(ita_establishment_links, '_link_pair', miscounted)
    with pytest.raises(ValueError, match=message('link report identities do not hold')):
        build(PRECEDENCE.rows)


KEYED_GAPS = [
    pytest.param(lambda lf: lf.drop('ein_key'), id='missing-ein-key'),
    pytest.param(lambda lf: lf.drop('address_key'), id='missing-address-key'),
    pytest.param(lambda lf: lf.drop('source_row'), id='missing-source-row'),
    pytest.param(lambda lf: lf.drop('size'), id='missing-source-column'),
    pytest.param(lambda lf: lf.with_columns(pl.col('source_row').cast(pl.Int64)),
                 id='source-row-type'),
    pytest.param(lambda lf: lf.with_columns(pl.col('flag_ein_padded').cast(pl.String)),
                 id='padded-flag-type'),
]


@pytest.mark.parametrize('transform', KEYED_GAPS)
def test_build_refuses_records_without_the_keyed_columns(transform):
    with pytest.raises(ValueError, match=message('links need keyed records')):
        build_links(transform(keyed(PRECEDENCE.rows)))
    with pytest.raises(ValueError, match=message('links need keyed records')):
        distinct_records(transform(keyed(PRECEDENCE.rows)), 2023)


@pytest.mark.parametrize('transform', KEYED_GAPS)
def test_validator_refuses_records_without_the_keyed_columns(transform):
    result = build(PRECEDENCE.rows)
    with pytest.raises(ValueError, match=message('links need keyed records')):
        validate_links(result.links, transform(keyed(PRECEDENCE.rows)))


# A valid build whose 2023 -> 2024 rows hold every status, both weaker kinds, a duplicate
# base record and changed-ID links whose base ID is absent, unique or competing in 2024.
VALID = Rows()
V_MISSING = VALID.add(2023, None, 'missing')
V_AMBIGUOUS = VALID.add(2023, 2, 'ambiguous-a')
VALID.add(2023, 2, 'ambiguous-b')
V_SAME = VALID.add(2023, 3, 'same', id=900)
V_SAME_TWIN = VALID.add(2023, 3, 'same', id=900)
V_SAME_LATER = VALID.add(2024, 3, 'same')
V_CHANGED = VALID.add(2023, 4, 'changed', ein='400000004')
V_CHANGED_LATER = VALID.add(2024, 44, 'changed', ein='400000004')
V_ELSEWHERE = VALID.add(2024, 4, 'elsewhere', ein='400000099')
V_WEAKER = VALID.add(2023, 5, 'weaker', ein=None)
V_WEAKER_LATER = VALID.add(2024, 5, 'weaker', ein='23456785', zip_code=None)
V_LATER_AMBIGUOUS = VALID.add(2023, 6, 'later-ambiguous')
V_LATER_AMBIGUOUS_A = VALID.add(2024, 6, 'later-ambiguous-a')
VALID.add(2024, 6, 'later-ambiguous-b')
V_CONFLICT = VALID.add(2023, 7, 'conflict', ein='700000007')
VALID.add(2024, 7, 'conflict-renamed', ein='700000007', street_address='conflict Main St')
V_CONFLICT_CHANGED = VALID.add(2024, 77, 'conflict', ein='700000007')
V_NONE = VALID.add(2023, 8, 'none')
V_ALONE = VALID.add(2023, 9, 'changed-alone', ein='900000009')
V_ALONE_LATER = VALID.add(2024, 99, 'changed-alone', ein='900000009')
VALID.add(2024, 2, 'ambiguous-a')
VALID.add(2024, 2, 'ambiguous-c')
V_CHANGED_AMBIGUOUS = VALID.add(2023, 10, 'changed-ambiguous', ein='100000010')
V_CHANGED_AMBIGUOUS_LATER = VALID.add(2024, 110, 'changed-ambiguous', ein='100000010')
VALID.add(2024, 10, 'changed-ambiguous-a')
VALID.add(2024, 10, 'changed-ambiguous-b')
# Unlinked probes whose later records differ from the base tuple in one way each.
V_PROBE = VALID.add(2023, 20, 'probe', ein='200000020')
V_PROBE_NAME = VALID.add(2024, 201, 'probe', ein='200000020',
                         establishment_name='Plant probe-renamed')
V_PROBE_EIN = VALID.add(2024, 202, 'probe', ein='200000021')
V_PROBE_ADDRESS = VALID.add(2024, 203, 'probe', ein='200000020', street_address='probe Moved St')
V_PROBE_NULL_EIN = VALID.add(2024, 205, 'probe', ein=None)
V_PROBE_LATER = VALID.add(2023, 21, 'probe-two', ein='200000022')
V_PROBE_LATER_TWIN = VALID.add(2024, 210, 'probe-two', ein='200000022')
VALID.add(2024, 210, 'probe-two-other', ein='200000022')
V_PROBE_BASE = VALID.add(2023, 22, 'probe-three', ein='200000023')
VALID.add(2023, 22, 'probe-three-other', ein='200000023')
V_PROBE_BASE_LATER = VALID.add(2024, 220, 'probe-three', ein='200000023')
# A same-ID and a changed-ID link to one record: both conflict.
SHARED = {'ein': '300000030', 'street_address': 'shared Main St'}
V_SHARED_SAME = VALID.add(2023, 30, 'shared-first', **SHARED)
V_SHARED_CHANGED = VALID.add(2023, 31, 'shared-second', **SHARED)
V_SHARED_LATER = VALID.add(2024, 30, 'shared-second', **SHARED)
# A weaker same-ID link and a changed-ID link to one record: both keep their status.
WEAK_SHARE = {'street_address': 'weakshare Main St'}
V_WEAK_SHARE = VALID.add(2023, 40, 'weakshare-first', ein=None, **WEAK_SHARE)
V_WEAK_SHARE_CHANGED = VALID.add(2023, 41, 'weakshare-second', ein='400000040', **WEAK_SHARE)
V_WEAK_SHARE_LATER = VALID.add(2024, 40, 'weakshare-second', ein='400000040', **WEAK_SHARE)


def test_valid_fixture_is_the_one_the_broken_tables_assume():
    links = pair_rows(build(VALID.rows))
    observed = {
        base: (row['status'], row['base_rows'], row['later_row'], row['later_establishment_id'],
               true_reasons(row), row['flag_id_reappears_elsewhere'])
        for base, row in links.items()
    }
    assert observed == {
        V_MISSING: ('missing_id', [V_MISSING], None, None, set(), False),
        V_AMBIGUOUS: ('ambiguous_id', [V_AMBIGUOUS], None, None, set(), False),
        V_AMBIGUOUS + 1: ('ambiguous_id', [V_AMBIGUOUS + 1], None, None, set(), False),
        V_SAME: ('confirmed_same_id', [V_SAME, V_SAME_TWIN], V_SAME_LATER, 3, set(), False),
        V_CHANGED: ('confirmed_changed_id', [V_CHANGED], V_CHANGED_LATER, 44, set(), True),
        V_WEAKER: ('weaker_same_id', [V_WEAKER], V_WEAKER_LATER, 5,
                   {'reason_ein_unknown', 'reason_ein_reconstructed',
                    'reason_address_incomplete'}, False),
        V_LATER_AMBIGUOUS: ('weaker_same_id', [V_LATER_AMBIGUOUS], None, None,
                            {'reason_later_id_ambiguous'}, False),
        V_CONFLICT: ('conflict', [V_CONFLICT], None, None, set(), False),
        V_NONE: ('no_candidate', [V_NONE], None, None, set(), False),
        V_ALONE: ('confirmed_changed_id', [V_ALONE], V_ALONE_LATER, 99, set(), False),
        V_CHANGED_AMBIGUOUS: ('confirmed_changed_id', [V_CHANGED_AMBIGUOUS],
                              V_CHANGED_AMBIGUOUS_LATER, 110, set(), True),
        V_PROBE: ('no_candidate', [V_PROBE], None, None, set(), False),
        V_PROBE_LATER: ('no_candidate', [V_PROBE_LATER], None, None, set(), False),
        V_PROBE_BASE: ('ambiguous_id', [V_PROBE_BASE], None, None, set(), False),
        V_PROBE_BASE + 1: ('ambiguous_id', [V_PROBE_BASE + 1], None, None, set(), False),
        V_SHARED_SAME: ('conflict', [V_SHARED_SAME], None, None, set(), False),
        V_SHARED_CHANGED: ('conflict', [V_SHARED_CHANGED], None, None, set(), False),
        V_WEAK_SHARE: ('weaker_same_id', [V_WEAK_SHARE], V_WEAK_SHARE_LATER, 40,
                       {'reason_ein_unknown'}, False),
        V_WEAK_SHARE_CHANGED: ('confirmed_changed_id', [V_WEAK_SHARE_CHANGED],
                               V_WEAK_SHARE_LATER, 40, set(), False),
    }
    distinct = distinct_records(keyed(VALID.rows), 2024).collect()
    eligible = dict(distinct.select('base_row', 'tuple_eligible').rows())
    assert [eligible[row] for row in (V_PROBE_NAME, V_PROBE_EIN, V_PROBE_ADDRESS,
                                      V_PROBE_NULL_EIN, V_PROBE_LATER_TWIN,
                                      V_PROBE_BASE_LATER)] == [True, True, True, False, False,
                                                               True]


@pytest.mark.parametrize(
    'rows',
    [
        pytest.param(VALID.rows, id='valid'),
        pytest.param(ORACLE.rows, id='oracle'),
        pytest.param(PRECEDENCE.rows, id='precedence'),
        pytest.param([], id='empty'),
    ],
)
def test_validator_accepts_the_build(rows):
    validate_links(build(rows).links, keyed(rows))


def at(base_row, pair=PAIR):
    return {'base_year': pair[0], 'later_year': pair[1], 'base_row': base_row}


def edit(frame, where, **changes):
    '''A copy of `frame` with `changes` applied to the rows matching every `where` item.'''
    rows = frame.to_dicts()
    hits = [row for row in rows if all(row[key] == value for key, value in where.items())]
    assert hits
    for row in hits:
        row.update(changes)
    return pl.DataFrame(rows, schema=frame.schema, orient='row')


def matching(where):
    condition = pl.lit(True)
    for key, value in where.items():
        condition = condition.and_(pl.col(key).eq(value))
    return condition


def without(frame, where):
    return frame.filter(matching(where).not_())


def resorted(frame):
    return frame.sort('base_year', 'later_year', 'base_row')


def test_validator_rejects_missing_base_record():
    links = build(VALID.rows).links.collect()
    broken = without(links, at(V_NONE))
    with pytest.raises(ValueError,
                       match=message('link base records differ from the distinct records')):
        validate_links(broken.lazy(), keyed(VALID.rows))


SCHEMA = 'links do not have the link schema'
NULLS = 'links hold a null key, status, reason or flag'
KEY_ORDER = 'link keys are not sorted and unique'
PAIRS = 'link year pairs are not the adopted pairs'
ROW_ORDER = 'link base rows are not sorted from the base row'
DIFFER = 'link base records differ from the distinct records'
STATUS = 'link statuses are not link statuses'
MISSING = 'a null base ID does not match the missing_id status'
SUCCESSORS = 'link successors do not follow the successor rules'
REASON_RULES = 'link reasons do not follow the weaker-evidence rules'
FLAG = 'link flags do not follow the reappearance rule'
LATER_2025 = {'base_year': 2023, 'later_year': 2025}
BROKEN = {
    'schema-missing-column': (lambda f: f.drop('flag_id_reappears_elsewhere'), SCHEMA),
    'schema-column-order': (lambda f: f.select(reversed(f.columns)), SCHEMA),
    'schema-dtype': (lambda f: f.with_columns(pl.col('base_row').cast(pl.Int64)), SCHEMA),
    'null-base-year': (lambda f: edit(f, at(V_NONE), base_year=None), NULLS),
    'null-later-year': (lambda f: edit(f, at(V_NONE), later_year=None), NULLS),
    'null-base-row': (lambda f: edit(f, at(V_NONE), base_row=None), NULLS),
    'null-base-rows': (lambda f: edit(f, at(V_NONE), base_rows=None), NULLS),
    'null-in-base-rows': (lambda f: edit(f, at(V_SAME), base_rows=[V_SAME, None]), NULLS),
    'null-status': (lambda f: edit(f, at(V_NONE), status=None), NULLS),
    **{f'null-{reason}': ((lambda f, r=reason: edit(f, at(V_NONE), **{r: None})), NULLS)
       for reason in REASONS},
    'null-flag': (lambda f: edit(f, at(V_NONE), flag_id_reappears_elsewhere=None), NULLS),
    'keys-unsorted': (lambda f: f.reverse(), KEY_ORDER),
    'keys-repeated': (lambda f: resorted(pl.concat([f, f.filter(matching(at(V_NONE)))])),
                      KEY_ORDER),
    'pair-unknown': (lambda f: edit(f, LATER_2025, later_year=2026), PAIRS),
    'base-rows-unsorted': (lambda f: edit(f, at(V_SAME), base_rows=[V_SAME_TWIN, V_SAME]),
                           ROW_ORDER),
    'base-rows-unsorted-from-base': (
        lambda f: edit(f, at(V_SAME), base_rows=[V_SAME, V_SAME_TWIN, V_MISSING]), ROW_ORDER),
    'base-rows-empty': (lambda f: edit(f, at(V_NONE), base_rows=[]), ROW_ORDER),
    'base-row-not-first': (lambda f: edit(f, at(V_SAME), base_rows=[V_SAME_TWIN]), ROW_ORDER),
    'base-record-extra': (
        lambda f: resorted(pl.concat([f, edit(f.filter(matching(at(V_NONE))), at(V_NONE),
                                              base_row=999, base_rows=[999])])),
        DIFFER,
    ),
    'base-rows-subset': (lambda f: edit(f, at(V_SAME), base_rows=[V_SAME]), DIFFER),
    'base-id-changed': (lambda f: edit(f, at(V_NONE), base_establishment_id=88), DIFFER),
    'pair-missing': (lambda f: without(f, LATER_2025), DIFFER),
    'status-unknown': (lambda f: edit(f, at(V_NONE), status='confirmed'), STATUS),
    'missing-status-with-id': (lambda f: edit(f, at(V_NONE), status='missing_id'), MISSING),
    'null-id-other-status': (lambda f: edit(f, at(V_MISSING), status='no_candidate'), MISSING),
    'confirmed-without-successor': (
        lambda f: edit(f, at(V_SAME), later_row=None, later_establishment_id=None), SUCCESSORS),
    'successor-on-no-candidate': (
        lambda f: edit(f, at(V_NONE), later_row=V_SAME_LATER, later_establishment_id=3),
        SUCCESSORS,
    ),
    'successor-on-ambiguous-later': (
        lambda f: edit(f, at(V_LATER_AMBIGUOUS), later_row=V_LATER_AMBIGUOUS_A,
                       later_establishment_id=6),
        SUCCESSORS,
    ),
    'successor-on-conflict': (
        lambda f: edit(f, at(V_CONFLICT), later_row=V_CONFLICT_CHANGED,
                       later_establishment_id=77),
        SUCCESSORS,
    ),
    'successor-without-id': (lambda f: edit(f, at(V_SAME), later_establishment_id=None),
                             SUCCESSORS),
    'id-without-successor': (lambda f: edit(f, at(V_NONE), later_establishment_id=8),
                             SUCCESSORS),
    'successor-not-a-later-record': (lambda f: edit(f, at(V_CHANGED), later_row=999),
                                     SUCCESSORS),
    'successor-id-differs-from-record': (
        lambda f: edit(f, at(V_CHANGED), later_establishment_id=45), SUCCESSORS),
    'weaker-successor-other-id': (
        lambda f: edit(f, at(V_WEAKER), later_row=V_SAME_LATER, later_establishment_id=3),
        SUCCESSORS,
    ),
    'confirmed-same-successor-other-id': (
        lambda f: edit(f, at(V_SAME), later_row=V_CHANGED_LATER, later_establishment_id=44),
        SUCCESSORS,
    ),
    'changed-successor-same-id': (
        lambda f: edit(f, at(V_CHANGED), later_row=V_ELSEWHERE, later_establishment_id=4),
        SUCCESSORS,
    ),
    'reason-on-confirmed': (lambda f: edit(f, at(V_SAME), reason_ein_unknown=True),
                            REASON_RULES),
    'reason-on-no-candidate': (lambda f: edit(f, at(V_NONE), reason_later_id_ambiguous=True),
                               REASON_RULES),
    'ambiguous-later-extra-reason': (
        lambda f: edit(f, at(V_LATER_AMBIGUOUS), reason_ein_unknown=True), REASON_RULES),
    'ambiguous-later-unflagged': (
        lambda f: edit(f, at(V_LATER_AMBIGUOUS), reason_later_id_ambiguous=False),
        REASON_RULES,
    ),
    'later-unique-flagged-ambiguous': (
        lambda f: edit(f, at(V_WEAKER), reason_later_id_ambiguous=True), REASON_RULES),
    **{f'flip-{reason}': ((lambda f, r=reason: edit(f, at(V_WEAKER), **{
        r: not f.filter(matching(at(V_WEAKER)))[r].item()})), REASON_RULES)
       for reason in REASONS[1:]},
    'flag-on-confirmed-same': (lambda f: edit(f, at(V_SAME), flag_id_reappears_elsewhere=True),
                               FLAG),
    'flag-missing-on-reappearance': (
        lambda f: edit(f, at(V_CHANGED), flag_id_reappears_elsewhere=False), FLAG),
    'flag-without-reappearance': (
        lambda f: edit(f, at(V_ALONE), flag_id_reappears_elsewhere=True), FLAG),
    'flag-missing-on-ambiguous-reappearance': (
        lambda f: edit(f, at(V_CHANGED_AMBIGUOUS), flag_id_reappears_elsewhere=False), FLAG),
    'flag-on-weaker': (lambda f: edit(f, at(V_WEAKER), flag_id_reappears_elsewhere=True), FLAG),
    'confirmed-same-to-ambiguous-later': (
        lambda f: edit(f, at(V_LATER_AMBIGUOUS), status='confirmed_same_id',
                       later_row=V_LATER_AMBIGUOUS_A, later_establishment_id=6,
                       reason_later_id_ambiguous=False),
        SUCCESSORS,
    ),
    'changed-successor-other-tuple': (
        lambda f: edit(f, at(V_CHANGED), later_row=V_ALONE_LATER, later_establishment_id=99),
        SUCCESSORS,
    ),
    'changed-successors-shared': (
        lambda f: edit(f, at(V_ALONE), later_row=V_CHANGED_LATER, later_establishment_id=44),
        SUCCESSORS,
    ),
    **{f'changed-successor-{name}': ((lambda f, r=row, i=later_id: edit(
        f, at(V_PROBE), status='confirmed_changed_id', later_row=r,
        later_establishment_id=i)), SUCCESSORS)
       for name, row, later_id in (('other-name', V_PROBE_NAME, 201),
                                   ('other-ein', V_PROBE_EIN, 202),
                                   ('other-address', V_PROBE_ADDRESS, 203),
                                   ('null-ein', V_PROBE_NULL_EIN, 205))},
    'changed-successor-later-ineligible': (
        lambda f: edit(f, at(V_PROBE_LATER), status='confirmed_changed_id',
                       later_row=V_PROBE_LATER_TWIN, later_establishment_id=210),
        SUCCESSORS,
    ),
    'changed-successor-base-ineligible': (
        lambda f: edit(f, at(V_PROBE_BASE), status='confirmed_changed_id',
                       later_row=V_PROBE_BASE_LATER, later_establishment_id=220),
        SUCCESSORS,
    ),
    'changed-successor-with-the-base-id': (
        lambda f: edit(f, at(V_SAME), status='confirmed_changed_id',
                       flag_id_reappears_elsewhere=True),
        SUCCESSORS,
    ),
    'changed-successor-without-id': (
        lambda f: edit(f, at(V_CHANGED), later_establishment_id=None), SUCCESSORS),
    'changed-without-successor': (
        lambda f: edit(f, at(V_CHANGED), later_row=None, later_establishment_id=None),
        SUCCESSORS,
    ),
    'confirmed-successors-shared': (
        lambda f: edit(edit(f, at(V_SHARED_SAME), status='confirmed_same_id',
                            later_row=V_SHARED_LATER, later_establishment_id=30),
                       at(V_SHARED_CHANGED), status='confirmed_changed_id',
                       later_row=V_SHARED_LATER, later_establishment_id=30),
        SUCCESSORS,
    ),
}


@pytest.mark.parametrize('case', list(BROKEN))
def test_validator_rejects_a_broken_table(case):
    change, reason = BROKEN[case]
    links = build(VALID.rows).links.collect()
    broken = change(links)
    with pytest.raises(ValueError, match=message(reason)):
        validate_links(broken.lazy(), keyed(VALID.rows))


def test_module_loads_no_ipums_or_dotenv_module():
    code = ('import sys; import embedding_data.ita_establishment_links as m; '
            'bad = [n for n in sys.modules if n.split(".")[0] in {"dotenv", "ipumspy"} '
            'or n.startswith(("embedding_data.ipums", "embedding_data.acs"))]; '
            'sys.exit(1 if bad else 0)')
    assert subprocess.run([sys.executable, '-c', code], check=False).returncode == 0
