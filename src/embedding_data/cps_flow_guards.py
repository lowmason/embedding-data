'''Guards, flag classes, product eligibility, evidence policies and funnels of the CPS flows.

A product frame gives each one-month link, or each ASEC person, its first-exclusion reason
(SD3) or `eligible`, its sensitivity inclusion reasons and its `strict` status. Every frame
check runs at collection on every row, whatever a caller reads later, and raises a fixed
message that names no value and no person.
'''

import polars as pl

from embedding_data.cps_flow_inputs import DDI_LABELS, FLAG_CLASS_BY_LABEL, FLAG_VARIABLES
from embedding_data.cps_flow_linkage import ONE_MONTH, classify_codes

PRODUCTS = ('monthly_ee', 'monthly_ue', 'asec_retro')
DIMENSIONS = ('industry', 'occupation')
# The first-exclusion order of each product (SD3), ending with `eligible`.
REASONS = {
    'monthly_ee': ('weight_null', 'weight_zero', 'not_employed_both', 'code_not_in_universe',
                   'guard_unusable', 'no_change_reported', 'coding_noise', 'eligible'),
    'monthly_ue': ('weight_null', 'weight_zero', 'origin_new_worker_22',
                   'origin_not_unemployed_21', 'destination_not_employed',
                   'code_not_in_universe', 'eligible'),
    'asec_retro': ('weight_nonpositive', 'not_employed', 'last_year_code_not_in_universe',
                   'current_code_not_in_universe', 'same_category', 'eligible'),
}
EMPLOYED = (10, 12)
UNEMPLOYED_EXPERIENCED, UNEMPLOYED_NEW = 21, 22
WEIGHT_STATUSES = ('positive', 'null', 'zero')
# EMPSAME 01 = No (another employer), 02 = Yes. ACTSAME 01 = Yes (same duties), 02 = No.
OTHER_EMPLOYER, SAME_EMPLOYER = 1, 2
SAME_DUTIES, CHANGED_DUTIES = 1, 2
NOT_USABLE = (96, 97, 99)
# The guard of a same-employer reading, by ACTSAME (spec, Guard). Every other reading has
# one guard in both dimensions: EMPSAME 01 is `changed`, EMPSAME 96, 97 or 99 `unusable`.
SAME_EMPLOYER_GUARDS = {
    'occupation': {SAME_DUTIES: 'same', CHANGED_DUTIES: 'changed',
                   **dict.fromkeys(NOT_USABLE, 'unusable')},
    'industry': {SAME_DUTIES: 'same', CHANGED_DUTIES: 'same', **dict.fromkeys(NOT_USABLE, 'same')},
}
# The code columns and the dimension's own flag of each frame.
MONTHLY_FIELDS = {'industry': ('ind', 'QIND'), 'occupation': ('occ', 'QOCC')}
ASEC_FIELDS = {'industry': ('INDLY', 'IND'), 'occupation': ('OCCLY', 'OCC')}
MONTHLY_FLAGS = ('QEMPSTAT', 'QIND', 'QOCC')
ASEC_FLAGS = ('QIND', 'QOCC', 'QOCCLY', 'QEMPSTAT')
SPECIAL_REASON = 'special_military'
ASEC_REASON = 'asec_no_flag_evidence'
NEW_COLUMNS = ('unit_a', 'unit_b', 'reason', 'strict', 'inclusion_reasons', 'special')
NOISE = 'noise_after_duty_change'
GUARD_MESSAGE = 'an EMPSAME or ACTSAME value is null or outside its DDI set'
LINK_MESSAGE = 'a link is not a one-month link'
WEIGHT_MESSAGE = 'a weight status is not positive, null or zero'


def _require(valid: pl.Expr, message: str) -> pl.Expr:
    '''Return `valid`, failing at collection unless every value is true.

    Polars appends the expression to an error raised here, so frames check with `_validated`.
    '''
    def check(found: pl.Series) -> pl.Series:
        if not found.fill_null(False).all():
            raise ValueError(message)
        return found
    return valid.map_batches(check, return_dtype=pl.Boolean)


def _check_variant(product: str, dimension: str) -> None:
    if product not in PRODUCTS:
        raise ValueError('unknown CPS flow product')
    if dimension not in DIMENSIONS:
        raise ValueError('unknown CPS flow dimension')


def _answered(empsame: pl.Expr, actsame: pl.Expr) -> pl.Expr:
    '''Whether both later-month answers are delivered DDI values (a null is not).'''
    return (empsame.is_in(list(DDI_LABELS['monthly']['EMPSAME'])).fill_null(False)
            & actsame.is_in(list(DDI_LABELS['monthly']['ACTSAME'])).fill_null(False))


