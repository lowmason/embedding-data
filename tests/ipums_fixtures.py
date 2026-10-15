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
