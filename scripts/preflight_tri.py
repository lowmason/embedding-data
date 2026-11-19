'''Preflight data checks for the EPA TRI basic data files (open checks E7 and E8).

`headers` prints, for each window year, the selected raw file, its exact header row, a BOM
flag, the count of lines that are not valid UTF-8, the CSV record count and hint lists of
header cells for each logical field. A hint matches a normalized cell exactly. The
normalization drops a leading `<digits>.`, upper-cases the cell, reads `_` as a space and
collapses spaces. Hints are suggestions, not decisions.

`measure` reads a draft layout (`tri_layout` JSON that may hold null columns and empty value
sets) and prints the E7 and E8 measures of each year, then `stops`, `asks` and `ok`. A stop
is a failed stop condition of the spec's preflight table. An ask is the 1% trigger or a
missing column that the owner should know about. The draft's header must equal the file's
header row, because the columns are found by header text.

Both commands read only the manifested raw files and, for `measure`, the pinned Stage 4
nodes. They are offline, load no `.env` and write no file. They print one sorted JSON line.
The exit status is 0 when no stop condition holds, 1 when one does and 2 on a refusal. A
refusal prints a fixed reason, never an exception text or row content. A D&B number is never
printed, except that `measure` lists the 20 most frequent `parent_dnb` values that are not
nine ASCII digits.
'''

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from embedding_data import manifest, tri_codes, tri_layout, tri_raw
from embedding_data.osha_encoding import decode_line

BOM = b'\xef\xbb\xbf'
TOP = 20
NINE_DIGITS = re.compile(r'[0-9]{9}')
LEADING_NUMBER = re.compile(r'^\s*[0-9]+\.')
PARENT_FIELDS = ('parent_name', 'parent_dnb', 'standardized_parent',
                 *tri_layout.FOREIGN_FIELDS)
VALUE_COUNTS = ('form_type', 'federal', 'state')
# The fields whose absence is only an ask. The key is the logical field.
ASKED_FIELDS = ('reporting_year', 'trifd', 'form_type', 'parent_dnb')
# Hint phrases for each logical field, from the spec's field names. Nobody has read the real
# EPA header yet, so these are guesses that the printed header row corrects.
HINTS = {
    'reporting_year': ('YEAR', 'REPORTING YEAR'),
    'trifd': ('TRIFD', 'TRI FACILITY ID', 'FACILITY ID'),
    'document_control_number': ('DOCUMENT CONTROL NUMBER', 'DOCUMENT CONTROL NUM', 'DCN'),
    'form_type': ('FORM TYPE',),
    'state': ('STATE', 'ST'),
    'federal': ('FEDERAL FACILITY', 'FEDERAL'),
    'primary_naics': ('PRIMARY NAICS', 'PRIMARY NAICS CODE', 'NAICS 1', '1ST NAICS'),
    'other_naics': ('NAICS 2', 'NAICS 3', 'NAICS 4', 'NAICS 5', 'NAICS 6'),
    'parent_name': ('PARENT NAME', 'PARENT CO NAME', 'PARENT COMPANY NAME'),
    'parent_dnb': ('PARENT D&B NUMBER', 'PARENT DNB NUMBER', 'PARENT CO DB NUM',
                   'PARENT COMPANY DB NUMBER'),
    'standardized_parent': ('STANDARDIZED PARENT', 'STANDARDIZED PARENT NAME',
                            'STANDARDIZED PARENT COMPANY'),
    'foreign_parent_name': ('FOREIGN PARENT NAME', 'FOREIGN PARENT CO NAME',
                            'FOREIGN PARENT COMPANY NAME'),
    'foreign_parent_dnb': ('FOREIGN PARENT D&B NUMBER', 'FOREIGN PARENT DNB NUMBER',
                           'FOREIGN PARENT CO DB NUM', 'FOREIGN PARENT COMPANY DB NUMBER'),
    'standardized_foreign_parent': ('STANDARDIZED FOREIGN PARENT',
                                    'STANDARDIZED FOREIGN PARENT NAME',
                                    'STANDARDIZED FOREIGN PARENT COMPANY'),
}


class Refused(Exception):
    '''An input the script refuses. The message is a fixed reason, never row content.'''


def normalize(cell: str) -> str:
    '''Read a header cell for the hint match: no leading number, upper case, single spaces.'''
    text = LEADING_NUMBER.sub('', cell, count=1)
    return ' '.join(text.upper().replace('_', ' ').split())


