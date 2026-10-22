'''Durable product lifetimes and exact complete-prefix table assembly.'''

from pathlib import Path

import polars as pl
import pytest
from acs_target_fixtures import minimal_target

from embedding_data import acs_target_tables as tables
from embedding_data.acs_target_contract import AUXILIARY_KEYS, AUXILIARY_SCHEMAS
from embedding_data.target_contract import TARGET_KEY_COLUMNS, TARGET_SCHEMA

def fragment(name, frame, root, label):
    helper = getattr(tables, '_sink_table_fragment', None)
    assert helper is not None, 'owned durable table fragments are required'
    return helper(name, frame.lazy(), root / (label + '.parquet'))


def assemble(name, records, root):
    helper = getattr(tables, '_assemble_table_spilled', None)
    assert helper is not None, 'complete leading-prefix assembly is required'
    return helper(name, records, root)


@pytest.mark.parametrize('name', tables.TARGET_TABLES)
def test_global_prefix_order_preserves_variants_and_duplicate_corruption(tmp_path, name):
    records, frames = [], []
    for i, policy in enumerate(['strict', 'sensitivity', 'strict']):
        frame = pl.DataFrame([
            minimal_target(unit_a=a, unit_b=b, universe='civilian_employed:' + policy)
            for a in ['a', 'b'] for b in ['z', 'a']
        ], schema=TARGET_SCHEMA).sort(TARGET_KEY_COLUMNS)
        frames.append(frame)
        records.append(fragment(name, frame, tmp_path, str(i)))
    expected = pl.concat(frames).sort(TARGET_KEY_COLUMNS)
    assert not pl.concat(frames).equals(expected)
    actual = assemble(name, records, tmp_path).collect()
    assert actual.equals(expected)
    assert actual.height == 12  # Original duplicate strict rows must reach validation.


def test_typed_empty_and_residual_replicate_before_kind_order(tmp_path):
    schema = AUXILIARY_SCHEMAS['allocation_residuals']
    rows = []
    for kind in ['non_msa_no_cbsa', 'non_msa_micropolitan']:
        for rep in [0, 37, 80]:
            row = {name: None for name in schema}
            row.update(source='acs', family='area_mix', workplace_unit_type='puma',
                workplace_unit='a', code_unit_type='code', code_unit='b', sample_set='s',
                vintage='v', universe='u', product_id='p', component_year=0, replicate=rep,
                residual_type=kind, pool_divisor=2, weighted_mass=1., n_input_support=1,
                fractional_support_mass=1., flags=[])
            rows.append(row)
    frame = pl.DataFrame(rows, schema=schema)
    records = [fragment('allocation_residuals', frame.head(3), tmp_path, 'first'),
               fragment('allocation_residuals', frame.tail(3), tmp_path, 'last')]
    assert assemble('allocation_residuals', records, tmp_path).collect().equals(
        frame.sort(AUXILIARY_KEYS['allocation_residuals']))
    for name in tables.TABLES:
        child = tmp_path / ('empty-' + name)
        child.mkdir()
        actual = assemble(name, [], child).collect()
        expected = TARGET_SCHEMA if name in tables.TARGET_TABLES else AUXILIARY_SCHEMAS[name]
        assert list(actual.schema.items()) == list(expected.items())
        assert actual.is_empty()


