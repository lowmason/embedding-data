'''Assign every submitted establishment-year row using selected county evidence.'''

import polars as pl

from embedding_data.geography_hud import LOOKUP_SCHEMA
from embedding_data.geography_tables import COUNTY_SCHEMA
from embedding_data.ita_assignment_prepare import SOURCE_INDEX_SCHEMA
from embedding_data.ita_county_verification import (
    OUT_OF_SCOPE_COUNTY_PREFIXES,
    OUT_OF_SCOPE_STATES,
)
from embedding_data.ita_verification import zip_key
from embedding_data.target_inputs import CANONICAL_SCHEMA

SCHEMA_VERSION = 'ita-assignment-v1'
RESPONSE_SCHEMA = {c: pl.String for c in [
    'request_id', 'geocode_status', 'match_type', 'geocode_county_geoid']}
FLAGS = [
    'flag_delivered_state_out_of_scope', 'flag_geocode_county_out_of_scope',
    'flag_geocode_county_incompatible', 'flag_geocode_county_legacy_ct',
    'flag_request_incomplete', 'flag_assignment_hud',
]
APPENDED_SCHEMA = {
    **SOURCE_INDEX_SCHEMA, 'zip_key': pl.String,
    **{c: dtype for c, dtype in RESPONSE_SCHEMA.items() if c != 'request_id'},
    **{c: dtype for c, dtype in LOOKUP_SCHEMA.items() if c != 'zip_key'},
    **COUNTY_SCHEMA, 'assignment_method': pl.String, 'assignment_reason': pl.String,
    **dict.fromkeys(FLAGS, pl.Boolean),
}


def assignment_schema(canonical_schema: pl.Schema) -> dict:
    if set(canonical_schema).intersection(APPENDED_SCHEMA):
        raise ValueError('overlapping assignment columns')
    if list(canonical_schema.items()) != list(CANONICAL_SCHEMA.items()):
        raise ValueError('canonical schema mismatch')
    return {**canonical_schema, **APPENDED_SCHEMA}


def _has_rows(frame: pl.LazyFrame) -> bool:
    return frame.select(pl.len()).collect().item() > 0


def _check_schema(frame, schema, label):
    if list(frame.collect_schema().items()) != list(schema.items()):
        raise ValueError(f'{label} schema mismatch')


def _check_unique(frame, key, label):
    stats = frame.select(pl.len().alias('rows'), pl.col(key).n_unique().alias('unique'),
                         pl.col(key).null_count().alias('nulls')).collect().row(0)
    if stats[0] != stats[1] or stats[2]:
        raise ValueError(f'{label} has duplicate or null {key}')


def county_choice(inventory: list[str]) -> tuple[pl.Expr, pl.Expr, pl.Expr]:
    delivered_veto = pl.col('flag_delivered_state_out_of_scope')
    exact = pl.col('geocode_status').eq('Match').and_(
        pl.col('match_type').eq('Exact')).fill_null(False)
    excluded = pl.col('flag_geocode_county_out_of_scope')
    compatible = pl.col('geocode_county_geoid').is_in(inventory).fill_null(False)
    hud = pl.col('eligibility_status').eq('eligible')
    choice = (pl.when(delivered_veto).then(pl.lit(None, dtype=pl.String))
              .when(exact.and_(excluded)).then(pl.lit(None, dtype=pl.String))
              .when(exact.and_(compatible)).then(pl.col('geocode_county_geoid'))
              .when(hud).then(pl.col('zip_fallback_county'))
              .otherwise(pl.lit(None, dtype=pl.String)))
    method = (pl.when(delivered_veto.or_(exact.and_(excluded))).then(pl.lit('unassigned'))
              .when(exact.and_(compatible)).then(pl.lit('census_exact'))
              .when(hud).then(pl.lit('hud_singleton')).otherwise(pl.lit('unassigned')))
    reason = (pl.when(delivered_veto).then(pl.lit('delivered_state_out_of_scope'))
              .when(exact.and_(excluded)).then(pl.lit('exact_census_out_of_scope'))
              .when(exact.and_(compatible)).then(pl.lit('exact_census_compatible'))
              .when(hud).then(pl.lit('eligible_hud_singleton'))
              .otherwise(pl.concat_str(pl.lit('no_compatible_county:'),
                                       pl.col('eligibility_status'))))
    return choice, method, reason


