'''EPA TRI raw files: the page catalog, acquisition, import and snapshot selection.'''

import gzip
import json
import shutil
from datetime import UTC, date, datetime, timedelta
from functools import partial
from importlib.metadata import version
from pathlib import Path

import httpx
import pytest

from embedding_data import manifest, paths, tri_raw

PAGE = Path(__file__).parent / 'fixtures/epa_tri/basic_data_files.html'
RECORDED = date(2025, 11, 5)
LATER = date(2026, 6, 1)
URLS = {
    y: f'https://data.epa.gov/efservice/downloads/tri/mv_tri_basic_download/{y}_US/csv'
    for y in (2022, 2023, 2024)
}
# Synthetic bodies: made-up rows, never EPA data.
BODIES = {y: f'YEAR,TRIFD\n{y},SYNTH{y}FAKE01\n'.encode() for y in URLS}
TEMPLATE = ('`https://data.epa.gov/efservice/downloads/tri/mv_tri_basic_download/'
            '${year}_${geography}/csv`')
CALL = 'updateDownloadButtonHref();'


def sentence(day: str) -> str:
    return f'<p>Includes reporting forms processed as of: <strong>{day}</strong></p>'


def option(value: str, label: str | None = None) -> str:
    return f'<option value="{value}">{value if label is None else label}</option>'


def edited(*replacements: tuple[str, str]) -> str:
    '''The fixture page with each `old` text, present exactly once, replaced by `new`.'''
    page = PAGE.read_text()
    for old, new in replacements:
        assert page.count(old) == 1, old
        page = page.replace(old, new)
    return page


UNREADABLE = {
    'drop_date': [('November 5, 2025', '')],
    'second_date': [('</main>', sentence('June 1, 2026') + '</main>')],
    'drop_2023': [(option('2023'), '')],
    'repeat_2024': [(option('2024'), option('2024') * 2)],
}


def test_parse_page_reads_the_snapshot_date_and_window_links():
    catalog = tri_raw.parse_page(PAGE.read_text(), tri_raw.PAGE_URL)
    assert catalog.processed_as_of == RECORDED
    assert sorted(catalog.urls) == [2022, 2023, 2024]
    assert all(url.startswith('https://') for url in catalog.urls.values())


@pytest.mark.parametrize('edit', ['drop_date', 'second_date', 'drop_2023', 'repeat_2024'])
def test_parse_page_refuses_an_unreadable_catalog(edit):
    with pytest.raises(ValueError):
        tri_raw.parse_page(edited(*UNREADABLE[edit]), tri_raw.PAGE_URL)


# Additional coverage beyond the plan tests.

def test_parse_page_applies_the_template_to_us_and_each_window_year():
    catalog = tri_raw.parse_page(PAGE.read_text(), tri_raw.PAGE_URL)
    assert list(catalog.urls.items()) == list(URLS.items())


REFUSED = {
    'impossible_date': [('November 5, 2025', 'February 30, 2025')],
    'date_only_in_a_script': [('November 5, 2025', ''),
                              (CALL, f'{CALL}\n      // processed as of: November 5, 2025')],
    'no_template': [(TEMPLATE, '"https://data.epa.gov/efservice/fixed/csv"')],
    'template_outside_a_script': [(TEMPLATE, '""'), ('</main>', f'<p>{TEMPLATE}</p></main>')],
    'two_templates': [(CALL, f'{CALL}\n      var copy = {TEMPLATE};')],
    'template_in_a_second_script': [
        ('</body>', f'<script>var copy = {TEMPLATE};</script></body>')],
    'http_scheme': [('`https://data', '`http://data')],
    'foreign_host': [('data.epa.gov', 'data.epa.gov.example.com')],
    'lookalike_host': [('data.epa.gov', 'data.notepa.gov')],
    'drop_us': [(option('US', 'U.S.'), '')],
    'repeat_us': [(option('US', 'U.S.'), option('US', 'U.S.') * 2)],
    'us_only_in_the_year_list': [(option('US', 'U.S.'), ''),
                                 (option('2021'), option('2021') + option('US', 'U.S.'))],
    'year_only_in_the_geography_list': [(option('2023'), ''),
                                        (option('AL'), option('AL') + option('2023'))],
    'drop_2022': [(option('2022'), '')],
    'drop_2024': [(option('2024'), '')],
    'repeat_2022': [(option('2022'), option('2022') * 2)],
}


