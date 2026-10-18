'''Strict, unweighted ACS classification evidence from selected public originals.'''

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import fastexcel
import polars as pl

from embedding_data import acs_mapping_references as refs
from embedding_data import manifest
from embedding_data.acs_mapping_contract import CODE_RULE_VERSION, CODE_SCHEMA, NATURAL_KEYS
from embedding_data.acs_mapping_inputs import SelectedInputs
from embedding_data.acs_mapping_io import safe_path
from embedding_data.classification_tables import naics_tables

KEY = list(NATURAL_KEYS['code'])
MEMBERSHIP_SCHEMA = {
    **{name: pl.String for name in KEY},
    'native_finest_code': pl.String,
    'native_node_id': pl.String,
    'aggregation_type': pl.String,
    'aggregation_markers': pl.List(pl.String),
    'flag_partial': pl.Boolean,
    'flag_exception': pl.Boolean,
    'reference_ids': pl.List(pl.String),
    'reference_locators': pl.List(pl.String),
}
DEFERRED = {
    'code_lookup_id',
    'canonical_vintage',
    'canonical_finest_candidates',
    'canonical_candidate_paths',
    'canonical_common_node_id',
    'canonical_scalar_code',
    'canonical_scalar_node_id',
    'flag_vintage_crosswalk',
}
METADATA_SCHEMA = {name: dtype for name, dtype in CODE_SCHEMA.items() if name not in DEFERRED}
# Approved D3 disposition, bounded to assertions in the inspected paired-industry edition.
# Each pair is (Census code, rejected IPUMS token); no future disagreement is waived.
KNOWN_INDUSTRY_CONFLICTS = {
    2017: {
        ('0190', '1133'),
        ('0270', '113M'),
        ('0590', '22132'),
        ('0680', '221MP'),
        ('1070', '3113'),
        ('1080', '3114'),
        ('1090', '3115'),
        ('1170', '3116'),
        ('1180', '311811'),
        ('1270', '311M1'),
        ('6180', '4853'),
        ('6190', '485M'),
        ('7071', '5313'),
        ('7072', '531M'),
        ('9070', '8122'),
    },
    2022: {
        ('0190', '1133'),
        ('0270', '113M'),
        ('0590', '22132'),
        ('0680', '221MP'),
        ('1070', '3113'),
        ('1080', '3114'),
        ('1090', '3115'),
        ('1170', '3116'),
        ('1180', '311811'),
        ('1270', '311M1'),
        ('4585', '4249Z'),
        ('6180', '4853'),
        ('6190', '485M'),
        ('7071', '5313'),
        ('7072', '531M'),
        ('9080', '8123'),
    },
}

