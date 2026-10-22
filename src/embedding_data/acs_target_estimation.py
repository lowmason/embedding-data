'''Exact native pooling and paired replicate uncertainty at aggregate cell grain.'''

import json
import math
import re
import shutil
from contextlib import ExitStack
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path

import polars as pl

from embedding_data.acs_mapping_io import safe_path
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
_ESTIMATE_DESCRIPTOR_BYTES = 64 * 1024


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


def _native_wide_groups(members, keys, scale):
    values = [pl.col(name).cast(pl.Decimal(DECIMAL_PRECISION, scale)).sum().alias(name)
              for name in WEIGHT_NAMES]
    values.extend([pl.len().cast(pl.UInt64).alias('n_unweighted'),
                   pl.col('flags').list.explode(keep_nulls=False, empty_as_null=False)
                   .unique().sort().alias('flags')])
    annual = members.group_by(*keys, 'YEAR').agg(values).rename({'YEAR': 'component_year'})
    pooled = members.group_by(keys).agg(values).with_columns(
        pl.lit(0, dtype=pl.Int64).alias('component_year'))
    return annual, pooled


def _native_long_groups(wide, keys, product):
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


def _native_groups(members, keys, product, scale):
    annual, pooled = _native_wide_groups(members, keys, scale)
    return _native_long_groups(pl.concat([annual, pooled], how='diagonal'), keys, product)


def _sink_native_aggregate(frame, destination):
    safe_path(destination)
    with destination.open('xb') as stream:
        frame.sink_parquet(stream)


def _native_wide_schema(keys, scale):
    return {**{key: pl.String for key in keys}, 'component_year': pl.Int64,
            **{name: pl.Decimal(DECIMAL_PRECISION, scale) for name in WEIGHT_NAMES},
            'n_unweighted': pl.UInt64, 'flags': pl.List(pl.String)}


def _spill_native_long(wide, keys, product, directory, label, batch_size, scale,
                       coverage=None):
    registry_path = directory / f'{label}-keys.parquet'
    _sink_native_aggregate(wide.select(keys).unique().sort(keys), registry_path)
    registry = pl.scan_parquet(registry_path)
    _reject_any(registry, pl.any_horizontal(pl.col(key).is_null() for key in keys),
                'null aggregate join key')
    paths = []
    offset = 0
    while True:
        batch = registry.slice(offset, batch_size).collect()
        if batch.is_empty() and paths:
            break
        selected = wide.join(batch.lazy(), on=keys, how='semi')
        long = _native_long_groups(selected, keys, product)
        if coverage is not None:
            long = long.join(coverage, on=[*keys, 'component_year'], how='left',
                             validate='m:1', maintain_order='left')
        path = directory / f'{label}-long-{len(paths):08d}.parquet'
        _sink_native_aggregate(long, path)
        if label == 'cells':
            _reject_any(pl.scan_parquet(path).filter(pl.col('replicate').eq(0)),
                        pl.col('sum_exact').cast(pl.Decimal(DECIMAL_PRECISION, scale)).lt(0),
                        'negative full cell mass')
        paths.append(path)
        if batch.height < batch_size:
            break
        offset += batch_size
    return pl.concat([pl.scan_parquet(path) for path in paths])


