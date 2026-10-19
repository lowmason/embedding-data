'''Build aggregate category and physical-area units from selected lookup/reference tables.'''

import polars as pl

from embedding_data.acs_mapping_contract import CODE_SCHEMA, validate_table
from embedding_data.acs_target_contract import (
    MSA_DELINEATION,
    SELECTED_NODE_FRAMES,
    UNIT_SCHEMA,
    validate_auxiliary,
)
from embedding_data.acs_target_inputs import SelectedTargets

def observed_unit(system: str, code_lookup_id: str) -> tuple[str, str]:
    kind = {'naics': 'acs_industry_category', 'soc': 'acs_occupation_category'}[system]
    return kind, f'feature:{kind}:{code_lookup_id}'


def puma_unit(area_type: str, state_fips: str, area_code: str) -> tuple[str, str]:
    kind = {'residence': 'residence_puma', 'work_migration': 'work_migration_puma'}[area_type]
    return kind, f'geography:2020:{kind}:{state_fips}{area_code}'


def _empty_unit(unit_type: str, unit: str, kind: str) -> dict:
    return {
        name: [] if isinstance(dtype, pl.List) else None for name, dtype in UNIT_SCHEMA.items()
    } | {'unit_type': unit_type, 'unit': unit, 'kind': kind}


def _union(row: dict, source: dict, names: tuple[str, ...]) -> dict:
    return {name: sorted(set(row[name]) | set(source[name])) for name in names}


def _node_index(table: pl.DataFrame) -> dict:
    if table['node_id'].n_unique() != table.height:
        raise ValueError('duplicate selected node identity')
    return {r['node_id']: r for r in table.iter_rows(named=True)}


def _selected_node(nodes: dict, node_id: str, unit_type: str) -> dict:
    if node_id not in nodes:
        raise ValueError('missing selected node')
    node = nodes[node_id]
    if (node['system'], node['vintage'], node['level']) != SELECTED_NODE_FRAMES[unit_type]:
        raise ValueError('selected node contradicts frozen frame')
    row = _empty_unit(unit_type, node_id, 'selected_node')
    row.update(
        {
            ('node_id' if name == 'node_id' else 'node_' + name): value
            for name, value in node.items()
        }
    )
    if unit_type in {'county', 'cbsa'}:
        row.update(
            population_year=2020,
            puma_vintage=2020,
            county_composition_year=2022,
            county_inventory_vintage=2025,
        )
    if unit_type == 'cbsa':
        row['msa_delineation'] = MSA_DELINEATION
    return row


