'''Synthetic complete Stage 4/5/7 bundles with independent detached pins.'''
from dataclasses import dataclass
from pathlib import Path

from code_fixtures import seed_code_tree
from geography_fixtures import seed_geography_tree
from target_fixtures import forbid_external_access
from test_ipums_verification_run import complete_inputs

from embedding_data import code_build, geography_build, ipums_verification_run, manifest

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
