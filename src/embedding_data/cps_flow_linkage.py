'''Value classes, the monthly panel and the person-month links of the CPS job flows.

Every delivered `IND`, `OCC`, `INDLY` and `OCCLY` value falls in one class: mapped, not in
universe or special. Anything else fails the build. The monthly panel carries a source row and
a month index, and its links join one person in two months. A failure raises a fixed message
and never names a value or a `CPSIDV`.
'''

import polars as pl

from embedding_data.cps_flow_units import UNIT_TYPES

NOT_IN_UNIVERSE = '0000'
SPECIALS = {'industry': '9890', 'occupation': '9840'}
FIRST_YEAR = 2025
ONE_MONTH, TWO_MONTH = 'one_month', 'two_month'
# September 2025 and November 2025 are consecutive delivered months: October 2025 is absent.
GAP_FROM = 2025 * 12 + 8
GAP_TO = 2025 * 12 + 10
LINK_COLUMNS = (
    'CPSIDV', 'CPSID', 'source_row_a', 'source_row_b', 'month_a', 'month_b', 'link_type',
    'mish_a', 'mish_b', 'empstat_a', 'empstat_b', 'ind_a', 'ind_b', 'occ_a', 'occ_b',
    'qempstat_a', 'qempstat_b', 'qind_a', 'qind_b', 'qocc_a', 'qocc_b', 'empsame_b',
    'actsame_b', 'cpsidp_a')
COUNT_COLUMNS = ('month_a', 'month_b', 'link_type', 'cpsidv', 'cpsidp', 'other_gap_matches')
VALUE_CLASSES = ('mapped', 'not_in_universe', 'special')
NO_EQUIVALENT = ('no_naics_equivalent', 'no_soc_equivalent')
EARLIER_FIELDS = ('CPSID', 'CPSIDP', 'source_row', 'month_index', 'MISH', 'EMPSTAT', 'IND',
                  'OCC', 'QEMPSTAT', 'QIND', 'QOCC')
LATER_FIELDS = ('source_row', 'month_index', 'MISH', 'EMPSTAT', 'IND', 'OCC', 'QEMPSTAT',
                'QIND', 'QOCC', 'EMPSAME', 'ACTSAME')
PAIR_KEYS = ['month_index_a', 'month_index_b', 'link_type']


def _class_expression(field: str, dimension: str, units: pl.DataFrame) -> pl.Expr:
    '''Return the class of each delivered value: null when it is none of the allowed classes.'''
    rows = units.filter(pl.col('unit_type') == UNIT_TYPES[dimension])
    mapped = rows.filter(pl.col('status') == 'mapped')['code']
    absent = rows.filter(pl.col('status').is_in(NO_EQUIVALENT))['code']
    value = pl.col(field)
    return (pl.when(value == NOT_IN_UNIVERSE).then(pl.lit('not_in_universe'))
            .when(value == SPECIALS[dimension]).then(pl.lit('special'))
            .when(value.is_in(absent.implode())).then(pl.lit('no_equivalent'))
            .when(value.is_in(mapped.implode())).then(pl.lit('mapped'))
            .alias(f'{field}_class'))


def _refuse_unclassified(frame: pl.LazyFrame, expression: pl.Expr) -> pl.LazyFrame:
    '''Run the class check at collection, on every row, whatever columns are read later.'''
    def check(rows: pl.DataFrame) -> pl.DataFrame:
        found = rows.select(expression).to_series()
        if found.is_null().any():
            raise ValueError('a delivered code is not on the list, not 0000 and not a special')
        if (found == 'no_equivalent').any():
            raise ValueError('a delivered code is a list row with no NAICS or SOC equivalent')
        return rows
    return frame.map_batches(check)


