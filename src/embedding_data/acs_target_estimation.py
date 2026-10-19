'''Exact native pooling and paired replicate uncertainty at aggregate cell grain.'''

import math
from dataclasses import dataclass
from decimal import Decimal, localcontext

import polars as pl

from embedding_data.acs_target_contract import (
    REPLICATE_SCHEMA,
    STAT_KEY_COLUMNS,
    SUPPORT_SCHEMA,
    Product,
)
from embedding_data.acs_target_membership import FamilyRows
from embedding_data.acs_target_weights import WEIGHT_NAMES
from embedding_data.target_contract import TARGET_KEY_COLUMNS, TARGET_SCHEMA

PAIR_KEYS = ['unit_a_type', 'unit_a', 'unit_b_type', 'unit_b']
DENOMINATOR_KEYS = ['unit_a_type', 'unit_a']
REPLICATE_COUNT = 80
DECIMAL_PRECISION = 38


@dataclass(frozen=True)
class AggregateSet:
    cells: pl.LazyFrame
    denominators: pl.LazyFrame
    diagnostics: pl.LazyFrame
    product: Product


def replicate_se(full: float, replicates: tuple[float | None, ...]) -> float | None:
    if len(replicates) != REPLICATE_COUNT:
        raise ValueError('exactly 80 replicates required')
    if not math.isfinite(full):
        raise ValueError('nonfinite full estimate')
    if any(value is not None and not math.isfinite(value) for value in replicates):
        raise ValueError('undefined replicate must carry an explicit status')
    if any(value is None for value in replicates):
        return None
    result = math.sqrt((4 / REPLICATE_COUNT) * math.fsum(
        (value - full) ** 2 for value in replicates))
    if not math.isfinite(result):
        raise ValueError('nonfinite standard error')
    return result


def _weight_scale(rows):
    schema = rows.members.collect_schema()
    if any(name not in schema or not isinstance(schema[name], pl.Decimal)
           for name in WEIGHT_NAMES):
        raise ValueError('exactly 81 finite Decimal estimator weights required')
    scale = max(schema[name].scale for name in WEIGHT_NAMES)
    if scale + (rows.product.pool_divisor == 2) > DECIMAL_PRECISION:
        raise ValueError('unsupported native precision for exact pooling division')
    summary = rows.members.select(
        pl.len().alias('n'),
        pl.any_horizontal(pl.col(name).is_null() for name in WEIGHT_NAMES).any().alias('null'),
        pl.col('YEAR').is_in(rows.product.years).not_().fill_null(True).any().alias('year'),
        *[pl.col(name).abs().max().alias(name) for name in WEIGHT_NAMES],
    ).collect().row(0, named=True)
    if summary['null'] or summary['year']:
        raise ValueError('null estimator weight or undeclared member year')
    with localcontext() as context:
        context.prec = 2 * DECIMAL_PRECISION
        limit = Decimal(10) ** (DECIMAL_PRECISION - scale)
        if any(summary[name] is not None and summary[name] * summary['n'] >= limit
               for name in WEIGHT_NAMES):
            raise ValueError('native Decimal aggregation overflow bound exceeded')
    return scale


def _native_groups(members, keys, product, scale):
    values = [pl.col(name).cast(pl.Decimal(DECIMAL_PRECISION, scale)).sum().alias(name)
              for name in WEIGHT_NAMES]
    values.extend([pl.len().cast(pl.UInt64).alias('n_unweighted'),
                   pl.col('flags').list.explode(keep_nulls=False, empty_as_null=False)
                   .unique().sort().alias('flags')])
    annual = members.group_by(*keys, 'YEAR').agg(values).rename({'YEAR': 'component_year'})
    pooled = members.group_by(keys).agg(values).with_columns(
        pl.lit(0, dtype=pl.Int64).alias('component_year'))
    wide = pl.concat([annual, pooled], how='diagonal')
    components = pl.LazyFrame({'component_year': [0, *product.years]},
                             schema={'component_year': pl.Int64})
    grid = wide.select(keys).unique().join(components, how='cross')
    wide = grid.join(wide, on=[*keys, 'component_year'], how='left', validate='1:1').with_columns(
        *[pl.col(name).fill_null(Decimal(0)) for name in WEIGHT_NAMES],
        pl.col('n_unweighted').fill_null(0),
        pl.col('flags').fill_null(pl.lit([], dtype=pl.List(pl.String))),
    )
    long = wide.unpivot(on=list(WEIGHT_NAMES), index=[*keys, 'component_year',
        'n_unweighted', 'flags'], variable_name='_weight', value_name='_sum')
    exact = pl.col('_sum').cast(pl.String).str.replace(r'(\.\d*?)0+$', '${1}').str.replace(
        r'\.$', '').replace('-0', '0')
    return long.with_columns(
        pl.when(pl.col('_weight').eq('PERWT')).then(pl.lit(0)).otherwise(
            pl.col('_weight').str.strip_prefix('REPWTP').cast(pl.UInt8, strict=False))
            .cast(pl.UInt8).alias('replicate'),
        exact.alias('sum_exact'),
        pl.col('n_unweighted').cast(pl.Float64).alias('fractional_support_mass'),
    ).drop('_weight', '_sum').sort([*keys, 'component_year', 'replicate'])


