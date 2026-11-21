'''Raw subawards and a raw extract to two verified, replay-equal Stage 14 bundles, offline.

The chain runs on the committed production registries with synthetic raw files, a real Stage 4
codes bundle and external access blocked. The firms, the reports and every count below are the
fixture's own, worked out from its design. No name or address value is in any file but
`DNB_SENTINEL`, which stands in for D&B Open Data. Fixture results show software readiness,
never benchmarks.
'''

import json
import socket
import zipfile
from types import SimpleNamespace

import httpx
import polars as pl
import pytest
from vendor_link_fixtures import (  # noqa: F401
    DNB_SENTINEL,
    V12_BAD_CODE,
    V12_CONFLICT,
    V12_MEMBER,
    V12_MONTH,
    V12_NO_CODE,
    V12_NOT_2022,
    V12_NOT_IN_SAM,
    V12_PRIME_A,
    V12_PRIME_B,
    V12_PRIME_C,
    V12_PRIME_D,
    V12_PRIME_OLD,
    V12_RUNS,
    V12_SELF,
    V12_SNAPSHOT,
    V12_SUB_A,
    V12_SUB_B,
    V12_SUB_C,
    V12_SUB_EDGE,
    no_live_sam,
    run_vendor_link_v12,
    v12_inputs,
)

from embedding_data import sam_raw, usaspending_raw, vendor_link_layouts
from embedding_data.vendor_link_bundle import FILES, TABLES, run_directory
from embedding_data.vendor_link_pairs import FIRM_STATUSES, PAIR_STATUSES, REPORT_STATUSES

NODE = 'naics:2022:national_industry:'
SENTINEL_PART = 'SENTINEL'
# The pair of each intra-group condition: the subcontractor's parent is the prime, the prime's
# parent is the subcontractor, and both parents are one other UEI.
GROUP_PAIRS = {
    'sub_parent_is_prime': (V12_PRIME_B, V12_SUB_A),
    'prime_parent_is_sub': (V12_PRIME_C, V12_SUB_B),
    'parents_equal': (V12_PRIME_D, V12_SUB_EDGE),
}
# Two firms with different valid parents: not a corporate group.
DIFFERENT_PARENTS = (V12_PRIME_C, V12_SUB_C)


class Pairs(dict):
    '''Pair rows by `(prime_uei, sub_uei)`. A pair that is not there fails as an assertion.'''

    def __missing__(self, key):
        raise AssertionError(f'the fixture has no pair {key}')


def node(code):
    return NODE + code


def load(directory):
    '''The report and the four tables of a published bundle, with the pairs keyed by
    `(prime_uei, sub_uei)`.'''
    frames = {name: pl.read_parquet(directory / f'{name}.parquet') for name in TABLES}
    return SimpleNamespace(
        report=json.loads((directory / 'report.json').read_text()),
        pair_table=frames['vendor_link_pairs'],
        pairs=Pairs(((row['prime_uei'], row['sub_uei']), row)
                    for row in frames['vendor_link_pairs'].iter_rows(named=True)),
        support=frames['vendor_link_support'], marginals=frames['vendor_link_marginals'],
        targets=frames['vendor_links'])


def cell(bundle, supplier_code, buyer_code):
    '''The one support row of the cell (supplier industry, buyer industry).'''
    rows = bundle.support.filter(pl.col('unit_a') == node(supplier_code),
                                 pl.col('unit_b') == node(buyer_code)).to_dicts()
    assert len(rows) == 1
    return rows[0]


def target(bundle, measure, supplier_code, buyer_code):
    rows = bundle.targets.filter(pl.col('measure') == measure,
                                 pl.col('unit_a') == node(supplier_code),
                                 pl.col('unit_b') == node(buyer_code)).to_dicts()
    assert len(rows) == 1
    return rows[0]


# ---- one check for each required case

def check_report_statuses(bundle):
    total = bundle.report['reports']['total']
    assert total['rows'] == 24
    assert total['by_status'] == {'uei_unusable': 2, 'action_date_invalid': 1,
                                  'outside_window': 2, 'usable': 19}
    assert set(total['by_status']) == set(REPORT_STATUSES)
    assert {year: section['rows']
            for year, section in bundle.report['reports']['by_file_year'].items()} == {
                '2024': 8, '2025': 9, '2026': 7}


