'''Publish, verify and compare immutable ACS wage microdata bundles.

A bundle holds `acs_wage_persons.parquet`, `inputs.json` (selection and provenance),
`report.json` (aggregate counts only) and the detached inventory `outputs.json`. `build`
stages into `<RUN_ID>.part`, streams the person rows from the pinned Stage 8 core table into
that directory, checks the staged table, rechecks its pinned inputs and its software just
before publication and only then renames the staging directory. A failure removes only that
staging directory.

`verify_bundle` authenticates the detached pin, the file set and the inventory before it reads
anything else, then recomputes the table offline and compares it in order, one batch per side.
`compare_runs` checks two published bundles for exact logical replay. It does not establish
trust.
'''

import json
import re
import shutil
import subprocess
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from embedding_data import (
    acs_wage_checks,
    acs_wage_inputs,
    acs_wage_rules,
    geography_references,
    manifest,
    paths,
    target_io,
)
from embedding_data.acs_wage_rules import CONTRACT, NEW, OUTPUT_COLUMNS, RULES, TABLE

PERSONS_FILE = TABLE + '.parquet'
FILES = (PERSONS_FILE, 'inputs.json', 'report.json')
INPUT_FIELDS = frozenset({'run_id', 'contract', 'mapping', 'codes', 'ddi', 'labels', 'rules',
                          'software', 'execution'})
RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')
PIN = re.compile(r'[0-9a-f]{64}')


def run_directory(data_dir: Path, run_id: str) -> Path:
    '''The published directory of one run: `derived/acs/wage-microdata/<run_id>`.'''
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError('unsafe run ID')
    return paths.derived_dir(Path(data_dir), 'acs') / 'wage-microdata' / run_id


def _batches(frame: pl.LazyFrame, chunk_size: int) -> Iterator[pl.DataFrame]:
    for batch in frame.collect_batches(chunk_size=chunk_size, maintain_order=True, lazy=True,
                                       engine='streaming'):
        if batch.height:
            yield batch


def ordered_compare(first: pl.LazyFrame, second: pl.LazyFrame, *,
                    chunk_size: int = 65536) -> dict:
    '''Compare ordered schemas and every value in row order, holding one batch per side.

    Both sides are drained, so the row counts are complete even when the schemas differ.
    `DataFrame.equals` counts a null against a value as a difference.
    '''
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError('chunk_size must be a positive integer')
    schema_equal = list(first.collect_schema().items()) == list(second.collect_schema().items())
    left_batches, right_batches = _batches(first, chunk_size), _batches(second, chunk_size)
    if not schema_equal:
        return {
            'schema_equal': False, 'values_equal': False,
            'first_rows': sum(batch.height for batch in left_batches),
            'second_rows': sum(batch.height for batch in right_batches),
        }
    left, right = next(left_batches, None), next(right_batches, None)
    first_rows = second_rows = left_offset = right_offset = 0
    values_equal = True
    while left is not None or right is not None:
        if left is None:
            values_equal = False
            second_rows += right.height - right_offset
            right, right_offset = next(right_batches, None), 0
        elif right is None:
            values_equal = False
            first_rows += left.height - left_offset
            left, left_offset = next(left_batches, None), 0
        else:
            count = min(left.height - left_offset, right.height - right_offset)
            if not left.slice(left_offset, count).equals(right.slice(right_offset, count)):
                values_equal = False
            first_rows += count
            second_rows += count
            left_offset += count
            right_offset += count
            if left_offset == left.height:
                left, left_offset = next(left_batches, None), 0
            if right_offset == right.height:
                right, right_offset = next(right_batches, None), 0
    return {'schema_equal': True, 'values_equal': values_equal, 'first_rows': first_rows,
            'second_rows': second_rows}


def _same(comparison: dict) -> bool:
    return (comparison['schema_equal'] and comparison['values_equal']
            and comparison['first_rows'] == comparison['second_rows'])


