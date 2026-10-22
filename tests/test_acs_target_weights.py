import shutil
from decimal import Decimal

import polars as pl
import pytest
from acs_mapping_fixtures import forbid_external_access
from acs_target_fixtures import authenticated_mapping, prepare_target_delivery

from embedding_data.acs_target_inputs import select_targets
from embedding_data.acs_target_weights import WEIGHT_NAMES, _scan_weights, weighted_source

@pytest.fixture(scope='module')
def template(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patches:
        yield authenticated_mapping(tmp_path_factory.mktemp('weight-template'), patches,
                                    prepare_acs=prepare_target_delivery)


@pytest.fixture
def selected(tmp_path, monkeypatch, template):
    forbid_external_access(monkeypatch)
    data_dir = tmp_path / 'data'
    shutil.copytree(template['data_dir'], data_dir)
    return select_targets(data_dir, 'mapping', request=template['request'],
                          expected_mapping_outputs_sha256=template['mapping_outputs_sha256'])


def test_exact_weights_keep_positions_duplicates_and_literal_units(
        selected, tmp_path, monkeypatch):
    import dotenv
    import httpx
    import ipumspy

    from embedding_data import acs_mapping_references, ipums_census_access, ipums_references
    from embedding_data.acs_target_contract import PRODUCTS
    from embedding_data.acs_target_membership import family_rows
    from embedding_data.acs_target_rules import read_rules
    from embedding_data.acs_target_units import build_units

    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError('external access attempted')

    for owner, names in [(dotenv, ('load_dotenv', 'dotenv_values')),
                         (httpx, ('Client', 'AsyncClient')),
                         (ipumspy, ('IpumsApiClient',)),
                         (ipums_census_access, ('dotenv_values', 'read_credential')),
                         (ipums_references, ('make_client',)),
                         (acs_mapping_references, ('make_client',))]:
        for name in names:
            monkeypatch.setattr(owner, name, forbidden)
    source = selected.upstream.sources['acs/core']
    assert read_rules(source).domains['QMIGRAT1']['dtype'] == 'Int64'
    original = pl.read_parquet(source.parquet)
    with weighted_source(selected, tmp_path / 'scratch') as weighted:
        result = weighted.frame.collect()
        assert result['source_row'].to_list() == list(range(original.height))
        assert result['source_row'].dtype == pl.UInt64
        assert result['source_parquet_sha256'].unique().to_list() == [
            source.parquet_record['sha256']]
        assert set(WEIGHT_NAMES) == {'PERWT', *(f'REPWTP{r}' for r in range(1, 81))}
        assert result['PERWT'].to_list() == [Decimal('100.25')] * original.height
        assert result['REPWTP37'].to_list() == [Decimal('-2.5')] * original.height
        assert original.row(0) == original.row(-1)
        assert result.drop('source_row').row(0) == result.drop('source_row').row(-1)
        assert weighted.rules['numeric_rule'] == 'literal_csv_value'
        rules, units = read_rules(source), build_units(selected)
        for product in PRODUCTS:
            if product.view != 'observed':
                continue
            rows = family_rows(weighted.frame, product, rules, units)
            expected = original.height
            if product.family == 'migration_flow' and product.years == (2024,):
                expected = 1 if product.evidence_policy == 'strict' else 2
            assert rows.members.select(pl.len()).collect().item() == expected
            funnel = rows.diagnostics.filter(pl.col('partition_kind').eq(
                'first_exclusion')).collect()
            assert funnel['n_unweighted'].sum() == original.height
            assert sum(Decimal(value) for value in funnel['weight_sum_exact']) == (
                Decimal('100.25') * original.height)
    assert not list((tmp_path / 'scratch').iterdir())
    assert set(original['QMIGRAT1'].to_list()) == {None, 0, 4}
    assert calls == []


@pytest.mark.parametrize('mutation', ['raw', 'companion', 'nonweight', 'count', 'order',
                                    'source_hash', 'source_row', 'schema'])
def test_alignment_rejects_mutations_before_yield(selected, tmp_path, mutation):
    import gzip
    source = selected.upstream.sources['acs/core']
    file = selected.tables['acs_core_canonical']
    frame = pl.read_parquet(file)
    if mutation == 'raw':
        raw = selected.data_dir / 'raw' / next(c['path'] for c in source.raw_citations
                                             if c['path'].endswith('.csv.gz'))
        with gzip.open(raw, 'rt') as stream:
            body = stream.read()
        with gzip.open(raw, 'wt') as stream:
            stream.write(body.replace('100.25', '100.26', 1))
    elif mutation == 'nonweight':
        file = source.parquet
        frame = pl.read_parquet(file).with_columns(pl.lit(99).alias('AGE'))
    elif mutation == 'companion':
        frame = frame.with_columns(pl.lit(99).alias('AGE'))
    elif mutation == 'count':
        frame = frame.head(1)
    elif mutation == 'order':
        frame = frame.reverse()
    elif mutation == 'source_hash':
        frame = frame.with_columns(pl.lit('b' * 64).alias('source_parquet_sha256'))
    elif mutation == 'source_row':
        frame = frame.with_columns(pl.lit(0, dtype=pl.UInt64).alias('source_row'))
    elif mutation == 'schema':
        frame = frame.with_columns(pl.col('AGE').cast(pl.Float64))
    if mutation != 'raw':
        frame.write_parquet(file)
    with pytest.raises(ValueError):
        with weighted_source(selected, tmp_path / 'scratch'):
            pytest.fail('invalid alignment yielded')


@pytest.mark.parametrize('change', ['null', 'missing', 'extra', 'exponent', 'invalid',
                                  'overflow', 'scale', 'ddi_exponent', 'blank', 'negative_point'])
def test_bad_required_weight_fails_before_aggregation(tmp_path, change):
    import csv

    from acs_target_fixtures import weights

    row = {'YEAR': '2024', **weights('100.25', {37: '-2.5'})}
    ddi = {'variables': [{'name': name, 'implied_decimals': 0} for name in row]}
    if change == 'missing':
        del row['REPWTP80']
    elif change == 'extra':
        row['REPWTP81'] = '1'
    elif change == 'ddi_exponent':
        next(v for v in ddi['variables'] if v['name'] == 'PERWT')['implied_decimals'] = -1
    elif change == 'negative_point':
        row['PERWT'] = '-1'
    else:
        row['REPWTP37'] = {'null': None, 'blank': '', 'exponent': '1e2',
                            'invalid': 'bad', 'overflow': '9' * 39,
                            'scale': '0.' + '1' * 39}[change]
    csv_path = tmp_path / 'weights.csv'
    with csv_path.open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    with pytest.raises((ValueError, pl.exceptions.PolarsError)):
        _scan_weights(csv_path, ddi)


def test_alignment_seam_rejects_reordered_raw_header(tmp_path):
    from types import SimpleNamespace

    from embedding_data import target_io
    from embedding_data.acs_mapping_contract import ANNOTATION_SCHEMA
    from embedding_data.acs_target_weights import _validate_alignment

    original = pl.DataFrame({'AGE': [22, 23], 'PERWT': [100.25, 100.25]})
    file = tmp_path / 'original.parquet'
    original.write_parquet(file)
    source = SimpleNamespace(parquet=file, parquet_record=target_io.file_record(file))
    companion = original.lazy().with_columns(
        pl.lit([] if isinstance(dtype, pl.List) else None, dtype=dtype).alias(name)
        for name, dtype in ANNOTATION_SCHEMA.items()).with_columns(
            pl.int_range(0, pl.len(), dtype=pl.UInt64).alias('source_row'),
            pl.lit(source.parquet_record['sha256']).alias('source_parquet_sha256'))
    numeric = original.lazy().with_row_index('source_row').with_columns(
        pl.col('source_row').cast(pl.UInt64))
    diagnostics = pl.DataFrame({'variable': ['PERWT']})
    _validate_alignment(source, numeric, companion, diagnostics)
    for bad in [numeric.select('source_row', 'PERWT', 'AGE'),
                numeric.with_columns(pl.lit(99, dtype=pl.Int64).alias('AGE')), numeric.head(1),
                numeric.reverse()]:
        with pytest.raises(ValueError):
            _validate_alignment(source, bad, companion, diagnostics)
    for bad in [companion.reverse(), companion.head(1),
                companion.with_columns(pl.lit('b' * 64).alias('source_parquet_sha256')),
                companion.with_columns(pl.lit(0, dtype=pl.UInt64).alias('source_row')),
                companion.with_columns(pl.col('AGE').cast(pl.Float64))]:
        with pytest.raises(ValueError):
            _validate_alignment(source, numeric, bad, diagnostics)


def test_helper_and_household_diagnostics_never_enter_estimator_weights(tmp_path):
    from acs_target_fixtures import weights

    file = tmp_path / 'helper.csv'
    pl.DataFrame([weights('100.25', {37: '-2.5'}) | {'REPWTP': '1', 'HHWT': '9'}]).write_csv(
        file)
    numeric, diagnostics, _ = _scan_weights(file, {'variables': []})
    families = dict(diagnostics.select('variable', 'family').iter_rows())
    assert families['REPWTP'] == 'helper'
    assert families['HHWT'] == 'household'
    exact = numeric.select(WEIGHT_NAMES).collect()
    assert exact.width == 81
    assert all(isinstance(dtype, pl.Decimal) for dtype in exact.dtypes)
    assert exact['PERWT'].item() == Decimal('100.25')
    assert exact['REPWTP37'].item() == Decimal('-2.5')
    assert 'REPWTP' not in exact and 'HHWT' not in exact
