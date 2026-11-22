'''Stage 14 vendor-link target (O6): supplier and buyer firm shares between NAICS 2022
national industries, with marginal and support companions.

`P` holds the pairs with status `eligible`. The intra-group sensitivity `P+` adds the pairs
with status `intra_group` whose prime and subcontractor are both `eligible` firms. In a cell
`(s, d)`, `s` is the subcontractor's node (the supplier industry, `unit_a`) and `d` is the
prime's node (the buyer industry, `unit_b`). `S(s,d)` counts the cell's distinct
subcontractors, `B(s,d)` its distinct primes and `L(s,d)` its pairs. `n_sup(s)` counts the
distinct subcontractors in `s` and `n_buy(d)` the distinct primes in `d`. Each firm counts
once in each count, however many reports, pairs, years or dollars it has, and a firm in both
roles counts in each role. Each cell with a pair in `P` gives a `supplier_share` row
(`S / n_sup(s)`) and a `buyer_share` row (`B / n_buy(d)`), the diagonal included. A cell or
a node seen only under `P+` is not listed. Every refusal is a `ValueError` with a fixed
message.
'''

from dataclasses import dataclass
from datetime import date

import polars as pl

from embedding_data.target_contract import TARGET_KEY_COLUMNS, TARGET_SCHEMA, validate_targets
from embedding_data.usaspending_raw import WINDOW
from embedding_data.vendor_link_pairs import (
    AMOUNT_TYPE,
    FIRM_STATUSES,
    PAIR_SCHEMA,
    PAIR_STATUSES,
)

CONTRACT = 'vendor-links-v1'
TOLERANCE = 1e-12
SIZE_LABEL = 'size_gate_pending'
INTRA_LABEL = 'numerator:intra_group_sensitivity:true'
UNIVERSE = (
    'USAspending.gov contract subaward reports (FFATA subcontracts) with subaward action '
    'dates in federal fiscal years 2024–2026, downloaded under snapshot {snapshot}, joined '
    'by UEI to the SAM.gov public monthly entity extract of {month}. The population is '
    'federal prime contractors and the subcontractors they report, not a frame of firms or '
    'of business-to-business trade. A link is a distinct prime–subcontractor pair. Links '
    'within one corporate group, as the reported parent UEIs show, are excluded. Industries '
    "are each firm's self-reported primary NAICS 2022 code in SAM.gov at the extract date, "
    'not at the subaward date. Links, codes and amounts are self-reported and unvalidated.'
)
METADATA = dict(source='usaspending_sam', family='vendor_links',
                unit_a_type='naics_national_industry', unit_b_type='naics_national_industry',
                se_method='none', sample_set='usaspending_subcontracts_fy2024_2026',
                vintage='naics=2022')
MEASURES = ('supplier_share', 'buyer_share')
MARGINAL_SCHEMA = {'node_id': pl.String, 'n_suppliers': pl.UInt64, 'n_buyers': pl.UInt64,
                   'n_supplier_pairs': pl.UInt64, 'n_buyer_pairs': pl.UInt64,
                   'n_suppliers_partial': pl.UInt64, 'n_buyers_partial': pl.UInt64,
                   'n_suppliers_including_intra_group': pl.UInt64,
                   'n_buyers_including_intra_group': pl.UInt64}
SUPPORT_SCHEMA = {'unit_a': pl.String, 'unit_b': pl.String, 's_suppliers': pl.UInt64,
                  'b_buyers': pl.UInt64, 'l_pairs': pl.UInt64, 'l_fy2024': pl.UInt64,
                  'l_fy2025': pl.UInt64, 'l_fy2026': pl.UInt64,
                  's_including_intra_group': pl.UInt64, 'b_including_intra_group': pl.UInt64,
                  'l_including_intra_group': pl.UInt64, 'amount_sum': AMOUNT_TYPE,
                  'n_reports': pl.UInt64}
_INTRA_GROUP, _PRIME_INELIGIBLE, _SUB_INELIGIBLE, _ELIGIBLE = PAIR_STATUSES[1:]
_FIRM_ELIGIBLE = FIRM_STATUSES[-1]
# Each role: the counted firms, the pair-count prefix, the pair-table column prefix, and the
# pair status that excludes a pair of this role's firm because its counterparty is ineligible.
_ROLES = (('suppliers', 'supplier', 'sub', _PRIME_INELIGIBLE),
          ('buyers', 'buyer', 'prime', _SUB_INELIGIBLE))
