'''Measure the headline minimum counts of the two USAspending vendor-link targets.

The rule groups testable cells into bands by base-year count, merges short bands upward, and
sets a year pair's minimum at the start of the trailing run of bands whose recurrence rate
reaches `LEVEL`. A measure's minimum is the largest minimum over its year pairs, and a top
band that misses `LEVEL` leaves the measure with no minimum. Rates use the point estimate, so
the Wilson interval is for readers only. The source is the spec section "From curves to a
minimum" in `specs/usaspending-minimum-counts.md`. The band functions are copied from
`scripts/measure_ita_minimum_counts.py` so that the Stage 21 constants govern.
'''

import math

import polars as pl

from embedding_data.usaspending_raw import WINDOW
from embedding_data.vendor_link_pairs import PAIR_STATUSES
from embedding_data.vendor_link_targets import MEASURES  # noqa: F401 (read by later tasks)

LEVEL = 0.90
TOP_BAND = 10
MIN_BAND_CELLS = 50
WILSON_Z = 1.959963984540054
YEAR_PAIRS = tuple(zip(WINDOW, WINDOW[1:]))
COUNTS = ('base_cells', 'testable_cells', 'recurring_cells')
_ELIGIBLE = PAIR_STATUSES[-1]
_CELL = ('unit_a', 'unit_b')
# Each measure's base count: `S_t` for `supplier_share` and `B_t` for `buyer_share`.
_BASE_COUNTS = dict(zip(MEASURES, ('s', 'b')))


def wilson(recurring: int, testable: int) -> tuple[float, float] | None:
    '''The 95% Wilson interval of a recurrence rate, or None when no cell is testable.'''
    if testable == 0:
        return None
    rate = recurring / testable
    square = WILSON_Z ** 2
    scale = 1 + square / testable
    center = (rate + square / (2 * testable)) / scale
    spread = WILSON_Z * math.sqrt(
        rate * (1 - rate) / testable + square / (4 * testable ** 2)) / scale
    return max(0.0, center - spread), min(1.0, center + spread)


def raw_counts(cells: pl.DataFrame) -> dict[int, dict]:
    '''The cell counts of each raw band: base counts 1 to TOP_BAND - 1 and TOP_BAND and more.

    A band with no cell has no entry. A recurring cell is testable and recurs.
    '''
    if cells.filter(pl.col('base_count') < 1).height:
        raise ValueError('a cell has a base count below 1')
    totals = cells.select(
        pl.col('base_count').clip(upper_bound=TOP_BAND).alias('band'),
        pl.col('testable'),
        (pl.col('testable') & pl.col('recurs')).alias('recurring'),
    ).group_by('band').agg(
        pl.len().alias('base_cells'),
        pl.col('testable').sum().alias('testable_cells'),
        pl.col('recurring').sum().alias('recurring_cells'),
    )
    return {row['band']: row for row in totals.to_dicts()}


def close_band(pending: dict, high: int | None) -> dict:
    '''A finished band: its counts, its recurrence rate and its Wilson interval.'''
    testable, recurring = pending['testable_cells'], pending['recurring_cells']
    interval = wilson(recurring, testable)
    return {
        'low': pending['low'],
        'high': high,
        'base_cells': pending['base_cells'],
        'testable_cells': testable,
        'recurring_cells': recurring,
        'rate': recurring / testable if testable else None,
        'wilson_low': interval[0] if interval else None,
        'wilson_high': interval[1] if interval else None,
    }


def bands(cells: pl.DataFrame) -> list[dict]:
    '''The bands of one measure and year pair, from the lowest count up.

    A band below TOP_BAND with fewer than MIN_BAND_CELLS testable cells merges into the next
    higher band, and a merged band starts at its lowest count. The top band keeps its
    cells whatever their number.
    '''
    raw = raw_counts(cells)
    merged, pending = [], None
    for index in range(1, TOP_BAND + 1):
        if pending is None:
            pending = dict.fromkeys(COUNTS, 0) | {'low': index}
        for key in COUNTS:
            pending[key] += raw.get(index, {}).get(key, 0)
        if index == TOP_BAND or pending['testable_cells'] >= MIN_BAND_CELLS:
            merged.append(close_band(pending, None if index == TOP_BAND else index))
            pending = None
    return merged


