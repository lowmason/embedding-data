'''SAM.gov key handling and the protected Entity Extracts transport: the key goes only into the
first wire URL, and no file, log record, printed line or error holds it.

Every key here is FAKE_KEY, or FAKE_KEY plus punctuation (PUNCTUATED_KEY and the derived keys
of the decoding table). None is a real key.
'''

import getpass
import html
import io
import json
import logging
import os
import sys
import warnings
import zipfile
from pathlib import Path
from urllib.parse import quote, quote_plus

import httpx
import pytest
from vendor_link_fixtures import (  # noqa: F401
    EXTRACT_NAME,
    EXTRACT_TARGET,
    FAKE_KEY,
    MONTH,
    PUNCTUATED_KEY,
    REAL_SAM_MAKE_CLIENT,
    FakeSam,
    extract_answer,
    install_sam,
    no_live_sam,
    redirect_answer,
    sample_extract,
)

from embedding_data import osha_benchmark_download, sam_access, usaspending_vendor_links

URL = sam_access.extract_url(MONTH)
FAILED = 'SAM.gov extract request failed; details suppressed'
UNAVAILABLE = ('SAM_API_KEY unavailable or invalid; use the environment, --env-file or '
               '--prompt')
EXTRACTS = 'raw/sam/entity-extract/public-monthly-v2'


def acquire_arguments(data_directory, *options):
    return ['acquire-sam-extract', '--month', MONTH, '--data-dir', str(data_directory),
            *options]


def echo_zip(spelling: bytes) -> bytes:
    '''A valid ZIP archive whose comment holds `spelling` as stored bytes.'''
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(zipfile.ZipInfo('member.dat', date_time=(2026, 1, 1, 0, 0, 0)), b'x')
        archive.comment = b'echo ' + spelling + b' end'
    return buffer.getvalue()


def percent_every_byte(text: str) -> str:
    return ''.join(f'%{byte:02X}' for byte in text.encode())


# --- constants, URL and client


def test_constants():
    assert sam_access.CREDENTIAL == 'SAM_API_KEY'
    assert sam_access.KEY_PARAMETER == 'api_key'
    assert sam_access.EXTRACTS_URL == 'https://api.sam.gov/data-services/v1/extracts'
    assert sam_access.TIMEOUT == httpx.Timeout(600.0, connect=15.0)
    assert sam_access.CHUNK_SIZE == 1024 * 1024


def test_extract_url_is_the_documented_key_free_request():
    assert sam_access.extract_url('2026-11') == (
        'https://api.sam.gov/data-services/v1/extracts?fileType=ENTITY&sensitivity=PUBLIC'
        '&frequency=MONTHLY&date=11/2026&charset=UTF8')
    assert sam_access.extract_url('2027-01').endswith('&date=01/2027&charset=UTF8')


@pytest.mark.parametrize('month', ['2026-13', '11/2026', '2026-1', ''])
def test_extract_url_refuses_a_month_that_is_not_yyyy_mm(month):
    with pytest.raises(ValueError):
        sam_access.extract_url(month)


def test_client_follows_no_redirect_ignores_the_environment_and_has_no_hooks():
    with REAL_SAM_MAKE_CLIENT() as client:
        assert client.follow_redirects is False
        assert client.trust_env is False
        assert client.event_hooks == {'request': [], 'response': []}
        assert client.timeout == httpx.Timeout(600.0, connect=15.0)
        assert client.headers['User-Agent'] == osha_benchmark_download.USER_AGENT
        assert client.headers['Accept-Encoding'] == 'identity'


# --- quiet transport


def test_quiet_transport_mutes_all_logging_and_restores_the_level_even_on_error():
    before = logging.root.manager.disable
    logging.disable(logging.WARNING)
    try:
        with pytest.raises(RuntimeError, match='inside'):
            with sam_access.quiet_transport():
                assert logging.root.manager.disable == sys.maxsize
                raise RuntimeError('inside')
        assert logging.root.manager.disable == logging.WARNING
        with sam_access.quiet_transport():
            assert logging.root.manager.disable == sys.maxsize
        assert logging.root.manager.disable == logging.WARNING
    finally:
        logging.disable(before)


