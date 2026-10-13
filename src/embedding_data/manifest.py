'''Append-only manifest of raw downloads (spec R1.4).

One JSON object per line and one line per raw file. Paths are POSIX paths relative
to the manifest's directory (data/raw), so the manifest survives moving the
project. Raw files are immutable, so a path is recorded once: a second entry for
the same path is refused rather than superseding the first. `proxies` names the
fields whose values were reconstructed after retrieval rather than recorded at it.
`through_date` is the submission through-date an OSHA ITA summary file's name carries.
'''

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path

@dataclass(frozen=True)
class ManifestEntry:
    path: str
    sha256: str
    size: int
    retrieved_at: str
    client: str
    client_version: str
    source_url: str | None = None
    collection: str | None = None
    extract_number: int | None = None
    samples: tuple[str, ...] = ()
    proxies: tuple[str, ...] = ()
    through_date: str | None = None


def sha256_file(file: Path) -> str:
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def describe_file(
    file: Path,
    raw_root: Path,
    *,
    retrieved_at: datetime,
    client: str,
    client_version: str,
    source_url: str | None = None,
    collection: str | None = None,
    extract_number: int | None = None,
    samples: Iterable[str] = (),
    proxies: Iterable[str] = (),
    through_date: date | None = None,
) -> ManifestEntry:
    '''Hash one raw file and pair it with where, when, and how it was retrieved.'''
    if retrieved_at.tzinfo is None:
        raise ValueError('retrieved_at must be timezone-aware')
    return ManifestEntry(
        path=file.relative_to(raw_root).as_posix(),
        sha256=sha256_file(file),
        size=file.stat().st_size,
        retrieved_at=retrieved_at.astimezone(UTC).isoformat(timespec='seconds'),
        client=client,
        client_version=client_version,
        source_url=source_url,
        collection=collection,
        extract_number=extract_number,
        samples=tuple(samples),
        proxies=tuple(proxies),
        through_date=None if through_date is None else through_date.isoformat(),
    )


def read_manifest(manifest_path: Path) -> list[ManifestEntry]:
    '''Every recorded raw file, in recording order; empty before the first download.'''
    if not manifest_path.exists():
        return []
    entries = []
    for line in manifest_path.read_text().splitlines():
        record = json.loads(line)
        record['samples'] = tuple(record['samples'])
        record['proxies'] = tuple(record['proxies'])
        entries.append(ManifestEntry(**record))
    return entries


def check_appendable(manifest_path: Path, entries: Iterable[ManifestEntry]) -> None:
    '''Refuse entries if any path is already recorded or repeated among them.'''
    recorded = {entry.path for entry in read_manifest(manifest_path)}
    appending = set()
    for entry in entries:
        if entry.path in recorded:
            raise ValueError(f'{entry.path} is already recorded in {manifest_path}')
        if entry.path in appending:
            raise ValueError(f'{entry.path} is repeated in this append')
        appending.add(entry.path)


def append_entries(manifest_path: Path, entries: Iterable[ManifestEntry]) -> None:
    '''Append entries, refusing all if any path is already recorded or repeated in this append.'''
    entries = list(entries)
    if not entries:
        return
    check_appendable(manifest_path, entries)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open('a') as stream:
        stream.writelines(json.dumps(asdict(entry)) + '\n' for entry in entries)


def recorded_entry_for(manifest_path: Path, raw_file: Path) -> ManifestEntry:
    '''Find provenance even when the file is absent; never use this to cite bytes.'''
    path = raw_file.relative_to(manifest_path.parent).as_posix()
    matches = [item for item in read_manifest(manifest_path) if item.path == path]
    if not matches:
        raise KeyError(f'{path} is not recorded in {manifest_path}')
    if len(matches) != 1:
        raise ValueError(f'{path} is recorded more than once in {manifest_path}')
    return matches[0]

def entry_for(manifest_path: Path, raw_file: Path) -> ManifestEntry:
    '''Return a citation only after verifying the file's current bytes.'''
    entry = recorded_entry_for(manifest_path, raw_file)
    actual = sha256_file(raw_file)
    if actual != entry.sha256:
        raise ValueError(
            f'{entry.path}: SHA-256 {actual[:12]}... differs from the '
            f'{entry.sha256[:12]}... recorded in {manifest_path}; the raw file has '
            'changed since it was downloaded'
        )
    if raw_file.stat().st_size != entry.size:
        raise ValueError(f'{entry.path}: size differs from its manifest entry')
    return entry
