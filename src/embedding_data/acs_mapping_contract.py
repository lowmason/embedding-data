'''Frozen typed ACS mapping schemas, natural keys and selection records.'''

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import polars as pl

S, I, F, B = pl.String, pl.Int64, pl.Float64, pl.Boolean  # noqa: E741 - frozen schema notation
LS = pl.List(S)
LLS = pl.List(LS)

CODE_SCHEMA = {
    'code_lookup_id': S, 'system': S, 'source_scheme': S,
    'native_vintage': I, 'canonical_vintage': I,
    'paired_census_code': S, 'source_token': S, 'mapping_status': S,
    'native_node_id': S, 'native_finest_candidates': LS,
    'canonical_finest_candidates': LS, 'canonical_candidate_paths': LLS,
    'canonical_common_node_id': S, 'canonical_scalar_code': S,
    'canonical_scalar_node_id': S, 'aggregation_type': S,
    'aggregation_markers': LS, 'aggregation_reason_status': S,
    'aggregation_reasons': LS, 'special_reason': S,
    'flag_aggregate': B, 'flag_partial': B, 'flag_exception': B,
    'flag_vintage_crosswalk': B, 'flag_reference_ambiguity': B,
    'reference_ids': LS, 'reference_locators': LS, 'rule_version': S,
}
AREA_SCHEMA = {
    'area_lookup_id': S, 'profile': S, 'sample_id': S,
    'release_year': I, 'component_year': I, 'role': S,
    'source_state_code': S, 'source_area_code': S,
    'state_fips': S, 'area_code': S, 'area_type': S,
    'puma_vintage': I, 'area_status': S, 'status_reason': S,
    'factor_key': S, 'flag_source_geography_recoded': B,
    'source_allocation_evidence_status': S,
    'reference_ids': LS, 'reference_locators': LS, 'rule_version': S,
}
COUNTY_FACTOR_SCHEMA = {
    'factor_key': S, 'area_type': S, 'state_fips': S, 'area_code': S,
    'county_geoid': S, 'county_node_id': S,
    'intersection_population': I, 'area_population': I, 'county_population': I,
    'factor': F, 'published_area_factor': F, 'published_county_factor': F,
    'population_year': I, 'puma_vintage': I, 'county_composition_year': I,
    'county_inventory_vintage': I, 'flag_geographic_allocation': B,
    'flag_fractional_split': B, 'reference_ids': LS, 'reference_locators': LS,
}
MSA_FACTOR_SCHEMA = {
    'state_fips': S, 'puma_code': S, 'msa_code': S, 'msa_node_id': S,
    'puma_population': I, 'msa_population': I, 'intersection_population': I,
    'puma_to_msa_factor': F, 'msa_to_puma_factor': F,
    'published_percent_puma': F, 'published_percent_msa': F,
    'population_year': I, 'puma_vintage': I, 'msa_delineation': S,
    'county_inventory_vintage': I, 'flag_geographic_allocation': B,
    'flag_fractional_split': B, 'reference_ids': LS, 'reference_locators': LS,
}
MSA_COVERAGE_SCHEMA = {
    'state_fips': S, 'puma_code': S, 'puma_population': I,
    'msa_population': I, 'non_msa_population': I,
    'msa_fraction': F, 'non_msa_fraction': F,
    'population_year': I, 'puma_vintage': I, 'msa_delineation': S,
    'reference_ids': LS, 'reference_locators': LS,
}

IDENTITY_SCHEMA = {
    'source_parquet_sha256': S, 'source_row': pl.UInt64,
    'acs_profile': S, 'acs_sample_id': S, 'acs_release_year': I,
    'acs_component_year': I, 'industry_delivered_scheme': S,
    'industry_interview_scheme': S, 'occupation_delivered_scheme': S,
    'flag_source_industry_recoded': B,
    'industry_source_allocation_status': S,
    'occupation_source_allocation_status': S,
    'industry_source_allocated': B, 'occupation_source_allocated': B,
    'migration_source_allocation_status': S, 'migration_source_allocated': B,
    'source_flag_reference_ids': LS,
}
CODE_ANNOTATIONS = ('code_lookup_id', 'source_token', 'mapping_status',
    'native_vintage', 'canonical_vintage', 'paired_census_code',
    'native_node_id', 'native_finest_candidates', 'canonical_finest_candidates',
    'canonical_candidate_paths', 'canonical_common_node_id',
    'canonical_scalar_code', 'canonical_scalar_node_id', 'aggregation_type',
    'aggregation_markers', 'aggregation_reason_status', 'aggregation_reasons',
    'special_reason', 'flag_aggregate', 'flag_partial', 'flag_exception',
    'flag_vintage_crosswalk', 'flag_reference_ambiguity',
    'reference_ids', 'reference_locators', 'rule_version')
