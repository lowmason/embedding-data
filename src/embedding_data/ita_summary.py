'''Stack the OSHA ITA Form 300A summary files into one establishment-year table (spec R2.3).

Each year's raw file (a zip holding one CSV, or the current year's plain CSV) is transcoded
to UTF-8, its headers are lowercased (2025 writes ID and establishment_ID), and the columns
spec R2.4 retains are cast: codes and text stay strings, counts become Int64. The 2019 file
writes every number with a zero fraction (452990.00), which is accepted. Four 2024 and 2025
rows write total_hours_worked in scientific notation (8.62847E+11), as a spreadsheet writes
a long number; in that column alone, such a value is read as the whole number it spells.
It is expanded on its digit string, not through a float, whose 53-bit significand would
silently round a longer value (1.23456789012345678E+17). Any other value that is not a
whole number, or that Int64 cannot hold, fails the build with the file and column named.
The one exception is establishment_type, where a value with no digit at all (one 2019 row
holds Executive and Legislative Offices) becomes null; any value holding a digit must
still be a whole number. Two dictionary changes are harmonized:

- size: code 2 (20-249 employees) was split into 21 (20-99) and 22 (100-249) with the 2023
  data, but the 2023 and later files still carry 2 for some establishments. size keeps the
  native code; size_class merges 21 and 22 into 2, one scheme in every year. Code 2 is
  never split, because size is peak employment, not the annual average.
- naics_year: delivered from the 2023 data on. Earlier files lack it, and the Summary Data
  Dictionary says data through 2022 use 2012 NAICS, so those rows take 2012 with
  naics_year_from_dictionary set. A delivered vintage other than 2012, 2017 or 2022 (the
  2024 file carries 0, the 2025 file 0 and 2025) becomes null and its code is kept;
  flag_naics_year_unknown marks every code left without a vintage.

establishment_id is present in every year's file and is kept as delivered; whether it
persists across years is spec V2's question. A file these rules do not cover fails the
build: a zip without exactly one CSV, a missing column, a row filed for another year, a
NAICS code that is not six digits, or an undocumented size code. Records are flagged,
never dropped (R2.9). Injury and illness counts, submission timestamps, and change reasons
stay in the raw files. Each row's source_file cites a manifest entry whose SHA-256 the
build has verified against the raw file; a file that no longer matches fails the build.
'''

import tempfile
import zipfile
from collections.abc import Iterable
from contextlib import ExitStack
from dataclasses import asdict, dataclass
from pathlib import Path

import polars as pl

from embedding_data import manifest, paths
from embedding_data.ita_catalog import through_date
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
# Scientific notation as a spreadsheet writes a long number (8.62847E+11), signed like a
# plain number and, like one, not padded. [0-9], because Rust's \d matches any Unicode digit.
SCIENTIFIC = (
    r'^(?<sign>[-+]?)(?<whole>[0-9]+)(?:\.(?<fraction>[0-9]+))?[eE](?<exponent>[-+]?[0-9]+)$'
)
# Digits in the largest Int64; a whole number with more cannot be one.
INT64_DIGITS = len(str(2**63 - 1))
SIZE_CLASS = {1: 1, 2: 2, 21: 2, 22: 2, 3: 3}
# Plausible annual hours worked per average employee, inclusive: about 10 to 77 hours a week.
HOURS_PER_EMPLOYEE = (500, 4_000)
TABLE_NAME = 'ita_300a_summary.parquet'
COLUMNS = [
    'year_filing_for', 'id', 'establishment_id', 'establishment_name', 'company_name', 'ein',
    'street_address', 'city', 'state', 'zip_code', 'naics_code', 'naics_year',
    'naics_year_from_dictionary', 'industry_description', 'establishment_type', 'size',
    'size_class', 'annual_average_employees', 'total_hours_worked', 'flag_employment',
    'flag_hours_per_employee', 'flag_below_filing_size', 'flag_naics_year_unknown',
    'source_file',
]


@dataclass(frozen=True)
class PublishedCount:
    '''An establishment count OSHA itself published for one filing year (spec V10).'''
    year_filing_for: int
    published: int
    qualifier: str
    as_of: str | None
    source: str


