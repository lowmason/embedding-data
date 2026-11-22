'''Stage 14 report, firm and pair statuses, and the counts the preflight and the report use.

Each subaward row is one report and gets one report status. Each distinct UEI on a usable
report gets one firm status from the SAM.gov extract rows that share its stripped UEI. Each
distinct (prime, subcontractor) pair of usable reports gets one pair status. Every chain is
checked in its spec order, and the first status that applies wins. Every strip uses the
ASCII set `WHITESPACE`. The work stays in lazy Polars until a small table or a count is
collected. The extract lines that the reader skips for their field count are counted with
the report firms whose UEIs they hold, and change no status. A malformed primary code on a
firm whose codes the build reads raises a `ValueError`, and so does each failed pair-table
check and a frame of skipped lines in another schema. Every message is fixed.
'''

from datetime import date

import polars as pl

from embedding_data.usaspending_raw import WINDOW
from embedding_data.vendor_link_codes import NODE_PREFIX
from embedding_data.vendor_link_layouts import (
    EXTRACT_OPTIONAL,
    WHITESPACE,
    ExtractLayout,
    SubawardLayout,
)
from embedding_data.vendor_link_readers import SUBAWARD_SCHEMA, UNREADABLE_SCHEMA

CONTRACT = 'vendor-link-pairs-v1'
UEI_PATTERN = r'^[A-Z0-9]{12}$'
CODE_PATTERN = r'^[0-9]{6}$'
AMOUNT_PATTERN = r'^-?[0-9]{1,36}(\.[0-9]{1,2})?$'
AMOUNT_TYPE = pl.Decimal(38, 2)
DNB_CUTOFF = date(2022, 4, 4)
SUBCONTRACT = 'sub-contract'
REPORT_STATUSES = ('uei_unusable', 'action_date_invalid', 'outside_window', 'usable')
FIRM_STATUSES = ('not_in_sam', 'dnb_era_record', 'naics_missing', 'naics_conflict',
                 'naics_not_2022', 'eligible')
PAIR_STATUSES = ('self_link', 'intra_group', 'prime_ineligible', 'sub_ineligible', 'eligible')
FIRM_SCHEMA = {'uei': pl.String, 'is_prime': pl.Boolean, 'is_sub': pl.Boolean,
               'firm_status': pl.String, 'node_id': pl.String, 'n_extract_rows': pl.UInt64,
               'flag_mixed_blank': pl.Boolean, 'flag_last_update_invalid': pl.Boolean,
               'flag_code_not_in_string': pl.Boolean}
PAIR_SCHEMA = {'prime_uei': pl.String, 'sub_uei': pl.String, 'n_reports': pl.UInt64,
               'n_fy2024': pl.UInt64, 'n_fy2025': pl.UInt64, 'n_fy2026': pl.UInt64,
               'prime_status': pl.String, 'sub_status': pl.String,
               'prime_node_id': pl.String, 'sub_node_id': pl.String,
               'flag_intra_group': pl.Boolean, 'pair_status': pl.String,
               'amount_sum': AMOUNT_TYPE}
_REPORT_COLUMNS = ('prime', 'sub', 'prime_parent', 'sub_parent', 'action', 'fiscal_year',
                   'amount_value', 'report_status')
_CODED = ('naics_conflict', 'naics_not_2022', 'eligible')
_ROLES = (('prime', 'prime'), ('subcontractor', 'sub'))


def _strip(column: str) -> pl.Expr:
    return pl.col(column).str.strip_chars(WHITESPACE)


def _matches(text: pl.Expr, pattern: str) -> pl.Expr:
    return text.str.contains(pattern).fill_null(False)


def _date(text: pl.Expr, date_format: str) -> pl.Expr:
    '''The date that `text` spells in `date_format`, null unless it formats back to `text`.'''
    parsed = text.str.to_date(date_format, strict=False)
    return pl.when(parsed.dt.to_string(date_format) == text).then(parsed)


