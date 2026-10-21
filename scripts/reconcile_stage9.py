'''Independent six-group ACS target acceptance CLI; consumes only authenticated source facts.'''

import importlib.util
import json
import math
import shutil
from collections import defaultdict
from decimal import Decimal, localcontext
from itertools import groupby
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import NamedTuple

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


def _normalized_sort(frame, keys):
    '''Keep original typed keys and input ordinal through lexical null-first sorting.'''
    for key in keys:
        if key not in frame.collect_schema():
            raise KeyError(key)
    ordinal = '__independent_ordinal'
    io.require(ordinal not in frame.collect_schema(), 'reserved comparison column')
    ordered = frame.with_columns(pl.int_range(0, pl.len(), dtype=pl.UInt64).alias(ordinal))
    expressions = []
    for key in keys:
        expressions.extend((pl.col(key).is_not_null(), pl.col(key).cast(pl.String).fill_null('')))
    return ordered.sort([*expressions, pl.col(ordinal)], maintain_order=True), ordinal


def _field_equal(name, field, actual_value, expected_value, expected, exact):
    equal = actual_value == expected_value
    if isinstance(expected_value, float) and actual_value is not None and not exact:
        if field in ('value', 'estimate') and expected.get('measure') == 'forward_share':
            return calc.close_share(actual_value, expected_value)
        if (
            field == 'se'
            or expected.get('view', '').startswith('allocated')
            or name == 'targets_allocated_area_mix'
            or name.startswith('allocation_')
        ):
            return calc.close_allocated_or_se(actual_value, expected_value)
        return math.isfinite(actual_value) and actual_value == expected_value
    return equal


def _compare_fact_rows(
    gates, group, name, actual, expected, keys, workspace, *, exact=False, batch_rows=4096
):
    '''Merge complete key groups; ledger duplicates in original side/encounter order.'''
    io.require(type(batch_rows) is int and batch_rows > 0, 'invalid batch_rows')
    with TemporaryDirectory(prefix='comparison-', dir=workspace) as temporary:
        owner = Path(temporary)
        duplicate_tables = []

        def grouped(frame, label):
            ordered, ordinal = _normalized_sort(frame, keys)
            path = owner / (label + '-ordered.parquet')
            calc._sink(ordered, path)
            writer = calc._FactWriter(
                owner,
                label + '-duplicates',
                {'ordinal': pl.UInt64, 'key': pl.String},
                ['ordinal'],
                '',
                None,
                batch_rows,
            )
            last_key, last = None, None
            for row in calc._rows(pl.scan_parquet(path), batch_rows):
                position = row.pop(ordinal)
                key = tuple(row[k] for k in keys)
                if last is not None and key == last_key:
                    writer.append({'ordinal': position, 'key': json.dumps(list(key))})
                elif last is not None:
                    yield last_key, last
                last_key, last = key, row
            if last is not None:
                yield last_key, last
            duplicate_tables.append((label, writer.finish(sort=True)))

        field_ledger = owner / 'fields.jsonl'
        with field_ledger.open('x') as output:

            def record(check, **details):
                single = {group: {'failures': []}}
                fail(single, group, check, **details)
                output.write(json.dumps(single[group]['failures'][0], allow_nan=False) + '\n')

            a_rows, e_rows = iter(grouped(actual, 'actual')), iter(grouped(expected, 'expected'))
            a, e = next(a_rows, None), next(e_rows, None)
            while a is not None or e is not None:
                if e is None or (a is not None and sort_key(a[0]) < sort_key(e[0])):
                    record(
                        name + ': key set differs',
                        key=list(a[0]),
                        actual_present=True,
                        expected_present=False,
                    )
                    a = next(a_rows, None)
                elif a is None or sort_key(e[0]) < sort_key(a[0]) or a[0] != e[0]:
                    record(
                        name + ': key set differs',
                        key=list(e[0]),
                        actual_present=False,
                        expected_present=True,
                    )
                    e = next(e_rows, None)
                else:
                    for field in set(a[1]) | set(e[1]):
                        av, ev = a[1].get(field), e[1].get(field)
                        if not _field_equal(name, field, av, ev, e[1], exact):
                            record(
                                name + ': field differs',
                                key=list(a[0]),
                                field=field,
                                actual=av,
                                expected=ev,
                            )
                    a, e = next(a_rows, None), next(e_rows, None)
        for label, table in sorted(duplicate_tables, key=lambda item: item[0]):
            for row in calc._rows(_scan(table), batch_rows):
                fail(
                    gates,
                    group,
                    name + ': duplicate ' + label + ' key',
                    key=json.loads(row['key']),
                )
        with field_ledger.open() as source:
            for line in source:
                gates[group]['failures'].append(json.loads(line))


