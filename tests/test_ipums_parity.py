import importlib
from unittest.mock import patch

import polars as pl
import pytest
from ipums_fixtures import write_csv

def expected_frame():
    return pl.DataFrame({'code': ['0001', '0001', None], 'weight': [1.25, 2.5, 0.0]})


def test_equal_ordered_values_and_exact_schema():
    parity = importlib.import_module('embedding_data.ipums_parity')
    expected = expected_frame()
    actual = expected_frame()
    assert parity.compare_ordered(expected.lazy(), actual.lazy(), chunk_size=2) == {
        'schema_equal': True, 'values_equal': True, 'expected_rows': 3, 'actual_rows': 3,
    }


@pytest.mark.parametrize('change,rows,schema_equal', [
    ('swapped', 3, True), ('duplicate_loss', 2, True), ('trailing', 4, True),
    ('float', 3, True), ('null', 3, True), ('column_order', 3, False),
    ('dtype', 3, False),
])
def test_comparison_detects_schema_order_multiplicity_and_value_changes(
    change, rows, schema_equal,
):
    parity = importlib.import_module('embedding_data.ipums_parity')
    expected = expected_frame()
    changes = {
        'swapped': expected.reverse(),
        'duplicate_loss': expected.slice(1),
        'trailing': pl.concat([expected, expected.head(1)]),
        'float': expected.with_columns(pl.col('weight').add(1e-12)),
        'null': expected.with_columns(pl.col('code').fill_null('0000')),
        'column_order': expected.select('weight', 'code'),
        'dtype': expected.with_columns(pl.col('weight').cast(pl.Float32)),
    }
    actual = changes[change]
    if change == 'dtype':
        assert expected.equals(actual)
    assert parity.compare_ordered(expected.lazy(), actual.lazy(), chunk_size=2) == {
        'schema_equal': schema_equal, 'values_equal': False,
        'expected_rows': 3, 'actual_rows': rows,
    }


@pytest.mark.parametrize('expected_rows,actual_rows', [(0, 0), (0, 3), (3, 0)])
def test_comparison_handles_empty_streams(expected_rows, actual_rows):
    parity = importlib.import_module('embedding_data.ipums_parity')
    expected = expected_frame().head(expected_rows)
    actual = expected_frame().head(actual_rows)
    assert parity.compare_ordered(expected.lazy(), actual.lazy(), chunk_size=1) == {
        'schema_equal': True, 'values_equal': expected_rows == actual_rows,
        'expected_rows': expected_rows, 'actual_rows': actual_rows,
    }


def test_duplicate_loss_is_detected_when_duplicate_rows_are_identical():
    parity = importlib.import_module('embedding_data.ipums_parity')
    expected = pl.DataFrame({'code': ['0001', '0001', None], 'weight': [1.25, 1.25, 0.0]})
    report = parity.compare_ordered(expected.lazy(), expected.unique(maintain_order=True).lazy())
    assert report == {
        'schema_equal': True, 'values_equal': False, 'expected_rows': 3, 'actual_rows': 2,
    }


@pytest.mark.parametrize('chunk_size', [0, -1, 1.5, True])
def test_comparison_requires_positive_integer_chunk_size(chunk_size):
    parity = importlib.import_module('embedding_data.ipums_parity')
    with pytest.raises(ValueError, match='chunk_size'):
        parity.compare_ordered(
            expected_frame().lazy(), expected_frame().lazy(), chunk_size=chunk_size,
        )


@pytest.mark.parametrize('mismatch', ['none', 'value', 'schema', 'trailing'])
def test_independent_batch_boundaries_skip_empty_batches_and_drain_both_streams(mismatch):
    parity = importlib.import_module('embedding_data.ipums_parity')
    expected = expected_frame()
    actual = expected_frame()
    if mismatch == 'value':
        actual = actual.with_columns(pl.col('weight').add(1.0))
    elif mismatch == 'schema':
        actual = actual.select('weight', 'code')
    elif mismatch == 'trailing':
        actual = pl.concat([actual, actual.head(1)])
    expected_lf, actual_lf = expected.lazy(), actual.lazy()
    drained = []
    observed_options = []

    def batches(self, **options):
        observed_options.append(options)
        frame = expected if self is expected_lf else actual
        widths = [0, 1, 0, 2, 0] if self is expected_lf else [0, 2, 0, 2, 0]
        offset = 0
        for width in widths:
            yield frame.slice(offset, width)
            offset += width
        drained.append('expected' if self is expected_lf else 'actual')

    with patch.object(pl.LazyFrame, 'collect_batches', batches):
        report = parity.compare_ordered(expected_lf, actual_lf, chunk_size=2)
    assert report == {
        'schema_equal': mismatch != 'schema', 'values_equal': mismatch == 'none',
        'expected_rows': 3, 'actual_rows': actual.height,
    }
    assert sorted(drained) == ['actual', 'expected']
    assert observed_options == [
        {'chunk_size': 2, 'maintain_order': True, 'lazy': True, 'engine': 'streaming'},
        {'chunk_size': 2, 'maintain_order': True, 'lazy': True, 'engine': 'streaming'},
    ]


