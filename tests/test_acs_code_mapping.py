'''Scheme-aware ACS classification regressions; all reads are offline.'''
from copy import deepcopy
from dataclasses import replace

import polars as pl
import pytest
from acs_mapping_fixtures import FixtureCodeCase
from code_fixtures import pair_sheet, toy_reference_tables
from test_acs_code_references import (  # noqa: F401 - shared public reference fixtures
    code_originals,
    graphs,
    offline,
    public_monkeypatch,
)
from test_acs_code_references import (
    evidence as evidence,
)
from test_acs_code_references import (
    selected as selected,
)

from embedding_data import target_io
from embedding_data.acs_code_mapping import (
    build_code_lookup,
    common_path_node,
    observed_code_keys,
    scheme_for,
    validate_code_lookup,
)
from embedding_data.acs_code_references import CodeEvidence, _metadata
from embedding_data.acs_mapping_contract import SourceInput
from embedding_data.naics_relationships import parse_concordance, validate_relationships

@pytest.fixture
def split_case(tmp_path, evidence, selected):
    nodes, relations, paths = toy_reference_tables()
    codes = dict(selected.codes)
    for name, table in [('naics_native_nodes', nodes), ('naics_concordance', relations),
                        ('code_paths', paths)]:
        codes[name] = tmp_path / (name + '.parquet')
        table.write_parquet(codes[name])
    metadata = _metadata('naics', 'naics2017', '0170', '111112', '111112', ['111112'],
                         nodes.filter(pl.col('vintage').eq(2017)), ['synthetic'], ['toy split'])
    provenance = deepcopy(selected.provenance)
    provenance['codes']['tables'].update(
        {name: target_io.file_record(file) for name, file in codes.items()})
    native = pl.DataFrame([metadata], schema=evidence.metadata.schema)
    member = {name: metadata.get(name) for name in evidence.membership.columns}
    member['native_finest_code'] = '111112'
    return FixtureCodeCase(native.select('system', 'source_scheme', 'paired_census_code',
                                         'source_token'),
                           CodeEvidence(pl.DataFrame([member], schema=evidence.membership.schema),
                                        native, {}),
                           replace(selected, codes=codes, provenance=provenance))


def test_same_code_content_change_traverses_the_full_relation(split_case):
    row = split_case.build_lookup().row(0, named=True)
    assert row['canonical_finest_candidates'] == ['111112', '111113']
    assert row['flag_vintage_crosswalk'] is True
    assert row['canonical_scalar_node_id'] is None


def test_documented_special_has_no_classification_claim(evidence, selected):
    observed = evidence.metadata.filter(pl.col('source_token').eq('559830')).select(
        'system', 'source_scheme', 'paired_census_code', 'source_token')
    row = FixtureCodeCase(observed, evidence, selected).build_lookup().row(0, named=True)
    assert row['mapping_status'] == 'documented_special'
    for field in ('native_finest_candidates', 'canonical_finest_candidates',
                  'canonical_candidate_paths'):
        assert row[field] == []
    for field in ('native_node_id', 'canonical_scalar_node_id', 'canonical_common_node_id'):
        assert row[field] is None
    assert row['special_reason'] and row['reference_locators']


@pytest.mark.parametrize('profile,sample,year,component,vintage,recoded', [
    ('vintage', 'us2022a', 2022, 2022, 2017, False),
    ('core', 'us2023a', 2023, 2023, 2022, False),
    ('core', 'us2024a', 2024, 2024, 2022, False),
    *[('five_year', 'us2024c', 2024, y, 2022, y < 2023) for y in range(2020, 2025)],
])
def test_schemes(profile, sample, year, component, vintage, recoded):
    result = scheme_for(profile, sample, year, component)
    assert result['industry_delivered_scheme'] == f'naics{vintage}'
    assert result['industry_interview_scheme'] == f'naics{2017 if component < 2023 else 2022}'
    assert result['occupation_delivered_scheme'] == 'soc2018'
    assert result['native_occupation_vintage'] == 2018
    assert result['flag_source_industry_recoded'] is recoded


@pytest.mark.parametrize('args', [('core','us2022a',2022,2022),
    ('five_year','us2024c',2024,2019), ('core','us2024a',2024,2023)])
def test_invalid_sample_metadata_fails(args):
    with pytest.raises(ValueError):
        scheme_for(*args)


@pytest.mark.parametrize('bad', ['11 1112', '+111112', '111112.0', '\t111112',
                                 '111112\n', '111112a', '11111222'])
def test_malformed_token_fails(split_case, bad):
    with pytest.raises(ValueError):
        build_code_lookup(split_case.observed.with_columns(pl.lit(bad).alias('source_token')),
                          split_case.evidence, split_case.selected)


def test_padding_normalizes_keys_only(split_case):
    observed = split_case.observed.with_columns(pl.lit(' 111112 ').alias('source_token'),
                                                pl.lit('170').alias('paired_census_code'))
    result = build_code_lookup(observed, split_case.evidence, split_case.selected)
    assert result['source_token'].to_list() == ['111112']
    assert observed['source_token'].to_list() == [' 111112 ']


