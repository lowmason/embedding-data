'''Owned synthetic qualification of exact private ordered consolidation.'''

import importlib
from decimal import Decimal

import polars as pl
import pytest

SCHEMA = {'key': pl.String, 'tie': pl.UInt8, 'signed': pl.Float64,
          'exact': pl.Decimal(38, 2), 'labels': pl.List(pl.String)}
KEYS = ['key', 'tie']


def merger():
    try:
        return importlib.import_module('embedding_data.acs_target_tables')
    except ModuleNotFoundError:
        pytest.fail('private bounded ordered merge is missing')


def synthetic_manifest(module, root, frames):
    manifest = root / 'fragments.jsonl'
    with manifest.open('x') as out:
        for index, frame in enumerate(frames):
            path = root / f'input-{index:05d}.parquet'
            frame.write_parquet(path, row_group_size=3)
            module.append_fragment(out, path, SCHEMA, KEYS, frame.height,
                frame.select(KEYS).row(0) if frame.height else None,
                frame.select(KEYS).row(-1) if frame.height else None)
    return manifest


def test_multilevel_nulls_signed_decimal_lists_stable_duplicate_ties(tmp_path):
    module = merger()
    frames = []
    for index in range(35):
        frames.append(pl.DataFrame([
            {'key': key, 'tie': 37, 'signed': -float(index),
             'exact': Decimal('123456789.25'), 'labels': [str(index), 'z', 'a', 'z']}
            for key in [None, 'a', 'z']
        ], schema=SCHEMA))
    manifest = synthetic_manifest(module, tmp_path, frames)
    original = {path: path.read_bytes() for path in tmp_path.glob('input-*')}
    result = module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS)
    actual = pl.read_parquet(result.path)
    expected = pl.concat(frames).sort(KEYS, nulls_last=False, maintain_order=True)
    assert actual.equals(expected)
    assert actual.schema == expected.schema
    assert result.row_count == 105
    assert all(path.read_bytes() == payload for path, payload in original.items())


def test_empty_typed_result(tmp_path):
    module = merger()
    manifest = synthetic_manifest(module, tmp_path, [pl.DataFrame(schema=SCHEMA)])
    result = module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS)
    assert pl.read_parquet(result.path).equals(pl.DataFrame(schema=SCHEMA))


@pytest.mark.parametrize('corruption', ['order', 'schema', 'count', 'boundary'])
def test_full_input_validation_refuses_without_result(tmp_path, corruption):
    module = merger()
    frame = pl.DataFrame({'key': ['a', 'b'], 'tie': [1, 2], 'signed': [-1., 0.],
        'exact': [Decimal('1.00'), Decimal('2.00')], 'labels': [[], ['x']]}, schema=SCHEMA)
    manifest = synthetic_manifest(module, tmp_path, [frame])
    path = tmp_path / 'input-00000.parquet'
    if corruption == 'order':
        frame.reverse().write_parquet(path)
    elif corruption == 'schema':
        frame.with_columns(pl.col('tie').cast(pl.UInt64)).write_parquet(path)
    else:
        import json
        record = json.loads(manifest.read_text())
        record['row_count' if corruption == 'count' else 'first_key'] = (
            3 if corruption == 'count' else ['wrong', 1])
        manifest.write_text(json.dumps(record) + '\n')
    with pytest.raises(ValueError):
        module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS)
    assert not (tmp_path / 'result.parquet').exists()
    assert path.exists()


