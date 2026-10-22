from decimal import Decimal

import polars as pl
import pytest
from acs_target_fixtures import membership_frame, membership_rules, membership_units

from embedding_data.acs_target_contract import DIAGNOSTIC_SCHEMA, PRODUCTS
from embedding_data.acs_target_membership import family_rows
from embedding_data.acs_target_rules import required_flags

def product(family='staffing_pattern', dimension='industry_occupation', policy='strict',
            universe='civilian_employed', years=(2023, 2024)):
    return next(p for p in PRODUCTS if p.view == 'observed' and p.family == family
                and p.dimension == dimension and p.evidence_policy == policy
                and p.base_universe == universe and p.years == years)


def members(records, p=None):
    return family_rows(membership_frame(records), p or product(),
                       membership_rules(), membership_units()).members.collect()


def test_workplace_excludes_absent_home_and_niu_in_both_policies():
    records = [{'source_row': 0}, {'source_row': 1, 'EMPSTATD': 12},
               {'source_row': 2, 'TRANWORK': 80}, {'source_row': 3, 'TRANWORK': 0},
               {'source_row': 4, 'QTRANWOR': '4'}]
    assert {policy: members(records, product('area_mix', 'industry', policy))[
        'source_row'].to_list() for policy in ('strict', 'sensitivity')} == {
            'strict': [0], 'sensitivity': [0, 4]}


@pytest.mark.parametrize('family,dimension,changes', [
    ('staffing_pattern', 'industry_occupation', {
        'EMPSTATD': 12, 'TRANWORK': 0, 'MIGRATE1': 1,
        'residence_area_status': 'niu_or_unidentifiable', 'residence_factor_key': None,
        'workplace_area_status': 'foreign', 'workplace_factor_key': None,
        'migration_area_status': 'documented_unavailable', 'migration_factor_key': None}),
    ('area_mix', 'industry', {'residence_area_status': 'niu_or_unidentifiable',
        'residence_factor_key': None, 'migration_area_status': 'foreign',
        'migration_factor_key': None}),
    ('commuting_flow', 'flow', {'MIGRATE1': 1,
        'migration_area_status': 'niu_or_unidentifiable', 'migration_factor_key': None}),
    ('migration_flow', 'flow', {'EMPSTATD': 12, 'TRANWORK': 80,
        'workplace_area_status': 'foreign', 'workplace_factor_key': None}),
])
def test_unused_roles_do_not_exclude_eligible_pairs(family, dimension, changes):
    years = (2024,) if family == 'migration_flow' else (2023, 2024)
    assert members([{'source_row': 0} | changes], product(family, dimension, years=years))[
        'source_row'].to_list() == [0]


def test_civilian_special_and_private_universes():
    records = [{'source_row': i, 'EMPSTATD': emp, 'CLASSWKRD': cls, 'OCCSOC': '559830'}
               for i, (emp, cls) in enumerate([(12, 22), (10, 23), (10, 13),
                                               (10, 14), (14, 22), (15, 22)])]
    assert members(records)['source_row'].to_list() == [0, 1, 2, 3]
    assert members(records, product(universe='private_wage_salary'))[
        'source_row'].to_list() == [0, 1]


@pytest.mark.parametrize('family,dimension', [('staffing_pattern', 'industry_occupation'),
    ('area_mix', 'industry'), ('area_mix', 'occupation'), ('commuting_flow', 'flow'),
    ('migration_flow', 'flow')])
@pytest.mark.parametrize('universe', ['civilian_employed', 'private_wage_salary'])
@pytest.mark.parametrize('value', ['4', '1', None])
def test_each_required_evidence_failure(family, dimension, universe, value):
    years = (2024,) if family == 'migration_flow' else (2023, 2024)
    records = [{'source_row': i, flag: value}
               for i, flag in enumerate(required_flags(family, universe))]
    assert members(records, product(family, dimension, universe=universe, years=years)).is_empty()
    assert members(records, product(family, dimension, 'sensitivity', universe, years)).height == (
        len(records))


