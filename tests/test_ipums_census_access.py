'''Fixture-only checks of the acquisition-only Census credential boundary.'''

import importlib
import json
import logging
import os
import traceback
from urllib.parse import quote

import httpx
import pytest
from ipums_fixtures import SAMPLE_CATALOG, bls_response

from embedding_data import ipums_references as references

SENTINEL = 'fake-census-secret-$/+?&'
KINDS = ('acs_2023_employment', 'acs_2024_employment')
BODY = b'{"transport_fixture":"opaque-public-response"}'


def access():
    return importlib.import_module('embedding_data.ipums_census_access')


@pytest.fixture(autouse=True)
def fake_environment(monkeypatch):
    monkeypatch.delenv('CENSUS_API_KEY', raising=False)


def install_transport(monkeypatch, handler):
    module = access()
    monkeypatch.setattr(module, 'make_client', lambda: httpx.Client(
        transport=httpx.MockTransport(handler), trust_env=False, follow_redirects=False))
    return module


def forbidden(*args, **kwargs):
    raise AssertionError('forbidden credential or network access')


def safe_failure(call):
    with pytest.raises(ValueError) as caught:
        call()
    formatted = ''.join(traceback.format_exception(caught.value))
    assert SENTINEL not in formatted
    assert quote(SENTINEL, safe='') not in formatted
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    return str(caught.value)


def test_two_originals_have_canonical_metadata_and_no_credentials(tmp_path, monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)
        assert request.url.params['key'] == SENTINEL
        return httpx.Response(200, content=BODY)

    module = install_transport(monkeypatch, handler)
    monkeypatch.setenv('CENSUS_API_KEY', SENTINEL)
    output = tmp_path / 'preflight'
    assert module.preflight(output) == output
    assert len(requests) == 2
    assert [request.url.path for request in requests] == [
        '/data/2023/acs/acs1', '/data/2024/acs/acs1']
    metadata = json.loads((output / 'metadata.json').read_text())
    assert set(metadata['originals']) == set(KINDS)
    for kind in KINDS:
        record = metadata['originals'][kind]
        assert record['source_url'] == references.REGISTRY[kind].url
        assert record['size_bytes'] == len(BODY)
        assert len(record['sha256']) == 64
        assert record['retrieved_at']
        assert (output / record['filename']).read_bytes() == BODY
    assert output.stat().st_mode & 0o777 == 0o700
    for file in output.iterdir():
        assert SENTINEL.encode() not in file.read_bytes()
    monkeypatch.setattr(module, 'read_credential', forbidden)
    with pytest.raises(ValueError, match='occupied'):
        module.preflight(output)
    assert len(requests) == 2


@pytest.mark.parametrize('kind,url', [
    ('usa_samples', references.REGISTRY['usa_samples'].url),
    ('cps_employment', references.REGISTRY['cps_employment'].url),
    ('acs_2023_b23025_metadata', references.REGISTRY['acs_2023_b23025_metadata'].url),
    (KINDS[0], 'http://api.census.gov/data/2023/acs/acs1'),
    (KINDS[0], references.REGISTRY[KINDS[1]].url),
    (KINDS[0], references.REGISTRY[KINDS[0]].url + '&key=other'),
])
def test_transport_refuses_unregistered_scope_before_client(monkeypatch, kind, url):
    module = access()
    monkeypatch.setattr(module, 'make_client', forbidden)
    safe_failure(lambda: module.fetch_original(kind, url, SENTINEL))


@pytest.mark.parametrize('failure', ['http', 'transport', 'redirect', 'echo', 'encoded_echo',
                                     'chunk_echo', 'too_large', 'length'])
