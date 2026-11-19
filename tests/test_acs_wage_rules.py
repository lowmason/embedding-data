'''Rules that derive the ACS wage microdata rows and flags from a Stage 8 core table.'''

import json
import math

import polars as pl
import pytest
from acs_wage_fixtures import (
    CARRIED_COLUMNS,
    COMMON_NODE,
    CORE_SCHEMA,
    DELIVERED_NODE,
    DROPPED,
    EXCLUDED_COLUMNS,
    Q_COLUMNS,
    REPLICATES,
    core_frame,
    core_row,
    with_excluded_columns,
)
from hypothesis import given, settings
from hypothesis import strategies as st

from embedding_data import acs_wage_rules as rules
from embedding_data.acs_wage_rules import HEADLINE_ALLOCATION, RULE_COLUMNS

# The spec writes these lists out. The pin tests compare them with the module, so a change in
# the module cannot also change what the parametrized tests below cover.
SPEC_HEADLINE_Q = Q_COLUMNS[:-1]
SPEC_RULE_COLUMNS = (
    'source_row',
    'YEAR',
    'STATEFIP',
    'INCWAGE',
    'INCWAGE_CPIU_2010',
    'UHRSWORK',
    'WKSWORK2',
    'CLASSWKRD',
    'INDNAICS',
    'industry_canonical_common_node_id',
    'industry_native_node_id',
    *Q_COLUMNS,
)
SPEC_NEW = (
    'log_wage_2010',
    'industry_node_code',
    'industry_node_level',
    'industry_delivered_node_code',
    'flag_industry_shared_node',
    'flag_any_allocated',
    'flag_incwage_topcoded',
    'flag_full_time_full_year',
    'flag_wage_salary',
    'flag_headline',
)
SPEC_FLAGS = tuple(name for name in SPEC_NEW if name.startswith('flag_'))
SPEC_OUTPUT_GROUPS = (
    ('source_parquet_sha256', 'source_row', 'YEAR', 'acs_sample_id'),
    ('PERWT', *REPLICATES),
    ('INCWAGE', 'INCWAGE_CPIU_2010', 'log_wage_2010'),
    ('UHRSWORK', 'WKSWORK2', 'CLASSWKR', 'CLASSWKRD'),
    ('SEX', 'AGE', 'EDUC', 'EDUCD', 'DEGFIELD', 'DEGFIELDD', 'STATEFIP', 'REGION', 'GQ'),
    (
        'OCC',
        'OCCSOC',
        'occupation_canonical_common_node_id',
        'occupation_aggregation_type',
    ),
    (
        'IND',
        'INDNAICS',
        'industry_canonical_common_node_id',
        'industry_aggregation_type',
        'industry_canonical_finest_candidates',
        'industry_native_node_id',
        'industry_node_code',
        'industry_node_level',
        'industry_delivered_node_code',
        'flag_industry_shared_node',
    ),
    (*Q_COLUMNS, 'flag_any_allocated'),
    ('flag_incwage_topcoded',),
    ('flag_full_time_full_year', 'flag_wage_salary', 'flag_headline'),
)
OTHER_COMMON = 'naics:2022:national_industry:623210'
OTHER_DELIVERED = 'naics:2022:industry_group:6232'
SHARED_COMMON = 'naics:2022:industry_group:5614'
FIXED_MESSAGES = (
    'core table lacks a carried column',
    'null in a rule column',
    'wage value out of range',
    'source rows not strictly increasing',
    'category maps to more than one node',
    'unparseable NAICS 2022 node ID',
)


def persons_of(*rows) -> pl.DataFrame:
    return rules.wage_persons(core_frame(list(rows))).collect()


def one(**overrides) -> dict:
    return persons_of(core_row(**overrides)).row(0, named=True)


def flags_by(rows: list[dict], key: str, flag: str) -> dict:
    persons = rules.wage_persons(core_frame(rows)).collect()
    return dict(zip(persons[key].to_list(), persons[flag].to_list(), strict=True))


# --- Columns -----------------------------------------------------------------------------


def test_output_columns_follow_the_spec_order():
    assert len(rules.CARRIED) == 120 and len(rules.OUTPUT_COLUMNS) == 130
    assert rules.OUTPUT_COLUMNS[:5] == (
        'source_parquet_sha256',
        'source_row',
        'YEAR',
        'acs_sample_id',
        'PERWT',
    )
    assert rules.OUTPUT_COLUMNS[-3:] == (
        'flag_full_time_full_year',
        'flag_wage_salary',
        'flag_headline',
    )
    assert set(rules.OUTPUT_COLUMNS) == set(rules.CARRIED) | set(rules.NEW)


def test_output_columns_are_the_spec_table_group_by_group():
    expected = tuple(name for group in SPEC_OUTPUT_GROUPS for name in group)
    assert rules.OUTPUT_COLUMNS == expected
    assert len(set(rules.OUTPUT_COLUMNS)) == 130
    assert rules.CARRIED == tuple(name for name in expected if name not in SPEC_NEW)


def test_new_columns_and_their_types():
    assert tuple(rules.NEW) == SPEC_NEW
    assert rules.NEW['log_wage_2010'] == pl.Float64
    for name in ('industry_node_code', 'industry_node_level', 'industry_delivered_node_code'):
        assert rules.NEW[name] == pl.String
    assert all(rules.NEW[name] == pl.Boolean for name in SPEC_FLAGS)
    assert len(SPEC_FLAGS) == 6


def test_the_fixture_schema_carries_exactly_the_delivered_columns():
    assert CARRIED_COLUMNS == tuple(name for name in CORE_SCHEMA if name not in DROPPED)
    assert set(CARRIED_COLUMNS) == set(rules.CARRIED)
    assert len(CORE_SCHEMA) == 122


