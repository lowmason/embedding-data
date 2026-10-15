import copy
import importlib
import json

import polars as pl
import pytest
from polars.testing import assert_frame_equal

ACS_VARIABLES = set((
    'PERWT REPWTP INDNAICS IND OCCSOC OCC EMPSTAT CLASSWKR GQ EDUC '
    'DEGFIELD DEGFIELD2 INCWAGE INCEARN UHRSWORK WKSWORK2 AGE SEX STATEFIP REGION PUMA '
    'COUNTYFIP MET2023 MET2023ERR PWSTATE2 PWPUMA00 PWMET23 PWMET23ERR TRANWORK TRANTIME '
    'MIGRATE1 MIGPLAC1 MIGPUMA1 MIGMET23 ').split())
MONTHLY_VARIABLES = set((
    'CPSIDP CPSIDV MISH WTFINL LNKFW1MWT EARNWT IND OCC CLASSWKR '
    'EMPSAME ACTSAME LABFORCE EMPSTAT UHRSWORK1 EARNWEEK2 HOURWAGE2 PAIDHOUR ELIGORG AGE SEX '
    'EDUC STATEFIP REGION METFIPS COUNTY ').split())
ASEC_VARIABLES = set((
    'CPSIDP CPSIDV ASECWT REPWTP IND OCC CLASSWKR INDLY OCCLY CLASSWLY '
    'LABFORCE EMPSTAT WKSWORK1 UHRSWORKLY INCWAGE AGE SEX EDUC STATEFIP REGION METFIPS COUNTY '
    'MIGRATE1 MIGSTA1 WHYMOVE ').split())
ACS_REPLICATES = {f'REPWTP{number}' for number in range(1, 81)}
ASEC_REPLICATES = {f'REPWTP{number}' for number in range(1, 161)}
PROFILES = [('acs', 'core'), ('acs', 'vintage'), ('acs', 'five_year'),
            ('cps', 'monthly'), ('cps', 'asec')]
KEY_SCHEMA = {'extract_key': pl.String, 'source': pl.String, 'set_name': pl.String}
SAMPLE_SCHEMA = {
    **KEY_SCHEMA, 'year': pl.Int64, 'month': pl.Int64, 'sample': pl.String,
    'multyear': pl.Int64, 'sample_id': pl.String, 'sample_label': pl.String, 'rows': pl.UInt64,
}
FLAG_SCHEMA = {
    **KEY_SCHEMA, 'year': pl.Int64, 'month': pl.Int64, 'sample': pl.String,
    'multyear': pl.Int64, 'sample_id': pl.String, 'flag': pl.String, 'present': pl.Boolean,
    'dtype': pl.String, 'value': pl.String, 'category_label': pl.String,
    'applicability': pl.String, 'rows': pl.UInt64,
}
VARIABLE_SCHEMA = {
    **KEY_SCHEMA, 'variable': pl.String, 'requested': pl.Boolean, 'required': pl.Boolean,
    'detailed': pl.Boolean, 'replicate': pl.Boolean, 'quality_flag': pl.Boolean,
    'in_ddi': pl.Boolean, 'in_parquet': pl.Boolean, 'ddi_position': pl.UInt32,
    'parquet_position': pl.UInt32, 'dtype': pl.String, 'implied_decimals': pl.Int64,
    'label': pl.String,
}


