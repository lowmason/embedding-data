'''Exact, bounded aggregate projection with owned disk lifetimes.'''

from dataclasses import replace

import polars as pl
import pytest
from acs_target_fixtures import projection_case

from embedding_data import acs_target_projection as projection
from embedding_data.acs_target_contract import AUXILIARY_KEYS
from embedding_data.acs_target_estimation import (
    DENOMINATOR_KEYS,
    PAIR_KEYS,
    _aggregate_native_spilled,
    estimate,
)

def spill(case, workspace, view='msa', **kwargs):
    helper = getattr(projection, '_allocate_area_mix_spilled', None)
    assert helper is not None, 'private wide projection helper is required'
    return helper(case['native'], case['factors'], case['counties'],
                  case[view + '_product'], workspace, **kwargs)


def assert_same(expected, actual):
    for label, keys in [('cells', PAIR_KEYS), ('denominators', DENOMINATOR_KEYS)]:
        order = [*keys, 'component_year', 'replicate']
        left = getattr(expected, label).sort(order).collect()
        right = getattr(actual, label).collect()
        assert list(left.schema.items()) == list(right.schema.items())
        assert left.equals(right), label
    assert expected.diagnostics.collect().equals(actual.diagnostics.collect())
    for name, frame in estimate(expected).items():
        assert frame.collect().equals(estimate(actual)[name].collect()), name


@pytest.mark.parametrize('view', ['county', 'msa'])
@pytest.mark.parametrize('batch_size', [1, 3, 128])
@pytest.mark.parametrize('artifact', [False, True])
def test_exact_wide_and_compatibility_paths(tmp_path, view, batch_size, artifact):
    case = projection_case()
    options = {}
    if artifact:
        case['native'] = _aggregate_native_spilled(case['rows'], tmp_path, batch_size=1)
        options['native_wide_root'] = tmp_path / ('native-' + case['native'].product.product_id)
    expected, residual = projection.allocate_area_mix(case['native'], case['factors'],
                                                       case['counties'], case[view + '_product'])
    actual, actual_residual = spill(case, tmp_path, view, batch_size=batch_size, **options)
    assert_same(expected, actual)
    assert residual.sort(AUXILIARY_KEYS['allocation_residuals']).collect().equals(
        actual_residual.collect())
    if view == 'msa':
        full = actual.cells.filter((pl.col('component_year') == 0)
                                   & (pl.col('replicate') == 0)).collect()
        assert full['mass'].to_list() == [150., 150.]
        assert full['n_unweighted'].to_list() == [2, 2]
        assert full['fractional_support_mass'].to_list() == [1.5, 1.5]
        target = estimate(actual)['targets'].collect()
        assert target.filter(pl.col('measure') == 'annual_average_total')[
            'value'].to_list() == [75., 75.]
        assert target.filter(pl.col('measure') == 'forward_share')['value'].to_list() == [.5, .5]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    import socket

    import dotenv

    def forbidden(*args, **kwargs):
        raise AssertionError('projection spill must remain offline')

    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)
    monkeypatch.setattr(dotenv, 'load_dotenv', forbidden)


@pytest.mark.parametrize('mutation', ['missing_r', 'missing_year', 'duplicate', 'null',
    'wrong_order', 'n', 'flags', 'fraction', 'denominator', 'negative', 'null_exact'])
