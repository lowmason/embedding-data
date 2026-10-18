'''Public reader/grammar fixtures; not selector-accepted mapping bundles.'''

import json
from dataclasses import replace
from itertools import count
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import polars as pl
import pytest
from acs_mapping_fixtures import seed_mapping_references, write_public_layout
from target_fixtures import forbid_external_access

from embedding_data import manifest, target_io
from embedding_data.acs_code_references import (
    CodeEvidence,
    parse_membership_expression,
    read_code_evidence,
    validate_paired_keys,
)
from embedding_data.acs_mapping_contract import SelectionRequest
from embedding_data.acs_mapping_inputs import SelectedInputs
from embedding_data.acs_mapping_references import check_cached_snapshot

PUBLIC = Path(__file__).parent / 'fixtures/acs_mapping/classification'


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    forbid_external_access(monkeypatch)
    import httpx

    from embedding_data import ipums_census_access

    def forbidden(*args, **kwargs):
        raise AssertionError('offline classification attempted external access')

    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, 'handle_async_request', forbidden)
    monkeypatch.setattr(ipums_census_access, 'read_credential', forbidden)


@pytest.fixture(scope='module')
def graphs():
    return {
        name: pl.read_parquet(PUBLIC / (name + '.parquet'))
        for name in ('naics_native_nodes', 'soc_nodes', 'code_paths')
    }


@pytest.fixture(scope='module')
def selected(tmp_path_factory, graphs):
    tmp_path = tmp_path_factory.mktemp('classification-graphs')
    codes = {}
    for name, frame in graphs.items():
        codes[name] = tmp_path / (name + '.parquet')
        frame.write_parquet(codes[name])
    provenance = json.loads((PUBLIC / 'provenance.json').read_text())
    originals = provenance['stage7_industry_originals']
    for name, record in originals.items():
        file = tmp_path / 'raw' / record['citation']['path']
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes((PUBLIC / (name + '.xlsx')).read_bytes())
    return SelectedInputs(
        tmp_path,
        SelectionRequest(*(['fixture'] * 7)),
        {},
        codes,
        {},
        {
            'fixture': provenance,
            'codes': {
                'tables': {name: target_io.file_record(file) for name, file in codes.items()}
            },
            'ipums': {'inputs': {'references': {'receipt': {'originals': originals}}}},
        },
        {},
    )


@pytest.fixture(scope='module')
def public_monkeypatch():
    with pytest.MonkeyPatch.context() as patch:
        yield patch


