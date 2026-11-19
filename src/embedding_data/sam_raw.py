'''Acquire and register SAM.gov public monthly V2 UTF-8 entity extracts (Stage 14).

`acquire` requests one month's extract through the Entity Extracts API with the owner's key.
`import_file` registers an extract that the owner downloaded in a browser. Both publish the
ZIP as delivered under `raw/sam/entity-extract/public-monthly-v2/<YYYY-MM>/` and append one
manifest entry, whose `source_url` never holds the key. Raw files are never replaced.
`select_extract` returns the one verified extract of a month.
'''

import re
import shutil
from importlib.metadata import version
from pathlib import Path

from embedding_data import manifest, paths, sam_access, usaspending_raw
from embedding_data.geography_references import safe_path

SOURCE = 'sam'
NAME = re.compile(r'SAM_PUBLIC_UTF-8_MONTHLY_V2_(\d{4})(\d{2})\d{2}\.ZIP')
MONTH_PATTERN = re.compile(r'[0-9]{4}-(0[1-9]|1[0-2])')
PARTIAL = 'download.part'


def parse_month(value: str) -> str:
    '''`value` itself when it is `YYYY-MM` with a month from 01 to 12.'''
    if not MONTH_PATTERN.fullmatch(value):
        raise ValueError('month is not YYYY-MM')
    return value


def month_dir(data_dir: Path, month: str) -> Path:
    return paths.raw_dir(data_dir, SOURCE) / 'entity-extract' / 'public-monthly-v2' / month


def is_extract_of(name: str, month: str) -> bool:
    '''Whether `name` is a UTF-8 public monthly V2 extract name dated in `month`.'''
    match = NAME.fullmatch(name)
    return match is not None and f'{match[1]}-{match[2]}' == month


def acquire(data_dir: Path, month: str, *, credential: str) -> Path:
    '''Request, download and record the extract of `month`.

    This is the only network call of the module. It prints nothing.
    '''
    month = parse_month(month)
    directory = month_dir(data_dir, month)
    usaspending_raw.require_free_directory(data_dir, directory)
    directory.mkdir(parents=True, exist_ok=True)
    partial = directory / PARTIAL
    url = sam_access.extract_url(month)
    # Outside the try: a failed fetch has already removed a `.part` that it created, and a
    # `.part` that was already there is not this call's to remove.
    name = sam_access.fetch_extract(url, credential, partial)
    try:
        if not is_extract_of(name, month):
            raise ValueError('delivered extract is of another month')
        return usaspending_raw.publish_partial(
            data_dir,
            partial,
            directory / name,
            client='httpx',
            client_version=version('httpx'),
            source_url=url,
            proxies=(),
        )
    finally:
        partial.unlink(missing_ok=True)


def import_file(data_dir: Path, original: Path, *, month: str) -> Path:
    '''Register an extract that the owner downloaded by hand, under its own name.'''
    month = parse_month(month)
    original = Path(original)
    if original.is_symlink() or not original.is_file():
        raise ValueError('original is not a regular file')
    if original.stat().st_size == 0:
        raise ValueError('original is empty')
    if not is_extract_of(original.name, month):
        raise ValueError('original is not the UTF-8 extract of the month')
    if not usaspending_raw.is_zip(original):
        raise ValueError('original is not a ZIP file')
    directory = month_dir(data_dir, month)
    usaspending_raw.require_free_directory(data_dir, directory)
    destination = directory / original.name
    partial = usaspending_raw.part_of(destination)
    expected = manifest.sha256_file(original)
    directory.mkdir(parents=True, exist_ok=True)
    # Opened before the try: a `.part` that is already there is not this call's to remove.
    target = partial.open('xb')
    try:
        with target, original.open('rb') as source:
            shutil.copyfileobj(source, target)
        if manifest.sha256_file(partial) != expected:
            raise ValueError('SHA-256 changed while copying the original')
        return usaspending_raw.publish_partial(
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


def select_extract(data_dir: Path, month: str) -> Path:
    '''The one manifested, hash-verified extract of `month`.'''
    month = parse_month(month)
    manifest_path = paths.manifest_path(data_dir)
    directory = month_dir(data_dir, month)
    safe_path(directory, data_dir)
    entries = list(directory.iterdir()) if directory.is_dir() else []
    if len(entries) != 1:
        raise ValueError('missing or extra raw file')
    (file,) = entries
    if file.is_symlink() or not file.is_file() or not is_extract_of(file.name, month):
        raise ValueError('missing or extra raw file')
    try:
        manifest.recorded_entry_for(manifest_path, file)
    except KeyError:
        raise ValueError('raw file is not recorded') from None
    try:
        manifest.entry_for(manifest_path, file)
    except ValueError:
        raise ValueError('raw file changed') from None
    return file
