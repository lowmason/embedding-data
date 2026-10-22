'''Bounded complete-key estimator spill and exact public estimator equivalence.'''

from dataclasses import replace
from math import sqrt

import polars as pl
import pytest
from acs_target_fixtures import estimation_rows, weights
from polars.testing import assert_frame_equal

from embedding_data import acs_target_estimation as estimation

def record(point='10', *, year=2023, a='a', b='A', overrides=None, flags=None):
    return dict(year=year, a=a, b=b, flags=flags or [], **weights(point, overrides))


def spill(aggregates, workspace, **kwargs):
    helper = getattr(estimation, '_spill_estimates', None)
    assert helper is not None, 'bounded estimator spill helper is missing'
    return helper(aggregates, workspace, **kwargs)


def ordered(aggregates):
    return replace(aggregates,
        cells=aggregates.cells.sort([*estimation.PAIR_KEYS, 'component_year', 'replicate']),
        denominators=aggregates.denominators.sort(
            [*estimation.DENOMINATOR_KEYS, 'component_year', 'replicate']))


def disk_inputs(aggregates, workspace):
    frames = {}
    for name in ('cells', 'denominators'):
        path = workspace / f'{name}.parquet'
        getattr(ordered(aggregates), name).collect().write_parquet(path, row_group_size=7)
        frames[name] = pl.scan_parquet(path)
    return replace(aggregates, **frames)


def assert_equivalent(aggregates, actual):
    assert list(actual) == ['targets', 'support', 'replicates']
    for name, expected in estimation.estimate(aggregates).items():
        assert_frame_equal(actual[name].collect(), expected.collect(), check_exact=True)


@pytest.mark.parametrize('batch_size', [1, 3, 128])
def test_complete_denominators_exact_order_all_values_and_handwritten_se(tmp_path, batch_size):
    records = [record('2', overrides={37: '6'}, flags=['z']),
               record('2', overrides={37: '6'}, flags=['z']),
               record('6', overrides={37: '18'}, flags=['a']), record('30', b='B'),
               record('100', year=2024), record('100', year=2024, b='B'),
               record('5', a='b', b='C'), record('15', a='b', b='D'),
               record('20', a='c', b='E')]
    aggregates = disk_inputs(estimation.aggregate_native(estimation_rows(records)), tmp_path)
    result = spill(aggregates, tmp_path, batch_size=batch_size)
    assert_equivalent(aggregates, result)
    target = result['targets'].filter(pl.col('unit_a').str.ends_with(':a')
        & pl.col('unit_b').str.ends_with(':A') & pl.col('measure').eq('forward_share')).collect()
    assert target['value'].item() == 11 / 24
    assert target['se'].item() == pytest.approx(1 / (24 * sqrt(20)), rel=0, abs=1e-12)
    assert target['n_unweighted'].item() == 4
    reps = result['replicates'].filter(pl.col('unit_a').str.ends_with(':a')
        & pl.col('unit_b').str.ends_with(':A') & pl.col('replicate').eq(37)
        & pl.col('measure').eq('forward_share')).collect()
    assert reps.select('numerator', 'denominator', 'estimate').row(0) == (65., 130., 0.5)
    pooled = result['support'].filter(pl.col('unit_a').str.ends_with(':a')
        & pl.col('unit_b').str.ends_with(':A') & pl.col('component_year').eq(0)).collect()
    assert pooled['cell_weight_sum_exact'].to_list() == ['110', '110']
    assert pooled['denominator_weight_sum_exact'].to_list() == ['240', '240']


