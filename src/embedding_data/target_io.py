'''Strict inventories and exclusive staging for immutable target artifacts.'''

import json
import re
from dataclasses import asdict
from pathlib import Path

import polars as pl

from embedding_data import geography_references as gr
from embedding_data import manifest, paths

def relative_file(directory: Path, name: str) -> Path:
    '''Resolve a literal relative POSIX name without traversal or symlinks.'''
    if not name or name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError(f'unsafe relative file name: {name!r}')
    file = directory / name
    gr.safe_path(file, directory)
    if not file.resolve().is_relative_to(directory.resolve()):
        raise ValueError('file escapes inventory directory')
    return file


def stage(root: Path, run_id: str, data_dir: Path) -> tuple[Path, Path]:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', run_id):
        raise ValueError('unsafe run ID')
    final, staging = root / run_id, root / (run_id + '.part')
    for file in (final, staging):
        gr.safe_path(file, data_dir)
        if not file.resolve().is_relative_to(data_dir.resolve()):
            raise ValueError('run path escapes data directory')
        if gr.occupied(file):
            raise ValueError('run or staging name already exists')
    root.mkdir(parents=True, exist_ok=True)
    staging.mkdir()
    return final, staging


def write_json(file: Path, value: object) -> None:
    file.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                               allow_nan=False) + '\n', encoding='utf-8')


def file_record(file: Path) -> dict:
    record = {'sha256': manifest.sha256_file(file), 'size': file.stat().st_size}
    if file.suffix == '.parquet':
        frame = pl.scan_parquet(file)
        schema = frame.collect_schema()
        record.update(rows=frame.select(pl.len()).collect().item(), columns=list(schema),
                      schema={c: str(t) for c, t in schema.items()})
    return record


def inventory(directory: Path, names: list[str]) -> dict:
    if len(names) != len(set(names)) or 'outputs.json' in names:
        raise ValueError('duplicate or self-referential inventory')
    return {name: file_record(relative_file(directory, name)) for name in sorted(names)}


def verify_inventory(directory: Path, expected: dict, names: set[str]) -> None:
    gr.safe_path(directory, directory)
    actual_names = set()
    for file in directory.rglob('*'):
        gr.safe_path(file, directory)
        if file.is_file() and file.relative_to(directory).as_posix() != 'outputs.json':
            actual_names.add(file.relative_to(directory).as_posix())
    if set(expected) != names or actual_names != names:
        raise ValueError('missing or extra inventory files')
    for name in sorted(names):
        file = relative_file(directory, name)
        if (manifest.sha256_file(file) != expected[name].get('sha256')
                or file.stat().st_size != expected[name].get('size')):
            raise ValueError(f'{name}: inventory hash or size differs')
        actual = file_record(file)
        required = {'sha256', 'size'}
        if name.endswith('.parquet') and 'schema' in expected[name]:
            required.update(('rows', 'schema', 'columns'))
        if not required.issubset(expected[name]) or any(
                actual.get(key) != value for key, value in expected[name].items()):
            raise ValueError(f'{name}: inventory hash, size, rows or ordered schema differs')


def verify_raw(data_dir: Path, citations: list[dict]) -> list[dict]:
    manifest_file = paths.manifest_path(data_dir)
    gr.safe_path(manifest_file, data_dir)
    verified = []
    for citation in sorted(citations, key=lambda r: r['path']):
        file = relative_file(manifest_file.parent, citation['path'])
        if any(part.endswith('.part') for part in file.parts):
            raise ValueError('incomplete raw download cannot be cited')
        current = json.loads(json.dumps(asdict(manifest.entry_for(manifest_file, file))))
        if current != citation:
            raise ValueError(f'{file}: cited raw provenance changed')
        verified.append(current)
    return verified
