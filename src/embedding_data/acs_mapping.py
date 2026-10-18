'''Separate explicit ACS mapping commands; offline except public acquisition.'''

import json
from pathlib import Path
from typing import Annotated

import typer

from embedding_data import acs_mapping_bundle as bundle
from embedding_data import acs_mapping_references as references
from embedding_data.acs_mapping_contract import SelectionRequest

app = typer.Typer(pretty_exceptions_enable=False, pretty_exceptions_show_locals=False)
DataRoot = Annotated[Path, typer.Option('--data-dir', help='Explicit local data root.')]


@app.callback()
def main():
    '''Build and verify explicit immutable ACS mapping runs.'''


def _invoke(operation, *args, **kwargs):
    try:
        result = operation(*args, **kwargs)
        typer.echo(json.dumps(result, sort_keys=True, allow_nan=False))
        return result
    except Exception:
        # Parser messages may embed delivered values; emit only a fixed public diagnostic.
        typer.echo('ACS mapping validation or acquisition failed.', err=True)
        raise typer.Exit(2) from None


def _reference_metadata(snapshot):
    return {'reference_id': snapshot.reference_id, 'receipt_sha256': snapshot.receipt_sha256,
            'originals': len(snapshot.files)}


@app.command('acquire-references')
def acquire(reference_id: str, data_dir: DataRoot):
    _invoke(lambda: _reference_metadata(references.acquire_references(data_dir, reference_id)))


@app.command('import-reference')
def import_reference(reference_id: str, kind: str, original: Path, data_dir: DataRoot):
    _invoke(references.import_reference, data_dir, reference_id, kind, original)


@app.command('build')
def build(run_id: str, data_dir: DataRoot,
          reference_id: Annotated[str, typer.Option('--references')],
          references_sha256: Annotated[str, typer.Option('--references-sha256')],
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
    _invoke(bundle.build, data_dir, run_id, request, reference_id,
            expected_reference_receipt_sha256=references_sha256)


@app.command('verify')
def verify(run_id: str, data_dir: DataRoot,
           outputs_sha256: Annotated[str, typer.Option('--outputs-sha256')]):
    _invoke(lambda: bundle.verify_bundle(bundle.run_directory(data_dir, run_id), data_dir,
                                         expected_outputs_sha256=outputs_sha256))


@app.command('compare-runs')
def compare(first_id: str, second_id: str, data_dir: DataRoot):
    result = _invoke(lambda: bundle.compare_runs(bundle.run_directory(data_dir, first_id),
                                                bundle.run_directory(data_dir, second_id)))
    if not result['equal']:
        raise typer.Exit(1)


if __name__ == '__main__':
    app()
