'''Link ITA establishment records across filing years, with one status per base record.

Within each filing year, source rows equal on all 24 Stage 2 summary columns, with nulls
equal, form one distinct record. This collapse serves linkage only. A distinct record's
`base_row` is the first of its sorted `source_rows`. For each year pair s -> t in
`YEAR_PAIRS`, every distinct record of s gets the first status in `STATUSES` order that
applies:

- `missing_id`: the base ID is null.
- `ambiguous_id`: the base ID is not `id_unique`, so another distinct record of s has it.
- `conflict`: the base has both confirmed kinds, or its confirmed successor is also the
  confirmed successor of another base record.
- `confirmed_same_id`: the base is `id_unique`, its ID is `id_unique` in t, both `ein_key`
  values are known and equal, neither EIN is padded, and the base `address_key` is known and
  equals the later one.
- `confirmed_changed_id`: base and later records are both `tuple_eligible`, their
  `(ein_key, name_key, address_key)` tuples are equal and their IDs differ.
- `weaker_same_id`: the base ID appears in t, unconfirmed. Its reasons say why.
- `no_candidate`: none of the above.

The confirmed kinds before conflict handling reproduce the adopted V2 counts. The report
shows that the statuses partition the base records and that conflicts account for the
difference. A null padded flag counts as padded.
'''

from dataclasses import dataclass

import polars as pl

from embedding_data.ita_establishment_expected import V2_COLUMNS, YEAR_PAIRS
from embedding_data.ita_establishment_records import SOURCE_COLUMNS
from embedding_data.target_inputs import CANONICAL_SCHEMA

LINKS_VERSION = 'ita-establishment-links-v1'
STATUSES = (
    'missing_id',
    'ambiguous_id',
    'conflict',
    'confirmed_same_id',
    'confirmed_changed_id',
    'weaker_same_id',
    'no_candidate',
)
REASONS = (
    'reason_later_id_ambiguous',
    'reason_ein_unknown',
    'reason_ein_reconstructed',
    'reason_ein_conflict',
    'reason_address_incomplete',
    'reason_address_conflict',
)
LINK_SCHEMA = {
    'base_year': pl.Int64,
    'later_year': pl.Int64,
    'base_row': pl.UInt64,
    'base_rows': pl.List(pl.UInt64),
    'later_row': pl.UInt64,
    'base_establishment_id': pl.Int64,
    'later_establishment_id': pl.Int64,
    'status': pl.String,
    **{reason: pl.Boolean for reason in REASONS},
    'flag_id_reappears_elsewhere': pl.Boolean,
}
DERIVED_KEYS = ('ein_key', 'flag_ein_padded', 'name_key', 'address_key')
KEY_COLUMNS = ('establishment_id', 'ein', *DERIVED_KEYS)
RECORD_SCHEMA = {
    'source_row': pl.UInt64,
    **{column: CANONICAL_SCHEMA[column] for column in SOURCE_COLUMNS},
    'ein_key': pl.String,
    'flag_ein_padded': pl.Boolean,
    'name_key': pl.String,
    'address_key': pl.String,
}
TUPLE = ('ein_key', 'name_key', 'address_key')
YEAR = 'year_filing_for'
PAIR_KEYS = ('base_year', 'later_year')
LINK_KEYS = (*PAIR_KEYS, 'base_row')
CONFIRMED = ('confirmed_same_id', 'confirmed_changed_id')
SAME_ID = ('confirmed_same_id', 'weaker_same_id')


@dataclass(frozen=True)
class Links:
    '''The link table, the pre-conflict V2 counts by year pair and the report.'''

    links: pl.LazyFrame
    v2: pl.DataFrame
    report: dict


def _require_records(records: pl.LazyFrame) -> None:
    schema = records.collect_schema()
    if any(schema.get(column) != dtype for column, dtype in RECORD_SCHEMA.items()):
        raise ValueError('links need keyed records')


