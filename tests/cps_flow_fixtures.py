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


# ---- A hand-made monthly and ASEC case for the job-flow bundle (Task 11)

# Made-up identifiers, long enough that no count, code or hash of the bundle contains them.
JOB_FLOW_CPSID = 7_711_000_000_000
JOB_FLOW_CPSIDV = 8_822_000_000_000_000
JOB_FLOW_CPSIDP = 9_933_000_000_000
# The weight of every later-month row, so that a link weighted at its later month shows.
JOB_FLOW_LATER_WEIGHT = '7.0000'
_JAN, _FEB = (2025, 1, 1), (2025, 2, 2)
_SEP, _NOV = (2025, 9, 1), (2025, 11, 3)
_MAR26, _APR26 = (2026, 3, 5), (2026, 4, 6)
# Each person: household, (YEAR, MONTH, MISH) at t and at t+1, the fields at t, the fields at
# t+1. An earlier-month row answers EMPSAME and ACTSAME 99 unless its fields say otherwise.
# `E` people test monthly_ee, `U` people monthly_ue and `L` people the linkage rules.
JOB_FLOW_PEOPLE = {
    # An employer change, eligible and strict in both dimensions.
    'E1': (101, _JAN, _FEB, dict(LNKFW1MWT='1500.1234'),
           dict(IND='1370', OCC='0020', EMPSAME=1, ACTSAME=99)),
    # A duty change: occupation eligible, industry coding noise after the duty change.
    'E2': (102, _JAN, _FEB, dict(LNKFW1MWT='1200.5000'),
           dict(IND='1380', OCC='2200', EMPSAME=2, ACTSAME=2)),
    # Coding noise in industry, no change in occupation. Its CPSIDP changes, so the CPSIDP
    # count of its month pair is one lower.
    'E3': (103, _JAN, _FEB, dict(IND='1370', OCC='0020', LNKFW1MWT='1100.0000'),
           dict(IND='0170', OCC='0020', EMPSAME=2, ACTSAME=1, CPSIDP=JOB_FLOW_CPSIDP + 999)),
    # A stayer. Its earlier row (MISH 1) answers EMPSAME 2: a source exception.
    'E4': (104, _JAN, _FEB, dict(LNKFW1MWT='1000.0000', EMPSAME=2, ACTSAME=1),
           dict(EMPSAME=2, ACTSAME=1)),
    # Coding noise in occupation, no change in industry.
    'E5': (105, _JAN, _FEB, dict(IND='3070', LNKFW1MWT='1300.0000'),
           dict(IND='3070', OCC='0020', EMPSAME=2, ACTSAME=1)),
    # An unusable guard in both dimensions, with an edited occupation flag.
    'E6': (106, _JAN, _FEB, dict(LNKFW1MWT='1400.0000'),
           dict(IND='1370', OCC='0020', EMPSAME=97, ACTSAME=99, QOCC=2)),
    # An unusable occupation guard; the industry guard is `same`.
    'E7': (107, _JAN, _FEB, dict(LNKFW1MWT='1600.0000'),
           dict(OCC='0020', EMPSAME=2, ACTSAME=96)),
    # An employer change with an allocated industry (sensitivity only) and an occupation
    # outside the universe.
    'E8': (108, _JAN, _FEB, dict(OCC='0000', LNKFW1MWT='2400.5000'),
           dict(IND='3070', OCC='7000', EMPSAME=1, ACTSAME=99, QIND=6)),
    'E9': (109, _JAN, _FEB, dict(LNKFW1MWT=''),
           dict(IND='1370', OCC='0020', EMPSAME=1, ACTSAME=99)),
    'E10': (110, _JAN, _FEB, dict(LNKFW1MWT='0.0000'),
            dict(IND='1370', OCC='0020', EMPSAME=1, ACTSAME=99)),
    'E11': (111, _JAN, _FEB, dict(LNKFW1MWT='1700.0000'),
            dict(EMPSTAT=30, IND='0000', OCC='0000', EMPSAME=99, ACTSAME=99)),
    'E12': (112, _JAN, _FEB, dict(EMPSTAT=12, IND='0000', OCC='0000', LNKFW1MWT='1800.0000'),
            dict(EMPSAME=1, ACTSAME=99)),
    # Special ends on a link that no product admits.
    'E14': (114, _JAN, _FEB, dict(IND='9890', LNKFW1MWT='1900.0000'),
            dict(OCC='9840', EMPSAME=96, ACTSAME=99)),
    # An employer change in 2026, in the household of E1.
    'E15': (101, _MAR26, _APR26, dict(IND='1370', OCC='0020', LNKFW1MWT='2100.2500'),
            dict(EMPSAME=1, ACTSAME=99)),
    # Unemployed (21) to employed: a move, a diagonal stay and a 9890/9840 origin.
    'U1': (201, _JAN, _FEB, dict(EMPSTAT=21, LNKFW1MWT='1250.0000'),
           dict(IND='3070', OCC='7000', EMPSAME=99, ACTSAME=99)),
    'U2': (202, _JAN, _FEB, dict(EMPSTAT=21, IND='1370', OCC='0020', LNKFW1MWT='1350.0000'),
           dict(IND='1370', OCC='0020', EMPSAME=99, ACTSAME=99)),
    'U3': (203, _JAN, _FEB, dict(EMPSTAT=21, IND='9890', OCC='9840', LNKFW1MWT='1450.0000'),
           dict(EMPSAME=99, ACTSAME=99)),
    'U4': (204, _JAN, _FEB, dict(EMPSTAT=22, IND='0000', OCC='0000', LNKFW1MWT='1550.0000'),
           dict(EMPSAME=99, ACTSAME=99)),
    'U5': (205, _JAN, _FEB, dict(EMPSTAT=21, LNKFW1MWT='1650.0000'),
           dict(EMPSTAT=21, EMPSAME=99, ACTSAME=99)),
    'U6': (206, _JAN, _FEB, dict(EMPSTAT=21, IND='0000', OCC='0000', LNKFW1MWT='1750.0000'),
           dict(EMPSAME=99, ACTSAME=99)),
    'U8': (208, _MAR26, _APR26, dict(EMPSTAT=21, IND='1370', OCC='9840', LNKFW1MWT='1850.0000'),
           dict(IND='1370', OCC='0020', EMPSAME=99, ACTSAME=99)),
    # September to November 2025 with MISH 1 to 3: the two-month link, with a nonnull weight.
    'L1': (301, _SEP, _NOV, dict(LNKFW1MWT='900.0000'),
           dict(IND='1370', OCC='0020', EMPSAME=1, ACTSAME=99)),
    # September MISH 3 to November MISH 4: no link.
    'L2': (302, (2025, 9, 3), (2025, 11, 4), dict(), dict()),
    # January MISH 4 to February MISH 5: no link. The later row (MISH 5) answers EMPSAME 1, a
    # source exception.
    'L3': (303, (2025, 1, 4), (2025, 2, 5), dict(), dict(EMPSAME=1, ACTSAME=99)),
}
# ASEC persons: YEAR and fields. A1 has replicate weights that differ from its full weight.
JOB_FLOW_ASEC = {
    'A1': (2025, dict(IND='1370', OCC='0020', ASECWT='3000.5000',
                      **{f'REPWTP{number}': f'{3000 + number}.5000' for number in range(1, 161)})),
    'A2': (2025, dict(ASECWT='2000.0000')),
    'A3': (2026, dict(INDLY='0000', OCCLY='0000', ASECWT='2100.0000')),
    'A4': (2026, dict(INDLY='9890', OCCLY='9840', ASECWT='2200.0000')),
    'A5': (2026, dict(EMPSTAT=21, ASECWT='2300.0000')),
    'A6': (2025, dict(IND='1370', OCC='0020', ASECWT='0.0000')),
    'A7': (2025, dict(EMPSTAT=12, IND='0000', OCC='0000', ASECWT='2500.0000')),
    'A8': (2026, dict(INDLY='1370', OCCLY='0020', OCC='2200', ASECWT='2600.0000', QOCCLY=1)),
}