@pytest.mark.parametrize('edit', list(REFUSED))
def test_parse_page_refuses_a_changed_date_or_url_rule(edit):
    with pytest.raises(ValueError):
        tri_raw.parse_page(edited(*REFUSED[edit]), tri_raw.PAGE_URL)


ACCEPTED = {
    'same_date_twice': [('</main>', sentence('November 5, 2025') + '</main>')],
    'repeated_unused_options': [(option('2021'), option('2021') * 2),
                                (option('FED', 'Fed'), option('FED', 'Fed') * 2)],
    'year_only_template': [(CALL, f'{CALL}\n      var label = `Reporting year ${{year}}`;')],
}


@pytest.mark.parametrize('edit', list(ACCEPTED))
def test_parse_page_accepts_a_repeated_date_and_unused_options(edit):
    catalog = tri_raw.parse_page(edited(*ACCEPTED[edit]), tri_raw.PAGE_URL)
    assert (catalog.processed_as_of, catalog.urls) == (RECORDED, URLS)


def test_parse_page_accepts_a_template_on_the_bare_epa_gov_host():
    catalog = tri_raw.parse_page(edited(('data.epa.gov', 'epa.gov')), tri_raw.PAGE_URL)
    assert catalog.urls == {
        y: url.replace('data.epa.gov', 'epa.gov') for y, url in URLS.items()}


def test_raw_layout_names_each_window_year_under_its_snapshot_date(tmp_path):
    assert (tri_raw.SOURCE, tri_raw.WINDOW) == ('epa_tri', (2022, 2023, 2024))
    assert [tri_raw.file_name(y) for y in (2022, 2023, 2024)] == [
        '2022_us.csv', '2023_us.csv', '2024_us.csv']
    snapshot = tmp_path / 'raw' / 'epa_tri' / 'basic' / '2023' / '2025-11-05'
    assert tri_raw.snapshot_dir(tmp_path, 2023, RECORDED) == snapshot
    assert tri_raw.raw_path(tmp_path, 2023, RECORDED) == snapshot / '2023_us.csv'
    for year in (2021, 2025):
        with pytest.raises(ValueError):
            tri_raw.file_name(year)


def test_registered_names_are_the_file_names_that_epa_sends():
    # EPA answers each download with `Content-Disposition: attachment; filename="<year>_us.csv"`.
    assert [tri_raw.file_name(year) for year in tri_raw.WINDOW] == [
        '2022_us.csv', '2023_us.csv', '2024_us.csv']


@pytest.mark.parametrize('year', [0, 2021, 2025, 2026, -2023])
def test_a_year_outside_the_window_has_no_registered_name(year):
    with pytest.raises(ValueError):
        tri_raw.file_name(year)


def test_client_sends_the_recorded_user_agent_and_asks_for_identity():
    assert tri_raw.PAGE_URL == (
        'https://www.epa.gov/toxics-release-inventory-tri-program/'
        'tri-basic-data-files-calendar-years-1987-present')
    assert tri_raw.USER_AGENT == 'embedding-data TRI acquisition'
    with tri_raw.make_client() as client:
        assert client.headers['User-Agent'] == 'embedding-data TRI acquisition'
        assert client.headers['Accept-Encoding'] == 'identity'
        assert client.follow_redirects is True
        assert client.timeout == httpx.Timeout(600.0, connect=15.0)


