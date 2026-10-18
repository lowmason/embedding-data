'''Role-specific interpretation, source identity and conserved geographic allocation.'''

from dataclasses import replace

import polars as pl
import pytest

pytest_plugins = ['acs_mapping_fixtures']

@pytest.mark.parametrize(
    'role,state,area,status', [
        ('workplace', '00', '00000', 'niu_or_unidentifiable'),
        ('workplace', '80', '00001', 'foreign'),
        ('migration', '000', '00000', 'niu_or_unidentifiable'),
        ('migration', '150', '00001', 'foreign'),
        ('migration', '110', '00002', 'territory'),
    ]
)
def test_documented_role_specials_have_no_domestic_factors(role_case, role, state, area, status):
    from embedding_data.acs_area_mapping import build_area_lookup

    lookup = build_area_lookup(
        role_case.observed(role, state, area), role_case.rules, role_case.evidence,
        role_case.factors
    )
    row = lookup.row(0, named=True)
    assert row['area_status'] == status
    assert row['factor_key'] is None
    assert row['reference_ids'] and row['reference_locators']
    assert row['flag_source_geography_recoded'] is False

@pytest.mark.parametrize(
    'role,state', [('residence', '01'), ('workplace', '01'), ('migration', '001')]
)
def test_domestic_roles_retain_allocation_and_distinct_provenance(role_case, role, state):
    from embedding_data.acs_area_mapping import build_area_lookup

    row = build_area_lookup(
        role_case.observed(role, state, '00100'), role_case.rules, role_case.evidence,
        role_case.factors
    ).row(0, named=True)
    assert row['area_status'] == 'applicable'
    assert row['state_fips'] == '01'
    assert row['puma_vintage'] == 2020
    assert row['source_allocation_evidence_status'] == 'unavailable'
    assert role_case.source_columns[role] in ' '.join(row['reference_locators'])
    assert row['factor_key']

@pytest.mark.parametrize(
    'role,state,area', [
        ('residence', '09', '00100'),
        ('migration', '072', '00100'),
        ('workplace', '01', '00001'),
        ('migration', '150', '00100'),
        ('migration', '110', '00001'),
        ('workplace', '99', '00000'),
        ('migration', '997', '00001'),
        ('migration', '988', '00000'),
        ('residence', None, '00100'),
        ('workplace', '01', None),
        ('workplace', '01', '00003'),
        ('migration', '999', '00000'),
        ('residence', '001', '00100'),
        ('workplace', '01', '000100'),
    ]
)
def test_unexplained_or_incompatible_keys_fail(role_case, role, state, area):
    from embedding_data.acs_area_mapping import build_area_lookup

    with pytest.raises(ValueError):
        build_area_lookup(
            role_case.observed(role, state, area), role_case.rules, role_case.evidence,
            role_case.factors
        )

@pytest.mark.parametrize(
    'year,recoded', [(2020, True), (2021, True), (2022, False), (2023, False), (2024, False)]
)
@pytest.mark.parametrize(
    'role,state', [('residence', '01'), ('workplace', '01'), ('migration', '001')]
)
def test_five_year_source_frame_reassignment_is_separate(role_case, year, recoded, role, state):
    from embedding_data.acs_area_mapping import build_area_lookup

    observed = role_case.observed(role, state, '00100').with_columns(
        pl.lit('acs/five_year').alias('profile'),
        pl.lit('us2024c').alias('sample_id'),
        pl.lit(year).cast(pl.Int64).alias('component_year')
    )
    row = build_area_lookup(observed, role_case.rules, role_case.evidence,
                            role_case.factors).row(0, named=True)
    assert row['flag_source_geography_recoded'] is recoded
    assert row['source_allocation_evidence_status'] == 'unavailable'

def test_shared_work_migration_factor_retains_separate_ids(role_case):
    from embedding_data.acs_area_mapping import build_area_lookup

    observed = pl.concat(
        [
            role_case.observed('workplace', '01', '00100'),
            role_case.observed('migration', '001', '00100')
        ]
    )
    result = build_area_lookup(observed, role_case.rules, role_case.evidence, role_case.factors)
    assert result['factor_key'].n_unique() == 1
    assert result['area_lookup_id'].n_unique() == 2
    assert result['reference_locators'][0].to_list() != result['reference_locators'][1].to_list()

