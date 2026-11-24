'''Publish, verify and compare immutable Stage 11 CPS job-flow bundles.

A bundle holds six tables, `inputs.json` (selection, rules and provenance), `report.json`
(counts and shares) and the detached inventory `outputs.json`. `build` stages into
`<RUN_ID>.part`. The decompressed CSV copies that carry the literal weights live in
`<RUN_ID>.part/.scratch` only while the weighted sources are open. Every other row-level
intermediate stays in memory. The build removes the scratch before it writes the JSON files,
rechecks its six pins and its software just before publication and only then renames the
staging directory. A failure removes only that staging directory.

`verify_bundle` authenticates the detached pin, the file set and the inventory before it reads
anything else, then recomputes every table offline in a temporary directory outside the data
root. `compare_runs` checks two published bundles for exact logical replay. It does not
establish trust. `cps_linked_pairs.parquet` is IPUMS microdata. Every other file is aggregate,
and no JSON file holds a person or household identifier. Every failure raises `ValueError`
with a fixed message that holds no row content.
'''

import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import distributions
from pathlib import Path

import polars as pl

from embedding_data import (
    cps_flow_estimation,
    cps_flow_guards,
    cps_flow_inputs,
    cps_flow_linkage,
    cps_flow_lists,
    cps_flow_references,
    cps_flow_targets,
    cps_flow_units,
    cps_flow_weights,
    geography_references,
    manifest,
    paths,
    target_contract,
    target_io,
)
from embedding_data.cps_flow_estimation import Variant
from embedding_data.cps_flow_linkage import ONE_MONTH, TWO_MONTH

SCHEMA_VERSION = cps_flow_targets.SCHEMA_VERSION
CONTRACTS = cps_flow_targets.CONTRACTS
TABLES = ('cps_job_flows', 'cps_category_units', 'cps_flow_support', 'cps_flow_replicates',
          'cps_flow_diagnostics', 'cps_linked_pairs')
FILES = (*(name + '.parquet' for name in TABLES), 'inputs.json', 'report.json')
SOFTWARE_ROOT = paths.PROJECT_ROOT
SOFTWARE_FILES = (
    'pyproject.toml',
    'src/embedding_data/__init__.py',
    'src/embedding_data/acs_code_references.py',
    'src/embedding_data/acs_mapping_contract.py',
    'src/embedding_data/acs_mapping_inputs.py',
    'src/embedding_data/acs_mapping_io.py',
    'src/embedding_data/acs_mapping_references.py',
    'src/embedding_data/classification_tables.py',
    'src/embedding_data/code_build.py',
    'src/embedding_data/code_references.py',
    'src/embedding_data/cps_flow_bundle.py',
    'src/embedding_data/cps_flow_estimation.py',
    'src/embedding_data/cps_flow_guards.py',
    'src/embedding_data/cps_flow_inputs.py',
    'src/embedding_data/cps_flow_linkage.py',
    'src/embedding_data/cps_flow_lists.py',
    'src/embedding_data/cps_flow_references.py',
    'src/embedding_data/cps_flow_targets.py',
    'src/embedding_data/cps_flow_units.py',
    'src/embedding_data/cps_flow_weights.py',
    'src/embedding_data/cps_job_flows.py',
    'src/embedding_data/filing_rules.py',
    'src/embedding_data/geography_build.py',
    'src/embedding_data/geography_hud.py',
    'src/embedding_data/geography_parsers.py',
    'src/embedding_data/geography_references.py',
    'src/embedding_data/geography_tables.py',
    'src/embedding_data/ipums_acceptance.py',
    'src/embedding_data/ipums_census_access.py',
    'src/embedding_data/ipums_conversion.py',
    'src/embedding_data/ipums_ddi.py',
    'src/embedding_data/ipums_delivery.py',
    'src/embedding_data/ipums_industry.py',
    'src/embedding_data/ipums_parity.py',
    'src/embedding_data/ipums_references.py',
    'src/embedding_data/ipums_totals.py',
    'src/embedding_data/ipums_verification_run.py',
    'src/embedding_data/ipums_weights.py',
    'src/embedding_data/ita_catalog.py',
    'src/embedding_data/ita_naics_mapping.py',
    'src/embedding_data/ita_references.py',
    'src/embedding_data/ita_summary.py',
    'src/embedding_data/manifest.py',
    'src/embedding_data/naics_relationships.py',
    'src/embedding_data/osha_benchmark_download.py',
    'src/embedding_data/osha_encoding.py',
    'src/embedding_data/paths.py',
    'src/embedding_data/target_contract.py',
    'src/embedding_data/target_inputs.py',
    'src/embedding_data/target_io.py',
    'uv.lock',
)
RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')
PIN = re.compile(r'[0-9a-f]{64}')
INPUT_FIELDS = frozenset({
    'run_id', 'contracts', 'upstream', 'deliveries', 'rules', 'divisors', 'bootstrap',
    'software', 'execution',
})
POLICIES = {'monthly_ee': ('strict', 'sensitivity'), 'monthly_ue': ('strict', 'sensitivity'),
            'asec_retro': ('sensitivity',)}
