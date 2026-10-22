'''Serialized report summaries and ordered detached reconstruction stay lazy.'''

from types import SimpleNamespace

import polars as pl
import pytest
from test_acs_target_contract import empty_tables
from test_acs_target_validation_spill import complete_tables

from embedding_data import acs_target_bundle as bundle
from embedding_data import acs_target_contract as contract
from embedding_data.target_contract import TARGET_SCHEMA

def report_case(tmp_path):
    tables = complete_tables()
    source = tmp_path / 'source.parquet'
    pl.DataFrame({'YEAR': [2023, 2024, 2024]}).write_parquet(source)
    selected = SimpleNamespace(upstream=SimpleNamespace(sources={'acs/core': SimpleNamespace(
        parquet=source, parquet_record={'sha256': 'f' * 64}, delivery_id='usa_test')}))
    records = []
    for product in contract.PRODUCTS:
        for year, count in ((2023, 1), (2024, 2)):
            records.append({'source': 'acs', 'profile': 'acs/core', 'delivery_id': 'usa_test',
                'source_parquet_sha256': 'f' * 64, 'sample_id': f'us{year}a',
                'component_year': year, 'product_id': product.product_id,
                'partition_kind': 'first_exclusion', 'n_unweighted': count,
                'weighted_mass': float(count)})
    tables['eligibility_diagnostics'] = pl.DataFrame(records, schema=contract.DIAGNOSTIC_SCHEMA)
    for name, data in tables.items():
        data.write_parquet(tmp_path / (name + '.parquet'), row_group_size=3)
    return tables, selected


def test_serialized_read_returns_scans_without_loading_published_rows(tmp_path, monkeypatch):
    original = empty_tables()
    for name, data in original.items():
        data.write_parquet(tmp_path / (name + '.parquet'))
    reads = []
    read = pl.read_parquet

    def eager_read(*args, **kwargs):
        reads.append(args[0])
        return read(*args, **kwargs)

    monkeypatch.setattr(pl, 'read_parquet', eager_read)
    tables = bundle._read_tables(tmp_path)
    assert reads == [], 'serialized table read eagerly materialized published rows'
    assert list(tables) == list(bundle.TABLES)
    for name, data in tables.items():
        assert isinstance(data, pl.LazyFrame)
        assert data.collect_schema() == original[name].schema


def test_report_from_scans_matches_exact_eager_shape_without_whole_table_collect(
    tmp_path, monkeypatch,
):
    eager, selected = report_case(tmp_path)
    expected = bundle._report(eager, selected, 'test', 'fixed-time')
    assert len(expected['products']) == 50
    assert all(row['funnel_closure'] == [
        {'year': 2023, 'input_rows': 1, 'partition_rows': 1},
        {'year': 2024, 'input_rows': 2, 'partition_rows': 2},
    ] for row in expected['products'])
    assert sum(row['target_rows'] for row in expected['products']) == 2
    assert sum(row['supported_statistics'] for row in expected['products']) == 2
    assert sum(row['empty_reason'] is None for row in expected['products']) == 1
    assert expected['tables']['replicate_estimates']['rows'] == 160
    assert expected['tables']['target_support']['rows'] == 6
    assert expected['limits'] == bundle.LIMITS
    collected = []
    collect = pl.LazyFrame.collect

    def tracked(lf, *args, **kwargs):
        result = collect(lf, *args, **kwargs)
        collected.append(result.schema)
        return result

    monkeypatch.setattr(pl.LazyFrame, 'collect', tracked)
    actual = bundle._report({name: pl.scan_parquet(tmp_path / (name + '.parquet'))
                            for name in eager}, selected, 'test', 'fixed-time')
    assert actual == expected
    assert not any(schema in [contract.SUPPORT_SCHEMA, contract.REPLICATE_SCHEMA, TARGET_SCHEMA,
                              contract.DIAGNOSTIC_SCHEMA, contract.RESIDUAL_SCHEMA]
                   for schema in collected), 'report collected complete published facts'


@pytest.mark.parametrize('defect', ['hash', 'delivery', 'profile', 'year', 'sample', 'closure'])
def test_lazy_report_rejects_diagnostic_identity_and_funnel_corruption(tmp_path, defect):
    tables, selected = report_case(tmp_path)
    column, value = {
        'hash': ('source_parquet_sha256', '0' * 64),
        'delivery': ('delivery_id', 'wrong'), 'profile': ('profile', 'acs/wrong'),
        'year': ('component_year', 2025), 'sample': ('sample_id', 'us2023b'),
        'closure': ('n_unweighted', 999),
    }[defect]
    diagnostics = tables['eligibility_diagnostics']
    tables['eligibility_diagnostics'] = diagnostics.with_columns(pl.when(
        pl.int_range(pl.len()).eq(diagnostics.height - 1)).then(pl.lit(value))
        .otherwise(pl.col(column)).cast(diagnostics.schema[column]).alias(column))
    with pytest.raises(ValueError, match='identity|funnel'):
        bundle._report({name: data.lazy() for name, data in tables.items()}, selected,
                       'test', 'fixed-time')


