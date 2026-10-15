'''Aggregate CSV weight evidence without changing delivered units or stored Parquets.'''

import re
from decimal import Decimal, localcontext
from importlib.metadata import version
from pathlib import Path

import polars as pl

from embedding_data.ipums_conversion import CODE_COLUMNS, INFER_SCHEMA_LENGTH, SCHEMA_OVERRIDES

NUMERIC = r'^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$'
EXPONENT = r'^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)[eE][+-]?[0-9]+$'
DIAGNOSTIC_SCHEMA = {
    'source': pl.String, 'set_name': pl.String, 'variable': pl.String, 'family': pl.String,
    'implied_decimals': pl.Int64, 'scale': pl.Int64, 'rows': pl.UInt64,
    'null_rows': pl.UInt64, 'blank_rows': pl.UInt64, 'non_numeric_rows': pl.UInt64,
    'explicit_decimal_rows': pl.UInt64, 'negative_rows': pl.UInt64, 'zero_rows': pl.UInt64,
    'minimum': pl.Float64, 'maximum': pl.Float64, 'sum': pl.Float64,
    'minimum_exact': pl.String, 'maximum_exact': pl.String, 'sum_exact': pl.String,
    'alternative_sum_exact': pl.String, 'extrema_status': pl.String,
}


def _family(name, metadata):
    if name == 'REPWTP':
        return 'helper'
    if re.fullmatch(r'REPWTP[0-9]+', name):
        return 'replicate'
    if (name in {'HHWT', 'ASECWTH', 'HWTFINL', 'HWTSUPP'}
            or 'household weight' in (metadata.get('label') or '').lower()):
        return 'household'
    if name.startswith('LNK') and name.endswith('WT'):
        return 'linkage'
    if name == 'EARNWT':
        return 'earnings'
    if name in {'PERWT', 'WTFINL', 'ASECWT', 'WTSUPP'}:
        return 'person'
    if 'WT' in name or 'weight' in (metadata.get('label') or '').lower():
        return 'other_weight'
    return None


def _lexical_summary(raw, names):
    expressions = [pl.len().alias('rows')]
    for name in names:
        value = pl.col(name)
        valid = value.str.contains(NUMERIC).fill_null(False)
        blank = value.eq('').fill_null(False)
        integer = (value.str.replace(r'^[+-]', '').str.split('.').list.first()
                   .str.strip_chars_start('0'))
        statistics = {
            'null': value.is_null().sum(), 'blank': blank.sum(),
            'invalid': value.is_not_null().and_(blank.not_()).and_(valid.not_()).sum(),
            'decimal': value.str.contains(r'\.').fill_null(False).sum(),
            'exponent': value.str.contains(EXPONENT).fill_null(False).sum(),
            'scale': value.filter(valid).str.extract(r'\.([0-9]*)$', 1)
                          .str.len_chars().fill_null(0).max(),
            'integer_digits': integer.filter(valid).str.len_chars().max(),
        }
        expressions.extend(expr.alias(f'{name}:{key}') for key, expr in statistics.items())
    return raw.select(expressions).collect(engine='streaming').row(0, named=True)