def check_self_link(bundle):
    row = bundle.pairs[(V12_SELF, V12_SELF)]
    assert row['pair_status'] == 'self_link'
    # Both firms are eligible, so the self-link rule alone excludes the pair.
    assert row['prime_status'] == row['sub_status'] == 'eligible'


def check_intra_group_by_each_condition(bundle):
    for name, key in GROUP_PAIRS.items():
        row = bundle.pairs[key]
        assert row['pair_status'] == 'intra_group', name
        assert row['flag_intra_group'] is True, name
        assert row['prime_status'] == row['sub_status'] == 'eligible', name
    assert {key for key, row in bundle.pairs.items() if row['flag_intra_group']} == set(
        GROUP_PAIRS.values())
    # Different valid parents show no group.
    control = bundle.pairs[DIFFERENT_PARENTS]
    assert control['pair_status'] == 'eligible'
    assert control['flag_intra_group'] is False


def check_subcontractor_not_in_sam(bundle):
    row = bundle.pairs[(V12_PRIME_A, V12_NOT_IN_SAM)]
    assert row['sub_status'] == 'not_in_sam'
    assert row['sub_node_id'] is None
    assert row['prime_status'] == 'eligible'
    assert row['pair_status'] == 'sub_ineligible'


def check_record_last_updated_before_the_cutoff_on_a_prime(bundle):
    row = bundle.pairs[(V12_PRIME_OLD, V12_SUB_A)]
    assert row['prime_status'] == 'dnb_era_record'
    assert row['prime_node_id'] is None
    assert row['sub_status'] == 'eligible'
    assert row['pair_status'] == 'prime_ineligible'
    # A record last updated on 2022-04-04 is not a D&B-era record.
    assert bundle.pairs[(V12_PRIME_B, V12_SUB_EDGE)]['sub_status'] == 'eligible'
    assert bundle.report['extract']['last_update_by_year'] == {'2022': 2, '2025': 13,
                                                               'invalid': 0}


def check_missing_code(bundle):
    row = bundle.pairs[(V12_PRIME_A, V12_NO_CODE)]
    assert row['sub_status'] == 'naics_missing'
    assert row['pair_status'] == 'sub_ineligible'
    assert bundle.report['extract']['primary_codes']['blank'] == 1


def check_code_conflict(bundle):
    row = bundle.pairs[(V12_PRIME_C, V12_CONFLICT)]
    assert row['sub_status'] == 'naics_conflict'
    assert row['sub_node_id'] is None
    assert row['pair_status'] == 'sub_ineligible'
    assert bundle.report['extract']['rows_per_uei'] == {'1': 13, '2': 1, '3+': 0}


def check_well_formed_code_outside_naics_2022(bundle):
    row = bundle.pairs[(V12_PRIME_B, V12_NOT_2022)]
    assert row['sub_status'] == 'naics_not_2022'
    assert row['sub_node_id'] is None
    assert row['pair_status'] == 'sub_ineligible'
    codes = bundle.report['extract']['primary_codes']
    assert codes['well_formed'] - codes['in_2022'] == 1
    trigger = bundle.report['trigger']
    assert (trigger['naics_not_2022'], trigger['with_code']) == (1, 11)


def check_malformed_code_on_a_row_no_usable_report_reaches(bundle):
    extract = bundle.report['extract']
    assert extract['primary_codes']['malformed'] == 1
    assert extract['malformed_unread_rows'] == 1
    # The firm's only report is outside the window, so the firm has no pair.
    assert all(V12_BAD_CODE not in key for key in bundle.pairs)


def check_blank_uei(bundle):
    total = bundle.report['reports']['total']
    assert total['blank_uei'] == {'prime': 1, 'sub': 0}
    assert total['malformed_uei']['prime'] == 0


def check_malformed_uei(bundle):
    total = bundle.report['reports']['total']
    assert total['malformed_uei'] == {'prime': 0, 'sub': 1}
    assert total['blank_uei']['sub'] == 0


