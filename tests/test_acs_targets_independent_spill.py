'''Disk-native independent arithmetic; expectations use only independent small oracles.'''

import ast
import builtins
import importlib.util
import socket
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def guarded_external_access(monkeypatch):
    original_import, original_open = builtins.__import__, Path.open

    def guarded_import(name, *args, **kwargs):
        assert not (name == 'embedding_data' or name.startswith('embedding_data.'))
        return original_import(name, *args, **kwargs)

    def guarded_open(path, *args, **kwargs):
        assert path.name != '.env', 'environment-file access is forbidden'
        return original_open(path, *args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError('network access is forbidden')

    monkeypatch.setattr(builtins, '__import__', guarded_import)
    monkeypatch.setattr(Path, 'open', guarded_open)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)


@pytest.fixture
def calc():
    return load('stage9_independent_estimates')


def product(calc, view='observed'):
    return next(
        p for p in calc.products() if p['view'] == view and p['family'] == 'staffing_pattern'
    )


def typed_schemas():
    reconcile = load('reconcile_stage9')

    def dtype(text):
        return pl.List(dtype(text[5:-1])) if text.startswith('List(') else getattr(pl, text)

    declared = reconcile.schemas({})
    return {
        name: pl.Schema({k: dtype(v) for k, v in declared[source].items()})
        for name, source in [
            ('targets', 'targets_observed'),
            ('target_support', 'target_support'),
            ('replicate_estimates', 'replicate_estimates'),
            ('diagnostics', 'eligibility_diagnostics'),
        ]
    }


def annual_frame(calc):
    rows = []
    for a, b, year, weight in [
        ('A', 'x', 2023, '3.5'),
        ('A', 'y', 2024, '2.5'),
        ('B', 'z', 2023, '0'),
    ]:
        rows.append(
            dict(zip(calc.PAIR, ['a', a, 'b', b], strict=True))
            | {
                'YEAR': year,
                '_flags': ['size_gate_pending', str(year)],
                **{w: Decimal(weight) for w in calc.WEIGHTS},
            }
        )
    schema = {
        **dict.fromkeys(calc.PAIR, pl.String),
        'YEAR': pl.Int64,
        '_flags': pl.List(pl.String),
        **dict.fromkeys(calc.WEIGHTS, pl.Decimal(38, 2)),
    }
    return pl.DataFrame(rows, schema=schema).lazy()


def read(table):
    return pl.concat([pl.read_parquet(p) for p in table.paths])


def decode(calc, table):
    return {
        tuple(row[k] for k in table.keys): {
            'weights': [
                Decimal(v) if table.weight_kind == 'decimal_text' else v for v in row['weights']
            ],
            'n': row['n'],
            'fraction': row['fraction'],
            'flags': set(row['flags']),
        }
        for row in read(table).iter_rows(named=True)
    }


@pytest.mark.parametrize('batch_rows', [1, 3, 128])
def test_annual_completion_denominators_and_finalization_match_oracles(calc, tmp_path, batch_rows):
    p = product(calc)
    frame = annual_frame(calc)
    expected = calc.complete_components(calc.aggregate(frame), p)
    cells = calc._complete_native_facts(frame, p, tmp_path, batch_rows=batch_rows)
    assert decode(calc, cells) == expected
    denominators = calc._denominator_facts(cells, p, tmp_path, batch_rows=batch_rows)
    assert decode(calc, denominators) == calc.denominator_groups(expected)
    schemas = typed_schemas()
    output = calc._finalize_disk(
        cells, denominators, None, p, tmp_path, schemas=schemas, batch_rows=batch_rows
    )
    old = calc.finalize(expected, {}, p)
    for name, rows in zip(('target_support', 'replicate_estimates', 'targets'), old, strict=True):
        actual = read(output[name])
        expected_frame = pl.DataFrame(rows, schema=schemas[name]).sort(
            output[name].keys, nulls_last=False
        )
        assert actual.schema == schemas[name]
        assert actual.equals(expected_frame)


def classified_input(calc):
    rows = []
    for a, b, year, mass, industry, occupation in [
        ('A', 'x', 2023, '3.50', 'i:A', 'o:x'),
        ('A', 'y', 2024, '2.50', 'i:A', None),
        ('A', 'z', 2023, '1.25', 'i:A', 'o:z'),
        ('B', 'y', 2024, '4.00', 'i:B', None),
        ('C', 'y', 2023, '7.00', None, 'o:y'),
    ]:
        rows.append(
            {
                'YEAR': year,
                'acs_component_year': year,
                'acs_sample_id': f'us{year}a',
                'EMPSTATD': '10',
                'CLASSWKRD': '22',
                'OCCSOC': '559830',
                'INDNAICS': '123456',
                'TRANWORK': '10',
                'MIGRATE1': '2',
                'industry_kind': 'industry',
                'industry_unit': a,
                'occupation_kind': 'occupation',
                'occupation_unit': b,
                'industry_canonical_scalar_node_id': industry,
                'occupation_canonical_scalar_node_id': occupation,
                'industry_flag_vintage_crosswalk': False,
                'occupation_flag_vintage_crosswalk': b == 'z',
                'limitation_flag': a == 'B',
                **{
                    role + suffix: value
                    for role in ('residence', 'workplace', 'migration')
                    for suffix, value in [
                        ('_kind', 'puma'),
                        ('_unit', 'P'),
                        ('_area_status', 'applicable'),
                    ]
                },
                **{q: '0' for q in calc.QFIELDS},
                **{'_q_' + q: 'nonallocation' for q in calc.QFIELDS},
                **{w: Decimal(mass) for w in calc.WEIGHTS},
            }
        )
    frame = pl.DataFrame(rows, schema_overrides={w: pl.Decimal(38, 2) for w in calc.WEIGHTS})
    core = (
        frame.lazy(),
        frame.schema,
        {},
        {'delivery_id': 'synthetic', 'parquet_record': {'sha256': 'a' * 64}},
        {'path': 'synthetic-ddi.xml'},
    )

    def codes(name, values):
        return pl.col(name).is_in(values).fill_null(False)

    usable = dict.fromkeys(('industry', 'occupation'), pl.lit(True))
    nodes = {'industry': ['i:A', 'i:B'], 'occupation': ['o:x', 'o:z', 'o:y']}
    return frame.lazy(), core, nodes, codes, usable


@pytest.mark.parametrize('view', ['observed', 'canonical'])
@pytest.mark.parametrize('batch_rows', [1, 3, 128])
def test_expected_native_disk_complete_cells_coverage_and_every_diagnostic(
    calc,
    tmp_path,
    view,
    batch_rows,
):
    p = product(calc, view)
    base, core, nodes, codes, usable = classified_input(calc)
    expected, coverage, diagnostics = calc.expected_native(base, core, p, nodes, codes, usable)
    schemas = typed_schemas()
    facts = calc._expected_native_disk(
        base,
        core,
        p,
        nodes,
        codes,
        usable,
        tmp_path,
        diagnostic_schema=schemas['diagnostics'],
        batch_rows=batch_rows,
    )
    assert decode(calc, facts.cells) == expected
    assert decode(calc, facts.denominators) == calc.denominator_groups(expected)
    assert (decode(calc, facts.coverage) if facts.coverage else {}) == coverage
    assert read(facts.diagnostics).equals(
        pl.DataFrame(diagnostics, schema=schemas['diagnostics']).sort(
            calc.DIAG_KEY, nulls_last=False
        )
    )
    if view == 'canonical':
        assert ('naics_national_industry', 'i:B', 2024) in coverage
        assert not any(key[1] == 'i:B' for key in expected)
        assert {d['reason'] for d in diagnostics if d['partition_kind'] == 'coverage'} == {
            'canonical_denominator_loss',
            'canonical_unsupported_or_policy_excluded',
        }
    assert {r['variable'] for r in diagnostics if r['partition_kind'] == 'evidence'} == set(
        calc.QFIELDS
    )


