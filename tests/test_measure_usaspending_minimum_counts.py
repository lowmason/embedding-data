'''The Stage 21 minimum-count script, on small synthetic cells frames.'''

import importlib.util
from pathlib import Path

import polars as pl
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'measure_usaspending_minimum_counts.py'
STAGE_3_SCRIPT = ROOT / 'scripts' / 'measure_ita_minimum_counts.py'


def load_script():
    assert SCRIPT.is_file(), 'measurement script is missing'
    spec = importlib.util.spec_from_file_location('measure_usaspending_minimum_counts', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script():
    return load_script()


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


def merge_frame():
    return cells((1, 200, 0, 7), (2, 30, 0, 0), (3, 30, 0, 0), (4, 60, 0, 0),
                 (5, 10, 0, 0), (9, 45, 0, 0), (10, 2, 0, 0), (12, 2, 0, 0),
                 (40, 1, 0, 0))


def empty_top_frame():
    return cells((1, 60, 60, 0))


def level_frames():
    return [cells((1, 50, 45, 0), (10, 50, 45, 0)), cells((1, 50, 44, 0), (10, 50, 45, 0))]


def untestable_frame():
    '''60 cells with base count 1 that are untestable yet carry recurs true.'''
    return pl.DataFrame(
        {'base_count': [1] * 60, 'testable': [False] * 60, 'recurs': [True] * 60},
        schema={'base_count': pl.UInt64, 'testable': pl.Boolean, 'recurs': pl.Boolean})


def trailing_run_bands():
    return [
        [band(1, 1, 0.95), band(2, 2, 0.5), band(3, 9, 0.95), band(10, None, 0.95)],
        [band(1, 1, 0.95), band(2, 2, 0.95), band(3, 9, 0.95), band(10, None, 0.95)],
    ]


def test_rule_constants_are_the_committed_values(script):
    assert (script.LEVEL, script.TOP_BAND, script.MIN_BAND_CELLS) == (0.90, 10, 50)
    assert script.WILSON_Z == 1.959963984540054
    assert script.YEAR_PAIRS == ((2024, 2025), (2025, 2026))
    assert script.MEASURES == ('supplier_share', 'buyer_share')


def test_bands_merge_short_bands_upward(script):
    found = script.bands(merge_frame())
    assert [(b['low'], b['high'], b['testable_cells']) for b in found] == [
        (1, 1, 200), (2, 3, 60), (4, 4, 60), (5, 9, 55), (10, None, 5)]
    assert found[0]['base_cells'] == 207


def test_empty_top_band_gives_no_minimum(script):
    found = script.bands(empty_top_frame())
    assert [(b['low'], b['high'], b['testable_cells']) for b in found] == [
        (1, 1, 60), (2, None, 0)]
    assert found[-1]['rate'] is None
    assert script.pair_minimum(found) is None


def test_rate_equal_to_level_passes(script):
    passing, failing = level_frames()
    assert script.pair_minimum(script.bands(passing)) == 1
    assert script.pair_minimum(script.bands(failing)) == 2


def test_pair_minimum_is_start_of_trailing_passing_run(script):
    broken, whole = trailing_run_bands()
    assert script.pair_minimum(broken) == 3
    assert script.pair_minimum(whole) == 1


def test_untestable_cells_never_count_as_recurring(script):
    (only,) = script.bands(untestable_frame())
    assert (only['low'], only['high']) == (1, None)
    assert (only['base_cells'], only['testable_cells'], only['recurring_cells']) == (60, 0, 0)


def test_measure_minimum_is_largest_and_needs_every_pair(script):
    assert script.measure_minimum([1, 3]) == 3
    assert script.measure_minimum([2, None]) is None
    assert script.measure_minimum([]) is None


def test_band_rule_matches_stage_3(script):
    spec = importlib.util.spec_from_file_location('stage3_measure', STAGE_3_SCRIPT)
    stage3 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stage3)
    frames = [merge_frame(), empty_top_frame(), *level_frames(), untestable_frame()]
    for frame in frames:
        assert script.bands(frame) == stage3.bands(frame)
        assert script.pair_minimum(script.bands(frame)) == stage3.pair_minimum(
            stage3.bands(frame))
    for found in trailing_run_bands():
        assert script.pair_minimum(found) == stage3.pair_minimum(found)
    for minimums in ([1, 3], [2, None], []):
        assert script.measure_minimum(minimums) == stage3.family_minimum(minimums)


