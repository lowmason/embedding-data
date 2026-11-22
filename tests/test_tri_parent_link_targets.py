'''TRI parent-link targets: shares, companion tables, report and validator, on synthetic rows.'''

import json
import re
from dataclasses import FrozenInstanceError, replace
from datetime import date

import polars as pl
import pytest
from tri_fixtures import rows_frame

from embedding_data import target_contract
from embedding_data.tri_codes import NODE_PREFIX
from embedding_data.tri_facility_years import reduce
from embedding_data.tri_layout import load_layouts
from embedding_data.tri_parent_link_targets import (
    CONTRACT,
    DNB_LABEL,
    FEDERAL_LABEL,
    MARGINAL_SCHEMA,
    METADATA,
    SIZE_LABEL,
    SUPPORT_SCHEMA,
    TOLERANCE,
    UNIVERSE,
    YEARS,
    ParentLinks,
    distribution,
    estimate,
    name_collisions,
    validate_parent_links,
)

LAYOUTS = load_layouts()
DAY = date(2025, 11, 5)
# Real NAICS 2022 codes stand for the selected national-industry nodes. Their sorted order
# (C, D, B, A) differs from the order of the letters, so a sort that is missing shows.
A, B, C, D = (NODE_PREFIX + code for code in ('325199', '311111', '212311', '221114'))
NODES = frozenset({A, B, C, D})
# Made-up D&B numbers, each distinct and nine digits long so that no count equals one.
NUMBERS = [f'{digit}{digit}0000{digit}{digit}{digit}' for digit in '123456789']
PINE, QUARTZ, SELF, ROCK, SLATE, TIN, CONFLICT, ZINC, TRIO = NUMBERS
UNKNOWN = NODE_PREFIX + '999999'
LABELS = [DNB_LABEL, FEDERAL_LABEL, SIZE_LABEL]
REASONS = ('naics_missing', 'naics_conflict', 'naics_not_2022', 'parent_conflict')


def form(year: int, trifd: str, node: str, parent: str = '', dnb: str = '', **fields: str) -> dict:
    '''One synthetic Form R row: not federal, in Texas, with the primary code of the node.'''
    row = dict(year=year, reporting_year=str(year), trifd=trifd, form_type='R', federal='NO',
               state='TX', primary_naics=node.removeprefix(NODE_PREFIX),
               standardized_parent=parent, parent_dnb=dnb)
    return {**row, **fields}


def excluded(reason: str, year: int, trifd: str, *parents: str) -> list[dict]:
    '''Form rows of one facility-year that is excluded for the reason, one row for each parent.'''
    names = parents or ('',)
    if reason == 'naics_missing':
        return [form(year, trifd, A, name, primary_naics='') for name in names]
    if reason == 'naics_conflict':
        return [form(year, trifd, node, name) for node in (A, B) for name in names]
    if reason == 'naics_not_2022':
        return [form(year, trifd, A, name, primary_naics='999999') for name in names]
    if reason == 'federal':
        return [form(year, trifd, A, name, federal='YES') for name in names]
    assert reason == 'parent_conflict' and len(names) > 1
    return [form(year, trifd, A, name) for name in names]


def reduced(records: list[dict]) -> pl.DataFrame:
    return reduce(rows_frame(records), LAYOUTS, NODES)


def run(records: list[dict], processed_as_of: date = DAY) -> ParentLinks:
    '''The estimate of the records, which must pass the validator.'''
    result = estimate(reduced(records), processed_as_of=processed_as_of)
    validate_parent_links(result, NODES)
    return result


def target(result: ParentLinks, a: str, b: str) -> dict:
    found = result.targets.filter((pl.col('unit_a') == a) & (pl.col('unit_b') == b))
    assert found.height == 1
    return found.row(0, named=True)


def support_row(result: ParentLinks, a: str, b: str) -> dict:
    '''The counts of the support row of a cell, without its units.'''
    found = result.support.filter((pl.col('unit_a') == a) & (pl.col('unit_b') == b))
    assert found.height == 1
    return {name: value for name, value in found.row(0, named=True).items()
            if name not in ('unit_a', 'unit_b')}


def marginal(result: ParentLinks, node: str) -> dict:
    found = result.marginals.filter(pl.col('node_id') == node)
    assert found.height == 1
    return found.row(0, named=True)


def cells(result: ParentLinks) -> set[tuple[str, str]]:
    return set(result.targets.select('unit_a', 'unit_b').rows())


def example_records() -> list[dict]:
    '''Three years, nine owners and four industries, every number of which is worked out by hand.

    Owners: Pine (parent), Quartz, Xenon, Yttrium, Wolfram, Rock, Slate and Tin are parents, and
    facility T6 owns itself. Slate and Tin each have a federal facility-year. Pine and Rock
    have a parent_conflict row, Xenon a naics_conflict row, Rock a naics_missing row, Zinc a
    naics_not_2022 row and Quartz a naics_missing row in another year than its eligible ones.
    '''
    return [
        form(2022, 'T1', A, 'Pine', PINE), form(2022, 'T2', A, 'Pine', PINE),
        form(2022, 'T3', B, 'Pine', PINE),
        form(2022, 'T4', A, 'Quartz', QUARTZ), form(2022, 'T5', B, 'Quartz', PINE),
        form(2022, 'T6', A, '', SELF),
        form(2022, 'T12', B, 'Xenon', TRIO), form(2022, 'T13', D, 'Yttrium', TRIO),
        form(2022, 'T19', C, 'Wolfram', TRIO),
        *excluded('naics_conflict', 2022, 'T17', 'Xenon'),
        form(2023, 'T1', A, 'Pine', PINE), form(2023, 'T3', B, 'Pine', PINE),
        form(2023, 'T6', A, '', SELF),
        form(2023, 'T7', A, 'Rock', ROCK), form(2023, 'T8', C, 'Rock', ROCK),
        form(2023, 'T10', D, 'Slate', SLATE),
        form(2023, 'T11', A, 'Slate', SLATE, federal='YES'),
        form(2023, 'T20', A, 'Tin', TIN), form(2023, 'T21', C, 'Tin', TIN, federal='YES'),
        *excluded('parent_conflict', 2023, 'T15', 'Pine', 'Rock'),
        *excluded('naics_not_2022', 2023, 'T18', 'Zinc'),
        *excluded('naics_missing', 2023, 'T22', 'Quartz'),
        form(2024, 'T1', C, 'Pine', PINE),
        form(2024, 'T6', A, '', SELF),
        form(2024, 'T7', A, 'Rock', ROCK), form(2024, 'T8', C, 'Rock', ROCK),
        form(2024, 'T9', B, 'Rock', ROCK),
        *excluded('naics_missing', 2024, 'T16', 'Rock'),
    ]


@pytest.fixture(scope='module')
def example() -> ParentLinks:
    return run(example_records())