@pytest.mark.parametrize('chunk_size', [1, 7, 100])
@pytest.mark.parametrize('case', ['signed', 'undefined', 'nonpositive', 'zero', 'empty', 'annual'])
def test_signed_zero_undefined_and_empty_with_physical_boundaries(tmp_path, monkeypatch,
                                                               chunk_size, case):
    monkeypatch.setattr(estimation, 'ESTIMATE_INPUT_CHUNK_ROWS', chunk_size)
    records = {
        'signed': [record('10', overrides={37: '-10'}), record('10', b='B', overrides={37: '5'})],
        'undefined': [record('10', overrides={37: '0'}), record('10', b='B', overrides={37: '0'})],
        'nonpositive': [record('0', overrides={37: '2'})],
        'zero': [record('0', overrides={37: '1'}), record('10', b='B')],
        'empty': [], 'annual': [record('0.3', year=2024)],
    }[case]
    options = dict(years=(2024,), pool_divisor=1) if case == 'annual' else {}
    aggregates = disk_inputs(estimation.aggregate_native(estimation_rows(records, **options)),
                             tmp_path)
    result = spill(aggregates, tmp_path, batch_size=1)
    assert_equivalent(aggregates, result)
    reps = result['replicates'].filter(pl.col('replicate').eq(37)
        & pl.col('measure').eq('forward_share') & pl.col('unit_b').str.ends_with(':A')).collect()
    if case == 'empty':
        child = tmp_path / ('estimates-' + aggregates.product.product_id)
        assert sorted(path.name for path in child.iterdir()) == [
            'replicates-empty.parquet', 'support-empty.parquet', 'targets-empty.parquet']
    if case == 'signed':
        assert reps.select('denominator', 'estimate', 'status').row(0) == (-2.5, 2., 'defined')
    if case == 'undefined':
        assert reps.select('estimate', 'reason').row(0) == (None, 'zero_denominator')
        totals = result['targets'].filter(pl.col('measure').eq('annual_average_total')).collect()
        assert totals['se'].to_list() == [pytest.approx(sqrt(1.25))] * 2
        ratios = result['targets'].filter(pl.col('measure').eq('forward_share')).collect()
        assert ratios['se'].to_list() == [None, None]


@pytest.mark.parametrize('allocated_exact', ['canonical', 'null', 'absent'])
def test_canonical_coverage_and_allocated_float_schemas(tmp_path, allocated_exact):
    from embedding_data.acs_target_contract import PRODUCTS

    aggregates = estimation.aggregate_native(estimation_rows([
        record('0.1', flags=['z', 'a']), record('0.2'), record('1.1', b='B')]))
    if allocated_exact == 'canonical':
        product = next(p for p in PRODUCTS if p.view == 'canonical'
                       and p.family == aggregates.product.family)
        denominators = aggregates.denominators.with_columns(
            pl.when(pl.col('component_year').eq(2024)).then(7).otherwise(10)
                .cast(pl.UInt64).alias('native_coverage_n'),
            pl.when(pl.col('component_year').eq(2024)).then(90.).otherwise(110.)
                .alias('native_coverage_mass'))
        aggregates = replace(aggregates, product=product, denominators=denominators)
    else:
        product = next(p for p in PRODUCTS if p.view == 'allocated_county'
                       and p.dimension == 'industry' and p.base_universe == 'civilian_employed'
                       and p.evidence_policy == 'strict')

        def allocated(frame):
            frame = frame.with_columns(pl.col('sum_exact').cast(pl.Float64).alias('mass'),
                (pl.col('fractional_support_mass') * 0.37).alias('fractional_support_mass'))
            return (frame.drop('sum_exact') if allocated_exact == 'absent' else
                    frame.with_columns(pl.lit(None, dtype=pl.String).alias('sum_exact')))

        aggregates = replace(aggregates, product=product,
            cells=allocated(aggregates.cells), denominators=allocated(aggregates.denominators))
    aggregates = disk_inputs(aggregates, tmp_path)
    result = spill(aggregates, tmp_path, batch_size=1)
    assert_equivalent(aggregates, result)
    support = result['support'].collect()
    if allocated_exact == 'canonical':
        absent = support.filter(pl.col('component_year').eq(2024))
        assert absent['n_unweighted'].to_list() == [0] * 4
        assert absent['native_coverage_n'].to_list() == [7] * 4
        assert absent['native_coverage_mass'].to_list() == [45.] * 4
        assert support['flags'].to_list()[0] == ['a', 'size_gate_pending', 'z']
    else:
        assert support['cell_weight_sum_exact'].null_count() == support.height
        assert support['fractional_support_mass'].max() == 0.74


