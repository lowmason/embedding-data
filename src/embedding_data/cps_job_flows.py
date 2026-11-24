'''Stage 11 CPS job-flow commands: one acquisition and four offline commands.

Run as `python -m embedding_data.cps_job_flows`. Every command needs an explicit
`--data-dir`. Only `acquire-references` uses the network. `import-reference`, `build`, `verify`
and `compare-runs` load no environment file, read no credential and construct no HTTP client.
No command reads `IPUMS_API_KEY` or constructs an IPUMS client. Success prints one sorted JSON
line. A failure prints one fixed line with a reason, the run ID and the data-relative path, and
exits 2. It never prints the exception text, which can hold row content. An unequal
`compare-runs` exits 1.
'''

import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import httpx
import typer

from embedding_data import cps_flow_bundle, cps_flow_inputs, cps_flow_references

app = typer.Typer(pretty_exceptions_enable=False, pretty_exceptions_show_locals=False)
DataRoot = Annotated[Path, typer.Option('--data-dir', help='Explicit local data root.')]
NO_RUN = '-'
RAW = 'raw/references/cps-job-flows'
BUNDLES = 'derived/cps/job-flows'


@app.callback()
def main():
    '''Acquire or import the CPS job-flow references, then build, verify and compare bundles.'''


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


def _run_path(run_id: str) -> str:
    '''The data-relative run directory for the failure line. It does not validate the ID.'''
    return f'{BUNDLES}/{run_id}'


def _invoke(command: str, run_id: str, path: object, operation: Callable[[], object]):
    '''Print the JSON result of `operation`, or only the fixed failure line, then exit 2.'''
    try:
        result = operation()
        typer.echo(json.dumps(result, sort_keys=True))
        return result
    except Exception as error:
        typer.echo(f'CPS job flows {command} failed: {_reason(error)}; run {run_id}; '
                   f'path {path}', err=True)
        raise typer.Exit(2) from None


@app.command('acquire-references')
def acquire_references(reference_id: str, data_dir: DataRoot):
    '''Fetch each Stage 11 reference original that is not staged yet. The network command.'''
    _invoke('acquire-references', NO_RUN, RAW, lambda: _relative(
        cps_flow_references.acquire(data_dir, reference_id), data_dir))


@app.command('import-reference')
def import_reference(reference_id: str, kind: str, file: Path, data_dir: DataRoot):
    '''Record the exact bytes of an original that the owner downloaded in a browser.'''
    _invoke('import-reference', NO_RUN, RAW, lambda: _relative(
        cps_flow_references.import_reference(data_dir, reference_id, kind, file), data_dir))


@app.command('build')
def build(run_id: str, data_dir: DataRoot,
          stage7_run: Annotated[str, typer.Option('--stage7-run')],
          stage7_outputs_sha256: Annotated[str, typer.Option('--stage7-outputs-sha256')],
          stage7_receipt: Annotated[str, typer.Option('--stage7-receipt')],
          stage7_receipt_sha256: Annotated[str, typer.Option('--stage7-receipt-sha256')],
          stage8_receipt: Annotated[str, typer.Option('--stage8-receipt')],
          stage8_receipt_sha256: Annotated[str, typer.Option('--stage8-receipt-sha256')],
          stage8_mapping_run: Annotated[str, typer.Option('--stage8-mapping-run')],
          stage8_mapping_outputs_sha256: Annotated[
              str, typer.Option('--stage8-mapping-outputs-sha256')],
          codes_run: Annotated[str, typer.Option('--codes-run')],
          codes_outputs_sha256: Annotated[str, typer.Option('--codes-outputs-sha256')],
          cps_receipt: Annotated[str, typer.Option('--cps-receipt')],
          cps_receipt_sha256: Annotated[str, typer.Option('--cps-receipt-sha256')]):
    '''Build one immutable bundle from the five pinned upstream runs and the Stage 11 receipt.'''
    request = cps_flow_inputs.InputRequest(
        stage7_run=stage7_run, stage7_outputs_sha256=stage7_outputs_sha256,
        stage7_receipt=stage7_receipt, stage7_receipt_sha256=stage7_receipt_sha256,
        stage8_receipt=stage8_receipt, stage8_receipt_sha256=stage8_receipt_sha256,
        stage8_mapping_run=stage8_mapping_run,
        stage8_mapping_outputs_sha256=stage8_mapping_outputs_sha256,
        codes_run=codes_run, codes_outputs_sha256=codes_outputs_sha256,
        cps_receipt=cps_receipt, cps_receipt_sha256=cps_receipt_sha256)

    def operation() -> dict:
        result = cps_flow_bundle.build(data_dir, run_id, request)
        return {**result, 'directory': _relative(result['directory'], data_dir)}

    _invoke('build', run_id, _run_path(run_id), operation)


@app.command('verify')
def verify(run_id: str, data_dir: DataRoot,
           outputs_sha256: Annotated[str, typer.Option('--outputs-sha256')]):
    '''Authenticate the detached pin, then recompute and compare every table.'''
    _invoke('verify', run_id, _run_path(run_id), lambda: cps_flow_bundle.verify_bundle(
        cps_flow_bundle.run_directory(data_dir, run_id), data_dir,
        expected_outputs_sha256=outputs_sha256))


@app.command('compare-runs')
def compare_runs(first_id: str, second_id: str, data_dir: DataRoot):
    '''Compare two published bundles exactly. Exit 1 when they differ.'''
    result = _invoke(
        'compare-runs', f'{first_id},{second_id}',
        f'{_run_path(first_id)},{_run_path(second_id)}',
        lambda: cps_flow_bundle.compare_runs(cps_flow_bundle.run_directory(data_dir, first_id),
                                             cps_flow_bundle.run_directory(data_dir, second_id)))
    # Outside the guard: the guard would turn this exit into the fixed line and exit 2.
    if not result['equal']:
        raise typer.Exit(1)


if __name__ == '__main__':
    app()