def build_units(selected: SelectedTargets) -> pl.DataFrame:
    '''Preserve complete code records and coalesce only identical physical PUMA identities.'''
    codes = pl.read_parquet(selected.tables['acs_code_lookup'])
    areas = pl.read_parquet(selected.tables['acs_area_lookup'])
    factors = pl.read_parquet(selected.tables['puma_county_factors'])
    for kind, table in [('code', codes), ('area', areas), ('county_factor', factors)]:
        validate_table(kind, table)
    code_nodes = {
        system: _node_index(pl.read_parquet(selected.upstream.codes[system + '_nodes']))
        for system in ('naics', 'soc')
    }
    paths = pl.read_parquet(selected.upstream.codes['code_paths'])
    if paths['node_id'].n_unique() != paths.height:
        raise ValueError('duplicate selected candidate path')
    path_index = dict(paths.iter_rows())
    geography_nodes = _node_index(pl.read_parquet(selected.upstream.geography['geography_nodes']))
    counties = pl.read_parquet(selected.upstream.geography['county_reference'])
    cbsas = pl.read_parquet(selected.upstream.geography['cbsa_reference'])
    if (
        counties['county_id'].n_unique() != counties.height
        or cbsas['cbsa_id'].n_unique() != cbsas.height
    ):
        raise ValueError('duplicate selected geographic membership')
    county_index = {r['county_id']: r for r in counties.iter_rows(named=True)}
    cbsa_index = {r['cbsa_id']: r for r in cbsas.iter_rows(named=True)}
    rows, native, nodes = [], {}, {}
    for code in codes.iter_rows(named=True):
        unit_type, unit = observed_unit(code['system'], code['code_lookup_id'])
        row = _empty_unit(unit_type, unit, 'observed_code')
        row.update({'code_' + name: code[name] for name in CODE_SCHEMA})
        row.update(
            reference_ids=code['reference_ids'], reference_locators=code['reference_locators']
        )
        rows.append(row)
        for candidate, path in zip(
            code['canonical_finest_candidates'], code['canonical_candidate_paths'], strict=True
        ):
            leaf_type = {'naics': 'naics_national_industry', 'soc': 'soc_detailed'}[code['system']]
            leaf = _selected_node(code_nodes[code['system']], path[-1], leaf_type)
            if path_index.get(path[-1]) != path:
                raise ValueError('candidate path differs from selected root-to-leaf path')
            if leaf['node_code'] != candidate:
                raise ValueError('misaligned candidate path')
            if any(node_id not in code_nodes[code['system']] for node_id in path):
                raise ValueError('candidate path has missing selected node')
        scalar = code['canonical_scalar_node_id']
        if scalar is not None:
            kind = {'naics': 'naics_national_industry', 'soc': 'soc_detailed'}[code['system']]
            node = nodes.setdefault(
                scalar, _selected_node(code_nodes[code['system']], scalar, kind)
            )
            node.update(_union(node, code, ('reference_ids', 'reference_locators')))
    for area in areas.filter(pl.col('area_status').eq('applicable')).iter_rows(named=True):
        unit_type, unit = puma_unit(area['area_type'], area['state_fips'], area['area_code'])
        row = native.setdefault(unit, _empty_unit(unit_type, unit, 'native_area'))
        identity = {
            name: area[name] for name in ('area_type', 'state_fips', 'area_code', 'puma_vintage')
        }
        if row['area_type'] is not None and any(
            row[name] != value for name, value in identity.items()
        ):
            raise ValueError('conflicting physical area identity')
        row.update(identity)
        row.update(_union(
            row,
            {
                'roles': [area['role']],
                'area_lookup_ids': [area['area_lookup_id']],
                'factor_keys': [area['factor_key']],
                'reference_ids': area['reference_ids'],
                'reference_locators': area['reference_locators'],
            },
            ('roles', 'area_lookup_ids', 'factor_keys', 'reference_ids', 'reference_locators'),
        ))
    for factor in factors.filter(pl.col('area_type').eq('work_migration')).iter_rows(named=True):
        county_id = factor['county_node_id']
        if county_id not in county_index:
            raise ValueError('factor county missing selected membership')
        county = county_index[county_id]
        if county['county_geoid'] != factor['county_geoid']:
            raise ValueError('factor county contradicts selected membership')
        row = nodes.setdefault(county_id, _selected_node(geography_nodes, county_id, 'county'))
        row.update(_union(row, factor, ('reference_ids', 'reference_locators')))
        if county['cbsa_type'] == 'metropolitan':
            cbsa_id = county['cbsa_id']
            if cbsa_id not in cbsa_index or cbsa_index[cbsa_id]['cbsa_type'] != 'metropolitan':
                raise ValueError('county CBSA contradicts selected metropolitan membership')
            cbsa = nodes.setdefault(cbsa_id, _selected_node(geography_nodes, cbsa_id, 'cbsa'))
            cbsa['cbsa_type'] = 'metropolitan'
            cbsa.update(_union(cbsa, factor, ('reference_ids', 'reference_locators')))
    result = pl.DataFrame([*rows, *native.values(), *nodes.values()], schema=UNIT_SCHEMA).sort(
        'unit_type', 'unit', nulls_last=False
    )
    validate_auxiliary('target_units', result)
    return result