def _compare_original_order(first, second, *, batch_rows=4096):
    '''Drain independently sized batches while comparing aligned original serialized slices.'''
    io.require(type(batch_rows) is int and batch_rows > 0, 'invalid batch_rows')
    schema_equal = list(first.collect_schema().items()) == list(second.collect_schema().items())
    streams = [
        iter(
            frame.collect_batches(
                chunk_size=batch_rows, engine='streaming', maintain_order=True, lazy=True
            )
        )
        for frame in (first, second)
    ]
    counts = [0, 0]

    def advance(side):
        batch = next(streams[side], None)
        if batch is not None:
            counts[side] += batch.height
        return batch

    a, b = advance(0), advance(1)
    values_equal = schema_equal
    while a is not None or b is not None:
        if a is None:
            values_equal = False
            b = advance(1)
        elif b is None:
            values_equal = False
            a = advance(0)
        else:
            length = min(a.height, b.height)
            if schema_equal and not a.head(length).equals(b.head(length)):
                values_equal = False
            a = a.slice(length) if a.height > length else advance(0)
            b = b.slice(length) if b.height > length else advance(1)
    return {
        'schema_equal': schema_equal,
        'values_equal': values_equal,
        'first_rows': counts[0],
        'second_rows': counts[1],
    }


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


class _DiskCalculation(NamedTuple):
    owner: Path
    tables: dict[str, calc._FactTable]
    schemas: dict
    sources: dict
    registry: tuple[dict, ...]
    allocation_measurements: tuple[calc._FactTable, ...]


def _typed_schema(schema):
    def dtype(text):
        if text.startswith('List('):
            return pl.List(dtype(text[5:-1]))
        return getattr(pl, text)

    return pl.Schema({name: dtype(text) for name, text in schema.items()})


def _scan(table):
    return pl.scan_parquet(table.paths, glob=False)


def _table_keys(name):
    return tuple(KEYS.get(name, TARGET_KEYS))



def _assemble_ranges(frame, name, owner, schema, keys, batch_rows):
    '''Persist leading-prefix ranges in one ordered pass without deduplication.'''
    ordered = owner / (name + '-ordered.parquet')
    calc._sink(frame.sort(keys, nulls_last=False, maintain_order=True), ordered)
    writer = calc._FactWriter(owner, name + '-range', schema, keys, '', None, batch_rows)
    prefix_keys = keys[:4]
    previous = None
    for row in calc._rows(pl.scan_parquet(ordered), batch_rows):
        prefix = tuple(row[k] for k in prefix_keys)
        if previous is not None and prefix != previous and writer.rows:
            writer.flush()
        writer.append(row)
        previous = prefix
    result = writer.finish()
    ordered.unlink()
    return result