def legacy_tables(selected, scratch):
    '''Small public-path oracle retaining the original eager assembly recipe.'''
    from embedding_data.acs_target_contract import PRODUCTS, RESIDUAL_SCHEMA, observed_counterpart
    from embedding_data.acs_target_estimation import aggregate_native, estimate
    from embedding_data.acs_target_membership import family_rows
    from embedding_data.acs_target_projection import allocate_area_mix, canonical_rows
    from embedding_data.acs_target_rules import read_rules
    from embedding_data.acs_target_units import build_units
    from embedding_data.acs_target_weights import weighted_source

    units = build_units(selected)
    rules = read_rules(selected.upstream.sources['acs/core'])
    nodes = {system: pl.read_parquet(selected.upstream.codes[system + '_nodes'])
             for system in ('naics', 'soc')}
    factors = pl.read_parquet(selected.tables['puma_county_factors'])
    counties = pl.read_parquet(selected.upstream.geography['county_reference'])
    outputs = {name: [] for name in tables.TABLES}
    outputs['target_units'].append(units)
    with weighted_source(selected, scratch) as source:
        for product in PRODUCTS:
            if product.view != 'observed':
                continue
            rows = family_rows(source.frame, product, rules, units)
            native = aggregate_native(rows)
            derived = [(native, pl.LazyFrame(schema=RESIDUAL_SCHEMA))]
            for projected in PRODUCTS:
                if projected.view == 'observed' or observed_counterpart(projected) != product:
                    continue
                if projected.view == 'canonical':
                    derived.append((aggregate_native(canonical_rows(rows, nodes)),
                                    pl.LazyFrame(schema=RESIDUAL_SCHEMA)))
                else:
                    derived.append(allocate_area_mix(native, factors, counties, projected))
            for aggregates, residuals in derived:
                estimates = estimate(aggregates)
                name = {'observed': 'targets_observed', 'canonical': 'targets_canonical',
                        'allocated_county': 'targets_allocated_area_mix',
                        'allocated_msa': 'targets_allocated_area_mix'}[aggregates.product.view]
                for table, frame in [(name, estimates['targets']),
                    ('target_support', estimates['support']),
                    ('replicate_estimates', estimates['replicates']),
                    ('eligibility_diagnostics', aggregates.diagnostics),
                    ('allocation_residuals', residuals)]:
                    outputs[table].append(frame.collect())
    result = {}
    for name, frames in outputs.items():
        schema = TARGET_SCHEMA if name in tables.TARGET_TABLES else AUXILIARY_SCHEMAS[name]
        keys = TARGET_KEY_COLUMNS if name in tables.TARGET_TABLES else AUXILIARY_KEYS[name]
        result[name] = (pl.concat(frames) if frames else pl.DataFrame(schema=schema)).sort(
            keys, nulls_last=False)
    return result


@pytest.fixture(scope='module')
def genuine_selection(tmp_path_factory):
    from acs_target_fixtures import authenticated_mapping, prepare_v12_delivery

    from embedding_data.acs_target_inputs import select_targets

    with pytest.MonkeyPatch.context() as patches:
        fixture = authenticated_mapping(tmp_path_factory.mktemp('assembly-selected'), patches,
                                        prepare_acs=prepare_v12_delivery)
        yield select_targets(fixture['data_dir'], 'mapping',
            expected_mapping_outputs_sha256=fixture['mapping_outputs_sha256'],
            request=fixture['request'])