ROLE_ANNOTATIONS = ('area_lookup_id', 'state_fips', 'area_code', 'area_type',
    'puma_vintage', 'area_status', 'status_reason', 'factor_key',
    'flag_source_geography_recoded', 'source_allocation_evidence_status',
    'reference_ids', 'reference_locators', 'rule_version')
ANNOTATION_SCHEMA = dict(IDENTITY_SCHEMA)
for prefix in ('industry', 'occupation'):
    ANNOTATION_SCHEMA.update({f'{prefix}_{name}': CODE_SCHEMA[name]
                              for name in CODE_ANNOTATIONS})
for prefix in ('residence', 'workplace', 'migration'):
    ANNOTATION_SCHEMA.update({f'{prefix}_{name}': AREA_SCHEMA[name]
                              for name in ROLE_ANNOTATIONS})
    ANNOTATION_SCHEMA.update({f'{prefix}_flag_geographic_allocation': B,
                              f'{prefix}_flag_fractional_split': B})

FORMAT_VERSION = 'acs-mapping-v1'
REFERENCE_VERSION = 'acs-mapping-references-v1'
CODE_RULE_VERSION = 'acs-code-rules-v1'
AREA_RULE_VERSION = 'acs-area-rules-v1'
NATURAL_KEYS = {
    'code': ('system', 'source_scheme', 'paired_census_code', 'source_token'),
    'area': ('profile', 'sample_id', 'release_year', 'component_year', 'role',
             'source_state_code', 'source_area_code'),
    'county_factor': ('area_type', 'state_fips', 'area_code', 'county_geoid'),
    'msa_factor': ('state_fips', 'puma_code', 'msa_code'),
    'msa_coverage': ('state_fips', 'puma_code'),
}


@dataclass(frozen=True)
class SelectionRequest:
    codes_run: str
    codes_outputs_sha256: str
    geography_run: str
    geography_outputs_sha256: str
    ipums_run: str
    ipums_outputs_sha256: str
    ipums_references_receipt_sha256: str


@dataclass(frozen=True)
class SourceInput:
    profile: str
    delivery_id: str
    parquet: Path
    parquet_record: dict
    raw_citations: list[dict]
    definition: dict
    ddi: dict


SCHEMAS = {'code': CODE_SCHEMA, 'area': AREA_SCHEMA, 'county_factor': COUNTY_FACTOR_SCHEMA,
           'msa_factor': MSA_FACTOR_SCHEMA, 'msa_coverage': MSA_COVERAGE_SCHEMA}
NULLABLE = {
    'code': {'native_node_id', 'canonical_common_node_id', 'canonical_scalar_code',
             'canonical_scalar_node_id', 'special_reason'},
    'area': {'source_state_code', 'source_area_code', 'state_fips', 'area_code',
             'factor_key', 'flag_source_geography_recoded'},
    'county_factor': {'published_area_factor', 'published_county_factor'},
    'msa_factor': set(), 'msa_coverage': set(),
}
CODE_STATUSES = frozenset({'mapped', 'documented_special'})
AREA_STATUSES = frozenset({'applicable', 'niu_or_unidentifiable', 'foreign', 'territory',
                           'documented_unavailable'})
AGGREGATION_REASON_STATUSES = frozenset({'documented', 'unknown', 'not_applicable'})
SOURCE_ALLOCATION_STATUSES = frozenset({'allocated', 'not_allocated', 'not_allocated_or_niu',
                                       'not_applicable', 'unavailable'})


