'''Select and authenticate the five pinned upstreams and the Stage 11 receipt; freeze DDI rules.

The build reads two Stage 7 CPS deliveries, the industry list of the Stage 7 receipt, the
occupation list of the Stage 8 receipt, the PUMS lists of one Stage 8 mapping run, three
Stage 4 node tables and the Stage 11 receipt. A run is authenticated by the SHA-256 of its
`outputs.json` against a detached pin, and a receipt by the SHA-256 of its `receipt.json`.
All six pins are checked before any other file is read.

Then only the files that the build uses are checked against their records: a partial
inventory, so a listed file that the build never reads may be absent. Each CPS delivery is
checked through the Stage 7 `inputs.json` record of its Parquet and its three raw citations.
Stage 7's `verify_bundle` is not run. No environment file is read and no client is built.

The Stage 4 constants and the receipt file names repeat their sources on purpose, as
`tri_codes` does, so that importing this module stays light.
`tests/test_cps_flow_inputs.py` ties each one to its source.
'''

import json
import re
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path

import polars as pl

from embedding_data import cps_flow_references, manifest, paths, target_io

RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')
PIN = re.compile(r'[0-9a-f]{64}')
CODES_SCHEMA_VERSION = 'codes-ita-v1'
NODE_SCHEMA = {'node_id': pl.String, 'system': pl.String, 'vintage': pl.Int64,
               'level': pl.String, 'code': pl.String, 'title': pl.String}
PATH_SCHEMA = {'node_id': pl.String, 'path': pl.List(pl.String)}
STAGE7_FORMAT_VERSION = 'ipums-verification-v1'
OUTPUTS_FILE = 'outputs.json'
RECEIPT_FILE = 'receipt.json'
ROOTS = {
    'stage7_run': 'derived/ipums/verification',
    'stage7_receipt': 'raw/references/ipums-verification',
    'stage8_receipt': 'raw/references/acs-mapping',
    'stage8_mapping_run': 'derived/acs/mapping',
    'codes_run': 'derived/codes',
    'cps_receipt': cps_flow_references.SNAPSHOT_ROOT,
}
# Each upstream: the request field of its ID, the field of its pin, and the pinned file.
PINNED = {
    'stage7_run': ('stage7_run', 'stage7_outputs_sha256', OUTPUTS_FILE),
    'stage7_receipt': ('stage7_receipt', 'stage7_receipt_sha256', RECEIPT_FILE),
    'stage8_receipt': ('stage8_receipt', 'stage8_receipt_sha256', RECEIPT_FILE),
    'stage8_mapping_run': ('stage8_mapping_run', 'stage8_mapping_outputs_sha256', OUTPUTS_FILE),
    'codes_run': ('codes_run', 'codes_outputs_sha256', OUTPUTS_FILE),
    'cps_receipt': ('cps_receipt', 'cps_receipt_sha256', RECEIPT_FILE),
}
# The industry list and the documentary originals that Stage 11 cites, not the online copies.
STAGE7_ORIGINALS = {
    'census_industry_2022': 'census_industry_2022.xlsx',
    'asec_2025_documentation': 'asec_2025_documentation.pdf',
    'asec_2026_documentation': 'asec_2026_documentation.pdf',
    'cps_jan2025_industry_documentation': 'IndustryCodes_Jan2025.pdf',
    'cps_lnkfw1mwt': 'cps_lnkfw1mwt.html',
    'cps_empsame': 'cps_empsame.html',
    'cps_actsame': 'cps_actsame.html',
    'cps_industry_2025_codes': 'ind_2025_codes.shtml',
}
STAGE8_ORIGINALS = {'census_occupation_2018': 'census_occupation_2018.xlsx'}
DELIVERIES = {'monthly': 'cps/monthly', 'asec': 'cps/asec'}
LOOKUP_FILE = 'acs_code_lookup.parquet'
CODE_TABLES = {'naics_nodes.parquet': NODE_SCHEMA, 'soc_nodes.parquet': NODE_SCHEMA,
               'code_paths.parquet': PATH_SCHEMA}
FILE_KEYS = ('sha256', 'size')
PARQUET_KEYS = ('sha256', 'size', 'rows', 'columns', 'schema')