def test_missing_or_tampered_integer_intersections_fail(role_case):
    from embedding_data.acs_area_mapping import build_area_lookup, validate_area_lookup

    observed = role_case.observed('residence', '01', '00100')
    lookup = build_area_lookup(observed, role_case.rules, role_case.evidence, role_case.factors)
    for county in [
        role_case.factors.county.head(0),
        role_case.factors.county.with_columns(pl.col('intersection_population').add(1))
    ]:
        with pytest.raises(ValueError):
            validate_area_lookup(lookup, observed, replace(role_case.factors, county=county))
    broken = replace(
        role_case.evidence,
        intersections=role_case.evidence.intersections.filter(pl.col('county_geoid').ne('01001'))
    )
    with pytest.raises(ValueError):
        build_area_lookup(observed, role_case.rules, broken, role_case.factors)

def test_observed_preserves_source_counts_raw_types_and_sample_identity(role_case):
    from embedding_data.acs_area_mapping import observed_area_keys

    before = pl.read_parquet(role_case.source.parquet)
    result = observed_area_keys({'core': role_case.source})
    assert result.height == 3
    assert result['rows'].to_list() == [3, 3, 3]
    assert set(result['sample_id']) == {'us2024a'}
    assert result.filter(pl.col('role').eq('migration'))['source_state_code'][0] == '1'
    assert pl.read_parquet(role_case.source.parquet).equals(before)

def test_rule_conflicting_categories_fail(role_case):
    from embedding_data.acs_area_references import read_role_rules

    source = role_case.source
    ddi = {'variables': [dict(v) for v in source.ddi['variables']]}
    for variable in ddi['variables']:
        if variable['name'] == 'MIGPLAC1':
            variable['categories'] = [*variable['categories'], {'value': '001', 'label': 'Canada'}]
    with pytest.raises(ValueError):
        read_role_rules(role_case.snapshot, {'core': replace(source, ddi=ddi)})


def test_special_meanings_remain_distinct_and_status_counts_reconcile(role_case):
    from embedding_data.acs_area_mapping import AREA_KEY, build_area_lookup

    observations = [
        ('workplace', '00', '00000', 5), ('workplace', '80', '00001', 9),
        ('workplace', '01', '00100', 7), ('migration', '000', '00000', 3),
        ('migration', '150', '00001', 11), ('migration', '110', '00002', 7),
        ('residence', '01', '00100', 21),
    ]
    core = pl.concat([role_case.observed(role, state, area).with_columns(
        pl.lit(rows, dtype=pl.UInt64).alias('rows'))
        for role, state, area, rows in observations])
    five = core.with_columns(
        pl.lit('acs/five_year').alias('profile'), pl.lit('us2024c').alias('sample_id'),
        pl.col('rows').mul(2))
    observed = pl.concat([core, five])
    result = build_area_lookup(observed, role_case.rules, role_case.evidence, role_case.factors)
    niu = result.filter(pl.col('area_status').eq('niu_or_unidentifiable'))
    assert niu['status_reason'].n_unique() == 2
    represented = result.join(observed, on=AREA_KEY, how='left', validate='1:1')
    actual = {tuple(row[:3]): row[3] for row in represented.group_by(
        'profile', 'role', 'area_status').agg(pl.col('rows').sum()).select(
            'profile', 'role', 'area_status', 'rows').iter_rows()}
    assert actual == {
        ('acs/core', 'workplace', 'niu_or_unidentifiable'): 5,
        ('acs/core', 'workplace', 'foreign'): 9,
        ('acs/core', 'workplace', 'applicable'): 7,
        ('acs/core', 'migration', 'niu_or_unidentifiable'): 3,
        ('acs/core', 'migration', 'foreign'): 11,
        ('acs/core', 'migration', 'territory'): 7,
        ('acs/core', 'residence', 'applicable'): 21,
        ('acs/five_year', 'workplace', 'niu_or_unidentifiable'): 10,
        ('acs/five_year', 'workplace', 'foreign'): 18,
        ('acs/five_year', 'workplace', 'applicable'): 14,
        ('acs/five_year', 'migration', 'niu_or_unidentifiable'): 6,
        ('acs/five_year', 'migration', 'foreign'): 22,
        ('acs/five_year', 'migration', 'territory'): 14,
        ('acs/five_year', 'residence', 'applicable'): 42,
    }
    totals = {tuple(row[:2]): row[2] for row in represented.group_by(
        'profile', 'role').agg(pl.col('rows').sum()).select('profile', 'role', 'rows').iter_rows()}
    assert totals == {('acs/core', 'residence'): 21, ('acs/core', 'workplace'): 21,
                      ('acs/core', 'migration'): 21, ('acs/five_year', 'residence'): 42,
                      ('acs/five_year', 'workplace'): 42, ('acs/five_year', 'migration'): 42}