@pytest.mark.parametrize('empty_cells', [False, True])
def test_denominator_only_domains_status_once_and_interleaved(tmp_path, empty_cells):
    records = [record('0', a='a'), record('10', a='b'), record('0', a='c'),
               record('10', a='d'), record('0', a='e'), record('15', a='f')]
    aggregates = estimation.aggregate_native(estimation_rows(records))
    cells = (aggregates.cells.head(0) if empty_cells else aggregates.cells.filter(
        pl.col('unit_a').str.ends_with(':b') | pl.col('unit_a').str.ends_with(':d')))
    aggregates = disk_inputs(replace(aggregates, cells=cells), tmp_path)
    result = spill(aggregates, tmp_path, batch_size=1)
    assert_equivalent(aggregates, result)
    support = result['support'].collect()
    statuses = support.filter(pl.col('record_kind').eq('denominator_status'))
    assert statuses.height == 6
    assert statuses['component_year'].to_list() == [0, 2023] * 3
    assert statuses['unit_a'].str.split(':').list.last().to_list() == [
        'a', 'a', 'c', 'c', 'e', 'e']
    if empty_cells:
        assert result['targets'].collect().is_empty()
        assert result['replicates'].collect().is_empty()


@pytest.mark.parametrize('stream', ['cells', 'denominators'])
@pytest.mark.parametrize('mutation,message', [
    ('duplicate_boundary', 'duplicate'), ('duplicate_instead', 'duplicate'),
    ('missing_last', 'incomplete'), ('missing_component', 'incomplete'),
    ('invalid_year', 'incomplete'), ('invalid_replicate', 'incomplete'),
    ('null', 'null aggregate'), ('out_of_order', 'globally ordered'),
    ('nonadjacent_repeat', 'globally ordered'), ('oversized', 'incomplete'),
    ('wrong_type', 'key types'),
])
def test_global_grain_validation_across_batches(tmp_path, monkeypatch, stream, mutation, message):
    monkeypatch.setattr(estimation, 'ESTIMATE_INPUT_CHUNK_ROWS', 1)
    aggregates = ordered(estimation.aggregate_native(estimation_rows([
        record('10', a='a'), record('20', a='b')])))
    frame = getattr(aggregates, stream).collect()
    if mutation == 'duplicate_boundary':
        frame = pl.concat([frame.head(7), frame.slice(6, 1), frame.slice(7)])
    elif mutation == 'duplicate_instead':
        frame = pl.concat([frame.head(37), frame.slice(36, 1), frame.slice(38)])
    elif mutation == 'missing_last':
        frame = frame.head(frame.height - 1)
    elif mutation == 'missing_component':
        frame = frame.filter(pl.col('component_year').ne(2024))
    elif mutation == 'invalid_year':
        frame = frame.with_columns(pl.when(pl.col('component_year').eq(2024)).then(2025)
                                  .otherwise(pl.col('component_year')).alias('component_year'))
    elif mutation == 'invalid_replicate':
        frame = frame.with_columns(pl.when(pl.col('replicate').eq(80)).then(81)
                                  .otherwise(pl.col('replicate')).cast(pl.UInt8).alias('replicate'))
    elif mutation == 'null':
        frame = pl.concat([frame.head(frame.height - 1), frame.tail(1).with_columns(
            pl.lit(None, dtype=pl.String).alias('unit_a'))])
    elif mutation == 'out_of_order':
        frame = pl.concat([frame.head(7), frame.slice(8, 1), frame.slice(7, 1), frame.slice(9)])
    elif mutation == 'nonadjacent_repeat':
        frame = pl.concat([frame, frame.head(243)])
    elif mutation == 'oversized':
        frame = pl.concat([frame.head(243), frame.slice(242, 1).with_columns(
            pl.lit(81, dtype=pl.UInt8).alias('replicate')), frame.slice(243)])
    else:
        frame = frame.with_columns(pl.col('replicate').cast(pl.Int64))
    aggregates = replace(aggregates, **{stream: frame.lazy()})
    sentinel = tmp_path / 'sentinel'
    sentinel.write_text('preserve')
    with pytest.raises(ValueError, match=message):
        spill(aggregates, tmp_path, batch_size=1)
    assert list(tmp_path.iterdir()) == [sentinel]


