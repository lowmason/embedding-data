'''Stage 17 ACS wage microdata commands: three offline commands.

Run as `python -m embedding_data.acs_wage_microdata`. Every command needs an explicit
`--data-dir`. No command uses the network, loads an environment file, reads a credential,
constructs an HTTP client or runs an upstream builder. Success prints one sorted JSON line.
A failure prints one fixed line with a reason, the run ID and the path, and exits 2. It never
prints the exception text, which can hold wage values or person rows. An unequal comparison
prints its JSON line and exits 1.
'''

import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer

from embedding_data import acs_wage_bundle, paths

app = typer.Typer(pretty_exceptions_enable=False, pretty_exceptions_show_locals=False)
DataRoot = Annotated[Path, typer.Option('--data-dir', help='Explicit local data root.')]


@app.callback()
def main():
    '''Build, verify and compare ACS wage microdata bundles from a pinned Stage 8 run.'''


def _reason(error: Exception) -> str:
    if isinstance(error, ValueError):
        return 'validation'
    if isinstance(error, OSError):
        return 'filesystem'
    return 'unexpected'


def _run_path(data_dir: Path, run_id: str) -> Path:
    '''The run directory for the failure line. It does not validate the run ID.'''
    return paths.derived_dir(data_dir, 'acs') / 'wage-microdata' / run_id


def _invoke(command: str, run_id: str, path: object, operation: Callable[[], dict]) -> dict:
    '''Print the JSON result of `operation`, or only the fixed failure line, then exit 2.'''
    try:
        result = operation()
        typer.echo(json.dumps(result, sort_keys=True))
        return result
    except Exception as error:
        typer.echo(f'ACS wage microdata {command} failed: {_reason(error)}; run {run_id}; '
                   f'path {path}', err=True)
        raise typer.Exit(2) from None


@app.command('build')
def build(run_id: str, data_dir: DataRoot,
          mapping_run: Annotated[str, typer.Option('--mapping-run')],
          mapping_outputs_sha256: Annotated[str, typer.Option('--mapping-outputs-sha256')],
          codes_run: Annotated[str, typer.Option('--codes-run')],
          codes_outputs_sha256: Annotated[str, typer.Option('--codes-outputs-sha256')]):
    '''Build one immutable bundle from the pinned Stage 8 and Stage 4 runs.'''
    _invoke('build', run_id, _run_path(data_dir, run_id), lambda: acs_wage_bundle.build(
        data_dir, run_id, mapping_run=mapping_run, mapping_outputs_sha256=mapping_outputs_sha256,
        codes_run=codes_run, codes_outputs_sha256=codes_outputs_sha256))


@app.command('verify')
def verify(run_id: str, data_dir: DataRoot,
           outputs_sha256: Annotated[str, typer.Option('--outputs-sha256')]):
    '''Authenticate the detached pin, then recompute and compare the table.'''
    _invoke('verify', run_id, _run_path(data_dir, run_id), lambda: acs_wage_bundle.verify_bundle(
        acs_wage_bundle.run_directory(data_dir, run_id), data_dir,
        expected_outputs_sha256=outputs_sha256))


@app.command('compare-runs')
def compare_runs(first_id: str, second_id: str, data_dir: DataRoot):
    '''Compare two published bundles exactly. Exit 1 when they differ.'''
    path = f'{_run_path(data_dir, first_id)},{_run_path(data_dir, second_id)}'
    result = _invoke('compare-runs', f'{first_id},{second_id}', path,
                     lambda: acs_wage_bundle.compare_runs(
                         acs_wage_bundle.run_directory(data_dir, first_id),
                         acs_wage_bundle.run_directory(data_dir, second_id)))
    # Outside the guard: the guard would turn this exit into the fixed line and exit 2.
    if not result['equal']:
        raise typer.Exit(1)


if __name__ == '__main__':
    app()
