'''The Stage 21 minimum-count script, on small synthetic cells frames and pair tables.

Every pair table is a typed frame in `PAIR_SCHEMA` with made-up UEIs that passes
`validate_pairs`, as in `tests/test_vendor_link_targets.py`.
'''

import importlib.util
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from embedding_data.vendor_link_codes import NODE_PREFIX
from embedding_data.vendor_link_pairs import FIRM_STATUSES, PAIR_SCHEMA, validate_pairs

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