class Epa:
    '''The page and the three window files behind a mock transport that records each request.'''

    def __init__(self, monkeypatch, page: str | None = None):
        self.responses = {
            url: (200, body, {'Content-Length': str(len(body))})
            for url, body in zip(URLS.values(), BODIES.values(), strict=True)
        }
        self.serve_page(PAGE.read_text() if page is None else page)
        self.requests: list[str] = []
        transport = httpx.MockTransport(self.respond)
        monkeypatch.setattr(tri_raw, 'make_client',
                            partial(tri_raw.make_client, transport=transport))

    def serve_page(self, page: str, status: int = 200) -> None:
        self.responses[tri_raw.PAGE_URL] = (
            status, page.encode(), {'Content-Type': 'text/html; charset=UTF-8'})

    def respond(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requests.append(url)
        assert request.headers['User-Agent'] == tri_raw.USER_AGENT
        assert request.headers['Accept-Encoding'] == 'identity'
        status, body, headers = self.responses[url]
        return httpx.Response(status, headers=headers, stream=httpx.ByteStream(body))


def files_under(directory: Path) -> list[str]:
    '''Every non-directory path below directory, relative and sorted.'''
    return sorted(path.relative_to(directory).as_posix() for path in directory.rglob('*')
                  if not path.is_dir())


def assert_retrieved_now(entry: manifest.ManifestEntry) -> None:
    retrieved = datetime.fromisoformat(entry.retrieved_at)
    assert retrieved.tzinfo is not None
    assert abs(datetime.now(UTC) - retrieved) < timedelta(minutes=10)


def test_acquire_downloads_and_records_each_window_file(data_directory, monkeypatch):
    Epa(monkeypatch)
    files = tri_raw.acquire(data_directory)
    assert [f.relative_to(data_directory).as_posix() for f in files] == [
        f'raw/epa_tri/basic/{y}/{RECORDED.isoformat()}/{tri_raw.file_name(y)}'
        for y in tri_raw.WINDOW]
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [(e.client, e.source_url, e.through_date, e.proxies) for e in entries] == [
        ('httpx', URLS[y], RECORDED.isoformat(), ()) for y in tri_raw.WINDOW]


def test_acquire_saves_the_sent_bytes_and_nothing_else(data_directory, monkeypatch, capsys):
    epa = Epa(monkeypatch)
    files = tri_raw.acquire(data_directory)
    assert epa.requests == [tri_raw.PAGE_URL, *URLS.values()]
    assert [file.read_bytes() for file in files] == list(BODIES.values())
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    for entry, file in zip(entries, files, strict=True):
        assert entry.path == file.relative_to(data_directory / 'raw').as_posix()
        assert (entry.sha256, entry.size) == (manifest.sha256_file(file), file.stat().st_size)
        assert entry.client_version == version('httpx')
        assert_retrieved_now(entry)
    assert files_under(data_directory) == sorted(
        [file.relative_to(data_directory).as_posix() for file in files]
        + ['raw/manifest.jsonl'])
    assert capsys.readouterr().out == ''


@pytest.mark.parametrize('length', ['short', 'absent', 'gzip_encoded'])
def test_acquire_refuses_a_short_unsized_or_encoded_body(length, data_directory, monkeypatch):
    epa = Epa(monkeypatch)
    body, packed = BODIES[2022], gzip.compress(BODIES[2022])
    epa.responses[URLS[2022]] = {
        'short': (200, body, {'Content-Length': str(len(body) + 1)}),
        'absent': (200, body, {}),
        'gzip_encoded': (200, packed, {'Content-Length': str(len(packed)),
                                       'Content-Encoding': 'gzip'}),
    }[length]
    error, message = {
        'short': (httpx.RemoteProtocolError, 'Content-Length'),
        'absent': (ValueError, 'download has no Content-Length'),
        'gzip_encoded': (ValueError, 'encoded download'),
    }[length]
    with pytest.raises(error, match=message):
        tri_raw.acquire(data_directory)
    assert epa.requests == [tri_raw.PAGE_URL, URLS[2022]]
    assert files_under(data_directory) == []


def test_acquire_refuses_an_empty_download(data_directory, monkeypatch):
    epa = Epa(monkeypatch)
    epa.responses[URLS[2022]] = (200, b'', {'Content-Length': '0'})
    with pytest.raises(ValueError, match='empty download'):
        tri_raw.acquire(data_directory)
    assert epa.requests == [tri_raw.PAGE_URL, URLS[2022]]
    assert files_under(data_directory) == []


def test_acquire_downloads_only_the_missing_years(data_directory, monkeypatch, tmp_path):
    epa = Epa(monkeypatch)
    original = tmp_path / 'download.csv'
    original.write_bytes(b'imported 2022\n')
    imported = tri_raw.import_file(data_directory, 2022, original, processed_as_of=RECORDED)
    ledger = paths.manifest_path(data_directory)
    [entry] = manifest.read_manifest(ledger)
    files = tri_raw.acquire(data_directory)
    assert epa.requests == [tri_raw.PAGE_URL, URLS[2023], URLS[2024]]
    assert files == [tri_raw.raw_path(data_directory, y, RECORDED) for y in (2022, 2023, 2024)]
    assert files[0] == imported
    assert [file.read_bytes() for file in files] == [
        b'imported 2022\n', BODIES[2023], BODIES[2024]]
    entries = manifest.read_manifest(ledger)
    assert entries[0] == entry
    assert [(e.path, e.client, e.source_url) for e in entries[1:]] == [
        (files[1].relative_to(data_directory / 'raw').as_posix(), 'httpx', URLS[2023]),
        (files[2].relative_to(data_directory / 'raw').as_posix(), 'httpx', URLS[2024])]


def test_acquire_refuses_a_body_longer_than_its_content_length(data_directory, monkeypatch):
    epa = Epa(monkeypatch)
    epa.responses[URLS[2022]] = (200, BODIES[2022], {'Content-Length': str(len(BODIES[2022]) - 1)})
    with pytest.raises(httpx.RemoteProtocolError):
        tri_raw.acquire(data_directory)
    assert files_under(data_directory) == []


def test_acquire_accepts_an_explicit_identity_encoding(data_directory, monkeypatch):
    epa = Epa(monkeypatch)
    status, body, headers = epa.responses[URLS[2023]]
    epa.responses[URLS[2023]] = (status, body, headers | {'Content-Encoding': 'identity'})
    files = tri_raw.acquire(data_directory)
    assert files[1].read_bytes() == BODIES[2023]


@pytest.mark.parametrize('failing', ['page', 'file'])
def test_acquire_refuses_a_failed_request(failing, data_directory, monkeypatch):
    epa = Epa(monkeypatch)
    if failing == 'page':
        epa.serve_page(PAGE.read_text(), status=500)
    else:
        epa.responses[URLS[2022]] = (500, b'{"error": "synthetic"}', {'Content-Length': '22'})
    with pytest.raises(httpx.HTTPStatusError):
        tri_raw.acquire(data_directory)
    assert files_under(data_directory) == []


def test_acquire_keeps_a_recorded_file_and_refuses_unrecorded_or_missing(
        data_directory, monkeypatch, tmp_path):
    epa = Epa(monkeypatch)
    files = tri_raw.acquire(data_directory)
    ledger = paths.manifest_path(data_directory)
    recorded = ledger.read_bytes()

    epa.requests.clear()
    assert tri_raw.acquire(data_directory) == files
    assert epa.requests == [tri_raw.PAGE_URL]
    assert ledger.read_bytes() == recorded

    aside = tmp_path / 'aside.csv'
    files[2].rename(aside)
    epa.requests.clear()
    with pytest.raises(ValueError, match='recorded raw file is missing'):
        tri_raw.acquire(data_directory)
    assert epa.requests == [tri_raw.PAGE_URL]
    assert not files[2].exists()
    assert ledger.read_bytes() == recorded
    aside.rename(files[2])

    # Nothing is recorded under a later snapshot date yet.
    epa.serve_page(edited(('November 5, 2025', 'June 1, 2026')))
    later = tri_raw.raw_path(data_directory, 2024, LATER)
    for left, message in ((later, 'raw file is not recorded'),
                          (later.with_name(later.name + '.part'), 'interrupted')):
        left.parent.mkdir(parents=True, exist_ok=True)
        left.write_bytes(b'left by hand\n')
        epa.requests.clear()
        with pytest.raises(ValueError, match=message):
            tri_raw.acquire(data_directory)
        assert epa.requests == [tri_raw.PAGE_URL]
        assert left.read_bytes() == b'left by hand\n'
        assert ledger.read_bytes() == recorded
        left.unlink()


@pytest.mark.parametrize('state', ['changed', 'symlinked_directory', 'symlinked_file'])
def test_acquire_refuses_a_changed_or_symlinked_destination(state, data_directory, monkeypatch,
                                                            tmp_path):
    epa = Epa(monkeypatch)
    destination = tri_raw.raw_path(data_directory, 2024, RECORDED)
    outside = tmp_path / 'outside'
    outside.mkdir()
    if state == 'changed':
        tri_raw.acquire(data_directory)
        destination.write_bytes(b'changed\n')
        message = 'raw file changed'
    elif state == 'symlinked_directory':
        destination.parent.parent.parent.mkdir(parents=True)
        destination.parent.parent.symlink_to(outside, target_is_directory=True)
        message = 'symlink'
    else:
        destination.parent.mkdir(parents=True)
        (outside / 'target.csv').write_bytes(b'outside\n')
        destination.symlink_to(outside / 'target.csv')
        message = 'symlink'
    epa.requests.clear()
    with pytest.raises(ValueError, match=message):
        tri_raw.acquire(data_directory)
    assert epa.requests == [tri_raw.PAGE_URL]
    assert sorted(path.name for path in outside.iterdir()) == (
        [] if state != 'symlinked_file' else ['target.csv'])


def test_import_file_records_a_proxy_retrieval_time(data_directory, tmp_path):
    original = tmp_path / 'download (1).csv'
    original.write_bytes(BODIES[2023])
    path = tri_raw.import_file(data_directory, 2023, original,
                               processed_as_of=date(2025, 11, 5))
    assert path.name == tri_raw.file_name(2023)
    entry = manifest.entry_for(paths.manifest_path(data_directory), path)
    assert (entry.client, entry.source_url, entry.proxies, entry.through_date) == (
        'manual-import', None, ('retrieved_at',), '2025-11-05')


def test_import_file_publishes_the_exact_bytes_under_the_snapshot_date(data_directory,
                                                                       tmp_path):
    original = tmp_path / 'download (1).csv'
    original.write_bytes(BODIES[2023])
    path = tri_raw.import_file(data_directory, 2023, original, processed_as_of=RECORDED)
    assert path == tri_raw.raw_path(data_directory, 2023, RECORDED)
    assert path.read_bytes() == original.read_bytes() == BODIES[2023]
    entry = manifest.entry_for(paths.manifest_path(data_directory), path)
    assert entry.path == 'epa_tri/basic/2023/2025-11-05/2023_us.csv'
    assert (entry.sha256, entry.size) == (manifest.sha256_file(original), len(BODIES[2023]))
    assert entry.client_version == version('embedding-data')
    assert_retrieved_now(entry)
    assert files_under(data_directory) == [
        'raw/epa_tri/basic/2023/2025-11-05/2023_us.csv', 'raw/manifest.jsonl']


def test_import_file_refuses_other_years_existing_paths_and_symlinks(data_directory, tmp_path):
    original = tmp_path / 'download.csv'
    original.write_bytes(BODIES[2023])
    for year in (2021, 2025):
        with pytest.raises(ValueError):
            tri_raw.import_file(data_directory, year, original, processed_as_of=RECORDED)
    link = tmp_path / 'link.csv'
    link.symlink_to(original)
    with pytest.raises(ValueError):
        tri_raw.import_file(data_directory, 2023, link, processed_as_of=RECORDED)
    assert not data_directory.exists()

    published = tri_raw.import_file(data_directory, 2023, original, processed_as_of=RECORDED)
    ledger = paths.manifest_path(data_directory)
    recorded = ledger.read_bytes()
    other = tmp_path / 'other.csv'
    other.write_bytes(b'other bytes\n')
    for source in (original, other):
        with pytest.raises(ValueError):
            tri_raw.import_file(data_directory, 2023, source, processed_as_of=RECORDED)
    assert published.read_bytes() == BODIES[2023]
    assert ledger.read_bytes() == recorded

    destination = tri_raw.raw_path(data_directory, 2024, RECORDED)
    left = destination.with_name(destination.name + '.part')
    left.parent.mkdir(parents=True)
    left.write_bytes(b'interrupted\n')
    with pytest.raises(ValueError):
        tri_raw.import_file(data_directory, 2024, other, processed_as_of=RECORDED)
    assert left.read_bytes() == b'interrupted\n'
    assert not destination.exists()
    assert ledger.read_bytes() == recorded

    outside = tmp_path / 'outside'
    outside.mkdir()
    tri_raw.snapshot_dir(data_directory, 2022, RECORDED).parent.symlink_to(
        outside, target_is_directory=True)
    with pytest.raises(ValueError):
        tri_raw.import_file(data_directory, 2022, other, processed_as_of=RECORDED)
    assert list(outside.iterdir()) == []
    assert ledger.read_bytes() == recorded


@pytest.mark.parametrize('kind', ['missing', 'directory', 'empty'])
def test_import_file_refuses_a_non_regular_or_empty_original(kind, data_directory, tmp_path):
    original = tmp_path / 'download.csv'
    if kind == 'directory':
        original.mkdir()
    elif kind == 'empty':
        original.write_bytes(b'')
    with pytest.raises(ValueError):
        tri_raw.import_file(data_directory, 2023, original, processed_as_of=RECORDED)
    assert not data_directory.exists()


def test_import_file_refuses_an_existing_destination_before_copying(data_directory, tmp_path):
    original = tmp_path / 'download.csv'
    original.write_bytes(BODIES[2023])
    destination = tri_raw.raw_path(data_directory, 2023, RECORDED)
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b'placed by hand\n')
    with pytest.raises(ValueError, match='raw destination already exists'):
        tri_raw.import_file(data_directory, 2023, original, processed_as_of=RECORDED)
    assert destination.read_bytes() == b'placed by hand\n'
    assert files_under(data_directory) == [destination.relative_to(data_directory).as_posix()]


