'''Stack the OSHA ITA Form 300A summary files into one establishment-year table (spec R2.3).

Each year's raw file (a zip holding one CSV, or the current year's plain CSV) is transcoded
to UTF-8, its headers are lowercased (2025 writes ID and establishment_ID), and the columns
spec R2.4 retains are cast: codes and text stay strings, counts become Int64. The 2019 file
writes every number with a zero fraction (452990.00), which is accepted; any other fraction
fails. Two dictionary changes are harmonized:

- size: code 2 (20-249 employees) was split into 21 (20-99) and 22 (100-249) with the 2023
  data, but the 2023 and later files still carry 2 for some establishments. size keeps the
  native code; size_class merges 21 and 22 into 2, one scheme in every year. Code 2 is
  never split, because size is peak employment, not the annual average.
- naics_year: delivered from the 2023 data on. Earlier files lack it, and the Summary Data
  Dictionary says data through 2022 use 2012 NAICS, so those rows take 2012 with
  naics_year_from_dictionary set.

establishment_id is present in every year's file and is kept as delivered; whether it
persists across years is spec V2's question. A file these rules do not cover fails the
build: a zip without exactly one CSV, a missing column, a row filed for another year, a
NAICS code that is not six digits, or an undocumented size code or NAICS vintage. Records
are flagged, never dropped (R2.9). Injury and illness counts, submission timestamps, and
change reasons stay in the raw files.
'''

import zipfile
from contextlib import ExitStack
from pathlib import Path

import polars as pl

from embedding_data.osha_encoding import decode_line

INTEGER_COLUMNS = [
    'id', 'establishment_id', 'establishment_type', 'size', 'annual_average_employees',
    'total_hours_worked', 'year_filing_for',
]
TEXT_COLUMNS = [
    'establishment_name', 'company_name', 'ein', 'street_address', 'city', 'state',
    'zip_code', 'industry_description',
]
REQUIRED_COLUMNS = [*INTEGER_COLUMNS, *TEXT_COLUMNS, 'naics_code']
NAICS_YEAR_FROM = 2023
DICTIONARY_NAICS_YEAR = 2012
NAICS_YEARS = [2012, 2017, 2022]
SIZE_CLASS = {1: 1, 2: 2, 21: 2, 22: 2, 3: 3}
# Plausible annual hours worked per average employee, inclusive: about 10 to 77 hours a week.
HOURS_PER_EMPLOYEE = (500, 4_000)


def transcode(raw_file: Path, utf8_path: Path) -> None:
    '''Write raw_file's CSV, or the one CSV inside a zip, to utf8_path as UTF-8.'''
    with ExitStack() as stack:
        if raw_file.suffix.lower() == '.zip':
            archive = stack.enter_context(zipfile.ZipFile(raw_file))
            members = [name for name in archive.namelist() if name.lower().endswith('.csv')]
            if len(members) != 1:
                raise ValueError(f'{raw_file.name}: expected one CSV member, found {members}')
            source = stack.enter_context(archive.open(members[0]))
        else:
            source = stack.enter_context(raw_file.open('rb'))
        target = stack.enter_context(utf8_path.open('w', encoding='utf-8', newline=''))
        target.writelines(decode_line(line) for line in source)


def whole_number(column: str) -> pl.Expr:
    '''An Int64 column; a zero fraction (2019.00) is dropped and any other fraction fails.'''
    return pl.col(column).str.replace(r'\.0+$', '').cast(pl.Int64)


