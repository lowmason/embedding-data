'''The Stage 19 minimum-earners measurement script: the SE and band rule on small typed rows, and
the authentication of the pinned Stage 17 bundle on small hand-made bundles.'''

import ast
import dataclasses
import importlib.util
import json
import math
import os
import random
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import acs_wage_fixtures
import polars as pl
import pytest
from acs_mapping_fixtures import forbid_external_access
from acs_wage_fixtures import core_row, wage_mapping

from embedding_data import acs_wage_bundle, manifest, target_io
from embedding_data.acs_wage_bundle import FILES

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'measure_acs_wage_minimum_earners.py'
REPLICATE_NAMES = tuple(f'REPWTP{r}' for r in range(1, 81))
PERSONS = 'acs_wage_persons.parquet'
REPORT = 'report.json'
OUTPUTS = 'outputs.json'
READ_SCHEMA = {
    'YEAR': pl.Int64,
    'INDNAICS': pl.String,
    'flag_headline': pl.Boolean,
    'log_wage_2010': pl.Float64,
    'PERWT': pl.Float64,
    **{name: pl.Int64 for name in REPLICATE_NAMES},
}
UNSAFE = 'unsafe run id or pin'
PIN_DIFFERS = 'outputs pin differs'
REPORT_DIFFERS = 'report differs from its inventory'
PERSONS_DIFFER = 'person table differs from its inventory'
MALFORMED = 'report is malformed'
YEARS_DIFFER = 'report years differ from 2023 and 2024'
COLUMNS_DIFFER = 'person table columns differ from the contract'
RECOUNT_DIFFERS = 'headline recount differs from the report'
COUNT_DIFFERS = 'headline category count differs from the report'
BAD_ROW = 'headline row has a non-finite wage or a non-positive weight'


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


def exact_sum(values):
    '''The correctly rounded sum, from exact rational arithmetic.'''
    return float(sum(Fraction(value) for value in values))


def reference_se(x, perwt, replicates):
    '''The spec's SE, with every sum taken exactly and then rounded once.'''
    theta = exact_sum([w * v for w, v in zip(perwt, x)]) / exact_sum(perwt)
    squares = []
    for index in range(80):
        column = [row[index] for row in replicates]
        theta_r = exact_sum([float(w) * v for w, v in zip(column, x)]) / sum(column)
        squares.append((theta_r - theta) ** 2)
    return math.sqrt(4 / 80 * exact_sum(squares))


def awkward_rows(count=24, seed=2):
    '''Rows whose sums depend on the order of addition, so a running sum shows it.'''
    rng = random.Random(seed)
    x = [round(rng.uniform(8.0, 13.0), 4) for _ in range(count)]
    perwt = [round(rng.uniform(1.0, 400.0), 3) for _ in range(count)]
    replicates = [[rng.randint(1, 900) for _ in range(80)] for _ in range(count)]
    return x, perwt, replicates


def test_undefined_reasons_are_the_spec_reasons_in_order(script):
    assert script.UNDEFINED == (
        'fewer_than_two_rows', 'constant_wage', 'replicate_denominator_not_positive')


def test_read_schema_is_the_85_columns_in_order(script):
    names = ['YEAR', 'INDNAICS', 'flag_headline', 'log_wage_2010', 'PERWT', *REPLICATE_NAMES]
    assert list(script.READ_SCHEMA) == names
    assert script.REPLICATE_COLUMNS == REPLICATE_NAMES and script.REPLICATES == 80
    types = {'YEAR': pl.Int64, 'INDNAICS': pl.String, 'flag_headline': pl.Boolean,
             'log_wage_2010': pl.Float64, 'PERWT': pl.Float64}
    assert {name: script.READ_SCHEMA[name] for name in types} == types
    assert all(script.READ_SCHEMA[name] == pl.Int64 for name in REPLICATE_NAMES)


def test_no_rows_are_undefined(script):
    assert script.category_se(rows([], [], [])) == (None, 'fewer_than_two_rows')


def test_two_equal_wages_are_undefined(script):
    frame = rows([10.5, 10.5], [1.0, 1.0], weights([1, 1]))
    assert script.category_se(frame) == (None, 'constant_wage')


def test_wages_one_ulp_apart_are_defined(script):
    frame = rows([10.5, math.nextafter(10.5, 11.0)], [1.0, 1.0], weights([1, 1]))
    se, reason = script.category_se(frame)
    assert reason is None and se is not None


def test_negative_replicate_denominator_is_undefined(script):
    frame = rows([10.0, 11.0], [1.0, 1.0], weights([1, 1], replicate=7, values=(1, -3)))
    assert script.category_se(frame) == (None, 'replicate_denominator_not_positive')


def test_every_replicate_denominator_is_checked(script):
    for replicate in (1, 80):
        frame = rows([10.0, 11.0], [1.0, 1.0],
                     weights([1, 1], replicate=replicate, values=(0, 0)))
        assert script.category_se(frame) == (None, 'replicate_denominator_not_positive')


def test_constant_wage_comes_before_the_denominator_check(script):
    frame = rows([10.5] * 3, [1.0] * 3, weights([1] * 3, replicate=7, values=(0, 0, 0)))
    assert script.category_se(frame) == (None, 'constant_wage')


def test_full_sample_mean_is_weighted_by_perwt(script):
    # theta is 0.25 with PERWT 3 and 1, and every theta_r is 0.5: SE = sqrt(4/80 * 80 / 16).
    frame = rows([0.0, 1.0], [3.0, 1.0], weights([1, 1]))
    se, reason = script.category_se(frame)
    assert reason is None and se == pytest.approx(0.5, abs=1e-15)


def test_se_is_exact_and_independent_of_row_order(script):
    x, perwt, replicates = awkward_rows()
    frame = rows(x, perwt, replicates)
    expected = (reference_se(x, perwt, replicates), None)
    assert script.category_se(frame) == expected
    assert script.category_se(frame.reverse()) == expected
    assert script.category_se(frame.sample(fraction=1.0, shuffle=True, seed=7)) == expected


def test_band_edges_belong_to_the_band_that_starts_there(script):
    after = {50: 100, 100: 200, 200: 400, 400: 800, 800: 1600, 1600: None}
    for start, next_start in after.items():
        counts = [start - 1] * 10 + [start] * 10
        assert spans(script.bands(records_at(counts)))[:2] == [(1, start, 10),
                                                               (start, next_start, 10)]


def test_one_row_and_a_huge_count_land_in_the_end_bands(script):
    result = script.bands(records_at([1] * 10 + [10 ** 7] * 3))
    assert spans(result) == [(1, 50, 10), (50, None, 3)]


def test_a_band_with_exactly_the_minimum_categories_closes(script):
    ten = script.bands(records_at([3] * 10 + [60] * 9))
    assert spans(ten) == [(1, 50, 10), (50, None, 9)]
    nine = script.bands(records_at([3] * 9 + [60] * 10))
    assert spans(nine) == [(1, 100, 19), (100, None, 0)]


def test_no_records_give_one_failing_top_band(script):
    assert script.bands([]) == [{'start': 1, 'next_start': None, 'categories': 0, 'meeting': 0,
                                 'share': None, 'passes': False}]


def test_merged_band_adds_up_its_meeting_counts(script):
    flags = [True] * 4 + [True] * 5 + [False] * 4
    counts = [60] * 4 + [150] * 9
    merged = script.bands([record(count, meets) for count, meets in zip(counts, flags)])[0]
    assert merged == {'start': 1, 'next_start': 200, 'categories': 13, 'meeting': 9,
                      'share': 9 / 13, 'passes': False}


def test_a_closed_band_is_the_documented_dict(script):
    assert script.bands(records_at([3] * 10, meeting=9))[0] == {
        'start': 1, 'next_start': 50, 'categories': 10, 'meeting': 9, 'share': 0.9,
        'passes': True}


def test_year_minimum_of_a_single_band(script):
    assert script.year_minimum([band(1, True)]) == 1
    assert script.year_minimum([band(1, False)]) is None


def test_zero_replicate_weight_with_positive_denominator_is_defined(script):
    frame = rows([10.0, 11.0], [1.0, 1.0], weights([1, 1], replicate=7, values=(5, 0)))
    se, reason = script.category_se(frame)
    # Only replicate 7 moves: (5 * 10 + 0 * 11) / 5 = 10.0 against theta 10.5.
    assert reason is None
    assert se == pytest.approx(math.sqrt(0.05 * 0.5 ** 2))


