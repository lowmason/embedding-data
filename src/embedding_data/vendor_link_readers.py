'''Streaming readers for the Stage 14 subaward ZIP files and the SAM.gov extract.

A subaward ZIP holds one or more CSV members. Each streams from the archive through a UTF-8
text wrapper into `csv.reader`, so a quoted value may hold commas, quotes and line breaks.
The reader checks the exact header and the width of every record, and writes only the
mapped columns and a row digest to Parquet parts in scratch, never a full copy.

The extract has one member, read line by line with no quote rules. The reader checks the BOF
and EOF framing lines and keeps only the registered positions of each data line of the
layout's field count, whose last field must be the record end. A data line with another
field count is skipped, not refused, because a `|` inside an unquoted text field splits it
(owner decision, 2026-11-19). `unreadable_extract_lines` lists those lines with their UEI
and field count only, so that the build counts them. The extract readers write nothing. No
name, address or other D&B Open Data field enters a frame or a file. Each failed check
raises a `ValueError` with a fixed message.
'''

import codecs
import csv
import hashlib
import io
import json
import re
import zipfile
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from embedding_data.vendor_link_layouts import (
    EXTRACT_FIELDS,
    SUBAWARD_FIELDS,
    ExtractLayout,
    SubawardLayout,
)

SUBAWARD_SCHEMA = {'file_year': pl.Int64, 'member': pl.String, 'record': pl.UInt64,
                   'prime_uei': pl.String, 'prime_parent_uei': pl.String, 'sub_uei': pl.String,
                   'sub_parent_uei': pl.String, 'action_date': pl.String, 'amount': pl.String,
                   'subaward_type': pl.String, 'report_id': pl.String,
                   'subaward_naics': pl.String, 'prime_naics': pl.String,
                   'row_digest': pl.String}
EXTRACT_SCHEMA = {'line': pl.UInt64, 'uei': pl.String, 'registration_status': pl.String,
                  'last_update_date': pl.String, 'primary_naics': pl.String,
                  'naics_code_string': pl.String, 'evs_source': pl.String}
UNREADABLE_SCHEMA = {'line': pl.Int64, 'uei': pl.String, 'fields': pl.Int64}
BATCH_ROWS = 200_000
FIELD_SIZE_LIMIT = 1 << 30


@dataclass(frozen=True)
class SubawardRead:
    '''The subaward rows of the window and, for each file year, its members in read order,
    its data-record count and whether any of its members started with a BOM.'''
    rows: pl.LazyFrame
    members: dict[int, tuple[str, ...]]
    records: dict[int, int]
    bom: dict[int, bool]


@contextmanager
def _field_size_limit() -> Iterator[None]:
    '''Raise the `csv` field size limit to `FIELD_SIZE_LIMIT`, and restore it afterwards.'''
    previous = csv.field_size_limit(FIELD_SIZE_LIMIT)
    try:
        yield
    finally:
        csv.field_size_limit(previous)