def fact_fixture(calc, tmp_path, p, values, *, pair=True, kind=None, label='fixture', rows=1):
    kind = kind or ('float64' if p['view'].startswith('allocated') else 'decimal_text')
    owner = tmp_path / label
    owner.mkdir()
    keys = [*(calc.PAIR if pair else calc.PAIR[:2]), 'component_year']
    schema = calc._fact_schema(calc.PAIR if pair else calc.PAIR[:2], kind)
    paths = []
    source = [calc._fact_row(keys, key, value, kind) for key, value in sorted(values.items())]
    for offset in range(0, len(source), rows):
        path = owner / f'{offset}.parquet'
        pl.DataFrame(source[offset : offset + rows], schema=schema).write_parquet(
            path, row_group_size=1
        )
        paths.append(path)
    if not paths:
        path = owner / 'empty.parquet'
        pl.DataFrame(schema=schema).write_parquet(path)
        paths.append(path)
    return calc._FactTable(owner, tuple(paths), schema, tuple(keys), p['product_id'], kind)


def value(weights, n=1, fraction=1.0, flags=()):
    return {'weights': list(weights), 'n': n, 'fraction': fraction, 'flags': set(flags)}


def test_statuses_once_per_a_and_denominator_only_coverage_drained(calc, tmp_path):
    p = product(calc)
    annual = {
        ('a', a, 'b', b, 2023): value([Decimal(0)] + [Decimal(1)] * 80)
        for a, b in [('A', 'x'), ('A', 'y'), ('B', 'z')]
    }
    cells = calc.complete_components(annual, p)
    den = calc.denominator_groups(cells)
    den.update({('a', 'C', year): value([Decimal(0)] * 81) for year in [0, *p['years']]})
    den.update({('a', 'D', year): value([Decimal(1)] * 81) for year in [0, *p['years']]})
    c = fact_fixture(calc, tmp_path, p, cells, label='cells')
    d = fact_fixture(calc, tmp_path, p, den, pair=False, label='den')
    output = calc._finalize_disk(c, d, None, p, tmp_path, schemas=typed_schemas(), batch_rows=1)
    statuses = read(output['target_support']).filter(pl.col('record_kind') == 'denominator_status')
    assert statuses.select('unit_a', 'component_year').rows() == [
        ('A', 0),
        ('A', 2023),
        ('B', 0),
        ('B', 2023),
        ('C', 0),
        ('C', 2023),
        ('C', 2024),
    ]
    assert read(output['targets']).is_empty()
    assert read(output['replicate_estimates']).height == 480


def test_39_digit_pool_and_heterogeneous_weight_scales_are_exact(calc, tmp_path):
    p = product(calc)
    wide = Decimal('9' * 38)
    frame = pl.DataFrame(
        {
            **{k: ['a', 'a'] for k in calc.PAIR},
            'YEAR': [2023, 2024],
            '_flags': [[], []],
            **{
                w: [wide, wide]
                if i == 0
                else [Decimal('1.2300'), Decimal('-0.0000')]
                if i % 2
                else [Decimal('.01'), Decimal('.02')]
                for i, w in enumerate(calc.WEIGHTS)
            },
        },
        schema_overrides={
            **{'_flags': pl.List(pl.String)},
            **{
                w: pl.Decimal(38, 0 if i == 0 else 4 if i % 2 else 2)
                for i, w in enumerate(calc.WEIGHTS)
            },
        },
    ).lazy()
    expected = calc.complete_components(calc.aggregate(frame), p)
    cells = calc._complete_native_facts(frame, p, tmp_path, batch_rows=1)
    assert decode(calc, cells) == expected
    pooled = read(cells).filter(pl.col('component_year') == 0).row(0, named=True)
    assert pooled['weights'][0] == '199999999999999999999999999999999999998'
    assert pooled['weights'][1:3] == ['1.23', '0.03']
    den = calc._denominator_facts(cells, p, tmp_path, batch_rows=1)
    assert decode(calc, den) == calc.denominator_groups(expected)


@pytest.mark.parametrize('empty', [False, True])
def test_float64_adapter_preserves_exact_order_and_null_exact_fields(calc, tmp_path, empty):
    p = next(p for p in calc.products() if p['view'] == 'allocated_county')
    cells = (
        {}
        if empty
        else {
            ('county', 'A', 'b', b, year): value([mass] * 81, fraction=fraction)
            for b, mass, fraction in [('x', 1e16, 1e16), ('y', -1e16, 1.0), ('z', 1.0, 1.0)]
            for year in [0, *p['years']]
        }
    )
    facts = fact_fixture(calc, tmp_path, p, cells)
    den = calc._denominator_facts(facts, p, tmp_path, batch_rows=1)
    assert decode(calc, den) == calc.denominator_groups(cells, True)
    result = calc._finalize_disk(
        facts, den, None, p, tmp_path, schemas=typed_schemas(), batch_rows=1
    )
    for name, rows in zip(
        ('target_support', 'replicate_estimates', 'targets'),
        calc.finalize(cells, {}, p),
        strict=True,
    ):
        assert read(result[name]).equals(
            pl.DataFrame(rows, schema=typed_schemas()[name]).sort(
                result[name].keys, nulls_last=False
            )
        )
    if not empty:
        assert read(result['replicate_estimates'])['numerator_sum_exact'].null_count() == 480


@pytest.mark.parametrize(
    'corruption',
    [
        'duplicate',
        'order',
        'missing',
        'null',
        'vector',
        'year',
        'weight_kind',
        'product',
        'schema',
        'decimal',
        'flags',
    ],
)
def test_malformed_component_facts_fail_and_owned_output_is_removed(calc, tmp_path, corruption):
    p = product(calc)
    cells = calc.complete_components(calc.aggregate(annual_frame(calc)), p)
    table = fact_fixture(calc, tmp_path, p, cells, rows=2)
    if corruption == 'weight_kind':
        table = table._replace(weight_kind='float64')
    elif corruption == 'product':
        table = table._replace(product_id='wrong')
    elif corruption == 'schema':
        table = table._replace(keys=('wrong',))
    else:
        path = table.paths[-1]
        frame = pl.read_parquet(path)
        if corruption == 'duplicate':
            table = table._replace(paths=(*table.paths, path))
        elif corruption == 'order':
            table = table._replace(paths=tuple(reversed(table.paths)))
        elif corruption == 'missing':
            frame = frame.head(frame.height - 1)
        elif corruption == 'null':
            frame = frame.with_columns(pl.lit(None, pl.String).alias('unit_a'))
        elif corruption == 'vector':
            frame = frame.with_columns(pl.lit(['1'], pl.List(pl.String)).alias('weights'))
        elif corruption == 'year':
            frame = frame.with_columns(pl.lit(2025, pl.Int64).alias('component_year'))
        elif corruption == 'decimal':
            frame = frame.with_columns(pl.lit(['NaN'] * 81, pl.List(pl.String)).alias('weights'))
        elif corruption == 'flags':
            frame = frame.with_columns(pl.lit(['z', 'a'], pl.List(pl.String)).alias('flags'))
        frame.write_parquet(path)
    sentinel = tmp_path / 'sentinel'
    sentinel.write_text('keep')
    with pytest.raises(ValueError):
        calc._denominator_facts(table, p, tmp_path, batch_rows=1)
    assert not (tmp_path / 'independent-denominators').exists()
    assert sentinel.read_text() == 'keep'
    assert table.owner.exists()