# --- spellings, echo detection and the hold-back scan


def test_spellings_are_the_utf8_bytes_of_the_five_forms():
    stem = FAKE_KEY.encode()
    assert sam_access.spellings(PUNCTUATED_KEY) == (
        stem + b' &"', stem + b'%20%26%22', stem + b'+%26%22', stem + b' &\\"',
        stem + b' &amp;&quot;')
    accented = FAKE_KEY + 'é'
    assert sam_access.spellings(accented) == (
        stem + b'\xc3\xa9', stem + b'%C3%A9', stem + b'%C3%A9', stem + b'\\u00e9',
        stem + b'\xc3\xa9')


# The five spellings of PUNCTUATED_KEY, built with the standard library, not by the code under
# test, so a spelling that the code drops is still sent.
PUNCTUATED_FORMS = [form.encode() for form in (
    PUNCTUATED_KEY, quote(PUNCTUATED_KEY, safe=''), quote_plus(PUNCTUATED_KEY, safe=''),
    json.dumps(PUNCTUATED_KEY)[1:-1], html.escape(PUNCTUATED_KEY))]
FORM_IDS = ['plain', 'quoted', 'form_quoted', 'json', 'html']


def test_spellings_match_the_standard_library_forms():
    assert sam_access.spellings(PUNCTUATED_KEY) == tuple(PUNCTUATED_FORMS)


# Each row is found by exactly one inspection pass, so dropping that pass misses it.
ECHO_FORMS = {
    'plain_only': (FAKE_KEY + '%41+&amp;', FAKE_KEY + '%41+&amp;'),
    'html_only': (FAKE_KEY + '%41&x', FAKE_KEY + '%41&amp;x'),
    'unquote_only': (FAKE_KEY + '+/&amp;', FAKE_KEY + '+%2F&amp;'),
    'html_of_unquote_only': (FAKE_KEY + '+/&x', FAKE_KEY + '+%2F&amp;x'),
    'unquote_plus_only': (FAKE_KEY + ' &amp;', FAKE_KEY + '+&amp;'),
    'html_of_unquote_plus_only': (FAKE_KEY + ' &x', FAKE_KEY + '+&amp;x'),
    'fully_percent_encoded': (FAKE_KEY, percent_every_byte(FAKE_KEY)),
    'inside_a_url': (FAKE_KEY, f'https://elsewhere.test.example/x?api_key={FAKE_KEY}&a=1'),
}


@pytest.mark.parametrize('case', ECHO_FORMS)
def test_contains_echo_finds_each_decoded_form(case):
    credential, text = ECHO_FORMS[case]
    assert sam_access.contains_echo(text, credential) is True


@pytest.mark.parametrize('text', ['', EXTRACT_TARGET, FAKE_KEY[:-1], FAKE_KEY[1:],
                                  FAKE_KEY[:10] + '+' + FAKE_KEY[10:],
                                  percent_every_byte(FAKE_KEY[:-1]), FAKE_KEY.lower(),
                                  FAKE_KEY.upper()])
def test_contains_echo_misses_text_without_the_whole_key(text):
    assert sam_access.contains_echo(text, FAKE_KEY) is False


@pytest.mark.parametrize('cut', range(1, len(FAKE_KEY)))
def test_holdback_writes_no_complete_spelling(cut):
    chunks = [b'PK\x03\x04 lead ' + FAKE_KEY[:cut].encode(), FAKE_KEY[cut:].encode() + b' tail']
    written = bytearray()
    with pytest.raises(ValueError):
        for part in sam_access.scan_chunks(chunks, sam_access.spellings(FAKE_KEY)):
            written.extend(part)
    assert FAKE_KEY.encode() not in written


HTML_SPELLING = html.escape(PUNCTUATED_KEY).encode()


@pytest.mark.parametrize('cut', range(1, len(HTML_SPELLING)))
def test_holdback_covers_the_longest_spelling(cut):
    spellings = sam_access.spellings(PUNCTUATED_KEY)
    chunks = [b'PK\x03\x04 lead ' + HTML_SPELLING[:cut], HTML_SPELLING[cut:] + b' tail']
    written = bytearray()
    with pytest.raises(ValueError, match='credential echoed by response'):
        for part in sam_access.scan_chunks(chunks, spellings):
            written.extend(part)
    assert not any(spelling in written for spelling in spellings)


