'''Measure the headline minimum counts of the two USAspending vendor-link targets.

The rule groups testable cells into bands by base-year count, merges short bands upward, and
sets a year pair's minimum at the start of the trailing run of bands whose recurrence rate
reaches `LEVEL`. A measure's minimum is the largest minimum over its year pairs, and a top
band that misses `LEVEL` leaves the measure with no minimum. Rates use the point estimate, so
the Wilson interval is for readers only. The source is the spec section "From curves to a
minimum" in `specs/usaspending-minimum-counts.md`. The band functions are copied from
`scripts/measure_ita_minimum_counts.py` so that the Stage 21 constants govern.

Before any curve, the script authenticates the pinned Stage 14 run by its detached pin and by
the SHA-256 and size of the four files it reads. Then it checks a recount from the pair table
against the bundle's own support table, targets and report. A refusal is a `Refused` whose
message is one fixed reason.

The command prints one sorted JSON line: the constants, the input pins, each measure's curves,
minimum, report distribution and kept counts, and the cells whose two rows are both kept. It
exits 0 when both measures have a minimum, 1 when one does not, and 2 on a refusal or any
other error.
'''

import argparse
import hashlib
import json
import math
import re
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from embedding_data.target_contract import TARGET_SCHEMA
from embedding_data.usaspending_raw import WINDOW
from embedding_data.vendor_link_pairs import PAIR_SCHEMA, PAIR_STATUSES
from embedding_data.vendor_link_targets import INTRA_LABEL, MEASURES, SUPPORT_SCHEMA, _distribution

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


# ---- authentication and self-checks

RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')
PIN = re.compile(r'[0-9a-f]{64}')
RUNS = 'derived/usaspending/vendor-links'
REPORT, PAIRS, SUPPORT, TARGETS = ('report.json', 'vendor_link_pairs.parquet',
                                   'vendor_link_support.parquet', 'vendor_links.parquet')
# The read files in check order.
READ_FILES = (REPORT, PAIRS, SUPPORT, TARGETS)
_FISCAL_YEARS = tuple(f'n_fy{year}' for year in WINDOW)
_LINK_YEARS = tuple(f'l_fy{year}' for year in WINDOW)
_SUPPORT_COUNTS = ('s_suppliers', 'b_buyers', 'l_pairs')
# The read columns of each Parquet file, with their types from the frozen schemas.
CONTRACT = {
    PAIRS: {name: PAIR_SCHEMA[name] for name in (
        'prime_uei', 'sub_uei', 'n_reports', *_FISCAL_YEARS, 'prime_node_id', 'sub_node_id',
        'pair_status')},
    SUPPORT: {name: SUPPORT_SCHEMA[name] for name in (*_CELL, *_SUPPORT_COUNTS, *_LINK_YEARS)},
    TARGETS: {name: TARGET_SCHEMA[name] for name in ('measure', *_CELL, 'n_unweighted', 'flags')},
}
# Each measure's support count: `S` for `supplier_share` and `B` for `buyer_share`.
_MEASURE_COUNTS = dict(zip(MEASURES, ('s_suppliers', 'b_buyers')))
_DISTRIBUTION = 'n_unweighted_distribution'


class Refused(Exception):
    '''A refusal of the pinned run. Its message is one fixed reason and holds no value read
    from the run.'''


@dataclass(frozen=True)
class Inputs:
    '''An authenticated run: its directory, its detached pin and the SHA-256 of each read
    file.'''
    directory: Path
    outputs_sha256: str
    files: dict[str, str]


@dataclass(frozen=True)
class Checked:
    '''A self-checked run: its eligible pairs `P`, their fiscal-year counts, the read target
    columns, and the `n_unweighted_distribution` entry of each measure in `report.json`.'''
    eligible: pl.LazyFrame
    years: pl.DataFrame
    targets: pl.DataFrame
    distributions: dict[str, dict]


