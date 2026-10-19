import hashlib
import json
from dataclasses import FrozenInstanceError, asdict

import polars as pl
import pytest
from acs_target_fixtures import minimal_target, weights

from embedding_data import acs_target_contract as c
from embedding_data.acs_mapping_contract import CODE_SCHEMA, NATURAL_KEYS, lookup_id
from embedding_data.target_contract import TARGET_SCHEMA

S, I, U, F = pl.String, pl.Int64, pl.UInt64, pl.Float64  # noqa: E741
LS, LU8 = pl.List(S), pl.List(pl.UInt8)
STAT = [
    (name, S)
    for name in [
        'view',
        'source',
        'family',
        'unit_a_type',
        'unit_a',
        'unit_b_type',
        'unit_b',
        'measure',
        'sample_set',
        'vintage',
        'universe',
    ]
]
CODE = [
    ('code_' + name, dtype)
    for name, dtype in [
        ('code_lookup_id', S),
        ('system', S),
        ('source_scheme', S),
        ('native_vintage', I),
        ('canonical_vintage', I),
        ('paired_census_code', S),
        ('source_token', S),
        ('mapping_status', S),
        ('native_node_id', S),
        ('native_finest_candidates', LS),
        ('canonical_finest_candidates', LS),
        ('canonical_candidate_paths', pl.List(LS)),
        ('canonical_common_node_id', S),
        ('canonical_scalar_code', S),
        ('canonical_scalar_node_id', S),
        ('aggregation_type', S),
        ('aggregation_markers', LS),
        ('aggregation_reason_status', S),
        ('aggregation_reasons', LS),
        ('special_reason', S),
        ('flag_aggregate', pl.Boolean),
        ('flag_partial', pl.Boolean),
        ('flag_exception', pl.Boolean),
        ('flag_vintage_crosswalk', pl.Boolean),
        ('flag_reference_ambiguity', pl.Boolean),
        ('reference_ids', LS),
        ('reference_locators', LS),
        ('rule_version', S),
    ]
]
EXPECTED = {
    'target_units': [('unit_type', S), ('unit', S), ('kind', S)]
    + CODE
    + [
        ('node_id', S),
        ('node_system', S),
        ('node_vintage', I),
        ('node_level', S),
        ('node_code', S),
        ('node_title', S),
        ('area_type', S),
        ('state_fips', S),
        ('area_code', S),
        ('puma_vintage', I),
        ('population_year', I),
        ('county_composition_year', I),
        ('county_inventory_vintage', I),
        ('msa_delineation', S),
        ('cbsa_type', S),
        ('roles', LS),
        ('area_lookup_ids', LS),
        ('factor_keys', LS),
        ('reference_ids', LS),
        ('reference_locators', LS),
    ],
    'target_support': STAT
    + [
        ('record_kind', S),
        ('component_year', I),
        ('product_id', S),
        ('pool_divisor', pl.UInt8),
        ('n_unweighted', U),
        ('denominator_n_unweighted', U),
        ('cell_weight_sum_exact', S),
        ('denominator_weight_sum_exact', S),
        ('cell_mass', F),
        ('denominator_mass', F),
        ('fractional_support_mass', F),
        ('denominator_fractional_support_mass', F),
        ('native_coverage_n', U),
        ('native_coverage_mass', F),
        ('point_status', S),
        ('point_reason', S),
        ('se_status', S),
        ('se_reason', S),
        ('undefined_replicates', LU8),
        ('support_semantics', S),
        ('flags', LS),
    ],
    'replicate_estimates': STAT
    + [
        ('product_id', S),
        ('replicate', pl.UInt8),
        ('numerator_sum_exact', S),
        ('denominator_sum_exact', S),
        ('pool_divisor', pl.UInt8),
        ('numerator', F),
        ('denominator', F),
        ('estimate', F),
        ('status', S),
        ('reason', S),
    ],
    'eligibility_diagnostics': [
        (name, S)
        for name in ['source', 'profile', 'delivery_id', 'source_parquet_sha256', 'sample_id']
    ]
    + [('component_year', I)]
    + [
        (name, S)
        for name in [
            'family',
            'dimension',
            'base_universe',
            'evidence_policy',
            'view',
            'product_id',
            'partition_kind',
            'variable',
            'raw_dtype',
            'raw_value',
            'evidence_status',
            'reason',
        ]
    ]
    + [
        ('n_unweighted', U),
        ('weight_sum_exact', S),
        ('weighted_mass', F),
        ('reference_ids', LS),
        ('reference_locators', LS),
    ],
    'allocation_residuals': [
        (name, S)
        for name in [
            'source',
            'family',
            'workplace_unit_type',
            'workplace_unit',
            'code_unit_type',
            'code_unit',
            'sample_set',
            'vintage',
            'universe',
            'product_id',
        ]
    ]
    + [
        ('component_year', I),
        ('replicate', pl.UInt8),
        ('residual_type', S),
        ('pool_divisor', pl.UInt8),
        ('weighted_mass', F),
        ('n_input_support', U),
        ('fractional_support_mass', F),
        ('flags', LS),
    ],
}


