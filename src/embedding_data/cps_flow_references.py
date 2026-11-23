'''Stage 11 reference snapshot: public originals for CPS industry 9890 and occupation 9840.

One immutable snapshot of seven public originals sits under
`raw/references/cps-job-flows/<REFERENCE_ID>/`, with a receipt and manifest entries. Acquisition
and import share one staging directory and one state file, so an owner download can finish a
snapshot that an acquisition began. Each original must carry the rows or anchors that name the
two specials with their labels. A changed original fails and needs a fresh reference ID.
'''

import csv
import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import fastexcel
import httpx

from embedding_data import geography_references as gr
from embedding_data import manifest, paths, target_io
from embedding_data.osha_benchmark_download import USER_AGENT

PARSER_VERSION = 'cps-job-flows-references-v1'
MAX_ORIGINAL_BYTES = 32 * 1024 * 1024
STATE_FILE = 'staging-state.json'
RECEIPT_FILE = 'receipt.json'
SNAPSHOT_ROOT = 'raw/references/cps-job-flows'

SPECIAL_LABEL = 'Armed Forces'
BLS_LABEL = 'Armed Forces (last job)'
INDUSTRY_SPECIAL = '9890'
OCCUPATION_SPECIAL = '9840'
# Census 2026 basic lists drop the military recodes that the ASEC lists still carry.
RETIRED_INDUSTRY_CODES = frozenset(
    ('9670', '9680', '9690', '9770', '9780', '9790', '9870'))
RETIRED_OCCUPATION_CODES = frozenset(f'{code:04d}' for code in range(9800, 9831))
BLS_PARTNERS = {INDUSTRY_SPECIAL: 'Part of 92811', OCCUPATION_SPECIAL: '55-0000'}


@dataclass(frozen=True)
class Reference:
    url: str
    filename: str


_CENSUS_2026 = 'https://www2.census.gov/programs-surveys/cps/datasets/2026/basic/'
_CENSUS_2025 = 'https://www2.census.gov/programs-surveys/cps/datasets/2025/basic/'
_LAYOUT = '2025_Basic_CPS_Public_Use_Record_Layout_plus_IO_Code_list.txt'
_BLS_INDUSTRY = '2022-census-industry-titles-and-code-list.xlsx'
_BLS_OCCUPATION = '2018-census-occupation-classification-titles-and-code-list.xlsx'

REGISTRY = {
    'cps_basic_2026_industry_codes': Reference(
        _CENSUS_2026 + 'cps_industry_codes.csv', 'cps_industry_codes.csv'),
    'cps_basic_2026_occupation_codes': Reference(
        _CENSUS_2026 + 'cps_occupation_codes.csv', 'cps_occupation_codes.csv'),
    'cps_basic_2025_layout_codes': Reference(_CENSUS_2025 + _LAYOUT, _LAYOUT),
    'bls_cps_industry_2022': Reference('https://www.bls.gov/cps/' + _BLS_INDUSTRY,
                                       _BLS_INDUSTRY),
    'bls_cps_occupation_2018': Reference('https://www.bls.gov/cps/' + _BLS_OCCUPATION,
                                         _BLS_OCCUPATION),
    'ipums_cps_ind_2020_codes': Reference('https://cps.ipums.org/cps/codes/ind_2020_codes.shtml',
                                          'ind_2020_codes.shtml'),
    'ipums_cps_occ_2020_codes': Reference('https://cps.ipums.org/cps/codes/occ_2020_codes.shtml',
                                          'occ_2020_codes.shtml'),
}


def _fail(kind: str, reason: str) -> ValueError:
    return ValueError(f'{kind}: {reason}')


def _read_text(kind: str, file: Path, encoding: str) -> str:
    try:
        return file.read_text(encoding=encoding)
    except UnicodeDecodeError as error:
        raise _fail(kind, 'original is not decodable text') from error


