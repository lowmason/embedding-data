'''Strict public-source parsing and immutable offline snapshot contracts.'''

import importlib
import json
import shutil
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import httpx
import polars as pl
import pytest
from ipums_fixtures import (
    ACS_STATE_CODES,
    SAMPLE_CATALOG,
    acs_levels,
    bls_documents,
    bls_response,
    industry_workbook,
    reference_originals,
)

from embedding_data import manifest, manifest_audit, paths

def references():
    return importlib.import_module('embedding_data.ipums_references')


def write_text(directory, name, value):
    file = directory / name
    file.write_text(value)
    return file


def test_sample_catalog_has_exact_id_description_mapping(tmp_path):
    file = write_text(tmp_path, 'samples.html', SAMPLE_CATALOG)
    assert references().parse_sample_catalog(file) == {
        'us2023a': '2023 ACS', 'us2024c': '2020-2024, ACS 5-year'}


@pytest.mark.parametrize('mutation', [
    lambda t: t.replace('Sample ID</th>', 'Identifier</th>'),
    lambda t: t.replace('us2024c', 'us2023a'),
    lambda t: t.replace('us2024c', 'invalid'),
    lambda t: t.replace('2023 ACS', ''),
    lambda t: '<html><h1>Log in</h1></html>',
])
def test_sample_catalog_rejects_drift(tmp_path, mutation):
    with pytest.raises(ValueError):
        references().parse_sample_catalog(write_text(tmp_path, 'samples.html',
                                                    mutation(SAMPLE_CATALOG)))


@pytest.mark.parametrize('vintage', [2017, 2022])
def test_industry_uses_verified_sheet_headers_and_separates_special_codes(tmp_path, vintage):
    file = industry_workbook(tmp_path / 'industry.xlsx', vintage)
    frame = references().parse_industry_list(file, vintage)
    assert frame.schema == {'code': pl.String, 'title': pl.String}
    assert frame.rows() == [('0170', 'Crop production'),
                            ('0180', 'Animal production and aquaculture')]
    info = references().parse_industry_metadata(file, vintage)
    assert info['vintage'] == vintage
    assert info['special_codes'] == {
        '9920': 'Unemployed, last worked 5 years ago or earlier or never worked'}


@pytest.mark.parametrize('mutation', ['header', 'sheet', 'vintage', 'duplicate', 'code', 'title'])
def test_industry_rejects_drift(tmp_path, mutation):
    options = {}
    if mutation == 'header':
        options['header'] = 'ACS PUMS code'
    if mutation == 'sheet':
        options['sheet'] = 'PUMS list'
    if mutation in ('duplicate', 'code', 'title'):
        options['leaves'] = [[None, 'Crop', None, '0170', '111'],
                             [None, '' if mutation == 'title' else 'Conflicting', None,
                              '0170' if mutation == 'duplicate' else '170', '111']]
    file = industry_workbook(tmp_path / 'industry.xlsx', **options)
    with pytest.raises(ValueError):
        references().parse_industry_list(file, 2022 if mutation == 'vintage' else 2017)


def test_industry_rejects_html_masquerading_as_workbook(tmp_path):
    file = write_text(tmp_path, 'industry.xlsx', '<html>Access denied</html>')
    with pytest.raises(ValueError):
        references().parse_industry_list(file, 2017)


def test_bls_retains_unavailable_october_and_source_footnotes(tmp_path):
    bls_documents(tmp_path)
    file = write_text(tmp_path, 'cps_employment.json', json.dumps(bls_response()))
    frame = references().parse_bls_levels(file)
    assert frame.schema == {'year': pl.Int64, 'month': pl.Int64, 'published': pl.Float64,
                            'units': pl.String, 'footnotes': pl.String}
    assert frame.height == 21
    october = frame.filter((pl.col('year') == 2025) & (pl.col('month') == 10))
    assert october['published'].item() is None
    assert 'lapse in appropriations' in october['footnotes'].item()
    assert frame['units'].unique().to_list() == ['thousands of persons']
    assert 'Population control revision.' in frame['footnotes'][12]


@pytest.mark.parametrize('mutation', ['status', 'message', 'series', 'M13', 'year', 'missing',
                                      'duplicate', 'negative', 'nan', 'unexplained_missing'])
def test_bls_refuses_unusable_monthly_responses(tmp_path, mutation):
    bls_documents(tmp_path)
    body = bls_response()
    series = body['Results']['series'][0]
    data = series['data']
    if mutation == 'status':
        body['status'] = 'REQUEST_FAILED'
    elif mutation == 'message':
        body['message'] = ['No data returned']
    elif mutation == 'series':
        series['seriesID'] = 'LNS12000000'
    elif mutation == 'M13':
        data[0]['period'] = 'M13'
    elif mutation == 'year':
        data[0]['year'] = '2024'
    elif mutation == 'missing':
        data.pop(0)
    elif mutation == 'duplicate':
        data.append(data[0])
    elif mutation == 'negative':
        data[0]['value'] = '-1'
    elif mutation == 'nan':
        data[0]['value'] = 'NaN'
    elif mutation == 'unexplained_missing':
        data[0]['value'] = '-'
    with pytest.raises(ValueError):
        references().parse_bls_levels(write_text(tmp_path, 'levels.json', json.dumps(body)))


