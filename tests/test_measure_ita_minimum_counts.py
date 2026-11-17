'''The V9 minimum-count script, on small synthetic cells frames and fixture bundles.'''

import hashlib
import importlib.util
import json
from pathlib import Path

import polars as pl
import pytest
from minimum_count_fixtures import build_frames, golden_rows, publish, republish

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


@pytest.fixture
def published(tmp_path):
    return publish(tmp_path, build_frames(golden_rows()))


def selections(published, **changes):
    '''The `authenticate` arguments of the published bundles, with role tuples replaced.'''
    selected = {
        'establishment': (published.establishment.name, published.establishment_pin),
        'area_mix': (published.area_mix.name, published.area_mix_pin),
        'codes': (published.codes.name, published.codes_pin),
    }
    return {'data_dir': published.data_dir, **selected, **changes}


def refusal(script, arguments):
    with pytest.raises(script.Refused) as raised:
        script.authenticate(**arguments)
    return str(raised.value)


def edit_inputs(directory, change):
    file = directory / 'inputs.json'
    inputs = json.loads(file.read_text())
    change(inputs)
    file.write_text(json.dumps(inputs))
    return republish(directory)


def test_fixture_builds_frozen_tables():
    frames = build_frames(golden_rows())
    assert frames.support.height == 2
    assert frames.support.select('j_2023', 'j_2024', 'j_2025').to_dicts() == [
        {'j_2023': 1, 'j_2024': 1, 'j_2025': 1}] * 2
    confirmed = frames.links.filter(pl.col('status') == 'confirmed_same_id')
    assert {(2023, 2024), (2024, 2025)} <= set(
        confirmed.select('base_year', 'later_year').iter_rows())


def test_authenticate_returns_pinned_files(script, published):
    inputs = script.authenticate(**selections(published))
    assert inputs.canonical == published.codes / 'ita_300a_canonical.parquet'
    assert inputs.assignments == published.area_mix / 'ita_county_assignments.parquet'


def test_authenticate_names_every_file(script, published):
    inputs = script.authenticate(**selections(published))
    establishment, area_mix = published.establishment, published.area_mix
    assert inputs == script.Inputs(
        canonical=published.codes / 'ita_300a_canonical.parquet',
        links=establishment / 'ita_establishment_links.parquet',
        pairs=establishment / 'ita_text_pairs.parquet',
        members=establishment / 'ita_text_pair_members.parquet',
        co_ownership=establishment / 'ita_co_ownership.parquet',
        support=establishment / 'co_ownership_support.parquet',
        establishment_report=establishment / 'report.json',
        assignments=area_mix / 'ita_county_assignments.parquet',
        area_mix=area_mix / 'ita_area_mix.parquet',
        area_mix_report=area_mix / 'report.json',
    )


@pytest.mark.parametrize('role, reason', [
    ('establishment', 'establishment-target pin differs'),
    ('area_mix', 'area-mix pin differs'),
    ('codes', 'codes pin differs'),
])
def test_wrong_pin_refused(script, published, role, reason):
    run_id = selections(published)[role][0]
    assert refusal(script, selections(published, **{role: (run_id, '0' * 64)})) == reason


def test_changed_file_refused(script, published):
    file = published.establishment / 'ita_co_ownership.parquet'
    pl.read_parquet(file).slice(1).write_parquet(file)
    assert refusal(script, selections(published)) == 'file differs from its inventory'


@pytest.mark.parametrize('bundle, name', [
    ('codes', 'ita_300a_canonical.parquet'),
    ('establishment', 'ita_establishment_links.parquet'),
    ('establishment', 'ita_text_pairs.parquet'),
    ('establishment', 'ita_text_pair_members.parquet'),
    ('establishment', 'ita_co_ownership.parquet'),
    ('establishment', 'co_ownership_support.parquet'),
    ('establishment', 'inputs.json'),
    ('establishment', 'report.json'),
    ('area_mix', 'ita_county_assignments.parquet'),
    ('area_mix', 'ita_area_mix.parquet'),
    ('area_mix', 'inputs.json'),
    ('area_mix', 'report.json'),
])
def test_every_read_file_is_checked(script, published, bundle, name):
    file = getattr(published, bundle) / name
    file.write_bytes(file.read_bytes() + b' ')
    assert refusal(script, selections(published)) == 'file differs from its inventory'