def empty_tables():
    return {name: pl.DataFrame(schema=dict(schema)) for name, schema in EXPECTED.items()} | {
        name: pl.DataFrame(schema=TARGET_SCHEMA)
        for name in ['targets_observed', 'targets_canonical', 'targets_allocated_area_mix']
    }


def frame(name, rows):
    return pl.DataFrame(rows, schema=dict(EXPECTED[name])).sort(
        c.AUXILIARY_KEYS[name], nulls_last=False
    )


def observed_unit(system):
    row = {
        name: ([] if isinstance(dtype, pl.List) else None) for name, dtype in c.UNIT_SCHEMA.items()
    }
    code = {
        name: (
            []
            if isinstance(dtype, pl.List)
            else False
            if dtype == pl.Boolean
            else 2022
            if dtype == I
            else 'fixture'
        )
        for name, dtype in CODE_SCHEMA.items()
    }
    code.update(
        system=system,
        source_scheme='naics2022' if system == 'naics' else 'soc2018',
        native_vintage=2022 if system == 'naics' else 2018,
        canonical_vintage=2022 if system == 'naics' else 2018,
        paired_census_code='0170' if system == 'naics' else '0010',
        source_token='111111' if system == 'naics' else '111011',
        mapping_status='mapped',
        native_node_id=None,
        canonical_common_node_id=None,
        canonical_scalar_code=None,
        canonical_scalar_node_id=None,
        special_reason=None,
        native_finest_candidates=['111111' if system == 'naics' else '111011'],
        canonical_finest_candidates=['111111' if system == 'naics' else '111011'],
        canonical_candidate_paths=[
            [
                'root',
                (
                    'naics:2022:national_industry:111111'
                    if system == 'naics'
                    else 'soc:2018:detailed:111011'
                ),
            ]
        ],
        aggregation_type='finest',
        aggregation_reason_status='not_applicable',
        rule_version='acs-code-rules-v1',
    )
    code['code_lookup_id'] = lookup_id([code[name] for name in NATURAL_KEYS['code']])
    kind = 'acs_industry_category' if system == 'naics' else 'acs_occupation_category'
    row.update(
        unit_type=kind, unit=f"feature:{kind}:{code['code_lookup_id']}", kind='observed_code'
    )
    return row | {'code_' + name: value for name, value in code.items()}


def support_row(product, target):
    return {name: target[name] for name in c.TARGET_STAT_KEY_COLUMNS} | dict(
        view=product.view,
        record_kind='cell',
        component_year=0,
        product_id=product.product_id,
        pool_divisor=product.pool_divisor,
        n_unweighted=2,
        denominator_n_unweighted=8,
        cell_weight_sum_exact='50',
        denominator_weight_sum_exact='200',
        cell_mass=25.0,
        denominator_mass=100.0,
        fractional_support_mass=2.0,
        denominator_fractional_support_mass=8.0,
        native_coverage_n=None,
        native_coverage_mass=None,
        point_status='defined',
        point_reason=None,
        se_status='defined',
        se_reason=None,
        undefined_replicates=[],
        support_semantics='native_person_support',
        flags=['size_gate_pending'],
    )


