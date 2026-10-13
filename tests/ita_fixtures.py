'''Miniature Form 300A summary files in each format OSHA has published (2016-2025).

Headers, column order, quoting, BOM, member names and number formats copy the delivered
files; the values are invented. year_file(year) renders records as that year's file does.
'''

import io
import zipfile

OLD_COLUMNS = (
    'id', 'company_name', 'establishment_name', 'ein', 'street_address', 'city', 'state',
    'zip_code', 'naics_code', 'industry_description', 'annual_average_employees',
    'total_hours_worked', 'no_injuries_illnesses', 'total_deaths', 'total_dafw_cases',
    'total_djtr_cases', 'total_other_cases', 'total_dafw_days', 'total_djtr_days',
    'total_injuries', 'total_poisonings', 'total_respiratory_conditions',
    'total_skin_disorders', 'total_hearing_loss', 'total_other_illnesses', 'establishment_id',
    'establishment_type', 'size', 'year_filing_for', 'created_timestamp', 'change_reason',
)
NEW_COLUMNS = (
    'id', 'establishment_name', 'establishment_id', 'ein', 'company_name', 'street_address',
    'city', 'state', 'zip_code', 'naics_code', 'naics_year', 'industry_description',
    'establishment_type', 'size', 'annual_average_employees', 'total_hours_worked',
    'no_injuries_illnesses', 'total_deaths', 'total_dafw_cases', 'total_djtr_cases',
    'total_other_cases', 'total_dafw_days', 'total_djtr_days', 'total_injuries',
    'total_skin_disorders', 'total_respiratory_conditions', 'total_poisonings',
    'total_hearing_loss', 'total_other_illnesses',
)
COLUMNS_2023 = (*NEW_COLUMNS, 'created_timestamp', 'change_reason', 'year_filing_for')
COLUMNS_2024 = (*NEW_COLUMNS, 'change_reason', 'created_timestamp', 'year_filing_for')
COLUMNS_2025 = (
    'ID', 'establishment_name', 'establishment_ID', *NEW_COLUMNS[3:],
    'date_submitted', 'Change_reason', 'year_filing_for',
)

RELEASE_NAMES = {
    **{year: f'ITA Data CY {year}.zip' for year in range(2016, 2020)},
    2020: 'ITA-Data-CY-2020.zip',
    2021: 'ITA-data-cy2021.zip',
    2022: 'ITA-data-cy2022.zip',
    2023: 'ITA_300A_Summary_Data_2023_through_12-31-2024.zip',
    2024: 'ITA_300A_Summary_Data_2024_through_12-31-2025.zip',
    2025: 'ITA_300A_Summary_Data_2025_through_08-31-2026.csv',
}
MEMBER_NAMES = {
    **{year: f'ITA Data CY {year}.csv' for year in range(2016, 2021)},
    2021: 'ITA 2021 data.csv',
    2022: 'CY 2022.csv',
    2023: 'ITA 300A Summary Data 2023 through 12-31-2024_v2.csv',
    2024: 'ITA_300A_Summary_Data_2024_through_12-31-2025_v2.csv',
}


def record(year: int, **fields: str) -> dict[str, str]:
    '''One establishment-year, numbers formatted as that year's file writes them.'''
    def number(value: int) -> str:
        return f'{value}.00' if year == 2019 else str(value)

    values = {
        'id': number(year * 10),
        'establishment_id': number(year),
        'establishment_name': 'Acme Plant 7',
        'company_name': 'Acme Holdings, Inc.',
        'ein': '' if year <= 2018 else '012345678',
        'street_address': '1 Main St',
        'city': 'Springfield',
        'state': 'IL',
        'zip_code': '02134',
        'naics_code': number(332312),
        'naics_year': '2022',
        'industry_description': 'Fabricated structural metal',
        'establishment_type': '1',
        'size': number(2 if year <= 2022 else 22),
        'annual_average_employees': number(100),
        'total_hours_worked': number(200_000),
        'year_filing_for': number(year),
        'created_timestamp': '1/1/2024',
        'date_submitted': '2/16/2026',
        'change_reason': '',
    }
    values.update(fields)
    return values


def cell(value: str, quote_text: bool) -> str:
    '''One CSV field: quoted if it holds a comma or quote, or is text in a quoted file.'''
    is_number = value.replace('.', '', 1).isdigit()
    if ',' in value or '"' in value or (quote_text and value and not is_number):
        return '"' + value.replace('"', '""') + '"'
    return value


def csv_bytes(columns, records, *, quote_text=False, bom=False, zero='0') -> bytes:
    '''CRLF CSV of records in column order; columns a record lacks (injury counts) get zero.'''
    header = ','.join(f'"{column}"' if quote_text else column for column in columns)
    rows = [
        ','.join(cell(values.get(column.lower(), zero), quote_text) for column in columns)
        for values in records
    ]
    text = '\r\n'.join([header, *rows]) + '\r\n'
    return (b'\xef\xbb\xbf' if bom else b'') + text.encode('utf-8')


def zipped(member: str, data: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, data)
    return buffer.getvalue()


def year_file(year: int, records: list[dict[str, str]] | None = None) -> bytes:
    '''Records rendered as that year's raw file: zipped through 2024, a plain CSV in 2025.'''
    records = [record(year)] if records is None else records
    if year <= 2020:
        zero = '0.00' if year == 2019 else '0'
        data = csv_bytes(OLD_COLUMNS, records, quote_text=True, zero=zero)
    elif year <= 2022:
        data = csv_bytes(OLD_COLUMNS, records, bom=year == 2022)
    elif year <= 2024:
        data = csv_bytes(COLUMNS_2023 if year == 2023 else COLUMNS_2024, records)
    else:
        return csv_bytes(COLUMNS_2025, records)
    return zipped(MEMBER_NAMES[year], data)
