'''Publish, verify and compare immutable Stage 5 TRI parent-link bundles.

A bundle holds five tables, `inputs.json` (selection and provenance), `report.json`
(accounting, distributions and limits) and the detached inventory `outputs.json`. `build`
stages into `<RUN_ID>.part` and keeps its scratch, which holds transcoded copies of the raw
files and so D&B numbers, in `<RUN_ID>.part/.scratch`. It removes the scratch before it
writes the JSON files, rechecks its pinned inputs and its software just before publication
and only then renames the staging directory. A failure removes only that staging directory.

`verify_bundle` authenticates the detached pin, the file set and the inventory before it
reads anything else, then recomputes every table offline in a temporary directory outside
the data root. `compare_runs` checks two published bundles for exact logical replay. It
does not establish trust. Every failure raises `ValueError` with a fixed message that holds
no row content.
'''

import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from importlib.metadata import distributions
from pathlib import Path

import polars as pl

from embedding_data import (
    geography_references,
    manifest,
    paths,
    target_contract,
    target_io,
    tri_codes,
    tri_facility_years,
    tri_layout,
    tri_parent_industries,
    tri_parent_link_targets,
    tri_raw,
    tri_reader,
)
from embedding_data.tri_layout import HeaderLayout

TABLES = ('tri_parent_links', 'tri_parent_link_marginals', 'tri_parent_link_support',
          'tri_parent_industries', 'tri_facility_years')
FILES = (*(name + '.parquet' for name in TABLES), 'inputs.json', 'report.json')
CONTRACTS = {
    'facility_years': 'tri-facility-years-v1',
    'parent_links': 'tri-parent-links-v1',
    'targets': 'targets-v1',
    'headers': 'tri-headers-v1',
}
SOFTWARE_ROOT = paths.PROJECT_ROOT
SOFTWARE_FILES = (
    'pyproject.toml',
    'src/embedding_data/__init__.py',
    'src/embedding_data/geography_parsers.py',
    'src/embedding_data/geography_references.py',
    'src/embedding_data/ita_catalog.py',
    'src/embedding_data/ita_references.py',
    'src/embedding_data/ita_summary.py',
    'src/embedding_data/manifest.py',
    'src/embedding_data/osha_benchmark_download.py',
    'src/embedding_data/osha_encoding.py',
    'src/embedding_data/paths.py',
    'src/embedding_data/target_contract.py',
    'src/embedding_data/target_io.py',
    'src/embedding_data/tri_bundle.py',
    'src/embedding_data/tri_codes.py',
    'src/embedding_data/tri_facility_years.py',
    'src/embedding_data/tri_layout.py',
    'src/embedding_data/tri_layouts.json',
    'src/embedding_data/tri_parent_industries.py',
    'src/embedding_data/tri_parent_link_targets.py',
    'src/embedding_data/tri_parent_links.py',
    'src/embedding_data/tri_raw.py',
    'src/embedding_data/tri_reader.py',
    'uv.lock',
)
RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')
PIN = re.compile(r'[0-9a-f]{64}')
INPUT_FIELDS = frozenset({
    'run_id', 'contracts', 'codes', 'raw', 'processed_as_of', 'window', 'layouts', 'rules',
    'software', 'execution',
})
RULES = {
    'facility_year': (
        'Rows are grouped by reporting year and TRIFD, and Form R and Form A rows both count.'
    ),
    'eligibility': (
        'An eligible facility-year has exactly one primary NAICS value, that value is a NAICS '
        '2022 national-industry code in the selected Stage 4 nodes, it has at most one '
        'standardized parent name, and it is not federal.'
    ),
    'owner': (
        'The headline owner key is `parent:<standardized name>` when the facility-year names a '
        'parent, else `facility:<TRIFD>`, and keys are compared as exact strings.'
    ),
    'measure': (
        'For each ordered pair `(a,b)` with `J(a,b) > 0` and `a ≠ b`, one target row has '
        '`value = J(a,b) / n(a)`, where `n(a)` is the number of owners with `a` in some year '
        'and `J(a,b)` the number of owners with both `a` and `b` in the same year.'
    ),
}
LIMITS = (
    'TRI is a program-selected population, mostly industrial. No product here represents all '
    'establishments or firms.',
    'A facility can contain several establishments. One primary code per facility hides the '
    'others. Secondary codes are diagnostics only.',
    'The parent is the top of the U.S. tree only. The middle of the tree is lost. One global '
    'firm can appear as several U.S. parents, because the foreign parent is not used for '
    'grouping.',
    'If E8 confirms that the standardized name shows the current owner, pooled years reflect '
    'ownership at the snapshot date, not as of each December 31. The D&B sensitivity count '
    'shows how much the grouping matters.',
    "EPA's standardization can split one parent under two names or merge two. This project "
    'cannot measure either. A self-owned facility that actually has a parent can only lower '
    '`J`.',
    'Codes are self-reported and unvalidated.',
    '`n(a)` pools presence over three years. `J(a,b)` requires the same year.',
    'State and municipal parents stay in, because no field marks them. Federal facilities are '
    'out.',
    'EPA revises earlier years. A later snapshot is a new run with a new pin.',
    'TRI parent links and ITA co-ownership measure close relations. Neither should judge an '
    'embedding that the other trained.',
    'Counts come from all filed forms, not a sample. Standard errors are `none`.',
)


