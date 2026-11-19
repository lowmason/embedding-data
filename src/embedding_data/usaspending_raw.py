'''Acquire and register USAspending contract-subaward ZIP downloads (Stage 14).

`acquire` asks USAspending for one fiscal year of contract subawards, waits until the file
is ready and downloads it. `import_file` registers a ZIP that the owner downloaded in a
browser. Both publish the bytes as delivered under
`raw/usaspending/subcontracts/<snapshot>/FY<year>/` and append one manifest entry. Raw files
are never replaced. `select_files` returns the one verified file of each window year for a
snapshot. The USAspending API takes no key, so nothing here reads a credential.
'''

import json
import os
import re
import shutil
import time
import zipfile
from collections.abc import Iterable
from dataclasses import asdict, replace
from datetime import UTC, date, datetime
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from embedding_data import manifest, paths
from embedding_data.geography_references import occupied, safe_path

SOURCE = 'usaspending'
WINDOW = (2024, 2025, 2026)
API_ROOT = 'https://api.usaspending.gov'
REQUEST_PATH = '/api/v2/bulk_download/awards/'
STATUS_PATH = '/api/v2/download/status'
POLL_SECONDS = 30
MAX_POLLS = 480
TIMEOUT = httpx.Timeout(600.0, connect=15.0)
CHUNK_SIZE = 1024 * 1024
USER_AGENT = 'embedding-data USAspending acquisition'
SAFE_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.zip')
ZIP_SIGNATURE = b'PK\x03\x04'
POLLING_STATUSES = ('ready', 'running')
sleep = time.sleep


def fiscal_year_range(fiscal_year: int) -> tuple[date, date]:
    '''The first and last day of a federal fiscal year (October 1 to September 30).'''
    return date(fiscal_year - 1, 10, 1), date(fiscal_year, 9, 30)


def request_body(fiscal_year: int) -> dict:
    '''Contract subawards of one fiscal year by their own action date, all agencies.'''
    start, end = fiscal_year_range(fiscal_year)
    return {
        'filters': {
            'sub_award_types': ['procurement'],
            'date_type': 'action_date',
            'date_range': {'start_date': start.isoformat(), 'end_date': end.isoformat()},
            'agencies': [{'type': 'awarding', 'tier': 'toptier', 'name': 'All'}],
        },
        'file_format': 'csv',
    }


def snapshot_dir(data_dir: Path, snapshot: date, fiscal_year: int) -> Path:
    return (paths.raw_dir(data_dir, SOURCE) / 'subcontracts' / snapshot.isoformat()
            / f'FY{fiscal_year}')


def make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    '''A keyless client that follows redirects, ignores the environment and asks for bytes
    as stored.'''
    return httpx.Client(
        follow_redirects=True,
        trust_env=False,
        headers={'User-Agent': USER_AGENT, 'Accept-Encoding': 'identity'},
        timeout=TIMEOUT,
        transport=transport,
    )


def require_window(fiscal_year: int) -> None:
    if fiscal_year not in WINDOW:
        raise ValueError('fiscal year is outside the window')


def require_free_directory(data_dir: Path, directory: Path) -> None:
    '''The snapshot directory must be absent or an empty real directory with no symlink.'''
    safe_path(directory, data_dir)
    if occupied(directory) and (not directory.is_dir() or any(directory.iterdir())):
        raise ValueError('snapshot directory is occupied')


def is_zip(file: Path) -> bool:
    with file.open('rb') as stream:
        signature = stream.read(len(ZIP_SIGNATURE))
    return signature == ZIP_SIGNATURE and zipfile.is_zipfile(file)


def part_of(destination: Path) -> Path:
    return destination.with_name(destination.name + '.part')


def publish_partial(
    data_dir: Path,
    partial: Path,
    destination: Path,
    *,
    client: str,
    client_version: str,
    source_url: str | None,
    proxies: tuple[str, ...],
) -> Path:
    '''Record the `.part` bytes under the destination path, then link them there.

    The link publishes atomically and refuses a competing destination. The caller owns the
    `.part` and removes it.
    '''
    manifest_path = paths.manifest_path(data_dir)
    entry = manifest.describe_file(
        partial,
        partial.parent,
        retrieved_at=datetime.now(UTC),
        client=client,
        client_version=client_version,
        source_url=source_url,
        proxies=proxies,
    )
    entry = replace(entry, path=destination.relative_to(manifest_path.parent).as_posix())
    manifest.check_appendable(manifest_path, [entry])
    if occupied(destination):
        raise ValueError('raw destination already exists')
    os.link(partial, destination)
    manifest.append_entries(manifest_path, [entry])
    return destination


def json_object(response: httpx.Response) -> dict:
    answer = response.json()
    if not isinstance(answer, dict):
        raise ValueError('answer is not a JSON object')
    return answer


def request_download(client: httpx.Client, fiscal_year: int) -> str:
    '''POST the year's request and return the safe name of the file it will produce.'''
    response = client.post(API_ROOT + REQUEST_PATH, json=request_body(fiscal_year))
    response.raise_for_status()
    file_name = json_object(response).get('file_name')
    if not isinstance(file_name, str) or not SAFE_NAME.fullmatch(file_name):
        raise ValueError('download request has no usable file name')
    return file_name


