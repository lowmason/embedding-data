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
from embedding_data.target_contract import TARGET_KEY_COLUMNS, TARGET_SCHEMA, validate_targets

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


def _checked_aggregates(aggregates):
    cells, denominators = pl.collect_all([aggregates.cells, aggregates.denominators])
    for frame, keys in [(cells, PAIR_KEYS), (denominators, DENOMINATOR_KEYS)]:
        grain = [*keys, 'component_year', 'replicate']
        if frame.select(pl.struct(grain).is_duplicated().any()).item():
            raise ValueError('duplicate aggregate join keys')
        if frame.filter(pl.any_horizontal(pl.col(k).is_null() for k in grain)).height:
            raise ValueError('null aggregate join key')
        groups = frame.group_by(keys).agg(
            pl.struct('component_year', 'replicate').n_unique().alias('n'),
            pl.col('component_year').is_in([0, *aggregates.product.years]).all().alias('years'),
            pl.col('replicate').is_in(range(REPLICATE_COUNT + 1)).all().alias('replicates'))
        if groups.filter(pl.col('n').ne((len(aggregates.product.years) + 1)
                                       * (REPLICATE_COUNT + 1))
                         | ~pl.col('years') | ~pl.col('replicates')).height:
            raise ValueError('incomplete aggregate component/replicate membership')
    renamed = {name: 'denominator_' + name for name in denominators.columns
               if name not in [*DENOMINATOR_KEYS, 'component_year', 'replicate']}
    joined = cells.join(denominators.rename(renamed),
                        on=[*DENOMINATOR_KEYS, 'component_year', 'replicate'],
                        how='left', validate='m:1')
    if joined['denominator_n_unweighted'].null_count():
        raise ValueError('cell missing denominator aggregate')
    return joined, denominators


def _mass(row, prefix, product):
    with localcontext() as context:
        context.prec = 2 * DECIMAL_PRECISION
        exact = row.get(prefix + 'sum_exact')
        value = (Decimal(exact) / product.pool_divisor if exact is not None
                 else row[prefix + 'mass'] / product.pool_divisor)
        number = float(value)
    if not math.isfinite(number):
        raise ValueError('nonfinite aggregate mass')
    return number


def _stat_key(product, row, measure):
    return {'view': product.view, 'source': 'acs', 'family': product.family,
            **{key: row[key] for key in PAIR_KEYS}, 'measure': measure,
            'sample_set': product.sample_set, 'vintage': product.vintage,
            'universe': product.base_universe + ':' + product.evidence_policy}


def _replicate_rows(product, key, rows):
    result = []
    for row in rows:
        numerator = _mass(row, '', product)
        denominator = _mass(row, 'denominator_', product)
        total = key['measure'] == 'annual_average_total'
        value = numerator if total else numerator / denominator if denominator else None
        status = ('zero_denominator' if value is None else
                  'defined' if math.isfinite(value) else 'nonfinite_ratio')
        result.append({**key, 'product_id': product.product_id, 'replicate': row['replicate'],
                       'numerator_sum_exact': row.get('sum_exact'),
                       'denominator_sum_exact': row.get('denominator_sum_exact'),
                       'pool_divisor': product.pool_divisor, 'numerator': numerator,
                       'denominator': denominator,
                       'estimate': value if status == 'defined' else None,
                       'status': status, 'reason': None if status == 'defined' else status})
    return result


def _support_row(product, key, row, statuses, *, record_kind='cell'):
    canonical = product.view == 'canonical'
    return {**key, 'record_kind': record_kind, 'component_year': row['component_year'],
            'product_id': product.product_id, 'pool_divisor': product.pool_divisor,
            'n_unweighted': row['n_unweighted'],
            'denominator_n_unweighted': row['denominator_n_unweighted'],
            'cell_weight_sum_exact': row.get('sum_exact'),
            'denominator_weight_sum_exact': row.get('denominator_sum_exact'),
            'cell_mass': _mass(row, '', product),
            'denominator_mass': _mass(row, 'denominator_', product),
            'fractional_support_mass': row['fractional_support_mass'],
            'denominator_fractional_support_mass': row['denominator_fractional_support_mass'],
            'native_coverage_n': row.get('denominator_native_coverage_n') if canonical else None,
            'native_coverage_mass': (row['denominator_native_coverage_mass'] / product.pool_divisor
                                     if canonical else None),
            **statuses, 'support_semantics': 'annual_average_contribution',
            'flags': sorted(set(row['flags']) | {'size_gate_pending'})}


