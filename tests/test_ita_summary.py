import io
import re
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


def source_file(year, name=None):
    return f'osha/summary/{year}/{name or RELEASE_NAMES[year]}'


def harmonize_raw(tmp_path, year, data, name=None):
    '''Write data as year's raw file under tmp_path and return its harmonized, lazy rows.'''
    raw_file = tmp_path / (name or RELEASE_NAMES[year])
    raw_file.write_bytes(data)
    utf8_path = tmp_path / f'{year}.utf8.csv'
    return ita_summary.harmonize_file(raw_file, year, source_file(year, name), utf8_path)


def harmonized(tmp_path, year, data, name=None):
    '''Write data as year's raw file under tmp_path and collect its harmonized rows.'''
    return harmonize_raw(tmp_path, year, data, name).collect()


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
        'source_file': source_file(year),
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


def test_an_undefined_naics_vintage_becomes_null_and_its_row_is_kept(tmp_path):
    # The 2024 and 2025 files carry vintages 0 and 2025 beside real six-digit codes.
    records = [
        record(2024, id='1', naics_code='485410', naics_year='0'),
        record(2024, id='2', naics_year='2025'),
        record(2024, id='3', naics_year='2017'),
    ]

    frame = harmonized(tmp_path, 2024, year_file(2024, records))

    assert frame.select(
        'id', 'naics_code', 'naics_year', 'naics_year_from_dictionary'
    ).rows() == [
        (1, '485410', None, False),
        (2, '332312', None, False),
        (3, '332312', 2017, False),
    ]


def test_a_naics_code_without_a_known_vintage_is_flagged(tmp_path):
    records = [
        record(2024, id='1', naics_year='0'),
        record(2024, id='2', naics_year='2025'),
        record(2024, id='3', naics_year=''),
        record(2024, id='4', naics_year='2017'),
        record(2024, id='5', naics_code='', naics_year=''),
    ]
    rows = pl.concat([
        harmonized(tmp_path, 2024, year_file(2024, records)),
        harmonized(tmp_path, 2022, year_file(2022)),
    ])

    flags = ita_summary.add_flags(rows.lazy()).select(
        'id', 'naics_year', 'flag_naics_year_unknown'
    ).collect()

    assert flags.rows() == [
        (1, None, True),
        (2, None, True),
        (3, None, True),       # a code delivered without its vintage
        (4, 2017, False),
        (5, None, False),      # no code, so no vintage to know
        (20220, 2012, False),  # before 2023 the vintage comes from the dictionary
    ]
    assert flags.schema['flag_naics_year_unknown'] == pl.Boolean


def not_a_whole_number(source, column):
    '''The harmonize_file failure for one row whose column is not a whole number.'''
    return rf'^{re.escape(source)}: 1 rows whose {column} is not a whole number$'


def test_a_fraction_that_is_not_zero_fails(tmp_path):
    data = year_file(2019, [record(2019, annual_average_employees='23.50')])

    with pytest.raises(
        ValueError, match=not_a_whole_number(source_file(2019), 'annual_average_employees'),
    ):
        harmonize_raw(tmp_path, 2019, data)


@pytest.mark.parametrize(
    'column',
    [
        'id', 'establishment_id', 'establishment_type', 'size', 'annual_average_employees',
        'total_hours_worked', 'year_filing_for', 'naics_year',
    ],
)
def test_a_value_that_is_not_a_whole_number_fails_naming_the_file_and_column(
    tmp_path, column,
):
    data = year_file(2024, [record(2024, **{column: '12.5'})])

    with pytest.raises(ValueError, match=not_a_whole_number(source_file(2024), column)):
        harmonize_raw(tmp_path, 2024, data)


def test_each_column_that_is_not_a_whole_number_is_named_with_its_row_count(tmp_path):
    records = [record(2024, id='1.5', size='2.5'), record(2024, id='2', size='3.5')]

    with pytest.raises(ValueError) as failure:
        harmonize_raw(tmp_path, 2024, year_file(2024, records))

    assert str(failure.value) == (
        f'{source_file(2024)}: 1 rows whose id is not a whole number;'
        ' 2 rows whose size is not a whole number'
    )


def test_scientific_notation_hours_are_read_as_the_whole_number_they_spell(tmp_path):
    # A spreadsheet wrote four real 2024 and 2025 hours this way (D11).
    records = [
        record(2024, id='1', annual_average_employees='133', total_hours_worked='8.62847E+11'),
    ]

    rows = harmonize_raw(tmp_path, 2024, year_file(2024, records))
    flagged = ita_summary.add_flags(rows).collect()

    assert flagged.select('id', 'total_hours_worked', 'flag_hours_per_employee').rows() == [
        (1, 862_847_000_000, True),
    ]


@pytest.mark.parametrize(
    ('written', 'hours'),
    [
        ('1.5E+3', 1_500),
        ('1.5e+3', 1_500),
        ('1.5E3', 1_500),
        ('150E-1', 15),       # trailing zeros absorb a negative exponent
        ('1.50E+1', 15),
        ('0.0E-5', 0),
        ('-1.5E+3', -1_500),  # signed, as a plain number may be
        # The largest Int64, which a float would round up to 2**63.
        ('9.223372036854775807E+18', 9_223_372_036_854_775_807),
        # More digits than a float holds: expanded exactly, not rejected.
        ('1.23456789012345678E+17', 123_456_789_012_345_678),
    ],
)
def test_scientific_notation_hours_are_expanded_exactly(tmp_path, written, hours):
    data = year_file(2024, [record(2024, total_hours_worked=written)])

    frame = harmonized(tmp_path, 2024, data)

    assert frame['total_hours_worked'].to_list() == [hours]


