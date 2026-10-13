'''Move raw files delivered before the raw manifest existed into its layout and record them.

Run once from the project root, after the Stage 1 commands are in place:

    uv run --locked python -m embedding_data.raw_backfill

Before Stage 1 each IPUMS set directory held one extract side by side
(extract.json, <name>.csv.gz, <name>.xml, and a converted <name>.parquet), and
data/raw/osha held its Parquet beside the CSV. This moves each extract's raw
files into <set>/<name>/, moves every Parquet under data/derived, and records
each raw file in data/raw/manifest.jsonl. Retrieval time and client version were
not recorded at download, so entries use the file's modification time and the
uv.lock version and flag both as proxies. Every check and hash runs before the
first file moves, and a tree already migrated is left as it is.
'''

import json
import re
import tomllib
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from embedding_data import manifest, osha_benchmark_download, paths

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)

LEGACY_DATA = re.compile(r'^(usa|cps)_(\d{5})\.csv\.gz$')
PROXIES = ('retrieved_at', 'client_version')


@dataclass(frozen=True)
class Move:
    source: Path
    destination: Path
    # A converted Parquet, rebuildable from raw files; any other move carries a raw file.
    derived: bool = False


def locked_version(lock_path: Path, package: str) -> str:
    '''The version uv.lock pins for package.'''
    for entry in tomllib.loads(lock_path.read_text())['package']:
        if entry['name'] == package:
            return entry['version']
    raise KeyError(f'{package} is not in {lock_path}')


def modified_at(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, UTC)


def plan_ipums_set(
    data_dir: Path, source: str, set_name: str, ipumspy_version: str,
) -> tuple[list[Move], list[manifest.ManifestEntry]]:
    '''Moves and manifest entries for one legacy set directory; none once it is migrated.'''
    set_dir = paths.raw_dir(data_dir, source) / set_name
    data_files = sorted(set_dir.glob('*.csv.gz'))
    if not data_files:
        return [], []
    if len(data_files) > 1:
        raise ValueError(f'{set_dir}: {len(data_files)} extracts share one extract.json')
    data = data_files[0]
    match = LEGACY_DATA.match(data.name)
    if match is None:
        raise ValueError(f'{data}: not an IPUMS extract file name')
    collection, number = match[1], int(match[2])
    name = data.name.removesuffix('.csv.gz')
    definition = set_dir / 'extract.json'
    codebook = set_dir / f'{name}.xml'
    for required in (definition, codebook):
        if not required.exists():
            raise FileNotFoundError(f'{required}: missing beside {data.name}')
    submitted = json.loads(definition.read_text())
    if (
        submitted['collection'] != collection
        or not submitted['description'].endswith(f': {set_name}')
    ):
        raise ValueError(f'{definition} does not define the {set_name} extract {name}')
    # The definition is written before submission; a dry run after the download rewrites it.
    if modified_at(definition) >= modified_at(data):
        raise ValueError(f'{definition} is newer than {data.name}: it may be a later dry run')

    raw_root = paths.manifest_path(data_dir).parent
    extract_dir = set_dir / name
    moves, entries = [], []
    for file in (definition, data, codebook):
        move = Move(file, extract_dir / file.name)
        entry = manifest.describe_file(
            file,
            raw_root,
            retrieved_at=modified_at(file),
            client='ipumspy',
            client_version=ipumspy_version,
            collection=collection,
            extract_number=number,
            samples=submitted['samples'],
            proxies=PROXIES,
        )
        moves.append(move)
        entries.append(replace(entry, path=move.destination.relative_to(raw_root).as_posix()))
    parquet = set_dir / f'{name}.parquet'
    if parquet.exists():
        destination = paths.derived_dir(data_dir, source) / set_name / parquet.name
        moves.append(Move(parquet, destination, derived=True))
    return moves, entries


