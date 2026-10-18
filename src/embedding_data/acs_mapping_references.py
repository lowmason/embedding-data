'''Immutable Stage 8 public reference registry and manifest-backed snapshots.'''

import csv
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urlencode, urljoin

import fastexcel
import httpx

from embedding_data import manifest, paths, target_io
from embedding_data.acs_mapping_contract import REFERENCE_VERSION
from embedding_data.acs_mapping_io import safe_path
from embedding_data.osha_benchmark_download import USER_AGENT

MAX_ORIGINAL_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True)
class Reference:
    kind: str
    filename: str
    authority_url: str
    edition: str
    parser_contract: str
    authority_role: str
    sha256: str | None = None


@dataclass(frozen=True)
class ReferenceSnapshot:
    reference_id: str
    directory: Path
    files: dict[str, Path]
    receipt: dict
    receipt_sha256: str


GEOCORR_STATES = (
    'Al01',
    'Ak02',
    'Az04',
    'Ar05',
    'Ca06',
    'Co08',
    'Ct09',
    'De10',
    'Dc11',
    'Fl12',
    'Ga13',
    'Hi15',
    'Id16',
    'Il17',
    'In18',
    'Ia19',
    'Ks20',
    'Ky21',
    'La22',
    'Me23',
    'Md24',
    'Ma25',
    'Mi26',
    'Mn27',
    'Ms28',
    'Mo29',
    'Mt30',
    'Ne31',
    'Nv32',
    'Nh33',
    'Nj34',
    'Nm35',
    'Ny36',
    'Nc37',
    'Nd38',
    'Oh39',
    'Ok40',
    'Or41',
    'Pa42',
    'Ri44',
    'Sc45',
    'Sd46',
    'Tn47',
    'Tx48',
    'Ut49',
    'Vt50',
    'Va51',
    'Wa53',
    'Wv54',
    'Wi55',
    'Wy56',
    'Pr72',
)
GEOCORR_QUERIES = {
    'geocorr_intersections': ('puma22', 'county'),
    'geocorr_puma_totals': ('puma22', 'state'),
    'geocorr_county_totals': ('county', 'state'),
}
GEOCORR_CONTROLS = [
    ('_PROGRAM', 'apps.geocorr2022.sas'),
    ('_SERVICE', 'MCDC_long'),
    ('_debug', '0'),
    ('g1_', 'puma22'),
    ('g2_', 'county'),
    ('wtvar', 'pop20'),
    ('nozerob', '1'),
    ('fileout', '1'),
    ('filefmt', 'csv'),
    ('lstfmt', 'html'),
    ('title', ''),
    ('afacts2', 'on'),
    ('counties', ''),
    ('metros', ''),
    ('places', ''),
    ('oropt', ''),
    ('latitude', ''),
    ('longitude', ''),
    ('distance', ''),
    ('kiloms', '0'),
    ('locname', ''),
]


def request_bytes(query: str) -> bytes:
    source, target = GEOCORR_QUERIES[query]
    controls = [
        (key, source if key == 'g1_' else target if key == 'g2_' else value)
        for key, value in GEOCORR_CONTROLS
    ]
    return urlencode([('state', state) for state in GEOCORR_STATES] + controls).encode('ascii')


