'''Independent disk reconciliation, streaming comparison and complete acceptance evidence.'''

import json
from pathlib import Path

import polars as pl
import pytest
from test_acs_targets_independent_spill import classified_input, load

def gates(module):
    return {n: {'name': name, 'failures': []} for n, name in module.GROUPS.items()}


def rows(table):
    return pl.scan_parquet(table.paths, glob=False).collect()


def test_disk_calculation_all_products_matches_small_oracle(tmp_path, monkeypatch):
    module = load('reconcile_stage9')
    base, core, nodes, codes, usable = classified_input(module.calc)
    base = base.with_columns(pl.lit('work_migration_puma').alias('workplace_kind'))
    core = (base, *core[1:])
    mapping = tmp_path / 'mapping'
    mapping.mkdir()
    pl.DataFrame({'lookup': ['x']}).write_parquet(mapping / 'acs_code_lookup.parquet')
    source = {'acs/core': {'rows': 5}}
    monkeypatch.setattr(module.calc, 'prepare_sources', lambda *a: (core, source))
    monkeypatch.setattr(module.calc, 'semantic_frame', lambda *a: (base, codes, usable))
    counties = {'C': {'cbsa_id': None, 'cbsa_type': None}}
    # Unit boundaries use authored source semantics; public authentication is tested separately.
    monkeypatch.setattr(
        module,
        'reference_facts',
        lambda *a: (nodes, counties, {'P': [('C', 1.0)]}, mapping, mapping),
    )
    monkeypatch.setattr(module, 'expected_units', lambda *a: [])
    old = tmp_path / 'old'
    old.mkdir()
    expected, schemas, sources, registry, measurements = module.calculate(
        tmp_path, mapping, {}, {}, old
    )
    scratch = tmp_path / 'disk'
    scratch.mkdir()
    calculation = module._calculate_disk(tmp_path, mapping, {}, {}, scratch, batch_rows=7)
    assert calculation.schemas == schemas
    assert calculation.sources == sources
    assert calculation.registry == tuple(registry)
    assert tuple(calculation.tables) == module.io.TABLES
    for name, table in calculation.tables.items():
        frame = rows(table)
        oracle = pl.DataFrame(expected[name], schema=module._typed_schema(schemas[name]))
        assert frame.equals(oracle.sort(table.keys, nulls_last=False)), name
    assert [
        {k: v for k, v in row.items() if k != '_check_order'}
        for table in calculation.allocation_measurements
        for row in rows(table).iter_rows(named=True)
    ] == measurements
    for table in calculation.tables.values():
        for path in table.paths:
            assert pl.scan_parquet(path).select(pl.len()).collect().item() <= 7
    assert not list(calculation.owner.glob('work/*'))
    actual = {n: rows(t) for n, t in calculation.tables.items()}
    report = small_report(module, expected, actual, registry)
    oracle_gates, disk_gates = gates(module), gates(module)
    module.report_checks(oracle_gates, report, expected, actual, registry, sources)
    module._report_checks_disk(
        disk_gates,
        report,
        calculation,
        {n: f.lazy() for n, f in actual.items()},
        scratch,
        batch_rows=7,
    )
    assert disk_gates == oracle_gates
    from copy import deepcopy

    for kind in ('diagnostic', 'support', 'residual', 'count', 'tolerance', 'r37'):
        corrupted = deepcopy(report)
        if kind in ('diagnostic', 'support', 'residual'):
            name = {
                'diagnostic': 'diagnostic_partitions',
                'support': 'support_distributions',
                'residual': 'allocation_residuals',
            }[kind]
            field = 'n_min' if kind == 'support' else 'weighted_mass'
            corrupted[name][-1][field] += 1
        elif kind == 'count':
            corrupted['tables']['target_support']['rows'] += 1
        elif kind == 'tolerance':
            corrupted['allocation_conservation']['absolute_tolerance'] = 1.0
        else:
            item = next(
                r
                for r in reversed(corrupted['allocation_conservation']['measurements'])
                if r['replicate'] == 37
            )
            item['actual_mass'] += 1
        a, b = gates(module), gates(module)
        module.report_checks(a, corrupted, expected, actual, registry, sources)
        module._report_checks_disk(
            b,
            corrupted,
            calculation,
            {n: f.lazy() for n, f in actual.items()},
            scratch,
            batch_rows=1,
        )
        assert b == a, kind
        assert any(g['failures'] for g in b.values()), kind

    failed = tmp_path / 'failure'
    failed.mkdir()
    sentinel = failed / 'sentinel'
    sentinel.write_bytes(b'caller-owned')
    original_finalizer = module.calc._finalize_disk
    calls = 0
    with monkeypatch.context() as patch:

        def late_sink(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError('late calculation sink')
            return original_finalizer(*args, **kwargs)

        patch.setattr(module.calc, '_finalize_disk', late_sink)
        with pytest.raises(OSError, match='late calculation sink'):
            module._calculate_disk(tmp_path, mapping, {}, {}, failed, batch_rows=7)
    assert list(failed.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b'caller-owned'


@pytest.mark.parametrize('batch_rows', [1, 7])
@pytest.mark.parametrize('exact', [False, True])
def test_streamed_key_comparison_preserves_complete_oracle_failures(tmp_path, batch_rows, exact):
    module = load('reconcile_stage9')
    actual = [
        {'key': 'r2', 'value': 1.0, 'flags': ['x'], 'measure': 'forward_share'},
        {'key': None, 'value': 3.0, 'flags': None, 'measure': None},
        {'key': 'r10', 'value': 1.0, 'flags': [], 'measure': 'forward_share'},
        *[
            {'key': 'r2', 'value': float(n), 'flags': ['x'], 'measure': 'forward_share'}
            for n in range(2, 32)
        ],
        {'key': 'tail', 'value': float('inf'), 'flags': [], 'measure': None},
    ]
    expected = [
        {'key': 'r2', 'value': 1.0, 'flags': ['x'], 'measure': 'forward_share'},
        {'key': 'r10', 'value': 1.0 + 1e-13, 'flags': [], 'measure': 'forward_share'},
        {'key': 'r2', 'value': 31.0, 'flags': ['x'], 'measure': 'forward_share'},
        {'key': 'tail2', 'value': 0.0, 'flags': [], 'measure': None},
    ]
    oracle, streamed = gates(module), gates(module)
    module.compare_rows(oracle, 3, 'facts', actual, expected, ['key'], exact=exact)
    module._compare_fact_rows(
        streamed,
        3,
        'facts',
        pl.DataFrame(actual).lazy(),
        pl.DataFrame(expected).lazy(),
        ['key'],
        tmp_path,
        batch_rows=batch_rows,
        exact=exact,
    )
    assert streamed == oracle
    assert len(streamed[3]['failures']) > 25


@pytest.mark.parametrize('batch_rows', [1, 7])
def test_original_order_drains_both_tails_and_keeps_exact_values(batch_rows):
    module = load('reconcile_stage9')
    first = pl.DataFrame({'key': ['b', 'a'], 'value': [1.0, 2.0], 'flags': [None, ['x']]})
    for second, equal in [
        (first, True),
        (first.reverse(), False),
        (first.with_columns(pl.col('value') + 1e-13), False),
        (first.head(1), False),
        (first.head(0), False),
    ]:
        result = module._compare_original_order(first.lazy(), second.lazy(), batch_rows=batch_rows)
        assert result == {
            'schema_equal': True,
            'values_equal': equal,
            'first_rows': 2,
            'second_rows': second.height,
        }
    result = module._compare_original_order(
        first.lazy(),
        first.with_columns(pl.col('value').cast(pl.String)).lazy(),
        batch_rows=batch_rows,
    )
    assert not result['schema_equal'] and not result['values_equal']
    assert result['first_rows'] == result['second_rows'] == 2


def test_streamed_wrong_float_scalar_retains_cli_type_failure(tmp_path):
    module = load('reconcile_stage9')
    with pytest.raises(TypeError):
        module._compare_fact_rows(
            gates(module),
            3,
            'facts',
            pl.DataFrame({'key': ['a'], 'value': ['bad']}).lazy(),
            pl.DataFrame({'key': ['a'], 'value': [1.0]}).lazy(),
            ['key'],
            tmp_path,
        )


@pytest.mark.parametrize('bad_view', ['unexpected', None])
@pytest.mark.parametrize('replace', [False, True])
def test_unknown_view_routing_gap_and_independent_counts(tmp_path, bad_view, replace):
    module = load('reconcile_stage9')
    valid = pl.DataFrame({'view': ['observed'], 'key': ['a']})
    bad = pl.DataFrame({'view': [bad_view], 'key': ['a']}, schema=valid.schema)
    actual = bad if replace else pl.concat([valid, bad])
    # The former routing predicates omit this row entirely.
    routed = sum(
        actual.filter(pl.col('view').is_in(views)).height
        for views in (['observed'], ['canonical'], ['allocated_county', 'allocated_msa'])
    )
    assert routed == (0 if replace else 1)
    found = gates(module)
    module._check_table_domain_counts(
        found, 'target_support', actual.lazy(), valid.lazy(), ['key']
    )
    failures = found[2]['failures']
    assert any(f['check'] == 'unsupported support/replicate view' for f in failures)
    assert any(f['check'] == 'independent table row count differs' for f in failures) != replace
    assert failures[0]['key'] == ['a']


def small_report(module, expected, actual, registry):
    products = []
    for p in registry:
        pooled = [
            r
            for r in expected['target_support']
            if r['product_id'] == p['product_id']
            and r['component_year'] == 0
            and r['record_kind'] == 'cell'
        ]
        funnels = [
            r
            for r in expected['eligibility_diagnostics']
            if r['product_id'] == p['product_id'] and r['partition_kind'] == 'first_exclusion'
        ]
        targets = sum(r['point_status'] == 'defined' for r in pooled)
        products.append(
            {
                'product': p,
                'target_rows': targets,
                'supported_statistics': len(pooled),
                'empty_reason': None if targets else 'no_positive_eligible_supported_cells',
                'funnel_closure': [
                    {
                        'year': y,
                        'input_rows': sum(
                            r['n_unweighted'] for r in funnels if r['component_year'] == y
                        ),
                        'partition_rows': sum(
                            r['n_unweighted'] for r in funnels if r['component_year'] == y
                        ),
                    }
                    for y in sorted({r['component_year'] for r in funnels})
                ],
            }
        )
    measurements, counts = module.expected_conservation(expected, registry)
    import math

    return {
        'products': products,
        'tables': {
            n: {
                'rows': f.height,
                'columns': f.columns,
                'schema': {k: str(t) for k, t in f.schema.items()},
            }
            for n, f in actual.items()
        },
        'diagnostic_partitions': module.partition_rows(
            expected['eligibility_diagnostics'],
            [
                'product_id',
                'component_year',
                'partition_kind',
                'variable',
                'evidence_status',
                'reason',
            ],
            {
                'n_unweighted': lambda rs: sum(r['n_unweighted'] for r in rs),
                'weighted_mass': lambda rs: math.fsum(r['weighted_mass'] for r in rs),
            },
        ),
        'support_distributions': module.partition_rows(
            expected['target_support'],
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
                'n_min': lambda rs: min(r['n_unweighted'] for r in rs),
                'n_max': lambda rs: max(r['n_unweighted'] for r in rs),
            },
        ),
        'allocation_residuals': module.partition_rows(
            expected['allocation_residuals'],
            ['product_id', 'component_year', 'replicate', 'residual_type'],
            {
                n: lambda rs, name=n: math.fsum(r[name] for r in rs)
                for n in ['weighted_mass', 'fractional_support_mass']
            },
        ),
        'allocation_conservation': {
            'measurements': measurements,
            'products': counts,
            'serialized_check_count': len(measurements),
            'serialized_failure_count': 0,
            'absolute_tolerance': 1e-8,
            'relative_tolerance': 1e-12,
        },
    }


def test_public_reconcile_uses_disk_calculation_and_no_read_all():
    import ast

    module = load('reconcile_stage9')
    tree = ast.parse(Path(module.__file__).read_text())
    function = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'reconcile'
    )
    calls = [
        n.func.id
        for n in ast.walk(function)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    ]
    attrs = [
        n.func.attr
        for n in ast.walk(function)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    ]
    assert '_calculate_disk' in calls
    assert '_allocation_evidence_disk' in calls
    assert 'calculate' not in calls
    assert 'read_parquet' not in attrs and 'to_dicts' not in attrs