@pytest.mark.parametrize('corruption', ['duplicate', 'null', 'order', 'year'])
def test_bad_annual_rows_reject_without_unbounded_carry(calc, corruption):
    p = product(calc)
    annual = list(calc.aggregate(annual_frame(calc)).items())
    rows = [
        dict(zip([*calc.PAIR, 'YEAR'], key, strict=True))
        | {
            '_n': item['n'],
            '_flags': sorted(item['flags']),
            **dict(zip(calc.WEIGHTS, item['weights'], strict=True)),
        }
        for key, item in sorted(annual)
    ]
    if corruption == 'duplicate':
        rows.insert(1, rows[0])
    elif corruption == 'null':
        rows[0]['unit_a'] = None
    elif corruption == 'order':
        rows.reverse()
    else:
        rows[-1]['YEAR'] = 2025
    with pytest.raises(ValueError):
        list(calc._complete_annual_rows(iter(rows), p))


@pytest.mark.parametrize('one_year', [False, True])
def test_handwritten_signed_replicates_sdr_and_all_annual_statuses(calc, tmp_path, one_year):
    p = next(
        p
        for p in calc.products()
        if p['view'] == 'observed'
        and (
            (p['family'] == 'migration_flow' and p['years'] == [2024])
            if one_year
            else p['family'] == 'staffing_pattern'
        )
    )
    year = p['years'][0]
    x = [Decimal(3)] + [Decimal(4)] * 80
    y = [Decimal(1)] + [Decimal(2)] * 80
    x[37], y[37], x[38], y[38] = Decimal(-1), Decimal(2), Decimal(0), Decimal(0)
    annual = {
        ('a', 'A', 'b', 'x', year): value(x, flags=['x']),
        ('a', 'A', 'b', 'y', year): value(y, flags=['y']),
    }
    cells = calc.complete_components(annual, p)
    table = fact_fixture(calc, tmp_path, p, cells)
    den = calc._denominator_facts(table, p, tmp_path, batch_rows=1)
    result = calc._finalize_disk(
        table, den, None, p, tmp_path, schemas=typed_schemas(), batch_rows=3
    )
    targets = read(result['targets'])
    total = targets.filter(
        (pl.col('unit_b') == 'x') & (pl.col('measure') == 'annual_average_total')
    ).row(0, named=True)
    k = p['pool_divisor']
    assert total['value'] == 3 / k
    import math

    assert total['se'] == math.sqrt(0.05 * (78 * (1 / k) ** 2 + (4 / k) ** 2 + (3 / k) ** 2))
    share = targets.filter((pl.col('unit_b') == 'x') & (pl.col('measure') == 'forward_share')).row(
        0, named=True
    )
    assert share['value'] == 0.75 and share['se'] is None
    reps = read(result['replicate_estimates']).filter(
        (pl.col('unit_b') == 'x') & (pl.col('measure') == 'forward_share')
    )
    assert reps.filter(pl.col('replicate') == 37)['estimate'].item() == -1.0
    assert reps.filter(pl.col('replicate') == 38)['status'].item() == 'zero_denominator'
    support = read(result['target_support']).filter(pl.col('measure') == 'forward_share')
    assert support['undefined_replicates'].to_list() == [[38]] * (2 * (len(p['years']) + 1))
    assert set(support['se_status']) == {'undefined_replicates'}


def test_empty_native_and_canonical_outputs_keep_every_ordered_dtype(calc, tmp_path):
    schemas = typed_schemas()
    for view in ('observed', 'canonical'):
        p = product(calc, view)
        base, core, nodes, codes, usable = classified_input(calc)
        facts = calc._expected_native_disk(
            base.filter(pl.lit(False)),
            core,
            p,
            nodes,
            codes,
            usable,
            tmp_path,
            diagnostic_schema=schemas['diagnostics'],
            batch_rows=1,
        )
        for table in [
            facts.cells,
            facts.denominators,
            facts.diagnostics,
            *([facts.coverage] if facts.coverage else []),
        ]:
            assert read(table).is_empty()
            assert read(table).schema == table.schema
        out = calc._finalize_disk(
            facts.cells,
            facts.denominators,
            facts.coverage,
            p,
            tmp_path,
            schemas=schemas,
            batch_rows=1,
        )
        for name, table in out.items():
            assert read(table).is_empty() and read(table).schema == schemas[name]


def test_native_facts_survive_removed_source_and_canonical_coverage_is_not_borrowed(
    calc, tmp_path
):
    p = product(calc, 'canonical')
    base, core, nodes, codes, usable = classified_input(calc)
    path = tmp_path / 'source.parquet'
    base.collect().write_parquet(path, row_group_size=2)
    base = pl.scan_parquet(path)
    expected, coverage, _ = calc.expected_native(base, core, p, nodes, codes, usable)
    schemas = typed_schemas()
    facts = calc._expected_native_disk(
        base,
        core,
        p,
        nodes,
        codes,
        usable,
        tmp_path,
        diagnostic_schema=schemas['diagnostics'],
        batch_rows=1,
    )
    path.unlink()
    result = calc._finalize_disk(
        facts.cells, facts.denominators, facts.coverage, p, tmp_path, schemas=schemas, batch_rows=1
    )
    for name, rows in zip(
        ('target_support', 'replicate_estimates', 'targets'),
        calc.finalize(expected, coverage, p),
        strict=True,
    ):
        assert read(result[name]).equals(
            pl.DataFrame(rows, schema=schemas[name]).sort(result[name].keys, nulls_last=False)
        )
    assert set(read(result['target_support'])['unit_a']) == {'i:A'}
    assert facts.owner.is_dir()


