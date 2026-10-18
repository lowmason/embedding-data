'''Synthetic complete Stage 4/5/7 bundles with independent detached pins.'''
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from code_fixtures import seed_code_tree
from geography_fixtures import seed_geography_tree
from target_fixtures import forbid_external_access
from test_ipums_verification_run import complete_inputs

from embedding_data import code_build, geography_build, ipums_verification_run, manifest

if TYPE_CHECKING:
    import polars as pl

    from embedding_data.acs_code_references import CodeEvidence
    from embedding_data.acs_mapping_inputs import SelectedInputs

@dataclass(frozen=True)
class FixtureInputs:
    data_dir: Path
    request: object
    sources: dict
    upstream_pins: dict


def seed_selected_inputs(tmp_path: Path, monkeypatch) -> FixtureInputs:
    from embedding_data.acs_mapping_inputs import SelectionRequest

    root, selection = complete_inputs.__wrapped__(tmp_path, monkeypatch)
    codes = code_build.build(root, 'fixture_codes', registry=seed_code_tree(root))
    geography = geography_build.build(root, 'fixture_geography',
                                      registry=seed_geography_tree(root))
    forbid_external_access(monkeypatch)
    run = ipums_verification_run.measure(root, 'fixture_ipums', 'references', selection)
    pins = {name: manifest.sha256_file(directory / 'outputs.json')
            for name, directory in [('codes', codes), ('geography', geography), ('ipums', run)]}
    receipt = root / 'raw/references/ipums-verification/references/receipt.json'
    request = SelectionRequest('fixture_codes', pins['codes'], 'fixture_geography',
                               pins['geography'], 'fixture_ipums', pins['ipums'],
                               manifest.sha256_file(receipt))
    import json
    sources = json.loads((run / 'inputs.json').read_text())['deliveries']
    return FixtureInputs(root, request, sources, pins)


def write_public_layout(file: Path, record: dict) -> None:
    '''Reconstruct a tiny public workbook while retaining original row/style locators.'''
    from xml.etree.ElementTree import Element, SubElement, tostring
    from zipfile import ZipFile

    if 'sheets' not in record:
        import base64
        body = (base64.b64decode(record['body_base64']) if 'body_base64' in record
                else record['body'].encode())
        file.write_bytes(body)
        return
    main = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    rel = 'http://schemas.openxmlformats.org/package/2006/relationships'
    office = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    workbook = Element('workbook', xmlns=main)
    sheets = SubElement(workbook, 'sheets')
    relationships = Element('Relationships', xmlns=rel)
    types = Element('Types', xmlns='http://schemas.openxmlformats.org/package/2006/content-types')
    SubElement(
        types,
        'Default',
        Extension='rels',
        ContentType='application/vnd.openxmlformats-package.relationships+xml',
    )
    SubElement(types, 'Default', Extension='xml', ContentType='application/xml')
    SubElement(
        types,
        'Override',
        PartName='/xl/workbook.xml',
        ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml',
    )
    root_relationships = Element('Relationships', xmlns=rel)
    SubElement(
        root_relationships,
        'Relationship',
        Id='rId1',
        Type=office + '/officeDocument',
        Target='xl/workbook.xml',
    )
    with ZipFile(file, 'w') as archive:
        for index, (name, sheet) in enumerate(record['sheets'].items(), 1):
            SubElement(
                sheets,
                'sheet',
                name=name,
                sheetId=str(index),
                attrib={f'{{{office}}}id': f'rId{index}'},
            )
            SubElement(
                relationships,
                'Relationship',
                Id=f'rId{index}',
                Type=office + '/worksheet',
                Target=f'worksheets/sheet{index}.xml',
            )
            SubElement(
                types,
                'Override',
                PartName=f'/xl/worksheets/sheet{index}.xml',
                ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml',
            )
            worksheet = Element('worksheet', xmlns=main)
            data = SubElement(worksheet, 'sheetData')
            for number, values in sheet['rows'].items():
                row = SubElement(data, 'row', r=number)
                for column, value in enumerate(values):
                    if value is None:
                        continue
                    letters, position = '', column + 1
                    while position:
                        position, remainder = divmod(position - 1, 26)
                        letters = chr(65 + remainder) + letters
                    address = letters + number
                    attrs = {'r': address, 't': 'inlineStr'}
                    if address in sheet.get('cell_styles', {}):
                        attrs['s'] = sheet['cell_styles'][address]
                    cell = SubElement(row, 'c', attrs)
                    SubElement(
                        SubElement(cell, 'is'),
                        't',
                        {'{http://www.w3.org/XML/1998/namespace}space': 'preserve'},
                    ).text = value
            archive.writestr(f'xl/worksheets/sheet{index}.xml', tostring(worksheet))
        if 'styles_xml' in record:
            archive.writestr('xl/styles.xml', record['styles_xml'])
            SubElement(
                relationships,
                'Relationship',
                Id='styles',
                Type=office + '/styles',
                Target='styles.xml',
            )
            SubElement(
                types,
                'Override',
                PartName='/xl/styles.xml',
                ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml',
            )
        if 'theme_xml' in record:
            archive.writestr('xl/theme/theme1.xml', record['theme_xml'])
            SubElement(relationships, 'Relationship', Id='theme',
                       Type=office + '/theme', Target='theme/theme1.xml')
            SubElement(types, 'Override', PartName='/xl/theme/theme1.xml',
                       ContentType='application/vnd.openxmlformats-officedocument.theme+xml')
        archive.writestr('[Content_Types].xml', tostring(types))
        archive.writestr('_rels/.rels', tostring(root_relationships))
        archive.writestr('xl/workbook.xml', tostring(workbook))
        archive.writestr('xl/_rels/workbook.xml.rels', tostring(relationships))