# The 18 one-month link months that divide the monthly totals. October 2025 is absent.
LINK_MONTHS = (
    '2025-01>2025-02', '2025-02>2025-03', '2025-03>2025-04', '2025-04>2025-05',
    '2025-05>2025-06', '2025-06>2025-07', '2025-07>2025-08', '2025-08>2025-09',
    '2025-11>2025-12', '2025-12>2026-01', '2026-01>2026-02', '2026-02>2026-03',
    '2026-03>2026-04', '2026-04>2026-05', '2026-05>2026-06', '2026-06>2026-07',
    '2026-07>2026-08', '2026-08>2026-09')
ASEC_PERIODS = ('asec-2025', 'asec-2026')
BOOTSTRAP_SCOPE = (
    'one sorted CPSID list per monthly product: the union over both dimensions and both '
    'policies of the households with an eligible, positive-weight link; one set of draws '
    'serves every variant of the product')
# The delivered code fields of each file and their dimensions.
VALUE_FIELDS = {'monthly': {'IND': 'industry', 'OCC': 'occupation'},
                'asec': {'IND': 'industry', 'OCC': 'occupation', 'INDLY': 'industry',
                         'OCCLY': 'occupation'}}
PANEL_COLUMNS = ('YEAR', 'MONTH', 'ASECFLAG', 'CPSID', 'CPSIDP', 'CPSIDV', 'MISH', 'EMPSTAT',
                 'IND', 'OCC', 'QEMPSTAT', 'QIND', 'QOCC', 'EMPSAME', 'ACTSAME')
PERSON_COLUMNS = ('YEAR', 'EMPSTAT', 'IND', 'OCC', 'INDLY', 'OCCLY', 'QEMPSTAT', 'QIND', 'QOCC',
                  'QOCCLY')
# The columns of a one-month link that a monthly product frame reads, keyed by its two rows.
LINK_KEYS = ['source_row_a', 'source_row_b']
FRAME_COLUMNS = (*LINK_KEYS, 'CPSID', 'month_a', 'month_b', 'link_type', 'empstat_a',
                 'empstat_b', 'ind_a', 'ind_b', 'occ_a', 'occ_b', 'qempstat_a', 'qempstat_b',
                 'qind_a', 'qind_b', 'qocc_a', 'qocc_b', 'empsame_b', 'actsame_b', 'weight_a',
                 'weight_status')


@dataclass(frozen=True)
class _Products:
    '''The tables, report and DDI rules of one computation.'''

    tables: dict[str, pl.DataFrame]
    report: dict
    ddi: dict[str, dict]


def run_directory(data_dir: Path, run_id: str) -> Path:
    '''The published directory of one run: `derived/cps/job-flows/<run_id>`.'''
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError('unsafe run ID')
    return paths.derived_dir(Path(data_dir), 'cps') / 'job-flows' / run_id


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


