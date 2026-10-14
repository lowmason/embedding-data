'''Conditional shares of submitted native-industry establishment-year records.'''

from dataclasses import dataclass

import polars as pl

from embedding_data.target_contract import TARGET_KEY_COLUMNS, TARGET_SCHEMA, validate_targets
from embedding_data.target_inputs import CANONICAL_SCHEMA, validate_native

ESTIMATOR_VERSION = 'ita-area-mix-v1'
DENOMINATOR_SCHEMA = {
    'sample_set': pl.String, 'county_id': pl.String,
    'n_assigned': pl.UInt64, 'n_eligible': pl.UInt64, 'n_excluded_industry': pl.UInt64,
}
FLAG_COUNT_SCHEMA = {
    'scope': pl.String, 'county_id': pl.String, 'naics_2022_node_id': pl.String,
    'flag_name': pl.String, 'flag_state': pl.String, 'n': pl.UInt64,
}
UNIVERSE = (
    'OSHA ITA Form 300A is a program-selected filing subset, not a frame representative '
    'of all establishments; voluntary/outside-rule filings are retained and reported '
    'employment is unvalidated. This target counts submitted 2023 establishment-year '
    'records with preserved duplicate multiplicity, valid native NAICS 2022 industries '
    'and adopted compatible county assignments in the common 2025 frame, within the '
    '50 states and DC. It is conditional on that eligibility population.'
)
SAMPLE_SET = 'ita_300a_2023'
TOLERANCE = 1e-12
CELL_KEYS = ['county_id', 'naics_2022_node_id']
METADATA = dict(source='osha_ita', family='area_mix', unit_a_type='county',
                unit_b_type='naics_national_industry', measure='establishment_share',
                se_method='none', sample_set=SAMPLE_SET, vintage='naics=2022;county=2025',
                universe=UNIVERSE)


@dataclass(frozen=True)
class AreaMix:
    targets: pl.LazyFrame
    denominators: pl.LazyFrame
    flag_counts: pl.LazyFrame
    report: dict


def eligible_industry() -> pl.Expr:
    return (pl.col('naics_mapping_status').eq('native_2022')
            .and_(pl.col('naics_2022_node_id').is_not_null())
            .and_(pl.col('flag_naics_crosswalked').not_())
            .and_(pl.col('flag_naics_ambiguous').not_())
            .and_(pl.col('flag_naics_unresolved').not_())).fill_null(False)


def _flag_aggregates(frame: pl.LazyFrame, keys: list[str]) -> pl.LazyFrame:
    columns = [c for c, dtype in frame.collect_schema().items() if dtype == pl.Boolean]
    schema = {key: frame.collect_schema()[key] for key in keys}
    if not columns:
        return pl.DataFrame(schema={**schema, 'flag_name': pl.String,
                                    'flag_state': pl.String, 'n': pl.UInt64}).lazy()
    return (frame.select(*keys, *columns).unpivot(on=columns, index=keys,
                variable_name='flag_name', value_name='_flag')
            .filter(pl.col('_flag').is_null().or_(pl.col('_flag')))
            .with_columns(pl.when(pl.col('_flag').is_null()).then(pl.lit('null'))
                          .otherwise(pl.lit('true')).alias('flag_state'))
            .group_by(*keys, 'flag_name', 'flag_state').agg(n=pl.len().cast(pl.UInt64)))


def support_flags(eligible: pl.LazyFrame) -> pl.LazyFrame:
    # Only aggregate cells are materialized; denominator support shares this result.
    numerator = _flag_aggregates(eligible, CELL_KEYS).collect().lazy()
    denominator = numerator.group_by('county_id', 'flag_name', 'flag_state').agg(
        pl.col('n').sum()).with_columns(
            pl.lit(None, dtype=pl.String).alias('naics_2022_node_id'))
    return pl.concat([frame.with_columns(pl.lit(scope).alias('scope'))
                      .select(list(FLAG_COUNT_SCHEMA)) for scope, frame in
                      [('numerator', numerator), ('denominator', denominator)]]).sort(
                          list(FLAG_COUNT_SCHEMA)[:-1], nulls_last=False)


def _labels(cells: pl.LazyFrame, flags: pl.LazyFrame) -> pl.LazyFrame:
    labels = flags.with_columns(pl.concat_str('scope', 'flag_name', 'flag_state',
                                              separator=':').alias('_label'))
    numerator = labels.filter(pl.col('scope').eq('numerator')).select(*CELL_KEYS, '_label')
    denominator = cells.select(CELL_KEYS).join(
        labels.filter(pl.col('scope').eq('denominator')).select('county_id', '_label'),
        on='county_id', how='inner')
    pending = cells.select(*CELL_KEYS, pl.lit('size_gate_pending').alias('_label'))
    return pl.concat([numerator, denominator, pending]).group_by(CELL_KEYS).agg(
        pl.col('_label').unique().sort().alias('flags'))


