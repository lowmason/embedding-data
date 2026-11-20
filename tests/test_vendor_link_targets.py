'''Stage 14 vendor-link target (O6) and its marginal and support companions.

Every pair table here is synthetic: a typed frame in `PAIR_SCHEMA` with made-up 12-character
UEIs, real-form NAICS 2022 national-industry node IDs and no name or address values. Each
table passes `validate_pairs`, so no fixture holds a pair that the pair step cannot produce.
Each refusal matches the exact message (`\\A...\\Z`), so a refusal at the wrong check fails.
'''

import json
import re
from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal

import polars as pl
import pytest
from vendor_link_fixtures import no_live_sam  # noqa: F401

from embedding_data import target_contract
from embedding_data.target_contract import TARGET_KEY_COLUMNS, TARGET_SCHEMA
from embedding_data.vendor_link_codes import NODE_PREFIX
from embedding_data.vendor_link_pairs import (
    AMOUNT_TYPE,
    FIRM_STATUSES,
    PAIR_SCHEMA,
    validate_pairs,
)
from embedding_data.vendor_link_targets import (
    CONTRACT,
    INTRA_LABEL,
    MARGINAL_SCHEMA,
    METADATA,
    SIZE_LABEL,
    SUPPORT_SCHEMA,
    TOLERANCE,
    UNIVERSE,
    VendorLinks,
    estimate,
    validate_vendor_links,
)

SNAPSHOT = date(2026, 11, 20)
MONTH = '2026-11'


def node(code: str) -> str:
    return NODE_PREFIX + code


N541511, N541512, N236220, N336411 = (node(code)
                                      for code in ('541511', '541512', '236220', '336411'))
# One selected node that no fixture firm holds, so the node set is wider than the units.
NODE_IDS = frozenset({N541511, N541512, N236220, N336411, node('111110')})


def exactly(message):
    return pytest.raises(ValueError, match=rf'\A{re.escape(message)}\Z')


def uei(name: str) -> str:
    '''A made-up 12-character UEI. Left padding keeps `U1` and `U10` apart.'''
    return name.rjust(12, 'Z')


def link(prime, sub, *, intra=False, fy=(1, 0, 0), amount='0.00'):
    '''One pair of the named firms: its usable reports by fiscal year (2024, 2025, 2026), its
    intra-group flag and its amount sum.'''
    return {'prime': prime, 'sub': sub, 'intra': intra, 'fy': fy, 'amount': amount}


def _firm(value):
    '''A six-digit code gives an eligible firm and its node. A firm status gives that status
    and no node.'''
    if value in FIRM_STATUSES:
        assert value != 'eligible'
        return value, None
    return 'eligible', node(value)


def _status(prime, sub, intra, prime_status, sub_status):
    if prime == sub:
        return 'self_link'
    if intra:
        return 'intra_group'
    if prime_status != 'eligible':
        return 'prime_ineligible'
    if sub_status != 'eligible':
        return 'sub_ineligible'
    return 'eligible'


def pair_table(firms, *links):
    '''The pair table of `links`, sorted and checked by `validate_pairs`. `firms` maps each
    firm name to its NAICS code or to an ineligible firm status.'''
    rows = []
    for item in links:
        prime_status, prime_node = _firm(firms[item['prime']])
        sub_status, sub_node = _firm(firms[item['sub']])
        fy2024, fy2025, fy2026 = item['fy']
        rows.append({
            'prime_uei': uei(item['prime']), 'sub_uei': uei(item['sub']),
            'n_reports': fy2024 + fy2025 + fy2026,
            'n_fy2024': fy2024, 'n_fy2025': fy2025, 'n_fy2026': fy2026,
            'prime_status': prime_status, 'sub_status': sub_status,
            'prime_node_id': prime_node, 'sub_node_id': sub_node,
            'flag_intra_group': item['intra'],
            'pair_status': _status(item['prime'], item['sub'], item['intra'], prime_status,
                                   sub_status),
            'amount_sum': Decimal(item['amount'])})
    table = pl.DataFrame(rows, schema=PAIR_SCHEMA).sort('prime_uei', 'sub_uei')
    validate_pairs(table, int(table['n_reports'].sum()))
    return table


def run(firms, *links):
    return estimate(pair_table(firms, *links), snapshot=SNAPSHOT, month=MONTH)


def _only(frame, **where):
    rows = frame.filter(*[pl.col(key) == value for key, value in where.items()])
    assert rows.height == 1, where
    return rows.row(0, named=True)


def lookups(result):
    '''Row lookups by key: a target row, a support row and a marginal row.'''
    def target(measure, s, d):
        return _only(result.targets, measure=measure, unit_a=s, unit_b=d)

    def support_row(s, d):
        return _only(result.support, unit_a=s, unit_b=d)

    def marginal(node_id):
        return _only(result.marginals, node_id=node_id)

    return target, support_row, marginal


def cells(result):
    return set(result.support.select('unit_a', 'unit_b').iter_rows())


# ---- plan tests

def test_each_firm_counts_once_however_many_reports_or_years():
    # sub u (541511) with prime p (236220): 3 reports over FY2024 and FY2026
    result = run({'P': '236220', 'U': '541511'}, link('P', 'U', fy=(2, 0, 1)))
    target, support_row, marginal = lookups(result)
    s, d = N541511, N236220
    assert support_row(s, d)['s_suppliers'] == 1 and support_row(s, d)['l_fy2025'] == 0
    assert support_row(s, d)['b_buyers'] == 1 and support_row(s, d)['l_pairs'] == 1
    assert target('supplier_share', s, d)['n_unweighted'] == 1
    assert target('buyer_share', s, d)['n_unweighted'] == 1
    assert marginal(s)['n_suppliers'] == 1 and marginal(d)['n_buyers'] == 1


def test_firm_in_both_roles_counts_in_each_role():
    # f (541512) subcontracts to p (236220) and is the prime of u (541511)
    result = run({'P': '236220', 'F': '541512', 'U': '541511'},
                 link('P', 'F'), link('F', 'U'))
    target, support_row, marginal = lookups(result)
    assert cells(result) == {(N541512, N236220), (N541511, N541512)}
    assert marginal(N541512)['n_suppliers'] == 1 and marginal(N541512)['n_buyers'] == 1
    assert marginal(N541512)['n_supplier_pairs'] == 1
    assert marginal(N541512)['n_buyer_pairs'] == 1
    assert target('supplier_share', N541512, N236220)['value'] == 1.0
    assert target('buyer_share', N541511, N541512)['value'] == 1.0
    assert result.report['n_suppliers']['eligible'] == 2
    assert result.report['n_buyers']['eligible'] == 2