# Flag classes by delivered label text (SD2), never by number.
FLAG_CLASS_BY_LABEL = {
    'No change or children or armed forces': 'nonallocation',
    'Value to blank': 'edited',
    'Blank to value': 'edited',
    'Value to value': 'edited',
    'Allocated': 'allocated',
    'Value to allocated value': 'allocated',
    'Blank to allocated value': 'allocated',
    'Blank to longitudinal value': 'longitudinal',
}
FLAG_VARIABLES = frozenset({'QEMPSTAT', 'QIND', 'QOCC', 'QOCCLY'})
_EMPSTAT = {
    0: 'NIU', 1: 'Armed Forces', 10: 'At work', 12: 'Has job, not at work last week',
    20: 'Unemployed', 21: 'Unemployed, experienced worker', 22: 'Unemployed, new worker',
    30: 'Not in labor force', 31: 'NILF, housework', 32: 'NILF, unable to work',
    33: 'NILF, school', 34: 'NILF, other', 35: 'NILF, unpaid, lt 15 hours', 36: 'NILF, retired',
}
_FLAG_BASE = ('No change or children or armed forces', 'Value to blank', 'Blank to value',
              'Value to value', 'Allocated')
_QEMPSTAT = dict(enumerate((*_FLAG_BASE, 'Blank to allocated value',
                            'Blank to longitudinal value')))
_QCODE = dict(enumerate((*_FLAG_BASE, 'Value to allocated value', 'Blank to allocated value',
                         'Blank to longitudinal value')))
# The delivered DDI labels, measured in both deliveries on 2026-11-23. Values are `int(value)`.
DDI_LABELS = {
    'monthly': {
        'EMPSTAT': _EMPSTAT,
        'EMPSAME': {1: 'No', 2: 'Yes', 96: 'Refused', 97: "Don't know", 99: 'NIU'},
        'ACTSAME': {1: 'Yes', 2: 'No', 96: 'Refused', 97: "Don't Know", 99: 'NIU'},
        'QEMPSTAT': _QEMPSTAT,
        'QIND': _QCODE,
        'QOCC': _QCODE,
    },
    'asec': {
        'EMPSTAT': _EMPSTAT,
        'QEMPSTAT': _QEMPSTAT,
        'QIND': _QCODE,
        'QOCC': _QCODE,
        'QOCCLY': {0: 'No change or children or armed forces', 1: 'Allocated'},
    },
}


@dataclass(frozen=True)
class InputRequest:
    stage7_run: str
    stage7_outputs_sha256: str
    stage7_receipt: str
    stage7_receipt_sha256: str
    stage8_receipt: str
    stage8_receipt_sha256: str
    stage8_mapping_run: str
    stage8_mapping_outputs_sha256: str
    codes_run: str
    codes_outputs_sha256: str
    cps_receipt: str
    cps_receipt_sha256: str


@dataclass(frozen=True)
class Delivery:
    delivery_id: str
    parquet: Path
    parquet_record: dict
    csv_gz: Path
    ddi: dict
    raw_citations: list[dict]


@dataclass(frozen=True)
class SelectedInputs:
    data_dir: Path
    request: InputRequest
    monthly: Delivery
    asec: Delivery
    industry_workbook: Path
    occupation_workbook: Path
    pums_lookup: Path
    naics_nodes: Path
    soc_nodes: Path
    code_paths: Path
    cps_receipt: dict
    provenance: dict

    def verify(self) -> None:
        '''Select again with the same request, and refuse any difference.'''
        try:
            current = select_inputs(self.data_dir, self.request)
        except (ValueError, OSError) as error:
            raise ValueError('selected inputs changed') from error
        if current != self:
            raise ValueError('selected inputs changed')