@pytest.mark.parametrize('missing', ['a', 'b', 'c'])
def test_missing_denominator_beginning_middle_eof(tmp_path, missing):
    aggregates = ordered(estimation.aggregate_native(estimation_rows([
        record('10', a=a) for a in ('a', 'b', 'c')])))
    aggregates = replace(aggregates, denominators=aggregates.denominators.filter(
        ~pl.col('unit_a').str.ends_with(':' + missing)))
    with pytest.raises(ValueError, match='cell missing denominator'):
        spill(aggregates, tmp_path, batch_size=1)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('mutation', ['missing_last', 'duplicate', 'null', 'order'])
def test_malformed_denominator_only_tail_is_drained(tmp_path, monkeypatch, mutation):
    monkeypatch.setattr(estimation, 'ESTIMATE_INPUT_CHUNK_ROWS', 7)
    aggregates = ordered(estimation.aggregate_native(estimation_rows([
        record('10', a='a'), record('0', a='z')])))
    denominators = aggregates.denominators.collect()
    if mutation == 'missing_last':
        denominators = denominators.head(denominators.height - 1)
    elif mutation == 'duplicate':
        denominators = pl.concat([denominators, denominators.tail(1)])
    elif mutation == 'null':
        denominators = pl.concat([denominators.head(denominators.height - 1),
            denominators.tail(1).with_columns(pl.lit(None, dtype=pl.UInt8).alias('replicate'))])
    else:
        denominators = pl.concat([denominators, denominators.head(1)])
    aggregates = replace(aggregates, cells=aggregates.cells.filter(
        pl.col('unit_a').str.ends_with(':a')), denominators=denominators.lazy())
    with pytest.raises(ValueError):
        spill(aggregates, tmp_path)
    assert not list(tmp_path.iterdir())


def test_nonpositive_full_denominator_with_positive_cells(tmp_path):
    aggregates = ordered(estimation.aggregate_native(estimation_rows([
        record('10'), record('20', b='B')])))
    aggregates = replace(aggregates, denominators=aggregates.denominators.with_columns(
        pl.when(pl.col('replicate').eq(0)).then(pl.lit('-30'))
            .otherwise(pl.col('sum_exact')).alias('sum_exact')))
    result = spill(aggregates, tmp_path, batch_size=1)
    assert_equivalent(aggregates, result)
    assert result['targets'].collect()['measure'].to_list() == ['annual_average_total'] * 2
    statuses = result['support'].collect().filter(pl.col('record_kind').eq('denominator_status'))
    assert statuses['component_year'].to_list() == [0, 2023]
    assert statuses['denominator_mass'].to_list() == [-15., -15.]


