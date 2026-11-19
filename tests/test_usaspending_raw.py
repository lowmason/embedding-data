'''USAspending contract-subaward raw files: the request, polling, download, import and
selection rules.'''

import gzip
import hashlib
import json
import shutil
from dataclasses import asdict, replace
from datetime import UTC, date, datetime
from importlib.metadata import version

import httpx
import pytest
from vendor_link_fixtures import (  # noqa: F401
    NAME,
    REAL_MAKE_CLIENT,
    URL,
    FakeUsaspending,
    install_usaspending,
    no_live_sam,
    sample_zip,
    zip_bytes,
)

from embedding_data import manifest, paths, usaspending_raw

SNAPSHOT = date(2026, 11, 20)
LATER_SNAPSHOT = date(2027, 1, 5)
SUBCONTRACTS = 'raw/usaspending/subcontracts'
WRONG_URL = 'https://wrong.test.example/from-the-post.zip'
NOT_A_ZIP = b'PK\x03\x04garbage that is not an archive'


def snapshot_directory(data_directory, fiscal_year=2025, snapshot=SNAPSHOT):
    return usaspending_raw.snapshot_dir(data_directory, snapshot, fiscal_year)


def manifest_lines(data_directory):
    path = paths.manifest_path(data_directory)
    return path.read_text().splitlines() if path.exists() else []


def assert_nothing_written(data_directory):
    '''No final file, no `.part` and no manifest line anywhere under the data root.'''
    leftovers = [file for file in data_directory.rglob('*') if not file.is_dir()]
    assert leftovers == []
    assert manifest_lines(data_directory) == []


@pytest.mark.parametrize('fy, start, end', [(2024, '2023-10-01', '2024-09-30'),
                                            (2025, '2024-10-01', '2025-09-30'),
                                            (2026, '2025-10-01', '2026-09-30')])
def test_request_body_selects_contract_subawards_by_action_date(fy, start, end):
    body = usaspending_raw.request_body(fy)
    assert body['filters']['sub_award_types'] == ['procurement']
    assert body['filters']['date_type'] == 'action_date'
    assert body['filters']['date_range'] == {'start_date': start, 'end_date': end}
    assert not body['filters'].get('prime_award_types')
    assert (date.fromisoformat(end) - date.fromisoformat(start)).days + 1 <= 366


def test_request_body_is_the_document_check_body_with_only_the_dates_changing():
    expected = {
        'filters': {
            'sub_award_types': ['procurement'], 'date_type': 'action_date',
            'date_range': {'start_date': '2023-10-01', 'end_date': '2024-09-30'},
            'agencies': [{'type': 'awarding', 'tier': 'toptier', 'name': 'All'}]},
        'file_format': 'csv'}
    assert usaspending_raw.request_body(2024) == expected
    for fiscal_year, (start, end) in {2025: ('2024-10-01', '2025-09-30'),
                                      2026: ('2025-10-01', '2026-09-30')}.items():
        expected['filters']['date_range'] = {'start_date': start, 'end_date': end}
        assert usaspending_raw.request_body(fiscal_year) == expected


def test_request_body_is_a_fresh_object_each_call():
    first = usaspending_raw.request_body(2025)
    first['filters']['agencies'].clear()
    first['filters']['sub_award_types'].append('grant')
    again = usaspending_raw.request_body(2025)
    assert again['filters']['sub_award_types'] == ['procurement']
    assert again['filters']['agencies']


def test_window_and_fiscal_year_range():
    assert usaspending_raw.WINDOW == (2024, 2025, 2026)
    assert usaspending_raw.fiscal_year_range(2024) == (date(2023, 10, 1), date(2024, 9, 30))
    assert usaspending_raw.fiscal_year_range(2026) == (date(2025, 10, 1), date(2026, 9, 30))


def test_snapshot_dir_layout(data_directory):
    assert snapshot_directory(data_directory) == (
        data_directory / SUBCONTRACTS / '2026-11-20' / 'FY2025')


def test_client_is_keyless_follows_redirects_ignores_the_environment_and_asks_for_identity():
    with REAL_MAKE_CLIENT() as client:
        assert client.follow_redirects is True
        assert client.trust_env is False
        assert client.timeout == httpx.Timeout(600.0, connect=15.0)
        assert client.headers['User-Agent'] == 'embedding-data USAspending acquisition'
        assert client.headers['Accept-Encoding'] == 'identity'


