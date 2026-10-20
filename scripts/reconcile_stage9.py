'''Independent six-group ACS target acceptance CLI; consumes only authenticated source facts.'''

import importlib.util
import json
import math
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path
from tempfile import TemporaryDirectory

import polars as pl
import typer

def sibling(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


io = sibling('stage9_independent_io')
calc = sibling('stage9_independent_estimates')
freeze, preservation = io.freeze, io.preservation
app = typer.Typer(pretty_exceptions_show_locals=False)
GROUPS = {
    1: 'source_weight_Q_alignment_and_disjoint_funnels',
    2: 'universes_all_50_products_periods_and_denominators',
    3: 'native_Decimal_sums_80_replicates_ratios_and_SEs',
    4: 'canonical_supported_leaves_provenance_and_coverage',
    5: 'county_MSA_micro_noCBSA_allocation_mass_and_support',
    6: 'undefined_reasons_replicates_empty_products_and_fixed_tolerances',
}
S, INT, U, F, LS = 'String', 'Int64', 'UInt64', 'Float64', 'List(String)'
STAT_SCHEMA = dict.fromkeys(calc.STAT, S)
TARGET_SCHEMA = {
    **dict.fromkeys(['source', 'family', *calc.PAIR, 'measure'], S),
    'value': F,
    'se': F,
    'se_method': S,
    'n_unweighted': U,
    'n_weighted': F,
    'sample_set': S,
    'vintage': S,
    'universe': S,
    'flags': LS,
}
SUPPORT_SCHEMA = {
    **STAT_SCHEMA,
    'record_kind': S,
    'component_year': INT,
    'product_id': S,
    'pool_divisor': 'UInt8',
    'n_unweighted': U,
    'denominator_n_unweighted': U,
    'cell_weight_sum_exact': S,
    'denominator_weight_sum_exact': S,
    'cell_mass': F,
    'denominator_mass': F,
    'fractional_support_mass': F,
    'denominator_fractional_support_mass': F,
    'native_coverage_n': U,
    'native_coverage_mass': F,
    'point_status': S,
    'point_reason': S,
    'se_status': S,
    'se_reason': S,
    'undefined_replicates': 'List(UInt8)',
    'support_semantics': S,
    'flags': LS,
}
REPLICATE_SCHEMA = {
    **STAT_SCHEMA,
    'product_id': S,
    'replicate': 'UInt8',
    'numerator_sum_exact': S,
    'denominator_sum_exact': S,
    'pool_divisor': 'UInt8',
    'numerator': F,
    'denominator': F,
    'estimate': F,
    'status': S,
    'reason': S,
}
DIAGNOSTIC_SCHEMA = {
    **dict.fromkeys(calc.DIAG_KEY, S),
    'n_unweighted': U,
    'weight_sum_exact': S,
    'weighted_mass': F,
    'reference_ids': LS,
    'reference_locators': LS,
}
DIAGNOSTIC_SCHEMA['component_year'] = INT
RESIDUAL_SCHEMA = {
    **dict.fromkeys(
        [
            'source',
            'family',
            'workplace_unit_type',
            'workplace_unit',
            'code_unit_type',
            'code_unit',
            'sample_set',
            'vintage',
            'universe',
            'product_id',
        ],
        S,
    ),
    'component_year': INT,
    'replicate': 'UInt8',
    'residual_type': S,
    'pool_divisor': 'UInt8',
    'weighted_mass': F,
    'n_input_support': U,
    'fractional_support_mass': F,
    'flags': LS,
}
KEYS = {
    'target_support': [*calc.STAT, 'record_kind', 'component_year'],
    'replicate_estimates': [*calc.STAT, 'replicate'],
    'eligibility_diagnostics': calc.DIAG_KEY,
    'allocation_residuals': list(RESIDUAL_SCHEMA)[:13],
    'target_units': ['unit_type', 'unit'],
}
TARGET_KEYS = [
    n for n in TARGET_SCHEMA if n not in ('value', 'se', 'n_unweighted', 'n_weighted', 'flags')
]


def fail(gates, group, check, **details):
    def finite_json(value):
        if isinstance(value, float) and not math.isfinite(value):
            return repr(value)
        if isinstance(value, dict):
            return {k: finite_json(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [finite_json(v) for v in value]
        return value

    gates[group]['failures'].append({'check': check, **finite_json(details)})


def sort_key(key):
    return tuple((v is not None, str(v) if v is not None else '') for v in key)


def compare_rows(gates, group, name, actual, expected, keys, *, exact=False):
    '''Preserve every failing aggregate key/field; no example limits or silent filtering.'''
    actual_index, expected_index = {}, {}
    for label, rows, index in [
        ('actual', actual, actual_index),
        ('expected', expected, expected_index),
    ]:
        for row in rows:
            key = tuple(row[n] for n in keys)
            if key in index:
                fail(gates, group, name + ': duplicate ' + label + ' key', key=list(key))
            index[key] = row
    for key in sorted(set(actual_index) | set(expected_index), key=sort_key):
        a, e = actual_index.get(key), expected_index.get(key)
        if a is None or e is None:
            fail(
                gates,
                group,
                name + ': key set differs',
                key=list(key),
                actual_present=a is not None,
                expected_present=e is not None,
            )
            continue
        for field in set(a) | set(e):
            actual_value, expected_value = a.get(field), e.get(field)
            equal = actual_value == expected_value
            if isinstance(expected_value, float) and actual_value is not None and not exact:
                if field in ('value', 'estimate') and e.get('measure') == 'forward_share':
                    equal = calc.close_share(actual_value, expected_value)
                elif (
                    field == 'se'
                    or e.get('view', '').startswith('allocated')
                    or name == 'targets_allocated_area_mix'
                    or name.startswith('allocation_')
                ):
                    equal = calc.close_allocated_or_se(actual_value, expected_value)
                else:
                    equal = math.isfinite(actual_value) and actual_value == expected_value
            if not equal:
                fail(
                    gates,
                    group,
                    name + ': field differs',
                    key=list(key),
                    field=field,
                    actual=actual_value,
                    expected=expected_value,
                )


def schemas(code_schema):
    unit = {
        'unit_type': S,
        'unit': S,
        'kind': S,
        **{'code_' + n: str(t) for n, t in code_schema.items()},
        **dict.fromkeys(['node_id', 'node_system'], S),
        'node_vintage': INT,
        **dict.fromkeys(
            ['node_level', 'node_code', 'node_title', 'area_type', 'state_fips', 'area_code'], S
        ),
        'puma_vintage': INT,
        'population_year': INT,
        'county_composition_year': INT,
        'county_inventory_vintage': INT,
        'msa_delineation': S,
        'cbsa_type': S,
        **dict.fromkeys(
            ['roles', 'area_lookup_ids', 'factor_keys', 'reference_ids', 'reference_locators'], LS
        ),
    }
    return {
        **{name: TARGET_SCHEMA for name in io.TABLES[:3]},
        'target_units': unit,
        'target_support': SUPPORT_SCHEMA,
        'replicate_estimates': REPLICATE_SCHEMA,
        'eligibility_diagnostics': DIAGNOSTIC_SCHEMA,
        'allocation_residuals': RESIDUAL_SCHEMA,
    }


def reference_facts(data_dir, frozen, mapping):
    code_dir = io.relative(data_dir, 'derived/codes/' + frozen['request']['codes_run'])
    geo_dir = io.relative(data_dir, 'derived/geography/' + frozen['request']['geography_run'])
    nodes = {}
    for dimension, filename, system, year, level in [
        ('industry', 'naics_native_nodes', 'naics', 2022, 'national_industry'),
        ('occupation', 'soc_nodes', 'soc', 2018, 'detailed'),
    ]:
        table = pl.read_parquet(code_dir / (filename + '.parquet'))
        nodes[dimension] = table.filter(
            pl.col('system').eq(system) & pl.col('vintage').eq(year) & pl.col('level').eq(level)
        )['node_id'].to_list()
    county_table = pl.read_parquet(geo_dir / 'county_reference.parquet')
    counties = {r['county_id']: r for r in county_table.iter_rows(named=True)}
    factors = defaultdict(list)
    factor_table = pl.read_parquet(mapping / 'puma_county_factors.parquet')
    for row in factor_table.filter(pl.col('area_type').eq('work_migration')).iter_rows(named=True):
        origin = 'geography:2020:work_migration_puma:' + row['state_fips'] + row['area_code']
        io.require(
            row['county_node_id'] in counties
            and math.isfinite(row['factor'])
            and 0 <= row['factor'] <= 1,
            'unknown county or invalid factor',
        )
        factors[origin].append((row['county_node_id'], row['factor']))
    return nodes, counties, factors, code_dir, geo_dir


def expected_units(mapping, code_dir, geo_dir, schema):
    '''Assemble the full registry from frozen code/area/factor and selected node facts.'''
    codes = pl.read_parquet(mapping / 'acs_code_lookup.parquet')
    areas = pl.read_parquet(mapping / 'acs_area_lookup.parquet')
    factors = pl.read_parquet(mapping / 'puma_county_factors.parquet')
    code_nodes = {
        r['node_id']: r
        for file in ('naics_native_nodes', 'soc_nodes')
        for r in pl.read_parquet(code_dir / (file + '.parquet')).iter_rows(named=True)
    }
    geo_nodes = {
        r['node_id']: r
        for r in pl.read_parquet(geo_dir / 'geography_nodes.parquet').iter_rows(named=True)
    }
    counties = {
        r['county_id']: r
        for r in pl.read_parquet(geo_dir / 'county_reference.parquet').iter_rows(named=True)
    }
    units = {}

    def row(kind, unit, category):
        key = kind, unit
        if key not in units:
            units[key] = {
                name: [] if dtype.startswith('List(') else None for name, dtype in schema.items()
            }
            units[key].update(unit_type=kind, unit=unit, kind=category)
        return units[key]

    def union(destination, source, names):
        for name in names:
            destination[name] = sorted(set(destination[name]) | set(source[name]))

    def node(identity, kind, facts):
        destination = row(kind, identity, 'selected_node')
        authority = facts[identity]
        for name, value in authority.items():
            destination['node_id' if name == 'node_id' else 'node_' + name] = value
        if kind in ('county', 'cbsa'):
            destination.update(
                population_year=2020,
                puma_vintage=2020,
                county_composition_year=2022,
                county_inventory_vintage=2025,
            )
        if kind == 'cbsa':
            destination.update(msa_delineation='July 2023', cbsa_type='metropolitan')
        return destination

    for code in codes.iter_rows(named=True):
        kind = 'acs_industry_category' if code['system'] == 'naics' else 'acs_occupation_category'
        destination = row(kind, 'feature:' + kind + ':' + code['code_lookup_id'], 'observed_code')
        destination.update({'code_' + name: value for name, value in code.items()})
        union(destination, code, ('reference_ids', 'reference_locators'))
        if code['canonical_scalar_node_id'] is not None:
            kind = 'naics_national_industry' if code['system'] == 'naics' else 'soc_detailed'
            selected = node(code['canonical_scalar_node_id'], kind, code_nodes)
            union(selected, code, ('reference_ids', 'reference_locators'))
    for area in areas.filter(pl.col('area_status').eq('applicable')).iter_rows(named=True):
        kind = 'residence_puma' if area['area_type'] == 'residence' else 'work_migration_puma'
        destination = row(
            kind,
            'geography:2020:' + kind + ':' + area['state_fips'] + area['area_code'],
            'native_area',
        )
        destination.update(
            {name: area[name] for name in ('area_type', 'state_fips', 'area_code', 'puma_vintage')}
        )
        union(
            destination,
            {
                **area,
                'roles': [area['role']],
                'factor_keys': [area['factor_key']],
                'area_lookup_ids': [area['area_lookup_id']],
            },
            ('roles', 'factor_keys', 'area_lookup_ids', 'reference_ids', 'reference_locators'),
        )
    for factor in factors.filter(pl.col('area_type').eq('work_migration')).iter_rows(named=True):
        destination = node(factor['county_node_id'], 'county', geo_nodes)
        union(destination, factor, ('reference_ids', 'reference_locators'))
        county = counties[factor['county_node_id']]
        if county['cbsa_type'] == 'metropolitan':
            destination = node(county['cbsa_id'], 'cbsa', geo_nodes)
            union(destination, factor, ('reference_ids', 'reference_locators'))
    return list(units.values())


def calculate(data_dir, mapping, mapping_inputs, frozen, scratch):
    core, sources = calc.prepare_sources(data_dir, mapping, mapping_inputs, scratch)
    base, codes, usable = calc.semantic_frame(core)
    nodes, counties, factors, code_dir, geo_dir = reference_facts(data_dir, frozen, mapping)
    registry = calc.products()
    expected = {name: [] for name in io.TABLES}
    native = {}
    allocation_measurements = []
    for product in registry:
        if product['view'].startswith('allocated'):
            continue
        cells, coverage, diagnostics = calc.expected_native(
            base, core, product, nodes, codes, usable
        )
        native[product['product_id']] = cells, diagnostics
        support, reps, targets = calc.finalize(cells, coverage, product)
        expected['target_support'] += support
        expected['replicate_estimates'] += reps
        expected['eligibility_diagnostics'] += diagnostics
        expected['targets_' + product['view']] += targets
    comparison_fields = (
        'family',
        'dimension',
        'base_universe',
        'evidence_policy',
        'years',
        'sample_set',
        'pool_divisor',
    )
    for product in registry:
        if not product['view'].startswith('allocated'):
            continue
        observed = next(
            p
            for p in registry
            if p['view'] == 'observed' and all(p[n] == product[n] for n in comparison_fields)
        )
        cells, diagnostics = native[observed['product_id']]
        allocated, residuals = calc.allocation(
            cells, product, factors, counties, measurements=allocation_measurements
        )
        support, reps, targets = calc.finalize(allocated, {}, product)
        expected['target_support'] += support
        expected['replicate_estimates'] += reps
        expected['targets_allocated_area_mix'] += targets
        expected['allocation_residuals'] += residuals
        expected['eligibility_diagnostics'] += [
            dict(
                row,
                **{
                    n: product[n]
                    for n in (
                        'family',
                        'dimension',
                        'base_universe',
                        'evidence_policy',
                        'view',
                        'product_id',
                    )
                },
            )
            for row in diagnostics
        ]
    code_schema = pl.read_parquet_schema(mapping / 'acs_code_lookup.parquet')
    expected_schemas = schemas(code_schema)
    expected['target_units'] = expected_units(
        mapping, code_dir, geo_dir, expected_schemas['target_units']
    )
    return expected, expected_schemas, sources, registry, allocation_measurements


def mapping_table_inventory(mapping):
    '''Project complete table records after detached upstream authentication.'''
    authenticated = io.read(mapping / 'outputs.json')
    return {name: authenticated[name + '.parquet'] for name in io.stage8.TABLES}


def input_checks(gates, inputs, mapping_inputs, frozen, data_dir, mapping, registry):
    expected_rules = {}
    substantive = {
        'QEMPSTAT': 'EMPSTATD',
        'QIND': 'INDNAICS',
        'QOCC': 'OCCSOC',
        'QCLASSWK': 'CLASSWKRD',
        'QMIGRAT1': 'MIGRATE1',
        'QMIGPLC1': 'MIGPLAC1',
        'QPWSTAT2': 'PWSTATE2',
        'QTRANWOR': 'TRANWORK',
    }
    for profile, source in mapping_inputs['sources'].items():
        variables = {v['name']: v for v in source['ddi']['variables']}
        schema = pl.read_parquet_schema(io.relative(data_dir, source['parquet']))
        citation = next(c for c in source['raw_citations'] if c['path'].endswith('.xml'))
        domains, references, universes = {}, {}, {}
        for q in calc.QFIELDS:
            if q not in variables:
                continue
            locator = f'dataDscr/var[@name="{q}"]'
            references[q] = {'citation': citation, 'locator': locator}
            domains[q] = {
                'dtype': str(schema[q]) if q in schema else None,
                'substantive_variable': substantive[q],
                'applicability': 'associated substantive field must be applicable and usable',
                'reference_locator': locator,
                'metadata': variables[q],
                'values': {
                    code: {
                        'label': label,
                        'status': calc.flag_status(label),
                        'reference_locator': locator + f'/catgry[catValu="{code}"]',
                    }
                    for code, label in calc.flag_labels(q).items()
                },
            }
        for name, eligible in [
            ('EMPSTATD', ['10', '12']),
            ('CLASSWKRD', ['22', '23']),
            ('MIGRATE1', ['2', '3']),
            ('TRANWORK', list(calc.TRANSPORT)),
        ]:
            metadata = variables[name]
            universes[name] = {
                'metadata': metadata,
                'values': {v['value']: v['label'] for v in metadata['categories']},
                'dtype': str(schema[name]) if name in schema else None,
                'eligible': eligible,
            }
            if name == 'TRANWORK':
                universes[name].update(home=['80'], not_applicable=['00'])
            references[name] = {'citation': citation, 'locator': f'dataDscr/var[@name="{name}"]'}
        references['limitations'] = {'undelivered_puma_specific_flags': True}
        expected_rules[profile] = {
            'version': 'acs-target-rules-v1',
            'domains': domains,
            'references': references,
            'universe_categories': universes,
        }
    if inputs.get('rules') != {'version': 'acs-target-rules-v1', 'sources': expected_rules}:
        fail(gates, 1, 'complete delivered rule/domain/dtype/reference registry differs')
    expected_requirements = {p['product_id']: calc.required_flags(p) for p in registry}
    if inputs.get('evidence_requirements') != expected_requirements:
        fail(gates, 2, 'required Q evidence matrix differs')
    if inputs.get('universes') != {
        'civilian_employed': {'EMPSTATD': [10, 12]},
        'private_wage_salary': {'EMPSTATD': [10, 12], 'CLASSWKRD': [22, 23]},
    }:
        fail(gates, 2, 'base universe registry differs')
    weights = inputs.get('weights', {})
    if (
        weights.get('variables') != calc.WEIGHTS
        or weights.get('point') != 'PERWT'
        or weights.get('variance') != calc.WEIGHTS[1:]
        or weights.get('factor') != 1
    ):
        fail(gates, 3, 'literal PERWT/numbered replicate/factor registry differs')
    source_software = inputs.get('software', {})
    expected_files = set(io.stage8.EXECUTING_NAMES) | {
        'src/embedding_data/' + name + '.py'
        for name in (
            'target_contract',
            'acs_target_contract',
            'acs_target_inputs',
            'acs_target_rules',
            'acs_target_units',
            'acs_target_weights',
            'acs_target_membership',
            'acs_target_estimation',
            'acs_target_projection',
            'acs_target_tables',
            'acs_target_bundle',
            'acs_targets',
        )
    }
    files = source_software.get('files', {})
    if set(files) != expected_files:
        fail(gates, 2, 'complete executing target software inventory differs')
    for name, expected in files.items():
        if frozen['software']['files'].get(name) != expected:
            fail(gates, 2, 'executing target member differs', member=name)
    if (
        source_software.get('python_full') != frozen['software']['python']
        or source_software.get('implementation') != frozen['software']['implementation']
        or source_software.get('python') != io.platform.python_version()
        or source_software.get('dependencies') != frozen['software']['dependencies']
        or source_software.get('uv_lock_sha256')
        != frozen['software']['files']['uv.lock']['sha256']
    ):
        fail(gates, 2, 'executing Python/dependency/lock inventory differs')
    if inputs.get('frames') != mapping_inputs['frames']:
        fail(gates, 5, 'distinct selected mapping frame registry differs')
    if inputs.get('allocation_flags') != calc.ALLOCATION_FLAGS:
        fail(gates, 5, 'allocation evidence/limitation flags differ')
    units = inputs.get('units')
    if units != {
        'schema': 'target_units.parquet',
        'complete_aggregate_registry': True,
        'keys': ['unit_type', 'unit'],
    }:
        fail(gates, 4, 'unit registry contract differs')
    if inputs.get('selected_upstreams') != mapping_inputs['selected_upstreams']:
        fail(gates, 2, 'complete selected upstream provenance differs')
    if inputs.get('mapping_provenance', {}).get('tables') != mapping_table_inventory(mapping):
        fail(gates, 2, 'physical mapping table inventory differs')


def partition_rows(rows, keys, reducers):
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row[n] for n in keys)].append(row)
    result = []
    for key, values in grouped.items():
        entry = dict(zip(keys, key, strict=True))
        for name, operation in reducers.items():
            entry[name] = operation(values)
        result.append(entry)
    return result


def expected_conservation(expected, registry):
    sums = defaultdict(list)
    residuals = defaultdict(list)
    for row in expected['target_support']:
        if (
            row['family'] == 'area_mix'
            and row['measure'] == 'annual_average_total'
            and row['record_kind'] == 'cell'
        ):
            sums[row['product_id'], row['component_year'], 0].append(row)
    for row in expected['replicate_estimates']:
        if row['family'] == 'area_mix' and row['measure'] == 'annual_average_total':
            sums[row['product_id'], 0, row['replicate']].append(row)
    for row in expected['allocation_residuals']:
        if row['component_year'] == 0 or row['replicate'] == 0:
            residuals[
                row['product_id'], row['component_year'], row['replicate'], row['residual_type']
            ].append(row)
    masses = {}
    for key, values in sums.items():
        exact = None
        if values[0]['view'] == 'observed':
            with localcontext() as context:
                context.prec = 80
                raw = sum(
                    (
                        Decimal(row.get('cell_weight_sum_exact', row.get('numerator_sum_exact')))
                        for row in values
                    ),
                    Decimal(0),
                )
            exact = calc.decimal_text(raw)
            mass = float(raw) / values[0]['pool_divisor']
        else:
            mass = 0.0
            for row in sorted(values, key=lambda r: tuple(r[n] for n in calc.PAIR)):
                mass += row.get('cell_mass', row.get('numerator'))
        masses[key] = mass, exact
    residual_masses = {}
    for key, values in residuals.items():
        total = 0.0
        for row in sorted(
            values,
            key=lambda r: (
                r['workplace_unit_type'],
                r['workplace_unit'],
                r['code_unit_type'],
                r['code_unit'],
            ),
        ):
            total += row['weighted_mass']
        residual_masses[key] = total
    measurements, counts = [], []
    match = ('dimension', 'base_universe', 'evidence_policy', 'years')
    for observed in registry:
        if observed['view'] != 'observed' or observed['family'] != 'area_mix':
            continue
        county = next(
            p
            for p in registry
            if p['view'] == 'allocated_county' and all(p[n] == observed[n] for n in match)
        )
        metro = next(
            p
            for p in registry
            if p['view'] == 'allocated_msa' and all(p[n] == observed[n] for n in match)
        )
        keys = {
            (year, rep)
            for pid, year, rep in masses
            if pid in (observed['product_id'], county['product_id'], metro['product_id'])
        }
        keys |= {
            (year, rep) for pid, year, rep, _ in residual_masses if pid == metro['product_id']
        }
        before = len(measurements)
        for year, rep in sorted(keys):
            native, exact = masses.get((observed['product_id'], year, rep), (0.0, None))
            allocated = masses.get((county['product_id'], year, rep), (0.0, None))[0]
            msa = masses.get((metro['product_id'], year, rep), (0.0, None))[0]
            micro = residual_masses.get((metro['product_id'], year, rep, 'micropolitan'), 0.0)
            no_cbsa = residual_masses.get((metro['product_id'], year, rep, 'no_cbsa'), 0.0)
            for label, expected_mass, actual_mass in [
                ('native_to_county', native, allocated),
                ('county_to_msa_and_residuals', allocated, math.fsum((msa, micro, no_cbsa))),
            ]:
                difference = actual_mass - expected_mass
                measurements.append(
                    {
                        'observed_product_id': observed['product_id'],
                        'county_product_id': county['product_id'],
                        'msa_product_id': metro['product_id'],
                        'component_year': year,
                        'replicate': rep,
                        'check': label,
                        'expected_mass': expected_mass,
                        'actual_mass': actual_mass,
                        'difference': difference,
                        'absolute_error': abs(difference),
                        'tolerance': 1e-8 + 1e-12 * abs(expected_mass),
                        'status': 'pass'
                        if calc.close_allocated_or_se(actual_mass, expected_mass)
                        else 'fail',
                        'native_weight_sum_exact': exact if label == 'native_to_county' else None,
                        'metropolitan_mass': msa if label != 'native_to_county' else None,
                        'micropolitan_mass': micro if label != 'native_to_county' else None,
                        'no_cbsa_mass': no_cbsa if label != 'native_to_county' else None,
                    }
                )
        counts.append(
            {
                'observed_product_id': observed['product_id'],
                'serialized_check_count': len(measurements) - before,
            }
        )
    return measurements, counts


def report_checks(gates, report, expected, actual, registry, sources):
    expected_products = {}
    for product in registry:
        pid = product['product_id']
        pooled = [
            r
            for r in expected['target_support']
            if r['product_id'] == pid and r['component_year'] == 0 and r['record_kind'] == 'cell'
        ]
        targets = sum(r['point_status'] == 'defined' for r in pooled)
        funnels = [
            r
            for r in expected['eligibility_diagnostics']
            if r['product_id'] == pid and r['partition_kind'] == 'first_exclusion'
        ]
        closure = []
        for year in sorted({r['component_year'] for r in funnels}):
            count = sum(r['n_unweighted'] for r in funnels if r['component_year'] == year)
            closure.append({'year': year, 'input_rows': count, 'partition_rows': count})
        expected_products[pid] = {
            'product': product,
            'target_rows': targets,
            'supported_statistics': len(pooled),
            'empty_reason': None if targets else 'no_positive_eligible_supported_cells',
            'funnel_closure': closure,
        }
    actual_products = {r['product']['product_id']: r for r in report.get('products', [])}
    if len(report.get('products', [])) != 50:
        fail(gates, 6, 'report product count is not exactly50')
    if actual_products != expected_products:
        for pid in sorted(set(actual_products) | set(expected_products)):
            if actual_products.get(pid) != expected_products.get(pid):
                fail(
                    gates,
                    6,
                    'product counts/empty reasons/funnel closure differ',
                    product_id=pid,
                    actual=actual_products.get(pid),
                    expected=expected_products.get(pid),
                )
    for name, frame in actual.items():
        expected_table = {
            'rows': frame.height,
            'columns': frame.columns,
            'schema': {n: str(t) for n, t in frame.schema.items()},
        }
        if report.get('tables', {}).get(name) != expected_table:
            fail(gates, 2, 'report table schema/count differs', table=name)
    partitions = [
        (
            'diagnostic_partitions',
            1,
            'eligibility_diagnostics',
            [
                'product_id',
                'component_year',
                'partition_kind',
                'variable',
                'evidence_status',
                'reason',
            ],
            {
                'n_unweighted': lambda rows: sum(r['n_unweighted'] for r in rows),
                'weighted_mass': lambda rows: math.fsum(r['weighted_mass'] for r in rows),
            },
        ),
        (
            'support_distributions',
            6,
            'target_support',
            [
                'product_id',
                'component_year',
                'measure',
                'record_kind',
                'point_status',
                'se_status',
                'se_reason',
            ],
            {
                'rows': len,
                'n_min': lambda rows: min(r['n_unweighted'] for r in rows),
                'n_max': lambda rows: max(r['n_unweighted'] for r in rows),
            },
        ),
        (
            'allocation_residuals',
            5,
            'allocation_residuals',
            ['product_id', 'component_year', 'replicate', 'residual_type'],
            {
                'weighted_mass': lambda rows: math.fsum(r['weighted_mass'] for r in rows),
                'fractional_support_mass': lambda rows: math.fsum(
                    r['fractional_support_mass'] for r in rows
                ),
            },
        ),
    ]
    for name, group, table, keys, reducers in partitions:
        compare_rows(
            gates,
            group,
            name,
            report.get(name, []),
            partition_rows(expected[table], keys, reducers),
            keys,
        )
    conservation = report.get('allocation_conservation', {})
    measurements, counts = expected_conservation(expected, registry)
    compare_rows(
        gates,
        5,
        'allocation_conservation',
        conservation.get('measurements', []),
        measurements,
        ['observed_product_id', 'component_year', 'replicate', 'check'],
    )
    compare_rows(
        gates,
        5,
        'allocation_product_counts',
        conservation.get('products', []),
        counts,
        ['observed_product_id'],
        exact=True,
    )
    if (
        conservation.get('serialized_check_count') != len(measurements)
        or conservation.get('serialized_failure_count') != 0
    ):
        fail(gates, 5, 'allocation conservation check/failure counts differ')
    if (
        conservation.get('absolute_tolerance') != 1e-8
        or conservation.get('relative_tolerance') != 1e-12
    ):
        fail(gates, 6, 'reported numerical tolerances differ')
    if (
        sum(
            r['n_unweighted']
            for r in expected['eligibility_diagnostics']
            if r['partition_kind'] == 'first_exclusion'
        )
        != sources['acs/core']['rows'] * 50
    ):
        fail(gates, 1, 'independent disjoint funnel closure failed')


def reconcile(
    data_dir: Path,
    run_id: str,
    outputs_sha256: str,
    control_dir: Path,
    *,
    expected_freeze_sha256: str,
) -> dict:
    frozen = io.authenticated_freeze(data_dir, control_dir, expected_freeze_sha256)
    io.require(
        run_id in (frozen['first_run'], frozen['replay_run']), 'target ID not explicitly frozen'
    )
    directory = io.target_directory(data_dir, run_id)
    inputs = io.stage8.authenticate_bundle(directory, outputs_sha256)
    io.require(inputs.get('run_id') == run_id, 'target input run identity differs')
    io.require(
        {p.name for p in directory.iterdir()} == io.MEMBERS, 'target bundle membership differs'
    )
    preserved = preservation(data_dir, control_dir, expected_freeze_sha256=expected_freeze_sha256)
    mapping, mapping_inputs, _, _, _ = io.selected_mapping(
        data_dir, frozen['mapping_run'], frozen['mapping_outputs_sha256'], frozen['request']
    )
    io.require(mapping_inputs == frozen['mapping_inputs'], 'frozen mapping inputs differ')
    gates = {group: {'name': name, 'failures': []} for group, name in GROUPS.items()}
    if inputs.get('mapping') != {
        'run_id': frozen['mapping_run'],
        'outputs_sha256': frozen['mapping_outputs_sha256'],
    }:
        fail(gates, 2, 'target mapping identity differs')
    if inputs.get('selected_upstreams', {}).get('request') != frozen['request']:
        fail(gates, 2, 'target explicit upstream request differs')
    if inputs.get('sources') != mapping_inputs['sources']:
        fail(gates, 1, 'target source metadata differs')
    actual = {name: pl.read_parquet(directory / (name + '.parquet')) for name in io.TABLES}
    with TemporaryDirectory(
        prefix='stage9-independent-', dir=Path(control_dir).parent
    ) as temporary:
        expected, expected_schemas, sources, registry, allocation_measurements = calculate(
            Path(data_dir), mapping, mapping_inputs, frozen, Path(temporary)
        )
    for measurement in allocation_measurements:
        if measurement['status'] != 'pass':
            fail(
                gates, 5, 'independent annual/pooled full/all80 conservation failed', **measurement
            )
    gates[5]['independent_conservation'] = allocation_measurements
    input_checks(gates, inputs, mapping_inputs, frozen, Path(data_dir), mapping, registry)
    if len(inputs.get('products', [])) != 50 or {
        p['product_id']: p for p in inputs.get('products', [])
    } != {p['product_id']: p for p in registry}:
        fail(gates, 2, '50-product spec registry differs')
    for name, frame in actual.items():
        schema = {n: str(t) for n, t in frame.schema.items()}
        if list(schema.items()) != list(expected_schemas[name].items()):
            fail(
                gates,
                2,
                'exact ordered schema differs',
                table=name,
                actual=schema,
                expected=expected_schemas[name],
            )
        keys = KEYS.get(name, [n for n in TARGET_KEYS if n != 'se_method'])
        if not set(keys) <= set(frame.columns):
            continue
        if name in ('target_support', 'replicate_estimates'):
            for views, group in [
                (['observed'], 3),
                (['canonical'], 4),
                (['allocated_county', 'allocated_msa'], 5),
            ]:
                compare_rows(
                    gates,
                    group,
                    name,
                    frame.filter(pl.col('view').is_in(views)).to_dicts(),
                    [row for row in expected[name] if row['view'] in views],
                    keys,
                )
        else:
            group = {
                'target_units': 4,
                'eligibility_diagnostics': 1,
                'allocation_residuals': 5,
                'targets_canonical': 4,
                'targets_allocated_area_mix': 5,
            }.get(name, 3)
            compare_rows(gates, group, name, frame.to_dicts(), expected[name], keys)
    report = io.read(directory / 'report.json')
    if report.get('run_id') != run_id or report.get('schema_version') != 'acs-targets-v1':
        fail(gates, 2, 'report run/schema identity differs')
    report_checks(gates, report, expected, actual, registry, sources)
    other_id = frozen['replay_run'] if run_id == frozen['first_run'] else frozen['first_run']
    other = io.target_directory(data_dir, other_id)
    if other.exists():
        for name, frame in actual.items():
            replay = pl.read_parquet(other / (name + '.parquet'))
            if list(frame.schema.items()) != list(replay.schema.items()):
                fail(gates, 6, 'exact replay schema differs', table=name)
            elif not frame.equals(replay):
                keys = KEYS.get(name, [n for n in TARGET_KEYS if n != 'se_method'])
                compare_rows(
                    gates,
                    6,
                    name + ': exact replay',
                    frame.to_dicts(),
                    replay.to_dicts(),
                    keys,
                    exact=True,
                )
                if frame.sort(keys, nulls_last=False).equals(replay.sort(keys, nulls_last=False)):
                    fail(gates, 6, 'exact replay row order differs', table=name)
        other_report = io.read(other / 'report.json')

        def substantive(value):
            return {k: v for k, v in value.items() if k not in ('run_id', 'created_at')}

        if substantive(report) != substantive(other_report):
            fail(gates, 6, 'exact substantive report replay differs')
    for group in gates.values():
        group['failure_count'] = len(group['failures'])
        group['status'] = 'fail' if group['failure_count'] else 'pass'
    result = {
        'failure_count': sum(g['failure_count'] for g in gates.values()),
        'gates': gates,
        'sources': sources,
        'preservation': preserved,
        'tolerances': {
            'share_absolute': 1e-12,
            'allocated_or_se_absolute': 1e-8,
            'allocated_or_se_relative': 1e-12,
        },
        'run_id': run_id,
        'outputs_sha256': outputs_sha256,
        'freeze_sha256': expected_freeze_sha256,
    }
    # Final authentication rejects drift during independent source evaluation.
    io.stage8.authenticate_bundle(directory, outputs_sha256)
    preservation(data_dir, control_dir, expected_freeze_sha256=expected_freeze_sha256)
    return result


def emit(operation, *args, **kwargs):
    try:
        result = operation(*args, **kwargs)
    except (ValueError, OSError, KeyError, TypeError) as error:
        typer.echo(
            json.dumps(
                {
                    'failure_count': 1,
                    'error': str(error),
                    'gates': {
                        n: {
                            'name': name,
                            'status': 'fail' if n == 1 else 'not_run',
                            'failure_count': 1 if n == 1 else 0,
                            'failures': [
                                {'check': 'authentication/control failure', 'error': str(error)}
                            ]
                            if n == 1
                            else [],
                        }
                        for n, name in GROUPS.items()
                    },
                },
                sort_keys=True,
            )
        )
        raise typer.Exit(2) from None
    typer.echo(json.dumps(result, sort_keys=True, allow_nan=False))
    if result.get('failure_count', 0):
        raise typer.Exit(1)


@app.command('freeze')
def freeze_command(
    data_dir: Path = typer.Option(...),
    control_dir: Path = typer.Option(...),
    mapping_run: str = typer.Option(...),
    mapping_outputs_sha256: str = typer.Option(...),
    codes_run: str = typer.Option(...),
    codes_outputs_sha256: str = typer.Option(...),
    geography_run: str = typer.Option(...),
    geography_outputs_sha256: str = typer.Option(...),
    ipums_run: str = typer.Option(...),
    ipums_outputs_sha256: str = typer.Option(...),
    ipums_references_receipt_sha256: str = typer.Option(..., '--ipums-references-sha256'),
    first_run: str = typer.Option(...),
    replay_run: str = typer.Option(...),
):
    request = {name: value for name, value in locals().items() if name in io.REQUEST_FIELDS}
    emit(
        freeze,
        data_dir,
        control_dir,
        mapping_run=mapping_run,
        mapping_outputs_sha256=mapping_outputs_sha256,
        request=request,
        first_run=first_run,
        replay_run=replay_run,
    )


@app.command('preservation')
def preservation_command(
    data_dir: Path = typer.Option(...),
    control_dir: Path = typer.Option(...),
    freeze_sha256: str = typer.Option(...),
):
    emit(preservation, data_dir, control_dir, expected_freeze_sha256=freeze_sha256)


@app.command('reconcile')
def reconcile_command(
    run_id: str = typer.Argument(...),
    data_dir: Path = typer.Option(...),
    control_dir: Path = typer.Option(...),
    outputs_sha256: str = typer.Option(...),
    freeze_sha256: str = typer.Option(...),
):
    emit(
        reconcile,
        data_dir,
        run_id,
        outputs_sha256,
        control_dir,
        expected_freeze_sha256=freeze_sha256,
    )


if __name__ == '__main__':
    app()
