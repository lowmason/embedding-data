'''Exact aggregate spill ordering, bounded expansion and caller-owned lifetime.'''

import errno
from dataclasses import replace
from pathlib import Path

import polars as pl
import pytest
from acs_target_fixtures import estimation_rows, weights
from polars.testing import assert_frame_equal

from embedding_data import acs_target_estimation as estimation
from embedding_data.acs_target_contract import PRODUCTS

def records():
    return [dict(year=2023, a='a', b='A', flags=['z', 'a'], **weights('0.1', {37: '-2'})),
            dict(year=2023, a='a', b='A', flags=['b', 'a'], **weights('0.2', {37: '2'})),
            dict(year=2024, a='a', b='B', **weights('3', {37: '-1'})),
            *[dict(year=2023 + i % 2, a=f'a{i}', b=f'B{i}', **weights(str(i + 1)))
              for i in range(5)]]


def spill(rows, scratch, **kwargs):
    helper = getattr(estimation, '_aggregate_native_spilled', None)
    assert helper is not None, 'native complete-key spill helper is missing'
    return helper(rows, scratch, **kwargs)


def long_schema(keys):
    return {**{key: pl.String for key in keys}, 'component_year': pl.Int64,
            'n_unweighted': pl.UInt64, 'flags': pl.List(pl.String), 'replicate': pl.UInt8,
            'sum_exact': pl.String, 'fractional_support_mass': pl.Float64}


@pytest.mark.parametrize('batch_size', [1, 3, 128])
@pytest.mark.parametrize('canonical', [False, True])
def test_exact_order_schemas_hand_totals_and_bounded_long_batches(tmp_path, monkeypatch,
                                                               batch_size, canonical):
    rows = estimation_rows(records())
    if canonical:
        product = next(p for p in PRODUCTS if p.family == rows.product.family
                       and p.view == 'canonical' and p.base_universe == rows.product.base_universe
                       and p.evidence_policy == rows.product.evidence_policy)
        metadata = [{'component_year': year, 'native_coverage_n': 9,
                     'native_coverage_mass': 99.} for year in [0, 2023, 2024]]
        dtype = pl.List(pl.Struct({'component_year': pl.Int64, 'native_coverage_n': pl.UInt64,
                                  'native_coverage_mass': pl.Float64}))
        rows = replace(rows, product=product, members=rows.members.with_columns(
            pl.lit(metadata, dtype=dtype).alias('_canonical_native_coverage')))
    expected = estimation.aggregate_native(rows)
    original_sink = pl.LazyFrame.sink_parquet
    long_sizes = []
    wide_paths = []

    def guarded_sink(frame, path, *args, **kwargs):
        schema = frame.collect_schema()
        if 'sum_exact' in schema:
            size = frame.select(pl.len()).collect().item()
            assert size <= batch_size * 3 * 81
            long_sizes.append(size)
        elif 'PERWT' in schema:
            wide_paths.append(Path(path.name))
        return original_sink(frame, path, *args, **kwargs)

    monkeypatch.setattr(pl.LazyFrame, 'sink_parquet', guarded_sink)
    actual = spill(rows, tmp_path, batch_size=batch_size)
    assert long_sizes and len(wide_paths) == 4
    for name in ['cells', 'denominators', 'diagnostics']:
        assert_frame_equal(getattr(actual, name).collect(), getattr(expected, name).collect(),
                           check_exact=True)
    assert dict(actual.cells.collect_schema()) == long_schema(estimation.PAIR_KEYS)
    denominator_schema = long_schema(estimation.DENOMINATOR_KEYS)
    if canonical:
        denominator_schema.update(native_coverage_n=pl.UInt64, native_coverage_mass=pl.Float64)
    assert list(actual.denominators.collect_schema().items()) == list(denominator_schema.items())
    cells = actual.cells.collect().filter(pl.col('unit_b').str.ends_with(':A'))
    assert cells.filter(pl.col('replicate') == 0)['sum_exact'].to_list() == ['0.3', '0.3', '0']
    assert cells.filter(pl.col('replicate') == 37)['sum_exact'].to_list() == ['0', '0', '0']
    assert cells.filter(pl.col('replicate') == 0)['n_unweighted'].to_list() == [2, 2, 0]
    assert cells.filter(pl.col('component_year') == 0)['replicate'].to_list() == list(range(81))
    assert cells.row(0, named=True)['flags'] == ['a', 'b', 'z']
    pooled = cells.filter(pl.col('component_year') == 0)
    assert pooled['sum_exact'].to_list() == [
        '0' if replicate == 37 else '0.3' for replicate in range(81)]
    denom = actual.denominators.collect().filter(pl.col('unit_a').str.ends_with(':a'))
    assert denom.filter(pl.col('replicate') == 0)['sum_exact'].to_list() == ['3.3', '0.3', '3']
    assert denom.filter(pl.col('replicate') == 37)['sum_exact'].to_list() == ['-1', '0', '-1']
    for path in wide_paths:
        wide = pl.read_parquet(path)
        assert 'source_row' not in wide.columns and 'source_parquet_sha256' not in wide.columns
        assert all(wide.schema[name] == pl.Decimal(38, 1) for name in estimation.WEIGHT_NAMES)
    expected_estimates = estimation.estimate(expected)
    for name, frame in estimation.estimate(actual).items():
        assert_frame_equal(frame.collect(), expected_estimates[name].collect(), check_exact=True)