def plan_osha(
    data_dir: Path, httpx_version: str, recorded: set[str],
) -> tuple[list[Move], list[manifest.ManifestEntry]]:
    '''Moves for the OSHA Parquet, and entries for OSHA downloads not yet recorded.'''
    raw = paths.raw_dir(data_dir, 'osha')
    raw_root = paths.manifest_path(data_dir).parent
    moves = [
        Move(parquet, paths.derived_dir(data_dir, 'osha') / parquet.name, derived=True)
        for parquet in sorted(raw.glob('*.parquet'))
    ]
    entries = []
    for url in (osha_benchmark_download.DICTIONARY_URL, osha_benchmark_download.CSV_URL):
        file = raw / osha_benchmark_download.file_name(url)
        if file.exists() and file.relative_to(raw_root).as_posix() not in recorded:
            entries.append(
                manifest.describe_file(
                    file,
                    raw_root,
                    retrieved_at=modified_at(file),
                    client='httpx',
                    client_version=httpx_version,
                    source_url=url,
                    proxies=PROXIES,
                )
            )
    return moves, entries


def occupied(move: Move) -> FileExistsError:
    '''Why move cannot go ahead and what to do; only a derived Parquet may be deleted.'''
    if move.derived:
        return FileExistsError(
            f'{move.destination} already exists, for example because `osha` converted the raw '
            f'CSV before this backfill ran. {move.source} is the legacy copy of a derived '
            f'Parquet and can be rebuilt from raw files: delete {move.source} (or '
            f'{move.destination}) and re-run. Nothing was moved.'
        )
    return FileExistsError(
        f'{move.destination} already exists; not moving the raw file {move.source} onto it. '
        'Raw files are never replaced: compare the two and resolve it by hand, then re-run. '
        'Nothing was moved.'
    )


def check_plan(
    moves: list[Move],
    entries: list[manifest.ManifestEntry],
    recorded: set[str],
    manifest_path: Path,
) -> None:
    '''Refuse the whole plan before the first move if appending or any move would fail.'''
    for entry in entries:
        if entry.path in recorded:
            raise ValueError(
                f'{entry.path} is already recorded in {manifest_path}; nothing was moved'
            )
    sources = {}
    for move in moves:
        if move.destination in sources:
            raise ValueError(
                f'{move.destination} is the destination of both {sources[move.destination]} '
                f'and {move.source}; nothing was moved'
            )
        sources[move.destination] = move.source
    for move in moves:
        if move.destination.exists():
            raise occupied(move)


def backfill(data_dir: Path, lock_path: Path) -> list[manifest.ManifestEntry]:
    '''Migrate a legacy raw tree and record its files; return the entries appended.'''
    manifest_path = paths.manifest_path(data_dir)
    recorded = {entry.path for entry in manifest.read_manifest(manifest_path)}
    ipumspy_version = locked_version(lock_path, 'ipumspy')
    moves, entries = [], []
    for source in ('acs', 'cps'):
        source_dir = paths.raw_dir(data_dir, source)
        if not source_dir.exists():
            continue
        for set_dir in sorted(path for path in source_dir.iterdir() if path.is_dir()):
            set_moves, set_entries = plan_ipums_set(
                data_dir, source, set_dir.name, ipumspy_version
            )
            moves += set_moves
            entries += set_entries
    osha_moves, osha_entries = plan_osha(data_dir, locked_version(lock_path, 'httpx'), recorded)
    moves += osha_moves
    entries += osha_entries

    check_plan(moves, entries, recorded, manifest_path)
    for move in moves:
        move.destination.parent.mkdir(parents=True, exist_ok=True)
        move.source.rename(move.destination)
    manifest.append_entries(manifest_path, entries)
    return entries


@app.command(help=__doc__.splitlines()[0])
def main(
    data_dir: Annotated[
        Path,
        typer.Option('--data-dir', help='Data root holding raw/ and derived/.'),
    ] = paths.DATA_DIR,
) -> None:
    entries = backfill(data_dir, paths.PROJECT_ROOT / 'uv.lock')
    for entry in entries:
        typer.echo(f'recorded {entry.path} ({entry.size:,} bytes)')
    typer.echo(f'{len(entries)} entries appended to {paths.manifest_path(data_dir)}')


if __name__ == '__main__':
    app()