REGISTRY = {
    'county_composition_2022': Reference(
        'county_composition_2022',
        'county_composition_2022.xls',
        'https://usa.ipums.org/usa/resources/volii/county_migpuma_pwpuma_2022.xls',
        '2022 county composition',
        'workbook-v1',
        'geographic_composition',
        'bd42f18ee36a10d91404be78106e60c613b6ec8ce53e9bc5860753af497ffadf',
    ),
    'puma_composition_2020': Reference(
        'puma_composition_2020',
        'puma_composition_2020.xls',
        'https://usa.ipums.org/usa/resources/volii/puma_migpuma1_pwpuma00_2020.xls',
        '2020 PUMA definitions',
        'workbook-v1',
        'geographic_composition',
        '022e4784cb08dcf01acfa4f680564cd26ba79e867f6643ee683577fde0b37a5d',
    ),
    'msa_puma_2023_2020': Reference(
        'msa_puma_2023_2020',
        'msa_puma_2023_2020.xlsx',
        'https://usa.ipums.org/usa/resources/volii/MSA2023_PUMA2020_crosswalk.xlsx',
        'July 2023 MSA; 2020 population',
        'workbook-v1',
        'geographic_composition',
        '80763eaf73cbda1b59818bdbf7650058eebbe18fa8a697599e645b3df235258f',
    ),
    'geocorr_form': Reference(
        'geocorr_form',
        'geocorr_form.html',
        'https://mcdc.missouri.edu/applications/geocorr2022.html',
        '2022 form version 1.8; inspected 2026-10-16',
        'geocorr-form-v1',
        'geocorr_request_form',
        '96ce8006b044529e8c23209e3d17de8921df2465dabaa3dd216c8367c0e94b40',
    ),
    'ipums_ind_pairs': Reference(
        'ipums_ind_pairs',
        'ipums_ind_pairs.xlsx',
        'https://usa.ipums.org/usa/resources/volii/ind_indnaics_crosswalk_2023.xlsx',
        '2023 crosswalk; 2018-2022 and 2023-2027 ACS/PRCS columns',
        'workbook-v1',
        'diagnostic_industry_pairs',
        '4d3f571905a9eddd905213878351c284ecf80ee48733e79cb9375181d70679a8',
    ),
    'ipums_ind_tokens': Reference(
        'ipums_ind_tokens',
        'ipums_ind_tokens.xlsx',
        'https://usa.ipums.org/usa/resources/volii/indnaics_crosswalk_2023.xlsx',
        '2023 crosswalk; 2018-2022 and 2023-2027 ACS/PRCS columns',
        'workbook-v1',
        'token_semantics',
        '96c767a70c1bf707d828fb186e4711a58b9dff73dc2bba99a7038127e75048c0',
    ),
    'pums_industry_2017': Reference(
        'pums_industry_2017',
        'pums_industry_2017.xlsx',
        'https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2018-ACS-PUMS-and-2018-SIPP-Public-Use-Industry-Code-List.xlsx',
        '2018 ACS PUMS / 2018 SIPP; 2017 industry classification',
        'workbook-v1',
        'classification_membership',
        '6f569f8bfcd1955db2f75ed4ec31dc836dea7faebf24375567107b725967f4d2',
    ),
    'pums_industry_2022': Reference(
        'pums_industry_2022',
        'pums_industry_2022.xlsx',
        'https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2023-ACS-PUMS-and-2024-SIPP-Public-Use-Industry-Code-List.xlsx',
        '2023 ACS PUMS / 2024 SIPP; 2022 industry classification',
        'workbook-v1',
        'classification_membership',
        'e6f9ec64ed2519c667a032d9766b460e50cf0ac085b7dd00ae97a98dc588816d',
    ),
    'ipums_occ_pairs': Reference(
        'ipums_occ_pairs',
        'ipums_occ_pairs.xlsx',
        'https://usa.ipums.org/usa/resources/volii/occ_occsoc_crosswalk_2000_onward.xlsx',
        '2000 onward crosswalk; current 2018 ACS/PRCS occupation columns',
        'workbook-v1',
        'occupation_pair_authority',
        'f95672c481af85302bc2f445888e2f5e493afffa6d88a5ca042b66a39cfc34f1',
    ),
    'census_occupation_2018': Reference(
        'census_occupation_2018',
        'census_occupation_2018.xlsx',
        'https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2018-occupation-code-list-and-crosswalk.xlsx',
        '2018 full Census occupation classification',
        'workbook-v1',
        'full_census_occupation_membership',
        'fca2818d691c32777a4cd733a9ab77c8c5bd47adcacd7ac3aa149bebd45b5f7f',
    ),
    'pums_occupation_2018': Reference(
        'pums_occupation_2018',
        'pums_occupation_2018.xlsx',
        'https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2018-ACS-PUMS-and-2018-SIPP-Public-Use-Occupation-Code-List.xlsx',
        '2018 ACS PUMS / 2018 SIPP; 2018 SOC',
        'workbook-v1',
        'classification_membership',
        '20cc7112cf96c7a3648b579cc0b2af239bea1c9094885a0d986959888695fe0a',
    ),
    'pums_annual_2024': Reference(
        'pums_annual_2024',
        'pums_annual_2024.xls',
        'https://www2.census.gov/programs-surveys/acs/tech_docs/pums/code_lists/ACSPUMS2024CodeLists.xls',
        '2024 annual product; 2022 industry and 2018 SOC; occupation heading names 2023',
        'workbook-v1',
        'delivered_scheme_and_source_recoding',
        'f8c945c383322f123b5d409fd1cd1352f23ace3c0ffff5de0bc1cf414886d40d',
    ),
    'pums_five_year_2024': Reference(
        'pums_five_year_2024',
        'pums_five_year_2024.xlsx',
        'https://www2.census.gov/programs-surveys/acs/tech_docs/pums/code_lists/ACSPUMS2020_2024CodeLists.xlsx',
        '2020-2024 five-year product; delivered 2022 industry and 2018 SOC',
        'workbook-v1',
        'delivered_scheme_and_source_recoding',
        '634fdd565249d72f09a8f75d82fe4193b20a09d898ef64a4b8e8039348d52994',
    ),
    'pums_annual_guide': Reference(
        'pums_annual_guide',
        'pums_annual_guide.pdf',
        'https://www2.census.gov/programs-surveys/acs/tech_docs/pums/2024ACS_PUMS_User_Guide.pdf',
        '2024 annual PUMS guide; section VIII.I and adjacent mapping sections',
        'pdf-documentary-v1',
        'documentary_evidence',
        '70d485604dfd89534eef7d491a219ab7d336f98e724732985a0a859eac5d9787',
    ),
    'pums_five_year_guide': Reference(
        'pums_five_year_guide',
        'pums_five_year_guide.pdf',
        'https://www2.census.gov/programs-surveys/acs/tech_docs/pums/2020_2024ACS_PUMS_User_Guide.pdf',
        '2020-2024 five-year PUMS guide; physical pages 18-19, VIII.I-L',
        'pdf-documentary-v1',
        'documentary_evidence',
        '77f9b74efef7cb9d3eb8ffa4dc875df9e15765432d6134ead3691a5fe8b35e1a',
    ),
    'usa_indnaics': Reference(
        'usa_indnaics',
        'usa_indnaics.html',
        'https://usa.ipums.org/usa-action/variables/INDNAICS',
        'public documentation inspected 2026-10-17',
        'variable-html-v1',
        'token_marker_semantics',
    ),
    'usa_occsoc': Reference(
        'usa_occsoc',
        'usa_occsoc.html',
        'https://usa.ipums.org/usa-action/variables/OCCSOC',
        'public documentation inspected 2026-10-17',
        'variable-html-v1',
        'token_marker_semantics',
    ),
    'usa_ind': Reference(
        'usa_ind',
        'usa_ind.html',
        'https://usa.ipums.org/usa-action/variables/IND',
        'public documentation inspected 2026-10-17',
        'variable-html-v1',
        'token_marker_semantics',
    ),
    'usa_occ': Reference(
        'usa_occ',
        'usa_occ.html',
        'https://usa.ipums.org/usa-action/variables/OCC',
        'public documentation inspected 2026-10-17',
        'variable-html-v1',
        'token_marker_semantics',
    ),
    'usa_pwpuma00': Reference(
        'usa_pwpuma00',
        'usa_pwpuma00.html',
        'https://usa.ipums.org/usa-action/variables/PWPUMA00',
        'public documentation inspected 2026-10-17',
        'variable-html-v1',
        'geographic_role_state_and_vintage',
    ),
    'usa_migpuma1': Reference(
        'usa_migpuma1',
        'usa_migpuma1.html',
        'https://usa.ipums.org/usa-action/variables/MIGPUMA1',
        'public documentation inspected 2026-10-17',
        'variable-html-v1',
        'geographic_role_state_and_vintage',
    ),
    'usa_pwstate2': Reference(
        'usa_pwstate2',
        'usa_pwstate2.html',
        'https://usa.ipums.org/usa-action/variables/PWSTATE2',
        'public documentation inspected 2026-10-17',
        'variable-html-v1',
        'geographic_role_state_and_vintage',
    ),
    'usa_migplac1': Reference(
        'usa_migplac1',
        'usa_migplac1.html',
        'https://usa.ipums.org/usa-action/variables/MIGPLAC1',
        'public documentation inspected 2026-10-17',
        'variable-html-v1',
        'geographic_role_state_and_vintage',
    ),
    'usa_puma': Reference(
        'usa_puma',
        'usa_puma.html',
        'https://usa.ipums.org/usa-action/variables/PUMA',
        'public documentation inspected 2026-10-17',
        'variable-html-v1',
        'geographic_role_state_and_vintage',
    ),
    'usa_multyear': Reference(
        'usa_multyear',
        'usa_multyear.html',
        'https://usa.ipums.org/usa-action/variables/MULTYEAR',
        'public documentation inspected 2026-10-17',
        'variable-html-v1',
        'geographic_role_state_and_vintage',
    ),
    'industry_tokens_html': Reference(
        'industry_tokens_html',
        'industry_tokens_html.html',
        'https://usa.ipums.org/usa/volii/indnaics.shtml',
        'public documentation inspected 2026-10-17',
        'crosswalk-html-v1',
        'token_marker_semantics',
    ),
    'industry_pairs_html': Reference(
        'industry_pairs_html',
        'industry_pairs_html.html',
        'https://usa.ipums.org/usa/volii/indtoindnaics.shtml',
        'public documentation inspected 2026-10-17',
        'crosswalk-html-v1',
        'diagnostic_industry_pairs',
    ),
    'soc_tokens_html': Reference(
        'soc_tokens_html',
        'soc_tokens_html.html',
        'https://usa.ipums.org/usa/volii/occsoc18.shtml',
        'public documentation inspected 2026-10-17',
        'crosswalk-html-v1',
        'token_marker_semantics',
    ),
    'occupation_pairs_html': Reference(
        'occupation_pairs_html',
        'occupation_pairs_html.html',
        'https://usa.ipums.org/usa/volii/occtooccsoc18.shtml',
        'public documentation inspected 2026-10-17',
        'crosswalk-html-v1',
        'token_marker_semantics',
    ),
    'geocorr_help': Reference(
        'geocorr_help',
        'geocorr_help.html',
        'https://mcdc.missouri.edu/applications/docs/geocorr2022-help.html',
        'public documentation inspected 2026-10-17',
        'geocorr-help-v1',
        'geocorr_population_factor_documentation',
    ),
}