def guard_expr(dimension: str, empsame: pl.Expr, actsame: pl.Expr) -> pl.Expr:
    '''Return the later-month guard of a link: `changed`, `same` or `unusable`.

    A null or undelivered `EMPSAME` or `ACTSAME` fails at collection, whichever question
    decides the guard.
    '''
    if dimension not in DIMENSIONS:
        raise ValueError('unknown CPS flow dimension')
    same_employer = actsame.replace_strict(SAME_EMPLOYER_GUARDS[dimension], default=None,
                                           return_dtype=pl.String)
    guard = (pl.when(empsame == OTHER_EMPLOYER).then(pl.lit('changed'))
             .when(empsame.is_in(NOT_USABLE)).then(pl.lit('unusable'))
             .when(empsame == SAME_EMPLOYER).then(same_employer))
    return pl.when(_require(_answered(empsame, actsame), GUARD_MESSAGE)).then(guard)


def flag_classes(file: str, variable: str) -> dict[int, str]:
    '''Return the class of each delivered value of one quality flag, by its DDI label.'''
    if variable not in FLAG_VARIABLES or variable not in DDI_LABELS.get(file, {}):
        raise ValueError('not a delivered quality flag')
    return {value: FLAG_CLASS_BY_LABEL[label]
            for value, label in DDI_LABELS[file][variable].items()}


def _flag_known(file: str, variable: str, value: pl.Expr) -> pl.Expr:
    '''Whether a flag value is null or a delivered DDI value.'''
    return value.is_null() | value.is_in(list(flag_classes(file, variable)))


def _flag_message(file: str, variable: str) -> str:
    return f'{file}/{variable}: a quality flag value is outside its DDI set'


def flag_class_expr(file: str, variable: str, value: pl.Expr) -> pl.Expr:
    '''Return the class of a flag value: its label's class, or `unavailable` for a null.

    A value outside the delivered DDI set fails at collection.
    '''
    known = flag_classes(file, variable)
    found = (pl.when(value.is_null()).then(pl.lit('unavailable'))
             .otherwise(value.replace_strict(known, default=None, return_dtype=pl.String)))
    valid = _require(_flag_known(file, variable, value), _flag_message(file, variable))
    return pl.when(valid).then(found)


def _validated(frame: pl.LazyFrame, checks: list[tuple[pl.Expr, str]]) -> pl.LazyFrame:
    '''Refuse at collection, on every row and whatever is read later, a row that fails a check.

    Each check is a validity expression and its fixed message. The first failing check raises.
    '''
    def check(rows: pl.DataFrame) -> pl.DataFrame:
        passed = rows.select(valid.fill_null(False).all().alias(f'check_{number}')
                             for number, (valid, _) in enumerate(checks)).row(0)
        for ok, (_, message) in zip(passed, checks):
            if not ok:
                raise ValueError(message)
        return rows
    return frame.map_batches(check)


def _weight_check() -> tuple[pl.Expr, str]:
    return pl.col('weight_status').is_in(WEIGHT_STATUSES), WEIGHT_MESSAGE


def _empstat_check(file: str, column: str) -> tuple[pl.Expr, str]:
    return (pl.col(column).is_in(list(DDI_LABELS[file]['EMPSTAT'])),
            f'{file}/EMPSTAT: a value is null or outside its DDI set')


def _link_checks() -> list[tuple[pl.Expr, str]]:
    flags = [(_flag_known('monthly', variable, pl.col(f'{variable.lower()}_{end}')),
              _flag_message('monthly', variable))
             for variable in MONTHLY_FLAGS for end in 'ab']
    return [(pl.col('link_type').eq_missing(ONE_MONTH), LINK_MESSAGE), _weight_check(),
            _empstat_check('monthly', 'empstat_a'), _empstat_check('monthly', 'empstat_b'),
            (_answered(pl.col('empsame_b'), pl.col('actsame_b')), GUARD_MESSAGE), *flags]


def _asec_value_checks() -> list[tuple[pl.Expr, str]]:
    return [_empstat_check('asec', 'EMPSTAT'),
            *((_flag_known('asec', variable, pl.col(variable)), _flag_message('asec', variable))
              for variable in ASEC_FLAGS)]


def _asec_checks() -> list[tuple[pl.Expr, str]]:
    return [_weight_check(), *_asec_value_checks()]


def _flag_entries(variable: str, value: pl.Expr) -> pl.Expr:
    '''The inclusion reason of one monthly flag value, null for nonallocation.'''
    found = flag_class_expr('monthly', variable, value)
    return (pl.when(found == 'unavailable').then(pl.lit(f'flag_unavailable:{variable}'))
            .when(found != 'nonallocation').then(pl.concat_str(pl.lit(f'flag:{variable}:'),
                                                               found)))