def test_unneeded_flags_and_associated_field_applicability():
    assert members([{'QCLASSWK': '4', 'QMIGRAT1': None, 'QTRANWOR': '4'}]).height == 1
    assert members([{'OCCSOC': None}], product('area_mix', 'industry')).is_empty()
    assert members([{'OCCSOC': None}], product('area_mix', 'industry', 'sensitivity')).height == 1
    assert members([{'industry_code_lookup_id': None}],
                   product('area_mix', 'industry', 'sensitivity')).is_empty()


@pytest.mark.parametrize('role,family,dimension', [('residence', 'commuting_flow', 'flow'),
    ('workplace', 'area_mix', 'occupation'), ('migration', 'migration_flow', 'flow')])
@pytest.mark.parametrize('status', ['foreign', 'territory', 'niu_or_unidentifiable',
                                    'documented_unavailable'])
def test_required_bad_endpoints_excluded_in_sensitivity(role, family, dimension, status):
    years = (2024,) if family == 'migration_flow' else (2023, 2024)
    p = product(family, dimension, 'sensitivity', years=years)
    rows = family_rows(membership_frame([{role + '_area_status': status,
                                         role + '_factor_key': None}]), p,
                       membership_rules(), membership_units())
    assert rows.members.collect().is_empty()
    assert rows.diagnostics.filter(pl.col('partition_kind').eq('first_exclusion')).collect()[
        'reason'].to_list() == [role + '_' + status]


def test_migration_periods_movers_and_typed_endpoints():
    records = [{'source_row': 0, 'acs_component_year': 2023, 'acs_sample_id': 'us2023a',
                'QMIGRAT1': None}, {'source_row': 1}, {'source_row': 2, 'MIGRATE1': 1},
               {'source_row': 3, 'MIGRATE1': 9}]
    for policy, years, expected in [('strict', (2024,), [1]),
        ('sensitivity', (2024,), [1]), ('sensitivity', (2023, 2024), [0, 1])]:
        frame = members(records, product('migration_flow', 'flow', policy, years=years))
        assert frame['source_row'].to_list() == expected
        assert set(frame['unit_a_type']) == {'work_migration_puma'}
        assert set(frame['unit_b_type']) == {'residence_puma'}
        assert frame['unit_a'].to_list() != frame['unit_b'].to_list()


def test_disjoint_funnels_close_for_every_product_and_year():
    records = [{'source_row': 0}, {'source_row': 1, 'EMPSTATD': 14},
               {'source_row': 2, 'acs_component_year': 2023, 'acs_sample_id': 'us2023a',
                'QMIGRAT1': None}, {'source_row': 3, 'QIND': '4', 'TRANWORK': 80}]
    for p in PRODUCTS:
        rows = family_rows(membership_frame(records), p, membership_rules(), membership_units())
        diagnostic = rows.diagnostics.collect()
        assert diagnostic.schema == DIAGNOSTIC_SCHEMA
        funnel = diagnostic.filter(pl.col('partition_kind').eq('first_exclusion'))
        assert funnel['n_unweighted'].sum() == 4
        assert sum(Decimal(v) for v in funnel['weight_sum_exact']) == Decimal('401.00')
        assert funnel.group_by('component_year').agg(pl.col('n_unweighted').sum()).sort(
            'component_year')['n_unweighted'].to_list() == [1, 3]
        assert all('size_gate_pending' in flags for flags in rows.members.collect()['flags'])


def test_unknown_flag_global_validation_and_numeric_transport_niu():
    with pytest.raises(ValueError, match='flag'):
        members([{'EMPSTATD': 14, 'QMIGPLC1': '99'}])
    assert members([{'TRANWORK': 0}], product('commuting_flow', 'flow')).is_empty()


def test_empty_membership_preserves_typed_outputs():
    rows = family_rows(membership_frame([]), product(), membership_rules(), membership_units())
    assert rows.members.collect().is_empty()
    assert rows.diagnostics.collect().schema == DIAGNOSTIC_SCHEMA