@pytest.fixture(autouse=True)
def external_access_guard(monkeypatch):
    from acs_mapping_fixtures import forbid_external_access
    from acs_target_fixtures import install_counted_guards

    counts = {'network': 0, 'environment_file': 0, 'live_client': 0}
    forbid_external_access(monkeypatch)
    install_counted_guards(monkeypatch, counts)
    yield
    assert not any(counts.values())


@pytest.mark.parametrize('name', ['target_support', 'replicate_estimates'])
def test_domain_validation_keeps_every_late_unknown_and_count_difference(tmp_path, name):
    module = load('reconcile_stage9')
    expected = pl.DataFrame({'view': ['observed'] * 29, 'key': list(range(29))})
    actual = expected.with_columns(
        pl.when(pl.col('key') >= 7).then(pl.lit('unknown')).otherwise(pl.col('view')).alias('view')
    )
    found = gates(module)
    module._check_table_domain_counts(
        found, name, actual.lazy(), expected.lazy(), ['key'], batch_rows=1
    )
    assert [f['key'] for f in found[2]['failures']] == [[i] for i in range(7, 29)]
    found = gates(module)
    module._check_table_domain_counts(
        found, name, expected.lazy(), pl.concat([expected, expected.tail(1)]).lazy(), ['key']
    )
    assert found[2]['failures'][0]['actual'] == 29
    assert found[2]['failures'][0]['expected'] == 30


