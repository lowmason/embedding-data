'''Selection and authentication of the five pinned upstreams and the Stage 11 receipt.'''

import dataclasses
import json
import shutil
from dataclasses import asdict
from pathlib import Path

import polars as pl
import pytest
from cps_flow_fixtures import (
    ASEC_COLUMNS,
    MONTHLY_COLUMNS,
    asec_row,
    monthly_row,
    no_live_clients,  # noqa: F401
    offline_guards,
    seed_upstreams,
)

from embedding_data import (
    acs_mapping_references,
    classification_tables,
    code_build,
    cps_flow_inputs,
    cps_flow_lists,
    cps_flow_references,
    cps_flow_units,
    ipums_references,
    manifest,
    paths,
    target_io,
    tri_codes,
)

MONTHLY = [
    monthly_row(MONTH=1, MISH=1),
    monthly_row(MONTH=2, MISH=2, IND='1370', OCC='8025', EMPSAME=1),
    monthly_row(MONTH=2, MISH=5, CPSID=2, CPSIDP=2, CPSIDV=2, IND='3070', OCC='2200'),
]
ASEC = [
    asec_row(YEAR=2025),
    asec_row(YEAR=2026, CPSID=3, CPSIDP=3, CPSIDV=3, IND='1380', OCC='8225'),
]
UPSTREAMS = {
    'stage7_run': ('stage7_run', 'stage7_outputs_sha256', 'run_id', 'outputs_sha256'),
    'stage7_receipt': ('stage7_receipt', 'stage7_receipt_sha256', 'reference_id',
                       'receipt_sha256'),
    'stage8_receipt': ('stage8_receipt', 'stage8_receipt_sha256', 'reference_id',
                       'receipt_sha256'),
    'stage8_mapping_run': ('stage8_mapping_run', 'stage8_mapping_outputs_sha256', 'run_id',
                           'outputs_sha256'),
    'codes_run': ('codes_run', 'codes_outputs_sha256', 'run_id', 'outputs_sha256'),
    'cps_receipt': ('cps_receipt', 'cps_receipt_sha256', 'reference_id', 'receipt_sha256'),
}
PIN_FIELDS = [pin for _, pin, _, _ in UPSTREAMS.values()]
# The spec's `ind_2025_codes` is the Stage 7 kind `cps_industry_2025_codes`, whose original
# is `ind_2025_codes.shtml`.
DOCUMENTARY = {
    'asec_2025_documentation': 'asec_2025_documentation.pdf',
    'asec_2026_documentation': 'asec_2026_documentation.pdf',
    'cps_jan2025_industry_documentation': 'IndustryCodes_Jan2025.pdf',
    'cps_lnkfw1mwt': 'cps_lnkfw1mwt.html',
    'cps_empsame': 'cps_empsame.html',
    'cps_actsame': 'cps_actsame.html',
    'cps_industry_2025_codes': 'ind_2025_codes.shtml',
}
FLAG = ['No change or children or armed forces', 'Value to blank', 'Blank to value',
        'Value to value', 'Allocated']
EMPSTAT = {0: 'NIU', 1: 'Armed Forces', 10: 'At work', 12: 'Has job, not at work last week',
           20: 'Unemployed', 21: 'Unemployed, experienced worker', 22: 'Unemployed, new worker',
           30: 'Not in labor force', 31: 'NILF, housework', 32: 'NILF, unable to work',
           33: 'NILF, school', 34: 'NILF, other', 35: 'NILF, unpaid, lt 15 hours',
           36: 'NILF, retired'}
QEMPSTAT = dict(enumerate([*FLAG, 'Blank to allocated value', 'Blank to longitudinal value']))
QCODE = dict(enumerate([*FLAG, 'Value to allocated value', 'Blank to allocated value',
                        'Blank to longitudinal value']))
EXPECTED_LABELS = {
    'monthly': {
        'EMPSTAT': EMPSTAT,
        'EMPSAME': {1: 'No', 2: 'Yes', 96: 'Refused', 97: "Don't know", 99: 'NIU'},
        'ACTSAME': {1: 'Yes', 2: 'No', 96: 'Refused', 97: "Don't Know", 99: 'NIU'},
        'QEMPSTAT': QEMPSTAT, 'QIND': QCODE, 'QOCC': QCODE},
    'asec': {'EMPSTAT': EMPSTAT, 'QEMPSTAT': QEMPSTAT, 'QIND': QCODE, 'QOCC': QCODE,
             'QOCCLY': {0: 'No change or children or armed forces', 1: 'Allocated'}},
}
EXPECTED_CLASSES = {
    'No change or children or armed forces': 'nonallocation',
    'Value to blank': 'edited', 'Blank to value': 'edited', 'Value to value': 'edited',
    'Allocated': 'allocated', 'Value to allocated value': 'allocated',
    'Blank to allocated value': 'allocated', 'Blank to longitudinal value': 'longitudinal',
}


@pytest.fixture(scope='module')
def seeded(tmp_path_factory):
    return seed_upstreams(tmp_path_factory.mktemp('upstreams'), monthly=MONTHLY, asec=ASEC)


