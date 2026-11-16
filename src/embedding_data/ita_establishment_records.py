'''Key canonical ITA records, flag text copied from NAICS titles and index entries, and count
the adopted V1 measurements by filing year.

`keyed_records` adds the Stage 3 matching keys through `ita_verification.with_keys`, which
reads only the eight text fields and keeps every other column, so its keys equal those
computed from the 24 Stage 2 summary columns alone. It then adds four copied-text flags.
A flag compares the record's `description_key` with the keys of the official NAICS titles
or index entries. It never uses an index code to infer or correct a record's code.
'''

import polars as pl

from embedding_data import ita_summary
from embedding_data.ita_establishment_expected import V1_COLUMNS
from embedding_data.ita_index_references import INDEX_SCHEMA
from embedding_data.ita_verification import normalize_key, with_keys
from embedding_data.target_inputs import CANONICAL_SCHEMA

SOURCE_COLUMNS = tuple(ita_summary.COLUMNS)
COPY_FLAGS = (
    'flag_copied_title_any',
    'flag_copied_title_native',
    'flag_copied_index_any',
    'flag_copied_index_native',
)
KINDS = ('title', 'index')
KEY_SCHEMA = {'kind': pl.String, 'vintage': pl.Int64, 'key': pl.String}
V1_INPUTS = (
    'year_filing_for',
    'naics_year',
    'description_key',
    'employer_key',
    'flag_empty',
    'flag_placeholder',
    'flag_ein_padded',
    'flag_suspected_mojibake',
    'flag_copied_title_any',
    'flag_copied_title_native',
)
INDEX_INPUTS = ('year_filing_for', *COPY_FLAGS)


def _source_keys(frame: pl.DataFrame, column: str, kind: str) -> list[tuple[str, int, str]]:
    '''The (kind, vintage, key) triples of one source column, refusing any empty key.'''
    label = 'title' if kind == 'title' else 'index entry'
    triples = []
    for vintage, text in frame.select('vintage', column).unique().iter_rows():
        if vintage is None:
            raise ValueError(f'text sources hold a {label} with no vintage')
        key = '' if text is None else normalize_key(text)
        if key == '':
            raise ValueError(f'an official {label} normalizes to an empty key')
        triples.append((kind, vintage, key))
    return triples


def text_keys(titles: pl.DataFrame, index: pl.DataFrame) -> pl.DataFrame:
    '''Normalized official title and index keys, one row per kind, vintage and key.

    `titles` holds the official NAICS titles of every level, with `vintage` and `title`
    columns. `index` has `INDEX_SCHEMA`. Both are keyed with `normalize_key`, so one key
    can belong to several codes and collapses to one row. Rows are sorted by kind, vintage
    and key. A title or an entry that normalizes to the empty key raises `ValueError`.
    '''
    if titles.schema.get('vintage') != pl.Int64 or titles.schema.get('title') != pl.String:
        raise ValueError('titles lack an Int64 vintage and a String title')
    if list(index.schema.items()) != list(INDEX_SCHEMA.items()):
        raise ValueError('index does not have the index schema')
    triples = [
        *_source_keys(titles, 'title', 'title'),
        *_source_keys(index, 'entry', 'index'),
    ]
    return (
        pl.DataFrame(triples, schema=KEY_SCHEMA, orient='row')
        .unique()
        .sort('kind', 'vintage', 'key')
    )


def _require_keys(keys: pl.DataFrame) -> None:
    if list(keys.schema.items()) != list(KEY_SCHEMA.items()):
        raise ValueError('text keys do not have the text key schema')
    if (
        keys.select(pl.any_horizontal(pl.all().is_null())).to_series().any()
        or keys['key'].eq('').any()
        or not set(keys['kind'].to_list()) <= set(KINDS)
    ):
        raise ValueError('text keys hold a null, an empty key or an unknown kind')


def _copy_flags(keys: pl.DataFrame) -> dict[str, pl.Expr]:
    description = pl.col('description_key')
    year = pl.col('naics_year')
    flags = {}
    for kind in KINDS:
        wanted = keys.filter(pl.col('kind').eq(kind))
        own = pl.lit(False)
        for (vintage,), group in wanted.group_by('vintage', maintain_order=True):
            own = own.or_(year.eq(vintage).and_(description.is_in(group['key'].implode())))
        flags[f'flag_copied_{kind}_any'] = description.is_in(wanted['key'].implode())
        flags[f'flag_copied_{kind}_native'] = (
            pl.when(year.is_null()).then(None).otherwise(own)
        )
    return flags