def _sha256(file: Path) -> str:
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _json(data: bytes):
    '''The JSON value of `data`, or None when `data` is not JSON.'''
    try:
        return json.loads(data)
    except ValueError:
        return None


def authenticate(data_dir: Path, run_id: str, pin: str) -> Inputs:
    '''Checks 1 to 3: a safe run ID and pin, the detached pin of `outputs.json`, then the
    SHA-256 and size of each read file, in `READ_FILES` order, against its record.

    The pin covers the bytes of `outputs.json` that are parsed. No other file of the run is
    read.
    '''
    if not (isinstance(run_id, str) and RUN_ID.fullmatch(run_id)
            and isinstance(pin, str) and PIN.fullmatch(pin)):
        raise Refused('unsafe run id or pin')
    directory = Path(data_dir) / RUNS / run_id
    outputs = directory / 'outputs.json'
    data = outputs.read_bytes() if outputs.is_file() else None
    if data is None or hashlib.sha256(data).hexdigest() != pin:
        raise Refused('outputs pin differs')
    records = _json(data)
    records = records if isinstance(records, dict) else {}
    files = {}
    for name in READ_FILES:
        file, record = directory / name, records.get(name)
        if (not isinstance(record, dict) or not file.is_file()
                or file.stat().st_size != record.get('size')
                or _sha256(file) != record.get('sha256')):
            raise Refused(f'{name} differs from its inventory')
        files[name] = record['sha256']
    return Inputs(directory=directory, outputs_sha256=pin, files=files)


def _refuse_if(frame: pl.LazyFrame, condition: pl.Expr, reason: str) -> None:
    '''Refuse with `reason` when `condition` holds, or is unknown, for any row.'''
    if frame.select(condition.fill_null(True).any()).collect().item():
        raise Refused(reason)


def _scan(inputs: Inputs, name: str) -> pl.LazyFrame:
    '''Check 4 for one Parquet file: every read column with its frozen type. Returns a lazy
    scan of the read columns only.'''
    scan = pl.scan_parquet(inputs.directory / name)
    schema = scan.collect_schema()
    if any(schema.get(column) != dtype for column, dtype in CONTRACT[name].items()):
        raise Refused(f'{name} columns differ from the contract')
    return scan.select(*CONTRACT[name])


def self_check(inputs: Inputs) -> Checked:
    '''Checks 4 to 12, in order. The first that fails refuses with its fixed reason.

    The read columns, then the pair table (unique keys, and both nodes and consistent report
    counts on each eligible pair), then the pooled and fiscal-year recounts against the
    support table, the target rows against the support table, and last the report
    distributions against the targets.
    '''
    pairs, support, targets = [_scan(inputs, name) for name in (PAIRS, SUPPORT, TARGETS)]
    _refuse_if(pairs, pl.struct('prime_uei', 'sub_uei').is_duplicated(),
               'pair keys are not unique')
    listed = pairs.filter(pl.col('pair_status') == _ELIGIBLE)
    _refuse_if(listed, pl.col('prime_node_id').is_null() | pl.col('sub_node_id').is_null(),
               'an eligible pair lacks a node')
    _refuse_if(listed, pl.col('n_reports') != pl.sum_horizontal(_FISCAL_YEARS, ignore_nulls=False),
               'pair report counts differ from their fiscal years')
    eligible = eligible_pairs(pairs).collect().lazy()
    support = support.collect()
    if not pooled_counts(eligible).equals(support.select(*_CELL, *_SUPPORT_COUNTS).sort(*_CELL)):
        raise Refused('pooled recount differs from the support table')
    years = year_counts(eligible)
    recount = support.lazy().select(*_CELL, *_LINK_YEARS)
    for year in WINDOW:
        recount = recount.join(years.lazy().filter(pl.col('year') == year).select(
            *_CELL, pl.col('l').alias(f'_l{year}')), on=list(_CELL), how='left')
    _refuse_if(recount, pl.any_horizontal(pl.col(f'_l{year}').fill_null(0) != pl.col(f'l_fy{year}')
                                          for year in WINDOW),
               'fiscal-year recount differs from the support table')
    targets = targets.collect()
    _refuse_if(targets.lazy(), ~pl.col('measure').is_in(MEASURES),
               'target rows differ from the support table')
    for measure, count in _MEASURE_COUNTS.items():
        rows = targets.filter(pl.col('measure') == measure).select(*_CELL, 'n_unweighted')
        expected = support.select(*_CELL, pl.col(count).alias('n_unweighted'))
        if not rows.sort(rows.columns).equals(expected.sort(expected.columns)):
            raise Refused('target rows differ from the support table')
    report = _json((inputs.directory / REPORT).read_bytes())
    entries = report.get(_DISTRIBUTION) if isinstance(report, dict) else None
    if not (isinstance(entries, dict) and set(entries) == set(MEASURES)
            and all(isinstance(entries[measure], dict) for measure in MEASURES)):
        raise Refused('report is malformed')
    for measure in MEASURES:
        series = targets.filter(pl.col('measure') == measure)['n_unweighted']
        if json.loads(json.dumps(_distribution(series.alias('n_unweighted')))) != entries[measure]:
            raise Refused('report distribution differs from the targets')
    return Checked(eligible=eligible, years=years, targets=targets,
                   distributions={measure: entries[measure] for measure in MEASURES})


