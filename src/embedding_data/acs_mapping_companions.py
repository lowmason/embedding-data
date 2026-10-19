'''Ordered ACS companions with separate source evidence and mapping provenance.'''

from pathlib import Path

import polars as pl

from embedding_data import manifest, target_io
from embedding_data.acs_area_mapping import observed_area_keys, validate_area_lookup
from embedding_data.acs_area_references import ROLE_COLUMNS
from embedding_data.acs_code_mapping import _token, scheme_for, source_sample_mapping
from embedding_data.acs_geography_factors import FactorTables
from embedding_data.acs_mapping_contract import (
    ANNOTATION_SCHEMA,
    CODE_ANNOTATIONS,
    NATURAL_KEYS,
    ROLE_ANNOTATIONS,
    SourceInput,
    companion_schema,
    validate_table,
)
from embedding_data.acs_mapping_io import safe_path
from embedding_data.ipums_parity import compare_ordered

TEMP_PREFIX = '__acs_'


def indexed_source(source: SourceInput) -> pl.LazyFrame:
    '''Keep source columns intact and establish ordinal identity before all joins.'''
    safe_path(source.parquet)
    frame = pl.scan_parquet(source.parquet)
    names = frame.collect_schema().names()
    if set(names).intersection(ANNOTATION_SCHEMA) or any(
        name.startswith(TEMP_PREFIX) for name in names
    ):
        raise ValueError('source columns collide with ACS annotations or temporary keys')
    if manifest.sha256_file(source.parquet) != source.parquet_record['sha256']:
        raise ValueError('source Parquet differs from verified source hash')
    return frame.with_row_index('source_row').with_columns(
        pl.col('source_row').cast(pl.UInt64),
        pl.lit(source.parquet_record['sha256']).alias('source_parquet_sha256'),
    )


def _join(frame, lookup, keys):
    if not isinstance(lookup, pl.DataFrame):
        raise TypeError('ACS lookup must be a materialized polars DataFrame')
    # Validate the small lookup eagerly: m:1 forces an in-memory person join.
    # Null-containing keys cannot match with nulls_equal=False.
    if lookup.select(keys).drop_nulls().is_duplicated().any():
        raise ValueError(f'duplicate ACS lookup keys violate m:1 cardinality: {keys}')
    return frame.join(lookup.lazy(), on=keys, how='left', validate='m:m',
                      maintain_order='left', nulls_equal=False, coalesce=True)


def _require_matched(frame, marker, *, missing=None):
    unexplained = pl.col(marker).is_null()
    if missing is not None:
        unexplained = unexplained.and_(missing.not_())
    if frame.select(unexplained.any()).collect().item():
        raise ValueError('missing classification or geographic role lookup')


def _with_identity(frame, source):
    samples = source_sample_mapping(source)
    five_year = source.profile.removeprefix('acs/') == 'five_year'
    names = frame.collect_schema().names()
    required = {'YEAR', 'SAMPLE', 'IND', 'INDNAICS', 'OCC', 'OCCSOC',
                *(c for pair in ROLE_COLUMNS.values() for c in pair[:2])}
    if five_year:
        required.add('MULTYEAR')
    if not required.issubset(names):
        raise ValueError('missing source classification, role or identity columns')
    frame = frame.with_columns(
        pl.col('SAMPLE').cast(pl.String).alias('__acs_sample'),
        pl.col('YEAR').cast(pl.Int64).alias('acs_release_year'),
        (pl.col('MULTYEAR') if five_year else pl.col('YEAR')).cast(pl.Int64).alias(
            'acs_component_year'),
    )
    identities = frame.select('__acs_sample', 'acs_release_year', 'acs_component_year').unique(
    ).collect()
    records = []
    scheme_names = ['industry_delivered_scheme', 'industry_interview_scheme',
                    'occupation_delivered_scheme', 'flag_source_industry_recoded']
    for row in identities.iter_rows(named=True):
        sample = samples.get(row['__acs_sample'])
        if sample is None:
            raise ValueError('observed SAMPLE lacks selected DDI identity')
        schemes = scheme_for(source.profile, sample, row['acs_release_year'],
                             row['acs_component_year'])
        records.append({**row, 'acs_sample_id': sample,
                        **{name: schemes[name] for name in scheme_names}})
    schema = {'__acs_sample': pl.String, 'acs_release_year': pl.Int64,
              'acs_component_year': pl.Int64, 'acs_sample_id': pl.String,
              **{name: ANNOTATION_SCHEMA[name] for name in scheme_names}}
    metadata = pl.DataFrame(records, schema=schema)
    return _join(frame, metadata, ['__acs_sample', 'acs_release_year', 'acs_component_year']
                 ).with_columns(pl.lit(source.profile).alias('acs_profile'))