def test_constants_follow_the_spec():
    assert (rules.CONTRACT, rules.TABLE) == ('acs-wage-microdata-v1', 'acs_wage_persons')
    assert (rules.FULL_TIME_HOURS, rules.FULL_YEAR_WKSWORK2) == (35, 6)
    assert rules.WAGE_SALARY_CLASSWKRD == (22, 23, 25, 27, 28)
    assert rules.INCWAGE_CODES == (999998, 999999)
    assert rules.HEADLINE_ALLOCATION == SPEC_HEADLINE_Q
    assert len(rules.HEADLINE_ALLOCATION) == 9 and 'QDEGFIELD' not in rules.HEADLINE_ALLOCATION
    assert rules.ALLOCATION == Q_COLUMNS and len(rules.ALLOCATION) == 10
    assert rules.RULE_COLUMNS == SPEC_RULE_COLUMNS


def test_ddi_labels_confirm_the_rule_codes():
    assert rules.DDI_LABELS['WKSWORK2'] == {'6': '50-52 weeks'}
    assert str(rules.FULL_YEAR_WKSWORK2) in rules.DDI_LABELS['WKSWORK2']
    labels = rules.DDI_LABELS['CLASSWKRD']
    assert set(labels) == {'13', '14', '22', '23', '25', '27', '28', '29'}
    assert {str(code) for code in rules.WAGE_SALARY_CLASSWKRD} <= set(labels)
    assert labels['22'] == 'Wage/salary, private' and labels['29'] == 'Unpaid family worker'


def test_rules_describe_each_new_column_and_the_rows():
    assert set(rules.RULES) == {'rows', *SPEC_NEW}
    assert all(isinstance(text, str) and text.endswith('.') for text in rules.RULES.values())


# --- Rows and types ----------------------------------------------------------------------


def test_keeps_positive_wage_rows_in_source_order_and_drops_other_columns():
    # INCWAGE 0, 7, -1, 5 -> rows with source_row 1 and 3 remain, in that order. The two
    # dropped rows carry values that would be refused on an earner.
    persons = persons_of(
        core_row(INCWAGE=0, INCWAGE_CPIU_2010=0.0, UHRSWORK=None),
        core_row(INCWAGE=7),
        core_row(INCWAGE=-1, INCWAGE_CPIU_2010=-1.0, industry_native_node_id='bad'),
        core_row(INCWAGE=5),
    )
    assert persons['source_row'].to_list() == [1, 3]
    assert persons['INCWAGE'].to_list() == [7, 5]
    assert persons.columns == list(rules.OUTPUT_COLUMNS)  # SERIAL and PUMA gone
    assert 'SERIAL' not in persons.columns and 'PUMA' not in persons.columns


def test_earners_selects_the_carried_columns_in_order_whatever_the_input_order():
    frame = core_frame([core_row(), core_row(INCWAGE=0)])
    shuffled = frame.select(reversed(CORE_SCHEMA))
    result = rules.earners(shuffled).collect()
    assert result.columns == list(rules.CARRIED)
    assert result.height == 1


def test_the_plans_stay_lazy_over_a_parquet_scan(tmp_path):
    # Both functions return a LazyFrame. A plan that collected the earners and made them lazy
    # again would still be a LazyFrame, so the type alone proves nothing. In production it would
    # hold every earner row and all carried columns in memory. The plan text shows it: the scan
    # must still be in it.
    rows = [core_row(), core_row(INCWAGE=0), core_row(INCWAGE=7)]
    path = tmp_path / 'core.parquet'
    core_frame(rows).collect().write_parquet(path)
    scan = pl.scan_parquet(path)
    assert isinstance(rules.earners(scan), pl.LazyFrame)
    assert isinstance(rules.wage_persons(scan), pl.LazyFrame)
    assert 'Parquet SCAN' in rules.earners(scan).explain()
    assert 'Parquet SCAN' in rules.wage_persons(scan).explain()
    assert rules.wage_persons(scan).collect().equals(persons_of(*rows))


def narrowed_core_frame() -> pl.LazyFrame:
    '''Return a core frame whose carried columns all differ from the Stage 8 types.'''
    casts = {}
    for name, dtype in CORE_SCHEMA.items():
        if name in REPLICATES:
            casts[name] = pl.Float64
        elif name == 'PERWT':
            casts[name] = pl.Float32
        elif name == 'source_row':
            casts[name] = pl.UInt32
        elif dtype == pl.Int64:
            casts[name] = pl.Int32
    return core_frame([core_row(), core_row(INCWAGE=7)]).cast(casts).with_columns(
        pl.col('REPWTP3') + 0.5
    )


def test_every_carried_column_keeps_the_type_and_value_of_the_input():
    frame = narrowed_core_frame()
    expected = frame.collect_schema()
    persons = rules.wage_persons(frame).collect()
    for name in CARRIED_COLUMNS:
        assert persons.schema[name] == expected[name], name
    assert persons['REPWTP3'].to_list() == [93.5, 93.5]
    assert persons['source_row'].to_list() == [0, 1]


def test_carried_types_follow_the_input_schema():
    # an input with REPWTP37 as Float64 and OCC as String keeps those types
    frame = core_frame([core_row()]).with_columns(
        pl.col('REPWTP37').cast(pl.Float64), pl.col('OCC').cast(pl.String)
    )
    schema = rules.wage_persons(frame).collect_schema()
    assert schema['REPWTP37'] == pl.Float64 and schema['OCC'] == pl.String
    assert schema['log_wage_2010'] == pl.Float64 and schema['flag_headline'] == pl.Boolean
    assert schema['source_row'] == pl.UInt64 and schema['PERWT'] == pl.Float64
    assert schema['industry_canonical_finest_candidates'] == pl.List(pl.String)


def test_output_types_are_the_new_types():
    schema = rules.wage_persons(core_frame([core_row()])).collect_schema()
    assert dict(schema) == {
        name: rules.NEW.get(name, CORE_SCHEMA.get(name)) for name in rules.OUTPUT_COLUMNS
    }