@pytest.mark.parametrize('form', PUNCTUATED_FORMS, ids=FORM_IDS)
def test_scan_refuses_each_spelling(form):
    chunks = [b'PK\x03\x04 lead ', form + b' tail']
    with pytest.raises(ValueError, match='credential echoed by response'):
        list(sam_access.scan_chunks(chunks, sam_access.spellings(PUNCTUATED_KEY)))


@pytest.mark.parametrize('form', PUNCTUATED_FORMS, ids=FORM_IDS)
def test_scan_writes_no_spelling_that_sits_early_in_a_long_chunk(form):
    chunks = [b'PK\x03\x04 lead ' + form + b'x' * 200]
    written = bytearray()
    with pytest.raises(ValueError, match='credential echoed by response'):
        for part in sam_access.scan_chunks(chunks, sam_access.spellings(PUNCTUATED_KEY)):
            written.extend(part)
    assert bytes(written) == b''


@pytest.mark.parametrize('chunks', [
    [b'PK\x03\x04' + bytes(range(256)) * 4],
    [b'PK', b'\x03\x04', b'', b'abc' * 50, b'', b'z'],
    [bytes([n]) for n in range(200)],
    [b'PK\x03\x04 short'],
    [],
], ids=['one_chunk', 'mixed_chunks', 'byte_chunks', 'shorter_than_the_holdback', 'no_chunk'])
def test_scan_passes_a_clean_body_through_unchanged(chunks):
    out = list(sam_access.scan_chunks(chunks, sam_access.spellings(PUNCTUATED_KEY)))
    assert b''.join(out) == b''.join(chunks)
    assert all(out), 'no empty piece is yielded'


def test_scan_holds_back_exactly_the_longest_spelling_less_one_byte():
    spellings = sam_access.spellings(PUNCTUATED_KEY)
    hold = len(HTML_SPELLING) - 1
    scanned = sam_access.scan_chunks(iter([b'A' * 100, b'B' * 100]), spellings)
    assert next(scanned) == b'A' * (100 - hold)
    assert next(scanned) == b'A' * hold + b'B' * (100 - hold)
    assert next(scanned) == b'B' * hold
    assert next(scanned, None) is None


# --- fetch_extract: the key and the protected exchange


def test_key_is_sent_only_in_the_first_wire_url(tmp_path, monkeypatch):
    for redirected in (False, True):
        answers = (redirect_answer(), extract_answer()) if redirected else (extract_answer(),)
        server = install_sam(monkeypatch, FakeSam(*answers))
        partial = tmp_path / f'download-{redirected}.part'
        assert sam_access.fetch_extract(URL, FAKE_KEY, partial) == EXTRACT_NAME
        first, *rest = server.requests
        assert (first.url.scheme, first.url.host, first.url.path) == (
            'https', 'api.sam.gov', '/data-services/v1/extracts')
        assert first.url.params.get_list('api_key') == [FAKE_KEY]
        assert [item for item in first.url.params.multi_items() if item[0] != 'api_key'] == (
            list(httpx.URL(URL).params.multi_items()))
        assert len(rest) == int(redirected)
        for request in rest:
            assert str(request.url) == EXTRACT_TARGET
            assert 'api_key' not in request.url.params
            assert FAKE_KEY not in str(request.url)
        for request in server.requests:
            assert not any(FAKE_KEY in value for value in request.headers.values())
            assert request.headers['User-Agent'] == osha_benchmark_download.USER_AGENT
            assert request.headers['Accept-Encoding'] == 'identity'