@dataclass(frozen=True)
class _Products:
    '''The tables, report and validation inputs of one computation.'''

    frame: pl.DataFrame
    source_rows: int
    links: tri_parent_link_targets.ParentLinks
    tables: dict[str, pl.DataFrame]
    report: dict


def run_directory(data_dir: Path, run_id: str) -> Path:
    '''The published directory of one run: `derived/epa_tri/parent-links/<run_id>`.'''
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError('unsafe run ID')
    return paths.derived_dir(Path(data_dir), 'epa_tri') / 'parent-links' / run_id


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


def _summary(frame: pl.DataFrame) -> dict:
    return {'rows': frame.height, 'columns': frame.columns,
            'schema': {column: str(dtype) for column, dtype in frame.schema.items()}}


def _by_year(rows: pl.LazyFrame, frame: pl.DataFrame, layouts: dict[int, HeaderLayout],
             transcoded: list[int]) -> dict:
    '''The counts of each year, with whether its raw file was transcoded for reading.'''
    by_year = {}
    for year, counts in tri_facility_years.year_report(rows, frame, layouts).items():
        if 'transcoded' in counts:
            raise ValueError('report keys collide')
        by_year[year] = {**counts, 'transcoded': int(year) in transcoded}
    return by_year


def _products(node_ids: frozenset[str], files: dict[int, Path],
              layouts: dict[int, HeaderLayout], processed_as_of: date,
              scratch: Path) -> _Products:
    '''Compute and validate every table and the report from the selected inputs.

    The rows are read once while `scratch` holds any transcoded copy. Everything after that
    is in memory, so the caller may remove `scratch` when this returns.
    '''
    lazy_rows, transcoded = tri_reader.read_window(files, layouts, scratch)
    rows = lazy_rows.collect().lazy()
    source_rows = rows.select(pl.len()).collect().item()
    frame = tri_facility_years.reduce(rows, layouts, node_ids)
    facility_years = tri_facility_years.public(frame)
    tri_facility_years.validate_facility_years(facility_years, source_rows)
    links = tri_parent_link_targets.estimate(frame, processed_as_of=processed_as_of)
    tri_parent_link_targets.validate_parent_links(links, node_ids)
    industries = tri_parent_industries.build_parent_industries(frame)
    tri_parent_industries.validate_parent_industries(industries, frame)
    tables = {
        'tri_parent_links': links.targets,
        'tri_parent_link_marginals': links.marginals,
        'tri_parent_link_support': links.support,
        'tri_parent_industries': industries,
        'tri_facility_years': facility_years,
    }
    own = {
        'contracts': CONTRACTS,
        'processed_as_of': processed_as_of.isoformat(),
        'by_year': _by_year(rows, frame, layouts, transcoded),
        'parents': tri_parent_industries.parent_report(industries, frame),
        'tables': {name: _summary(tables[name]) for name in TABLES},
        'limits': list(LIMITS),
        'universe': tri_parent_link_targets.UNIVERSE.format(date=processed_as_of.isoformat()),
        'size_gate': 'pending',
    }
    if set(own) & set(links.report):
        raise ValueError('report keys collide')
    report = _normalized({**own, **links.report})
    return _Products(frame, source_rows, links, tables, report)