def _distinct(records: pl.LazyFrame) -> pl.LazyFrame:
    '''The distinct records of every year, `year_filing_for` first, sorted by `base_row`.'''
    eligible = (
        pl.col('id_unique')
        .and_(pl.col('ein_key').is_not_null())
        .and_(pl.col('flag_ein_padded').not_())
        .and_(pl.col('address_key').is_not_null())
        .and_(pl.col('name_key').ne(''))
        .and_(pl.len().over(YEAR, *TUPLE).eq(1))
    )
    return (
        records.select('source_row', *SOURCE_COLUMNS, *DERIVED_KEYS)
        .group_by(list(SOURCE_COLUMNS))
        .agg(pl.col('source_row').sort().alias('source_rows'),
             *(pl.col(column).first() for column in DERIVED_KEYS))
        .with_columns(
            base_row=pl.col('source_rows').list.first(),
            flag_ein_padded=pl.col('flag_ein_padded').fill_null(True),
            id_unique=pl.col('establishment_id').is_not_null()
            .and_(pl.len().over(YEAR, 'establishment_id').eq(1)),
        )
        .with_columns(tuple_eligible=eligible.fill_null(False))
        .select(YEAR, 'base_row', 'source_rows', *KEY_COLUMNS, 'id_unique', 'tuple_eligible')
        .sort('base_row')
    )


def distinct_records(records: pl.LazyFrame, year: int) -> pl.LazyFrame:
    '''One row per distinct record of the year, sorted by `base_row`.

    `records` is `ita_establishment_records.keyed_records` output. The columns are
    `base_row`, `source_rows`, `KEY_COLUMNS`, `id_unique` and `tuple_eligible`.
    `id_unique` holds when the ID is non-null and no other distinct record of the year has
    it. `tuple_eligible` holds when the record is `id_unique`, its EIN is usable and not
    padded, its address is complete, its name key is not empty, and no other distinct
    record of the year, of any ID or EIN padding, has its tuple.
    '''
    _require_records(records)
    return _distinct(records.filter(pl.col(YEAR).eq(year))).drop(YEAR)


def _count(condition: pl.Expr) -> pl.Expr:
    return condition.fill_null(False).sum()