def test_carried_values_pass_through_unchanged():
    row = one(OCC=1234, industry_canonical_finest_candidates=['623110', '623210'])
    source = core_row(OCC=1234, industry_canonical_finest_candidates=['623110', '623210'])
    for name in rules.CARRIED:
        if name != 'source_row':
            assert row[name] == source[name]
    assert row['source_row'] == 0


def test_nulls_in_other_carried_columns_pass_through():
    row = one(DEGFIELD=None, OCC=None, REPWTP3=None, GQ=None)
    assert row['DEGFIELD'] is None and row['OCC'] is None and row['REPWTP3'] is None
    assert row['flag_headline'] is True


def test_extra_columns_are_not_required():
    frame = core_frame([core_row()]).drop(*DROPPED)
    assert rules.wage_persons(frame).collect().columns == list(rules.OUTPUT_COLUMNS)


def test_identifier_and_geography_columns_never_reach_the_file():
    # SERIAL and PUMA are in the fixture schema. This core also carries the other household
    # identifiers, the county, the workplace and migration geography, and the design variables.
    frame = with_excluded_columns(core_frame([core_row(), core_row(INCWAGE=7)]))
    assert set(EXCLUDED_COLUMNS) <= set(frame.collect_schema().names())
    persons = rules.wage_persons(frame).collect()
    assert persons.columns == list(rules.OUTPUT_COLUMNS)
    assert not set(EXCLUDED_COLUMNS) & set(persons.columns)
    assert not set(EXCLUDED_COLUMNS) & set(rules.OUTPUT_COLUMNS)
    assert not set(EXCLUDED_COLUMNS) & set(rules.earners(frame).collect_schema().names())


# --- Allocation --------------------------------------------------------------------------


def test_rows_that_are_not_headline_stay_in_the_file():
    # One row leaves the headline for each reason, and one row stays. The file keeps all of them,
    # in source order, so that a panel can report what each exclusion does.
    rows = [
        core_row(),
        core_row(QIND=4),
        core_row(UHRSWORK=20),
        core_row(CLASSWKRD=13),
        core_row(
            INDNAICS='X',
            industry_canonical_common_node_id=OTHER_COMMON,
            industry_native_node_id=OTHER_DELIVERED,
        ),
        core_row(
            INDNAICS='Y',
            industry_canonical_common_node_id=OTHER_COMMON,
            industry_native_node_id='naics:2022:industry:62321',
        ),
    ]
    persons = rules.wage_persons(core_frame(rows)).collect()
    assert persons['source_row'].to_list() == [0, 1, 2, 3, 4, 5]
    assert persons['flag_headline'].to_list() == [True, False, False, False, False, False]


def test_a_clean_row_is_a_headline_row():
    row = one()
    assert row['flag_any_allocated'] is False and row['flag_headline'] is True
    assert row['flag_full_time_full_year'] is True and row['flag_wage_salary'] is True
    assert row['flag_industry_shared_node'] is False and row['flag_incwage_topcoded'] is True


@pytest.mark.parametrize('column', HEADLINE_ALLOCATION)
def test_each_headline_allocation_column_leaves_the_headline(column):
    row = rules.wage_persons(core_frame([core_row(**{column: 4})])).collect().row(0, named=True)
    assert row['flag_any_allocated'] is True and row['flag_headline'] is False


@pytest.mark.parametrize('column', SPEC_HEADLINE_Q)
def test_each_spec_headline_column_leaves_the_headline(column):
    row = one(**{column: 4})
    assert row['flag_any_allocated'] is True and row['flag_headline'] is False


def test_qdegfield_alone_keeps_the_headline():
    row = one(QDEGFIELD=4)
    assert row['flag_any_allocated'] is True and row['flag_headline'] is True


@pytest.mark.parametrize('value', [1, 2, 3, 4, 5, 6, 7, 8])
def test_any_nonzero_q_value_is_allocated(value):
    assert one(QIND=value)['flag_any_allocated'] is True
    assert one(QIND=value)['flag_headline'] is False
    assert one(QDEGFIELD=value)['flag_any_allocated'] is True


# --- Full time, full year, and employee class ----------------------------------------------


@pytest.mark.parametrize(
    ('hours', 'weeks', 'expected'), [(34, 6, False), (35, 6, True), (35, 5, False)]
)
def test_full_time_full_year_boundaries(hours, weeks, expected):
    row = one(UHRSWORK=hours, WKSWORK2=weeks)
    assert row['flag_full_time_full_year'] is expected
    assert row['flag_headline'] is expected


@pytest.mark.parametrize(
    ('hours', 'weeks', 'expected'),
    [(36, 6, True), (99, 6, True), (0, 6, False), (35, 0, False), (35, 7, False), (34, 5, False)],
)
def test_full_time_full_year_needs_both_parts(hours, weeks, expected):
    assert one(UHRSWORK=hours, WKSWORK2=weeks)['flag_full_time_full_year'] is expected


@pytest.mark.parametrize(
    ('classwkrd', 'expected'),
    [
        (13, False),
        (14, False),
        (22, True),
        (23, True),
        (25, True),
        (27, True),
        (28, True),
        (29, False),
    ],
)
def test_wage_salary_classes(classwkrd, expected):
    row = one(CLASSWKRD=classwkrd)
    assert row['flag_wage_salary'] is expected
    assert row['flag_headline'] is expected


@pytest.mark.parametrize('classwkrd', [0, 21, 24, 26, 99])
def test_other_class_codes_are_not_wage_salary(classwkrd):
    assert one(CLASSWKRD=classwkrd)['flag_wage_salary'] is False