def test_import_file_refuses_a_recorded_path_whose_file_is_gone(data_directory, tmp_path):
    original = tmp_path / 'download.csv'
    original.write_bytes(BODIES[2023])
    published = tri_raw.import_file(data_directory, 2023, original, processed_as_of=RECORDED)
    ledger = paths.manifest_path(data_directory)
    recorded = ledger.read_bytes()
    published.unlink()
    with pytest.raises(ValueError, match='already recorded'):
        tri_raw.import_file(data_directory, 2023, original, processed_as_of=RECORDED)
    assert files_under(data_directory) == ['raw/manifest.jsonl']
    assert ledger.read_bytes() == recorded


def test_import_file_refuses_a_copy_that_differs_from_the_original(data_directory, tmp_path,
                                                                   monkeypatch):
    original = tmp_path / 'download.csv'
    original.write_bytes(BODIES[2023])

    def corrupt(source, output):
        output.write(b'not the original\n')

    monkeypatch.setattr(shutil, 'copyfileobj', corrupt)
    with pytest.raises(ValueError):
        tri_raw.import_file(data_directory, 2023, original, processed_as_of=RECORDED)
    assert files_under(data_directory) == []


@pytest.mark.parametrize('command', ['acquire', 'import'])
def test_a_symlinked_manifest_is_refused(command, data_directory, monkeypatch, tmp_path):
    epa = Epa(monkeypatch)
    outside = tmp_path / 'outside.jsonl'
    outside.write_bytes(b'')
    ledger = paths.manifest_path(data_directory)
    ledger.parent.mkdir(parents=True)
    ledger.symlink_to(outside)
    original = tmp_path / 'download.csv'
    original.write_bytes(BODIES[2023])
    with pytest.raises(ValueError, match='symlink'):
        if command == 'acquire':
            tri_raw.acquire(data_directory)
        else:
            tri_raw.import_file(data_directory, 2023, original, processed_as_of=RECORDED)
    assert epa.requests == ([tri_raw.PAGE_URL] if command == 'acquire' else [])
    assert outside.read_bytes() == b''
    assert files_under(data_directory) == ['raw/manifest.jsonl']