@pytest.mark.parametrize('source', ['acs', 'cps'])
def test_verify_conversion_uses_independently_written_parquet(tmp_path, source):
    parity = importlib.import_module('embedding_data.ipums_parity')
    if source == 'acs':
        csv = 'INDNAICS,OCCSOC,INCWAGE_CPIU_2010\n31M,1110XX,12.5\n001,001010,\n'
        expected = pl.DataFrame({
            'INDNAICS': ['31M', '001'], 'OCCSOC': ['1110XX', '001010'],
            'INCWAGE_CPIU_2010': [12.5, None],
        })
    else:
        csv = 'IND,OCC,INDLY,OCCLY,INCWAGE_CPIU_2010\n170,20,770,30,12.5\n0,,9999,0,\n'
        expected = pl.DataFrame({
            'IND': ['0170', '0000'], 'OCC': ['0020', None], 'INDLY': ['0770', '9999'],
            'OCCLY': ['0030', '0000'], 'INCWAGE_CPIU_2010': [12.5, None],
        })
    csv_gz = write_csv(tmp_path, csv)
    parquet = tmp_path / 'delivery.parquet'
    expected.write_parquet(parquet)
    scratch = tmp_path / 'scratch'
    before = csv_gz.read_bytes(), parquet.read_bytes()
    assert parity.verify_conversion(csv_gz, parquet, source, scratch) == {
        'schema_equal': True, 'values_equal': True, 'expected_rows': 2, 'actual_rows': 2,
    }
    assert (csv_gz.read_bytes(), parquet.read_bytes()) == before
    assert list(scratch.iterdir()) == []


def test_verify_never_casts_actual_parquet_to_conceal_cps_dtype_mismatch(tmp_path):
    parity = importlib.import_module('embedding_data.ipums_parity')
    csv_gz = write_csv(tmp_path, 'IND\n170\n0\n')
    parquet = tmp_path / 'delivery.parquet'
    pl.DataFrame({'IND': [170, 0]}).write_parquet(parquet)
    assert parity.verify_conversion(csv_gz, parquet, 'cps', tmp_path / 'scratch') == {
        'schema_equal': False, 'values_equal': False, 'expected_rows': 2, 'actual_rows': 2,
    }


def test_verify_drains_mismatched_csv_before_temporary_cleanup(tmp_path):
    parity = importlib.import_module('embedding_data.ipums_parity')
    csv_gz = write_csv(tmp_path, 'INDNAICS\n31M\n001\n')
    parquet = tmp_path / 'delivery.parquet'
    pl.DataFrame({'INDNAICS': ['31M', 'different']}).write_parquet(parquet)
    scratch = tmp_path / 'scratch'
    real_batches = pl.LazyFrame.collect_batches
    drained = []

    def batches(self, **options):
        yield from real_batches(self, **options)
        assert len(list(scratch.rglob('*.csv'))) == 1
        drained.append(True)

    with patch.object(pl.LazyFrame, 'collect_batches', batches):
        report = parity.verify_conversion(csv_gz, parquet, 'acs', scratch)
    assert not report['values_equal']
    assert drained == [True, True]
    assert list(scratch.iterdir()) == []


def test_verify_cleans_scratch_on_scan_failure(tmp_path):
    parity = importlib.import_module('embedding_data.ipums_parity')
    csv_gz = write_csv(tmp_path, 'INDNAICS\n31M\n')
    parquet = tmp_path / 'delivery.parquet'
    parquet.write_bytes(b'invalid synthetic parquet')
    scratch = tmp_path / 'scratch'
    with pytest.raises(pl.exceptions.ComputeError):
        parity.verify_conversion(csv_gz, parquet, 'acs', scratch)
    assert list(scratch.iterdir()) == []


def test_verify_rejects_unsupported_source_before_any_io(tmp_path):
    parity = importlib.import_module('embedding_data.ipums_parity')
    with pytest.raises(ValueError, match='source'):
        parity.verify_conversion(tmp_path / 'missing.gz', tmp_path / 'missing', 'other', tmp_path)
    assert list(tmp_path.iterdir()) == []