def test_band_of_exactly_the_minimum_cells_stands_alone(script):
    found = script.bands(cells((1, 50, 0, 0), (2, 49, 0, 0), (3, 1, 0, 0)))
    assert [(b['low'], b['high'], b['testable_cells']) for b in found] == [
        (1, 1, 50), (2, 3, 50), (4, None, 0)]


def test_short_bands_chain_into_the_top_band(script):
    found = script.bands(cells(*[(k, 50, 0, 0) for k in range(1, 8)],
                               (8, 20, 0, 0), (9, 10, 0, 0), (11, 500, 0, 0)))
    assert [(b['low'], b['high'], b['testable_cells']) for b in found] == [
        *[(k, k, 50) for k in range(1, 8)], (8, None, 530)]


def test_top_band_keeps_its_cells_whatever_their_number(script):
    found = script.bands(cells((1, 60, 0, 0), (10, 3, 3, 0), (25, 2, 0, 0)))
    assert [(b['low'], b['high'], b['testable_cells']) for b in found] == [
        (1, 1, 60), (2, None, 5)]


def test_merged_band_sums_every_count(script):
    found = script.bands(cells((1, 30, 27, 4), (2, 30, 30, 0), (10, 60, 54, 0)))
    assert [(b['low'], b['high']) for b in found] == [(1, 2), (3, None)]
    assert [(b['base_cells'], b['testable_cells'], b['recurring_cells']) for b in found] == [
        (64, 60, 57), (60, 60, 54)]
    assert [b['rate'] for b in found] == [0.95, 0.9]


def test_band_rate_and_wilson(script):
    (only,) = script.bands(cells((10, 50, 45, 3)))
    assert (only['low'], only['high'], only['recurring_cells']) == (1, None, 45)
    assert only['rate'] == 0.9
    assert (only['wilson_low'], only['wilson_high']) == pytest.approx(
        (0.7863976856252035, 0.9565242350681096))


def test_band_without_testable_cells_has_no_rate_or_interval(script):
    (only,) = script.bands(cells())
    assert (only['low'], only['high'], only['base_cells'], only['testable_cells']) == (
        1, None, 0, 0)
    assert (only['rate'], only['wilson_low'], only['wilson_high']) == (None, None, None)


def test_wilson_reference_values(script):
    assert script.wilson(9, 10) == pytest.approx((0.5958499732047615, 0.9821237869049271))
    assert script.wilson(50, 50) == pytest.approx((0.9286524008666414, 1.0))
    assert script.wilson(0, 0) is None


def test_wilson_interval_stays_inside_zero_and_one(script):
    assert script.wilson(16, 16)[1] == 1.0
    assert script.wilson(0, 21)[0] == 0.0


def test_pair_minimum_shapes_of_one_band_and_a_lone_passing_top(script):
    assert script.pair_minimum([band(1, None, 0.95)]) == 1
    assert script.pair_minimum([band(1, 9, 0.5), band(10, None, 0.95)]) == 10
    assert script.pair_minimum([band(1, 9, 0.95), band(10, None, 0.89)]) is None
    assert script.pair_minimum([]) is None


def test_base_count_below_one_is_refused(script):
    with pytest.raises(ValueError, match='base count'):
        script.bands(cells((0, 3, 0, 0)))


def test_measure_minimum_is_none_when_either_pair_has_none(script):
    spec = importlib.util.spec_from_file_location('stage3_measure', STAGE_3_SCRIPT)
    stage3 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stage3)
    for minimums in ([None, 3], [None, None], [3, None]):
        assert script.measure_minimum(minimums) is None
        assert script.measure_minimum(minimums) == stage3.family_minimum(minimums)