@pytest.mark.parametrize('batch_rows', [1, 7])
def test_replay_classification_is_exact_and_report_excludes_only_top_level_identity(
    tmp_path, batch_rows
):
    module = load('reconcile_stage9')
    first = pl.DataFrame(
        {
            'unit_type': ['b', 'a'],
            'unit': ['2', '1'],
            'value': [1.0, 2.0],
            'se_method': ['sdr', None],
            'flags': [[], ['x']],
        }
    )
    for second, order_only in [
        (first.reverse(), True),
        (first.with_columns(pl.col('value') + 1e-13), False),
        (first.with_columns(pl.lit('changed').alias('se_method')), False),
        (first.with_columns(pl.lit(['new']).alias('flags')), False),
        (first.head(1), False),
    ]:
        found = gates(module)
        module._replay_checks_disk(
            found,
            {'target_units': first.lazy()},
            {'target_units': second.lazy()},
            tmp_path,
            batch_rows=batch_rows,
        )
        failures = found[6]['failures']
        assert failures
        assert any(f['check'] == 'exact replay row order differs' for f in failures) == order_only
    a = {'run_id': 'first', 'created_at': 'then', 'nested': {'run_id': 'first'}}
    b = dict(a, run_id='second', created_at='now')
    assert module._substantive_report(a) == module._substantive_report(b)
    b['nested'] = {'run_id': 'second'}
    assert module._substantive_report(a) != module._substantive_report(b)