@pytest.mark.parametrize('empty', [False, True])
def test_empty_and_zero_products(tmp_path, empty):
    rows = estimation_rows([] if empty else [dict(year=2023, a='a', b='b', **weights('0'))])
    actual, expected = spill(rows, tmp_path), estimation.aggregate_native(rows)
    for name in ['cells', 'denominators', 'diagnostics']:
        assert_frame_equal(getattr(actual, name).collect(), getattr(expected, name).collect(),
                           check_exact=True)


def test_source_unlink_before_estimate_and_readback(tmp_path):
    rows = estimation_rows(records())
    source = tmp_path / 'source.parquet'
    rows.members.collect().write_parquet(source)
    expected = estimation.estimate(estimation.aggregate_native(rows))
    source_rows = replace(rows, members=pl.scan_parquet(source),
                          diagnostics=pl.scan_parquet(source).select(pl.len().alias('count')))
    actual = spill(source_rows, tmp_path, batch_size=1)
    source.unlink()
    assert actual.diagnostics.collect()['count'].item() == len(records())
    for name, frame in estimation.estimate(actual).items():
        path = tmp_path / f'{name}.parquet'
        frame.sink_parquet(path)
        assert_frame_equal(pl.read_parquet(path), expected[name].collect(), check_exact=True)


@pytest.mark.parametrize('key', estimation.PAIR_KEYS)
def test_null_keys_rejected_before_batch_selection(tmp_path, key):
    rows = estimation_rows(records())
    members = rows.members.with_columns(pl.lit(None, dtype=pl.String).alias(key))
    rows = replace(rows, members=members)
    with pytest.raises(ValueError, match='null aggregate join key'):
        estimation.estimate(estimation.aggregate_native(rows))
    with pytest.raises(ValueError, match='null aggregate join key'):
        spill(rows, tmp_path, batch_size=1)
    assert list(tmp_path.iterdir()) == []


def test_exclusive_child_and_symlink_safety(tmp_path):
    rows = estimation_rows(records())
    spill(rows, tmp_path)
    child = next(tmp_path.iterdir())
    sentinel = child / 'sentinel'
    sentinel.write_text('preserve')
    with pytest.raises(FileExistsError):
        spill(rows, tmp_path)
    assert sentinel.read_text() == 'preserve'
    link = tmp_path / 'link'
    link.symlink_to(child, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        spill(rows, link)
    assert sentinel.read_text() == 'preserve'


@pytest.mark.parametrize('failure_call', [6, 8, 20])
def test_io_failure_cleans_only_owned_child(tmp_path, monkeypatch, failure_call):
    sentinel = tmp_path / 'sentinel'
    sentinel.write_text('preserve')
    original = pl.LazyFrame.sink_parquet
    calls = 0

    def fail(frame, path, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == failure_call:
            raise OSError(errno.ENOSPC, 'synthetic no space')
        return original(frame, path, *args, **kwargs)

    monkeypatch.setattr(pl.LazyFrame, 'sink_parquet', fail)
    with pytest.raises(OSError, match='synthetic no space'):
        spill(estimation_rows(records()), tmp_path, batch_size=1)
    assert list(tmp_path.iterdir()) == [sentinel]
    assert sentinel.read_text() == 'preserve'


@pytest.mark.parametrize('point, message', [('-1', 'negative full'), ('9' * 38, 'overflow')])
def test_negative_and_overflow_rejection(tmp_path, point, message):
    rows = estimation_rows([dict(year=2023, a='a', b='b', **weights(point))] * 2)
    with pytest.raises(ValueError, match=message):
        spill(rows, tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('batch_size', [0, -1, True, 1.5])
def test_invalid_batch_size_rejected_without_artifacts(tmp_path, batch_size):
    with pytest.raises(ValueError, match='batch_size'):
        spill(estimation_rows(records()), tmp_path, batch_size=batch_size)
    assert not list(tmp_path.iterdir())


def test_aggregate_sink_refuses_existing_and_symlink_files(tmp_path):
    destination = tmp_path / 'occupied.parquet'
    destination.write_bytes(b'sentinel')
    with pytest.raises(FileExistsError):
        estimation._sink_native_aggregate(pl.LazyFrame({'aggregate': [1]}), destination)
    link = tmp_path / 'link.parquet'
    link.symlink_to(destination)
    with pytest.raises(ValueError, match='symlink'):
        estimation._sink_native_aggregate(pl.LazyFrame({'aggregate': [1]}), link)
    assert destination.read_bytes() == b'sentinel'