def delivery(source='acs', set_name='core'):
    if source == 'acs':
        sample_ids = {'core': ['us2023a', 'us2024a'], 'vintage': ['us2022a'],
                      'five_year': ['us2024c']}[set_name]
        catalog = {'us2022a': '2022 ACS', 'us2023a': '2023 ACS', 'us2024a': '2024 ACS',
                   'us2024c': '2020-2024, ACS 5-year'}
        requested = ACS_VARIABLES | ({'MULTYEAR'} if set_name == 'five_year' else set())
        names = requested - {'REPWTP'} | ACS_REPLICATES | {
            'YEAR', 'SAMPLE', 'EMPSTATD', 'CLASSWKRD', 'INCWAGE_CPIU_2010', 'QMIGRAT1',
        }
        years = {'core': [2023, 2023, 2024], 'vintage': [2022],
                 'five_year': [2024] * 5}[set_name]
        samples = {'core': [1, 1, 2], 'vintage': [1], 'five_year': [1] * 5}[set_name]
    else:
        catalog = {'cps2025_01b': 'January 2025 basic monthly',
                   'cps2025_03s': 'March 2025 ASEC',
                   'cps2025_02b': 'February 2025 basic monthly'}
        sample_ids = ['cps2025_03s'] if set_name == 'asec' else ['cps2025_01b', 'cps2025_02b']
        requested = ASEC_VARIABLES if set_name == 'asec' else MONTHLY_VARIABLES
        names = requested - {'REPWTP'} | {'YEAR', 'MONTH', 'QMIGRAT1'}
        if set_name == 'asec':
            names |= ASEC_REPLICATES | {'INCWAGE_CPIU_2010'}
        years, samples = [2025, 2025], None
    values = {name: [1] * len(years) for name in sorted(names)}
    values['YEAR'] = years
    values['QMIGRAT1'] = (['01', '10', None] if len(years) == 3
                         else ['01'] * len(years))
    if source == 'acs':
        values['EMPSTAT'] = [1] * len(years)
        values['SAMPLE'] = samples
        if set_name == 'five_year':
            values['MULTYEAR'] = [2020, 2021, 2022, 2023, 2024]
    else:
        values['MONTH'] = [3, 3] if set_name == 'asec' else [1, 2]
        values['LABFORCE'] = [0, 2] if set_name == 'asec' else [2, 2]
    variables = []
    for name in values:
        categories = []
        if name == 'SAMPLE':
            categories = [{'value': str(index), 'label': catalog[sample_id]}
                          for index, sample_id in enumerate(sample_ids, 1)]
            categories += [{'value': '999', 'label': '1900 Census'}]
        if name == 'QMIGRAT1':
            categories = [{'value': '01', 'label': 'NIU'},
                          {'value': '10', 'label': 'Allocated by procedure'}]
        variables.append({'name': name, 'label': name, 'implied_decimals': 0,
                          'categories': categories, 'instructions': []})
    definition = {'collection': 'usa' if source == 'acs' else 'cps', 'dataFormat': 'csv',
                  'samples': {name: {} for name in sample_ids}, 'dataQualityFlags': True,
                  'variables': {name: {'caseSelections': {}} for name in requested}}
    if source == 'acs':
        definition['variables']['EMPSTAT']['caseSelections'] = {'general': ['1']}
    if set_name == 'monthly':
        definition['variables']['LABFORCE']['caseSelections'] = {'general': ['2']}
    ddi = {'variables': variables, 'study_notes': [catalog[name] for name in sample_ids],
           'time_notes': [{'kind': 'timePrd', 'text': '2020-2025',
                           'date': '2025-01 2025-02 2025-03'}]}
    return definition, ddi, pl.DataFrame(values).lazy(), source, set_name, catalog


def measure(args):
    return importlib.import_module('embedding_data.ipums_acceptance').measure_acceptance(*args)


@pytest.mark.parametrize('source,set_name', PROFILES)
def test_five_profiles_exact_required_sets_and_aggregate_schemas(source, set_name):
    result = measure(delivery(source, set_name))
    expected = (ACS_VARIABLES if source == 'acs' else
                ASEC_VARIABLES if set_name == 'asec' else MONTHLY_VARIABLES) - {'REPWTP'}
    if source == 'acs':
        expected |= ACS_REPLICATES | {'YEAR', 'SAMPLE', 'EMPSTATD', 'CLASSWKRD',
                                      'INCWAGE_CPIU_2010'}
        if set_name == 'five_year':
            expected |= {'MULTYEAR'}
    elif set_name == 'asec':
        expected |= ASEC_REPLICATES | {'YEAR', 'MONTH', 'INCWAGE_CPIU_2010'}
    else:
        expected |= {'YEAR', 'MONTH'}
    assert 'REPWTP' not in ACS_REPLICATES | ASEC_REPLICATES
    inventory = result['variable_inventory']
    assert set(inventory.filter(pl.col('required'))['variable']) == expected
    assert list(inventory.schema.items()) == list(VARIABLE_SCHEMA.items())
    assert list(result['sample_counts'].schema.items()) == list(SAMPLE_SCHEMA.items())
    assert list(result['flag_coverage'].schema.items()) == list(FLAG_SCHEMA.items())
    assert result['status']['status'] == 'pass'
    assert result['status']['raw_header_parity'] == 'external_required'
    json.dumps(result['status'], allow_nan=False)
    assert 'CPSIDP' not in result['sample_counts'].columns


