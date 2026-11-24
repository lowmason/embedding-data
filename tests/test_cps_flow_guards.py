'''Tests for the CPS flow guards, product eligibility, funnels and evidence policies.'''

from collections import Counter

import polars as pl
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from embedding_data.cps_flow_guards import (
    asec_flag_counts,
    flag_class_expr,
    funnel,
    guard_expr,
    guard_source_exceptions,
    product_frame,
    usable_guard_share,
)
from embedding_data.cps_flow_linkage import LINK_COLUMNS

INDUSTRY, OCCUPATION = 'cps_industry_category', 'cps_occupation_category'
UNIT_ROWS = [
    (INDUSTRY, '0170', 'mapped'), (INDUSTRY, '1370', 'mapped'),
    (INDUSTRY, '9920', 'no_naics_equivalent'), (INDUSTRY, '9890', 'special_military'),
    (OCCUPATION, '0010', 'mapped'), (OCCUPATION, '0020', 'mapped'),
    (OCCUPATION, '9830', 'no_soc_equivalent'), (OCCUPATION, '9840', 'special_military')]
PRODUCTS = ('monthly_ee', 'monthly_ue', 'asec_retro')
DIMENSIONS = ('industry', 'occupation')
# The first-exclusion order of SD3, restated from the plan.
ORDER = {
    'monthly_ee': ('weight_null', 'weight_zero', 'not_employed_both', 'code_not_in_universe',
                   'guard_unusable', 'no_change_reported', 'coding_noise', 'eligible'),
    'monthly_ue': ('weight_null', 'weight_zero', 'origin_new_worker_22',
                   'origin_not_unemployed_21', 'destination_not_employed',
                   'code_not_in_universe', 'eligible'),
    'asec_retro': ('weight_nonpositive', 'not_employed', 'last_year_code_not_in_universe',
                   'current_code_not_in_universe', 'same_category', 'eligible'),
}
NOT_USABLE = (96, 97, 99)
ANSWERS = (1, 2, *NOT_USABLE)
# The spec's Guard table, cell by cell: (EMPSAME, ACTSAME) -> (occupation, industry).
GUARD_TABLE = {
    **{(1, actsame): ('changed', 'changed') for actsame in ANSWERS},
    (2, 2): ('changed', 'same'),
    (2, 1): ('same', 'same'),
    **{(2, actsame): ('unusable', 'same') for actsame in NOT_USABLE},
    **{(empsame, actsame): ('unusable', 'unusable')
       for empsame in NOT_USABLE for actsame in ANSWERS},
}
GUARD_COLUMN = {'occupation': 0, 'industry': 1}
# Flag classes by value, from the delivered labels (Global Constraints).
QEMPSTAT_CLASSES = ['nonallocation', 'edited', 'edited', 'edited', 'allocated', 'allocated',
                    'longitudinal']
QCODE_CLASSES = ['nonallocation', 'edited', 'edited', 'edited', 'allocated', 'allocated',
                 'allocated', 'longitudinal']
QOCCLY_CLASSES = ['nonallocation', 'allocated']
# Two mapped codes and the special of each dimension.
CODES = {'industry': ('0170', '1370', '9890'), 'occupation': ('0010', '0020', '9840')}
MONTHLY_FIELDS = {'industry': ('ind_a', 'ind_b', 'qind', 'QIND'),
                  'occupation': ('occ_a', 'occ_b', 'qocc', 'QOCC')}
ASEC_FIELDS = {'industry': ('INDLY', 'IND'), 'occupation': ('OCCLY', 'OCC')}
NEW_COLUMNS = ['unit_a', 'unit_b', 'reason', 'strict', 'inclusion_reasons', 'special']

_STRINGS = {'month_a', 'month_b', 'link_type', 'ind_a', 'ind_b', 'occ_a', 'occ_b'}
_ROWS = {'source_row_a', 'source_row_b'}
LINK_SCHEMA = {
    **{name: pl.String if name in _STRINGS else pl.UInt64 if name in _ROWS else pl.Int64
       for name in LINK_COLUMNS},
    'weight_status': pl.String}
# An employer change with both codes different, nonallocation flags and a positive weight:
# eligible and strict in `monthly_ee` for both dimensions.
LINK_DEFAULTS = {
    'CPSIDV': 1, 'CPSID': 10, 'source_row_a': 0, 'source_row_b': 1, 'month_a': '2025-01',
    'month_b': '2025-02', 'link_type': 'one_month', 'mish_a': 1, 'mish_b': 2, 'empstat_a': 10,
    'empstat_b': 10, 'ind_a': '0170', 'ind_b': '1370', 'occ_a': '0010', 'occ_b': '0020',
    'qempstat_a': 0, 'qempstat_b': 0, 'qind_a': 0, 'qind_b': 0, 'qocc_a': 0, 'qocc_b': 0,
    'empsame_b': 1, 'actsame_b': 99, 'cpsidp_a': 1, 'weight_status': 'positive'}
ASEC_SCHEMA = {
    'CPSID': pl.Int64, 'EMPSTAT': pl.Int64, 'INDLY': pl.String, 'IND': pl.String,
    'OCCLY': pl.String, 'OCC': pl.String, 'QEMPSTAT': pl.Int64, 'QIND': pl.Int64,
    'QOCC': pl.Int64, 'QOCCLY': pl.Int64, 'weight_status': pl.String}
