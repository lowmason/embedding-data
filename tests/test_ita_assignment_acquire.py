import json

import httpx
import polars as pl
import pytest
from target_fixtures import census_client, prepared_tree

from embedding_data import manifest, paths

@pytest.fixture(autouse=True)
def implemented_software_boundary(monkeypatch):
    from target_fixtures import install_implemented_software_boundary

    install_implemented_software_boundary(monkeypatch)


def setup_acquisition(tmp_path, monkeypatch, *, fail_batch=None):
    from embedding_data import ita_assignment_acquire as acquisition

    prepared = prepared_tree(tmp_path, batch_limit=3)
    calls = []
    monkeypatch.setattr(acquisition, 'make_client',
                        lambda: census_client(calls, fail_batch=fail_batch))
    raw = tmp_path / 'raw/references/census-geocoder/ita-assignment/requests'
    return acquisition, prepared, raw, calls


def test_sequential_resume_preserves_first_receipt(tmp_path, monkeypatch):
    acquisition, prepared, raw, calls = setup_acquisition(tmp_path, monkeypatch, fail_batch=1)
    with pytest.raises(httpx.TransportError):
        acquisition.acquire(tmp_path, 'requests')
    receipts = sorted(raw.glob('*.receipt.json'))
    assert len(receipts) == 1
    original = receipts[0].read_bytes()
    monkeypatch.setattr(acquisition, 'make_client', lambda: census_client(calls))
    completion = acquisition.acquire(tmp_path, 'requests')
    assert completion.exists()
    assert receipts[0].read_bytes() == original
    posts = [c for c in calls if c['method'] == 'POST']
    assert all(c['benchmark'] == '7' and c['vintage'] == '999' for c in posts)
    assert sum(c['request_sha256'] == posts[0]['request_sha256'] for c in posts) == 1
    assert len([c for c in calls if c['method'] == 'GET']) == 2
    monkeypatch.setattr(acquisition, 'make_client', lambda: pytest.fail('opened client'))
    original_completion = completion.read_bytes()
    assert acquisition.acquire(tmp_path, 'requests') == completion
    assert completion.read_bytes() == original_completion
    evidence = acquisition.read_evidence(tmp_path, prepared)
    evidence.verify()
    responses = evidence.responses.collect()
    assert responses.height == pl.read_parquet(prepared.request_index).height
    assert responses.schema == dict.fromkeys(
        ['request_id', 'geocode_status', 'match_type', 'geocode_county_geoid'], pl.String)
    assert responses['request_id'].null_count() == 0
    assert responses['request_id'].n_unique() == responses.height
    assert 'No_Match' in responses['geocode_status']
    assert evidence.provenance['options']['benchmark_id'] == '7'


@pytest.mark.parametrize('body', [
    'wrong,"",No_Match\n', 'one,"",No_Match\none,"",No_Match\n',
    'one,"",Match,Exact\n', 'one,"",Unknown\n', ',"",No_Match\n', '',
    'one,"",No_Match\nextra,"",No_Match\n',
])
def test_response_defects_fail_instead_of_becoming_unmatched(body):
    from embedding_data.ita_assignment_acquire import parse_response

    with pytest.raises(ValueError):
        parse_response(body, ['one'])


def test_tie_and_unmatched_states_are_retained():
    from embedding_data.ita_assignment_acquire import parse_response

    frame = parse_response('a,"",Tie\nb,"",No_Match\n', ['a', 'b'])
    assert frame['geocode_status'].to_list() == ['Tie', 'No_Match']
    assert frame['geocode_county_geoid'].null_count() == 2
    with pytest.raises(ValueError):
        parse_response('a,"",Tie\n', ['a', 'a'])


@pytest.mark.parametrize('catalog', [
    {}, {'benchmarks': []}, {'benchmarks': [None]},
    {'benchmarks': [{'benchmarkName': 'Public_AR_Current', 'id': ''}]},
    {'benchmarks': [{'benchmarkName': 'Public_AR_Current', 'id': True}]},
    {'benchmarks': [{'benchmarkName': 'Public_AR_Current', 'id': []}]},
    {'benchmarks': [{'benchmarkName': 'Public_AR_Current', 'id': 7}] * 2},
])
def test_bad_benchmark_stops_before_vintages(tmp_path, monkeypatch, catalog):
    acquisition, _, raw, calls = setup_acquisition(tmp_path, monkeypatch)

    def serve(request):
        calls.append(request.url.path)
        return httpx.Response(200, json=catalog)

    monkeypatch.setattr(acquisition, 'make_client',
                        lambda: httpx.Client(transport=httpx.MockTransport(serve)))
    with pytest.raises(ValueError, match='requests'):
        acquisition.acquire(tmp_path, 'requests')
    assert len(calls) == 1
    assert not list(raw.glob('*.csv'))