@pytest.fixture(scope='module')
def code_originals(tmp_path_factory, public_monkeypatch):
    tmp_path = tmp_path_factory.mktemp('classification-originals')
    monkeypatch = public_monkeypatch
    overrides = {
        f.stem: f for f in PUBLIC.glob('*.xlsx') if not f.stem.startswith('census_industry_')
    }
    excerpt_dir = tmp_path / 'release-excerpts'
    excerpt_dir.mkdir()
    for kind, record in json.loads((PUBLIC / 'release-layouts.json').read_text()).items():
        file = excerpt_dir / (kind + '.xlsx')
        write_public_layout(file, record)
        overrides[kind] = file
    sequence = count()

    def make(directory, changes=None, part_change=None):
        directory.mkdir()
        values = dict(overrides)
        if changes:
            kind, sheet, address, value = changes
            altered = directory / 'synthetic-conflict.xlsx'
            if kind in overrides:
                row, col = address
                address_text = chr(65 + col) + str(row)
                namespace = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                with ZipFile(overrides[kind]) as original, ZipFile(altered, 'w') as output:
                    workbook = ET.fromstring(original.read('xl/workbook.xml'))
                    names = [node.attrib['name'] for node in workbook.find('m:sheets', namespace)]
                    target = f'xl/worksheets/sheet{names.index(sheet) + 1}.xml'
                    for part in original.namelist():
                        body = original.read(part)
                        if part == target:
                            document = ET.fromstring(body)
                            cell = document.find(f'.//m:c[@r="{address_text}"]', namespace)
                            assert cell is not None
                            for child in list(cell):
                                cell.remove(child)
                            cell.set('t', 'inlineStr')
                            text = ET.SubElement(
                                ET.SubElement(cell, '{' + namespace['m'] + '}is'),
                                '{' + namespace['m'] + '}t',
                            )
                            text.text = value
                            body = ET.tostring(document)
                        output.writestr(part, body)
            else:
                record = json.loads(
                    (
                        Path(__file__).parent / 'fixtures/acs_mapping/reference-layouts.json'
                    ).read_text()
                )['originals'][kind]
                row, col = address
                record['sheets'][sheet]['rows'][str(row)][col] = value
                write_public_layout(altered, record)
            values[kind] = altered
        if part_change:
            kind, part, replacement = part_change
            altered = directory / 'synthetic-style-change.xlsx'
            with ZipFile(overrides[kind]) as original, ZipFile(altered, 'w') as output:
                for name in original.namelist():
                    if name != part:
                        output.writestr(name, original.read(name))
                    elif replacement is not None:
                        output.writestr(name, replacement)
            values[kind] = altered
        seeded = seed_mapping_references(directory, monkeypatch, original_overrides=values)
        return check_cached_snapshot(seeded.data_dir, seeded.reference_id)

    snapshot = make(tmp_path / 'original')
    return SimpleNamespace(
        snapshot=snapshot,
        changed=lambda *change: make(tmp_path / f'mutation-{next(sequence)}', change),
        changed_part=lambda *change: make(
            tmp_path / f'mutation-{next(sequence)}', part_change=change
        ),
        with_conflicting_authority=lambda: make(
            tmp_path / 'conflict', ('pums_annual_2024', 'Industry', (27, 4), '1133')
        ),
    )


@pytest.fixture(scope='module')
def evidence(code_originals, selected):
    return read_code_evidence(code_originals.snapshot, selected)


def members(evidence, token, scheme='naics2022'):
    return evidence.membership.filter(
        pl.col('source_scheme').eq(scheme).and_(pl.col('source_token').eq(token))
    )['native_finest_code'].to_list()


@pytest.mark.parametrize(
    'token,expected',
    [
        ('113M', ['113110', '113210']),
        (
            '311M1',
            [
                '311111',
                '311119',
                '311211',
                '311212',
                '311213',
                '311221',
                '311224',
                '311225',
                '311230',
            ],
        ),
        (
            '311M2',
            [
                '311710',
                '311911',
                '311919',
                '311920',
                '311930',
                '311941',
                '311942',
                '311991',
                '311999',
            ],
        ),
        (
            '332MZ',
            [
                '332510',
                '332613',
                '332618',
                '332911',
                '332912',
                '332913',
                '332919',
                '332991',
                '332996',
                '332999',
            ],
        ),
        (
            '221MP',
            [
                '221111',
                '221112',
                '221113',
                '221114',
                '221115',
                '221116',
                '221117',
                '221118',
                '221121',
                '221122',
                '221210',
            ],
        ),
        ('22132', ['221320']),
        ('2212P', ['221210']),
        ('3118Z', ['311812', '311813', '311821', '311824', '311830']),
        ('3219ZM', ['321911', '321912', '321918', '321920', '321999']),
        ('92811P1', ['928110']),
    ],
)
def test_literal_industry_membership(evidence, token, expected):
    assert members(evidence, token) == expected


@pytest.mark.parametrize(
    'token,expected',
    [
        ('1110XX', ['11-1011', '11-1031']),
        ('15124X', ['15-1242', '15-1243']),
        ('1721XX', ['17-2151', '17-2171']),
        ('1721YY', ['17-2161', '17-2199']),
        ('1940YY', ['19-4061', '19-4071', '19-4092', '19-4099']),
        (
            '291210',
            [
                '29-1211',
                '29-1212',
                '29-1213',
                '29-1214',
                '29-1215',
                '29-1216',
                '29-1217',
                '29-1218',
                '29-1221',
                '29-1222',
                '29-1223',
                '29-1224',
                '29-1229',
            ],
        ),
    ],
)
def test_literal_occupation_membership(evidence, token, expected):
    assert members(evidence, token, 'soc2018') == expected