def job_flow_rows(changes: dict[str, dict] | None = None) -> tuple[list[dict], list[dict]]:
    '''Return the monthly and ASEC rows of the job-flow case, in person order.

    `changes` maps a person to fields that replace those of its earlier-month row (monthly)
    or of its row (ASEC).
    '''
    changes = changes or {}
    monthly = []
    for number, (name, (household, start, end, earlier, later)) in enumerate(
            JOB_FLOW_PEOPLE.items(), start=1):
        person = dict(CPSID=JOB_FLOW_CPSID + household, CPSIDV=JOB_FLOW_CPSIDV + number,
                      CPSIDP=JOB_FLOW_CPSIDP + number)
        for (year, month, mish), fields, defaults in (
                (start, {**earlier, **changes.get(name, {})}, dict(EMPSAME=99, ACTSAME=99)),
                (end, later, dict(LNKFW1MWT=JOB_FLOW_LATER_WEIGHT))):
            monthly.append(monthly_row(YEAR=year, MONTH=month, MISH=mish,
                                       **{**person, **defaults, **fields}))
    asec = [asec_row(YEAR=year, CPSID=JOB_FLOW_CPSID + 400 + number,
                     CPSIDV=JOB_FLOW_CPSIDV + 400 + number, CPSIDP=JOB_FLOW_CPSIDP + 400 + number,
                     **{**fields, **changes.get(name, {})})
            for number, (name, (year, fields)) in enumerate(JOB_FLOW_ASEC.items(), start=1)]
    return monthly, asec