def check_ddi(file: str, ddi: dict) -> dict:
    '''Verify every frozen label set of one file against its delivered DDI.

    Each DDI category value is a string, converted with `int`. A flag label outside
    `FLAG_CLASS_BY_LABEL` fails first, then any difference from `DDI_LABELS`. Returns the
    int-keyed label maps that `inputs.json` records (JSON writes the keys as strings).
    '''
    if file not in DDI_LABELS:
        raise ValueError('unknown CPS file')
    delivered = {variable.get('name'): variable for variable in _field(ddi, 'variables')}
    rules = {}
    for name, frozen in DDI_LABELS[file].items():
        if name not in delivered:
            raise ValueError(f'{file}/{name}: DDI variable missing')
        labels = {}
        for category in _field(delivered[name], 'categories'):
            try:
                value = int(category['value'])
            except ValueError:
                raise ValueError(f'{file}/{name}: a DDI value is not an integer') from None
            if value in labels:
                raise ValueError(f'{file}/{name}: two DDI values share one integer')
            labels[value] = category['label']
        if name in FLAG_VARIABLES and not set(labels.values()) <= set(FLAG_CLASS_BY_LABEL):
            raise ValueError(f'{file}/{name}: unknown flag label')
        if labels != frozen:
            raise ValueError(f'{file}/{name}: frozen DDI labels differ')
        rules[name] = labels
    return deepcopy(rules)


def _field(value: object, *keys: str) -> object:
    '''The value at `keys`, refusing a missing level.'''
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise ValueError('a recorded field is missing: ' + '/'.join(keys))
        value = value[key]
    return value


def _read(file: Path) -> dict:
    return json.loads(file.read_text(encoding='utf-8'))


def _raw_path(data_dir: Path, file: Path) -> str:
    return file.relative_to(paths.manifest_path(data_dir).parent).as_posix()


def _citation(data_dir: Path, file: Path) -> dict:
    '''The manifest entry of a file, after its bytes match it.'''
    try:
        entry = manifest.entry_for(paths.manifest_path(data_dir), file)
    except KeyError:
        raise ValueError('raw file is not recorded') from None
    return json.loads(json.dumps(asdict(entry)))


def _verified(data_dir: Path, citations: list[dict]) -> list[dict]:
    try:
        return target_io.verify_raw(data_dir, citations)
    except KeyError:
        raise ValueError('cited raw file is not recorded') from None


def _listed(directory: Path, outputs: dict, name: str, required=FILE_KEYS) -> dict:
    '''Check one used file against its inventory record and return its file record.'''
    record = _field(outputs, name)
    if not isinstance(record, dict) or not set(required) <= set(record):
        raise ValueError(f'{name}: inventory record lacks a field')
    file = target_io.relative_file(directory, name)
    if not file.is_file():
        raise ValueError(f'{name}: listed file is missing')
    if manifest.sha256_file(file) != record['sha256'] or file.stat().st_size != record['size']:
        raise ValueError(f'{name}: inventory hash or size differs')
    actual = target_io.file_record(file)
    if any(actual.get(key) != value for key, value in record.items()):
        raise ValueError(f'{name}: inventory rows or schema differ')
    return actual


def _check_request(request: InputRequest) -> None:
    for upstream, (id_field, pin_field, _) in PINNED.items():
        identifier, pin = getattr(request, id_field), getattr(request, pin_field)
        if not isinstance(identifier, str) or not RUN_ID.fullmatch(identifier):
            raise ValueError(f'{upstream}: unsafe selected ID')
        if not isinstance(pin, str) or not PIN.fullmatch(pin):
            raise ValueError(f'{upstream}: invalid detached checksum')


def _check_pins(data_dir: Path, request: InputRequest) -> dict[str, Path]:
    '''Hash each pinned file against its pin before any other read; return the directories.'''
    directories = {}
    for upstream, (id_field, pin_field, name) in PINNED.items():
        directory = target_io.relative_file(
            data_dir, f'{ROOTS[upstream]}/{getattr(request, id_field)}')
        file = target_io.relative_file(directory, name)
        if not file.is_file() or manifest.sha256_file(file) != getattr(request, pin_field):
            raise ValueError(f'{upstream}: detached checksum differs')
        directories[upstream] = directory
    return directories


def _receipt(data_dir: Path, upstream: str, directory: Path, reference_id: str, pin: str,
             originals: dict[str, str]) -> dict:
    '''Authenticate the used originals of a pinned Stage 7 or Stage 8 receipt.'''
    receipt_file = directory / RECEIPT_FILE
    receipt = _read(receipt_file)
    if _field(receipt, 'reference_id') != reference_id:
        raise ValueError(f'{upstream}: receipt identity differs')
    record = {'reference_id': reference_id, 'receipt_sha256': pin,
              'receipt': _citation(data_dir, receipt_file), 'originals': {}}
    for kind, name in originals.items():
        file = target_io.relative_file(directory, name)
        recorded = _field(receipt, 'files', name)
        if not file.is_file() or target_io.file_record(file) != recorded:
            raise ValueError(f'{kind}: original differs from its receipt')
        citation = _field(receipt, 'originals', kind, 'citation')
        if _field(citation, 'path') != _raw_path(data_dir, file):
            raise ValueError(f'{kind}: receipt cites another file')
        [verified] = _verified(data_dir, [citation])
        record['originals'][kind] = {'file': recorded, 'citation': verified}
    return record