def test_key_reaches_no_file_log_line_or_error(cli_runner, data_directory, caplog,
                                               monkeypatch):
    caplog.set_level(logging.DEBUG)
    # The command records the extract, so its member must fit the committed layout.
    server = install_sam(monkeypatch, FakeSam(
        redirect_answer(), extract_answer(sample_extract(committed=True))))
    monkeypatch.setenv('SAM_API_KEY', FAKE_KEY)
    result = cli_runner.invoke(usaspending_vendor_links.app, acquire_arguments(data_directory))
    assert result.exit_code == 0, result.output
    assert server.requests[0].url.params['api_key'] == FAKE_KEY
    assert FAKE_KEY not in result.output and FAKE_KEY not in caplog.text
    assert not any(FAKE_KEY.encode() in f.read_bytes()
                   for f in data_directory.rglob('*') if f.is_file())


def test_logging_is_muted_during_every_request_and_restored_after(tmp_path, monkeypatch):
    before = logging.root.manager.disable
    server = install_sam(monkeypatch, FakeSam(redirect_answer(), extract_answer()))
    sam_access.fetch_extract(URL, FAKE_KEY, tmp_path / 'download.part')
    assert server.logging_thresholds == [sys.maxsize, sys.maxsize]
    assert logging.root.manager.disable == before


@pytest.mark.parametrize('status', [301, 302, 303, 307, 308])
def test_one_redirect_of_any_kind_is_fetched_once_without_the_key(status, tmp_path,
                                                                  monkeypatch):
    server = install_sam(monkeypatch, FakeSam(redirect_answer(status=status), extract_answer()))
    partial = tmp_path / 'download.part'
    assert sam_access.fetch_extract(URL, FAKE_KEY, partial) == EXTRACT_NAME
    assert partial.read_bytes() == sample_extract()
    assert [str(request.url) for request in server.requests[1:]] == [EXTRACT_TARGET]


@pytest.mark.parametrize('location, target', [
    (f'/extracts/{EXTRACT_NAME}', f'https://api.sam.gov/extracts/{EXTRACT_NAME}'),
    ('#fragment', f'{URL}#fragment'),
], ids=['relative_path', 'fragment_only'])
def test_a_relative_location_resolves_against_the_key_free_url(location, target, tmp_path,
                                                               monkeypatch):
    server = install_sam(monkeypatch, FakeSam(redirect_answer(location), extract_answer()))
    assert sam_access.fetch_extract(URL, FAKE_KEY, tmp_path / 'download.part') == EXTRACT_NAME
    redirected = server.requests[1]
    assert redirected.url == httpx.URL(target)
    assert 'api_key' not in redirected.url.params
    assert FAKE_KEY not in str(redirected.url)


def test_a_cookie_from_the_keyed_answer_is_not_sent_to_the_target(tmp_path, monkeypatch):
    target = f'https://api.sam.gov/files/{EXTRACT_NAME}'
    cookie = {'Set-Cookie': f'session={FAKE_KEY}; Path=/'}
    server = install_sam(monkeypatch, FakeSam(redirect_answer(target, headers=cookie),
                                              extract_answer()))
    assert sam_access.fetch_extract(URL, FAKE_KEY, tmp_path / 'download.part') == EXTRACT_NAME
    assert str(server.requests[1].url) == target
    assert 'cookie' not in server.requests[1].headers


def test_the_name_falls_back_to_the_redirect_target_segment(tmp_path, monkeypatch):
    body = sample_extract()
    for number, extra in enumerate(({}, {'Content-Disposition': 'attachment'})):
        answer = (200, {'Content-Length': str(len(body))} | extra, body)
        install_sam(monkeypatch, FakeSam(redirect_answer(), answer))
        partial = tmp_path / f'download-{number}.part'
        assert sam_access.fetch_extract(URL, FAKE_KEY, partial) == EXTRACT_NAME
        assert partial.read_bytes() == body


def test_a_direct_answer_streams_the_delivered_bytes_into_the_part(tmp_path, monkeypatch):
    body = sample_extract()
    monkeypatch.setattr(sam_access, 'CHUNK_SIZE', 7)
    headers = {'Content-Length': str(len(body)), 'Content-Encoding': 'identity',
               'Content-Disposition': f'attachment; filename={EXTRACT_NAME}'}
    install_sam(monkeypatch, FakeSam((200, headers, body)))
    partial = tmp_path / 'download.part'
    assert sam_access.fetch_extract(URL, FAKE_KEY, partial) == EXTRACT_NAME
    assert partial.read_bytes() == body