def test_real_fifty_product_derive_write_and_source_independent_lifetimes(
    tmp_path, monkeypatch, genuine_selection
):
    from collections import Counter

    from embedding_data.acs_target_contract import PRODUCTS

    oracle_scratch, scratch, destination = [tmp_path / p for p in ('oracle', 'spill', 'bundle')]
    for path in (oracle_scratch, scratch, destination):
        path.mkdir()
    expected = legacy_tables(genuine_selection, oracle_scratch)
    from contextlib import contextmanager

    calls, native_roots, durable, target_writes = [], [], [], []
    original_rows = tables.family_rows
    original_native = tables._aggregate_native_spilled
    original_product = tables._spill_product_outputs
    original_source = tables.weighted_source
    source_closed = False

    def begin_product(*args, **kwargs):
        assert all(not root.exists() for root in native_roots), (
            'prior observed product aggregate files must be released')
        for record in durable:
            assert pl.scan_parquet(record.path).select(pl.len()).collect().item() == record.rows
        return original_rows(*args, **kwargs)

    def native(rows, workspace, **kwargs):
        result = original_native(rows, workspace, **kwargs)
        if result.product.view == 'observed':
            root = workspace / ('native-' + result.product.product_id)
            assert root.is_dir()
            native_roots.append(root)
        return result

    def product(*args, **kwargs):
        records = original_product(*args, **kwargs)
        durable.extend(records)
        return records

    @contextmanager
    def source(*args, **kwargs):
        nonlocal source_closed
        with original_source(*args, **kwargs) as weighted:
            yield weighted
        source_closed = True

    monkeypatch.setattr(tables, 'family_rows', begin_product)
    monkeypatch.setattr(tables, '_aggregate_native_spilled', native)
    monkeypatch.setattr(tables, '_spill_product_outputs', product)
    monkeypatch.setattr(tables, 'weighted_source', source)
    actual = tables.derive_tables(genuine_selection, scratch)
    assert list(actual) == list(tables.TABLES)
    assert all(isinstance(frame, pl.LazyFrame) for frame in actual.values())
    assert source_closed
    assert len(native_roots) == 22
    assert all(not root.exists() for root in native_roots)
    assert len(durable) == 50 * 5
    assert not list(scratch.glob('ipums-*'))
    for name, frame in actual.items():
        assert frame.collect().equals(expected[name]), name
    assert set(actual['target_support'].select('view').unique().collect()['view']) == {
        'observed', 'canonical', 'allocated_county', 'allocated_msa'}
    assert actual['eligibility_diagnostics'].select('product_id').unique().collect().height == 50
    original_compare, original_writer = tables.ipums_parity.compare_ordered, tables.write_targets

    def compare(left, right, **kwargs):
        assert isinstance(left, pl.LazyFrame) and isinstance(right, pl.LazyFrame)
        calls.append('parity')
        return original_compare(left, right, **kwargs)

    def writer(frame, path):
        target_writes.append(Path(path).stem)
        return original_writer(frame, path)

    monkeypatch.setattr(tables.ipums_parity, 'compare_ordered', compare)
    monkeypatch.setattr(tables, 'write_targets', writer)
    records = tables.write_tables(destination, actual)
    assert len(calls) == 8
    assert Counter(target_writes) == Counter(tables.TARGET_TABLES)
    assert set(records) == set(tables.TABLES)
    assert {p.name for p in destination.iterdir()} == {name + '.parquet' for name in tables.TABLES}
    for name in tables.TABLES:
        assert pl.read_parquet(destination / (name + '.parquet')).equals(expected[name])
    assert len(PRODUCTS) == 50


def test_serialized_equality_uses_scan_streams_and_drains_changed_tail(tmp_path, monkeypatch):
    from test_acs_target_contract import valid_tables

    frames = valid_tables()
    validations, comparisons = [], []
    monkeypatch.setattr(tables, 'validate_complete_tables', validations.append)
    original = tables.ipums_parity.compare_ordered

    def compare(left, right, **kwargs):
        assert isinstance(left, pl.LazyFrame) and isinstance(right, pl.LazyFrame)
        comparisons.append(original(left, right, chunk_size=1))
        return comparisons[-1]

    monkeypatch.setattr(tables.ipums_parity, 'compare_ordered', compare)
    tables.write_tables(tmp_path, frames)
    assert len(validations) == 2
    assert all(isinstance(frame, pl.LazyFrame) for frame in validations[-1].values())
    assert len(comparisons) == 8
    assert all(item['values_equal'] for item in comparisons)