@pytest.mark.parametrize('value,reason', [(1, 'stayer'), (9, 'unknown_movement'),
                                         (4, 'moved_from_abroad'), (0, 'movement_not_applicable')])
def test_mover_failures_remain_separate(value, reason):
    p = product('migration_flow', 'flow', 'sensitivity', years=(2024,))
    rows = family_rows(membership_frame([{'MIGRATE1': value}]), p,
                       membership_rules(), membership_units())
    assert rows.diagnostics.filter(pl.col('partition_kind').eq('first_exclusion')).collect()[
        'reason'].to_list() == [reason]


def test_provenance_is_overlapping_and_puma_limitations_remain_flagged():
    p = product('area_mix', 'industry', 'sensitivity')
    frame = membership_frame([{'flag_source_industry_recoded': True, 'QIND': '4'},
                               {'source_row': 1}])
    rows = family_rows(frame, p, membership_rules(), membership_units())
    flags = rows.members.collect()['flags'].to_list()
    assert 'flag_source_industry_recoded' in flags[0]
    assert 'source_evidence_QIND_allocated' in flags[0]
    assert all('workplace_puma_specific_evidence_unavailable' in f for f in flags)
    diagnostic = rows.diagnostics.collect()
    provenance = diagnostic.filter(pl.col('reason').eq('flag_source_industry_recoded'))
    assert provenance['partition_kind'].to_list() == ['limitation']
    assert provenance['n_unweighted'].to_list() == [1]
    assert diagnostic.filter(pl.col('partition_kind').eq('first_exclusion'))[
        'n_unweighted'].sum() == 2


@pytest.mark.parametrize('role,flag,family,dimension', [
    ('workplace', 'QPWSTAT2', 'area_mix', 'industry'),
    ('migration', 'QMIGPLC1', 'migration_flow', 'flow')])
def test_state_place_evidence_is_applicable_with_unusable_puma(role, flag, family, dimension):
    years = (2024,) if family == 'migration_flow' else (2023, 2024)
    p = product(family, dimension, years=years)
    rows = family_rows(membership_frame([{role + '_area_status': 'niu_or_unidentifiable',
                                         role + '_factor_key': None}]), p,
                       membership_rules(), membership_units())
    assert rows.members.collect().is_empty()
    evidence = rows.diagnostics.filter(pl.col('partition_kind').eq('evidence').and_(
        pl.col('variable').eq(flag))).collect()
    assert evidence['evidence_status'].to_list() == ['nonallocation']


@pytest.mark.parametrize('field,flag,value,status', [
    ('EMPSTATD', 'QEMPSTAT', 14, 'allocated'),
    ('EMPSTATD', 'QEMPSTAT', 20, 'allocated'),
    ('EMPSTATD', 'QEMPSTAT', 99, 'not_applicable'),
    ('CLASSWKRD', 'QCLASSWK', 13, 'allocated'),
    ('CLASSWKRD', 'QCLASSWK', 98, 'not_applicable'),
    ('CLASSWKRD', 'QCLASSWK', 99, 'not_applicable')])
def test_substantive_applicability_is_separate_from_universe(field, flag, value, status):
    rows = family_rows(membership_frame([{field: value, flag: '4'}]), product(),
                       membership_rules(), membership_units())
    evidence = rows.diagnostics.filter(pl.col('partition_kind').eq('evidence').and_(
        pl.col('variable').eq(flag))).collect()
    assert evidence['evidence_status'].to_list() == [status]


def test_observed_diagnostic_exact_mass_uses_canonical_decimal_strings():
    from embedding_data.acs_target_contract import validate_auxiliary

    rows = family_rows(membership_frame([{'source_row': i} for i in range(8)]),
                       product(), membership_rules(), membership_units())
    diagnostic = rows.diagnostics.collect()
    validate_auxiliary('eligibility_diagnostics', diagnostic)
    full = diagnostic.filter((pl.col('partition_kind') == 'first_exclusion')
                              & (pl.col('reason') == 'eligible'))
    assert full['weight_sum_exact'].item() == '802'
    assert full['weighted_mass'].item() == 401.
