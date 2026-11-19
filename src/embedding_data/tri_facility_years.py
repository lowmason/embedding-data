'''Reduce TRI form rows to one row per facility-year, with its eligibility and owner keys.

`reduce` takes the rows of `tri_reader` and returns `TABLE_SCHEMA` and then `PRIVATE`
columns, sorted by `reporting_year` and `trifd`. A facility-year is one TRIFD in one
reporting year, grouped as delivered. Every set of strings (form type, federal flag, "no
parent", "no D&B number") comes from the layout of the row's own year. A blank cell is
absence, so a blank standardized parent never names a parent and a blank D&B cell is never
a usable number. A blank TRIFD, a form type or federal value outside the year's sets, or a
year with no layout raises `ValueError` with a fixed message. No message holds a cell value.

`PRIVATE` columns hold D&B numbers and reported parent names. They are for the later
tables and counts and are never published: `public` drops them. `year_report` returns
counts only.
'''

import polars as pl

from embedding_data.tri_codes import NODE_PREFIX
from embedding_data.tri_layout import HeaderLayout
from embedding_data.tri_reader import NAICS_FIELDS

CONTRACT = 'tri-facility-years-v1'
EXCLUSIONS = ('naics_missing', 'naics_conflict', 'naics_not_2022', 'parent_conflict', 'federal')
TERRITORIES = ('AS', 'GU', 'MP', 'PR', 'VI')
TABLE_SCHEMA = {
    'reporting_year': pl.Int64,
    'trifd': pl.String,
    'n_forms': pl.UInt64,
    'n_form_r': pl.UInt64,
    'n_form_a': pl.UInt64,
    'primary_naics_values': pl.List(pl.String),
    'other_naics_values': pl.List(pl.String),
    'naics_2022_node_id': pl.String,
    'parent_names': pl.List(pl.String),
    'foreign_parent_names': pl.List(pl.String),
    'federal_values': pl.List(pl.String),
    'state_values': pl.List(pl.String),
    'flag_parent_mixed_blank': pl.Boolean,
    'owner_key': pl.String,
    'exclusion_reason': pl.String,
}
PRIVATE = {
    '_candidate_key': pl.String,
    '_membership_keys': pl.List(pl.String),
    '_dnb_key': pl.String,
    '_reported_names': pl.List(pl.String),
    '_usable_dnb': pl.List(pl.String),
}
FULL_SCHEMA = {**TABLE_SCHEMA, **PRIVATE}
SIX_DIGITS = '^[0-9]{6}$'


def _strings(values: frozenset[str] | set[str]) -> pl.Series:
    '''A value set as one typed list for `is_in`, so that an empty set still matches strings.'''
    return pl.Series(sorted(values), dtype=pl.String).implode()


def _clean(column: str, absent: frozenset[str] = frozenset()) -> pl.Expr:
    '''The column stripped, and null when it is blank or one of the `absent` strings.'''
    value = pl.col(column).str.strip_chars()
    return pl.when(value.is_in(_strings(absent)) | (value == '')).then(None).otherwise(value)


def _layout(layouts: dict[int, HeaderLayout], year: int) -> HeaderLayout:
    if year not in layouts:
        raise ValueError('no layout for year')
    return layouts[year]


def _years(frame: pl.DataFrame, layouts: dict[int, HeaderLayout]) -> list[int]:
    '''The sorted years of the rows, each checked for a layout.'''
    years = sorted(frame['year'].unique().to_list())
    for year in years:
        _layout(layouts, year)
    return years


def _prepare(rows: pl.DataFrame, layout: HeaderLayout) -> pl.DataFrame:
    '''The rows of one year with their checked flags and cleaned values as `_` columns.'''
    sets = layout.values
    if rows['trifd'].str.strip_chars().eq('').any():
        raise ValueError('blank trifd')
    if not rows['form_type'].is_in(_strings(sets['form_r'] | sets['form_a'])).all():
        raise ValueError('unregistered form type')
    if not rows['federal'].is_in(_strings(sets['federal_yes'] | sets['federal_no'])).all():
        raise ValueError('unregistered federal value')
    return rows.with_columns(
        pl.col('form_type').is_in(_strings(sets['form_r'])).alias('_form_r'),
        pl.col('form_type').is_in(_strings(sets['form_a'])).alias('_form_a'),
        pl.col('federal').is_in(_strings(sets['federal_yes'])).alias('_federal'),
        _clean('primary_naics').alias('_primary'),
        pl.concat_list([_clean(name) for name in NAICS_FIELDS]).alias('_other'),
        _clean('standardized_parent', sets['no_parent']).alias('_parent'),
        _clean('standardized_foreign_parent', sets['no_parent']).alias('_foreign'),
        _clean('parent_name', sets['no_parent']).alias('_reported'),
        _clean('parent_dnb', sets['no_dnb']).alias('_dnb'),
    )


