'''Tests for the CPS flow target rows, companion tables and report.'''

import json
from decimal import Decimal

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from embedding_data.cps_flow_estimation import (
    ASEC_R,
    BOOTSTRAP_B,
    Variant,
    estimate_asec,
    estimate_monthly,
    household_draws,
)
from embedding_data.cps_flow_guards import (
    asec_flag_counts,
    funnel,
    guard_source_exceptions,
    product_frame,
    usable_guard_share,
)
from embedding_data.cps_flow_linkage import COUNT_COLUMNS, LINK_COLUMNS
from embedding_data.cps_flow_targets import (
    COMPANION_SCHEMAS,
    CONTRACTS,
    FLAG_REGISTRY,
    build_report,
    diagnostics_table,
    linked_pairs_table,
    n_unweighted_distribution,
    replicates_table,
    support_table,
    target_rows,
)
from embedding_data.cps_flow_units import UNIT_SCHEMA
from embedding_data.target_contract import TARGET_SCHEMA, write_targets

INDUSTRY, OCCUPATION = 'cps_industry_category', 'cps_occupation_category'
P1, P2 = '2025-01>2025-02', '2025-02>2025-03'
Y1, Y2 = 'asec-2025', 'asec-2026'
EE_STRICT = Variant('monthly_ee', 'industry', 'strict')
EE_SENS = Variant('monthly_ee', 'industry', 'sensitivity')
UE_SENS = Variant('monthly_ue', 'occupation', 'sensitivity')
ASEC_SENS = Variant('asec_retro', 'occupation', 'sensitivity')
UNIT_ROWS = [
    (INDUSTRY, '0170', 'mapped'), (INDUSTRY, '1370', 'mapped'),
    (INDUSTRY, '9920', 'no_naics_equivalent'), (INDUSTRY, '9890', 'special_military'),
    (OCCUPATION, '0010', 'mapped'), (OCCUPATION, '0020', 'mapped'),
    (OCCUPATION, '9830', 'no_soc_equivalent'), (OCCUPATION, '9840', 'special_military')]
X_CODES = ['8001', '8002', '8003', '8004', '8005', '8006']

# The Schemas section of the plan, restated column by column.
SCHEMAS = {
    'cps_category_units': {
        'unit': pl.String, 'unit_type': pl.String, 'code': pl.String, 'vintage': pl.String,
        'label': pl.String, 'status': pl.String, 'source_expression': pl.String,
        'membership_types': pl.List(pl.String), 'candidates': pl.List(pl.String),
        'candidate_node_ids': pl.List(pl.String), 'x_token': pl.String,
        'x_cross_check': pl.String, 'evidence_monthly': pl.String,
        'evidence_asec_current': pl.String, 'evidence_asec_last_year': pl.String,
        'bls_evidence': pl.String, 'list_locator': pl.String, 'pums_locator': pl.String,
        'reference_id': pl.String},
    'cps_flow_support': {
        'product': pl.String, 'dimension': pl.String, 'policy': pl.String, 'kind': pl.String,
        'unit_a': pl.String, 'unit_b': pl.String, 'period': pl.String,
        'n_unweighted': pl.UInt64, 'mass': pl.Float64, 'reason': pl.String,
        'replicates': pl.List(pl.UInt16)},
    'cps_flow_replicates': {
        'product': pl.String, 'dimension': pl.String, 'policy': pl.String,
        'unit_a': pl.String, 'unit_b': pl.String, 'replicate': pl.UInt16,
        'numerator': pl.Float64, 'denominator': pl.Float64, 'estimate': pl.Float64,
        'status': pl.String},
    'cps_flow_diagnostics': {
        'topic': pl.String, 'product': pl.String, 'dimension': pl.String, 'policy': pl.String,
        'period': pl.String, 'reason': pl.String, 'exclusive': pl.Boolean,
        'count': pl.UInt64, 'count_cpsidp': pl.UInt64},
    'cps_linked_pairs': {
        'CPSIDV': pl.Int64, 'CPSID': pl.Int64, 'month_a': pl.String, 'month_b': pl.String,
        'link_type': pl.String, 'source_row_a': pl.UInt64, 'source_row_b': pl.UInt64,
        'mish_a': pl.Int64, 'mish_b': pl.Int64, 'empstat_a': pl.Int64, 'empstat_b': pl.Int64,
        'ind_a': pl.String, 'ind_b': pl.String, 'occ_a': pl.String, 'occ_b': pl.String,
        'qempstat_a': pl.Int64, 'qempstat_b': pl.Int64, 'qind_a': pl.Int64, 'qind_b': pl.Int64,
        'qocc_a': pl.Int64, 'qocc_b': pl.Int64, 'empsame_b': pl.Int64, 'actsame_b': pl.Int64,
        'guard_industry': pl.String, 'guard_occupation': pl.String, 'weight_a': pl.Float64,
        'weight_status': pl.String, 'products': pl.List(pl.String)},
}


def unit_frame(x_checks: tuple = ()) -> pl.DataFrame:
    '''A registry frame: the list rows above, then one X occupation row for each check.'''
    rows = [(unit_type, code, status) for unit_type, code, status in UNIT_ROWS]
    rows += [(OCCUPATION, code, 'mapped') for code in X_CODES[:len(x_checks)]]
    checks = [None] * len(UNIT_ROWS) + list(x_checks)
    units = []
    for (unit_type, code, status), check in zip(rows, checks):
        unit = dict.fromkeys(UNIT_SCHEMA)
        unit.update(unit=f'feature:{unit_type}:{code}', unit_type=unit_type, code=code,
                    vintage='v', label='Title', status=status, membership_types=[],
                    candidates=[], candidate_node_ids=[], x_cross_check=check,
                    list_locator='locator', reference_id='receipt')
        units.append(unit)
    return pl.DataFrame(units, schema=UNIT_SCHEMA)