def valid_tables():
    tables = empty_tables()
    product = next(
        p
        for p in c.PRODUCTS
        if p.family == 'staffing_pattern'
        and p.view == 'observed'
        and p.base_universe == 'civilian_employed'
        and p.evidence_policy == 'strict'
    )
    industry, occupation = observed_unit('naics'), observed_unit('soc')
    target = minimal_target(unit_a=industry['unit'], unit_b=occupation['unit'])
    tables['target_units'] = frame('target_units', [industry, occupation])
    tables['targets_observed'] = pl.DataFrame([target], schema=TARGET_SCHEMA)
    support = support_row(product, target)
    tables['target_support'] = frame('target_support', [support])
    replicates = [
        {name: support[name] for name in c.STAT_KEY_COLUMNS}
        | dict(
            product_id=product.product_id,
            replicate=r,
            numerator_sum_exact='50',
            denominator_sum_exact='200',
            pool_divisor=2,
            numerator=25.0,
            denominator=100.0,
            estimate=0.25,
            status='defined',
            reason=None,
        )
        for r in range(1, 81)
    ]
    tables['replicate_estimates'] = frame('replicate_estimates', replicates)
    return tables


def test_flags_or_se_method_cannot_identify_another_statistic():
    for changed in [
        minimal_target(flags=['allocated_source', 'size_gate_pending']),
        minimal_target(se=None, se_method='none'),
    ]:
        with pytest.raises(ValueError, match='logical statistic'):
            c.validate_statistic_keys(
                pl.DataFrame([minimal_target(), changed], schema=TARGET_SCHEMA)
            )


def test_declared_products_freeze_periods_and_identities():
    assert len(c.PRODUCTS) == 50
    observed = [p for p in c.PRODUCTS if p.view == 'observed']
    assert len(observed) == 22
    assert len([p for p in c.PRODUCTS if p.view == 'canonical']) == 12
    assert len([p for p in c.PRODUCTS if p.view.startswith('allocated_')]) == 16
    migration = [p for p in observed if p.family == 'migration_flow']
    assert sorted((p.evidence_policy, p.years, p.pool_divisor) for p in migration) == (
        [('sensitivity', (2023, 2024), 2)] * 2
        + [('sensitivity', (2024,), 1)] * 2
        + [('strict', (2024,), 1)] * 2
    )
    assert len({p.product_id for p in c.PRODUCTS}) == 50
    for product in c.PRODUCTS:
        identity = asdict(product)
        identity.pop('product_id')
        encoded = json.dumps(
            identity, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False
        ).encode()
        assert product.product_id == hashlib.sha256(encoded).hexdigest()
        counterpart = c.observed_counterpart(product)
        assert counterpart.view == 'observed'
        assert counterpart.years == product.years
        if product.view == 'observed':
            assert counterpart == product
    with pytest.raises(FrozenInstanceError):
        c.PRODUCTS[0].years = (2025,)


def test_schema_contracts_are_literal_ordered_and_empty_roundtrip(tmp_path):
    assert c.SCHEMA_VERSION == 'acs-targets-v1'
    assert c.RULE_VERSION == 'acs-target-rules-v1'
    assert list(c.STAT_KEY_SCHEMA.items()) == STAT
    assert list(c.CELL_KEY_SCHEMA.items()) == [(n, t) for n, t in STAT if n != 'measure']
    schemas = [
        c.UNIT_SCHEMA,
        c.SUPPORT_SCHEMA,
        c.REPLICATE_SCHEMA,
        c.DIAGNOSTIC_SCHEMA,
        c.RESIDUAL_SCHEMA,
    ]
    for (name, expected), schema in zip(EXPECTED.items(), schemas, strict=True):
        assert list(schema.items()) == expected
        path = tmp_path / f'{name}.parquet'
        pl.DataFrame(schema=schema).write_parquet(path)
        reread = pl.scan_parquet(path)
        c.validate_auxiliary(name, reread)
        assert list(reread.collect_schema().items()) == expected
    c.validate_cross_tables(empty_tables(), ())


@pytest.mark.parametrize('name', EXPECTED)
@pytest.mark.parametrize('defect', ['extra', 'missing', 'reordered', 'dtype', 'microdata'])
def test_auxiliary_schema_rejects_shape_drift(name, defect):
    table = empty_tables()[name]
    column = table.columns[0]
    variants = dict(
        extra=table.with_columns(pl.lit('x').alias('extra')),
        missing=table.drop(column),
        reordered=table.select(list(reversed(table.columns))),
        dtype=table.with_columns(pl.lit(1).alias(column)),
        microdata=table.with_columns(pl.lit(0).alias('source_row')),
    )
    with pytest.raises(ValueError, match='schema'):
        c.validate_auxiliary(name, variants[defect])