def test_acquire_polls_then_downloads_and_records(data_directory, monkeypatch):
    server = FakeUsaspending(statuses=('running', 'running', 'finished'),
                             post_file_url=WRONG_URL)
    slept = install_usaspending(monkeypatch, server)
    path = usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    assert path.relative_to(data_directory).as_posix() == (
        f'raw/usaspending/subcontracts/2026-11-20/FY2025/{NAME}')
    assert slept == [30, 30]
    entry = manifest.entry_for(paths.manifest_path(data_directory), path)
    assert (entry.client, entry.source_url, entry.proxies, entry.through_date) == (
        'httpx', URL, (), None)


def test_acquire_records_the_delivered_bytes_and_prints_nothing(data_directory, monkeypatch,
                                                                capsys):
    server = FakeUsaspending()
    install_usaspending(monkeypatch, server)
    before = datetime.now(UTC).replace(microsecond=0)
    path = usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    assert capsys.readouterr() == ('', '')
    assert path.read_bytes() == server.body
    (line,) = manifest_lines(data_directory)
    recorded = json.loads(line)
    assert recorded['path'] == f'usaspending/subcontracts/2026-11-20/FY2025/{NAME}'
    assert recorded['sha256'] == hashlib.sha256(server.body).hexdigest()
    assert recorded['size'] == len(server.body)
    assert recorded['client_version'] == version('httpx')
    assert before <= datetime.fromisoformat(recorded['retrieved_at']) <= datetime.now(UTC)
    assert not list(path.parent.glob('*.part'))


def test_acquire_sends_the_request_body_and_polls_by_file_name(data_directory, monkeypatch):
    server = FakeUsaspending(statuses=('running', 'finished'))
    install_usaspending(monkeypatch, server)
    usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    (post,) = server.posts
    assert str(post.url) == 'https://api.usaspending.gov/api/v2/bulk_download/awards/'
    assert server.posted_body() == usaspending_raw.request_body(2025)
    assert [(poll.url.host, poll.url.path, poll.url.params['file_name'])
            for poll in server.polls] == [
        ('api.usaspending.gov', '/api/v2/download/status', NAME)] * 2
    (download,) = server.downloads
    assert str(download.url) == URL
    for request in server.requests:
        assert request.headers['User-Agent'] == 'embedding-data USAspending acquisition'
        assert request.headers['Accept-Encoding'] == 'identity'
        assert 'authorization' not in request.headers
        assert 'api_key' not in str(request.url)


def test_acquire_follows_a_download_redirect_and_records_the_status_url(data_directory,
                                                                         monkeypatch):
    server = FakeUsaspending(redirect_to='https://files-2.test.example/other.zip')
    install_usaspending(monkeypatch, server)
    path = usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    assert [str(request.url) for request in server.downloads] == [
        URL, 'https://files-2.test.example/other.zip']
    entry = manifest.entry_for(paths.manifest_path(data_directory), path)
    assert entry.source_url == URL


@pytest.mark.parametrize('statuses', [('finished',), ('ready', 'finished'),
                                      ('running', 'ready', 'running', 'finished')])
def test_acquire_sleeps_between_polls_only(data_directory, monkeypatch, statuses):
    server = FakeUsaspending(statuses=statuses)
    slept = install_usaspending(monkeypatch, server)
    usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    assert len(server.polls) == len(statuses)
    assert slept == [30] * (len(statuses) - 1)


@pytest.mark.parametrize('fiscal_year', [2024, 2026])
def test_acquire_names_the_year_directory_after_the_requested_year(
        data_directory, monkeypatch, fiscal_year):
    server = FakeUsaspending(file_name=f'FY{fiscal_year}_subawards.zip',
                             file_url=URL.replace(NAME, f'FY{fiscal_year}_subawards.zip'))
    install_usaspending(monkeypatch, server)
    path = usaspending_raw.acquire(data_directory, fiscal_year, snapshot=SNAPSHOT)
    assert path.parent == snapshot_directory(data_directory, fiscal_year)
    assert server.posted_body() == usaspending_raw.request_body(fiscal_year)


def test_acquire_accepts_an_existing_empty_directory(data_directory, monkeypatch):
    install_usaspending(monkeypatch, FakeUsaspending())
    snapshot_directory(data_directory).mkdir(parents=True)
    path = usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    assert path.is_file()


def short_body_headers():
    return {'Content-Length': str(len(sample_zip()) + 10)}