def _validate_code_csv(kind, file, *, code_column, text_column, token_column, special,
                       retired):
    required = ['ROW_TYPE', code_column, text_column, token_column]
    try:
        with file.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            header = reader.fieldnames or []
            rows = list(reader)
    except (UnicodeDecodeError, csv.Error) as error:
        raise _fail(kind, 'original is not a readable CSV') from error
    if any(header.count(name) != 1 for name in required):
        raise _fail(kind, 'required CSV header columns differ')

    def cell(row, name):
        return (row.get(name) or '').strip()

    if any(cell(row, code_column) in retired for row in rows):
        raise _fail(kind, 'a retired military recode is listed')
    details = [row for row in rows
               if cell(row, 'ROW_TYPE') == 'detail' and cell(row, code_column) == special]
    if not details or any(
            cell(row, text_column) != SPECIAL_LABEL or cell(row, token_column)
            for row in details):
        raise _fail(kind, f'special {special} row, label or empty code cell differs')


def _validate_layout(kind, file):
    text = _read_text(kind, file, 'latin-1')
    lines = text.splitlines()
    if not any(re.search(rf'{SPECIAL_LABEL}\t+{INDUSTRY_SPECIAL}', line) for line in lines):
        raise _fail(kind, f'layout line for {INDUSTRY_SPECIAL} differs')
    if not any(re.match(rf'{OCCUPATION_SPECIAL}\t+{SPECIAL_LABEL}', line) for line in lines):
        raise _fail(kind, f'layout line for {OCCUPATION_SPECIAL} differs')


def _workbook_sheets(kind, file):
    try:
        workbook = fastexcel.read_excel(file)
        return [workbook.load_sheet(name, header_row=None, dtypes='string').to_polars()
                for name in workbook.sheet_names]
    except Exception as error:
        raise _fail(kind, 'original is not a readable workbook') from error


def _validate_workbook(kind, file, special):
    partner = BLS_PARTNERS[special]
    for sheet in _workbook_sheets(kind, file):
        for row in sheet.iter_rows():
            cells = [value.strip() for value in row if isinstance(value, str)]
            if (special in cells and any(c.startswith(BLS_LABEL) for c in cells)
                    and any(partner in c for c in cells)):
                return
    raise _fail(kind, f'no workbook row holds {special}, {BLS_LABEL!r} and {partner!r}')


def _validate_page(kind, file, special):
    text = _read_text(kind, file, 'utf-8')
    pattern = rf'<dt>\s*{special}\s*</dt>\s*<dd>\s*{SPECIAL_LABEL}\s*</dd>'
    if not re.search(pattern, text):
        raise _fail(kind, f'definition for {special} differs')


def validate_original(kind: str, file: Path) -> None:
    '''Raise ValueError unless the original carries its special rows or anchors.'''
    file = Path(file)
    if kind == 'cps_basic_2026_industry_codes':
        _validate_code_csv(
            kind, file, code_column='2022 Industry Code',
            text_column='Industry 2025 Description', token_column='2022 NAICS Code',
            special=INDUSTRY_SPECIAL, retired=RETIRED_INDUSTRY_CODES)
    elif kind == 'cps_basic_2026_occupation_codes':
        _validate_code_csv(
            kind, file, code_column='2020 Census Public Use Occupation Code',
            text_column='Description (2020 Census Occupation Code)',
            token_column='2018 SOC Code', special=OCCUPATION_SPECIAL,
            retired=RETIRED_OCCUPATION_CODES)
    elif kind == 'cps_basic_2025_layout_codes':
        _validate_layout(kind, file)
    elif kind == 'bls_cps_industry_2022':
        _validate_workbook(kind, file, INDUSTRY_SPECIAL)
    elif kind == 'bls_cps_occupation_2018':
        _validate_workbook(kind, file, OCCUPATION_SPECIAL)
    elif kind == 'ipums_cps_ind_2020_codes':
        _validate_page(kind, file, INDUSTRY_SPECIAL)
    elif kind == 'ipums_cps_occ_2020_codes':
        _validate_page(kind, file, OCCUPATION_SPECIAL)
    else:
        raise ValueError('unknown registered public source identity')


def make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    '''A client that follows no redirect and reads no proxy or credential setting.'''
    return httpx.Client(timeout=60, follow_redirects=False, trust_env=False,
                        headers={'User-Agent': USER_AGENT}, transport=transport)