@pytest.fixture
def upstreams(seeded, tmp_path):
    '''A private copy of the seeded tree that a test may change.'''
    data_dir = tmp_path / 'data'
    shutil.copytree(seeded.data_dir, data_dir)
    return dataclasses.replace(seeded, data_dir=data_dir)


def select(upstreams, **changes):
    request = dataclasses.replace(upstreams.request, **changes)
    return cps_flow_inputs.select_inputs(upstreams.data_dir, request)


def run_directory(upstreams, upstream):
    data_dir, request = upstreams.data_dir, upstreams.request
    return {
        'stage7_run': data_dir / 'derived/ipums/verification' / request.stage7_run,
        'stage7_receipt': data_dir / 'raw/references/ipums-verification' / request.stage7_receipt,
        'stage8_receipt': data_dir / 'raw/references/acs-mapping' / request.stage8_receipt,
        'stage8_mapping_run': data_dir / 'derived/acs/mapping' / request.stage8_mapping_run,
        'codes_run': data_dir / 'derived/codes' / request.codes_run,
        'cps_receipt': data_dir / cps_flow_references.SNAPSHOT_ROOT / request.cps_receipt,
    }[upstream]


def flip(file: Path) -> None:
    data = bytearray(file.read_bytes())
    data[len(data) // 2] ^= 1
    file.write_bytes(bytes(data))


def truncate(file: Path) -> None:
    '''Cut a file to half its size, so that a Parquet reader cannot open it.'''
    data = file.read_bytes()
    file.write_bytes(data[:len(data) // 2])


def repin(directory: Path) -> str:
    '''Rewrite every present file's record in `outputs.json`, keeping its keys; return the pin.'''
    outputs_file = directory / 'outputs.json'
    outputs = json.loads(outputs_file.read_text())
    for name, record in outputs.items():
        if (directory / name).is_file():
            actual = target_io.file_record(directory / name)
            record.update({key: actual[key] for key in record})
    target_io.write_json(outputs_file, outputs)
    return manifest.sha256_file(outputs_file)


def edit_json(directory: Path, name: str, change) -> str:
    '''Replace one JSON file of a run by `change(value)`, then repin the run.'''
    file = directory / name
    value = json.loads(file.read_text())
    change(value)
    target_io.write_json(file, value)
    return repin(directory)


def edit_outputs(directory: Path, change) -> str:
    file = directory / 'outputs.json'
    value = json.loads(file.read_text())
    change(value)
    target_io.write_json(file, value)
    return manifest.sha256_file(file)


def edit_manifest(data_dir: Path, suffix: str, change) -> None:
    '''Change the one manifest line whose path ends with `suffix`.'''
    manifest_file = paths.manifest_path(data_dir)
    lines = []
    for line in manifest_file.read_text().splitlines():
        record = json.loads(line)
        if record['path'].endswith(suffix):
            record = change(record)
            if record is None:
                continue
        lines.append(json.dumps(record))
    manifest_file.write_text(''.join(line + '\n' for line in lines))


def rewrite_receipt(upstreams, upstream: str, change) -> str:
    '''Rewrite a Stage 7 or Stage 8 receipt, record its new bytes, and return its new pin.'''
    file = run_directory(upstreams, upstream) / 'receipt.json'
    value = json.loads(file.read_text())
    change(value)
    target_io.write_json(file, value)
    record = target_io.file_record(file)
    edit_manifest(upstreams.data_dir, file.relative_to(upstreams.data_dir / 'raw').as_posix(),
                  lambda entry: {**entry, **record})
    return record['sha256']


def citation(data_dir: Path, file: Path) -> dict:
    return json.loads(json.dumps(asdict(manifest.entry_for(paths.manifest_path(data_dir),
                                                           file))))


def test_select_inputs_authenticates_all_six_pins(upstreams):
    data_dir, request = upstreams.data_dir, upstreams.request
    selected = cps_flow_inputs.select_inputs(data_dir, request)
    upstream = selected.provenance['upstream']
    assert set(upstream) == set(UPSTREAMS)
    for key, (id_field, pin_field, id_key, pin_key) in UPSTREAMS.items():
        assert upstream[key][id_key] == getattr(request, id_field)
        assert upstream[key][pin_key] == getattr(request, pin_field)
    assert set(selected.provenance) == {'upstream', 'deliveries'}
    selected.verify()
    assert selected.data_dir == data_dir and selected.request == request
    assert selected.monthly.delivery_id == 'cps_00001'
    assert selected.monthly.parquet == data_dir / 'derived/cps/monthly/cps_00001.parquet'
    assert selected.monthly.csv_gz == data_dir / 'raw/cps/monthly/cps_00001/cps_00001.csv.gz'
    assert selected.asec.delivery_id == 'cps_00002'
    assert selected.asec.csv_gz == data_dir / 'raw/cps/asec/cps_00002/cps_00002.csv.gz'
    assert pl.scan_parquet(selected.monthly.parquet).collect_schema().names() == list(
        MONTHLY_COLUMNS)
    assert pl.scan_parquet(selected.asec.parquet).collect_schema().names() == list(ASEC_COLUMNS)
    for delivery in (selected.monthly, selected.asec):
        assert delivery.parquet_record == target_io.file_record(delivery.parquet)
        assert sorted(item['path'] for item in delivery.raw_citations) == sorted(
            f'{delivery.csv_gz.parent.relative_to(data_dir / "raw").as_posix()}/{name}'
            for name in ('extract.json', f'{delivery.delivery_id}.xml',
                         f'{delivery.delivery_id}.csv.gz'))
        assert [variable['name'] for variable in delivery.ddi['variables']] == list(
            pl.scan_parquet(delivery.parquet).collect_schema().names())
    deliveries = selected.provenance['deliveries']
    assert deliveries['monthly']['samples'] == ['cps2025_01b', 'cps2025_02b']
    assert deliveries['asec']['samples'] == ['cps2025_03s', 'cps2026_03s']
    assert deliveries['asec']['parquet'] == 'derived/cps/asec/cps_00002.parquet'
    assert deliveries['monthly']['parquet_record'] == selected.monthly.parquet_record
    assert deliveries['monthly']['raw_citations'] == selected.monthly.raw_citations
    receipts = data_dir / 'raw/references'
    assert selected.industry_workbook == (
        receipts / 'ipums-verification' / request.stage7_receipt / 'census_industry_2022.xlsx')
    assert selected.occupation_workbook == (
        receipts / 'acs-mapping' / request.stage8_receipt / 'census_occupation_2018.xlsx')
    codes = data_dir / 'derived/codes' / request.codes_run
    assert (selected.naics_nodes, selected.soc_nodes, selected.code_paths) == (
        codes / 'naics_nodes.parquet', codes / 'soc_nodes.parquet', codes / 'code_paths.parquet')
    assert selected.pums_lookup == (
        data_dir / 'derived/acs/mapping' / request.stage8_mapping_run / 'acs_code_lookup.parquet')
    assert selected.cps_receipt == cps_flow_references.check_references(
        data_dir, request.cps_receipt)


def test_provenance_records_the_verified_inventories_and_receipts(upstreams):
    data_dir, request = upstreams.data_dir, upstreams.request
    upstream = cps_flow_inputs.select_inputs(data_dir, request).provenance['upstream']
    inventories = {
        'stage7_run': ['inputs.json'],
        'stage8_mapping_run': ['acs_code_lookup.parquet', 'inputs.json'],
        'codes_run': ['code_paths.parquet', 'inputs.json', 'naics_nodes.parquet',
                      'report.json', 'soc_nodes.parquet'],
    }
    for key, names in inventories.items():
        directory = run_directory(upstreams, key)
        assert upstream[key]['inventory'] == {
            name: target_io.file_record(directory / name) for name in names}
    for key in ('stage7_receipt', 'stage8_receipt', 'cps_receipt'):
        receipt = run_directory(upstreams, key) / 'receipt.json'
        assert upstream[key]['receipt'] == citation(data_dir, receipt)
    occupation = run_directory(upstreams, 'stage8_receipt') / 'census_occupation_2018.xlsx'
    assert upstream['stage8_receipt']['originals'] == {'census_occupation_2018': {
        'file': target_io.file_record(occupation), 'citation': citation(data_dir, occupation)}}
    receipt = cps_flow_references.check_references(data_dir, request.cps_receipt)
    assert upstream['cps_receipt']['raw_citations'] == receipt['raw_citations']


@pytest.mark.parametrize('field', PIN_FIELDS)
def test_a_wrong_pin_for_each_upstream_fails(upstreams, field):
    with pytest.raises(ValueError, match='checksum differs'):
        select(upstreams, **{field: '0' * 64})


def test_every_pin_is_checked_before_any_other_file_is_read(upstreams, monkeypatch):
    read = []
    monkeypatch.setattr(Path, 'read_text', lambda self, *args, **kwargs: read.append(self))
    for field in PIN_FIELDS:
        with pytest.raises(ValueError, match='checksum differs'):
            select(upstreams, **{field: '0' * 64})
    assert read == []


def test_changed_parquet_raw_csv_or_manifest_entry_fails(upstreams):
    data_dir = upstreams.data_dir
    cases = {
        'parquet': lambda: flip(data_dir / 'derived/cps/monthly/cps_00001.parquet'),
        'raw_csv': lambda: flip(data_dir / 'raw/cps/monthly/cps_00001/cps_00001.csv.gz'),
        'manifest_entry': lambda: edit_manifest(
            data_dir, 'cps_00001/cps_00001.csv.gz',
            lambda entry: {**entry, 'retrieved_at': '2026-10-13T00:00:00+00:00'}),
    }
    pristine = data_dir.parent / 'pristine'
    shutil.copytree(data_dir, pristine)
    for name, change in cases.items():
        shutil.rmtree(data_dir)
        shutil.copytree(pristine, data_dir)
        cps_flow_inputs.select_inputs(data_dir, upstreams.request)
        change()
        with pytest.raises(ValueError):
            cps_flow_inputs.select_inputs(data_dir, upstreams.request)


@pytest.mark.parametrize('case', ['asec_parquet', 'asec_xml', 'monthly_extract',
                                  'unrecorded_csv', 'parquet_part_of_record',
                                  'truncated_parquet'])
def test_each_delivery_file_is_authenticated(upstreams, case):
    data_dir = upstreams.data_dir
    stage7 = run_directory(upstreams, 'stage7_run')
    pin = upstreams.request.stage7_outputs_sha256
    if case == 'asec_parquet':
        flip(data_dir / 'derived/cps/asec/cps_00002.parquet')
        message = 'asec: Parquet differs from its Stage 7 record'
    elif case == 'asec_xml':
        flip(data_dir / 'raw/cps/asec/cps_00002/cps_00002.xml')
        message = 'differs from the'
    elif case == 'monthly_extract':
        edit_manifest(data_dir, 'cps_00001/extract.json',
                      lambda entry: {**entry, 'client_version': '0.7.1'})
        message = 'cited raw provenance changed'
    elif case == 'unrecorded_csv':
        edit_manifest(data_dir, 'cps_00002/cps_00002.csv.gz', lambda entry: None)
        message = 'raw file is not recorded'
    elif case == 'truncated_parquet':
        truncate(data_dir / 'derived/cps/monthly/cps_00001.parquet')
        message = 'monthly: Parquet differs from its Stage 7 record'
    else:
        pin = edit_json(stage7, 'inputs.json', lambda value: value['deliveries']['cps/monthly'][
            'parquet_record'].update(rows=99))
        message = 'monthly: Parquet differs from its Stage 7 record'
    with pytest.raises(ValueError, match=message):
        select(upstreams, stage7_outputs_sha256=pin)


@pytest.mark.parametrize('upstream, name', [
    ('stage7_run', 'inputs.json'), ('stage8_mapping_run', 'inputs.json'),
    ('codes_run', 'inputs.json'), ('codes_run', 'report.json')])
def test_a_used_file_that_differs_from_its_inventory_fails(upstreams, upstream, name):
    file = run_directory(upstreams, upstream) / name
    file.write_text(file.read_text() + '\n')
    with pytest.raises(ValueError, match=f'{name}: inventory hash or size differs'):
        cps_flow_inputs.select_inputs(upstreams.data_dir, upstreams.request)


@pytest.mark.parametrize('case', ['stage7_reference_id', 'stage7_receipt_citation',
                                  'mapping_reference_id', 'mapping_receipt_sha256'])
def test_each_run_must_record_the_requested_receipt(upstreams, case):
    if case.startswith('stage7'):
        directory, field = run_directory(upstreams, 'stage7_run'), 'stage7_outputs_sha256'
        key = 'reference_id' if case == 'stage7_reference_id' else 'receipt_citation'
        value = 'another_receipt' if key == 'reference_id' else {'path': 'another'}
    else:
        directory = run_directory(upstreams, 'stage8_mapping_run')
        field = 'stage8_mapping_outputs_sha256'
        key = 'reference_id' if case == 'mapping_reference_id' else 'receipt_sha256'
        value = 'another_receipt' if key == 'reference_id' else '1' * 64
    pin = edit_json(directory, 'inputs.json', lambda inputs: inputs['references'].update(
        {key: value}))
    with pytest.raises(ValueError, match='records another receipt'):
        select(upstreams, **{field: pin})


def test_only_the_used_files_are_read(upstreams):
    data_dir, request = upstreams.data_dir, upstreams.request
    mapping = run_directory(upstreams, 'stage8_mapping_run')
    outputs = json.loads((mapping / 'outputs.json').read_text())
    assert 'acs_core_canonical.parquet' in outputs
    assert not (mapping / 'acs_core_canonical.parquet').exists()
    stage7, codes = run_directory(upstreams, 'stage7_run'), run_directory(upstreams, 'codes_run')
    assert 'weight_rules.json' in json.loads((stage7 / 'outputs.json').read_text())
    assert 'naics_edges.parquet' in json.loads((codes / 'outputs.json').read_text())
    receipt = run_directory(upstreams, 'stage7_receipt')
    assert 'usa_samples.html' in json.loads((receipt / 'receipt.json').read_text())['files']
    assert not (receipt / 'usa_samples.html').exists()
    (stage7 / 'report.json').unlink()
    (mapping / 'report.json').unlink()
    cps_flow_inputs.select_inputs(data_dir, request)
    lookup = mapping / 'acs_code_lookup.parquet'
    flip(lookup)
    with pytest.raises(ValueError, match='acs_code_lookup.parquet: inventory hash or size'):
        cps_flow_inputs.select_inputs(data_dir, request)
    lookup.unlink()
    with pytest.raises(ValueError, match='acs_code_lookup.parquet: listed file is missing'):
        cps_flow_inputs.select_inputs(data_dir, request)


@pytest.mark.parametrize('case', ['industry_workbook', 'occupation_workbook',
                                  'documentary_original', 'original_manifest_entry',
                                  'receipt_manifest_entry', 'unrecorded_receipt',
                                  'citation_of_another_file', 'stage11_original'])
def test_each_used_receipt_original_is_authenticated(upstreams, case):
    data_dir = upstreams.data_dir
    stage7 = run_directory(upstreams, 'stage7_receipt')
    stage8 = run_directory(upstreams, 'stage8_receipt')
    changes = {}
    if case == 'industry_workbook':
        flip(stage7 / 'census_industry_2022.xlsx')
        message = 'census_industry_2022: original differs from its receipt'
    elif case == 'occupation_workbook':
        flip(stage8 / 'census_occupation_2018.xlsx')
        message = 'census_occupation_2018: original differs from its receipt'
    elif case == 'documentary_original':
        flip(stage7 / 'IndustryCodes_Jan2025.pdf')
        message = 'cps_jan2025_industry_documentation: original differs from its receipt'
    elif case == 'original_manifest_entry':
        edit_manifest(data_dir, 'asec_2025_documentation.pdf',
                      lambda entry: {**entry, 'retrieved_at': '2026-10-13T00:00:00+00:00'})
        message = 'cited raw provenance changed'
    elif case == 'receipt_manifest_entry':
        edit_manifest(data_dir, f'{stage8.name}/receipt.json',
                      lambda entry: {**entry, 'sha256': '0' * 64})
        message = 'differs from the'
    elif case == 'unrecorded_receipt':
        edit_manifest(data_dir, f'{stage8.name}/receipt.json', lambda entry: None)
        message = 'raw file is not recorded'
    elif case == 'stage11_original':
        flip(run_directory(upstreams, 'cps_receipt') / 'cps_industry_codes.csv')
        message = 'reference inventory hash or size differs'
    else:
        other = stage7 / 'asec_2026_documentation.pdf'
        changes['stage7_receipt_sha256'] = rewrite_receipt(
            upstreams, 'stage7_receipt', lambda receipt: receipt['originals'][
                'cps_empsame'].update(citation=citation(data_dir, other)))
        message = 'cps_empsame: receipt cites another file'
    with pytest.raises(ValueError, match=message):
        select(upstreams, **changes)


def test_provenance_cites_the_frozen_documentary_originals(upstreams):
    data_dir, request = upstreams.data_dir, upstreams.request
    selected = cps_flow_inputs.select_inputs(data_dir, request)
    originals = selected.provenance['upstream']['stage7_receipt']['originals']
    assert set(originals) == {'census_industry_2022', *DOCUMENTARY}
    directory = run_directory(upstreams, 'stage7_receipt')
    for kind, name in DOCUMENTARY.items():
        file = directory / name
        assert originals[kind] == {'file': target_io.file_record(file),
                                   'citation': citation(data_dir, file)}
        assert originals[kind]['citation']['path'] == (
            f'references/ipums-verification/{request.stage7_receipt}/{name}')


def test_receipt_file_names_repeat_the_reference_registries():
    assert cps_flow_inputs.STAGE7_ORIGINALS == {
        'census_industry_2022': 'census_industry_2022.xlsx', **DOCUMENTARY}
    for kind, name in cps_flow_inputs.STAGE7_ORIGINALS.items():
        assert ipums_references.REGISTRY[kind].filename == name
    assert cps_flow_inputs.STAGE8_ORIGINALS == {
        'census_occupation_2018': 'census_occupation_2018.xlsx'}
    for kind, name in cps_flow_inputs.STAGE8_ORIGINALS.items():
        assert acs_mapping_references.REGISTRY[kind].filename == name


@pytest.mark.parametrize('case', ['stage7_format_version', 'stage7_run_id',
                                  'stage7_missing_references', 'stage7_receipt_id',
                                  'stage8_receipt_id', 'mapping_run_id', 'codes_inputs_schema',
                                  'codes_report_schema', 'codes_run_id'])
def test_recorded_identities_must_match(upstreams, case):
    stage7 = run_directory(upstreams, 'stage7_run')
    mapping = run_directory(upstreams, 'stage8_mapping_run')
    codes = run_directory(upstreams, 'codes_run')

    def assign(key, value):
        return lambda inputs: inputs.update({key: value})

    edits = {
        'stage7_format_version': ('stage7_outputs_sha256', stage7, 'inputs.json',
                                  assign('format_version', 'ipums-verification-v0'),
                                  'stage7_run: format version differs'),
        'stage7_run_id': ('stage7_outputs_sha256', stage7, 'inputs.json',
                          assign('run_id', 'another_run'), 'stage7_run: run identity differs'),
        'stage7_missing_references': ('stage7_outputs_sha256', stage7, 'inputs.json',
                                      lambda inputs: inputs.pop('references'),
                                      'a recorded field is missing: references'),
        'mapping_run_id': ('stage8_mapping_outputs_sha256', mapping, 'inputs.json',
                           assign('run_id', 'another_run'),
                           'stage8_mapping_run: run identity differs'),
        'codes_inputs_schema': ('codes_outputs_sha256', codes, 'inputs.json',
                                assign('schema_version', 'codes-ita-v0'),
                                'codes_run: inputs.json schema version differs'),
        'codes_report_schema': ('codes_outputs_sha256', codes, 'report.json',
                                assign('schema_version', 'codes-ita-v0'),
                                'codes_run: report.json schema version differs'),
        'codes_run_id': ('codes_outputs_sha256', codes, 'inputs.json',
                         assign('run_id', 'another_run'), 'codes_run: run identity differs'),
    }
    if case in edits:
        field, directory, name, change, message = edits[case]
        changes = {field: edit_json(directory, name, change)}
    else:
        upstream = case.removesuffix('_id')
        changes = {f'{upstream}_sha256': rewrite_receipt(
            upstreams, upstream, lambda receipt: receipt.update(reference_id='another'))}
        message = f'{upstream}: receipt identity differs'
    with pytest.raises(ValueError, match=message):
        select(upstreams, **changes)


@pytest.mark.parametrize('case', ['delivery_id', 'parquet_path', 'missing_citation',
                                  'citation_of_another_delivery', 'swapped_sets'])
def test_delivery_records_must_name_their_own_files(upstreams, case):
    stage7 = run_directory(upstreams, 'stage7_run')

    def change(inputs):
        deliveries = inputs['deliveries']
        monthly = deliveries['cps/monthly']
        if case == 'delivery_id':
            monthly['delivery_id'] = 'cps_x'
        elif case == 'parquet_path':
            monthly['parquet'] = 'derived/cps/asec/cps_00002.parquet'
        elif case == 'missing_citation':
            monthly['raw_citations'] = monthly['raw_citations'][:2]
        elif case == 'citation_of_another_delivery':
            monthly['raw_citations'][2] = deliveries['cps/asec']['raw_citations'][2]
        else:
            deliveries['cps/monthly'], deliveries['cps/asec'] = (
                deliveries['cps/asec'], deliveries['cps/monthly'])

    messages = {'delivery_id': 'monthly: invalid delivery ID',
                'parquet_path': "monthly: Parquet is not the delivery's own",
                'missing_citation': 'monthly: raw citations name other files',
                'citation_of_another_delivery': 'monthly: raw citations name other files',
                'swapped_sets': "monthly: Parquet is not the delivery's own"}
    pin = edit_json(stage7, 'inputs.json', change)
    with pytest.raises(ValueError, match=messages[case]):
        select(upstreams, stage7_outputs_sha256=pin)


@pytest.mark.parametrize('case', ['report_rows', 'report_schema', 'reordered_columns',
                                  'path_type', 'missing_record', 'record_without_size',
                                  'changed_table', 'truncated_table', 'mapping_rows',
                                  'mapping_record_keys'])
def test_used_tables_must_match_their_records(upstreams, case):
    codes = run_directory(upstreams, 'codes_run')
    mapping = run_directory(upstreams, 'stage8_mapping_run')
    field = 'codes_outputs_sha256'

    def report_table(name, **record):
        return lambda report: report['tables'][name].update(record)

    def rewrite(name, frame):
        frame.write_parquet(codes / name)
        schema = {column: str(dtype) for column, dtype in frame.schema.items()}
        return edit_json(codes, 'report.json', report_table(name, rows=frame.height,
                                                            schema=schema))

    if case == 'report_rows':
        pin = edit_json(codes, 'report.json', report_table('naics_nodes.parquet', rows=1))
        message = 'naics_nodes.parquet: rows or schema differ from report.json'
    elif case == 'report_schema':
        pin = edit_json(codes, 'report.json', report_table(
            'code_paths.parquet', schema={'node_id': 'String', 'path': 'String'}))
        message = 'code_paths.parquet: rows or schema differ from report.json'
    elif case == 'reordered_columns':
        frame = pl.read_parquet(codes / 'soc_nodes.parquet')
        pin = rewrite('soc_nodes.parquet', frame.select(frame.columns[::-1]))
        message = 'soc_nodes.parquet: ordered schema differs'
    elif case == 'path_type':
        frame = pl.read_parquet(codes / 'code_paths.parquet')
        pin = rewrite('code_paths.parquet', frame.with_columns(pl.col('path').list.join('>')))
        message = 'code_paths.parquet: ordered schema differs'
    elif case == 'missing_record':
        pin = edit_outputs(codes, lambda outputs: outputs.pop('soc_nodes.parquet'))
        message = 'a recorded field is missing: soc_nodes.parquet'
    elif case == 'record_without_size':
        pin = edit_outputs(codes, lambda outputs: outputs['report.json'].pop('size'))
        message = 'report.json: inventory record lacks a field'
    elif case == 'changed_table':
        flip(codes / 'naics_nodes.parquet')
        pin = upstreams.request.codes_outputs_sha256
        message = 'naics_nodes.parquet: inventory hash or size differs'
    elif case == 'truncated_table':
        truncate(codes / 'soc_nodes.parquet')
        pin = upstreams.request.codes_outputs_sha256
        message = 'soc_nodes.parquet: inventory hash or size differs'
    else:
        field = 'stage8_mapping_outputs_sha256'
        if case == 'mapping_rows':
            pin = edit_outputs(mapping, lambda outputs: outputs[
                'acs_code_lookup.parquet'].update(rows=99))
            message = 'acs_code_lookup.parquet: inventory rows or schema differ'
        else:
            pin = edit_outputs(mapping, lambda outputs: outputs[
                'acs_code_lookup.parquet'].pop('schema'))
            message = 'acs_code_lookup.parquet: inventory record lacks a field'
    with pytest.raises(ValueError, match=message):
        select(upstreams, **{field: pin})


@pytest.mark.parametrize('field', [
    'stage7_run', 'stage7_receipt', 'stage8_receipt', 'stage8_mapping_run', 'codes_run',
    'cps_receipt', *PIN_FIELDS])
def test_request_ids_and_pins_must_be_safe(upstreams, field):
    is_pin = field.endswith('_sha256')
    value = getattr(upstreams.request, field).upper() if is_pin else '-unsafe'
    message = 'invalid detached checksum' if is_pin else 'unsafe selected ID'
    with pytest.raises(ValueError, match=message):
        select(upstreams, **{field: value})
    with pytest.raises(ValueError, match=message):
        select(upstreams, **{field: None})


def test_verify_refuses_a_change_after_selection(upstreams):
    data_dir = upstreams.data_dir
    selected = cps_flow_inputs.select_inputs(data_dir, upstreams.request)
    (run_directory(upstreams, 'stage7_run') / 'report.json').write_text('{}\n')
    selected.verify()
    flip(data_dir / 'derived/cps/asec/cps_00002.parquet')
    with pytest.raises(ValueError, match='selected inputs changed'):
        selected.verify()


def test_verify_refuses_a_selection_that_differs(upstreams):
    selected = cps_flow_inputs.select_inputs(upstreams.data_dir, upstreams.request)
    changed = dataclasses.replace(selected, cps_receipt={**selected.cps_receipt, 'extra': 1})
    with pytest.raises(ValueError, match='selected inputs changed'):
        changed.verify()


def test_selection_reads_no_environment_and_builds_no_client(upstreams, monkeypatch):
    counts = offline_guards(monkeypatch)
    selected = cps_flow_inputs.select_inputs(upstreams.data_dir, upstreams.request)
    selected.verify()
    assert counts == {'network': 0, 'environment_file': 0, 'live_client': 0}


def test_selected_lists_and_nodes_build_the_unit_registry(upstreams):
    selected = cps_flow_inputs.select_inputs(upstreams.data_dir, upstreams.request)
    industry = cps_flow_lists.read_industry_list(selected.industry_workbook)
    occupation = cps_flow_lists.read_occupation_list(selected.occupation_workbook)
    assert [row.code for row in industry] == ['0170', '1370', '1380', '3070', '9920']
    assert [row.code for row in occupation] == [
        '0010', '0020', '2200', '7000', '8025', '8225', '9830', '9920']
    monthly = pl.read_parquet(selected.monthly.parquet)
    asec = pl.read_parquet(selected.asec.parquet)
    delivered = {
        'industry': set(monthly['IND']) | set(asec['IND']) | set(asec['INDLY']),
        'occupation': set(monthly['OCC']) | set(asec['OCC']) | set(asec['OCCLY'])}
    assert delivered == {'industry': {'0170', '1370', '1380', '3070'},
                         'occupation': {'0010', '2200', '8025', '8225'}}
    units = cps_flow_units.build_units(
        industry, occupation, naics_nodes=pl.read_parquet(selected.naics_nodes),
        soc_nodes=pl.read_parquet(selected.soc_nodes),
        paths=pl.read_parquet(selected.code_paths),
        pums=cps_flow_units.read_pums_lists(selected.pums_lookup),
        delivered=delivered, evidence=cps_flow_references.special_evidence(selected.cps_receipt),
        references={'industry': upstreams.request.stage7_receipt,
                    'occupation': upstreams.request.stage8_receipt,
                    'special': upstreams.request.cps_receipt})
    x_rows = units.filter(pl.col('x_token').is_not_null())
    assert dict(zip(x_rows['code'], x_rows['x_cross_check'], strict=True)) == {
        '8025': 'equal', '8225': 'strict_subset'}
    assert units.height == 5 + 8 + 2


def test_ddi_labels_are_frozen(upstreams):
    selected = cps_flow_inputs.select_inputs(upstreams.data_dir, upstreams.request)
    monthly = cps_flow_inputs.check_ddi('monthly', selected.monthly.ddi)
    asec = cps_flow_inputs.check_ddi('asec', selected.asec.ddi)
    assert monthly == EXPECTED_LABELS['monthly']
    assert asec == EXPECTED_LABELS['asec']
    assert all(isinstance(value, int) for labels in (*monthly.values(), *asec.values())
               for value in labels)

    def changed(file, name, change):
        ddi = json.loads(json.dumps(getattr(selected, file).ddi))
        [variable] = [item for item in ddi['variables'] if item['name'] == name]
        change(variable['categories'])
        return ddi

    def relabel(value, label):
        return lambda categories: next(
            item for item in categories if int(item['value']) == value).update(label=label)

    cases = [
        ('monthly', 'EMPSAME', relabel(1, 'Different employer'), 'frozen DDI labels differ'),
        ('monthly', 'QEMPSTAT', lambda categories: categories.append(
            {'value': '7', 'label': 'Value to allocated value'}), 'frozen DDI labels differ'),
        ('asec', 'QOCCLY', lambda categories: categories.append(
            {'value': '2', 'label': 'Blank to value'}), 'frozen DDI labels differ'),
        ('monthly', 'QIND', relabel(4, 'Imputed'), 'monthly/QIND: unknown flag label'),
    ]
    for file, name, change, message in cases:
        with pytest.raises(ValueError, match=message):
            cps_flow_inputs.check_ddi(file, changed(file, name, change))


@pytest.mark.parametrize('case', ['missing_variable', 'unknown_file', 'shared_integer',
                                  'not_an_integer', 'changed_label_set', 'asec_flag_label',
                                  'empstat_label', 'actsame_label', 'qocc_label'])
def test_check_ddi_refusals(upstreams, case):
    selected = cps_flow_inputs.select_inputs(upstreams.data_dir, upstreams.request)
    file = 'asec' if case.startswith('asec') else 'monthly'
    ddi = json.loads(json.dumps(getattr(selected, file).ddi))
    variables = {item['name']: item for item in ddi['variables']}
    if case == 'missing_variable':
        ddi['variables'] = [item for item in ddi['variables'] if item['name'] != 'ACTSAME']
        message = 'monthly/ACTSAME: DDI variable missing'
    elif case == 'unknown_file':
        file, message = 'basic', 'unknown CPS file'
    elif case == 'shared_integer':
        variables['QIND']['categories'].append({'value': '05', 'label': 'Value to blank'})
        message = 'monthly/QIND: two DDI values share one integer'
    elif case == 'not_an_integer':
        variables['EMPSTAT']['categories'][0]['value'] = 'NIU'
        message = 'monthly/EMPSTAT: a DDI value is not an integer'
    elif case == 'changed_label_set':
        variables['QOCC']['categories'].pop()
        message = 'monthly/QOCC: frozen DDI labels differ'
    elif case == 'asec_flag_label':
        variables['QOCCLY']['categories'][1]['label'] = 'Imputed'
        message = 'asec/QOCCLY: unknown flag label'
    elif case == 'empstat_label':
        variables['EMPSTAT']['categories'][-1]['label'] = 'NILF, retired or disabled'
        message = 'monthly/EMPSTAT: frozen DDI labels differ'
    elif case == 'actsame_label':
        variables['ACTSAME']['categories'][3]['label'] = "Don't know"
        message = 'monthly/ACTSAME: frozen DDI labels differ'
    else:
        variables['QOCC']['categories'][7]['label'] = 'Blank to allocated value'
        message = 'monthly/QOCC: frozen DDI labels differ'
    with pytest.raises(ValueError, match=message):
        cps_flow_inputs.check_ddi(file, ddi)


def test_ddi_labels_and_flag_classes_are_the_frozen_tables():
    assert cps_flow_inputs.DDI_LABELS == EXPECTED_LABELS
    assert cps_flow_inputs.FLAG_CLASS_BY_LABEL == EXPECTED_CLASSES
    for labels in cps_flow_inputs.DDI_LABELS.values():
        for name in ('QEMPSTAT', 'QIND', 'QOCC', 'QOCCLY'):
            assert set(labels.get(name, {}).values()) <= set(EXPECTED_CLASSES)


def test_check_ddi_returns_a_copy(upstreams):
    selected = cps_flow_inputs.select_inputs(upstreams.data_dir, upstreams.request)
    rules = cps_flow_inputs.check_ddi('monthly', selected.monthly.ddi)
    rules['EMPSAME'][1] = 'changed'
    assert cps_flow_inputs.DDI_LABELS['monthly']['EMPSAME'][1] == 'No'


def test_stage4_schemas_and_pins_match_tri_codes():
    assert cps_flow_inputs.CODES_SCHEMA_VERSION == tri_codes.CODES_SCHEMA_VERSION
    assert cps_flow_inputs.CODES_SCHEMA_VERSION == code_build.SCHEMA_VERSION
    assert list(cps_flow_inputs.NODE_SCHEMA.items()) == list(tri_codes.NODE_SCHEMA.items())
    assert list(cps_flow_inputs.PATH_SCHEMA.items()) == list(
        classification_tables.PATH_SCHEMA.items())
    assert cps_flow_inputs.RUN_ID.pattern == tri_codes.RUN_ID.pattern
    assert cps_flow_inputs.PIN.pattern == tri_codes.PIN.pattern


def test_input_request_holds_the_twelve_fields_in_order():
    assert [field.name for field in dataclasses.fields(cps_flow_inputs.InputRequest)] == [
        'stage7_run', 'stage7_outputs_sha256', 'stage7_receipt', 'stage7_receipt_sha256',
        'stage8_receipt', 'stage8_receipt_sha256', 'stage8_mapping_run',
        'stage8_mapping_outputs_sha256', 'codes_run', 'codes_outputs_sha256', 'cps_receipt',
        'cps_receipt_sha256']
