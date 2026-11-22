'''TRI parent industry table (O8): one row for each parent and industry, on synthetic rows.'''

import json
from functools import cache

import polars as pl
import pytest
from tri_fixtures import rows_frame

from embedding_data.tri_codes import NODE_PREFIX
from embedding_data.tri_facility_years import EXCLUSIONS, reduce
from embedding_data.tri_layout import load_layouts
from embedding_data.tri_parent_industries import (
    SCHEMA,
    build_parent_industries,
    parent_report,
    validate_parent_industries,
)

LAYOUTS = load_layouts()
# Real NAICS 2022 codes stand for the selected national-industry nodes. Their sorted order is
# the order of the letters, so that a, b, c, d name the rows in the order that they are listed.
A, B, C, D = (NODE_PREFIX + code for code in ('212311', '221114', '311111', '325199'))
NODES = frozenset({A, B, C, D})
COUNTS = ['n_facilities', 'n_facility_years', 'f_2022', 'f_2023', 'f_2024']
OUTSIDE = '^reporting year outside the window$'
PARENTS = 'parents differ from the facility-years'
ROWS = 'rows differ from the facility-years'
COUNT_MESSAGE = 'counts differ from the facility-years'
KEY = 'key not unique and sorted'
SCHEMA_MESSAGE = 'schema differs'


def form(year: int, trifd: str, node: str, parent: str = '', **fields: str) -> dict:
    '''One synthetic Form R row: not federal, in Texas, with the primary code of the node.'''
    row = dict(year=year, reporting_year=str(year), trifd=trifd, form_type='R', federal='NO',
               state='TX', primary_naics=node.removeprefix(NODE_PREFIX),
               standardized_parent=parent)
    return {**row, **fields}


def excluded(reason: str, year: int, trifd: str, *parents: str) -> list[dict]:
    '''Form rows of one facility-year that is excluded for the reason, one row for each parent.'''
    names = parents or ('',)
    if reason == 'naics_missing':
        return [form(year, trifd, A, name, primary_naics='') for name in names]
    if reason == 'naics_conflict':
        return [form(year, trifd, node, name) for node in (A, B) for name in names]
    if reason == 'naics_not_2022':
        return [form(year, trifd, A, name, primary_naics='999999') for name in names]
    if reason == 'federal':
        return [form(year, trifd, A, name, federal='YES') for name in names]
    assert reason == 'parent_conflict' and len(names) > 1
    return [form(year, trifd, A, name) for name in names]


def reduced(records: list[dict]) -> pl.DataFrame:
    return reduce(rows_frame(records), LAYOUTS, NODES)


def table_of(records: list[dict]) -> pl.DataFrame:
    return build_parent_industries(reduced(records))


def minimal(rows: list[tuple]) -> pl.DataFrame:
    '''The five columns that the table reads, as (year, TRIFD, node, owner key, reason) rows.'''
    schema = {'reporting_year': pl.Int64, 'trifd': pl.String, 'naics_2022_node_id': pl.String,
              'owner_key': pl.String, 'exclusion_reason': pl.String}
    return pl.DataFrame(rows, schema=schema, orient='row')


def from_rows(rows: list[tuple]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=SCHEMA, orient='row')


def example_records() -> list[dict]:
    '''Three parents in four industries, with a facility that changes industry, every number
    of which is worked out by hand.

    Acme: T1 in a in 2022 and 2023, T2 in a in 2022, T3 in b in 2023, and T1 in c in 2024.
    Beta: T4 in a in 2023. Core: T5 to T9 in b in 2022 and T5 in b in 2023. T10 owns itself.
    T11 (parent Dune, federal) and T12 (parent Echo, no code) are excluded, and each parent has
    no other facility.
    '''
    return [
        form(2022, 'T1', A, 'Acme'), form(2022, 'T2', A, 'Acme'),
        form(2023, 'T1', A, 'Acme'), form(2023, 'T3', B, 'Acme'), form(2024, 'T1', C, 'Acme'),
        form(2023, 'T4', A, 'Beta'),
        *(form(2022, f'T{number}', B, 'Core') for number in range(5, 10)),
        form(2023, 'T5', B, 'Core'),
        form(2022, 'T10', D),
        *excluded('federal', 2023, 'T11', 'Dune'),
        *excluded('naics_missing', 2024, 'T12', 'Echo'),
    ]