def test_report_complete_fsum_groups_and_39_digit_native_text(tmp_path):
    from decimal import Decimal

    module = load('reconcile_stage9')
    observed = next(
        p for p in module.calc.products() if p['view'] == 'observed' and p['family'] == 'area_mix'
    )
    match = ('dimension', 'base_universe', 'evidence_policy', 'years')
    county, metro = [
        next(
            p
            for p in module.calc.products()
            if p['view'] == v and all(p[k] == observed[k] for k in match)
        )
        for v in ('allocated_county', 'allocated_msa')
    ]
    expected = {n: [] for n in module.io.TABLES}
    raw = '123456789012345678901234567890123456789.123456789'
    for product in (observed, county, metro):
        for code, weight in [('x', raw), ('y', '0.000000001')]:
            native = product['view'] == 'observed'
            expected['target_support'].append(
                {
                    'family': 'area_mix',
                    'measure': 'annual_average_total',
                    'record_kind': 'cell',
                    'product_id': product['product_id'],
                    'view': product['view'],
                    'component_year': 0,
                    'pool_divisor': 2,
                    'cell_weight_sum_exact': weight if native else None,
                    'cell_mass': float(Decimal(weight)) / 2,
                    **dict(zip(module.calc.PAIR, ['a', 'A', 'b', code], strict=True)),
                }
            )
        expected['replicate_estimates'].append(
            {
                'family': 'area_mix',
                'measure': 'annual_average_total',
                'product_id': product['product_id'],
                'view': product['view'],
                'replicate': 37,
                'pool_divisor': 2,
                'numerator_sum_exact': raw if product == observed else None,
                'numerator': float(Decimal(raw)) / 2,
                **dict(zip(module.calc.PAIR, ['a', 'A', 'b', 'x'], strict=True)),
            }
        )
    for kind, mass in [('micropolitan', 1e16), ('no_cbsa', -1e16)]:
        expected['allocation_residuals'].append(
            {
                'product_id': metro['product_id'],
                'component_year': 0,
                'replicate': 37,
                'residual_type': kind,
                'weighted_mass': mass,
                'workplace_unit_type': 'p',
                'workplace_unit': 'P',
                'code_unit_type': 'b',
                'code_unit': 'x',
            }
        )
    tables = {}
    for name in ['target_support', 'replicate_estimates', 'allocation_residuals']:
        frame = pl.DataFrame(expected[name], infer_schema_length=None)
        path = tmp_path / (name + '.parquet')
        frame.write_parquet(path)
        tables[name] = module.calc._FactTable(tmp_path, (path,), frame.schema, (), '', None)
    calculation = module._DiskCalculation(tmp_path, tables, {}, {}, (observed, county, metro), ())
    oracle = module.expected_conservation(expected, calculation.registry)
    assert module._report_conservation_disk(calculation, tmp_path, 1) == oracle
    assert oracle[0][0]['native_weight_sum_exact'].endswith('.12345679')
    frame = pl.DataFrame({'key': ['a'] * 3, 'mass': [1e16, 1.0, -1e16]})
    for batch in (1, 7):
        owner = tmp_path / str(batch)
        owner.mkdir()
        summary = module._partition_disk(
            frame.lazy(),
            ['key'],
            [('mass', pl.Float64, __import__('math').fsum, 'mass')],
            owner,
            'sum',
            batch,
        )
        assert rows(summary)['mass'].item() == 1.0