def test_failures_suppress_debug_logs_traceback_and_secret_bytes(tmp_path, monkeypatch,
                                                                caplog, failure):
    requests = []

    def handler(request):
        requests.append(request)
        logging.getLogger('httpx').debug('request %s', request.url)
        logging.getLogger('httpcore.connection').debug('credentials %s', SENTINEL)
        if failure == 'transport':
            raise httpx.ConnectError(str(request.url), request=request)
        if failure == 'http':
            return httpx.Response(403, text=SENTINEL)
        if failure == 'redirect':
            return httpx.Response(302, headers={'location': 'https://other.test/' + SENTINEL})
        if failure in ('echo', 'chunk_echo'):
            return httpx.Response(200, stream=httpx.ByteStream(b'prefix' + SENTINEL.encode()))
        if failure == 'encoded_echo':
            return httpx.Response(200, text=quote(SENTINEL, safe=''))
        if failure == 'too_large':
            return httpx.Response(200, headers={'content-length': str(100_000_000)})
        return httpx.Response(200, content=BODY, headers={'content-length': '2'})

    module = install_transport(monkeypatch, handler)
    monkeypatch.setenv('CENSUS_API_KEY', SENTINEL)
    caplog.set_level(logging.DEBUG)
    previous = logging.root.manager.disable
    output = tmp_path / 'failed'
    safe_failure(lambda: module.preflight(output))
    assert logging.root.manager.disable == previous
    assert SENTINEL not in caplog.text
    assert quote(SENTINEL, safe='') not in caplog.text
    assert len(requests) == 1
    assert not list(output.glob('*.json'))


def test_missing_key_fails_before_full_acquire_staging_or_network(tmp_path, monkeypatch):
    module = access()
    monkeypatch.setattr(module, 'make_client', forbidden)
    monkeypatch.setattr(references, 'make_client', forbidden)
    with pytest.raises(ValueError, match='CENSUS_API_KEY'):
        references.acquire(tmp_path, 'missing')
    assert not (tmp_path / 'raw').exists()


def test_explicit_dotenv_is_literal_and_does_not_mutate_environment(tmp_path, monkeypatch):
    module = access()
    env_file = tmp_path / 'fake.env'
    env_file.write_text('CENSUS_API_KEY=${D3_TEST_EXPANSION}\nOTHER=fake-other\n')
    monkeypatch.setenv('D3_TEST_EXPANSION', 'expanded')
    before = dict(os.environ)
    assert module.read_credential(env_file=env_file) == '${D3_TEST_EXPANSION}'
    assert dict(os.environ) == before
    monkeypatch.setenv('CENSUS_API_KEY', SENTINEL)
    monkeypatch.setattr(module, 'dotenv_values', forbidden)
    assert module.read_credential(env_file=env_file) == SENTINEL


@pytest.mark.parametrize('credential', ['', '   ', 'bad\nvalue', 'bad\x00value'])
def test_invalid_key_is_sanitized(monkeypatch, credential):
    module = access()
    monkeypatch.setenv('CENSUS_API_KEY', credential.replace('\x00', '\r'))
    safe_failure(module.read_credential)


@pytest.mark.parametrize('cancel', [EOFError, KeyboardInterrupt])
def test_hidden_prompt_cancel_is_sanitized(monkeypatch, cancel):
    module = access()
    monkeypatch.setattr(module.sys.stdin, 'isatty', lambda: True)

    def cancelled(*args, **kwargs):
        raise cancel(SENTINEL)

    monkeypatch.setattr(module.getpass, 'getpass', cancelled)
    safe_failure(lambda: module.read_credential(prompt=True))


def test_prompt_requires_tty_and_success_uses_hidden_getpass(monkeypatch):
    module = access()
    monkeypatch.setattr(module.sys.stdin, 'isatty', lambda: False)
    monkeypatch.setattr(module.getpass, 'getpass', forbidden)
    safe_failure(lambda: module.read_credential(prompt=True))
    monkeypatch.setattr(module.sys.stdin, 'isatty', lambda: True)
    monkeypatch.setattr(module.getpass, 'getpass', lambda *args, **kwargs: SENTINEL)
    assert module.read_credential(prompt=True) == SENTINEL


def test_explicit_env_file_failures_are_sanitized(tmp_path, monkeypatch):
    module = access()

    def failure(*args, **kwargs):
        raise OSError(SENTINEL)

    monkeypatch.setattr(module, 'dotenv_values', failure)
    safe_failure(lambda: module.read_credential(env_file=tmp_path / 'fake.env'))


def test_cached_acquire_check_import_and_import_module_never_read_credentials(tmp_path,
                                                                           monkeypatch):
    module = access()
    monkeypatch.setattr(module, 'read_credential', forbidden)
    monkeypatch.setattr(module, 'dotenv_values', forbidden)
    monkeypatch.setattr(module, 'make_client', forbidden)
    monkeypatch.setattr(references, 'make_client', forbidden)
    monkeypatch.setattr(references, 'REGISTRY', {
        'usa_samples': references.REGISTRY['usa_samples']})
    original = tmp_path / 'catalog.html'
    original.write_text(SAMPLE_CATALOG)
    completed = references.import_reference(tmp_path, 'cached', 'usa_samples', original)
    assert references.acquire(tmp_path, 'cached', census_env_file=tmp_path / 'forbidden.env') == (
        completed)
    references.check_references(tmp_path, 'cached')
    import dotenv
    monkeypatch.setattr(dotenv, 'dotenv_values', forbidden)
    importlib.reload(references)
    importlib.reload(module)