def check_report_outside_the_window(bundle):
    # 2023-09-30 is in fiscal year 2023 and 2026-10-01 in fiscal year 2027.
    assert bundle.report['reports']['total']['by_status']['outside_window'] == 2
    assert bundle.report['reports']['total']['outside_file_year'] == 2
    # 2023-10-01 and 2026-09-30 are the window's first and last days.
    assert bundle.pairs[(V12_PRIME_A, V12_SUB_A)]['n_fy2024'] == 1
    assert bundle.pairs[(V12_PRIME_A, V12_SUB_C)]['n_fy2026'] == 1


def check_duplicate_row(bundle):
    reports = bundle.report['reports']
    assert reports['total']['duplicate_rows'] == 1
    assert {year: section['duplicate_rows']
            for year, section in reports['by_file_year'].items()} == {
                '2024': 0, '2025': 1, '2026': 0}
    # Both copies are reports of their pair: one in 2024 and two in 2025.
    row = bundle.pairs[(V12_PRIME_B, V12_SUB_EDGE)]
    assert (row['n_reports'], row['n_fy2024'], row['n_fy2025']) == (3, 1, 2)


def check_diagonal_cell(bundle):
    assert bundle.report['diagonal'] == {'cells': 1, 'pairs': 1, 'share_of_pairs': 1 / 7}
    row = cell(bundle, '541511', '541511')
    assert (row['s_suppliers'], row['b_buyers'], row['l_pairs']) == (1, 1, 1)
    diagonal = bundle.targets.filter(pl.col('unit_a') == pl.col('unit_b'))
    assert sorted(diagonal['measure']) == ['buyer_share', 'supplier_share']
    assert set(diagonal['unit_a']) == {node('541511')}


def check_firm_in_both_roles(bundle):
    # The self-link firm does not count: it is one firm with one report.
    both = {prime for prime, _ in bundle.pairs} & {sub for _, sub in bundle.pairs}
    assert both - {V12_SELF} == {V12_PRIME_B}
    assert bundle.pairs[(V12_PRIME_A, V12_PRIME_B)]['pair_status'] == 'eligible'
    # It counts once as a supplier and once as a buyer in its industry.
    (row,) = bundle.marginals.filter(pl.col('node_id') == node('236220')).to_dicts()
    assert (row['n_suppliers'], row['n_buyers']) == (1, 1)
    firms = bundle.report['firms']
    assert firms['prime']['eligible'] + firms['subcontractor']['eligible'] == (
        firms['all']['eligible'] + 2)


def check_prime_with_several_subcontractors_in_one_industry(bundle):
    row = cell(bundle, '541512', '541511')
    assert (row['s_suppliers'], row['b_buyers'], row['l_pairs']) == (2, 1, 2)
    assert target(bundle, 'supplier_share', '541512', '541511')['value'] == 1.0
    assert bundle.report['subcontractors_per_prime']['max'] == 4


def check_report_in_each_fiscal_year(bundle):
    assert bundle.report['usable_by_fiscal_year'] == {'2024': 4, '2025': 9, '2026': 6}
    assert [bundle.pair_table[f'n_fy{year}'].sum() for year in (2024, 2025, 2026)] == [4, 9, 6]
    assert bundle.pair_table['n_reports'].sum() == 19


def check_every_status_and_the_headline_counts(bundle):
    report = bundle.report
    assert report['firms']['all'] == {'not_in_sam': 1, 'dnb_era_record': 1, 'naics_missing': 1,
                                      'naics_conflict': 1, 'naics_not_2022': 1, 'eligible': 9}
    assert set(report['firms']['all']) == set(FIRM_STATUSES)
    assert report['firms']['prime'] == {'not_in_sam': 0, 'dnb_era_record': 1, 'naics_missing': 0,
                                        'naics_conflict': 0, 'naics_not_2022': 0, 'eligible': 5}
    assert report['firms']['subcontractor'] == {
        'not_in_sam': 1, 'dnb_era_record': 0, 'naics_missing': 1, 'naics_conflict': 1,
        'naics_not_2022': 1, 'eligible': 6}
    assert report['pairs'] == {'self_link': 1, 'intra_group': 3, 'prime_ineligible': 1,
                               'sub_ineligible': 4, 'eligible': 7, 'total': 16}
    assert set(report['pairs']) == {*PAIR_STATUSES, 'total'}
    assert report['join_coverage']['prime'] == {'eligible': 5, 'total': 6, 'share': 5 / 6}
    assert report['join_coverage']['subcontractor'] == {'eligible': 6, 'total': 10,
                                                        'share': 0.6}


