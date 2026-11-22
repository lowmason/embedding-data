'''Synthetic fixtures for the Stage 14 vendor-link tests.

Nothing here is real data: the file names, URLs, ZIP members and the key are made up, and
the fake USAspending and SAM.gov servers answer from memory. Fixture results show software
readiness only.
'''

import codecs
import csv
import io
import json
import logging
import struct
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from embedding_data import sam_access, sam_raw, usaspending_raw, vendor_link_layouts

FAKE_KEY = 'FAKEKEYfake0123456789ABCDEFghij'
# FAKE_KEY plus punctuation, not a second key. Its five spellings (plain, quote, quote_plus,
# JSON, HTML) are distinct bytes, and the HTML spelling is the longest.
PUNCTUATED_KEY = FAKE_KEY + ' &"'
NAME = 'FY2025_Subawards_2026-11-20_H10M00S00.zip'
URL = f'https://files.test.example/generated_downloads/{NAME}'
MONTH = '2026-11'
EXTRACT_NAME = 'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261102.ZIP'
EXTRACT_TARGET = f'https://files.test.example/extracts/{EXTRACT_NAME}'
# The modules' real factories, taken at import time, before `no_live_sam` replaces them.
REAL_MAKE_CLIENT = usaspending_raw.make_client
REAL_SAM_MAKE_CLIENT = sam_access.make_client


@pytest.fixture(autouse=True)
def no_live_sam(monkeypatch):
    '''Make a missed patch fail the test instead of spending a live request.'''
    monkeypatch.delenv('SAM_API_KEY', raising=False)

    def refuse(*args, **kwargs):
        raise AssertionError('live client')

    monkeypatch.setattr(usaspending_raw, 'make_client', refuse)
    monkeypatch.setattr(sam_access, 'make_client', refuse)


def zip_bytes(members: dict[str, bytes]) -> bytes:
    '''A deterministic ZIP archive: fixed member dates, deflate compression.'''
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name, content in members.items():
            archive.writestr(zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)), content,
                             compress_type=zipfile.ZIP_DEFLATED)
    return buffer.getvalue()


def without_members(archive: bytes) -> bytes:
    '''`archive` with its end record replaced by one that lists no member.

    The body still starts with a local file header, so the ZIP signature check accepts it, and
    Python 3.14's `zipfile.is_zipfile` accepts it too. `zipfile.ZipFile` reads no member from it.
    An empty ZIP from `zipfile` starts with the end record, which fails the signature check.
    '''
    end = archive.rindex(b'PK\x05\x06')
    return archive[:end] + struct.pack('<4s4H2LH', b'PK\x05\x06', 0, 0, 0, 0, 0, 0, 0)


def sample_zip() -> bytes:
    return zip_bytes({'FY2025_subawards_1.csv': b'column_a,column_b\r\n1,2\r\n'})


class FakeUsaspending:
    '''A scripted USAspending API for `httpx.MockTransport`.

    The POST names the file. Each status poll answers the next entry of `statuses`, and the
    last entry repeats. The file URL answers the ZIP body, or a redirect to `redirect_to`.
    Every request is recorded.
    '''

    def __init__(self, *, statuses=('finished',), file_name=NAME, file_url=URL,
                 post_file_url=None, body=None, headers=None, redirect_to=None):
        self.statuses = statuses
        self.file_name = file_name
        self.file_url = file_url
        self.post_file_url = post_file_url
        self.body = sample_zip() if body is None else body
        self.headers = {'Content-Length': str(len(self.body))} if headers is None else headers
        self.redirect_to = redirect_to
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        path = request.url.path
        if request.method == 'POST' and path == usaspending_raw.REQUEST_PATH:
            return httpx.Response(200, json={
                'status_url': f'{usaspending_raw.API_ROOT}{usaspending_raw.STATUS_PATH}',
                'file_name': self.file_name, 'file_url': self.post_file_url})
        if request.method == 'GET' and path == usaspending_raw.STATUS_PATH:
            index = min(len(self.polls) - 1, len(self.statuses) - 1)
            answer = {'status': self.statuses[index], 'file_name': self.file_name,
                      'message': None}
            if self.file_url is not None:
                answer['file_url'] = self.file_url
            return httpx.Response(200, json=answer)
        if request.method == 'GET' and str(request.url) == self.file_url:
            if self.redirect_to is not None:
                return httpx.Response(302, headers={'Location': self.redirect_to})
            return self.zip_response()
        if request.method == 'GET' and str(request.url) == self.redirect_to:
            return self.zip_response()
        return httpx.Response(404)

    def zip_response(self):
        # stream= keeps `num_bytes_downloaded` counting; a content= body is preloaded.
        return httpx.Response(200, headers=self.headers, stream=httpx.ByteStream(self.body))

    @property
    def posts(self):
        return [request for request in self.requests if request.method == 'POST']

    @property
    def polls(self):
        return [request for request in self.requests
                if request.method == 'GET' and request.url.path == usaspending_raw.STATUS_PATH]

    @property
    def downloads(self):
        return [request for request in self.requests
                if request.method == 'GET' and request.url.path != usaspending_raw.STATUS_PATH]

    def posted_body(self):
        return json.loads(self.posts[0].content)


