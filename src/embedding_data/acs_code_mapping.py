'''Scheme-aware, unweighted classification possibilities for verified ACS inputs.'''

import re

import polars as pl

from embedding_data.acs_code_references import CodeEvidence, validate_paired_keys
from embedding_data.acs_mapping_contract import (
    CODE_SCHEMA,
    NATURAL_KEYS,
    SourceInput,
    lookup_id,
    validate_table,
)
from embedding_data.acs_mapping_inputs import SelectedInputs
from embedding_data.classification_tables import naics_tables
from embedding_data.naics_relationships import candidates

KEY = list(NATURAL_KEYS['code'])
SAMPLES = {'core': ('us2023a', 'us2024a'), 'vintage': ('us2022a',),
           'five_year': ('us2024c',)}


def scheme_for(profile: str, sample_id: str, release_year: int,
               component_year: int) -> dict[str, str | int | bool]:
    '''Keep delivered classification and interview-vintage recoding independent.'''
    product = profile.removeprefix('acs/')
    if (sample_id not in SAMPLES.get(product, ()) or release_year != int(sample_id[2:6])
            or (product == 'five_year' and component_year not in range(2020, 2025))
            or (product != 'five_year' and component_year != release_year)):
        raise ValueError('unsupported ACS sample/product/release/component identity')
    native = 2017 if release_year == 2022 else 2022
    interview = 2017 if component_year < 2023 else 2022
    return dict(industry_delivered_scheme=f'naics{native}',
                industry_interview_scheme=f'naics{interview}',
                occupation_delivered_scheme='soc2018', native_industry_vintage=native,
                native_occupation_vintage=2018,
                flag_source_industry_recoded=native != interview)


def source_sample_mapping(source: SourceInput) -> dict[str, str]:
    '''Resolve selected SAMPLE values through positive delivered DDI product labels.'''
    product = source.profile.removeprefix('acs/')
    requested = set(source.definition['samples'])
    if product not in SAMPLES or requested != set(SAMPLES[product]):
        raise ValueError('source sample definition differs from supported ACS product')
    categories = [c for v in source.ddi.get('variables', []) if v['name'] == 'SAMPLE'
                  for c in v.get('categories', [])]
    numeric = pl.scan_parquet(source.parquet).collect_schema()['SAMPLE'].is_integer()
    mapping = {}
    for sample in sorted(requested):
        label = ('2020-2024, ACS 5-year' if product == 'five_year'
                 else f'{sample[2:6]} ACS')
        matched = [c for c in categories if c['label'] == label]
        if len(matched) != 1:
            raise ValueError('missing or ambiguous DDI SAMPLE product identity')
        value = str(matched[0]['value'])
        if not re.fullmatch('[0-9]+', value):
            raise ValueError('malformed DDI SAMPLE category value')
        value = str(int(value)) if numeric else value
        category_values = [
            str(int(c['value'])) if numeric else str(c['value'])
            for c in categories if re.fullmatch('[0-9]+', str(c['value']))
        ]
        if category_values.count(value) != 1:
            raise ValueError('ambiguous DDI SAMPLE category value')
        if value in mapping:
            raise ValueError('duplicate DDI SAMPLE category value')
        mapping[value] = sample
    return mapping


def _token(value, *, paired=False):
    if value is None:
        return None
    value = str(value).strip(' ')
    if paired:
        if not re.fullmatch('[0-9]{1,4}', value):
            raise ValueError('malformed paired Census code')
        return value.zfill(4)
    if not re.fullmatch('[0-9]{1,6}(?:[MPSZXY][0-9MPSZXY]*)?', value):
        raise ValueError('malformed classification token')
    return value


def _normalized_keys(frame):
    return frame.with_columns(
        pl.col('source_token').map_elements(_token, return_dtype=pl.String),
        pl.col('paired_census_code').map_elements(
            lambda v: _token(v, paired=True), return_dtype=pl.String),
    )


def observed_code_keys(sources: dict[str, SourceInput]) -> pl.DataFrame:
    '''Collect grouped small keys only; no person-level materialization or expansion.'''
    records = []
    for source in sources.values():
        mapping = source_sample_mapping(source)
        scan = pl.scan_parquet(source.parquet)
        schema = scan.collect_schema()
        if not {'YEAR', 'SAMPLE', 'IND', 'INDNAICS', 'OCC', 'OCCSOC'}.issubset(schema):
            raise ValueError('missing source classification or identity columns')
        five_year = source.profile.removeprefix('acs/') == 'five_year'
        if five_year and 'MULTYEAR' not in schema:
            raise ValueError('missing five-year component identity')
        for system, pair, token in [('naics', 'IND', 'INDNAICS'), ('soc', 'OCC', 'OCCSOC')]:
            grouped = scan.select(
                pl.col('YEAR').alias('release_year'),
                (pl.col('MULTYEAR') if five_year else pl.col('YEAR')).alias('component_year'),
                pl.col('SAMPLE').cast(pl.String).alias('sample'),
                pl.col(pair).cast(pl.String).alias('paired_census_code'),
                pl.col(token).cast(pl.String).alias('source_token'),
            ).group_by(pl.all()).agg(pl.len().cast(pl.UInt64).alias('rows')).collect()
            for row in grouped.iter_rows(named=True):
                sample = mapping.get(row.pop('sample'))
                if sample is None:
                    raise ValueError('observed SAMPLE lacks selected DDI identity')
                schemes = scheme_for(
                    source.profile, sample, row['release_year'], row['component_year'])
                records.append({**row, 'profile': source.profile, 'sample_id': sample,
                                'system': system, 'source_scheme': schemes[
                                    'industry_delivered_scheme' if system == 'naics'
                                    else 'occupation_delivered_scheme'],
                                'flag_source_industry_recoded':
                                    schemes['flag_source_industry_recoded']})
    schema = {'release_year': pl.Int64, 'component_year': pl.Int64,
              'paired_census_code': pl.String, 'source_token': pl.String, 'rows': pl.UInt64,
              'profile': pl.String, 'sample_id': pl.String, 'system': pl.String,
              'source_scheme': pl.String, 'flag_source_industry_recoded': pl.Boolean}
    result = _normalized_keys(pl.DataFrame(records, schema=schema))
    groups = [name for name in schema if name != 'rows']
    return result.group_by(groups).agg(pl.col('rows').sum()).select(list(schema)).sort(
        ['profile', 'sample_id', 'release_year', 'component_year', *KEY], nulls_last=False)