# ---- The V12 fixture chain (Task 13): raw files to replay-equal bundles, offline

# Made-up identifiers with their own prefixes, long enough that no count, code or hash of a
# bundle contains them.
V12_CPSID = 5_544_000_000_000
V12_CPSIDV = 6_655_000_000_000_000
V12_CPSIDP = 4_433_000_000_000
# The IDs of the chain. The Stage 7 run and receipt IDs are the ones that
# `acs_mapping_fixtures._authenticated_deliveries` and `seed_reconciliation_inputs` use, and
# `build_fixture_mapping` names the Stage 8 receipt `<mapping run>_references`.
V12_IDS = {
    'stage7_run': 'fixture_ipums', 'stage7_receipt': 'references', 'codes_run': 'fixture_codes',
    'geography_run': 'fixture_geography', 'stage8_mapping_run': 'fixture_mapping',
    'stage8_receipt': 'fixture_mapping_references', 'cps_receipt': 'stage11_fixture_references'}
V12_RUNS = {'first': 'v12_first', 'replay': 'v12_replay'}
# `_authenticated_deliveries` numbers the deliveries in profile order: `usa_1` to `usa_3`, then
# the two CPS deliveries.
V12_DELIVERIES = {'monthly': 4, 'asec': 5}
_V12_JAN, _V12_FEB = (2025, 1, 1), (2025, 2, 2)
# Each person: (YEAR, MONTH, MISH) at t and at t+1, the fields at t, the fields at t+1. An
# earlier-month row answers EMPSAME and ACTSAME 99. Every September 2025 row has a null
# LNKFW1MWT, as delivered: October 2025 is absent.
V12_PEOPLE = {
    # An employer change: EMPSAME 1, both codes differ.
    'P1': (_V12_JAN, _V12_FEB, dict(LNKFW1MWT='1500.1234'),
           dict(IND='0180', OCC='0020', EMPSAME=1, ACTSAME=99)),
    # A duty change at the same employer: both codes differ.
    'P2': (_V12_JAN, _V12_FEB, dict(LNKFW1MWT='1200.5000'),
           dict(IND='0180', OCC='0040', EMPSAME=2, ACTSAME=2)),
    # Coding noise: same employer and duties, the industry differs.
    'P3': (_V12_JAN, _V12_FEB, dict(LNKFW1MWT='1100.2500'),
           dict(IND='1190', EMPSAME=2, ACTSAME=1)),
    # An unusable guard: EMPSAME 99, both codes differ.
    'P4': (_V12_JAN, _V12_FEB, dict(LNKFW1MWT='1300.7500'),
           dict(IND='0180', OCC='0020', EMPSAME=99, ACTSAME=99)),
    # Unemployed (21) with last job 0170/0010, then employed.
    'P5': (_V12_JAN, _V12_FEB, dict(EMPSTAT=21, LNKFW1MWT='1400.0001'),
           dict(IND='0180', OCC='0020', EMPSAME=99, ACTSAME=99)),
    # Unemployed (21) with last job 9890/9840, then employed.
    'P6': (_V12_JAN, _V12_FEB, dict(EMPSTAT=21, IND='9890', OCC='9840', LNKFW1MWT='1600.0002'),
           dict(EMPSAME=99, ACTSAME=99)),
    # September to November 2025 with MISH 1 to 3: the two-month link, an employer change.
    'P7': ((2025, 9, 1), (2025, 11, 3), dict(IND='1190', OCC='0040'),
           dict(IND='0180', OCC='0010', EMPSAME=1, ACTSAME=99)),
    # An employer change whose later industry is allocated (QIND 6, 'Blank to allocated value').
    'P8': (_V12_JAN, _V12_FEB, dict(LNKFW1MWT='1700.0003'),
           dict(IND='0180', OCC='0020', EMPSAME=1, ACTSAME=99, QIND=6)),
    # September MISH 3 to November MISH 4: no link.
    'P9': ((2025, 9, 3), (2025, 11, 4), dict(), dict()),
}
# ASEC persons: YEAR and fields. A1 is the difference, with replicate weights that differ from
# its full weight. Its occupation differs too, so that both ASEC variants have a cell.
V12_ASEC = {
    'A1': (2025, dict(INDLY='0170', IND='0180', OCCLY='0010', OCC='0020', ASECWT='2500.1234',
                      **{f'REPWTP{number}': f'{2500 + number}.1234' for number in range(1, 161)})),
    'A2': (2026, dict(INDLY='0170', IND='0170', ASECWT='2100.0000')),
    'A3': (2026, dict(INDLY='0000', OCCLY='0000', ASECWT='2200.0000')),
    'A4': (2025, dict(INDLY='9890', OCCLY='9840', ASECWT='2300.0000')),
}


