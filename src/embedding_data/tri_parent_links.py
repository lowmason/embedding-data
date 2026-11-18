'''Stage 5 TRI parent-link commands: acquire or import the EPA TRI basic data files.

Run as `python -m embedding_data.tri_parent_links`. Every command needs an explicit
`--data-dir`. Only `acquire` uses the network. `import-file` loads no environment file,
reads no credential and constructs no HTTP client. Success prints one sorted JSON line. A
failure prints one fixed line with a reason, the run ID and the data-relative path, and
exits 2. It never prints the exception text, which can hold row content.
'''

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Annotated

import httpx
import typer

from embedding_data import tri_raw

app = typer.Typer(pretty_exceptions_enable=False, pretty_exceptions_show_locals=False)
DataRoot = Annotated[Path, typer.Option('--data-dir', help='Explicit local data root.')]
NO_RUN = '-'
RAW = 'raw/epa_tri/basic'


@app.callback()
def main():
    '''Acquire or import the EPA TRI basic data files of reporting years 2022-2024.'''


def _reason(error: Exception) -> str:
    if isinstance(error, ValueError):
        return 'validation'
    if isinstance(error, OSError):
        return 'filesystem'
    if isinstance(error, httpx.HTTPError):
        return 'network'
    return 'unexpected'


def _relative(file: Path, data_dir: Path) -> str:
    return Path(file).relative_to(data_dir).as_posix()


def _invoke(command: str, run_id: str, path: object, operation: Callable[[], object]):
    '''Print the JSON result of `operation`, or only the fixed failure line, then exit 2.'''
    try:
        result = operation()
        typer.echo(json.dumps(result, sort_keys=True))
        return result
    except Exception as error:
        typer.echo(f'TRI parent links {command} failed: {_reason(error)}; run {run_id}; '
                   f'path {path}', err=True)
        raise typer.Exit(2) from None


@app.command('acquire')
def acquire(data_dir: DataRoot):
    '''Download each window year's U.S. file that is not on disk yet. The network command.'''
    _invoke('acquire', NO_RUN, RAW, lambda: [
        _relative(file, data_dir) for file in tri_raw.acquire(data_dir)])


@app.command('import-file')
def import_file(year: int, file: Path, data_dir: DataRoot,
                processed_as_of: Annotated[str, typer.Option(
                    '--processed-as-of', help='EPA "processed as of" date, YYYY-MM-DD.')]):
    '''Record the exact bytes of a file that the owner downloaded in a browser.'''
    _invoke('import-file', NO_RUN, RAW, lambda: _relative(tri_raw.import_file(
        data_dir, year, file, processed_as_of=date.fromisoformat(processed_as_of)), data_dir))


if __name__ == '__main__':
    app()