def test_constants_are_the_documented_ones():
    assert CONTRACT == 'tri-parent-links-v1'
    assert YEARS == (2022, 2023, 2024)
    assert TOLERANCE == 1e-12
    assert METADATA == {
        'source': 'epa_tri', 'family': 'tri_parent_links',
        'unit_a_type': 'naics_national_industry', 'unit_b_type': 'naics_national_industry',
        'measure': 'owner_share', 'se_method': 'none', 'sample_set': 'tri_basic_ry2022_2024',
        'vintage': 'naics=2022'}
    assert (SIZE_LABEL, DNB_LABEL, FEDERAL_LABEL) == (
        'size_gate_pending', 'numerator:dnb_key_sensitivity:true',
        'numerator:federal_sensitivity:true')
    assert LABELS == sorted(LABELS)
    assert list(MARGINAL_SCHEMA.items()) == [
        ('node_id', pl.String), ('n_owners', pl.UInt64), ('n_parent_owners', pl.UInt64),
        ('n_multi_industry_owners', pl.UInt64), ('n_facilities', pl.UInt64),
        ('n_facility_years', pl.UInt64), ('n_owners_dnb', pl.UInt64),
        ('n_owners_including_federal', pl.UInt64), ('n_owners_partial', pl.UInt64)]
    assert list(SUPPORT_SCHEMA.items()) == [
        ('unit_a', pl.String), ('unit_b', pl.String), ('j_owners', pl.UInt64),
        ('j_2022', pl.UInt64), ('j_2023', pl.UInt64), ('j_2024', pl.UInt64),
        ('j_dnb', pl.UInt64), ('j_including_federal', pl.UInt64)]


def test_universe_is_the_documented_statement():
    assert UNIVERSE == (
        'EPA Toxics Release Inventory basic data files, U.S. files for reporting years '
        '2022–2024, forms processed as of {date}. TRI is a program-selected population of '
        'facilities that meet its reporting criteria, not a frame of all establishments or '
        'firms. Codes are self-reported primary NAICS 2022 codes, one per facility. A facility '
        "can contain more than one establishment. An owner is EPA's standardized highest-level "
        'U.S. parent, or the facility itself when it reports none. Federal facilities are '
        'excluded.')


def test_the_result_holds_three_typed_tables_and_a_report(example):
    assert isinstance(example, ParentLinks)
    assert list(example.targets.schema.items()) == list(target_contract.TARGET_SCHEMA.items())
    assert list(example.marginals.schema.items()) == list(MARGINAL_SCHEMA.items())
    assert list(example.support.schema.items()) == list(SUPPORT_SCHEMA.items())
    assert isinstance(example.report, dict)
    with pytest.raises(FrozenInstanceError):
        example.report = {}


def test_same_year_co_presence_counts_each_owner_once():
    # parent P: two facilities in a and one in b in 2022, and a, b again in 2023
    result = run([form(2022, 'T1', A, 'P', PINE), form(2022, 'T2', A, 'P', PINE),
                  form(2022, 'T3', B, 'P', PINE), form(2023, 'T1', A, 'P', PINE),
                  form(2023, 'T3', B, 'P', PINE)])
    for a, b in ((A, B), (B, A)):
        assert support_row(result, a, b) == {
            'j_owners': 1, 'j_2022': 1, 'j_2023': 1, 'j_2024': 0, 'j_dnb': 1,
            'j_including_federal': 1}
    assert target(result, A, B)['value'] == 1.0 and target(result, B, A)['value'] == 1.0
    assert (target(result, A, B)['n_unweighted'], target(result, A, B)['n_weighted']) == (1, 1.0)
    assert cells(result) == {(A, B), (B, A)}


def test_cross_year_presence_is_not_a_pair():
    # a in 2022 and b in 2023 for one owner: both are in n, and no cell exists
    result = run([form(2022, 'T1', A, 'P', PINE), form(2023, 'T2', B, 'P', PINE),
                  form(2024, 'T3', C, 'P', PINE)])
    assert result.targets.is_empty() and result.support.is_empty()
    assert result.marginals['node_id'].to_list() == [C, B, A]
    assert result.marginals['n_owners'].to_list() == [1, 1, 1]
    assert result.report['n_unweighted_distribution']['count'] == 0


def test_mirror_rows_and_no_diagonal():
    # P has a, b and c in 2023, and two facilities in a: six ordered cells, none with a == b
    result = run([form(2023, 'T1', A, 'P', PINE), form(2023, 'T2', A, 'P', PINE),
                  form(2023, 'T3', B, 'P', PINE), form(2023, 'T4', C, 'P', PINE)])
    assert cells(result) == {(A, B), (B, A), (A, C), (C, A), (B, C), (C, B)}
    assert all(a != b for a, b in cells(result))
    for a, b in cells(result):
        assert target(result, a, b)['n_unweighted'] == target(result, b, a)['n_unweighted']
    assert result.targets.height == result.support.height == 6


def test_self_owned_facility_counts_in_n_only():
    # facility T9 owns itself in a; P has a and b: n(a) = 2 and only P forms the cell
    result = run([form(2023, 'T9', A), form(2023, 'T1', A, 'P', PINE),
                  form(2023, 'T2', B, 'P', PINE)])
    assert cells(result) == {(A, B), (B, A)}
    assert marginal(result, A)['n_owners'] == 2
    assert marginal(result, A)['n_parent_owners'] == 1
    assert marginal(result, A)['n_multi_industry_owners'] == 1
    alone = run([form(2023, 'T9', A), form(2023, 'T8', B)])
    assert alone.targets.is_empty() and alone.support.is_empty()
    assert alone.marginals['n_owners'].to_list() == [1, 1]
    assert alone.marginals['n_parent_owners'].to_list() == [0, 0]
    assert alone.marginals['n_multi_industry_owners'].to_list() == [0, 0]


def test_value_is_j_over_n_a():
    # n(a) = 2, n(b) = 1, J = 1
    result = run([form(2023, 'T1', A, 'P', PINE), form(2023, 'T2', B, 'P', PINE),
                  form(2023, 'T3', A, 'Q', QUARTZ)])
    assert (marginal(result, A)['n_owners'], marginal(result, B)['n_owners']) == (2, 1)
    assert (target(result, A, B)['value'], target(result, B, A)['value']) == (0.5, 1.0)


def test_dnb_sensitivity_counts_and_label():
    # same D&B number, two names: no headline cell, one D&B cell in each direction, unlisted
    shared = run([form(2023, 'T1', A, 'X', PINE), form(2023, 'T2', B, 'Y', PINE)])
    assert shared.targets.is_empty() and shared.support.is_empty()
    assert shared.report['cells_only_dnb'] == 2
    assert shared.report['cells_only_federal'] == 0
    # one name, two D&B numbers: the headline cell carries the label and j_dnb is zero
    split = run([form(2023, 'T1', A, 'P', PINE), form(2023, 'T2', B, 'P', QUARTZ)])
    assert target(split, A, B)['flags'] == [DNB_LABEL, SIZE_LABEL]
    assert target(split, B, A)['flags'] == [DNB_LABEL, SIZE_LABEL]
    assert support_row(split, A, B)['j_dnb'] == 0
    assert split.report['cells_only_dnb'] == 0
    # one name, one number: the labels stay off
    same = run([form(2023, 'T1', A, 'P', PINE), form(2023, 'T2', B, 'P', PINE)])
    assert target(same, A, B)['flags'] == [SIZE_LABEL]


def test_federal_sensitivity_counts_and_label():
    # P has a eligible and b federal: no headline cell, one federal cell each way, unlisted
    only = run([form(2023, 'T1', A, 'P', PINE), form(2023, 'T2', B, 'P', QUARTZ, federal='YES')])
    assert only.targets.is_empty() and only.support.is_empty()
    assert only.report['cells_only_federal'] == 2
    assert only.report['cells_only_dnb'] == 0
    # Q has a and b eligible. S has a eligible and b federal: the federal J is 2, the J is 1
    extra = run([form(2023, 'T3', A, 'Q', ROCK), form(2023, 'T4', B, 'Q', ROCK),
                 form(2023, 'T5', A, 'S', SLATE), form(2023, 'T6', B, 'S', TIN, federal='YES')])
    assert target(extra, A, B)['flags'] == [FEDERAL_LABEL, SIZE_LABEL]
    assert target(extra, B, A)['flags'] == [FEDERAL_LABEL, SIZE_LABEL]
    assert support_row(extra, A, B)['j_including_federal'] == 2
    assert support_row(extra, A, B)['j_owners'] == 1
    assert extra.report['cells_only_federal'] == 0
    assert marginal(extra, A)['n_owners_including_federal'] == 2
    assert marginal(extra, B)['n_owners_including_federal'] == 2
    assert marginal(extra, B)['n_owners'] == 1


