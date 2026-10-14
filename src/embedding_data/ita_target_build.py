'''Publish and verify immutable offline ITA assignment and area-mix bundles.'''

import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from embedding_data import geography_references as gr
from embedding_data import ita_area_mix as area_mix
from embedding_data import ita_assignment as assignment
from embedding_data import ita_assignment_acquire as acquisition
from embedding_data import ita_assignment_prepare as preparation
from embedding_data import manifest, paths, target_contract, target_io

OUTPUT_NAMES = (
    'ita_county_assignments.parquet', 'ita_area_mix.parquet',
    'county_denominators.parquet', 'target_flag_counts.parquet', 'inputs.json', 'report.json',
)
CONTRACTS = {
    'preparation': 'ita-assignment-inputs-v1', 'assignment': 'ita-assignment-v1',
    'target_schema': 'targets-v1', 'estimator': 'ita-area-mix-v1',
    'request_identity': 'ita-request-v1',
}
REFERENCE_FRAMES = {
    'administrative': '2025', 'cbsa': 'July 2023', 'hud': '2025Q4',
    'census_benchmark': 'Public_AR_Current', 'census_vintage': 'ACS2025_Current',
}
RULES = {
    'counting_unit': 'submitted establishment-year record', 'weight': 1,
    'duplicate_policy': 'preserve source order and multiplicity, including exact duplicates',
    'eligibility': '2023, assigned compatible county, native six-digit NAICS 2022',
    'excluded_industry': ['crosswalked', 'ambiguous', 'unresolved'],
    'diagnostics_only': ['employment', 'hours', 'filing-rule flags'],
    'size_gate': 'pending; no count threshold set or passed', 'se_method': 'none',
    'universe': area_mix.UNIVERSE,
}


def _options(assignment_run_id: str, target_run_id: str, year: int) -> None:
    if type(year) is not int or year != 2023:
        raise ValueError('ITA targets support only year 2023')
    for run_id in (assignment_run_id, target_run_id):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', run_id):
            raise ValueError('unsafe run ID')


def _software() -> dict:
    return {**preparation.software_contract(),
            'implementation': preparation.module_hashes(
                preparation.FROZEN_MODULES + preparation.TARGET_MODULES),
            'pyproject_sha256': manifest.sha256_file(paths.PROJECT_ROOT / 'pyproject.toml')}


def _execution() -> dict:
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=paths.PROJECT_ROOT, text=True).strip()
    return {'commit': git('rev-parse', 'HEAD'),
            'dirty': bool(git('status', '--porcelain', '--untracked-files=normal')),
            'created_at': datetime.now(UTC).isoformat()}


def _json(file: Path) -> dict:
    return json.loads(file.read_text(encoding='utf-8'))


def _provenance(data_dir, prepared, evidence, target_run_id, software, execution):
    selected = prepared.selected
    citations = {}
    for citation in [*selected.provenance['raw'], *evidence.provenance['raw']]:
        if citation['path'] in citations and citations[citation['path']] != citation:
            raise ValueError('conflicting raw provenance')
        citations[citation['path']] = citation
    raw = target_io.verify_raw(data_dir, list(citations.values()))
    source_files = pl.scan_parquet(selected.canonical).filter(
        pl.col('year_filing_for').eq(2023)).select('source_file').unique().collect()
    source_names = set(source_files['source_file'].to_list())
    target_sources = [item for item in raw if Path(item['path']).name in source_names
                      or item['path'] in source_names]
    if len(target_sources) != len(source_names):
        raise ValueError('selected target source files lack raw citations')
    bundles = {}
    for family, directory in [('codes', selected.canonical.parent),
                               ('geography', selected.geography['county_reference'].parent)]:
        bundles[family] = {**selected.provenance[family],
                           'outputs': _json(directory / 'outputs.json')}
    return {
        'contracts': CONTRACTS, 'reference_frames': REFERENCE_FRAMES, 'rules': RULES,
        'assignment_run_id': prepared.directory.name, 'target_run_id': target_run_id,
        'year': 2023, 'execution': execution, 'fixture_inputs': prepared.inputs['fixture_inputs'],
        'source_parquet': selected.provenance['source_parquet'],
        'canonical': prepared.inputs['canonical'], 'bundles': bundles,
        'preparation': {'inputs': prepared.inputs,
                        'outputs': _json(prepared.directory / 'outputs.json'),
                        'outputs_sha256': manifest.sha256_file(
                            prepared.directory / 'outputs.json')},
        'acquisition': evidence.provenance, 'software': software,
        'versions': {'codes': 'codes-ita-v1', 'crosswalk': {
                         'implementation_sha256':
                             software['implementation']['naics_relationships'],
                         'codes_run_id': selected.provenance['codes']['run_id']},
                     'normalization': preparation.ZIP_VERSION, **CONTRACTS},
        'raw': raw, 'target_source_files': target_sources,
    }


