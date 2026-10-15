'''Freeze physical ITA row identity and exact Census submission tuples offline.'''

import csv
import hashlib
import importlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import polars as pl

from embedding_data import geography_references as gr
from embedding_data import manifest, paths, target_inputs, target_io
from embedding_data.ita_verification import zip_key
from embedding_data.target_inputs import SelectedInputs

IDENTITY_VERSION = 'ita-request-v1'
SCHEMA_VERSION = 'ita-assignment-inputs-v1'
ZIP_VERSION = 'ita-verification-zip-v1'
SOFTWARE_VERSION = 'ita-assignment-software-v1'
BATCH_LIMIT = 1000
SERVICE_BATCH_LIMIT = 10_000
CSV_ESCAPECHAR = '\\'
SUBMITTED = ['street', 'city', 'state', 'zip']
SOURCE_INDEX_SCHEMA = {'source_row': pl.UInt64, 'request_id': pl.String}
REQUEST_INDEX_SCHEMA = {
    'request_id': pl.String, **{c: pl.String for c in SUBMITTED},
    'n_source_rows': pl.UInt64,
}
FROZEN_MODULES = (
    'target_io', 'target_inputs', 'ita_assignment_prepare', 'ita_assignment_acquire',
    'ita_assignment', 'ita_verification', 'ita_county_verification', 'ita_verification_run',
    'ita_references', 'geography_hud', 'geography_tables', 'geography_parsers',
    'geography_references', 'geography_build', 'classification_tables', 'code_build',
    'code_references', 'filing_rules', 'ita_naics_mapping', 'naics_relationships',
    'ita_summary', 'ita_catalog', 'osha_encoding', 'osha_benchmark_download', 'manifest', 'paths',
)
TARGET_MODULES = ('target_contract', 'ita_area_mix', 'ita_target_build', 'targets_cli', 'cli')
DEPENDENCIES = ('embedding-data', 'polars', 'fastexcel', 'httpx', 'typer')


@dataclass(frozen=True)
class PreparedInputs:
    directory: Path
    selected: SelectedInputs
    inputs: dict
    source_index: Path
    request_index: Path
    batches: tuple[Path, ...]


def request_id(fields: tuple[str, str, str, str]) -> str:
    payload = json.dumps(list(fields), ensure_ascii=False, separators=(',', ':'),
                         allow_nan=False).encode('utf-8')
    return hashlib.sha256(IDENTITY_VERSION.encode('ascii') + b'\0' + payload).hexdigest()


def request_frames(canonical: pl.LazyFrame) -> tuple[pl.LazyFrame, pl.LazyFrame]:
    submitted = canonical.with_row_index('source_row').with_columns(
        pl.col('source_row').cast(pl.UInt64),
    ).select(
        'source_row', pl.col('street_address').fill_null('').alias('street'),
        pl.col('city').fill_null(''), pl.col('state').fill_null(''),
        pl.col('zip_code').map_elements(zip_key, return_dtype=pl.String)
        .fill_null('').alias('zip'),
    )
    requests_frame = submitted.group_by(SUBMITTED).agg(
        n_source_rows=pl.len().cast(pl.UInt64),
    ).with_columns(request_id=pl.struct(SUBMITTED).map_elements(
        lambda row: request_id(tuple(row[c] for c in SUBMITTED)), return_dtype=pl.String,
    )).select(list(REQUEST_INDEX_SCHEMA)).sort('request_id').collect()
    if requests_frame['request_id'].n_unique() != requests_frame.height:
        raise ValueError('request ID collision between distinct submitted tuples')
    requests = requests_frame.lazy()
    source_index = submitted.join(requests.select('request_id', *SUBMITTED),
                                  on=SUBMITTED, how='left', validate='m:1').select(
        list(SOURCE_INDEX_SCHEMA)).sort('source_row')
    return source_index, requests


def _batch_limit(limit: int) -> None:
    if type(limit) is not int or not 1 <= limit <= SERVICE_BATCH_LIMIT:
        raise ValueError('batch limit must be between 1 and 10000')


def write_batches(directory: Path, requests: pl.DataFrame, batch_limit: int) -> list[dict]:
    _batch_limit(batch_limit)
    (directory / 'requests').mkdir()
    records = []
    for number, start in enumerate(range(0, requests.height, batch_limit)):
        name = f'requests/batch_{number:05d}.csv'
        file = directory / name
        batch = requests.slice(start, batch_limit)
        with file.open('w', newline='', encoding='utf-8') as stream:
            csv.writer(stream, escapechar=CSV_ESCAPECHAR, doublequote=True).writerows(
                batch.select('request_id', *SUBMITTED).iter_rows())
        validate_batch(file, batch)
        records.append({'path': name, **target_io.file_record(file), 'rows': batch.height})
    return records


