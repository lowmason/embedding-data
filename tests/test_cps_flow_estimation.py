'''Tests for the CPS flow totals, shares, standard errors and the seeded bootstrap.'''

import math
import random
import statistics
from collections import Counter
from decimal import Decimal

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from embedding_data import cps_flow_estimation
from embedding_data.cps_flow_estimation import (
    ASEC_K,
    ASEC_R,
    BOOTSTRAP_B,
    BOOTSTRAP_SEED,
    MONTHLY_K,
    REPLICATES_SCHEMA,
    SUPPORT_SCHEMA,
    TARGETS_SCHEMA,
    Variant,
    bootstrap_se,
    estimate_asec,
    estimate_monthly,
    household_draws,
    replicate_se,
)

EE = Variant('monthly_ee', 'industry', 'sensitivity')
EE_STRICT = Variant('monthly_ee', 'industry', 'strict')
UE = Variant('monthly_ue', 'occupation', 'sensitivity')
ASEC = Variant('asec_retro', 'occupation', 'sensitivity')
P1, P2 = '2025-01>2025-02', '2025-02>2025-03'
Y1, Y2 = 'asec-2025', 'asec-2026'
WEIGHT = pl.Decimal(38, 4)
REPLICATES = list(range(1, BOOTSTRAP_B + 1))
ASEC_REPLICATES = list(range(1, ASEC_R + 1))
VARIANT_KEYS = ['product', 'dimension', 'policy']


def monthly(rows):
    '''A monthly records frame from `(CPSID, unit_a, unit_b, period, weight)` rows.'''
    cpsids, units_a, units_b, periods, weights = (list(column) for column in zip(*rows))
    return pl.DataFrame({
        'CPSID': pl.Series(cpsids, dtype=pl.Int64),
        'unit_a': pl.Series(units_a, dtype=pl.String),
        'unit_b': pl.Series(units_b, dtype=pl.String),
        'period': pl.Series(periods, dtype=pl.String),
        'weight': pl.Series([Decimal(value) for value in weights], dtype=WEIGHT),
    })


def asec(rows):
    '''An ASEC records frame from `(unit_a, unit_b, period, weight, replicates)` rows.

    `replicates` lists the 160 replicate weights, or is None for replicates equal to the weight.
    '''
    units_a, units_b, periods, weights, replicates = (list(column) for column in zip(*rows))
    columns = {
        'unit_a': pl.Series(units_a, dtype=pl.String),
        'unit_b': pl.Series(units_b, dtype=pl.String),
        'period': pl.Series(periods, dtype=pl.String),
        'weight': pl.Series([Decimal(value) for value in weights], dtype=WEIGHT),
    }
    for number in ASEC_REPLICATES:
        columns[f'rep{number}'] = pl.Series(
            [Decimal(weight if values is None else values[number - 1])
             for weight, values in zip(weights, replicates)], dtype=WEIGHT)
    return pl.DataFrame(columns)


def draws_for(records):
    '''The draws over the sorted distinct households of `records`.'''
    return household_draws(sorted(set(records['CPSID'].to_list())))


def draw_counts(draws):
    '''Map `(replicate, CPSID)` to the household's draw count.'''
    return {(replicate, cpsid): count for replicate, cpsid, count in draws.iter_rows()}


def target(estimates, unit_a, unit_b, measure):
    '''The one target row of a cell and measure, as a dict.'''
    rows = estimates.targets.filter(
        pl.col('unit_a').eq(unit_a) & pl.col('unit_b').eq(unit_b)
        & pl.col('measure').eq(measure))
    assert rows.height == 1
    return rows.row(0, named=True)


def cell_replicates(estimates, unit_a, unit_b):
    '''The replicate rows of one cell.'''
    return estimates.replicates.filter(pl.col('unit_a').eq(unit_a) & pl.col('unit_b').eq(unit_b))