def _reasons_list(entries: list[pl.Expr]) -> pl.Expr:
    return pl.concat_list(entries).list.drop_nulls().list.unique().list.sort()


def _monthly_reason(product: str, guard: pl.Expr, outside: pl.Expr) -> pl.Expr:
    weight, empstat_a, empstat_b = (pl.col(name)
                                    for name in ('weight_status', 'empstat_a', 'empstat_b'))
    start = (pl.when(weight == 'null').then(pl.lit('weight_null'))
             .when(weight == 'zero').then(pl.lit('weight_zero')))
    if product == 'monthly_ee':
        return (start.when(~(empstat_a.is_in(EMPLOYED) & empstat_b.is_in(EMPLOYED)))
                .then(pl.lit('not_employed_both'))
                .when(outside).then(pl.lit('code_not_in_universe'))
                .when(guard == 'unusable').then(pl.lit('guard_unusable'))
                .when((guard == 'same') & (pl.col('unit_a') == pl.col('unit_b')))
                .then(pl.lit('no_change_reported'))
                .when(guard == 'same').then(pl.lit('coding_noise'))
                .otherwise(pl.lit('eligible')))
    return (start.when(empstat_a == UNEMPLOYED_NEW).then(pl.lit('origin_new_worker_22'))
            .when(empstat_a != UNEMPLOYED_EXPERIENCED).then(pl.lit('origin_not_unemployed_21'))
            .when(~empstat_b.is_in(EMPLOYED)).then(pl.lit('destination_not_employed'))
            .when(outside).then(pl.lit('code_not_in_universe'))
            .otherwise(pl.lit('eligible')))


def _monthly_frame(frame: pl.LazyFrame, product: str, dimension: str,
                   units: pl.DataFrame) -> pl.LazyFrame:
    field, variable = MONTHLY_FIELDS[dimension]
    ends = (f'{field}_a', f'{field}_b')
    classified = _validated(frame, _link_checks())
    for column in ends:
        classified = classify_codes(classified, column, dimension, units)
    class_a, class_b = (pl.col(f'{column}_class') for column in ends)
    special = (class_a == 'special') | (class_b == 'special')
    guard = guard_expr(dimension, pl.col('empsame_b'), pl.col('actsame_b'))
    flags = [_flag_entries(name, pl.col(f'{name.lower()}_{end}'))
             for name in ('QEMPSTAT', variable) for end in 'ab']
    found = classified.with_columns(
        pl.col(ends[0]).alias('unit_a'), pl.col(ends[1]).alias('unit_b'),
        special.alias('special'),
        _reasons_list([pl.when(special).then(pl.lit(SPECIAL_REASON)), *flags])
        .alias('inclusion_reasons'))
    outside = (class_a == 'not_in_universe') | (class_b == 'not_in_universe')
    found = found.with_columns(_monthly_reason(product, guard, outside).alias('reason'))
    found = found.with_columns(
        ((pl.col('reason') == 'eligible') & (pl.col('inclusion_reasons').list.len() == 0))
        .alias('strict'),
        ((pl.col('reason') == 'coding_noise') & (pl.col('empsame_b') == SAME_EMPLOYER)
         & (pl.col('actsame_b') == CHANGED_DUTIES)).alias(NOISE))
    return found


def _asec_frame(frame: pl.LazyFrame, dimension: str, units: pl.DataFrame) -> pl.LazyFrame:
    last, current = ASEC_FIELDS[dimension]
    classified = _validated(frame, _asec_checks())
    for column in (last, current):
        classified = classify_codes(classified, column, dimension, units)
    class_a, class_b = pl.col(f'{last}_class'), pl.col(f'{current}_class')
    special = (class_a == 'special') | (class_b == 'special')
    reason = (pl.when(pl.col('weight_status').is_in(['null', 'zero']))
              .then(pl.lit('weight_nonpositive'))
              .when(~pl.col('EMPSTAT').is_in(EMPLOYED)).then(pl.lit('not_employed'))
              .when(class_a == 'not_in_universe').then(pl.lit('last_year_code_not_in_universe'))
              .when(class_b == 'not_in_universe').then(pl.lit('current_code_not_in_universe'))
              .when(pl.col(last) == pl.col(current)).then(pl.lit('same_category'))
              .otherwise(pl.lit('eligible')))
    return classified.with_columns(
        pl.col(last).alias('unit_a'), pl.col(current).alias('unit_b'), reason.alias('reason'),
        pl.lit(False).alias('strict'),
        _reasons_list([pl.when(special).then(pl.lit(SPECIAL_REASON)), pl.lit(ASEC_REASON)])
        .alias('inclusion_reasons'),
        special.alias('special'), pl.lit(False).alias(NOISE))