def cps_flow_case() -> dict:
    '''Return the monthly and ASEC rows of the V12 chain and each monthly person's CPSIDV.

    Monthly rows are in delivery order, by sample. Every value is on the committed Census lists,
    `0000` or a special.
    '''
    monthly, cpsidv = [], {}
    for number, (name, (start, end, earlier, later)) in enumerate(V12_PEOPLE.items(), start=1):
        person = dict(CPSID=V12_CPSID + number, CPSIDV=V12_CPSIDV + number,
                      CPSIDP=V12_CPSIDP + number)
        cpsidv[name] = person['CPSIDV']
        for (year, month, mish), fields, defaults in (
                (start, earlier, dict(EMPSAME=99, ACTSAME=99)), (end, later, {})):
            unlinked = dict(LNKFW1MWT=None) if (year, month) == (2025, 9) else {}
            monthly.append(monthly_row(YEAR=year, MONTH=month, MISH=mish,
                                       **{**person, **defaults, **fields, **unlinked}))
    monthly.sort(key=lambda row: (row['YEAR'], row['MONTH']))
    asec = [asec_row(YEAR=year, CPSID=V12_CPSID + 100 + number,
                     CPSIDV=V12_CPSIDV + 100 + number, CPSIDP=V12_CPSIDP + 100 + number, **fields)
            for number, (year, fields) in enumerate(V12_ASEC.values(), start=1)]
    return {'monthly': monthly, 'asec': asec, 'cpsidv': cpsidv}


def _v12_delivery(data_dir: Path, set_name: str, rows: list[dict]) -> dict:
    '''Write one CPS raw triple in the layout of `_authenticated_deliveries` and convert it.

    The triple is recorded in the manifest of `data_dir` before the unchanged converter runs.
    The definition requests every column, with the monthly LABFORCE case selection of the
    Stage 7 profile. Returns the delivery's `selection.json` entry.
    '''
    import gzip

    from embedding_data import ipums_conversion

    columns = MONTHLY_COLUMNS if set_name == 'monthly' else ASEC_COLUMNS
    suffix = 'b' if set_name == 'monthly' else 's'
    samples = sorted({f'cps{row["YEAR"]}_{row["MONTH"]:02d}{suffix}' for row in rows})
    number = V12_DELIVERIES[set_name]
    name = f'cps_{number}'
    directory = data_dir / 'raw/cps' / set_name / name
    directory.mkdir(parents=True)
    selections = {'LABFORCE': {'general': ['2']}} if set_name == 'monthly' else {}
    definition = {
        'collection': 'cps', 'version': None, 'dataFormat': 'csv',
        'dataStructure': {'rectangular': {'on': 'P'}}, 'description': 'Synthetic CPS fixture',
        'samples': {sample: {} for sample in samples}, 'dataQualityFlags': True,
        'variables': {column: {'preselected': False,
                               'caseSelections': selections.get(column, {}),
                               'attachedCharacteristics': [], 'dataQualityFlags': False,
                               'adjustMonetaryValues': False} for column in columns}}
    (directory / 'extract.json').write_text(json.dumps(definition))
    (directory / f'{name}.xml').write_text(cps_ddi_xml(set_name, samples), encoding='utf-8')
    csv_gz = directory / f'{name}.csv.gz'
    lines = [','.join(columns), *(','.join('' if value is None else str(value)
                                           for value in row.values()) for row in rows)]
    with gzip.open(csv_gz, 'wt', encoding='utf-8', newline='') as stream:
        stream.write('\n'.join(lines) + '\n')
    for file in (directory / 'extract.json', directory / f'{name}.xml', csv_gz):
        _record(data_dir, file, client='fixture', client_version='1', collection='cps',
                extract_number=number, samples=samples)
    relative = f'derived/cps/{set_name}/{name}.parquet'
    (data_dir / relative).parent.mkdir(parents=True, exist_ok=True)
    ipums_conversion.convert(csv_gz, data_dir / relative, 'cps')
    return {'delivery': name, 'parquet': relative}