def _link_pair(base: pl.DataFrame, later: pl.DataFrame, pair: tuple[int, int]) -> tuple:
    '''The link rows and the report of one year pair, from its distinct records.'''
    base_id = pl.col('establishment_id')
    counts = later.filter(base_id.is_not_null()).group_by('establishment_id').agg(
        _n_later=pl.len())
    unique_later = later.filter(pl.col('id_unique')).select(
        'establishment_id',
        _same_row=pl.col('base_row'),
        _same_id=base_id,
        _ein=pl.col('ein'),
        _ein_key=pl.col('ein_key'),
        _padded=pl.col('flag_ein_padded'),
        _address=pl.col('address_key'),
    )
    eligible = pl.col('tuple_eligible')
    matches = base.filter(eligible).select('base_row', 'establishment_id', *TUPLE).join(
        later.filter(eligible).select(*TUPLE, _changed_row=pl.col('base_row'),
                                      _changed_id=base_id),
        on=list(TUPLE),
        how='inner',
    )
    changed = matches.filter(base_id.ne(pl.col('_changed_id'))).select(
        'base_row', '_changed_row', '_changed_id')

    later_unique = pl.col('_same_row').is_not_null()
    reappeared = pl.col('id_unique').and_(later_unique)
    known = pl.col('ein_key').is_not_null().and_(pl.col('_ein_key').is_not_null())
    same_ein = known.and_(pl.col('ein_key').eq(pl.col('_ein_key')))
    base_address = pl.col('address_key').is_not_null()
    same_address = base_address.and_(pl.col('address_key').eq(pl.col('_address')))
    unpadded = pl.col('flag_ein_padded').not_().and_(pl.col('_padded').not_())
    frame = (
        base.join(counts, on='establishment_id', how='left')
        .join(unique_later, on='establishment_id', how='left')
        .join(changed, on='base_row', how='left')
        .with_columns(
            _padded_link=reappeared.and_(same_ein).and_(same_address).fill_null(False),
            _changed=pl.col('_changed_row').is_not_null(),
        )
        .with_columns(_same=pl.col('_padded_link').and_(unpadded).fill_null(False))
    )
    edges = pl.concat([
        frame.filter(pl.col('_same')).select('base_row', _successor=pl.col('_same_row')),
        frame.filter(pl.col('_changed')).select('base_row', _successor=pl.col('_changed_row')),
    ])
    shared = edges.filter(pl.len().over('_successor').gt(1))['base_row']
    frame = frame.with_columns(
        _conflict=pl.col('_same').and_(pl.col('_changed'))
        .or_(pl.col('base_row').is_in(shared.implode()))
    ).with_columns(
        status=pl.when(base_id.is_null()).then(pl.lit('missing_id'))
        .when(pl.col('id_unique').not_()).then(pl.lit('ambiguous_id'))
        .when(pl.col('_conflict')).then(pl.lit('conflict'))
        .when(pl.col('_same')).then(pl.lit('confirmed_same_id'))
        .when(pl.col('_changed')).then(pl.lit('confirmed_changed_id'))
        .when(pl.col('_n_later').is_not_null()).then(pl.lit('weaker_same_id'))
        .otherwise(pl.lit('no_candidate'))
    )

    status = pl.col('status')
    weaker = status.eq('weaker_same_id')
    direct = weaker.and_(later_unique)
    reasons = {
        'reason_later_id_ambiguous': weaker.and_(later_unique.not_()),
        'reason_ein_unknown': direct.and_(known.not_()),
        'reason_ein_reconstructed': direct.and_(
            pl.col('flag_ein_padded').or_(pl.col('_padded'))),
        'reason_ein_conflict': direct.and_(known).and_(
            pl.col('ein_key').ne(pl.col('_ein_key'))),
        'reason_address_incomplete': direct.and_(
            base_address.not_().or_(pl.col('_address').is_null())),
        'reason_address_conflict': direct.and_(pl.col('address_key').ne(pl.col('_address'))),
    }
    links = frame.select(
        base_year=pl.lit(pair[0], pl.Int64),
        later_year=pl.lit(pair[1], pl.Int64),
        base_row=pl.col('base_row'),
        base_rows=pl.col('source_rows'),
        later_row=pl.when(status.eq('confirmed_changed_id')).then(pl.col('_changed_row'))
        .when(status.is_in(SAME_ID)).then(pl.col('_same_row')),
        base_establishment_id=base_id,
        later_establishment_id=pl.when(status.eq('confirmed_changed_id'))
        .then(pl.col('_changed_id'))
        .when(status.is_in(SAME_ID)).then(pl.col('_same_id')),
        status=status,
        **{reason: rule.fill_null(False) for reason, rule in reasons.items()},
        flag_id_reappears_elsewhere=status.eq('confirmed_changed_id')
        .and_(pl.col('_n_later').is_not_null()),
    )

    def missing_rows(frame):
        return frame.select(
            pl.col('source_rows').list.len().filter(pl.col('establishment_id').is_null()).sum()
        ).item()

    v2 = frame.select(
        n_cohort_ids=base_id.drop_nulls().n_unique(),
        n_raw_reappeared=base_id.filter(pl.col('_n_later').is_not_null()).n_unique(),
        n_unique_cohort_ids=_count(pl.col('id_unique')),
        n_reappeared=_count(reappeared),
        n_same_ein_address=_count(pl.col('_same')),
        n_same_ein_address_including_padded=_count(pl.col('_padded_link')),
        n_same_raw_ein_address=_count(
            pl.col('_padded_link').and_(pl.col('ein').eq(pl.col('_ein')))),
        n_reappeared_ein_unknown=_count(reappeared.and_(known.not_())),
        n_reappeared_ein_conflict=_count(
            reappeared.and_(known).and_(pl.col('ein_key').ne(pl.col('_ein_key')))),
        n_reappeared_address_conflict=_count(reappeared.and_(
            base_address.not_().or_(pl.col('address_key').ne(pl.col('_address'))))),
        n_unique_address_matches=pl.lit(matches.height),
        n_address_matches_different_id=_count(pl.col('_changed')),
    ).row(0, named=True)
    v2['n_base_missing_id_rows'] = missing_rows(base)
    v2['n_later_missing_id_rows'] = missing_rows(later)
    found = dict(links.group_by('status').agg(pl.len()).iter_rows())
    conflict = status.eq('conflict')
    conflicts = frame.select(
        n_conflict_with_same_link=_count(conflict.and_(pl.col('_same'))),
        n_conflict_with_changed_link=_count(conflict.and_(pl.col('_changed'))),
        n_conflict_both_links=_count(conflict.and_(pl.col('_same')).and_(pl.col('_changed'))),
    ).row(0, named=True)
    report = {
        'base_year': pair[0],
        'later_year': pair[1],
        'n_base_records': base.height,
        'v2': {column: v2[column] for column in V2_COLUMNS},
        'statuses': {name: found.get(name, 0) for name in STATUSES},
        **conflicts,
    }
    return links, report