def _node(code: pl.Expr) -> pl.Expr:
    return pl.lit(NODE_PREFIX) + code


def _count(predicate: pl.Expr) -> pl.Expr:
    return predicate.fill_null(False).sum()


# ---- subaward type

def subaward_types(rows: pl.LazyFrame) -> dict[str, int]:
    '''The count of each delivered subaward type value, in value order.'''
    counts = rows.group_by('subaward_type').agg(pl.len()).sort('subaward_type').collect()
    return {value: int(count) for value, count in counts.iter_rows()}


def check_subaward_types(rows: pl.LazyFrame) -> None:
    '''Refuse any row whose delivered subaward type is not `sub-contract`.'''
    other = rows.select(_count(pl.col('subaward_type').ne_missing(SUBCONTRACT))).collect()
    if other.item() > 0:
        raise ValueError('subaward type is not sub-contract')


# ---- reports

def _action(layouts: dict[int, SubawardLayout]) -> pl.Expr:
    '''The action date, read with the date format of the row's own file year.'''
    text = _strip('action_date')
    return pl.coalesce([pl.when(pl.col('file_year') == year)
                        .then(_date(text, layout.date_format))
                        for year, layout in layouts.items()])


def _parent(field: str, layouts: dict[int, SubawardLayout]) -> pl.Expr:
    '''A stripped parent UEI, null unless the year maps the field and it is usable.'''
    mapped = [year for year, layout in layouts.items() if layout.columns[field] is not None]
    text = _strip(field)
    return pl.when(pl.col('file_year').is_in(mapped) & _matches(text, UEI_PATTERN)).then(text)


def _amount() -> pl.Expr:
    text = _strip('amount')
    return pl.when(_matches(text, AMOUNT_PATTERN)).then(text).cast(AMOUNT_TYPE)


def _report_status() -> pl.Expr:
    usable_ueis = _matches(pl.col('prime'), UEI_PATTERN) & _matches(pl.col('sub'), UEI_PATTERN)
    return (pl.when(~usable_ueis).then(pl.lit('uei_unusable'))
            .when(pl.col('action').is_null()).then(pl.lit('action_date_invalid'))
            .when(~pl.col('fiscal_year').is_in(WINDOW)).then(pl.lit('outside_window'))
            .otherwise(pl.lit('usable')))


def reports(rows: pl.LazyFrame, layouts: dict[int, SubawardLayout]) -> pl.LazyFrame:
    '''Every row in `SUBAWARD_SCHEMA` order, with its stripped UEIs, usable parent UEIs,
    action date, fiscal year, parsed amount and report status.'''
    action = pl.col('action')
    return (rows
            .with_columns(prime=_strip('prime_uei'), sub=_strip('sub_uei'),
                          prime_parent=_parent('prime_parent_uei', layouts),
                          sub_parent=_parent('sub_parent_uei', layouts),
                          action=_action(layouts), amount_value=_amount())
            .with_columns(fiscal_year=action.dt.year().cast(pl.Int64)
                          + (action.dt.month() >= 10).cast(pl.Int64))
            .with_columns(report_status=_report_status())
            .select(*SUBAWARD_SCHEMA, *_REPORT_COLUMNS))


# ---- firms

def _roles(usable: pl.LazyFrame) -> pl.LazyFrame:
    '''Each distinct UEI on a usable report, with whether it is a prime and a subcontractor.'''
    primes = usable.select(uei='prime', is_prime=pl.lit(True), is_sub=pl.lit(False))
    subs = usable.select(uei='sub', is_prime=pl.lit(False), is_sub=pl.lit(True))
    return pl.concat([primes, subs]).group_by('uei').agg(pl.col('is_prime').any(),
                                                         pl.col('is_sub').any())