def install_usaspending(monkeypatch, server):
    '''Route `usaspending_raw` through `server` and record sleeps instead of waiting.

    Returns the list of recorded sleep durations.
    '''
    slept = []
    monkeypatch.setattr(usaspending_raw, 'make_client',
                        lambda: REAL_MAKE_CLIENT(httpx.MockTransport(server)))
    monkeypatch.setattr(usaspending_raw, 'sleep', slept.append)
    return slept


def extract_name(month=MONTH, day='02'):
    return f'SAM_PUBLIC_UTF-8_MONTHLY_V2_{month.replace("-", "")}{day}.ZIP'


# The real extract's member name ends in 32 hex characters, which the invented test layout's
# member pattern does not allow.
COMMITTED_MEMBER_HEX = '0123456789abcdef' * 2
EXTRACT_FRAMING = (b'BOF PUBLIC V2 00000000 20261102 0000000 0000000\r\n'
                   b'EOF PUBLIC V2 00000000 20261102 0000000 0000000')


def extract_member_name(month=MONTH, *, committed=False) -> str:
    '''The member name of the extract of `month`: the one that the invented test layout
    accepts, or with `committed` the one that the committed layout accepts.'''
    stem = extract_name(month).removesuffix('.ZIP')
    return f'{stem}_{COMMITTED_MEMBER_HEX}.dat' if committed else f'{stem}.dat'


def sample_extract(month=MONTH, *, committed=False) -> bytes:
    '''A synthetic extract ZIP: one member with framing lines and no entity record.'''
    return zip_bytes({extract_member_name(month, committed=committed): EXTRACT_FRAMING})


def extract_answer(body=None, *, name=EXTRACT_NAME, headers=None):
    '''A 200 answer with the ZIP body, its Content-Length and a Content-Disposition name.'''
    body = sample_extract() if body is None else body
    if headers is None:
        headers = {'Content-Length': str(len(body))}
        if name is not None:
            headers['Content-Disposition'] = f'attachment; filename="{name}"'
    return 200, headers, body


def redirect_answer(location=EXTRACT_TARGET, status=302, headers=None):
    headers = ({} if location is None else {'Location': location}) | (headers or {})
    return status, headers, b''


class FakeSam:
    '''A scripted SAM.gov Entity Extracts API for `httpx.MockTransport`.

    The n-th request gets the n-th answer, a `(status, headers, body)` tuple, and a request
    past the script gets 404. Every request is recorded, with the logging threshold that
    was in force while it was sent.
    '''

    def __init__(self, *answers):
        self.answers = answers
        self.requests = []
        self.logging_thresholds = []

    def __call__(self, request):
        self.requests.append(request)
        self.logging_thresholds.append(logging.root.manager.disable)
        if len(self.requests) > len(self.answers):
            return httpx.Response(404)
        status, headers, body = self.answers[len(self.requests) - 1]
        # stream= keeps `num_bytes_downloaded` counting; a content= body is preloaded.
        return httpx.Response(status, headers=headers, stream=httpx.ByteStream(body))


def install_sam(monkeypatch, handler):
    '''Route `sam_access` through `handler`, a `FakeSam` or any MockTransport handler.'''
    monkeypatch.setattr(sam_access, 'make_client',
                        lambda: REAL_SAM_MAKE_CLIENT(httpx.MockTransport(handler)))
    return handler