def _check_pair_report(pair: dict) -> None:
    '''Raise unless the statuses partition the base records and conflicts explain the gaps.'''
    v2, statuses = pair['v2'], pair['statuses']
    if (
        v2['n_same_ein_address'] - statuses['confirmed_same_id']
        != pair['n_conflict_with_same_link']
        or v2['n_address_matches_different_id'] - statuses['confirmed_changed_id']
        != pair['n_conflict_with_changed_link']
        or sum(statuses.values()) != pair['n_base_records']
    ):
        raise ValueError('link report identities do not hold')


def build_links(records: pl.LazyFrame) -> Links:
    '''The links of every year pair in `YEAR_PAIRS`, the V2 counts and the report.

    `records` is `ita_establishment_records.keyed_records` output. Links are sorted by
    `base_year`, `later_year` and `base_row`. `v2` has one Int64 row per pair, in
    `YEAR_PAIRS` order, with the counts before conflict handling. A report identity that
    does not hold raises `ValueError`.
    '''
    _require_records(records)
    distinct = _distinct(records).collect()
    frames, counts, pairs = [], [], {}
    for pair in YEAR_PAIRS:
        base, later = (distinct.filter(pl.col(YEAR).eq(year)).drop(YEAR) for year in pair)
        links, report = _link_pair(base, later, pair)
        _check_pair_report(report)
        frames.append(links)
        counts.append({'base_year': pair[0], 'later_year': pair[1], **report['v2']})
        pairs[f'{pair[0]}-{pair[1]}'] = report
    v2_schema = {'base_year': pl.Int64, 'later_year': pl.Int64,
                 **dict.fromkeys(V2_COLUMNS, pl.Int64)}
    return Links(
        links=pl.concat(frames).sort(LINK_KEYS).lazy(),
        v2=pl.DataFrame(counts, schema=v2_schema),
        report={'pairs': pairs},
    )


def _reject(frame: pl.DataFrame, condition: pl.Expr, message: str) -> None:
    '''Raise `message` when `condition` holds, or is unknown, for any row.'''
    if frame.select(condition.fill_null(True).any()).item():
        raise ValueError(message)


def _by_pair(distinct: pl.DataFrame, side: int) -> pl.DataFrame:
    '''The distinct records of each pair's base (side 0) or later (side 1) year.'''
    return pl.concat([
        distinct.filter(pl.col(YEAR).eq(pair[side])).with_columns(
            base_year=pl.lit(pair[0], pl.Int64), later_year=pl.lit(pair[1], pl.Int64))
        for pair in YEAR_PAIRS
    ])