def _partition(frame: pl.LazyFrame) -> dict:
    assigned = pl.col('county_id').is_not_null()
    industry = eligible_industry()
    return frame.select(source=pl.len(), unassigned_geography=assigned.not_().sum(),
        assigned_excluded_industry=assigned.and_(industry.not_()).sum(),
        eligible=assigned.and_(industry).sum()).collect().row(0, named=True)


def _duplicates(frame: pl.LazyFrame, keys: list[str]) -> dict:
    return (frame.group_by(keys).len().filter(pl.col('len').gt(1)).select(
        groups=pl.len(), rows=pl.col('len').sum(), excess=pl.col('len').sub(1).sum())
        .collect().row(0, named=True))


def _distribution(frame: pl.LazyFrame, column: str) -> dict:
    value = pl.col(column)
    return frame.select(count=pl.len(), min=value.min(), p25=value.quantile(.25),
                        median=value.median(), p75=value.quantile(.75),
                        p95=value.quantile(.95), max=value.max()).collect().row(0, named=True)


def _report(assignments, selected, denominators, cells):
    return {
        'estimator_version': ESTIMATOR_VERSION,
        'all_year_partition': _partition(assignments),
        'selected_year_partition': _partition(selected),
        'partition_by_year': assignments.group_by('year_filing_for').agg(
            source=pl.len(), assigned=pl.col('county_id').is_not_null().sum(),
            eligible=pl.col('county_id').is_not_null().and_(eligible_industry()).sum(),
            unassigned_geography=pl.col('county_id').is_null().sum(),
            assigned_excluded_industry=pl.col('county_id').is_not_null()
                .and_(eligible_industry().not_()).sum()).sort('year_filing_for').collect().to_dicts(),
        'selected_year_mapping_assignment': selected.group_by(
            'naics_mapping_status', 'assignment_method', 'assignment_reason').len()
            .sort('naics_mapping_status', 'assignment_method', 'assignment_reason')
            .collect().to_dicts(),
        'exact_duplicates': _duplicates(assignments, list(CANONICAL_SCHEMA)),
        'repeated_ids': {key: _duplicates(assignments.filter(pl.col(key).is_not_null()), [key])
                         for key in ['id', 'establishment_id']},
        'county_denominator_distribution': _distribution(denominators, 'n_eligible'),
        'cell_count_distribution': _distribution(cells, 'n_unweighted'),
        'method_coverage_by_year': assignments.group_by('year_filing_for', 'assignment_method')
            .len().sort('year_filing_for', 'assignment_method').collect().to_dicts(),
        'flags_by_year': _flag_aggregates(assignments, ['year_filing_for'])
            .sort('year_filing_for', 'flag_name', 'flag_state').collect().to_dicts(),
    }


def estimate(assignments: pl.LazyFrame, nodes: pl.DataFrame, *, year: int = 2023) -> AreaMix:
    if year != 2023:
        raise ValueError('area_mix supports only 2023')
    validate_native(assignments, nodes)
    selected = assignments.filter(pl.col('year_filing_for').eq(year))
    assigned = selected.filter(pl.col('county_id').is_not_null())
    eligible = assigned.filter(eligible_industry())
    cells = eligible.group_by(CELL_KEYS).agg(n_unweighted=pl.len().cast(pl.UInt64)).collect()
    if cells.is_empty():
        raise ValueError('no eligible 2023 records')
    cells = cells.lazy()
    eligible_counts = cells.group_by('county_id').agg(
        pl.col('n_unweighted').sum().alias('n_eligible'))
    denominators = (assigned.group_by('county_id').agg(n_assigned=pl.len().cast(pl.UInt64))
        .join(eligible_counts, on='county_id', how='left')
        .with_columns(pl.col('n_eligible').fill_null(0), pl.lit(SAMPLE_SET).alias('sample_set'))
        .with_columns(pl.col('n_assigned').sub(pl.col('n_eligible')).alias('n_excluded_industry'))
        .select(list(DENOMINATOR_SCHEMA)).sort('sample_set', 'county_id').collect().lazy())
    flags = support_flags(eligible)
    targets = (cells.join(eligible_counts, on='county_id')
        .join(_labels(cells, flags), on=CELL_KEYS)
        .with_columns(*[pl.lit(value).alias(key) for key, value in METADATA.items()],
            pl.col('county_id').alias('unit_a'), pl.col('naics_2022_node_id').alias('unit_b'),
            pl.col('n_unweighted').truediv(pl.col('n_eligible')).alias('value'),
            pl.col('n_unweighted').cast(pl.Float64).alias('n_weighted'),
            pl.lit(None, dtype=pl.Float64).alias('se'))
        .select(list(TARGET_SCHEMA)).sort(TARGET_KEY_COLUMNS))
    report = _report(assignments, selected, denominators, cells)
    return AreaMix(targets, denominators, flags, report)


def _reject(frame: pl.LazyFrame, condition: pl.Expr, message: str) -> None:
    if frame.select(condition.fill_null(True).any()).collect().item():
        raise ValueError(message)


