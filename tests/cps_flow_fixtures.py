'''Synthetic Stage 11 reference originals and the offline guards for CPS job-flow tests.'''

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile

import polars as pl
import pytest

from embedding_data import cps_flow_references

INDUSTRY_HEADER = 'ROW_TYPE,Industry 2025 Description,2022 Industry Code,2022 NAICS Code'
OCCUPATION_HEADER = (
    'ROW_TYPE,2020 Census Public Use Occupation Code,2018 SOC Code,'
    'Description (2020 Census Occupation Code)')
BLS_LABEL = 'Armed Forces (last job)'


@pytest.fixture(autouse=True)
def no_live_clients(monkeypatch):
    '''A reference test that forgets to patch the client fails instead of reaching a network.'''

    def deny(*args, **kwargs):
        raise AssertionError('a reference test reached an HTTP client without a patch')

    monkeypatch.setattr(cps_flow_references, 'make_client', deny)


def offline_guards(monkeypatch) -> dict[str, int]:
    '''Count, then deny, every network, environment-file and live-client attempt.

    It counts at the real seams (sockets, httpx, dotenv, IpumsApiClient, the module
    `make_client` functions and opens of the production `.env` and `data/`). It also denies
    `httpx.Client`, so never install it in an `acquire-references` test.
    '''
    from acs_target_fixtures import install_counted_guards

    counts = {'network': 0, 'environment_file': 0, 'live_client': 0}
    install_counted_guards(monkeypatch, counts)

    def deny(*args, **kwargs):
        counts['live_client'] += 1
        raise AssertionError('offline CPS job flows attempted a live client')

    monkeypatch.setattr(cps_flow_references, 'make_client', deny)
    return counts


