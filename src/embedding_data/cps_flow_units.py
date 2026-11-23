'''Category units for CPS job flows: candidates, X residuals, the PUMS cross-check, the registry.

Every Census industry and occupation list row becomes one unit, with the two specials added.
An industry row takes its candidates from its NAICS expression and an occupation row from its
SOC token. An X token takes the detailed codes that no other row claims. The Stage 8 PUMS
lists only check those residuals and never supply members.
'''

import re
from pathlib import Path

import polars as pl

from embedding_data.cps_flow_lists import ListRow, membership_types, naics_candidates
from embedding_data.cps_flow_references import INDUSTRY_SPECIAL, OCCUPATION_SPECIAL

X_TOKEN = re.compile(r'\d{2}-(?:\d{3}X|\d{2}XX|\dXXX)')
NO_SOC = 'none'
FINEST_LEVELS = {'industry': ['national_industry'], 'occupation': ['detailed']}
UNIT_TYPES = {'industry': 'cps_industry_category', 'occupation': 'cps_occupation_category'}
VINTAGES = {'industry': 'census-industry-2022', 'occupation': 'census-occupation-2018'}
SPECIALS = {'industry': INDUSTRY_SPECIAL, 'occupation': OCCUPATION_SPECIAL}
SPECIAL_LOCATORS = {
    'industry': 'cps_basic_2026_industry_codes', 'occupation': 'cps_basic_2026_occupation_codes'}
STRING, STRINGS = pl.String, pl.List(pl.String)
UNIT_SCHEMA = {
    'unit': STRING, 'unit_type': STRING, 'code': STRING, 'vintage': STRING, 'label': STRING,
    'status': STRING, 'source_expression': STRING, 'membership_types': STRINGS,
    'candidates': STRINGS, 'candidate_node_ids': STRINGS, 'x_token': STRING,
    'x_cross_check': STRING, 'evidence_monthly': STRING, 'evidence_asec_current': STRING,
    'evidence_asec_last_year': STRING, 'bls_evidence': STRING, 'list_locator': STRING,
    'pums_locator': STRING, 'reference_id': STRING}


def soc_candidates(token: str, soc_nodes: pl.DataFrame, paths: pl.DataFrame) -> list[str]:
    '''Return the detailed descendants of the node with this code, at any level, sorted.'''
    matched = soc_nodes.filter(pl.col('code') == token)
    if matched.height != 1:
        raise ValueError(f'unknown SOC code: {token}')
    below = paths.filter(pl.col('path').list.contains(matched['node_id'][0]))['node_id']
    members = soc_nodes.filter(
        pl.col('level').eq('detailed') & pl.col('node_id').is_in(below.implode()))
    if members.is_empty():
        raise ValueError(f'SOC code has no detailed members: {token}')
    return sorted(members['code'])


def x_matches(token: str, detailed_codes: list[str]) -> list[str]:
    '''Return the detailed codes that match the token, with each `X` standing for one digit.'''
    if not X_TOKEN.fullmatch(token):
        raise ValueError(f'unsupported X token: {token}')
    pattern = re.compile(token.replace('X', r'\d'))
    return sorted(code for code in detailed_codes if pattern.fullmatch(code))


def _is_x(row: ListRow) -> bool:
    return row.expression is not None and 'X' in row.expression


def _non_x_claims(rows: list[ListRow], soc_nodes, paths) -> set[str]:
    claims: set[str] = set()
    for row in rows:
        if row.expression not in (None, NO_SOC) and not _is_x(row):
            claims.update(soc_candidates(row.expression, soc_nodes, paths))
    return claims


def x_residuals(rows: list[ListRow], soc_nodes, paths) -> dict[str, list[str]]:
    '''Return each X row's residual, keyed by Census code.

    The rows go from the most fixed digits to the fewest, then by token and code. A residual
    is the token's matches minus every detailed code that a non-X row claims and minus every
    earlier residual.
    '''
    detailed = list(soc_nodes.filter(pl.col('level') == 'detailed')['code'])
    taken = _non_x_claims(rows, soc_nodes, paths)
    residuals: dict[str, list[str]] = {}
    ordered = sorted((row for row in rows if _is_x(row)),
                     key=lambda row: (-sum(c.isdigit() for c in row.expression),
                                      row.expression, row.code))
    for row in ordered:
        residuals[row.code] = [code for code in x_matches(row.expression, detailed)
                               if code not in taken]
        taken.update(residuals[row.code])
    return residuals


def read_pums_lists(lookup_file: Path) -> dict[str, tuple[list[str], str]]:
    '''Return each SOC row of the Stage 8 code lookup: Census code to (candidates, locators).'''
    frame = pl.read_parquet(lookup_file, columns=[
        'system', 'paired_census_code', 'canonical_finest_candidates', 'reference_locators'])
    lists: dict[str, tuple[list[str], str]] = {}
    for row in frame.filter(pl.col('system') == 'soc').iter_rows(named=True):
        code = row['paired_census_code']
        if code in lists:
            raise ValueError(f'PUMS list repeats Census code {code}')
        lists[code] = (list(row['canonical_finest_candidates']),
                       '|'.join(row['reference_locators']))
    return lists


