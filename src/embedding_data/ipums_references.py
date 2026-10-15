'''Explicit public evidence snapshots and strict offline Stage 7 source parsers.'''

import csv
import json
import math
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from importlib.metadata import version
from pathlib import Path

import fastexcel
import httpx
import polars as pl

from embedding_data import geography_references as gr
from embedding_data import ipums_census_access, manifest, paths, target_io
from embedding_data.geography_parsers import SCOPE as ACS_COMPARISON_STATES
from embedding_data.osha_benchmark_download import USER_AGENT

PARSER_VERSION = 'ipums-public-references-v2'
MAX_ORIGINAL_BYTES = 32 * 1024 * 1024
BLS_SERIES = 'LNU02000000'
BLS_REQUEST_BODY = b'{"seriesid":["LNU02000000"],"startyear":"2025","endyear":"2026"}'
SELECTED_MONTHS = frozenset(
    (year, month) for year, last in ((2025, 12), (2026, 9))
    for month in range(1, last + 1) if (year, month) != (2025, 10))
INDUSTRY_SHEETS = {2017: '2017 Census Industry Code List', 2022: '2022 Census Ind Code List '}
SPECIAL_INDUSTRY_CODES = {
    '9920': 'Unemployed, last worked 5 years ago or earlier or never worked'}


@dataclass(frozen=True)
class Reference:
    url: str
    filename: str
    method: str = 'GET'
    request_body: bytes | None = None
    sha256: str | None = None


REGISTRY = {
    'usa_samples': Reference('https://usa.ipums.org/usa-action/samples/sample_ids',
                             'usa_samples.html'),
    'census_industry_2017': Reference(
        'https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/'
        '2017-industry-code-list-with-crosswalk.xlsx', 'census_industry_2017.xlsx',
        sha256='479161190aedc0a64529f930d34a21f18e1950609332defe4967e4e3f129c816'),
    'census_industry_2022': Reference(
        'https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/'
        '2022-Census-Industry-Code-List-with-Crosswalk.xlsx', 'census_industry_2022.xlsx',
        sha256='c9d2e004b2735c3975f0768e7dac704df6d2e0b36b24d33f5dbc7109cab5628c'),
    **{f'acs_{year}_employment': Reference(
        f'https://api.census.gov/data/{year}/acs/acs1?get=NAME,B23025_004E&for=state:*',
        f'acs_{year}_employment.json') for year in (2023, 2024)},
    'bls_series_metadata': Reference('https://download.bls.gov/pub/time.series/ln/ln.series',
                                     'bls_series_metadata.txt'),
    'bls_a1_metadata': Reference('https://www.bls.gov/news.release/empsit.t01.htm',
                                 'bls_a1_metadata.html'),
    'cps_employment': Reference('https://api.bls.gov/publicAPI/v1/timeseries/data/',
                                'cps_employment.json', 'POST', BLS_REQUEST_BODY),
    'asec_2025_documentation': Reference(
        'https://www2.census.gov/programs-surveys/cps/techdocs/cpsmar25.pdf',
        'asec_2025_documentation.pdf',
        sha256='7f0cb9f791f2737ad12fd552b8cb201f4d1de266eac160322597344e73499fb4'),
    'asec_2026_documentation': Reference(
        'https://www2.census.gov/programs-surveys/cps/techdocs/cpsmar26.pdf',
        'asec_2026_documentation.pdf',
        sha256='8f6d4c10ae5e720449ae23fdf739bb7812aff8102218d7c013be8ce737125107'),
    **{f'usa_{name.lower()}': Reference(f'https://usa.ipums.org/usa-action/variables/{name}',
                                      f'usa_{name.lower()}.html')
       for name in ('PERWT', 'REPWTP')},
    **{f'cps_{name.lower()}': Reference(f'https://cps.ipums.org/cps-action/variables/{name}',
                                      f'cps_{name.lower()}.html')
       for name in ('WTFINL', 'EARNWT', 'LNKFW1MWT', 'ASECWT', 'REPWTP', 'IND', 'INDLY',
                    'UH_IND_A10', 'UH_INDLYR_A10', 'EMPSAME', 'ACTSAME')},
    **{f'acs_{year}_b23025_metadata': Reference(
        f'https://api.census.gov/data/{year}/acs/acs1/groups/B23025.html',
        f'acs_{year}_b23025_metadata.html') for year in (2023, 2024)},
}


