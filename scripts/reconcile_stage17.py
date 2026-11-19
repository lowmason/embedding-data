'''Independent Stage 17 cross-checks over one published ACS wage microdata bundle.

`reconcile` checks the person table against the Stage 8 core table and the Stage 4 NAICS
tables. It joins every person row to its Stage 8 row through `source_row` and compares every
carried column, at most 20 columns at a time. It recomputes the ten new columns and the
headline funnel from the Stage 8 columns with rules written here from the spec's "Rules for the
new columns", and it checks spec item 6 against the Stage 4 node and edge tables. It imports no
`embedding_data` module: only the standard library and Polars.

`reconcile` takes `--data-dir`, `--run` and `--outputs-sha256`. It checks the detached
`outputs.json` pin first. Then each file it reads must match its record in that inventory or in
the pinned upstream inventory that `inputs.json` names. It prints one sorted JSON line of
counts, column names and booleans, never a person value, and returns 0 when everything is equal
and 1 otherwise. A refusal prints a fixed reason.

`freeze` and `preservation` prove spec item 7: the stage's runs wrote nothing outside their own
directories. `freeze` records the SHA-256 and size of every regular file under `raw` and
`derived` in `derived/acs/wage-microdata-controls/<ID>/freeze.json`, except the raw manifest,
whose SHA-256, size and line count it records apart, and the stage's own trees. `preservation`
authenticates that record against a detached pin, walks the same trees again and prints one JSON
line of paths and flags. Both read each file in fixed-size chunks and refuse a symlink anywhere
in the walk. They print paths and counts only, never file contents. A refusal prints a fixed
reason (and, for an entry in the walk, its path) and returns 1, as does a changed tree.
'''

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from collections.abc import Iterable
from itertools import accumulate, zip_longest
from operator import and_
from pathlib import Path

import polars as pl

BUNDLES = Path('derived/acs/wage-microdata')
MAPPINGS = Path('derived/acs/mapping')
CODES = Path('derived/codes')
PERSONS = 'acs_wage_persons.parquet'
CORE = 'acs_core_canonical.parquet'
NODES = 'naics_nodes.parquet'
EDGES = 'naics_edges.parquet'
RUN_ID = re.compile('[A-Za-z0-9][A-Za-z0-9_-]*')
KEY = 'source_row'
GROUP_SIZE = 20
CONTROLS = Path('derived/acs/wage-microdata-controls')
TREES = ('raw', 'derived')
MANIFEST = Path('raw/manifest.jsonl')
FREEZE = 'freeze.json'
READ_SIZE = 1 << 20

# The spec's Columns table, in its order. Every column that is not new is carried from Stage 8.
HEADLINE_Q = ('QINCWAGE', 'QIND', 'QOCC', 'QUHRSWOR', 'QWKSWORK2', 'QAGE', 'QSEX', 'QEDUC',
              'QCLASSWK')
ALLOCATION_Q = (*HEADLINE_Q, 'QDEGFIELD')
NEW_TYPES = {
    'log_wage_2010': pl.Float64,
    'industry_node_code': pl.String,
    'industry_node_level': pl.String,
    'industry_delivered_node_code': pl.String,
    'flag_industry_shared_node': pl.Boolean,
    'flag_any_allocated': pl.Boolean,
    'flag_incwage_topcoded': pl.Boolean,
    'flag_full_time_full_year': pl.Boolean,
    'flag_wage_salary': pl.Boolean,
    'flag_headline': pl.Boolean,
}
COLUMNS = (
    'source_parquet_sha256', KEY, 'YEAR', 'acs_sample_id',
    'PERWT', *(f'REPWTP{n}' for n in range(1, 81)),
    'INCWAGE', 'INCWAGE_CPIU_2010', 'log_wage_2010',
    'UHRSWORK', 'WKSWORK2', 'CLASSWKR', 'CLASSWKRD',
    'SEX', 'AGE', 'EDUC', 'EDUCD', 'DEGFIELD', 'DEGFIELDD', 'STATEFIP', 'REGION', 'GQ',
    'OCC', 'OCCSOC', 'occupation_canonical_common_node_id', 'occupation_aggregation_type',
    'IND', 'INDNAICS', 'industry_canonical_common_node_id', 'industry_aggregation_type',
    'industry_canonical_finest_candidates', 'industry_native_node_id', 'industry_node_code',
    'industry_node_level', 'industry_delivered_node_code', 'flag_industry_shared_node',
    *ALLOCATION_Q, 'flag_any_allocated',
    'flag_incwage_topcoded',
    'flag_full_time_full_year', 'flag_wage_salary', 'flag_headline',
)
NEW = tuple(NEW_TYPES)
COMPARED = tuple(name for name in COLUMNS if name not in NEW_TYPES and name != KEY)