def _extract_rows(extract: pl.DataFrame, layout: ExtractLayout) -> pl.LazyFrame:
    '''Each extract row with its stripped UEI and code, the code's shape, its last update
    date and whether the row is a D&B-era record.'''
    code = _strip('primary_naics')
    update = _date(_strip('last_update_date'), layout.date_format)
    if layout.positions['evs_source'] is None:
        evs_dnb = pl.lit(False)
    else:
        evs_dnb = _strip('evs_source').is_in(sorted(layout.evs_dnb))
    return extract.lazy().with_columns(
        key=_strip('uei'), code=code, blank=code == '',
        malformed=(code != '') & ~_matches(code, CODE_PATTERN), update=update,
        dnb=update.is_null() | (update < DNB_CUTOFF) | evs_dnb)


def _read_ueis(usable: pl.LazyFrame, rows: pl.LazyFrame) -> pl.LazyFrame:
    '''The UEIs on usable reports that are in the extract and are not D&B-era records.'''
    dnb = rows.group_by('key').agg(pl.col('dnb').any())
    return (_roles(usable).join(dnb, left_on='uei', right_on='key')
            .filter(~pl.col('dnb')).select(key='uei', read=pl.lit(True)))


def _malformed(usable: pl.LazyFrame, rows: pl.LazyFrame) -> dict[str, int]:
    read = pl.col('read').fill_null(False)
    counts = (rows.join(_read_ueis(usable, rows), on='key', how='left')
              .select(read_rows=_count(pl.col('malformed') & read),
                      unread_rows=_count(pl.col('malformed') & ~read))
              .collect())
    return {name: int(value) for name, value in counts.row(0, named=True).items()}


def count_malformed(usable: pl.LazyFrame, extract: pl.DataFrame,
                    layout: ExtractLayout) -> dict[str, int]:
    '''Malformed primary codes on rows of UEIs that reach firm steps 3-5 (`read_rows`) and on
    every other extract row (`unread_rows`).'''
    return _malformed(usable, _extract_rows(extract, layout))


def _firm_status(node_ids: frozenset[str]) -> pl.Expr:
    return (pl.when(pl.col('n_extract_rows') == 0).then(pl.lit('not_in_sam'))
            .when(pl.col('dnb')).then(pl.lit('dnb_era_record'))
            .when(pl.col('n_codes') == 0).then(pl.lit('naics_missing'))
            .when(pl.col('n_codes') > 1).then(pl.lit('naics_conflict'))
            .when(~_node(pl.col('code')).is_in(sorted(node_ids))).then(pl.lit('naics_not_2022'))
            .otherwise(pl.lit('eligible')))


def firms(usable: pl.LazyFrame, extract: pl.DataFrame, layout: ExtractLayout,
          node_ids: frozenset[str]) -> pl.DataFrame:
    '''One row per distinct UEI on usable reports, sorted by `uei`, in `FIRM_SCHEMA`.

    A malformed primary code on any row of a firm that reaches steps 3-5 raises before any
    status is assigned.
    '''
    rows = _extract_rows(extract, layout)
    if _malformed(usable, rows)['read_rows'] > 0:
        raise ValueError('malformed primary NAICS code')
    summary = rows.group_by('key').agg(
        n_extract_rows=pl.len(), dnb=pl.col('dnb').any(),
        codes=pl.col('code').filter(~pl.col('blank')).unique(),
        flag_mixed_blank=pl.col('blank').any() & (~pl.col('blank')).any(),
        flag_last_update_invalid=pl.col('update').is_null().any())
    runs = (rows.select(uei='key', code=pl.col('naics_code_string').str.extract_all('[0-9]+'))
            .explode('code').filter(pl.col('code').str.len_chars() == 6).unique()
            .with_columns(in_string=pl.lit(True)))
    table = (_roles(usable).join(summary, left_on='uei', right_on='key', how='left')
             .with_columns(pl.col('n_extract_rows').fill_null(0),
                           pl.col('flag_mixed_blank', 'flag_last_update_invalid')
                           .fill_null(False),
                           n_codes=pl.col('codes').list.len(),
                           code=pl.col('codes').list.first())
             .with_columns(firm_status=_firm_status(node_ids))
             .join(runs, on=['uei', 'code'], how='left')
             .with_columns(
                 node_id=pl.when(pl.col('firm_status') == 'eligible').then(_node(pl.col('code'))),
                 flag_code_not_in_string=pl.col('firm_status').is_in(['naics_not_2022',
                                                                      'eligible'])
                 & pl.col('in_string').is_null()))
    return (table.select(pl.col(name).cast(dtype) for name, dtype in FIRM_SCHEMA.items())
            .sort('uei').collect())