def test_diagonal_cell_is_emitted():
    # p (541511) buys from u (541511) of its own industry, and from v (541512)
    result = run({'P': '541511', 'U': '541511', 'V': '541512'},
                 link('P', 'U'), link('P', 'V'))
    target, support_row, marginal = lookups(result)
    assert (N541511, N541511) in cells(result)
    assert target('supplier_share', N541511, N541511)['value'] == 1.0
    assert target('buyer_share', N541511, N541511)['value'] == 1.0
    assert support_row(N541511, N541511)['l_pairs'] == 1
    assert result.report['diagonal'] == {'cells': 1, 'pairs': 1, 'share_of_pairs': 0.5}


def test_firm_shares_and_pair_counts_differ_for_a_large_prime():
    # prime p in d has 4 subs in s; prime q in d has 1 sub in s; n_sup(s) = 5, n_buy(d) = 2
    firms = {'P': '236220', 'Q': '236220'} | {f'U{k}': '541511' for k in range(1, 6)}
    result = run(firms, *[link('P', f'U{k}') for k in range(1, 5)], link('Q', 'U5'))
    target, support_row, marginal = lookups(result)
    s, d = N541511, N236220
    assert target('supplier_share', s, d)['value'] == 1.0
    assert target('buyer_share', s, d)['value'] == 1.0
    assert support_row(s, d)['l_pairs'] == 5


def test_values_are_ratios_of_firm_counts():
    # n_sup(s) = 4 with S(s,d) = 1: value 0.25, n_unweighted 1
    firms = {'P': '236220', 'R': '336411'} | {f'U{k}': '541511' for k in range(1, 5)}
    result = run(firms, link('P', 'U1'), *[link('R', f'U{k}') for k in range(2, 5)])
    target, support_row, marginal = lookups(result)
    row = target('supplier_share', N541511, N236220)
    assert row['value'] == 0.25 and row['n_unweighted'] == 1
    assert row['n_weighted'] == 1.0
    other = target('supplier_share', N541511, N336411)
    assert other['value'] == 0.75 and other['n_unweighted'] == 3


def test_intra_group_sensitivity_counts_and_label():
    # an intra_group pair raises s_including_intra_group and adds INTRA_LABEL; a cell
    # only under P+ is counted in report['cells_only_intra_group'] and not listed
    firms = {'P': '236220', 'R': '336411', 'U': '541511', 'W': '541511', 'G': '541512'}
    result = run(firms, link('P', 'U'), link('P', 'W', intra=True), link('R', 'G', intra=True))
    target, support_row, marginal = lookups(result)
    s, d = N541511, N236220
    assert support_row(s, d)['s_suppliers'] == 1
    assert support_row(s, d)['s_including_intra_group'] == 2
    assert support_row(s, d)['l_including_intra_group'] == 2
    assert target('supplier_share', s, d)['flags'] == [INTRA_LABEL, SIZE_LABEL]
    assert target('buyer_share', s, d)['flags'] == [SIZE_LABEL]
    assert result.report['cells_only_intra_group'] == 1
    assert cells(result) == {(s, d)}
    assert set(result.targets['unit_a']) | set(result.targets['unit_b']) == {s, d}


def test_intra_group_pair_with_an_ineligible_firm_stays_out_of_the_sensitivity():
    firms = {'P': '236220', 'U': '541511', 'X': 'not_in_sam', 'Y': 'naics_conflict'}
    result = run(firms, link('P', 'U'), link('P', 'X', intra=True), link('X', 'U', intra=True),
                 link('Y', 'U', intra=True))
    target, support_row, marginal = lookups(result)
    s, d = N541511, N236220
    row = support_row(s, d)
    assert (row['s_including_intra_group'], row['b_including_intra_group'],
            row['l_including_intra_group']) == (1, 1, 1)
    assert target('supplier_share', s, d)['flags'] == [SIZE_LABEL]
    assert target('buyer_share', s, d)['flags'] == [SIZE_LABEL]
    assert result.report['n_pairs'] == {'eligible': 1, 'including_intra_group': 1}
    assert result.report['cells_only_intra_group'] == 0


def test_partial_counterparty_sets_are_counted_per_industry():
    firms = {'P': '236220', 'R': '336411', 'U1': '541511', 'U2': '541511', 'V': '541512',
             'X': 'not_in_sam', 'Y': 'dnb_era_record'}
    result = run(firms, link('P', 'U1'), link('R', 'U2'), link('R', 'V'),
                 link('X', 'U1'), link('Y', 'U1'), link('X', 'V'), link('P', 'Y'))
    target, support_row, marginal = lookups(result)
    # U1 has two prime_ineligible pairs and counts once; U2 has none.
    assert marginal(N541511)['n_suppliers_partial'] == 1
    assert marginal(N541512)['n_suppliers_partial'] == 1
    assert marginal(N236220)['n_buyers_partial'] == 1
    assert marginal(N336411)['n_buyers_partial'] == 0
    # Partial sets are per industry: U1's cell (541511, 236220) and U2's cell
    # (541511, 336411) share the industry's one count.
    assert marginal(N541511)['n_suppliers'] == 2


def test_amount_sum_and_reports_sum_over_the_cell():
    firms = {'P': '236220', 'Q': '236220', 'U': '541511', 'V': '541511', 'W': '541511',
             'X': 'not_in_sam'}
    result = run(firms,
                 link('P', 'U', fy=(1, 1, 0), amount='100.25'),
                 link('Q', 'U', fy=(0, 0, 3), amount='-20.10'),
                 link('P', 'V', fy=(2, 0, 0), amount='0.00'),
                 link('P', 'W', intra=True, fy=(1, 0, 0), amount='500.00'),
                 link('X', 'U', fy=(4, 0, 0), amount='999.99'))
    target, support_row, marginal = lookups(result)
    row = support_row(N541511, N236220)
    assert row['amount_sum'] == Decimal('80.15')
    assert row['n_reports'] == 7
    assert (row['l_pairs'], row['l_fy2024'], row['l_fy2025'], row['l_fy2026']) == (3, 2, 1, 1)


