'''The V9 minimum-count rule functions, on small synthetic cells frames.'''

import importlib.util
from pathlib import Path

import polars as pl
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'measure_ita_minimum_counts.py'


def load_script():
    assert SCRIPT.is_file(), 'measurement script is missing'
    spec = importlib.util.spec_from_file_location('measure_ita_minimum_counts', SCRIPT)
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


def test_rule_constants_are_the_committed_values(script):
    assert (script.LEVEL, script.TOP_BAND, script.MIN_BAND_CELLS) == (0.90, 10, 50)
    assert script.YEAR_PAIRS == ((2023, 2024), (2024, 2025))


def test_bands_merge_short_bands_upward(script):
    found = script.bands(cells((1, 200, 0, 7), (2, 30, 0, 0), (3, 30, 0, 0), (4, 60, 0, 0),
                               (5, 10, 0, 0), (9, 45, 0, 0), (10, 2, 0, 0), (12, 2, 0, 0),
                               (40, 1, 0, 0)))
    assert [(b['low'], b['high'], b['testable_cells']) for b in found] == [
        (1, 1, 200), (2, 3, 60), (4, 4, 60), (5, 9, 55), (10, None, 5)]
    assert found[0]['base_cells'] == 207


def test_short_bands_chain_into_the_top_band(script):
    found = script.bands(cells(*[(k, 50, 0, 0) for k in range(1, 8)],
                               (8, 20, 0, 0), (9, 10, 0, 0), (11, 500, 0, 0)))
    assert [(b['low'], b['high'], b['testable_cells']) for b in found] == [
        *[(k, k, 50) for k in range(1, 8)], (8, None, 530)]


def test_band_rate_and_wilson(script):
    (band,) = script.bands(cells((10, 50, 45, 3)))
    assert (band['low'], band['high'], band['recurring_cells']) == (1, None, 45)
    assert band['rate'] == 0.9
    assert (band['wilson_low'], band['wilson_high']) == pytest.approx(
        (0.7863976856252035, 0.9565242350681096))


def test_wilson_reference_values(script):
    assert script.wilson(9, 10) == pytest.approx((0.5958499732047615, 0.9821237869049271))
    assert script.wilson(50, 50) == pytest.approx((0.9286524008666414, 1.0))
    assert script.wilson(0, 0) is None


def test_pair_minimum_is_start_of_trailing_passing_run(script):
    found = [band(1, 1, 0.5), band(2, 3, 0.95), band(4, 4, 0.85), band(5, 9, 0.92),
             band(10, None, 0.99)]
    assert script.pair_minimum(found) == 5


def test_pair_minimum_of_one_is_valid(script):
    found = [band(1, 1, 0.9), band(2, 3, 0.95), band(4, 9, 0.97), band(10, None, 1.0)]
    assert script.pair_minimum(found) == 1


def test_rate_equal_to_level_passes(script):
    assert script.pair_minimum([band(1, 9, 0.9), band(10, None, 0.9)]) == 1


def test_no_minimum_when_top_band_misses_level(script):
    assert script.pair_minimum([band(1, 9, 0.95), band(10, None, 0.89)]) is None
    assert script.pair_minimum([band(1, 9, 0.95), band(10, None, None)]) is None


def test_family_minimum_is_largest_over_year_pairs(script):
    assert script.family_minimum([1, 3]) == 3
    assert script.family_minimum([2, None]) is None


def test_wilson_z_and_family_names_are_the_committed_values(script):
    assert script.WILSON_Z == 1.959963984540054
    assert script.FAMILIES == ('co_ownership', 'area_mix', 'text_pairs')


def test_wilson_interval_stays_inside_zero_and_one(script):
    assert script.wilson(16, 16)[1] == 1.0
    assert script.wilson(0, 21)[0] == 0.0


def test_empty_cells_give_one_band_without_a_rate(script):
    (only,) = script.bands(cells())
    assert (only['low'], only['high'], only['base_cells'], only['testable_cells']) == (
        1, None, 0, 0)
    assert (only['rate'], only['wilson_low'], only['wilson_high']) == (None, None, None)


def test_base_count_below_one_is_refused(script):
    with pytest.raises(ValueError, match='base count'):
        script.bands(cells((0, 3, 0, 0)))


def test_band_with_one_cell_fewer_than_the_minimum_merges(script):
    found = script.bands(cells((1, 49, 0, 0), (2, 50, 0, 0), (3, 49, 0, 0), (4, 1, 0, 0)))
    assert [(b['low'], b['high'], b['testable_cells']) for b in found] == [
        (1, 2, 99), (3, 4, 50), (5, None, 0)]


def test_untestable_cells_do_not_fill_a_band(script):
    found = script.bands(cells((1, 10, 0, 100), (2, 50, 0, 0)))
    assert [(b['low'], b['high'], b['base_cells'], b['testable_cells']) for b in found] == [
        (1, 2, 160, 60), (3, None, 0, 0)]


def test_untestable_cells_never_count_as_recurring(script):
    frame = pl.DataFrame(
        {'base_count': [3, 3, 3], 'testable': [True, False, False],
         'recurs': [True, True, False]},
        schema={'base_count': pl.UInt64, 'testable': pl.Boolean, 'recurs': pl.Boolean})
    (only,) = script.bands(frame)
    assert (only['base_cells'], only['testable_cells'], only['recurring_cells']) == (3, 1, 1)


def test_minimum_from_cells_uses_the_rate_not_the_interval(script):
    found = script.bands(cells((1, 100, 50, 0), (2, 60, 58, 0), (3, 60, 50, 0),
                               (10, 100, 95, 0)))
    assert [(b['low'], b['high']) for b in found] == [(1, 1), (2, 2), (3, 3), (4, None)]
    assert found[-1]['wilson_low'] < script.LEVEL <= found[-1]['rate']
    assert script.pair_minimum(found) == 4


def test_minimum_from_cells_accepts_a_rate_of_exactly_the_level(script):
    assert script.pair_minimum(script.bands(cells((10, 50, 45, 3)))) == 1


def test_top_band_without_testable_cells_gives_no_minimum(script):
    assert script.pair_minimum(script.bands(cells((1, 60, 60, 0)))) is None


def test_pair_minimum_is_the_top_band_when_only_the_top_passes(script):
    assert script.pair_minimum([band(1, 4, 0.5), band(5, None, 0.95)]) == 5


def test_pair_minimum_rejects_a_rate_just_below_the_level(script):
    assert script.pair_minimum([band(1, 9, 0.95), band(10, None, 0.899)]) is None


def test_pair_minimum_stops_at_a_band_without_a_rate(script):
    found = [band(1, 1, 0.95), band(2, 3, None), band(4, None, 0.95)]
    assert script.pair_minimum(found) == 4


def test_pair_minimum_of_no_bands_is_none(script):
    assert script.pair_minimum([]) is None


def test_family_minimum_ignores_year_pair_order_and_needs_every_pair(script):
    assert script.family_minimum([3, 1]) == 3
    assert script.family_minimum([None, 2]) is None
    assert script.family_minimum([4]) == 4
    assert script.family_minimum([]) is None