@pytest.mark.parametrize('field,value', [
    ('flag_source_geography_recoded', True),
    ('source_allocation_evidence_status', 'allocated'),
    ('area_code', '12345'), ('puma_vintage', 2010),
])
def test_validator_rejects_contradictory_role_annotations(role_case, field, value):
    from embedding_data.acs_area_mapping import build_area_lookup, validate_area_lookup

    observed = role_case.observed('workplace', '00', '00000')
    lookup = build_area_lookup(observed, role_case.rules, role_case.evidence, role_case.factors)
    broken = lookup.with_columns(pl.lit(value).cast(lookup.schema[field]).alias(field))
    with pytest.raises(ValueError):
        validate_area_lookup(broken, observed, role_case.factors)


def test_rules_require_nonempty_honest_reference_lists(role_case):
    from embedding_data.acs_area_mapping import build_area_lookup

    rules = role_case.rules.with_columns(
        pl.lit([], dtype=pl.List(pl.String)).alias('reference_ids'))
    with pytest.raises(ValueError):
        build_area_lookup(role_case.observed('workplace', '01', '00100'), rules,
                          role_case.evidence, role_case.factors)


def test_original_role_document_tampering_fails(role_case):
    from embedding_data.acs_area_references import read_role_rules

    role_case.snapshot.files['usa_puma'].write_text('changed')
    with pytest.raises(ValueError, match='original differs'):
        read_role_rules(role_case.snapshot, {'core': role_case.source})


def test_foreign_labels_do_not_become_domestic_by_numeric_suffix(role_case):
    from embedding_data.acs_area_mapping import build_area_lookup
    from embedding_data.acs_area_references import read_role_rules

    source = role_case.source
    ddi = {'variables': [dict(v) for v in source.ddi['variables']]}
    for variable in ddi['variables']:
        if variable['name'] == 'MIGPLAC1':
            variable['categories'] = [*variable['categories'], {'value': '101', 'label': 'Canada'}]
    rules = read_role_rules(role_case.snapshot, {'core': replace(source, ddi=ddi)})
    row = build_area_lookup(role_case.observed('migration', '101', '00001'), rules,
                            role_case.evidence, role_case.factors).row(0, named=True)
    assert row['area_status'] == 'foreign'
    assert row['state_fips'] is None


@pytest.mark.parametrize('column,value', [('puma_vintage', 2010), ('population_year', 2021),
                                         ('county_composition_year', 2020),
                                         ('county_inventory_vintage', 2020)])
def test_lookup_refuses_wrong_factor_frames(role_case, column, value):
    from embedding_data.acs_area_mapping import build_area_lookup

    county = role_case.factors.county.with_columns(pl.lit(value).cast(pl.Int64).alias(column))
    with pytest.raises(ValueError):
        build_area_lookup(role_case.observed('residence', '01', '00100'), role_case.rules,
                          role_case.evidence, replace(role_case.factors, county=county))


@pytest.mark.parametrize('role,code,label', [('migration', '105', 'Guam'),
                                           ('workplace', '73', 'U.S. outlying area')])
def test_non_pr_territory_outside_us_pr_retains_territory_status(role_case, role, code, label):
    from embedding_data.acs_area_mapping import build_area_lookup
    from embedding_data.acs_area_references import read_role_rules

    source = role_case.source
    variable_name = 'MIGPLAC1' if role == 'migration' else 'PWSTATE2'
    ddi = {'variables': [dict(v) for v in source.ddi['variables']]}
    for variable in ddi['variables']:
        if variable['name'] == variable_name:
            variable['categories'] = [*variable['categories'], {'value': code, 'label': label}]
    rules = read_role_rules(role_case.snapshot, {'core': replace(source, ddi=ddi)})
    row = build_area_lookup(role_case.observed(role, code, '00001'), rules,
                            role_case.evidence, role_case.factors).row(0, named=True)
    assert row['area_status'] == 'territory'
    assert row['factor_key'] is None
    assert label in row['status_reason']


@pytest.mark.parametrize('year,recoded', [(2020, True), (2021, True), (2022, False)])
@pytest.mark.parametrize('role,state', [('residence', '72'), ('workplace', '72'),
                                        ('migration', '110')])