def _finalize_cell(product, rows):
    annual_full = [row for row in rows if row['replicate'] == 0]
    full = next(row for row in annual_full if row['component_year'] == 0)
    pooled_replicates = sorted((row for row in rows if row['component_year'] == 0
                                and row['replicate'] > 0), key=lambda r: r['replicate'])
    numerator = _mass(full, '', product)
    denominator = _mass(full, 'denominator_', product)
    if numerator < 0:
        raise ValueError('negative full cell mass')
    targets, support, replicates = [], [], []
    for measure in ('annual_average_total', 'forward_share'):
        key = _stat_key(product, full, measure)
        total = measure == 'annual_average_total'
        point = numerator if total else numerator / denominator if denominator > 0 else None
        if point is not None and not math.isfinite(point):
            raise ValueError('nonfinite full estimate')
        point_status = ('nonpositive_denominator' if point is None else
                        'defined' if numerator > 0 else 'no_positive_cell_mass')
        estimates = _replicate_rows(product, key, pooled_replicates)
        undefined = [r['replicate'] for r in estimates if r['status'] != 'defined']
        se = (replicate_se(point, tuple(r['estimate'] for r in estimates))
              if point is not None else None)
        se_status = ('undefined_point' if point is None else
                     'undefined_replicates' if undefined else 'defined')
        statuses = {'point_status': point_status,
                    'point_reason': None if point_status == 'defined' else point_status,
                    'se_status': se_status,
                    'se_reason': None if se_status == 'defined' else se_status,
                    'undefined_replicates': undefined}
        replicates.extend(estimates)
        support.extend(_support_row(product, key, row, statuses) for row in annual_full)
        if point_status == 'defined':
            targets.append({**{k: v for k, v in key.items() if k != 'view'},
                            'value': point, 'se': se,
                            'se_method': 'replicate' if se is not None else 'none',
                            'n_unweighted': full['n_unweighted'], 'n_weighted': numerator,
                            'flags': sorted(set(full['flags']) | {'size_gate_pending'})})
    return targets, support, replicates


def _denominator_status(product, denominators):
    result = []
    for group in denominators.filter(pl.col('replicate').eq(0)).partition_by(DENOMINATOR_KEYS):
        full = group.filter(pl.col('component_year').eq(0)).row(0, named=True)
        if _mass(full, '', product) > 0 or full['n_unweighted'] == 0:
            continue
        key = _stat_key(product, full | {'unit_b_type': None, 'unit_b': None}, 'forward_share')
        statuses = {'point_status': 'nonpositive_denominator',
                    'point_reason': 'nonpositive_denominator', 'se_status': 'undefined_point',
                    'se_reason': 'undefined_point', 'undefined_replicates': []}
        for denominator in group.filter(pl.col('n_unweighted').gt(0)).iter_rows(named=True):
            row = {**denominator,
                   **{'denominator_' + k: v for k, v in denominator.items()},
                   'n_unweighted': 0,
                   'sum_exact': None if product.view.startswith('allocated') else '0',
                   'mass': 0., 'fractional_support_mass': 0.}
            result.append(_support_row(product, key, row, statuses,
                                       record_kind='denominator_status'))
    return result


def estimate(aggregates: AggregateSet) -> dict[str, pl.LazyFrame]:
    '''Finalize paired 80-replicate vectors after exact native aggregation.'''
    joined, denominators = _checked_aggregates(aggregates)
    targets, support, replicates = [], [], []
    for group in joined.partition_by(PAIR_KEYS, maintain_order=True):
        t, s, r = _finalize_cell(aggregates.product, group.to_dicts())
        targets.extend(t)
        support.extend(s)
        replicates.extend(r)
    support.extend(_denominator_status(aggregates.product, denominators))
    frames = {
        'targets': pl.DataFrame(targets, schema=TARGET_SCHEMA).lazy().sort(TARGET_KEY_COLUMNS),
        'support': pl.DataFrame(support, schema=SUPPORT_SCHEMA).lazy().sort(
            [*STAT_KEY_COLUMNS, 'record_kind', 'component_year'], nulls_last=False),
        'replicates': pl.DataFrame(replicates, schema=REPLICATE_SCHEMA).lazy().sort(
            [*STAT_KEY_COLUMNS, 'replicate'], nulls_last=False),
    }
    validate_targets(frames['targets'])
    return frames