def _distinct(column: str) -> pl.Expr:
    '''The sorted distinct values of a column that are not null, within one group.'''
    return pl.col(column).drop_nulls().unique().sort()


def _node_id(node_ids: frozenset[str]) -> pl.Expr:
    '''The prefixed primary code when it is the only one, six digits and a selected node.'''
    primary = pl.col('primary_naics_values')
    node = pl.lit(NODE_PREFIX) + primary.list.first()
    valid = ((primary.list.len() == 1) & primary.list.first().str.contains(SIX_DIGITS)
             & node.is_in(_strings(node_ids)))
    return pl.when(valid).then(node).otherwise(None).alias('naics_2022_node_id')


def _exclusion() -> pl.Expr:
    '''The first failing rule, in the order of `EXCLUSIONS`, and null when none fails.'''
    missing, conflict, not_2022, parent_conflict, federal = EXCLUSIONS
    primaries = pl.col('primary_naics_values').list.len()
    return (pl.when(primaries == 0).then(pl.lit(missing))
            .when(primaries > 1).then(pl.lit(conflict))
            .when(pl.col('naics_2022_node_id').is_null()).then(pl.lit(not_2022))
            .when(pl.col('parent_names').list.len() > 1).then(pl.lit(parent_conflict))
            .when(pl.col('_is_federal')).then(pl.lit(federal))
            .otherwise(None).alias('exclusion_reason'))


def _facility_years(rows: pl.DataFrame, layout: HeaderLayout,
                    node_ids: frozenset[str]) -> pl.DataFrame:
    '''One year's rows reduced to facility-years, in `FULL_SCHEMA` and in no set order.'''
    names = pl.col('parent_names')
    dnb = pl.col('_usable_dnb')
    trifd = pl.col('trifd')
    candidate = (pl.when(names.list.len() == 1).then(pl.lit('parent:') + names.list.first())
                 .when(names.list.len() == 0).then(pl.lit('facility:') + trifd)
                 .otherwise(None))
    grouped = _prepare(rows, layout).group_by('year', 'trifd').agg(
        pl.len().alias('n_forms'),
        pl.col('_form_r').sum().alias('n_form_r'),
        pl.col('_form_a').sum().alias('n_form_a'),
        _distinct('_primary').alias('primary_naics_values'),
        pl.col('_other').explode().drop_nulls().unique().sort().alias('other_naics_values'),
        _distinct('_parent').alias('parent_names'),
        _distinct('_foreign').alias('foreign_parent_names'),
        pl.col('federal').unique().sort().alias('federal_values'),
        pl.col('state').unique().sort().alias('state_values'),
        (pl.col('_parent').is_not_null().any() & pl.col('_parent').is_null().any())
        .alias('flag_parent_mixed_blank'),
        pl.col('_federal').any().alias('_is_federal'),
        _distinct('_reported').alias('_reported_names'),
        _distinct('_dnb').alias('_usable_dnb'),
    )
    return (grouped
            .rename({'year': 'reporting_year'})
            .with_columns(_node_id(node_ids))
            .with_columns(_exclusion())
            .with_columns(
                candidate.alias('_candidate_key'),
                pl.when(names.list.len() == 0).then(pl.concat_list(pl.lit('facility:') + trifd))
                .otherwise(names.list.eval(pl.lit('parent:') + pl.element()))
                .alias('_membership_keys'),
                pl.when(dnb.list.len() == 1).then(pl.lit('dnb:') + dnb.list.first())
                .otherwise(pl.lit('facility:') + trifd).alias('_dnb_key'))
            .with_columns(
                pl.when(pl.col('exclusion_reason').is_null()).then(pl.col('_candidate_key'))
                .otherwise(None).alias('owner_key'))
            .select(*(pl.col(name).cast(dtype) for name, dtype in FULL_SCHEMA.items())))


def reduce(rows: pl.LazyFrame, layouts: dict[int, HeaderLayout],
           node_ids: frozenset[str]) -> pl.DataFrame:
    '''The facility-years of the rows: `TABLE_SCHEMA` and `PRIVATE`, sorted by year and TRIFD.

    The lazy rows are collected once. A year with no layout, a blank TRIFD and an
    unregistered form type or federal value raise `ValueError`.
    '''
    frame = rows.collect()
    parts = [
        _facility_years(frame.filter(pl.col('year') == year), layouts[year], node_ids)
        for year in _years(frame, layouts)
    ]
    if not parts:
        return pl.DataFrame(schema=FULL_SCHEMA)
    return pl.concat(parts).sort('reporting_year', 'trifd')