def test_prefix_predicates_skip_unrelated_sorted_row_groups(tmp_path, monkeypatch, capfd):
    import re

    monkeypatch.setattr(tables, '_ASSEMBLY_ROW_GROUP_SIZE', 16)
    frame = pl.DataFrame([
        minimal_target(unit_a=f'a-{a:02d}', unit_b=f'b-{b:02d}')
        for a in range(8) for b in range(16)
    ], schema=TARGET_SCHEMA)
    record = fragment('targets_observed', frame, tmp_path, 'locality')
    with pl.Config(verbose=True):
        actual = assemble('targets_observed', [record], tmp_path).collect()
    logs = capfd.readouterr().err
    groups = [(int(read), int(total)) for read, total in re.findall(
        r'Predicate pushdown: reading (\d+) / (\d+) row groups', logs)]
    assert len(groups) == 8, logs
    assert all(read == 1 and total == 8 for read, total in groups), logs
    assert actual.equals(frame.sort(TARGET_KEY_COLUMNS))
    assert sorted(p.name for p in (tmp_path / 'targets_observed').iterdir()) == [
        'prefixes.parquet', *[f'range-{i:08d}.parquet' for i in range(8)]]


def test_null_prefix_rows_are_not_lost_or_repaired(tmp_path):
    frame = pl.DataFrame([minimal_target(unit_a=None), minimal_target(unit_a='a')],
                         schema=TARGET_SCHEMA)
    record = fragment('targets_observed', frame, tmp_path, 'null')
    assert assemble('targets_observed', [record], tmp_path).collect().equals(
        frame.sort(TARGET_KEY_COLUMNS, nulls_last=False))


@pytest.mark.parametrize('kind', ['occupied', 'symlink', 'ancestor_symlink'])
def test_exclusive_fragment_paths_preserve_existing_content(tmp_path, kind):
    original = tmp_path / 'original'
    original.write_bytes(b'caller bytes')
    path = tmp_path / 'output.parquet'
    if kind == 'occupied':
        path.write_bytes(b'occupied bytes')
    elif kind == 'symlink':
        path.symlink_to(original)
    else:
        link = tmp_path / 'alias'
        link.symlink_to(tmp_path, target_is_directory=True)
        path = link / 'output.parquet'
    with pytest.raises((ValueError, FileExistsError)):
        tables._sink_table_fragment('targets_observed',
            pl.DataFrame([minimal_target()], schema=TARGET_SCHEMA).lazy(), path)
    assert original.read_bytes() == b'caller bytes'
    if kind == 'occupied':
        assert path.read_bytes() == b'occupied bytes'


@pytest.mark.parametrize('kind', ['occupied', 'symlink', 'late_failure'])
def test_assembly_cleanup_is_owned_and_keeps_input_fragments(tmp_path, monkeypatch, kind):
    frame = pl.DataFrame([minimal_target(unit_a=a) for a in ['a', 'b', 'c']],
                         schema=TARGET_SCHEMA)
    record = fragment('targets_observed', frame, tmp_path, 'input')
    old_bytes = record.path.read_bytes()
    sentinel = tmp_path / 'sentinel'
    sentinel.write_bytes(b'caller')
    directory = tmp_path / 'targets_observed'
    if kind == 'occupied':
        directory.mkdir()
        (directory / 'existing').write_bytes(b'existing')
    elif kind == 'symlink':
        directory.symlink_to(tmp_path, target_is_directory=True)
    else:
        original = tables._sink_table_fragment

        def fail(name, source, destination):
            if Path(destination).name == 'range-00000002.parquet':
                raise OSError('synthetic ENOSPC')
            return original(name, source, destination)

        monkeypatch.setattr(tables, '_sink_table_fragment', fail)
    with pytest.raises((ValueError, FileExistsError, OSError)):
        assemble('targets_observed', [record], tmp_path)
    assert record.path.read_bytes() == old_bytes
    assert sentinel.read_bytes() == b'caller'
    if kind == 'occupied':
        assert (directory / 'existing').read_bytes() == b'existing'
    elif kind == 'symlink':
        assert directory.is_symlink()
    else:
        assert not directory.exists()


