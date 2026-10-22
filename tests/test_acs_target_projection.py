'''Handwritten supported-leaf and deterministic allocation conservation cases.'''

from dataclasses import replace

import polars as pl
import pytest
from acs_target_fixtures import (
    membership_frame,
    membership_rules,
    membership_units,
    projection_case,
)

from embedding_data.acs_target_contract import PRODUCTS, RESIDUAL_SCHEMA
from embedding_data.acs_target_estimation import aggregate_native, estimate
from embedding_data.acs_target_membership import family_rows
from embedding_data.acs_target_projection import allocate_area_mix, canonical_rows

@pytest.fixture(autouse=True)
def forbid_external_access(monkeypatch):
    import socket

    import dotenv

    def forbidden(*args, **kwargs):
        raise AssertionError('projection tests must remain offline without environment files')

    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)
    monkeypatch.setattr(dotenv, 'load_dotenv', forbidden)


def test_workplace_allocation_keeps_metro_micro_and_no_cbsa_mass():
    case = projection_case()
    allocated, residuals = allocate_area_mix(
        case['native'], case['factors'], case['counties'], case['msa_product'])
    full = allocated.cells.filter((pl.col('replicate') == 0)
                                  & (pl.col('component_year') == 0)).collect()
    assert full.filter(pl.col('unit_b') == case['code_a'])['mass'].sum() == 150.
    published = estimate(allocated)['targets'].collect()
    a_total = published.filter((pl.col('unit_b') == case['code_a'])
                               & (pl.col('measure') == 'annual_average_total'))
    assert a_total['value'].sum() == 75.
    residual = residuals.filter((pl.col('replicate') == 0)
                               & (pl.col('component_year') == 0)
                               & (pl.col('code_unit') == case['code_a'])).collect()
    assert dict(residual.select('residual_type', 'weighted_mass').rows()) == {
        'micropolitan': 25., 'no_cbsa': 60.}
    assert full['n_unweighted'].max() == case['w1_input_count']
    assert full['fractional_support_mass'].to_list() == [1.5, 1.5]
    assert full['sum_exact'].null_count() == full.height
    assert residuals.collect_schema() == RESIDUAL_SCHEMA
    shares = published.filter(pl.col('measure') == 'forward_share')
    assert shares['value'].to_list() == [.5, .5]
    assert all('flag_geographic_allocation' in f for f in published['flags'])
    assert all('allocation_conditional_sampling_se' in f for f in published['flags'])


def test_every_component_and_signed_replicate_conserves_mass():
    case = projection_case()
    county, empty = allocate_area_mix(case['native'], case['factors'], case['counties'],
                                     case['county_product'])
    msa, residuals = allocate_area_mix(case['native'], case['factors'], case['counties'],
                                      case['msa_product'])
    assert empty.collect().is_empty()
    keys = ['component_year', 'replicate', 'unit_b']
    expected = case['native'].cells.with_columns(pl.col('sum_exact').cast(pl.Float64)
                                                .alias('mass')).group_by(keys).agg(pl.col('mass').sum()).collect()
    actual = county.cells.group_by(keys).agg(pl.col('mass').sum()).collect()
    assert actual.sort(keys).equals(expected.sort(keys))
    combined = pl.concat([msa.cells.select(*keys, 'mass'), residuals.select(
        *keys[:2], pl.col('code_unit').alias('unit_b'),
        (pl.col('weighted_mass') * 2).alias('mass'))])
    assert combined.group_by(keys).agg(pl.col('mass').sum()).collect().sort(keys).equals(
        expected.sort(keys))
    assert county.cells.filter(pl.col('unit_a').str.ends_with('00000')).collect().is_empty()
    assert county.cells.filter(pl.col('replicate') == 37).collect()['mass'].min() < 0
    factor_one = county.cells.filter(pl.col('unit_a').str.ends_with('02003')).collect()
    assert all('flag_geographic_allocation' in f for f in factor_one['flags'])


@pytest.mark.parametrize('mutation', ['residence', 'bad_key', 'unknown_county',
    'unknown_cbsa', 'duplicate_county', 'missing', 'all_zero', 'bad_factor'])