def classify_codes(frame: pl.LazyFrame, field: str, dimension: str,
                   units: pl.DataFrame) -> pl.LazyFrame:
    '''Add `<field>_class`: `mapped`, `not_in_universe` or `special`.

    A value in none of these classes fails at collection, and so does a delivered code whose
    registry status is `no_naics_equivalent` or `no_soc_equivalent`. A null fails too.
    '''
    expression = _class_expression(field, dimension, units)
    return _refuse_unclassified(frame, expression).with_columns(expression)


def count_value_classes(frame: pl.LazyFrame, file: str, fields: dict[str, str],
                        units: pl.DataFrame) -> dict:
    '''Count each field's classes, and its specials by `YEAR`, keyed `<file>/<field>`.

    `fields` maps a field to its dimension. A failing value fails here as in `classify_codes`.
    '''
    counts = {}
    for field, dimension in fields.items():
        name = f'{field}_class'
        found = (classify_codes(frame, field, dimension, units).group_by(name, 'YEAR').len()
                 .collect())
        by_class = dict.fromkeys(VALUE_CLASSES, 0)
        by_year: dict[str, int] = {}
        for value_class, year, number in found.iter_rows():
            by_class[value_class] += number
            if value_class == 'special':
                by_year[str(year)] = number
        counts[f'{file}/{field}'] = {**by_class, 'special_by_year': dict(sorted(by_year.items()))}
    return counts


def monthly_panel(monthly: pl.LazyFrame) -> pl.LazyFrame:
    '''Add `source_row` (UInt64) and `month_index` (`YEAR * 12 + MONTH - 1`), after checks.

    The checks collect aggregates only. They refuse a sample before 2025-01, an `ASECFLAG` of 1,
    a null in `YEAR`, `MONTH`, `CPSIDV`, `MISH` or `EMPSTAT`, a `MISH` outside 1 to 8 and a
    `CPSIDV` that repeats inside one month.
    '''
    panel = monthly.with_columns(
        pl.int_range(pl.len(), dtype=pl.UInt64).alias('source_row'),
        (pl.col('YEAR').cast(pl.Int64) * 12 + pl.col('MONTH') - 1).alias('month_index'))
    mish = pl.col('MISH')
    found = panel.select(
        (pl.col('YEAR') < FIRST_YEAR).sum().alias('early'),
        (pl.col('ASECFLAG') == 1).sum().alias('asec'),
        pl.sum_horizontal(
            pl.col(name).is_null().sum()
            for name in ('YEAR', 'MONTH', 'CPSIDV', 'MISH', 'EMPSTAT')).alias('null'),
        ((mish < 1) | (mish > 8)).sum().alias('mish'),
        pl.struct('month_index', 'CPSIDV').is_duplicated().sum().alias('repeat')
    ).collect().row(0, named=True)
    messages = {
        'early': 'a monthly sample starts before 2025-01',
        'asec': 'a monthly row has ASECFLAG 1',
        'null': 'a monthly row has a null YEAR, MONTH, CPSIDV, MISH or EMPSTAT',
        'mish': 'a monthly row has a MISH outside 1 to 8',
        'repeat': 'a CPSIDV repeats inside one month'}
    for name, message in messages.items():
        if found[name]:
            raise ValueError(message)
    return panel


def _pairs(panel: pl.LazyFrame, key: str) -> pl.LazyFrame:
    '''Return every pair of rows with one `key` in a candidate month pair, before the MISH rule.

    The candidate month pairs are adjacent calendar months (`one_month`) and September 2025 to
    November 2025 (`two_month`). Side `a` is the earlier month.
    '''
    earlier = panel.select(key, *(pl.col(name).alias(f'{name.lower()}_a')
                                  for name in EARLIER_FIELDS if name != key))
    later = panel.select(key, *(pl.col(name).alias(f'{name.lower()}_b')
                                for name in LATER_FIELDS if name != key))
    adjacent = (
        earlier.with_columns(pl.col('month_index_a').alias('join_month'))
        .join(later.with_columns((pl.col('month_index_b') - 1).alias('join_month')),
              on=[key, 'join_month'])
        .drop('join_month').with_columns(pl.lit(ONE_MONTH).alias('link_type')))
    gap = (
        earlier.filter(pl.col('month_index_a') == GAP_FROM)
        .join(later.filter(pl.col('month_index_b') == GAP_TO), on=key)
        .with_columns(pl.lit(TWO_MONTH).alias('link_type')))
    return pl.concat([adjacent, gap.select(adjacent.collect_schema().names())])