# An employed person who changed both categories since last year: eligible in `asec_retro`.
ASEC_DEFAULTS = {
    'CPSID': 1, 'EMPSTAT': 10, 'INDLY': '0170', 'IND': '1370', 'OCCLY': '0010', 'OCC': '0020',
    'QEMPSTAT': 0, 'QIND': 0, 'QOCC': 0, 'QOCCLY': 0, 'weight_status': 'positive'}


def units() -> pl.DataFrame:
    return pl.DataFrame(UNIT_ROWS, schema=['unit_type', 'code', 'status'], orient='row')


def link(**fields) -> dict:
    '''One one-month link with a weight status; unknown columns are refused.'''
    assert set(fields) <= set(LINK_SCHEMA)
    return {**LINK_DEFAULTS, **fields}


def links(*rows: dict) -> pl.LazyFrame:
    '''Number the links: link `i` has `CPSIDV` `i + 1` and source rows `2i` and `2i + 1`.'''
    numbered = [{**row, 'CPSIDV': number + 1, 'source_row_a': 2 * number,
                 'source_row_b': 2 * number + 1} for number, row in enumerate(rows)]
    return pl.LazyFrame(numbered, schema=LINK_SCHEMA)


def person(**fields) -> dict:
    '''One ASEC person with a weight status; unknown columns are refused.'''
    assert set(fields) <= set(ASEC_SCHEMA)
    return {**ASEC_DEFAULTS, **fields}


def people(*rows: dict) -> pl.LazyFrame:
    numbered = [{**row, 'CPSID': number + 1} for number, row in enumerate(rows)]
    return pl.LazyFrame(numbered, schema=ASEC_SCHEMA)


def source(product: str, rows: list[dict]) -> pl.LazyFrame:
    return people(*rows) if product == 'asec_retro' else links(*rows)


def built(rows: list[dict], product: str = 'monthly_ee',
          dimension: str = 'industry') -> pl.DataFrame:
    return product_frame(source(product, rows), product, dimension, units=units()).collect()


def reasons(rows: list[dict], product: str = 'monthly_ee',
            dimension: str = 'industry') -> list[str]:
    return built(rows, product, dimension)['reason'].to_list()


def select(expression: pl.Expr, **columns: list) -> list:
    frame = pl.DataFrame(columns, schema={name: pl.Int64 for name in columns})
    return frame.select(expression).to_series().to_list()


def guards(dimension: str, empsame: list, actsame: list) -> list:
    return select(guard_expr(dimension, pl.col('empsame'), pl.col('actsame')),
                  empsame=empsame, actsame=actsame)


def classes(file: str, variable: str, values: list) -> list:
    return select(flag_class_expr(file, variable, pl.col('value')), value=values)


# The guards.

def test_guard_table_for_both_dimensions():
    empsame, actsame = (list(column) for column in zip(*GUARD_TABLE))
    for dimension, column in GUARD_COLUMN.items():
        expected = [cells[column] for cells in GUARD_TABLE.values()]
        assert guards(dimension, empsame, actsame) == expected
    assert len(GUARD_TABLE) == 25


def test_guard_refuses_a_null_or_undelivered_answer_in_either_question():
    for dimension in DIMENSIONS:
        for empsame, actsame in ((None, 1), (3, 1), (0, 99), (1, None), (1, 0), (2, 98),
                                 (99, 3), (2, None)):
            with pytest.raises(ValueError):
                guards(dimension, [1, empsame], [99, actsame])
    with pytest.raises(ValueError):
        guard_expr('geography', pl.col('empsame'), pl.col('actsame'))


# Flag classes.

def test_flag_classes_follow_the_delivered_labels_of_each_file():
    for file in ('monthly', 'asec'):
        assert classes(file, 'QEMPSTAT', list(range(7))) == QEMPSTAT_CLASSES
        for variable in ('QIND', 'QOCC'):
            assert classes(file, variable, list(range(8))) == QCODE_CLASSES
            assert classes(file, variable, [None, 0]) == ['unavailable', 'nonallocation']
    assert classes('asec', 'QOCCLY', [0, 1, None]) == [*QOCCLY_CLASSES, 'unavailable']
    for file, variable, value in (('monthly', 'QEMPSTAT', 7), ('monthly', 'QIND', 8),
                                  ('asec', 'QOCC', -1), ('asec', 'QOCCLY', 2)):
        with pytest.raises(ValueError):
            classes(file, variable, [0, value])
    for file, variable in (('monthly', 'QOCCLY'), ('monthly', 'EMPSTAT'), ('cps', 'QIND'),
                           ('asec', 'EMPSAME')):
        with pytest.raises(ValueError):
            flag_class_expr(file, variable, pl.col('value'))


def test_an_unknown_flag_value_fails_rule_validation():
    with pytest.raises(ValueError):
        built([link(qind_b=9)])
    with pytest.raises(ValueError):
        classes('monthly', 'QIND', [0, 9])
    for fields in ({'empsame_b': None}, {'empsame_b': 3}, {'actsame_b': None},
                   {'actsame_b': 98}):
        with pytest.raises(ValueError):
            built([link(**fields)])
    assert reasons([link(qind_a=None)]) == ['eligible']
    assert classes('monthly', 'QIND', [None]) == ['unavailable']


