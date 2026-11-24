'''Recover the literal Decimal CPS weights, aligned by position to the stored Parquets.

The Stage 7 Parquets store every weight as Float64, which cannot hold a sum of delivered
decimals exactly. This module reads the raw CSV text of each delivery instead. A weight is
`Decimal(38, s)`, as `ipums_weights.scan_numeric_csv` yields: `s` is the largest number of
fractional digits in that column, so every delivered value is exact, and 38 digits leave room
for a sum over every row.

Before any weight is used, every other column of the CSV must equal the Parquet row by row,
so that a row number names the same person-month in both. The returned frames are lazy and
read the decompressed CSV copies, which exist only inside the context.
'''

import re
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from embedding_data import ipums_conversion, ipums_parity, ipums_weights
from embedding_data.cps_flow_inputs import Delivery, SelectedInputs
from embedding_data.cps_flow_linkage import TWO_MONTH

# The full weight is first. The unnumbered `REPWTP` is a request helper, never a replicate.
WEIGHTS = {
    'monthly': ('LNKFW1MWT',),
    'asec': ('ASECWT', *(f'REPWTP{number}' for number in range(1, 161))),
}


@dataclass(frozen=True)
class WeightedSource:
    monthly: pl.LazyFrame
    asec: pl.LazyFrame
    diagnostics: dict[str, pl.DataFrame]
    rules: dict[str, dict]


def weight_status_expr(weight: pl.Expr, link_type: pl.Expr) -> pl.Expr:
    '''Name the state of a link's weight: `not_linkable` for a two-month link.'''
    return (pl.when(link_type.eq(TWO_MONTH)).then(pl.lit('not_linkable'))
            .when(weight.is_null()).then(pl.lit('null'))
            .when(weight.eq(0)).then(pl.lit('zero'))
            .otherwise(pl.lit('positive')))


def _scan(csv_path: Path, ddi: dict, set_name: str):
    '''Measure the weights of one CSV, then scan them with the source row number.'''
    diagnostics, rules = ipums_weights.measure_weights(csv_path, ddi, 'cps', set_name)
    names = set(diagnostics['variable'])
    required = set(WEIGHTS[set_name])
    if not required <= names or {
            name for name in names if re.fullmatch(r'REPWTP[0-9]+', name)} - required:
        raise ValueError(f'{set_name}: expected exactly the required weights')
    full = diagnostics.filter(pl.col('variable').eq(WEIGHTS[set_name][0]))
    if full['negative_rows'].item():
        raise ValueError(f'{set_name}: negative full weight')
    numeric = ipums_weights.scan_numeric_csv(csv_path, diagnostics, 'cps').with_row_index(
        'source_row').with_columns(pl.col('source_row').cast(pl.UInt64))
    return numeric, diagnostics, rules


def _check_alignment(delivery: Delivery, numeric: pl.LazyFrame,
                     diagnostics: pl.DataFrame) -> None:
    '''Refuse unless every non-weight column equals the Parquet, in order and by value.'''
    original = pl.scan_parquet(delivery.parquet)
    stored = original.collect_schema().names()
    if [name for name in numeric.collect_schema().names() if name != 'source_row'] != stored:
        raise ValueError('raw ordered source columns differ from original schema')
    indexed = original.with_row_index('source_row').with_columns(
        pl.col('source_row').cast(pl.UInt64))
    weights = set(diagnostics['variable'])
    columns = ['source_row', *(name for name in stored if name not in weights)]
    parity = ipums_parity.compare_ordered(numeric.select(columns), indexed.select(columns))
    rows = delivery.parquet_record['rows']
    if (not parity['schema_equal'] or not parity['values_equal']
            or parity['expected_rows'] != rows or parity['actual_rows'] != rows):
        raise ValueError('ordered source values or row counts differ before weight alignment')


@contextmanager
def weighted_sources(selected: SelectedInputs, scratch: Path):
    '''Yield the exact weights of both deliveries while their decompressed copies exist.

    The selection is verified on entry and again on exit, also after an exception.
    '''
    selected.verify()
    try:
        with ExitStack() as stack:
            scans = {}
            for set_name in WEIGHTS:
                delivery = getattr(selected, set_name)
                csv_path = stack.enter_context(
                    ipums_conversion.decompressed_csv(delivery.csv_gz, scratch))
                numeric, diagnostics, rules = _scan(csv_path, delivery.ddi, set_name)
                _check_alignment(delivery, numeric, diagnostics)
                scans[set_name] = (numeric.select('source_row', *WEIGHTS[set_name]),
                                   diagnostics, rules)
            yield WeightedSource(
                monthly=scans['monthly'][0], asec=scans['asec'][0],
                diagnostics={name: scan[1] for name, scan in scans.items()},
                rules={name: scan[2] for name, scan in scans.items()})
    finally:
        selected.verify()