def test_reject_invalid_allocation_relations(mutation):
    case = projection_case()
    factors, counties = case['factors'], case['counties']
    if mutation == 'residence':
        factors = factors.with_columns(pl.lit('residence').alias('area_type'))
    elif mutation == 'bad_key':
        factors = factors.with_columns(pl.lit('invalid').alias('factor_key'))
    elif mutation == 'unknown_county':
        counties = counties.filter(pl.col('county_geoid') != '02003')
    elif mutation == 'unknown_cbsa':
        counties = counties.with_columns(pl.when(pl.col('cbsa_type').is_not_null())
            .then(pl.lit('bad')).otherwise(pl.col('cbsa_id')).alias('cbsa_id'))
    elif mutation == 'duplicate_county':
        counties = pl.concat([counties, counties.head(1)])
    elif mutation == 'missing':
        factors = factors.filter(pl.col('state_fips') != '02')
    elif mutation == 'all_zero':
        factors = factors.with_columns(pl.lit(0.).alias('factor'))
    else:
        factors = factors.with_columns(pl.lit(float('nan')).alias('factor'))
    with pytest.raises(ValueError):
        allocate_area_mix(case['native'], factors, counties, case['msa_product'])


def canonical_case(policy='strict', dimension='industry_occupation'):
    product = next(p for p in PRODUCTS if p.view == 'observed'
        and p.dimension == dimension and p.evidence_policy == policy)
    records = [
        {},
        {'industry_canonical_scalar_node_id': None,
         'industry_canonical_finest_candidates': ['111110', '111120']},
        {'industry_canonical_scalar_node_id': None,
         'industry_canonical_finest_candidates': ['111110']},
        {'industry_flag_aggregate': True, 'industry_flag_partial': True},
        {'industry_flag_vintage_crosswalk': True},
        {'flag_source_industry_recoded': True},
        {'occupation_source_allocated': True},
        {'occupation_canonical_scalar_node_id': None, 'OCCSOC': '559830'},
    ]
    frame = membership_frame([r | {'source_row': i} for i, r in enumerate(records)]).with_columns(
        pl.col('acs_component_year').alias('YEAR'),
        pl.col('industry_canonical_scalar_node_id').replace(
            'node:industry-a', 'naics:2022:national_industry:111110'),
        pl.col('occupation_canonical_scalar_node_id').replace(
            'node:occupation-a', 'soc:2018:detailed:111021'))
    rows = family_rows(frame, product, membership_rules(), membership_units())
    nodes = {
        'naics': pl.DataFrame({'node_id': ['naics:2022:national_industry:111110'],
                              'system': ['naics'],
                              'vintage': [2022], 'level': ['national_industry']}),
        'soc': pl.DataFrame({'node_id': ['soc:2018:detailed:111021'], 'system': ['soc'],
                            'vintage': [2018], 'level': ['detailed']})}
    return rows, nodes


@pytest.mark.parametrize('policy,positions', [('strict', [0, 3]),
    ('sensitivity', [0, 3, 4, 5, 6])])
def test_canonical_requires_supported_scalar_and_preserves_flags(policy, positions):
    rows, nodes = canonical_case(policy)
    result = canonical_rows(rows, nodes)
    members = result.members.collect()
    assert members['source_row'].to_list() == positions
    assert result.product.view == 'canonical'
    assert members['unit_a_type'].unique().to_list() == ['naics_national_industry']
    assert members['unit_b_type'].unique().to_list() == ['soc_detailed']
    assert 'industry_flag_aggregate' in members.filter(pl.col('source_row') == 3)['flags'][0]
    aggregates = aggregate_native(result)
    output = estimate(aggregates)
    support = output['support'].filter((pl.col('component_year') == 0)
        & (pl.col('measure') == 'forward_share')).collect()
    assert support['denominator_n_unweighted'][0] == len(positions)
    assert support['native_coverage_n'][0] == 6
    assert support['native_coverage_mass'][0] == 6 * 100.25 / 2
    loss = result.diagnostics.filter((pl.col('partition_kind') == 'coverage')
        & (pl.col('reason') == 'canonical_unsupported_or_policy_excluded')).collect()
    assert loss['n_unweighted'].sum() == 8 - len(positions)


@pytest.mark.parametrize('dimension', ['industry', 'occupation'])
def test_area_mix_requires_only_used_code_support(dimension):
    rows, nodes = canonical_case('sensitivity', dimension)
    projected = canonical_rows(rows, nodes).members.collect()
    assert projected.height == (6 if dimension == 'industry' else 7)


@pytest.mark.parametrize('field,value', [('level', 'sector'), ('system', 'soc'),
                                       ('vintage', 2017)])
def test_scalar_identifier_cannot_override_selected_node_frame(field, value):
    rows, nodes = canonical_case()
    nodes['naics'] = nodes['naics'].with_columns(pl.lit(value).alias(field))
    assert canonical_rows(rows, nodes).members.collect().is_empty()


