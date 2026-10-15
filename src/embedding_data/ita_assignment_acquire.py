'''Acquire sequential, immutable Census batches and replay verified evidence offline.'''

import json
import math
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import httpx
import polars as pl

from embedding_data import geography_references as gr
from embedding_data import manifest, paths, target_io
from embedding_data.ita_assignment_prepare import PreparedInputs, check_preparation, validate_batch
from embedding_data.ita_county_verification import parse_geocodes
from embedding_data.ita_verification_run import BENCHMARK, GEOCODER, VINTAGE, make_client
from embedding_data.osha_benchmark_download import record_download

CURRENT_FRAME_LIMIT = (
    'Current address ranges may change between batches or resumed requests. Catalog '
    'snapshots identify the requested options, not an immutable service address frame. '
    'Offline determinism means replay of verified cached evidence, not identical '
    'answers from future Census requests.'
)
METADATA_CLIENT = 'ita-assignment-generated-metadata'
CATALOGS = ('benchmarks.json', 'vintages.json')
SELECTION = 'catalog-selection.json'
COMPLETION = 'acquisition.json'
START = 'acquisition-start.json'


@dataclass(frozen=True)
class Evidence:
    responses: pl.LazyFrame
    provenance: dict
    _data_dir: Path = field(repr=False)
    _prepared: PreparedInputs = field(repr=False)

    def verify(self) -> None:
        '''Recheck preparation and every cited original without opening a client.'''
        current = read_evidence(self._data_dir, self._prepared)
        if current.provenance != self.provenance:
            raise ValueError(f'{self._prepared.directory}: evidence provenance changed')


def parse_response(text: str, expected_ids: list[str]) -> pl.DataFrame:
    frame = parse_geocodes(text)
    if (not all(isinstance(value, str) and value for value in expected_ids)
            or len(expected_ids) != len(set(expected_ids))
            or frame.height != len(expected_ids)
            or set(frame['row_key']) != set(expected_ids)):
        raise ValueError('Census response IDs do not exactly cover frozen batch')
    return frame.rename({'row_key': 'request_id',
                         'county_geoid': 'geocode_county_geoid'}).sort('request_id')


def _option(catalog: dict, kind: str, required: str) -> str:
    if not isinstance(catalog, dict) or not isinstance(catalog.get(kind + 's'), list):
        raise ValueError('invalid Census catalog structure')
    rows = catalog[kind + 's']
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get(kind + 'Name'), str):
            raise ValueError('invalid Census catalog row')
        value = row.get('id')
        if (type(value) not in (str, int, float) or not str(value).strip()
                or isinstance(value, float) and not math.isfinite(value)):
            raise ValueError('invalid Census catalog option ID')
    matches = [row for row in rows if row[kind + 'Name'] == required]
    if len(matches) != 1:
        raise ValueError('required Census benchmark/vintage unavailable or ambiguous')
    return str(matches[0]['id'])


def choose_options(benchmarks: dict, vintages: dict) -> dict:
    return {'benchmark_name': BENCHMARK,
            'benchmark_id': _option(benchmarks, 'benchmark', BENCHMARK),
            'vintage_name': VINTAGE,
            'vintage_id': _option(vintages, 'vintage', VINTAGE)}