def seed_codes_bundle(data_dir, directory):
    '''Build a real Stage 4 codes bundle from the committed Stage 10 fixtures.

    It seeds the raw summary releases and the Stage 2 table, imports the committed exact
    public Stage 4 originals into `directory`, and builds the bundle. It skips the Stage 10
    index import and Stage 3 expectations. Returns the run ID and the detached pin.
    '''
    # Imported here so that every vendor-link test module does not load the Stage 10 chain.
    import ita_establishment_fixtures
    import ita_fixtures

    from embedding_data import code_build, ita_summary, manifest

    for year, rows in ita_establishment_fixtures.golden_releases().items():
        ita_fixtures.write_release(data_dir, year, ita_fixtures.year_file(year, rows))
    ita_summary.build_summary_table(data_dir)
    ita_establishment_fixtures.import_stage4_originals(data_dir, directory)
    bundle = code_build.build(data_dir, ita_establishment_fixtures.CODES_RUN)
    return (ita_establishment_fixtures.CODES_RUN,
            manifest.sha256_file(bundle / 'outputs.json'))


# The invented test registries. The 30 header cells imitate USAspending's column names. The
# free-text `description` cell comes before the subcontractor columns, so a value that splits
# wrongly shifts them. FY2026 has no subaward NAICS column, so its `subaward_naics` is unmapped.
_SUBAWARD_HEADER = (
    'prime_award_unique_key', 'prime_award_piid', 'prime_award_amount', 'prime_awardee_uei',
    'prime_awardee_name', 'prime_awardee_parent_uei', 'prime_awardee_parent_name',
    'prime_award_naics_code', 'prime_award_naics_description', 'subaward_type',
    'subaward_report_id', 'subaward_number', 'description', 'subawardee_uei',
    'subawardee_name', 'subawardee_parent_uei', 'subawardee_parent_name', 'subaward_amount',
    'subaward_action_date', 'subaward_action_date_fiscal_year', 'subaward_naics',
    'subawardee_business_types', 'subaward_last_modified_date', 'prime_award_base_action_date',
    'prime_award_awarding_agency_name', 'prime_award_funding_agency_name',
    'prime_award_project_title', 'usaspending_permalink', 'subaward_fsrs_report_id',
    'subaward_fsrs_report_year')
_SUBAWARD_COLUMNS = {
    'prime_uei': 'prime_awardee_uei', 'sub_uei': 'subawardee_uei',
    'action_date': 'subaward_action_date', 'amount': 'subaward_amount',
    'subaward_type': 'subaward_type', 'prime_parent_uei': 'prime_awardee_parent_uei',
    'sub_parent_uei': 'subawardee_parent_uei', 'report_id': 'subaward_report_id',
    'subaward_naics': 'subaward_naics', 'prime_naics': 'prime_award_naics_code'}


def _subaward_year(year: int) -> dict:
    header = list(_SUBAWARD_HEADER)
    columns = dict(_SUBAWARD_COLUMNS)
    if year == 2026:
        header[header.index('subaward_naics')] = 'subaward_fsrs_report_month'
        columns['subaward_naics'] = None
    return {'member_pattern': r'Contracts_Subawards_[0-9]+\.csv', 'header': header,
            'date_format': '%Y-%m-%d', 'columns': columns}


TEST_SUBAWARD_LAYOUTS = vendor_link_layouts.parse_subaward_layouts({
    'version': vendor_link_layouts.SUBAWARD_VERSION,
    'years': {str(year): _subaward_year(year) for year in usaspending_raw.WINDOW}})
