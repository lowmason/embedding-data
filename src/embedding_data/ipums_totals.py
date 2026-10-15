'''Exact-weight employment levels and explicitly aligned reference comparisons.'''

import polars as pl

from embedding_data.ipums_references import ACS_COMPARISON_STATES

ACS_UNIVERSE = 'civilian_employed_residents_age_16_plus'
CPS_UNIVERSE = 'civilian_noninstitutional_employed_age_16_plus'
CONTEXT = ['period', 'period_start', 'period_end', 'period_years', 'universe',
           'geography_basis', 'geography_scope']
COUNT_COLUMNS = ['rows', 'eligible_rows', 'missing_weight_rows', 'unexpected_status_rows',
                 'military_rows', 'under16_rows', 'missing_age_rows']
LEVEL_SCHEMA = {
    'year': pl.Int64, 'month': pl.Int64, 'state_fips': pl.String,
    'period': pl.String, 'period_start': pl.Int64, 'period_end': pl.Int64,
    'period_years': pl.List(pl.Int64), 'observed_years': pl.List(pl.Int64),
    'missing_years': pl.List(pl.Int64),
    'units': pl.String, 'universe': pl.String, 'geography_basis': pl.String,
    'geography_scope': pl.String, 'weight': pl.String, 'measured': pl.Float64,
    'weight_sum_exact': pl.String, 'annual_divisor': pl.UInt32,
    **{name: pl.UInt64 for name in COUNT_COLUMNS}, 'unexpected_statuses': pl.List(
        pl.Struct({'field': pl.String, 'value': pl.String})),
}


def _validate_input(frame, weight, temporal):
    schema = frame.collect_schema()
    dtype = schema[weight]
    if not isinstance(dtype, pl.Decimal):
        raise ValueError('employment weights require exact Decimal values from the raw CSV scan')
    for name in [*temporal, 'AGE', 'EMPSTAT']:
        if not schema[name].is_integer():
            raise ValueError(f'{name} must retain verified integer source interpretation')
    summary = frame.select(pl.len().alias('rows'), pl.col(weight).abs().max().alias('maximum'),
                           pl.any_horizontal(pl.col(temporal).is_null()).any().alias('missing'))
    evidence = summary.collect().row(0, named=True)
    if evidence['missing']:
        raise ValueError('employment period cannot be missing')
    if evidence['maximum'] is not None:
        integer_digits = max(evidence['maximum'].adjusted() + 1, 0)
        carry = len(str(evidence['rows'] - 1)) if evidence['rows'] > 1 else 0
        if integer_digits + dtype.scale + carry > 38:
            raise ValueError('employment Decimal38 aggregate precision bound exceeded')


def _aggregate(frame, keys, weight, eligible, military, unexpected):
    status_values = pl.concat_list([
        pl.when(condition).then(pl.struct(
            pl.lit(name).alias('field'), pl.col(name).cast(pl.String).alias('value'),
        )).otherwise(None) for name, condition in unexpected.items()
    ]).list.drop_nulls()
    return frame.group_by(keys).agg(
        pl.len().cast(pl.UInt64).alias('rows'),
        eligible.fill_null(False).sum().cast(pl.UInt64).alias('eligible_rows'),
        eligible.and_(pl.col(weight).is_null()).fill_null(False).sum()
            .cast(pl.UInt64).alias('missing_weight_rows'),
        pl.any_horizontal(list(unexpected.values())).sum().cast(pl.UInt64)
            .alias('unexpected_status_rows'),
        military.fill_null(False).sum().cast(pl.UInt64).alias('military_rows'),
        pl.col('AGE').lt(16).sum().cast(pl.UInt64).alias('under16_rows'),
        pl.col('AGE').is_null().sum().cast(pl.UInt64).alias('missing_age_rows'),
        status_values.explode().drop_nulls().unique().sort().alias('unexpected_statuses'),
        pl.col(weight).filter(eligible).sum().alias('_weight_sum'),
    )


def _display(frame):
    return frame.with_columns(
        pl.when(pl.col('missing_weight_rows').eq(0).and_(pl.col('missing_years').list.len().eq(0)))
        .then(pl.col('_weight_sum').cast(pl.Float64).truediv(pl.col('annual_divisor')))
        .otherwise(None).alias('measured'),
        pl.col('_weight_sum').cast(pl.String).alias('weight_sum_exact'),
        pl.lit('persons').alias('units'), pl.lit('residence').alias('geography_basis'),
    ).select(list(LEVEL_SCHEMA)).cast(LEVEL_SCHEMA)