def test_allocation_rejects_flow_and_canonical_products():
    case = projection_case()
    for product in [next(p for p in PRODUCTS if p.family == 'commuting_flow'),
                    replace(case['msa_product'], view='canonical')]:
        with pytest.raises(ValueError):
            allocate_area_mix(case['native'], case['factors'], case['counties'], product)


def test_projection_diagnostics_have_destination_product_identity():
    rows, nodes = canonical_case()
    result = canonical_rows(rows, nodes)
    assert result.diagnostics.select('view', 'product_id').unique().collect().rows() == [
        ('canonical', result.product.product_id)]
    case = projection_case()
    # Supply real aggregate membership diagnostics, which allocation must retag.
    native = replace(case['native'], diagnostics=rows.diagnostics)
    allocated, _ = allocate_area_mix(native, case['factors'], case['counties'],
                                     case['msa_product'])
    assert allocated.diagnostics.select('view', 'product_id').unique().collect().rows() == [
        ('allocated_msa', case['msa_product'].product_id)]


def test_canonical_annual_baseline_survives_year_without_supported_members():
    rows, nodes = canonical_case('sensitivity')
    year = pl.when(pl.col('source_row') == 0).then(pl.lit(2023, dtype=pl.Int64))\
        .otherwise(pl.lit(2024, dtype=pl.Int64))
    selected = rows.members.filter(pl.col('source_row').is_in([0, 7])).with_columns(
        year.alias('YEAR'), year.alias('acs_component_year'))
    result = canonical_rows(replace(rows, members=selected), nodes)
    aggregates = aggregate_native(result)
    annual = aggregates.denominators.filter((pl.col('component_year') == 2024)
                                           & (pl.col('replicate') == 0)).collect()
    assert annual['n_unweighted'].item() == 0
    assert annual['native_coverage_n'].item() == 1
    assert annual['native_coverage_mass'].item() == 100.25
    published = estimate(aggregates)['support'].filter((pl.col('component_year') == 2024)
        & (pl.col('measure') == 'forward_share')).collect()
    assert published['native_coverage_mass'].item() == 50.125


def test_two_observed_categories_collapse_to_leaf_without_multiplying_positions():
    rows, nodes = canonical_case('sensitivity')
    frame = rows.members.filter(pl.col('source_row').is_in([0, 3])).with_columns(
        pl.when(pl.col('source_row') == 0).then(pl.lit('category-a'))
            .otherwise(pl.lit('category-b')).alias('unit_a'))
    projected = canonical_rows(replace(rows, members=frame), nodes)
    assert projected.members.collect()['source_row'].to_list() == [0, 3]
    full = aggregate_native(projected).cells.filter((pl.col('component_year') == 0)
                                                  & (pl.col('replicate') == 0)).collect()
    assert full.height == 1
    assert full['n_unweighted'].item() == 2
    assert full['sum_exact'].item() == '200.5'


def test_no_metropolitan_membership_produces_empty_msa_without_renormalizing():
    case = projection_case()
    counties = case['counties'].with_columns(
        pl.when(pl.col('cbsa_type') == 'metropolitan').then(pl.lit('micropolitan'))
            .otherwise(pl.col('cbsa_type')).alias('cbsa_type'))
    allocated, residuals = allocate_area_mix(case['native'], case['factors'], counties,
                                             case['msa_product'])
    assert allocated.cells.collect().is_empty()
    assert estimate(allocated)['targets'].collect().is_empty()
    assert residuals.filter((pl.col('component_year') == 0) & (pl.col('replicate') == 0)
                           & (pl.col('code_unit') == case['code_a'])).collect()[
                               'weighted_mass'].sum() == 160.


def test_all_nine_connecticut_planning_regions_remain_counties():
    from embedding_data.acs_mapping_contract import factor_key

    case = projection_case()
    native = replace(case['native'], cells=case['native'].cells.with_columns(
        pl.lit('geography:2020:work_migration_puma:0900100').alias('unit_a'))
        .group_by('unit_a_type', 'unit_a', 'unit_b_type', 'unit_b', 'component_year', 'replicate')
        .agg(pl.col('sum_exact').cast(pl.Float64).sum().cast(pl.String),
             pl.col('n_unweighted').sum(), pl.col('fractional_support_mass').sum(),
             pl.col('flags').first()))
    factors, counties = [], []
    for code in range(110, 191, 10):
        geoid = '09' + str(code)
        factors.append(case['factors'].row(0, named=True) | {
            'factor_key': factor_key('work_migration', '09', '00100'),
            'state_fips': '09', 'area_code': '00100', 'county_geoid': geoid,
            'county_node_id': 'geography:2025:county:' + geoid, 'factor': 1 / 9})
        counties.append(case['counties'].row(0, named=True) | {
            'county_id': 'geography:2025:county:' + geoid, 'county_geoid': geoid})
    allocated, _ = allocate_area_mix(native, pl.DataFrame(factors, schema=case['factors'].schema),
        pl.DataFrame(counties, schema=case['counties'].schema), case['county_product'])
    assert allocated.cells.select('unit_a').unique().collect().height == 9
    full = estimate(allocated)['targets'].filter((pl.col('measure') == 'annual_average_total')
        & (pl.col('unit_b') == case['code_a'])).collect()
    assert full['value'].sum() == pytest.approx(160., rel=0, abs=1e-8)