def test_comparison_missing_nonkey_fields_nonfinite_and_duplicate_encounter_order(tmp_path):
    module = load('reconcile_stage9')
    actual = [
        {'key': k, 'v': v}
        for k, v in [('z', 0.0), ('a', 0.0), ('z', float('nan')), ('a', float('inf')), ('z', 2.0)]
    ]
    expected = [
        {'key': 'a', 'v': float('inf'), 'missing': None},
        {'key': 'z', 'v': 2.0, 'missing': None},
    ]
    oracle, streamed = gates(module), gates(module)
    module.compare_rows(oracle, 3, 'facts', actual, expected, ['key'])
    module._compare_fact_rows(
        streamed,
        3,
        'facts',
        pl.DataFrame(actual).lazy(),
        pl.DataFrame(expected).lazy(),
        ['key'],
        tmp_path,
        batch_rows=1,
    )
    assert streamed == oracle
    assert [f['key'] for f in streamed[3]['failures'][:3]] == [['z'], ['a'], ['z']]


def test_streams_and_duplicate_ledgers_are_bounded_and_fully_drained(tmp_path, monkeypatch):
    module = load('reconcile_stage9')
    actual = pl.DataFrame({'key': ['a', 'b'] * 63 + ['z'], 'value': list(range(127))})
    expected = pl.DataFrame({'key': ['a', 'b', 'zz'], 'value': [124, 125, 128]})
    original_append, original_rows = module.calc._FactWriter.append, module.calc._rows
    seen, max_buffer = {}, []

    def append(writer, row):
        original_append(writer, row)
        max_buffer.append(len(writer.rows))
        assert len(writer.rows) < writer.batch_rows

    def stream(frame, batch):
        for row in original_rows(frame, batch):
            if '__independent_ordinal' in row:
                key = tuple(frame.collect_schema().names())
                seen[key] = seen.get(key, 0) + 1
            yield row

    def forbidden(*args, **kwargs):
        pytest.fail('whole-frame conversion is forbidden during comparison')

    monkeypatch.setattr(module.calc._FactWriter, 'append', append)
    monkeypatch.setattr(module.calc, '_rows', stream)
    monkeypatch.setattr(pl.DataFrame, 'to_dicts', forbidden)
    found = gates(module)
    module._compare_fact_rows(
        found, 3, 'facts', actual.lazy(), expected.lazy(), ['key'], tmp_path, batch_rows=7
    )
    assert sum(seen.values()) == 130
    assert max(max_buffer) <= 6
    assert sum('duplicate' in f['check'] for f in found[3]['failures']) == 124
    assert [f['key'] for f in found[3]['failures'][-2:]] == [['z'], ['zz']]
    assert not list(tmp_path.iterdir())