# ---- pairs

def _intra_group() -> pl.Expr:
    '''Whether a report shows a corporate group. A null parent never matches.'''
    prime_parent, sub_parent = pl.col('prime_parent'), pl.col('sub_parent')
    return ((sub_parent == pl.col('prime')) | (prime_parent == pl.col('sub'))
            | (prime_parent == sub_parent)).fill_null(False)


def _pair_status() -> pl.Expr:
    return (pl.when(pl.col('prime_uei') == pl.col('sub_uei')).then(pl.lit('self_link'))
            .when(pl.col('flag_intra_group')).then(pl.lit('intra_group'))
            .when(pl.col('prime_status') != 'eligible').then(pl.lit('prime_ineligible'))
            .when(pl.col('sub_status') != 'eligible').then(pl.lit('sub_ineligible'))
            .otherwise(pl.lit('eligible')))


def pairs(usable: pl.LazyFrame, firm_table: pl.DataFrame) -> pl.DataFrame:
    '''One row per distinct (prime, subcontractor) pair of usable reports, sorted by
    `prime_uei` and `sub_uei`, in `PAIR_SCHEMA`.'''
    years = {f'n_fy{year}': _count(pl.col('fiscal_year') == year) for year in WINDOW}
    grouped = usable.group_by(prime_uei='prime', sub_uei='sub').agg(
        n_reports=pl.len(), **years, flag_intra_group=_intra_group().any(),
        amount_sum=pl.col('amount_value').sum())
    firm = firm_table.lazy().select('uei', 'firm_status', 'node_id')
    table = (grouped
             .join(firm.rename({'firm_status': 'prime_status', 'node_id': 'prime_node_id'}),
                   left_on='prime_uei', right_on='uei', how='left')
             .join(firm.rename({'firm_status': 'sub_status', 'node_id': 'sub_node_id'}),
                   left_on='sub_uei', right_on='uei', how='left')
             .with_columns(pair_status=_pair_status()))
    return (table.select(pl.col(name).cast(dtype) for name, dtype in PAIR_SCHEMA.items())
            .sort('prime_uei', 'sub_uei').collect())


def _all(predicate: pl.Series) -> bool:
    return bool(predicate.fill_null(False).all())


def validate_pairs(table: pl.DataFrame, usable_reports: int) -> None:
    '''Refuse a pair table that breaks its schema, its key, its report counts or the rules
    that join its statuses and node IDs.'''
    if list(table.schema.items()) != list(PAIR_SCHEMA.items()):
        raise ValueError('pair table schema differs')
    keys = table.select('prime_uei', 'sub_uei')
    if keys.is_duplicated().any() or not keys.equals(keys.sort('prime_uei', 'sub_uei')):
        raise ValueError('pair keys are not unique and sorted')
    if table['n_reports'].sum() != usable_reports:
        raise ValueError('pair reports differ from the usable reports')
    years = sum(table[f'n_fy{year}'] for year in WINDOW)
    if not _all(table['n_reports'] == years):
        raise ValueError('pair fiscal-year counts differ from its reports')
    known = (table['pair_status'].is_in(PAIR_STATUSES).fill_null(False)
             & table['prime_status'].is_in(FIRM_STATUSES).fill_null(False)
             & table['sub_status'].is_in(FIRM_STATUSES).fill_null(False))
    if not _all(known):
        raise ValueError('pair table holds an unknown status')
    if not _all(table.select(_pair_status().eq_missing(pl.col('pair_status'))).to_series()):
        raise ValueError('pair status differs from its rule')
    for role in ('prime', 'sub'):
        eligible = table[f'{role}_status'] == 'eligible'
        if not _all(table[f'{role}_node_id'].is_not_null() == eligible):
            raise ValueError('pair node IDs differ from the firm statuses')


