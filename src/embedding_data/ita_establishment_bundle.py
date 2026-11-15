'''Publish, verify and compare immutable Stage 10 ITA establishment-target bundles.

A bundle holds the eight tables of one build, `inputs.json` (selection and provenance),
`report.json` (accounting, reproductions and limits) and the detached inventory
`outputs.json`. `build` stages into `<RUN_ID>.part`, keeps its scratch inside that
directory, rechecks its pinned inputs and its software just before publication and only
then renames the staging directory. A failure removes only that staging directory.

`verify_bundle` authenticates the detached pin, the file set and the inventory before it
reads anything else, then recomputes every table offline in a temporary directory outside
the data root. `compare_runs` checks two published bundles for exact logical replay. It
does not establish trust.
'''

import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import distributions
from pathlib import Path

import polars as pl

from embedding_data import (
    geography_references,
    ita_co_ownership,
    ita_establishment_expected,
    ita_establishment_inputs,
    ita_establishment_links,
    ita_establishment_records,
    ita_index_references,
    ita_references,
    ita_text_pairs,
    manifest,
    paths,
    target_contract,
    target_io,
)
from embedding_data.ita_establishment_expected import ADOPTED_BASIS, Expectations
from embedding_data.ita_index_references import IndexReference

TABLES = (
    'ita_establishment_links',
    'ita_text_pairs',
    'ita_text_pair_codes',
    'ita_text_pair_members',
    'naics_2022_paths',
    'ita_co_ownership',
    'co_ownership_marginals',
    'co_ownership_support',
)
FILES = (*(name + '.parquet' for name in TABLES), 'inputs.json', 'report.json')
CONTRACTS = {
    'links': 'ita-establishment-links-v1',
    'pairs': 'ita-text-pairs-v1',
    'co_ownership': 'ita-co-ownership-v1',
    'index': 'naics-index-v1',
    'targets': 'targets-v1',
}
SOFTWARE_ROOT = paths.PROJECT_ROOT
SOFTWARE_FILES = (
    'src/embedding_data/__init__.py',
    'src/embedding_data/classification_tables.py',
    'src/embedding_data/code_build.py',
    'src/embedding_data/code_references.py',
    'src/embedding_data/filing_rules.py',
    'src/embedding_data/geography_build.py',
    'src/embedding_data/geography_hud.py',
    'src/embedding_data/geography_parsers.py',
    'src/embedding_data/geography_references.py',
    'src/embedding_data/geography_tables.py',
    'src/embedding_data/ita_area_mix.py',
    'src/embedding_data/ita_catalog.py',
    'src/embedding_data/ita_co_ownership.py',
    'src/embedding_data/ita_establishment_bundle.py',
    'src/embedding_data/ita_establishment_expected.py',
    'src/embedding_data/ita_establishment_inputs.py',
    'src/embedding_data/ita_establishment_links.py',
    'src/embedding_data/ita_establishment_records.py',
    'src/embedding_data/ita_index_references.py',
    'src/embedding_data/ita_naics_mapping.py',
    'src/embedding_data/ita_references.py',
    'src/embedding_data/ita_summary.py',
    'src/embedding_data/ita_text_pairs.py',
    'src/embedding_data/ita_verification.py',
    'src/embedding_data/manifest.py',
    'src/embedding_data/naics_relationships.py',
    'src/embedding_data/osha_benchmark_download.py',
    'src/embedding_data/osha_encoding.py',
    'src/embedding_data/paths.py',
    'src/embedding_data/target_contract.py',
    'src/embedding_data/target_inputs.py',
    'src/embedding_data/target_io.py',
    'pyproject.toml',
    'uv.lock',
)
RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')
PIN = re.compile(r'[0-9a-f]{64}')
INPUT_FIELDS = frozenset({
    'run_id', 'contracts', 'codes', 'source_parquet', 'canonical', 'raw', 'index_references',
    'expectations', 'rules', 'software', 'execution',
})
RULES = {
    'headline': (
        'a headline pair has a known employer, a description that is neither empty nor a '
        'placeholder, and an eligible native NAICS 2022 record in 2023-2025; its headline '
        'codes come from those records only'
    ),
    'co_ownership': (
        'J(a,b)/n(a) over usable unpadded EINs; J needs both industries in one 2023-2025 '
        'filing year; records are deduplicated to EIN, year and industry'
    ),
    'links': (
        'one status per distinct base record and year pair, in precedence order; same-ID '
        'confirmation needs equal known unpadded EINs and equal complete addresses; changed-ID '
        'confirmation needs equal unique EIN, name and address tuples; a shared or double '
        'successor is a conflict'
    ),
}
LIMITS = (
    'ITA is a program-selected filing population. No product here represents all '
    'establishments or firms.',
    'Codes are self-reported and unvalidated. A pair is a noisy label.',
    'Copied-text flags catch exact normalized identity only. Near-copies and reworded index '
    'entries stay unflagged.',
    'Restricting to native 2022 codes drops about 40% of 2024–2025 records. '
    "Some employers' industry sets are partial, so co-ownership can be undercounted. "
    'The marginals table measures this per industry.',
    'An EIN is a tax-filing entity. One firm can hold several EINs, so co-ownership within '
    'EIN can miss relationships across a firm.',
    'Which establishments file is shaped by the filing rule. Co-ownership can over-represent '
    'designated industries (methodology K6, assumption 6).',
    'Linkage uses exact address equality. Relocations and address reformatting break '
    'confirmation. Probabilistic linkage stays out of scope.',
    'The marginal n(a) pools presence over three years. An employer that left industry a in '
    '2024 still counts in n(a). J(a,b) requires both industries in the same year.',
)