def validate_links(links: pl.LazyFrame, records: pl.LazyFrame) -> None:
    '''Check the link table against the distinct records of `records` and the link rules.'''
    _require_records(records)
    if list(links.collect_schema().items()) != list(LINK_SCHEMA.items()):
        raise ValueError('links do not have the link schema')
    table = links.collect()
    base_rows = pl.col('base_rows')
    required = [*LINK_KEYS, 'base_rows', 'status', *REASONS, 'flag_id_reappears_elsewhere']
    _reject(table, pl.any_horizontal([pl.col(column).is_null() for column in required])
            .or_(base_rows.list.eval(pl.element().is_null()).list.any()),
            'links hold a null key, status, reason or flag')
    keys = table.select(LINK_KEYS)
    if not keys.equals(keys.sort(LINK_KEYS)) or keys.is_duplicated().any():
        raise ValueError('link keys are not sorted and unique')
    adopted = pl.DataFrame(list(YEAR_PAIRS), schema=dict.fromkeys(PAIR_KEYS, pl.Int64),
                           orient='row')
    if table.select(PAIR_KEYS).join(adopted, on=list(PAIR_KEYS), how='anti').height:
        raise ValueError('link year pairs are not the adopted pairs')
    _reject(table, base_rows.list.sort().ne(base_rows)
            .or_(base_rows.list.first().ne(pl.col('base_row'))),
            'link base rows are not sorted from the base row')

    distinct = _distinct(records).collect()
    base = _by_pair(distinct, 0).sort(LINK_KEYS).select(
        *LINK_KEYS,
        base_rows=pl.col('source_rows'),
        base_establishment_id=pl.col('establishment_id'),
        _base_ein_key=pl.col('ein_key'),
        _base_padded=pl.col('flag_ein_padded'),
        _base_address=pl.col('address_key'),
    )
    observed = table.select(*LINK_KEYS, 'base_rows', 'base_establishment_id')
    if not observed.equals(base.select(observed.columns)):
        raise ValueError('link base records differ from the distinct records')
    status = pl.col('status')
    _reject(table, status.is_in(STATUSES).not_(), 'link statuses are not link statuses')
    _reject(table, pl.col('base_establishment_id').is_null().ne(status.eq('missing_id')),
            'a null base ID does not match the missing_id status')

    later = _by_pair(distinct, 1)
    successors = later.select(
        *PAIR_KEYS,
        later_row=pl.col('base_row'),
        _record_id=pl.col('establishment_id'),
        _later_ein_key=pl.col('ein_key'),
        _later_padded=pl.col('flag_ein_padded'),
        _later_address=pl.col('address_key'),
    )
    id_counts = later.filter(pl.col('establishment_id').is_not_null()).group_by(
        *PAIR_KEYS, 'establishment_id').agg(_n=pl.len()).rename(
        {'establishment_id': 'base_establishment_id'})
    joined = (
        table.join(base.drop('base_rows', 'base_establishment_id'), on=list(LINK_KEYS),
                   how='left')
        .join(successors, on=[*PAIR_KEYS, 'later_row'], how='left')
        .join(id_counts, on=[*PAIR_KEYS, 'base_establishment_id'], how='left')
    )
    row = pl.col('later_row')
    later_id = pl.col('later_establishment_id')
    base_id = pl.col('base_establishment_id')
    later_unique = pl.col('_n').eq(1).fill_null(False)
    has_row = row.is_not_null()
    _reject(
        joined,
        has_row.ne(status.is_in(CONFIRMED).or_(status.eq('weaker_same_id').and_(later_unique)))
        .or_(later_id.ne_missing(pl.col('_record_id')))
        .or_(status.is_in(SAME_ID).and_(has_row).and_(later_id.ne(base_id)))
        .or_(status.eq('confirmed_changed_id').and_(later_id.eq(base_id))),
        'link successors do not follow the successor rules',
    )
    weaker = status.eq('weaker_same_id')
    direct = weaker.and_(later_unique)
    known = pl.col('_base_ein_key').is_not_null().and_(pl.col('_later_ein_key').is_not_null())
    expected = {
        'reason_later_id_ambiguous': weaker.and_(later_unique.not_()),
        'reason_ein_unknown': direct.and_(known.not_()),
        'reason_ein_reconstructed': direct.and_(
            pl.col('_base_padded').or_(pl.col('_later_padded'))),
        'reason_ein_conflict': direct.and_(known).and_(
            pl.col('_base_ein_key').ne(pl.col('_later_ein_key'))),
        'reason_address_incomplete': direct.and_(
            pl.col('_base_address').is_null().or_(pl.col('_later_address').is_null())),
        'reason_address_conflict': direct.and_(
            pl.col('_base_address').ne(pl.col('_later_address'))),
    }
    _reject(joined, pl.any_horizontal(
        [pl.col(reason).ne(rule.fill_null(False)) for reason, rule in expected.items()]),
        'link reasons do not follow the weaker-evidence rules')
    _reject(joined, pl.col('flag_id_reappears_elsewhere').ne(
        status.eq('confirmed_changed_id').and_(pl.col('_n').is_not_null())),
        'link flags do not follow the reappearance rule')
