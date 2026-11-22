'''Measure the minimum headline earners for the ACS wage microdata (Stage 19).

A category meets the target in a year when the replicate-weight standard error of its weighted
mean `log_wage_2010` is at most `SE_TARGET`. Categories fall into bands by headline row count,
short bands merge upward, and the minimum is the lowest band start that passes at `LEVEL`
together with every higher band, taken as the larger of the two years.

The rule and its constants are in `specs/acs-wage-minimum-earners.md` ("The rule"). This script
imports only the standard library and Polars, and no `embedding_data` module.
'''

import math
from fractions import Fraction

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