def test_lookup_validator_reconstructs_assertions(split_case):
    result = split_case.build_lookup()
    validate_code_lookup(result, split_case.evidence, split_case.selected)
    for field, value in [('flag_partial', True), ('canonical_scalar_code', '111112'),
                         ('canonical_finest_candidates', ['111112'])]:
        with pytest.raises(ValueError):
            validate_code_lookup(result.with_columns(pl.lit(value).alias(field)),
                                 split_case.evidence, split_case.selected)


def test_public_partial_singletons_and_exact_finest(evidence, selected):
    observed = evidence.metadata.filter(pl.col('source_scheme').eq('naics2022')).select(
        'system', 'source_scheme', 'paired_census_code', 'source_token')
    result = build_code_lookup(observed, evidence, selected)
    partial = result.filter(pl.col('source_token').eq('2212P')).row(0, named=True)
    assert partial['flag_partial'] and partial['flag_aggregate']
    assert partial['canonical_scalar_code'] is None
    assert partial['aggregation_reason_status'] == 'unknown'
    finest = result.filter(pl.col('aggregation_type').eq('finest'))
    assert finest['canonical_scalar_code'].null_count() == 0


def test_roots_without_common_ancestor():
    assert common_path_node([['a', 'b'], ['x', 'y']]) is None
    assert common_path_node([['a', 'b'], ['a', 'c']]) == 'a'


def test_observed_keys_preserve_partitions_counts_and_raw(tmp_path):
    raw = pl.DataFrame({'YEAR': [2024]*3, 'SAMPLE': [202401]*3,
                        'IND': [190]*3, 'INDNAICS': [' 113M ', ' 113M ', '113M'],
                        'OCC': [10]*3, 'OCCSOC': ['1110XX']*3})
    file = tmp_path / 'source.parquet'
    raw.write_parquet(file)
    source = SourceInput('core', 'fixture', file, {}, [],
                         {'samples': {'us2023a': {}, 'us2024a': {}}},
                         {'variables': [{'name': 'SAMPLE', 'categories': [
                             {'value': '202301', 'label': '2023 ACS'},
                             {'value': '202401', 'label': '2024 ACS'}]}]})
    result = observed_code_keys({'core': source})
    assert result.height == 2
    assert result['rows'].to_list() == [3, 3]
    assert result['source_token'].to_list() == ['113M', '1110XX']
    assert 'flag_source_industry_recoded' in result.columns
    assert raw.equals(pl.read_parquet(file))


@pytest.mark.parametrize('token', ['999920', '559831', '000000', '999999'])
def test_unapproved_specials_fail(evidence, selected, token):
    observed = evidence.metadata.filter(pl.col('source_token').eq('559830')).select(
        'system', 'source_scheme', 'paired_census_code', 'source_token'
    ).with_columns(pl.lit(token).alias('source_token'))
    with pytest.raises(ValueError):
        build_code_lookup(observed, evidence, selected)


def test_all_soc_uses_selected_paths_and_retains_suffixes(evidence, selected):
    observed = evidence.metadata.filter(pl.col('system').eq('soc')).select(
        'system', 'source_scheme', 'paired_census_code', 'source_token')
    result = build_code_lookup(observed, evidence, selected)
    assert result['flag_vintage_crosswalk'].any() is False
    row = result.filter(pl.col('source_token').eq('1110XX')).row(0, named=True)
    assert row['canonical_finest_candidates'] == ['11-1011', '11-1031']
    assert row['aggregation_reasons'] == ['disclosure']
    assert row['canonical_common_node_id'] == row['native_node_id']
    selected_paths = dict(pl.read_parquet(selected.codes['code_paths']).iter_rows())
    for paths in result['canonical_candidate_paths'].to_list():
        for path in paths:
            assert path == selected_paths[path[-1]]


def _replace_native_category(case, code):
    metadata = case.evidence.metadata.with_columns(
        pl.lit(code).alias('source_token'),
        pl.lit([code]).alias('native_finest_candidates'),
        pl.lit(f'naics:2017:national_industry:{code}').alias('native_node_id'))
    member = case.evidence.membership.with_columns(
        pl.lit(code).alias('source_token'), pl.lit(code).alias('native_finest_code'),
        pl.lit(f'naics:2017:national_industry:{code}').alias('native_node_id'))
    return FixtureCodeCase(metadata.select('system', 'source_scheme', 'paired_census_code',
                                           'source_token'),
                           CodeEvidence(member, metadata, {}), case.selected)


def test_singleton_crosswalk_keeps_flag_with_supported_scalar(split_case):
    row = _replace_native_category(split_case, '111111').build_lookup().row(0, named=True)
    assert row['flag_vintage_crosswalk'] is True
    assert row['canonical_scalar_code'] == '111111'


