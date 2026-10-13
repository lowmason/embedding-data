import re

import polars as pl

from embedding_data.classification_tables import PATH_SCHEMA, naics_tables
from embedding_data.naics_relationships import candidates, validate_relationships

KEY_SCHEMA = {'naics_code': pl.String, 'naics_year': pl.Int64}
MAPPING_SCHEMA = {
    'naics_mapping_status': pl.String,
    'naics_matching_vintages': pl.List(pl.Int64),
    'naics_2022_candidates': pl.List(pl.String),
    'naics_2022_code': pl.String,
    'naics_2022_node_id': pl.String,
    'naics_deepest_common_node_id': pl.String,
    'flag_naics_crosswalked': pl.Boolean,
    'flag_naics_ambiguous': pl.Boolean,
    'flag_naics_unresolved': pl.Boolean,
}
LOOKUP_SCHEMA = {**KEY_SCHEMA, **MAPPING_SCHEMA}
SOURCE_VINTAGES = (2012, 2017, 2022)


def _validate_references(structures, relations, code_paths):
    rebuilt = []
    canonical_paths = None
    for vintage in (2002, 2007, *SOURCE_VINTAGES):
        titles = structures.filter(pl.col('vintage').eq(vintage)).select(
            'vintage', 'code', 'title'
        )
        nodes, _, paths = naics_tables(titles, vintage)
        rebuilt.append(nodes)
        if vintage == 2022:
            canonical_paths = paths
    if not pl.concat(rebuilt).sort('node_id').equals(structures.sort('node_id')):
        raise ValueError('incompatible native structures')
    if code_paths.schema != PATH_SCHEMA or not code_paths.sort('node_id').equals(canonical_paths):
        raise ValueError('missing or incompatible canonical path')
    validate_relationships(relations, structures)


def build_lookup(keys, structures, relations, code_paths):
    if keys.schema != KEY_SCHEMA or keys.is_duplicated().any():
        raise ValueError('incompatible or duplicate lookup key')
    _validate_references(structures, relations, code_paths)
    leaves = {
        vintage: set(
            structures.filter(
                pl.col('vintage').eq(vintage).and_(pl.col('level').eq('national_industry'))
            )['code'].to_list()
        )
        for vintage in SOURCE_VINTAGES
    }
    path_of = dict(code_paths.iter_rows())
    canonical_nodes = dict(
        structures.filter(pl.col('vintage').eq(2022).and_(pl.col('level').eq('national_industry')))
        .select('code', 'node_id')
        .iter_rows()
    )
    rows = []
    for code, vintage in keys.iter_rows():
        if vintage is not None and vintage not in SOURCE_VINTAGES:
            raise ValueError('incompatible nonnull NAICS vintage')
        if code is not None and not re.fullmatch(r'[0-9]{6}', code):
            raise ValueError('malformed source NAICS code')
        matching = [year for year in SOURCE_VINTAGES if code in leaves[year]]
        interpretations = []
        if code is None:
            status, unresolved = 'missing_code', False
        elif vintage is not None:
            if code not in leaves[vintage]:
                status, unresolved = 'invalid_native_code', True
            else:
                status = 'native_2022' if vintage == 2022 else 'concorded'
                unresolved, interpretations = False, [vintage]
        else:
            status = 'unknown_vintage_candidates' if matching else 'unknown_vintage_unmapped'
            unresolved, interpretations = True, matching
        possible = sorted(
            {
                target
                for year in interpretations
                for target in candidates(relations, year, code, 2022)
            }
        )
        scalar = possible[0] if vintage is not None and len(possible) == 1 else None
        common = None
        for group in zip(*(path_of[canonical_nodes[target]] for target in possible)):
            if len(set(group)) != 1:
                break
            common = group[0]
        rows.append(
            (
                code,
                vintage,
                status,
                matching,
                possible,
                scalar,
                canonical_nodes[scalar] if scalar else None,
                common,
                bool(possible) and any(year != 2022 for year in interpretations),
                len(possible) > 1,
                unresolved,
            )
        )
    return pl.DataFrame(rows, schema=LOOKUP_SCHEMA, orient='row').sort(
        'naics_code', 'naics_year', nulls_last=False
    )


def enrich(source, lookup):
    names = source.collect_schema().names()
    if '_code_row' in names or any(name in names for name in MAPPING_SCHEMA):
        raise ValueError('mapping output/temporary column collision')
    if lookup.schema != LOOKUP_SCHEMA or lookup.select(*KEY_SCHEMA).is_duplicated().any():
        raise ValueError('duplicate or incompatible mapping lookup')
    joined = source.with_row_index('_code_row').join(
        lookup.lazy(),
        on=list(KEY_SCHEMA),
        how='left',
        nulls_equal=True,
        validate='m:1',
        maintain_order='left',
    )
    if joined.select(pl.col('naics_mapping_status').is_null().any()).collect().item():
        raise ValueError('missing mapping lookup result')
    return joined.sort('_code_row').drop('_code_row').select(*names, *MAPPING_SCHEMA)
