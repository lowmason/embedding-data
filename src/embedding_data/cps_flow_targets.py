'''Target rows, companion tables and the report of the CPS job-change flows.

These are pure functions over the pieces that earlier modules compute. `target_rows` turns the
estimates of every variant into `targets-v1` rows, with the frozen metadata and flag registry.
The companion tables have fixed ordered schemas (`COMPANION_SCHEMAS`, contract
`cps-job-flows-v1`) and fixed sort orders. `build_report` returns counts and shares only: it
never holds a `CPSIDV`, a `CPSID`, a household or a row.

`parts`, the computed pieces of a build, is a dict with these keys:

- `value_classes`: `count_value_classes` entries, merged over both files, keyed
  `<file>/<field>`.
- `links`: the `link_counts` frame.
- `weights`: the one-month link counts `{'null': n, 'zero': n, 'positive': n}`.
- `funnels`: `<product>:<dimension>` to the `funnel` frame of that product frame.
- `guards`: `states` (`<dimension>` to `{'changed': n, 'same': n, 'unusable': n}`),
  `noise_after_duty_change` (a count), `source_exceptions` (the `guard_source_exceptions` count
  over the monthly panel rows renamed to `mish_b` and `empsame_b`) and `usable_share` (the
  `usable_guard_share` result).
- `evidence`: `monthly` (`<product>:<dimension>` to inclusion reason to count) and `asec_flags`
  (the `asec_flag_counts` result).
- `specials`: `<product>:<dimension>` to the number of rows with a special end.

Only first-exclusion funnels are `exclusive`: they partition a source total. Every other
diagnostic count may overlap another and is labeled so.
'''

import polars as pl

from embedding_data import target_contract
from embedding_data.cps_flow_estimation import (
    MONTHLY_PRODUCTS,
    REPLICATES_SCHEMA,
    SUPPORT_SCHEMA,
    Estimates,
    Variant,
)
from embedding_data.cps_flow_guards import EMPLOYED, guard_expr
from embedding_data.cps_flow_linkage import COUNT_COLUMNS, ONE_MONTH, TWO_MONTH, VALUE_CLASSES
from embedding_data.cps_flow_units import UNIT_SCHEMA, UNIT_TYPES, VINTAGES
from embedding_data.target_contract import TARGET_SCHEMA

SCHEMA_VERSION = 'cps-job-flows-v1'
CONTRACTS = {'bundle': SCHEMA_VERSION, 'references': 'cps-job-flows-references-v1',
             'targets': target_contract.SCHEMA_VERSION}
SOURCE = 'cps'
FAMILY = 'job_change_flow'
SAMPLE_SETS = {'monthly_ee': 'cps-basic-2025-01-to-2026-09',
               'monthly_ue': 'cps-basic-2025-01-to-2026-09',
               'asec_retro': 'cps-asec-2025-2026'}
SIZE_GATE_FLAG = 'size_gate_pending'
PRODUCT_FLAGS = {'monthly_ee': 'bootstrap_approximate', 'monthly_ue': 'bootstrap_approximate',
                 'asec_retro': 'unguarded_upper_bound'}
SPECIAL_FLAG = 'special_military'
FLAG_REGISTRY = tuple(sorted({SIZE_GATE_FLAG, SPECIAL_FLAG, *PRODUCT_FLAGS.values()}))
SPECIAL_STATUS = 'special_military'
TARGET_STATUSES = ('mapped', SPECIAL_STATUS)
BOOTSTRAP, REPLICATE, NO_SE = 'bootstrap', 'replicate', 'none'
DIMENSION_OF_UNIT_TYPE = {unit_type: dimension for dimension, unit_type in UNIT_TYPES.items()}
STRINGS = pl.List(pl.String)

