'''Select complete pinned upstream bundles and reverify their immutable evidence.'''

import json
import platform
import re
import sys
from dataclasses import dataclass
from importlib.metadata import distributions, version
from pathlib import Path

import polars as pl

from embedding_data import code_build, geography_build, ipums_verification_run, manifest, target_io
from embedding_data.acs_mapping_contract import SelectionRequest, SourceInput
from embedding_data.acs_mapping_io import safe_path
from embedding_data.target_inputs import CODE_SCHEMAS, REFERENCE_FRAMES

SOFTWARE_ROOT = Path(__file__).resolve().parents[2]
# Task 8 expands this explicit boundary before any production mapping freeze.
SOFTWARE_FILES = tuple(dict.fromkeys((*ipums_verification_run.SOFTWARE_FILES, *(
    f'src/embedding_data/{name}.py' for name in (
        'acs_mapping_contract', 'acs_mapping_inputs', 'acs_mapping_io',
        'target_inputs', 'code_build', 'classification_tables', 'naics_relationships',
        'filing_rules', 'ita_naics_mapping', 'ita_summary', 'ita_references', 'ita_catalog',
        'osha_encoding', 'geography_build', 'geography_tables', 'geography_hud',
    )))))
ACS_PROFILES = ('acs/core', 'acs/five_year', 'acs/vintage')


@dataclass(frozen=True)
class SelectedInputs:
    data_dir: Path
    request: SelectionRequest
    sources: dict[str, SourceInput]
    codes: dict[str, Path]
    geography: dict[str, Path]
    provenance: dict
    software: dict

    def verify(self) -> None:
        selected = select_inputs(self.data_dir, self.request)
        if selected != self:
            raise ValueError('selected inputs, provenance or executing software changed')


def freeze_software() -> dict:
    '''Freeze every explicit executing helper and every installed distribution.'''
    return {
        'files': {name: target_io.file_record(SOFTWARE_ROOT / name) for name in SOFTWARE_FILES},
        'python': platform.python_version(), 'implementation': platform.python_implementation(),
        'dependencies': dict(sorted((dist.metadata['Name'], dist.version)
                                    for dist in distributions())),
        'uv_lock_sha256': manifest.sha256_file(SOFTWARE_ROOT / 'uv.lock'),
    }