def pair_minimum(bands: list[dict]) -> int | None:
    '''The start of the trailing run of bands whose rate reaches LEVEL, or None.

    Walk the bands from the top down and stop at the first rate that is missing or below
    LEVEL. A rate equal to LEVEL passes.
    '''
    minimum = None
    for band in reversed(bands):
        if band['rate'] is None or band['rate'] < LEVEL:
            break
        minimum = band['low']
    return minimum


def measure_minimum(minimums: list[int | None]) -> int | None:
    '''The largest year-pair minimum, or None when any year pair has none.'''
    if not minimums or any(minimum is None for minimum in minimums):
        return None
    return max(minimums)


# ---- per-year counts, testable cells and recurrence

def eligible_pairs(pairs: pl.LazyFrame) -> pl.LazyFrame:
    '''`P`: the pairs with pair status `eligible`. A cell is (`unit_a`, `unit_b`): the
    subcontractor's node (the supplier industry), then the prime's (the buyer industry).'''
    return pairs.filter(pl.col('pair_status') == _ELIGIBLE).select(
        'prime_uei', 'sub_uei', pl.col('sub_node_id').alias('unit_a'),
        pl.col('prime_node_id').alias('unit_b'), *(f'n_fy{year}' for year in WINDOW))


def _in_year(eligible: pl.LazyFrame, year: int) -> pl.LazyFrame:
    '''`P_t`: the eligible pairs with a usable report in fiscal year `year`.'''
    return eligible.filter(pl.col(f'n_fy{year}') > 0)


def _tally(pairs: pl.LazyFrame, suppliers: str, buyers: str, links: str) -> pl.LazyFrame:
    '''For each cell of `pairs`: its distinct subcontractors, its distinct primes and its
    pairs. A firm counts once in a cell, however many pairs or reports it has there.'''
    return pairs.group_by(*_CELL).agg(
        pl.col('sub_uei').n_unique().cast(pl.UInt64).alias(suppliers),
        pl.col('prime_uei').n_unique().cast(pl.UInt64).alias(buyers),
        pl.len().cast(pl.UInt64).alias(links))


def pooled_counts(eligible: pl.LazyFrame) -> pl.DataFrame:
    '''`S`, `B` and `L` of each cell over the whole window, sorted by cell.'''
    return _tally(eligible, 's_suppliers', 'b_buyers', 'l_pairs').sort(*_CELL).collect()


def year_counts(eligible: pl.LazyFrame) -> pl.DataFrame:
    '''`S_t`, `B_t` and `L_t` of each cell and fiscal year of `WINDOW` with a pair in `P_t`,
    sorted by cell and year. A cell has no row for a year with no pair.'''
    years = [_tally(_in_year(eligible, year), 's', 'b', 'l').select(
        *_CELL, pl.lit(year, dtype=pl.Int64).alias('year'), 's', 'b', 'l') for year in WINDOW]
    return pl.concat(years).sort(*_CELL, 'year').collect()


def cells(eligible: pl.LazyFrame, base: int) -> dict[str, pl.DataFrame]:
    '''The cells frame of each measure for the base cells of fiscal year `base`.

    A base cell has a pair in `P_t`. It recurs when a pair of `P_{t+1}` has the same cell. It
    is testable when one of its `P_t` pairs has a subcontractor that is the subcontractor of
    some `P_{t+1}` pair and a prime that is the prime of some `P_{t+1}` pair: the roles are
    fixed. Both measures share `testable` and `recurs`, and each takes its own base count.
    Each frame holds `unit_a`, `unit_b`, `base_count`, `testable` and `recurs`, sorted by
    cell.
    '''
    now, later = _in_year(eligible, base), _in_year(eligible, base + 1)
    active = (now.join(later.select('sub_uei').unique(), on='sub_uei', how='semi')
              .join(later.select('prime_uei').unique(), on='prime_uei', how='semi'))
    table = _tally(now, 's', 'b', 'l')
    for pairs, outcome in ((active, 'testable'), (later, 'recurs')):
        marked = pairs.select(*_CELL).unique().with_columns(pl.lit(True).alias(outcome))
        table = table.join(marked, on=_CELL, how='left')
    table = (table.with_columns(pl.col('testable', 'recurs').fill_null(False))
             .sort(*_CELL).collect())
    return {measure: table.select(*_CELL, pl.col(count).alias('base_count'), 'testable',
                                  'recurs')
            for measure, count in _BASE_COUNTS.items()}