def _with_code(frame, lookup, prefix, system, pair, token):
    fields = {name: f'{prefix}_{name}' for name in CODE_ANNOTATIONS}
    # Normalization creates separate keys; the delivered pair and token stay untouched.
    frame = frame.with_columns(
        pl.col(pair).cast(pl.String).map_elements(
            lambda value: _token(value, paired=True), return_dtype=pl.String
        ).alias('__acs_pair'),
        pl.col(token).cast(pl.String).map_elements(_token, return_dtype=pl.String).alias(
            '__acs_token'),
        pl.col(f'{prefix}_delivered_scheme').alias('__acs_scheme'),
    )
    own = lookup.filter(pl.col('system').eq(system)).select(
        pl.col('paired_census_code').alias('__acs_pair'),
        pl.col('source_token').alias('__acs_token'),
        pl.col('source_scheme').alias('__acs_scheme'),
        *[pl.col(name).alias(output) for name, output in fields.items()],
    )
    frame = _join(frame, own, ['__acs_pair', '__acs_token', '__acs_scheme'])
    missing = pl.col('__acs_token').is_null()
    _require_matched(frame, f'{prefix}_code_lookup_id', missing=missing)
    defaults = {
        'source_token': pl.col('__acs_token'), 'paired_census_code': pl.col('__acs_pair'),
        'mapping_status': pl.lit('missing'),
        'native_vintage': pl.col('__acs_scheme').str.extract(r'([0-9]{4})$', 1).cast(pl.Int64),
        'canonical_vintage': pl.lit(2022 if system == 'naics' else 2018),
        'aggregation_type': pl.lit('missing'),
        'aggregation_reason_status': pl.lit('not_applicable'),
    }
    expressions = []
    for name, output in fields.items():
        dtype = ANNOTATION_SCHEMA[output]
        fallback = defaults.get(name)
        if fallback is None:
            value = [] if isinstance(dtype, pl.List) else False if dtype == pl.Boolean else None
            fallback = pl.lit(value, dtype=dtype)
        expressions.append(pl.when(missing).then(fallback.cast(dtype)).otherwise(
            pl.col(output)).alias(output))
    return frame.with_columns(expressions).drop('__acs_pair', '__acs_token', '__acs_scheme')


def _with_role(frame, lookup, factors, role):
    state, area, _ = ROLE_COLUMNS[role]
    area_keys = list(NATURAL_KEYS['area'])
    names = ['acs_profile', 'acs_sample_id', 'acs_release_year', 'acs_component_year',
             '__acs_role', '__acs_state', '__acs_area']
    own = lookup.filter(pl.col('role').eq(role)).select(
        *[pl.col(key).alias(name) for key, name in zip(area_keys, names)],
        *[pl.col(name).alias(f'{role}_{name}') for name in ROLE_ANNOTATIONS],
    )
    frame = frame.with_columns(pl.lit(role).alias('__acs_role'),
                               pl.col(state).cast(pl.String).alias('__acs_state'),
                               pl.col(area).cast(pl.String).alias('__acs_area'))
    frame = _join(frame, own, names)
    _require_matched(frame, f'{role}_area_lookup_id')
    summary = factors.county.group_by('factor_key').agg(
        pl.col('intersection_population').gt(0).sum().gt(1).alias('__acs_split')
    ).rename({'factor_key': f'{role}_factor_key'})
    frame = _join(frame, summary, [f'{role}_factor_key'])
    applicable = pl.col(f'{role}_area_status').eq('applicable')
    return frame.with_columns(
        applicable.alias(f'{role}_flag_geographic_allocation'),
        applicable.and_(pl.col('__acs_split').fill_null(False)).alias(
            f'{role}_flag_fractional_split'),
    ).drop('__acs_role', '__acs_state', '__acs_area', '__acs_split')


