'''Totals, forward shares and their standard errors for the CPS job-change flows.

A cell is an origin category `unit_a` and a destination category `unit_b`. `S` is the exact
Decimal sum of the weights of a cell's records, over every period. The total is
`float(S) / k`, and the forward share is the cell total over its origin total, in Float64
(SD5). So a share is the ratio of pooled totals, never a mean of period shares.

Each replicate recomputes both statistics with its own weights: the monthly link weight times
the household's draw count in that bootstrap replicate (SD4), or `REPWTP1`-`REPWTP160` for
ASEC. Every observed cell has a row in every replicate, zero where the replicate misses it.
A cell with no record is absent.

A nonpositive full-sample origin total publishes no share. A defined share with a nonpositive
replicate origin total keeps its point with a null SE. Each case gives one `undefined_share`
support row for each cell of the origin, with period `all` and the cell's undivided
full-sample mass.
'''

import math
import random
from collections import Counter
from dataclasses import dataclass

import polars as pl

MONTHLY_K = 18
ASEC_K = 2
BOOTSTRAP_B = 200
ASEC_R = 160
BOOTSTRAP_SEED = 20261123
MONTHLY_PRODUCTS = ('monthly_ee', 'monthly_ue')
ASEC_PRODUCTS = ('asec_retro',)
DIMENSIONS = ('industry', 'occupation')
# The unnumbered `REPWTP` is an availability helper, never a replicate.
REPLICATE_WEIGHTS = tuple(f'rep{number}' for number in range(1, ASEC_R + 1))
ALL_PERIODS = 'all'
VARIANT_COLUMNS = ('product', 'dimension', 'policy')
CELL = ['unit_a', 'unit_b']

TARGETS_SCHEMA = {
    'product': pl.String, 'dimension': pl.String, 'policy': pl.String,
    'unit_a': pl.String, 'unit_b': pl.String, 'measure': pl.String,
    'value': pl.Float64, 'se': pl.Float64, 'se_method': pl.String,
    'n_unweighted': pl.UInt64, 'n_weighted': pl.Float64,
}
SUPPORT_SCHEMA = {
    'product': pl.String, 'dimension': pl.String, 'policy': pl.String, 'kind': pl.String,
    'unit_a': pl.String, 'unit_b': pl.String, 'period': pl.String,
    'n_unweighted': pl.UInt64, 'mass': pl.Float64, 'reason': pl.String,
    'replicates': pl.List(pl.UInt16),
}
REPLICATES_SCHEMA = {
    'product': pl.String, 'dimension': pl.String, 'policy': pl.String,
    'unit_a': pl.String, 'unit_b': pl.String, 'replicate': pl.UInt16,
    'numerator': pl.Float64, 'denominator': pl.Float64, 'estimate': pl.Float64,
    'status': pl.String,
}
DRAWS_SCHEMA = {'replicate': pl.UInt16, 'CPSID': pl.Int64, 'draws': pl.UInt32}


@dataclass(frozen=True)
class Variant:
    product: str
    dimension: str
    policy: str


@dataclass(frozen=True)
class Estimates:
    targets: pl.DataFrame
    support: pl.DataFrame
    replicates: pl.DataFrame


def bootstrap_se(replicates: list[float | None]) -> float | None:
    '''The standard deviation of the replicate statistics, divisor B - 1 (SD5).

    B is the length of the list. Any undefined replicate leaves the SE undefined.
    '''
    count = len(replicates)
    if count < 2:
        raise ValueError('a bootstrap SE needs at least two replicates')
    if any(value is None for value in replicates):
        return None
    mean = math.fsum(replicates) / count
    return math.sqrt(math.fsum((value - mean) ** 2 for value in replicates) / (count - 1))


def replicate_se(point: float, replicates: list[float | None]) -> float | None:
    '''The successive-difference SE over `REPWTP1`-`REPWTP160` (SD5).

    Any undefined replicate leaves the SE undefined.
    '''
    if len(replicates) != ASEC_R:
        raise ValueError('an ASEC SE needs exactly 160 replicates')
    if any(value is None for value in replicates):
        return None
    return math.sqrt((4 / ASEC_R) * math.fsum((value - point) ** 2 for value in replicates))


def household_draws(households: list[int], *, seed: int = BOOTSTRAP_SEED,
                    replicates: int = BOOTSTRAP_B) -> pl.DataFrame:
    '''Draw the households with replacement, once for each replicate, from one generator (SD4).

    Replicate `r` is the `r`-th `choices(range(H), k=H)` of one fresh `random.Random(seed)`,
    counted per index. Every household has a row in every replicate, with 0 draws where the
    replicate missed it. Rows are sorted by replicate, then household.
    '''
    if households != sorted(set(households)):
        raise ValueError('bootstrap households must be sorted and distinct')
    size = len(households)
    rng = random.Random(seed)
    numbers, counts = [], []
    for replicate in range(1, replicates + 1):
        drawn = Counter(rng.choices(range(size), k=size))
        numbers.extend([replicate] * size)
        counts.extend(drawn[index] for index in range(size))
    return pl.DataFrame({'replicate': numbers, 'CPSID': households * replicates,
                         'draws': counts}, schema=DRAWS_SCHEMA)