@dataclass(frozen=True)
class _Products:
    '''The tables, report and validation inputs of one computation.'''

    records: pl.LazyFrame
    nodes: pl.DataFrame
    code_paths: pl.DataFrame
    pairs: ita_text_pairs.TextPairs
    co_ownership: ita_co_ownership.CoOwnership
    tables: dict[str, pl.LazyFrame]
    report: dict


def run_directory(data_dir: Path, run_id: str) -> Path:
    '''The published directory of one run: `derived/osha/establishment-targets/<run_id>`.'''
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError('unsafe run ID')
    return paths.derived_dir(Path(data_dir), 'osha') / 'establishment-targets' / run_id


def freeze_software() -> dict:
    '''The executing files, Python identity, installed distributions and `uv.lock` hash.'''
    return {
        'files': {name: target_io.file_record(SOFTWARE_ROOT / name) for name in SOFTWARE_FILES},
        'python': platform.python_version(),
        'python_full': sys.version,
        'implementation': platform.python_implementation(),
        'dependencies': dict(sorted((dist.metadata['Name'], dist.version)
                                    for dist in distributions())),
        'uv_lock_sha256': manifest.sha256_file(SOFTWARE_ROOT / 'uv.lock'),
    }


def ordered_equal(first: pl.LazyFrame, second: pl.LazyFrame) -> dict:
    '''Compare ordered schemas, row counts and every value in physical row order.

    Rows are joined on their position, and `ne_missing` counts a null against a value as a
    difference. Frames with different schemas or row counts never have equal values.
    '''
    schema = list(first.collect_schema().items())
    schema_equal = schema == list(second.collect_schema().items())
    first_rows = first.select(pl.len()).collect().item()
    second_rows = second.select(pl.len()).collect().item()
    values_equal = False
    if schema_equal and first_rows == second_rows:
        joined = first.with_row_index('_position').join(
            second.with_row_index('_position'), on='_position', how='full', coalesce=True,
            suffix='_second', validate='1:1')
        different = pl.any_horizontal(
            [pl.col(name).ne_missing(pl.col(name + '_second')) for name, _ in schema])
        values_equal = not joined.select(different.any()).collect().item()
    return {
        'schema_equal': schema_equal,
        'values_equal': values_equal,
        'first_rows': first_rows,
        'second_rows': second_rows,
    }