# Restricted positions 10 to 16 sit right after `last_update_date` (9) and right before
# `primary_naics` (17), so a read one position off reaches a restricted field.
TEST_EXTRACT_LAYOUT = vendor_link_layouts.parse_extract_layout({
    'version': vendor_link_layouts.EXTRACT_VERSION,
    'layout': 'Fixture extract layout v1',
    'member_pattern': r'SAM_PUBLIC_UTF-8_MONTHLY_V2_[0-9]{8}\.dat',
    'encoding': 'utf-8',
    'delimiter': '|',
    'field_count': 40,
    'bof_prefix': 'BOF FIXTURE V2 00000000 ',
    'eof_prefix': 'EOF FIXTURE V2 00000000 ',
    'record_end': '!end',
    'date_format': '%Y%m%d',
    'positions': {'uei': 2, 'registration_status': 5, 'last_update_date': 9,
                  'primary_naics': 17, 'naics_code_string': 27, 'evs_source': 33},
    'evs_dnb': ['D&B'],
    'restricted_positions': [10, 11, 12, 13, 14, 15, 16],
})
# Stands in for a D&B Open Data value (a name or an address). It must reach no output.
DNB_SENTINEL = 'DNB-SENTINEL-NAME'


def subaward_record(layout: vendor_link_layouts.SubawardLayout, **fields: str) -> list[str]:
    '''A full record in header order, every other cell empty.

    A keyword names a logical field or, after the prefix `cell_`, a raw header cell.
    '''
    record = dict.fromkeys(layout.header, '')
    for name, value in fields.items():
        cell = name.removeprefix('cell_') if name.startswith('cell_') else layout.columns[name]
        if cell not in record:
            raise ValueError(f'{name} names no header cell')
        record[cell] = value
    return list(record.values())


def write_subaward_zip(file: Path, layout: vendor_link_layouts.SubawardLayout,
                       members: dict[str, list[list[str]]], *, bom: bool = False,
                       extra: dict[str, bytes] | None = None) -> None:
    '''Write a subaward ZIP. Each CSV member holds the layout's header, then its records.

    `csv.writer` quotes a value that holds a comma, a quote or a line break, and ends each
    line with CRLF. `bom` starts every CSV member with a UTF-8 BOM. `extra` adds members with
    exact bytes after the CSV members.
    '''
    contents = {}
    for name, records in members.items():
        text = io.StringIO()
        writer = csv.writer(text, lineterminator='\r\n')
        writer.writerow(layout.header)
        writer.writerows(records)
        contents[name] = (codecs.BOM_UTF8 if bom else b'') + text.getvalue().encode('utf-8')
    file.write_bytes(zip_bytes(contents | (extra or {})))


def extract_line(layout: vendor_link_layouts.ExtractLayout, **fields: str) -> str:
    '''A data line: each keyword at its field's position, `DNB_SENTINEL` at each restricted
    position, the record end last, and every other position empty.'''
    values = [''] * layout.field_count
    for position in layout.restricted_positions:
        values[position - 1] = DNB_SENTINEL
    if layout.record_end is not None:
        values[-1] = layout.record_end
    for name, value in fields.items():
        values[layout.positions[name] - 1] = value
    return layout.delimiter.join(values)


def write_extract_zip(file: Path, layout: vendor_link_layouts.ExtractLayout, lines: list[str],
                      *, member: str, bof: str | None = None, eof: str | None = None) -> None:
    '''Write an extract ZIP with one member: the BOF line, `lines` and the EOF line.

    Lines end with CRLF and the EOF line has no line end, as in the SAM.gov sample file. The
    default framing lines are the layout's prefixes followed by a date and two counts.
    '''
    bof = f'{layout.bof_prefix}20261102 0000000 0000000' if bof is None else bof
    eof = f'{layout.eof_prefix}20261102 0000000 0000000' if eof is None else eof
    text = '\r\n'.join([bof, *lines, eof])
    file.write_bytes(zip_bytes({member: text.encode(layout.encoding)}))


def seed_raw(data_dir: Path, directory: Path, subawards: dict[int, dict[str, list[list[str]]]],
             extract_lines: list[str], *, snapshot: date, month: str, subaward_layouts,
             extract_layout, extract_member: str) -> None:
    '''Write a subaward ZIP for each year of `subawards` and one extract ZIP in `directory`,
    and import them into `data_dir` under `snapshot` and `month`.

    Each year's ZIP is `FY<year>_Contracts_Subawards_fixture.zip` and holds its members, each
    with that year's layout header. The extract is `extract_name(month)` with one member. The
    import checks that member against `extract_layout`, the layout that the extract is for.
    '''
    directory.mkdir(parents=True, exist_ok=True)
    for year, members in subawards.items():
        file = directory / f'FY{year}_Contracts_Subawards_fixture.zip'
        write_subaward_zip(file, subaward_layouts[year], members)
        usaspending_raw.import_file(data_dir, year, file, snapshot=snapshot)
    extract = directory / extract_name(month)
    write_extract_zip(extract, extract_layout, extract_lines, member=extract_member)
    with patch.object(vendor_link_layouts, 'load_extract_layout', lambda: extract_layout):
        sam_raw.import_file(data_dir, extract, month=month)