def monthly(rows):
    '''A monthly records frame from `(CPSID, unit_a, unit_b, period, weight)` rows.'''
    cpsids, units_a, units_b, periods, weights = (list(column) for column in zip(*rows))
    return pl.DataFrame({
        'CPSID': pl.Series(cpsids, dtype=pl.Int64),
        'unit_a': pl.Series(units_a, dtype=pl.String),
        'unit_b': pl.Series(units_b, dtype=pl.String),
        'period': pl.Series(periods, dtype=pl.String),
        'weight': pl.Series([Decimal(value) for value in weights], dtype=pl.Decimal(38, 4)),
    })


def replicates_of(weight: str, zero_at: tuple = ()) -> list[str]:
    '''The 160 replicate weights of a person, `0` at the replicate numbers in `zero_at`.'''
    return ['0' if number in zero_at else weight for number in range(1, ASEC_R + 1)]


def asec(rows):
    '''An ASEC records frame from `(unit_a, unit_b, period, weight, replicates)` rows.'''
    units_a, units_b, periods, weights, replicates = (list(column) for column in zip(*rows))
    columns = {
        'unit_a': pl.Series(units_a, dtype=pl.String),
        'unit_b': pl.Series(units_b, dtype=pl.String),
        'period': pl.Series(periods, dtype=pl.String),
        'weight': pl.Series([Decimal(value) for value in weights], dtype=pl.Decimal(38, 4)),
    }
    for number in range(1, ASEC_R + 1):
        columns[f'rep{number}'] = pl.Series(
            [Decimal(values[number - 1]) for values in replicates], dtype=pl.Decimal(38, 4))
    return pl.DataFrame(columns)


def estimates_of(records: dict) -> dict:
    '''Estimate each variant of `records`; the monthly products share one set of draws.'''
    households = sorted({cpsid for frame in records.values() if 'CPSID' in frame.columns
                         for cpsid in frame['CPSID']})
    draws = household_draws(households)
    return {variant: (estimate_monthly(frame, variant, draws) if 'CPSID' in frame.columns
                      else estimate_asec(frame, variant))
            for variant, frame in records.items()}


@pytest.fixture(scope='module')
def estimates():
    '''Four variants. The `0010` and `1370` origins have one household each, so some
    bootstrap replicates miss them; ASEC replicate 5 has no weight in the `0010` origin.'''
    strict = [(1, '0170', '1370', P1, '10.5'), (2, '1370', '0170', P1, '20'),
              (3, '0170', '1370', P2, '30')]
    sensitivity = [*strict, (1, '0170', '9890', P2, '5'), (4, '9890', '0170', P1, '7')]
    unemployed = [(1, '0010', '0020', P1, '12'), (2, '0020', '0010', P1, '8'),
                  (3, '0020', '0010', P2, '9'), (4, '0020', '0020', P2, '3')]
    asec_rows = [('0010', '0020', Y1, '100', replicates_of('100', (5,))),
                 ('0010', '9840', Y2, '50', replicates_of('50', (5,))),
                 ('0020', '0010', Y1, '40', replicates_of('40')),
                 ('9840', '0010', Y2, '10', replicates_of('10'))]
    return estimates_of({
        EE_STRICT: monthly(strict), EE_SENS: monthly(sensitivity), UE_SENS: monthly(unemployed),
        ASEC_SENS: asec(asec_rows)})


@pytest.fixture(scope='module')
def rows(estimates):
    return target_rows(estimates, unit_frame())


def variant_rows(frame: pl.DataFrame, universe: str, unit_type: str) -> pl.DataFrame:
    return frame.filter(pl.col('universe').eq(universe) & pl.col('unit_a_type').eq(unit_type))


# The target rows.

def test_target_rows_pass_the_contract_with_frozen_metadata(estimates, rows, tmp_path):
    assert list(rows.schema.items()) == list(TARGET_SCHEMA.items())
    record = write_targets(rows, tmp_path / 'cps_job_flows.parquet')
    assert record['rows'] == rows.height == sum(
        found.targets.height for found in estimates.values())
    expected = {
        EE_STRICT: ('monthly_ee:strict', INDUSTRY, 'census-industry-2022',
                    'cps-basic-2025-01-to-2026-09'),
        EE_SENS: ('monthly_ee:sensitivity', INDUSTRY, 'census-industry-2022',
                  'cps-basic-2025-01-to-2026-09'),
        UE_SENS: ('monthly_ue:sensitivity', OCCUPATION, 'census-occupation-2018',
                  'cps-basic-2025-01-to-2026-09'),
        ASEC_SENS: ('asec_retro:sensitivity', OCCUPATION, 'census-occupation-2018',
                    'cps-asec-2025-2026'),
    }
    for variant, (universe, unit_type, vintage, sample_set) in expected.items():
        found = estimates[variant].targets
        part = variant_rows(rows, universe, unit_type)
        assert part.height == found.height
        assert part.select('source', 'family', 'unit_a_type', 'unit_b_type', 'vintage',
                           'sample_set', 'universe').unique().rows() == [
            ('cps', 'job_change_flow', unit_type, unit_type, vintage, sample_set, universe)]
        for side in ('unit_a', 'unit_b'):
            assert part[side].to_list() == [
                f'feature:{unit_type}:{code}' for code in found[side]]
        for column in ('measure', 'value', 'se', 'n_unweighted', 'n_weighted'):
            assert part[column].to_list() == found[column].to_list()
    assert ('feature:cps_industry_category:0170' in rows['unit_a'].to_list()
            and 'feature:cps_occupation_category:0010' in rows['unit_b'].to_list())