def _check_variant(variant: Variant, products: tuple[str, ...],
                   policies: tuple[str, ...]) -> None:
    if (variant.product not in products or variant.dimension not in DIMENSIONS
            or variant.policy not in policies):
        raise ValueError('unknown estimation variant for this product')


def _check_records(records: pl.DataFrame, *, ids: tuple[str, ...],
                   weights: tuple[str, ...]) -> None:
    '''Refuse a frame without exactly the estimation columns and types, or with a null.'''
    schema = records.schema
    strings = ('unit_a', 'unit_b', 'period')
    if (set(schema) != {*strings, *ids, *weights}
            or any(schema[name] != pl.String for name in strings)
            or any(schema[name] != pl.Int64 for name in ids)
            or any(not schema[name].is_decimal() for name in weights)):
        raise ValueError('records must have exactly the estimation columns and types')
    if records.null_count().sum_horizontal().item():
        raise ValueError('records hold a null value')


def _check_draws(draws: pl.DataFrame, records: pl.DataFrame) -> None:
    '''Refuse draws that miss a record household or lack a replicate 1..B exactly once.'''
    expected = list(range(1, BOOTSTRAP_B + 1))
    numbers = draws.group_by('CPSID').agg(pl.col('replicate').sort())
    if any(replicates != expected for replicates in numbers['replicate'].to_list()):
        raise ValueError('draws must hold each household once in every replicate')
    if not records.join(numbers, on='CPSID', how='anti').is_empty():
        raise ValueError('draws miss a record household')


def _over_k(sums: pl.Series, k: int) -> pl.Series:
    '''Publish exact Decimal sums as `float(S) / k`, with Python's division (SD5).

    The Decimal to Float64 cast is `float(S)`. Polars divides a column by a scalar through
    its reciprocal, which can differ from `float(S) / k` in the last bit, so the division by k
    runs in Python.
    '''
    return pl.Series([value / k for value in sums.cast(pl.Float64).to_list()],
                     dtype=pl.Float64)


def _replicate_sums(weighted: pl.DataFrame, k: int) -> pl.DataFrame:
    '''Sum one replicate weight per row into cell and origin totals, each divided by k.'''
    cells = weighted.group_by(*CELL, 'replicate').agg(pl.col('weight').sum().alias('_cell'))
    origins = weighted.group_by('unit_a', 'replicate').agg(
        pl.col('weight').sum().alias('_origin'))
    sums = cells.join(origins, on=['unit_a', 'replicate'], how='left', validate='m:1')
    return sums.select(*CELL, 'replicate').with_columns(
        _over_k(sums['_cell'], k).alias('numerator'),
        _over_k(sums['_origin'], k).alias('denominator'))


def _replicate_rows(sums: pl.DataFrame) -> pl.DataFrame:
    positive = pl.col('denominator').gt(0)
    return sums.with_columns(
        pl.when(positive).then(pl.col('numerator') / pl.col('denominator')).alias('estimate'),
        pl.when(positive).then(pl.lit('defined')).otherwise(pl.lit('denominator_nonpositive'))
        .alias('status'))


def _support_counts() -> list[pl.Expr]:
    return [pl.col('weight').gt(0).sum().cast(pl.UInt64).alias('n_unweighted'),
            pl.col('weight').sum().alias('_sum')]


def _full_sample(records: pl.DataFrame, k: int) -> pl.DataFrame:
    '''One row per observed cell with its count, mass, total and (when defined) share.'''
    cells = records.group_by(CELL).agg(*_support_counts())
    origins = records.group_by('unit_a').agg(pl.col('weight').sum().alias('_origin'))
    cells = cells.join(origins, on='unit_a', how='left', validate='m:1')
    return cells.with_columns(
        pl.col('_sum').cast(pl.Float64).alias('mass'), _over_k(cells['_sum'], k).alias('total'),
        _over_k(cells['_origin'], k).alias('_origin_total'),
        pl.col('_origin').gt(0).alias('defined'),
    ).with_columns(pl.when('defined').then(pl.col('total') / pl.col('_origin_total'))
                   .alias('share'))


def _period_support(records: pl.DataFrame) -> pl.DataFrame:
    cells = records.group_by(*CELL, 'period').agg(*_support_counts()).with_columns(
        pl.lit('cell').alias('kind'))
    origins = records.group_by('unit_a', 'period').agg(*_support_counts()).with_columns(
        pl.lit('denominator').alias('kind'), pl.lit(None, dtype=pl.String).alias('unit_b'))
    return pl.concat([frame.select(
        'kind', *CELL, 'period', 'n_unweighted', pl.col('_sum').cast(pl.Float64).alias('mass'),
        pl.lit(None, dtype=pl.String).alias('reason'),
        pl.lit(None, dtype=pl.List(pl.UInt16)).alias('replicates')) for frame in (cells, origins)])


def _standard_error(method: str, point: float, values: list[float | None]) -> float | None:
    return bootstrap_se(values) if method == 'bootstrap' else replicate_se(point, values)


