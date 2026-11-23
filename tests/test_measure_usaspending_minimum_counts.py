'''The Stage 21 minimum-count script, on small synthetic cells frames and pair tables.

Every pair table is a typed frame in `PAIR_SCHEMA` with made-up UEIs that passes
`validate_pairs`, as in `tests/test_vendor_link_targets.py`.
'''

import dataclasses
import importlib.util
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from embedding_data.manifest import sha256_file
from embedding_data.target_io import inventory, write_json
from embedding_data.vendor_link_bundle import FILES, TABLES
from embedding_data.vendor_link_codes import NODE_PREFIX
from embedding_data.vendor_link_pairs import FIRM_STATUSES, PAIR_SCHEMA, validate_pairs
from embedding_data.vendor_link_targets import INTRA_LABEL, estimate

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


# ---- per-year counts, testable cells and recurrence (Task 2)

def node(code: str) -> str:
    return NODE_PREFIX + code


def uei(name: str) -> str:
    '''A made-up 12-character UEI. Left padding keeps `U1` and `U10` apart.'''
    return name.rjust(12, 'Z')


def link(prime, sub, *, intra=False, fy=(1, 0, 0), amount='0.00'):
    '''One pair of the named firms: its usable reports by fiscal year (2024, 2025, 2026), its
    intra-group flag and its amount sum.'''
    return {'prime': prime, 'sub': sub, 'intra': intra, 'fy': fy, 'amount': amount}


def _firm(value):
    '''A six-digit code gives an eligible firm and its node. A firm status gives that status
    and no node.'''
    if value in FIRM_STATUSES:
        assert value != 'eligible'
        return value, None
    return 'eligible', node(value)


def _status(prime, sub, intra, prime_status, sub_status):
    if prime == sub:
        return 'self_link'
    if intra:
        return 'intra_group'
    if prime_status != 'eligible':
        return 'prime_ineligible'
    if sub_status != 'eligible':
        return 'sub_ineligible'
    return 'eligible'


def pair_frame(firms, *links):
    '''The pair table of `links`, sorted and checked by `validate_pairs`. `firms` maps each
    firm name to its NAICS code or to an ineligible firm status.'''
    rows = []
    for item in links:
        prime_status, prime_node = _firm(firms[item['prime']])
        sub_status, sub_node = _firm(firms[item['sub']])
        fy2024, fy2025, fy2026 = item['fy']
        rows.append({
            'prime_uei': uei(item['prime']), 'sub_uei': uei(item['sub']),
            'n_reports': fy2024 + fy2025 + fy2026,
            'n_fy2024': fy2024, 'n_fy2025': fy2025, 'n_fy2026': fy2026,
            'prime_status': prime_status, 'sub_status': sub_status,
            'prime_node_id': prime_node, 'sub_node_id': sub_node,
            'flag_intra_group': item['intra'],
            'pair_status': _status(item['prime'], item['sub'], item['intra'], prime_status,
                                   sub_status),
            'amount_sum': Decimal(item['amount'])})
    table = pl.DataFrame(rows, schema=PAIR_SCHEMA).sort('prime_uei', 'sub_uei')
    validate_pairs(table, int(table['n_reports'].sum()))
    return table


S, D, E = '541512', '541511', '236220'
FIRMS = {'P1': D, 'P2': D, 'P3': E, 'U1': S, 'U2': S, 'U3': E, 'X': 'not_in_sam'}
# A cell is (unit_a, unit_b): the subcontractor's node, then the prime's. In node order
# E < D < S, so the cells sort as EE, ED, SE, SD.
SD, SE, ED, EE = ((node(sub), node(prime)) for sub, prime in ((S, D), (S, E), (E, D), (E, E)))
ELIGIBLE_SCHEMA = {'prime_uei': pl.String, 'sub_uei': pl.String, 'unit_a': pl.String,
                   'unit_b': pl.String, 'n_fy2024': pl.UInt64, 'n_fy2025': pl.UInt64,
                   'n_fy2026': pl.UInt64}
YEAR_SCHEMA = {'unit_a': pl.String, 'unit_b': pl.String, 'year': pl.Int64, 's': pl.UInt64,
               'b': pl.UInt64, 'l': pl.UInt64}
POOLED_SCHEMA = {'unit_a': pl.String, 'unit_b': pl.String, 's_suppliers': pl.UInt64,
                 'b_buyers': pl.UInt64, 'l_pairs': pl.UInt64}
CELLS_SCHEMA = {'unit_a': pl.String, 'unit_b': pl.String, 'base_count': pl.UInt64,
                'testable': pl.Boolean, 'recurs': pl.Boolean}
YEAR_LINKS = (link('P1', 'U1', fy=(1, 1, 0)), link('P1', 'U2', fy=(1, 0, 0)),
              link('P2', 'U1', fy=(0, 0, 2)))


def frame(schema, *items):
    '''A frame in `schema` from rows that each start with their (unit_a, unit_b) cell.'''
    return pl.DataFrame([(*cell, *values) for cell, *values in items], schema=schema,
                        orient='row')


def eligible(script, *links, firms=FIRMS):
    return script.eligible_pairs(pair_frame(firms, *links).lazy())


def base_cells(script, base, *links, firms=FIRMS):
    return script.cells(eligible(script, *links, firms=firms), base)


def assert_cells(found, supplier, buyer=None):
    '''Both cells frames, from (cell, base_count, testable, recurs) rows. The buyer rows
    default to the supplier rows.'''
    assert list(found) == ['supplier_share', 'buyer_share']
    assert_frame_equal(found['supplier_share'], frame(CELLS_SCHEMA, *supplier))
    assert_frame_equal(found['buyer_share'],
                       frame(CELLS_SCHEMA, *(supplier if buyer is None else buyer)))


