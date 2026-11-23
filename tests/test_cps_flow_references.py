'''Stage 11 reference snapshot: registry, anchors, staged acquisition and import, receipt.'''

import json
import shutil
from datetime import UTC, datetime
from functools import partial
from importlib.metadata import version

import httpx
import pytest
from cps_flow_fixtures import (
    INDUSTRY_HEADER,
    OCCUPATION_HEADER,
    bls_workbook,
    industry_csv,
    ipums_page,
    layout_text,
    no_live_clients,  # noqa: F401
    occupation_csv,
    offline_guards,
    reference_originals,
    write_workbook,
)

from embedding_data import cps_flow_references as module
from embedding_data import manifest, paths
from embedding_data.osha_benchmark_download import USER_AGENT

REAL_MAKE_CLIENT = module.make_client
CENSUS_2026 = 'https://www2.census.gov/programs-surveys/cps/datasets/2026/basic/'
CENSUS_2025 = 'https://www2.census.gov/programs-surveys/cps/datasets/2025/basic/'
LAYOUT = '2025_Basic_CPS_Public_Use_Record_Layout_plus_IO_Code_list.txt'
SPEC_TABLE = {
    'cps_basic_2026_industry_codes': (CENSUS_2026 + 'cps_industry_codes.csv',
                                      'cps_industry_codes.csv'),
    'cps_basic_2026_occupation_codes': (CENSUS_2026 + 'cps_occupation_codes.csv',
                                        'cps_occupation_codes.csv'),
    'cps_basic_2025_layout_codes': (CENSUS_2025 + LAYOUT, LAYOUT),
    'bls_cps_industry_2022': (
        'https://www.bls.gov/cps/2022-census-industry-titles-and-code-list.xlsx',
        '2022-census-industry-titles-and-code-list.xlsx'),
    'bls_cps_occupation_2018': (
        'https://www.bls.gov/cps/2018-census-occupation-classification-titles-and-code-list.xlsx',
        '2018-census-occupation-classification-titles-and-code-list.xlsx'),
    'ipums_cps_ind_2020_codes': ('https://cps.ipums.org/cps/codes/ind_2020_codes.shtml',
                                 'ind_2020_codes.shtml'),
    'ipums_cps_occ_2020_codes': ('https://cps.ipums.org/cps/codes/occ_2020_codes.shtml',
                                 'occ_2020_codes.shtml'),
}
BLS_ANCHORS = {'bls_cps_industry_2022': ('9890', 'Part of 92811'),
               'bls_cps_occupation_2018': ('9840', '55-0000')}
KINDS = list(SPEC_TABLE)
REFUSED_KIND = 'bls_cps_industry_2022'
REFUSED_URL = SPEC_TABLE[REFUSED_KIND][0]
SNAPSHOT = 'data/raw/references/cps-job-flows'


def bodies(directory):
    originals = reference_originals(directory)
    return {module.REGISTRY[kind].url: file.read_bytes() for kind, file in originals.items()}


def serve(monkeypatch, directory, calls=None, overrides=None):
    '''Patch `make_client` with a partial that injects a mock transport serving the originals.'''
    served = bodies(directory)
    calls = [] if calls is None else calls

    def handler(request):
        calls.append(request)
        url = str(request.url)
        if overrides and url in overrides:
            return overrides[url](request)
        return ok(served[url])

    monkeypatch.setattr(module, 'make_client',
                        partial(REAL_MAKE_CLIENT, transport=httpx.MockTransport(handler)))
    return calls


def ok(body, **headers):
    headers = {'content-length': str(len(body)), **headers}
    return httpx.Response(200, headers=headers, stream=httpx.ByteStream(body))


def refuse_industry_workbook(monkeypatch, directory, calls=None):
    return serve(monkeypatch, directory, calls,
                 {REFUSED_URL: lambda request: httpx.Response(403)})


def manifest_entries(tmp_path):
    return manifest.read_manifest(paths.manifest_path(tmp_path / 'data'))


def published(tmp_path, reference_id='refs'):
    '''A complete snapshot through seven imports; returns its directory.'''
    originals = reference_originals(tmp_path / 'originals')
    result = None
    for kind, file in originals.items():
        result = module.import_reference(tmp_path / 'data', reference_id, kind, file)
    return result


def test_registry_holds_the_seven_kinds_with_the_spec_urls():
    assert {kind: (item.url, item.filename) for kind, item in module.REGISTRY.items()} \
        == SPEC_TABLE
    assert module.PARSER_VERSION == 'cps-job-flows-references-v1'
    assert module.MAX_ORIGINAL_BYTES == 32 * 1024 * 1024
    assert isinstance(module.REGISTRY[KINDS[0]], module.Reference)


def test_make_client_follows_no_redirect_reads_no_environment_and_sends_the_user_agent():
    with REAL_MAKE_CLIENT() as client:
        assert client.timeout == httpx.Timeout(60)
        assert client.follow_redirects is False
        assert client._trust_env is False
        assert client.headers['user-agent'] == USER_AGENT