def lookup_id(key: list | tuple) -> str:
    '''Hash the complete natural key, preserving JSON null and lexical values.'''
    encoded = json.dumps(list(key), ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def factor_key(area_type: str, state_fips: str, area_code: str) -> str:
    return lookup_id([area_type, state_fips, area_code, 2020])


def companion_schema(source_schema: dict) -> dict:
    if set(source_schema).intersection(ANNOTATION_SCHEMA):
        raise ValueError('source columns collide with annotation suffix')
    return {**source_schema, **ANNOTATION_SCHEMA}


def _validate_lists(frame: pl.DataFrame, schema: dict) -> None:
    for name, dtype in schema.items():
        if not isinstance(dtype, pl.List):
            continue
        for values in frame[name].to_list():
            if values is None or any(value is None for value in values):
                raise ValueError(f'{name}: null list or list element')
            if dtype == LLS:
                if any(any(node is None for node in path) or not path for path in values):
                    raise ValueError(f'{name}: empty path or null path element')
            elif values != sorted(set(values)):
                raise ValueError(f'{name}: list must be sorted and distinct')


def validate_table(kind: str, frame: pl.DataFrame) -> None:
    '''Check ordered schema, nullability, natural-key identity and list invariants.'''
    schema, keys = SCHEMAS[kind], NATURAL_KEYS[kind]
    if list(frame.schema.items()) != list(schema.items()):
        raise ValueError(f'{kind}: ordered schema differs')
    for name in set(schema).difference(NULLABLE[kind]):
        if frame[name].null_count():
            raise ValueError(f'{name}: unexpected null')
    _validate_lists(frame, schema)
    if frame.select(keys).is_duplicated().any():
        raise ValueError(f'{kind}: duplicate natural key')
    if not frame.equals(frame.sort(keys, nulls_last=False)):
        raise ValueError(f'{kind}: natural-key sort differs')
    if kind in ('code', 'area'):
        id_column = f'{kind}_lookup_id'
        expected = [lookup_id(row) for row in frame.select(keys).iter_rows()]
        if frame[id_column].to_list() != expected or frame[id_column].n_unique() != frame.height:
            raise ValueError(f'{kind}: lookup IDs contradict natural keys')
    if kind == 'code':
        for row in frame.iter_rows(named=True):
            if row['mapping_status'] not in CODE_STATUSES:
                raise ValueError('unsupported code mapping status')
            if (row['rule_version'] != CODE_RULE_VERSION or row['aggregation_reason_status']
                    not in AGGREGATION_REASON_STATUSES or not set(row['aggregation_reasons'])
                    .issubset({'category_design', 'disclosure'})):
                raise ValueError('unsupported code rule or aggregation reason')
            if (row['aggregation_reason_status'] != 'documented'
                    and row['aggregation_reasons']):
                raise ValueError('undocumented aggregation status cannot claim reasons')
            if row['mapping_status'] == 'documented_special' and (
                    row['system'] != 'soc' or row['source_token'] != '559830'
                    or not row['special_reason'] or row['native_finest_candidates']
                    or row['canonical_finest_candidates']
                    or any(row[name] is not None for name in (
                        'native_node_id', 'canonical_common_node_id', 'canonical_scalar_code',
                        'canonical_scalar_node_id'))):
                raise ValueError('unsupported documented special')
            candidates = row['canonical_finest_candidates']
            if len(candidates) != len(row['canonical_candidate_paths']):
                raise ValueError('missing canonical candidate paths')
            if row['mapping_status'] == 'mapped' and (
                    not candidates or not row['native_finest_candidates']):
                raise ValueError('mapped code has no native or canonical candidates')
    if kind == 'area':
        if frame.filter(pl.col('rule_version').ne(AREA_RULE_VERSION)).height:
            raise ValueError('unsupported area rule version')
        if not set(frame['area_status']).issubset(AREA_STATUSES):
            raise ValueError('unsupported area status')
        if frame.filter(pl.col('area_status').eq('applicable').ne(
                pl.col('factor_key').is_not_null())).height:
            raise ValueError('area factor key contradicts applicability')
    if kind == 'county_factor':
        missing_published = pl.any_horizontal(
            pl.col('published_area_factor').is_null(),
            pl.col('published_county_factor').is_null())
        if frame.filter(pl.col('area_type').ne('work_migration').and_(missing_published)).height:
            raise ValueError('published county factors may be null only for work_migration')
    if kind in ('area', 'county_factor'):
        applicable = (frame.filter(pl.col('area_status').eq('applicable'))
                      if kind == 'area' else frame)
        for row in applicable.iter_rows(named=True):
            expected = factor_key(row['area_type'], row['state_fips'], row['area_code'])
            if row['factor_key'] != expected:
                raise ValueError('factor key contradicts area identity')