def acs_employment(frame: pl.LazyFrame) -> pl.DataFrame:
    '''Annual and observed-year annual-average state civilian employment with PERWT.

    Requires YEAR, STATEFIP, AGE, EMPSTAT, EMPSTATD, Decimal PERWT. Q flags are retained
    implicitly: no allocation filter is applied. PR/islands are reported outside the
    50-state/DC comparison scope. Pooled rows use all input component years, recording
    the exact summed numerator, divisor and missing years; incomplete states have null levels.
    Task4 must separately verify the global set of delivered/requested component years.
    Unexpected or missing status diagnostics retain both field and value; affected
    records count once even when both EMPSTAT and EMPSTATD are unexpected.
    '''
    _validate_input(frame, 'PERWT', ['YEAR'])
    schema = frame.collect_schema()
    if not schema['EMPSTATD'].is_integer():
        raise ValueError('EMPSTATD must retain verified integer source interpretation')
    state = pl.col('STATEFIP')
    if schema['STATEFIP'].is_integer():
        state = state.cast(pl.String).str.zfill(2)
    elif schema['STATEFIP'] != pl.String:
        raise ValueError('STATEFIP requires integer or String source codes')
    frame = frame.with_columns(state.alias('state_fips'))
    years = frame.select(pl.col('YEAR').unique().sort()).collect()['YEAR'].to_list()
    eligible = pl.col('AGE').ge(16).and_(pl.col('EMPSTAT').eq(1)).and_(
        pl.col('EMPSTATD').is_in([10, 11, 12]))
    military = pl.col('EMPSTATD').is_in([13, 14, 15])
    known = [0, 10, 11, 12, 13, 14, 15, 20, 30]
    unexpected = {
        'EMPSTAT': pl.col('EMPSTAT').is_in([0, 1, 2, 3]).fill_null(False).not_(),
        'EMPSTATD': pl.col('EMPSTATD').is_in(known).fill_null(False).not_(),
    }
    annual = _aggregate(frame, ['YEAR', 'state_fips'], 'PERWT', eligible, military,
                        unexpected).rename({'YEAR': 'year'}).with_columns(
        pl.lit(None, dtype=pl.Int64).alias('month'), pl.lit('annual').alias('period'),
        pl.col('year').alias('period_start'), pl.col('year').alias('period_end'),
        pl.lit(1, dtype=pl.UInt32).alias('annual_divisor'),
        pl.concat_list('year').alias('period_years'),
        pl.concat_list('year').alias('observed_years'),
        pl.lit([], dtype=pl.List(pl.Int64)).alias('missing_years'))
    pooled = annual.group_by('state_fips').agg(
        pl.col('year').unique().sort().alias('observed_years'),
        pl.col(COUNT_COLUMNS).sum(), pl.col('_weight_sum').sum(),
        pl.col('unexpected_statuses').explode().drop_nulls().unique().sort(),
    ).with_columns(pl.lit(None, dtype=pl.Int64).alias('year'),
                   pl.lit(None, dtype=pl.Int64).alias('month'),
                   pl.lit('annual_average').alias('period'),
                   pl.lit(min(years) if years else None, dtype=pl.Int64).alias('period_start'),
                   pl.lit(max(years) if years else None, dtype=pl.Int64).alias('period_end'),
                   pl.lit(len(years), dtype=pl.UInt32).alias('annual_divisor'),
                   pl.lit(years, dtype=pl.List(pl.Int64)).alias('period_years'),
    ).with_columns(pl.col('period_years').list.set_difference(pl.col('observed_years'))
                   .list.sort().alias('missing_years'))
    combined = pl.concat([annual, pooled.select(annual.collect_schema().names())]).with_columns(
        pl.lit(ACS_UNIVERSE).alias('universe'), pl.lit('PERWT').alias('weight'),
        pl.when(pl.col('state_fips').is_in(sorted(ACS_COMPARISON_STATES)))
        .then(pl.lit('50_states_dc')).otherwise(pl.lit('outside_50_states_dc'))
        .alias('geography_scope'))
    return _display(combined).sort('state_fips', 'period', 'year', nulls_last=False).collect()


def cps_employment(frame: pl.LazyFrame) -> pl.DataFrame:
    '''Monthly national civilian employment, AGE>=16 and EMPSTAT10/12, weighted WTFINL.

    EARNWT, ASECWT, linkage weights and replicate weights never enter this estimate.
    Missing eligible weights produce a null level, not an apparently complete partial sum.
    '''
    _validate_input(frame, 'WTFINL', ['YEAR', 'MONTH'])
    if frame.filter(pl.col('MONTH').is_between(1, 12).not_()).select(pl.len()).collect().item():
        raise ValueError('CPS employment requires calendar months 1 through 12')
    eligible = pl.col('AGE').ge(16).and_(pl.col('EMPSTAT').is_in([10, 12]))
    military = pl.col('EMPSTAT').eq(1)
    known = [0, 1, 10, 12, 20, 21, 22, 30, 31, 32, 33, 34, 35, 36]
    unexpected = {'EMPSTAT': pl.col('EMPSTAT').is_in(known).fill_null(False).not_()}
    monthly = _aggregate(frame, ['YEAR', 'MONTH'], 'WTFINL', eligible, military,
                         unexpected).rename({'YEAR': 'year', 'MONTH': 'month'})
    monthly = monthly.with_columns(
        pl.lit(None, dtype=pl.String).alias('state_fips'), pl.lit('monthly').alias('period'),
        pl.col('year').mul(100).add(pl.col('month')).alias('period_start'),
        pl.col('year').mul(100).add(pl.col('month')).alias('period_end'),
        pl.lit(1, dtype=pl.UInt32).alias('annual_divisor'),
        pl.concat_list('year').alias('period_years'),
        pl.concat_list('year').alias('observed_years'),
        pl.lit([], dtype=pl.List(pl.Int64)).alias('missing_years'),
        pl.lit(CPS_UNIVERSE).alias('universe'), pl.lit('50_states_dc').alias('geography_scope'),
        pl.lit('WTFINL').alias('weight'))
    return _display(monthly).sort('year', 'month').collect()


