'''Complete-prefix validation with streamed keys and unchanged scientific closure.'''

import polars as pl
import pytest
from test_acs_target_contract import empty_tables, frame, valid_tables

from embedding_data import acs_target_contract as contract
from embedding_data import acs_target_tables as assembly
from embedding_data.target_contract import TARGET_KEY_COLUMNS, TARGET_SCHEMA

def complete_tables():
    tables = valid_tables()
    target = tables['targets_observed'].row(0, named=True)
    target.update(value=1.0)
    tables['targets_observed'] = pl.DataFrame([
        target | {'measure': 'annual_average_total', 'value': 25.0}, target
    ], schema=TARGET_SCHEMA).sort(TARGET_KEY_COLUMNS)
    original = tables['target_support'].row(0, named=True)
    tables['target_support'] = frame('target_support', [original | {
        'measure': measure, 'component_year': year,
        'n_unweighted': 2 if year == 0 else 1,
        'denominator_n_unweighted': 2 if year == 0 else 1,
        'cell_weight_sum_exact': '50' if year == 0 else '25',
        'denominator_weight_sum_exact': '50' if year == 0 else '25',
        'cell_mass': 25.0 if year == 0 else 12.5,
        'denominator_mass': 25.0 if year == 0 else 12.5,
        'fractional_support_mass': 2.0 if year == 0 else 1.0,
        'denominator_fractional_support_mass': 2.0 if year == 0 else 1.0,
    } for measure in contract.MEASURES for year in (0, 2023, 2024)])
    tables['replicate_estimates'] = pl.concat([
        tables['replicate_estimates'].with_columns(
            pl.lit(measure).alias('measure'), pl.lit('50').alias('denominator_sum_exact'),
            pl.lit(25.0).alias('denominator'),
            pl.lit(25.0 if measure == 'annual_average_total' else 1.0).alias('estimate'))
        for measure in contract.MEASURES
    ]).sort(contract.AUXILIARY_KEYS['replicate_estimates'])
    return tables


def scans(tables, root):
    result = {}
    for name, data in tables.items():
        # Real physical fragment boundaries, including inside an 80-vector.
        paths = []
        for index, part in enumerate(data.iter_slices(7)):
            path = root / f'{name}-{index}.parquet'
            part.write_parquet(path, row_group_size=3)
            paths.append(path)
        if not paths:
            path = root / f'{name}-empty.parquet'
            data.write_parquet(path)
            paths.append(path)
        result[name] = pl.scan_parquet(paths)
    return result


def test_complete_validation_does_not_materialize_full_output_tables(tmp_path, monkeypatch):
    data = scans(complete_tables(), tmp_path)
    original = pl.LazyFrame.collect
    observed = []

    def collect(lf, *args, **kwargs):
        result = original(lf, *args, **kwargs)
        if result.schema in [contract.SUPPORT_SCHEMA, contract.REPLICATE_SCHEMA, TARGET_SCHEMA]:
            observed.append((tuple(result.columns), result.height))
        return result

    monkeypatch.setattr(pl.LazyFrame, 'collect', collect)
    assembly.validate_complete_tables(data)
    assert observed == [], f'whole published tables were materialized: {observed}'


def test_key_order_carry_rejects_late_fragment_regression(tmp_path, monkeypatch):
    helper = getattr(contract, '_validate_key_order', None)
    assert helper is not None, 'key-only streamed order validation is required'
    monkeypatch.setattr(contract, '_VALIDATION_CHUNK_ROWS', 2)
    data = pl.DataFrame({'a': [None, 'a', 'a', 'b', 'a'], 'b': [0, 0, 1, 0, 2]})
    paths = []
    for index, part in enumerate(data.iter_slices(2)):
        path = tmp_path / f'{index}.parquet'
        part.write_parquet(path)
        paths.append(path)
    with pytest.raises(ValueError, match='order'):
        helper(pl.scan_parquet(paths), ['a', 'b'], 'order differs')