def _guard_table() -> dict:
    '''The guard of every delivered EMPSAME/ACTSAME reading, by dimension.'''
    labels = cps_flow_inputs.DDI_LABELS['monthly']
    readings = pl.DataFrame(
        [(empsame, actsame) for empsame in sorted(labels['EMPSAME'])
         for actsame in sorted(labels['ACTSAME'])],
        schema={'empsame': pl.Int64, 'actsame': pl.Int64}, orient='row')
    found = readings.with_columns(
        cps_flow_guards.guard_expr(dimension, pl.col('empsame'), pl.col('actsame'))
        .alias(dimension) for dimension in cps_flow_guards.DIMENSIONS)
    return {f'{empsame:02d}/{actsame:02d}': {'industry': industry, 'occupation': occupation}
            for empsame, actsame, industry, occupation in found.iter_rows()}


def _rules(ddi: dict[str, dict]) -> dict:
    return {
        'guards': _guard_table(),
        'flag_classes': {
            file: {variable: cps_flow_guards.flag_classes(file, variable)
                   for variable in labels if variable in cps_flow_inputs.FLAG_VARIABLES}
            for file, labels in cps_flow_inputs.DDI_LABELS.items()},
        'value_classes': {
            'not_in_universe': cps_flow_linkage.NOT_IN_UNIVERSE,
            'specials': cps_flow_linkage.SPECIALS,
            'refused_statuses': list(cps_flow_linkage.NO_EQUIVALENT),
            'fields': VALUE_FIELDS},
        'ddi': ddi,
        'funnels': cps_flow_guards.REASONS,
        'flags': list(cps_flow_targets.FLAG_REGISTRY),
    }


def _inputs(run_id: str, selected: cps_flow_inputs.SelectedInputs, ddi: dict[str, dict],
            software: dict, execution: dict) -> dict:
    '''The provenance record of one build, in the form JSON reads it back.'''
    return _normalized({
        'run_id': run_id,
        'contracts': CONTRACTS,
        'upstream': selected.provenance['upstream'],
        'deliveries': selected.provenance['deliveries'],
        'rules': _rules(ddi),
        'divisors': {'monthly_k': cps_flow_estimation.MONTHLY_K,
                     'asec_k': cps_flow_estimation.ASEC_K, 'link_months': list(LINK_MONTHS),
                     'asec_periods': list(ASEC_PERIODS)},
        'bootstrap': {'seed': cps_flow_estimation.BOOTSTRAP_SEED,
                      'replicates': cps_flow_estimation.BOOTSTRAP_B, 'scope': BOOTSTRAP_SCOPE},
        'software': software,
        'execution': execution,
    })


def _units(selected: cps_flow_inputs.SelectedInputs) -> pl.DataFrame:
    '''The unit registry: the two Census lists, the Stage 4 nodes and the PUMS cross-check.'''
    delivered = {'industry': set(), 'occupation': set()}
    for file, fields in VALUE_FIELDS.items():
        frame = pl.scan_parquet(getattr(selected, file).parquet)
        for field, dimension in fields.items():
            found = frame.select(pl.col(field).unique()).collect().to_series()
            delivered[dimension].update(found.drop_nulls().to_list())
    request = selected.request
    return cps_flow_units.build_units(
        cps_flow_lists.read_industry_list(selected.industry_workbook),
        cps_flow_lists.read_occupation_list(selected.occupation_workbook),
        naics_nodes=pl.read_parquet(selected.naics_nodes),
        soc_nodes=pl.read_parquet(selected.soc_nodes),
        paths=pl.read_parquet(selected.code_paths),
        pums=cps_flow_units.read_pums_lists(selected.pums_lookup), delivered=delivered,
        evidence=cps_flow_references.special_evidence(selected.cps_receipt),
        references={'industry': request.stage7_receipt, 'occupation': request.stage8_receipt,
                    'special': request.cps_receipt})


def _value_classes(selected: cps_flow_inputs.SelectedInputs, units: pl.DataFrame) -> dict:
    '''Count the value classes of every delivered code field over both full files.'''
    counts = {}
    for file, fields in VALUE_FIELDS.items():
        frame = pl.scan_parquet(getattr(selected, file).parquet).select('YEAR', *fields)
        counts.update(cps_flow_linkage.count_value_classes(frame, file, fields, units))
    return counts


def _refuse_outside(periods: pl.Series, allowed: tuple[str, ...], message: str) -> None:
    if not set(periods.unique().to_list()) <= set(allowed):
        raise ValueError(message)