def keyed_records(canonical: pl.LazyFrame, keys: pl.DataFrame) -> pl.LazyFrame:
    '''Canonical records with `source_row`, the Stage 3 keys and the copied-text flags.

    `source_row` is the 0-based physical position, first. The canonical columns follow in
    order, then the columns `with_keys` appends, then `COPY_FLAGS`. An `_any` flag is true
    when `description_key` is a key of that kind in any vintage. A `_native` flag is null
    when `naics_year` is null, else true when `(naics_year, description_key)` is a key of
    that kind. Keys never hold the empty key, so an empty description never matches.
    '''
    if list(canonical.collect_schema().items()) != list(CANONICAL_SCHEMA.items()):
        raise ValueError('records do not have the canonical schema')
    _require_keys(keys)
    return (
        canonical.with_row_index('source_row')
        .with_columns(pl.col('source_row').cast(pl.UInt64))
        .pipe(with_keys)
        .with_columns(**_copy_flags(keys))
    )


def _require_keyed(records: pl.LazyFrame, required: tuple[str, ...]) -> None:
    names = records.collect_schema().names()
    if any(column not in names for column in required):
        raise ValueError('counts need keyed records')


def _count(flag: pl.Expr) -> pl.Expr:
    return flag.fill_null(False).sum().cast(pl.Int64)


def v1_counts(records: pl.LazyFrame) -> pl.DataFrame:
    '''The adopted V1 counts by filing year, equal to `ita_verification.description_report`.

    A repeat group is a known employer with one nonempty description key in one year.
    `n_repeat_rows` sums the sizes of groups above 1, and `n_repeat_excess` sums size - 1.
    '''
    _require_keyed(records, V1_INPUTS)
    groups = (
        records.filter(pl.col('employer_key').is_not_null().and_(pl.col('description_key').ne('')))
        .group_by('year_filing_for', 'employer_key', 'description_key')
        .agg(n=pl.len().cast(pl.Int64))
    )
    repeats = groups.group_by('year_filing_for').agg(
        n_repeat_rows=pl.col('n').filter(pl.col('n').gt(1)).sum(),
        n_repeat_excess=pl.col('n').sub(1).sum(),
    )
    return (
        records.group_by('year_filing_for')
        .agg(
            n_rows=pl.len().cast(pl.Int64),
            n_empty=_count(pl.col('flag_empty')),
            n_placeholder=_count(pl.col('flag_placeholder')),
            n_copied_any=_count(pl.col('flag_copied_title_any')),
            n_native_title_match=_count(pl.col('flag_copied_title_native')),
            n_vintage_unknown=_count(pl.col('naics_year').is_null()),
            n_employer_unknown=_count(pl.col('employer_key').is_null()),
            n_employer_company=_count(pl.col('employer_key').str.starts_with('company:')),
            n_ein_padded=_count(pl.col('flag_ein_padded')),
            n_mojibake=_count(pl.col('flag_suspected_mojibake')),
        )
        .join(repeats, on='year_filing_for', how='left', validate='1:1')
        .with_columns(pl.col('n_repeat_rows', 'n_repeat_excess').fill_null(0))
        .select('year_filing_for', *V1_COLUMNS)
        .sort('year_filing_for')
        .collect()
    )


def index_counts(records: pl.LazyFrame) -> pl.DataFrame:
    '''The copied-index counts by filing year, with title-and-index overlap kept apart.

    `n_copied_title_only_any`, `n_copied_index_only_any` and `n_copied_title_and_index_any`
    partition the records that copy any title or index entry.
    '''
    _require_keyed(records, INDEX_INPUTS)
    title = pl.col('flag_copied_title_any')
    index = pl.col('flag_copied_index_any')
    return (
        records.group_by('year_filing_for')
        .agg(
            n_copied_index_any=_count(index),
            n_copied_index_native=_count(pl.col('flag_copied_index_native')),
            n_copied_title_and_index_any=_count(title.and_(index)),
            n_copied_title_only_any=_count(title.and_(index.not_())),
            n_copied_index_only_any=_count(index.and_(title.not_())),
        )
        .sort('year_filing_for')
        .collect()
    )
