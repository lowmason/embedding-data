'''Synthetic Stage 11 reference originals and the offline guards for CPS job-flow tests.'''

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
