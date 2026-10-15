import polars as pl
import pytest
from polars.testing import assert_frame_equal
from target_fixtures import assignment_case, assignment_inputs

from embedding_data import ita_assignment as ia
from embedding_data.geography_hud import LOOKUP_SCHEMA
from embedding_data.geography_tables import COUNTY_SCHEMA
from embedding_data.ita_assignment_prepare import request_frames

@pytest.mark.parametrize('status,kind,returned,zip_code,state,method,chosen', [
    ('Match', 'Exact', '01001', '00003', 'AL', 'census_exact', '01001'),
    ('Match', 'Exact', '01001', '00005', 'AL', 'census_exact', '01001'),
    ('Match', 'Non_Exact', '51510', '00001', 'AL', 'hud_singleton', '01001'),
    ('No_Match', None, None, '00001', 'AL', 'hud_singleton', '01001'),
    ('Tie', None, None, '00001', 'AL', 'hud_singleton', '01001'),
    ('Match', 'Exact', '01999', '00001', 'AL', 'hud_singleton', '01001'),
    ('Match', 'Exact', '09001', '00001', 'AL', 'hud_singleton', '01001'),
    ('Match', 'Exact', '72001', '00001', 'AL', 'unassigned', None),
    ('Match', 'Exact', '01001', '00001', ' PR ', 'unassigned', None),
    ('No_Match', None, None, '00003', 'AL', 'unassigned', None),
    ('No_Match', None, None, '00002', 'AL', 'unassigned', None),
    ('No_Match', None, None, '99999', 'AL', 'unassigned', None),
    ('Match', 'Exact', '51001', '99999', 'VA', 'census_exact', '51001'),
    ('Match', 'Exact', '09110', '99999', 'CT', 'census_exact', '09110'),
])
def test_adopted_county_precedence(status, kind, returned, zip_code, state, method, chosen):
    row = assignment_case(status, kind, returned, zip_code, state)
    assert row['assignment_method'] == method
    assert row['county_geoid'] == chosen


@pytest.mark.parametrize('prefix,state', [('60', 'AS'), ('66', 'GU'), ('69', 'MP'),
                                         ('72', 'PR'), ('74', 'UM'), ('78', 'VI')])
def test_scope_independent_of_exactness(prefix, state):
    row = assignment_case('Match', 'Non_Exact', prefix + '001', '00001', 'AL')
    assert row['flag_geocode_county_out_of_scope']
    assert not row['flag_geocode_county_incompatible']
    assert row['assignment_method'] == 'hud_singleton'
    veto = assignment_case('Match', 'Exact', '01001', '00001', ' ' + state.lower() + ' ')
    assert veto['flag_delivered_state_out_of_scope']
    assert veto['county_geoid'] is None


@pytest.mark.parametrize('returned,legacy,incompatible', [
    ('09001', True, True), ('01999', False, True), ('09110', False, False),
    ('72001', False, False), (None, False, False)])
def test_independent_returned_flags(returned, legacy, incompatible):
    row = assignment_case('Match', 'Non_Exact', returned, '00001', 'AL')
    assert row['flag_geocode_county_legacy_ct'] == legacy
    assert row['flag_geocode_county_incompatible'] == incompatible


@pytest.mark.parametrize('zipcode,status,count,business,dominant', [
    ('00003', 'multiple_counties', 2, ['01001', '72001'], ['01001']),
    ('00004', 'multiple_counties', 2, ['01001', '51510'], ['01001', '51510']),
    ('00002', 'zero_business', 1, [], []), ('99999', 'absent', 0, [], []),
    ('00007', 'incompatible_county', 1, ['09001'], ['09001'])])
def test_hud_evidence_preserved(zipcode, status, count, business, dominant):
    row = assignment_case('No_Match', None, None, zipcode, 'AL')
    assert row['eligibility_status'] == status
    assert row['n_hud_rows'] == count
    assert row['business_counties'] == business
    assert row['dominant_candidates'] == dominant
    assert row['county_geoid'] is None
    assert row['flag_zip_zero_business'] == (status == 'zero_business')