def test_normal_acquire_scopes_key_and_canonical_request_record(tmp_path, monkeypatch):
    kinds = ['usa_samples', 'cps_employment', 'acs_2023_b23025_metadata', *KINDS]
    monkeypatch.setattr(references, 'REGISTRY', {
        kind: references.REGISTRY[kind] for kind in kinds})
    public_calls, census_calls = [], []

    def public(request):
        public_calls.append(request)
        assert 'key' not in request.url.params
        if request.method == 'POST':
            assert 'registrationkey' not in request.content.decode()
            return httpx.Response(200, json=bls_response())
        if '/groups/' in request.url.path:
            return httpx.Response(200, text=(
                '/data/2023/acs/acs1/groups/B23025 B23025_004E'))
        return httpx.Response(200, text=SAMPLE_CATALOG)

    def census(request):
        census_calls.append(request)
        assert request.url.params['key'] == SENTINEL
        return httpx.Response(200, content=BODY)

    monkeypatch.setattr(references, 'make_client', lambda: httpx.Client(
        transport=httpx.MockTransport(public)))
    install_transport(monkeypatch, census)
    monkeypatch.setenv('CENSUS_API_KEY', SENTINEL)
    # ACS validation intentionally stays blocked until actual originals are inspected.
    with pytest.raises(ValueError, match='preflight'):
        references.acquire(tmp_path, 'scoped')
    assert len(public_calls) == 3
    assert len(census_calls) == 1
    record = references._request_record(KINDS[0], '2026-10-15T00:00:00+00:00', imported=False)
    assert record['source_url'] == references.REGISTRY[KINDS[0]].url
    assert SENTINEL not in json.dumps(record)


def test_default_client_has_no_external_auth_hooks_proxies_or_redirects(monkeypatch):
    module = access()
    monkeypatch.setenv('HTTPS_PROXY', 'http://forbidden.test')
    with module.make_client() as client:
        assert client.trust_env is False
        assert client.follow_redirects is False
        assert not client.auth
        assert client.event_hooks == {'request': [], 'response': []}


def test_preflight_refuses_symlink_and_missing_key_without_output(tmp_path, monkeypatch):
    module = access()
    output = tmp_path / 'new'
    with pytest.raises(ValueError, match='CENSUS_API_KEY'):
        module.preflight(output)
    assert not output.exists()
    destination = tmp_path / 'destination'
    destination.mkdir()
    alias = tmp_path / 'alias'
    alias.symlink_to(destination, target_is_directory=True)
    monkeypatch.setattr(module, 'read_credential', forbidden)
    with pytest.raises(ValueError, match='symlink'):
        module.preflight(alias / 'new')


def test_cli_prints_only_safe_paths_and_hashes(tmp_path, monkeypatch, capsys):
    module = install_transport(monkeypatch, lambda _: httpx.Response(200, content=BODY))
    monkeypatch.setenv('CENSUS_API_KEY', SENTINEL)
    output = tmp_path / 'cli'
    assert module.main(['--output-dir', str(output)]) == 0
    result = capsys.readouterr()
    assert str(output) in result.out
    assert SENTINEL not in result.out + result.err
    monkeypatch.delenv('CENSUS_API_KEY')
    assert module.main(['--output-dir', str(tmp_path / 'missing')]) == 1
    result = capsys.readouterr()
    assert 'CENSUS_API_KEY' in result.err


def test_echo_split_across_chunks_is_rejected_before_write(tmp_path, monkeypatch):
    class Chunked(httpx.SyncByteStream):
        def __iter__(self):
            yield SENTINEL[:7].encode()
            yield SENTINEL[7:].encode()

    module = install_transport(monkeypatch, lambda _: httpx.Response(200, stream=Chunked()))
    monkeypatch.setenv('CENSUS_API_KEY', SENTINEL)
    output = tmp_path / 'split'
    safe_failure(lambda: module.preflight(output))
    assert not list(output.iterdir())