def assign(canonical: pl.LazyFrame, source_index: pl.LazyFrame, responses: pl.LazyFrame,
           hud_lookup: pl.DataFrame, counties: pl.DataFrame) -> pl.LazyFrame:
    schema = assignment_schema(canonical.collect_schema())
    for frame, expected, label in [
        (source_index, SOURCE_INDEX_SCHEMA, 'source index'),
        (responses, RESPONSE_SCHEMA, 'responses'),
        (hud_lookup.lazy(), LOOKUP_SCHEMA, 'HUD'),
        (counties.lazy(), COUNTY_SCHEMA, 'counties'),
    ]:
        _check_schema(frame, expected, label)
    for frame, key, label in [(source_index, 'source_row', 'source index'),
                              (responses, 'request_id', 'responses'),
                              (hud_lookup.lazy(), 'zip_key', 'HUD'),
                              (counties.lazy(), 'county_geoid', 'counties')]:
        _check_unique(frame, key, label)
    indexed = canonical.with_row_index('source_row').with_columns(
        pl.col('source_row').cast(pl.UInt64))
    for left, right, key in [(indexed, source_index, 'source_row'),
                              (source_index, responses, 'request_id')]:
        if (_has_rows(left.join(right.select(key), on=key, how='anti'))
                or _has_rows(right.join(left.select(key), on=key, how='anti'))):
            raise ValueError(f'incomplete or unexpected {key} coverage')
    if _has_rows(responses.filter(pl.col('geocode_status').is_null())):
        raise ValueError('missing geocode status')
    joined = indexed.join(source_index, on='source_row', how='left', validate='1:1').join(
        responses, on='request_id', how='left', validate='m:1').with_columns(
            pl.col('zip_code').map_elements(zip_key, return_dtype=pl.String).alias('zip_key')
        ).join(hud_lookup.lazy(), on='zip_key', how='left', validate='m:1')
    defaults = []
    for name, dtype in LOOKUP_SCHEMA.items():
        if dtype == pl.Int64:
            defaults.append(pl.col(name).fill_null(pl.lit(0, dtype=pl.Int64)))
        elif dtype == pl.List(pl.String):
            defaults.append(pl.col(name).fill_null(pl.lit([], dtype=dtype)))
        elif dtype == pl.Boolean:
            defaults.append(pl.col(name).fill_null(False))
    inventory = counties['county_geoid'].to_list()
    returned = pl.col('geocode_county_geoid')
    excluded = returned.str.slice(0, 2).is_in(OUT_OF_SCOPE_COUNTY_PREFIXES).fill_null(False)
    joined = joined.with_columns(
        *defaults, pl.col('eligibility_status').fill_null('absent'),
        flag_delivered_state_out_of_scope=pl.col('state').str.strip_chars()
        .str.to_uppercase().is_in(OUT_OF_SCOPE_STATES).fill_null(False),
        flag_geocode_county_out_of_scope=excluded,
        flag_geocode_county_incompatible=returned.is_not_null().and_(excluded.not_())
        .and_(returned.is_in(inventory).fill_null(False).not_()),
        flag_geocode_county_legacy_ct=returned.str.contains(r'^090[0-9]{2}$').fill_null(False),
        flag_request_incomplete=pl.any_horizontal([
            pl.col(c).fill_null('').str.strip_chars().eq('')
            for c in ['street_address', 'city', 'state', 'zip_key']]),
    )
    choice, method, reason = county_choice(inventory)
    result = joined.with_columns(choice.alias('county_geoid'), method.alias('assignment_method'),
                                 reason.alias('assignment_reason')).join(
        counties.lazy(), on='county_geoid', how='left', validate='m:1').with_columns(
            flag_assignment_hud=pl.col('assignment_method').eq('hud_singleton')
        ).select(list(schema)).sort('source_row')
    validate_assignments(result, canonical, counties)
    return result


