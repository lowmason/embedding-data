'''Measure the minimum headline earners for the ACS wage microdata (Stage 19).

A category meets the target in a year when the replicate-weight standard error of its weighted
mean `log_wage_2010` is at most `SE_TARGET`. Categories fall into bands by headline row count,
short bands merge upward, and the minimum is the lowest band start that passes at `LEVEL`
together with every higher band, taken as the larger of the two years.

The rule and its constants are in `specs/acs-wage-minimum-earners.md` ("The rule"). This script
imports only the standard library and Polars, and no `embedding_data` module.

Before any SE, the script authenticates the pinned Stage 17 bundle and checks the report against
the person rows. A failed check raises `Refused` with a fixed reason: no path, value or exception
text goes into it.
'''

import hashlib
import json
import math
import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import polars as pl

SE_TARGET = 0.05
LEVEL = 0.90
LEVEL_EXACT = Fraction('0.90')   # the float 0.90 is not 9/10, so a band compares against this
BAND_STARTS = (1, 50, 100, 200, 400, 800, 1600)
MIN_BAND_CATEGORIES = 10
REPLICATE_FACTOR = 4 / 80
REPLICATES = 80
YEARS = (2023, 2024)

REPLICATE_COLUMNS = tuple(f'REPWTP{r}' for r in range(1, REPLICATES + 1))
READ_SCHEMA = {
    'YEAR': pl.Int64,
    'INDNAICS': pl.String,
    'flag_headline': pl.Boolean,
    'log_wage_2010': pl.Float64,
    'PERWT': pl.Float64,
    **{name: pl.Int64 for name in REPLICATE_COLUMNS},
}

FEWER_THAN_TWO_ROWS = 'fewer_than_two_rows'
CONSTANT_WAGE = 'constant_wage'
DENOMINATOR_NOT_POSITIVE = 'replicate_denominator_not_positive'
UNDEFINED = (FEWER_THAN_TWO_ROWS, CONSTANT_WAGE, DENOMINATOR_NOT_POSITIVE)

BUNDLES = Path('derived/acs/wage-microdata')
OUTPUTS = 'outputs.json'
REPORT = 'report.json'
PERSONS = 'acs_wage_persons.parquet'
RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')
PIN = re.compile(r'[0-9a-f]{64}')

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


def category_se(rows: pl.DataFrame) -> tuple[float | None, str | None]:
    '''The replicate-weight SE of one category-year's mean wage, or the reason it is undefined.

    `rows` holds that category-year's headline rows. `PERWT` is positive in every row, which the
    bundle checks guarantee before any SE is computed. Each weighted sum adds the elementwise
    products with `math.fsum`, which is correctly rounded and so does not depend on row order.
    The replicate weights are integers, so their denominators are exact.
    '''
    if rows.height < 2:
        return None, FEWER_THAN_TWO_ROWS
    wages = rows['log_wage_2010']
    if wages.min() == wages.max():
        return None, CONSTANT_WAGE
    denominators = rows.select(REPLICATE_COLUMNS).sum().row(0)
    if any(denominator <= 0 for denominator in denominators):
        return None, DENOMINATOR_NOT_POSITIVE
    products = rows.select(
        (pl.col(name) * pl.col('log_wage_2010')).alias(name)
        for name in ('PERWT', *REPLICATE_COLUMNS))
    theta = math.fsum(products['PERWT'].to_list()) / math.fsum(rows['PERWT'].to_list())
    thetas = (math.fsum(products[name].to_list()) / denominator
              for name, denominator in zip(REPLICATE_COLUMNS, denominators))
    squares = math.fsum((theta_r - theta) ** 2 for theta_r in thetas)
    return math.sqrt(REPLICATE_FACTOR * squares), None


def meets_target(se: float | None) -> bool:
    return se is not None and se <= SE_TARGET


def bands(records: list[dict]) -> list[dict]:
    '''One year's bands over its category records, short bands merged into the next higher one.

    A record sits in the band with the largest start not above its `headline_rows`. A band below
    the top with fewer than `MIN_BAND_CATEGORIES` categories carries its counts into the next
    band, and a merged band keeps its lowest start. The top band stays however few it holds.
    '''
    raw = {start: [0, 0] for start in BAND_STARTS}
    for record in records:
        start = max(lowest for lowest in BAND_STARTS if lowest <= record['headline_rows'])
        raw[start][0] += 1
        raw[start][1] += int(record['meets_se_target'])
    merged = []
    first, categories, meeting = None, 0, 0
    for index, start in enumerate(BAND_STARTS):
        first = start if first is None else first
        categories += raw[start][0]
        meeting += raw[start][1]
        top = index == len(BAND_STARTS) - 1
        if top or categories >= MIN_BAND_CATEGORIES:
            next_start = None if top else BAND_STARTS[index + 1]
            merged.append(_band(first, next_start, categories, meeting))
            first, categories, meeting = None, 0, 0
    return merged


def _band(start: int, next_start: int | None, categories: int, meeting: int) -> dict:
    return {
        'start': start,
        'next_start': next_start,
        'categories': categories,
        'meeting': meeting,
        'share': meeting / categories if categories else None,
        'passes': categories > 0 and Fraction(meeting, categories) >= LEVEL_EXACT,
    }


def year_minimum(bands: list[dict]) -> int | None:
    '''The start of the lowest band in the run of passing bands that ends at the top band.'''
    minimum = None
    for band in reversed(bands):
        if not band['passes']:
            break
        minimum = band['start']
    return minimum


def overall_minimum(minimums: list[int | None]) -> int | None:
    '''The largest year minimum, or None when any year has none.'''
    if any(minimum is None for minimum in minimums):
        return None
    return max(minimums)