for _query in GEOCORR_QUERIES:
    _url = 'https://mcdc.missouri.edu/cgi-bin/broker?' + request_bytes(_query).decode()
    for _suffix, _extension, _contract, _role in (
        ('', '.csv', 'geocorr-csv-v1', '2020_population_relation'),
        ('_request', '.request.txt', 'geocorr-request-v1', 'exact_get_query'),
        (
            '_response',
            '.response.html',
            'geocorr-response-v1',
            'application_completion_and_generated_link',
        ),
    ):
        _kind = _query + _suffix
        REGISTRY[_kind] = Reference(
            _kind,
            _kind + _extension,
            _url,
            '2020 Census population; 2020 PUMAs; current CT planning regions',
            _contract,
            _role,
        )

WORKBOOK_LAYOUTS = {
    'county_composition_2022': {
        'MIGPUMA-POWPUMA 2022 Lookup': (
            4,
            (
                'State of Residence (ST)',
                'County of Residence',
                'Place of Work State (PWSTATE2) or Migration State (MIGPLAC1)',
                'PWPUMA00 or MIGPUMA1',
            ),
        )
    },
    'puma_composition_2020': {
        'PUMA_POWPUMA_MIGPUMA': (
            4,
            (
                'State of Residence (ST)',
                'PUMA',
                'Place of Work State (PWSTATE2) or Migration State (MIGPLAC1)',
                'PWPUMA00 or MIGPUMA1',
            ),
        )
    },
    'msa_puma_2023_2020': {
        'MSA2023_PUMA2020_crosswalk': (
            11,
            (
                'MSA Code',
                'MSA Title',
                'State FIPS Code',
                'State Name',
                'PUMA Code',
                'PUMA Name',
                'MSA 2020 Population ',
                'PUMA 2020 Population ',
                ' Intersection 2020 Population ',
                'Percent MSA Population',
                'Percent PUMA Population',
            ),
        )
    },
    'ipums_ind_pairs': {
        'Sheet1': (
            16,
            (
                '2000 Census, 2000-2002 ACS/PRCS IND CODE',
                '2003-2007 ACS/PRCS IND CODE',
                '2008-2012 ACS/PRCS IND CODE',
                '2013-2017 ACS/PRCS IND CODE',
                '2018-2022 ACS/PRCS IND CODE',
                '2023-2027 ACS/PRCS IND CODE',
                '2000 Census 1% INDNAICS CODE',
                '2000 Census 5% INDNAICS CODE',
                '2000-2002 ACS INDNAICS CODE',
                '2003-2007 ACS/PRCS INDNAICS CODE ',
                '2008-2012 ACS/PRCS INDNAICS CODE',
                '2013-2017 ACS/PRCS INDNAICS CODE',
                '2018-2022 ACS/PRCS INDNAICS CODE',
                '2023-2027 ACS/PRCS INDNAICS CODE',
                'Industry Title',
            ),
        )
    },
    'ipums_ind_tokens': {
        'Sheet 1': (
            10,
            (
                '2000 Census 1% INDNAICS CODE',
                '2000 Census 5% INDNAICS CODE',
                '2000-2002 ACS INDNAICS CODE',
                '2003-2007 ACS/PRCS INDNAICS CODE ',
                '2008-2012 ACS/PRCS INDNAICS CODE',
                '2013-2017 ACS/PRCS INDNAICS CODE',
                '2018-2022 ACS/PRCS INDNAICS CODE',
                '2023-2027 ACS/PRCS INDNAICS CODE',
                'Industry Title',
            ),
        )
    },
    'pums_industry_2017': {
        'ACS': (
            5,
            (
                'Industry 2017 Description',
                '2017 Industry Code',
                '2017 NAICS Code',
                '2017 NAICS Based Code',
            ),
        )
    },
    'pums_industry_2022': {
        'ACS': (
            5,
            (
                'Industry 2022 Description',
                '2022 Industry Code',
                '2022 NAICS Code',
                '2022 NAICS Based Code',
            ),
        )
    },
    'ipums_occ_pairs': {
        'Codes without Descriptions': (
            16,
            (
                '2000 1% Census OCC code',
                '2000 5% Census OCC code',
                '2000-2004 ACS OCC code',
                '2005-2009 ACS/PRCS OCC code',
                '2010-2012 ACS/PRCS OCC code',
                '2013-2017 ACS/PRCS OCC code',
                '2018 ACS/PRCS OCC code',
                '2000 1% Census OCCSOC code',
                '2000 5% Census OCCSOC code',
                '2000-2004 ACS OCCSOC code',
                '2005-2009 ACS/PRCS OCCSOC code',
                '2010-2012 ACS/PRCS OCCSOC',
                '2013-2017 ACS/PRCS OCCSOC code',
                '2018 Onward ACS/PRCS',
                'Occupation title',
            ),
        ),
        'Codes with Descriptions': (
            30,
            (
                '2000 1% Census OCC code',
                'Description of Change',
                '2000 5% Census OCC code',
                'Description of Change',
                '2000-2004 ACS OCC code',
                'Description of Change',
                '2005-2009 ACS/PRCS OCC code',
                'Description of Change',
                '2010-2012 ACS/PRCS OCC code',
                'Description of Change',
                '2013-2017 ACS/PRCS OCC code',
                'Description of Change',
                '2018 ACS/PRCS OCC code',
                'Description of Change',
                '2000 1% Census OCCSOC code',
                'Description of Change',
                '2000 5% Census OCCSOC code',
                'Description of Change',
                '2000-2004 ACS OCCSOC code',
                'Description of Change',
                '2005-2009 ACS/PRCS OCCSOC code',
                'Description of Change',
                '2010-2012 ACS/PRCS OCCSOC',
                'Description of Change',
                '2013-2017 ACS/PRCS OCCSOC code',
                'Description of Change',
                '2018 ACS/PRCS',
                'Description of Change',
                'Occupation title',
            ),
        ),
    },
    'census_occupation_2018': {
        '2018 Census Occ Code List': (
            4,
            ('2018 Census Title ', '2018 Census Code', '2018 SOC Code'),
        ),
        '2010 to 2018 Crosswalk ': (
            6,
            (
                '2010 SOC code',
                '2010 Census Code',
                '2010 Census Title \n',
                '2018 SOC Code',
                '2018 Census Code',
                '2018 Census Title ',
            ),
        ),
    },
    'pums_occupation_2018': {
        'ACS': (
            3,
            (
                '2018 Census PUMS Occupation Code',
                '2018 SOC Code',
                'Description (2018 Census Occupation Code)',
            ),
        )
    },
    'pums_annual_2024': {
        'Industry': (
            5,
            (
                'Industry 2022 Description',
                '2022 Industry Code',
                '2022 NAICS Code',
                '2022 NAICS Based Code',
            ),
        ),
        'Occupation': (
            3,
            (
                '2018 Census PUMS Occupation Code',
                '2018 SOC Code',
                'Description (2018 Census Occupation Code)',
            ),
        ),
    },
    'pums_five_year_2024': {
        'IND README': (
            4,
            ('Industry Bridge Coding and PUMS File Creation Process: PUMS 2020-2024',),
        ),
        'Industry': (
            5,
            (
                'Industry 2022 Description',
                '2022 Industry Code',
                '2022 NAICS Code',
                '2022 NAICS Based Code',
            ),
        ),
        '2017 to 2022 IND Crosswalk': (
            14,
            (
                '2017 American Community Survey PUMS Industry Code List',
                '2022 American Community Survey PUMS Industry Code List',
            ),
        ),
        'IND Recodes & Conversion Rates': (
            20,
            ('2018-2022 INDP code', '2024 INDP code', '2018-2022 NAICSP', '2024 NAICSP'),
        ),
        'OCCP & SOCP': (
            3,
            (
                '2018 Census PUMS Occupation Code',
                '2018 SOC Code',
                'Description (2018 Census Occupation Code)',
            ),
        ),
    },
}

