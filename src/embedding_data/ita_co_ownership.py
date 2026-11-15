'''Directional ITA co-ownership shares between NAICS 2022 national industries.

An employer is a usable, unreconstructed EIN (`ein_key`). For employer `e` and filing year
`t`, `S(e,t)` is the set of `naics_2022_node_id` values on its eligible records in `t`. The
target for the ordered pair `(a,b)` is `J(a,b) / n(a)`: `J(a,b)` counts employers with both
industries in one `S(e,t)`, and `n(a)` counts employers with `a` in some `S(e,t)`. Records
are deduplicated to `(ein_key, year, node)` before the self-join, so record multiplicity
never adds weight to `J` or `n`.

A record is eligible unless an exclusion applies. Each record takes the first reason in
`EXCLUSIONS` order: a filing year outside `YEARS`, an industry that fails
`ita_area_mix.eligible_industry()`, a null `ein_key`, or a `flag_ein_padded` that is not
false. The padded sensitivity admits the eligible records plus the `ein_padded` exclusions,
whose zero-filled `ein_key` joins any unpadded spelling of the same key.
'''

from dataclasses import dataclass

import polars as pl

from embedding_data.classification_tables import NODE_SCHEMA
from embedding_data.ita_area_mix import eligible_industry
from embedding_data.target_contract import TARGET_KEY_COLUMNS, TARGET_SCHEMA, validate_targets

CO_OWNERSHIP_VERSION = 'ita-co-ownership-v1'
YEARS = (2023, 2024, 2025)
SAMPLE_SET = 'ita_300a_2023_2025'
TOLERANCE = 1e-12
UNIVERSE = (
    'OSHA ITA Form 300A is a program-selected filing subset, not a frame representative '
    'of all establishments or firms. Voluntary and outside-rule filings are retained, and '
    'reported codes and employment are unvalidated. This target counts employers '
    'identified by a usable, unreconstructed EIN that filed 2023–2025 '
    'establishment-year records with valid native NAICS 2022 industries. An EIN is a '
    'tax-filing entity, not necessarily a whole firm. It is conditional on that '
    'eligibility population.'
)
METADATA = dict(source='osha_ita', family='co_ownership', unit_a_type='naics_national_industry',
                unit_b_type='naics_national_industry', measure='employer_share',
                se_method='none', sample_set=SAMPLE_SET, vintage='naics=2022',
                universe=UNIVERSE)
SIZE_LABEL = 'size_gate_pending'
PADDED_LABEL = 'numerator:ein_padded_sensitivity:true'
MARGINAL_SCHEMA = {
    'node_id': pl.String,
    'n_employers': pl.UInt64,
    'n_multi_industry_employers': pl.UInt64,
    'n_records': pl.UInt64,
    'n_employers_including_padded': pl.UInt64,
    'n_employers_partial': pl.UInt64,
}
SUPPORT_SCHEMA = {
    'unit_a': pl.String,
    'unit_b': pl.String,
    'j_employers': pl.UInt64,
    'j_2023': pl.UInt64,
    'j_2024': pl.UInt64,
    'j_2025': pl.UInt64,
    'j_including_padded': pl.UInt64,
}
EXCLUSIONS = ('year_outside_window', 'industry_ineligible', 'ein_unusable', 'ein_padded')
RECORD_FLAGS = (
    'flag_employment',
    'flag_hours_per_employee',
    'flag_below_filing_size',
    'flag_naics_year_unknown',
    'flag_outside_filing_industry',
    'flag_outside_filing_rule',
    'flag_filing_rule_label_bridged',
    'flag_filing_reference_ambiguous',
    'naics_year_from_dictionary',
)
ELIGIBLE = 'eligible'
RECORD_SCHEMA = {
    'year_filing_for': pl.Int64,
    'naics_mapping_status': pl.String,
    'naics_2022_node_id': pl.String,
    'flag_naics_crosswalked': pl.Boolean,
    'flag_naics_ambiguous': pl.Boolean,
    'flag_naics_unresolved': pl.Boolean,
    'ein_key': pl.String,
    'flag_ein_padded': pl.Boolean,
    **{flag: pl.Boolean for flag in RECORD_FLAGS},
}
EMPLOYER_YEAR = ['ein_key', 'year_filing_for']
PRESENCE = [*EMPLOYER_YEAR, 'naics_2022_node_id']
CELL = ['unit_a', 'unit_b']
YEAR_COUNTS = [f'j_{year}' for year in YEARS]


@dataclass(frozen=True)
class CoOwnership:
    targets: pl.LazyFrame
    marginals: pl.LazyFrame
    support: pl.LazyFrame
    report: dict


