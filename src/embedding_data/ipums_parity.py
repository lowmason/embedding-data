'''Bounded, ordered logical comparison of delivered CSV and derived Parquet.'''

from collections.abc import Iterator
from pathlib import Path

import polars as pl

from embedding_data.ipums_conversion import COLLECTIONS, decompressed_csv, scan_delivered_csv

def _nonempty_batches(frame: pl.LazyFrame, chunk_size: int) -> Iterator[pl.DataFrame]:
    for batch in frame.collect_batches(
        chunk_size=chunk_size, maintain_order=True, lazy=True, engine='streaming',
    ):
        if batch.height:
            yield batch


def compare_ordered(
    expected: pl.LazyFrame, actual: pl.LazyFrame, *, chunk_size: int = 16384,
) -> dict:
    '''Compare exact ordered schemas/values and drain both independent batch streams.

    Holds one current batch and offset per side. The chunk size bounds application-held
    rows, not scanner buffers or process memory. Logical equality does not establish
    physical Parquet equality, NaN payload identity or signed-zero identity.
    '''
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ValueError('chunk_size must be a positive integer')
    schema_equal = list(expected.collect_schema().items()) == list(actual.collect_schema().items())
    left_batches = _nonempty_batches(expected, chunk_size)
    right_batches = _nonempty_batches(actual, chunk_size)
    if not schema_equal:
        return {
            'schema_equal': False, 'values_equal': False,
            'expected_rows': sum(batch.height for batch in left_batches),
            'actual_rows': sum(batch.height for batch in right_batches),
        }
    left = next(left_batches, None)
    right = next(right_batches, None)
    expected_rows = actual_rows = 0
    left_offset = right_offset = 0
    values_equal = True
    while left is not None or right is not None:
        if left is None:
            values_equal = False
            actual_rows += right.height - right_offset
            right = next(right_batches, None)
            right_offset = 0
        elif right is None:
            values_equal = False
            expected_rows += left.height - left_offset
            left = next(left_batches, None)
            left_offset = 0
        else:
            count = min(left.height - left_offset, right.height - right_offset)
            if not left.slice(left_offset, count).equals(right.slice(right_offset, count)):
                values_equal = False
            expected_rows += count
            actual_rows += count
            left_offset += count
            right_offset += count
            if left_offset == left.height:
                left = next(left_batches, None)
                left_offset = 0
            if right_offset == right.height:
                right = next(right_batches, None)
                right_offset = 0
    return {
        'schema_equal': True, 'values_equal': values_equal,
        'expected_rows': expected_rows, 'actual_rows': actual_rows,
    }


def verify_conversion(
    csv_gz: Path, parquet: Path, source: str, temporary_directory: Path,
) -> dict:
    '''Compare the independent delivered CSV scan with the existing, unmodified Parquet.'''
    if source not in COLLECTIONS:
        raise ValueError(f'unknown source: {source}')
    with decompressed_csv(csv_gz, temporary_directory) as csv:
        return compare_ordered(scan_delivered_csv(csv, source), pl.scan_parquet(parquet))