PUBLISHED_COUNTS = (
    PublishedCount(
        2023, 385_488, 'exactly', '2024-05-31',
        'OSHA 2023 Work-Related Injury and Illness Summary',
    ),
    PublishedCount(
        2024, 390_000, 'over', None, 'OSHA 2024 Work-Related Injury and Illness Summary',
    ),
)
PUBLISHED_SCHEMA = {
    'year_filing_for': pl.Int64, 'published': pl.Int64, 'qualifier': pl.String,
    'as_of': pl.String, 'source': pl.String,
}


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


def whole_number(value: pl.Expr, *, strict: bool = True) -> pl.Expr:
    '''value as Int64; a zero fraction (2019.00) is dropped and any other fraction fails.

    With strict False, a value that does not cast becomes null instead of failing.
    '''
    return value.str.replace(r'\.0+$', '').cast(pl.Int64, strict=strict)


def expand_scientific(value: pl.Expr) -> pl.Expr:
    '''value, with scientific notation that spells a whole number written out in digits.

    The digits are moved, never converted through a float, so the result is exact:
    8.62847E+11 becomes 862847000000. Any other value, including a fraction (1.5E+0) or a
    number with more digits than an Int64 holds (1E+30), is returned unchanged, so the
    cast it feeds rejects it.
    '''
    parts = value.str.extract_groups(SCIENTIFIC).struct
    fraction = parts.field('fraction').fill_null('')
    digits = parts.field('whole') + fraction
    trimmed = digits.str.strip_chars_end('0')
    significant = trimmed.str.strip_chars_start('0')
    # The value is significant * 10**zeros. An exponent beyond Int64 is null, leaving the
    # value unchanged (none spells a nonzero Int64); widened to Int128, the sum cannot
    # overflow.
    zeros = (
        parts.field('exponent').cast(pl.Int64, strict=False).cast(pl.Int128)
        - fraction.str.len_chars()
        + (digits.str.len_chars() - trimmed.str.len_chars())
    )
    width = significant.str.len_chars() + zeros
    fits = (zeros >= 0) & (width <= INT64_DIGITS)
    # Polars evaluates every branch on every row, so the width is masked where it does not
    # fit, or 1E+999999999 would be padded to a billion digits before being discarded.
    written_out = parts.field('sign') + significant.str.pad_end(pl.when(fits).then(width), '0')
    return (
        pl.when(significant == '').then(pl.lit('0'))
        .when(fits).then(written_out)
        .otherwise(value)
    )


def integer_value(column: str) -> pl.Expr:
    '''The raw string an integer column is cast from; establishment_type with no digit is null.

    An establishment_type with no digit at all is text, masked out before the cast rather
    than skipped by a branch around it, so the strict cast never sees it, whichever rows
    Polars evaluates a branch on. Any value holding a digit reaches the cast; the mask uses
    Rust's \\d, which matches any Unicode digit, so a full-width 1 fails there rather than
    being nulled. total_hours_worked in scientific notation is written out in digits
    (expand_scientific); no other column reads that notation as a number.
    '''
    value = pl.col(column)
    if column == 'establishment_type':
        return pl.when(value.str.contains(r'\d')).then(value)
    if column == 'total_hours_worked':
        return expand_scientific(value)
    return value


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
        delivered = whole_number(pl.col('naics_year'))
        naics_year = pl.when(delivered.is_in(NAICS_YEARS)).then(delivered)
        from_dictionary = pl.lit(False)
    else:
        naics_year = pl.when(naics_code.is_not_null()).then(pl.lit(DICTIONARY_NAICS_YEAR))
        from_dictionary = naics_code.is_not_null()
    size_class = whole_number(pl.col('size')).replace_strict(
        SIZE_CLASS, default=None, return_dtype=pl.Int64
    )
    return lf.select(
        *(whole_number(integer_value(column)).alias(column) for column in INTEGER_COLUMNS),
        *TEXT_COLUMNS,
        naics_code.alias('naics_code'),
        naics_year.cast(pl.Int64).alias('naics_year'),
        from_dictionary.alias('naics_year_from_dictionary'),
        size_class.alias('size_class'),
        pl.lit(source_file).alias('source_file'),
    )


