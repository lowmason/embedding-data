'''Deduplicated ITA text-code pairs, the codes observed under each pair and their paths.

A pair is one employer key and one description key, pooled across every filing year. A
record with no employer key is its own pair, identified by its source row. Every record
belongs to exactly one pair, and the members table records which. A pair is a headline pair
when it has an `eligible_industry()` record, a description key that is neither empty nor a
placeholder, and a known employer. Its headline codes are the codes of those records only,
and a pair with more than one headline node keeps them all with a conflict flag.

Mapping fields come unchanged from Stage 4 and depend only on `(naics_code, naics_year)`.
Copied-text, mojibake, padded-EIN and company-fallback flags never change the headline rule.
'''

import hashlib
from dataclasses import dataclass

import polars as pl

from embedding_data import classification_tables
from embedding_data.classification_tables import NODE_SCHEMA
from embedding_data.ita_area_mix import eligible_industry
from embedding_data.ita_establishment_records import COPY_FLAGS
from embedding_data.ita_naics_mapping import KEY_SCHEMA, MAPPING_SCHEMA

PAIRS_VERSION = 'ita-text-pairs-v1'
HEADLINE_YEARS = (2023, 2025)
PAIR_SCHEMA = {
    'pair_id': pl.String,
    'pair_kind': pl.String,
    'employer_key': pl.String,
    'employer_basis': pl.String,
    'description_key': pl.String,
    'original_strings': pl.List(pl.String),
    'representative_string': pl.String,
    'n_records': pl.UInt64,
    'n_headline_records': pl.UInt64,
    'first_year': pl.Int64,
    'last_year': pl.Int64,
    'n_years': pl.UInt64,
    'flag_headline': pl.Boolean,
    'flag_headline_codes_conflict': pl.Boolean,
    'flag_empty': pl.Boolean,
    'flag_placeholder': pl.Boolean,
    'flag_copied_title_any': pl.Boolean,
    'flag_copied_index_any': pl.Boolean,
    'flag_suspected_mojibake': pl.Boolean,
    'flag_employer_unknown': pl.Boolean,
    'flag_employer_company_fallback': pl.Boolean,
    'n_records_ein_padded': pl.UInt64,
}
PAIR_CODE_SCHEMA = {
    'pair_id': pl.String,
    'naics_code': pl.String,
    'naics_year': pl.Int64,
    'naics_mapping_status': pl.String,
    'naics_2022_candidates': pl.List(pl.String),
    'naics_2022_candidate_node_ids': pl.List(pl.String),
    'naics_2022_node_id': pl.String,
    'naics_deepest_common_node_id': pl.String,
    'flag_naics_crosswalked': pl.Boolean,
    'flag_naics_ambiguous': pl.Boolean,
    'flag_naics_unresolved': pl.Boolean,
    'flag_headline_basis': pl.Boolean,
    'flag_copied_title_native': pl.Boolean,
    'flag_copied_index_native': pl.Boolean,
    'n_records': pl.UInt64,
    'n_records_year_from_dictionary': pl.UInt64,
    'years': pl.List(pl.Int64),
}
MEMBER_SCHEMA = {'source_row': pl.UInt64, 'pair_id': pl.String}
PATH_SCHEMA = classification_tables.PATH_SCHEMA
STATE_SCHEMA = {**KEY_SCHEMA, **MAPPING_SCHEMA}
RECORD_SCHEMA = {
    'source_row': pl.UInt64,
    'year_filing_for': pl.Int64,
    'industry_description': pl.String,
    'naics_year_from_dictionary': pl.Boolean,
    **STATE_SCHEMA,
    'description_key': pl.String,
    'employer_key': pl.String,
    'flag_empty': pl.Boolean,
    'flag_placeholder': pl.Boolean,
    'flag_ein_padded': pl.Boolean,
    'flag_suspected_mojibake': pl.Boolean,
    **{flag: pl.Boolean for flag in COPY_FLAGS},
}
PAIR_KEY = ['pair_kind', 'employer_key', 'description_key', '_unknown_row']
CODE_KEY = ['pair_id', 'naics_code', 'naics_year']
CODE_FIELDS = [
    'naics_mapping_status',
    'naics_2022_candidates',
    'naics_2022_node_id',
    'naics_deepest_common_node_id',
    'flag_naics_crosswalked',
    'flag_naics_ambiguous',
    'flag_naics_unresolved',
    'flag_headline_basis',
    'flag_copied_title_native',
    'flag_copied_index_native',
]


@dataclass(frozen=True)
class TextPairs:
    pairs: pl.LazyFrame
    pair_codes: pl.LazyFrame
    members: pl.LazyFrame
    paths: pl.LazyFrame
    report: dict