def _same(comparison: dict) -> bool:
    return (comparison['schema_equal'] and comparison['values_equal']
            and comparison['first_rows'] == comparison['second_rows'])


def _execution() -> dict:
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=paths.PROJECT_ROOT, text=True).strip()
    return {'commit': git('rev-parse', 'HEAD'),
            'dirty': bool(git('status', '--porcelain', '--untracked-files=normal')),
            'created_at': datetime.now(UTC).isoformat()}


def _normalized(value: object) -> object:
    '''The value as JSON reads it back: tuples become lists and keys become strings.'''
    return json.loads(json.dumps(value, allow_nan=False))


def _unique_object(pairs: list) -> dict:
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError('duplicate JSON key')
    return dict(pairs)


def _reject_constant(name: str) -> None:
    raise ValueError('non-finite JSON number')


def _read_json(file: Path) -> dict:
    '''A bundle JSON object, read strictly and required to be in canonical form.'''
    if not file.is_file():
        raise ValueError(f'{file.name}: bundle JSON file is missing')
    text = file.read_text(encoding='utf-8')
    try:
        value = json.loads(text, object_pairs_hook=_unique_object,
                           parse_constant=_reject_constant)
    except json.JSONDecodeError:
        raise ValueError(f'{file.name}: not valid JSON') from None
    if not isinstance(value, dict):
        raise ValueError(f'{file.name}: not a JSON object')
    canonical = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                           allow_nan=False) + '\n'
    if text != canonical:
        raise ValueError(f'{file.name}: not canonical JSON')
    return value


def _adopted(source: dict) -> bool:
    '''Whether the selected Stage 2 summary is the adopted one, as `expectations_for` judges.'''
    adopted = ita_establishment_expected.ADOPTED_SOURCE
    return source.get('sha256') == adopted['sha256'] and source.get('size') == adopted['size']


def _expectations(source: dict, explicit: Expectations | None,
                  registry: dict[str, IndexReference]) -> Expectations:
    expected = ita_establishment_expected.expectations_for(source, explicit)
    if _adopted(source) and registry != ita_index_references.REGISTRY:
        raise ValueError('adopted source requires the production index registry')
    return expected


def _references(data_dir: Path, registry: dict[str, IndexReference]) -> tuple:
    '''The official titles and the registered index rows, each read from verified bytes.'''
    try:
        titles = ita_references.read_titles(data_dir)
        index = ita_index_references.read_index(data_dir, titles, registry=registry)
    except KeyError:
        raise ValueError('a reference original is not recorded or not registered') from None
    return titles, index


def _title_citations(data_dir: Path) -> list[dict]:
    manifest_path = paths.manifest_path(data_dir)
    return [
        _normalized(asdict(manifest.entry_for(manifest_path, ita_references.reference_path(
            data_dir, 'naics/' + url.rsplit('/', 1)[1]))))
        for url in ita_references.TITLE_FILES.values()
    ]


def _inputs(data_dir: Path, run_id: str, selected, registry: dict[str, IndexReference],
            expected: Expectations, software: dict, execution: dict) -> dict:
    '''The provenance record of one build, in the form JSON reads it back.'''
    provenance = selected.provenance
    try:
        raw = ita_establishment_inputs.merge_citations(
            provenance['raw'],
            _title_citations(data_dir),
            _normalized(ita_index_references.citations(data_dir, registry=registry)),
        )
    except KeyError:
        raise ValueError('a cited raw file is not recorded') from None
    return _normalized({
        'run_id': run_id,
        'contracts': CONTRACTS,
        'codes': provenance['codes'],
        'source_parquet': provenance['source_parquet'],
        'canonical': provenance['canonical'],
        'raw': raw,
        'index_references': {kind: asdict(reference) for kind, reference in registry.items()},
        'expectations': expected.to_json(),
        'rules': RULES,
        'software': software,
        'execution': execution,
    })