def test_handwritten_observed_counts_and_typed_flag_categories():
    result = measure(delivery())
    expected = pl.DataFrame([
        ('acs/core', 'acs', 'core', 2023, None, '1', None, 'us2023a', '2023 ACS', 2),
        ('acs/core', 'acs', 'core', 2024, None, '2', None, 'us2024a', '2024 ACS', 1),
    ], schema=SAMPLE_SCHEMA, orient='row')
    assert_frame_equal(result['sample_counts'], expected)
    flags = result['flag_coverage']
    assert flags.select('year', 'value', 'category_label', 'rows').rows() == [
        (2023, '01', 'NIU', 1), (2023, '10', 'Allocated by procedure', 1),
        (2024, None, None, 1),
    ]
    assert flags['dtype'].to_list() == ['String'] * 3
    assert flags['applicability'].to_list() == ['unknown'] * 3


@pytest.mark.parametrize('source,set_name,missing,extra', [
    ('acs', 'core', 'REPWTP80', 'REPWTP81'),
    ('cps', 'asec', 'REPWTP160', 'REPWTP161'),
])
def test_exact_replicate_range_never_accepts_parent_or_extra(source, set_name, missing, extra):
    args = list(delivery(source, set_name))
    args[2] = args[2].drop(missing).with_columns(pl.lit(1).alias('REPWTP'),
                                               pl.lit(1).alias(extra))
    result = measure(args)
    assert result['status']['status'] == 'fail'
    assert result['status']['replicates_missing'] == [missing]
    assert result['status']['replicates_unexpected'] == ['REPWTP', extra]


@pytest.mark.parametrize('source,set_name,variable', [
    ('acs', 'core', 'REGION'), ('cps', 'monthly', 'REGION'),
    ('cps', 'asec', 'CLASSWLY'), ('acs', 'vintage', 'EMPSTATD'),
    ('acs', 'five_year', 'MULTYEAR'), ('cps', 'asec', 'INCWAGE_CPIU_2010'),
])
def test_missing_requested_or_required_variable_fails(source, set_name, variable):
    args = list(delivery(source, set_name))
    args[2] = args[2].drop(variable)
    status = measure(args)['status']
    assert status['status'] == 'fail'
    assert variable in status['required_missing_parquet']


def test_missing_automatic_flag_is_absent_coverage_with_unknown_interpretation():
    args = list(delivery())
    args[2] = args[2].drop('QMIGRAT1')
    result = measure(args)
    assert 'QMIGRAT1' not in result['status']['required_missing_parquet']
    assert result['status']['missing_flags'] == ['QMIGRAT1']
    assert result['status']['status'] == 'unresolved'
    flags = result['flag_coverage']
    assert flags.select('present', 'dtype', 'value', 'rows').rows() == [
        (False, None, None, 2), (False, None, None, 1),
    ]
    assert flags['applicability'].to_list() == ['unknown', 'unknown']


def test_generic_ddi_sample_category_does_not_prove_observed_membership():
    args = list(delivery())
    args[2] = args[2].filter(pl.col('SAMPLE').eq(1))
    status = measure(args)['status']
    assert status['status'] == 'fail'
    assert status['samples_missing'] == ['us2024a']