@pytest.mark.parametrize('mutation', ['missing_series', 'seasonal', 'units', 'universe'])
def test_bls_requires_frozen_series_and_units_evidence(tmp_path, mutation):
    bls_documents(tmp_path)
    if mutation == 'missing_series':
        (tmp_path / 'bls_series_metadata.txt').unlink()
    elif mutation == 'seasonal':
        file = tmp_path / 'bls_series_metadata.txt'
        file.write_text(file.read_text().replace('\tU\n', '\tS\n'))
    else:
        file = tmp_path / 'bls_a1_metadata.html'
        file.write_text(file.read_text().replace(
            'thousands' if mutation == 'units' else '16 years and over', 'unknown'))
    with pytest.raises(ValueError):
        references().parse_bls_levels(write_text(tmp_path, 'levels.json',
                                               json.dumps(bls_response())))


def test_acs_parser_rejects_missing_key_html(tmp_path):
    file = write_text(tmp_path, 'acs.json', '<html><h1>Missing Key</h1></html>')
    with pytest.raises(ValueError, match='ACS levels'):
        references().parse_acs_levels(file, 2023)


@pytest.fixture
def catalog_registry(monkeypatch):
    module = references()
    monkeypatch.setattr(module, 'REGISTRY', {'usa_samples': module.REGISTRY['usa_samples']})
    return module


def install_transport(monkeypatch, module, handler):
    monkeypatch.setattr(module, 'make_client',
                        lambda: httpx.Client(transport=httpx.MockTransport(handler)))


def no_client():
    raise AssertionError('offline replay contacted a service')


def test_acquire_receipt_cached_replay_and_manifest(tmp_path, monkeypatch, catalog_registry):
    module = catalog_registry
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, content=SAMPLE_CATALOG.encode())

    install_transport(monkeypatch, module, handler)
    directory = module.acquire(tmp_path, 'public1')
    assert directory == tmp_path / 'raw/references/ipums-verification/public1'
    receipt = module.check_references(tmp_path, 'public1')
    assert set(receipt['files']) == {'usa_samples.html'}
    assert receipt['parser_version'] == module.PARSER_VERSION
    assert receipt['originals']['usa_samples']['method'] == 'GET'
    assert receipt['originals']['usa_samples']['source_url'] == calls[0]
    entries = manifest.read_manifest(paths.manifest_path(tmp_path))
    assert len(entries) == 2
    assert entries[0].sha256 == manifest.sha256_file(directory / 'usa_samples.html')
    monkeypatch.setattr(module, 'make_client', no_client)
    assert module.acquire(tmp_path, 'public1') == directory
    assert module.check_references(tmp_path, 'public1') == receipt
    assert len(calls) == 1


@pytest.mark.parametrize('mutation', ['changed', 'missing', 'extra', 'symlink', 'receipt',
                                      'manifest', 'directory_symlink'])
def test_cached_snapshot_mutations_fail_offline(tmp_path, monkeypatch, catalog_registry, mutation):
    module = catalog_registry
    install_transport(monkeypatch, module, lambda _: httpx.Response(200, text=SAMPLE_CATALOG))
    directory = module.acquire(tmp_path, 'snapshot')
    file = directory / 'usa_samples.html'
    if mutation == 'changed':
        file.write_text('changed')
    elif mutation == 'missing':
        file.unlink()
    elif mutation == 'extra':
        (directory / 'extra').write_text('unmanifested')
    elif mutation == 'symlink':
        file.unlink()
        file.symlink_to(tmp_path / 'outside')
    elif mutation == 'receipt':
        (directory / 'receipt.json').unlink()
    elif mutation == 'manifest':
        paths.manifest_path(tmp_path).write_text('')
    elif mutation == 'directory_symlink':
        directory.rename(directory.with_name('other'))
        directory.symlink_to(directory.with_name('other'), target_is_directory=True)
    monkeypatch.setattr(module, 'make_client', no_client)
    with pytest.raises((ValueError, KeyError, FileNotFoundError)):
        module.acquire(tmp_path, 'snapshot')


@pytest.mark.parametrize('name', ['snapshot.part', 'snapshot'])
def test_acquire_refuses_occupied_incomplete_before_client(tmp_path, monkeypatch,
                                                         catalog_registry, name):
    module = catalog_registry
    root = tmp_path / 'raw/references/ipums-verification'
    (root / name).mkdir(parents=True)
    monkeypatch.setattr(module, 'make_client', no_client)
    with pytest.raises(ValueError, match='incomplete|occupied'):
        module.acquire(tmp_path, 'snapshot')


