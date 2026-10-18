'''Synthetic complete Stage 4/5/7 bundles with independent detached pins.'''
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from code_fixtures import seed_code_tree
from geography_fixtures import seed_geography_tree
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


def seed_mapping_references(tmp_path, monkeypatch, *, original_overrides=None, data_dir=None,
                            reference_id='fixture_references',
                            reference_version='acs-mapping-references-v1'):
    '''Use every registered kind, with explicit independently computed excerpt pins.'''
    import json
    from dataclasses import replace
    from types import SimpleNamespace

    from target_fixtures import forbid_external_access as forbid_fixture_access

    from embedding_data import acs_mapping_references as refs

    # Shared raw setup also serves mocked acquisition; strict callers keep their guard.
    forbid_fixture_access(monkeypatch)
    layouts = json.loads(
        (Path(__file__).parent / 'fixtures/acs_mapping/reference-layouts.json').read_text()
    )['originals']
    originals = tmp_path / 'public-excerpts'
    originals.mkdir()
    files = {}
    registry = {}
    for kind, reference in refs.registry_for_version(reference_version).items():
        file = originals / reference.filename
        if original_overrides and kind in original_overrides:
            file.write_bytes(original_overrides[kind].read_bytes())
        elif kind in {'pums_five_year_guide', 'usa_migplac1'}:
            import gzip
            public = Path(__file__).parent / 'fixtures/acs_mapping/roles'
            file.write_bytes(gzip.decompress((public / (reference.filename + '.gz')).read_bytes()))
        elif kind.endswith('_request'):
            file.write_bytes(refs.request_bytes(kind.removesuffix('_request')))
        else:
            write_public_layout(file, layouts[kind])
        files[kind] = file
        registry[kind] = replace(reference, sha256=manifest.sha256_file(file))
    monkeypatch.setattr(refs, 'REGISTRY', {k: r for k, r in registry.items()
                                           if k in refs.REGISTRY})
    if reference_version == 'acs-mapping-references-v2':
        monkeypatch.setattr(refs, 'CT_REGISTRY', {k: r for k, r in registry.items()
                                                  if k in refs.CT_REGISTRY})
    root = data_dir if data_dir is not None else tmp_path / 'data'
    for kind, file in files.items():
        refs.import_reference(root, reference_id, kind, file,
                              reference_version=reference_version)
    receipt = refs.reference_directory(root, reference_id) / 'receipt.json'
    return SimpleNamespace(
        data_dir=root,
        reference_id=reference_id,
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


@pytest.fixture
def role_case(population_case):
    '''Role evidence uses public excerpts and clearly synthetic delivered keys.'''
    import json
    from types import SimpleNamespace

    import polars as pl

    from embedding_data.acs_area_mapping import OBSERVED_AREA_SCHEMA
    from embedding_data.acs_area_references import read_role_rules
    from embedding_data.acs_geography_factors import build_factor_tables
    from embedding_data.acs_mapping_contract import SourceInput
    from embedding_data.acs_mapping_references import ReferenceSnapshot

    case = population_case
    originals = json.loads(
        (Path(__file__).parent / 'fixtures/acs_mapping/reference-layouts.json').read_text()
    )['originals']
    files = dict(case.snapshot.files)
    for kind in [
        'usa_puma', 'usa_pwpuma00', 'usa_migpuma1', 'usa_pwstate2', 'usa_migplac1', 'usa_multyear'
    ]:
        file = case.snapshot.directory / (kind + '.html')
        file.write_text(originals[kind]['body'])
        files[kind] = file
    import gzip
    public = Path(__file__).parent / 'fixtures/acs_mapping/roles'
    for name in ('pums_five_year_guide.pdf', 'usa_migplac1.html'):
        file = case.snapshot.directory / name
        file.write_bytes(gzip.decompress((public / (name + '.gz')).read_bytes()))
        files[name.rsplit('.', 1)[0]] = file
    receipt = {'originals': {k: {'sha256': manifest.sha256_file(p)} for k, p in files.items()}}
    receipt_file = case.snapshot.directory / 'receipt.json'
    receipt_file.write_text(json.dumps(receipt, sort_keys=True))
    snapshot = ReferenceSnapshot(
        'role_fixture', case.snapshot.directory, files, receipt, manifest.sha256_file(
            receipt_file
        )
    )
    states = [('01', 'Alabama'), ('09', 'Connecticut'), ('72', 'Puerto Rico')]
    categories = {
        'PUMA': [],
        'PWPUMA00': [],
        'MIGPUMA1': [],
        'STATEFIP': states,
        'PWSTATE2': [*states, ('00', 'N/A'), ('80', 'Abroad'), ('99', 'Not reported')],
        'MIGPLAC1': [
            ('001', 'Alabama'), ('009', 'Connecticut'), ('000', 'N/A'), ('110', 'Puerto Rico'),
            ('150', 'Canada'), ('997', 'Unknown value'), ('999', 'Missing'),
            ('988', 'Suppressed for data year 2022 for select cases')
        ],
        'SAMPLE': [('202301', '2023 ACS'), ('202401', '2024 ACS')],
    }
    file = case.snapshot.directory / 'source.parquet'
    pl.DataFrame(
        {
            'YEAR': [2024] * 3,
            'SAMPLE': [202401] * 3,
            'STATEFIP': [1] * 3,
            'PUMA': [100] * 3,
            'PWSTATE2': [1] * 3,
            'PWPUMA00': [100] * 3,
            'MIGPLAC1': [1] * 3,
            'MIGPUMA1': [100] * 3
        }
    ).write_parquet(file)
    ddi_file = case.snapshot.directory / 'synthetic.xml'
    ddi_file.write_text('<synthetic-ddi>' + json.dumps(categories) + '</synthetic-ddi>')
    source = SourceInput(
        'acs/core', 'synthetic', file, {}, [
            {
                'path': ddi_file.name,
                'sha256': manifest.sha256_file(ddi_file)
            }
        ], {'samples': {
            'us2023a': {},
            'us2024a': {}
        }}, {
            'variables': [
                {
                    'name': name,
                    'categories': [{
                        'value': code,
                        'label': label
                    } for code, label in values]
                } for name, values in categories.items()
            ]
        }
    )
    five = SourceInput(
        'acs/five_year', 'synthetic_five', file, {}, source.raw_citations, {
            'samples': {
                'us2024c': {}
            }
        }, source.ddi
    )
    rules = read_role_rules(snapshot, {'core': source, 'five_year': five})

    def observed(role, state, area):
        return pl.DataFrame(
            [
                dict(
                    profile='acs/core',
                    sample_id='us2024a',
                    release_year=2024,
                    component_year=2024,
                    role=role,
                    source_state_code=state,
                    source_area_code=area,
                    rows=1
                )
            ],
            schema=OBSERVED_AREA_SCHEMA
        )

    return SimpleNamespace(
        observed=observed,
        rules=rules,
        evidence=case.evidence,
        factors=build_factor_tables(case.evidence, case.selected),
        source=source,
        snapshot=snapshot,
        source_columns={
            'residence': 'PUMA',
            'workplace': 'PWPUMA00',
            'migration': 'MIGPUMA1'
        }
    )


@pytest.fixture
def companion_case(tmp_path, role_case, evidence, selected):
    '''Converted synthetic deliveries plus real reader-unit lookup/factor builders.

    These are honest unit evidence objects, not selector-authenticated bundles.
    The vintage concordance is an explicitly synthetic identity relation restricted
    to the selected public 113M members. Task8 owns the authenticated build chain.
    '''
    import csv
    import gzip
    import io
    import json
    from dataclasses import replace
    from types import SimpleNamespace
    from xml.etree.ElementTree import Element, SubElement, tostring

    import polars as pl
    from code_fixtures import pair_sheet

    from embedding_data import ipums_conversion, ipums_ddi, target_io
    from embedding_data.acs_area_mapping import build_area_lookup, observed_area_keys
    from embedding_data.acs_area_references import read_role_rules
    from embedding_data.acs_code_mapping import build_code_lookup, observed_code_keys
    from embedding_data.acs_mapping_contract import SourceInput
    from embedding_data.naics_relationships import parse_concordance

    native = evidence.metadata.filter(
        pl.col('source_scheme').eq('naics2017').and_(pl.col('source_token').eq('113M'))
    ).row(0, named=True)
    relation = parse_concordance(
        pair_sheet(2017, 2022, [(c, c) for c in native['native_finest_candidates']]),
        2017, 2022, 'synthetic-companion-identity.xlsx'
    )
    relation_path = tmp_path / 'synthetic-concordance.parquet'
    relation.write_parquet(relation_path)
    selected = replace(selected, codes={**selected.codes, 'naics_concordance': relation_path})
    profiles = {}
    for profile, years in [('core', [2023, 2024, 2024, 2024, 2024, 2024]),
                           ('vintage', [2022] * 6), ('five_year', [2024] * 6)]:
        directory = tmp_path / ('converted-' + profile)
        directory.mkdir()
        product = 'acs/' + profile
        samples = {'core': {'us2023a': {}, 'us2024a': {}},
                   'vintage': {'us2022a': {}}, 'five_year': {'us2024c': {}}}[profile]
        categories = {
            'SAMPLE': [(s[2:6] + '01', f'{s[2:6]} ACS') for s in samples],
            'STATEFIP': [('01', 'Alabama'), ('09', 'Connecticut'), ('72', 'Puerto Rico')],
            'PUMA': [], 'PWPUMA00': [], 'MIGPUMA1': [],
            'PWSTATE2': [('01', 'Alabama'), ('09', 'Connecticut'), ('72', 'Puerto Rico'),
                         ('00', 'N/A'), ('80', 'Abroad'), ('99', 'Not reported')],
            'MIGPLAC1': [('001', 'Alabama'), ('009', 'Connecticut'), ('000', 'N/A'),
                         ('110', 'Puerto Rico'), ('150', 'Canada'), ('997', 'Unknown value'),
                         ('999', 'Missing'),
                         ('988', 'Suppressed for data year 2022 for select cases')],
            'QIND': [('0', 'Original entry or Inapplicable (not in universe)'),
                     ('1', 'Failed edit'), ('4', 'Allocated')],
            'QOCC': [('0', 'Entered as written'), ('4', 'Allocated'), ('8',
                      'Original entry missing or failed edit')],
        }
        if profile == 'five_year':
            categories['SAMPLE'] = [('202401', '2020-2024, ACS 5-year')]
        if profile != 'vintage':
            categories['QMIGRAT1'] = [('0', 'Not allocated'), ('4', 'Allocated')]
        metadata = Element('codeBook')
        variables = SubElement(metadata, 'dataDscr')
        for name, values in categories.items():
            var = SubElement(variables, 'var', name=name)
            for value, label in values:
                category = SubElement(var, 'catgry')
                SubElement(category, 'catValu').text = value
                SubElement(category, 'labl').text = label
        ddi_path = directory / 'delivery.xml'
        ddi_path.write_bytes(tostring(metadata))
        definition = {'collection': 'usa', 'dataFormat': 'csv', 'samples': samples,
                      'variables': {'IND': {}, 'OCC': {}}, 'dataQualityFlags': True}
        definition_path = directory / 'extract.json'
        definition_path.write_text(json.dumps(definition))
        token = '113M' if profile == 'vintage' else '2212P'
        ind = evidence.metadata.filter(pl.col('source_scheme').eq(
            'naics2017' if profile == 'vintage' else 'naics2022'
        ).and_(pl.col('source_token').eq(token))).row(0, named=True)
        rows = []
        for index, year in enumerate(years):
            row = dict(YEAR=year, SAMPLE=year * 100 + 1, IND=ind['paired_census_code'],
                       INDNAICS=' ' + token + ' ', OCC='9830', OCCSOC='559830',
                       STATEFIP=1, PUMA=200 if index == 1 else 100,
                       PWSTATE2=[1, 1, 0, 80, 72, 1][index],
                       PWPUMA00=[100, 100, 0, 1, 100, 100][index],
                       MIGPLAC1=[1, 1, 0, 150, 110, 1][index],
                       MIGPUMA1=[100, 100, 0, 1, 100, 100][index],
                       QIND=[4, 0, 1, None, 0, 4][index],
                       QOCC=[0, 4, 8, None, 0, 0][index])
            if profile == 'five_year':
                row['MULTYEAR'] = [2020, 2021, 2022, 2023, 2024, 2020][index]
            if profile != 'vintage':
                row['QMIGRAT1'] = None if profile == 'core' else [0, 4, 0, None, 0, 0][index]
            rows.append(row)
        rows[-1] = rows[0].copy()  # Deliberate exact duplicate retained by conversion.
        text = io.StringIO()
        writer = csv.DictWriter(text, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        raw = directory / 'delivery.csv.gz'
        with gzip.open(raw, 'wt') as output:
            output.write(text.getvalue())
        parquet = directory / 'delivery.parquet'
        ipums_conversion.convert(raw, parquet, 'acs')
        citations = [{'path': f'{directory.name}/{p.name}',
                      'sha256': manifest.sha256_file(p)} for p in [raw, ddi_path, definition_path]]
        profiles[profile] = SimpleNamespace(source=SourceInput(
            product, profile + '-fixture', parquet, target_io.file_record(parquet), citations,
            ipums_ddi.read_definition(definition_path), ipums_ddi.read_ddi(ddi_path)
        ))
    sources = {k: v.source for k, v in profiles.items()}
    codes = build_code_lookup(observed_code_keys(sources), evidence, selected)
    rules = read_role_rules(role_case.snapshot, sources)
    areas = build_area_lookup(observed_area_keys(sources), rules, role_case.evidence,
                              role_case.factors)
    for case in profiles.values():
        case.codes, case.areas, case.factors = codes, areas, role_case.factors
    return SimpleNamespace(**vars(profiles['core']), profiles=profiles)


def forbid_external_access(monkeypatch):
    '''Deny client construction as well as network, dotenv and credential seams.'''
    import dotenv
    import httpx
    import ipumspy
    from target_fixtures import forbid_external_access as forbid_base

    from embedding_data import acs_mapping_references, ipums_census_access, ipums_references

    forbid_base(monkeypatch)

    def forbidden(*args, **kwargs):
        raise AssertionError('offline ACS mapping attempted external access')

    for owner, names in (
        (httpx, ('Client', 'AsyncClient')),
        (dotenv, ('load_dotenv', 'dotenv_values')),
        (ipumspy, ('IpumsApiClient',)),
        (ipums_census_access, ('dotenv_values', 'read_credential')),
        (ipums_references, ('make_client',)),
        (acs_mapping_references, ('make_client',)),
    ):
        for name in names:
            monkeypatch.setattr(owner, name, forbidden)


def _authenticated_deliveries(data_dir, directory, monkeypatch, *, prepare_acs=None):
    '''Manifest definitions/DDI/gzip CSV before the unchanged converter is invoked.'''
    import gzip
    import json
    from dataclasses import replace
    from datetime import UTC, datetime
    from xml.etree import ElementTree as ET

    import polars as pl
    from ipums_fixtures import bls_response, reference_originals
    from test_ipums_acceptance import PROFILES, delivery

    from embedding_data import ipums_conversion, ipums_references, paths

    originals = reference_originals(directory / 'stage7-originals', ipums_references.REGISTRY)
    public = Path(__file__).parent / 'fixtures/acs_mapping/classification'
    for year in (2017, 2022):
        originals[f'census_industry_{year}'].write_bytes(
            (public / f'census_industry_{year}.xlsx').read_bytes())
    originals['cps_employment'].write_text(json.dumps(bls_response()))
    originals['usa_samples'].write_text(
        '<table><tr><th>Sample ID</th><th>Description</th></tr>'
        + ''.join(f'<tr><td>{key}</td><td>{label}</td></tr>' for key, label in
                  delivery()[-1].items()) + '</table>')
    for year in (2023, 2024):
        file = originals[f'acs_{year}_b23025_metadata']
        file.write_text(file.read_text().replace(
            '<td>B23025_004E</td>', '<td>B23025_004E</td>'
            '<td>Estimate!!Civilian labor force:!!Employed</td>')
            + '<p>Population 16 years and over</p>')
    monkeypatch.setattr(ipums_references, 'REGISTRY', {
        kind: replace(reference, sha256=manifest.sha256_file(originals[kind]))
        if reference.sha256 else reference
        for kind, reference in ipums_references.REGISTRY.items()})
    for kind, file in originals.items():
        ipums_references.import_reference(data_dir, 'references', kind, file)
    selections = {}
    for index, (source, profile) in enumerate(PROFILES, 1):
        definition, ddi, frame, _, _, _ = delivery(source, profile)
        frame = frame.with_columns(pl.lit(30).alias('AGE'))
        if source == 'acs':
            frame = frame.with_columns(
                pl.lit(10).alias('EMPSTATD'), pl.lit('113M').alias('INDNAICS'),
                pl.lit(190).alias('IND'), pl.lit('559830').alias('OCCSOC'),
                pl.lit(9830).alias('OCC'), pl.lit('100.25').alias('PERWT'),
                pl.lit(100).alias('PUMA'), pl.lit(1).alias('PWSTATE2'),
                pl.lit(100).alias('PWPUMA00'), pl.lit(1).alias('MIGPLAC1'),
                pl.lit(100).alias('MIGPUMA1'))
            states = [('01', 'Alabama'), ('09', 'Connecticut'), ('72', 'Puerto Rico')]
            categories = {
                'STATEFIP': states, 'PUMA': [], 'PWPUMA00': [], 'MIGPUMA1': [],
                'PWSTATE2': [*states, ('00', 'N/A'), ('80', 'Abroad'), ('99', 'Not reported')],
                'MIGPLAC1': [('001', 'Alabama'), ('009', 'Connecticut'), ('000', 'N/A'),
                             ('110', 'Puerto Rico'), ('150', 'Canada'), ('997', 'Unknown value'),
                             ('999', 'Missing'), ('988', 'Suppressed for data year 2022')],
            }
            for variable in ddi['variables']:
                name = variable['name']
                if name in categories:
                    variable['categories'] = [{'value': code, 'label': label}
                                              for code, label in categories[name]]
        else:
            frame = frame.with_columns(pl.lit(10).alias('EMPSTAT'),
                                       pl.lit('0170').alias('IND'), pl.lit('0010').alias('OCC'))
            if profile == 'monthly':
                frame = frame.with_columns(pl.lit('123.5').alias('WTFINL'))
            else:
                frame = frame.with_columns(pl.lit('0180').alias('INDLY'),
                                           pl.lit('0010').alias('OCCLY'))
        if source == 'acs' and prepare_acs is not None:
            ddi, frame = prepare_acs(profile, ddi, frame)
        if source == 'acs' and profile == 'core':
            frame = pl.concat([frame, frame.head(1)])  # Genuine duplicate in manifested CSV.
        collection = 'usa' if source == 'acs' else 'cps'
        name = f'{collection}_{index}'
        raw = data_dir / 'raw' / source / profile / name
        raw.mkdir(parents=True)
        (raw / 'extract.json').write_text(json.dumps(definition))
        xml = ET.Element('codeBook', version='2.5')
        info = ET.SubElement(ET.SubElement(xml, 'stdyDscr'), 'stdyInfo')
        for note in ddi['study_notes']:
            ET.SubElement(info, 'notes').text = note
        summary = ET.SubElement(info, 'sumDscr')
        for note in ddi['time_notes']:
            ET.SubElement(summary, 'timePrd', date=note['date']).text = note['text']
        data = ET.SubElement(xml, 'dataDscr')
        for variable in ddi['variables']:
            element = ET.SubElement(data, 'var', name=variable['name'], dcml='2')
            ET.SubElement(element, 'labl').text = variable['label']
            for category in variable['categories']:
                item = ET.SubElement(element, 'catgry')
                ET.SubElement(item, 'catValu').text = category['value']
                ET.SubElement(item, 'labl').text = category['label']
        ET.ElementTree(xml).write(raw / f'{name}.xml')
        with gzip.open(raw / f'{name}.csv.gz', 'wt') as output:
            output.write(frame.collect().write_csv())
        for file in raw.iterdir():
            manifest.append_entries(paths.manifest_path(data_dir), [manifest.describe_file(
                file, data_dir / 'raw', retrieved_at=datetime.now(UTC), client='fixture',
                client_version='1', collection=collection, extract_number=index,
                samples=list(definition['samples']))])
        parquet = data_dir / f'derived/{source}/{profile}/{name}.parquet'
        parquet.parent.mkdir(parents=True)
        ipums_conversion.convert(raw / f'{name}.csv.gz', parquet, source)
        selections[f'{source}/{profile}'] = {
            'delivery': name, 'parquet': parquet.relative_to(data_dir).as_posix()}
    selection = directory / 'selection.json'
    selection.write_text(json.dumps(selections))
    return selection


def _authenticated_codes(data_dir, directory):
    import hashlib
    import json
    import shutil
    from zipfile import ZipFile

    from embedding_data import code_references, paths

    # The existing synthetic summary is created by the genuine fixture builder.
    summary_root = directory / 'summary-seed'
    seed_code_tree(summary_root)
    for file in (summary_root / 'raw/osha').rglob('*'):
        if file.is_file():
            target = data_dir / 'raw' / file.relative_to(summary_root / 'raw')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, target)
            entry = manifest.recorded_entry_for(paths.manifest_path(summary_root), file)
            manifest.append_entries(paths.manifest_path(data_dir), [entry])
    summary = data_dir / 'derived/osha/ita_300a_summary.parquet'
    summary.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(summary_root / 'derived/osha/ita_300a_summary.parquet', summary)
    assets = Path(__file__).parent / 'fixtures/acs_mapping/upstream'
    records = json.loads((assets / 'provenance.json').read_text())['originals']
    with ZipFile(assets / 'stage4-originals.zip') as archive:
        for record in records:
            body = archive.read(record['path'])
            assert len(body) == record['size']
            assert hashlib.sha256(body).hexdigest() == record['sha256']
            file = directory / Path(record['path']).name
            file.write_bytes(body)
            code_references.import_reference(data_dir, record['kind'], file)
    return code_build.build(data_dir, 'fixture_codes')


def _authenticated_geography(data_dir, directory, *, original_overrides=None):
    import json

    from code_fixtures import write_xlsx
    from geography_fixtures import MEMBER_HEADER, fixture_registry, originals, write_counties

    from embedding_data import geography_references

    files = originals(directory / 'stage5-originals')
    ct = json.loads((Path(__file__).parent / 'fixtures/acs_mapping/geography/ct-inventory.json')
                    .read_text())['rows']
    write_counties(files['counties_2025'], [
        ['AL', '01001', 'Autauga County'], ['AL', '01003', 'Baldwin County'], *ct,
        ['VA', '51001', 'Accomack County'], ['VA', '51510', 'Alexandria city'],
        ['PR', '72001', 'Adjuntas Municipio']])
    rows = [
        ['Table with row headers in column A and column headers in row 3'] + [None] * 11,
        ['List 1. Synthetic July 2023 delineations'] + [None] * 11, MEMBER_HEADER,
    ]
    for code, title, kind, county, state, sf, cf, role in [
        ('10000', 'Synthetic metro', 'Metropolitan', 'Autauga County', 'Alabama',
         '01', '001', 'Central'),
        ('10000', 'Synthetic metro', 'Metropolitan', 'Capitol Planning Region', 'Connecticut',
         '09', '110', 'Outlying'),
        ('20000', 'Synthetic micro', 'Micropolitan', 'Baldwin County', 'Alabama',
         '01', '003', 'Central'),
    ]:
        rows.append([code, None, None, title, kind + ' Statistical Area', None, None,
                     county, state, sf, cf, role])
    write_xlsx(files['cbsa_2023'], rows)
    if original_overrides:
        for kind, original in original_overrides.items():
            files[kind].write_bytes(original.read_bytes())
    registry = fixture_registry(files)
    if original_overrides:
        from dataclasses import replace

        from embedding_data.geography_parsers import SCOPE
        registry = {kind: replace(reference, state_scope=SCOPE)
                    for kind, reference in registry.items()}
    for kind, file in files.items():
        geography_references.import_reference(data_dir, kind, file, registry=registry)
    return geography_build.build(data_dir, 'fixture_geography', registry=registry)


def run_acs_mapping_v12(data_dir: Path, monkeypatch) -> dict[str, Path]:
    '''Genuine fixture-only raw→conversion→Stage4/5/7→selected→Stage8 replay chain.'''
    import json

    from embedding_data import acs_mapping_bundle as bundle
    from embedding_data.acs_mapping_contract import SelectionRequest
    from embedding_data.acs_mapping_inputs import select_inputs

    forbid_external_access(monkeypatch)
    directory = data_dir.parent / 'authenticated-setup'
    directory.mkdir()
    selection = _authenticated_deliveries(data_dir, directory, monkeypatch)
    codes = _authenticated_codes(data_dir, directory)
    geography = _authenticated_geography(data_dir, directory)
    ipums = ipums_verification_run.measure(data_dir, 'fixture_ipums', 'references', selection)
    request = SelectionRequest(
        'fixture_codes', manifest.sha256_file(codes / 'outputs.json'),
        'fixture_geography', manifest.sha256_file(geography / 'outputs.json'),
        'fixture_ipums', manifest.sha256_file(ipums / 'outputs.json'),
        manifest.sha256_file(
            data_dir / 'raw/references/ipums-verification/references/receipt.json'))
    selected = select_inputs(data_dir, request)
    selected.verify()
    # Reuse synthetic raw geographic originals, never its assembled unit-test tables.
    population = population_case.__wrapped__(directory, monkeypatch)
    public = Path(__file__).parent / 'fixtures/acs_mapping/classification'
    overrides = {f.stem: f for f in public.glob('*.xlsx')
                 if not f.stem.startswith('census_industry_')}
    release = directory / 'release-excerpts'
    release.mkdir()
    for kind, record in json.loads((public / 'release-layouts.json').read_text()).items():
        file = release / (kind + '.xlsx')
        write_public_layout(file, record)
        overrides[kind] = file
    overrides.update(population.snapshot.files)
    references = seed_mapping_references(
        data_dir.parent, monkeypatch, original_overrides=overrides, data_dir=data_dir)
    assert references.data_dir == data_dir
    results = {'data_dir': data_dir}
    for name in ('first', 'replay'):
        response = bundle.build(data_dir, name, request, references.reference_id,
                                 expected_reference_receipt_sha256=references.receipt_sha256)
        results[name] = Path(response['directory'])
        control = directory / (name + '-build-response.json')
        control.write_text(json.dumps(response, sort_keys=True) + '\n')
        results[name + '_control'] = control
        bundle.verify_bundle(results[name], data_dir,
                             expected_outputs_sha256=response['outputs_sha256'])
    return results


def seed_reconciliation_inputs(tmp_path, monkeypatch, *, prepare_acs=None):
    '''Freeze-ready authenticated upstreams; no Stage 8 snapshot exists yet.'''
    import json

    from embedding_data.acs_mapping_contract import SelectionRequest
    from embedding_data.acs_mapping_inputs import select_inputs

    forbid_external_access(monkeypatch)
    data_dir = tmp_path / 'data'
    directory = tmp_path / 'authenticated-setup'
    directory.mkdir()
    selection = _authenticated_deliveries(
        data_dir, directory, monkeypatch, prepare_acs=prepare_acs or _reconciliation_delivery)
    codes = _authenticated_codes(data_dir, directory)
    geography = _authenticated_geography(data_dir, directory)
    ipums = ipums_verification_run.measure(data_dir, 'fixture_ipums', 'references', selection)
    pins = {name: manifest.sha256_file(path / 'outputs.json') for name, path in (
        ('codes', codes), ('geography', geography), ('ipums', ipums))}
    request = SelectionRequest(
        'fixture_codes', pins['codes'], 'fixture_geography', pins['geography'],
        'fixture_ipums', pins['ipums'], manifest.sha256_file(
            data_dir / 'raw/references/ipums-verification/references/receipt.json'))
    select_inputs(data_dir, request).verify()
    return FixtureInputs(data_dir, request,
                         json.loads((ipums / 'inputs.json').read_text())['deliveries'], pins)


def build_fixture_mapping(fixture, run_id, monkeypatch):
    '''Import originals only after callers freeze their independent before-state.'''
    import json

    from embedding_data import acs_mapping_bundle as bundle

    directory = fixture.data_dir.parent / ('mapping-setup-' + run_id)
    directory.mkdir()
    population = population_case.__wrapped__(directory, monkeypatch)
    public = Path(__file__).parent / 'fixtures/acs_mapping/classification'
    overrides = {f.stem: f for f in public.glob('*.xlsx')
                 if not f.stem.startswith('census_industry_')}
    release = directory / 'release-excerpts'
    release.mkdir()
    for kind, record in json.loads((public / 'release-layouts.json').read_text()).items():
        file = release / (kind + '.xlsx')
        write_public_layout(file, record)
        overrides[kind] = file
    overrides.update(population.snapshot.files)
    references = seed_mapping_references(
        directory, monkeypatch, original_overrides=overrides, data_dir=fixture.data_dir,
        reference_id=run_id + '_references')
    forbid_external_access(monkeypatch)
    return bundle.build(fixture.data_dir, run_id, fixture.request, references.reference_id,
                        expected_reference_receipt_sha256=references.receipt_sha256)



def _reconciliation_delivery(profile, ddi, frame):
    '''Put edge cases in manifested raw originals before any unchanged upstream work.'''
    import polars as pl

    if profile == 'core':
        frame = frame.with_columns(
            pl.Series('OCC', [9830, 10, 20]),
            pl.Series('OCCSOC', ['559830', '1110XX', '111021']),
            pl.Series('INDNAICS', ['113M', '113M', None], dtype=pl.String),
            pl.Series('PWSTATE2', [0, 80, 72]), pl.Series('PWPUMA00', [0, 1, 100]),
            pl.Series('MIGPLAC1', [110, 150, 1]), pl.Series('MIGPUMA1', [2, 1, 100]),
            pl.Series('QIND', [0, 1, None], dtype=pl.Int64))
        ddi['variables'].append({
            'name': 'QIND', 'label': 'Industry allocation flag', 'implied_decimals': 0,
            'categories': [
                {'value': '0', 'label': 'Original entry or Inapplicable (not in universe)'},
                {'value': '1', 'label': 'Allocated'}]})
    if profile == 'five_year':
        frame = frame.with_columns(pl.Series('PWSTATE2', [72, 1, 1, 1, 1]),
                                   pl.Series('MIGPLAC1', [110, 1, 1, 1, 1]),
                                   pl.Series('MIGPUMA1', [2, 100, 100, 100, 100]))
    return ddi, frame


def genuine_geocorr_bytes():
    '''Load the exact captured public CSV; verify archive and original independently.'''
    import gzip
    import hashlib
    import json
    root = Path(__file__).parent / 'fixtures/acs_mapping/geography'
    metadata = json.loads((root / 'geocorr-intersections-20261018.provenance.json').read_text())
    archive = (root / 'geocorr-intersections-20261018.csv.gz').read_bytes()
    assert hashlib.sha256(archive).hexdigest() == metadata['archive_sha256']
    body = gzip.decompress(archive)
    assert hashlib.sha256(body).hexdigest() == metadata['original_sha256'] == (
        '9d7ef74ba87b2b3bd4b22303c4c0910a4da0bca966721232c0e9b4461737e04d')
    assert len(body) == metadata['original_size']
    return body


def national_mapping_originals(directory):
    '''Unpack complete pinned public geography originals into isolated fixture setup.'''
    import gzip
    import hashlib
    import json
    root = Path(__file__).parent / 'fixtures/acs_mapping/national'
    directory.mkdir()
    files = {}
    renames = {'2025_Gaz_counties_national.zip': 'counties_2025',
               'state-geocodes-v2025.xlsx': 'states_2025', 'list1_2023.xlsx': 'cbsa_2023'}
    for record in json.loads((root / 'provenance.json').read_text())['intake']:
        archive = (root / (record['name'] + '.gz')).read_bytes()
        assert hashlib.sha256(archive).hexdigest() == record['gzip_sha256']
        body = gzip.decompress(archive)
        assert hashlib.sha256(body).hexdigest() == record['original_sha256']
        assert len(body) == record['original_bytes']
        file = directory / record['name']
        file.write_bytes(body)
        files[renames.get(record['name'], file.stem)] = file
    geocorr = directory / 'geocorr_intersections.csv'
    geocorr.write_bytes(genuine_geocorr_bytes())
    files['geocorr_intersections'] = geocorr
    return files


def seed_national_reconciliation_inputs(tmp_path, monkeypatch, originals):
    '''Genuine unchanged upstream builders over national public geography and toy people.'''
    import json

    import fastexcel
    import polars as pl

    from embedding_data.acs_mapping_contract import SelectionRequest
    from embedding_data.acs_mapping_inputs import select_inputs

    forbid_external_access(monkeypatch)
    data_dir, directory = tmp_path / 'data', tmp_path / 'authenticated-national-setup'
    directory.mkdir()
    rows = fastexcel.read_excel(originals['puma_composition_2020'].read_bytes()).load_sheet(
        'PUMA_POWPUMA_MIGPUMA', header_row=None, dtypes='string').to_polars().rows()
    ct_group = next(r[3] for r in rows[1:] if r[:2] == ('09', '20201'))

    def prepare(profile, ddi, frame):
        ddi, frame = _reconciliation_delivery(profile, ddi, frame)
        expressions = [pl.when(pl.col('STATEFIP').eq(9)).then(pl.lit(20201))
                       .otherwise(pl.col('PUMA')).alias('PUMA')]
        for state, area in [('PWSTATE2', 'PWPUMA00'), ('MIGPLAC1', 'MIGPUMA1')]:
            expressions.append(pl.when(pl.col(state).eq(9)).then(pl.lit(int(ct_group)))
                               .otherwise(pl.col(area)).alias(area))
        return ddi, frame.with_columns(expressions)

    selection = _authenticated_deliveries(data_dir, directory, monkeypatch, prepare_acs=prepare)
    codes = _authenticated_codes(data_dir, directory)
    geography = _authenticated_geography(data_dir, directory, original_overrides={
        kind: originals[kind] for kind in ('states_2025', 'counties_2025', 'cbsa_2023')})
    ipums = ipums_verification_run.measure(data_dir, 'fixture_ipums', 'references', selection)
    pins = {name: manifest.sha256_file(path / 'outputs.json') for name, path in (
        ('codes', codes), ('geography', geography), ('ipums', ipums))}
    request = SelectionRequest(
        'fixture_codes', pins['codes'], 'fixture_geography', pins['geography'],
        'fixture_ipums', pins['ipums'], manifest.sha256_file(
            data_dir / 'raw/references/ipums-verification/references/receipt.json'))
    select_inputs(data_dir, request).verify()
    return FixtureInputs(data_dir, request,
                         json.loads((ipums / 'inputs.json').read_text())['deliveries'], pins)


def build_v2_fixture_mapping(fixture, run_id, monkeypatch, originals, ct_files):
    '''Explicit v2 actual import/select/build chain; no copied graph or validator bypass.'''
    import json

    from embedding_data import acs_mapping_bundle as bundle

    directory = fixture.data_dir.parent / ('v2-mapping-setup-' + run_id)
    directory.mkdir()
    public = Path(__file__).parent / 'fixtures/acs_mapping/classification'
    overrides = {f.stem: f for f in public.glob('*.xlsx')
                 if not f.stem.startswith('census_industry_')}
    release = directory / 'release-excerpts'
    release.mkdir()
    for kind, record in json.loads((public / 'release-layouts.json').read_text()).items():
        file = release / (kind + '.xlsx')
        write_public_layout(file, record)
        overrides[kind] = file
    overrides.update({k: v for k, v in originals.items() if k not in
                      ('states_2025', 'counties_2025', 'cbsa_2023')})
    overrides.update(ct_files)
    references = seed_mapping_references(
        directory, monkeypatch, original_overrides=overrides, data_dir=fixture.data_dir,
        reference_id=run_id + '_references', reference_version='acs-mapping-references-v2')
    forbid_external_access(monkeypatch)
    return bundle.build(fixture.data_dir, run_id, fixture.request, references.reference_id,
                        expected_reference_receipt_sha256=references.receipt_sha256)
