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

from embedding_data import ita_co_ownership
from embedding_data.ita_area_mix import eligible_industry
from embedding_data.ita_establishment_links import CONFIRMED
from embedding_data.ita_establishment_records import KEY_SCHEMA, keyed_records

LEVEL = 0.90
TOP_BAND = 10
MIN_BAND_CELLS = 50
WILSON_Z = 1.959963984540054
YEAR_PAIRS = ((2023, 2024), (2024, 2025))
FAMILIES = ('co_ownership', 'area_mix', 'text_pairs')
COUNTS = ('base_cells', 'testable_cells', 'recurring_cells')
CELL = ['unit_a', 'unit_b']
EMPLOYER_YEAR = ['ein_key', 'year_filing_for']
YEAR_COUNTS = [f'j_{year}' for year in ita_co_ownership.YEARS]

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


def record_frame(canonical: pl.LazyFrame) -> pl.DataFrame:
    '''The 2023-2025 keyed records with their industry and employer eligibility.

    No title or index keys are given, so the copied-text flags are all false, and no rule
    reads them. `employer_eligible` is the co-ownership classification: a year in
    `ita_co_ownership.YEARS`, an industry that passes `eligible_industry()`, a known
    `ein_key` and an EIN that is not padded, with a null padded flag counted as padded.
    '''
    year = pl.col('year_filing_for').is_in(ita_co_ownership.YEARS)
    employer = (year.and_(eligible_industry())
                .and_(pl.col('ein_key').is_not_null())
                .and_(pl.col('flag_ein_padded').fill_null(True).not_()))
    return (
        keyed_records(canonical, pl.DataFrame(schema=KEY_SCHEMA))
        .filter(year)
        .select(
            'source_row', 'year_filing_for', 'naics_code', 'naics_2022_node_id', 'ein_key',
            industry_eligible=eligible_industry(),
            employer_eligible=employer,
        )
        .collect()
    )


def confirmed_links(links: pl.LazyFrame, records: pl.DataFrame) -> pl.DataFrame:
    '''One row per year-t source row with a confirmed link to year t + 1.

    A link row counts when its `(base_year, later_year)` is in `YEAR_PAIRS` and its
    `status` is in `CONFIRMED`. Every source row in its `base_rows` gets its `later_row`,
    so exact duplicates all count as linked. Refuse unless each `(base_year, source_row)`
    occurs once, each source row is a record of `base_year` and each later row is a record
    of `base_year + 1`.
    '''
    pairs = pl.DataFrame(YEAR_PAIRS, schema={'base_year': pl.Int64, 'later_year': pl.Int64},
                         orient='row')
    found = (
        links.join(pairs.lazy(), on=['base_year', 'later_year'], how='semi')
        .filter(pl.col('status').is_in(CONFIRMED))
        .select('base_year', pl.col('base_rows').alias('source_row'), 'later_row')
        .explode('source_row')
        .collect()
    )
    years = records.select('source_row', pl.col('year_filing_for').alias('base_year'))
    later = records.select(pl.col('source_row').alias('later_row'),
                           (pl.col('year_filing_for') - 1).alias('base_year'))
    if (found.select('base_year', 'source_row').is_duplicated().any()
            or found.join(years, on=['base_year', 'source_row'], how='anti').height
            or found.join(later, on=['base_year', 'later_row'], how='anti').height):
        raise Refused('link rows disagree with canonical rows')
    return found


def visible(links: pl.DataFrame, eligible_rows: pl.Series) -> pl.DataFrame:
    '''The linked year-t source rows whose `later_row` is in `eligible_rows`.'''
    return links.filter(pl.col('later_row').is_in(eligible_rows.implode())).select(
        'base_year', 'source_row')



def _industry_pairs(presence: pl.LazyFrame, keys: list[str]) -> pl.LazyFrame:
    '''Self-join presence rows on `keys` into ordered pairs of distinct industries.'''
    node = 'naics_2022_node_id'
    left = presence.rename({node: 'unit_a'})
    right = presence.rename({node: 'unit_b'})
    return left.join(right, on=keys, suffix='_b').filter(pl.col('unit_a').ne(pl.col('unit_b')))


def co_ownership_counts(records: pl.DataFrame) -> pl.DataFrame:
    '''The co-ownership `j_t` of each directed industry pair, as `ita_co_ownership` counts it.

    `j_t` counts the distinct `ein_key` values with both nodes among their
    `employer_eligible` year-t records. Records are deduplicated to `(ein_key, year, node)`
    before the self-join on `(ein_key, year)`, so record multiplicity adds nothing.
    '''
    year = pl.col('year_filing_for')
    presence = (
        records.lazy()
        .filter(pl.col('employer_eligible'))
        .select(*EMPLOYER_YEAR, 'naics_2022_node_id')
        .unique()
    )
    return (
        _industry_pairs(presence, EMPLOYER_YEAR)
        .group_by(CELL)
        .agg(**{f'j_{t}': year.eq(t).sum().cast(pl.UInt64) for t in ita_co_ownership.YEARS})
        .sort(CELL)
        .collect()
    )


def check_co_ownership(counts: pl.DataFrame, support: pl.DataFrame,
                       targets: pl.DataFrame) -> None:
    '''Refuse unless the recount equals the published support and target cells exactly.

    `counts` must equal the `unit_a`, `unit_b` and `j_*` columns of `support` row for row
    after sorting, and `targets` must hold the same `(unit_a, unit_b)` cells.
    '''
    published = support.select(*CELL, *YEAR_COUNTS).sort(CELL)
    recounted = counts.select(*CELL, *YEAR_COUNTS).sort(CELL)
    cells = targets.select(CELL).sort(CELL)
    if not (recounted.equals(published) and recounted.select(CELL).equals(cells)):
        raise Refused('co-ownership recount differs')


def co_ownership_cells(records: pl.DataFrame, links: pl.DataFrame,
                       base_year: int) -> pl.DataFrame:
    '''The co-ownership cells of one base year t, keyed by `unit_a` and `unit_b`.

    `base_count` is `j_t` and `recurs` is `j_{t+1} >= 1`, through any employer. A cell is
    testable when one of its EINs has year-t `employer_eligible` records at both nodes
    with a visible link: a confirmed link to an `employer_eligible` year t + 1 record.
    '''
    eligible = records.filter(pl.col('employer_eligible'))
    linked = visible(links, eligible['source_row']).filter(pl.col('base_year').eq(base_year))
    presence = (
        eligible.lazy()
        .filter(pl.col('year_filing_for').eq(base_year))
        .group_by('ein_key', 'naics_2022_node_id')
        .agg(linked=pl.col('source_row').is_in(linked['source_row'].implode()).any())
    )
    testable = (
        _industry_pairs(presence, ['ein_key'])
        .group_by(CELL)
        .agg(testable=pl.col('linked').and_(pl.col('linked_b')).any())
    )
    base, later = pl.col(f'j_{base_year}'), pl.col(f'j_{base_year + 1}')
    return (
        co_ownership_counts(records).lazy()
        .filter(base.ge(1))
        .join(testable, on=CELL, how='left', validate='1:1')
        .select(*CELL, base_count=base, testable=pl.col('testable').fill_null(False),
                recurs=later.ge(1))
        .sort(CELL)
        .collect()
    )