def test_year_counts_follow_each_fiscal_year(script):
    pairs = eligible(script, *YEAR_LINKS)
    assert_frame_equal(script.year_counts(pairs), frame(
        YEAR_SCHEMA, (SD, 2024, 2, 1, 2), (SD, 2025, 1, 1, 1), (SD, 2026, 1, 1, 1)))
    assert_frame_equal(script.pooled_counts(pairs), frame(POOLED_SCHEMA, (SD, 2, 2, 3)))


def test_only_eligible_pairs_are_counted(script):
    alone = eligible(script, *YEAR_LINKS)
    wider = eligible(script, *YEAR_LINKS, link('P1', 'X', fy=(1, 1, 1)),
                     link('P2', 'U2', intra=True, fy=(1, 1, 1)))
    assert_frame_equal(script.year_counts(wider), script.year_counts(alone))
    assert_frame_equal(script.pooled_counts(wider), script.pooled_counts(alone))


def test_same_pair_recurs(script):
    found = base_cells(script, 2024, link('P1', 'U1', fy=(1, 1, 0)))
    assert_frame_equal(found['supplier_share'], frame(CELLS_SCHEMA, (SD, 1, True, True)))


def test_subcontractor_that_is_only_a_prime_next_year_is_not_testable(script):
    found = base_cells(script, 2024, link('P1', 'U1', fy=(1, 0, 0)),
                       link('U1', 'U3', fy=(0, 1, 0)), link('P1', 'U3', fy=(0, 1, 0)))
    assert_cells(found, [(SD, 1, False, False)])


def test_both_firms_active_elsewhere_is_testable_without_recurring(script):
    found = base_cells(script, 2024, link('P1', 'U1', fy=(1, 0, 0)),
                       link('P1', 'U3', fy=(0, 1, 0)), link('P3', 'U1', fy=(0, 1, 0)))
    assert_cells(found, [(SD, 1, True, False)])


def test_activity_through_an_ineligible_pair_does_not_count(script):
    found = base_cells(script, 2024, link('P1', 'U1', fy=(1, 0, 0)),
                       link('P3', 'U1', intra=True, fy=(0, 1, 0)),
                       link('P1', 'X', fy=(0, 1, 0)))
    assert_cells(found, [(SD, 1, False, False)])


def test_pair_without_a_base_year_report_is_not_in_the_base_year(script):
    found = base_cells(script, 2024, link('P1', 'U1', fy=(0, 1, 1)),
                       link('P2', 'U2', fy=(1, 0, 0)), link('P3', 'U3', fy=(0, 1, 0)))
    assert_cells(found, [(SD, 1, False, True)])


def test_each_measure_takes_its_own_base_count(script):
    found = base_cells(script, 2024, link('P1', 'U1', fy=(1, 1, 0)),
                       link('P1', 'U2', fy=(1, 1, 0)))
    assert_cells(found, [(SD, 2, True, True)], [(SD, 1, True, True)])
    assert_frame_equal(found['supplier_share'].drop('base_count'),
                       found['buyer_share'].drop('base_count'))


def test_second_year_pair_reads_fy2025_and_fy2026(script):
    pairs = eligible(script, link('P1', 'U1', fy=(0, 1, 1)))
    assert_cells(script.cells(pairs, 2024), [])
    assert_cells(script.cells(pairs, 2025), [(SD, 1, True, True)])


def test_eligible_pairs_keep_the_counted_columns(script):
    '''The subcontractor's node is `unit_a` and the prime's is `unit_b`.'''
    found = eligible(script, link('P1', 'U1', fy=(1, 2, 3)), link('P1', 'X', fy=(1, 1, 1)))
    assert_frame_equal(found.collect(), pl.DataFrame(
        [(uei('P1'), uei('U1'), node(S), node(D), 1, 2, 3)], schema=ELIGIBLE_SCHEMA,
        orient='row'))


def test_prime_ineligible_and_self_link_pairs_are_not_counted(script):
    alone = eligible(script, *YEAR_LINKS)
    wider = eligible(script, *YEAR_LINKS, link('X', 'U1', fy=(1, 1, 1)),
                     link('U1', 'U1', fy=(1, 1, 1)), link('P1', 'P1', fy=(1, 1, 1)))
    assert_frame_equal(script.year_counts(wider), script.year_counts(alone))
    assert_frame_equal(script.pooled_counts(wider), script.pooled_counts(alone))
    assert_cells(script.cells(wider, 2024), [(SD, 2, True, True)], [(SD, 1, True, True)])


def test_counts_take_distinct_firms(script):
    '''One subcontractor in two pairs of one cell and year counts once.'''
    pairs = eligible(script, link('P1', 'U1', fy=(1, 0, 0)), link('P2', 'U1', fy=(1, 0, 0)))
    assert_frame_equal(script.year_counts(pairs), frame(YEAR_SCHEMA, (SD, 2024, 1, 2, 2)))
    assert_frame_equal(script.pooled_counts(pairs), frame(POOLED_SCHEMA, (SD, 1, 2, 2)))
    assert_cells(script.cells(pairs, 2024), [(SD, 1, False, False)], [(SD, 2, False, False)])


def test_year_counts_leave_out_years_without_a_pair(script):
    '''ED lacks its first and last year, SE its first two and SD its middle year.'''
    pairs = eligible(script, link('P1', 'U1', fy=(1, 0, 1)), link('P1', 'U3', fy=(0, 1, 0)),
                     link('P3', 'U1', fy=(0, 0, 1)))
    assert_frame_equal(script.year_counts(pairs), frame(
        YEAR_SCHEMA, (ED, 2025, 1, 1, 1), (SE, 2026, 1, 1, 1), (SD, 2024, 1, 1, 1),
        (SD, 2026, 1, 1, 1)))