def _references(prepared):
    return (pl.read_parquet(prepared.selected.codes['naics_nodes']),
            pl.read_parquet(prepared.selected.geography['county_reference']))


def _equal(actual, expected, label):
    '''Compare physical order and all values lazily, including nulls and lists.'''
    if list(actual.collect_schema().items()) != list(expected.collect_schema().items()):
        raise ValueError(f'{label}: schema differs')
    left = actual.with_row_index('_position')
    right = expected.with_row_index('_position')
    joined = left.join(right, on='_position', how='full', coalesce=True, suffix='_expected',
                       validate='1:1')
    columns = actual.collect_schema().names()
    different = pl.any_horizontal([pl.col(c).ne_missing(pl.col(c + '_expected')) for c in columns])
    counts = (actual.select(pl.len()).collect().item(), expected.select(pl.len()).collect().item())
    if counts[0] != counts[1] or joined.select(different.any()).collect().item():
        raise ValueError(f'{label}: serialized rows or order differ')


def _report(directory, assignments, result, evidence):
    return {**assignment.assignment_report(assignments), **result.report,
            'contracts': CONTRACTS, 'reference_frames': REFERENCE_FRAMES,
            'coverage_limits': {'universe': area_mix.UNIVERSE,
                                'current_frame': evidence.provenance['current_frame_limit'],
                                'county_accuracy': 'not measured', 'size_gate': 'pending'},
            'tables': target_io.inventory(directory, [name for name in OUTPUT_NAMES
                                                       if name.endswith('.parquet')])}


def _validate_evidence(assignments, prepared, evidence, counties):
    indexed = assignments.select('source_row', 'request_id')
    _equal(indexed, pl.scan_parquet(prepared.source_index), 'assignment request identity')
    response_columns = list(assignment.RESPONSE_SCHEMA)
    actual = assignments.select(response_columns).unique().sort('request_id')
    _equal(actual, evidence.responses.sort('request_id'), 'assignment response evidence')
    hud = pl.read_parquet(prepared.selected.geography['hud_zip_lookup'])
    normalized = assignments.select('source_row', pl.col('zip_code').map_elements(
        assignment.zip_key, return_dtype=pl.String).alias('zip_key'))
    _equal(assignments.select('source_row', 'zip_key'), normalized, 'assignment ZIP identity')
    expected = normalized.join(hud.lazy(), on='zip_key', how='left', validate='m:1')
    defaults = []
    for name, dtype in assignment.LOOKUP_SCHEMA.items():
        if dtype == pl.Int64:
            defaults.append(pl.col(name).fill_null(0))
        elif dtype == pl.Boolean:
            defaults.append(pl.col(name).fill_null(False))
        elif dtype == pl.List(pl.String):
            defaults.append(pl.col(name).fill_null(pl.lit([], dtype=dtype)))
    columns = ['source_row', *assignment.LOOKUP_SCHEMA]
    expected = expected.with_columns(*defaults, pl.col('eligibility_status').fill_null('absent'))
    _equal(assignments.select(columns), expected.select(columns).sort('source_row'),
           'assignment HUD evidence')
    returned = pl.col('geocode_county_geoid')
    excluded = returned.str.slice(0, 2).is_in(
        assignment.OUT_OF_SCOPE_COUNTY_PREFIXES).fill_null(False)
    checks = assignments.select(
        pl.col('state').str.strip_chars().str.to_uppercase().is_in(
            assignment.OUT_OF_SCOPE_STATES).fill_null(False)
            .alias('flag_delivered_state_out_of_scope'),
        excluded.alias('flag_geocode_county_out_of_scope'),
        returned.is_not_null().and_(excluded.not_()).and_(
            returned.is_in(counties['county_geoid'].to_list()).fill_null(False).not_())
            .alias('flag_geocode_county_incompatible'),
        returned.str.contains(r'^090[0-9]{2}$').fill_null(False)
            .alias('flag_geocode_county_legacy_ct'),
        pl.any_horizontal([pl.col(c).fill_null('').str.strip_chars().eq('')
                           for c in ['street_address', 'city', 'state', 'zip_key']])
            .alias('flag_request_incomplete'))
    _equal(assignments.select(checks.collect_schema().names()), checks,
           'assignment diagnostic flags')