def hints(header: list[str]) -> dict[str, list[str]]:
    '''The header cells, in header order, that match a hint of each logical field.'''
    found = {}
    for name, phrases in HINTS.items():
        wanted = {normalize(phrase) for phrase in phrases}
        found[name] = [cell for cell in header if normalize(cell) in wanted]
    return found


class RawCsv:
    '''One raw file read line by line through `decode_line`, one CSV record at a time.

    The BOM is dropped before the first line is decoded. A line that is not valid UTF-8 is
    counted and then decoded by `decode_line`. A line it cannot decode refuses the run. The
    counts are final once `rows` is exhausted. Blank lines are not records.
    '''

    def __init__(self, file: Path):
        self.file = file
        self.bom = False
        self.invalid_utf8_lines = 0
        self.records = 0
        self.header: list[str] = []

    def __enter__(self) -> 'RawCsv':
        self._stream = self.file.open('rb')
        try:
            self._reader = csv.reader(self._lines())
            self.header = self._next() or []
            if not self.header:
                raise Refused('file has no header row')
        except BaseException:
            self._stream.close()
            raise
        return self

    def __exit__(self, *exception) -> None:
        self._stream.close()

    def _lines(self) -> Iterator[str]:
        for number, raw in enumerate(self._stream):
            if number == 0 and raw.startswith(BOM):
                self.bom = True
                raw = raw[len(BOM):]
            try:
                raw.decode('utf-8')
            except UnicodeDecodeError:
                self.invalid_utf8_lines += 1
            try:
                text = decode_line(raw)
            except UnicodeDecodeError:
                raise Refused('a line cannot be decoded') from None
            yield text

    def _next(self) -> list[str] | None:
        try:
            return next(self._reader, None)
        except csv.Error:
            raise Refused('file is not valid CSV') from None

    def rows(self) -> Iterator[list[str]]:
        while (record := self._next()) is not None:
            if record:
                self.records += 1
                yield record


def selected_files(data_dir: Path, processed_as_of: date) -> dict[int, Path]:
    try:
        return tri_raw.select_files(data_dir, processed_as_of)
    except (ValueError, OSError):
        raise Refused('raw files cannot be selected') from None


def selected_nodes(data_dir: Path, codes_run: str, pin: str) -> frozenset[str]:
    try:
        return tri_codes.select_nodes(data_dir, codes_run, codes_outputs_sha256=pin).node_ids
    except (ValueError, OSError):
        raise Refused('codes nodes cannot be selected') from None


def headers(data_dir: Path, processed_as_of: date) -> dict:
    report = {}
    for year, file in selected_files(data_dir, processed_as_of).items():
        with RawCsv(file) as raw:
            for _ in raw.rows():
                pass
            report[str(year)] = {
                'path': file.relative_to(data_dir).as_posix(),
                'sha256': manifest.sha256_file(file),
                'header': raw.header,
                'bom': raw.bom,
                'invalid_utf8_lines': raw.invalid_utf8_lines,
                'records': raw.records,
                'hints': hints(raw.header),
            }
    return report


# The draft layout


def read_draft(file: Path) -> dict[int, tri_layout.HeaderLayout]:
    '''A draft layout, which may hold null columns and empty or absent value sets.

    It must name the window's years, a header of distinct nonblank cells for each, and only
    known fields. Every mapped column must be a header cell. `tri_layout.parse_layouts`
    refuses such a draft, so the script reads it on its own.
    '''
    try:
        document = json.loads(file.read_text())
    except (OSError, ValueError):
        raise Refused('layout file cannot be read') from None
    if not isinstance(document, dict):
        raise Refused('layout file cannot be read')
    if document.get('version') != tri_layout.LAYOUT_VERSION:
        raise Refused('layout version differs')
    years = document.get('years')
    if not isinstance(years, dict) or set(years) != {str(year) for year in tri_raw.WINDOW}:
        raise Refused('layout years differ from the window')
    return {year: _draft_year(year, years[str(year)]) for year in tri_raw.WINDOW}