@pytest.mark.parametrize('name', ['target_units', 'target_support', 'replicate_estimates'])
def test_duplicate_auxiliary_keys_are_rejected(name):
    table = valid_tables()[name].head(1)
    with pytest.raises(ValueError, match='duplicate'):
        c.validate_auxiliary(name, pl.concat([table, table]))


@pytest.mark.parametrize(
    'column,value',
    [
        ('roles', None),
        ('roles', [None]),
        ('roles', ['b', 'a']),
        ('roles', ['a', 'a']),
        ('code_canonical_candidate_paths', [None]),
        ('code_canonical_candidate_paths', [[None]]),
        ('code_canonical_candidate_paths', []),
        ('code_canonical_candidate_paths', [['wrong']]),
        ('unit', None),
        ('kind', None),
        ('code_system', None),
        ('area_type', 'residence'),
    ],
)
def test_units_enforce_lists_paths_required_fields_and_kind_separation(column, value):
    row = observed_unit('naics') | {column: value}
    with pytest.raises(ValueError):
        c.validate_auxiliary('target_units', frame('target_units', [row]))


@pytest.mark.parametrize(
    'column,value',
    [
        ('product_id', None),
        ('cell_mass', float('nan')),
        ('denominator_mass', float('inf')),
        ('cell_mass', -1.0),
        ('point_status', 'unknown'),
        ('point_status', 'nonpositive_denominator'),
        ('point_reason', 'unexpected'),
        ('se_status', 'undefined_replicates'),
        ('undefined_replicates', [0]),
        ('undefined_replicates', [81]),
        ('flags', [None]),
        ('cell_weight_sum_exact', '1e3'),
        ('cell_weight_sum_exact', '01'),
        ('native_coverage_n', 4),
        ('unit_b', None),
    ],
)
def test_support_rejects_invalid_domains(column, value):
    row = valid_tables()['target_support'].row(0, named=True) | {column: value}
    with pytest.raises(ValueError):
        c.validate_auxiliary('target_support', frame('target_support', [row]))


@pytest.mark.parametrize(
    'column,value',
    [
        ('replicate', 0),
        ('replicate', 81),
        ('replicate', None),
        ('estimate', float('inf')),
        ('estimate', None),
        ('status', 'zero_denominator'),
        ('reason', 'unexpected'),
        ('status', 'missing_replicate'),
        ('numerator_sum_exact', 'NaN'),
    ],
)
def test_replicate_domains_are_explicit(column, value):
    row = valid_tables()['replicate_estimates'].row(0, named=True) | {column: value}
    with pytest.raises(ValueError):
        c.validate_auxiliary('replicate_estimates', frame('replicate_estimates', [row]))


def test_signed_replicates_and_independent_ratio_status_are_allowed():
    row = valid_tables()['replicate_estimates'].row(0, named=True)
    row.update(
        numerator_sum_exact='-50',
        denominator_sum_exact='-200',
        numerator=-25.0,
        denominator=-100.0,
    )
    c.validate_auxiliary('replicate_estimates', frame('replicate_estimates', [row]))
    row.update(
        denominator_sum_exact='0',
        denominator=0.0,
        estimate=None,
        status='zero_denominator',
        reason='zero_denominator',
    )
    c.validate_auxiliary('replicate_estimates', frame('replicate_estimates', [row]))


def test_denominator_status_null_endpoints_use_null_safe_keys():
    row = valid_tables()['target_support'].row(0, named=True)
    row.update(
        record_kind='denominator_status',
        unit_b_type=None,
        unit_b=None,
        n_unweighted=0,
        cell_weight_sum_exact=None,
        cell_mass=None,
        fractional_support_mass=None,
        denominator_weight_sum_exact='0',
        denominator_mass=0.0,
        point_status='nonpositive_denominator',
        point_reason='nonpositive_denominator',
        se_status='undefined_point',
        se_reason='undefined_point',
    )
    table = frame('target_support', [row])
    c.validate_auxiliary('target_support', table)
    with pytest.raises(ValueError, match='duplicate'):
        c.validate_auxiliary('target_support', pl.concat([table, table]))
    for change in [
        dict(denominator_mass=1.0),
        dict(n_unweighted=1),
        dict(denominator_n_unweighted=0),
        dict(measure='annual_average_total'),
    ]:
        with pytest.raises(ValueError):
            c.validate_auxiliary('target_support', frame('target_support', [row | change]))