# Exact structural key/scope signatures from the registered complete Census editions.
# These rows describe headings, not membership; unexpected body keys never become headings.
_FULL_OCCUPATION_SECTIONS = {
    9: ('0010-3550', '11-0000 - 29-0000'),
    11: ('0010-0960', '11-0000 - 13-0000'),
    13: ('0010-0440', '11-0000'),
    49: ('0500-0960', '13-0000'),
    81: ('1005-1980', '15-0000 - 19-0000'),
    83: ('1005-1240', '15-0000'),
    104: ('1305-1560', '17-0000'),
    131: ('1600-1980', '19-0000'),
    161: ('2001-2970', '21-0000 - 27-0000'),
    163: ('2001-2060', '21-0000'),
    182: ('2100-2180', '23-0000'),
    191: ('2205-2555', '25-0000'),
    206: ('2600-2970', '27-0000'),
    240: ('3000-3550', '29-0000'),
    289: ('3601-4655', '31-0000 - 39-0000'),
    291: ('3601-3655', '31-0000'),
    308: ('3700-3960', '33-0000'),
    331: ('4000-4160', '35-0000'),
    346: ('4200-4255', '37-0000'),
    357: ('4330-4655', '39-0000'),
    380: ('4700-5940', '41-0000 - 43-0000'),
    382: ('4700-4965', '41-0000'),
    403: ('5000-5940', '43-0000'),
    460: ('6005-7640', '45-0000 - 49-0000'),
    462: ('6005-6130', '45-0000'),
    473: ('6200-6950', '47-0000'),
    513: ('7000-7640', '49-0000'),
    552: ('7700-9760', '51-0000 - 53-0000'),
    554: ('7700-8990', '51-0000'),
    620: ('9005-9760', '53-0000'),
    622: ('9005-9430', '53-1000 - 53-6000'),
    647: ('9510-9760', '53-7000'),
    661: ('9800-9830', '55-0000'),
}
_FULL_INDUSTRY_SECTIONS = {
    2017: {
        8: ('0170-0490', '11-21'),
        10: ('0170-0290', '11'),
        19: ('0370-0490', '21'),
        32: ('1070-3990', '31-33'),
        114: ('4070-4590', '42'),
        138: ('4670-5790', '44-45'),
        176: ('6070-6390, 0570-0690', '48-49, 22'),
        178: ('6070-6390', '48-49'),
        193: ('0570-0690', '22'),
        202: ('6470-6780', '51'),
        217: ('6870-7190', '52-53'),
        219: ('6870-6992', '52'),
        228: ('7071-7190', '53'),
        237: ('7270-7790', '54-56'),
        240: ('7270-7490', '54'),
        257: ('7580-7790', '56'),
        268: ('7860-8470', '61-62'),
        270: ('7860-7890', '61'),
        277: ('7970-8470', '62'),
        296: ('8561-8690', '71-72'),
        298: ('8561-8590', '71'),
        308: ('8660-8690', '72'),
        315: ('8770-9290', '81'),
        334: ('9370-9590', '92'),
        345: ('9670-9870', '928110'),
    },
    2022: {
        8: ('0170-0490', '11-21'),
        10: ('0170-0290', '11'),
        19: ('0370-0490', '21'),
        32: ('1070-3990', '31-33'),
        114: ('4070-4590', '42'),
        138: ('4670-5791', '44-45'),
        172: ('6070-6390, 0570-0690', '48-49, 22'),
        174: ('6070-6390', '48-49'),
        189: ('0570-0690', '22'),
        198: ('6471-6781', '51'),
        213: ('6871-7190', '52-53'),
        215: ('6871-6992', '52'),
        224: ('7071-7190', '53'),
        233: ('7270-7790', '54-56'),
        236: ('7270-7490', '54'),
        253: ('7580-7790', '56'),
        264: (None, '61-62'),
        265: ('7860-8470', None),
        267: ('7860-7890', '61'),
        274: ('7970-8470', '62'),
        294: ('8561-8690', '71-72'),
        296: ('8561-8590', '71'),
        306: ('8660-8690', '72'),
        314: ('8770-9290', '81'),
        334: ('9370-9590', '92'),
        346: ('9670-9870', 'pt. 92811'),
    },
}


@dataclass(frozen=True)
class CodeEvidence:
    membership: pl.DataFrame
    metadata: pl.DataFrame
    diagnostics: dict


def _node_members(code, nodes, paths):
    matched = nodes.filter(pl.col('code').eq(code))
    if matched.height != 1:
        raise ValueError(f'unsupported aggregation expression: unknown/ambiguous node {code}')
    identifier = matched['node_id'][0]
    finest = nodes.filter(pl.col('level').is_in(['national_industry', 'detailed']))
    descendants = paths.filter(pl.col('path').list.contains(identifier))['node_id']
    result = set(finest.filter(pl.col('node_id').is_in(descendants.implode()))['code'])
    if not result:
        raise ValueError(f'empty classification membership: {code}')
    return result


def _union_expression(expression, nodes, paths):
    if re.search(r'\d\s+\d', expression):
        raise ValueError('unsupported aggregation expression: split code')
    expression = re.sub(r'\b(?:Part of|Pts\.|pt\.)\s+', '', expression)
    expression = re.sub(r'\s+and\s+', ',', expression)
    expression = re.sub(r'\s+', '', expression)
    for spelling, sector in [('31,32,33', '31-33'), ('44,45', '44-45'), ('48,49', '48-49')]:
        expression = expression.replace(spelling, sector)
    if not expression or expression.endswith(','):
        raise ValueError('unsupported aggregation expression')
    result = set()
    for token in expression.split(','):
        if not re.fullmatch(r'(?:\d{2,6}|\d{2}-\d{4}|31-33|44-45|48-49)', token):
            interval = re.fullmatch(r'(\d{6})-(\d{6})', token)
            if not interval:
                raise ValueError(f'unsupported aggregation expression: {token}')
            first, last = interval.groups()
            _node_members(first, nodes, paths)
            _node_members(last, nodes, paths)
            if first > last:
                raise ValueError('unsupported aggregation expression: reversed interval')
            codes = nodes.filter(
                pl.col('level')
                .eq('national_industry')
                .and_(pl.col('code').is_between(pl.lit(first), pl.lit(last)))
            )['code']
            result.update(codes)
        else:
            result.update(_node_members(token, nodes, paths))
    return result


def parse_membership_expression(
    expression: str, nodes: pl.DataFrame, paths: pl.DataFrame
) -> list[str]:
    '''Resolve only explicit public unions, official nodes, ranges and exclusions.'''
    if not isinstance(expression, str):
        raise ValueError('unsupported aggregation expression')
    clauses = expression.strip().split(' exc. ')
    if len(clauses) not in (1, 2):
        raise ValueError('unsupported aggregation expression')
    positive = _union_expression(clauses[0], nodes, paths)
    negative = _union_expression(clauses[1], nodes, paths) if len(clauses) == 2 else set()
    if not positive or not negative.issubset(positive):
        raise ValueError('unsupported aggregation expression: exclusion outside positive scope')
    result = sorted(positive - negative)
    if not result:
        raise ValueError('empty classification membership')
    return result


