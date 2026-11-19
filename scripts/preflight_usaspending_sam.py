'''The Stage 14 preflight data checks E4 and E5 on the recorded raw files.

`headers` describes the files as delivered: for each window year the subaward ZIP members
with their header cells and the keyword hints, and for the SAM.gov extract its framing,
the shapes of the values at each mapped position and the tallies of two coded fields.
`measure` reads the files with a draft subaward registry, the committed extract layout and
the pinned Stage 4 nodes through the build's own readers and status functions, so that its
counts are the ones the build will see, and prints E4, E5 and the spec's stops and asks.

Both commands print one sorted JSON object. They exit 0 when no stop holds, 1 when one
does and 2 on a refusal. Output holds counts, shares, header cells, value shapes and tallies
of coded values, never a UEI, a name, an address, an amount or any other row value. Two
guards hold this structurally: `headers` prints a year's header cells only when they are
lower-case names, and a tally whose values do not look coded is replaced by its number of
distinct values. Either withholding is a stop. A refusal prints a fixed reason and never
exception text. The script loads no `.env`, reads no key, opens no HTTP client and runs no
upstream builder. `measure` reads in a temporary directory outside the data root, and
neither command writes under the data root.
'''

import argparse
import json
import re
import sys
import tempfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import polars as pl

from embedding_data import (
    manifest,
    sam_raw,
    usaspending_raw,
    vendor_link_codes,
    vendor_link_layouts,
    vendor_link_pairs,
    vendor_link_readers,
)
from embedding_data.usaspending_raw import WINDOW
from embedding_data.vendor_link_layouts import EXTRACT_FIELDS, PARENT_FIELDS

HINTS = {'prime_uei': ('prime', 'uei'), 'prime_parent_uei': ('prime', 'parent', 'uei'),
         'sub_uei': ('sub', 'uei'), 'sub_parent_uei': ('sub', 'parent', 'uei'),
         'action_date': ('action', 'date'), 'amount': ('amount',), 'subaward_type': ('type',),
         'report_id': ('report',), 'subaward_naics': ('naics',), 'prime_naics': ('naics',)}
SHAPES = 10
TRIGGER_SHARE = 0.01
COVERAGE_SHARE = 0.5
ROLES = ('prime', 'subcontractor')
# A year without one of these columns stops the stage, and a year without one of these
# asks the owner.
STOP_FIELDS = ('prime_uei', 'sub_uei', 'action_date')
ASK_FIELDS = ('subaward_type', 'amount')
SHAPED_FIELDS = ('action_date', 'amount')
TALLIED_FIELDS = ('registration_status', 'evs_source')
# The tallies of delivered extract values in the E5 extract counts. Its other tallies count
# fixed statuses or the years and months of parsed dates.
EXTRACT_TALLIES = ('by_registration_status', 'evs_source')
# A delivered header cell is a lower-case snake_case name. A UEI, an amount or a date is not.
HEADER_NAME = re.compile(r'[a-z][a-z0-9_]*')
# A tally of a coded field has few distinct values, and each is short.
TALLY_VALUES = 25
TALLY_LENGTH = 40
# The fixed messages of the raw-file selectors and the readers. A refusal prints one of
# these or the fixed reason of the step that failed, never other exception text.
MESSAGES = frozenset({
    'missing or extra raw file', 'raw file is not recorded', 'raw file changed',
    'month is not YYYY-MM', 'unexpected ZIP member', 'changed header',
    'ragged subaward record', 'subaward file is not UTF-8', 'malformed subaward CSV',
    'unexpected extract member', 'missing extract framing', 'wrong field count',
    'missing record end'})
# The extract reader's refusals that the extract summary already shows.
FRAMING = frozenset({'missing extract framing', 'wrong field count', 'missing record end'})


class Refused(Exception):
    '''A refusal. Its one argument is a fixed reason.'''


@contextmanager
def step(reason: str, *, not_utf8: str | None = None) -> Iterator[None]:
    '''Turn a failure inside the block into a refusal: a message of `MESSAGES`, `not_utf8`
    for a byte that is not UTF-8, or otherwise `reason`.'''
    try:
        yield
    except UnicodeDecodeError:
        raise Refused(not_utf8 or reason) from None
    except Exception as error:
        raise Refused(str(error) if str(error) in MESSAGES else reason) from None