def _links(panel: pl.LazyFrame, weights: pl.LazyFrame) -> pl.DataFrame:
    '''Every monthly link with its earlier month's link weight and the weight's status.

    A two-month link has no linking weight (spec, Linkage), so its `weight_a` is null.
    '''
    weights = weights.select(pl.col('source_row').alias('source_row_a'),
                             pl.col('LNKFW1MWT').alias('weight_a'))
    linked = cps_flow_linkage.monthly_links(panel).join(
        weights, on='source_row_a', how='left', validate='m:1', maintain_order='left')
    return linked.with_columns(
        cps_flow_weights.weight_status_expr(pl.col('weight_a'), pl.col('link_type'))
        .alias('weight_status'),
        pl.when(pl.col('link_type') == TWO_MONTH).then(None).otherwise(pl.col('weight_a'))
        .alias('weight_a')).collect()


def _persons(selected: cps_flow_inputs.SelectedInputs, weights: pl.LazyFrame) -> pl.DataFrame:
    '''Every ASEC person with its source row, period, `ASECWT` status and code fields.

    An ASEC person is never a two-month link, so its weight is `null`, `zero` or `positive`.
    '''
    full = weights.select('source_row', pl.col('ASECWT').alias('weight'))
    return (pl.scan_parquet(selected.asec.parquet).select(PERSON_COLUMNS)
            .with_row_index('source_row').with_columns(pl.col('source_row').cast(pl.UInt64))
            .join(full, on='source_row', how='left', validate='1:1', maintain_order='left')
            .with_columns(
                cps_flow_weights.weight_status_expr(pl.col('weight'), pl.lit(ONE_MONTH))
                .alias('weight_status'),
                pl.format('asec-{}', pl.col('YEAR')).alias('period'))
            .collect())


def _monthly_period() -> pl.Expr:
    return pl.format('{}>{}', pl.col('month_a'), pl.col('month_b'))


def _guard_states(links: pl.DataFrame) -> dict:
    '''Count each guard over the employed-to-employed one-month links with a positive weight.'''
    employed = cps_flow_guards.EMPLOYED
    population = links.filter(
        (pl.col('link_type') == ONE_MONTH) & (pl.col('weight_status') == 'positive')
        & pl.col('empstat_a').is_in(employed) & pl.col('empstat_b').is_in(employed))
    states = {}
    for dimension in cps_flow_guards.DIMENSIONS:
        guard = cps_flow_guards.guard_expr(dimension, pl.col('empsame_b'), pl.col('actsame_b'))
        found = dict(population.select(guard.alias('state')).group_by('state').len().iter_rows())
        states[dimension] = {state: found.get(state, 0)
                             for state in cps_flow_targets.GUARD_STATES}
    return states


def _reason_counts(frame: pl.DataFrame) -> dict[str, int]:
    '''Count each entry of the `inclusion_reasons` lists over every row of a product frame.'''
    entries = frame.select(pl.col('inclusion_reasons').explode().drop_nulls()).to_series()
    return dict(sorted(entries.value_counts().iter_rows()))


def _memberships(frames: dict[tuple[str, str], pl.DataFrame]) -> pl.DataFrame:
    '''The `<product>:<dimension>:<policy>` variants that admit each monthly link.'''
    found = []
    for (product, dimension), frame in frames.items():
        eligible = frame.filter(pl.col('reason') == 'eligible')
        for policy in POLICIES[product]:
            rows = eligible if policy == 'sensitivity' else eligible.filter('strict')
            found.append(rows.select(*LINK_KEYS, pl.lit(f'{product}:{dimension}:{policy}')
                                     .alias('products')))
    return pl.concat(found).group_by(LINK_KEYS).agg(pl.col('products'))