@pytest.mark.parametrize('mutation,diagnostic', [
    ('label', 'sample_catalog_mismatch'), ('notes', 'sample_study_notes_unknown'),
    ('year', 'sample_year_mismatch'), ('time', 'ddi_time_unknown'),
    ('unknown_sample', 'samples_unmapped'),
])
def test_sample_evidence_does_not_guess_membership(mutation, diagnostic):
    args = list(delivery())
    if mutation == 'label':
        args[1]['variables'] = copy.deepcopy(args[1]['variables'])
        sample = next(v for v in args[1]['variables'] if v['name'] == 'SAMPLE')
        sample['categories'][0]['label'] = '2022 ACS'
    elif mutation == 'notes':
        args[1]['study_notes'] = []
    elif mutation == 'year':
        args[2] = args[2].with_columns(pl.lit(2022).alias('YEAR'))
    elif mutation == 'time':
        args[1]['time_notes'] = []
    else:
        args[2] = args[2].with_columns(pl.lit(999).alias('SAMPLE'))
    status = measure(args)['status']
    assert status['status'] != 'pass'
    assert status[diagnostic]


def test_monthly_absent_requested_periods_are_explicit():
    args = list(delivery('cps', 'monthly'))
    args[2] = args[2].filter(pl.col('MONTH').eq(1))
    status = measure(args)['status']
    assert status['status'] == 'fail'
    assert status['periods_missing'] == ['2025-02']
    assert status['samples_missing'] == ['cps2025_02b']


@pytest.mark.parametrize('source,set_name,variable,value', [
    ('acs', 'core', 'EMPSTAT', 2), ('cps', 'monthly', 'LABFORCE', 0),
    ('acs', 'core', 'EMPSTAT', None),
])
def test_unexpected_selection_values_are_counted_and_fail(source, set_name, variable, value):
    args = list(delivery(source, set_name))
    args[2] = args[2].with_columns(pl.lit(value).cast(pl.Int64).alias(variable))
    status = measure(args)['status']
    assert status['status'] == 'fail'
    assert status['selection_unexpected_rows'] in (2, 3)
    assert status['rows'] in (2, 3)


@pytest.mark.parametrize('source,set_name', PROFILES)
def test_wrong_submitted_selection_or_collection_fails(source, set_name):
    args = list(delivery(source, set_name))
    if set_name == 'asec':
        args[0]['variables']['EMPSTAT']['caseSelections'] = {'general': ['1']}
    else:
        name = 'EMPSTAT' if source == 'acs' else 'LABFORCE'
        args[0]['variables'][name]['caseSelections'] = {'detailed': ['1']}
    assert measure(args)['status']['definition_errors']
    args = list(delivery(source, set_name))
    args[0]['collection'] = 'wrong'
    assert measure(args)['status']['definition_errors']


def test_asec_separate_from_monthly_and_unrestricted_observations():
    args = list(delivery('cps', 'asec'))
    assert measure(args)['status']['selection_unexpected_rows'] == 0
    args[1]['study_notes'] = ['March 2025 basic monthly']
    assert measure(args)['status']['status'] == 'fail'


def test_ddi_parquet_order_and_missing_metadata_are_diagnostic():
    args = list(delivery())
    args[1]['variables'] = args[1]['variables'][::-1]
    status = measure(args)['status']
    assert status['status'] == 'fail'
    assert status['ddi_parquet_order_equal'] is False
    args[1]['variables'] = [v for v in args[1]['variables'] if v['name'] != 'REGION']
    assert 'REGION' in measure(args)['status']['required_missing_ddi']


def test_empty_input_fails_with_typed_empty_aggregates():
    args = list(delivery())
    args[2] = args[2].head(0)
    result = measure(args)
    assert result['status']['status'] == 'fail'
    assert result['status']['rows'] == 0
    assert list(result['sample_counts'].schema.items()) == list(SAMPLE_SCHEMA.items())
    assert list(result['flag_coverage'].schema.items()) == list(FLAG_SCHEMA.items())


def test_unknown_profile_rejected_without_collecting_person_data():
    args = list(delivery())
    args[4] = 'unknown'
    with pytest.raises(ValueError, match='profile'):
        measure(args)


@pytest.mark.parametrize('set_name', ['monthly', 'asec'])
def test_cps_uses_submitted_periods_and_ddi_not_the_usa_public_catalog(set_name):
    args = list(delivery('cps', set_name))
    args[5] = {'us2023a': '2023 ACS', 'us2024c': '2020-2024, ACS 5-year'}
    result = measure(args)
    assert result['status']['status'] == 'pass'
    assert result['status']['sample_catalog_mismatch'] == []
    assert result['status']['sample_study_notes_unknown'] == []
    assert result['status']['ddi_sample_type_unknown'] == []
    assert result['sample_counts']['sample_label'].null_count() == len(result['sample_counts'])