def test_a_missed_patch_fails_instead_of_reaching_a_network(tmp_path):
    with pytest.raises(AssertionError, match='without a patch'):
        module.acquire(tmp_path / 'data', 'unpatched')


def test_offline_guards_count_and_deny_the_live_seams(monkeypatch):
    counts = offline_guards(monkeypatch)
    assert counts == {'network': 0, 'environment_file': 0, 'live_client': 0}
    with pytest.raises(AssertionError):
        module.make_client()
    with pytest.raises(AssertionError):
        httpx.Client()
    assert counts == {'network': 1, 'environment_file': 0, 'live_client': 1}


def test_fixture_originals_are_valid_for_every_kind(tmp_path):
    originals = reference_originals(tmp_path)
    assert list(originals) == KINDS
    for kind, file in originals.items():
        assert file.name == SPEC_TABLE[kind][1]
        module.validate_original(kind, file)


def change_label(kind, file):
    if kind in BLS_ANCHORS:
        code, partner = BLS_ANCHORS[kind]
        bls_workbook(file, code, partner, label='Military (last job)')
    else:
        file.write_bytes(file.read_bytes().replace(b'Armed Forces', b'Military'))


@pytest.mark.parametrize('kind', KINDS)
def test_each_original_must_carry_its_anchor(tmp_path, kind):
    file = reference_originals(tmp_path)[kind]
    module.validate_original(kind, file)
    change_label(kind, file)
    with pytest.raises(ValueError):
        module.validate_original(kind, file)


def test_an_unknown_kind_is_refused(tmp_path):
    with pytest.raises(ValueError, match='unknown'):
        module.validate_original('cps_basic_2027_codes', tmp_path / 'file')


@pytest.mark.parametrize('mutation', [
    {'naics': '928110'},
    {'row_type': 'total'},
    {'code': '9891'},
    {'header': INDUSTRY_HEADER.replace('ROW_TYPE', 'ROWTYPE')},
    {'header': INDUSTRY_HEADER.replace('2022 NAICS Code', '2017 NAICS Code')},
    {'header': INDUSTRY_HEADER + ',2022 NAICS Code'},
    {'extra': ('detail,Military,9890,',)},
    *({'extra': (f'detail,Military,{code},928110',)}
      for code in ('9670', '9680', '9690', '9770', '9780', '9790', '9870')),
    {'extra': ('summary,Military,9870,',)},
    {'extra': ('detail,Military, 9770 ,',)},
])
def test_industry_csv_drift_fails(tmp_path, mutation):
    file = industry_csv(tmp_path / 'industry.csv', **mutation)
    with pytest.raises(ValueError):
        module.validate_original('cps_basic_2026_industry_codes', file)


def test_industry_csv_allows_an_exact_repeat_of_the_special_row(tmp_path):
    file = industry_csv(tmp_path / 'industry.csv', extra=('detail,Armed Forces,9890,',))
    module.validate_original('cps_basic_2026_industry_codes', file)


@pytest.mark.parametrize('extra', [('detail,Other,9880,',), ('detail,Other,9660,',)])
def test_industry_csv_allows_other_codes(tmp_path, extra):
    file = industry_csv(tmp_path / 'industry.csv', extra=extra)
    module.validate_original('cps_basic_2026_industry_codes', file)


def test_industry_csv_reads_with_or_without_a_byte_order_mark(tmp_path):
    file = industry_csv(tmp_path / 'industry.csv')
    assert file.read_bytes().startswith(b'\xef\xbb\xbf')
    file.write_bytes(file.read_bytes()[3:])
    module.validate_original('cps_basic_2026_industry_codes', file)


@pytest.mark.parametrize('mutation', [
    {'soc': '55-0000'},
    {'row_type': 'total'},
    {'code': '9841'},
    {'header': OCCUPATION_HEADER.replace('ROW_TYPE', 'ROWTYPE')},
    {'header': OCCUPATION_HEADER.replace('2018 SOC Code', '2010 SOC Code')},
    *({'extra': (f'detail,{code},,Military',)} for code in ('9800', '9810', '9820', '9830')),
    {'extra': ('summary,9815,,Military',)},
])
def test_occupation_csv_drift_fails(tmp_path, mutation):
    file = occupation_csv(tmp_path / 'occupation.csv', **mutation)
    with pytest.raises(ValueError):
        module.validate_original('cps_basic_2026_occupation_codes', file)


@pytest.mark.parametrize('code', ['9799', '9831', '9850'])
def test_occupation_csv_allows_codes_beside_the_retired_range(tmp_path, code):
    file = occupation_csv(tmp_path / 'occupation.csv', extra=(f'detail,{code},,Other',))
    module.validate_original('cps_basic_2026_occupation_codes', file)


def test_csv_that_is_not_text_is_refused(tmp_path):
    file = tmp_path / 'industry.csv'
    file.write_bytes(b'\xff\xfe\x00\xd8 not text')
    with pytest.raises(ValueError):
        module.validate_original('cps_basic_2026_industry_codes', file)