# ---- kept counts, the result and the command line

# The keys of `kept` that a minimum decides. With no minimum, each is None.
KEPT_KEYS = ('kept_rows', 'kept_row_share', 'kept_support', 'kept_support_share',
             'lenient_kept_rows', 'kept_intra_group_rows')


def published(targets: pl.DataFrame, years: pl.DataFrame) -> dict[str, pl.DataFrame]:
    '''The published rows of each measure, sorted by cell.

    Each row holds its cell, its pooled `n_unweighted` as `count`, its `largest_year_count`
    and its `intra_group` label. The largest year count is the measure's largest firm count
    over every fiscal year of `WINDOW`: `S_t` for `supplier_share` and `B_t` for
    `buyer_share`, never a pair count `L_t`. `intra_group` is true when the row's `flags`
    hold `INTRA_LABEL`.
    '''
    rows = {}
    for measure, count in _BASE_COUNTS.items():
        largest = years.lazy().group_by(*_CELL).agg(
            pl.col(count).max().alias('largest_year_count'))
        rows[measure] = (
            targets.lazy().filter(pl.col('measure') == measure)
            .join(largest, on=_CELL, how='left')
            .select(*_CELL, pl.col('n_unweighted').alias('count'), 'largest_year_count',
                    pl.col('flags').list.contains(INTRA_LABEL).alias('intra_group'))
            .sort(*_CELL).collect())
    return rows


def kept(rows: pl.DataFrame, minimum: int | None) -> dict:
    '''The rows and support of one measure, and what its minimum keeps.

    A row is kept when its `count` is at least `minimum`. A kept row is lenient when its
    largest single-year count is below `minimum`. The shares divide by this measure's rows and
    by its summed counts. With no minimum, the keys of `KEPT_KEYS` are None.
    '''
    support = int(rows['count'].sum())
    counts = {'rows': rows.height, 'support': support,
              'intra_group_rows': rows.filter(pl.col('intra_group')).height}
    if minimum is None:
        return counts | dict.fromkeys(KEPT_KEYS)
    meeting = rows.filter(pl.col('count') >= minimum)
    kept_support = int(meeting['count'].sum())
    return counts | {
        'kept_rows': meeting.height,
        'kept_row_share': meeting.height / rows.height,
        'kept_support': kept_support,
        'kept_support_share': kept_support / support,
        'lenient_kept_rows': meeting.filter(pl.col('largest_year_count') < minimum).height,
        'kept_intra_group_rows': meeting.filter(pl.col('intra_group')).height,
    }