@pytest.mark.parametrize('set_name,notes,expected', [
    ('monthly', ['January 2025 ASEC', 'February 2025 ASEC'], 'fail'),
    ('asec', ['March 2025 basic monthly'], 'fail'),
    ('monthly', ['January 2025', 'February 2025'], 'unresolved'),
    ('asec', [], 'unresolved'),
])
def test_cps_ddi_type_proof_is_explicit(set_name, notes, expected):
    args = list(delivery('cps', set_name))
    args[1]['study_notes'] = notes
    status = measure(args)['status']
    assert status['status'] == expected
    assert status['ddi_sample_type_mismatch'] or status['ddi_sample_type_unknown']


def test_integer_flags_unknown_lexical_categories_and_source_types_are_retained():
    args = list(delivery())
    args[2] = args[2].with_columns(pl.Series('QMIGRAT1', ['01', 'A9', '01']),
                                   pl.Series('QOTHER', [0, 2, None]))
    args[1]['variables'].append({'name': 'QOTHER', 'label': 'Other flag',
                                'implied_decimals': 0, 'instructions': [],
                                'categories': [{'value': '0', 'label': 'NIU'},
                                               {'value': '2', 'label': 'Allocated'}]})
    original_schema = args[2].collect_schema()
    result = measure(args)
    flags = result['flag_coverage']
    assert flags.filter(pl.col('flag').eq('QMIGRAT1')).select(
        'year', 'value', 'category_label', 'rows').rows() == [
            (2023, '01', 'NIU', 1), (2023, 'A9', None, 1), (2024, '01', 'NIU', 1)]
    assert flags.filter(pl.col('flag').eq('QOTHER')).select(
        'dtype', 'value', 'category_label', 'rows').rows() == [
            ('Int64', '0', 'NIU', 1), ('Int64', '2', 'Allocated', 1),
            ('Int64', None, None, 1)]
    assert args[2].collect_schema() == original_schema


def test_missing_selection_column_counts_every_row_as_unverified():
    args = list(delivery())
    args[2] = args[2].drop('EMPSTAT')
    assert measure(args)['status']['selection_unexpected_rows'] == 3


@pytest.mark.parametrize('month', [0, 13, None])
def test_invalid_months_fail_without_silent_filtering(month):
    args = list(delivery('cps', 'monthly'))
    args[2] = args[2].with_columns(pl.lit(month).cast(pl.Int64).alias('MONTH'))
    result = measure(args)
    assert result['status']['status'] == 'fail'
    assert result['status']['rows'] == 2
    assert result['sample_counts']['rows'].sum() == 2


def test_missing_five_year_component_is_explicit():
    args = list(delivery('acs', 'five_year'))
    args[2] = args[2].filter(pl.col('MULTYEAR').ne(2020))
    status = measure(args)['status']
    assert status['status'] == 'fail'
    assert status['multyears_missing'] == [2020]


def test_repeat_measurement_is_deterministic_and_metadata_unchanged():
    args = delivery()
    definition_before, ddi_before = copy.deepcopy(args[:2])
    first, second = measure(args), measure(args)
    assert first['status'] == second['status']
    for name in ('variable_inventory', 'sample_counts', 'flag_coverage'):
        assert_frame_equal(first[name], second[name])
    assert args[0] == definition_before
    assert args[1] == ddi_before


def test_unrequested_interior_month_is_reported_without_inventing_catalog_availability():
    args = list(delivery('cps', 'monthly'))
    args[0]['samples'] = {'cps2025_01b': {}, 'cps2025_03b': {}}
    args[1]['study_notes'] = ['January 2025 basic monthly', 'March 2025 basic monthly']
    args[2] = args[2].with_columns(pl.Series('MONTH', [1, 3]))
    status = measure(args)['status']
    assert status['periods_missing'] == []
    assert status['periods_not_requested'] == ['2025-02']
    assert status['periods_absent'] == ['2025-02']
    assert status['status'] == 'pass'