def write_workbook(file: Path, sheets: dict[str, list[list[str | None]]]) -> Path:
    '''Write a minimal workbook with one worksheet for each entry, in order.'''
    namespace = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    relations = 'http://schemas.openxmlformats.org/package/2006/relationships'
    kind = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    count = len(sheets)
    with ZipFile(file, 'w') as archive:
        overrides = ''.join(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/'
            'vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for i in range(1, count + 1))
        archive.writestr(
            '[Content_Types].xml',
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
            'relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-'
            f'officedocument.spreadsheetml.sheet.main+xml"/>{overrides}</Types>')
        archive.writestr(
            '_rels/.rels',
            f'<Relationships xmlns="{relations}"><Relationship Id="rId1" '
            f'Type="{kind}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        listed = ''.join(
            f'<sheet name="{escape(name, {chr(34): "&quot;"})}" sheetId="{i}" r:id="rId{i}"/>'
            for i, name in enumerate(sheets, 1))
        archive.writestr(
            'xl/workbook.xml',
            f'<workbook xmlns="{namespace}" xmlns:r="{kind}"><sheets>{listed}</sheets></workbook>')
        archive.writestr(
            'xl/_rels/workbook.xml.rels',
            f'<Relationships xmlns="{relations}">' + ''.join(
                f'<Relationship Id="rId{i}" Type="{kind}/worksheet" '
                f'Target="worksheets/sheet{i}.xml"/>' for i in range(1, count + 1))
            + '</Relationships>')
        for i, rows in enumerate(sheets.values(), 1):
            body = ''.join(
                f'<row r="{r}">' + ''.join(
                    f'<c r="{chr(65 + c)}{r}" t="inlineStr"><is>'
                    f'<t xml:space="preserve">{escape(value)}</t></is></c>'
                    for c, value in enumerate(row) if value is not None) + '</row>'
                for r, row in enumerate(rows, 1))
            archive.writestr(f'xl/worksheets/sheet{i}.xml',
                             f'<worksheet xmlns="{namespace}"><sheetData>{body}</sheetData>'
                             '</worksheet>')
    return file


def bls_workbook(file: Path, code: str, partner: str, *, label: str = BLS_LABEL,
                 code_cell: str | None = None) -> Path:
    '''A two-sheet list: notes first, then a row that holds the code, label and partner.'''
    return write_workbook(file, {
        'Notes': [['Census list used for CPS'], ['Synthetic stand-in']],
        'List': [[None, 'Title', None, 'Code', 'Cross-reference'],
                 [None, 'Crop production', None, '0170', '111'],
                 [None, label, None, code_cell or code, partner]]})


def industry_csv(file: Path, *, label: str = 'Armed Forces', naics: str = '',
                 row_type: str = 'detail', extra: tuple[str, ...] = (),
                 header: str = INDUSTRY_HEADER, code: str = '9890') -> Path:
    rows = [header, 'detail,Crop production,0170,111', f'{row_type},{label},{code},{naics}',
            *extra]
    file.write_text('\n'.join(rows) + '\n', encoding='utf-8-sig')
    return file


def occupation_csv(file: Path, *, label: str = 'Armed Forces', soc: str = '',
                   row_type: str = 'detail', extra: tuple[str, ...] = (),
                   header: str = OCCUPATION_HEADER, code: str = '9840') -> Path:
    rows = [header, 'detail,0010,11-1011,Chief executives', f'{row_type},{code},{soc},{label}',
            *extra]
    file.write_text('\n'.join(rows) + '\n', encoding='utf-8-sig')
    return file


def layout_text(*, industry: str = 'Armed Forces\t\t9890',
                occupation: str = '9840\t\tArmed Forces') -> str:
    return '\n'.join(['CPS record layout', 'Crop production\t\t0170', industry, occupation,
                      'Chief executives\t\t0010']) + '\n'


def ipums_page(code: str, label: str = 'Armed Forces') -> str:
    return ('<html><body><dl class="list-fixed-dt"><dt>0170</dt><dd>Crop production</dd>'
            f'<dt>{code}</dt>\n<dd>{label}</dd></dl></body></html>')


def reference_originals(directory: Path) -> dict[str, Path]:
    '''Write small valid synthetic originals for the seven kinds, never real source bytes.'''
    directory.mkdir(parents=True, exist_ok=True)
    registry = cps_flow_references.REGISTRY
    names = {kind: directory / reference.filename for kind, reference in registry.items()}
    industry_csv(names['cps_basic_2026_industry_codes'])
    occupation_csv(names['cps_basic_2026_occupation_codes'])
    names['cps_basic_2025_layout_codes'].write_text(layout_text(), encoding='utf-8')
    bls_workbook(names['bls_cps_industry_2022'], '9890', 'Part of 92811')
    bls_workbook(names['bls_cps_occupation_2018'], '9840', '55-0000')
    names['ipums_cps_ind_2020_codes'].write_text(ipums_page('9890'), encoding='utf-8')
    names['ipums_cps_occ_2020_codes'].write_text(ipums_page('9840'), encoding='utf-8')
    return names


INDUSTRY_SHEET = '2022 Census Ind Code List '
OCCUPATION_SHEET = '2018 Census Occ Code List'
INDUSTRY_PREAMBLE = [
    ['2022 Census Industry Code List'], ['U.S. Census Bureau'], ['2024-09-09'],
    [None, 'Industry 2022 Description', None, '2022 Census Industry Code', '2022 NAICS Code'],
    [None]]
OCCUPATION_PREAMBLE = [
    [None, 'U.S. Census Bureau'], [None, '2018 Census Occupation Code List'], [None],
    [None, 'last updated: September 26, 2019'],
    [None, '2018 Census Title ', '2018 Census Code', '2018 SOC Code'], [None],
    ['Management,  Business, Science, and Arts Occupations:', None, '0010-3550',
     '11-0000 - 29-0000'], [None]]


def industry_list_workbook(file: Path, rows: list[list[str | None]], *,
                           sheet: str = INDUSTRY_SHEET) -> None:
    '''Write the real sheet name and column layout (A group, B title, D code, E NAICS).

    Each row is one worksheet row of columns A to E. It follows a five-row preamble, so
    row `i` of `rows` is worksheet row `len(INDUSTRY_PREAMBLE) + i + 1`. It writes through
    `write_workbook`, not `code_fixtures.write_xlsx`, because only that writer keeps the
    padding of a cell, and the readers must strip it.
    '''
    write_workbook(file, {sheet: [*INDUSTRY_PREAMBLE, *rows]})


def occupation_list_workbook(file: Path, rows: list[list[str | None]], *,
                             sheet: str = OCCUPATION_SHEET) -> None:
    '''Write the real sheet name and column layout (A group, B title, C code, D SOC token).

    Row `i` of `rows` is worksheet row `len(OCCUPATION_PREAMBLE) + i + 1`.
    '''
    write_workbook(file, {sheet: [*OCCUPATION_PREAMBLE, *rows]})


NAICS_EDGES = [
    ('21', None, 'sector'), ('211', '21', 'subsector'), ('2111', '211', 'industry_group'),
    ('21112', '2111', 'industry'), ('211120', '21112', 'national_industry'),
    ('31-33', None, 'sector'), ('311', '31-33', 'subsector'),
    ('3118', '311', 'industry_group'), ('31181', '3118', 'industry'),
    ('311811', '31181', 'national_industry'), ('311812', '31181', 'national_industry'),
    ('311813', '31181', 'national_industry'), ('31183', '3118', 'industry'),
    ('311830', '31183', 'national_industry'), ('3114', '311', 'industry_group'),
    ('31141', '3114', 'industry'), ('311411', '31141', 'national_industry'),
    ('333', '31-33', 'subsector'), ('3332', '333', 'industry_group'),
    ('33324', '3332', 'industry'), ('333242', '33324', 'national_industry'),
    ('3334', '333', 'industry_group'), ('33341', '3334', 'industry'),
    ('333415', '33341', 'national_industry')]
SOC_EDGES = [
    ('13-0000', None, 'major'), ('13-2000', '13-0000', 'minor'),
    ('13-2050', '13-2000', 'broad'), ('13-2051', '13-2050', 'detailed'),
    ('13-2052', '13-2050', 'detailed'), ('13-2054', '13-2050', 'detailed'),
    ('13-2090', '13-2000', 'broad'), ('13-2099', '13-2090', 'detailed'),
    ('25-0000', None, 'major'), ('25-1000', '25-0000', 'minor'),
    ('25-1010', '25-1000', 'broad'), ('25-1011', '25-1010', 'detailed'),
    ('25-1020', '25-1000', 'broad'), ('25-1021', '25-1020', 'detailed'),
    ('51-0000', None, 'major'), ('51-4000', '51-0000', 'minor'),
    ('51-4030', '51-4000', 'broad'), ('51-4031', '51-4030', 'detailed'),
    ('51-4032', '51-4030', 'detailed'), ('51-4040', '51-4000', 'broad'),
    ('51-4041', '51-4040', 'detailed'), ('51-4090', '51-4000', 'broad'),
    ('51-4099', '51-4090', 'detailed')]


def tree_frames() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    '''Return `naics_nodes`, `soc_nodes` and `paths` with the Stage 4 columns.

    Each path runs from the root to the node itself, as the Stage 4 `paths` table does.
    '''
    nodes, paths = {}, []
    for system, vintage, edges in (('naics', 2022, NAICS_EDGES), ('soc', 2018, SOC_EDGES)):
        parents = {code: parent for code, parent, _ in edges}
        identifiers = {code: f'{system}:{vintage}:{level}:{code}' for code, _, level in edges}
        rows = []
        for code, _, level in edges:
            rows.append(dict(node_id=identifiers[code], system=system, vintage=vintage,
                             level=level, code=code, title=f'{system} {code}'))
            chain, cursor = [], code
            while cursor is not None:
                chain.append(identifiers[cursor])
                cursor = parents[cursor]
            paths.append(dict(node_id=identifiers[code], path=chain[::-1]))
        nodes[system] = pl.DataFrame(rows)
    return nodes['naics'], nodes['soc'], pl.DataFrame(paths)


# The delivered column order of the two Stage 7 CPS Parquets, measured on 2026-11-23.
MONTHLY_COLUMNS = (
    'YEAR', 'SERIAL', 'MONTH', 'HWTFINL', 'CPSID', 'ASECFLAG', 'MISH', 'REGION', 'STATEFIP',
    'COUNTY', 'METFIPS', 'PERNUM', 'WTFINL', 'CPSIDP', 'CPSIDV', 'EARNWEEK2', 'HOURWAGE2', 'AGE',
    'SEX', 'QAGE', 'QSEX', 'EMPSTAT', 'LABFORCE', 'OCC', 'IND', 'CLASSWKR', 'UHRSWORK1',
    'EMPSAME', 'QUHRSWORK1', 'QEMPSTAT', 'QIND', 'QLABFORC', 'QOCC', 'ACTSAME', 'EDUC', 'QEDUC',
    'EARNWT', 'LNKFW1MWT', 'QEARNWEE', 'PAIDHOUR', 'ELIGORG', 'QHOURWAG', 'QPAIDHOU')
ASEC_COLUMNS = (
    'YEAR', 'SERIAL', 'MONTH', 'CPSID', 'ASECFLAG', 'ASECWTH', 'REGION', 'STATEFIP', 'COUNTY',
    'METFIPS', 'PERNUM', 'CPSIDP', 'CPSIDV', 'ASECWT', 'AGE', 'SEX', 'QAGE', 'QSEX', 'EMPSTAT',
    'LABFORCE', 'OCC', 'IND', 'CLASSWKR', 'QCLASSWK', 'QEMPSTAT', 'QIND', 'QLABFORC', 'QOCC',
    'EDUC', 'QEDUC', 'REPWTP', *(f'REPWTP{number}' for number in range(1, 161)), 'OCCLY',
    'INDLY', 'CLASSWLY', 'WKSWORK1', 'UHRSWORKLY', 'QCLASSWL', 'QOCCLY', 'QUHRSWORKLY',
    'QWKSWORK', 'INCWAGE', 'INCWAGE_CPIU_2010', 'MIGSTA1', 'WHYMOVE', 'MIGRATE1', 'QMIGRAT1',
    'QMIGST1B', 'QWHYMOVE', 'QMIGRAT1G')
# DDI decimal exponents as delivered; every other variable has 0.
DDI_DECIMALS = {
    'HWTFINL': 4, 'WTFINL': 4, 'EARNWT': 4, 'LNKFW1MWT': 4, 'ASECWTH': 4, 'ASECWT': 4,
    'EARNWEEK2': 2, 'HOURWAGE2': 2, **{f'REPWTP{number}': 4 for number in range(1, 161)}}
# Neutral values: an employed stayer on the seeded lists, with positive weights written as
# decimal text. ASECFLAG is 2 so that the converter infers Int64: a column of blanks
# converts to String.
MONTHLY_DEFAULTS = {
    'YEAR': 2025, 'SERIAL': 1, 'MONTH': 1, 'HWTFINL': '1000.0000', 'CPSID': 1, 'ASECFLAG': 2,
    'MISH': 1, 'REGION': 11, 'STATEFIP': 23, 'COUNTY': 0, 'METFIPS': 99999, 'PERNUM': 1,
    'WTFINL': '1000.0000', 'CPSIDP': 1, 'CPSIDV': 1, 'EARNWEEK2': '500.00',
    'HOURWAGE2': '20.00', 'AGE': 40, 'SEX': 1, 'QAGE': 0, 'QSEX': 0, 'EMPSTAT': 10,
    'LABFORCE': 2, 'OCC': '0010', 'IND': '0170', 'CLASSWKR': 21, 'UHRSWORK1': 40, 'EMPSAME': 2,
    'QUHRSWORK1': 0, 'QEMPSTAT': 0, 'QIND': 0, 'QLABFORC': 0, 'QOCC': 0, 'ACTSAME': 1,
    'EDUC': 73, 'QEDUC': 0, 'EARNWT': '1000.0000', 'LNKFW1MWT': '1500.1234', 'QEARNWEE': 0,
    'PAIDHOUR': 1, 'ELIGORG': 1, 'QHOURWAG': 0, 'QPAIDHOU': 0}
ASEC_DEFAULTS = {
    'YEAR': 2025, 'SERIAL': 1, 'MONTH': 3, 'CPSID': 1, 'ASECFLAG': 1, 'ASECWTH': '1000.0000',
    'REGION': 11, 'STATEFIP': 23, 'COUNTY': 0, 'METFIPS': 99999, 'PERNUM': 1, 'CPSIDP': 1,
    'CPSIDV': 1, 'ASECWT': '1500.1234', 'AGE': 40, 'SEX': 1, 'QAGE': 0, 'QSEX': 0,
    'EMPSTAT': 10, 'LABFORCE': 2, 'OCC': '0010', 'IND': '0170', 'CLASSWKR': 21, 'QCLASSWK': 0,
    'QEMPSTAT': 0, 'QIND': 0, 'QLABFORC': 0, 'QOCC': 0, 'EDUC': 73, 'QEDUC': 0, 'REPWTP': 1,
    **{f'REPWTP{number}': '1500.1234' for number in range(1, 161)}, 'OCCLY': '0010',
    'INDLY': '0170', 'CLASSWLY': 21, 'WKSWORK1': 52, 'UHRSWORKLY': 40, 'QCLASSWL': 0,
    'QOCCLY': 0, 'QUHRSWORKLY': 0, 'QWKSWORK': 0, 'INCWAGE': 50000,
    'INCWAGE_CPIU_2010': '40000.0', 'MIGSTA1': 0, 'WHYMOVE': 0, 'MIGRATE1': 1, 'QMIGRAT1': 0,
    'QMIGST1B': 0, 'QWHYMOVE': 0, 'QMIGRAT1G': 0}

# DDI categories with the labels exactly as the two deliveries carry them (2026-11-23).
EMPSTAT_CATEGORIES = [
    ('00', 'NIU'), ('01', 'Armed Forces'), ('10', 'At work'),
    ('12', 'Has job, not at work last week'), ('20', 'Unemployed'),
    ('21', 'Unemployed, experienced worker'), ('22', 'Unemployed, new worker'),
    ('30', 'Not in labor force'), ('31', 'NILF, housework'), ('32', 'NILF, unable to work'),
    ('33', 'NILF, school'), ('34', 'NILF, other'), ('35', 'NILF, unpaid, lt 15 hours'),
    ('36', 'NILF, retired')]
EMPSAME_CATEGORIES = [('01', 'No'), ('02', 'Yes'), ('96', 'Refused'), ('97', "Don't know"),
                      ('99', 'NIU')]
ACTSAME_CATEGORIES = [('01', 'Yes'), ('02', 'No'), ('96', 'Refused'), ('97', "Don't Know"),
                      ('99', 'NIU')]
_FLAG_LABELS = ['No change or children or armed forces', 'Value to blank', 'Blank to value',
                'Value to value', 'Allocated']
QEMPSTAT_CATEGORIES = [(str(value), label) for value, label in enumerate(
    [*_FLAG_LABELS, 'Blank to allocated value', 'Blank to longitudinal value'])]
QCODE_CATEGORIES = [(str(value), label) for value, label in enumerate(
    [*_FLAG_LABELS, 'Value to allocated value', 'Blank to allocated value',
     'Blank to longitudinal value'])]
QOCCLY_CATEGORIES = [('0', 'No change or children or armed forces'), ('1', 'Allocated')]
MISH_CATEGORIES = [(str(value), label) for value, label in enumerate(
    ['One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight'], 1)]
ASECFLAG_CATEGORIES = [('1', 'ASEC'), ('2', 'March Basic')]
DDI_CATEGORIES = {
    'monthly': {'ASECFLAG': ASECFLAG_CATEGORIES, 'MISH': MISH_CATEGORIES,
                'EMPSTAT': EMPSTAT_CATEGORIES, 'EMPSAME': EMPSAME_CATEGORIES,
                'QEMPSTAT': QEMPSTAT_CATEGORIES, 'QIND': QCODE_CATEGORIES,
                'QOCC': QCODE_CATEGORIES, 'ACTSAME': ACTSAME_CATEGORIES},
    'asec': {'ASECFLAG': ASECFLAG_CATEGORIES, 'EMPSTAT': EMPSTAT_CATEGORIES,
             'QEMPSTAT': QEMPSTAT_CATEGORIES, 'QIND': QCODE_CATEGORIES,
             'QOCC': QCODE_CATEGORIES, 'QOCCLY': QOCCLY_CATEGORIES},
}

# Seeded list rows. Every candidate falls inside `tree_frames()`. The two X rows have PUMS
# lists: `8025` is equal, `8225` is a strict subset (its extra 51-4041 is claimed by 7000).
SEED_INDUSTRY_ROWS = [
    [None, 'Fixture industries', None, '0170-3070', '21'],
    [None, 'Fixture extraction', None, '0170', '211120'],
    [None, 'Fixture bakeries', None, '1370', '311811, 311812'],
    [None, 'Fixture other food', None, '1380', '3118 exc. 311813'],
    [None, 'Fixture machinery', None, '3070', 'Part of 333'],
    [None, 'Unemployed, last worked 5 years ago or earlier or never worked', None, '9920',
     None]]
SEED_OCCUPATION_ROWS = [
    [None, 'Fixture budget analysts', '0010', '13-2051'],
    [None, 'Fixture financial analysts', '0020', '13-2050'],
    [None, 'Fixture postsecondary teachers', '2200', '25-1000'],
    [None, 'Fixture forging workers', '7000', '51-4040'],
    [None, 'Fixture machine setters', '8025', '51-403X'],
    [None, 'Fixture metal workers, all other', '8225', '51-4XXX'],
    [None, 'Fixture military, rank not specified', '9830', 'none'],
    [None, 'Fixture unemployed, never worked', '9920', 'none']]
SEED_PUMS_LISTS = [
    ('naics', '0170', ['211120'], ['pums_industry_2022:ACS!A:B:row=4']),
    ('soc', '8025', ['51-4031', '51-4032'], ['pums_occupation_2018:ACS!A:B:row=7']),
    ('soc', '8225', ['51-4041', '51-4099'], ['pums_occupation_2018:ACS!A:B:row=9'])]
SEED_IDS = {
    'stage7_run': 'stage7_fixture_verification', 'stage7_receipt': 'stage7_fixture_references',
    'stage8_receipt': 'stage8_fixture_references', 'stage8_mapping_run': 'stage8_fixture_mapping',
    'codes_run': 'stage4_fixture_codes', 'cps_receipt': 'stage11_fixture_references'}
# Stage 7 kinds that the Stage 11 build reads or cites, plus one it never touches.
SEED_STAGE7_KINDS = (
    'census_industry_2022', 'asec_2025_documentation', 'asec_2026_documentation',
    'cps_jan2025_industry_documentation', 'cps_lnkfw1mwt', 'cps_empsame', 'cps_actsame',
    'cps_industry_2025_codes')
SEED_RETRIEVED_AT = '2026-10-12T16:27:00+00:00'


def monthly_row(**fields) -> dict:
    '''One monthly Parquet row: every delivered column, with a neutral default for each.'''
    unknown = set(fields) - set(MONTHLY_COLUMNS)
    if unknown:
        raise KeyError(f'not a monthly column: {sorted(unknown)}')
    return {name: fields.get(name, MONTHLY_DEFAULTS[name]) for name in MONTHLY_COLUMNS}


def asec_row(**fields) -> dict:
    '''One ASEC Parquet row: every delivered column, with a neutral default for each.'''
    unknown = set(fields) - set(ASEC_COLUMNS)
    if unknown:
        raise KeyError(f'not an ASEC column: {sorted(unknown)}')
    return {name: fields.get(name, ASEC_DEFAULTS[name]) for name in ASEC_COLUMNS}


@dataclass(frozen=True)
class SeededUpstreams:
    data_dir: Path
    request: 'cps_flow_inputs.InputRequest'  # noqa: F821
    reference_id: str


def _json_record(entry) -> dict:
    return json.loads(json.dumps(asdict(entry)))


def _record(data_dir: Path, file: Path, **provenance) -> dict:
    '''Append one manifest entry for a seeded raw file and return it as a citation.'''
    from embedding_data import manifest, paths

    manifest_file = paths.manifest_path(data_dir)
    entry = manifest.describe_file(
        file, manifest_file.parent, retrieved_at=datetime.fromisoformat(SEED_RETRIEVED_AT),
        **provenance)
    manifest.append_entries(manifest_file, [entry])
    return _json_record(entry)


def _write_json(file: Path, value: object) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n', encoding='utf-8')


def cps_ddi_xml(set_name: str, samples: list[str]) -> str:
    '''A delivered-shape DDI: every column in order, with the real category labels.'''
    columns = MONTHLY_COLUMNS if set_name == 'monthly' else ASEC_COLUMNS
    variables = []
    for name in columns:
        categories = ''.join(
            f'<catgry><catValu>{value}</catValu><labl>{escape(label)}</labl></catgry>'
            for value, label in DDI_CATEGORIES[set_name].get(name, []))
        variables.append(f'<var name="{name}" dcml="{DDI_DECIMALS.get(name, 0)}">'
                         f'<labl>{name} (synthetic)</labl>{categories}</var>')
    notes = ''.join(f'<notes>{sample}: synthetic sample</notes>' for sample in samples)
    return ('<codeBook xmlns="ddi:codebook:2_5" version="2.5"><stdyDscr><citation><titlStmt>'
            '<titl>Synthetic IPUMS CPS data</titl></titlStmt><verStmt>'
            '<version date="2026-10-12">fixture</version></verStmt></citation>'
            f'<stdyInfo>{notes}</stdyInfo></stdyDscr><dataDscr>{"".join(variables)}'
            '</dataDscr></codeBook>')


def _seed_delivery(data_dir: Path, set_name: str, number: int, rows: list[dict]) -> dict:
    '''Write one CPS raw triple, record it, convert it, and return its Stage 7 record.'''
    import gzip

    from embedding_data import ipums_conversion, ipums_ddi, target_io

    columns = MONTHLY_COLUMNS if set_name == 'monthly' else ASEC_COLUMNS
    if any(tuple(row) != columns for row in rows):
        raise ValueError(f'{set_name} rows must carry every column in order')
    if set_name == 'monthly':
        samples = sorted({f'cps{row["YEAR"]}_{row["MONTH"]:02d}b' for row in rows}
                         or {'cps2025_01b'})
    else:
        samples = sorted({f'cps{row["YEAR"]}_03s' for row in rows} or {'cps2025_03s'})
    name = f'cps_{number:05d}'
    directory = data_dir / 'raw/cps' / set_name / name
    directory.mkdir(parents=True)
    definition = {
        'collection': 'cps', 'version': None, 'dataFormat': 'csv',
        'dataStructure': {'rectangular': {'on': 'P'}}, 'description': 'Synthetic CPS fixture',
        'samples': {sample: {} for sample in samples}, 'dataQualityFlags': True,
        'variables': {column: {'preselected': False, 'caseSelections': {},
                               'attachedCharacteristics': [], 'dataQualityFlags': False,
                               'adjustMonetaryValues': False} for column in columns}}
    extract = directory / 'extract.json'
    extract.write_text(json.dumps(definition))
    xml = directory / f'{name}.xml'
    xml.write_text(cps_ddi_xml(set_name, samples), encoding='utf-8')
    csv_gz = directory / f'{name}.csv.gz'
    lines = [','.join(columns), *(','.join('' if value is None else str(value)
                                           for value in row.values()) for row in rows)]
    with gzip.open(csv_gz, 'wt', encoding='utf-8', newline='') as stream:
        stream.write('\n'.join(lines) + '\n')
    citations = [_record(data_dir, file, client='ipumspy', client_version='0.7.0',
                         collection='cps', extract_number=number, samples=samples)
                 for file in (extract, xml, csv_gz)]
    relative = f'derived/cps/{set_name}/{name}.parquet'
    parquet = data_dir / relative
    parquet.parent.mkdir(parents=True, exist_ok=True)
    ipums_conversion.convert(csv_gz, parquet, 'cps')
    return {'delivery_id': name, 'parquet': relative,
            'parquet_record': target_io.file_record(parquet), 'raw_citations': citations,
            'definition': ipums_ddi.read_definition(extract), 'ddi': ipums_ddi.read_ddi(xml)}


def _receipt_original(data_dir: Path, directory: Path, name: str, body: bytes, url: str,
                      **provenance) -> tuple[dict, dict]:
    from embedding_data import target_io

    file = directory / name
    if body:
        file.write_bytes(body)
    citation = _record(data_dir, file, client='manual-import', client_version='0.1.0',
                       source_url=url, proxies=('retrieved_at',), **provenance)
    return target_io.file_record(file), citation


def _absent_record(directory: Path, name: str, data_dir: Path) -> tuple[dict, dict]:
    '''A receipt or inventory record for a file that the Stage 11 build never reads.'''
    record = {'sha256': '0' * 64, 'size': 0}
    path = (directory / name).relative_to(data_dir / 'raw').as_posix()
    citation = {'path': path, 'sha256': '0' * 64, 'size': 0, 'retrieved_at': SEED_RETRIEVED_AT,
                'client': 'manual-import', 'client_version': '0.1.0', 'source_url': None,
                'collection': None, 'extract_number': None, 'samples': [],
                'proxies': ['retrieved_at'], 'through_date': None}
    return record, citation


def _publish_receipt(data_dir: Path, directory: Path, receipt: dict) -> tuple[str, dict]:
    '''Write `receipt.json`, record it as a generated file, and return its pin and citation.'''
    from embedding_data import manifest

    file = directory / 'receipt.json'
    _write_json(file, receipt)
    citation = _record(data_dir, file, client='embedding-data', client_version='0.1.0')
    return manifest.sha256_file(file), citation


def _seed_stage7_receipt(data_dir: Path, reference_id: str) -> tuple[str, dict]:
    from embedding_data import ipums_references

    directory = data_dir / 'raw/references/ipums-verification' / reference_id
    directory.mkdir(parents=True)
    registry = ipums_references.REGISTRY
    industry_list_workbook(directory / registry['census_industry_2022'].filename,
                           SEED_INDUSTRY_ROWS)
    originals, files, citations = {}, {}, []
    for kind in (*SEED_STAGE7_KINDS, 'usa_samples'):
        reference = registry[kind]
        if kind == 'usa_samples':
            files[reference.filename], citation = _absent_record(
                directory, reference.filename, data_dir)
        else:
            body = b'' if kind == 'census_industry_2022' else (
                f'Synthetic documentary original: {kind}\n'.encode())
            files[reference.filename], citation = _receipt_original(
                data_dir, directory, reference.filename, body, reference.url)
            citations.append(citation)
        originals[kind] = {'citation': citation, 'method': 'GET', 'request_body': None,
                           'retrieved_at': SEED_RETRIEVED_AT, 'retrieved_at_is_proxy': True,
                           'source_url': reference.url}
    return _publish_receipt(data_dir, directory, {
        'reference_id': reference_id, 'parser_version': ipums_references.PARSER_VERSION,
        'originals': originals, 'files': files, 'raw_citations': citations})


def _seed_stage8_receipt(data_dir: Path, reference_id: str) -> tuple[str, dict]:
    from embedding_data import acs_mapping_references

    directory = data_dir / 'raw/references/acs-mapping' / reference_id
    directory.mkdir(parents=True)
    version = 'acs-mapping-references-v2'
    originals, files, citations = {}, {}, []
    for kind in ('census_occupation_2018', 'pums_occupation_2018'):
        reference = acs_mapping_references.REGISTRY[kind]
        if kind == 'pums_occupation_2018':
            files[reference.filename], citation = _absent_record(
                directory, reference.filename, data_dir)
        else:
            occupation_list_workbook(directory / reference.filename, SEED_OCCUPATION_ROWS)
            files[reference.filename], citation = _receipt_original(
                data_dir, directory, reference.filename, b'', reference.authority_url,
                collection=version)
            citations.append(citation)
        originals[kind] = {
            'authority_url': reference.authority_url, 'edition': reference.edition,
            'authority_role': reference.authority_role,
            'parser_contract': reference.parser_contract, 'citation': citation,
            'retrieved_at': SEED_RETRIEVED_AT, 'retrieved_at_is_proxy': True,
            **files[reference.filename]}
    return _publish_receipt(data_dir, directory, {
        'reference_id': reference_id, 'reference_version': version, 'originals': originals,
        'request_files': {}, 'raw_citations': citations, 'files': files})


def _publish_run(directory: Path, present: dict[str, set[str]], absent: list[str]) -> str:
    '''Write `outputs.json` over the present files and return its pin.

    `present` maps each written file to the record keys that the stage's inventory keeps.
    Each name in `absent` is listed with a placeholder record and is never written, as a
    stand-in for an upstream file that the Stage 11 build never reads.
    '''
    from embedding_data import manifest, target_io

    outputs = {}
    for name, keys in present.items():
        record = target_io.file_record(directory / name)
        outputs[name] = {key: record[key] for key in keys}
    outputs.update({name: {'sha256': '0' * 64, 'size': 0} for name in absent})
    _write_json(directory / 'outputs.json', outputs)
    return manifest.sha256_file(directory / 'outputs.json')


FILE_KEYS = {'sha256', 'size'}
PARQUET_KEYS = {'sha256', 'size', 'rows', 'columns', 'schema'}


def _seed_stage7_run(data_dir, run_id, deliveries, receipt_id, receipt_citation) -> str:
    directory = data_dir / 'derived/ipums/verification' / run_id
    _write_json(directory / 'inputs.json', {
        'format_version': 'ipums-verification-v1', 'run_id': run_id,
        'references': {'reference_id': receipt_id, 'receipt': {'reference_id': receipt_id},
                       'receipt_citation': receipt_citation},
        'deliveries': deliveries})
    _write_json(directory / 'report.json', {'format_version': 'ipums-verification-v1',
                                            'status': 'unresolved'})
    absent = [f'{name}.parquet' for name in (
        'variable_inventory', 'sample_counts', 'flag_coverage', 'weight_diagnostics',
        'industry_frequencies', 'employment_comparisons', 'conversion_parity',
        'verification_checks')] + ['weight_rules.json']
    return _publish_run(directory, {'inputs.json': FILE_KEYS, 'report.json': FILE_KEYS}, absent)


def _seed_mapping_run(data_dir, run_id, receipt_id, receipt_sha256) -> str:
    directory = data_dir / 'derived/acs/mapping' / run_id
    directory.mkdir(parents=True)
    system, codes, candidates, locators = zip(*SEED_PUMS_LISTS, strict=True)
    pl.DataFrame({
        'code_lookup_id': [f'{kind}:{code}' for kind, code in zip(system, codes, strict=True)],
        'system': list(system), 'paired_census_code': list(codes),
        'canonical_finest_candidates': [list(value) for value in candidates],
        'reference_locators': [list(value) for value in locators]},
    ).write_parquet(directory / 'acs_code_lookup.parquet')
    _write_json(directory / 'inputs.json', {
        'schema_version': 'acs-mapping-v1', 'run_id': run_id,
        'references': {'reference_id': receipt_id, 'receipt_sha256': receipt_sha256}})
    _write_json(directory / 'report.json', {'schema_version': 'acs-mapping-v1', 'run_id': run_id})
    absent = [f'{name}.parquet' for name in (
        'acs_area_lookup', 'puma_county_factors', 'puma_msa_factors', 'puma_msa_coverage',
        'acs_core_canonical', 'acs_five_year_canonical', 'acs_vintage_canonical')]
    return _publish_run(directory, {'acs_code_lookup.parquet': PARQUET_KEYS,
                                    'inputs.json': FILE_KEYS, 'report.json': FILE_KEYS}, absent)


def _seed_codes_run(data_dir, run_id) -> str:
    directory = data_dir / 'derived/codes' / run_id
    directory.mkdir(parents=True)
    naics, soc, code_paths = tree_frames()
    tables = {'naics_nodes.parquet': naics.sort('node_id'),
              'soc_nodes.parquet': soc.sort('node_id'),
              'code_paths.parquet': code_paths.sort('node_id')}
    for name, frame in tables.items():
        frame.write_parquet(directory / name)
    _write_json(directory / 'inputs.json', {'schema_version': 'codes-ita-v1', 'run_id': run_id})
    _write_json(directory / 'report.json', {'schema_version': 'codes-ita-v1', 'tables': {
        name: {'rows': frame.height, 'schema': {c: str(t) for c, t in frame.schema.items()}}
        for name, frame in tables.items()}})
    absent = [f'{name}.parquet' for name in (
        'naics_edges', 'soc_edges', 'naics_native_nodes', 'naics_concordance', 'filing_rules',
        'filing_rule_labels', 'filing_rule_membership', 'ita_naics_lookup',
        'ita_300a_canonical')]
    return _publish_run(directory, {name: FILE_KEYS for name in (
        *tables, 'inputs.json', 'report.json')}, absent)


def seed_upstreams(tmp_path: Path, *, monthly: list[dict], asec: list[dict]) -> SeededUpstreams:
    '''Write hand-made upstreams in the production layout under `tmp_path / 'data'`.

    It writes two CPS raw triples with their manifest entries and converted Parquets, a
    Stage 7 run, the Stage 7 and Stage 8 receipts that hold the two list workbooks, a Stage 8
    mapping run with `acs_code_lookup.parquet`, a Stage 4 codes run with the `tree_frames()`
    node tables, and a Stage 11 receipt imported from `reference_originals`. Each run's
    `outputs.json` also lists the files that the build never reads, which are not written.
    The rows come from `monthly_row` and `asec_row`. The real chain is Task 13.
    '''
    from embedding_data import cps_flow_inputs, manifest

    data_dir = tmp_path / 'data'
    deliveries = {'cps/monthly': _seed_delivery(data_dir, 'monthly', 1, monthly),
                  'cps/asec': _seed_delivery(data_dir, 'asec', 2, asec)}
    stage7_receipt_sha256, stage7_citation = _seed_stage7_receipt(
        data_dir, SEED_IDS['stage7_receipt'])
    stage8_receipt_sha256, _ = _seed_stage8_receipt(data_dir, SEED_IDS['stage8_receipt'])
    stage7_outputs_sha256 = _seed_stage7_run(data_dir, SEED_IDS['stage7_run'], deliveries,
                                             SEED_IDS['stage7_receipt'], stage7_citation)
    mapping_outputs_sha256 = _seed_mapping_run(data_dir, SEED_IDS['stage8_mapping_run'],
                                               SEED_IDS['stage8_receipt'], stage8_receipt_sha256)
    codes_outputs_sha256 = _seed_codes_run(data_dir, SEED_IDS['codes_run'])
    reference_id = SEED_IDS['cps_receipt']
    originals = reference_originals(tmp_path / 'stage11-originals')
    for kind, file in originals.items():
        cps_flow_references.import_reference(data_dir, reference_id, kind, file)
    cps_receipt_sha256 = manifest.sha256_file(
        data_dir / cps_flow_references.SNAPSHOT_ROOT / reference_id / 'receipt.json')
    request = cps_flow_inputs.InputRequest(
        stage7_run=SEED_IDS['stage7_run'], stage7_outputs_sha256=stage7_outputs_sha256,
        stage7_receipt=SEED_IDS['stage7_receipt'], stage7_receipt_sha256=stage7_receipt_sha256,
        stage8_receipt=SEED_IDS['stage8_receipt'], stage8_receipt_sha256=stage8_receipt_sha256,
        stage8_mapping_run=SEED_IDS['stage8_mapping_run'],
        stage8_mapping_outputs_sha256=mapping_outputs_sha256,
        codes_run=SEED_IDS['codes_run'], codes_outputs_sha256=codes_outputs_sha256,
        cps_receipt=reference_id, cps_receipt_sha256=cps_receipt_sha256)
    return SeededUpstreams(data_dir, request, reference_id)
