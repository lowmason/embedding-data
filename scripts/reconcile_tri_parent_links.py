'''Independent reconciliation of one published TRI parent-link bundle with its raw TRI files.

Written from the Stage 5 spec (`specs/tri-parent-links.md`), not from the build modules, and
importing none of them: only the standard library and Polars, which reads Parquet. It checks
the detached `outputs.json` pin and the bundle inventory, the three raw TRI files that
`inputs.json` cites, and the cited Stage 4 `naics_nodes.parquet`. It reads each CSV file with
`csv.reader` and its own decoding: UTF-8 with a byte order mark dropped, and Windows-1252
for only the bytes of a line that UTF-8 rejects. With plain sets and dicts it recomputes the
facility-year reduction, eligibility, n(a), J(a,b), the yearly j, N, both sensitivities, the
partial owners and the O8 counts, and compares them exactly with the five bundle tables and
with the report.

    python scripts/reconcile_tri_parent_links.py --data-dir D --run ID --outputs-sha256 PIN

It prints one sorted JSON line of counts and booleans, never a name, TRIFD or D&B number. It
returns 0 when everything is equal and 1 when something differs. A refusal (a wrong pin, an
unsafe path, unreadable inputs or raw bytes that differ from their citation) prints a fixed
reason and returns 2.
'''

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from datetime import date
from itertools import zip_longest
from pathlib import Path, PurePosixPath
from typing import BinaryIO

import polars as pl

BUNDLES = Path('derived/epa_tri/parent-links')
CODES = Path('derived/codes')
RAW = Path('raw')
WINDOW = (2022, 2023, 2024)
RUN_ID = re.compile('[A-Za-z0-9][A-Za-z0-9_-]*')
PIN = re.compile('[0-9a-f]{64}')
BYTE_ORDER_MARK = b'\xef\xbb\xbf'
NODES_FILE = 'naics_nodes.parquet'

# Spec "Eligibility": the exclusion reasons, in the order they are checked.
REASONS = ('naics_missing', 'naics_conflict', 'naics_not_2022', 'parent_conflict', 'federal')
# Spec "Companion tables", `n_owners_partial`: the reasons that make an owner partial.
PARTIAL_REASONS = frozenset(REASONS[:4])

# Spec "Target rows" and the plan's verbatim target metadata.
SIZE_GATE = 'size_gate_pending'
DNB_LABEL = 'numerator:dnb_key_sensitivity:true'
FEDERAL_LABEL = 'numerator:federal_sensitivity:true'
UNIVERSE = (
    'EPA Toxics Release Inventory basic data files, U.S. files for reporting years 2022–2024, '
    'forms processed as of {date}. TRI is a program-selected population of facilities that meet '
    'its reporting criteria, not a frame of all establishments or firms. Codes are self-reported '
    'primary NAICS 2022 codes, one per facility. A facility can contain more than one '
    "establishment. An owner is EPA's standardized highest-level U.S. parent, or the facility "
    'itself when it reports none. Federal facilities are excluded.'
)
UNIT_TYPE = 'naics_national_industry'

# The bundle tables, with the column types that the spec's tables give.
COUNT, TEXT, TEXTS = 'UInt64', 'String', 'List(String)'
FACILITY_SCHEMA = {
    'reporting_year': 'Int64', 'trifd': TEXT, 'n_forms': COUNT, 'n_form_r': COUNT,
    'n_form_a': COUNT, 'primary_naics_values': TEXTS, 'other_naics_values': TEXTS,
    'naics_2022_node_id': TEXT, 'parent_names': TEXTS, 'foreign_parent_names': TEXTS,
    'federal_values': TEXTS, 'state_values': TEXTS, 'flag_parent_mixed_blank': 'Boolean',
    'owner_key': TEXT, 'exclusion_reason': TEXT,
}
FACILITY_COLUMNS = tuple(FACILITY_SCHEMA)
ELIGIBILITY_COLUMNS = ('reporting_year', 'trifd', 'naics_2022_node_id', 'owner_key',
                       'exclusion_reason')
REDUCTION_COLUMNS = tuple(name for name in FACILITY_COLUMNS
                          if name not in ELIGIBILITY_COLUMNS[2:])