@dataclass(frozen=True)
class SeededChain:
    '''The real upstream bundles of the V12 chain and the Stage 11 request that selects them.'''
    data_dir: Path
    request: 'cps_flow_inputs.InputRequest'  # noqa: F821
    stage7: Path
    codes: Path
    mapping: Path
    originals: dict[str, Path]


# Step 1 probe of the existing chain helpers (2026-11-24), before this code was written:
# (a) `acs_mapping_fixtures._authenticated_deliveries` writes its two CPS deliveries from
#     constants only: EMPSTAT 10, IND `0170` and OCC `0010` in both, WTFINL `123.5` monthly,
#     INDLY `0180` and OCCLY `0010` in ASEC. Its `prepare_acs` hook runs for ACS profiles only,
#     so it has no CPS hook. `seed_cps_chain` narrows `test_ipums_acceptance.PROFILES` to the
#     three ACS profiles and writes the two CPS triples itself, in the same raw layout.
# (b) The chain's Stage 4 bundle (`_authenticated_codes`, built from the genuine originals in
#     `fixtures/acs_mapping/upstream/stage4-originals.zip`) holds the full NAICS 2022 and
#     SOC 2018 trees: `naics_nodes` has 2,125 rows and `soc_nodes` 1,447 (measured).
# (c) The `census_industry_2022.xlsx` of the chain's Stage 7 receipt and the
#     `census_occupation_2018.xlsx` of its Stage 8 receipt have the SHA-256 of the committed
#     workbooks in `fixtures/acs_mapping/classification/` (measured on a built chain).
#     `build_fixture_mapping` imports an `acs-mapping-references-v1` receipt, the default of
#     `seed_mapping_references`; production selects a v2 receipt. The Stage 11 selector reads
#     only the occupation workbook of that receipt and does not check its version.
def seed_cps_chain(tmp_path: Path, monkeypatch) -> SeededChain:
    '''Seed real Stage 4, 7 and 8 bundles, the two CPS deliveries and the Stage 11 receipt.

    This follows `seed_reconciliation_inputs`, then builds the Stage 8 mapping run with
    `build_fixture_mapping` and imports the Stage 11 references from `reference_originals`
    through `import_reference`. Everything is under `tmp_path`, with `tmp_path / 'data'` as
    the data directory.
    '''
    import acs_mapping_fixtures as mapping
    import test_ipums_acceptance

    from embedding_data import cps_flow_inputs, ipums_verification_run, manifest
    from embedding_data.acs_mapping_contract import SelectionRequest
    from embedding_data.acs_mapping_inputs import select_inputs

    mapping.forbid_external_access(monkeypatch)
    data_dir = tmp_path / 'data'
    directory = tmp_path / 'authenticated-setup'
    directory.mkdir()
    with pytest.MonkeyPatch.context() as profiles:
        profiles.setattr(test_ipums_acceptance, 'PROFILES', [
            profile for profile in test_ipums_acceptance.PROFILES if profile[0] == 'acs'])
        selection = mapping._authenticated_deliveries(
            data_dir, directory, monkeypatch, prepare_acs=mapping._reconciliation_delivery)
    case = cps_flow_case()
    selected = json.loads(selection.read_text())
    for set_name in V12_DELIVERIES:
        selected[f'cps/{set_name}'] = _v12_delivery(data_dir, set_name, case[set_name])
    selection.write_text(json.dumps(selected))
    codes = mapping._authenticated_codes(data_dir, directory)
    geography = mapping._authenticated_geography(data_dir, directory)
    stage7 = ipums_verification_run.measure(data_dir, V12_IDS['stage7_run'],
                                            V12_IDS['stage7_receipt'], selection)
    pins = {name: manifest.sha256_file(path / 'outputs.json') for name, path in (
        ('codes', codes), ('geography', geography), ('ipums', stage7))}
    stage7_receipt = (data_dir / 'raw/references/ipums-verification'
                      / V12_IDS['stage7_receipt'] / 'receipt.json')
    stage8_request = SelectionRequest(
        V12_IDS['codes_run'], pins['codes'], V12_IDS['geography_run'], pins['geography'],
        V12_IDS['stage7_run'], pins['ipums'], manifest.sha256_file(stage7_receipt))
    select_inputs(data_dir, stage8_request).verify()
    fixture = mapping.FixtureInputs(
        data_dir, stage8_request,
        json.loads((stage7 / 'inputs.json').read_text())['deliveries'], pins)
    built = mapping.build_fixture_mapping(fixture, V12_IDS['stage8_mapping_run'], monkeypatch)
    stage8_receipt = (data_dir / 'raw/references/acs-mapping' / V12_IDS['stage8_receipt']
                      / 'receipt.json')
    originals = reference_originals(tmp_path / 'stage11-originals')
    for kind, file in originals.items():
        cps_flow_references.import_reference(data_dir, V12_IDS['cps_receipt'], kind, file)
    cps_receipt = (data_dir / cps_flow_references.SNAPSHOT_ROOT / V12_IDS['cps_receipt']
                   / 'receipt.json')
    request = cps_flow_inputs.InputRequest(
        stage7_run=V12_IDS['stage7_run'], stage7_outputs_sha256=pins['ipums'],
        stage7_receipt=V12_IDS['stage7_receipt'],
        stage7_receipt_sha256=manifest.sha256_file(stage7_receipt),
        stage8_receipt=V12_IDS['stage8_receipt'],
        stage8_receipt_sha256=manifest.sha256_file(stage8_receipt),
        stage8_mapping_run=V12_IDS['stage8_mapping_run'],
        stage8_mapping_outputs_sha256=built['outputs_sha256'],
        codes_run=V12_IDS['codes_run'], codes_outputs_sha256=pins['codes'],
        cps_receipt=V12_IDS['cps_receipt'], cps_receipt_sha256=manifest.sha256_file(cps_receipt))
    return SeededChain(data_dir, request, stage7, codes, Path(built['directory']), originals)