def test_official_paths_determine_overflow_and_combined_sector(graphs):
    nodes, paths = graphs['soc_nodes'], graphs['code_paths']
    assert '29-1221' in parse_membership_expression('29-1210', nodes, paths)
    nodes = graphs['naics_native_nodes'].filter(pl.col('vintage').eq(2022))
    assert parse_membership_expression('31,32,33', nodes, paths) == parse_membership_expression(
        '31-33', nodes, paths
    )
    metal = parse_membership_expression('Part of 331 and 332', nodes, paths)
    assert '331110' in metal and '333111' not in metal


@pytest.mark.parametrize(
    'expression',
    [
        '321 9',
        'Part of3219',
        '3219 bananas',
        '3219XX',
        '3219 + 3211',
        '3219 exc. 311811',
        '3219 exc. 3219',
        '000000',
        '321911-999999',
        '',
        '3219,',
    ],
)
def test_unsupported_grammar_fails(graphs, expression):
    with pytest.raises(ValueError):
        parse_membership_expression(
            expression,
            graphs['naics_native_nodes'].filter(pl.col('vintage').eq(2022)),
            graphs['code_paths'],
        )


def test_bounded_range_and_explicit_exclusion(graphs):
    nodes = graphs['naics_native_nodes'].filter(pl.col('vintage').eq(2022))
    assert parse_membership_expression('321911-321918', nodes, graphs['code_paths']) == [
        '321911',
        '321912',
        '321918',
    ]


def test_paired_industry_disagreement_is_not_merged(code_originals, selected):
    with pytest.raises(ValueError, match='contradictory paired'):
        read_code_evidence(code_originals.with_conflicting_authority(), selected)


def test_metadata_reasons_special_and_typed_sets(evidence):
    assert isinstance(evidence, CodeEvidence)
    metadata = evidence.metadata
    x = metadata.filter(pl.col('source_token').eq('1110XX')).row(0, named=True)
    assert x['aggregation_reason_status'] == 'documented'
    assert x['aggregation_reasons'] == ['disclosure']
    design = metadata.filter(pl.col('source_token').eq('15124X')).row(0, named=True)
    assert design['aggregation_reasons'] == ['category_design']
    special = metadata.filter(pl.col('source_token').eq('559830')).row(0, named=True)
    assert special['mapping_status'] == 'documented_special'
    assert special['native_finest_candidates'] == []
    assert special['native_node_id'] is None
    assert not members(evidence, '559830', 'soc2018')
    assert metadata.filter(pl.col('source_token').eq('999920')).is_empty()
    assert evidence.diagnostics['excluded_nonworking']
    for frame in [metadata, evidence.membership]:
        for name, dtype in frame.schema.items():
            if isinstance(dtype, pl.List):
                assert frame[name].null_count() == 0
                assert all(None not in values for values in frame[name])


def test_partial_and_suffix_provenance_survives_singleton(evidence):
    metadata = evidence.metadata
    for token in ('2212P', '92811P1', '928110P7'):
        row = metadata.filter(pl.col('source_token').eq(token)).row(0, named=True)
        assert row['flag_partial'] and row['flag_aggregate']
        assert row['aggregation_reason_status'] == 'unknown'
        assert row['aggregation_reasons'] == []
    assert members(evidence, '928110P7', 'naics2017') == ['928110']