def test_reverse_multiple_sources_prevent_scalar(split_case):
    case = _replace_native_category(split_case, '111111')
    file = case.selected.codes['naics_concordance']
    relation = pl.read_parquet(file)
    pair = relation.filter(pl.col('source_vintage').eq(2017))
    pairs = pair.select('source_code', 'target_code').rows() + [('111112', '111111')]
    altered = pl.concat([
        relation.filter(pl.col('source_vintage').ne(2017)),
        parse_concordance(pair_sheet(2017, 2022, pairs), 2017, 2022, 'synthetic_merge.xlsx'),
    ])
    validate_relationships(altered, pl.read_parquet(case.selected.codes['naics_native_nodes']))
    altered.write_parquet(file)
    case.selected.provenance['codes']['tables']['naics_concordance'] = target_io.file_record(file)
    row = case.build_lookup().row(0, named=True)
    assert row['canonical_finest_candidates'] == ['111111']
    assert row['canonical_scalar_code'] is None


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'prcs', 'unmatched', 'year'])
def test_ddi_identity_mismatches_fail(tmp_path, mutation):
    categories = [{'value': '123', 'label': '2022 ACS'}]
    sample, year = 123, 2022
    if mutation == 'missing':
        categories = []
    elif mutation == 'duplicate':
        categories *= 2
    elif mutation == 'prcs':
        categories[0]['label'] = '2022 PRCS'
    elif mutation == 'unmatched':
        sample = 124
    else:
        year = 2023
    file = tmp_path / 'identity.parquet'
    pl.DataFrame({'SAMPLE': [sample], 'YEAR': [year], 'IND': [170],
                  'INDNAICS': ['111112'], 'OCC': [10], 'OCCSOC': ['1110XX']}).write_parquet(file)
    source = SourceInput('acs/vintage', 'fixture', file, {}, [],
                         {'samples': {'us2022a': {}}},
                         {'variables': [{'name': 'SAMPLE', 'categories': categories}]})
    with pytest.raises(ValueError):
        observed_code_keys({'acs/vintage': source})


def test_five_year_components_retain_source_recoding_and_null_flags(tmp_path):
    file = tmp_path / 'five.parquet'
    pl.DataFrame({'SAMPLE': ['007']*2, 'YEAR': [2024]*2, 'MULTYEAR': [2022, 2023],
                  'IND': ['0190']*2, 'INDNAICS': ['113M']*2,
                  'OCC': ['0010']*2, 'OCCSOC': ['1110XX']*2}).write_parquet(file)
    source = SourceInput('acs/five_year', 'fixture', file, {}, [],
                         {'samples': {'us2024c': {}}},
                         {'variables': [{'name': 'SAMPLE', 'categories': [
                             {'value': '007', 'label': '2020-2024, ACS 5-year'}]}]})
    result = observed_code_keys({'acs/five_year': source})
    assert result['rows'].sum() == 4
    assert result.filter(pl.col('component_year').eq(2022))[
        'flag_source_industry_recoded'].all()
    assert not result.filter(pl.col('component_year').eq(2023))[
        'flag_source_industry_recoded'].any()
    assert 'QIND' not in result.columns


@pytest.mark.parametrize('bad', ['12345', '-170', '170.0', '01 0', '\t170'])
def test_malformed_paired_keys_fail(split_case, bad):
    with pytest.raises(ValueError):
        build_code_lookup(split_case.observed.with_columns(pl.lit(bad).alias('paired_census_code')),
                          split_case.evidence, split_case.selected)


def test_numeric_coarse_singleton_retains_declared_native_depth(evidence, selected):
    observed = evidence.metadata.filter(
        pl.col('source_scheme').eq('naics2022').and_(pl.col('source_token').eq('22132'))
    ).select('system', 'source_scheme', 'paired_census_code', 'source_token')
    row = build_code_lookup(observed, evidence, selected).row(0, named=True)
    assert row['canonical_finest_candidates'] == ['221320']
    assert row['native_node_id'] == 'naics:2022:industry:22132'
    assert row['flag_aggregate'] is True
    assert row['canonical_scalar_code'] is None


def test_conflicting_ddi_category_value_fails(tmp_path):
    file = tmp_path / 'ambiguous-value.parquet'
    pl.DataFrame({'SAMPLE': [123], 'YEAR': [2022], 'IND': [170],
                  'INDNAICS': ['111112'], 'OCC': [10], 'OCCSOC': ['1110XX']}).write_parquet(file)
    source = SourceInput('acs/vintage', 'fixture', file, {}, [],
                         {'samples': {'us2022a': {}}},
                         {'variables': [{'name': 'SAMPLE', 'categories': [
                             {'value': '123', 'label': '2022 ACS'},
                             {'value': '0123', 'label': '2022 PRCS'}]}]})
    with pytest.raises(ValueError, match='ambiguous'):
        observed_code_keys({'acs/vintage': source})
