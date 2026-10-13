import polars as pl

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