def test_failed_download_leaves_owned_partial_and_no_manifest(tmp_path, monkeypatch,
                                                            catalog_registry):
    module = catalog_registry
    install_transport(monkeypatch, module, lambda _: httpx.Response(200, text='Access denied'))
    with pytest.raises(ValueError):
        module.acquire(tmp_path, 'failed')
    assert not paths.manifest_path(tmp_path).exists()
    assert (tmp_path / 'raw/references/ipums-verification/failed.part').is_dir()
    monkeypatch.setattr(module, 'make_client', no_client)
    with pytest.raises(ValueError):
        module.acquire(tmp_path, 'failed')


def test_import_records_local_time_as_proxy_and_never_contacts_network(tmp_path, monkeypatch,
                                                                     catalog_registry):
    module = catalog_registry
    original = write_text(tmp_path, 'browser.html', SAMPLE_CATALOG)
    monkeypatch.setattr(module, 'make_client', no_client)
    directory = module.import_reference(tmp_path, 'manual', 'usa_samples', original)
    receipt = module.check_references(tmp_path, 'manual')
    entry = receipt['originals']['usa_samples']['citation']
    assert entry['proxies'] == ['retrieved_at']
    assert entry['client'] == 'manual-import'
    assert directory.joinpath('usa_samples.html').read_bytes() == original.read_bytes()
    with pytest.raises(ValueError):
        module.import_reference(tmp_path, 'manual', 'usa_samples', original)


@pytest.mark.parametrize('identity', ['../unsafe', '/absolute', 'bad.name', ''])
def test_unsafe_snapshot_names_fail_before_network(tmp_path, monkeypatch, catalog_registry,
                                                 identity):
    monkeypatch.setattr(catalog_registry, 'make_client', no_client)
    with pytest.raises(ValueError):
        catalog_registry.acquire(tmp_path, identity)


def test_post_exact_bytes_receipt_and_successful_response(tmp_path, monkeypatch):
    module = references()
    kinds = ['bls_series_metadata', 'bls_a1_metadata', 'cps_employment']
    monkeypatch.setattr(module, 'REGISTRY', {k: module.REGISTRY[k] for k in kinds})
    docs = tmp_path / 'docs'
    docs.mkdir()
    bls_documents(docs)
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == 'POST':
            assert request.content == (
                b'{"seriesid":["LNU02000000"],"startyear":"2025","endyear":"2026"}')
            assert 'registrationkey' not in request.content.decode()
            recorded = Path(__file__).parent / 'fixtures/ipums/bls-employment-v1.json'
            return httpx.Response(200, content=recorded.read_bytes())
        name = ('bls_series_metadata.txt' if 'ln.series' in str(request.url)
                else 'bls_a1_metadata.html')
        return httpx.Response(200, content=(docs / name).read_bytes())

    install_transport(monkeypatch, module, handler)
    directory = module.acquire(tmp_path, 'post')
    receipt = module.check_references(tmp_path, 'post')
    record = receipt['originals']['cps_employment']
    assert record['method'] == 'POST'
    assert record['source_url'] == 'https://api.bls.gov/publicAPI/v1/timeseries/data/'
    assert (directory / record['request_body']).read_bytes() == module.BLS_REQUEST_BODY
    assert set(receipt['files']) == {
        'bls_series_metadata.txt', 'bls_a1_metadata.html', 'cps_employment.json',
        'cps_employment.request.json'}
    assert len(calls) == 3
    monkeypatch.setattr(module, 'make_client', no_client)
    assert module.acquire(tmp_path, 'post') == directory


def test_import_staging_validates_existing_bytes_and_finalizes_only_when_complete(tmp_path,
                                                                               monkeypatch):
    module = references()
    kinds = ['usa_samples', 'usa_perwt']
    monkeypatch.setattr(module, 'REGISTRY', {k: module.REGISTRY[k] for k in kinds})
    monkeypatch.setattr(module, 'make_client', no_client)
    samples = write_text(tmp_path, 'samples.html', SAMPLE_CATALOG)
    variable = write_text(tmp_path, 'weight.html',
                          '<html><title>IPUMS USA: descr: PERWT</title><h1>PERWT</h1>'
                          '<h2>Description</h2><p>Person weight.</p></html>')
    staging = module.import_reference(tmp_path, 'imported', 'usa_samples', samples)
    assert staging.name == 'imported.part'
    with pytest.raises(ValueError, match='incomplete|occupied'):
        module.acquire(tmp_path, 'imported')
    directory = module.import_reference(tmp_path, 'imported', 'usa_perwt', variable)
    assert directory.name == 'imported'
    assert set(module.check_references(tmp_path, 'imported')['originals']) == set(kinds)