def seed_mapping_references(tmp_path, monkeypatch, *, original_overrides=None):
    '''Use every registered kind, with explicit independently computed excerpt pins.'''
    import json
    from dataclasses import replace
    from types import SimpleNamespace

    from embedding_data import acs_mapping_references as refs

    forbid_external_access(monkeypatch)
    layouts = json.loads(
        (Path(__file__).parent / 'fixtures/acs_mapping/reference-layouts.json').read_text()
    )['originals']
    originals = tmp_path / 'public-excerpts'
    originals.mkdir()
    files = {}
    registry = {}
    for kind, reference in refs.REGISTRY.items():
        file = originals / reference.filename
        if original_overrides and kind in original_overrides:
            file.write_bytes(original_overrides[kind].read_bytes())
        elif kind.endswith('_request'):
            file.write_bytes(refs.request_bytes(kind.removesuffix('_request')))
        else:
            write_public_layout(file, layouts[kind])
        files[kind] = file
        registry[kind] = replace(reference, sha256=manifest.sha256_file(file))
    monkeypatch.setattr(refs, 'REGISTRY', registry)
    root = tmp_path / 'data'
    for kind, file in files.items():
        refs.import_reference(root, 'fixture_references', kind, file)
    receipt = refs.reference_directory(root, 'fixture_references') / 'receipt.json'
    return SimpleNamespace(
        data_dir=root,
        reference_id='fixture_references',
        receipt_sha256=manifest.sha256_file(receipt),
        originals=files,
    )


@dataclass(frozen=True)
class FixtureCodeCase:
    '''Native-membership fixture calling the production lookup builder.'''
    observed: 'pl.DataFrame'
    evidence: 'CodeEvidence'
    selected: 'SelectedInputs'

    def build_lookup(self):
        from embedding_data.acs_code_mapping import build_code_lookup
        return build_code_lookup(self.observed, self.evidence, self.selected)