def harmonize(lf: pl.LazyFrame, year: int, source_file: str) -> pl.LazyFrame:
    '''The R2.4 columns of one year's file, typed, with size and NAICS vintage harmonized.'''
    lf = lf.rename(str.lower)
    names = lf.collect_schema().names()
    required = REQUIRED_COLUMNS + (['naics_year'] if year >= NAICS_YEAR_FROM else [])
    missing = [column for column in required if column not in names]
    if missing:
        raise ValueError(f'{source_file}: missing columns {missing}')
    naics_code = pl.col('naics_code').str.replace(r'\.0+$', '')
    if 'naics_year' in names:
        naics_year = whole_number('naics_year')
        from_dictionary = pl.lit(False)
    else:
        naics_year = pl.when(naics_code.is_not_null()).then(pl.lit(DICTIONARY_NAICS_YEAR))
        from_dictionary = naics_code.is_not_null()
    size_class = whole_number('size').replace_strict(
        SIZE_CLASS, default=None, return_dtype=pl.Int64
    )
    return lf.select(
        *(whole_number(column) for column in INTEGER_COLUMNS),
        *TEXT_COLUMNS,
        naics_code.alias('naics_code'),
        naics_year.cast(pl.Int64).alias('naics_year'),
        from_dictionary.alias('naics_year_from_dictionary'),
        size_class.alias('size_class'),
        pl.lit(source_file).alias('source_file'),
    )


def check_summary(lf: pl.LazyFrame, year: int, source_file: str) -> None:
    '''Fail on rows no harmonization rule covers, naming each kind and its count.'''
    labels = {
        'other_year': f'filed for a year other than {year}',
        'naics_code': 'with a NAICS code that is not six digits',
        'size': 'with a size code the dictionary does not define',
        'naics_year': 'with a NAICS vintage other than 2012, 2017 or 2022',
    }
    size, naics_year = pl.col('size'), pl.col('naics_year')
    counts = lf.select(
        other_year=pl.col('year_filing_for').ne_missing(year).sum(),
        naics_code=pl.col('naics_code').str.contains(r'^\d{6}$').not_().sum(),
        size=(size.is_not_null() & size.is_in(list(SIZE_CLASS)).not_()).sum(),
        naics_year=(naics_year.is_not_null() & naics_year.is_in(NAICS_YEARS).not_()).sum(),
    ).collect().row(0, named=True)
    problems = [f'{count:,} rows {labels[kind]}' for kind, count in counts.items() if count]
    if problems:
        raise ValueError(f'{source_file}: ' + '; '.join(problems))


def harmonize_file(
    raw_file: Path, year: int, source_file: str, utf8_path: Path,
) -> pl.LazyFrame:
    '''Transcode one raw summary file to utf8_path; return its checked, harmonized rows.

    The frame reads utf8_path lazily, so the caller keeps that file until the frame is
    collected or sunk. check_summary reads only the columns it checks, so a bad value in
    another integer column fails when the frame is collected or sunk.
    '''
    transcode(raw_file, utf8_path)
    lf = harmonize(pl.scan_csv(utf8_path, infer_schema=False), year, source_file)
    check_summary(lf, year, source_file)
    return lf


def add_flags(lf: pl.LazyFrame) -> pl.LazyFrame:
    '''Flag, never drop, the implausible records spec R2.9 names.

    flag_employment: annual average employment is missing, zero, or negative.
    flag_hours_per_employee: hours per average employee fall outside HOURS_PER_EMPLOYEE, or
        hours are missing; null where employment is flagged, since no ratio exists.
    flag_below_filing_size: fewer than 20 employees at peak (size_class 1), outside the
        filing rule in every industry. Whether a larger establishment's industry places it
        outside the rule needs NAICS vintage concordances and is not evaluated here.
    '''
    employees, hours = pl.col('annual_average_employees'), pl.col('total_hours_worked')
    no_employment = employees.is_null() | (employees <= 0)
    implausible_hours = hours.is_null() | (hours / employees).is_between(
        *HOURS_PER_EMPLOYEE
    ).not_()
    return lf.with_columns(
        flag_employment=no_employment,
        flag_hours_per_employee=pl.when(no_employment).then(None).otherwise(implausible_hours),
        flag_below_filing_size=pl.col('size_class') == 1,
    )