COMMON_NODE = 'industry_canonical_common_node_id'
DELIVERED_NODE = 'industry_native_node_id'
# A node ID is `<system>:<vintage>:<level>:<code>`.
NODE_ID = r'^[^:]+:[^:]+:([^:]+):([^:]+)$'
EMPLOYEE_CLASSES = (22, 23, 25, 27, 28)
UNALLOCATED = 'no_headline_allocation'
STEPS = ('earners', UNALLOCATED, 'full_time_full_year', 'wage_salary', 'headline')


class Refused(Exception):
    '''An input that the pins do not authenticate, or rows that cannot be joined.

    The message is a fixed reason.
    '''


def sha256(file: Path) -> str:
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run_directory(root: Path, run_id: object, reason: str) -> Path:
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise Refused(reason)
    return root / run_id


def pinned_inventory(directory: Path, pin: str, reason: str) -> dict:
    '''The inventory of a run directory, once its `outputs.json` matches the pin.'''
    outputs = directory / 'outputs.json'
    if not outputs.is_file() or sha256(outputs) != pin:
        raise Refused(reason)
    return json.loads(outputs.read_text())


def inventory_file(directory: Path, inventory: dict, name: str, reason: str) -> Path:
    '''One file of a run, once its bytes match its record in the pinned inventory.'''
    file = directory / name
    record = inventory.get(name)
    expected = record.get('sha256') if isinstance(record, dict) else None
    if not file.is_file() or sha256(file) != expected:
        raise Refused(reason)
    return file


def recorded_runs(inputs: object) -> tuple[str, str, str, str]:
    '''The Stage 8 mapping run and pin and the Stage 4 codes run and pin in `inputs.json`.'''
    try:
        mapping, codes = inputs['mapping'], inputs['codes']
        runs = (mapping['run_id'], mapping['outputs_sha256'], codes['run_id'],
                codes['outputs_sha256'])
    except (KeyError, TypeError):
        raise Refused('recorded inputs are malformed') from None
    if not all(isinstance(value, str) for value in runs) or not all(
            RUN_ID.fullmatch(run) for run in runs[::2]):
        raise Refused('recorded inputs are malformed')
    return runs


def earners(core: pl.LazyFrame) -> pl.LazyFrame:
    '''The file's rows: every Stage 8 core row with `INCWAGE > 0`, in source order.'''
    return core.filter(pl.col('INCWAGE') > 0)


def node_part(column: str, part: int) -> pl.Expr:
    '''Part 1 (the level) or part 2 (the code) of a node ID, unchanged.'''
    return pl.col(column).str.extract(NODE_ID, part)


def derive(core: pl.LazyFrame) -> pl.LazyFrame:
    '''`source_row`, `YEAR`, the ten new columns and the funnel's allocation step per earner.

    Every rule reads the file's rows only, so the windows run after the earner filter.
    '''
    unallocated = ~pl.any_horizontal(pl.col(name).ne_missing(0) for name in HEADLINE_Q)
    full_time_full_year = (pl.col('UHRSWORK') >= 35) & (pl.col('WKSWORK2') == 6)
    wage_salary = pl.col('CLASSWKRD').is_in(EMPLOYEE_CLASSES)
    shared = pl.col('INDNAICS').n_unique().over(COMMON_NODE) > 1
    return earners(core).select(
        KEY,
        'YEAR',
        pl.col('INCWAGE_CPIU_2010').log().cast(pl.Float64).alias('log_wage_2010'),
        node_part(COMMON_NODE, 2).alias('industry_node_code'),
        node_part(COMMON_NODE, 1).alias('industry_node_level'),
        node_part(DELIVERED_NODE, 2).alias('industry_delivered_node_code'),
        shared.alias('flag_industry_shared_node'),
        pl.any_horizontal(pl.col(name).ne_missing(0) for name in ALLOCATION_Q)
        .alias('flag_any_allocated'),
        (pl.col('INCWAGE') == pl.col('INCWAGE').max().over('STATEFIP', 'YEAR'))
        .alias('flag_incwage_topcoded'),
        full_time_full_year.alias('flag_full_time_full_year'),
        wage_salary.alias('flag_wage_salary'),
        (unallocated & full_time_full_year & wage_salary & ~shared).alias('flag_headline'),
        unallocated.alias(UNALLOCATED),
    )


