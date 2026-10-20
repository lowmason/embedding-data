'''Explicit offline build, detached verification and comparison of ACS targets.'''

import json
from pathlib import Path
from typing import Annotated

import typer

from embedding_data import acs_target_bundle as bundle
from embedding_data.acs_mapping_contract import SelectionRequest

app = typer.Typer(pretty_exceptions_enable=False, pretty_exceptions_show_locals=False)
DataRoot = Annotated[Path, typer.Option('--data-dir', help='Explicit local data root.')]


@app.callback()
def main():
    '''Build and verify explicit immutable ACS target runs offline.'''


def _invoke(operation, *args, **kwargs):
    try:
        result = operation(*args, **kwargs)
        typer.echo(json.dumps(result, sort_keys=True, allow_nan=False))
        return result
    except Exception:
        # Delivered parser exceptions may contain raw values; expose only this diagnostic.
        typer.echo('ACS target validation failed.', err=True)
        raise typer.Exit(2) from None


@app.command('build')
def build(run_id: str, data_dir: DataRoot,
          mapping_run: Annotated[str, typer.Option('--mapping-run')],
          mapping_outputs_sha256: Annotated[str, typer.Option('--mapping-outputs-sha256')],
          codes_run: Annotated[str, typer.Option('--codes-run')],
          codes_outputs_sha256: Annotated[str, typer.Option('--codes-outputs-sha256')],
          geography_run: Annotated[str, typer.Option('--geography-run')],
          geography_outputs_sha256: Annotated[str, typer.Option('--geography-outputs-sha256')],
          ipums_run: Annotated[str, typer.Option('--ipums-run')],
          ipums_outputs_sha256: Annotated[str, typer.Option('--ipums-outputs-sha256')],
          ipums_references_sha256: Annotated[str, typer.Option('--ipums-references-sha256')]):
    request = SelectionRequest(codes_run, codes_outputs_sha256, geography_run,
                               geography_outputs_sha256, ipums_run, ipums_outputs_sha256,
                               ipums_references_sha256)
    _invoke(bundle.build, data_dir, run_id, mapping_run,
            expected_mapping_outputs_sha256=mapping_outputs_sha256, request=request)


@app.command('verify')
def verify(run_id: str, data_dir: DataRoot,
           mapping_run: Annotated[str, typer.Option('--mapping-run')],
           mapping_outputs_sha256: Annotated[str, typer.Option('--mapping-outputs-sha256')],
           outputs_sha256: Annotated[str, typer.Option('--outputs-sha256')]):
    _invoke(lambda: bundle.verify_bundle(bundle.run_directory(data_dir, run_id), data_dir,
        expected_outputs_sha256=outputs_sha256, mapping_run=mapping_run,
        expected_mapping_outputs_sha256=mapping_outputs_sha256))


@app.command('compare-runs')
def compare(first_id: str, second_id: str, data_dir: DataRoot,
            mapping_run: Annotated[str, typer.Option('--mapping-run')],
            mapping_outputs_sha256: Annotated[str, typer.Option('--mapping-outputs-sha256')]):
    result = _invoke(lambda: bundle.compare_runs(bundle.run_directory(data_dir, first_id),
        bundle.run_directory(data_dir, second_id), data_dir=data_dir, mapping_run=mapping_run,
        expected_mapping_outputs_sha256=mapping_outputs_sha256))
    if not result['equal']:
        raise typer.Exit(1)


if __name__ == '__main__':
    app()