def test_stream_bound_without_content_length(tmp_path, monkeypatch):
    module = install_transport(monkeypatch, lambda _: httpx.Response(
        200, stream=httpx.ByteStream(BODY)))
    monkeypatch.setenv('CENSUS_API_KEY', SENTINEL)
    monkeypatch.setattr(module, 'MAX_ORIGINAL_BYTES', 4)
    output = tmp_path / 'bounded'
    safe_failure(lambda: module.preflight(output))
    assert not list(output.iterdir())


def test_getpass_echo_fallback_is_refused(monkeypatch):
    module = access()
    monkeypatch.setattr(module.sys.stdin, 'isatty', lambda: True)

    def fallback(*args, **kwargs):
        import warnings
        warnings.warn('echo fallback', module.getpass.GetPassWarning)
        raise AssertionError('echoed input must never be read')

    monkeypatch.setattr(module.getpass, 'getpass', fallback)
    safe_failure(lambda: module.read_credential(prompt=True))


def test_transport_close_failure_is_sanitized_and_logging_restored(monkeypatch, caplog):
    class FailingStream(httpx.SyncByteStream):
        def __iter__(self):
            yield BODY

        def close(self):
            logging.getLogger('httpcore.http11').debug('closing %s', SENTINEL)
            raise RuntimeError(SENTINEL)

    module = install_transport(monkeypatch, lambda _: httpx.Response(200, stream=FailingStream()))
    caplog.set_level(logging.DEBUG)
    previous = logging.root.manager.disable
    try:
        logging.disable(logging.INFO)
        safe_failure(lambda: module.fetch_original(
            KINDS[0], references.REGISTRY[KINDS[0]].url, SENTINEL))
        assert logging.root.manager.disable == logging.INFO
        assert SENTINEL not in caplog.text
    finally:
        logging.disable(previous)


def test_transport_requests_unencoded_original_bytes(monkeypatch):
    def handler(request):
        assert request.headers['accept-encoding'] == 'identity'
        return httpx.Response(200, content=BODY)

    module = install_transport(monkeypatch, handler)
    assert module.fetch_original(KINDS[0], references.REGISTRY[KINDS[0]].url, SENTINEL) == BODY


def test_encoded_response_is_refused_instead_of_rewriting_original_bytes(monkeypatch):
    import gzip
    encoded = gzip.compress(BODY)
    module = install_transport(monkeypatch, lambda _: httpx.Response(
        200, stream=httpx.ByteStream(encoded), headers={'content-encoding': 'gzip'}))
    safe_failure(lambda: module.fetch_original(
        KINDS[0], references.REGISTRY[KINDS[0]].url, SENTINEL))


def test_cli_explicit_env_file_uses_only_fake_file(tmp_path, monkeypatch, capsys):
    module = install_transport(monkeypatch, lambda request: httpx.Response(200, content=BODY)
                               if request.url.params['key'] == SENTINEL
                               else httpx.Response(403))
    fake_file = tmp_path / 'fake.env'
    fake_file.write_text('CENSUS_API_KEY=' + SENTINEL + '\n')
    assert module.main(['--output-dir', str(tmp_path / 'file-cli'),
                        '--env-file', str(fake_file)]) == 0
    result = capsys.readouterr()
    assert SENTINEL not in result.out + result.err


def test_preflight_refuses_data_tree_before_credential_access(tmp_path, monkeypatch):
    module = access()
    monkeypatch.setattr(module, 'read_credential', forbidden)
    with pytest.raises(ValueError, match='production data tree'):
        module.preflight(tmp_path / 'data' / 'new')
    assert not (tmp_path / 'data').exists()