def _calculate_disk(data_dir, mapping, mapping_inputs, frozen, scratch, *, batch_rows=4096):
    '''Complete source-dependent work before publishing calculation-owned aggregate files.'''
    io.require(type(batch_rows) is int and batch_rows > 0, 'invalid batch_rows')
    declared = schemas(pl.read_parquet_schema(mapping / 'acs_code_lookup.parquet'))
    typed = {name: _typed_schema(schema) for name, schema in declared.items()}
    with calc._owned(scratch, 'independent-calculation') as owner:
        work, outputs = owner / 'work', owner / 'outputs'
        work.mkdir()
        outputs.mkdir()
        core, sources = calc.prepare_sources(data_dir, mapping, mapping_inputs, owner)
        base, codes, usable = calc.semantic_frame(core)
        nodes, counties, factors, code_dir, geo_dir = reference_facts(data_dir, frozen, mapping)
        registry = tuple(calc.products())
        paths = {name: [] for name in io.TABLES}
        measurements = {}
        final_schemas = {
            name: typed[name] for name in ('target_support', 'replicate_estimates')
        } | {'targets': typed['targets_observed']}

        def retain(name, table):
            path = outputs / f'{name}-{len(paths[name]):04d}.parquet'
            calc._sink(_scan(table).select(typed[name].names()), path)
            paths[name].append(path)

        def finalize(facts, product):
            completed = calc._finalize_disk(
                facts.cells,
                facts.denominators,
                facts.coverage if isinstance(facts, calc._NativeFacts) else None,
                product,
                work,
                schemas=final_schemas,
                batch_rows=batch_rows,
            )
            for name in ('target_support', 'replicate_estimates'):
                retain(name, completed[name])
            target = (
                'targets_allocated_area_mix'
                if product['view'].startswith('allocated')
                else ('targets_' + product['view'])
            )
            retain(target, completed['targets'])
            retain('eligibility_diagnostics', facts.diagnostics)
            shutil.rmtree(completed['targets'].owner)

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
            if product['view'].startswith('allocated'):
                continue
            native = calc._expected_native_disk(
                base,
                core,
                product,
                nodes,
                codes,
                usable,
                work,
                diagnostic_schema=typed['eligibility_diagnostics'],
                batch_rows=batch_rows,
            )
            finalize(native, product)
            if product['view'] == 'observed':
                for allocated in registry:
                    if not allocated['view'].startswith('allocated') or not all(
                        product[n] == allocated[n] for n in comparison_fields
                    ):
                        continue
                    facts = calc._allocation_disk(
                        native,
                        allocated,
                        factors,
                        counties,
                        work,
                        residual_schema=typed['allocation_residuals'],
                        diagnostic_schema=typed['eligibility_diagnostics'],
                        batch_rows=batch_rows,
                    )
                    finalize(facts, allocated)
                    retain('allocation_residuals', facts.residuals)
                    path = outputs / ('measurements-' + allocated['product_id'] + '.parquet')
                    calc._sink(_scan(facts.measurements), path)
                    measurements[allocated['product_id']] = facts.measurements._replace(
                        owner=owner, paths=(path,)
                    )
                    shutil.rmtree(facts.owner)
            shutil.rmtree(native.owner)
        units = pl.DataFrame(
            expected_units(mapping, code_dir, geo_dir, declared['target_units']),
            schema=typed['target_units'],
        ).lazy()
        unit_path = outputs / 'units.parquet'
        calc._sink(units, unit_path)
        paths['target_units'].append(unit_path)
        tables = {}
        for name in io.TABLES:
            keys = _table_keys(name)
            frame = (
                pl.scan_parquet(paths[name], glob=False)
                if paths[name]
                else (pl.DataFrame(schema=typed[name]).lazy())
            )
            tables[name] = _assemble_ranges(frame, name, outputs, typed[name], keys, batch_rows)
            for fragment in paths[name]:
                fragment.unlink()
        return _DiskCalculation(
            owner,
            tables,
            declared,
            sources,
            registry,
            tuple(
                measurements[p['product_id']]
                for p in registry
                if p['view'].startswith('allocated')
            ),
        )


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


def _row_count(frame):
    return frame.select(pl.len()).collect(engine='streaming').item()


def _check_table_domain_counts(gates, name, actual, expected, keys, *, batch_rows=4096):
    if name in ('target_support', 'replicate_estimates') and 'view' in actual.collect_schema():
        invalid = actual.filter(
            pl.col('view').is_null()
            | ~pl.col('view').is_in(['observed', 'canonical', 'allocated_county', 'allocated_msa'])
        )
        for row in calc._rows(invalid, batch_rows):
            fail(
                gates,
                2,
                'unsupported support/replicate view',
                table=name,
                key=[row[k] for k in keys],
                view=row['view'],
            )
    actual_count, expected_count = _row_count(actual), _row_count(expected)
    if actual_count != expected_count:
        fail(
            gates,
            2,
            'independent table row count differs',
            table=name,
            actual=actual_count,
            expected=expected_count,
        )