def _normalized(value: object) -> object:
    '''The value as JSON reads it back: tuples become lists and keys become strings.'''
    return json.loads(json.dumps(value, allow_nan=False))


def _git(*args: str) -> str:
    return subprocess.run(['git', *args], cwd=paths.PROJECT_ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def _execution() -> dict:
    return {
        'commit': _git('rev-parse', 'HEAD'),
        'dirty': bool(_git('status', '--porcelain', '--untracked-files=normal')),
        'created_at': datetime.now(UTC).isoformat(),
    }


def _inputs(run_id: str, selected: acs_wage_inputs.SelectedWageInputs, software: dict,
            execution: dict) -> dict:
    '''The provenance record of one build, in the form JSON reads it back.'''
    provenance = selected.provenance
    return _normalized({
        'run_id': run_id,
        'contract': CONTRACT,
        'mapping': provenance['mapping'],
        'codes': provenance['codes'],
        'ddi': provenance['ddi'],
        'labels': selected.labels,
        'rules': RULES,
        'software': software,
        'execution': execution,
    })


def _check_persons(table: Path, selected: acs_wage_inputs.SelectedWageInputs,
                   label: str) -> None:
    '''Check a written person table against the contract, the core earners and the rules.

    Every check is a lazy aggregate over the file, so no person rows are held at once.
    `label` names the table in the fixed refusal message.
    '''
    persons = pl.scan_parquet(table)
    core = pl.scan_parquet(selected.core)
    carried = core.collect_schema()
    expected = [(name, NEW[name] if name in NEW else carried.get(name))
                for name in OUTPUT_COLUMNS]
    if list(persons.collect_schema().items()) != expected:
        raise ValueError(f'{label} schema differs from the contract')
    source = pl.col('source_row')
    disordered, rows, earners = pl.collect_all([
        persons.select((source <= source.shift(1)).any().alias('disordered')),
        persons.select(pl.len()),
        core.filter(pl.col('INCWAGE') > 0).select(pl.len()),
    ])
    if disordered.item() or rows.item() != earners.item():
        raise ValueError(f'{label} rows differ from the earners')
    acs_wage_checks.check_headline(persons)
    acs_wage_checks.check_nodes(persons, pl.read_parquet(selected.naics_nodes),
                                pl.read_parquet(selected.naics_edges))


def build(data_dir: Path, run_id: str, *, mapping_run: str, mapping_outputs_sha256: str,
          codes_run: str, codes_outputs_sha256: str) -> dict:
    '''Build, check and publish one immutable bundle under `run_directory(data_dir, run_id)`.

    An existing final or `.part` name fails before anything is written.
    '''
    data_dir = Path(data_dir)
    final, staging = target_io.stage(run_directory(data_dir, run_id).parent, run_id, data_dir)
    try:
        software = acs_wage_inputs.freeze_software()
        selected = acs_wage_inputs.select_wage_inputs(
            data_dir, mapping_run, mapping_outputs_sha256=mapping_outputs_sha256,
            codes_run=codes_run, codes_outputs_sha256=codes_outputs_sha256)
        table = staging / PERSONS_FILE
        acs_wage_rules.wage_persons(pl.scan_parquet(selected.core)).sink_parquet(table)
        _check_persons(table, selected, 'staged')
        report = _normalized(acs_wage_rules.summarize(pl.scan_parquet(table)))
        target_io.write_json(staging / 'report.json', report)
        target_io.write_json(staging / 'inputs.json',
                             _inputs(run_id, selected, software, _execution()))
        selected.verify()
        if acs_wage_inputs.freeze_software() != software:
            raise ValueError('executing software changed before publication')
        target_io.write_json(staging / 'outputs.json', target_io.inventory(staging, list(FILES)))
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


def _recorded_runs(inputs: dict, directory: Path) -> tuple[str, str, str, str]:
    '''The mapping and codes runs and pins that `inputs.json` records.'''
    if set(inputs) != INPUT_FIELDS:
        raise ValueError('recorded inputs are malformed')
    if inputs['run_id'] != directory.name:
        raise ValueError('recorded run ID differs from the directory')
    if inputs['contract'] != CONTRACT:
        raise ValueError('recorded contract differs')
    try:
        mapping, codes = inputs['mapping'], inputs['codes']
        return (mapping['run_id'], mapping['outputs_sha256'], codes['run_id'],
                codes['outputs_sha256'])
    except (KeyError, TypeError):
        raise ValueError('recorded inputs are malformed') from None


def verify_bundle(directory: Path, data_dir: Path, *, expected_outputs_sha256: str) -> dict:
    '''Authenticate a published bundle by its detached pin, then recompute it offline.

    The pin, the exact file set and the inventory are checked before any other file is read.
    Recorded software must equal the executing software. The table is recomputed from the
    recorded Stage 8 and Stage 4 runs and compared in order, the build's checks run on the
    published table, and the report and the inputs (with their recorded execution) must
    equal the recomputed ones.
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
    outputs = acs_wage_inputs.read_json(outputs_file)
    target_io.verify_inventory(directory, outputs, set(FILES))
    if outputs != target_io.inventory(directory, list(FILES)):
        raise ValueError('output inventory records differ')

    inputs = acs_wage_inputs.read_json(directory / 'inputs.json')
    mapping_run, mapping_pin, codes_run, codes_pin = _recorded_runs(inputs, directory)
    selected = acs_wage_inputs.select_wage_inputs(
        data_dir, mapping_run, mapping_outputs_sha256=mapping_pin, codes_run=codes_run,
        codes_outputs_sha256=codes_pin)
    software = acs_wage_inputs.freeze_software()
    if inputs['software'] != _normalized(software):
        raise ValueError('executing software differs from the build')

    table = directory / PERSONS_FILE
    recomputed = acs_wage_rules.wage_persons(pl.scan_parquet(selected.core))
    if not _same(ordered_compare(pl.scan_parquet(table), recomputed)):
        raise ValueError(f'{TABLE}: published table differs from the recomputation')
    _check_persons(table, selected, 'published')
    report = acs_wage_inputs.read_json(directory / 'report.json')
    if report != _normalized(acs_wage_rules.summarize(pl.scan_parquet(table))):
        raise ValueError('published report differs from the recomputation')
    if _inputs(directory.name, selected, software, inputs['execution']) != inputs:
        raise ValueError('recorded inputs differ from the recomputation')
    return {
        'run_id': directory.name,
        'outputs_sha256': expected_outputs_sha256,
        'mapping_run': mapping_run,
        'codes_run': codes_run,
        'rows': report['rows']['total'],
        'headline_rows': report['flags']['flag_headline']['total'],
    }


def compare_runs(first: Path, second: Path) -> dict:
    '''Compare two published bundles: the table in order, one batch per side, and the reports.

    Each bundle must match its own `outputs.json` inventory. Equality establishes replay, not
    trust: neither bundle is authenticated by a detached pin here.
    '''
    first, second = Path(first), Path(second)
    for directory in (first, second):
        if directory.name.endswith('.part') or not directory.is_dir():
            raise ValueError('compared bundles must be published')
        outputs = acs_wage_inputs.read_json(target_io.relative_file(directory, 'outputs.json'))
        target_io.verify_inventory(directory, outputs, set(FILES))
    table = ordered_compare(pl.scan_parquet(first / PERSONS_FILE),
                            pl.scan_parquet(second / PERSONS_FILE))
    report_equal = (acs_wage_inputs.read_json(first / 'report.json')
                    == acs_wage_inputs.read_json(second / 'report.json'))
    return {
        'equal': report_equal and _same(table),
        'table': table,
        'report_equal': report_equal,
        'trust_established': False,
    }