@pytest.mark.parametrize('vintages', [[], [None], [{'vintageName': 'wrong', 'id': 1}],
    [{'vintageName': 'ACS2025_Current', 'id': 999}] * 2])
def test_invalid_vintage_selection(vintages):
    from embedding_data.ita_assignment_acquire import choose_options

    with pytest.raises(ValueError):
        choose_options({'benchmarks': [{'benchmarkName': 'Public_AR_Current', 'id': 7}]},
                       {'vintages': vintages})


@pytest.mark.parametrize('defect', [
    'response_hash', 'response_size', 'response_missing', 'receipt_missing',
    'receipt_hash', 'selection_hash', 'catalog_hash', 'request_hash', 'software',
    'start_hash', 'start_missing',
    'partial', 'unrecorded', 'completion_missing',
])
def test_offline_tampering_fails_before_client(tmp_path, monkeypatch, defect):
    acquisition, prepared, raw, _ = setup_acquisition(tmp_path, monkeypatch)
    acquisition.acquire(tmp_path, 'requests')
    evidence = acquisition.read_evidence(tmp_path, prepared)
    response = next(raw.glob('*.csv'))
    receipt = next(raw.glob('*.receipt.json'))
    if defect.endswith('_hash'):
        file = {'response_hash': response, 'receipt_hash': receipt,
                'selection_hash': raw / 'catalog-selection.json',
                'catalog_hash': raw / 'benchmarks.json', 'request_hash': prepared.batches[0],
                'start_hash': raw / 'acquisition-start.json'
                }[defect]
        file.write_bytes(file.read_bytes() + b' ')
    elif defect == 'response_size':
        ledger = paths.manifest_path(tmp_path)
        records = [json.loads(line) for line in ledger.read_text().splitlines()]
        for item in records:
            if item['path'].endswith(response.name):
                item['size'] += 1
        ledger.write_text(''.join(json.dumps(item) + '\n' for item in records))
    elif defect.endswith('_missing'):
        {'response_missing': response, 'receipt_missing': receipt,
         'completion_missing': raw / 'acquisition.json',
         'start_missing': raw / 'acquisition-start.json'}[defect].unlink()
    elif defect == 'partial':
        (raw / 'interrupted.csv.part').write_bytes(b'partial')
    elif defect == 'unrecorded':
        (raw / 'unexpected.csv').write_bytes(b'unrecorded')
    elif defect == 'software':
        from embedding_data import ita_assignment_prepare as preparation
        monkeypatch.setattr(preparation, 'software_contract', lambda: {})
    monkeypatch.setattr(acquisition, 'make_client', lambda: pytest.fail('opened client'))
    with pytest.raises(ValueError):
        acquisition.acquire(tmp_path, 'requests')
    with pytest.raises(ValueError):
        acquisition.read_evidence(tmp_path, prepared)
    with pytest.raises(ValueError):
        evidence.verify()


@pytest.mark.parametrize('crash', ['before_receipt', 'response_unrecorded', 'receipt_unrecorded'])
def test_publication_crash_windows(tmp_path, monkeypatch, crash):
    acquisition, prepared, raw, calls = setup_acquisition(tmp_path, monkeypatch)
    original_record = acquisition.record_download
    original_append = manifest.append_entries

    def record(file_manifest, destination, url, **kwargs):
        if destination.suffix == '.csv' and crash == 'response_unrecorded':
            raise RuntimeError('crash before response recording')
        return original_record(file_manifest, destination, url, **kwargs)

    def append(file_manifest, entries):
        entries = list(entries)
        if any(e.path.endswith('.receipt.json') for e in entries):
            raise RuntimeError('crash before receipt recording')
        return original_append(file_manifest, entries)

    monkeypatch.setattr(acquisition, 'record_download', record)
    if crash == 'before_receipt':
        original_receipt = acquisition.batch_receipt
        monkeypatch.setattr(acquisition, 'batch_receipt',
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError('crash')))
    if crash == 'receipt_unrecorded':
        monkeypatch.setattr(manifest, 'append_entries', append)
    with pytest.raises(RuntimeError):
        acquisition.acquire(tmp_path, 'requests')
    response = next(raw.glob('*.csv'))
    original_bytes = response.read_bytes()
    monkeypatch.setattr(acquisition, 'record_download', original_record)
    monkeypatch.setattr(manifest, 'append_entries', original_append)
    if crash == 'before_receipt':
        monkeypatch.setattr(acquisition, 'batch_receipt', original_receipt)
        entry = manifest.entry_for(paths.manifest_path(tmp_path), response)
        acquisition.acquire(tmp_path, 'requests')
        receipt = json.loads(response.with_suffix('.receipt.json').read_text())
        assert receipt['acquired_at'] == entry.retrieved_at
        assert response.read_bytes() == original_bytes
        acquisition.read_evidence(tmp_path, prepared).verify()
    else:
        monkeypatch.setattr(acquisition, 'make_client', lambda: pytest.fail('opened client'))
        with pytest.raises(ValueError, match='requests'):
            acquisition.acquire(tmp_path, 'requests')
    assert not any(c['method'] == 'GET' for c in calls[3:])