def gzipped():
    body = gzip.compress(sample_zip())
    return {'body': body,
            'headers': {'Content-Length': str(len(body)), 'Content-Encoding': 'gzip'}}


def sized(body):
    return {'body': body, 'headers': {'Content-Length': str(len(body))}}


REFUSALS = {
    'failed': ({'statuses': ('running', 'failed')}, ValueError, 'download request failed'),
    'timed_out': ({'statuses': ('running',)}, ValueError, 'download request timed out'),
    'short': ({'headers': short_body_headers()}, httpx.RemoteProtocolError, 'received'),
    'unsized': ({'headers': {}}, ValueError, 'download has no Content-Length'),
    'gzip': (gzipped(), ValueError, 'encoded download'),
    'not_zip': (sized(NOT_A_ZIP), ValueError, 'download is not a ZIP file'),
    'unsafe_name': ({'file_name': '../evil.zip'}, ValueError, 'no usable file name'),
}


@pytest.mark.parametrize('case', ['failed', 'timed_out', 'short', 'unsized', 'gzip',
                                  'not_zip', 'unsafe_name'])
def test_acquire_refuses_and_leaves_nothing(case, data_directory, monkeypatch):
    options, error, message = REFUSALS[case]
    server = FakeUsaspending(**options)
    install_usaspending(monkeypatch, server)
    with pytest.raises(error, match=message):
        usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    assert_nothing_written(data_directory)


def test_acquire_accepts_an_explicit_identity_content_encoding(data_directory, monkeypatch):
    body = sample_zip()
    server = FakeUsaspending(body=body, headers={
        'Content-Length': str(len(body)), 'Content-Encoding': 'identity'})
    install_usaspending(monkeypatch, server)
    path = usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    assert path.read_bytes() == body


def test_acquire_refuses_a_body_longer_than_its_content_length(data_directory, monkeypatch):
    server = FakeUsaspending(headers={'Content-Length': str(len(sample_zip()) - 3)})
    install_usaspending(monkeypatch, server)
    with pytest.raises(httpx.RemoteProtocolError, match='received'):
        usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    assert_nothing_written(data_directory)


def test_acquire_never_writes_over_an_existing_part_file(data_directory, monkeypatch):
    # The occupancy check normally stops this first, so switch it off to reach the open.
    install_usaspending(monkeypatch, FakeUsaspending())
    monkeypatch.setattr(usaspending_raw, 'require_free_directory', lambda *arguments: None)
    directory = snapshot_directory(data_directory)
    directory.mkdir(parents=True)
    (directory / f'{NAME}.part').write_bytes(b'someone else')
    with pytest.raises(FileExistsError):
        usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    assert not (directory / NAME).exists()
    assert manifest_lines(data_directory) == []
    # The .part belongs to someone else, so a failed call must leave it as it found it.
    assert (directory / f'{NAME}.part').read_bytes() == b'someone else'


def test_acquire_gives_up_after_exactly_max_polls(data_directory, monkeypatch):
    server = FakeUsaspending(statuses=('running',))
    slept = install_usaspending(monkeypatch, server)
    with pytest.raises(ValueError, match='download request timed out'):
        usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    assert len(server.polls) == usaspending_raw.MAX_POLLS == 480
    assert set(slept) == {30}
    assert server.downloads == []


def test_acquire_stops_at_a_failed_status_without_polling_again(data_directory, monkeypatch):
    server = FakeUsaspending(statuses=('running', 'failed', 'finished'))
    slept = install_usaspending(monkeypatch, server)
    with pytest.raises(ValueError, match='download request failed'):
        usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    assert (len(server.polls), slept, server.downloads) == (2, [30], [])