def _partition_disk(frame, keys, reducers, owner, label, batch_rows):
    '''One sorted aggregate file, independent complete-group passes for each reduction.'''
    path = owner / (label + '-groups.parquet')
    calc._sink(frame.sort(keys, nulls_last=False, maintain_order=True), path)
    schema = frame.collect_schema()
    output_schema = {k: schema[k] for k in keys} | {n: dtype for n, dtype, _, _ in reducers}
    writer = calc._FactWriter(owner, label, output_schema, keys, '', None, batch_rows)

    def reduced(operation, column):
        for key, values in groupby(
            calc._rows(pl.scan_parquet(path), batch_rows),
            key=lambda row: tuple(row[k] for k in keys),
        ):
            yield key, operation(row[column] if column else 1 for row in values)

    streams = [reduced(operation, column) for _, _, operation, column in reducers]
    for groups in zip(*streams, strict=True):
        key = groups[0][0]
        io.require(all(g[0] == key for g in groups), 'summary group alignment differs')
        writer.append(
            dict(zip(keys, key, strict=True))
            | {spec[0]: group[1] for spec, group in zip(reducers, groups, strict=True)}
        )
    return writer.finish()


def _report_conservation_disk(calculation, owner, batch_rows):
    '''Keep only required product/year/r mass summaries, never cell or replicate indexes.'''
    masses, residual_masses = {}, {}
    registry = calculation.registry
    products_by_id = {p['product_id']: p for p in registry}
    for name, group_keys, value_column, text_column in [
        ('target_support', ['product_id', 'component_year'], 'cell_mass', 'cell_weight_sum_exact'),
        ('replicate_estimates', ['product_id', 'replicate'], 'numerator', 'numerator_sum_exact'),
    ]:
        frame = _scan(calculation.tables[name]).filter(
            pl.col('family').eq('area_mix') & pl.col('measure').eq('annual_average_total')
        )
        if name == 'target_support':
            frame = frame.filter(pl.col('record_kind').eq('cell'))
        path = owner / (name + '-report-mass.parquet')
        calc._sink(frame.sort([*group_keys, *calc.PAIR], maintain_order=True), path)
        for key, values in groupby(
            calc._rows(pl.scan_parquet(path), batch_rows),
            key=lambda r: tuple(r[k] for k in group_keys),
        ):
            product = products_by_id[key[0]]
            exact = None
            if product['view'] == 'observed':
                with localcontext() as context:
                    context.prec = 80
                    raw = sum((Decimal(r[text_column]) for r in values), Decimal(0))
                exact = calc.decimal_text(raw)
                mass = float(raw) / product['pool_divisor']
            else:
                mass = 0.0
                for row in values:
                    mass += row[value_column]
            year, rep = (key[1], 0) if name == 'target_support' else (0, key[1])
            masses[key[0], year, rep] = mass, exact
    keys = ['product_id', 'component_year', 'replicate', 'residual_type']
    path = owner / 'report-residual-masses.parquet'
    calc._sink(
        _scan(calculation.tables['allocation_residuals'])
        .filter(pl.col('component_year').eq(0) | pl.col('replicate').eq(0))
        .sort(
            [*keys, 'workplace_unit_type', 'workplace_unit', 'code_unit_type', 'code_unit'],
            maintain_order=True,
        ),
        path,
    )
    for key, values in groupby(
        calc._rows(pl.scan_parquet(path), batch_rows), key=lambda r: tuple(r[k] for k in keys)
    ):
        mass = 0.0
        for row in values:
            mass += row['weighted_mass']
        residual_masses[key] = mass

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


