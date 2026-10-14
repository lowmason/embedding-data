import polars as pl
import pytest
from geography_fixtures import source_frames

from embedding_data import geography_tables as gt

def test_both_paths_full_inventory_and_cross_state_cbsa(tmp_path):
    sources = source_frames(tmp_path)
    tables = gt.assemble(sources)
    gt.validate_tables(tables, sources)
    assert {k: f.schema for k, f in tables.items()} == gt.SCHEMAS
    counties = tables['county_reference']
    assert counties['county_geoid'].to_list() == ['01001', '09110', '51001', '51510']
    assert tables['geography_nodes'].height == 14
    assert tables['geography_edges'].height == 13
    assert counties.filter(pl.col('county_geoid').eq('51001')).select(
        'cbsa_id', 'cbsa_code', 'cbsa_type', 'cbsa_role', 'cbsa_vintage').null_count().row(0) == (
            1, 1, 1, 1, 1)
    metro = tables['cbsa_reference'].filter(pl.col('cbsa_code').eq('10000')).row(0, named=True)
    assert metro['state_fips'] == ['01', '51']
    assert metro['n_counties'] == 2
    assert metro['cbsa_type'] == 'metropolitan'
    assert tables['cbsa_reference'].filter(pl.col('cbsa_code').eq('20000')).item(
        0, 'cbsa_type') == 'micropolitan'
    edges = set(tables['geography_edges'].rows())
    assert ('geography:2025:county:51510', 'geography:2025:state:51', 'county_state') in edges
    assert ('geography:2025:county:51510', 'geography:2023:cbsa:10000', 'county_cbsa') in edges
    assert not any('72001' in child or kind == 'cbsa_state' for child, parent, kind in edges)
    assert {'geography:2025:region:1', 'geography:2025:division:1'}.issubset(
        set(tables['geography_nodes']['node_id']))


@pytest.mark.parametrize('name', ['geography_nodes', 'geography_edges',
                                  'county_reference', 'cbsa_reference'])
def test_output_reference_parity_is_checked(tmp_path, name):
    sources = source_frames(tmp_path)
    tables = gt.assemble(sources)
    tables[name] = tables[name].slice(1)
    with pytest.raises(ValueError):
        gt.validate_tables(tables, sources)


def test_membership_join_failure_is_not_a_non_cbsa_county(tmp_path):
    sources = source_frames(tmp_path)
    sources['members'] = sources['members'].with_columns(
        pl.when(pl.col('county_geoid').eq('01001')).then(pl.lit('01003'))
        .otherwise(pl.col('county_geoid')).alias('county_geoid'))
    with pytest.raises(ValueError, match='member county'):
        gt.assemble(sources)


def test_orphan_duplicate_parent_wrong_id_and_cycle_fail(tmp_path):
    tables = gt.assemble(source_frames(tmp_path))
    nodes, edges = tables['geography_nodes'], tables['geography_edges']
    county_edge = edges.filter(pl.col('edge_type').eq('county_state')).head(1)
    for invalid in [pl.concat([edges, county_edge]),
                    pl.concat([edges, county_edge.with_columns(
                        pl.lit('geography:2025:state:51').alias('parent_id'))]),
                    edges.with_columns(pl.lit('missing').alias('parent_id')),
                    pl.concat([edges, pl.DataFrame(
                        [('geography:2025:state:01', 'geography:2025:county:01001',
                          'state_division')], schema=gt.EDGE_SCHEMA, orient='row')]),
                    edges.filter(pl.col('child_id').ne('geography:2025:county:01001'))]:
        with pytest.raises(ValueError):
            gt.validate_graph(nodes, invalid)
    with pytest.raises(ValueError):
        gt.validate_graph(nodes.with_columns(pl.lit('bad').alias('node_id')), edges)


def test_admin_parent_is_not_a_cbsa_parent_and_titles_must_agree(tmp_path):
    sources = source_frames(tmp_path)
    tables = gt.assemble(sources)
    bad_edge = pl.DataFrame([('geography:2023:cbsa:10000', 'geography:2025:state:01',
                             'county_state')], schema=gt.EDGE_SCHEMA, orient='row')
    with pytest.raises(ValueError):
        gt.validate_graph(
            tables['geography_nodes'], pl.concat([tables['geography_edges'], bad_edge]))
    tables['county_reference'] = tables['county_reference'].with_columns(
        pl.lit('wrong official title').alias('state_title'))
    with pytest.raises(ValueError):
        gt.validate_tables(tables, sources)
