'''Stage 14 USAspending vendor-link commands: two acquisitions and five offline commands.

Run as `python -m embedding_data.usaspending_vendor_links`. Every command needs an explicit
`--data-dir`. `acquire-subawards` uses the network with no key. `acquire-sam-extract` uses
the network and is the only command that reads the SAM.gov key. `import-subawards`,
`import-sam-extract`, `build`, `verify` and `compare-runs` load no environment file, read no
credential, construct no HTTP client and run no upstream builder. Success prints one sorted
JSON line. A failure prints one fixed line with a reason, the run ID and the path, and exits
2. It never prints the exception text, which can hold row content, a URL or the key.
`compare-runs` exits 1 when the two bundles differ.
'''

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Annotated

import httpx
import typer

from embedding_data import sam_access, sam_raw, usaspending_raw, vendor_link_bundle

app = typer.Typer(pretty_exceptions_enable=False, pretty_exceptions_show_locals=False)
DataRoot = Annotated[Path, typer.Option('--data-dir', help='Explicit local data root.')]
Snapshot = Annotated[str, typer.Option('--snapshot', help='Snapshot date, YYYY-MM-DD.')]
Month = Annotated[str, typer.Option('--month', help='Extract month, YYYY-MM.')]
EnvFile = Annotated[Path | None, typer.Option(
    '--env-file', help='Explicit env file holding SAM_API_KEY (read, never loaded).')]
Prompt = Annotated[bool, typer.Option(
    '--prompt', help='Ask for the key with hidden input in a local terminal.')]
CodesRun = Annotated[str, typer.Option('--codes-run', help='Selected Stage 4 codes run ID.')]
CodesPin = Annotated[str, typer.Option(
    '--codes-outputs-sha256', help='Detached SHA-256 of the codes run `outputs.json`.')]
SamMonth = Annotated[str, typer.Option('--sam-month', help='Extract month, YYYY-MM.')]
OutputsPin = Annotated[str, typer.Option(
    '--outputs-sha256', help='Detached SHA-256 of the bundle `outputs.json`.')]
NO_RUN = '-'
SUBAWARDS = 'raw/usaspending/subcontracts'
EXTRACTS = 'raw/sam/entity-extract/public-monthly-v2'
VENDOR_LINKS = 'derived/usaspending/vendor-links'


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


def _run_path(run_id: str) -> str:
    '''The data-relative run directory for the failure line. It does not validate the run ID.'''
    return f'{VENDOR_LINKS}/{run_id}'


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


@app.command('build')
def build(run_id: str, data_dir: DataRoot, codes_run: CodesRun, codes_outputs_sha256: CodesPin,
          snapshot: Snapshot, sam_month: SamMonth):
    '''Build one immutable bundle from the pinned codes run and the raw files.'''
    def operation():
        return vendor_link_bundle.build(
            data_dir, run_id, codes_run=codes_run, codes_outputs_sha256=codes_outputs_sha256,
            snapshot=date.fromisoformat(snapshot), sam_month=sam_raw.parse_month(sam_month))

    _invoke('build', run_id, _run_path(run_id), operation)


@app.command('verify')
def verify(run_id: str, data_dir: DataRoot, outputs_sha256: OutputsPin):
    '''Authenticate the detached pin, then recompute and compare every table.'''
    _invoke('verify', run_id, _run_path(run_id), lambda: vendor_link_bundle.verify_bundle(
        vendor_link_bundle.run_directory(data_dir, run_id), data_dir,
        expected_outputs_sha256=outputs_sha256))


@app.command('compare-runs')
def compare_runs(first_id: str, second_id: str, data_dir: DataRoot):
    '''Compare two published bundles exactly. Exit 1 when they differ.'''
    result = _invoke(
        'compare-runs', f'{first_id},{second_id}',
        f'{_run_path(first_id)},{_run_path(second_id)}',
        lambda: vendor_link_bundle.compare_runs(
            vendor_link_bundle.run_directory(data_dir, first_id),
            vendor_link_bundle.run_directory(data_dir, second_id)))
    # Outside the guard: the guard would turn this exit into the fixed line and exit 2.
    if not result['equal']:
        raise typer.Exit(1)


if __name__ == '__main__':
    app()