def _rows(snapshot, kind, sheet):
    refs._validate_workbook(kind, snapshot.files[kind])
    frame = (
        fastexcel.read_excel(snapshot.files[kind].read_bytes())
        .load_sheet(sheet, header_row=None, dtypes='string')
        .to_polars()
    )
    return list(frame.iter_rows())


def _locator(kind, sheet, row, columns):
    return f'{kind}:{sheet}!{columns}:row={row}'


def _industry_rows(snapshot, kind, sheet, vintage):
    result = []
    seen = {}
    for number, row in enumerate(_rows(snapshot, kind, sheet), 1):
        code, expression, token = row[2:5]
        if code is None:
            continue
        if not re.fullmatch(r'\d{4}', code):
            if code == f'{vintage} Industry Code' or re.fullmatch(
                r'\d{4}-\d{4}(?:, \d{4}-\d{4})*', code
            ):
                continue
            raise ValueError('malformed industry reference key')
        if code == '9920' and expression is None and token == '999920':
            result.append((code, token, '', _locator(kind, sheet, number, 'C:E')))
            continue
        if (
            (code in seen and seen[code] != (expression, token))
            or not expression
            or not token
            or not re.fullmatch(r'\d{1,6}(?:[MPSZ]{1,3}[1-7]?)?', token.strip())
        ):
            raise ValueError('contradictory paired or malformed industry row')
        seen[code] = (expression, token)
        result.append(
            (
                code,
                token.strip(),
                expression,
                _locator(kind, sheet, number, 'C:E') + ':source_token_raw=' + repr(token),
            )
        )
    if not result:
        raise ValueError('empty authoritative industry list')
    return result


def _occupation_rows(snapshot, kind, sheet, full, rejected):
    rows = _rows(snapshot, kind, sheet)
    result, seen = [], set()
    for index, row in enumerate(rows):
        code, token, title = row
        if not code:
            continue
        if not re.fullmatch(r'\d{4}', code):
            if (
                index < 10
                or re.fullmatch(r'\d{4}-\d{4}', code)
                or code == 'Note:'
                or code.startswith(('Highlighting ', 'The 4-digit '))
            ):
                continue
            raise ValueError('malformed occupation reference key')
        if code in seen or token is None or title is None:
            raise ValueError('contradictory paired or malformed occupation row')
        seen.add(code)
        original_token = token
        token = token.strip()
        if not re.fullmatch(r'(?:\d{2}-[0-9XY]{4}|999920)', token):
            raise ValueError('unsupported occupation source token')
        # Nested Combines blocks are flattened only through their explicit terminal rows.
        # A letter token must be followed by its own Combines block; never use a wildcard.
        constituents, full_constituents = [], set()
        locators = [
            _locator(kind, sheet, index + 1, 'A:C') + ':source_token_raw=' + repr(original_token)
        ]
        cursor = index + 1
        while cursor < len(rows) and rows[cursor][0] is None:
            value = rows[cursor][1].strip() if rows[cursor][1] else None
            if value and value != 'Combines:':
                if not re.fullmatch(r'\d{2}-[0-9XY]{4}', value.strip()):
                    raise ValueError('unsupported occupation constituent')
                description = rows[cursor][2] or ''
                correspondence = re.match(r'(\d{4}) - ', description)
                if correspondence:
                    full_code = correspondence[1]
                    if full_code not in full:
                        raise ValueError('missing explicit full Census constituent')
                    full_token, full_locator = full[full_code]
                    full_constituents.add(full_code)
                    locators.append(full_locator)
                    if value.replace('-', '') != full_token:
                        # D4 is exactly one independently named constituent in three editions.
                        if not (
                            code == '7640'
                            and token == '49-90XX'
                            and cursor + 1 == 707
                            and value == '40-9095'
                            and full_code == '7550'
                            and full_token == '499095'
                            and description
                            == '7550 - Manufactured building and mobile home installers'
                        ):
                            raise ValueError('contradictory paired occupation constituent')
                        rejected.append(
                            dict(
                                kind=kind,
                                paired_census_code=code,
                                source_token=token.replace('-', ''),
                                asserted_soc=value,
                                full_census_code=full_code,
                                supported_soc='49-9095',
                                status='rejected_d4',
                                reference_locators=[
                                    _locator(kind, sheet, cursor + 1, 'B:C'),
                                    full_locator,
                                ],
                            )
                        )
                        value = '49-9095'
                if not re.search('[XY]', value):
                    constituents.append(value.strip())
                elif cursor + 1 >= len(rows) or (rows[cursor + 1][1] or '').strip() != 'Combines:':
                    raise ValueError('unsupported occupation collapse without explicit members')
                locators.append(
                    _locator(kind, sheet, cursor + 1, 'B:C')
                    + ':asserted_soc_raw='
                    + repr(rows[cursor][1])
                )
            cursor += 1
        if re.search('[XY]', token) and not constituents:
            raise ValueError('unsupported occupation collapse without explicit members')
        if not full_constituents:
            expected = full.get(code)
            full_token = (
                'none'
                if (code, token) in (('9830', '55-9830'), ('9920', '999920'))
                else token.replace('-', '')
            )
            if expected is None or expected[0] != full_token:
                raise ValueError('contradictory paired full Census occupation correspondence')
            locators.append(expected[1])
        # Explicit named collapses use their full Census constituents, not a same-key guess.
        result.append((code, token.replace('-', ''), constituents or [token], locators))
    if not result:
        raise ValueError('empty authoritative occupation list')
    return result