def test_partial_owners_count_conflicts_for_each_named_parent():
    # T3 in 2023 names P and Q: P and Q are partial for their 2023 nodes. A federal exclusion
    # of R and an exclusion of S in 2024 are not partial. An excluded self-owned facility
    # belongs to no parent.
    result = run([
        form(2023, 'T1', A, 'P', PINE), form(2023, 'T2', B, 'Q', QUARTZ),
        *excluded('parent_conflict', 2023, 'T3', 'P', 'Q'),
        form(2023, 'T4', A, 'R', ROCK), *excluded('federal', 2023, 'T5', 'R'),
        form(2023, 'T6', A, 'S', SLATE), *excluded('naics_missing', 2024, 'T7', 'S'),
        *excluded('naics_missing', 2023, 'T9')])
    assert result.marginals.select('node_id', 'n_owners', 'n_owners_partial').rows() == [
        (B, 1, 1), (A, 3, 1)]
    assert result.report['partial_owners'] == 2


@pytest.mark.parametrize('reason', REASONS)
def test_each_partial_reason_makes_the_named_owner_partial(reason):
    names = ('P', 'Q') if reason == 'parent_conflict' else ('P',)
    records = [form(2023, 'T1', A, 'P', PINE), *excluded(reason, 2023, 'T2', *names)]
    assert reason in reduced(records)['exclusion_reason'].to_list()
    result = run(records)
    assert marginal(result, A)['n_owners_partial'] == 1
    assert result.report['partial_owners'] == 1


def test_a_federal_exclusion_never_makes_an_owner_partial():
    records = [form(2023, 'T1', A, 'P', PINE), *excluded('federal', 2023, 'T2', 'P')]
    assert 'federal' in reduced(records)['exclusion_reason'].to_list()
    result = run(records)
    assert marginal(result, A)['n_owners_partial'] == 0
    assert result.report['partial_owners'] == 0


def test_every_named_parent_of_an_excluded_facility_year_is_partial():
    # a facility-year without a code and with two parents is excluded as naics_missing, and it
    # still belongs to both of its parents through the membership keys
    records = [form(2023, 'T1', A, 'P', PINE), form(2023, 'T2', B, 'Q', QUARTZ),
               *excluded('naics_missing', 2023, 'T3', 'P', 'Q')]
    result = run(records)
    assert marginal(result, A)['n_owners_partial'] == 1
    assert marginal(result, B)['n_owners_partial'] == 1
    assert result.report['partial_owners'] == 2


def test_partiality_needs_the_same_year_and_is_counted_per_node():
    # P is in a in 2022 and in b in 2023, and has an excluded facility-year in 2023: partial
    # for b only. Q is in a in 2022 and 2023 and is excluded in both years and twice in 2023:
    # one owner, partial for a once.
    result = run([
        form(2022, 'T1', A, 'P', PINE), form(2023, 'T2', B, 'P', PINE),
        *excluded('naics_missing', 2023, 'T3', 'P'),
        form(2022, 'T4', A, 'Q', QUARTZ), form(2023, 'T4', A, 'Q', QUARTZ),
        *excluded('naics_missing', 2022, 'T5', 'Q'), *excluded('naics_missing', 2023, 'T6', 'Q'),
        *excluded('naics_not_2022', 2023, 'T7', 'Q')])
    assert result.marginals.select('node_id', 'n_owners_partial').rows() == [(B, 1), (A, 1)]
    assert result.report['partial_owners'] == 2


def test_partiality_reads_the_headline_presence_only():
    # P is in a, is in b only through a federal facility-year, and has an excluded
    # facility-year: partial for a, not for b, where Q is the one owner
    result = run([form(2023, 'T1', A, 'P', PINE), form(2023, 'T2', B, 'P', QUARTZ, federal='YES'),
                  *excluded('naics_missing', 2023, 'T3', 'P'), form(2023, 'T4', B, 'Q', ROCK)])
    assert result.marginals.select('node_id', 'n_owners', 'n_owners_partial').rows() == [
        (B, 1, 0), (A, 1, 1)]


def test_an_owner_partial_for_two_nodes_counts_once_in_the_report():
    result = run([form(2023, 'T1', A, 'P', PINE), form(2023, 'T2', B, 'P', PINE),
                  *excluded('naics_missing', 2023, 'T3', 'P')])
    assert result.marginals['n_owners_partial'].to_list() == [1, 1]
    assert result.report['partial_owners'] == 1


def test_a_facility_year_owned_by_a_facility_is_never_partial():
    # an excluded facility with no parent has the key facility:T2, and no eligible
    # facility-year of the same year can carry it
    result = run([form(2023, 'T1', A), *excluded('naics_missing', 2023, 'T2')])
    assert marginal(result, A)['n_owners_partial'] == 0
    assert result.report['partial_owners'] == 0


def test_name_spellings_join_only_after_the_strip():
    # ' Acme Corp ' (a) and 'Acme Corp' (b) in 2023 are one owner. 'ACME CORP' (c) is another
    result = run([form(2023, 'T1', A, ' Acme Corp ', PINE), form(2023, 'T2', B, 'Acme Corp', PINE),
                  form(2023, 'T3', C, 'ACME CORP', QUARTZ)])
    assert support_row(result, A, B)['j_owners'] == 1
    assert cells(result) == {(A, B), (B, A)}
    assert result.report['parent_name_collisions'] == {'keys': 1, 'names': 2}


def test_metadata_flags_and_universe(example):
    for row in example.targets.rows(named=True):
        assert row['flags'] == sorted(row['flags'])
        assert row['universe'] == UNIVERSE.format(date='2025-11-05')
        assert row['se'] is None
        assert {name: row[name] for name in METADATA} == METADATA
    other = run([form(2023, 'T1', A, 'P', PINE), form(2023, 'T2', B, 'P', PINE)],
                processed_as_of=date(2026, 1, 31))
    assert other.targets['universe'].unique().to_list() == [UNIVERSE.format(date='2026-01-31')]