def _json(file: Path) -> dict:
    try:
        value = json.loads(file.read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise ValueError('expected JSON object')
        return value
    except (ValueError, UnicodeError):
        raise ValueError(f'{file}: invalid acquisition JSON') from None


def _checked_preparation(data_dir: Path, run_id: str) -> PreparedInputs:
    try:
        return check_preparation(data_dir, run_id)
    except (ValueError, OSError):
        raise ValueError(f'{run_id}: frozen preparation validation failed') from None


def _root(data_dir: Path, prepared: PreparedInputs) -> Path:
    return data_dir / 'raw/references/census-geocoder/ita-assignment' / prepared.directory.name


def _citation(data_dir: Path, file: Path) -> dict:
    try:
        gr.safe_path(file, data_dir)
        entry = manifest.entry_for(paths.manifest_path(data_dir), file)
        return json.loads(json.dumps(asdict(entry)))
    except (KeyError, OSError, ValueError):
        raise ValueError(f'{file}: missing, unrecorded or changed acquisition artifact') from None


def _batch_ids(prepared: PreparedInputs) -> dict[Path, list[str]]:
    requests = pl.read_parquet(prepared.request_index)
    limit = prepared.inputs['batch_limit']
    return {file: validate_batch(file, requests.slice(index * limit, limit))
            for index, file in enumerate(prepared.batches)}


def batch_receipt(prepared: PreparedInputs, request: Path, selection: Path,
                  options: dict, response_entry: dict) -> dict:
    index = prepared.batches.index(request)
    limit = prepared.inputs['batch_limit']
    expected = pl.scan_parquet(prepared.request_index).slice(index * limit, limit).collect()
    expected_ids = validate_batch(request, expected)
    return {
        'schema_version': 'ita-assignment-receipt-v1',
        'assignment_run_id': prepared.directory.name,
        'preparation_outputs_sha256': manifest.sha256_file(prepared.directory / 'outputs.json'),
        'request': {'path': request.relative_to(prepared.directory).as_posix(),
                    **target_io.file_record(request), 'rows': len(expected_ids)},
        'selection_sha256': manifest.sha256_file(selection),
        'options': options, 'response': response_entry,
        'acquired_at': response_entry['retrieved_at'],
    }


def _preflight(data_dir: Path, prepared: PreparedInputs) -> tuple[dict, dict, list]:
    '''Validate all existing state before any client or recovery publication.'''
    try:
        return _inspect_existing(data_dir, prepared)
    except (ValueError, OSError) as error:
        raise ValueError(f'{_root(data_dir, prepared)}: {error}') from None


def _inspect_existing(data_dir: Path, prepared: PreparedInputs) -> tuple[dict, dict, list]:
    root = _root(data_dir, prepared)
    gr.safe_path(root, data_dir)
    gr.safe_path(paths.manifest_path(data_dir), data_dir)
    ids = _batch_ids(prepared)
    expected = {*CATALOGS, SELECTION, COMPLETION, START}
    for request in ids:
        digest = manifest.sha256_file(request)
        expected.update((digest + '.csv', digest + '.receipt.json'))
    prefix = root.relative_to(data_dir / 'raw').as_posix() + '/'
    recorded = [entry for entry in manifest.read_manifest(paths.manifest_path(data_dir))
                if entry.path.startswith(prefix)]
    present = set(root.iterdir()) if root.exists() else set()
    present.update(data_dir / 'raw' / entry.path for entry in recorded)
    citations = {}
    for file in sorted(present):
        if file.parent != root or file.name not in expected or not file.is_file():
            raise ValueError(f'{file}: unexpected or incomplete acquisition artifact')
        citations[file.name] = _citation(data_dir, file)
    if citations and START not in citations:
        raise ValueError(f'{root / START}: missing acquisition start')
    if START in citations:
        start = _json(root / START)
        expected_start = _start_record(prepared, start.get('acquisition_started_at'))
        try:
            started = datetime.fromisoformat(start['acquisition_started_at'])
            if started.tzinfo is None or start != expected_start:
                raise ValueError('invalid start')
        except (KeyError, TypeError, ValueError):
            raise ValueError(f'{root / START}: invalid acquisition start') from None
    benchmark_id = None
    if CATALOGS[0] in citations:
        benchmark_id = _option(_json(root / CATALOGS[0]), 'benchmark', BENCHMARK)
    if CATALOGS[1] in citations:
        if benchmark_id is None:
            raise ValueError(f'{root}: vintage catalog without benchmark catalog')
        _option(_json(root / CATALOGS[1]), 'vintage', VINTAGE)
    for name, entry in citations.items():
        if name in CATALOGS or name.endswith('.csv'):
            url = GEOCODER + ('/benchmarks' if name == CATALOGS[0] else
                              f'/vintages?benchmark={benchmark_id}' if name == CATALOGS[1]
                              else '/geographies/addressbatch')
            if entry['client'] != 'httpx' or entry['source_url'] != url:
                raise ValueError(f'{root / name}: acquisition source identity differs')
        elif entry['client'] != METADATA_CLIENT or entry['source_url'] is not None:
            raise ValueError(f'{root / name}: generated metadata identity differs')
    selection = {}
    if SELECTION in citations:
        if not all(name in citations for name in CATALOGS):
            raise ValueError(f'{root}: selection requires original catalogs')
        selection = _json(root / SELECTION)
        options = choose_options(*[_json(root / name) for name in CATALOGS])
        expected_selection = {
            'schema_version': 'ita-assignment-selection-v1',
            'assignment_run_id': prepared.directory.name,
            'preparation_outputs_sha256': manifest.sha256_file(
                prepared.directory / 'outputs.json'),
            'catalogs': [citations[name] for name in CATALOGS], 'options': options,
            'acquisition_started_at': _json(root / START)['acquisition_started_at'],
        }
        if selection != expected_selection:
            raise ValueError(f'{root / SELECTION}: frozen selection differs')
    batches = []
    for request, expected_ids in ids.items():
        digest = manifest.sha256_file(request)
        response, receipt = root / (digest + '.csv'), root / (digest + '.receipt.json')
        frame = None
        if response.name in citations:
            if not selection:
                raise ValueError(f'{response}: response without frozen selection')
            try:
                frame = parse_response(response.read_text(encoding='utf-8'), expected_ids)
            except (ValueError, UnicodeError):
                raise ValueError(f'{response}: invalid response for frozen batch') from None
        if receipt.name in citations:
            if frame is None:
                raise ValueError(f'{receipt}: receipt without original response')
            expected_receipt = batch_receipt(prepared, request, root / SELECTION,
                                             selection['options'], citations[response.name])
            if _json(receipt) != expected_receipt:
                raise ValueError(f'{receipt}: receipt differs from frozen batch evidence')
        batches.append((request, expected_ids, response, receipt, frame))
    return citations, selection, batches


def _publish(data_dir: Path, file: Path, body: bytes, *, url: str | None = None) -> None:
    gr.safe_path(file, data_dir)
    if gr.occupied(file):
        raise ValueError(f'{file}: occupied acquisition destination')
    file.parent.mkdir(parents=True, exist_ok=True)
    partial = file.with_name(file.name + '.part')
    with partial.open('xb') as stream:
        stream.write(body)
    gr.safe_path(file, data_dir)
    os.link(partial, file)
    partial.unlink()
    if url is not None:
        record_download(paths.manifest_path(data_dir), file, url)
    else:
        entry = manifest.describe_file(
            file, data_dir / 'raw', retrieved_at=datetime.now(UTC),
            client=METADATA_CLIENT, client_version=version('embedding-data'))
        manifest.append_entries(paths.manifest_path(data_dir), [entry])


def _publish_json(data_dir: Path, file: Path, value: dict) -> None:
    body = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                       allow_nan=False) + '\n').encode('utf-8')
    _publish(data_dir, file, body)


