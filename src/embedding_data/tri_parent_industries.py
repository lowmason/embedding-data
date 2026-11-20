'''List the NAICS 2022 industries of each TRI parent (O8), with a validator and a report.

`build_parent_industries` takes the facility-years of `tri_facility_years.reduce`. It keeps the
eligible facility-years whose owner key names a parent (`parent:<standardized name>`) and
leaves out the self-owned facilities, so a parent is only a name that EPA gives. The table
holds one row for each parent and industry: the distinct TRIFDs of the parent in that
industry, its facility-years, and its distinct TRIFDs in each reporting year. The table lists
the child industries of a parent. It does not give the industry of the parent, which TRI does
not report. The table holds counts and parent names and its report holds counts only. Neither
holds a D&B number.
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


def _parent_rows(frame: pl.DataFrame) -> pl.DataFrame:
    '''The eligible facility-years with a `parent:` owner key, with `parent_name` added.

    `parent_name` is the owner key without its prefix, as the exact string.
    '''
    return (frame.filter(ELIGIBLE & pl.col('owner_key').str.starts_with(PARENT_PREFIX))
            .with_columns(pl.col('owner_key').str.strip_prefix(PARENT_PREFIX).alias('parent_name')))


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
    parents = _parent_rows(frame)
    _require(parents['naics_2022_node_id'].null_count() == 0, 'node is null')
    trifd = pl.col('trifd')
    return (parents
            .group_by('parent_name', pl.col('naics_2022_node_id').alias('node_id'))
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


def parent_report(table: pl.DataFrame, frame: pl.DataFrame) -> dict:
    '''The number of parents and the distributions of facilities and industries per parent.

    `frame` is the output of `tri_facility_years.reduce` that the table was built from.
    `facilities_per_parent` is the number of distinct TRIFDs of each parent across all years
    and industries, counted in the eligible `parent:` facility-years of `frame`, so a facility
    that changes industry between years counts once. `industries_per_parent` is the number of
    table rows of each parent, and `n_parents` the number of parent names in the table. Each
    distribution has the shape of `distribution`. If the parents of the table and of `frame`
    are not the same set, a `ValueError` with a fixed message holding no name is raised. The
    report holds counts only, never a parent name.
    '''
    facilities = _parent_rows(frame).group_by('parent_name').agg(
        pl.col('trifd').n_unique().alias('facilities'))
    industries = table.group_by('parent_name').agg(pl.len().alias('industries'))
    _require(set(industries['parent_name']) == set(facilities['parent_name']),
             'parents differ from the facility-years')
    return {
        'n_parents': industries.height,
        'facilities_per_parent': distribution(facilities['facilities'].to_list()),
        'industries_per_parent': distribution(industries['industries'].to_list()),
    }