def encoded_echo(encoding):
    unicode_key = ''.join(f'\\u{ord(character):04x}' for character in SENTINEL)
    mixed_unicode = ''.join(f'\\u{ord(character):04x}' if index % 2 else character
                            for index, character in enumerate(SENTINEL))
    percent_key = ''.join(f'%{ord(character):02x}' for character in SENTINEL)
    mixed_percent = ''.join(f'%{ord(character):02X}' if index % 2 else character
                            for index, character in enumerate(SENTINEL))
    decimal_key = ''.join(f'&#{ord(character)};' for character in SENTINEL)
    hex_key = ''.join(f'&#x{ord(character):X};' for character in SENTINEL)
    mixed_html = ''.join(f'&#x{ord(character):x};' if index % 2 else character
                         for index, character in enumerate(SENTINEL))
    mixed_url_html = ''.join(f'%{ord(character):02x}' if index % 2
                             else f'&#{ord(character)};'
                             for index, character in enumerate(SENTINEL))
    cases = {
        'json_unicode_value': '{"error":"key=' + unicode_key + '"}',
        'json_unicode_key': '{"' + unicode_key + '":"refused"}',
        'json_mixed_value': '{"error":"key=' + mixed_unicode + '"}',
        'json_duplicate_value': '{"error":"' + unicode_key + '","error":"safe"}',
        'json_nested_value': '["safe",{"error":["' + unicode_key + '"]}]',
        'url_percent': 'key=' + percent_key,
        'url_mixed': 'key=' + mixed_percent,
        'html_decimal': '<p>key=' + decimal_key + '</p>',
        'html_hex': '<p>key=' + hex_key + '</p>',
        'html_mixed': '<p>key=' + mixed_html + '</p>',
        'mixed_url_html': 'key=' + mixed_url_html,
        'json_url_value': json.dumps({'error': mixed_percent}),
    }
    return cases[encoding].encode()


@pytest.mark.parametrize('operation', ['preflight', 'acquire'])
@pytest.mark.parametrize('encoding', [
    'json_unicode_value', 'json_unicode_key', 'json_mixed_value', 'json_duplicate_value',
    'json_nested_value', 'url_percent', 'url_mixed', 'html_decimal', 'html_hex',
    'html_mixed', 'mixed_url_html', 'json_url_value'])
def test_equivalent_encoded_echo_never_written_or_recorded(tmp_path, monkeypatch, caplog,
                                                           operation, encoding):
    echoed = encoded_echo(encoding)
    calls = []

    def handler(request):
        calls.append(request)
        logging.getLogger('httpcore.connection').debug('response %s', echoed)
        return httpx.Response(200, content=echoed)

    module = install_transport(monkeypatch, handler)
    monkeypatch.setenv('CENSUS_API_KEY', SENTINEL)
    monkeypatch.setattr(references, 'REGISTRY', {
        kind: references.REGISTRY[kind] for kind in KINDS})
    monkeypatch.setattr(references, 'make_client', lambda: httpx.Client(
        transport=httpx.MockTransport(forbidden)))
    caplog.set_level(logging.DEBUG)
    output = tmp_path / 'encoded'
    if operation == 'preflight':
        safe_failure(lambda: module.preflight(output))
    else:
        safe_failure(lambda: references.acquire(tmp_path, 'encoded'))
        output = tmp_path / 'raw/references/ipums-verification/encoded.part'
    assert output.is_dir()
    assert not list(output.iterdir())
    assert not (tmp_path / 'raw/manifest.jsonl').exists()
    assert not list(tmp_path.rglob('metadata.json'))
    assert not list(tmp_path.rglob('receipt.json'))
    assert len(calls) == 1
    assert SENTINEL not in caplog.text
    assert echoed.decode() not in caplog.text


def test_safe_encoded_text_preserves_original_bytes_and_hash(tmp_path, monkeypatch):
    import hashlib
    original = b'{"display":"\\u0041 %42 &#67;","nested":{"public":"value"}} \n'
    module = install_transport(monkeypatch, lambda _: httpx.Response(200, content=original))
    monkeypatch.setenv('CENSUS_API_KEY', SENTINEL)
    output = module.preflight(tmp_path / 'safe-encoded')
    metadata = json.loads((output / 'metadata.json').read_text())
    for kind in KINDS:
        record = metadata['originals'][kind]
        assert (output / record['filename']).read_bytes() == original
        assert record['sha256'] == hashlib.sha256(original).hexdigest()
        assert record['size_bytes'] == len(original)


def test_json_echo_inspection_work_is_bounded_and_fails_closed(tmp_path, monkeypatch):
    original = json.dumps(['public'] * 5).encode()
    module = install_transport(monkeypatch, lambda _: httpx.Response(200, content=original))
    monkeypatch.setattr(module, 'MAX_ECHO_INSPECTION_ITEMS', 4)
    monkeypatch.setenv('CENSUS_API_KEY', SENTINEL)
    output = tmp_path / 'bounded-inspection'
    safe_failure(lambda: module.preflight(output))
    assert not list(output.iterdir())