def test_a_share_row_keeps_the_mass_over_k_of_its_total(rows):
    for universe in ('monthly_ee:strict', 'asec_retro:sensitivity'):
        part = rows.filter(pl.col('universe').eq(universe))
        totals = part.filter(pl.col('measure').eq('average_total'))
        shares = part.filter(pl.col('measure').eq('forward_share'))
        assert shares.height > 0
        by_cell = {(a, b): (value, weighted) for a, b, value, weighted in totals.select(
            'unit_a', 'unit_b', 'value', 'n_weighted').iter_rows()}
        for a, b, value, weighted in shares.select(
                'unit_a', 'unit_b', 'value', 'n_weighted').iter_rows():
            assert weighted == by_cell[a, b][0] == by_cell[a, b][1]
            assert value != weighted


def test_flags_follow_the_registry(rows):
    assert FLAG_REGISTRY == ('bootstrap_approximate', 'size_gate_pending', 'special_military',
                             'unguarded_upper_bound')
    monthly_flags = ['bootstrap_approximate', 'size_gate_pending']
    asec_flags = ['size_gate_pending', 'unguarded_upper_bound']
    by_universe = dict(rows.group_by('universe').agg(pl.col('flags')).iter_rows())
    assert by_universe['monthly_ee:strict'] == [monthly_flags] * len(
        by_universe['monthly_ee:strict'])
    assert by_universe['monthly_ue:sensitivity'] == [monthly_flags] * len(
        by_universe['monthly_ue:sensitivity'])
    for universe, unit_type, special_code, plain in (
            ('monthly_ee:sensitivity', INDUSTRY, '9890', monthly_flags),
            ('asec_retro:sensitivity', OCCUPATION, '9840', asec_flags)):
        part = variant_rows(rows, universe, unit_type)
        special = f'feature:{unit_type}:{special_code}'
        ends = part.select(
            (pl.col('unit_a').eq(special) | pl.col('unit_b').eq(special)).alias('end'))['end']
        assert ends.any() and not ends.all()
        assert part['flags'].to_list() == [
            sorted([*plain, 'special_military']) if end else plain for end in ends]
    # The special is an origin in some rows and a destination in others.
    sensitivity = variant_rows(rows, 'monthly_ee:sensitivity', INDUSTRY)
    flagged = sensitivity.filter(pl.col('flags').list.contains('special_military'))
    assert 'feature:cps_industry_category:9890' in flagged['unit_a'].to_list()
    assert 'feature:cps_industry_category:9890' in flagged['unit_b'].to_list()
    strict = rows.filter(pl.col('universe').eq('monthly_ee:strict'))
    assert 'feature:cps_industry_category:9890' not in strict['unit_a'].to_list()
    assert 'feature:cps_industry_category:9890' not in strict['unit_b'].to_list()
    for flags in rows['flags']:
        assert flags.to_list() == sorted(set(flags))


def test_se_method_follows_the_se(rows):
    seen = set()
    for universe, se, method in rows.select('universe', 'se', 'se_method').iter_rows():
        product = universe.split(':')[0]
        expected = 'none' if se is None else 'replicate' if product == 'asec_retro' else (
            'bootstrap')
        assert method == expected
        seen.add((product, se is None))
    assert seen == {(product, missing) for product in ('monthly_ee', 'monthly_ue', 'asec_retro')
                    for missing in (True, False)}


def test_target_rows_refuse_a_wrong_unit_or_label(estimates):
    units = unit_frame()
    strict_with_special = estimates_of({EE_STRICT: monthly([
        (1, '0170', '9890', P1, '5'), (2, '0170', '1370', P1, '5')])})
    with pytest.raises(ValueError, match='strict'):
        target_rows(strict_with_special, units)
    strict_origin_special = estimates_of({EE_STRICT: monthly([
        (1, '9890', '0170', P1, '5'), (2, '0170', '1370', P1, '5')])})
    with pytest.raises(ValueError, match='strict'):
        target_rows(strict_origin_special, units)
    for code in ('9999', '9920'):
        for records in ([(1, code, '0170', P1, '5')], [(1, '0170', code, P1, '5')]):
            with pytest.raises(ValueError, match='registry'):
                target_rows(estimates_of({EE_SENS: monthly(records)}), units)
    wrong_dimension = Variant('monthly_ee', 'occupation', 'sensitivity')
    with pytest.raises(ValueError, match='registry'):
        target_rows(estimates_of({wrong_dimension: monthly([(1, '0170', '1370', P1, '5')])}),
                    units)
    with pytest.raises(ValueError, match='labels'):
        target_rows({EE_STRICT: estimates[EE_SENS]}, units)
    with pytest.raises(ValueError, match='labels'):
        target_rows({Variant('monthly_ue', 'industry', 'sensitivity'): estimates[UE_SENS]},
                    units)
    with pytest.raises(ValueError, match='labels'):
        target_rows({Variant('monthly_ee', 'occupation', 'sensitivity'): estimates[UE_SENS]},
                    units)


# The companion tables.

def assert_sorted(table: pl.DataFrame, columns: list[str]) -> None:
    '''Check, with Python's ordering and nulls first, that rows follow `columns` in order.'''
    keys = [tuple((value is not None, value) for value in row)
            for row in table.select(columns).iter_rows()]
    assert keys == sorted(keys)


