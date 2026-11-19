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
import zipfile
from pathlib import Path

import httpx
import pytest

from embedding_data import sam_access, usaspending_raw, vendor_link_layouts

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


def sample_extract(month=MONTH) -> bytes:
    '''A synthetic extract ZIP: one member with framing lines and no entity record.'''
    stem = extract_name(month).removesuffix('.ZIP')
    return zip_bytes({f'{stem}.dat': b'BOF PUBLIC V2 00000000 20261102 0000000 0000000\r\n'
                                     b'EOF PUBLIC V2 00000000 20261102 0000000 0000000'})


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
