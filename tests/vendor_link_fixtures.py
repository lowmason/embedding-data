'''Synthetic fixtures for the Stage 14 vendor-link tests.

Nothing here is real data: the file names, URLs, ZIP members and the key are made up, and
the fake USAspending and SAM.gov servers answer from memory. Fixture results show software
readiness only.
'''

import io
import json
import logging
import zipfile

import httpx
import pytest

from embedding_data import sam_access, usaspending_raw

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
