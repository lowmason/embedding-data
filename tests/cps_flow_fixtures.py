'''Synthetic Stage 11 reference originals and the offline guards for CPS job-flow tests.'''

from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile

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
                    f'<c r="{chr(65 + c)}{r}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
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