@pytest.mark.parametrize('text', [
    layout_text(industry='Military\t\t9890'),
    layout_text(industry='Armed Forces  9890'),
    layout_text(industry='Armed Forces\t\t9891'),
    layout_text(occupation='9840\t\tMilitary'),
    layout_text(occupation='9840  Armed Forces'),
    layout_text(occupation='Group 9840\t\tArmed Forces'),
    layout_text(occupation='Armed Forces\t\t9840'),
    'CPS record layout\n',
])
def test_layout_drift_fails(tmp_path, text):
    file = tmp_path / 'layout.txt'
    file.write_text(text, encoding='utf-8')
    with pytest.raises(ValueError):
        module.validate_original('cps_basic_2025_layout_codes', file)


def test_layout_anchor_may_sit_inside_a_longer_line(tmp_path):
    file = tmp_path / 'layout.txt'
    file.write_text(layout_text(industry='Group: Armed Forces\t\t9890 (see note)'),
                    encoding='utf-8')
    module.validate_original('cps_basic_2025_layout_codes', file)


def workbook_case(file, case, code, partner):
    rows = {
        'wrong code': [[None, 'Armed Forces (last job)', None, '9999', partner]],
        'wrong partner': [[None, 'Armed Forces (last job)', None, code, 'Part of 99999']],
        'code cell padded': [[None, 'Armed Forces (last job)', None, code + '1', partner]],
        'split rows': [[None, 'Armed Forces (last job)', None, None, partner],
                       [None, 'Other', None, code, None]],
        'label inside a longer title': [[None, 'Not Armed Forces (last job)', None, code,
                                         partner]],
        'single cell row': [[f'{code} Armed Forces (last job) {partner}']],
        'no partner': [[None, 'Armed Forces (last job)', None, code, None]],
        'no label': [[None, None, None, code, partner]],
        'empty sheet only': [[None]],
    }[case]
    return write_workbook(file, {'List': rows})


@pytest.mark.parametrize('case', [
    'wrong code', 'wrong partner', 'code cell padded', 'split rows',
    'label inside a longer title', 'single cell row', 'no partner', 'no label',
    'empty sheet only'])
@pytest.mark.parametrize('kind', list(BLS_ANCHORS))
def test_workbook_row_must_hold_code_label_and_partner_together(tmp_path, kind, case):
    code, partner = BLS_ANCHORS[kind]
    file = workbook_case(tmp_path / 'case.xlsx', case, code, partner)
    with pytest.raises(ValueError):
        module.validate_original(kind, file)


@pytest.mark.parametrize('kind', list(BLS_ANCHORS))
def test_workbook_anchor_on_any_sheet_counts_and_label_may_continue(tmp_path, kind):
    code, partner = BLS_ANCHORS[kind]
    file = write_workbook(tmp_path / 'a.xlsx', {
        'First': [[None, 'Armed Forces (last job)', None, '1234', 'Part of 11111']],
        'Second': [[None, 'Armed Forces (last job), see note', None, f' {code} ',
                    f'{partner} and more']]})
    module.validate_original(kind, file)
    first_only = write_workbook(tmp_path / 'b.xlsx', {
        'First': [[None, 'Armed Forces (last job)', None, code, partner]],
        'Second': [[None, 'Other', None, '1234', None]]})
    module.validate_original(kind, first_only)


def test_html_masquerading_as_a_workbook_is_refused(tmp_path):
    file = tmp_path / 'list.xlsx'
    file.write_text('<html>Access denied</html>')
    with pytest.raises(ValueError, match='workbook'):
        module.validate_original('bls_cps_industry_2022', file)


IPUMS_PAGES = [('ipums_cps_ind_2020_codes', '9890', '9840'),
               ('ipums_cps_occ_2020_codes', '9840', '9890')]


@pytest.mark.parametrize('kind, code, other', IPUMS_PAGES)
def test_ipums_page_with_the_label_right_after_the_code_passes(tmp_path, kind, code, other):
    file = tmp_path / 'page.shtml'
    file.write_text(ipums_page(code), encoding='utf-8')
    module.validate_original(kind, file)
    file.write_text(f'<dt> {code} </dt>\n  <dd>\n Armed Forces </dd>', encoding='utf-8')
    module.validate_original(kind, file)


@pytest.mark.parametrize('case', ['other code', 'label drift', 'code padded', 'not adjacent',
                                  'not a page'])
@pytest.mark.parametrize('kind, code, other', IPUMS_PAGES)
def test_ipums_page_drift_fails(tmp_path, kind, code, other, case):
    text = {
        'other code': ipums_page(other),
        'label drift': ipums_page(code, 'Military'),
        'code padded': ipums_page(code + '1'),
        'not adjacent': f'<dt>{code}</dt><dd>Military</dd><dt>1</dt><dd>Armed Forces</dd>',
        'not a page': 'Access denied',
    }[case]
    file = tmp_path / 'page.shtml'
    file.write_text(text, encoding='utf-8')
    with pytest.raises(ValueError):
        module.validate_original(kind, file)


