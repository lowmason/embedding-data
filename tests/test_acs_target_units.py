'''Complete native lookup identity, physical-area unions and selected node membership.'''

from dataclasses import replace

import polars as pl
import pytest
from acs_mapping_fixtures import forbid_external_access
from acs_target_fixtures import selected_target_fixture

from embedding_data.acs_mapping_contract import CODE_SCHEMA
from embedding_data.acs_target_contract import UNIT_SCHEMA, validate_auxiliary
from embedding_data.acs_target_units import build_units, observed_unit, puma_unit

@pytest.fixture(scope='module')
def selected(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patches:
        yield selected_target_fixture(tmp_path_factory.mktemp('unit-input'), patches)


def test_literal_unit_identifiers():
    assert observed_unit('soc', 'special') == (
        'acs_occupation_category',
        'feature:acs_occupation_category:special',
    )
    assert observed_unit('naics', 'a') == (
        'acs_industry_category',
        'feature:acs_industry_category:a',
    )
    assert puma_unit('residence', '01', '00100') == (
        'residence_puma',
        'geography:2020:residence_puma:0100100',
    )
    assert puma_unit('work_migration', '01', '00100') == (
        'work_migration_puma',
        'geography:2020:work_migration_puma:0100100',
    )


def test_authenticated_complete_registry_preserves_categories_and_unions_roles(
    selected, monkeypatch
):
    forbid_external_access(monkeypatch)
    units = build_units(selected)
    assert list(units.schema.items()) == list(UNIT_SCHEMA.items())
    validate_auxiliary('target_units', units)
    codes = pl.read_parquet(selected.tables['acs_code_lookup'])
    observed = units.filter(pl.col('kind').eq('observed_code'))
    reconstructed = observed.select([pl.col('code_' + n).alias(n) for n in CODE_SCHEMA])
    assert reconstructed.sort('code_lookup_id').equals(codes.sort('code_lookup_id'))
    special = observed.filter(pl.col('code_source_token').eq('559830'))
    assert special.height > 0
    assert special['code_canonical_scalar_node_id'].null_count() == special.height
    assert special['code_canonical_finest_candidates'].to_list() == [[]] * special.height
    areas = pl.read_parquet(selected.tables['acs_area_lookup']).filter(
        pl.col('area_status').eq('applicable')
    )
    for area in units.filter(pl.col('kind').eq('native_area')).iter_rows(named=True):
        records = areas.filter(
            pl.col('area_type').eq(area['area_type'])
            & pl.col('state_fips').eq(area['state_fips'])
            & pl.col('area_code').eq(area['area_code'])
        )
        assert area['roles'] == sorted(set(records['role']))
        assert area['area_lookup_ids'] == sorted(set(records['area_lookup_id']))
        assert area['factor_keys'] == sorted(set(records['factor_key']))
    assert units.filter(pl.col('roles').list.len().gt(1)).height > 0


def test_selected_nodes_are_exact_supported_leaves_counties_and_metropolitan_members(selected):
    units = build_units(selected)
    codes = pl.read_parquet(selected.tables['acs_code_lookup'])
    expected = set(codes['canonical_scalar_node_id'].drop_nulls())
    factors = pl.read_parquet(selected.tables['puma_county_factors']).filter(
        pl.col('area_type').eq('work_migration')
    )
    expected |= set(factors['county_node_id'])
    counties = pl.read_parquet(selected.upstream.geography['county_reference']).filter(
        pl.col('county_id').is_in(factors['county_node_id'].to_list())
    )
    expected |= set(counties.filter(pl.col('cbsa_type').eq('metropolitan'))['cbsa_id'])
    nodes = units.filter(pl.col('kind').eq('selected_node'))
    assert set(nodes['node_id']) == expected
    assert nodes.filter(pl.col('unit_type').eq('cbsa'))['cbsa_type'].to_list() == ['metropolitan']
    for system, unit_type, level, vintage in [
        ('naics', 'naics_national_industry', 'national_industry', 2022),
        ('soc', 'soc_detailed', 'detailed', 2018),
    ]:
        for node in nodes.filter(pl.col('unit_type').eq(unit_type)).iter_rows(named=True):
            assert (node['node_system'], node['node_level'], node['node_vintage']) == (
                system,
                level,
                vintage,
            )
    assert (
        nodes.filter(pl.col('unit_type').is_in(['county', 'cbsa']))['population_year'].to_list()
        == [2020] * nodes.filter(pl.col('unit_type').is_in(['county', 'cbsa'])).height
    )


def test_same_token_different_natural_keys_have_different_units(selected):
    units = build_units(selected).filter(pl.col('kind').eq('observed_code'))
    groups = units.group_by('code_system', 'code_source_token').agg(
        pl.col('unit').n_unique().alias('n')
    )
    assert groups.filter(pl.col('n').gt(1)).height > 0


@pytest.mark.parametrize('defect', ['path', 'node_level'])
def test_misaligned_candidate_or_unsupported_node_fails(selected, tmp_path, defect):
    if defect == 'path':
        table = pl.read_parquet(selected.tables['acs_code_lookup'])
        rows = table.to_dicts()
        row = next(r for r in rows if r['canonical_candidate_paths'])
        row['canonical_candidate_paths'][0][-1] = 'soc:2018:detailed:000000'
        file = tmp_path / 'codes.parquet'
        pl.DataFrame(rows, schema=table.schema).write_parquet(file)
        changed = replace(selected, tables=selected.tables | {'acs_code_lookup': file})
    else:
        file = tmp_path / 'nodes.parquet'
        table = pl.read_parquet(selected.upstream.codes['soc_nodes'])
        table.with_columns(
            pl.when(pl.col('level').eq('detailed'))
            .then(pl.lit('broad'))
            .otherwise(pl.col('level'))
            .alias('level')
        ).write_parquet(file)
        changed = replace(
            selected,
            upstream=replace(
                selected.upstream, codes=selected.upstream.codes | {'soc_nodes': file}
            ),
        )
    with pytest.raises(ValueError, match='candidate|path|node|frame'):
        build_units(changed)


def test_candidate_path_internal_order_must_follow_selected_edges(selected, tmp_path):
    table = pl.read_parquet(selected.tables['acs_code_lookup'])
    rows = table.to_dicts()
    row = next(
        r
        for r in rows
        if r['canonical_candidate_paths'] and len(r['canonical_candidate_paths'][0]) >= 3
    )
    path = row['canonical_candidate_paths'][0]
    path[0], path[1] = path[1], path[0]
    file = tmp_path / 'misordered-path.parquet'
    pl.DataFrame(rows, schema=table.schema).write_parquet(file)
    with pytest.raises(ValueError, match='path'):
        build_units(replace(selected, tables=selected.tables | {'acs_code_lookup': file}))


def test_all_selected_node_fields_are_verbatim_reference_records(selected):
    units = build_units(selected).filter(pl.col('kind').eq('selected_node'))
    references = pl.concat(
        [
            pl.read_parquet(selected.upstream.codes['naics_nodes']),
            pl.read_parquet(selected.upstream.codes['soc_nodes']),
            pl.read_parquet(selected.upstream.geography['geography_nodes']),
        ]
    )
    expected = references.filter(pl.col('node_id').is_in(units['node_id'].to_list())).sort(
        'node_id'
    )
    actual = units.select(
        [
            pl.col('node_id') if n == 'node_id' else pl.col('node_' + n).alias(n)
            for n in references.columns
        ]
    ).sort('node_id')
    assert actual.equals(expected)