def test_class_of_worker_reads_the_detailed_code_not_the_general_one():
    # An unpaid family worker (29) sits under CLASSWKR 2 with the employees.
    row = one(CLASSWKR=2, CLASSWKRD=29)
    assert row['flag_wage_salary'] is False
    assert one(CLASSWKR=1, CLASSWKRD=22)['flag_wage_salary'] is True


# --- Shared nodes ------------------------------------------------------------------------


def test_shared_node_spans_years():
    # category 'A' only in 2023 and 'B' only in 2024, both on one common node;
    # category 'C' on its own node in both years
    rows = [
        core_row(INDNAICS='A', YEAR=2023, industry_native_node_id=DELIVERED_NODE),
        core_row(
            INDNAICS='B',
            YEAR=2024,
            industry_native_node_id='naics:2022:industry:62311',
        ),
        core_row(
            INDNAICS='C',
            YEAR=2023,
            industry_canonical_common_node_id=OTHER_COMMON,
            industry_native_node_id=OTHER_DELIVERED,
        ),
        core_row(
            INDNAICS='C',
            YEAR=2024,
            industry_canonical_common_node_id=OTHER_COMMON,
            industry_native_node_id=OTHER_DELIVERED,
        ),
    ]
    assert flags_by(rows, 'INDNAICS', 'flag_industry_shared_node') == {
        'A': True,
        'B': True,
        'C': False,
    }


def test_a_category_does_not_share_a_node_with_itself():
    rows = [core_row(), core_row(), core_row(YEAR=2024)]
    persons = rules.wage_persons(core_frame(rows)).collect()
    assert persons['flag_industry_shared_node'].to_list() == [False, False, False]


def test_shared_node_removes_both_categories_from_the_headline():
    rows = [
        core_row(INDNAICS='A', industry_native_node_id=DELIVERED_NODE),
        core_row(INDNAICS='B', industry_native_node_id='naics:2022:industry:62311'),
        core_row(INDNAICS='C', industry_canonical_common_node_id=OTHER_COMMON,
                 industry_native_node_id=OTHER_DELIVERED),
    ]
    assert flags_by(rows, 'INDNAICS', 'flag_headline') == {'A': False, 'B': False, 'C': True}


def test_shared_node_reads_only_the_rows_of_the_file():
    # Category 'B' has the same common node, but its only row has no wage, so the file
    # does not hold it.
    rows = [
        core_row(INDNAICS='A'),
        core_row(INDNAICS='B', INCWAGE=0, industry_native_node_id='naics:2022:industry:62311'),
    ]
    persons = rules.wage_persons(core_frame(rows)).collect()
    assert persons['INDNAICS'].to_list() == ['A']
    assert persons['flag_industry_shared_node'].to_list() == [False]


def test_three_categories_on_one_node_are_all_shared():
    rows = [
        core_row(INDNAICS=name, industry_native_node_id=f'naics:2022:industry:6231{n}')
        for n, name in enumerate('ABC', start=1)
    ]
    persons = rules.wage_persons(core_frame(rows)).collect()
    assert persons['flag_industry_shared_node'].to_list() == [True, True, True]


# --- Top code ----------------------------------------------------------------------------


def test_topcode_flags_every_row_at_its_state_year_maximum():
    # state 1, 2023: 900, 900, 500 -> True, True, False; state 1, 2024: 500 -> True;
    # state 2, 2023: 700 -> True. The rows interleave the groups.
    rows = [
        core_row(STATEFIP=1, YEAR=2023, INCWAGE=900),
        core_row(STATEFIP=1, YEAR=2023, INCWAGE=500),
        core_row(STATEFIP=2, YEAR=2023, INCWAGE=700),
        core_row(STATEFIP=1, YEAR=2024, INCWAGE=500),
        core_row(STATEFIP=1, YEAR=2023, INCWAGE=900),
    ]
    persons = rules.wage_persons(core_frame(rows)).collect()
    assert persons['source_row'].to_list() == [0, 1, 2, 3, 4]
    assert persons['flag_incwage_topcoded'].to_list() == [True, False, True, True, True]


def test_topcode_flags_only_the_exact_maximum_not_a_wage_near_it():
    rows = [core_row(INCWAGE=900), core_row(INCWAGE=899), core_row(INCWAGE=850)]
    persons = rules.wage_persons(core_frame(rows)).collect()
    assert persons['flag_incwage_topcoded'].to_list() == [True, False, False]


def test_topcode_is_not_a_headline_rule():
    rows = [core_row(INCWAGE=900), core_row(INCWAGE=500)]
    persons = rules.wage_persons(core_frame(rows)).collect()
    assert persons['flag_incwage_topcoded'].to_list() == [True, False]
    assert persons['flag_headline'].to_list() == [True, True]


def test_topcode_compares_the_delivered_wage_not_the_deflated_one():
    rows = [
        core_row(INCWAGE=900, INCWAGE_CPIU_2010=100.0),
        core_row(INCWAGE=500, INCWAGE_CPIU_2010=300.0),
    ]
    persons = rules.wage_persons(core_frame(rows)).collect()
    assert persons['flag_incwage_topcoded'].to_list() == [True, False]


# --- Derived columns ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ('common', 'delivered', 'expected'),
    [
        ('naics:2022:sector:31-33', 'naics:2022:sector:31-33', ('31-33', 'sector', '31-33')),
        (
            'naics:2022:national_industry:623110',
            'naics:2022:industry_group:6231',
            ('623110', 'national_industry', '6231'),
        ),
        (
            'naics:2022:subsector:722',
            'naics:2022:industry:72251',
            ('722', 'subsector', '72251'),
        ),
        (
            'naics:2022:industry_group:5614',
            'naics:2022:sector:56',
            ('5614', 'industry_group', '56'),
        ),
        (
            'naics:2022:industry:56141',
            'naics:2022:sector:44-45',
            ('56141', 'industry', '44-45'),
        ),
    ],
)
def test_node_parts_split_the_common_and_delivered_ids(common, delivered, expected):
    row = one(industry_canonical_common_node_id=common, industry_native_node_id=delivered)
    assert (
        row['industry_node_code'],
        row['industry_node_level'],
        row['industry_delivered_node_code'],
    ) == expected