def test_original_replay_aligns_unequal_physical_chunks_and_drains_schema_mismatch():
    module = load('reconcile_stage9')
    frame = pl.DataFrame({'value': [1, 2, 3, 4], 'flags': [None, [], ['x'], []]})

    class Physical:
        def __init__(self, chunks):
            self.chunks, self.visited = chunks, 0

        def collect_schema(self):
            return self.chunks[0].schema

        def collect_batches(self, **kwargs):
            for chunk in self.chunks:
                self.visited += 1
                yield chunk

    first = Physical([frame.head(1), frame.slice(1)])
    second = Physical([frame.head(3), frame.tail(1)])
    assert module._compare_original_order(first, second)['values_equal']
    assert first.visited == second.visited == 2
    second = Physical(
        [
            frame.head(1).with_columns(pl.col('value').cast(pl.String)),
            frame.slice(1).with_columns(pl.col('value').cast(pl.String)),
        ]
    )
    result = module._compare_original_order(first, second)
    assert not result['schema_equal'] and result['first_rows'] == result['second_rows'] == 4
    assert second.visited == 2


def test_genuine_disk_oracle_lifetimes_unknown_views_and_late_drift(tmp_path, monkeypatch):
    import hashlib
    import shutil
    from dataclasses import asdict

    from acs_target_fixtures import run_acs_target_v12

    module = load('reconcile_stage9')
    data = tmp_path / 'data'
    controls = data / 'derived/acs/independent-controls'
    captured, lifetime = {}, {'calculate': 0, 'report': 0, 'replay': 0, 'preservation': 0}
    historical = data / 'derived/acs/targets/historical-failed.scratch/evidence.csv'

    def before(fixture):
        historical.parent.mkdir(parents=True)
        historical.write_bytes(b'historical scratch is protected\n')
        captured.update(
            module.freeze(
                data,
                controls,
                mapping_run=fixture['mapping_run'],
                mapping_outputs_sha256=fixture['mapping_pin'],
                request=asdict(fixture['request']),
                first_run='first',
                replay_run='replay',
            )
        )

    fixture = run_acs_target_v12(data, monkeypatch, before_targets=before)
    frozen = json.loads((controls / 'freeze.json').read_bytes())
    mapping = data / 'derived/acs/mapping/mapping'
    freeze_pin = captured['freeze_sha256']
    original_calculate, original_report = module._calculate_disk, module._report_checks_disk
    original_replay, original_preservation = module._replay_checks_disk, module.preservation
    owners = []

    def calculate(*args, **kwargs):
        result = original_calculate(*args, **kwargs)
        owners.append(result.owner)
        if lifetime['calculate'] == 0:
            oracle_dir = args[4] / 'small-oracle'
            oracle_dir.mkdir()
            expected, schemas, sources, registry, measurements = module.calculate(
                data, mapping, frozen['mapping_inputs'], frozen, oracle_dir
            )
            assert len(registry) == 50
            assert result.schemas == schemas and result.sources == sources
            for name, table in result.tables.items():
                oracle = pl.DataFrame(expected[name], schema=module._typed_schema(schemas[name]))
                assert rows(table).equals(oracle.sort(table.keys, nulls_last=False)), name
            assert [
                {k: v for k, v in r.items() if k != '_check_order'}
                for table in result.allocation_measurements
                for r in rows(table).iter_rows(named=True)
            ] == measurements
            shutil.rmtree(oracle_dir)
        # Every source-dependent plan must already be drained when the descriptor returns.
        for csv in result.owner.glob('*.csv'):
            csv.unlink()
        lifetime['calculate'] += 1
        return result

    def report(g, value, calculation, actual, workspace, **kwargs):
        assert calculation.owner.exists() and all(
            p.exists() for t in calculation.tables.values() for p in t.paths
        )
        lifetime['report'] += 1
        return original_report(g, value, calculation, actual, workspace, **kwargs)

    def replay(*args, **kwargs):
        assert owners[-1].exists()
        lifetime['replay'] += 1
        return original_replay(*args, **kwargs)

    def preservation(*args, **kwargs):
        assert not list(controls.parent.glob('stage9-independent-*'))
        lifetime['preservation'] += 1
        return original_preservation(*args, **kwargs)

    monkeypatch.setattr(module, '_calculate_disk', calculate)
    monkeypatch.setattr(module, '_report_checks_disk', report)
    monkeypatch.setattr(module, '_replay_checks_disk', replay)
    monkeypatch.setattr(module, 'preservation', preservation)

    def reconcile():
        pin = hashlib.sha256((fixture['first'] / 'outputs.json').read_bytes()).hexdigest()
        return module.reconcile(data, 'first', pin, controls, expected_freeze_sha256=freeze_pin)

    result = reconcile()
    assert result['failure_count'] == 0, result
    assert all(g['status'] == 'pass' for g in result['gates'].values())
    assert lifetime == {'calculate': 1, 'report': 1, 'replay': 1, 'preservation': 2}
    assert all(not p.exists() for p in owners)
    # External pins are checked before any malformed control/bundle JSON is parsed.
    for file, target_pin, freeze_value in [
        (fixture['first'] / 'inputs.json', '0' * 64, freeze_pin),
        (
            controls / 'freeze.json',
            hashlib.sha256((fixture['first'] / 'outputs.json').read_bytes()).hexdigest(),
            '0' * 64,
        ),
    ]:
        saved = file.read_bytes()
        file.write_bytes(b'{')
        try:
            with pytest.raises(ValueError, match='pin'):
                module.reconcile(
                    data, 'first', target_pin, controls, expected_freeze_sha256=freeze_value
                )
        finally:
            file.write_bytes(saved)
    from embedding_data import acs_target_bundle

    def forbidden(*a, **kw):
        pytest.fail('production verification is unavailable during independent mutation checks')

    monkeypatch.setattr(acs_target_bundle, 'verify_bundle', forbidden)
    for table in ('target_support', 'replicate_estimates'):
        for bad_view, replace in [('unexpected', False), (None, False), ('unexpected', True)]:
            saved = {}
            try:
                for run in ('first', 'replay'):
                    bundle = fixture[run]
                    files = [
                        bundle / (table + '.parquet'),
                        bundle / 'report.json',
                        bundle / 'outputs.json',
                    ]
                    saved.update({p: p.read_bytes() for p in files})
                    frame = pl.read_parquet(files[0])
                    bad = frame.tail(1).with_columns(
                        pl.lit(bad_view, dtype=pl.String).alias('view')
                    )
                    changed = (
                        pl.concat([frame.head(frame.height - 1), bad])
                        if replace
                        else pl.concat([frame, bad])
                    )
                    changed.write_parquet(files[0])
                    value = json.loads(saved[files[1]])
                    value['tables'][table]['rows'] = changed.height
                    files[1].write_text(json.dumps(value))
                    inventory = json.loads(saved[files[2]])
                    for file in files[:2]:
                        inventory[file.name].update(module.io.record(file))
                        if file.suffix == '.parquet':
                            serialized = pl.scan_parquet(file)
                            schema = serialized.collect_schema()
                            inventory[file.name].update(
                                rows=serialized.select(pl.len()).collect().item(),
                                columns=schema.names(),
                                schema={n: str(t) for n, t in schema.items()},
                            )
                    files[2].write_text(json.dumps(inventory))
                result = reconcile()
                failures = result['gates'][2]['failures']
                assert any(f['check'] == 'unsupported support/replicate view' for f in failures)
                assert (
                    any(f['check'] == 'independent table row count differs' for f in failures)
                    != replace
                )
                if replace:
                    assert any(
                        f['check'] == table + ': key set differs'
                        for g in (3, 4, 5)
                        for f in result['gates'][g]['failures']
                    )
                assert not result['gates'][6]['failures'], result['gates'][6]
            finally:
                for file, content in saved.items():
                    file.write_bytes(content)
    original = data / frozen['mapping_inputs']['sources']['acs/core']['parquet']
    before_bytes = original.read_bytes()
    with monkeypatch.context() as patch:

        def drift(*args, **kwargs):
            report(*args, **kwargs)
            original.write_bytes(before_bytes + b' ')

        patch.setattr(module, '_report_checks_disk', drift)
        try:
            with pytest.raises(ValueError, match='protected'):
                reconcile()
        finally:
            original.write_bytes(before_bytes)
    with monkeypatch.context() as patch:

        def late_failure(*args, **kwargs):
            assert owners[-1].exists()
            raise ValueError('late replay failure')

        patch.setattr(module, '_replay_checks_disk', late_failure)
        with pytest.raises(ValueError, match='late replay failure'):
            reconcile()
    original_software = module.io.software
    with monkeypatch.context() as patch:
        changed = original_software() | {'injected_software_drift': True}
        patch.setattr(module.io, 'software', lambda: changed)
        with pytest.raises(ValueError, match='software changed'):
            reconcile()
    with monkeypatch.context() as patch:

        def software_drift(*args, **kwargs):
            report(*args, **kwargs)
            changed = original_software() | {'injected_software_drift': True}
            patch.setattr(module.io, 'software', lambda: changed)

        patch.setattr(module, '_report_checks_disk', software_drift)
        with pytest.raises(ValueError, match='software changed'):
            reconcile()
    assert all(not p.exists() for p in owners)
    assert historical.read_bytes() == b'historical scratch is protected\n'
    leftover = controls.parent / 'unaccounted.csv'
    leftover.write_bytes(b'not an excluded scratch artifact\n')
    with pytest.raises(ValueError, match='unaccounted'):
        original_preservation(data, controls, expected_freeze_sha256=freeze_pin)
    leftover.unlink()
    assert (
        original_preservation(data, controls, expected_freeze_sha256=freeze_pin)['failure_count']
        == 0
    )