EXAMPLE_ROWS = [
    ('Acme', A, 2, 3, 2, 1, 0),
    ('Acme', B, 1, 1, 0, 1, 0),
    ('Acme', C, 1, 1, 0, 0, 1),
    ('Beta', A, 1, 1, 0, 1, 0),
    ('Core', B, 5, 6, 5, 1, 0),
]


def test_the_schema_is_the_documented_one():
    assert list(SCHEMA.items()) == [
        ('parent_name', pl.String), ('node_id', pl.String), ('n_facilities', pl.UInt64),
        ('n_facility_years', pl.UInt64), ('f_2022', pl.UInt64), ('f_2023', pl.UInt64),
        ('f_2024', pl.UInt64)]


def test_one_row_per_parent_and_industry():
    # P: T1 in a for 2022 and 2023, T2 in a for 2023, T3 in b for 2024
    table = table_of([
        form(2022, 'T1', A, 'P'), form(2023, 'T1', A, 'P'), form(2023, 'T2', A, 'P'),
        form(2024, 'T3', B, 'P')])
    rows = table.rows()
    assert rows == [('P', A, 2, 3, 1, 2, 0), ('P', B, 1, 1, 0, 0, 1)]


@pytest.mark.parametrize('records', [
    [],
    [form(2022, 'T1', A)],
    excluded('federal', 2022, 'T1', 'P'),
], ids=['no rows', 'self-owned only', 'excluded only'])
def test_an_empty_selection_gives_an_empty_table_with_the_schema(records):
    table = table_of(records)
    assert table.height == 0
    assert list(table.schema.items()) == list(SCHEMA.items())


def test_self_owned_and_excluded_facility_years_are_left_out():
    records = [
        form(2023, 'T1', A, 'P'),
        form(2022, 'T6', A), form(2023, 'T6', A), form(2024, 'T6', A),
        form(2022, 'T7', B), form(2023, 'T8', A),
        *(row for number, reason in enumerate(EXCLUSIONS) for row in excluded(
            reason, 2022 + number % 3, f'T{20 + number}',
            *(('P', 'Q') if reason == 'parent_conflict' else ('P',)))),
        *excluded('federal', 2023, 'T30', 'Q'),
        *excluded('naics_missing', 2024, 'T31', 'R'),
    ]
    assert table_of(records).rows() == [('P', A, 1, 1, 0, 1, 0)]


@pytest.mark.parametrize('reason', EXCLUSIONS)
def test_each_excluded_reason_is_left_out_of_every_count(reason):
    names = ('P', 'Z') if reason == 'parent_conflict' else ('P',)
    others = ('Q', 'Z') if reason == 'parent_conflict' else ('Q',)
    table = table_of([
        form(2023, 'T1', A, 'P'),
        *excluded(reason, 2022, 'T2', *names), *excluded(reason, 2024, 'T3', *names),
        *excluded(reason, 2023, 'T4', *others)])
    assert table.rows() == [('P', A, 1, 1, 0, 1, 0)]


def test_an_excluded_row_that_carries_a_parent_key_is_left_out():
    # `reduce` gives an excluded row no owner key, but the table names both conditions
    frame = minimal([
        (2023, 'T1', A, 'parent:P', None),
        (2023, 'T2', A, 'parent:P', 'federal'),
        (2022, 'T3', B, 'parent:P', 'parent_conflict'),
        (2022, 'T4', B, 'parent:Q', 'naics_conflict')])
    assert build_parent_industries(frame).rows() == [('P', A, 1, 1, 0, 1, 0)]


