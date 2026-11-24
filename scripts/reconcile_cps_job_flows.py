'''Independent reconciliation of one published CPS job-flow bundle with its upstream files.

Written from the Stage 11 spec (`specs/cps-job-change-flows.md`) and the plan's Schemas and
Settled Defaults (`specs/plans/23-cps-job-change-flows.md`), not from the build modules, and
importing none of them: only the standard library, Polars and fastexcel. After the detached
`outputs.json` pin and the bundle inventory pass, it takes from `inputs.json` only where each
upstream file lives and the hash recorded for it, and checks every file it reads against that
hash. It reads the two CPS Parquets, the literal weights of their raw CSV files with
`decimal.Decimal` (row i of a CSV is row i of its Parquet, proved on every row), the delivered
DDI labels of the quality flags, the two Census list workbooks, the Stage 4 SOC nodes and paths,
and the Stage 8 PUMS member lists. With its own statement of the spec's rules it recomputes:

- `value_classes`: the class of every delivered code, the specials by year, the registry rows;
- `x_residuals`: the SOC candidates of every occupation row, the X residuals, their cross-check;
- `links`: the one-month and two-month links with their codes, flags and weights, and the link
  and weight counts;
- `guards`: both dimensions' guard of every link, the guard counts, the usable-guard shares;
- `eligibility`: the first-exclusion funnels and each link's product membership;
- `targets`: every `average_total` and `forward_share` value, `n_unweighted`, `n_weighted` and
  the support rows, from exact Decimal sums with `float(S) / k`;
- `asec_se`: the replicate SE of every ASEC row, its replicate rows and undefined-share rows.

It never recomputes a bootstrap SE, which shares the build's algorithm.

    python scripts/reconcile_cps_job_flows.py --data-dir ROOT --run RUN_ID --outputs-sha256 PIN

It prints one sorted JSON line, `{"checks": {...}, "equal": ...}`, of booleans only, and returns
0 when every check is equal and 1 when one differs. A refusal (a wrong pin, a missing run, an
unsafe path, or an input that is missing, differs from its record or cannot be read) prints one
fixed reason line to stderr, never row content, and returns 2.
'''

import argparse
import csv
import gzip
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import (
    Context,
    Decimal,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    Overflow,
    localcontext,
)
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

import fastexcel
import polars as pl

BUNDLES = Path('derived/cps/job-flows')
CODES = Path('derived/codes')
MAPPING = Path('derived/acs/mapping')
RAW = Path('raw')
RUN_ID = re.compile('[A-Za-z0-9][A-Za-z0-9_-]*')
PIN = re.compile('[0-9a-f]{64}')
TABLES = ('cps_job_flows', 'cps_category_units', 'cps_flow_support', 'cps_flow_replicates',
          'cps_flow_diagnostics', 'cps_linked_pairs')
INVENTORY = frozenset({*(name + '.parquet' for name in TABLES), 'inputs.json', 'report.json'})
CHECKS = ('value_classes', 'x_residuals', 'links', 'guards', 'eligibility', 'targets', 'asec_se')
FAILURE = 'CPS job flows reconcile failed: '
# Sums of literal weights must be exact: any rounding raises.
EXACT = Context(prec=400, traps=[Inexact, InvalidOperation, Overflow, DivisionByZero])
CHUNK = 65536

# Spec "Code mapping": value classes, specials and unit identity.
DIMENSIONS = ('industry', 'occupation')
NOT_IN_UNIVERSE = '0000'
SPECIAL = {'industry': '9890', 'occupation': '9840'}
SPECIAL_LABEL = 'Armed Forces'
UNIT_TYPE = {'industry': 'cps_industry_category', 'occupation': 'cps_occupation_category'}
VINTAGE = {'industry': 'census-industry-2022', 'occupation': 'census-occupation-2018'}
FIELDS = {'monthly': {'IND': 'industry', 'OCC': 'occupation'},
          'asec': {'IND': 'industry', 'OCC': 'occupation', 'INDLY': 'industry',
                   'OCCLY': 'occupation'}}
CLASSES = ('mapped', 'not_in_universe', 'special')
V11 = {'statement': 'zero unparseable CPS values', 'unparseable_values': 0}
CROSS_CHECKS = ('equal', 'strict_subset', 'not_delivered_no_pums_list')

# Plan Global Constraints: the list workbooks. A row is data when its code cell, stripped, is
# four digits. Industry: B title, D code, E NAICS expression. Occupation: B title, C code, D
# SOC token, where `none` means no SOC equivalent and an X stands for any digit.
INDUSTRY_SHEET = '2022 Census Ind Code List '
OCCUPATION_SHEET = '2018 Census Occ Code List'
CODE = re.compile(r'\d{4}')
NO_SOC = 'none'

# Spec "Linkage": one-month links join calendar months m and m + 1, with MISH rising by one
# and the earlier MISH not 4 or 8. The only two-month link runs from September to November
# 2025, with MISH rising by two. A month is YEAR * 12 + MONTH - 1.
TWO_MONTH_FROM = 2025 * 12 + 9 - 1
ONE_MONTH_RULE = (pl.col('MISH_b') == pl.col('MISH_a') + 1) & ~pl.col('MISH_a').is_in([4, 8])
TWO_MONTH_RULE = pl.col('MISH_b') == pl.col('MISH_a') + 2
LINK_TYPES = ('one_month', 'two_month')

# Spec "Products" and the plan's SD3: EMPSTAT codes and the first-exclusion funnels.
EMPLOYED = [10, 12]
UNEMPLOYED_WITH_LAST_JOB, NEW_WORKER = 21, 22
MONTHLY_PRODUCTS = ('monthly_ee', 'monthly_ue')
FUNNELS = {
    'monthly_ee': ('weight_null', 'weight_zero', 'not_employed_both', 'code_not_in_universe',
                   'guard_unusable', 'no_change_reported', 'coding_noise', 'eligible'),
    'monthly_ue': ('weight_null', 'weight_zero', 'origin_new_worker_22',
                   'origin_not_unemployed_21', 'destination_not_employed',
                   'code_not_in_universe', 'eligible'),
    'asec_retro': ('weight_nonpositive', 'not_employed', 'last_year_code_not_in_universe',
                   'current_code_not_in_universe', 'same_category', 'eligible'),
}
POLICIES = {'monthly_ee': ('sensitivity', 'strict'), 'monthly_ue': ('sensitivity', 'strict'),
            'asec_retro': ('sensitivity',)}
GUARD_STATES = ('changed', 'same', 'unusable')
WEIGHT_STATUSES = ('null', 'zero', 'positive')
# Spec "Evidence policies": a flag shows nonallocation when its delivered DDI label is this one.
NONALLOCATION = 'No change or children or armed forces'
FLAG_VARIABLES = ('QEMPSTAT', 'QIND', 'QOCC')
DIMENSION_FLAG = {'industry': 'qind', 'occupation': 'qocc'}
DIMENSION_CODE = {'industry': 'ind', 'occupation': 'occ'}
LAST_YEAR = {'industry': 'INDLY', 'occupation': 'OCCLY'}
CURRENT = {'industry': 'IND', 'occupation': 'OCC'}

# Spec "Estimation": k is 18 one-month link months for monthly products and 2 for the ASEC.
LINK_MONTHS = tuple(
    f'{year}-{month:02d}>{year + month // 12}-{month % 12 + 1:02d}'
    for year, month in [*((2025, month) for month in range(1, 9)), (2025, 11), (2025, 12),
                        *((2026, month) for month in range(1, 9))])
MONTHLY_K = len(LINK_MONTHS)
ASEC_K = 2
REPLICATES = 160
K = {'monthly_ee': MONTHLY_K, 'monthly_ue': MONTHLY_K, 'asec_retro': ASEC_K}