def _draft_year(year: int, entry: object) -> tri_layout.HeaderLayout:
    if not isinstance(entry, dict):
        raise Refused('layout year is malformed')
    header = entry.get('header')
    if (not isinstance(header, list)
            or not all(isinstance(cell, str) and cell.strip() for cell in header)
            or len(set(header)) != len(header)):
        raise Refused('layout header is not a list of distinct nonblank cells')
    raw_columns = entry.get('columns', {})
    raw_values = entry.get('values', {})
    if not isinstance(raw_columns, dict) or not isinstance(raw_values, dict):
        raise Refused('layout year is malformed')
    if (set(raw_columns) - set(tri_layout.COLUMN_ORDER)
            or set(raw_values) - set(tri_layout.VALUE_SETS)):
        raise Refused('layout names an unknown field')
    columns = {name: raw_columns.get(name) for name in tri_layout.SCALAR_FIELDS}
    other = raw_columns.get(tri_layout.OTHER_NAICS)
    if other is None:
        other = []
    if not isinstance(other, list):
        raise Refused('layout year is malformed')
    mapped = [cell for cell in columns.values() if cell is not None] + other
    if any(cell not in header for cell in mapped):
        raise Refused('layout maps a cell that is not in the header')
    values = {}
    for name in tri_layout.VALUE_SETS:
        entries = raw_values.get(name, [])
        if not isinstance(entries, list) or not all(isinstance(item, str) for item in entries):
            raise Refused('layout year is malformed')
        values[name] = frozenset(entries)
    return tri_layout.HeaderLayout(year, tuple(header), columns, tuple(other), values)


# The measures


def filled(value: str | None, none_values: frozenset[str]) -> bool:
    '''A stripped value that is neither blank nor one of the year's "none" strings.'''
    return value is not None and value != '' and value not in none_values


def top(counter: Counter) -> list[list]:
    '''The most frequent values with their counts. Equal counts follow the value order.'''
    ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [[value, count] for value, count in ranked[:TOP]]


@dataclass
class FacilityYear:
    '''What the forms of one facility in one year say.'''

    primary: set[str] = field(default_factory=set)
    named: bool = False
    standardized: bool = False
    dnb: bool = False
    compared: bool = False
    differs: bool = False