def product_frame(frame: pl.LazyFrame, product: str, dimension: str, *,
                  units: pl.DataFrame) -> pl.LazyFrame:
    '''Return every input row with its unit codes, reason, evidence and `strict` status.

    `frame` holds one-month links with `weight_status` for a monthly product, or ASEC persons
    with `weight_status` for `asec_retro`. The input columns keep their order and are
    followed by `unit_a`, `unit_b`, `reason` (the first exclusion of SD3, or `eligible`),
    `strict`, `inclusion_reasons` (sorted and distinct, for every row), `special` and, for
    industry, `noise_after_duty_change`.

    A monthly row has `special_military` for a special end, `flag_unavailable:<VARIABLE>` for
    a null flag and `flag:<VARIABLE>:<class>` for another non-nonallocation class, at either
    end, for `QEMPSTAT` and the dimension's own flag. `strict` is an `eligible` monthly row
    with no inclusion reason. Every ASEC row has `asec_no_flag_evidence`, and
    `special_military` for a special end, but no flag entry: no `QINDLY` is delivered, so the
    ASEC flags give no evidence for the pair. `strict` is false for every ASEC row.

    A two-month link, a weight status outside `positive`, `null` and `zero`, an undelivered
    `EMPSTAT`, `EMPSAME`, `ACTSAME` or flag value, and an unclassified code fail at collection.
    '''
    _check_variant(product, dimension)
    names = frame.collect_schema().names()
    if product == 'asec_retro':
        found = _asec_frame(frame, dimension, units)
    else:
        found = _monthly_frame(frame, product, dimension, units)
    return found.select(*names, *NEW_COLUMNS, *([NOISE] if dimension == 'industry' else []))


def funnel(frame: pl.LazyFrame, product: str, dimension: str) -> pl.DataFrame:
    '''Count a product frame's reasons in SD3 order, zero-filled; the counts sum to its rows.

    A reason that is not in the product's order, or a null reason, fails.
    '''
    _check_variant(product, dimension)
    found = dict(frame.group_by('reason').agg(pl.len()).collect().iter_rows())
    order = REASONS[product]
    if not set(found) <= set(order):
        raise ValueError('a reason is not in the funnel order of its product')
    return pl.DataFrame({'reason': list(order), 'count': [found.get(name, 0) for name in order]},
                        schema={'reason': pl.String, 'count': pl.UInt64})


def usable_guard_share(links: pl.LazyFrame) -> dict[str, float]:
    '''Return `(changed + same) / total` for each dimension.

    The total is every employed-to-employed one-month link with a positive weight, whatever
    its codes. None such fails.
    '''
    employed = links.filter(
        (pl.col('link_type') == ONE_MONTH) & (pl.col('weight_status') == 'positive')
        & pl.col('empstat_a').is_in(EMPLOYED) & pl.col('empstat_b').is_in(EMPLOYED))
    found = employed.select(
        pl.len().alias('total'),
        *((guard_expr(dimension, pl.col('empsame_b'), pl.col('actsame_b')) != 'unusable')
          .sum().alias(dimension) for dimension in DIMENSIONS)).collect().row(0, named=True)
    if not found['total']:
        raise ValueError('no employed-to-employed one-month link has a positive weight')
    return {dimension: found[dimension] / found['total'] for dimension in DIMENSIONS}


def guard_source_exceptions(links: pl.LazyFrame) -> int:
    '''Count the rows whose `mish_b` is 1 or 5 and whose `empsame_b` is 1 or 2.

    These answers are kept: the count is a diagnostic, and no frame drops them.
    '''
    exception = (pl.col('mish_b').is_in([1, 5])
                 & pl.col('empsame_b').is_in([OTHER_EMPLOYER, SAME_EMPLOYER]))
    return links.select(exception.sum()).collect().item()


def asec_flag_counts(asec: pl.LazyFrame) -> dict:
    '''Count each ASEC flag's values by `EMPSTAT`: `<variable>` -> `<EMPSTAT>` -> `<value>`.

    Every row counts, whatever its weight or codes, and `weight_status` is not needed. Keys
    are strings in numeric order, with a null flag counted as `null` and listed last. An
    undelivered `EMPSTAT` or flag value fails.
    '''
    rows = _validated(asec, _asec_value_checks()).select('EMPSTAT', *ASEC_FLAGS).collect()
    counts = {}
    for variable in ASEC_FLAGS:
        found = rows.group_by('EMPSTAT', variable).len().iter_rows()
        nested: dict[str, dict[str, int]] = {}
        for empstat, value, number in sorted(
                found, key=lambda row: (row[0], row[1] is None, row[1] or 0)):
            key = 'null' if value is None else str(value)
            nested.setdefault(str(empstat), {})[key] = number
        counts[variable] = nested
    return counts