def require_detached(file: Path, expected_sha256: str) -> None:
    if not isinstance(expected_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise ValueError('invalid detached checksum')
    if manifest.sha256_file(file) != expected_sha256:
        raise ValueError('detached inventory checksum differs')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON object key')
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError(f'nonfinite JSON number: {value}')


def _read_json(file: Path) -> dict:
    result = json.loads(file.read_text(encoding='utf-8'), object_pairs_hook=_unique_object,
                        parse_constant=_invalid_constant)
    if not isinstance(result, dict):
        raise ValueError('JSON inventory must be an object')
    return result


def _run_directory(data_dir: Path, family: str, run_id: str) -> Path:
    if not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', run_id):
        raise ValueError('unsafe selected run ID')
    directory = target_io.relative_file(data_dir, f'derived/{family}/{run_id}')
    safe_path(directory)
    return directory


def _upstream_software(inputs: dict) -> None:
    for name, checksum in inputs['implementation'].items():
        file = target_io.relative_file(SOFTWARE_ROOT, name)
        if manifest.sha256_file(file) != checksum:
            raise ValueError('upstream executing implementation changed')
    if any(version(name) != expected for name, expected in inputs['dependencies'].items()):
        raise ValueError('upstream dependency identity changed')
    if (inputs['python'] != sys.version or inputs['uv_lock_sha256'] !=
            manifest.sha256_file(SOFTWARE_ROOT / 'uv.lock')):
        raise ValueError('upstream Python or lock identity changed')


def _reference_bundle(data_dir, family, run_id, pin, schemas, schema_version):
    directory = _run_directory(data_dir, family, run_id)
    require_detached(directory / 'outputs.json', pin)
    names = {f'{name}.parquet' for name in schemas} | {'inputs.json', 'report.json'}
    if {file.name for file in directory.iterdir()} != names | {'outputs.json'}:
        raise ValueError('missing or extra bundle paths')
    inventory = _read_json(directory / 'outputs.json')
    target_io.verify_inventory(directory, inventory, names)
    inputs, report = (_read_json(directory / name) for name in ('inputs.json', 'report.json'))
    if (inputs.get('schema_version') != schema_version or
            report.get('schema_version') != schema_version or inputs.get('run_id') != run_id):
        raise ValueError('incompatible upstream schema version or run identity')
    if family == 'geography' and inputs.get('reference_frames') != REFERENCE_FRAMES:
        raise ValueError('incompatible geography reference frames')
    if set(report['tables']) != {f'{name}.parquet' for name in schemas}:
        raise ValueError('report table inventory differs')
    files = {}
    records = {}
    for name, schema in schemas.items():
        file = target_io.relative_file(directory, f'{name}.parquet')
        record = target_io.file_record(file)
        actual = pl.scan_parquet(file).collect_schema()
        recorded = report['tables'][file.name]
        if (list(actual.items()) != list(schema.items()) or recorded['schema'] != record['schema']
                or recorded['rows'] != record['rows']):
            raise ValueError(f'{name}: rows or ordered schema differs')
        files[name], records[name] = file, record
    raw = target_io.verify_raw(data_dir, inputs['raw'])
    _upstream_software(inputs)
    source_record = None
    if family == 'codes':
        source = inputs['source_parquet']
        file = target_io.relative_file(data_dir, source['path'])
        source_record = target_io.file_record(file)
        if any(source_record[key] != source[key] for key in ('sha256', 'size')):
            raise ValueError('selected source hash or size differs')
    return files, {'run_id': run_id, 'outputs_sha256': pin, 'inputs': inputs,
                   'tables': records, 'raw': raw, 'source_parquet': source_record}


def _select_snapshot(data_dir: Path, request: SelectionRequest):
    directory = _run_directory(data_dir, 'ipums/verification', request.ipums_run)
    # Stage 7 authenticates all five deliveries and current software before selection.
    verified = ipums_verification_run.verify_bundle(
        directory, data_dir, expected_outputs_sha256=request.ipums_outputs_sha256)
    # Stage 7 verifies bytes; Stage 8 also requires strict JSON for every artifact.
    for name in ('outputs.json', 'weight_rules.json'):
        _read_json(directory / name)
    upstream = _read_json(directory / 'inputs.json')
    report = _read_json(directory / 'report.json')
    if report.get('format_version') != ipums_verification_run.FORMAT_VERSION:
        raise ValueError('incompatible IPUMS report version')
    if verified['run_id'] != request.ipums_run:
        raise ValueError('selected IPUMS run identity differs')
    receipt_citation = upstream['references']['receipt_citation']
    receipt = target_io.relative_file(data_dir / 'raw', receipt_citation['path'])
    require_detached(receipt, request.ipums_references_receipt_sha256)
    sources = {}
    for profile in ACS_PROFILES:
        item = upstream['deliveries'][profile]
        sources[profile] = SourceInput(
            profile=profile, delivery_id=item['delivery_id'],
            parquet=target_io.relative_file(data_dir, item['parquet']),
            parquet_record=item['parquet_record'], raw_citations=item['raw_citations'],
            definition=item['definition'], ddi=item['ddi'])
    codes, code_provenance = _reference_bundle(
        data_dir, 'codes', request.codes_run, request.codes_outputs_sha256,
        CODE_SCHEMAS, code_build.SCHEMA_VERSION)
    geography, geo_provenance = _reference_bundle(
        data_dir, 'geography', request.geography_run, request.geography_outputs_sha256,
        geography_build.SCHEMAS, geography_build.SCHEMA_VERSION)
    return sources, codes, geography, {
        'codes': code_provenance, 'geography': geo_provenance,
        'ipums': {**verified, 'inputs': upstream,
                  'references_receipt_sha256': request.ipums_references_receipt_sha256},
        'reference_frames': REFERENCE_FRAMES.copy(),
    }


def select_inputs(data_dir: Path, request: SelectionRequest) -> SelectedInputs:
    '''Authenticate in place, then repeat checks to detect concurrent input changes.'''
    data_dir = Path(data_dir)
    safe_path(data_dir)
    software = freeze_software()
    try:
        selected = _select_snapshot(data_dir, request)
        if _select_snapshot(data_dir, request) != selected:
            raise ValueError('selected inputs changed during validation')
    except pl.exceptions.PolarsError as error:
        raise ValueError('selected Parquet cannot satisfy its frozen schema') from error
    if freeze_software() != software:
        raise ValueError('executing software or dependency identity changed')
    sources, codes, geography, provenance = selected
    return SelectedInputs(data_dir, request, sources, codes, geography, provenance, software)
