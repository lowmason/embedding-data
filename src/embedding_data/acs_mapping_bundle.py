'''Immutable offline ACS mapping publication, reconstruction and ordered replay.'''

import re
import shutil
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from embedding_data import ipums_parity, manifest, target_io
from embedding_data.acs_area_mapping import build_area_lookup, observed_area_keys
from embedding_data.acs_area_references import read_area_evidence, read_role_rules
from embedding_data.acs_code_mapping import build_code_lookup, observed_code_keys
from embedding_data.acs_code_references import read_code_evidence
from embedding_data.acs_geography_factors import build_factor_tables
from embedding_data.acs_mapping_companions import (
    annotate_source,
    companion_diagnostics,
    validate_companion,
    write_companion,
)
from embedding_data.acs_mapping_contract import (
    AREA_RULE_VERSION,
    CODE_RULE_VERSION,
    FORMAT_VERSION,
    SelectionRequest,
)
from embedding_data.acs_mapping_inputs import (
    SOFTWARE_ROOT,
    _read_json,
    freeze_software,
    require_detached,
    select_inputs,
)
from embedding_data.acs_mapping_io import publish_directory, reserve_run, safe_path
from embedding_data.acs_mapping_references import check_references

TABLES = ('acs_code_lookup', 'acs_area_lookup', 'puma_county_factors',
          'puma_msa_factors', 'puma_msa_coverage', 'acs_core_canonical',
          'acs_five_year_canonical', 'acs_vintage_canonical')
FILES = tuple(name + '.parquet' for name in TABLES) + ('inputs.json', 'report.json')
LIMITS = {
    'evaluation_inputs_only': True, 'individual_locations_inferred': False,
    'classification_possibilities_weighted': False, 'population_year': 2020,
    'puma_vintage': 2020, 'county_composition_year': 2022,
    'county_inventory_vintage': 2025, 'msa_delineation': 'July 2023',
    'universes_or_headline_inclusion_adopted': False,
    'full_data_acceptance': False, 'complete_eight_family_v12': False,
    'later_stages_9_through_13': False,
}
FRAMES = {key: LIMITS[key] for key in ('population_year', 'puma_vintage',
          'county_composition_year', 'county_inventory_vintage', 'msa_delineation')}


def run_directory(data_dir: Path, run_id: str) -> Path:
    if not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', run_id):
        raise ValueError('unsafe run ID')
    directory = Path(data_dir) / 'derived/acs/mapping' / run_id
    safe_path(directory)
    return directory


def _git_label():
    try:
        return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=SOFTWARE_ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _inputs(selected, snapshot, run_id, created_at):
    sources = {}
    for profile, source in selected.sources.items():
        sources[profile] = {**asdict(source),
                            'parquet': source.parquet.relative_to(selected.data_dir).as_posix()}
    return {
        'schema_version': FORMAT_VERSION, 'run_id': run_id, 'created_at': created_at,
        'git_commit_informational': _git_label(),
        'selected_upstreams': {'request': asdict(selected.request),
                               'provenance': selected.provenance},
        'sources': sources,
        'references': {'reference_id': snapshot.reference_id,
                       'receipt_sha256': snapshot.receipt_sha256, 'receipt': snapshot.receipt},
        'rules': {'classification': CODE_RULE_VERSION, 'area': AREA_RULE_VERSION,
                  'transform': FORMAT_VERSION},
        'frames': FRAMES, 'software': selected.software,
    }


def _derive(selected, snapshot):
    codes = read_code_evidence(snapshot, selected)
    geography = read_area_evidence(snapshot, selected)
    factors = build_factor_tables(geography, selected)
    code_lookup = build_code_lookup(observed_code_keys(selected.sources), codes, selected)
    rules = read_role_rules(snapshot, selected.sources)
    areas = build_area_lookup(observed_area_keys(selected.sources), rules, geography, factors)
    tables = dict(zip(TABLES[:5], (code_lookup, areas, factors.county, factors.msa,
                                  factors.coverage), strict=True))
    return tables, factors, codes, geography


def _table_summary(file):
    record = target_io.file_record(file)
    return {key: record[key] for key in ('columns', 'schema', 'rows')}


def _report(directory, selected, tables, factors, codes, geography, run_id, created_at):
    companions = {}
    for profile, source in selected.sources.items():
        name = 'acs_' + profile.split('/')[1] + '_canonical'
        file = directory / (name + '.parquet')
        validate_companion(source, file, tables['acs_code_lookup'],
                           tables['acs_area_lookup'], factors)
        companions[profile] = companion_diagnostics(source, file)
    return {
        'schema_version': FORMAT_VERSION, 'run_id': run_id, 'created_at': created_at,
        'tables': {name: _table_summary(directory / (name + '.parquet')) for name in TABLES},
        'classifications': {'reference_diagnostics': codes.diagnostics,
                            'source_measurements': companions},
        'areas': {'reference_diagnostics': geography.reference_provenance,
                  'statuses': tables['acs_area_lookup'].group_by('area_status').len()
                      .sort('area_status').to_dicts()},
        'factors': factors.diagnostics,
        'v8': {'status': 'measured', 'adopted': False,
               'composition_conflicts': 0, 'factor_conservation': 'pass'},
        'limits': LIMITS,
    }