def funnel(derived: pl.LazyFrame) -> list[dict]:
    '''The headline funnel from the recomputed flags: each step keeps the rows of the last.'''
    conditions = (pl.lit(True), pl.col(UNALLOCATED), pl.col('flag_full_time_full_year'),
                  pl.col('flag_wage_salary'), ~pl.col('flag_industry_shared_node'))
    steps = derived.select('YEAR', *(condition.alias(step) for step, condition in
                                     zip(STEPS, accumulate(conditions, and_), strict=True)))
    counts = steps.group_by('YEAR').agg(pl.col(*STEPS).sum()).sort('YEAR').collect()
    return [{'step': step, 'total': int(counts[step].sum()),
             'by_year': {str(year): int(n) for year, n in counts.select('YEAR', step).rows()}}
            for step in STEPS]


def differences(first: pl.LazyFrame, second: pl.LazyFrame, names: Iterable[str]) -> dict:
    '''Per column, the joined rows whose two values differ. A null against a value differs.

    The frames are joined on `source_row`, and only the one-row aggregate is collected.
    '''
    names = list(names)
    other = {name: f'{name}:second' for name in names}
    joined = first.select(KEY, *names).join(second.select(KEY, *names).rename(other), on=KEY,
                                            how='inner')
    counts = joined.select(pl.col(name).ne_missing(pl.col(other[name])).sum()
                           for name in names).collect(engine='streaming')
    return counts.row(0, named=True)


def check_schema(persons: pl.LazyFrame, core: pl.LazyFrame) -> None:
    '''The contract's columns in order, carried ones with their Stage 8 types.'''
    carried = core.collect_schema()
    expected = [(name, NEW_TYPES[name] if name in NEW_TYPES else carried.get(name))
                for name in COLUMNS]
    if list(persons.collect_schema().items()) != expected:
        raise Refused('person table schema differs from the contract')


def check_rows(persons: pl.LazyFrame, core: pl.LazyFrame) -> int:
    '''The number of rows, once the person keys equal the unique Stage 8 earner keys in order.'''
    person_keys, earner_keys = (frame.to_series() for frame in pl.collect_all(
        [persons.select(KEY), earners(core).select(KEY)]))
    if earner_keys.n_unique() != earner_keys.len() or not person_keys.equals(earner_keys):
        raise Refused('person rows differ from the Stage 8 earners')
    return earner_keys.len()


def single_child_ancestor(delivered: str, node: str, parents: dict, children: Counter) -> bool:
    '''True when `delivered` is `node` itself or a single-child ancestor of it.

    Walking up from `node`, each parent must have exactly one child until `delivered` is met.
    '''
    while node != delivered:
        node = parents.get(node)
        if node is None or children[node] != 1:
            return False
    return True


def node_failures(pairs: Iterable[tuple], nodes: pl.DataFrame, edges: pl.DataFrame) -> dict:
    '''Rows that break spec item 6, from (node code, delivered node code, rows) triples.

    `unknown_node` counts rows whose node code or delivered node code names no NAICS 2022 node.
    `delivered_node_chain` counts the other rows whose delivered node is neither the node
    itself nor an ancestor with one child at each level down to it.
    '''
    naics = nodes.filter((pl.col('system') == 'naics') & (pl.col('vintage') == 2022))
    ids = dict(naics.select('code', 'node_id').rows())
    hierarchy = edges.filter(pl.col('edge_type') == 'hierarchy')
    parents = dict(hierarchy.select('child_id', 'parent_id').rows())
    children = Counter(hierarchy['parent_id'].to_list())
    failures = {'unknown_node': 0, 'delivered_node_chain': 0}
    for code, delivered, rows in pairs:
        if code not in ids or delivered not in ids:
            failures['unknown_node'] += rows
        elif not single_child_ancestor(ids[delivered], ids[code], parents, children):
            failures['delivered_node_chain'] += rows
    return failures