# ---- report counts

def _tally(frame: pl.LazyFrame | pl.DataFrame, column: str,
           keys: tuple[str, ...] | None = None) -> dict[str, int]:
    '''The count of each value of `column`: of each of `keys`, or of each value present.'''
    counts = frame.lazy().group_by(column).agg(pl.len()).sort(column).collect()
    found = {value: int(count) for value, count in counts.iter_rows()}
    return found if keys is None else {key: found.get(key, 0) for key in keys}


def _share(part: int, whole: int) -> float | None:
    return None if whole == 0 else part / whole


def _section(frame: pl.LazyFrame, duplicate_rows: int, report_ids: bool,
             naics: bool) -> dict:
    '''The counts of one file year's rows, or of all rows.'''
    blank = {side: pl.col(side) == '' for side in ('prime', 'sub')}
    malformed = {side: ~blank[side] & ~_matches(pl.col(side), UEI_PATTERN)
                 for side in ('prime', 'sub')}
    report_id = _strip('report_id')
    sub_naics, prime_naics = _strip('subaward_naics'), _strip('prime_naics')
    both = (sub_naics != '') & (prime_naics != '')
    stats = frame.select(
        rows=pl.len(),
        outside_file_year=_count(pl.col('fiscal_year') != pl.col('file_year')),
        amount_unparseable=_count((pl.col('report_status') == 'usable')
                                  & pl.col('amount_value').is_null()),
        blank_prime=_count(blank['prime']), blank_sub=_count(blank['sub']),
        malformed_prime=_count(malformed['prime']), malformed_sub=_count(malformed['sub']),
        report_ids=report_id.filter(report_id != '').n_unique(),
        naics_both=_count(both), naics_equal=_count(both & (sub_naics == prime_naics)),
    ).collect().row(0, named=True)
    months = frame.filter(pl.col('action').is_not_null()).select(
        month=pl.col('action').dt.to_string('%Y-%m'))
    return {
        'rows': int(stats['rows']),
        'by_status': _tally(frame, 'report_status', REPORT_STATUSES),
        'duplicate_rows': duplicate_rows,
        'outside_file_year': int(stats['outside_file_year']),
        'amount_unparseable': int(stats['amount_unparseable']),
        'blank_uei': {'prime': int(stats['blank_prime']), 'sub': int(stats['blank_sub'])},
        'malformed_uei': {'prime': int(stats['malformed_prime']),
                          'sub': int(stats['malformed_sub'])},
        'by_month': _tally(months, 'month'),
        'distinct_report_ids': int(stats['report_ids']) if report_ids else None,
        'subaward_naics_equal_prime': ({'both': int(stats['naics_both']),
                                        'equal': int(stats['naics_equal'])} if naics else None),
    }


def _duplicates(reported: pl.LazyFrame) -> dict[int, int]:
    '''Duplicate rows by file year: each digest's first copy is in its earliest file year,
    and every other copy is a duplicate in its own file year.'''
    rows = dict(reported.group_by('file_year').agg(pl.len()).collect().iter_rows())
    firsts = (reported.group_by('row_digest').agg(year=pl.col('file_year').min())
              .group_by('year').agg(pl.len()).collect())
    distinct = dict(firsts.iter_rows())
    return {year: int(rows.get(year, 0) - distinct.get(year, 0)) for year in WINDOW}