def _count_external_access(monkeypatch, counts: dict[str, int]) -> list:
    '''Install the counted guards on `counts` and count the Stage 11 client too.

    `offline_guards` does the same with a new dict; the chain needs one dict across the
    reinstalls of the upstream helpers. Returns the probes of every counted seam.
    '''
    from functools import partial

    from acs_target_fixtures import install_counted_guards

    probes = install_counted_guards(monkeypatch, counts)

    def deny(*args, **kwargs):
        counts['live_client'] += 1
        raise AssertionError('offline CPS job flows attempted a live client')

    monkeypatch.setattr(cps_flow_references, 'make_client', deny)
    return [*probes, ('live_client', partial(deny, 'guard-probe'))]


def run_cps_flow_v12(data_dir: Path, monkeypatch) -> dict:
    '''Seed the chain under counted guards, then build, verify, build again and compare.

    Returns the `SeededChain`, the converter calls, each build response and its verification,
    the comparison, the external-access counts and the probes of the counting guards.
    '''
    import acs_mapping_fixtures as mapping

    from embedding_data import cps_flow_bundle, ipums_conversion

    counts = {'network': 0, 'environment_file': 0, 'live_client': 0}
    probes = []
    original_guard = mapping.forbid_external_access

    def counted_guard(patch):
        original_guard(patch)
        probes[:] = _count_external_access(patch, counts)

    # The upstream seed and build helpers reinstall their guards: layer the counters after.
    monkeypatch.setattr(mapping, 'forbid_external_access', counted_guard)
    counted_guard(monkeypatch)
    conversions = []
    convert = ipums_conversion.convert

    def recorded_convert(csv_gz, parquet, source):
        conversions.append((Path(csv_gz), Path(parquet), source))
        return convert(csv_gz, parquet, source)

    monkeypatch.setattr(ipums_conversion, 'convert', recorded_convert)
    chain = seed_cps_chain(data_dir.parent, monkeypatch)
    if chain.data_dir != data_dir:
        raise ValueError('the chain seeded another data directory')
    counted_guard(monkeypatch)
    result = {'chain': chain, 'conversions': conversions, 'external_access_counts': counts,
              'probes': probes}
    for key, run_id in V12_RUNS.items():
        response = cps_flow_bundle.build(data_dir, run_id, chain.request)
        result[key] = response
        result[key + '_verification'] = cps_flow_bundle.verify_bundle(
            Path(response['directory']), data_dir,
            expected_outputs_sha256=response['outputs_sha256'])
    result['compared'] = cps_flow_bundle.compare_runs(
        Path(result['first']['directory']), Path(result['replay']['directory']))
    return result