MARGINAL_SCHEMA = {
    'node_id': TEXT, 'n_owners': COUNT, 'n_parent_owners': COUNT,
    'n_multi_industry_owners': COUNT, 'n_facilities': COUNT, 'n_facility_years': COUNT,
    'n_owners_dnb': COUNT, 'n_owners_including_federal': COUNT, 'n_owners_partial': COUNT,
}
SUPPORT_SCHEMA = {
    'unit_a': TEXT, 'unit_b': TEXT, 'j_owners': COUNT, 'j_2022': COUNT, 'j_2023': COUNT,
    'j_2024': COUNT, 'j_dnb': COUNT, 'j_including_federal': COUNT,
}
INDUSTRY_SCHEMA = {
    'parent_name': TEXT, 'node_id': TEXT, 'n_facilities': COUNT, 'n_facility_years': COUNT,
    'f_2022': COUNT, 'f_2023': COUNT, 'f_2024': COUNT,
}
# The target rows: R7.4's columns in their physical order, with the `targets-v1` types
# (specs/completed/target-contract-ita-area-mix.md, "Shared target contract").
TARGET_SCHEMA = {
    'source': TEXT, 'family': TEXT, 'unit_a_type': TEXT, 'unit_a': TEXT, 'unit_b_type': TEXT,
    'unit_b': TEXT, 'measure': TEXT, 'value': 'Float64', 'se': 'Float64', 'se_method': TEXT,
    'n_unweighted': COUNT, 'n_weighted': 'Float64', 'sample_set': TEXT, 'vintage': TEXT,
    'universe': TEXT, 'flags': TEXTS,
}
TARGET_KEY = (list(TARGET_SCHEMA).index('unit_a'), list(TARGET_SCHEMA).index('unit_b'))
TARGET_VALUES = ('source', 'family', 'unit_a_type', 'unit_b_type', 'measure', 'value', 'se',
                 'se_method', 'n_unweighted', 'n_weighted', 'sample_set', 'vintage', 'universe',
                 'flags')
TABLE_FILES = {
    'targets': 'tri_parent_links.parquet',
    'marginals': 'tri_parent_link_marginals.parquet',
    'support': 'tri_parent_link_support.parquet',
    'parent_industries': 'tri_parent_industries.parquet',
    'facility_years': 'tri_facility_years.parquet',
}
INVENTORY = frozenset({*TABLE_FILES.values(), 'inputs.json', 'report.json'})
YEAR_COUNTS = ('rows', 'facility_years', 'mixed_blank', 'with_foreign_parent',
               'with_secondary_codes')