def aggregate_native(rows: FamilyRows) -> AggregateSet:
    '''Consume lazy members while their authenticated source context is still alive.'''
    if rows.product.pool_divisor not in (1, 2) or not rows.product.years:
        raise ValueError('unsupported declared pooling period')
    scale = _weight_scale(rows)
    cells, denominators = pl.collect_all([
        _native_groups(rows.members, PAIR_KEYS, rows.product, scale),
        _native_groups(rows.members, DENOMINATOR_KEYS, rows.product, scale),
    ])
    if cells.filter(pl.col('replicate').eq(0)).select(
            pl.col('sum_exact').cast(pl.Decimal(DECIMAL_PRECISION, scale)).lt(0).any()).item():
        raise ValueError('negative full cell mass')
    return AggregateSet(cells.lazy(), denominators.lazy(), rows.diagnostics.collect().lazy(),
                        rows.product)


def _reject_any(frame, expression, message):
    if frame.select(expression.any()).collect().item():
        raise ValueError(message)


def _checked_aggregates(aggregates):
    cells, denominators = aggregates.cells, aggregates.denominators
    for frame, keys in [(cells, PAIR_KEYS), (denominators, DENOMINATOR_KEYS)]:
        grain = [*keys, 'component_year', 'replicate']
        _reject_any(frame, pl.struct(grain).is_duplicated(), 'duplicate aggregate join keys')
        _reject_any(frame, pl.any_horizontal(pl.col(k).is_null() for k in grain),
                    'null aggregate join key')
        groups = frame.group_by(keys).agg(
            pl.struct('component_year', 'replicate').n_unique().alias('n'),
            pl.col('component_year').is_in([0, *aggregates.product.years]).all().alias('years'),
            pl.col('replicate').is_in(range(REPLICATE_COUNT + 1)).all().alias('replicates'))
        _reject_any(groups, pl.col('n').ne((len(aggregates.product.years) + 1)
                                         * (REPLICATE_COUNT + 1))
                    | ~pl.col('years') | ~pl.col('replicates'),
                    'incomplete aggregate component/replicate membership')
    renamed = {name: 'denominator_' + name for name in denominators.collect_schema()
               if name not in [*DENOMINATOR_KEYS, 'component_year', 'replicate']}
    joined = cells.join(denominators.rename(renamed),
                        on=[*DENOMINATOR_KEYS, 'component_year', 'replicate'],
                        how='left', validate='m:1')
    _reject_any(joined, pl.col('denominator_n_unweighted').is_null(),
                'cell missing denominator aggregate')
    return joined, denominators


def _mass_expression(schema, prefix, divisor):
    exact = prefix + 'sum_exact'
    mass = prefix + 'mass'
    raw = [pl.col(exact).cast(pl.Float64)] if exact in schema else []
    if mass in schema:
        raw.append(pl.col(mass))
    if not raw:
        raise ValueError('aggregate missing raw mass')
    return pl.coalesce(raw) / divisor


def _metadata(frame, product):
    return frame.with_columns(
        pl.lit(product.view).alias('view'), pl.lit('acs').alias('source'),
        pl.lit(product.family).alias('family'), pl.lit(product.sample_set).alias('sample_set'),
        pl.lit(product.vintage).alias('vintage'),
        pl.lit(product.base_universe + ':' + product.evidence_policy).alias('universe'),
        pl.lit(product.product_id).alias('product_id'),
        pl.lit(product.pool_divisor, dtype=pl.UInt8).alias('pool_divisor'),
    )


