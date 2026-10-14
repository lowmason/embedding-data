from dataclasses import replace

import polars as pl
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from target_fixtures import assigned_tree

from embedding_data import ita_area_mix as mix

@pytest.fixture(scope='module')
def inputs(tmp_path_factory):
    assignments, nodes, counties = assigned_tree(tmp_path_factory.mktemp('area_mix'))
    return assignments.collect().lazy(), nodes, counties


def test_golden_shares_and_coverage(inputs):
    assignments, nodes, counties = inputs
    result = mix.estimate(assignments, nodes)
    mix.validate_area_mix(result, nodes, counties)
    target = result.targets.collect()
    assert target.select('unit_a', 'unit_b', 'value', 'n_unweighted', 'n_weighted').rows() == [
        ('geography:2025:county:01001', 'naics:2022:national_industry:111111', .75, 3, 3.),
        ('geography:2025:county:01001', 'naics:2022:national_industry:111112', .25, 1, 1.),
        ('geography:2025:county:51510', 'naics:2022:national_industry:111112', 1., 1, 1.),
    ]
    assert result.denominators.collect().select(
        'county_id', 'n_assigned', 'n_eligible', 'n_excluded_industry').rows() == [
        ('geography:2025:county:01001', 7, 4, 3),
        ('geography:2025:county:51001', 1, 0, 1),
        ('geography:2025:county:51510', 1, 1, 0),
    ]
    assert result.report['selected_year_partition'] == dict(
        source=12, unassigned_geography=3, assigned_excluded_industry=4, eligible=5)
    assert result.report['all_year_partition'] == dict(
        source=21, unassigned_geography=3, assigned_excluded_industry=11, eligible=7)
    assert result.report['exact_duplicates'] == {'groups': 1, 'rows': 2, 'excess': 1}
    assert result.report['repeated_ids']['id'] == {'groups': 1, 'rows': 2, 'excess': 1}
    assert target['se'].null_count() == 3
    assert target['se_method'].to_list() == ['none'] * 3
    assert all('size_gate_pending' in flags for flags in target['flags'])


def test_true_null_support_and_county_labels(inputs):
    assignments, nodes, _ = inputs
    assignments = assignments.with_columns(
        pl.when(pl.col('id').eq(23003)).then(None).otherwise(False)
        .cast(pl.Boolean).alias('filing_decision'),
        pl.col('id').eq(23003).alias('outside_rule'),
        pl.col('id').eq(23003).alias('naics_year_from_dictionary'))
    result = mix.estimate(assignments, nodes)
    counts = result.flag_counts.collect()
    for flag, state in [('flag_hours_per_employee', 'null'), ('outside_rule', 'true'),
                        ('filing_decision', 'null'), ('naics_year_from_dictionary', 'true')]:
        selected = counts.filter(pl.col('county_id').eq('geography:2025:county:01001')
                                 .and_(pl.col('flag_name').eq(flag))
                                 .and_(pl.col('flag_state').eq(state)))
        assert selected['scope'].to_list() == ['denominator', 'numerator']
        assert selected['n'].to_list() == [1, 1]
        for labels in result.targets.filter(
                pl.col('unit_a').eq('geography:2025:county:01001')).collect()['flags']:
            assert f'denominator:{flag}:{state}' in labels
    assert counts.filter(pl.col('flag_name').eq('flag_naics_crosswalked')).is_empty()


def test_empty_support_is_exactly_typed():
    for frame in [pl.LazyFrame({'county_id': ['x'], 'naics_2022_node_id': ['y']}),
                  pl.LazyFrame({'county_id': ['x'], 'naics_2022_node_id': ['y'],
                                'diagnostic': [False]})]:
        support = mix.support_flags(frame).collect()
        assert support.schema == mix.FLAG_COUNT_SCHEMA
        assert support.is_empty()


@pytest.mark.parametrize('year', [2016, 2022, 2024, 2025])
def test_other_year_refused(inputs, year):
    with pytest.raises(ValueError, match='2023'):
        mix.estimate(inputs[0], inputs[1], year=year)


def test_no_eligible_refused(inputs):
    with pytest.raises(ValueError, match='eligible'):
        mix.estimate(inputs[0].filter(pl.col('id').eq(23012)), inputs[1])


@pytest.mark.parametrize('column,value', [
    ('flag_naics_crosswalked', True), ('flag_naics_unresolved', None),
    ('naics_2022_code', '111112'), ('naics_2022_node_id', 'absent')])
def test_native_contradiction_refused(inputs, column, value):
    changed = inputs[0].with_columns(pl.when(pl.col('id').eq(23001)).then(pl.lit(value))
                                     .otherwise(pl.col(column)).alias(column))
    with pytest.raises(ValueError, match='native'):
        mix.estimate(changed, inputs[1])


@pytest.mark.parametrize('column,value', [('system', 'soc'), ('vintage', 2017),
                                         ('level', 'industry')])