def _with_source_flags(frame, source):
    names = frame.collect_schema().names()
    variables = {v['name']: v for v in source.ddi.get('variables', [])}
    used = False
    for field, prefix in [('QIND', 'industry'), ('QOCC', 'occupation'),
                          ('QMIGRAT1', 'migration')]:
        categories = variables.get(field, {}).get('categories', [])
        labels = {str(c['value']): c.get('label') for c in categories}
        allocated_codes = [code for code, label in labels.items() if label == 'Allocated']
        zero_label = {'QIND': 'Original entry or Inapplicable (not in universe)',
                      'QOCC': 'Entered as written', 'QMIGRAT1': 'Not allocated'}[field]
        available = field in names and bool(categories)
        if available:
            used = True
            value = pl.col(field).cast(pl.String)
            allocated = value.is_in(allocated_codes).fill_null(False)
            ambiguous_zero = value.eq('0').fill_null(False) if labels.get('0') == zero_label else (
                pl.lit(False))
            status = (pl.when(allocated).then(pl.lit('allocated')).when(ambiguous_zero)
                      .then(pl.lit('not_allocated_or_niu')).otherwise(pl.lit('unavailable')))
        else:
            allocated, status = pl.lit(False), pl.lit('unavailable')
        frame = frame.with_columns(
            status.alias(f'{prefix}_source_allocation_status'),
            pl.when(allocated).then(pl.lit(True)).otherwise(pl.lit(None, dtype=pl.Boolean)).alias(
                f'{prefix}_source_allocated'),
        )
    references = sorted({f'ddi:sha256:{r["sha256"]}' for r in source.raw_citations
                         if str(r['path']).endswith('.xml')}) if used else []
    return frame.with_columns(pl.lit(references, dtype=pl.List(pl.String)).alias(
        'source_flag_reference_ids'))


def annotate_source(source: SourceInput, code_lookup: pl.DataFrame,
                    area_lookup: pl.DataFrame, factors: FactorTables) -> pl.LazyFrame:
    '''Join unique small interpretations while preserving the complete person prefix.'''
    frame = indexed_source(source)
    original_names = pl.scan_parquet(source.parquet).collect_schema().names()
    validate_table('code', code_lookup)
    validate_table('area', area_lookup)
    observed = observed_area_keys({source.delivery_id: source})
    own_areas = area_lookup.join(observed.select(list(NATURAL_KEYS['area'])),
                                 on=list(NATURAL_KEYS['area']), how='semi', nulls_equal=True)
    validate_area_lookup(own_areas.sort(list(NATURAL_KEYS['area']), nulls_last=False),
                         observed, factors)
    frame = _with_identity(frame, source)
    for args in [('industry', 'naics', 'IND', 'INDNAICS'),
                 ('occupation', 'soc', 'OCC', 'OCCSOC')]:
        frame = _with_code(frame, code_lookup, *args)
    for role in ROLE_COLUMNS:
        frame = _with_role(frame, area_lookup, factors, role)
    frame = _with_source_flags(frame, source)
    return frame.select(original_names + list(ANNOTATION_SCHEMA)).cast(
        {name: dtype for name, dtype in ANNOTATION_SCHEMA.items()})


def require_original_prefix(source: SourceInput, companion: Path) -> dict:
    '''Compare bounded batches for exact original order, types and multiplicity.'''
    safe_path(companion)
    expected = pl.scan_parquet(source.parquet)
    actual = pl.scan_parquet(companion)
    names = expected.collect_schema().names()
    if actual.collect_schema().names()[:len(names)] != names:
        raise ValueError('original ordered schema prefix changed')
    result = compare_ordered(expected, actual.select(names))
    if not result['schema_equal'] or not result['values_equal']:
        raise ValueError('original source values, types, order or multiplicity changed')
    return result


