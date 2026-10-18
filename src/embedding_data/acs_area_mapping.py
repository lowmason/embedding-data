'''Separate residence, workplace and migration interpretations of delivered ACS keys.'''

import math
import re

import polars as pl

from embedding_data.acs_area_references import (
    ROLE_COLUMNS,
    ROLE_RULE_SCHEMA,
    AreaEvidence,
    validate_area_evidence,
)
from embedding_data.acs_code_mapping import scheme_for, source_sample_mapping
from embedding_data.acs_geography_factors import FactorTables
from embedding_data.acs_mapping_contract import (
    AREA_RULE_VERSION,
    AREA_SCHEMA,
    NATURAL_KEYS,
    SourceInput,
    factor_key,
    lookup_id,
    validate_table,
)

AREA_KEY = list(NATURAL_KEYS['area'])
OBSERVED_AREA_SCHEMA = {**{k: AREA_SCHEMA[k] for k in AREA_KEY}, 'rows': pl.UInt64}
CLOSURE_TOLERANCE = 1e-12
FACTOR_FRAMES = dict(population_year=2020, puma_vintage=2020,
                     county_composition_year=2022, county_inventory_vintage=2025)

def normalized_role_code(value: str | None, width: int) -> str:
    '''Validate the documented role width before constructing a separate lookup key.'''
    if not isinstance(value, str) or not re.fullmatch('[0-9]{1,' + str(width) + '}', value):
        raise ValueError('unparseable or unavailable geographic role code')
    return value.zfill(width)

def observed_area_keys(sources: dict[str, SourceInput]) -> pl.DataFrame:
    '''Collect distinct keys and counts per role without materializing person rows.'''
    records = []
    for source in sources.values():
        samples = source_sample_mapping(source)
        scan = pl.scan_parquet(source.parquet)
        schema = scan.collect_schema()
        five = source.profile.removeprefix('acs/') == 'five_year'
        required = {'YEAR', 'SAMPLE', *(c for pair in ROLE_COLUMNS.values() for c in pair[:2])}
        if five:
            required.add('MULTYEAR')
        if not required.issubset(schema):
            raise ValueError('missing source role or sample identity columns')
        for role, (state, area, width) in ROLE_COLUMNS.items():
            if any(schema[c] != pl.String and not schema[c].is_integer() for c in [state, area]):
                raise ValueError('role source requires original integer or String code type')
            grouped = scan.select(
                pl.col('SAMPLE').cast(pl.String).alias('sample'),
                pl.col('YEAR').cast(pl.Int64).alias('release_year'),
                (pl.col('MULTYEAR')
                 if five else pl.col('YEAR')).cast(pl.Int64).alias('component_year'),
                pl.col(state).cast(pl.String).alias('source_state_code'),
                pl.col(area).cast(pl.String).alias('source_area_code'),
            ).group_by(pl.all()).agg(pl.len().cast(pl.UInt64).alias('rows')).collect()
            for row in grouped.iter_rows(named=True):
                sample = samples.get(row.pop('sample'))
                if sample is None:
                    raise ValueError('observed SAMPLE lacks selected DDI identity')
                scheme_for(source.profile, sample, row['release_year'], row['component_year'])
                normalized_role_code(row['source_state_code'], width)
                normalized_role_code(row['source_area_code'], 5)
                records.append(dict(profile=source.profile, sample_id=sample, role=role, **row))
    frame = pl.DataFrame(records, schema=OBSERVED_AREA_SCHEMA)
    if frame.select(AREA_KEY).is_duplicated().any():
        frame = frame.group_by(AREA_KEY).agg(pl.col('rows').sum())
    return frame.select(list(OBSERVED_AREA_SCHEMA)).sort(AREA_KEY, nulls_last=False)

def _validate_observed(observed):
    if observed.schema != OBSERVED_AREA_SCHEMA:
        raise ValueError('observed area schema differs')
    if observed.select(AREA_KEY).is_duplicated().any() or observed['rows'].null_count():
        raise ValueError('duplicate observed area keys or absent source counts')
    if observed.filter(pl.col('rows').eq(0)).height:
        raise ValueError('observed keys must have positive source counts')