def pair_id(kind: str, fields: tuple[str, ...]) -> str:
    '''The SHA-256 hex digest of the version, the kind and the fields.

    Each part is encoded as UTF-8 and prefixed by its byte length as 8 big-endian bytes, so
    no two different part lists share an encoding.
    '''
    digest = hashlib.sha256()
    for part in (PAIRS_VERSION, kind, *fields):
        encoded = part.encode('utf-8')
        digest.update(len(encoded).to_bytes(8, 'big'))
        digest.update(encoded)
    return digest.hexdigest()


def _has_columns(frame: pl.LazyFrame, schema: dict) -> bool:
    found = frame.collect_schema()
    return all(found.get(name) == dtype for name, dtype in schema.items())


def require_single_mapping_state(records: pl.LazyFrame) -> None:
    '''Refuse records whose `(naics_code, naics_year)` key shows two mapping states.'''
    if not _has_columns(records, STATE_SCHEMA):
        raise ValueError('records lack the NAICS mapping columns')
    states = (
        records.select(*STATE_SCHEMA)
        .unique()
        .group_by(*KEY_SCHEMA)
        .agg(n=pl.len())
        .filter(pl.col('n').gt(1))
    )
    if states.select(pl.len()).collect().item():
        raise ValueError('contradictory mapping states')


def _require_references(nodes: pl.DataFrame, code_paths: pl.DataFrame) -> None:
    if (
        list(nodes.schema.items()) != list(NODE_SCHEMA.items())
        or list(code_paths.schema.items()) != list(PATH_SCHEMA.items())
    ):
        raise ValueError('nodes or code paths do not have the Stage 4 schemas')


def _basis(employer: pl.Expr) -> pl.Expr:
    return (
        pl.when(employer.is_null())
        .then(pl.lit('unknown'))
        .when(employer.str.starts_with('ein:'))
        .then(pl.lit('ein'))
        .when(employer.str.starts_with('company:'))
        .then(pl.lit('company'))
    )


def _pair_ids(frame: pl.LazyFrame) -> pl.DataFrame:
    '''One row per pair key with its pair ID, hashed once per pair.'''
    keys = frame.select(PAIR_KEY).unique().collect()
    if keys.select(_basis(pl.col('employer_key')).is_null().any()).item():
        raise ValueError('an employer key has no known basis')
    identities = [
        pair_id('employer', (employer, description))
        if kind == 'employer'
        else pair_id('unknown_employer', (str(row),))
        for kind, employer, description, row in keys.iter_rows()
    ]
    return keys.with_columns(pair_id=pl.Series(identities, dtype=pl.String))


def _strings(members: pl.LazyFrame) -> pl.LazyFrame:
    '''Distinct originals, nulls first in code-point order, and the most frequent of them.'''
    description = pl.col('industry_description')
    return (
        members.group_by('pair_id', 'industry_description')
        .agg(_n=pl.len())
        .group_by('pair_id')
        .agg(
            original_strings=description.sort(nulls_last=False),
            representative_string=description.sort_by(
                '_n', 'industry_description', descending=[True, False], nulls_last=False
            ).first(),
        )
    )


def _headline_rule() -> pl.Expr:
    '''The headline rule over pair columns.

    A headline pair has an eligible record, a description key that is neither empty nor a
    placeholder, and a known employer. The build and the validator share this rule.
    '''
    return (
        pl.col('n_headline_records')
        .gt(0)
        .and_(pl.col('flag_empty').not_())
        .and_(pl.col('flag_placeholder').not_())
        .and_(pl.col('pair_kind').eq('employer'))
    )


def _pairs(members: pl.LazyFrame) -> pl.DataFrame:
    basis = pl.col('flag_headline_basis')
    summary = members.group_by('pair_id').agg(
        pl.col('pair_kind', 'employer_key', 'description_key').first(),
        n_records=pl.len().cast(pl.UInt64),
        n_headline_records=basis.sum().cast(pl.UInt64),
        first_year=pl.col('year_filing_for').min(),
        last_year=pl.col('year_filing_for').max(),
        n_years=pl.col('year_filing_for').n_unique().cast(pl.UInt64),
        flag_empty=pl.col('flag_empty').first(),
        flag_placeholder=pl.col('flag_placeholder').first(),
        flag_copied_title_any=pl.col('flag_copied_title_any').first(),
        flag_copied_index_any=pl.col('flag_copied_index_any').first(),
        flag_suspected_mojibake=pl.col('flag_suspected_mojibake').any(),
        n_records_ein_padded=pl.col('flag_ein_padded').sum().cast(pl.UInt64),
        n_headline_nodes=pl.col('naics_2022_node_id').filter(basis).drop_nulls().n_unique(),
    )
    return (
        summary.join(_strings(members), on='pair_id', how='left', validate='1:1')
        .with_columns(
            employer_basis=_basis(pl.col('employer_key')), flag_headline=_headline_rule()
        )
        .with_columns(
            flag_headline_codes_conflict=pl.col('flag_headline').and_(
                pl.col('n_headline_nodes').gt(1)
            ),
            flag_employer_unknown=pl.col('employer_basis').eq('unknown'),
            flag_employer_company_fallback=pl.col('employer_basis').eq('company'),
        )
        .select(*PAIR_SCHEMA, 'n_headline_nodes')
        .sort('pair_id')
        .collect()
    )