def _occupation_styles(file):
    '''Resolve the published highlighted fill through actual OOXML styles.'''
    namespace = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    try:
        with ZipFile(file) as archive:
            styles = ET.fromstring(archive.read('xl/styles.xml'))
            fills = styles.find('m:fills', namespace)
            formats = styles.find('m:cellXfs', namespace)
            highlighted = set()
            for index, cell_format in enumerate(formats):
                fill = fills[int(cell_format.attrib['fillId'])]
                pattern = fill.find('m:patternFill', namespace)
                color = pattern.find('m:fgColor', namespace) if pattern is not None else None
                if color is not None and color.attrib == {
                    'theme': '7',
                    'tint': '0.79998168889431442',
                }:
                    if pattern.attrib.get('patternType') != 'solid':
                        raise ValueError('contradictory occupation highlighting')
                    highlighted.add(str(index))
            sheet = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
            rows = set()
            for cell in sheet.findall('.//m:c', namespace):
                if cell.attrib.get('s') in highlighted:
                    rows.add(int(re.search(r'\d+', cell.attrib['r'])[0]))
            if not highlighted or not rows:
                raise ValueError('missing occupation highlighting')
            return rows
    except (KeyError, IndexError, ET.ParseError) as error:
        raise ValueError('missing occupation styles or legend') from error


def _complete_reference_rows(rows, key_column, expression_column, header_row, sections, label):
    '''Only exact registered structural signatures may bypass complete data-key validation.'''
    for number, row in enumerate(rows, 1):
        if number <= header_row:
            continue
        code, expression = row[key_column], row[expression_column]
        if number in sections:
            if (code, expression) != sections[number]:
                raise ValueError(f'malformed {label} structural key/scope at row {number}')
            continue
        if code is None and expression is None:
            continue
        if code is None or not re.fullmatch(r'\d{4}', code):
            raise ValueError(f'malformed {label} reference key at row {number}')
        yield number, row


def _paired_reference_key(code, locator, *, numeric_padding=False):
    if code in (None, '', '-'):
        return None
    pattern = r'\d{1,4}' if numeric_padding else r'(?:\d{4}|0)'
    if not re.fullmatch(pattern, code):
        raise ValueError(f'malformed paired reference key: {locator}')
    return code.zfill(4) if numeric_padding else code


def _full_occupation(snapshot):
    rows, result = _rows(snapshot, 'census_occupation_2018', '2018 Census Occ Code List'), {}
    for number, row in _complete_reference_rows(
        rows, 2, 3, 5, _FULL_OCCUPATION_SECTIONS, 'full Census occupation'
    ):
        code, expression = row[2:4]
        if (
            code in result
            or not expression
            or not re.fullmatch(r'(?:\d{2}-[0-9X]{4}|none)', expression)
        ):
            raise ValueError('contradictory full Census occupation category')
        result[code] = (
            expression.replace('-', ''),
            _locator('census_occupation_2018', '2018 Census Occ Code List', number, 'C:D'),
        )
    return result