class PublicHTML(HTMLParser):
    '''Collect tables and text without executing scripts or loading remote assets.'''

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.text = []
        self.table = None
        self.row = None
        self.cell = None
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            if self.table is not None:
                raise ValueError('nested public table')
            self.table = []
        elif tag == 'tr' and self.table is not None:
            self.row = []
        elif tag in ('th', 'td') and self.row is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if tag in ('th', 'td') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == 'table' and self.table is not None:
            self.tables.append(self.table)
            self.table = None

    def handle_data(self, text):
        self.text.append(text)
        if self.cell is not None:
            self.cell.append(text)


def parse_sample_catalog(file: Path) -> dict[str, str]:
    html = PublicHTML(file.read_text(encoding='utf-8'))
    tables = [t for t in html.tables if t and t[0] == ['Sample ID', 'Description']]
    if len(tables) != 1:
        raise ValueError('public sample catalog requires Sample ID / Description headers')
    result = {}
    for row in tables[0][1:]:
        if (len(row) != 2 or not re.fullmatch(r'us\d{4}[a-z]+', row[0]) or not row[1]
                or row[0] in result):
            raise ValueError('invalid or duplicate public sample ID/description')
        result[row[0]] = row[1]
    if not result:
        raise ValueError('empty public sample catalog')
    return result


def _industry_rows(file, vintage):
    if vintage not in INDUSTRY_SHEETS:
        raise ValueError('unsupported Census industry vintage')
    try:
        workbook = fastexcel.read_excel(file)
        sheet = INDUSTRY_SHEETS[vintage]
        if sheet not in workbook.sheet_names:
            raise ValueError('required Census industry sheet/vintage absent')
        frame = workbook.load_sheet(sheet, header_row=None, dtypes='string').to_polars()
    except Exception as error:
        raise ValueError('invalid Census industry workbook or sheet identity') from error
    code_header = '2017 Census Code' if vintage == 2017 else '2022 Census Industry Code'
    title_header = f'Industry {vintage} Description'
    expected = [title_header, code_header, f'{vintage} NAICS Code']
    headers = [(i, row) for i, row in enumerate(frame.iter_rows())
               if all(value in row for value in expected)]
    if len(headers) != 1:
        raise ValueError('required unique Census industry headers/vintage absent')
    index, header = headers[0]
    if any(header.count(value) != 1 for value in expected):
        raise ValueError('ambiguous Census industry headers')
    body = frame.slice(index + 1).lazy()
    code_column = frame.columns[header.index(code_header)]
    title_column = frame.columns[header.index(title_header)]
    # Both official sheets repeat code 0770 in a Construction section heading.
    construction_heading = (
        (pl.col(frame.columns[0]).str.strip_chars() == 'Construction')
        & pl.col(title_column).is_null()
        & (pl.col(code_column).str.strip_chars() == '0770')).fill_null(False)
    selected = body.filter(~construction_heading).select(
        pl.col(frame.columns[header.index(code_header)]).str.strip_chars().alias('code'),
        pl.col(frame.columns[header.index(title_header)]).str.strip_chars().alias('title'))
    selected = selected.filter(pl.col('code').is_not_null())
    supported_code = pl.col('code').str.contains(
        r'^(\d{4}|\d{4}-\d{4}(,\s*\d{4}-\d{4})*)$')
    invalid = selected.filter(~supported_code).collect()
    if invalid.height:
        raise ValueError('unsupported Census industry code form')
    leaves = selected.filter(pl.col('code').str.contains(r'^\d{4}$')).collect()
    if (not leaves.height or leaves['title'].null_count()
            or leaves.filter(pl.col('title') == '').height):
        raise ValueError('empty Census industry leaves or missing title')
    if leaves.lazy().group_by('code').agg(pl.col('title').n_unique()).filter(
            pl.col('title') != 1).collect().height:
        raise ValueError('conflicting duplicate Census industry labels')
    for code, title in leaves.iter_rows():
        if code in SPECIAL_INDUSTRY_CODES and title != SPECIAL_INDUSTRY_CODES[code]:
            raise ValueError('documented special industry label changed')
    return leaves.lazy().unique(maintain_order=True).collect()