def test_companion_tables_have_the_fixed_ordered_schemas(estimates, rows):
    assert {name: list(schema.items()) for name, schema in COMPANION_SCHEMAS.items()} == {
        name: list(schema.items()) for name, schema in SCHEMAS.items()}
    assert support_table(estimates).schema == COMPANION_SCHEMAS['cps_flow_support']
    assert replicates_table(estimates).schema == COMPANION_SCHEMAS['cps_flow_replicates']
    assert diagnostics_table(diagnostic_parts()).schema == COMPANION_SCHEMAS[
        'cps_flow_diagnostics']
    assert linked_pairs_table(pair_frame(PAIR_ROWS)).schema == COMPANION_SCHEMAS[
        'cps_linked_pairs']
    assert unit_frame().schema == COMPANION_SCHEMAS['cps_category_units']
    assert list(support_table(estimates).schema) == list(SCHEMAS['cps_flow_support'])
    # Rows sort as the Schemas section says, whatever order the inputs arrive in.
    assert_sorted(support_table(estimates), ['product', 'dimension', 'policy', 'kind',
                                             'unit_a', 'unit_b', 'period'])
    assert_sorted(replicates_table(estimates), ['product', 'dimension', 'policy', 'unit_a',
                                                'unit_b', 'replicate'])
    diagnostics = diagnostics_table(diagnostic_parts())
    assert_sorted(diagnostics, list(SCHEMAS['cps_flow_diagnostics']))
    assert_sorted(linked_pairs_table(pair_frame(PAIR_ROWS)),
                  ['month_a', 'link_type', 'CPSIDV'])


def test_support_rows_sort_by_every_column_in_order(estimates):
    forward = support_table(estimates)
    backward = support_table(dict(reversed(list(estimates.items()))))
    assert_frame_equal(forward, backward)
    assert forward.height == sum(found.support.height for found in estimates.values())
    keys = [(product, dimension, policy, kind, unit_a, unit_b or '', period)
            for product, dimension, policy, kind, unit_a, unit_b, period in forward.select(
                'product', 'dimension', 'policy', 'kind', 'unit_a', 'unit_b',
                'period').iter_rows()]
    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys)
    assert set(forward['kind']) == {'cell', 'denominator', 'undefined_share'}
    assert forward.filter(pl.col('kind').eq('denominator'))['unit_b'].null_count() == (
        forward.filter(pl.col('kind').eq('denominator')).height)


def test_replicate_rows_sort_by_variant_cell_and_replicate(estimates):
    forward = replicates_table(estimates)
    assert_frame_equal(forward, replicates_table(dict(reversed(list(estimates.items())))))
    monthly_cells = sum(
        found.replicates.height for variant, found in estimates.items()
        if variant.product != 'asec_retro')
    assert forward.height == monthly_cells + estimates[ASEC_SENS].replicates.height
    assert forward.height == sum(found.replicates.height for found in estimates.values())
    keys = list(forward.select('product', 'dimension', 'policy', 'unit_a', 'unit_b',
                               'replicate').iter_rows())
    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys)
    assert BOOTSTRAP_B == 200 and ASEC_R == 160


# The diagnostics.

LINK_DEFAULTS = {
    'CPSIDV': 1, 'CPSID': 10, 'source_row_a': 0, 'source_row_b': 1, 'month_a': '2025-01',
    'month_b': '2025-02', 'link_type': 'one_month', 'mish_a': 1, 'mish_b': 2, 'empstat_a': 10,
    'empstat_b': 10, 'ind_a': '0170', 'ind_b': '1370', 'occ_a': '0010', 'occ_b': '0020',
    'qempstat_a': 0, 'qempstat_b': 0, 'qind_a': 0, 'qind_b': 0, 'qocc_a': 0, 'qocc_b': 0,
    'empsame_b': 1, 'actsame_b': 99, 'cpsidp_a': 1, 'weight_status': 'positive'}
LINK_STRINGS = {'month_a', 'month_b', 'link_type', 'ind_a', 'ind_b', 'occ_a', 'occ_b',
                'weight_status'}
LINK_SCHEMA = {
    name: pl.String if name in LINK_STRINGS
    else pl.UInt64 if name.startswith('source_row') else pl.Int64 for name in LINK_DEFAULTS}
ASEC_DEFAULTS = {
    'CPSID': 1, 'EMPSTAT': 10, 'INDLY': '0170', 'IND': '1370', 'OCCLY': '0010', 'OCC': '0020',
    'QEMPSTAT': 0, 'QIND': 0, 'QOCC': 0, 'QOCCLY': 0, 'weight_status': 'positive'}
ASEC_SCHEMA = {name: pl.String if isinstance(value, str) else pl.Int64
               for name, value in ASEC_DEFAULTS.items()}
# Eleven one-month links: every first-exclusion reason of the employer-change product occurs.
LINK_CHANGES = [
    {}, {'weight_status': 'null'}, {'weight_status': 'zero'}, {'empstat_b': 21},
    {'empsame_b': 99}, {'empsame_b': 2, 'actsame_b': 1, 'ind_b': '0170', 'occ_b': '0010'},
    {'empsame_b': 2, 'actsame_b': 1}, {'empstat_a': 21}, {'ind_b': '9890', 'occ_b': '9840'},
    {'ind_a': '0000', 'occ_a': '0000', 'mish_b': 5}, {'empsame_b': 2, 'actsame_b': 99}]