def test_fresh_process_thread_counts_have_exact_logical_replay(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path

    case = projection_case()
    for name in ['cells', 'denominators', 'diagnostics']:
        getattr(case['native'], name).collect().write_parquet(tmp_path / (name + '.parquet'))
    case['factors'].write_parquet(tmp_path / 'factors.parquet')
    case['counties'].write_parquet(tmp_path / 'counties.parquet')
    script = """
import json, socket, sys
def forbidden(*args, **kwargs):
    raise AssertionError("fresh-process projection must remain offline")
socket.socket.connect = forbidden
socket.socket.connect_ex = forbidden
from pathlib import Path
import polars as pl
from embedding_data.acs_target_contract import PRODUCTS
from embedding_data.acs_target_estimation import AggregateSet, estimate
from embedding_data.acs_target_projection import allocate_area_mix
root = Path(sys.argv[1])
observed = next(p for p in PRODUCTS if p.product_id == sys.argv[2])
product = next(p for p in PRODUCTS if p.product_id == sys.argv[3])
native = AggregateSet(*(pl.scan_parquet(root / (name + '.parquet')) for name in
    ['cells', 'denominators', 'diagnostics']), observed)
allocated, residual = allocate_area_mix(native, pl.read_parquet(root / 'factors.parquet'),
    pl.read_parquet(root / 'counties.parquet'), product)
frames = estimate(allocated) | {'residuals': residual}
print(json.dumps({name: frame.collect().to_dicts() for name, frame in frames.items()},
    sort_keys=True, allow_nan=False))
"""
    results = [subprocess.run([sys.executable, '-c', script, str(tmp_path),
        case['native'].product.product_id, case['msa_product'].product_id], check=True,
        capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1],
        env=os.environ | {'POLARS_MAX_THREADS': str(threads)}).stdout
        for threads in (1, 2, 4)]
    assert results[0] == results[1] == results[2]


def test_canonical_projection_rejects_flows():
    rows, nodes = canonical_case()
    flow = next(p for p in PRODUCTS if p.family == 'commuting_flow')
    with pytest.raises(ValueError, match='canonical'):
        canonical_rows(replace(rows, product=flow), nodes)


def test_supported_zero_mass_has_support_but_no_positive_target():
    case = projection_case()
    native = replace(case['native'], cells=case['native'].cells.with_columns(
        pl.when(pl.col('unit_b') == case['code_a']).then(pl.lit('0'))
            .otherwise(pl.col('sum_exact')).alias('sum_exact')))
    allocated, _ = allocate_area_mix(native, case['factors'], case['counties'],
                                     case['msa_product'])
    output = estimate(allocated)
    assert output['targets'].filter(pl.col('unit_b') == case['code_a']).collect().is_empty()
    support = output['support'].filter((pl.col('component_year') == 0)
        & (pl.col('unit_b') == case['code_a'])).collect()
    assert support['n_unweighted'].to_list() == [2, 2]
    assert support['fractional_support_mass'].to_list() == [1.5, 1.5]
    assert support['cell_mass'].to_list() == [0., 0.]