def subprocess_modules(name: str, *, prefix: str | None = 'embedding_data') -> set[str]:
    '''Import `name` in a fresh `sys.executable` process and return the names in its
    `sys.modules`: only those that start with `prefix`, or all of them when it is None.'''
    code = ('import importlib, json, sys; importlib.import_module(sys.argv[1]); '
            'print(json.dumps(sorted(sys.modules)))')
    result = subprocess.run([sys.executable, '-c', code, name], capture_output=True,
                            text=True, check=True)
    loaded = set(json.loads(result.stdout))
    return loaded if prefix is None else {module for module in loaded
                                          if module.startswith(prefix)}


def module_file(module: str) -> str:
    '''The project-relative source file of an `embedding_data` module: the package itself is
    `src/embedding_data/__init__.py` and `embedding_data.x` is `src/embedding_data/x.py`.'''
    if module == 'embedding_data':
        return 'src/embedding_data/__init__.py'
    return 'src/' + module.replace('.', '/') + '.py'


# ---- the V12 fixture chain: raw files in the production layouts to replay-equal bundles

V12_SNAPSHOT = date(2026, 11, 20)
V12_MONTH = '2026-11'
V12_RUNS = ('v12_first', 'v12_second')
# Member names that match the committed registries' patterns. Each year's ZIP holds one.
V12_MEMBER = 'All_Contracts_Subawards_2026-11-20_H10M00S00_1.csv'
V12_EXTRACT_MEMBER = f'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261102_{"0123456789abcdef" * 2}.dat'
# Made-up UEIs. The industry of each firm is in `_V12_FIRMS`.
V12_PRIME_A = 'V12PRIMEA001'
V12_PRIME_B = 'V12PRIMEB002'
V12_PRIME_C = 'V12PRIMEC003'
V12_PRIME_D = 'V12PRIMED004'
V12_PRIME_OLD = 'V12PRIMEOLD5'
V12_SELF = 'V12SELFLINK6'
V12_SUB_A = 'V12SUBAWA001'
V12_SUB_B = 'V12SUBAWB002'
V12_SUB_C = 'V12SUBAWC003'
V12_SUB_EDGE = 'V12SUBEDGE04'
V12_NOT_IN_SAM = 'V12NOTSAM005'
V12_NO_CODE = 'V12NOCODE006'
V12_CONFLICT = 'V12CONFLT007'
V12_NOT_2022 = 'V12NOTN22008'
V12_BAD_CODE = 'V12BADCODE09'
V12_BLANK_DATE = 'V12BLANKDT01'
V12_BAD_DATE = 'V12BADDATE02'
V12_EVS_DNB = 'V12EVSDNB003'
V12_TWO_ROWS = 'V12TWOROWS04'
V12_MIXED = 'V12MIXEDBL05'
V12_PADDED = 'V12PADDED006'
V12_PRIME_E = 'V12PRIMEE007'
V12_SUB_D1 = 'V12SUBAWD001'
V12_SUB_D2 = 'V12SUBAWE002'
_V12_GROUP_X = 'V12GROUPX001'
_V12_GROUP_Y = 'V12GROUPY002'
_V12_GROUP_Z = 'V12GROUPZ003'
_V12_UPDATE = '20250115'
# Name and address cells of the subaward files. The reader keeps none of them.
_V12_TEXT_CELLS = ('prime_awardee_name', 'prime_awardee_parent_name', 'subawardee_name',
                   'subawardee_parent_name', 'prime_awardee_address_line_1',
                   'subawardee_address_line_1')