def _starts_with_bom(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> bool:
    with archive.open(info) as member:
        return member.read(len(codecs.BOM_UTF8)) == codecs.BOM_UTF8


def _text(archive: zipfile.ZipFile, info: zipfile.ZipInfo,
          errors: str = 'strict') -> io.TextIOWrapper:
    '''A member as text. `utf-8-sig` removes one leading BOM and `newline=''` keeps line
    breaks inside quoted values for `csv.reader`.'''
    return io.TextIOWrapper(archive.open(info), encoding='utf-8-sig', errors=errors, newline='')


def _row_digest(record: list[str]) -> str:
    text = json.dumps(record, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _subaward_members(archive: zipfile.ZipFile, layout: SubawardLayout) -> list[zipfile.ZipInfo]:
    '''Every member in name order. Any member but a CSV member of the registry fails.'''
    infos = archive.infolist()
    for info in infos:
        if info.is_dir() or not re.fullmatch(layout.member_pattern, info.filename):
            raise ValueError('unexpected ZIP member')
    if not infos:
        raise ValueError('no subaward CSV member')
    return sorted(infos, key=lambda info: info.filename)


def _empty_batch() -> dict[str, list]:
    return {name: [] for name in SUBAWARD_SCHEMA}


def _write_batch(batch: dict[str, list], file: Path) -> None:
    pl.DataFrame(batch, schema=SUBAWARD_SCHEMA).write_parquet(file)


def _read_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo, layout: SubawardLayout,
                 year: int, index: int, folder: Path) -> int:
    '''Write one member's rows to scratch parts and return its data-record count.'''
    width = len(layout.header)
    cells = {field: layout.header.index(cell) for field, cell in layout.columns.items()
             if cell is not None}
    batch = _empty_batch()
    written = 0
    records = 0
    try:
        with _text(archive, info) as text:
            reader = csv.reader(text, strict=True)
            if next(reader, None) != list(layout.header):
                raise ValueError('changed header')
            for record in reader:
                if len(record) != width:
                    raise ValueError('ragged subaward record')
                records += 1
                batch['file_year'].append(year)
                batch['member'].append(info.filename)
                batch['record'].append(records)
                for field in SUBAWARD_FIELDS:
                    batch[field].append(record[cells[field]] if field in cells else '')
                batch['row_digest'].append(_row_digest(record))
                if len(batch['record']) == BATCH_ROWS:
                    _write_batch(batch, folder / f'{year}-{index:03d}-{written:05d}.parquet')
                    written += 1
                    batch = _empty_batch()
    except UnicodeDecodeError as error:
        raise ValueError('subaward file is not UTF-8') from error
    except csv.Error as error:
        raise ValueError('malformed subaward CSV') from error
    if batch['record']:
        _write_batch(batch, folder / f'{year}-{index:03d}-{written:05d}.parquet')
    return records


def read_subawards(files: dict[int, Path], layouts: dict[int, SubawardLayout],
                   scratch: Path) -> SubawardRead:
    '''Read every CSV member of each file year's ZIP with that year's registry layout.

    The rows are a lazy scan of the Parquet parts under `scratch / 'subawards'`, in
    `SUBAWARD_SCHEMA`, ordered by file year, member name and record. `record` counts data
    records from 1 in each member. The scan must hold exactly the records read.
    '''
    folder = scratch / 'subawards'
    folder.mkdir(parents=True, exist_ok=True)
    members, records, bom = {}, {}, {}
    with _field_size_limit():
        for year in sorted(files):
            layout = layouts[year]
            with zipfile.ZipFile(files[year]) as archive:
                infos = _subaward_members(archive, layout)
                counts = [_read_member(archive, info, layout, year, index, folder)
                          for index, info in enumerate(infos)]
                bom[year] = any(_starts_with_bom(archive, info) for info in infos)
            members[year] = tuple(info.filename for info in infos)
            records[year] = sum(counts)
    parts = sorted(folder.glob('*.parquet'))
    rows = (pl.scan_parquet(parts, glob=False) if parts
            else pl.LazyFrame(schema=SUBAWARD_SCHEMA))
    if rows.select(pl.len()).collect().item() != sum(records.values()):
        raise ValueError('row count differs')
    return SubawardRead(rows=rows, members=members, records=records, bom=bom)


def _member_shape(archive: zipfile.ZipFile, info: zipfile.ZipInfo,
                  errors: str) -> tuple[list[str] | None, int, int]:
    with _text(archive, info, errors) as text:
        reader = csv.reader(text, strict=True)
        header = next(reader, None)
        records = ragged = 0
        for record in reader:
            records += 1
            ragged += len(record) != len(header)
    return header, records, ragged


def _describe_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> dict:
    try:
        header, records, ragged = _member_shape(archive, info, 'strict')
        utf8_valid = True
    except UnicodeDecodeError:
        header, records, ragged = _member_shape(archive, info, 'replace')
        utf8_valid = False
    return {'name': info.filename, 'header': header, 'bom': _starts_with_bom(archive, info),
            'utf8_valid': utf8_valid, 'records': records, 'ragged': ragged}


def subaward_headers(file: Path) -> dict:
    '''Describe every member of a subaward ZIP, in name order, for the preflight.

    For each member: its name, its first record as the header (None when it has none),
    whether it starts with a BOM, whether all of its bytes are UTF-8, its records after the
    header, and how many of them have a field count other than the header's. A member that
    is not UTF-8 is read with replacement characters for the counts. A member that breaks
    the CSV quote rules or the field size limit raises `malformed subaward CSV`, so that no
    run of row text can pass for a header cell.
    '''
    with _field_size_limit(), zipfile.ZipFile(file) as archive:
        infos = sorted(archive.infolist(), key=lambda info: info.filename)
        try:
            return {'members': [_describe_member(archive, info) for info in infos]}
        except csv.Error as error:
            raise ValueError('malformed subaward CSV') from error


def _extract_member(archive: zipfile.ZipFile, layout: ExtractLayout) -> zipfile.ZipInfo:
    infos = archive.infolist()
    if len(infos) != 1 or not re.fullmatch(layout.member_pattern, infos[0].filename):
        raise ValueError('unexpected extract member')
    return infos[0]


def _framed(text: io.TextIOWrapper) -> Iterator[tuple[str, int, str]]:
    '''Yield `(kind, line number, line)` with one line end removed from each line.

    `kind` is `first` for the first line, `last` for the last line of two or more, and
    `data` for each line between them.
    '''
    lines = (line.removesuffix('\n').removesuffix('\r') for line in text)
    numbered = enumerate(lines, start=1)
    first = next(numbered, None)
    if first is None:
        return
    yield 'first', *first
    previous = next(numbered, None)
    if previous is None:
        return
    for current in numbered:
        yield 'data', *previous
        previous = current
    yield 'last', *previous


@contextmanager
def _extract_text(file: Path, layout: ExtractLayout) -> Iterator[tuple[str, io.TextIOWrapper]]:
    '''The one extract member's name and its text, split into lines at `\\n` only.'''
    with zipfile.ZipFile(file) as archive:
        info = _extract_member(archive, layout)
        with io.TextIOWrapper(archive.open(info), encoding=layout.encoding,
                              newline='\n') as text:
            yield info.filename, text


def _data_lines(file: Path, layout: ExtractLayout) -> Iterator[tuple[int, list[str]]]:
    '''Yield each data line's number and its fields, split at the delimiter.

    The first line must start with the BOF prefix, checked before the first data line, and
    the last line with the EOF prefix, checked after the last data line. Either failure
    raises `missing extract framing`.
    '''
    framed = False
    with _extract_text(file, layout) as (_, text):
        for kind, number, line in _framed(text):
            if kind == 'first':
                if not line.startswith(layout.bof_prefix):
                    raise ValueError('missing extract framing')
            elif kind == 'last':
                if not line.startswith(layout.eof_prefix):
                    raise ValueError('missing extract framing')
                framed = True
            else:
                yield number, line.split(layout.delimiter)
    if not framed:
        raise ValueError('missing extract framing')


def read_extract(file: Path, layout: ExtractLayout) -> pl.DataFrame:
    '''The registered positions of every data line of the layout's field count, as
    delivered, in `EXTRACT_SCHEMA`.

    A data line with another field count is skipped: it gives no row and no error, and
    `unreadable_extract_lines` lists it. A data line of the field count whose last field is
    not the record end raises `missing record end`. `line` is the line number in the member,
    so the first data line is line 2. An unmapped `evs_source` reads as empty text.
    '''
    columns = {name: [] for name in EXTRACT_SCHEMA}
    for number, fields in _data_lines(file, layout):
        if len(fields) != layout.field_count:
            continue
        if layout.record_end is not None and fields[-1] != layout.record_end:
            raise ValueError('missing record end')
        columns['line'].append(number)
        for field in EXTRACT_FIELDS:
            position = layout.positions[field]
            columns[field].append('' if position is None else fields[position - 1])
    return pl.DataFrame(columns, schema=EXTRACT_SCHEMA)


def unreadable_extract_lines(file: Path, layout: ExtractLayout) -> pl.DataFrame:
    '''Each data line whose field count differs from the layout's, in `UNREADABLE_SCHEMA`
    and in line order: its line number, its value at the registered UEI position as
    delivered, and its field count.

    The UEI position comes before every restricted position, so a line that a `|` inside a
    later text field split still holds the UEI there. A line with fewer fields than that
    position has an empty UEI. No other field is read, and the record end is not checked.
    The member and framing checks are those of `read_extract`.
    '''
    position = layout.positions['uei']
    columns = {name: [] for name in UNREADABLE_SCHEMA}
    for number, fields in _data_lines(file, layout):
        if len(fields) == layout.field_count:
            continue
        columns['line'].append(number)
        columns['uei'].append(fields[position - 1] if len(fields) >= position else '')
        columns['fields'].append(len(fields))
    return pl.DataFrame(columns, schema=UNREADABLE_SCHEMA)


def extract_summary(file: Path, layout: ExtractLayout) -> dict:
    '''Describe the extract's framing and field counts for the preflight, without values.

    `unreadable_lines` counts the data lines whose field count differs from the layout's,
    which the build skips. `record_end_matches` counts the data lines whose last field is
    the record end (None when the layout names none). The BOF and EOF lines appear only when
    they match their prefix, because a line that does not may be an entity record.
    '''
    counts = Counter()
    ends = 0
    first = last = None
    with _extract_text(file, layout) as (member, text):
        for kind, _, line in _framed(text):
            if kind == 'first':
                first = line
            elif kind == 'last':
                last = line
            else:
                fields = line.split(layout.delimiter)
                counts[len(fields)] += 1
                ends += fields[-1] == layout.record_end
    bof_matches = first is not None and first.startswith(layout.bof_prefix)
    eof_matches = last is not None and last.startswith(layout.eof_prefix)
    unreadable = sum(count for width, count in counts.items() if width != layout.field_count)
    summary = {'member': member, 'data_lines': sum(counts.values()),
               'field_counts': dict(counts), 'unreadable_lines': unreadable,
               'bof_matches': bof_matches,
               'eof_matches': eof_matches,
               'record_end_matches': None if layout.record_end is None else ends}
    if bof_matches:
        summary['bof'] = first
    if eof_matches:
        summary['eof'] = last
    return summary