def test_node_type_vintage_level_refused(inputs, column, value):
    nodes = inputs[1].with_columns(pl.lit(value).cast(inputs[1].schema[column]).alias(column))
    with pytest.raises(ValueError):
        mix.estimate(inputs[0], nodes)


@given(st.integers(min_value=1, max_value=4), st.booleans())
@settings(max_examples=8, deadline=None)
def test_repeat_and_permute_preserve_support(inputs, copies, reverse):
    assignments, nodes, _ = inputs
    frame = pl.concat([assignments] * copies)
    if reverse:
        frame = frame.reverse()
    result = mix.estimate(frame, nodes).targets.collect()
    assert result['value'].to_list() == [.75, .25, 1.]
    assert result['n_unweighted'].to_list() == [3 * copies, copies, copies]


@pytest.mark.parametrize('column,value', [('value', .5), ('n_weighted', 99.),
    ('n_unweighted', 0), ('se', 1.), ('source', 'other'), ('unit_b', 'naics:2022:industry:11111')])
def test_family_validator_rejects_corrupt_target(inputs, column, value):
    result = mix.estimate(inputs[0], inputs[1])
    altered = result.targets.with_columns(
        pl.lit(value).cast(result.targets.collect_schema()[column]).alias(column))
    with pytest.raises(ValueError):
        mix.validate_area_mix(replace(result, targets=altered), inputs[1], inputs[2])


def test_normalization_tolerance(inputs):
    result = mix.estimate(inputs[0], inputs[1])
    for epsilon, valid in [(1e-14, True), (1e-10, False)]:
        changed = replace(result, targets=result.targets.with_columns(
            pl.col('value').add(epsilon)))
        if valid:
            mix.validate_area_mix(changed, inputs[1], inputs[2])
        else:
            with pytest.raises(ValueError):
                mix.validate_area_mix(changed, inputs[1], inputs[2])


def test_validator_refuses_empty_population(inputs):
    result = mix.estimate(inputs[0], inputs[1])
    empty = replace(result, targets=result.targets.limit(0),
                    denominators=result.denominators.limit(0),
                    flag_counts=result.flag_counts.limit(0))
    with pytest.raises(ValueError):
        mix.validate_area_mix(empty, inputs[1], inputs[2])


@pytest.mark.parametrize('defect', ['count', 'missing', 'duplicate', 'sample', 'county'])
def test_denominator_corruption_refused(inputs, defect):
    result = mix.estimate(inputs[0], inputs[1])
    frame = result.denominators
    if defect == 'count':
        frame = frame.with_columns(pl.col('n_eligible').add(1))
    elif defect == 'missing':
        frame = frame.filter(pl.col('n_eligible').eq(0))
    elif defect == 'duplicate':
        frame = pl.concat([frame, frame])
    elif defect == 'sample':
        frame = frame.with_columns(pl.lit('other').alias('sample_set'))
    else:
        frame = frame.with_columns(pl.lit('geography:2025:county:99999').alias('county_id'))
    with pytest.raises(ValueError):
        mix.validate_area_mix(replace(result, denominators=frame), inputs[1], inputs[2])


@pytest.mark.parametrize('defect', ['count', 'missing_scope', 'duplicate', 'state', 'label'])
def test_flag_corruption_refused(inputs, defect):
    result = mix.estimate(inputs[0], inputs[1])
    frame = result.flag_counts
    if defect == 'count':
        frame = frame.with_columns(pl.col('n').add(20))
    elif defect == 'missing_scope':
        frame = frame.filter(pl.col('scope').eq('numerator'))
    elif defect == 'duplicate':
        frame = pl.concat([frame, frame])
    elif defect == 'state':
        frame = frame.with_columns(pl.lit('false').alias('flag_state'))
    else:
        frame = frame.with_columns(pl.lit('other').alias('flag_name'))
    with pytest.raises(ValueError):
        mix.validate_area_mix(replace(result, flag_counts=frame), inputs[1], inputs[2])


def test_true_and_null_support_cannot_overlap(inputs):
    result = mix.estimate(inputs[0], inputs[1])
    frame = result.flag_counts.filter(pl.col('flag_name').eq('flag_hours_per_employee'))
    forged = pl.concat([frame.with_columns(pl.lit(state).alias('flag_state'))
                        for state in ['true', 'null']])
    labels = result.targets.with_columns(pl.lit(['size_gate_pending']).alias('flags'))
    # Even canonical labels cannot legitimize impossible disjoint-state counts.
    keys = labels.select(pl.col('unit_a').alias('county_id'),
                         pl.col('unit_b').alias('naics_2022_node_id'))
    expected_labels = mix._labels(keys, forged).collect().rename(
        {'county_id': 'unit_a', 'naics_2022_node_id': 'unit_b'})
    labels = labels.drop('flags').join(expected_labels.lazy(), on=['unit_a', 'unit_b'])
    with pytest.raises(ValueError):
        mix.validate_area_mix(replace(result, targets=labels, flag_counts=forged),
                              inputs[1], inputs[2])