# Spec "Target metadata" and the plan's verbatim strings.
SOURCE, FAMILY = 'cps', 'job_change_flow'
SAMPLE_SET = {'monthly_ee': 'cps-basic-2025-01-to-2026-09',
              'monthly_ue': 'cps-basic-2025-01-to-2026-09', 'asec_retro': 'cps-asec-2025-2026'}
PRODUCT_FLAG = {'monthly_ee': 'bootstrap_approximate', 'monthly_ue': 'bootstrap_approximate',
                'asec_retro': 'unguarded_upper_bound'}
SIZE_GATE, SPECIAL_FLAG = 'size_gate_pending', 'special_military'
TARGET_FIELDS = ('source', 'family', 'unit_a_type', 'unit_b_type', 'value', 'n_unweighted',
                 'n_weighted', 'sample_set', 'vintage', 'flags')

# The plan's Schemas for the linked pairs and the ASEC replicate rows.
LINKED_PAIRS_SCHEMA = {
    'CPSIDV': pl.Int64, 'CPSID': pl.Int64, 'month_a': pl.String, 'month_b': pl.String,
    'link_type': pl.String, 'source_row_a': pl.UInt64, 'source_row_b': pl.UInt64,
    'mish_a': pl.Int64, 'mish_b': pl.Int64, 'empstat_a': pl.Int64, 'empstat_b': pl.Int64,
    'ind_a': pl.String, 'ind_b': pl.String, 'occ_a': pl.String, 'occ_b': pl.String,
    'qempstat_a': pl.Int64, 'qempstat_b': pl.Int64, 'qind_a': pl.Int64, 'qind_b': pl.Int64,
    'qocc_a': pl.Int64, 'qocc_b': pl.Int64, 'empsame_b': pl.Int64, 'actsame_b': pl.Int64,
    'guard_industry': pl.String, 'guard_occupation': pl.String, 'weight_a': pl.Float64,
    'weight_status': pl.String, 'products': pl.List(pl.String)}
GUARD_COLUMNS = ('guard_industry', 'guard_occupation')
PRODUCT_COLUMNS = ('products',)
LINK_COLUMNS = tuple(name for name in LINKED_PAIRS_SCHEMA
                     if name not in GUARD_COLUMNS + PRODUCT_COLUMNS)
REPLICATE_SCHEMA = {'policy': pl.String, 'unit_a': pl.String, 'unit_b': pl.String,
                    'replicate': pl.UInt16, 'numerator': pl.Float64, 'denominator': pl.Float64,
                    'estimate': pl.Float64, 'status': pl.String}

# The monthly Parquet columns that the links read, and the CSV columns that prove alignment.
PANEL_COLUMNS = ('YEAR', 'MONTH', 'MISH', 'CPSID', 'CPSIDP', 'CPSIDV', 'EMPSTAT', 'IND', 'OCC',
                 'QEMPSTAT', 'QIND', 'QOCC', 'EMPSAME', 'ACTSAME')
LINK_SIDE = ('source_row', 'label', 'CPSID', 'MISH', 'EMPSTAT', 'IND', 'OCC', 'QEMPSTAT', 'QIND',
             'QOCC', 'EMPSAME', 'ACTSAME')
ALIGNMENT = {'monthly': ('YEAR', 'MONTH', 'SERIAL', 'PERNUM', 'MISH', 'CPSIDV'),
             'asec': ('YEAR', 'SERIAL', 'PERNUM', 'CPSIDV')}
WEIGHT = {'monthly': 'LNKFW1MWT', 'asec': 'ASECWT'}
# Guard source exceptions: EMPSAME is not in universe in MISH 1 and 5, so a delivered substantive
# answer there is counted (spec, Guard; controller ruling 2026-11-24: rows, values 1 and 2).
SOURCE_EXCEPTION = 'empsame_in_mish_1_or_5'
SOURCE_EXCEPTION_MISH = (1, 5)
SUBSTANTIVE_EMPSAME = (1, 2)


class Refused(Exception):
    '''An input that cannot be trusted or read. The message is a fixed reason, never data.'''


# Inputs.

def sha256(file: Path) -> str:
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(file: Path) -> dict:
    try:
        value = json.loads(file.read_bytes())
    except (OSError, ValueError):
        raise Refused('json file is unreadable') from None
    if not isinstance(value, dict):
        raise Refused('json file is not an object')
    return value


def matching_file(file: Path, record: object) -> bool:
    '''Whether `file` is a regular file, not a link, whose size and SHA-256 match `record`.'''
    if not isinstance(record, dict) or file.is_symlink() or not file.is_file():
        return False
    return record.get('size') == file.stat().st_size and record.get('sha256') == sha256(file)


def open_bundle(data_dir: Path, run_id: str, pin: str) -> Path:
    '''The bundle directory, once `outputs.json` matches the pin and every file its record.'''
    if not data_dir.is_dir():
        raise Refused('data directory is missing')
    if not RUN_ID.fullmatch(run_id):
        raise Refused('unsafe run id')
    if not PIN.fullmatch(pin):
        raise Refused('malformed pin')
    directory = data_dir / BUNDLES / run_id
    outputs = directory / 'outputs.json'
    if directory.is_symlink() or outputs.is_symlink() or not outputs.is_file():
        raise Refused('bundle is missing')
    if sha256(outputs) != pin:
        raise Refused('detached pin differs')
    inventory = read_json(outputs)
    if set(inventory) != INVENTORY:
        raise Refused('bundle inventory differs')
    for name in sorted(INVENTORY):
        if not matching_file(directory / name, inventory[name]):
            raise Refused('bundle file differs from its inventory')
    return directory


def under(root: Path, text: object) -> Path:
    '''`text`, a relative POSIX path with no `..`, joined to `root`.'''
    if not isinstance(text, str):
        raise Refused('inputs.json is malformed')
    relative = PurePosixPath(text)
    if relative.is_absolute() or not relative.parts or '..' in relative.parts:
        raise Refused('upstream path is unsafe')
    return root.joinpath(*relative.parts)


def cited(data_dir: Path, citation: object) -> Path:
    '''The raw file of a manifest citation, once its size and SHA-256 match the citation.'''
    if not isinstance(citation, dict):
        raise Refused('inputs.json is malformed')
    file = under(data_dir / RAW, citation.get('path'))
    if not matching_file(file, citation):
        raise Refused('upstream file differs from its record')
    return file


def run_file(data_dir: Path, root: Path, upstream: dict, name: str) -> Path:
    '''A file of a pinned upstream run, checked against the pin and the run's own inventory.'''
    run_id = upstream.get('run_id')
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise Refused('upstream run id is unsafe')
    directory = data_dir / root / run_id
    outputs = directory / 'outputs.json'
    if outputs.is_symlink() or not outputs.is_file():
        raise Refused('upstream run is missing')
    if sha256(outputs) != upstream.get('outputs_sha256'):
        raise Refused('upstream pin differs')
    if not matching_file(directory / name, read_json(outputs).get(name)):
        raise Refused('upstream file differs from its record')
    return directory / name


@dataclass(frozen=True)
class Delivery:
    name: str
    parquet: Path
    csv_gz: Path
    ddi: Path


@dataclass(frozen=True)
class Upstream:
    monthly: Delivery
    asec: Delivery
    industry_list: Path
    occupation_list: Path
    soc_nodes: Path
    code_paths: Path
    pums_lookup: Path


def delivery(data_dir: Path, name: str, record: dict) -> Delivery:
    parquet = under(data_dir, record['parquet'])
    if not matching_file(parquet, record['parquet_record']):
        raise Refused('delivery parquet differs from its record')
    raw = {suffix: [citation for citation in record['raw_citations']
                    if str(citation['path']).endswith(suffix)] for suffix in ('.csv.gz', '.xml')}
    if any(len(citations) != 1 for citations in raw.values()):
        raise Refused('delivery citations differ')
    return Delivery(name, parquet, cited(data_dir, raw['.csv.gz'][0]),
                    cited(data_dir, raw['.xml'][0]))