def check_intra_group_sensitivity(bundle):
    report = bundle.report
    assert report['n_pairs'] == {'eligible': 7, 'including_intra_group': 10}
    assert report['n_buyers'] == {'eligible': 3, 'including_intra_group': 4}
    assert report['n_suppliers'] == {'eligible': 5, 'including_intra_group': 5}
    # Two cells hold intra-group pairs only. The third group pair widens a cell of P.
    assert report['cells_only_intra_group'] == 2
    assert len(bundle.support) == 6
    assert len(bundle.targets) == 12
    widened = cell(bundle, '541512', '236220')
    assert (widened['s_suppliers'], widened['s_including_intra_group']) == (1, 2)
    assert (widened['b_buyers'], widened['b_including_intra_group']) == (1, 1)
    supplier = target(bundle, 'supplier_share', '541512', '236220')
    assert supplier['value'] == 0.5
    assert supplier['flags'] == ['numerator:intra_group_sensitivity:true', 'size_gate_pending']
    assert target(bundle, 'buyer_share', '541512', '236220')['flags'] == ['size_gate_pending']


def check_production_registries_map_both_parent_fields(bundle):
    # Neither parent field is missing, so all three group conditions can occur.
    assert bundle.report['missing_fields'] == {
        'subawards': {str(year): ['subaward_naics'] for year in (2024, 2025, 2026)},
        'extract': []}


REQUIRED_CASES = (
    check_report_statuses,
    check_self_link,
    check_intra_group_by_each_condition,
    check_subcontractor_not_in_sam,
    check_record_last_updated_before_the_cutoff_on_a_prime,
    check_missing_code,
    check_code_conflict,
    check_well_formed_code_outside_naics_2022,
    check_malformed_code_on_a_row_no_usable_report_reaches,
    check_blank_uei,
    check_malformed_uei,
    check_report_outside_the_window,
    check_duplicate_row,
    check_diagonal_cell,
    check_firm_in_both_roles,
    check_prime_with_several_subcontractors_in_one_industry,
    check_report_in_each_fiscal_year,
    check_every_status_and_the_headline_counts,
    check_intra_group_sensitivity,
    check_production_registries_map_both_parent_fields,
)


def leaked_values(directory, part):
    '''The tables' cells and the JSON files that hold `part`, as text.

    A Parquet column is compressed, so its raw bytes can hide a value. Each table is read and
    written back as JSON text, which holds every string and list cell.
    '''
    found = []
    for file in sorted(directory.iterdir()):
        if file.suffix == '.parquet':
            text = pl.read_parquet(file).write_json()
        else:
            text = file.read_text(encoding='utf-8')
        if part in text.upper():
            found.append(file.name)
    return found


# ---- plan tests

def test_v12_chain_is_offline_verified_and_replay_equal(tmp_path, monkeypatch):
    result = run_vendor_link_v12(tmp_path, monkeypatch)
    assert result['comparison']['equal'] is True
    assert result['first_verification']['outputs_sha256'] == result['first_pin']


def test_v12_fixture_holds_every_required_case(tmp_path, monkeypatch):
    result = run_vendor_link_v12(tmp_path, monkeypatch)
    pairs = pl.read_parquet(result['first'] / 'vendor_link_pairs.parquet')
    report = json.loads((result['first'] / 'report.json').read_text())
    assert set(pairs['pair_status']) == set(PAIR_STATUSES)
    assert report['reports']['total']['duplicate_rows'] == 1
    assert report['extract']['malformed_unread_rows'] == 1
    assert {'not_in_sam', 'dnb_era_record', 'naics_missing', 'naics_conflict',
            'naics_not_2022', 'eligible'} <= set(report['firms']['all'])
    # plus: every report status, a diagonal cell, a usable report in each fiscal year, and one
    # check for each other required case.
    bundle = load(result['first'])
    for check in REQUIRED_CASES:
        check(bundle)