def _validate_outputs(directory, tables):
    for name, expected in tables.items():
        actual = pl.read_parquet(directory / (name + '.parquet'))
        if list(actual.schema.items()) != list(expected.schema.items()):
            raise ValueError('output reference ordered schema differs from reconstructed evidence')
        if not actual.equals(expected):
            raise ValueError('output reference table differs from reconstructed evidence')


def publish_validated(staging, final, selected, snapshot, data_dir):
    selected.verify()
    check_references(data_dir, snapshot.reference_id,
                     expected_receipt_sha256=snapshot.receipt_sha256)
    if freeze_software() != selected.software:
        raise ValueError('executing software or dependency identity changed before publication')
    target_io.write_json(staging / 'outputs.json', target_io.inventory(staging, list(FILES)))
    pin = manifest.sha256_file(staging / 'outputs.json')
    publish_directory(staging, final)
    return {'run_id': final.name, 'directory': str(final), 'outputs_sha256': pin}


def build(data_dir: Path, run_id: str, request: SelectionRequest, reference_id: str,
          *, expected_reference_receipt_sha256: str) -> dict:
    final, staging = reserve_run(data_dir, run_id)
    try:
        selected = select_inputs(data_dir, request)
        snapshot = check_references(data_dir, reference_id,
                                    expected_receipt_sha256=expected_reference_receipt_sha256)
        tables, factors, codes, geography = _derive(selected, snapshot)
        created_at = datetime.now(UTC).isoformat()
        for name, frame in tables.items():
            frame.write_parquet(staging / (name + '.parquet'))
        for profile, source in selected.sources.items():
            name = 'acs_' + profile.split('/')[1] + '_canonical.parquet'
            write_companion(annotate_source(source, tables['acs_code_lookup'],
                                            tables['acs_area_lookup'], factors),
                            source, staging / name)
        _validate_outputs(staging, tables)
        target_io.write_json(staging / 'inputs.json',
                             _inputs(selected, snapshot, run_id, created_at))
        target_io.write_json(staging / 'report.json', _report(
            staging, selected, tables, factors, codes, geography, run_id, created_at))
        # Strict reread also rejects nonfinite values and duplicate keys before publication.
        _read_json(staging / 'inputs.json')
        _read_json(staging / 'report.json')
        if freeze_software() != selected.software:
            raise ValueError('executing software or dependency identity changed')
        return publish_validated(staging, final, selected, snapshot, data_dir)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def verify_bundle(directory: Path, data_dir: Path, *, expected_outputs_sha256: str) -> dict:
    directory, data_dir = Path(directory), Path(data_dir)
    safe_path(directory)
    # Authenticate authority before accepting any local inventory or input description.
    safe_path(directory / 'outputs.json')
    require_detached(directory / 'outputs.json', expected_outputs_sha256)
    if {file.name for file in directory.iterdir()} != set(FILES) | {'outputs.json'}:
        raise ValueError('missing or extra bundle paths')
    if any(not file.is_file() or file.is_symlink() for file in directory.iterdir()):
        raise ValueError('bundle contains a directory or symlink')
    inventory = _read_json(directory / 'outputs.json')
    target_io.verify_inventory(directory, inventory, set(FILES))
    if inventory != target_io.inventory(directory, list(FILES)):
        raise ValueError('output inventory records are incomplete or contain extra fields')
    inputs, report = (_read_json(directory / name) for name in ('inputs.json', 'report.json'))
    if inputs.get('run_id') != directory.name or report.get('run_id') != directory.name:
        raise ValueError('bundle run identity differs')
    selected = select_inputs(data_dir, SelectionRequest(**inputs['selected_upstreams']['request']))
    reference = inputs['references']
    snapshot = check_references(data_dir, reference['reference_id'],
                                expected_receipt_sha256=reference['receipt_sha256'])
    expected = _inputs(selected, snapshot, directory.name, inputs['created_at'])
    expected['git_commit_informational'] = inputs['git_commit_informational']
    if inputs != expected:
        raise ValueError('input provenance, rules, frames or software changed')
    tables, factors, codes, geography = _derive(selected, snapshot)
    _validate_outputs(directory, tables)
    reconstructed = _report(directory, selected, tables, factors, codes, geography,
                             directory.name, report['created_at'])
    if report != reconstructed:
        raise ValueError('substantive report differs from reconstructed measurements')
    selected.verify()
    check_references(data_dir, snapshot.reference_id,
                     expected_receipt_sha256=snapshot.receipt_sha256)
    return {'run_id': directory.name, 'status': 'verified',
            'outputs_sha256': expected_outputs_sha256,
            'mapping_gate': {'status': 'measured', 'adopted': False},
            'factor_gate': report['v8'], 'limits': LIMITS}


def substantive_report(report: dict) -> dict:
    return {key: value for key, value in report.items() if key not in {'run_id', 'created_at'}}


def compare_runs(first: Path, second: Path) -> dict:
    for directory in (first, second):
        safe_path(directory)
        for name in (*TABLES, 'report'):
            suffix = '.json' if name == 'report' else '.parquet'
            safe_path(directory / (name + suffix))
    tables = {name: ipums_parity.compare_ordered(
        pl.scan_parquet(first / (name + '.parquet')),
        pl.scan_parquet(second / (name + '.parquet'))) for name in TABLES}
    reports_equal = substantive_report(_read_json(first / 'report.json')) == substantive_report(
        _read_json(second / 'report.json'))
    return {'equal': reports_equal and all(row['values_equal'] for row in tables.values()),
            'tables': tables, 'substantive_report_equal': reports_equal,
            'trust_established': False}
