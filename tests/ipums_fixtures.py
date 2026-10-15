'''Synthetic delivery metadata and tiny microdata for offline IPUMS tests.'''

import gzip
import json

DDI_NAMESPACE = 'ddi:codebook:2_5'


def definition():
    return {
        'collection': 'usa', 'version': None, 'dataFormat': 'csv',
        'samples': {'us2023a': {}, 'us2024a': {}},
        'variables': {
            'EMPSTAT': {'dataQualityFlags': False, 'caseSelections': {'general': ['1']}},
            'PERWT': {'dataQualityFlags': True, 'caseSelections': {}},
            'REPWTP': {'dataQualityFlags': False, 'caseSelections': {}},
        },
        'dataQualityFlags': True,
    }


def write_definition(directory, contents=None):
    file = directory / 'extract.json'
    file.write_text(json.dumps(definition() if contents is None else contents))
    return file


def ddi_xml():
    return f"""<codeBook xmlns="{DDI_NAMESPACE}" version="2.5">
      <stdyDscr>
        <citation><titlStmt><titl>Synthetic IPUMS data</titl></titlStmt>
          <verStmt><version date="2026-10-12">fixture dataset v17.0</version></verStmt>
        </citation>
        <stdyInfo><notes>us2023a: delivered synthetic sample</notes>
          <notes>us2024a: delivered synthetic sample</notes>
          <sumDscr><timePrd event="start" date="2023">2023-2024</timePrd>
          <collDate event="single" date="2026-10-12"/></sumDscr>
        </stdyInfo>
        <dataAccs><useStmt><citReq>Synthetic citation <emph>version 17.0</emph>.</citReq>
        </useStmt></dataAccs>
      </stdyDscr>
      <dataDscr>
        <var name="SAMPLE" dcml="0"><labl>Sample</labl>
          <catgry><catValu>001</catValu><labl>us2023a</labl></catgry>
          <catgry><catValu>002</catValu><labl>us2024a</labl></catgry>
          <catgry><catValu>003</catValu><labl>us1900a not delivered</labl></catgry>
        </var>
        <var name="PERWT" dcml="2"><labl>Person weight</labl>
          <txt>Divide stored values by 100.</txt><notes>Preserve decimals.</notes>
          <varFormat type="numeric"/>
        </var>
        <var name="REPWTP1" dcml="4"><labl>Replicate weight 1</labl></var>
        <var name="REPWTP2" dcml="4"><labl>Replicate weight 2</labl></var>
        <var name="INDNAICS" dcml="0"><labl>Industry</labl>
          <catgry><catValu>31M</catValu><labl>Manufacturing</labl></catgry>
        </var>
      </dataDscr>
    </codeBook>"""


def write_ddi(directory, contents=None):
    file = directory / 'delivery.xml'
    file.write_text(ddi_xml() if contents is None else contents)
    return file


def write_csv(directory, text):
    file = directory / 'delivery.csv.gz'
    with gzip.open(file, 'wt') as stream:
        stream.write(text)
    return file


# Public layouts inspected 2026-10-15; see the Task 3 preflight ledger.
SAMPLE_CATALOG = """<html><title>IPUMS USA</title><h1>Sample IDs</h1>
<table class="supplementalTable"><tr><th>Sample ID</th><th>Description</th></tr>
<tr><td><span>us2023a</span></td><td>2023 ACS</td></tr>
<tr><td><span>us2024c</span></td><td>2020-2024, ACS 5-year</td></tr></table></html>"""


def industry_workbook(file, vintage=2017, *, header=None, sheet=None, leaves=None):
    from zipfile import ZipFile

    from code_fixtures import write_xlsx

    sheet = sheet or ('2017 Census Industry Code List' if vintage == 2017
                      else '2022 Census Ind Code List ')
    code_header = '2017 Census Code' if vintage == 2017 else '2022 Census Industry Code'
    preamble = ([[None, '2017 Industry Code List'], [None, 'U.S. Census Bureau'], [None]]
                if vintage == 2017 else
                [['2022 Census Industry Code List'], ['U.S. Census Bureau'], ['2024-09-09']])
    rows = [
        *preamble,
        [None, f'Industry {vintage} Description', None, header or code_header,
         f'{vintage} NAICS Code'],
        [None],
        [None, 'Agriculture', None, '0170-0290', '11'],
        *(leaves if leaves is not None else [
            [None, 'Crop production  ', None, '0170', '111'],
            [None, 'Animal production and aquaculture', None, '0180', '112'],
            [None, 'Unemployed, last worked 5 years ago or earlier or never worked',
             None, '9920', None],
        ]),
    ]
    write_xlsx(file, rows)
    with ZipFile(file) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    parts['xl/workbook.xml'] = parts['xl/workbook.xml'].replace(
        b'name="Fixture"', f'name="{sheet}"'.encode())
    with ZipFile(file, 'w') as archive:
        for name, body in parts.items():
            archive.writestr(name, body)
    return file


