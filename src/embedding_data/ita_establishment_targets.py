'''Stage 10 ITA establishment-target commands: one acquisition and four offline commands.

Run as `python -m embedding_data.ita_establishment_targets`. Every command needs an
explicit `--data-dir`. Only `acquire-references` uses the network. `import-reference`,
`build`, `verify` and `compare-runs` load no environment file, read no credential and
construct no HTTP client. Success prints one sorted JSON line. A failure prints one fixed
line with a reason, the run ID and the path, and exits 2. It never prints the exception
text, which can hold EINs, names or addresses.
'''

import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import httpx
import typer

from embedding_data import ita_establishment_bundle, ita_index_references, paths

app = typer.Typer(pretty_exceptions_enable=False, pretty_exceptions_show_locals=False)
DataRoot = Annotated[Path, typer.Option('--data-dir', help='Explicit local data root.')]
NO_RUN = '-'
REFERENCES = 'raw/references/naics'


@app.callback()
def main():
    '''Acquire NAICS index originals, then build, verify and compare Stage 10 bundles.'''


def _reason(error: Exception) -> str:
    if isinstance(error, ValueError):
        return 'validation'
    if isinstance(error, OSError):
        return 'filesystem'
    if isinstance(error, httpx.HTTPError):
        return 'network'
    return 'unexpected'


def _run_path(data_dir: Path, run_id: str) -> Path:
    '''The run directory for the failure line. It does not validate the run ID.'''
    return paths.derived_dir(data_dir, 'osha') / 'establishment-targets' / run_id


def _relative(file: Path, data_dir: Path) -> str:
    return Path(file).relative_to(data_dir).as_posix()


def _invoke(command: str, run_id: str, path: object, operation: Callable[[], object]):
    '''Print the JSON result of `operation`, or only the fixed failure line, then exit 2.'''
    try:
        result = operation()
        typer.echo(json.dumps(result, sort_keys=True))
        return result
    except Exception as error:
        typer.echo(f'ITA establishment {command} failed: {_reason(error)}; run {run_id}; '
                   f'path {path}', err=True)
        raise typer.Exit(2) from None


@app.command('acquire-references')
def acquire_references(data_dir: DataRoot):
    '''Download only the missing NAICS index originals. This is the network command.'''
    _invoke('acquire-references', NO_RUN, REFERENCES, lambda: [
        _relative(file, data_dir) for file in ita_index_references.acquire(data_dir)])


@app.command('import-reference')
def import_reference(kind: str, file: Path, data_dir: DataRoot):
    '''Register the exact bytes of an index original that the owner downloaded.'''
    _invoke('import-reference', NO_RUN, REFERENCES, lambda: _relative(
        ita_index_references.import_reference(data_dir, kind, file), data_dir))


@app.command('build')
def build(run_id: str, data_dir: DataRoot,
          codes_run: Annotated[str, typer.Option('--codes-run')],
          codes_outputs_sha256: Annotated[str, typer.Option('--codes-outputs-sha256')]):
    '''Build one immutable bundle from the pinned Stage 4 codes run.'''
    _invoke('build', run_id, _run_path(data_dir, run_id), lambda: ita_establishment_bundle.build(
        data_dir, run_id, codes_run=codes_run, codes_outputs_sha256=codes_outputs_sha256))


@app.command('verify')
def verify(run_id: str, data_dir: DataRoot,
           outputs_sha256: Annotated[str, typer.Option('--outputs-sha256')]):
    '''Authenticate the detached pin, then recompute and compare every table.'''
    _invoke('verify', run_id, _run_path(data_dir, run_id),
            lambda: ita_establishment_bundle.verify_bundle(
                ita_establishment_bundle.run_directory(data_dir, run_id), data_dir,
                expected_outputs_sha256=outputs_sha256))


@app.command('compare-runs')
def compare_runs(first_id: str, second_id: str, data_dir: DataRoot):
    '''Compare two published bundles exactly. Exit 1 when they differ.'''
    path = f'{_run_path(data_dir, first_id)},{_run_path(data_dir, second_id)}'
    result = _invoke('compare-runs', f'{first_id},{second_id}', path,
                     lambda: ita_establishment_bundle.compare_runs(
                         ita_establishment_bundle.run_directory(data_dir, first_id),
                         ita_establishment_bundle.run_directory(data_dir, second_id)))
    # Outside the guard: the guard would turn this exit into the fixed line and exit 2.
    if not result['equal']:
        raise typer.Exit(1)


if __name__ == '__main__':
    app()