def shape(column: str) -> pl.Expr:
    '''`A` for each letter, `9` for each digit, and every other character kept.'''
    return pl.col(column).str.replace_all(r'\p{L}', 'A').str.replace_all(r'\p{Nd}', '9')


def shapes(frame: pl.LazyFrame | pl.DataFrame, column: str) -> list[dict]:
    '''The `SHAPES` most frequent shapes of `column`, by count and then by shape.'''
    counts = (frame.lazy().group_by(shape=shape(column)).agg(count=pl.len())
              .sort(['count', 'shape'], descending=[True, False]).head(SHAPES).collect())
    return [{'count': int(count), 'shape': text} for text, count in counts.iter_rows()]


def tally(frame: pl.DataFrame, column: str) -> dict[str, int]:
    '''The count of each delivered value of `column`.'''
    counts = frame.group_by(column).agg(pl.len())
    return {value: int(count) for value, count in counts.iter_rows()}


def coded(counts: dict[str, int]) -> bool:
    '''Whether a tally looks like one of a coded field: at most `TALLY_VALUES` distinct
    values, each at most `TALLY_LENGTH` characters long.'''
    return len(counts) <= TALLY_VALUES and all(len(value) <= TALLY_LENGTH for value in counts)


def guard(tallies: dict | None, keys: Iterable[str], name: str) -> list[str]:
    '''Replace each tally of `tallies` under `keys` that does not look coded by its number of
    distinct values, and return the stop `<name>_not_coded` when one was replaced.'''
    replaced = False
    for key in keys if tallies is not None else ():
        counts = tallies[key]
        if counts is not None and not coded(counts):
            tallies[key] = {'too_many_values': len(counts)}
            replaced = True
    return [f'{name}_not_coded'] if replaced else []


def hints(header: list[str]) -> dict[str, list[str]]:
    '''For each field, the header cells whose lower-case text, with `_` read as a space,
    holds every keyword of `HINTS[field]`. Hints are not decisions.'''
    texts = [(cell, cell.lower().replace('_', ' ')) for cell in header]
    return {field: [cell for cell, text in texts if all(word in text for word in words)]
            for field, words in HINTS.items()}


def relative(data_dir: Path, file: Path) -> str:
    return file.relative_to(data_dir).as_posix()


# ---- headers

def names(header: list[str] | None) -> bool:
    '''Whether every cell of a member's first record is a lower-case name. An empty member
    has no first record to print.'''
    return header is None or all(HEADER_NAME.fullmatch(cell) for cell in header)


def describe_year(data_dir: Path, file: Path) -> dict:
    '''A year's file and members. The header cells and hints appear only when every member
    has the same first record and its cells are lower-case names, because a member without
    a header row would put a data row in their place.'''
    with step('subaward file is unreadable'):
        members = vendor_link_readers.subaward_headers(file)['members']
    first = members[0]['header'] if members else None
    mismatch = any(member['header'] != first for member in members)
    not_names = not all(names(member['header']) for member in members)
    withheld = mismatch or not_names
    for member in members:
        member['cells'] = None if member['header'] is None else len(member['header'])
        if withheld:
            member['header'] = None
    return {'path': relative(data_dir, file), 'sha256': manifest.sha256_file(file),
            'members': members, 'header_mismatch': mismatch, 'header_not_names': not_names,
            'hints': None if withheld or first is None else hints(first)}


def describe_extract(data_dir: Path, file: Path,
                     layout: vendor_link_layouts.ExtractLayout) -> dict:
    '''The extract summary, and the shapes and tallies of the values that the build reads.
    The values are absent when the build's reader refuses a line the summary describes.'''
    with step('extract is unreadable', not_utf8='extract is not UTF-8'):
        summary = vendor_link_readers.extract_summary(file, layout)
        try:
            extract = vendor_link_readers.read_extract(file, layout)
        except ValueError as error:
            if str(error) not in FRAMING:
                raise
            extract = None
    mapped = [field for field in EXTRACT_FIELDS if layout.positions[field] is not None]
    values = extract is not None
    return {'path': relative(data_dir, file), 'sha256': manifest.sha256_file(file), **summary,
            'shapes': {field: shapes(extract, field) for field in mapped} if values else None,
            'tallies': {field: tally(extract, field) if field in mapped else None
                        for field in TALLIED_FIELDS} if values else None}


