'''The Stage 22 TRI minimum-count script, on small synthetic cells frames.'''

import ast
import importlib.util
import json
import re
import runpy
import sys
from datetime import date
from pathlib import Path

import httpx
import polars as pl
import pytest
from polars.testing import assert_frame_equal
from target_fixtures import forbid_external_access
from tri_fixtures import V12_RUNS, rows_frame, run_tri_v12

from embedding_data.manifest import sha256_file
from embedding_data.target_contract import write_targets
from embedding_data.target_io import inventory, write_json
from embedding_data.tri_bundle import FILES
from embedding_data.tri_codes import NODE_PREFIX
from embedding_data.tri_facility_years import EXCLUSIONS, public, reduce
from embedding_data.tri_layout import load_layouts
from embedding_data.tri_parent_industries import build_parent_industries
from embedding_data.tri_parent_link_targets import YEARS, estimate, validate_parent_links

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
SCRIPT = SCRIPTS / 'measure_tri_minimum_counts.py'
STAGE_3_SCRIPT = SCRIPTS / 'measure_ita_minimum_counts.py'


def load_script():
    assert SCRIPT.is_file(), 'measurement script is missing'
    spec = importlib.util.spec_from_file_location('measure_tri_minimum_counts', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script():
    return load_script()


def load_stage_3():
    spec = importlib.util.spec_from_file_location('stage3_measure', STAGE_3_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cells(*groups):
    '''A cells frame from (base_count, n_testable, n_recurring, n_untestable) tuples.

    The first n_recurring testable cells of a group recur. Untestable cells never recur.
    '''
    base_count, testable, recurs = [], [], []
    for count, n_testable, n_recurring, n_untestable in groups:
        base_count += [count] * (n_testable + n_untestable)
        testable += [True] * n_testable + [False] * n_untestable
        recurs += ([True] * n_recurring + [False] * (n_testable - n_recurring)
                   + [False] * n_untestable)
    return pl.DataFrame(
        {'cell': list(range(len(base_count))), 'base_count': base_count, 'testable': testable,
         'recurs': recurs},
        schema={'cell': pl.UInt64, 'base_count': pl.UInt64, 'testable': pl.Boolean,
                'recurs': pl.Boolean})


def band(low, high, rate):
    return {'low': low, 'high': high, 'rate': rate}


def shape(found):
    '''Each band as (low, high, testable cells, recurring cells).'''
    return [(b['low'], b['high'], b['testable_cells'], b['recurring_cells']) for b in found]


THIN_TOP = ((1, 200, 0, 7), (2, 30, 0, 0), (3, 30, 0, 0), (4, 60, 0, 0), (5, 10, 0, 0),
            (9, 45, 0, 0), (10, 2, 0, 0), (12, 2, 0, 0), (40, 1, 0, 0))

TASK_FRAMES = (
    THIN_TOP,
    ((1, 60, 60, 0),),
    ((1, 60, 30, 0), (9, 60, 53, 0), (10, 20, 20, 0)),
    ((1, 60, 60, 0), (9, 60, 40, 0), (10, 20, 20, 0)),
    ((1, 30, 30, 0), (3, 30, 30, 0), (10, 10, 10, 0)),
    ((1, 60, 60, 0), (10, 50, 45, 0)),
    ((1, 49, 49, 0),),
    ((1, 0, 0, 60),),
    (),
    ((1, 50, 50, 0),),
)


def test_rule_constants_are_the_committed_values(script):
    assert (script.LEVEL, script.TOP_BAND, script.MIN_BAND_CELLS) == (0.90, 10, 50)
    assert script.WILSON_Z == 1.959963984540054
    assert script.YEAR_PAIRS == ((2022, 2023), (2023, 2024))


@pytest.mark.parametrize('groups', TASK_FRAMES)
def test_band_functions_match_stage_3(script, groups):
    stage3 = load_stage_3()
    frame = cells(*groups)
    assert script.bands(frame) == stage3.bands(frame)
    assert script.pair_minimum(script.bands(frame)) == stage3.pair_minimum(
        stage3.bands(frame))
    assert script.wilson(73, 80) == stage3.wilson(73, 80)
    for minimums in ([1, 3], [2, None], []):
        assert script.family_minimum(minimums) == stage3.family_minimum(minimums)


def test_bands_merge_short_bands_upward(script):
    found = script.bands(cells((1, 200, 0, 7), (2, 30, 0, 0), (3, 30, 0, 0), (4, 60, 0, 0),
                               (5, 10, 0, 0), (9, 45, 0, 0), (10, 2, 0, 0), (12, 2, 0, 0),
                               (40, 1, 0, 0)))
    assert [(b['low'], b['high'], b['testable_cells']) for b in found] == [
        (1, 1, 200), (2, 3, 60), (4, 4, 60), (5, 9, 55), (10, None, 5)]
    assert found[0]['base_cells'] == 207


def test_curve_merges_the_thin_top_band_down(script):
    result = script.curve(cells(*THIN_TOP))
    assert shape(result['bands']) == [(1, 1, 200, 0), (2, 3, 60, 0), (4, 4, 60, 0),
                                      (5, None, 60, 0)]
    assert shape(result['before_downward_merge']) == [(5, 9, 55, 0), (10, None, 5, 0)]


def test_empty_top_band_merges_down(script):
    frame = cells((1, 60, 60, 0))
    result = script.curve(frame)
    assert shape(result['bands']) == [(1, None, 60, 60)]
    assert result['bands'][0]['rate'] == 1.0
    assert shape(result['before_downward_merge']) == [(1, 1, 60, 60), (2, None, 0, 0)]
    assert (result['minimum'], result['reason']) == (1, None)
    assert script.pair_minimum(load_stage_3().bands(frame)) is None


def test_merged_rate_sums_counts(script):
    frame = cells((1, 60, 30, 0), (9, 60, 53, 0), (10, 20, 20, 0))
    result = script.curve(frame)
    assert shape(result['before_downward_merge']) == [(2, 9, 60, 53), (10, None, 20, 20)]
    assert shape(result['bands']) == [(1, 1, 60, 30), (2, None, 80, 73)]
    top = result['bands'][-1]
    assert top['rate'] == 73 / 80
    assert (top['wilson_low'], top['wilson_high']) == script.wilson(73, 80)
    assert result['minimum'] == 2
    assert script.pair_minimum(script.bands(frame)) == 10


def test_downward_merge_can_stop_a_passing_pair(script):
    frame = cells((1, 60, 60, 0), (9, 60, 40, 0), (10, 20, 20, 0))
    result = script.curve(frame)
    top = result['bands'][-1]
    assert (top['low'], top['high'], top['testable_cells'], top['recurring_cells']) == (
        2, None, 80, 60)
    assert top['rate'] == 0.75
    assert (result['minimum'], result['reason']) == (None, 'top_band_misses_level')
    assert script.pair_minimum(script.bands(frame)) == 10


def test_merged_lower_band_keeps_its_start(script):
    result = script.curve(cells((1, 30, 30, 0), (3, 30, 30, 0), (10, 10, 10, 0)))
    assert shape(result['bands']) == [(1, None, 70, 70)]
    assert result['minimum'] == 1


def test_full_top_band_is_not_merged(script):
    result = script.curve(cells((1, 60, 60, 0), (10, 50, 45, 0)))
    assert result['before_downward_merge'] is None
    assert shape(result['bands']) == [(1, 1, 60, 60), (2, None, 50, 45)]
    assert result['minimum'] == 1


@pytest.mark.parametrize(('groups', 'expected'), [
    pytest.param(((1, 49, 49, 0),), [(1, None, 49, 49)], id='49-testable-cells'),
    pytest.param(((1, 0, 0, 60),), [(1, None, 0, 0)], id='no-testable-cells'),
    pytest.param((), [(1, None, 0, 0)], id='no-cells'),
])
def test_too_few_testable_cells_give_no_minimum(script, groups, expected):
    result = script.curve(cells(*groups))
    assert (result['minimum'], result['reason']) == (None, 'too_few_testable_cells')
    assert result['before_downward_merge'] is None
    assert shape(result['bands']) == expected


def test_too_few_testable_cells_would_pass_pair_minimum_alone(script):
    (only,) = script.bands(cells((1, 49, 49, 0)))
    assert only['rate'] == 1.0
    assert script.pair_minimum([only]) == 1


def test_fifty_testable_cells_are_enough(script):
    result = script.curve(cells((1, 50, 50, 0)))
    assert (result['minimum'], result['reason']) == (1, None)


def test_pair_minimum_is_start_of_trailing_passing_run(script):
    found = [band(1, 1, 0.95), band(2, 2, 0.5), band(3, 9, 0.95), band(10, None, 0.95)]
    assert script.pair_minimum(found) == 3
    assert script.pair_minimum([band(1, 1, 0.95), band(2, 2, 0.95), band(3, 9, 0.95),
                                band(10, None, 0.95)]) == 1


def test_family_minimum_is_largest_and_needs_both_pairs(script):
    assert script.family_minimum([1, 3]) == 3
    assert script.family_minimum([2, None]) is None
    assert script.family_minimum([]) is None


def test_band_with_exactly_the_minimum_keeps_its_own_band(script):
    found = script.bands(cells((1, 49, 0, 0), (2, 50, 0, 0), (3, 49, 0, 0), (4, 1, 0, 0)))
    assert [(b['low'], b['high'], b['testable_cells']) for b in found] == [
        (1, 2, 99), (3, 4, 50), (5, None, 0)]
    found = script.bands(cells((1, 50, 0, 0), (2, 60, 0, 0)))
    assert [(b['low'], b['high'], b['testable_cells']) for b in found] == [
        (1, 1, 50), (2, 2, 60), (3, None, 0)]


def test_top_band_one_below_the_minimum_merges_down(script):
    result = script.curve(cells((1, 60, 60, 0), (10, 49, 49, 0)))
    assert shape(result['before_downward_merge']) == [(1, 1, 60, 60), (2, None, 49, 49)]
    assert shape(result['bands']) == [(1, None, 109, 109)]
    assert (result['minimum'], result['reason']) == (1, None)


def test_rate_counts_testable_cells_only(script):
    result = script.curve(cells((1, 60, 54, 40)))
    (only,) = result['bands']
    assert (only['base_cells'], only['testable_cells'], only['recurring_cells']) == (100, 60, 54)
    assert only['rate'] == 0.9
    assert (result['minimum'], result['reason']) == (1, None)


def test_untestable_cells_never_count_as_recurring(script):
    frame = pl.DataFrame(
        {'base_count': [3, 3, 3], 'testable': [True, False, False],
         'recurs': [True, True, False]},
        schema={'base_count': pl.UInt64, 'testable': pl.Boolean, 'recurs': pl.Boolean})
    (only,) = script.bands(frame)
    assert (only['base_cells'], only['testable_cells'], only['recurring_cells']) == (3, 1, 1)


def test_base_count_below_one_is_refused(script):
    with pytest.raises(ValueError, match='base count'):
        script.bands(cells((0, 3, 0, 0)))
    with pytest.raises(ValueError, match='base count'):
        script.curve(cells((0, 3, 0, 0)))


def test_wilson_interval_stays_inside_zero_and_one(script):
    assert script.wilson(16, 16)[1] == 1.0
    assert script.wilson(0, 21)[0] == 0.0
    assert script.wilson(0, 0) is None


def test_untestable_base_cells_do_not_keep_a_thin_top_band(script):
    result = script.curve(cells((1, 60, 60, 0), (10, 10, 5, 50)))
    assert shape(result['before_downward_merge']) == [(1, 1, 60, 60), (2, None, 10, 5)]
    assert shape(result['bands']) == [(1, None, 70, 65)]
    assert (result['minimum'], result['reason']) == (1, None)


def test_untestable_cells_do_not_fill_a_band(script):
    found = script.bands(cells((1, 10, 0, 100), (2, 50, 0, 0)))
    assert [(b['low'], b['high'], b['base_cells'], b['testable_cells']) for b in found] == [
        (1, 2, 160, 60), (3, None, 0, 0)]


def test_curve_sums_counts_over_the_bands(script):
    result = script.curve(cells(*THIN_TOP))
    assert (result['base_cells'], result['testable_cells'], result['recurring_cells']) == (
        387, 380, 0)
    result = script.curve(cells((1, 60, 30, 5), (9, 60, 53, 0), (10, 20, 20, 2)))
    assert (result['base_cells'], result['testable_cells'], result['recurring_cells']) == (
        147, 140, 103)


# Real NAICS 2022 codes stand for the national-industry nodes. Their sorted order differs from
# the order of the names, so a sort that is missing shows.
NODE_LIST = [NODE_PREFIX + code for code in (
    '325199', '311111', '212311', '221114', '324110', '325211', '331110', '562211', '336111',
    '336112')]
N1, N2, N3, N4, N5, N6, N7, N8, N9, N10 = NODE_LIST
NODES = frozenset(NODE_LIST)
LAYOUTS = load_layouts()
DAY = date(2025, 11, 5)
# Made-up D&B numbers, each distinct and nine digits long.
PINE, ROCK, SLATE = '110000111', '220000222', '330000333'
COUNT_SCHEMA = {'unit_a': pl.String, 'unit_b': pl.String, 'j_owners': pl.UInt64,
                'j_2022': pl.UInt64, 'j_2023': pl.UInt64, 'j_2024': pl.UInt64}
CELL_SCHEMA = {'unit_a': pl.String, 'unit_b': pl.String, 'base_count': pl.UInt64,
               'testable': pl.Boolean, 'recurs': pl.Boolean}


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
        return [form(year, trifd, N1, name, primary_naics='') for name in names]
    if reason == 'naics_conflict':
        return [form(year, trifd, node, name) for node in (N1, N2) for name in names]
    if reason == 'naics_not_2022':
        return [form(year, trifd, N1, name, primary_naics='999999') for name in names]
    if reason == 'federal':
        return [form(year, trifd, N1, name, federal='YES') for name in names]
    assert reason == 'parent_conflict' and len(names) > 1
    return [form(year, trifd, N1, name) for name in names]


def pine(year: int, *placed: tuple[str, str]) -> list[dict]:
    '''The facility-years of Pine in a year: each item of `placed` is a TRIFD and a node.'''
    return [form(year, trifd, node, 'Pine', PINE) for trifd, node in placed]


def rock(year: int) -> list[dict]:
    '''Rock owns T9 at N1 and T10 at N2 in the year.'''
    return [form(year, 'T9', N1, 'Rock', ROCK), form(year, 'T10', N2, 'Rock', SLATE)]


def table(records: list[dict]) -> pl.DataFrame:
    return public(reduce(rows_frame(records), LAYOUTS, NODES))


def golden_records() -> list[dict]:
    '''Every kind of row: all years, owners that leave, and the five exclusions.

    Pine owns T1 to T8 at N1 to N8 in each year. T11 is self-owned at N3 in each year. Rock owns
    T9 at N1 and T10 at N2 in 2022 and 2023. Tin owns T13 at N2 in 2023 and has a federal
    facility-year. Zinc has one excluded facility-year of each other reason in 2023.
    '''
    records = []
    placed = [(f'T{index}', node) for index, node in enumerate(NODE_LIST[:8], 1)]
    for year in YEARS:
        records += pine(year, *placed)
        records.append(form(year, 'T11', N3))
    for year in (2022, 2023):
        records += rock(year)
    records += [form(2023, 'T13', N2, 'Tin'), *excluded('federal', 2023, 'T14', 'Tin')]
    for trifd, reason in (('T15', 'naics_missing'), ('T16', 'naics_conflict'),
                          ('T17', 'naics_not_2022')):
        records += excluded(reason, 2023, trifd, 'Zinc')
    return records + excluded('parent_conflict', 2023, 'T18', 'Zinc', 'Quartz')


def counted(script, records: list[dict]) -> tuple[pl.DataFrame, pl.DataFrame]:
    '''The eligible facility-years of the records and their recount.'''
    eligible = script.eligible_facility_years(table(records).lazy())
    return eligible, script.recount(eligible)


def year_cells_of(script, records: list[dict], base: int = 2022) -> pl.DataFrame:
    eligible, counts = counted(script, records)
    return script.year_cells(eligible, counts, base)


def counts_frame(*rows: tuple) -> pl.DataFrame:
    '''A recount frame from (unit_a, unit_b, j_owners, j_2022, j_2023, j_2024) tuples.'''
    return pl.DataFrame(sorted(rows), schema=COUNT_SCHEMA, orient='row')


def cell_row(frame: pl.DataFrame, unit_a: str, unit_b: str) -> dict:
    found = frame.filter((pl.col('unit_a') == unit_a) & (pl.col('unit_b') == unit_b))
    assert found.height == 1
    return found.row(0, named=True)


def test_recount_equals_the_frozen_support(script):
    records = golden_records()
    expected = estimate(reduce(rows_frame(records), LAYOUTS, NODES), processed_as_of=DAY).support
    expected = expected.select('unit_a', 'unit_b', 'j_owners', 'j_2022', 'j_2023', 'j_2024')
    assert expected.height == 56
    _, counts = counted(script, records)
    assert_frame_equal(counts, expected)


def test_year_counts_follow_each_reporting_year(script):
    records = [*pine(2022, ('T1', N1), ('T2', N2)), *pine(2023, ('T1', N1), ('T2', N2)),
               *rock(2023)]
    _, counts = counted(script, records)
    assert_frame_equal(counts, counts_frame((N1, N2, 2, 1, 2, 0), (N2, N1, 2, 1, 2, 0)))


def test_facility_owner_forms_no_cell(script):
    records = [*(form(year, 'T11', N1) for year in YEARS),
               *pine(2022, ('T1', N3), ('T2', N4))]
    _, counts = counted(script, records)
    assert_frame_equal(counts, counts_frame((N3, N4, 1, 1, 0, 0), (N4, N3, 1, 1, 0, 0)))


def test_two_facilities_at_one_node_count_once(script):
    records = [*pine(2022, ('T1', N1), ('T3', N1), ('T2', N2)),
               *pine(2023, ('T3', N1), ('T2', N2))]
    eligible, counts = counted(script, records)
    assert cell_row(counts, N1, N2)['j_2022'] == 1
    row = cell_row(script.year_cells(eligible, counts, 2022), N1, N2)
    assert (row['base_count'], row['testable'], row['recurs']) == (1, True, True)


def test_cell_recurs_through_the_same_owner(script):
    records = [*pine(2022, ('T1', N1), ('T2', N2)), *pine(2023, ('T1', N1), ('T2', N2))]
    row = cell_row(year_cells_of(script, records), N1, N2)
    assert (row['testable'], row['recurs']) == (True, True)


def test_facility_that_leaves_makes_no_cell_testable(script):
    records = [*pine(2022, ('T1', N1), ('T2', N2)), *pine(2023, ('T1', N1)), *rock(2023)]
    row = cell_row(year_cells_of(script, records), N1, N2)
    assert (row['testable'], row['recurs']) == (False, True)


@pytest.mark.parametrize('reason', EXCLUSIONS)
def test_ineligible_refile_makes_no_cell_testable(script, reason):
    parents = ('Pine', 'Quartz') if reason == 'parent_conflict' else ('Pine',)
    records = [*pine(2022, ('T1', N1), ('T2', N2)), *pine(2023, ('T1', N1)),
               *excluded(reason, 2023, 'T2', *parents)]
    row = cell_row(year_cells_of(script, records), N1, N2)
    assert row['testable'] is False


def test_changed_code_makes_a_testable_cell_that_fails(script):
    records = [*pine(2022, ('T1', N1), ('T2', N2)), *pine(2023, ('T1', N1), ('T2', N3))]
    row = cell_row(year_cells_of(script, records), N1, N2)
    assert (row['testable'], row['recurs']) == (True, False)


def test_cell_recurs_through_another_owner(script):
    records = [*pine(2022, ('T1', N1), ('T2', N2)), *pine(2023, ('T1', N1), ('T2', N3)),
               *rock(2023)]
    row = cell_row(year_cells_of(script, records), N1, N2)
    assert (row['testable'], row['recurs']) == (True, True)


def test_owner_key_change_is_not_staying(script):
    records = [*rock(2022), form(2023, 'T9', N1, 'Slate', SLATE),
               form(2023, 'T10', N2, 'Rock', SLATE)]
    row = cell_row(year_cells_of(script, records), N1, N2)
    assert (row['testable'], row['recurs']) == (False, False)
    frozen = estimate(reduce(rows_frame(records), LAYOUTS, NODES), processed_as_of=DAY)
    assert frozen.report['owner_key_changes'] == 1


def test_second_year_pair_reads_2023_and_2024(script):
    records = [*pine(2023, ('T1', N1), ('T2', N2)), *pine(2024, ('T1', N1), ('T2', N2))]
    eligible, counts = counted(script, records)
    assert script.year_cells(eligible, counts, 2022).height == 0
    row = cell_row(script.year_cells(eligible, counts, 2023), N1, N2)
    assert (row['testable'], row['recurs']) == (True, True)


@pytest.mark.parametrize('base', (2022, 2023))
def test_mirror_rows_share_counts_and_outcome(script, base):
    frame = year_cells_of(script, golden_records(), base)
    mirror = frame.rename({'unit_a': 'unit_b', 'unit_b': 'unit_a'})
    joined = frame.join(mirror, on=['unit_a', 'unit_b'], suffix='_mirror')
    assert frame.height > 0
    assert joined.height == frame.height
    for name in ('base_count', 'testable', 'recurs'):
        assert (joined[name] == joined[f'{name}_mirror']).all()


def test_eligible_facility_years_are_the_null_reason_rows_in_order(script):
    eligible = script.eligible_facility_years(table(golden_records()).reverse().lazy())
    assert dict(eligible.schema) == {'year': pl.Int64, 'trifd': pl.String, 'node': pl.String,
                                     'owner': pl.String}
    assert eligible.height == 32
    assert not {'T14', 'T15', 'T16', 'T17', 'T18'} & set(eligible['trifd'])
    keys = eligible.select('year', 'trifd').rows()
    assert keys == sorted(keys)
    assert eligible.row(0) == (2022, 'T1', N1, 'parent:Pine')
    assert (2022, 'T11', N3, 'facility:T11') in eligible.rows()


def test_no_eligible_facility_years_give_no_cells(script):
    eligible, counts = counted(script, excluded('federal', 2022, 'T1', 'Pine'))
    assert eligible.height == 0
    assert (dict(counts.schema), counts.height) == (COUNT_SCHEMA, 0)
    frame = script.year_cells(eligible, counts, 2022)
    assert (dict(frame.schema), frame.height) == (CELL_SCHEMA, 0)


def test_result_types_and_one_row_for_each_cell(script):
    eligible, counts = counted(script, golden_records())
    assert dict(counts.schema) == COUNT_SCHEMA
    for base in (2022, 2023):
        frame = script.year_cells(eligible, counts, base)
        assert dict(frame.schema) == CELL_SCHEMA
        assert frame.height == 56
        assert frame.select('unit_a', 'unit_b').unique().height == 56


def test_results_are_sorted_whatever_the_row_order(script):
    eligible, counts = counted(script, golden_records())
    assert_frame_equal(script.recount(eligible.reverse()), counts)
    keys = counts.select('unit_a', 'unit_b').rows()
    assert keys == sorted(keys)
    for base in (2022, 2023):
        expected = script.year_cells(eligible, counts, base)
        found = script.year_cells(eligible.reverse(), counts.reverse(), base)
        assert_frame_equal(found, expected)
        keys = found.select('unit_a', 'unit_b').rows()
        assert keys == sorted(keys)


def test_owners_of_different_years_count_once_each_in_j_owners(script):
    _, counts = counted(script, [*pine(2022, ('T1', N1), ('T2', N2)), *rock(2023)])
    assert_frame_equal(counts, counts_frame((N1, N2, 2, 1, 1, 0), (N2, N1, 2, 1, 1, 0)))


def test_nodes_of_different_years_form_no_cell(script):
    _, counts = counted(script, [*pine(2022, ('T1', N1)), *pine(2023, ('T2', N2))])
    assert counts.height == 0


def test_testable_needs_one_owner_at_both_nodes(script):
    records = [*pine(2022, ('T1', N1), ('T2', N2)), *rock(2022), *pine(2023, ('T1', N1)),
               form(2023, 'T10', N2, 'Rock', SLATE)]
    row = cell_row(year_cells_of(script, records), N1, N2)
    assert (row['base_count'], row['testable'], row['recurs']) == (2, False, False)


def test_base_count_is_the_owners_of_the_base_year(script):
    records = [*pine(2022, ('T1', N1), ('T2', N2)), *pine(2023, ('T1', N1), ('T2', N2)),
               *rock(2023)]
    eligible, counts = counted(script, records)
    assert cell_row(counts, N1, N2)['j_owners'] == 2
    first = cell_row(script.year_cells(eligible, counts, 2022), N1, N2)
    second = cell_row(script.year_cells(eligible, counts, 2023), N1, N2)
    assert (first['base_count'], first['testable'], first['recurs']) == (1, True, True)
    assert (second['base_count'], second['testable'], second['recurs']) == (2, False, False)


def test_one_owner_again_is_a_recurrence(script):
    records = [*pine(2022, ('T1', N1), ('T2', N2)), *rock(2022),
               *pine(2023, ('T1', N1), ('T2', N2))]
    row = cell_row(year_cells_of(script, records), N1, N2)
    assert (row['base_count'], row['testable'], row['recurs']) == (2, True, True)


@pytest.mark.parametrize('leaver', ('T1', 'T3'))
def test_a_node_stays_while_any_of_its_facilities_stays(script, leaver):
    stayer = 'T3' if leaver == 'T1' else 'T1'
    records = [*pine(2022, ('T1', N1), ('T3', N1), ('T2', N2)),
               *pine(2023, (stayer, N1), ('T2', N2))]
    frame = year_cells_of(script, records)
    for unit_a, unit_b in ((N1, N2), (N2, N1)):
        assert cell_row(frame, unit_a, unit_b)['testable'] is True


def test_mirror_cells_of_a_leaving_facility_are_both_untestable(script):
    records = [*pine(2022, ('T1', N1), ('T2', N2)), *pine(2023, ('T1', N1))]
    frame = year_cells_of(script, records)
    for unit_a, unit_b in ((N1, N2), (N2, N1)):
        row = cell_row(frame, unit_a, unit_b)
        assert (row['base_count'], row['testable'], row['recurs']) == (1, False, False)


def test_staying_means_the_next_year_and_no_later_year(script):
    records = [*pine(2022, ('T1', N1), ('T2', N2)), *pine(2023, ('T1', N1)),
               *pine(2024, ('T1', N1), ('T2', N2))]
    row = cell_row(year_cells_of(script, records), N1, N2)
    assert (row['testable'], row['recurs']) == (False, False)


def test_only_base_year_rows_can_stay(script):
    records = [*pine(2022, ('T1', N1), ('T2', N2)), *pine(2023, ('T5', N1), ('T6', N2)),
               *pine(2024, ('T5', N1), ('T6', N2))]
    row = cell_row(year_cells_of(script, records), N1, N2)
    assert (row['testable'], row['recurs']) == (False, True)


@pytest.mark.parametrize(('refile', 'expected'), [
    pytest.param(pine(2024, ('T1', N1), ('T2', N3)), (True, False), id='changed-code'),
    pytest.param(pine(2024, ('T1', N1)), (False, False), id='leaves'),
])
def test_second_year_pair_reads_the_2024_filings(script, refile, expected):
    records = [*pine(2022, ('T1', N1), ('T2', N2)), *pine(2023, ('T1', N1), ('T2', N2)),
               *refile]
    eligible, counts = counted(script, records)
    first = cell_row(script.year_cells(eligible, counts, 2022), N1, N2)
    second = cell_row(script.year_cells(eligible, counts, 2023), N1, N2)
    assert (first['testable'], first['recurs']) == (True, True)
    assert (second['testable'], second['recurs']) == expected


READ_FILES = ('report.json', 'tri_facility_years.parquet', 'tri_parent_link_support.parquet',
              'tri_parent_links.parquet')
UNREAD_FILES = ('inputs.json', 'tri_parent_link_marginals.parquet',
                'tri_parent_industries.parquet')


def code_change_records() -> list[dict]:
    '''Pine owns T1 to T8 at N1 to N8 in 2022, then T1 moves to N9 and T2 to N10 in 2023 and 2024.

    T3 to T8 keep their nodes in every year.
    '''
    placed = [(f'T{index}', node) for index, node in enumerate(NODE_LIST[:8], 1)]
    moved = [('T1', N9), ('T2', N10), *placed[2:]]
    return [*pine(2022, *placed), *pine(2023, *moved), *pine(2024, *moved)]


def owner_key_change_records() -> list[dict]:
    '''Rock owns T9 and T10 in 2022. In 2023 T9 is owned by Slate: the bundle has one change.'''
    return [*rock(2022), form(2023, 'T9', N1, 'Slate', SLATE),
            form(2023, 'T10', N2, 'Rock', SLATE)]


def publish(root: Path, records: list[dict], *, run: str = 'fixture') -> dict:
    '''Write a Stage 5 bundle of the records under `root/data` and return where it is.

    The bundle has the five tables, `report.json`, an empty `inputs.json` and the detached
    `outputs.json`, which `pin` hashes.
    '''
    frame = reduce(rows_frame(records), LAYOUTS, NODES)
    links = estimate(frame, processed_as_of=DAY)
    validate_parent_links(links, NODES)
    data_dir = root / 'data'
    directory = data_dir / 'derived/epa_tri/parent-links' / run
    directory.mkdir(parents=True)
    tables = {
        'tri_parent_links': links.targets,
        'tri_parent_link_marginals': links.marginals,
        'tri_parent_link_support': links.support,
        'tri_parent_industries': build_parent_industries(frame),
        'tri_facility_years': public(frame),
    }
    for name, value in tables.items():
        if name == 'tri_parent_links':
            write_targets(value, directory / f'{name}.parquet')
        else:
            value.write_parquet(directory / f'{name}.parquet')
    write_json(directory / 'report.json', links.report)
    write_json(directory / 'inputs.json', {})
    write_json(directory / 'outputs.json', inventory(directory, list(FILES)))
    return {'data_dir': data_dir, 'directory': directory, 'run': run,
            'pin': sha256_file(directory / 'outputs.json')}


def rehash(directory: Path) -> str:
    '''Rewrite `outputs.json` from the files of the run and return its new SHA-256.'''
    write_json(directory / 'outputs.json', inventory(directory, list(FILES)))
    return sha256_file(directory / 'outputs.json')


def forge_table(bundle: dict, name: str, change) -> str:
    '''Replace a table with `change(table)`, rehash the run and return the new pin.'''
    file = bundle['directory'] / (name.removesuffix('.parquet') + '.parquet')
    change(pl.read_parquet(file)).write_parquet(file)
    return rehash(bundle['directory'])


def forge_report(bundle: dict, change) -> str:
    '''Replace the report with `change(report)`, rehash the run and return the new pin.'''
    file = bundle['directory'] / 'report.json'
    write_json(file, change(json.loads(file.read_text())))
    return rehash(bundle['directory'])


def edited(*path: str, new):
    '''A report change that replaces the value at the path with `new(old value)`.'''
    def change(report: dict) -> dict:
        parent = report
        for key in path[:-1]:
            parent = parent[key]
        parent[path[-1]] = new(parent[path[-1]])
        return report
    return change


def dropped(*path: str):
    '''A report change that deletes the key at the path.'''
    def change(report: dict) -> dict:
        parent = report
        for key in path[:-1]:
            parent = parent[key]
        del parent[path[-1]]
        return report
    return change


def bump_report(*path: str):
    '''A report change that adds 1 to the value at the path.'''
    return edited(*path, new=lambda old: old + 1)


def compose(*changes):
    '''One report change that applies each change in turn.'''
    def change(report: dict) -> dict:
        for each in changes:
            report = each(report)
        return report
    return change


def set_row(frame: pl.DataFrame, row: int, column: str, value) -> pl.DataFrame:
    '''The frame with one cell replaced, in the type of its column.'''
    values = frame[column].to_list()
    values[row] = value
    return frame.with_columns(pl.Series(column, values, dtype=frame.schema[column]))


def bump(column: str, row: int = 0):
    '''A table change that adds 1 to a cell.'''
    return lambda frame: set_row(frame, row, column, frame[column][row] + 1)


def first_eligible(frame: pl.DataFrame) -> int:
    return frame['exclusion_reason'].is_null().arg_true()[0]


def authenticated(script, bundle: dict, *, run: str | None = None, pin: str | None = None):
    '''What `authenticate` returns for the bundle, with the run or the pin replaced.'''
    return script.authenticate(bundle['data_dir'], bundle['run'] if run is None else run,
                               bundle['pin'] if pin is None else pin)


def checked(script, bundle: dict, *, pin: str | None = None):
    '''What `self_check` returns for the bundle, once `authenticate` accepts it.'''
    authenticate = script.authenticate
    inputs = authenticate(bundle['data_dir'], bundle['run'],
                          bundle['pin'] if pin is None else pin)
    return script.self_check(inputs)


def refusal(script, bundle: dict, *, run: str | None = None, pin: str | None = None) -> str:
    '''The fixed reason with which `authenticate` or then `self_check` refuses the bundle.'''
    authenticate = script.authenticate
    with pytest.raises(script.Refused) as caught:
        script.self_check(authenticate(bundle['data_dir'], bundle['run'] if run is None else run,
                                       bundle['pin'] if pin is None else pin))
    return str(caught.value)


def append_byte(directory: Path, name: str) -> None:
    with (directory / name).open('ab') as stream:
        stream.write(b'\n')


@pytest.fixture
def golden(tmp_path):
    return publish(tmp_path, golden_records())


def test_authenticate_returns_pinned_files(script, golden):
    inputs = authenticated(script, golden)
    records = json.loads((golden['directory'] / 'outputs.json').read_text())
    assert inputs.outputs_sha256 == golden['pin']
    assert inputs.directory == golden['directory']
    assert inputs.files == {name: records[name]['sha256'] for name in READ_FILES}


@pytest.mark.parametrize(('run', 'pin'), [
    pytest.param('../fixture', None, id='parent-directory'),
    pytest.param('fixture/', None, id='trailing-slash'),
    pytest.param('-fixture', None, id='leading-hyphen'),
    pytest.param('fixture\n', None, id='trailing-newline'),
    pytest.param(None, 'A' * 64, id='uppercase-pin'),
    pytest.param(None, '0' * 63, id='short-pin'),
])
def test_unsafe_run_id_or_pin_refused(script, golden, run, pin):
    assert refusal(script, golden, run=run, pin=pin) == 'unsafe run id or pin'


@pytest.mark.parametrize('pin', ('0' * 64, None), ids=('wrong', 'missing'))
def test_wrong_or_missing_pin_refused(script, golden, pin):
    if pin is None:
        (golden['directory'] / 'outputs.json').unlink()
    assert refusal(script, golden, pin=pin) == 'outputs pin differs'


@pytest.mark.parametrize('name', READ_FILES)
def test_changed_file_refused(script, golden, name):
    append_byte(golden['directory'], name)
    assert refusal(script, golden) == f'{name} differs from its inventory'


def test_size_is_checked(script, golden):
    file = golden['directory'] / 'outputs.json'
    records = json.loads(file.read_text())
    records['tri_facility_years.parquet']['size'] += 1
    write_json(file, records)
    pin = sha256_file(file)
    assert refusal(script, golden, pin=pin) == (
        'tri_facility_years.parquet differs from its inventory')


def test_missing_record_refused(script, golden):
    file = golden['directory'] / 'outputs.json'
    records = json.loads(file.read_text())
    del records['tri_parent_link_support.parquet']
    write_json(file, records)
    pin = sha256_file(file)
    assert refusal(script, golden, pin=pin) == (
        'tri_parent_link_support.parquet differs from its inventory')


def test_pin_is_checked_before_files(script, golden):
    append_byte(golden['directory'], 'tri_parent_link_support.parquet')
    assert refusal(script, golden, pin='0' * 64) == 'outputs pin differs'


def test_unread_files_are_never_read(script, golden):
    for name in UNREAD_FILES:
        append_byte(golden['directory'], name)
    assert checked(script, golden) is not None


@pytest.mark.parametrize(('name', 'change', 'reason'), [
    pytest.param(
        'tri_facility_years',
        lambda frame: frame.with_columns(pl.col('reporting_year').cast(pl.Int32)),
        'tri_facility_years.parquet columns differ from the contract', id='retyped-year'),
    pytest.param(
        'tri_parent_link_support', lambda frame: frame.drop('j_2024'),
        'tri_parent_link_support.parquet columns differ from the contract', id='dropped-j-2024'),
    pytest.param(
        'tri_parent_links',
        lambda frame: frame.with_columns(pl.col('n_unweighted').cast(pl.Int64)),
        'tri_parent_links.parquet columns differ from the contract', id='retyped-count'),
])
def test_retyped_or_missing_column_refused(script, golden, name, change, reason):
    assert refusal(script, golden, pin=forge_table(golden, name, change)) == reason


def test_golden_passes_with_excluded_rows(script, golden):
    facility = pl.read_parquet(golden['directory'] / 'tri_facility_years.parquet')
    excluded_rows = facility.filter(pl.col('exclusion_reason').is_not_null())
    assert excluded_rows.height == 5
    assert excluded_rows['owner_key'].null_count() == 5
    assert excluded_rows['naics_2022_node_id'].null_count() == 3
    result = checked(script, golden)
    assert result.eligible.height == 32
    assert result.counts.height == 56
    assert result.targets.height == 56
    assert result.targets.columns == ['measure', 'unit_a', 'unit_b', 'n_unweighted', 'flags']
    report = json.loads((golden['directory'] / 'report.json').read_text())
    assert result.distribution == report['n_unweighted_distribution']


def test_owner_key_change_passes_the_self_check(script, tmp_path):
    bundle = publish(tmp_path, owner_key_change_records())
    assert checked(script, bundle) is not None
    report = json.loads((bundle['directory'] / 'report.json').read_text())
    assert report['owner_key_changes'] == 1


def test_unread_report_keys_are_not_checked(script, golden):
    pin = forge_report(golden, compose(
        edited('n_owners', 'dnb', new=lambda old: -1),
        edited('owners_by_year', '2023', 'federal', new=lambda old: -1)))
    assert checked(script, golden, pin=pin) is not None


def on_report(change):
    '''A forge that replaces the report of a bundle with `change(report)`.'''
    return lambda bundle: forge_report(bundle, change)


def on_table(name: str, change):
    '''A forge that replaces a table of a bundle with `change(table)`.'''
    return lambda bundle: forge_table(bundle, name, change)


SELF_CHECK_REFUSALS = [
    pytest.param(on_report(dropped('n_unweighted_distribution')), 'report is malformed',
                 id='5-distribution-missing'),
    pytest.param(on_report(dropped('owners_by_year', '2024')), 'report is malformed',
                 id='5-year-missing'),
    pytest.param(on_report(edited('n_owners', 'headline', new=lambda old: '4')),
                 'report is malformed', id='5-headline-text'),
    pytest.param(on_table('tri_facility_years', lambda frame: pl.concat([frame, frame.head(1)])),
                 'facility-year keys are not unique', id='6-repeated-key'),
    pytest.param(on_table('tri_facility_years',
                          lambda frame: set_row(frame, 0, 'reporting_year', 2021)),
                 'reporting year outside the window', id='7-year-before-window'),
    pytest.param(on_table('tri_facility_years',
                          lambda frame: set_row(frame, first_eligible(frame), 'owner_key', None)),
                 'an eligible facility-year lacks an owner or node', id='8-null-owner'),
    pytest.param(on_table(
        'tri_facility_years',
        lambda frame: set_row(frame, first_eligible(frame), 'naics_2022_node_id', None)),
        'an eligible facility-year lacks an owner or node', id='8-null-node'),
    pytest.param(on_report(bump_report('owner_key_changes')),
                 'owner key changes differ from the report', id='9-changes'),
    pytest.param(on_report(bump_report('n_owners', 'headline')),
                 'owner counts differ from the report', id='10-pooled-owners'),
    pytest.param(on_report(bump_report('owners_by_year', '2023', 'headline')),
                 'owner counts differ from the report', id='10-year-owners'),
    pytest.param(on_table('tri_parent_link_support', lambda frame: frame.slice(1)),
                 'recount differs from the support table', id='11-dropped-row'),
    pytest.param(on_table('tri_parent_link_support', bump('j_2023')),
                 'recount differs from the support table', id='11-year-count'),
    pytest.param(on_table('tri_parent_link_support', bump('j_owners')),
                 'recount differs from the support table', id='11-pooled-count'),
    pytest.param(on_table('tri_parent_links', lambda frame: frame.slice(1)),
                 'target rows differ from the support table', id='12-dropped-row'),
    pytest.param(on_table('tri_parent_links',
                          lambda frame: set_row(frame, 0, 'measure', 'other_share')),
                 'target rows differ from the support table', id='12-measure'),
    pytest.param(on_table('tri_parent_links', bump('n_unweighted')),
                 'target rows differ from the support table', id='12-count'),
    pytest.param(on_report(bump_report('n_unweighted_distribution', 'max')),
                 'report distribution differs from the targets', id='13-distribution'),
]


@pytest.mark.parametrize(('forge', 'reason'), SELF_CHECK_REFUSALS)
def test_self_check_refusals(script, golden, forge, reason):
    assert refusal(script, golden, pin=forge(golden)) == reason


# Input shapes of the rules above that the plan tests do not use.

READ_COLUMNS = {
    'tri_facility_years': ('reporting_year', 'trifd', 'naics_2022_node_id', 'owner_key',
                           'exclusion_reason'),
    'tri_parent_link_support': ('unit_a', 'unit_b', 'j_owners', 'j_2022', 'j_2023', 'j_2024'),
    'tri_parent_links': ('measure', 'unit_a', 'unit_b', 'n_unweighted', 'flags'),
}
COLUMN_CASES = [pytest.param(table, column, id=f'{table}-{column}')
                for table, columns in READ_COLUMNS.items() for column in columns]


def forge_outputs(bundle: dict, change) -> str:
    '''Replace the records of `outputs.json` with `change(records)` and return its new SHA-256.'''
    file = bundle['directory'] / 'outputs.json'
    write_json(file, change(json.loads(file.read_text())))
    return sha256_file(file)


def seal(bundle: dict, content: bytes) -> str:
    '''Write the bytes as `outputs.json` and return its SHA-256.'''
    file = bundle['directory'] / 'outputs.json'
    file.write_bytes(content)
    return sha256_file(file)


def forge_bytes(bundle: dict, name: str, content: bytes) -> str:
    '''Write the bytes as a file of the run, give it a matching record and return the new pin.'''
    file = bundle['directory'] / name

    def record(records: dict) -> dict:
        records[name].update(sha256=sha256_file(file), size=file.stat().st_size)
        return records

    file.write_bytes(content)
    return forge_outputs(bundle, record)


def drop_record(*names: str):
    '''An `outputs.json` change that deletes the records of the files.'''
    def change(records: dict) -> dict:
        for name in names:
            del records[name]
        return records
    return change


@pytest.mark.parametrize('run', ('stage5_tri_parent_links_20261121_r1', '9-Run_A', 'a'))
def test_safe_run_ids_are_accepted(script, tmp_path, run):
    bundle = publish(tmp_path, golden_records(), run=run)
    assert authenticated(script, bundle).directory == bundle['directory']


UNSAFE = {
    'empty-run': lambda bundle: ('', bundle['pin']),
    'space-in-run': lambda bundle: ('fix ture', bundle['pin']),
    'slash-in-run': lambda bundle: ('fix/ture', bundle['pin']),
    'dot-in-run': lambda bundle: ('fixture.', bundle['pin']),
    'backslash-in-run': lambda bundle: ('fix\\ture', bundle['pin']),
    'pin-with-extra-hex': lambda bundle: (bundle['run'], bundle['pin'] + 'a'),
    'pin-with-newline': lambda bundle: (bundle['run'], bundle['pin'] + '\n'),
    'pin-of-65-digits': lambda bundle: (bundle['run'], '0' * 65),
    'empty-pin': lambda bundle: (bundle['run'], ''),
    'uppercase-pin': lambda bundle: (bundle['run'], bundle['pin'].upper()),
}


@pytest.mark.parametrize('shape', UNSAFE.values(), ids=UNSAFE)
def test_more_unsafe_shapes_are_refused(script, golden, shape):
    run, pin = shape(golden)
    assert pin != golden['pin'] or run != golden['run']
    assert refusal(script, golden, run=run, pin=pin) == 'unsafe run id or pin'


@pytest.mark.parametrize('first', range(len(READ_FILES)))
def test_files_are_checked_in_order(script, golden, first):
    for name in READ_FILES[first:]:
        append_byte(golden['directory'], name)
    assert refusal(script, golden) == f'{READ_FILES[first]} differs from its inventory'


@pytest.mark.parametrize('name', READ_FILES)
def test_change_of_equal_size_is_refused(script, golden, name):
    file = golden['directory'] / name
    content = bytearray(file.read_bytes())
    content[-1] ^= 1
    file.write_bytes(bytes(content))
    assert file.stat().st_size == json.loads(
        (golden['directory'] / 'outputs.json').read_text())[name]['size']
    assert refusal(script, golden) == f'{name} differs from its inventory'


@pytest.mark.parametrize('name', READ_FILES)
def test_deleted_file_with_its_record_is_refused(script, golden, name):
    (golden['directory'] / name).unlink()
    assert refusal(script, golden) == f'{name} differs from its inventory'


def drop_key(name: str, key: str):
    def change(records: dict) -> dict:
        del records[name][key]
        return records
    return change


def put_record(name: str, value):
    def change(records: dict) -> dict:
        records[name] = value
        return records
    return change


UNUSABLE_RECORDS = [
    pytest.param(drop_record('report.json'), 'report.json', id='report-record-missing'),
    pytest.param(drop_record('tri_facility_years.parquet'), 'tri_facility_years.parquet',
                 id='facility-record-missing'),
    pytest.param(drop_record('tri_parent_links.parquet'), 'tri_parent_links.parquet',
                 id='targets-record-missing'),
    pytest.param(put_record('report.json', None), 'report.json', id='record-null'),
    pytest.param(put_record('report.json', 'abc'), 'report.json', id='record-text'),
    pytest.param(put_record('report.json', []), 'report.json', id='record-list'),
    pytest.param(drop_key('tri_parent_link_support.parquet', 'sha256'),
                 'tri_parent_link_support.parquet', id='record-without-hash'),
    pytest.param(drop_key('tri_parent_link_support.parquet', 'size'),
                 'tri_parent_link_support.parquet', id='record-without-size'),
    pytest.param(lambda records: {**records, 'report.json': {**records['report.json'],
                                                             'sha256': '0' * 64}},
                 'report.json', id='record-with-another-hash'),
    pytest.param(lambda records: [records], 'report.json', id='inventory-is-a-list'),
]


@pytest.mark.parametrize(('change', 'name'), UNUSABLE_RECORDS)
def test_unusable_records_are_refused(script, golden, change, name):
    pin = forge_outputs(golden, change)
    assert refusal(script, golden, pin=pin) == f'{name} differs from its inventory'


@pytest.mark.parametrize('content', (b'', b'not json', b'null', b'[]', b'\xff\xfe'),
                         ids=('empty', 'text', 'null', 'list', 'not-utf8'))
def test_outputs_that_are_no_object_refuse_the_first_file(script, golden, content):
    pin = seal(golden, content)
    assert refusal(script, golden, pin=pin) == 'report.json differs from its inventory'


def test_unread_files_and_records_may_be_missing(script, golden):
    for name in UNREAD_FILES:
        (golden['directory'] / name).unlink()
    pin = forge_outputs(golden, drop_record(*UNREAD_FILES))
    assert checked(script, golden, pin=pin) is not None


def test_pin_of_another_run_is_refused(script, tmp_path):
    first = publish(tmp_path, golden_records(), run='first')
    second = publish(tmp_path, code_change_records(), run='second')
    assert first['pin'] != second['pin']
    assert refusal(script, first, pin=second['pin']) == 'outputs pin differs'


def test_inputs_and_checked_are_frozen(script, golden):
    inputs = authenticated(script, golden)
    with pytest.raises(AttributeError):
        inputs.outputs_sha256 = 'x'
    result = script.self_check(inputs)
    with pytest.raises(AttributeError):
        result.eligible = None


def test_checked_holds_the_recount_and_the_read_columns(script, golden):
    result = checked(script, golden)
    facility = pl.read_parquet(golden['directory'] / 'tri_facility_years.parquet')
    assert_frame_equal(result.eligible, script.eligible_facility_years(facility.lazy()))
    assert_frame_equal(result.counts, script.recount(result.eligible))
    assert result.counts.columns == ['unit_a', 'unit_b', 'j_owners', 'j_2022', 'j_2023', 'j_2024']
    targets = pl.read_parquet(golden['directory'] / 'tri_parent_links.parquet')
    assert_frame_equal(result.targets, targets.select(
        'measure', 'unit_a', 'unit_b', 'n_unweighted', 'flags'))


def test_code_change_bundle_passes_the_self_check(script, tmp_path):
    bundle = publish(tmp_path, code_change_records())
    result = checked(script, bundle)
    assert result.eligible.height == 24
    report = json.loads((bundle['directory'] / 'report.json').read_text())
    assert report['owner_key_changes'] == 0


def test_owner_key_change_is_counted(script, tmp_path):
    bundle = publish(tmp_path, owner_key_change_records())
    pin = forge_report(bundle, edited('owner_key_changes', new=lambda old: 0))
    assert refusal(script, bundle, pin=pin) == 'owner key changes differ from the report'


@pytest.mark.parametrize('name', ('tri_facility_years', 'tri_parent_link_support',
                                  'tri_parent_links'))
def test_row_order_does_not_matter(script, golden, name):
    expected = checked(script, golden)
    pin = forge_table(golden, name, lambda frame: frame.reverse())
    found = checked(script, golden, pin=pin)
    assert_frame_equal(found.eligible, expected.eligible)
    assert_frame_equal(found.counts, expected.counts)
    assert found.distribution == expected.distribution


def test_shuffled_facility_years_pass(script, golden):
    expected = checked(script, golden)
    pin = forge_table(golden, 'tri_facility_years',
                      lambda frame: frame.sample(fraction=1.0, shuffle=True, seed=7))
    assert_frame_equal(checked(script, golden, pin=pin).eligible, expected.eligible)


@pytest.mark.parametrize(('table', 'column'), COLUMN_CASES)
def test_every_read_column_is_required(script, golden, table, column):
    pin = forge_table(golden, table, lambda frame: frame.drop(column))
    assert refusal(script, golden, pin=pin) == (
        f'{table}.parquet columns differ from the contract')


@pytest.mark.parametrize(('table', 'column'), COLUMN_CASES)
def test_every_read_column_needs_its_type(script, golden, table, column):
    pin = forge_table(golden, table, lambda frame: frame.with_columns(
        pl.lit(None, dtype=pl.Boolean).alias(column)))
    assert refusal(script, golden, pin=pin) == (
        f'{table}.parquet columns differ from the contract')


@pytest.mark.parametrize('table', READ_COLUMNS)
def test_unreadable_parquet_is_refused(script, golden, table):
    pin = forge_bytes(golden, f'{table}.parquet', b'not a parquet file')
    assert refusal(script, golden, pin=pin) == (
        f'{table}.parquet columns differ from the contract')


def test_columns_are_checked_in_file_order(script, golden):
    retype = pl.lit(None, dtype=pl.Boolean)
    forge_table(golden, 'tri_parent_links',
                lambda frame: frame.with_columns(retype.alias('flags')))
    pin = forge_table(golden, 'tri_parent_link_support',
                      lambda frame: frame.with_columns(retype.alias('j_2022')))
    assert refusal(script, golden, pin=pin) == (
        'tri_parent_link_support.parquet columns differ from the contract')
    pin = forge_table(golden, 'tri_facility_years',
                      lambda frame: frame.with_columns(retype.alias('trifd')))
    assert refusal(script, golden, pin=pin) == (
        'tri_facility_years.parquet columns differ from the contract')


def without(*names: str):
    '''A table change that drops the columns and reverses the order of the others.'''
    return lambda frame: frame.drop(names).select(frame.drop(names).columns[::-1])


def test_unread_columns_and_column_order_do_not_matter(script, golden):
    forge_table(golden, 'tri_facility_years', without('n_forms', 'parent_names'))
    forge_table(golden, 'tri_parent_link_support', without('j_dnb', 'j_including_federal'))
    pin = forge_table(golden, 'tri_parent_links', without('value', 'universe'))
    assert checked(script, golden, pin=pin) is not None


def test_unread_cells_are_not_checked(script, golden):
    forge_table(golden, 'tri_parent_link_support', compose_tables(
        bump('j_dnb'), bump('j_including_federal', 1)))
    forge_table(golden, 'tri_parent_links', lambda frame: set_row(frame, 0, 'flags', []))
    pin = forge_table(golden, 'tri_facility_years', bump('n_forms'))
    assert checked(script, golden, pin=pin) is not None


def compose_tables(*changes):
    '''One table change that applies each change in turn.'''
    def change(frame: pl.DataFrame) -> pl.DataFrame:
        for each in changes:
            frame = each(frame)
        return frame
    return change


REPORT_SHAPES = [
    pytest.param(edited('n_unweighted_distribution', new=lambda old: []),
                 id='distribution-is-a-list'),
    pytest.param(edited('n_unweighted_distribution', new=lambda old: None),
                 id='distribution-is-null'),
    pytest.param(dropped('owner_key_changes'), id='changes-missing'),
    pytest.param(edited('owner_key_changes', new=lambda old: True), id='changes-is-true'),
    pytest.param(edited('owner_key_changes', new=lambda old: False), id='changes-is-false'),
    pytest.param(edited('owner_key_changes', new=lambda old: 0.0), id='changes-is-a-float'),
    pytest.param(edited('owner_key_changes', new=lambda old: None), id='changes-is-null'),
    pytest.param(edited('owner_key_changes', new=lambda old: '0'), id='changes-is-text'),
    pytest.param(dropped('n_owners'), id='owners-missing'),
    pytest.param(edited('n_owners', new=lambda old: []), id='owners-is-a-list'),
    pytest.param(dropped('n_owners', 'headline'), id='owners-headline-missing'),
    pytest.param(edited('n_owners', 'headline', new=lambda old: True), id='owners-headline-true'),
    pytest.param(edited('n_owners', 'headline', new=lambda old: float(old)),
                 id='owners-headline-float'),
    pytest.param(edited('n_owners', 'headline', new=lambda old: None), id='owners-headline-null'),
    pytest.param(dropped('owners_by_year'), id='years-missing'),
    pytest.param(edited('owners_by_year', new=lambda old: []), id='years-is-a-list'),
    *(pytest.param(change, id=f'{year}-{label}')
      for year in YEARS
      for label, change in (
          ('missing', dropped('owners_by_year', str(year))),
          ('is-a-list', edited('owners_by_year', str(year), new=lambda old: [old])),
          ('headline-missing', dropped('owners_by_year', str(year), 'headline')),
          ('headline-true', edited('owners_by_year', str(year), 'headline',
                                   new=lambda old: True)),
          ('headline-float', edited('owners_by_year', str(year), 'headline',
                                    new=lambda old: float(old))),
          ('headline-text', edited('owners_by_year', str(year), 'headline',
                                   new=lambda old: str(old))),
      )),
]


@pytest.mark.parametrize('change', REPORT_SHAPES)
def test_report_shapes_are_malformed(script, golden, change):
    pin = forge_report(golden, change)
    assert refusal(script, golden, pin=pin) == 'report is malformed'


@pytest.mark.parametrize('content', (b'', b'not json', b'null', b'[]', b'[{}]', b'3',
                                     b'\xff\xfe'),
                         ids=('empty', 'text', 'null', 'list', 'list-of-object', 'number',
                              'not-utf8'))
def test_report_that_is_no_object_is_malformed(script, golden, content):
    pin = forge_bytes(golden, 'report.json', content)
    assert refusal(script, golden, pin=pin) == 'report is malformed'


@pytest.mark.parametrize('value', ('x', None, [], {}, 1.5, True), ids=repr)
def test_unread_report_keys_may_hold_anything(script, golden, value):
    pin = forge_report(golden, compose(
        edited('n_owners', 'dnb', new=lambda old: value),
        edited('n_owners', 'federal', new=lambda old: value),
        edited('owners_by_year', '2022', 'dnb', new=lambda old: value),
        edited('owners_by_year', '2024', 'federal', new=lambda old: value),
        edited('parent_name_collisions', new=lambda old: value)))
    assert checked(script, golden, pin=pin) is not None


def excluded_row(frame: pl.DataFrame) -> int:
    return frame['exclusion_reason'].is_not_null().arg_true()[0]


def last_eligible(frame: pl.DataFrame) -> int:
    return frame['exclusion_reason'].is_null().arg_true()[-1]


FACILITY_SHAPES = [
    pytest.param(lambda frame: set_row(frame, 3, 'trifd', None),
                 'facility-year keys are not unique', id='6-null-trifd'),
    pytest.param(lambda frame: set_row(frame, 3, 'reporting_year', None),
                 'facility-year keys are not unique', id='6-null-year'),
    pytest.param(lambda frame: pl.concat([frame, frame.slice(excluded_row(frame), 1)]),
                 'facility-year keys are not unique', id='6-repeated-excluded-row'),
    pytest.param(lambda frame: pl.concat([frame, frame.tail(1)]),
                 'facility-year keys are not unique', id='6-repeated-last-row'),
    pytest.param(lambda frame: set_row(frame, frame.height - 1, 'reporting_year', 2025),
                 'reporting year outside the window', id='7-year-after-window'),
    pytest.param(lambda frame: set_row(frame, excluded_row(frame), 'reporting_year', 2025),
                 'reporting year outside the window', id='7-excluded-row-outside'),
    pytest.param(lambda frame: set_row(frame, 0, 'reporting_year', 0),
                 'reporting year outside the window', id='7-year-zero'),
    pytest.param(lambda frame: set_row(frame, last_eligible(frame), 'owner_key', None),
                 'an eligible facility-year lacks an owner or node', id='8-last-null-owner'),
    pytest.param(lambda frame: set_row(frame, last_eligible(frame), 'naics_2022_node_id', None),
                 'an eligible facility-year lacks an owner or node', id='8-last-null-node'),
]


@pytest.mark.parametrize(('change', 'reason'), FACILITY_SHAPES)
def test_facility_year_shapes_are_refused(script, golden, change, reason):
    pin = forge_table(golden, 'tri_facility_years', change)
    assert refusal(script, golden, pin=pin) == reason


def test_same_trifd_in_each_year_is_not_a_repeat(script, golden):
    facility = pl.read_parquet(golden['directory'] / 'tri_facility_years.parquet')
    assert facility.filter(pl.col('trifd') == 'T1').height == 3
    assert checked(script, golden) is not None


def test_excluded_rows_may_carry_an_owner_and_node(script, golden):
    pin = forge_table(golden, 'tri_facility_years', lambda frame: frame.with_columns(
        pl.when(pl.col('exclusion_reason').is_not_null()).then(pl.lit('parent:Tin'))
        .otherwise(pl.col('owner_key')).alias('owner_key')))
    assert checked(script, golden, pin=pin).eligible.height == 32


def with_extra_distribution_key(report: dict) -> dict:
    report['n_unweighted_distribution']['extra'] = 1
    return report


COUNT_SHAPES = [
    pytest.param(on_report(edited('owner_key_changes', new=lambda old: old - 1)),
                 'owner key changes differ from the report', id='9-fewer-changes'),
    pytest.param(on_report(edited('n_owners', 'headline', new=lambda old: old - 1)),
                 'owner counts differ from the report', id='10-fewer-pooled-owners'),
    *(pytest.param(on_report(bump_report('owners_by_year', str(year), 'headline')),
                   'owner counts differ from the report', id=f'10-{year}-owners')
      for year in YEARS),
    *(pytest.param(on_report(edited('owners_by_year', str(year), 'headline',
                                    new=lambda old: old - 1)),
                   'owner counts differ from the report', id=f'10-{year}-fewer-owners')
      for year in YEARS),
    pytest.param(on_table('tri_parent_link_support',
                          lambda frame: frame.slice(0, frame.height - 1)),
                 'recount differs from the support table', id='11-dropped-last-row'),
    pytest.param(on_table('tri_parent_link_support',
                          lambda frame: pl.concat([frame, frame.head(1)])),
                 'recount differs from the support table', id='11-repeated-row'),
    pytest.param(on_table('tri_parent_link_support', bump('j_2022')),
                 'recount differs from the support table', id='11-2022-count'),
    pytest.param(on_table('tri_parent_link_support', bump('j_2024')),
                 'recount differs from the support table', id='11-2024-count'),
    pytest.param(on_table('tri_parent_link_support', bump('j_owners', 5)),
                 'recount differs from the support table', id='11-last-cell-count'),
    pytest.param(on_table('tri_parent_link_support',
                          lambda frame: set_row(frame, 0, 'unit_b', frame['unit_a'][0])),
                 'recount differs from the support table', id='11-other-cell'),
    pytest.param(on_table('tri_parent_links',
                          lambda frame: frame.slice(0, frame.height - 1)),
                 'target rows differ from the support table', id='12-dropped-last-row'),
    pytest.param(on_table('tri_parent_links', lambda frame: pl.concat([frame, frame.head(1)])),
                 'target rows differ from the support table', id='12-repeated-row'),
    pytest.param(on_table('tri_parent_links', lambda frame: set_row(frame, 0, 'measure', None)),
                 'target rows differ from the support table', id='12-null-measure'),
    pytest.param(on_table('tri_parent_links',
                          lambda frame: set_row(frame, frame.height - 1, 'measure', 'other')),
                 'target rows differ from the support table', id='12-last-measure'),
    pytest.param(on_table('tri_parent_links', bump('n_unweighted', 7)),
                 'target rows differ from the support table', id='12-last-count'),
    pytest.param(on_table('tri_parent_links',
                          lambda frame: set_row(frame, 0, 'unit_b', frame['unit_a'][0])),
                 'target rows differ from the support table', id='12-other-cell'),
    pytest.param(on_report(bump_report('n_unweighted_distribution', 'count')),
                 'report distribution differs from the targets', id='13-count'),
    pytest.param(on_report(bump_report('n_unweighted_distribution', 'p90')),
                 'report distribution differs from the targets', id='13-percentile'),
    pytest.param(on_report(bump_report('n_unweighted_distribution', 'ge_10')),
                 'report distribution differs from the targets', id='13-threshold'),
    pytest.param(on_report(dropped('n_unweighted_distribution', 'ge_5')),
                 'report distribution differs from the targets', id='13-key-missing'),
    pytest.param(on_report(with_extra_distribution_key),
                 'report distribution differs from the targets', id='13-extra-key'),
    pytest.param(on_report(edited('n_unweighted_distribution', 'min', new=lambda old: None)),
                 'report distribution differs from the targets', id='13-null-field'),
    pytest.param(on_report(edited('n_unweighted_distribution', new=lambda old: {})),
                 'report distribution differs from the targets', id='13-empty-distribution'),
]


@pytest.mark.parametrize(('forge', 'reason'), COUNT_SHAPES)
def test_count_shapes_are_refused(script, golden, forge, reason):
    assert refusal(script, golden, pin=forge(golden)) == reason


CHAIN = [
    ('4', on_table('tri_facility_years',
                   lambda frame: frame.with_columns(pl.col('reporting_year').cast(pl.Int32))),
     'tri_facility_years.parquet columns differ from the contract'),
    ('5', on_report(dropped('n_unweighted_distribution')), 'report is malformed'),
    ('6', on_table('tri_facility_years', lambda frame: pl.concat([frame, frame.head(1)])),
     'facility-year keys are not unique'),
    ('7', on_table('tri_facility_years', lambda frame: set_row(frame, 0, 'reporting_year', 2021)),
     'reporting year outside the window'),
    ('8', on_table('tri_facility_years',
                   lambda frame: set_row(frame, first_eligible(frame), 'owner_key', None)),
     'an eligible facility-year lacks an owner or node'),
    ('9', on_report(edited('owner_key_changes', new=lambda old: old + 2)),
     'owner key changes differ from the report'),
    ('10', on_report(bump_report('n_owners', 'headline')), 'owner counts differ from the report'),
    ('11', on_table('tri_parent_link_support', bump('j_owners')),
     'recount differs from the support table'),
    ('12', on_table('tri_parent_links', bump('n_unweighted', 7)),
     'target rows differ from the support table'),
    ('13', on_report(bump_report('n_unweighted_distribution', 'max')),
     'report distribution differs from the targets'),
]


@pytest.mark.parametrize('index', range(len(CHAIN) - 1),
                         ids=[f'{a[0]}-before-{b[0]}' for a, b in zip(CHAIN, CHAIN[1:])])
def test_the_earlier_check_refuses_first(script, golden, index):
    (_, earlier, reason), (_, later, _) = CHAIN[index], CHAIN[index + 1]
    later(golden)
    pin = earlier(golden)
    assert refusal(script, golden, pin=pin) == reason


@pytest.mark.parametrize('name', READ_FILES)
def test_changed_content_is_never_parsed(script, golden, name):
    (golden['directory'] / name).write_bytes(b'garbage')
    assert refusal(script, golden) == f'{name} differs from its inventory'


@pytest.mark.parametrize(('records', 'eligible'), [
    pytest.param([form(2022, 'T11', N3)], 1, id='self-owned-facility'),
    pytest.param(excluded('federal', 2022, 'T1', 'Pine'), 0, id='excluded-facility'),
])
def test_bundle_without_cells_passes_the_self_check(script, tmp_path, records, eligible):
    result = checked(script, publish(tmp_path, records))
    assert result.eligible.height == eligible
    assert (result.counts.height, result.targets.height) == (0, 0)
    assert result.distribution['count'] == 0


@pytest.mark.parametrize('reason', EXCLUSIONS)
def test_excluded_refile_is_no_owner_key_change(script, tmp_path, reason):
    parents = ('Pine', 'Quartz') if reason == 'parent_conflict' else ('Pine',)
    records = [*pine(2022, ('T1', N1), ('T2', N2)), *pine(2023, ('T1', N1)),
               *excluded(reason, 2023, 'T2', *parents)]
    bundle = publish(tmp_path, records)
    facility = pl.read_parquet(bundle['directory'] / 'tri_facility_years.parquet')
    refiles = facility.filter(pl.col('trifd') == 'T2').sort('reporting_year')
    assert refiles['exclusion_reason'].to_list() == [None, reason]
    assert refiles['owner_key'].to_list() == ['parent:Pine', None]
    report = json.loads((bundle['directory'] / 'report.json').read_text())
    assert report['owner_key_changes'] == 0
    assert checked(script, bundle) is not None


# The kept counts, the result and the command line.

DNB = 'numerator:dnb_key_sensitivity:true'
FEDERAL = 'numerator:federal_sensitivity:true'
ROW_SCHEMA = {'count': pl.UInt64, 'largest_year_count': pl.UInt64, 'dnb_label': pl.Boolean,
              'federal_label': pl.Boolean}
TARGET_COLUMNS = {'measure': pl.String, 'unit_a': pl.String, 'unit_b': pl.String,
                  'n_unweighted': pl.UInt64, 'flags': pl.List(pl.String)}
KEPT_KEYS = ('kept_rows', 'kept_row_share', 'kept_support', 'kept_support_share',
             'lenient_kept_rows', 'kept_dnb_rows', 'kept_federal_rows')
RESULT_KEYS = {'complete', 'constants', 'inputs', 'year_pairs', 'minimum',
               'n_unweighted_distribution', 'published'}
PAIRS = ('2022-2023', '2023-2024')
F, T = False, True


def rows_of(*rows: tuple) -> pl.DataFrame:
    '''A `published` frame from (count, largest_year_count, dnb_label, federal_label) tuples.'''
    return pl.DataFrame(list(rows), schema=ROW_SCHEMA, orient='row')


def targets_of(*rows: tuple) -> pl.DataFrame:
    '''A target frame from (unit_a, unit_b, n_unweighted, flags) tuples.'''
    return pl.DataFrame([('owner_share', *row) for row in rows], schema=TARGET_COLUMNS,
                        orient='row')


def lenient_records() -> list[dict]:
    '''Pine and Rock link N1 and N2 in 2022 and 2023. Oak and Elm both link N3 and N4 in 2024.'''
    return [*pine(2022, ('T1', N1), ('T2', N2)),
            form(2023, 'T9', N1, 'Rock', ROCK), form(2023, 'T10', N2, 'Rock', ROCK),
            form(2024, 'T21', N3, 'Oak'), form(2024, 'T22', N4, 'Oak'),
            form(2024, 'T23', N3, 'Elm'), form(2024, 'T24', N4, 'Elm')]


def run_main(script, capsys, bundle, pin=None):
    '''Call `main` on the bundle: the status, the one parsed line of stdout and stderr.'''
    status = script.main(['--data-dir', str(bundle['data_dir']), '--run', bundle['run'],
                          '--outputs-sha256', bundle['pin'] if pin is None else pin])
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    assert len(lines) == 1 and captured.out == lines[0] + '\n'
    assert lines[0] == json.dumps(json.loads(lines[0]), sort_keys=True)
    return status, json.loads(lines[0]), captured.err


def without_inputs(result: dict) -> str:
    return json.dumps({key: value for key, value in result.items() if key != 'inputs'},
                      sort_keys=True)


def test_kept_counts(script):
    rows = rows_of(*[(1, 1, F, F)] * 2, *[(2, 1, T, F)] * 2, *[(3, 3, F, T)] * 2)
    assert script.kept(rows, 2) == {
        'rows': 6, 'support': 12, 'dnb_rows': 2, 'federal_rows': 2, 'kept_rows': 4,
        'kept_row_share': 4 / 6, 'kept_support': 10, 'kept_support_share': 10 / 12,
        'lenient_kept_rows': 2, 'kept_dnb_rows': 2, 'kept_federal_rows': 2}
    assert script.kept(rows, None) == {
        'rows': 6, 'support': 12, 'dnb_rows': 2, 'federal_rows': 2, **dict.fromkeys(KEPT_KEYS)}


def test_lenient_count_reads_every_year(script, tmp_path):
    found = checked(script, publish(tmp_path, lenient_records()))
    rows = script.published(found.targets, found.counts)
    assert rows.height == 4
    for pair, largest in (((N1, N2), 1), ((N3, N4), 2)):
        for unit_a, unit_b in (pair, pair[::-1]):
            row = cell_row(rows, unit_a, unit_b)
            assert (row['count'], row['largest_year_count']) == (2, largest)
    result = script.kept(rows, 2)
    assert (result['kept_rows'], result['lenient_kept_rows']) == (4, 2)
    for base in (2022, 2023):
        frame = script.year_cells(found.eligible, found.counts, base)
        assert set(frame.select('unit_a', 'unit_b').rows()) == {(N1, N2), (N2, N1)}


def test_golden_run_exits_zero(script, golden, capsys):
    status, result, error = run_main(script, capsys, golden)
    assert (status, error) == (0, '')
    assert set(result) == RESULT_KEYS
    assert (result['complete'], result['minimum']) == (True, 1)
    assert set(result['year_pairs']) == set(PAIRS)
    for found in result['year_pairs'].values():
        assert (found['base_cells'], found['testable_cells'], found['recurring_cells']) == (
            56, 56, 56)
        assert shape(found['bands']) == [(1, None, 56, 56)]
        assert found['bands'][0]['rate'] == 1.0
        assert shape(found['before_downward_merge']) == [(1, 1, 54, 54), (2, None, 2, 2)]
        assert (found['minimum'], found['reason']) == (1, None)
    assert result['constants'] == {
        'level': 0.9, 'top_band': 10, 'min_band_cells': 50, 'wilson_z': 1.959963984540054,
        'year_pairs': [[2022, 2023], [2023, 2024]]}
    records = json.loads((golden['directory'] / 'outputs.json').read_text())
    assert result['inputs'] == {
        'run': golden['run'], 'outputs_sha256': golden['pin'],
        'files': {name: records[name]['sha256'] for name in READ_FILES}}
    assert result['published'] == {
        'rows': 56, 'support': 58, 'dnb_rows': 2, 'federal_rows': 2, 'kept_rows': 56,
        'kept_row_share': 1.0, 'kept_support': 58, 'kept_support_share': 1.0,
        'lenient_kept_rows': 0, 'kept_dnb_rows': 2, 'kept_federal_rows': 2}
    report = json.loads((golden['directory'] / 'report.json').read_text())
    assert result['n_unweighted_distribution'] == report['n_unweighted_distribution']


def test_changed_codes_exit_one(script, tmp_path, capsys):
    bundle = publish(tmp_path, code_change_records())
    status, result, error = run_main(script, capsys, bundle)
    assert (status, error) == (1, '')
    assert (result['complete'], result['minimum']) == (False, None)
    first, second = (result['year_pairs'][label] for label in PAIRS)
    assert (first['base_cells'], first['testable_cells'], first['recurring_cells']) == (
        56, 56, 30)
    assert shape(first['bands']) == [(1, None, 56, 30)]
    assert (first['minimum'], first['reason']) == (None, 'top_band_misses_level')
    assert (second['minimum'], second['reason']) == (1, None)
    published = result['published']
    assert (published['rows'], published['kept_rows']) == (82, None)
    assert [published[key] for key in KEPT_KEYS] == [None] * 7


def test_too_few_cells_exit_one(script, tmp_path, capsys):
    records = [*pine(2022, ('T1', N1), ('T2', N2)), *pine(2023, ('T1', N1), ('T2', N2))]
    status, result, error = run_main(script, capsys, publish(tmp_path, records))
    assert (status, error) == (1, '')
    assert (result['complete'], result['minimum']) == (False, None)
    first, second = (result['year_pairs'][label] for label in PAIRS)
    assert (first['testable_cells'], first['recurring_cells']) == (2, 2)
    assert first['bands'][0]['rate'] == 1.0
    assert (first['minimum'], first['reason']) == (None, 'too_few_testable_cells')
    assert (second['base_cells'], second['testable_cells']) == (2, 0)
    assert (second['minimum'], second['reason']) == (None, 'too_few_testable_cells')


def test_refusal_prints_only_the_reason(script, golden, capsys):
    assert run_main(script, capsys, golden, pin='0' * 64) == (
        2, {'complete': False, 'reason': 'outputs pin differs'}, '')


def test_unexpected_error_hides_its_message(script, golden, capsys, monkeypatch):
    def explode(*args):
        raise ValueError('parent:Pine T1')

    monkeypatch.setattr(script, 'year_cells', explode)
    status, result, error = run_main(script, capsys, golden)
    assert (status, result) == (2, {'complete': False, 'reason': 'unexpected error'})
    assert 'ValueError' in error
    for text in (json.dumps(result), error):
        assert 'Pine' not in text and 'T1' not in text


def test_shuffled_facility_years_give_identical_output(script, golden, capsys):
    _, expected, _ = run_main(script, capsys, golden)
    pin = forge_table(golden, 'tri_facility_years',
                      lambda frame: frame.sample(fraction=1.0, shuffle=True, seed=7))
    status, found, _ = run_main(script, capsys, golden, pin=pin)
    assert status == 0
    assert (found['inputs']['files']['tri_facility_years.parquet']
            != expected['inputs']['files']['tri_facility_years.parquet'])
    assert without_inputs(found) == without_inputs(expected)


def test_two_runs_are_byte_identical(script, golden, capsys):
    script.main(['--data-dir', str(golden['data_dir']), '--run', golden['run'],
                 '--outputs-sha256', golden['pin']])
    first = capsys.readouterr().out
    script.main(['--data-dir', str(golden['data_dir']), '--run', golden['run'],
                 '--outputs-sha256', golden['pin']])
    assert first and capsys.readouterr().out == first


def strings_of(value) -> list[str]:
    '''Every key and string value of a parsed JSON value.'''
    if isinstance(value, dict):
        return [text for key, item in value.items() for text in (key, *strings_of(item))]
    if isinstance(value, list):
        return [text for item in value for text in strings_of(item)]
    return [value] if isinstance(value, str) else []


@pytest.mark.parametrize('make', (lambda path: publish(path, golden_records()),
                                  lambda path: publish(path, code_change_records())),
                         ids=('golden', 'changed-codes'))
def test_output_holds_no_identifier(script, tmp_path, capsys, make):
    _, result, _ = run_main(script, capsys, make(tmp_path))
    found = strings_of(result)
    assert found
    names = [f'T{number}' for number in range(1, 25)] + [
        'Pine', 'Rock', 'Tin', 'Zinc', 'Quartz', 'parent:', 'facility:', NODE_PREFIX]
    for text in found:
        assert not any(name in text for name in names), text


def tree(root: Path) -> list[tuple[str, str | None]]:
    '''Every file and directory under the root, with the SHA-256 of each file.'''
    return sorted((str(path.relative_to(root)), sha256_file(path) if path.is_file() else None)
                  for path in root.rglob('*'))


def test_writes_nothing_under_data_dir(script, golden, capsys):
    before = tree(golden['data_dir'])
    assert before
    assert run_main(script, capsys, golden)[0] == 0
    assert tree(golden['data_dir']) == before


def test_runs_offline(script, golden, capsys, monkeypatch):
    def no_client(*args, **kwargs):
        raise AssertionError('the script built an HTTP client')

    forbid_external_access(monkeypatch)
    monkeypatch.setattr(httpx.Client, '__init__', no_client)
    monkeypatch.setattr(httpx.AsyncClient, '__init__', no_client)
    assert run_main(script, capsys, golden)[0] == 0


def test_script_imports(script):
    allowed = {'polars', 'embedding_data.target_contract', 'embedding_data.tri_facility_years',
               'embedding_data.tri_parent_link_targets'}
    imports = [node for node in ast.walk(ast.parse(SCRIPT.read_text()))
               if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert imports
    for node in imports:
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        else:
            assert node.level == 0
            modules = [node.module]
        for module in modules:
            assert (module.partition('.')[0] in sys.stdlib_module_names
                    or module in allowed), module
        assert not any(alias.name.startswith('_') for alias in node.names)


@pytest.fixture(scope='module')
def v12(tmp_path_factory):
    '''One run of the V12 chain, shared by the tests that only read its bundles.'''
    with pytest.MonkeyPatch.context() as patch:
        return run_tri_v12(tmp_path_factory.mktemp('minimum-v12'), patch)


def test_genuine_chain_bundles_pass_the_checks(script, v12, capsys):
    results = []
    for name, run in zip(('first', 'second'), V12_RUNS, strict=True):
        bundle = {'data_dir': v12['data_dir'], 'run': run, 'pin': v12[f'{name}_pin']}
        assert v12[name].name == run
        status, result, error = run_main(script, capsys, bundle)
        assert (status, error) == (1, '')
        assert result['complete'] is False
        assert [result['year_pairs'][label]['reason'] for label in PAIRS] == [
            'too_few_testable_cells'] * 2
        results.append(result)
    first, second = results
    assert without_inputs(first) == without_inputs(second)
    records = json.loads((v12['first'] / 'outputs.json').read_text())
    assert first['inputs']['files']['report.json'] == records['report.json']['sha256']


# Input shapes of the rules above that the plan tests do not use.

PUBLISHED_SCHEMA = {'unit_a': pl.String, 'unit_b': pl.String, 'count': pl.UInt64,
                    'largest_year_count': pl.UInt64, 'dnb_label': pl.Boolean,
                    'federal_label': pl.Boolean}
LABEL_CASES = (
    ([], F, F),
    ([DNB], T, F),
    ([FEDERAL], F, T),
    ([DNB, FEDERAL], T, T),
    (['numerator:other:true'], F, F),
    (['numerator:dnb_key_sensitivity:false', 'numerator:federal_sensitivity:false'], F, F),
)


def test_published_takes_the_largest_single_year_count(script):
    counts = counts_frame(('a', 'b', 9, 7, 0, 0), ('c', 'd', 9, 0, 8, 0),
                          ('e', 'f', 9, 0, 0, 9), ('g', 'h', 9, 3, 3, 3))
    targets = targets_of(('g', 'h', 9, []), ('e', 'f', 9, []), ('c', 'd', 9, []),
                         ('a', 'b', 9, []))
    rows = script.published(targets, counts)
    assert dict(rows.schema) == PUBLISHED_SCHEMA
    assert dict(rows.select('unit_a', 'largest_year_count').rows()) == {
        'a': 7, 'c': 8, 'e': 9, 'g': 3}
    assert rows['count'].to_list() == [9] * 4


def test_published_reads_the_labels_from_flags(script):
    units = [str(index) for index in range(len(LABEL_CASES))]
    counts = counts_frame(*((unit, unit + 'x', 1, 1, 0, 0) for unit in units))
    targets = targets_of(*((unit, unit + 'x', 1, flags)
                           for unit, (flags, _, _) in zip(units, LABEL_CASES, strict=True)))
    rows = script.published(targets, counts)
    found = {row['unit_a']: (row['dnb_label'], row['federal_label'])
             for row in rows.iter_rows(named=True)}
    assert found == {unit: (dnb, federal) for unit, (_, dnb, federal)
                     in zip(units, LABEL_CASES, strict=True)}


def test_published_has_one_row_for_each_target_row(script, golden):
    found = checked(script, golden)
    rows = script.published(found.targets, found.counts)
    assert dict(rows.schema) == PUBLISHED_SCHEMA
    assert (rows.height, rows.select('unit_a', 'unit_b').unique().height) == (56, 56)
    cells = ['unit_a', 'unit_b']
    assert rows['count'].to_list() == found.targets.sort(cells)['n_unweighted'].to_list()
    assert (rows['dnb_label'].sum(), rows['federal_label'].sum()) == (2, 2)


def test_kept_counts_at_the_boundaries(script):
    rows = rows_of((1, 1, F, F), (2, 2, F, F), (3, 1, F, F), (2, 1, F, F))
    low = script.kept(rows, 2)
    assert (low['kept_rows'], low['kept_support'], low['lenient_kept_rows']) == (3, 7, 2)
    assert (low['kept_row_share'], low['kept_support_share']) == (3 / 4, 7 / 8)
    high = script.kept(rows, 3)
    assert (high['kept_rows'], high['kept_support'], high['lenient_kept_rows']) == (1, 3, 1)
    none = script.kept(rows, 4)
    assert [none[key] for key in KEPT_KEYS] == [0, 0.0, 0, 0.0, 0, 0, 0]
    assert none['rows'] == 4 and none['support'] == 8


def test_kept_labels_are_counted_separately(script):
    rows = rows_of(*[(1, 1, F, F)] * 2, *[(2, 1, T, F)] * 2, *[(3, 3, F, T)] * 2)
    found = script.kept(rows, 3)
    assert (found['kept_dnb_rows'], found['kept_federal_rows']) == (0, 2)
    found = script.kept(rows, 1)
    assert (found['kept_dnb_rows'], found['kept_federal_rows']) == (2, 2)
    both = script.kept(rows_of((2, 2, T, T), (2, 2, F, F)), 2)
    assert (both['dnb_rows'], both['federal_rows']) == (1, 1)
    assert (both['kept_dnb_rows'], both['kept_federal_rows'], both['kept_rows']) == (1, 1, 2)


def test_summarize_takes_the_larger_year_pair_minimum(script):
    low = cells((1, 60, 60, 0))
    high = cells((1, 60, 30, 0), (10, 60, 60, 0))
    rows = rows_of((1, 1, F, F), (2, 2, F, F), (3, 3, F, F))
    distribution = {'count': 3}
    for pair in ((low, high), (high, low)):
        found = script.summarize(dict(zip(PAIRS, pair, strict=True)), rows, distribution)
        assert [script.curve(each)['minimum'] for each in pair] in ([1, 2], [2, 1])
        assert found['minimum'] == 2
        assert found['published'] == script.kept(rows, 2)
        assert found['n_unweighted_distribution'] is distribution
        assert found['year_pairs'] == {label: script.curve(each)
                                       for label, each in zip(PAIRS, pair, strict=True)}


@pytest.mark.parametrize('none', (cells((1, 49, 49, 0)), cells((1, 60, 30, 0))),
                         ids=('too-few-testable-cells', 'top-band-misses-level'))
def test_summarize_gives_no_minimum_when_a_pair_has_none(script, none):
    fine = cells((1, 60, 60, 0))
    rows = rows_of((1, 1, F, F), (2, 2, F, F))
    for pair in ((fine, none), (none, fine)):
        found = script.summarize(dict(zip(PAIRS, pair, strict=True)), rows, {})
        assert found['minimum'] is None
        assert [found['published'][key] for key in KEPT_KEYS] == [None] * 7
        assert found['published']['rows'] == 2
        assert set(found['year_pairs']) == set(PAIRS)


@pytest.mark.parametrize(('forge', 'reason'), SELF_CHECK_REFUSALS)
def test_self_check_refusals_print_only_the_reason(script, golden, capsys, monkeypatch, forge,
                                                   reason):
    called = []
    monkeypatch.setattr(script, 'year_cells', lambda *args: called.append(args))
    assert run_main(script, capsys, golden, pin=forge(golden)) == (
        2, {'complete': False, 'reason': reason}, '')
    assert called == []


def raise_plain(*args):
    raise KeyError(('parent:Pine', 'T1'))


def raise_with_cause(*args):
    try:
        raise KeyError('owner:Slate T99')
    except KeyError as cause:
        raise ValueError('harmless words') from cause


def raise_in_handler(*args):
    try:
        raise KeyError('owner:Slate T99')
    except KeyError:
        raise ValueError('harmless words')


@pytest.mark.parametrize(('raiser', 'kind'), [
    pytest.param(raise_plain, 'KeyError', id='plain'),
    pytest.param(raise_with_cause, 'ValueError', id='explicit-cause'),
    pytest.param(raise_in_handler, 'ValueError', id='implicit-context'),
])
def test_unexpected_error_hides_every_message_in_its_chain(
        script, golden, capsys, monkeypatch, raiser, kind):
    monkeypatch.setattr(script, 'year_cells', raiser)
    status, result, error = run_main(script, capsys, golden)
    assert (status, result) == (2, {'complete': False, 'reason': 'unexpected error'})
    assert error.splitlines()[0] == kind
    for text in ('Pine', 'T1', 'Slate', 'T99', 'owner:', 'parent:', 'harmless'):
        assert text not in error


def test_unexpected_error_gives_one_line_for_each_frame(script, golden, capsys, monkeypatch):
    def explode(*args):
        raise ValueError('a message')

    monkeypatch.setattr(script, 'year_cells', explode)
    _, _, error = run_main(script, capsys, golden)
    lines = error.splitlines()
    assert lines[0] == 'ValueError'
    places = [re.fullmatch(r'(.+):(\d+) in (\S+)', line) for line in lines[1:]]
    assert all(places)
    assert [place[3] for place in places if not place[3].startswith('<')] == [
        'main', 'measure', 'explode']
    assert places[0][1] == str(SCRIPT)
    assert int(places[0][2]) > 0
    assert 'a message' not in error


def test_a_result_that_is_not_json_is_an_unexpected_error(script, golden, capsys, monkeypatch):
    monkeypatch.setattr(script, 'measure',
                        lambda inputs: {'complete': True, 'rate': float('nan')})
    status, result, error = run_main(script, capsys, golden)
    assert (status, result) == (2, {'complete': False, 'reason': 'unexpected error'})
    assert error.splitlines()[0] == 'ValueError'


@pytest.mark.parametrize('missing', ('--data-dir', '--run', '--outputs-sha256'))
def test_every_option_is_required(script, golden, capsys, missing):
    options = {'--data-dir': str(golden['data_dir']), '--run': golden['run'],
               '--outputs-sha256': golden['pin']}
    del options[missing]
    with pytest.raises(SystemExit) as stopped:
        script.main([part for pair in options.items() for part in pair])
    assert stopped.value.code == 2
    assert capsys.readouterr().out == ''


def test_the_command_line_exits_with_the_status(golden, capsys, monkeypatch):
    changed = publish(golden['data_dir'].parent, code_change_records(), run='changed')
    for bundle, pin, status in ((golden, None, 0), (changed, None, 1), (golden, '0' * 64, 2)):
        monkeypatch.setattr(sys, 'argv', [
            str(SCRIPT), '--data-dir', str(bundle['data_dir']), '--run', bundle['run'],
            '--outputs-sha256', bundle['pin'] if pin is None else pin])
        with pytest.raises(SystemExit) as stopped:
            runpy.run_path(str(SCRIPT), run_name='__main__')
        assert stopped.value.code == status
        assert len(capsys.readouterr().out.splitlines()) == 1
