'''Conserved population allocation factors; no inferred individual locations.'''

from dataclasses import dataclass

import polars as pl

from embedding_data import geography_tables as gt
from embedding_data import target_io
from embedding_data.acs_area_references import (
    GROUP_KEY,
    PUMA_KEY,
    AreaEvidence,
    CompositionConflict,
    validate_area_evidence,
)
from embedding_data.acs_mapping_contract import (
    COUNTY_FACTOR_SCHEMA,
    MSA_COVERAGE_SCHEMA,
    MSA_FACTOR_SCHEMA,
    NATURAL_KEYS,
    factor_key,
    validate_table,
)
from embedding_data.acs_mapping_inputs import SelectedInputs
from embedding_data.acs_mapping_io import safe_path

CLOSURE_TOLERANCE = 1e-12
FRAMES = dict(population_year=2020, puma_vintage=2020, county_inventory_vintage=2025)


@dataclass(frozen=True)
class FactorTables:
    county: pl.DataFrame
    msa: pl.DataFrame
    coverage: pl.DataFrame
    diagnostics: dict


def _references(*rows):
    return {
        name: sorted({value for row in rows for value in row[name]})
        for name in ('reference_ids', 'reference_locators')
    }


def _geography(selected):
    tables = {}
    for name in ('county_reference', 'cbsa_reference', 'geography_nodes', 'geography_edges'):
        file = selected.geography[name]
        safe_path(file)
        expected = selected.provenance['geography']['tables'][name]
        actual = target_io.file_record(file)
        if actual != expected:
            raise ValueError('selected geographic table differs from pinned record')
        table = pl.read_parquet(file)
        if table.schema != gt.SCHEMAS[name]:
            raise ValueError('selected geographic table schema differs')
        tables[name] = table
    gt.validate_graph(tables['geography_nodes'], tables['geography_edges'])
    return tables


def _validate_composition(evidence):
    groups = {
        (r['state_fips'], r['puma_code']): r for r in evidence.puma_groups.iter_rows(named=True)
    }
    county_groups = {r['county_geoid']: r for r in evidence.county_groups.iter_rows(named=True)}
    memberships = {}
    conflicts = []
    for row in evidence.intersections.iter_rows(named=True):
        group = groups[(row['state_fips'], row['puma_code'])]
        county = county_groups[row['county_geoid']]
        identity = tuple(group[k] for k in GROUP_KEY)
        memberships.setdefault(row['county_geoid'], set()).add(identity)
        if identity != tuple(county[k] for k in GROUP_KEY):
            conflicts.append(
                {
                    **row,
                    'puma_group': list(identity),
                    'county_group': [county[k] for k in GROUP_KEY],
                    **_references(row, group, county),
                }
            )
    if conflicts:
        raise CompositionConflict(
            {
                'conflicting_memberships': conflicts,
                'split_counties': sorted(k for k, v in memberships.items() if len(v) > 1),
                'includes_zero_population_relations': True,
                'v8_adopted': False,
            }
        )
    puma_totals = {
        (r['state_fips'], r['puma_code']): r['population']
        for r in evidence.puma_totals.iter_rows(named=True)
    }
    county_totals = dict(evidence.county_totals.select('county_geoid', 'population').iter_rows())
    by_puma, by_county = {}, {}
    for key, row in groups.items():
        group = tuple(row[k] for k in GROUP_KEY)
        by_puma[group] = by_puma.get(group, 0) + puma_totals[key]
    for key, row in county_groups.items():
        group = tuple(row[k] for k in GROUP_KEY)
        by_county[group] = by_county.get(group, 0) + county_totals[key]
    if by_puma != by_county:
        raise CompositionConflict(
            {
                'conflicting_memberships': [],
                'group_population_totals_disagree': True,
                'v8_adopted': False,
            }
        )
    return {
        'v8_composition_reconciled': True,
        'v8_adopted': False,
        'relationships_including_zero': evidence.intersections.height,
        'group_count': len(by_puma),
    }


def work_group_populations(intersections, puma_groups, puma_totals) -> pl.DataFrame:
    '''Sum integer persons before dividing, never average constituent PUMA shares.'''
    numerators = (
        intersections.join(puma_groups, on=PUMA_KEY, validate='m:1')
        .group_by(*GROUP_KEY, 'county_geoid')
        .agg(pl.col('intersection_population').sum())
    )
    denominators = (
        puma_groups.join(puma_totals, on=PUMA_KEY, validate='1:1')
        .group_by(GROUP_KEY)
        .agg(pl.col('population').sum().alias('area_population'))
    )
    return numerators.join(denominators, on=GROUP_KEY, validate='m:1').with_columns(
        pl.col('intersection_population')
        .cast(pl.Float64)
        .truediv(pl.col('area_population'))
        .alias('factor')
    )