def test_prefix_registry_is_union_and_keeps_all_views_and_variants():
    helper = getattr(contract, '_validation_partitions', None)
    assert helper is not None, 'complete union-prefix validation is required'
    keys = ['source', 'family', 'unit_a_type', 'unit_a']
    left = pl.DataFrame({'source': ['acs'] * 3, 'family': ['f'] * 3,
        'unit_a_type': ['t'] * 3, 'unit_a': ['a'] * 3,
        'view': ['observed', 'canonical', 'observed'],
        'variant': ['strict', 'strict', 'sensitive']})
    right = left.tail(1).with_columns(pl.lit('orphan-tail').alias('unit_a'))
    parts = list(helper([left.lazy(), right.lazy()], keys))
    assert len(parts) == 2
    assert [p.collect().height for p in parts[0]] == [3, 0]
    assert [p.collect().height for p in parts[1]] == [0, 1]


@pytest.mark.parametrize('defect', [
    'duplicate_flags', 'duplicate_se', 'late_denominator', 'missing37_duplicate36',
    'bad_component', 'target_orphan', 'replicate_orphan', 'status_orphan', 'bad_product',
    'bad_pool', 'bad_view', 'bad_universe', 'unknown_tail', 'missing_se_reason',
    'missing_annual', 'missing_measure', 'missing_target', 'bad_affected', 'bad_se',
])
def test_cross_fragment_semantic_corruptions_are_rejected(tmp_path, monkeypatch, defect):
    data = complete_tables()
    support = data['target_support']
    reps = data['replicate_estimates']
    targets = data['targets_observed']
    if defect in {'duplicate_flags', 'duplicate_se'}:
        extra = targets.head(1).with_columns(
            pl.lit(['size_gate_pending', 'variant']).alias('flags'))
        if defect == 'duplicate_se':
            extra = extra.with_columns(pl.lit('none').alias('se_method'),
                                      pl.lit(None, dtype=pl.Float64).alias('se'))
        data['targets_observed'] = pl.concat([targets, extra]).sort(TARGET_KEY_COLUMNS)
    elif defect == 'late_denominator':
        data['replicate_estimates'] = reps.with_columns(pl.when(
            pl.col('replicate').eq(80) & pl.col('measure').eq('forward_share'))
            .then(pl.lit(50.)).otherwise(pl.col('denominator')).alias('denominator'))
    elif defect == 'missing37_duplicate36':
        data['replicate_estimates'] = reps.with_columns(pl.when(pl.col('replicate').eq(37))
            .then(pl.lit(36, dtype=pl.UInt8)).otherwise(pl.col('replicate')).alias('replicate'))
    elif defect == 'bad_component':
        data['target_support'] = support.with_columns(pl.when(pl.col('component_year').eq(2024))
            .then(pl.lit(2025, dtype=pl.Int64)).otherwise(pl.col('component_year'))
            .alias('component_year'))
    elif defect in {'target_orphan', 'replicate_orphan'}:
        name = 'targets_observed' if defect == 'target_orphan' else 'replicate_estimates'
        data[name] = data[name].with_columns(pl.lit('feature:acs_industry_category:z-tail')
                                            .alias('unit_a'))
    elif defect == 'status_orphan':
        row = support.row(0, named=True) | {
            'unit_a': 'feature:acs_industry_category:z-tail', 'unit_b_type': None, 'unit_b': None,
            'measure': 'forward_share', 'record_kind': 'denominator_status',
            'n_unweighted': 0, 'cell_weight_sum_exact': None, 'cell_mass': None,
            'fractional_support_mass': None, 'denominator_mass': 0.,
            'point_status': 'nonpositive_denominator', 'point_reason': 'nonpositive_denominator',
            'se_status': 'undefined_point', 'se_reason': 'undefined_point'}
        data['target_support'] = pl.concat([support, frame('target_support', [row])]).sort(
            contract.AUXILIARY_KEYS['target_support'], nulls_last=False)
    elif defect in {'bad_product', 'bad_pool', 'bad_view', 'bad_universe', 'unknown_tail'}:
        column, value = {'bad_product': ('product_id', 'unregistered'),
            'bad_pool': ('pool_divisor', 1), 'bad_view': ('view', 'canonical'),
            'bad_universe': ('universe', 'wrong'), 'unknown_tail': ('source', 'zzz')}[defect]
        dtype = reps.schema[column]
        data['replicate_estimates'] = reps.with_columns(pl.when(pl.col('replicate').eq(80))
            .then(pl.lit(value, dtype=dtype)).otherwise(pl.col(column)).alias(column)).sort(
                contract.AUXILIARY_KEYS['replicate_estimates'])
    elif defect == 'missing_se_reason':
        data['target_support'] = support.with_columns(pl.lit('fabricated').alias('se_reason'))
    elif defect == 'missing_annual':
        data['target_support'] = support.filter(pl.col('component_year').ne(2024))
    elif defect == 'missing_measure':
        for name in ('target_support', 'replicate_estimates', 'targets_observed'):
            data[name] = data[name].filter(pl.col('measure').eq('forward_share'))
    elif defect == 'missing_target':
        data['targets_observed'] = targets.head(0)
    elif defect == 'bad_affected':
        data['target_support'] = support.with_columns(
            pl.lit([37], dtype=pl.List(pl.UInt8)).alias('undefined_replicates'))
    else:
        data['targets_observed'] = targets.with_columns(pl.lit(0.125).alias('se'))
    monkeypatch.setattr(contract, '_VALIDATION_CHUNK_ROWS', 3)
    with pytest.raises(ValueError):
        assembly.validate_complete_tables(scans(data, tmp_path))


