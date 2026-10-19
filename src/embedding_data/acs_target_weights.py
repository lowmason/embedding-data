'''Recover literal Decimal person weights only after exact positional authentication.'''

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from embedding_data import ipums_conversion, ipums_parity, ipums_weights, target_io
from embedding_data.acs_mapping_contract import companion_schema
from embedding_data.acs_target_inputs import SelectedTargets

WEIGHT_NAMES = ('PERWT', *(f'REPWTP{r}' for r in range(1, 81)))


@dataclass(frozen=True)
class WeightedSource:
    frame: pl.LazyFrame
    diagnostics: pl.DataFrame
    rules: dict


def _validate_alignment(source, numeric, companion, diagnostics):
    original = pl.scan_parquet(source.parquet)
    schema = original.collect_schema()
    recorded = source.parquet_record
    if [name for name in numeric.collect_schema() if name != 'source_row'] != list(schema):
        raise ValueError('raw ordered source columns differ from original schema')
    if (list(schema) != recorded['columns']
            or {name: str(dtype) for name, dtype in schema.items()} != recorded['schema']):
        raise ValueError('source ordered schema differs from recorded evidence')
    if list(companion.collect_schema().items()) != list(companion_schema(schema).items()):
        raise ValueError('companion ordered schema differs from source prefix and annotations')
    indexed_original = original.with_row_index('source_row').with_columns(
        pl.col('source_row').cast(pl.UInt64))
    nonweights = ['source_row', *[name for name in schema
                                  if name not in set(diagnostics['variable'])]]
    for left, right in ((numeric, indexed_original), (indexed_original, companion)):
        parity = ipums_parity.compare_ordered(left.select(nonweights), right.select(nonweights))
        if (not parity['schema_equal'] or not parity['values_equal']
                or parity['expected_rows'] != recorded['rows']
                or parity['actual_rows'] != recorded['rows']):
            raise ValueError('ordered source values or row counts differ before weight alignment')
    if companion.select(pl.col('source_parquet_sha256').is_null().or_(
            pl.col('source_parquet_sha256').ne(recorded['sha256'])).any()).collect().item():
        raise ValueError('companion source hash differs')
    if target_io.file_record(source.parquet) != recorded:
        raise ValueError('original source bytes differ from recorded evidence')


def _scan_weights(csv_path, ddi):
    diagnostics, rules = ipums_weights.measure_weights(csv_path, ddi, 'acs', 'core')
    names = set(diagnostics['variable'])
    numbered = {name for name in names if name.startswith('REPWTP')
                and name.removeprefix('REPWTP').isdigit()}
    if numbered != set(WEIGHT_NAMES[1:]) or 'PERWT' not in names:
        raise ValueError('expected exactly PERWT and REPWTP1 through REPWTP80')
    required = diagnostics.filter(pl.col('variable').is_in(WEIGHT_NAMES))
    if required.select(pl.col('null_rows').sum()).item():
        raise ValueError('required weight is missing')
    numeric = ipums_weights.scan_numeric_csv(csv_path, diagnostics, 'acs').with_row_index(
        'source_row').with_columns(pl.col('source_row').cast(pl.UInt64))
    checks = numeric.select(pl.col('PERWT').lt(0).any(),
                            *[pl.col(name).is_null().any().alias(name + '_null')
                              for name in WEIGHT_NAMES]).collect()
    if any(checks.row(0)):
        raise ValueError('negative full person weight or missing exact required weight')
    return numeric, diagnostics, rules


@contextmanager
def weighted_source(selected: SelectedTargets, scratch: Path):
    '''Keep the authenticated decompressed scan alive until native aggregates finish.'''
    selected.verify()
    source = selected.upstream.sources['acs/core']
    citations = [c for c in source.raw_citations if c['path'].endswith('.csv.gz')]
    if len(citations) != 1:
        raise ValueError('one authenticated core CSV is required')
    raw_csv = target_io.relative_file(selected.data_dir / 'raw', citations[0]['path'])
    if target_io.file_record(raw_csv)['sha256'] != citations[0]['sha256']:
        raise ValueError('raw source bytes differ from selected citation')
    with ipums_conversion.decompressed_csv(raw_csv, scratch) as csv_path:
        numeric, diagnostics, rules = _scan_weights(csv_path, source.ddi)
        companion = pl.scan_parquet(selected.tables['acs_core_canonical'])
        _validate_alignment(source, numeric, companion, diagnostics)
        frame = companion.drop(WEIGHT_NAMES).join(
            numeric.select('source_row', *WEIGHT_NAMES), on='source_row', how='left',
            validate='1:1', maintain_order='left').with_columns(
                pl.lit(source.delivery_id).alias('source_delivery_id'))
        selected.verify()
        try:
            yield WeightedSource(frame, diagnostics, rules)
        finally:
            selected.verify()