def _county_rows(evidence, counties):
    pumas = {
        (r['state_fips'], r['puma_code']): r for r in evidence.puma_totals.iter_rows(named=True)
    }
    controls = {r['county_geoid']: r for r in evidence.county_totals.iter_rows(named=True)}
    rows = []
    for row in evidence.intersections.iter_rows(named=True):
        if row['state_fips'] not in evidence.scope_states:
            continue
        state, code, county = row['state_fips'], row['puma_code'], row['county_geoid']
        if county not in counties:
            raise ValueError('scoped population county absent from selected Stage 5 inventory')
        total = pumas[(state, code)]
        rows.append(
            dict(
                factor_key=factor_key('residence', state, code),
                area_type='residence',
                state_fips=state,
                area_code=code,
                county_geoid=county,
                county_node_id=counties[county]['county_id'],
                intersection_population=row['intersection_population'],
                area_population=total['population'],
                county_population=controls[county]['population'],
                factor=row['intersection_population'] / total['population'],
                published_area_factor=row['published_area_factor'],
                published_county_factor=row['published_county_factor'],
                county_composition_year=2022,
                **FRAMES,
                flag_geographic_allocation=True,
                flag_fractional_split=row['intersection_population'] != total['population'],
                **_references(row, total, controls[county]),
            )
        )
    group_rows = work_group_populations(
        evidence.intersections, evidence.puma_groups, evidence.puma_totals
    )
    groups = {
        (r['state_fips'], r['puma_code']): r for r in evidence.puma_groups.iter_rows(named=True)
    }
    source_rows = {}
    denominator_sources = {}
    for key, group in groups.items():
        identity = tuple(group[k] for k in GROUP_KEY)
        denominator_sources.setdefault(identity, []).extend([group, pumas[key]])
    for row in evidence.intersections.iter_rows(named=True):
        group = groups[(row['state_fips'], row['puma_code'])]
        key = (*[group[k] for k in GROUP_KEY], row['county_geoid'])
        source_rows.setdefault(key, []).extend(
            [row, group, pumas[(row['state_fips'], row['puma_code'])]]
        )
    county_groups = {r['county_geoid']: r for r in evidence.county_groups.iter_rows(named=True)}
    for row in group_rows.iter_rows(named=True):
        state, code, county = row['group_state_fips'], row['group_code'], row['county_geoid']
        if state not in evidence.scope_states:
            continue
        if county not in counties:
            raise ValueError('work/migration county absent from selected Stage 5 inventory')
        rows.append(
            dict(
                factor_key=factor_key('work_migration', state, code),
                area_type='work_migration',
                state_fips=state,
                area_code=code,
                county_geoid=county,
                county_node_id=counties[county]['county_id'],
                intersection_population=row['intersection_population'],
                area_population=row['area_population'],
                county_population=controls[county]['population'],
                factor=row['factor'],
                published_area_factor=None,
                published_county_factor=None,
                county_composition_year=2022,
                **FRAMES,
                flag_geographic_allocation=True,
                flag_fractional_split=row['intersection_population'] != row['area_population'],
                **_references(
                    *source_rows[(state, code, county)],
                    *denominator_sources[(state, code)],
                    county_groups[county],
                    controls[county],
                ),
            )
        )
    return rows