def test_complete_native_input_validation_and_cleanup(tmp_path, mutation):
    case = projection_case()
    native = case['native']
    frame = native.cells
    if mutation == 'missing_r':
        frame = frame.filter(pl.col('replicate') != 37)
    elif mutation == 'missing_year':
        frame = frame.filter(pl.col('component_year') != 2024)
    elif mutation == 'duplicate':
        frame = pl.concat([frame, frame.tail(1)])
    elif mutation == 'null':
        frame = frame.with_columns(pl.lit(None, dtype=pl.String).alias('unit_b'))
    elif mutation == 'wrong_order':
        frame = frame.reverse()
    elif mutation in {'n', 'flags', 'fraction'}:
        name, value = {'n': ('n_unweighted', pl.lit(999, dtype=pl.UInt64)),
            'flags': ('flags', pl.lit(['changed'])),
            'fraction': ('fractional_support_mass', pl.lit(-1.))}[mutation]
        frame = frame.with_columns(pl.when(pl.col('replicate') == 37).then(value)
                                  .otherwise(pl.col(name)).alias(name))
    elif mutation == 'denominator':
        native = replace(native, denominators=native.denominators.with_columns(
            pl.when(pl.col('replicate') == 37).then(pl.lit('999'))
              .otherwise(pl.col('sum_exact')).alias('sum_exact')))
    elif mutation == 'negative':
        frame = frame.with_columns(pl.when(pl.col('replicate') == 0).then(pl.lit('-1'))
                                  .otherwise(pl.col('sum_exact')).alias('sum_exact'))
    else:
        frame = frame.with_columns(pl.lit(None, dtype=pl.String).alias('sum_exact'))
    case['native'] = replace(native, cells=frame)
    sentinel = tmp_path / 'sentinel'
    sentinel.write_text('owned by caller')
    with pytest.raises((ValueError, pl.exceptions.PolarsError)):
        spill(case, tmp_path)
    assert sentinel.read_text() == 'owned by caller'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['sentinel']


@pytest.mark.parametrize('mutation', ['missing', 'schema', 'scale', 'duplicate', 'null',
    'wrong_year', 'changed_mass', 'wrong_root', 'symlink', 'ancestor_symlink'])
def test_exact_artifact_binding_and_paths(tmp_path, mutation):
    case = projection_case()
    case['native'] = _aggregate_native_spilled(case['rows'], tmp_path)
    root = tmp_path / ('native-' + case['native'].product.product_id)
    member = root / 'cells-annual.parquet'
    frame = pl.read_parquet(member)
    if mutation == 'missing':
        member.unlink()
    elif mutation == 'wrong_root':
        root = tmp_path
    elif mutation == 'symlink':
        target = tmp_path / 'original.parquet'
        member.rename(target)
        member.symlink_to(target)
    elif mutation == 'ancestor_symlink':
        link = tmp_path / 'alias'
        link.symlink_to(tmp_path, target_is_directory=True)
        root = link / root.name
    else:
        if mutation == 'schema':
            frame = frame.select(list(reversed(frame.columns)))
        elif mutation == 'scale':
            frame = frame.with_columns(pl.col('PERWT').cast(pl.Decimal(38, 1)))
        elif mutation == 'duplicate':
            frame = pl.concat([frame, frame.head(1)])
        elif mutation == 'null':
            frame = frame.with_columns(pl.lit(None, dtype=pl.String).alias('unit_b'))
        elif mutation == 'wrong_year':
            frame = frame.with_columns(pl.lit(2000).alias('component_year'))
        else:
            frame = frame.with_columns((pl.col('REPWTP37') + 1).alias('REPWTP37'))
        frame.write_parquet(member)
    with pytest.raises((ValueError, pl.exceptions.PolarsError)):
        spill(case, tmp_path, native_wide_root=root)
    assert not (tmp_path / ('projection-' + case['msa_product'].product_id)).exists()
    assert (tmp_path / ('native-' + case['native'].product.product_id)).exists()


@pytest.mark.parametrize('batch_size', [0, -1, True, 1.5, '1'])
def test_invalid_batch_size_has_no_side_effect(tmp_path, batch_size):
    with pytest.raises(ValueError, match='positive integer'):
        spill(projection_case(), tmp_path, batch_size=batch_size)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('view', ['county', 'msa'])