def _body(response, file: Path) -> bytes:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise httpx.HTTPStatusError(
            f'{file}: Census HTTP status {response.status_code}',
            request=error.request, response=error.response) from None
    body = response.read()
    length = response.headers.get('Content-Length')
    downloaded = response.num_bytes_downloaded or len(body)
    if length is not None and (not length.isdecimal() or downloaded != int(length)):
        raise ValueError(f'{file}: response Content-Length differs')
    return body


def _start_record(prepared, timestamp):
    return {
        'schema_version': 'ita-assignment-start-v1',
        'assignment_run_id': prepared.directory.name,
        'preparation_outputs_sha256': manifest.sha256_file(prepared.directory / 'outputs.json'),
        'acquisition_started_at': timestamp,
    }


def _acquire_selection(data_dir, prepared, client, citations):
    root = _root(data_dir, prepared)
    for name in CATALOGS:
        if name in citations:
            continue
        url = GEOCODER + '/benchmarks'
        if name == CATALOGS[1]:
            identifier = _option(_json(root / CATALOGS[0]), 'benchmark', BENCHMARK)
            url = GEOCODER + f'/vintages?benchmark={identifier}'
        file = root / name
        try:
            with client.stream('GET', url) as response:
                body = _body(response, file)
        except httpx.TransportError:
            raise httpx.TransportError(f'{file}: Census catalog transport failed') from None
        try:
            catalog = json.loads(body)
            _option(catalog, 'benchmark' if name == CATALOGS[0] else 'vintage',
                    BENCHMARK if name == CATALOGS[0] else VINTAGE)
        except (ValueError, UnicodeError):
            raise ValueError(f'{file}: invalid or ambiguous Census catalog') from None
        _publish(data_dir, file, body, url=url)
        citations[name] = _citation(data_dir, file)
    selection = {
        'schema_version': 'ita-assignment-selection-v1',
        'assignment_run_id': prepared.directory.name,
        'preparation_outputs_sha256': manifest.sha256_file(prepared.directory / 'outputs.json'),
        'catalogs': [citations[name] for name in CATALOGS],
        'options': choose_options(*[_json(root / name) for name in CATALOGS]),
        'acquisition_started_at': _json(root / START)['acquisition_started_at'],
    }
    _publish_json(data_dir, root / SELECTION, selection)
    return selection