def test_the_hand_computed_example_matches_every_table_and_the_report(example):
    # Presence, headline: 2022 Pine {A,B}, Quartz {A,B}, T6 {A}, Xenon {B}, Yttrium {D},
    # Wolfram {C}; 2023 Pine {A,B}, T6 {A}, Rock {A,C}, Slate {D}, Tin {A};
    # 2024 Pine {C}, T6 {A}, Rock {A,B,C}.
    third = 1 / 3
    assert example.targets.select(
        'unit_a', 'unit_b', 'value', 'n_unweighted', 'n_weighted', 'flags').rows() == [
        (C, B, third, 1, 1.0, [DNB_LABEL, SIZE_LABEL]),
        (C, A, third, 1, 1.0, [FEDERAL_LABEL, SIZE_LABEL]),
        (B, C, 0.25, 1, 1.0, [DNB_LABEL, SIZE_LABEL]),
        (B, A, 0.75, 3, 3.0, [DNB_LABEL, SIZE_LABEL]),
        (A, C, 0.2, 1, 1.0, [FEDERAL_LABEL, SIZE_LABEL]),
        (A, B, 0.6, 3, 3.0, [DNB_LABEL, SIZE_LABEL])]
    assert example.support.rows() == [
        (C, B, 1, 0, 0, 1, 2, 1), (C, A, 1, 0, 1, 1, 1, 2), (B, C, 1, 0, 0, 1, 2, 1),
        (B, A, 3, 2, 1, 1, 2, 3), (A, C, 1, 0, 1, 1, 1, 2), (A, B, 3, 2, 1, 1, 2, 3)]
    assert example.marginals.rows() == [
        (C, 3, 3, 1, 3, 4, 3, 4, 1),
        (D, 2, 2, 0, 2, 2, 2, 2, 0),
        (B, 4, 4, 3, 4, 5, 3, 4, 3),
        (A, 5, 4, 3, 6, 10, 5, 6, 2)]
    assert example.report == {
        'n_owners': {'headline': 9, 'dnb': 7, 'federal': 9},
        'owners_by_year': {
            '2022': {'headline': 6, 'dnb': 4, 'federal': 6},
            '2023': {'headline': 5, 'dnb': 5, 'federal': 5},
            '2024': {'headline': 3, 'dnb': 3, 'federal': 3}},
        'partial_owners': 3,
        'cells_only_dnb': 4,
        'cells_only_federal': 2,
        'n_unweighted_distribution': {
            'count': 6, 'min': 1, 'p25': 1, 'median': 1, 'p75': 3, 'p90': 3, 'max': 3,
            'ge_1': 6, 'ge_2': 2, 'ge_3': 2, 'ge_5': 0, 'ge_10': 0},
        'owner_key_changes': 0,
        'parent_name_collisions': {'keys': 0, 'names': 0}}


def test_the_three_presence_variants_use_their_own_keys():
    # Cell (a, b): P gives headline J 1. X and Y share a D&B number across two names and give
    # D&B J 2. F and G each have a federal b and give federal J 3.
    result = run([
        form(2023, 'T1', A, 'P', PINE), form(2023, 'T2', B, 'P', QUARTZ),
        form(2023, 'T3', A, 'Xa', SELF), form(2023, 'T4', B, 'Xb', SELF),
        form(2023, 'T9', A, 'Ya', ROCK), form(2023, 'T10', B, 'Yb', ROCK),
        form(2023, 'T5', A, 'F', SLATE), form(2023, 'T6', B, 'F', TIN, federal='YES'),
        form(2023, 'T7', A, 'G', CONFLICT), form(2023, 'T8', B, 'G', ZINC, federal='YES')])
    assert support_row(result, A, B) == {
        'j_owners': 1, 'j_2022': 0, 'j_2023': 1, 'j_2024': 0, 'j_dnb': 2,
        'j_including_federal': 3}
    assert target(result, A, B)['flags'] == [DNB_LABEL, FEDERAL_LABEL, SIZE_LABEL]
    assert target(result, A, B)['value'] == 1 / 5 and target(result, B, A)['value'] == 1 / 3
    assert result.marginals.select(
        'node_id', 'n_owners', 'n_owners_dnb', 'n_owners_including_federal').rows() == [
        (B, 3, 3, 5), (A, 5, 5, 5)]
    assert result.report['n_owners'] == {'headline': 7, 'dnb': 6, 'federal': 7}
    assert result.report['cells_only_dnb'] == 0 and result.report['cells_only_federal'] == 0


def test_the_sensitivities_read_only_the_rows_they_name():
    # P has a in T1. T2 is R's federal b and T3 names two parents in b, and both carry P's D&B
    # number: D&B reads eligible rows only, so it forms no cell. Federal adds the federal
    # exclusion and no other: R is not P, so it forms no cell either. The other exclusions have
    # no node, and a variant that read them would raise on the null.
    result = run([
        form(2023, 'T1', A, 'P', PINE), form(2023, 'T2', B, 'R', PINE, federal='YES'),
        form(2023, 'T3', B, 'Q', PINE), form(2023, 'T3', B, 'S', PINE),
        *excluded('naics_missing', 2023, 'T4', 'P'), *excluded('naics_conflict', 2023, 'T5', 'P'),
        *excluded('naics_not_2022', 2023, 'T6', 'P')])
    assert result.targets.is_empty() and result.support.is_empty()
    assert result.report['cells_only_dnb'] == 0 and result.report['cells_only_federal'] == 0
    assert result.report['n_owners'] == {'headline': 1, 'dnb': 1, 'federal': 2}


def federal_first(reason: str) -> list[dict]:
    '''Form rows of the federal facility-year T2 of 2023 that an earlier rule excludes first.

    T2 names P (and Q for a parent conflict) and carries the federal flag on every form.
    '''
    if reason == 'naics_missing':
        return [form(2023, 'T2', B, 'P', QUARTZ, federal='YES', primary_naics='')]
    if reason == 'naics_conflict':
        return [form(2023, 'T2', node, 'P', QUARTZ, federal='YES') for node in (A, B)]
    if reason == 'naics_not_2022':
        return [form(2023, 'T2', B, 'P', QUARTZ, federal='YES', primary_naics='999999')]
    assert reason == 'parent_conflict'
    return [form(2023, 'T2', B, name, QUARTZ, federal='YES') for name in ('P', 'Q')]


@pytest.mark.parametrize('reason, partial_a, partial_b, partial_owners', [
    ('naics_missing', 1, 0, 1), ('naics_conflict', 1, 0, 1), ('naics_not_2022', 1, 0, 1),
    ('parent_conflict', 2, 1, 2)])
def test_a_federal_facility_year_that_an_earlier_rule_excludes_is_not_a_federal_row(
        reason, partial_a, partial_b, partial_owners):
    # Spec 411 adds the facility-years excluded only as federal. T2 has the federal flag, but
    # its reason is the earlier rule, so the federal sensitivity leaves it out: no owner, no
    # node and no raise. By hand: P in a (T1); Q in a (T3) and b (T4) with one D&B number.
    # Headline n(a) = 2 (P, Q) and n(b) = 1 (Q), so J(a, b) = 1: value 1/2 and 1. The D&B owners
    # are P's number and Q's number (2), the federal owners are P and Q (2), and the
    # sensitivities add no cell. T2 is excluded, so it is in no facility count. T2 names P
    # (and Q for a parent conflict) in 2023: P (and Q) is partial for the 2023 nodes.
    records = [form(2023, 'T1', A, 'P', PINE), form(2023, 'T3', A, 'Q', ROCK),
               form(2023, 'T4', B, 'Q', ROCK), *federal_first(reason)]
    row = reduced(records).filter(pl.col('trifd') == 'T2').row(0, named=True)
    assert (row['exclusion_reason'], row['federal_values']) == (reason, ['YES'])
    result = run(records)
    assert result.targets.select('unit_a', 'unit_b', 'value', 'n_unweighted', 'flags').rows() == [
        (B, A, 1.0, 1, [SIZE_LABEL]), (A, B, 0.5, 1, [SIZE_LABEL])]
    assert result.support.rows() == [(B, A, 1, 0, 1, 0, 1, 1), (A, B, 1, 0, 1, 0, 1, 1)]
    assert result.marginals.rows() == [
        (B, 1, 1, 1, 1, 1, 1, 1, partial_b), (A, 2, 2, 1, 2, 2, 2, 2, partial_a)]
    assert result.report['n_owners'] == {'headline': 2, 'dnb': 2, 'federal': 2}
    assert result.report['cells_only_dnb'] == 0 and result.report['cells_only_federal'] == 0
    assert result.report['partial_owners'] == partial_owners