def test_node_parts_split_the_default_row():
    row = one()
    assert row['industry_canonical_common_node_id'] == COMMON_NODE
    assert row['industry_native_node_id'] == DELIVERED_NODE
    assert (
        row['industry_node_code'],
        row['industry_node_level'],
        row['industry_delivered_node_code'],
    ) == ('623110', 'national_industry', '6231')


def test_log_wage_is_the_natural_log():
    assert one(INCWAGE_CPIU_2010=math.e)['log_wage_2010'] == pytest.approx(1.0)
    assert one(INCWAGE_CPIU_2010=1.0)['log_wage_2010'] == pytest.approx(0.0)
    assert one(INCWAGE_CPIU_2010=100.0)['log_wage_2010'] == pytest.approx(math.log(100.0))
    assert one(INCWAGE_CPIU_2010=0.5)['log_wage_2010'] == pytest.approx(math.log(0.5))


def test_log_wage_reads_the_deflated_wage_not_the_delivered_one():
    row = one(INCWAGE=1000, INCWAGE_CPIU_2010=math.e)
    assert row['log_wage_2010'] == pytest.approx(1.0)


# --- Refusals ----------------------------------------------------------------------------


@pytest.mark.parametrize('column', RULE_COLUMNS)
def test_refuses_a_null_rule_input(column):
    with pytest.raises(ValueError, match='null in a rule column'):
        rules.wage_persons(core_frame([core_row(**{column: None})])).collect()


@pytest.mark.parametrize('column', SPEC_RULE_COLUMNS)
def test_refuses_a_null_in_each_spec_rule_column(column):
    with pytest.raises(ValueError, match='null in a rule column'):
        rules.wage_persons(core_frame([core_row(), core_row(**{column: None})])).collect()


@pytest.mark.parametrize(
    'changes',
    [
        {'INCWAGE_CPIU_2010': 0.0},
        {'INCWAGE_CPIU_2010': -1.0},
        {'INCWAGE': 999998},
        {'INCWAGE': 999999},
    ],
)
def test_refuses_bad_wage_values(changes):
    with pytest.raises(ValueError, match='wage value'):
        rules.wage_persons(core_frame([core_row(**changes)])).collect()


@pytest.mark.parametrize('deflated', [float('nan'), float('inf'), float('-inf'), -1e-9])
def test_refuses_a_deflated_wage_that_has_no_finite_log(deflated):
    with pytest.raises(ValueError, match='wage value out of range'):
        rules.wage_persons(core_frame([core_row(INCWAGE_CPIU_2010=deflated)])).collect()


def test_a_bad_wage_on_a_later_row_is_still_refused():
    rows = [core_row(), core_row(), core_row(INCWAGE=999999)]
    with pytest.raises(ValueError, match='wage value out of range'):
        rules.wage_persons(core_frame(rows)).collect()


@pytest.mark.parametrize(
    'changes',
    [
        {'INCWAGE': 999997},
        {'INCWAGE': 1_000_000},
        {'INCWAGE': 1, 'INCWAGE_CPIU_2010': 1e-9},
    ],
)
def test_accepts_wage_values_beside_the_refused_ones(changes):
    row = one(**changes)
    assert math.isfinite(row['log_wage_2010'])


def test_refuses_a_category_on_two_nodes():
    rows = [
        core_row(INDNAICS='A'),
        core_row(
            INDNAICS='A',
            industry_canonical_common_node_id=OTHER_COMMON,
            industry_native_node_id=DELIVERED_NODE,
        ),
    ]
    with pytest.raises(ValueError, match='more than one node'):
        rules.wage_persons(core_frame(rows)).collect()


@pytest.mark.parametrize(
    'changes',
    [
        {'industry_canonical_common_node_id': OTHER_COMMON},
        {'industry_native_node_id': OTHER_DELIVERED},
        {
            'industry_canonical_common_node_id': OTHER_COMMON,
            'industry_native_node_id': OTHER_DELIVERED,
        },
        {'YEAR': 2024, 'industry_native_node_id': OTHER_DELIVERED},
    ],
)
def test_refuses_a_category_with_two_common_or_two_delivered_nodes(changes):
    rows = [core_row(INDNAICS='A'), core_row(INDNAICS='A', **changes)]
    with pytest.raises(ValueError, match='category maps to more than one node'):
        rules.wage_persons(core_frame(rows)).collect()


def test_two_categories_may_hold_different_delivered_nodes_on_one_common_node():
    rows = [
        core_row(INDNAICS='A', industry_native_node_id=DELIVERED_NODE),
        core_row(INDNAICS='B', industry_native_node_id='naics:2022:industry:62311'),
    ]
    assert rules.wage_persons(core_frame(rows)).collect().height == 2


BAD_NODE_IDS = [
    'naics:2017:industry:11111',
    'soc:2018:detailed:11-1021',
    'naics:2022:industry:1111100',
    'naics:2022:industry:1',
    'naics:2022:unknown_level:11',
    'naics:2022:sector:11-3',
    'naics:2022:sector:11x',
    'xnaics:2022:sector:11',
    'naics:2022:sector:11\n',
    'NAICS:2022:sector:11',
    '',
]


@pytest.mark.parametrize('column', ['industry_canonical_common_node_id',
                                    'industry_native_node_id'])
@pytest.mark.parametrize('node_id', BAD_NODE_IDS)
def test_refuses_an_unparseable_node_id(column, node_id):
    with pytest.raises(ValueError, match='unparseable NAICS 2022 node ID'):
        rules.wage_persons(core_frame([core_row(**{column: node_id})])).collect()


