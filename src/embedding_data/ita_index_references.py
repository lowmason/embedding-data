'''Acquire, import, parse and verify the official Census NAICS index originals.

Each index file lists NAICS index entries beside the six-digit code they belong to, then
ends with cross-reference rows whose code is the marker `******`. The parser keeps every
row as delivered and counts the cross-references. Originals are immutable and pinned by
size and SHA-256.
'''

import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import polars as pl

from embedding_data import ita_references, manifest, paths
from embedding_data.ita_verification import normalize_key
from embedding_data.osha_benchmark_download import download, make_client

INDEX_VERSION = 'naics-index-v1'
CROSS_REFERENCE = '******'
INDEX_SCHEMA = {'vintage': pl.Int64, 'code': pl.String, 'entry': pl.String}


@dataclass(frozen=True)
class IndexReference:
    kind: str
    vintage: int
    url: str
    relative: str
    sheet: str
    header: tuple[str, str]
    sha256: str
    size: int
    expected_rows: int
    expected_cross_references: int


REGISTRY = {
    'naics_index_2012': IndexReference(
        kind='naics_index_2012',
        vintage=2012,
        url='https://www.census.gov/naics/2012NAICS/2012_NAICS_Index_File.xls',
        relative='naics/2012_NAICS_Index_File.xls',
        sheet='2012NAICS',
        header=('NAICS12', 'INDEX ITEM DESCRIPTION'),
        sha256='c688f221987497db897bbc0e641156997d4e2f528e4fd390a3ad983b13462a23',
        size=2_177_024,
        expected_rows=19_280,
        expected_cross_references=25,
    ),
    'naics_index_2017': IndexReference(
        kind='naics_index_2017',
        vintage=2017,
        url='https://www.census.gov/naics/2017NAICS/2017_NAICS_Index_File.xlsx',
        relative='naics/2017_NAICS_Index_File.xlsx',
        sheet='2017NAICS',
        header=('NAICS17', 'INDEX ITEM DESCRIPTION'),
        sha256='fb3b428300f698aa3d623e1a0edc50aaa3b729e930b7cdc22851825f487fb1ac',
        size=509_235,
        expected_rows=20_082,
        expected_cross_references=25,
    ),
    'naics_index_2022': IndexReference(
        kind='naics_index_2022',
        vintage=2022,
        url='https://www.census.gov/naics/2022NAICS/2022_NAICS_Index_File.xlsx',
        relative='naics/2022_NAICS_Index_File.xlsx',
        sheet='2022NAICS',
        header=('NAICS22', 'INDEX ITEM DESCRIPTION'),
        sha256='6506b37b9546dd9cec1f8b79e0b38b68e547a5cce5fd6f8332d35024dbd6cd63',
        size=499_358,
        expected_rows=20_398,
        expected_cross_references=25,
    ),
}


def reference_path(data_dir: Path, reference: IndexReference) -> Path:
    return ita_references.reference_path(data_dir, reference.relative)


def leaves_by_vintage(titles: pl.DataFrame) -> dict[int, frozenset[str]]:
    '''Six-digit codes of each vintage in the official structure titles.'''
    leaves = titles.filter(pl.col('code').str.len_chars().eq(6)).group_by('vintage').agg(
        pl.col('code')
    )
    return {vintage: frozenset(codes) for vintage, codes in leaves.iter_rows()}


def parse_index(file: Path, reference: IndexReference, leaves: frozenset[str]) -> pl.DataFrame:
    '''Every index row in file order, with the code stripped and the entry as delivered.'''
    sheets = pl.read_excel(file, sheet_id=0, has_header=False, read_options={'dtypes': 'string'})
    if list(sheets) != [reference.sheet] or sheets[reference.sheet].width != 2:
        raise ValueError(f'{reference.kind}: expected one sheet {reference.sheet} of two columns')
    raw = sheets[reference.sheet]
    first = None if raw.is_empty() else tuple(
        None if cell is None else cell.strip() for cell in raw.row(0)
    )
    if first != reference.header:
        raise ValueError(f'{reference.kind}: ambiguous or unexpected index header')
    body = raw.slice(1).select(
        vintage=pl.lit(reference.vintage, dtype=pl.Int64),
        code=pl.col(raw.columns[0]).str.strip_chars(),
        entry=pl.col(raw.columns[1]),
    )
    if body['code'].is_null().any() or body['code'].eq('').any():
        raise ValueError(f'{reference.kind}: null or blank index code')
    if body['entry'].is_null().any() or any(
        normalize_key(entry) == '' for entry in body['entry']
    ):
        raise ValueError(f'{reference.kind}: null or blank index entry')
    if not body['code'].is_in(leaves | {CROSS_REFERENCE}).all():
        raise ValueError(f'{reference.kind}: index code is neither a leaf nor a cross-reference')
    cross_references = body['code'].eq(CROSS_REFERENCE).sum()
    if body.height != reference.expected_rows:
        raise ValueError(f'{reference.kind}: index row count changed: {body.height}')
    if cross_references != reference.expected_cross_references:
        raise ValueError(f'{reference.kind}: cross-reference count changed: {cross_references}')
    return body


