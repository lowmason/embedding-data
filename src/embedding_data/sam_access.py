'''The SAM.gov key and the protected Entity Extracts transport (Stage 14).

Only `acquire-sam-extract` uses this module's key and network functions. The key comes from
the environment, an explicit env file or a hidden prompt, and never enters the process
environment. It goes only into the first wire URL, as `api_key`, while all logging is muted,
because HTTPX logs wire URLs. A redirect `Location` or a response body that holds any spelling
of the key is refused, and nothing from it is written. No error raised here holds the key, the
wire URL or response bytes. The pattern is `ipums_census_access`, and nothing is imported
from it.
'''

import getpass
import html
import itertools
import json
import logging
import os
import sys
import unicodedata
import warnings
import zipfile
from collections.abc import Iterable, Iterator
from contextlib import ExitStack, contextmanager
from email.message import Message
from pathlib import Path
from urllib.parse import quote, quote_plus, unquote, unquote_plus

import httpx

from embedding_data import sam_raw, usaspending_raw
from embedding_data.osha_benchmark_download import USER_AGENT

CREDENTIAL = 'SAM_API_KEY'
KEY_PARAMETER = 'api_key'
EXTRACTS_URL = 'https://api.sam.gov/data-services/v1/extracts'
TIMEOUT = httpx.Timeout(600.0, connect=15.0)
CHUNK_SIZE = 1024 * 1024
PROMPT = 'SAM.gov API key (hidden): '
UNAVAILABLE = 'SAM_API_KEY unavailable or invalid; use the environment, --env-file or --prompt'
FAILED = 'SAM.gov extract request failed; details suppressed'


@contextmanager
def quiet_transport():
    '''Mute every logger while the key is in use, then restore the caller's threshold.'''
    previous = logging.root.manager.disable
    logging.disable(sys.maxsize)
    try:
        yield
    finally:
        logging.disable(previous)


def usable_credential(value: object) -> bool:
    '''A non-blank string with no control character.'''
    return (isinstance(value, str) and bool(value.strip())
            and not any(unicodedata.category(character) == 'Cc' for character in value))


def read_credential(*, env_file: Path | None = None, prompt: bool = False) -> str:
    '''The key from the environment, else from `env_file`, else from a hidden prompt.

    The prompt runs only in a real terminal and fails when the input could echo. No error
    holds the value, and the process environment is never changed.
    '''
    value = None
    with quiet_transport():
        try:
            value = os.environ.get(CREDENTIAL)
            if value is None and env_file is not None:
                from dotenv import dotenv_values

                value = dotenv_values(env_file, interpolate=False).get(CREDENTIAL)
            if value is None and prompt:
                if not sys.stdin.isatty():
                    raise ValueError('hidden entry needs a terminal')
                with warnings.catch_warnings():
                    warnings.simplefilter('error', getpass.GetPassWarning)
                    value = getpass.getpass(PROMPT)
        except Exception:
            value = None
    # Raised after the handler, so no chained exception can hold the value.
    if not usable_credential(value):
        raise ValueError(UNAVAILABLE)
    return value


def extract_url(month: str) -> str:
    '''The key-free request for the public monthly V2 UTF-8 extract of `month`.'''
    year, number = sam_raw.parse_month(month).split('-')
    return (f'{EXTRACTS_URL}?fileType=ENTITY&sensitivity=PUBLIC&frequency=MONTHLY'
            f'&date={number}/{year}&charset=UTF8')


def make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    '''A client that follows no redirect, ignores the environment, has no event hooks and
    asks for bytes as stored.'''
    return httpx.Client(
        follow_redirects=False,
        trust_env=False,
        event_hooks={},
        headers={'User-Agent': USER_AGENT, 'Accept-Encoding': 'identity'},
        timeout=TIMEOUT,
        transport=transport,
    )


def spellings(credential: str) -> tuple[bytes, ...]:
    '''The UTF-8 bytes of the key as written, URL-quoted, form-quoted, JSON-escaped and
    HTML-escaped.'''
    forms = (credential, quote(credential, safe=''), quote_plus(credential, safe=''),
             json.dumps(credential, ensure_ascii=True)[1:-1], html.escape(credential))
    return tuple(form.encode('utf-8') for form in forms)


