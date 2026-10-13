import polars as pl

from embedding_data.classification_tables import below_header, column

CHAIN = (2002, 2007, 2012, 2017, 2022)
RELATION_SCHEMA = {
    'source_vintage': pl.Int64,
    'target_vintage': pl.Int64,
    'source_code': pl.String,
    'target_code': pl.String,
    'link_type': pl.String,
    'source_file': pl.String,
}


def parse_concordance(raw, source_vintage, target_vintage, source_file):
    body = below_header(raw, (str(source_vintage), str(target_vintage), 'code'))
    source = column(body, str(source_vintage), 'code')
    target = column(body, str(target_vintage), 'code')
    pairs = body.select(
        *[
            pl.col(c).cast(pl.String).str.strip_chars().str.replace(r'\.0$', '').alias(name)
            for c, name in [(source, 'source_code'), (target, 'target_code')]
        ]
    ).filter(pl.any_horizontal(pl.all().is_not_null()))
    if (
        pairs.is_empty()
        or pairs.filter(
            pl.any_horizontal(
                [
                    pl.col(c).str.contains(r'^[0-9]{6}$').not_().fill_null(True)
                    for c in pairs.columns
                ]
            )
        ).height
    ):
        raise ValueError('invalid or incomplete concordance endpoint')
    pairs = pairs.unique().sort('source_code', 'target_code')
    outgoing = pl.col('target_code').n_unique().over('source_code').gt(1)
    incoming = pl.col('source_code').n_unique().over('target_code').gt(1)
    return pairs.with_columns(
        source_vintage=pl.lit(source_vintage, dtype=pl.Int64),
        target_vintage=pl.lit(target_vintage, dtype=pl.Int64),
        source_file=pl.lit(source_file),
        link_type=pl.when(outgoing.and_(incoming))
        .then(pl.lit('m:m'))
        .when(outgoing)
        .then(pl.lit('1:m'))
        .when(incoming)
        .then(pl.lit('m:1'))
        .otherwise(pl.lit('1:1')),
    ).select(list(RELATION_SCHEMA))


def validate_relationships(relations, structures):
    if relations.schema != RELATION_SCHEMA:
        raise ValueError('incompatible relationship schema')
    if (
        any(relations[c].null_count() for c in relations.columns)
        or relations.filter(pl.col('source_file').str.strip_chars().eq('')).height
    ):
        raise ValueError('null relationship field or empty provenance')
    if (
        relations.select('source_vintage', 'target_vintage', 'source_code', 'target_code')
        .is_duplicated()
        .any()
    ):
        raise ValueError('duplicate relationship pair')
    partition = ['source_vintage', 'target_vintage']
    outgoing = pl.col('target_code').n_unique().over([*partition, 'source_code']).gt(1)
    incoming = pl.col('source_code').n_unique().over([*partition, 'target_code']).gt(1)
    expected = (
        pl.when(outgoing.and_(incoming))
        .then(pl.lit('m:m'))
        .when(outgoing)
        .then(pl.lit('1:m'))
        .when(incoming)
        .then(pl.lit('m:1'))
        .otherwise(pl.lit('1:1'))
    )
    if relations.filter(pl.col('link_type').ne(expected)).height:
        raise ValueError('corrupt relationship degree classification')
    if set(relations.select('source_vintage', 'target_vintage').unique().iter_rows()) != set(
        zip(CHAIN, CHAIN[1:])
    ):
        raise ValueError('missing or extra vintage bridge')
    for source, target in zip(CHAIN, CHAIN[1:]):
        pair = relations.filter(
            pl.col('source_vintage').eq(source).and_(pl.col('target_vintage').eq(target))
        )
        for vintage, name in [(source, 'source_code'), (target, 'target_code')]:
            leaves = set(
                structures.filter(
                    pl.col('vintage').eq(vintage).and_(pl.col('level').eq('national_industry'))
                )['code'].to_list()
            )
            if not leaves or set(pair[name].to_list()) != leaves:
                raise ValueError(f'{vintage}: invalid endpoint or incomplete bridge coverage')


def candidates(relations, source_vintage, source_code, target_vintage):
    if source_vintage not in CHAIN or target_vintage not in CHAIN:
        raise ValueError('unsupported bridge vintage')
    codes = {source_code}
    start, stop = CHAIN.index(source_vintage), CHAIN.index(target_vintage)
    step = 1 if stop > start else -1
    for i in range(start, stop, step):
        a, b = CHAIN[i], CHAIN[i + step]
        source, target = min(a, b), max(a, b)
        pair = relations.filter(
            pl.col('source_vintage').eq(source).and_(pl.col('target_vintage').eq(target))
        )
        left, right = (
            ('source_code', 'target_code') if step == 1 else ('target_code', 'source_code')
        )
        if not codes.issubset(set(pair[left].to_list())):
            raise ValueError('missing bridge for supported candidate')
        codes = set(pair.filter(pl.col(left).is_in(sorted(codes)))[right].to_list())
    return sorted(codes)