EXTRA_REFUSALS = {
    'queued_status': ({'statuses': ('queued',)}, 'unexpected download status'),
    'unnamed_status': ({'statuses': (None,)}, 'unexpected download status'),
    'ready_then_resumed': ({'statuses': ('ready', 'resumed')}, 'unexpected download status'),
    'relative_url': ({'file_url': '/generated_downloads/file.zip'}, 'no usable URL'),
    'plain_http_url': ({'file_url': 'http://files.test.example/file.zip'}, 'no usable URL'),
    'hostless_url': ({'file_url': 'https:///file.zip'}, 'no usable URL'),
    'missing_url': ({'file_url': None}, 'no usable URL'),
    'prefixed_zip': (sized(b'XXXX' + sample_zip()), 'download is not a ZIP file'),
    'name_with_a_suffix': ({'file_name': 'file.zip.exe'}, 'no usable file name'),
    'name_with_a_path': ({'file_name': 'file.zip/../../x'}, 'no usable file name'),
    'name_with_a_newline': ({'file_name': 'file.zip\n'}, 'no usable file name'),
    'name_not_a_zip': ({'file_name': 'file.csv'}, 'no usable file name'),
    'name_with_a_capital_suffix': ({'file_name': 'FILE.ZIP'}, 'no usable file name'),
    'name_starting_with_a_dot': ({'file_name': '.hidden.zip'}, 'no usable file name'),
    'name_not_text': ({'file_name': 12345}, 'no usable file name'),
    'name_missing': ({'file_name': None}, 'no usable file name'),
}


@pytest.mark.parametrize('case', EXTRA_REFUSALS)
def test_acquire_refuses_more_shapes_before_downloading(case, data_directory, monkeypatch):
    options, message = EXTRA_REFUSALS[case]
    server = FakeUsaspending(**options)
    slept = install_usaspending(monkeypatch, server)
    with pytest.raises(ValueError, match=message):
        usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    if 'no usable URL' in message or 'unexpected download status' in message:
        assert server.downloads == []
    if 'unexpected download status' in message:
        assert len(server.polls) == len(options['statuses'])
        assert len(slept) == len(server.polls) - 1
    assert_nothing_written(data_directory)


def break_one_request(server, where, response):
    '''A transport that answers `response` to one stage of the exchange.

    `handle.hits` lists the requests that got `response`.
    '''
    def handle(request):
        if ((where == 'post' and request.method == 'POST')
                or (where == 'poll' and request.url.path == usaspending_raw.STATUS_PATH)
                or (where == 'download' and str(request.url) == URL)):
            handle.hits.append(request)
            return response
        return server(request)

    handle.hits = []
    return handle


@pytest.mark.parametrize('where', ['post', 'poll', 'download'])
def test_acquire_raises_on_an_http_error_status(where, data_directory, monkeypatch):
    server = FakeUsaspending()
    handle = break_one_request(server, where, httpx.Response(503))
    install_usaspending(monkeypatch, handle)
    with pytest.raises(httpx.HTTPStatusError):
        usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    assert len(handle.hits) == 1
    assert_nothing_written(data_directory)


@pytest.mark.parametrize('where', ['post', 'poll'])
@pytest.mark.parametrize('content, message', [
    (b'not json', 'Expecting value'), (b'[]', 'not a JSON object'),
    (b'null', 'not a JSON object'), (b'"text"', 'not a JSON object')])
def test_acquire_refuses_an_answer_that_is_not_a_json_object(where, content, message,
                                                              data_directory, monkeypatch):
    # Settled Default 15: no automatic retry. A bad answer ends the call at the first hit,
    # and its own message survives (it is not swallowed into an empty answer).
    server = FakeUsaspending()
    answer = httpx.Response(200, content=content)
    handle = break_one_request(server, where, answer)
    install_usaspending(monkeypatch, handle)
    with pytest.raises(ValueError, match=message):
        usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    assert len(handle.hits) == 1
    assert server.downloads == []
    assert_nothing_written(data_directory)


@pytest.mark.parametrize('fiscal_year', [2023, 2027, 0])
def test_acquire_refuses_a_year_outside_the_window_before_any_request(
        fiscal_year, data_directory, monkeypatch):
    server = FakeUsaspending()
    install_usaspending(monkeypatch, server)
    with pytest.raises(ValueError, match='outside the window'):
        usaspending_raw.acquire(data_directory, fiscal_year, snapshot=SNAPSHOT)
    assert server.requests == []


def occupy_with_file(data_directory):
    directory = snapshot_directory(data_directory)
    directory.mkdir(parents=True)
    (directory / 'earlier.zip').write_bytes(sample_zip())


def occupy_with_part(data_directory):
    directory = snapshot_directory(data_directory)
    directory.mkdir(parents=True)
    (directory / f'{NAME}.part').write_bytes(b'interrupted')


def occupy_with_directory(data_directory):
    (snapshot_directory(data_directory) / 'nested').mkdir(parents=True)


def occupy_with_a_file_in_place_of_the_directory(data_directory):
    directory = snapshot_directory(data_directory)
    directory.parent.mkdir(parents=True)
    directory.write_bytes(sample_zip())


