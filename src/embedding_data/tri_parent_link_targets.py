'''Estimate the TRI parent-link target (O7) with its marginal and support tables.

`estimate` takes the facility-years of `tri_facility_years.reduce`, with their `PRIVATE`
columns. An owner is present in an industry in a year when it has a facility-year there. Three
presence sets give the headline and its two sensitivities:

- headline: eligible facility-years, owned by their `owner_key`
- D&B: the same facility-years, owned by their `_dnb_key`
- federal: eligible and federal-excluded facility-years, owned by their `_candidate_key`

`n(a)` counts the owners present in industry `a` in any year. `J(a, b)` counts the owners that
are present in `a` and in `b` in one same year. Each ordered pair with a headline `J` of at least
1 is one target row with `value = J / n(a)`. The result holds the target rows, the marginal and
support tables, and a report of counts. D&B numbers exist in memory only: no output and no
message holds one.
'''

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

import polars as pl

from embedding_data.target_contract import TARGET_SCHEMA, validate_targets

CONTRACT = 'tri-parent-links-v1'
YEARS = (2022, 2023, 2024)
TOLERANCE = 1e-12
METADATA = {
    'source': 'epa_tri',
    'family': 'tri_parent_links',
    'unit_a_type': 'naics_national_industry',
    'unit_b_type': 'naics_national_industry',
    'measure': 'owner_share',
    'se_method': 'none',
    'sample_set': 'tri_basic_ry2022_2024',
    'vintage': 'naics=2022',
}
SIZE_LABEL = 'size_gate_pending'
DNB_LABEL = 'numerator:dnb_key_sensitivity:true'
FEDERAL_LABEL = 'numerator:federal_sensitivity:true'
UNIVERSE = (
    'EPA Toxics Release Inventory basic data files, U.S. files for reporting years 2022–2024, '
    'forms processed as of {date}. TRI is a program-selected population of facilities that '
    'meet its reporting criteria, not a frame of all establishments or firms. Codes are '
    'self-reported primary NAICS 2022 codes, one per facility. A facility can contain more than '
    "one establishment. An owner is EPA's standardized highest-level U.S. parent, or the "
    'facility itself when it reports none. Federal facilities are excluded.')
MARGINAL_SCHEMA = {
    'node_id': pl.String,
    'n_owners': pl.UInt64,
    'n_parent_owners': pl.UInt64,
    'n_multi_industry_owners': pl.UInt64,
    'n_facilities': pl.UInt64,
    'n_facility_years': pl.UInt64,
    'n_owners_dnb': pl.UInt64,
    'n_owners_including_federal': pl.UInt64,
    'n_owners_partial': pl.UInt64,
}
SUPPORT_SCHEMA = {
    'unit_a': pl.String,
    'unit_b': pl.String,
    'j_owners': pl.UInt64,
    'j_2022': pl.UInt64,
    'j_2023': pl.UInt64,
    'j_2024': pl.UInt64,
    'j_dnb': pl.UInt64,
    'j_including_federal': pl.UInt64,
}
PARTIAL_REASONS = ('naics_missing', 'naics_conflict', 'naics_not_2022', 'parent_conflict')
PARENT_PREFIX = 'parent:'
THRESHOLDS = (1, 2, 3, 5, 10)
REASON = pl.col('exclusion_reason')
ELIGIBLE = REASON.is_null()
# name -> (column that holds the owner key, rows that count)
VARIANTS = {
    'headline': ('owner_key', ELIGIBLE),
    'dnb': ('_dnb_key', ELIGIBLE),
    'federal': ('_candidate_key', ELIGIBLE | (REASON == 'federal')),
}


@dataclass(frozen=True)
class ParentLinks:
    '''The target rows, the marginal and support tables, and the counts-only report.'''

    targets: pl.DataFrame
    marginals: pl.DataFrame
    support: pl.DataFrame
    report: dict