def select_upstream(data_dir: Path, inputs: dict) -> Upstream:
    '''The upstream files that `inputs.json` locates, each checked against its record.'''
    try:
        deliveries, upstream = inputs['deliveries'], inputs['upstream']
        return Upstream(
            monthly=delivery(data_dir, 'monthly', deliveries['monthly']),
            asec=delivery(data_dir, 'asec', deliveries['asec']),
            industry_list=cited(data_dir, upstream['stage7_receipt']['originals']
                                ['census_industry_2022']['citation']),
            occupation_list=cited(data_dir, upstream['stage8_receipt']['originals']
                                  ['census_occupation_2018']['citation']),
            soc_nodes=run_file(data_dir, CODES, upstream['codes_run'], 'soc_nodes.parquet'),
            code_paths=run_file(data_dir, CODES, upstream['codes_run'], 'code_paths.parquet'),
            pums_lookup=run_file(data_dir, MAPPING, upstream['stage8_mapping_run'],
                                 'acs_code_lookup.parquet'))
    except (KeyError, TypeError, AttributeError):
        raise Refused('inputs.json is malformed') from None


# Readers.

def local(tag: str) -> str:
    return tag.rpartition('}')[2]


def nonallocation_values(ddi: Path) -> dict[str, list[int]]:
    '''The values of each quality flag whose delivered DDI label is the nonallocation label.'''
    try:
        tree = ElementTree.parse(ddi)
    except (ElementTree.ParseError, OSError):
        raise Refused('ddi is unreadable') from None
    found = {}
    for element in tree.iter():
        name = element.get('name')
        if local(element.tag) != 'var' or name not in FLAG_VARIABLES:
            continue
        values = set()
        for category in element.iter():
            if local(category.tag) != 'catgry':
                continue
            parts = {local(part.tag): (part.text or '').strip() for part in category}
            if parts.get('labl') == NONALLOCATION:
                try:
                    values.add(int(parts.get('catValu', '')))
                except ValueError:
                    raise Refused('ddi category value is not an integer') from None
        found[name] = sorted(values)
    if set(found) != set(FLAG_VARIABLES):
        raise Refused('ddi lacks a flag variable')
    return found


def sheet_rows(file: Path, name: str, width: int) -> list[tuple]:
    '''Every row of one worksheet as strings, read with no header row.'''
    try:
        reader = fastexcel.read_excel(file)
        if name not in reader.sheet_names:
            raise Refused('list workbook sheet is missing')
        frame = reader.load_sheet_by_name(name, header_row=None, dtypes='string').to_polars()
    except Refused:
        raise
    except Exception:
        raise Refused('list workbook is unreadable') from None
    if frame.width < width:
        raise Refused('list workbook layout differs')
    return frame.rows()