def occupy_with_a_symlinked_directory(data_directory):
    target = data_directory.parent / 'elsewhere'
    target.mkdir()
    directory = snapshot_directory(data_directory)
    directory.parent.mkdir(parents=True)
    directory.symlink_to(target, target_is_directory=True)


def occupy_with_a_symlinked_parent(data_directory):
    target = data_directory.parent / 'elsewhere'
    target.mkdir()
    (data_directory / 'raw').mkdir(parents=True)
    (data_directory / 'raw' / 'usaspending').symlink_to(target, target_is_directory=True)


def occupy_with_a_symlinked_raw_directory(data_directory):
    target = data_directory.parent / 'elsewhere'
    target.mkdir()
    data_directory.mkdir()
    (data_directory / 'raw').symlink_to(target, target_is_directory=True)


OCCUPATIONS = [occupy_with_file, occupy_with_part, occupy_with_directory,
               occupy_with_a_file_in_place_of_the_directory,
               occupy_with_a_symlinked_directory, occupy_with_a_symlinked_parent,
               occupy_with_a_symlinked_raw_directory]


@pytest.mark.parametrize('occupy', OCCUPATIONS, ids=lambda function: function.__name__)
def test_acquire_refuses_an_occupied_destination_before_any_request(occupy, data_directory,
                                                                    monkeypatch):
    server = FakeUsaspending()
    install_usaspending(monkeypatch, server)
    occupy(data_directory)
    with pytest.raises(ValueError):
        usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    assert server.requests == []
    assert manifest_lines(data_directory) == []


def test_publish_partial_records_the_part_bytes_under_the_destination_path(data_directory):
    directory = snapshot_directory(data_directory)
    directory.mkdir(parents=True)
    partial = directory / f'{NAME}.part'
    partial.write_bytes(sample_zip())
    destination = directory / NAME
    before = datetime.now(UTC).replace(microsecond=0)
    result = usaspending_raw.publish_partial(
        data_directory, partial, destination, client='httpx', client_version='9.9',
        source_url='https://files.test.example/x.zip', proxies=('retrieved_at',))
    assert result == destination
    assert destination.read_bytes() == sample_zip()
    (entry,) = manifest.read_manifest(paths.manifest_path(data_directory))
    assert entry.path == f'usaspending/subcontracts/2026-11-20/FY2025/{NAME}'
    assert (entry.client, entry.client_version, entry.source_url, entry.proxies,
            entry.through_date) == ('httpx', '9.9', 'https://files.test.example/x.zip',
                                    ('retrieved_at',), None)
    assert (entry.sha256, entry.size) == (hashlib.sha256(sample_zip()).hexdigest(),
                                          len(sample_zip()))
    assert before <= datetime.fromisoformat(entry.retrieved_at) <= datetime.now(UTC)
    assert manifest.entry_for(paths.manifest_path(data_directory), destination) == entry


def test_publish_partial_refuses_a_recorded_path_before_linking(data_directory):
    directory = snapshot_directory(data_directory)
    directory.mkdir(parents=True)
    partial = directory / f'{NAME}.part'
    partial.write_bytes(sample_zip())
    destination = directory / NAME
    earlier = manifest.describe_file(
        partial, partial.parent, retrieved_at=datetime.now(UTC), client='httpx',
        client_version='1')
    manifest.append_entries(paths.manifest_path(data_directory), [replace(
        earlier, path=f'usaspending/subcontracts/2026-11-20/FY2025/{NAME}')])
    before = manifest_lines(data_directory)
    with pytest.raises(ValueError, match='already recorded'):
        usaspending_raw.publish_partial(
            data_directory, partial, destination, client='httpx', client_version='9.9',
            source_url=None, proxies=())
    assert not destination.exists()
    assert manifest_lines(data_directory) == before


def test_publish_partial_refuses_an_existing_destination_and_replaces_nothing(data_directory):
    directory = snapshot_directory(data_directory)
    directory.mkdir(parents=True)
    partial = directory / f'{NAME}.part'
    partial.write_bytes(sample_zip())
    destination = directory / NAME
    destination.write_bytes(b'kept')
    with pytest.raises(ValueError, match='already exists'):
        usaspending_raw.publish_partial(
            data_directory, partial, destination, client='httpx', client_version='9.9',
            source_url=None, proxies=())
    assert destination.read_bytes() == b'kept'
    assert manifest_lines(data_directory) == []