def _report_sections(reported: pl.LazyFrame, layouts: dict[int, SubawardLayout]) -> dict:
    duplicates = _duplicates(reported)
    report_ids = {year: layouts[year].columns['report_id'] is not None for year in WINDOW}
    naics = {year: all(layouts[year].columns[field] is not None
                       for field in ('subaward_naics', 'prime_naics')) for year in WINDOW}
    by_file_year = {
        str(year): _section(reported.filter(pl.col('file_year') == year), duplicates[year],
                            report_ids[year], naics[year])
        for year in WINDOW}
    total = _section(reported, sum(duplicates.values()), all(report_ids.values()),
                     all(naics.values()))
    return {'by_file_year': by_file_year, 'total': total}


def _firm_counts(firm_table: pl.DataFrame) -> dict:
    return {
        'prime': _tally(firm_table.filter(pl.col('is_prime')), 'firm_status', FIRM_STATUSES),
        'subcontractor': _tally(firm_table.filter(pl.col('is_sub')), 'firm_status',
                                FIRM_STATUSES),
        'all': _tally(firm_table, 'firm_status', FIRM_STATUSES),
        'mixed_blank': int(firm_table['flag_mixed_blank'].sum()),
        'last_update_invalid': int(firm_table['flag_last_update_invalid'].sum()),
        'code_not_in_string': int(firm_table['flag_code_not_in_string'].sum()),
    }


def _coverage(usable: pl.LazyFrame, firm_table: pl.DataFrame) -> dict:
    '''For each role, the distinct UEIs on `usable` and those whose firm is eligible.'''
    statuses = firm_table.lazy().select('uei', 'firm_status')
    coverage = {}
    for role, column in _ROLES:
        counts = (usable.select(uei=column).unique()
                  .join(statuses, on='uei', how='left')
                  .select(eligible=_count(pl.col('firm_status') == 'eligible'), total=pl.len())
                  .collect().row(0, named=True))
        eligible, total = int(counts['eligible']), int(counts['total'])
        coverage[role] = {'eligible': eligible, 'total': total,
                          'share': _share(eligible, total)}
    return coverage


def _trigger_counts(status: pl.Series) -> dict:
    not_2022 = int((status == 'naics_not_2022').sum())
    with_code = int(status.is_in(_CODED).sum())
    return {'naics_not_2022': not_2022, 'with_code': with_code,
            'share': _share(not_2022, with_code)}


def _trigger(usable: pl.LazyFrame, firm_table: pl.DataFrame) -> dict:
    '''The not-2022 share of the firms with a code: over the firm table, and over the
    distinct UEIs of both roles on each fiscal year's usable reports.'''
    statuses = firm_table.lazy().select('uei', 'firm_status')
    by_year = {}
    for year in WINDOW:
        in_year = usable.filter(pl.col('fiscal_year') == year)
        ueis = pl.concat([in_year.select(uei=column) for _, column in _ROLES]).unique()
        status = ueis.join(statuses, on='uei', how='left').collect()['firm_status']
        by_year[str(year)] = _trigger_counts(status)
    return _trigger_counts(firm_table['firm_status']) | {'by_fiscal_year': by_year}


def _firms_in(usable: pl.LazyFrame, ueis: pl.LazyFrame) -> dict[str, int]:
    '''For each role, and pooled over both, the distinct UEIs on `usable` that `ueis` holds.'''
    by_role = {role: usable.select(uei=column) for role, column in _ROLES}
    frames = by_role | {'all': pl.concat(list(by_role.values()))}
    return {name: int(frame.unique().join(ueis, on='uei', how='semi').select(pl.len())
                      .collect().item())
            for name, frame in frames.items()}