def _aggregate_native_spilled(rows: FamilyRows, scratch: Path, *,
                              batch_size: int = 128) -> AggregateSet:
    '''Persist aggregate-only shards; returned scans live until caller removes scratch.'''
    if rows.product.pool_divisor not in (1, 2) or not rows.product.years:
        raise ValueError('unsupported declared pooling period')
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
        raise ValueError('batch_size must be a positive integer')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', rows.product.product_id):
        raise ValueError('unsafe native aggregate product ID')
    scratch = Path(scratch)
    safe_path(scratch)
    if not scratch.is_dir():
        raise ValueError('native aggregate scratch must be an existing directory')
    directory = scratch / ('native-' + rows.product.product_id)
    safe_path(directory)
    directory.mkdir()
    try:
        scale = _weight_scale(rows)
        wide_frames = {}
        for label, keys in [('cells', PAIR_KEYS), ('denominators', DENOMINATOR_KEYS)]:
            paths = []
            schema = _native_wide_schema(keys, scale)
            for component, frame in zip(('annual', 'pooled'),
                    _native_wide_groups(rows.members, keys, scale), strict=True):
                path = directory / f'{label}-{component}.parquet'
                _sink_native_aggregate(_typed_projection(frame, schema), path)
                if list(pl.scan_parquet(path).collect_schema().items()) != list(schema.items()):
                    raise ValueError('native wide aggregate schema mismatch')
                paths.append(path)
            wide_frames[label] = pl.concat([pl.scan_parquet(path) for path in paths])
        coverage = None
        if rows.product.view == 'canonical':
            coverage_path = directory / 'coverage.parquet'
            _sink_native_aggregate(rows.members.select(
                *DENOMINATOR_KEYS, '_canonical_native_coverage').unique().explode(
                    '_canonical_native_coverage').unnest('_canonical_native_coverage'),
                coverage_path)
            coverage = pl.scan_parquet(coverage_path)
        diagnostics_path = directory / 'diagnostics.parquet'
        _sink_native_aggregate(rows.diagnostics, diagnostics_path)
        cells = _spill_native_long(wide_frames['cells'], PAIR_KEYS, rows.product, directory,
                                   'cells', batch_size, scale)
        denominators = _spill_native_long(wide_frames['denominators'], DENOMINATOR_KEYS,
            rows.product, directory, 'denominators', batch_size, scale, coverage)
        return AggregateSet(cells, denominators, pl.scan_parquet(diagnostics_path), rows.product)
    except BaseException:
        shutil.rmtree(directory)
        raise


def aggregate_native(rows: FamilyRows) -> AggregateSet:
    '''Consume lazy members while their authenticated source context is still alive.'''
    if rows.product.pool_divisor not in (1, 2) or not rows.product.years:
        raise ValueError('unsupported declared pooling period')
    scale = _weight_scale(rows)
    cells, denominators = pl.collect_all([
        _native_groups(rows.members, PAIR_KEYS, rows.product, scale),
        _native_groups(rows.members, DENOMINATOR_KEYS, rows.product, scale),
    ])
    if rows.product.view == 'canonical':
        coverage = rows.members.select(
            *DENOMINATOR_KEYS, '_canonical_native_coverage').unique().explode(
                '_canonical_native_coverage').unnest('_canonical_native_coverage').collect()
        denominators = denominators.join(coverage,
            on=[*DENOMINATOR_KEYS, 'component_year'], how='left', validate='m:1')
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


ESTIMATE_INPUT_CHUNK_ROWS = 4096


def _aggregate_batches(frame):
    return frame.collect_batches(chunk_size=ESTIMATE_INPUT_CHUNK_ROWS,
                                 engine='streaming', maintain_order=True, lazy=True)