PERSON_CHANGES = [
    {}, {'weight_status': 'null'}, {'EMPSTAT': 21}, {'INDLY': '0000', 'OCCLY': '0000'},
    {'IND': '0170', 'OCC': '0010', 'INDLY': '0170', 'OCCLY': '0010'}]


def links():
    return pl.LazyFrame([{**LINK_DEFAULTS, **change, 'CPSIDV': number}
                         for number, change in enumerate(LINK_CHANGES, start=1)],
                        schema=LINK_SCHEMA)


def people():
    return pl.LazyFrame([{**ASEC_DEFAULTS, **change, 'CPSID': number}
                         for number, change in enumerate(PERSON_CHANGES, start=1)],
                        schema=ASEC_SCHEMA)


def real_funnels() -> dict:
    found = {}
    for product in ('monthly_ee', 'monthly_ue', 'asec_retro'):
        for dimension in ('industry', 'occupation'):
            source = people() if product == 'asec_retro' else links()
            frame = product_frame(source, product, dimension, units=unit_frame())
            found[f'{product}:{dimension}'] = funnel(frame, product, dimension)
    return found


def diagnostic_parts() -> dict:
    return {
        'value_classes': {
            'monthly/IND': {'mapped': 90, 'not_in_universe': 7, 'special': 3,
                            'special_by_year': {'2025': 2, '2026': 1}},
            'asec/OCCLY': {'mapped': 20, 'not_in_universe': 5, 'special': 0,
                           'special_by_year': {}}},
        'links': pl.DataFrame(
            [('2025-08', '2025-09', 'one_month', 100, 98, 3),
             ('2025-09', '2025-11', 'two_month', 40, 41, 0)],
            schema=dict(zip(COUNT_COLUMNS, [pl.String] * 3 + [pl.Int64] * 3)), orient='row'),
        'weights': {'null': 2, 'zero': 3, 'positive': 40},
        'funnels': real_funnels(),
        'guards': {
            'states': {'industry': {'changed': 20, 'same': 15, 'unusable': 5},
                       'occupation': {'changed': 25, 'same': 10, 'unusable': 6}},
            'noise_after_duty_change': 4,
            'source_exceptions': guard_source_exceptions(links()),
            'usable_share': usable_guard_share(links())},
        'evidence': {
            'monthly': {'monthly_ee:industry': {'flag:QIND:allocated': 2, 'special_military': 1},
                        'monthly_ue:occupation': {'flag_unavailable:QOCC': 3}},
            'asec_flags': asec_flag_counts(people())},
        'specials': {'monthly_ee:industry': 2, 'asec_retro:occupation': 1},
    }


def string_key(row: tuple) -> tuple:
    return (row[0], row[1] or '', row[2] or '', row[3] or '', row[4], row[5], row[6], row[7],
            -1 if row[8] is None else row[8])


def test_diagnostics_label_exclusive_funnels_and_overlaps():
    parts = diagnostic_parts()
    table = diagnostics_table(parts)
    rows = table.rows()
    assert rows == sorted(rows, key=string_key)
    funnels = [row for row in rows if row[0] == 'funnel']
    assert funnels and all(row[6] is True for row in funnels)
    for product, sources in (('monthly_ee', len(LINK_CHANGES)), ('monthly_ue', len(LINK_CHANGES)),
                             ('asec_retro', len(PERSON_CHANGES))):
        for dimension in ('industry', 'occupation'):
            mine = [row for row in funnels if row[1] == product and row[2] == dimension]
            assert sum(row[7] for row in mine) == sources
            assert {row[5] for row in mine} == set(
                parts['funnels'][f'{product}:{dimension}']['reason'])
            assert all(row[3] is None and row[4] == 'all' and row[8] is None for row in mine)
    assert len(funnels) == sum(frame.height for frame in parts['funnels'].values())
    overlapping = [row for row in rows if row[0] != 'funnel']
    assert {row[0] for row in overlapping} == {
        'value_class', 'links', 'weight', 'guard', 'evidence', 'special'}
    assert all(row[6] is False for row in overlapping)


