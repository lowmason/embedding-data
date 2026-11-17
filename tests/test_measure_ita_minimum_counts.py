'''The V9 minimum-count script, on small synthetic cells frames and fixture bundles.'''

import hashlib
import importlib.util
import json
from pathlib import Path

import polars as pl
import pytest
from ita_establishment_fixtures import canonical_frame, crosswalked
from minimum_count_fixtures import build_frames, golden_rows, publish, republish, row

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


def derive(script, rows):
    '''The frames, record frame and confirmed links of canonical override rows.'''
    frames = build_frames(rows)
    records = script.record_frame(frames.canonical.lazy())
    return frames, records, script.confirmed_links(frames.links.lazy(), records)


def rows_of(records, year, establishment, canonical):
    '''The source rows of one establishment's records in one year.'''
    wanted = canonical.with_row_index('source_row').filter(
        (pl.col('year_filing_for') == year)
        & (pl.col('establishment_name') == f'Plant {establishment}'))
    return sorted(wanted['source_row'].cast(pl.UInt64).to_list())


def linked(links, year):
    return set(links.filter(pl.col('base_year') == year)['source_row'].to_list())


def test_record_frame_keeps_2023_to_2025(script):
    golden = golden_rows()
    frames = build_frames(
        [*golden, row(2022, 1, '238220', 'Plumbing contractor',
                      mapping=crosswalked('238220', 2017, ['238220']))])
    records = script.record_frame(frames.canonical.lazy())
    assert records.height == 6
    assert records['industry_eligible'].all()
    assert records['employer_eligible'].all()


def test_record_frame_columns(script):
    frames = build_frames(golden_rows())
    records = script.record_frame(frames.canonical.lazy())
    assert records.columns == ['source_row', 'year_filing_for', 'naics_code',
                               'naics_2022_node_id', 'ein_key', 'industry_eligible',
                               'employer_eligible']
    assert records.schema['source_row'] == pl.UInt64
    assert records['source_row'].to_list() == list(range(6))
    assert sorted(set(records['year_filing_for'].to_list())) == [2023, 2024, 2025]
    assert records['ein_key'].to_list() == ['123456789'] * 6
    assert records['naics_code'].to_list() == ['238220', '722511'] * 3


def test_record_frame_drops_the_years_outside_the_window(script):
    frames = build_frames([
        row(2022, 1, '238220', 'Plumbing contractor',
            mapping=crosswalked('238220', 2017, ['238220'])),
        *golden_rows(),
        row(2026, 1, '238220', 'Plumbing contractor',
            mapping=crosswalked('238220', 2017, ['238220'])),
    ])
    records = script.record_frame(frames.canonical.lazy())
    assert records['source_row'].to_list() == list(range(1, 7))


def test_employer_eligibility_follows_the_co_ownership_classification(script):
    frames = build_frames([
        row(2023, 1, '238220', 'Plumbing contractor'),
        row(2023, 2, '238220', 'Plumbing contractor',
            mapping=crosswalked('238220', 2017, ['238220'])),
        row(2023, 3, '238220', 'Plumbing contractor', ein=''),
        row(2023, 4, '238220', 'Plumbing contractor', ein='23456789'),
    ])
    records = script.record_frame(frames.canonical.lazy())
    assert records['industry_eligible'].to_list() == [True, False, True, True]
    assert records['employer_eligible'].to_list() == [True, False, False, False]
    assert records['ein_key'].to_list() == ['123456789', '123456789', None, '023456789']


@pytest.mark.parametrize('change', [
    {'flag_naics_crosswalked': True},
    {'flag_naics_ambiguous': True},
    {'flag_naics_unresolved': True},
    {'naics_2022_node_id': None},
    {'flag_naics_unresolved': None},
], ids=['crosswalked flag', 'ambiguous flag', 'unresolved flag', 'no node', 'null flag'])
def test_industry_eligibility_is_the_frozen_rule(script, change):
    canonical = canonical_frame([
        row(2023, 1, '238220', 'Plumbing contractor'),
        row(2023, 2, '238220', 'Plumbing contractor', **change),
    ])
    records = script.record_frame(canonical)
    assert records['industry_eligible'].to_list() == [True, False]
    assert records['employer_eligible'].to_list() == [True, False]


def test_two_year_link_is_not_visible(script):
    rows = [r for r in golden_rows()
            if not (r['year_filing_for'] == 2024 and r['establishment_name'] == 'Plant 1')]
    frames, _records, links = derive(script, rows)
    base = rows_of(_records, 2023, 1, frames.canonical)
    guard = frames.links.filter(
        (pl.col('base_year') == 2023) & (pl.col('later_year') == 2025)
        & (pl.col('status') == 'confirmed_same_id'))
    assert any(base[0] in rows for rows in guard['base_rows'].to_list())
    assert base[0] not in linked(links, 2023)