_V12_LOWER_GROUP = _V12_GROUP_X.lower()
# The extract rows as `(UEI, primary code, last update date)`, and optionally a dict of other
# fields of the line (`dnb_evs` stands for the layout's own D&B EVS value). Industries: prime A
# 541511, B 236220, C 336411, D 238220, E 722511; the old record, the self-linking firm and
# subcontractors A and B 541512; subcontractor C 541511; the edge firm 336411; subcontractors
# D1 and D2 722513. The old record was last updated the day before the D&B cutoff and the edge
# firm on the cutoff day. The conflicting firm has two rows. 517311 is a NAICS 2017 code and
# 54151A is malformed. The not-in-SAM firm has no row. Three firms are D&B-era records for the
# other reasons: no last update date, a last update date that is no date, and a D&B EVS source
# with a recent date. One firm has two rows that agree on the code (the second one an expired
# registration), and one has a blank row and a coded row. The padded firm has one row.
_V12_FIRMS = (
    (V12_PRIME_A, '541511', _V12_UPDATE),
    (V12_PRIME_B, '236220', _V12_UPDATE),
    (V12_PRIME_C, '336411', _V12_UPDATE),
    (V12_PRIME_D, '238220', _V12_UPDATE),
    (V12_PRIME_OLD, '541512', '20220403'),
    (V12_SELF, '541512', _V12_UPDATE),
    (V12_SUB_A, '541512', _V12_UPDATE),
    (V12_SUB_B, '541512', _V12_UPDATE),
    (V12_SUB_C, '541511', _V12_UPDATE),
    (V12_SUB_EDGE, '336411', '20220404'),
    (V12_NO_CODE, '', _V12_UPDATE),
    (V12_CONFLICT, '541511', _V12_UPDATE),
    (V12_CONFLICT, '541330', _V12_UPDATE),
    (V12_NOT_2022, '517311', _V12_UPDATE),
    (V12_BAD_CODE, '54151A', _V12_UPDATE),
    (V12_BLANK_DATE, '541511', ''),
    (V12_BAD_DATE, '541511', '20251332'),
    (V12_EVS_DNB, '541511', _V12_UPDATE, {'dnb_evs': True}),
    (V12_TWO_ROWS, '541512', _V12_UPDATE),
    (V12_TWO_ROWS, '541512', _V12_UPDATE, {'registration_status': 'E'}),
    (V12_MIXED, '', _V12_UPDATE),
    (V12_MIXED, '541511', _V12_UPDATE),
    (V12_PADDED, '541511', _V12_UPDATE),
    (V12_PRIME_E, '722511', _V12_UPDATE),
    (V12_SUB_D1, '722513', _V12_UPDATE),
    (V12_SUB_D2, '722513', _V12_UPDATE),
)


def _v12_report(prime, sub, action, amount, **fields):
    return dict(prime_uei=prime, sub_uei=sub, action_date=action, amount=amount, **fields)