def test_a_self_owned_facility_is_not_a_parent():
    # the prefix must start the key: a `facility:` key that holds it later is still self-owned
    frame = minimal([(2023, 'T1', A, 'facility:T1', None), (2023, 'T2', A, 'parent:P', None),
                     (2023, 'T3', A, 'facility:parent:T3', None)])
    assert build_parent_industries(frame).rows() == [('P', A, 1, 1, 0, 1, 0)]


def test_a_facility_that_changes_industry_counts_once_in_each_industry():
    table = table_of([
        form(2022, 'T1', A, 'P'), form(2023, 'T1', B, 'P'), form(2024, 'T1', B, 'P')])
    assert table.rows() == [('P', A, 1, 1, 1, 0, 0), ('P', B, 1, 2, 0, 1, 1)]


def test_a_facility_that_changes_parent_counts_once_for_each_parent():
    table = table_of([form(2022, 'T1', A, 'P'), form(2023, 'T1', A, 'Q')])
    assert table.rows() == [('P', A, 1, 1, 1, 0, 0), ('Q', A, 1, 1, 0, 1, 0)]


def test_a_parent_with_one_industry_has_one_row():
    table = table_of([form(2023, 'T1', C, 'Solo'), form(2024, 'T2', C, 'Solo')])
    assert table.rows() == [('Solo', C, 2, 2, 0, 1, 1)]


def test_a_facility_in_each_year_of_one_industry_counts_once_a_facility_and_once_a_year():
    table = table_of([form(year, 'T1', A, 'P') for year in (2022, 2023, 2024)])
    assert table.rows() == [('P', A, 1, 3, 1, 1, 1)]


def test_many_facilities_count_distinct_trifds_in_total_and_in_each_year():
    table = table_of([
        form(2022, 'T1', A, 'P'), form(2022, 'T2', A, 'P'),
        form(2023, 'T1', A, 'P'), form(2023, 'T2', A, 'P'), form(2023, 'T3', A, 'P'),
        form(2024, 'T1', A, 'P'), form(2024, 'T4', A, 'P')])
    assert table.rows() == [('P', A, 4, 7, 2, 3, 2)]


def test_a_year_with_no_facility_counts_zero():
    table = table_of([form(2023, 'T1', A, 'P'), form(2023, 'T2', B, 'P')])
    assert [row[4:] for row in table.rows()] == [(0, 1, 0), (0, 1, 0)]


def test_a_repeated_facility_year_row_still_counts_distinct_trifds():
    # a reduced frame has one row for each facility-year, so a repeat is not expected; the
    # distinct counts follow their meaning and `n_facility_years` counts the rows
    frame = minimal([(2023, 'T1', A, 'parent:P', None), (2023, 'T1', A, 'parent:P', None)])
    assert build_parent_industries(frame).rows() == [('P', A, 1, 2, 0, 1, 0)]


def test_several_parents_share_an_industry_and_keep_their_own_counts():
    table = table_of([
        form(2022, 'T1', A, 'P'), form(2022, 'T2', A, 'P'),
        form(2022, 'T3', A, 'Q'), form(2023, 'T3', A, 'Q'),
        form(2024, 'T4', A, 'R')])
    assert table.rows() == [
        ('P', A, 2, 2, 2, 0, 0), ('Q', A, 1, 2, 1, 1, 0), ('R', A, 1, 1, 0, 0, 1)]


def test_the_hand_computed_example():
    table = table_of(example_records())
    assert list(table.schema.items()) == list(SCHEMA.items())
    assert table.rows() == EXAMPLE_ROWS
    assert table['n_facilities'].sum() == 10 and table['n_facility_years'].sum() == 12


def test_the_table_is_sorted_by_parent_name_and_then_by_node_id():
    records = [
        form(2023, 'T1', D, 'Zeta'), form(2023, 'T2', B, 'Zeta'),
        form(2023, 'T3', C, 'Zeta'), form(2023, 'T4', A, 'Zeta'),
        form(2023, 'T5', D, 'Alpha'), form(2023, 'T6', A, 'Alpha'), form(2023, 'T7', C, 'Alpha'),
        form(2023, 'T8', B, 'Mid'), form(2023, 'T9', D, 'Mid')]
    keys = table_of(records).select('parent_name', 'node_id').rows()
    assert keys == [
        ('Alpha', A), ('Alpha', C), ('Alpha', D), ('Mid', B), ('Mid', D),
        ('Zeta', A), ('Zeta', B), ('Zeta', C), ('Zeta', D)]