def test_a_federal_facility_year_with_no_code_still_has_its_parent_partial():
    # the reviewer's case: P in a, and T2 federal with no code in b. Nothing forms a cell.
    records = [form(2023, 'T1', A, 'P', PINE), *federal_first('naics_missing')]
    result = run(records)
    assert result.targets.is_empty() and result.support.is_empty()
    assert result.report['n_owners'] == {'headline': 1, 'dnb': 1, 'federal': 1}
    assert result.report['cells_only_federal'] == 0
    assert marginal(result, A)['n_owners_partial'] == 1
    assert result.report['partial_owners'] == 1


def test_an_owner_present_in_all_three_years_counts_once_in_j_and_once_a_year():
    records = [form(year, f'T{year}{node[-1]}', node, 'P', PINE)
               for year in YEARS for node in (A, B)]
    result = run(records)
    assert support_row(result, A, B) == {
        'j_owners': 1, 'j_2022': 1, 'j_2023': 1, 'j_2024': 1, 'j_dnb': 1,
        'j_including_federal': 1}
    assert marginal(result, A)['n_owners'] == 1


@pytest.mark.parametrize('years, expected', [
    ((2022, 2024), (1, 0, 1)), ((2023,), (0, 1, 0)), ((2022, 2023, 2024), (1, 1, 1))])
def test_each_year_column_counts_the_years_of_co_presence(years, expected):
    result = run([form(year, f'T{year}{node[-1]}', node, 'P', PINE)
                  for year in years for node in (A, B)])
    row = support_row(result, A, B)
    assert (row['j_2022'], row['j_2023'], row['j_2024']) == expected
    assert row['j_owners'] == 1


def test_different_owners_in_different_years_add_up():
    result = run([form(2022, 'T1', A, 'P', PINE), form(2022, 'T2', B, 'P', PINE),
                  form(2023, 'T3', A, 'Q', QUARTZ), form(2023, 'T4', B, 'Q', QUARTZ),
                  form(2024, 'T5', A, 'R', ROCK), form(2024, 'T6', B, 'R', ROCK),
                  form(2024, 'T7', A, 'S', SLATE), form(2024, 'T8', B, 'S', SLATE)])
    row = support_row(result, A, B)
    assert (row['j_owners'], row['j_2022'], row['j_2023'], row['j_2024']) == (4, 1, 1, 2)
    assert target(result, A, B)['n_unweighted'] == 4
    assert target(result, A, B)['value'] == 1.0


def test_many_facilities_forms_and_years_count_an_owner_once_in_n_and_each_row_in_the_counts():
    records = [form(year, trifd, A, 'P', PINE)
               for year in YEARS for trifd in ('T1', 'T2', 'T3')]
    records += [form(2023, 'T1', A, 'P', PINE, form_type='A'), form(2023, 'T1', A, 'P', PINE)]
    row = marginal(run(records), A)
    assert (row['n_owners'], row['n_facilities'], row['n_facility_years']) == (1, 3, 9)


def test_facility_counts_are_per_node_and_count_the_repeats_across_years():
    result = run([form(2022, 'T1', A, 'P', PINE), form(2023, 'T1', A, 'P', PINE),
                  form(2023, 'T2', A, 'Q', QUARTZ), form(2024, 'T3', B, 'P', PINE)])
    assert result.marginals.select('node_id', 'n_facilities', 'n_facility_years').rows() == [
        (B, 1, 1), (A, 2, 3)]


def test_multi_industry_owners_need_two_industries_in_one_year():
    result = run([
        form(2022, 'T1', A, 'P', PINE), form(2022, 'T2', B, 'P', PINE),
        form(2022, 'T3', A, 'Q', QUARTZ), form(2023, 'T4', B, 'Q', QUARTZ),
        form(2023, 'T5', A, 'R', ROCK), form(2024, 'T6', A, 'S', SLATE)])
    assert result.marginals.select('node_id', 'n_owners', 'n_multi_industry_owners').rows() == [
        (B, 2, 1), (A, 4, 1)]


def test_parent_owners_are_the_owners_keyed_by_a_parent_name():
    result = run([form(2022, 'T1', A, 'P', PINE), form(2023, 'T1', A, 'P', PINE),
                  form(2023, 'T2', A, 'Q', QUARTZ), form(2022, 'T3', A), form(2023, 'T3', A),
                  form(2023, 'T4', A)])
    row = marginal(result, A)
    assert (row['n_owners'], row['n_parent_owners']) == (4, 2)


def test_marginals_cover_every_node_with_an_owner_and_are_sorted_by_node_id():
    result = run([form(2022, 'T1', A, 'P', PINE), form(2022, 'T2', B, 'Q', QUARTZ),
                  form(2022, 'T3', D), form(2022, 'T4', C, 'R', ROCK)])
    assert result.targets.is_empty()
    assert result.marginals['node_id'].to_list() == sorted(NODES)
    assert result.marginals['n_owners'].to_list() == [1, 1, 1, 1]


@pytest.mark.parametrize('reason', (*REASONS, 'federal'))
def test_an_excluded_facility_year_never_enters_the_headline_counts(reason):
    names = ('P', 'Q') if reason == 'parent_conflict' else ('P',)
    records = [form(2023, 'T1', A, 'Z', ZINC), form(2023, 'T3', B, 'Y', TIN),
               *excluded(reason, 2023, 'T2', *names)]
    assert reason in reduced(records)['exclusion_reason'].to_list()
    result = run(records)
    assert result.marginals['n_owners'].to_list() == [1, 1]
    assert result.marginals['n_facility_years'].to_list() == [1, 1]
    assert result.report['n_owners']['headline'] == 2


def test_owner_key_changes_count_trifds_whose_eligible_owner_key_differs():
    result = run([
        # T1 changes parent between years: counted once
        form(2022, 'T1', A, 'P', PINE), form(2023, 'T1', A, 'Q', QUARTZ),
        form(2024, 'T1', A, 'R', ROCK),
        # T2 keeps one parent: not counted
        form(2022, 'T2', A, 'P', PINE), form(2024, 'T2', A, 'P', PINE),
        # T3 goes from a parent to none: counted
        form(2022, 'T3', B, 'P', PINE), form(2023, 'T3', B),
        # T4 is eligible in one year only: not counted
        form(2023, 'T4', B, 'Q', QUARTZ), *excluded('naics_missing', 2024, 'T4', 'R'),
        # T5 changes key through an excluded year only: the excluded year is ignored
        form(2022, 'T5', C, 'P', PINE), *excluded('naics_missing', 2023, 'T5', 'Q'),
        form(2024, 'T5', C, 'P', PINE),
        # T6 has no parent in any year: facility:T6 each time, not counted
        form(2022, 'T6', C), form(2023, 'T6', C), form(2024, 'T6', C),
        # T7 keeps its parent and changes its D&B number: the owner key is the same
        form(2022, 'T7', C, 'P', PINE), form(2024, 'T7', C, 'P', QUARTZ),
        # T8 changes its parent and keeps its D&B number: the owner key differs
        form(2022, 'T8', D, 'P', PINE), form(2023, 'T8', D, 'Q', PINE),
        form(2022, 'T9', B, 'P', PINE), form(2023, 'T9', B, 'Q', PINE)])
    assert result.report['owner_key_changes'] == 4


def test_the_n_unweighted_distribution_is_taken_over_the_target_rows():
    # four owners share the cell (a, b): two target rows, each with J = 4
    result = run([form(2023, f'T{owner}{node[-1]}', node, f'P{owner}')
                  for owner in range(4) for node in (A, B)])
    assert result.targets['n_unweighted'].to_list() == [4, 4]
    assert result.report['n_unweighted_distribution'] == {
        'count': 2, 'min': 4, 'p25': 4, 'median': 4, 'p75': 4, 'p90': 4, 'max': 4,
        'ge_1': 2, 'ge_2': 2, 'ge_3': 2, 'ge_5': 0, 'ge_10': 0}