def validate_assignments(frame: pl.LazyFrame, canonical: pl.LazyFrame,
                         counties: pl.DataFrame) -> None:
    schema = assignment_schema(canonical.collect_schema())
    _check_schema(frame, schema, 'assignment')
    _check_schema(counties.lazy(), COUNTY_SCHEMA, 'counties')
    _check_unique(counties.lazy(), 'county_geoid', 'counties')
    stats = frame.select(pl.len().alias('rows'),
                         pl.col('source_row').n_unique().alias('unique'),
                         pl.col('source_row').null_count().alias('nulls'),
                         pl.col('source_row').ne_missing(pl.int_range(
                             pl.len(), dtype=pl.UInt64)).any().alias('wrong_order')).collect()
    n = canonical.select(pl.len()).collect().item()
    if stats.row(0) != (n, n, 0, False):
        raise ValueError('source row count/index/order changed')
    expected = canonical.with_row_index('source_row').with_columns(
        pl.col('source_row').cast(pl.UInt64))
    compare = frame.join(expected, on='source_row', how='left', suffix='_expected', validate='1:1')
    if _has_rows(compare.filter(pl.any_horizontal([
            pl.col(c).ne_missing(pl.col(c + '_expected')) for c in CANONICAL_SCHEMA]))):
        raise ValueError('canonical source prefix changed')
    required = ['request_id', 'geocode_status', 'assignment_method', 'assignment_reason', *FLAGS]
    required += [c for c, dtype in LOOKUP_SCHEMA.items() if dtype == pl.Boolean]
    if _has_rows(frame.filter(pl.any_horizontal([pl.col(c).is_null() for c in required]))):
        raise ValueError('required assignment field is null')
    reference = frame.join(counties.lazy(), on='county_geoid', how='left',
                           suffix='_reference', validate='m:1')
    mismatched = pl.any_horizontal([
        pl.col(c).ne_missing(pl.col(c + '_reference'))
        for c in COUNTY_SCHEMA if c != 'county_geoid'])
    missing = pl.col('county_geoid').is_not_null().and_(pl.col('county_id_reference').is_null())
    missing = missing.or_(pl.col('assignment_method').ne('unassigned').and_(
        pl.col('county_geoid').is_null()))
    if _has_rows(reference.filter(mismatched.or_(missing))):
        raise ValueError('assigned attributes differ from selected county reference')
    choice, method, reason = county_choice(counties['county_geoid'].to_list())
    if _has_rows(frame.filter(pl.any_horizontal(
            pl.col('county_geoid').ne_missing(choice),
            pl.col('assignment_method').ne_missing(method),
            pl.col('assignment_reason').ne_missing(reason),
            pl.col('flag_assignment_hud').ne_missing(
                pl.col('assignment_method').eq('hud_singleton'))))):
        raise ValueError('assignment contradicts county precedence')


def assignment_report(frame: pl.LazyFrame) -> dict:
    year = 'year_filing_for'
    partitions = {
        'assignment_reasons': ['assignment_reason'],
        'assignment_methods': ['assignment_method'],
        'geocode_coverage': ['geocode_status', 'match_type'],
        'delivered_scope': ['flag_delivered_state_out_of_scope'],
        'returned_scope': ['flag_geocode_county_out_of_scope',
                           'flag_geocode_county_incompatible'],
    }
    report = {
        'schema_version': SCHEMA_VERSION,
        'input_rows': frame.select(pl.len()).collect().item(),
        'partition_semantics': 'disjoint within each partition',
        'diagnostic_semantics': 'overlapping flags; not county accuracy',
    }
    for name, keys in partitions.items():
        report[name] = frame.group_by(year, *keys).agg(pl.len().alias('rows')).sort(
            year, *keys).collect().to_dicts()
    flags = [c for c, dtype in frame.collect_schema().items() if dtype == pl.Boolean]
    aggregates = frame.group_by(year).agg([
        expression for c in flags for expression in [
            pl.col(c).sum().alias(c + '_true'), pl.col(c).null_count().alias(c + '_null')]
    ]).sort(year).collect()
    report['diagnostic_flags'] = [
        {year: row[year], 'flag': flag, 'true_rows': row[flag + '_true'],
         'null_rows': row[flag + '_null']}
        for row in aggregates.iter_rows(named=True) for flag in flags]
    return report