def test_diagnostics_rows_of_every_topic():
    parts = diagnostic_parts()
    rows = [row for row in diagnostics_table(parts).rows() if row[0] != 'funnel']
    allp = 'all'
    expected = [
        ('value_class', None, None, None, allp, 'monthly/IND/mapped', False, 90, None),
        ('value_class', None, None, None, allp, 'monthly/IND/not_in_universe', False, 7, None),
        ('value_class', None, None, None, allp, 'monthly/IND/special', False, 3, None),
        ('value_class', None, None, None, allp, 'asec/OCCLY/mapped', False, 20, None),
        ('value_class', None, None, None, allp, 'asec/OCCLY/not_in_universe', False, 5, None),
        ('value_class', None, None, None, allp, 'asec/OCCLY/special', False, 0, None),
        ('links', None, None, None, '2025-08>2025-09', 'one_month', False, 100, 98),
        ('links', None, None, None, '2025-08>2025-09', 'other_gap_matches_one_month', False, 3,
         None),
        ('links', None, None, None, '2025-09>2025-11', 'two_month', False, 40, 41),
        ('links', None, None, None, '2025-09>2025-11', 'other_gap_matches_two_month', False, 0,
         None),
        ('weight', None, None, None, allp, 'null', False, 2, None),
        ('weight', None, None, None, allp, 'zero', False, 3, None),
        ('weight', None, None, None, allp, 'positive', False, 40, None),
        ('guard', 'monthly_ee', 'industry', None, allp, 'changed', False, 20, None),
        ('guard', 'monthly_ee', 'industry', None, allp, 'same', False, 15, None),
        ('guard', 'monthly_ee', 'industry', None, allp, 'unusable', False, 5, None),
        ('guard', 'monthly_ee', 'occupation', None, allp, 'changed', False, 25, None),
        ('guard', 'monthly_ee', 'occupation', None, allp, 'same', False, 10, None),
        ('guard', 'monthly_ee', 'occupation', None, allp, 'unusable', False, 6, None),
        ('guard', 'monthly_ee', 'industry', None, allp, 'noise_after_duty_change', False, 4,
         None),
        ('guard', None, None, None, allp, 'empsame_in_mish_1_or_5', False, 1, None),
        ('evidence', 'monthly_ee', 'industry', None, allp, 'flag:QIND:allocated', False, 2, None),
        ('evidence', 'monthly_ee', 'industry', None, allp, 'special_military', False, 1, None),
        ('evidence', 'monthly_ue', 'occupation', None, allp, 'flag_unavailable:QOCC', False, 3,
         None),
        ('special', 'monthly_ee', 'industry', None, allp, 'special_end', False, 2, None),
        ('special', 'asec_retro', 'occupation', None, allp, 'special_end', False, 1, None),
    ]
    for variable, by_empstat in parts['evidence']['asec_flags'].items():
        for empstat, by_value in by_empstat.items():
            for value, count in by_value.items():
                expected.append(('evidence', 'asec_retro', None, None, allp,
                                 f'{variable}/{empstat}/{value}', False, count, None))
    assert sorted(rows, key=string_key) == sorted(expected, key=string_key)
    assert len(rows) == len(expected)
    assert parts['guards']['source_exceptions'] == 1
    assert any(row[5].startswith('QIND/10/') for row in rows)


# The linked pairs.

PAIR_STRINGS = {'month_a', 'month_b', 'link_type', 'ind_a', 'ind_b', 'occ_a', 'occ_b',
                'weight_status'}
PAIR_SCHEMA = {
    **{name: pl.String if name in PAIR_STRINGS else pl.UInt64 if name.startswith('source_row')
       else pl.Int64 for name in LINK_COLUMNS},
    'weight_a': pl.Decimal(38, 4), 'weight_status': pl.String, 'products': pl.List(pl.String)}
PAIR_DEFAULTS = {**{name: LINK_DEFAULTS[name] for name in LINK_COLUMNS if name in LINK_DEFAULTS},
                 'weight_a': Decimal('123.4567'), 'weight_status': 'positive',
                 'products': ['monthly_ee:industry:strict']}
PAIR_ROWS = [
    {'CPSIDV': 9, 'CPSID': 91, 'month_a': '2025-02', 'products': []},
    {'CPSIDV': 8, 'month_a': '2025-01', 'link_type': 'two_month', 'month_b': '2025-03',
     'mish_b': 3, 'empsame_b': 2, 'actsame_b': 2, 'weight_a': None,
     'weight_status': 'not_linkable'},
    {'CPSIDV': 7, 'CPSID': 71, 'month_a': '2025-01', 'empstat_a': 12, 'empsame_b': 2,
     'actsame_b': 2, 'weight_a': Decimal('0.0001'),
     'products': ['monthly_ue:industry:sensitivity', 'monthly_ee:industry:sensitivity',
                  'monthly_ee:industry:strict']},
    {'CPSIDV': 3, 'month_a': '2025-01', 'empstat_b': 12, 'empsame_b': 2, 'actsame_b': 1,
     'weight_status': 'zero', 'weight_a': Decimal('0')},
    {'CPSIDV': 4, 'month_a': '2025-01', 'empsame_b': 99, 'actsame_b': 99},
    {'CPSIDV': 5, 'month_a': '2025-01', 'empstat_b': 21},
    {'CPSIDV': 6, 'month_a': '2025-01', 'empstat_a': 21, 'weight_status': 'null',
     'weight_a': None},
    {'CPSIDV': 2, 'month_a': '2025-01', 'empstat_a': 21, 'empstat_b': 22},
    {'CPSIDV': 1, 'month_a': '2025-01'},
]


def pair_frame(changes: list[dict]) -> pl.DataFrame:
    return pl.DataFrame([{**PAIR_DEFAULTS, **change} for change in changes],
                        schema=PAIR_SCHEMA)


def test_linked_pairs_carry_guards_weights_and_sorted_products():
    table = linked_pairs_table(pair_frame(PAIR_ROWS))
    assert list(table.schema) == list(SCHEMAS['cps_linked_pairs'])
    assert 'cpsidp_a' not in table.columns
    by_cpsidv = {row['CPSIDV']: row for row in table.iter_rows(named=True)}
    guards = {cpsidv: (row['guard_industry'], row['guard_occupation'])
              for cpsidv, row in by_cpsidv.items()}
    assert guards == {
        1: ('changed', 'changed'), 2: (None, None), 3: ('same', 'same'),
        4: ('unusable', 'unusable'), 5: (None, None), 6: (None, None),
        7: ('same', 'changed'), 8: ('same', 'changed'), 9: ('changed', 'changed')}
    assert by_cpsidv[7]['products'] == ['monthly_ee:industry:sensitivity',
                                        'monthly_ee:industry:strict',
                                        'monthly_ue:industry:sensitivity']
    assert by_cpsidv[9]['products'] == []
    assert by_cpsidv[1]['products'] == ['monthly_ee:industry:strict']
    assert by_cpsidv[7]['weight_a'] == 0.0001 and by_cpsidv[1]['weight_a'] == 123.4567
    assert by_cpsidv[3]['weight_a'] == 0.0 and by_cpsidv[8]['weight_a'] is None
    assert by_cpsidv[8]['weight_status'] == 'not_linkable'
    assert by_cpsidv[6]['weight_status'] == 'null' and by_cpsidv[6]['weight_a'] is None
    assert by_cpsidv[3]['weight_status'] == 'zero'
    assert by_cpsidv[7]['CPSID'] == 71 and by_cpsidv[7]['qocc_b'] == 0