# --- fetch_extract: refusals


def refused_answers(case, monkeypatch):
    if case == 'body_echo':
        return (extract_answer(echo_zip(FAKE_KEY.encode())),)
    if case == 'body_echo_across_chunks':
        body = echo_zip(FAKE_KEY.encode())
        # The first chunk ends five bytes into the key.
        monkeypatch.setattr(sam_access, 'CHUNK_SIZE', body.index(FAKE_KEY.encode()) + 5)
        return (extract_answer(body),)
    if case == 'quoted_echo':
        echoed = quote(f'{URL}&api_key={FAKE_KEY}', safe='').encode()
        return (extract_answer(echo_zip(echoed)),)
    if case == 'location_echo':
        return (redirect_answer(f'{EXTRACT_TARGET}?api_key={FAKE_KEY}'), extract_answer())
    if case == 'location_percent_echo':
        location = f'{EXTRACT_TARGET}?token={percent_every_byte(FAKE_KEY)}'
        return (redirect_answer(location), extract_answer())
    if case == 'json_body':
        return (extract_answer(json.dumps({'error': 'invalid request'}).encode()),)
    if case == 'second_redirect':
        again = f'https://files-2.test.example/extracts/{EXTRACT_NAME}'
        return (redirect_answer(), redirect_answer(again), extract_answer())
    if case == 'no_length':
        return (extract_answer(headers={
            'Content-Disposition': f'attachment; filename="{EXTRACT_NAME}"'}),)
    if case == 'short':
        body = sample_extract()
        return (extract_answer(body, headers={
            'Content-Length': str(len(body) + 10),
            'Content-Disposition': f'attachment; filename="{EXTRACT_NAME}"'}),)
    if case == 'bad_name':
        return (extract_answer(name='SAM_PUBLIC_MONTHLY_V2_20261102.ZIP'),)
    raise AssertionError(case)


@pytest.mark.parametrize('case', ['body_echo', 'body_echo_across_chunks', 'quoted_echo',
                                  'location_echo', 'location_percent_echo', 'json_body',
                                  'second_redirect', 'no_length', 'short', 'bad_name'])
def test_refused_responses_leave_nothing(case, tmp_path, monkeypatch):
    install_sam(monkeypatch, FakeSam(*refused_answers(case, monkeypatch)))
    with pytest.raises(ValueError) as error:
        sam_access.fetch_extract(URL, FAKE_KEY, tmp_path / 'download.part')
    assert FAKE_KEY not in str(error.value) and error.value.__context__ is None
    assert not (tmp_path / 'download.part').exists()


def zip_with_name(body, name=EXTRACT_NAME, **extra):
    return extract_answer(body, headers={
        'Content-Length': str(len(body)), 'Content-Disposition': f'attachment; filename="{name}"',
        **extra})


MORE_REFUSALS = {
    # case: (answers, requests made)
    'no_location': ((redirect_answer(None), extract_answer()), 1),
    'empty_location': ((redirect_answer(''), extract_answer()), 1),
    'blank_location': ((redirect_answer('   '), extract_answer()), 1),
    'created_not_ok': (((201,) + extract_answer()[1:],), 1),
    'unauthorized': (((401, {'Content-Length': '2'}, b'{}'),), 1),
    'redirect_target_missing': ((redirect_answer(), (404, {}, b'')), 2),
    'redirect_target_created': ((redirect_answer(), (201,) + extract_answer()[1:]), 2),
    'gzip_encoded': ((zip_with_name(sample_extract(), **{'Content-Encoding': 'gzip'}),), 1),
    'length_not_a_number': ((extract_answer(headers={
        'Content-Length': 'many', 'Content-Disposition': f'attachment; filename={EXTRACT_NAME}'}),
    ), 1),
    'longer_than_its_length': ((extract_answer(sample_extract(), headers={
        'Content-Length': str(len(sample_extract()) - 3),
        'Content-Disposition': f'attachment; filename={EXTRACT_NAME}'}),), 1),
    'garbage_after_the_signature': ((zip_with_name(b'PK\x03\x04 not an archive'),), 1),
    'prefixed_zip': ((zip_with_name(b'XXXX' + sample_extract()),), 1),
    'empty_body': ((zip_with_name(b''),), 1),
    'signature_cut_short': ((zip_with_name(b'PK\x03'),), 1),
    'no_name_and_no_redirect': ((extract_answer(name=None),), 1),
    'bad_name_beats_a_good_segment': ((redirect_answer(),
                                       extract_answer(name='SAM_PUBLIC_MONTHLY_V2_20261102.ZIP')),
                                      2),
    'segment_not_a_name': ((redirect_answer('https://files.test.example/extracts/download'),
                            extract_answer(name=None)), 2),
    'lowercase_name': ((extract_answer(name=EXTRACT_NAME.lower()),), 1),
    'name_with_a_prefix': ((extract_answer(name='x' + EXTRACT_NAME),), 1),
    'name_with_a_suffix': ((extract_answer(name=EXTRACT_NAME + '.x'),), 1),
    'name_with_a_path': ((extract_answer(name='../' + EXTRACT_NAME),), 1),
    'ascii_name': ((extract_answer(name='SAM_PUBLIC_MONTHLY_V2_20261102.ZIP'),), 1),
    'second_redirect': ((redirect_answer(), redirect_answer(EXTRACT_TARGET + '?again=1'),
                         extract_answer()), 2),
}