@pytest.mark.parametrize('defect', [None, 'value', 'schema', 'tail', 'order',
                                  'report_count', 'report_status', 'report_conservation'])
def test_detached_reconstruction_uses_real_ordered_streams_and_cleans_external_scratch(
    tmp_path, monkeypatch, defect,
):
    # Isolate this bundle boundary from upstream fixture cost. The authenticated
    # raw-chain lifecycle suite separately exercises real selection and reconstruction.
    import hashlib
    import json

    from embedding_data import target_io

    directory = tmp_path / 'test'
    directory.mkdir()
    eager, selected = report_case(directory)
    (directory / 'source.parquet').rename(tmp_path / 'source.parquet')
    selected.upstream.sources['acs/core'].parquet = tmp_path / 'source.parquet'
    inputs = {'mapping': {'run_id': 'mapping', 'outputs_sha256': 'a' * 64},
              'run_id': 'test', 'created_at': 'fixed-time',
              'selected_upstreams': {'request': dict.fromkeys(
                  bundle.SelectionRequest.__dataclass_fields__, 'test')}}
    report = bundle._report(eager, selected, 'test', 'fixed-time')
    if defect == 'report_count':
        report['tables']['target_support']['rows'] += 1
    elif defect == 'report_status':
        report['support_distributions'][0]['point_status'] = 'fabricated'
    elif defect == 'report_conservation':
        report['allocation_conservation']['serialized_failure_count'] = 1
    (directory / 'inputs.json').write_text(json.dumps(inputs))
    (directory / 'report.json').write_text(json.dumps(bundle._json_normalized(report)))
    target_io.write_json(directory / 'outputs.json', target_io.inventory(directory,
                                                                       list(bundle.FILES)))
    pin = hashlib.sha256((directory / 'outputs.json').read_bytes()).hexdigest()
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    reconstructed = {name: data.lazy() for name, data in eager.items()}
    data = eager['replicate_estimates']
    if defect == 'value':
        data = data.with_columns((pl.col('estimate') + 1).alias('estimate'))
    elif defect == 'schema':
        data = data.with_columns(pl.col('replicate').cast(pl.UInt16))
    elif defect == 'tail':
        data = pl.concat([data, data.tail(1)])
    elif defect == 'order':
        data = data.reverse()
    reconstructed['replicate_estimates'] = data.lazy()
    monkeypatch.setattr(bundle, 'select_targets', lambda *a, **k: selected)
    monkeypatch.setattr(bundle, '_input_evidence', lambda *a: None)
    monkeypatch.setattr(bundle, '_inputs', lambda *a: inputs)
    monkeypatch.setattr(bundle, '_recheck', lambda *a: None)
    monkeypatch.setattr(bundle, 'validate_complete_tables', lambda *a: None)
    roots = []

    def derive(selected, scratch):
        roots.append(scratch)
        assert directory not in scratch.parents
        (scratch / 'owned').write_text('temporary')
        return reconstructed

    monkeypatch.setattr(bundle, 'derive_tables', derive)
    collect = pl.LazyFrame.collect
    collected = []

    def tracked(lf, *args, **kwargs):
        result = collect(lf, *args, **kwargs)
        collected.append(result.schema)
        return result

    compare = bundle.ipums_parity.compare_ordered
    comparisons = []

    def ordered(expected, actual, **kwargs):
        assert isinstance(expected, pl.LazyFrame) and isinstance(actual, pl.LazyFrame)
        result = compare(expected, actual, chunk_size=7)
        comparisons.append(result)
        return result

    monkeypatch.setattr(pl.LazyFrame, 'collect', tracked)
    monkeypatch.setattr(bundle.ipums_parity, 'compare_ordered', ordered)

    def verify():
        return bundle.verify_bundle(directory, tmp_path, expected_outputs_sha256=pin,
                                    mapping_run='mapping',
                                    expected_mapping_outputs_sha256='a' * 64)

    if defect is None:
        assert verify()['status'] == 'verified'
        assert len(comparisons) == 8
        assert all(row['values_equal'] and row['schema_equal'] for row in comparisons)
    elif defect.startswith('report_'):
        with pytest.raises(ValueError, match='substantive report differs'):
            verify()
        assert comparisons == []
    else:
        with pytest.raises(ValueError, match='replicate_estimates: ordered table differs'):
            verify()
        assert comparisons
        assert comparisons[-1]['actual_rows'] == 160
        assert comparisons[-1]['expected_rows'] == (161 if defect == 'tail' else 160)
    assert not any(schema in [contract.SUPPORT_SCHEMA, contract.REPLICATE_SCHEMA, TARGET_SCHEMA]
                   for schema in collected), 'reconstruction materialized a published table'
    if not (defect and defect.startswith('report_')):
        assert roots
    assert all(not root.exists() for root in roots)
    assert before == {p.name: p.read_bytes() for p in directory.iterdir()}