def check_integers(raw: pl.LazyFrame, source_file: str) -> None:
    '''Fail on raw values an integer column cannot hold, naming each column and its count.'''
    names = raw.collect_schema().names()
    columns = INTEGER_COLUMNS + (['naics_year'] if 'naics_year' in names else [])
    counts = raw.select(
        (
            integer_value(column).is_not_null()
            & whole_number(integer_value(column), strict=False).is_null()
        ).sum().alias(column)
        for column in columns
    ).collect().row(0, named=True)
    problems = [
        f'{count:,} rows whose {column} is not a whole number'
        for column, count in counts.items() if count
    ]
    if problems:
        raise ValueError(f'{source_file}: ' + '; '.join(problems))


def check_summary(lf: pl.LazyFrame, year: int, source_file: str) -> None:
    '''Fail on rows no harmonization rule covers, naming each kind and its count.'''
    labels = {
        'other_year': f'filed for a year other than {year}',
        'naics_code': 'with a NAICS code that is not six digits',
        'size': 'with a size code the dictionary does not define',
    }
    size = pl.col('size')
    counts = lf.select(
        other_year=pl.col('year_filing_for').ne_missing(year).sum(),
        # [0-9], not \d, which in Rust's regex matches any Unicode digit.
        naics_code=pl.col('naics_code').str.contains(r'^[0-9]{6}$').not_().sum(),
        size=(size.is_not_null() & size.is_in(list(SIZE_CLASS)).not_()).sum(),
    ).collect().row(0, named=True)
    problems = [f'{count:,} rows {labels[kind]}' for kind, count in counts.items() if count]
    if problems:
        raise ValueError(f'{source_file}: ' + '; '.join(problems))


def harmonize_file(
    raw_file: Path, year: int, source_file: str, utf8_path: Path,
) -> pl.LazyFrame:
    '''Transcode one raw summary file to utf8_path; return its checked, harmonized rows.

    The frame reads utf8_path lazily, so the caller keeps that file until the frame is
    collected or sunk. Every integer column is checked on its raw strings before
    check_summary reads the cast ones, so a value that is not a whole number fails here,
    naming the file, rather than when the frame is collected or sunk.
    '''
    transcode(raw_file, utf8_path)
    raw = pl.scan_csv(utf8_path, infer_schema=False).rename(str.lower)
    lf = harmonize(raw, year, source_file)
    check_integers(raw, source_file)
    check_summary(lf, year, source_file)
    return lf


def add_flags(lf: pl.LazyFrame) -> pl.LazyFrame:
    '''Flag, never drop, the implausible records spec R2.9 names, and codes of no vintage.

    flag_employment: annual average employment is missing, zero, or negative.
    flag_hours_per_employee: hours per average employee fall outside HOURS_PER_EMPLOYEE, or
        hours are missing; null where employment is flagged, since no ratio exists.
    flag_below_filing_size: fewer than 20 employees at peak (size_class 1), outside the
        filing rule in every industry. Whether a larger establishment's industry places it
        outside the rule needs NAICS vintage concordances and is not evaluated here.
    flag_naics_year_unknown: a NAICS code with no vintage, because the file delivered none
        or one other than 2012, 2017 or 2022; never null. A provenance flag for the
        vintage, not one of the R2.9 flags.
    '''
    employees, hours = pl.col('annual_average_employees'), pl.col('total_hours_worked')
    no_employment = employees.is_null() | (employees <= 0)
    implausible_hours = hours.is_null() | (hours / employees).is_between(
        *HOURS_PER_EMPLOYEE
    ).not_()
    no_vintage = pl.col('naics_code').is_not_null() & pl.col('naics_year').is_null()
    return lf.with_columns(
        flag_employment=no_employment,
        flag_hours_per_employee=pl.when(no_employment).then(None).otherwise(implausible_hours),
        flag_below_filing_size=pl.col('size_class') == 1,
        flag_naics_year_unknown=no_vintage,
    )


def summary_dir(data_dir: Path) -> Path:
    return paths.raw_dir(data_dir, 'osha') / 'summary'


def release_names(year_dir: Path) -> set[str]:
    '''The names of the releases in a year's directory; none if it does not exist.

    Hidden files (a Finder .DS_Store) and interrupted .part downloads are not releases.
    '''
    if not year_dir.is_dir():
        return set()
    return {
        path.name for path in year_dir.iterdir()
        if path.is_file() and not path.name.startswith('.') and not path.name.endswith('.part')
    }