def _write_tables(staging: Path, products: _Products, node_ids: frozenset[str]) -> None:
    '''Write each table, then validate the serialized frames and compare them in order.'''
    for name in TABLES:
        file = staging / (name + '.parquet')
        if name == 'tri_parent_links':
            target_contract.write_targets(products.tables[name], file)
        else:
            products.tables[name].lazy().sink_parquet(file)
    serialized = {name: pl.read_parquet(staging / (name + '.parquet')) for name in TABLES}
    tri_facility_years.validate_facility_years(serialized['tri_facility_years'],
                                               products.source_rows)
    tri_parent_link_targets.validate_parent_links(
        tri_parent_link_targets.ParentLinks(
            serialized['tri_parent_links'], serialized['tri_parent_link_marginals'],
            serialized['tri_parent_link_support'], products.links.report),
        node_ids)
    tri_parent_industries.validate_parent_industries(serialized['tri_parent_industries'],
                                                     products.frame)
    for name in TABLES:
        if not _same(ordered_equal(serialized[name].lazy(), products.tables[name].lazy())):
            raise ValueError(f'{name}: serialized table differs from the in-memory result')


def _inputs(run_id: str, selected: tri_codes.SelectedNodes, raw: list[dict],
            processed_as_of: date, layouts: dict[int, HeaderLayout], software: dict,
            execution: dict) -> dict:
    '''The provenance record of one build, in the form JSON reads it back.'''
    return _normalized({
        'run_id': run_id,
        'contracts': CONTRACTS,
        'codes': selected.provenance(),
        'raw': raw,
        'processed_as_of': processed_as_of.isoformat(),
        'window': list(tri_raw.WINDOW),
        'layouts': tri_layout.layouts_json(layouts),
        'rules': RULES,
        'software': software,
        'execution': execution,
    })


def _recheck(data_dir: Path, selected: tri_codes.SelectedNodes, software: dict, inputs: dict,
             processed_as_of: date) -> None:
    '''Refuse any change of the pinned inputs or the software since the build began.'''
    selected.verify()
    if freeze_software() != software:
        raise ValueError('executing software changed before publication')
    files = tri_raw.select_files(data_dir, processed_as_of)
    if tri_raw.citations(data_dir, files) != inputs['raw']:
        raise ValueError('cited raw provenance changed')


def build(
    data_dir: Path,
    run_id: str,
    *,
    codes_run: str,
    codes_outputs_sha256: str,
    processed_as_of: date,
    layouts: dict[int, HeaderLayout] | None = None,
) -> dict:
    '''Build, check and publish one immutable bundle under `run_directory(data_dir, run_id)`.

    An existing final or `.part` name fails before anything is written. `layouts` defaults
    to the committed production layout. The result names the run, its directory and the
    SHA-256 of its `outputs.json`, the detached pin.
    '''
    data_dir = Path(data_dir)
    layouts = tri_layout.load_layouts() if layouts is None else layouts
    final, staging = target_io.stage(run_directory(data_dir, run_id).parent, run_id, data_dir)
    try:
        scratch = staging / '.scratch'
        scratch.mkdir()
        software = freeze_software()
        selected = tri_codes.select_nodes(data_dir, codes_run,
                                          codes_outputs_sha256=codes_outputs_sha256)
        files = tri_raw.select_files(data_dir, processed_as_of)
        products = _products(selected.node_ids, files, layouts, processed_as_of, scratch)
        _write_tables(staging, products, selected.node_ids)
        geography_references.safe_path(scratch, data_dir)
        shutil.rmtree(scratch)
        inputs = _inputs(run_id, selected, tri_raw.citations(data_dir, files), processed_as_of,
                         layouts, software, _execution())
        target_io.write_json(staging / 'inputs.json', inputs)
        target_io.write_json(staging / 'report.json', products.report)
        _recheck(data_dir, selected, software, inputs, processed_as_of)
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