# The header layout of each window year, in the shape of the committed registry: the exact
# header row, the header cell of each field (None where a year lacks it) and the registered
# value sets. A test compares it with the committed registry.
HEADER = [
    '1. YEAR', '2. TRIFD', '3. FRS ID', '4. FACILITY NAME', '5. STREET ADDRESS', '6. CITY',
    '7. COUNTY', '8. ST', '9. ZIP', '10. BIA', '11. TRIBE', '12. LATITUDE', '13. LONGITUDE',
    '14. HORIZONTAL DATUM', '15. PARENT CO NAME', '16. PARENT CO DB NUM',
    '17. STANDARD PARENT CO NAME', '18. FOREIGN PARENT CO NAME', '19. FOREIGN PARENT CO DB NUM',
    '20. STANDARD FOREIGN PARENT CO NAME', '21. FEDERAL FACILITY', '22. INDUSTRY SECTOR CODE',
    '23. INDUSTRY SECTOR', '24. PRIMARY SIC', '25. SIC 2', '26. SIC 3', '27. SIC 4', '28. SIC 5',
    '29. SIC 6', '30. PRIMARY NAICS', '31. NAICS 2', '32. NAICS 3', '33. NAICS 4', '34. NAICS 5',
    '35. NAICS 6', '36. DOC_CTRL_NUM', '37. CHEMICAL', '38. ELEMENTAL METAL INCLUDED',
    '39. TRI CHEMICAL/COMPOUND ID', '40. CAS#', '41. SRS ID', '42. CLEAN AIR ACT CHEMICAL',
    '43. CLASSIFICATION', '44. METAL', '45. METAL CATEGORY', '46. CARCINOGEN', '47. PBT',
    '48. PFAS', '49. FORM TYPE', '50. UNIT OF MEASURE', '51. 5.1 - FUGITIVE AIR',
    '52. 5.2 - STACK AIR', '53. 5.3 - WATER', '54. 5.4 - UNDERGROUND',
    '55. 5.4.1 - UNDERGROUND CL I', '56. 5.4.2 - UNDERGROUND C II-V', '57. 5.5.1 - LANDFILLS',
    '58. 5.5.1A - RCRA C LANDFILL', '59. 5.5.1B - OTHER LANDFILLS', '60. 5.5.2 - LAND TREATMENT',
    '61. 5.5.3 - SURFACE IMPNDMNT', '62. 5.5.3A - RCRA SURFACE IM',
    '63. 5.5.3B - OTHER SURFACE I', '64. 5.5.4 - OTHER DISPOSAL', '65. ON-SITE RELEASE TOTAL',
    '66. 6.1 - POTW - TRNS RLSE', '67. 6.1 - POTW - TRNS TRT', '68. POTW - TOTAL TRANSFERS',
    '69. 6.2 - M10', '70. 6.2 - M41', '71. 6.2 - M62', '72. 6.2 - M40 METAL',
    '73. 6.2 - M61 METAL', '74. 6.2 - M71', '75. 6.2 - M81', '76. 6.2 - M82', '77. 6.2 - M72',
    '78. 6.2 - M63', '79. 6.2 - M66', '80. 6.2 - M67', '81. 6.2 - M64', '82. 6.2 - M65',
    '83. 6.2 - M73', '84. 6.2 - M79', '85. 6.2 - M90', '86. 6.2 - M94', '87. 6.2 - M99',
    '88. OFF-SITE RELEASE TOTAL', '89. 6.2 - M20', '90. 6.2 - M24', '91. 6.2 - M26',
    '92. 6.2 - M28', '93. 6.2 - M93', '94. OFF-SITE RECYCLED TOTAL', '95. 6.2 - M56',
    '96. 6.2 - M92', '97. OFF-SITE ENERGY RECOVERY T', '98. 6.2 - M40 NON-METAL', '99. 6.2 - M50',
    '100. 6.2 - M54', '101. 6.2 - M61 NON-METAL', '102. 6.2 - M69', '103. 6.2 - M95',
    '104. OFF-SITE TREATED TOTAL', '105. 6.2 - UNCLASSIFIED', '106. 6.2 - TOTAL TRANSFER',
    '107. TOTAL RELEASES', '108. 8.1 - RELEASES', '109. 8.1A - ON-SITE CONTAINED',
    '110. 8.1B - ON-SITE OTHER', '111. 8.1C - OFF-SITE CONTAIN', '112. 8.1D - OFF-SITE OTHER R',
    '113. 8.2 - ENERGY RECOVER ON', '114. 8.3 - ENERGY RECOVER OF',
    '115. 8.4 - RECYCLING ON SITE', '116. 8.5 - RECYCLING OFF SIT',
    '117. 8.6 - TREATMENT ON SITE', '118. 8.7 - TREATMENT OFF SITE',
    '119. PRODUCTION WSTE (8.1-8.7)', '120. 8.8 - ONE-TIME RELEASE',
    '121. PROD_RATIO_OR_ ACTIVITY', '122. 8.9 - PRODUCTION RATIO',
]
OTHER_NAICS = ['31. NAICS 2', '32. NAICS 3', '33. NAICS 4', '34. NAICS 5', '35. NAICS 6']
VALUES = {
    'federal_no': ['NO'], 'federal_yes': ['YES'], 'form_a': ['A'], 'form_r': ['R'],
    'no_dnb': ['NA'], 'no_parent': ['NA'],
}
LAYOUT: dict[str, dict] = {
    '2022': {
        'columns': {
            'document_control_number': '36. DOC_CTRL_NUM',
            'federal': '21. FEDERAL FACILITY',
            'foreign_parent_dnb': None,
            'foreign_parent_name': None,
            'form_type': '49. FORM TYPE',
            'other_naics': OTHER_NAICS,
            'parent_dnb': '16. PARENT CO DB NUM',
            'parent_name': '15. PARENT CO NAME',
            'primary_naics': '30. PRIMARY NAICS',
            'reporting_year': '1. YEAR',
            'standardized_foreign_parent': None,
            'standardized_parent': '17. STANDARD PARENT CO NAME',
            'state': '8. ST',
            'trifd': '2. TRIFD',
        },
        'header': HEADER,
        'values': VALUES,
    },
    '2023': {
        'columns': {
            'document_control_number': '36. DOC_CTRL_NUM',
            'federal': '21. FEDERAL FACILITY',
            'foreign_parent_dnb': '19. FOREIGN PARENT CO DB NUM',
            'foreign_parent_name': '18. FOREIGN PARENT CO NAME',
            'form_type': '49. FORM TYPE',
            'other_naics': OTHER_NAICS,
            'parent_dnb': '16. PARENT CO DB NUM',
            'parent_name': '15. PARENT CO NAME',
            'primary_naics': '30. PRIMARY NAICS',
            'reporting_year': '1. YEAR',
            'standardized_foreign_parent': '20. STANDARD FOREIGN PARENT CO NAME',
            'standardized_parent': '17. STANDARD PARENT CO NAME',
            'state': '8. ST',
            'trifd': '2. TRIFD',
        },
        'header': HEADER,
        'values': VALUES,
    },
    '2024': {
        'columns': {
            'document_control_number': '36. DOC_CTRL_NUM',
            'federal': '21. FEDERAL FACILITY',
            'foreign_parent_dnb': '19. FOREIGN PARENT CO DB NUM',
            'foreign_parent_name': '18. FOREIGN PARENT CO NAME',
            'form_type': '49. FORM TYPE',
            'other_naics': OTHER_NAICS,
            'parent_dnb': '16. PARENT CO DB NUM',
            'parent_name': '15. PARENT CO NAME',
            'primary_naics': '30. PRIMARY NAICS',
            'reporting_year': '1. YEAR',
            'standardized_foreign_parent': '20. STANDARD FOREIGN PARENT CO NAME',
            'standardized_parent': '17. STANDARD PARENT CO NAME',
            'state': '8. ST',
            'trifd': '2. TRIFD',
        },
        'header': HEADER,
        'values': VALUES,
    },
}


class Refused(Exception):
    '''An input that cannot be trusted or read. The message is a fixed reason, never data.'''


# Inputs.

def sha256(file: Path) -> str:
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(file: Path) -> dict:
    value = json.loads(file.read_bytes())
    if not isinstance(value, dict):
        raise Refused('bundle json is not an object')
    return value


def matching_file(file: Path, record: object) -> bool:
    '''Whether `file` is a regular file, not a link, whose size and SHA-256 match `record`.'''
    if not isinstance(record, dict) or file.is_symlink() or not file.is_file():
        return False
    return record.get('size') == file.stat().st_size and record.get('sha256') == sha256(file)