def test_defined_pr_source_frame_reassignment_survives_scope_exclusion(
        role_case, year, recoded, role, state):
    from embedding_data.acs_area_mapping import build_area_lookup

    observed = role_case.observed(role, state, '00100').with_columns(
        pl.lit('acs/five_year').alias('profile'), pl.lit('us2024c').alias('sample_id'),
        pl.lit(year).cast(pl.Int64).alias('component_year'))
    row = build_area_lookup(observed, role_case.rules, role_case.evidence,
                            role_case.factors).row(0, named=True)
    assert row['area_status'] == 'territory'
    assert row['factor_key'] is None
    assert row['flag_source_geography_recoded'] is recoded
    assert row['source_allocation_evidence_status'] == 'unavailable'


@pytest.mark.parametrize('year', [2020, 2021, 2022])
def test_pr_migration_special_does_not_claim_defined_source_frame(role_case, year):
    from embedding_data.acs_area_mapping import build_area_lookup

    observed = role_case.observed('migration', '110', '00002').with_columns(
        pl.lit('acs/five_year').alias('profile'), pl.lit('us2024c').alias('sample_id'),
        pl.lit(year).cast(pl.Int64).alias('component_year'))
    row = build_area_lookup(observed, role_case.rules, role_case.evidence,
                            role_case.factors).row(0, named=True)
    assert row['area_status'] == 'territory'
    assert row['factor_key'] is None
    assert row['flag_source_geography_recoded'] is False


@pytest.mark.parametrize('role,state,area', [
    ('workplace', '72', '00002'), ('residence', '72', '00000'),
    ('residence', '72', '00001'), ('residence', '72', '00002'),
])
def test_territory_digits_require_role_special_or_complete_definition(
        role_case, role, state, area):
    from embedding_data.acs_area_mapping import build_area_lookup

    with pytest.raises(ValueError, match='absent from complete reference definitions'):
        build_area_lookup(role_case.observed(role, state, area), role_case.rules,
                          role_case.evidence, role_case.factors)


def test_missing_migration_pr_special_cannot_borrow_its_raw_digits(role_case):
    from embedding_data.acs_area_mapping import build_area_lookup

    rules = role_case.rules.filter(pl.col('rule_kind').ne('area_special').or_(
        pl.col('role').ne('migration')).or_(pl.col('source_code').ne('00002')))
    with pytest.raises(ValueError, match='absent from complete reference definitions'):
        build_area_lookup(role_case.observed('migration', '110', '00002'), rules,
                          role_case.evidence, role_case.factors)


@pytest.mark.parametrize('role,state', [('workplace', '72'), ('migration', '110')])
def test_matched_pr_niu_special_stays_nondefined(role_case, role, state):
    from embedding_data.acs_area_mapping import build_area_lookup

    observed = role_case.observed(role, state, '00000').with_columns(
        pl.lit('acs/five_year').alias('profile'), pl.lit('us2024c').alias('sample_id'),
        pl.lit(2020, dtype=pl.Int64).alias('component_year'))
    row = build_area_lookup(observed, role_case.rules, role_case.evidence,
                            role_case.factors).row(0, named=True)
    assert row['area_status'] == 'niu_or_unidentifiable'
    assert row['flag_source_geography_recoded'] is False
    assert row['factor_key'] is None


@pytest.mark.parametrize('role,code', [('residence', '00001'), ('workplace', '00002')])
def test_defined_territory_code_does_not_borrow_another_roles_special(role_case, role, code):
    from embedding_data.acs_area_mapping import build_area_lookup

    def recode_pr(frame, column):
        return frame.with_columns(pl.when(pl.col('state_fips').eq('72')).then(
            pl.lit(code)).otherwise(pl.col(column)).alias(column))

    evidence = role_case.evidence
    if role == 'residence':
        evidence = replace(evidence,
                           intersections=recode_pr(evidence.intersections, 'puma_code'),
                           puma_totals=recode_pr(evidence.puma_totals, 'puma_code'),
                           puma_groups=recode_pr(evidence.puma_groups, 'puma_code'))
    else:
        evidence = replace(evidence,
                           puma_groups=recode_pr(evidence.puma_groups, 'group_code'),
                           county_groups=recode_pr(evidence.county_groups, 'group_code'))
    observed = role_case.observed(role, '72', code).with_columns(
        pl.lit('acs/five_year').alias('profile'), pl.lit('us2024c').alias('sample_id'),
        pl.lit(2020, dtype=pl.Int64).alias('component_year'))
    row = build_area_lookup(observed, role_case.rules, evidence,
                            role_case.factors).row(0, named=True)
    assert row['area_status'] == 'territory'
    assert row['flag_source_geography_recoded'] is True
    assert row['factor_key'] is None