def test_linked_pairs_sort_by_month_link_type_and_person():
    table = linked_pairs_table(pair_frame(PAIR_ROWS))
    assert table.select('month_a', 'link_type', 'CPSIDV').rows() == [
        ('2025-01', 'one_month', 1), ('2025-01', 'one_month', 2), ('2025-01', 'one_month', 3),
        ('2025-01', 'one_month', 4), ('2025-01', 'one_month', 5), ('2025-01', 'one_month', 6),
        ('2025-01', 'one_month', 7), ('2025-01', 'two_month', 8),
        ('2025-02', 'one_month', 9)]
    late_person = pair_frame([
        {'CPSIDV': 1, 'month_a': '2025-09', 'link_type': 'two_month'},
        {'CPSIDV': 9, 'month_a': '2025-09', 'link_type': 'one_month'}])
    assert linked_pairs_table(late_person)['CPSIDV'].to_list() == [9, 1]


def test_linked_pairs_refuse_an_undelivered_answer():
    with pytest.raises(ValueError):
        linked_pairs_table(pair_frame([{'empsame_b': 3}]))
    with pytest.raises(ValueError):
        linked_pairs_table(pair_frame([{'actsame_b': None}]))


# The distribution and the report.

def counts_frame(counts: list[int], measure: str = 'average_total') -> pl.DataFrame:
    return pl.DataFrame({'measure': [measure] * len(counts), 'n_unweighted': counts},
                        schema={'measure': pl.String, 'n_unweighted': pl.UInt64})


def test_n_unweighted_distribution_has_the_fixed_keys():
    found = n_unweighted_distribution(counts_frame([5, 1, 30, 10]))
    assert list(found) == ['cells', 'min', 'max', 'p10', 'p25', 'p50', 'p75', 'p90',
                           'at_least']
    assert list(found['at_least']) == ['1', '2', '5', '10', '20', '30', '50', '100']
    assert found['cells'] == 4 and found['min'] == 1 and found['max'] == 30
    assert json.loads(json.dumps(found)) == found


def test_distribution_percentiles_use_the_nearest_rank():
    ten = n_unweighted_distribution(counts_frame([3, 9, 1, 7, 5, 2, 10, 8, 4, 6]))
    assert (ten['cells'], ten['min'], ten['max']) == (10, 1, 10)
    assert [ten[name] for name in ('p10', 'p25', 'p50', 'p75', 'p90')] == [1, 3, 5, 8, 9]
    seven = n_unweighted_distribution(counts_frame([70, 10, 20, 30, 40, 50, 60]))
    assert [seven[name] for name in ('p10', 'p25', 'p50', 'p75', 'p90')] == [
        10, 20, 40, 60, 70]
    twenty = n_unweighted_distribution(counts_frame(list(range(20, 0, -1))))
    assert [twenty[name] for name in ('p10', 'p25', 'p50', 'p75', 'p90')] == [2, 5, 10, 15, 18]
    one = n_unweighted_distribution(counts_frame([7]))
    assert [one[name] for name in ('p10', 'p25', 'p50', 'p75', 'p90')] == [7] * 5
    assert (one['cells'], one['min'], one['max']) == (1, 7, 7)


def test_distribution_counts_the_cells_at_each_threshold():
    counts = [1, 2, 2, 5, 9, 10, 19, 20, 29, 30, 49, 50, 99, 100, 150]
    found = n_unweighted_distribution(counts_frame(counts[::-1]))
    assert found['at_least'] == {'1': 15, '2': 14, '5': 12, '10': 10, '20': 8, '30': 6,
                                 '50': 4, '100': 2}
    assert found['cells'] == 15 and found['max'] == 150


def test_distribution_reads_only_the_average_total_rows():
    both = pl.concat([counts_frame([1, 2, 3]), counts_frame([500, 600], 'forward_share')])
    assert n_unweighted_distribution(both) == n_unweighted_distribution(counts_frame([1, 2, 3]))
    with pytest.raises(ValueError):
        n_unweighted_distribution(counts_frame([4], 'forward_share'))


def report_tables(estimates, rows, units) -> dict:
    parts = diagnostic_parts()
    return {
        'cps_job_flows': rows, 'cps_category_units': units,
        'cps_flow_support': support_table(estimates),
        'cps_flow_replicates': replicates_table(estimates),
        'cps_flow_diagnostics': diagnostics_table(parts),
        'cps_linked_pairs': linked_pairs_table(pair_frame(PAIR_ROWS))}


REPORT_KEYS = {
    'schema_version', 'run_id', 'contracts', 'v11', 'value_classes', 'specials',
    'x_categories', 'linkage', 'weights', 'funnels', 'usable_guard_share',
    'guard_source_exceptions', 'asec_flags_by_empstat', 'n_unweighted_distribution', 'tables'}