def curve(cells: pl.DataFrame) -> dict:
    '''One year pair's bands, their summed cell counts and the year pair's minimum.'''
    found = bands(cells)
    return {
        **{key: sum(band[key] for band in found) for key in COUNTS},
        'bands': found,
        'minimum': pair_minimum(found),
    }


def summarize(year_pair_cells: dict[str, dict[str, pl.DataFrame]],
              rows: dict[str, pl.DataFrame], distributions: dict[str, dict]) -> dict:
    '''Each measure's curves, minimum, report distribution and kept counts, and the number of
    cells whose two rows are both kept.

    The measures never share a minimum: each takes the larger of its own year-pair minimums,
    and each row is gated by the minimum of its own measure. `cells_meeting_both` is None when
    either measure has no minimum.
    '''
    measures = {}
    for name in MEASURES:
        year_pairs = {pair: curve(frame) for pair, frame in year_pair_cells[name].items()}
        minimum = measure_minimum([found['minimum'] for found in year_pairs.values()])
        measures[name] = {'year_pairs': year_pairs, 'minimum': minimum,
                          'n_unweighted_distribution': distributions[name],
                          'published': kept(rows[name], minimum)}
    minimums = {name: measures[name]['minimum'] for name in MEASURES}
    both = None
    if all(minimum is not None for minimum in minimums.values()):
        supplier, buyer = (rows[name].lazy().filter(pl.col('count') >= minimums[name])
                           .select(*_CELL) for name in MEASURES)
        both = supplier.join(buyer, on=_CELL, how='inner').select(pl.len()).collect().item()
    return {'measures': measures, 'cells_meeting_both': both}


def measure(inputs: Inputs) -> dict:
    '''The result of an authenticated run, with `complete` true when both measures have a
    minimum.

    `self_check` runs first, so a refusal stops the run before any cells frame or curve. The
    cells frames come from the base year of each year pair.
    '''
    checked = self_check(inputs)
    by_base = {base: cells(checked.eligible, base) for base, _later in YEAR_PAIRS}
    year_pair_cells = {name: {f'{base}-{later}': by_base[base][name]
                              for base, later in YEAR_PAIRS} for name in MEASURES}
    result = summarize(year_pair_cells, published(checked.targets, checked.years),
                       checked.distributions)
    return {
        'complete': all(result['measures'][name]['minimum'] is not None for name in MEASURES),
        'constants': {'level': LEVEL, 'top_band': TOP_BAND, 'min_band_cells': MIN_BAND_CELLS,
                      'wilson_z': WILSON_Z, 'year_pairs': [list(pair) for pair in YEAR_PAIRS]},
        'inputs': {'run': inputs.directory.name, 'outputs_sha256': inputs.outputs_sha256,
                   'files': dict(inputs.files)},
        **result,
    }


def parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Measure the Stage 21 minimum counts of the USAspending vendor links.')
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--outputs-sha256', required=True)
    return parser.parse_args(argv)


def _line(value: dict) -> str:
    return json.dumps(value, sort_keys=True, allow_nan=False)


def main(argv: list[str] | None = None) -> int:
    '''Print one sorted JSON line. Exit 0 when both measures have a minimum, 1 when one does
    not, and 2 on a refusal or any other error.

    A refusal prints only its fixed reason. Any other error prints a fixed reason, and stderr
    gets the exception's type name and one `file:line in function` line per frame. Its
    message is never printed, because it can hold a value read from the run.
    '''
    options = parse(argv)
    try:
        result = measure(authenticate(options.data_dir, options.run, options.outputs_sha256))
        line = _line(result)
    except Refused as refusal:
        print(_line({'complete': False, 'reason': str(refusal)}))
        return 2
    except Exception as error:
        print(type(error).__name__, file=sys.stderr)
        for frame in traceback.extract_tb(error.__traceback__):
            print(f'{frame.filename}:{frame.lineno} in {frame.name}', file=sys.stderr)
        print(_line({'complete': False, 'reason': 'unexpected error'}))
        return 2
    print(line)
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    sys.exit(main())