def _labeled(frame: pl.DataFrame, variant: Variant, schema: dict) -> pl.DataFrame:
    labels = [pl.lit(getattr(variant, name), dtype=pl.String).alias(name)
              for name in VARIANT_COLUMNS]
    return frame.with_columns(labels).select(
        pl.col(name).cast(dtype) for name, dtype in schema.items())


def _estimate(records: pl.DataFrame, variant: Variant, k: int, sums: pl.DataFrame,
              method: str) -> Estimates:
    '''Publish the totals, shares, support and replicates of one variant.'''
    replicates = _replicate_rows(sums)
    vectors = replicates.group_by(CELL).agg(
        pl.col('numerator').sort_by('replicate').alias('_numerators'),
        pl.col('estimate').sort_by('replicate').alias('_estimates'),
        pl.col('replicate').filter(pl.col('status').ne('defined')).sort().alias('_undefined'))
    cells = _full_sample(records, k).join(vectors, on=CELL, how='left', validate='1:1')
    targets, undefined = [], []
    for cell in cells.iter_rows(named=True):
        key, support = (cell['unit_a'], cell['unit_b']), (cell['n_unweighted'], cell['total'])
        targets.append((*key, 'average_total', cell['total'],
                        _standard_error(method, cell['total'], cell['_numerators']), *support))
        if not cell['defined']:
            undefined.append((*key, cell['n_unweighted'], cell['mass'],
                              'nonpositive_denominator', None))
            continue
        targets.append((*key, 'forward_share', cell['share'],
                        _standard_error(method, cell['share'], cell['_estimates']), *support))
        if cell['_undefined']:
            undefined.append((*key, cell['n_unweighted'], cell['mass'],
                              'replicate_share_undefined', cell['_undefined']))
    targets = pl.DataFrame(targets, orient='row', schema={
        'unit_a': pl.String, 'unit_b': pl.String, 'measure': pl.String, 'value': pl.Float64,
        'se': pl.Float64, 'n_unweighted': pl.UInt64, 'n_weighted': pl.Float64,
    }).with_columns(pl.when(pl.col('se').is_not_null()).then(pl.lit(method))
                    .otherwise(pl.lit('none')).alias('se_method'))
    undefined = pl.DataFrame(undefined, orient='row', schema={
        'unit_a': pl.String, 'unit_b': pl.String, 'n_unweighted': pl.UInt64,
        'mass': pl.Float64, 'reason': pl.String, 'replicates': pl.List(pl.UInt16),
    }).with_columns(pl.lit('undefined_share').alias('kind'),
                    pl.lit(ALL_PERIODS).alias('period'))
    support = pl.concat([_period_support(records), undefined], how='diagonal')
    return Estimates(
        targets=_labeled(targets, variant, TARGETS_SCHEMA).sort(
            [*VARIANT_COLUMNS, *CELL, 'measure']),
        support=_labeled(support, variant, SUPPORT_SCHEMA).sort(
            list(SUPPORT_SCHEMA), nulls_last=False),
        replicates=_labeled(replicates, variant, REPLICATES_SCHEMA).sort(
            [*VARIANT_COLUMNS, *CELL, 'replicate']))


def estimate_monthly(records: pl.DataFrame, variant: Variant, draws: pl.DataFrame) -> Estimates:
    '''Estimate one monthly variant with the product's household bootstrap.

    `records` holds the variant's eligible links: `CPSID`, `unit_a`, `unit_b`, `period` and
    the Decimal `weight`. `draws` comes from `household_draws` over the product's households,
    so every variant of the product shares it.
    '''
    _check_variant(variant, MONTHLY_PRODUCTS, ('strict', 'sensitivity'))
    _check_records(records, ids=('CPSID',), weights=('weight',))
    _check_draws(draws, records)
    weighted = records.join(draws, on='CPSID', how='inner').with_columns(
        (pl.col('weight') * pl.col('draws')).alias('weight'))
    return _estimate(records, variant, MONTHLY_K, _replicate_sums(weighted, MONTHLY_K),
                     'bootstrap')


def estimate_asec(records: pl.DataFrame, variant: Variant) -> Estimates:
    '''Estimate one ASEC variant with the 160 successive-difference replicates.

    `records` holds the variant's eligible persons: `unit_a`, `unit_b`, `period`, the Decimal
    `weight` (`ASECWT`) and the Decimal `rep1`-`rep160` (`REPWTP1`-`REPWTP160`).
    '''
    _check_variant(variant, ASEC_PRODUCTS, ('sensitivity',))
    _check_records(records, ids=(), weights=('weight', *REPLICATE_WEIGHTS))
    scale = max(records.schema[name].scale for name in REPLICATE_WEIGHTS)
    weighted = records.select(
        *CELL, *(pl.col(name).cast(pl.Decimal(38, scale)) for name in REPLICATE_WEIGHTS),
    ).unpivot(on=list(REPLICATE_WEIGHTS), index=CELL, variable_name='replicate',
              value_name='weight').with_columns(
        pl.col('replicate').str.strip_prefix('rep').cast(pl.UInt16))
    return _estimate(records, variant, ASEC_K, _replicate_sums(weighted, ASEC_K), 'replicate')