def latest_release_name(names: Iterable[str]) -> str:
    '''The only name, or the one carrying the latest through-date.

    Raises ValueError when there is no name, or when the names cannot be ordered by date:
    one has no through-date beside another, or two carry the same through-date.
    '''
    names = sorted(set(names))
    if len(names) == 1:
        return names[0]
    dates = {through_date(name): name for name in names}
    if not names or None in dates or len(dates) < len(names):
        raise ValueError(
            f'cannot choose one of {names}; each file in a year needs a distinct '
            'through-date in its name'
        )
    return dates[max(dates)]


def latest_release(year_dir: Path) -> Path:
    '''A year's only raw file, or the one whose name carries the latest through-date.'''
    try:
        return year_dir / latest_release_name(release_names(year_dir))
    except ValueError as error:
        raise ValueError(f'{year_dir}: {error}') from None


def summary_files(data_dir: Path) -> dict[int, Path]:
    '''The raw file each year's rows come from (raw/osha/summary/<year>/), by year.'''
    root = summary_dir(data_dir)
    year_dirs = (
        sorted(path for path in root.iterdir() if path.is_dir() and path.name.isdigit())
        if root.is_dir() else []
    )
    if not year_dirs:
        raise ValueError(f'{root}: no summary files to stack')
    return {int(year_dir.name): latest_release(year_dir) for year_dir in year_dirs}


def build_summary_table(data_dir: Path) -> Path:
    '''Rebuild the stacked table from each year's latest recorded raw file; return its path.

    Unlike the case-detail Parquet, the table is rebuilt on every call, because a new
    release replaces its year's rows. Each input must be in the manifest with the SHA-256
    it has now, and its manifest path becomes source_file. The table is written to a .part
    file, renamed on success.
    '''
    manifest_path = paths.manifest_path(data_dir)
    derived = paths.derived_dir(data_dir, 'osha')
    derived.mkdir(parents=True, exist_ok=True)
    table = derived / TABLE_NAME
    partial = table.with_name(table.name + '.part')
    with tempfile.TemporaryDirectory(dir=derived) as work:
        frames = []
        for year, raw_file in summary_files(data_dir).items():
            entry = manifest.entry_for(manifest_path, raw_file)
            sha256 = manifest.sha256_file(raw_file)
            if sha256 != entry.sha256:
                raise ValueError(
                    f'{entry.path}: SHA-256 {sha256[:12]}... differs from the '
                    f'{entry.sha256[:12]}... recorded in {manifest_path}; the raw file has '
                    'changed since it was downloaded'
                )
            utf8_path = Path(work) / f'{year}.csv'
            frames.append(harmonize_file(raw_file, year, entry.path, utf8_path))
        try:
            (
                add_flags(pl.concat(frames))
                .select(COLUMNS)
                .sort('year_filing_for', 'id', maintain_order=True)
                .sink_parquet(partial)
            )
            partial.replace(table)
        finally:
            partial.unlink(missing_ok=True)
    return table


def totals_report(table: Path) -> pl.DataFrame:
    '''Rows and source file per year beside OSHA's published counts; gaps kept, not tuned.'''
    published = pl.LazyFrame(
        [asdict(count) for count in PUBLISHED_COUNTS], schema=PUBLISHED_SCHEMA
    )
    return (
        pl.scan_parquet(table)
        .group_by('year_filing_for')
        .agg(rows=pl.len().cast(pl.Int64), source_file=pl.col('source_file').first())
        .join(published, on='year_filing_for', how='left')
        .with_columns(gap=pl.col('rows') - pl.col('published'))
        .sort('year_filing_for')
        .collect()
    )


def report_lines(report: pl.DataFrame) -> list[str]:
    '''One line per year: rows, source file, and the published count and gap where known.'''
    lines = []
    for row in report.iter_rows(named=True):
        year, rows, source_file = row['year_filing_for'], row['rows'], row['source_file']
        line = f'{year}: {rows:,} rows from {source_file}'
        if row['published'] is None:
            line += '; no published count located'
        else:
            qualifier, published, source, gap, as_of_date = (
                row['qualifier'], row['published'], row['source'], row['gap'], row['as_of']
            )
            as_of = f' as of {as_of_date}' if as_of_date else ''
            line += (
                f'; OSHA published {qualifier} {published:,}{as_of} ({source}); gap {gap:+,}'
            )
        lines.append(line)
    return lines