def check_pin(file: Path, reference: IndexReference) -> None:
    '''Refuse bytes that differ from the registered size or SHA-256.'''
    if file.stat().st_size != reference.size:
        raise ValueError(f'{reference.kind}: size differs from the registered original')
    if manifest.sha256_file(file) != reference.sha256:
        raise ValueError(f'{reference.kind}: SHA-256 differs from the registered original')


def preflight(data_dir: Path, registry: dict[str, IndexReference]) -> dict[str, bool]:
    '''Whether each original is present, after refusing every unsafe or unverifiable state.'''
    present = {}
    for kind, reference in registry.items():
        destination = reference_path(data_dir, reference)
        if destination.is_symlink() or destination.with_name(destination.name + '.part').exists():
            raise ValueError(f'{kind}: symlink or interrupted reference')
        present[kind] = ita_references.existing_reference(data_dir, destination)
        if present[kind]:
            check_pin(destination, reference)
    return present


def structure_leaves(data_dir: Path) -> dict[int, frozenset[str]]:
    return leaves_by_vintage(ita_references.read_titles(data_dir))


def publish_original(
    data_dir: Path,
    reference: IndexReference,
    original: Path,
    leaves: dict[int, frozenset[str]],
    *,
    imported: bool,
) -> Path:
    '''Pin-check and parse original, then publish it without replacing anything.'''
    destination = reference_path(data_dir, reference)
    check_pin(original, reference)
    parse_index(original, reference, leaves[reference.vintage])
    citation = manifest.describe_file(
        original,
        original.parent,
        retrieved_at=datetime.now(UTC),
        client='manual-import' if imported else 'httpx',
        client_version=version('embedding-data') if imported else version('httpx'),
        source_url=reference.url,
        proxies=('retrieved_at',) if imported else (),
    )
    citation = replace(
        citation, path=destination.relative_to(paths.manifest_path(data_dir).parent).as_posix()
    )
    manifest.check_appendable(paths.manifest_path(data_dir), [citation])
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + '.part')
    if partial.exists():
        raise ValueError('interrupted reference already exists')
    output = partial.open('xb')
    try:
        with output, original.open('rb') as source:
            shutil.copyfileobj(source, output)
        if manifest.sha256_file(partial) != citation.sha256:
            raise ValueError('SHA-256 changed while copying original')
        # Re-check immediately before the publish boundary; never overwrite a destination.
        if destination.exists() or destination.is_symlink():
            raise ValueError('reference destination appeared during import')
        # A hard link publishes atomically and refuses a competing destination.
        os.link(partial, destination)
        manifest.append_entries(paths.manifest_path(data_dir), [citation])
    finally:
        partial.unlink(missing_ok=True)
    return destination


def import_reference(
    data_dir: Path,
    kind: str,
    original: Path,
    *,
    registry: dict[str, IndexReference] = REGISTRY,
) -> Path:
    '''Record exact original bytes that the owner downloaded by hand.'''
    if kind not in registry:
        raise ValueError('unknown registered reference identity')
    reference = registry[kind]
    destination = reference_path(data_dir, reference)
    if preflight(data_dir, {kind: reference})[kind]:
        if manifest.sha256_file(original) != manifest.sha256_file(destination):
            raise ValueError('registered original already has different bytes')
        return destination
    leaves = structure_leaves(data_dir)
    return publish_original(data_dir, reference, original, leaves, imported=True)


def acquire(
    data_dir: Path, *, registry: dict[str, IndexReference] = REGISTRY
) -> list[Path]:
    '''Download only the missing originals. This is the only network call of the module.'''
    present = preflight(data_dir, registry)
    leaves = structure_leaves(data_dir) if not all(present.values()) else {}
    acquired = []
    with make_client() as client:
        for kind, reference in registry.items():
            if present[kind]:
                acquired.append(reference_path(data_dir, reference))
                continue
            with tempfile.TemporaryDirectory() as temporary:
                original = Path(temporary) / Path(reference.relative).name
                download(client, reference.url, original)
                acquired.append(
                    publish_original(data_dir, reference, original, leaves, imported=False)
                )
    return acquired


def read_index(
    data_dir: Path,
    titles: pl.DataFrame,
    *,
    registry: dict[str, IndexReference] = REGISTRY,
) -> pl.DataFrame:
    '''The index rows of every registered original: vintages ascending, file order within one.'''
    leaves = leaves_by_vintage(titles)
    frames = []
    for reference in sorted(registry.values(), key=lambda item: item.vintage):
        file = reference_path(data_dir, reference)
        manifest.entry_for(paths.manifest_path(data_dir), file)
        check_pin(file, reference)
        frames.append(parse_index(file, reference, leaves[reference.vintage]))
    return pl.concat(frames)


def citations(
    data_dir: Path, *, registry: dict[str, IndexReference] = REGISTRY
) -> list[dict]:
    '''Verified manifest entries of the registered originals, sorted by path.'''
    manifest_path = paths.manifest_path(data_dir)
    entries = [
        asdict(manifest.entry_for(manifest_path, reference_path(data_dir, reference)))
        for reference in registry.values()
    ]
    return sorted(entries, key=lambda entry: entry['path'])
