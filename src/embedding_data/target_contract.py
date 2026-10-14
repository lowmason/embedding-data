'''Family-independent validation and sorted serialization for long targets.'''

import re
from pathlib import Path

import polars as pl

from embedding_data.geography_references import occupied
from embedding_data.target_io import file_record

SCHEMA_VERSION = 'targets-v1'
TARGET_SCHEMA = {
    'source': pl.String, 'family': pl.String,
    'unit_a_type': pl.String, 'unit_a': pl.String,
    'unit_b_type': pl.String, 'unit_b': pl.String, 'measure': pl.String,
    'value': pl.Float64, 'se': pl.Float64, 'se_method': pl.String,
    'n_unweighted': pl.UInt64, 'n_weighted': pl.Float64,
    'sample_set': pl.String, 'vintage': pl.String, 'universe': pl.String,
    'flags': pl.List(pl.String),
}
TARGET_KEY_COLUMNS = [column for column in TARGET_SCHEMA
                      if column not in {'value', 'se', 'n_unweighted', 'n_weighted', 'flags'}]


def valid_unit(kind: str, value: str) -> bool:
    '''Check typed syntax; selected reference membership belongs to each family.'''
    if value.startswith('feature:'):
        parts = value.split(':', 2)
        return len(parts) == 3 and parts[1] == kind and bool(parts[2].strip())
    parts = value.split(':', 3)
    if len(parts) != 4 or not re.fullmatch(r'[0-9]{4}', parts[1]) or not parts[3].strip():
        return False
    system, level = parts[0], parts[2]
    return ((system == 'geography' and kind == level) or
            (system in {'naics', 'soc'} and kind == system + '_' + level))


def validate_targets(frame: pl.LazyFrame | pl.DataFrame) -> None:
    '''Reject noncanonical rows without casting, repairing, or estimating values.'''
    lf = frame.lazy() if isinstance(frame, pl.DataFrame) else frame
    if list(lf.collect_schema().items()) != list(TARGET_SCHEMA.items()):
        raise ValueError('targets schema must match exact ordered targets-v1 types')
    required_columns = [column for column in TARGET_SCHEMA if column != 'se']
    string_columns = [column for column, dtype in TARGET_SCHEMA.items() if dtype == pl.String]
    flags = pl.col('flags')
    valid_se = (
        pl.col('se_method').eq('none').and_(pl.col('se').is_null())
        .or_(pl.col('se_method').is_in(['replicate', 'bootstrap'])
             .and_(pl.col('se').is_not_null())
             .and_(pl.col('se').is_finite()).and_(pl.col('se').ge(0)))
    )
    checks = {
        'null required columns': pl.any_horizontal(
            [pl.col(column).is_null() for column in required_columns]),
        'blank metadata': pl.any_horizontal(
            [pl.col(column).str.strip_chars().eq('') for column in string_columns]),
        'nonfinite value': pl.col('value').is_finite().not_(),
        'invalid weighted count': pl.col('n_weighted').is_finite().not_()
            .or_(pl.col('n_weighted').lt(0)),
        'invalid standard error': valid_se.fill_null(False).not_(),
        'noncanonical flags': flags.list.eval(
            pl.element().is_null().or_(pl.element().str.strip_chars().eq(''))).list.any()
            .or_(flags.ne(flags.list.unique().list.sort())),
    }
    failures = lf.select([expression.any().alias(name)
                          for name, expression in checks.items()]).collect().row(0, named=True)
    for name, failed in failures.items():
        if failed:
            raise ValueError('targets contain ' + name)
    for side in ('a', 'b'):
        pairs = lf.select('unit_' + side + '_type', 'unit_' + side).unique().collect()
        if any(not valid_unit(kind, value) for kind, value in pairs.iter_rows()):
            raise ValueError('targets contain invalid typed unit_' + side)
    if (lf.group_by(TARGET_KEY_COLUMNS).len().filter(pl.col('len').gt(1))
            .select(pl.len()).collect().item()):
        raise ValueError('targets contain duplicate keys')


def write_targets(frame: pl.LazyFrame | pl.DataFrame, destination: Path) -> dict:
    '''Write one sorted staging file and inventory its validated serialized bytes.'''
    lf = frame.lazy() if isinstance(frame, pl.DataFrame) else frame
    validate_targets(lf)
    if occupied(destination):
        raise ValueError(f'{destination}: target file already exists')
    expected_rows = lf.select(pl.len()).collect().item()
    lf.sort(TARGET_KEY_COLUMNS).sink_parquet(destination)
    published = pl.scan_parquet(destination)
    validate_targets(published)
    keys = pl.struct(TARGET_KEY_COLUMNS)
    if published.select(keys.ne(keys.sort_by(TARGET_KEY_COLUMNS)).any()).collect().item():
        raise ValueError('serialized target keys are not sorted')
    record = file_record(destination)
    schema = published.collect_schema()
    record.update(rows=published.select(pl.len()).collect().item(), columns=list(schema),
                  schema={column: str(dtype) for column, dtype in schema.items()})
    if record['rows'] != expected_rows:
        raise ValueError('serialized target row count differs')
    return record