def test_metadata_flags_and_universe():
    result = run({'P': '236220', 'U': '541511'}, link('P', 'U'))
    assert result.targets.height == 2
    for row in result.targets.iter_rows(named=True):
        assert {key: row[key] for key in METADATA} == METADATA
        assert row['se'] is None
        assert row['flags'] == [SIZE_LABEL]
        assert row['universe'] == UNIVERSE.format(snapshot='2026-11-20', month='2026-11')
    assert result.targets['measure'].to_list() == ['buyer_share', 'supplier_share']


# ---- validator fixture and breaks

VALID_FIRMS = {'P': '236220', 'Q': '236220', 'R': '336411', 'U1': '541511', 'U2': '541511',
               'U3': '541511', 'V': '541512', 'G': '541512', 'X': 'not_in_sam'}
VALID_LINKS = (
    link('P', 'U1', fy=(1, 0, 0), amount='10.00'),
    link('P', 'U2', fy=(0, 2, 0), amount='5.50'),
    link('Q', 'U1', fy=(0, 0, 1), amount='1.25'),
    link('R', 'U3', fy=(1, 1, 1), amount='7.00'),
    link('P', 'V', fy=(1, 0, 0), amount='3.00'),
    link('X', 'U3'),
    link('R', 'X'),
    link('R', 'G', intra=True),
    link('Q', 'V', intra=True),
)
VALID_TABLE = pair_table(VALID_FIRMS, *VALID_LINKS)


def valid():
    return estimate(VALID_TABLE, snapshot=SNAPSHOT, month=MONTH)


def match(where):
    return pl.all_horizontal([pl.col(key) == value for key, value in where.items()])


def edit(frame, where, **changes):
    '''A copy of `frame` with `changes` applied to the rows matching every `where` item.'''
    rows = frame.to_dicts()
    hits = [row for row in rows if all(row[key] == value for key, value in where.items())]
    assert hits, where
    for row in hits:
        row.update(changes)
    return pl.DataFrame(rows, schema=frame.schema, orient='row')


def without(frame, where):
    return frame.filter(~match(where))


def broken(change):
    result = valid()
    targets, marginals, support = change(result.targets, result.marginals, result.support)
    return replace(result, targets=targets, marginals=marginals, support=support)


SD = {'unit_a': N541511, 'unit_b': N236220}
SD2 = {'unit_a': N541511, 'unit_b': N336411}
VD = {'unit_a': N541512, 'unit_b': N236220}
SUPPLIER = {'measure': 'supplier_share'}
BUYER = {'measure': 'buyer_share'}
MEASURES = 'vendor-link cells lack exactly one row of each measure'
SUPPORT_CELLS = 'vendor-link support does not match the target cells'
FIRM_BOUNDS = 'vendor-link firm counts are out of bounds'
PAIR_BOUNDS = 'vendor-link pair counts are out of bounds'
VALUES = 'vendor-link values differ from the ratios'
UNITS = 'vendor-link units are not selected NAICS 2022 national industries'
PAIR_SUMS = 'vendor-link pair sums differ from the marginals'
MARGINALS = 'vendor-link marginals differ from the pair table'
SUPPORT = 'vendor-link support differs from the pair table'
BREAKS = {
    'missing_measure': (lambda t, m, s: (without(t, SD2 | BUYER), m, s), MEASURES),
    'value': (lambda t, m, s: (edit(t, SD | SUPPLIER, value=0.5), m, s), VALUES),
    's_above_n': (lambda t, m, s: (t, edit(m, {'node_id': N541511}, n_suppliers=1), s),
                  FIRM_BOUNDS),
    'l_below_max': (lambda t, m, s: (t, m, edit(s, SD, l_pairs=1)), PAIR_BOUNDS),
    'l_above_product': (lambda t, m, s: (t, m, edit(s, SD2, l_pairs=2)), PAIR_BOUNDS),
    'unknown_node': (lambda t, m, s: (edit(t, SD | BUYER, unit_b=node('541519')), m, s), UNITS),
    'pair_sum': (lambda t, m, s: (t, m, edit(s, SD, l_pairs=4)), PAIR_SUMS),
    'support_differs': (lambda t, m, s: (t, m, edit(s, SD, s_suppliers=1)), SUPPORT_CELLS),
    'marginal_differs': (lambda t, m, s: (t, edit(m, {'node_id': N541511},
                                                  n_suppliers_partial=0), s), MARGINALS),
}


@pytest.mark.parametrize('break_', ['missing_measure', 'value', 's_above_n', 'l_below_max',
                                    'l_above_product', 'unknown_node', 'pair_sum',
                                    'support_differs', 'marginal_differs'])
def test_validator_rejects(break_):
    change, message = BREAKS[break_]
    with exactly(message):
        validate_vendor_links(broken(change), VALID_TABLE, NODE_IDS)


# ---- constants and result shape

def test_contract_constants():
    assert CONTRACT == 'vendor-links-v1'
    assert TOLERANCE == 1e-12
    assert SIZE_LABEL == 'size_gate_pending'
    assert INTRA_LABEL == 'numerator:intra_group_sensitivity:true'
    assert METADATA == {'source': 'usaspending_sam', 'family': 'vendor_links',
                        'unit_a_type': 'naics_national_industry',
                        'unit_b_type': 'naics_national_industry', 'se_method': 'none',
                        'sample_set': 'usaspending_subcontracts_fy2024_2026',
                        'vintage': 'naics=2022'}
    assert list(MARGINAL_SCHEMA.items()) == [
        ('node_id', pl.String), ('n_suppliers', pl.UInt64), ('n_buyers', pl.UInt64),
        ('n_supplier_pairs', pl.UInt64), ('n_buyer_pairs', pl.UInt64),
        ('n_suppliers_partial', pl.UInt64), ('n_buyers_partial', pl.UInt64),
        ('n_suppliers_including_intra_group', pl.UInt64),
        ('n_buyers_including_intra_group', pl.UInt64)]
    assert list(SUPPORT_SCHEMA.items()) == [
        ('unit_a', pl.String), ('unit_b', pl.String), ('s_suppliers', pl.UInt64),
        ('b_buyers', pl.UInt64), ('l_pairs', pl.UInt64), ('l_fy2024', pl.UInt64),
        ('l_fy2025', pl.UInt64), ('l_fy2026', pl.UInt64),
        ('s_including_intra_group', pl.UInt64), ('b_including_intra_group', pl.UInt64),
        ('l_including_intra_group', pl.UInt64), ('amount_sum', pl.Decimal(38, 2)),
        ('n_reports', pl.UInt64)]
    assert AMOUNT_TYPE == pl.Decimal(38, 2)