def bls_response():
    data = [
        {'year': str(year), 'period': f'M{month:02}', 'periodName': 'fixture month',
         'value': '100.5', 'footnotes': [{}]}
        for year, last in [(2025, 12), (2026, 9)] for month in range(1, last + 1)
    ]
    data[9].update(value='-', footnotes=[{
        'code': '9', 'text': 'Data unavailable due to the 2025 lapse in appropriations.'}])
    data[12]['footnotes'] = [{'code': '12', 'text': 'Population control revision.'}]
    return {'status': 'REQUEST_SUCCEEDED', 'responseTime': 1, 'message': [],
            'Results': {'series': [{'seriesID': 'LNU02000000', 'data': data}]}}


def bls_documents(directory):
    (directory / 'bls_series_metadata.txt').write_text(
        'series_id        \tperiodicity_code\tseries_title\tseasonal\n'
        'LNU02000000      \tM\t(Unadj) Employment Level\tU\n')
    (directory / 'bls_a1_metadata.html').write_text(
        '<html><h1>Table A-1. Employment status of the civilian population by sex and age</h1>'
        '<table><caption>[Numbers in thousands]</caption>'
        '<tr><th>Not seasonally adjusted</th></tr>'
        '<tr><th>Civilian noninstitutional population</th></tr>'
        '<tr><th>Men, 16 years and over</th></tr><tr><th>Employed</th></tr></table></html>')


# Codes and shape inspected in both canonical 2023/2024 public ACS responses.
ACS_STATE_CODES = tuple('01 02 04 05 06 08 09 10 11 12 13 15 16 17 18 19 20 21 22 '
                        '23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 '
                        '42 44 45 46 47 48 49 50 51 53 54 55 56'.split())


def acs_levels(*, include_pr=True):
    rows = [['NAME', 'B23025_004E', 'state']]
    rows.extend([[f'Fixture state {code}', str(100 + index), code]
                 for index, code in enumerate(ACS_STATE_CODES)])
    if include_pr:
        rows.append(['Puerto Rico', '777', '72'])
    return rows


def reference_originals(directory, registry):
    '''Tiny inspected-layout inputs; pinned originals use fixture-only hashes in tests.'''
    from pathlib import Path

    directory.mkdir()
    bls_documents(directory)
    originals = {}
    for kind, reference in registry.items():
        file = directory / reference.filename
        if kind == 'usa_samples':
            file.write_text(SAMPLE_CATALOG)
        elif kind.startswith('census_industry_'):
            industry_workbook(file, int(kind.rsplit('_', 1)[1]))
        elif kind in ('acs_2023_employment', 'acs_2024_employment'):
            rows = acs_levels()
            if kind == 'acs_2024_employment':
                for row in rows[1:]:
                    row[1] = str(int(row[1]) + 100)
            file.write_text(json.dumps(rows))
        elif kind == 'cps_employment':
            recorded = Path(__file__).parent / 'fixtures/ipums/bls-employment-v1.json'
            file.write_bytes(recorded.read_bytes())
        elif kind in ('bls_series_metadata', 'bls_a1_metadata'):
            assert file.is_file()
        elif kind.startswith('asec_'):
            file.write_bytes(b'%PDF-1.4\n% Synthetic documentary-byte fixture\n%%EOF\n')
        elif kind.startswith('acs_'):
            year = kind.split('_')[1]
            file.write_text(f'<html><title>Census Data API: /data/{year}/acs/acs1/groups/B23025'
                            '</title><table><tr><td>B23025_004E</td></tr></table></html>')
        else:
            collection, variable = kind.split('_', 1)
            file.write_text(f'<html><title>IPUMS {collection.upper()}: descr: {variable.upper()}'
                            f'</title><h1>{variable.upper()}</h1><h2>Description</h2>'
                            '<p>Synthetic public variable metadata.</p></html>')
        originals[kind] = file
    return originals