def test_counts_and_cells_are_sorted_by_cell(script):
    pairs = eligible(script, link('P1', 'U1', fy=(1, 1, 0)), link('P1', 'U3', fy=(1, 0, 0)),
                     link('P3', 'U1', fy=(1, 0, 0)), link('P3', 'U2', fy=(1, 0, 0)),
                     link('P3', 'U3', fy=(1, 0, 1)))
    assert_frame_equal(script.year_counts(pairs), frame(
        YEAR_SCHEMA, (EE, 2024, 1, 1, 1), (EE, 2026, 1, 1, 1), (ED, 2024, 1, 1, 1),
        (SE, 2024, 2, 1, 2), (SD, 2024, 1, 1, 1), (SD, 2025, 1, 1, 1)))
    assert_frame_equal(script.pooled_counts(pairs), frame(
        POOLED_SCHEMA, (EE, 1, 1, 1), (ED, 1, 1, 1), (SE, 2, 1, 2), (SD, 1, 1, 1)))
    assert_cells(script.cells(pairs, 2024),
                 [(EE, 1, False, False), (ED, 1, False, False), (SE, 2, False, False),
                  (SD, 1, True, True)],
                 [(EE, 1, False, False), (ED, 1, False, False), (SE, 1, False, False),
                  (SD, 1, True, True)])


def test_base_count_is_the_base_year_firm_count(script):
    '''In FY2024, S is 2 and B is 1. In FY2025 and pooled, both are 3.'''
    pairs = eligible(script, link('P1', 'U1', fy=(1, 1, 0)), link('P1', 'U2', fy=(1, 0, 0)),
                     link('P2', 'U4', fy=(0, 1, 0)), link('P4', 'U2', fy=(0, 1, 0)),
                     firms=FIRMS | {'P4': D, 'U4': S})
    assert_frame_equal(script.pooled_counts(pairs), frame(POOLED_SCHEMA, (SD, 3, 3, 4)))
    assert_cells(script.cells(pairs, 2024), [(SD, 2, True, True)], [(SD, 1, True, True)])
    assert_cells(script.cells(pairs, 2025), [(SD, 3, False, False)])


def test_prime_that_is_only_a_subcontractor_next_year_is_not_testable(script):
    found = base_cells(script, 2024, link('P1', 'U1', fy=(1, 0, 0)),
                       link('P3', 'P1', fy=(0, 1, 0)), link('P3', 'U1', fy=(0, 1, 0)))
    assert_cells(found, [(SD, 1, False, False)])


def test_active_firms_on_different_pairs_do_not_make_the_cell_testable(script):
    '''U1 is active but its prime P1 is not. P2 is active but its subcontractor U2 is not.'''
    found = base_cells(script, 2024, link('P1', 'U1', fy=(1, 0, 0)),
                       link('P2', 'U2', fy=(1, 0, 0)), link('P3', 'U1', fy=(0, 1, 0)),
                       link('P2', 'U3', fy=(0, 1, 0)))
    assert_cells(found, [(SD, 2, False, False)])


@pytest.mark.parametrize('prime, sub', [('P1', 'U1'), ('P2', 'U2')], ids=['first', 'last'])
def test_one_active_pair_makes_the_cell_testable(script, prime, sub):
    '''Of the base pairs P1–U1 (first in key order) and P2–U2 (last), only one is active.'''
    found = base_cells(script, 2024, link('P1', 'U1', fy=(1, 0, 0)),
                       link('P2', 'U2', fy=(1, 0, 0)), link(prime, 'U3', fy=(0, 1, 0)),
                       link('P3', sub, fy=(0, 1, 0)))
    assert_cells(found, [(SD, 2, True, False)])


def test_activity_and_recurrence_read_only_the_next_year(script):
    '''FY2026 reports do not reach a FY2024 base cell, nor FY2024 reports a FY2025 one.'''
    assert_cells(base_cells(script, 2024, link('P1', 'U1', fy=(1, 0, 1))),
                 [(SD, 1, False, False)])
    assert_cells(base_cells(script, 2025, link('P1', 'U1', fy=(1, 1, 0))),
                 [(SD, 1, False, False)])


@pytest.mark.parametrize('links', [
    (link('P1', 'X', fy=(0, 1, 0)), link('P3', 'U1', fy=(0, 1, 0))),
    (link('X', 'U1', fy=(0, 1, 0)), link('P1', 'U3', fy=(0, 1, 0))),
    (link('P3', 'U1', intra=True, fy=(0, 1, 0)), link('P1', 'U3', fy=(0, 1, 0))),
    (link('P1', 'U3', intra=True, fy=(0, 1, 0)), link('P3', 'U1', fy=(0, 1, 0))),
    (link('U1', 'U1', fy=(0, 1, 0)), link('P1', 'U3', fy=(0, 1, 0))),
    (link('P1', 'P1', fy=(0, 1, 0)), link('P3', 'U1', fy=(0, 1, 0))),
], ids=['sub_ineligible_prime', 'prime_ineligible_sub', 'intra_group_sub', 'intra_group_prime',
        'self_link_sub', 'self_link_prime'])
def test_each_ineligible_status_gives_no_activity(script, links):
    '''One firm of P1–U1 is active through an eligible pair, the other only through a pair of
    the named status.'''
    found = base_cells(script, 2024, link('P1', 'U1', fy=(1, 0, 0)), *links)
    assert_cells(found, [(SD, 1, False, False)])


def test_intra_group_pair_of_the_same_cell_does_not_recur(script):
    found = base_cells(script, 2024, link('P1', 'U1', fy=(1, 0, 0)),
                       link('P2', 'U2', intra=True, fy=(0, 1, 0)))
    assert_cells(found, [(SD, 1, False, False)])


# ---- small bundles, authentication and self-checks (Task 3)

RUNS = Path('derived/usaspending/vendor-links')
READ_FILES = ('report.json', 'vendor_link_pairs.parquet', 'vendor_link_support.parquet',
              'vendor_links.parquet')
PAIR_TABLE, SUPPORT_TABLE, TARGET_TABLE = ('vendor_link_pairs', 'vendor_link_support',
                                           'vendor_links')
