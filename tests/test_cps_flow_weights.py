'''Tests for the literal Decimal weights of the CPS job flows.'''

from decimal import Decimal
from functools import reduce
from operator import add

import polars as pl
import pytest
from cps_flow_fixtures import (
    asec_row,
    monthly_row,
    no_live_clients,  # noqa: F401
    offline_guards,
    seed_upstreams,
)

from embedding_data import cps_flow_inputs, cps_flow_weights, ipums_parity
from embedding_data.cps_flow_weights import WEIGHTS, weight_status_expr, weighted_sources

REPLICATES = [f'REPWTP{number}' for number in range(1, 161)]


def selected_from(tmp_path, monthly, asec):
    seeded = seed_upstreams(tmp_path, monthly=monthly, asec=asec)
    return cps_flow_inputs.select_inputs(seeded.data_dir, seeded.request)


def write_csv(file, columns, rows):
    file.write_text('\n'.join([','.join(columns), *(','.join(row) for row in rows)]) + '\n')
    return file


def asec_csv(tmp_path, replicates, *, helper=True, full='ASECWT'):
    columns = [full, *(['REPWTP'] if helper else []), *replicates]
    rows = [['1.5', *(['1'] if helper else []), *['2.5'] * len(replicates)]]
    return write_csv(tmp_path / 'asec.csv', columns, rows)


@pytest.fixture(scope='module')
def seeded_selected(tmp_path_factory):
    '''Rows whose weights differ by position, so that a misaligned join shows.'''
    monthly = [monthly_row(MONTH=1 + number % 2, CPSIDV=number + 1,
                           LNKFW1MWT=f'{number}00.2500') for number in range(5)]
    asec = [asec_row(YEAR=2025, ASECWT='10.2500', REPWTP3='-4.0000'),
            asec_row(YEAR=2026, CPSIDV=2, ASECWT='20.5000', REPWTP160='7.7500')]
    return selected_from(tmp_path_factory.mktemp('weights'), monthly, asec)


def test_weights_are_the_literal_csv_text(tmp_path):
    monthly = [monthly_row(CPSIDV=number + 1, LNKFW1MWT='0.1') for number in range(10)]
    selected = selected_from(tmp_path, monthly, [asec_row()])
    with weighted_sources(selected, tmp_path / 'scratch') as weighted:
        frame = weighted.monthly.collect()
    assert frame['LNKFW1MWT'].sum() == Decimal('1.0')
    assert frame.schema['LNKFW1MWT'] == pl.Decimal(38, 1)
    stored = pl.read_parquet(selected.monthly.parquet)['LNKFW1MWT'].to_list()
    assert reduce(add, stored) != 1.0


def test_frames_are_lazy_and_carry_exactly_the_required_columns(seeded_selected, tmp_path):
    with weighted_sources(seeded_selected, tmp_path / 'scratch') as weighted:
        assert isinstance(weighted.monthly, pl.LazyFrame)
        assert isinstance(weighted.asec, pl.LazyFrame)
        assert weighted.monthly.collect_schema().names() == ['source_row', 'LNKFW1MWT']
        assert weighted.asec.collect_schema().names() == ['source_row', 'ASECWT', *REPLICATES]
        monthly, asec = weighted.monthly.collect(), weighted.asec.collect()
    assert monthly.schema['source_row'] == asec.schema['source_row'] == pl.UInt64
    assert monthly['source_row'].to_list() == [0, 1, 2, 3, 4]
    assert monthly['LNKFW1MWT'].to_list() == [
        Decimal(f'{number}00.2500') for number in range(5)]
    assert asec['ASECWT'].to_list() == [Decimal('10.2500'), Decimal('20.5000')]
    assert asec['REPWTP3'].to_list() == [Decimal('-4.0000'), Decimal('1500.1234')]
    assert asec['REPWTP160'].to_list() == [Decimal('1500.1234'), Decimal('7.7500')]
    assert all(isinstance(dtype, pl.Decimal) for name, dtype in asec.schema.items()
               if name != 'source_row')


def test_diagnostics_and_rules_are_kept_for_both_sets(seeded_selected, tmp_path):
    with weighted_sources(seeded_selected, tmp_path / 'scratch') as weighted:
        assert set(weighted.diagnostics) == set(weighted.rules) == {'monthly', 'asec'}
        assert 'LNKFW1MWT' in weighted.diagnostics['monthly']['variable'].to_list()
        assert 'ASECWT' in weighted.diagnostics['asec']['variable'].to_list()
        assert weighted.rules['asec']['set_name'] == 'asec'
        assert weighted.rules['monthly']['numeric_rule'] == 'literal_csv_value'