def test_product_handoff_precedes_union_and_preserves_small_oracle(tmp_path, monkeypatch):
    from acs_target_fixtures import estimation_rows, weights

    from embedding_data import acs_target_estimation as estimation
    from embedding_data import acs_target_tables as tables
    from embedding_data.acs_target_contract import RESIDUAL_SCHEMA
    rows = estimation_rows([dict(year=2023, a='a', b=str(index), flags=[],
                                **weights('10', {37: '-2'})) for index in range(19)])
    aggregates = estimation.aggregate_native(rows)
    from dataclasses import replace
    aggregates = replace(aggregates,
        cells=aggregates.cells.sort([*estimation.PAIR_KEYS, 'component_year', 'replicate']),
        denominators=aggregates.denominators.sort(
            [*estimation.DENOMINATOR_KEYS, 'component_year', 'replicate']))
    expected = estimation.estimate(aggregates)
    helper = getattr(estimation, '_spill_estimate_fragments', None)
    assert helper is not None, 'descriptor handoff must occur before scan union'
    manifests = helper(aggregates, tmp_path, batch_size=1)
    assert set(manifests) == {'targets', 'support', 'replicates'}
    for label, manifest in manifests.items():
        assert isinstance(manifest, type(tmp_path))
        assert len(manifest.read_text().splitlines()) >= 19
    def forbidden(*args, **kwargs):
        pytest.fail('product compaction must not construct public scan union')
    monkeypatch.setattr(estimation, '_spill_estimates', forbidden)
    if hasattr(tables, '_spill_estimates'):
        monkeypatch.setattr(tables, '_spill_estimates', forbidden)
    product_root = tmp_path / 'product'
    product_root.mkdir()
    records = tables._spill_product_outputs(aggregates,
        pl.LazyFrame(schema=RESIDUAL_SCHEMA), product_root)
    labels = {'targets_observed': 'targets', 'target_support': 'support',
              'replicate_estimates': 'replicates'}
    for record in records:
        if record.name in labels:
            oracle = expected[labels[record.name]].collect()
            assert pl.read_parquet(record.path).equals(oracle)


@pytest.fixture(autouse=True)
def independent_owned_fence(tmp_path, monkeypatch):
    import builtins
    import ctypes
    import io
    import os
    import socket
    import subprocess
    from pathlib import Path
    owned = tmp_path.resolve()
    def checked(path):
        if isinstance(path, int):
            return
        candidate = Path(path).absolute()
        assert candidate.is_relative_to(owned), f'write outside independently owned root: {path}'
    for namespace in (builtins, io):
        original = namespace.open
        def guarded(path, mode='r', *args, _original=original, **kwargs):
            if any(char in mode for char in 'wax+'):
                checked(path)
            return _original(path, mode, *args, **kwargs)
        monkeypatch.setattr(namespace, 'open', guarded)
    original_open = os.open
    def guarded_os_open(path, flags, *args, **kwargs):
        if flags & (os.O_CREAT | os.O_WRONLY | os.O_RDWR | os.O_TRUNC):
            checked(path)
        return original_open(path, flags, *args, **kwargs)
    monkeypatch.setattr(os, 'open', guarded_os_open)
    original_link = os.link
    def guarded_link(source, destination, *args, **kwargs):
        checked(source)
        checked(destination)
        return original_link(source, destination, *args, **kwargs)
    monkeypatch.setattr(os, 'link', guarded_link)
    def forbidden(*args, **kwargs):
        pytest.fail('external process/network/native access is forbidden')
    for namespace, name in ((subprocess, 'Popen'), (os, 'system'), (os, 'fork'),
                            (ctypes, 'CDLL'), (socket, 'create_connection')):
        monkeypatch.setattr(namespace, name, forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)


@pytest.mark.parametrize('budget,limit,reason', [
    ('DESCRIPTOR_BYTES', 128, 'descriptor-record-bytes'),
    ('FOOTER_BYTES', 100, 'encoded-footer-bytes'),
    ('INPUT_GROUPS', 1, 'input-row-groups'),
    ('CHUNK_BYTES', 1, 'declared-column-chunk-bytes'),
    ('GROUP_BYTES', 1, 'declared-row-group-bytes'),
    ('BATCH_BYTES', 1, 'input-batch-backing-bytes'),
])
def test_actual_input_and_descriptor_budget_refusals(tmp_path, monkeypatch, budget, limit, reason):
    module = merger()
    frame = pl.DataFrame({'key': ['a'] * 7, 'tie': [1] * 7, 'signed': [-1.] * 7,
        'exact': [Decimal('1.00')] * 7, 'labels': [['x']] * 7}, schema=SCHEMA)
    manifest = synthetic_manifest(module, tmp_path, [frame])
    original = (tmp_path / 'input-00000.parquet').read_bytes()
    monkeypatch.setattr(module, budget, limit)
    with pytest.raises(ValueError, match=reason):
        module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS)
    assert not (tmp_path / 'result.parquet').exists()
    assert not (tmp_path / 'result.parquet.merge').exists()
    assert (tmp_path / 'input-00000.parquet').read_bytes() == original


