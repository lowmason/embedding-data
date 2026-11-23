'''Measure the Stage 22 minimum count of the TRI parent-link targets.

The rule groups testable cells into bands by base count, merges short bands upward and a thin
top band downward, and sets a year pair's minimum at the start of the trailing run of bands
whose recurrence rate reaches `LEVEL`, as the spec section "From curves to a minimum" in
`specs/tri-minimum-counts.md` says. The band functions are copied from
`scripts/measure_ita_minimum_counts.py` so that the Stage 22 constants govern them. The
downward merge and the total check run after `bands`, in `merge_thin_top` and `curve`.
'''

import math

import polars as pl

from embedding_data.tri_parent_link_targets import YEARS

LEVEL = 0.90
TOP_BAND = 10
MIN_BAND_CELLS = 50
WILSON_Z = 1.959963984540054
YEAR_PAIRS = tuple(zip(YEARS, YEARS[1:]))
COUNTS = ('base_cells', 'testable_cells', 'recurring_cells')


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
    '''The bands of one year pair, from the lowest count up.

    A band below TOP_BAND with fewer than MIN_BAND_CELLS testable cells merges into the next
    higher band, and a merged band starts at its lowest count. The top band keeps its
    cells whatever their number: `merge_thin_top` merges it later.
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


def family_minimum(minimums: list[int | None]) -> int | None:
    '''The largest year-pair minimum, or None when any year pair has none.'''
    if not minimums or any(minimum is None for minimum in minimums):
        return None
    return max(minimums)


def merge_thin_top(found: list[dict]) -> tuple[list[dict], list[dict] | None]:
    '''The bands after spec step 3, and the two bands that it merged, or None.

    A top band with fewer than MIN_BAND_CELLS testable cells merges into the band directly
    below it, when a band lies below. The merged band starts at the lower band's start. Its
    rate and its Wilson interval come from the summed counts, never from the two rates.
    '''
    if len(found) < 2 or found[-1]['testable_cells'] >= MIN_BAND_CELLS:
        return found, None
    below, top = found[-2:]
    pending = {key: below[key] + top[key] for key in COUNTS} | {'low': below['low']}
    return [*found[:-2], close_band(pending, None)], [below, top]


def curve(cells: pl.DataFrame) -> dict:
    '''The bands, the minimum and the absence reason of one year pair.

    Fewer than MIN_BAND_CELLS testable cells in total give no minimum. Otherwise the minimum
    is that of the merged bands, and a top band that misses LEVEL gives no minimum.
    '''
    merged, before = merge_thin_top(bands(cells))
    totals = {key: sum(band[key] for band in merged) for key in COUNTS}
    if totals['testable_cells'] < MIN_BAND_CELLS:
        minimum, reason = None, 'too_few_testable_cells'
    else:
        minimum = pair_minimum(merged)
        reason = None if minimum is not None else 'top_band_misses_level'
    return totals | {
        'bands': merged,
        'before_downward_merge': before,
        'minimum': minimum,
        'reason': reason,
    }


def eligible_facility_years(table: pl.LazyFrame) -> pl.DataFrame:
    '''The eligible facility-years: `year`, `trifd`, `node` and `owner`, sorted by year and TRIFD.

    A facility-year is eligible when its `exclusion_reason` is null, as spec "Per-year counts"
    says. An excluded row has no owner, so every later join would drop it without this filter.
    '''
    return table.filter(pl.col('exclusion_reason').is_null()).select(
        pl.col('reporting_year').alias('year'),
        pl.col('trifd'),
        pl.col('naics_2022_node_id').alias('node'),
        pl.col('owner_key').alias('owner'),
    ).sort('year', 'trifd').collect()


def recount(eligible: pl.DataFrame) -> pl.DataFrame:
    '''The owners of each ordered pair of distinct nodes, over all years and in each year.

    An owner joins two nodes of one year. `j_owners` counts the distinct owners over all years,
    and `j_<year>` counts them in that year, so `j_owners` is not the sum of the years.
    '''
    presence = eligible.select('owner', 'year', 'node').unique()
    pairs = presence.join(presence, on=['owner', 'year'], suffix='_b').filter(
        pl.col('node') != pl.col('node_b'))
    owner = pl.col('owner')
    return pairs.group_by('node', 'node_b').agg(
        owner.n_unique().cast(pl.UInt64).alias('j_owners'),
        *(owner.filter(pl.col('year') == year).n_unique().cast(pl.UInt64).alias(f'j_{year}')
          for year in YEARS),
    ).rename({'node': 'unit_a', 'node_b': 'unit_b'}).sort('unit_a', 'unit_b')


def year_cells(eligible: pl.DataFrame, counts: pl.DataFrame, base: int) -> pl.DataFrame:
    '''The base cells of year `base`, each with its count, its testability and its recurrence.

    A year-`base` row is staying when a row of the next year has the same TRIFD and the same
    owner. An owner is staying at a node when any of its rows there stays. A cell is testable
    when one owner is staying at both nodes. It recurs when any owner links the nodes in the
    next year. `base_count` and `recurs` come from `counts`.
    '''
    following = eligible.filter(pl.col('year') == base + 1).select('trifd', 'owner').unique()
    rows = eligible.filter(pl.col('year') == base).join(
        following.with_columns(pl.lit(True).alias('staying')), on=['trifd', 'owner'], how='left')
    owners = rows.group_by('owner', 'node').agg(pl.col('staying').fill_null(False).any())
    staying = owners.filter(pl.col('staying'))
    testable = staying.join(staying, on='owner', suffix='_b').filter(
        pl.col('node') != pl.col('node_b')).select(
        pl.col('node').alias('unit_a'), pl.col('node_b').alias('unit_b'),
        pl.lit(True).alias('testable')).unique()
    base_cells = counts.filter(pl.col(f'j_{base}') >= 1).select(
        'unit_a', 'unit_b', pl.col(f'j_{base}').alias('base_count'),
        (pl.col(f'j_{base + 1}') >= 1).alias('recurs'))
    return base_cells.join(testable, on=['unit_a', 'unit_b'], how='left').select(
        'unit_a', 'unit_b', 'base_count', pl.col('testable').fill_null(False), 'recurs',
    ).sort('unit_a', 'unit_b')
