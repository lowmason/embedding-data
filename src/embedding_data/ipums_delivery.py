'''Shared IPUMS flow: preview a definition, or submit, download, and record an extract.

A dry run writes the definition under preview/. A real run gives every extract
its own raw directory, raw/<source>/<set>/<collection>_<number>/, holding the
submitted definition (extract.json) and the delivered .csv.gz and .xml, and
records each file in the raw manifest. Extract numbers are never reused, so a
re-run writes a new directory and never overwrites or reconverts an earlier one.
'''

import json
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
    '''Submit and download an extract into its own new raw directory, then record its files.'''
    client.submit_extract(extract)
    typer.echo(f'{set_name}: submitted extract {extract.extract_id}, waiting')
    set_dir = paths.raw_dir(data_dir, source) / set_name
    set_dir.mkdir(parents=True, exist_ok=True)
    extract_dir = set_dir / extract_name(extract.collection, extract.extract_id)
    # An existing directory is an earlier delivery: fail rather than write into it.
    extract_dir.mkdir()
    definition = extract.build()
    write_definition(definition, extract_dir / 'extract.json')
    client.wait_for_extract(extract)
    client.download_extract(extract, download_dir=extract_dir)
    retrieved_at = datetime.now(UTC)

    manifest_path = paths.manifest_path(data_dir)
    manifest.append_entries(
        manifest_path,
        [
            manifest.describe_file(
                file,
                manifest_path.parent,
                retrieved_at=retrieved_at,
                client='ipumspy',
                client_version=version('ipumspy'),
                collection=extract.collection,
                extract_number=extract.extract_id,
                samples=definition['samples'],
            )
            for file in sorted(extract_dir.iterdir())
        ],
    )
    return extract_dir


def parquet_path(data_dir: Path, source: str, set_name: str, csv_gz: Path) -> Path:
    '''Where the Parquet converted from a delivered .csv.gz goes, outside raw/.'''
    name = csv_gz.name.removesuffix('.csv.gz')
    return paths.derived_dir(data_dir, source) / set_name / f'{name}.parquet'
