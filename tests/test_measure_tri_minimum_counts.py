'''The Stage 22 TRI minimum-count script, on small synthetic cells frames.'''

import importlib.util
from pathlib import Path

import polars as pl
import pytest

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