def make_original(tmp_path, name=NAME, content=None, folder='downloads'):
    original = tmp_path / folder / name
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(sample_zip() if content is None else content)
    return original


def test_import_records_a_proxy_retrieval_time(data_directory, tmp_path):
    original = make_original(tmp_path)
    path = usaspending_raw.import_file(data_directory, 2025, original, snapshot=SNAPSHOT)
    assert path == snapshot_directory(data_directory) / NAME
    assert path.read_bytes() == original.read_bytes()
    entry = manifest.entry_for(paths.manifest_path(data_directory), path)
    assert (entry.client, entry.source_url, entry.proxies, entry.through_date) == (
        'manual-import', None, ('retrieved_at',), None)
    assert entry.client_version == version('embedding-data')
    assert entry.sha256 == hashlib.sha256(original.read_bytes()).hexdigest()
    assert original.exists()
    assert not list(path.parent.glob('*.part'))


@pytest.mark.parametrize('fiscal_year', [2024, 2026])
def test_import_publishes_each_window_year_under_its_own_directory(
        data_directory, tmp_path, fiscal_year):
    path = usaspending_raw.import_file(
        data_directory, fiscal_year, make_original(tmp_path), snapshot=SNAPSHOT)
    assert path.parent == snapshot_directory(data_directory, fiscal_year)


def prepare_symlink(tmp_path):
    target = make_original(tmp_path, 'real.zip')
    link = tmp_path / 'downloads' / NAME
    link.symlink_to(target)
    return link


def prepare_directory(tmp_path):
    folder = tmp_path / 'downloads' / NAME
    folder.mkdir(parents=True)
    return folder


IMPORT_REFUSALS = {
    'year_below_the_window': (2023, lambda tmp_path: make_original(tmp_path),
                              'outside the window'),
    'year_above_the_window': (2027, lambda tmp_path: make_original(tmp_path),
                              'outside the window'),
    'symlink': (2025, prepare_symlink, 'not a regular file'),
    'directory': (2025, prepare_directory, 'not a regular file'),
    'missing': (2025, lambda tmp_path: tmp_path / 'downloads' / NAME, 'not a regular file'),
    'empty': (2025, lambda tmp_path: make_original(tmp_path, content=b''), 'empty'),
    'not_a_zip': (2025, lambda tmp_path: make_original(tmp_path, content=NOT_A_ZIP),
                  'not a ZIP file'),
    'prefixed_zip': (2025, lambda tmp_path: make_original(
        tmp_path, content=b'XXXX' + sample_zip()), 'not a ZIP file'),
    'name_with_a_space': (2025, lambda tmp_path: make_original(tmp_path, 'two words.zip'),
                          'safe .zip name'),
    'name_not_a_zip': (2025, lambda tmp_path: make_original(tmp_path, 'data.csv'),
                       'safe .zip name'),
    'name_with_a_capital_suffix': (2025, lambda tmp_path: make_original(tmp_path, 'FILE.ZIP'),
                                   'safe .zip name'),
    'name_with_a_trailing_suffix': (2025, lambda tmp_path: make_original(
        tmp_path, 'file.zip.exe'), 'safe .zip name'),
    'name_with_a_longer_suffix': (2025, lambda tmp_path: make_original(tmp_path, 'file.zipx'),
                                  'safe .zip name'),
    'name_starting_with_a_dot': (2025, lambda tmp_path: make_original(
        tmp_path, '.hidden.zip'), 'safe .zip name'),
}


@pytest.mark.parametrize('case', IMPORT_REFUSALS)
def test_import_refuses_other_years_existing_paths_symlinks_and_bad_names(
        case, data_directory, tmp_path):
    fiscal_year, prepare, message = IMPORT_REFUSALS[case]
    original = prepare(tmp_path)
    with pytest.raises(ValueError, match=message):
        usaspending_raw.import_file(data_directory, fiscal_year, original, snapshot=SNAPSHOT)
    assert_nothing_written(data_directory)


@pytest.mark.parametrize('occupy', OCCUPATIONS, ids=lambda function: function.__name__)
def test_import_refuses_an_occupied_snapshot_directory(occupy, data_directory, tmp_path):
    original = make_original(tmp_path)
    occupy(data_directory)
    with pytest.raises(ValueError):
        usaspending_raw.import_file(data_directory, 2025, original, snapshot=SNAPSHOT)
    assert manifest_lines(data_directory) == []


