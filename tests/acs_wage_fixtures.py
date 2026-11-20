'''Synthetic Stage 8 core rows and the fixture chain for the ACS wage microdata tests.

The schema, the column names and the delivered DDI labels are written out here, not read from
the module under test, so a change to the module cannot change what the tests feed it.
'''

import shutil
from pathlib import Path

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


# The chain's delivery hook adds these columns to the core frame and, in this order, to its DDI.
# Stage 7 acceptance needs every Q flag in both.
DELIVERY_COLUMNS = (
    'EDUCD',
    'DEGFIELDD',
    'QINCWAGE',
    'QUHRSWOR',
    'QWKSWORK2',
    'QAGE',
    'QSEX',
    'QEDUC',
    'QDEGFIELD',
)
# Delivered DDI categories, written out here. The hook adds each one that the upstream fixtures
# do not supply yet.
DELIVERED_CATEGORIES = {
    'WKSWORK2': {
        '0': 'N/A',
        '1': '1-13 weeks',
        '2': '14-26 weeks',
        '3': '27-39 weeks',
        '4': '40-47 weeks',
        '5': '48-49 weeks',
        '6': '50-52 weeks',
    },
    'CLASSWKRD': {
        '13': 'Self-employed, not incorporated',
        '14': 'Self-employed, incorporated',
        '22': 'Wage/salary, private',
        '23': 'Wage/salary at non-profit',
        '25': 'Federal govt employee',
        '27': 'State govt employee',
        '28': 'Local govt employee',
        '29': 'Unpaid family worker',
    },
}
# Every control row starts as a full-time, full-year private employee with no allocated wage
# field. The other Q columns keep the seed row's values (2023 QMIGRAT1 stays null).
CONTROL_VALUES = {
    'INCWAGE': 50000,
    'INCWAGE_CPIU_2010': 40000.0,
    'UHRSWORK': 40,
    'WKSWORK2': 6,
    'CLASSWKR': 2,
    'CLASSWKRD': 22,
    **{name: 0 for name in Q_COLUMNS},
}
# AGE marker to the changes of its control row, with the expected result in the wage file.
# A row copies the first core row of its YEAR, 2023 unless the changes name 2024.
CONTROLS: dict[int, dict] = {
    41: {},  # headline
    42: {'QINCWAGE': 4},  # allocated, not headline
    43: {'QDEGFIELD': 4},  # allocated, headline
    44: {'UHRSWORK': 34},  # not full time, not headline
    45: {'WKSWORK2': 5},  # not full year, not headline
    46: {'CLASSWKR': 1, 'CLASSWKRD': 14},  # not wage/salary, not headline
    47: {'CLASSWKRD': 29},  # not wage/salary, not headline
    48: {'INCWAGE': 0},  # absent
    49: {'YEAR': 2024, 'IND': 8780, 'INDNAICS': '811192'},  # headline, node 811192
    50: {'INCWAGE': 90000},  # headline, top-coded; delivered as two identical rows
}
DUPLICATED_CONTROL = 50


def prepare_wage_delivery(
    profile: str, ddi: dict, frame: pl.LazyFrame
) -> tuple[dict, pl.LazyFrame]:
    '''Deliver the Stage 9 target rows plus the wage columns, labels and control rows.

    Only the `core` profile changes. The hook edits the raw originals before the unchanged
    upstream conversion, so Stages 7 and 8 see a genuine delivery.
    '''
    from acs_target_fixtures import prepare_target_delivery

    ddi, frame = prepare_target_delivery(profile, ddi, frame)
    if profile != 'core':
        return ddi, frame
    frame = frame.with_columns(
        pl.col('INCWAGE_CPIU_2010').cast(pl.Float64),
        *(pl.lit(0, dtype=pl.Int64).alias(name) for name in DELIVERY_COLUMNS),
    )
    ddi['variables'].extend(
        {'name': name, 'label': name, 'implied_decimals': 0, 'categories': [],
         'instructions': []}
        for name in DELIVERY_COLUMNS
    )
    for variable in ddi['variables']:
        present = {category['value'] for category in variable['categories']}
        variable['categories'].extend(
            {'value': code, 'label': label}
            for code, label in DELIVERED_CATEGORIES.get(variable['name'], {}).items()
            if code not in present
        )
    schema = frame.collect_schema()
    controls = []
    for age, changes in CONTROLS.items():
        seed = frame.filter(pl.col('YEAR') == changes.get('YEAR', 2023)).head(1)
        values = CONTROL_VALUES | {'AGE': age} | changes
        row = seed.with_columns(
            pl.lit(value, dtype=schema[name]).alias(name) for name, value in values.items()
        )
        controls.extend([row] * (2 if age == DUPLICATED_CONTROL else 1))
    return ddi, pl.concat([frame, *controls])


def wage_mapping(tmp_path: Path, monkeypatch) -> dict:
    '''Build the chain from raw delivery to a pinned Stage 8 run named `mapping`.'''
    from acs_target_fixtures import authenticated_mapping

    fixture = authenticated_mapping(tmp_path, monkeypatch, prepare_acs=prepare_wage_delivery)
    request = fixture['request']
    return {
        'data_dir': fixture['data_dir'],
        'mapping_run': 'mapping',
        'mapping_outputs_sha256': fixture['mapping_outputs_sha256'],
        'codes_run': request.codes_run,
        'codes_outputs_sha256': request.codes_outputs_sha256,
    }


def copy_template(template: dict, tmp_path: Path) -> dict:
    '''Copy the template's data directory into `tmp_path`, so that a test can change it.'''
    data_dir = tmp_path / 'data'
    shutil.copytree(template['data_dir'], data_dir)
    return template | {'data_dir': data_dir}