@pytest.mark.parametrize('empty', [False, True])
def test_absent_year_zero_and_empty_exact_outputs(tmp_path, view, empty):
    from embedding_data.acs_target_estimation import aggregate_native

    case = projection_case()
    members = case['rows'].members.filter(pl.col('YEAR') == 2023)
    if empty:
        members = members.head(0)
    else:
        members = members.with_columns(pl.lit(0, dtype=pl.Decimal(38, 0)).alias('PERWT'))
    case['rows'] = replace(case['rows'], members=members)
    case['native'] = aggregate_native(case['rows'])
    expected, residuals = projection.allocate_area_mix(case['native'], case['factors'],
                                                       case['counties'], case[view + '_product'])
    actual, residual = spill(case, tmp_path, view, batch_size=1)
    assert_same(expected, actual)
    assert residuals.sort(AUXILIARY_KEYS['allocation_residuals']).collect().equals(
        residual.collect())


def test_binding_artifacts_released_and_final_long_shards_bounded(tmp_path, monkeypatch):
    case = projection_case()
    case['native'] = _aggregate_native_spilled(case['rows'], tmp_path, batch_size=1)
    root = tmp_path / ('native-' + case['native'].product.product_id)
    original = projection._sink_projection
    counts = []

    def tracked(frame, directory, label):
        result = original(frame, directory, label)
        if '-long-' in label:
            counts.append((label, result.select(pl.len()).collect().item()))
        return result

    monkeypatch.setattr(projection, '_sink_projection', tracked)
    actual, residual = spill(case, tmp_path, native_wide_root=root, batch_size=1)
    directory = tmp_path / ('projection-' + case['msa_product'].product_id)
    assert not any(p.name.startswith('binding') for p in directory.iterdir())
    assert counts and all(n <= 2 * 3 * 81 for _, n in counts)
    assert all(n <= 3 * 81 for label, n in counts if not label.startswith('residual'))
    assert actual.cells.select(pl.len()).collect().item() == 486
    assert residual.select(pl.len()).collect().item() == 972


@pytest.mark.parametrize('phase', ['contributions', 'denominators', 'residual-long-00000000'])
def test_interior_replicate_corruption_fails_before_return(tmp_path, monkeypatch, phase):
    case = projection_case()
    original = projection._sink_projection

    def corrupted(frame, directory, label):
        if label == phase:
            if phase.startswith('residual'):
                frame = frame.with_columns(pl.when(pl.col('replicate') == 37)
                    .then(pl.col('weighted_mass') + 100).otherwise(pl.col('weighted_mass'))
                    .alias('weighted_mass'))
            else:
                frame = frame.with_columns((pl.col('_mass_37') + 100).alias('_mass_37'))
        return original(frame, directory, label)

    monkeypatch.setattr(projection, '_sink_projection', corrupted)
    with pytest.raises(ValueError, match='conservation'):
        spill(case, tmp_path)
    assert not list(tmp_path.iterdir())