def test_import_rejects_symlink_and_unknown_identity_before_network(tmp_path, monkeypatch,
                                                                  catalog_registry):
    module = catalog_registry
    original = write_text(tmp_path, 'browser.html', SAMPLE_CATALOG)
    link = tmp_path / 'link'
    link.symlink_to(original)
    monkeypatch.setattr(module, 'make_client', no_client)
    with pytest.raises(ValueError):
        module.import_reference(tmp_path, 'x', 'usa_samples', link)
    with pytest.raises(ValueError):
        module.import_reference(tmp_path, 'x', 'unknown', original)


def test_industry_skips_observed_comma_separated_group_ranges(tmp_path):
    file = industry_workbook(tmp_path / 'industry.xlsx', leaves=[
        ['Transportation and Warehousing, and Utilities', None, None,
         '6070-6390, 0570-0690', '48-49, 22'],
        [None, 'Crop production', None, '0170', '111'],
    ])
    assert references().parse_industry_list(file, 2017).rows() == [('0170', 'Crop production')]


def test_full_registry_refuses_nonaggregate_acs_html(tmp_path):
    module = references()
    assert {'acs_2023_employment', 'acs_2024_employment'}.issubset(module.REGISTRY)
    original = write_text(tmp_path, 'acs.json', '<html><h1>Missing Key</h1></html>')
    for kind in ('acs_2023_employment', 'acs_2024_employment'):
        with pytest.raises(ValueError, match='ACS levels'):
            module._validate_original(kind, original)


@pytest.mark.parametrize('mutation', ['changed', 'extra', 'missing', 'symlink'])
def test_import_revalidates_prior_staged_originals(tmp_path, monkeypatch, mutation):
    module = references()
    monkeypatch.setattr(module, 'REGISTRY', {k: module.REGISTRY[k]
                                           for k in ('usa_samples', 'usa_perwt')})
    original = write_text(tmp_path, 'samples.html', SAMPLE_CATALOG)
    staging = module.import_reference(tmp_path, 'manual', 'usa_samples', original)
    previous = staging / 'usa_samples.html'
    if mutation == 'changed':
        previous.write_text('changed')
    elif mutation == 'extra':
        (staging / 'unexpected').write_text('unmanifested')
    elif mutation == 'missing':
        previous.unlink()
    else:
        previous.unlink()
        previous.symlink_to(original)
    with pytest.raises(ValueError):
        module.import_reference(tmp_path, 'manual', 'usa_perwt', original)
    assert not paths.manifest_path(tmp_path).exists()


def test_import_cannot_resume_a_failed_download_staging(tmp_path, monkeypatch, catalog_registry):
    module = catalog_registry
    install_transport(monkeypatch, module, lambda _: httpx.Response(403, text='Access denied'))
    with pytest.raises(httpx.HTTPStatusError):
        module.acquire(tmp_path, 'failed')
    original = write_text(tmp_path, 'browser.html', SAMPLE_CATALOG)
    with pytest.raises(ValueError, match='fresh ID'):
        module.import_reference(tmp_path, 'failed', 'usa_samples', original)


def test_redirect_refused_without_following_auth_endpoint(tmp_path, monkeypatch, catalog_registry):
    module = catalog_registry
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={'location': 'https://account.ipums.org/login'})

    install_transport(monkeypatch, module, handler)
    with pytest.raises(httpx.HTTPStatusError):
        module.acquire(tmp_path, 'redirect')
    assert len(calls) == 1
    assert not paths.manifest_path(tmp_path).exists()


@pytest.mark.parametrize('field,value', [('source_url', 'https://example.com/'),
                                         ('method', 'POST'), ('request_body', 'other.json'),
                                         ('retrieved_at_is_proxy', 'unknown')])
def test_receipt_request_provenance_mutations_fail(tmp_path, monkeypatch, catalog_registry,
                                                 field, value):
    module = catalog_registry
    install_transport(monkeypatch, module, lambda _: httpx.Response(200, text=SAMPLE_CATALOG))
    directory = module.acquire(tmp_path, 'frozen')
    receipt_file = directory / 'receipt.json'
    receipt = json.loads(receipt_file.read_text())
    receipt['originals']['usa_samples'][field] = value
    receipt_file.write_text(json.dumps(receipt))
    monkeypatch.setattr(module, 'make_client', no_client)
    with pytest.raises(ValueError):
        module.check_references(tmp_path, 'frozen')


def test_industry_distinguishes_observed_construction_heading_from_leaf(tmp_path):
    title = ('Construction (the cleaning of buildings and dwellings is incidental during '
             'construction and immediately after construction)')
    file = industry_workbook(tmp_path / 'industry.xlsx', leaves=[
        ['Construction', None, None, '0770', '23'],
        [None, title, None, '0770', '23'],
        [None, 'Management of companies and enterprises', None, '7570', '55'],
        [None, 'Management of companies and enterprises ', None, '7570', '55'],
    ])
    assert references().parse_industry_list(file, 2017).rows() == [
        ('0770', title), ('7570', 'Management of companies and enterprises')]