def _statistics(joined, product):
    schema = joined.collect_schema()
    masses = _metadata(joined, product).with_columns(
        _mass_expression(schema, '', product.pool_divisor).alias('cell_mass'),
        _mass_expression(schema, 'denominator_', product.pool_divisor).alias('denominator_mass'),
    )
    _reject_any(masses, pl.any_horizontal(
        pl.col(name).is_null() | ~pl.col(name).is_finite()
        for name in ('cell_mass', 'denominator_mass')), 'nonfinite aggregate mass')
    _reject_any(masses.filter(pl.col('replicate').eq(0)), pl.col('cell_mass').lt(0),
                'negative full cell mass')
    measures = []
    for measure in ('annual_average_total', 'forward_share'):
        total = measure == 'annual_average_total'
        numerator, denominator = pl.col('cell_mass'), pl.col('denominator_mass')
        point = numerator if total else pl.when(denominator.gt(0)).then(numerator / denominator)
        replicate = (numerator if total else
                     pl.when(denominator.ne(0)).then(numerator / denominator))
        measures.append(masses.with_columns(
            pl.lit(measure).alias('measure'), point.alias('_point'),
            replicate.alias('_replicate_estimate')))
    statistics = pl.concat(measures)
    _reject_any(statistics.filter(pl.col('replicate').eq(0)),
                pl.col('_point').is_not_null() & ~pl.col('_point').is_finite(),
                'nonfinite full estimate')
    return statistics


def _typed_projection(frame, schema):
    return frame.select(pl.col(name).cast(dtype) for name, dtype in schema.items())


def _replicate_frame(statistics):
    total = pl.col('measure').eq('annual_average_total')
    zero_denominator = ~total & pl.col('denominator_mass').eq(0)
    status = pl.when(zero_denominator).then(pl.lit('zero_denominator')).when(
        pl.col('_replicate_estimate').is_finite()).then(pl.lit('defined')).otherwise(
            pl.lit('nonfinite_ratio'))
    return statistics.filter(pl.col('component_year').eq(0) & pl.col('replicate').gt(0))\
        .with_columns(status.alias('status')).with_columns(
            pl.col('cell_mass').alias('numerator'),
            pl.col('denominator_mass').alias('denominator'),
            pl.col('sum_exact').alias('numerator_sum_exact'),
            pl.col('denominator_sum_exact'),
            pl.when(pl.col('status').eq('defined')).then(pl.col('_replicate_estimate'))
                .alias('estimate'),
            pl.when(pl.col('status').ne('defined')).then(pl.col('status')).alias('reason'))


def _se_from_vector(row):
    # Only this fixed 80-statistic vector crosses the Python finalization boundary.
    return (replicate_se(row['_point'], tuple(row['_values']))
            if row['_point'] is not None else None)


def _pooled_status(statistics, replicates):
    full = statistics.filter(pl.col('component_year').eq(0) & pl.col('replicate').eq(0))
    vectors = replicates.group_by(STAT_KEY_COLUMNS).agg(
        pl.col('estimate').sort_by('replicate').alias('_values'),
        pl.col('replicate').filter(pl.col('status').ne('defined')).sort()
            .alias('undefined_replicates'))
    full = full.join(vectors, on=STAT_KEY_COLUMNS, how='left', validate='1:1').with_columns(
        pl.struct('_point', '_values').map_elements(_se_from_vector, return_dtype=pl.Float64,
                                                   skip_nulls=False).alias('_se'),
        pl.when(pl.col('_point').is_null()).then(pl.lit('nonpositive_denominator'))
            .when(pl.col('cell_mass').gt(0)).then(pl.lit('defined'))
            .otherwise(pl.lit('no_positive_cell_mass')).alias('point_status'),
        pl.when(pl.col('_point').is_null()).then(pl.lit('undefined_point'))
            .when(pl.col('undefined_replicates').list.len().gt(0))
            .then(pl.lit('undefined_replicates')).otherwise(pl.lit('defined')).alias('se_status'),
    )
    return full.with_columns(
        pl.when(pl.col('point_status').ne('defined')).then(pl.col('point_status'))
            .alias('point_reason'),
        pl.when(pl.col('se_status').ne('defined')).then(pl.col('se_status')).alias('se_reason'))


def _support_metadata(frame, product):
    schema = frame.collect_schema()
    exact_fields = [name for name in ('sum_exact', 'denominator_sum_exact') if name not in schema]
    frame = frame.with_columns(pl.lit(None, dtype=pl.String).alias(name) for name in exact_fields)
    coverage_n = pl.lit(None, dtype=pl.UInt64)
    coverage_mass = pl.lit(None, dtype=pl.Float64)
    if product.view == 'canonical':
        coverage_n = pl.col('denominator_native_coverage_n')
        coverage_mass = pl.col('denominator_native_coverage_mass') / product.pool_divisor
    return frame.with_columns(
        pl.col('sum_exact').alias('cell_weight_sum_exact'),
        pl.col('denominator_sum_exact').alias('denominator_weight_sum_exact'),
        coverage_n.alias('native_coverage_n'), coverage_mass.alias('native_coverage_mass'),
        pl.lit('annual_average_contribution').alias('support_semantics'),
        pl.concat_list('flags', pl.lit(['size_gate_pending']))
            .list.unique().list.sort().alias('flags'))


