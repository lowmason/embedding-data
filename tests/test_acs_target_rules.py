'''Exact delivered evidence meanings and substantive applicability gates.'''

from copy import deepcopy
from dataclasses import replace

import polars as pl
import pytest
from acs_mapping_fixtures import forbid_external_access
from acs_target_fixtures import FLAG_LABELS, selected_target_fixture

from embedding_data.acs_target_rules import FlagRules, classify_flag, read_rules, required_flags

@pytest.fixture(scope='module')
def selected(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patches:
        yield selected_target_fixture(tmp_path_factory.mktemp('rules-input'), patches)


def test_zero_needs_substantive_applicability_and_missing_is_unavailable():
    rules = FlagRules(
        'acs-target-rules-v1',
        {
            'QIND': {
                'dtype': 'Int64',
                'values': {
                    '0': {
                        'label': 'Original entry or Inapplicable (not in universe)',
                        'status': 'nonallocation',
                    },
                    '1': {'label': 'Allocated', 'status': 'allocated'},
                },
            }
        },
        {},
        {},
    )
    assert classify_flag('0', 'QIND', True, rules) == 'nonallocation'
    assert classify_flag('0', 'QIND', False, rules) == 'not_applicable'
    assert classify_flag(None, 'QIND', True, rules) == 'unavailable'
    assert classify_flag(None, 'absent', True, rules) == 'unavailable'
    for applicable in (True, False):
        with pytest.raises(ValueError, match='domain'):
            classify_flag('9', 'QIND', applicable, rules)
        with pytest.raises(ValueError, match='domain'):
            classify_flag('0', 'absent', applicable, rules)


@pytest.mark.parametrize(
    'family,extra',
    [
        ('staffing_pattern', ()),
        ('area_mix', ('QPWSTAT2', 'QTRANWOR')),
        ('commuting_flow', ('QPWSTAT2', 'QTRANWOR')),
        ('migration_flow', ('QMIGRAT1', 'QMIGPLC1')),
    ],
)
@pytest.mark.parametrize('universe', ['civilian_employed', 'private_wage_salary'])
def test_required_evidence_is_family_and_universe_specific(family, extra, universe):
    expected = ('QEMPSTAT', 'QIND', 'QOCC')
    if universe == 'private_wage_salary':
        expected += ('QCLASSWK',)
    assert required_flags(family, universe) == expected + extra


@pytest.mark.parametrize(
    'family,universe', [('wrong', 'civilian_employed'), ('area_mix', 'wrong')]
)
def test_unknown_product_definition_is_rejected(family, universe):
    with pytest.raises(ValueError):
        required_flags(family, universe)


def test_authenticated_rules_freeze_every_literal_pair_dtype_and_locator(selected, monkeypatch):
    forbid_external_access(monkeypatch)
    source = selected.upstream.sources['acs/core']
    rules = read_rules(source)
    assert rules.version == 'acs-target-rules-v1'
    for name, labels in FLAG_LABELS.items():
        expected = {
            str(k): v
            for k, v in (labels.items() if isinstance(labels, dict) else enumerate(labels))
        }
        domain = rules.domains[name]
        assert {k: v['label'] for k, v in domain['values'].items()} == expected
        assert domain['dtype'] == ('String' if name == 'QMIGRAT1' else 'Int64')
        assert domain['reference_locator'] == f'dataDscr/var[@name="{name}"]'
        assert rules.references[name]['citation'] in source.raw_citations
        for code in expected:
            ordinary = ('nonallocation', 'edited_failed_edit', 'unavailable',
                        'unavailable', 'allocated', 'unavailable', 'unavailable',
                        'unavailable', 'edited_failed_edit')
            statuses = {
                'QEMPSTAT': ordinary, 'QCLASSWK': ordinary, 'QIND': ordinary,
                'QOCC': ordinary, 'QMIGRAT1': ordinary,
                'QMIGPLC1': ('nonallocation', 'edited_failed_edit', 'edited_failed_edit',
                             'edited_failed_edit', 'edited_failed_edit', 'unavailable',
                             'edited_failed_edit', 'unavailable', 'edited_failed_edit'),
                'QPWSTAT2': {'0': 'nonallocation', '4': 'allocated'},
                'QTRANWOR': {'0': 'nonallocation', '4': 'allocated'},
            }
            expected_status = statuses[name]
            status = (expected_status[code] if isinstance(expected_status, dict)
                      else expected_status[int(code)])
            assert classify_flag(code, name, True, rules) == status
            assert classify_flag(code, name, False, rules) == 'not_applicable'
    assert classify_flag('4', 'QMIGPLC1', True, rules) == 'edited_failed_edit'
    assert classify_flag('4', 'QIND', True, rules) == 'allocated'
    assert rules.domains['QIND']['values']['8']['label'] == 'Original entry missing or failed edit'
    assert rules.universe_categories['EMPSTATD']['eligible'] == ['10', '12']
    assert rules.universe_categories['CLASSWKRD']['eligible'] == ['22', '23']
    assert rules.universe_categories['TRANWORK']['home'] == ['80']
    assert rules.universe_categories['TRANWORK']['not_applicable'] == ['00']
    assert rules.universe_categories['MIGRATE1']['eligible'] == ['2', '3']


@pytest.mark.parametrize(
    'defect', ['unknown_label', 'duplicate', 'employment', 'private', 'migration', 'transport']
)
def test_delivered_metadata_corruption_fails(selected, defect):
    source = selected.upstream.sources['acs/core']
    ddi = deepcopy(source.ddi)
    variable = {
        'employment': 'EMPSTATD',
        'private': 'CLASSWKRD',
        'migration': 'MIGRATE1',
        'transport': 'TRANWORK',
    }.get(defect, 'QIND')
    record = next(v for v in ddi['variables'] if v['name'] == variable)
    if defect == 'duplicate':
        record['categories'].append(record['categories'][0].copy())
    else:
        record['categories'][0]['label'] = 'undocumented meaning'
    with pytest.raises(ValueError, match='DDI|label|categor'):
        read_rules(replace(source, ddi=ddi))


def test_missing_variable_and_all_null_string_are_unavailable(selected, tmp_path):
    source = selected.upstream.sources['acs/core']
    frame = (
        pl.read_parquet(source.parquet)
        .drop('QCLASSWK')
        .with_columns(pl.lit(None, dtype=pl.String).alias('QMIGRAT1'))
    )
    file = tmp_path / 'source.parquet'
    frame.write_parquet(file)
    ddi = deepcopy(source.ddi)
    ddi['variables'] = [v for v in ddi['variables'] if v['name'] != 'QCLASSWK']
    rules = read_rules(replace(source, parquet=file, ddi=ddi))
    assert 'QCLASSWK' not in rules.domains
    assert rules.domains['QMIGRAT1']['dtype'] == 'String'
    assert classify_flag(None, 'QMIGRAT1', True, rules) == 'unavailable'


@pytest.mark.parametrize('value', ['9', 'unknown'])
def test_unknown_nonmissing_domain_is_checked_before_any_eligibility(selected, tmp_path, value):
    source = selected.upstream.sources['acs/core']
    file = tmp_path / 'source.parquet'
    pl.read_parquet(source.parquet).with_columns(
        pl.lit(value).alias('QIND'), pl.lit(0).alias('EMPSTATD')
    ).write_parquet(file)
    with pytest.raises(ValueError, match='domain'):
        read_rules(replace(source, parquet=file))


@pytest.mark.parametrize('dtype', [pl.Int64, pl.String])
def test_documented_zero_four_in_original_integer_and_string_storage(selected, tmp_path, dtype):
    source = selected.upstream.sources['acs/core']
    file = tmp_path / 'original-schema.parquet'
    frame = pl.read_parquet(source.parquet)
    values = [0, 4] + [0] * (frame.height - 2)
    if dtype == pl.String:
        values = [str(value) for value in values]
    frame.with_columns(pl.Series('QMIGRAT1', values, dtype=dtype)).write_parquet(file)
    rules = read_rules(replace(source, parquet=file))
    assert rules.domains['QMIGRAT1']['dtype'] == str(dtype)
    assert classify_flag('0', 'QMIGRAT1', True, rules) == 'nonallocation'
    assert classify_flag('4', 'QMIGRAT1', True, rules) == 'allocated'
    assert pl.read_parquet_schema(file)['QMIGRAT1'] == dtype


def test_rules_preserve_metadata_and_original_source_schema(selected):
    source = selected.upstream.sources['acs/core']
    before = deepcopy(source.ddi)
    schema = pl.read_parquet_schema(source.parquet)
    rules = read_rules(source)
    assert source.ddi == before
    assert pl.read_parquet_schema(source.parquet) == schema
    for variable in before['variables']:
        if variable['name'] in rules.domains:
            assert rules.domains[variable['name']]['metadata'] == variable


def test_unsupported_original_dtype_fails(selected, tmp_path):
    source = selected.upstream.sources['acs/core']
    file = tmp_path / 'unsupported.parquet'
    pl.read_parquet(source.parquet).with_columns(pl.col('QIND').cast(pl.Float64)).write_parquet(
        file
    )
    with pytest.raises(ValueError, match='dtype'):
        read_rules(replace(source, parquet=file))