def measure_weights(csv_path: Path, ddi: dict, source: str,
                    set_name: str) -> tuple[pl.DataFrame, dict]:
    '''Summarize every delivered weight, including automatic and individual replicates.

    Exact numeric summaries cover valid numeric cells only; lexical failures remain counts.
    Exponent notation, unrepresentable scale and potential Decimal38 aggregate overflow fail.
    No value is excluded as an undocumented sentinel. REPWTP is a request helper only.
    No artifact is written; caller owns publication and Task2 full-column Parquet parity.
    '''
    if source not in SCHEMA_OVERRIDES:
        raise ValueError('unknown source')
    metadata = {variable['name']: variable for variable in ddi.get('variables', [])}
    raw = pl.scan_csv(csv_path, infer_schema=False)
    families = {name: family for name in raw.collect_schema().names()
                if (family := _family(name, metadata.get(name, {}))) is not None}
    names = sorted(families)
    lexical = _lexical_summary(raw, names)
    numeric_expressions = []
    scales = {}
    for name in names:
        if families[name] == 'helper':
            continue
        scale = lexical[f'{name}:scale'] or 0
        integer_digits = lexical[f'{name}:integer_digits'] or 0
        if lexical[f'{name}:exponent']:
            raise ValueError(f'{name}: unsupported exponent notation')
        # An absolute-sum bound prevents Decimal128 wrapping before cancellation.
        carry_digits = len(str(max(lexical['rows'] - 1, 0))) if lexical['rows'] > 1 else 0
        if scale > 38 or integer_digits + scale + carry_digits > 38:
            raise ValueError(f'{name}: unsupported Decimal38 precision or aggregate bound')
        scales[name] = scale
        number = pl.when(pl.col(name).str.contains(NUMERIC)).then(pl.col(name)).otherwise(None)
        number = number.cast(pl.Decimal(38, scale), strict=True)
        statistics = {'minimum': number.min(), 'maximum': number.max(), 'sum': number.sum(),
                      'negative': number.lt(0).sum(), 'zero': number.eq(0).sum()}
        numeric_expressions.extend(expr.alias(f'{name}:{key}') for key, expr in statistics.items())
    numeric = (raw.select(numeric_expressions).collect(engine='streaming').row(0, named=True)
               if numeric_expressions else {})
    rows = []
    for name in names:
        exponent = metadata.get(name, {}).get('implied_decimals')
        if exponent is not None and (type(exponent) is not int or exponent < 0):
            raise ValueError(f'{name}: invalid DDI decimal exponent')
        row = {'source': source, 'set_name': set_name, 'variable': name,
               'family': families[name], 'implied_decimals': exponent, 'scale': scales.get(name),
               'rows': lexical['rows'], 'null_rows': lexical[f'{name}:null'],
               'blank_rows': lexical[f'{name}:blank'],
               'non_numeric_rows': lexical[f'{name}:invalid'],
               'explicit_decimal_rows': lexical[f'{name}:decimal'],
               'extrema_status': 'unexplained_without_documentation'}
        valid_count = row['rows'] - row['null_rows'] - row['blank_rows'] - row['non_numeric_rows']
        for statistic in ('minimum', 'maximum', 'sum'):
            value = numeric.get(f'{name}:{statistic}') if valid_count else None
            row[statistic] = float(value) if value is not None else None
            row[f'{statistic}_exact'] = str(value) if value is not None else None
        row['negative_rows'] = numeric.get(f'{name}:negative')
        row['zero_rows'] = numeric.get(f'{name}:zero')
        with localcontext() as context:
            context.prec = 38
            row['alternative_sum_exact'] = (
                str(Decimal(row['sum_exact']).scaleb(-exponent))
                if row['sum_exact'] is not None and exponent is not None else None)
        rows.append(row)
    diagnostics = pl.DataFrame(rows, schema=DIAGNOSTIC_SCHEMA)
    family_evidence = {}
    for family in sorted(set(families.values())):
        members = [row for row in rows if row['family'] == family]
        totals = [Decimal(row['sum_exact']) for row in members if row['sum_exact'] is not None]
        family_evidence[family] = {
            'variables': len(members), 'csv_factors': [1] if family != 'helper' else [],
            'sum_min_exact': str(min(totals)) if totals else None,
            'sum_max_exact': str(max(totals)) if totals else None,
            'implied_decimal_exponents': sorted({row['implied_decimals'] for row in members
                                                if row['implied_decimals'] is not None}),
            'unknown_exponents': sum(row['implied_decimals'] is None for row in members),
            'benchmark_limit': 'employment evidence applies only to PERWT or WTFINL',
        }
    rules = {
        'source': source, 'set_name': set_name, 'numeric_rule': 'literal_csv_value',
        'arithmetic': 'Decimal38 at observed per-column fractional scale; final display Float64',
        'fixed_width_alternative': '10**(-implied_decimals), diagnostic only',
        'csv_software_evidence': {
            'package': 'ipumspy', 'version': version('ipumspy'),
            'location': 'ipumspy/readers.py CSV branch _fix_decimal_expansion identity function',
        },
        'parquet_parity': 'external_required_all_variables', 'production_adoption': 'pending',
        'public_design_and_universe_evidence': 'external_required_per_weight_family',
        'sentinel_policy': 'no undocumented values excluded; extrema need source review',
        'families': family_evidence,
        'ddi_evidence': {name: metadata.get(name) for name in names},
        'aggregate_schema': {key: str(dtype) for key, dtype in DIAGNOSTIC_SCHEMA.items()},
    }
    return diagnostics, rules


def scan_numeric_csv(csv_path: Path, diagnostics: pl.DataFrame, source: str) -> pl.LazyFrame:
    '''Scan weights exactly using measure_weights scale; retain converter nonweight types.

    Required diagnostic columns: variable, family, scale, null_rows, blank_rows,
    non_numeric_rows. Call on the same immutable CSV used for those diagnostics.
    Non-numeric/blank cells fail; source nulls remain null for universe diagnostics.
    '''
    if source not in SCHEMA_OVERRIDES:
        raise ValueError('unknown source')
    overrides = dict(SCHEMA_OVERRIDES[source])
    expressions = []
    for row in diagnostics.iter_rows(named=True):
        if row['family'] == 'helper':
            continue
        if row['non_numeric_rows'] or row['blank_rows']:
            raise ValueError(f"{row['variable']}: invalid weight lexical cells")
        scale = row['scale']
        if type(scale) is not int or not 0 <= scale <= 38:
            raise ValueError('invalid weight scale')
        name = row['variable']
        overrides[name] = pl.String
        expressions.append(pl.col(name).cast(pl.Decimal(38, scale), strict=True))
    frame = pl.scan_csv(csv_path, schema_overrides=overrides,
                        infer_schema_length=INFER_SCHEMA_LENGTH).with_columns(expressions)
    if source == 'cps':
        codes = [name for name in CODE_COLUMNS if name in frame.collect_schema()]
        if codes:
            frame = frame.with_columns(pl.col(codes).cast(pl.String).str.zfill(4))
    return frame