GEOCORR_PUMA_TOTALS_HEADERS = ['state', 'puma22', 'stab', 'PUMA22name', 'pop20', 'afact2', 'afact']
GEOCORR_COUNTY_TOTALS_HEADERS = [
    'county',
    'state',
    'stab',
    'CountyName',
    'pop20',
    'afact2',
    'afact',
]
GEOCORR_INTERSECTIONS_HEADERS = [
    'state',
    'puma22',
    'county',
    'stab',
    'CountyName',
    'PUMA22name',
    'pop20',
    'afact2',
    'afact',
]


def reference_directory(data_dir: Path, reference_id: str) -> Path:
    """Resolve a safe, explicitly selected snapshot under the caller's data root."""
    if not isinstance(reference_id, str) or not re.fullmatch(
        r'[A-Za-z0-9][A-Za-z0-9_-]*', reference_id
    ):
        raise ValueError('unsafe reference snapshot ID')
    directory = Path(data_dir) / 'raw/references/acs-mapping' / reference_id
    for file in (
        directory,
        directory.with_name(reference_id + '.part'),
        paths.manifest_path(data_dir),
    ):
        safe_path(file)
    if directory.with_name(reference_id + '.part').exists():
        raise ValueError('occupied snapshot partial; inspect and choose a fresh reference ID')
    return directory