class _OrderedAggregateReader:
    '''Read and validate one complete fact key with a bounded unfinished carry.'''

    def __init__(self, frame, keys, product):
        self.schema = frame.collect_schema()
        expected = {**{key: pl.String for key in keys},
                    'component_year': pl.Int64, 'replicate': pl.UInt8}
        if any(self.schema.get(key) != dtype for key, dtype in expected.items()):
            raise ValueError('aggregate join key types must match ordered aggregate schema')
        self._keys = [self.schema.names().index(key) for key in keys]
        self._grain = [*self._keys, self.schema.names().index('component_year'),
                       self.schema.names().index('replicate')]
        self._components = sorted([0, *product.years])
        self._group_rows = len(self._components) * (REPLICATE_COUNT + 1)
        self._batches = _aggregate_batches(frame)
        self._batch = None
        self._offset = 0
        self._previous = None
        self._rows = []

    def release(self):
        # The pinned Polars batch iterator has no public cancellation method.
        self._batches = None
        self._batch = None
        self._rows = []

    def _take_row(self):
        while self._batch is None or self._offset == self._batch.height:
            self._batch = next(self._batches, None)
            self._offset = 0
            if self._batch is None:
                return None
        row = self._batch.row(self._offset)
        self._offset += 1
        return row

    def next_group(self):
        key = None
        while len(self._rows) < self._group_rows:
            row = self._take_row()
            if row is None:
                if self._rows:
                    raise ValueError('incomplete aggregate component/replicate membership')
                return None
            grain = tuple(row[index] for index in self._grain)
            if any(value is None for value in grain):
                raise ValueError('null aggregate join key')
            if self._previous is not None:
                if grain == self._previous:
                    raise ValueError('duplicate aggregate join keys')
                if grain < self._previous:
                    raise ValueError('aggregate input must be globally ordered by full grain')
            self._previous = grain
            row_key = grain[:-2]
            if key is None:
                key = row_key
            if (row_key != key or grain[-2] not in self._components
                    or not 0 <= grain[-1] <= REPLICATE_COUNT):
                raise ValueError('incomplete aggregate component/replicate membership')
            self._rows.append(row)
        # C strictly increasing grains from C allowed members fill the complete grid.
        frame = pl.DataFrame(self._rows, schema=self.schema, orient='row')
        self._rows = []
        return key, frame


def _append_estimate_fragment(output, path, schema, keys, row_count, first_key, last_key,
                              *, descriptor_bytes=None):
    '''Append one bounded descriptor without retaining a product-wide collection.'''
    descriptor_bytes = (_ESTIMATE_DESCRIPTOR_BYTES if descriptor_bytes is None
                        else descriptor_bytes)
    record = dict(path=Path(path).name, schema=str(pl.Schema(schema)), row_count=row_count,
                  first_key=first_key, last_key=last_key, keys=keys)
    encoded = json.dumps(record, ensure_ascii=True, allow_nan=False) + '\n'
    if len(encoded.encode()) > descriptor_bytes:
        raise ValueError('ordered-merge resource-budget: descriptor-record-bytes')
    output.write(encoded)


@dataclass(frozen=True)
class _EstimateFragment:
    path: Path
    first_key: tuple | None
    last_key: tuple | None
    row_count: int
    schema: tuple


def _sink_estimate_fragment(frame, directory, label, index, keys):
    schema = tuple(frame.collect_schema().items())
    summary = frame.select(pl.len().alias('n'),
        pl.struct(keys).first().alias('first'), pl.struct(keys).last().alias('last')).collect()
    count, first, last = summary.row(0)
    if not count:
        return
    path = directory / f'{label}-{index:08d}.parquet'
    _sink_native_aggregate(frame, path)
    return _EstimateFragment(path, tuple(first.values()), tuple(last.values()), count, schema)


def _spill_estimates(aggregates: AggregateSet, workspace: Path, *,
                     batch_size: int = 128) -> dict[str, pl.LazyFrame]:
    '''Compatibility adapter retaining the existing small/public scan interface.'''
    return _spill_estimates_impl(aggregates, workspace, batch_size=batch_size, descriptors=False)


def _spill_estimate_fragments(aggregates: AggregateSet, workspace: Path, *,
                              batch_size: int = 128) -> dict[str, Path]:
    '''Hand off streamed descriptors before building any product-wide scan union.'''
    return _spill_estimates_impl(aggregates, workspace, batch_size=batch_size, descriptors=True)


