'''Select and reverify a pinned Stage 4 codes bundle without a Stage 5 geography run.

Stage 10 reads classification and canonical ITA tables only, so this selector authenticates
the detached codes pin and checks the bundle, its raw citations and the Stage 2 source,
and it consumes no geography bundle. `target_inputs.select` needs one, so its codes-side
checks are repeated here from the same public helpers.
'''

import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from embedding_data import code_build, ita_summary, manifest, paths, target_inputs, target_io

RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')
PIN = re.compile(r'[0-9a-f]{64}')
SOURCE_YEARS = list(range(2016, 2026))
BUNDLE_FILES = {name + '.parquet' for name in target_inputs.CODE_SCHEMAS}
INVENTORY_NAMES = BUNDLE_FILES | {'inputs.json', 'report.json'}


@dataclass(frozen=True)
class SelectedCodes:
    data_dir: Path
    codes_run: str
    codes_outputs_sha256: str
    directory: Path
    tables: dict[str, Path]
    summary: Path
    provenance: dict

    def verify(self) -> None:
        '''Reselect the pinned bundle and refuse any difference from this selection.'''
        try:
            current = select_codes(self.data_dir, self.codes_run,
                                   codes_outputs_sha256=self.codes_outputs_sha256)
        except (ValueError, OSError) as error:
            raise ValueError('selected codes inputs changed') from error
        if current != self:
            raise ValueError('selected codes inputs changed')


def merge_citations(*groups: list[dict]) -> list[dict]:
    '''Join citation lists by path, sorted, refusing one path cited with different content.'''
    by_path = {}
    for citation in (citation for group in groups for citation in group):
        if by_path.setdefault(citation['path'], citation) != citation:
            raise ValueError('conflicting citations for the same raw path')
    return [by_path[path] for path in sorted(by_path)]


def _read_object(file: Path, *required: str) -> dict:
    value = json.loads(file.read_text())
    if not isinstance(value, dict) or not set(required) <= set(value):
        raise ValueError(f'{file.name}: not an object with the required fields')
    return value


def _check_tables(directory: Path, report: dict) -> dict[str, Path]:
    if set(report['tables']) != BUNDLE_FILES:
        raise ValueError('report table inventory differs')
    files = {}
    for name, schema in target_inputs.CODE_SCHEMAS.items():
        file = directory / (name + '.parquet')
        frame = pl.scan_parquet(file)
        actual = frame.collect_schema()
        recorded = report['tables'][file.name]
        if (list(actual.items()) != list(schema.items())
                or recorded.get('schema') != {c: str(t) for c, t in actual.items()}
                or recorded.get('rows') != frame.select(pl.len()).collect().item()):
            raise ValueError(f'{name}: rows or ordered schema differs')
        files[name] = file
    return files


def _snapshot(data_dir: Path, codes_run: str, outputs_sha256: str) -> SelectedCodes:
    if not RUN_ID.fullmatch(codes_run):
        raise ValueError('unsafe selected run ID')
    if not PIN.fullmatch(outputs_sha256):
        raise ValueError('invalid detached checksum')
    directory = target_io.relative_file(data_dir, f'derived/codes/{codes_run}')
    outputs_file = target_io.relative_file(directory, 'outputs.json')
    if manifest.sha256_file(outputs_file) != outputs_sha256:
        raise ValueError('detached inventory checksum differs')
    outputs = json.loads(outputs_file.read_text())
    target_io.verify_inventory(directory, outputs, INVENTORY_NAMES)
    inputs = _read_object(directory / 'inputs.json', 'schema_version', 'run_id', 'raw',
                          'source_parquet')
    report = _read_object(directory / 'report.json', 'schema_version', 'tables')
    if (inputs['schema_version'] != code_build.SCHEMA_VERSION
            or report['schema_version'] != code_build.SCHEMA_VERSION
            or inputs['run_id'] != codes_run):
        raise ValueError('incompatible schema version or run identity')
    tables = _check_tables(directory, report)
    try:
        verified = target_io.verify_raw(data_dir, inputs['raw'])
    except KeyError:
        raise ValueError('cited raw file is not recorded') from None
    source = inputs['source_parquet']
    summary = target_io.relative_file(data_dir, source.get('path'))
    if summary != paths.derived_dir(data_dir, 'osha') / ita_summary.TABLE_NAME:
        raise ValueError('unexpected selected source path')
    if (manifest.sha256_file(summary) != source.get('sha256')
            or summary.stat().st_size != source.get('size')):
        raise ValueError('selected source hash or size differs')
    source_record = target_io.file_record(summary)
    try:
        with tempfile.TemporaryDirectory() as work:
            frame, source_citations = code_build.check_source(data_dir, Path(work))
    except KeyError:
        raise ValueError('cited raw file is not recorded') from None
    years = frame.select('year_filing_for').unique().collect().to_series().to_list()
    if sorted(years) != SOURCE_YEARS:
        raise ValueError('source years must be exactly 2016 through 2025')
    by_path = {citation['path']: citation for citation in verified}
    source_citations = json.loads(json.dumps(source_citations))
    for citation in source_citations:
        if by_path.get(citation['path']) != citation:
            raise ValueError('source release missing from selected bundle citations')
    canonical = tables['ita_300a_canonical']
    target_inputs.require_source_parity(summary, canonical)
    target_inputs.validate_native(pl.scan_parquet(canonical),
                                  pl.read_parquet(tables['naics_nodes']))
    return SelectedCodes(data_dir, codes_run, outputs_sha256, directory, tables, summary, {
        'codes': {'run_id': codes_run, 'outputs_sha256': outputs_sha256, 'outputs': outputs},
        'raw': merge_citations(verified, source_citations),
        'source_parquet': {'path': source['path'], **source_record},
        'canonical': {'path': canonical.relative_to(data_dir).as_posix(),
                      **target_io.file_record(canonical)},
        'source_years': sorted(years),
        'source_rows': source_record['rows'],
    })


def select_codes(data_dir: Path, codes_run: str, *, codes_outputs_sha256: str) -> SelectedCodes:
    '''Authenticate the pinned codes bundle and its source twice, refusing any difference.'''
    first = _snapshot(data_dir, codes_run, codes_outputs_sha256)
    second = _snapshot(data_dir, codes_run, codes_outputs_sha256)
    if first != second:
        raise ValueError('selected codes inputs changed during validation')
    return second
