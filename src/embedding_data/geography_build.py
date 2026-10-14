import json
import re
import sys
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

import polars as pl

from embedding_data import geography_hud as gh
from embedding_data import geography_references as gr
from embedding_data import geography_tables as gt
from embedding_data import manifest, paths

SCHEMA_VERSION = 'geography-v1'
SCHEMAS = {**gt.SCHEMAS, **gh.SCHEMAS}


def write_json(file, payload) -> None:
    file.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + '\n',
                    encoding='utf-8')


def report(tables, sources) -> dict:
    counties, cbsa = tables['county_reference'], tables['cbsa_reference']
    hud, lookup = tables['hud_zip_county'], tables['hud_zip_lookup']
    scoped_states = counties['state_fips'].unique().to_list()
    excluded_members = sources['members'].filter(pl.col('state_fips').is_in(scoped_states).not_())
    return {
        'schema_version': SCHEMA_VERSION, 'graph_validation': 'passed',
        'tables': {name + '.parquet': {'rows': frame.height,
                   'schema': {c: str(t) for c, t in frame.schema.items()}}
                   for name, frame in sorted(tables.items())},
        'cbsa_types': cbsa.group_by('cbsa_type').agg(
            n_cbsas=pl.len().cast(pl.Int64), n_counties=pl.col('n_counties').sum()).sort(
                'cbsa_type').to_dicts(),
        'multi_state_cbsas': cbsa.filter(pl.col('state_fips').list.len().gt(1)).height,
        'non_cbsa_counties': counties.filter(pl.col('cbsa_id').is_null()).height,
        'hud_statuses': lookup.group_by('eligibility_status').agg(
            n_zips=pl.len().cast(pl.Int64)).sort('eligibility_status').to_dicts(),
        'hud_candidate_diagnostics': {c: int(hud[c].sum()) for c in hud.columns
                                      if c.startswith('flag_') or c == 'noncounty_geography'},
        'hud_zip_diagnostics': {c: int(lookup[c].sum()) for c in lookup.columns
                                if c.startswith('flag_')},
        'hud_unexpected_in_scope_county_codes': hud.filter(
            pl.col('flag_county_incompatible')).get_column('county_geoid').n_unique(),
        'source_scope_exclusions': {
            'state_rows': sources['excluded_states'].height,
            'county_rows': sources['counties'].height - counties.height,
            'membership_rows': excluded_members.height,
            'cbsa_codes_without_scoped_members': len(set(sources['members']['cbsa_code']) -
                                                      set(cbsa['cbsa_code'])),
        },
        'limits': ['2025 common administrative frame, not historical address geography',
                   'July 2023 OMB membership; both CBSA types retained',
                   'HUD 2025Q4 singleton eligibility only; maxima are diagnostics',
                   'No establishment assignment, target construction or PUMA allocation'],
    }


def build(data_dir: Path, run_id: str, *, registry=gr.REGISTRY) -> Path:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', run_id):
        raise ValueError('run ID must contain only ASCII letters, digits, underscore or hyphen')
    root = paths.derived_dir(data_dir, 'geography')
    final, staging = root / run_id, root / (run_id + '.part')
    for file in [final, staging]:
        gr.safe_path(file, data_dir)
        if gr.occupied(file):
            raise ValueError('run or staging name already exists')
    existing = gr.preflight(data_dir, registry)
    if not all(existing.values()):
        missing = [k for k, present in existing.items() if not present]
        raise ValueError(
            f'missing manifested geography originals: {missing}; acquire/import first')
    manifest_file = paths.manifest_path(data_dir)
    manifest_hash = manifest.sha256_file(manifest_file)
    citations = [asdict(manifest.entry_for(manifest_file, gr.reference_path(data_dir, r)))
                 for r in registry.values()]
    module_names = ['geography_parsers', 'geography_tables', 'geography_hud',
                    'geography_references', 'geography_build', 'geography_cli', 'cli',
                    'classification_tables', 'ita_references', 'manifest', 'paths',
                    'osha_benchmark_download']
    code_files = [Path(__import__('embedding_data.' + name, fromlist=['__file__']).__file__)
                  for name in module_names]
    code_hashes = {file.relative_to(paths.PROJECT_ROOT).as_posix(): manifest.sha256_file(file)
                   for file in sorted(code_files)}
    lock_hash = manifest.sha256_file(paths.PROJECT_ROOT / 'uv.lock')
    sources = gr.read_sources(data_dir, registry=registry)
    tables = gt.assemble(sources)
    tables['hud_zip_county'] = gh.annotate(sources['hud'], tables['county_reference'])
    tables['hud_zip_lookup'] = gh.lookup(tables['hud_zip_county'])
    gt.validate_tables(tables, sources)
    root.mkdir(parents=True, exist_ok=True)
    staging.mkdir()
    for name, frame in tables.items():
        if frame.schema != SCHEMAS[name]:
            raise ValueError(f'{name}: incompatible output schema')
        frame.write_parquet(staging / (name + '.parquet'))
    published = {name: pl.read_parquet(staging / (name + '.parquet')) for name in SCHEMAS}
    gt.validate_tables(published, sources)
    for name in SCHEMAS:
        if published[name].schema != SCHEMAS[name] or not published[name].equals(tables[name]):
            raise ValueError(f'{name}: serialized content or schema differs')
    inventory = {
        'schema_version': SCHEMA_VERSION, 'run_id': run_id,
        'fixture': any(r.fixture for r in registry.values()),
        'reference_frames': {'administrative': '2025', 'omb': 'July 2023', 'hud': '2025Q4'},
        'raw': sorted(citations, key=lambda r: r['path']),
        'references': {k: {**asdict(r), 'state_scope': sorted(r.state_scope)}
                       for k, r in sorted(registry.items())},
        'implementation': code_hashes,
        'dependencies': {name: version(name) for name in ['embedding-data', 'polars', 'fastexcel',
                                                         'httpx', 'typer']},
        'python': sys.version,
        'uv_lock_sha256': lock_hash,
    }
    write_json(staging / 'inputs.json', inventory)
    write_json(staging / 'report.json', report(published, sources))
    names = [name + '.parquet' for name in SCHEMAS] + ['inputs.json', 'report.json']
    write_json(staging / 'outputs.json', {
        name: {'sha256': manifest.sha256_file(staging / name),
               'size': (staging / name).stat().st_size}
        for name in sorted(names)})
    if manifest.sha256_file(manifest_file) != manifest_hash:
        raise ValueError('raw manifest changed during geography build')
    for citation in citations:
        file = manifest_file.parent / citation['path']
        current = asdict(manifest.entry_for(manifest_file, file))
        if current != citation:
            raise ValueError('cited original changed during geography build')
    if any(manifest.sha256_file(paths.PROJECT_ROOT / name) != checksum
           for name, checksum in code_hashes.items()) or (
            manifest.sha256_file(paths.PROJECT_ROOT / 'uv.lock') != lock_hash):
        raise ValueError('implementation or lockfile changed during geography build')
    gr.preflight(data_dir, registry)
    gr.safe_path(final, data_dir)
    if gr.occupied(final):
        raise ValueError('run destination appeared during build')
    staging.rename(final)
    return final