def test_every_delivered_flag_is_checked_in_every_monthly_frame():
    for column, value in (('qempstat_a', 7), ('qempstat_b', 9), ('qind_a', 8), ('qind_b', 9),
                          ('qocc_a', 8), ('qocc_b', 9)):
        for product in ('monthly_ee', 'monthly_ue'):
            for dimension in DIMENSIONS:
                with pytest.raises(ValueError):
                    built([link(**{column: value})], product, dimension)


# Product eligibility.

def test_monthly_ee_admits_only_a_changed_guard_with_positive_weight():
    weights = {'positive': None, 'null': 'weight_null', 'zero': 'weight_zero'}
    exclusions = {'unusable': 'guard_unusable', 'same': 'coding_noise', 'changed': 'eligible'}
    for dimension, column in GUARD_COLUMN.items():
        rows, expected = [], []
        for (empsame, actsame), cells in GUARD_TABLE.items():
            for status, reason in weights.items():
                rows.append(link(empsame_b=empsame, actsame_b=actsame, weight_status=status))
                expected.append(reason or exclusions[cells[column]])
        assert reasons(rows, 'monthly_ee', dimension) == expected


def test_duty_change_moves_occupation_but_industry_difference_is_noise():
    duty = link(empsame_b=2, actsame_b=2)
    occupation = built([duty], 'monthly_ee', 'occupation')
    industry = built([duty], 'monthly_ee', 'industry')
    assert occupation['reason'].to_list() == ['eligible']
    assert occupation['strict'].to_list() == [True]
    assert 'noise_after_duty_change' not in occupation.columns
    assert industry['reason'].to_list() == ['coding_noise']
    assert industry['noise_after_duty_change'].to_list() == [True]


def test_noise_after_duty_change_marks_only_industry_noise_after_changed_duties():
    rows = [link(empsame_b=2, actsame_b=1), link(empsame_b=2, actsame_b=2, ind_b='0170'),
            link(empsame_b=2, actsame_b=2), link(empsame_b=1, actsame_b=2),
            link(empsame_b=2, actsame_b=96)]
    found = built(rows, 'monthly_ee', 'industry')
    assert found['reason'].to_list() == [
        'coding_noise', 'no_change_reported', 'coding_noise', 'eligible', 'coding_noise']
    assert found['noise_after_duty_change'].to_list() == [False, False, True, False, False]
    moved = built([link(empstat_a=21, empsame_b=2, actsame_b=2)], 'monthly_ue', 'industry')
    assert moved['reason'].to_list() == ['eligible']
    assert moved['noise_after_duty_change'].to_list() == [False]
    assert 'noise_after_duty_change' not in built([link()], 'monthly_ue', 'occupation').columns
    retro = built([person(), person(IND='0170')], 'asec_retro', 'industry')
    assert retro['noise_after_duty_change'].to_list() == [False, False]
    assert 'noise_after_duty_change' not in built([person()], 'asec_retro', 'occupation').columns


def test_monthly_ee_needs_employment_at_both_ends_and_keeps_the_diagonal():
    for dimension in DIMENSIONS:
        first = CODES[dimension][0]
        field_b = MONTHLY_FIELDS[dimension][1]
        rows = [link(empstat_a=12), link(empstat_b=12), link(empstat_a=21), link(empstat_b=21),
                link(empstat_a=1, empstat_b=1), link(**{field_b: first})]
        found = built(rows, 'monthly_ee', dimension)
        assert found['reason'].to_list() == [
            'eligible', 'eligible', 'not_employed_both', 'not_employed_both',
            'not_employed_both', 'eligible']
        assert found['strict'].to_list() == [True, True, False, False, False, True]
        assert found.select('unit_a', 'unit_b').rows()[-1] == (first, first)


def test_monthly_ue_uses_the_last_job_origin():
    for dimension in DIMENSIONS:
        rows = [link(empstat_a=21, empstat_b=10, empsame_b=99, actsame_b=99),
                link(empstat_a=22), link(empstat_a=30)]
        assert reasons(rows, 'monthly_ue', dimension) == [
            'eligible', 'origin_new_worker_22', 'origin_not_unemployed_21']


def test_monthly_ue_destination_codes_and_units():
    for dimension in DIMENSIONS:
        first, second, _ = CODES[dimension]
        field_a, field_b, _, _ = MONTHLY_FIELDS[dimension]
        rows = [link(empstat_a=21, empstat_b=12), link(empstat_a=21, empstat_b=21),
                link(empstat_a=20), link(empstat_a=21, **{field_b: '0000'}),
                link(empstat_a=21, **{field_a: '0000'}), link(empstat_a=21, **{field_b: first})]
        found = built(rows, 'monthly_ue', dimension)
        assert found['reason'].to_list() == [
            'eligible', 'destination_not_employed', 'origin_not_unemployed_21',
            'code_not_in_universe', 'code_not_in_universe', 'eligible']
        assert found.select('unit_a', 'unit_b').rows() == [
            (first, second), (first, second), (first, second), (first, '0000'),
            ('0000', second), (first, first)]
        assert found['strict'].to_list() == [True, False, False, False, False, True]


