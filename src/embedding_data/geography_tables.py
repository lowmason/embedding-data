import re
from collections import Counter, defaultdict

import polars as pl

from embedding_data.classification_tables import EDGE_SCHEMA, NODE_SCHEMA
from embedding_data.geography_parsers import EXCLUDED, SCOPE

COUNTY_SCHEMA = {c: pl.String for c in ['county_id', 'county_geoid', 'county_title']}
COUNTY_SCHEMA['county_vintage'] = pl.Int64
COUNTY_SCHEMA.update({c: pl.String for c in [
    'state_id', 'state_fips', 'state_usps', 'state_title', 'division_id', 'division_code',
    'division_title', 'region_id', 'region_code', 'region_title', 'cbsa_id', 'cbsa_code',
    'cbsa_type', 'cbsa_role']})
COUNTY_SCHEMA['cbsa_vintage'] = pl.Int64
CBSA_SCHEMA = {c: pl.String for c in ['cbsa_id', 'cbsa_code', 'cbsa_title', 'cbsa_type']}
CBSA_SCHEMA.update(cbsa_vintage=pl.Int64, n_counties=pl.Int64, state_fips=pl.List(pl.String))
SCHEMAS = {'geography_nodes': NODE_SCHEMA, 'geography_edges': EDGE_SCHEMA,
           'county_reference': COUNTY_SCHEMA, 'cbsa_reference': CBSA_SCHEMA}
EDGE_ENDPOINTS = {
    'county_state': (('county', 2025), ('state', 2025)),
    'state_division': (('state', 2025), ('division', 2025)),
    'division_region': (('division', 2025), ('region', 2025)),
    'county_cbsa': (('county', 2025), ('cbsa', 2023)),
}


def identifier(level, code):
    return f'geography:{2023 if level == "cbsa" else 2025}:{level}:{code}'


def validate_graph(nodes: pl.DataFrame, edges: pl.DataFrame) -> None:
    if nodes.schema != NODE_SCHEMA or edges.schema != EDGE_SCHEMA or nodes.is_empty():
        raise ValueError('incompatible or empty geography graph')
    if any(nodes[c].null_count() for c in nodes.columns) or any(
            edges[c].null_count() for c in edges.columns):
        raise ValueError('null graph field')
    if (nodes['node_id'].n_unique() != nodes.height or
            nodes.select('system', 'vintage', 'level', 'code').is_duplicated().any() or
            edges.is_duplicated().any()):
        raise ValueError('duplicate node or edge')
    records = {r['node_id']: r for r in nodes.iter_rows(named=True)}
    adjacency = defaultdict(list)
    for child, parent, kind in edges.rows():
        if child not in records or parent not in records:
            raise ValueError('missing graph endpoint')
        adjacency[child].append(parent)
    visited, active = set(), set()

    def visit(node):
        if node in active:
            raise ValueError('cycle in geography graph')
        if node in visited:
            return
        active.add(node)
        for parent in adjacency[node]:
            visit(parent)
        active.remove(node)
        visited.add(node)

    for node in records:
        visit(node)
    for node in records.values():
        width = {'region': 1, 'division': 1, 'state': 2, 'county': 5, 'cbsa': 5}.get(node['level'])
        if (width is None or node['system'] != 'geography' or
                node['vintage'] != (2023 if node['level'] == 'cbsa' else 2025) or
                not re.fullmatch(r'[0-9]{' + str(width) + '}', node['code']) or
                node['node_id'] != identifier(node['level'], node['code']) or
                not node['title'].strip()):
            raise ValueError('invalid namespaced geography node')
    degree = Counter()
    for child, parent, kind in edges.rows():
        a, b = records[child], records[parent]
        actual = ((a['level'], a['vintage']), (b['level'], b['vintage']))
        if EDGE_ENDPOINTS.get(kind) != actual:
            raise ValueError('unsupported edge type/endpoint levels or vintages')
        if kind == 'county_state' and a['code'][:2] != b['code']:
            raise ValueError('county administrative state contradicts its GEOID')
        degree[(child, kind)] += 1
    required = {'county': 'county_state', 'state': 'state_division', 'division': 'division_region'}
    for node, record in records.items():
        kind = required.get(record['level'])
        if kind and degree[(node, kind)] != 1:
            raise ValueError('missing or contradictory administrative parent')
        if degree[(node, 'county_cbsa')] > 1:
            raise ValueError('contradictory county-to-CBSA membership')