@pytest.mark.parametrize(
    'written',
    [
        '1.5E+0',                    # spells 1.5
        '15E-1',                     # spells 1.5
        '12.5',
        'abc',
        '1E+30',                     # too large for Int64
        '9.223372036854775808E+18',  # 2**63, one past the largest Int64
        '1E+99999999999999999999',   # an exponent too large for Int64
        ' 1.5E+3',                   # padded, as a plain number may not be either
        '1.5E+3 ',
        '１.5E+3',                   # a full-width digit, which Rust's \d would match
    ],
)
def test_hours_that_spell_no_whole_number_an_int64_holds_fail(tmp_path, written):
    data = year_file(2024, [record(2024, total_hours_worked=written)])

    with pytest.raises(
        ValueError, match=not_a_whole_number(source_file(2024), 'total_hours_worked'),
    ):
        harmonize_raw(tmp_path, 2024, data)


@pytest.mark.parametrize(
    'column',
    [
        'id', 'establishment_id', 'size', 'annual_average_employees', 'year_filing_for',
        'naics_year',
    ],
)
def test_scientific_notation_in_another_integer_column_fails(tmp_path, column):
    # establishment_type is not listed: E-notation there is text, which becomes null.
    data = year_file(2024, [record(2024, **{column: '1E+2'})])

    with pytest.raises(ValueError, match=not_a_whole_number(source_file(2024), column)):
        harmonize_raw(tmp_path, 2024, data)


def test_a_text_establishment_type_becomes_null_and_its_row_is_kept(tmp_path):
    # One 2019 row carries an industry title where the establishment type code belongs.
    records = [
        record(2019, id='1', establishment_type='Executive and Legislative Offices'),
        record(2019, id='2', establishment_type='2.00'),
    ]

    frame = harmonized(tmp_path, 2019, year_file(2019, records))

    assert frame.select('id', 'establishment_type').rows() == [(1, None), (2, 2)]


def test_a_numeric_establishment_type_with_a_fraction_fails(tmp_path):
    data = year_file(2019, [record(2019, establishment_type='1.5')])

    with pytest.raises(
        ValueError, match=not_a_whole_number(source_file(2019), 'establishment_type'),
    ):
        harmonize_raw(tmp_path, 2019, data)


@pytest.mark.parametrize(
    ('fields', 'message'),
    [
        ({'year_filing_for': '2023'}, 'filed for a year other than 2024'),
        ({'naics_code': '33231'}, 'NAICS code that is not six digits'),
        ({'size': '4'}, 'size code the dictionary does not define'),
    ],
    ids=['other-year', 'naics-code', 'size-code'],
)
def test_rows_no_rule_covers_fail_the_build(tmp_path, fields, message):
    with pytest.raises(ValueError, match=message):
        harmonized(tmp_path, 2024, year_file(2024, [record(2024, **fields)]))


def test_a_naics_code_of_six_full_width_digits_is_not_six_digits(tmp_path):
    # Rust's \d matches any Unicode digit; a NAICS code is six ASCII digits.
    data = year_file(2024, [record(2024, naics_code='３３２３１２')])

    with pytest.raises(ValueError) as failure:
        harmonize_raw(tmp_path, 2024, data)

    assert str(failure.value) == (
        f'{source_file(2024)}: 1 rows with a NAICS code that is not six digits'
    )


def test_a_naics_vintage_no_rule_covers_is_nulled_and_flagged_not_failed(tmp_path):
    rows = harmonized(tmp_path, 2024, year_file(2024, [record(2024, naics_year='2007')]))

    flagged = ita_summary.add_flags(rows.lazy()).collect()

    assert flagged.select(
        'naics_code', 'naics_year', 'naics_year_from_dictionary', 'flag_naics_year_unknown'
    ).rows() == [('332312', None, False, True)]


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
    'flag_naics_year_unknown': pl.Boolean, 'source_file': pl.String,
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


def test_the_stacked_table_holds_expanded_hours_and_unknown_vintages(data_directory):
    write_release(data_directory, 2022)
    records = [
        record(2024, id='1', naics_code='485410', naics_year='0'),
        record(2024, id='2', annual_average_employees='133', total_hours_worked='8.62847E+11'),
    ]
    write_release(data_directory, 2024, year_file(2024, records))

    table = pl.read_parquet(ita_summary.build_summary_table(data_directory))

    assert table.select(
        'year_filing_for', 'id', 'naics_year', 'flag_naics_year_unknown',
        'total_hours_worked', 'flag_hours_per_employee',
    ).rows() == [
        (2022, 20220, 2012, False, 200_000, False),
        (2024, 1, None, True, 200_000, False),
        (2024, 2, 2022, False, 862_847_000_000, True),
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

    with pytest.raises(
        ValueError,
        match=not_a_whole_number(source_file(2025, NEXT_2025), 'annual_average_employees'),
    ):
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