def adversarial_case():
    from embedding_data.acs_mapping_contract import factor_key
    from embedding_data.acs_target_estimation import aggregate_native

    case = projection_case()
    members = case['rows'].members.collect()
    originals = [members.filter(pl.col('unit_a').str.ends_with('0100100'))
                 .filter(pl.col('YEAR') == 2023),
                 members.filter(pl.col('unit_a').str.ends_with('0200200'))
                 .filter(pl.col('YEAR') == 2024)]
    third = originals[0].with_columns(
        pl.lit('geography:2020:work_migration_puma:0300300').alias('unit_a'),
        pl.lit(2024, dtype=pl.Int64).alias('YEAR'),
        (pl.col('source_row') + 100).alias('source_row'))
    sources = []
    for source, weight in zip([*originals, third], [10**16, 1, -10**16], strict=True):
        sources.append(source.with_columns(pl.lit(weight, dtype=pl.Decimal(38, 0))
                                          .alias('REPWTP37')))
    source = pl.concat(sources)
    # A typed category with identical text must remain a separate aggregate key.
    source = pl.concat([source, source.head(1).with_columns(
        pl.lit('other_category').alias('unit_b_type'),
        (pl.col('source_row') + 1000).alias('source_row'),
        pl.lit(0, dtype=pl.Decimal(38, 0)).alias('PERWT'))])
    case['rows'] = replace(case['rows'], members=source.lazy())
    case['native'] = aggregate_native(case['rows'])
    factors = case['factors'].with_columns(pl.when(pl.col('state_fips') == '01')
        .then(pl.lit(.25)).otherwise(pl.col('factor')).alias('factor'))
    extra = []
    for geoid, factor in [('01001', .25), ('02003', .75)]:
        extra.append(factors.row(0, named=True) | {
            'state_fips': '03', 'area_code': '00300',
            'factor_key': factor_key('work_migration', '03', '00300'),
            'county_geoid': geoid, 'county_node_id': 'geography:2025:county:' + geoid,
            'factor': factor})
    case['factors'] = pl.concat([factors, pl.DataFrame(extra, schema=factors.schema)]).reverse()
    case['counties'] = case['counties'].with_columns(
        *[pl.when(pl.col('county_geoid') == '02003').then(pl.lit(value, dtype=dtype))
          .otherwise(pl.col(name)).alias(name) for name, value, dtype in [
            ('cbsa_id', 'geography:2023:cbsa:30000', pl.String),
            ('cbsa_code', '30000', pl.String), ('cbsa_type', 'metropolitan', pl.String),
            ('cbsa_vintage', 2023, pl.Int64)]]).reverse()
    return case


@pytest.mark.parametrize('artifact', [False, True])
@pytest.mark.parametrize('view', ['county', 'msa'])
def test_adversarial_float_order_typed_codes_absent_support_and_residual_order(tmp_path, artifact,
                                                                            view):
    case = adversarial_case()
    root = None
    if artifact:
        case['native'] = _aggregate_native_spilled(case['rows'], tmp_path, batch_size=1)
        root = tmp_path / ('native-' + case['native'].product.product_id)
    expected, residual = projection.allocate_area_mix(case['native'], case['factors'],
                                                       case['counties'], case[view + '_product'])
    actual, result = spill(case, tmp_path, view, native_wide_root=root, batch_size=1)
    assert_same(expected, actual)
    result = result.collect()
    assert result.equals(result.sort(AUXILIARY_KEYS['allocation_residuals']))
    assert residual.sort(AUXILIARY_KEYS['allocation_residuals']).collect().equals(result)
    assert not result.select(
        pl.struct(AUXILIARY_KEYS['allocation_residuals']).is_duplicated().any()).item()
    if view == 'msa':
        pair = result.filter((pl.col('workplace_unit').str.ends_with('0100100'))
            & (pl.col('code_unit') == case['code_a'])
            & (pl.col('code_unit_type') == 'acs_industry_category')
            & (pl.col('component_year') == 0))
        assert pair.select('replicate', 'residual_type').head(4).rows() == [
            (0, 'micropolitan'), (0, 'no_cbsa'), (1, 'micropolitan'), (1, 'no_cbsa')]


def test_no_metro_retains_all_residual_mass(tmp_path):
    case = projection_case()
    case['counties'] = case['counties'].with_columns(
        pl.when(pl.col('cbsa_type') == 'metropolitan').then(pl.lit('micropolitan'))
          .otherwise(pl.col('cbsa_type')).alias('cbsa_type'))
    expected, residual = projection.allocate_area_mix(case['native'], case['factors'],
                                                       case['counties'], case['msa_product'])
    actual, result = spill(case, tmp_path, batch_size=1)
    assert_same(expected, actual)
    assert residual.sort(AUXILIARY_KEYS['allocation_residuals']).collect().equals(
            result.collect())
    assert actual.cells.collect().is_empty()


@pytest.mark.parametrize('mutation', ['residence', 'bad_key', 'unknown_county', 'unknown_cbsa',
    'duplicate_county', 'duplicate_factor', 'missing', 'all_zero', 'bad_factor'])