def assemble(sources: dict[str, pl.DataFrame]) -> dict[str, pl.DataFrame]:
    states = {r['state_fips']: r for r in sources['states'].iter_rows(named=True)}
    divisions = {r['division_code']: r for r in sources['divisions'].iter_rows(named=True)}
    regions = {r['region_code']: r for r in sources['regions'].iter_rows(named=True)}
    counties = sources['counties'].filter(pl.col('state_fips').is_in(list(states)))
    members = sources['members'].filter(pl.col('state_fips').is_in(list(states)))
    for frame in [sources['counties'], sources['members']]:
        unknown = set(frame['state_fips']) - set(states) - EXCLUDED
        if unknown or not set(states).issubset(SCOPE):
            raise ValueError('scoped county/membership state absent from state reference')
    if (counties['county_geoid'].n_unique() != counties.height or
            members['county_geoid'].n_unique() != members.height):
        raise ValueError('duplicate county or membership reference key')
    if not set(members['county_geoid']).issubset(set(counties['county_geoid'])):
        raise ValueError('member county is absent from the complete county frame')
    if counties.filter(pl.col('state_fips').eq('09').and_(
            pl.col('county_geoid').str.contains(r'^091[1-9]0$').not_())).height:
        raise ValueError('Connecticut frame must contain planning regions')
    by_county = {r['county_geoid']: r for r in members.iter_rows(named=True)}
    cbsa_members = defaultdict(list)
    for r in members.iter_rows(named=True):
        cbsa_members[r['cbsa_code']].append(r)
    node_rows, edge_rows, county_rows, cbsa_rows = [], [], [], []

    def node(level, value, name):
        node_rows.append((identifier(level, value), 'geography',
                          2023 if level == 'cbsa' else 2025, level, value, name))

    for r, item in regions.items():
        node('region', r, item['region_title'])
    for d, item in divisions.items():
        r = item['region_code']
        if r not in regions:
            raise ValueError('division region is absent')
        node('division', d, item['division_title'])
        edge_rows.append((identifier('division', d), identifier('region', r), 'division_region'))
    for s, item in states.items():
        d, r = item['division_code'], item['region_code']
        if d not in divisions or divisions[d]['region_code'] != r:
            raise ValueError('state division/region contradicts the reference')
        node('state', s, item['state_title'])
        edge_rows.append((identifier('state', s), identifier('division', d), 'state_division'))
    for item in counties.iter_rows(named=True):
        c, s = item['county_geoid'], item['state_fips']
        state = states[s]
        d, r = state['division_code'], state['region_code']
        membership = by_county.get(c)
        node('county', c, item['county_title'])
        edge_rows.append((identifier('county', c), identifier('state', s), 'county_state'))
        cbsa = membership['cbsa_code'] if membership else None
        if membership:
            edge_rows.append((identifier('county', c), identifier('cbsa', cbsa), 'county_cbsa'))
        county_rows.append((identifier('county', c), c, item['county_title'], 2025,
                            identifier('state', s), s, item['state_usps'], state['state_title'],
                            identifier('division', d), d, divisions[d]['division_title'],
                            identifier('region', r), r, regions[r]['region_title'],
                            identifier('cbsa', cbsa) if membership else None, cbsa,
                            membership['cbsa_type'] if membership else None,
                            membership['cbsa_role'] if membership else None,
                            2023 if membership else None))
    for c, items in cbsa_members.items():
        labels = {(r['cbsa_title'], r['cbsa_type']) for r in items}
        if len(labels) != 1:
            raise ValueError('contradictory CBSA title/type')
        name, kind = next(iter(labels))
        node('cbsa', c, name)
        cbsa_rows.append((identifier('cbsa', c), c, name, kind, 2023, len(items),
                          sorted({r['state_fips'] for r in items})))
    output = {
        'geography_nodes': pl.DataFrame(node_rows, schema=NODE_SCHEMA, orient='row').sort(
            'node_id'),
        'geography_edges': pl.DataFrame(edge_rows, schema=EDGE_SCHEMA, orient='row').sort(
            'child_id', 'parent_id', 'edge_type'),
        'county_reference': pl.DataFrame(county_rows, schema=COUNTY_SCHEMA, orient='row').sort(
            'county_geoid'),
        'cbsa_reference': pl.DataFrame(cbsa_rows, schema=CBSA_SCHEMA, orient='row').sort(
            'cbsa_code'),
    }
    validate_graph(output['geography_nodes'], output['geography_edges'])
    return output


def validate_tables(tables, sources) -> None:
    validate_graph(tables['geography_nodes'], tables['geography_edges'])
    expected = assemble(sources)
    for name, schema in SCHEMAS.items():
        if tables[name].schema != schema or not tables[name].equals(expected[name]):
            raise ValueError(f'{name}: exact source/graph/reference parity failed')