READ_COLUMNS = {
    PAIR_TABLE: ('prime_uei', 'sub_uei', 'n_reports', 'n_fy2024', 'n_fy2025', 'n_fy2026',
                 'prime_node_id', 'sub_node_id', 'pair_status'),
    SUPPORT_TABLE: ('unit_a', 'unit_b', 's_suppliers', 'b_buyers', 'l_pairs', 'l_fy2024',
                    'l_fy2025', 'l_fy2026'),
    TARGET_TABLE: ('measure', 'unit_a', 'unit_b', 'n_unweighted', 'flags'),
}
DIST = 'n_unweighted_distribution'
SUPPLIER, BUYER = 'supplier_share', 'buyer_share'
REFUSED_ROWS = 'target rows differ from the support table'


def golden_links():
    '''Cells SD and ED. Every base cell of both year pairs is testable and recurs. P2–X is
    `sub_ineligible` with a null `sub_node_id`, and the intra-group P2–U1 puts `INTRA_LABEL`
    on the `buyer_share` row of SD.'''
    return [link('P1', 'U1', fy=(1, 1, 1)), link('P1', 'U2', fy=(1, 1, 0)),
            link('P2', 'U3', fy=(2, 1, 1)), link('P2', 'X', fy=(1, 0, 0)),
            link('P2', 'U1', intra=True, fy=(1, 0, 0))]


def failing_links():
    '''The one 2024 base cell, SD, is testable and does not recur. Both 2025 base cells, ED
    and SE, are testable and recur.'''
    return [link('P1', 'U1', fy=(1, 0, 0)), link('P1', 'U3', fy=(0, 1, 1)),
            link('P3', 'U1', fy=(0, 1, 1))]


def rehash(directory: Path) -> str:
    '''Rewrite `outputs.json` from the inventory of the bundle files and return its SHA-256.'''
    write_json(directory / 'outputs.json', inventory(directory, list(FILES)))
    return sha256_file(directory / 'outputs.json')


def publish(root: Path, links: list[dict], *, firms=FIRMS, run='fixture') -> dict:
    '''A small Stage 14 bundle of `links` under `root/data`, built by the frozen `estimate`.'''
    table = pair_frame(firms, *links)
    result = estimate(table, snapshot=date(2026, 11, 19), month='2026-10')
    data_dir = root / 'data'
    directory = data_dir / RUNS / run
    directory.mkdir(parents=True)
    tables = {'vendor_links': result.targets, 'vendor_link_marginals': result.marginals,
              'vendor_link_support': result.support, 'vendor_link_pairs': table}
    for name in TABLES:
        tables[name].write_parquet(directory / f'{name}.parquet')
    write_json(directory / 'report.json', result.report)
    write_json(directory / 'inputs.json', {})
    return {'data_dir': data_dir, 'directory': directory, 'run': run, 'pin': rehash(directory)}


def forge_table(bundle: dict, name: str, change) -> str:
    '''Apply `change` to the table `name`, rehash the bundle and return the new pin.'''
    file = bundle['directory'] / f'{name}.parquet'
    change(pl.read_parquet(file)).write_parquet(file)
    return rehash(bundle['directory'])


def forge_report(bundle: dict, change) -> str:
    '''Replace `report.json` by `change` of its value, rehash the bundle and return the pin.'''
    file = bundle['directory'] / 'report.json'
    write_json(file, change(json.loads(file.read_text(encoding='utf-8'))))
    return rehash(bundle['directory'])


@pytest.fixture
def golden(tmp_path):
    return publish(tmp_path, golden_links())


def run_checks(script, bundle, *, run=None, pin=None):
    '''`self_check` of the authenticated bundle, by default under its own run and pin.'''
    inputs = script.authenticate(bundle['data_dir'], bundle['run'] if run is None else run,
                                 bundle['pin'] if pin is None else pin)
    return script.self_check(inputs)


def assert_refused(script, bundle, reason, **names):
    '''The checks refuse with exactly `reason`, and the exception holds nothing else.'''
    with pytest.raises(script.Refused) as caught:
        run_checks(script, bundle, **names)
    assert caught.value.args == (reason,)


def append(file: Path, data: bytes = b'\0') -> None:
    with file.open('ab') as stream:
        stream.write(data)


def outputs_records(bundle: dict) -> dict:
    return json.loads((bundle['directory'] / 'outputs.json').read_text(encoding='utf-8'))


def is_pair(prime, sub):
    return (pl.col('prime_uei') == uei(prime)) & (pl.col('sub_uei') == uei(sub))


def is_cell(cell, measure=None):
    where = (pl.col('unit_a') == cell[0]) & (pl.col('unit_b') == cell[1])
    return where if measure is None else where & (pl.col('measure') == measure)


def bump(column, where, by=1):
    '''A table change that adds `by` to `column` on the rows where `where` holds.'''
    changed = pl.col(column) + by if by >= 0 else pl.col(column) - -by
    return lambda table: table.with_columns(
        pl.when(where).then(changed).otherwise(pl.col(column)).alias(column))


def replaced(column, value, where):
    '''A table change that sets `column` to `value` on the rows where `where` holds.'''
    return lambda table: table.with_columns(
        pl.when(where).then(pl.lit(value)).otherwise(pl.col(column)).alias(column))


def retyped(column, expression):
    return lambda table: table.with_columns(expression.alias(column))


def twice(where):
    '''A table change that appends a copy of the rows where `where` holds.'''
    return lambda table: pl.concat([table, table.filter(where)])


def dropped(where):
    return lambda table: table.filter(~where)


def added(where, **columns):
    '''A table change that appends a copy of the rows where `where` holds, with `columns`
    replaced.'''
    return lambda table: pl.concat([table, table.filter(where).with_columns(**columns)])


def then(*changes):
    '''One change that applies `changes` in order.'''
    def change(value):
        for each in changes:
            value = each(value)
        return value
    return change