def test_acquire_publishes_a_manifested_snapshot_and_receipt(tmp_path, monkeypatch):
    calls = serve(monkeypatch, tmp_path / 'served')
    data_dir = tmp_path / 'data'
    final = module.acquire(data_dir, 'refs')
    assert final == data_dir / 'raw/references/cps-job-flows/refs'
    assert [str(call.url) for call in calls] == [item.url for item in module.REGISTRY.values()]
    assert {call.method for call in calls} == {'GET'}
    assert {call.headers['user-agent'] for call in calls} == {USER_AGENT}
    assert sorted(file.name for file in final.iterdir()) == sorted(
        [item.filename for item in module.REGISTRY.values()] + ['receipt.json'])
    assert not final.with_name('refs.part').exists()
    entries = manifest_entries(tmp_path)
    assert len(entries) == 8
    receipt = module.check_references(data_dir, 'refs')
    assert receipt['reference_id'] == 'refs'
    assert receipt['parser_version'] == module.PARSER_VERSION
    assert set(receipt) == {'reference_id', 'parser_version', 'originals', 'files',
                            'raw_citations'}
    assert set(receipt['originals']) == set(module.REGISTRY)
    assert set(receipt['files']) == {item.filename for item in module.REGISTRY.values()}
    for entry in entries[:7]:
        assert entry.path.startswith('references/cps-job-flows/refs/')
        assert (entry.client, entry.client_version) == ('httpx', version('httpx'))
        assert entry.proxies == () and entry.source_url is not None
        assert entry.sha256 == manifest.sha256_file(final / entry.path.rsplit('/', 1)[1])
    receipt_entry = entries[7]
    assert receipt_entry.path == 'references/cps-job-flows/refs/receipt.json'
    assert receipt_entry.client == 'embedding-data'
    assert receipt_entry.source_url is None and receipt_entry.proxies == ()
    assert receipt_entry.sha256 == manifest.sha256_file(final / 'receipt.json')
    for kind, record in receipt['originals'].items():
        assert record['retrieved_at_is_proxy'] is False
        assert record['source_url'] == module.REGISTRY[kind].url
        assert record['method'] == 'GET'
        assert record['citation']['source_url'] == module.REGISTRY[kind].url
        assert datetime.fromisoformat(record['retrieved_at']).tzinfo is not None
    assert datetime.fromisoformat(receipt['originals'][KINDS[0]]['retrieved_at']).tzinfo == UTC


def test_occupied_final_is_verified_not_replaced_and_needs_no_client(tmp_path, monkeypatch):
    serve(monkeypatch, tmp_path / 'served')
    final = module.acquire(tmp_path / 'data', 'refs')
    before = manifest_entries(tmp_path)
    monkeypatch.setattr(module, 'make_client', lambda: pytest.fail('contacted a service'))
    assert module.acquire(tmp_path / 'data', 'refs') == final
    assert manifest_entries(tmp_path) == before
    (final / 'extra.txt').write_text('unmanifested')
    with pytest.raises(ValueError, match='inventory'):
        module.acquire(tmp_path / 'data', 'refs')


def test_refused_kind_leaves_staging_and_import_completes_it(tmp_path, monkeypatch):
    refuse_industry_workbook(monkeypatch, tmp_path / 'served')
    data_dir = tmp_path / 'data'
    with pytest.raises(ValueError, match=REFUSED_KIND):
        module.acquire(data_dir, 'refs')
    staging = data_dir / 'raw/references/cps-job-flows/refs.part'
    assert sorted(file.name for file in staging.iterdir()) == sorted(
        [item.filename for kind, item in module.REGISTRY.items() if kind != REFUSED_KIND]
        + ['staging-state.json'])
    state = json.loads((staging / 'staging-state.json').read_text())
    assert state['parser_version'] == module.PARSER_VERSION
    assert set(state['kinds']) == set(module.REGISTRY) - {REFUSED_KIND}
    for kind, item in state['kinds'].items():
        assert item['request']['retrieved_at_is_proxy'] is False
        assert item['file'] == {
            'sha256': manifest.sha256_file(staging / module.REGISTRY[kind].filename),
            'size': (staging / module.REGISTRY[kind].filename).stat().st_size}
    assert not manifest_entries(tmp_path)
    browser = reference_originals(tmp_path / 'browser')[REFUSED_KIND]
    final = module.import_reference(data_dir, 'refs', REFUSED_KIND, browser)
    assert final == data_dir / 'raw/references/cps-job-flows/refs'
    assert not staging.exists()
    receipt = module.check_references(data_dir, 'refs')
    imported = receipt['originals'][REFUSED_KIND]
    assert imported['retrieved_at_is_proxy'] is True
    assert imported['citation']['client'] == 'manual-import'
    assert imported['citation']['client_version'] == version('embedding-data')
    assert imported['citation']['proxies'] == ['retrieved_at']
    others = [r for kind, r in receipt['originals'].items() if kind != REFUSED_KIND]
    assert all(r['retrieved_at_is_proxy'] is False and r['citation']['client'] == 'httpx'
               and r['citation']['proxies'] == [] for r in others)
    by_path = {entry.path.rsplit('/', 1)[1]: entry for entry in manifest_entries(tmp_path)}
    entry = by_path[module.REGISTRY[REFUSED_KIND].filename]
    assert (entry.client, entry.proxies) == ('manual-import', ('retrieved_at',))
    assert len(by_path) == 8