@pytest.mark.parametrize('field,value', [('source_url', 'https://example.com/'),
                                         ('method', 'POST'), ('retrieved_at', 'not a time')])
def test_import_rejects_changed_staging_provenance_before_publication(tmp_path, monkeypatch,
                                                                    field, value):
    module = references()
    monkeypatch.setattr(module, 'REGISTRY', {k: module.REGISTRY[k]
                                           for k in ('usa_samples', 'usa_perwt')})
    samples = write_text(tmp_path, 'samples.html', SAMPLE_CATALOG)
    weight = write_text(tmp_path, 'weight.html',
                        '<html><title>IPUMS USA: descr: PERWT</title><h1>PERWT</h1>'
                        '<h2>Description</h2></html>')
    staging = module.import_reference(tmp_path, 'changed', 'usa_samples', samples)
    state_file = staging / 'import-state.json'
    state = json.loads(state_file.read_text())
    state['originals']['usa_samples'][field] = value
    state_file.write_text(json.dumps(state))
    with pytest.raises(ValueError):
        module.import_reference(tmp_path, 'changed', 'usa_perwt', weight)
    assert not paths.manifest_path(tmp_path).exists()
    assert not (staging.parent / 'changed').exists()


def test_bls_absent_october_is_not_fabricated(tmp_path):
    bls_documents(tmp_path)
    response = bls_response()
    response['Results']['series'][0]['data'].pop(9)
    file = write_text(tmp_path, 'levels.json', json.dumps(response))
    frame = references().parse_bls_levels(file)
    assert frame.height == 20
    assert not frame.filter((pl.col('year') == 2025) & (pl.col('month') == 10)).height


def test_industry_refuses_changed_documented_special_label(tmp_path):
    file = industry_workbook(tmp_path / 'industry.xlsx', leaves=[
        [None, 'Crop production', None, '0170', '111'],
        [None, 'Not a documented special meaning', None, '9920', None],
    ])
    with pytest.raises(ValueError, match='special'):
        references().parse_industry_list(file, 2017)


@pytest.mark.parametrize('operation', ['acquire', 'import'])
@pytest.mark.parametrize('retained_manifest', [
    'all_originals', 'request_body_only', 'receipt_only'])
def test_recorded_missing_snapshot_refused_before_staging_and_client(tmp_path, monkeypatch,
                                                                   operation, retained_manifest):
    module = references()
    kinds = ['bls_series_metadata', 'bls_a1_metadata', 'cps_employment']
    monkeypatch.setattr(module, 'REGISTRY', {kind: module.REGISTRY[kind] for kind in kinds})
    originals = tmp_path / 'official-fixtures'
    originals.mkdir()
    bls_documents(originals)
    response = Path(__file__).parent / 'fixtures/ipums/bls-employment-v1.json'
    imported = originals / 'levels.json'
    imported.write_bytes(response.read_bytes())

    def handler(request):
        if request.method == 'POST':
            return httpx.Response(200, content=response.read_bytes())
        name = ('bls_series_metadata.txt' if 'ln.series' in str(request.url)
                else 'bls_a1_metadata.html')
        return httpx.Response(200, content=(originals / name).read_bytes())

    install_transport(monkeypatch, module, handler)
    completed = module.acquire(tmp_path, 'recorded')
    module.check_references(tmp_path, 'recorded')
    manifest_file = paths.manifest_path(tmp_path)
    if retained_manifest != 'all_originals':
        from dataclasses import asdict

        suffix = ('/receipt.json' if retained_manifest == 'receipt_only'
                  else '/cps_employment.request.json')
        retained = [asdict(entry) for entry in manifest.read_manifest(manifest_file)
                    if entry.path.endswith(suffix)]
        assert len(retained) == 1
        manifest_file.write_text(json.dumps(retained[0]) + '\n')
    recorded_bytes = manifest_file.read_bytes()
    shutil.rmtree(completed)
    staging = completed.with_name('recorded.part')
    monkeypatch.setattr(module, 'make_client', no_client)

    with pytest.raises(ValueError, match='recorded.*restor'):
        if operation == 'acquire':
            module.acquire(tmp_path, 'recorded')
        else:
            module.import_reference(tmp_path, 'recorded', 'cps_employment', imported)

    assert not completed.exists()
    assert not staging.exists()
    assert manifest_file.read_bytes() == recorded_bytes