def _asec_records(frames: dict[str, pl.DataFrame], weights: pl.LazyFrame) -> dict:
    '''Each dimension's eligible ASEC persons with `ASECWT` and `REPWTP1`-`REPWTP160`.

    The 160 replicate columns are collected only for the eligible rows of either dimension.
    '''
    eligible = {dimension: frame.filter(pl.col('reason') == 'eligible')
                for dimension, frame in frames.items()}
    rows = pl.concat([frame.select('source_row') for frame in eligible.values()]).unique()
    replicates = weights.join(rows.lazy(), on='source_row', how='semi').select(
        'source_row', pl.col('ASECWT').alias('weight'),
        *(pl.col(f'REPWTP{number}').alias(name)
          for number, name in enumerate(cps_flow_estimation.REPLICATE_WEIGHTS, start=1))
    ).collect()
    return {dimension: frame.select('source_row', 'unit_a', 'unit_b', 'period').join(
        replicates, on='source_row', how='left', validate='1:1', maintain_order='left')
        .drop('source_row') for dimension, frame in eligible.items()}


def _estimates(monthly: dict[tuple[str, str], pl.DataFrame],
               asec: dict[str, pl.DataFrame]) -> dict[Variant, cps_flow_estimation.Estimates]:
    '''Estimate every variant. Each monthly product draws its households once (OD6).'''
    found = {}
    for product in cps_flow_estimation.MONTHLY_PRODUCTS:
        records = {}
        for dimension in cps_flow_guards.DIMENSIONS:
            eligible = monthly[(product, dimension)].filter(pl.col('reason') == 'eligible')
            for policy in POLICIES[product]:
                rows = eligible if policy == 'sensitivity' else eligible.filter('strict')
                records[Variant(product, dimension, policy)] = rows.select(
                    'CPSID', 'unit_a', 'unit_b', _monthly_period().alias('period'),
                    pl.col('weight_a').alias('weight'))
        # An eligible link has a positive weight, so the union over every variant is the
        # product's list of households with an eligible, positive-weight link.
        households = sorted(set().union(*(frame['CPSID'] for frame in records.values())))
        draws = cps_flow_estimation.household_draws(households)
        for variant, rows in records.items():
            found[variant] = cps_flow_estimation.estimate_monthly(rows, variant, draws)
    for dimension in cps_flow_guards.DIMENSIONS:
        variant = Variant('asec_retro', dimension, 'sensitivity')
        found[variant] = cps_flow_estimation.estimate_asec(asec[dimension], variant)
    return found