@pytest.mark.parametrize('chunk_rows', [1, 3, 7])
def test_valid_exact_tables_and_empties_keep_original_acceptance(
    tmp_path, monkeypatch, chunk_rows
):
    monkeypatch.setattr(contract, '_VALIDATION_CHUNK_ROWS', chunk_rows)
    assembly.validate_complete_tables(scans(complete_tables(), tmp_path))
    assembly.validate_complete_tables(empty_tables())


def test_auxiliary_unsorted_tail_and_null_first_keys_keep_original_rejection(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(contract, '_VALIDATION_CHUNK_ROWS', 1)
    data = complete_tables()['target_support']
    contract.validate_auxiliary('target_support', data)
    with pytest.raises(ValueError, match='sort'):
        contract.validate_auxiliary('target_support', data.reverse().lazy())


def test_complete_native_denominator_crosses_128_code_batches(monkeypatch):
    from acs_target_fixtures import estimation_rows, weights

    from embedding_data.acs_target_estimation import aggregate_native

    native = aggregate_native(estimation_rows([
        {'year': 2024, 'a': a, 'b': str(b), **weights('1')}
        for a in ('a', 'z-tail') for b in range(257)
    ]))
    checks = []
    original = assembly._check_denominator_sums

    def check(frame, *args, **kwargs):
        checks.append(frame.select(pl.col('unit_a').n_unique(), pl.len()).collect().row(0))
        return original(frame, *args, **kwargs)

    monkeypatch.setattr(assembly, '_check_denominator_sums', check)
    assembly._validate_aggregate_denominators(native)
    assert checks == [(1, 257 * 243), (1, 257 * 243)]


def second_prefix(tables):
    from embedding_data.acs_mapping_contract import NATURAL_KEYS, lookup_id

    unit = tables['target_units'].filter(pl.col('code_system').eq('naics')).row(0, named=True)
    old = unit['unit']
    unit['code_source_token'] = '111112'
    unit['code_code_lookup_id'] = lookup_id([unit['code_' + name]
                                           for name in NATURAL_KEYS['code']])
    unit['unit'] = 'feature:acs_industry_category:' + unit['code_code_lookup_id']
    extra = {name: data for name, data in tables.items()}
    extra['target_units'] = pl.concat([tables['target_units'],
                                      frame('target_units', [unit])]).sort(['unit_type', 'unit'])
    for name in ('target_support', 'replicate_estimates', 'targets_observed'):
        extra[name] = tables[name].with_columns(pl.when(pl.col('unit_a').eq(old))
            .then(pl.lit(unit['unit'])).otherwise(pl.col('unit_a')).alias('unit_a'))
    return extra


@pytest.mark.parametrize('precision_case', ['ordinary', 'heterogeneous_overflow'])
def test_global_decimal38_scale_is_preserved_across_prefixes(precision_case):
    left = complete_tables()
    right = second_prefix(left)
    if precision_case == 'heterogeneous_overflow':
        for data, pooled_exact, annual_exact, mass in [
            (left, '20000000000000000000', '10000000000000000000', 1e19),
            (right, '0.00000000000000000002', '0.00000000000000000001', 1e-20),
        ]:
            data['target_support'] = data['target_support'].with_columns([
                pl.when(pl.col('component_year').eq(0)).then(pl.lit(pooled_exact))
                .otherwise(pl.lit(annual_exact)).alias(name)
                for name in ('cell_weight_sum_exact', 'denominator_weight_sum_exact')
            ] + [pl.when(pl.col('component_year').eq(0)).then(pl.lit(mass))
                 .otherwise(pl.lit(mass / 2)).alias(name)
                 for name in ('cell_mass', 'denominator_mass')])
            data['replicate_estimates'] = data['replicate_estimates'].with_columns([
                pl.lit(pooled_exact).alias(name)
                for name in ('numerator_sum_exact', 'denominator_sum_exact')
            ] + [pl.lit(mass).alias(name) for name in ('numerator', 'denominator')]
              + [pl.when(pl.col('measure').eq('annual_average_total')).then(pl.lit(mass))
                 .otherwise(pl.lit(1.)).alias('estimate')])
            data['targets_observed'] = data['targets_observed'].with_columns(
                pl.lit(mass).alias('n_weighted'),
                pl.when(pl.col('measure').eq('annual_average_total')).then(pl.lit(mass))
                .otherwise(pl.lit(1.)).alias('value'))
    combined = {}
    for name in left:
        if name == 'target_units':
            combined[name] = right[name]
        else:
            combined[name] = pl.concat([left[name], right[name]]).sort(
                TARGET_KEY_COLUMNS if name in contract.TARGET_TABLES
                else contract.AUXILIARY_KEYS[name], nulls_last=False)
    if precision_case == 'heterogeneous_overflow':
        with pytest.raises(pl.exceptions.InvalidOperationError, match='Decimal'):
            assembly.validate_complete_tables(combined)
    else:
        assembly.validate_complete_tables(combined)


@pytest.mark.parametrize('table,column,value', [
    ('target_support', 'product_id', 'unknown-tail'),
    ('replicate_estimates', 'product_id', 'unknown-tail'),
    ('replicate_estimates', 'source', 'unknown-tail'),
    ('targets_observed', 'universe', 'unknown-tail'),
])
def test_unknown_global_metadata_rejected_before_partition_filtering(monkeypatch, table,
                                                                    column, value):
    data = complete_tables()
    data[table] = data[table].with_columns(pl.lit(value).alias(column))

    def unexpected(*args, **kwargs):
        raise AssertionError('invalid global metadata reached prefix filtering')

    monkeypatch.setattr(contract, '_validation_partitions', unexpected)
    with pytest.raises(ValueError):
        contract.validate_cross_tables(data, contract.PRODUCTS)


def test_same_a_variants_share_complete_relation_and_bounded_key_batches(tmp_path, monkeypatch):
    from embedding_data import acs_target_estimation as estimation

    data = complete_tables()
    original_id = data['target_support']['product_id'][0]
    original_product = next(p for p in contract.PRODUCTS if p.product_id == original_id)
    other = next(p for p in contract.PRODUCTS if p.family == original_product.family
                 and p.view == original_product.view
                 and p.base_universe == original_product.base_universe
                 and p.evidence_policy != original_product.evidence_policy)
    for name in ('target_support', 'replicate_estimates', 'targets_observed'):
        extra = data[name].with_columns(
            pl.lit(other.base_universe + ':' + other.evidence_policy).alias('universe'))
        if 'product_id' in extra.columns:
            extra = extra.with_columns(pl.lit(other.product_id).alias('product_id'))
        data[name] = pl.concat([data[name], extra]).sort(
            TARGET_KEY_COLUMNS if name == 'targets_observed' else contract.AUXILIARY_KEYS[name])
    scans_on_disk = scans(data, tmp_path)
    original_relation = contract._validate_statistic_relationships
    original_batches = pl.LazyFrame.collect_batches
    original_se = estimation.replicate_se
    relations, vectors, batches_seen = [], [], []

    def relation(support, reps, targets, scales):
        relations.append(tuple(lf.select(pl.len()).collect().item()
                               for lf in (support, reps, targets)))
        assert support.select(pl.col('universe').n_unique()).collect().item() == 2
        return original_relation(support, reps, targets, scales)

    def batches(lf, *args, **kwargs):
        for batch in original_batches(lf, *args, **kwargs):
            # Only original keys or actual-prefix metadata cross the Python boundary.
            assert not {'cell_mass', 'estimate', 'value', 'flags'} & set(batch.columns)
            batches_seen.append(batch.height)
            yield batch

    def se(point, vector):
        vectors.append(len(vector))
        return original_se(point, vector)

    monkeypatch.setattr(contract, '_VALIDATION_CHUNK_ROWS', 3)
    monkeypatch.setattr(contract, '_validate_statistic_relationships', relation)
    monkeypatch.setattr(pl.LazyFrame, 'collect_batches', batches)
    monkeypatch.setattr(estimation, 'replicate_se', se)
    assembly.validate_complete_tables(scans_on_disk)
    assert relations == [(12, 320, 4)]
    assert vectors == [80] * 4
    assert max(batches_seen) <= 3
    assert sum(batches_seen) >= 12 + 320 + 4


@pytest.mark.parametrize('defect', ['unknown_metadata', 'duplicate', 'order'])
def test_residual_axes_checked_once_even_without_target_prefixes(tmp_path, monkeypatch, defect):
    from test_acs_target_contract import valid_residual_tables

    data = valid_residual_tables()
    residual = data['allocation_residuals']
    # These workplace-origin residuals have no corresponding target a prefix.
    data.update({name: empty_tables()[name] for name in (*contract.TARGET_TABLES,
                 'target_support', 'replicate_estimates')})
    if defect == 'unknown_metadata':
        data['allocation_residuals'] = residual.with_columns(pl.lit('unknown').alias('product_id'))
    elif defect == 'duplicate':
        data['allocation_residuals'] = pl.concat([residual, residual])
    else:
        first = residual.with_columns(pl.lit(80, dtype=pl.UInt8).alias('replicate'))
        data['allocation_residuals'] = pl.concat([first, residual])
    monkeypatch.setattr(contract, '_VALIDATION_CHUNK_ROWS', 1)
    with pytest.raises(ValueError):
        contract.validate_cross_tables(scans(data, tmp_path), contract.PRODUCTS)


def test_public_cross_validator_does_not_gain_complete_target_order_requirement():
    data = complete_tables()
    data['targets_observed'] = data['targets_observed'].reverse()
    contract.validate_cross_tables(data, contract.PRODUCTS)
    with pytest.raises(ValueError, match='sort'):
        assembly.validate_complete_tables(data)


def test_allocated_signed_replicate_closure_keeps_full_code_reduction_order():
    from dataclasses import replace
    from math import fsum

    from embedding_data.acs_target_estimation import AggregateSet

    values = [1e16, *([1.] * 255), -1e16]
    assert fsum(values) == 255.0
    cells = pl.DataFrame([
        {'unit_a_type': 'county', 'unit_a': a, 'unit_b_type': 'acs_industry_category',
         'unit_b': f'{b:03}', 'component_year': 2024, 'replicate': 37, 'mass': value}
        for a in ('a', 'z-tail') for b, value in enumerate(values)
    ]).lazy()
    denominators = cells.select('unit_a_type', 'unit_a', 'component_year', 'replicate').unique(
    ).with_columns(pl.lit(0.).alias('mass'))
    product = next(p for p in contract.PRODUCTS if p.view == 'allocated_county')
    aggregate = AggregateSet(cells, denominators, pl.LazyFrame(), product)
    assembly._validate_aggregate_denominators(aggregate)
    # A changed last denominator cannot be hidden by per-batch partial reduction.
    broken = denominators.with_columns(pl.when(pl.col('unit_a').eq('z-tail'))
        .then(pl.lit(255.)).otherwise(pl.col('mass')).alias('mass'))
    with pytest.raises(ValueError, match='denominator'):
        assembly._validate_aggregate_denominators(replace(aggregate, denominators=broken))


@pytest.mark.parametrize('table,side', [
    ('targets_observed', 'a'), ('targets_observed', 'b'),
    ('replicate_estimates', 'a'), ('replicate_estimates', 'b'),
])
def test_unknown_endpoints_rejected_before_partition_filtering(monkeypatch, table, side):
    data = complete_tables()
    kind = data[table]['unit_' + side + '_type'][0]
    data[table] = data[table].with_columns(
        pl.lit(f'feature:{kind}:unregistered').alias('unit_' + side))

    def unexpected(*args, **kwargs):
        raise AssertionError('unregistered endpoint reached prefix filtering')

    monkeypatch.setattr(contract, '_validation_partitions', unexpected)
    with pytest.raises(ValueError, match='endpoint missing from unit registry'):
        contract.validate_cross_tables(data, contract.PRODUCTS)