def at(*path, change=None):
    '''A report change that replaces the value at the key `path` by `change` of it, or deletes
    the key when `change` is None.'''
    def apply(report):
        *parents, key = path
        holder = report
        for part in parents:
            holder = holder[part]
        if change is None:
            del holder[key]
        else:
            holder[key] = change(holder.get(key))
        return report
    return apply


def on(name, change):
    '''A forge of the table `name`, or of `report.json` when `name` is `report`.'''
    if name == 'report':
        return lambda bundle: forge_report(bundle, change)
    return lambda bundle: forge_table(bundle, name, change)


def forges(*steps):
    '''Several forges in order. The pin is that of the last.'''
    return lambda bundle: [step(bundle) for step in steps][-1]


def swapped_supplier_counts(table):
    '''The golden `supplier_share` counts of SD (2) and ED (1), exchanged.'''
    supplier = pl.col('measure') == SUPPLIER
    return table.with_columns(n_unweighted=pl.when(supplier & is_cell(SD))
                              .then(pl.lit(1, dtype=pl.UInt64))
                              .when(supplier & is_cell(ED)).then(pl.lit(2, dtype=pl.UInt64))
                              .otherwise(pl.col('n_unweighted')))


def test_authenticate_returns_pinned_files(script, golden):
    inputs = script.authenticate(golden['data_dir'], golden['run'], golden['pin'])
    assert inputs.outputs_sha256 == golden['pin']
    records = outputs_records(golden)
    assert inputs.files == {name: records[name]['sha256'] for name in READ_FILES}


@pytest.mark.parametrize('run, pin', [
    ('../fixture', None), ('fixture/', None), ('-fixture', None), ('fixture\n', None),
    (None, 'A' * 64), (None, '0' * 63),
], ids=['parent', 'trailing-slash', 'leading-dash', 'newline', 'upper-pin', 'short-pin'])
def test_unsafe_run_id_or_pin_refused(script, golden, run, pin):
    assert_refused(script, golden, 'unsafe run id or pin', run=run, pin=pin)


def test_wrong_or_missing_pin_refused(script, golden):
    assert_refused(script, golden, 'outputs pin differs', pin='0' * 64)
    (golden['directory'] / 'outputs.json').unlink()
    assert_refused(script, golden, 'outputs pin differs')


@pytest.mark.parametrize('name', READ_FILES)
def test_changed_file_refused(script, golden, name):
    append(golden['directory'] / name)
    assert_refused(script, golden, f'{name} differs from its inventory')


def test_size_is_checked(script, golden):
    records = outputs_records(golden)
    records['vendor_link_pairs.parquet']['size'] += 1
    write_json(golden['directory'] / 'outputs.json', records)
    assert_refused(script, golden, 'vendor_link_pairs.parquet differs from its inventory',
                   pin=sha256_file(golden['directory'] / 'outputs.json'))


def test_missing_record_refused(script, golden):
    records = outputs_records(golden)
    del records['vendor_link_support.parquet']
    write_json(golden['directory'] / 'outputs.json', records)
    assert_refused(script, golden, 'vendor_link_support.parquet differs from its inventory',
                   pin=sha256_file(golden['directory'] / 'outputs.json'))


def test_pin_is_checked_before_files(script, golden):
    append(golden['directory'] / 'vendor_link_pairs.parquet')
    assert_refused(script, golden, 'outputs pin differs', pin='0' * 64)


def test_unread_files_are_never_read(script, golden):
    append(golden['directory'] / 'inputs.json', b' ')
    append(golden['directory'] / 'vendor_link_marginals.parquet')
    assert isinstance(run_checks(script, golden), script.Checked)


@pytest.mark.parametrize('name, change, reason', [
    (PAIR_TABLE, retyped('n_fy2025', pl.col('n_fy2025').cast(pl.Int64)),
     'vendor_link_pairs.parquet columns differ from the contract'),
    (SUPPORT_TABLE, lambda table: table.drop('l_fy2026'),
     'vendor_link_support.parquet columns differ from the contract'),
], ids=['retyped', 'missing'])
def test_retyped_or_missing_column_refused(script, golden, name, change, reason):
    assert_refused(script, golden, reason, pin=forge_table(golden, name, change))


def test_golden_passes_with_a_null_ineligible_node(script, golden):
    assert isinstance(run_checks(script, golden), script.Checked)


@pytest.mark.parametrize('forge, reason', [
    (on(PAIR_TABLE, twice(is_pair('P1', 'U1'))), 'pair keys are not unique'),
    (on(PAIR_TABLE, replaced('sub_node_id', None, is_pair('P1', 'U1'))),
     'an eligible pair lacks a node'),
    (on(PAIR_TABLE, bump('n_reports', is_pair('P1', 'U1'))),
     'pair report counts differ from their fiscal years'),
    (on(SUPPORT_TABLE, dropped(is_cell(SD))), 'pooled recount differs from the support table'),
    (on(SUPPORT_TABLE, bump('s_suppliers', is_cell(SD))),
     'pooled recount differs from the support table'),
    (on(SUPPORT_TABLE, bump('l_fy2025', is_cell(SD))),
     'fiscal-year recount differs from the support table'),
    (on(TARGET_TABLE, bump('n_unweighted', is_cell(SD, SUPPLIER))), REFUSED_ROWS),
    (on(TARGET_TABLE, dropped(is_cell(SD, BUYER))), REFUSED_ROWS),
    (on(TARGET_TABLE, replaced('measure', 'other_share', is_cell(SD, SUPPLIER))), REFUSED_ROWS),
    (on('report', at(DIST)), 'report is malformed'),
    (on('report', at(DIST, BUYER)), 'report is malformed'),
    (on('report', at(DIST, BUYER, 'max', change=lambda value: value + 1)),
     'report distribution differs from the targets'),
], ids=['duplicated-pair', 'null-sub-node', 'report-count', 'dropped-support-row',
        'support-suppliers', 'support-fy2025', 'supplier-count', 'dropped-buyer-row',
        'other-measure', 'no-distribution', 'no-buyer-entry', 'buyer-max'])