class Refused(Exception):
    '''An input that the pins do not authenticate, or a report that the rows do not match.

    The message is a fixed reason.
    '''


@dataclass(frozen=True)
class Inputs:
    '''The two files of the pinned run that the script reads, with the hashes that matched.'''

    report: Path
    persons: Path
    outputs_sha256: str
    report_sha256: str
    persons_sha256: str


def sha256(file: Path) -> str:
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory_of(content: bytes) -> dict:
    '''The `outputs.json` object, or an empty one when the bytes are not a JSON object.

    An empty inventory holds no record, so the check on the report record refuses it.
    '''
    try:
        inventory = json.loads(content)
    except ValueError:
        return {}
    return inventory if isinstance(inventory, dict) else {}


def recorded_file(directory: Path, inventory: dict, name: str, reason: str) -> tuple[Path, str]:
    '''One file of the run and its SHA-256, once both hash and size match the inventory.'''
    file = directory / name
    record = inventory.get(name)
    if not isinstance(record, dict) or not file.is_file():
        raise Refused(reason)
    digest = sha256(file)
    if digest != record.get('sha256') or file.stat().st_size != record.get('size'):
        raise Refused(reason)
    return file, digest


def authenticate(data_dir: Path, run_id: str, pin: str) -> Inputs:
    '''Check the detached pin, then the report and the person table against the inventory.'''
    if not RUN_ID.fullmatch(run_id) or not PIN.fullmatch(pin):
        raise Refused(UNSAFE)
    directory = data_dir / BUNDLES / run_id
    outputs = directory / OUTPUTS
    if not outputs.is_file():
        raise Refused(PIN_DIFFERS)
    content = outputs.read_bytes()
    if hashlib.sha256(content).hexdigest() != pin:
        raise Refused(PIN_DIFFERS)
    inventory = inventory_of(content)
    report, report_sha256 = recorded_file(directory, inventory, REPORT, REPORT_DIFFERS)
    persons, persons_sha256 = recorded_file(directory, inventory, PERSONS, PERSONS_DIFFER)
    return Inputs(report, persons, pin, report_sha256, persons_sha256)


def _is_integer(value: object) -> bool:
    return type(value) is int


def _is_entry(entry: object) -> bool:
    return (isinstance(entry, dict) and isinstance(entry.get('INDNAICS'), str)
            and _is_integer(entry.get('YEAR')) and _is_integer(entry.get('headline_rows'))
            and entry['headline_rows'] >= 0)


def load_report(file: Path) -> dict:
    '''The report, once its shape and its years are right.

    Shape: a list `categories` of entries with a string `INDNAICS`, an integer `YEAR` and a
    non-negative integer `headline_rows`, no `(INDNAICS, YEAR)` key twice, and an object
    `headline_categories` of integers. Years: `headline_categories` has exactly the keys of
    `YEARS`, and no entry names another year.
    '''
    try:
        report = json.loads(file.read_text(encoding='utf-8'))
    except ValueError:
        raise Refused(MALFORMED) from None
    categories = report.get('categories') if isinstance(report, dict) else None
    totals = report.get('headline_categories') if isinstance(report, dict) else None
    if not isinstance(categories, list) or not isinstance(totals, dict):
        raise Refused(MALFORMED)
    if not all(_is_entry(entry) for entry in categories) or not all(
            _is_integer(count) for count in totals.values()):
        raise Refused(MALFORMED)
    keys = {(entry['INDNAICS'], entry['YEAR']) for entry in categories}
    if len(keys) != len(categories):
        raise Refused(MALFORMED)
    if set(totals) != {str(year) for year in YEARS} or any(
            year not in YEARS for _, year in keys):
        raise Refused(YEARS_DIFFER)
    return report


def headline_frame(persons: Path) -> pl.DataFrame:
    '''The headline rows of the person table, read as the `READ_SCHEMA` columns only.

    Each of those columns must be in the table with exactly its type. Other columns are ignored
    and never read.
    '''
    table = pl.scan_parquet(persons)
    schema = table.collect_schema()
    if any(schema.get(name) != dtype for name, dtype in READ_SCHEMA.items()):
        raise Refused(COLUMNS_DIFFER)
    return table.select(list(READ_SCHEMA)).filter(pl.col('flag_headline')).collect()


def self_check(report: dict, headline: pl.DataFrame) -> None:
    '''Check the report against the headline rows, before any SE.

    The recount of `(INDNAICS, YEAR, headline_rows)` must equal, as a set, the report entries
    with headline rows. The categories with headline rows must number `headline_categories` in
    each year. Every headline row needs a finite wage and a positive weight, and a null is
    neither. Keys keep the delivered `INDNAICS` strings, with their space padding.
    '''
    counted = headline.group_by('INDNAICS', 'YEAR').agg(pl.len().alias('rows'))
    recount = set(zip(counted['INDNAICS'], counted['YEAR'], counted['rows'], strict=True))
    recorded = {(entry['INDNAICS'], entry['YEAR'], entry['headline_rows'])
                for entry in report['categories'] if entry['headline_rows'] > 0}
    if recount != recorded:
        raise Refused(RECOUNT_DIFFERS)
    for year in YEARS:
        found = sum(1 for _, found_year, _ in recount if found_year == year)
        if found != report['headline_categories'][str(year)]:
            raise Refused(COUNT_DIFFERS)
    usable = (pl.col('log_wage_2010').is_finite() & (pl.col('PERWT') > 0)
              & pl.col('PERWT').is_not_nan()).fill_null(False)
    if not headline.select(usable.all()).item():
        raise Refused(BAD_ROW)