def _msa_rows(evidence, cbsas):
    rows, coverage, population = [], [], {}
    provenance = {}
    for row in evidence.msa_intersections.iter_rows(named=True):
        if row['state_fips'] not in evidence.scope_states:
            continue
        msa = cbsas.get(row['msa_code'])
        if msa is None or msa['cbsa_type'] != 'metropolitan':
            raise ValueError('scoped MSA must be a typed metropolitan Stage 5 node')
        key = row['state_fips'], row['puma_code']
        population[key] = population.get(key, 0) + row['intersection_population']
        provenance.setdefault(key, []).append(row)
        rows.append(
            dict(
                **row,
                msa_node_id=msa['cbsa_id'],
                puma_to_msa_factor=row['intersection_population'] / row['puma_population'],
                msa_to_puma_factor=row['intersection_population'] / row['msa_population'],
                **FRAMES,
                msa_delineation='July 2023',
                flag_geographic_allocation=True,
                flag_fractional_split=row['intersection_population'] != row['puma_population'],
            )
        )
    for total in evidence.puma_totals.iter_rows(named=True):
        state, code = total['state_fips'], total['puma_code']
        if state not in evidence.scope_states:
            continue
        whole = total['population']
        allocated = population.get((state, code), 0)
        coverage.append(
            dict(
                state_fips=state,
                puma_code=code,
                puma_population=whole,
                msa_population=allocated,
                non_msa_population=whole - allocated,
                msa_fraction=allocated / whole,
                non_msa_fraction=(whole - allocated) / whole,
                population_year=2020,
                puma_vintage=2020,
                msa_delineation='July 2023',
                **_references(
                    total,
                    *provenance.get((state, code), []),
                    {
                        'reference_ids': [
                            evidence.reference_provenance['reference_id'] + ':msa_puma_2023_2020'
                        ],
                        'reference_locators': ['msa_puma_2023_2020:complete-original'],
                    },
                ),
            )
        )
    return rows, coverage


def _derive(evidence, selected):
    validate_area_evidence(evidence)
    diagnostics = _validate_composition(evidence)
    geography = _geography(selected)
    counties = {r['county_geoid']: r for r in geography['county_reference'].iter_rows(named=True)}
    cbsas = {r['cbsa_code']: r for r in geography['cbsa_reference'].iter_rows(named=True)}
    county_rows = _county_rows(evidence, counties)
    msa_rows, coverage_rows = _msa_rows(evidence, cbsas)
    frames = []
    for rows, schema, kind in [
        (county_rows, COUNTY_FACTOR_SCHEMA, 'county_factor'),
        (msa_rows, MSA_FACTOR_SCHEMA, 'msa_factor'),
        (coverage_rows, MSA_COVERAGE_SCHEMA, 'msa_coverage'),
    ]:
        frame = pl.DataFrame(rows, schema=schema).sort(NATURAL_KEYS[kind], nulls_last=False)
        validate_table(kind, frame)
        frames.append(frame)
    diagnostics.update(
        population_year=2020,
        puma_vintage=2020,
        county_composition_year=2022,
        county_inventory_vintage=2025,
        msa_delineation='July 2023',
        excluded_states=evidence.reference_provenance['excluded_states'],
        rejected_geocorr_rounding_assertions=evidence.reference_provenance.get(
            'rejected_geocorr_rounding_assertions', []),
        published_factor_rounding_bound=0.00005 + CLOSURE_TOLERANCE,
        published_percent_scale='0-100',
        closure_tolerance=CLOSURE_TOLERANCE,
        absent_relation_is_zero_population_relation=False,
        interpretation='Separate population allocation factors; no joint probability or '
        'individual location claim. Micropolitan counties contribute to non-MSA residuals.',
    )
    return FactorTables(*frames, diagnostics)


def build_factor_tables(evidence: AreaEvidence, selected: SelectedInputs) -> FactorTables:
    factors = _derive(evidence, selected)
    _validate_closure(factors)
    return factors


def _validate_closure(factors):
    for group in factors.county.partition_by('factor_key'):
        if abs(sum(group['factor']) - 1) > CLOSURE_TOLERANCE:
            raise ValueError('county factor closure differs')
    for group in factors.msa.partition_by('msa_code'):
        if abs(sum(group['msa_to_puma_factor']) - 1) > CLOSURE_TOLERANCE:
            raise ValueError('MSA reverse factor closure differs')
    for row in factors.coverage.iter_rows(named=True):
        if abs(row['msa_fraction'] + row['non_msa_fraction'] - 1) > CLOSURE_TOLERANCE:
            raise ValueError('MSA coverage fractions do not close')


def validate_factor_tables(
    factors: FactorTables, evidence: AreaEvidence, selected: SelectedInputs
) -> None:
    '''Reconstruct integer numerators, denominators and every annotation from evidence.'''
    expected = _derive(evidence, selected)
    for kind, actual, rebuilt in [
        ('county_factor', factors.county, expected.county),
        ('msa_factor', factors.msa, expected.msa),
        ('msa_coverage', factors.coverage, expected.coverage),
    ]:
        validate_table(kind, actual)
        if not actual.equals(rebuilt):
            raise ValueError(f'{kind}: differs from integer reference reconstruction')
    if factors.diagnostics != expected.diagnostics:
        raise ValueError('factor diagnostics differ from reference reconstruction')
    _validate_closure(factors)