def _denominator_status(product, denominators):
    schema = denominators.collect_schema()
    renamed = {name: 'denominator_' + name for name in schema
               if name not in [*DENOMINATOR_KEYS, 'component_year', 'replicate', 'flags']}
    full = denominators.filter(pl.col('component_year').eq(0) & pl.col('replicate').eq(0))
    bad_keys = full.filter(_mass_expression(schema, '', product.pool_divisor).le(0)
                           & pl.col('n_unweighted').gt(0)).select(DENOMINATOR_KEYS)
    annual = denominators.filter(pl.col('replicate').eq(0) & pl.col('n_unweighted').gt(0))
    frame = _metadata(annual.join(bad_keys, on=DENOMINATOR_KEYS, how='semi').rename(renamed),
                      product).with_columns(
        pl.lit(None, dtype=pl.String).alias('unit_b_type'),
        pl.lit(None, dtype=pl.String).alias('unit_b'), pl.lit('forward_share').alias('measure'),
        pl.lit('denominator_status').alias('record_kind'),
        pl.lit(0, dtype=pl.UInt64).alias('n_unweighted'),
        pl.lit(0.).alias('fractional_support_mass'), pl.lit(0.).alias('cell_mass'),
        pl.lit(None if product.view.startswith('allocated') else '0', dtype=pl.String)
            .alias('sum_exact'),
        pl.lit('nonpositive_denominator').alias('point_status'),
        pl.lit('nonpositive_denominator').alias('point_reason'),
        pl.lit('undefined_point').alias('se_status'), pl.lit('undefined_point').alias('se_reason'),
        pl.lit([], dtype=pl.List(pl.UInt8)).alias('undefined_replicates'))
    return frame.with_columns(_mass_expression(frame.collect_schema(), 'denominator_',
                                               product.pool_divisor).alias('denominator_mass'))


def estimate(aggregates: AggregateSet) -> dict[str, pl.LazyFrame]:
    '''Build lazy publication plans with only fixed-size SE vectors evaluated in Python.'''
    joined, denominators = _checked_aggregates(aggregates)
    schema = joined.collect_schema()
    joined = joined.with_columns(pl.lit(None, dtype=pl.String).alias(name) for name in
        ('sum_exact', 'denominator_sum_exact') if name not in schema)
    statistics = _statistics(joined, aggregates.product)
    replicates = _replicate_frame(statistics)
    pooled = _pooled_status(statistics, replicates)
    statuses = pooled.select(*STAT_KEY_COLUMNS, 'point_status', 'point_reason',
                             'se_status', 'se_reason', 'undefined_replicates')
    support = statistics.filter(pl.col('replicate').eq(0)).join(
        statuses, on=STAT_KEY_COLUMNS, how='left', validate='m:1').with_columns(
            pl.lit('cell').alias('record_kind'))
    support = pl.concat([
        _typed_projection(_support_metadata(support, aggregates.product), SUPPORT_SCHEMA),
        _typed_projection(_support_metadata(_denominator_status(aggregates.product, denominators),
                                            aggregates.product), SUPPORT_SCHEMA),
    ])
    targets = pooled.filter(pl.col('point_status').eq('defined')).with_columns(
        pl.col('_point').alias('value'), pl.col('_se').alias('se'),
        pl.when(pl.col('_se').is_not_null()).then(pl.lit('replicate')).otherwise(pl.lit('none'))
            .alias('se_method'), pl.col('cell_mass').alias('n_weighted'),
        pl.concat_list('flags', pl.lit(['size_gate_pending']))
            .list.unique().list.sort().alias('flags'))
    return {
        'targets': _typed_projection(targets, TARGET_SCHEMA).sort(TARGET_KEY_COLUMNS),
        'support': support.sort([*STAT_KEY_COLUMNS, 'record_kind', 'component_year'],
                                nulls_last=False),
        'replicates': _typed_projection(replicates, REPLICATE_SCHEMA).sort(
            [*STAT_KEY_COLUMNS, 'replicate'], nulls_last=False),
    }