def test_asec_retro_is_off_diagonal_and_sensitivity_only():
    for dimension in DIMENSIONS:
        last, current = ASEC_FIELDS[dimension]
        first, second, _ = CODES[dimension]
        rows = [person(**{last: first, current: second}), person(**{last: first, current: first}),
                person(**{last: '0000', current: second})]
        found = built(rows, 'asec_retro', dimension)
        assert found['reason'].to_list() == [
            'eligible', 'same_category', 'last_year_code_not_in_universe']
        assert found['strict'].to_list() == [False, False, False]
        assert found['inclusion_reasons'].to_list() == [['asec_no_flag_evidence']] * 3
        assert found.select('unit_a', 'unit_b').rows() == [
            (first, second), (first, first), ('0000', second)]


def test_asec_retro_weight_employment_codes_and_specials():
    for dimension in DIMENSIONS:
        last, current = ASEC_FIELDS[dimension]
        first, second, special = CODES[dimension]
        rows = [person(weight_status='null'), person(weight_status='zero'), person(EMPSTAT=12),
                person(EMPSTAT=1), person(EMPSTAT=21), person(**{current: '0000'}),
                person(**{last: special}), person(QIND=4, QOCC=5, QOCCLY=1, QEMPSTAT=6)]
        found = built(rows, 'asec_retro', dimension)
        assert found['reason'].to_list() == [
            'weight_nonpositive', 'weight_nonpositive', 'eligible', 'not_employed',
            'not_employed', 'current_code_not_in_universe', 'eligible', 'eligible']
        assert found['special'].to_list() == [False] * 6 + [True, False]
        assert found['inclusion_reasons'].to_list()[-2:] == [
            ['asec_no_flag_evidence', 'special_military'], ['asec_no_flag_evidence']]
        assert not found['strict'].any()


def test_each_exclusion_reason_in_funnel_order():
    for product in PRODUCTS:
        for dimension in DIMENSIONS:
            frame = product_frame(source(product, cascade(product, dimension)), product,
                                  dimension, units=units())
            assert frame.collect()['reason'].to_list() == list(ORDER[product])
            found = funnel(frame, product, dimension)
            assert found['reason'].to_list() == list(ORDER[product])
            assert found['count'].to_list() == [1] * len(ORDER[product])


def cascade(product: str, dimension: str) -> list[dict]:
    '''One record per reason, in order, each also meeting every later exclusion it can.'''
    first = CODES[dimension][0]
    if product == 'asec_retro':
        last, current = ASEC_FIELDS[dimension]
        outside = {last: '0000', current: '0000'}
        return [person(weight_status='null', EMPSTAT=30, **outside),
                person(EMPSTAT=30, **outside), person(**outside),
                person(**{last: first, current: '0000'}), person(**{last: first, current: first}),
                person()]
    field_a, field_b, _, _ = MONTHLY_FIELDS[dimension]
    if product == 'monthly_ue':
        outside = {field_a: '0000'}
        return [link(weight_status='null', empstat_a=22, empstat_b=30, **outside),
                link(weight_status='zero', empstat_a=22, empstat_b=30, **outside),
                link(empstat_a=22, empstat_b=30, **outside),
                link(empstat_a=30, empstat_b=30, **outside),
                link(empstat_a=21, empstat_b=30, **outside),
                link(empstat_a=21, **outside), link(empstat_a=21)]
    unusable = {'empsame_b': 99, 'actsame_b': 99, field_b: '0000'}
    return [link(weight_status='null', empstat_b=30, **unusable),
            link(weight_status='zero', empstat_b=30, **unusable),
            link(empstat_a=30, **unusable), link(**unusable),
            link(empsame_b=99, actsame_b=99), link(empsame_b=2, actsame_b=1, **{field_b: first}),
            link(empsame_b=2, actsame_b=1), link()]


def test_funnel_lists_every_reason_with_zero_counts_and_refuses_an_unknown_reason():
    for product in PRODUCTS:
        for dimension in DIMENSIONS:
            found = funnel(product_frame(source(product, []), product, dimension,
                                         units=units()), product, dimension)
            assert found.schema == pl.Schema({'reason': pl.String, 'count': pl.UInt64})
            assert found.rows() == [(reason, 0) for reason in ORDER[product]]
    mixed = pl.LazyFrame({'reason': ['eligible', 'weight_null']})
    with pytest.raises(ValueError):
        funnel(mixed, 'asec_retro', 'industry')
    assert funnel(mixed, 'monthly_ue', 'industry')['count'].to_list() == [1, 0, 0, 0, 0, 0, 1]
    with pytest.raises(ValueError):
        funnel(pl.LazyFrame({'reason': ['eligible', None]}), 'monthly_ee', 'industry')
    for product, dimension in (('monthly', 'industry'), ('monthly_ee', 'geography')):
        with pytest.raises(ValueError):
            funnel(mixed, product, dimension)


def test_funnel_counts_each_reason_of_a_larger_frame():
    rows = [link(weight_status='null')] * 3 + [link(empsame_b=99)] * 2 + [link()] * 4
    found = funnel(product_frame(links(*rows), 'monthly_ee', 'occupation', units=units()),
                   'monthly_ee', 'occupation')
    assert dict(found.rows()) == {**dict.fromkeys(ORDER['monthly_ee'], 0), 'weight_null': 3,
                                  'guard_unusable': 2, 'eligible': 4}


# The funnel and evidence properties.

