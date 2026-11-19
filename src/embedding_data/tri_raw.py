'''EPA TRI basic data files: the page catalog, the raw layout, acquisition, import and selection.

The basic data files page (PAGE_URL) states the date through which EPA processed reporting
forms ("processed as of"). It addresses each file through two option lists, reporting
years (`select_year`) and geographic areas (`select_geography`), and one URL template
literal in an inline script. `parse_page` reads the date and applies the template to the
`US` area and each window year. Raw files are immutable and live under
`raw/epa_tri/basic/<RY>/<processed-as-of, ISO>/<file name>`, so a later EPA snapshot lands
beside the earlier one. Each manifest entry puts the processed-as-of date in
`through_date`.

`acquire` is the only network call. `import_file` records a file that the owner downloaded
in a browser, with its retrieval time flagged as a proxy. `select_files` picks the one
recorded file of each window year under one snapshot date.
'''

import json
import os
import re
import shutil
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

from embedding_data import manifest, paths
from embedding_data.geography_references import occupied, safe_path

SOURCE = 'epa_tri'
WINDOW = (2022, 2023, 2024)
PAGE_URL = (
    'https://www.epa.gov/toxics-release-inventory-tri-program/'
    'tri-basic-data-files-calendar-years-1987-present'
)
# The page answered 200 to this descriptive user agent when Task 1 read it (2026-11-18).
USER_AGENT = 'embedding-data TRI acquisition'
TIMEOUT = httpx.Timeout(600.0, connect=15.0)
CHUNK_SIZE = 1024 * 1024

YEAR_SELECT = 'select_year'
GEOGRAPHY_SELECT = 'select_geography'
GEOGRAPHY = 'US'
YEAR_PLACEHOLDER = '${year}'
GEOGRAPHY_PLACEHOLDER = '${geography}'
MONTHS = {
    'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
    'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12,
}
PROCESSED_AS_OF = re.compile(
    r'processed as of:?\s*(' + '|'.join(MONTHS) + r')\s+(\d{1,2}),\s*(\d{4})(?!\d)')
TEMPLATE_LITERAL = re.compile(r'`([^`]*)`')


@dataclass(frozen=True)
class Catalog:
    processed_as_of: date
    urls: dict[int, str]


class _PageParser(HTMLParser):
    '''Collect the page's visible text, each script's body and each select's option values.'''

    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.scripts: list[str] = []
        self.options: list[tuple[str, str | None]] = []
        self.select: str | None = None
        self.raw_tag: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag in ('script', 'style'):
            self.raw_tag = tag
            if tag == 'script':
                self.scripts.append('')
        elif tag == 'select':
            self.select = attributes.get('id')
        elif tag == 'option' and self.select is not None:
            self.options.append((self.select, attributes.get('value')))

    def handle_endtag(self, tag: str) -> None:
        if tag == self.raw_tag:
            self.raw_tag = None
        elif tag == 'select':
            self.select = None

    def handle_data(self, data: str) -> None:
        if self.raw_tag == 'script':
            self.scripts[-1] += data
        elif self.raw_tag is None:
            self.text.append(data)


def _processed_as_of(text: str) -> date:
    '''The one date the page's "processed as of" sentences state.'''
    found = {
        date(int(year), MONTHS[month], int(day))
        for month, day, year in PROCESSED_AS_OF.findall(text)
    }
    if not found:
        raise ValueError('the page states no processed-as-of date')
    if len(found) > 1:
        raise ValueError('the page states two different processed-as-of dates')
    return found.pop()


def _template(scripts: list[str]) -> str:
    '''The one https epa.gov URL template literal that takes a year and a geography.'''
    templates = [
        literal for script in scripts for literal in TEMPLATE_LITERAL.findall(script)
        if YEAR_PLACEHOLDER in literal and GEOGRAPHY_PLACEHOLDER in literal
    ]
    if len(templates) != 1:
        raise ValueError(f'expected one download URL template, found {len(templates)}')
    parts = urlsplit(templates[0])
    host = parts.hostname or ''
    if parts.scheme != 'https' or not (host == 'epa.gov' or host.endswith('.epa.gov')):
        raise ValueError('the download URL template is not an https epa.gov URL')
    return templates[0]


def _require_once(options: list[tuple[str, str | None]], select: str, value: str) -> None:
    count = options.count((select, value))
    if count != 1:
        raise ValueError(f'{select} lists {value} {count} times, not once')