def name_collisions(names: Iterable[str]) -> dict[str, int]:
    '''The groups of distinct names that differ only in case or whitespace.

    Names group by `' '.join(name.casefold().split())`. `keys` counts the groups with more
    than one name, and `names` counts the names in those groups.
    '''
    groups: defaultdict[str, set[str]] = defaultdict(set)
    for name in names:
        groups[' '.join(name.casefold().split())].add(name)
    several = [group for group in groups.values() if len(group) > 1]
    return {'keys': len(several), 'names': sum(len(group) for group in several)}


def distribution(values: Iterable[int]) -> dict[str, int | None]:
    '''The count, extremes, nearest-rank percentiles and cumulative counts of the values.

    The p-th percentile is the sorted value at the 1-based rank `ceil(p / 100 * count)`, and
    the median is the 50th. With no values, `count` and each `ge_<k>` are 0 and the rest null.
    '''
    ordered = sorted(values)
    count = len(ordered)

    def nearest_rank(percent: int) -> int | None:
        return ordered[(percent * count + 99) // 100 - 1] if count else None

    return {
        'count': count,
        'min': ordered[0] if count else None,
        'p25': nearest_rank(25),
        'median': nearest_rank(50),
        'p75': nearest_rank(75),
        'p90': nearest_rank(90),
        'max': ordered[-1] if count else None,
        **{f'ge_{k}': sum(value >= k for value in ordered) for k in THRESHOLDS},
    }


def _typed(frame: pl.DataFrame, schema: dict[str, pl.DataType]) -> pl.DataFrame:
    '''The frame's columns in the order and types of the schema.'''
    return frame.select(*(pl.col(name).cast(dtype) for name, dtype in schema.items()))


def _check_years(frame: pl.DataFrame) -> None:
    if not frame['reporting_year'].is_in(list(YEARS)).fill_null(False).all():
        raise ValueError('reporting year outside the window')


def _presence(frame: pl.DataFrame, owner: str, rows: pl.Expr) -> pl.DataFrame:
    '''The `owner`, `year` and `node` of the rows, with the owner read from a column.

    A repeat stays: every count of the estimate is a distinct count.
    '''
    presence = frame.filter(rows).select(
        pl.col(owner).alias('owner'),
        pl.col('reporting_year').alias('year'),
        pl.col('naics_2022_node_id').alias('node'),
    )
    if any(presence.null_count().row(0)):
        raise ValueError('owner or node is null')
    return presence


def _pairs(presence: pl.DataFrame) -> pl.DataFrame:
    '''The `owner`, `year`, `node` and `node_b` of each ordered pair of industries in one year.'''
    return presence.join(presence, on=['owner', 'year'], suffix='_b').filter(
        pl.col('node') != pl.col('node_b'))


def _joint(pairs: pl.DataFrame, years: tuple[int, ...] = ()) -> pl.DataFrame:
    '''The owners of each ordered pair: `j_owners` over all years, then `j_<year>` by year.'''
    return pairs.group_by('node', 'node_b').agg(
        pl.col('owner').n_unique().alias('j_owners'),
        *(pl.col('owner').filter(pl.col('year') == year).n_unique().alias(f'j_{year}')
          for year in years))


def _by_node(presence: pl.DataFrame, name: str) -> pl.DataFrame:
    return presence.group_by('node').agg(pl.col('owner').n_unique().alias(name))


def _support(pairs: dict[str, pl.DataFrame]) -> pl.DataFrame:
    '''One row for each headline cell, with its counts under both sensitivities.'''
    support = _joint(pairs['headline'], YEARS)
    for name, column in (('dnb', 'j_dnb'), ('federal', 'j_including_federal')):
        other = _joint(pairs[name]).select(
            'node', 'node_b', pl.col('j_owners').alias(column))
        support = support.join(other, on=['node', 'node_b'], how='left')
    return _typed(
        support.rename({'node': 'unit_a', 'node_b': 'unit_b'})
        .with_columns(pl.col('j_dnb', 'j_including_federal').fill_null(0))
        .sort('unit_a', 'unit_b'),
        SUPPORT_SCHEMA)


def _partial(frame: pl.DataFrame, headline: pl.DataFrame) -> pl.DataFrame:
    '''The `owner` and `node` of each place where the owner is partial, with repeats.

    An owner is partial for a node when it is present there in a year and, in that same year,
    a facility-year excluded for a partial reason lists it among its membership keys.
    '''
    owned = (frame.filter(REASON.is_in(list(PARTIAL_REASONS)))
             .select(pl.col('reporting_year').alias('year'),
                     pl.col('_membership_keys').alias('owner'))
             .explode('owner'))
    return headline.join(owned, on=['owner', 'year'], how='inner').select('owner', 'node')


def _marginals(frame: pl.DataFrame, presence: dict[str, pl.DataFrame], pairs: pl.DataFrame,
               partial: pl.DataFrame) -> pl.DataFrame:
    '''One row for each industry that has a headline owner, sorted by node ID.'''
    owner = pl.col('owner')
    headline = presence['headline'].group_by('node').agg(
        owner.n_unique().alias('n_owners'),
        owner.filter(owner.str.starts_with(PARENT_PREFIX)).n_unique().alias('n_parent_owners'))
    facilities = frame.filter(ELIGIBLE).group_by(pl.col('naics_2022_node_id').alias('node')).agg(
        pl.col('trifd').n_unique().alias('n_facilities'), pl.len().alias('n_facility_years'))
    joined = headline
    for extra in (_by_node(pairs, 'n_multi_industry_owners'), facilities,
                  _by_node(presence['dnb'], 'n_owners_dnb'),
                  _by_node(presence['federal'], 'n_owners_including_federal'),
                  _by_node(partial, 'n_owners_partial')):
        joined = joined.join(extra, on='node', how='left')
    return _typed(
        joined.rename({'node': 'node_id'}).with_columns(pl.exclude('node_id').fill_null(0))
        .sort('node_id'),
        MARGINAL_SCHEMA)


def _flags() -> pl.Expr:
    '''The labels of a cell, in sorted order, from its `j_owners`, `j_dnb` and federal count.'''
    return pl.concat_list(
        pl.when(pl.col('j_dnb') != pl.col('j_owners')).then(pl.lit(DNB_LABEL)),
        pl.when(pl.col('j_including_federal') != pl.col('j_owners')).then(pl.lit(FEDERAL_LABEL)),
        pl.lit(SIZE_LABEL),
    ).list.drop_nulls()


def _targets(support: pl.DataFrame, marginals: pl.DataFrame, universe: str) -> pl.DataFrame:
    '''The target rows of the support table: `value = J / n(a)`, in `TARGET_SCHEMA`.

    `n_weighted` is `float(J)`: `_typed` casts the count. The rows keep the order of `support`.
    '''
    owners = dict(marginals.select('node_id', 'n_owners').iter_rows())
    return _typed(
        support.select(
            pl.lit(METADATA['source']).alias('source'),
            pl.lit(METADATA['family']).alias('family'),
            pl.lit(METADATA['unit_a_type']).alias('unit_a_type'),
            'unit_a',
            pl.lit(METADATA['unit_b_type']).alias('unit_b_type'),
            'unit_b',
            pl.lit(METADATA['measure']).alias('measure'),
            (pl.col('j_owners') / pl.col('unit_a').replace_strict(owners)).alias('value'),
            pl.lit(None, dtype=pl.Float64).alias('se'),
            pl.lit(METADATA['se_method']).alias('se_method'),
            pl.col('j_owners').alias('n_unweighted'),
            pl.col('j_owners').alias('n_weighted'),
            pl.lit(METADATA['sample_set']).alias('sample_set'),
            pl.lit(METADATA['vintage']).alias('vintage'),
            pl.lit(universe).alias('universe'),
            _flags().alias('flags')),
        TARGET_SCHEMA)


def _owner_counts(presence: dict[str, pl.DataFrame], year: int | None = None) -> dict[str, int]:
    '''The distinct owners of each presence set, in one year or in all.'''
    return {name: (rows if year is None else rows.filter(pl.col('year') == year))[
        'owner'].n_unique() for name, rows in presence.items()}


def _report(frame: pl.DataFrame, presence: dict[str, pl.DataFrame],
            pairs: dict[str, pl.DataFrame], partial: pl.DataFrame,
            targets: pl.DataFrame) -> dict:
    '''The counts of the estimate, as plain integers, strings and nulls.'''
    headline = _joint(pairs['headline'])

    def only(name: str) -> int:
        '''The ordered cells of a sensitivity that have no headline owner.'''
        return _joint(pairs[name]).join(headline, on=['node', 'node_b'], how='anti').height

    changes = (frame.filter(ELIGIBLE).group_by('trifd')
               .agg(pl.col('owner_key').n_unique().alias('n')).filter(pl.col('n') > 1).height)
    return {
        'n_owners': _owner_counts(presence),
        'owners_by_year': {str(year): _owner_counts(presence, year) for year in YEARS},
        'partial_owners': partial['owner'].n_unique(),
        'cells_only_dnb': only('dnb'),
        'cells_only_federal': only('federal'),
        'n_unweighted_distribution': distribution(targets['n_unweighted'].to_list()),
        'owner_key_changes': changes,
        'parent_name_collisions': name_collisions(
            frame['parent_names'].explode().drop_nulls().to_list()),
    }


def estimate(frame: pl.DataFrame, *, processed_as_of: date) -> ParentLinks:
    '''The parent-link target of the facility-years, with its companions and report.

    `frame` is the output of `tri_facility_years.reduce`, with its `PRIVATE` columns. A
    reporting year outside `YEARS`, or a null owner key or node in a row that a presence set
    counts, raises `ValueError` with a fixed message. `targets`, `marginals` and `support` are
    sorted by their keys, so the result does not depend on the order of the rows.
    '''
    _check_years(frame)
    presence = {name: _presence(frame, owner, rows) for name, (owner, rows) in VARIANTS.items()}
    pairs = {name: _pairs(rows) for name, rows in presence.items()}
    partial = _partial(frame, presence['headline'])
    support = _support(pairs)
    marginals = _marginals(frame, presence, pairs['headline'], partial)
    targets = _targets(support, marginals, UNIVERSE.format(date=processed_as_of.isoformat()))
    return ParentLinks(targets=targets, marginals=marginals, support=support,
                       report=_report(frame, presence, pairs, partial, targets))


def _require(holds: bool, message: str) -> None:
    if not holds:
        raise ValueError(message)


def _has_universe(text: str) -> bool:
    '''Whether the text is `UNIVERSE` with an ISO date in place of `{date}`.'''
    prefix, suffix = UNIVERSE.split('{date}')
    try:
        stamp = date.fromisoformat(text[len(prefix):len(text) - len(suffix)])
    except ValueError:
        return False
    return text == UNIVERSE.format(date=stamp.isoformat())


def _check_rows(targets: pl.DataFrame) -> None:
    '''The metadata, universe and weighted count that every target row must carry.'''
    for column, value in METADATA.items():
        _require(targets[column].eq(value).all(), 'targets metadata differs')
    universes = targets['universe'].unique().to_list()
    _require(len(universes) <= 1 and all(map(_has_universe, universes)),
             'targets universe differs')
    _require(targets['n_weighted'].equals(targets['n_unweighted'].cast(pl.Float64)),
             'targets n_weighted differs from n_unweighted')


def _check_cells(targets: pl.DataFrame, node_ids: frozenset[str]) -> None:
    '''The units, diagonal, count and mirror rules of the target cells.'''
    _require(set(targets['unit_a']) | set(targets['unit_b']) <= node_ids,
             'unit is not a selected node')
    _require(not (targets['unit_a'] == targets['unit_b']).any(), 'diagonal cell')
    _require(not (targets['n_unweighted'] == 0).any(), 'cell count below one')
    forward = targets.select('unit_a', 'unit_b', 'n_unweighted')
    backward = forward.rename({'unit_a': 'unit_b', 'unit_b': 'unit_a'}).select(forward.columns)
    _require(forward.join(backward, on=forward.columns, how='anti').is_empty(),
             'cell has no mirror')


def _check_marginals(marginals: pl.DataFrame, targets: pl.DataFrame,
                     node_ids: frozenset[str]) -> None:
    '''The marginal rows are unique, sorted, selected, owned and cover every target unit.'''
    ids = marginals['node_id']
    _require(ids.is_unique().all() and ids.equals(ids.sort()), 'marginals not unique and sorted')
    _require(set(ids) <= node_ids, 'marginal node is not a selected node')
    _require(not (marginals['n_owners'] == 0).any(), 'marginal owner count below one')
    _require(set(targets['unit_a']) <= set(ids), 'target unit has no marginal row')


def _check_counts(targets: pl.DataFrame, marginals: pl.DataFrame) -> None:
    '''`value = J / n(a)` within the tolerance, and `J` at most `n(a)`.

    The mirror row gives `J` at most `n(b)`. A marginal `n_owners` that differs from the owner
    count the values imply fails the first check.
    '''
    counts = targets.join(
        marginals.select(pl.col('node_id').alias('unit_a'), 'n_owners'), on='unit_a')
    gap = (counts['value'] - counts['n_unweighted'] / counts['n_owners']).abs()
    _require(not (gap > TOLERANCE).any(),
             'value differs from the cell count over the owner count')
    _require(not (counts['n_unweighted'] > counts['n_owners']).any(),
             'cell count above an owner count')


def _check_support(targets: pl.DataFrame, support: pl.DataFrame) -> None:
    '''The support rows are the target cells, sorted, with equal counts and the flags they give.'''
    cells = targets.select('unit_a', 'unit_b', pl.col('n_unweighted').alias('j_owners')).sort(
        'unit_a', 'unit_b')
    _require(support.select('unit_a', 'unit_b').equals(cells.select('unit_a', 'unit_b')),
             'support rows differ from the target cells')
    _require(support['j_owners'].equals(cells['j_owners']),
             'support count differs from the target count')
    joined = targets.select('unit_a', 'unit_b', 'flags').join(
        support, on=['unit_a', 'unit_b'], how='left')
    _require(joined['flags'].equals(joined.select(_flags()).to_series()),
             'flags differ from the support counts')


def validate_parent_links(result: ParentLinks, node_ids: frozenset[str]) -> None:
    '''Require the target, marginal and support tables to agree. A failure raises `ValueError`.

    The messages are fixed and hold no cell value. `validate_targets` runs first. Then the
    rows carry the metadata, the units are selected nodes, and no cell is on the diagonal or
    below one. Each cell has its mirror with an equal count. Each value is the cell count over
    the first unit's marginal owner count, so a marginal that differs from the owners the values
    imply fails here, and no cell count exceeds its first unit's owner count. The support rows
    are the sorted target cells with equal counts, and the flags follow the support counts.
    '''
    targets, marginals, support = result.targets, result.marginals, result.support
    validate_targets(targets)
    _require(list(marginals.schema.items()) == list(MARGINAL_SCHEMA.items()),
             'marginals schema differs')
    _require(list(support.schema.items()) == list(SUPPORT_SCHEMA.items()),
             'support schema differs')
    _check_rows(targets)
    _check_cells(targets, node_ids)
    _check_marginals(marginals, targets, node_ids)
    _check_counts(targets, marginals)
    _check_support(targets, support)