@pytest.mark.parametrize('year', [2023, 2024])
@pytest.mark.parametrize('include_pr', [False, True])
def test_acs_exact_schema_complete_states_and_optional_retained_pr(tmp_path, year, include_pr):
    body = acs_levels(include_pr=include_pr)
    body[1][1] = '0'
    file = write_text(tmp_path, 'acs.json', json.dumps(body))
    frame = references().parse_acs_levels(file, year)
    assert frame.schema == {'year': pl.Int64, 'state_fips': pl.String,
                            'published': pl.Float64, 'units': pl.String}
    assert frame['year'].to_list() == [year] * (52 if include_pr else 51)
    assert frame['state_fips'].to_list() == [*ACS_STATE_CODES, *(['72'] if include_pr else [])]
    assert frame.row(0) == (year, '01', 0.0, 'persons')
    assert frame.row(1) == (year, '02', 101.0, 'persons')
    comparable = frame.filter(pl.col('state_fips').is_in(references().ACS_COMPARISON_STATES))
    assert comparable.height == 51
    assert set(comparable['state_fips']) == set(ACS_STATE_CODES)
    if include_pr:
        assert frame.filter(pl.col('state_fips') == '72').rows() == [
            (year, '72', 777.0, 'persons')]


@pytest.mark.parametrize('mutation', ['header_name', 'header_estimate', 'header_state',
    'header_order', 'header_extra_units', 'header_extra_year', 'header_duplicate',
    'repeated_header', 'row_short', 'row_extra', 'row_object', 'missing_state',
    'missing_dc', 'duplicate_state', 'duplicate_pr', 'extra_territory', 'unknown_state',
    'integer_state', 'unpadded_state', 'empty_name', 'null_name'])
def test_acs_refuses_header_row_or_geography_drift(tmp_path, mutation):
    body = acs_levels()
    if mutation.startswith('header_'):
        if mutation == 'header_order':
            body[0][0], body[0][1] = body[0][1], body[0][0]
        elif mutation == 'header_extra_units':
            body[0].append('units')
        elif mutation == 'header_extra_year':
            body[0].append('year')
        elif mutation == 'header_duplicate':
            body[0].append('NAME')
        else:
            column = {'header_name': 0, 'header_estimate': 1, 'header_state': 2}[mutation]
            body[0][column] = 'unexpected'
    elif mutation == 'repeated_header':
        body.append(body[0].copy())
    elif mutation == 'row_short':
        body[1].pop()
    elif mutation == 'row_extra':
        body[1].append('persons')
    elif mutation == 'row_object':
        body[1] = {'NAME': 'Fixture', 'B23025_004E': '100', 'state': '01'}
    elif mutation == 'missing_state':
        body.pop(1)
    elif mutation == 'missing_dc':
        body = [row for row in body if row[2] != '11']
    elif mutation == 'duplicate_state':
        body.append(body[1].copy())
    elif mutation == 'duplicate_pr':
        body.append(body[-1].copy())
    elif mutation == 'extra_territory':
        body.append(['Guam', '100', '66'])
    elif mutation == 'unknown_state':
        body[1][2] = '03'
    elif mutation == 'integer_state':
        body[1][2] = 1
    elif mutation == 'unpadded_state':
        body[1][2] = '1'
    elif mutation == 'empty_name':
        body[1][0] = ' '
    elif mutation == 'null_name':
        body[1][0] = None
    with pytest.raises(ValueError):
        references().parse_acs_levels(write_text(tmp_path, 'acs.json', json.dumps(body)), 2023)


@pytest.mark.parametrize('value', ['-1', '-0', 'NaN', 'Infinity', 'inf', '1e3', '100 persons',
    '1,000', '1000.5', '', ' 100', '１００', '9' * 400, None, True, 100, 100.0])
def test_acs_refuses_nonfinite_negative_nonnumeric_or_nonstring_levels(tmp_path, value):
    body = acs_levels()
    body[1][1] = value
    with pytest.raises(ValueError):
        references().parse_acs_levels(write_text(tmp_path, 'acs.json', json.dumps(body)), 2023)


@pytest.mark.parametrize('body', [[], {}, {'year': 2024, 'data': []}, ['not a header'],
                                 [['NAME', 'B23025_004E', 'state'], ['Fixture', '1', '01']]])
def test_acs_refuses_noncanonical_or_incomplete_response(tmp_path, body):
    with pytest.raises(ValueError):
        references().parse_acs_levels(write_text(tmp_path, 'acs.json', json.dumps(body)), 2023)


@pytest.mark.parametrize('year', [2022, 2025, '2023', None, True, 2023.0])
def test_acs_refuses_unsupported_year_before_file_read(tmp_path, year):
    with pytest.raises(ValueError):
        references().parse_acs_levels(tmp_path / 'absent.json', year)


