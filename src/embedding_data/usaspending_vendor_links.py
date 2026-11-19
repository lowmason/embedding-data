'''Stage 14 USAspending vendor-link commands: subaward and SAM.gov extract acquisition and
import so far.

Run as `python -m embedding_data.usaspending_vendor_links`. Every command needs an explicit
`--data-dir`. `acquire-subawards` uses the network with no key. `acquire-sam-extract` uses
the network and is the only command that reads the SAM.gov key. The import commands load no
environment file, read no credential and construct no HTTP client. Success prints one sorted
JSON line. A failure prints one fixed line with a reason, the run ID and the path, and exits
2. It never prints the exception text, which can hold row content, a URL or the key.
'''

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Annotated

import httpx
import typer

from embedding_data import sam_access, sam_raw, usaspending_raw

app = typer.Typer(pretty_exceptions_enable=False, pretty_exceptions_show_locals=False)
DataRoot = Annotated[Path, typer.Option('--data-dir', help='Explicit local data root.')]
Snapshot = Annotated[str, typer.Option('--snapshot', help='Snapshot date, YYYY-MM-DD.')]
Month = Annotated[str, typer.Option('--month', help='Extract month, YYYY-MM.')]
EnvFile = Annotated[Path | None, typer.Option(
    '--env-file', help='Explicit env file holding SAM_API_KEY (read, never loaded).')]
Prompt = Annotated[bool, typer.Option(
    '--prompt', help='Ask for the key with hidden input in a local terminal.')]
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


@app.command('acquire-sam-extract')
def acquire_sam_extract(month: Month, data_dir: DataRoot, env_file: EnvFile = None,
                        prompt: Prompt = False):
    '''Download one public monthly SAM.gov extract. The only command that reads the key.'''
    def operation():
        checked = sam_raw.parse_month(month)
        credential = sam_access.read_credential(env_file=env_file, prompt=prompt)
        path = sam_raw.acquire(data_dir, checked, credential=credential)
        return {'path': _relative(path, data_dir)}

    _invoke('acquire-sam-extract', NO_RUN, EXTRACTS, operation)


@app.command('import-sam-extract')
def import_sam_extract(file: Path, month: Month, data_dir: DataRoot):
    '''Register a SAM.gov extract that the owner downloaded in a browser.'''
    _invoke('import-sam-extract', NO_RUN, EXTRACTS, lambda: {'path': _relative(
        sam_raw.import_file(data_dir, file, month=month), data_dir)})


if __name__ == '__main__':
    app()