def parse_page(html: str, page_url: str) -> Catalog:
    '''The processed-as-of date and the U.S. file URL of each window year.'''
    parser = _PageParser()
    parser.feed(html)
    parser.close()
    processed_as_of = _processed_as_of(' '.join(' '.join(parser.text).split()))
    template = _template(parser.scripts)
    _require_once(parser.options, GEOGRAPHY_SELECT, GEOGRAPHY)
    urls = {}
    for year in WINDOW:
        _require_once(parser.options, YEAR_SELECT, str(year))
        url = template.replace(YEAR_PLACEHOLDER, str(year))
        urls[year] = urljoin(page_url, url.replace(GEOGRAPHY_PLACEHOLDER, GEOGRAPHY))
    return Catalog(processed_as_of=processed_as_of, urls=urls)


def file_name(year: int) -> str:
    '''The registered raw file name of a window year's U.S. file.

    This is the name that EPA gives the file: the download answers with
    `Content-Disposition: attachment; filename="<year>_us.csv"`, and a browser saves it
    under that name. It is not a name that this project invents. The registered name, not
    the local name of an imported file, decides where a file is published.
    '''
    if year not in WINDOW:
        raise ValueError('reporting year outside the window')
    return f'{year}_us.csv'


def snapshot_dir(data_dir: Path, year: int, processed_as_of: date) -> Path:
    return paths.raw_dir(data_dir, SOURCE) / 'basic' / str(year) / processed_as_of.isoformat()


def raw_path(data_dir: Path, year: int, processed_as_of: date) -> Path:
    return snapshot_dir(data_dir, year, processed_as_of) / file_name(year)


def make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    '''A client that asks EPA for the unencoded bytes of each file.'''
    return httpx.Client(
        follow_redirects=True,
        headers={'User-Agent': USER_AGENT, 'Accept-Encoding': 'identity'},
        timeout=TIMEOUT,
        transport=transport,
    )


def _partial(destination: Path) -> Path:
    return destination.with_name(destination.name + '.part')


def _recorded(manifest_path: Path, file: Path) -> bool:
    path = file.relative_to(manifest_path.parent).as_posix()
    return any(entry.path == path for entry in manifest.read_manifest(manifest_path))


def _verify(manifest_path: Path, file: Path) -> None:
    '''Refuse a raw file that the manifest does not record, or whose bytes changed.'''
    if not _recorded(manifest_path, file):
        raise ValueError('raw file is not recorded')
    try:
        manifest.entry_for(manifest_path, file)
    except ValueError:
        raise ValueError('raw file changed') from None


def _present(data_dir: Path, destination: Path) -> bool:
    '''Whether a recorded, intact file holds destination. Refuse every other occupied state.'''
    manifest_path = paths.manifest_path(data_dir)
    safe_path(destination, data_dir)
    if occupied(_partial(destination)):
        raise ValueError('interrupted raw download exists')
    if occupied(destination):
        _verify(manifest_path, destination)
        return True
    if _recorded(manifest_path, destination):
        raise ValueError('recorded raw file is missing')
    return False


def _describe(data_dir: Path, partial: Path, destination: Path,
              **provenance) -> manifest.ManifestEntry:
    '''The manifest entry of the bytes in partial, under destination's path.'''
    entry = manifest.describe_file(
        partial, partial.parent, retrieved_at=datetime.now(UTC), **provenance)
    raw_root = paths.manifest_path(data_dir).parent
    return replace(entry, path=destination.relative_to(raw_root).as_posix())


def _publish(data_dir: Path, partial: Path, destination: Path,
             entry: manifest.ManifestEntry) -> None:
    '''Link partial to destination without replacing anything, then record it.'''
    manifest_path = paths.manifest_path(data_dir)
    manifest.check_appendable(manifest_path, [entry])
    safe_path(destination, data_dir)
    if occupied(destination):
        raise ValueError('raw destination appeared during publication')
    os.link(partial, destination)
    manifest.append_entries(manifest_path, [entry])