def cross_check(residuals: dict[str, list[str]], pums: dict[str, list[str]],
                claimed_elsewhere: dict[str, set[str]], delivered: set[str]) -> dict[str, str]:
    '''Compare each residual with its PUMS list and return `equal`, `strict_subset` or
    `not_delivered_no_pums_list`, or fail with a fixed reason.'''
    outcomes: dict[str, str] = {}
    for code, residual in sorted(residuals.items()):
        if not residual:
            raise ValueError('x residual is empty')
        if code not in pums:
            if code in delivered:
                raise ValueError('x category has no PUMS list')
            outcomes[code] = 'not_delivered_no_pums_list'
            continue
        if not set(residual) <= set(pums[code]):
            raise ValueError('x residual is not within the PUMS list')
        extra = set(pums[code]) - set(residual)
        if not extra <= claimed_elsewhere.get(code, set()):
            raise ValueError('x PUMS extra member is not claimed by another row')
        outcomes[code] = 'strict_subset' if extra else 'equal'
    return outcomes


def _check_codes(rows: list[ListRow], dimension: str) -> None:
    codes = [row.code for row in rows]
    if len(set(codes)) != len(codes) or SPECIALS[dimension] in codes:
        raise ValueError(f'the {dimension} list repeats a code or carries its special')


def _node_ids(candidates: list[str], nodes: pl.DataFrame, dimension: str) -> list[str]:
    finest = nodes.filter(pl.col('level').is_in(FINEST_LEVELS[dimension]))
    ids = dict(zip(finest['code'], finest['node_id']))
    if not all(code in ids for code in candidates):
        raise ValueError('candidate is not a Stage 4 node')
    return [ids[code] for code in candidates]


def _refuse_delivered(row: ListRow, delivered: set[str]) -> None:
    if row.code in delivered:
        raise ValueError('delivered code has no equivalent')


def _unit(dimension: str, row: ListRow, reference_id: str, **fields) -> dict:
    unit = dict.fromkeys(UNIT_SCHEMA)
    unit.update(
        unit=f'feature:{UNIT_TYPES[dimension]}:{row.code}', unit_type=UNIT_TYPES[dimension],
        code=row.code, vintage=VINTAGES[dimension], label=row.title,
        source_expression=row.expression, membership_types=[], candidates=[],
        candidate_node_ids=[], list_locator=row.locator, reference_id=reference_id)
    unit.update(fields)
    return unit


def _special(dimension: str, evidence: dict, reference_id: str) -> dict:
    code, found = SPECIALS[dimension], evidence[SPECIALS[dimension]]
    row = ListRow(code, found['label'], None, f'{SPECIAL_LOCATORS[dimension]}:{code}')
    return _unit(dimension, row, reference_id, status='special_military',
                 evidence_monthly=found['monthly'], evidence_asec_current=found['asec_current'],
                 evidence_asec_last_year=found['asec_last_year'], bls_evidence=found['bls'])


def build_units(industry: list[ListRow], occupation: list[ListRow], *, naics_nodes, soc_nodes,
                paths, pums: dict, delivered: dict[str, set[str]], evidence: dict[str, dict],
                references: dict[str, str]) -> pl.DataFrame:
    '''Return the `cps_category_units` frame: one row per list row and the two specials.

    `pums` is `read_pums_lists` output. `delivered` holds the delivered codes by dimension.
    A delivered code with no NAICS or SOC equivalent fails, as does a failed X cross-check.
    '''
    _check_codes(industry, 'industry')
    _check_codes(occupation, 'occupation')
    residuals = x_residuals(occupation, soc_nodes, paths)
    taken = _non_x_claims(occupation, soc_nodes, paths)
    claimed = {code: taken.union(*(other for name, other in residuals.items() if name != code))
               for code in residuals}
    outcomes = cross_check(residuals, {code: found[0] for code, found in pums.items()}, claimed,
                           delivered['occupation'])
    soc_levels = dict(zip(soc_nodes['code'], soc_nodes['level']))
    units = [_special('industry', evidence, references['special']),
             _special('occupation', evidence, references['special'])]
    for row in industry:
        if row.expression is None:
            _refuse_delivered(row, delivered['industry'])
            fields = dict(status='no_naics_equivalent')
        else:
            candidates = naics_candidates(row.expression, naics_nodes, paths)
            fields = dict(
                status='mapped', candidates=candidates,
                membership_types=membership_types(row.expression, naics_nodes),
                candidate_node_ids=_node_ids(candidates, naics_nodes, 'industry'))
        units.append(_unit('industry', row, references['industry'], **fields))
    for row in occupation:
        if row.expression == NO_SOC:
            _refuse_delivered(row, delivered['occupation'])
            fields = dict(status='no_soc_equivalent')
        elif _is_x(row):
            candidates = residuals[row.code]
            fields = dict(
                status='mapped', candidates=candidates, membership_types=['x_residual'],
                candidate_node_ids=_node_ids(candidates, soc_nodes, 'occupation'),
                x_token=row.expression, x_cross_check=outcomes[row.code],
                pums_locator=pums[row.code][1] if row.code in pums else None)
        else:
            candidates = soc_candidates(row.expression, soc_nodes, paths)
            kind = 'whole' if soc_levels[row.expression] == 'detailed' else 'group'
            fields = dict(
                status='mapped', candidates=candidates, membership_types=[kind],
                candidate_node_ids=_node_ids(candidates, soc_nodes, 'occupation'))
        units.append(_unit('occupation', row, references['occupation'], **fields))
    return pl.DataFrame(units, schema=UNIT_SCHEMA).sort('unit_type', 'code')