def test_self_check_refusals(script, golden, forge, reason):
    assert_refused(script, golden, reason, pin=forge(golden))


# ---- Task 3 input shapes beyond the plan tests

@pytest.mark.parametrize('run, pin', [
    ('', None), ('_fixture', None), ('fix ture', None), (None, '0' * 65),
    (None, '0' * 64 + '\n'), (None, 'g' * 64),
], ids=['empty', 'leading-underscore', 'space', 'long-pin', 'pin-newline', 'pin-not-hex'])
def test_unsafe_names_beyond_the_plan_refused(script, golden, run, pin):
    assert_refused(script, golden, 'unsafe run id or pin', run=run, pin=pin)


def test_run_id_may_hold_underscores_and_dashes(script, tmp_path):
    bundle = publish(tmp_path, golden_links(), run='Stage14_run-2')
    assert isinstance(run_checks(script, bundle), script.Checked)


@pytest.mark.parametrize('name', READ_FILES)
def test_missing_read_file_refused(script, golden, name):
    (golden['directory'] / name).unlink()
    assert_refused(script, golden, f'{name} differs from its inventory')


@pytest.mark.parametrize('name', READ_FILES)
def test_change_that_keeps_the_size_refused(script, golden, name):
    file = golden['directory'] / name
    data = bytearray(file.read_bytes())
    data[-1] ^= 1
    file.write_bytes(bytes(data))
    assert_refused(script, golden, f'{name} differs from its inventory')


@pytest.mark.parametrize('text', ['[]', 'not json', None],
                         ids=['list', 'not-json', 'record-not-an-object'])
def test_outputs_that_are_not_an_inventory_refused(script, golden, text):
    outputs = golden['directory'] / 'outputs.json'
    if text is None:
        records = outputs_records(golden)
        records['report.json'] = records['report.json']['sha256']
        write_json(outputs, records)
    else:
        outputs.write_text(text, encoding='utf-8')
    assert_refused(script, golden, 'report.json differs from its inventory',
                   pin=sha256_file(outputs))


@pytest.mark.parametrize('first', range(3), ids=READ_FILES[:3])
def test_first_changed_file_is_named(script, golden, first):
    '''Files `READ_FILES[first:]` change, and the refusal names the first in check order.'''
    for name in READ_FILES[first:]:
        append(golden['directory'] / name)
    assert_refused(script, golden, f'{READ_FILES[first]} differs from its inventory')


def test_inventory_is_checked_before_columns(script, golden):
    file = golden['directory'] / 'vendor_link_pairs.parquet'
    pl.read_parquet(file).with_columns(pl.col('n_fy2025').cast(pl.Int64)).write_parquet(file)
    assert_refused(script, golden, 'vendor_link_pairs.parquet differs from its inventory')


def test_every_read_file_is_hashed_before_any_column_check(script, golden):
    pin = forge_table(golden, PAIR_TABLE, retyped('n_fy2025', pl.col('n_fy2025').cast(pl.Int64)))
    append(golden['directory'] / 'vendor_links.parquet')
    assert_refused(script, golden, 'vendor_links.parquet differs from its inventory', pin=pin)


@pytest.mark.parametrize('name, column', [
    (name, column) for name, columns in READ_COLUMNS.items() for column in columns])
def test_every_read_column_is_required(script, golden, name, column):
    pin = forge_table(golden, name, lambda table: table.drop(column))
    assert_refused(script, golden, f'{name}.parquet columns differ from the contract', pin=pin)


@pytest.mark.parametrize('name, column, expression', [
    (PAIR_TABLE, 'pair_status', pl.col('pair_status').cast(pl.Categorical)),
    (SUPPORT_TABLE, 'l_pairs', pl.col('l_pairs').cast(pl.Int64)),
    (TARGET_TABLE, 'n_unweighted', pl.col('n_unweighted').cast(pl.Int64)),
    (TARGET_TABLE, 'flags', pl.col('flags').list.join(',')),
], ids=['pair-status', 'support-pairs', 'target-count', 'target-flags'])
def test_retyped_column_of_each_table_refused(script, golden, name, column, expression):
    pin = forge_table(golden, name, retyped(column, expression))
    assert_refused(script, golden, f'{name}.parquet columns differ from the contract', pin=pin)


@pytest.mark.parametrize('name, column', [
    (PAIR_TABLE, 'amount_sum'), (PAIR_TABLE, 'flag_intra_group'), (SUPPORT_TABLE, 'n_reports'),
    (SUPPORT_TABLE, 'amount_sum'), (TARGET_TABLE, 'value'), (TARGET_TABLE, 'universe'),
])
def test_unread_columns_are_not_required(script, golden, name, column):
    pin = forge_table(golden, name, lambda table: table.drop(column))
    assert isinstance(run_checks(script, golden, pin=pin), script.Checked)


@pytest.mark.parametrize('name, change', [
    (PAIR_TABLE, retyped('n_fy2025', pl.col('n_fy2025').cast(pl.Int64))),
    (SUPPORT_TABLE, lambda table: table.drop('l_fy2026')),
    (TARGET_TABLE, lambda table: table.drop('flags')),
], ids=['pairs', 'support', 'targets'])
def test_columns_of_every_table_are_checked_before_the_pair_keys(script, golden, name, change):
    forge_table(golden, PAIR_TABLE, twice(is_pair('P2', 'X')))
    pin = forge_table(golden, name, change)
    assert_refused(script, golden, f'{name}.parquet columns differ from the contract', pin=pin)