def test_the_order_of_the_facility_years_does_not_change_the_table():
    frame = reduced(example_records())
    expected = build_parent_industries(frame)
    assert build_parent_industries(frame.reverse()).equals(expected)
    assert build_parent_industries(frame.sort('trifd', descending=True)).equals(expected)


def test_the_parent_name_is_the_key_without_its_prefix_and_nothing_else():
    names = ['Acme', 'ACME', 'parent', 'tenant', 'parent:X', 'Mid parent: name', 'Two  Spaces']
    table = table_of([form(2023, f'T{number}', A, name) for number, name in enumerate(names)])
    assert table['parent_name'].to_list() == sorted(names)
    assert table['n_facilities'].to_list() == [1] * len(names)


def test_the_parent_name_keeps_its_spaces_and_removes_the_prefix_once():
    frame = minimal([
        (2023, 'T1', A, 'parent: Padded ', None), (2023, 'T2', A, 'parent:parent:X', None),
        (2023, 'T3', A, 'parent:Acme', None), (2023, 'T4', A, 'parent:ACME', None)])
    assert build_parent_industries(frame)['parent_name'].to_list() == [
        ' Padded ', 'ACME', 'Acme', 'parent:X']


@pytest.mark.parametrize('year', [2021, 2025, 0, None])
@pytest.mark.parametrize('trifd', ['T1', 'T6', 'T7'], ids=['parent', 'self-owned', 'excluded'])
def test_a_year_outside_the_window_raises_a_fixed_message(trifd, year):
    frame = reduced([
        form(2022, 'T1', A, 'P'), form(2023, 'T6', A), *excluded('federal', 2024, 'T7', 'P')])
    shifted = frame.with_columns(
        pl.when(pl.col('trifd') == trifd).then(pl.lit(year, dtype=pl.Int64))
        .otherwise(pl.col('reporting_year')).alias('reporting_year'))
    with pytest.raises(ValueError, match=OUTSIDE):
        build_parent_industries(shifted)


def test_a_null_node_in_a_row_that_the_table_counts_raises_a_fixed_message():
    frame = minimal([(2023, 'T1', A, 'parent:P', None), (2023, 'T2', None, 'parent:P', None)])
    with pytest.raises(ValueError, match='^node is null$'):
        build_parent_industries(frame)


def test_a_null_node_in_a_row_that_the_table_leaves_out_is_ignored():
    frame = minimal([
        (2023, 'T1', A, 'parent:P', None), (2023, 'T2', None, None, 'naics_missing'),
        (2023, 'T3', None, 'facility:T3', None)])
    assert build_parent_industries(frame).rows() == [('P', A, 1, 1, 0, 1, 0)]


# ---- the validator

@cache
def example_frame() -> pl.DataFrame:
    return reduced(example_records())


@cache
def example_table() -> pl.DataFrame:
    return build_parent_industries(example_frame())


def test_the_validator_accepts_the_table_that_the_builder_gives():
    assert validate_parent_industries(example_table(), example_frame()) is None


def test_the_validator_accepts_an_empty_table_of_an_empty_selection():
    for empty in (reduced([]), reduced([form(2022, 'T1', A)])):
        validate_parent_industries(build_parent_industries(empty), empty)


def changed(column: str, row: int, delta: int) -> pl.DataFrame:
    rows = example_table().rows()
    index = list(SCHEMA).index(column)
    rows[row] = (*rows[row][:index], rows[row][index] + delta, *rows[row][index + 1:])
    return from_rows(rows)