def _json_record(entry):
    return json.loads(json.dumps(asdict(entry)))


def _expected_names():
    names = [reference.filename for reference in REGISTRY.values()]
    if len(names) != len(set(names)) or any(
        Path(name).name != name or name.endswith('.part') for name in names
    ):
        raise ValueError('unsafe or duplicate registered reference filenames')
    return set(names)


def _recorded_snapshot(data_dir, directory):
    manifest_file = paths.manifest_path(data_dir)
    prefix = directory.relative_to(manifest_file.parent).as_posix() + '/'
    entries = [e for e in manifest.read_manifest(manifest_file) if e.path.startswith(prefix)]
    by_name = {}
    for entry in entries:
        name = entry.path.removeprefix(prefix)
        if name in by_name:
            raise ValueError('duplicate snapshot manifest path')
        by_name[name] = entry
    return by_name


def preflight_destinations(data_dir: Path, reference_id: str) -> None:
    '''Check all registered destinations and absent-but-recorded paths before writes.'''
    directory = reference_directory(data_dir, reference_id)
    names = _expected_names()
    recorded = _recorded_snapshot(data_dir, directory)
    actual = set()
    if directory.exists():
        if not directory.is_dir():
            raise ValueError('occupied snapshot destination')
        for file in directory.rglob('*'):
            safe_path(file)
            if not file.is_file():
                raise ValueError('unexpected reference subdirectory')
            actual.add(file.relative_to(directory).as_posix())
    for name in names | {'receipt.json'}:
        safe_path(directory / name)
        partial = directory / (name + '.part')
        safe_path(partial)
        if partial.exists():
            raise ValueError('occupied per-file reference partial')
    if not actual.issubset(names) or not set(recorded).issubset(names):
        raise ValueError('conflicting or complete snapshot; originals are immutable')
    if actual != set(recorded):
        raise ValueError(
            'missing recorded file or unrecorded evidence; inspect and choose a fresh reference ID'
        )
    by_filename = {r.filename: k for k, r in REGISTRY.items()}
    for name in sorted(actual):
        entry = manifest.entry_for(paths.manifest_path(data_dir), directory / name)
        kind = by_filename[name]
        if entry.source_url != REGISTRY[kind].authority_url:
            raise ValueError('registered source citation differs')
        _validate_original(kind, directory / name)


