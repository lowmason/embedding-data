'''Verify source parity and publish immutable offline classification bundles.'''

import json
import re
import sys
import tempfile
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

import polars as pl

from embedding_data import code_references as cr
from embedding_data import ita_summary, manifest, paths
from embedding_data.classification_tables import naics_tables, soc_tables
from embedding_data.filing_rules import (
    FILING_COLUMNS,
    FILING_KEYS,
    add_filing_flags,
    build_filing_lookup,
)
from embedding_data.ita_naics_mapping import KEY_SCHEMA, MAPPING_SCHEMA, build_lookup, enrich

SCHEMA_VERSION = 'codes-ita-v1'
SUMMARY_SCHEMA = {
    c: pl.String
    if c in [*ita_summary.TEXT_COLUMNS, 'naics_code', 'source_file']
    else (pl.Boolean if c.startswith('flag_') or c == 'naics_year_from_dictionary' else pl.Int64)
    for c in ita_summary.COLUMNS
}


def check_source(data_dir: Path, work: Path) -> tuple[pl.LazyFrame, list[dict]]:
    '''Verify the exact Stage 2 schema, selected raw inventory and full-row multiplicity.'''
    table = paths.derived_dir(data_dir, 'osha') / ita_summary.TABLE_NAME
    lf = pl.scan_parquet(table)
    if lf.collect_schema() != SUMMARY_SCHEMA:
        raise ValueError('incompatible Stage 2 summary schema')
    selected = ita_summary.summary_files(data_dir)
    if sorted(selected) != list(range(min(selected), max(selected) + 1)):
        raise ValueError('incomplete source year inventory')
    citations = []
    observed = set(lf.select('year_filing_for', 'source_file').unique().collect().iter_rows())
    expected_inventory = set()
    for year, file in selected.items():
        entry = manifest.entry_for(paths.manifest_path(data_dir), file)
        citations.append(asdict(entry))
        expected_inventory.add((year, entry.path))
        raw = ita_summary.harmonize_file(file, year, entry.path, work / f'{year}.csv')
        expected = (
            ita_summary.add_flags(raw)
            .select(ita_summary.COLUMNS)
            .group_by(ita_summary.COLUMNS)
            .agg(_n=pl.len().cast(pl.Int64))
        )
        actual = (
            lf.filter(pl.col('year_filing_for').eq(year))
            .group_by(ita_summary.COLUMNS)
            .agg(_n=pl.len().cast(pl.Int64))
        )
        mismatches = (
            actual.join(
                expected,
                on=ita_summary.COLUMNS,
                how='full',
                nulls_equal=True,
                coalesce=True,
                suffix='_raw',
            )
            .filter(pl.col('_n').ne_missing(pl.col('_n_raw')))
            .select(pl.len())
            .collect()
            .item()
        )
        if mismatches:
            raise ValueError('stale Stage 2 summary: raw/full-row multiset mismatch')
    if observed != expected_inventory or not observed:
        raise ValueError('stale Stage 2 summary: selected source inventory differs')
    return lf, citations


def report(table: Path) -> dict:
    '''Count every canonical row in deterministic mapping and filing partitions.'''
    lf = pl.scan_parquet(table)
    total = lf.select(pl.len().cast(pl.Int64)).collect().item()

    def counts(columns):
        return (
            lf.group_by(columns)
            .agg(n=pl.len().cast(pl.Int64))
            .sort(columns, nulls_last=False)
            .collect()
            .to_dicts()
        )

    mapping = counts(['year_filing_for', 'naics_mapping_status'])
    filing = counts(
        [
            'year_filing_for',
            'filing_industry_status',
            'flag_outside_filing_industry',
            'flag_outside_filing_rule',
            'flag_filing_rule_label_bridged',
            'flag_filing_reference_ambiguous',
        ]
    )
    distribution = (
        lf.with_columns(candidate_count=pl.col('naics_2022_candidates').list.len())
        .group_by('year_filing_for', 'candidate_count')
        .agg(n=pl.len().cast(pl.Int64))
        .sort('year_filing_for', 'candidate_count')
        .collect()
        .to_dicts()
    )
    flags = (
        lf.group_by('year_filing_for')
        .agg(
            *[
                pl.col(c).sum().cast(pl.Int64).alias(c)
                for c in MAPPING_SCHEMA
                if c.startswith('flag_')
            ]
        )
        .sort('year_filing_for')
        .collect()
        .to_dicts()
    )
    if not total or sum(r['n'] for r in mapping) != total or sum(r['n'] for r in filing) != total:
        raise ValueError('report partitions do not account for every input row')
    return {
        'schema_version': SCHEMA_VERSION,
        'input_rows': total,
        'mapping': mapping,
        'filing': filing,
        'candidate_counts': distribution,
        'mapping_flags': flags,
        'filing_period_basis': (
            'nominal filing cycle: filing year plus one; actual submission dates unavailable'
        ),
    }