@pytest.mark.parametrize(('schema_equal', 'values_equal', 'extra_expected', 'extra_actual'), [
    (True, False, 0, 0),
    (False, True, 0, 0),
    (True, True, -1, 0),
    (True, True, 0, 1),
], ids=['values', 'schema', 'expected-rows', 'actual-rows'])
def test_positional_alignment_failure_is_refused(seeded_selected, tmp_path, monkeypatch,
                                                 schema_equal, values_equal, extra_expected,
                                                 extra_actual):
    def report(left, right, **kwargs):
        rows = right.select(pl.len()).collect().item()
        return {'schema_equal': schema_equal, 'values_equal': values_equal,
                'expected_rows': rows + extra_expected, 'actual_rows': rows + extra_actual}

    monkeypatch.setattr(ipums_parity, 'compare_ordered', report)
    with pytest.raises(ValueError, match='before weight alignment'):
        with weighted_sources(seeded_selected, tmp_path / 'scratch'):
            pytest.fail('the context must not be entered')


def test_alignment_compares_every_nonweight_column_in_each_file(seeded_selected, tmp_path,
                                                                monkeypatch):
    compared = []
    original = ipums_parity.compare_ordered

    def spy(left, right, **kwargs):
        compared.append(left.collect_schema().names())
        assert left.collect_schema().names() == right.collect_schema().names()
        return original(left, right, **kwargs)

    monkeypatch.setattr(ipums_parity, 'compare_ordered', spy)
    with weighted_sources(seeded_selected, tmp_path / 'scratch'):
        pass
    [monthly, asec] = compared
    assert monthly[0] == 'source_row' and 'MISH' in monthly and 'CPSIDV' in monthly
    assert 'LNKFW1MWT' not in monthly and 'WTFINL' not in monthly
    assert asec[0] == 'source_row' and 'QOCCLY' in asec and 'CPSIDV' in asec
    assert 'ASECWT' not in asec and 'REPWTP160' not in asec and 'ASECWTH' not in asec


def test_scanned_columns_must_equal_the_stored_columns(seeded_selected, tmp_path, monkeypatch):
    scan = cps_flow_weights.ipums_weights.scan_numeric_csv
    monkeypatch.setattr(cps_flow_weights.ipums_weights, 'scan_numeric_csv',
                        lambda *args: scan(*args).drop('AGE'))
    with pytest.raises(ValueError, match='raw ordered source columns differ'):
        with weighted_sources(seeded_selected, tmp_path / 'scratch'):
            pytest.fail('the context must not be entered')


def test_a_changed_nonweight_value_in_the_csv_is_refused(tmp_path, monkeypatch):
    selected = selected_from(tmp_path, [monthly_row(AGE=30), monthly_row(CPSIDV=2, AGE=50)],
                             [asec_row()])
    scan = cps_flow_weights.ipums_weights.scan_numeric_csv
    monkeypatch.setattr(
        cps_flow_weights.ipums_weights, 'scan_numeric_csv',
        lambda *args: scan(*args).with_columns(pl.col('AGE').reverse()))
    with pytest.raises(ValueError, match='before weight alignment'):
        with weighted_sources(selected, tmp_path / 'scratch'):
            pytest.fail('the context must not be entered')


@pytest.mark.parametrize(('names', 'message'), [
    ([name for name in REPLICATES if name != 'REPWTP160'], 'exactly'),
    ([*REPLICATES, 'REPWTP161'], 'exactly'),
    ([name for name in REPLICATES if name != 'REPWTP1'], 'exactly'),
], ids=['no-160', 'extra-161', 'no-1'])
def test_required_replicate_names_are_exact(tmp_path, names, message):
    with pytest.raises(ValueError, match=message):
        cps_flow_weights._scan(asec_csv(tmp_path, names), {'variables': []}, 'asec')


def test_the_unnumbered_helper_is_ignored(tmp_path):
    csv = asec_csv(tmp_path, REPLICATES)
    numeric, diagnostics, _ = cps_flow_weights._scan(csv, {'variables': []}, 'asec')
    assert 'REPWTP' in diagnostics['variable'].to_list()
    assert numeric.select('source_row', *WEIGHTS['asec']).collect().width == 162
    without = asec_csv(tmp_path, REPLICATES, helper=False)
    assert cps_flow_weights._scan(without, {'variables': []}, 'asec')[1].height == 161


def test_the_full_weight_is_required_by_name(tmp_path):
    with pytest.raises(ValueError, match='exactly'):
        cps_flow_weights._scan(asec_csv(tmp_path, REPLICATES, full='ASECWTH'),
                               {'variables': []}, 'asec')
    monthly = write_csv(tmp_path / 'monthly.csv', ['WTFINL', 'AGE'], [['1.0', '5']])
    with pytest.raises(ValueError, match='exactly'):
        cps_flow_weights._scan(monthly, {'variables': []}, 'monthly')