def _spill_estimates_impl(aggregates, workspace, *, batch_size, descriptors):
    product = aggregates.product
    if product.pool_divisor not in (1, 2) or not product.years:
        raise ValueError('unsupported declared pooling period')
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
        raise ValueError('batch_size must be a positive integer')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', product.product_id):
        raise ValueError('unsafe estimator aggregate product ID')
    workspace = Path(workspace)
    safe_path(workspace)
    if not workspace.is_dir():
        raise ValueError('estimator workspace must be an existing directory')
    directory = workspace / ('estimates-' + product.product_id)
    safe_path(directory)
    directory.mkdir()
    cells = denominators = None
    manifests = ExitStack()
    try:
        cells = _OrderedAggregateReader(aggregates.cells, PAIR_KEYS, product)
        denominators = _OrderedAggregateReader(aggregates.denominators, DENOMINATOR_KEYS, product)
        empty_cells = pl.DataFrame(schema=cells.schema).lazy()
        labels = ('targets', 'support', 'replicates')
        fragments = {name: [] for name in labels} if not descriptors else None
        counters = dict.fromkeys(labels, 0)
        paths = {name: directory / (name + '.jsonl') for name in labels}
        outputs = {name: manifests.enter_context(path.open('x'))
                   for name, path in paths.items()} if descriptors else {}
        schemas = {'targets': TARGET_SCHEMA, 'support': SUPPORT_SCHEMA,
                   'replicates': REPLICATE_SCHEMA}
        keys = {'targets': TARGET_KEY_COLUMNS,
                'support': [*STAT_KEY_COLUMNS, 'record_kind', 'component_year'],
                'replicates': [*STAT_KEY_COLUMNS, 'replicate']}

        def sink(label, frame):
            fragment = _sink_estimate_fragment(frame, directory, label,
                                               counters[label], keys[label])
            if fragment is not None:
                counters[label] += 1
                if descriptors:
                    _append_estimate_fragment(
                        outputs[label], fragment.path, schemas[label], keys[label],
                        fragment.row_count, fragment.first_key, fragment.last_key)
                else:
                    fragments[label].append(fragment)

        def sink_cells(batch, denominator):
            bounded = AggregateSet(pl.concat(batch).lazy(), denominator.lazy(),
                                   aggregates.diagnostics, product)
            outputs = estimate(bounded)
            sink('targets', outputs['targets'])
            sink('support', outputs['support'].filter(pl.col('record_kind').eq('cell')))
            sink('replicates', outputs['replicates'])

        cell = cells.next_group()
        denominator = denominators.next_group()
        while denominator is not None:
            a, facts = denominator
            if cell is not None and cell[0][:len(DENOMINATOR_KEYS)] < a:
                raise ValueError('cell missing denominator aggregate')
            statuses = estimate(AggregateSet(empty_cells, facts.lazy(),
                                            aggregates.diagnostics, product))['support']
            sink('support', statuses.filter(pl.col('record_kind').eq('denominator_status')))
            del statuses
            batch = []
            while cell is not None and cell[0][:len(DENOMINATOR_KEYS)] == a:
                batch.append(cell[1])
                cell = None
                if len(batch) == batch_size:
                    sink_cells(batch, facts)
                    batch.clear()
                cell = cells.next_group()
            if batch:
                sink_cells(batch, facts)
                batch.clear()
            denominator = None
            del facts
            denominator = denominators.next_group()
        if cell is not None:
            raise ValueError('cell missing denominator aggregate')
        if descriptors:
            for label in labels:
                if not counters[label]:
                    path = directory / f'{label}-empty.parquet'
                    _sink_native_aggregate(pl.LazyFrame(schema=schemas[label]), path)
                    _append_estimate_fragment(outputs[label], path, schemas[label], keys[label],
                                    0, None, None)
            manifests.close()
            return paths
        outputs = {}
        for label, records in fragments.items():
            paths = [fragment.path for fragment in records]
            if not paths:
                path = directory / f'{label}-empty.parquet'
                _sink_native_aggregate(pl.LazyFrame(schema=schemas[label]), path)
                paths.append(path)
            outputs[label] = pl.concat([pl.scan_parquet(path) for path in paths])
        return outputs
    except BaseException:
        shutil.rmtree(directory)
        raise
    finally:
        manifests.close()
        if cells is not None:
            cells.release()
        if denominators is not None:
            denominators.release()