def _products(selected: cps_flow_inputs.SelectedInputs, scratch: Path,
              run_id: str) -> _Products:
    '''Compute every table and the report from the selected inputs.

    The decompressed CSVs exist only inside `weighted_sources`, and everything that reads them
    is collected there. The caller may remove `scratch` when this returns.
    '''
    units = _units(selected)
    ddi = {'monthly': cps_flow_inputs.check_ddi('monthly', selected.monthly.ddi),
           'asec': cps_flow_inputs.check_ddi('asec', selected.asec.ddi)}
    value_classes = _value_classes(selected, units)
    with cps_flow_weights.weighted_sources(selected, scratch) as weighted:
        panel = cps_flow_linkage.monthly_panel(
            pl.scan_parquet(selected.monthly.parquet).select(PANEL_COLUMNS)).collect().lazy()
        links = _links(panel, weighted.monthly)
        persons = _persons(selected, weighted.asec)
        one_month = links.filter(pl.col('link_type') == ONE_MONTH)
        _refuse_outside(one_month.select(_monthly_period()).to_series(), LINK_MONTHS,
                        'a one-month link falls outside the frozen link months')
        _refuse_outside(persons['period'], ASEC_PERIODS,
                        'an ASEC year falls outside the frozen periods')
        monthly, asec = {}, {}
        for product in cps_flow_guards.PRODUCTS:
            for dimension in cps_flow_guards.DIMENSIONS:
                if product == 'asec_retro':
                    asec[dimension] = cps_flow_guards.product_frame(
                        persons.lazy().drop('weight'), product, dimension,
                        units=units).collect()
                else:
                    monthly[(product, dimension)] = cps_flow_guards.product_frame(
                        one_month.lazy().select(FRAME_COLUMNS), product, dimension,
                        units=units).collect()
        asec_records = _asec_records(asec, weighted.asec)
    frames = {**{f'{product}:{dimension}': frame
                 for (product, dimension), frame in monthly.items()},
              **{f'asec_retro:{dimension}': frame for dimension, frame in asec.items()}}
    estimates = _estimates(monthly, asec_records)
    statuses = dict(one_month.group_by('weight_status').len().iter_rows())
    parts = {
        'value_classes': value_classes,
        'links': cps_flow_linkage.link_counts(panel),
        'weights': {status: statuses.get(status, 0)
                    for status in cps_flow_targets.WEIGHT_STATUSES},
        'funnels': {name: cps_flow_guards.funnel(frame.lazy(), *name.split(':'))
                    for name, frame in frames.items()},
        'guards': {
            'states': _guard_states(links),
            'noise_after_duty_change': int(
                monthly[('monthly_ee', 'industry')][cps_flow_guards.NOISE].sum()),
            'source_exceptions': cps_flow_guards.guard_source_exceptions(panel.select(
                pl.col('MISH').alias('mish_b'), pl.col('EMPSAME').alias('empsame_b'))),
            'usable_share': cps_flow_guards.usable_guard_share(one_month.lazy()),
        },
        'evidence': {
            'monthly': {f'{product}:{dimension}': _reason_counts(frame)
                        for (product, dimension), frame in monthly.items()},
            'asec_flags': cps_flow_guards.asec_flag_counts(persons.lazy()),
        },
        'specials': {name: int(frame['special'].sum()) for name, frame in frames.items()},
    }
    pairs = links.join(_memberships(monthly), on=LINK_KEYS, how='left', validate='1:1',
                       maintain_order='left').with_columns(
        pl.col('products').fill_null(pl.lit([], dtype=pl.List(pl.String))))
    tables = {
        'cps_job_flows': cps_flow_targets.target_rows(estimates, units).sort(
            target_contract.TARGET_KEY_COLUMNS),
        'cps_category_units': units,
        'cps_flow_support': cps_flow_targets.support_table(estimates),
        'cps_flow_replicates': cps_flow_targets.replicates_table(estimates),
        'cps_flow_diagnostics': cps_flow_targets.diagnostics_table(parts),
        'cps_linked_pairs': cps_flow_targets.linked_pairs_table(pairs),
    }
    report = _normalized(cps_flow_targets.build_report(run_id=run_id, parts=parts,
                                                       tables=tables))
    return _Products({name: tables[name] for name in TABLES}, report, ddi)


def _write_tables(staging: Path, tables: dict[str, pl.DataFrame]) -> None:
    '''Write each table, then compare the serialized frames with the results in order.'''
    for name in TABLES:
        file = staging / (name + '.parquet')
        if name == 'cps_job_flows':
            target_contract.write_targets(tables[name], file)
        else:
            tables[name].write_parquet(file)
    for name in TABLES:
        serialized = pl.scan_parquet(staging / (name + '.parquet'))
        if not _same(ordered_equal(serialized, tables[name].lazy())):
            raise ValueError(f'{name}: serialized table differs from the in-memory result')


def _recheck(selected: cps_flow_inputs.SelectedInputs, software: dict) -> None:
    '''Refuse any change of the six pinned inputs or the software since the build began.'''
    selected.verify()
    if freeze_software() != software:
        raise ValueError('executing software changed before publication')


def build(data_dir: Path, run_id: str, request: cps_flow_inputs.InputRequest) -> dict:
    '''Build, check and publish one immutable bundle under `run_directory(data_dir, run_id)`.

    An existing final or `.part` name fails before anything is written. The result names the
    run, its directory and the SHA-256 of its `outputs.json`, the detached pin.
    '''
    data_dir = Path(data_dir)
    final, staging = target_io.stage(run_directory(data_dir, run_id).parent, run_id, data_dir)
    try:
        scratch = staging / '.scratch'
        scratch.mkdir()
        software = freeze_software()
        selected = cps_flow_inputs.select_inputs(data_dir, request)
        products = _products(selected, scratch, run_id)
        _write_tables(staging, products.tables)
        geography_references.safe_path(scratch, data_dir)
        shutil.rmtree(scratch)
        inputs = _inputs(run_id, selected, products.ddi, software, _execution())
        target_io.write_json(staging / 'inputs.json', inputs)
        target_io.write_json(staging / 'report.json', products.report)
        _recheck(selected, software)
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