@pytest.mark.parametrize('column', COUNTS)
@pytest.mark.parametrize('delta', [1, -1], ids=['too high', 'too low'])
def test_validator_rejects_counts_that_differ_from_the_facility_years(column, delta):
    # a row whose count is at least one, so that a count one too low is still a count
    row = next(number for number, value in enumerate(example_table()[column]) if value >= 1)
    with pytest.raises(ValueError, match=f'^{COUNT_MESSAGE}$'):
        validate_parent_industries(changed(column, row, delta), example_frame())


@pytest.mark.parametrize('column', COUNTS)
def test_the_validator_rejects_a_count_that_is_off_on_any_row(column):
    for row in range(example_table().height):
        with pytest.raises(ValueError, match=f'^{COUNT_MESSAGE}$'):
            validate_parent_industries(changed(column, row, 2), example_frame())


@pytest.mark.parametrize('row, count', [(0, 0), (2, 1)],
                         ids=['where the count is 0', 'where the count is 1'])
def test_the_validator_rejects_a_null_count(row, count):
    rows = example_table().rows()
    assert rows[row][6] == count
    rows[row] = (*rows[row][:6], None)
    with pytest.raises(ValueError, match=f'^{COUNT_MESSAGE}$'):
        validate_parent_industries(from_rows(rows), example_frame())


# Each break is a table that breaks one rule of the validator, built from the good table and
# its rows, and the message that names the rule. The five rows are Acme in a, b and c, Beta in
# a and Core in b.
BREAKS = {
    'a wrong column type': (lambda good, rows: good.cast({'n_facilities': pl.UInt32}),
                            SCHEMA_MESSAGE),
    'columns out of order': (lambda good, rows: good.select(*reversed(good.columns)),
                             SCHEMA_MESSAGE),
    'a missing column': (lambda good, rows: good.drop('f_2024'), SCHEMA_MESSAGE),
    'an extra column': (lambda good, rows: good.with_columns(extra=pl.lit(1)), SCHEMA_MESSAGE),
    'a renamed column': (lambda good, rows: good.rename({'f_2024': 'f_2025'}), SCHEMA_MESSAGE),
    'a duplicated first row': (lambda good, rows: from_rows([rows[0], *rows]), KEY),
    'a duplicated last row': (lambda good, rows: from_rows([*rows, rows[-1]]), KEY),
    'swapped rows': (lambda good, rows: from_rows([rows[1], rows[0], *rows[2:]]), KEY),
    'a reversed table': (lambda good, rows: from_rows(rows[::-1]), KEY),
    'node order first': (lambda good, rows: good.sort('node_id', 'parent_name'), KEY),
    'a null parent name': (lambda good, rows: from_rows([(None, *rows[0][1:]), *rows[1:]]), KEY),
    'a null node': (lambda good, rows: from_rows([(rows[0][0], None, *rows[0][2:]), *rows[1:]]),
                    KEY),
    'a missing parent': (lambda good, rows: from_rows(rows[:3] + rows[4:]), PARENTS),
    'a missing last parent': (lambda good, rows: from_rows(rows[:-1]), PARENTS),
    'a renamed parent': (lambda good, rows: from_rows(
        [*rows[:3], ('Bzzz', *rows[3][1:]), rows[4]]), PARENTS),
    'a parent with no facility-year': (lambda good, rows: from_rows(
        [*rows, ('Zulu', A, 1, 1, 1, 0, 0)]), PARENTS),
    'a self-owned facility as a parent': (lambda good, rows: from_rows(
        [*rows, ('facility:T10', D, 1, 1, 1, 0, 0)]), PARENTS),
    'an excluded parent': (lambda good, rows: from_rows(
        [*rows, ('Dune', A, 1, 1, 0, 1, 0)]), PARENTS),
    'a missing row of a parent': (lambda good, rows: from_rows(rows[:1] + rows[2:]), ROWS),
    'an extra row of a parent': (lambda good, rows: from_rows(
        [*rows[:3], ('Acme', D, 1, 1, 1, 0, 0), *rows[3:]]), ROWS),
    'a changed node': (lambda good, rows: from_rows(
        [*rows[:2], (rows[2][0], D, *rows[2][2:]), *rows[3:]]), ROWS),
    'counts swapped between two rows': (lambda good, rows: from_rows(
        [(*rows[0][:2], *rows[1][2:]), (*rows[1][:2], *rows[0][2:]), *rows[2:]]), COUNT_MESSAGE),
}