def public(frame: pl.DataFrame) -> pl.DataFrame:
    '''The published columns of a reduced frame: `TABLE_SCHEMA` and nothing private.'''
    return frame.select(list(TABLE_SCHEMA))


def validate_facility_years(table: pl.DataFrame, source_rows: int) -> None:
    '''Require the published table to be exact. Any failed check raises `ValueError`.

    The checks are the schema, a unique sorted key, form counts that add up to the source
    rows, and owner keys, exclusion reasons and node IDs that agree with each other.
    '''
    if list(table.schema.items()) != list(TABLE_SCHEMA.items()):
        raise ValueError('schema differs')
    key = table.select('reporting_year', 'trifd')
    if (key.null_count().row(0) != (0, 0) or key.is_duplicated().any()
            or not key.equals(key.sort('reporting_year', 'trifd'))):
        raise ValueError('key not unique and sorted')
    if table['n_forms'].sum() != source_rows:
        raise ValueError('n_forms differ from source rows')
    if not table.select((pl.col('n_forms') == pl.col('n_form_r') + pl.col('n_form_a')).all()
                        ).item():
        raise ValueError('n_forms not the sum of form types')
    reason = pl.col('exclusion_reason')
    if not table.select((pl.col('owner_key').is_null() == reason.is_not_null()).all()).item():
        raise ValueError('owner_key and exclusion_reason disagree')
    if not table.select(reason.is_null() | reason.is_in(_strings(set(EXCLUSIONS)))).to_series(
            ).all():
        raise ValueError('unknown exclusion reason')
    has_node = reason.is_null() | reason.is_in(_strings({'parent_conflict', 'federal'}))
    if not table.select((pl.col('naics_2022_node_id').is_not_null() == has_node).all()).item():
        raise ValueError('node ID and exclusion_reason disagree')


def _several(rows: pl.DataFrame, key: str, other: str) -> int:
    '''The distinct `key` values on rows that hold at least two distinct `other` values.

    Only rows with both a `key` and an `other` value count.
    '''
    both = rows.filter(pl.col(key).is_not_null() & pl.col(other).is_not_null())
    several = both.group_by(key).agg(pl.col(other).n_unique().alias('n')).filter(pl.col('n') > 1)
    return several.height


def _count(mask: pl.Series) -> int:
    return int(mask.sum())


def _year_counts(rows: pl.DataFrame, table: pl.DataFrame, layout: HeaderLayout) -> dict:
    '''The counts of one year, from its prepared rows and its facility-years.'''
    has_parent = table['parent_names'].list.len() > 0
    has_reported = table['_reported_names'].list.len() > 0
    one_dnb = table['_usable_dnb'].list.len() == 1
    reasons = table['exclusion_reason']
    reported = layout.columns['parent_name'] is not None
    in_territory = table['state_values'].list.eval(
        pl.element().is_in(_strings(set(TERRITORIES)))).list.any()
    return {
        'rows': rows.height,
        'rows_by_form_type': {
            'form_r': _count(rows['_form_r']),
            'form_a': _count(rows['_form_a']),
        },
        'facility_years': table.height,
        'facility_years_by_reason': {
            'eligible': _count(reasons.is_null()),
            **{reason: _count(reasons == reason) for reason in EXCLUSIONS},
        },
        'with_parent': _count(has_parent),
        'with_usable_dnb': _count(table['_usable_dnb'].list.len() > 0),
        'names_with_several_dnb': _several(rows, '_parent', '_dnb'),
        'dnb_with_several_names': _several(rows, '_dnb', '_parent'),
        'mixed_blank': _count(table['flag_parent_mixed_blank']),
        'with_foreign_parent': _count(table['foreign_parent_names'].list.len() > 0),
        'with_secondary_codes': _count(table['other_naics_values'].list.len() > 0),
        'in_territories': _count(in_territory) if layout.columns['state'] else None,
        'case_a': _count(~has_reported & has_parent) if reported else None,
        'case_b': _count(has_reported & ~has_parent) if reported else None,
        'case_c': _count(one_dnb & ~has_parent),
        'missing_fields': list(layout.missing),
    }


def year_report(rows: pl.LazyFrame, frame: pl.DataFrame,
                layouts: dict[int, HeaderLayout]) -> dict[str, dict]:
    '''The counts of each year of the rows, keyed by the year string.

    `frame` is the output of `reduce` for the same rows, with its `PRIVATE` columns. The
    report holds counts only, never a D&B number or a name.
    '''
    collected = rows.collect()
    return {
        str(year): _year_counts(
            _prepare(collected.filter(pl.col('year') == year), layouts[year]),
            frame.filter(pl.col('reporting_year') == year), layouts[year])
        for year in _years(collected, layouts)
    }