DIAGNOSTICS_SCHEMA = {
    'topic': pl.String, 'product': pl.String, 'dimension': pl.String, 'policy': pl.String,
    'period': pl.String, 'reason': pl.String, 'exclusive': pl.Boolean, 'count': pl.UInt64,
    'count_cpsidp': pl.UInt64,
}
LINKED_PAIRS_SCHEMA = {
    'CPSIDV': pl.Int64, 'CPSID': pl.Int64, 'month_a': pl.String, 'month_b': pl.String,
    'link_type': pl.String, 'source_row_a': pl.UInt64, 'source_row_b': pl.UInt64,
    'mish_a': pl.Int64, 'mish_b': pl.Int64, 'empstat_a': pl.Int64, 'empstat_b': pl.Int64,
    'ind_a': pl.String, 'ind_b': pl.String, 'occ_a': pl.String, 'occ_b': pl.String,
    'qempstat_a': pl.Int64, 'qempstat_b': pl.Int64, 'qind_a': pl.Int64, 'qind_b': pl.Int64,
    'qocc_a': pl.Int64, 'qocc_b': pl.Int64, 'empsame_b': pl.Int64, 'actsame_b': pl.Int64,
    'guard_industry': pl.String, 'guard_occupation': pl.String, 'weight_a': pl.Float64,
    'weight_status': pl.String, 'products': STRINGS,
}
COMPANION_SCHEMAS = {
    'cps_category_units': dict(UNIT_SCHEMA),
    'cps_flow_support': dict(SUPPORT_SCHEMA),
    'cps_flow_replicates': dict(REPLICATES_SCHEMA),
    'cps_flow_diagnostics': dict(DIAGNOSTICS_SCHEMA),
    'cps_linked_pairs': dict(LINKED_PAIRS_SCHEMA),
}
LINKED_PAIRS_SORT = ['month_a', 'link_type', 'CPSIDV']
REPLICATES_SORT = ['product', 'dimension', 'policy', 'unit_a', 'unit_b', 'replicate']
WEIGHT_STATUSES = ('null', 'zero', 'positive')
GUARD_STATES = ('changed', 'same', 'unusable')
X_CHECKS = ('equal', 'strict_subset', 'not_delivered_no_pums_list')
PERCENTILES = (10, 25, 50, 75, 90)
THRESHOLDS = (1, 2, 5, 10, 20, 30, 50, 100)
V11_STATEMENT = 'zero unparseable CPS values'
NOT_APPLICABLE = 'not_applicable'


def _registry_units(units: pl.DataFrame, unit_type: str) -> tuple[pl.Series, pl.Series]:
    '''Return the codes a target may use and the codes of the specials, for one unit type.'''
    rows = units.filter(pl.col('unit_type') == unit_type)
    allowed = rows.filter(pl.col('status').is_in(TARGET_STATUSES))['code']
    return allowed, rows.filter(pl.col('status') == SPECIAL_STATUS)['code']


def _variant_rows(variant: Variant, found: Estimates, units: pl.DataFrame) -> pl.DataFrame:
    rows = found.targets
    labels = rows.select('product', 'dimension', 'policy').unique().rows()
    if labels != [(variant.product, variant.dimension, variant.policy)]:
        raise ValueError('estimates do not carry the labels of their variant')
    unit_type = UNIT_TYPES[variant.dimension]
    allowed, specials = _registry_units(units, unit_type)
    known = (pl.col('unit_a').is_in(allowed.implode())
             & pl.col('unit_b').is_in(allowed.implode()))
    if not rows.select(known.all()).item():
        raise ValueError('a category unit is not a mapped or special unit of the registry')
    special = (pl.col('unit_a').is_in(specials.implode())
               | pl.col('unit_b').is_in(specials.implode()))
    if variant.policy == 'strict' and rows.select(special.any()).item():
        raise ValueError('a strict row has a special end')
    plain = [SIZE_GATE_FLAG, PRODUCT_FLAGS[variant.product]]
    flags = (pl.when(special).then(pl.lit(sorted([*plain, SPECIAL_FLAG]), dtype=STRINGS))
             .otherwise(pl.lit(sorted(plain), dtype=STRINGS)))
    method = BOOTSTRAP if variant.product in MONTHLY_PRODUCTS else REPLICATE
    return rows.select(
        pl.lit(SOURCE).alias('source'), pl.lit(FAMILY).alias('family'),
        pl.lit(unit_type).alias('unit_a_type'),
        pl.concat_str(pl.lit(f'feature:{unit_type}:'), 'unit_a').alias('unit_a'),
        pl.lit(unit_type).alias('unit_b_type'),
        pl.concat_str(pl.lit(f'feature:{unit_type}:'), 'unit_b').alias('unit_b'),
        'measure', 'value', 'se',
        pl.when(pl.col('se').is_not_null()).then(pl.lit(method)).otherwise(pl.lit(NO_SE))
        .alias('se_method'),
        'n_unweighted', 'n_weighted',
        pl.lit(SAMPLE_SETS[variant.product]).alias('sample_set'),
        pl.lit(VINTAGES[variant.dimension]).alias('vintage'),
        pl.lit(f'{variant.product}:{variant.policy}').alias('universe'),
        flags.alias('flags')).cast(TARGET_SCHEMA)


def target_rows(estimates: dict[Variant, Estimates], units: pl.DataFrame) -> pl.DataFrame:
    '''Return the `targets-v1` rows of every variant, with the frozen metadata and flags.

    `n_unweighted` and `n_weighted` come from the estimates unchanged. `flags` hold
    `size_gate_pending`, then `bootstrap_approximate` for a monthly product or
    `unguarded_upper_bound` for `asec_retro`, and `special_military` on a row with a special
    end of the registry, sorted. A category the registry does not hold as mapped or special,
    estimates that carry other labels than their variant, and a special end in a `strict`
    variant are refused.
    '''
    return pl.concat([_variant_rows(variant, found, units)
                      for variant, found in estimates.items()])