def broken(name: str) -> pl.DataFrame:
    return BREAKS[name][0](example_table(), example_table().rows())


@pytest.mark.parametrize('name', BREAKS)
def test_the_validator_rejects_each_break_with_the_message_of_its_rule(name):
    with pytest.raises(ValueError, match=f'^{BREAKS[name][1]}$'):
        validate_parent_industries(broken(name), example_frame())


def test_the_validator_messages_hold_no_cell_value():
    values = {'Acme', 'Beta', 'Core', 'Bzzz', 'Zulu', 'Dune', 'T10', A, B, C, D, NODE_PREFIX}
    for name in BREAKS:
        with pytest.raises(ValueError) as failure:
            validate_parent_industries(broken(name), example_frame())
        assert not [value for value in values if value in str(failure.value)], name


def test_the_validator_rejects_a_table_of_another_frame_by_its_counts():
    short = reduced([form(2022, 'T1', A, 'Acme')])
    longer = reduced([form(2022, 'T1', A, 'Acme'), form(2023, 'T1', A, 'Acme')])
    validate_parent_industries(build_parent_industries(short), short)
    with pytest.raises(ValueError, match=f'^{COUNT_MESSAGE}$'):
        validate_parent_industries(build_parent_industries(short), longer)


def test_the_validator_rejects_a_table_of_a_frame_with_no_parents():
    for empty in (reduced([]), reduced([form(2022, 'T1', A)])):
        with pytest.raises(ValueError, match=f'^{PARENTS}$'):
            validate_parent_industries(example_table(), empty)


def test_the_validator_rejects_an_empty_table_for_a_frame_with_parents():
    with pytest.raises(ValueError, match=f'^{PARENTS}$'):
        validate_parent_industries(from_rows([]), example_frame())


@pytest.mark.parametrize('trifd', ['T1', 'T10', 'T11'], ids=['parent', 'self-owned', 'excluded'])
def test_the_validator_rejects_a_frame_with_a_year_outside_the_window(trifd):
    shifted = example_frame().with_columns(
        pl.when(pl.col('trifd') == trifd).then(pl.lit(2025, dtype=pl.Int64))
        .otherwise(pl.col('reporting_year')).alias('reporting_year'))
    with pytest.raises(ValueError, match=OUTSIDE):
        validate_parent_industries(example_table(), shifted)


# ---- the report


def report_of(records: list[dict]) -> dict:
    frame = reduced(records)
    return parent_report(build_parent_industries(frame), frame)


EMPTY = {'count': 0, 'min': None, 'p25': None, 'median': None, 'p75': None, 'p90': None,
         'max': None, 'ge_1': 0, 'ge_2': 0, 'ge_3': 0, 'ge_5': 0, 'ge_10': 0}
PARENT_BREAKS = [name for name, (_, message) in BREAKS.items() if message == PARENTS]
NAMES = ('Acme', 'Beta', 'Core', 'Bzzz', 'Zulu', 'Dune', 'T10')


def test_the_report_gives_the_distributions_of_facilities_and_industries_per_parent():
    report = report_of(example_records())
    assert report == {
        'n_parents': 3,
        # Acme 3 (T1 is in a and in c, and counts once), Beta 1, Core 5
        'facilities_per_parent': {
            'count': 3, 'min': 1, 'p25': 1, 'median': 3, 'p75': 5, 'p90': 5, 'max': 5,
            'ge_1': 3, 'ge_2': 2, 'ge_3': 2, 'ge_5': 1, 'ge_10': 0},
        # Acme 3, Beta 1, Core 1
        'industries_per_parent': {
            'count': 3, 'min': 1, 'p25': 1, 'median': 1, 'p75': 3, 'p90': 3, 'max': 3,
            'ge_1': 3, 'ge_2': 1, 'ge_3': 1, 'ge_5': 0, 'ge_10': 0},
    }


