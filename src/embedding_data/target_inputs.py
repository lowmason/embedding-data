'''Select and reverify pinned classification, geography and full ITA source inputs.'''

import json
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import polars as pl

from embedding_data import classification_tables as ct
from embedding_data import (
    code_build,
    filing_rules,
    geography_build,
    geography_hud,
    ita_summary,
    manifest,
    naics_relationships,
    paths,
    target_io,
)
from embedding_data import geography_references as gr
from embedding_data import geography_tables as gt
from embedding_data import ita_naics_mapping as mapping

PRODUCTION_PINS = {
    'codes': ('stage4_v11_20261013_r2',
              '15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a'),
    'geography': ('stage5_geography_20261014',
                  '5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d'),
}
CANONICAL_SCHEMA = {**code_build.SUMMARY_SCHEMA, **mapping.MAPPING_SCHEMA,
                    **filing_rules.FILING_COLUMNS}
CODE_SCHEMAS = {
    'naics_nodes': ct.NODE_SCHEMA, 'naics_edges': ct.EDGE_SCHEMA,
    'soc_nodes': ct.NODE_SCHEMA, 'soc_edges': ct.EDGE_SCHEMA,
    'naics_native_nodes': ct.NODE_SCHEMA, 'naics_concordance': naics_relationships.RELATION_SCHEMA,
    'filing_rules': filing_rules.RULE_SCHEMA, 'code_paths': ct.PATH_SCHEMA,
    'filing_rule_labels': filing_rules.LABEL_SCHEMA,
    'filing_rule_membership': filing_rules.MEMBERSHIP_SCHEMA,
    'ita_naics_lookup': mapping.LOOKUP_SCHEMA, 'ita_300a_canonical': CANONICAL_SCHEMA,
}
REFERENCE_FRAMES = {'administrative': '2025', 'omb': 'July 2023', 'hud': '2025Q4'}


@dataclass(frozen=True)
class SelectedInputs:
    summary: Path
    canonical: Path
    codes: dict[str, Path]
    geography: dict[str, Path]
    provenance: dict

    def verify(self, data_dir: Path) -> None:
        selected = select(
            data_dir, self.provenance['codes']['run_id'], self.provenance['geography']['run_id'],
            codes_outputs_sha256=self.provenance['codes']['outputs_sha256'],
            geography_outputs_sha256=self.provenance['geography']['outputs_sha256'])
        if selected != self:
            raise ValueError('selected paths, source or cited provenance changed')


def _bundle(data_dir, family, run_id, checksum, schemas, version):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', run_id):
        raise ValueError('unsafe selected run ID')
    if checksum is None:
        production_run, checksum = PRODUCTION_PINS[family]
        if run_id != production_run:
            raise ValueError('a different selected run requires an explicit detached checksum')
    if not re.fullmatch(r'[0-9a-f]{64}', checksum):
        raise ValueError('invalid detached checksum')
    directory = paths.derived_dir(data_dir, family) / run_id
    gr.safe_path(directory, data_dir)
    outputs = target_io.relative_file(directory, 'outputs.json')
    if manifest.sha256_file(outputs) != checksum:
        raise ValueError(f'{family}: detached inventory checksum differs')
    expected = json.loads(outputs.read_text())
    names = {name + '.parquet' for name in schemas} | {'inputs.json', 'report.json'}
    target_io.verify_inventory(directory, expected, names)
    inputs = json.loads((directory / 'inputs.json').read_text())
    report = json.loads((directory / 'report.json').read_text())
    if (inputs['schema_version'] != version or report['schema_version'] != version
            or inputs['run_id'] != run_id):
        raise ValueError(f'{family}: incompatible schema version or run identity')
    if family == 'geography' and inputs['reference_frames'] != REFERENCE_FRAMES:
        raise ValueError('incompatible geography reference frames')
    if set(report['tables']) != {name + '.parquet' for name in schemas}:
        raise ValueError('report table inventory differs')
    files = {}
    for name, schema in schemas.items():
        file = directory / (name + '.parquet')
        frame = pl.scan_parquet(file)
        actual = frame.collect_schema()
        recorded = report['tables'][file.name]
        if (list(actual.items()) != list(schema.items())
                or recorded['schema'] != {c: str(t) for c, t in actual.items()}
                or recorded['rows'] != frame.select(pl.len()).collect().item()):
            raise ValueError(f'{name}: rows or ordered schema differs')
        files[name] = file
    return files, inputs, {'run_id': run_id, 'outputs_sha256': checksum}