def test_observed_pair_is_exact_and_preserves_source_padding(evidence):
    good = pl.DataFrame(
        {
            'system': ['naics'],
            'source_scheme': ['naics2022'],
            'paired_census_code': ['0190'],
            'source_token': ['113M'],
        }
    )
    validate_paired_keys(good, evidence)
    for name, value in [
        ('paired_census_code', '0270'),
        ('paired_census_code', '190'),
        ('source_token', ' 113M'),
        ('source_token', '999920'),
    ]:
        with pytest.raises(ValueError, match='paired'):
            validate_paired_keys(good.with_columns(pl.lit(value).alias(name)), evidence)


def test_fixture_public_pins():
    for filename, pin in json.loads((PUBLIC / 'provenance.json').read_text())['files'].items():
        assert manifest.sha256_file(PUBLIC / filename) == pin


@pytest.mark.parametrize(
    'change',
    [
        ('pums_occupation_2018', 'ACS', (707, 1), '40-9094'),
        (
            'pums_occupation_2018',
            'ACS',
            (707, 2),
            '7551 - Manufactured building and mobile home installers',
        ),
        ('census_occupation_2018', '2018 Census Occ Code List', (547, 3), '49-9094'),
    ],
)
def test_d4_is_bounded_to_exact_constituent_and_assertion(code_originals, selected, change):
    with pytest.raises(ValueError, match='constituent|contradictory'):
        read_code_evidence(code_originals.changed(*change), selected)


def test_approved_d4_retains_rejected_assertion(evidence):
    assert '49-9095' in members(evidence, '4990XX', 'soc2018')
    assertions = evidence.diagnostics['rejected_occupation_assertions']
    assert assertions
    assert all(
        row['asserted_soc'] == '40-9095'
        and row['full_census_code'] == '7550'
        and row['supported_soc'] == '49-9095'
        for row in assertions
    )
    assert any('row=707' in locator for row in assertions for locator in row['reference_locators'])


@pytest.mark.parametrize(
    'change',
    [
        ('ipums_ind_pairs', 'Sheet1', (4, 14), '112'),
        ('ipums_occ_pairs', 'Codes without Descriptions', (6, 14), '111011'),
        (
            'pums_occupation_2018',
            'ACS',
            (884, 0),
            'Highlighting never determines confidentiality.',
        ),
    ],
)
def test_new_source_disagreement_or_legend_fails(code_originals, selected, change):
    with pytest.raises(ValueError):
        read_code_evidence(code_originals.changed(*change), selected)


@pytest.mark.parametrize(
    'change',
    [
        ('pums_industry_2022', 'ACS', (25, 2), '01A0'),
        ('pums_occupation_2018', 'ACS', (17, 0), '00A0'),
    ],
)
def test_malformed_reference_keys_fail_before_observed_filter(code_originals, selected, change):
    with pytest.raises(ValueError, match='malformed.*key'):
        read_code_evidence(code_originals.changed(*change), selected)


def test_unknown_reason_does_not_borrow_another_codes_reason(evidence):
    row = evidence.metadata.filter(pl.col('source_token').eq('112030')).row(0, named=True)
    assert row['flag_aggregate']
    assert row['aggregation_reason_status'] == 'unknown'
    assert row['aggregation_reasons'] == []
    assert any('census_occupation_2018' in locator for locator in row['reference_locators'])


def test_d3_extra_has_published_legacy_evidence_and_is_never_admitted(evidence):
    extras = [
        r
        for r in evidence.diagnostics['rejected_industry_assertions']
        if r['status'] == 'not_in_pums_list'
    ]
    assert {(r['vintage'], r['paired_census_code'], r['source_token']) for r in extras} == {
        (2017, '8880', '8114'),
        (2022, '8880', '8114'),
    }
    for row in extras:
        assert row['historical_evidence']['current_census_code'] == '8891'
        assert 'row=313' in row['historical_evidence']['reference_locators'][0]
    assert evidence.metadata.filter(pl.col('paired_census_code').eq('8880')).is_empty()
    bad = pl.DataFrame(
        {
            'system': ['naics'],
            'source_scheme': ['naics2022'],
            'paired_census_code': ['8880'],
            'source_token': ['8114'],
        }
    )
    with pytest.raises(ValueError, match='paired'):
        validate_paired_keys(bad, evidence)