EMPSTATS = (0, 1, 10, 12, 21, 22, 30)
WEIGHTS = ('positive', 'null', 'zero')
LINK_ROWS = st.fixed_dictionaries({
    'weight_status': st.sampled_from(WEIGHTS), 'empstat_a': st.sampled_from(EMPSTATS),
    'empstat_b': st.sampled_from(EMPSTATS),
    'ind_a': st.sampled_from(('0170', '1370', '0000', '9890')),
    'ind_b': st.sampled_from(('0170', '1370', '0000', '9890')),
    'occ_a': st.sampled_from(('0010', '0020', '0000', '9840')),
    'occ_b': st.sampled_from(('0010', '0020', '0000', '9840')),
    'empsame_b': st.sampled_from(ANSWERS), 'actsame_b': st.sampled_from(ANSWERS),
    'qempstat_a': st.sampled_from((None, *range(7))),
    'qempstat_b': st.sampled_from((None, *range(7))),
    'qind_a': st.sampled_from((None, *range(8))), 'qind_b': st.sampled_from((None, *range(8))),
    'qocc_a': st.sampled_from((None, *range(8))), 'qocc_b': st.sampled_from((None, *range(8))),
}).map(lambda fields: link(**fields))
ASEC_ROWS = st.fixed_dictionaries({
    'weight_status': st.sampled_from(WEIGHTS), 'EMPSTAT': st.sampled_from(EMPSTATS),
    'INDLY': st.sampled_from(('0170', '1370', '0000', '9890')),
    'IND': st.sampled_from(('0170', '1370', '0000', '9890')),
    'OCCLY': st.sampled_from(('0010', '0020', '0000', '9840')),
    'OCC': st.sampled_from(('0010', '0020', '0000', '9840')),
    'QEMPSTAT': st.sampled_from((None, *range(7))), 'QIND': st.sampled_from((None, *range(8))),
    'QOCC': st.sampled_from((None, *range(8))), 'QOCCLY': st.sampled_from((None, 0, 1)),
}).map(lambda fields: person(**fields))


def expected_reason(row: dict, product: str, dimension: str) -> str:
    '''SD3 restated: the first exclusion that a record meets, or `eligible`.'''
    employed = (10, 12)
    if product == 'asec_retro':
        last, current = (row[name] for name in ASEC_FIELDS[dimension])
        if row['weight_status'] != 'positive':
            return 'weight_nonpositive'
        if row['EMPSTAT'] not in employed:
            return 'not_employed'
        if last == '0000':
            return 'last_year_code_not_in_universe'
        if current == '0000':
            return 'current_code_not_in_universe'
        return 'same_category' if last == current else 'eligible'
    code_a, code_b = (row[name] for name in MONTHLY_FIELDS[dimension][:2])
    if row['weight_status'] != 'positive':
        return f"weight_{row['weight_status']}"
    if product == 'monthly_ee':
        if row['empstat_a'] not in employed or row['empstat_b'] not in employed:
            return 'not_employed_both'
        if '0000' in (code_a, code_b):
            return 'code_not_in_universe'
        guard = GUARD_TABLE[row['empsame_b'], row['actsame_b']][GUARD_COLUMN[dimension]]
        if guard == 'unusable':
            return 'guard_unusable'
        if guard == 'same':
            return 'no_change_reported' if code_a == code_b else 'coding_noise'
        return 'eligible'
    if row['empstat_a'] == 22:
        return 'origin_new_worker_22'
    if row['empstat_a'] != 21:
        return 'origin_not_unemployed_21'
    if row['empstat_b'] not in employed:
        return 'destination_not_employed'
    return 'code_not_in_universe' if '0000' in (code_a, code_b) else 'eligible'


def expected_inclusion(row: dict, product: str, dimension: str) -> list[str]:
    '''The sensitivity inclusion reasons, restated from the brief, sorted and distinct.'''
    special = CODES[dimension][2]
    if product == 'asec_retro':
        found = {'asec_no_flag_evidence'}
        ends = [row[name] for name in ASEC_FIELDS[dimension]]
        return sorted(found | ({'special_military'} if special in ends else set()))
    field_a, field_b, prefix, variable = MONTHLY_FIELDS[dimension]
    found = {'special_military'} if special in (row[field_a], row[field_b]) else set()
    for name, column, table in (('QEMPSTAT', 'qempstat', QEMPSTAT_CLASSES),
                                (variable, prefix, QCODE_CLASSES)):
        for end in 'ab':
            value = row[f'{column}_{end}']
            if value is None:
                found.add(f'flag_unavailable:{name}')
            elif table[value] != 'nonallocation':
                found.add(f'flag:{name}:{table[value]}')
    return sorted(found)


@settings(derandomize=True, deadline=None, max_examples=60)
@given(product=st.sampled_from(PRODUCTS), dimension=st.sampled_from(DIMENSIONS),
       monthly=st.lists(LINK_ROWS, max_size=12), asec=st.lists(ASEC_ROWS, max_size=12))
def test_funnel_is_disjoint_and_sums_to_the_source_total(product, dimension, monthly, asec):
    rows = asec if product == 'asec_retro' else monthly
    frame = product_frame(source(product, rows), product, dimension, units=units())
    expected = [expected_reason(row, product, dimension) for row in rows]
    assert frame.collect()['reason'].to_list() == expected
    found = funnel(frame, product, dimension)
    tally = Counter(expected)
    assert found.rows() == [(reason, tally[reason]) for reason in ORDER[product]]
    assert found['count'].sum() == len(rows)