def test_durable_product_outputs_are_independent_of_removed_native_work(tmp_path):
    from acs_target_fixtures import projection_case

    from embedding_data.acs_target_estimation import _aggregate_native_spilled, estimate

    helper = getattr(tables, '_spill_product_outputs', None)
    assert helper is not None, 'durable per-product completion is required'
    work, output = tmp_path / 'work', tmp_path / 'output'
    work.mkdir()
    output.mkdir()
    case = projection_case()
    native = _aggregate_native_spilled(case['rows'], work)
    expected = {name: frame.collect() for name, frame in estimate(native).items()}
    records = helper(native, pl.LazyFrame(schema=AUXILIARY_SCHEMAS['allocation_residuals']),
                     output)
    import shutil

    shutil.rmtree(work)
    result = {record.name: pl.read_parquet(record.path) for record in records}
    for table, label in [('targets_observed', 'targets'), ('target_support', 'support'),
                         ('replicate_estimates', 'replicates')]:
        assert result[table].equals(expected[label]), table
    assert result['allocation_residuals'].is_empty()
    assert not list(output.rglob('estimates-*'))


@pytest.mark.parametrize('defect', ['value', 'schema', 'rows', 'order'])
def test_serialized_parity_rejects_wrong_values_schema_counts_and_order(
    tmp_path, monkeypatch, defect
):
    from test_acs_target_contract import valid_tables

    frames = valid_tables()
    monkeypatch.setattr(tables, 'validate_complete_tables', lambda frames: None)
    original = pl.LazyFrame.sink_parquet

    def corrupt(frame, output, *args, **kwargs):
        if Path(getattr(output, 'name', '')).stem == 'replicate_estimates':
            if defect == 'value':
                frame = frame.with_columns((pl.col('estimate') + 1).alias('estimate'))
            elif defect == 'schema':
                frame = frame.with_columns(pl.lit('extra').alias('extra'))
            elif defect == 'rows':
                frame = frame.head(0)
            else:
                frame = frame.reverse()
        return original(frame, output, *args, **kwargs)

    monkeypatch.setattr(pl.LazyFrame, 'sink_parquet', corrupt)
    with pytest.raises(ValueError, match='replicate_estimates: serialized table differs'):
        tables.write_tables(tmp_path, frames)


def test_late_product_failure_removes_only_owned_output_and_keeps_native(tmp_path, monkeypatch):
    from acs_target_fixtures import projection_case

    from embedding_data.acs_target_estimation import _aggregate_native_spilled

    work, output = tmp_path / 'work', tmp_path / 'output'
    work.mkdir()
    output.mkdir()
    native = _aggregate_native_spilled(projection_case()['rows'], work)
    before = {path: path.read_bytes() for path in work.rglob('*.parquet')}
    sentinel = output / 'sentinel'
    sentinel.write_bytes(b'caller')
    original = tables._sink_table_fragment

    def fail(name, frame, destination):
        if name == 'eligibility_diagnostics':
            raise OSError('synthetic ENOSPC after estimates')
        return original(name, frame, destination)

    monkeypatch.setattr(tables, '_sink_table_fragment', fail)
    with pytest.raises(OSError, match='ENOSPC'):
        tables._spill_product_outputs(native,
            pl.LazyFrame(schema=AUXILIARY_SCHEMAS['allocation_residuals']), output)
    assert list(output.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b'caller'
    assert {path: path.read_bytes() for path in work.rglob('*.parquet')} == before


@pytest.mark.parametrize('kind', ['occupied', 'symlink'])
def test_derive_refuses_unowned_scratch_child_before_selected_reads(tmp_path, kind):
    child = tmp_path / 'target-assembly'
    if kind == 'occupied':
        child.mkdir()
        (child / 'sentinel').write_bytes(b'caller')
    else:
        child.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises((FileExistsError, ValueError)):
        tables.derive_tables(None, tmp_path)
    if kind == 'occupied':
        assert (child / 'sentinel').read_bytes() == b'caller'
    else:
        assert child.is_symlink()