def _extract_counts(extract: pl.DataFrame, layout: ExtractLayout, node_ids: frozenset[str],
                    usable: pl.LazyFrame, unreadable: pl.DataFrame) -> dict:
    rows = _extract_rows(extract, layout)
    skipped = unreadable.lazy().select(uei=_strip('uei'))
    without_rows = skipped.join(rows.select(uei='key'), on='uei', how='anti')
    well_formed = _matches(pl.col('code'), CODE_PATTERN)
    codes = rows.select(
        blank=_count(pl.col('blank')), well_formed=_count(well_formed),
        in_2022=_count(_node(pl.col('code')).is_in(sorted(node_ids))),
        malformed=_count(pl.col('malformed'))).collect().row(0, named=True)
    per_uei = rows.group_by('key').agg(pl.len()).collect()['len']
    years = rows.filter(pl.col('update').is_not_null()).select(
        year=pl.col('update').dt.year().cast(pl.String))
    statuses = rows.select(status=_strip('registration_status'))
    evs = rows.select(evs=_strip('evs_source'))
    return {
        'rows': extract.height,
        'by_registration_status': _tally(statuses, 'status'),
        'rows_per_uei': {'1': int((per_uei == 1).sum()), '2': int((per_uei == 2).sum()),
                         '3+': int((per_uei >= 3).sum())},
        'last_update_by_year': _tally(years, 'year') | {
            'invalid': int(rows.select(_count(pl.col('update').is_null())).collect().item())},
        'evs_source': None if layout.positions['evs_source'] is None else _tally(evs, 'evs'),
        'primary_codes': {name: int(value) for name, value in codes.items()},
        'malformed_unread_rows': _malformed(usable, rows)['unread_rows'],
        'unreadable_lines': unreadable.height,
        'unreadable_firms': _firms_in(usable, skipped),
        'unreadable_firms_not_in_sam': _firms_in(usable, without_rows),
    }


def report_counts(reported: pl.LazyFrame, firm_table: pl.DataFrame, pair_table: pl.DataFrame,
                  extract: pl.DataFrame, layouts: dict[int, SubawardLayout],
                  layout: ExtractLayout, node_ids: frozenset[str],
                  unreadable: pl.DataFrame | None = None) -> dict:
    '''The counts that the preflight prints and `report.json` stores. Every key is text and
    every value is an integer, a share, None, a list or a dict of these.

    `unreadable` holds the extract lines that the reader skipped for their field count, in
    `UNREADABLE_SCHEMA`, and None stands for none. The `extract` section counts them
    (`unreadable_lines`). It also counts the distinct UEIs of usable reports that equal a
    skipped line's stripped UEI, by role and pooled (`unreadable_firms`), and those of them
    with no readable extract row, whose firm status is `not_in_sam`
    (`unreadable_firms_not_in_sam`). These counts read the extract, never the firm table.
    '''
    if unreadable is None:
        unreadable = pl.DataFrame(schema=UNREADABLE_SCHEMA)
    elif list(unreadable.schema.items()) != list(UNREADABLE_SCHEMA.items()):
        raise ValueError('unreadable frame schema is wrong')
    usable = reported.filter(pl.col('report_status') == 'usable')
    fiscal_years = _tally(usable.select(year=pl.col('fiscal_year').cast(pl.String)), 'year',
                          tuple(str(year) for year in WINDOW))
    pair_counts = _tally(pair_table, 'pair_status', PAIR_STATUSES)
    return {
        'reports': _report_sections(reported, layouts),
        'usable_by_fiscal_year': fiscal_years,
        'firms': _firm_counts(firm_table),
        'pairs': pair_counts | {'total': pair_table.height},
        'join_coverage': _coverage(usable, firm_table) | {
            'by_fiscal_year': {
                str(year): _coverage(usable.filter(pl.col('fiscal_year') == year), firm_table)
                for year in WINDOW}},
        'trigger': _trigger(usable, firm_table),
        'extract': _extract_counts(extract, layout, node_ids, usable, unreadable),
        'missing_fields': {
            'subawards': {str(year): list(layouts[year].missing) for year in WINDOW},
            'extract': [field for field in EXTRACT_OPTIONAL if layout.positions[field] is None]},
    }