def test_county_first_msa_reduction_uses_declared_county_order():
    # A signed replica makes associativity observable: county-first gives 1,
    # whereas source-first gives 0 for the metropolitan cell.
    from embedding_data.acs_mapping_contract import factor_key

    case = projection_case()
    base = case['native'].cells.filter(pl.col('unit_a').str.ends_with('0100100'))
    tables, factors = [], []
    for index, masses in enumerate(['10000000000000000', '1',
                                    '-10000000000000000'], start=1):
        workplace = f'geography:2020:work_migration_puma:01{index:05d}'
        tables.append(base.with_columns(pl.lit(workplace).alias('unit_a'),
            pl.when(pl.col('replicate') == 37).then(pl.lit(masses))
                .otherwise(pl.col('sum_exact')).alias('sum_exact')))
        for geoid, value in [('01001', .25), ('02001', .75)]:
            factors.append(case['factors'].row(1, named=True) | {
                'factor_key': factor_key('work_migration', '01', f'{index:05d}'),
                'state_fips': '01', 'area_code': f'{index:05d}',
                'county_geoid': geoid, 'county_node_id': 'geography:2025:county:' + geoid,
                'factor': value})
    native = replace(case['native'], cells=pl.concat(tables))
    allocated, _ = allocate_area_mix(native,
        pl.DataFrame(factors, schema=case['factors'].schema), case['counties'],
        case['msa_product'])
    mass = allocated.cells.filter((pl.col('replicate') == 37)
        & (pl.col('component_year') == 0) & (pl.col('unit_b') == case['code_a'])).collect()
    assert mass['mass'].item() == 1.


def test_projection_outputs_match_unchanged_target_and_auxiliary_contracts():
    from embedding_data.acs_target_contract import validate_auxiliary
    from embedding_data.target_contract import validate_targets

    rows, nodes = canonical_case('sensitivity')
    canonical = aggregate_native(canonical_rows(rows, nodes))
    case = projection_case()
    allocated, residuals = allocate_area_mix(case['native'], case['factors'], case['counties'],
                                            case['msa_product'])
    for aggregates in [canonical, allocated]:
        result = estimate(aggregates)
        validate_targets(result['targets'])
        validate_auxiliary('target_support', result['support'])
        validate_auxiliary('replicate_estimates', result['replicates'])
        validate_auxiliary('eligibility_diagnostics', aggregates.diagnostics)
    validate_auxiliary('allocation_residuals', residuals)


@pytest.mark.parametrize('view', ['allocated_county', 'allocated_msa'])
def test_allocated_sensitivity_retains_evidence_identity_and_limitations(view):
    from embedding_data.acs_target_contract import observed_counterpart

    case = projection_case()
    observed = next(p for p in PRODUCTS if p.view == 'observed'
        and p.family == case['native'].product.family
        and p.dimension == case['native'].product.dimension
        and p.base_universe == case['native'].product.base_universe
        and p.evidence_policy == 'sensitivity'
        and p.years == case['native'].product.years)
    product = next(p for p in PRODUCTS if p.view == view
                   and observed_counterpart(p) == observed)
    evidence_flags = ['source_evidence_QIND_allocated', 'industry_flag_vintage_crosswalk']
    incoming_flags = pl.concat_list('flags', pl.lit(evidence_flags)).list.unique().list.sort()
    native = replace(case['native'], product=observed,
        cells=case['native'].cells.with_columns(incoming_flags.alias('flags')),
        denominators=case['native'].denominators.with_columns(incoming_flags.alias('flags')))
    allocated, residuals = allocate_area_mix(native, case['factors'], case['counties'], product)
    assert allocated.product == product
    output = estimate(allocated)
    targets, support, residuals = pl.collect_all([
        output['targets'], output['support'], residuals])
    assert targets.height > 0
    assert support.height > 0
    expected_flags = {
        *evidence_flags, 'size_gate_pending', 'flag_geographic_allocation',
        'allocation_conditional_sampling_se', 'allocation_error_unquantified',
        'mapping_uncertainty_unquantified', 'population2020', 'puma2020',
        'county_composition2022', 'county_inventory2025', 'msa_delineation_July_2023',
    }
    expected_metadata = {
        'source': 'acs', 'family': 'area_mix', 'sample_set': observed.sample_set,
        'vintage': product.vintage, 'universe': observed.base_universe + ':sensitivity',
    }
    for frame in [targets, support]:
        assert frame.select(*expected_metadata).unique().to_dicts() == [expected_metadata]
        assert all(expected_flags.issubset(flags) for flags in frame['flags'])
    assert support.select('view', 'product_id').unique().rows() == [(view, product.product_id)]
    assert support['pool_divisor'].unique().to_list() == [product.pool_divisor]
    if view == 'allocated_msa':
        assert residuals['residual_type'].unique().sort().to_list() == ['micropolitan', 'no_cbsa']
        metadata = expected_metadata | {'product_id': product.product_id,
                                        'pool_divisor': product.pool_divisor}
        assert residuals.select(*metadata).unique().to_dicts() == [metadata]
        assert all(expected_flags.issubset(flags) for flags in residuals['flags'])
    else:
        assert residuals.is_empty()