def test_single_pass_scanning_and_measured_pending_resource_bounds(tmp_path, monkeypatch):
    aggregates = disk_inputs(estimation.aggregate_native(estimation_rows([
        record(str(i + 1), a='a', b=f'B{i:03d}') for i in range(29)] + [
        record('7', a='b', b='C'), record('9', a='c', b='D')])), tmp_path)
    original_batches = pl.LazyFrame.collect_batches
    original_take = estimation._OrderedAggregateReader._take_row
    original_estimate = estimation.estimate
    original_group = estimation._OrderedAggregateReader.next_group
    group_references = {2: [], 4: []}
    live_groups = {2: [], 4: []}
    scanned_rows = []
    yielded_batches = []
    carry_rows = []
    estimated_pairs = []
    denominator_sizes = []

    def batches(frame, **kwargs):
        assert kwargs == dict(chunk_size=7, engine='streaming', maintain_order=True, lazy=True)
        counts = []
        scanned_rows.append(counts)
        iterator = original_batches(frame, **kwargs)
        try:
            for batch in iterator:
                counts.append(batch.height)
                yielded_batches.append(batch.height)
                yield batch
        finally:
            iterator = None

    def take(reader):
        row = original_take(reader)
        if row is not None:
            carry_rows.append(len(reader._rows) + 1)
        return row

    def group(reader):
        import weakref

        result = original_group(reader)
        if result is not None:
            width = len(reader._keys)
            group_references[width].append(weakref.ref(result[1]))
            live_groups[width].append(sum(ref() is not None for ref in group_references[width]))
        return result

    def bounded_estimate(batch):
        cell_rows = batch.cells.select(pl.len()).collect().item()
        denominator_rows = batch.denominators.select(pl.len()).collect().item()
        assert cell_rows % 243 == 0
        estimated_pairs.append(cell_rows // 243)
        denominator_sizes.append(denominator_rows)
        assert batch.diagnostics is aggregates.diagnostics
        return original_estimate(batch)

    monkeypatch.setattr(estimation, 'ESTIMATE_INPUT_CHUNK_ROWS', 7)
    monkeypatch.setattr(pl.LazyFrame, 'collect_batches', batches)
    monkeypatch.setattr(estimation._OrderedAggregateReader, '_take_row', take)
    monkeypatch.setattr(estimation, 'estimate', bounded_estimate)
    monkeypatch.setattr(estimation._OrderedAggregateReader, 'next_group', group)
    result = spill(aggregates, tmp_path, batch_size=3)
    assert len(scanned_rows) == 2
    assert [sum(counts) for counts in scanned_rows] == [31 * 243, 3 * 243]
    assert max(yielded_batches) == 7
    assert max(carry_rows) == 243
    assert max(estimated_pairs) == 3
    assert max(live_groups[4]) == 3
    assert max(live_groups[2]) == 1
    assert max(denominator_sizes) == 243
    assert sum(estimated_pairs) == 31
    assert result['targets'].collect().height == 62


@pytest.mark.parametrize('stream', ['cells', 'denominators'])
def test_oversized_same_key_fails_at_c_plus_one(tmp_path, monkeypatch, stream):
    aggregates = ordered(estimation.aggregate_native(estimation_rows([record()])))
    base = getattr(aggregates, stream).collect()
    aggregates = replace(aggregates, **{stream: pl.concat([base, *[base.tail(1)] * 5000]).lazy()})
    original_take = estimation._OrderedAggregateReader._take_row
    takes = []

    def take(reader):
        row = original_take(reader)
        if row is not None and len(reader._keys) == (4 if stream == 'cells' else 2):
            takes.append(len(reader._rows) + 1)
        return row

    monkeypatch.setattr(estimation, 'ESTIMATE_INPUT_CHUNK_ROWS', 1)
    monkeypatch.setattr(estimation._OrderedAggregateReader, '_take_row', take)
    with pytest.raises(ValueError, match='duplicate'):
        spill(aggregates, tmp_path)
    assert len(takes) == 244
    assert max(takes) == 243
    assert not list(tmp_path.iterdir())


def test_source_gone_output_lifetime_and_no_diagnostics_evaluation(tmp_path):
    rows = estimation_rows([record('10'), record('30', b='B')])
    source = tmp_path / 'source.parquet'
    rows.members.collect().write_parquet(source)
    native = estimation._aggregate_native_spilled(replace(rows, members=pl.scan_parquet(source)),
                                                  tmp_path, batch_size=1)
    source.unlink()
    expected = estimation.estimate(native)
    native = replace(native, diagnostics=pl.scan_parquet(tmp_path / 'never-read.parquet'))
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    result = spill(native, workspace, batch_size=1)
    for name, frame in result.items():
        assert_frame_equal(frame.collect(), expected[name].collect(), check_exact=True)
    assert set(result) == {'targets', 'support', 'replicates'}
    import shutil
    shutil.rmtree(workspace)
    with pytest.raises(FileNotFoundError):
        result['targets'].collect()
    assert native.cells.collect().height == 486


@pytest.mark.parametrize('failure_call', [2, 5, 8])
def test_later_sequential_sink_failure_cleanup_and_iterator_release(tmp_path, monkeypatch,
                                                                  failure_call):
    import weakref

    aggregates = disk_inputs(estimation.aggregate_native(estimation_rows([
        record('10'), record('20', b='B'), record('30', a='b')])), tmp_path)
    sentinel = tmp_path / 'sentinel'
    sentinel.write_text('preserve')
    input_bytes = {path: path.read_bytes() for path in tmp_path.iterdir()}
    original_sink = pl.LazyFrame.sink_parquet
    original_batches = estimation._aggregate_batches
    calls = []
    references = []

    def observed_batches(frame):
        iterator = original_batches(frame)
        references.append(weakref.ref(iterator))
        return iterator

    def fail(frame, destination, *args, **kwargs):
        calls.append(destination.name)
        if len(calls) == failure_call:
            raise OSError('synthetic later sink failure')
        return original_sink(frame, destination, *args, **kwargs)

    monkeypatch.setattr(estimation, '_aggregate_batches', observed_batches)
    monkeypatch.setattr(pl.LazyFrame, 'sink_parquet', fail)
    with pytest.raises(OSError, match='synthetic later sink failure'):
        spill(aggregates, tmp_path, batch_size=1)
    assert [name.split('/')[-1].split('-')[0] for name in calls[:2]] == ['targets', 'support']
    assert {path: path.read_bytes() for path in tmp_path.iterdir()} == input_bytes
    assert references and all(reference() is None for reference in references)


def test_preexisting_child_and_symlinks_fail_without_replacement(tmp_path):
    aggregates = estimation.aggregate_native(estimation_rows([record()]))
    result = spill(aggregates, tmp_path)
    child = tmp_path / ('estimates-' + aggregates.product.product_id)
    sentinel = child / 'sentinel'
    sentinel.write_bytes(b'preserve')
    original = {path: path.read_bytes() for path in child.iterdir()}
    with pytest.raises(FileExistsError):
        spill(aggregates, tmp_path)
    assert {path: path.read_bytes() for path in child.iterdir()} == original
    assert result['targets'].collect().height == 2
    other = tmp_path / 'other'
    other.mkdir()
    (other / child.name).symlink_to(child, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        spill(aggregates, other)
    workspace_link = tmp_path / 'workspace-link'
    workspace_link.symlink_to(other, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        spill(aggregates, workspace_link)
    assert sentinel.read_bytes() == b'preserve'


@pytest.mark.parametrize('batch_size', [True, False, 0, -1, 1.5, '3', None])
def test_invalid_batch_arguments_leave_no_artifacts(tmp_path, batch_size):
    aggregates = estimation.aggregate_native(estimation_rows([]))
    with pytest.raises(ValueError, match='batch_size'):
        spill(aggregates, tmp_path, batch_size=batch_size)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('change,message', [
    ({'product_id': '../unsafe'}, 'unsafe'), ({'pool_divisor': 3}, 'pooling'),
    ({'years': ()}, 'pooling')])
def test_invalid_product_leaves_no_artifacts(tmp_path, change, message):
    aggregates = estimation.aggregate_native(estimation_rows([]))
    aggregates = replace(aggregates, product=replace(aggregates.product, **change))
    with pytest.raises(ValueError, match=message):
        spill(aggregates, tmp_path)
    assert not list(tmp_path.iterdir())
