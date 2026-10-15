'''Prepare, explicitly acquire and build immutable ITA targets.'''

from pathlib import Path

import httpx
import typer

from embedding_data import ita_assignment_acquire as acquisition
from embedding_data import ita_assignment_prepare as preparation
from embedding_data import ita_target_build as builder
from embedding_data import paths

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@app.command('prepare-ita')
def prepare_ita(
    assignment_run_id: str,
    codes_run: str = typer.Option(..., '--codes-run'),
    geography_run: str = typer.Option(..., '--geography-run'),
    data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir'),
    codes_outputs_sha256: str | None = typer.Option(None, '--codes-outputs-sha256'),
    geography_outputs_sha256: str | None = typer.Option(None, '--geography-outputs-sha256'),
) -> None:
    try:
        result = preparation.prepare(
            data_dir, assignment_run_id, codes_run, geography_run,
            codes_outputs_sha256=codes_outputs_sha256,
            geography_outputs_sha256=geography_outputs_sha256)
    except (ValueError, KeyError, OSError) as error:
        typer.echo(f'ITA preparation failed: {error}', err=True)
        raise typer.Exit(1) from None
    typer.echo(str(result))


@app.command('acquire-ita')
def acquire_ita(
    assignment_run_id: str,
    data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir'),
) -> None:
    try:
        result = acquisition.acquire(data_dir, assignment_run_id)
    except (ValueError, KeyError, OSError, httpx.HTTPError) as error:
        typer.echo(f'ITA acquisition failed: {error}', err=True)
        raise typer.Exit(1) from None
    typer.echo(str(result))


@app.command('build-ita')
def build_ita(
    assignment_run_id: str, target_run_id: str,
    year: int = typer.Option(2023, '--year'),
    data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir'),
) -> None:
    try:
        result = builder.build(data_dir, assignment_run_id, target_run_id, year=year)
    except (ValueError, KeyError, OSError) as error:
        typer.echo(f'ITA target build failed: {error}', err=True)
        raise typer.Exit(1) from None
    typer.echo(str(result))