@pytest.mark.parametrize('case', MORE_REFUSALS)
def test_each_refusal_raises_one_fixed_error_with_no_chain_and_writes_nothing(
        case, tmp_path, monkeypatch):
    answers, requests = MORE_REFUSALS[case]
    server = install_sam(monkeypatch, FakeSam(*answers))
    with pytest.raises(ValueError) as error:
        sam_access.fetch_extract(URL, FAKE_KEY, tmp_path / 'download.part')
    assert str(error.value) == FAILED
    assert error.value.__cause__ is None and error.value.__context__ is None
    assert list(tmp_path.iterdir()) == []
    assert len(server.requests) == requests


def test_a_refused_location_is_never_requested(tmp_path, monkeypatch):
    for location in (f'{EXTRACT_TARGET}?api_key={FAKE_KEY}',
                     f'{EXTRACT_TARGET}?token={percent_every_byte(FAKE_KEY)}'):
        server = install_sam(monkeypatch, FakeSam(redirect_answer(location), extract_answer()))
        with pytest.raises(ValueError, match=FAILED):
            sam_access.fetch_extract(URL, FAKE_KEY, tmp_path / 'download.part')
        assert len(server.requests) == 1


def test_a_body_without_the_zip_signature_is_refused_before_the_part_is_opened(
        tmp_path, monkeypatch):
    opened = []
    original_open = Path.open

    def spy(path, *args, **kwargs):
        opened.append(path)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', spy)
    for body in (json.dumps({'error': 'invalid'}).encode(), b'XXXX' + sample_extract(),
                 b'PK\x03', b''):
        install_sam(monkeypatch, FakeSam(zip_with_name(body)))
        with pytest.raises(ValueError, match=FAILED):
            sam_access.fetch_extract(URL, FAKE_KEY, tmp_path / 'download.part')
    assert opened == []
    assert list(tmp_path.iterdir()) == []


def test_an_existing_part_is_neither_overwritten_nor_removed(tmp_path, monkeypatch):
    install_sam(monkeypatch, FakeSam(extract_answer()))
    partial = tmp_path / 'download.part'
    partial.write_bytes(b'someone else')
    with pytest.raises(ValueError) as error:
        sam_access.fetch_extract(URL, FAKE_KEY, partial)
    assert str(error.value) == FAILED and error.value.__context__ is None
    assert partial.read_bytes() == b'someone else'


def test_a_transport_error_is_replaced_by_the_fixed_error(tmp_path, monkeypatch):
    def fail(request):
        raise httpx.ConnectError(f'failed {request.url}', request=request)

    install_sam(monkeypatch, fail)
    with pytest.raises(ValueError) as error:
        sam_access.fetch_extract(URL, FAKE_KEY, tmp_path / 'download.part')
    assert str(error.value) == FAILED
    assert error.value.__cause__ is None and error.value.__context__ is None
    assert list(tmp_path.iterdir()) == []