def reconcile(data_dir: Path, run_id: str, pin: str) -> dict:
    '''Check the person table against Stage 8 and Stage 4 and count the differences.'''
    directory = run_directory(data_dir / BUNDLES, run_id, 'unsafe run ID')
    inventory = pinned_inventory(directory, pin, 'detached pin differs')
    bundle_reason = 'bundle file differs from its inventory'
    persons_file = inventory_file(directory, inventory, PERSONS, bundle_reason)
    inputs = json.loads(inventory_file(directory, inventory, 'inputs.json',
                                       bundle_reason).read_text())
    report = json.loads(inventory_file(directory, inventory, 'report.json',
                                       bundle_reason).read_text())
    mapping_run, mapping_pin, codes_run, codes_pin = recorded_runs(inputs)
    mapping = data_dir / MAPPINGS / mapping_run
    mapping_inventory = pinned_inventory(mapping, mapping_pin, 'Stage 8 pin differs')
    core_file = inventory_file(mapping, mapping_inventory, CORE,
                               'Stage 8 core table differs from its inventory')
    codes = data_dir / CODES / codes_run
    codes_inventory = pinned_inventory(codes, codes_pin, 'Stage 4 pin differs')
    codes_reason = 'Stage 4 table differs from its inventory'
    nodes_file = inventory_file(codes, codes_inventory, NODES, codes_reason)
    edges_file = inventory_file(codes, codes_inventory, EDGES, codes_reason)

    persons, core = pl.scan_parquet(persons_file), pl.scan_parquet(core_file)
    check_schema(persons, core)
    rows = check_rows(persons, core)
    mismatches = Counter()
    for start in range(0, len(COMPARED), GROUP_SIZE):
        mismatches.update(differences(persons, earners(core), COMPARED[start:start + GROUP_SIZE]))
    derived = derive(core)
    mismatches.update(differences(persons, derived, NEW))
    recomputed = funnel(derived)
    recorded = report.get('funnel') if isinstance(report.get('funnel'), list) else []
    mismatches['funnel'] = sum(step != entry for step, entry in zip_longest(recomputed, recorded))
    pairs = persons.group_by('industry_node_code', 'industry_delivered_node_code').agg(
        pl.len()).collect().rows()
    mismatches.update(node_failures(pairs, pl.read_parquet(nodes_file),
                                    pl.read_parquet(edges_file)))
    differing = {name: count for name, count in mismatches.items() if count}
    return {'equal': not differing, 'rows': rows, 'headline_rows': recomputed[-1]['total'],
            'mismatches': differing}


def control_directory(data_dir: Path, control_dir: Path) -> Path:
    '''`control_dir`, once it is `data_dir/derived/acs/wage-microdata-controls/<ID>`.'''
    location = Path(os.path.abspath(control_dir))
    if (location.parent != Path(os.path.abspath(data_dir / CONTROLS))
            or not RUN_ID.fullmatch(location.name)):
        raise Refused('unsafe control directory')
    return location


def walk(top: Path, root: Path) -> dict[str, int]:
    '''The size of every regular file under `top`, by path relative to `root`.

    A symlink, or any entry that is neither a file nor a directory, is refused.
    '''
    sizes, pending = {}, [top]
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                path = Path(entry.path).relative_to(root).as_posix()
                if entry.is_symlink():
                    raise Refused(f'symlink in the walk: {path}')
                if entry.is_dir():
                    pending.append(Path(entry.path))
                elif entry.is_file():
                    sizes[path] = entry.stat().st_size
                else:
                    raise Refused(f'not a regular file in the walk: {path}')
    return sizes


def tracked(data_dir: Path) -> dict[str, int]:
    '''The size of every regular file under `raw` and `derived`, but the manifest and the runs.

    The runs and the control directories are the stage's own trees. The walk still enters
    them, so a symlink in one is refused.
    '''
    sizes = {}
    for name in TREES:
        top = data_dir / name
        if top.is_symlink():
            raise Refused(f'symlink in the walk: {name}')
        if not top.is_dir():
            raise Refused('raw or derived is not a directory')
        sizes.update(walk(top, data_dir))
    stage = (BUNDLES.parts, CONTROLS.parts)
    return {path: size for path, size in sizes.items()
            if path != MANIFEST.as_posix() and Path(path).parts[:3] not in stage}


def manifest_facts(data_dir: Path) -> dict | None:
    '''The SHA-256, size and line count of the raw manifest, or None when it is absent.

    The last line counts when the file does not end with a newline.
    '''
    file = data_dir / MANIFEST
    if not file.is_file():
        return None
    digest, size, lines, last = hashlib.sha256(), 0, 0, b'\n'
    with file.open('rb') as stream:
        while chunk := stream.read(READ_SIZE):
            digest.update(chunk)
            size += len(chunk)
            lines += chunk.count(b'\n')
            last = chunk[-1:]
    return {'sha256': digest.hexdigest(), 'size': size, 'lines': lines + (last != b'\n')}


def run_names(data_dir: Path) -> list[str]:
    '''The names under `derived/acs/wage-microdata/`, sorted. Absent means none.'''
    directory = data_dir / BUNDLES
    return sorted(os.listdir(directory)) if directory.is_dir() else []