@pytest.mark.parametrize(('monthly', 'asec'), [
    ([monthly_row(LNKFW1MWT='-1.0000')], [asec_row()]),
    ([monthly_row()], [asec_row(ASECWT='-1.0000')]),
], ids=['monthly-link-weight', 'asec-weight'])
def test_negative_full_weight_fails(tmp_path, monthly, asec):
    selected = selected_from(tmp_path, monthly, asec)
    with pytest.raises(ValueError, match='negative full weight'):
        with weighted_sources(selected, tmp_path / 'scratch'):
            pytest.fail('the context must not be entered')


def test_a_negative_replicate_is_kept_and_a_null_weight_stays_null(tmp_path):
    monthly = [monthly_row(LNKFW1MWT=None), monthly_row(CPSIDV=2)]
    asec = [asec_row(REPWTP7='-2.5000', ASECWT=None), asec_row(YEAR=2026, CPSIDV=2)]
    selected = selected_from(tmp_path, monthly, asec)
    with weighted_sources(selected, tmp_path / 'scratch') as weighted:
        link_weights = weighted.monthly.collect()['LNKFW1MWT'].to_list()
        full = weighted.asec.collect()
    assert link_weights == [None, Decimal('1500.1234')]
    assert full['REPWTP7'].to_list() == [Decimal('-2.5000'), Decimal('1500.1234')]
    assert full['ASECWT'].to_list() == [None, Decimal('1500.1234')]


def test_link_weight_status_values():
    frame = pl.DataFrame({
        'weight': [Decimal('1.5'), Decimal('0.0'), None, Decimal('2.0'), None, Decimal('0.0'),
                   Decimal('0.5')],
        'link_type': ['one_month', 'one_month', 'one_month', 'two_month', 'two_month',
                      'two_month', 'one_month'],
    }, schema={'weight': pl.Decimal(38, 1), 'link_type': pl.String})
    result = frame.select(weight_status_expr(pl.col('weight'), pl.col('link_type')).alias('s'))
    assert result['s'].to_list() == ['positive', 'zero', 'null', 'not_linkable',
                                     'not_linkable', 'not_linkable', 'positive']
    assert result.schema['s'] == pl.String


def test_scratch_is_empty_after_exit_and_verify_runs_twice(seeded_selected, tmp_path,
                                                          monkeypatch):
    calls = []
    scratch = tmp_path / 'scratch'
    verify = cps_flow_inputs.SelectedInputs.verify

    def spy(self):
        calls.append(sorted(path.name for path in scratch.rglob('*.csv')))
        verify(self)

    monkeypatch.setattr(cps_flow_inputs.SelectedInputs, 'verify', spy)
    with weighted_sources(seeded_selected, scratch):
        inside = sorted(path.name for path in scratch.rglob('*.csv'))
    assert inside == ['cps_00001.csv', 'cps_00002.csv']
    assert len(calls) == 2
    assert calls[0] == []
    assert list(scratch.iterdir()) == []


def test_scratch_is_empty_after_an_exception_and_verify_still_runs(seeded_selected, tmp_path,
                                                                  monkeypatch):
    calls = []
    scratch = tmp_path / 'scratch'
    verify = cps_flow_inputs.SelectedInputs.verify

    def spy(self):
        calls.append(1)
        verify(self)

    monkeypatch.setattr(cps_flow_inputs.SelectedInputs, 'verify', spy)
    with pytest.raises(RuntimeError, match='boom'):
        with weighted_sources(seeded_selected, scratch):
            raise RuntimeError('boom')
    assert len(calls) == 2
    assert list(scratch.iterdir()) == []


def spoil(file):
    file.write_bytes(file.read_bytes()[:-3] + b'xyz')


def test_changed_selection_is_refused_on_entry(tmp_path):
    selected = selected_from(tmp_path, [monthly_row()], [asec_row()])
    spoil(selected.asec.csv_gz)
    with pytest.raises(ValueError, match='selected inputs changed'):
        with weighted_sources(selected, tmp_path / 'scratch'):
            pytest.fail('the context must not be entered')
    assert not (tmp_path / 'scratch').exists()


def test_changed_selection_is_refused_on_exit_and_scratch_is_removed(tmp_path):
    selected = selected_from(tmp_path, [monthly_row()], [asec_row()])
    scratch = tmp_path / 'scratch'
    with pytest.raises(ValueError, match='selected inputs changed'):
        with weighted_sources(selected, scratch) as weighted:
            weighted.monthly.collect()
            spoil(selected.monthly.csv_gz)
    assert list(scratch.iterdir()) == []


def test_recovery_reads_no_environment_and_builds_no_client(seeded_selected, tmp_path,
                                                            monkeypatch):
    counts = offline_guards(monkeypatch)
    with weighted_sources(seeded_selected, tmp_path / 'scratch') as weighted:
        weighted.monthly.collect()
    assert counts == {'network': 0, 'environment_file': 0, 'live_client': 0}
