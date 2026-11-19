'''Synthetic Stage 8 core rows for the ACS wage microdata tests.

The schema and the column names are written out here, not read from the module under test,
so a change to the module cannot change what the tests feed it.
'''

import polars as pl

STRING_COLUMNS = (
    'source_parquet_sha256',
    'acs_sample_id',
    'OCCSOC',
    'occupation_canonical_common_node_id',
    'occupation_aggregation_type',
    'INDNAICS',
    'industry_canonical_common_node_id',
    'industry_aggregation_type',
    'industry_native_node_id',
)
Q_COLUMNS = (
    'QINCWAGE',
    'QIND',
    'QOCC',
    'QUHRSWOR',
    'QWKSWORK2',
    'QAGE',
    'QSEX',
    'QEDUC',
    'QCLASSWK',
    'QDEGFIELD',
)
REPLICATES = tuple(f'REPWTP{n}' for n in range(1, 81))
INTEGER_COLUMNS = (
    'YEAR',
    *REPLICATES,
    'INCWAGE',
    'UHRSWORK',
    'WKSWORK2',
    'CLASSWKR',
    'CLASSWKRD',
    'SEX',
    'AGE',
    'EDUC',
    'EDUCD',
    'DEGFIELD',
    'DEGFIELDD',
    'STATEFIP',
    'REGION',
    'GQ',
    'OCC',
    'IND',
    *Q_COLUMNS,
)
DROPPED = ('SERIAL', 'PUMA')

CORE_SCHEMA: dict[str, pl.DataType] = {
    'source_parquet_sha256': pl.String,
    'source_row': pl.UInt64,
    'YEAR': pl.Int64,
    'acs_sample_id': pl.String,
    'SERIAL': pl.Int64,
    'PERWT': pl.Float64,
    **{name: pl.Int64 for name in REPLICATES},
    'INCWAGE': pl.Int64,
    'INCWAGE_CPIU_2010': pl.Float64,
    'UHRSWORK': pl.Int64,
    'WKSWORK2': pl.Int64,
    'CLASSWKR': pl.Int64,
    'CLASSWKRD': pl.Int64,
    'SEX': pl.Int64,
    'AGE': pl.Int64,
    'EDUC': pl.Int64,
    'EDUCD': pl.Int64,
    'DEGFIELD': pl.Int64,
    'DEGFIELDD': pl.Int64,
    'STATEFIP': pl.Int64,
    'REGION': pl.Int64,
    'GQ': pl.Int64,
    'PUMA': pl.Int64,
    'OCC': pl.Int64,
    'OCCSOC': pl.String,
    'occupation_canonical_common_node_id': pl.String,
    'occupation_aggregation_type': pl.String,
    'IND': pl.Int64,
    'INDNAICS': pl.String,
    'industry_canonical_common_node_id': pl.String,
    'industry_aggregation_type': pl.String,
    'industry_canonical_finest_candidates': pl.List(pl.String),
    'industry_native_node_id': pl.String,
    **{name: pl.Int64 for name in Q_COLUMNS},
}

CARRIED_COLUMNS = tuple(name for name in CORE_SCHEMA if name not in DROPPED)

# The spec leaves these out of the file: household identifiers, PUMA, county, the workplace and
# migration geography, and the design variables. The fixture schema holds only SERIAL and PUMA.
EXCLUDED_COLUMNS = (
    'SERIAL',
    'CBSERIAL',
    'PERNUM',
    'PUMA',
    'COUNTYFIP',
    'POWSTATE',
    'POWPUMA',
    'MIGPLAC1',
    'MIGPUMA1',
    'CLUSTER',
    'STRATA',
)

COMMON_NODE = 'naics:2022:national_industry:623110'
DELIVERED_NODE = 'naics:2022:industry_group:6231'


def core_row(**overrides) -> dict:
    '''Return a 2023 full-time, full-year private employee with no allocated value.

    The row has no `source_row`; `core_frame` numbers it unless an override sets it.
    '''
    row = {
        'source_parquet_sha256': 'a' * 64,
        'YEAR': 2023,
        'acs_sample_id': 'us2023a',
        'SERIAL': 11,
        'PERWT': 100.0,
        **{name: 90 + n for n, name in enumerate(REPLICATES, start=1)},
        'INCWAGE': 50000,
        'INCWAGE_CPIU_2010': 40000.0,
        'UHRSWORK': 40,
        'WKSWORK2': 6,
        'CLASSWKR': 2,
        'CLASSWKRD': 22,
        'SEX': 1,
        'AGE': 40,
        'EDUC': 6,
        'EDUCD': 101,
        'DEGFIELD': 50,
        'DEGFIELDD': 5001,
        'STATEFIP': 1,
        'REGION': 32,
        'GQ': 1,
        'PUMA': 100,
        'OCC': 1000,
        'OCCSOC': '291141',
        'occupation_canonical_common_node_id': 'soc:2018:detailed:29-1141',
        'occupation_aggregation_type': 'exact',
        'IND': 8270,
        'INDNAICS': '6231',
        'industry_canonical_common_node_id': COMMON_NODE,
        'industry_aggregation_type': 'exact',
        'industry_canonical_finest_candidates': ['623110'],
        'industry_native_node_id': DELIVERED_NODE,
        **{name: 0 for name in Q_COLUMNS},
    }
    return row | overrides


def with_excluded_columns(frame: pl.LazyFrame) -> pl.LazyFrame:
    '''Return the frame with every column of `EXCLUDED_COLUMNS` that it lacks, as Int64.'''
    have = set(frame.collect_schema().names())
    return frame.with_columns(
        pl.lit(7, dtype=pl.Int64).alias(name) for name in EXCLUDED_COLUMNS if name not in have
    )


def core_frame(rows: list[dict]) -> pl.LazyFrame:
    '''Return the rows as a lazy core table, numbering `source_row` from 0 in list order.'''
    numbered = [
        row if 'source_row' in row else {'source_row': position} | row
        for position, row in enumerate(rows)
    ]
    return pl.from_dicts(numbered, schema=CORE_SCHEMA).lazy()