def _download(client: httpx.Client, data_dir: Path, url: str, destination: Path,
              processed_as_of: date) -> None:
    '''Stream url into an exclusive `.part`, check its length, then publish and record it.'''
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = _partial(destination)
    output = partial.open('xb')  # If this fails, this call does not own the partial.
    try:
        with output, client.stream('GET', url) as response:
            response.raise_for_status()
            if response.headers.get('Content-Encoding', 'identity') != 'identity':
                raise ValueError('encoded download')
            expected = response.headers.get('Content-Length')
            if expected is None:
                raise ValueError('download has no Content-Length')
            # A recorded empty file would be kept by every later acquire, and import-file
            # refuses an occupied destination, so the year could never be filled.
            if int(expected) == 0:
                raise ValueError('empty download')
            for chunk in response.iter_raw(CHUNK_SIZE):
                output.write(chunk)
        if response.num_bytes_downloaded != int(expected):
            raise httpx.RemoteProtocolError(
                'download length differs from its Content-Length', request=response.request)
        entry = _describe(
            data_dir, partial, destination, client='httpx', client_version=version('httpx'),
            source_url=url, through_date=processed_as_of)
        _publish(data_dir, partial, destination, entry)
    finally:
        partial.unlink(missing_ok=True)


def acquire(data_dir: Path) -> list[Path]:
    '''Download each window year's U.S. file that is not on disk yet. The network command.

    The page fixes the snapshot date, so it is read first. Then every destination is
    checked before any download: a recorded, intact file is kept, and an unrecorded file,
    a recorded file that is missing or changed, a `.part` or a symlink is refused.
    '''
    with make_client() as client:
        page = client.get(PAGE_URL)
        page.raise_for_status()
        catalog = parse_page(page.text, str(page.url))
        destinations = {
            year: raw_path(data_dir, year, catalog.processed_as_of) for year in WINDOW
        }
        safe_path(paths.manifest_path(data_dir), data_dir)
        present = {year: _present(data_dir, destinations[year]) for year in WINDOW}
        for year in WINDOW:
            if not present[year]:
                _download(client, data_dir, catalog.urls[year], destinations[year],
                          catalog.processed_as_of)
    return [destinations[year] for year in WINDOW]


def import_file(data_dir: Path, year: int, original: Path, *, processed_as_of: date) -> Path:
    '''Record the exact bytes of a file that the owner downloaded in a browser. Offline.'''
    destination = raw_path(data_dir, year, processed_as_of)
    original = Path(original)
    if original.is_symlink() or not original.is_file():
        raise ValueError('import source is not a regular file')
    if original.stat().st_size == 0:
        raise ValueError('import source is empty')
    safe_path(paths.manifest_path(data_dir), data_dir)
    safe_path(destination, data_dir)
    partial = _partial(destination)
    if occupied(destination) or occupied(partial):
        raise ValueError('raw destination already exists')
    expected = manifest.sha256_file(original)
    destination.parent.mkdir(parents=True, exist_ok=True)
    output = partial.open('xb')  # If this fails, this call does not own the partial.
    try:
        with output, original.open('rb') as source:
            shutil.copyfileobj(source, output)
        entry = _describe(
            data_dir, partial, destination, client='manual-import',
            client_version=version('embedding-data'), proxies=('retrieved_at',),
            through_date=processed_as_of)
        if entry.sha256 != expected:
            raise ValueError('the copy differs from the original')
        _publish(data_dir, partial, destination, entry)
    finally:
        partial.unlink(missing_ok=True)
    return destination


def select_files(data_dir: Path, processed_as_of: date) -> dict[int, Path]:
    '''The one recorded, intact file of each window year under one snapshot date.'''
    manifest_path = paths.manifest_path(data_dir)
    selected = {}
    for year in WINDOW:
        directory = snapshot_dir(data_dir, year, processed_as_of)
        file = directory / file_name(year)
        safe_path(file, data_dir)
        if not directory.is_dir() or [entry.name for entry in directory.iterdir()] != [
                file.name] or not file.is_file():
            raise ValueError('missing or extra raw file')
        _verify(manifest_path, file)
        selected[year] = file
    return selected


def citations(data_dir: Path, files: dict[int, Path]) -> list[dict]:
    '''Verified manifest entries of files, as JSON reads them back, sorted by path.'''
    manifest_path = paths.manifest_path(data_dir)
    entries = [
        json.loads(json.dumps(asdict(manifest.entry_for(manifest_path, file))))
        for file in files.values()
    ]
    return sorted(entries, key=lambda entry: entry['path'])
