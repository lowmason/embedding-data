'''Explicit public acquisition and offline delivered-extract evidence commands.'''

import json
from pathlib import Path
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

import httpx
import polars as pl
import typer
from fastexcel import FastExcelError

from embedding_data import ipums_references, ipums_verification_run, manifest, paths

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@app.callback()
def ipums():
    '''Acquire public references and measure existing immutable IPUMS deliveries.'''


def invoke(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except ipums_verification_run.FidelityError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(2) from None
    except (OSError, EOFError, ValueError, KeyError, TypeError, ParseError, BadZipFile,
            httpx.HTTPError, pl.exceptions.PolarsError, FastExcelError):
        # Parser exceptions can contain person values or authenticated transport URLs.
        typer.echo('IPUMS verification failed; inspect selected input metadata and staging.',
                   err=True)
        raise typer.Exit(2) from None


@app.command('acquire-references')
def acquire_references(
    reference_id: str, data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir'),
    census_env_file: Path | None = typer.Option(None, '--census-env-file'),
):
    typer.echo(invoke(ipums_references.acquire, data_dir, reference_id,
                      census_env_file=census_env_file))


@app.command('import-reference')
def import_reference(reference_id: str, kind: str, original: Path,
                     data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')):
    typer.echo(invoke(ipums_references.import_reference, data_dir, reference_id, kind, original))


@app.command('measure')
def measure(run_id: str, references: str = typer.Option(..., '--references'),
            selection: Path = typer.Option(..., '--selection'),
            data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')):
    directory = invoke(ipums_verification_run.measure, data_dir, run_id, references, selection)
    typer.echo(directory)
    typer.echo(f'outputs.json SHA-256: {manifest.sha256_file(directory / "outputs.json")}')


@app.command('verify')
def verify(run_id: str, outputs_sha256: str = typer.Option(..., '--outputs-sha256'),
           data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')):
    directory = invoke(ipums_verification_run.run_directory, data_dir, run_id)
    result = invoke(ipums_verification_run.verify_bundle, directory, data_dir,
                    expected_outputs_sha256=outputs_sha256)
    typer.echo(json.dumps(result, sort_keys=True))


@app.command('compare-runs')
def compare_runs(first_id: str, second_id: str,
                 data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')):
    first = invoke(ipums_verification_run.run_directory, data_dir, first_id)
    second = invoke(ipums_verification_run.run_directory, data_dir, second_id)
    result = invoke(ipums_verification_run.compare_runs, first, second)
    typer.echo(json.dumps(result, sort_keys=True))
    if not result['equal']:
        raise typer.Exit(1)