def test_overall_minimum_is_none_when_either_year_has_none(script):
    assert script.overall_minimum([None, 50]) is None
    assert script.overall_minimum([None, None]) is None
    assert script.overall_minimum([200, 1]) == 200


# Small bundles. Every one lives under `tmp_path`, and none holds a real count.

SMALL_CODES = ('6231  ', '6231', '1111', '2222', '3333', '4444', '5555', '7777', '8888')
LARGE_CODE = '9999'
LARGE_ROWS = 1600


def person(INDNAICS, YEAR, log_wage_2010, *, headline=True, **weights):
    '''One person row with the 85 read columns: `core_row` weights, overridden by `weights`.'''
    row = core_row(YEAR=YEAR, INDNAICS=INDNAICS) | weights
    row |= {'log_wage_2010': log_wage_2010, 'flag_headline': headline}
    return {name: row[name] for name in READ_SCHEMA}


def golden_people():
    '''Per year, nine categories of two rows and one of 1,600, each with a non-headline row.

    Equal default weights give every SE 0, so every category meets the target.
    '''
    people = []
    for year in (2023, 2024):
        for code in SMALL_CODES:
            people += [person(code, year, 10.0), person(code, year, 11.0),
                       person(code, year, 10.0, headline=False)]
        people += [person(LARGE_CODE, year, 10.0 + index % 2) for index in range(LARGE_ROWS)]
        people.append(person(LARGE_CODE, year, 10.0, headline=False))
    return people


def report_for(people):
    '''The `report.json` that Stage 17 writes for `people`: category counts and per-year totals.'''
    counts = {}
    for row in people:
        key = (row['INDNAICS'], row['YEAR'])
        rows_, headline_rows = counts.get(key, (0, 0))
        counts[key] = (rows_ + 1, headline_rows + row['flag_headline'])
    categories = [{'INDNAICS': code, 'YEAR': year, 'rows': rows_, 'headline_rows': headline_rows}
                  for (code, year), (rows_, headline_rows) in sorted(counts.items())]
    years = sorted({year for _, year in counts})
    return {'categories': categories,
            'headline_categories': {
                str(year): sum(1 for entry in categories
                               if entry['YEAR'] == year and entry['headline_rows'] > 0)
                for year in years}}


def publish(root, people, report=None):
    '''Write a bundle of `people` under `root/data`, with its inventory. Return its handles.'''
    directory = root / 'data' / 'derived/acs/wage-microdata/fixture'
    directory.mkdir(parents=True)
    pl.from_dicts(people, schema=READ_SCHEMA).write_parquet(directory / PERSONS)
    target_io.write_json(directory / REPORT, report_for(people) if report is None else report)
    target_io.write_json(directory / 'inputs.json', {})
    target_io.write_json(directory / OUTPUTS, target_io.inventory(directory, list(FILES)))
    return {'data_dir': root / 'data', 'directory': directory, 'run': 'fixture',
            'pin': manifest.sha256_file(directory / OUTPUTS)}


def rehash(directory):
    '''Rewrite a bundle's inventory after an edit, and return the new detached pin.'''
    target_io.write_json(directory / OUTPUTS, target_io.inventory(directory, list(FILES)))
    return manifest.sha256_file(directory / OUTPUTS)


def forge_persons(bundle, change):
    '''Rewrite the person table through `change`, then the inventory. Return the new pin.'''
    file = bundle['directory'] / PERSONS
    change(pl.read_parquet(file)).write_parquet(file)
    return rehash(bundle['directory'])


def forge_report(bundle, change):
    '''Edit the report in place through `change`, then rewrite the inventory. Return the pin.'''
    file = bundle['directory'] / REPORT
    report = json.loads(file.read_text())
    change(report)
    target_io.write_json(file, report)
    return rehash(bundle['directory'])


def forge_report_text(bundle, content):
    '''Replace the report's bytes, then rewrite the inventory. Return the new pin.'''
    (bundle['directory'] / REPORT).write_bytes(content)
    return rehash(bundle['directory'])


def edit_outputs(bundle, change):
    '''Edit `outputs.json` in place and leave the files alone. Return the edited file's pin.'''
    outputs = bundle['directory'] / OUTPUTS
    inventory = json.loads(outputs.read_text())
    change(inventory)
    target_io.write_json(outputs, inventory)
    return manifest.sha256_file(outputs)


def set_value(column, value, *, headline=True):
    '''A change that sets `column` in the first row whose `flag_headline` is `headline`.'''
    def change(frame):
        position = frame['flag_headline'].to_list().index(headline)
        values = frame[column].to_list()
        values[position] = value
        return frame.with_columns(pl.Series(column, values, dtype=frame.schema[column]))
    return change


def entry_for(report, code, year):
    return next(entry for entry in report['categories']
                if entry['INDNAICS'] == code and entry['YEAR'] == year)


def append_byte(file):
    file.write_bytes(file.read_bytes() + b'\0')


def attempt(script, bundle, pin=None, run=None):
    '''Run the four checks in the order of the command line. Return what they produce.'''
    inputs = script.authenticate(bundle['data_dir'], bundle['run'] if run is None else run,
                                 bundle['pin'] if pin is None else pin)
    report = script.load_report(inputs.report)
    headline = script.headline_frame(inputs.persons)
    script.self_check(report, headline)
    return inputs, report, headline


def assert_refused(script, bundle, reason, pin=None, run=None):
    with pytest.raises(script.Refused) as refusal:
        attempt(script, bundle, pin=pin, run=run)
    assert str(refusal.value) == reason


@pytest.fixture
def golden(tmp_path):
    return publish(tmp_path, golden_people())


def test_authenticate_returns_pinned_files(script, golden):
    inputs = script.authenticate(golden['data_dir'], golden['run'], golden['pin'])
    directory = golden['directory']
    assert inputs.persons == directory / PERSONS
    assert inputs.report == directory / REPORT
    assert inputs.outputs_sha256 == golden['pin']
    assert inputs.report_sha256 == manifest.sha256_file(directory / REPORT)
    assert inputs.persons_sha256 == manifest.sha256_file(directory / PERSONS)


def test_unsafe_run_id_refused(script, golden):
    assert_refused(script, golden, UNSAFE, run='../fixture')


def test_wrong_pin_refused(script, golden):
    assert_refused(script, golden, PIN_DIFFERS, pin='0' * 64)


def test_changed_report_refused(script, golden):
    append_byte(golden['directory'] / REPORT)
    assert_refused(script, golden, REPORT_DIFFERS)


def test_changed_persons_refused(script, golden):
    append_byte(golden['directory'] / PERSONS)
    assert_refused(script, golden, PERSONS_DIFFER)


def test_size_is_checked(script, golden):
    pin = edit_outputs(golden, lambda inventory: inventory[REPORT].update(
        size=inventory[REPORT]['size'] + 1))
    assert_refused(script, golden, REPORT_DIFFERS, pin=pin)


def test_pin_is_checked_before_files(script, golden):
    append_byte(golden['directory'] / PERSONS)
    assert_refused(script, golden, PIN_DIFFERS, pin='0' * 64)


def drop_categories(report):
    del report['categories']


def string_headline_rows(report):
    report['categories'][0]['headline_rows'] = '2'


def repeat_entry(report):
    report['categories'].append(dict(report['categories'][0]))


@pytest.mark.parametrize('change', [drop_categories, string_headline_rows, repeat_entry],
                         ids=['missing_categories', 'string_headline_rows', 'entry_twice'])
def test_malformed_report_refused(script, golden, change):
    assert_refused(script, golden, MALFORMED, pin=forge_report(golden, change))


def drop_2024(report):
    del report['headline_categories']['2024']
    report['categories'] = [entry for entry in report['categories'] if entry['YEAR'] != 2024]


def test_one_year_report_refused(script, golden):
    assert_refused(script, golden, YEARS_DIFFER, pin=forge_report(golden, drop_2024))


def test_retyped_column_refused(script, golden):
    pin = forge_persons(
        golden, lambda frame: frame.with_columns(pl.col('REPWTP5').cast(pl.Float64)))
    assert_refused(script, golden, COLUMNS_DIFFER, pin=pin)


def one_more(report):
    entry_for(report, '1111', 2023)['headline_rows'] += 1


def renamed(report):
    entry_for(report, '6231  ', 2023)['INDNAICS'] = '6231 '


def zeroed(report):
    entry_for(report, '1111', 2023)['headline_rows'] = 0


@pytest.mark.parametrize('change', [one_more, renamed, zeroed],
                         ids=['plus_one', 'renamed_padding', 'zero_headline_rows'])