def _recorded_request(inputs: dict) -> cps_flow_inputs.InputRequest:
    '''The six selected IDs and pins that `inputs.json` records.'''
    if set(inputs) != INPUT_FIELDS:
        raise ValueError('recorded inputs are malformed')
    fields = {}
    try:
        for upstream, (id_field, pin_field, name) in cps_flow_inputs.PINNED.items():
            record = inputs['upstream'][upstream]
            if name == cps_flow_inputs.OUTPUTS_FILE:
                fields[id_field], fields[pin_field] = record['run_id'], record['outputs_sha256']
            else:
                fields[id_field] = record['reference_id']
                fields[pin_field] = record['receipt_sha256']
    except (KeyError, TypeError):
        raise ValueError('recorded inputs are malformed') from None
    if not all(isinstance(value, str) for value in fields.values()):
        raise ValueError('recorded inputs are malformed')
    return cps_flow_inputs.InputRequest(**fields)


@contextmanager
def _verification_scratch(data_dir: Path):
    '''A fresh temporary directory outside `data_dir`, under the resolved OS temp root.'''
    root = Path(tempfile.gettempdir()).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='cps-job-flows-verify-', dir=root) as temporary:
        scratch = Path(temporary)
        geography_references.safe_path(scratch, root)
        if scratch.is_relative_to(Path(data_dir).resolve()):
            raise ValueError('verification scratch is inside the data directory')
        yield scratch


def verify_bundle(directory: Path, data_dir: Path, *, expected_outputs_sha256: str) -> dict:
    '''Authenticate a published bundle by its detached pin, then recompute it offline.

    The pin, the exact file set and the inventory are checked before any recomputation. The
    recorded software must equal the executing software. Every table is recomputed from the
    six recorded IDs and pins in a temporary directory outside `data_dir` and compared in
    physical order. Then the report and the inputs (with their recorded execution) must
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
    outputs = _read_json(outputs_file)
    target_io.verify_inventory(directory, outputs, set(FILES))
    if outputs != target_io.inventory(directory, list(FILES)):
        raise ValueError('output inventory records differ')

    inputs = _read_json(directory / 'inputs.json')
    report = _read_json(directory / 'report.json')
    request = _recorded_request(inputs)
    if inputs['run_id'] != directory.name:
        raise ValueError('recorded run ID differs from the directory')
    if inputs['contracts'] != CONTRACTS or report.get('contracts') != CONTRACTS:
        raise ValueError('contract versions differ')
    software = freeze_software()
    if inputs['software'] != software:
        raise ValueError('executing software differs from the build')

    selected = cps_flow_inputs.select_inputs(data_dir, request)
    with _verification_scratch(data_dir) as scratch:
        products = _products(selected, scratch, directory.name)
    for name in TABLES:
        published = pl.scan_parquet(directory / (name + '.parquet'))
        if not _same(ordered_equal(published, products.tables[name].lazy())):
            raise ValueError(f'{name}: published table differs from the recomputation')
    if products.report != report:
        raise ValueError('published report differs from the recomputation')
    if _inputs(directory.name, selected, products.ddi, software, inputs['execution']) != inputs:
        raise ValueError('recorded inputs differ from the recomputation')
    return {
        'run_id': directory.name,
        'outputs_sha256': expected_outputs_sha256,
        'rows': {name: report['tables'][name]['rows'] for name in TABLES},
    }


def compare_runs(first: Path, second: Path) -> dict:
    '''Compare two published bundles table by table, in order, and their reports.

    Each bundle must match its own `outputs.json` inventory. The reports are compared without
    their `run_id`. `inputs.json`, which holds the run ID and the execution record, is not
    compared. Equality establishes replay, not trust: neither bundle is authenticated by a
    detached pin here.
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
    reports = [{key: value for key, value in _read_json(directory / 'report.json').items()
                if key != 'run_id'} for directory in (first, second)]
    report_equal = reports[0] == reports[1]
    return {
        'equal': report_equal and all(_same(comparison) for comparison in tables.values()),
        'tables': tables,
        'report_equal': report_equal,
        'trust_established': False,
    }