def hand_replicate(records, counts, unit_a, unit_b, replicate):
    '''Sum weight times draws by hand over the records of a cell (or origin, `unit_b` None).'''
    total = Decimal(0)
    for cpsid, origin, destination, _, weight in records.iter_rows():
        if origin == unit_a and (unit_b is None or destination == unit_b):
            total += weight * counts[replicate, cpsid]
    return float(total) / MONTHLY_K


def test_pooled_totals_and_shares_with_fixed_divisors():
    weights = [('0170', '0180', '12'), ('0170', '0180', '24'), ('0170', '0190', '24'),
               ('0170', '0190', '24'), ('0170', '0190', '24')]
    records = monthly([(cpsid, unit_a, unit_b, P1, weight)
                       for cpsid, (unit_a, unit_b, weight) in enumerate(weights, start=1)])
    found = {
        MONTHLY_K: estimate_monthly(records, EE, draws_for(records)),
        ASEC_K: estimate_asec(
            asec([(unit_a, unit_b, Y1, weight, None) for unit_a, unit_b, weight in weights]),
            ASEC),
    }
    assert (MONTHLY_K, ASEC_K) == (18, 2)
    for k, estimates in found.items():
        assert estimates.targets.select(
            'unit_a', 'unit_b', 'measure', 'value', 'n_unweighted', 'n_weighted').rows() == [
            ('0170', '0180', 'average_total', 36 / k, 2, 36 / k),
            ('0170', '0180', 'forward_share', 1 / 3, 2, 36 / k),
            ('0170', '0190', 'average_total', 72 / k, 3, 72 / k),
            ('0170', '0190', 'forward_share', 2 / 3, 3, 72 / k),
        ]
    assert found[MONTHLY_K].targets['value'].to_list()[::2] == [2.0, 4.0]


def test_share_is_the_ratio_of_pooled_totals():
    records = monthly([(1, '0170', '0180', P1, '10'), (2, '0170', '0190', P1, '10'),
                       (3, '0170', '0180', P2, '30'), (4, '0170', '0190', P2, '90')])
    found = estimate_monthly(records, EE, draws_for(records))
    share = target(found, '0170', '0180', 'forward_share')['value']
    assert share == (40 / MONTHLY_K) / (140 / MONTHLY_K)
    assert share != (10 / 20 + 30 / 120) / 2


def test_decimal_sums_do_not_drift(monkeypatch):
    monkeypatch.setattr(cps_flow_estimation, 'MONTHLY_K', 1)
    monkeypatch.setattr(cps_flow_estimation, 'ASEC_K', 1)
    records = monthly([(cpsid, '0170', '0180', P1, '0.1') for cpsid in range(1, 11)])
    monthly_total = target(estimate_monthly(records, EE, draws_for(records)),
                           '0170', '0180', 'average_total')
    asec_total = target(estimate_asec(asec([('0010', '0020', Y1, '0.1', None)] * 10), ASEC),
                        '0010', '0020', 'average_total')
    assert monthly_total['value'] == asec_total['value'] == 1.0


