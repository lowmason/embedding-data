'''Stage 14 USAspending vendor-link commands: subaward acquisition and import so far.

Run as `python -m embedding_data.usaspending_vendor_links`. Every command needs an explicit
`--data-dir`. Only `acquire-subawards` uses the network, and it needs no key.
`import-subawards` loads no environment file, reads no credential and constructs no HTTP
client. Success prints one sorted JSON line. A failure prints one fixed line with a reason,
the run ID and the path, and exits 2. It never prints the exception text, which can hold
row content or a URL.
'''

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Annotated

import httpx
import typer

from embedding_data import usaspending_raw

app = typer.Typer(pretty_exceptions_enable=False, pretty_exceptions_show_locals=False)
DataRoot = Annotated[Path, typer.Option('--data-dir', help='Explicit local data root.')]
Snapshot = Annotated[str, typer.Option('--snapshot', help='Snapshot date, YYYY-MM-DD.')]
NO_RUN = '-'
SUBAWARDS = 'raw/usaspending/subcontracts'
EXTRACTS = 'raw/sam/entity-extract/public-monthly-v2'


@app.callback()
def main():
    '''Acquire USAspending contract subawards, then build, verify and compare bundles.'''


def _reason(error: Exception) -> str:
    if isinstance(error, ValueError):
        return 'validation'
    if isinstance(error, OSError):
        return 'filesystem'
    if isinstance(error, httpx.HTTPError):
        return 'network'
    return 'unexpected'


def _invoke(command: str, run_id: str, path: object, operation: Callable[[], object]):
    '''Print the JSON result of `operation`, or only the fixed failure line, then exit 2.'''
    try:
        result = operation()
        typer.echo(json.dumps(result, sort_keys=True))
        return result
    except Exception as error:
        typer.echo(f'USAspending vendor links {command} failed: {_reason(error)}; '
                   f'run {run_id}; path {path}', err=True)
        raise typer.Exit(2) from None


def _relative(file: Path, data_dir: Path) -> str:
    return Path(file).relative_to(data_dir).as_posix()


@app.command('acquire-subawards')
def acquire_subawards(fiscal_year: int, snapshot: Snapshot, data_dir: DataRoot):
    '''Download one fiscal year of contract subawards. This is the network command.'''
    _invoke('acquire-subawards', NO_RUN, SUBAWARDS, lambda: {'path': _relative(
        usaspending_raw.acquire(
            data_dir, fiscal_year, snapshot=date.fromisoformat(snapshot)), data_dir)})


@app.command('import-subawards')
def import_subawards(fiscal_year: int, file: Path, snapshot: Snapshot, data_dir: DataRoot):
    '''Register a subaward ZIP that the owner downloaded in a browser.'''
    _invoke('import-subawards', NO_RUN, SUBAWARDS, lambda: {'path': _relative(
        usaspending_raw.import_file(
            data_dir, fiscal_year, file, snapshot=date.fromisoformat(snapshot)), data_dir)})


if __name__ == '__main__':
    app()