class YearTally:
    '''The counts of one year's file. A measure that needs an unmapped column stays None.'''

    def __init__(self, layout: tri_layout.HeaderLayout, header: list[str]):
        self.layout = layout
        self.position = {name: header.index(cell) for name, cell in layout.columns.items()
                         if cell is not None}
        self.other = {cell: header.index(cell) for cell in layout.other_naics}
        self.no_parent = layout.values['no_parent']
        self.no_dnb = layout.values['no_dnb']
        self.rows = 0
        self.rows_without_trifd = 0
        self.counts = {name: Counter() for name in VALUE_COUNTS}
        self.names = {'parent_name': Counter(), 'standardized_parent': Counter()}
        self.dnb_odd = Counter()
        self.other_fill = dict.fromkeys(layout.other_naics, 0)
        self.document_control_numbers = Counter()
        self.fill_rows = Counter()
        self.facility_years: dict[str, FacilityYear] | None = (
            {} if 'trifd' in self.position else None)
        self.dnb_by_name = defaultdict(set)
        self.name_by_dnb = defaultdict(set)

    def stripped(self, row: list[str], name: str) -> str | None:
        return row[self.position[name]].strip() if name in self.position else None

    def add(self, row: list[str]) -> None:
        self.rows += 1
        for name, counter in self.counts.items():
            if name in self.position:
                counter[row[self.position[name]]] += 1
        parent = self.stripped(row, 'parent_name')
        standardized = self.stripped(row, 'standardized_parent')
        dnb = self.stripped(row, 'parent_dnb')
        named = filled(parent, self.no_parent)
        has_standardized = filled(standardized, self.no_parent)
        has_dnb = filled(dnb, self.no_dnb)
        for name, value, present in (('parent_name', parent, named),
                                     ('standardized_parent', standardized, has_standardized),
                                     ('parent_dnb', dnb, has_dnb)):
            self.fill_rows[name] += present
            if value is not None and name in self.names:
                self.names[name][value] += 1
        if dnb is not None and not NINE_DIGITS.fullmatch(dnb):
            self.dnb_odd[dnb] += 1
        for cell, position in self.other.items():
            self.other_fill[cell] += row[position].strip() != ''
        if 'document_control_number' in self.position:
            self.document_control_numbers[self.stripped(row, 'document_control_number')] += 1
        if has_standardized and has_dnb:
            self.dnb_by_name[standardized].add(dnb)
            self.name_by_dnb[dnb].add(standardized)
        facility_year = self.facility_year(row)
        if facility_year is None:
            return
        primary = self.stripped(row, 'primary_naics')
        if primary:
            facility_year.primary.add(primary)
        facility_year.named |= named
        facility_year.standardized |= has_standardized
        facility_year.dnb |= has_dnb
        if named and has_standardized:
            facility_year.compared = True
            facility_year.differs |= parent != standardized

    def facility_year(self, row: list[str]) -> FacilityYear | None:
        '''The facility-year of a row. None without a TRIFD column or with a blank TRIFD.'''
        if self.facility_years is None:
            return None
        trifd = row[self.position['trifd']]
        if not trifd.strip():
            self.rows_without_trifd += 1
            return None
        return self.facility_years.setdefault(trifd, FacilityYear())

    def value_counts(self, name: str) -> dict[str, int] | None:
        return dict(self.counts[name]) if name in self.position else None

    def naics_classes(self, nodes: frozenset[str]) -> dict[str, int | None]:
        classes = dict.fromkeys(
            ('naics_valid', 'naics_missing', 'naics_conflict', 'naics_not_2022'))
        if self.facility_years is None or 'primary_naics' not in self.position:
            return classes
        counts = Counter()
        for facility_year in self.facility_years.values():
            if not facility_year.primary:
                counts['naics_missing'] += 1
            elif len(facility_year.primary) > 1:
                counts['naics_conflict'] += 1
            elif tri_codes.NODE_PREFIX + next(iter(facility_year.primary)) in nodes:
                counts['naics_valid'] += 1
            else:
                counts['naics_not_2022'] += 1
        return {name: counts[name] for name in classes}

    def parent_cases(self) -> dict[str, int | None]:
        '''Cases (a), (b) and (c) of the spec's owner keys, and the name comparison.'''
        cases = dict.fromkeys(('case_a', 'case_b', 'case_c', 'standardized_compared',
                               'standardized_differs'))
        if self.facility_years is None or 'standardized_parent' not in self.position:
            return cases
        years = list(self.facility_years.values())
        if 'parent_dnb' in self.position:
            cases['case_c'] = sum(fy.dnb and not fy.standardized for fy in years)
        if 'parent_name' in self.position:
            cases['case_a'] = sum(fy.standardized and not fy.named for fy in years)
            cases['case_b'] = sum(fy.named and not fy.standardized for fy in years)
            cases['standardized_compared'] = sum(fy.compared for fy in years)
            cases['standardized_differs'] = sum(fy.differs for fy in years)
        return cases

    def fills(self) -> dict[str, dict | None]:
        '''Filled cells of each parent field, by row and by facility-year.'''
        years = None if self.facility_years is None else list(self.facility_years.values())
        fill = {}
        for name, attribute in (('parent_name', 'named'), ('standardized_parent', 'standardized'),
                                ('parent_dnb', 'dnb')):
            if name not in self.position:
                fill[name] = None
                continue
            fill[name] = {
                'rows': self.fill_rows[name],
                'facility_years': None if years is None else sum(
                    getattr(fy, attribute) for fy in years),
            }
        return fill

    def top_names(self, name: str) -> list[list] | None:
        return top(self.names[name]) if name in self.position else None

    def document_control_number(self) -> dict[str, int] | None:
        if 'document_control_number' not in self.position:
            return None
        numbers = self.document_control_numbers
        return {
            'blank': numbers[''],
            'distinct': len(numbers) - ('' in numbers),
            'repeated': sum(1 for number, rows in numbers.items() if number and rows > 1),
        }

    def result(self, nodes: frozenset[str]) -> dict:
        both = 'standardized_parent' in self.position and 'parent_dnb' in self.position
        return {
            'rows': self.rows,
            'rows_without_trifd': None if self.facility_years is None else (
                self.rows_without_trifd),
            'facility_years': None if self.facility_years is None else len(self.facility_years),
            **{name: self.value_counts(name) for name in VALUE_COUNTS},
            **self.naics_classes(nodes),
            'other_naics_fill': self.other_fill,
            'document_control_number': self.document_control_number(),
            'parent_fields': {name: self.layout.columns[name] for name in PARENT_FIELDS},
            'parent_name_top': self.top_names('parent_name'),
            'standardized_parent_top': self.top_names('standardized_parent'),
            'parent_dnb_not_nine_digits_top': top(self.dnb_odd)
            if 'parent_dnb' in self.position else None,
            'fill': self.fills(),
            'standardized_with_many_dnb': sum(len(v) > 1 for v in self.dnb_by_name.values())
            if both else None,
            'dnb_with_many_standardized': sum(len(v) > 1 for v in self.name_by_dnb.values())
            if both else None,
            **self.parent_cases(),
        }


