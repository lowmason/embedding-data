'''Acquisition-only credentials and protected transport for two public ACS queries.'''

import argparse
import getpass
import hashlib
import html
import json
import logging
import os
import sys
import warnings
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, quote_plus

import httpx
from dotenv import dotenv_values

from embedding_data.osha_benchmark_download import USER_AGENT

ACS_QUERIES = {
    f'acs_{year}_employment': (
        f'https://api.census.gov/data/{year}/acs/acs1?get=NAME,B23025_004E&for=state:*',
        f'acs_{year}_employment.json') for year in (2023, 2024)}
MAX_ORIGINAL_BYTES = 32 * 1024 * 1024


@contextmanager
def _quiet_transport():
    # HTTPX/httpcore log wire URLs. Suppress globally while secrets are in transport,
    # including child loggers/exception handlers, then restore the caller's threshold.
    previous = logging.root.manager.disable
    logging.disable(sys.maxsize)
    try:
        yield
    finally:
        logging.disable(previous)


def _valid_credential(value):
    return (isinstance(value, str) and bool(value.strip())
            and not any(ord(character) < 32 or ord(character) == 127 for character in value))


def read_credential(*, env_file: Path | None = None, prompt: bool = False) -> str:
    '''Resolve only at explicit acquisition; never populate the process environment.'''
    value = None
    with _quiet_transport():
        try:
            value = os.environ.get('CENSUS_API_KEY')
            if value is None and env_file is not None:
                value = dotenv_values(env_file, interpolate=False).get('CENSUS_API_KEY')
            if value is None and prompt:
                if not sys.stdin.isatty():
                    raise ValueError('hidden entry requires a local terminal')
                # getpass can fall back to echoed stdin; warnings must instead fail closed.
                with warnings.catch_warnings():
                    warnings.simplefilter('error', getpass.GetPassWarning)
                    value = getpass.getpass('Census API key (hidden): ')
        except (Exception, KeyboardInterrupt):
            value = None
    if not _valid_credential(value):
        raise ValueError('CENSUS_API_KEY unavailable or invalid; use acquisition runtime '
                         'environment, an explicit --env-file, or --prompt in a local terminal')
    return value


def make_client():
    '''Build an isolated client without environment auth, proxies or external hooks.'''
    return httpx.Client(timeout=60, follow_redirects=False, trust_env=False,
                        headers={'User-Agent': USER_AGENT}, event_hooks={})


def _reject_echo(body, credential):
    spellings = (credential, quote(credential, safe=''), quote_plus(credential, safe=''),
                 json.dumps(credential, ensure_ascii=True)[1:-1], html.escape(credential))
    if any(spelling.encode('utf-8') in body for spelling in spellings):
        raise ValueError('credential echoed by response')


def fetch_original(kind: str, url: str, credential: str) -> bytes:
    '''Return checked original bytes; wire URL/errors never cross this boundary.'''
    if kind not in ACS_QUERIES or url != ACS_QUERIES[kind][0]:
        raise ValueError('Census authentication requires an exact registered ACS query')
    if not _valid_credential(credential):
        raise ValueError('CENSUS_API_KEY unavailable or invalid')
    body = None
    with _quiet_transport():
        try:
            # Build the authenticated URL only inside the protected transport scope.
            wire_url = httpx.URL(url).copy_add_param('key', credential)
            with make_client() as client:
                with client.stream('GET', wire_url, follow_redirects=False,
                                   headers={'Accept-Encoding': 'identity'}) as response:
                    # Status validation rejects all redirects without reading Location.
                    response.raise_for_status()
                    if response.headers.get('content-encoding', 'identity').lower() != 'identity':
                        raise ValueError('encoded original requires separate inspection')
                    length = response.headers.get('content-length')
                    if length is not None and int(length) > MAX_ORIGINAL_BYTES:
                        raise ValueError('response exceeds bound')
                    buffer = bytearray()
                    for chunk in response.iter_bytes():
                        if len(buffer) + len(chunk) > MAX_ORIGINAL_BYTES:
                            raise ValueError('response exceeds bound')
                        buffer.extend(chunk)
                    if length is not None and len(buffer) != int(length):
                        raise ValueError('response length differs')
                    _reject_echo(buffer, credential)
                    body = bytes(buffer)
        except Exception:
            # Raise after leaving the handler so even __context__ cannot retain a
            # transport exception containing the authenticated URL or response body.
            body = None
    if body is None:
        raise ValueError('Census public query failed; response/transport details suppressed')
    return body


def _fresh_output(output_dir):
    output_dir = Path(output_dir).absolute()
    if any(path.is_symlink() for path in (output_dir, *output_dir.parents)):
        raise ValueError('preflight output contains a symlink')
    if output_dir.exists():
        raise ValueError('occupied preflight output; choose a fresh directory')
    # This helper is for inspection outside every checkout's data tree.
    if 'data' in output_dir.parts:
        raise ValueError('preflight output must be outside the production data tree')
    return output_dir


def preflight(output_dir: Path, *, env_file: Path | None = None,
              prompt: bool = False) -> Path:
    '''Save exactly two originals in fresh private inspection storage, without parsing.'''
    output_dir = _fresh_output(output_dir)
    credential = read_credential(env_file=env_file, prompt=prompt)
    try:
        output_dir.mkdir(mode=0o700)
    except OSError:
        raise ValueError('preflight output creation failed; choose a fresh directory') from None
    originals = {}
    for kind, (url, filename) in ACS_QUERIES.items():
        body = fetch_original(kind, url, credential)
        with (output_dir / filename).open('xb') as output:
            output.write(body)
        originals[kind] = {
            'source_url': url, 'method': 'GET', 'filename': filename,
            'sha256': hashlib.sha256(body).hexdigest(), 'size_bytes': len(body),
            'retrieved_at': datetime.now(UTC).isoformat(timespec='seconds')}
    with (output_dir / 'metadata.json').open('x', encoding='utf-8') as output:
        json.dump({'purpose': 'public-original-layout-inspection', 'originals': originals},
                  output, sort_keys=True, indent=2)
        output.write('\n')
    return output_dir


def main(argv=None):
    parser = argparse.ArgumentParser(description=(
        'Acquire only the two registered public ACS originals for layout inspection.'))
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='Fresh directory outside the production data tree')
    parser.add_argument('--env-file', type=Path,
                        help='Explicit existing local dotenv file (never copied or modified)')
    parser.add_argument('--prompt', action='store_true', help='Allow hidden local terminal entry')
    args = parser.parse_args(argv)
    try:
        output_dir = preflight(args.output_dir, env_file=args.env_file, prompt=args.prompt)
    except (ValueError, OSError):
        print('Census preflight failed. Check CENSUS_API_KEY runtime configuration, '
              'network access and a fresh output directory; no response details displayed.',
              file=sys.stderr)
        return 1
    metadata = json.loads((output_dir / 'metadata.json').read_text(encoding='utf-8'))
    for record in metadata['originals'].values():
        print(f'{output_dir / record["filename"]} sha256={record["sha256"]}')
    print(output_dir / 'metadata.json')
    return 0


if __name__ == '__main__':
    sys.exit(main())