@pytest.mark.parametrize(
    'node_id',
    ['naics:2022:sector:31-33', 'naics:2022:industry:11111', 'naics:2022:national_industry:111110',
     'naics:2022:sector:11', 'naics:2022:subsector:111', 'naics:2022:industry_group:1111'],
)
def test_accepts_every_level_and_width_the_pattern_names(node_id):
    row = one(industry_canonical_common_node_id=node_id, industry_native_node_id=node_id)
    assert row['industry_node_code'] == node_id.rsplit(':', 1)[1]


def test_refuses_source_rows_out_of_order():
    rows = [core_row(source_row=3), core_row(source_row=1)]
    with pytest.raises(ValueError, match='source rows'):
        rules.wage_persons(core_frame(rows)).collect()


def test_refuses_a_repeated_source_row():
    rows = [core_row(source_row=1), core_row(source_row=1)]
    with pytest.raises(ValueError, match='source rows not strictly increasing'):
        rules.wage_persons(core_frame(rows)).collect()


def test_accepts_increasing_source_rows_with_gaps():
    rows = [core_row(source_row=0), core_row(source_row=5), core_row(source_row=2**40)]
    assert persons_of(*rows)['source_row'].to_list() == [0, 5, 2**40]


def test_the_order_check_holds_for_the_largest_source_rows():
    top = 2**64 - 1
    rows = [core_row(source_row=top - 1), core_row(source_row=top)]
    assert persons_of(*rows).height == 2
    with pytest.raises(ValueError, match='source rows'):
        persons_of(core_row(source_row=top), core_row(source_row=0))


def test_source_order_is_checked_among_earners_only():
    # source_row 2 has no wage, so it is not in the file and does not break the order.
    rows = [core_row(source_row=1), core_row(source_row=0, INCWAGE=0), core_row(source_row=2)]
    assert persons_of(*rows)['source_row'].to_list() == [1, 2]


@pytest.mark.parametrize('column', CARRIED_COLUMNS)
def test_refuses_a_missing_carried_column(column):
    frame = core_frame([core_row()]).drop(column)
    with pytest.raises(ValueError, match='lacks a carried column'):
        rules.wage_persons(frame).collect()


def test_earners_refuses_a_missing_carried_column_when_it_is_called():
    with pytest.raises(ValueError, match='lacks a carried column'):
        rules.earners(core_frame([core_row()]).drop('QDEGFIELD'))


def test_every_refusal_uses_a_fixed_message_with_no_data_value():
    secret = 'naics:2017:industry:99999'
    with pytest.raises(ValueError) as caught:
        persons_of(core_row(industry_native_node_id=secret, INDNAICS='SECRET-CATEGORY'))
    assert str(caught.value) in FIXED_MESSAGES
    assert secret not in str(caught.value) and 'SECRET' not in str(caught.value)
    with pytest.raises(ValueError) as caught:
        persons_of(core_row(INCWAGE=999999))
    assert str(caught.value) == 'wage value out of range'


def test_check_inputs_accepts_clean_earners_and_returns_nothing():
    earners = rules.earners(core_frame([core_row(), core_row(YEAR=2024)]))
    assert rules.check_inputs(earners) is None


def test_check_inputs_refuses_before_wage_persons_builds_a_plan():
    frame = core_frame([core_row(INCWAGE=999998)])
    with pytest.raises(ValueError, match='wage value out of range'):
        rules.check_inputs(rules.earners(frame))
    with pytest.raises(ValueError, match='wage value out of range'):
        rules.wage_persons(frame)


# --- Report ------------------------------------------------------------------------------

K = {
    'INDNAICS': 'K',
    'industry_canonical_common_node_id': COMMON_NODE,
    'industry_native_node_id': DELIVERED_NODE,
}
P = {
    'INDNAICS': 'P',
    'industry_canonical_common_node_id': SHARED_COMMON,
    'industry_native_node_id': SHARED_COMMON,
}
Q = {
    'INDNAICS': 'Q',
    'industry_canonical_common_node_id': SHARED_COMMON,
    'industry_native_node_id': 'naics:2022:industry:56141',
}
S = {
    'INDNAICS': 'S',
    'industry_canonical_common_node_id': 'naics:2022:sector:31-33',
    'industry_native_node_id': 'naics:2022:sector:31-33',
}
T = {
    'INDNAICS': 'T',
    'industry_canonical_common_node_id': 'naics:2022:subsector:722',
    'industry_native_node_id': 'naics:2022:subsector:722',
}


def funnel_rows() -> list[dict]:
    '''Return rows that leave the funnel one step at a time, in both years.'''
    rows = []
    for year in (2023, 2024):
        top = 90000 if year == 2023 else 80000
        rows += [
            core_row(YEAR=year, INCWAGE=top, **K),  # stays in the headline
            core_row(YEAR=year, QIND=4, **K),  # leaves at allocation
            core_row(YEAR=year, UHRSWORK=30, **K),  # leaves at full time, full year
            core_row(YEAR=year, CLASSWKRD=13, **K),  # leaves at wage and salary
            core_row(YEAR=year, **(P if year == 2023 else Q)),  # leaves at the shared node
            core_row(YEAR=year, QDEGFIELD=4, **S),  # allocated in field of degree only
        ]
    rows.append(core_row(YEAR=2024, INCWAGE=80000, **T))  # a second 2024 headline category
    return rows


