import json
from decimal import Decimal

import polars as pl
import pytest

from embedding_data.ipums_weights import measure_weights, scan_numeric_csv

def ddi(*names, decimals=4):
    return {'variables': [{'name': name, 'label': name, 'implied_decimals': decimals,
                           'categories': [], 'instructions': []} for name in names]}


def test_decimal_storage_household_helper_and_negative_replicate(tmp_path):
    csv = tmp_path / 'weights.csv'
    csv.write_text('WTFINL,ASECWTH,REPWTP1,REPWTP\n123.4500,10.0000,-2.0000,1\n'
                   '0.0000,0.0000,999999.0000,1\n')
    diagnostics, rules = measure_weights(csv, ddi('WTFINL', 'ASECWTH', 'REPWTP1', 'REPWTP'),
                                         'cps', 'asec')
    rows = {row['variable']: row for row in diagnostics.to_dicts()}
    assert rows['WTFINL']['sum_exact'] == '123.4500'
    assert rows['WTFINL']['sum'] == 123.45
    assert rows['WTFINL']['alternative_sum_exact'] == '0.01234500'
    assert rows['WTFINL']['explicit_decimal_rows'] == 2
    assert rows['WTFINL']['scale'] == 4
    assert rows['ASECWTH']['family'] == 'household'
    assert rows['REPWTP1']['negative_rows'] == 1
    assert rows['REPWTP1']['maximum'] == 999999
    assert rows['REPWTP1']['extrema_status'] == 'unexplained_without_documentation'
    assert rows['REPWTP']['family'] == 'helper'
    assert rows['REPWTP']['sum_exact'] is None
    assert rules['parquet_parity'] == 'external_required_all_variables'
    assert rules['production_adoption'] == 'pending'
    json.dumps(rules, allow_nan=False)


def test_all_replicates_and_integer_storage(tmp_path):
    names = [f'REPWTP{i}' for i in range(1, 81)]
    csv = tmp_path / 'weights.csv'
    csv.write_text(','.join(names) + '\n' + ','.join(['123'] * 80) + '\n')
    diagnostics, rules = measure_weights(csv, ddi(*names, decimals=0), 'acs', 'core')
    assert diagnostics.height == 80
    assert diagnostics['sum_exact'].to_list() == ['123'] * 80
    assert rules['families']['replicate']['variables'] == 80
    assert rules['families']['replicate']['sum_min_exact'] == '123'


def test_lexical_missing_invalid_and_unknown_exponent(tmp_path):
    csv = tmp_path / 'weights.csv'
    csv.write_text('PERWT,x\n,1\n"",2\nabc,3\n1.20,4\n')
    diagnostics, rules = measure_weights(csv, ddi('PERWT', decimals=None), 'acs', 'core')
    row = diagnostics.row(0, named=True)
    assert (row['null_rows'], row['blank_rows'], row['non_numeric_rows']) == (1, 1, 1)
    assert row['implied_decimals'] is None
    assert row['alternative_sum_exact'] is None
    with pytest.raises(ValueError, match='invalid weight'):
        scan_numeric_csv(csv, diagnostics, 'acs')


@pytest.mark.parametrize('value', ['1e4', '1E-3', '9' * 39, '0.' + '1' * 39])
def test_unsupported_numeric_precision_rejected(tmp_path, value):
    csv = tmp_path / 'weights.csv'
    csv.write_text('PERWT\n' + value + '\n')
    with pytest.raises(ValueError, match='precision|exponent'):
        measure_weights(csv, ddi('PERWT'), 'acs', 'core')


def test_exact_scan_and_reductions_survive_order_and_partitioning(tmp_path):
    values = ['10000000000000000.0001', '0.0002', '-10000000000000000.0000']
    sums = []
    for i, ordered in enumerate((values, list(reversed(values)))):
        csv = tmp_path / f'{i}.csv'
        csv.write_text('PERWT,STATEFIP,INDNAICS\n' + ''.join(
            f'{value},1,31M\n' for value in ordered))
        diagnostics, _ = measure_weights(csv, ddi('PERWT'), 'acs', 'core')
        scan = scan_numeric_csv(csv, diagnostics, 'acs')
        assert scan.collect_schema()['PERWT'] == pl.Decimal(38, 4)
        assert scan.collect_schema()['INDNAICS'] == pl.String
        for size in (1, 2, 7):
            batches = list(scan.collect_batches(chunk_size=size, engine='streaming'))
            sums.append(sum((batch['PERWT'].sum() for batch in batches), Decimal(0)))
        assert diagnostics['sum_exact'].item() == '0.0003'
    assert sums == [Decimal('0.0003')] * 6


def test_large_integer_precision_bound_cannot_drop_trailing_zeros(tmp_path):
    csv = tmp_path / 'weights.csv'
    csv.write_text('PERWT\n' + '1' + '0' * 38 + '\n')
    with pytest.raises(ValueError, match='precision'):
        measure_weights(csv, ddi('PERWT'), 'acs', 'core')


def test_numeric_nulls_empty_input_and_unknown_weight_family(tmp_path):
    csv = tmp_path / 'weights.csv'
    csv.write_text('AUTO_WEIGHT,PERWT,x\n2.00,,1\n3.00,,2\n')
    metadata = ddi('AUTO_WEIGHT', 'PERWT')
    metadata['variables'][0]['label'] = 'Household weight supplied automatically'
    diagnostics, rules = measure_weights(csv, metadata, 'acs', 'core')
    assert diagnostics.filter(pl.col('variable').eq('AUTO_WEIGHT'))['family'].item() == 'household'
    assert diagnostics.filter(pl.col('variable').eq('PERWT'))['sum_exact'].item() is None
    assert scan_numeric_csv(csv, diagnostics, 'acs').collect()['PERWT'].null_count() == 2
    assert rules['families']['household']['csv_factors'] == [1]
    csv.write_text('PERWT\n')
    diagnostics, _ = measure_weights(csv, ddi('PERWT'), 'acs', 'core')
    assert diagnostics['rows'].item() == 0
    assert diagnostics['sum_exact'].item() is None


def test_weight_schema_and_every_asec_replicate(tmp_path):
    names = [f'REPWTP{i}' for i in range(1, 161)]
    csv = tmp_path / 'weights.csv'
    csv.write_text(','.join(names) + '\n' + ','.join(['-0.0100'] * 160) + '\n')
    result, _ = measure_weights(csv, ddi(*names), 'cps', 'asec')
    assert result.height == 160
    assert result['negative_rows'].to_list() == [1] * 160
    assert result.schema == {
        'source': pl.String, 'set_name': pl.String, 'variable': pl.String, 'family': pl.String,
        'implied_decimals': pl.Int64, 'scale': pl.Int64, 'rows': pl.UInt64,
        'null_rows': pl.UInt64, 'blank_rows': pl.UInt64, 'non_numeric_rows': pl.UInt64,
        'explicit_decimal_rows': pl.UInt64, 'negative_rows': pl.UInt64, 'zero_rows': pl.UInt64,
        'minimum': pl.Float64, 'maximum': pl.Float64, 'sum': pl.Float64,
        'minimum_exact': pl.String, 'maximum_exact': pl.String, 'sum_exact': pl.String,
        'alternative_sum_exact': pl.String, 'extrema_status': pl.String,
    }