def _report_checks_disk(gates, report, calculation, actual, workspace, *, batch_rows=4096):
    registry, sources = calculation.registry, calculation.sources
    expected = {n: _scan(t) for n, t in calculation.tables.items()}
    support_counts = {
        r['product_id']: r
        for r in expected['target_support']
        .filter(pl.col('component_year').eq(0) & pl.col('record_kind').eq('cell'))
        .group_by('product_id')
        .agg(
            pl.len().alias('supported_statistics'),
            pl.col('point_status').eq('defined').sum().alias('target_rows'),
        )
        .collect(engine='streaming')
        .iter_rows(named=True)
    }
    funnels = defaultdict(list)
    for r in (
        expected['eligibility_diagnostics']
        .filter(pl.col('partition_kind').eq('first_exclusion'))
        .group_by('product_id', 'component_year')
        .agg(pl.col('n_unweighted').sum().alias('count'))
        .sort('component_year')
        .collect(engine='streaming')
        .iter_rows(named=True)
    ):
        funnels[r['product_id']].append(
            {'year': r['component_year'], 'input_rows': r['count'], 'partition_rows': r['count']}
        )
    expected_products = {}
    for product in registry:
        pid = product['product_id']
        counts = support_counts.get(pid, {'target_rows': 0, 'supported_statistics': 0})
        expected_products[pid] = {
            'product': product,
            'target_rows': counts['target_rows'],
            'supported_statistics': counts['supported_statistics'],
            'empty_reason': None
            if counts['target_rows']
            else 'no_positive_eligible_supported_cells',
            'funnel_closure': funnels[pid],
        }
    actual_products = {r['product']['product_id']: r for r in report.get('products', [])}
    if len(report.get('products', [])) != 50:
        fail(gates, 6, 'report product count is not exactly50')
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
        schema = frame.collect_schema()
        expected_table = {
            'rows': _row_count(frame),
            'columns': schema.names(),
            'schema': {n: str(t) for n, t in schema.items()},
        }
        if report.get('tables', {}).get(name) != expected_table:
            fail(gates, 2, 'report table schema/count differs', table=name)
        keys = KEYS.get(name, [n for n in TARGET_KEYS if n != 'se_method'])
        if set(keys) <= set(schema):
            _check_table_domain_counts(
                gates, name, frame, expected[name], keys, batch_rows=batch_rows
            )
        elif _row_count(frame) != _row_count(expected[name]):
            fail(
                gates,
                2,
                'independent table row count differs',
                table=name,
                actual=_row_count(frame),
                expected=_row_count(expected[name]),
            )
    with TemporaryDirectory(prefix='report-', dir=workspace) as temporary:
        owner = Path(temporary)
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
                [
                    ('n_unweighted', pl.UInt64, sum, 'n_unweighted'),
                    ('weighted_mass', pl.Float64, math.fsum, 'weighted_mass'),
                ],
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
                [
                    ('rows', pl.UInt64, sum, None),
                    ('n_min', pl.UInt64, min, 'n_unweighted'),
                    ('n_max', pl.UInt64, max, 'n_unweighted'),
                ],
            ),
            (
                'allocation_residuals',
                5,
                'allocation_residuals',
                ['product_id', 'component_year', 'replicate', 'residual_type'],
                [
                    ('weighted_mass', pl.Float64, math.fsum, 'weighted_mass'),
                    ('fractional_support_mass', pl.Float64, math.fsum, 'fractional_support_mass'),
                ],
            ),
        ]
        for name, group, table, keys, reducers in partitions:
            summary = _partition_disk(expected[table], keys, reducers, owner, name, batch_rows)
            values = report.get(name, [])
            reported = (
                pl.DataFrame(values, infer_schema_length=None)
                if values
                else pl.DataFrame(schema=summary.schema)
            ).lazy()
            _compare_fact_rows(
                gates, group, name, reported, _scan(summary), keys, owner, batch_rows=batch_rows
            )
        measurements, counts = _report_conservation_disk(calculation, owner, batch_rows)
        conservation = report.get('allocation_conservation', {})
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
        sum(r['input_rows'] for values in funnels.values() for r in values)
        != sources['acs/core']['rows'] * 50
    ):
        fail(gates, 1, 'independent disjoint funnel closure failed')



def _allocation_evidence_disk(gates, tables, *, batch_rows=4096):
    '''Retain every measurement and nest failed records without reserved-key collisions.'''
    io.require(type(batch_rows) is int and batch_rows > 0, 'invalid batch_rows')
    measurements = []
    for table in tables:
        for row in calc._rows(_scan(table), batch_rows):
            measurement = {k: v for k, v in row.items() if k != '_check_order'}
            measurements.append(measurement)
            if measurement['status'] != 'pass':
                fail(
                    gates,
                    5,
                    'independent annual/pooled full/all80 conservation failed',
                    measurement=measurement,
                )
    return measurements