def contains_echo(text: str, credential: str) -> bool:
    '''Whether `text`, its URL or form decoding, or the HTML unescaping of any of these
    holds the key.'''
    for decoded in (text, unquote(text), unquote_plus(text)):
        if credential in decoded or credential in html.unescape(decoded):
            return True
    return False


def scan_chunks(chunks: Iterable[bytes], spellings: tuple[bytes, ...]) -> Iterator[bytes]:
    '''Yield the bytes of `chunks` that are safe to write.

    The last `len(longest spelling) - 1` bytes are held back and joined to the next chunk,
    so a spelling that crosses a chunk boundary is found before any of its bytes is yielded.
    '''
    hold = max(len(spelling) for spelling in spellings) - 1
    tail = b''
    for chunk in chunks:
        window = tail + chunk
        if any(spelling in window for spelling in spellings):
            raise ValueError('credential echoed by response')
        cut = max(len(window) - hold, 0)
        if cut:
            yield window[:cut]
        tail = window[cut:]
    if tail:
        yield tail


def redirect_target(response: httpx.Response, url: str, credential: str) -> httpx.URL:
    '''The target of a 3xx answer, resolved against the key-free URL.'''
    location = response.headers.get('Location', '')
    if not location.strip():
        raise ValueError('redirect without a Location')
    if contains_echo(location, credential):
        raise ValueError('credential echoed by redirect')
    return httpx.URL(url).join(location)


def delivered_name(response: httpx.Response, target: httpx.URL | None) -> str:
    '''The Content-Disposition file name, or else the redirect target's last path segment.'''
    message = Message()
    message['Content-Disposition'] = response.headers.get('Content-Disposition', '')
    name = message.get_filename()
    if name is None and target is not None:
        name = target.path.rsplit('/', 1)[-1]
    if name is None or not sam_raw.NAME.fullmatch(name):
        raise ValueError('delivered file has no extract name')
    return name


def get(stack: ExitStack, url: httpx.URL) -> httpx.Response:
    '''Stream a GET of `url` through a new client, so no state from an earlier answer
    (a cookie, say) reaches it. `stack` closes both.'''
    client = stack.enter_context(make_client())
    return stack.enter_context(client.stream('GET', url))


def require_final_answer(response: httpx.Response) -> int:
    '''A 200 answer, stored as is, with a declared length. Returns the length.'''
    if response.status_code != 200:
        raise ValueError('extract answer is not 200')
    if response.headers.get('Content-Encoding', 'identity').strip().lower() != 'identity':
        raise ValueError('encoded extract')
    length = response.headers.get('Content-Length')
    if length is None:
        raise ValueError('extract has no Content-Length')
    return int(length)


def fetch_extract(url: str, credential: str, partial: Path) -> str:
    '''Stream the extract requested by key-free `url` into `partial`, opened exclusively,
    and return the delivered file name.

    The key is added only to the first wire URL. A redirect is fetched once, with no key,
    by a new client. Any failure removes `partial` if this call created it and raises one
    fixed error with no chained exception.
    '''
    failed = False
    created = False
    name = None
    with quiet_transport():
        try:
            forms = spellings(credential)
            wire_url = httpx.URL(url).copy_add_param(KEY_PARAMETER, credential)
            with ExitStack() as stack:
                response = get(stack, wire_url)
                target = None
                if 300 <= response.status_code < 400:
                    target = redirect_target(response, url, credential)
                    response = get(stack, target)
                length = require_final_answer(response)
                name = delivered_name(response, target)
                chunks = response.iter_raw(CHUNK_SIZE)
                first = next(chunks, b'')
                if not first.startswith(usaspending_raw.ZIP_SIGNATURE):
                    raise ValueError('extract is not a ZIP file')
                stream = partial.open('xb')
                created = True
                with stream:
                    written = sum(stream.write(part) for part in
                                  scan_chunks(itertools.chain([first], chunks), forms))
            if written != length:
                raise ValueError('extract length differs from Content-Length')
            if not zipfile.is_zipfile(partial):
                raise ValueError('extract is not a ZIP file')
        except Exception:
            failed = True
    # Raised after the handler, so no chained exception keeps the wire URL or a body.
    if failed:
        if created:
            partial.unlink(missing_ok=True)
        raise ValueError(FAILED)
    return name