def usable_url(url: object) -> str:
    '''An absolute https URL with a host, or a refusal before any request to it.'''
    if isinstance(url, str):
        parts = urlsplit(url)
        if parts.scheme == 'https' and parts.hostname:
            return url
    raise ValueError('download has no usable URL')


def wait_for_url(client: httpx.Client, file_name: str) -> str:
    '''Poll the status until the file is finished and return its URL.'''
    for poll in range(MAX_POLLS):
        if poll:
            sleep(POLL_SECONDS)
        response = client.get(API_ROOT + STATUS_PATH, params={'file_name': file_name})
        response.raise_for_status()
        answer = json_object(response)
        status = answer.get('status')
        if status == 'finished':
            return usable_url(answer.get('file_url'))
        if status == 'failed':
            raise ValueError('download request failed')
        if status not in POLLING_STATUSES:
            raise ValueError('unexpected download status')
    raise ValueError('download request timed out')


def download_zip(client: httpx.Client, url: str, partial: Path) -> None:
    '''Stream the file as delivered into a new `.part` and check its length and type.'''
    with client.stream('GET', url) as response:
        response.raise_for_status()
        length = response.headers.get('Content-Length')
        if length is None:
            raise ValueError('download has no Content-Length')
        if response.headers.get('Content-Encoding', 'identity').strip().lower() != 'identity':
            raise ValueError('encoded download')
        partial.parent.mkdir(parents=True, exist_ok=True)
        with partial.open('xb') as stream:
            for chunk in response.iter_raw(CHUNK_SIZE):
                stream.write(chunk)
        if response.num_bytes_downloaded != int(length):
            raise httpx.RemoteProtocolError(
                f'received {response.num_bytes_downloaded:,} of {int(length):,} bytes',
                request=response.request,
            )
    if not is_zip(partial):
        raise ValueError('download is not a ZIP file')


def acquire(data_dir: Path, fiscal_year: int, *, snapshot: date) -> Path:
    '''Request, wait for, download and record one fiscal year of contract subawards.

    This is the only network call of the module. It prints nothing.
    '''
    require_window(fiscal_year)
    directory = snapshot_dir(data_dir, snapshot, fiscal_year)
    require_free_directory(data_dir, directory)
    with make_client() as client:
        file_name = request_download(client, fiscal_year)
        url = wait_for_url(client, file_name)
        destination = directory / file_name
        partial = part_of(destination)
        try:
            download_zip(client, url, partial)
            return publish_partial(
                data_dir,
                partial,
                destination,
                client='httpx',
                client_version=version('httpx'),
                source_url=url,
                proxies=(),
            )
        finally:
            partial.unlink(missing_ok=True)


def import_file(data_dir: Path, fiscal_year: int, original: Path, *, snapshot: date) -> Path:
    '''Register a ZIP that the owner downloaded by hand, under its own name.'''
    require_window(fiscal_year)
    original = Path(original)
    if original.is_symlink() or not original.is_file():
        raise ValueError('original is not a regular file')
    if original.stat().st_size == 0:
        raise ValueError('original is empty')
    if not SAFE_NAME.fullmatch(original.name):
        raise ValueError('original name is not a safe .zip name')
    if not is_zip(original):
        raise ValueError('original is not a ZIP file')
    directory = snapshot_dir(data_dir, snapshot, fiscal_year)
    require_free_directory(data_dir, directory)
    destination = directory / original.name
    partial = part_of(destination)
    expected = manifest.sha256_file(original)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        with original.open('rb') as source, partial.open('xb') as target:
            shutil.copyfileobj(source, target)
        if manifest.sha256_file(partial) != expected:
            raise ValueError('SHA-256 changed while copying the original')
        return publish_partial(
            data_dir,
            partial,
            destination,
            client='manual-import',
            client_version=version('embedding-data'),
            source_url=None,
            proxies=('retrieved_at',),
        )
    finally:
        partial.unlink(missing_ok=True)


def select_files(data_dir: Path, snapshot: date) -> dict[int, Path]:
    '''The one manifested, hash-verified ZIP of each window year under `snapshot`.'''
    manifest_path = paths.manifest_path(data_dir)
    selected = {}
    for fiscal_year in WINDOW:
        directory = snapshot_dir(data_dir, snapshot, fiscal_year)
        safe_path(directory, data_dir)
        entries = list(directory.iterdir()) if directory.is_dir() else []
        if len(entries) != 1:
            raise ValueError('missing or extra raw file')
        (file,) = entries
        if file.is_symlink() or not file.is_file() or file.suffix != '.zip':
            raise ValueError('missing or extra raw file')
        try:
            manifest.recorded_entry_for(manifest_path, file)
        except KeyError:
            raise ValueError('raw file is not recorded') from None
        try:
            manifest.entry_for(manifest_path, file)
        except ValueError:
            raise ValueError('raw file changed') from None
        selected[fiscal_year] = file
    return selected


def citations(data_dir: Path, files: Iterable[Path]) -> list[dict]:
    '''Verified manifest entries of `files`, as JSON reads them back, sorted by path.'''
    manifest_path = paths.manifest_path(data_dir)
    entries = [
        json.loads(json.dumps(asdict(manifest.entry_for(manifest_path, file))))
        for file in files
    ]
    return sorted(entries, key=lambda entry: entry['path'])