def test_a_second_acquire_asks_only_for_the_missing_kind(tmp_path, monkeypatch):
    refuse_industry_workbook(monkeypatch, tmp_path / 'served')
    data_dir = tmp_path / 'data'
    with pytest.raises(ValueError):
        module.acquire(data_dir, 'refs')
    calls = serve(monkeypatch, tmp_path / 'served2')
    final = module.acquire(data_dir, 'refs')
    assert [str(call.url) for call in calls] == [REFUSED_URL]
    assert module.check_references(data_dir, 'refs')['reference_id'] == 'refs'
    assert final.is_dir()


def test_every_refused_kind_is_named_after_all_are_tried(tmp_path, monkeypatch):
    calls = serve(monkeypatch, tmp_path / 'served', overrides={
        item.url: (lambda request: httpx.Response(403))
        for kind, item in module.REGISTRY.items() if kind in BLS_ANCHORS})
    with pytest.raises(ValueError, match='refused') as raised:
        module.acquire(tmp_path / 'data', 'refs')
    assert all(kind in str(raised.value) for kind in BLS_ANCHORS)
    assert len(calls) == 7


@pytest.mark.parametrize('name', ['oversize', 'short', 'long', 'redirect', 'server error',
                                  'drifted label'])
def test_a_bad_response_refuses_only_its_kind_and_removes_its_partial(
        tmp_path, monkeypatch, name):
    body = reference_originals(tmp_path / 'probe')[REFUSED_KIND].read_bytes()
    bad = bls_workbook(tmp_path / 'bad.xlsx', '9890', 'Part of 92811',
                       label='Military (last job)').read_bytes()
    responses = {
        'oversize': lambda request: ok(body * 2),
        'short': lambda request: ok(body, **{'content-length': str(len(body) + 1)}),
        'long': lambda request: ok(body, **{'content-length': str(len(body) - 1)}),
        'redirect': lambda request: httpx.Response(302, headers={'location': 'https://x.test/'}),
        'server error': lambda request: httpx.Response(500),
        'drifted label': lambda request: ok(bad),
    }
    if name == 'oversize':
        monkeypatch.setattr(module, 'MAX_ORIGINAL_BYTES', len(body) + 1)
    serve(monkeypatch, tmp_path / 'served', overrides={REFUSED_URL: responses[name]})
    with pytest.raises(ValueError, match=REFUSED_KIND):
        module.acquire(tmp_path / 'data', 'refs')
    staging = tmp_path / 'data/raw/references/cps-job-flows/refs.part'
    assert not (staging / module.REGISTRY[REFUSED_KIND].filename).exists()
    assert len(list(staging.iterdir())) == 7  # six originals and the state file


def test_content_length_is_not_compared_for_an_encoded_response(tmp_path, monkeypatch):
    body = reference_originals(tmp_path / 'probe')[REFUSED_KIND].read_bytes()
    serve(monkeypatch, tmp_path / 'served', overrides={REFUSED_URL: lambda request: ok(
        body, **{'content-length': str(len(body) + 5), 'content-encoding': 'identity'})})
    final = module.acquire(tmp_path / 'data', 'refs')
    assert (final / module.REGISTRY[REFUSED_KIND].filename).read_bytes() == body


def test_import_of_a_staged_kind_and_an_occupied_final_fail(tmp_path):
    data_dir = tmp_path / 'data'
    originals = reference_originals(tmp_path / 'originals')
    first = KINDS[0]
    staging = module.import_reference(data_dir, 'refs', first, originals[first])
    assert staging == data_dir / 'raw/references/cps-job-flows/refs.part'
    with pytest.raises(ValueError, match='already staged'):
        module.import_reference(data_dir, 'refs', first, originals[first])
    for kind in KINDS[1:]:
        result = module.import_reference(data_dir, 'refs', kind, originals[kind])
    assert result == data_dir / 'raw/references/cps-job-flows/refs'
    with pytest.raises(ValueError, match='immutable'):
        module.import_reference(data_dir, 'refs', first, originals[first])