def test_independent_active_readers_and_actual_batch_bounds(tmp_path, monkeypatch):
    import pyarrow.parquet as pq
    module = merger()
    frame = pl.DataFrame({'key': ['a'] * 13, 'tie': [1] * 13, 'signed': [-1.] * 13,
        'exact': [Decimal('1.00')] * 13, 'labels': [['x']] * 13}, schema=SCHEMA)
    manifest = synthetic_manifest(module, tmp_path, [frame] * 35)
    original = pq.ParquetFile
    counts = dict(active=0, maximum=0, batches=0)
    class ObservedReader:
        def __init__(self, *args, **kwargs):
            self.reader = original(*args, **kwargs)
            self.closed = False
            counts['active'] += 1
            counts['maximum'] = max(counts['maximum'], counts['active'])
        def __getattr__(self, name):
            return getattr(self.reader, name)
        def iter_batches(self, *args, **kwargs):
            assert kwargs['use_threads'] is False
            for batch in self.reader.iter_batches(*args, **kwargs):
                counts['batches'] += 1
                assert batch.num_rows <= module.BATCH_ROWS
                assert batch.get_total_buffer_size() <= module.BATCH_BYTES
                yield batch
        def close(self, *args, **kwargs):
            if not self.closed:
                counts['active'] -= 1
                self.closed = True
            self.reader.close(*args, **kwargs)
    monkeypatch.setattr(pq, 'ParquetFile', ObservedReader)
    module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS)
    assert counts['active'] == 0
    # Count preflight/witness readers too; 16 is the combined bound.
    assert counts['maximum'] <= module.FAN_IN
    assert counts['batches'] > 35


def test_late_final_writer_group_refusal_closes_and_preserves(tmp_path, monkeypatch):
    module = merger()
    frame = pl.DataFrame({'key': ['a'] * 40, 'tie': [1] * 40, 'signed': [-1.] * 40,
        'exact': [Decimal('1.00')] * 40, 'labels': [['x']] * 40}, schema=SCHEMA)
    manifest = synthetic_manifest(module, tmp_path, [frame])
    monkeypatch.setattr(module, 'GROUP_ROWS', 8)
    monkeypatch.setattr(module, 'BATCH_ROWS', 4)
    monkeypatch.setattr(module, 'WRITER_GROUPS', 3)
    events = []
    with pytest.raises(ValueError, match='writer-row-groups'):
        module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS,
                               telemetry=events.append)
    assert sum(event['event'] == 'writer-group' for event in events) == 3
    assert sum(event['event'] == 'reader-open' for event in events) == sum(
        event['event'] == 'reader-close' for event in events)
    assert not (tmp_path / 'result.parquet').exists()


def test_single_oversized_row_refuses_actual_backing_store(tmp_path):
    module = merger()
    frame = pl.DataFrame({'key': ['a'], 'tie': [1], 'signed': [-1.],
        'exact': [Decimal('1.00')], 'labels': [['x' * (module.BATCH_BYTES + 1)]]}, schema=SCHEMA)
    manifest = synthetic_manifest(module, tmp_path, [frame])
    with pytest.raises(ValueError, match='input-batch-backing-bytes'):
        module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS)
    assert not (tmp_path / 'result.parquet').exists()


