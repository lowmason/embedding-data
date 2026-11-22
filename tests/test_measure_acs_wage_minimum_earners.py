'''The Stage 19 minimum-earners measurement script: the SE and band rule on small typed rows, and
the authentication of the pinned Stage 17 bundle on small hand-made bundles.'''

import dataclasses
import importlib.util
import json
import math
import random
import shutil
from fractions import Fraction
from pathlib import Path

import polars as pl
import pytest
from acs_wage_fixtures import core_row

from embedding_data import manifest, target_io
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