def test_missing_completion_is_not_offline_evidence(tmp_path, monkeypatch):
    acquisition, prepared, _, _ = setup_acquisition(tmp_path, monkeypatch, fail_batch=1)
    with pytest.raises(httpx.TransportError):
        acquisition.acquire(tmp_path, 'requests')
    monkeypatch.setattr(acquisition, 'make_client', lambda: pytest.fail('opened client'))
    with pytest.raises(ValueError, match='acquisition.json'):
        acquisition.read_evidence(tmp_path, prepared)


@pytest.mark.parametrize('defect', ['bad_ids', 'short_body', 'interrupted'])
def test_invalid_batch_stops_without_publication(tmp_path, monkeypatch, defect):
    acquisition, _, raw, calls = setup_acquisition(tmp_path, monkeypatch)
    base = census_client(calls)

    class Interrupted(httpx.SyncByteStream):
        def __iter__(self):
            yield b'incomplete'
            raise httpx.ReadError('fixture interruption')

    def serve(request):
        if request.method != 'POST':
            return base.send(request)
        calls.append({'method': 'POST'})
        if defect == 'interrupted':
            return httpx.Response(200, stream=Interrupted())
        return httpx.Response(200, headers={'Content-Length': '999' if defect == 'short_body'
                                           else '13'}, stream=httpx.ByteStream(b'x,"",No_Match\n'))

    monkeypatch.setattr(acquisition, 'make_client',
                        lambda: httpx.Client(transport=httpx.MockTransport(serve)))
    with pytest.raises((ValueError, httpx.TransportError)):
        acquisition.acquire(tmp_path, 'requests')
    assert sum(c['method'] == 'POST' for c in calls) == 1
    assert not list(raw.glob('*.csv'))
    assert not list(raw.glob('*.receipt.json'))
    assert not (raw / 'acquisition.json').exists()


def test_acquisition_start_survives_catalog_failure(tmp_path, monkeypatch):
    from datetime import UTC, datetime, timedelta

    acquisition, _, raw, calls = setup_acquisition(tmp_path, monkeypatch)
    start = datetime(2026, 10, 14, tzinfo=UTC)

    class Clock(datetime):
        @staticmethod
        def now(tz):
            return start

    monkeypatch.setattr(acquisition, 'datetime', Clock)
    base = census_client(calls)

    def serve(request):
        if request.url.path.endswith('/vintages'):
            raise httpx.ReadError('catalog interrupted')
        return base.send(request)

    monkeypatch.setattr(acquisition, 'make_client',
                        lambda: httpx.Client(transport=httpx.MockTransport(serve)))
    with pytest.raises(httpx.TransportError):
        acquisition.acquire(tmp_path, 'requests')
    start += timedelta(days=1)
    monkeypatch.setattr(acquisition, 'datetime', datetime)
    monkeypatch.setattr(acquisition, 'make_client', lambda: census_client(calls))
    acquisition.acquire(tmp_path, 'requests')
    selection = json.loads((raw / 'catalog-selection.json').read_text())
    assert selection['acquisition_started_at'] == '2026-10-14T00:00:00+00:00'