def test_recount_differs_refused(script, golden, change):
    assert_refused(script, golden, RECOUNT_DIFFERS, pin=forge_report(golden, change))


def test_headline_category_count_refused(script, golden):
    pin = forge_report(golden, lambda report: report['headline_categories'].update(
        {'2023': report['headline_categories']['2023'] + 1}))
    assert_refused(script, golden, COUNT_DIFFERS, pin=pin)


@pytest.mark.parametrize('column, value', [('log_wage_2010', math.nan),
                                           ('log_wage_2010', math.inf), ('PERWT', 0.0)],
                         ids=['nan_wage', 'inf_wage', 'zero_weight'])
def test_bad_wage_or_weight_refused(script, golden, column, value):
    pin = forge_persons(golden, set_value(column, value))
    assert_refused(script, golden, BAD_ROW, pin=pin)


def test_non_headline_rows_are_not_checked(script, golden):
    def change(frame):
        frame = set_value('log_wage_2010', math.nan, headline=False)(frame)
        return set_value('PERWT', 0.0, headline=False)(frame)
    attempt(script, golden, pin=forge_persons(golden, change))


def test_padded_strings_stay_distinct(script, golden):
    _, _, headline = attempt(script, golden)
    assert headline.select('INDNAICS', 'YEAR').unique().height == 20
    assert {'6231', '6231  '} <= set(headline['INDNAICS'].to_list())


# Input shapes beyond the plan's named tests, one test for each shape the rules' words cover.

def test_inputs_are_frozen_and_the_reason_is_the_only_message(script, golden):
    inputs = script.authenticate(golden['data_dir'], golden['run'], golden['pin'])
    with pytest.raises(dataclasses.FrozenInstanceError):
        inputs.report = inputs.persons
    with pytest.raises(script.Refused) as refusal:
        attempt(script, golden, pin='0' * 64)
    assert refusal.value.args == (PIN_DIFFERS,)


def test_report_is_returned_as_written(script, golden):
    _, report, headline = attempt(script, golden)
    assert report == report_for(golden_people())
    assert script.self_check(report, headline) is None


@pytest.mark.parametrize('run', ['', '-fixture', '_fixture', 'fixture/', 'a/../fixture',
                                 'fix ture', 'fixture\n', '.', '..'])
def test_unsafe_run_id_shapes_refused(script, golden, run):
    assert_refused(script, golden, UNSAFE, run=run)


@pytest.mark.parametrize('shape', [str.upper, lambda pin: pin[:63], lambda pin: pin + 'a',
                                   lambda pin: pin + '\n', lambda pin: '', lambda pin: 'g' * 64],
                         ids=['upper_case', 'short', 'long', 'trailing_newline', 'empty',
                              'not_hex'])
def test_unsafe_pin_shapes_refused(script, golden, shape):
    assert_refused(script, golden, UNSAFE, pin=shape(golden['pin']))


def test_unsafe_run_id_is_refused_before_the_pin(script, golden):
    assert_refused(script, golden, UNSAFE, pin='0' * 64, run='../fixture')


@pytest.mark.parametrize('run', ['stage-19_run-2', 'a', '7'],
                         ids=['underscore_and_dashes', 'one_letter', 'one_digit'])
def test_safe_run_ids_are_accepted(script, golden, run):
    copy = golden['data_dir'] / 'derived/acs/wage-microdata' / run
    shutil.copytree(golden['directory'], copy)
    inputs = script.authenticate(golden['data_dir'], run, golden['pin'])
    assert inputs.persons == copy / PERSONS


def test_missing_outputs_refused(script, golden):
    (golden['directory'] / OUTPUTS).unlink()
    assert_refused(script, golden, PIN_DIFFERS)


def test_absent_run_refused(script, golden):
    assert_refused(script, golden, PIN_DIFFERS, run='absent')