@pytest.mark.parametrize('command', ['acquire', 'import'])
def test_a_partial_that_appears_after_the_checks_is_never_overwritten(
        command, data_directory, monkeypatch, tmp_path):
    epa = Epa(monkeypatch)
    destination = tri_raw.raw_path(data_directory, 2022, RECORDED)
    left = destination.with_name(destination.name + '.part')
    left.parent.mkdir(parents=True)
    left.write_bytes(b'another writer\n')
    original = tmp_path / 'download.csv'
    original.write_bytes(BODIES[2022])
    # Each patch hides the planted partial from the checks, as a racing writer would.
    if command == 'acquire':
        monkeypatch.setattr(tri_raw, '_present', lambda data_dir, file: False)
    else:
        monkeypatch.setattr(tri_raw, 'occupied', lambda file: False)
    with pytest.raises(FileExistsError):
        if command == 'acquire':
            tri_raw.acquire(data_directory)
        else:
            tri_raw.import_file(data_directory, 2022, original, processed_as_of=RECORDED)
    assert epa.requests == ([tri_raw.PAGE_URL] if command == 'acquire' else [])
    assert left.read_bytes() == b'another writer\n'
    assert files_under(data_directory) == [left.relative_to(data_directory).as_posix()]


def plant_file(destination: Path, outside: Path) -> None:
    destination.write_bytes(b'another writer\n')