def test_file_missing_from_inventory_refused(script, published):
    outputs = published.area_mix / 'outputs.json'
    inventory = json.loads(outputs.read_text())
    del inventory['ita_area_mix.parquet']
    outputs.write_text(json.dumps(inventory))
    pin = hashlib.sha256(outputs.read_bytes()).hexdigest()
    arguments = selections(published, area_mix=(published.area_mix.name, pin))
    assert refusal(script, arguments) == 'file differs from its inventory'


def test_pins_are_checked_before_files(script, published):
    file = published.area_mix / 'ita_area_mix.parquet'
    pl.read_parquet(file).slice(1).write_parquet(file)
    arguments = selections(published, codes=(published.codes.name, '0' * 64))
    assert refusal(script, arguments) == 'codes pin differs'


def test_pins_are_checked_in_table_order(script, published):
    arguments = selections(published, establishment=(published.establishment.name, '0' * 64),
                           codes=(published.codes.name, '0' * 64))
    assert refusal(script, arguments) == 'establishment-target pin differs'
    arguments = selections(published, area_mix=(published.area_mix.name, '0' * 64),
                           codes=(published.codes.name, '0' * 64))
    assert refusal(script, arguments) == 'area-mix pin differs'


def test_establishment_inputs_naming_other_canonical_refused(script, published):
    pin = edit_inputs(published.establishment,
                      lambda inputs: inputs['canonical'].update(sha256='1' * 64))
    arguments = selections(published, establishment=(published.establishment.name, pin))
    assert refusal(script, arguments) == 'inputs name another canonical table or codes run'


def test_area_mix_inputs_naming_other_canonical_refused(script, published):
    pin = edit_inputs(published.area_mix,
                      lambda inputs: inputs['canonical'].update(sha256='1' * 64))
    arguments = selections(published, area_mix=(published.area_mix.name, pin))
    assert refusal(script, arguments) == 'inputs name another canonical table or codes run'


OTHER_PATH = 'derived/codes/other_codes/ita_300a_canonical.parquet'


@pytest.mark.parametrize('role, change', [
    ('establishment', lambda inputs: inputs['canonical'].update(path=OTHER_PATH)),
    ('area_mix', lambda inputs: inputs['canonical'].update(path=OTHER_PATH)),
    ('establishment', lambda inputs: inputs['codes'].update(run_id='other_codes')),
    ('establishment', lambda inputs: inputs['codes'].update(outputs_sha256='1' * 64)),
    ('establishment', lambda inputs: inputs.pop('codes')),
    ('area_mix', lambda inputs: inputs.pop('canonical')),
    ('establishment', lambda inputs: inputs.update(canonical='derived/codes')),
])
def test_cross_bundle_identity_refused(script, published, role, change):
    directory = getattr(published, role)
    pin = edit_inputs(directory, change)
    arguments = selections(published, **{role: (directory.name, pin)})
    assert refusal(script, arguments) == 'inputs name another canonical table or codes run'


def test_unsafe_run_id_refused(script, published):
    arguments = selections(published, codes=('../fixture_codes', published.codes_pin))
    assert refusal(script, arguments) == 'unsafe run id or pin'


@pytest.mark.parametrize('role', ['establishment', 'area_mix', 'codes'])
@pytest.mark.parametrize('form', ['trailing slash', 'trailing newline', 'leading dash',
                                  'upper pin', 'pin newline', 'short pin'])
def test_unsafe_forms_refused(script, published, role, form):
    run_id, pin = selections(published)[role]
    run_id, pin = {
        'trailing slash': (run_id + '/', pin),
        'trailing newline': (run_id + '\n', pin),
        'leading dash': ('-' + run_id, pin),
        'upper pin': (run_id, pin.upper()),
        'pin newline': (run_id, pin + '\n'),
        'short pin': (run_id, pin[:-1]),
    }[form]
    arguments = selections(published, **{role: (run_id, pin)})
    assert refusal(script, arguments) == 'unsafe run id or pin'