def _recorded(inputs: dict) -> tuple[str, str, date]:
    '''The recorded codes run, its detached pin and the snapshot date of `inputs.json`.'''
    if set(inputs) != INPUT_FIELDS:
        raise ValueError('recorded inputs are malformed')
    try:
        codes = inputs['codes']
        codes_run, codes_pin = codes['run_id'], codes['outputs_sha256']
        processed_as_of = date.fromisoformat(inputs['processed_as_of'])
    except (KeyError, TypeError, ValueError):
        raise ValueError('recorded inputs are malformed') from None
    if not isinstance(codes_run, str) or not isinstance(codes_pin, str):
        raise ValueError('recorded inputs are malformed')
    return codes_run, codes_pin, processed_as_of


def verify_bundle(directory: Path, data_dir: Path, *, expected_outputs_sha256: str,
                  layouts: dict[int, HeaderLayout] | None = None) -> dict:
    '''Authenticate a published bundle by its detached pin, then recompute it offline.

    The pin, the exact file set and the inventory are checked before any recomputation.
    The recorded layouts must equal `layouts` (by default the committed production layout),
    and the recorded software must equal the executing software. Every table is recomputed
    in a temporary directory outside `data_dir` from the recorded codes run, pin and
    snapshot date and compared in physical order. Then the report and the inputs (with
    their recorded execution) must equal the recomputed ones.
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
    codes_run, codes_pin, processed_as_of = _recorded(inputs)
    if inputs['run_id'] != directory.name:
        raise ValueError('recorded run ID differs from the directory')
    if inputs['contracts'] != CONTRACTS or report.get('contracts') != CONTRACTS:
        raise ValueError('contract versions differ')
    layouts = tri_layout.load_layouts() if layouts is None else layouts
    if inputs['layouts'] != _normalized(tri_layout.layouts_json(layouts)):
        raise ValueError('recorded layouts differ from the supplied layouts')
    software = freeze_software()
    if inputs['software'] != software:
        raise ValueError('executing software differs from the build')

    selected = tri_codes.select_nodes(data_dir, codes_run, codes_outputs_sha256=codes_pin)
    files = tri_raw.select_files(data_dir, processed_as_of)
    with tempfile.TemporaryDirectory() as temporary:
        products = _products(selected.node_ids, files, layouts, processed_as_of,
                             Path(temporary))
    for name in TABLES:
        published = pl.scan_parquet(directory / (name + '.parquet'))
        if not _same(ordered_equal(published, products.tables[name].lazy())):
            raise ValueError(f'{name}: published table differs from the recomputation')
    if products.report != report:
        raise ValueError('published report differs from the recomputation')
    if _inputs(directory.name, selected, tri_raw.citations(data_dir, files), processed_as_of,
               layouts, software, inputs['execution']) != inputs:
        raise ValueError('recorded inputs differ from the recomputation')
    return {
        'run_id': directory.name,
        'outputs_sha256': expected_outputs_sha256,
        'processed_as_of': processed_as_of.isoformat(),
        'rows': {name: report['tables'][name]['rows'] for name in TABLES},
    }


def compare_runs(first: Path, second: Path) -> dict:
    '''Compare two published bundles table by table, in order, and their reports exactly.

    Each bundle must match its own `outputs.json` inventory. Equality establishes replay,
    not trust: neither bundle is authenticated by a detached pin here. The run ID and the
    execution record live in `inputs.json`, which is not compared.
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
