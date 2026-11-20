'''List the NAICS 2022 industries of each TRI parent (O8), with a validator and a report.

`build_parent_industries` takes the facility-years of `tri_facility_years.reduce`. It keeps the
eligible facility-years whose owner key names a parent (`parent:<standardized name>`) and
leaves out the self-owned facilities, so a parent is only a name that EPA gives. The table
holds one row for each parent and industry: the distinct TRIFDs of the parent in that
industry, its facility-years, and its distinct TRIFDs in each reporting year. The table lists
the child industries of a parent. It does not give the industry of the parent, which TRI does
not report. The table and its report hold counts and parent names, never a D&B number.
'''

import polars as pl

from embedding_data.tri_parent_link_targets import (
    ELIGIBLE,
    PARENT_PREFIX,
    YEARS,
    distribution,
)

SCHEMA = {
    'parent_name': pl.String,
    'node_id': pl.String,
    'n_facilities': pl.UInt64,
    'n_facility_years': pl.UInt64,
    **{f'f_{year}': pl.UInt64 for year in YEARS},
}
KEY = ['parent_name', 'node_id']


def _require(holds: bool, message: str) -> None:
    if not holds:
        raise ValueError(message)


def build_parent_industries(frame: pl.DataFrame) -> pl.DataFrame:
    '''One row for each parent and industry of the eligible facility-years, sorted by the key.

    `frame` is the output of `tri_facility_years.reduce`. `parent_name` is the owner key
    without its `parent:` prefix, as the exact string. `n_facilities` counts the distinct
    TRIFDs, `n_facility_years` the facility-years and `f_<year>` the distinct TRIFDs of that
    year (0 when there are none). A facility that changes industry between years counts once
    in the row of each industry. A reporting year outside `YEARS`, and a null node in a row
    that the table counts, raise `ValueError` with a fixed message.
    '''
    _require(frame['reporting_year'].is_in(list(YEARS)).fill_null(False).all(),
             'reporting year outside the window')
    parents = frame.filter(ELIGIBLE & pl.col('owner_key').str.starts_with(PARENT_PREFIX))
    _require(parents['naics_2022_node_id'].null_count() == 0, 'node is null')
    trifd = pl.col('trifd')
    return (parents
            .group_by(pl.col('owner_key').str.strip_prefix(PARENT_PREFIX).alias('parent_name'),
                      pl.col('naics_2022_node_id').alias('node_id'))
            .agg(trifd.n_unique().alias('n_facilities'),
                 pl.len().alias('n_facility_years'),
                 *(trifd.filter(pl.col('reporting_year') == year).n_unique().alias(f'f_{year}')
                   for year in YEARS))
            .select(*(pl.col(name).cast(dtype) for name, dtype in SCHEMA.items()))
            .sort(KEY))


def validate_parent_industries(table: pl.DataFrame, frame: pl.DataFrame) -> None:
    '''Require the table to be the one that `build_parent_industries` gives for the frame.

    A failure raises `ValueError` with a fixed message that holds no parent name, node ID or
    count. The checks run in this order: the schema, a unique sorted key without nulls, the
    set of parents, the set of rows, and every count. The table is built again from `frame`
    with the same rules, so a count that is too high or too low, a missing or extra row, a
    parent that has no eligible `parent:` facility-year and a parent that the table lacks all
    fail. A year outside `YEARS` in `frame` fails with the message of the build.
    '''
    _require(list(table.schema.items()) == list(SCHEMA.items()), 'schema differs')
    key = table.select(KEY)
    _require(key.null_count().row(0) == (0, 0) and not key.is_duplicated().any()
             and key.equals(key.sort(KEY)), 'key not unique and sorted')
    expected = build_parent_industries(frame)
    _require(set(table['parent_name']) == set(expected['parent_name']),
             'parents differ from the facility-years')
    _require(key.equals(expected.select(KEY)), 'rows differ from the facility-years')
    _require(table.equals(expected), 'counts differ from the facility-years')


def parent_report(table: pl.DataFrame) -> dict:
    '''The number of parents and the distributions of facilities and industries per parent.

    `facilities_per_parent` is the sum of `n_facilities` over the rows of a parent, so a
    facility that changes industry between years counts once for each industry. The table
    does not say which rows share a TRIFD. `industries_per_parent` is the number of rows of a
    parent. Each distribution has the shape of `distribution`. The report holds counts only,
    never a parent name.
    '''
    per_parent = table.group_by('parent_name').agg(
        pl.col('n_facilities').sum().alias('facilities'), pl.len().alias('industries'))
    return {
        'n_parents': per_parent.height,
        'facilities_per_parent': distribution(per_parent['facilities'].to_list()),
        'industries_per_parent': distribution(per_parent['industries'].to_list()),
    }
