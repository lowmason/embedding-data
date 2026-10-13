import polars as pl

from embedding_data import ita_verification as verify

def rows(records):
    base = {
        'year_filing_for': 2023,
        'id': 1,
        'establishment_id': 10,
        'ein': '012345678',
        'company_name': 'Acme',
        'establishment_name': 'Plant',
        'street_address': '1 Main St',
        'city': 'Town',
        'state': 'MA',
        'zip_code': '02134',
        'industry_description': 'Steel',
        'naics_year': 2022,
        'naics_code': '332312',
        'source_file': 'osha/fixture.csv',
    }
    return pl.DataFrame([{**base, **item} for item in records]).lazy()

def test_unicode_and_employer_missingness():
    assert verify.normalize_key('  STRAßE\u00a0Steel  ') == 'strasse steel'
    out = verify.with_keys(
        rows(
            [
                {
                    'ein': None,
                    'company_name': None
                },
                {
                    'id': 2,
                    'ein': '12345678',
                    'industry_description': ' N/A '
                },
            ]
        )
    ).collect()
    assert out['employer_key'].to_list() == [None, 'ein:012345678']
    assert out['flag_ein_padded'].to_list() == [False, True]
    assert out['flag_placeholder'].to_list() == [False, True]

def test_description_repetition_never_groups_unknown_employers():
    lf = rows(
        [
            {
                'industry_description': ' Manufacturing '
            },
            {
                'id': 2,
                'industry_description': 'MANUFACTURING'
            },
            {
                'id': 3,
                'ein': None,
                'company_name': None,
                'industry_description': None
            },
            {
                'id': 4,
                'ein': None,
                'company_name': None,
                'industry_description': 'N/A'
            },
        ]
    )
    titles = pl.DataFrame({'vintage': [2022], 'code': ['31-33'], 'title': ['Manufacturing']})
    report = verify.description_report(lf, titles).row(0, named=True)
    assert report['n_rows'] == 4
    assert report['n_empty'] == 1 and report['n_placeholder'] == 1
    assert report['n_copied_any'] == 2 and report['n_employer_unknown'] == 2
    assert report['n_repeat_rows'] == 2 and report['n_repeat_excess'] == 1

def test_link_denominators_null_ein_collisions_and_changed_id():
    lf = rows(
        [
            {},
            {},  # Exact duplicate, one cohort ID after collapsing.
            {
                'id': 2,
                'establishment_id': 20,
                'ein': None,
                'street_address': '2 Main St'
            },
            {
                'id': 3,
                'establishment_id': 30,
                'street_address': '3 Main St'
            },
            {
                'year_filing_for': 2024,
                'id': 4
            },
            {
                'year_filing_for': 2024,
                'id': 5,
                'establishment_id': 20,
                'ein': None,
                'street_address': '2 Main St'
            },
            {
                'year_filing_for': 2024,
                'id': 6,
                'establishment_id': 31,
                'street_address': '3 Main St'
            },
        ]
    )
    out = verify.link_report(lf, 2023, 2024)
    assert out['n_cohort_ids'] == 3 and out['n_unique_cohort_ids'] == 3
    assert out['n_reappeared'] == 2 and out['n_same_ein_address'] == 1
    assert out['n_reappeared_ein_unknown'] == 1
    assert out['n_unique_address_matches'] == 2
    assert out['n_address_matches_different_id'] == 1
    conflict = pl.concat(
        [lf, rows([
            {
                'year_filing_for': 2024,
                'id': 7,
                'street_address': 'Other Street'
            },
        ])]
    )
    assert verify.link_report(conflict, 2023, 2024)['n_same_ein_address'] == 0

def test_reappearing_id_with_unusable_address_is_still_present():
    lf = rows([{}, {'year_filing_for': 2024, 'id': 2, 'street_address': ''}])
    out = verify.link_report(lf, 2023, 2024)
    assert out['n_reappeared'] == 1
    assert out['n_same_ein_address'] == 0

def test_title_vintage_denominator_and_unknown_employer_repetition():
    lf = rows(
        [
            {
                'industry_description': 'Steel',
                'naics_year': 2022
            },
            {
                'id': 2,
                'industry_description': 'Steel',
                'naics_year': 2017
            },
            {
                'id': 3,
                'industry_description': 'Steel',
                'naics_year': None
            },
            {
                'id': 4,
                'ein': None,
                'company_name': None,
                'industry_description': 'Other'
            },
            {
                'id': 5,
                'ein': None,
                'company_name': None,
                'industry_description': 'Other'
            },
        ]
    )
    titles = pl.DataFrame(
        {
            'vintage': [2022, 2022, 2017],
            'code': ['111111', '222222', '333333'],
            'title': ['Steel', 'Steel', 'Different'],
        }
    )
    report = verify.description_report(lf, titles).row(0, named=True)
    assert report['n_rows'] == 5
    assert report['n_copied_any'] == 3
    assert report['n_native_title_match'] == 1
    assert report['n_vintage_unknown'] == 1
    assert report['share_native_title_match'] == 0.25
    assert report['share_copied_any'] == 0.6
    assert report['n_repeat_rows'] == 3
    assert report['n_repeat_excess'] == 2

def test_quality_counts_exact_duplicates_and_preserves_source():
    lf = rows([{}, {}, {'id': 2, 'ein': '000000000', 'company_name': '', 'zip_code': 'bad'}])
    source = lf.collect()
    report = verify.quality_report(lf).row(0, named=True)
    assert report == {
        'year_filing_for': 2023,
        'n_company_empty': 1,
        'n_ein_unusable': 1,
        'n_zip_unusable': 1,
        'n_distinct_record_ids': 2,
        'n_distinct_establishment_ids': 1,
        'n_rows': 3,
        'n_distinct_rows': 2,
        'n_exact_duplicate_excess': 1,
    }
    assert verify.with_keys(lf).collect().select(source.columns).equals(source)

def test_zip_formats_company_fallback_and_padded_link_separation():
    keyed = verify.with_keys(
        rows(
            [
                {
                    'ein': 'invalid',
                    'company_name': ' ACME ',
                    'zip_code': '2134'
                },
                {
                    'id': 2,
                    'zip_code': '02134-1234'
                },
                {
                    'id': 3,
                    'zip_code': '021341234'
                },
                {
                    'id': 4,
                    'zip_code': ''
                },
            ]
        )
    ).collect()
    assert keyed['employer_key'][0] == 'company:acme'
    assert keyed['zip_key'].to_list() == ['02134', '02134', '02134', None]
    assert keyed['zip_format'].to_list() == [
        'padded_four_digit', 'zip_plus_four', 'zip_plus_four', 'missing'
    ]
    out = verify.link_report(
        rows([
            {
                'ein': '12345678'
            },
            {
                'year_filing_for': 2024,
                'id': 2
            },
        ]), 2023, 2024
    )
    assert out['n_same_ein_address'] == 0
    assert out['n_same_ein_address_including_padded'] == 1
    assert out['n_same_raw_ein_address'] == 0
    assert out['n_unique_address_matches'] == 0

def test_empty_cohort_rates_are_missing():
    out = verify.link_report(rows([{}]), 2022, 2024)
    assert out['n_cohort_ids'] == 0
    assert out['n_reappeared'] == 0
    assert out['share_raw_reappeared'] is None
    assert out['share_same_ein_address'] is None
    assert out['share_address_matches_different_id'] is None