def _validate_serialized(directory, prepared, evidence):
    nodes, counties = _references(prepared)
    canonical = pl.scan_parquet(prepared.selected.canonical)
    assignments = pl.scan_parquet(directory / 'ita_county_assignments.parquet')
    assignment.validate_assignments(assignments, canonical, counties)
    _validate_evidence(assignments, prepared, evidence, counties)
    result = area_mix.estimate(assignments, nodes)
    serialized = area_mix.AreaMix(
        pl.scan_parquet(directory / 'ita_area_mix.parquet'),
        pl.scan_parquet(directory / 'county_denominators.parquet'),
        pl.scan_parquet(directory / 'target_flag_counts.parquet'), result.report)
    area_mix.validate_area_mix(serialized, nodes, counties)
    for label in ('targets', 'denominators', 'flag_counts'):
        _equal(getattr(serialized, label), getattr(result, label), label)
    return _report(directory, assignments, result, evidence)


def _verify(directory: Path, data_dir: Path) -> dict:
    gr.safe_path(directory, data_dir)
    if {p.name for p in directory.iterdir()} != {*OUTPUT_NAMES, 'outputs.json'}:
        raise ValueError('target bundle file set differs')
    target_io.verify_inventory(directory, _json(directory / 'outputs.json'), set(OUTPUT_NAMES))
    inputs = _json(directory / 'inputs.json')
    _options(inputs['assignment_run_id'], inputs['target_run_id'], inputs['year'])
    if directory.name not in (inputs['target_run_id'], inputs['target_run_id'] + '.part'):
        raise ValueError('target run ID differs from directory')
    prepared = preparation.check_preparation(data_dir, inputs['assignment_run_id'])
    evidence = acquisition.read_evidence(data_dir, prepared)
    expected = _provenance(data_dir, prepared, evidence, inputs['target_run_id'],
                           _software(), inputs['execution'])
    if inputs != expected:
        raise ValueError('target input/software provenance differs')
    report = _validate_serialized(directory, prepared, evidence)
    if _json(directory / 'report.json') != report:
        raise ValueError('target report differs from verified serialized tables')
    for name in ('inputs.json', 'report.json', 'outputs.json'):
        value = _json(directory / name)
        canonical = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                               allow_nan=False) + '\n'
        if (directory / name).read_text(encoding='utf-8') != canonical:
            raise ValueError('noncanonical target JSON')
    return report


def verify_bundle(directory: Path, data_dir: Path) -> dict:
    '''Verify bytes, cited inputs, assignments, estimates and report entirely offline.'''
    if directory.name.endswith('.part'):
        raise ValueError('interrupted target bundle is not published')
    return _verify(directory, data_dir)


def build(data_dir: Path, assignment_run_id: str, target_run_id: str, *, year: int = 2023) -> Path:
    _options(assignment_run_id, target_run_id, year)
    final, staging = target_io.stage(
        paths.derived_dir(data_dir, 'targets'), target_run_id, data_dir)
    prepared = preparation.check_preparation(data_dir, assignment_run_id)
    evidence = acquisition.read_evidence(data_dir, prepared)
    software = _software()
    nodes, counties = _references(prepared)
    assigned = assignment.assign(
        pl.scan_parquet(prepared.selected.canonical), pl.scan_parquet(prepared.source_index),
        evidence.responses, pl.read_parquet(prepared.selected.geography['hud_zip_lookup']),
        counties)
    assigned.sink_parquet(staging / 'ita_county_assignments.parquet')
    serialized = pl.scan_parquet(staging / 'ita_county_assignments.parquet')
    assignment.validate_assignments(serialized, pl.scan_parquet(prepared.selected.canonical),
                                    counties)
    result = area_mix.estimate(serialized, nodes, year=year)
    area_mix.validate_area_mix(result, nodes, counties)
    target_contract.write_targets(result.targets, staging / 'ita_area_mix.parquet')
    result.denominators.sink_parquet(staging / 'county_denominators.parquet')
    result.flag_counts.sink_parquet(staging / 'target_flag_counts.parquet')
    target_io.write_json(staging / 'inputs.json', _provenance(
        data_dir, prepared, evidence, target_run_id, software, _execution()))
    target_io.write_json(staging / 'report.json', _report(staging, serialized, result, evidence))
    target_io.write_json(
        staging / 'outputs.json', target_io.inventory(staging, list(OUTPUT_NAMES)))
    _verify(staging, data_dir)
    # Last boundary: recheck pinned bytes, evidence and software after serialized checks.
    fresh = preparation.check_preparation(data_dir, assignment_run_id)
    evidence.verify()
    if fresh.inputs != prepared.inputs or _software() != software:
        raise ValueError('inputs or software changed during target build')
    target_io.verify_raw(data_dir, _json(staging / 'inputs.json')['raw'])
    target_io.verify_inventory(staging, _json(staging / 'outputs.json'), set(OUTPUT_NAMES))
    if {p.name for p in staging.iterdir()} != {*OUTPUT_NAMES, 'outputs.json'}:
        raise ValueError('target bundle file set changed before publication')
    gr.safe_path(final, data_dir)
    if gr.occupied(final):
        raise ValueError('final target name already exists')
    staging.rename(final)
    return final