def _inventory(prepared, citations, selection, batches) -> dict:
    times = [citations[response.name]['retrieved_at'] for _, _, response, _, _ in batches]
    return {
        'schema_version': 'ita-assignment-acquisition-v1',
        'assignment_run_id': prepared.directory.name,
        'preparation_outputs_sha256': manifest.sha256_file(prepared.directory / 'outputs.json'),
        'requests': sorted([
            {'path': request.relative_to(prepared.directory).as_posix(),
             **target_io.file_record(request), 'rows': len(ids)}
            for request, ids, _, _, _ in batches], key=lambda item: item['path']),
        'catalogs': [citations[name] for name in CATALOGS],
        'selection': citations[SELECTION], 'start': citations[START],
        'responses': sorted([citations[response.name] for _, _, response, _, _ in batches],
                            key=lambda item: item['path']),
        'receipts': sorted([citations[receipt.name] for _, _, _, receipt, _ in batches],
                           key=lambda item: item['path']),
        'options': selection['options'],
        'methods': {'request': 'POST', 'endpoint': GEOCODER + '/geographies/addressbatch',
                    'execution': 'sequential', 'timeout_seconds': 600},
        'acquisition_started_at': selection['acquisition_started_at'],
        'response_acquired_at_min': min(times), 'response_acquired_at_max': max(times),
        'current_frame_limit': CURRENT_FRAME_LIMIT,
    }


def _verify_completion(root, prepared, citations, selection, batches):
    if COMPLETION not in citations:
        raise ValueError(f'{root / COMPLETION}: missing completed acquisition inventory')
    if any(frame is None or receipt.name not in citations
           for _, _, _, receipt, frame in batches):
        raise ValueError(f'{root / COMPLETION}: incomplete batch evidence')
    completion = _json(root / COMPLETION)
    end = completion.get('acquisition_completed_at')
    try:
        ended = datetime.fromisoformat(end)
        if (ended.tzinfo is None or ended < datetime.fromisoformat(
                max(citations[response.name]['retrieved_at']
                    for _, _, response, _, _ in batches))):
            raise ValueError('invalid completion time')
    except (TypeError, ValueError):
        raise ValueError(f'{root / COMPLETION}: invalid completion time') from None
    expected = _inventory(prepared, citations, selection, batches)
    expected['acquisition_completed_at'] = end
    if completion != expected:
        raise ValueError(f'{root / COMPLETION}: completion inventory differs')
    return completion