def open_bundle(data_dir: Path, run_id: str, pin: str) -> Path:
    '''The bundle directory, once `outputs.json` matches the pin and every file its record.'''
    if not data_dir.is_dir():
        raise Refused('data directory is missing')
    if not RUN_ID.fullmatch(run_id):
        raise Refused('unsafe run id')
    if not PIN.fullmatch(pin):
        raise Refused('malformed pin')
    directory = data_dir / BUNDLES / run_id
    outputs = directory / 'outputs.json'
    if directory.is_symlink() or outputs.is_symlink() or not outputs.is_file():
        raise Refused('bundle is missing')
    if sha256(outputs) != pin:
        raise Refused('detached pin differs')
    inventory = read_json(outputs)
    if set(inventory) != INVENTORY:
        raise Refused('bundle inventory differs')
    for name in sorted(INVENTORY):
        if not matching_file(directory / name, inventory[name]):
            raise Refused('bundle file differs from its inventory')
    return directory


def iso_date(text: object) -> bool:
    try:
        return isinstance(text, str) and date.fromisoformat(text).isoformat() == text
    except ValueError:
        return False


def select_raw(data_dir: Path, inputs: dict) -> tuple[str, dict[int, Path]]:
    '''The snapshot date and the cited raw file of each window year, once each hash matches.

    Each citation's path is `epa_tri/basic/<RY>/<processed-as-of>/<EPA file name>` under the
    raw tree (spec "Layout and manifest"), and the three cover the window exactly.
    '''
    processed = inputs.get('processed_as_of')
    if not iso_date(processed):
        raise Refused('snapshot date is malformed')
    if inputs.get('window') != list(WINDOW):
        raise Refused('window differs')
    entries = inputs.get('raw')
    if not isinstance(entries, list) or len(entries) != len(WINDOW):
        raise Refused('raw citations differ from the window')
    root = (data_dir / RAW).resolve()
    files = {}
    for entry in entries:
        path = entry.get('path') if isinstance(entry, dict) else None
        if not isinstance(path, str):
            raise Refused('raw citation is malformed')
        parts = PurePosixPath(path).parts
        if (len(parts) != 5 or parts[:2] != ('epa_tri', 'basic') or parts[3] != processed
                or parts[4] == '..'):
            raise Refused('raw path is unsafe')
        if parts[2] not in {str(year) for year in WINDOW} or int(parts[2]) in files:
            raise Refused('raw citations differ from the window')
        file = data_dir / RAW / path
        if file.is_symlink() or not file.resolve().is_relative_to(root):
            raise Refused('raw path is unsafe')
        if not matching_file(file, entry):
            raise Refused('raw file differs from its citation')
        files[int(parts[2])] = file
    return processed, files


def select_nodes(data_dir: Path, inputs: dict) -> dict[str, str]:
    '''The NAICS 2022 national-industry node ID of each code, from the cited Stage 4 bundle.

    The codes `outputs.json` must match the recorded pin and the recorded inventory, and
    `naics_nodes.parquet` its record in that inventory.
    '''
    codes = inputs.get('codes')
    if not isinstance(codes, dict):
        raise Refused('codes citation is malformed')
    run_id = codes.get('run_id')
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise Refused('unsafe codes run id')
    directory = data_dir / CODES / run_id
    outputs = directory / 'outputs.json'
    if directory.is_symlink() or outputs.is_symlink() or not outputs.is_file():
        raise Refused('codes bundle is missing')
    if sha256(outputs) != codes.get('outputs_sha256'):
        raise Refused('codes pin differs')
    inventory = read_json(outputs)
    if inventory != codes.get('outputs'):
        raise Refused('codes inventory differs')
    if not matching_file(directory / NODES_FILE, inventory.get(NODES_FILE)):
        raise Refused('codes nodes differ from their inventory')
    frame = (
        pl.scan_parquet(directory / NODES_FILE)
        .filter(pl.col('system').eq('naics'), pl.col('vintage').eq(2022),
                pl.col('level').eq('national_industry'))
        .select('code', 'node_id')
        .collect()
    )
    nodes = dict(frame.iter_rows())
    if len(nodes) != frame.height:
        raise Refused('codes nodes repeat a code')
    return nodes


# Reading the raw files.

def decoded_line(line: bytes) -> str:
    '''One line as text: UTF-8, with only the bytes that UTF-8 rejects decoded as Windows-1252.

    One line can hold both encodings. A rejected byte that Windows-1252 leaves undefined is
    refused.
    '''
    parts = []
    while True:
        try:
            parts.append(line.decode('utf-8'))
            return ''.join(parts)
        except UnicodeDecodeError as error:
            parts.append(line[:error.start].decode('utf-8'))
            try:
                parts.append(line[error.start:error.end].decode('cp1252'))
            except UnicodeDecodeError:
                raise Refused('raw line is neither UTF-8 nor Windows-1252') from None
            line = line[error.end:]


def decoded_lines(stream: BinaryIO) -> Iterator[str]:
    '''Each line of a binary stream as text, with its line ending kept.

    The UTF-8 byte order mark is dropped from the start of the first line only.
    '''
    first = True
    for line in stream:
        if first:
            line = line.removeprefix(BYTE_ORDER_MARK)
            first = False
        yield decoded_line(line)