@pytest.mark.parametrize('tail', ['denominators', 'coverage'])
def test_finalizer_validates_unused_malformed_tails(calc, tmp_path, tail):
    p = product(calc, 'canonical')
    cells = calc.complete_components(calc.aggregate(annual_frame(calc)), p)
    c = fact_fixture(calc, tmp_path, p, cells, label='cells')
    values = calc.denominator_groups(cells)
    d = fact_fixture(calc, tmp_path, p, values, pair=False, label='den')
    cov = fact_fixture(
        calc,
        tmp_path,
        p,
        {('z', 'unused', year): value([Decimal(1)] * 81) for year in [0, *p['years']]},
        pair=False,
        label='cov',
    )
    bad = d if tail == 'denominators' else cov
    bad = bad._replace(paths=(*bad.paths, bad.paths[-1]))
    with pytest.raises(ValueError, match='duplicate/out-of-order'):
        calc._finalize_disk(
            c,
            bad if tail == 'denominators' else d,
            bad if tail == 'coverage' else cov,
            p,
            tmp_path,
            schemas=typed_schemas(),
            batch_rows=1,
        )
    assert not (tmp_path / ('independent-final-' + p['product_id'])).exists()
    assert c.owner.exists() and d.owner.exists() and cov.owner.exists()


@pytest.mark.parametrize('batch_rows', [0, -1, True, 1.5])
def test_invalid_batch_size_refuses_before_output(calc, tmp_path, batch_rows):
    with pytest.raises(ValueError, match='batch_rows'):
        calc._complete_native_facts(
            annual_frame(calc), product(calc), tmp_path, batch_rows=batch_rows
        )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('kind', ['occupied', 'symlink', 'label', 'workspace_symlink'])
def test_unsafe_or_existing_owned_paths_refuse_untouched(calc, tmp_path, kind):
    p = product(calc)
    sentinel = tmp_path / 'sentinel'
    sentinel.write_text('keep')
    if kind in ('occupied', 'symlink'):
        path = tmp_path / 'completed-cells'
        path.mkdir() if kind == 'occupied' else path.symlink_to(sentinel)
        kwargs = {}
    elif kind == 'label':
        kwargs = {'label': '../escape'}
    else:
        alias = tmp_path / 'alias'
        alias.symlink_to(tmp_path, target_is_directory=True)
        kwargs = {}
    with pytest.raises((ValueError, FileExistsError)):
        calc._complete_native_facts(
            annual_frame(calc), p, alias if kind == 'workspace_symlink' else tmp_path, **kwargs
        )
    assert sentinel.read_text() == 'keep'


def test_late_sink_failure_removes_only_its_owned_child(calc, tmp_path, monkeypatch):
    p = product(calc)
    table = calc._complete_native_facts(annual_frame(calc), p, tmp_path, batch_rows=1)
    den = calc._denominator_facts(table, p, tmp_path, batch_rows=1)
    sentinel = tmp_path / 'sentinel'
    sentinel.write_text('keep')
    original = calc._sink
    seen = []

    def fail(frame, path):
        seen.append(path)
        if path.name.endswith('-ordered.parquet'):
            raise OSError('simulated ENOSPC on late sorted sink')
        original(frame, path)

    monkeypatch.setattr(calc, '_sink', fail)
    with pytest.raises(OSError, match='ENOSPC'):
        calc._finalize_disk(table, den, None, p, tmp_path, schemas=typed_schemas(), batch_rows=1)
    assert len(seen) > 100
    assert all(path.is_file() for path in (*table.paths, *den.paths))
    assert sentinel.read_text() == 'keep'
    assert not (tmp_path / ('independent-final-' + p['product_id'])).exists()


def test_strict_migration_out_of_period_and_559830_diagnostics_remain_complete(calc, tmp_path):
    p = next(
        p
        for p in calc.products()
        if p['family'] == 'migration_flow' and p['evidence_policy'] == 'strict'
    )
    base, core, nodes, codes, usable = classified_input(calc)
    base = base.with_columns(
        pl.when(pl.col('industry_unit') == 'C')
        .then(pl.lit('30'))
        .otherwise(pl.col('EMPSTATD'))
        .alias('EMPSTATD')
    )
    expected, coverage, diagnostics = calc.expected_native(base, core, p, nodes, codes, usable)
    facts = calc._expected_native_disk(
        base,
        core,
        p,
        nodes,
        codes,
        usable,
        tmp_path,
        diagnostic_schema=typed_schemas()['diagnostics'],
        batch_rows=1,
    )
    assert decode(calc, facts.cells) == expected
    assert not coverage
    actual = read(facts.diagnostics)
    assert actual.equals(
        pl.DataFrame(diagnostics, schema=typed_schemas()['diagnostics']).sort(
            calc.DIAG_KEY, nulls_last=False
        )
    )
    reasons = set(actual['reason'])
    assert {
        'outside_declared_period',
        '559830_civilian_special',
        '559830_outside_civilian',
        'residence_puma_specific_evidence_unavailable',
        'migration_puma_specific_evidence_unavailable',
    } <= reasons


@pytest.mark.parametrize('change', ['divisor', 'years', 'id'])
def test_product_mismatch_rejects_before_any_output(calc, tmp_path, change):
    p = dict(product(calc))
    if change == 'divisor':
        p['pool_divisor'] = 1
    elif change == 'years':
        p['years'] = [2024]
    else:
        p['product_id'] = 'wrong'
    with pytest.raises(ValueError, match='identity/years/divisor'):
        calc._complete_native_facts(annual_frame(calc), p, tmp_path)
    assert not list(tmp_path.iterdir())


def test_missing_matching_denominator_fails_and_cannot_borrow_next_a(calc, tmp_path):
    p = product(calc)
    cells = calc.complete_components(calc.aggregate(annual_frame(calc)), p)
    c = fact_fixture(calc, tmp_path, p, cells, label='cells')
    d = fact_fixture(
        calc,
        tmp_path,
        p,
        {key: v for key, v in calc.denominator_groups(cells).items() if key[1] != 'A'},
        pair=False,
        label='den',
    )
    with pytest.raises(ValueError, match='missing matching denominator'):
        calc._finalize_disk(c, d, None, p, tmp_path, schemas=typed_schemas())


def test_source_decimal_scale_overflow_matches_original_failure(calc, tmp_path):
    p = product(calc)
    frame = annual_frame(calc).with_columns(pl.col('PERWT').cast(pl.Decimal(38, 38)))
    with pytest.raises(pl.exceptions.InvalidOperationError):
        calc.aggregate(frame)
    with pytest.raises(pl.exceptions.InvalidOperationError):
        calc._complete_native_facts(frame, p, tmp_path, batch_rows=1)
    assert not (tmp_path / 'completed-cells').exists()