def validate_batch(file: Path, request_index: pl.DataFrame) -> list[str]:
    '''Validate one expected sorted contiguous slice of the frozen request index.'''
    if list(request_index.schema.items()) != list(REQUEST_INDEX_SCHEMA.items()):
        raise ValueError('request index schema differs')
    with file.open(newline='', encoding='utf-8') as stream:
        rows = list(csv.reader(stream, escapechar=CSV_ESCAPECHAR, doublequote=True, strict=True))
    if not rows or len(rows) > SERVICE_BATCH_LIMIT:
        raise ValueError('empty or oversized Census batch')
    ids = []
    for row in rows:
        if len(row) != 5 or not re.fullmatch(r'[0-9a-f]{64}', row[0]):
            raise ValueError('Census batch requires a lowercase SHA-256 ID and four fields')
        if request_id(tuple(row[1:])) != row[0]:
            raise ValueError('Census batch ID contradicts submitted tuple')
        ids.append(row[0])
    if len(set(ids)) != len(ids) or ids != sorted(ids):
        raise ValueError('duplicate or unordered Census request IDs')
    expected = [list(row) for row in request_index.select('request_id', *SUBMITTED).iter_rows()]
    if rows != expected:
        raise ValueError('Census batch differs from expected contiguous request slice')
    return ids


def module_hashes(modules: tuple[str, ...]) -> dict[str, str]:
    '''Hash actual executing source modules, requiring every named implementation.'''
    result = {}
    for name in modules:
        module = importlib.import_module('embedding_data.' + name)
        file = Path(module.__file__).resolve()
        if file.suffix != '.py' or not file.is_relative_to(paths.PROJECT_ROOT.resolve()):
            raise ValueError(f'{name}: implementation is not source in the execution checkout')
        result[name] = manifest.sha256_file(file)
    return result


def software_contract() -> dict:
    return {
        'contract': SOFTWARE_VERSION,
        'implementation': module_hashes(FROZEN_MODULES),
        'dependencies': {name: version(name) for name in DEPENDENCIES},
        'python': sys.version,
        'uv_lock_sha256': manifest.sha256_file(paths.PROJECT_ROOT / 'uv.lock'),
    }


def _source_metadata(selected: SelectedInputs, data_dir: Path) -> dict:
    counts = pl.scan_parquet(selected.canonical).group_by('year_filing_for').agg(
        rows=pl.len().cast(pl.UInt64)).sort('year_filing_for').collect()
    years = counts['year_filing_for'].to_list()
    if years != list(range(2016, 2026)):
        raise ValueError('source years must be exactly 2016 through 2025')
    return {
        'canonical': {'path': selected.canonical.relative_to(data_dir).as_posix(),
                      **target_io.file_record(selected.canonical)},
        'source_years': years, 'source_counts': counts.to_dicts(),
        'source_rows': counts['rows'].sum(),
    }


def _verify_indexes(directory: Path, selected: SelectedInputs, inputs: dict) -> pl.DataFrame:
    source_file = target_io.relative_file(directory, 'source_index.parquet')
    request_file = target_io.relative_file(directory, 'request_index.parquet')
    source = pl.scan_parquet(source_file)
    requests = pl.read_parquet(request_file)
    if (list(source.collect_schema().items()) != list(SOURCE_INDEX_SCHEMA.items())
            or list(requests.schema.items()) != list(REQUEST_INDEX_SCHEMA.items())):
        raise ValueError('source/request index schema differs')
    if (inputs['source_index'] != target_io.file_record(source_file)
            or inputs['request_index'] != target_io.file_record(request_file)):
        raise ValueError('frozen source/request index metadata differs')
    expected_source, expected_requests = request_frames(pl.scan_parquet(selected.canonical))
    if not requests.equals(expected_requests.collect()):
        raise ValueError('request index contradicts canonical submitted tuples/counts')
    if requests.height != inputs['distinct_requests']:
        raise ValueError('distinct request total differs')
    row_count = source.select(pl.len()).collect().item()
    if row_count != inputs['source_rows'] or requests['n_source_rows'].sum() != row_count:
        raise ValueError('source and request row totals differ')
    # Physical position is checked independently of the recorded source_row key.
    joined = source.with_row_index('_position').join(
        expected_source.with_row_index('_position'), on='_position', how='full',
        coalesce=True, suffix='_expected', validate='1:1')
    different = pl.any_horizontal([
        pl.col(c).ne_missing(pl.col(c + '_expected')) for c in SOURCE_INDEX_SCHEMA])
    if joined.filter(different).select(pl.len()).collect().item():
        raise ValueError('source row order or request mapping differs')
    return requests