def _comparison_input(frame, keys, level):
    required = set(keys + CONTEXT + ['units', level])
    if not required.issubset(frame.columns):
        raise ValueError('comparison requires explicit period/unit/universe/geography metadata')
    if frame.select(keys).is_duplicated().any():
        raise ValueError('comparison keys must be unique')
    if (frame['units'].null_count() or not set(frame['units']).issubset(
            {'persons', 'thousands of persons'})):
        raise ValueError('comparison units must be persons or thousands of persons')
    if not frame.schema[level].is_numeric():
        raise ValueError('comparison levels must be numeric')
    if frame.filter(pl.col(level).is_not_null().and_(pl.col(level).is_finite().not_())).height:
        raise ValueError('comparison levels must be finite or missing')
    return frame.lazy().with_columns(
        pl.col('units').alias(f'{level}_original_units'),
        pl.when(pl.col('units').eq('thousands of persons')).then(pl.col(level).mul(1000))
        .otherwise(pl.col(level)).cast(pl.Float64).alias(level),
        pl.lit('persons').alias('units'), pl.lit(True).alias(f'_{level}_present'))


def compare_levels(measured: pl.DataFrame, published: pl.DataFrame,
                   keys: list[str]) -> pl.DataFrame:
    '''Full comparison preserving source extras, unmatched rows, and compatibility failures.

    Both frames require CONTEXT and units; caller enriches Task3 parsed reference frames
    from frozen metadata. Keys must identify observations uniquely (include period and
    bounds for annual averages). Shared non-key metadata are preserved with _published
    suffix; source footnotes and snapshot provenance pass through untouched.
    '''
    if not keys or len(keys) != len(set(keys)):
        raise ValueError('comparison requires distinct keys')
    left = _comparison_input(measured, keys, 'measured')
    right = _comparison_input(published, keys, 'published')
    joined = left.join(right, on=keys, how='full', coalesce=True, nulls_equal=True,
                       suffix='_published')
    comparable = pl.lit(True)
    for name in CONTEXT:
        if name not in keys:
            comparable = comparable.and_(pl.col(name).eq(pl.col(f'{name}_published')))
        else:
            comparable = comparable.and_(pl.col(name).is_not_null())
    status = (pl.when(pl.col('_measured_present').is_null()).then(pl.lit('published_only'))
              .when(pl.col('_published_present').is_null()).then(pl.lit('measured_only'))
              .when(comparable.fill_null(False).not_()).then(pl.lit('incompatible_metadata'))
              .when(pl.col('geography_scope').ne('50_states_dc')).then(pl.lit('outside_scope'))
              .otherwise(pl.lit('matched')))
    joined = joined.with_columns(status.alias('comparison_status')).with_columns(
        pl.when(pl.col('comparison_status').eq('matched'))
        .then(pl.col('measured').sub(pl.col('published'))).otherwise(None).alias('gap'),
        pl.when(pl.col('comparison_status').ne('matched')).then(pl.col('comparison_status'))
        .when(pl.col('published').is_null()).then(pl.lit('missing_published'))
        .when(pl.col('published').eq(0)).then(pl.lit('zero_published'))
        .when(pl.col('measured').is_null()).then(pl.lit('missing_measured'))
        .otherwise(pl.lit(None, dtype=pl.String)).alias('relative_gap_reason'),
    ).with_columns(
        pl.when(pl.col('relative_gap_reason').is_null())
        .then(pl.col('gap').truediv(pl.col('published'))).otherwise(None).alias('relative_gap'))
    common = [name for name in CONTEXT + ['units'] if name not in keys]
    joined = joined.with_columns(
        pl.when(pl.col('_measured_present').is_null())
        .then(pl.col(f'{name}_published')).otherwise(pl.col(name)).alias(name) for name in common)
    return joined.drop('_measured_present', '_published_present').sort(
        keys, nulls_last=False).collect()