def _validate_fidelity(source, companion):
    prefix = require_original_prefix(source, companion)
    expected_schema = companion_schema(dict(pl.scan_parquet(source.parquet).collect_schema()))
    actual = pl.scan_parquet(companion)
    if list(actual.collect_schema().items()) != list(expected_schema.items()):
        raise ValueError('companion ordered schema differs')
    expected_identity = indexed_source(source).select('source_row', 'source_parquet_sha256')
    identity = compare_ordered(expected_identity, actual.select(
        'source_row', 'source_parquet_sha256'))
    if not identity['values_equal'] or not identity['schema_equal']:
        raise ValueError('companion ordinal identity or source hash differs')
    return prefix


def write_companion(frame: pl.LazyFrame, source: SourceInput, destination: Path) -> dict:
    '''Sink exclusively into caller-owned staging and reread full prefix/identity fidelity.

    The caller supplies lookups to validate_companion for complete semantic validation;
    this fixed writer interface deliberately carries no hidden lookup context.
    '''
    safe_path(destination)
    partial = destination.with_name(destination.name + '.part')
    safe_path(partial)
    if destination.exists() or partial.exists():
        raise FileExistsError(destination)
    stream = destination.open('xb')
    try:
        with stream:
            frame.sink_parquet(stream, maintain_order=True)
        _validate_fidelity(source, destination)
        return target_io.file_record(destination)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise


def validate_companion(source: SourceInput, companion: Path, code_lookup: pl.DataFrame,
                       area_lookup: pl.DataFrame, factors: FactorTables) -> dict:
    '''Reconstruct and compare every annotation with bounded ordered batch streams.'''
    prefix = _validate_fidelity(source, companion)
    expected = annotate_source(source, code_lookup, area_lookup, factors)
    result = compare_ordered(expected, pl.scan_parquet(companion))
    if not result['schema_equal'] or not result['values_equal']:
        raise ValueError('companion annotations contradict exact mapping/source evidence')
    return {**prefix, 'annotations_equal': True}


def companion_diagnostics(source: SourceInput, companion: Path) -> dict:
    '''Return aggregate partitions and independent overlapping true/false/null counts.'''
    _validate_fidelity(source, companion)
    frame = pl.scan_parquet(companion)
    rows = frame.select(pl.len()).collect().item()
    primary = {}
    statuses = [f'{p}_mapping_status' for p in ('industry', 'occupation')]
    statuses += [f'{r}_area_status' for r in ROLE_COLUMNS]
    statuses += [f'{p}_source_allocation_status' for p in ('industry', 'occupation', 'migration')]
    for name in statuses:
        counts = frame.group_by(name).agg(pl.len().alias('rows')).collect()
        primary[name] = {row[name]: row['rows'] for row in counts.sort(name).iter_rows(named=True)}
        if None in primary[name] or sum(primary[name].values()) != rows:
            raise ValueError('primary-status partition does not reconcile')
    flag_names = [name for name, dtype in ANNOTATION_SCHEMA.items() if dtype == pl.Boolean]
    counts = frame.select(
        *[expression for name in flag_names for expression in (
            pl.col(name).eq(True).sum().alias(name + '__true'),
            pl.col(name).eq(False).sum().alias(name + '__false'),
            pl.col(name).null_count().alias(name + '__null'),
        )]
    ).collect().row(0, named=True)
    flags = {name: {value: counts[name + '__' + value] for value in ('true', 'false', 'null')}
             for name in flag_names}
    partitions = frame.group_by('acs_profile', 'acs_sample_id', 'acs_release_year',
                               'acs_component_year').agg(pl.len().alias('rows')).collect().sort(
                                   'acs_profile', 'acs_sample_id', 'acs_release_year',
                                   'acs_component_year').to_dicts()
    if sum(part['rows'] for part in partitions) != rows or any(
        sum(counts.values()) != rows for counts in flags.values()
    ):
        raise ValueError('source/component or provenance counts do not reconcile')
    return {'rows': rows, 'primary_statuses': primary, 'provenance_flags': flags,
            'partitions': partitions}