@pytest.mark.parametrize('lazy', [False, True])
def test_cross_table_membership_is_structural_and_accepts_valid_bundle(lazy):
    tables = valid_tables()
    if lazy:
        tables = {name: table.lazy() for name, table in tables.items()}
    c.validate_cross_tables(tables, c.PRODUCTS)


@pytest.mark.parametrize(
    'defect',
    [
        'missing_unit',
        'missing_support',
        'missing_replicate',
        'orphan_replicate',
        'unknown_product',
        'wrong_year',
        'wrong_pool',
        'wrong_view',
        'wrong_unit_kind',
        'unknown_table',
    ],
)
def test_cross_table_membership_rejects_orphans_and_metadata_mismatch(defect):
    tables = valid_tables()
    if defect == 'missing_unit':
        tables['target_units'] = tables['target_units'].head(1)
    elif defect == 'missing_support':
        tables['target_support'] = tables['target_support'].head(0)
    elif defect == 'missing_replicate':
        tables['replicate_estimates'] = tables['replicate_estimates'].head(79)
    elif defect == 'unknown_table':
        tables['source_rows'] = pl.DataFrame()
    elif defect == 'wrong_unit_kind':
        tables['targets_observed'] = tables['targets_observed'].with_columns(
            pl.lit('county').alias('unit_a_type')
        )
    else:
        name = 'replicate_estimates' if defect == 'orphan_replicate' else 'target_support'
        column, value = {
            'orphan_replicate': ('unit_b', 'feature:acs_occupation_category:orphan'),
            'unknown_product': ('product_id', 'unknown'),
            'wrong_year': ('component_year', 2025),
            'wrong_pool': ('pool_divisor', 1),
            'wrong_view': ('view', 'canonical'),
        }[defect]
        tables[name] = tables[name].with_columns(
            pl.lit(value, dtype=tables[name].schema[column]).alias(column)
        )
    with pytest.raises(ValueError):
        c.validate_cross_tables(tables, c.PRODUCTS)


def test_fixture_weights_include_exactly_eighty_numbered_replicates():
    result = weights('2.5', {1: '-3', 80: '0'})
    assert len(result) == 81
    assert result['PERWT'] == '2.5'
    assert result['REPWTP1'] == '-3'
    assert result['REPWTP2'] == '2.5'
    assert result['REPWTP80'] == '0'


def node_unit(kind, code='01001', cbsa_type=None):
    row = {
        name: ([] if isinstance(dtype, pl.List) else None) for name, dtype in c.UNIT_SCHEMA.items()
    }
    system, vintage, level = {
        'county': ('geography', 2025, 'county'),
        'cbsa': ('geography', 2023, 'cbsa'),
        'naics_national_industry': ('naics', 2022, 'national_industry'),
        'soc_detailed': ('soc', 2018, 'detailed'),
    }[kind]
    unit = f'{system}:{vintage}:{level}:{code}'
    row.update(
        unit_type=kind,
        unit=unit,
        kind='selected_node',
        node_id=unit,
        node_system=system,
        node_vintage=vintage,
        node_level=level,
        node_code=code,
        node_title='Synthetic selected reference node',
        cbsa_type=cbsa_type,
    )
    if kind in {'county', 'cbsa'}:
        row.update(
            population_year=2020,
            county_composition_year=2022,
            county_inventory_vintage=2025,
            puma_vintage=2020,
        )
    if kind == 'cbsa':
        row['msa_delineation'] = 'July 2023'
    return row


def allocated_tables(view='allocated_county', cbsa_type='metropolitan',
                     dimension='industry'):
    tables = empty_tables()
    product = next(
        p
        for p in c.PRODUCTS
        if p.view == view
        and p.dimension == dimension
        and p.base_universe == 'civilian_employed'
        and p.evidence_policy == 'strict'
    )
    area = (
        node_unit('county')
        if view == 'allocated_county'
        else node_unit('cbsa', '12345', cbsa_type)
    )
    code = observed_unit('naics' if dimension == 'industry' else 'soc')
    target = minimal_target(
        family='area_mix',
        unit_a_type=area['unit_type'],
        unit_a=area['unit'],
        unit_b_type=code['unit_type'],
        unit_b=code['unit'],
        vintage=product.vintage,
    )
    support = support_row(product, target) | dict(
        cell_weight_sum_exact=None,
        denominator_weight_sum_exact=None,
        support_semantics='fractional_input_support',
    )
    tables['target_units'] = frame('target_units', [area, code])
    tables['target_support'] = frame('target_support', [support])
    tables['targets_allocated_area_mix'] = pl.DataFrame([target], schema=TARGET_SCHEMA)
    tables['replicate_estimates'] = frame(
        'replicate_estimates',
        [
            {name: support[name] for name in c.STAT_KEY_COLUMNS}
            | dict(
                product_id=product.product_id,
                replicate=r,
                numerator_sum_exact=None,
                denominator_sum_exact=None,
                pool_divisor=2,
                numerator=25.0,
                denominator=100.0,
                estimate=0.25,
                status='defined',
                reason=None,
            )
            for r in range(1, 81)
        ],
    )
    return tables