def test_a_facility_that_changes_industry_counts_once_in_the_report():
    # T1 of P is in a in 2022 and in b in 2023: one facility and two industries
    report = report_of([form(2022, 'T1', A, 'P'), form(2023, 'T1', B, 'P')])
    assert report == {
        'n_parents': 1,
        'facilities_per_parent': {
            'count': 1, 'min': 1, 'p25': 1, 'median': 1, 'p75': 1, 'p90': 1, 'max': 1,
            'ge_1': 1, 'ge_2': 0, 'ge_3': 0, 'ge_5': 0, 'ge_10': 0},
        'industries_per_parent': {
            'count': 1, 'min': 2, 'p25': 2, 'median': 2, 'p75': 2, 'p90': 2, 'max': 2,
            'ge_1': 1, 'ge_2': 1, 'ge_3': 0, 'ge_5': 0, 'ge_10': 0},
    }


def test_a_facility_that_changes_industry_beside_another_facility_counts_once():
    # T1 is in a in 2022 and in b in 2023, and T2 is in a in 2023: two facilities and two
    # industries, where the rows of the table hold 2 facilities in a and 1 in b
    report = report_of([
        form(2022, 'T1', A, 'P'), form(2023, 'T1', B, 'P'), form(2023, 'T2', A, 'P')])
    facilities, industries = report['facilities_per_parent'], report['industries_per_parent']
    assert (facilities['count'], facilities['min'], facilities['max']) == (1, 2, 2)
    assert (industries['count'], industries['min'], industries['max']) == (1, 2, 2)


def test_a_facility_in_three_industries_counts_once_in_the_report():
    report = report_of([
        form(2022, 'T1', A, 'P'), form(2023, 'T1', B, 'P'), form(2024, 'T1', C, 'P')])
    assert report['facilities_per_parent']['max'] == 1
    assert report['industries_per_parent']['max'] == 3


def test_a_facility_in_each_year_of_one_industry_counts_once_in_the_report():
    # three facility-years of one TRIFD: one facility, one industry, and one parent
    report = report_of([form(year, 'T1', A, 'P') for year in (2022, 2023, 2024)])
    assert report['n_parents'] == 1
    assert report['facilities_per_parent'] == {
        'count': 1, 'min': 1, 'p25': 1, 'median': 1, 'p75': 1, 'p90': 1, 'max': 1,
        'ge_1': 1, 'ge_2': 0, 'ge_3': 0, 'ge_5': 0, 'ge_10': 0}
    assert report['industries_per_parent']['max'] == 1


def test_several_facilities_per_parent_are_counted_across_years_and_industries():
    # P: T1 to T4 in a (T1 in two years), so four facilities and one industry
    # Q: T5 in a and T6 in b, so two facilities and two industries
    report = report_of([
        form(2022, 'T1', A, 'P'), form(2022, 'T2', A, 'P'), form(2023, 'T1', A, 'P'),
        form(2023, 'T3', A, 'P'), form(2024, 'T4', A, 'P'),
        form(2022, 'T5', A, 'Q'), form(2023, 'T6', B, 'Q')])
    assert report == {
        'n_parents': 2,
        'facilities_per_parent': {
            'count': 2, 'min': 2, 'p25': 2, 'median': 2, 'p75': 4, 'p90': 4, 'max': 4,
            'ge_1': 2, 'ge_2': 2, 'ge_3': 1, 'ge_5': 0, 'ge_10': 0},
        'industries_per_parent': {
            'count': 2, 'min': 1, 'p25': 1, 'median': 1, 'p75': 2, 'p90': 2, 'max': 2,
            'ge_1': 2, 'ge_2': 1, 'ge_3': 0, 'ge_5': 0, 'ge_10': 0},
    }


def test_the_report_counts_parents_not_rows():
    report = report_of([
        form(2022, 'T1', A, 'Acme'), form(2022, 'T2', B, 'Acme'), form(2022, 'T3', C, 'Acme'),
        form(2023, 'T4', A, 'Beta'), form(2024, 'T5', A, 'Beta')])
    assert report['n_parents'] == 2
    assert report['facilities_per_parent']['count'] == 2
    assert report['industries_per_parent']['count'] == 2