def test_reference_validation_precedes_allocation(tmp_path, mutation):
    case = projection_case()
    if mutation == 'residence':
        case['factors'] = case['factors'].with_columns(pl.lit('residence').alias('area_type'))
    elif mutation == 'bad_key':
        case['factors'] = case['factors'].with_columns(pl.lit('bad').alias('factor_key'))
    elif mutation == 'unknown_county':
        case['counties'] = case['counties'].head(1)
    elif mutation == 'unknown_cbsa':
        case['counties'] = case['counties'].with_columns(pl.lit('bad').alias('cbsa_id'))
    elif mutation == 'duplicate_county':
        case['counties'] = pl.concat([case['counties'], case['counties'].head(1)])
    elif mutation == 'duplicate_factor':
        case['factors'] = pl.concat([case['factors'], case['factors'].head(1)])
    elif mutation == 'missing':
        case['factors'] = case['factors'].filter(pl.col('state_fips') == '01')
    else:
        case['factors'] = case['factors'].with_columns(
            pl.lit(0. if mutation == 'all_zero' else float('nan')).alias('factor'))
    with pytest.raises(ValueError):
        spill(case, tmp_path)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('occupied', ['directory', 'symlink', 'workspace_symlink'])
def test_exclusive_owned_paths(tmp_path, occupied):
    case = projection_case()
    path = tmp_path / ('projection-' + case['msa_product'].product_id)
    workspace = tmp_path
    if occupied == 'workspace_symlink':
        workspace = tmp_path / 'alias'
        workspace.symlink_to(tmp_path, target_is_directory=True)
    elif occupied == 'symlink':
        path.symlink_to(tmp_path, target_is_directory=True)
    else:
        path.mkdir()
        (path / 'sentinel').write_text('preserved')
    before = sorted(p.name for p in tmp_path.iterdir())
    with pytest.raises((ValueError, FileExistsError)):
        spill(case, workspace)
    assert sorted(p.name for p in tmp_path.iterdir()) == before


def test_late_io_failure_preserves_caller_native_and_sentinels(tmp_path, monkeypatch):
    case = projection_case()
    case['native'] = _aggregate_native_spilled(case['rows'], tmp_path)
    root = tmp_path / ('native-' + case['native'].product.product_id)
    sentinel = tmp_path / 'caller'
    sentinel.write_text('preserved')
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    original = projection._sink_projection

    def fail(frame, directory, label):
        if label == 'diagnostics':
            raise OSError('simulated late ENOSPC')
        return original(frame, directory, label)

    monkeypatch.setattr(projection, '_sink_projection', fail)
    with pytest.raises(OSError, match='ENOSPC'):
        spill(case, tmp_path, native_wide_root=root)
    assert before == {p.name: p.read_bytes() for p in root.iterdir()}
    assert sentinel.read_text() == 'preserved'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['caller', root.name]


def test_all_metropolitan_and_all_nine_ct_county_identities(tmp_path):
    from embedding_data.acs_mapping_contract import factor_key
    from embedding_data.acs_target_estimation import aggregate_native

    case = projection_case()
    case['rows'] = replace(case['rows'], members=case['rows'].members.with_columns(
        pl.lit('geography:2020:work_migration_puma:0900100').alias('unit_a')))
    case['native'] = aggregate_native(case['rows'])
    factors, counties = [], []
    for code in range(110, 191, 10):
        geoid = '09' + str(code)
        factors.append(case['factors'].row(0, named=True) | {
            'factor_key': factor_key('work_migration', '09', '00100'),
            'state_fips': '09', 'area_code': '00100', 'county_geoid': geoid,
            'county_node_id': 'geography:2025:county:' + geoid, 'factor': 1 / 9})
        counties.append(case['counties'].row(1, named=True) | {
            'county_id': 'geography:2025:county:' + geoid, 'county_geoid': geoid})
    case['factors'] = pl.DataFrame(factors, schema=case['factors'].schema)
    case['counties'] = pl.DataFrame(counties, schema=case['counties'].schema)
    for view in ('county', 'msa'):
        expected, residual = projection.allocate_area_mix(case['native'], case['factors'],
            case['counties'], case[view + '_product'])
        actual, result = spill(case, tmp_path, view, batch_size=1)
        assert_same(expected, actual)
        assert residual.collect().equals(result.collect())
        if view == 'county':
            assert actual.cells.select(pl.col('unit_a').n_unique()).collect().item() == 9