def test_application_buffers_and_group_carries_are_bounded_not_source_rescans(
    calc,
    tmp_path,
    monkeypatch,
):
    p = product(calc)
    base = annual_frame(calc).collect()
    frame = pl.concat([base.with_columns(pl.lit(f'{i:03}').alias('unit_b')) for i in range(35)])
    source = tmp_path / 'source.parquet'
    frame.write_parquet(source, row_group_size=7)
    max_output, max_carry, grouped_sinks, batch_calls = [0], [0], [], []
    append, complete, sink, collect_batches = (
        calc._FactWriter.append,
        calc.complete_components,
        calc._sink,
        pl.LazyFrame.collect_batches,
    )

    def tracked_append(self, row):
        append(self, row)
        max_output[0] = max(max_output[0], len(self.rows))
        assert len(self.rows) < self.batch_rows

    def tracked_complete(annual, product):
        max_carry[0] = max(max_carry[0], len(annual))
        assert len({key[:4] for key in annual}) <= 1
        assert len(annual) <= len(product['years'])
        return complete(annual, product)

    def tracked_sink(plan, path):
        if path.name == 'annual.parquet':
            grouped_sinks.append(plan.explain())
        return sink(plan, path)

    def tracked_batches(self, **kwargs):
        assert kwargs['engine'] == 'streaming' and kwargs['maintain_order'] is True
        assert kwargs['lazy'] is True and kwargs['chunk_size'] == 3
        batch_calls.append(self.explain())
        return collect_batches(self, **kwargs)

    monkeypatch.setattr(calc._FactWriter, 'append', tracked_append)
    monkeypatch.setattr(calc, 'complete_components', tracked_complete)
    monkeypatch.setattr(calc, '_sink', tracked_sink)
    monkeypatch.setattr(pl.LazyFrame, 'collect_batches', tracked_batches)
    cells = calc._complete_native_facts(pl.scan_parquet(source), p, tmp_path, batch_rows=3)
    den = calc._denominator_facts(cells, p, tmp_path, batch_rows=3)
    calc._finalize_disk(cells, den, None, p, tmp_path, schemas=typed_schemas(), batch_rows=3)
    assert max_carry[0] == 2 and max_output[0] == 2
    assert len(grouped_sinks) == 1 and len(batch_calls) == 4
    assert all(str(source) not in plan for plan in batch_calls)


def test_duplicate_annual_carry_fails_at_first_repeat_without_draining(calc):
    p = product(calc)
    row = {
        **dict.fromkeys(calc.PAIR, 'x'),
        'YEAR': 2023,
        '_n': 1,
        '_flags': [],
        **dict.fromkeys(calc.WEIGHTS, Decimal(1)),
    }

    def rows():
        yield row
        yield row
        raise AssertionError('duplicate annual stream was not stopped immediately')

    with pytest.raises(ValueError, match='duplicate/out-of-order'):
        list(calc._complete_annual_rows(rows(), p))