def test_import_never_replaces_an_earlier_import(data_directory, tmp_path):
    first = make_original(tmp_path)
    path = usaspending_raw.import_file(data_directory, 2025, first, snapshot=SNAPSHOT)
    second = make_original(tmp_path, 'other.zip', zip_bytes({'other.csv': b'x'}), 'second')
    before = manifest_lines(data_directory)
    with pytest.raises(ValueError):
        usaspending_raw.import_file(data_directory, 2025, second, snapshot=SNAPSHOT)
    assert path.read_bytes() == first.read_bytes()
    assert manifest_lines(data_directory) == before
    assert sorted(file.name for file in path.parent.iterdir()) == [NAME]


def test_import_never_writes_over_an_existing_part_file(data_directory, tmp_path,
                                                        monkeypatch):
    original = make_original(tmp_path)
    monkeypatch.setattr(usaspending_raw, 'require_free_directory', lambda *arguments: None)
    directory = snapshot_directory(data_directory)
    directory.mkdir(parents=True)
    (directory / f'{NAME}.part').write_bytes(b'someone else')
    with pytest.raises(FileExistsError):
        usaspending_raw.import_file(data_directory, 2025, original, snapshot=SNAPSHOT)
    assert not (directory / NAME).exists()
    assert manifest_lines(data_directory) == []
    # The .part belongs to someone else, so a failed call must leave it as it found it.
    assert (directory / f'{NAME}.part').read_bytes() == b'someone else'


def record_without_a_file(data_directory, tmp_path, name=NAME):
    '''Put the destination path of FY2025 in the manifest while no file exists there.'''
    scratch = make_original(tmp_path, 'scratch.zip', folder='scratch')
    earlier = manifest.describe_file(
        scratch, scratch.parent, retrieved_at=datetime.now(UTC), client='httpx',
        client_version='1')
    manifest.append_entries(paths.manifest_path(data_directory), [replace(
        earlier, path=f'usaspending/subcontracts/2026-11-20/FY2025/{name}')])
    return manifest_lines(data_directory)


def test_acquire_removes_the_part_it_made_when_publishing_fails(data_directory, tmp_path,
                                                                monkeypatch):
    install_usaspending(monkeypatch, FakeUsaspending())
    before = record_without_a_file(data_directory, tmp_path)
    with pytest.raises(ValueError, match='already recorded'):
        usaspending_raw.acquire(data_directory, 2025, snapshot=SNAPSHOT)
    assert list(snapshot_directory(data_directory).iterdir()) == []
    assert manifest_lines(data_directory) == before


def test_import_removes_the_part_it_made_when_publishing_fails(data_directory, tmp_path):
    original = make_original(tmp_path)
    before = record_without_a_file(data_directory, tmp_path)
    with pytest.raises(ValueError, match='already recorded'):
        usaspending_raw.import_file(data_directory, 2025, original, snapshot=SNAPSHOT)
    assert list(snapshot_directory(data_directory).iterdir()) == []
    assert manifest_lines(data_directory) == before


def test_import_refuses_a_copy_whose_hash_differs_and_leaves_nothing(
        data_directory, tmp_path, monkeypatch):
    original = make_original(tmp_path)

    def corrupt(source, target):
        target.write(b'corrupt copy')

    monkeypatch.setattr(usaspending_raw.shutil, 'copyfileobj', corrupt)
    with pytest.raises(ValueError, match='SHA-256 changed while copying'):
        usaspending_raw.import_file(data_directory, 2025, original, snapshot=SNAPSHOT)
    assert_nothing_written(data_directory)


def import_window(data_directory, tmp_path, snapshot):
    '''Import one distinct file for every window year under `snapshot`.'''
    return {
        fiscal_year: usaspending_raw.import_file(
            data_directory, fiscal_year,
            make_original(tmp_path, f'FY{fiscal_year}_{snapshot}.zip',
                          zip_bytes({f'FY{fiscal_year}.csv': snapshot.isoformat().encode()}),
                          f'{snapshot}-{fiscal_year}'),
            snapshot=snapshot)
        for fiscal_year in usaspending_raw.WINDOW}


def test_snapshot_selection_ignores_other_snapshots(data_directory, tmp_path):
    first = import_window(data_directory, tmp_path, SNAPSHOT)
    second = import_window(data_directory, tmp_path, LATER_SNAPSHOT)
    selected = usaspending_raw.select_files(data_directory, SNAPSHOT)
    assert selected == first
    assert list(selected) == [2024, 2025, 2026]
    assert usaspending_raw.select_files(data_directory, LATER_SNAPSHOT) == second
    assert set(first.values()).isdisjoint(second.values())