@pytest.mark.parametrize('values, expected', [
    ([], {'count': 0, 'min': None, 'p25': None, 'median': None, 'p75': None, 'p90': None,
          'max': None, 'ge_1': 0, 'ge_2': 0, 'ge_3': 0, 'ge_5': 0, 'ge_10': 0}),
    ([7], {'count': 1, 'min': 7, 'p25': 7, 'median': 7, 'p75': 7, 'p90': 7, 'max': 7,
           'ge_1': 1, 'ge_2': 1, 'ge_3': 1, 'ge_5': 1, 'ge_10': 0}),
    ([4, 1, 3, 2], {'count': 4, 'min': 1, 'p25': 1, 'median': 2, 'p75': 3, 'p90': 4, 'max': 4,
                    'ge_1': 4, 'ge_2': 3, 'ge_3': 2, 'ge_5': 0, 'ge_10': 0}),
    (list(range(10, 0, -1)), {
        'count': 10, 'min': 1, 'p25': 3, 'median': 5, 'p75': 8, 'p90': 9, 'max': 10,
        'ge_1': 10, 'ge_2': 9, 'ge_3': 8, 'ge_5': 6, 'ge_10': 1}),
    (list(range(1, 12)), {
        'count': 11, 'min': 1, 'p25': 3, 'median': 6, 'p75': 9, 'p90': 10, 'max': 11,
        'ge_1': 11, 'ge_2': 10, 'ge_3': 9, 'ge_5': 7, 'ge_10': 2}),
    (list(range(100, 0, -1)), {
        'count': 100, 'min': 1, 'p25': 25, 'median': 50, 'p75': 75, 'p90': 90, 'max': 100,
        'ge_1': 100, 'ge_2': 99, 'ge_3': 98, 'ge_5': 96, 'ge_10': 91}),
    ([5, 5, 5, 20], {'count': 4, 'min': 5, 'p25': 5, 'median': 5, 'p75': 5, 'p90': 20,
                     'max': 20, 'ge_1': 4, 'ge_2': 4, 'ge_3': 4, 'ge_5': 4, 'ge_10': 1})])
def test_distribution_uses_nearest_rank_percentiles_and_cumulative_counts(values, expected):
    assert distribution(values) == expected
    assert distribution(sorted(values, reverse=True)) == expected


def test_distribution_values_are_plain_integers():
    for value in distribution([3, 1, 2]).values():
        assert type(value) is int


@pytest.mark.parametrize('names, expected', [
    ([], {'keys': 0, 'names': 0}),
    (['Acme Corp'], {'keys': 0, 'names': 0}),
    (['Acme Corp', 'ACME CORP'], {'keys': 1, 'names': 2}),
    (['Acme Corp', 'ACME CORP', 'acme corp'], {'keys': 1, 'names': 3}),
    (['Acme Corp', 'Acme Corp', 'Acme Corp'], {'keys': 0, 'names': 0}),
    (['Acme Corp', 'ACME CORP', 'ACME CORP'], {'keys': 1, 'names': 2}),
    (['Acme Corp', 'Beta Inc', 'ACME CORP', 'beta inc', 'Gamma'], {'keys': 2, 'names': 4}),
    (['Acme  Corp', 'Acme Corp'], {'keys': 1, 'names': 2}),
    (['Acme\tCorp', 'Acme Corp', 'Acme Corp'], {'keys': 1, 'names': 3}),
    (['Straße', 'STRASSE'], {'keys': 1, 'names': 2}),
    ([' Acme Corp', 'Acme Corp '], {'keys': 1, 'names': 2}),
    (['Acme Corp', 'Acme-Corp'], {'keys': 0, 'names': 0})])
def test_name_collisions_group_distinct_names_by_casefold_and_collapsed_whitespace(
        names, expected):
    assert name_collisions(names) == expected
    assert name_collisions(iter(names)) == expected


def test_parent_name_collisions_read_the_names_of_every_facility_year():
    # the excluded facility-year names 'ACME' too: the collision counts excluded rows
    result = run([form(2023, 'T1', A, 'Acme', PINE), form(2023, 'T2', B, 'Beta', QUARTZ),
                  *excluded('naics_missing', 2023, 'T3', 'ACME')])
    assert result.report['parent_name_collisions'] == {'keys': 1, 'names': 2}


@pytest.mark.parametrize('year', [2021, 2025, 1999, 0, None])
def test_a_year_outside_the_window_raises_a_fixed_message(year):
    frame = reduced([form(2022, 'T1', A, 'P', PINE), form(2023, 'T2', B, 'P', PINE)])
    shifted = frame.with_columns(
        pl.when(pl.col('trifd') == 'T2').then(pl.lit(year, dtype=pl.Int64))
        .otherwise(pl.col('reporting_year'))
        .alias('reporting_year'))
    with pytest.raises(ValueError, match='^reporting year outside the window$'):
        estimate(shifted, processed_as_of=DAY)


@pytest.mark.parametrize('column, trifd', [
    ('owner_key', 'T1'), ('naics_2022_node_id', 'T1'), ('_dnb_key', 'T1'),
    ('_candidate_key', 'T1'), ('_candidate_key', 'T2'), ('naics_2022_node_id', 'T2')])
def test_a_null_owner_or_node_in_a_counted_row_raises_a_fixed_message(column, trifd):
    frame = reduced([form(2023, 'T1', A, 'P', PINE),
                     form(2023, 'T2', B, 'P', PINE, federal='YES')])
    broken = frame.with_columns(
        pl.when(pl.col('trifd') == trifd).then(None).otherwise(pl.col(column)).alias(column))
    with pytest.raises(ValueError, match='^owner or node is null$'):
        estimate(broken, processed_as_of=DAY)


def test_a_null_key_on_a_row_no_variant_counts_is_ignored():
    # an excluded row has a null owner_key by design, and the D&B variant never reads its keys
    frame = reduced([form(2023, 'T1', A, 'P', PINE), *excluded('naics_missing', 2023, 'T2', 'P')])
    broken = frame.with_columns(
        pl.when(pl.col('trifd') == 'T2').then(None).otherwise(pl.col('_dnb_key'))
        .alias('_dnb_key'))
    assert estimate(broken, processed_as_of=DAY).marginals.height == 1


def test_an_empty_frame_gives_empty_typed_tables_and_a_zero_report():
    result = run([])
    assert result.targets.is_empty() and result.marginals.is_empty() and result.support.is_empty()
    assert list(result.targets.schema.items()) == list(target_contract.TARGET_SCHEMA.items())
    assert list(result.marginals.schema.items()) == list(MARGINAL_SCHEMA.items())
    assert list(result.support.schema.items()) == list(SUPPORT_SCHEMA.items())
    assert result.report['n_owners'] == {'headline': 0, 'dnb': 0, 'federal': 0}
    assert result.report['owners_by_year']['2023'] == {'headline': 0, 'dnb': 0, 'federal': 0}
    assert result.report['partial_owners'] == 0
    assert result.report['owner_key_changes'] == 0
    assert result.report['parent_name_collisions'] == {'keys': 0, 'names': 0}
    assert result.report['n_unweighted_distribution'] == distribution([])


