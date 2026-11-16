'''Independent Stage 10 cross-checks over one published ITA establishment-target bundle.

`co-ownership` recounts N, n(a) and J(a,b) from the selected canonical table with plain
Python sets. Its EIN normalization and its eligibility rule are written here from the spec
text, and it imports none of the Stage 10 modules that build the bundle. `stage3` reruns
the frozen Stage 3 reports on the Stage 2 summary and compares their integer V1 and V2
counts with `report.json`.

Each subcommand takes `--data-dir`, `--run` and `--outputs-sha256`. It checks the detached
`outputs.json` pin first. Then each file it reads must match its record in that inventory
or in `inputs.json`. It prints one sorted JSON line of counts and booleans, never an EIN,
and returns 0 when everything is equal and 1 otherwise.
'''

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Iterable, Iterator
from pathlib import Path

import polars as pl

from embedding_data import ita_references, ita_verification
from embedding_data.ita_establishment_expected import V1_COLUMNS, V2_COLUMNS, YEAR_PAIRS

BUNDLES = Path('derived/osha/establishment-targets')
COLUMNS = (
    'year_filing_for', 'ein', 'naics_mapping_status', 'naics_2022_node_id',
    'flag_naics_crosswalked', 'flag_naics_ambiguous', 'flag_naics_unresolved',
)
YEARS = frozenset({2023, 2024, 2025})
NATIVE = 'native_2022'
EIN_DIGITS = re.compile('[0-9]{8,9}')


class Refused(Exception):
    '''An input that the pin does not authenticate. The message is a fixed reason.'''


def normalize_ein(value: str | None) -> tuple[str, bool] | None:
    '''The nine-digit EIN key and whether it was zero-padded, or None when it is unusable.

    Strip the value, remove its hyphens and require eight or nine ASCII digits. Zero-fill
    the digits to nine. A key of one repeated digit is unusable. Eight digits mean padded.
    '''
    if value is None:
        return None
    digits = value.strip().replace('-', '')
    if not EIN_DIGITS.fullmatch(digits):
        return None
    key = digits.zfill(9)
    if len(set(key)) == 1:
        return None
    return key, len(digits) == 8


def eligible_employer(row: tuple) -> str | None:
    '''The usable unpadded EIN of an eligible record, else None. `row` is in `COLUMNS` order.

    An eligible record files for 2023, 2024 or 2025, has the status `native_2022` and a 2022
    node, has the crosswalked, ambiguous and unresolved flags all false (a null flag is not
    false) and has a usable EIN that was not zero-padded.
    '''
    year, ein, status, node, *flags = row
    if year not in YEARS or status != NATIVE or node is None:
        return None
    if any(flag is not False for flag in flags):
        return None
    normalized = normalize_ein(ein)
    if normalized is None or normalized[1]:
        return None
    return normalized[0]


def count(rows: Iterable[tuple]) -> tuple[int, dict[str, int], dict[tuple[str, str], int]]:
    '''N, n(a) and J(a,b) for a != b, counting each EIN at most once in each.

    S(e,t) is the set of nodes on the eligible records of EIN e in year t. n(a) counts the
    EINs with a in some S(e,t). J(a,b) counts the EINs with a and b in one S(e,t).
    '''
    industries: dict[str, dict[int, set[str]]] = {}
    for row in rows:
        employer = eligible_employer(row)
        if employer is not None:
            year, _ein, _status, node, *_flags = row
            industries.setdefault(employer, {}).setdefault(year, set()).add(node)
    marginals = Counter()
    cells = Counter()
    for years in industries.values():
        marginals.update(set().union(*years.values()))
        cells.update({(a, b) for nodes in years.values() for a in nodes for b in nodes
                      if a != b})
    return len(industries), dict(marginals), dict(cells)


def read_canonical(file: Path) -> Iterator[tuple]:
    '''The canonical rows as plain tuples in `COLUMNS` order.'''
    return pl.read_parquet(file, columns=list(COLUMNS)).iter_rows()


def sha256(file: Path) -> str:
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def open_bundle(data_dir: Path, run_id: str, pin: str) -> tuple[Path, dict]:
    '''The bundle directory and its inventory, once `outputs.json` matches the pin.'''
    directory = data_dir / BUNDLES / run_id
    outputs = directory / 'outputs.json'
    if not outputs.is_file() or sha256(outputs) != pin:
        raise Refused('detached pin differs')
    return directory, json.loads(outputs.read_text())


def bundle_file(directory: Path, inventory: dict, name: str) -> Path:
    '''One bundle file, once its bytes match its record in the pinned inventory.'''
    file = directory / name
    record = inventory.get(name)
    expected = record.get('sha256') if isinstance(record, dict) else None
    if not file.is_file() or sha256(file) != expected:
        raise Refused('bundle file differs from its inventory')
    return file