class InterruptedStream(httpx.SyncByteStream):
    '''A body that delivers `first`, then stops as a Ctrl-C would.'''

    def __init__(self, first):
        self.first = first

    def __iter__(self):
        yield self.first
        raise KeyboardInterrupt


def test_an_interrupted_download_removes_its_part_and_raises_the_fixed_error(tmp_path,
                                                                             monkeypatch):
    before = logging.root.manager.disable
    body = sample_extract()
    headers = {'Content-Length': str(len(body)),
               'Content-Disposition': f'attachment; filename="{EXTRACT_NAME}"'}
    install_sam(monkeypatch, lambda request: httpx.Response(
        200, headers=headers, stream=InterruptedStream(body[:64])))
    # Small chunks, so the .part exists and holds bytes before the interrupt.
    monkeypatch.setattr(sam_access, 'CHUNK_SIZE', 16)
    partial = tmp_path / 'download.part'
    # BaseException: under a wrong version the interrupt escapes, and this must still fail
    # the test rather than stop the session.
    with pytest.raises(BaseException) as error:
        sam_access.fetch_extract(URL, FAKE_KEY, partial)
    assert error.type is ValueError
    assert str(error.value) == FAILED
    assert error.value.__cause__ is None and error.value.__context__ is None
    assert list(tmp_path.iterdir()) == []
    assert logging.root.manager.disable == before


def test_transport_error_line_holds_no_key(cli_runner, data_directory, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)

    def fail(request):
        raise httpx.ConnectError(f'failed {request.url}', request=request)

    install_sam(monkeypatch, fail)
    monkeypatch.setenv('SAM_API_KEY', FAKE_KEY)
    result = cli_runner.invoke(usaspending_vendor_links.app, acquire_arguments(data_directory))
    assert result.exit_code == 2
    assert result.output.strip() == ('USAspending vendor links acquire-sam-extract failed: '
                                     'validation; run -; path '
                                     'raw/sam/entity-extract/public-monthly-v2')
    assert FAKE_KEY not in result.output + caplog.text


# --- read_credential


class Terminal(io.StringIO):
    def __init__(self, tty):
        super().__init__()
        self.tty = tty

    def isatty(self):
        return self.tty


def hidden_prompt(monkeypatch, *, tty, answer=FAKE_KEY, warn=False):
    '''Replace stdin and getpass. Returns the list of prompts shown.'''
    asked = []

    def fake_getpass(prompt=''):
        asked.append(prompt)
        if warn:
            warnings.warn('input may be echoed', getpass.GetPassWarning)
        return answer

    monkeypatch.setattr(sys, 'stdin', Terminal(tty))
    monkeypatch.setattr(getpass, 'getpass', fake_getpass)
    return asked


def env_file(tmp_path, text):
    file = tmp_path / 'sam.env'
    file.write_text(text)
    return file


def unavailable(**options):
    '''Expect the fixed refusal, raised with no chained exception that could hold a value.'''
    with pytest.raises(ValueError) as error:
        sam_access.read_credential(**options)
    assert str(error.value) == UNAVAILABLE
    assert error.value.__cause__ is None and error.value.__context__ is None
    return error.value


def test_read_credential_order_and_refusals(tmp_path, monkeypatch):
    other = 'OTHERkey0123456789abcdefFAKE'
    file = env_file(tmp_path, f'SAM_API_KEY={other}\n')
    asked = hidden_prompt(monkeypatch, tty=True, answer='PROMPTkey0123456789FAKE')
    # The environment wins over --env-file and --prompt.
    monkeypatch.setenv('SAM_API_KEY', FAKE_KEY)
    assert sam_access.read_credential(env_file=file, prompt=True) == FAKE_KEY
    # --env-file comes next, and it leaves the process environment unchanged.
    monkeypatch.delenv('SAM_API_KEY')
    before = dict(os.environ)
    assert sam_access.read_credential(env_file=file, prompt=True) == other
    assert dict(os.environ) == before
    assert asked == []
    # --prompt without a terminal raises before any prompt.
    asked = hidden_prompt(monkeypatch, tty=False)
    unavailable(prompt=True)
    assert asked == []
    # A blank value and a control character raise, without the value.
    for value in ('', '   ', FAKE_KEY + '\n', FAKE_KEY[:5] + '\x1b' + FAKE_KEY[5:]):
        monkeypatch.setenv('SAM_API_KEY', value)
        assert FAKE_KEY[:5] not in str(unavailable())


