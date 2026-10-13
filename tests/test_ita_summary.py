import io
import zipfile

import polars as pl
import pytest
from ita_fixtures import (
    COLUMNS_2023,
    MEMBER_NAMES,
    OLD_COLUMNS,
    RELEASE_NAMES,
    csv_bytes,
    record,
    year_file,
    zipped,
)
from polars.exceptions import InvalidOperationError

from embedding_data import ita_summary

HARMONIZED_SCHEMA = {
    'id': pl.Int64, 'establishment_id': pl.Int64, 'establishment_type': pl.Int64,
    'size': pl.Int64, 'annual_average_employees': pl.Int64, 'total_hours_worked': pl.Int64,
    'year_filing_for': pl.Int64, 'establishment_name': pl.String, 'company_name': pl.String,
    'ein': pl.String, 'street_address': pl.String, 'city': pl.String, 'state': pl.String,
    'zip_code': pl.String, 'industry_description': pl.String, 'naics_code': pl.String,
    'naics_year': pl.Int64, 'naics_year_from_dictionary': pl.Boolean,
    'size_class': pl.Int64, 'source_file': pl.String,
}


def harmonized(tmp_path, year, data, name=None):
    '''Write data as year's raw file under tmp_path and collect its harmonized rows.'''
    raw_file = tmp_path / (name or RELEASE_NAMES[year])
    raw_file.write_bytes(data)
    source_file = f'osha/summary/{year}/{raw_file.name}'
    utf8_path = tmp_path / f'{year}.utf8.csv'
    return ita_summary.harmonize_file(raw_file, year, source_file, utf8_path).collect()


def expected_row(year, **changes):
    row = {
        'id': year * 10, 'establishment_id': year, 'establishment_type': 1,
        'size': 2 if year <= 2022 else 22, 'annual_average_employees': 100,
        'total_hours_worked': 200_000, 'year_filing_for': year,
        'establishment_name': 'Acme Plant 7', 'company_name': 'Acme Holdings, Inc.',
        'ein': None if year <= 2018 else '012345678', 'street_address': '1 Main St',
        'city': 'Springfield', 'state': 'IL', 'zip_code': '02134',
        'industry_description': 'Fabricated structural metal', 'naics_code': '332312',
        'naics_year': 2012 if year <= 2022 else 2022,
        'naics_year_from_dictionary': year <= 2022, 'size_class': 2,
        'source_file': f'osha/summary/{year}/{RELEASE_NAMES[year]}',
    }
    row.update(changes)
    return row


@pytest.mark.parametrize('year', range(2016, 2026))
def test_every_published_format_harmonizes_to_one_schema(tmp_path, year):
    frame = harmonized(tmp_path, year, year_file(year))

    assert frame.schema == HARMONIZED_SCHEMA
    assert frame.rows(named=True) == [expected_row(year)]


def test_size_two_and_its_2023_split_share_one_harmonized_class(tmp_path):
    records = [
        record(2023, id=str(n), size=size) for n, size in enumerate(['1', '2', '21', '22', '3'])
    ]

    frame = harmonized(tmp_path, 2023, year_file(2023, records))

    assert frame['size'].to_list() == [1, 2, 21, 22, 3]
    assert frame['size_class'].to_list() == [1, 2, 2, 2, 3]


def test_naics_year_before_2023_comes_from_the_dictionary_and_says_so(tmp_path):
    records = [record(2022), record(2022, id='2', naics_code='')]

    frame = harmonized(tmp_path, 2022, year_file(2022, records))

    assert frame.select('naics_code', 'naics_year', 'naics_year_from_dictionary').rows() == [
        ('332312', 2012, True),
        (None, None, False),
    ]


def test_a_delivered_naics_year_is_kept_and_not_marked(tmp_path):
    records = [record(2024, naics_year='2012'), record(2024, id='2', naics_code='', naics_year='')]

    frame = harmonized(tmp_path, 2024, year_file(2024, records))

    assert frame.select('naics_code', 'naics_year', 'naics_year_from_dictionary').rows() == [
        ('332312', 2012, False),
        (None, None, False),
    ]