def test_universe_is_the_spec_statement():
    assert UNIVERSE == (
        'USAspending.gov contract subaward reports (FFATA subcontracts) with subaward action '
        'dates in federal fiscal years 2024–2026, downloaded under snapshot {snapshot}, '
        'joined by UEI to the SAM.gov public monthly entity extract of {month}. The '
        'population is federal prime contractors and the subcontractors they report, not a '
        'frame of firms or of business-to-business trade. A link is a distinct '
        'prime–subcontractor pair. Links within one corporate group, as the reported '
        'parent UEIs show, are excluded. Industries are each firm\N{APOSTROPHE}s '
        'self-reported primary NAICS 2022 code in SAM.gov at the extract date, not at the '
        'subaward date. Links, codes and amounts are self-reported and unvalidated.')


def test_universe_takes_the_snapshot_and_month_of_the_call():
    table = pair_table({'P': '236220', 'U': '541511'}, link('P', 'U'))
    result = estimate(table, snapshot=date(2027, 1, 3), month='2026-12')
    expected = UNIVERSE.format(snapshot='2027-01-03', month='2026-12')
    assert 'snapshot 2027-01-03, joined' in expected and 'extract of 2026-12.' in expected
    assert set(result.targets['universe']) == {expected}


def test_result_is_a_frozen_dataclass_of_frames():
    result = valid()
    assert isinstance(result, VendorLinks)
    assert all(isinstance(frame, pl.DataFrame)
               for frame in (result.targets, result.marginals, result.support))
    with pytest.raises(FrozenInstanceError):
        result.report = {}


def test_tables_have_their_exact_schemas():
    result = valid()
    assert list(result.targets.schema.items()) == list(TARGET_SCHEMA.items())
    assert list(result.marginals.schema.items()) == list(MARGINAL_SCHEMA.items())
    assert list(result.support.schema.items()) == list(SUPPORT_SCHEMA.items())


# ---- estimand shapes

def test_one_subcontractor_with_two_primes_in_one_buyer_industry():
    result = run({'P': '236220', 'Q': '236220', 'U': '541511'},
                 link('P', 'U'), link('Q', 'U'))
    target, support_row, marginal = lookups(result)
    row = support_row(N541511, N236220)
    assert (row['s_suppliers'], row['b_buyers'], row['l_pairs']) == (1, 2, 2)
    assert target('supplier_share', N541511, N236220)['n_unweighted'] == 1
    assert target('buyer_share', N541511, N236220)['n_unweighted'] == 2
    assert marginal(N541511)['n_suppliers'] == 1
    assert marginal(N541511)['n_supplier_pairs'] == 2
    assert marginal(N236220)['n_buyers'] == 2


def test_industry_counts_are_distinct_firms_across_cells():
    # u (541511) sells to primes in two buyer industries; p (236220) buys from two supplier
    # industries. Each counts once in its industry's denominator.
    firms = {'P': '236220', 'R': '336411', 'U': '541511', 'V': '541512'}
    result = run(firms, link('P', 'U'), link('R', 'U'), link('P', 'V'))
    target, support_row, marginal = lookups(result)
    assert marginal(N541511)['n_suppliers'] == 1
    assert marginal(N541511)['n_supplier_pairs'] == 2
    assert marginal(N236220)['n_buyers'] == 1
    assert marginal(N236220)['n_buyer_pairs'] == 2
    assert target('supplier_share', N541511, N236220)['value'] == 1.0
    assert target('supplier_share', N541511, N336411)['value'] == 1.0
    assert target('buyer_share', N541511, N236220)['value'] == 1.0
    assert target('buyer_share', N541512, N236220)['value'] == 1.0
    assert result.report['n_suppliers'] == {'eligible': 2, 'including_intra_group': 2}
    assert result.report['n_buyers'] == {'eligible': 2, 'including_intra_group': 2}


def test_buyer_value_divides_by_the_buyer_industry():
    # Two primes in d buy from s and from v; only p buys from s.
    firms = {'P': '236220', 'Q': '236220', 'U': '541511', 'V': '541512'}
    result = run(firms, link('P', 'U'), link('P', 'V'), link('Q', 'V'))
    target, support_row, marginal = lookups(result)
    row = target('buyer_share', N541511, N236220)
    assert row['value'] == 0.5 and row['n_unweighted'] == 1
    assert target('buyer_share', N541512, N236220)['value'] == 1.0
    assert target('supplier_share', N541511, N236220)['value'] == 1.0


def test_rows_in_both_directions_are_different_cells():
    # u (541511) sells to p (236220), g (236220) sells to f (541511), and w (541511) sells
    # to f.
    firms = {'P': '236220', 'U': '541511', 'F': '541511', 'G': '236220', 'W': '541511'}
    result = run(firms, link('P', 'U'), link('F', 'G'), link('F', 'W'))
    assert cells(result) == {(N541511, N236220), (N236220, N541511), (N541511, N541511)}
    target, support_row, marginal = lookups(result)
    assert target('supplier_share', N541511, N236220)['value'] == 0.5
    assert target('supplier_share', N236220, N541511)['value'] == 1.0


def test_intra_group_pair_that_raises_only_the_buyer_count():
    # v is already in the cell through p; the new prime q joins it only through intra_group.
    firms = {'P': '236220', 'Q': '236220', 'V': '541512'}
    result = run(firms, link('P', 'V'), link('Q', 'V', intra=True))
    target, support_row, marginal = lookups(result)
    row = support_row(N541512, N236220)
    assert (row['s_including_intra_group'], row['b_including_intra_group'],
            row['l_including_intra_group']) == (1, 2, 2)
    assert target('supplier_share', N541512, N236220)['flags'] == [SIZE_LABEL]
    assert target('buyer_share', N541512, N236220)['flags'] == [INTRA_LABEL, SIZE_LABEL]
    assert marginal(N236220)['n_buyers_including_intra_group'] == 2
    assert marginal(N236220)['n_buyers'] == 1