def freeze(data_dir: Path, control_dir: Path) -> dict:
    '''Record the SHA-256 and size of every file the stage's runs must leave alone.'''
    control = control_directory(data_dir, control_dir)
    if os.path.lexists(control):
        raise Refused('control directory exists')
    sizes = tracked(data_dir)
    facts = manifest_facts(data_dir)
    if facts is None:
        raise Refused('manifest is missing')
    files = {path: {'sha256': sha256(data_dir / path), 'size': size}
             for path, size in sorted(sizes.items())}
    record = {'files': files, 'manifest': facts, 'runs': run_names(data_dir)}
    control.mkdir(parents=True)
    file = control / FREEZE
    file.write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    return {'freeze_sha256': sha256(file), 'files': len(files)}


def named_runs(value: str) -> list[str]:
    '''The comma-separated run names, each a safe run ID.'''
    names = value.split(',')
    if not all(RUN_ID.fullmatch(name) for name in names):
        raise Refused('unsafe run ID')
    return names


def preservation(data_dir: Path, control_dir: Path, pin: str, runs: str) -> dict:
    '''Check the frozen files, the manifest and the runs directory against the freeze record.

    It hashes `freeze.json` against the pin before anything else. The result is `preserved`
    only when every frozen file is equal, no file is added outside the runs and the control
    directory, the manifest's SHA-256 and size are equal, and `wage-microdata/` holds exactly the
    frozen runs and the named ones, with no `.part`.
    '''
    record_file = control_directory(data_dir, control_dir) / FREEZE
    if not record_file.is_file() or sha256(record_file) != pin:
        raise Refused('freeze pin differs')
    record = json.loads(record_file.read_text())
    named = named_runs(runs)
    frozen = record['files']
    sizes = tracked(data_dir)
    changed = [path for path, entry in frozen.items() if path in sizes and (
        sizes[path] != entry['size'] or sha256(data_dir / path) != entry['sha256'])]
    missing = [path for path in frozen if path not in sizes]
    added = [path for path in sizes if path not in frozen]
    present = run_names(data_dir)
    expected = {*record['runs'], *named}
    prefix = BUNDLES.as_posix()
    missing += [f'{prefix}/{name}' for name in expected if name not in present]
    added += [f'{prefix}/{name}' for name in present
              if name not in expected or name.endswith('.part')]
    facts = manifest_facts(data_dir)
    kept = record['manifest']
    manifest_equal = facts is not None and (facts['sha256'], facts['size']) == (
        kept['sha256'], kept['size'])
    clean = manifest_equal and not (changed or missing or added)
    return {'status': 'preserved' if clean else 'changed', 'changed': sorted(changed),
            'missing': sorted(missing), 'added': sorted(added),
            'manifest_equal': manifest_equal, 'runs': present}


# A subcommand's name, the `check` it reports and its function.
COMMANDS = {'reconcile': ('persons', reconcile)}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = result.add_subparsers(dest='command', required=True)
    for name, (_check, function) in COMMANDS.items():
        command = commands.add_parser(name, help=function.__doc__.splitlines()[0])
        command.add_argument('--data-dir', type=Path, required=True)
        command.add_argument('--run', required=True)
        command.add_argument('--outputs-sha256', required=True)
    for function in (freeze, preservation):
        command = commands.add_parser(function.__name__, help=function.__doc__.splitlines()[0])
        command.add_argument('--data-dir', type=Path, required=True)
        command.add_argument('--control-dir', type=Path, required=True)
        if function is preservation:
            command.add_argument('--freeze-sha256', required=True)
            command.add_argument('--runs', required=True)
    return result


def control_main(arguments: argparse.Namespace) -> int:
    '''Run `freeze` or `preservation`. Print its line and return 0 unless it refused or changed.'''
    name = arguments.command
    try:
        if name == 'freeze':
            result = freeze(arguments.data_dir, arguments.control_dir)
        else:
            result = preservation(arguments.data_dir, arguments.control_dir,
                                  arguments.freeze_sha256, arguments.runs)
    except Refused as refusal:
        result = {'check': name, 'reason': str(refusal), 'status': 'refused'}
    except Exception:
        # An exception's text may name a path, so only a fixed reason is printed.
        result = {'check': name, 'reason': f'{name} failed', 'status': 'refused'}
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get('status', 'preserved') == 'preserved' else 1


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.command not in COMMANDS:
        return control_main(arguments)
    check, function = COMMANDS[arguments.command]
    result = {'check': check, 'run': arguments.run}
    try:
        result.update(function(arguments.data_dir, arguments.run, arguments.outputs_sha256))
    except Refused as refusal:
        result.update(equal=False, reason=str(refusal))
    except Exception:
        # An exception's text may hold a person value, so only a fixed reason is printed.
        result.update(equal=False, reason='reconciliation failed')
    print(json.dumps(result, sort_keys=True))
    return 0 if result['equal'] is True else 1


if __name__ == '__main__':
    sys.exit(main())