def test_summarize_counts_the_funnel_flags_and_categories():
    report = rules.summarize(rules.wage_persons(core_frame(funnel_rows())))
    assert report == {
        'contract': 'acs-wage-microdata-v1',
        'rows': {'total': 13, 'by_year': {'2023': 6, '2024': 7}},
        'funnel': [
            {'step': 'earners', 'total': 13, 'by_year': {'2023': 6, '2024': 7}},
            {'step': 'no_headline_allocation', 'total': 11, 'by_year': {'2023': 5, '2024': 6}},
            {'step': 'full_time_full_year', 'total': 9, 'by_year': {'2023': 4, '2024': 5}},
            {'step': 'wage_salary', 'total': 7, 'by_year': {'2023': 3, '2024': 4}},
            {'step': 'headline', 'total': 5, 'by_year': {'2023': 2, '2024': 3}},
        ],
        'flags': {
            'flag_industry_shared_node': {'total': 2, 'by_year': {'2023': 1, '2024': 1}},
            'flag_any_allocated': {'total': 4, 'by_year': {'2023': 2, '2024': 2}},
            'flag_incwage_topcoded': {'total': 3, 'by_year': {'2023': 1, '2024': 2}},
            'flag_full_time_full_year': {'total': 11, 'by_year': {'2023': 5, '2024': 6}},
            'flag_wage_salary': {'total': 11, 'by_year': {'2023': 5, '2024': 6}},
            'flag_headline': {'total': 5, 'by_year': {'2023': 2, '2024': 3}},
        },
        'categories': [
            {'INDNAICS': 'K', 'YEAR': 2023, 'rows': 4, 'headline_rows': 1},
            {'INDNAICS': 'K', 'YEAR': 2024, 'rows': 4, 'headline_rows': 1},
            {'INDNAICS': 'P', 'YEAR': 2023, 'rows': 1, 'headline_rows': 0},
            {'INDNAICS': 'Q', 'YEAR': 2024, 'rows': 1, 'headline_rows': 0},
            {'INDNAICS': 'S', 'YEAR': 2023, 'rows': 1, 'headline_rows': 1},
            {'INDNAICS': 'S', 'YEAR': 2024, 'rows': 1, 'headline_rows': 1},
            {'INDNAICS': 'T', 'YEAR': 2024, 'rows': 1, 'headline_rows': 1},
        ],
        'headline_categories': {'2023': 2, '2024': 3},
        'shared_nodes': {'categories': 2, 'nodes': 1},
        'node_levels': {
            'industry_group': {'categories': 2, 'headline_rows': 0},
            'national_industry': {'categories': 1, 'headline_rows': 2},
            'sector': {'categories': 1, 'headline_rows': 2},
            'subsector': {'categories': 1, 'headline_rows': 1},
        },
    }


def test_summarize_counts_categories_and_nodes_not_rows():
    # Category K has two headline rows. Shared categories P, Q, U and V hold five rows between
    # them, on two nodes. A count of rows would give a different number each time.
    u = {
        'INDNAICS': 'U',
        'industry_canonical_common_node_id': T['industry_canonical_common_node_id'],
        'industry_native_node_id': 'naics:2022:subsector:722',
    }
    v = u | {'INDNAICS': 'V', 'industry_native_node_id': 'naics:2022:industry:72251'}
    rows = [core_row(**K), core_row(**K), core_row(**S)]
    rows += [core_row(**P), core_row(**P), core_row(**Q), core_row(**u), core_row(**v)]
    report = rules.summarize(rules.wage_persons(core_frame(rows)))
    assert report['headline_categories'] == {'2023': 2}
    assert report['shared_nodes'] == {'categories': 4, 'nodes': 2}
    assert report['node_levels'] == {
        'industry_group': {'categories': 2, 'headline_rows': 0},
        'national_industry': {'categories': 1, 'headline_rows': 2},
        'sector': {'categories': 1, 'headline_rows': 1},
        'subsector': {'categories': 2, 'headline_rows': 0},
    }
    assert report['categories'] == [
        {'INDNAICS': 'K', 'YEAR': 2023, 'rows': 2, 'headline_rows': 2},
        {'INDNAICS': 'P', 'YEAR': 2023, 'rows': 2, 'headline_rows': 0},
        {'INDNAICS': 'Q', 'YEAR': 2023, 'rows': 1, 'headline_rows': 0},
        {'INDNAICS': 'S', 'YEAR': 2023, 'rows': 1, 'headline_rows': 1},
        {'INDNAICS': 'U', 'YEAR': 2023, 'rows': 1, 'headline_rows': 0},
        {'INDNAICS': 'V', 'YEAR': 2023, 'rows': 1, 'headline_rows': 0},
    ]


def test_the_funnel_is_cumulative_and_ends_at_the_headline_flag():
    report = rules.summarize(rules.wage_persons(core_frame(funnel_rows())))
    totals = [step['total'] for step in report['funnel']]
    assert [step['step'] for step in report['funnel']] == [
        'earners',
        'no_headline_allocation',
        'full_time_full_year',
        'wage_salary',
        'headline',
    ]
    assert totals == sorted(totals, reverse=True)
    assert report['funnel'][-1]['total'] == report['flags']['flag_headline']['total']
    assert report['rows']['total'] == report['funnel'][0]['total']


def test_the_funnel_counts_each_step_beside_the_previous_ones_not_alone():
    # One row is part time with a headline allocation. A step that counted its own rule
    # alone would count it at full time, full year.
    rows = [core_row(), core_row(QIND=4, UHRSWORK=30), core_row(UHRSWORK=30, CLASSWKRD=13)]
    funnel = rules.summarize(rules.wage_persons(core_frame(rows)))['funnel']
    assert [step['total'] for step in funnel] == [3, 2, 1, 1, 1]


def test_summarize_keeps_every_year_key_when_a_year_has_no_headline_rows():
    rows = [core_row(YEAR=2023), core_row(YEAR=2024, QIND=4, CLASSWKRD=13, UHRSWORK=20)]
    report = rules.summarize(rules.wage_persons(core_frame(rows)))
    assert report['rows']['by_year'] == {'2023': 1, '2024': 1}
    assert report['headline_categories'] == {'2023': 1, '2024': 0}
    assert report['flags']['flag_headline'] == {'total': 1, 'by_year': {'2023': 1, '2024': 0}}
    assert report['funnel'][-1] == {'step': 'headline', 'total': 1,
                                    'by_year': {'2023': 1, '2024': 0}}
    assert report['flags']['flag_any_allocated']['by_year'] == {'2023': 0, '2024': 1}
    assert report['categories'] == [
        {'INDNAICS': '6231', 'YEAR': 2023, 'rows': 1, 'headline_rows': 1},
        {'INDNAICS': '6231', 'YEAR': 2024, 'rows': 1, 'headline_rows': 0},
    ]