@settings(derandomize=True, deadline=None, max_examples=60)
@given(product=st.sampled_from(PRODUCTS), dimension=st.sampled_from(DIMENSIONS),
       monthly=st.lists(LINK_ROWS, min_size=1, max_size=12),
       asec=st.lists(ASEC_ROWS, min_size=1, max_size=12))
def test_evidence_policies_follow_the_flag_classes(product, dimension, monthly, asec):
    rows = asec if product == 'asec_retro' else monthly
    found = built(rows, product, dimension)
    inclusion = [expected_inclusion(row, product, dimension) for row in rows]
    assert found['inclusion_reasons'].to_list() == inclusion
    eligible = [expected_reason(row, product, dimension) == 'eligible' for row in rows]
    monthly_product = product != 'asec_retro'
    assert found['strict'].to_list() == [
        monthly_product and admitted and not entries
        for admitted, entries in zip(eligible, inclusion)]
    ends = ASEC_FIELDS[dimension] if product == 'asec_retro' else MONTHLY_FIELDS[dimension][:2]
    assert found.select('unit_a', 'unit_b').rows() == [
        tuple(row[name] for name in ends) for row in rows]
    assert found['special'].to_list() == [
        CODES[dimension][2] in (row[ends[0]], row[ends[1]]) for row in rows]
    if dimension == 'industry':
        assert found['noise_after_duty_change'].to_list() == [
            product == 'monthly_ee' and row['empsame_b'] == 2 and row['actsame_b'] == 2
            and expected_reason(row, product, dimension) == 'coding_noise' for row in rows]


# Evidence policies.

def test_allocated_and_special_ends_never_reach_strict():
    diagonal = built([link(ind_b='0170', qind_b=6)], 'monthly_ee', 'industry')
    assert diagonal['reason'].to_list() == ['eligible']
    assert diagonal['strict'].to_list() == [False]
    assert diagonal['inclusion_reasons'].to_list() == [['flag:QIND:allocated']]
    origin = link(empstat_a=21, ind_a='9890', occ_a='9840')
    for dimension in DIMENSIONS:
        found = built([origin], 'monthly_ue', dimension)
        assert found['reason'].to_list() == ['eligible']
        assert found['strict'].to_list() == [False]
        assert found['special'].to_list() == [True]
        assert found['inclusion_reasons'].to_list() == [['special_military']]
    unavailable = built([link(qind_a=None)], 'monthly_ee', 'industry')
    assert unavailable['reason'].to_list() == ['eligible']
    assert unavailable['strict'].to_list() == [False]
    assert unavailable['inclusion_reasons'].to_list() == [['flag_unavailable:QIND']]


def test_each_flag_class_reaches_the_inclusion_reasons_at_either_end():
    rows = [link(qind_a=1), link(qind_b=4), link(qind_a=7), link(qempstat_b=6),
            link(qempstat_a=None), link(qempstat_a=5), link(qind_b=2), link(qind_b=0)]
    found = built(rows, 'monthly_ee', 'industry')
    assert found['inclusion_reasons'].to_list() == [
        ['flag:QIND:edited'], ['flag:QIND:allocated'], ['flag:QIND:longitudinal'],
        ['flag:QEMPSTAT:longitudinal'], ['flag_unavailable:QEMPSTAT'],
        ['flag:QEMPSTAT:allocated'], ['flag:QIND:edited'], []]
    assert found['strict'].to_list() == [False] * 7 + [True]
    assert set(found['reason']) == {'eligible'}


def test_each_dimension_reads_its_own_codes_flags_and_guard():
    rows = [link(qocc_a=4), link(qind_b=4), link(ind_b='0000'), link(occ_b='0000'),
            link(empsame_b=2, actsame_b=96), link(ind_b='9890'), link(occ_a='9840')]
    industry = built(rows, 'monthly_ee', 'industry')
    occupation = built(rows, 'monthly_ee', 'occupation')
    assert industry['reason'].to_list() == [
        'eligible', 'eligible', 'code_not_in_universe', 'eligible', 'coding_noise', 'eligible',
        'eligible']
    assert occupation['reason'].to_list() == [
        'eligible', 'eligible', 'eligible', 'code_not_in_universe', 'guard_unusable',
        'eligible', 'eligible']
    assert industry['strict'].to_list() == [True, False, False, True, False, False, True]
    assert occupation['strict'].to_list() == [False, True, True, False, False, True, False]
    assert industry['special'].to_list() == [False] * 5 + [True, False]
    assert occupation['special'].to_list() == [False] * 6 + [True]
    assert industry.select('unit_a', 'unit_b').row(0) == ('0170', '1370')
    assert occupation.select('unit_a', 'unit_b').row(0) == ('0010', '0020')


def test_inclusion_reasons_are_sorted_distinct_and_never_null():
    rows = [link(qind_a=4, qind_b=5),
            link(qind_a=1, qind_b=6, qempstat_a=None, qempstat_b=None, ind_a='9890'), link()]
    found = built(rows, 'monthly_ee', 'industry')
    assert found.schema['inclusion_reasons'] == pl.List(pl.String)
    assert found['inclusion_reasons'].to_list() == [
        ['flag:QIND:allocated'],
        ['flag:QIND:allocated', 'flag:QIND:edited', 'flag_unavailable:QEMPSTAT',
         'special_military'],
        []]
    assert found['inclusion_reasons'].null_count() == 0