@dataclass(frozen=True, slots=True)
class Form:
    '''The fields of one raw row that the reconciler reads, as delivered.'''

    trifd: str
    form_type: str
    state: str
    federal: str
    primary_naics: str
    other_naics: tuple[str, ...]
    parent_dnb: str
    standardized_parent: str
    standardized_foreign_parent: str | None


def read_forms(file: Path, year: int) -> Iterator[Form]:
    '''The forms of one raw file, after its header matches the layout of `year` exactly.

    Each row must have the header's width and give `year` as its reporting year. An empty
    line holds no form.
    '''
    layout = LAYOUT[str(year)]
    header, columns = layout['header'], layout['columns']
    position = {cell: index for index, cell in enumerate(header)}

    def at(name: str) -> int | None:
        return None if columns[name] is None else position[columns[name]]

    year_at, trifd_at, form_at, state_at = (at(name) for name in (
        'reporting_year', 'trifd', 'form_type', 'state'))
    federal_at, primary_at, dnb_at, parent_at, foreign_at = (at(name) for name in (
        'federal', 'primary_naics', 'parent_dnb', 'standardized_parent',
        'standardized_foreign_parent'))
    other_at = [position[cell] for cell in columns['other_naics']]
    with file.open('rb') as stream:
        rows = csv.reader(decoded_lines(stream))
        if next(rows, None) != header:
            raise Refused('raw header differs from the layout')
        for row in rows:
            if not row:
                continue
            if len(row) != len(header):
                raise Refused('raw row width differs from the header')
            if row[year_at].strip() != str(year):
                raise Refused('raw reporting year differs from its file')
            yield Form(
                trifd=row[trifd_at], form_type=row[form_at], state=row[state_at],
                federal=row[federal_at], primary_naics=row[primary_at],
                other_naics=tuple(row[index] for index in other_at), parent_dnb=row[dnb_at],
                standardized_parent=row[parent_at],
                standardized_foreign_parent=None if foreign_at is None else row[foreign_at])


# The facility-year reduction (spec "Facility-year table").

@dataclass(slots=True)
class FacilityYear:
    '''The forms of one TRIFD in one reporting year, reduced.'''

    forms: int = 0
    form_r: int = 0
    form_a: int = 0
    primary: set[str] = field(default_factory=set)
    other: set[str] = field(default_factory=set)
    parents: set[str] = field(default_factory=set)
    unnamed_form: bool = False
    foreign: set[str] = field(default_factory=set)
    federal_values: set[str] = field(default_factory=set)
    states: set[str] = field(default_factory=set)
    federal: bool = False
    dnb: set[str] = field(default_factory=set)

    @property
    def mixed_blank(self) -> bool:
        '''Some forms name a parent and others give a "no parent" string.'''
        return bool(self.parents) and self.unnamed_form


def add_form(item: FacilityYear, form: Form, values: dict[str, list[str]]) -> None:
    '''Fold one form into its facility-year.

    Primary and other NAICS codes and standardized names are stripped of surrounding
    whitespace. A blank code is no code. A blank or a registered "no parent" string is no name.
    The state and federal cells are kept exactly as delivered, a blank cell included. A D&B
    number is usable when, stripped, it is not blank and not a registered "no D&B number"
    string.
    '''
    item.forms += 1
    form_type = form.form_type.strip()
    if form_type in values['form_r']:
        item.form_r += 1
    elif form_type in values['form_a']:
        item.form_a += 1
    if code := form.primary_naics.strip():
        item.primary.add(code)
    item.other.update(code for value in form.other_naics if (code := value.strip()))
    name = form.standardized_parent.strip()
    if name and name not in values['no_parent']:
        item.parents.add(name)
    else:
        item.unnamed_form = True
    if form.standardized_foreign_parent is not None:
        foreign = form.standardized_foreign_parent.strip()
        if foreign and foreign not in values['no_parent']:
            item.foreign.add(foreign)
    item.federal_values.add(form.federal)
    if form.federal.strip() in values['federal_yes']:
        item.federal = True
    item.states.add(form.state)
    number = form.parent_dnb.strip()
    if number and number not in values['no_dnb']:
        item.dnb.add(number)


def classify(item: FacilityYear, nodes: dict[str, str]) -> tuple[str | None, str | None]:
    '''The node ID and the exclusion reason of one facility-year, None when it is eligible.

    The node ID is set whenever the facility-year has exactly one valid primary code.
    '''
    if not item.primary:
        return None, 'naics_missing'
    if len(item.primary) > 1:
        return None, 'naics_conflict'
    (code,) = item.primary
    node = nodes.get(code)
    if node is None:
        return None, 'naics_not_2022'
    if len(item.parents) > 1:
        return node, 'parent_conflict'
    if item.federal:
        return node, 'federal'
    return node, None


def headline_key(trifd: str, item: FacilityYear) -> str:
    '''`parent:<name>` for the one standardized parent name, else `facility:<TRIFD>`.'''
    if len(item.parents) == 1:
        (name,) = item.parents
        return 'parent:' + name
    return 'facility:' + trifd