def _cps_receipt(data_dir: Path, directory: Path, request: InputRequest) -> tuple[dict, dict]:
    try:
        receipt = cps_flow_references.check_references(data_dir, request.cps_receipt)
    except KeyError:
        raise ValueError('cps_receipt: raw file is not recorded') from None
    return receipt, {'reference_id': request.cps_receipt,
                     'receipt_sha256': request.cps_receipt_sha256,
                     'receipt': _citation(data_dir, directory / RECEIPT_FILE),
                     'raw_citations': receipt['raw_citations']}


def _delivery(data_dir: Path, set_name: str, record: dict) -> tuple[Delivery, dict]:
    '''Authenticate one CPS delivery by its Stage 7 Parquet record and its raw citations.'''
    delivery_id = _field(record, 'delivery_id')
    if not isinstance(delivery_id, str) or not re.fullmatch(r'cps_[0-9]+', delivery_id):
        raise ValueError(f'{set_name}: invalid delivery ID')
    relative = f'derived/cps/{set_name}/{delivery_id}.parquet'
    if _field(record, 'parquet') != relative:
        raise ValueError(f"{set_name}: Parquet is not the delivery's own")
    parquet = target_io.relative_file(data_dir, relative)
    parquet_record = _field(record, 'parquet_record')
    if (not parquet.is_file()
            or manifest.sha256_file(parquet) != _field(parquet_record, 'sha256')
            or target_io.file_record(parquet) != parquet_record):
        raise ValueError(f'{set_name}: Parquet differs from its Stage 7 record')
    raw = f'cps/{set_name}/{delivery_id}'
    expected = [f'{raw}/extract.json', f'{raw}/{delivery_id}.xml', f'{raw}/{delivery_id}.csv.gz']
    citations = _field(record, 'raw_citations')
    if (not isinstance(citations, list)
            or sorted(_field(citation, 'path') for citation in citations) != sorted(expected)):
        raise ValueError(f'{set_name}: raw citations name other files')
    verified = _verified(data_dir, citations)
    [csv_entry] = [entry for entry in verified if entry['path'] == expected[2]]
    csv_gz = target_io.relative_file(paths.manifest_path(data_dir).parent, expected[2])
    delivery = Delivery(delivery_id, parquet, parquet_record, csv_gz, _field(record, 'ddi'),
                        verified)
    return delivery, {'delivery_id': delivery_id, 'parquet': relative,
                      'parquet_record': parquet_record, 'raw_citations': verified,
                      'samples': csv_entry['samples']}


def _stage7_run(data_dir: Path, directory: Path, request: InputRequest,
                receipt_citation: dict) -> tuple[dict, dict]:
    outputs = _read(directory / OUTPUTS_FILE)
    inventory = {'inputs.json': _listed(directory, outputs, 'inputs.json')}
    inputs = _read(directory / 'inputs.json')
    if _field(inputs, 'format_version') != STAGE7_FORMAT_VERSION:
        raise ValueError('stage7_run: format version differs')
    if _field(inputs, 'run_id') != request.stage7_run:
        raise ValueError('stage7_run: run identity differs')
    if (_field(inputs, 'references', 'reference_id') != request.stage7_receipt
            or _field(inputs, 'references', 'receipt_citation') != receipt_citation):
        raise ValueError('stage7_run: records another receipt')
    deliveries = {name: _delivery(data_dir, name, _field(inputs, 'deliveries', key))
                  for name, key in DELIVERIES.items()}
    return {'run_id': request.stage7_run, 'outputs_sha256': request.stage7_outputs_sha256,
            'inventory': inventory}, deliveries