def _pair_codes(members: pl.LazyFrame, nodes: pl.DataFrame) -> pl.DataFrame:
    codes = (
        members.group_by(CODE_KEY)
        .agg(
            pl.col(CODE_FIELDS).first(),
            n_records=pl.len().cast(pl.UInt64),
            n_records_year_from_dictionary=pl.col('naics_year_from_dictionary')
            .fill_null(False)
            .sum()
            .cast(pl.UInt64),
            years=pl.col('year_filing_for').unique().sort(),
        )
        .collect()
    )
    leaves = nodes.filter(
        pl.col('vintage').eq(2022).and_(pl.col('level').eq('national_industry'))
    )
    node_of = dict(leaves.select('code', 'node_id').iter_rows())
    wanted = codes['naics_2022_candidates'].explode().drop_nulls().unique()
    if any(code not in node_of for code in wanted.to_list()):
        raise ValueError('a candidate has no NAICS 2022 national industry node')
    candidate_nodes = pl.col('naics_2022_candidates').list.eval(
        pl.element().replace_strict(node_of, return_dtype=pl.String)
    )
    return (
        codes.with_columns(naics_2022_candidate_node_ids=candidate_nodes)
        .select(*PAIR_CODE_SCHEMA)
        .sort(CODE_KEY, nulls_last=False)
    )


def _referenced(codes: pl.DataFrame) -> pl.Series:
    '''Every node a pair-code row references, as a candidate or as a scalar node.'''
    return (
        pl.concat(
            [codes['naics_2022_candidate_node_ids'].explode(), codes['naics_2022_node_id']]
        )
        .drop_nulls()
        .unique()
    )


def _paths(codes: pl.DataFrame, code_paths: pl.DataFrame) -> pl.DataFrame:
    referenced = _referenced(codes)
    paths = code_paths.filter(pl.col('node_id').is_in(referenced.implode()))
    if set(referenced.to_list()) - set(paths['node_id'].to_list()):
        raise ValueError('a referenced node has no path')
    return paths.sort('node_id')


def _distribution(values: pl.Series) -> dict:
    value = pl.col('n_records')
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


def _report(members: pl.LazyFrame, pairs: pl.DataFrame) -> dict:
    by_year = ['year_filing_for', 'naics_mapping_status', 'flag_headline_basis']
    text_state = (
        pl.when(pl.col('flag_empty'))
        .then(pl.lit('empty'))
        .when(pl.col('flag_placeholder'))
        .then(pl.lit('placeholder'))
        .otherwise(pl.lit('text'))
    )
    by_text = ['pair_kind', 'flag_headline', 'text_state']
    headline = pairs.filter(pl.col('flag_headline'))
    return {
        'n_pairs': pairs.height,
        'n_records': members.select(pl.len()).collect().item(),
        'records_by_year_status_basis': members.group_by(by_year)
        .agg(n=pl.len())
        .sort(by_year)
        .collect()
        .to_dicts(),
        'pairs_by_kind_headline_text': pairs.with_columns(text_state=text_state)
        .group_by(by_text)
        .agg(n=pl.len())
        .sort(by_text)
        .to_dicts(),
        'headline_pairs_by_node_count': headline.group_by('n_headline_nodes')
        .agg(n=pl.len())
        .sort('n_headline_nodes')
        .to_dicts(),
        'headline_pair_record_distribution': _distribution(headline['n_records']),
    }


def build_pairs(
    records: pl.LazyFrame, nodes: pl.DataFrame, code_paths: pl.DataFrame
) -> TextPairs:
    '''The pair, pair-code, member and path tables of keyed records, with their report.

    `records` is `ita_establishment_records.keyed_records` output. `nodes` and `code_paths`
    are the Stage 4 `naics_nodes` and `code_paths` frames. Each table is computed once.
    '''
    require_single_mapping_state(records)
    if not _has_columns(records, RECORD_SCHEMA):
        raise ValueError('pairs need keyed records')
    _require_references(nodes, code_paths)
    basis = eligible_industry()
    year = pl.col('year_filing_for')
    outside = records.filter(basis.and_(year.is_between(*HEADLINE_YEARS).not_()))
    if outside.select(pl.len()).collect().item():
        raise ValueError('an eligible record falls outside 2023 to 2025')
    unknown = pl.col('employer_key').is_null()
    frame = records.select(*RECORD_SCHEMA).with_columns(
        flag_headline_basis=basis,
        pair_kind=pl.when(unknown).then(pl.lit('unknown_employer')).otherwise(pl.lit('employer')),
        _unknown_row=pl.when(unknown).then(pl.col('source_row')),
    )
    identities = _pair_ids(frame)
    members = frame.join(
        identities.lazy(), on=PAIR_KEY, how='left', nulls_equal=True, validate='m:1'
    )
    pairs = _pairs(members)
    codes = _pair_codes(members, nodes)
    paths = _paths(codes, code_paths)
    report = _report(members, pairs)
    return TextPairs(
        pairs=pairs.select(*PAIR_SCHEMA).lazy(),
        pair_codes=codes.lazy(),
        members=members.select(*MEMBER_SCHEMA).sort('source_row').collect().lazy(),
        paths=paths.lazy(),
        report=report,
    )