def test_a_frame_of_self_owned_facilities_gives_marginals_and_no_targets():
    result = run([form(2022, 'T1', A), form(2023, 'T2', B)])
    assert result.targets.is_empty() and result.support.is_empty()
    assert list(result.targets.schema.items()) == list(target_contract.TARGET_SCHEMA.items())
    assert list(result.support.schema.items()) == list(SUPPORT_SCHEMA.items())
    assert list(result.marginals.schema.items()) == list(MARGINAL_SCHEMA.items())
    assert result.marginals.height == 2


def test_a_frame_of_only_excluded_facility_years_has_no_owner():
    result = run(excluded('naics_missing', 2023, 'T1', 'P') + excluded('federal', 2023, 'T2', 'P'))
    assert result.marginals.is_empty() and result.targets.is_empty()
    assert result.report['n_owners'] == {'headline': 0, 'dnb': 0, 'federal': 1}
    assert result.report['partial_owners'] == 0


def test_the_estimate_does_not_depend_on_the_input_order(example):
    frame = reduced(example_records())
    for other in (frame.reverse(), frame.sample(fraction=1.0, shuffle=True, seed=5)):
        again = estimate(other, processed_as_of=DAY)
        assert again.targets.equals(example.targets)
        assert again.marginals.equals(example.marginals)
        assert again.support.equals(example.support)
        assert again.report == example.report


def test_the_report_is_plain_json(example):
    text = json.dumps(example.report, sort_keys=True)
    assert json.loads(text) == example.report

    def leaves(value):
        if isinstance(value, dict):
            assert all(type(key) is str for key in value)
            for item in value.values():
                yield from leaves(item)
        else:
            yield value

    assert all(type(leaf) is int for leaf in leaves(example.report))
    assert set(example.report['owners_by_year']) == {'2022', '2023', '2024'}


def test_no_dnb_number_reaches_any_output_or_message(example):
    texts = [str(example.targets.rows()), str(example.marginals.rows()),
             str(example.support.rows()), json.dumps(example.report)]
    broken = replace(example, support=example.support.head(2))
    with pytest.raises(ValueError) as failure:
        validate_parent_links(broken, NODES)
    with pytest.raises(ValueError) as shifted:
        estimate(reduced(example_records()).with_columns(pl.col('reporting_year') + 5),
                 processed_as_of=DAY)
    texts += [str(failure.value), str(shifted.value)]
    for number in NUMBERS:
        assert not any(number in text for text in texts)
    assert any(PINE in str(row) for row in reduced(example_records()).rows())


# ---- validator -----------------------------------------------------------------------------


def edit(frame: pl.DataFrame, keys: dict, **columns) -> pl.DataFrame:
    '''The frame with columns set on the rows whose columns equal `keys`.'''
    mask = pl.all_horizontal([pl.col(name) == value for name, value in keys.items()])
    return frame.with_columns(*(
        pl.when(mask).then(pl.lit(value, dtype=frame.schema[name])).otherwise(pl.col(name))
        .alias(name) for name, value in columns.items()))


def at(a: str, b: str) -> dict:
    return {'unit_a': a, 'unit_b': b}


def only(frame: pl.DataFrame, a: str, b: str) -> pl.DataFrame:
    '''The frame without the row of the cell.'''
    return frame.filter(~((pl.col('unit_a') == a) & (pl.col('unit_b') == b)))


MESSAGES = {
    'no_mirror': 'cell has no mirror',
    'mirror_count': 'cell has no mirror',
    'diagonal': 'diagonal cell',
    'j_above_min': 'cell count above an owner count',
    'value': 'value differs from the cell count over the owner count',
    'unknown_node': 'unit is not a selected node',
    'support_differs': 'support rows differ from the target cells',
    'marginal_differs': 'value differs from the cell count over the owner count',
}


def break_one(example: ParentLinks, kind: str) -> tuple[ParentLinks, frozenset[str]]:
    '''A copy of the example result with one clause broken, and the node IDs to check against.'''
    targets, marginals, support, nodes = (
        example.targets, example.marginals, example.support, NODES)
    if kind == 'no_mirror':
        targets = only(targets, B, A)
    elif kind == 'mirror_count':
        targets = edit(targets, at(A, B), n_unweighted=2, n_weighted=2.0, value=0.4)
    elif kind == 'diagonal':
        row = edit(targets, at(A, B), unit_b=A).filter(pl.col('unit_a') == pl.col('unit_b'))
        targets = pl.concat([targets, row])
    elif kind == 'j_above_min':
        marginals = edit(marginals, {'node_id': B}, n_owners=2)
        targets = edit(targets, {'unit_a': B, 'unit_b': A}, value=1.5)
        targets = edit(targets, {'unit_a': B, 'unit_b': C}, value=0.5)
    elif kind == 'value':
        targets = edit(targets, at(A, B), value=0.61)
    elif kind == 'unknown_node':
        nodes = NODES - {C}
    elif kind == 'support_differs':
        support = only(support, A, C)
    elif kind == 'marginal_differs':
        marginals = edit(marginals, {'node_id': A}, n_owners=6)
    return replace(example, targets=targets, marginals=marginals, support=support), nodes


@pytest.mark.parametrize('break_', ['no_mirror', 'diagonal', 'j_above_min', 'value',
                                    'unknown_node', 'support_differs', 'marginal_differs'])
def test_validator_rejects(example, break_):
    result, nodes = break_one(example, break_)
    with pytest.raises(ValueError, match=f'^{MESSAGES[break_]}$'):
        validate_parent_links(result, nodes)


def test_the_diagonal_break_really_has_a_diagonal_row(example):
    result, _ = break_one(example, 'diagonal')
    assert result.targets.filter(pl.col('unit_a') == pl.col('unit_b')).height == 1


def test_the_validator_accepts_the_example_and_other_valid_results(example):
    validate_parent_links(example, NODES)
    validate_parent_links(run([]), NODES)
    validate_parent_links(run([form(2023, 'T1', A)]), NODES)
    validate_parent_links(example, NODES | {'naics:2022:national_industry:999999'})
    # the order of the target rows is not the validator's concern, and the support is sorted
    validate_parent_links(replace(example, targets=example.targets.reverse()), NODES)


def test_the_validator_rejects_a_mirror_with_another_count(example):
    result, nodes = break_one(example, 'mirror_count')
    with pytest.raises(ValueError, match='^cell has no mirror$'):
        validate_parent_links(result, nodes)


def test_the_validator_runs_validate_targets_first(example):
    result = replace(example, targets=example.targets.drop('flags'))
    with pytest.raises(ValueError, match='^targets schema must match'):
        validate_parent_links(result, NODES)
    result = replace(example, targets=example.targets.with_columns(
        pl.lit(float('nan')).alias('value')))
    with pytest.raises(ValueError, match='^targets contain nonfinite value$'):
        validate_parent_links(result, NODES)


METADATA_BREAKS = {
    'source': {'source': 'other'},
    'family': {'family': 'other'},
    'measure': {'measure': 'other'},
    'sample_set': {'sample_set': 'other'},
    'vintage': {'vintage': 'naics=2017'},
    'se_method': {'se_method': 'replicate', 'se': 0.1},
    'unit_a_type': {'unit_a_type': 'naics_sector', 'unit_a': 'naics:2022:sector:11'},
    'unit_b_type': {'unit_b_type': 'naics_sector', 'unit_b': 'naics:2022:sector:11'},
}


@pytest.mark.parametrize('column', list(METADATA_BREAKS))
def test_the_validator_rejects_other_metadata_in_one_row(example, column):
    assert set(METADATA_BREAKS) == set(METADATA)
    result = replace(example, targets=edit(example.targets, at(A, B), **METADATA_BREAKS[column]))
    with pytest.raises(ValueError, match='^targets metadata differs$'):
        validate_parent_links(result, NODES)