def test_no_name_or_address_value_in_any_bundle_byte(tmp_path, monkeypatch):
    result = run_vendor_link_v12(tmp_path, monkeypatch)
    for file in result['first'].iterdir():
        assert DNB_SENTINEL.encode() not in file.read_bytes()


# ---- strengthening tests: each runs its own chain

def test_v12_replay_registries_and_guards(tmp_path, monkeypatch):
    result = run_vendor_link_v12(tmp_path, monkeypatch)
    assert result['second_verification']['outputs_sha256'] == result['second_pin']
    assert result['comparison']['trust_established'] is False
    assert result['comparison']['report_equal'] is True
    assert {name: (table['schema_equal'], table['values_equal'])
            for name, table in result['comparison']['tables'].items()} == {
                name: (True, True) for name in TABLES}
    # The replay holds the same cases.
    assert load(result['second']).report == load(result['first']).report
    assert [result['first'].name, result['second'].name] == list(V12_RUNS)
    assert result['data_dir'] == tmp_path / 'data'
    for name in ('first', 'second'):
        directory = result[name]
        assert directory == run_directory(result['data_dir'], directory.name)
        assert sorted(path.name for path in directory.iterdir()) == sorted(
            [*FILES, 'outputs.json'])
        assert result[name + '_verification']['rows'] == {
            table: len(pl.read_parquet(directory / f'{table}.parquet')) for table in TABLES}
    # The guards are still in force.
    with pytest.raises(AssertionError):
        socket.create_connection(('127.0.0.1', 9))
    with pytest.raises(AssertionError):
        httpx.Client()
    # The chain ran on the committed production registries.
    inputs = json.loads((result['first'] / 'inputs.json').read_text())
    assert inputs['registries'] == {
        'subaward_headers': vendor_link_layouts.subaward_layouts_json(
            vendor_link_layouts.load_subaward_layouts()),
        'extract_layout': vendor_link_layouts.extract_layout_json(
            vendor_link_layouts.load_extract_layout())}
    assert (inputs['snapshot'], inputs['sam_month']) == (V12_SNAPSHOT.isoformat(), V12_MONTH)


def test_v12_sentinel_is_in_the_raw_files_and_in_no_decoded_cell(tmp_path, monkeypatch):
    result = run_vendor_link_v12(tmp_path, monkeypatch)
    data_dir = result['data_dir']
    layout = vendor_link_layouts.load_extract_layout()
    extract_file = sam_raw.select_extract(data_dir, V12_MONTH)
    assert extract_file.name == 'SAM_PUBLIC_UTF-8_MONTHLY_V2_20261102.ZIP'
    # The raw files are deflated, so the sentinel is read from the decoded members.
    with zipfile.ZipFile(extract_file) as archive:
        (member,) = archive.namelist()
        lines = archive.read(member).decode(layout.encoding).split('\r\n')[1:-1]
    assert len(lines) == 15
    for line in lines:
        fields = line.split(layout.delimiter)
        assert len(fields) == layout.field_count
        for position in layout.restricted_positions:
            assert fields[position - 1] == DNB_SENTINEL
    for year, file in usaspending_raw.select_files(data_dir, V12_SNAPSHOT).items():
        with zipfile.ZipFile(file) as archive:
            assert archive.namelist() == [V12_MEMBER]
            assert DNB_SENTINEL.encode() in archive.read(V12_MEMBER), year
    for name in ('first', 'second'):
        for file in result[name].iterdir():
            assert DNB_SENTINEL.encode() not in file.read_bytes(), (name, file.name)
        assert leaked_values(result[name], SENTINEL_PART) == [], name


def test_v12_inputs_are_deterministic():
    first, second = v12_inputs(), v12_inputs()
    assert first == second