def _metadata(
    system,
    scheme,
    code,
    token,
    expression,
    members,
    nodes,
    ids,
    locators,
    reasons=(),
    special=None,
):
    markers = sorted(set(re.findall('[MPSZXY]', token)))
    node_code = token if system == 'naics' else token[:2] + '-' + token[2:]
    node = nodes.filter(pl.col('code').eq(node_code))
    node_id = node['node_id'][0] if node.height == 1 and not special else None
    partial = 'P' in markers or bool(re.search(r'(?:Part of|Pts\.|pt\.)', expression))
    aggregate = bool(markers or len(members) > 1 or (members and node_code != members[0]))
    return dict(
        system=system,
        source_scheme=scheme,
        native_vintage=int(scheme[-4:]),
        paired_census_code=code,
        source_token=token,
        mapping_status='documented_special' if special else 'mapped',
        native_node_id=node_id,
        native_finest_candidates=members,
        aggregation_type=(
            'special'
            if special
            else 'source_aggregate'
            if markers
            else 'whole_node'
            if aggregate
            else 'finest'
        ),
        aggregation_markers=markers,
        aggregation_reason_status=(
            'documented' if reasons else 'unknown' if aggregate else 'not_applicable'
        ),
        aggregation_reasons=list(reasons),
        special_reason=special,
        flag_aggregate=aggregate,
        flag_partial=partial,
        flag_exception='Z' in markers,
        flag_reference_ambiguity=False,
        reference_ids=sorted(set(ids)),
        reference_locators=sorted(set(locators)),
        rule_version=CODE_RULE_VERSION,
    )


class _Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.cell, self.text = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.rows.append([])
        if tag in ('td', 'th'):
            self.cell = ''

    def handle_data(self, data):
        self.text.append(data)
        if self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            if self.rows:
                self.rows[-1].append(self.cell.strip())
            self.cell = None


def _token_semantics(snapshot):
    table = _Tables()
    table.feed(snapshot.files['industry_tokens_html'].read_text())
    text = ' '.join(' '.join(table.text).split())
    legend = {
        'M': 'Multiple NAICS codes',
        'P': 'Part of a NAICS code - NAICS code split between two or more Census codes',
        'S': 'Not specified Industry in NAICS sector - Specific to Census codes only',
        'Z': 'Exception to NAICS code - Part of NAICS Industry has own Census code',
    }
    if any(f'{marker} = {meaning}' not in text for marker, meaning in legend.items()):
        raise ValueError('industry marker legend differs')
    result = {2017: {}, 2022: {}}
    for number, row in enumerate(_rows(snapshot, 'ipums_ind_tokens', 'Sheet 1'), 1):
        if number == 1:
            continue
        for vintage, column in [(2017, 7), (2022, 8)]:
            token = row[column]
            if token and token not in ('0', '-'):
                token = token.strip()
                if not re.fullmatch(r'\d{1,6}(?:[MPSZ]{1,3}[1-7]?)?', token):
                    raise ValueError('malformed industry token documentation')
                result[vintage].setdefault(token, []).append(
                    _locator('ipums_ind_tokens', 'Sheet 1', number, 'H:I')
                )
    for kind in ('soc_tokens_html', 'usa_occsoc'):
        if 'confidentiality' not in snapshot.files[kind].read_text():
            raise ValueError('occupation aggregate documentation absent')
    return result


def _selected_full_industry(selected):
    '''Cite frozen Stage 7 originals in place; never import them into this snapshot.'''
    originals = selected.provenance['ipums']['inputs']['references']['receipt']['originals']
    by_vintage, files, excluded = {}, {}, []
    for vintage, sheet, census_header in [
        (2017, '2017 Census Industry Code List', '2017 Census Code'),
        (2022, '2022 Census Ind Code List ', '2022 Census Industry Code'),
    ]:
        kind = f'census_industry_{vintage}'
        citation = originals[kind]['citation']
        file = selected.data_dir / 'raw' / citation['path']
        safe_path(file)
        if manifest.sha256_file(file) != citation['sha256']:
            raise ValueError('selected full Census industry original changed')
        workbook = fastexcel.read_excel(file.read_bytes())
        rows = workbook.load_sheet(sheet, header_row=None, dtypes='string').to_polars().rows()
        if rows[3] != (
            None,
            f'Industry {vintage} Description',
            None,
            census_header,
            f'{vintage} NAICS Code',
        ):
            raise ValueError('selected full Census industry layout changed')
        current = {}
        for number, row in _complete_reference_rows(
            rows, 3, 4, 4, _FULL_INDUSTRY_SECTIONS[vintage], f'full Census industry {vintage}'
        ):
            code, expression = row[3:5]
            if (
                code == '9920'
                and expression is None
                and row[1] == ('Unemployed, last worked 5 years ago or earlier or never worked')
            ):
                excluded.append(
                    dict(
                        kind=kind,
                        code=code,
                        token=None,
                        locators=[_locator(kind, sheet, number, 'D:E')],
                        reason='unemployed_no_work_experience',
                    )
                )
                continue
            if not expression or (code in current and current[code][0] != expression.strip()):
                raise ValueError('contradictory full Census industry category')
            current[code] = (expression.strip(), _locator(kind, sheet, number, 'D:E'))
        by_vintage[vintage], files[vintage] = current, file
    workbook = fastexcel.read_excel(files[2022].read_bytes())
    rows = (
        workbook.load_sheet('2007 to 2022 Industry Crosswalk', header_row=None, dtypes='string')
        .to_polars()
        .rows()
    )
    row = rows[312]
    if not (
        row[0] == '8880'
        and row[1] == '8114 exc. 81143'
        and row[8:10] == ('8891', '8114')
        and row[12:14] == ('8891', '8114')
    ):
        raise ValueError('unexplained diagnostic industry extra')
    if any(by_vintage[v]['8891'][0] != '8114' for v in (2017, 2022)):
        raise ValueError('contradictory current Census industry category')
    legacy = dict(
        legacy_census_code='8880',
        current_census_code='8891',
        current_naics_scope='8114',
        reference_locators=[
            _locator('census_industry_2022', '2007 to 2022 Industry Crosswalk', 313, 'A:O'),
            by_vintage[2017]['8891'][1],
            by_vintage[2022]['8891'][1],
        ],
    )
    return by_vintage, legacy, excluded