@pytest.mark.parametrize('changes,incomplete', [({}, False), ({'street': ' \t '}, True),
    ({'city': None}, True), ({'state': ''}, True), ({'zip_code': 'bad'}, True),
    ({'street': '', 'city': '', 'state': '', 'zip_code': ''}, True)])
def test_request_completeness(tmp_path, changes, incomplete):
    row = ia.assign(*assignment_inputs(tmp_path, **changes)).collect().row(0, named=True)
    assert row['flag_request_incomplete'] == incomplete


def test_prefix_schema_order_duplicates_and_report(tmp_path):
    canonical, _, responses, hud, counties = assignment_inputs(tmp_path)
    canonical = pl.concat([canonical, canonical, canonical.with_columns(
        pl.lit(2024, dtype=pl.Int64).alias('year_filing_for'))])
    index, _ = request_frames(canonical)
    result = ia.assign(canonical, index.reverse(), responses, hud, counties)
    frame = result.collect()
    assert len(canonical.collect_schema()) == 38
    assert_frame_equal(frame.select(canonical.collect_schema().names()), canonical.collect())
    assert frame['source_row'].to_list() == [0, 1, 2]
    assert frame['source_row'].dtype == pl.UInt64
    assert list(frame.schema.items()) == list(ia.assignment_schema(
        canonical.collect_schema()).items())
    assert frame.columns[38:44] == ['source_row', 'request_id', 'zip_key',
                                   'geocode_status', 'match_type', 'geocode_county_geoid']
    assert frame.columns[44:44 + len(LOOKUP_SCHEMA) - 1] == list(LOOKUP_SCHEMA)[1:]
    ia.validate_assignments(result, canonical, counties)
    report = ia.assignment_report(result)
    assert report['input_rows'] == 3
    for key in ['assignment_reasons', 'assignment_methods', 'geocode_coverage',
                'delivered_scope', 'returned_scope']:
        assert sum(row['rows'] for row in report[key]) == 3
    diagnostics = report['diagnostic_flags']
    assert any(row['null_rows'] == 2 for row in diagnostics if row['year_filing_for'] == 2023)
    assert report['partition_semantics'] == 'disjoint within each partition'
    assert report['diagnostic_semantics'] == 'overlapping flags; not county accuracy'


@pytest.mark.parametrize('county,cbsa,kind,role', [
    ('01001', '10000', 'metropolitan', 'central'),
    ('51510', '10000', 'metropolitan', 'outlying'),
    ('09110', '20000', 'micropolitan', 'central'), ('51001', None, None, None)])
def test_chosen_attributes(tmp_path, county, cbsa, kind, role):
    inputs = assignment_inputs(tmp_path, returned=county)
    frame = ia.assign(*inputs).collect()
    assert_frame_equal(frame.select(list(COUNTY_SCHEMA)), inputs[-1].filter(
        pl.col('county_geoid').eq(county)))
    assert frame.select('cbsa_code', 'cbsa_type', 'cbsa_role').row(0) == (cbsa, kind, role)


@pytest.mark.parametrize('defect', ['index_duplicate', 'index_missing', 'index_extra',
    'response_duplicate', 'response_missing', 'response_extra', 'overlap', 'schema'])
def test_invalid_join_contract_fails(tmp_path, defect):
    canonical, index, responses, hud, counties = assignment_inputs(tmp_path)
    if defect == 'index_duplicate':
        index = pl.concat([index, index])
    elif defect == 'index_missing':
        index = index.head(0)
    elif defect == 'index_extra':
        index = pl.concat([index, index.with_columns(pl.lit(1, dtype=pl.UInt64)
                                                     .alias('source_row'))])
    elif defect == 'response_duplicate':
        responses = pl.concat([responses, responses])
    elif defect == 'response_missing':
        responses = responses.head(0)
    elif defect == 'response_extra':
        responses = pl.concat([responses, responses.with_columns(
            pl.lit('unexpected').alias('request_id'))])
    elif defect == 'overlap':
        canonical = canonical.with_columns(pl.lit('bad').alias('county_geoid'))
    else:
        hud = hud.with_columns(pl.col('n_hud_rows').cast(pl.Int32))
    with pytest.raises(ValueError):
        ia.assign(canonical, index, responses, hud, counties).collect()