class _PublicLinks(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.extend(value for key, value in attrs if key == 'href' and value is not None)


def generated_csv_url(html: str) -> str:
    '''Accept only successful application output and its documented padded CSV link.'''
    if (
        'Processing completed' not in html
        or 'geocorr2022 version ' not in html
        or re.search(r'(?:ERROR:|SAS Error|application error|Access Denied)', html, re.I)
    ):
        raise ValueError('Geocorr application did not complete successfully')
    links = []
    for link in _PublicLinks(html).links:
        padded = link.rstrip(' \t\r\n\f\v')
        if '..' in padded.split('/') or padded != padded.lstrip():
            raise ValueError('generated Geocorr CSV URL is not allowlisted')
        if '.csv' not in padded.lower():
            continue
        url = urljoin('https://mcdc.missouri.edu/cgi-bin/broker', padded)
        if not re.fullmatch(r'https://mcdc\.missouri\.edu/temp/geocorr2022_[0-9]+\.csv', url):
            raise ValueError('generated Geocorr CSV URL is not allowlisted')
        links.append(url)
    if len(links) != 1:
        raise ValueError('Geocorr response requires one generated original CSV')
    return links[0]


def _validate_workbook(kind, file):
    try:
        workbook = fastexcel.read_excel(file.read_bytes())
        for sheet, (width, header) in WORKBOOK_LAYOUTS[kind].items():
            if sheet not in workbook.sheet_names:
                raise ValueError('registered worksheet identity absent')
            frame = workbook.load_sheet(sheet, header_row=None, dtypes='string').to_polars()
            rows = list(frame.iter_rows())
            if frame.width != width or len(rows) < 2:
                raise ValueError('registered workbook column count or body differs')
            matches = [
                i
                for i, row in enumerate(rows)
                if tuple(value for value in row if value is not None) == header
            ]
            if len(matches) != 1 or matches[0] == len(rows) - 1:
                raise ValueError('registered workbook unique exact header/body differs')
    except Exception as error:
        raise ValueError(f'{kind}: malformed workbook or registered layout differs') from error


def _validate_csv(kind, file):
    headers = {
        'geocorr_intersections': GEOCORR_INTERSECTIONS_HEADERS,
        'geocorr_puma_totals': GEOCORR_PUMA_TOTALS_HEADERS,
        'geocorr_county_totals': GEOCORR_COUNTY_TOTALS_HEADERS,
    }[kind]
    try:
        with file.open(encoding='utf-8-sig', newline='') as source:
            rows = list(csv.reader(source, strict=True))
        if len(rows) < 3 or rows[0] != headers or len(rows[1]) != len(headers):
            raise ValueError('Geocorr header/label/body differs')
        labels = dict(zip(headers, rows[1], strict=True))
        if (
            labels['pop20'] != 'Total population (2020 Census)'
            or 'allocation factor' not in labels['afact']
            or 'allocation factor' not in labels['afact2']
        ):
            raise ValueError('Geocorr population/factor label identity differs')
        seen = set()
        for row in rows[2:]:
            if len(row) != len(headers):
                raise ValueError('Geocorr original row width differs')
            record = dict(zip(headers, row, strict=True))
            keys = tuple(record[k] for k in headers if k in ('state', 'puma22', 'county'))
            if keys in seen:
                raise ValueError('duplicate Geocorr original relation')
            seen.add(keys)
            for key in ('state', 'puma22', 'county'):
                if key in record and not re.fullmatch(
                    r'\d{' + ('2' if key == 'state' else '5') + '}', record[key]
                ):
                    raise ValueError('Geocorr original code format differs')
            if not re.fullmatch(r'[0-9]+', record['pop20'].strip()):
                raise ValueError('Geocorr original population must be an integer')
            from decimal import Decimal, InvalidOperation

            try:
                factors = [Decimal(record[k].strip()) for k in ('afact', 'afact2')]
            except InvalidOperation as error:
                raise ValueError('invalid Geocorr published factor') from error
            if any(not value.is_finite() or not 0 <= value <= 1 for value in factors):
                raise ValueError('Geocorr published factor outside unit interval')
    except (csv.Error, UnicodeError) as error:
        raise ValueError('invalid Geocorr CSV original') from error


def _validate_html(kind, text):
    if re.search(r'(?:ERROR:|SAS Error|application error|Access Denied)', text, re.I):
        raise ValueError('HTTP-200 public application error')
    if kind.startswith('usa_'):
        variable = kind.removeprefix('usa_').upper()
        required = (
            f'IPUMS USA: descr: {variable}',
            f'<h1>{variable}</h1>',
            'description_section',
            'codes_section',
            'comparability_section',
        )
    elif kind == 'geocorr_form':
        required = (
            'action="/cgi-bin/broker"',
            'method="GET"',
            'name="state"',
            'puma22',
            'county',
            'pop20',
            'CTcounty',
        )
        # HTML attribute names and method values are case-insensitive.
        if not all(value.lower() in text.lower() for value in required):
            raise ValueError('registered Geocorr form layout differs')
        states = set(re.findall(r'<option\s+value="([A-Za-z]{2}[0-9]{2})"', text, re.I))
        if states != set(GEOCORR_STATES):
            raise ValueError('registered Geocorr state inventory differs')
        return
    elif kind == 'geocorr_help':
        required = ('Geocorr 2022 Help', 'afact2', '2020 decennial population')
    else:
        required = (
            'class="condensed"',
            'INDNAICS' if kind.startswith('industry') else 'OCCSOC',
            'Industry Title' if kind.startswith('industry') else 'Occupation Title',
        )
        tables = re.findall(r'<table[^>]*class="condensed"[^>]*>(.*?)</table>', text, re.S | re.I)
        if len(tables) != 1:
            raise ValueError('registered public crosswalk table differs')
        rows = re.findall(r'<tr\b[^>]*>(.*?)</tr>', tables[0], re.S | re.I)
        if (
            len(rows) < 3
            or not all('<th' in row.lower() for row in rows[:2])
            or '<td' not in rows[2].lower()
        ):
            raise ValueError('registered public crosswalk two-header/body layout differs')
    if not all(value in text for value in required):
        raise ValueError(f'{kind}: registered public HTML identity/layout differs')


def _validate_original(kind, file):
    reference = REGISTRY[kind]
    safe_path(file)
    if not file.is_file() or not 0 < file.stat().st_size <= MAX_ORIGINAL_BYTES:
        raise ValueError('missing/empty/oversized public original')
    if reference.sha256 is not None and manifest.sha256_file(file) != reference.sha256:
        raise ValueError(f'{kind}: original differs from approved inspected edition')
    if kind in WORKBOOK_LAYOUTS:
        _validate_workbook(kind, file)
    elif kind in GEOCORR_QUERIES:
        _validate_csv(kind, file)
    elif kind.endswith('_request'):
        if file.read_bytes() != request_bytes(kind.removesuffix('_request')):
            raise ValueError('Geocorr exact registered request bytes differ')
    elif kind.endswith('_response'):
        text = file.read_text(encoding='utf-8')
        generated_csv_url(text)
        source, target = GEOCORR_QUERIES[kind.removesuffix('_response')]
        source_match = re.search(r'Source geographies requested:\s*<b>([^<]+)</b>', text)
        target_match = re.search(r'Target geographies requested:\s*<b>([^<]+)</b>', text)
        expected_source = ['state', 'puma22'] if source == 'puma22' else [source]
        if (source_match is None or target_match is None
                or source_match[1].split() != expected_source
                or target_match[1].split() != [target]):
            raise ValueError('Geocorr response query identity differs')
    elif reference.parser_contract == 'pdf-documentary-v1':
        if not file.read_bytes().startswith(b'%PDF-'):
            raise ValueError('registered documentary original is not a PDF')
    else:
        _validate_html(kind, file.read_text(encoding='utf-8'))


def _publish_original(data_dir, directory, kind, partial, *, imported):
    reference = REGISTRY[kind]
    _validate_original(kind, partial)
    file = directory / reference.filename
    safe_path(file)
    entry = manifest.describe_file(
        partial,
        directory,
        retrieved_at=datetime.now(UTC),
        client='manual-import' if imported else 'httpx',
        client_version=version('embedding-data') if imported else version('httpx'),
        source_url=reference.authority_url,
        proxies=('retrieved_at',) if imported else (),
    )
    from dataclasses import replace

    entry = replace(entry, path=file.relative_to(paths.manifest_path(data_dir).parent).as_posix())
    manifest.check_appendable(paths.manifest_path(data_dir), [entry])
    os.link(partial, file)
    try:
        manifest.append_entries(paths.manifest_path(data_dir), [entry])
    except Exception as error:
        raise ValueError(
            f'{file}: unrecorded evidence after manifest append failure; '
            'inspect and choose a fresh reference ID'
        ) from error
    return _json_record(entry)


def _import_bytes(data_dir, directory, kind, original, *, imported):
    partial = directory / (REGISTRY[kind].filename + '.part')
    safe_path(partial)
    with partial.open('xb') as output:
        try:
            with original.open('rb') as source:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
            output.flush()
            return _publish_original(data_dir, directory, kind, partial, imported=imported)
        finally:
            partial.unlink(missing_ok=True)


def _original_record(reference, entry):
    proxy = entry.client == 'manual-import'
    if entry.client not in ('manual-import', 'httpx') or entry.proxies != (
        ('retrieved_at',) if proxy else ()
    ):
        raise ValueError('reference retrieval/import provenance differs')
    timestamp = datetime.fromisoformat(entry.retrieved_at)
    if timestamp.tzinfo is None:
        raise ValueError('reference retrieval/import time must be timezone-aware')
    return {
        'authority_url': reference.authority_url,
        'edition': reference.edition,
        'authority_role': reference.authority_role,
        'parser_contract': reference.parser_contract,
        'sha256': entry.sha256,
        'size': entry.size,
        'retrieved_at': entry.retrieved_at,
        'retrieved_at_is_proxy': proxy,
        'citation': _json_record(entry),
    }


def _receipt_contents(data_dir, reference_id, directory):
    originals, citations, files, requests = {}, [], {}, {}
    for kind, reference in sorted(REGISTRY.items()):
        file = directory / reference.filename
        _validate_original(kind, file)
        entry = manifest.entry_for(paths.manifest_path(data_dir), file)
        if entry.source_url != reference.authority_url:
            raise ValueError('public reference manifest authority differs')
        originals[kind] = _original_record(reference, entry)
        citations.append(_json_record(entry))
        files[reference.filename] = target_io.file_record(file)
        if kind.endswith('_request'):
            requests[kind] = {
                'filename': reference.filename,
                'method': 'GET',
                **files[reference.filename],
            }
        if kind in GEOCORR_QUERIES:
            originals[kind]['retrieval_url'] = generated_csv_url(
                (directory / REGISTRY[kind + '_response'].filename).read_text(encoding='utf-8')
            )
    return {
        'reference_id': reference_id,
        'reference_version': REFERENCE_VERSION,
        'originals': originals,
        'request_files': requests,
        'raw_citations': citations,
        'files': files,
    }


def _finish_snapshot(data_dir, reference_id, directory):
    receipt = _receipt_contents(data_dir, reference_id, directory)
    file = directory / 'receipt.json'
    partial = directory / 'receipt.json.part'
    body = (json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    safe_path(partial)
    with partial.open('xb') as output:
        try:
            output.write(body)
            output.flush()
            entry = manifest.describe_file(
                partial,
                paths.manifest_path(data_dir).parent,
                retrieved_at=datetime.now(UTC),
                client='embedding-data',
                client_version=version('embedding-data'),
            )
            from dataclasses import replace

            entry = replace(
                entry, path=file.relative_to(paths.manifest_path(data_dir).parent).as_posix()
            )
            manifest.check_appendable(paths.manifest_path(data_dir), [entry])
            safe_path(file)
            os.link(partial, file)
            try:
                manifest.append_entries(paths.manifest_path(data_dir), [entry])
            except Exception as error:
                raise ValueError(
                    'unrecorded evidence: generated receipt manifest append failed'
                ) from error
        finally:
            partial.unlink(missing_ok=True)
    return check_cached_snapshot(data_dir, reference_id)


def check_cached_snapshot(data_dir: Path, reference_id: str) -> ReferenceSnapshot:
    '''Verify a complete immutable snapshot against independently recorded manifest entries.'''
    directory = reference_directory(data_dir, reference_id)
    expected = _expected_names() | {'receipt.json'}
    if not directory.is_dir():
        raise ValueError('reference snapshot is absent or incomplete')
    actual = set()
    for file in directory.rglob('*'):
        safe_path(file)
        if not file.is_file():
            raise ValueError('unexpected reference subdirectory')
        actual.add(file.relative_to(directory).as_posix())
    if actual != expected or set(_recorded_snapshot(data_dir, directory)) != expected:
        raise ValueError('reference snapshot inventory incomplete or unexpected')
    file = directory / 'receipt.json'
    entry = manifest.entry_for(paths.manifest_path(data_dir), file)
    if entry.client != 'embedding-data' or entry.source_url is not None or entry.proxies:
        raise ValueError('generated receipt manifest identity differs')
    try:
        receipt = json.loads(file.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ValueError('invalid generated reference receipt') from error
    expected_receipt = _receipt_contents(data_dir, reference_id, directory)
    if receipt != expected_receipt:
        raise ValueError('reference receipt inventory/citations/identity differs')
    return ReferenceSnapshot(
        reference_id,
        directory,
        {kind: directory / reference.filename for kind, reference in REGISTRY.items()},
        receipt,
        entry.sha256,
    )


def check_references(
    data_dir: Path, reference_id: str, *, expected_receipt_sha256: str
) -> ReferenceSnapshot:
    """Offline build boundary: require the caller's detached receipt pin."""
    if not isinstance(expected_receipt_sha256, str) or not re.fullmatch(
        '[a-f0-9]{64}', expected_receipt_sha256
    ):
        raise ValueError('an independent reference receipt SHA-256 pin is required')
    snapshot = check_cached_snapshot(data_dir, reference_id)
    if snapshot.receipt_sha256 != expected_receipt_sha256:
        raise ValueError('reference receipt differs from independent external pin')
    return snapshot


def import_reference(data_dir: Path, reference_id: str, kind: str, original: Path) -> dict:
    '''Import exact public bytes; only an explicitly incomplete import set may grow.'''
    if kind not in REGISTRY:
        raise ValueError('unknown registered reference kind')
    original = Path(original)
    if any(part.endswith('.part') for part in original.parts):
        raise ValueError('partial import source is not an original')
    safe_path(original)
    preflight_destinations(data_dir, reference_id)
    directory = reference_directory(data_dir, reference_id)
    recorded = _recorded_snapshot(data_dir, directory)
    if any(entry.client != 'manual-import' for entry in recorded.values()):
        raise ValueError('failed acquisition is immutable; use a fresh reference ID for import')
    if REGISTRY[kind].filename in recorded:
        raise ValueError('registered original already imported; conflicting import refused')
    _validate_original(kind, original)
    directory.mkdir(parents=True, exist_ok=True)
    safe_path(directory)
    citation = _import_bytes(data_dir, directory, kind, original, imported=True)
    complete = len(recorded) + 1 == len(REGISTRY)
    if complete:
        snapshot = _finish_snapshot(data_dir, reference_id, directory)
        return {'complete': True, 'citation': citation, 'receipt_sha256': snapshot.receipt_sha256}
    return {'complete': False, 'citation': citation, 'receipt_sha256': None}


def make_client() -> httpx.Client:
    return httpx.Client(
        timeout=120,
        follow_redirects=False,
        trust_env=False,
        headers={'User-Agent': USER_AGENT, 'Accept-Encoding': 'identity'},
    )


def _content_type(reference, value):
    allowed = {
        'workbook-v1': {
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/octet-stream',
        },
        'pdf-documentary-v1': {'application/pdf', 'application/octet-stream'},
        'geocorr-csv-v1': {'text/csv', 'text/plain', 'application/octet-stream'},
    }.get(reference.parser_contract, {'text/html', 'application/xhtml+xml'})
    if value.split(';', 1)[0].strip().lower() not in allowed:
        raise ValueError('public original transport content type differs')


def _download_original(data_dir, directory, kind, url, client):
    reference = REGISTRY[kind]
    partial = directory / (reference.filename + '.part')
    safe_path(partial)
    # Exclusive open establishes cleanup ownership before contacting transport.
    with partial.open('xb') as output:
        try:
            with client.stream('GET', url) as response:
                response.raise_for_status()
                _content_type(reference, response.headers.get('content-type', ''))
                length = response.headers.get('content-length')
                if length is not None and (
                    not length.isdigit() or int(length) > MAX_ORIGINAL_BYTES
                ):
                    raise ValueError('invalid/oversized public transport content length')
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_ORIGINAL_BYTES:
                        raise ValueError('public original exceeds byte bound')
                    output.write(chunk)
                output.flush()
                if (
                    length is not None
                    and not response.headers.get('content-encoding')
                    and size != int(length)
                ):
                    raise ValueError('public original transport completion differs')
            _publish_original(data_dir, directory, kind, partial, imported=False)
        finally:
            partial.unlink(missing_ok=True)


def acquire_missing(data_dir: Path, reference_id: str, client: httpx.Client) -> ReferenceSnapshot:
    preflight_destinations(data_dir, reference_id)
    directory = reference_directory(data_dir, reference_id)
    directory.mkdir(parents=True, exist_ok=False)
    # A failed acquisition keeps already manifested originals and can never resume silently.
    for kind, reference in REGISTRY.items():
        if kind in GEOCORR_QUERIES or kind.endswith(('_request', '_response')):
            continue
        _download_original(data_dir, directory, kind, reference.authority_url, client)
    for query in GEOCORR_QUERIES:
        request_kind, response_kind = query + '_request', query + '_response'
        partial = directory / (REGISTRY[request_kind].filename + '.part')
        with partial.open('xb') as output:
            try:
                output.write(request_bytes(query))
                output.flush()
                _publish_original(data_dir, directory, request_kind, partial, imported=False)
            finally:
                partial.unlink(missing_ok=True)
        _download_original(
            data_dir, directory, response_kind, REGISTRY[response_kind].authority_url, client
        )
        url = generated_csv_url(
            (directory / REGISTRY[response_kind].filename).read_text(encoding='utf-8')
        )
        _download_original(data_dir, directory, query, url, client)
    return _finish_snapshot(data_dir, reference_id, directory)


def acquire_references(
    data_dir: Path, reference_id: str, *, client: httpx.Client | None = None
) -> ReferenceSnapshot:
    '''Verify cached bytes before any client construction; otherwise acquire a fresh set.'''
    directory = reference_directory(data_dir, reference_id)
    if directory.exists():
        return check_cached_snapshot(data_dir, reference_id)
    preflight_destinations(data_dir, reference_id)
    if client is not None:
        return acquire_missing(data_dir, reference_id, client)
    with make_client() as owned_client:
        return acquire_missing(data_dir, reference_id, owned_client)