def _industry_diagnostics(snapshot, admitted, legacy, excluded):
    diagnostics = []
    assertions = []
    for number, row in enumerate(_rows(snapshot, 'ipums_ind_pairs', 'Sheet1'), 1):
        if number == 1:
            continue
        assertions.extend(
            (v, row[c], row[t], _locator('ipums_ind_pairs', 'Sheet1', number, 'F:O'))
            for v, c, t in [(2017, 5, 13), (2022, 6, 14)]
        )
    table = _Tables()
    table.feed(snapshot.files['industry_pairs_html'].read_text())
    for number, row in enumerate(table.rows, 1):
        if len(row) == 15:
            assertions.extend(
                (v, row[c], row[t], f'industry_pairs_html:tr={number}')
                for v, c, t in [(2017, 4, 12), (2022, 5, 13)]
            )
    for vintage, code, token, locator in assertions:
        code = _paired_reference_key(code, locator)
        if code is None:
            continue
        if code == '9920':
            if token != '999920':
                raise ValueError('contradictory paired nonworking industry reference')
            excluded.append(
                dict(
                    kind=locator.split(':')[0],
                    code=code,
                    token=token,
                    locators=[locator],
                    reason='unemployed_no_work_experience',
                )
            )
            continue
        if not code or not token or token in ('-', '0') or code in ('0', '0000'):
            continue
        expected = admitted.get((vintage, code))
        if expected is None:
            if (code, token) != ('8880', '8114'):
                raise ValueError(f'contradictory paired industry diagnostic extra: {locator}')
            # This registered IPUMS-only assertion supplies no admitted Census PUMS key.
            diagnostics.append(
                dict(
                    vintage=vintage,
                    paired_census_code=code,
                    source_token=token,
                    locator=locator,
                    status='not_in_pums_list',
                    historical_evidence=legacy,
                )
            )
            continue
        if token.strip() != expected:
            if (code, token.strip()) not in KNOWN_INDUSTRY_CONFLICTS[vintage]:
                raise ValueError(f'contradictory paired industry diagnostic: {locator}')
            diagnostics.append(
                dict(
                    vintage=vintage,
                    paired_census_code=code,
                    source_token=token,
                    authoritative_token=expected,
                    locator=locator,
                    status='rejected_d3',
                )
            )
    return diagnostics


def _validate_occ_pairs(snapshot, admitted, excluded):
    assertions, citations = [], {}
    for sheet, c, t in [
        ('Codes without Descriptions', 7, 14),
        ('Codes with Descriptions', 13, 27),
    ]:
        for number, row in enumerate(_rows(snapshot, 'ipums_occ_pairs', sheet), 1):
            if number == 1:
                continue
            assertions.append((row[c], row[t], _locator('ipums_occ_pairs', sheet, number, 'H:AB')))
    table = _Tables()
    table.feed(snapshot.files['occupation_pairs_html'].read_text())
    for number, row in enumerate(table.rows, 1):
        if len(row) == 15:
            assertions.append((row[6], row[13], f'occupation_pairs_html:tr={number}'))
    for code, token, locator in assertions:
        code = _paired_reference_key(code, locator, numeric_padding=True)
        if code is None:
            continue
        if code == '9920':
            if token != '999920':
                raise ValueError('contradictory paired nonworking occupation reference')
            excluded.append(
                dict(
                    kind=locator.split(':')[0],
                    code=code,
                    token=token,
                    locators=[locator],
                    reason='unemployed_no_work_experience',
                )
            )
            continue
        if not code or not token or code in ('0', '0000') or token == '-':
            continue
        if (code, token) not in admitted:
            raise ValueError(f'contradictory paired occupation: {locator}')
        citations.setdefault((code, token), []).append(locator)
    return citations