@pytest.mark.parametrize('defect', ['prefix', 'order', 'county', 'flag_null', 'row_loss'])
def test_validation_rejects_corruption(tmp_path, defect):
    canonical, index, responses, hud, counties = assignment_inputs(tmp_path)
    result = ia.assign(canonical, index, responses, hud, counties)
    if defect == 'prefix':
        result = result.with_columns(pl.lit('changed').alias('city'))
    elif defect == 'order':
        result = result.with_columns(pl.lit(1, dtype=pl.UInt64).alias('source_row'))
    elif defect == 'county':
        result = result.with_columns(pl.lit('wrong').alias('county_title'))
    elif defect == 'flag_null':
        result = result.with_columns(pl.lit(None, dtype=pl.Boolean).alias('flag_assignment_hud'))
    else:
        result = result.head(0)
    with pytest.raises(ValueError):
        ia.validate_assignments(result, canonical, counties)


def test_missing_required_county_join_fails(tmp_path):
    canonical, index, responses, hud, counties = assignment_inputs(
        tmp_path, status='No_Match', kind=None, returned=None)
    for invalid in [None, '01999']:
        bad_hud = hud.with_columns(pl.lit(invalid, dtype=pl.String).alias('zip_fallback_county'))
        with pytest.raises(ValueError, match='county'):
            ia.assign(canonical, index, responses, bad_hud, counties)


def test_all_years_and_empty_input(tmp_path):
    canonical, _, responses, hud, counties = assignment_inputs(tmp_path)
    years = pl.concat([canonical.with_columns(pl.lit(year, dtype=pl.Int64)
                                             .alias('year_filing_for'))
                       for year in range(2016, 2026)])
    index, _ = request_frames(years)
    result = ia.assign(years, index, responses, hud, counties)
    assert result.select(pl.len()).collect().item() == 10
    assert len(ia.assignment_report(result)['assignment_methods']) == 10
    empty = ia.assign(canonical.head(0), index.head(0), responses.head(0), hud, counties)
    assert ia.assignment_report(empty)['input_rows'] == 0


@pytest.mark.parametrize('zip_code', ['00003', '00004', '00005', '00006', '00007', '00009'])
def test_every_selected_lookup_field_survives(tmp_path, zip_code):
    inputs = assignment_inputs(tmp_path, zip_code=zip_code)
    result = ia.assign(*inputs).collect()
    assert_frame_equal(result.select(list(LOOKUP_SCHEMA)),
                       inputs[-2].filter(pl.col('zip_key').eq(zip_code)))


@pytest.mark.parametrize('reference', ['hud', 'counties'])
def test_reference_fanout_rejected(tmp_path, reference):
    canonical, index, responses, hud, counties = assignment_inputs(tmp_path)
    if reference == 'hud':
        hud = pl.concat([hud, hud.head(1)])
    else:
        counties = pl.concat([counties, counties.head(1)])
    with pytest.raises(ValueError, match='duplicate'):
        ia.assign(canonical, index, responses, hud, counties)


def test_report_counts_true_and_null_source_diagnostics(tmp_path):
    canonical, _, responses, hud, counties = assignment_inputs(tmp_path)
    canonical = pl.concat([canonical, canonical.with_columns(
        pl.lit(True).alias('flag_outside_filing_rule'))])
    index, _ = request_frames(canonical)
    report = ia.assignment_report(ia.assign(canonical, index, responses, hud, counties))
    flag = next(row for row in report['diagnostic_flags']
                if row['flag'] == 'flag_outside_filing_rule')
    assert flag == {'year_filing_for': 2023, 'flag': 'flag_outside_filing_rule',
                    'true_rows': 1, 'null_rows': 1}