def test_membership_contract_and_only_approved_empty_special(evidence):
    assert evidence.membership.columns == [
        'system',
        'source_scheme',
        'paired_census_code',
        'source_token',
        'native_finest_code',
        'native_node_id',
        'aggregation_type',
        'aggregation_markers',
        'flag_partial',
        'flag_exception',
        'reference_ids',
        'reference_locators',
    ]
    assert (
        evidence.membership.select(
            'system', 'source_scheme', 'paired_census_code', 'source_token', 'native_finest_code'
        )
        .is_duplicated()
        .any()
        is False
    )
    empty = evidence.metadata.filter(pl.col('native_finest_candidates').list.len().eq(0))
    assert empty.select('paired_census_code', 'source_token').rows() == [('9830', '559830')]


def test_nonmissing_token_cannot_hide_a_missing_paired_key(evidence):
    incomplete = pl.DataFrame(
        {
            'system': ['naics'],
            'source_scheme': ['naics2022'],
            'paired_census_code': [None],
            'source_token': ['113M'],
        },
        schema={
            name: pl.String
            for name in ('system', 'source_scheme', 'paired_census_code', 'source_token')
        },
    )
    with pytest.raises(ValueError, match='paired'):
        validate_paired_keys(incomplete, evidence)


def test_changed_selected_graph_is_not_read_as_new_evidence(
    evidence, code_originals, selected, tmp_path
):
    file = tmp_path / 'changed-native.parquet'
    pl.read_parquet(selected.codes['naics_native_nodes']).with_columns(
        pl.lit('Changed public title').alias('title')
    ).write_parquet(file)
    altered = replace(selected, codes={**selected.codes, 'naics_native_nodes': file})
    with pytest.raises(ValueError, match='selected.*classification'):
        read_code_evidence(code_originals.snapshot, altered)


def test_changed_snapshot_pin_is_not_read(code_originals, selected):
    altered = replace(code_originals.snapshot, receipt_sha256='0' * 64)
    with pytest.raises(ValueError, match='receipt'):
        read_code_evidence(altered, selected)


def test_token_semantics_cites_inspected_documentation(evidence):
    industry = evidence.metadata.filter(
        pl.col('source_scheme').eq('naics2022').and_(pl.col('source_token').eq('113M'))
    ).row(0, named=True)
    assert {'industry_tokens_html', 'ipums_ind_tokens'}.issubset(industry['reference_ids'])
    occupation = evidence.metadata.filter(pl.col('source_token').eq('1110XX')).row(0, named=True)
    assert {'soc_tokens_html', 'usa_occsoc'}.issubset(occupation['reference_ids'])
    assert any('ipums_occ_pairs' in locator for locator in occupation['reference_locators'])


def test_missing_styles_fail_instead_of_clearing_a_reason(code_originals, selected):
    with pytest.raises(ValueError, match='styles|malformed'):
        read_code_evidence(
            code_originals.changed_part('pums_occupation_2018', 'xl/styles.xml', None), selected
        )


def test_unapproved_empty_military_code_fails(code_originals, selected):
    with pytest.raises(ValueError, match='unknown|contradictory'):
        read_code_evidence(
            code_originals.changed('pums_occupation_2018', 'ACS', (879, 1), '55-9831'), selected
        )


def test_nonworking_diagnostics_cover_full_census_originals(evidence):
    excluded = evidence.diagnostics['excluded_nonworking']
    assert {'census_industry_2017', 'census_industry_2022', 'census_occupation_2018'}.issubset(
        {row['kind'] for row in excluded}
    )


def test_original_expression_padding_remains_in_exact_locator(evidence):
    row = evidence.metadata.filter(pl.col('source_scheme').eq('naics2017')
        .and_(pl.col('source_token').eq('22S'))).row(0,named=True)
    assert any(locator.endswith('expression=Part of 22 ') for locator in row['reference_locators'])