def test_summarize_has_exactly_the_documented_keys_and_python_values():
    report = rules.summarize(rules.wage_persons(core_frame(funnel_rows())))
    assert set(report) == {'contract', 'rows', 'funnel', 'flags', 'categories',
                           'headline_categories', 'shared_nodes', 'node_levels'}
    assert tuple(report['flags']) == SPEC_FLAGS
    assert json.loads(json.dumps(report)) == report
    assert type(report['rows']['total']) is int
    assert type(report['categories'][0]['YEAR']) is int
    assert all(type(year) is str for year in report['rows']['by_year'])


def keys_of(value) -> set:
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in keys_of(item)}
    if isinstance(value, list):
        return {key for item in value for key in keys_of(item)}
    return set()


def test_the_report_holds_no_run_identity_or_person_value():
    report = rules.summarize(rules.wage_persons(core_frame(funnel_rows())))
    banned = {'run_id', 'created_at', 'commit', 'dirty', 'source_row', 'source_parquet_sha256',
              'INCWAGE', 'PERWT'}
    assert not banned & keys_of(report)


def test_summarize_reads_a_parquet_scan_the_same_way(tmp_path):
    persons = rules.wage_persons(core_frame(funnel_rows()))
    path = tmp_path / 'persons.parquet'
    persons.sink_parquet(path)
    assert rules.summarize(pl.scan_parquet(path)) == rules.summarize(persons)


def test_summarize_an_empty_file_reports_zero_rows():
    report = rules.summarize(rules.wage_persons(core_frame([core_row(INCWAGE=0)])))
    assert report['rows'] == {'total': 0, 'by_year': {}}
    assert report['categories'] == []
    assert report['shared_nodes'] == {'categories': 0, 'nodes': 0}
    assert report['node_levels'] == {}


# --- Property ----------------------------------------------------------------------------

CATEGORIES = {
    'A': (COMMON_NODE, DELIVERED_NODE),
    'B': (COMMON_NODE, 'naics:2022:industry:62311'),
    'C': (OTHER_COMMON, OTHER_DELIVERED),
}
SPEC_CLASSWKRD = (13, 14, 22, 23, 25, 27, 28, 29)


@st.composite
def core_rows(draw) -> dict:
    category = draw(st.sampled_from(sorted(CATEGORIES)))
    common, delivered = CATEGORIES[category]
    return core_row(
        **{name: draw(st.sampled_from([0, 4])) for name in Q_COLUMNS},
        UHRSWORK=draw(st.integers(30, 40)),
        WKSWORK2=draw(st.integers(1, 6)),
        CLASSWKRD=draw(st.sampled_from(SPEC_CLASSWKRD)),
        STATEFIP=draw(st.integers(1, 2)),
        YEAR=draw(st.integers(2023, 2024)),
        INCWAGE=draw(st.sampled_from([40000, 50000, 60000])),
        INDNAICS=category,
        industry_canonical_common_node_id=common,
        industry_native_node_id=delivered,
    )


def oracle(rows: list[dict]) -> dict[str, list[bool]]:
    '''Return each flag for each row, from the spec's words and plain Python.'''
    categories_on = {}
    top = {}
    for row in rows:
        node = row['industry_canonical_common_node_id']
        categories_on.setdefault(node, set()).add(row['INDNAICS'])
        key = (row['STATEFIP'], row['YEAR'])
        top[key] = max(top.get(key, 0), row['INCWAGE'])
    expected = {name: [] for name in SPEC_FLAGS}
    for row in rows:
        headline_allocated = any(row[name] != 0 for name in SPEC_HEADLINE_Q)
        shared = len(categories_on[row['industry_canonical_common_node_id']]) > 1
        full_time_full_year = row['UHRSWORK'] >= 35 and row['WKSWORK2'] == 6
        wage_salary = row['CLASSWKRD'] in (22, 23, 25, 27, 28)
        expected['flag_industry_shared_node'].append(shared)
        expected['flag_any_allocated'].append(any(row[name] != 0 for name in Q_COLUMNS))
        at_top = row['INCWAGE'] == top[(row['STATEFIP'], row['YEAR'])]
        expected['flag_incwage_topcoded'].append(at_top)
        expected['flag_full_time_full_year'].append(full_time_full_year)
        expected['flag_wage_salary'].append(wage_salary)
        expected['flag_headline'].append(
            not headline_allocated and full_time_full_year and wage_salary and not shared
        )
    return expected


@settings(deadline=None)  # Polars aggregates on shared CPUs exceed 200 ms
@given(rows=st.lists(core_rows(), min_size=1, max_size=30))
def test_headline_is_the_conjunction_of_its_parts(rows):
    persons = rules.wage_persons(core_frame(rows)).collect()
    expected = oracle(rows)
    assert persons['flag_headline'].to_list() == expected['flag_headline']


@settings(deadline=None, max_examples=60)
@given(rows=st.lists(core_rows(), min_size=1, max_size=30))
def test_every_flag_follows_the_spec_words(rows):
    persons = rules.wage_persons(core_frame(rows)).collect()
    assert persons['source_row'].to_list() == list(range(len(rows)))
    for name, values in oracle(rows).items():
        assert persons[name].to_list() == values, name
    report = rules.summarize(persons.lazy())
    assert report['rows']['total'] == len(rows)
    assert report['funnel'][-1]['total'] == sum(oracle(rows)['flag_headline'])