def _mapping_run(directory: Path, request: InputRequest) -> dict:
    outputs = _read(directory / OUTPUTS_FILE)
    inventory = {LOOKUP_FILE: _listed(directory, outputs, LOOKUP_FILE, PARQUET_KEYS),
                 'inputs.json': _listed(directory, outputs, 'inputs.json')}
    inputs = _read(directory / 'inputs.json')
    if _field(inputs, 'run_id') != request.stage8_mapping_run:
        raise ValueError('stage8_mapping_run: run identity differs')
    if (_field(inputs, 'references', 'reference_id') != request.stage8_receipt
            or _field(inputs, 'references', 'receipt_sha256') != request.stage8_receipt_sha256):
        raise ValueError('stage8_mapping_run: records another receipt')
    return {'run_id': request.stage8_mapping_run,
            'outputs_sha256': request.stage8_mapping_outputs_sha256, 'inventory': inventory}


def _codes_run(directory: Path, request: InputRequest) -> dict:
    outputs = _read(directory / OUTPUTS_FILE)
    inventory = {name: _listed(directory, outputs, name)
                 for name in (*CODE_TABLES, 'inputs.json', 'report.json')}
    inputs = _read(directory / 'inputs.json')
    report = _read(directory / 'report.json')
    if _field(inputs, 'schema_version') != CODES_SCHEMA_VERSION:
        raise ValueError('codes_run: inputs.json schema version differs')
    if _field(report, 'schema_version') != CODES_SCHEMA_VERSION:
        raise ValueError('codes_run: report.json schema version differs')
    if _field(inputs, 'run_id') != request.codes_run:
        raise ValueError('codes_run: run identity differs')
    for name, schema in CODE_TABLES.items():
        actual, recorded = inventory[name], _field(report, 'tables', name)
        if (_field(recorded, 'rows') != actual['rows']
                or _field(recorded, 'schema') != actual['schema']):
            raise ValueError(f'{name}: rows or schema differ from report.json')
        if (actual['columns'] != list(schema)
                or actual['schema'] != {column: str(dtype) for column, dtype in schema.items()}):
            raise ValueError(f'{name}: ordered schema differs')
    return {'run_id': request.codes_run, 'outputs_sha256': request.codes_outputs_sha256,
            'inventory': inventory}


def select_inputs(data_dir: Path, request: InputRequest) -> SelectedInputs:
    '''Authenticate the six pinned upstreams and return the files that the build reads.'''
    data_dir = Path(data_dir)
    _check_request(request)
    directories = _check_pins(data_dir, request)
    stage7_receipt = _receipt(data_dir, 'stage7_receipt', directories['stage7_receipt'],
                              request.stage7_receipt, request.stage7_receipt_sha256,
                              STAGE7_ORIGINALS)
    stage8_receipt = _receipt(data_dir, 'stage8_receipt', directories['stage8_receipt'],
                              request.stage8_receipt, request.stage8_receipt_sha256,
                              STAGE8_ORIGINALS)
    cps_receipt, cps_record = _cps_receipt(data_dir, directories['cps_receipt'], request)
    stage7, deliveries = _stage7_run(data_dir, directories['stage7_run'], request,
                                     stage7_receipt['receipt'])
    mapping = _mapping_run(directories['stage8_mapping_run'], request)
    codes = _codes_run(directories['codes_run'], request)
    provenance = {
        'upstream': {'stage7_run': stage7, 'stage7_receipt': stage7_receipt,
                     'stage8_receipt': stage8_receipt, 'stage8_mapping_run': mapping,
                     'codes_run': codes, 'cps_receipt': cps_record},
        'deliveries': {name: record for name, (_, record) in deliveries.items()},
    }
    code_files = {name: directories['codes_run'] / name for name in CODE_TABLES}
    return SelectedInputs(
        data_dir=data_dir, request=request, monthly=deliveries['monthly'][0],
        asec=deliveries['asec'][0],
        industry_workbook=directories['stage7_receipt'] / STAGE7_ORIGINALS[
            'census_industry_2022'],
        occupation_workbook=directories['stage8_receipt'] / STAGE8_ORIGINALS[
            'census_occupation_2018'],
        pums_lookup=directories['stage8_mapping_run'] / LOOKUP_FILE,
        naics_nodes=code_files['naics_nodes.parquet'],
        soc_nodes=code_files['soc_nodes.parquet'],
        code_paths=code_files['code_paths.parquet'],
        cps_receipt=cps_receipt, provenance=provenance)