def support_table(estimates: dict[Variant, Estimates]) -> pl.DataFrame:
    '''Return the support rows of every variant, sorted by all columns in order.'''
    return pl.concat([found.support for found in estimates.values()]).sort(
        list(SUPPORT_SCHEMA))


def replicates_table(estimates: dict[Variant, Estimates]) -> pl.DataFrame:
    '''Return the replicate rows of every variant, sorted by variant, cell and replicate.'''
    return pl.concat([found.replicates for found in estimates.values()]).sort(REPLICATES_SORT)


def _month_pair(month_a: str, month_b: str) -> str:
    return f'{month_a}>{month_b}'


def _value_class_rows(value_classes: dict) -> list[tuple]:
    return [('value_class', None, None, None, 'all', f'{field}/{name}', False, counts[name], None)
            for field, counts in value_classes.items() for name in VALUE_CLASSES]


def _link_rows(links: pl.DataFrame) -> list[tuple]:
    rows = []
    for month_a, month_b, link_type, cpsidv, cpsidp, other in links.select(
            COUNT_COLUMNS).iter_rows():
        period = _month_pair(month_a, month_b)
        rows.append(('links', None, None, None, period, link_type, False, cpsidv, cpsidp))
        rows.append(('links', None, None, None, period, f'other_gap_matches_{link_type}',
                     False, other, None))
    return rows


def _funnel_rows(funnels: dict[str, pl.DataFrame]) -> list[tuple]:
    rows = []
    for name, frame in funnels.items():
        product, dimension = name.split(':')
        rows.extend(('funnel', product, dimension, None, 'all', reason, True, count, None)
                    for reason, count in frame.iter_rows())
    return rows


def _guard_rows(guards: dict) -> list[tuple]:
    rows = [('guard', 'monthly_ee', dimension, None, 'all', state, False, counts[state], None)
            for dimension, counts in guards['states'].items() for state in GUARD_STATES]
    rows.append(('guard', 'monthly_ee', 'industry', None, 'all', 'noise_after_duty_change',
                 False, guards['noise_after_duty_change'], None))
    rows.append(('guard', None, None, None, 'all', 'empsame_in_mish_1_or_5', False,
                 guards['source_exceptions'], None))
    return rows


def _evidence_rows(evidence: dict) -> list[tuple]:
    rows = []
    for name, reasons in evidence['monthly'].items():
        product, dimension = name.split(':')
        rows.extend(('evidence', product, dimension, None, 'all', reason, False, count, None)
                    for reason, count in reasons.items())
    for variable, by_empstat in evidence['asec_flags'].items():
        for empstat, by_value in by_empstat.items():
            rows.extend(('evidence', 'asec_retro', None, None, 'all',
                         f'{variable}/{empstat}/{value}', False, count, None)
                        for value, count in by_value.items())
    return rows


def _special_rows(specials: dict[str, int]) -> list[tuple]:
    rows = []
    for name, count in specials.items():
        product, dimension = name.split(':')
        rows.append(('special', product, dimension, None, 'all', 'special_end', False, count,
                     None))
    return rows


def diagnostics_table(parts: dict) -> pl.DataFrame:
    '''Return the aggregate diagnostics, sorted by all columns in order.

    One row for each count of `parts` (see the module text). Funnel rows are `exclusive`: they
    sum to the source total of their product and dimension. Every other row is not. A `links`
    row counts the links of a month pair and link type on `CPSIDV` and on `CPSIDP`, and one
    more row counts the `CPSIDV` matches that fail the `MISH` rule.
    '''
    rows = [
        *_value_class_rows(parts['value_classes']), *_link_rows(parts['links']),
        *(('weight', None, None, None, 'all', status, False, parts['weights'][status], None)
          for status in WEIGHT_STATUSES),
        *_funnel_rows(parts['funnels']), *_guard_rows(parts['guards']),
        *_evidence_rows(parts['evidence']), *_special_rows(parts['specials'])]
    return pl.DataFrame(rows, schema=DIAGNOSTICS_SCHEMA, orient='row').sort(
        list(DIAGNOSTICS_SCHEMA))