@pytest.mark.parametrize('view', ['allocated_county', 'allocated_msa'])
def test_shared_allocated_filename_derives_view_from_typed_membership(view):
    c.validate_cross_tables(allocated_tables(view), c.PRODUCTS)


def test_micropolitan_units_cannot_supply_allocated_msa_support_even_without_targets():
    tables = allocated_tables('allocated_msa', 'micropolitan')
    tables['targets_allocated_area_mix'] = tables['targets_allocated_area_mix'].head(0)
    with pytest.raises(ValueError, match='metropolitan'):
        c.validate_cross_tables(tables, c.PRODUCTS)


@pytest.mark.parametrize(
    'change',
    [
        dict(cell_mass=0.0),
        dict(denominator_mass=0.0),
        dict(point_status='no_positive_cell_mass', point_reason='no_positive_cell_mass'),
        dict(
            point_status='nonpositive_denominator',
            point_reason='nonpositive_denominator',
            se_status='undefined_point',
            se_reason='undefined_point',
        ),
    ],
)
def test_pooled_support_status_matches_full_point_publication_domain(change):
    row = valid_tables()['target_support'].row(0, named=True) | change
    with pytest.raises(ValueError):
        c.validate_auxiliary('target_support', frame('target_support', [row]))


def test_annual_support_repeats_pooled_status_instead_of_inventing_annual_status():
    tables = valid_tables()
    pooled = tables['target_support'].row(0, named=True)
    annual = pooled | dict(
        component_year=2023,
        cell_mass=0.0,
        point_status='no_positive_cell_mass',
        point_reason='no_positive_cell_mass',
    )
    tables['target_support'] = frame('target_support', [pooled, annual])
    with pytest.raises(ValueError, match='pooled status'):
        c.validate_cross_tables(tables, c.PRODUCTS)


def diagnostic_row():
    product = c.PRODUCTS[0]
    return dict(
        source='acs',
        profile='acs/core',
        delivery_id='synthetic',
        source_parquet_sha256='a' * 64,
        sample_id='us2023a',
        component_year=2023,
        family=product.family,
        dimension=product.dimension,
        base_universe=product.base_universe,
        evidence_policy=product.evidence_policy,
        view=product.view,
        product_id=product.product_id,
        partition_kind='first_exclusion',
        variable=None,
        raw_dtype=None,
        raw_value=None,
        evidence_status=None,
        reason='eligible',
        n_unweighted=1,
        weight_sum_exact='2',
        weighted_mass=1.0,
        reference_ids=[],
        reference_locators=[],
    )


def residual_row():
    product = next(p for p in c.PRODUCTS if p.view == 'allocated_msa')
    return dict(
        source='acs',
        family='area_mix',
        workplace_unit_type='work_migration_puma',
        workplace_unit='geography:2020:work_migration_puma:0100001',
        code_unit_type='acs_industry_category',
        code_unit='feature:acs_industry_category:synthetic',
        sample_set=product.sample_set,
        vintage=product.vintage,
        universe=product.base_universe + ':' + product.evidence_policy,
        product_id=product.product_id,
        component_year=0,
        replicate=0,
        residual_type='micropolitan',
        pool_divisor=2,
        weighted_mass=1.0,
        n_input_support=1,
        fractional_support_mass=0.5,
        flags=['size_gate_pending'],
    )