def test_source_unlinked_before_projection_and_native_removed_before_readback(tmp_path):
    import shutil

    case = projection_case()
    source = tmp_path / 'members.parquet'
    case['rows'].members.sink_parquet(source)
    case['rows'] = replace(case['rows'], members=pl.scan_parquet(source))
    case['native'] = _aggregate_native_spilled(case['rows'], tmp_path, batch_size=1)
    root = tmp_path / ('native-' + case['native'].product.product_id)
    expected, residual = projection.allocate_area_mix(case['native'], case['factors'],
        case['counties'], case['msa_product'])
    expected_values = {name: frame.collect() for name, frame in estimate(expected).items()}
    residual = residual.sort(AUXILIARY_KEYS['allocation_residuals']).collect()
    source.unlink()
    actual, result = spill(case, tmp_path, native_wide_root=root, batch_size=1)
    shutil.rmtree(root)
    for name, frame in estimate(actual).items():
        assert expected_values[name].equals(frame.collect())
    assert residual.equals(result.collect())
    directory = tmp_path / ('projection-' + case['msa_product'].product_id)
    shutil.rmtree(directory)
    with pytest.raises(FileNotFoundError):
        actual.cells.collect()


@pytest.mark.parametrize('mutation', ['canonical', 'flow', 'mismatched', 'unsafe', 'traversal'])
def test_product_and_workspace_contracts(tmp_path, mutation):
    case = projection_case()
    if mutation == 'canonical':
        case['native'] = replace(case['native'], product=replace(case['native'].product,
                                                               view='canonical'))
    elif mutation == 'flow':
        case['msa_product'] = replace(case['msa_product'], family='commuting_flow')
    elif mutation == 'mismatched':
        case['msa_product'] = replace(case['msa_product'], evidence_policy='sensitivity')
    elif mutation == 'unsafe':
        case['msa_product'] = replace(case['msa_product'], product_id='../unsafe')
    workspace = tmp_path / '..' / tmp_path.name if mutation == 'traversal' else tmp_path
    with pytest.raises(ValueError):
        spill(case, workspace)
    assert not list(tmp_path.iterdir())