@pytest.mark.parametrize('forge, reason', [
    (on(PAIR_TABLE, twice(is_pair('P2', 'X'))), 'pair keys are not unique'),
    (on(PAIR_TABLE, added(is_pair('P1', 'U1'), n_reports=pl.col('n_reports') + 1,
                          n_fy2024=pl.col('n_fy2024') + 1)), 'pair keys are not unique'),
    (on(PAIR_TABLE, replaced('prime_node_id', None, is_pair('P1', 'U1'))),
     'an eligible pair lacks a node'),
    (on(PAIR_TABLE, bump('n_fy2025', is_pair('P1', 'U1'))),
     'pair report counts differ from their fiscal years'),
    (on(PAIR_TABLE, replaced('n_reports', None, is_pair('P1', 'U1'))),
     'pair report counts differ from their fiscal years'),
    (on(PAIR_TABLE, replaced('n_fy2026', None, is_pair('P1', 'U2'))),
     'pair report counts differ from their fiscal years'),
    (on(SUPPORT_TABLE, bump('b_buyers', is_cell(SD))),
     'pooled recount differs from the support table'),
    (on(SUPPORT_TABLE, bump('l_pairs', is_cell(SD))),
     'pooled recount differs from the support table'),
    (on(SUPPORT_TABLE, added(is_cell(SD), unit_b=pl.lit(node(E)))),
     'pooled recount differs from the support table'),
    (on(SUPPORT_TABLE, bump('l_fy2024', is_cell(SD))),
     'fiscal-year recount differs from the support table'),
    (on(SUPPORT_TABLE, bump('l_fy2026', is_cell(SD))),
     'fiscal-year recount differs from the support table'),
    (on(SUPPORT_TABLE, bump('l_fy2025', is_cell(ED))),
     'fiscal-year recount differs from the support table'),
    (on(SUPPORT_TABLE, bump('l_fy2024', is_cell(SD), by=-1)),
     'fiscal-year recount differs from the support table'),
    (on(TARGET_TABLE, bump('n_unweighted', is_cell(SD, BUYER))), REFUSED_ROWS),
    (on(TARGET_TABLE, dropped(is_cell(SD, SUPPLIER))), REFUSED_ROWS),
    (on(TARGET_TABLE, twice(is_cell(SD, SUPPLIER))), REFUSED_ROWS),
    (on(TARGET_TABLE, added(is_cell(SD, SUPPLIER), measure=pl.lit('other_share'))),
     REFUSED_ROWS),
    (on(TARGET_TABLE, added(is_cell(SD, SUPPLIER), measure=pl.lit(None, dtype=pl.String))),
     REFUSED_ROWS),
    (on(TARGET_TABLE, swapped_supplier_counts), REFUSED_ROWS),
    (on(TARGET_TABLE, replaced('unit_b', node(E), is_cell(SD, SUPPLIER))), REFUSED_ROWS),
    (on('report', lambda report: [report]), 'report is malformed'),
    (on('report', at(DIST, change=lambda entries: list(entries.values()))),
     'report is malformed'),
    (on('report', at(DIST, SUPPLIER)), 'report is malformed'),
    (on('report', at(DIST, 'other_share', change=lambda _: {})), 'report is malformed'),
    (on('report', at(DIST, SUPPLIER, change=lambda _: None)), 'report is malformed'),
    (on('report', at(DIST, BUYER, change=lambda entry: list(entry.items()))),
     'report is malformed'),
    (on('report', at(DIST, SUPPLIER, 'median', change=lambda value: value + 0.5)),
     'report distribution differs from the targets'),
    (on('report', at(DIST, SUPPLIER, 'count', change=lambda value: value + 1)),
     'report distribution differs from the targets'),
    (on('report', at(DIST, BUYER, 'p90')), 'report distribution differs from the targets'),
    (on('report', at(DIST, BUYER, 'mean', change=lambda _: 1)),
     'report distribution differs from the targets'),
], ids=['duplicated-ineligible-pair', 'duplicated-key-other-counts', 'null-prime-node',
        'fiscal-year-count', 'null-report-count', 'null-fiscal-year-count', 'support-buyers',
        'support-pairs', 'extra-support-cell', 'support-fy2024', 'support-fy2026',
        'support-fy2025-other-cell', 'support-fy2024-lower', 'buyer-count',
        'dropped-supplier-row', 'duplicated-supplier-row', 'extra-other-measure-row',
        'extra-null-measure-row', 'swapped-supplier-counts', 'changed-target-cell',
        'report-not-an-object', 'distribution-not-an-object', 'no-supplier-entry',
        'extra-measure-entry', 'supplier-entry-null', 'buyer-entry-a-list', 'supplier-median',
        'supplier-count-entry', 'buyer-entry-lacks-a-key', 'buyer-entry-extra-key'])
def test_more_self_check_refusals(script, golden, forge, reason):
    assert_refused(script, golden, reason, pin=forge(golden))


def test_report_that_is_not_json_refused(script, golden):
    (golden['directory'] / 'report.json').write_text('not json', encoding='utf-8')
    assert_refused(script, golden, 'report is malformed', pin=rehash(golden['directory']))


@pytest.mark.parametrize('forge', [
    on(PAIR_TABLE, lambda table: table.reverse()),
    on(SUPPORT_TABLE, lambda table: table.reverse()),
    on(TARGET_TABLE, lambda table: table.reverse()),
    on(PAIR_TABLE, bump('n_reports', is_pair('P2', 'X'))),
    on(PAIR_TABLE, bump('n_reports', is_pair('P2', 'U1'))),
    on('report', lambda report: {DIST: report[DIST]}),
], ids=['reversed-pairs', 'reversed-support', 'reversed-targets',
        'sub-ineligible-report-count', 'intra-group-report-count', 'report-distribution-only'])
def test_valid_variants_pass(script, golden, forge):
    assert isinstance(run_checks(script, golden, pin=forge(golden)), script.Checked)