def test_transport_error_names_batch_without_submitted_strings(tmp_path, monkeypatch):
    acquisition, _, _, _ = setup_acquisition(tmp_path, monkeypatch, fail_batch=0)
    with pytest.raises(httpx.TransportError, match='ita-assignment/requests/') as error:
        acquisition.acquire(tmp_path, 'requests')
    assert 'Exact A' not in str(error.value)


def test_unrelated_manifest_append_preserves_evidence(tmp_path, monkeypatch):
    acquisition, prepared, _, _ = setup_acquisition(tmp_path, monkeypatch)
    acquisition.acquire(tmp_path, 'requests')
    evidence = acquisition.read_evidence(tmp_path, prepared)
    # A manifested reference outside this run does not change its citations.
    from datetime import UTC, datetime

    extra = tmp_path / 'raw/unrelated.txt'
    extra.write_bytes(b'unrelated')
    manifest.append_entries(paths.manifest_path(tmp_path), [manifest.describe_file(
        extra, tmp_path / 'raw', retrieved_at=datetime.now(UTC),
        client='fixture', client_version='1')])
    monkeypatch.setattr(acquisition, 'make_client', lambda: pytest.fail('opened client'))
    evidence.verify()
    acquisition.acquire(tmp_path, 'requests')


@pytest.mark.parametrize('kind', ['selection', 'receipt', 'completion'])
def test_repinned_metadata_semantic_tampering(tmp_path, monkeypatch, kind):
    acquisition, prepared, raw, _ = setup_acquisition(tmp_path, monkeypatch)
    acquisition.acquire(tmp_path, 'requests')
    file = {'selection': raw / 'catalog-selection.json', 'completion': raw / 'acquisition.json',
            'receipt': next(raw.glob('*.receipt.json'))}[kind]
    content = json.loads(file.read_text())
    content['options']['benchmark_id'] = '4'
    file.write_text(json.dumps(content))
    ledger = paths.manifest_path(tmp_path)
    records = [json.loads(line) for line in ledger.read_text().splitlines()]
    for item in records:
        if item['path'] == file.relative_to(tmp_path / 'raw').as_posix():
            item.update(sha256=manifest.sha256_file(file), size=file.stat().st_size)
    ledger.write_text(''.join(json.dumps(item) + '\n' for item in records))
    monkeypatch.setattr(acquisition, 'make_client', lambda: pytest.fail('opened client'))
    with pytest.raises(ValueError):
        acquisition.acquire(tmp_path, 'requests')
    with pytest.raises(ValueError):
        acquisition.read_evidence(tmp_path, prepared)


def test_compressed_transport_length_measures_wire_bytes(tmp_path, monkeypatch):
    import gzip

    acquisition, prepared, _, calls = setup_acquisition(tmp_path, monkeypatch)
    base = census_client(calls)

    def serve(request):
        response = base.send(request)
        if request.method == 'GET':
            return response
        body = gzip.compress(response.read())
        return httpx.Response(200, headers={'Content-Encoding': 'gzip',
                                          'Content-Length': str(len(body))},
                              stream=httpx.ByteStream(body))

    monkeypatch.setattr(acquisition, 'make_client',
                        lambda: httpx.Client(transport=httpx.MockTransport(serve)))
    acquisition.acquire(tmp_path, 'requests')
    acquisition.read_evidence(tmp_path, prepared).verify()


def test_preparation_failure_identifies_run(tmp_path, monkeypatch):
    from embedding_data import ita_assignment_prepare as preparation

    acquisition, prepared, _, _ = setup_acquisition(tmp_path, monkeypatch)
    monkeypatch.setattr(preparation, 'software_contract', lambda: {})
    monkeypatch.setattr(acquisition, 'make_client', lambda: pytest.fail('opened client'))
    with pytest.raises(ValueError, match='requests'):
        acquisition.acquire(tmp_path, 'requests')
    with pytest.raises(ValueError, match='requests'):
        acquisition.read_evidence(tmp_path, prepared)


def test_http_status_failure_identifies_batch(tmp_path, monkeypatch):
    acquisition, _, _, calls = setup_acquisition(tmp_path, monkeypatch)
    base = census_client(calls)

    def serve(request):
        if request.method == 'POST':
            return httpx.Response(503, stream=httpx.ByteStream(b'unavailable'))
        return base.send(request)

    monkeypatch.setattr(acquisition, 'make_client',
                        lambda: httpx.Client(transport=httpx.MockTransport(serve)))
    with pytest.raises(httpx.HTTPStatusError, match='ita-assignment/requests/'):
        acquisition.acquire(tmp_path, 'requests')