def test_intra_group_pair_that_raises_only_the_pair_count():
    # u and p are both already in the cell; their intra_group pairs add no firm.
    firms = {'P': '236220', 'Q': '236220', 'U': '541511', 'W': '541511'}
    result = run(firms, link('P', 'U'), link('Q', 'W'), link('P', 'W', intra=True),
                 link('Q', 'U', intra=True))
    target, support_row, marginal = lookups(result)
    row = support_row(N541511, N236220)
    assert (row['s_including_intra_group'], row['b_including_intra_group'],
            row['l_including_intra_group']) == (2, 2, 4)
    assert target('supplier_share', N541511, N236220)['flags'] == [SIZE_LABEL]
    assert target('buyer_share', N541511, N236220)['flags'] == [SIZE_LABEL]


def test_intra_group_pair_that_raises_only_a_denominator():
    # w (541511) joins s only through an intra_group pair with a prime in another industry.
    firms = {'P': '236220', 'R': '336411', 'U': '541511', 'W': '541511'}
    result = run(firms, link('P', 'U'), link('R', 'W', intra=True))
    target, support_row, marginal = lookups(result)
    assert target('supplier_share', N541511, N236220)['flags'] == [SIZE_LABEL]
    assert target('supplier_share', N541511, N236220)['value'] == 1.0
    assert marginal(N541511)['n_suppliers_including_intra_group'] == 2
    assert marginal(N541511)['n_suppliers'] == 1
    assert result.report['cells_only_intra_group'] == 1
    assert cells(result) == {(N541511, N236220)}


def test_self_link_stays_out_of_the_target_and_the_sensitivity():
    firms = {'P': '236220', 'U': '541511'}
    result = run(firms, link('P', 'U'), link('U', 'U'), link('P', 'P'))
    target, support_row, marginal = lookups(result)
    assert cells(result) == {(N541511, N236220)}
    row = support_row(N541511, N236220)
    assert (row['s_including_intra_group'], row['b_including_intra_group'],
            row['l_including_intra_group']) == (1, 1, 1)
    assert result.report['n_pairs'] == {'eligible': 1, 'including_intra_group': 1}
    assert result.report['cells_only_intra_group'] == 0
    assert marginal(N541511)['n_buyers'] == 0
    assert marginal(N236220)['n_suppliers'] == 0


def test_partial_counts_follow_the_role_of_the_excluded_pair():
    # u is the subcontractor of an ineligible prime: a supplier partial. p is the prime of an
    # ineligible subcontractor: a buyer partial. Neither counts in the other role.
    firms = {'P': '236220', 'U': '541511', 'F': '541511', 'X': 'not_in_sam'}
    result = run(firms, link('P', 'U'), link('F', 'P'), link('X', 'U'), link('P', 'X'))
    target, support_row, marginal = lookups(result)
    assert marginal(N541511)['n_suppliers_partial'] == 1
    assert marginal(N541511)['n_buyers_partial'] == 0
    assert marginal(N236220)['n_buyers_partial'] == 1
    assert marginal(N236220)['n_suppliers_partial'] == 0


def test_partial_counts_ignore_the_other_excluded_statuses():
    # u's other pairs are intra_group, self_link and sub_ineligible (as a prime): no supplier
    # partial. p's other pairs are intra_group, self_link and prime_ineligible (as a sub): no
    # buyer partial.
    firms = {'P': '236220', 'U': '541511', 'G': '336411', 'H': '541512', 'X': 'not_in_sam'}
    result = run(firms, link('P', 'U'), link('G', 'U', intra=True), link('U', 'U'),
                 link('U', 'X'), link('P', 'H', intra=True), link('P', 'P'), link('X', 'P'))
    target, support_row, marginal = lookups(result)
    assert marginal(N541511)['n_suppliers_partial'] == 0
    assert marginal(N236220)['n_buyers_partial'] == 0


def test_partial_counts_only_firms_in_the_target():
    # v's only pair is prime_ineligible, and r's only pair is sub_ineligible: no marginal row.
    firms = {'P': '236220', 'U': '541511', 'V': '541512', 'R': '336411', 'X': 'not_in_sam'}
    result = run(firms, link('P', 'U'), link('X', 'V'), link('R', 'X'))
    assert result.marginals['node_id'].to_list() == [N236220, N541511]
    assert result.marginals['n_suppliers_partial'].to_list() == [0, 0]
    assert result.marginals['n_buyers_partial'].to_list() == [0, 0]


def test_node_in_one_role_has_zero_counts_in_the_other():
    result = run({'P': '236220', 'U': '541511'}, link('P', 'U'))
    target, support_row, marginal = lookups(result)
    assert marginal(N541511) == {
        'node_id': N541511, 'n_suppliers': 1, 'n_buyers': 0, 'n_supplier_pairs': 1,
        'n_buyer_pairs': 0, 'n_suppliers_partial': 0, 'n_buyers_partial': 0,
        'n_suppliers_including_intra_group': 1, 'n_buyers_including_intra_group': 0}
    assert marginal(N236220) == {
        'node_id': N236220, 'n_suppliers': 0, 'n_buyers': 1, 'n_supplier_pairs': 0,
        'n_buyer_pairs': 1, 'n_suppliers_partial': 0, 'n_buyers_partial': 0,
        'n_suppliers_including_intra_group': 0, 'n_buyers_including_intra_group': 1}


def test_sensitivity_counts_reach_a_role_seen_only_under_the_sensitivity():
    # 541511 has a supplier in P, and a buyer only through an intra_group pair.
    firms = {'P': '236220', 'U': '541511', 'F': '541511', 'G': '336411'}
    result = run(firms, link('P', 'U'), link('F', 'G', intra=True))
    target, support_row, marginal = lookups(result)
    row = marginal(N541511)
    assert (row['n_buyers'], row['n_buyers_including_intra_group']) == (0, 1)
    assert (row['n_suppliers'], row['n_suppliers_including_intra_group']) == (1, 1)