def _require_records(records: pl.LazyFrame) -> None:
    found = records.collect_schema()
    if any(found.get(name) != dtype for name, dtype in RECORD_SCHEMA.items()):
        raise ValueError('co-ownership needs keyed records')


def _reason() -> pl.Expr:
    '''The first exclusion reason in `EXCLUSIONS` order that applies, or `eligible`.'''
    return (
        pl.when(pl.col('year_filing_for').is_in(list(YEARS)).fill_null(False).not_())
        .then(pl.lit('year_outside_window'))
        .when(eligible_industry().not_())
        .then(pl.lit('industry_ineligible'))
        .when(pl.col('ein_key').is_null())
        .then(pl.lit('ein_unusable'))
        .when(pl.col('_padded'))
        .then(pl.lit('ein_padded'))
        .otherwise(pl.lit(ELIGIBLE))
    )


def _presence(frame: pl.LazyFrame) -> pl.DataFrame:
    '''One row per employer, year and industry.'''
    return frame.select(PRESENCE).unique().collect()


def _pairs(presence: pl.DataFrame) -> pl.DataFrame:
    '''One row per employer, year and ordered pair of distinct industries in that year.'''
    node = 'naics_2022_node_id'
    left = presence.rename({node: 'unit_a'})
    right = presence.rename({node: 'unit_b'})
    return left.join(right, on=EMPLOYER_YEAR).filter(pl.col('unit_a').ne(pl.col('unit_b')))


def _employers() -> pl.Expr:
    return pl.col('ein_key').n_unique().cast(pl.UInt64)


def _support(pairs: pl.DataFrame, padded_pairs: pl.DataFrame) -> pl.DataFrame:
    year = pl.col('year_filing_for')
    headline = pairs.group_by(CELL).agg(
        j_employers=_employers(),
        **{f'j_{t}': year.eq(t).sum().cast(pl.UInt64) for t in YEARS},
    )
    padded = padded_pairs.group_by(CELL).agg(j_including_padded=_employers())
    return (
        headline.join(padded, on=CELL, how='left', validate='1:1')
        .select(*SUPPORT_SCHEMA)
        .sort(CELL)
    )


def _marginals(
    frame: pl.LazyFrame,
    presence: pl.DataFrame,
    padded_presence: pl.DataFrame,
    pairs: pl.DataFrame,
) -> pl.DataFrame:
    node = 'naics_2022_node_id'
    reason = pl.col('reason')
    records = (
        frame.filter(reason.eq(ELIGIBLE))
        .group_by(node)
        .agg(n_records=pl.len().cast(pl.UInt64))
        .collect()
    )
    multi = pairs.group_by('unit_a').agg(n_multi_industry_employers=_employers())
    padded = padded_presence.group_by(node).agg(n_employers_including_padded=_employers())
    ineligible = (
        frame.filter(reason.eq('industry_ineligible').and_(pl.col('_padded').not_()))
        .select(EMPLOYER_YEAR)
        .unique()
        .collect()
    )
    partial = (
        presence.join(ineligible, on=EMPLOYER_YEAR, how='semi')
        .group_by(node)
        .agg(n_employers_partial=_employers())
    )
    counts = ['n_multi_industry_employers', 'n_employers_partial']
    return (
        presence.group_by(node)
        .agg(n_employers=_employers())
        .join(multi.rename({'unit_a': node}), on=node, how='left', validate='1:1')
        .join(records, on=node, how='left', validate='1:1')
        .join(padded, on=node, how='left', validate='1:1')
        .join(partial, on=node, how='left', validate='1:1')
        .with_columns(pl.col(counts).fill_null(0))
        .rename({node: 'node_id'})
        .select(*MARGINAL_SCHEMA)
        .sort('node_id')
    )


def _flags(padded_differs: pl.Expr) -> pl.Expr:
    '''The sorted unique flags of a cell. The build and the validator share them.'''
    return (
        pl.concat_list(pl.lit(SIZE_LABEL), pl.when(padded_differs).then(pl.lit(PADDED_LABEL)))
        .list.drop_nulls()
        .list.unique()
        .list.sort()
    )


def _targets(support: pl.DataFrame, marginals: pl.DataFrame) -> pl.DataFrame:
    employers = marginals.select(pl.col('node_id').alias('unit_a'), 'n_employers')
    j = pl.col('j_employers')
    return (
        support.join(employers, on='unit_a', how='left', validate='m:1')
        .with_columns(
            *[pl.lit(value).alias(key) for key, value in METADATA.items()],
            value=j.truediv(pl.col('n_employers')),
            se=pl.lit(None, dtype=pl.Float64),
            n_unweighted=j,
            n_weighted=j.cast(pl.Float64),
            flags=_flags(pl.col('j_including_padded').ne(j)),
        )
        .select(*TARGET_SCHEMA)
        .sort(TARGET_KEY_COLUMNS)
    )