def _summary(frame: pl.LazyFrame) -> dict:
    schema = frame.collect_schema()
    return {'rows': frame.select(pl.len()).collect().item(), 'columns': list(schema),
            'schema': {column: str(dtype) for column, dtype in schema.items()}}


def _products(selected, titles: pl.DataFrame, index: pl.DataFrame, expected: Expectations,
              scratch: Path) -> _Products:
    '''Compute and validate every table and the report from the selected inputs.

    The keyed records are written once to `scratch/records.parquet`. Every builder and
    validator reads that file, so the keying functions run only once.
    '''
    keys = ita_establishment_records.text_keys(titles, index)
    canonical = pl.scan_parquet(selected.tables['ita_300a_canonical'])
    records_file = scratch / 'records.parquet'
    ita_establishment_records.keyed_records(canonical, keys).sink_parquet(records_file)
    records = pl.scan_parquet(records_file)
    nodes = pl.read_parquet(selected.tables['naics_nodes'])
    code_paths = pl.read_parquet(selected.tables['code_paths'])
    pairs = ita_text_pairs.build_pairs(records, nodes, code_paths)
    ita_text_pairs.validate_pairs(pairs, records, code_paths)
    links = ita_establishment_links.build_links(records)
    ita_establishment_links.validate_links(links.links, records)
    co_ownership = ita_co_ownership.estimate(records)
    ita_co_ownership.validate_co_ownership(co_ownership, nodes)
    v1 = ita_establishment_records.v1_counts(records)
    reproduction = ita_establishment_expected.check_reproduction(
        expected, source_records=records.select(pl.len()).collect().item(), v1=v1,
        v2=links.v2)
    tables = {
        'ita_establishment_links': links.links,
        'ita_text_pairs': pairs.pairs,
        'ita_text_pair_codes': pairs.pair_codes,
        'ita_text_pair_members': pairs.members,
        'naics_2022_paths': pairs.paths,
        'ita_co_ownership': co_ownership.targets,
        'co_ownership_marginals': co_ownership.marginals,
        'co_ownership_support': co_ownership.support,
    }
    report = _normalized({
        'contracts': CONTRACTS,
        'reproduction': reproduction,
        'v1_by_year': v1.to_dicts(),
        'index_by_year': ita_establishment_records.index_counts(records).to_dicts(),
        'pairs': pairs.report,
        'links': links.report,
        'co_ownership': co_ownership.report,
        'tables': {name: _summary(tables[name]) for name in TABLES},
        'limits': list(LIMITS),
        'universe': ita_co_ownership.UNIVERSE,
        'size_gate': 'pending',
    })
    return _Products(records, nodes, code_paths, pairs, co_ownership, tables, report)


def _write_tables(staging: Path, products: _Products) -> None:
    '''Write each table, then validate the serialized frames and compare them in order.'''
    for name in TABLES:
        file = staging / (name + '.parquet')
        if name == 'ita_co_ownership':
            target_contract.write_targets(products.tables[name], file)
        else:
            products.tables[name].sink_parquet(file)
    serialized = {name: pl.scan_parquet(staging / (name + '.parquet')) for name in TABLES}
    ita_text_pairs.validate_pairs(
        ita_text_pairs.TextPairs(
            serialized['ita_text_pairs'], serialized['ita_text_pair_codes'],
            serialized['ita_text_pair_members'], serialized['naics_2022_paths'],
            products.pairs.report),
        products.records, products.code_paths)
    ita_establishment_links.validate_links(serialized['ita_establishment_links'],
                                           products.records)
    ita_co_ownership.validate_co_ownership(
        ita_co_ownership.CoOwnership(
            serialized['ita_co_ownership'], serialized['co_ownership_marginals'],
            serialized['co_ownership_support'], products.co_ownership.report),
        products.nodes)
    for name in TABLES:
        if not _same(ordered_equal(serialized[name], products.tables[name])):
            raise ValueError(f'{name}: serialized table differs from the in-memory result')


