'''Classification reference acquisition and immutable offline builds.'''

from pathlib import Path

import httpx
import polars as pl
import typer
from fastexcel import FastExcelError

from embedding_data import code_build, code_references, paths

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@app.callback()
def codes():
    '''Acquire official code references and build immutable canonical ITA bundles.'''


def invoke(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except (
        OSError, ValueError, KeyError, httpx.HTTPError, pl.exceptions.PolarsError, FastExcelError
    ) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(2) from None


@app.command('acquire')
def acquire(data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')):
    for file in invoke(code_references.acquire, data_dir, registry=code_references.REGISTRY):
        typer.echo(file)


@app.command('import-reference')
def import_reference(
    kind: str, file: Path, data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')
):
    typer.echo(
        invoke(
            code_references.import_reference,
            data_dir,
            kind,
            file,
            registry=code_references.REGISTRY,
        )
    )


@app.command('build')
def build(run_id: str, data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')):
    typer.echo(invoke(code_build.build, data_dir, run_id, registry=code_references.REGISTRY))