def linked_pairs_table(links: pl.DataFrame) -> pl.DataFrame:
    '''Return the person-level monthly links in the fixed columns, sorted.

    `links` holds the `LINK_COLUMNS` of `monthly_links`, plus `weight_a` (Decimal or Float64,
    null when the link has no weight), `weight_status` and `products` (the
    `<product>:<dimension>:<policy>` memberships of each link). The two guards are read at
    the later month and are null unless the person is employed in both months, for every link
    type. `products` are sorted. Rows sort by `month_a`, `link_type` and `CPSIDV`. An
    undelivered `EMPSAME` or `ACTSAME` fails.
    '''
    employed = (pl.col('empstat_a').is_in(list(EMPLOYED))
                & pl.col('empstat_b').is_in(list(EMPLOYED)))
    guards = [pl.when(employed).then(
        guard_expr(dimension, pl.col('empsame_b'), pl.col('actsame_b')))
        .alias(f'guard_{dimension}') for dimension in UNIT_TYPES]
    return links.with_columns(
        *guards, pl.col('products').list.sort().alias('products')
    ).select(pl.col(name).cast(dtype) for name, dtype in LINKED_PAIRS_SCHEMA.items()).sort(
        LINKED_PAIRS_SORT)


def n_unweighted_distribution(targets: pl.DataFrame) -> dict:
    '''Describe `n_unweighted` over the `average_total` rows of one variant.

    Percentiles use the nearest-rank method: the value at rank `ceil(p * cells / 100)` of the
    sorted counts. `at_least` counts the cells with at least each threshold, with string keys.
    '''
    counts = sorted(targets.filter(pl.col('measure') == 'average_total')['n_unweighted']
                    .to_list())
    if not counts:
        raise ValueError('a distribution needs at least one average_total row')
    cells = len(counts)
    found = {'cells': cells, 'min': counts[0], 'max': counts[-1]}
    for percent in PERCENTILES:
        found[f'p{percent}'] = counts[-(-percent * cells // 100) - 1]
    found['at_least'] = {str(threshold): sum(count >= threshold for count in counts)
                         for threshold in THRESHOLDS}
    return found


def _distributions(targets: pl.DataFrame) -> dict:
    found = {}
    for (universe, unit_type), rows in targets.partition_by(
            'universe', 'unit_a_type', as_dict=True).items():
        product, policy = universe.split(':')
        found[f'{product}:{DIMENSION_OF_UNIT_TYPE[unit_type]}:{policy}'] = (
            n_unweighted_distribution(rows))
    return dict(sorted(found.items()))


def _linkage(links: pl.DataFrame) -> dict:
    found = {ONE_MONTH: {}, TWO_MONTH: {}}
    for month_a, month_b, link_type, cpsidv, cpsidp, other in links.select(
            COUNT_COLUMNS).iter_rows():
        found[link_type][_month_pair(month_a, month_b)] = {
            'cpsidv': cpsidv, 'cpsidp': cpsidp, 'other_gap_matches': other}
    return found


def _x_categories(units: pl.DataFrame) -> dict:
    found = dict(units.filter(pl.col('x_cross_check').is_not_null())
                 .group_by('x_cross_check').len().iter_rows())
    return {name: found.get(name, 0) for name in X_CHECKS}


def build_report(*, run_id: str, parts: dict, tables: dict[str, pl.DataFrame]) -> dict:
    '''Return `report.json`: counts and shares only, never a person, household or row.

    `tables` holds the six tables by name, `cps_job_flows` and `cps_category_units` among them.
    The `specials` are the specials of each file, field and year, from `special_by_year`.
    '''
    classes = parts['value_classes']
    share = parts['guards']['usable_share']
    return {
        'schema_version': SCHEMA_VERSION,
        'run_id': run_id,
        'contracts': dict(CONTRACTS),
        'v11': {'unparseable_values': 0, 'statement': V11_STATEMENT},
        'value_classes': {field: {name: counts[name] for name in VALUE_CLASSES}
                          for field, counts in classes.items()},
        'specials': {f'{field}/{year}': count for field, counts in classes.items()
                     for year, count in counts['special_by_year'].items()},
        'x_categories': _x_categories(tables['cps_category_units']),
        'linkage': _linkage(parts['links']),
        'weights': {status: parts['weights'][status] for status in WEIGHT_STATUSES},
        'funnels': {name: dict(frame.iter_rows()) for name, frame in parts['funnels'].items()},
        'usable_guard_share': {
            'monthly_ee:industry': share['industry'],
            'monthly_ee:occupation': share['occupation'],
            'monthly_ue': NOT_APPLICABLE, 'asec_retro': NOT_APPLICABLE},
        'guard_source_exceptions': {
            'empsame_in_mish_1_or_5': parts['guards']['source_exceptions']},
        'asec_flags_by_empstat': parts['evidence']['asec_flags'],
        'n_unweighted_distribution': _distributions(tables['cps_job_flows']),
        'tables': {name: {'rows': frame.height} for name, frame in sorted(tables.items())},
    }