def dnb_key(trifd: str, item: FacilityYear) -> str:
    '''`dnb:<number>` when the forms give exactly one usable D&B number, else the facility.'''
    if len(item.dnb) == 1:
        (number,) = item.dnb
        return 'dnb:' + number
    return 'facility:' + trifd


def excluded_owners(trifd: str, item: FacilityYear) -> list[str]:
    '''The owner keys that a facility-year excluded for a partial reason belongs to.

    It belongs to each standardized parent name it lists, and to `facility:<TRIFD>` when it
    lists none. The exclusion reason does not change who it belongs to.
    '''
    if item.parents:
        return ['parent:' + name for name in item.parents]
    return ['facility:' + trifd]


# The counts (spec "Parent-link target (O7)" and "Parent industry table (O8)").

Presence = dict[str, dict[int, set[str]]]


@dataclass
class Counts:
    '''N, n(a), J(a,b), the yearly j, the multi-industry owners and the owners by year.'''

    owners: int
    n: Counter
    j: Counter
    j_by_year: dict[int, Counter]
    multi: Counter
    by_year: Counter


def count(presence: Presence) -> Counts:
    '''Count each owner at most once in n(a), in J(a,b) and in each year's j(a,b).

    `presence` maps each owner key to S(o,t), its set of nodes in each year t. n(a) counts the
    owners with a in some S(o,t). J(a,b) counts the owners with a and b, a != b, in one
    S(o,t). A multi-industry owner of a has a and another node in one S(o,t).
    '''
    n, j, multi, by_year = Counter(), Counter(), Counter(), Counter()
    j_by_year: dict[int, Counter] = defaultdict(Counter)
    for years in presence.values():
        n.update(set().union(*years.values()))
        by_year.update(years.keys())
        pairs, several = set(), set()
        for year, nodes in years.items():
            if len(nodes) > 1:
                year_pairs = {(a, b) for a in nodes for b in nodes if a != b}
                j_by_year[year].update(year_pairs)
                pairs |= year_pairs
                several |= nodes
        j.update(pairs)
        multi.update(several)
    return Counts(len(presence), n, j, j_by_year, multi, by_year)


def nested() -> defaultdict:
    return defaultdict(lambda: defaultdict(set))


@dataclass
class Recomputed:
    '''The bundle's tables and report counts, recomputed from the raw files and the nodes.'''

    facility_years: list[tuple]
    marginals: list[tuple]
    support: list[tuple]
    targets: dict[tuple[str, str], tuple]
    parent_industries: list[tuple]
    report: dict


def reduce_files(files: dict[int, Path]) -> dict[tuple[int, str], FacilityYear]:
    '''The facility-years of the raw files, keyed by reporting year and TRIFD as delivered.'''
    facility_years: dict[tuple[int, str], FacilityYear] = {}
    for year, file in sorted(files.items()):
        values = LAYOUT[str(year)]['values']
        for form in read_forms(file, year):
            item = facility_years.get((year, form.trifd))
            if item is None:
                item = facility_years[(year, form.trifd)] = FacilityYear()
            add_form(item, form, values)
    return facility_years


