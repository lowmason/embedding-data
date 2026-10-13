import polars as pl
import pytest
from ita_verification_fixtures import rows
from polars.testing import assert_frame_equal

from embedding_data import ita_county_verification as county

def hud_rows():
    return pl.DataFrame(
        {
            'zip_key': ['02134', '02135', '02135', '06001'],
            'county_geoid': ['25025', '25025', '25017', '09003'],
            'bus_ratio': [1.0, 0.6, 0.4, 1.0],
        }
    )

def test_candidates_retain_ambiguity_and_ct_vintage():
    result = county.zip_candidates(hud_rows()).sort('zip_key')
    assert result['n_business_counties'].to_list() == [1, 2, 1]
    assert result['zip_single_county'].to_list() == ['25025', None, None]
    assert result['flag_zip_legacy_ct'].to_list() == [False, False, True]

def test_sample_is_stable_with_duplicate_and_conflicting_record_ids():
    lf = rows(
        [
            {}, {}, {
                'industry_description': 'Other'
            }, {
                'id': 2,
                'zip_code': 'bad'
            }, {
                'year_filing_for': 2024,
                'id': 3
            }
        ]
    )
    candidates = county.zip_candidates(hud_rows())
    sample = county.stratified_sample(lf, candidates, per_stratum=1)
    shuffled = county.stratified_sample(lf.collect().reverse().lazy(), candidates, per_stratum=1)
    assert_frame_equal(sample, shuffled)
    assert sample['row_key'].n_unique() == sample.height
    assert sample.height == 3
    assert sorted(sample['population_n'].to_list()) == [1, 1, 2]
    assert sample['sample_weight'].sum() == 4

def test_parser_supports_matches_no_matches_and_ties():
    text = (
        'a,"1 Main St,Town,MA,02134",Match,Exact,matched,"-71,42",7,L,25,025,1,1\n'
        'b,"bad",No_Match\n'
        'c,"ambiguous",Tie\n'
    )
    result = county.parse_geocodes(text)
    assert result['county_geoid'].to_list() == ['25025', None, None]
    with pytest.raises(ValueError, match='duplicate'):
        county.parse_geocodes(text + 'b,"bad",No_Match\n')

def test_coverage_and_agreement_use_separate_denominators():
    sample = county.stratified_sample(
        rows(
            [
                {},
                {
                    'id': 2,
                    'zip_code': '02135'
                },
                {
                    'id': 3,
                    'zip_code': 'bad'
                },
                {
                    'id': 4,
                    'zip_code': '06001',
                    'state': 'CT'
                },
            ]
        ), county.zip_candidates(hud_rows())
    )
    geocodes = sample.select('row_key').with_columns(
        geocode_status=pl.lit('Match'),
        match_type=pl.lit('Exact'),
        county_geoid=pl.when(pl.Series(sample['state'].to_list()).eq('CT')
                             ).then(pl.lit('09110')).otherwise(pl.lit('25025')),
    )
    _, result = county.county_report(sample, geocodes)
    assert result['n_sample'] == 4
    assert result['n_geocode_exact'] == 4
    assert result['n_zip_covered'] == 3
    assert result['n_zip_single_compatible'] == 1
    assert result['n_joint_dominant_comparable'] == 2
    assert result['n_joint_dominant_agree'] == 2
    assert result['n_ct_incomparable'] == 1
    assert result['n_joint_single_comparable'] == 1
    assert result['n_joint_single_agree'] == 1
    assert result['share_zip_single_compatible'] == 0.25
    assert result['share_joint_single_agree'] == 1.0

def test_status_scope_and_incompatible_geocoder_are_reported():
    sample = county.stratified_sample(
        rows(
            [
                {},
                {
                    'id': 2
                },
                {
                    'id': 3
                },
                {
                    'id': 4
                },
                {
                    'id': 5,
                    'state': 'PR'
                },
                {
                    'id': 6,
                    'state': 'CT',
                    'zip_code': '06001'
                },
            ]
        ), county.zip_candidates(hud_rows())
    )
    statuses = [
        ('Match', 'Exact', '25025'), ('Match', 'Non_Exact', '25025'), ('No_Match', None, None),
        ('Tie', None, None), ('Match', 'Exact', '72001'), ('Match', 'Exact', '09003')
    ]
    geocodes = sample.sort('id').select('row_key').hstack(
        pl.DataFrame(
            statuses,
            schema=['geocode_status', 'match_type', 'county_geoid'],
            orient='row',
        )
    )
    _, result = county.county_report(sample, geocodes)
    assert result['n_geocode_non_exact'] == 1
    assert result['n_geocode_no_match'] == 1
    assert result['n_geocode_tie'] == 1
    assert result['n_geocode_legacy_ct'] == 1
    assert result['n_out_of_scope'] == 1
    assert result['n_proposed_assignable'] == 4
    assert result['share_joint_single_agree'] == 1.0
