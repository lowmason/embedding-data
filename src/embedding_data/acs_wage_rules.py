'''Derive the ACS wage microdata rows and flags from the Stage 8 core table.

Every function is pure Polars. A function that returns a plan never collects person rows.
`check_inputs` and `wage_persons` collect small aggregates only, and every refusal has a fixed
message that holds no data value.
'''

import polars as pl

CONTRACT = 'acs-wage-microdata-v1'
TABLE = 'acs_wage_persons'

FULL_TIME_HOURS = 35
FULL_YEAR_WKSWORK2 = 6
WAGE_SALARY_CLASSWKRD = (22, 23, 25, 27, 28)
# IPUMS codes for a wage that is not applicable. They are positive, so INCWAGE > 0 keeps them.
INCWAGE_CODES = (999998, 999999)

# QDEGFIELD is carried for panels that use field of degree. It does not enter the headline.
HEADLINE_ALLOCATION = (
    'QINCWAGE',
    'QIND',
    'QOCC',
    'QUHRSWOR',
    'QWKSWORK2',
    'QAGE',
    'QSEX',
    'QEDUC',
    'QCLASSWK',
)
ALLOCATION = (*HEADLINE_ALLOCATION, 'QDEGFIELD')

NEW: dict[str, pl.DataType] = {
    'log_wage_2010': pl.Float64,
    'industry_node_code': pl.String,
    'industry_node_level': pl.String,
    'industry_delivered_node_code': pl.String,
    'flag_industry_shared_node': pl.Boolean,
    'flag_any_allocated': pl.Boolean,
    'flag_incwage_topcoded': pl.Boolean,
    'flag_full_time_full_year': pl.Boolean,
    'flag_wage_salary': pl.Boolean,
    'flag_headline': pl.Boolean,
}
FLAGS = tuple(name for name in NEW if name.startswith('flag_'))

OUTPUT_COLUMNS = (
    'source_parquet_sha256',
    'source_row',
    'YEAR',
    'acs_sample_id',
    'PERWT',
    *(f'REPWTP{n}' for n in range(1, 81)),
    'INCWAGE',
    'INCWAGE_CPIU_2010',
    'log_wage_2010',
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
    'OCCSOC',
    'occupation_canonical_common_node_id',
    'occupation_aggregation_type',
    'IND',
    'INDNAICS',
    'industry_canonical_common_node_id',
    'industry_aggregation_type',
    'industry_canonical_finest_candidates',
    'industry_native_node_id',
    'industry_node_code',
    'industry_node_level',
    'industry_delivered_node_code',
    'flag_industry_shared_node',
    *ALLOCATION,
    'flag_any_allocated',
    'flag_incwage_topcoded',
    'flag_full_time_full_year',
    'flag_wage_salary',
    'flag_headline',
)
CARRIED = tuple(name for name in OUTPUT_COLUMNS if name not in NEW)

# The columns that a rule reads. A null in one of them stops the build.
RULE_COLUMNS = (
    'source_row',
    'YEAR',
    'STATEFIP',
    'INCWAGE',
    'INCWAGE_CPIU_2010',
    'UHRSWORK',
    'WKSWORK2',
    'CLASSWKRD',
    'INDNAICS',
    'industry_canonical_common_node_id',
    'industry_native_node_id',
    *ALLOCATION,
)

