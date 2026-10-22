'''Assemble the fixed ACS products within one authenticated source scan lifetime.'''

import heapq
import json
import shutil
import sys
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from embedding_data import ipums_parity, target_io
from embedding_data.acs_mapping_io import safe_path
from embedding_data.acs_target_contract import (
    AUXILIARY_KEYS,
    AUXILIARY_SCHEMAS,
    CELL_KEY_COLUMNS,
    PRODUCTS,
    RESIDUAL_SCHEMA,
    STAT_KEY_COLUMNS,
    TARGET_TABLES,
    _validate_key_order,
    _validation_partitions,
    observed_counterpart,
    validate_cross_tables,
)
from embedding_data.acs_target_estimation import (
    _ESTIMATE_DESCRIPTOR_BYTES as DESCRIPTOR_BYTES,
)
from embedding_data.acs_target_estimation import (
    _aggregate_native_spilled,
    _append_estimate_fragment,
    _spill_estimate_fragments,
)
from embedding_data.acs_target_inputs import SelectedTargets
from embedding_data.acs_target_membership import family_rows
from embedding_data.acs_target_projection import _allocate_area_mix_spilled, canonical_rows
from embedding_data.acs_target_rules import read_rules
from embedding_data.acs_target_units import build_units
from embedding_data.acs_target_weights import weighted_source
from embedding_data.target_contract import TARGET_KEY_COLUMNS, TARGET_SCHEMA, write_targets

FAN_IN = 16
BATCH_ROWS = 4096
BATCH_BYTES = 8 * 1024**2
PYTHON_STAGING_BYTES = 32 * 1024**2
FOOTER_BYTES = 64 * 1024**2
INPUT_GROUPS = 32768
CHUNK_BYTES = 32 * 1024**2
GROUP_BYTES = 64 * 1024**2
GROUP_ROWS = 16384
# Earlier private flushing leaves room below the mandatory decoded/chunk maxima.
# This target is not an encoded-size proof: witness preflight remains authoritative.
GROUP_TARGET_BYTES = 16 * 1024**2
WRITER_GROUPS = 32768
# A witness pays all variable metadata. Reserve layout-dependent integer growth:
# column: nine i64 + two i32 fields <=144 bytes with worst compact headers;
# group: four i64 + one i16 <=63 bytes. 256 also covers fixed framing slack.
COLUMN_LAYOUT_BYTES = 256
GROUP_LAYOUT_BYTES = 256
FILE_LAYOUT_BYTES = 256
_WRITER_OPTIONS = dict(use_dictionary=False, write_statistics=False, write_page_index=False,
    compression='NONE', column_encoding='PLAIN', data_page_version='1.0', store_schema=True,
    write_page_checksum=False)


@dataclass(frozen=True)
class MergedFragment:
    path: Path
    row_count: int
    first_key: tuple | None
    last_key: tuple | None
    schema: tuple


def _refuse(reason):
    raise ValueError('ordered-merge resource-budget: ' + reason)


def _emit(telemetry, event, **values):
    if telemetry is not None:
        telemetry(dict(event=event, **values))


def _key(values):
    return tuple((value is not None, value) for value in values)


def append_fragment(output, path, schema, keys, row_count, first_key, last_key):
    return _append_estimate_fragment(output, path, schema, keys, row_count, first_key, last_key,
                                     descriptor_bytes=DESCRIPTOR_BYTES)


def _records(manifest, schema, keys):
    safe_path(manifest)
    with manifest.open('rb') as source:
        while raw := source.readline(DESCRIPTOR_BYTES + 1):
            if len(raw) > DESCRIPTOR_BYTES:
                _refuse('descriptor-record-bytes')
            record = json.loads(raw)
            if (set(record) != {'path', 'schema', 'keys', 'row_count', 'first_key', 'last_key'}
                    or record['schema'] != str(pl.Schema(schema)) or record['keys'] != keys):
                raise ValueError('ordered-merge descriptor schema/keys differ')
            name = record['path']
            if not isinstance(name, str) or Path(name).name != name or name in ('.', '..'):
                raise ValueError('ordered-merge unsafe fragment path')
            if (type(record['row_count']) is not int or record['row_count'] < 0
                    or any(value is not None and not isinstance(value, list)
                           for value in (record['first_key'], record['last_key']))):
                raise ValueError('ordered-merge malformed fragment descriptor')
            record['path'] = manifest.parent / name
            yield record