def test_node_only_under_the_sensitivity_has_no_marginal_row():
    firms = {'P': '236220', 'U': '541511', 'R': '336411', 'G': '541512'}
    result = run(firms, link('P', 'U'), link('R', 'G', intra=True))
    assert result.marginals['node_id'].to_list() == [N236220, N541511]
    assert result.report['n_suppliers'] == {'eligible': 1, 'including_intra_group': 2}
    assert result.report['n_buyers'] == {'eligible': 1, 'including_intra_group': 2}
    assert result.report['n_pairs'] == {'eligible': 1, 'including_intra_group': 2}


def test_tables_are_sorted_whatever_the_pair_order():
    table = VALID_TABLE.reverse()
    result = estimate(table, snapshot=SNAPSHOT, month=MONTH)
    expected = valid()
    assert result.targets.equals(expected.targets)
    assert result.marginals.equals(expected.marginals)
    assert result.support.equals(expected.support)
    assert result.report == expected.report
    assert result.targets.equals(result.targets.sort(TARGET_KEY_COLUMNS))
    assert result.support.equals(result.support.sort('unit_a', 'unit_b'))
    assert result.marginals['node_id'].to_list() == sorted(result.marginals['node_id'])
    assert result.targets.select('unit_a', 'unit_b').unique(maintain_order=True).equals(
        result.support.select('unit_a', 'unit_b'))


def test_estimate_refuses_another_pair_schema():
    for table in (VALID_TABLE.drop('amount_sum'),
                  VALID_TABLE.with_columns(pl.col('n_reports').cast(pl.Int64)),
                  VALID_TABLE.select(reversed(VALID_TABLE.columns))):
        with exactly('vendor-link pair table schema differs'):
            estimate(table, snapshot=SNAPSHOT, month=MONTH)


def test_empty_target_population_gives_empty_tables():
    only_intra = ({'P': '236220', 'U': '541511', 'X': 'not_in_sam'},
                  link('P', 'U', intra=True), link('X', 'U'))
    for firms, *links in (({},), only_intra):
        table = pair_table(firms, *links)
        result = estimate(table, snapshot=SNAPSHOT, month=MONTH)
        assert list(result.targets.schema.items()) == list(TARGET_SCHEMA.items())
        assert list(result.marginals.schema.items()) == list(MARGINAL_SCHEMA.items())
        assert list(result.support.schema.items()) == list(SUPPORT_SCHEMA.items())
        assert (result.targets.height, result.marginals.height, result.support.height) == (0,
                                                                                         0, 0)
        assert result.report['n_pairs']['eligible'] == 0
        assert result.report['diagonal'] == {'cells': 0, 'pairs': 0, 'share_of_pairs': None}
        assert result.report['subcontractors_per_prime'] == {
            'count': 0, 'min': None, 'p25': None, 'median': None, 'p75': None, 'p90': None,
            'max': None, '1': 0, '2': 0, '3': 0, '5': 0, '10+': 0}
        validate_vendor_links(result, table, NODE_IDS)
    assert result.report['n_pairs'] == {'eligible': 0, 'including_intra_group': 1}
    assert result.report['cells_only_intra_group'] == 1


# ---- report

def test_report_keys_and_counts():
    report = valid().report
    assert list(report) == ['n_suppliers', 'n_buyers', 'n_pairs', 'diagonal',
                            'cells_only_intra_group', 'n_unweighted_distribution',
                            'subcontractors_per_prime', 'primes_per_subcontractor']
    assert report['n_suppliers'] == {'eligible': 4, 'including_intra_group': 5}
    assert report['n_buyers'] == {'eligible': 3, 'including_intra_group': 3}
    assert report['n_pairs'] == {'eligible': 5, 'including_intra_group': 7}
    assert report['diagonal'] == {'cells': 0, 'pairs': 0, 'share_of_pairs': 0.0}
    assert report['cells_only_intra_group'] == 1
    assert list(report['n_unweighted_distribution']) == ['supplier_share', 'buyer_share']
    assert report['n_unweighted_distribution']['supplier_share'] == {
        'count': 3, 'min': 1, 'p25': 1.0, 'median': 1.0, 'p75': 2.0, 'p90': 2.0, 'max': 2,
        '1': 2, '2': 1, '3': 0, '5': 0, '10+': 0}
    assert report['n_unweighted_distribution']['buyer_share'] == {
        'count': 3, 'min': 1, 'p25': 1.0, 'median': 1.0, 'p75': 2.0, 'p90': 2.0, 'max': 2,
        '1': 2, '2': 1, '3': 0, '5': 0, '10+': 0}
    # Over P: P has U1, U2 and V; Q has U1; R has U3. U1 has P and Q.
    assert report['subcontractors_per_prime'] == {
        'count': 3, 'min': 1, 'p25': 1.0, 'median': 1.0, 'p75': 3.0, 'p90': 3.0, 'max': 3,
        '1': 2, '2': 0, '3': 1, '5': 0, '10+': 0}
    assert report['primes_per_subcontractor'] == {
        'count': 4, 'min': 1, 'p25': 1.0, 'median': 1.0, 'p75': 1.0, 'p90': 2.0, 'max': 2,
        '1': 3, '2': 1, '3': 0, '5': 0, '10+': 0}


def test_report_distribution_counts_and_order_statistics():
    # Nine primes in d with 1, 1, 2, 3, 4, 5, 10, 12 and 12 subcontractors in s. With nine
    # values, p25, p75 and p90 fall on whole positions 2, 6 and 7 (from 0).
    sizes = (1, 1, 2, 3, 4, 5, 10, 12, 12)
    firms, links = {}, []
    for index, size in enumerate(sizes):
        firms[f'P{index}'] = '236220'
        for k in range(size):
            firms[f'U{index}X{k}'] = '541511'
            links.append(link(f'P{index}', f'U{index}X{k}'))
    report = run(firms, *links).report
    assert report['subcontractors_per_prime'] == {
        'count': 9, 'min': 1, 'p25': 2.0, 'median': 4.0, 'p75': 10.0, 'p90': 12.0, 'max': 12,
        '1': 2, '2': 1, '3': 1, '5': 1, '10+': 3}
    assert report['primes_per_subcontractor'] == {
        'count': 50, 'min': 1, 'p25': 1.0, 'median': 1.0, 'p75': 1.0, 'p90': 1.0, 'max': 1,
        '1': 50, '2': 0, '3': 0, '5': 0, '10+': 0}
    assert report['n_unweighted_distribution']['supplier_share']['max'] == 50
    assert report['n_unweighted_distribution']['buyer_share']['10+'] == 0


