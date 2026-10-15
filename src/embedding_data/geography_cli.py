from pathlib import Path
from zipfile import BadZipFile

import httpx
import polars as pl
import typer
from fastexcel import FastExcelError

from embedding_data import geography_build, geography_references, paths

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@app.callback()
def geography():
    '''Acquire official geography originals and build immutable offline reference bundles.'''


def invoke(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except (OSError, ValueError, KeyError, BadZipFile, httpx.HTTPError,
            pl.exceptions.PolarsError, FastExcelError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(2) from None


@app.command('acquire')
def acquire(data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')):
    for file in invoke(geography_references.acquire, data_dir,
                       registry=geography_references.REGISTRY):
        typer.echo(file)


@app.command('import-reference')
def import_reference(kind: str, file: Path,
                     data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')):
    typer.echo(invoke(geography_references.import_reference, data_dir, kind, file,
                      registry=geography_references.REGISTRY))


@app.command('build')
def build(run_id: str, data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')):
    typer.echo(invoke(geography_build.build, data_dir, run_id,
                      registry=geography_references.REGISTRY))