def test_all_published_scalar_widths_nullable_lists_and_float_bits(tmp_path):
    module = merger()
    schema = {'key': pl.String, 'u8': pl.UInt8, 'u64': pl.UInt64, 'i': pl.Int64,
              'b': pl.Boolean, 'f': pl.Float64, 'd': pl.Decimal(38, 4),
              's': pl.String, 'ls': pl.List(pl.String), 'lu': pl.List(pl.UInt8)}
    frame = pl.DataFrame([
        [None, 255, 2**64 - 1, -(2**63), True, -0., Decimal('-123.4500'), None,
         ['z', 'a', 'z'], [0, 37, 80]],
        ['a', 0, 0, 0, None, None, None, '', [], []],
        ['z', 37, 1, 1, False, -2.5, Decimal('0.0001'), 'null', None, None],
    ], schema=schema, orient='row')
    path = tmp_path / 'values.parquet'
    with path.open('xb') as out:
        frame.write_parquet(out)
    manifest = tmp_path / 'values.jsonl'
    with manifest.open('x') as out:
        module.append_fragment(out, path, schema, ['key'], 3, (None,), ('z',))
    result = module.merge_fragments(manifest, tmp_path / 'result.parquet', schema, ['key'])
    actual = pl.read_parquet(result.path)
    assert actual.equals(frame)
    import math
    assert math.copysign(1, actual['f'][0]) == -1


def test_footer_refusal_precedes_arrow_construction(tmp_path, monkeypatch):
    import pyarrow.parquet as pq
    module = merger()
    manifest = synthetic_manifest(module, tmp_path, [pl.DataFrame(schema=SCHEMA)])
    monkeypatch.setattr(module, 'FOOTER_BYTES', 1)
    def forbidden(*args, **kwargs):
        pytest.fail('oversized footer must be refused before reader construction')
    monkeypatch.setattr(pq, 'ParquetFile', forbidden)
    with pytest.raises(ValueError, match='encoded-footer-bytes'):
        module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS)


def test_oversized_dictionary_chunk_is_declared_before_decode(tmp_path, monkeypatch):
    import pyarrow.parquet as pq
    module = merger()
    frame = pl.DataFrame({'key': ['a', 'b'], 'tie': [1, 2], 'signed': [-1., 0.],
        'exact': [Decimal('1.00'), Decimal('2.00')],
        'labels': [['x' * 4096], ['y' * 4096]]}, schema=SCHEMA)
    path = tmp_path / 'dictionary.parquet'
    with path.open('xb') as out:
        pq.write_table(frame.to_arrow(), out, use_dictionary=True)
    with path.open('rb') as source:
        metadata = pq.read_metadata(source)
        assert metadata.row_group(0).column(4).has_dictionary_page
    manifest = tmp_path / 'dictionary.jsonl'
    with manifest.open('x') as out:
        module.append_fragment(out, path, SCHEMA, KEYS, 2, ('a', 1), ('b', 2))
    monkeypatch.setattr(module, 'CHUNK_BYTES', 1024)
    with pytest.raises(ValueError, match='declared-column-chunk-bytes'):
        module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS)


def test_descriptor_overflow_refuses_before_append(tmp_path):
    module = merger()
    path = tmp_path / 'manifest.jsonl'
    with path.open('x') as out:
        with pytest.raises(ValueError, match='descriptor-record-bytes'):
            module.append_fragment(out, tmp_path / 'never-opened.parquet', SCHEMA, KEYS,
                                   1, ('x' * module.DESCRIPTOR_BYTES, 1), ('z', 1))
    assert path.read_bytes() == b''


def test_late_preappend_footer_budget_refuses_before_actual_writer_append(tmp_path, monkeypatch):
    module = merger()
    frame = pl.DataFrame({'key': ['a'] * 40, 'tie': [1] * 40, 'signed': [-1.] * 40,
        'exact': [Decimal('1.00')] * 40, 'labels': [['x']] * 40}, schema=SCHEMA)
    manifest = synthetic_manifest(module, tmp_path, [frame])
    monkeypatch.setattr(module, 'GROUP_ROWS', 8)
    monkeypatch.setattr(module, 'BATCH_ROWS', 4)
    events = []
    def telemetry(event):
        events.append(event)
        if event['event'] == 'writer-group':
            # Allow footer parsing, but reject the next prospective cumulative append.
            monkeypatch.setattr(module, 'FOOTER_BYTES', event['footer_bound'] + 1)
    with pytest.raises(ValueError, match='prospective-writer-footer-bytes'):
        module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS,
                               telemetry=telemetry)
    assert sum(event['event'] == 'writer-group' for event in events) == 1
    assert not (tmp_path / 'result.parquet').exists()