def _partition(frame: pl.LazyFrame) -> list[dict]:
    reason = pl.col('reason')
    return (
        frame.group_by('year_filing_for')
        .agg(*[reason.eq(name).sum().cast(pl.Int64).alias(name)
               for name in (*EXCLUSIONS, ELIGIBLE)])
        .sort('year_filing_for', nulls_last=False)
        .collect()
        .to_dicts()
    )


def _flag_counts(eligible: pl.LazyFrame) -> list[dict]:
    '''True and null counts of each record flag among eligible records, for every year.'''
    year = pl.col('year_filing_for')
    columns = []
    for t in YEARS:
        for flag in RECORD_FLAGS:
            value = pl.col(flag).filter(year.eq(t))
            columns.append(value.sum().cast(pl.Int64).alias(f'{t}:{flag}:n_true'))
            columns.append(value.is_null().sum().cast(pl.Int64).alias(f'{t}:{flag}:n_null'))
    counts = eligible.select(columns).collect().row(0, named=True)
    return [
        {
            'year_filing_for': t,
            'flag_name': flag,
            'n_true': counts[f'{t}:{flag}:n_true'],
            'n_null': counts[f'{t}:{flag}:n_null'],
        }
        for t in YEARS
        for flag in RECORD_FLAGS
    ]


def _distribution(values: pl.Series) -> dict:
    value = pl.col(values.name)
    return (
        values.to_frame()
        .select(
            count=pl.len(),
            min=value.min(),
            p25=value.quantile(0.25, interpolation='nearest'),
            median=value.median(),
            p75=value.quantile(0.75, interpolation='nearest'),
            p95=value.quantile(0.95, interpolation='nearest'),
            max=value.max(),
        )
        .row(0, named=True)
    )


def _report(
    frame: pl.LazyFrame,
    presence: pl.DataFrame,
    padded_presence: pl.DataFrame,
    padded_pairs: pl.DataFrame,
    targets: pl.DataFrame,
    marginals: pl.DataFrame,
) -> dict:
    node = 'naics_2022_node_id'
    padded_cells = padded_pairs.select(CELL).unique()
    padded_nodes = padded_presence.select(node).unique()
    return {
        'N': presence['ein_key'].n_unique(),
        'N_including_padded': padded_presence['ein_key'].n_unique(),
        'partition_by_year': _partition(frame),
        'eligible_flags_by_year': _flag_counts(frame.filter(pl.col('reason').eq(ELIGIBLE))),
        'n_cells': targets.height,
        'n_cells_padded_label': targets['flags'].list.contains(PADDED_LABEL).sum(),
        'n_sensitivity_only_cells': padded_cells.join(
            targets.select(CELL), on=CELL, how='anti').height,
        'n_padded_only_nodes': padded_nodes.join(
            presence.select(node), on=node, how='anti').height,
        'cell_count_distribution': _distribution(targets['n_unweighted']),
        'marginal_employer_distribution': _distribution(marginals['n_employers']),
    }


def estimate(records: pl.LazyFrame) -> CoOwnership:
    '''The co-ownership targets, marginals and support of keyed records, with their report.

    `records` is `ita_establishment_records.keyed_records` output. Targets are sorted by
    `TARGET_KEY_COLUMNS`, support rows by `unit_a` and `unit_b`, and marginal rows by
    `node_id`. A marginal row exists for each industry with an eligible employer.
    '''
    _require_records(records)
    frame = (
        records.select(*RECORD_SCHEMA)
        .with_columns(_padded=pl.col('flag_ein_padded').fill_null(True))
        .with_columns(reason=_reason())
    )
    reason = pl.col('reason')
    presence = _presence(frame.filter(reason.eq(ELIGIBLE)))
    padded_presence = _presence(frame.filter(reason.is_in([ELIGIBLE, 'ein_padded'])))
    pairs = _pairs(presence)
    padded_pairs = _pairs(padded_presence)
    support = _support(pairs, padded_pairs)
    marginals = _marginals(frame, presence, padded_presence, pairs)
    targets = _targets(support, marginals)
    report = _report(frame, presence, padded_presence, padded_pairs, targets, marginals)
    return CoOwnership(
        targets=targets.lazy(), marginals=marginals.lazy(), support=support.lazy(), report=report
    )


def _reject(frame: pl.DataFrame, condition: pl.Expr, message: str) -> None:
    '''Raise `message` when `condition` holds, or is unknown, for any row.'''
    if frame.select(condition.fill_null(True).any()).item():
        raise ValueError(message)