def test_read_credential_prompts_only_in_a_terminal(monkeypatch):
    asked = hidden_prompt(monkeypatch, tty=True)
    assert sam_access.read_credential(prompt=True) == FAKE_KEY
    assert asked == ['SAM.gov API key (hidden): ']
    asked = hidden_prompt(monkeypatch, tty=True)
    unavailable(prompt=False)
    assert asked == []


def test_read_credential_refuses_a_prompt_that_could_echo(monkeypatch):
    asked = hidden_prompt(monkeypatch, tty=True, warn=True)
    error = unavailable(prompt=True)
    assert len(asked) == 1
    assert FAKE_KEY not in str(error)


def test_read_credential_returns_the_env_file_value_without_interpolation(tmp_path,
                                                                          monkeypatch):
    monkeypatch.setenv('OTHER_VALUE', FAKE_KEY)
    file = env_file(tmp_path, 'SAM_API_KEY=${OTHER_VALUE}\n')
    assert sam_access.read_credential(env_file=file) == '${OTHER_VALUE}'
    assert 'SAM_API_KEY' not in os.environ


def test_a_blank_environment_value_fails_closed_without_reading_the_env_file(tmp_path,
                                                                             monkeypatch):
    file = env_file(tmp_path, f'SAM_API_KEY={FAKE_KEY}\n')
    monkeypatch.setenv('SAM_API_KEY', '')
    unavailable(env_file=file)


@pytest.mark.parametrize('position', ['start', 'middle', 'end'])
def test_read_credential_refuses_any_control_character(position, tmp_path):
    # An env file carries every control character, NUL included, which the environment cannot.
    # NUL, tab, newline and unit separator (C0), delete, and next line (C1).
    for character in ('\x00', '\t', '\n', '\x1f', '\x7f', '\x85'):
        value = {'start': character + FAKE_KEY,
                 'middle': FAKE_KEY[:9] + character + FAKE_KEY[9:],
                 'end': FAKE_KEY + character}[position]
        error = unavailable(env_file=env_file(tmp_path, f'SAM_API_KEY="{value}"\n'))
        assert FAKE_KEY[:9] not in str(error)


def test_read_credential_accepts_printable_non_ascii(tmp_path):
    value = FAKE_KEY + 'é'
    assert sam_access.read_credential(env_file=env_file(tmp_path, f'SAM_API_KEY={value}\n')) == (
        value)


@pytest.mark.parametrize('content', ['', 'OTHER=1\n', 'SAM_API_KEY\n'],
                         ids=['empty', 'other_name', 'name_without_value'])
def test_read_credential_refuses_an_env_file_without_a_usable_key(content, tmp_path,
                                                                  monkeypatch):
    # A terminal is there, but no --prompt was given, so nothing is asked.
    asked = hidden_prompt(monkeypatch, tty=True)
    unavailable(env_file=env_file(tmp_path, content))
    unavailable(env_file=tmp_path / 'absent.env')
    unavailable()
    assert asked == []


def test_read_credential_falls_back_to_the_prompt_when_the_env_file_lacks_the_key(
        tmp_path, monkeypatch):
    asked = hidden_prompt(monkeypatch, tty=True)
    file = env_file(tmp_path, 'OTHER=1\n')
    assert sam_access.read_credential(env_file=file, prompt=True) == FAKE_KEY
    assert len(asked) == 1


def test_read_credential_restores_the_logging_level(tmp_path, monkeypatch):
    before = logging.root.manager.disable
    hidden_prompt(monkeypatch, tty=False)
    unavailable(prompt=True)
    assert logging.root.manager.disable == before
    monkeypatch.setenv('SAM_API_KEY', FAKE_KEY)
    assert sam_access.read_credential() == FAKE_KEY
    assert logging.root.manager.disable == before