def common_path_node(paths: list[list[str]]) -> str | None:
    '''Deepest supported ancestor; disjoint classification roots have none.'''
    common = []
    for level in zip(*paths):
        if len(set(level)) != 1:
            break
        common.append(level[0])
    return common[-1] if common else None


def _classification_context(selected, needs_relations):
    native = pl.read_parquet(selected.codes['naics_native_nodes'])
    soc = pl.read_parquet(selected.codes['soc_nodes'])
    paths = dict(pl.read_parquet(selected.codes['code_paths']).iter_rows())
    for vintage in native['vintage'].unique():
        table = native.filter(pl.col('vintage').eq(vintage))
        native_paths = naics_tables(table.select('vintage', 'code', 'title'), vintage)[2]
        paths.update(dict(native_paths.iter_rows()))
    nodes = {(r['system'], r['vintage'], r['code']): r['node_id']
             for frame in (native, soc) for r in frame.iter_rows(named=True)}
    relations = pl.read_parquet(selected.codes['naics_concordance']) if needs_relations else None
    return nodes, paths, relations


def build_code_lookup(observed: pl.DataFrame, evidence: CodeEvidence,
                      selected: SelectedInputs) -> pl.DataFrame:
    '''Resolve every native possibility through complete official classification paths.'''
    keys = (_normalized_keys(observed.select(KEY)).unique()
            .filter(pl.col('source_token').is_not_null()))
    validate_paired_keys(keys, evidence)
    needs_relations = keys.filter(pl.col('source_scheme').eq('naics2017')).height > 0
    nodes, paths, relations = _classification_context(selected, needs_relations)
    metadata = {tuple(row[name] for name in KEY): row
                for row in evidence.metadata.iter_rows(named=True)}
    records = []
    for key in keys.sort(KEY).iter_rows():
        row = dict(metadata[key])
        system, native = row['system'], row['native_vintage']
        canonical = 2022 if system == 'naics' else 2018
        row.update(code_lookup_id=lookup_id(key), canonical_vintage=canonical,
                   flag_vintage_crosswalk=native != canonical,
                   canonical_scalar_code=None, canonical_scalar_node_id=None,
                   canonical_common_node_id=None, canonical_finest_candidates=[],
                   canonical_candidate_paths=[])
        if row['mapping_status'] == 'documented_special':
            if (key != ('soc', 'soc2018', '9830', '559830') or not row['special_reason']
                    or not row['reference_locators'] or row['native_finest_candidates']):
                raise ValueError('unsupported special classification evidence')
            row['native_node_id'] = None
        else:
            members = row['native_finest_candidates']
            if not members:
                raise ValueError('uncovered native classification category')
            canonical_members = sorted({target for member in members for target in (
                candidates(relations, native, member, canonical) if native != canonical
                else [member])})
            if not canonical_members:
                raise ValueError('uncovered canonical classification relation')
            try:
                native_paths = [paths[nodes[system, native, code]] for code in members]
                canonical_paths = [paths[nodes[system, canonical, code]]
                                   for code in canonical_members]
            except KeyError as error:
                raise ValueError('unsupported classification node/path') from error
            row['native_node_id'] = row['native_node_id'] or common_path_node(native_paths)
            row['canonical_finest_candidates'] = canonical_members
            row['canonical_candidate_paths'] = canonical_paths
            row['canonical_common_node_id'] = common_path_node(canonical_paths)
            scalar = (row['aggregation_type'] == 'finest' and not row['flag_aggregate']
                      and not row['flag_partial'] and not row['flag_exception']
                      and not row['flag_reference_ambiguity'] and len(members) == 1
                      and len(canonical_members) == 1)
            if scalar and native != canonical:
                scalar = candidates(relations, canonical, canonical_members[0], native) == members
            if scalar:
                row['canonical_scalar_code'] = canonical_members[0]
                row['canonical_scalar_node_id'] = canonical_paths[0][-1]
        records.append(row)
    result = pl.DataFrame(records, schema=CODE_SCHEMA).sort(KEY, nulls_last=False)
    validate_table('code', result)
    return result


def validate_code_lookup(frame: pl.DataFrame, evidence: CodeEvidence,
                         selected: SelectedInputs) -> None:
    '''Rebuild every asserted candidate, path, scalar and provenance field.'''
    validate_table('code', frame)
    expected = build_code_lookup(frame.select(KEY), evidence, selected)
    if not frame.equals(expected):
        raise ValueError('code lookup contradicts reconstructed classification evidence')