def _snapshot_paths(data_dir, reference_id):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', reference_id):
        raise ValueError('unsafe reference snapshot ID')
    root = data_dir / SNAPSHOT_ROOT
    final, staging = root / reference_id, root / (reference_id + '.part')
    for file in (paths.manifest_path(data_dir), final, staging):
        gr.safe_path(file, data_dir)
    return final, staging


def _filenames():
    return {reference.filename for reference in REGISTRY.values()}


def _require_unrecorded_snapshot(data_dir, final):
    manifest_file = paths.manifest_path(data_dir)
    expected = {(final / name).relative_to(manifest_file.parent).as_posix()
                for name in _filenames() | {RECEIPT_FILE}}
    recorded = {entry.path for entry in manifest.read_manifest(manifest_file)}
    if expected & recorded:
        raise ValueError(f'{final.name}: manifest-recorded reference paths require restoration; '
                         'use a fresh reference ID')


def _request_record(kind, retrieved_at, *, imported):
    return {'source_url': REGISTRY[kind].url, 'method': 'GET', 'retrieved_at': retrieved_at,
            'retrieved_at_is_proxy': imported}


def _verify_requests(originals):
    for kind, record in originals.items():
        proxy = record.get('retrieved_at_is_proxy')
        if not isinstance(proxy, bool):
            raise ValueError('unknown reference retrieval-time proxy flag')
        expected = _request_record(kind, record.get('retrieved_at'), imported=proxy)
        if any(record.get(key) != value for key, value in expected.items()):
            raise ValueError('reference URL or method identity differs')
        try:
            timestamp = datetime.fromisoformat(record['retrieved_at'])
            if timestamp.tzinfo is None:
                raise ValueError('reference retrieval time must be timezone-aware')
        except (TypeError, ValueError) as error:
            raise ValueError('invalid reference retrieval time') from error


def _now():
    return datetime.now(UTC).isoformat(timespec='seconds')


def _save_state(staging, kinds):
    target_io.write_json(staging / STATE_FILE, {'parser_version': PARSER_VERSION, 'kinds': kinds})


def _load_staging(data_dir, staging):
    '''Verify an owned staging directory and return its per-kind records.'''
    state_file = staging / STATE_FILE
    if not state_file.is_file():
        raise ValueError('occupied incomplete snapshot has no staging state; '
                         'use a fresh reference ID')
    for file in staging.rglob('*'):
        gr.safe_path(file, data_dir)
    state = json.loads(state_file.read_text(encoding='utf-8'))
    kinds = state.get('kinds')
    if state.get('parser_version') != PARSER_VERSION or not isinstance(kinds, dict):
        raise ValueError('incomplete snapshot state identity differs')
    if not set(kinds).issubset(REGISTRY):
        raise ValueError('unknown identity in incomplete snapshot')
    names = {REGISTRY[kind].filename for kind in kinds}
    if {file.name for file in staging.iterdir()} != names | {STATE_FILE}:
        raise ValueError('unmanifested or missing staging files')
    _verify_requests({kind: item.get('request', {}) for kind, item in kinds.items()})
    for kind, item in kinds.items():
        file = staging / REGISTRY[kind].filename
        if target_io.file_record(file) != item.get('file'):
            raise ValueError('previously staged original changed')
        validate_original(kind, file)
    return kinds


def _open_staging(data_dir, final, staging):
    if gr.occupied(staging):
        return staging, _load_staging(data_dir, staging)
    _, staging = target_io.stage(final.parent, final.name, data_dir)
    _save_state(staging, {})
    return staging, {}


def _write_exclusive(file, body):
    with file.open('xb') as output:
        output.write(body)