@pytest.mark.parametrize(
    'name,row_factory,changes',
    [
        (
            'eligibility_diagnostics',
            diagnostic_row,
            [
                ('reason', None),
                ('partition_kind', 'unknown'),
                ('reference_ids', [None]),
                ('weighted_mass', float('nan')),
                ('n_unweighted', None),
                ('weight_sum_exact', 'NaN'),
                ('partition_kind', 'evidence'),
            ],
        ),
        (
            'allocation_residuals',
            residual_row,
            [
                ('residual_type', 'unknown'),
                ('replicate', 81),
                ('replicate', None),
                ('weighted_mass', float('inf')),
                ('n_input_support', None),
                ('flags', None),
                ('fractional_support_mass', -1.0),
            ],
        ),
    ],
)
def test_diagnostic_and_residual_domains_and_null_safe_grains(name, row_factory, changes):
    row = row_factory()
    c.validate_auxiliary(name, frame(name, [row]))
    with pytest.raises(ValueError, match='duplicate'):
        c.validate_auxiliary(name, frame(name, [row, row]))
    for column, value in changes:
        with pytest.raises(ValueError):
            c.validate_auxiliary(name, frame(name, [row | {column: value}]))


def test_signed_residual_replicate_mass_is_preserved():
    c.validate_auxiliary(
        'allocation_residuals',
        frame('allocation_residuals', [residual_row() | dict(replicate=80, weighted_mass=-1.0)]),
    )


def test_unit_code_paths_preserve_typed_leaf_and_common_ancestor_fields():
    row = observed_unit('naics')
    for path in [['root', 'soc:2018:detailed:111111'],
                 ['root', 'naics:2017:national_industry:111111']]:
        with pytest.raises(ValueError):
            c.validate_auxiliary('target_units', frame('target_units', [
                row | dict(code_canonical_candidate_paths=[path])]))


def test_cross_table_statuses_match_undefined_replicates():
    tables = valid_tables()
    row = tables['target_support'].row(0, named=True)
    row.update(se_status='undefined_replicates', se_reason='undefined_replicates',
               undefined_replicates=[1])
    tables['target_support'] = frame('target_support', [row])
    tables['targets_observed'] = tables['targets_observed'].with_columns(
        pl.lit(None, dtype=F).alias('se'), pl.lit('none').alias('se_method'))
    with pytest.raises(ValueError, match='affected replicates'):
        c.validate_cross_tables(tables, c.PRODUCTS)


def test_defined_pooled_support_requires_a_published_target():
    tables = valid_tables()
    tables['targets_observed'] = tables['targets_observed'].head(0)
    with pytest.raises(ValueError, match='defined support missing target'):
        c.validate_cross_tables(tables, c.PRODUCTS)


@pytest.mark.parametrize('column', ['population_year', 'puma_vintage',
    'county_composition_year', 'county_inventory_vintage', 'msa_delineation'])
def test_allocated_unit_registry_retains_distinct_frames(column):
    row = node_unit('cbsa', '12345', 'metropolitan')
    c.validate_auxiliary('target_units', frame('target_units', [row]))
    with pytest.raises(ValueError):
        c.validate_auxiliary('target_units', frame('target_units', [row | {column: None}]))


def test_nonpositive_share_denominator_overrides_zero_cell_publication_status():
    row = valid_tables()['target_support'].row(0, named=True)
    row.update(cell_weight_sum_exact='0', cell_mass=0.0, denominator_weight_sum_exact='0',
        denominator_mass=0.0, point_status='no_positive_cell_mass',
        point_reason='no_positive_cell_mass')
    with pytest.raises(ValueError, match='point domain'):
        c.validate_auxiliary('target_support', frame('target_support', [row]))


def test_share_replicate_status_respects_zero_denominator_while_totals_remain_defined():
    row = valid_tables()['replicate_estimates'].row(0, named=True)
    with pytest.raises(ValueError, match='denominator status'):
        c.validate_auxiliary('replicate_estimates', frame('replicate_estimates', [
            row | dict(denominator=0.0, denominator_sum_exact='0')]))
    with pytest.raises(ValueError, match='denominator status'):
        c.validate_auxiliary('replicate_estimates', frame('replicate_estimates', [
            row | dict(status='zero_denominator', reason='zero_denominator', estimate=None)]))
    c.validate_auxiliary('replicate_estimates', frame('replicate_estimates', [row | dict(
        measure='annual_average_total', denominator=0.0,
        denominator_sum_exact='0', estimate=25.0)]))