@pytest.fixture
def population_case(tmp_path, monkeypatch):
    '''Genuine-layout synthetic truth; reader-unit boundary, not an authenticated bundle.'''
    import csv
    import io
    import json
    from dataclasses import asdict
    from datetime import UTC, datetime
    from types import SimpleNamespace

    import polars as pl
    from geography_fixtures import STATE_ROWS, sheet, write_counties

    from embedding_data import geography_parsers as gp
    from embedding_data import geography_tables as gt
    from embedding_data import target_io
    from embedding_data.acs_area_references import read_area_evidence
    from embedding_data.acs_mapping_contract import SelectionRequest
    from embedding_data.acs_mapping_inputs import SelectedInputs
    from embedding_data.acs_mapping_references import WORKBOOK_LAYOUTS, ReferenceSnapshot

    forbid_external_access(monkeypatch)
    import httpx

    from embedding_data import ipums_census_access

    def forbidden(*args, **kwargs):
        raise AssertionError('offline population reference attempted external access')

    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, 'handle_async_request', forbidden)
    monkeypatch.setattr(ipums_census_access, 'read_credential', forbidden)

    root = tmp_path / 'population-data'
    raw = root / 'raw'
    raw.mkdir(parents=True)
    county_file = raw / 'counties.zip'
    public = Path(__file__).parent / 'fixtures/acs_mapping/geography/ct-inventory.json'
    ct = json.loads(public.read_text())['rows']
    write_counties(
        county_file,
        [
            ['AL', '01001', 'Autauga County'],
            ['AL', '01003', 'Baldwin County'],
            *ct,
            ['PR', '72001', 'Adjuntas Municipio'],
        ],
    )
    citation = manifest.describe_file(
        county_file,
        raw,
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        client='fixture',
        client_version='1',
    )
    manifest.append_entries(raw / 'manifest.jsonl', [citation])
    counties = gp.parse_counties(county_file)
    states = gp.parse_states(sheet(STATE_ROWS), scope=frozenset({'01', '09', '51'}))
    members = pl.DataFrame(
        [
            ['01001', '01', '10000', 'Synthetic metro', 'metropolitan', 'central'],
            ['09110', '09', '10000', 'Synthetic metro', 'metropolitan', 'outlying'],
            ['01003', '01', '20000', 'Synthetic micro', 'micropolitan', 'central'],
        ],
        schema=gp.MEMBER_SCHEMA,
        orient='row',
    )
    tables = gt.assemble({**states, 'counties': counties, 'members': members})
    geography = {}
    for name, frame in tables.items():
        geography[name] = root / (name + '.parquet')
        frame.write_parquet(geography[name])
    selected = SelectedInputs(
        root,
        SelectionRequest(*(['fixture'] * 7)),
        {},
        {},
        geography,
        {
            'geography': {
                'tables': {n: target_io.file_record(p) for n, p in geography.items()},
                'raw': [json.loads(json.dumps(asdict(citation)))],
                'inputs': {
                    'raw': [json.loads(json.dumps(asdict(citation)))],
                    'references': {'counties_2025': {'relative': 'counties.zip'}},
                },
            }
        },
        {},
    )
    directory = root / 'references'
    directory.mkdir()
    layouts = json.loads(
        (Path(__file__).parent / 'fixtures/acs_mapping/reference-layouts.json').read_text()
    )['originals']
    files = {}
    pumas = [('01', '00100', 100), ('01', '00200', 300), ('09', '20100', 200), ('72', '00100', 10)]
    county_controls = [
        ('01', '01001', 60),
        ('01', '01003', 340),
        ('09', '09110', 200),
        ('72', '72001', 10),
    ]
    groups = [
        ('01', '00100', '001', '00100'),
        ('01', '00200', '001', '00100'),
        ('09', '20100', '009', '20100'),
        ('72', '00100', '072', '00100'),
    ]
    county_groups = [
        ('01', '001', '001', '00100'),
        ('01', '003', '001', '00100'),
        ('09', '110', '009', '20100'),
        ('72', '001', '072', '00100'),
    ]
    msa_rows = [
        [
            '10000',
            'Synthetic metro',
            '01',
            'Alabama',
            '00100',
            'Synthetic',
            '260',
            '100',
            '60',
            '23.0769',
            '60',
        ],
        [
            '10000',
            'Synthetic metro',
            '09',
            'Connecticut',
            '20100',
            'Synthetic',
            '260',
            '200',
            '200',
            '76.9231',
            '100',
        ],
    ]
    for kind, body in [
        ('puma_composition_2020', groups),
        ('county_composition_2022', county_groups),
        ('msa_puma_2023_2020', msa_rows),
    ]:
        name, (_, header) = next(iter(WORKBOOK_LAYOUTS[kind].items()))
        file = directory / (kind + '.xlsx')
        write_public_layout(
            file,
            {
                'sheets': {
                    name: {'rows': {str(i): row for i, row in enumerate([header, *body], 1)}}
                }
            },
        )
        files[kind] = file
    intersections = [
        ('01', '00100', '01001', 60, '1', '.6'),
        ('01', '00100', '01003', 40, '0.1176', '.4'),
        ('01', '00200', '01003', 300, '0.8824', '1'),
        ('09', '20100', '09110', 200, '1', '1'),
        ('72', '00100', '72001', 10, '1', '1'),
    ]
    for kind in ['geocorr_intersections', 'geocorr_puma_totals', 'geocorr_county_totals']:
        original = list(csv.reader(io.StringIO(layouts[kind]['body'])))
        headers, labels = original[:2]
        records = []
        values = (
            intersections
            if kind == 'geocorr_intersections'
            else (pumas if kind == 'geocorr_puma_totals' else county_controls)
        )
        for value in values:
            record = dict.fromkeys(headers, 'Synthetic')
            if kind == 'geocorr_intersections':
                state, puma, county, pop, reverse, forward = value
                record.update(
                    state=state,
                    puma22=puma,
                    county=county,
                    pop20=pop,
                    afact=forward,
                    afact2=reverse,
                )
            else:
                state, code, pop = value
                record.update(state=state, pop20=pop, afact='1', afact2='1')
                record['puma22' if kind == 'geocorr_puma_totals' else 'county'] = code
            records.append([record[h] for h in headers])
        file = directory / (kind + '.csv')
        with file.open('w', newline='') as output:
            csv.writer(output).writerows([headers, labels, *records])
        files[kind] = file

    def snapshot():
        receipt = {'originals': {k: {'sha256': manifest.sha256_file(p)} for k, p in files.items()}}
        (directory / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True))
        return ReferenceSnapshot(
            'population_fixture',
            directory,
            files.copy(),
            receipt,
            manifest.sha256_file(directory / 'receipt.json'),
        )

    def mutate_csv(kind, column, value):
        file = files[kind]
        with file.open(newline='') as source:
            rows = list(csv.reader(source))
        rows[2][rows[0].index(column)] = value
        with file.open('w', newline='') as output:
            csv.writer(output).writerows(rows)
        return snapshot()

    reference = snapshot()
    return SimpleNamespace(
        selected=selected,
        snapshot=reference,
        evidence=read_area_evidence(reference, selected),
        mutate_csv=mutate_csv,
        repin=snapshot,
    )