def test_acs_body_does_not_authenticate_source_year(tmp_path):
    file = write_text(tmp_path, 'arbitrary-name.json', json.dumps(acs_levels()))
    earlier = references().parse_acs_levels(file, 2023)
    later = references().parse_acs_levels(file, 2024)
    assert earlier['year'].unique().to_list() == [2023]
    assert later['year'].unique().to_list() == [2024]
    assert earlier.drop('year').equals(later.drop('year'))


@pytest.mark.parametrize('operation', ['acquire', 'import'])
def test_completed_snapshot_receipt_is_manifested_and_whole_tree_auditable(tmp_path, monkeypatch,
                                                                        catalog_registry,
                                                                        operation):
    module = catalog_registry
    original = write_text(tmp_path, 'catalog.html', SAMPLE_CATALOG)
    before = datetime.now(UTC).replace(microsecond=0)
    if operation == 'acquire':
        install_transport(monkeypatch, module, lambda _: httpx.Response(200, text=SAMPLE_CATALOG))
        completed = module.acquire(tmp_path, 'auditable')
    else:
        monkeypatch.setattr(module, 'make_client', no_client)
        completed = module.import_reference(tmp_path, 'auditable', 'usa_samples', original)
    after = datetime.now(UTC)
    assert manifest_audit.audit(tmp_path) == []
    receipt_entry = manifest.entry_for(paths.manifest_path(tmp_path), completed / 'receipt.json')
    assert receipt_entry.source_url is None
    assert receipt_entry.client == 'embedding-data'
    assert receipt_entry.client_version
    assert receipt_entry.proxies == ()
    assert before <= datetime.fromisoformat(receipt_entry.retrieved_at) <= after
    receipt = module.check_references(tmp_path, 'auditable')
    assert 'receipt.json' not in receipt['files']
    assert all(not entry['path'].endswith('/receipt.json') for entry in receipt['raw_citations'])
    assert len(manifest.read_manifest(paths.manifest_path(tmp_path))) == 2


def test_cached_receipt_checks_external_manifest_hash_even_for_json_whitespace(tmp_path,
                                                                            monkeypatch,
                                                                            catalog_registry):
    module = catalog_registry
    install_transport(monkeypatch, module, lambda _: httpx.Response(200, text=SAMPLE_CATALOG))
    completed = module.acquire(tmp_path, 'receipt-hash')
    receipt = completed / 'receipt.json'
    receipt.write_bytes(receipt.read_bytes() + b' ')
    monkeypatch.setattr(module, 'make_client', no_client)
    with pytest.raises(ValueError, match='SHA-256'):
        module.acquire(tmp_path, 'receipt-hash')


def test_cached_receipt_requires_external_manifest_entry(tmp_path, monkeypatch, catalog_registry):
    module = catalog_registry
    install_transport(monkeypatch, module, lambda _: httpx.Response(200, text=SAMPLE_CATALOG))
    module.acquire(tmp_path, 'receipt-missing')
    manifest_file = paths.manifest_path(tmp_path)
    records = [json.loads(line) for line in manifest_file.read_text().splitlines()]
    manifest_file.write_text(''.join(json.dumps(record) + '\n' for record in records
                                     if not record['path'].endswith('/receipt.json')))
    monkeypatch.setattr(module, 'make_client', no_client)
    with pytest.raises(KeyError):
        module.acquire(tmp_path, 'receipt-missing')


@pytest.fixture
def full_reference_registry(tmp_path, monkeypatch):
    module = references()
    registered = dict(module.REGISTRY)
    assert len(registered) == 25
    originals = reference_originals(tmp_path / 'public-layout-fixtures', registered)
    fixtures = {kind: replace(reference, sha256=manifest.sha256_file(originals[kind])
                              if reference.sha256 else None)
                for kind, reference in registered.items()}
    assert set(fixtures) == set(registered)
    assert all(fixtures[kind].url == reference.url and
               fixtures[kind].filename == reference.filename
               for kind, reference in registered.items())
    monkeypatch.setattr(module, 'REGISTRY', fixtures)
    return module, originals


def forbid_reference_access(monkeypatch, module):
    def forbidden(*args, **kwargs):
        raise AssertionError('credential/network access forbidden in offline replay/import')

    access = module.ipums_census_access
    for name in ('read_credential', 'dotenv_values', 'fetch_original', 'make_client'):
        monkeypatch.setattr(access, name, forbidden)
    monkeypatch.setattr(module, 'make_client', forbidden)