def validate_area_mix(result: AreaMix, nodes: pl.DataFrame, counties: pl.DataFrame) -> None:
    validate_targets(result.targets)
    for frame, schema in [(result.denominators, DENOMINATOR_SCHEMA),
                          (result.flag_counts, FLAG_COUNT_SCHEMA)]:
        if list(frame.collect_schema().items()) != list(schema.items()):
            raise ValueError('area_mix companion schema mismatch')
    targets, denominators, flags = result.targets, result.denominators, result.flag_counts
    if targets.select(pl.len()).collect().item() == 0:
        raise ValueError('no eligible target cells')
    leaves = nodes.filter(pl.col('system').eq('naics').and_(pl.col('vintage').eq(2022))
                          .and_(pl.col('level').eq('national_industry')))['node_id'].to_list()
    inventory = counties['county_id'].to_list()
    _reject(targets, pl.any_horizontal([pl.col(k).ne(v) for k, v in METADATA.items()])
            .or_(pl.col('unit_a').is_in(inventory).not_())
            .or_(pl.col('unit_b').is_in(leaves).not_())
            .or_(pl.col('n_unweighted').eq(0))
            .or_(pl.col('n_weighted').ne(pl.col('n_unweighted').cast(pl.Float64)))
            .or_(pl.col('se').is_not_null())
            .or_(pl.col('value').le(0)).or_(pl.col('value').gt(1 + TOLERANCE)),
            'invalid area_mix metadata, membership or support')
    _reject(denominators, pl.any_horizontal(pl.all().is_null())
            .or_(pl.col('sample_set').ne(SAMPLE_SET))
            .or_(pl.col('county_id').is_in(inventory).not_())
            .or_(pl.col('n_assigned').eq(0))
            .or_(pl.col('n_eligible').gt(pl.col('n_assigned')))
            .or_(pl.col('n_excluded_industry').ne(
                pl.col('n_assigned').sub(pl.col('n_eligible')))), 'invalid county denominator')
    _reject(denominators.group_by('county_id').len(), pl.col('len').ne(1),
            'duplicate county denominator')
    totals = targets.group_by('unit_a').agg(pl.col('n_unweighted').sum(), pl.col('value').sum())
    joined = denominators.join(totals, left_on='county_id', right_on='unit_a', how='full',
                               coalesce=True)
    _reject(joined, pl.col('n_eligible').ne_missing(pl.col('n_unweighted').fill_null(0))
            .or_(pl.col('n_eligible').gt(0).and_(
                pl.col('value').sub(1).abs().gt(TOLERANCE))),
            'county support or normalization differs')
    cells = targets.select(pl.col('unit_a').alias('county_id'),
                           pl.col('unit_b').alias('naics_2022_node_id'), 'n_unweighted', 'value')
    joined = cells.join(denominators, on='county_id', how='left')
    _reject(joined, pl.col('n_unweighted').gt(pl.col('n_eligible'))
            .or_(pl.col('value').sub(pl.col('n_unweighted').truediv(pl.col('n_eligible')))
                 .abs().gt(TOLERANCE)), 'cell numerator/denominator differs')
    _reject(flags, pl.col('scope').is_in(['numerator', 'denominator']).not_()
            .or_(pl.col('flag_state').is_in(['true', 'null']).not_())
            .or_(pl.col('flag_name').is_null()).or_(pl.col('flag_name').str.len_chars().eq(0))
            .or_(pl.col('n').eq(0))
            .or_(pl.col('scope').eq('denominator').ne(pl.col('naics_2022_node_id').is_null())),
            'invalid flag support')
    _reject(flags.group_by(list(FLAG_COUNT_SCHEMA)[:-1]).len(), pl.col('len').ne(1),
            'duplicate flag support')
    numerator = flags.filter(pl.col('scope').eq('numerator'))
    denominator = flags.filter(pl.col('scope').eq('denominator'))
    combined = numerator.group_by(*CELL_KEYS, 'flag_name').agg(pl.col('n').sum())
    _reject(combined.join(cells, on=CELL_KEYS, how='left'),
            pl.col('n').gt(pl.col('n_unweighted')), 'true/null support overlaps')
    _reject(numerator.join(cells, on=CELL_KEYS, how='left'),
            pl.col('n').gt(pl.col('n_unweighted')), 'flag numerator exceeds cell')
    _reject(denominator.join(denominators, on='county_id', how='left'),
            pl.col('n').gt(pl.col('n_eligible')), 'flag denominator exceeds county')
    flag_keys = ['county_id', 'flag_name', 'flag_state']
    expected = numerator.group_by(flag_keys).agg(pl.col('n').sum().alias('_expected'))
    _reject(denominator.join(expected, on=flag_keys, how='full', coalesce=True),
            pl.col('n').ne_missing(pl.col('_expected')), 'flag scopes disagree')
    labels = _labels(cells, flags).rename({'flags': '_expected_flags'})
    actual = targets.select(pl.col('unit_a').alias('county_id'),
                            pl.col('unit_b').alias('naics_2022_node_id'), 'flags')
    _reject(actual.join(labels, on=CELL_KEYS), pl.col('flags').ne(pl.col('_expected_flags')),
            'target flags disagree with support')