def write_json(file, payload):
    file.write_text(json.dumps(payload, sort_keys=True, indent=2) + '\n', encoding='utf-8')


def validate_canonical(table, expected_schema):
    lf = pl.scan_parquet(table)
    if lf.collect_schema() != expected_schema:
        raise ValueError('published canonical schema differs')
    nonnull = [
        'naics_mapping_status',
        'naics_matching_vintages',
        'naics_2022_candidates',
        'flag_naics_crosswalked',
        'flag_naics_ambiguous',
        'flag_naics_unresolved',
        'filing_industry_status',
        'flag_filing_rule_label_bridged',
        'flag_filing_reference_ambiguous',
    ]
    if lf.select(pl.any_horizontal([pl.col(c).is_null() for c in nonnull]).any()).collect().item():
        raise ValueError('null mapping contract field')
    states = [
        'missing_code',
        'native_2022',
        'concorded',
        'invalid_native_code',
        'unknown_vintage_candidates',
        'unknown_vintage_unmapped',
    ]
    length = pl.col('naics_2022_candidates').list.len()
    invalid_mapping = (
        pl.col('naics_mapping_status')
        .is_in(states)
        .not_()
        .or_(pl.col('flag_naics_ambiguous').ne(length.gt(1)))
        .or_(
            pl.col('naics_year')
            .is_null()
            .and_(
                pl.any_horizontal(
                    pl.col('naics_2022_code').is_not_null(),
                    pl.col('naics_2022_node_id').is_not_null(),
                )
            )
        )
        .or_(
            pl.col('naics_mapping_status')
            .is_in(['missing_code', 'invalid_native_code', 'unknown_vintage_unmapped'])
            .and_(length.ne(0))
        )
    )
    if lf.filter(invalid_mapping).select(pl.len()).collect().item():
        raise ValueError('invalid published mapping state or scalar assertion')