def test_fresh_process_thread_counts_match_both_paths_and_public_oracle(tmp_path):
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    case = adversarial_case()
    _aggregate_native_spilled(case['rows'], tmp_path, batch_size=1)
    case['factors'].write_parquet(tmp_path / 'factors.parquet')
    case['counties'].write_parquet(tmp_path / 'counties.parquet')
    script = """
import json, socket, sys
from pathlib import Path
import dotenv
import polars as pl
from embedding_data.acs_target_contract import PRODUCTS, AUXILIARY_KEYS
from embedding_data.acs_target_estimation import (
    AggregateSet, estimate, PAIR_KEYS, DENOMINATOR_KEYS)
from embedding_data.acs_target_projection import allocate_area_mix, _allocate_area_mix_spilled

def forbidden(*args, **kwargs):
    raise AssertionError('fresh-process projection must remain offline')
socket.socket.connect = forbidden
socket.socket.connect_ex = forbidden
dotenv.load_dotenv = forbidden
root = Path(sys.argv[1])
observed = next(p for p in PRODUCTS if p.product_id == sys.argv[2])
native_root = root / ('native-' + observed.product_id)
cells = pl.concat([pl.scan_parquet(path)
                   for path in sorted(native_root.glob('cells-long-*.parquet'))])
denoms = pl.concat([pl.scan_parquet(path)
                    for path in sorted(native_root.glob('denominators-long-*.parquet'))])
native = AggregateSet(cells, denoms,
    pl.scan_parquet(native_root / 'diagnostics.parquet'), observed)
factors = pl.read_parquet(root / 'factors.parquet')
counties = pl.read_parquet(root / 'counties.parquet')
results = {}
for view, pid in zip(('county', 'msa'), sys.argv[3:5]):
    product = next(p for p in PRODUCTS if p.product_id == pid)
    expected, residual = allocate_area_mix(native, factors, counties, product)
    for path_kind in ('artifact', 'fallback'):
        workspace = root / (sys.argv[5] + '-' + view + '-' + path_kind)
        workspace.mkdir()
        actual, actual_residual = _allocate_area_mix_spilled(native, factors, counties, product,
            workspace, native_wide_root=native_root if path_kind == 'artifact' else None,
            batch_size=1)
        for label, keys in [('cells', PAIR_KEYS), ('denominators', DENOMINATOR_KEYS)]:
            left = getattr(expected, label).sort([*keys, 'component_year', 'replicate']).collect()
            assert left.equals(getattr(actual, label).collect())
        expected_residual = residual.sort(AUXILIARY_KEYS['allocation_residuals']).collect()
        assert expected_residual.equals(actual_residual.collect())
        frames = estimate(actual) | {'residuals': actual_residual}
        for name, frame in estimate(expected).items():
            assert frame.collect().equals(frames[name].collect())
        results[view + '-' + path_kind] = {name: frame.collect().to_dicts()
                                         for name, frame in frames.items()}
print(json.dumps(results, sort_keys=True, allow_nan=False))
"""
    outputs = []
    for threads in (1, 2, 4):
        result = subprocess.run([sys.executable, '-c', script, str(tmp_path),
            case['native'].product.product_id, case['county_product'].product_id,
            case['msa_product'].product_id, str(threads)], check=True, capture_output=True,
            text=True, cwd=Path(__file__).resolve().parents[1],
            env=os.environ | {'POLARS_MAX_THREADS': str(threads)})
        assert result.stderr == ''
        outputs.append(json.loads(result.stdout))
    assert outputs[0] == outputs[1] == outputs[2]


def test_denominator_flags_cannot_disagree_with_native_cells(tmp_path):
    case = projection_case()
    case['native'] = replace(case['native'], denominators=case['native'].denominators.with_columns(
        pl.lit(['invented'], dtype=pl.List(pl.String)).alias('flags')))
    with pytest.raises(ValueError, match='closure'):
        spill(case, tmp_path)
    assert not list(tmp_path.iterdir())


def test_seven_row_physical_boundaries_and_diagnostics_once(tmp_path, monkeypatch):
    from embedding_data import acs_target_estimation as estimation
    from embedding_data.acs_target_membership import _diagnostic

    case = projection_case()
    diagnostic_members = case['rows'].members.with_columns(
        pl.lit('core').alias('acs_profile'), pl.lit('synthetic').alias('source_delivery_id'),
        pl.lit('sample').alias('acs_sample_id'), pl.col('YEAR').alias('acs_component_year'))
    diagnostics = _diagnostic(diagnostic_members, case['rows'].product,
                             partition='eligibility', reason=pl.lit('eligible'))
    case['rows'] = replace(case['rows'], diagnostics=diagnostics)
    case['native'] = _aggregate_native_spilled(case['rows'], tmp_path, batch_size=1)
    root = tmp_path / ('native-' + case['native'].product.product_id)
    physical_rows = []

    def batches(frame):
        for batch in frame.collect_batches(chunk_size=7, engine='streaming',
                                           maintain_order=True, lazy=True):
            physical_rows.append(batch.height)
            yield batch

    monkeypatch.setattr(estimation, '_aggregate_batches', batches)
    for artifact in (False, True):
        workspace = tmp_path / str(artifact)
        workspace.mkdir()
        expected, residual = projection.allocate_area_mix(case['native'], case['factors'],
            case['counties'], case['msa_product'])
        actual, result = spill(case, workspace, native_wide_root=root if artifact else None,
                               batch_size=1)
        assert_same(expected, actual)
        assert residual.sort(AUXILIARY_KEYS['allocation_residuals']).collect().equals(
            result.collect())
        actual_diagnostics = actual.diagnostics.collect()
        assert actual_diagnostics.height == diagnostics.collect().height == 2
        assert actual_diagnostics['product_id'].unique().to_list() == [
            case['msa_product'].product_id]
    assert physical_rows and max(physical_rows) <= 7