def test_a_fraction_that_is_not_zero_fails(tmp_path):
    data = year_file(2019, [record(2019, annual_average_employees='23.50')])

    with pytest.raises(InvalidOperationError):
        harmonized(tmp_path, 2019, data)


@pytest.mark.parametrize(
    ('fields', 'message'),
    [
        ({'year_filing_for': '2023'}, 'filed for a year other than 2024'),
        ({'naics_code': '33231'}, 'NAICS code that is not six digits'),
        ({'size': '4'}, 'size code the dictionary does not define'),
        ({'naics_year': '2007'}, 'NAICS vintage other than 2012, 2017 or 2022'),
    ],
    ids=['other-year', 'naics-code', 'size-code', 'naics-vintage'],
)
def test_rows_no_rule_covers_fail_the_build(tmp_path, fields, message):
    with pytest.raises(ValueError, match=message):
        harmonized(tmp_path, 2024, year_file(2024, [record(2024, **fields)]))


def test_a_missing_column_fails_the_build(tmp_path):
    columns = tuple(column for column in COLUMNS_2023 if column != 'naics_year')
    data = zipped(MEMBER_NAMES[2023], csv_bytes(columns, [record(2023)]))

    with pytest.raises(ValueError, match=r"missing columns \['naics_year'\]"):
        harmonized(tmp_path, 2023, data)


def test_a_zip_must_hold_exactly_one_csv(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('a.csv', b'id\r\n')
        archive.writestr('b.csv', b'id\r\n')

    with pytest.raises(ValueError, match='expected one CSV member'):
        harmonized(tmp_path, 2016, buffer.getvalue())


def test_bom_mojibake_and_windows_1252_bytes_survive_as_delivered(tmp_path):
    # 2022 opens with a UTF-8 BOM and carries UTF-8 mojibake of a Windows-1252 apostrophe;
    # other years carry raw Windows-1252 bytes. Text is kept as delivered, not repaired.
    data_2022 = year_file(2022, [record(2022, company_name='Farmerâ€™s Co-op')])
    text_2021 = csv_bytes(OLD_COLUMNS, [record(2021, company_name='Owner’s Choice')])
    data_2021 = zipped(MEMBER_NAMES[2021], text_2021.replace('’'.encode(), b'\x92'))

    frame_2022 = harmonized(tmp_path, 2022, data_2022)
    frame_2021 = harmonized(tmp_path, 2021, data_2021)

    assert frame_2022['company_name'].to_list() == ['Farmerâ€™s Co-op']
    assert frame_2022['id'].to_list() == [20220]
    assert frame_2021['company_name'].to_list() == ['Owner’s Choice']


def test_implausible_records_are_flagged_not_dropped(tmp_path):
    cases = [  # (employees, hours, size) -> (employment, hours per employee, below size)
        (('100', '200000', '22'), (False, False, False)),  # 2,000 hours each
        (('100', '50000', '22'), (False, False, False)),   # 500, the inclusive lower bound
        (('100', '400000', '22'), (False, False, False)),  # 4,000, the inclusive upper bound
        (('100', '49900', '22'), (False, True, False)),    # 499
        (('100', '400100', '22'), (False, True, False)),   # 4,001
        (('100', '', '22'), (False, True, False)),         # hours missing
        (('0', '1000', '22'), (True, None, False)),        # zero employment: no ratio
        (('-5', '1000', '22'), (True, None, False)),       # negative employment: flagged, no ratio
        (('', '1000', '22'), (True, None, False)),         # employment missing: no ratio
        (('10', '20000', '1'), (False, False, True)),      # fewer than 20 at peak
        (('100', '200000', ''), (False, False, None)),     # size missing
    ]
    records = [
        record(2024, id=str(n), annual_average_employees=e, total_hours_worked=h, size=s)
        for n, ((e, h, s), _) in enumerate(cases)
    ]

    frame = ita_summary.add_flags(harmonized(tmp_path, 2024, year_file(2024, records)).lazy())
    flags = frame.select(
        'flag_employment', 'flag_hours_per_employee', 'flag_below_filing_size'
    ).collect()

    assert flags.rows() == [expected for _, expected in cases]
    assert flags.schema == {
        'flag_employment': pl.Boolean,
        'flag_hours_per_employee': pl.Boolean,
        'flag_below_filing_size': pl.Boolean,
    }