def symlink_snapshot(destination: Path, outside: Path) -> None:
    moved = outside / 'snapshot'
    destination.parent.rename(moved)
    destination.parent.symlink_to(moved, target_is_directory=True)


@pytest.mark.parametrize('race,message', [
    (plant_file, 'appeared during publication'),
    (symlink_snapshot, 'symlink'),
], ids=['planted_file', 'symlinked_snapshot'])
def test_publication_checks_the_destination_again(race, message, data_directory, tmp_path,
                                                  monkeypatch):
    original = tmp_path / 'download.csv'
    original.write_bytes(BODIES[2023])
    destination = tri_raw.raw_path(data_directory, 2023, RECORDED)
    outside = tmp_path / 'outside'
    outside.mkdir()
    check, raced = manifest.check_appendable, []

    def check_then_race(manifest_path, entries):
        check(manifest_path, entries)
        if not raced:
            raced.append(True)
            race(destination, outside)

    monkeypatch.setattr(manifest, 'check_appendable', check_then_race)
    with pytest.raises(ValueError, match=message):
        tri_raw.import_file(data_directory, 2023, original, processed_as_of=RECORDED)
    assert not paths.manifest_path(data_directory).exists()
    if race is plant_file:
        assert destination.read_bytes() == b'another writer\n'
        assert files_under(data_directory) == [destination.relative_to(data_directory).as_posix()]
    else:
        assert list((outside / 'snapshot').iterdir()) == []