def stripped(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def list_rows(file: Path, name: str, width: int, code: int, expression: int) -> list[tuple]:
    '''The (code, expression) of each data row: a row whose stripped code is four digits.'''
    rows = [(stripped(row[code]), stripped(row[expression]))
            for row in sheet_rows(file, name, width)]
    rows = [(value, text) for value, text in rows if value is not None and CODE.fullmatch(value)]
    if not rows:
        raise Refused('list workbook has no codes')
    return rows


def industry_statuses(file: Path) -> dict[str, str]:
    '''Each industry list code: mapped when a row of it gives a NAICS expression.'''
    statuses = {}
    for code, expression in list_rows(file, INDUSTRY_SHEET, 5, 3, 4):
        if expression is not None or code not in statuses:
            statuses[code] = 'mapped' if expression is not None else 'no_naics_equivalent'
    return statuses


def occupation_tokens(file: Path) -> dict[str, str | None]:
    '''Each occupation list code with its SOC token.'''
    tokens = {}
    for code, token in list_rows(file, OCCUPATION_SHEET, 4, 2, 3):
        if tokens.setdefault(code, token) != token:
            raise Refused('occupation list repeats a code')
    return tokens


def occupation_status(token: str | None) -> str:
    return 'no_soc_equivalent' if token == NO_SOC else 'mapped'


@dataclass(frozen=True)
class SocTree:
    descendants: dict[str, set[str]]  # any SOC code -> its detailed codes, by node paths
    node_of: dict[str, str]  # detailed code -> node ID


def soc_tree(soc_nodes: Path, code_paths: Path) -> SocTree:
    nodes = pl.read_parquet(soc_nodes, columns=['node_id', 'level', 'code'])
    code_of = dict(nodes.select('node_id', 'code').iter_rows())
    detailed = dict(nodes.filter(pl.col('level') == 'detailed').select('node_id', 'code')
                    .iter_rows())
    descendants = defaultdict(set)
    paths = pl.read_parquet(code_paths, columns=['node_id', 'path'])
    for node_id, path in paths.filter(pl.col('node_id').is_in(list(detailed))).iter_rows():
        for ancestor in (*(path or ()), node_id):
            if ancestor in code_of:
                descendants[code_of[ancestor]].add(detailed[node_id])
    return SocTree(dict(descendants), {code: node_id for node_id, code in detailed.items()})


def pums_lists(file: Path) -> dict[str, tuple[frozenset[str], str]]:
    '''Each Census occupation code with its PUMS member list and joined locators.'''
    frame = (pl.read_parquet(file, columns=['system', 'paired_census_code',
                                            'canonical_finest_candidates', 'reference_locators'])
             .filter(pl.col('system') == 'soc', pl.col('paired_census_code').is_not_null()))
    lists = {}
    for _, code, members, locators in frame.iter_rows():
        if code in lists:
            raise Refused('pums lists repeat a code')
        lists[code] = (frozenset(members or ()), '|'.join(locators or ()))
    return lists


def decimal_text(text: str) -> Decimal | None:
    '''A literal CSV weight: None when empty, else its exact Decimal.'''
    if text == '':
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise Refused('weight is not a decimal') from None
    if not value.is_finite():
        raise Refused('weight is not a decimal')
    return value


def integer_text(text: str) -> int | None:
    if text == '':
        return None
    try:
        return int(text)
    except ValueError:
        raise Refused('csv value is not an integer') from None


@dataclass
class Weights:
    full: dict[int, Decimal | None] = field(default_factory=dict)
    replicates: dict[int, str] = field(default_factory=dict)


def read_weights(source: Delivery, keep: set[int] | None, replicates: set[int]) -> Weights:
    '''The literal weights of the raw CSV, by row, after proving that it aligns with the Parquet.

    Every CSV row must carry the same alignment keys and the same weight value as the Parquet
    row at its position, and both files the same number of rows. The full weight is kept for
    the rows in `keep` (all rows when None), and the joined replicate weight text for the rows
    in `replicates`.
    '''
    keys, weight = ALIGNMENT[source.name], WEIGHT[source.name]
    columns = pl.scan_parquet(source.parquet).collect_schema().names()
    if not {*keys, weight} <= set(columns):
        raise Refused('parquet lacks an alignment column')
    expected = pl.read_parquet(source.parquet, columns=[*keys, weight])
    result = Weights()
    with gzip.open(source.csv_gz, 'rt', encoding='utf-8', newline='') as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        if header != columns:
            raise Refused('csv header differs from its parquet')
        key_index = [header.index(name) for name in keys]
        weight_index = header.index(weight)
        replicate_index = ([header.index(f'REPWTP{number}') for number in range(1, 161)]
                           if replicates else [])
        start, chunk = 0, {name: [] for name in (*keys, weight)}
        for number, row in enumerate(reader):
            if len(row) != len(header):
                raise Refused('csv row has the wrong field count')
            for name, index in zip(keys, key_index, strict=True):
                chunk[name].append(integer_text(row[index]))
            value = decimal_text(row[weight_index])
            chunk[weight].append(None if value is None else float(value))
            if keep is None or number in keep:
                result.full[number] = value
            if number in replicates:
                result.replicates[number] = ','.join(row[index] for index in replicate_index)
            if len(chunk[weight]) == CHUNK:
                start = check_chunk(expected, start, chunk)
        start = check_chunk(expected, start, chunk)
    if start != expected.height:
        raise Refused('csv rows do not align with the parquet')
    return result


def check_chunk(expected: pl.DataFrame, start: int, chunk: dict[str, list]) -> int:
    count = len(next(iter(chunk.values())))
    part = expected.slice(start, count)
    if part.height != count or any(part[name].to_list() != values
                                   for name, values in chunk.items()):
        raise Refused('csv rows do not align with the parquet')
    for values in chunk.values():
        values.clear()
    return start + count


def replicate_weights(text: str) -> list[Decimal]:
    values = [decimal_text(part) for part in text.split(',')]
    if len(values) != REPLICATES or any(value is None for value in values):
        raise Refused('replicate weight is missing')
    return values


# Comparison helpers.

def plain(value: object) -> object:
    return tuple(map(plain, value)) if isinstance(value, (list, tuple)) else value


def canonical_row(row: Iterable) -> str:
    '''A text that tells 1 from 1.0 and True from 1, so rows compare with their types.'''
    return repr(plain(tuple(row)))


def same_rows(expected: Iterable[Iterable], actual: Iterable[Iterable]) -> bool:
    '''Equal multisets of rows, with types.'''
    return Counter(map(canonical_row, expected)) == Counter(map(canonical_row, actual))


def same_json(first: object, second: object) -> bool:
    return json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def same(first: object, second: object) -> bool:
    return canonical_row([first]) == canonical_row([second])


def columns_equal(expected: pl.DataFrame, actual: pl.DataFrame, columns: Iterable[str]) -> bool:
    '''Equal columns in physical order, with equal types.'''
    columns = list(columns)
    if not set(columns) <= set(actual.columns) or expected.height != actual.height:
        return False
    if [actual.schema[name] for name in columns] != [expected.schema[name] for name in columns]:
        return False
    return expected.select(columns).equals(actual.select(columns))


def diagnostics_rows(diagnostics: pl.DataFrame, topic: str) -> list[tuple]:
    return [row for row in diagnostics.iter_rows() if row[0] == topic]


def diagnostic(topic: str, reason: str, count: int, *, product=None, dimension=None,
               period: str = 'all', exclusive: bool = False, count_cpsidp=None) -> tuple:
    return (topic, product, dimension, None, period, reason, exclusive, count, count_cpsidp)


# Value classes and the registry.

def code_class(code: object, dimension: str, statuses: dict[str, dict[str, str]]) -> str:
    if code == NOT_IN_UNIVERSE:
        return 'not_in_universe'
    if code == SPECIAL[dimension]:
        return 'special'
    if statuses[dimension].get(code) == 'mapped':
        return 'mapped'
    return 'unparseable'


def check_value_classes(frames: dict[str, pl.DataFrame], statuses, report: dict,
                        diagnostics: pl.DataFrame, units: pl.DataFrame) -> bool:
    classes, specials, rows, unparseable = {}, {}, [], 0
    for file, fields in FIELDS.items():
        frame = frames[file]
        for name, dimension in fields.items():
            counts = dict.fromkeys(CLASSES, 0)
            for code, count in frame.group_by(name).len().iter_rows():
                kind = code_class(code, dimension, statuses)
                if kind == 'unparseable':
                    unparseable += count
                else:
                    counts[kind] += count
            classes[f'{file}/{name}'] = counts
            rows += [diagnostic('value_class', f'{file}/{name}/{kind}', count)
                     for kind, count in counts.items()]
            special = frame.filter(pl.col(name) == SPECIAL[dimension]).group_by('YEAR').len()
            for year, count in special.iter_rows():
                specials[f'{file}/{name}/{year}'] = count
    registry = [(f'feature:{UNIT_TYPE[dimension]}:{code}', UNIT_TYPE[dimension], code,
                 VINTAGE[dimension], status)
                for dimension in DIMENSIONS
                for code, status in [*statuses[dimension].items(),
                                     (SPECIAL[dimension], 'special_military')]]
    special_rows = [(UNIT_TYPE[dimension], SPECIAL[dimension], SPECIAL_LABEL, [], [])
                    for dimension in DIMENSIONS]
    return all((
        unparseable == 0,
        same_json(report.get('value_classes'), classes),
        same_json(report.get('specials'), specials),
        same_json(report.get('v11'), {**V11, 'unparseable_values': unparseable}),
        same_rows(rows, diagnostics_rows(diagnostics, 'value_class')),
        same_rows(registry, units.select('unit', 'unit_type', 'code', 'vintage', 'status')
                  .iter_rows()),
        same_rows(special_rows, units.filter(pl.col('status') == 'special_military')
                  .select('unit_type', 'code', 'label', 'candidates', 'membership_types')
                  .iter_rows()),
    ))


# X residuals.

def x_matches(token: str, detailed: Iterable[str]) -> set[str]:
    '''The detailed codes that match the token as written, each X standing for any digit.'''
    return {code for code in detailed if len(code) == len(token) and all(
        mark == digit or (mark == 'X' and digit.isdigit())
        for mark, digit in zip(token, code, strict=True))}


def check_x_residuals(tokens: dict[str, str | None], tree: SocTree, pums: dict,
                      delivered: set[str], report: dict, units: pl.DataFrame) -> bool:
    '''Spec "X occupation categories": the residual rule, the cross-check and the registry.'''
    x_rows = {code: token for code, token in tokens.items() if token and 'X' in token}
    candidates = {code: set() if token in (None, NO_SOC) else set(tree.descendants.get(token, ()))
                  for code, token in tokens.items() if code not in x_rows}
    claimed = set().union(*candidates.values())
    taken = set()
    for code, token in sorted(x_rows.items(), key=lambda item: (
            -sum(mark.isdigit() for mark in item[1]), item[1], item[0])):
        candidates[code] = x_matches(token, tree.node_of) - claimed - taken
        taken |= candidates[code]
    outcomes, expected = {}, []
    for code, token in tokens.items():
        members = sorted(candidates[code])
        if code in x_rows:
            others = set().union(*(value for other, value in candidates.items() if other != code))
            outcomes[code] = cross_check(code, candidates[code], pums.get(code), others,
                                         delivered)
            types = ['x_residual']
        elif token in (None, NO_SOC):
            types = []
        else:
            types = ['whole'] if token in tree.node_of else ['group']
        locator = pums[code][1] if code in x_rows and code in pums else None
        expected.append((code, types, members, [tree.node_of.get(item) for item in members],
                         token if code in x_rows else None, outcomes.get(code), locator))
    expected.append((SPECIAL['occupation'], [], [], [], None, None, None))
    counts = Counter(outcomes.values())
    actual = (units.filter(pl.col('unit_type') == UNIT_TYPE['occupation'])
              .select('code', 'membership_types', 'candidates', 'candidate_node_ids', 'x_token',
                      'x_cross_check', 'pums_locator').iter_rows())
    categories = {name: counts[name] for name in CROSS_CHECKS}
    return same_rows(expected, actual) and same_json(report.get('x_categories'), categories)


def cross_check(code: str, residual: set[str], pums: tuple | None, others: set[str],
                delivered: set[str]) -> str:
    '''The spec's refined cross-check; `failed` stands for a build that should have stopped.'''
    if pums is None:
        return 'failed' if code in delivered else 'not_delivered_no_pums_list'
    members = pums[0]
    if not residual or not residual <= members or not members - residual <= others:
        return 'failed'
    return 'equal' if residual == members else 'strict_subset'


# Links, guards and eligibility.

def monthly_panel(parquet: Path) -> pl.DataFrame:
    return (pl.scan_parquet(parquet).select(PANEL_COLUMNS).with_row_index('source_row')
            .with_columns(pl.col('source_row').cast(pl.UInt64),
                          month=pl.col('YEAR') * 12 + pl.col('MONTH') - 1,
                          label=pl.format('{}-{}', pl.col('YEAR'),
                                          pl.col('MONTH').cast(pl.String).str.zfill(2)))
            .collect())


def matched(panel: pl.DataFrame, key: str, side: Iterable[str], gap: int,
            start: int | None = None) -> pl.DataFrame:
    '''Every pair of rows with the same `key` in calendar months m and m + gap.'''
    side = list(side)
    a = panel.select(key, 'month', *side)
    if start is not None:
        a = a.filter(pl.col('month') == start)
    a = a.rename({name: name + '_a' for name in ('month', *side)})
    b = panel.select(key, 'month', *side).rename({name: name + '_b' for name in side})
    return (a.with_columns(month=pl.col('month_a') + gap).join(b, on=[key, 'month'])
            .drop('month', 'month_a'))


def link_candidates(panel: pl.DataFrame, key: str, side: Iterable[str]) -> pl.DataFrame:
    '''The one-month and two-month matches on `key`, with whether each meets its MISH rule.'''
    side = list(side)
    return pl.concat([
        matched(panel, key, side, 1).with_columns(link_type=pl.lit('one_month'),
                                                  rule=ONE_MONTH_RULE),
        matched(panel, key, side, 2, TWO_MONTH_FROM).with_columns(
            link_type=pl.lit('two_month'), rule=TWO_MONTH_RULE),
    ]).with_columns(period=pl.format('{}>{}', pl.col('label_a'), pl.col('label_b')))


def link_counts(panel: pl.DataFrame, candidates: pl.DataFrame) -> tuple[dict, list[tuple]]:
    '''The report's linkage counts and the `links` diagnostics, by link type and month pair.'''
    on_cpsidp = link_candidates(panel, 'CPSIDP', ('label', 'MISH')).filter('rule')
    counts = {}
    for link_type, period, rule in candidates.select('link_type', 'period', 'rule').iter_rows():
        entry = counts.setdefault((link_type, period), [0, 0, 0])
        entry[0 if rule else 2] += 1
    for link_type, period in on_cpsidp.select('link_type', 'period').iter_rows():
        counts.setdefault((link_type, period), [0, 0, 0])[1] += 1
    linkage, rows = {name: {} for name in LINK_TYPES}, []
    for (link_type, period), (cpsidv, cpsidp, other) in counts.items():
        linkage[link_type][period] = {'cpsidp': cpsidp, 'cpsidv': cpsidv,
                                      'other_gap_matches': other}
        rows.append(diagnostic('links', link_type, cpsidv, period=period, count_cpsidp=cpsidp))
        rows.append(diagnostic('links', f'other_gap_matches_{link_type}', other, period=period))
    return linkage, rows


def monthly_links(candidates: pl.DataFrame) -> pl.DataFrame:
    '''The links of the plan's linked-pairs table, before guards, weights and products.'''
    renamed = {'CPSID_a': 'CPSID', 'label_a': 'month_a', 'label_b': 'month_b'}
    for name in ('source_row', 'MISH', 'EMPSTAT', 'IND', 'OCC', 'QEMPSTAT', 'QIND', 'QOCC'):
        for side in ('a', 'b'):
            renamed[f'{name}_{side}'] = f'{name.lower()}_{side}'
    renamed |= {'EMPSAME_b': 'empsame_b', 'ACTSAME_b': 'actsame_b'}
    return (candidates.filter('rule').rename(renamed)
            .select('CPSIDV', 'CPSID', 'month_a', 'month_b', 'link_type', 'source_row_a',
                    'source_row_b', 'mish_a', 'mish_b', 'empstat_a', 'empstat_b', 'ind_a',
                    'ind_b', 'occ_a', 'occ_b', 'qempstat_a', 'qempstat_b', 'qind_a', 'qind_b',
                    'qocc_a', 'qocc_b', 'empsame_b', 'actsame_b', 'period')
            .sort('month_a', 'link_type', 'CPSIDV'))


def weight_status(link_type: str, weight: Decimal | None) -> str:
    if link_type != 'one_month':
        return 'not_linkable'
    if weight is None:
        return 'null'
    return 'zero' if weight == 0 else 'positive' if weight > 0 else 'negative'


EMPLOYED_BOTH = pl.col('empstat_a').is_in(EMPLOYED) & pl.col('empstat_b').is_in(EMPLOYED)


def guard_expr(dimension: str) -> pl.Expr:
    '''Spec "Guard": read at the later month; null unless employed in both months.'''
    empsame, actsame = pl.col('empsame_b'), pl.col('actsame_b')
    if dimension == 'industry':
        guard = (pl.when(empsame == 1).then(pl.lit('changed'))
                 .when(empsame == 2).then(pl.lit('same')).otherwise(pl.lit('unusable')))
    else:
        guard = (pl.when(empsame == 1).then(pl.lit('changed'))
                 .when((empsame == 2) & (actsame == 2)).then(pl.lit('changed'))
                 .when((empsame == 2) & (actsame == 1)).then(pl.lit('same'))
                 .otherwise(pl.lit('unusable')))
    return pl.when(EMPLOYED_BOTH).then(guard)


def reason_expr(product: str, dimension: str) -> pl.Expr:
    '''SD3: the first exclusion of a one-month link, or `eligible`.'''
    code = DIMENSION_CODE[dimension]
    a, b = pl.col(f'{code}_a'), pl.col(f'{code}_b')
    status = pl.col('weight_status')
    reason = (pl.when(status == 'null').then(pl.lit('weight_null'))
              .when(status == 'zero').then(pl.lit('weight_zero')))
    if product == 'monthly_ee':
        guard = pl.col(f'guard_{dimension}')
        reason = (reason.when(~EMPLOYED_BOTH).then(pl.lit('not_employed_both'))
                  .when((a == NOT_IN_UNIVERSE) | (b == NOT_IN_UNIVERSE))
                  .then(pl.lit('code_not_in_universe'))
                  .when(guard == 'unusable').then(pl.lit('guard_unusable'))
                  .when((guard == 'same') & (a == b)).then(pl.lit('no_change_reported'))
                  .when(guard == 'same').then(pl.lit('coding_noise')))
    else:
        empstat_a = pl.col('empstat_a')
        reason = (reason.when(empstat_a == NEW_WORKER).then(pl.lit('origin_new_worker_22'))
                  .when(empstat_a != UNEMPLOYED_WITH_LAST_JOB)
                  .then(pl.lit('origin_not_unemployed_21'))
                  .when(~pl.col('empstat_b').is_in(EMPLOYED))
                  .then(pl.lit('destination_not_employed'))
                  .when((a == NOT_IN_UNIVERSE) | (b == NOT_IN_UNIVERSE))
                  .then(pl.lit('code_not_in_universe')))
    return reason.otherwise(pl.lit('eligible'))


def strict_expr(dimension: str, nonallocation: dict[str, list[int]]) -> pl.Expr:
    '''Spec "Evidence policies": both ends mapped, and QEMPSTAT and the dimension's own flag
    show nonallocation at both months.'''
    code, flag = DIMENSION_CODE[dimension], DIMENSION_FLAG[dimension]
    special = SPECIAL[dimension]
    condition = (pl.col(f'{code}_a') != special) & (pl.col(f'{code}_b') != special)
    for variable, column in (('QEMPSTAT', 'qempstat'), (flag.upper(), flag)):
        for side in ('a', 'b'):
            condition &= pl.col(f'{column}_{side}').is_in(nonallocation[variable])
    return condition.fill_null(False)


def variant_columns(nonallocation: dict[str, list[int]]) -> list[pl.Expr]:
    '''For each monthly product and dimension: the funnel reason, sensitivity and strict.'''
    one_month = pl.col('link_type') == 'one_month'
    columns = []
    for product in MONTHLY_PRODUCTS:
        for dimension in DIMENSIONS:
            reason = reason_expr(product, dimension)
            eligible = one_month & (reason == 'eligible')
            columns += [
                reason.alias(f'reason:{product}:{dimension}'),
                eligible.alias(f'{product}:{dimension}:sensitivity'),
                (eligible & strict_expr(dimension, nonallocation))
                .alias(f'{product}:{dimension}:strict'),
            ]
    return columns


def products_expr() -> pl.Expr:
    names = [f'{product}:{dimension}:{policy}' for product in MONTHLY_PRODUCTS
             for dimension in DIMENSIONS for policy in POLICIES[product]]
    return (pl.concat_list([pl.when(pl.col(name)).then(pl.lit(name)) for name in names])
            .list.drop_nulls().list.sort().alias('products'))


def recompute_links(panel: pl.DataFrame, monthly: Delivery,
                    nonallocation: dict[str, list[int]]) -> tuple[pl.DataFrame, list, dict, list]:
    '''The linked-pairs frame with weights, guards, reasons and products, and the link counts.'''
    candidates = link_candidates(panel, 'CPSIDV', LINK_SIDE)
    linkage, link_rows = link_counts(panel, candidates)
    links = monthly_links(candidates)
    one_month = links.filter(pl.col('link_type') == 'one_month')
    weights = read_weights(monthly, set(one_month['source_row_a'].to_list()), set()).full
    link_weights = [weights.get(row) if link_type == 'one_month' else None
                    for link_type, row in links.select('link_type', 'source_row_a').iter_rows()]
    statuses = [weight_status(link_type, weight) for link_type, weight
                in zip(links['link_type'].to_list(), link_weights, strict=True)]
    links = links.with_columns(
        pl.Series('weight_a', [None if status == 'not_linkable' or weight is None
                               else float(weight)
                               for status, weight in zip(statuses, link_weights, strict=True)],
                  dtype=pl.Float64),
        pl.Series('weight_status', statuses, dtype=pl.String),
        guard_expr('industry').alias('guard_industry'),
        guard_expr('occupation').alias('guard_occupation'),
    ).with_columns(variant_columns(nonallocation)).with_columns(products_expr())
    return links, link_weights, linkage, link_rows


def check_links(links: pl.DataFrame, ours: pl.DataFrame, pairs: pl.DataFrame, linkage: dict,
                link_rows: list, report: dict, diagnostics: pl.DataFrame) -> bool:
    one_month = links.filter(pl.col('link_type') == 'one_month')
    weights = dict.fromkeys(WEIGHT_STATUSES, 0)
    for status, count in one_month.group_by('weight_status').len().iter_rows():
        weights[status] = count
    weight_rows = [diagnostic('weight', status, count) for status, count in weights.items()]
    schema = [(name, dtype) for name, dtype in pairs.schema.items()]
    return all((
        schema == list(LINKED_PAIRS_SCHEMA.items()),
        columns_equal(ours, pairs, LINK_COLUMNS),
        same_json(report.get('linkage'), linkage),
        same_json(report.get('weights'), weights),
        same_rows(link_rows, diagnostics_rows(diagnostics, 'links')),
        same_rows(weight_rows, diagnostics_rows(diagnostics, 'weight')),
    ))


def expected_pairs(links: pl.DataFrame) -> pl.DataFrame:
    return links.select([pl.col(name).cast(dtype) for name, dtype in LINKED_PAIRS_SCHEMA.items()])


def source_exceptions(panel: pl.DataFrame) -> int:
    '''Monthly panel rows in MISH 1 or 5 that deliver a substantive EMPSAME answer, 1 or 2.

    EMPSAME is not in universe in MISH 1 and 5, so each such row is a source exception. The
    count is of panel rows, whatever their EMPSTAT, weight or link status (controller ruling,
    2026-11-24): a one-month link never has MISH 1 or 5 at its later month.
    '''
    return panel.filter(pl.col('MISH').is_in(SOURCE_EXCEPTION_MISH),
                        pl.col('EMPSAME').is_in(SUBSTANTIVE_EMPSAME)).height


def guard_population(links: pl.DataFrame) -> pl.DataFrame:
    '''SD3: employed-to-employed one-month links with positive weight.'''
    return links.filter(pl.col('link_type') == 'one_month', EMPLOYED_BOTH,
                        pl.col('weight_status') == 'positive')


def check_guards(links: pl.DataFrame, ours: pl.DataFrame, pairs: pl.DataFrame, report: dict,
                 diagnostics: pl.DataFrame, exceptions: int) -> bool:
    population = guard_population(links)
    rows, shares = [], {}
    for dimension in DIMENSIONS:
        counts = dict.fromkeys(GUARD_STATES, 0)
        for state, count in population.group_by(f'guard_{dimension}').len().iter_rows():
            counts[state] = count
        rows += [diagnostic('guard', state, count, product='monthly_ee', dimension=dimension)
                 for state, count in counts.items()]
        total = sum(counts.values())
        shares[f'monthly_ee:{dimension}'] = (
            (counts['changed'] + counts['same']) / total if total else None)
    noise = links.filter(pl.col('link_type') == 'one_month',
                         pl.col('reason:monthly_ee:industry') == 'coding_noise',
                         pl.col('empsame_b') == 2, pl.col('actsame_b') == 2).height
    rows.append(diagnostic('guard', 'noise_after_duty_change', noise, product='monthly_ee',
                           dimension='industry'))
    shares |= {'monthly_ue': 'not_applicable', 'asec_retro': 'not_applicable'}
    rows.append(diagnostic('guard', SOURCE_EXCEPTION, exceptions))
    return all((
        columns_equal(ours, pairs, GUARD_COLUMNS),
        same_rows(rows, diagnostics_rows(diagnostics, 'guard')),
        same_json(report.get('usable_guard_share'), shares),
        same_json(report.get('guard_source_exceptions'), {SOURCE_EXCEPTION: exceptions}),
    ))


def funnel_counts(frame: pl.DataFrame, column: str, product: str) -> dict[str, int]:
    counts = dict.fromkeys(FUNNELS[product], 0)
    for reason, count in frame.group_by(column).len().iter_rows():
        counts[reason] = count
    return counts


def check_eligibility(links: pl.DataFrame, ours: pl.DataFrame, reasons: dict[str, pl.DataFrame],
                      pairs: pl.DataFrame, report: dict, diagnostics: pl.DataFrame) -> bool:
    one_month = links.filter(pl.col('link_type') == 'one_month')
    funnels, rows = {}, []
    for product in (*MONTHLY_PRODUCTS, 'asec_retro'):
        for dimension in DIMENSIONS:
            if product == 'asec_retro':
                counts = funnel_counts(reasons[dimension], 'reason', product)
            else:
                counts = funnel_counts(one_month, f'reason:{product}:{dimension}', product)
            funnels[f'{product}:{dimension}'] = counts
            rows += [diagnostic('funnel', reason, count, product=product, dimension=dimension,
                                exclusive=True) for reason, count in counts.items()]
    return all((
        columns_equal(ours, pairs, PRODUCT_COLUMNS),
        same_json(report.get('funnels'), funnels),
        same_rows(rows, diagnostics_rows(diagnostics, 'funnel')),
    ))


# The ASEC persons.

def asec_frame(parquet: Path) -> pl.DataFrame:
    return (pl.scan_parquet(parquet)
            .select('YEAR', 'EMPSTAT', 'IND', 'OCC', 'INDLY', 'OCCLY')
            .with_row_index('row').with_columns(pl.col('row').cast(pl.Int64)).collect())


def asec_candidates(asec: pl.DataFrame) -> set[int]:
    '''Rows that may be eligible in some dimension whatever their weight.'''
    condition = pl.lit(False)
    for dimension in DIMENSIONS:
        last, current = pl.col(LAST_YEAR[dimension]), pl.col(CURRENT[dimension])
        condition |= ((last != NOT_IN_UNIVERSE) & (current != NOT_IN_UNIVERSE)
                      & (last != current))
    return set(asec.filter(pl.col('EMPSTAT').is_in(EMPLOYED), condition)['row'].to_list())


def asec_reasons(asec: pl.DataFrame, weights: dict[int, Decimal | None]) -> dict:
    '''SD3's ASEC funnel reason of every person, for each dimension.'''
    statuses = [weight_status('one_month', weights[row]) for row in asec['row'].to_list()]
    frame = asec.with_columns(pl.Series('weight_status', statuses, dtype=pl.String))
    reasons = {}
    for dimension in DIMENSIONS:
        last, current = pl.col(LAST_YEAR[dimension]), pl.col(CURRENT[dimension])
        reason = (pl.when(pl.col('weight_status') != 'positive')
                  .then(pl.lit('weight_nonpositive'))
                  .when(~pl.col('EMPSTAT').is_in(EMPLOYED)).then(pl.lit('not_employed'))
                  .when(last == NOT_IN_UNIVERSE).then(pl.lit('last_year_code_not_in_universe'))
                  .when(current == NOT_IN_UNIVERSE)
                  .then(pl.lit('current_code_not_in_universe'))
                  .when(last == current).then(pl.lit('same_category'))
                  .otherwise(pl.lit('eligible')))
        reasons[dimension] = frame.select('row', 'YEAR', last.alias('a'), current.alias('b'),
                                          reason.alias('reason'))
    return reasons


# Estimation.

@dataclass
class Sums:
    '''Exact counts and weight sums of one variant's eligible records.'''
    cells: dict = field(default_factory=dict)  # (a, b) -> [n, S]
    origins: dict = field(default_factory=dict)  # a -> [n, S]
    period_cells: dict = field(default_factory=dict)  # (a, b, period) -> [n, S]
    period_origins: dict = field(default_factory=dict)  # (a, period) -> [n, S]


def accumulate(records: Iterable[tuple[str, str, str, Decimal]]) -> Sums:
    sums = Sums()
    with localcontext(EXACT):
        for a, b, period, weight in records:
            for table, key in ((sums.cells, (a, b)), (sums.origins, a),
                               (sums.period_cells, (a, b, period)),
                               (sums.period_origins, (a, period))):
                entry = table.setdefault(key, [0, Decimal(0)])
                entry[0] += 1
                entry[1] += weight
    return sums


def unit(dimension: str, code: str) -> str:
    return f'feature:{UNIT_TYPE[dimension]}:{code}'


@dataclass
class Expected:
    targets: dict = field(default_factory=dict)  # (universe, unit_a, unit_b, measure) -> row
    support: list = field(default_factory=list)  # point rows: cells, denominators, nonpositive
    asec_se: dict = field(default_factory=dict)  # target key -> (se, se_method)
    asec_support: list = field(default_factory=list)  # replicate_share_undefined rows
    replicates_equal: dict = field(default_factory=dict)  # dimension -> bool


def add_points(expected: Expected, product: str, dimension: str, policy: str,
               sums: Sums) -> None:
    '''Spec "Measures": `average_total` and `forward_share` of every observed cell.'''
    k, universe = K[product], f'{product}:{policy}'
    for (a, b), (count, mass) in sorted(sums.cells.items()):
        total = float(mass) / k
        origin_mass = sums.origins[a][1]
        flags = {SIZE_GATE, PRODUCT_FLAG[product]}
        if SPECIAL[dimension] in (a, b):
            flags.add(SPECIAL_FLAG)
        row = {'source': SOURCE, 'family': FAMILY, 'unit_a_type': UNIT_TYPE[dimension],
               'unit_b_type': UNIT_TYPE[dimension], 'n_unweighted': count, 'n_weighted': total,
               'sample_set': SAMPLE_SET[product], 'vintage': VINTAGE[dimension],
               'flags': sorted(flags)}
        key = (universe, unit(dimension, a), unit(dimension, b))
        expected.targets[(*key, 'average_total')] = {**row, 'value': total}
        if origin_mass > 0:
            share = total / (float(origin_mass) / k)
            expected.targets[(*key, 'forward_share')] = {**row, 'value': share}
        else:
            expected.support.append((product, dimension, policy, 'undefined_share', a, b, 'all',
                                     count, float(mass), 'nonpositive_denominator', None))
    for (a, b, period), (count, mass) in sums.period_cells.items():
        expected.support.append((product, dimension, policy, 'cell', a, b, period, count,
                                 float(mass), None, None))
    for (a, period), (count, mass) in sums.period_origins.items():
        expected.support.append((product, dimension, policy, 'denominator', a, None, period,
                                 count, float(mass), None, None))


def replicate_se(point: float, values: list[float]) -> float:
    '''Spec "Standard errors", ASEC: sqrt((4/160) × Σ (θ_r − θ)²).'''
    return math.sqrt((4 / 160) * math.fsum((value - point) ** 2 for value in values))


def recorded_replicates(replicates_file: Path, dimension: str) -> pl.DataFrame | None:
    '''The bundle's ASEC replicate rows of one dimension in file order; None for a bad schema.'''
    frame = (pl.scan_parquet(replicates_file)
             .filter(pl.col('product') == 'asec_retro', pl.col('dimension') == dimension)
             .select(list(REPLICATE_SCHEMA)).collect())
    schema = [(name, dtype) for name, dtype in frame.schema.items()]
    return frame if schema == list(REPLICATE_SCHEMA.items()) else None


def add_asec_replicates(expected: Expected, dimension: str, records: list[tuple],
                        replicate_texts: dict[int, str], sums: Sums,
                        recorded: pl.DataFrame | None) -> None:
    '''The replicate statistics of every ASEC cell, one origin at a time.

    Each origin's replicate rows are compared with the next rows of `recorded`, the bundle's
    rows in the plan's order (origin, destination, replicate), and then dropped.
    '''
    universe, start, equal = 'asec_retro:sensitivity', 0, recorded is not None
    by_origin = defaultdict(list)
    for row, a, b in records:
        by_origin[a].append((row, b))
    for a in sorted(by_origin):
        rows = []
        origin = [Decimal(0)] * REPLICATES
        cells = {}
        with localcontext(EXACT):
            for row, b in by_origin[a]:
                weights = replicate_weights(replicate_texts[row])
                cell = cells.setdefault(b, [Decimal(0)] * REPLICATES)
                for index, weight in enumerate(weights):
                    origin[index] += weight
                    cell[index] += weight
        denominators = [float(value) / ASEC_K for value in origin]
        undefined = [index + 1 for index, value in enumerate(origin) if not value > 0]
        origin_mass = sums.origins[a][1]
        for b in sorted(cells):
            count, mass = sums.cells[(a, b)]
            total = float(mass) / ASEC_K
            numerators = [float(value) / ASEC_K for value in cells[b]]
            key = (universe, unit(dimension, a), unit(dimension, b))
            expected.asec_se[(*key, 'average_total')] = (replicate_se(total, numerators),
                                                         'replicate')
            estimates = [numerator / denominator if value > 0 else None
                         for numerator, denominator, value
                         in zip(numerators, denominators, origin, strict=True)]
            if origin_mass > 0:
                share = total / (float(origin_mass) / ASEC_K)
                if undefined:
                    expected.asec_se[(*key, 'forward_share')] = (None, 'none')
                    expected.asec_support.append((
                        'asec_retro', dimension, 'sensitivity', 'undefined_share', a, b, 'all',
                        count, float(mass), 'replicate_share_undefined', undefined))
                else:
                    expected.asec_se[(*key, 'forward_share')] = (
                        replicate_se(share, estimates), 'replicate')
            rows += [('sensitivity', a, b, index + 1, numerators[index], denominators[index],
                      estimates[index],
                      'defined' if estimates[index] is not None else 'denominator_nonpositive')
                     for index in range(REPLICATES)]
        if equal:
            ours = pl.DataFrame(rows, schema=REPLICATE_SCHEMA, orient='row')
            equal = recorded.slice(start, ours.height).equals(ours)
            start += ours.height
    expected.replicates_equal[dimension] = equal and start == recorded.height


def recompute_estimates(links: pl.DataFrame, link_weights: list, reasons: dict,
                        weights: dict[int, Decimal | None], replicate_texts: dict,
                        replicates_file: Path) -> Expected:
    expected = Expected()
    positions = links.with_row_index('position')
    for product in MONTHLY_PRODUCTS:
        for dimension in DIMENSIONS:
            code = DIMENSION_CODE[dimension]
            for policy in POLICIES[product]:
                selected = positions.filter(pl.col(f'{product}:{dimension}:{policy}'))
                records = [(a, b, period, link_weights[position])
                           for position, a, b, period in selected.select(
                               'position', f'{code}_a', f'{code}_b', 'period').iter_rows()]
                add_points(expected, product, dimension, policy, accumulate(records))
    for dimension in DIMENSIONS:
        eligible = reasons[dimension].filter(pl.col('reason') == 'eligible')
        rows = list(eligible.select('row', 'a', 'b', 'YEAR').iter_rows())
        sums = accumulate((a, b, f'asec-{year}', weights[row]) for row, a, b, year in rows)
        add_points(expected, 'asec_retro', dimension, 'sensitivity', sums)
        add_asec_replicates(expected, dimension, [(row, a, b) for row, a, b, _ in rows],
                            replicate_texts, sums,
                            recorded_replicates(replicates_file, dimension))
    return expected


def check_targets(expected: Expected, targets: pl.DataFrame, support: pl.DataFrame) -> bool:
    actual, repeated = {}, 0
    columns = ('universe', 'unit_a', 'unit_b', 'measure', 'se', 'se_method', *TARGET_FIELDS)
    for row in targets.select(columns).iter_rows(named=True):
        key = (row['universe'], row['unit_a'], row['unit_b'], row['measure'])
        repeated += key in actual
        actual[key] = row
    if repeated or set(actual) != set(expected.targets):
        return False
    for key, row in expected.targets.items():
        recorded = actual[key]
        if not all(same(row[name], recorded[name]) for name in TARGET_FIELDS):
            return False
        if not key[0].startswith('asec_retro:') and recorded['se_method'] != (
                'none' if recorded['se'] is None else 'bootstrap'):
            return False
    point_rows = [row for row in support.iter_rows()
                  if row[3] in ('cell', 'denominator') or row[9] == 'nonpositive_denominator']
    return same_rows(expected.support, point_rows)


def check_asec_se(expected: Expected, targets: pl.DataFrame, support: pl.DataFrame) -> bool:
    recorded = {(row['universe'], row['unit_a'], row['unit_b'], row['measure']):
                (row['se'], row['se_method'])
                for row in targets.filter(pl.col('universe') == 'asec_retro:sensitivity')
                .iter_rows(named=True)}
    undefined = [row for row in support.iter_rows() if row[0] == 'asec_retro'
                 and row[9] == 'replicate_share_undefined']
    return all((
        set(recorded) == set(expected.asec_se),
        all(same(value, recorded.get(key)) for key, value in expected.asec_se.items()),
        same_rows(expected.asec_support, undefined),
        all(expected.replicates_equal.get(dimension, False) for dimension in DIMENSIONS),
    ))


# Reconciliation.

def reconcile(data_dir: Path, run_id: str, pin: str) -> dict[str, bool]:
    '''Authenticate the bundle and its inputs, recompute, and compare.'''
    directory = open_bundle(data_dir, run_id, pin)
    inputs = read_json(directory / 'inputs.json')
    report = read_json(directory / 'report.json')
    upstream = select_upstream(data_dir, inputs)
    tables = {name: directory / f'{name}.parquet' for name in TABLES}
    units = pl.read_parquet(tables['cps_category_units'])
    diagnostics = pl.read_parquet(tables['cps_flow_diagnostics'])
    targets = pl.read_parquet(tables['cps_job_flows'])
    support = pl.read_parquet(tables['cps_flow_support'])
    pairs = pl.read_parquet(tables['cps_linked_pairs'])

    statuses = {'industry': industry_statuses(upstream.industry_list)}
    tokens = occupation_tokens(upstream.occupation_list)
    statuses['occupation'] = {code: occupation_status(token) for code, token in tokens.items()}
    nonallocation = nonallocation_values(upstream.monthly.ddi)

    panel = monthly_panel(upstream.monthly.parquet)
    asec = asec_frame(upstream.asec.parquet)
    delivered = {code for frame, names in ((panel, ('OCC',)), (asec, ('OCC', 'OCCLY')))
                 for name in names for code in frame[name].unique().to_list()}
    checks = {
        'value_classes': check_value_classes({'monthly': panel, 'asec': asec}, statuses, report,
                                             diagnostics, units),
        'x_residuals': check_x_residuals(tokens, soc_tree(upstream.soc_nodes,
                                                          upstream.code_paths),
                                         pums_lists(upstream.pums_lookup), delivered, report,
                                         units),
    }
    links, link_weights, linkage, link_rows = recompute_links(panel, upstream.monthly,
                                                              nonallocation)
    exceptions = source_exceptions(panel)
    del panel
    asec_weights = read_weights(upstream.asec, None, asec_candidates(asec))
    reasons = asec_reasons(asec, asec_weights.full)
    expected = recompute_estimates(links, link_weights, reasons, asec_weights.full,
                                   asec_weights.replicates, tables['cps_flow_replicates'])
    ours = expected_pairs(links)
    checks |= {
        'links': check_links(links, ours, pairs, linkage, link_rows, report, diagnostics),
        'guards': check_guards(links, ours, pairs, report, diagnostics, exceptions),
        'eligibility': check_eligibility(links, ours, reasons, pairs, report, diagnostics),
        'targets': check_targets(expected, targets, support),
        'asec_se': check_asec_se(expected, targets, support),
    }
    return {name: checks[name] for name in CHECKS}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    result.add_argument('--data-dir', type=Path, required=True)
    result.add_argument('--run', required=True)
    result.add_argument('--outputs-sha256', required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        checks = reconcile(arguments.data_dir, arguments.run, arguments.outputs_sha256)
    except Refused as refusal:
        print(FAILURE + str(refusal), file=sys.stderr)
        return 2
    except Exception:
        # A refusal never prints exception text, which can hold row content.
        print(FAILURE + 'unexpected', file=sys.stderr)
        return 2
    equal = all(checks.values())
    print(json.dumps({'checks': checks, 'equal': equal}, sort_keys=True))
    return 0 if equal else 1


if __name__ == '__main__':
    sys.exit(main())