def build(data_dir: Path, run_id: str, *, registry=cr.REGISTRY) -> Path:
    '''Publish a verified bundle; leave failed staging intact for investigation.'''
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', run_id):
        raise ValueError('run ID must contain only ASCII letters, digits, underscore or hyphen')
    root = paths.derived_dir(data_dir, 'codes')
    final, staging = root / run_id, root / (run_id + '.part')
    if final.exists() or staging.exists() or final.is_symlink() or staging.is_symlink():
        raise ValueError('run or staging name already exists')
    refs = cr.read_references(data_dir, registry=registry)
    source = paths.derived_dir(data_dir, 'osha') / ita_summary.TABLE_NAME
    source_hash = manifest.sha256_file(source)
    manifest_hash = manifest.sha256_file(paths.manifest_path(data_dir))
    root.mkdir(parents=True, exist_ok=True)
    staging.mkdir()
    with tempfile.TemporaryDirectory(dir=staging) as work:
        lf, raw_citations = check_source(data_dir, Path(work))
    native = refs['structures']
    naics_nodes, naics_edges, naics_paths = naics_tables(
        native.select('vintage', 'code', 'title'),
        2022,
    )
    soc_original = cr.reference_path(data_dir, registry['soc_2018'])
    manifest.entry_for(paths.manifest_path(data_dir), soc_original)
    soc_nodes, soc_edges, soc_paths = soc_tables(
        pl.read_excel(
            soc_original,
            has_header=False,
            read_options={'dtypes': 'string'},
        )
    )
    lookup = build_lookup(
        lf.select(*KEY_SCHEMA).unique().collect(), native, refs['relations'], naics_paths
    )
    filing_lookup = build_filing_lookup(
        lf.select(*FILING_KEYS).unique().collect(),
        native,
        refs['relations'],
        refs['rule_membership'],
    )
    canonical = add_filing_flags(enrich(lf, lookup), filing_lookup)
    expected_schema = {**SUMMARY_SCHEMA, **MAPPING_SCHEMA, **FILING_COLUMNS}
    if canonical.collect_schema() != expected_schema:
        raise ValueError('incompatible canonical output schema')
    tables = {
        'naics_nodes': naics_nodes,
        'naics_edges': naics_edges,
        'soc_nodes': soc_nodes,
        'soc_edges': soc_edges,
        'naics_native_nodes': native,
        'naics_concordance': refs['relations'],
        'filing_rules': refs['rules'],
        'code_paths': pl.concat([naics_paths, soc_paths]).sort('node_id'),
        'filing_rule_labels': refs['rule_labels'],
        'filing_rule_membership': refs['rule_membership'],
        'ita_naics_lookup': lookup,
    }
    for name, frame in tables.items():
        frame.write_parquet(staging / (name + '.parquet'))
    canonical.sink_parquet(staging / 'ita_300a_canonical.parquet')
    validate_canonical(staging / 'ita_300a_canonical.parquet', expected_schema)
    diagnostics = report(staging / 'ita_300a_canonical.parquet')
    if diagnostics['input_rows'] != lf.select(pl.len()).collect().item():
        raise ValueError('canonical row count changed')
    diagnostics['tables'] = {}
    for file in sorted(staging.glob('*.parquet')):
        frame = pl.scan_parquet(file)
        diagnostics['tables'][file.name] = {
            'rows': frame.select(pl.len()).collect().item(),
            'schema': {name: str(dtype) for name, dtype in frame.collect_schema().items()},
        }
    reference_counts = (
        refs['rule_membership']
        .group_by('rule_id')
        .agg(
            rule_native_codes=pl.len().cast(pl.Int64),
            definite_members=pl.col('membership_candidates')
            .list.len()
            .eq(1)
            .and_(pl.col('membership_candidates').list.contains(True))
            .sum()
            .cast(pl.Int64),
            mixed_memberships=pl.col('membership_candidates')
            .list.len()
            .eq(2)
            .sum()
            .cast(pl.Int64),
            label_bridge_codes=pl.col('flag_rule_label_bridged').sum().cast(pl.Int64),
        )
    )
    label_counts = (
        refs['rule_labels']
        .group_by('rule_id')
        .agg(
            listed_groups=pl.len().cast(pl.Int64),
            legacy_labels=pl.col('flag_rule_label_legacy').sum().cast(pl.Int64),
        )
    )
    diagnostics['rule_counts'] = (
        label_counts.join(reference_counts, on='rule_id', validate='1:1')
        .sort('rule_id')
        .to_dicts()
    )
    citations = raw_citations + [
        asdict(
            manifest.entry_for(
                paths.manifest_path(data_dir), cr.reference_path(data_dir, reference)
            )
        )
        for reference in registry.values()
    ]
    code_files = sorted(
        {
            Path(__file__),
            *[
                Path(module.__file__)
                for module in [
                    cr,
                    ita_summary,
                    manifest,
                    paths,
                    __import__('embedding_data.classification_tables', fromlist=['forest']),
                    __import__('embedding_data.naics_relationships', fromlist=['candidates']),
                    __import__('embedding_data.filing_rules', fromlist=['evaluate']),
                    __import__('embedding_data.ita_naics_mapping', fromlist=['enrich']),
                    __import__('embedding_data.ita_references', fromlist=['parse_titles']),
                    __import__('embedding_data.ita_catalog', fromlist=['through_date']),
                    __import__('embedding_data.osha_encoding', fromlist=['decode_line']),
                ]
            ],
        }
    )
    inventory = {
        'schema_version': SCHEMA_VERSION,
        'run_id': run_id,
        'source_parquet': {
            'path': source.relative_to(data_dir).as_posix(),
            'sha256': source_hash,
            'size': source.stat().st_size,
        },
        'raw': sorted(citations, key=lambda r: r['path']),
        'references': {kind: asdict(reference) for kind, reference in sorted(registry.items())},
        'implementation': {
            file.relative_to(paths.PROJECT_ROOT).as_posix(): manifest.sha256_file(file)
            for file in code_files
        },
        'dependencies': {
            name: version(name)
            for name in ['embedding-data', 'polars', 'fastexcel', 'httpx', 'typer']
        },
        'python': sys.version,
        'uv_lock_sha256': manifest.sha256_file(paths.PROJECT_ROOT / 'uv.lock'),
    }
    write_json(staging / 'inputs.json', inventory)
    write_json(staging / 'report.json', diagnostics)
    # Detached checksum inventory avoids a self-referential hash in report.json/inputs.json.
    write_json(
        staging / 'outputs.json',
        {
            file.name: {'sha256': manifest.sha256_file(file), 'size': file.stat().st_size}
            for file in sorted(staging.iterdir())
            if file.is_file()
        },
    )
    if (
        manifest.sha256_file(source) != source_hash
        or manifest.sha256_file(paths.manifest_path(data_dir)) != manifest_hash
    ):
        raise ValueError('source table or raw manifest changed during build')
    for citation in citations:
        manifest.entry_for(
            paths.manifest_path(data_dir), paths.manifest_path(data_dir).parent / citation['path']
        )
    if final.exists() or final.is_symlink():
        raise ValueError('run destination appeared during build')
    staging.rename(final)
    return final