def seed(data_directory: Path, tmp_path: Path, when: date) -> dict[int, Path]:
    '''Import a distinct synthetic file for each window year under one snapshot date.'''
    published = {}
    for y in tri_raw.WINDOW:
        original = tmp_path / f'{when.isoformat()}-{y}.csv'
        original.write_bytes(f'{when.isoformat()} {y}\n'.encode())
        published[y] = tri_raw.import_file(data_directory, y, original, processed_as_of=when)
    return published


def test_snapshot_selection_ignores_other_dates(data_directory, tmp_path):
    for when in (date(2025, 11, 5), date(2026, 6, 1)):
        seed(data_directory, tmp_path, when)
    assert tri_raw.select_files(data_directory, date(2025, 11, 5)) == {
        y: tri_raw.raw_path(data_directory, y, date(2025, 11, 5)) for y in tri_raw.WINDOW}

    extra = tri_raw.snapshot_dir(data_directory, 2023, date(2025, 11, 5)) / 'extra.csv'
    extra.write_bytes(b'extra\n')
    with pytest.raises(ValueError, match='missing or extra raw file'):
        tri_raw.select_files(data_directory, date(2025, 11, 5))
    extra.unlink()

    missing = tri_raw.raw_path(data_directory, 2024, date(2025, 11, 5))
    aside = tmp_path / 'aside.csv'
    missing.rename(aside)
    with pytest.raises(ValueError, match='missing or extra raw file'):
        tri_raw.select_files(data_directory, date(2025, 11, 5))
    aside.rename(missing)

    tri_raw.raw_path(data_directory, 2022, date(2025, 11, 5)).write_bytes(b'changed\n')
    with pytest.raises(ValueError, match='raw file changed'):
        tri_raw.select_files(data_directory, date(2025, 11, 5))


