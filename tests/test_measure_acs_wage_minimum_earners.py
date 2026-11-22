'''The Stage 19 minimum-earners measurement script: the SE and band rule, on small typed rows.'''

import importlib.util
import math
from pathlib import Path

import polars as pl
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'measure_acs_wage_minimum_earners.py'
REPLICATE_NAMES = tuple(f'REPWTP{r}' for r in range(1, 81))


def load_script():
    assert SCRIPT.is_file(), 'measurement script is missing'
    spec = importlib.util.spec_from_file_location('measure_acs_wage_minimum_earners', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script():
    return load_script()


def rows(x, perwt, replicates):
    '''One category-year's headline rows: `replicates` holds 80 weights for each row.'''
    schema = {'log_wage_2010': pl.Float64, 'PERWT': pl.Float64}
    schema |= {name: pl.Int64 for name in REPLICATE_NAMES}
    data = {'log_wage_2010': x, 'PERWT': perwt}
    data |= {name: [row[index] for row in replicates]
             for index, name in enumerate(REPLICATE_NAMES)}
    return pl.DataFrame(data, schema=schema)


def weights(base, replicate=None, values=None):
    '''80 weights per row: `base[i]` in each replicate, but `values[i]` in number `replicate`.'''
    return [[values[i] if r == replicate else base[i] for r in range(1, 81)]
            for i in range(len(base))]


def record(headline_rows, meets):
    '''A category record with the given row count and target outcome.'''
    return {'INDNAICS': 'X', 'YEAR': 2023, 'headline_rows': headline_rows,
            'se': 0.0 if meets else 1.0, 'undefined': None, 'meets_se_target': meets}


def records_at(counts, meeting=None):
    '''One record per count. `meeting` is how many of them meet the target, the first ones.'''
    meeting = len(counts) if meeting is None else meeting
    return [record(count, index < meeting) for index, count in enumerate(counts)]


def spans(result):
    return [(band['start'], band['next_start'], band['categories']) for band in result]


def band(start, passes):
    '''A band that the minimum walk reads: only its start and `passes` matter.'''
    return {'start': start, 'next_start': None, 'categories': 10, 'meeting': 10 if passes else 0,
            'share': 1.0 if passes else 0.0, 'passes': passes}


def test_rule_constants_are_the_committed_values(script):
    assert (script.SE_TARGET, script.LEVEL, script.MIN_BAND_CATEGORIES) == (0.05, 0.90, 10)
    assert script.BAND_STARTS == (1, 50, 100, 200, 400, 800, 1600)
    assert script.REPLICATE_FACTOR == 4 / 80 and script.YEARS == (2023, 2024)
    assert len(script.READ_SCHEMA) == 85


def test_se_matches_hand_computed_case(script):
    odd, even = [2, 1], [1, 2]   # weights of rows 1 and 2 in odd and even replicates
    frame = rows([0.0, 1.0], [1.0, 1.0],
                 [[odd[i] if r % 2 else even[i] for r in range(1, 81)] for i in (0, 1)])
    se, reason = script.category_se(frame)
    assert reason is None and se == pytest.approx(1 / 3, abs=1e-15)


def test_one_row_is_undefined(script):
    frame = rows([10.0], [1.0], weights([1]))
    assert script.category_se(frame) == (None, 'fewer_than_two_rows')


def test_equal_wages_are_undefined(script):
    frame = rows([10.5] * 3, [1.0] * 3, weights([1] * 3))
    assert script.category_se(frame) == (None, 'constant_wage')


def test_nonpositive_replicate_denominator_is_undefined(script):
    opposite = rows([10.0, 11.0], [1.0, 1.0], weights([1, 1], replicate=7, values=(3, -3)))
    assert script.category_se(opposite) == (None, 'replicate_denominator_not_positive')
    zero = rows([10.0, 11.0], [1.0, 1.0], weights([1, 1], replicate=7, values=(0, 0)))
    assert script.category_se(zero) == (None, 'replicate_denominator_not_positive')


def test_first_undefined_reason_wins(script):
    frame = rows([10.0], [1.0], weights([1], replicate=1, values=(-1,)))
    assert script.category_se(frame) == (None, 'fewer_than_two_rows')


def test_negative_replicate_weight_with_positive_denominator_is_defined(script):
    frame = rows([10.0, 11.0], [1.0, 1.0], weights([1, 1], replicate=7, values=(5, -1)))
    se, reason = script.category_se(frame)
    # Only replicate 7 moves: (5 * 10 - 11) / 4 = 9.75 against theta 10.5.
    assert reason is None and math.isfinite(se)
    assert se == pytest.approx(math.sqrt(0.05 * 0.75 ** 2))


def test_equal_weights_give_zero_se(script):
    by_replicate = [list(range(1, 81))] * 3   # every row has the same weight in a replicate
    frame = rows([10.0, 10.5, 11.25], [2.0] * 3, by_replicate)
    assert script.category_se(frame) == (0.0, None)
    assert script.meets_target(0.0)


def test_meets_target_boundary(script):
    assert script.meets_target(0.05)
    assert not script.meets_target(0.0500001)
    assert not script.meets_target(None)


def test_bands_merge_short_bands_upward(script):
    counts = [3] * 12 + [60] * 4 + [150] * 9 + [300] * 2 + [2000] * 15
    assert spans(script.bands(records_at(counts))) == [(1, 50, 12), (50, 200, 13), (200, None, 17)]


def test_short_top_band_stays(script):
    counts = [3] * 20 + [2000] * 4
    assert spans(script.bands(records_at(counts))) == [(1, 50, 20), (50, None, 4)]


def test_empty_top_band_fails(script):
    result = script.bands(records_at([3] * 20))
    assert spans(result)[-1] == (50, None, 0)
    assert result[-1]['share'] is None and result[-1]['passes'] is False
    assert script.year_minimum(result) is None


def test_share_equal_to_level_passes(script):
    nine = script.bands(records_at([3] * 10, meeting=9))[0]
    assert nine['share'] == 0.9 and nine['passes'] is True
    eight = script.bands(records_at([3] * 10, meeting=8))[0]
    assert eight['share'] == 0.8 and eight['passes'] is False


def test_year_minimum_is_start_of_trailing_passing_run(script):
    starts = (1, 50, 100, 200)
    mixed = [band(start, passes) for start, passes in zip(starts, (True, False, True, True))]
    assert script.year_minimum(mixed) == 100
    assert script.year_minimum([band(start, True) for start in starts]) == 1


def test_no_minimum_when_top_band_fails(script):
    result = [band(1, True), band(50, True), band(100, False)]
    assert script.year_minimum(result) is None


def test_overall_minimum_is_largest_year(script):
    assert script.overall_minimum([1, 200]) == 200
    assert script.overall_minimum([50, None]) is None