def recompute(files: dict[int, Path], nodes: dict[str, str], processed_as_of: str) -> Recomputed:
    '''Recompute every compared table and report count from the raw files.'''
    facility_years = reduce_files(files)
    headline, by_dnb, with_federal = nested(), nested(), nested()
    excluded: set[tuple[str, int]] = set()
    facilities: dict[str, set[str]] = defaultdict(set)
    facility_year_counts = Counter()
    industries: dict[tuple[str, str], dict[int, set[str]]] = nested()
    keys_by_trifd: dict[str, set[str]] = defaultdict(set)
    reasons = {year: Counter() for year in files}
    by_year = {year: Counter() for year in files}
    table = []
    for year, trifd in sorted(facility_years):
        item = facility_years[(year, trifd)]
        node, reason = classify(item, nodes)
        owner = None
        if reason is None:
            owner = headline_key(trifd, item)
            headline[owner][year].add(node)
            by_dnb[dnb_key(trifd, item)][year].add(node)
            with_federal[owner][year].add(node)
            facilities[node].add(trifd)
            facility_year_counts[node] += 1
            keys_by_trifd[trifd].add(owner)
            if item.parents:
                (name,) = item.parents
                industries[(name, node)][year].add(trifd)
        elif reason == 'federal':
            with_federal[headline_key(trifd, item)][year].add(node)
        elif reason in PARTIAL_REASONS:
            excluded.update((key, year) for key in excluded_owners(trifd, item))
        reasons[year][reason or 'eligible'] += 1
        by_year[year]['rows'] += item.forms
        by_year[year]['form_r'] += item.form_r
        by_year[year]['form_a'] += item.form_a
        by_year[year]['facility_years'] += 1
        by_year[year]['mixed_blank'] += item.mixed_blank
        by_year[year]['with_foreign_parent'] += bool(item.foreign)
        by_year[year]['with_secondary_codes'] += bool(item.other)
        table.append((
            year, trifd, item.forms, item.form_r, item.form_a, tuple(sorted(item.primary)),
            tuple(sorted(item.other)), node, tuple(sorted(item.parents)),
            tuple(sorted(item.foreign)), tuple(sorted(item.federal_values)),
            tuple(sorted(item.states)), item.mixed_blank, owner, reason))

    owners, dnb, federal = count(headline), count(by_dnb), count(with_federal)
    parent_owners, partial, partial_owners = Counter(), Counter(), set()
    for owner, years in headline.items():
        if owner.startswith('parent:'):
            parent_owners.update(set().union(*years.values()))
        seen = set().union(*(nodes for year, nodes in years.items() if (owner, year) in excluded))
        if seen:
            partial.update(seen)
            partial_owners.add(owner)
    marginals = [
        (a, owners.n[a], parent_owners[a], owners.multi[a], len(facilities[a]),
         facility_year_counts[a], dnb.n[a], federal.n[a], partial[a])
        for a in sorted(owners.n)
    ]
    support = [
        (a, b, owners.j[(a, b)], *(owners.j_by_year[year][(a, b)] for year in WINDOW),
         dnb.j[(a, b)], federal.j[(a, b)])
        for a, b in sorted(owners.j)
    ]
    universe = UNIVERSE.format(date=processed_as_of)
    targets = {}
    for (a, b), shared in owners.j.items():
        flags = [SIZE_GATE]
        if dnb.j[(a, b)] != shared:
            flags.append(DNB_LABEL)
        if federal.j[(a, b)] != shared:
            flags.append(FEDERAL_LABEL)
        targets[(a, b)] = (
            'epa_tri', 'tri_parent_links', UNIT_TYPE, UNIT_TYPE, 'owner_share',
            shared / owners.n[a], None, 'none', shared, float(shared), 'tri_basic_ry2022_2024',
            'naics=2022', universe, tuple(sorted(flags)))
    parent_industries = [
        (name, node, len(set().union(*years.values())), sum(map(len, years.values())),
         *(len(years.get(year, ())) for year in WINDOW))
        for (name, node), years in sorted(industries.items())
    ]
    report = {
        'n_owners': {'headline': owners.owners, 'dnb': dnb.owners, 'federal': federal.owners},
        'owners_by_year': {
            str(year): {'headline': owners.by_year[year], 'dnb': dnb.by_year[year],
                        'federal': federal.by_year[year]}
            for year in sorted(files)
        },
        'rows_by_form_type': {
            str(year): {'form_a': by_year[year]['form_a'], 'form_r': by_year[year]['form_r']}
            for year in sorted(files)
        },
        'facility_years_by_reason': {
            str(year): {reason: reasons[year][reason] for reason in ('eligible', *REASONS)}
            for year in sorted(files)
        },
        'year_counts': {
            str(year): {name: by_year[year][name] for name in YEAR_COUNTS}
            for year in sorted(files)
        },
        'sensitivity_cells': {'cells_only_dnb': len(dnb.j.keys() - owners.j.keys()),
                              'cells_only_federal': len(federal.j.keys() - owners.j.keys())},
        'owner_key_changes': sum(len(keys) > 1 for keys in keys_by_trifd.values()),
        'partial_owners': len(partial_owners),
    }
    return Recomputed(table, marginals, support, targets, parent_industries, report)


# The comparison.

MISSING = object()


def same(first: object, second: object) -> bool:
    '''Exact equality that also requires equal types, so True is not 1 and 1 is not 1.0.'''
    if type(first) is not type(second):
        return False
    if isinstance(first, tuple):
        return len(first) == len(second) and all(map(same, first, second))
    return first == second


def plain(value: object) -> object:
    return tuple(value) if isinstance(value, list) else value


def table_rows(frame: pl.DataFrame, columns: Iterable[str]) -> list[tuple] | None:
    '''The named columns of each row as tuples, lists as tuples; None if a column is missing.'''
    columns = list(columns)
    if not set(columns) <= set(frame.columns):
        return None
    return [tuple(map(plain, row)) for row in frame.select(columns).iter_rows()]


def ordered_differing(expected: list[tuple], actual: list[tuple] | None) -> int:
    '''The positions at which two ordered row lists differ, a missing row included.'''
    if actual is None:
        return max(len(expected), 1)
    return sum(not same(first, second)
               for first, second in zip_longest(expected, actual, fillvalue=MISSING))


def target_rows(targets: dict) -> list[tuple]:
    '''The recomputed target rows in `TARGET_SCHEMA` column order, sorted by `(unit_a, unit_b)`.

    The shared writer sorts by every column except `value`, `se`, the counts and `flags`. All of
    them except `unit_a` and `unit_b` are constants here.
    '''
    rows = []
    for (a, b), values in sorted(targets.items()):
        row = dict(zip(TARGET_VALUES, values, strict=True), unit_a=a, unit_b=b)
        rows.append(tuple(row[name] for name in TARGET_SCHEMA))
    return rows


def target_differing(expected: dict, actual: list[tuple] | None) -> int:
    '''The positions at which the target rows differ, plus repeated keys on the bundle side.'''
    differing = ordered_differing(target_rows(expected), actual)
    if actual is None:
        return differing
    keys = [tuple(row[index] for index in TARGET_KEY) for row in actual]
    return differing + len(keys) - len(set(keys))