def headers(options: argparse.Namespace) -> dict:
    data_dir = options.data_dir
    with step('subaward files are refused'):
        files = usaspending_raw.select_files(data_dir, options.snapshot)
    with step('extract is refused'):
        extract_file = sam_raw.select_extract(data_dir, options.sam_month)
    with step('extract layout is unreadable'):
        layout = vendor_link_layouts.load_extract_layout()
    subawards = {str(year): describe_year(data_dir, files[year]) for year in WINDOW}
    extract = describe_extract(data_dir, extract_file, layout)
    stops = [f'headers_differ_{year}' for year, described in subawards.items()
             if described['header_mismatch']]
    stops += [f'headers_not_names_{year}' for year, described in subawards.items()
              if described['header_not_names']]
    for field in TALLIED_FIELDS:
        stops += guard(extract['tallies'], [field], field)
    return {'subawards': subawards, 'extract': extract, 'stops': stops}


# ---- measure

def measure_stops(layouts: dict[int, vendor_link_layouts.SubawardLayout],
                  malformed: dict[str, int]) -> list[str]:
    '''The spec's E4 and E5 stops, by rule and then by year.'''
    stops = [f'no_{field}_{year}' for field in STOP_FIELDS for year in WINDOW
             if layouts[year].columns[field] is None]
    stops += [f'no_parent_columns_{year}' for year in WINDOW
              if all(layouts[year].columns[field] is None for field in PARENT_FIELDS)]
    if malformed['read_rows'] > 0:
        stops.append('malformed_read_codes')
    return stops


def measure_asks(layouts: dict[int, vendor_link_layouts.SubawardLayout], e5: dict,
                 other_types: bool) -> list[str]:
    '''The owner's questions, by rule and then by year. A share of None (no UEI to count)
    asks nothing, and neither do the firm counts when `e5` lacks them.'''
    asks = []
    trigger = e5.get('trigger', {}).get('share')
    if trigger is not None and trigger > TRIGGER_SHARE:
        asks.append('trigger_above_one_percent')
    for role in ROLES:
        share = e5.get('join_coverage', {}).get(role, {}).get('share')
        if share is not None and share < COVERAGE_SHARE:
            asks.append(f'low_coverage_{role}')
    asks += [f'no_{field}_{year}' for field in ASK_FIELDS for year in WINDOW
             if layouts[year].columns[field] is None]
    if other_types:
        asks.append('subaward_type_not_sub_contract')
    return asks