def test_asec_replicate_se_formula():
    assert replicate_se(5.0, [6.0] * ASEC_R) == math.sqrt((4 / 160) * 160) == 2.0
    assert replicate_se(5.0, [4.0, 6.0] * (ASEC_R // 2)) == 2.0
    replicates = ['10'] * ASEC_R
    replicates[6] = '-10'
    records = asec([('0010', '0020', Y1, '10', replicates)])
    found = estimate_asec(records, ASEC)
    total = target(found, '0010', '0020', 'average_total')
    assert total['value'] == 5.0
    assert total['se'] == math.sqrt((4 / 160) * (-5.0 - 5.0) ** 2)
    rows = cell_replicates(found, '0010', '0020')
    assert rows['replicate'].to_list() == ASEC_REPLICATES
    assert rows.filter(pl.col('replicate').eq(7))['numerator'].item() == -5.0
    with pytest.raises(ValueError, match='exactly the estimation columns'):
        estimate_asec(records.with_columns(pl.col('rep1').alias('REPWTP')), ASEC)


def test_every_cell_has_every_replicate_row_zero_filled():
    records = monthly([(11, '0170', '0180', P1, '1.8'), (22, '0170', '0190', P1, '3.6'),
                       (33, '1370', '0180', P2, '5.4')])
    draws = draws_for(records)
    counts = draw_counts(draws)
    found = estimate_monthly(records, EE, draws)
    rows = cell_replicates(found, '0170', '0180')
    missed = [replicate for replicate in REPLICATES if counts[replicate, 11] == 0]
    assert 0 < len(missed) < BOOTSTRAP_B
    assert rows['replicate'].to_list() == REPLICATES
    assert rows['numerator'].to_list() == [
        float(Decimal('1.8') * counts[replicate, 11]) / MONTHLY_K for replicate in REPLICATES]
    assert all(rows['numerator'][replicate - 1] == 0.0 for replicate in missed)
    assert found.replicates.height == 3 * BOOTSTRAP_B

    replicates = ['2' if number % 3 else '0' for number in ASEC_REPLICATES]
    asec_found = estimate_asec(asec([('0010', '0020', Y1, '2', replicates),
                                     ('0010', '0030', Y2, '4', None)]), ASEC)
    rows = cell_replicates(asec_found, '0010', '0020')
    assert rows['replicate'].to_list() == ASEC_REPLICATES
    assert rows['numerator'].to_list() == [
        0.0 if number % 3 == 0 else 1.0 for number in ASEC_REPLICATES]
    assert asec_found.replicates.height == 2 * ASEC_R


def test_bootstrap_draws_are_pinned_and_reproducible():
    households = [101, 202, 303]
    draws = household_draws(households)
    assert_frame_equal(draws, household_draws(households))
    first = draws.filter(pl.col('replicate').eq(1))
    expected = Counter(random.Random(20261123).choices(range(3), k=3))
    assert Counter({households.index(cpsid): count
                    for cpsid, count in first.select('CPSID', 'draws').iter_rows()}) == expected
    sums = draws.group_by('replicate').agg(pl.col('draws').sum()).sort('replicate')
    assert sums['draws'].to_list() == [len(households)] * BOOTSTRAP_B
    for households in ([303, 101, 202], [101, 101, 202]):
        with pytest.raises(ValueError, match='sorted and distinct'):
            household_draws(households)


def test_bootstrap_se_uses_b_minus_one():
    assert bootstrap_se([1.0, 2.0, 3.0]) == 1.0


def test_strict_and_sensitivity_share_the_same_draws():
    sensitivity = monthly([
        (1, '0170', '0180', P1, '10'), (2, '0170', '0180', P1, '20'),
        (3, '0170', '0190', P1, '30'), (4, '0170', '0180', P2, '40'),
        (5, '0170', '0190', P2, '50'), (6, '1370', '0180', P2, '60')])
    strict = sensitivity.filter(pl.col('CPSID').is_in([2, 4, 5]))
    draws = draws_for(sensitivity)
    counts = draw_counts(draws)
    for records, variant in ((strict, EE_STRICT), (sensitivity, EE)):
        found = estimate_monthly(records, variant, draws)
        rows = cell_replicates(found, '0170', '0180')
        assert rows['policy'].unique().to_list() == [variant.policy]
        assert rows['numerator'].to_list() == [
            hand_replicate(records, counts, '0170', '0180', replicate)
            for replicate in REPLICATES]


def test_nonpositive_denominator_publishes_no_share():
    records = monthly([(1, '0170', '0180', P1, '1'), (2, '0170', '0180', P1, '-1'),
                       (3, '1370', '0180', P1, '2')])
    found = estimate_monthly(records, EE, draws_for(records))
    assert found.targets.filter(pl.col('unit_a').eq('0170')).select(
        'unit_b', 'measure', 'value').rows() == [('0180', 'average_total', 0.0)]
    assert target(found, '1370', '0180', 'forward_share')['value'] == 1.0
    undefined = found.support.filter(
        pl.col('kind').eq('undefined_share') & pl.col('unit_a').eq('0170'))
    assert undefined.select('unit_a', 'unit_b', 'period', 'n_unweighted', 'mass', 'reason',
                            'replicates').rows() == [
        ('0170', '0180', 'all', 1, 0.0, 'nonpositive_denominator', None)]


def test_undefined_replicate_ratio_keeps_the_point_with_null_se():
    first, second = ['10'] * ASEC_R, ['30'] * ASEC_R
    first[4], second[4] = '0', '0'
    first[8], second[8] = '-3', '1'
    found = estimate_asec(asec([('0010', '0020', Y1, '10', first),
                                ('0010', '0030', Y2, '30', second)]), ASEC)
    share = target(found, '0010', '0020', 'forward_share')
    assert (share['value'], share['se'], share['se_method']) == (0.25, None, 'none')
    total = target(found, '0010', '0020', 'average_total')
    numerators = cell_replicates(found, '0010', '0020')['numerator'].to_list()
    assert total['se_method'] == 'replicate'
    assert total['se'] == math.sqrt((4 / 160) * math.fsum(
        (value - 5.0) ** 2 for value in numerators))
    undefined = found.support.filter(pl.col('kind').eq('undefined_share'))
    assert undefined.select('unit_a', 'unit_b', 'period', 'n_unweighted', 'mass', 'reason',
                            'replicates').rows() == [
        ('0010', '0020', 'all', 1, 10.0, 'replicate_share_undefined', [5, 9]),
        ('0010', '0030', 'all', 1, 30.0, 'replicate_share_undefined', [5, 9])]
    rows = cell_replicates(found, '0010', '0020')
    bad = rows.filter(pl.col('replicate').is_in([5, 9]))
    assert bad.select('replicate', 'denominator', 'estimate', 'status').rows() == [
        (5, 0.0, None, 'denominator_nonpositive'), (9, -1.0, None, 'denominator_nonpositive')]
    good = rows.filter(~pl.col('replicate').is_in([5, 9]))
    assert good['status'].unique().to_list() == ['defined']
    assert good['estimate'].unique().to_list() == [0.25]


def test_unobserved_cells_are_absent():
    records = monthly([(1, '0170', '0180', P1, '5'), (2, '1370', '0190', P2, '7')])
    found = estimate_monthly(records, EE, draws_for(records))
    observed = [('0170', '0180'), ('1370', '0190')]
    assert found.targets.select('unit_a', 'unit_b').unique().sort(['unit_a', 'unit_b']).rows() \
        == observed
    assert found.replicates.select('unit_a', 'unit_b').unique().sort(
        ['unit_a', 'unit_b']).rows() == observed
    cells = found.support.filter(pl.col('kind').eq('cell'))
    assert cells.select('unit_a', 'unit_b').rows() == observed
    assert found.targets.filter(pl.col('measure').eq('average_total'))['value'].to_list() == [
        5 / MONTHLY_K, 7 / MONTHLY_K]


def test_a_total_is_the_float_of_the_exact_sum_over_k():
    big = str(2 ** 53 + 1)
    records = monthly([(1, '0170', '0180', P1, '1'), (2, '0170', '0190', P1, big),
                       (3, '0170', '0190', P1, big), (4, '0170', '0190', P1, big)])
    found = estimate_monthly(records, EE, draws_for(records))
    exact = float(Decimal(3 * (2 ** 53 + 1))) / MONTHLY_K
    assert exact != 3 * float(big) / MONTHLY_K
    assert target(found, '0170', '0190', 'average_total')['value'] == exact
    assert target(found, '0170', '0180', 'average_total')['value'] == 1 / 18


def test_a_share_divides_the_two_published_totals():
    records = monthly([(1, '0170', '0180', P1, '399.2384'), (2, '0170', '0190', P1, '913065.2')])
    draws = draws_for(records)
    counts = draw_counts(draws)
    found = estimate_monthly(records, EE, draws)
    published = (399.2384 / MONTHLY_K) / (913464.4384 / MONTHLY_K)
    assert published != 399.2384 / 913464.4384
    assert target(found, '0170', '0180', 'forward_share')['value'] == published
    rows = cell_replicates(found, '0170', '0180')
    hand = []
    for replicate in REPLICATES:
        denominator = hand_replicate(records, counts, '0170', None, replicate)
        numerator = hand_replicate(records, counts, '0170', '0180', replicate)
        hand.append(numerator / denominator if denominator > 0 else None)
    assert rows['estimate'].to_list() == hand
    assert published in hand


def test_monthly_ses_are_the_bootstrap_sd_of_the_replicate_statistics():
    rows = [(cpsid, '0170', '0180' if cpsid <= 10 else '0190', P1 if cpsid % 2 else P2,
             str(cpsid * 3)) for cpsid in range(1, 31)]
    records = monthly(rows)
    draws = draws_for(records)
    counts = draw_counts(draws)
    found = estimate_monthly(records, UE, draws)
    replicates = cell_replicates(found, '0170', '0180')
    numerators = [hand_replicate(records, counts, '0170', '0180', replicate)
                  for replicate in REPLICATES]
    denominators = [hand_replicate(records, counts, '0170', None, replicate)
                    for replicate in REPLICATES]
    estimates = [numerator / denominator
                 for numerator, denominator in zip(numerators, denominators)]
    assert replicates['numerator'].to_list() == numerators
    assert replicates['denominator'].to_list() == denominators
    assert replicates['estimate'].to_list() == estimates
    total = target(found, '0170', '0180', 'average_total')
    share = target(found, '0170', '0180', 'forward_share')
    assert total['se'] == pytest.approx(statistics.stdev(numerators), rel=1e-12)
    assert share['se'] == pytest.approx(statistics.stdev(estimates), rel=1e-12)
    assert (total['se_method'], share['se_method']) == ('bootstrap', 'bootstrap')
    assert total['se'] > 0 and share['se'] > 0


def test_asec_ses_recompute_numerator_and_denominator():
    first = [str(10 + number % 4) for number in ASEC_REPLICATES]
    second = [str(30 - number % 5) for number in ASEC_REPLICATES]
    records = asec([('0010', '0020', Y1, '10', first), ('0010', '0030', Y2, '30', second)])
    records = records.with_columns(
        pl.Series('rep2', [Decimal('10.000001'), Decimal(second[1])], dtype=pl.Decimal(38, 6)))
    first[1] = '10.000001'
    found = estimate_asec(records, ASEC)
    numerators = [float(Decimal(value)) / ASEC_K for value in first]
    denominators = [float(Decimal(left) + Decimal(right)) / ASEC_K
                    for left, right in zip(first, second)]
    estimates = [numerator / denominator
                 for numerator, denominator in zip(numerators, denominators)]
    rows = cell_replicates(found, '0010', '0020')
    assert rows['numerator'].to_list() == numerators
    assert rows['denominator'].to_list() == denominators
    assert rows['estimate'].to_list() == estimates
    total = target(found, '0010', '0020', 'average_total')
    share = target(found, '0010', '0020', 'forward_share')
    assert total['se'] == pytest.approx(math.sqrt((4 / 160) * math.fsum(
        (value - 5.0) ** 2 for value in numerators)), rel=1e-12)
    assert share['se'] == pytest.approx(math.sqrt((4 / 160) * math.fsum(
        (value - 0.25) ** 2 for value in estimates)), rel=1e-12)
    assert (total['se_method'], share['se_method']) == ('replicate', 'replicate')


def test_a_missed_origin_leaves_the_bootstrap_share_se_undefined():
    records = monthly([(11, '0170', '0180', P1, '1.8'), (22, '1370', '0190', P1, '3.6'),
                       (33, '1370', '0180', P2, '5.4')])
    draws = draws_for(records)
    counts = draw_counts(draws)
    found = estimate_monthly(records, EE, draws)
    missed = [replicate for replicate in REPLICATES if counts[replicate, 11] == 0]
    share = target(found, '0170', '0180', 'forward_share')
    assert (share['value'], share['se'], share['se_method']) == (1.0, None, 'none')
    total = target(found, '0170', '0180', 'average_total')
    assert total['se_method'] == 'bootstrap' and total['se'] > 0
    undefined = found.support.filter(
        pl.col('kind').eq('undefined_share') & pl.col('unit_a').eq('0170'))
    assert undefined.select('unit_a', 'unit_b', 'reason', 'replicates').rows() == [
        ('0170', '0180', 'replicate_share_undefined', missed)]
    statuses = cell_replicates(found, '0170', '0180')['status'].to_list()
    assert [replicate for replicate, status in zip(REPLICATES, statuses)
            if status == 'denominator_nonpositive'] == missed


def test_a_negative_full_denominator_publishes_no_share():
    records = monthly([(1, '0170', '0180', P1, '1'), (2, '0170', '0190', P2, '-2')])
    found = estimate_monthly(records, EE, draws_for(records))
    assert found.targets['measure'].to_list() == ['average_total', 'average_total']
    undefined = found.support.filter(pl.col('kind').eq('undefined_share'))
    assert undefined.select('unit_a', 'unit_b', 'period', 'n_unweighted', 'mass', 'reason',
                            'replicates').rows() == [
        ('0170', '0180', 'all', 1, 1.0, 'nonpositive_denominator', None),
        ('0170', '0190', 'all', 0, -2.0, 'nonpositive_denominator', None)]


def test_support_counts_each_contributing_period():
    records = monthly([(1, '0170', '0180', P1, '10'), (2, '0170', '0180', P1, '20'),
                       (3, '0170', '0180', P2, '5'), (4, '0170', '0190', P2, '7'),
                       (5, '0170', '0190', P2, '0'), (6, '1370', '0180', P1, '1')])
    found = estimate_monthly(records, EE, draws_for(records))
    assert list(found.support.schema.items()) == list(SUPPORT_SCHEMA.items())
    periods = found.support.filter(pl.col('kind').ne('undefined_share'))
    assert periods.select(
        'kind', 'unit_a', 'unit_b', 'period', 'n_unweighted', 'mass').rows() == [
        ('cell', '0170', '0180', P1, 2, 30.0), ('cell', '0170', '0180', P2, 1, 5.0),
        ('cell', '0170', '0190', P2, 1, 7.0), ('cell', '1370', '0180', P1, 1, 1.0),
        ('denominator', '0170', None, P1, 2, 30.0), ('denominator', '0170', None, P2, 2, 12.0),
        ('denominator', '1370', None, P1, 1, 1.0)]
    assert found.support.select(VARIANT_KEYS).unique().rows() == [
        ('monthly_ee', 'industry', 'sensitivity')]
    assert periods['reason'].null_count() == periods['replicates'].null_count() == periods.height
    assert target(found, '0170', '0190', 'average_total')['n_unweighted'] == 1

    asec_found = estimate_asec(asec([('0010', '0020', Y1, '4', None),
                                     ('0010', '0020', Y2, '6', None)]), ASEC)
    assert asec_found.support.select('kind', 'unit_b', 'period', 'n_unweighted', 'mass').rows() \
        == [('cell', '0020', Y1, 1, 4.0), ('cell', '0020', Y2, 1, 6.0),
            ('denominator', None, Y1, 1, 4.0), ('denominator', None, Y2, 1, 6.0)]


def test_frames_have_the_fixed_ordered_schemas_and_sort_orders():
    records = monthly([(4, '1370', '0190', P2, '7'), (3, '1370', '0180', P1, '2'),
                       (2, '0170', '0190', P2, '3'), (1, '0170', '0180', P1, '5')])
    found = estimate_monthly(records, EE_STRICT, draws_for(records))
    asec_found = estimate_asec(asec([('0030', '0020', Y2, '7', None),
                                     ('0010', '0020', Y1, '5', None)]), ASEC)
    for estimates, variant in ((found, EE_STRICT), (asec_found, ASEC)):
        assert list(estimates.targets.schema.items()) == list(TARGETS_SCHEMA.items())
        assert list(estimates.support.schema.items()) == list(SUPPORT_SCHEMA.items())
        assert list(estimates.replicates.schema.items()) == list(REPLICATES_SCHEMA.items())
        assert_frame_equal(estimates.targets, estimates.targets.sort(
            [*VARIANT_KEYS, 'unit_a', 'unit_b', 'measure']))
        assert_frame_equal(estimates.support, estimates.support.sort(
            list(SUPPORT_SCHEMA), nulls_last=False))
        assert_frame_equal(estimates.replicates, estimates.replicates.sort(
            [*VARIANT_KEYS, 'unit_a', 'unit_b', 'replicate']))
        for frame in (estimates.targets, estimates.support, estimates.replicates):
            assert frame.select(VARIANT_KEYS).unique().rows() == [
                (variant.product, variant.dimension, variant.policy)]
    assert found.targets.select('unit_a', 'unit_b', 'measure').rows()[:2] == [
        ('0170', '0180', 'average_total'), ('0170', '0180', 'forward_share')]
    assert found.replicates['replicate'].to_list()[:3] == [1, 2, 3]


def test_draws_continue_one_generator_and_cover_every_household():
    households = [5, 7, 9, 11]
    draws = household_draws(households)
    assert list(draws.schema.items()) == [
        ('replicate', pl.UInt16), ('CPSID', pl.Int64), ('draws', pl.UInt32)]
    assert draws.height == BOOTSTRAP_B * len(households)
    rng = random.Random(BOOTSTRAP_SEED)
    for replicate in REPLICATES:
        counts = Counter(rng.choices(range(len(households)), k=len(households)))
        rows = draws.filter(pl.col('replicate').eq(replicate))
        assert rows['CPSID'].to_list() == households
        assert rows['draws'].to_list() == [counts[index] for index in range(len(households))]
    other = household_draws(households, seed=7, replicates=5)
    rng = random.Random(7)
    assert other['replicate'].unique().sort().to_list() == [1, 2, 3, 4, 5]
    for replicate in range(1, 6):
        counts = Counter(rng.choices(range(len(households)), k=len(households)))
        assert other.filter(pl.col('replicate').eq(replicate))['draws'].to_list() == [
            counts[index] for index in range(len(households))]


def test_standard_errors_sum_with_fsum():
    values = [1e16, 1.0, 1e-16]
    mean = math.fsum(values) / 3
    assert bootstrap_se(values) == math.sqrt(math.fsum((value - mean) ** 2
                                                       for value in values) / 2)
    assert bootstrap_se(values) == 5773502691896258.0
    deviations = [1e8, 1.0, 1e-8] + [0.0] * (ASEC_R - 3)
    assert replicate_se(0.0, deviations) == 15811388.300841898


def test_se_functions_check_lengths_and_keep_undefined_replicates():
    with pytest.raises(ValueError, match='at least two'):
        bootstrap_se([1.0])
    with pytest.raises(ValueError, match='exactly 160'):
        replicate_se(1.0, [1.0] * (ASEC_R - 1))
    with pytest.raises(ValueError, match='exactly 160'):
        replicate_se(1.0, [1.0] * (ASEC_R + 1))
    assert bootstrap_se([1.0, None, 3.0]) is None
    assert replicate_se(1.0, [None] + [1.0] * (ASEC_R - 1)) is None


def _monthly_records():
    return monthly([(1, '0170', '0180', P1, '5'), (2, '0170', '0190', P1, '7')])


def _asec_records():
    return asec([('0010', '0020', Y1, '5', None)])


@pytest.mark.parametrize('build', [
    pytest.param(lambda: estimate_monthly(_monthly_records().drop('CPSID'), EE,
                                          household_draws([1, 2])), id='monthly-no-cpsid'),
    pytest.param(lambda: estimate_monthly(
        _monthly_records().with_columns(pl.lit('x').alias('reason')), EE,
        household_draws([1, 2])), id='monthly-extra-column'),
    pytest.param(lambda: estimate_monthly(
        _monthly_records().with_columns(pl.col('weight').cast(pl.Float64)), EE,
        household_draws([1, 2])), id='monthly-float-weight'),
    pytest.param(lambda: estimate_monthly(
        _monthly_records().with_columns(pl.col('CPSID').cast(pl.String)), EE,
        household_draws([1, 2])), id='monthly-string-cpsid'),
    pytest.param(lambda: estimate_asec(_asec_records().drop('rep160'), ASEC),
                 id='asec-no-rep160'),
    pytest.param(lambda: estimate_asec(
        _asec_records().with_columns(pl.col('rep1').alias('rep161')), ASEC),
        id='asec-rep161'),
    pytest.param(lambda: estimate_asec(
        _asec_records().with_columns(pl.col('rep9').cast(pl.Float64)), ASEC),
        id='asec-float-replicate'),
    pytest.param(lambda: estimate_asec(
        _asec_records().with_columns(pl.col('unit_b').cast(pl.Categorical)), ASEC),
        id='asec-categorical-unit'),
])
def test_records_must_have_exactly_the_estimation_columns(build):
    with pytest.raises(ValueError, match='exactly the estimation columns'):
        build()


@pytest.mark.parametrize('build', [
    pytest.param(lambda: estimate_monthly(
        _monthly_records().with_columns(
            pl.when(pl.col('CPSID').eq(2)).then(pl.col('weight')).alias('weight')),
        EE, household_draws([1, 2])), id='monthly-null-weight'),
    pytest.param(lambda: estimate_asec(
        _asec_records().with_columns(pl.lit(None, dtype=WEIGHT).alias('rep80')), ASEC),
        id='asec-null-replicate'),
])
def test_null_record_values_are_refused(build):
    with pytest.raises(ValueError, match='null'):
        build()


def _drop_one_draw(draws):
    return draws.filter(~(pl.col('replicate').eq(7) & pl.col('CPSID').eq(2)))


@pytest.mark.parametrize('change', [
    pytest.param(lambda draws: draws.filter(pl.col('CPSID').ne(2)), id='missing-household'),
    pytest.param(_drop_one_draw, id='missing-replicate'),
    pytest.param(lambda draws: pl.concat([draws, draws.head(1)]), id='duplicated-row'),
    pytest.param(lambda draws: draws.with_columns(pl.col('replicate') - 1),
                 id='zero-based'),
    pytest.param(lambda draws: draws.filter(pl.col('replicate').lt(BOOTSTRAP_B)),
                 id='too-few-replicates'),
])
def test_draws_must_cover_each_record_household_in_every_replicate(change):
    records = _monthly_records()
    with pytest.raises(ValueError, match='draws'):
        estimate_monthly(records, EE, change(draws_for(records)))


@pytest.mark.parametrize('call', [
    pytest.param(lambda: estimate_monthly(_monthly_records(),
                                          Variant('asec_retro', 'industry', 'sensitivity'),
                                          household_draws([1, 2])), id='monthly-asec-product'),
    pytest.param(lambda: estimate_monthly(_monthly_records(),
                                          Variant('monthly_ee', 'industry', 'loose'),
                                          household_draws([1, 2])), id='monthly-unknown-policy'),
    pytest.param(lambda: estimate_monthly(_monthly_records(),
                                          Variant('monthly_ue', 'county', 'strict'),
                                          household_draws([1, 2])),
                 id='monthly-unknown-dimension'),
    pytest.param(lambda: estimate_asec(_asec_records(),
                                       Variant('asec_retro', 'industry', 'strict')),
                 id='asec-strict'),
    pytest.param(lambda: estimate_asec(_asec_records(),
                                       Variant('monthly_ee', 'industry', 'sensitivity')),
                 id='asec-monthly-product'),
])
def test_variants_must_match_their_product(call):
    with pytest.raises(ValueError, match='variant'):
        call()