def test_duplicate_rows_link_through_base_rows(script):
    rows = [
        row(2023, 1, '238220', 'Plumbing contractor', id=7),
        row(2023, 1, '238220', 'Plumbing contractor', id=7),
        row(2024, 1, '238220', 'Plumbing contractor'),
    ]
    _frames, _records, links = derive(script, rows)
    found = links.filter(pl.col('base_year') == 2023)
    assert sorted(found['source_row'].to_list()) == [0, 1]
    assert found['later_row'].to_list() == [2, 2]


def test_unconfirmed_links_are_not_visible(script):
    rows = golden_rows()
    rows[2] = {**rows[2], 'street_address': '1 Other St'}
    frames, records, links = derive(script, rows)
    status = frames.links.filter(
        (pl.col('base_year') == 2023) & (pl.col('later_year') == 2024)
        & (pl.col('base_row') == 0))['status'].to_list()
    assert status == ['weaker_same_id']
    assert 0 not in linked(links, 2023)
    assert 1 in linked(links, 2023)


def test_changed_id_link_is_visible(script):
    rows = golden_rows()
    rows[2] = {**rows[2], 'establishment_id': 999}
    frames, _records, links = derive(script, rows)
    status = frames.links.filter(
        (pl.col('base_year') == 2023) & (pl.col('later_year') == 2024)
        & (pl.col('base_row') == 0))['status'].to_list()
    assert status == ['confirmed_changed_id']
    assert links.filter(pl.col('base_year') == 2023).sort('source_row').rows() == [
        (2023, 0, 2), (2023, 1, 3)]


def test_confirmed_links_cover_both_year_pairs(script):
    _frames, _records, links = derive(script, golden_rows())
    assert links.columns == ['base_year', 'source_row', 'later_row']
    assert links.sort('base_year', 'source_row').rows() == [
        (2023, 0, 2), (2023, 1, 3), (2024, 2, 4), (2024, 3, 5)]


def test_ineligible_successor_is_not_visible(script):
    rows = golden_rows()
    rows[2] = row(2024, 1, '238220', 'Plumbing contractor',
                  mapping=crosswalked('238220', 2017, ['238220']))
    _frames, records, links = derive(script, rows)
    found = script.visible(links, records.filter('industry_eligible')['source_row'])
    assert 0 not in linked(found, 2023)
    assert 1 in linked(found, 2023)


def test_visible_keeps_base_year_and_source_row(script):
    _frames, records, links = derive(script, golden_rows())
    found = script.visible(links, records.filter('industry_eligible')['source_row'])
    assert found.columns == ['base_year', 'source_row']
    assert found.sort('base_year', 'source_row').rows() == [
        (2023, 0), (2023, 1), (2024, 2), (2024, 3)]


def refused_links(script, change):
    frames = build_frames(golden_rows())
    records = script.record_frame(frames.canonical.lazy())
    links = change(frames.links)
    with pytest.raises(script.Refused) as raised:
        script.confirmed_links(links.lazy(), records)
    return str(raised.value)


def point(column, value):
    '''Set one column of the 2023 -> 2024 link of source row 0.'''
    target = ((pl.col('base_year') == 2023) & (pl.col('later_year') == 2024)
              & (pl.col('base_row') == 0))
    return lambda links: links.with_columns(
        pl.when(target).then(value).otherwise(pl.col(column)).alias(column))


def test_link_year_disagreement_refused(script):
    reason = refused_links(script, point('later_row', pl.lit(1, pl.UInt64)))
    assert reason == 'link rows disagree with canonical rows'


@pytest.mark.parametrize('change', [
    point('later_row', pl.lit(4, pl.UInt64)),
    point('later_row', pl.lit(99, pl.UInt64)),
    point('base_rows', pl.lit([2], pl.List(pl.UInt64))),
    point('base_rows', pl.lit([99], pl.List(pl.UInt64))),
    point('base_rows', pl.lit([0, 1], pl.List(pl.UInt64))),
    lambda links: pl.concat([links, links.filter(
        (pl.col('base_year') == 2023) & (pl.col('later_year') == 2024)
        & (pl.col('base_row') == 0))]),
], ids=['later two years on', 'later absent', 'source in later year', 'source absent',
        'source twice', 'link twice'])
def test_link_row_disagreements_refused(script, change):
    assert refused_links(script, change) == 'link rows disagree with canonical rows'