def test_final_footer_envelope_is_checked_before_descriptor_exposure(tmp_path, monkeypatch):
    module = merger()
    frame = pl.DataFrame({'key': ['a'], 'tie': [1], 'signed': [-1.],
        'exact': [Decimal('1.00')], 'labels': [['x']]}, schema=SCHEMA)
    manifest = synthetic_manifest(module, tmp_path, [frame])
    original = module._Writer.close
    def corrupt_bound(writer):
        original(writer)
        writer.footer_bound = 1
    monkeypatch.setattr(module._Writer, 'close', corrupt_bound)
    with pytest.raises(ValueError, match='serialized-writer-footer-envelope'):
        module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS)
    assert not (tmp_path / 'result.parquet').exists()


def test_actual_writer_failure_closes_all_readers_and_cleans_only_owned(tmp_path, monkeypatch):
    import pyarrow.parquet as pq
    module = merger()
    frame = pl.DataFrame({'key': ['a'], 'tie': [1], 'signed': [-1.],
        'exact': [Decimal('1.00')], 'labels': [['x']]}, schema=SCHEMA)
    manifest = synthetic_manifest(module, tmp_path, [frame] * 17)
    sentinel = tmp_path / 'retained-failure'
    sentinel.write_text('preserve')
    original = pq.ParquetWriter.write_table
    def fail(writer, *args, **kwargs):
        if not str(getattr(writer.where, 'name', '')).endswith('.witness'):
            raise OSError('owned late writer failure')
        return original(writer, *args, **kwargs)
    monkeypatch.setattr(pq.ParquetWriter, 'write_table', fail)
    events = []
    with pytest.raises(OSError, match='owned late writer failure'):
        module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS,
                               telemetry=events.append)
    assert sum(event['event'] == 'reader-open' for event in events) == sum(
        event['event'] == 'reader-close' for event in events)
    assert sentinel.read_text() == 'preserve'
    assert len(list(tmp_path.glob('input-*'))) == 17
    assert not (tmp_path / 'result.parquet.merge').exists()


def test_metadata_guidance_uses_each_group_width_before_requesting_batches(tmp_path, monkeypatch):
    import pyarrow.parquet as pq
    module = merger()
    frame = pl.DataFrame({'key': ['a'] * 512, 'tie': [1] * 512, 'signed': [-1.] * 512,
        'exact': [Decimal('1.00')] * 512,
        'labels': [['x' * 1024] * 16] * 512}, schema=SCHEMA)
    manifest = synthetic_manifest(module, tmp_path, [frame])
    original = pq.ParquetFile.iter_batches
    requested = []
    def observed(reader, *args, **kwargs):
        requested.append(kwargs['batch_size'])
        return original(reader, *args, **kwargs)
    monkeypatch.setattr(pq.ParquetFile, 'iter_batches', observed)
    result = module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS)
    assert pl.read_parquet(result.path).equals(frame)
    assert max(requested) <= 256


def test_wide_output_flushes_before_unchanged_column_chunk_budget(tmp_path):
    module = merger()
    frame = pl.DataFrame({'key': ['a'] * 512, 'tie': [1] * 512, 'signed': [-1.] * 512,
        'exact': [Decimal('1.00')] * 512,
        'labels': [['x' * 1024] * 16] * 512}, schema=SCHEMA)
    manifest = synthetic_manifest(module, tmp_path, [frame] * 5)
    events = []
    result = module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS,
                                   telemetry=events.append)
    assert pl.read_parquet(result.path).equals(pl.concat([frame] * 5))
    assert sum(event['event'] == 'writer-group' for event in events) > 1