@pytest.mark.parametrize('status, extra', [
    ('prime_ineligible', link('X', 'U1')), ('self_link', link('X', 'X')),
    ('intra_group', link('P3', 'X', intra=True)), ('sub_ineligible', link('P3', 'X')),
], ids=['prime-ineligible', 'self-link', 'intra-group', 'sub-ineligible'])
def test_every_ineligible_status_may_lack_a_node(script, tmp_path, status, extra):
    bundle = publish(tmp_path, [*golden_links(), extra])
    pairs = pl.read_parquet(bundle['directory'] / 'vendor_link_pairs.parquet')
    row = pairs.filter(is_pair(extra['prime'], extra['sub']))
    assert row['pair_status'].to_list() == [status]
    assert row.select(pl.col('prime_node_id').is_null() | pl.col('sub_node_id').is_null()).item()
    assert isinstance(run_checks(script, bundle), script.Checked)


def test_cell_with_more_pairs_than_subcontractors_passes(script, tmp_path):
    '''One subcontractor with two primes: S is 1 while B and L are 2, pooled and in FY2024.'''
    bundle = publish(tmp_path, [link('P1', 'U1', fy=(1, 0, 0)), link('P2', 'U1', fy=(1, 0, 0))])
    assert isinstance(run_checks(script, bundle), script.Checked)


def test_failing_bundle_shape(script, tmp_path):
    checked = run_checks(script, publish(tmp_path, failing_links()))
    assert_cells(script.cells(checked.eligible, 2024), [(SD, 1, True, False)])
    assert_cells(script.cells(checked.eligible, 2025),
                 [(ED, 1, True, True), (SE, 1, True, True)])


@pytest.mark.parametrize('column, cell', [
    ('l_fy2025', SD), ('l_fy2026', SD), ('l_fy2024', ED), ('l_fy2024', SE),
], ids=['middle-year', 'last-year', 'first-year', 'first-year-last-cell'])
def test_support_count_for_a_year_without_a_pair_refused(script, tmp_path, column, cell):
    '''In the failing bundle, SD has a pair only in FY2024, and ED and SE none in FY2024.'''
    bundle = publish(tmp_path, failing_links())
    pin = forge_table(bundle, SUPPORT_TABLE, bump(column, is_cell(cell)))
    assert_refused(script, bundle, 'fiscal-year recount differs from the support table', pin=pin)


def test_golden_bundle_shape(script, golden):
    pairs = pl.read_parquet(golden['directory'] / 'vendor_link_pairs.parquet')
    assert pairs.filter(is_pair('P2', 'X')).select('pair_status', 'sub_node_id').rows() == [
        ('sub_ineligible', None)]
    checked = run_checks(script, golden)
    for base in (2024, 2025):
        assert_cells(script.cells(checked.eligible, base),
                     [(ED, 1, True, True), (SD, 2, True, True)],
                     [(ED, 1, True, True), (SD, 1, True, True)])
    flagged = checked.targets.filter(pl.col('flags').list.contains(INTRA_LABEL))
    assert flagged.select('measure', 'unit_a', 'unit_b').rows() == [(BUYER, *SD)]


def test_checked_holds_the_checked_frames(script, golden):
    inputs = script.authenticate(golden['data_dir'], golden['run'], golden['pin'])
    assert inputs.directory == golden['directory']
    with pytest.raises(dataclasses.FrozenInstanceError):
        inputs.outputs_sha256 = '0' * 64
    checked = script.self_check(inputs)
    table = pair_frame(FIRMS, *golden_links())
    expected = script.eligible_pairs(table.lazy())
    assert isinstance(checked.eligible, pl.LazyFrame)
    assert_frame_equal(checked.eligible.collect(), expected.collect())
    assert_frame_equal(checked.years, script.year_counts(expected))
    targets = estimate(table, snapshot=date(2026, 11, 19), month='2026-10').targets
    assert_frame_equal(checked.targets, targets.select(READ_COLUMNS[TARGET_TABLE]))
    report = json.loads((golden['directory'] / 'report.json').read_text(encoding='utf-8'))
    assert checked.distributions == report[DIST]
    assert list(checked.distributions) == list(script.MEASURES)
    with pytest.raises(dataclasses.FrozenInstanceError):
        checked.targets = None


@pytest.mark.parametrize('forge, reason', [
    (on(PAIR_TABLE, then(twice(is_pair('P1', 'U1')),
                         replaced('sub_node_id', None, is_pair('P1', 'U1')))),
     'pair keys are not unique'),
    (on(PAIR_TABLE, then(replaced('sub_node_id', None, is_pair('P1', 'U1')),
                         bump('n_reports', is_pair('P1', 'U1')))),
     'an eligible pair lacks a node'),
    (forges(on(PAIR_TABLE, bump('n_reports', is_pair('P1', 'U1'))),
            on(SUPPORT_TABLE, dropped(is_cell(SD)))),
     'pair report counts differ from their fiscal years'),
    (on(SUPPORT_TABLE, then(bump('s_suppliers', is_cell(SD)), bump('l_fy2025', is_cell(SD)))),
     'pooled recount differs from the support table'),
    (forges(on(SUPPORT_TABLE, bump('l_fy2025', is_cell(SD))),
            on(TARGET_TABLE, bump('n_unweighted', is_cell(SD, SUPPLIER)))),
     'fiscal-year recount differs from the support table'),
    (forges(on(TARGET_TABLE, bump('n_unweighted', is_cell(SD, SUPPLIER))),
            on('report', at(DIST))), REFUSED_ROWS),
    (on('report', then(at(DIST, BUYER), at(DIST, SUPPLIER, 'max', change=lambda v: v + 1))),
     'report is malformed'),
], ids=['5-before-6', '6-before-7', '7-before-8', '8-before-9', '9-before-10', '10-before-11',
        '11-before-12'])
def test_earlier_check_refuses_first(script, golden, forge, reason):
    assert_refused(script, golden, reason, pin=forge(golden))