def test_an_occupied_part_without_state_is_refused(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    (data_dir / 'raw/references/cps-job-flows/refs.part').mkdir(parents=True)
    with pytest.raises(ValueError, match='no staging state'):
        module.acquire(data_dir, 'refs')
    originals = reference_originals(tmp_path / 'originals')
    with pytest.raises(ValueError, match='no staging state'):
        module.import_reference(data_dir, 'refs', KINDS[0], originals[KINDS[0]])


def test_a_changed_staged_original_stops_a_resume(tmp_path, monkeypatch):
    refuse_industry_workbook(monkeypatch, tmp_path / 'served')
    data_dir = tmp_path / 'data'
    with pytest.raises(ValueError):
        module.acquire(data_dir, 'refs')
    staged = data_dir / 'raw/references/cps-job-flows/refs.part' / 'cps_industry_codes.csv'
    staged.write_text(staged.read_text(encoding='utf-8-sig') + ' ', encoding='utf-8-sig')
    with pytest.raises(ValueError, match='changed'):
        module.acquire(data_dir, 'refs')
    originals = reference_originals(tmp_path / 'browser')
    with pytest.raises(ValueError, match='changed'):
        module.import_reference(data_dir, 'refs', REFUSED_KIND, originals[REFUSED_KIND])


def test_staging_with_an_extra_file_or_foreign_state_is_refused(tmp_path, monkeypatch):
    refuse_industry_workbook(monkeypatch, tmp_path / 'served')
    data_dir = tmp_path / 'data'
    with pytest.raises(ValueError):
        module.acquire(data_dir, 'refs')
    staging = data_dir / 'raw/references/cps-job-flows/refs.part'
    (staging / 'stray.txt').write_text('x')
    with pytest.raises(ValueError, match='unmanifested'):
        module.acquire(data_dir, 'refs')
    (staging / 'stray.txt').unlink()
    state_file = staging / 'staging-state.json'
    state = json.loads(state_file.read_text())
    state['parser_version'] = 'other'
    state_file.write_text(json.dumps(state))
    with pytest.raises(ValueError, match='identity'):
        module.acquire(data_dir, 'refs')


def test_import_refuses_bad_sources_before_staging_anything(tmp_path):
    data_dir = tmp_path / 'data'
    originals = reference_originals(tmp_path / 'originals')
    kind = KINDS[0]
    with pytest.raises(ValueError, match='unknown'):
        module.import_reference(data_dir, 'refs', 'other_kind', originals[kind])
    with pytest.raises(ValueError, match='missing'):
        module.import_reference(data_dir, 'refs', kind, tmp_path / 'absent.csv')
    link = tmp_path / 'link.csv'
    link.symlink_to(originals[kind])
    with pytest.raises(ValueError, match='symlink'):
        module.import_reference(data_dir, 'refs', kind, link)
    industry_csv(tmp_path / 'drift.csv', label='Military')
    with pytest.raises(ValueError, match='special'):
        module.import_reference(data_dir, 'refs', kind, tmp_path / 'drift.csv')
    assert not (data_dir / 'raw/references').exists()


def test_import_refuses_an_oversize_source(tmp_path, monkeypatch):
    originals = reference_originals(tmp_path / 'originals')
    monkeypatch.setattr(module, 'MAX_ORIGINAL_BYTES', 10)
    with pytest.raises(ValueError, match='size bound'):
        module.import_reference(tmp_path / 'data', 'refs', KINDS[0], originals[KINDS[0]])


@pytest.mark.parametrize('reference_id', ['../refs', 'a/b', '.hidden', '', 'a b', '_refs',
                                          '-refs'])
def test_unsafe_reference_ids_are_refused(tmp_path, reference_id):
    originals = reference_originals(tmp_path / 'originals')
    with pytest.raises(ValueError, match='unsafe'):
        module.import_reference(tmp_path / 'data', reference_id, KINDS[0], originals[KINDS[0]])
    with pytest.raises(ValueError, match='unsafe'):
        module.acquire(tmp_path / 'data', reference_id)
    with pytest.raises(ValueError, match='unsafe'):
        module.check_references(tmp_path / 'data', reference_id)


def test_a_recorded_snapshot_path_needs_a_fresh_id(tmp_path):
    data_dir = tmp_path / 'data'
    originals = reference_originals(tmp_path / 'originals')
    manifest.append_entries(paths.manifest_path(data_dir), [manifest.ManifestEntry(
        path='references/cps-job-flows/refs/cps_industry_codes.csv', sha256='0' * 64, size=1,
        retrieved_at='2026-11-23T00:00:00+00:00', client='x', client_version='1')])
    with pytest.raises(ValueError, match='fresh reference ID'):
        module.import_reference(data_dir, 'refs', KINDS[0], originals[KINDS[0]])
    with pytest.raises(ValueError, match='fresh reference ID'):
        module.acquire(data_dir, 'refs')


def test_a_changed_manifest_entry_directory_or_receipt_fails_the_check(tmp_path):
    final = published(tmp_path)
    data_dir = tmp_path / 'data'
    receipt = module.check_references(data_dir, 'refs')
    assert receipt['originals'][KINDS[0]]['retrieved_at_is_proxy'] is True
    assert not final.with_name('refs.part').exists()
    (final / 'extra.txt').write_text('unmanifested')
    with pytest.raises(ValueError, match='inventory'):
        module.check_references(data_dir, 'refs')
    (final / 'extra.txt').unlink()
    (final.with_name('refs.part')).mkdir()
    with pytest.raises(ValueError, match='incomplete or occupied'):
        module.check_references(data_dir, 'refs')
    final.with_name('refs.part').rmdir()
    stored = (final / 'receipt.json').read_text()
    (final / 'receipt.json').write_text(stored.replace('"refs"', '"other"', 1))
    with pytest.raises(ValueError):
        module.check_references(data_dir, 'refs')
    (final / 'receipt.json').write_text(stored)
    assert module.check_references(data_dir, 'refs') == receipt
    paths.manifest_path(data_dir).write_text('')
    with pytest.raises(KeyError):
        module.check_references(data_dir, 'refs')


def test_changed_original_fails_check_and_needs_a_fresh_id(tmp_path, monkeypatch):
    serve(monkeypatch, tmp_path / 'served')
    data_dir = tmp_path / 'data'
    final = module.acquire(data_dir, 'refs')
    original = final / 'ind_2020_codes.shtml'
    body = bytearray(original.read_bytes())
    body[-1] ^= 1
    original.write_bytes(bytes(body))
    with pytest.raises(ValueError):
        module.check_references(data_dir, 'refs')
    with pytest.raises(ValueError):
        module.acquire(data_dir, 'refs')
    with pytest.raises(ValueError, match='immutable'):
        module.import_reference(data_dir, 'refs', 'ipums_cps_ind_2020_codes',
                                reference_originals(tmp_path / 'again')[
                                    'ipums_cps_ind_2020_codes'])


def test_a_symlinked_original_fails_the_check(tmp_path):
    final = published(tmp_path)
    target = tmp_path / 'outside.csv'
    target.write_bytes((final / 'cps_industry_codes.csv').read_bytes())
    (final / 'cps_industry_codes.csv').unlink()
    (final / 'cps_industry_codes.csv').symlink_to(target)
    with pytest.raises(ValueError, match='symlink'):
        module.check_references(tmp_path / 'data', 'refs')


def test_special_evidence_statuses(tmp_path):
    published(tmp_path)
    receipt = module.check_references(tmp_path / 'data', 'refs')
    evidence = module.special_evidence(receipt)
    assert set(evidence) == {'9890', '9840'}
    assert evidence['9840'] == {
        'label': 'Armed Forces', 'monthly': 'settled', 'asec_current': 'settled',
        'asec_last_year': 'settled', 'bls': '55-0000'}
    assert evidence['9890'] == {
        'label': 'Armed Forces', 'monthly': 'settled',
        'asec_current': 'unresolved_owner_decision',
        'asec_last_year': 'unresolved_owner_decision', 'bls': 'pt. 92811'}
    evidence['9840']['monthly'] = 'changed'
    assert module.special_evidence(receipt)['9840']['monthly'] == 'settled'


@pytest.mark.parametrize('mutation', ['parser_version', 'missing_kind'])
def test_special_evidence_needs_a_current_complete_receipt(tmp_path, mutation):
    published(tmp_path)
    receipt = module.check_references(tmp_path / 'data', 'refs')
    if mutation == 'parser_version':
        receipt['parser_version'] = 'old'
    else:
        receipt['originals'].pop('bls_cps_industry_2022')
    with pytest.raises(ValueError, match='receipt'):
        module.special_evidence(receipt)


@pytest.mark.parametrize('status', [301, 403, 404, 500])
def test_a_non_success_status_with_a_valid_body_is_still_refused(tmp_path, monkeypatch, status):
    body = reference_originals(tmp_path / 'probe')[REFUSED_KIND].read_bytes()
    serve(monkeypatch, tmp_path / 'served', overrides={REFUSED_URL: lambda request: (
        httpx.Response(status, headers={'content-length': str(len(body))},
                       stream=httpx.ByteStream(body)))})
    with pytest.raises(ValueError, match=REFUSED_KIND):
        module.acquire(tmp_path / 'data', 'refs')
    assert not manifest_entries(tmp_path)


def test_the_download_bound_holds_for_a_declared_and_for_an_undeclared_size(
        tmp_path, monkeypatch):
    body = reference_originals(tmp_path / 'probe')[REFUSED_KIND].read_bytes()
    monkeypatch.setattr(module, 'MAX_ORIGINAL_BYTES', len(body) - 1)
    declared = ok(body, **{'content-encoding': 'identity'})
    undeclared = httpx.Response(200, stream=httpx.ByteStream(body))
    for response in (declared, undeclared):
        serve(monkeypatch, tmp_path / 'served',
              overrides={REFUSED_URL: lambda request, response=response: response})
        with pytest.raises(ValueError, match=REFUSED_KIND):
            module.acquire(tmp_path / 'data', 'refs')
        shutil.rmtree(tmp_path / 'data')


def test_an_oversize_header_alone_refuses_before_any_byte_is_kept(tmp_path, monkeypatch):
    body = reference_originals(tmp_path / 'probe')[REFUSED_KIND].read_bytes()
    monkeypatch.setattr(module, 'MAX_ORIGINAL_BYTES', len(body) + 100)
    huge = ok(body, **{'content-length': str(len(body) + 101), 'content-encoding': 'identity'})
    serve(monkeypatch, tmp_path / 'served', overrides={REFUSED_URL: lambda request: huge})
    with pytest.raises(ValueError, match=REFUSED_KIND):
        module.acquire(tmp_path / 'data', 'refs')


def test_an_import_source_below_a_symlinked_directory_is_refused(tmp_path):
    originals = reference_originals(tmp_path / 'real')
    (tmp_path / 'alias').symlink_to(tmp_path / 'real', target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        module.import_reference(tmp_path / 'data', 'refs', KINDS[0],
                                tmp_path / 'alias' / originals[KINDS[0]].name)


@pytest.mark.parametrize('change', ['client', 'proxies', 'source_url'])
def test_the_receipt_manifest_entry_must_be_generated_provenance(tmp_path, change):
    published(tmp_path)
    manifest_file = paths.manifest_path(tmp_path / 'data')
    lines = manifest_file.read_text().splitlines()
    record = json.loads(lines[-1])
    assert record['path'].endswith('/receipt.json')
    if change == 'client':
        record['client'] = 'manual-import'
    elif change == 'proxies':
        record['proxies'] = ['retrieved_at']
    else:
        record['source_url'] = 'https://example.test/'
    lines[-1] = json.dumps(record)
    manifest_file.write_text('\n'.join(lines) + '\n')
    with pytest.raises(ValueError, match='receipt provenance'):
        module.check_references(tmp_path / 'data', 'refs')


def refused_staging(tmp_path, monkeypatch):
    refuse_industry_workbook(monkeypatch, tmp_path / 'served')
    data_dir = tmp_path / 'data'
    with pytest.raises(ValueError):
        module.acquire(data_dir, 'refs')
    return data_dir, data_dir / 'raw/references/cps-job-flows/refs.part' / 'staging-state.json'


def test_staging_state_with_an_unregistered_kind_is_refused(tmp_path, monkeypatch):
    data_dir, state_file = refused_staging(tmp_path, monkeypatch)
    state = json.loads(state_file.read_text())
    state['kinds']['cps_basic_2027_codes'] = state['kinds'][KINDS[0]]
    state_file.write_text(json.dumps(state))
    calls = serve(monkeypatch, tmp_path / 'served2')
    with pytest.raises(ValueError, match='unknown identity'):
        module.acquire(data_dir, 'refs')
    assert calls == []


@pytest.mark.parametrize('change', ['naive time', 'invalid time', 'proxy not boolean',
                                    'other url', 'other method'])
def test_staging_request_records_must_be_exact(tmp_path, monkeypatch, change):
    data_dir, state_file = refused_staging(tmp_path, monkeypatch)
    state = json.loads(state_file.read_text())
    request = state['kinds'][KINDS[0]]['request']
    request.update({
        'naive time': {'retrieved_at': '2026-11-23T00:00:00'},
        'invalid time': {'retrieved_at': 'yesterday'},
        'proxy not boolean': {'retrieved_at_is_proxy': 'no'},
        'other url': {'source_url': 'https://example.test/'},
        'other method': {'method': 'POST'},
    }[change])
    state_file.write_text(json.dumps(state))
    calls = serve(monkeypatch, tmp_path / 'served2')
    with pytest.raises(ValueError):
        module.acquire(data_dir, 'refs')
    assert calls == []  # the staged records are refused before any request is made


def test_a_publication_copy_that_differs_from_staging_is_refused(tmp_path, monkeypatch):
    originals = reference_originals(tmp_path / 'originals')
    for kind in KINDS[:-1]:
        module.import_reference(tmp_path / 'data', 'refs', kind, originals[kind])

    def truncated(source, output):
        output.write(source.read()[:-1])

    monkeypatch.setattr(module.shutil, 'copyfileobj', truncated)
    with pytest.raises(ValueError, match='changed during publication'):
        module.import_reference(tmp_path / 'data', 'refs', KINDS[-1], originals[KINDS[-1]])
    assert not manifest_entries(tmp_path)


def test_a_transport_error_refuses_only_its_kind(tmp_path, monkeypatch):
    def broken(request):
        raise httpx.ConnectError('unreachable', request=request)

    serve(monkeypatch, tmp_path / 'served', overrides={REFUSED_URL: broken})
    with pytest.raises(ValueError, match=REFUSED_KIND):
        module.acquire(tmp_path / 'data', 'refs')
    staging = tmp_path / 'data/raw/references/cps-job-flows/refs.part'
    assert len(list(staging.iterdir())) == 7  # six originals and the state file


def test_a_filesystem_error_is_not_a_refusal(tmp_path, monkeypatch):
    serve(monkeypatch, tmp_path / 'served')

    def disk_full(client, reference, file):
        raise OSError('disk full')

    monkeypatch.setattr(module, '_download', disk_full)
    with pytest.raises(OSError, match='disk full'):
        module.acquire(tmp_path / 'data', 'refs')