def measure_year(file: Path, layout: tri_layout.HeaderLayout, nodes: frozenset[str]) -> dict:
    '''The E7 and E8 measures of one year's file.'''
    with RawCsv(file) as raw:
        if list(layout.header) != raw.header:
            raise Refused('layout header differs from the file header')
        tally = YearTally(layout, raw.header)
        for row in raw.rows():
            if len(row) != len(raw.header):
                raise Refused('a record has the wrong number of fields')
            tally.add(row)
        return {**tally.result(nodes), 'invalid_utf8_lines': raw.invalid_utf8_lines}


def judge(year: int, layout: tri_layout.HeaderLayout, report: dict) -> tuple[list, list]:
    '''The stops and the asks of one year.'''
    columns = layout.columns
    stops = []
    for reason, name in (('no_primary', 'primary_naics'), ('no_federal', 'federal'),
                         ('no_standardized', 'standardized_parent')):
        if columns[name] is None:
            stops.append({'reason': reason, 'year': year})
    # Every facility-year that reports a parent name lacks a standardized name. With no such
    # facility-year there is nothing to judge.
    reporting = (report['fill']['parent_name'] or {}).get('facility_years')
    if reporting and report['case_b'] == reporting:
        stops.append({'reason': 'standardized_always_blank', 'year': year})
    asks = []
    outside = report['naics_not_2022']
    if outside is not None and outside * 100 > report['facility_years']:
        asks.append({'reason': 'naics_not_2022_above_1_percent', 'year': year,
                     'naics_not_2022': outside, 'facility_years': report['facility_years']})
    asks += [{'reason': f'no_{name}', 'year': year} for name in ASKED_FIELDS
             if columns[name] is None]
    if columns['parent_name'] is None:
        asks.append({'reason': 'parent_name_unmapped', 'year': year})
    return stops, asks


def ordered(item: dict) -> tuple[int, str]:
    return item['year'], item['reason']


def measure(options: argparse.Namespace) -> dict:
    files = selected_files(options.data_dir, options.processed_as_of)
    nodes = selected_nodes(options.data_dir, options.codes_run, options.codes_outputs_sha256)
    layouts = read_draft(options.layout)
    years, stops, asks = {}, [], []
    for year, file in files.items():
        years[str(year)] = measure_year(file, layouts[year], nodes)
        year_stops, year_asks = judge(year, layouts[year], years[str(year)])
        stops += year_stops
        asks += year_asks
    return {
        'asks': sorted(asks, key=ordered),
        'inputs': {
            'codes_outputs_sha256': options.codes_outputs_sha256,
            'codes_run': options.codes_run,
            'files': {
                str(year): {'path': file.relative_to(options.data_dir).as_posix(),
                            'sha256': manifest.sha256_file(file)}
                for year, file in files.items()
            },
            'processed_as_of': options.processed_as_of.isoformat(),
        },
        'ok': not stops,
        'stops': sorted(stops, key=ordered),
        'years': years,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = result.add_subparsers(dest='command', required=True)
    for name, summary in (('headers', 'Print each year file and its exact header row.'),
                          ('measure', 'Print the E7 and E8 measures, the stops and the asks.')):
        command = commands.add_parser(name, help=summary, description=summary)
        command.add_argument('--data-dir', type=Path, required=True)
        command.add_argument('--processed-as-of', type=date.fromisoformat, required=True)
        if name == 'measure':
            command.add_argument('--layout', type=Path, required=True)
            command.add_argument('--codes-run', required=True)
            command.add_argument('--codes-outputs-sha256', required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    '''Print one sorted JSON line. Exit 0 with no stop, 1 with a stop and 2 on a refusal.'''
    options = parser().parse_args(argv)
    try:
        if options.command == 'headers':
            report, status = headers(options.data_dir, options.processed_as_of), 0
        else:
            report = measure(options)
            status = 0 if report['ok'] else 1
    except Refused as refusal:
        report, status = {'ok': False, 'reason': str(refusal)}, 2
    except Exception as error:
        report = {'ok': False, 'reason': f'unexpected error: {type(error).__name__}'}
        status = 2
    print(json.dumps(report, sort_keys=True))
    return status


if __name__ == '__main__':
    sys.exit(main())
