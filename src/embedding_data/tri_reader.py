'''Read an EPA TRI basic data file as a typed lazy frame, by its recorded header layout.

`read_year` checks the file against its `HeaderLayout`, then returns the mapped columns
under the names of `READ_SCHEMA`. Every column is a string, a blank cell is `''` and never
null, and `year` is the file's year. The three checks run before the frame returns, so a
bad file fails in `read_year` and not at a later `collect`:

- The first row equals `layout.header` exactly.
- Every record has one cell for each header cell, and the `csv` module and Polars count the
  same number of records. A record with another number of cells is a row count difference,
  because Polars pads a short record and does not count it apart.
- Each reporting-year cell, stripped, equals the year of the file.

A file with a UTF-8 byte order mark, or a line that is not valid UTF-8, goes through
`osha_encoding.decode_line` into `scratch / '<year>.utf8.csv'` first. The returned frame
then reads that copy, so the caller keeps `scratch` until the frame is collected. The raw
file is never written or moved.
'''

import csv
from pathlib import Path

import polars as pl

from embedding_data.osha_encoding import decode_line
from embedding_data.tri_layout import HeaderLayout

BYTE_ORDER_MARK = b'\xef\xbb\xbf'
NAICS_FIELDS = ('naics_2', 'naics_3', 'naics_4', 'naics_5', 'naics_6')
READ_SCHEMA = {
    'year': pl.Int64,
    'reporting_year': pl.String,
    'trifd': pl.String,
    'form_type': pl.String,
    'state': pl.String,
    'federal': pl.String,
    'primary_naics': pl.String,
    'naics_2': pl.String,
    'naics_3': pl.String,
    'naics_4': pl.String,
    'naics_5': pl.String,
    'naics_6': pl.String,
    'parent_name': pl.String,
    'parent_dnb': pl.String,
    'standardized_parent': pl.String,
    'standardized_foreign_parent': pl.String,
}


def needs_transcoding(file: Path) -> bool:
    '''Whether the file starts with a UTF-8 byte order mark or holds a line that is not UTF-8.'''
    with Path(file).open('rb') as handle:
        for number, line in enumerate(handle):
            if number == 0 and line.startswith(BYTE_ORDER_MARK):
                return True
            try:
                line.decode('utf-8')
            except UnicodeDecodeError:
                return True
    return False


def _transcode(file: Path, destination: Path) -> None:
    '''Write the file to `destination` as UTF-8, line by line, without a byte order mark.'''
    destination.parent.mkdir(parents=True, exist_ok=True)
    with file.open('rb') as source, destination.open(
            'w', encoding='utf-8', newline='') as target:
        for number, line in enumerate(source):
            if number == 0:
                line = line.removeprefix(BYTE_ORDER_MARK)
            target.write(decode_line(line))


def _record_count(source: Path, layout: HeaderLayout) -> int:
    '''The number of records after the header, read with the `csv` module.'''
    with source.open(newline='', encoding='utf-8') as handle:
        reader = csv.reader(handle)
        if tuple(next(reader, ())) != layout.header:
            raise ValueError('changed header')
        count = 0
        for record in reader:
            if len(record) != len(layout.header):
                raise ValueError('row count differs')
            count += 1
    return count


def _selection(layout: HeaderLayout) -> list[pl.Expr]:
    '''The mapped cells under the names of `READ_SCHEMA`; an unmapped field reads as `''`.'''
    cells = dict(layout.columns)
    cells.update(zip(NAICS_FIELDS, layout.other_naics))
    expressions = []
    for name in READ_SCHEMA:
        if name == 'year':
            expressions.append(pl.lit(layout.year, dtype=pl.Int64).alias(name))
        elif cells.get(name) is None:
            expressions.append(pl.lit('', dtype=pl.String).alias(name))
        else:
            expressions.append(pl.col(cells[name]).alias(name))
    return expressions


def _check(scan: pl.LazyFrame, frame: pl.LazyFrame, records: int, year: int) -> None:
    '''Require the `csv` record count from a Polars count, then one reporting year.

    The count query reads no column, so a file with a stray quote gives a count that
    differs from the `csv` count, where a query on a column raises a Polars error.
    '''
    if scan.select(pl.len()).collect().item() != records:
        raise ValueError('row count differs')
    other_years = frame.filter(
        pl.col('reporting_year').str.strip_chars() != str(year)).select(pl.len()).collect()
    if other_years.item():
        raise ValueError('reporting year mismatch')


def _read(file: Path, layout: HeaderLayout, scratch: Path) -> tuple[pl.LazyFrame, bool]:
    file = Path(file)
    transcode = needs_transcoding(file)
    source = Path(scratch) / f'{layout.year}.utf8.csv' if transcode else file
    if transcode:
        _transcode(file, source)
    records = _record_count(source, layout)
    # Polars reads an empty cell as null unless `empty_string_is_null` is false.
    scan = pl.scan_csv(source, infer_schema=False, empty_string_is_null=False)
    frame = scan.select(_selection(layout))
    _check(scan, frame, records, layout.year)
    return frame, transcode


def read_year(file: Path, layout: HeaderLayout, scratch: Path) -> pl.LazyFrame:
    '''The rows of one year's file in `READ_SCHEMA`, after the header, count and year checks.'''
    return _read(file, layout, scratch)[0]


def read_window(files: dict[int, Path], layouts: dict[int, HeaderLayout],
                scratch: Path) -> tuple[pl.LazyFrame, list[int]]:
    '''The rows of all the years in window order, and the sorted years that were transcoded.'''
    frames = []
    transcoded = []
    for year in sorted(files):
        frame, converted = _read(files[year], layouts[year], scratch)
        frames.append(frame)
        if converted:
            transcoded.append(year)
    return pl.concat(frames), transcoded