_CELL = ['unit_a', 'unit_b']
_BY_CELL = dict(unit_a='sub_node_id', unit_b='prime_node_id')
_COUNTED = (1, 2, 3, 5)
_MANY = 10


@dataclass(frozen=True)
class VendorLinks:
    targets: pl.DataFrame
    marginals: pl.DataFrame
    support: pl.DataFrame
    report: dict


def _require_pairs(pair_table: pl.DataFrame) -> None:
    if list(pair_table.schema.items()) != list(PAIR_SCHEMA.items()):
        raise ValueError('vendor-link pair table schema differs')


def _sets(pair_table: pl.DataFrame) -> tuple[pl.LazyFrame, pl.LazyFrame]:
    '''`P` and `P+`.'''
    status = pl.col('pair_status')
    both = (pl.col('prime_status') == _FIRM_ELIGIBLE) & (pl.col('sub_status') == _FIRM_ELIGIBLE)
    pairs = pair_table.lazy()
    return (pairs.filter(status == _ELIGIBLE),
            pairs.filter((status == _ELIGIBLE) | ((status == _INTRA_GROUP) & both)))


def _cast(frame: pl.LazyFrame, schema: dict) -> pl.LazyFrame:
    return frame.select(pl.col(name).cast(dtype) for name, dtype in schema.items())


def _firms(side: str) -> pl.Expr:
    return pl.col(f'{side}_uei').n_unique()


def _support(eligible: pl.LazyFrame, sensitivity: pl.LazyFrame) -> pl.LazyFrame:
    '''One row per cell of `P`, sorted by `unit_a` and `unit_b`.'''
    headline = eligible.group_by(**_BY_CELL).agg(
        s_suppliers=_firms('sub'), b_buyers=_firms('prime'), l_pairs=pl.len(),
        **{f'l_fy{year}': (pl.col(f'n_fy{year}') > 0).sum() for year in WINDOW},
        amount_sum=pl.col('amount_sum').sum(), n_reports=pl.col('n_reports').sum())
    wider = sensitivity.group_by(**_BY_CELL).agg(
        s_including_intra_group=_firms('sub'), b_including_intra_group=_firms('prime'),
        l_including_intra_group=pl.len())
    return _cast(headline.join(wider, on=_CELL, how='left'), SUPPORT_SCHEMA).sort(_CELL)


def _marginals(pair_table: pl.DataFrame, eligible: pl.LazyFrame,
               sensitivity: pl.LazyFrame) -> pl.LazyFrame:
    '''One row per node with a subcontractor or a prime in `P`, sorted by `node_id`.'''
    nodes = pl.concat([eligible.select(node_id=f'{side}_node_id') for *_, side, _ in _ROLES])
    table = nodes.unique()
    for firms, pairs, side, excluded in _ROLES:
        by_node = dict(node_id=f'{side}_node_id')
        uei = f'{side}_uei'
        excluded_firms = pair_table.lazy().filter(pl.col('pair_status') == excluded).select(uei)
        counts = (
            eligible.group_by(**by_node).agg(**{f'n_{firms}': _firms(side),
                                                f'n_{pairs}_pairs': pl.len()}),
            eligible.join(excluded_firms, on=uei, how='semi')
            .group_by(**by_node).agg(**{f'n_{firms}_partial': _firms(side)}),
            sensitivity.group_by(**by_node).agg(
                **{f'n_{firms}_including_intra_group': _firms(side)}),
        )
        for count in counts:
            table = table.join(count, on='node_id', how='left')
    return (_cast(table.with_columns(pl.exclude('node_id').fill_null(0)), MARGINAL_SCHEMA)
            .sort('node_id'))