def test_report_diagonal_counts_cells_pairs_and_share():
    # Diagonal cells (541511, 541511) with 2 pairs and (236220, 236220) with 1; 5 pairs in P.
    firms = {'P': '541511', 'Q': '541511', 'U': '541511', 'C': '236220', 'D': '236220',
             'R': '336411'}
    result = run(firms, link('P', 'U'), link('Q', 'U'), link('C', 'D'), link('R', 'U'),
                 link('R', 'D'))
    assert result.report['diagonal'] == {'cells': 2, 'pairs': 3, 'share_of_pairs': 0.6}


def test_report_is_plain_json():
    for result in (valid(), run({})):
        text = json.dumps(result.report, allow_nan=False, sort_keys=True)
        assert json.loads(text) == result.report


# ---- writer and validator

def test_targets_pass_the_shared_writer(tmp_path):
    result = valid()
    record = target_contract.write_targets(result.targets, tmp_path / 'vendor_links.parquet')
    assert record['rows'] == 6
    assert pl.read_parquet(tmp_path / 'vendor_links.parquet').equals(result.targets)


@pytest.mark.parametrize('case', ['valid', 'diagonal', 'large_prime', 'both_roles'])
def test_validator_accepts_the_build(case):
    tables = {
        'valid': VALID_TABLE,
        'diagonal': pair_table({'P': '541511', 'U': '541511', 'V': '541512'},
                               link('P', 'U'), link('P', 'V')),
        'large_prime': pair_table({'P': '236220', 'Q': '236220'}
                                  | {f'U{k}': '541511' for k in range(1, 6)},
                                  *[link('P', f'U{k}') for k in range(1, 5)], link('Q', 'U5')),
        'both_roles': pair_table({'P': '236220', 'F': '541512', 'U': '541511'},
                                 link('P', 'F'), link('F', 'U')),
    }
    table = tables[case]
    validate_vendor_links(estimate(table, snapshot=SNAPSHOT, month=MONTH), table, NODE_IDS)


def test_validator_accepts_a_value_within_tolerance():
    result = valid()
    nudged = edit(result.targets, SD | SUPPLIER, value=2 / 3 + 1e-13)
    assert nudged['value'].ne(result.targets['value']).sum() == 1
    validate_vendor_links(replace(result, targets=nudged), VALID_TABLE, NODE_IDS)


def test_validator_rejects_a_unit_outside_the_node_set():
    with exactly(UNITS):
        validate_vendor_links(valid(), VALID_TABLE, NODE_IDS - {N336411})


def test_validator_rejects_a_pair_table_of_another_schema():
    with exactly('vendor-link pair table schema differs'):
        validate_vendor_links(valid(), VALID_TABLE.drop('flag_intra_group'), NODE_IDS)


def test_validator_rejects_a_changed_pair_table():
    # One more eligible report on P-U1 changes the support's n_reports and l_fy2025.
    changed = VALID_TABLE.with_columns(
        pl.when(pl.col('prime_uei') == uei('P'), pl.col('sub_uei') == uei('U1'))
        .then(pl.col(name) + 1).otherwise(pl.col(name)).alias(name)
        for name in ('n_reports', 'n_fy2025'))
    with exactly(SUPPORT):
        validate_vendor_links(valid(), changed, NODE_IDS)