def require_source_parity(summary: Path, canonical: Path) -> None:
    left = pl.scan_parquet(summary).with_row_index('_row')
    right = pl.scan_parquet(canonical).select(ita_summary.COLUMNS).with_row_index('_row')
    if list(left.collect_schema().items()) != list(right.collect_schema().items()):
        raise ValueError('canonical source prefix schema differs')
    joined = left.join(right, on='_row', how='full', coalesce=True, suffix='_canonical',
                       validate='1:1')
    different = pl.any_horizontal([
        pl.col(c).ne_missing(pl.col(c + '_canonical')) for c in ita_summary.COLUMNS])
    n_left = left.select(pl.len()).collect().item()
    n_right = right.select(pl.len()).collect().item()
    if n_left != n_right or joined.filter(different).select(pl.len()).collect().item():
        raise ValueError('source/canonical physical row order or multiplicity differs')


def validate_native(canonical: pl.LazyFrame, nodes: pl.DataFrame) -> None:
    '''Fail contradictory native assertions across every year before target filtering.'''
    if list(nodes.schema.items()) != list(ct.NODE_SCHEMA.items()):
        raise ValueError('incompatible NAICS node schema')
    leaves = nodes.filter(pl.col('system').eq('naics').and_(pl.col('vintage').eq(2022))
                          .and_(pl.col('level').eq('national_industry')))
    if leaves.is_empty() or leaves['node_id'].n_unique() != leaves.height:
        raise ValueError('missing or duplicate NAICS 2022 national-industry nodes')
    native = pl.col('naics_mapping_status').eq('native_2022')
    expected_native = pl.col('naics_year').eq(2022).and_(
        pl.col('naics_code').is_in(leaves['code'].to_list())).fill_null(False)
    if canonical.filter(native.ne_missing(expected_native)).select(pl.len()).collect().item():
        raise ValueError('native status contradicts delivered code and vintage')
    joined = canonical.join(leaves.lazy().select(
        pl.col('node_id').alias('_native_node'), pl.col('code').alias('_native_code')),
        left_on='naics_2022_node_id', right_on='_native_node', how='left', validate='m:1')
    valid = pl.all_horizontal(
        pl.col('naics_year').eq(2022),
        pl.col('naics_code').str.contains(r'^[0-9]{6}$'),
        pl.col('naics_2022_code').eq(pl.col('naics_code')),
        pl.col('_native_code').eq(pl.col('naics_code')),
        pl.col('naics_2022_candidates').list.len().eq(1),
        pl.col('naics_2022_candidates').list.first().eq(pl.col('naics_code')),
        *[pl.col(c).eq(False) for c in (
            'flag_naics_crosswalked', 'flag_naics_ambiguous', 'flag_naics_unresolved')])
    if joined.filter(native.and_(valid.fill_null(False).not_())).select(pl.len()).collect().item():
        raise ValueError('contradictory native NAICS assertion')


def _validate_codes(files):
    tables = {name: pl.read_parquet(file) for name, file in files.items()
              if name != 'ita_300a_canonical'}
    expected_paths = pl.concat([
        ct.forest(tables[system + '_nodes'], tables[system + '_edges'])
        for system in ('naics', 'soc')]).sort('node_id')
    if not expected_paths.equals(tables['code_paths'].sort('node_id')):
        raise ValueError('classification paths contradict selected forests')
    native = tables['naics_native_nodes']
    if not native.filter(pl.col('vintage').eq(2022)).sort('node_id').equals(
            tables['naics_nodes'].sort('node_id')):
        raise ValueError('canonical and native NAICS nodes differ')
    filing_rules.validate_rules(tables['filing_rules'], native)
    filing_rules.validate_membership(tables['filing_rule_membership'], native)
    canonical = pl.scan_parquet(files['ita_300a_canonical'])
    code_build.validate_canonical(files['ita_300a_canonical'], CANONICAL_SCHEMA)
    validate_native(canonical, tables['naics_nodes'])
    keys = canonical.select(*mapping.KEY_SCHEMA).unique().collect()
    expected_lookup = mapping.build_lookup(
        keys, native, tables['naics_concordance'],
        tables['code_paths'].join(tables['naics_nodes'].select('node_id'), on='node_id'))
    if not expected_lookup.equals(tables['ita_naics_lookup']):
        raise ValueError('selected mapping lookup contradicts references')
    joined = canonical.join(expected_lookup.lazy(), on=list(mapping.KEY_SCHEMA),
                            how='left', nulls_equal=True, suffix='_expected', validate='m:1')
    differences = pl.any_horizontal([
        pl.col(c).ne_missing(pl.col(c + '_expected')) for c in mapping.MAPPING_SCHEMA])
    if joined.filter(differences).select(pl.len()).collect().item():
        raise ValueError('canonical mapping assertions contradict selected references')