def _recheck(data_dir: Path, selected, software: dict, inputs: dict,
             registry: dict[str, IndexReference]) -> None:
    '''Refuse any change of the pinned inputs or the software since the build began.'''
    selected.verify()
    if freeze_software() != software:
        raise ValueError('executing software changed before publication')
    try:
        target_io.verify_raw(data_dir, inputs['raw'])
    except KeyError:
        raise ValueError('a cited raw file is not recorded') from None
    for reference in registry.values():
        ita_index_references.check_pin(
            ita_index_references.reference_path(data_dir, reference), reference)


def build(
    data_dir: Path,
    run_id: str,
    *,
    codes_run: str,
    codes_outputs_sha256: str,
    index_registry: dict = ita_index_references.REGISTRY,
    expectations: Expectations | None = None,
) -> dict:
    '''Build, check and publish one immutable bundle under `run_directory(data_dir, run_id)`.

    An existing final or `.part` name fails before anything is written. The adopted Stage 2
    summary takes the adopted V1/V2 expectations and the production index registry only.
    Any other summary needs explicit expectations whose basis is not the adopted one.
    '''
    data_dir = Path(data_dir)
    final, staging = target_io.stage(run_directory(data_dir, run_id).parent, run_id, data_dir)
    try:
        scratch = staging / '.scratch'
        scratch.mkdir()
        software = freeze_software()
        selected = ita_establishment_inputs.select_codes(
            data_dir, codes_run, codes_outputs_sha256=codes_outputs_sha256)
        titles, index = _references(data_dir, index_registry)
        expected = _expectations(selected.provenance['source_parquet'], expectations,
                                 index_registry)
        products = _products(selected, titles, index, expected, scratch)
        _write_tables(staging, products)
        geography_references.safe_path(scratch, data_dir)
        shutil.rmtree(scratch)
        inputs = _inputs(data_dir, run_id, selected, index_registry, expected, software,
                         _execution())
        target_io.write_json(staging / 'inputs.json', inputs)
        target_io.write_json(staging / 'report.json', products.report)
        _recheck(data_dir, selected, software, inputs, index_registry)
        target_io.write_json(staging / 'outputs.json',
                             target_io.inventory(staging, list(FILES)))
        if {path.name for path in staging.iterdir()} != {*FILES, 'outputs.json'}:
            raise ValueError('staged bundle files differ from the bundle file set')
        geography_references.safe_path(final, data_dir)
        if geography_references.occupied(final):
            raise ValueError('final run name already exists')
        pin = manifest.sha256_file(staging / 'outputs.json')
        staging.rename(final)
        return {'run_id': run_id, 'directory': str(final), 'outputs_sha256': pin}
    finally:
        if staging.exists():
            geography_references.safe_path(staging, data_dir)
            shutil.rmtree(staging)


def _recorded(inputs: dict) -> tuple:
    '''The recorded codes selection, index registry and expectations of `inputs.json`.'''
    if set(inputs) != INPUT_FIELDS:
        raise ValueError('recorded inputs are malformed')
    try:
        codes = inputs['codes']
        registry = {
            kind: IndexReference(**{**value, 'header': tuple(value['header'])})
            for kind, value in inputs['index_references'].items()
        }
        expectations = Expectations.from_json(inputs['expectations'])
        return codes['run_id'], codes['outputs_sha256'], registry, expectations
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ValueError('recorded inputs are malformed') from None


