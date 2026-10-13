'''Shared IPUMS flow: preview a definition, or submit, download, and record an extract.

A dry run writes the definition under preview/. A real run gives every extract
its own raw directory, raw/<source>/<set>/<collection>_<number>/, holding the
submitted definition (extract.json) and the delivered .csv.gz and .xml. The
download is staged in <set>/<name>.part/ and renamed to <set>/<name>/ only once
all three files are there, so a .part directory is an interrupted delivery: not
recorded, and not a delivery. Only those three files are recorded in the raw
manifest; anything else in the directory is not. Extract numbers are never
reused, so a re-run writes a new directory and never overwrites or reconverts an
earlier one.
'''

import json
from dataclasses import replace
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import typer
from ipumspy import IpumsApiClient, MicrodataExtract

from embedding_data import manifest, paths

def extract_name(collection: str, number: int) -> str:
    '''IPUMS names an extract's files <collection>_<five-digit number>, e.g. usa_00001.'''
    return f'{collection}_{number:05d}'


def write_definition(definition: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(definition, indent=2))
    return path


def write_preview(extract: MicrodataExtract, data_dir: Path, source: str, set_name: str) -> Path:
    '''Write the definition a real run would submit; previews are overwritten freely.'''
    preview = paths.preview_dir(data_dir, source) / set_name / 'extract.json'
    return write_definition(extract.build(), preview)


def deliver(
    client: IpumsApiClient,
    extract: MicrodataExtract,
    data_dir: Path,
    source: str,
    set_name: str,
) -> Path:
    '''Submit an extract, stage its download, move it into its own raw directory, and record it.'''
    client.submit_extract(extract)
    typer.echo(f'{set_name}: submitted extract {extract.extract_id}, waiting')
    set_dir = paths.raw_dir(data_dir, source) / set_name
    name = extract_name(extract.collection, extract.extract_id)
    extract_dir = set_dir / name
    staging = set_dir / f'{name}.part'
    if extract_dir.exists():
        raise FileExistsError(
            f'{extract_dir} is an earlier delivery; raw files are never replaced'
        )
    if staging.exists():
        raise FileExistsError(
            f'{staging} is an interrupted delivery of this extract; not reusing it'
        )
    set_dir.mkdir(parents=True, exist_ok=True)
    staging.mkdir()
    definition = extract.build()
    write_definition(definition, staging / 'extract.json')
    client.wait_for_extract(extract)
    client.download_extract(extract, download_dir=staging)
    retrieved_at = datetime.now(UTC)

    delivered = ['extract.json', f'{name}.csv.gz', f'{name}.xml']
    for file_name in delivered:
        if not (staging / file_name).exists():
            raise FileNotFoundError(
                f'{staging / file_name}: not delivered; {staging} is incomplete'
            )

    # Hash in staging and check the manifest first, so only the rename-to-append gap remains.
    manifest_path = paths.manifest_path(data_dir)
    raw_root = manifest_path.parent
    entries = [
        replace(
            manifest.describe_file(
                staging / file_name,
                raw_root,
                retrieved_at=retrieved_at,
                client='ipumspy',
                client_version=version('ipumspy'),
                collection=extract.collection,
                extract_number=extract.extract_id,
                samples=definition['samples'],
            ),
            path=(extract_dir / file_name).relative_to(raw_root).as_posix(),
        )
        for file_name in sorted(delivered)
    ]
    manifest.check_appendable(manifest_path, entries)
    staging.rename(extract_dir)
    manifest.append_entries(manifest_path, entries)
    return extract_dir


def parquet_path(data_dir: Path, source: str, set_name: str, csv_gz: Path) -> Path:
    '''Where the Parquet converted from a delivered .csv.gz goes, outside raw/.'''
    name = csv_gz.name.removesuffix('.csv.gz')
    return paths.derived_dir(data_dir, source) / set_name / f'{name}.parquet'