@pytest.mark.parametrize('universe', [
    'No date', UNIVERSE.format(date='5 Nov 2025'), UNIVERSE.format(date='2025-13-45'),
    UNIVERSE.format(date='20251105'), UNIVERSE.format(date='') + '.', UNIVERSE.format(date=DAY)
    + ' ', ' ' + UNIVERSE.format(date=DAY), UNIVERSE.replace('{date}', '2025-11-05 x')])
def test_the_validator_rejects_a_universe_without_an_iso_date(example, universe):
    result = replace(example, targets=example.targets.with_columns(pl.lit(universe).alias(
        'universe')))
    with pytest.raises(ValueError, match='^targets universe differs$'):
        validate_parent_links(result, NODES)


def test_the_validator_rejects_two_universes(example):
    result = replace(example, targets=edit(
        example.targets, at(A, B), universe=UNIVERSE.format(date='2025-11-06')))
    with pytest.raises(ValueError, match='^targets universe differs$'):
        validate_parent_links(result, NODES)


def test_the_validator_rejects_a_weighted_count_that_differs(example):
    result = replace(example, targets=edit(example.targets, at(A, B), n_weighted=2.0))
    with pytest.raises(ValueError, match='^targets n_weighted differs from n_unweighted$'):
        validate_parent_links(result, NODES)


def test_the_validator_rejects_a_cell_count_below_one(example):
    targets = edit(example.targets, at(A, C), n_unweighted=0, n_weighted=0.0, value=0.0)
    targets = edit(targets, at(C, A), n_unweighted=0, n_weighted=0.0, value=0.0)
    support = edit(edit(example.support, at(A, C), j_owners=0), at(C, A), j_owners=0)
    with pytest.raises(ValueError, match='^cell count below one$'):
        validate_parent_links(replace(example, targets=targets, support=support), NODES)


@pytest.mark.parametrize('side', ['unit_a', 'unit_b'])
def test_the_validator_rejects_an_unknown_unit_in_either_column(example, side):
    row = example.targets.filter((pl.col('unit_a') == A) & (pl.col('unit_b') == B)).with_columns(
        pl.lit(UNKNOWN).alias(side))
    result = replace(example, targets=pl.concat([example.targets, row]))
    with pytest.raises(ValueError, match='^unit is not a selected node$'):
        validate_parent_links(result, NODES)


def test_the_validator_rejects_a_mirror_that_exists_for_one_direction_only(example):
    # every (a, b) row needs its (b, a) row, and the reverse: dropping (A, B) leaves (B, A)
    for a, b in ((A, B), (B, C), (C, A)):
        result = replace(example, targets=only(example.targets, a, b))
        with pytest.raises(ValueError, match='^cell has no mirror$'):
            validate_parent_links(result, NODES)


def test_the_validator_rejects_a_value_that_is_off_by_more_than_the_tolerance(example):
    close = edit(example.targets, at(A, C), value=0.2 + 1e-13)
    validate_parent_links(replace(example, targets=close), NODES)
    far = edit(example.targets, at(A, C), value=0.2 + 1e-11)
    with pytest.raises(ValueError, match='^value differs from the cell count over'):
        validate_parent_links(replace(example, targets=far), NODES)


def test_the_validator_rejects_a_flag_set_that_the_support_counts_do_not_give(example):
    for flags in ([SIZE_LABEL], [DNB_LABEL], [FEDERAL_LABEL, SIZE_LABEL],
                  [DNB_LABEL, FEDERAL_LABEL, SIZE_LABEL], ['extra', DNB_LABEL, SIZE_LABEL]):
        targets = example.targets.with_columns(
            pl.when((pl.col('unit_a') == A) & (pl.col('unit_b') == B))
            .then(pl.lit(flags, dtype=pl.List(pl.String))).otherwise(pl.col('flags'))
            .alias('flags'))
        with pytest.raises(ValueError, match='^flags differ from the support counts$'):
            validate_parent_links(replace(example, targets=targets), NODES)


def test_the_validator_rejects_a_support_count_that_differs_from_the_cell_count(example):
    support = edit(example.support, at(A, B), j_owners=4)
    with pytest.raises(ValueError, match='^support count differs from the target count$'):
        validate_parent_links(replace(example, support=support), NODES)


@pytest.mark.parametrize('change', ['extra', 'duplicate', 'unsorted', 'other_cell'])
def test_the_validator_rejects_support_rows_that_are_not_the_target_cells(example, change):
    support = example.support
    if change == 'extra':
        extra = edit(support, at(A, B), unit_b=D).filter(pl.col('unit_b') == D)
        support = pl.concat([support, extra]).sort('unit_a', 'unit_b')
    elif change == 'duplicate':
        support = pl.concat([support, support.head(1)]).sort('unit_a', 'unit_b')
    elif change == 'unsorted':
        support = support.reverse()
    else:
        support = edit(support, at(A, C), unit_b=D).sort('unit_a', 'unit_b')
    with pytest.raises(ValueError, match='^support rows differ from the target cells$'):
        validate_parent_links(replace(example, support=support), NODES)


def test_the_validator_rejects_a_marginals_or_support_schema_that_differs(example):
    with pytest.raises(ValueError, match='^marginals schema differs$'):
        validate_parent_links(
            replace(example, marginals=example.marginals.drop('n_owners')), NODES)
    with pytest.raises(ValueError, match='^marginals schema differs$'):
        validate_parent_links(replace(example, marginals=example.marginals.with_columns(
            pl.col('n_owners').cast(pl.Int64))), NODES)
    with pytest.raises(ValueError, match='^marginals schema differs$'):
        validate_parent_links(replace(example, marginals=example.marginals.select(
            *reversed(example.marginals.columns))), NODES)
    with pytest.raises(ValueError, match='^support schema differs$'):
        validate_parent_links(replace(example, support=example.support.drop('j_dnb')), NODES)
    with pytest.raises(ValueError, match='^support schema differs$'):
        validate_parent_links(replace(example, support=example.support.with_columns(
            pl.col('j_2022').cast(pl.Int64))), NODES)


@pytest.mark.parametrize('change', ['reversed', 'duplicate'])
def test_the_validator_rejects_marginals_that_are_not_unique_and_sorted(example, change):
    marginals = example.marginals.reverse() if change == 'reversed' else pl.concat(
        [example.marginals, example.marginals.head(1)]).sort('node_id')
    with pytest.raises(ValueError, match='^marginals not unique and sorted$'):
        validate_parent_links(replace(example, marginals=marginals), NODES)


def test_the_validator_rejects_a_marginal_node_that_is_not_selected(example):
    # D has a marginal row and no cell: only the marginals mention it
    with pytest.raises(ValueError, match='^marginal node is not a selected node$'):
        validate_parent_links(example, NODES - {D})


def test_the_validator_rejects_a_target_unit_without_a_marginal_row(example):
    marginals = example.marginals.filter(pl.col('node_id') != C)
    with pytest.raises(ValueError, match='^target unit has no marginal row$'):
        validate_parent_links(replace(example, marginals=marginals), NODES)


def test_the_validator_rejects_a_marginal_with_no_owner(example):
    marginals = edit(example.marginals, {'node_id': D}, n_owners=0)
    with pytest.raises(ValueError, match='^marginal owner count below one$'):
        validate_parent_links(replace(example, marginals=marginals), NODES)


def test_the_validator_messages_hold_no_cell_value(example):
    for kind in MESSAGES:
        result, nodes = break_one(example, kind)
        with pytest.raises(ValueError) as failure:
            validate_parent_links(result, nodes)
        assert not re.search(r'[0-9]|naics', str(failure.value))