@pytest.mark.parametrize('artifact', [False, True])
def test_hand_county_mass_and_observable_three_term_float_order(tmp_path, artifact):
    from embedding_data.acs_mapping_contract import factor_key
    from embedding_data.acs_target_estimation import aggregate_native

    case = projection_case()
    base = case['rows'].members.filter(pl.col('unit_a').str.ends_with('0100100'))
    members, factors = [], []
    for index, annual_replica in enumerate([10**16, 1, -(10**16)], start=1):
        area = f'{index:05d}'
        members.append(base.with_columns(
            pl.lit('geography:2020:work_migration_puma:01' + area).alias('unit_a'),
            (pl.col('source_row') + index * 100).alias('source_row'),
            pl.lit(annual_replica, dtype=pl.Decimal(38, 0)).alias('REPWTP37')))
        for geoid, factor in [('01001', .25), ('02001', .75)]:
            factors.append(case['factors'].row(1, named=True) | {
                'state_fips': '01', 'area_code': area,
                'factor_key': factor_key('work_migration', '01', area),
                'county_geoid': geoid, 'county_node_id': 'geography:2025:county:' + geoid,
                'factor': factor})
    case['rows'] = replace(case['rows'], members=pl.concat(members))
    case['native'] = aggregate_native(case['rows'])
    case['factors'] = pl.DataFrame(factors, schema=case['factors'].schema).reverse()
    root = None
    if artifact:
        case['native'] = _aggregate_native_spilled(case['rows'], tmp_path, batch_size=1)
        root = tmp_path / ('native-' + case['native'].product.product_id)

    # Pooling two annual components gives these three native replicate masses.
    # Changing just their addition order loses or retains the low-order value.
    original_origin_order = (2e16 + 2.) + -2e16
    alternative_origin_order = (2e16 + -2e16) + 2.
    assert original_origin_order == 0.
    assert alternative_origin_order == 2.
    assert original_origin_order.hex() != alternative_origin_order.hex()

    for view in ('county', 'msa'):
        expected, residual = projection.allocate_area_mix(case['native'], case['factors'],
            case['counties'], case[view + '_product'])
        actual, result = spill(case, tmp_path, view, native_wide_root=root, batch_size=1)
        assert_same(expected, actual)
        assert residual.collect().equals(result.collect())
        full = actual.cells.filter((pl.col('component_year') == 0)
            & (pl.col('unit_b') == case['code_a']))
        if view == 'county':
            quarter_county = full.filter(pl.col('unit_a').str.ends_with('01001')
                                         & (pl.col('replicate') == 0)).collect()
            # Three origins * two annual records * raw100 * factor1/4 = raw150.
            assert quarter_county['mass'].item() == 150.
            assert quarter_county['n_unweighted'].item() == 6
            assert quarter_county['fractional_support_mass'].item() == 1.5
        else:
            # County-first: quarter county rounds its pooled replica to0;
            # three-quarter county rounds it to2. Origin-first would give0.
            assert full.filter(pl.col('replicate') == 37).collect()['mass'].item() == 2.