def require_factor_coverage(applicable: pl.DataFrame, county_factors: pl.DataFrame) -> None:
    '''Require complete exact integer controls as well as floating factor closure.'''
    validate_table('county_factor', county_factors)
    if county_factors.filter(pl.any_horizontal(
            pl.col(name).ne(value) for name, value in FACTOR_FRAMES.items())).height:
        raise ValueError('factor geographic reference frames differ')
    totals = county_factors.group_by('factor_key').agg(pl.col('factor').sum().alias('factor_sum'))
    joined = applicable.select('factor_key').unique().join(
        totals, on='factor_key', how='left', validate='1:1'
    )
    if joined.filter(
        pl.col('factor_sum').is_null().or_(
            pl.col('factor_sum').sub(1.0).abs().gt(CLOSURE_TOLERANCE)
        )
    ).height:
        raise ValueError('applicable area has missing or incomplete county factors')
    for group in county_factors.partition_by('factor_key'):
        population = group['area_population'].unique().to_list()
        if (
            len(population) != 1 or population[0] <= 0
            or sum(group['intersection_population']) != population[0]
        ):
            raise ValueError('exact area integer population control differs')
        positive_support = sum(n > 0 for n in group['intersection_population'])
        for row in group.iter_rows(named=True):
            numerator = row['intersection_population']
            exact_factor = numerator / population[0]
            split = numerator != population[0]
            if (numerator < 0 or row['county_population'] <= 0
                    or not math.isfinite(row['factor']) or row['factor'] != exact_factor
                    or not row['flag_geographic_allocation']
                    or row['flag_fractional_split'] != split
                    or (positive_support > 1 and numerator > 0 and not split)):
                raise ValueError('factor contradicts integer populations or allocation provenance')
    for area_type in county_factors['area_type'].unique():
        for group in county_factors.filter(pl.col('area_type').eq(area_type)).partition_by(
            'county_geoid'
        ):
            populations = group['county_population'].unique().to_list()
            if len(populations) != 1 or sum(group['intersection_population']) != populations[0]:
                raise ValueError('exact county integer population control differs')

def _verify_evidence_factors(evidence, factors):
    '''Compare complete scoped original relations, including explicit zero intersections.'''
    validate_area_evidence(evidence)
    pumas = {
        (r['state_fips'], r['puma_code']): r['population']
        for r in evidence.puma_totals.iter_rows(named=True)
    }
    county_controls = {
        r['county_geoid']: r['population']
        for r in evidence.county_totals.iter_rows(named=True)
    }
    groups = {
        (r['state_fips'], r['puma_code']): (r['group_state_fips'], r['group_code'])
        for r in evidence.puma_groups.iter_rows(named=True)
    }
    county_groups = {
        r['county_geoid']: (r['group_state_fips'], r['group_code'])
        for r in evidence.county_groups.iter_rows(named=True)
    }
    expected, work, work_totals = {}, {}, {}
    for key, pop in pumas.items():
        group = groups[key]
        work_totals[group] = work_totals.get(group, 0) + pop
    for row in evidence.intersections.iter_rows(named=True):
        key = row['state_fips'], row['puma_code']
        group = groups[key]
        county = row['county_geoid']
        if county_groups[county] != group:
            raise ValueError('incompatible county/group composition')
        if row['state_fips'] in evidence.scope_states:
            expected[('residence', *key, county)] = (
                row['intersection_population'], pumas[key], county_controls[county]
            )
        work_key = *group, county
        work[work_key] = work.get(work_key, 0) + row['intersection_population']
    for (state, code, county), pop in work.items():
        if state in evidence.scope_states:
            expected[('work_migration', state, code, county)] = (
                pop, work_totals[(state, code)], county_controls[county]
            )
    actual = {
        (r['area_type'], r['state_fips'], r['area_code'], r['county_geoid']): (
            r['intersection_population'], r['area_population'], r['county_population']
        )
        for r in factors.county.iter_rows(named=True)
    }
    if actual != expected:
        raise ValueError('county factors differ from complete original integer relations')

def _interpret(row, rules):
    role = row['role']
    if role not in ROLE_COLUMNS:
        raise ValueError('unsupported geographic role')
    scheme_for(row['profile'], row['sample_id'], row['release_year'], row['component_year'])
    _, _, width = ROLE_COLUMNS[role]
    state = normalized_role_code(row['source_state_code'], width)
    area = normalized_role_code(row['source_area_code'], 5)
    own = rules.filter(pl.col('profile').eq(row['profile']).and_(pl.col('role').eq(role)))
    state_rules = own.filter(pl.col('rule_kind').eq('state').and_(pl.col('source_code').eq(state)))
    frame = own.filter(pl.col('rule_kind').eq('frame'))
    if state_rules.height != 1 or frame.height != 1:
        raise ValueError('missing or conflicting role state/frame evidence')
    state_rule, frame_rule = state_rules.row(0, named=True), frame.row(0, named=True)
    if state_rule['status'] == 'unsupported':
        raise ValueError('unexplained state/place value')
    special = own.filter(
        pl.col('rule_kind').eq('area_special').and_(pl.col('source_code').eq(area))
    )
    references = [state_rule, frame_rule]
    fips, status = state_rule['state_fips'], state_rule['status']
    if special.height:
        if special.height != 1:
            raise ValueError('conflicting area special rules')
        rule = special.row(0, named=True)
        references.append(rule)
        valid = (
            rule['status'] == 'niu_or_unidentifiable' and status in {
                'niu', 'domestic', 'territory'
            } or rule['status'] == 'foreign' and (status == 'foreign'
                or status == 'territory' and state_rule['label'] != 'Puerto Rico')
            or rule['status'] == 'territory' and state_rule['label'] == 'Puerto Rico'
        )
        if not valid:
            raise ValueError('incompatible documented role state/area pairing')
        outside_territory = (rule['status'] == 'foreign' and status == 'territory')
        status = 'territory' if outside_territory else rule['status']
        reason = (state_rule['label'] + ': ' if outside_territory else '') + rule['label']
    elif status == 'domestic':
        status = 'applicable'
        reason = '2020 defined area; population allocation retains uncertainty'
    elif status == 'territory':
        status, reason = 'territory', state_rule['label'] + ' outside 50-state/DC scope'
    else:
        raise ValueError('state/place has no compatible documented area interpretation')
    return dict(
        state_fips=fips,
        area_code=area,
        area_type='residence' if role == 'residence' else 'work_migration',
        puma_vintage=2020,
        area_status=status,
        status_reason=reason,
        flag_source_geography_recoded=(
            status == 'applicable' and row['profile'].removeprefix('acs/') == 'five_year'
            and row['component_year'] < 2022
        ),
        source_allocation_evidence_status='unavailable',
        reference_ids=sorted({v
                              for r in references
                              for v in r['reference_ids']}),
        reference_locators=sorted({v
                                   for r in references
                                   for v in r['reference_locators']}),
        rule_version=AREA_RULE_VERSION,
    )

