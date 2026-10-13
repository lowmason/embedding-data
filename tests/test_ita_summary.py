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
    write_release,
    year_file,
    zipped,
)
from polars.exceptions import InvalidOperationError
from polars.testing import assert_frame_equal

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


TABLE_SCHEMA = {
    'year_filing_for': pl.Int64, 'id': pl.Int64, 'establishment_id': pl.Int64,
    'establishment_name': pl.String, 'company_name': pl.String, 'ein': pl.String,
    'street_address': pl.String, 'city': pl.String, 'state': pl.String, 'zip_code': pl.String,
    'naics_code': pl.String, 'naics_year': pl.Int64, 'naics_year_from_dictionary': pl.Boolean,
    'industry_description': pl.String, 'establishment_type': pl.Int64, 'size': pl.Int64,
    'size_class': pl.Int64, 'annual_average_employees': pl.Int64,
    'total_hours_worked': pl.Int64, 'flag_employment': pl.Boolean,
    'flag_hours_per_employee': pl.Boolean, 'flag_below_filing_size': pl.Boolean,
    'source_file': pl.String,
}
NEXT_2025 = 'ITA_300A_Summary_Data_2025_through_11-30-2026.csv'


def table_path(data_directory):
    return data_directory / 'derived/osha' / ita_summary.TABLE_NAME


def test_every_year_stacks_into_one_sorted_table_without_injury_counts(data_directory):
    write_release(data_directory, 2022)
    unsorted = [record(2023, id='5'), record(2023, id='3')]
    write_release(data_directory, 2023, year_file(2023, unsorted))
    write_release(data_directory, 2024)

    table = pl.read_parquet(ita_summary.build_summary_table(data_directory))

    assert table.columns == list(TABLE_SCHEMA)
    assert table.schema == TABLE_SCHEMA
    assert table.select('year_filing_for', 'id').rows() == [
        (2022, 20220), (2023, 3), (2023, 5), (2024, 20240),
    ]
    assert table['source_file'].unique(maintain_order=True).to_list() == [
        f'osha/summary/{year}/{RELEASE_NAMES[year]}' for year in (2022, 2023, 2024)
    ]


def test_each_year_uses_its_latest_release(data_directory):
    write_release(data_directory, 2025)
    newer = [record(2025, id=str(n)) for n in range(3)]
    write_release(data_directory, 2025, year_file(2025, newer), NEXT_2025)

    table = pl.read_parquet(ita_summary.build_summary_table(data_directory))

    assert table.height == 3
    assert table['source_file'].unique().to_list() == [f'osha/summary/2025/{NEXT_2025}']


def test_two_files_in_a_year_without_distinct_through_dates_fail(data_directory):
    write_release(data_directory, 2016)
    write_release(data_directory, 2016, name='ITA Data CY 2016 (1).zip')

    with pytest.raises(ValueError, match='distinct through-date'):
        ita_summary.build_summary_table(data_directory)


def test_hidden_files_and_partial_downloads_beside_a_release_are_ignored(data_directory):
    release = write_release(data_directory, 2016)
    (release.parent / '.DS_Store').write_bytes(b'\x00\x00\x00\x01Bud1')
    (release.parent / 'ITA Data CY 2016.zip.part').write_bytes(b'PK')

    table = pl.read_parquet(ita_summary.build_summary_table(data_directory))

    assert table['source_file'].to_list() == ['osha/summary/2016/ITA Data CY 2016.zip']


def test_an_unrecorded_raw_file_is_not_stacked(data_directory):
    write_release(data_directory, 2024, recorded=False)

    with pytest.raises(KeyError, match='not recorded'):
        ita_summary.build_summary_table(data_directory)

    assert not table_path(data_directory).exists()


def test_the_table_is_rebuilt_on_every_call(data_directory):
    write_release(data_directory, 2025)
    assert pl.read_parquet(ita_summary.build_summary_table(data_directory)).height == 1
    newer = [record(2025, id=str(n)) for n in range(3)]
    write_release(data_directory, 2025, year_file(2025, newer), NEXT_2025)

    assert pl.read_parquet(ita_summary.build_summary_table(data_directory)).height == 3


def test_a_failed_build_keeps_the_previous_table(data_directory):
    write_release(data_directory, 2025)
    table = ita_summary.build_summary_table(data_directory)
    before = table.read_bytes()
    bad = year_file(2025, [record(2025, annual_average_employees='23.50')])
    write_release(data_directory, 2025, bad, NEXT_2025)

    with pytest.raises(InvalidOperationError):
        ita_summary.build_summary_table(data_directory)

    assert table.read_bytes() == before
    assert sorted(path.name for path in table.parent.iterdir()) == [ita_summary.TABLE_NAME]


def test_rebuilding_unchanged_inputs_gives_the_same_table(data_directory):
    for year in (2019, 2022, 2025):
        write_release(data_directory, year)
    first = pl.read_parquet(ita_summary.build_summary_table(data_directory))

    second = pl.read_parquet(ita_summary.build_summary_table(data_directory))

    assert_frame_equal(first, second)


def test_totals_report_sets_rows_beside_published_counts(data_directory):
    write_release(data_directory, 2022)
    two_rows = [record(2023, id='1'), record(2023, id='2')]
    write_release(data_directory, 2023, year_file(2023, two_rows))
    write_release(data_directory, 2024)

    report = ita_summary.totals_report(ita_summary.build_summary_table(data_directory))

    assert report.select('year_filing_for', 'rows', 'published', 'gap').rows() == [
        (2022, 1, None, None),
        (2023, 2, 385_488, -385_486),
        (2024, 1, 390_000, -389_999),
    ]
    assert ita_summary.report_lines(report) == [
        '2022: 1 rows from osha/summary/2022/ITA-data-cy2022.zip; no published count located',
        '2023: 2 rows from osha/summary/2023/ITA_300A_Summary_Data_2023_through_12-31-2024.zip;'
        ' OSHA published exactly 385,488 as of 2024-05-31'
        ' (OSHA 2023 Work-Related Injury and Illness Summary); gap -385,486',
        '2024: 1 rows from osha/summary/2024/ITA_300A_Summary_Data_2024_through_12-31-2025.zip;'
        ' OSHA published over 390,000'
        ' (OSHA 2024 Work-Related Injury and Illness Summary); gap -389,999',
    ]