def test_report_has_the_fixed_keys_and_no_row_content(estimates, rows):
    units = unit_frame(('equal', 'equal', 'equal', 'strict_subset', 'strict_subset',
                        'not_delivered_no_pums_list'))
    tables = report_tables(estimates, rows, units)
    tables['cps_linked_pairs'] = linked_pairs_table(pair_frame([
        {'CPSIDV': 7777701, 'CPSID': 8888801}, {'CPSIDV': 7777702, 'CPSID': 8888802}]))
    report = build_report(run_id='run_1', parts=diagnostic_parts(), tables=tables)
    assert set(report) == REPORT_KEYS and len(report) == len(REPORT_KEYS)
    assert report['schema_version'] == 'cps-job-flows-v1' and report['run_id'] == 'run_1'
    assert report['contracts'] == {'bundle': 'cps-job-flows-v1', 'targets': 'targets-v1',
                                   'references': 'cps-job-flows-references-v1'} == CONTRACTS
    assert report['v11']['unparseable_values'] == 0
    assert report['v11']['statement'] == 'zero unparseable CPS values'
    assert report['tables']['cps_linked_pairs'] == {'rows': 2}
    text = json.dumps(report)
    assert json.loads(text) == report
    for fixture_id in ('7777701', '7777702', '8888801', '8888802'):
        assert fixture_id not in text
    for forbidden in ('CPSID', 'household', 'source_row', 'weight_a'):
        assert forbidden not in text


def test_report_counts_value_classes_specials_and_x_categories(estimates, rows):
    parts = diagnostic_parts()
    tables = report_tables(estimates, rows, unit_frame(
        ('equal', 'equal', 'equal', 'strict_subset', 'strict_subset',
         'not_delivered_no_pums_list')))
    report = build_report(run_id='r', parts=parts, tables=tables)
    assert report['value_classes'] == {
        'monthly/IND': {'mapped': 90, 'not_in_universe': 7, 'special': 3},
        'asec/OCCLY': {'mapped': 20, 'not_in_universe': 5, 'special': 0}}
    assert report['specials'] == {'monthly/IND/2025': 2, 'monthly/IND/2026': 1}
    assert report['x_categories'] == {'equal': 3, 'strict_subset': 2,
                                      'not_delivered_no_pums_list': 1}
    plain = build_report(run_id='r', parts=parts,
                         tables=report_tables(estimates, rows, unit_frame()))
    assert plain['x_categories'] == {'equal': 0, 'strict_subset': 0,
                                     'not_delivered_no_pums_list': 0}


def test_report_counts_linkage_weights_and_guards(estimates, rows):
    parts = diagnostic_parts()
    report = build_report(run_id='r', parts=parts,
                          tables=report_tables(estimates, rows, unit_frame()))
    assert report['linkage'] == {
        'one_month': {'2025-08>2025-09': {'cpsidv': 100, 'cpsidp': 98, 'other_gap_matches': 3}},
        'two_month': {'2025-09>2025-11': {'cpsidv': 40, 'cpsidp': 41, 'other_gap_matches': 0}}}
    assert report['weights'] == {'null': 2, 'zero': 3, 'positive': 40}
    share = parts['guards']['usable_share']
    assert report['usable_guard_share'] == {
        'monthly_ee:industry': share['industry'], 'monthly_ee:occupation': share['occupation'],
        'monthly_ue': 'not_applicable', 'asec_retro': 'not_applicable'}
    assert (share['industry'], share['occupation']) == (6 / 7, 5 / 7)
    assert report['guard_source_exceptions'] == {'empsame_in_mish_1_or_5': 1}
    assert report['asec_flags_by_empstat'] == asec_flag_counts(people())
    assert set(report['asec_flags_by_empstat']) == {'QIND', 'QOCC', 'QOCCLY', 'QEMPSTAT'}


def test_report_funnels_and_distribution_and_table_rows(estimates, rows):
    parts = diagnostic_parts()
    tables = report_tables(estimates, rows, unit_frame())
    report = build_report(run_id='r', parts=parts, tables=tables)
    assert set(report['funnels']) == set(parts['funnels'])
    assert report['funnels']['asec_retro:occupation'] == {
        'weight_nonpositive': 1, 'not_employed': 1, 'last_year_code_not_in_universe': 1,
        'current_code_not_in_universe': 0, 'same_category': 1, 'eligible': 1}
    assert list(report['funnels']['monthly_ue:industry']) == [
        'weight_null', 'weight_zero', 'origin_new_worker_22', 'origin_not_unemployed_21',
        'destination_not_employed', 'code_not_in_universe', 'eligible']
    assert set(report['n_unweighted_distribution']) == {
        'monthly_ee:industry:strict', 'monthly_ee:industry:sensitivity',
        'monthly_ue:occupation:sensitivity', 'asec_retro:occupation:sensitivity'}
    assert report['n_unweighted_distribution']['monthly_ee:industry:strict'] == {
        'cells': 2, 'min': 1, 'max': 2, 'p10': 1, 'p25': 1, 'p50': 1, 'p75': 2, 'p90': 2,
        'at_least': {'1': 2, '2': 1, '5': 0, '10': 0, '20': 0, '30': 0, '50': 0, '100': 0}}
    for name, found in report['n_unweighted_distribution'].items():
        product, dimension, policy = name.split(':')
        unit_type = INDUSTRY if dimension == 'industry' else OCCUPATION
        assert found == n_unweighted_distribution(
            variant_rows(rows, f'{product}:{policy}', unit_type))
    assert report['tables'] == {name: {'rows': frame.height}
                                for name, frame in sorted(tables.items())}
    assert set(report['tables']) == set(SCHEMAS) | {'cps_job_flows'}
    assert report['tables']['cps_job_flows']['rows'] == rows.height
