'''Offline conversion of immutable, manifest-verified IPUMS deliveries.'''

import gzip
import json
import os
import re
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl

from embedding_data import ipums_delivery, manifest, paths

# Alphanumeric codes and adjusted wages must survive CSV type inference.
ACS_SCHEMA_OVERRIDES = {
    'INDNAICS': pl.String,
    'OCCSOC': pl.String,
    'INCWAGE_CPIU_2010': pl.Float64,
}
CPS_SCHEMA_OVERRIDES = {'INCWAGE_CPIU_2010': pl.Float64}
CODE_COLUMNS = ['IND', 'OCC', 'INDLY', 'OCCLY']
SCHEMA_OVERRIDES = {'acs': ACS_SCHEMA_OVERRIDES, 'cps': CPS_SCHEMA_OVERRIDES}
COLLECTIONS = {'acs': 'usa', 'cps': 'cps'}
SAMPLE_SETS = {'acs': {'core', 'vintage', 'five_year'}, 'cps': {'monthly', 'asec'}}
INFER_SCHEMA_LENGTH = 100_000
COPY_BUFFER_SIZE = 16 * 1024 * 1024


def _safe_path(path: Path) -> None:
    '''Reject symlinks in both a path and its existing ancestors before any I/O.'''
    for component in (path, *path.absolute().parents):
        if component.is_symlink():
            raise ValueError(f'{component}: symlinks are not permitted for conversion')


def _preflight_destination(destination: Path, *, allow_existing: bool = False) -> None:
    _safe_path(destination)
    partial = destination.with_name(destination.name + '.part')
    _safe_path(partial)
    if partial.exists():
        raise FileExistsError(partial)
    for parent in destination.parents:
        if parent.exists() and not parent.is_dir():
            raise NotADirectoryError(parent)
    if destination.exists() and (not allow_existing or not destination.is_file()):
        raise FileExistsError(destination)


@contextmanager
def decompressed_csv(csv_gz: Path, directory: Path) -> Iterator[Path]:
    '''Own a unique decompressed CSV under the derived directory for this context.'''
    _safe_path(csv_gz)
    _safe_path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='ipums-', dir=directory) as scratch:
        csv_path = Path(scratch) / csv_gz.name.removesuffix('.gz')
        with gzip.open(csv_gz, 'rb') as src, csv_path.open('xb') as dst:
            shutil.copyfileobj(src, dst, length=COPY_BUFFER_SIZE)
        yield csv_path


def scan_delivered_csv(csv_path: Path, source: str) -> pl.LazyFrame:
    '''Apply the existing source-specific scanner and CPS code normalization.'''
    lf = pl.scan_csv(
        csv_path, schema_overrides=SCHEMA_OVERRIDES[source],
        infer_schema_length=INFER_SCHEMA_LENGTH,
    )
    if source == 'cps':
        codes = [column for column in CODE_COLUMNS if column in lf.collect_schema().names()]
        if codes:
            lf = lf.with_columns(pl.col(codes).cast(pl.String).str.zfill(4))
    return lf


def publish_parquet(frame: pl.LazyFrame, destination: Path) -> Path:
    '''Publish a validated Parquet without replacing an occupied final or partial.'''
    partial = destination.with_name(destination.name + '.part')
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    stream = partial.open('xb')
    try:
        with stream:
            frame.sink_parquet(stream, maintain_order=True, lazy=False)
        pl.scan_parquet(partial).select(pl.len()).collect()
        os.link(partial, destination)
    finally:
        partial.unlink(missing_ok=True)
    return destination


def convert(csv_gz: Path, parquet_path: Path, source: str) -> Path:
    '''Convert one delivered gzip CSV, preserving every occupied output path.'''
    if source not in COLLECTIONS:
        raise ValueError(f'unknown source: {source}')
    _safe_path(csv_gz)
    _preflight_destination(parquet_path)
    with decompressed_csv(csv_gz, parquet_path.parent) as csv:
        return publish_parquet(scan_delivered_csv(csv, source), parquet_path)


def _verify_delivery(data_dir: Path, directory: Path, collection: str) -> Path:
    '''Verify all three raw files and the definition/directory/manifest identity.'''
    name = directory.name
    number = int(name.removeprefix(collection + '_'))
    definition_path = directory / 'extract.json'
    csv_gz = directory / f'{name}.csv.gz'
    files = [definition_path, csv_gz, directory / f'{name}.xml']
    for file in files:
        _safe_path(file)
        if not file.is_file():
            raise FileNotFoundError(file)
    definition = json.loads(definition_path.read_text())
    samples = definition.get('samples')
    if (
        definition.get('collection') != collection
        or not isinstance(samples, dict)
        or not samples
    ):
        raise ValueError(f'{definition_path}: invalid collection or samples')
    for file in files:
        entry = manifest.entry_for(paths.manifest_path(data_dir), file)
        if (
            entry.collection != collection
            or entry.extract_number != number
            or set(entry.samples) != set(samples)
            or len(entry.samples) != len(samples)
        ):
            raise ValueError(f'{file}: delivery identity differs from its manifest entry')
    return csv_gz


def recover(data_dir: Path, source: str, sets: list[str]) -> list[Path]:
    '''Verify all selected complete deliveries before creating any missing Parquet.'''
    if source not in COLLECTIONS:
        raise ValueError(f'unknown source: {source}')
    if not sets or set(sets).difference(SAMPLE_SETS[source]):
        raise ValueError(f'unknown or empty {source} sets')
    collection = COLLECTIONS[source]
    _safe_path(paths.manifest_path(data_dir))
    pending = []
    for set_name in dict.fromkeys(sets):
        set_dir = paths.raw_dir(data_dir, source) / set_name
        _safe_path(set_dir)
        deliveries = []
        if set_dir.exists():
            deliveries = sorted(
                directory for directory in set_dir.iterdir()
                if re.fullmatch(rf'{collection}_[0-9]+', directory.name)
            )
        if not deliveries:
            raise ValueError(f'{set_dir}: no complete deliveries found')
        for directory in deliveries:
            _safe_path(directory)
            if not directory.is_dir():
                raise NotADirectoryError(directory)
            csv_gz = _verify_delivery(data_dir, directory, collection)
            destination = ipums_delivery.parquet_path(data_dir, source, set_name, csv_gz)
            _preflight_destination(destination, allow_existing=True)
            if not destination.exists():
                pending.append((csv_gz, destination))
    return [convert(csv_gz, destination, source) for csv_gz, destination in pending]