def build_area_lookup(
    observed: pl.DataFrame, rules: pl.DataFrame, evidence: AreaEvidence, factors: FactorTables
) -> pl.DataFrame:
    '''Interpret each role independently and require complete compatible factor evidence.'''
    _validate_observed(observed)
    if rules.schema != ROLE_RULE_SCHEMA or rules.select(
        'profile', 'role', 'rule_kind', 'source_code'
    ).is_duplicated().any():
        raise ValueError('invalid or conflicting geographic role rules')
    for field in ['reference_ids', 'reference_locators']:
        for values in rules[field]:
            if values is None or not len(values) or any(v is None for v in values):
                raise ValueError('role rule lacks reference provenance')
            if values.to_list() != sorted(set(values.to_list())):
                raise ValueError('role rule references must be sorted and distinct')
    _verify_evidence_factors(evidence, factors)
    rows = []
    for observed_row in observed.iter_rows(named=True):
        identity = {key: observed_row[key] for key in AREA_KEY}
        interpreted = _interpret(observed_row, rules)
        key = (
            factor_key(
                interpreted['area_type'], interpreted['state_fips'], interpreted['area_code']
            ) if interpreted['area_status'] == 'applicable' else None
        )
        if interpreted['area_status'] == 'territory' and interpreted['area_code'] not in {
            '00000', '00001', '00002'
        }:
            residence = observed_row['role'] == 'residence'
            table = evidence.puma_totals if residence else evidence.puma_groups
            state_column = 'state_fips' if residence else 'group_state_fips'
            area_column = 'puma_code' if residence else 'group_code'
            if not table.filter(
                pl.col(state_column).eq(interpreted['state_fips']).and_(
                    pl.col(area_column).eq(interpreted['area_code'])
                )
            ).height:
                raise ValueError('territory area absent from complete reference definitions')
        if key is not None:
            citations = factors.county.filter(pl.col('factor_key').eq(key))
            for field in ['reference_ids', 'reference_locators']:
                interpreted[field] = sorted(
                    set(interpreted[field]).union(
                        value for values in citations[field] for value in values
                    )
                )
        rows.append(
            dict(
                area_lookup_id=lookup_id(tuple(identity.values())),
                **identity,
                **interpreted,
                factor_key=key
            )
        )
    lookup = pl.DataFrame(rows, schema=AREA_SCHEMA).sort(AREA_KEY, nulls_last=False)
    validate_area_lookup(lookup, observed, factors)
    return lookup

def validate_area_lookup(
    lookup: pl.DataFrame, observed: pl.DataFrame, factors: FactorTables
) -> None:
    '''Check exact key coverage, cited statuses and complete conserved applicable factors.'''
    _validate_observed(observed)
    validate_table('area', lookup)
    if not lookup.select(AREA_KEY).equals(
        observed.select(AREA_KEY).sort(AREA_KEY, nulls_last=False)
    ):
        raise ValueError('lookup differs from observed area keys')
    if lookup.filter(
        pl.col('reference_ids').list.len().eq(0).or_(
            pl.col('reference_locators').list.len().eq(0)
        ).or_(pl.col('status_reason').eq(''))
    ).height:
        raise ValueError('area interpretation lacks source citations or status reason')
    for row in lookup.iter_rows(named=True):
        role = row['role']
        if role not in ROLE_COLUMNS:
            raise ValueError('unsupported geographic role')
        scheme_for(row['profile'], row['sample_id'], row['release_year'], row['component_year'])
        area = normalized_role_code(row['source_area_code'], 5)
        normalized_role_code(row['source_state_code'], ROLE_COLUMNS[role][2])
        applicable = row['area_status'] == 'applicable'
        recoded = (applicable and row['profile'].removeprefix('acs/') == 'five_year'
                   and row['component_year'] < 2022)
        if (row['area_code'] != area or row['puma_vintage'] != 2020
                or row['area_type'] != ('residence' if role == 'residence' else 'work_migration')
                or row['flag_source_geography_recoded'] != recoded
                or row['source_allocation_evidence_status'] != 'unavailable'):
            raise ValueError('role annotations contradict documented source/frame identity')
    require_factor_coverage(lookup.filter(pl.col('area_status').eq('applicable')), factors.county)
