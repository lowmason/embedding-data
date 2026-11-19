'''Synthetic fixtures for the Stage 14 vendor-link tests.

Nothing here is real data: the file names, URLs and ZIP members are made up, and the fake
USAspending server answers from memory. Fixture results show software readiness only.
'''

import io
import json
import zipfile

import httpx
import pytest

from embedding_data import usaspending_raw

FAKE_KEY = 'FAKEKEYfake0123456789ABCDEFghij'
NAME = 'FY2025_Subawards_2026-11-20_H10M00S00.zip'
URL = f'https://files.test.example/generated_downloads/{NAME}'
# The module's real factory, taken at import time, before `no_live_sam` replaces it.
REAL_MAKE_CLIENT = usaspending_raw.make_client


@pytest.fixture(autouse=True)
def no_live_sam(monkeypatch):
    '''Make a missed patch fail the test instead of spending a live request.'''
    monkeypatch.delenv('SAM_API_KEY', raising=False)

    def refuse(*args, **kwargs):
        raise AssertionError('live client')

    monkeypatch.setattr(usaspending_raw, 'make_client', refuse)


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