def _follows_rule() -> pl.Expr:
    '''Return whether a pair's `MISH` values make a link, for its `link_type`.'''
    rise = pl.col('mish_b') - pl.col('mish_a')
    return (pl.when(pl.col('link_type') == ONE_MONTH)
            .then((rise == 1) & ~pl.col('mish_a').is_in([4, 8]))
            .otherwise(rise == 2))


def _month_label(index: str) -> pl.Expr:
    '''Format a month index as `YYYY-MM`.'''
    month = (pl.col(index) % 12 + 1).cast(pl.String).str.zfill(2)
    return pl.format('{}-{}', pl.col(index) // 12, month)


def monthly_links(panel: pl.LazyFrame) -> pl.LazyFrame:
    '''Return the person-month links of a `monthly_panel`, with `LINK_COLUMNS`.

    A one-month link has one `CPSIDV` in calendar months `m` and `m + 1`, `MISH` rising by one
    and the earlier `MISH` not 4 or 8. The two-month link is September 2025 to November 2025
    with `MISH` rising by two. No other pair links. Rows sort by source row.
    '''
    pairs = _pairs(panel, 'CPSIDV').filter(_follows_rule())
    return pairs.select(
        'CPSIDV', pl.col('cpsid_a').alias('CPSID'), 'source_row_a', 'source_row_b',
        _month_label('month_index_a').alias('month_a'),
        _month_label('month_index_b').alias('month_b'), 'link_type',
        *(name for name in LINK_COLUMNS[7:-1]), 'cpsidp_a').sort('source_row_a', 'source_row_b')


def _candidate_months(panel: pl.LazyFrame) -> pl.LazyFrame:
    '''List the candidate month pairs whose two months are both in the panel.'''
    months = set(panel.select(pl.col('month_index').unique()).collect()['month_index'])
    found = [(month, month + 1, ONE_MONTH) for month in sorted(months) if month + 1 in months]
    if {GAP_FROM, GAP_TO} <= months:
        found.append((GAP_FROM, GAP_TO, TWO_MONTH))
    return pl.LazyFrame(found, schema={'month_index_a': pl.Int64, 'month_index_b': pl.Int64,
                                       'link_type': pl.String}, orient='row')


def link_counts(panel: pl.LazyFrame) -> pl.DataFrame:
    '''Count links by month pair on `CPSIDV` and on `CPSIDP`, and the failed `CPSIDV` matches.

    `other_gap_matches` counts `CPSIDV` matches in the same month pair that fail the `MISH`
    rule. The `CPSIDP` count applies the same rules to `CPSIDP`.
    '''
    linked = _follows_rule()
    by_person = _pairs(panel, 'CPSIDV').group_by(PAIR_KEYS).agg(
        linked.sum().alias('cpsidv'), (~linked).sum().alias('other_gap_matches'))
    by_slot = _pairs(panel, 'CPSIDP').group_by(PAIR_KEYS).agg(linked.sum().alias('cpsidp'))
    counts = (_candidate_months(panel).join(by_person, on=PAIR_KEYS, how='left')
              .join(by_slot, on=PAIR_KEYS, how='left')
              .with_columns(_month_label('month_index_a').alias('month_a'),
                            _month_label('month_index_b').alias('month_b'),
                            pl.col('cpsidv', 'cpsidp', 'other_gap_matches')
                            .fill_null(0).cast(pl.Int64))
              .select(COUNT_COLUMNS).sort('month_a', 'month_b', 'link_type'))
    return counts.collect()