# The reports by file year: 36 rows, 30 of them usable. Every amount differs, so the one row
# that `copies=2` writes twice is the only duplicate. `v12_inputs` adds a report ID to each row.
_V12_REPORTS = {
    2024: [
        # 2023-10-01 is the first day of fiscal year 2024.
        _v12_report(V12_PRIME_A, V12_SUB_A, '2023-10-01', '1000.00'),
        _v12_report(V12_PRIME_A, V12_SUB_B, '2024-04-15', '250.50'),
        _v12_report(V12_PRIME_A, V12_SUB_C, '2024-05-01', '75.25'),
        _v12_report(V12_PRIME_B, V12_SUB_EDGE, '2024-06-01', '40.00'),
        # A blank prime UEI and a malformed subcontractor UEI.
        _v12_report('', V12_SUB_A, '2024-03-01', '11.00'),
        _v12_report(V12_PRIME_A, 'bad-uei', '2024-03-02', '12.00'),
        # Fiscal year 2023, so the extract row of this subcontractor (its code is malformed)
        # is reached by no usable report. Then a date that does not exist.
        _v12_report(V12_PRIME_A, V12_BAD_CODE, '2023-09-30', '13.00'),
        _v12_report(V12_PRIME_A, V12_SUB_A, '2024-02-30', '14.00'),
        # Subcontractors that are D&B-era records for the other reasons, and a firm with two
        # extract rows that agree on the code (reported by a D&B-era prime).
        _v12_report(V12_PRIME_A, V12_BLANK_DATE, '2024-07-01', '51.00'),
        _v12_report(V12_PRIME_OLD, V12_TWO_ROWS, '2024-08-01', '52.00'),
        _v12_report(V12_PRIME_A, V12_EVS_DNB, '2024-09-01', '53.00'),
    ],
    2025: [
        # The duplicate row.
        _v12_report(V12_PRIME_B, V12_SUB_EDGE, '2025-01-15', '500.00', copies=2),
        # Group condition 1: the subcontractor's parent UEI is the prime.
        _v12_report(V12_PRIME_B, V12_SUB_A, '2025-02-01', '21.00', sub_parent_uei=V12_PRIME_B),
        _v12_report(V12_PRIME_B, V12_SUB_B, '2025-03-01', '22.00'),
        _v12_report(V12_PRIME_OLD, V12_SUB_A, '2025-04-01', '23.00'),
        _v12_report(V12_SELF, V12_SELF, '2025-05-01', '24.00'),
        _v12_report(V12_PRIME_A, V12_NOT_IN_SAM, '2025-06-01', '25.00'),
        _v12_report(V12_PRIME_A, V12_NO_CODE, '2025-07-01', '26.00'),
        # Prime B is a subcontractor here, so it is a firm in both roles.
        _v12_report(V12_PRIME_A, V12_PRIME_B, '2025-08-01', '27.00'),
        # Reports in the 2025 file that count under their own fiscal year, 2026.
        _v12_report(V12_PRIME_A, V12_SUB_B, '2025-11-10', '41.00'),
        _v12_report(V12_PRIME_B, V12_SUB_B, '2025-12-12', '43.00'),
        _v12_report(V12_PRIME_A, V12_BAD_DATE, '2025-09-20', '54.00'),
        _v12_report(V12_PRIME_OLD, V12_MIXED, '2025-09-05', '55.00'),
        # Both UEIs are padded with ASCII whitespace and join their extract rows.
        _v12_report(f' {V12_PRIME_OLD}\t', f'\t{V12_PADDED} ', '2025-07-15', '56.00'),
        # The lowercase spelling of a real UEI is unusable.
        _v12_report(V12_PRIME_A.lower(), V12_SUB_A, '2025-06-15', '57.00'),
        # Two parent UEIs that are equal and malformed are no group.
        _v12_report(V12_PRIME_E, V12_SUB_D1, '2025-08-20', '58.00',
                    prime_parent_uei=_V12_LOWER_GROUP, sub_parent_uei=_V12_LOWER_GROUP),
    ],
    2026: [
        # Group condition 2: the prime's parent UEI is the subcontractor.
        _v12_report(V12_PRIME_C, V12_SUB_B, '2026-01-10', '31.00', prime_parent_uei=V12_SUB_B),
        # Group condition 3: both parent UEIs are one other UEI.
        _v12_report(V12_PRIME_D, V12_SUB_EDGE, '2026-02-01', '32.00',
                    prime_parent_uei=_V12_GROUP_X, sub_parent_uei=_V12_GROUP_X),
        # Two different valid parents are no group.
        _v12_report(V12_PRIME_C, V12_SUB_C, '2026-03-01', '33.00',
                    prime_parent_uei=_V12_GROUP_Y, sub_parent_uei=_V12_GROUP_Z),
        _v12_report(V12_PRIME_B, V12_NOT_2022, '2026-04-01', '34.00'),
        _v12_report(V12_PRIME_C, V12_CONFLICT, '2026-05-01', '35.00'),
        # Fiscal year 2027, and the last day of fiscal year 2026.
        _v12_report(V12_PRIME_C, V12_SUB_EDGE, '2026-10-01', '36.00'),
        _v12_report(V12_PRIME_A, V12_SUB_C, '2026-09-30', '37.00'),
        # A report in the 2026 file that counts under its own fiscal year, 2025.
        _v12_report(V12_PRIME_B, V12_SUB_B, '2025-09-15', '42.00'),
        # Two parent UEIs that are blank after stripping are no group.
        _v12_report(V12_PRIME_E, V12_SUB_D2, '2026-06-01', '59.00',
                    prime_parent_uei='   ', sub_parent_uei='\t'),
    ],
}