def assert_full_reference_snapshot(data_dir, module, completed, originals, *, imported):
    receipt = module.check_references(data_dir, completed.name)
    assert len(receipt['originals']) == 25
    assert len(receipt['files']) == 26
    assert len(receipt['raw_citations']) == 26
    assert 'receipt.json' not in receipt['files']
    assert manifest_audit.audit(data_dir) == []
    entries = manifest.read_manifest(paths.manifest_path(data_dir))
    assert len(entries) == 27
    assert sum(entry.source_url is None for entry in entries) == 1
    for kind, original in originals.items():
        reference = module.REGISTRY[kind]
        assert (completed / reference.filename).read_bytes() == original.read_bytes()
        record = receipt['originals'][kind]
        assert record['source_url'] == reference.url
        assert record['retrieved_at_is_proxy'] is imported
        assert record['citation']['client'] == ('manual-import' if imported else 'httpx')
        assert record['citation']['proxies'] == (['retrieved_at'] if imported else [])
    for year, expected in ((2023, 100.0), (2024, 200.0)):
        levels = module.parse_acs_levels(completed / f'acs_{year}_employment.json', year)
        assert levels.row(0) == (year, '01', expected, 'persons')
        assert levels.height == 52
    assert module.parse_bls_levels(completed / 'cps_employment.json').height == 21
    assert module.parse_industry_list(completed / 'census_industry_2017.xlsx', 2017).height == 2
    assert module.parse_industry_list(completed / 'census_industry_2022.xlsx', 2022).height == 2
    receipt_entry = manifest.entry_for(paths.manifest_path(data_dir), completed / 'receipt.json')
    assert receipt_entry.client == 'embedding-data'
    assert receipt_entry.source_url is None
    assert receipt_entry.proxies == ()
    return receipt


def test_full_registry_acquire_protected_queries_audit_and_credential_free_cached_replay(
        tmp_path, monkeypatch, full_reference_registry, caplog):
    import logging

    module, originals = full_reference_registry
    access = module.ipums_census_access
    dummy = 'fake-full-reference-credential'
    public_calls, protected_calls, credential_reads = [], [], []
    public_urls = {reference.url: kind for kind, reference in module.REGISTRY.items()
                   if kind not in access.ACS_QUERIES}

    def public(request):
        public_calls.append(request)
        assert 'key' not in request.url.params
        kind = public_urls[str(request.url)]
        assert request.method == module.REGISTRY[kind].method
        if request.method == 'POST':
            assert request.content == module.BLS_REQUEST_BODY
            assert request.headers['content-type'] == 'application/json'
        return httpx.Response(200, content=originals[kind].read_bytes())

    def protected(request):
        protected_calls.append(request)
        assert request.method == 'GET'
        assert request.url.params['key'] == dummy
        assert request.url.params['get'] == 'NAME,B23025_004E'
        assert request.url.params['for'] == 'state:*'
        year = request.url.path.split('/')[2]
        kind = f'acs_{year}_employment'
        assert kind in access.ACS_QUERIES
        return httpx.Response(200, content=originals[kind].read_bytes())

    def fake_credential(**kwargs):
        credential_reads.append(kwargs)
        return dummy

    monkeypatch.setattr(access, 'read_credential', fake_credential)
    monkeypatch.setattr(access, 'make_client', lambda: httpx.Client(
        transport=httpx.MockTransport(protected), trust_env=False, follow_redirects=False))
    install_transport(monkeypatch, module, public)
    caplog.set_level(logging.DEBUG)
    completed = module.acquire(tmp_path, 'full-acquire')
    assert len(public_calls) == 23
    assert len(protected_calls) == 2
    assert len(credential_reads) == 1
    receipt = assert_full_reference_snapshot(
        tmp_path, module, completed, originals, imported=False)
    assert dummy not in caplog.text
    assert dummy not in json.dumps(receipt)
    assert all(dummy.encode() not in file.read_bytes() for file in completed.iterdir())
    manifest_bytes = paths.manifest_path(tmp_path).read_bytes()
    assert dummy.encode() not in manifest_bytes
    forbid_reference_access(monkeypatch, module)
    assert module.acquire(
        tmp_path, 'full-acquire', census_env_file=tmp_path / 'never-read.env') == completed
    assert module.check_references(tmp_path, 'full-acquire') == receipt
    assert paths.manifest_path(tmp_path).read_bytes() == manifest_bytes


def test_full_registry_import_finalizes_once_and_cached_replay_is_offline(tmp_path, monkeypatch,
                                                                       full_reference_registry):
    module, originals = full_reference_registry
    forbid_reference_access(monkeypatch, module)
    for index, (kind, original) in enumerate(originals.items()):
        completed = module.import_reference(tmp_path, 'full-import', kind, original)
        if index < 24:
            assert completed.name == 'full-import.part'
            assert not (completed / 'receipt.json').exists()
            assert not paths.manifest_path(tmp_path).exists()
        else:
            assert completed.name == 'full-import'
    receipt = assert_full_reference_snapshot(tmp_path, module, completed, originals, imported=True)
    assert module.acquire(
        tmp_path, 'full-import', census_env_file=tmp_path / 'never-read.env') == completed
    assert module.check_references(tmp_path, 'full-import') == receipt
    with pytest.raises(ValueError, match='immutable'):
        module.import_reference(tmp_path, 'full-import', 'usa_samples', originals['usa_samples'])
