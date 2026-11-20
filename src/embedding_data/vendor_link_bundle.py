'''Publish, verify and compare immutable Stage 14 vendor-link bundles.

A bundle holds the four tables of one build (the O6 targets, the industry marginals, the cell
support and the firm pairs), `inputs.json` (selection and provenance), `report.json`
(accounting, distributions and limits) and the detached inventory `outputs.json`. `build`
stages into `<RUN_ID>.part` and keeps its scratch inside that directory. It rechecks its
pinned inputs and its software just before publication, and only then renames the staging
directory. A failure removes only that staging directory.

`verify_bundle` authenticates the detached pin, the file set and the inventory before it
reads anything else, then recomputes every table offline in a temporary directory outside
the data root. `compare_runs` checks two published bundles for exact logical replay. It
does not establish trust. Nothing here loads an environment file, reads a credential,
constructs an HTTP client or runs an upstream builder.
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
    sam_raw,
    target_contract,
    target_io,
    usaspending_raw,
    vendor_link_codes,
    vendor_link_layouts,
    vendor_link_pairs,
    vendor_link_readers,
    vendor_link_targets,
)
from embedding_data.usaspending_raw import WINDOW
from embedding_data.vendor_link_layouts import ExtractLayout, SubawardLayout

TABLES = ('vendor_links', 'vendor_link_marginals', 'vendor_link_support', 'vendor_link_pairs')
FILES = (*(name + '.parquet' for name in TABLES), 'inputs.json', 'report.json')
CONTRACTS = {
    'pairs': 'vendor-link-pairs-v1',
    'vendor_links': 'vendor-links-v1',
    'targets': 'targets-v1',
    'subaward_headers': 'usaspending-subaward-headers-v1',
    'extract_layout': 'sam-extract-layout-v1',
}
SOFTWARE_ROOT = paths.PROJECT_ROOT
SOFTWARE_FILES = (
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
    'src/embedding_data/sam_access.py',
    'src/embedding_data/sam_extract_layout.json',
    'src/embedding_data/sam_raw.py',
    'src/embedding_data/target_contract.py',
    'src/embedding_data/target_io.py',
    'src/embedding_data/usaspending_raw.py',
    'src/embedding_data/usaspending_subaward_headers.json',
    'src/embedding_data/usaspending_vendor_links.py',
    'src/embedding_data/vendor_link_bundle.py',
    'src/embedding_data/vendor_link_codes.py',
    'src/embedding_data/vendor_link_layouts.py',
    'src/embedding_data/vendor_link_pairs.py',
    'src/embedding_data/vendor_link_readers.py',
    'src/embedding_data/vendor_link_targets.py',
    'pyproject.toml',
    'uv.lock',
)
RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')
PIN = re.compile(r'[0-9a-f]{64}')
INPUT_FIELDS = frozenset({
    'run_id', 'contracts', 'codes', 'raw', 'snapshot', 'sam_month', 'window', 'registries',
    'rules', 'software', 'execution',
})
USABLE = 'usable'
RULES = {
    'report': (
        'each subaward row is one report with the first status that applies: uei_unusable '
        '(a prime or subcontractor UEI that is not ^[A-Z0-9]{12}$ after stripping ASCII '
        'whitespace), action_date_invalid, outside_window (a fiscal year, the calendar year '
        'of the action date plus three months, outside 2024-2026) or usable'
    ),
    'corporate_group': (
        'a pair is intra-group when any of its usable reports shows the subcontractor parent '
        'UEI equal to the prime UEI, the prime parent UEI equal to the subcontractor UEI, or '
        'both parent UEIs present and equal, each parent UEI valid under the UEI rule'
    ),
    'firm': (
        'each distinct UEI on a usable report has the first status that applies: not_in_sam, '
        'dnb_era_record (an extract row last updated before 2022-04-04, with a blank or '
        'invalid last update date, or with a D&B EVS source), naics_missing, naics_conflict, '
        'naics_not_2022 or eligible; a malformed primary code on a firm whose codes the build '
        'reads fails the build'
    ),
    'pair': (
        'each distinct (prime UEI, subcontractor UEI) pair of usable reports has the first '
        'status that applies: self_link, intra_group, prime_ineligible, sub_ineligible or '
        'eligible'
    ),
    'measure': (
        'for each cell (s, d) with an eligible pair, supplier_share is S(s,d)/n_sup(s) and '
        'buyer_share is B(s,d)/n_buy(d), each firm counted once in each role over the pooled '
        'window; intra_group pairs of two eligible firms enter the sensitivity counts only'
    ),
}
LIMITS = (
    'The population is federal prime contractors and the subcontractors they report. It is '
    'not all firms or all business-to-business trade.',
    'Industries are SAM.gov registrations at the extract date. A firm whose industry changed '
    'after a subaward counts under its new code. A firm whose registration expired more than '
    '6 months before the extract is missing.',
    'A subcontractor with a UEI only has no code. Its links are lost. Join coverage measures '
    'this loss.',
    'Codes, links and amounts are self-reported and unvalidated. That codes are self-reported '
    'is also what the KYB use tests.',
    "One primary code per firm hides a firm's other industries. Other codes are diagnostics "
    'only.',
    'Corporate groups are seen only through reported parent UEIs. A group with no reported '
    'parent stays in the headline cells.',
    'One firm can hold several UEIs. This project cannot join them.',
    'The window spans the move of subaward reporting from FSRS.gov to SAM.gov on 2025-03-08. '
    'Counts by year and month show any break, but no correction is made.',
    'USAspending revises its data. A later snapshot is a new run with a new pin.',
    'Counts come from all reports, not a sample. Standard errors are `none`.',
    'Vendor links, TRI parent links and ITA co-ownership measure different relations. '
    'Excluding intra-group pairs keeps vendor links apart from ownership. The protocol '
    'section, O18, decides which families may judge one another.',
)


@dataclass(frozen=True)
class _Products:
    '''The tables, the report and the validation inputs of one computation.'''

    tables: dict[str, pl.DataFrame]
    links: vendor_link_targets.VendorLinks
    usable_reports: int
    report: dict


def run_directory(data_dir: Path, run_id: str) -> Path:
    '''The published directory of one run: `derived/usaspending/vendor-links/<run_id>`.'''
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError('unsafe run ID')
    return paths.derived_dir(Path(data_dir), 'usaspending') / 'vendor-links' / run_id


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


def _registries(subaward_layouts: dict[int, SubawardLayout] | None,
                extract_layout: ExtractLayout | None) -> tuple:
    '''The supplied registries, or the committed ones loaded now. Refuses another window.'''
    layouts = (vendor_link_layouts.load_subaward_layouts() if subaward_layouts is None
               else subaward_layouts)
    layout = (vendor_link_layouts.load_extract_layout() if extract_layout is None
              else extract_layout)
    if set(layouts) != set(WINDOW):
        raise ValueError('subaward registry years differ from the window')
    return layouts, layout


def _registries_json(layouts: dict[int, SubawardLayout], layout: ExtractLayout) -> dict:
    return _normalized({'subaward_headers': vendor_link_layouts.subaward_layouts_json(layouts),
                        'extract_layout': vendor_link_layouts.extract_layout_json(layout)})


def _universe(snapshot: date, month: str) -> str:
    return vendor_link_targets.UNIVERSE.format(snapshot=snapshot.isoformat(), month=month)


def _citations(data_dir: Path, files: dict[int, Path], extract_file: Path) -> dict:
    '''The verified manifest entries of the selected subaward files and the extract.'''
    (extract,) = usaspending_raw.citations(data_dir, [extract_file])
    return {'subawards': usaspending_raw.citations(data_dir, files.values()),
            'extract': extract}


def _inputs(run_id: str, selected: vendor_link_codes.SelectedNodes, raw: dict, snapshot: date,
            month: str, layouts: dict[int, SubawardLayout], layout: ExtractLayout,
            software: dict, execution: dict) -> dict:
    '''The provenance record of one build, in the form JSON reads it back.'''
    return _normalized({
        'run_id': run_id,
        'contracts': CONTRACTS,
        'codes': selected.provenance(),
        'raw': raw,
        'snapshot': snapshot.isoformat(),
        'sam_month': month,
        'window': list(WINDOW),
        'registries': _registries_json(layouts, layout),
        'rules': RULES,
        'software': software,
        'execution': execution,
    })


def _summary(frame: pl.DataFrame) -> dict:
    return {'rows': frame.height, 'columns': frame.columns,
            'schema': {column: str(dtype) for column, dtype in frame.schema.items()}}


def _products(node_ids: frozenset[str], files: dict[int, Path], extract_file: Path,
              layouts: dict[int, SubawardLayout], layout: ExtractLayout, snapshot: date,
              month: str, scratch: Path) -> _Products:
    '''Compute and validate every table and the report from the selected inputs.

    The subaward rows are scanned from Parquet parts under `scratch`, so every value that
    needs them is collected here, before the caller removes `scratch`.
    '''
    read = vendor_link_readers.read_subawards(files, layouts, scratch)
    vendor_link_pairs.check_subaward_types(read.rows)
    reported = vendor_link_pairs.reports(read.rows, layouts)
    extract = vendor_link_readers.read_extract(extract_file, layout)
    unreadable = vendor_link_readers.unreadable_extract_lines(extract_file, layout)
    usable = reported.filter(pl.col('report_status') == USABLE)
    firm_table = vendor_link_pairs.firms(usable, extract, layout, node_ids)
    pair_table = vendor_link_pairs.pairs(usable, firm_table)
    usable_reports = usable.select(pl.len()).collect().item()
    vendor_link_pairs.validate_pairs(pair_table, usable_reports)
    counts = vendor_link_pairs.report_counts(
        reported, firm_table, pair_table, extract, layouts=layouts, layout=layout,
        node_ids=node_ids, unreadable=unreadable)
    links = vendor_link_targets.estimate(pair_table, snapshot=snapshot, month=month)
    vendor_link_targets.validate_vendor_links(links, pair_table, node_ids)
    tables = {
        'vendor_links': links.targets,
        'vendor_link_marginals': links.marginals,
        'vendor_link_support': links.support,
        'vendor_link_pairs': pair_table,
    }
    report = _normalized({
        'contracts': CONTRACTS,
        'snapshot': snapshot.isoformat(),
        'sam_month': month,
        'window': list(WINDOW),
        **counts,
        **links.report,
        'bom': sorted(year for year, bom in read.bom.items() if bom),
        'tables': {name: _summary(tables[name]) for name in TABLES},
        'limits': list(LIMITS),
        'universe': _universe(snapshot, month),
        'size_gate': 'pending',
    })
    return _Products(tables, links, usable_reports, report)


def _write_tables(staging: Path, products: _Products, node_ids: frozenset[str]) -> None:
    '''Write each table, then validate the serialized tables and compare them in order.'''
    for name in TABLES:
        file = staging / (name + '.parquet')
        if name == 'vendor_links':
            target_contract.write_targets(products.tables[name], file)
        else:
            products.tables[name].write_parquet(file)
    serialized = {name: pl.read_parquet(staging / (name + '.parquet')) for name in TABLES}
    vendor_link_pairs.validate_pairs(serialized['vendor_link_pairs'], products.usable_reports)
    vendor_link_targets.validate_vendor_links(
        vendor_link_targets.VendorLinks(
            serialized['vendor_links'], serialized['vendor_link_marginals'],
            serialized['vendor_link_support'], products.links.report),
        serialized['vendor_link_pairs'], node_ids)
    for name in TABLES:
        if not _same(ordered_equal(serialized[name].lazy(), products.tables[name].lazy())):
            raise ValueError(f'{name}: serialized table differs from the in-memory result')


def _recheck(data_dir: Path, selected: vendor_link_codes.SelectedNodes, software: dict,
             raw: dict) -> None:
    '''Refuse any change of the pinned inputs or the software since the build began.'''
    selected.verify()
    if freeze_software() != software:
        raise ValueError('executing software changed before publication')
    try:
        target_io.verify_raw(data_dir, [*raw['subawards'], raw['extract']])
    except KeyError:
        raise ValueError('a cited raw file is not recorded') from None


def build(
    data_dir: Path,
    run_id: str,
    *,
    codes_run: str,
    codes_outputs_sha256: str,
    snapshot: date,
    sam_month: str,
    subaward_layouts: dict[int, SubawardLayout] | None = None,
    extract_layout: ExtractLayout | None = None,
) -> dict:
    '''Build, check and publish one immutable bundle under `run_directory(data_dir, run_id)`.

    An existing final or `.part` name fails before anything is written. A registry of None
    is the committed one, loaded through `vendor_link_layouts` when the build starts.
    '''
    data_dir = Path(data_dir)
    final, staging = target_io.stage(run_directory(data_dir, run_id).parent, run_id, data_dir)
    try:
        scratch = staging / '.scratch'
        scratch.mkdir()
        software = freeze_software()
        layouts, layout = _registries(subaward_layouts, extract_layout)
        selected = vendor_link_codes.select_nodes(
            data_dir, codes_run, codes_outputs_sha256=codes_outputs_sha256)
        files = usaspending_raw.select_files(data_dir, snapshot)
        extract_file = sam_raw.select_extract(data_dir, sam_month)
        raw = _citations(data_dir, files, extract_file)
        products = _products(selected.node_ids, files, extract_file, layouts, layout, snapshot,
                             sam_month, scratch)
        _write_tables(staging, products, selected.node_ids)
        geography_references.safe_path(scratch, data_dir)
        shutil.rmtree(scratch)
        inputs = _inputs(run_id, selected, raw, snapshot, sam_month, layouts, layout, software,
                         _execution())
        target_io.write_json(staging / 'inputs.json', inputs)
        target_io.write_json(staging / 'report.json', products.report)
        _recheck(data_dir, selected, software, raw)
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


def _recorded(inputs: dict) -> tuple[str, str, date, str]:
    '''The recorded codes run, codes pin, snapshot and extract month of `inputs.json`.'''
    if set(inputs) != INPUT_FIELDS:
        raise ValueError('recorded inputs are malformed')
    try:
        codes = inputs['codes']
        codes_run, codes_pin = codes['run_id'], codes['outputs_sha256']
        if not isinstance(codes_run, str) or not isinstance(codes_pin, str):
            raise ValueError('recorded codes selection is not text')
        return (codes_run, codes_pin, date.fromisoformat(inputs['snapshot']),
                sam_raw.parse_month(inputs['sam_month']))
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ValueError('recorded inputs are malformed') from None


def verify_bundle(directory: Path, data_dir: Path, *, expected_outputs_sha256: str,
                  subaward_layouts: dict[int, SubawardLayout] | None = None,
                  extract_layout: ExtractLayout | None = None) -> dict:
    '''Authenticate a published bundle by its detached pin, then recompute it offline.

    The pin, the exact file set and the inventory are checked before anything else is read.
    The recorded registries must equal the supplied ones (None is the committed one) and the
    recorded software the executing software. Every table is recomputed in a temporary
    directory outside `data_dir` from the recorded codes run and pin, snapshot and month, and
    compared in physical order. Then the report and the inputs, with their recorded
    execution, must equal the recomputed ones.
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
    codes_run, codes_pin, snapshot, month = _recorded(inputs)
    if inputs['run_id'] != directory.name:
        raise ValueError('recorded run ID differs from the directory')
    if inputs['contracts'] != CONTRACTS or report.get('contracts') != CONTRACTS:
        raise ValueError('contract versions differ')
    if report.get('universe') != _universe(snapshot, month):
        raise ValueError('recorded universe differs')
    layouts, layout = _registries(subaward_layouts, extract_layout)
    if inputs['registries'] != _registries_json(layouts, layout):
        raise ValueError('recorded registries differ from the supplied ones')
    software = freeze_software()
    if inputs['software'] != software:
        raise ValueError('executing software differs from the build')

    selected = vendor_link_codes.select_nodes(data_dir, codes_run,
                                              codes_outputs_sha256=codes_pin)
    files = usaspending_raw.select_files(data_dir, snapshot)
    extract_file = sam_raw.select_extract(data_dir, month)
    raw = _citations(data_dir, files, extract_file)
    with tempfile.TemporaryDirectory() as temporary:
        products = _products(selected.node_ids, files, extract_file, layouts, layout, snapshot,
                             month, Path(temporary))
        for name in TABLES:
            published = pl.scan_parquet(directory / (name + '.parquet'))
            if not _same(ordered_equal(published, products.tables[name].lazy())):
                raise ValueError(f'{name}: published table differs from the recomputation')
    if products.report != report:
        raise ValueError('published report differs from the recomputation')
    if _inputs(directory.name, selected, raw, snapshot, month, layouts, layout, software,
               inputs['execution']) != inputs:
        raise ValueError('recorded inputs differ from the recomputation')
    return {
        'run_id': directory.name,
        'outputs_sha256': expected_outputs_sha256,
        'rows': {name: report['tables'][name]['rows'] for name in TABLES},
    }


def compare_runs(first: Path, second: Path) -> dict:
    '''Compare two published bundles table by table, in order, and their reports exactly.

    Each bundle must match its own `outputs.json` inventory. `inputs.json` is not compared.
    Equality establishes replay, not trust: neither bundle is authenticated by a detached
    pin here.
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