def schema_equal(frame: pl.DataFrame, schema: dict[str, str]) -> bool:
    '''Whether the frame has exactly the spec's columns, in order, with the spec's types.'''
    return [(name, str(dtype)) for name, dtype in frame.schema.items()] == list(schema.items())


def canonical(value: object) -> str:
    '''A JSON text that tells true from 1 and orders keys, for exact report comparison.'''
    return json.dumps(value, sort_keys=True)


def report_years(report: dict, pick: Callable[[dict], object]) -> dict:
    '''`pick` applied to each year's entry of `report['by_year']`.'''
    by_year = report.get('by_year')
    if not isinstance(by_year, dict):
        return {}
    return {year: pick(entry) if isinstance(entry, dict) else None
            for year, entry in by_year.items()}


def compare(expected: Recomputed, directory: Path, report: dict) -> dict:
    '''Each check's equality and each table's differing rows, against the bundle.'''
    frames = {name: pl.read_parquet(directory / file) for name, file in TABLE_FILES.items()}
    years = frames['facility_years']
    facility_expected = [tuple(row[FACILITY_COLUMNS.index(name)] for name in REDUCTION_COLUMNS)
                         for row in expected.facility_years]
    eligibility_expected = [
        tuple(row[FACILITY_COLUMNS.index(name)] for name in ELIGIBILITY_COLUMNS)
        for row in expected.facility_years]
    differing = {
        'facility_years': ordered_differing(facility_expected,
                                            table_rows(years, REDUCTION_COLUMNS)),
        'eligibility': ordered_differing(eligibility_expected,
                                         table_rows(years, ELIGIBILITY_COLUMNS)),
        'marginals': ordered_differing(expected.marginals,
                                       table_rows(frames['marginals'], MARGINAL_SCHEMA)),
        'support': ordered_differing(expected.support,
                                     table_rows(frames['support'], SUPPORT_SCHEMA)),
        'parent_industries': ordered_differing(
            expected.parent_industries, table_rows(frames['parent_industries'],
                                                   INDUSTRY_SCHEMA)),
        'targets': target_differing(expected.targets,
                                    table_rows(frames['targets'], TARGET_SCHEMA)),
    }
    schemas = {
        'facility_years': FACILITY_SCHEMA, 'marginals': MARGINAL_SCHEMA,
        'support': SUPPORT_SCHEMA, 'parent_industries': INDUSTRY_SCHEMA,
        'targets': TARGET_SCHEMA,
    }
    checks = {name: count == 0 for name, count in differing.items()}
    for name, schema in schemas.items():
        checks[name] = checks[name] and schema_equal(frames[name], schema)
    ours = expected.report
    recorded = {
        'n_owners': report.get('n_owners'),
        'owners_by_year': report.get('owners_by_year'),
        'rows_by_form_type': report_years(report, lambda entry: entry.get('rows_by_form_type')),
        'facility_years_by_reason': report_years(
            report, lambda entry: entry.get('facility_years_by_reason')),
        'year_counts': report_years(
            report, lambda entry: {name: entry.get(name) for name in YEAR_COUNTS}),
        'sensitivity_cells': {name: report.get(name) for name in ours['sensitivity_cells']},
        'owner_key_changes': report.get('owner_key_changes'),
        'partial_owners': report.get('partial_owners'),
    }
    for name, value in recorded.items():
        checks[name] = canonical(value) == canonical(ours[name])
    result = {f'{name}_equal': equal for name, equal in checks.items()}
    result.update({f'{name}_differing': count for name, count in differing.items()})
    result['rows'] = {'facility_years': len(expected.facility_years),
                      'marginals': len(expected.marginals), 'support': len(expected.support),
                      'targets': len(expected.targets),
                      'parent_industries': len(expected.parent_industries)}
    result['n_owners'] = ours['n_owners']
    result['equal'] = all(checks.values())
    result['refused'] = False
    return result


def reconcile(data_dir: Path, run_id: str, pin: str) -> dict:
    '''Authenticate the bundle and its inputs, recompute, and compare.'''
    directory = open_bundle(data_dir, run_id, pin)
    inputs = read_json(directory / 'inputs.json')
    report = read_json(directory / 'report.json')
    processed_as_of, files = select_raw(data_dir, inputs)
    nodes = select_nodes(data_dir, inputs)
    return compare(recompute(files, nodes, processed_as_of), directory, report)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    result.add_argument('--data-dir', type=Path, required=True)
    result.add_argument('--run', required=True)
    result.add_argument('--outputs-sha256', required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        result = reconcile(arguments.data_dir, arguments.run, arguments.outputs_sha256)
    except Refused as refusal:
        result = {'equal': False, 'refused': True, 'reason': str(refusal)}
    except Exception:
        # A refusal never prints exception text, which can hold row content.
        result = {'equal': False, 'refused': True, 'reason': 'unexpected'}
    print(json.dumps(result, sort_keys=True))
    if result['refused']:
        return 2
    return 0 if result['equal'] else 1


if __name__ == '__main__':
    sys.exit(main())