def test_wide_pending_rows_are_bounded_before_arrow_construction(tmp_path, monkeypatch):
    import pyarrow as pa
    module = merger()
    frame = pl.DataFrame({'key': [f'{i:02d}' for i in range(12)], 'tie': [1] * 12,
        'signed': [-1.] * 12, 'exact': [Decimal('1.00')] * 12,
        'labels': [['x' * (1024**2)]] * 12}, schema=SCHEMA)
    manifest = synthetic_manifest(module, tmp_path, [frame])
    original = pa.RecordBatch
    constructions = []
    class ProxyMeta(type):
        def __getattr__(cls, name):
            return getattr(original, name)
    class ObservedBatch(metaclass=ProxyMeta):
        @staticmethod
        def from_pylist(rows, *args, **kwargs):
            # Independent payload lower bound BEFORE the real Arrow construction.
            payload = sum(len(label.encode()) for row in rows for label in row['labels'])
            assert payload <= module.BATCH_BYTES, 'oversized pending Python payload'
            batch = original.from_pylist(rows, *args, **kwargs)
            constructions.append((len(rows), payload, batch.get_total_buffer_size()))
            assert batch.get_total_buffer_size() <= module.BATCH_BYTES
            return batch
    monkeypatch.setattr(pa, 'RecordBatch', ObservedBatch)
    result = module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS)
    assert pl.read_parquet(result.path).equals(frame)
    assert len(constructions) > 1
    assert max(count for count, _, _ in constructions) < 12


def test_independently_traced_live_python_pending_payload_never_exceeds_budget(tmp_path):
    import sys
    module = merger()
    frame = pl.DataFrame({'key': [f'{i:02d}' for i in range(12)], 'tie': [1] * 12,
        'signed': [-1.] * 12, 'exact': [Decimal('1.00')] * 12,
        'labels': [['x' * (1024**2)]] * 12}, schema=SCHEMA)
    manifest = synthetic_manifest(module, tmp_path, [frame])
    observed = []
    def trace(frame, event, argument):
        if frame.f_code is module._merge_group.__code__ and event == 'line':
            pending = frame.f_locals.get('rows', [])
            payload = sum(len(label) for row in pending for label in row[-1])
            observed.append(payload)
            assert payload <= module.BATCH_BYTES, 'live pending payload exceeds byte budget'
        return trace
    previous = sys.gettrace()
    sys.settrace(trace)
    try:
        result = module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS)
    finally:
        sys.settrace(previous)
    assert pl.read_parquet(result.path).equals(frame)
    assert observed and max(observed) <= module.BATCH_BYTES


def test_python_staging_includes_conversion_dicts_before_construction(tmp_path, monkeypatch):
    import sys

    import pyarrow as pa
    module = merger()
    frame = pl.DataFrame({'key': [f'{i:02d}' for i in range(20)], 'tie': [1] * 20,
        'signed': [-1.] * 20, 'exact': [Decimal('1.00')] * 20,
        'labels': [['short', 'list']] * 20}, schema=SCHEMA)
    manifest = synthetic_manifest(module, tmp_path, [frame])
    monkeypatch.setattr(module, 'PYTHON_STAGING_BYTES', 4000)
    original = pa.RecordBatch
    observed = []
    def deep(value):
        return sys.getsizeof(value) + (sum(deep(child) for child in value)
                                       if isinstance(value, (tuple, list)) else 0)
    class ProxyMeta(type):
        def __getattr__(cls, name):
            return getattr(original, name)
    class ObservedBatch(metaclass=ProxyMeta):
        @staticmethod
        def from_pylist(records, *args, **kwargs):
            pending = sys._getframe(1).f_locals['rows']
            retained = deep(pending) + sys.getsizeof(records) + sum(
                sys.getsizeof(record) for record in records)
            observed.append(retained)
            assert retained <= module.PYTHON_STAGING_BYTES, 'conversion Python staging exceeds cap'
            return original.from_pylist(records, *args, **kwargs)
    monkeypatch.setattr(pa, 'RecordBatch', ObservedBatch)
    result = module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS)
    assert pl.read_parquet(result.path).equals(frame)
    assert max(observed) <= 4000