def acquire(data_dir: Path, assignment_run_id: str) -> Path:
    prepared = _checked_preparation(data_dir, assignment_run_id)
    root = _root(data_dir, prepared)
    citations, selection, batches = _preflight(data_dir, prepared)
    if COMPLETION in citations:
        _verify_completion(root, prepared, citations, selection, batches)
        return root / COMPLETION
    if START not in citations:
        _publish_json(data_dir, root / START, _start_record(
            prepared, datetime.now(UTC).isoformat(timespec='seconds')))
    # Receipt recovery uses only verified originals and never changes retrieval times.
    for request, _, response, receipt, frame in batches:
        if frame is not None and receipt.name not in citations:
            _publish_json(data_dir, receipt, batch_receipt(
                prepared, request, root / SELECTION, selection['options'],
                citations[response.name]))
    if not selection or any(frame is None for _, _, _, _, frame in batches):
        with make_client() as client:
            if not selection:
                selection = _acquire_selection(data_dir, prepared, client, citations)
            for request, expected_ids, response_file, receipt, frame in batches:
                if frame is not None:
                    continue
                url = GEOCODER + '/geographies/addressbatch'
                options = {'benchmark': selection['options']['benchmark_id'],
                           'vintage': selection['options']['vintage_id']}
                try:
                    with request.open('rb') as stream:
                        files = {'addressFile': (request.name, stream, 'text/csv')}
                        with client.stream('POST', url, files=files, data=options) as reply:
                            body = _body(reply, response_file)
                except httpx.TransportError:
                    raise httpx.TransportError(
                        f'{response_file}: Census batch transport failed') from None
                try:
                    parse_response(body.decode('utf-8'), expected_ids)
                except (ValueError, UnicodeError):
                    raise ValueError(
                        f'{response_file}: invalid response for frozen batch') from None
                _publish(data_dir, response_file, body, url=url)
                entry = _citation(data_dir, response_file)
                _publish_json(data_dir, receipt, batch_receipt(
                    prepared, request, root / SELECTION, selection['options'], entry))
    prepared = _checked_preparation(data_dir, assignment_run_id)
    citations, selection, batches = _preflight(data_dir, prepared)
    completion = _inventory(prepared, citations, selection, batches)
    completion['acquisition_completed_at'] = datetime.now(UTC).isoformat(timespec='seconds')
    _publish_json(data_dir, root / COMPLETION, completion)
    read_evidence(data_dir, prepared)
    return root / COMPLETION


def read_evidence(data_dir: Path, prepared: PreparedInputs) -> Evidence:
    checked = _checked_preparation(data_dir, prepared.directory.name)
    if checked.directory != prepared.directory or checked.inputs != prepared.inputs:
        raise ValueError(f'{prepared.directory}: supplied preparation differs from frozen run')
    citations, selection, batches = _preflight(data_dir, checked)
    provenance = _verify_completion(
        _root(data_dir, checked), checked, citations, selection, batches)
    frames = [frame.lazy() for _, _, _, _, frame in batches]
    responses = pl.concat(frames)
    expected_ids = pl.read_parquet(checked.request_index)['request_id']
    actual_ids = responses.select('request_id').collect()['request_id']
    if len(actual_ids) != len(expected_ids) or set(actual_ids) != set(expected_ids):
        raise ValueError(f'{checked.directory}: response union differs from distinct requests')
    provenance = {**provenance, 'completion': citations[COMPLETION],
                  'raw': sorted(citations.values(), key=lambda item: item['path'])}
    return Evidence(responses, provenance, data_dir, checked)
