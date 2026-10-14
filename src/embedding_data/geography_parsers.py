import csv
import io
import re
from pathlib import Path
from zipfile import ZipFile

import polars as pl

SCOPE = frozenset('01 02 04 05 06 08 09 10 11 12 13 15 16 17 18 19 20 21 22 '
                  '23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 '
                  '42 44 45 46 47 48 49 50 51 53 54 55 56'.split())
EXCLUDED = frozenset('60 64 66 68 69 70 72 74 78'.split())
STATE_SCHEMA = {c: pl.String for c in ['state_fips', 'state_title', 'division_code',
                                     'region_code']}
DIVISION_SCHEMA = {c: pl.String for c in ['division_code', 'division_title', 'region_code']}
REGION_SCHEMA = {c: pl.String for c in ['region_code', 'region_title']}
COUNTY_SCHEMA = {c: pl.String for c in ['county_geoid', 'county_title', 'state_fips',
                                      'state_usps']}
MEMBER_SCHEMA = {c: pl.String for c in ['county_geoid', 'state_fips', 'cbsa_code',
                                      'cbsa_title', 'cbsa_type', 'cbsa_role']}
STATE_HEADER = ('Region', 'Division', 'State (FIPS)', 'Name')
MEMBER_HEADER = ('CBSA Code', 'Metropolitan Division Code', 'CSA Code', 'CBSA Title',
                 'Metropolitan/Micropolitan Statistical Area', 'Metropolitan Division Title',
                 'CSA Title', 'County/County Equivalent', 'State Name', 'FIPS State Code',
                 'FIPS County Code', 'Central/Outlying County')
CBSA_FOOTERS = (
    "Note: The Office of Management and Budget's (OMB's) 2020 Standards for Delineating "
    'Core Based Statistical Areas are at <https://www.federalregister.gov/documents/'
    '2021/07/16/2021-15159/2020-standards-for-delineating-core-based-statistical-areas>.',
    'Source: File prepared by U.S. Census Bureau, Population Division, based on OMB, '
    'July 2023 delineations <https://www.whitehouse.gov/wp-content/uploads/2023/07/'
    'OMB-Bulletin-23-01.pdf>.',
)


def text(value):
    return '' if value is None else str(value).strip()


def code(value, width, label):
    value = text(value)
    if not re.fullmatch(r'[0-9]{' + str(width) + '}', value):
        raise ValueError(f'{label}: expected {width} ASCII digits, received {value!r}')
    return value


def title(value, label):
    value = text(value)
    if not value:
        raise ValueError(f'{label}: missing title')
    return value


def body(raw, header):
    rows = [tuple(text(x) for x in row) for row in raw.rows()]
    hits = [i for i, row in enumerate(rows) if row == header]
    if len(hits) != 1:
        raise ValueError('missing or ambiguous exact reference header')
    return [row for row in rows[hits[0] + 1:] if any(row)]


def frame(rows, schema, key):
    result = pl.DataFrame(rows, schema=schema, orient='row')
    if result.is_empty() or result[key].n_unique() != result.height:
        raise ValueError(f'empty or duplicate {key}')
    return result.sort(key)


def parse_states(raw: pl.DataFrame, *, scope=SCOPE) -> dict[str, pl.DataFrame]:
    regions, divisions, states, excluded = [], [], [], []
    for r, d, s, name in body(raw, STATE_HEADER):
        r, d, s = code(r, 1, 'region'), code(d, 1, 'division'), code(s, 2, 'state')
        name = title(name, 'state/region/division')
        if s in EXCLUDED:
            excluded.append((s, name, d, r))
        elif s == '00' and r in '1234' and d == '0':
            regions.append((r, name))
        elif s == '00' and r in '1234' and d in '123456789':
            divisions.append((d, name, r))
        elif s in scope and r in '1234' and d in '123456789':
            states.append((s, name, d, r))
        else:
            raise ValueError('unsupported or contradictory administrative row')
    result = {'regions': frame(regions, REGION_SCHEMA, 'region_code'),
              'divisions': frame(divisions, DIVISION_SCHEMA, 'division_code'),
              'states': frame(states, STATE_SCHEMA, 'state_fips'),
              'excluded_states': pl.DataFrame(excluded, schema=STATE_SCHEMA, orient='row')}
    if excluded and result['excluded_states']['state_fips'].n_unique() != len(excluded):
        raise ValueError('duplicate excluded state')
    if set(result['states']['state_fips']) != set(scope):
        raise ValueError('state inventory does not equal the explicit administrative scope')
    region_keys = set(result['regions']['region_code'])
    division_parents = dict(result['divisions'].select('division_code', 'region_code').rows())
    if not set(division_parents.values()).issubset(region_keys):
        raise ValueError('division has no region reference')
    for s, name, d, r in states:
        if division_parents.get(d) != r:
            raise ValueError('state division/region relationships disagree')
    return result


def parse_counties(file: Path) -> pl.DataFrame:
    member = '2025_Gaz_counties_national.txt'
    with ZipFile(file) as archive:
        if archive.namelist() != [member]:
            raise ValueError('county archive must contain exactly the registered text member')
        contents = archive.read(member).decode('utf-8-sig')
    reader = csv.reader(io.StringIO(contents), delimiter='|')
    header = [text(x) for x in next(reader, [])]
    if len(header) != len(set(header)) or not {'USPS', 'GEOID', 'NAME'}.issubset(header):
        raise ValueError('missing or ambiguous county header')
    rows = []
    for values in reader:
        if not any(text(x) for x in values):
            continue
        if len(values) != len(header):
            raise ValueError('malformed county row width')
        row = dict(zip(header, values, strict=True))
        geoid = code(row['GEOID'], 5, 'county GEOID')
        usps = text(row['USPS'])
        if not re.fullmatch('[A-Z]{2}', usps) or geoid[:2] not in SCOPE | EXCLUDED:
            raise ValueError('unrecognized county state/USPS syntax')
        rows.append((geoid, title(row['NAME'], 'county'), geoid[:2], usps))
    result = frame(rows, COUNTY_SCHEMA, 'county_geoid')
    pairs = result.select('state_fips', 'state_usps').unique()
    if (pairs['state_fips'].n_unique() != pairs.height
            or pairs['state_usps'].n_unique() != pairs.height):
        raise ValueError('Gazetteer FIPS/USPS pairs are not one-to-one')
    return result


def parse_members(raw: pl.DataFrame) -> pl.DataFrame:
    types = {'Metropolitan Statistical Area': 'metropolitan',
             'Micropolitan Statistical Area': 'micropolitan'}
    roles = {'Central': 'central', 'Outlying': 'outlying'}
    rows = []
    for row in body(raw, MEMBER_HEADER):
        if row[0] in CBSA_FOOTERS and not any(row[1:]):
            continue
        cbsa = code(row[0], 5, 'CBSA')
        state, county = code(row[9], 2, 'membership state'), code(row[10], 3, 'membership county')
        if state not in SCOPE | EXCLUDED or row[4] not in types or row[11] not in roles:
            raise ValueError('unsupported CBSA type, role or state')
        title(row[7], 'member county')
        title(row[8], 'member state')
        rows.append((state + county, state, cbsa, title(row[3], 'CBSA'),
                     types[row[4]], roles[row[11]]))
    result = frame(rows, MEMBER_SCHEMA, 'county_geoid')
    descriptions = result.select('cbsa_code', 'cbsa_title', 'cbsa_type').unique()
    if descriptions['cbsa_code'].n_unique() != descriptions.height:
        raise ValueError('CBSA title/type contradicts another membership')
    return result