# The frame itself.

def test_product_frame_keeps_every_row_column_and_order():
    rows = [link(), link(weight_status='null'), link(mish_b=5, empsame_b=1), link(empsame_b=99)]
    for product in ('monthly_ee', 'monthly_ue'):
        for dimension in DIMENSIONS:
            found = built(rows, product, dimension)
            extra = ['noise_after_duty_change'] if dimension == 'industry' else []
            assert found.columns == [*LINK_SCHEMA, *NEW_COLUMNS, *extra]
            assert found['source_row_a'].to_list() == [0, 2, 4, 6]
            assert found.select(list(LINK_SCHEMA)).equals(links(*rows).collect())
            assert found.schema['strict'] == pl.Boolean
            assert found.schema['special'] == pl.Boolean
    retro = built([person(), person(EMPSTAT=30), person()], 'asec_retro', 'industry')
    assert retro.columns == [*ASEC_SCHEMA, *NEW_COLUMNS, 'noise_after_duty_change']
    assert retro['CPSID'].to_list() == [1, 2, 3]
    assert built([person()], 'asec_retro', 'occupation').columns == [*ASEC_SCHEMA, *NEW_COLUMNS]


def test_rule_validation_runs_on_every_row_whatever_is_read_later():
    bad_rows = {
        'monthly_ee': [link(weight_status='null', qind_b=9)],
        'monthly_ue': [link(weight_status='zero', empsame_b=3)],
        'asec_retro': [person(weight_status='null', QOCCLY=2)]}
    for product, bad in bad_rows.items():
        good = [person()] if product == 'asec_retro' else [link()]
        frame = product_frame(source(product, [*good, *bad]), product, 'industry',
                              units=units())
        for query in (frame.select('reason'), frame.filter(pl.col('reason') == 'eligible'),
                      frame.head(1), frame.select('unit_a')):
            with pytest.raises(ValueError):
                query.collect()
        with pytest.raises(ValueError):
            funnel(frame, product, 'industry')


def test_links_must_be_one_month_with_a_known_weight_status():
    for fields in ({'link_type': 'two_month'}, {'link_type': None},
                   {'weight_status': 'not_linkable'}, {'weight_status': None},
                   {'weight_status': 'negative'}):
        for product in ('monthly_ee', 'monthly_ue'):
            with pytest.raises(ValueError):
                built([link(), link(**fields)], product, 'occupation')
    for status in ('not_linkable', None, 'positive '):
        with pytest.raises(ValueError):
            built([person(), person(weight_status=status)], 'asec_retro', 'occupation')


def test_empstat_outside_its_ddi_set_fails():
    for fields in ({'empstat_a': 5}, {'empstat_b': 11}, {'empstat_b': None},
                   {'empstat_a': None}):
        for product in ('monthly_ee', 'monthly_ue'):
            with pytest.raises(ValueError):
                built([link(), link(**fields)], product, 'industry')
    for value in (2, None, 37):
        with pytest.raises(ValueError):
            built([person(), person(EMPSTAT=value)], 'asec_retro', 'industry')


def test_an_unparseable_or_foreign_code_fails_in_every_product():
    for product, fields, dimension in (
            ('monthly_ee', {'ind_a': '170'}, 'industry'),
            ('monthly_ee', {'occ_b': '9890'}, 'occupation'),
            ('monthly_ue', {'ind_b': '9920'}, 'industry'),
            ('monthly_ue', {'occ_a': '1234'}, 'occupation'),
            ('asec_retro', {'INDLY': '1234'}, 'industry'),
            ('asec_retro', {'IND': '0010'}, 'industry'),
            ('asec_retro', {'OCCLY': '9830'}, 'occupation'),
            ('asec_retro', {'OCC': None}, 'occupation')):
        row = person(**fields) if product == 'asec_retro' else link(**fields)
        with pytest.raises(ValueError):
            built([row], product, dimension)


def test_unknown_product_or_dimension_fails():
    for product, dimension in (('monthly', 'industry'), ('asec_retro', 'geography'),
                               ('monthly_ee', 'Industry')):
        with pytest.raises(ValueError):
            product_frame(links(link()), product, dimension, units=units())


def test_each_refusal_has_a_fixed_message_without_row_content():
    cases = [([link(qind_b=9)], 'monthly_ee'), ([link(empsame_b=3)], 'monthly_ee'),
             ([link(empstat_b=5)], 'monthly_ue'), ([link(weight_status='bad')], 'monthly_ee'),
             ([link(link_type='two_month')], 'monthly_ue'), ([person(QOCCLY=4)], 'asec_retro')]
    seen = set()
    for rows, product in cases:
        with pytest.raises(ValueError) as caught:
            built(rows, product, 'industry')
        message = str(caught.value)
        assert not any(character.isdigit() for character in message)
        assert 'two_month' not in message and 'bad' not in message
        seen.add(message)
    assert len(seen) == len(cases)