def test_typed_prospective_buffer_bound_covers_all_scalar_and_list_edge_values():
    import pyarrow as pa
    module = merger()
    schema = pa.schema([('s', pa.large_string()), ('u', pa.uint64()), ('i', pa.int64()),
        ('u8', pa.uint8()), ('b', pa.bool_()), ('f', pa.float64()),
        ('d', pa.decimal128(38, 4)), ('ls', pa.large_list(pa.large_string())),
        ('lu', pa.large_list(pa.uint8()))])
    rows = [(None, 2**64 - 1, -(2**63), 255, True, -0., Decimal('-123.4500'),
             ['é', '😀', '', None], [0, 37, 80, None]),
            ('é😀', None, None, None, None, None, None, [], []),
            ('', 0, 0, 0, False, -2.5, Decimal('0.0001'), None, None)]
    bounds = [module._row_sizes(row, schema)[0] for row in rows]
    for count in range(1, len(rows) + 1):
        batch = pa.RecordBatch.from_pylist([dict(zip(schema.names, row, strict=True))
                                           for row in rows[:count]], schema=schema)
        assert batch.get_total_buffer_size() <= sum(bounds[:count])


@pytest.mark.parametrize('glyph', ['x', 'é', '😀'])
def test_prospective_python_bound_covers_container_capacity_and_utf8_cache(tmp_path, monkeypatch,
                                                                        glyph):
    import sys

    import pyarrow as pa
    module = merger()
    frame = pl.DataFrame({'key': ['a'], 'tie': [1], 'signed': [-1.],
        'exact': [Decimal('1.00')], 'labels': [[glyph * 2000]]}, schema=SCHEMA)
    manifest = synthetic_manifest(module, tmp_path, [frame])
    events = []
    original = pa.RecordBatch
    def deep(value):
        return sys.getsizeof(value) + (sum(deep(child) for child in value)
                                       if isinstance(value, (tuple, list)) else 0)
    class ProxyMeta(type):
        def __getattr__(cls, name):
            return getattr(original, name)
    class ObservedBatch(metaclass=ProxyMeta):
        @staticmethod
        def from_pylist(records, *args, **kwargs):
            caller = sys._getframe(1)
            pending = caller.f_locals['rows']
            result = original.from_pylist(records, *args, **kwargs)
            retained = deep(pending) + sys.getsizeof(records) + sum(
                sys.getsizeof(record) for record in records)
            if 'sizes' in caller.f_locals:
                retained += deep(caller.f_locals['sizes'])
            bound = [event for event in events if event['event'] == 'output-staging'][-1]
            assert retained <= bound['python_bytes'], 'prospective Python bound undercounts'
            assert retained <= module.PYTHON_STAGING_BYTES
            return result
    monkeypatch.setattr(pa, 'RecordBatch', ObservedBatch)
    result = module.merge_fragments(manifest, tmp_path / 'result.parquet', SCHEMA, KEYS,
                                   telemetry=events.append)
    assert pl.read_parquet(result.path).equals(frame)


def test_complete_production_inventory_matches_independent_acceptance_literal():
    import ast
    from pathlib import Path
    from types import SimpleNamespace
    root = Path(__file__).resolve().parents[1]
    def declared(file, name, namespace):
        tree = ast.parse((root / file).read_text())
        node = next(node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == name
                            for target in node.targets))
        return eval(compile(ast.Expression(node.value), '<literal-inventory>', 'eval'), namespace)
    upstream = declared('src/embedding_data/ipums_verification_run.py', 'SOFTWARE_FILES', {})
    mapping = declared('src/embedding_data/acs_mapping_inputs.py', 'SOFTWARE_FILES',
                       {'ipums_verification_run': SimpleNamespace(SOFTWARE_FILES=upstream)})
    actual = declared('src/embedding_data/acs_target_inputs.py', 'SOFTWARE_FILES',
                      {'acs_mapping_inputs': SimpleNamespace(SOFTWARE_FILES=mapping)})
    independent7 = declared('scripts/reconcile_stage8.py', 'STAGE7_NAMES', {})
    independent8 = declared('scripts/reconcile_stage8.py', 'EXECUTING_NAMES',
                            {'STAGE7_NAMES': independent7})
    expected = declared('scripts/reconcile_stage9.py', 'expected_files',
        {'io': SimpleNamespace(stage8=SimpleNamespace(EXECUTING_NAMES=independent8))})
    assert set(actual) == expected


def test_merge_executes_inside_existing_authenticated_tables_module():
    from embedding_data import acs_target_tables as module
    assert module.merge_fragments.__module__ == module.__name__
    assert importlib.util.find_spec('embedding_data.acs_target_ordered_merge') is None