def _reject(frame: pl.DataFrame, condition: pl.Expr, message: str) -> None:
    '''Raise `message` when `condition` holds, or is unknown, for any row.'''
    if frame.select(condition.fill_null(True).any()).item():
        raise ValueError(message)


def validate_pairs(result: TextPairs, records: pl.LazyFrame, code_paths: pl.DataFrame) -> None:
    '''Check the pair tables against the records they cover and the Stage 4 paths.'''
    if list(code_paths.schema.items()) != list(PATH_SCHEMA.items()):
        raise ValueError('code paths do not have the path schema')
    frames = [result.pairs, result.pair_codes, result.members, result.paths]
    schemas = [PAIR_SCHEMA, PAIR_CODE_SCHEMA, MEMBER_SCHEMA, PATH_SCHEMA]
    if any(
        list(frame.collect_schema().items()) != list(schema.items())
        for frame, schema in zip(frames, schemas)
    ):
        raise ValueError('pair tables do not have their schemas')
    pairs, codes, members, paths = (frame.collect() for frame in frames)
    n = records.select(pl.len()).collect().item()
    if pairs['pair_id'].is_duplicated().any():
        raise ValueError('pair IDs repeat')
    rows = pl.int_range(0, n, dtype=pl.UInt64, eager=True)
    if members.height != n or not members['source_row'].sort().equals(rows):
        raise ValueError('members do not hold each source row once')
    if members.join(pairs, on='pair_id', how='anti').height:
        raise ValueError('a member names no pair')
    if pairs['n_records'].sum() != n:
        raise ValueError('pair record counts do not sum to the record count')
    counted = members.group_by('pair_id').agg(_members=pl.len().cast(pl.UInt64))
    _reject(
        pairs.join(counted, on='pair_id', how='left'),
        pl.col('n_records').ne(pl.col('_members')),
        'pair member counts differ from n_records',
    )
    if (
        pairs.join(codes, on='pair_id', how='anti').height
        or codes.join(pairs, on='pair_id', how='anti').height
    ):
        raise ValueError('pairs and pair codes disagree on pair IDs')
    if codes.select(CODE_KEY).is_duplicated().any():
        raise ValueError('pair code keys repeat')
    basis = pl.col('flag_headline_basis')
    sums = codes.group_by('pair_id').agg(
        _codes=pl.col('n_records').sum(),
        _basis=pl.col('n_records').filter(basis).sum(),
        _nodes=pl.col('naics_2022_node_id').filter(basis).drop_nulls().n_unique(),
    )
    joined = pairs.join(sums, on='pair_id', how='left')
    _reject(
        joined,
        pl.col('n_records').ne(pl.col('_codes')),
        'pair code counts differ from n_records',
    )
    _reject(
        joined,
        pl.col('n_headline_records')
        .ne(pl.col('_basis'))
        .or_(pl.col('flag_headline').ne(_headline_rule())),
        'headline invariants fail',
    )
    _reject(
        joined,
        pl.col('flag_headline_codes_conflict').ne(
            pl.col('flag_headline').and_(pl.col('_nodes').gt(1))
        ),
        'headline conflict flags differ from the basis nodes',
    )
    _reject(
        pairs,
        pl.col('pair_kind')
        .eq('unknown_employer')
        .and_(
            pl.col('n_records')
            .ne(1)
            .or_(pl.col('employer_key').is_not_null())
            .or_(pl.col('flag_employer_unknown').not_())
        ),
        'unknown-employer pairs are malformed',
    )
    stage4 = code_paths.rename({'path': '_stage4'})
    _reject(
        paths.join(stage4, on='node_id', how='left'),
        pl.col('path').ne_missing(pl.col('_stage4')),
        'paths differ from the Stage 4 rows',
    )
    referenced = set(_referenced(codes).to_list())
    if paths.height != len(referenced) or set(paths['node_id'].to_list()) != referenced:
        raise ValueError('referenced nodes differ from the path nodes')
