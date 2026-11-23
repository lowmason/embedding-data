'''The Stage 22 TRI minimum-count script, on small synthetic cells frames.'''

import importlib.util
from datetime import date
from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal
from tri_fixtures import rows_frame

from embedding_data.tri_codes import NODE_PREFIX
from embedding_data.tri_facility_years import EXCLUSIONS, public, reduce
from embedding_data.tri_layout import load_layouts
from embedding_data.tri_parent_link_targets import YEARS, estimate

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