def _schema(frame: pl.LazyFrame) -> list:
    return list(frame.collect_schema().items())


def validate_co_ownership(result: CoOwnership, nodes: pl.DataFrame) -> None:
    '''Check the targets, marginals and support against each other and the NAICS nodes.

    `nodes` is the Stage 4 `naics_nodes` frame. Every unit must be one of its NAICS 2022
    national-industry nodes. A null key or count in the support or the marginals fails, and
    each marginal node has at least as many eligible records as employers.
    '''
    validate_targets(result.targets)
    if (_schema(result.marginals) != list(MARGINAL_SCHEMA.items())
            or _schema(result.support) != list(SUPPORT_SCHEMA.items())):
        raise ValueError('co-ownership companion schemas differ')
    if list(nodes.schema.items()) != list(NODE_SCHEMA.items()):
        raise ValueError('nodes do not have the node schema')
    targets, marginals, support = (
        frame.collect() for frame in (result.targets, result.marginals, result.support)
    )
    _reject(targets, pl.any_horizontal([pl.col(key).ne(value) for key, value in METADATA.items()]),
            'co-ownership rows differ from the metadata')
    leaves = nodes.filter(
        pl.col('system').eq('naics')
        .and_(pl.col('vintage').eq(2022))
        .and_(pl.col('level').eq('national_industry'))
    )['node_id'].implode()
    unit_a, unit_b = pl.col('unit_a'), pl.col('unit_b')
    _reject(targets, unit_a.is_in(leaves).not_().or_(unit_b.is_in(leaves).not_())
            .or_(unit_a.eq(unit_b)),
            'co-ownership units are not two distinct NAICS 2022 national industries')
    j = pl.col('n_unweighted')
    mirrors = targets.select(unit_a=unit_b, unit_b=unit_a, _mirror=j)
    _reject(targets.join(mirrors, on=CELL, how='left'), j.ne(pl.col('_mirror')),
            'co-ownership cells lack an equal mirror')
    _reject(targets, j.lt(1).or_(pl.col('n_weighted').ne(j.cast(pl.Float64)))
            .or_(pl.col('se').is_not_null()), 'co-ownership counts are invalid')
    employers = marginals.select('node_id', 'n_employers')
    shares = (
        targets.join(employers.rename({'node_id': 'unit_a', 'n_employers': '_n_a'}),
                     on='unit_a', how='left')
        .join(employers.rename({'node_id': 'unit_b', 'n_employers': '_n_b'}),
              on='unit_b', how='left')
    )
    _reject(shares, pl.col('value').sub(j.truediv(pl.col('_n_a'))).abs().gt(TOLERANCE),
            'co-ownership values differ from the shares')
    _reject(shares, j.gt(pl.col('_n_a')).or_(j.gt(pl.col('_n_b'))),
            'co-ownership counts exceed a marginal')
    if not support.select(CELL).sort(CELL).equals(targets.select(CELL).sort(CELL)):
        raise ValueError('co-ownership support does not match the targets one to one')
    joined = targets.select(*CELL, 'n_unweighted', 'flags').join(support, on=CELL, how='left')
    _reject(joined, pl.col('j_employers').ne(j)
            .or_(pl.max_horizontal(YEAR_COUNTS).gt(j))
            .or_(pl.sum_horizontal(YEAR_COUNTS).lt(j))
            .or_(pl.any_horizontal(pl.col(YEAR_COUNTS).is_null())),
            'co-ownership support counts disagree with the targets')
    padded = pl.col('j_including_padded')
    _reject(joined, padded.lt(j), 'co-ownership padded counts fall below J')
    _reject(joined, pl.col('flags').ne(_flags(padded.ne(j))),
            'co-ownership flags disagree with the support')
    if marginals['node_id'].is_null().any():
        raise ValueError('co-ownership marginal nodes are null')
    if marginals['node_id'].is_duplicated().any():
        raise ValueError('co-ownership marginal nodes repeat')
    n = pl.col('n_employers')
    multi = pl.col('n_multi_industry_employers')
    _reject(marginals, n.lt(1).or_(multi.gt(n)).or_(pl.col('n_employers_partial').gt(n))
            .or_(pl.col('n_records').lt(n))
            .or_(pl.col('n_employers_including_padded').lt(n)),
            'co-ownership marginal counts are out of bounds')
    widest = targets.group_by('unit_a').agg(_widest=j.max()).rename({'unit_a': 'node_id'})
    _reject(marginals.join(widest, on='node_id', how='left'),
            multi.lt(pl.col('_widest').fill_null(0))
            .or_(multi.eq(0).ne(pl.col('_widest').is_null())),
            'co-ownership multi-industry counts disagree with the targets')
