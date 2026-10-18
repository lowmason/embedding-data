'''Hand-calculated public-reference arithmetic, independent of production data.'''

from dataclasses import replace

import polars as pl
import pytest

pytest_plugins = ['acs_mapping_fixtures']


def test_work_group_uses_populations_not_mean_puma_shares(population_case):
    from embedding_data.acs_geography_factors import build_factor_tables

    group = build_factor_tables(population_case.evidence, population_case.selected).county.filter(
        pl.col('area_type').eq('work_migration').and_(pl.col('state_fips').eq('01'))
    )
    assert group['intersection_population'].to_list() == [60, 340]
    assert group['area_population'].to_list() == [400, 400]
    assert group['factor'].to_list() == pytest.approx([0.15, 0.85], abs=1e-12)


def test_directional_factors_and_full_non_msa_residual(population_case):
    from embedding_data.acs_geography_factors import build_factor_tables, validate_factor_tables

    factors = build_factor_tables(population_case.evidence, population_case.selected)
    validate_factor_tables(factors, population_case.evidence, population_case.selected)
    residence = factors.county.filter(pl.col('area_type').eq('residence'))
    assert residence['factor'].to_list() == pytest.approx([0.6, 0.4, 1, 1])
    assert factors.msa['puma_to_msa_factor'].to_list() == pytest.approx([0.6, 1])
    assert factors.msa['msa_to_puma_factor'].to_list() == pytest.approx([60 / 260, 200 / 260])
    assert factors.coverage['non_msa_population'].to_list() == [40, 300, 0]
    assert factors.coverage['non_msa_fraction'].to_list() == [0.4, 1, 0]


@pytest.mark.parametrize('field', ['intersections', 'puma_totals', 'county_totals'])
def test_missing_intersection_or_independent_control_fails(population_case, field):
    from embedding_data.acs_geography_factors import build_factor_tables

    frame = getattr(population_case.evidence, field)
    if field == 'intersections':
        frame = frame.filter(pl.col('intersection_population').ne(40))
    else:
        frame = frame.slice(1)
    evidence = replace(population_case.evidence, **{field: frame})
    with pytest.raises(ValueError, match='population|key|control|composition'):
        build_factor_tables(evidence, population_case.selected)


def test_split_county_refuses_union_and_preserves_source_evidence(population_case):
    from embedding_data.acs_geography_factors import build_factor_tables

    groups = population_case.evidence.puma_groups.with_columns(
        pl.when(pl.col('puma_code').eq('00200'))
        .then(pl.lit('00200'))
        .otherwise(pl.col('group_code'))
        .alias('group_code')
    )
    with pytest.raises(ValueError, match='V8') as caught:
        build_factor_tables(
            replace(population_case.evidence, puma_groups=groups), population_case.selected
        )
    assert caught.value.diagnostics['conflicting_memberships']
    assert 'reference_locators' in caught.value.diagnostics['conflicting_memberships'][0]


def test_tampered_integer_or_factor_is_rejected(population_case):
    from embedding_data.acs_geography_factors import build_factor_tables, validate_factor_tables

    factors = build_factor_tables(population_case.evidence, population_case.selected)
    for column, value in [('intersection_population', 1), ('factor', 0.5)]:
        altered = factors.county.with_columns(
            pl.lit(value).cast(factors.county.schema[column]).alias(column)
        )
        with pytest.raises(ValueError):
            validate_factor_tables(
                replace(factors, county=altered),
                population_case.evidence,
                population_case.selected,
            )


def test_retained_zero_intersection_is_not_an_absent_relation(population_case):
    from embedding_data.acs_geography_factors import build_factor_tables

    evidence = population_case.evidence
    row = evidence.intersections.row(0, named=True)
    row.update(
        puma_code='00200',
        intersection_population=0,
        published_area_factor=0.0,
        published_county_factor=0.0,
    )
    intersections = pl.concat(
        [evidence.intersections, pl.DataFrame([row], schema=evidence.intersections.schema)]
    ).sort('state_fips', 'puma_code', 'county_geoid')
    factors = build_factor_tables(
        replace(evidence, intersections=intersections), population_case.selected
    )
    zero = factors.county.filter(
        pl.col('area_type')
        .eq('residence')
        .and_(pl.col('area_code').eq('00200'))
        .and_(pl.col('county_geoid').eq('01001'))
    )
    assert zero['factor'].to_list() == [0.0]
    assert factors.diagnostics['relationships_including_zero'] == 6


def test_independent_county_composition_disagreement_is_refused(population_case):
    from embedding_data.acs_geography_factors import build_factor_tables

    evidence = population_case.evidence
    groups = evidence.county_groups.with_columns(
        pl.when(pl.col('county_geoid').eq('01003'))
        .then(pl.lit('00200'))
        .otherwise(pl.col('group_code'))
        .alias('group_code')
    )
    with pytest.raises(ValueError, match='V8'):
        build_factor_tables(replace(evidence, county_groups=groups), population_case.selected)


def test_duplicate_county_composition_preserves_diagnostic(population_case):
    from embedding_data.acs_geography_factors import build_factor_tables

    evidence = population_case.evidence
    duplicate = evidence.county_groups.head(1).with_columns(pl.lit('00200').alias('group_code'))
    with pytest.raises(ValueError) as caught:
        build_factor_tables(
            replace(
                evidence,
                county_groups=pl.concat([evidence.county_groups, duplicate]).sort(
                    'state_fips', 'county_geoid'
                ),
            ),
            population_case.selected,
        )
    assert caught.value.diagnostics['conflicting_memberships']


def test_absent_msa_coverage_cites_the_complete_original(population_case):
    from embedding_data.acs_geography_factors import build_factor_tables

    row = (
        build_factor_tables(population_case.evidence, population_case.selected)
        .coverage.filter(pl.col('puma_code').eq('00200'))
        .row(0, named=True)
    )
    assert any('msa_puma_2023_2020' in value for value in row['reference_ids'])


def test_micropolitan_node_cannot_be_used_as_msa(population_case):
    from embedding_data.acs_geography_factors import build_factor_tables

    msa = population_case.evidence.msa_intersections.with_columns(
        pl.lit('20000').alias('msa_code')
    )
    with pytest.raises(ValueError, match='metropolitan'):
        build_factor_tables(
            replace(population_case.evidence, msa_intersections=msa), population_case.selected
        )