def _validate_geography(data_dir, files, inputs):
    registry = {name: gr.Reference(**{**reference,
                'state_scope': frozenset(reference['state_scope'])})
                for name, reference in inputs['references'].items()}
    sources = gr.read_sources(data_dir, registry=registry)
    tables = {name: pl.read_parquet(file) for name, file in files.items()}
    gt.validate_tables(tables, sources)
    annotated = geography_hud.annotate(sources['hud'], tables['county_reference'])
    if not annotated.equals(tables['hud_zip_county']):
        raise ValueError('HUD annotations contradict selected county reference')
    if not geography_hud.lookup(tables['hud_zip_county']).equals(tables['hud_zip_lookup']):
        raise ValueError('HUD lookup contradicts all original positive candidates')


def select(data_dir: Path, codes_run: str, geography_run: str, *,
           codes_outputs_sha256: str | None = None,
           geography_outputs_sha256: str | None = None) -> SelectedInputs:
    codes, code_inputs, code_pin = _bundle(
        data_dir, 'codes', codes_run, codes_outputs_sha256, CODE_SCHEMAS,
        code_build.SCHEMA_VERSION)
    geography, geo_inputs, geo_pin = _bundle(
        data_dir, 'geography', geography_run, geography_outputs_sha256,
        geography_build.SCHEMAS, geography_build.SCHEMA_VERSION)
    citations = [*code_inputs['raw'], *geo_inputs['raw']]
    for name in ('summary_data_dictionary.pdf', 'ITA_Data_Dictionary.pdf'):
        file = target_io.relative_file(data_dir / 'raw', 'osha/summary/' + name)
        citations.append(json.loads(json.dumps(asdict(manifest.entry_for(
            paths.manifest_path(data_dir), file)))))
    by_path = {}
    for citation in citations:
        if citation['path'] in by_path and by_path[citation['path']] != citation:
            raise ValueError('conflicting citations for the same raw path')
        by_path[citation['path']] = citation
    raw = target_io.verify_raw(data_dir, list(by_path.values()))
    source = code_inputs['source_parquet']
    summary = target_io.relative_file(data_dir, source['path'])
    if summary != paths.derived_dir(data_dir, 'osha') / ita_summary.TABLE_NAME:
        raise ValueError('unexpected selected source path')
    if (manifest.sha256_file(summary) != source['sha256']
            or summary.stat().st_size != source['size']):
        raise ValueError('selected source hash or size differs')
    source_record = target_io.file_record(summary)
    with tempfile.TemporaryDirectory() as work:
        frame, source_citations = code_build.check_source(data_dir, Path(work))
    years = frame.select('year_filing_for').unique().collect().to_series().to_list()
    if sorted(years) != list(range(2016, 2026)):
        raise ValueError('selected source must cover 2016 through 2025')
    for citation in json.loads(json.dumps(source_citations)):
        if by_path.get(citation['path']) != citation:
            raise ValueError('source release missing from selected bundle citations')
    canonical = codes['ita_300a_canonical']
    require_source_parity(summary, canonical)
    _validate_codes(codes)
    _validate_geography(data_dir, geography, geo_inputs)
    return SelectedInputs(summary, canonical, codes, geography, {
        'codes': code_pin, 'geography': geo_pin, 'raw': raw,
        'source_parquet': {'path': source['path'], **source_record},
        'reference_frames': REFERENCE_FRAMES.copy()})