def parse_industry_list(file: Path, vintage: int) -> pl.DataFrame:
    return _industry_rows(file, vintage).lazy().filter(
        ~pl.col('code').is_in(list(SPECIAL_INDUSTRY_CODES))).collect()


def parse_industry_metadata(file: Path, vintage: int) -> dict:
    special = _industry_rows(file, vintage).lazy().filter(
        pl.col('code').is_in(list(SPECIAL_INDUSTRY_CODES))).collect()
    codes = dict(special.iter_rows())
    if any(SPECIAL_INDUSTRY_CODES[code] != title for code, title in codes.items()):
        raise ValueError('documented special industry label changed')
    return {'vintage': vintage, 'special_codes': codes, 'sheet': INDUSTRY_SHEETS[vintage]}


def parse_acs_levels(file: Path, year: int) -> pl.DataFrame:
    '''Parse person counts; retain optional PR (72), outside ACS_COMPARISON_STATES.

    Source year is supplied from the canonical request/receipt, never inferred
    from this response body, which has no year field.
    '''
    if type(year) is not int or year not in (2023, 2024):
        raise ValueError('ACS levels require a registered 2023 or 2024 source year')
    try:
        response = json.loads(file.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError('invalid ACS levels response JSON') from error
    header = ['NAME', 'B23025_004E', 'state']
    if not isinstance(response, list) or not response or response[0] != header:
        raise ValueError('invalid ACS levels response structure/header')
    rows = response[1:]
    for row in rows:
        if (not isinstance(row, list) or len(row) != len(header)
                or any(not isinstance(value, str) for value in row)
                or not row[0].strip() or not re.fullmatch(r'[0-9]+', row[1])):
            raise ValueError('invalid ACS levels row/string/count format')
    states = [row[2] for row in rows]
    if (len(states) != len(set(states)) or not ACS_COMPARISON_STATES.issubset(states)
            or not set(states).issubset(ACS_COMPARISON_STATES | {'72'})):
        raise ValueError('ACS levels require unique 50-state/DC coverage with optional PR72')
    raw = pl.DataFrame(rows, schema={name: pl.String for name in header}, orient='row')
    try:
        levels = raw.lazy().select(
            pl.lit(year, dtype=pl.Int64).alias('year'),
            pl.col('state').alias('state_fips'),
            pl.col('B23025_004E').cast(pl.Float64).alias('published'),
            pl.lit('persons').alias('units')).collect()
    except pl.exceptions.PolarsError as error:
        raise ValueError('invalid ACS levels numeric representation') from error
    if not levels['published'].is_finite().all() or (levels['published'] < 0).any():
        raise ValueError('ACS levels must be finite nonnegative person counts')
    return levels


def _series_metadata(file):
    try:
        with file.open(encoding='utf-8', newline='') as stream:
            rows = list(csv.reader(stream, delimiter='\t'))
    except OSError as error:
        raise ValueError('missing frozen BLS series metadata') from error
    if not rows:
        raise ValueError('empty BLS series metadata')
    header = [cell.strip() for cell in rows[0]]
    required = ['series_id', 'periodicity_code', 'series_title', 'seasonal']
    if len(header) != len(set(header)) or not set(required).issubset(header):
        raise ValueError('BLS series metadata header drift')
    matches = []
    for row in rows[1:]:
        if len(row) != len(header):
            raise ValueError('BLS series metadata row width differs')
        record = dict(zip(header, (cell.strip() for cell in row), strict=True))
        if record['series_id'] == BLS_SERIES:
            matches.append(record)
    if len(matches) != 1 or any(matches[0][key] != value for key, value in {
            'periodicity_code': 'M', 'seasonal': 'U',
            'series_title': '(Unadj) Employment Level'}.items()):
        raise ValueError('requested monthly NSA employment series metadata differs')
    return matches[0]


def _a1_metadata(file):
    try:
        text = ' '.join(PublicHTML(file.read_text(encoding='utf-8')).text)
        text = ' '.join(text.split())
    except OSError as error:
        raise ValueError('missing frozen BLS A-1 units metadata') from error
    required = ('Table A-1.', 'Numbers in thousands', 'Not seasonally adjusted',
                'Civilian noninstitutional population', '16 years and over', 'Employed')
    if not all(term in text for term in required):
        raise ValueError('BLS A-1 units/universe evidence differs')


def _bls_response(file):
    try:
        response = json.loads(file.read_text(encoding='utf-8'))
        series = response['Results']['series']
        if (response['status'] != 'REQUEST_SUCCEEDED' or response['message'] != []
                or len(series) != 1 or series[0]['seriesID'] != BLS_SERIES):
            raise ValueError('BLS response status/message/series differs')
        data = series[0]['data']
        if not data:
            raise ValueError('empty BLS monthly response')
        rows = []
        periods = set()
        finite_periods = set()
        for point in data:
            if (not re.fullmatch(r'202[56]', point['year'])
                    or not re.fullmatch(r'M(0[1-9]|1[0-2])', point['period'])):
                raise ValueError('BLS requires requested years and monthly periods, never M13')
            period = (int(point['year']), int(point['period'][1:]))
            if period in periods:
                raise ValueError('duplicate BLS month')
            periods.add(period)
            footnotes = point['footnotes']
            if (not isinstance(footnotes, list) or any(
                    not isinstance(note, dict) or any(
                        not isinstance(value, str) for value in note.values())
                    for note in footnotes)):
                raise ValueError('invalid BLS source footnotes')
            if point['value'] == '-':
                if period != (2025, 10) or not any(note.get('text') for note in footnotes):
                    raise ValueError('unexplained missing selected BLS month')
                value = None
            else:
                value = float(point['value'])
                if not math.isfinite(value) or value < 0:
                    raise ValueError('invalid BLS level')
                finite_periods.add(period)
            rows.append((*period, value, 'thousands of persons',
                         json.dumps(footnotes, sort_keys=True, ensure_ascii=False)))
        if not SELECTED_MONTHS.issubset(finite_periods):
            raise ValueError('BLS response missing selected months')
        return pl.DataFrame(rows, schema={'year': pl.Int64, 'month': pl.Int64,
                            'published': pl.Float64, 'units': pl.String, 'footnotes': pl.String},
                            orient='row')
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError('invalid BLS response structure') from error


def parse_bls_levels(file: Path) -> pl.DataFrame:
    _series_metadata(file.parent / 'bls_series_metadata.txt')
    _a1_metadata(file.parent / 'bls_a1_metadata.html')
    return _bls_response(file)


def _validate_original(kind, file):
    reference = REGISTRY[kind]
    if reference.sha256 is not None and manifest.sha256_file(file) != reference.sha256:
        raise ValueError(f'{kind}: original differs from inspected source vintage')
    if kind == 'usa_samples':
        parse_sample_catalog(file)
    elif kind.startswith('census_industry_'):
        vintage = int(kind.rsplit('_', 1)[1])
        parse_industry_list(file, vintage)
        parse_industry_metadata(file, vintage)
    elif kind in ('acs_2023_employment', 'acs_2024_employment'):
        parse_acs_levels(file, int(kind.split('_')[1]))
    elif kind == 'cps_employment':
        _bls_response(file)
    elif kind == 'bls_series_metadata':
        _series_metadata(file)
    elif kind == 'bls_a1_metadata':
        _a1_metadata(file)
    elif kind.startswith('asec_'):
        if not file.read_bytes().startswith(b'%PDF-'):
            raise ValueError('ASEC documentary original is not a PDF')
    else:
        text = file.read_text(encoding='utf-8')
        if kind.startswith('acs_'):
            year = kind.split('_')[1]
            required = (f'/data/{year}/acs/acs1/groups/B23025', 'B23025_004E')
        else:
            collection, variable = kind.split('_', 1)
            required = (f'IPUMS {collection.upper()}: descr: {variable.upper()}',
                        f'<h1>{variable.upper()}</h1>', 'Description')
        if not all(term in text for term in required):
            raise ValueError(f'{kind}: public metadata identity differs')


def _validate_all(directory):
    for kind, reference in REGISTRY.items():
        _validate_original(kind, directory / reference.filename)
    if 'cps_employment' in REGISTRY:
        parse_bls_levels(directory / REGISTRY['cps_employment'].filename)


def _snapshot_paths(data_dir, reference_id):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', reference_id):
        raise ValueError('unsafe reference snapshot ID')
    root = data_dir / 'raw/references/ipums-verification'
    final, staging = root / reference_id, root / (reference_id + '.part')
    for file in (paths.manifest_path(data_dir), final, staging):
        gr.safe_path(file, data_dir)
    return final, staging


def _filenames(kinds):
    names = set()
    for kind in kinds:
        reference = REGISTRY[kind]
        names.add(reference.filename)
        if reference.request_body is not None:
            names.add(f'{kind}.request.json')
    return names


def _require_unrecorded_snapshot(data_dir, final):
    manifest_file = paths.manifest_path(data_dir)
    expected_paths = {(final / name).relative_to(manifest_file.parent).as_posix()
                      for name in _filenames(REGISTRY) | {'receipt.json'}}
    recorded_paths = {entry.path for entry in manifest.read_manifest(manifest_file)}
    if expected_paths & recorded_paths:
        raise ValueError(f'{final.name}: manifest-recorded reference paths require restoration; '
                         'use a fresh reference ID')


def _request_record(kind, retrieved_at, *, imported):
    reference = REGISTRY[kind]
    return {'source_url': reference.url, 'method': reference.method,
            'request_body': f'{kind}.request.json' if reference.request_body is not None else None,
            'retrieved_at': retrieved_at, 'retrieved_at_is_proxy': imported}



def _verify_requests(originals):
    for kind, record in originals.items():
        proxy = record.get('retrieved_at_is_proxy')
        if not isinstance(proxy, bool):
            raise ValueError('unknown reference retrieval-time proxy flag')
        expected = _request_record(kind, record.get('retrieved_at'), imported=proxy)
        if any(record.get(key) != value for key, value in expected.items()):
            raise ValueError('reference URL/method/request body identity differs')
        try:
            timestamp = datetime.fromisoformat(record['retrieved_at'])
            if timestamp.tzinfo is None:
                raise ValueError('reference retrieval time must be timezone-aware')
        except (TypeError, ValueError) as error:
            raise ValueError('invalid reference retrieval time') from error


def _write_exclusive(file, body):
    with file.open('xb') as output:
        output.write(body)


def _publish(data_dir, reference_id, staging, originals):
    originals = {kind: dict(record) for kind, record in originals.items()}
    _verify_requests(originals)
    _validate_all(staging)
    final, _ = _snapshot_paths(data_dir, reference_id)
    files = {name: target_io.file_record(staging / name) for name in sorted(_filenames(originals))}
    entries = []
    raw_root = paths.manifest_path(data_dir).parent
    for kind, record in originals.items():
        reference = REGISTRY[kind]
        entry = manifest.describe_file(
            staging / reference.filename, staging, retrieved_at=datetime.fromisoformat(
                record['retrieved_at']), client='manual-import' if record[
                    'retrieved_at_is_proxy'] else 'httpx',
            client_version=version('embedding-data') if record['retrieved_at_is_proxy']
            else version('httpx'), source_url=reference.url,
            proxies=('retrieved_at',) if record['retrieved_at_is_proxy'] else ())
        entry = manifest.ManifestEntry(**{**asdict(entry), 'path': (
            final / reference.filename).relative_to(raw_root).as_posix()})
        entries.append(entry)
        record['citation'] = json.loads(json.dumps(asdict(entry)))
    # Request bytes are immutable raw evidence too, with the POST's retrieval-time provenance.
    for kind, record in originals.items():
        if record['request_body'] is not None:
            body_file = staging / record['request_body']
            entry = manifest.describe_file(
                body_file, staging, retrieved_at=datetime.fromisoformat(record['retrieved_at']),
                client='embedding-data', client_version=version('embedding-data'),
                source_url=record['source_url'],
                proxies=('retrieved_at',) if record['retrieved_at_is_proxy'] else ())
            entries.append(manifest.ManifestEntry(**{**asdict(entry), 'path': (
                final / body_file.name).relative_to(raw_root).as_posix()}))
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
    receipt_file = final / 'receipt.json'
    _write_exclusive(receipt_file, (json.dumps(
        receipt, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
    # The generated receipt is externally manifested, never self-inventoried.
    receipt_entry = manifest.describe_file(
        receipt_file, raw_root, retrieved_at=datetime.now(UTC),
        client='embedding-data', client_version=version('embedding-data'))
    manifest.append_entries(paths.manifest_path(data_dir), [receipt_entry])
    for file in staging.iterdir():
        file.unlink()
    staging.rmdir()
    check_references(data_dir, reference_id)
    return final


def check_references(data_dir: Path, reference_id: str) -> dict:
    data_dir = Path(data_dir)
    final, staging = _snapshot_paths(data_dir, reference_id)
    if gr.occupied(staging) or not (final / 'receipt.json').is_file():
        raise ValueError('incomplete or occupied reference snapshot')
    for file in final.rglob('*'):
        gr.safe_path(file, data_dir)
    receipt_file = final / 'receipt.json'
    receipt_entry = manifest.entry_for(paths.manifest_path(data_dir), receipt_file)
    if (receipt_entry.source_url is not None or receipt_entry.client != 'embedding-data'
            or receipt_entry.proxies):
        raise ValueError('generated reference receipt provenance differs')
    receipt = json.loads(receipt_file.read_text(encoding='utf-8'))
    if (receipt.get('reference_id') != reference_id
            or receipt.get('parser_version') != PARSER_VERSION
            or set(receipt.get('originals', {})) != set(REGISTRY)):
        raise ValueError('reference receipt identity/parser version differs')
    expected_names = _filenames(REGISTRY)
    actual_names = {p.relative_to(final).as_posix() for p in final.rglob('*') if p.is_file()}
    if (actual_names != expected_names | {'receipt.json'}
            or set(receipt['files']) != expected_names):
        raise ValueError('missing or extra reference inventory files')
    for name in sorted(expected_names):
        if target_io.file_record(target_io.relative_file(final, name)) != receipt['files'][name]:
            raise ValueError('reference inventory hash or size differs')
    citations = target_io.verify_raw(data_dir, receipt['raw_citations'])
    by_path = {entry['path']: entry for entry in citations}
    raw_root = paths.manifest_path(data_dir).parent
    expected_paths = {(final / name).relative_to(raw_root).as_posix() for name in expected_names}
    if set(by_path) != expected_paths:
        raise ValueError('reference manifest inventory differs')
    _verify_requests(receipt['originals'])
    for kind, reference in REGISTRY.items():
        record = receipt['originals'][kind]
        citation = by_path[(final / reference.filename).relative_to(raw_root).as_posix()]
        if (record.get('citation') != citation or citation['source_url'] != reference.url
                or citation['retrieved_at'] != record['retrieved_at']
                or not isinstance(record['retrieved_at_is_proxy'], bool)
                or citation['proxies'] != (['retrieved_at'] if record[
                    'retrieved_at_is_proxy'] else [])):
            raise ValueError('reference retrieval provenance differs')
        if reference.request_body is not None and (final / record['request_body']).read_bytes(
                ) != reference.request_body:
            raise ValueError('frozen POST request bytes differ')
    _validate_all(final)
    return receipt


def make_client():
    return httpx.Client(timeout=60, follow_redirects=False, headers={'User-Agent': USER_AGENT},
                        trust_env=False)


def acquire(data_dir: Path, reference_id: str, *,
            census_env_file: Path | None = None) -> Path:
    data_dir = Path(data_dir)
    final, staging = _snapshot_paths(data_dir, reference_id)
    if gr.occupied(staging):
        raise ValueError('occupied incomplete snapshot; use a fresh reference ID for imports')
    if gr.occupied(final):
        check_references(data_dir, reference_id)
        return final
    _require_unrecorded_snapshot(data_dir, final)
    census_kinds = set(REGISTRY) & ipums_census_access.ACS_QUERIES.keys()
    census_credential = (ipums_census_access.read_credential(
        env_file=census_env_file) if census_kinds else None)
    _, staging = target_io.stage(final.parent, reference_id, data_dir)
    originals = {}
    with make_client() as client:
        for kind, reference in REGISTRY.items():
            file = staging / reference.filename
            if kind in census_kinds:
                body = ipums_census_access.fetch_original(kind, reference.url, census_credential)
                _write_exclusive(file, body)
                _validate_original(kind, file)
                originals[kind] = _request_record(
                    kind, datetime.now(UTC).isoformat(timespec='seconds'), imported=False)
                continue
            headers = {'Content-Type': 'application/json'} if reference.request_body else {}
            with client.stream(reference.method, reference.url, content=reference.request_body,
                               headers=headers) as response:
                response.raise_for_status()
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
                if length is not None and not response.headers.get('content-encoding') and (
                        size != int(length)):
                    raise ValueError('public original content length differs')
            _validate_original(kind, file)
            if reference.request_body is not None:
                _write_exclusive(staging / f'{kind}.request.json', reference.request_body)
            originals[kind] = _request_record(
                kind, datetime.now(UTC).isoformat(timespec='seconds'), imported=False)
    return _publish(data_dir, reference_id, staging, originals)


def import_reference(data_dir: Path, reference_id: str, kind: str, original: Path) -> Path:
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
    state_file = staging / 'import-state.json'
    if gr.occupied(staging):
        if not state_file.is_file():
            raise ValueError('occupied incomplete download; import originals using a fresh ID')
        for file in staging.rglob('*'):
            gr.safe_path(file, data_dir)
        state = json.loads(state_file.read_text())
        if state.get('mode') != 'import' or state.get('parser_version') != PARSER_VERSION:
            raise ValueError('incomplete import state identity differs')
        originals = state['originals']
        if not set(originals).issubset(REGISTRY):
            raise ValueError('unknown identity in incomplete import')
        names = _filenames(originals)
        actual = {p.name for p in staging.iterdir()}
        if actual != names | {'import-state.json'} or set(state['files']) != names:
            raise ValueError('unmanifested or missing import staging files')
        for name in names:
            if target_io.file_record(staging / name) != state['files'][name]:
                raise ValueError('previously imported original changed')
        _verify_requests(originals)
        for previous in originals:
            _validate_original(previous, staging / REGISTRY[previous].filename)
    else:
        _, staging = target_io.stage(final.parent, reference_id, data_dir)
        originals = {}
    if kind in originals:
        raise ValueError('source identity already imported; originals are immutable')
    reference = REGISTRY[kind]
    _validate_original(kind, original)
    file = staging / reference.filename
    with original.open('rb') as source, file.open('xb') as output:
        shutil.copyfileobj(source, output)
    _validate_original(kind, file)
    if reference.request_body is not None:
        _write_exclusive(staging / f'{kind}.request.json', reference.request_body)
    originals[kind] = _request_record(
        kind, datetime.now(UTC).isoformat(timespec='seconds'), imported=True)
    state = {'mode': 'import', 'parser_version': PARSER_VERSION, 'originals': originals,
             'files': {name: target_io.file_record(staging / name)
                       for name in sorted(_filenames(originals))}}
    target_io.write_json(state_file, state)
    if set(originals) == set(REGISTRY):
        return _publish(data_dir, reference_id, staging, originals)
    return staging