def evaluate(read: vendor_link_readers.SubawardRead, extract: pl.DataFrame,
             layouts: dict[int, vendor_link_layouts.SubawardLayout],
             layout: vendor_link_layouts.ExtractLayout, node_ids: frozenset[str]) -> dict:
    '''E4 and E5 through the build's functions, and the stops and asks.

    A malformed code on a read firm makes `firms` raise, so then the firm table is empty
    and only the counts that do not depend on it are printed. The pair tally is never
    printed, so the pair table is always empty.
    '''
    reported = vendor_link_pairs.reports(read.rows, layouts)
    usable = reported.filter(pl.col('report_status') == 'usable')
    malformed = vendor_link_pairs.count_malformed(usable, extract, layout)
    if malformed['read_rows'] > 0:
        firm_table = pl.DataFrame(schema=vendor_link_pairs.FIRM_SCHEMA)
        e5_keys = ('extract',)
    else:
        firm_table = vendor_link_pairs.firms(usable, extract, layout, node_ids)
        e5_keys = ('firms', 'join_coverage', 'trigger', 'extract')
    pair_table = pl.DataFrame(schema=vendor_link_pairs.PAIR_SCHEMA)
    counts = vendor_link_pairs.report_counts(reported, firm_table, pair_table, extract,
                                             layouts, layout, node_ids)

    def in_year(year: int) -> pl.LazyFrame:
        return read.rows.filter(pl.col('file_year') == year)

    def mapped(field: str) -> list[int]:
        return [year for year in WINDOW if layouts[year].columns[field] is not None]

    typed = mapped('subaward_type')
    e4 = {
        'headers': {str(year): list(layouts[year].header) for year in WINDOW},
        'columns': {str(year): dict(layouts[year].columns) for year in WINDOW},
        'subaward_types': {str(year): vendor_link_pairs.subaward_types(in_year(year))
                           if year in typed else None for year in WINDOW},
        'shapes': {field: {str(year): shapes(in_year(year), field)
                           if year in mapped(field) else None for year in WINDOW}
                   for field in SHAPED_FIELDS},
        'reports': counts['reports'],
    }
    e5 = {key: counts[key] for key in e5_keys} | {'malformed': malformed}
    try:
        vendor_link_pairs.check_subaward_types(
            read.rows.filter(pl.col('file_year').is_in(typed)))
        other_types = False
    except ValueError:
        other_types = True
    stops = measure_stops(layouts, malformed)
    # One stop for the types of all years: each year's tally shows where it holds.
    stops += guard(e4['subaward_types'], [str(year) for year in WINDOW], 'subaward_types')
    for key in EXTRACT_TALLIES:
        stops += guard(e5['extract'], [key], key)
    return {'e4': e4, 'e5': e5, 'stops': stops,
            'asks': measure_asks(layouts, e5, other_types), 'ok': not stops}


def measure(options: argparse.Namespace) -> dict:
    data_dir = options.data_dir
    with step('subaward registry is unreadable'):
        layouts = vendor_link_layouts.parse_subaward_layouts(
            json.loads(options.registry.read_text(encoding='utf-8')), draft=True)
    with step('extract layout is unreadable'):
        layout = vendor_link_layouts.load_extract_layout()
    with step('subaward files are refused'):
        files = usaspending_raw.select_files(data_dir, options.snapshot)
    with step('extract is refused'):
        extract_file = sam_raw.select_extract(data_dir, options.sam_month)
    with step('codes bundle is refused'):
        nodes = vendor_link_codes.select_nodes(
            data_dir, options.codes_run, codes_outputs_sha256=options.codes_outputs_sha256)
    # Checked before the directory exists, so that a refusal creates nothing either.
    if Path(tempfile.gettempdir()).resolve().is_relative_to(data_dir.resolve()):
        raise Refused('scratch is under the data root')
    with tempfile.TemporaryDirectory() as scratch:
        with step('subaward file is unreadable'):
            read = vendor_link_readers.read_subawards(files, layouts, Path(scratch))
        with step('extract is unreadable', not_utf8='extract is not UTF-8'):
            extract = vendor_link_readers.read_extract(extract_file, layout)
        return evaluate(read, extract, layouts, layout, nodes.node_ids)


COMMANDS = {'headers': headers, 'measure': measure}


def parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Preflight data checks E4 and E5 of the USAspending vendor links.')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in COMMANDS:
        command = commands.add_parser(name)
        command.add_argument('--data-dir', type=Path, required=True)
        command.add_argument('--snapshot', type=date.fromisoformat, required=True)
        command.add_argument('--sam-month', required=True)
        if name == 'measure':
            command.add_argument('--registry', type=Path, required=True)
            command.add_argument('--codes-run', required=True)
            command.add_argument('--codes-outputs-sha256', required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    '''Print one sorted JSON object. Exit 0 with no stop, 1 with a stop, 2 on a refusal.

    Every failure is a refusal with a fixed reason. No exception text or traceback is
    printed, because it may hold a row value.
    '''
    options = parse(argv)
    try:
        report = COMMANDS[options.command](options)
        code = 1 if report['stops'] else 0
    except Refused as refusal:
        report, code = {'reason': refusal.args[0], 'refused': True}, 2
    except Exception:
        report, code = {'reason': 'unexpected error', 'refused': True}, 2
    print(json.dumps(report, sort_keys=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