def test_the_report_keeps_parent_names_that_differ_in_case_apart():
    report = report_of([form(2023, 'T1', A, 'ACME'), form(2023, 'T2', A, 'Acme')])
    assert report['n_parents'] == 2
    assert report['facilities_per_parent']['count'] == 2


def test_the_report_counts_industries_in_the_table_and_facilities_in_the_frame():
    # the table lacks the row of Acme in b, so Acme has two rows, and still three facilities
    table = broken('a missing row of a parent')
    report = parent_report(table, example_frame())
    assert report['n_parents'] == 3
    assert report['facilities_per_parent'] == {
        'count': 3, 'min': 1, 'p25': 1, 'median': 3, 'p75': 5, 'p90': 5, 'max': 5,
        'ge_1': 3, 'ge_2': 2, 'ge_3': 2, 'ge_5': 1, 'ge_10': 0}
    assert report['industries_per_parent'] == {
        'count': 3, 'min': 1, 'p25': 1, 'median': 1, 'p75': 2, 'p90': 2, 'max': 2,
        'ge_1': 3, 'ge_2': 1, 'ge_3': 0, 'ge_5': 0, 'ge_10': 0}


def test_an_excluded_facility_year_is_not_a_facility_of_the_report():
    # `reduce` gives an excluded row no owner key, but the report names both conditions
    frame = minimal([
        (2023, 'T1', A, 'parent:P', None), (2023, 'T2', A, 'parent:P', 'federal'),
        (2023, 'T3', B, 'parent:P', 'naics_conflict'), (2023, 'T4', A, 'facility:T4', None)])
    report = parent_report(build_parent_industries(frame), frame)
    assert report['n_parents'] == 1
    assert report['facilities_per_parent']['max'] == 1
    assert report['industries_per_parent']['max'] == 1


@pytest.mark.parametrize('records', [
    [], [form(2022, 'T1', A)], excluded('federal', 2022, 'T1', 'P')
], ids=['no rows', 'self-owned only', 'excluded only'])
def test_the_report_of_an_empty_selection_has_no_parents(records):
    assert report_of(records) == {
        'n_parents': 0, 'facilities_per_parent': EMPTY, 'industries_per_parent': EMPTY}


@pytest.mark.parametrize('name', PARENT_BREAKS)
def test_the_report_rejects_a_table_whose_parents_differ_from_the_frame(name):
    with pytest.raises(ValueError, match=f'^{PARENTS}$') as failure:
        parent_report(broken(name), example_frame())
    assert not [value for value in NAMES if value in str(failure.value)]


@pytest.mark.parametrize('records', [
    [], [form(2022, 'T1', A)], [form(2022, 'T1', A, 'Acme')]
], ids=['no rows', 'self-owned only', 'a part of the parents'])
def test_the_report_rejects_a_frame_whose_parents_differ_from_the_table(records):
    with pytest.raises(ValueError, match=f'^{PARENTS}$') as failure:
        parent_report(example_table(), reduced(records))
    assert not [value for value in NAMES if value in str(failure.value)]


def test_the_report_rejects_an_empty_table_for_a_frame_with_parents():
    with pytest.raises(ValueError, match=f'^{PARENTS}$'):
        parent_report(from_rows([]), example_frame())


def test_the_report_is_plain_json_of_counts_only():
    report = report_of(example_records())
    text = json.dumps(report, sort_keys=True)
    assert json.loads(text) == report
    assert set(report) == {'n_parents', 'facilities_per_parent', 'industries_per_parent'}
    assert not any(name in text for name in ('Acme', 'Beta', 'Core'))

    def leaves(value):
        if isinstance(value, dict):
            assert all(type(key) is str for key in value)
            for item in value.values():
                yield from leaves(item)
        else:
            yield value

    assert all(leaf is None or type(leaf) is int for leaf in leaves(report))