def test_independent_math_has_no_production_imports(calc):
    tree = ast.parse(Path(calc.__file__).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(not alias.name.startswith('embedding_data') for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or '').startswith('embedding_data')


def test_handwritten_defined_share_sdr(calc, tmp_path):
    import math

    p = product(calc)
    x = [Decimal(3)] + [Decimal(4)] * 80
    y = [Decimal(1)] + [Decimal(2)] * 80
    x[37], y[37] = Decimal(-1), Decimal(2)
    cells = calc.complete_components(
        {('a', 'A', 'b', 'x', 2023): value(x), ('a', 'A', 'b', 'y', 2023): value(y)}, p
    )
    table = fact_fixture(calc, tmp_path, p, cells)
    den = calc._denominator_facts(table, p, tmp_path, batch_rows=3)
    out = calc._finalize_disk(table, den, None, p, tmp_path, schemas=typed_schemas(), batch_rows=3)
    share = (
        read(out['targets'])
        .filter((pl.col('unit_b') == 'x') & (pl.col('measure') == 'forward_share'))
        .row(0, named=True)
    )
    assert share['value'] == 0.75
    expected = math.sqrt(0.05 * math.fsum([(2 / 3 - 0.75) ** 2] * 79 + [(-1 - 0.75) ** 2]))
    assert share['se'] == expected


def test_completed_fact_reader_refuses_noncanonical_exponent_without_format_expansion(
    calc, tmp_path, monkeypatch,
):
    p = product(calc)
    cells = calc.complete_components(calc.aggregate(annual_frame(calc)), p)
    table = fact_fixture(calc, tmp_path, p, cells)
    path = table.paths[-1]
    frame = pl.read_parquet(path).with_columns(
        pl.lit(['1E+1000'] * 81, pl.List(pl.String)).alias('weights'))
    frame.write_parquet(path)
    original = calc.decimal_text
    def guarded(number):
        assert number.as_tuple().exponent <= 0, 'noncanonical exponent expanded before validation'
        return original(number)
    monkeypatch.setattr(calc, 'decimal_text', guarded)
    with pytest.raises(ValueError, match='decimal vector'):
        calc._denominator_facts(table, p, tmp_path)


def test_late_native_diagnostic_sink_failure_cleans_owned_tree_and_preserves_source(
    calc, tmp_path, monkeypatch,
):
    p = product(calc, 'canonical')
    base, core, nodes, codes, usable = classified_input(calc)
    source = tmp_path / 'source.parquet'
    base.collect().write_parquet(source)
    sentinel = tmp_path / 'sentinel'
    sentinel.write_text('keep')
    original = calc._sink

    def fail(plan, path):
        if path.name == 'diagnostics-ordered.parquet':
            raise OSError('simulated late native sink failure')
        return original(plan, path)

    monkeypatch.setattr(calc, '_sink', fail)
    with pytest.raises(OSError, match='late native'):
        calc._expected_native_disk(pl.scan_parquet(source), core, p, nodes, codes, usable,
                                   tmp_path, diagnostic_schema=typed_schemas()['diagnostics'],
                                   batch_rows=1)
    assert not (tmp_path / ('independent-native-' + p['product_id'])).exists()
    assert source.is_file() and sentinel.read_text() == 'keep'


def area_product(calc, view):
    return next(
        p
        for p in calc.products()
        if p['family'] == 'area_mix' and p['dimension'] == 'industry' and p['view'] == view
    )


def allocation_input(calc, tmp_path, batch_rows):
    p = area_product(calc, 'observed')
    rows = []
    for origin, code, year, mass in [
        ('A', 'x', 2023, '30.00'),
        ('A', 'y', 2024, '10.25'),
        ('B', 'x', 2024, '20.5'),
        ('C', 'x', 2023, '15.75'),
    ]:
        rows.append(
            dict(zip(calc.PAIR, ['work_migration_puma', origin, 'industry', code]))
            | {
                'YEAR': year,
                '_flags': ['size_gate_pending'],
                **{
                    w: Decimal('-3.5' if i == 37 else '0' if i == 38 else mass)
                    for i, w in enumerate(calc.WEIGHTS)
                },
            }
        )
    frame = pl.DataFrame(
        rows,
        schema={
            **dict.fromkeys(calc.PAIR, pl.String),
            'YEAR': pl.Int64,
            '_flags': pl.List(pl.String),
            **dict.fromkeys(calc.WEIGHTS, pl.Decimal(38, 2)),
        },
    ).lazy()
    cells = calc._complete_native_facts(frame, p, tmp_path, batch_rows=batch_rows)
    den = calc._denominator_facts(cells, p, tmp_path, batch_rows=batch_rows)
    schemas = typed_schemas()
    owner = tmp_path / 'native-diagnostics'
    owner.mkdir()
    writer = calc._FactWriter(
        owner,
        'diagnostics',
        schemas['diagnostics'],
        calc.DIAG_KEY,
        p['product_id'],
        None,
        batch_rows,
    )
    native = calc._NativeFacts(tmp_path, cells, den, None, writer.finish())
    factors = {
        'A': [('c3', 0.25), ('c1', 0.25), ('c2', 0.5)],
        'B': [('c2', 0.5), ('c4', 0.25), ('c5', 0.25)],
        'C': [('c1', 0.5), ('c5', 0.5)],
    }
    counties = {
        c: {'cbsa_type': kind, 'cbsa_id': cbsa}
        for c, kind, cbsa in [
            ('c1', 'metropolitan', 'm1'),
            ('c2', 'metropolitan', 'm1'),
            ('c3', 'metropolitan', 'm2'),
            ('c4', 'micropolitan', 'u1'),
            ('c5', None, None),
        ]
    }
    return native, factors, counties


def allocation_schemas():
    declared = load('reconcile_stage9').schemas({})

    def dtype(v):
        return pl.List(dtype(v[5:-1])) if v.startswith('List(') else getattr(pl, v)

    return {
        n: pl.Schema({k: dtype(v) for k, v in declared[n].items()})
        for n in ('allocation_residuals', 'eligibility_diagnostics')
    }


@pytest.mark.parametrize('view', ['allocated_county', 'allocated_msa'])
@pytest.mark.parametrize('batch_rows', [1, 3, 128])
def test_allocation_disk_exact_oracle(calc, tmp_path, view, batch_rows):
    native, factors, counties = allocation_input(calc, tmp_path, batch_rows)
    p = area_product(calc, view)
    assert hasattr(calc, '_allocation_disk'), 'bounded allocation helper missing'
    schemas = allocation_schemas()
    actual = calc._allocation_disk(
        native,
        p,
        factors,
        counties,
        tmp_path,
        residual_schema=schemas['allocation_residuals'],
        diagnostic_schema=schemas['eligibility_diagnostics'],
        batch_rows=batch_rows,
    )
    measurements = []
    expected, residuals = calc.allocation(
        decode(calc, native.cells), p, factors, counties, measurements=measurements
    )
    assert decode(calc, actual.cells) == expected
    assert decode(calc, actual.denominators) == calc.denominator_groups(expected, True)
    assert read(actual.residuals).equals(
        pl.DataFrame(residuals, schema=schemas['allocation_residuals']).sort(
            actual.residuals.keys, nulls_last=False
        )
    )
    assert read(actual.measurements).drop('_check_order').to_dicts() == measurements
    assert len(measurements) == 2 * 3 * 81 * (2 if view == 'allocated_msa' else 1)
    output = calc._finalize_disk(
        actual.cells,
        actual.denominators,
        None,
        p,
        tmp_path,
        schemas=typed_schemas(),
        batch_rows=batch_rows,
    )
    old = calc.finalize(expected, {}, p)
    for name, rows in zip(('target_support', 'replicate_estimates', 'targets'), old):
        assert read(output[name]).equals(
            pl.DataFrame(rows, schema=typed_schemas()[name]).sort(
                output[name].keys, nulls_last=False
            )
        )


def allocated_call(calc, native, p, factors, counties, tmp_path, **kwargs):
    schemas = allocation_schemas()
    return calc._allocation_disk(
        native,
        p,
        factors,
        counties,
        tmp_path,
        residual_schema=schemas['allocation_residuals'],
        diagnostic_schema=schemas['eligibility_diagnostics'],
        **kwargs,
    )


def authored_native(calc, workspace, values, *, batch_rows=3):
    p = area_product(calc, 'observed')
    owner = workspace / 'authored-native'
    owner.mkdir()
    writer = calc._FactWriter(
        owner,
        'cells',
        calc._fact_schema(calc.PAIR, 'decimal_text'),
        [*calc.PAIR, 'component_year'],
        p['product_id'],
        'decimal_text',
        batch_rows,
    )
    for key, value in sorted(values.items()):
        writer.append(calc._fact_row(writer.keys, key, value, 'decimal_text'))
    cells = writer.finish()
    den = calc._denominator_facts(cells, p, owner, batch_rows=batch_rows)
    diag = calc._FactWriter(
        owner,
        'diagnostics',
        typed_schemas()['diagnostics'],
        calc.DIAG_KEY,
        p['product_id'],
        None,
        batch_rows,
    ).finish()
    return calc._NativeFacts(owner, cells, den, None, diag)


def test_allocation_original_fraction_order_county_first_mass_and_signed_zero(calc, tmp_path):
    import math

    values = {}
    for origin, n, mass in [
        ('A', 1, '10000000000000000'),
        ('B', 3, '-10000000000000000'),
        ('C', 3, '3'),
    ]:
        for year in (0, 2023, 2024):
            weights = [Decimal(mass)] * 81
            weights[38] = Decimal('-0')
            values['work_migration_puma', origin, 'acs_industry_category', 'x', year] = {
                'weights': weights,
                'n': n,
                'fraction': float(n),
                'flags': {'original'},
            }
    native = authored_native(calc, tmp_path, values, batch_rows=1)
    factors = {
        'C': [('c2', 1 - 0.7), ('c1', 0.7)],
        'B': [('c2', 0.7), ('c1', 0.3)],
        'A': [('c2', 1 - 0.9), ('c1', 0.9)],
    }
    counties = {c: {'cbsa_type': 'metropolitan', 'cbsa_id': 'm'} for c in ('c1', 'c2')}
    p = area_product(calc, 'allocated_msa')
    result = allocated_call(calc, native, p, factors, counties, tmp_path, batch_rows=3)
    expected, _ = calc.allocation(values, p, factors, counties)
    assert decode(calc, result.cells) == expected
    row = read(result.cells).row(0, named=True)
    assert row['fraction'] == 7.0
    assert row['fraction'] != 6.999999999999999  # county-first metadata would differ
    assert row['n'] == 7
    assert row['weights'][0] == (
        (0.0 + 1e16 * 0.9 - 1e16 * 0.3 + 3 * 0.7)
        + (0.0 + 1e16 * (1 - 0.9) - 1e16 * 0.7 + 3 * (1 - 0.7))
    )
    assert math.copysign(1, row['weights'][38]) == 1
    assert read(result.residuals).is_empty()


@pytest.mark.parametrize('kind', [None, 'micropolitan', 'metropolitan', 'empty'])
def test_allocation_empty_and_residual_support_reset(calc, tmp_path, kind):
    values = {}
    if kind != 'empty':
        for year in (0, 2023, 2024):
            values['work_migration_puma', 'A', 'industry', 'x', year] = {
                'weights': [Decimal('12.5')] * 81,
                'n': 7,
                'fraction': 7.0,
                'flags': set(),
            }
    native = authored_native(calc, tmp_path, values)
    factors = {'A': [('c0', 0), ('c2', 0.5), ('c1', 0.5)]}
    counties = {
        c: {
            'cbsa_type': None if kind == 'empty' else kind,
            'cbsa_id': 'm' if kind in ('metropolitan', 'micropolitan') else None,
        }
        for c in ('c0', 'c1', 'c2')
    }
    p = area_product(calc, 'allocated_msa')
    actual = allocated_call(calc, native, p, factors, counties, tmp_path, batch_rows=3)
    expected_measurements = []
    expected, residuals = calc.allocation(
        values, p, factors, counties, measurements=expected_measurements
    )
    assert decode(calc, actual.cells) == expected
    assert read(actual.measurements).drop('_check_order').to_dicts() == expected_measurements
    assert read(actual.residuals).equals(
        pl.DataFrame(residuals, schema=allocation_schemas()['allocation_residuals']).sort(
            actual.residuals.keys
        )
    )
    if kind in (None, 'micropolitan'):
        assert read(actual.residuals)['n_input_support'].unique().to_list() == [7]
        assert read(actual.residuals)['fractional_support_mass'].unique().to_list() == [7.0]
        assert read(actual.residuals)['weighted_mass'].unique().to_list() == [6.25]


@pytest.mark.parametrize(
    'corruption',
    [
        'missing',
        'zero',
        'nan',
        'negative',
        'unknown',
        'duplicate',
        'membership',
        'native_kind',
        'native_type',
        'denominator_tail',
        'native_vector',
        'native_duplicate',
        'native_component',
        'wrong_product',
        'batch_bool',
        'batch_zero',
    ],
)
def test_allocation_rejects_malformed_inputs(calc, tmp_path, corruption):
    native, factors, counties = allocation_input(calc, tmp_path, 3)
    p = area_product(calc, 'allocated_msa')
    kwargs = {}
    if corruption == 'missing':
        del factors['C']
    elif corruption == 'zero':
        factors['C'] = [('c1', 0.0)]
    elif corruption in ('nan', 'negative'):
        factors['C'] = [('c1', float('nan') if corruption == 'nan' else -0.5)]
    elif corruption == 'unknown':
        factors['C'] = [('unknown', 1.0)]
    elif corruption == 'duplicate':
        factors['C'] = [('c1', 0.5), ('c1', 0.5)]
    elif corruption == 'membership':
        counties['c1'] = {'cbsa_type': 'metropolitan', 'cbsa_id': None}
    elif corruption == 'native_kind':
        native = native._replace(cells=native.cells._replace(weight_kind='float64'))
    elif corruption == 'wrong_product':
        p = area_product(calc, 'observed')
    elif corruption in ('batch_bool', 'batch_zero'):
        kwargs['batch_rows'] = True if corruption == 'batch_bool' else 0
    else:
        table = native.denominators if corruption == 'denominator_tail' else native.cells
        frame = read(table)
        rows = frame.to_dicts()
        if corruption == 'native_type':
            for row in rows:
                row['unit_a_type'] = 'residence_puma'
        elif corruption == 'native_vector':
            rows[-1]['weights'].pop(37)
        elif corruption == 'native_duplicate':
            rows.append(rows[-1])
        else:
            rows.pop()
        path = table.paths[0]
        pl.DataFrame(rows, schema=frame.schema).write_parquet(path)
        for other in table.paths[1:]:
            other.unlink()
        table = table._replace(paths=(path,))
        native = native._replace(
            **{'denominators' if corruption == 'denominator_tail' else 'cells': table}
        )
    sentinel = tmp_path / 'sentinel'
    sentinel.write_text('untouched')
    with pytest.raises((ValueError, KeyError)):
        allocated_call(calc, native, p, factors, counties, tmp_path, **kwargs)
    assert sentinel.read_text() == 'untouched'
    assert all(path.exists() for path in native.cells.paths)
    assert not (tmp_path / ('independent-allocation-' + p['product_id'])).exists()


def test_allocation_owned_lifetime_and_bounded_buffers(calc, tmp_path, monkeypatch):
    import shutil

    values = {}
    for origin in ('A', 'B', 'C'):
        for code in range(19):
            for year in (0, 2023, 2024):
                values['work_migration_puma', origin, 'industry', f'{code:02d}', year] = {
                    'weights': [
                        Decimal('100000000000000000000000000000000000001')
                        if year == 0
                        else Decimal('1.0001')
                    ]
                    * 81,
                    'n': 2,
                    'fraction': 2.0,
                    'flags': {'source'},
                }
    native = authored_native(calc, tmp_path, values)
    p = area_product(calc, 'allocated_msa')
    factors = {origin: [('c2', 0.5), ('c1', 0.5)] for origin in ('A', 'B', 'C')}
    counties = {c: {'cbsa_type': 'metropolitan', 'cbsa_id': 'm'} for c in ('c1', 'c2')}
    append = calc._FactWriter.append
    calls = []

    def bounded(writer, row):
        assert len(writer.rows) < 3
        calls.append(writer.label)
        return append(writer, row)

    monkeypatch.setattr(calc._FactWriter, 'append', bounded)
    result = allocated_call(calc, native, p, factors, counties, tmp_path, batch_rows=3)
    shutil.rmtree(native.owner)
    expected, _ = calc.allocation(values, p, factors, counties)
    assert decode(calc, result.cells) == expected
    assert set(calls) >= {'contributions', 'county', 'county-rollups', 'metro', 'measurements'}
    out = calc._finalize_disk(
        result.cells, result.denominators, None, p, tmp_path, schemas=typed_schemas(), batch_rows=3
    )
    assert read(out['targets']).height > 0
    assert read(result.measurements).height == 19 * 3 * 81 * 2


def test_allocation_late_sink_cleanup_and_existing_owner(calc, tmp_path, monkeypatch):
    native, factors, counties = allocation_input(calc, tmp_path, 3)
    p = area_product(calc, 'allocated_msa')
    sentinel = tmp_path / 'sentinel'
    sentinel.write_text('owned by caller')
    sink = calc._sink

    def fail_measurement(frame, path):
        if path.name.startswith('measurements-'):
            raise OSError('late allocation sink')
        return sink(frame, path)

    monkeypatch.setattr(calc, '_sink', fail_measurement)
    with pytest.raises(OSError, match='late allocation sink'):
        allocated_call(calc, native, p, factors, counties, tmp_path, batch_rows=3)
    assert sentinel.read_text() == 'owned by caller'
    assert all(path.exists() for path in native.cells.paths)
    owner = tmp_path / ('independent-allocation-' + p['product_id'])
    assert not owner.exists()
    owner.mkdir()
    (owner / 'keep').write_text('existing')
    with pytest.raises(FileExistsError):
        allocated_call(calc, native, p, factors, counties, tmp_path)
    assert (owner / 'keep').read_text() == 'existing'


def test_allocation_measurement_retains_interior_replicate_failure(calc, tmp_path, monkeypatch):
    native, factors, counties = allocation_input(calc, tmp_path, 3)
    p = area_product(calc, 'allocated_msa')
    sink = calc._sink

    def corrupt(frame, path):
        if path.name == 'county-summary.parquet':
            frame = frame.with_columns(
                pl.col('weights').list.eval(
                    pl.when(pl.int_range(pl.len()) == 37)
                    .then(pl.element() + 50.0)
                    .otherwise(pl.element())
                )
            )
        return sink(frame, path)

    monkeypatch.setattr(calc, '_sink', corrupt)
    actual = allocated_call(calc, native, p, factors, counties, tmp_path, batch_rows=3)
    failed = read(actual.measurements).filter(pl.col('status') == 'fail')
    assert failed.height == 2 * 3 * 2
    assert failed['replicate'].unique().to_list() == [37]
    assert set(failed['check']) == {'native_to_county', 'county_to_msa_and_residuals'}


@pytest.mark.parametrize('corrupt_tag', [False, True])
def test_allocation_diagnostics_retag_once_and_validate_identity(calc, tmp_path, corrupt_tag):
    native, factors, counties = allocation_input(calc, tmp_path, 3)
    observed = area_product(calc, 'observed')
    schema = native.diagnostics.schema
    row = {
        name: []
        if dtype == pl.List(pl.String)
        else 2
        if dtype == pl.UInt64
        else 2023
        if dtype == pl.Int64
        else 1.25
        if dtype == pl.Float64
        else name
        for name, dtype in schema.items()
    }
    row.update(
        {
            n: observed[n]
            for n in (
                'family',
                'dimension',
                'base_universe',
                'evidence_policy',
                'view',
                'product_id',
            )
        }
    )
    if corrupt_tag:
        row['product_id'] = 'wrong-product'
    pl.DataFrame([row], schema=schema).write_parquet(native.diagnostics.paths[0])
    p = area_product(calc, 'allocated_msa')
    if corrupt_tag:
        with pytest.raises(ValueError, match='diagnostic.*identity'):
            allocated_call(calc, native, p, factors, counties, tmp_path)
    else:
        result = allocated_call(calc, native, p, factors, counties, tmp_path)
        expected = row | {
            n: p[n]
            for n in (
                'family',
                'dimension',
                'base_universe',
                'evidence_policy',
                'view',
                'product_id',
            )
        }
        assert read(result.diagnostics).to_dicts() == [expected]


def test_allocation_residual_both_kinds_ct_identity_and_division_order(calc, tmp_path):
    values = {}
    for component in (0, 2023, 2024):
        values['work_migration_puma', 'A', 'industry', 'x', component] = {
            'weights': [Decimal('3.50000000000000000000000000000000000001')] * 81,
            'n': 3,
            'fraction': 3.0,
            'flags': {'source'},
        }
    native = authored_native(calc, tmp_path, values)
    county_ids = ['geography:2025:county:09' + str(i) for i in range(110, 119)]
    factors = {
        'A': [(county, 0.125 if i < 8 else 0.0) for i, county in enumerate(reversed(county_ids))]
    }
    counties = {
        county: {
            'cbsa_type': 'micropolitan' if i % 2 else None,
            'cbsa_id': 'micro' if i % 2 else None,
        }
        for i, county in enumerate(county_ids)
    }
    p = area_product(calc, 'allocated_msa')
    actual = allocated_call(calc, native, p, factors, counties, tmp_path, batch_rows=3)
    measurements = []
    expected, residuals = calc.allocation(values, p, factors, counties, measurements=measurements)
    assert not expected and read(actual.cells).is_empty()
    assert read(actual.residuals).equals(
        pl.DataFrame(residuals, schema=allocation_schemas()['allocation_residuals']).sort(
            actual.residuals.keys
        )
    )
    assert read(actual.residuals)['n_input_support'].unique().to_list() == [3]
    assert read(actual.measurements).drop('_check_order').to_dicts() == measurements


def test_allocation_summary_unexpected_tail_rejected(calc, tmp_path, monkeypatch):
    native, factors, counties = allocation_input(calc, tmp_path, 3)
    summary = calc._allocation_summary

    def extra_tail(table, *args, **kwargs):
        yield from summary(table, *args, **kwargs)
        if args[2] == 'metro-summary':
            yield ('zzzz', 'extra', 2024), [0.0] * 81

    monkeypatch.setattr(calc, '_allocation_summary', extra_tail)
    p = area_product(calc, 'allocated_msa')
    with pytest.raises(ValueError, match='unexpected allocation summary tail'):
        allocated_call(calc, native, p, factors, counties, tmp_path)
    assert not (tmp_path / ('independent-allocation-' + p['product_id'])).exists()


def test_allocation_symlink_owner_refused(calc, tmp_path):
    native, factors, counties = allocation_input(calc, tmp_path, 3)
    p = area_product(calc, 'allocated_county')
    external = tmp_path / 'external'
    external.mkdir()
    sentinel = external / 'sentinel'
    sentinel.write_text('untouched')
    (tmp_path / ('independent-allocation-' + p['product_id'])).symlink_to(external)
    with pytest.raises(ValueError, match='symlink refused'):
        allocated_call(calc, native, p, factors, counties, tmp_path)
    assert sentinel.read_text() == 'untouched'


def test_allocation_native_support_corruption_fails_denominator_closure(calc, tmp_path):
    native, factors, counties = allocation_input(calc, tmp_path, 3)
    path = native.cells.paths[-1]
    frame = pl.read_parquet(path).with_columns((pl.col('n') + 1).alias('n'))
    frame.write_parquet(path)
    with pytest.raises(ValueError, match='native denominator closure'):
        allocated_call(
            calc, native, area_product(calc, 'allocated_msa'), factors, counties, tmp_path
        )


def test_allocation_conservation_uses_two_value_fsum(calc, tmp_path, monkeypatch):
    native, factors, counties = allocation_input(calc, tmp_path, 3)
    original = calc.math.fsum
    lengths = []

    def two_values(values):
        values = tuple(values)
        lengths.append(len(values))
        return original(values)

    monkeypatch.setattr(calc.math, 'fsum', two_values)
    allocated_call(
        calc,
        native,
        area_product(calc, 'allocated_msa'),
        factors,
        counties,
        tmp_path,
        batch_rows=3,
    )
    assert lengths == [2] * (2 * 3 * 81)


def test_allocation_thread_counts_preserve_exact_order(tmp_path):
    import subprocess
    import sys

    script = """
import hashlib
import importlib.util
import sys
from pathlib import Path
test_file = Path(sys.argv[1]) / 'tests/test_acs_targets_independent_spill.py'
spec = importlib.util.spec_from_file_location('allocation_tests', test_file)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
c = m.load('stage9_independent_estimates')
w = Path(sys.argv[2])
n, f, counties = m.allocation_input(c, w, 3)
p = m.area_product(c, 'allocated_msa')
r = m.allocated_call(c, n, p, f, counties, w, batch_rows=3)
print(hashlib.sha256(''.join(m.read(t).write_json() for t in r[1:]).encode()).hexdigest())
"""
    digests = []
    for threads in (1, 2, 4):
        workspace = tmp_path / str(threads)
        workspace.mkdir()
        result = subprocess.run(
            [sys.executable, '-c', script, str(ROOT), str(workspace)],
            env={'POLARS_MAX_THREADS': str(threads), 'PATH': '/usr/bin:/bin'},
            text=True,
            capture_output=True,
            check=True,
        )
        assert result.stderr == ''
        digests.append(result.stdout.strip())
    assert len(set(digests)) == 1


def test_allocation_decimal_summary_does_not_leak_context_across_yields(calc, tmp_path):
    from decimal import getcontext
    native, _, _ = allocation_input(calc, tmp_path, 3)
    owner = tmp_path / 'summary-context'
    owner.mkdir()
    initial = getcontext().prec
    rows = calc._allocation_summary(native.cells, area_product(calc, 'observed'), owner,
                                   'context-summary', 3)
    next(rows)
    try:
        assert getcontext().prec == initial
    finally:
        rows.close()