def _substantive_report(value):
    return {k: v for k, v in value.items() if k not in ('run_id', 'created_at')}


def _replay_checks_disk(gates, actual, replay, workspace, *, batch_rows=4096):
    for name, frame in actual.items():
        second = replay[name]
        comparison = _compare_original_order(frame, second, batch_rows=batch_rows)
        if not comparison['schema_equal']:
            fail(gates, 6, 'exact replay schema differs', table=name)
        elif not comparison['values_equal']:
            keys = KEYS.get(name, [n for n in TARGET_KEYS if n != 'se_method'])
            _compare_fact_rows(
                gates,
                6,
                name + ': exact replay',
                frame,
                second,
                keys,
                workspace,
                exact=True,
                batch_rows=batch_rows,
            )
            ordered = _compare_original_order(
                frame.sort(keys, nulls_last=False, maintain_order=True),
                second.sort(keys, nulls_last=False, maintain_order=True),
                batch_rows=batch_rows,
            )
            if ordered['values_equal']:
                fail(gates, 6, 'exact replay row order differs', table=name)


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
    actual = {name: pl.scan_parquet(directory / (name + '.parquet')) for name in io.TABLES}
    with TemporaryDirectory(
        prefix='stage9-independent-', dir=Path(control_dir).parent
    ) as temporary:
        workspace = Path(temporary)
        calculation = _calculate_disk(Path(data_dir), mapping, mapping_inputs, frozen, workspace)
        sources, registry = calculation.sources, calculation.registry
        gates[5]['independent_conservation'] = _allocation_evidence_disk(
            gates, calculation.allocation_measurements
        )
        input_checks(gates, inputs, mapping_inputs, frozen, Path(data_dir), mapping, registry)
        if len(inputs.get('products', [])) != 50 or {
            p['product_id']: p for p in inputs.get('products', [])
        } != {p['product_id']: p for p in registry}:
            fail(gates, 2, '50-product spec registry differs')
        for name, frame in actual.items():
            schema = {n: str(t) for n, t in frame.collect_schema().items()}
            if list(schema.items()) != list(calculation.schemas[name].items()):
                fail(
                    gates,
                    2,
                    'exact ordered schema differs',
                    table=name,
                    actual=schema,
                    expected=calculation.schemas[name],
                )
            keys = KEYS.get(name, [n for n in TARGET_KEYS if n != 'se_method'])
            if not set(keys) <= set(schema):
                continue
            expected = _scan(calculation.tables[name])
            if name in ('target_support', 'replicate_estimates'):
                for views, group in [
                    (['observed'], 3),
                    (['canonical'], 4),
                    (['allocated_county', 'allocated_msa'], 5),
                ]:
                    _compare_fact_rows(
                        gates,
                        group,
                        name,
                        frame.filter(pl.col('view').is_in(views)),
                        expected.filter(pl.col('view').is_in(views)),
                        keys,
                        workspace,
                    )
            else:
                group = {
                    'target_units': 4,
                    'eligibility_diagnostics': 1,
                    'allocation_residuals': 5,
                    'targets_canonical': 4,
                    'targets_allocated_area_mix': 5,
                }.get(name, 3)
                _compare_fact_rows(gates, group, name, frame, expected, keys, workspace)
        report = io.read(directory / 'report.json')
        if report.get('run_id') != run_id or report.get('schema_version') != 'acs-targets-v1':
            fail(gates, 2, 'report run/schema identity differs')
        _report_checks_disk(gates, report, calculation, actual, workspace)
        other_id = frozen['replay_run'] if run_id == frozen['first_run'] else frozen['first_run']
        other = io.target_directory(data_dir, other_id)
        if other.exists():
            replay = {name: pl.scan_parquet(other / (name + '.parquet')) for name in io.TABLES}
            _replay_checks_disk(gates, actual, replay, workspace)
            other_report = io.read(other / 'report.json')
            if _substantive_report(report) != _substantive_report(other_report):
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