def _companions(pair_table: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    '''The marginals and the support of a pair table.'''
    eligible, sensitivity = _sets(pair_table)
    return (_marginals(pair_table, eligible, sensitivity).collect(),
            _support(eligible, sensitivity).collect())


def _flags(widened: pl.Expr) -> pl.Expr:
    '''`INTRA_LABEL` when `widened`, then `SIZE_LABEL`. The two sort in this order.'''
    return (pl.concat_list(pl.when(widened).then(pl.lit(INTRA_LABEL)), pl.lit(SIZE_LABEL))
            .list.drop_nulls())


def _targets(support: pl.DataFrame, marginals: pl.DataFrame, universe: str) -> pl.DataFrame:
    '''Two rows per support cell, sorted by `TARGET_KEY_COLUMNS`.'''
    cells = (support.lazy()
             .join(marginals.lazy().select(unit_a='node_id', _n_sup='n_suppliers'),
                   on='unit_a', how='left')
             .join(marginals.lazy().select(unit_b='node_id', _n_buy='n_buyers'),
                   on='unit_b', how='left'))
    rows = []
    for measure, count, wider, denominator in (
            ('supplier_share', 's_suppliers', 's_including_intra_group', '_n_sup'),
            ('buyer_share', 'b_buyers', 'b_including_intra_group', '_n_buy')):
        n = pl.col(count)
        rows.append(cells.select(
            *_CELL, *[pl.lit(value).alias(key) for key, value in METADATA.items()],
            measure=pl.lit(measure), value=n / pl.col(denominator),
            se=pl.lit(None, dtype=pl.Float64), n_unweighted=n,
            n_weighted=n.cast(pl.Float64), universe=pl.lit(universe),
            flags=_flags(pl.col(wider) != n)))
    return _cast(pl.concat(rows), TARGET_SCHEMA).sort(TARGET_KEY_COLUMNS).collect()


def _distribution(values: pl.Series) -> dict:
    '''Order statistics of positive counts, and how many equal 1, 2, 3 and 5 or reach 10.'''
    value = pl.col(values.name)
    return values.to_frame().select(
        count=pl.len(), min=value.min(),
        p25=value.quantile(0.25, interpolation='nearest'), median=value.median(),
        p75=value.quantile(0.75, interpolation='nearest'),
        p90=value.quantile(0.90, interpolation='nearest'), max=value.max(),
        **{str(count): (value == count).sum() for count in _COUNTED},
        **{f'{_MANY}+': (value >= _MANY).sum()},
    ).row(0, named=True)


def _per_firm(eligible: pl.DataFrame, side: str, other: str) -> pl.Series:
    '''For each firm of one role in `P`, its distinct counterparties.'''
    return eligible.group_by(f'{side}_uei').agg(n=_firms(other))['n']


def _report(eligible: pl.DataFrame, sensitivity: pl.DataFrame, support: pl.DataFrame,
            targets: pl.DataFrame) -> dict:
    def both(count):
        return {'eligible': count(eligible), 'including_intra_group': count(sensitivity)}

    wider_cells = sensitivity.select(**_BY_CELL).unique()
    diagonal = support.filter(pl.col('unit_a') == pl.col('unit_b'))
    diagonal_pairs = int(diagonal['l_pairs'].sum())
    return {
        'n_suppliers': both(lambda frame: frame['sub_uei'].n_unique()),
        'n_buyers': both(lambda frame: frame['prime_uei'].n_unique()),
        'n_pairs': both(lambda frame: frame.height),
        'diagonal': {'cells': diagonal.height, 'pairs': diagonal_pairs,
                     'share_of_pairs': (diagonal_pairs / eligible.height
                                        if eligible.height else None)},
        'cells_only_intra_group': wider_cells.join(support, on=_CELL, how='anti').height,
        'n_unweighted_distribution': {
            measure: _distribution(targets.filter(pl.col('measure') == measure)['n_unweighted'])
            for measure in MEASURES},
        'subcontractors_per_prime': _distribution(_per_firm(eligible, 'prime', 'sub')),
        'primes_per_subcontractor': _distribution(_per_firm(eligible, 'sub', 'prime')),
    }


def estimate(pair_table: pl.DataFrame, *, snapshot: date, month: str) -> VendorLinks:
    '''The vendor-link targets, marginals and support of a pair table, with their report.

    `pair_table` is `vendor_link_pairs.pairs` output. `snapshot` and `month` fill the
    universe statement. Targets are sorted by `TARGET_KEY_COLUMNS`, support rows by `unit_a`
    and `unit_b`, and marginal rows by `node_id`.
    '''
    _require_pairs(pair_table)
    marginals, support = _companions(pair_table)
    targets = _targets(support, marginals,
                       UNIVERSE.format(snapshot=snapshot.isoformat(), month=month))
    eligible, sensitivity = (frame.collect() for frame in _sets(pair_table))
    return VendorLinks(targets=targets, marginals=marginals, support=support,
                       report=_report(eligible, sensitivity, support, targets))


def _reject(frame: pl.DataFrame, condition: pl.Expr, message: str) -> None:
    '''Raise `message` when `condition` holds, or is unknown, for any row.'''
    if frame.select(condition.fill_null(True).any()).item():
        raise ValueError(message)


def _side(targets: pl.DataFrame, measure: str, prefix: str) -> pl.DataFrame:
    '''The rows of one measure, keyed by cell, with their columns prefixed.'''
    return targets.filter(pl.col('measure') == measure).select(
        *_CELL, **{f'{prefix}_count': 'n_unweighted', f'{prefix}_value': 'value',
                   f'{prefix}_weighted': 'n_weighted', f'{prefix}_flags': 'flags'})


def _check_cells(targets: pl.DataFrame, marginals: pl.DataFrame,
                 support: pl.DataFrame) -> None:
    '''Check each cell's two rows against its support row and its marginal rows.'''
    measure = pl.col('measure')
    rows = targets.group_by(_CELL).agg(*[(measure == name).sum().alias(name)
                                         for name in MEASURES], _rows=pl.len())
    _reject(rows, ~(pl.all_horizontal([pl.col(name) == 1 for name in MEASURES])
                    & (pl.col('_rows') == len(MEASURES))),
            'vendor-link cells lack exactly one row of each measure')
    cells = _side(targets, 'supplier_share', 's').join(_side(targets, 'buyer_share', 'b'),
                                                       on=_CELL)
    if not support.select(_CELL).sort(_CELL).equals(cells.select(_CELL).sort(_CELL)):
        raise ValueError('vendor-link support does not match the target cells')
    joined = (cells.join(support, on=_CELL)
              .join(marginals.select(unit_a='node_id', _n_sup='n_suppliers'), on='unit_a',
                    how='left')
              .join(marginals.select(unit_b='node_id', _n_buy='n_buyers'), on='unit_b',
                    how='left'))
    s, b, links = pl.col('s_count'), pl.col('b_count'), pl.col('l_pairs')
    _reject(joined, (pl.col('s_suppliers') != s) | (pl.col('b_buyers') != b),
            'vendor-link support does not match the target cells')
    _reject(joined, (s < 1) | (s > pl.col('_n_sup')) | (b < 1) | (b > pl.col('_n_buy')),
            'vendor-link firm counts are out of bounds')
    _reject(joined, (links < pl.max_horizontal(s, b)) | (links > s * b),
            'vendor-link pair counts are out of bounds')
    _reject(joined, ((pl.col('s_value') - s / pl.col('_n_sup')).abs() > TOLERANCE)
            | ((pl.col('b_value') - b / pl.col('_n_buy')).abs() > TOLERANCE),
            'vendor-link values differ from the ratios')
    _reject(joined, (pl.col('s_weighted') != s.cast(pl.Float64))
            | (pl.col('b_weighted') != b.cast(pl.Float64)),
            'vendor-link weighted counts differ from the unweighted counts')
    _reject(joined, (pl.col('s_flags') != _flags(pl.col('s_including_intra_group') != s))
            | (pl.col('b_flags') != _flags(pl.col('b_including_intra_group') != b)),
            'vendor-link flags disagree with the support')


def validate_vendor_links(result: VendorLinks, pair_table: pl.DataFrame,
                          node_ids: frozenset[str]) -> None:
    '''Check the targets against the companions, and the companions against the pair table.

    `node_ids` holds the selected NAICS 2022 national-industry nodes. The checks run in a
    fixed order, and the first that fails raises its own message.
    '''
    targets, marginals, support = result.targets, result.marginals, result.support
    validate_targets(targets)
    _require_pairs(pair_table)
    if (list(marginals.schema.items()) != list(MARGINAL_SCHEMA.items())
            or list(support.schema.items()) != list(SUPPORT_SCHEMA.items())):
        raise ValueError('vendor-link companion schemas differ')
    _reject(targets, pl.any_horizontal([pl.col(key) != value for key, value in METADATA.items()]),
            'vendor-link rows differ from the metadata')
    nodes = sorted(node_ids)
    _reject(targets, ~pl.col('unit_a').is_in(nodes) | ~pl.col('unit_b').is_in(nodes),
            'vendor-link units are not selected NAICS 2022 national industries')
    _check_cells(targets, marginals, support)
    for unit, column in (('unit_a', 'n_supplier_pairs'), ('unit_b', 'n_buyer_pairs')):
        sums = support.group_by(node_id=unit).agg(_sum=pl.col('l_pairs').sum())
        _reject(marginals.join(sums, on='node_id', how='full', coalesce=True),
                pl.col('_sum').fill_null(0) != pl.col(column),
                'vendor-link pair sums differ from the marginals')
    expected_marginals, expected_support = _companions(pair_table)
    if not marginals.equals(expected_marginals):
        raise ValueError('vendor-link marginals differ from the pair table')
    if not support.equals(expected_support):
        raise ValueError('vendor-link support differs from the pair table')