def read_code_evidence(snapshot: refs.ReferenceSnapshot, selected: SelectedInputs) -> CodeEvidence:
    '''Read complete selected originals before admitting any observed source keys.'''
    if manifest.sha256_file(snapshot.directory / 'receipt.json') != snapshot.receipt_sha256:
        raise ValueError('classification receipt differs from selected snapshot')
    for kind, file in snapshot.files.items():
        safe_path(file)
        citation = snapshot.receipt['originals'][kind]
        if manifest.sha256_file(file) != citation['sha256']:
            raise ValueError('classification original differs from snapshot receipt')
    for name in ('naics_native_nodes', 'soc_nodes', 'code_paths'):
        safe_path(selected.codes[name])
        expected = selected.provenance['codes']['tables'][name]
        if manifest.sha256_file(selected.codes[name]) != expected['sha256']:
            raise ValueError('selected classification table differs from pinned input')
    native = pl.read_parquet(selected.codes['naics_native_nodes'])
    soc = pl.read_parquet(selected.codes['soc_nodes'])
    paths = pl.read_parquet(selected.codes['code_paths'])
    metadata, industry, exclusions = [], {}, []
    full_industry, legacy_industry, full_exclusions = _selected_full_industry(selected)
    exclusions.extend(full_exclusions)
    token_locators = _token_semantics(snapshot)
    for vintage in (2017, 2022):
        nodes = native.filter(pl.col('vintage').eq(vintage))
        native_paths = naics_tables(nodes.select('vintage', 'code', 'title'), vintage)[2]
        kinds = [(f'pums_industry_{vintage}', 'ACS')]
        if vintage == 2022:
            kinds += [('pums_annual_2024', 'Industry'), ('pums_five_year_2024', 'Industry')]
        by_code = {}
        for kind, sheet in kinds:
            for code, token, expression, locator in _industry_rows(snapshot, kind, sheet, vintage):
                if code == '9920':
                    exclusions.append(
                        dict(
                            kind=kind,
                            code=code,
                            token=token,
                            locators=[locator],
                            reason='unemployed_no_work_experience',
                        )
                    )
                    continue
                members = parse_membership_expression(expression, nodes, native_paths)
                previous = by_code.get(code)
                if previous:
                    if (
                        previous['source_token'] != token
                        or previous['native_finest_candidates'] != members
                    ):
                        raise ValueError(f'contradictory paired industry authority: {locator}')
                    previous['reference_ids'].append(kind)
                    previous['reference_locators'].append(locator + ':expression=' + expression)
                else:
                    by_code[code] = _metadata(
                        'naics',
                        f'naics{vintage}',
                        code,
                        token,
                        expression,
                        members,
                        nodes,
                        [kind],
                        [locator + ':expression=' + expression],
                    )
                industry[vintage, code] = token
        for code, row in by_code.items():
            if code not in full_industry[vintage]:
                raise ValueError('missing full Census industry support')
            row['reference_ids'].append(f'census_industry_{vintage}')
            row['reference_locators'].append(full_industry[vintage][code][1])
        metadata.extend(by_code.values())
    full = _full_occupation(snapshot)
    if '9920' not in full or full['9920'][0] != 'none':
        raise ValueError('contradictory full Census nonworking occupation reference')
    exclusions.append(
        dict(
            kind='census_occupation_2018',
            code='9920',
            token=None,
            locators=[full['9920'][1]],
            reason='unemployed_no_work_experience',
        )
    )
    highlighted = _occupation_styles(snapshot.files['pums_occupation_2018'])
    primary_rows = _rows(snapshot, 'pums_occupation_2018', 'ACS')
    legend = primary_rows[883][0] if len(primary_rows) >= 884 else None
    if legend != (
        'Highlighting indicates places where detailed Census occupation codes were combined '
        'into one PUMS code for confidentiality reasons, including because the category '
        'contained fewer than 10,000 people nationwide.'
    ):
        raise ValueError('missing or contradictory occupation highlighting legend')
    occupations, rejected_occupation = {}, []
    for kind, sheet in [
        ('pums_occupation_2018', 'ACS'),
        ('pums_annual_2024', 'Occupation'),
        ('pums_five_year_2024', 'OCCP & SOCP'),
    ]:
        for code, token, expressions, locators in _occupation_rows(
            snapshot, kind, sheet, full, rejected_occupation
        ):
            if code == '9920':
                if token != '999920' or expressions != ['999920']:
                    raise ValueError('contradictory nonworking reference category')
                exclusions.append(
                    dict(
                        kind=kind,
                        code=code,
                        token=token,
                        locators=locators,
                        reason='unemployed_no_work_experience',
                    )
                )
                continue
            special = (
                'military_rank_not_specified' if (code, token) == ('9830', '559830') else None
            )
            if special:
                members = []
            else:
                members = sorted(
                    set().union(
                        *[set(parse_membership_expression(e, soc, paths)) for e in expressions]
                    )
                )
            existing = occupations.get(code)
            if existing:
                if (
                    existing['source_token'] != token
                    or existing['native_finest_candidates'] != members
                ):
                    raise ValueError('contradictory paired occupation authority')
                existing['reference_ids'].append(kind)
                existing['reference_locators'].extend(locators)
                continue
            reasons = []
            source_row = int(locators[0].split('row=')[1].split(':')[0])
            if re.search('[XY]', token) or len(expressions) > 1:
                if source_row in highlighted:
                    reasons = ['disclosure']
                elif code in full and full[code][0] == token and re.search('[XY]', token):
                    reasons = ['category_design']
            ids = [kind, 'census_occupation_2018']
            if special:
                ids += ['pums_annual_guide', 'pums_five_year_guide']
                locators += [
                    'pums_annual_guide:physical-page=17:VIII.I:SOCP=559830',
                    'pums_five_year_guide:physical-page=18:VIII.I:SOCP=559830',
                ]
            if reasons == ['disclosure']:
                locators += [
                    'pums_occupation_2018:ACS!A884:highlighting-confidentiality',
                    f'pums_occupation_2018:xl/styles.xml:ACS-row={source_row}:theme7-tint',
                ]
            occupations[code] = _metadata(
                'soc',
                'soc2018',
                code,
                token,
                ','.join(expressions),
                members,
                soc,
                ids,
                locators,
                reasons,
                special,
            )
    occupation_pair_locators = _validate_occ_pairs(
        snapshot, {(code, row['source_token']) for code, row in occupations.items()}, exclusions
    )
    for code, row in occupations.items():
        row['reference_ids'].extend(
            ['soc_tokens_html', 'usa_occsoc', 'ipums_occ_pairs', 'occupation_pairs_html']
        )
        row['reference_locators'].extend(
            [
                'soc_tokens_html:aggregate-code-explanation',
                'usa_occsoc:description:aggregate-code-explanation',
            ]
        )
        row['reference_locators'].extend(
            occupation_pair_locators.get((code, row['source_token']), [])
        )
    metadata.extend(occupations.values())
    rows = []
    for row in metadata:
        if row['system'] == 'naics':
            row['reference_ids'].append('industry_tokens_html')
            row['reference_locators'].append('industry_tokens_html:Legend:M,P,S,Z')
            locators = token_locators[row['native_vintage']].get(row['source_token'], [])
            if locators:
                row['reference_ids'].append('ipums_ind_tokens')
                row['reference_locators'].extend(locators)
        native_table = 'naics_native_nodes' if row['system'] == 'naics' else 'soc_nodes'
        row['reference_ids'].append(f'stage4_codes:{selected.request.codes_run}')
        row['reference_locators'].extend(
            f'stage4_codes:{name}.parquet:sha256='
            + selected.provenance['codes']['tables'][name]['sha256']
            for name in (native_table, 'code_paths')
        )
        for field in ('reference_ids', 'reference_locators'):
            row[field] = sorted(set(row[field]))
        for member in row['native_finest_candidates']:
            rows.append(
                {
                    **{
                        name: row[name]
                        for name in MEMBERSHIP_SCHEMA
                        if name not in ('native_finest_code', 'native_node_id')
                    },
                    'native_finest_code': member,
                    'native_node_id': row['native_node_id'],
                }
            )
    return CodeEvidence(
        pl.DataFrame(rows, schema=MEMBERSHIP_SCHEMA).sort(*KEY, 'native_finest_code'),
        pl.DataFrame(metadata, schema=METADATA_SCHEMA).sort(KEY),
        {
            'rejected_industry_assertions': _industry_diagnostics(
                snapshot, industry, legacy_industry, exclusions
            ),
            'excluded_nonworking': exclusions,
            'rejected_occupation_assertions': rejected_occupation,
        },
    )


def validate_paired_keys(observed: pl.DataFrame, evidence: CodeEvidence) -> None:
    '''Demand exact lexical pair evidence; aggregate references do not waive a mismatch.'''
    if not set(KEY).issubset(observed.columns):
        raise ValueError('observed paired key fields absent')
    if any(observed.schema[name] != pl.String for name in KEY):
        raise ValueError('observed paired keys require lexical String fields')
    nonmissing = observed.select(KEY).filter(pl.col('source_token').is_not_null())
    if nonmissing.select(pl.any_horizontal(pl.all().is_null()).any()).item():
        raise ValueError('nonmissing token has incomplete paired key')
    if nonmissing.join(evidence.metadata.select(KEY), on=KEY, how='anti').height:
        raise ValueError('observed official paired key mismatch')