def test_missing_report_key_is_a_coherent_cli_key_failure(tmp_path):
    module = load('reconcile_stage9')
    with pytest.raises(KeyError, match='key'):
        module._compare_fact_rows(
            gates(module),
            6,
            'summary',
            pl.DataFrame({'value': [1]}).lazy(),
            pl.DataFrame({'key': ['a'], 'value': [1]}).lazy(),
            ['key'],
            tmp_path,
        )


@pytest.mark.parametrize('batch_rows', [1, 7])
def test_failed_allocation_measurements_retain_every_record_and_exit1(
    tmp_path, capsys, batch_rows
):
    import typer

    module = load('reconcile_stage9')
    schema = pl.Schema(
        {
            'product_id': pl.String,
            'code_unit_type': pl.String,
            'code_unit': pl.String,
            'component_year': pl.Int64,
            'replicate': pl.UInt8,
            'check': pl.String,
            'expected_mass': pl.Float64,
            'actual_mass': pl.Float64,
            'status': pl.String,
            '_check_order': pl.UInt8,
        }
    )
    descriptors, expected = [], []
    for product_id in ('first-product', 'second-product'):
        authored = [
            {
                'product_id': product_id,
                'code_unit_type': 'category',
                'code_unit': 'X',
                'component_year': 0,
                'replicate': replicate,
                'check': label,
                'expected_mass': 1.0,
                'actual_mass': 1.0 if replicate == 0 else 2.0,
                'status': 'pass' if replicate == 0 else 'fail',
                '_check_order': order,
            }
            for replicate in (0, 37, 80)
            for order, label in enumerate(('native_to_county', 'county_to_msa_and_residuals'))
        ]
        paths = []
        for index in range(0, len(authored), batch_rows):
            path = tmp_path / f'{product_id}-{index}.parquet'
            pl.DataFrame(authored[index : index + batch_rows], schema=schema).write_parquet(path)
            paths.append(path)
        descriptors.append(
            module.calc._FactTable(
                tmp_path,
                tuple(paths),
                schema,
                ('replicate', '_check_order'),
                product_id,
                None,
            )
        )
        expected.extend({k: v for k, v in r.items() if k != '_check_order'} for r in authored)
    found = gates(module)
    actual = module._allocation_evidence_disk(found, tuple(descriptors), batch_rows=batch_rows)
    assert actual == expected
    failed = [r for r in expected if r['status'] != 'pass']
    assert len(failed) == 8
    assert found[5]['failures'] == [
        {'check': 'independent annual/pooled full/all80 conservation failed', 'measurement': r}
        for r in failed
    ]
    for group in found.values():
        group['failure_count'] = len(group['failures'])
        group['status'] = 'fail' if group['failures'] else 'pass'
    result = {'gates': found, 'failure_count': len(failed)}
    with pytest.raises(typer.Exit) as error:
        module.emit(lambda: result)
    assert error.value.exit_code == 1
    assert json.loads(capsys.readouterr().out)['gates']['5']['failures'] == found[5]['failures']
