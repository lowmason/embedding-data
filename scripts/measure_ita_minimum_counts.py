'''Measure the V9 minimum counts of the three ITA NAICS target families.

The rule groups testable cells into bands by base count, merges short bands upward, and
sets a year pair's minimum at the start of the trailing run of bands whose recurrence rate
reaches `LEVEL`. A family's minimum is the largest minimum over its year pairs, and a top
band that misses `LEVEL` leaves the family with no minimum. The source is the spec section
"From curves to a minimum" in `specs/ita-naics-minimum-counts.md`.
'''

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import polars as pl

LEVEL = 0.90
TOP_BAND = 10
MIN_BAND_CELLS = 50
WILSON_Z = 1.959963984540054
YEAR_PAIRS = ((2023, 2024), (2024, 2025))
FAMILIES = ('co_ownership', 'area_mix', 'text_pairs')
COUNTS = ('base_cells', 'testable_cells', 'recurring_cells')

SAFE_RUN_ID = re.compile('[A-Za-z0-9][A-Za-z0-9_-]*')
SAFE_PIN = re.compile('[0-9a-f]{64}')
CANONICAL = 'ita_300a_canonical.parquet'
# Each role in table order: its bundle root, the refusal of a wrong pin and the files read.
ROLES = {
    'establishment': (Path('derived/osha/establishment-targets'),
                      'establishment-target pin differs',
                      ('ita_establishment_links.parquet', 'ita_text_pairs.parquet',
                       'ita_text_pair_members.parquet', 'ita_co_ownership.parquet',
                       'co_ownership_support.parquet', 'inputs.json', 'report.json')),
    'area_mix': (Path('derived/targets'), 'area-mix pin differs',
                 ('ita_county_assignments.parquet', 'ita_area_mix.parquet', 'inputs.json',
                  'report.json')),
    'codes': (Path('derived/codes'), 'codes pin differs', (CANONICAL,)),
}


class Refused(Exception):
    '''An input that the pins do not authenticate. The message is a fixed reason.'''


@dataclass(frozen=True)
class Inputs:
    '''The authenticated files that the measurement reads.'''

    canonical: Path
    links: Path
    pairs: Path
    members: Path
    co_ownership: Path
    support: Path
    establishment_report: Path
    assignments: Path
    area_mix: Path
    area_mix_report: Path


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
    '''The bands of one family and year pair, from the lowest count up.

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


def family_minimum(minimums: list[int | None]) -> int | None:
    '''The largest year-pair minimum, or None when any year pair has none.'''
    if not minimums or any(minimum is None for minimum in minimums):
        return None
    return max(minimums)


def sha256(file: Path) -> str:
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_inventory(directory: Path, names: tuple[str, ...]) -> dict[str, str]:
    '''The `sha256` record of each named file, once each file matches it.

    Call it only after `outputs.json` matched its detached pin.
    '''
    inventory = json.loads((directory / 'outputs.json').read_text())
    records = {}
    for name in names:
        record = inventory.get(name) if isinstance(inventory, dict) else None
        expected = record.get('sha256') if isinstance(record, dict) else None
        file = directory / name
        if not file.is_file() or sha256(file) != expected:
            raise Refused('file differs from its inventory')
        records[name] = expected
    return records


def check_identity(establishment: Path, area_mix: Path, codes: tuple[str, str],
                   canonical_sha256: str) -> None:
    '''Refuse unless both `inputs.json` name the selected codes run and canonical table.'''
    run_id, pin = codes
    expected = {'path': f'derived/codes/{run_id}/{CANONICAL}', 'sha256': canonical_sha256}
    documents = [json.loads((directory / 'inputs.json').read_text())
                 for directory in (establishment, area_mix)]
    for inputs in documents:
        canonical = inputs.get('canonical') if isinstance(inputs, dict) else None
        if not isinstance(canonical, dict) or any(
                canonical.get(key) != value for key, value in expected.items()):
            raise Refused('inputs name another canonical table or codes run')
    selected = documents[0].get('codes')
    if not isinstance(selected, dict) or (
            selected.get('run_id'), selected.get('outputs_sha256')) != (run_id, pin):
        raise Refused('inputs name another canonical table or codes run')


def authenticate(data_dir: Path, establishment: tuple[str, str], area_mix: tuple[str, str],
                 codes: tuple[str, str]) -> Inputs:
    '''The pinned input files, once every pin, file record and cross-bundle name agrees.

    Each selection is `(run_id, outputs_sha256)`. The checks run in order: safe run IDs and
    pins, the three detached pins in table order, the record of every file read, then the
    canonical table and codes run that both `inputs.json` files name.
    '''
    selections = {'establishment': establishment, 'area_mix': area_mix, 'codes': codes}
    for run_id, pin in selections.values():
        if not (isinstance(run_id, str) and isinstance(pin, str)
                and SAFE_RUN_ID.fullmatch(run_id) and SAFE_PIN.fullmatch(pin)):
            raise Refused('unsafe run id or pin')
    directories = {}
    for role, (run_id, pin) in selections.items():
        root, reason, _names = ROLES[role]
        directory = data_dir / root / run_id
        outputs = directory / 'outputs.json'
        if not outputs.is_file() or sha256(outputs) != pin:
            raise Refused(reason)
        directories[role] = directory
    records = {role: check_inventory(directory, ROLES[role][2])
               for role, directory in directories.items()}
    check_identity(directories['establishment'], directories['area_mix'], codes,
                   records['codes'][CANONICAL])
    first, second = directories['establishment'], directories['area_mix']
    return Inputs(
        canonical=directories['codes'] / CANONICAL,
        links=first / 'ita_establishment_links.parquet',
        pairs=first / 'ita_text_pairs.parquet',
        members=first / 'ita_text_pair_members.parquet',
        co_ownership=first / 'ita_co_ownership.parquet',
        support=first / 'co_ownership_support.parquet',
        establishment_report=first / 'report.json',
        assignments=second / 'ita_county_assignments.parquet',
        area_mix=second / 'ita_area_mix.parquet',
        area_mix_report=second / 'report.json',
    )