def add_a_file(files):
    (files[2025].parent / 'extra.zip').write_bytes(sample_zip())


def add_a_part(files):
    (files[2025].parent / 'FY2025.zip.part').write_bytes(b'interrupted')


def add_a_directory(files):
    (files[2025].parent / 'nested').mkdir()


def remove_a_year(files):
    shutil.rmtree(files[2026].parent)


def empty_a_year(files):
    files[2024].unlink()


def rename_without_the_suffix(files):
    files[2025].rename(files[2025].with_name('FY2025.dat'))


def replace_with_a_symlink(files):
    copy = files[2025].parent.parent / 'copy.zip'
    shutil.copy(files[2025], copy)
    files[2025].unlink()
    files[2025].symlink_to(copy)


def replace_a_year_directory_with_a_symlink(files):
    moved = files[2024].parent.parent / 'moved'
    files[2024].parent.rename(moved)
    files[2024].parent.symlink_to(moved, target_is_directory=True)


def change_the_bytes(files):
    original = files[2026].read_bytes()
    files[2026].write_bytes(bytes([original[0] ^ 1]) + original[1:])


SELECTION_FAILURES = {
    'extra_file': (add_a_file, 'missing or extra raw file'),
    'extra_part': (add_a_part, 'missing or extra raw file'),
    'extra_directory': (add_a_directory, 'missing or extra raw file'),
    'missing_year': (remove_a_year, 'missing or extra raw file'),
    'empty_year': (empty_a_year, 'missing or extra raw file'),
    'not_a_zip_name': (rename_without_the_suffix, 'missing or extra raw file'),
    'symlinked_file': (replace_with_a_symlink, 'missing or extra raw file'),
    'symlinked_year_directory': (replace_a_year_directory_with_a_symlink, 'symlink'),
    'changed_bytes': (change_the_bytes, 'raw file changed'),
}


@pytest.mark.parametrize('case', SELECTION_FAILURES)
def test_snapshot_selection_refuses_any_other_state(case, data_directory, tmp_path):
    files = import_window(data_directory, tmp_path, SNAPSHOT)
    damage, message = SELECTION_FAILURES[case]
    damage(files)
    with pytest.raises(ValueError, match=message):
        usaspending_raw.select_files(data_directory, SNAPSHOT)


def test_snapshot_selection_refuses_files_the_manifest_does_not_record(data_directory):
    for fiscal_year in usaspending_raw.WINDOW:
        directory = snapshot_directory(data_directory, fiscal_year, LATER_SNAPSHOT)
        directory.mkdir(parents=True)
        (directory / f'FY{fiscal_year}.zip').write_bytes(sample_zip())
    with pytest.raises(ValueError, match='raw file is not recorded'):
        usaspending_raw.select_files(data_directory, LATER_SNAPSHOT)


def test_snapshot_selection_of_an_unknown_snapshot_is_missing(data_directory):
    with pytest.raises(ValueError, match='missing or extra raw file'):
        usaspending_raw.select_files(data_directory, date(2030, 1, 1))


def test_citations_are_verified_json_round_tripped_and_sorted_by_path(data_directory,
                                                                       tmp_path):
    files = import_window(data_directory, tmp_path, SNAPSHOT)
    cited = usaspending_raw.citations(data_directory, [files[2026], files[2024], files[2025]])
    assert [entry['path'] for entry in cited] == sorted(entry['path'] for entry in cited)
    assert [entry['path'] for entry in cited] == [
        f'usaspending/subcontracts/2026-11-20/FY{year}/FY{year}_2026-11-20.zip'
        for year in (2024, 2025, 2026)]
    for year, entry in zip((2024, 2025, 2026), cited):
        recorded = manifest.entry_for(paths.manifest_path(data_directory), files[year])
        assert entry == json.loads(json.dumps(asdict(recorded)))
        assert entry['proxies'] == ['retrieved_at']
        assert entry['samples'] == []


def test_citations_refuse_a_changed_file(data_directory, tmp_path):
    files = import_window(data_directory, tmp_path, SNAPSHOT)
    files[2025].write_bytes(b'changed')
    with pytest.raises(ValueError, match='changed'):
        usaspending_raw.citations(data_directory, files.values())