# Delivered DDI usa_00001.xml, read 2026-11-18. The builder confirms these labels.
DDI_LABELS = {
    'WKSWORK2': {'6': '50-52 weeks'},
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

RULES = {
    'rows': (
        'Every Stage 8 core row with INCWAGE > 0, in Stage 8 source order. '
        'Rows that are not headline stay in the file.'
    ),
    'log_wage_2010': 'The natural log of INCWAGE_CPIU_2010, as Float64.',
    'industry_node_code': (
        'The code part of industry_canonical_common_node_id, unchanged, such as 5614, '
        '623110 or 31-33. This is the join key.'
    ),
    'industry_node_level': (
        'The level part of industry_canonical_common_node_id, such as national_industry.'
    ),
    'industry_delivered_node_code': (
        'The code part of industry_native_node_id, such as 6231. '
        'It is never the headline join key.'
    ),
    'flag_industry_shared_node': (
        "True when another INDNAICS category among the file's rows has the same common node."
    ),
    'flag_any_allocated': (
        'True when any of the ten Q columns is not 0. The headline reads nine of them. '
        'QDEGFIELD is carried and does not enter the headline.'
    ),
    'flag_incwage_topcoded': (
        "True when INCWAGE equals the highest INCWAGE of its state and year among the file's "
        'rows.'
    ),
    'flag_full_time_full_year': (
        'True when UHRSWORK is at least 35 and WKSWORK2 is 6, which IPUMS labels 50-52 weeks.'
    ),
    'flag_wage_salary': (
        'True when CLASSWKRD is 22, 23, 25, 27 or 28: private for-profit, private nonprofit, '
        'federal, state or local employees.'
    ),
    'flag_headline': (
        'True when no headline field is allocated, the row is full time and full year, '
        'flag_wage_salary is true and the node is not shared.'
    ),
}

# A node ID is `naics:2022:<level>:<code>`. Group 1 is the level and group 2 is the code.
NODE_ID = (
    r'^naics:2022:(sector|subsector|industry_group|industry|national_industry):'
    r'(\d{2}-\d{2}|\d{2,6})$'
)
NODE_ID_COLUMNS = ('industry_canonical_common_node_id', 'industry_native_node_id')

TOP_WAGE = '_state_year_top_wage'
SHARED = '_shared_common_node'


def earners(core: pl.LazyFrame) -> pl.LazyFrame:
    '''Return the carried columns of the core rows that have a wage, in source order.

    A null `INCWAGE` stays in, so that `check_inputs` refuses it. Dropping it would hide it.
    '''
    if not set(CARRIED) <= set(core.collect_schema().names()):
        raise ValueError('core table lacks a carried column')
    wage = pl.col('INCWAGE')
    return core.filter(wage.is_null() | (wage > 0)).select(CARRIED)


def check_inputs(earners: pl.LazyFrame) -> None:
    '''Refuse earner rows that break an input rule, with a fixed message.'''
    wage = pl.col('INCWAGE_CPIU_2010')
    found = earners.select(
        pl.any_horizontal(pl.col(*RULE_COLUMNS).is_null()).any().alias('null'),
        (~wage.is_finite() | (wage <= 0) | pl.col('INCWAGE').is_in(INCWAGE_CODES))
        .any()
        .alias('wage'),
        (pl.col('source_row') <= pl.col('source_row').shift(1)).any().alias('order'),
        pl.any_horizontal(
            *(pl.col(name).n_unique().over('INDNAICS') > 1 for name in NODE_ID_COLUMNS)
        )
        .any()
        .alias('nodes'),
        pl.any_horizontal(*(~pl.col(name).str.contains(NODE_ID) for name in NODE_ID_COLUMNS))
        .any()
        .alias('parse'),
    ).collect().row(0, named=True)
    if found['null']:
        raise ValueError('null in a rule column')
    if found['wage']:
        raise ValueError('wage value out of range')
    if found['order']:
        raise ValueError('source rows not strictly increasing')
    if found['nodes']:
        raise ValueError('category maps to more than one node')
    if found['parse']:
        raise ValueError('unparseable NAICS 2022 node ID')


def wage_persons(core: pl.LazyFrame) -> pl.LazyFrame:
    '''Return the lazy wage microdata plan with the carried and the new columns.'''
    rows = earners(core)
    check_inputs(rows)
    shared = (
        rows.group_by('industry_canonical_common_node_id')
        .agg(pl.col('INDNAICS').n_unique().alias('categories'))
        .filter(pl.col('categories') > 1)
        .select('industry_canonical_common_node_id', pl.lit(True).alias(SHARED))
        .collect()
    )
    tops = (
        rows.group_by('STATEFIP', 'YEAR')
        .agg(pl.col('INCWAGE').max().alias(TOP_WAGE))
        .collect()
    )
    no_headline_allocation = pl.all_horizontal(pl.col(*HEADLINE_ALLOCATION) == 0)
    full_time_full_year = (pl.col('UHRSWORK') >= FULL_TIME_HOURS) & (
        pl.col('WKSWORK2') == FULL_YEAR_WKSWORK2
    )
    wage_salary = pl.col('CLASSWKRD').is_in(WAGE_SALARY_CLASSWKRD)
    return (
        rows.join(
            shared.lazy(),
            on='industry_canonical_common_node_id',
            how='left',
            maintain_order='left',
        )
        .join(tops.lazy(), on=['STATEFIP', 'YEAR'], how='left', maintain_order='left')
        .with_columns(
            pl.col('INCWAGE_CPIU_2010').log().alias('log_wage_2010'),
            pl.col('industry_canonical_common_node_id')
            .str.extract(NODE_ID, 2)
            .alias('industry_node_code'),
            pl.col('industry_canonical_common_node_id')
            .str.extract(NODE_ID, 1)
            .alias('industry_node_level'),
            pl.col('industry_native_node_id')
            .str.extract(NODE_ID, 2)
            .alias('industry_delivered_node_code'),
            pl.col(SHARED).fill_null(False).alias('flag_industry_shared_node'),
            pl.any_horizontal(pl.col(*ALLOCATION) != 0).alias('flag_any_allocated'),
            (pl.col('INCWAGE') == pl.col(TOP_WAGE)).alias('flag_incwage_topcoded'),
            full_time_full_year.alias('flag_full_time_full_year'),
            wage_salary.alias('flag_wage_salary'),
        )
        .with_columns(
            (
                no_headline_allocation
                & pl.col('flag_full_time_full_year')
                & pl.col('flag_wage_salary')
                & ~pl.col('flag_industry_shared_node')
            ).alias('flag_headline')
        )
        .select(OUTPUT_COLUMNS)
    )


def summarize(persons: pl.LazyFrame) -> dict:
    '''Return aggregate counts of the wage microdata: the funnel, the flags and the categories.

    The report holds no run ID, time or commit, so that a replay compares equal.
    '''
    no_allocation = pl.all_horizontal(pl.col(*HEADLINE_ALLOCATION) == 0)
    through_hours = no_allocation & pl.col('flag_full_time_full_year')
    through_class = through_hours & pl.col('flag_wage_salary')
    steps = {
        'no_headline_allocation': no_allocation,
        'full_time_full_year': through_hours,
        'wage_salary': through_class,
        'headline': through_class & ~pl.col('flag_industry_shared_node'),
    }
    by_year, categories, shared, headline_categories, levels = pl.collect_all(
        [
            persons.group_by('YEAR').agg(
                pl.len().alias('earners'),
                *(expr.sum().alias(step) for step, expr in steps.items()),
                *(pl.col(flag).sum().alias(flag) for flag in FLAGS),
            ),
            persons.group_by('INDNAICS', 'YEAR').agg(
                pl.len().alias('rows'), pl.col('flag_headline').sum().alias('headline_rows')
            ),
            persons.filter(pl.col('flag_industry_shared_node')).select(
                pl.col('INDNAICS').n_unique().alias('categories'),
                pl.col('industry_canonical_common_node_id').n_unique().alias('nodes'),
            ),
            persons.filter(pl.col('flag_headline'))
            .group_by('YEAR')
            .agg(pl.col('INDNAICS').n_unique().alias('categories')),
            persons.group_by('industry_node_level').agg(
                pl.col('INDNAICS').n_unique().alias('categories'),
                pl.col('flag_headline').sum().alias('headline_rows'),
            ),
        ]
    )
    years = sorted(by_year['YEAR'].to_list())

    def counted(column: str) -> dict:
        found = dict(zip(by_year['YEAR'].to_list(), by_year[column].to_list(), strict=True))
        return {
            'total': sum(found.values()),
            'by_year': {str(year): found[year] for year in years},
        }

    headline_found = dict(
        zip(
            headline_categories['YEAR'].to_list(),
            headline_categories['categories'].to_list(),
            strict=True,
        )
    )
    return {
        'contract': CONTRACT,
        'rows': counted('earners'),
        'funnel': [{'step': step, **counted(step)} for step in ('earners', *steps)],
        'flags': {flag: counted(flag) for flag in FLAGS},
        'categories': categories.sort('INDNAICS', 'YEAR').to_dicts(),
        'headline_categories': {str(year): headline_found.get(year, 0) for year in years},
        'shared_nodes': shared.row(0, named=True),
        'node_levels': {
            row['industry_node_level']: {
                'categories': row['categories'],
                'headline_rows': row['headline_rows'],
            }
            for row in levels.sort('industry_node_level').to_dicts()
        },
    }