def verify_bundle(directory: Path, data_dir: Path, *, expected_outputs_sha256: str) -> dict:
    '''Authenticate a published bundle by its detached pin, then recompute it offline.

    The pin, the exact file set and the inventory are checked before any recomputation.
    Recorded software must equal the executing software. Every table is recomputed in a
    temporary directory outside `data_dir` and compared in physical order, then the report
    and the inputs (with their recorded execution) must equal the recomputed ones.
    '''
    directory, data_dir = Path(directory), Path(data_dir)
    if directory.name.endswith('.part'):
        raise ValueError('an interrupted bundle is not published')
    if not isinstance(expected_outputs_sha256, str) or not PIN.fullmatch(
            expected_outputs_sha256):
        raise ValueError('invalid detached checksum')
    outputs_file = target_io.relative_file(directory, 'outputs.json')
    if not outputs_file.is_file() or manifest.sha256_file(outputs_file) != expected_outputs_sha256:
        raise ValueError('detached inventory checksum differs')
    if {path.name for path in directory.iterdir()} != {*FILES, 'outputs.json'}:
        raise ValueError('bundle file set differs')
    outputs = _read_json(outputs_file)
    target_io.verify_inventory(directory, outputs, set(FILES))
    if outputs != target_io.inventory(directory, list(FILES)):
        raise ValueError('output inventory records differ')

    inputs = _read_json(directory / 'inputs.json')
    report = _read_json(directory / 'report.json')
    codes_run, codes_pin, registry, recorded = _recorded(inputs)
    if inputs['run_id'] != directory.name:
        raise ValueError('recorded run ID differs from the directory')
    if inputs['contracts'] != CONTRACTS or report.get('contracts') != CONTRACTS:
        raise ValueError('contract versions differ')
    selected = ita_establishment_inputs.select_codes(
        data_dir, codes_run, codes_outputs_sha256=codes_pin)
    source = selected.provenance['source_parquet']
    adopted = _adopted(source)
    if adopted:
        if recorded != ita_establishment_expected.ADOPTED:
            raise ValueError('an adopted bundle must record the adopted expectations')
        if registry != ita_index_references.REGISTRY:
            raise ValueError('an adopted bundle must record the production index registry')
    elif recorded.basis == ADOPTED_BASIS:
        raise ValueError('a bundle of another source must not claim the adopted basis')

    software = freeze_software()
    if inputs['software'] != software:
        raise ValueError('executing software differs from the build')

    titles, index = _references(data_dir, registry)
    expected = _expectations(source, None if adopted else recorded, registry)
    with tempfile.TemporaryDirectory() as temporary:
        products = _products(selected, titles, index, expected, Path(temporary))
        for name in TABLES:
            published = pl.scan_parquet(directory / (name + '.parquet'))
            if not _same(ordered_equal(published, products.tables[name])):
                raise ValueError(f'{name}: published table differs from the recomputation')
    if products.report != report:
        raise ValueError('published report differs from the recomputation')
    if _inputs(data_dir, directory.name, selected, registry, expected, software,
               inputs['execution']) != inputs:
        raise ValueError('recorded inputs differ from the recomputation')
    return {
        'run_id': directory.name,
        'outputs_sha256': expected_outputs_sha256,
        'reproduction': report['reproduction'],
        'rows': {name: report['tables'][name]['rows'] for name in TABLES},
    }


def compare_runs(first: Path, second: Path) -> dict:
    '''Compare two published bundles table by table, in order, and their reports exactly.

    Each bundle must match its own `outputs.json` inventory. Equality establishes replay,
    not trust: neither bundle is authenticated by a detached pin here.
    '''
    first, second = Path(first), Path(second)
    for directory in (first, second):
        if directory.name.endswith('.part') or not directory.is_dir():
            raise ValueError('compared bundles must be published')
        target_io.verify_inventory(directory, _read_json(directory / 'outputs.json'),
                                   set(FILES))
    tables = {
        name: ordered_equal(pl.scan_parquet(first / (name + '.parquet')),
                            pl.scan_parquet(second / (name + '.parquet')))
        for name in TABLES
    }
    report_equal = _read_json(first / 'report.json') == _read_json(second / 'report.json')
    return {
        'equal': report_equal and all(_same(comparison) for comparison in tables.values()),
        'tables': tables,
        'report_equal': report_equal,
        'trust_established': False,
    }