def v12_inputs() -> tuple[dict[int, dict[str, list[list[str]]]], list[str]]:
    '''The subaward members by year, in the committed header layout, and the extract lines in
    the committed extract layout.

    Each record has every header cell, and the name and address cells hold `DNB_SENTINEL`. Each
    extract line has every field. The restricted positions hold `DNB_SENTINEL`, and the
    last-update date, the code and the EVS source are set. The design is in `_V12_REPORTS` and
    `_V12_FIRMS`.
    '''
    layouts = vendor_link_layouts.load_subaward_layouts()
    layout = vendor_link_layouts.load_extract_layout()
    text = {f'cell_{name}': DNB_SENTINEL for name in _V12_TEXT_CELLS}
    subawards = {}
    for year, reports in _V12_REPORTS.items():
        records = []
        for number, report in enumerate(reports, start=1):
            fields = {key: value for key, value in report.items() if key != 'copies'}
            record = subaward_record(layouts[year], subaward_type='sub-contract',
                                     report_id=f'V12-{year}-{number:03d}', **fields, **text)
            records.extend(list(record) for _ in range(report.get('copies', 1)))
        subawards[year] = {V12_MEMBER: records}
    lines = []
    for uei, code, update, *other in _V12_FIRMS:
        fields = {'registration_status': 'A', 'evs_source': 'SAM'} | (other[0] if other else {})
        if fields.pop('dnb_evs', False):
            fields['evs_source'] = sorted(layout.evs_dnb)[0]
        lines.append(extract_line(layout, uei=uei, last_update_date=update, primary_naics=code,
                                  naics_code_string=f'{code}Y' if code else '', **fields))
    return subawards, lines


def _v12_no_client(*args, **kwargs):
    raise AssertionError('the V12 fixture chain attempted external access')


def run_vendor_link_v12(tmp_path: Path, monkeypatch) -> dict:
    '''Raw subaward and extract files to two verified, replay-equal Stage 14 bundles, with
    external access blocked.

    The guards go in first, so seeding, both builds, both verifications and the comparison run
    under them, in the spec's order: build and verify the first run, build and verify the
    second, then compare. The data root is `tmp_path / 'data'`, and every command gets it
    explicitly. The returned dict holds `data_dir`, the `first` and `second` bundle directories,
    their detached pins (`first_pin`, `second_pin`), both verification results and the
    `comparison`.
    '''
    # Imported here so that every vendor-link test module does not load these modules.
    from target_fixtures import forbid_external_access

    from embedding_data import vendor_link_bundle

    forbid_external_access(monkeypatch)
    monkeypatch.delenv('SAM_API_KEY', raising=False)
    monkeypatch.setattr(httpx.Client, '__init__', _v12_no_client)
    monkeypatch.setattr(httpx.AsyncClient, '__init__', _v12_no_client)
    monkeypatch.setattr(usaspending_raw, 'make_client', _v12_no_client)
    monkeypatch.setattr(sam_access, 'make_client', _v12_no_client)
    data_dir = tmp_path / 'data'
    codes_run, codes_pin = seed_codes_bundle(data_dir, tmp_path / 'stage4-originals')
    subawards, lines = v12_inputs()
    seed_raw(data_dir, tmp_path / 'raw-originals', subawards, lines, snapshot=V12_SNAPSHOT,
             month=V12_MONTH, subaward_layouts=vendor_link_layouts.load_subaward_layouts(),
             extract_layout=vendor_link_layouts.load_extract_layout(),
             extract_member=V12_EXTRACT_MEMBER)
    result = {'data_dir': data_dir}
    for name, run_id in zip(('first', 'second'), V12_RUNS, strict=True):
        run = vendor_link_bundle.build(
            data_dir, run_id, codes_run=codes_run, codes_outputs_sha256=codes_pin,
            snapshot=V12_SNAPSHOT, sam_month=V12_MONTH)
        directory = Path(run['directory'])
        result[name] = directory
        result[name + '_pin'] = run['outputs_sha256']
        result[name + '_verification'] = vendor_link_bundle.verify_bundle(
            directory, data_dir, expected_outputs_sha256=run['outputs_sha256'])
    result['comparison'] = vendor_link_bundle.compare_runs(result['first'], result['second'])
    return result