TARGETS_SCHEMA = 'targets schema must match exact ordered targets-v1 types'
COMPANIONS = 'vendor-link companion schemas differ'
METADATA_DIFFERS = 'vendor-link rows differ from the metadata'
WEIGHTED = 'vendor-link weighted counts differ from the unweighted counts'
FLAGS = 'vendor-link flags disagree with the support'
MORE_BREAKS = {
    'targets-schema': (lambda t, m, s: (t.drop('universe'), m, s), TARGETS_SCHEMA),
    'marginal-dtype': (lambda t, m, s: (t, m.with_columns(pl.col('n_buyers').cast(pl.Int64)),
                                        s), COMPANIONS),
    'support-order': (lambda t, m, s: (t, m, s.select(reversed(s.columns))), COMPANIONS),
    'support-amount-dtype': (
        lambda t, m, s: (t, m, s.with_columns(pl.col('amount_sum').cast(pl.Decimal(38, 4)))),
        COMPANIONS),
    'metadata-source': (lambda t, m, s: (edit(t, SD | BUYER, source='usaspending'), m, s),
                        METADATA_DIFFERS),
    'metadata-family': (lambda t, m, s: (edit(t, SD | BUYER, family='co_ownership'), m, s),
                        METADATA_DIFFERS),
    'metadata-unit-a-type': (
        lambda t, m, s: (edit(t, SD | BUYER, unit_a_type='naics_industry',
                              unit_a='naics:2022:industry:54151'), m, s), METADATA_DIFFERS),
    'metadata-unit-b-type': (
        lambda t, m, s: (edit(t, SD | BUYER, unit_b_type='naics_industry',
                              unit_b='naics:2022:industry:23622'), m, s), METADATA_DIFFERS),
    'metadata-se-method': (lambda t, m, s: (edit(t, SD | BUYER, se_method='replicate', se=0.0),
                                            m, s), METADATA_DIFFERS),
    'metadata-sample-set': (lambda t, m, s: (edit(t, SD | BUYER, sample_set='other'), m, s),
                            METADATA_DIFFERS),
    'metadata-vintage': (lambda t, m, s: (edit(t, SD | BUYER, vintage='naics=2017'), m, s),
                         METADATA_DIFFERS),
    'unit-a-unknown': (lambda t, m, s: (edit(t, SD | SUPPLIER, unit_a=node('541519')), m, s),
                       UNITS),
    'measure-unknown': (lambda t, m, s: (edit(t, SD | BUYER, measure='link_share'), m, s),
                        MEASURES),
    'cell-without-supplier': (lambda t, m, s: (without(t, SD | SUPPLIER), m, s), MEASURES),
    'support-row-missing': (lambda t, m, s: (t, m, without(s, SD2)), SUPPORT_CELLS),
    'support-row-extra': (lambda t, m, s: (t, m, pl.concat([s, edit(s.filter(match(SD2)), SD2,
                                                                    unit_b=N541512)])),
                          SUPPORT_CELLS),
    'support-row-repeated': (lambda t, m, s: (t, m, pl.concat([s, s.filter(match(SD2))])),
                             SUPPORT_CELLS),
    'support-buyers': (lambda t, m, s: (t, m, edit(s, SD, b_buyers=1)), SUPPORT_CELLS),
    'b_above_n': (lambda t, m, s: (t, edit(m, {'node_id': N236220}, n_buyers=1), s),
                  FIRM_BOUNDS),
    's_zero': (lambda t, m, s: (edit(t, SD2 | SUPPLIER, n_unweighted=0, n_weighted=0.0,
                                     value=0.0), m, edit(s, SD2, s_suppliers=0)), FIRM_BOUNDS),
    'b_zero': (lambda t, m, s: (edit(t, SD2 | BUYER, n_unweighted=0, n_weighted=0.0, value=0.0),
                                m, edit(s, SD2, b_buyers=0)), FIRM_BOUNDS),
    'marginal-missing': (lambda t, m, s: (t, without(m, {'node_id': N541512}), s), FIRM_BOUNDS),
    'buyer-value': (lambda t, m, s: (edit(t, VD | BUYER, value=1.0), m, s), VALUES),
    'value-beyond-tolerance': (lambda t, m, s: (edit(t, SD | SUPPLIER, value=2 / 3 + 1e-11),
                                                m, s), VALUES),
    'weighted': (lambda t, m, s: (edit(t, SD | SUPPLIER, n_weighted=2.5), m, s), WEIGHTED),
    'buyer-weighted': (lambda t, m, s: (edit(t, SD | BUYER, n_weighted=1.0), m, s), WEIGHTED),
    'label-missing': (lambda t, m, s: (edit(t, VD | BUYER, flags=[SIZE_LABEL]), m, s), FLAGS),
    'label-extra': (lambda t, m, s: (edit(t, SD | SUPPLIER, flags=[INTRA_LABEL, SIZE_LABEL]),
                                     m, s), FLAGS),
    'size-label-missing': (lambda t, m, s: (edit(t, SD | BUYER, flags=[]), m, s), FLAGS),
    'other-label': (lambda t, m, s: (edit(t, SD | BUYER, flags=['other_label', SIZE_LABEL]),
                                     m, s), FLAGS),
    'wider-buyers': (lambda t, m, s: (t, m, edit(s, VD, b_including_intra_group=1)), FLAGS),
    'wider-suppliers': (lambda t, m, s: (t, m, edit(s, SD, s_including_intra_group=3)), FLAGS),
    'supplier-pairs': (lambda t, m, s: (t, edit(m, {'node_id': N541512}, n_supplier_pairs=2), s),
                       PAIR_SUMS),
    'buyer-pairs': (lambda t, m, s: (t, edit(m, {'node_id': N336411}, n_buyer_pairs=2), s),
                    PAIR_SUMS),
    'buyer-pairs-zero-node': (lambda t, m, s: (t, edit(m, {'node_id': N541511},
                                                       n_buyer_pairs=1), s), PAIR_SUMS),
    'marginal-wider': (lambda t, m, s: (t, edit(m, {'node_id': N541512},
                                                n_suppliers_including_intra_group=1), s),
                       MARGINALS),
    'marginal-buyers-partial': (lambda t, m, s: (t, edit(m, {'node_id': N336411},
                                                         n_buyers_partial=0), s), MARGINALS),
    'marginal-extra-node': (
        lambda t, m, s: (t, pl.concat([m, edit(m.filter(pl.col('node_id') == N336411),
                                               {'node_id': N336411}, node_id=node('111110'),
                                               n_buyer_pairs=0)]), s), MARGINALS),
    'marginal-order': (lambda t, m, s: (t, m.reverse(), s), MARGINALS),
    'support-amount': (lambda t, m, s: (t, m, edit(s, SD, amount_sum=Decimal('16.00'))), SUPPORT),
    'support-reports': (lambda t, m, s: (t, m, edit(s, SD, n_reports=5)), SUPPORT),
    'support-year': (lambda t, m, s: (t, m, edit(s, SD, l_fy2026=0)), SUPPORT),
    'support-wider-pairs': (lambda t, m, s: (t, m, edit(s, VD, l_including_intra_group=1)),
                            SUPPORT),
    'support-order-rows': (lambda t, m, s: (t, m, s.reverse()), SUPPORT),
}


@pytest.mark.parametrize('case', list(MORE_BREAKS))
def test_validator_rejects_more_breaks(case):
    change, message = MORE_BREAKS[case]
    with exactly(message):
        validate_vendor_links(broken(change), VALID_TABLE, NODE_IDS)


def test_valid_fixture_is_the_one_the_breaks_assume():
    result = valid()
    target, support_row, marginal = lookups(result)
    assert cells(result) == {(N541511, N236220), (N541511, N336411), (N541512, N236220)}
    summary = {(row['unit_a'], row['unit_b']): (row['s_suppliers'], row['b_buyers'],
                                                row['l_pairs'])
               for row in result.support.iter_rows(named=True)}
    assert summary == {(N541511, N236220): (2, 2, 3), (N541511, N336411): (1, 1, 1),
                       (N541512, N236220): (1, 1, 1)}
    assert target('supplier_share', N541511, N236220)['value'] == pytest.approx(2 / 3,
                                                                                abs=TOLERANCE)
    assert target('buyer_share', N541512, N236220)['flags'] == [INTRA_LABEL, SIZE_LABEL]
    assert target('buyer_share', N541512, N236220)['value'] == 0.5
    assert support_row(N541511, N236220)['amount_sum'] == Decimal('16.75')
    assert support_row(N541511, N236220)['n_reports'] == 4
    rows = {row['node_id']: row for row in result.marginals.iter_rows(named=True)}
    assert {key: tuple(row.values())[1:] for key, row in rows.items()} == {
        N236220: (0, 2, 0, 4, 0, 0, 0, 2),
        N336411: (0, 1, 0, 1, 0, 1, 0, 1),
        N541511: (3, 0, 4, 0, 1, 0, 3, 0),
        N541512: (1, 0, 1, 0, 0, 0, 2, 0),
    }