def _publish(data_dir, reference_id, staging, kinds):
    originals = {kind: dict(item['request']) for kind, item in kinds.items()}
    _verify_requests(originals)
    for kind in originals:
        validate_original(kind, staging / REGISTRY[kind].filename)
    final, _ = _snapshot_paths(data_dir, reference_id)
    files = {name: target_io.file_record(staging / name) for name in sorted(_filenames())}
    raw_root = paths.manifest_path(data_dir).parent
    entries = []
    for kind, record in originals.items():
        reference = REGISTRY[kind]
        imported = record['retrieved_at_is_proxy']
        entry = manifest.describe_file(
            staging / reference.filename, staging,
            retrieved_at=datetime.fromisoformat(record['retrieved_at']),
            client='manual-import' if imported else 'httpx',
            client_version=version('embedding-data') if imported else version('httpx'),
            source_url=reference.url, proxies=('retrieved_at',) if imported else ())
        entry = manifest.ManifestEntry(**{**asdict(entry), 'path': (
            final / reference.filename).relative_to(raw_root).as_posix()})
        entries.append(entry)
        record['citation'] = json.loads(json.dumps(asdict(entry)))
    manifest.check_appendable(paths.manifest_path(data_dir), entries)
    receipt = {'reference_id': reference_id, 'parser_version': PARSER_VERSION,
               'originals': originals, 'files': files,
               'raw_citations': json.loads(json.dumps([asdict(entry) for entry in entries]))}
    final.mkdir()  # An occupied destination must never be replaced, even by an empty directory.
    for name in sorted(files):
        with (staging / name).open('rb') as source, (final / name).open('xb') as output:
            shutil.copyfileobj(source, output)
        if target_io.file_record(final / name) != files[name]:
            raise ValueError('original changed during publication')
    manifest.append_entries(paths.manifest_path(data_dir), entries)
    receipt_file = final / RECEIPT_FILE
    _write_exclusive(receipt_file, (json.dumps(
        receipt, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
    # The generated receipt is externally manifested, never self-inventoried.
    receipt_entry = manifest.describe_file(
        receipt_file, raw_root, retrieved_at=datetime.now(UTC), client='embedding-data',
        client_version=version('embedding-data'))
    manifest.append_entries(paths.manifest_path(data_dir), [receipt_entry])
    for file in staging.iterdir():
        file.unlink()
    staging.rmdir()
    check_references(data_dir, reference_id)
    return final


def check_references(data_dir: Path, reference_id: str) -> dict:
    '''Verify a published snapshot against its receipt and the manifest; return the receipt.'''
    data_dir = Path(data_dir)
    final, staging = _snapshot_paths(data_dir, reference_id)
    if gr.occupied(staging) or not (final / RECEIPT_FILE).is_file():
        raise ValueError('incomplete or occupied reference snapshot')
    for file in final.rglob('*'):
        gr.safe_path(file, data_dir)
    receipt_file = final / RECEIPT_FILE
    receipt_entry = manifest.entry_for(paths.manifest_path(data_dir), receipt_file)
    if (receipt_entry.source_url is not None or receipt_entry.client != 'embedding-data'
            or receipt_entry.proxies):
        raise ValueError('generated reference receipt provenance differs')
    receipt = json.loads(receipt_file.read_text(encoding='utf-8'))
    if (receipt.get('reference_id') != reference_id
            or receipt.get('parser_version') != PARSER_VERSION
            or set(receipt.get('originals', {})) != set(REGISTRY)):
        raise ValueError('reference receipt identity or parser version differs')
    names = _filenames()
    actual = {file.relative_to(final).as_posix() for file in final.rglob('*') if file.is_file()}
    if actual != names | {RECEIPT_FILE} or set(receipt['files']) != names:
        raise ValueError('missing or extra reference inventory files')
    for name in sorted(names):
        if target_io.file_record(target_io.relative_file(final, name)) != receipt['files'][name]:
            raise ValueError('reference inventory hash or size differs')
    citations = target_io.verify_raw(data_dir, receipt['raw_citations'])
    by_path = {entry['path']: entry for entry in citations}
    raw_root = paths.manifest_path(data_dir).parent
    if set(by_path) != {(final / name).relative_to(raw_root).as_posix() for name in names}:
        raise ValueError('reference manifest inventory differs')
    _verify_requests(receipt['originals'])
    for kind, reference in REGISTRY.items():
        record = receipt['originals'][kind]
        citation = by_path[(final / reference.filename).relative_to(raw_root).as_posix()]
        if (record.get('citation') != citation or citation['source_url'] != reference.url
                or citation['retrieved_at'] != record['retrieved_at']
                or citation['proxies'] != (['retrieved_at'] if record[
                    'retrieved_at_is_proxy'] else [])):
            raise ValueError('reference retrieval provenance differs')
        validate_original(kind, final / reference.filename)
    return receipt


def _download(client, reference, file):
    with client.stream('GET', reference.url) as response:
        if not response.is_success:
            raise ValueError('public original was refused')
        length = response.headers.get('content-length')
        if length is not None and int(length) > MAX_ORIGINAL_BYTES:
            raise ValueError('public original exceeds download bound')
        size = 0
        with file.open('xb') as output:
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_ORIGINAL_BYTES:
                    raise ValueError('public original exceeds download bound')
                output.write(chunk)
        if (length is not None and not response.headers.get('content-encoding')
                and size != int(length)):
            raise ValueError('public original content length differs')


def acquire(data_dir: Path, reference_id: str) -> Path:
    '''Fetch every missing original, then publish when all seven are staged.

    A refused kind stays missing in the shared staging directory. The owner can import it with
    `import_reference`, or a later call can try again. An occupied final is verified, not replaced.
    '''
    data_dir = Path(data_dir)
    final, staging = _snapshot_paths(data_dir, reference_id)
    if gr.occupied(final):
        check_references(data_dir, reference_id)
        return final
    _require_unrecorded_snapshot(data_dir, final)
    staging, kinds = _open_staging(data_dir, final, staging)
    missing = [kind for kind in REGISTRY if kind not in kinds]
    refused = []
    if missing:
        with make_client() as client:
            for kind in missing:
                file = staging / REGISTRY[kind].filename
                try:
                    _download(client, REGISTRY[kind], file)
                    validate_original(kind, file)
                except (httpx.HTTPError, ValueError):
                    file.unlink(missing_ok=True)
                    refused.append(kind)
                    continue
                kinds[kind] = {'request': _request_record(kind, _now(), imported=False),
                               'file': target_io.file_record(file)}
                _save_state(staging, kinds)
    if refused:
        raise ValueError('refused: ' + ', '.join(refused))
    return _publish(data_dir, reference_id, staging, kinds)


def import_reference(data_dir: Path, reference_id: str, kind: str, original: Path) -> Path:
    '''Register one owner-downloaded original, with the import time flagged as a proxy.

    Returns the staging directory until all seven originals are present, then the snapshot.
    '''
    data_dir, original = Path(data_dir), Path(original)
    if kind not in REGISTRY:
        raise ValueError('unknown registered public source identity')
    if original.is_symlink() or any(parent.is_symlink() for parent in original.parents):
        raise ValueError('import source contains a symlink')
    if not original.is_file() or original.stat().st_size > MAX_ORIGINAL_BYTES:
        raise ValueError('import source missing or exceeds size bound')
    final, staging = _snapshot_paths(data_dir, reference_id)
    if gr.occupied(final):
        raise ValueError('occupied snapshot; completed references are immutable')
    _require_unrecorded_snapshot(data_dir, final)
    validate_original(kind, original)
    staging, kinds = _open_staging(data_dir, final, staging)
    if kind in kinds:
        raise ValueError('source identity already staged; originals are immutable')
    file = staging / REGISTRY[kind].filename
    with original.open('rb') as source, file.open('xb') as output:
        shutil.copyfileobj(source, output)
    validate_original(kind, file)
    kinds[kind] = {'request': _request_record(kind, _now(), imported=True),
                   'file': target_io.file_record(file)}
    _save_state(staging, kinds)
    if set(kinds) == set(REGISTRY):
        return _publish(data_dir, reference_id, staging, kinds)
    return staging


def special_evidence(receipt: dict) -> dict[str, dict]:
    '''Evidence status of the two specials by file, from a verified receipt.'''
    if (receipt.get('parser_version') != PARSER_VERSION
            or set(receipt.get('originals', {})) != set(REGISTRY)):
        raise ValueError('reference receipt identity or parser version differs')
    return {
        INDUSTRY_SPECIAL: {
            'label': SPECIAL_LABEL, 'monthly': 'settled',
            'asec_current': 'unresolved_owner_decision',
            'asec_last_year': 'unresolved_owner_decision', 'bls': 'pt. 92811'},
        OCCUPATION_SPECIAL: {
            'label': SPECIAL_LABEL, 'monthly': 'settled', 'asec_current': 'settled',
            'asec_last_year': 'settled', 'bls': '55-0000'},
    }