def bundle_json(directory: Path, inventory: dict, name: str) -> dict:
    return json.loads(bundle_file(directory, inventory, name).read_text())


def selected_table(data_dir: Path, record: dict) -> Path:
    '''A table that `inputs.json` selects, once its bytes match the recorded hash.'''
    file = data_dir / record['path']
    if not file.is_file() or sha256(file) != record['sha256']:
        raise Refused('selected table differs from inputs.json')
    return file


def differing(first: dict, second: dict) -> int:
    '''The number of keys that one side lacks or that hold different counts.'''
    return sum(first.get(key) != second.get(key) for key in first.keys() | second.keys())


def co_ownership(data_dir: Path, run_id: str, pin: str) -> dict:
    '''Recount N, n(a) and J(a,b) from the canonical table and compare them with the bundle.'''
    directory, inventory = open_bundle(data_dir, run_id, pin)
    inputs = bundle_json(directory, inventory, 'inputs.json')
    report = bundle_json(directory, inventory, 'report.json')
    targets = pl.read_parquet(bundle_file(directory, inventory, 'ita_co_ownership.parquet'),
                              columns=['unit_a', 'unit_b', 'n_unweighted'])
    marginals = pl.read_parquet(
        bundle_file(directory, inventory, 'co_ownership_marginals.parquet'),
        columns=['node_id', 'n_employers'])
    canonical = selected_table(data_dir, inputs['canonical'])
    employers, industries, cells = count(read_canonical(canonical))
    bundle_n = report['co_ownership']['N']
    bundle_industries = {node: n for node, n in marginals.iter_rows()}
    bundle_cells = {(a, b): n for a, b, n in targets.iter_rows()}
    marginals_differing = differing(industries, bundle_industries)
    cells_differing = differing(cells, bundle_cells)
    checks = {
        'N_equal': employers == bundle_n,
        'marginals_equal': marginals_differing == 0,
        'cells_equal': cells_differing == 0,
    }
    return {
        **checks,
        'equal': all(checks.values()),
        'N': {'bundle': bundle_n, 'independent': employers},
        'n_industries': {'bundle': len(bundle_industries), 'independent': len(industries)},
        'n_cells': {'bundle': len(bundle_cells), 'independent': len(cells)},
        'marginals_differing': marginals_differing,
        'cells_differing': cells_differing,
    }


def integer(value: object) -> int | None:
    return None if value is None else int(value)


def stage3(data_dir: Path, run_id: str, pin: str) -> dict:
    '''Rerun the Stage 3 V1 and V2 reports and compare their integer counts with the bundle.'''
    directory, inventory = open_bundle(data_dir, run_id, pin)
    inputs = bundle_json(directory, inventory, 'inputs.json')
    report = bundle_json(directory, inventory, 'report.json')
    summary = pl.scan_parquet(selected_table(data_dir, inputs['source_parquet']))
    measured = ita_verification.description_report(summary, ita_references.read_titles(data_dir))
    v1 = {row['year_filing_for']: row for row in measured.iter_rows(named=True)}
    recorded_v1 = {row['year_filing_for']: row for row in report['v1_by_year']}
    v1_differences = [
        [year, column]
        for year in sorted(v1.keys() | recorded_v1.keys())
        for column in V1_COLUMNS
        if integer(v1.get(year, {}).get(column)) != recorded_v1.get(year, {}).get(column)
    ]
    v2_differences = []
    for base, later in YEAR_PAIRS:
        name = f'{base}-{later}'
        counts = ita_verification.link_report(summary, base, later)
        recorded = report['links']['pairs'].get(name, {}).get('v2', {})
        v2_differences += [[name, column] for column in V2_COLUMNS
                           if integer(counts.get(column)) != recorded.get(column)]
    return {
        'equal': not v1_differences and not v2_differences,
        'v1_equal': not v1_differences,
        'v2_equal': not v2_differences,
        'v1_differences': v1_differences,
        'v2_differences': v2_differences,
    }


CHECKS = {'co-ownership': co_ownership, 'stage3': stage3}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = result.add_subparsers(dest='check', required=True)
    for name, check in CHECKS.items():
        command = commands.add_parser(name, help=check.__doc__.splitlines()[0])
        command.add_argument('--data-dir', type=Path, required=True)
        command.add_argument('--run', required=True)
        command.add_argument('--outputs-sha256', required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    result = {'check': arguments.check, 'run': arguments.run}
    try:
        result.update(CHECKS[arguments.check](arguments.data_dir, arguments.run,
                                              arguments.outputs_sha256))
    except Refused as refusal:
        result.update(equal=False, reason=str(refusal))
    print(json.dumps(result, sort_keys=True))
    return 0 if result['equal'] is True else 1


if __name__ == '__main__':
    sys.exit(main())
