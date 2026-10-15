import os
import shutil
import tempfile
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import httpx
import polars as pl

from embedding_data import geography_parsers as gp
from embedding_data import ita_references, manifest, paths
from embedding_data.osha_benchmark_download import USER_AGENT, download

@dataclass(frozen=True)
class Reference:
    kind: str
    url: str
    relative: str
    edition: str
    sha256: str
    size: int
    downloadable: bool = True
    fixture: bool = False
    state_scope: frozenset[str] = gp.SCOPE


REGISTRY = {
    'states_2025': Reference(
        'states_2025', 'https://www2.census.gov/programs-surveys/popest/geographies/2025/'
        'state-geocodes-v2025.xlsx', 'geography/2025/state-geocodes-v2025.xlsx', '2025',
        '327c7fa3dfeb6526b20cd3d1cef7f471ec08316e92b183f12c5b168bfed7da84', 14700),
    'counties_2025': Reference(
        'counties_2025', 'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/'
        '2025_Gazetteer/2025_Gaz_counties_national.zip',
        'geography/2025/2025_Gaz_counties_national.zip', '2025',
        '4c90d0f805779923b5958ab13d0c1e9b99fe4932b786bfcf75dd739bb2dcb4ea', 138993),
    'cbsa_2023': Reference(
        'cbsa_2023', 'https://www2.census.gov/programs-surveys/metro-micro/geographies/'
        'reference-files/2023/delineation-files/list1_2023.xlsx',
        'geography/2023/list1_2023.xlsx', 'July 2023',
        '952c4b1e78acbb54e6ec9412434b7602fedacbf021736351a63c181bdb753629', 143798),
    'hud_2025q4': Reference(
        'hud_2025q4', ita_references.HUD_SOURCE, 'hud/2025Q4/ZIP-COUNTY_122025.xlsx', '2025Q4',
        '554379b618f21380bed6777a9c69845ac138843c1a57f951886d605bc9611c68', 2462769,
        downloadable=False),
}


def occupied(file):
    return file.exists() or file.is_symlink()


def safe_path(file, data_dir):
    root, file = Path(data_dir).absolute(), Path(file).absolute()
    if not file.is_relative_to(root):
        raise ValueError('registered destination escapes data directory')
    for candidate in [root, *file.parents, file]:
        if candidate.is_relative_to(root) and candidate.is_symlink():
            raise ValueError(f'{candidate}: symlink in registered destination')


def reference_path(data_dir, reference):
    return ita_references.reference_path(data_dir, reference.relative)


def verify_pin(file, reference):
    if file.is_symlink() or file.stat().st_size != reference.size or (
            manifest.sha256_file(file) != reference.sha256):
        raise ValueError(f'{reference.kind}: original differs from registered bytes; '
                         'record a distinct source identity and decision')


def preflight(data_dir, registry):
    if set(registry) != set(REGISTRY):
        raise ValueError('geography requires all four registered reference identities')
    safe_path(paths.manifest_path(data_dir), data_dir)
    result = {}
    for kind, reference in registry.items():
        file = reference_path(data_dir, reference)
        safe_path(file, data_dir)
        partial = file.with_name(file.name + '.part')
        if occupied(partial):
            raise ValueError(f'{kind}: occupied reference partial')
        result[kind] = ita_references.existing_reference(data_dir, file)
        if result[kind]:
            verify_pin(file, reference)
    return result


def parse_reference(file, reference):
    verify_pin(file, reference)
    if reference.kind == 'counties_2025':
        return {'counties': gp.parse_counties(file)}
    if reference.kind == 'hud_2025q4':
        # read_hud's GEOID variant requires the registered workbook basename.
        with tempfile.TemporaryDirectory() as directory:
            logical = Path(directory) / Path(reference.relative).name
            shutil.copyfile(file, logical)
            verify_pin(logical, reference)
            return {'hud': ita_references.read_hud(logical)}
    raw = pl.read_excel(file, has_header=False, drop_empty_rows=False,
                        read_options={'dtypes': 'string'})
    if reference.kind == 'states_2025':
        return gp.parse_states(raw, scope=reference.state_scope)
    if reference.kind == 'cbsa_2023':
        return {'members': gp.parse_members(raw)}
    raise ValueError('unknown geography reference parser')


def publish_original(data_dir, reference, original, *, imported):
    file = reference_path(data_dir, reference)
    if original.is_symlink():
        raise ValueError('import source must be original bytes, not a symlink')
    verify_pin(original, reference)
    parse_reference(original, reference)
    if ita_references.existing_reference(data_dir, file):
        verify_pin(file, reference)
        return file
    citation = manifest.describe_file(
        original, original.parent, retrieved_at=datetime.now(UTC),
        client='manual-import' if imported else 'httpx',
        client_version=version('embedding-data') if imported else version('httpx'),
        source_url=reference.url, proxies=('retrieved_at',) if imported else ())
    citation = replace(
        citation, path=file.relative_to(paths.manifest_path(data_dir).parent).as_posix())
    if (citation.sha256, citation.size) != (reference.sha256, reference.size):
        raise ValueError('original changed during validation')
    manifest.check_appendable(paths.manifest_path(data_dir), [citation])
    safe_path(file, data_dir)
    file.parent.mkdir(parents=True, exist_ok=True)
    partial = file.with_name(file.name + '.part')
    output = partial.open('xb')  # If this fails, this invocation does not own cleanup.
    try:
        with output, original.open('rb') as source:
            shutil.copyfileobj(source, output)
        verify_pin(partial, reference)
        safe_path(file, data_dir)
        if occupied(file):
            raise ValueError('reference destination appeared during publication')
        os.link(partial, file)
        manifest.append_entries(paths.manifest_path(data_dir), [citation])
    finally:
        partial.unlink(missing_ok=True)
    return file


def import_reference(data_dir, kind, original, *, registry=REGISTRY):
    if kind not in registry:
        raise ValueError('unknown registered geography identity')
    preflight(data_dir, registry)
    return publish_original(data_dir, registry[kind], Path(original), imported=True)


def make_client():
    return httpx.Client(http2=True, follow_redirects=True, timeout=120,
                        headers={'User-Agent': USER_AGENT})


def acquire(data_dir, *, registry=REGISTRY):
    existing = preflight(data_dir, registry)
    if any(not existing[k] and not r.downloadable for k, r in registry.items()):
        raise ValueError('import-reference hud_2025q4 ORIGINAL before acquiring references')
    if all(existing.values()):
        return [reference_path(data_dir, r) for r in registry.values()]
    with make_client() as client:
        for kind, reference in registry.items():
            if existing[kind]:
                continue
            with tempfile.TemporaryDirectory() as directory:
                original = Path(directory) / Path(reference.relative).name
                download(client, reference.url, original)
                publish_original(data_dir, reference, original, imported=False)
    return [reference_path(data_dir, r) for r in registry.values()]


def read_sources(data_dir, *, registry=REGISTRY):
    existing = preflight(data_dir, registry)
    missing = [k for k, present in existing.items() if not present]
    if missing:
        raise ValueError(
            f'missing manifested geography originals: {missing}; acquire/import first')
    result = {}
    for reference in registry.values():
        file = reference_path(data_dir, reference)
        manifest.entry_for(paths.manifest_path(data_dir), file)
        result.update(parse_reference(file, reference))
    return result