def _check_directory(data_dir: Path, directory: Path, run_id: str) -> PreparedInputs:
    inputs_file = target_io.relative_file(directory, 'inputs.json')
    outputs_file = target_io.relative_file(directory, 'outputs.json')
    inputs = json.loads(inputs_file.read_text(encoding='utf-8'))
    outputs = json.loads(outputs_file.read_text(encoding='utf-8'))
    if (inputs['schema_version'] != SCHEMA_VERSION
            or inputs['identity_version'] != IDENTITY_VERSION
            or inputs['zip_normalization_version'] != ZIP_VERSION
            or inputs['assignment_run_id'] != run_id):
        raise ValueError('unsupported preparation contract or run ID')
    _batch_limit(inputs['batch_limit'])
    names = {'inputs.json', 'source_index.parquet', 'request_index.parquet'}
    names.update(batch['path'] for batch in inputs['batches'])
    target_io.verify_inventory(directory, outputs, names)
    if inputs['software'] != software_contract():
        raise ValueError('frozen assignment software/dependency/lock contract changed')
    provenance = inputs['selected']
    selected = target_inputs.select(
        data_dir, provenance['codes']['run_id'], provenance['geography']['run_id'],
        codes_outputs_sha256=provenance['codes']['outputs_sha256'],
        geography_outputs_sha256=provenance['geography']['outputs_sha256'])
    if selected.provenance != provenance:
        raise ValueError('selected input provenance changed')
    metadata = _source_metadata(selected, data_dir)
    if any(inputs[key] != value for key, value in metadata.items()):
        raise ValueError('canonical source identity, years or counts differ')
    requests = _verify_indexes(directory, selected, inputs)
    slices = list(range(0, requests.height, inputs['batch_limit']))
    if len(inputs['batches']) != len(slices):
        raise ValueError('batch inventory does not cover all requests')
    batches = []
    for number, (record, start) in enumerate(zip(inputs['batches'], slices, strict=True)):
        if record['path'] != f'requests/batch_{number:05d}.csv':
            raise ValueError('batch paths must be contiguous and ordered')
        file = target_io.relative_file(directory, record['path'])
        expected = requests.slice(start, inputs['batch_limit'])
        if record != {'path': record['path'], **target_io.file_record(file),
                      'rows': expected.height}:
            raise ValueError('batch metadata differs')
        validate_batch(file, expected)
        batches.append(file)
    return PreparedInputs(directory, selected, inputs, directory / 'source_index.parquet',
                          directory / 'request_index.parquet', tuple(batches))


def check_preparation(data_dir: Path, assignment_run_id: str) -> PreparedInputs:
    root = paths.derived_dir(data_dir, 'osha') / 'assignment-inputs'
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', assignment_run_id):
        raise ValueError('unsafe assignment run ID')
    directory = target_io.relative_file(root, assignment_run_id)
    gr.safe_path(directory, data_dir)
    return _check_directory(data_dir, directory, assignment_run_id)


def prepare(data_dir: Path, assignment_run_id: str, codes_run: str, geography_run: str, *,
            codes_outputs_sha256: str | None = None,
            geography_outputs_sha256: str | None = None) -> Path:
    final, staging = target_io.stage(paths.derived_dir(data_dir, 'osha') / 'assignment-inputs',
                                     assignment_run_id, data_dir)
    selected = target_inputs.select(
        data_dir, codes_run, geography_run, codes_outputs_sha256=codes_outputs_sha256,
        geography_outputs_sha256=geography_outputs_sha256)
    software = software_contract()
    source, requests = request_frames(pl.scan_parquet(selected.canonical))
    source.sink_parquet(staging / 'source_index.parquet')
    requests.sink_parquet(staging / 'request_index.parquet')
    requests_frame = requests.collect()
    batches = write_batches(staging, requests_frame, BATCH_LIMIT)
    inputs = {
        'schema_version': SCHEMA_VERSION, 'identity_version': IDENTITY_VERSION,
        'zip_normalization_version': ZIP_VERSION, 'assignment_run_id': assignment_run_id,
        'selected': selected.provenance, **_source_metadata(selected, data_dir),
        'software': software,
        'entry_points': {'implementation': module_hashes(('cli',)),
                         'pyproject_sha256': manifest.sha256_file(
                             paths.PROJECT_ROOT / 'pyproject.toml')},
        'execution_commit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=paths.PROJECT_ROOT, text=True).strip(),
        'fixture_inputs': any(r['client'] == 'fixture' for r in selected.provenance['raw']),
        'source_index': target_io.file_record(staging / 'source_index.parquet'),
        'request_index': target_io.file_record(staging / 'request_index.parquet'),
        'distinct_requests': requests_frame.height, 'batch_limit': BATCH_LIMIT, 'batches': batches,
    }
    target_io.write_json(staging / 'inputs.json', inputs)
    names = ['inputs.json', 'source_index.parquet', 'request_index.parquet',
             *[record['path'] for record in batches]]
    target_io.write_json(staging / 'outputs.json', target_io.inventory(staging, names))
    _check_directory(data_dir, staging, assignment_run_id)
    selected.verify(data_dir)
    if software_contract() != software:
        raise ValueError('assignment software changed during preparation')
    gr.safe_path(final, data_dir)
    if gr.occupied(final):
        raise ValueError('final preparation name already exists')
    staging.rename(final)
    return final