def _preflight(path, schema):
    safe_path(path)
    with path.open('rb') as source:
        size = source.seek(0, 2)
        if size < 12:
            raise ValueError('ordered-merge invalid parquet extent')
        source.seek(0)
        magic = source.read(4)
        source.seek(-8, 2)
        trailer = source.read(8)
        footer = int.from_bytes(trailer[:4], 'little')
        if magic != b'PAR1' or trailer[4:] != b'PAR1' or footer > size - 12:
            raise ValueError('ordered-merge invalid parquet footer')
        if footer > FOOTER_BYTES:
            _refuse('encoded-footer-bytes')
        reader = pq.ParquetFile(source, pre_buffer=False, memory_map=False,
            thrift_string_size_limit=FOOTER_BYTES, thrift_container_size_limit=FOOTER_BYTES)
        try:
            metadata = reader.metadata
            if metadata.serialized_size != footer:
                raise ValueError('ordered-merge inconsistent footer size')
            actual = pl.from_arrow(pa.Table.from_batches([], schema=reader.schema_arrow)).schema
            if actual != pl.Schema(schema):
                raise ValueError('ordered-merge fragment schema differs')
            if len(reader.schema_arrow.serialize()) > DESCRIPTOR_BYTES:
                _refuse('schema-metadata-bytes')
            _validate_schema(reader.schema_arrow)
            if metadata.num_row_groups > INPUT_GROUPS:
                _refuse('input-row-groups')
            maximum_width = 0
            for index in range(metadata.num_row_groups):
                group = metadata.row_group(index)
                declared = 0
                for column_index in range(group.num_columns):
                    column = group.column(column_index)
                    uncompressed, compressed = (column.total_uncompressed_size,
                                                column.total_compressed_size)
                    if uncompressed < 0 or compressed < 0 or (group.num_rows and not compressed):
                        raise ValueError('ordered-merge contradictory column size')
                    if uncompressed > CHUNK_BYTES:
                        _refuse('declared-column-chunk-bytes')
                    declared += uncompressed
                    if column.file_path:
                        raise ValueError('ordered-merge external column chunk')
                if group.total_byte_size < 0 or group.total_byte_size != declared:
                    raise ValueError('ordered-merge contradictory row-group size')
                if declared > GROUP_BYTES:
                    _refuse('declared-row-group-bytes')
                group_rows = max(group.num_rows, 1)
                maximum_width = max(maximum_width, (declared + group_rows - 1) // group_rows)
            return footer, metadata.num_rows, metadata.num_row_groups, maximum_width
        finally:
            reader.close(force=True)


def _validate_schema(schema):
    if schema.metadata:
        raise ValueError('ordered-merge unsupported Arrow schema metadata')
    for field in schema:
        dtype = field.type
        if field.metadata:
            raise ValueError('ordered-merge unsupported Arrow field metadata')
        if pa.types.is_large_list(dtype) or pa.types.is_list(dtype):
            child = dtype.value_field
            if child.metadata or not (pa.types.is_string(child.type)
                                      or pa.types.is_large_string(child.type)
                                      or pa.types.is_uint8(child.type)):
                raise ValueError('ordered-merge unsupported list type')
        elif not (pa.types.is_string(dtype) or pa.types.is_large_string(dtype)
                  or pa.types.is_integer(dtype) or pa.types.is_floating(dtype)
                  or pa.types.is_boolean(dtype) or pa.types.is_decimal128(dtype)):
            raise ValueError('ordered-merge unsupported Arrow type')


class _Reader:
    def __init__(self, record, schema, keys, telemetry):
        self.record, self.keys, self.telemetry = record, keys, telemetry
        self.source = self.reader = self.batches = self.batch = None
        self.count, self.previous, self.first = 0, None, None
        self.position = 0
        _, count, _, maximum_width = _preflight(record['path'], schema)
        if count != record['row_count']:
            raise ValueError('ordered-merge descriptor count differs')
        requested = BATCH_ROWS
        # Declared bytes only guide requests; actual backing buffers decide refusal.
        while requested > 1 and maximum_width * requested > BATCH_BYTES // 2:
            requested = max(1, requested // 2)
        try:
            self.source = record['path'].open('rb')
            self.reader = pq.ParquetFile(self.source, pre_buffer=False, memory_map=False)
            self.batches = self.reader.iter_batches(batch_size=requested, use_threads=False)
            _emit(telemetry, 'reader-open', path=str(record['path']))
        except BaseException:
            self.close()
            raise

    def next(self):
        if self.batch is None or self.position == self.batch.num_rows:
            self.batch = None
            try:
                batch = next(self.batches)
            except StopIteration:
                expected_last = self.record['last_key']
                if (self.count != self.record['row_count']
                        or self.first != self.record['first_key']
                        or (list(self.previous) if self.previous is not None else None)
                        != expected_last):
                    raise ValueError('ordered-merge descriptor boundaries/count differ')
                return None
            if batch.num_rows > BATCH_ROWS:
                _refuse('input-batch-rows')
            size = batch.get_total_buffer_size()
            _emit(self.telemetry, 'input-batch', rows=batch.num_rows, bytes=size)
            if size > BATCH_BYTES:
                _refuse('input-batch-backing-bytes')
            self.batch, self.position = batch, 0
        row = tuple(column[self.position].as_py() for column in self.batch.columns)
        self.position += 1
        indices = [self.batch.schema.get_field_index(name) for name in self.keys]
        key = tuple(row[index] for index in indices)
        if any(not (value is None or isinstance(value, (str, int))) for value in key):
            raise ValueError('ordered-merge unsupported key value')
        if self.previous is not None and _key(key) < _key(self.previous):
            raise ValueError('ordered-merge input is not ordered')
        if self.count == 0:
            self.first = list(key)
        self.previous = key
        self.count += 1
        return key, row

    def close(self):
        self.batches = self.batch = None
        if self.reader is not None:
            self.reader.close(force=True)
            self.reader = None
            _emit(self.telemetry, 'reader-close', path=str(self.record['path']))
        if self.source is not None:
            self.source.close()
            self.source = None


def _value_buffer_bound(value, dtype):
    # Per-row validity/initial-offset overpayment bounds fresh Arrow construction.
    # Variable lists are restricted by _validate_schema to one scalar child level.
    if pa.types.is_large_list(dtype) or pa.types.is_list(dtype):
        return 25 + (sum(_value_buffer_bound(child, dtype.value_type) for child in value)
                     if value is not None else 0)
    if pa.types.is_string(dtype) or pa.types.is_large_string(dtype):
        return 17 + (len(value.encode('utf-8')) if value is not None else 0)
    if pa.types.is_decimal128(dtype):
        return 17
    if pa.types.is_boolean(dtype):
        return 2
    return dtype.bit_width // 8 + 1


def _python_bytes(value):
    size = sys.getsizeof(value)
    if isinstance(value, (tuple, list)):
        # Count shared values repeatedly: conservative, with no growing identity set.
        size += sum(_python_bytes(child) for child in value)
    return size


def _row_sizes(row, schema):
    arrow_bytes = sum(_value_buffer_bound(value, field.type)
                      for value, field in zip(row, schema, strict=True))
    # Arrow conversion can retain a newly cached UTF8 representation on Python strings.
    # The entire prospective Arrow size overpays all such cache bytes conservatively.
    return arrow_bytes, _python_bytes(row) + arrow_bytes


class _Writer:
    def __init__(self, path, schema, keys, telemetry):
        self.path, self.schema, self.keys, self.telemetry = path, schema, keys, telemetry
        self.arrow_schema = pl.DataFrame(schema=schema).to_arrow().schema
        # Own both pending tuple-list and conversion dict-list, sharing value objects.
        self.conversion_bytes_per_row = (sys.getsizeof(dict.fromkeys(schema))
                                         + 2 * sys.getsizeof([None] * 4))
        _validate_schema(self.arrow_schema)
        if len(self.arrow_schema.serialize()) > DESCRIPTOR_BYTES:
            _refuse('schema-metadata-bytes')
        self.output = path.open('xb')
        self.writer = None
        try:
            self.writer = pq.ParquetWriter(self.output, self.arrow_schema, **_WRITER_OPTIONS)
        except BaseException:
            self.output.close()
            raise
        self.groups, self.rows, self.footer_bound = 0, 0, FILE_LAYOUT_BYTES
        self.first = self.last = None
        self.batches, self.batch_rows, self.batch_bytes = [], 0, 0

    def append(self, rows):
        arrow_bound = python_bound = 0
        for row in rows:
            arrow_bytes, python_bytes = _row_sizes(row, self.arrow_schema)
            arrow_bound += arrow_bytes
            python_bound += python_bytes + self.conversion_bytes_per_row
        if len(rows) > BATCH_ROWS or arrow_bound > BATCH_BYTES:
            _refuse('oversized-output-row' if len(rows) == 1 else 'output-staging-bytes')
        if python_bound > PYTHON_STAGING_BYTES:
            _refuse('python-output-staging-bytes')
        batch = pa.RecordBatch.from_pylist([dict(zip(self.schema, row, strict=True))
                                           for row in rows], schema=self.arrow_schema)
        size = batch.get_total_buffer_size()
        if size > BATCH_BYTES:
            _refuse('output-batch-backing-bytes')
        _emit(self.telemetry, 'output-batch', rows=batch.num_rows, bytes=size)
        if (self.batch_rows + batch.num_rows > GROUP_ROWS
                or self.batch_bytes + size > min(GROUP_BYTES, GROUP_TARGET_BYTES)):
            self.flush()
        self.batches.append(batch)
        self.batch_rows += batch.num_rows
        self.batch_bytes += size

    def flush(self):
        if not self.batches:
            return
        if self.groups >= WRITER_GROUPS:
            _refuse('writer-row-groups')
        table = pa.Table.from_batches(self.batches, schema=self.arrow_schema)
        witness = self.path.parent / (self.path.name + '.witness')
        safe_path(witness)
        try:
            with witness.open('xb') as output:
                with pq.ParquetWriter(output, self.arrow_schema, **_WRITER_OPTIONS) as writer:
                    writer.write_table(table, row_group_size=table.num_rows)
            footer, count, groups, _ = _preflight(witness, self.schema)
            with witness.open('rb') as source:
                metadata = pq.read_metadata(source)
                leaves = metadata.num_columns
                if groups != 1 or count != table.num_rows:
                    raise ValueError('ordered-merge witness grouping differs')
                for index in range(leaves):
                    column = metadata.row_group(0).column(index)
                    if (column.is_stats_set or column.has_dictionary_page
                            or column.has_column_index or column.has_offset_index
                            or column.is_geo_stats_set or column.metadata):
                        raise ValueError('ordered-merge unexpected writer metadata')
            reservation = footer + COLUMN_LAYOUT_BYTES * leaves + GROUP_LAYOUT_BYTES
            if self.footer_bound + reservation > FOOTER_BYTES:
                _refuse('prospective-writer-footer-bytes')
            self.footer_bound += reservation
            self.writer.write_table(table, row_group_size=table.num_rows)
            self.groups += 1
            self.rows += table.num_rows
            first = tuple(table[name][0].as_py() for name in self.keys)
            last = tuple(table[name][-1].as_py() for name in self.keys)
            if self.first is None:
                self.first = first
            if self.last is not None and _key(first) < _key(self.last):
                raise ValueError('ordered-merge output boundary is not ordered')
            self.last = last
            _emit(self.telemetry, 'writer-group', rows=table.num_rows,
                  bytes=table.get_total_buffer_size(), witness_footer=footer,
                  footer_bound=self.footer_bound, groups=self.groups)
            self.batches.clear()
            self.batch_rows = self.batch_bytes = 0
        finally:
            witness.unlink(missing_ok=True)

    def close(self):
        try:
            if self.writer is not None:
                self.writer.close()
                self.writer = None
        finally:
            self.output.close()

    def finish(self):
        self.flush()
        self.close()
        footer, count, groups, _ = _preflight(self.path, self.schema)
        if footer > self.footer_bound and count:
            _refuse('serialized-writer-footer-envelope')
        if count != self.rows or groups != self.groups:
            # Arrow writes one physical empty group when an empty Table is written;
            # no Table is appended here, so the empty run has zero groups.
            raise ValueError('ordered-merge final writer count/group differs')
        _emit(self.telemetry, 'writer-finished', rows=count, groups=groups, footer=footer,
              footer_bound=self.footer_bound)
        return MergedFragment(self.path, count, self.first, self.last, tuple(self.schema.items()))


def _merge_group(records, path, schema, keys, telemetry):
    writer = None
    try:
        with ExitStack() as stack:
            readers = []
            for record in records:
                reader = _Reader(record, schema, keys, telemetry)
                stack.callback(reader.close)
                readers.append(reader)
            writer = _Writer(path, schema, keys, telemetry)
            stack.callback(writer.close)
            heap = []
            for index, reader in enumerate(readers):
                item = reader.next()
                if item is not None:
                    key, row = item
                    heapq.heappush(heap, (_key(key), index, row))
            rows = []
            staged_arrow_bytes = staged_python_bytes = 0
            while heap:
                _, index, row = heapq.heappop(heap)
                arrow_bytes, python_bytes = _row_sizes(row, writer.arrow_schema)
                python_bytes += writer.conversion_bytes_per_row
                if arrow_bytes > BATCH_BYTES:
                    _refuse('oversized-output-row')
                if python_bytes > PYTHON_STAGING_BYTES:
                    _refuse('python-output-staging-bytes')
                if rows and (len(rows) == BATCH_ROWS
                             or staged_arrow_bytes + arrow_bytes > BATCH_BYTES
                             or staged_python_bytes + python_bytes > PYTHON_STAGING_BYTES):
                    _emit(telemetry, 'output-staging', rows=len(rows),
                          arrow_bound=staged_arrow_bytes, python_bytes=staged_python_bytes)
                    writer.append(rows)
                    rows.clear()
                    staged_arrow_bytes = staged_python_bytes = 0
                rows.append(row)
                staged_arrow_bytes += arrow_bytes
                staged_python_bytes += python_bytes
                item = readers[index].next()
                if item is not None:
                    key, row = item
                    heapq.heappush(heap, (_key(key), index, row))
            if rows:
                _emit(telemetry, 'output-staging', rows=len(rows),
                      arrow_bound=staged_arrow_bytes, python_bytes=staged_python_bytes)
                writer.append(rows)
            return writer.finish()
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def merge_fragments(manifest, destination, schema, keys, *, telemetry=None):
    '''Consume a streamed manifest into one exact globally ordered compact file.'''
    manifest, destination = Path(manifest), Path(destination)
    safe_path(manifest)
    safe_path(destination)
    if destination.exists():
        raise ValueError('ordered-merge destination already exists')
    workspace = destination.parent / (destination.name + '.merge')
    safe_path(workspace)
    workspace.mkdir()
    current, level = manifest, 0
    try:
        while True:
            next_manifest = workspace / f'level-{level:04d}.jsonl'
            emitted = 0
            with next_manifest.open('x') as output:
                iterator = iter(_records(current, schema, keys))
                while True:
                    group = []
                    # Reserve one reader slot for bounded footer/witness checks.
                    for _ in range(FAN_IN - 1):
                        try:
                            group.append(next(iterator))
                        except StopIteration:
                            break
                    if not group and emitted:
                        break
                    path = workspace / f'level-{level:04d}-run-{emitted:08d}.parquet'
                    result = _merge_group(group, path, schema, keys, telemetry)
                    append_fragment(output, path, schema, keys, result.row_count,
                                    result.first_key, result.last_key)
                    emitted += 1
                    if not group:
                        break
            _emit(telemetry, 'merge-level', level=level, runs=emitted,
                  disk_bytes=sum(path.stat().st_size for path in workspace.iterdir()))
            if emitted == 1:
                # Validate descriptor and fully drain final output before exposing it.
                record = next(_records(next_manifest, schema, keys))
                reader = _Reader(record, schema, keys, telemetry)
                try:
                    while reader.next() is not None:
                        pass
                finally:
                    reader.close()
                # No-replacement publication of this operation's owned validated file.
                import os
                os.link(result.path, destination)
                return MergedFragment(destination, result.row_count, result.first_key,
                                      result.last_key, result.schema)
            if current.parent == workspace:
                for record in _records(current, schema, keys):
                    record['path'].unlink()
                current.unlink()
            current = next_manifest
            level += 1
    except BaseException:
        raise
    finally:
        shutil.rmtree(workspace)


TABLES = (*TARGET_TABLES, *AUXILIARY_SCHEMAS)
_ASSEMBLY_ROW_GROUP_SIZE = 16384
_ASSEMBLY_PREFIXES = {
    **{name: ['source', 'family', 'unit_a_type', 'unit_a'] for name in TARGET_TABLES},
    'target_units': ['unit_type', 'unit'],
    'target_support': ['view', 'source', 'family', 'unit_a_type', 'unit_a'],
    'replicate_estimates': ['view', 'source', 'family', 'unit_a_type', 'unit_a'],
    'eligibility_diagnostics': ['source', 'profile', 'delivery_id', 'source_parquet_sha256',
                                'sample_id', 'component_year'],
    'allocation_residuals': ['source', 'family', 'workplace_unit_type', 'workplace_unit',
                             'code_unit_type', 'code_unit'],
}


@dataclass(frozen=True)
class _TableFragment:
    name: str
    path: Path
    schema: tuple
    rows: int


def _table_layout(name):
    if name in TARGET_TABLES:
        return TARGET_SCHEMA, TARGET_KEY_COLUMNS
    return AUXILIARY_SCHEMAS[name], AUXILIARY_KEYS[name]


def _sink_table_fragment(name, frame, destination):
    schema, keys = _table_layout(name)
    actual_schema = tuple(frame.collect_schema().items())
    if actual_schema != tuple(schema.items()):
        raise ValueError(name + ': fragment schema differs')
    safe_path(destination)
    with destination.open('xb') as output:
        frame.sort(keys, nulls_last=False).sink_parquet(
            output, row_group_size=_ASSEMBLY_ROW_GROUP_SIZE, statistics=True,
            maintain_order=True, engine='streaming')
    rows = pl.scan_parquet(destination).select(pl.len()).collect().item()
    return _TableFragment(name, destination, actual_schema, rows)


def _assemble_table_spilled(name, fragments, workspace):
    schema, keys = _table_layout(name)
    safe_path(workspace)
    directory = workspace / name
    safe_path(directory)
    directory.mkdir()
    try:
        for record in fragments:
            safe_path(record.path)
            if record.name != name or record.schema != tuple(schema.items()):
                raise ValueError(name + ': mismatched fragment descriptor')
        frames = [pl.scan_parquet(record.path, use_statistics=True) for record in fragments]
        source = pl.concat(frames) if frames else pl.LazyFrame(schema=schema)
        prefix = _ASSEMBLY_PREFIXES[name]
        registry = directory / 'prefixes.parquet'
        # Only actual aggregate prefixes are deduplicated; source rows stay untouched.
        with registry.open('xb') as output:
            source.select(prefix).unique().sort(prefix, nulls_last=False).sink_parquet(
                output, maintain_order=True, engine='streaming')
        paths = []
        for batch in pl.scan_parquet(registry).collect_batches(
            chunk_size=1024, maintain_order=True, lazy=True, engine='streaming'
        ):
            for values in batch.iter_rows():
                predicate = pl.all_horizontal([
                    pl.col(key).eq_missing(pl.lit(value, dtype=schema[key]))
                    for key, value in zip(prefix, values, strict=True)])
                path = directory / f'range-{len(paths):08d}.parquet'
                _sink_table_fragment(name, source.filter(predicate), path)
                paths.append(path)
        if not paths:
            path = directory / 'empty.parquet'
            _sink_table_fragment(name, pl.LazyFrame(schema=schema), path)
            paths.append(path)
        # Disjoint leading prefixes make explicit range concatenation globally ordered.
        return pl.concat([pl.scan_parquet(path) for path in paths])
    except BaseException:
        shutil.rmtree(directory)
        raise


def _spill_product_outputs(aggregates, residuals, workspace):
    _validate_aggregate_denominators(aggregates)
    directory = workspace / aggregates.product.product_id
    safe_path(directory)
    directory.mkdir()
    try:
        estimates = _spill_estimate_fragments(aggregates, directory)
        target = {
            'observed': 'targets_observed',
            'canonical': 'targets_canonical',
            'allocated_county': 'targets_allocated_area_mix',
            'allocated_msa': 'targets_allocated_area_mix',
        }[aggregates.product.view]
        records = []
        for name, frame in [
            (target, estimates['targets']),
            ('target_support', estimates['support']),
            ('replicate_estimates', estimates['replicates']),
            ('eligibility_diagnostics', aggregates.diagnostics),
            ('allocation_residuals', residuals),
        ]:
            destination = directory / (name + '.parquet')
            if name in (target, 'target_support', 'replicate_estimates'):
                schema, keys = _table_layout(name)
                merged = merge_fragments(frame, destination, schema, keys)
                records.append(_TableFragment(name, merged.path, merged.schema, merged.row_count))
            else:
                records.append(_sink_table_fragment(name, frame, destination))
        # Every returned scan now reads its compact durable file, not estimator shards.
        shutil.rmtree(directory / ('estimates-' + aggregates.product.product_id))
        return records
    except BaseException:
        shutil.rmtree(directory)
        raise


def derive_tables(
    selected: SelectedTargets, scratch: Path
) -> dict[str, pl.DataFrame | pl.LazyFrame]:
    '''Finish one product's aggregate work before retaining only durable output scans.'''
    safe_path(scratch)
    directory = scratch / 'target-assembly'
    safe_path(directory)
    directory.mkdir()
    try:
        work, output, ranges = [directory / name for name in ('work', 'outputs', 'ranges')]
        for child in (work, output, ranges):
            child.mkdir()
        units = build_units(selected)
        rules = {profile: read_rules(source)
                 for profile, source in selected.upstream.sources.items()}
        nodes = {system: pl.read_parquet(selected.upstream.codes[system + '_nodes'])
                 for system in ('naics', 'soc')}
        factors = pl.read_parquet(selected.tables['puma_county_factors'])
        counties = pl.read_parquet(selected.upstream.geography['county_reference'])
        outputs = {name: [] for name in TABLES}
        unit_record = _sink_table_fragment('target_units', units.lazy(),
                                           output / 'target_units.parquet')
        with weighted_source(selected, scratch) as source:
            for product in PRODUCTS:
                if product.view != 'observed':
                    continue
                rows = family_rows(source.frame, product, rules['acs/core'], units)
                product_work = work / product.product_id
                safe_path(product_work)
                product_work.mkdir()
                try:
                    native = _aggregate_native_spilled(rows, product_work)
                    for record in _spill_product_outputs(
                        native, pl.LazyFrame(schema=RESIDUAL_SCHEMA), output
                    ):
                        outputs[record.name].append(record)
                    for projected in PRODUCTS:
                        if (projected.view == 'observed'
                            or observed_counterpart(projected) != product):
                            continue
                        projected_work = product_work / projected.product_id
                        safe_path(projected_work)
                        projected_work.mkdir()
                        try:
                            if projected.view == 'canonical':
                                aggregates = _aggregate_native_spilled(
                                    canonical_rows(rows, nodes), projected_work)
                                residuals = pl.LazyFrame(schema=RESIDUAL_SCHEMA)
                            else:
                                aggregates, residuals = _allocate_area_mix_spilled(
                                    native, factors, counties, projected, projected_work,
                                    native_wide_root=(
                                        product_work / ('native-' + product.product_id)))
                            for record in _spill_product_outputs(aggregates, residuals, output):
                                outputs[record.name].append(record)
                        finally:
                            shutil.rmtree(projected_work)
                finally:
                    shutil.rmtree(product_work)
        tables = {'target_units': pl.scan_parquet(unit_record.path)}
        for name in TABLES:
            if name != 'target_units':
                tables[name] = _assemble_table_spilled(name, outputs[name], ranges)
        return {name: tables[name] for name in TABLES}
    except BaseException:
        shutil.rmtree(directory)
        raise


def write_tables(staging: Path, tables: dict[str, pl.DataFrame | pl.LazyFrame]) -> dict:
    '''Validate before writing and again on the exact serialized ordered tables.'''
    validate_complete_tables(tables)
    for name in TABLES:
        destination = staging / (name + '.parquet')
        safe_path(destination)
        if destination.exists():
            raise FileExistsError(destination)
        if name in TARGET_TABLES:
            write_targets(tables[name], destination)
        else:
            frame = tables[name]
            if isinstance(frame, pl.DataFrame):
                frame = frame.lazy()
            with destination.open('xb') as output:
                frame.sink_parquet(output, maintain_order=True, engine='streaming')
    serialized = {name: pl.scan_parquet(staging / (name + '.parquet')) for name in TABLES}
    validate_complete_tables(serialized)
    for name in TABLES:
        expected = tables[name]
        if isinstance(expected, pl.DataFrame):
            expected = expected.lazy()
        parity = ipums_parity.compare_ordered(expected, serialized[name])
        if (not parity['schema_equal'] or not parity['values_equal']
                or parity['expected_rows'] != parity['actual_rows']):
            raise ValueError(name + ': serialized table differs')
    return {name: target_io.file_record(staging / (name + '.parquet')) for name in TABLES}


def validate_complete_tables(tables):
    '''Add whole-bundle annual/measure and denominator closure to shared schemas.'''
    validate_cross_tables(tables, PRODUCTS)
    support = tables['target_support']
    replicate = tables['replicate_estimates']
    support = support.lazy() if isinstance(support, pl.DataFrame) else support
    replicate = replicate.lazy() if isinstance(replicate, pl.DataFrame) else replicate
    native_views = pl.col('view').is_in(['observed', 'canonical'])
    native_scales = (
        _denominator_scale(support.filter(native_views & pl.col('record_kind').eq('cell')),
                           'cell_weight_sum_exact', 'denominator_weight_sum_exact'),
        _denominator_scale(replicate.filter(native_views),
                           'numerator_sum_exact', 'denominator_sum_exact'))
    for support_part, replicate_part in _validation_partitions([support, replicate]):
        _validate_complete_partition(support_part, replicate_part, native_scales)
    for name in TARGET_TABLES:
        _validate_key_order(tables[name], TARGET_KEY_COLUMNS, 'target ordered key sort differs')


def _validate_complete_partition(support, replicate, native_scales):
    '''Reconcile complete-a denominators without collecting whole published tables.'''
    cells = support.filter(pl.col('record_kind').eq('cell'))
    annual = cells.group_by(STAT_KEY_COLUMNS).agg(
        pl.col('component_year').n_unique().alias('_components'), pl.col('pool_divisor').first()
    )
    if annual.filter(pl.col('_components').ne(pl.col('pool_divisor') + 1)).select(
            pl.len()).collect().item():
        raise ValueError('complete annual support components required')
    paired = cells.group_by(*CELL_KEY_COLUMNS, 'component_year').agg(
        pl.col('measure').n_unique().alias('_measures')
    )
    if paired.filter(pl.col('_measures').ne(2)).select(pl.len()).collect().item():
        raise ValueError('both measures require matching annual/pooled support')
    denominator_keys = [name for name in STAT_KEY_COLUMNS if name not in {'unit_b', 'unit_b_type'}]
    for column, denominator in [
        ('n_unweighted', 'denominator_n_unweighted'),
        ('fractional_support_mass', 'denominator_fractional_support_mass'),
    ]:
        groups = cells.group_by(*denominator_keys, 'component_year').agg(
            pl.col(column).sum().alias('_sum'), pl.col(denominator).first().alias('_expected')
        )
        error = (pl.col('_sum') - pl.col('_expected')).abs()
        tolerance = (
            pl.lit(0) if column == 'n_unweighted' else 1e-8 + 1e-12 * pl.col('_expected').abs()
        )
        if groups.filter(error > tolerance).select(pl.len()).collect().item():
            raise ValueError('support denominator does not close')
    for native in (True, False):
        native_views = pl.col('view').is_in(['observed', 'canonical'])
        cell_subset = cells.filter(native_views if native else ~native_views)
        replicate_subset = replicate.filter(native_views if native else ~native_views)
        _check_denominator_sums(cell_subset, [*denominator_keys, 'component_year'],
            'cell_weight_sum_exact' if native else 'cell_mass',
            'denominator_weight_sum_exact' if native else 'denominator_mass', native=native,
            scale=native_scales[0] if native else None)
        _check_denominator_sums(replicate_subset, [*denominator_keys, 'replicate'],
            'numerator_sum_exact' if native else 'numerator',
            'denominator_sum_exact' if native else 'denominator', native=native,
            scale=native_scales[1] if native else None)


def _denominator_scale(lf, numerator, denominator):
    return lf.select(pl.max_horizontal([
        pl.col(name).str.split('.').list.get(1, null_on_oob=True).str.len_chars()
        for name in (numerator, denominator)]).max()).collect().item() or 0


def _check_denominator_sums(frame, keys, numerator, denominator, *, native, scale=None):
    lf = frame.lazy() if isinstance(frame, pl.DataFrame) else frame
    if native:
        scale = _denominator_scale(lf, numerator, denominator) if scale is None else scale
        dtype = pl.Decimal(38, scale)
        groups = lf.group_by(keys).agg(
            pl.col(numerator).cast(dtype).sum().alias('_sum'),
            pl.col(denominator).cast(dtype).first().alias('_expected'),
            pl.col(denominator).n_unique().alias('_versions'))
        invalid = pl.col('_sum').ne(pl.col('_expected'))
    else:
        # The same typed code order used by allocation fixes Float64 reduction order.
        ordered = lf.sort([*keys, 'unit_b_type', 'unit_b']).with_columns(
            pl.col(numerator).cum_sum().over(keys, order_by=['unit_b_type', 'unit_b'])
            .alias('_cumulative'))
        groups = ordered.group_by(keys).agg(pl.col('_cumulative').last().alias('_sum'),
            pl.col(denominator).first().alias('_expected'),
            pl.col(denominator).n_unique().alias('_versions'))
        invalid = (pl.col('_sum') - pl.col('_expected')).abs().gt(
            1e-8 + 1e-12 * pl.col('_expected').abs())
    invalid = invalid | pl.col('_expected').is_null() | pl.col('_versions').ne(1)
    if groups.select(invalid.any()).collect().item():
        raise ValueError('identified cell sums differ from denominator')


def _validate_aggregate_denominators(aggregates):
    keys = ['unit_a_type', 'unit_a', 'component_year', 'replicate']
    native = aggregates.product.view in {'observed', 'canonical'}
    column = 'sum_exact' if native else 'mass'
    denominators = aggregates.denominators.select(*keys, pl.col(column).alias('_denominator'))
    joined = aggregates.cells.join(denominators, on=keys, how='left', validate='m:1')
    scale = _denominator_scale(joined, column, '_denominator') if native else None
    for (part,) in _validation_partitions([joined], ['unit_a_type', 'unit_a']):
        _check_denominator_sums(part, keys, column, '_denominator', native=native, scale=scale)