def test_a_failing_expression_raises_one_fixed_message_without_the_value():
    for failing in (lambda value, at: guards('industry', at([1, value]), [99, 99, 1]),
                    lambda value, at: guards('occupation', [2, 2, 2], at([1, value])),
                    lambda value, at: classes('monthly', 'QIND', at([0, value]))):
        messages = set()
        for value in (4242, 5353):
            for at in (lambda pair: [pair[1], pair[0], pair[0]],
                       lambda pair: [pair[0], pair[1], pair[0]],
                       lambda pair: [pair[0], pair[1], pair[1]]):
                with pytest.raises(ValueError) as caught:
                    failing(value, at)
                assert str(value) not in str(caught.value)
                messages.add(str(caught.value).splitlines()[0])
        assert len(messages) == 1
        assert not any(character.isdigit() for character in messages.pop())


# Guard diagnostics.

def test_usable_guard_share_and_mish_exceptions():
    counted = [link(), link(empstat_a=12, empsame_b=2, actsame_b=1),
               link(empstat_b=12, empsame_b=2, actsame_b=96), link(empsame_b=99),
               link(ind_b='0000', occ_b='0000')]
    excluded = [link(link_type='two_month', empsame_b=99),
                link(weight_status='null', empsame_b=99),
                link(weight_status='zero', empsame_b=99), link(empstat_a=21, empsame_b=99),
                link(empstat_b=30, empsame_b=99)]
    shares = usable_guard_share(links(*counted, *excluded))
    assert shares == {'industry': 4 / 5, 'occupation': 3 / 5}
    assert list(shares) == ['industry', 'occupation']
    exceptions = [link(mish_b=5, empsame_b=1), link(mish_b=1, empsame_b=2),
                  link(mish_b=5, empsame_b=2)]
    others = [link(mish_b=5, empsame_b=99), link(mish_b=1, empsame_b=97), link(mish_b=2),
              link(mish_b=6, empsame_b=2), link(mish_b=4, empsame_b=1)]
    frame = links(*others[:2], *exceptions, *others[2:])
    assert guard_source_exceptions(frame) == 3
    kept = built([*others[:2], *exceptions, *others[2:]], 'monthly_ee', 'industry')
    assert kept.height == 8
    assert kept['reason'].to_list()[2:5] == ['eligible', 'coding_noise', 'coding_noise']


def test_usable_guard_share_of_no_employed_link_fails():
    for rows in ([], [link(weight_status='zero')], [link(empstat_b=21)]):
        with pytest.raises(ValueError):
            usable_guard_share(links(*rows))


# ASEC flag counts.

def test_asec_flag_counts_cover_every_empstat():
    rows = [person(EMPSTAT=10), person(EMPSTAT=10, QIND=4), person(EMPSTAT=1, QOCCLY=1),
            person(EMPSTAT=0, QEMPSTAT=None), person(EMPSTAT=30, QOCC=7),
            person(EMPSTAT=12), person(EMPSTAT=21, QEMPSTAT=6), person(EMPSTAT=22, QOCC=None),
            person(EMPSTAT=10, IND='0000', weight_status='zero')]
    found = asec_flag_counts(people(*rows))
    assert found == {
        'QIND': {'0': {'0': 1}, '1': {'0': 1}, '10': {'0': 2, '4': 1}, '12': {'0': 1},
                 '21': {'0': 1}, '22': {'0': 1}, '30': {'0': 1}},
        'QOCC': {'0': {'0': 1}, '1': {'0': 1}, '10': {'0': 3}, '12': {'0': 1},
                 '21': {'0': 1}, '22': {'null': 1}, '30': {'7': 1}},
        'QOCCLY': {'0': {'0': 1}, '1': {'1': 1}, '10': {'0': 3}, '12': {'0': 1},
                   '21': {'0': 1}, '22': {'0': 1}, '30': {'0': 1}},
        'QEMPSTAT': {'0': {'null': 1}, '1': {'0': 1}, '10': {'0': 3}, '12': {'0': 1},
                     '21': {'6': 1}, '22': {'0': 1}, '30': {'0': 1}}}
    assert list(found) == ['QIND', 'QOCC', 'QOCCLY', 'QEMPSTAT']
    assert list(found['QIND']) == ['0', '1', '10', '12', '21', '22', '30']
    assert list(found['QIND']['10']) == ['0', '4']
    many = asec_flag_counts(people(person(QEMPSTAT=6), person(QEMPSTAT=None),
                                   person(QEMPSTAT=1), person(QEMPSTAT=None)))
    assert list(many['QEMPSTAT']['10'].items()) == [('1', 1), ('6', 1), ('null', 2)]


def test_asec_flag_counts_need_only_empstat_and_the_flags():
    frame = people(person(EMPSTAT=1, QOCCLY=1), person()).select(
        'EMPSTAT', 'QIND', 'QOCC', 'QOCCLY', 'QEMPSTAT')
    assert asec_flag_counts(frame)['QOCCLY'] == {'1': {'1': 1}, '10': {'0': 1}}


def test_asec_flag_counts_refuse_an_undelivered_value():
    for fields in ({'QOCCLY': 2}, {'QIND': 8}, {'QEMPSTAT': 7}, {'QOCC': -1},
                   {'EMPSTAT': None}, {'EMPSTAT': 2}):
        with pytest.raises(ValueError):
            asec_flag_counts(people(person(), person(**fields)))