def native_area_unit(role='workplace'):
    area_type = 'residence' if role == 'residence' else 'work_migration'
    unit_type = 'residence_puma' if role == 'residence' else 'work_migration_puma'
    row = {name: ([] if isinstance(dtype, pl.List) else None)
           for name, dtype in c.UNIT_SCHEMA.items()}
    row.update(unit_type=unit_type, unit=f'geography:2020:{unit_type}:0100001',
        kind='native_area', area_type=area_type, state_fips='01', area_code='00001',
        puma_vintage=2020, roles=[role],
        area_lookup_ids=[lookup_id(['acs/core', 'us2023a', 2023, 2023, role, '01', '00001'])],
        factor_keys=[lookup_id([area_type, '01', '00001', 2020])])
    return row


def valid_residual_tables(dimension='industry', role='workplace'):
    tables = allocated_tables('allocated_msa', dimension=dimension)
    workplace = native_area_unit(role)
    support = tables['target_support'].row(0, named=True)
    row = residual_row() | {name: support[name] for name in
        ['source', 'family', 'sample_set', 'vintage', 'universe', 'product_id', 'pool_divisor']}
    row.update(workplace_unit_type=workplace['unit_type'], workplace_unit=workplace['unit'],
               code_unit_type=support['unit_b_type'], code_unit=support['unit_b'])
    tables['target_units'] = frame('target_units',
        tables['target_units'].to_dicts() + [workplace])
    tables['allocation_residuals'] = frame('allocation_residuals', [row])
    return tables


@pytest.mark.parametrize('dimension', ['industry', 'occupation'])
def test_allocated_residuals_retain_native_workplace_and_dimension_provenance(dimension):
    c.validate_cross_tables(valid_residual_tables(dimension), c.PRODUCTS)


@pytest.mark.parametrize('dimension', ['industry', 'occupation'])
@pytest.mark.parametrize('defect', ['swapped', 'wrong_dimension', 'residence', 'migration_only'])
def test_residual_endpoints_must_match_workplace_role_and_product_dimension(dimension, defect):
    tables = valid_residual_tables(dimension,
        role={'residence': 'residence', 'migration_only': 'migration'}.get(defect, 'workplace'))
    row = tables['allocation_residuals'].row(0, named=True)
    if defect == 'swapped':
        support = tables['target_support'].row(0, named=True)
        row.update(workplace_unit_type=support['unit_b_type'], workplace_unit=support['unit_b'],
                   code_unit_type=support['unit_a_type'], code_unit=support['unit_a'])
    if defect == 'wrong_dimension':
        code = observed_unit('soc' if dimension == 'industry' else 'naics')
        tables['target_units'] = frame('target_units',
            tables['target_units'].to_dicts() + [code])
        row.update(code_unit_type=code['unit_type'], code_unit=code['unit'])
    tables['allocation_residuals'] = frame('allocation_residuals', [row])
    with pytest.raises(ValueError, match='residual endpoint'):
        c.validate_cross_tables(tables, c.PRODUCTS)


@pytest.mark.parametrize('kind,code,wrong_vintage', [
    ('naics_national_industry', '111111', 2017), ('soc_detailed', '111011', 2010),
    ('county', '01001', 2020), ('cbsa', '12345', 2025)])
def test_selected_node_structural_frames_reject_self_consistent_wrong_vintages(
        kind, code, wrong_vintage):
    row = node_unit(kind, code, 'metropolitan' if kind == 'cbsa' else None)
    c.validate_auxiliary('target_units', frame('target_units', [row]))
    system, _, level, _ = row['unit'].split(':', 3)
    wrong_unit = f'{system}:{wrong_vintage}:{level}:{code}'
    row.update(unit=wrong_unit, node_id=wrong_unit, node_vintage=wrong_vintage)
    with pytest.raises(ValueError, match='selected node.*frame'):
        c.validate_auxiliary('target_units', frame('target_units', [row]))


@pytest.mark.parametrize('column,value', [
    ('population_year', 2021), ('puma_vintage', 2010), ('county_composition_year', 2025),
    ('county_inventory_vintage', 2022), ('msa_delineation', '2023-07'),
    ('msa_delineation', '2099-01'), ('msa_delineation', 'July 2025')])
def test_allocated_unit_distinct_frames_reject_incorrect_nonnull_values(column, value):
    row = node_unit('cbsa', '12345', 'metropolitan')
    assert row['msa_delineation'] == 'July 2023'
    with pytest.raises(ValueError, match='frame'):
        c.validate_auxiliary('target_units', frame('target_units', [row | {column: value}]))