@pytest.mark.parametrize('name, reason', [(REPORT, REPORT_DIFFERS), (PERSONS, PERSONS_DIFFER)])
def test_same_size_change_is_refused(script, golden, name, reason):
    file = golden['directory'] / name
    content = bytearray(file.read_bytes())
    content[len(content) // 2] ^= 1
    file.write_bytes(bytes(content))
    assert file.stat().st_size == len(content)
    assert_refused(script, golden, reason)


def test_persons_size_is_checked(script, golden):
    pin = edit_outputs(golden, lambda inventory: inventory[PERSONS].update(
        size=inventory[PERSONS]['size'] + 1))
    assert_refused(script, golden, PERSONS_DIFFER, pin=pin)


@pytest.mark.parametrize('name, reason', [(REPORT, REPORT_DIFFERS), (PERSONS, PERSONS_DIFFER)])
def test_size_below_the_record_is_refused(script, golden, name, reason):
    pin = edit_outputs(golden, lambda inventory: inventory[name].update(
        size=inventory[name]['size'] - 1))
    assert_refused(script, golden, reason, pin=pin)


def test_report_is_checked_before_persons(script, golden):
    append_byte(golden['directory'] / REPORT)
    append_byte(golden['directory'] / PERSONS)
    assert_refused(script, golden, REPORT_DIFFERS)


@pytest.mark.parametrize('content', [b'\xff\xfe not json', b'not json', b'[]', b'"text"', b'{}',
                                     b'{"report.json": "text"}'],
                         ids=['not_utf8', 'not_json', 'array', 'string', 'empty_object',
                              'record_not_an_object'])
def test_malformed_outputs_refused_for_the_report_record(script, golden, content):
    outputs = golden['directory'] / OUTPUTS
    outputs.write_bytes(content)
    assert_refused(script, golden, REPORT_DIFFERS, pin=manifest.sha256_file(outputs))


def test_record_without_size_refused(script, golden):
    pin = edit_outputs(golden, lambda inventory: inventory[REPORT].pop('size'))
    assert_refused(script, golden, REPORT_DIFFERS, pin=pin)


def test_record_without_hash_refused(script, golden):
    pin = edit_outputs(golden, lambda inventory: inventory[REPORT].pop('sha256'))
    assert_refused(script, golden, REPORT_DIFFERS, pin=pin)


def test_missing_report_record_refused(script, golden):
    pin = edit_outputs(golden, lambda inventory: inventory.pop(REPORT))
    assert_refused(script, golden, REPORT_DIFFERS, pin=pin)


def test_missing_persons_record_refused(script, golden):
    pin = edit_outputs(golden, lambda inventory: inventory.pop(PERSONS))
    assert_refused(script, golden, PERSONS_DIFFER, pin=pin)


def test_missing_report_file_refused(script, golden):
    (golden['directory'] / REPORT).unlink()
    assert_refused(script, golden, REPORT_DIFFERS)


def test_missing_persons_file_refused(script, golden):
    (golden['directory'] / PERSONS).unlink()
    assert_refused(script, golden, PERSONS_DIFFER)


@pytest.mark.parametrize('state', ['corrupt', 'absent'])
def test_no_other_file_of_the_run_is_read(script, golden, state):
    other = golden['directory'] / 'inputs.json'
    if state == 'corrupt':
        other.write_text('not json at all')
    else:
        other.unlink()
    attempt(script, golden)


def drop_key(entry, key):
    del entry[key]


def replace_entry(position, value):
    def change(report):
        report['categories'][position] = value
    return change


def edit_first_entry(**values):
    def change(report):
        report['categories'][0].update(values)
    return change


MALFORMED_CHANGES = {
    'categories_is_an_object': lambda report: report.update(categories={}),
    'categories_is_null': lambda report: report.update(categories=None),
    'entry_is_a_string': replace_entry(0, 'text'),
    'indnaics_is_an_integer': edit_first_entry(INDNAICS=6231),
    'indnaics_is_missing': lambda report: drop_key(report['categories'][0], 'INDNAICS'),
    'year_is_a_string': edit_first_entry(YEAR='2023'),
    'year_is_a_float': edit_first_entry(YEAR=2023.0),
    'year_is_a_boolean': edit_first_entry(YEAR=True),
    'year_is_missing': lambda report: drop_key(report['categories'][0], 'YEAR'),
    'headline_rows_is_a_float': edit_first_entry(headline_rows=2.0),
    'headline_rows_is_a_boolean': edit_first_entry(headline_rows=True),
    'headline_rows_is_negative': edit_first_entry(headline_rows=-1),
    'headline_rows_is_missing': lambda report: drop_key(report['categories'][0], 'headline_rows'),
    'totals_are_missing': lambda report: drop_key(report, 'headline_categories'),
    'totals_are_a_list': lambda report: report.update(headline_categories=[10, 10]),
    'a_total_is_a_string': lambda report: report['headline_categories'].update({'2023': '10'}),
    'a_total_is_a_boolean': lambda report: report['headline_categories'].update({'2023': True}),
    'a_total_is_a_float': lambda report: report['headline_categories'].update({'2023': 10.0}),
    'key_twice_with_other_counts': lambda report: report['categories'].append(
        {'INDNAICS': '1111', 'YEAR': 2023, 'rows': 3, 'headline_rows': 0}),
}


@pytest.mark.parametrize('change', MALFORMED_CHANGES.values(), ids=MALFORMED_CHANGES.keys())
def test_malformed_report_shapes_refused(script, golden, change):
    assert_refused(script, golden, MALFORMED, pin=forge_report(golden, change))


@pytest.mark.parametrize('content', [b'', b'not json', b'\xff', b'[]', b'null', b'7',
                                     b'{"categories": []}'],
                         ids=['empty', 'not_json', 'not_utf8', 'array', 'null', 'number',
                              'one_key'])
def test_unreadable_report_refused(script, golden, content):
    pin = forge_report_text(golden, content)
    assert_refused(script, golden, MALFORMED, pin=pin)


def test_malformed_report_is_refused_without_the_json_error(script, golden):
    pin = forge_report_text(golden, b'not json')
    with pytest.raises(script.Refused) as refusal:
        attempt(script, golden, pin=pin)
    assert refusal.value.__suppress_context__ and refusal.value.__cause__ is None


def test_malformed_comes_before_the_years(script, golden):
    def change(report):
        drop_2024(report)
        string_headline_rows(report)
    assert_refused(script, golden, MALFORMED, pin=forge_report(golden, change))


YEAR_CHANGES = {
    'extra_year_total': lambda report: report['headline_categories'].update({'2025': 0}),
    'missing_2023_total': lambda report: report['headline_categories'].pop('2023'),
    'entry_for_another_year': lambda report: report['categories'].append(
        {'INDNAICS': '0000', 'YEAR': 2022, 'rows': 1, 'headline_rows': 0}),
    'entry_for_a_later_year': lambda report: report['categories'].append(
        {'INDNAICS': '0000', 'YEAR': 2025, 'rows': 1, 'headline_rows': 0}),
    'empty_totals': lambda report: report.update(headline_categories={}),
}


@pytest.mark.parametrize('change', YEAR_CHANGES.values(), ids=YEAR_CHANGES.keys())
def test_other_year_sets_refused(script, golden, change):
    assert_refused(script, golden, YEARS_DIFFER, pin=forge_report(golden, change))


def retype(column, dtype):
    return lambda frame: frame.with_columns(pl.col(column).cast(dtype))


COLUMN_CHANGES = {
    'missing_perwt': lambda frame: frame.drop('PERWT'),
    'missing_first_replicate': lambda frame: frame.drop('REPWTP1'),
    'missing_last_replicate': lambda frame: frame.drop('REPWTP80'),
    'missing_year': lambda frame: frame.drop('YEAR'),
    'renamed_flag': lambda frame: frame.rename({'flag_headline': 'headline'}),
    'year_int32': retype('YEAR', pl.Int32),
    'flag_int8': retype('flag_headline', pl.Int8),
    'wage_float32': retype('log_wage_2010', pl.Float32),
    'perwt_int64': retype('PERWT', pl.Int64),
    'code_categorical': retype('INDNAICS', pl.Categorical),
    'last_replicate_float64': retype('REPWTP80', pl.Float64),
}


@pytest.mark.parametrize('change', COLUMN_CHANGES.values(), ids=COLUMN_CHANGES.keys())
def test_column_shapes_refused(script, golden, change):
    assert_refused(script, golden, COLUMNS_DIFFER, pin=forge_persons(golden, change))


def test_extra_columns_are_ignored_and_not_read(script, golden):
    def change(frame):
        return frame.with_columns(pl.lit('x').alias('extra'), pl.col('YEAR').alias('YEAR_copy'))
    pin = forge_persons(golden, change)
    assert 'extra' in pl.read_parquet(golden['directory'] / PERSONS).columns
    _, _, headline = attempt(script, golden, pin=pin)
    assert headline.columns == list(READ_SCHEMA)


def test_columns_come_back_in_contract_order_with_contract_types(script, golden):
    pin = forge_persons(golden, lambda frame: frame.select(reversed(frame.columns)))
    _, _, headline = attempt(script, golden, pin=pin)
    assert headline.columns == list(READ_SCHEMA)
    assert dict(headline.schema) == READ_SCHEMA


def test_headline_frame_keeps_only_headline_rows(script, golden):
    _, _, headline = attempt(script, golden)
    assert headline.height == sum(row['flag_headline'] for row in golden_people())
    assert headline['flag_headline'].all()


def test_null_headline_flag_is_not_a_headline_row(script, golden):
    pin = forge_persons(golden, set_value('flag_headline', None, headline=False))
    _, _, headline = attempt(script, golden, pin=pin)
    assert headline.height == sum(row['flag_headline'] for row in golden_people())


def drop_entry(code, year):
    def change(report):
        report['categories'].remove(entry_for(report, code, year))
    return change


def lowered(report):
    entry_for(report, '9999', 2024)['headline_rows'] -= 1


def phantom(report):
    report['categories'].append({'INDNAICS': 'ZZZZ', 'YEAR': 2023, 'rows': 5, 'headline_rows': 3})


RECOUNT_CHANGES = {
    'headline_key_has_no_entry': drop_entry('2222', 2024),
    'entry_has_no_headline_rows_in_the_table': phantom,
    'large_category_minus_one': lowered,
    'padded_key_has_no_entry': drop_entry('6231  ', 2024),
}


@pytest.mark.parametrize('change', RECOUNT_CHANGES.values(), ids=RECOUNT_CHANGES.keys())
def test_recount_set_differences_refused(script, golden, change):
    assert_refused(script, golden, RECOUNT_DIFFERS, pin=forge_report(golden, change))


def test_report_entry_without_headline_rows_is_not_counted(script, golden):
    def shared_node(report):
        report['categories'].append({'INDNAICS': '0000', 'YEAR': 2023, 'rows': 3,
                                     'headline_rows': 0})
    attempt(script, golden, pin=forge_report(golden, shared_node))


def test_recount_ignores_the_order_of_entries(script, golden):
    pin = forge_report(golden, lambda report: report['categories'].reverse())
    attempt(script, golden, pin=pin)


@pytest.mark.parametrize('year, delta', [('2023', -1), ('2024', 1), ('2024', -1)],
                         ids=['2023_minus_one', '2024_plus_one', '2024_minus_one'])
def test_headline_category_count_refused_in_each_year(script, golden, year, delta):
    pin = forge_report(golden, lambda report: report['headline_categories'].update(
        {year: report['headline_categories'][year] + delta}))
    assert_refused(script, golden, COUNT_DIFFERS, pin=pin)


def test_a_year_with_no_headline_rows_counts_zero(script, tmp_path):
    people = [row for row in golden_people() if row['YEAR'] == 2023]
    people += [person('1111', 2024, 10.0, headline=False)]
    bundle = publish(tmp_path, people)
    _, report, _ = attempt(script, bundle)
    assert report['headline_categories'] == {'2023': 10, '2024': 0}


@pytest.mark.parametrize('column, value', [('log_wage_2010', None), ('log_wage_2010', -math.inf),
                                           ('PERWT', None), ('PERWT', -1.0),
                                           ('PERWT', math.nan)],
                         ids=['null_wage', 'minus_inf_wage', 'null_weight', 'negative_weight',
                              'nan_weight'])
def test_other_bad_wages_and_weights_refused(script, golden, column, value):
    pin = forge_persons(golden, set_value(column, value))
    assert_refused(script, golden, BAD_ROW, pin=pin)


def test_the_last_headline_row_is_checked_too(script, golden):
    def change(frame):
        position = len(frame) - 1 - frame['flag_headline'].to_list()[::-1].index(True)
        values = frame['PERWT'].to_list()
        values[position] = 0.0
        return frame.with_columns(pl.Series('PERWT', values, dtype=pl.Float64))
    assert_refused(script, golden, BAD_ROW, pin=forge_persons(golden, change))


def test_negative_wage_and_tiny_weight_pass(script, golden):
    def change(frame):
        frame = set_value('log_wage_2010', -3.5)(frame)
        return set_value('PERWT', 1e-9)(frame)
    attempt(script, golden, pin=forge_persons(golden, change))


def test_the_recount_comes_before_the_row_check(script, golden):
    forge_persons(golden, set_value('PERWT', 0.0))
    pin = forge_report(golden, one_more)
    assert_refused(script, golden, RECOUNT_DIFFERS, pin=pin)


def test_the_category_count_comes_before_the_row_check(script, golden):
    forge_persons(golden, set_value('PERWT', 0.0))
    pin = forge_report(golden, lambda report: report['headline_categories'].update(
        {'2023': report['headline_categories']['2023'] + 1}))
    assert_refused(script, golden, COUNT_DIFFERS, pin=pin)


def test_the_recount_comes_before_the_category_count(script, golden):
    def change(report):
        one_more(report)
        report['headline_categories']['2023'] += 1
    assert_refused(script, golden, RECOUNT_DIFFERS, pin=forge_report(golden, change))


def test_padding_is_kept_on_both_sides_of_the_recount(script, golden):
    _, report, headline = attempt(script, golden)
    assert '6231  ' in {entry['INDNAICS'] for entry in report['categories']}
    assert '6231  ' in headline['INDNAICS'].to_list()


def test_columns_are_checked_before_the_rows(script, golden):
    def change(frame):
        return set_value('PERWT', 0.0)(frame).with_columns(pl.col('REPWTP5').cast(pl.Float64))
    assert_refused(script, golden, COLUMNS_DIFFER, pin=forge_persons(golden, change))


def test_category_totals_that_shift_both_years_are_refused(script, golden):
    assert report_for(golden_people())['headline_categories'] == {'2023': 10, '2024': 10}
    pin = forge_report(golden, lambda report: report['headline_categories'].update(
        {'2023': 11, '2024': 9}))
    assert_refused(script, golden, COUNT_DIFFERS, pin=pin)


def weighted_people():
    '''Headline rows whose weights differ by row and by replicate, as delivered.

    `PERWT` has a fraction, one replicate weight is 0 and one is negative, so that a scaling,
    a rounding or a cast shows in the values or in the types.
    '''
    people = []
    for year in (2023, 2024):
        for index in range(3):
            weights = {name: 1000 * (index + 1) + 7 * number + year % 5
                       for number, name in enumerate(REPLICATE_NAMES, start=1)}
            weights['PERWT'] = 37.625 + 11.5 * index + (year - 2023) / 8
            people.append(person('1111', year, 10.0 + index, **weights))
        people[-3]['REPWTP1'] = 0
        people[-2]['REPWTP80'] = -5
        people.append(person('1111', year, 10.0, headline=False))
    return people


def test_headline_frame_returns_the_delivered_weights(script, tmp_path):
    people = weighted_people()
    delivered = [row for row in people if row['flag_headline']]
    assert len({row['PERWT'] for row in delivered}) == len(delivered)
    _, _, headline = attempt(script, publish(tmp_path, people))
    for column in ('PERWT', *REPLICATE_NAMES):
        assert headline[column].to_list() == [row[column] for row in delivered]
        assert headline.schema[column] == READ_SCHEMA[column]


# Task 3: the category records, the kept counts and the command line.

RECORD_KEYS = {'INDNAICS', 'YEAR', 'headline_rows', 'se', 'undefined', 'meets_se_target'}
KEPT_KEYS = {'headline_categories', 'headline_rows', 'shared_node_categories', 'kept_categories',
             'kept_category_share', 'kept_headline_rows', 'kept_headline_row_share',
             'count_meets_se_misses', 'count_misses_se_meets', 'missed'}
NO_REASONS = {'fewer_than_two_rows': 0, 'constant_wage': 0,
              'replicate_denominator_not_positive': 0}
CONSTANTS = {'se_target': 0.05, 'level': 0.9, 'band_starts': [1, 50, 100, 200, 400, 800, 1600],
             'min_band_categories': 10, 'replicate_factor': 0.05, 'years': [2023, 2024]}
GOLDEN_ROWS = len(SMALL_CODES) * 2 + LARGE_ROWS
GOLDEN_KEPT = {'headline_categories': 10, 'headline_rows': GOLDEN_ROWS,
               'shared_node_categories': 0, 'kept_categories': 10, 'kept_category_share': 1.0,
               'kept_headline_rows': GOLDEN_ROWS, 'kept_headline_row_share': 1.0,
               'count_meets_se_misses': 0, 'count_misses_se_meets': 0, 'missed': []}
NO_MINIMUM_KEPT = dict.fromkeys(KEPT_KEYS - {'headline_categories', 'headline_rows',
                                             'shared_node_categories'})


def command_line(bundle, pin=None, run=None):
    return ['--data-dir', str(bundle['data_dir']), '--run', bundle['run'] if run is None else run,
            '--outputs-sha256', bundle['pin'] if pin is None else pin]


def run_main(script, capsys, bundle, pin=None):
    '''Run `main` on a bundle. Return its status and its one JSON line, parsed.'''
    status = script.main(command_line(bundle, pin))
    captured = capsys.readouterr()
    assert captured.err == '' and captured.out.endswith('\n')
    lines = captured.out.splitlines()
    assert len(lines) == 1
    result = json.loads(lines[0])
    assert lines[0] == json.dumps(result, sort_keys=True)
    return status, result


def run_command(arguments, *, threads=None, hash_seed=None):
    '''Run the script as a program, with a Polars thread count and a Python hash seed.'''
    env = dict(os.environ)
    if threads is not None:
        env['POLARS_MAX_THREADS'] = str(threads)
    if hash_seed is not None:
        env['PYTHONHASHSEED'] = str(hash_seed)
    return subprocess.run([sys.executable, str(SCRIPT), *arguments], cwd=ROOT, env=env,
                          capture_output=True, text=True, check=False)


def tree(data_dir):
    '''Every file under `data_dir` as a sorted list of (relative path, SHA-256).'''
    return sorted((path.relative_to(data_dir).as_posix(), manifest.sha256_file(path))
                  for path in data_dir.rglob('*') if path.is_file())


def swing(index):
    '''Replicate weights of 2 and 1 that swap with each replicate, in opposite phase by parity.'''
    return {name: 1 + (index + number) % 2 for number, name in enumerate(REPLICATE_NAMES, start=1)}


def category(code, year, count, *, swinging=False):
    '''`count` headline rows alternating between the wages 10 and 11.

    For an even `count`, equal weights give SE 0 and swinging weights give SE 1/3.
    '''
    return [person(code, year, 10.0 + index % 2, **(swing(index) if swinging else {}))
            for index in range(count)]


def headline_of(people):
    return pl.from_dicts(people, schema=READ_SCHEMA)


def noisy_people(seed=5):
    '''`golden_people` with row-by-row wages and weights in the 1,600-row categories.

    Their SEs are above 0 and below the target, and the sums depend on the order of addition.
    '''
    rng = random.Random(seed)
    people = golden_people()
    for row in people:
        if row['INDNAICS'] == LARGE_CODE and row['flag_headline']:
            row['log_wage_2010'] = round(rng.uniform(10.0, 12.0), 4)
            row['PERWT'] = round(rng.uniform(50.0, 150.0), 3)
            row |= {name: rng.randint(50, 150) for name in REPLICATE_NAMES}
    return people


def crowded_people():
    '''`noisy_people` and 60 more two-row categories in each year, so that group order shows.'''
    people = noisy_people()
    for year in (2023, 2024):
        for number in range(60):
            people += category(f'3{number:03d}', year, 2)
    return people


def banded_people(hard_year):
    '''Per year: ten 2-row categories, ten 60-row ones and one 1,600-row one.

    In `hard_year` the 2-row categories miss the target, so the band that starts at 1 fails and
    the year's minimum is 50. In the other year one 60-row category misses it: 9 of 10 meet, and
    every band passes.
    '''
    people = []
    for year in (2023, 2024):
        hard = year == hard_year
        for number in range(10):
            people += category(f'1{number:03d}', year, 2, swinging=hard)
            people += category(f'2{number:03d}', year, 60, swinging=not hard and number == 0)
        people += category(LARGE_CODE, year, LARGE_ROWS)
    return people


def without_second_row(people, year, codes=('1111', '2222')):
    '''Make the second headline row of each of `codes` in `year` a non-headline row.'''
    for row in people:
        if row['YEAR'] == year and row['INDNAICS'] in codes and row['log_wage_2010'] == 11.0:
            row['flag_headline'] = False
    return people


def keyed(code, headline_rows, meets, year=2023):
    return record(headline_rows, meets) | {'INDNAICS': code, 'YEAR': year}


def shared_node(code, year):
    return {'INDNAICS': code, 'YEAR': year, 'rows': 3, 'headline_rows': 0}


def test_kept_counts_and_disagreements(script):
    records = [keyed('1111', 30, False), keyed('2222', 60, True), keyed('3333', 60, False),
               keyed('4444', 90, True)]
    report = {'categories': [shared_node('0000', 2023)]}
    assert script.kept(records, report, 2023, 50) == {
        'headline_categories': 4, 'headline_rows': 240, 'shared_node_categories': 1,
        'kept_categories': 3, 'kept_category_share': 0.75, 'kept_headline_rows': 210,
        'kept_headline_row_share': 0.875, 'count_meets_se_misses': 1,
        'count_misses_se_meets': 0, 'missed': [{'INDNAICS': '1111', 'headline_rows': 30}]}
    assert script.kept(records, report, 2023, None) == {
        'headline_categories': 4, 'headline_rows': 240, 'shared_node_categories': 1,
        'kept_categories': None, 'kept_category_share': None, 'kept_headline_rows': None,
        'kept_headline_row_share': None, 'count_meets_se_misses': None,
        'count_misses_se_meets': None, 'missed': None}


def test_kept_counts_only_the_year_asked(script):
    records = [keyed('1111', 30, True), keyed('2222', 70, False),
               keyed('1111', 80, True, 2024), keyed('3333', 20, False, 2024),
               keyed('4444', 200, True, 2024)]
    report = {'categories': [
        shared_node('0000', 2023), shared_node('0001', 2023), shared_node('0000', 2024),
        {'INDNAICS': '1111', 'YEAR': 2023, 'rows': 5, 'headline_rows': 2}]}
    assert script.kept(records, report, 2023, 50) == {
        'headline_categories': 2, 'headline_rows': 100, 'shared_node_categories': 2,
        'kept_categories': 1, 'kept_category_share': 1 / 2, 'kept_headline_rows': 70,
        'kept_headline_row_share': 70 / 100, 'count_meets_se_misses': 1,
        'count_misses_se_meets': 1, 'missed': [{'INDNAICS': '1111', 'headline_rows': 30}]}
    assert script.kept(records, report, 2024, 50) == {
        'headline_categories': 3, 'headline_rows': 300, 'shared_node_categories': 1,
        'kept_categories': 2, 'kept_category_share': 2 / 3, 'kept_headline_rows': 280,
        'kept_headline_row_share': 280 / 300, 'count_meets_se_misses': 0,
        'count_misses_se_meets': 0, 'missed': [{'INDNAICS': '3333', 'headline_rows': 20}]}


def test_kept_at_the_minimum_is_kept(script):
    records = [keyed('a', 49, True), keyed('b', 50, True), keyed('c', 51, True)]
    result = script.kept(records, {'categories': []}, 2023, 50)
    assert result['kept_categories'] == 2 and result['kept_headline_rows'] == 101
    assert result['missed'] == [{'INDNAICS': 'a', 'headline_rows': 49}]


def test_kept_tallies_each_disagreement_apart(script):
    records = ([keyed(f'a{n}', 60, False) for n in range(3)]
               + [keyed(f'b{n}', 10, True) for n in range(2)]
               + [keyed('c', 60, True), keyed('d', 10, False)])
    result = script.kept(records, {'categories': []}, 2023, 50)
    assert (result['count_meets_se_misses'], result['count_misses_se_meets']) == (3, 2)


def test_kept_missed_are_sorted_by_code_with_their_padding(script):
    records = [keyed('6231  ', 5, False), keyed('1111', 7, False), keyed('6231', 9, False),
               keyed('0200', 1, False)]
    missed = script.kept(records, {'categories': []}, 2023, 50)['missed']
    assert missed == [{'INDNAICS': '0200', 'headline_rows': 1},
                      {'INDNAICS': '1111', 'headline_rows': 7},
                      {'INDNAICS': '6231', 'headline_rows': 9},
                      {'INDNAICS': '6231  ', 'headline_rows': 5}]


def test_kept_of_a_year_without_headline_categories(script):
    report = {'categories': [shared_node('0000', 2023)]}
    assert script.kept([], report, 2023, 1) == {
        'headline_categories': 0, 'headline_rows': 0, 'shared_node_categories': 1,
        'kept_categories': 0, 'kept_category_share': None, 'kept_headline_rows': 0,
        'kept_headline_row_share': None, 'count_meets_se_misses': 0, 'count_misses_se_meets': 0,
        'missed': []}


def test_category_records_are_one_per_year_and_code_in_sorted_order(script):
    people = (category('6231  ', 2024, 4) + category('1111', 2023, 2) + category('6231', 2024, 2)
              + category('6231  ', 2023, 6) + category('6231', 2023, 2)
              + category('1111', 2024, 2))
    records = script.category_records(headline_of(people))
    assert [(r['YEAR'], r['INDNAICS'], r['headline_rows']) for r in records] == [
        (2023, '1111', 2), (2023, '6231', 2), (2023, '6231  ', 6),
        (2024, '1111', 2), (2024, '6231', 2), (2024, '6231  ', 4)]
    assert all(set(r) == RECORD_KEYS for r in records)


def test_category_records_hold_the_se_the_reason_and_the_target_flag(script):
    people = (category('1111', 2023, 2, swinging=True) + category('2222', 2023, 4)
              + [person('3333', 2023, 10.0)])
    by_code = {r['INDNAICS']: r for r in script.category_records(headline_of(people))}
    swinging, equal, single = by_code['1111'], by_code['2222'], by_code['3333']
    assert swinging['se'] == pytest.approx(1 / 3)
    assert (swinging['undefined'], swinging['meets_se_target']) == (None, False)
    assert (equal['se'], equal['undefined'], equal['meets_se_target']) == (0.0, None, True)
    assert (single['se'], single['undefined'], single['meets_se_target']) == (
        None, 'fewer_than_two_rows', False)


def test_category_records_of_no_rows_are_empty(script):
    assert script.category_records(headline_of([])) == []


def test_golden_run_exits_zero(script, capsys, golden):
    status, result = run_main(script, capsys, golden)
    assert status == 0 and result['complete'] is True and result['minimum'] == 1
    assert set(result) == {'complete', 'constants', 'inputs', 'years', 'minimum', 'categories'}
    assert result['constants'] == CONSTANTS
    assert result['inputs'] == {
        'run': 'fixture', 'outputs_sha256': golden['pin'],
        'report_sha256': manifest.sha256_file(golden['directory'] / REPORT),
        'persons_sha256': manifest.sha256_file(golden['directory'] / PERSONS)}
    assert set(result['years']) == {'2023', '2024'}
    for year in result['years'].values():
        assert year == {
            'bands': [{'start': 1, 'next_start': None, 'categories': 10, 'meeting': 10,
                       'share': 1.0, 'passes': True}],
            'minimum': 1, 'undefined': NO_REASONS, 'kept': GOLDEN_KEPT}


def test_golden_categories_are_sorted_and_keep_the_delivered_codes(script, capsys, golden):
    _, result = run_main(script, capsys, golden)
    codes = sorted((*SMALL_CODES, LARGE_CODE))
    assert [(c['YEAR'], c['INDNAICS'], c['headline_rows']) for c in result['categories']] == [
        (year, code, LARGE_ROWS if code == LARGE_CODE else 2)
        for year in (2023, 2024) for code in codes]
    assert {'6231', '6231  '} <= {c['INDNAICS'] for c in result['categories']}
    assert all((c['se'], c['undefined'], c['meets_se_target']) == (0.0, None, True)
               for c in result['categories'])


def test_failing_top_band_exits_one(script, capsys, tmp_path):
    people = without_second_row(golden_people(), 2024)
    status, result = run_main(script, capsys, publish(tmp_path, people))
    assert status == 1 and result['complete'] is False and result['minimum'] is None
    assert result['years']['2024']['bands'] == [
        {'start': 1, 'next_start': None, 'categories': 10, 'meeting': 8, 'share': 0.8,
         'passes': False}]
    assert result['years']['2024']['minimum'] is None
    assert result['years']['2024']['undefined'] == NO_REASONS | {'fewer_than_two_rows': 2}
    assert result['years']['2023']['bands'] == [
        {'start': 1, 'next_start': None, 'categories': 10, 'meeting': 10, 'share': 1.0,
         'passes': True}]
    assert result['years']['2023']['minimum'] == 1
    assert result['years']['2023']['undefined'] == NO_REASONS
    assert result['years']['2023']['kept'] == {
        'headline_categories': 10, 'headline_rows': GOLDEN_ROWS,
        'shared_node_categories': 0} | NO_MINIMUM_KEPT
    assert result['years']['2024']['kept'] == {
        'headline_categories': 10, 'headline_rows': GOLDEN_ROWS - 2,
        'shared_node_categories': 0} | NO_MINIMUM_KEPT
    assert len(result['categories']) == 20


@pytest.mark.parametrize('failing_year', [2023, 2024])
def test_one_failing_year_leaves_no_minimum(script, capsys, tmp_path, failing_year):
    people = without_second_row(golden_people(), failing_year)
    status, result = run_main(script, capsys, publish(tmp_path, people))
    other = ({2023, 2024} - {failing_year}).pop()
    assert (status, result['complete'], result['minimum']) == (1, False, None)
    assert result['years'][str(other)]['minimum'] == 1
    assert result['years'][str(failing_year)]['minimum'] is None


def test_a_year_without_headline_rows_exits_one(script, capsys, tmp_path):
    people = [row for row in golden_people() if row['YEAR'] == 2023]
    people.append(person('1111', 2024, 10.0, headline=False))
    status, result = run_main(script, capsys, publish(tmp_path, people))
    assert status == 1 and result['complete'] is False and result['minimum'] is None
    empty = result['years']['2024']
    assert empty['bands'] == [{'start': 1, 'next_start': None, 'categories': 0, 'meeting': 0,
                               'share': None, 'passes': False}]
    assert empty['minimum'] is None and empty['undefined'] == NO_REASONS
    assert empty['kept'] == {'headline_categories': 0, 'headline_rows': 0,
                             'shared_node_categories': 1} | NO_MINIMUM_KEPT
    assert result['years']['2023']['minimum'] == 1
    assert {c['YEAR'] for c in result['categories']} == {2023}


@pytest.mark.parametrize('hard_year', [2023, 2024])
def test_the_minimum_is_the_larger_year_minimum(script, capsys, tmp_path, hard_year):
    status, result = run_main(script, capsys, publish(tmp_path, banded_people(hard_year)))
    easy_year = ({2023, 2024} - {hard_year}).pop()
    assert status == 0 and result['complete'] is True and result['minimum'] == 50
    hard, easy = result['years'][str(hard_year)], result['years'][str(easy_year)]
    assert (hard['minimum'], easy['minimum']) == (50, 1)
    assert hard['bands'] == [
        {'start': 1, 'next_start': 50, 'categories': 10, 'meeting': 0, 'share': 0.0,
         'passes': False},
        {'start': 50, 'next_start': 100, 'categories': 10, 'meeting': 10, 'share': 1.0,
         'passes': True},
        {'start': 100, 'next_start': None, 'categories': 1, 'meeting': 1, 'share': 1.0,
         'passes': True}]
    assert easy['bands'] == [
        {'start': 1, 'next_start': 50, 'categories': 10, 'meeting': 10, 'share': 1.0,
         'passes': True},
        {'start': 50, 'next_start': 100, 'categories': 10, 'meeting': 9, 'share': 0.9,
         'passes': True},
        {'start': 100, 'next_start': None, 'categories': 1, 'meeting': 1, 'share': 1.0,
         'passes': True}]
    missed = [{'INDNAICS': f'1{number:03d}', 'headline_rows': 2} for number in range(10)]
    common = {'headline_categories': 21, 'headline_rows': 20 + 600 + LARGE_ROWS,
              'shared_node_categories': 0, 'kept_categories': 11,
              'kept_category_share': 11 / 21, 'kept_headline_rows': 600 + LARGE_ROWS,
              'kept_headline_row_share': (600 + LARGE_ROWS) / (20 + 600 + LARGE_ROWS),
              'missed': missed}
    assert hard['kept'] == common | {'count_meets_se_misses': 0, 'count_misses_se_meets': 0}
    assert easy['kept'] == common | {'count_meets_se_misses': 1, 'count_misses_se_meets': 10}


def test_undefined_ses_are_counted_for_each_year_and_reason(script, capsys, tmp_path):
    def zero_denominator(code, year, wages=(10.0, 11.0)):
        return [person(code, year, wage, REPWTP7=0) for wage in wages]

    people = (
        [person('1111', 2023, 10.0), person('1112', 2023, 10.0)]
        + [person('2222', 2023, 10.0), person('2222', 2023, 10.0)]
        + zero_denominator('2223', 2023, (10.0, 10.0))
        + category('3333', 2023, 2)
        + [person('1111', 2024, 10.0)] + zero_denominator('4444', 2024)
        + zero_denominator('4445', 2024) + category('3333', 2024, 2, swinging=True))
    status, result = run_main(script, capsys, publish(tmp_path, people))
    assert status == 1
    assert result['years']['2023']['undefined'] == {
        'fewer_than_two_rows': 2, 'constant_wage': 2, 'replicate_denominator_not_positive': 0}
    assert result['years']['2024']['undefined'] == {
        'fewer_than_two_rows': 1, 'constant_wage': 0, 'replicate_denominator_not_positive': 2}
    by_key = {(c['YEAR'], c['INDNAICS']): c for c in result['categories']}
    assert by_key[2023, '2223'] == {
        'INDNAICS': '2223', 'YEAR': 2023, 'headline_rows': 2, 'se': None,
        'undefined': 'constant_wage', 'meets_se_target': False}
    assert by_key[2024, '4444']['undefined'] == 'replicate_denominator_not_positive'
    assert by_key[2024, '3333']['se'] == pytest.approx(1 / 3)
    assert by_key[2024, '3333']['undefined'] is None


def test_shared_node_categories_are_counted_for_each_year(script, capsys, tmp_path):
    people = golden_people() + [person('0000', 2023, 10.0, headline=False),
                                person('0001', 2023, 10.0, headline=False),
                                person('0000', 2024, 10.0, headline=False)]
    status, result = run_main(script, capsys, publish(tmp_path, people))
    assert status == 0
    assert result['years']['2023']['kept'] == GOLDEN_KEPT | {'shared_node_categories': 2}
    assert result['years']['2024']['kept'] == GOLDEN_KEPT | {'shared_node_categories': 1}


def test_refusal_exits_two(script, capsys, golden):
    status, result = run_main(script, capsys, golden, pin='0' * 64)
    assert status == 2 and result == {'complete': False, 'reason': 'outputs pin differs'}


def refuse_unsafe_run(bundle):
    return {'run': '../fixture'}


def refuse_malformed_report(bundle):
    return {'pin': forge_report(bundle, drop_categories)}


def refuse_retyped_column(bundle):
    return {'pin': forge_persons(bundle, retype('REPWTP5', pl.Float64))}


def refuse_changed_recount(bundle):
    return {'pin': forge_report(bundle, one_more)}


def refuse_bad_row(bundle):
    return {'pin': forge_persons(bundle, set_value('PERWT', 0.0))}


REFUSALS = {
    'unsafe_run': (refuse_unsafe_run, UNSAFE),
    'malformed_report': (refuse_malformed_report, MALFORMED),
    'retyped_column': (refuse_retyped_column, COLUMNS_DIFFER),
    'changed_recount': (refuse_changed_recount, RECOUNT_DIFFERS),
    'bad_row': (refuse_bad_row, BAD_ROW),
}


@pytest.mark.parametrize('refuse, reason', REFUSALS.values(), ids=REFUSALS.keys())
def test_refusals_at_each_check_print_the_fixed_reason(script, capsys, golden, refuse, reason):
    change = refuse(golden)
    arguments = command_line(golden, pin=change.get('pin'), run=change.get('run'))
    assert script.main(arguments) == 2
    assert capsys.readouterr().out == json.dumps(
        {'complete': False, 'reason': reason}, sort_keys=True) + '\n'


def test_the_checks_run_in_the_order_of_the_command_line(script, capsys, golden):
    forge_report(golden, drop_categories)
    pin = forge_persons(golden, retype('REPWTP5', pl.Float64))
    status, result = run_main(script, capsys, golden, pin)
    assert (status, result) == (2, {'complete': False, 'reason': MALFORMED})


@pytest.mark.parametrize('refuse, reason', [(refuse_changed_recount, RECOUNT_DIFFERS),
                                            (refuse_bad_row, BAD_ROW)],
                         ids=['changed_recount', 'bad_row'])
def test_every_check_runs_before_any_se(script, golden, monkeypatch, refuse, reason):
    computed = []
    monkeypatch.setattr(script, 'category_se', lambda rows: computed.append(rows) or (0.0, None))
    pin = refuse(golden)['pin']
    with pytest.raises(script.Refused) as refusal:
        script.measure(golden['data_dir'], golden['run'], pin)
    assert str(refusal.value) == reason and computed == []


def forge_null_replicate(bundle):
    return forge_persons(bundle, set_value('REPWTP7', None))


def forge_infinite_weight(bundle):
    return forge_persons(bundle, set_value('PERWT', math.inf))


def forge_unreadable_table(bundle):
    '''Replace the person table with bytes that are not Parquet, and record them in the inventory.

    `rehash` cannot do it: the inventory reads the table's schema.
    '''
    file = bundle['directory'] / PERSONS
    file.write_bytes(b'not a parquet file')
    return edit_outputs(bundle, lambda inventory: inventory[PERSONS].update(
        sha256=manifest.sha256_file(file), size=file.stat().st_size))


FAILURES = {'null_replicate_weight': forge_null_replicate,
            'infinite_weight': forge_infinite_weight,
            'persons_not_parquet': forge_unreadable_table}


@pytest.mark.parametrize('forge', FAILURES.values(), ids=FAILURES.keys())
def test_any_other_failure_prints_the_fixed_line_and_exits_two(script, capsys, golden, forge):
    status = script.main(command_line(golden, pin=forge(golden)))
    captured = capsys.readouterr()
    assert status == 2
    assert captured.out == '{"complete": false, "reason": "measurement failed"}\n'
    assert captured.err == ''


@pytest.mark.parametrize('missing', ['--data-dir', '--run', '--outputs-sha256'])
def test_every_option_is_required(script, capsys, golden, missing):
    arguments = command_line(golden)
    position = arguments.index(missing)
    del arguments[position:position + 2]
    with pytest.raises(SystemExit) as stop:
        script.main(arguments)
    assert stop.value.code == 2 and capsys.readouterr().out == ''


def test_shuffled_rows_give_identical_output(script, capsys, tmp_path):
    bundle = publish(tmp_path, noisy_people())
    status, before = run_main(script, capsys, bundle)
    large = [c for c in before['categories'] if c['INDNAICS'] == LARGE_CODE]
    assert len(large) == 2 and all(0 < c['se'] < 0.05 for c in large)
    pin = forge_persons(bundle, lambda frame: frame.sample(fraction=1.0, shuffle=True, seed=7))
    status_after, after = run_main(script, capsys, bundle, pin)
    assert before['inputs']['persons_sha256'] != after['inputs']['persons_sha256']
    assert before['inputs']['report_sha256'] == after['inputs']['report_sha256']
    assert status_after == status == 0

    def body(result):
        return json.dumps({k: v for k, v in result.items() if k != 'inputs'}, sort_keys=True)
    assert body(after) == body(before)


def test_two_runs_are_byte_identical(script, capsys, tmp_path):
    bundle = publish(tmp_path, noisy_people())
    statuses, lines = [], []
    for _ in range(2):
        statuses.append(script.main(command_line(bundle)))
        lines.append(capsys.readouterr().out)
    assert statuses == [0, 0] and lines[0] == lines[1] and lines[0].count('\n') == 1


def test_output_does_not_depend_on_thread_count_or_hash_seed(tmp_path):
    arguments = command_line(publish(tmp_path, crowded_people()))
    runs = [run_command(arguments, threads=threads, hash_seed=seed)
            for threads, seed in ((1, 0), (2, 1), (8, 2))]
    assert [run.returncode for run in runs] == [0, 0, 0]
    assert [run.stderr for run in runs] == ['', '', '']
    assert runs[0].stdout == runs[1].stdout == runs[2].stdout
    categories = json.loads(runs[0].stdout)['categories']
    assert len(categories) == 140 and any(c['se'] > 0 for c in categories)


def test_the_program_exits_with_the_status_of_the_run(tmp_path):
    incomplete = publish(tmp_path / 'incomplete', without_second_row(golden_people(), 2024))
    run = run_command(command_line(incomplete))
    assert run.returncode == 1 and run.stderr == ''
    assert json.loads(run.stdout)['complete'] is False
    refused = run_command(command_line(incomplete, pin='0' * 64))
    assert refused.returncode == 2 and refused.stderr == ''
    assert json.loads(refused.stdout) == {'complete': False, 'reason': PIN_DIFFERS}


def walk(value):
    '''Every key and every float in a parsed JSON value, nested ones included.'''
    if isinstance(value, dict):
        for key, inner in value.items():
            yield 'key', key
            yield from walk(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from walk(inner)
    elif type(value) is float:
        yield 'float', value


def test_output_holds_no_means_or_person_values(script, capsys, tmp_path):
    people = golden_people()
    for row in people:
        if row['INDNAICS'] == '1111':
            row['log_wage_2010'] = 10.25 if row['log_wage_2010'] == 10.0 else 11.75
    status, result = run_main(script, capsys, publish(tmp_path, people))
    assert status == 0
    assert all(set(entry) == RECORD_KEYS for entry in result['categories'])
    keys = {value for kind, value in walk(result) if kind == 'key'}
    floats = {value for kind, value in walk(result) if kind == 'float'}
    # `constant_wage` is the name of an undefined-SE reason, fixed by the plan, not a wage value.
    assert not [key for key in keys - set(NO_REASONS) if any(
        word in key.lower() for word in ('mean', 'theta', 'wage'))]
    assert set(NO_REASONS) <= keys
    assert floats and not floats & {10.25, 11.75, 11.0}


def test_writes_nothing_under_data_dir(script, capsys, golden):
    before = tree(golden['data_dir'])
    assert len(before) == 4
    status, _ = run_main(script, capsys, golden)
    assert status == 0 and tree(golden['data_dir']) == before


def test_script_imports_are_offline():
    imported = set()
    for node in ast.walk(ast.parse(SCRIPT.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Import):
            imported |= {alias.name.partition('.')[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            imported.add(node.module.partition('.')[0])
    assert imported - set(sys.stdlib_module_names) == {'polars'}
    assert not imported & {'embedding_data', 'httpx', 'dotenv', 'ipumspy', 'requests', 'urllib',
                           'socket', 'subprocess', 'typer'}


def integer_replicate_delivery(original):
    '''The wage delivery with an integer `REPWTP37`, as IPUMS delivers every replicate weight.

    The Stage 9 target fixture delivers `REPWTP37` as the text -2.5, and the unchanged upstream
    conversion types that column Float64. The script's contract is Int64 for all 80 (spec
    "Inputs"), so the chain would be refused for a fixture choice, not for the script.
    '''
    def prepare(profile, ddi, frame):
        ddi, frame = original(profile, ddi, frame)
        return ddi, frame.with_columns(pl.lit(127, dtype=pl.Int64).alias('REPWTP37'))
    return prepare


@pytest.fixture(scope='module')
def template(tmp_path_factory):
    '''One genuine Stage 17 bundle named `first`, built through the fixture chain.'''
    with pytest.MonkeyPatch.context() as patches:
        forbid_external_access(patches)
        patches.setattr(acs_wage_fixtures, 'prepare_wage_delivery',
                        integer_replicate_delivery(acs_wage_fixtures.prepare_wage_delivery))
        chain = wage_mapping(tmp_path_factory.mktemp('minimum-earners-chain'), patches)
        built = acs_wage_bundle.build(
            chain['data_dir'], 'first', mapping_run=chain['mapping_run'],
            mapping_outputs_sha256=chain['mapping_outputs_sha256'], codes_run=chain['codes_run'],
            codes_outputs_sha256=chain['codes_outputs_sha256'])
    return chain | {'first_pin': built['outputs_sha256']}


def test_genuine_chain_bundle_passes_the_checks(script, capsys, template):
    bundle = {'data_dir': template['data_dir'], 'run': 'first', 'pin': template['first_pin']}
    status, result = run_main(script, capsys, bundle)
    inventory = json.loads(
        (template['data_dir'] / 'derived/acs/wage-microdata/first' / OUTPUTS).read_text())
    assert status in (0, 1), result
    assert result['inputs']['report_sha256'] == inventory[REPORT]['sha256']
    assert result['inputs']['persons_sha256'] == inventory[PERSONS]['sha256']
    assert result['inputs']['outputs_sha256'] == template['first_pin']