def test_snapshot_selection_reads_only_the_named_date(data_directory, tmp_path):
    first = seed(data_directory, tmp_path, RECORDED)
    later = seed(data_directory, tmp_path, LATER)
    assert tri_raw.select_files(data_directory, LATER) == later
    assert tri_raw.select_files(data_directory, RECORDED) == first


def leftover_part(file: Path, outside: Path) -> None:
    file.with_name(file.name + '.part').write_bytes(b'interrupted\n')


def renamed(file: Path, outside: Path) -> None:
    file.rename(file.with_name('other.csv'))


def directory_in_place(file: Path, outside: Path) -> None:
    file.unlink()
    file.mkdir()


def symlinked_snapshot(file: Path, outside: Path) -> None:
    moved = outside / 'snapshot'
    file.parent.rename(moved)
    file.parent.symlink_to(moved, target_is_directory=True)


def symlinked_file(file: Path, outside: Path) -> None:
    moved = outside / file.name
    file.rename(moved)
    file.symlink_to(moved)


@pytest.mark.parametrize('change,message', [
    (leftover_part, 'missing or extra raw file'),
    (renamed, 'missing or extra raw file'),
    (directory_in_place, 'missing or extra raw file'),
    (symlinked_snapshot, 'symlink'),
    (symlinked_file, 'symlink'),
], ids=['leftover_part', 'renamed', 'directory_in_place', 'symlinked_snapshot',
        'symlinked_file'])
def test_snapshot_selection_refuses_any_other_state(change, message, data_directory, tmp_path):
    files = seed(data_directory, tmp_path, RECORDED)
    outside = tmp_path / 'outside'
    outside.mkdir()
    change(files[2024], outside)
    with pytest.raises(ValueError, match=message):
        tri_raw.select_files(data_directory, RECORDED)


def test_snapshot_selection_refuses_an_empty_or_unrecorded_date(data_directory, tmp_path):
    seed(data_directory, tmp_path, RECORDED)
    with pytest.raises(ValueError, match='missing or extra raw file'):
        tri_raw.select_files(data_directory, LATER)
    for y in tri_raw.WINDOW:
        placed = tri_raw.raw_path(data_directory, y, LATER)
        placed.parent.mkdir(parents=True)
        placed.write_bytes(b'placed by hand\n')
    with pytest.raises(ValueError, match='raw file is not recorded'):
        tri_raw.select_files(data_directory, LATER)


def test_citations_are_verified_entries_through_json_sorted_by_path(data_directory, tmp_path):
    files = seed(data_directory, tmp_path, RECORDED)
    shuffled = {y: files[y] for y in (2024, 2022, 2023)}
    lines = [json.loads(line)
             for line in paths.manifest_path(data_directory).read_text().splitlines()]
    citations = tri_raw.citations(data_directory, shuffled)
    assert citations == sorted(lines, key=lambda line: line['path'])
    assert [citation['proxies'] for citation in citations] == [['retrieved_at']] * 3
    files[2023].write_bytes(b'changed\n')
    with pytest.raises(ValueError):
        tri_raw.citations(data_directory, files)
