'''Census 2020 CT block population evidence for the separately versioned D9 basis.'''
import csv
import io
import re
import stat
import struct
from collections import defaultdict
from dataclasses import dataclass
from html.parser import HTMLParser
from zipfile import BadZipFile, ZipFile

import fastexcel

CT_STATE_POPULATION = 3605944
CT_ORIGINAL_LIMITS = {
    'ct_tabblock2020': 64 * 1024 * 1024,
    'ct_block_assignment2020': 2 * 1024 * 1024,
    'ct_county_crosswalk': 32 * 1024,
    'tract_puma2020': 2 * 1024 * 1024,
    'census_puma_population2020': 2 * 1024 * 1024,
    'census_ct_mcd_population2020': 256 * 1024,
    'ct_opm_population2020': 32 * 1024,
}
DBF_FIELDS = (
    ('STATEFP20', 'C', 2, 0), ('COUNTYFP20', 'C', 3, 0), ('TRACTCE20', 'C', 6, 0),
    ('BLOCKCE20', 'C', 4, 0), ('GEOID20', 'C', 15, 0), ('NAME20', 'C', 10, 0),
    ('MTFCC20', 'C', 5, 0), ('UR20', 'C', 5, 0), ('UACE20', 'C', 5, 0),
    ('UATYPE20', 'C', 5, 0), ('FUNCSTAT20', 'C', 1, 0), ('ALAND20', 'N', 14, 0),
    ('AWATER20', 'N', 14, 0), ('INTPTLAT20', 'C', 11, 0), ('INTPTLON20', 'C', 12, 0),
    ('HOUSING20', 'N', 12, 0), ('POP20', 'N', 12, 0),
)
TIGER_MEMBERS = {f'tl_2020_09_tabblock20.{suffix}' for suffix in (
    'cpg', 'dbf', 'prj', 'shp', 'shp.ea.iso.xml', 'shx', 'shp.iso.xml')}
BAF_MEMBERS = {f'BlockAssign_ST09_CT_{suffix}.txt' for suffix in (
    'INCPLACE_CDP', 'AIANNH', 'VTD', 'MCD', 'CD', 'SLDL', 'SDSEC', 'SLDU', 'SDELM', 'SDUNI')}
REGION_NAMES = {
    'Capitol': ('09110', 'Capitol'), 'Greater Bridgeport': ('09120', 'Greater Bridgeport'),
    'Lower Connecticut River Valley': ('09130', 'Lower CT River Valley'),
    'Naugatuck Valley': ('09140', 'Naugatuck Valley'),
    'Northeastern Connecticut': ('09150', 'Northeast CT'),
    'Northwest Hills': ('09160', 'Northwest Hills'),
    'South Central Connecticut': ('09170', 'South Central'),
    'Southeastern Connecticut': ('09180', 'Southeastern CT'),
    'Western Connecticut': ('09190', 'Western CT'),
}
SUMMARY_NAMES = {name: code for code, name in REGION_NAMES.values()}
SUMMARY_NAMES['Northeastern CT'] = SUMMARY_NAMES.pop('Northeast CT')
PUMA_HEADERS = ('MTFCC OID GEOID STATE PUMA BASENAME NAME LSADC FUNCSTAT POP100 HU100 '
                'AREALAND AREAWATER CENTLAT CENTLON INTPTLAT INTPTLON').split()
MCD_HEADERS = ('MTFCC OID GEOID STATE COUNTY COUSUB COUSUBNS BASENAME NAME LSADC FUNCSTAT '
               'COUSUBCC POP100 HU100 AREALAND AREAWATER UR CNECTA NECTA NECTADIV '
               'CENTLAT CENTLON INTPTLAT INTPTLON').split()
CROSSWALK_HEADERS = ('STATEFP (INCITS38)|OLD_COUNTYFP (INCITS31)|OLD_COUNTY_NAMELSAD|'
                     'NEW_COUNTYFP (INCITS31)|NEW_COUNTY_NAMELSAD|COUSUBFP|OLD_COUSUB_GEOID|'
                     'NEW_COUSUB_GEOID|COUSUB_NAMELSAD|COUSUBNS (INCITS446)|COUSUB_LSAD|'
                     'COUSUB_FUNCSTAT|COUSUB_CLASSFP').split('|')


@dataclass(frozen=True)
class CTPopulation:
    relations: list[dict]
    puma_totals: dict[str, int]
    county_totals: dict[str, int]
    national_puma_totals: dict[tuple[str, str], int]
    diagnostics: dict


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _code(value, width):
    _require(isinstance(value, str) and re.fullmatch('[0-9]{' + str(width) + '}', value),
             'malformed CT geographic key')
    return value


def _population(value):
    _require(isinstance(value, str) and re.fullmatch('[0-9]+', value),
             'invalid unsigned integer CT population')
    return int(value)


def archive_members(file, *, tiger):
    '''Validate the entire directory before reading a bounded member; never extract.'''
    expected, cap, compression = ((TIGER_MEMBERS, 64 * 1024 * 1024, 0) if tiger else
                                  (BAF_MEMBERS, 2 * 1024 * 1024, 8))
    _require(0 < file.stat().st_size <= cap, 'CT archive byte bound differs')
    try:
        with ZipFile(file) as archive:
            entries = archive.infolist()
            _require(len(entries) == len(expected) and {m.filename for m in entries} == expected,
                     'CT archive member inventory differs')
            for member in entries:
                mode = member.external_attr >> 16
                _require('/' not in member.filename and '\\' not in member.filename
                         and not member.is_dir() and not stat.S_ISLNK(mode)
                         and (not stat.S_IFMT(mode) or stat.S_ISREG(mode))
                         and not member.flag_bits & 1 and member.compress_type == compression
                         and 0 < member.file_size <= (56 * 1024 * 1024 if tiger else
                                                     2 * 1024 * 1024)
                         and 0 < member.compress_size <= member.file_size + 1024,
                         'unsafe/malformed CT archive member')
            selected = ['tl_2020_09_tabblock20.dbf', 'tl_2020_09_tabblock20.cpg'] if tiger else [
                'BlockAssign_ST09_CT_MCD.txt']
            _require(all(archive.getinfo(n).file_size <= 8 * 1024 * 1024 for n in selected),
                     'CT selected archive member exceeds byte bound')
            return {name: archive.read(name) for name in selected}
    except (BadZipFile, OSError, RuntimeError) as error:
        raise ValueError('malformed CT ZIP original') from error


def block_populations(file):
    members = archive_members(file, tiger=True)
    _require(members['tl_2020_09_tabblock20.cpg'] == b'UTF-8', 'CT DBF encoding differs')
    body = members['tl_2020_09_tabblock20.dbf']
    _require(len(body) >= 578 and body[0] == 3 and body[29] == 0, 'CT DBF header differs')
    count, header, length = struct.unpack_from('<IHH', body, 4)
    _require(count == 49926 and header == 577 and length == 137
             and len(body) == header + count * length + 1
             and body[header - 1] == 13 and body[-1] == 26, 'CT DBF physical length differs')
    descriptors = []
    for start in range(32, header - 1, 32):
        field = body[start:start + 32]
        descriptors.append((field[:11].split(b'\0')[0].decode('ascii'), chr(field[11]),
                            field[16], field[17]))
    _require(tuple(descriptors) == DBF_FIELDS, 'CT DBF field descriptors differ')
    result = {}
    for number in range(count):
        record = body[header + number * length:header + (number + 1) * length]
        _require(record[:1] == b' ', 'deleted or malformed CT DBF record')
        values, offset = {}, 1
        for name, _, width, _ in DBF_FIELDS:
            if name in {'STATEFP20', 'COUNTYFP20', 'TRACTCE20', 'BLOCKCE20', 'GEOID20', 'POP20'}:
                values[name] = record[offset:offset + width].decode('ascii').strip(' ')
            offset += width
        state, county, tract, block, geoid = (
            _code(values[k], n) for k, n in [('STATEFP20', 2), ('COUNTYFP20', 3),
                                           ('TRACTCE20', 6), ('BLOCKCE20', 4), ('GEOID20', 15)])
        _require(state == '09' and geoid == state + county + tract + block and geoid not in result,
                 'duplicate or contradictory CT block key')
        result[geoid] = (_population(values['POP20']), number + 1)
    return result


def _csv(body, headers, delimiter=','):
    reader = csv.DictReader(io.StringIO(body.decode('utf-8-sig'), newline=''),
                            delimiter=delimiter, strict=True)
    _require([h.replace('\n', ' ').strip() for h in reader.fieldnames] == headers,
             'CT original CSV header differs')
    rows = []
    for number, row in enumerate(reader, 2):
        _require(None not in row, 'CT CSV row width differs')
        rows.append(({k.replace('\n', ' ').strip(): v for k, v in row.items()}, number))
    return rows


def block_towns(file):
    body = archive_members(file, tiger=False)['BlockAssign_ST09_CT_MCD.txt']
    result = {}
    for row, number in _csv(body, ['BLOCKID', 'COUNTYFP', 'COUSUBFP'], '|'):
        key = _code(row['BLOCKID'], 15)
        county, town = _code(row['COUNTYFP'], 3), _code(row['COUSUBFP'], 5)
        _require(key.startswith('09' + county) and key not in result,
                 'duplicate/contradictory CT BAF block key')
        result[key] = ('09' + county + town, number)
    _require(len(result) == 49926, 'CT BAF coverage differs')
    return result


def tract_pumas(file):
    result = {}
    for row, number in _csv(file.read_bytes(), ['STATEFP', 'COUNTYFP', 'TRACTCE', 'PUMA5CE']):
        key = _code(row['STATEFP'], 2) + _code(row['COUNTYFP'], 3) + _code(row['TRACTCE'], 6)
        _require(key not in result, 'duplicate tract/PUMA key')
        result[key] = (_code(row['PUMA5CE'], 5), number)
    _require(len(result) == 85452 and sum(k.startswith('09') for k in result) == 883,
             'complete national tract/PUMA coverage differs')
    return result


def town_regions(file):
    rows = _csv(file.read_bytes(), CROSSWALK_HEADERS, '|')
    result, glossary = defaultdict(list), []
    for row, number in rows:
        if row['STATEFP (INCITS38)'] != '09':
            _require(all(v is None for k, v in row.items() if k != 'STATEFP (INCITS38)'),
                     'unexpected CT crosswalk glossary/body row')
            glossary.append(row['STATEFP (INCITS38)'])
            continue
        _require(not glossary, 'CT crosswalk body follows glossary')
        old = '09' + _code(row['OLD_COUNTYFP (INCITS31)'], 3) + _code(row['COUSUBFP'], 5)
        new = '09' + _code(row['NEW_COUNTYFP (INCITS31)'], 3)
        _require(row['OLD_COUSUB_GEOID'] == old and row['NEW_COUSUB_GEOID'] ==
                 new + row['COUSUBFP'], 'CT crosswalk component key differs')
        label = row['NEW_COUNTY_NAMELSAD'].removesuffix(' Planning Region')
        _require(label in REGION_NAMES and REGION_NAMES[label][0] == new,
                 'CT crosswalk region identity differs')
        _require(not any(r[0] == new for r in result[old]), 'duplicate CT crosswalk relation')
        result[old].append((new, REGION_NAMES[label][1], number))
    _require(len(glossary) == 9 and glossary[0] == 'GLOSSARY', 'CT glossary differs')
    _require(len(result) == 173 and sum(len(v) for v in result.values()) == 174,
             'CT crosswalk coverage differs')
    return dict(result)


class _ControlRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.cell = [], None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.rows.append([])
        if tag in ('td', 'th'):
            self.cell = ''

    def handle_data(self, value):
        if self.cell is not None:
            self.cell += value

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.rows[-1].append(self.cell.strip())
            self.cell = None


def census_controls(file, *, puma):
    parser = _ControlRows()
    parser.feed(file.read_text(encoding='utf-8'))
    headers = PUMA_HEADERS if puma else MCD_HEADERS
    _require(parser.rows[0] == headers, 'Census population control header differs')
    result = {}
    for number, values in enumerate(parser.rows[1:], 2):
        _require(len(values) == len(headers), 'Census population control width differs')
        row = dict(zip(headers, values, strict=True))
        state, key = _code(row['STATE'], 2), _code(row['GEOID'], 7 if puma else 10)
        components = state + (_code(row['PUMA'], 5) if puma else
                              _code(row['COUNTY'], 3) + _code(row['COUSUB'], 5))
        _require(key == components and key not in result and (puma or state == '09'),
                 'Census control duplicate/contradictory key')
        result[key] = (row, _population(row['POP100']), number)
    _require(len(result) == (2487 if puma else 173), 'Census population control coverage differs')
    return result


def opm_controls(file):
    workbook = fastexcel.read_excel(file.read_bytes())
    _require(workbook.sheet_names == ['Sheet1'], 'OPM worksheet identity differs')
    rows = workbook.load_sheet(0, header_row=None, dtypes='string').to_polars().rows()
    _require(rows[:3] == [(None, '2020 Census Population By Planning Region', None, None, None),
                         (None, None, None, None, None),
                         ('TOWN', 'Planning Region', '2020 Population',
                          'Population by Planning Region', None)], 'OPM header differs')
    towns, summaries = {}, {}
    for number, values in enumerate(rows[3:], 4):
        _require(len(values) == 5, 'OPM column count differs')
        name, region, population, total, summary = values
        if name and region:
            _require(name not in towns, 'duplicate OPM town')
            towns[name] = (region, _population(population), number)
        if total and summary:
            _require(summary in SUMMARY_NAMES and SUMMARY_NAMES[summary] not in summaries,
                     'duplicate/unknown OPM summary')
            summaries[SUMMARY_NAMES[summary]] = _population(total)
    _require(len(towns) == 169 and len(summaries) == 9, 'OPM control coverage differs')
    return towns, summaries


def compact_source_locators(locators):
    groups = defaultdict(set)
    for locator in locators:
        prefix, number = locator.rsplit('=', 1)
        groups[prefix].add(int(number))
    result = []
    for prefix, numbers in sorted(groups.items()):
        ranges = []
        first = last = None
        for number in sorted(numbers):
            if first is None:
                first = last = number
            elif number == last + 1:
                last = number
            else:
                ranges.append(str(first) if first == last else f'{first}-{last}')
                first = last = number
        ranges.append(str(first) if first == last else f'{first}-{last}')
        result.append(prefix + '-ranges=' + ','.join(ranges))
    return result


def read_ct_population(files):
    for kind, limit in CT_ORIGINAL_LIMITS.items():
        _require(0 < files[kind].stat().st_size <= limit, 'CT original byte bound differs')
    blocks = block_populations(files['ct_tabblock2020'])
    baf = block_towns(files['ct_block_assignment2020'])
    tracts = tract_pumas(files['tract_puma2020'])
    crosswalk = town_regions(files['ct_county_crosswalk'])
    _require(set(blocks) == set(baf), 'CT block/BAF key sets differ')
    puma_control = census_controls(files['census_puma_population2020'], puma=True)
    town_control = census_controls(files['census_ct_mcd_population2020'], puma=False)
    opm, summaries = opm_controls(files['ct_opm_population2020'])
    pumas, towns, counties, relations = (defaultdict(int) for _ in range(4))
    exclusions, locators = [], defaultdict(set)
    for block, (population, record) in blocks.items():
        town, baf_row = baf[block]
        towns[town] += population
        _require(block[:11] in tracts, 'CT block has unmatched tract')
        puma, tract_row = tracts[block[:11]]
        targets = crosswalk.get(town, [])
        if len(targets) != 1:
            _require(population == 0 and town == '0900100000'
                     and sorted(t[0] for t in targets) == ['09120', '09190'],
                     'positive or unexplained ambiguous/unmatched CT membership')
            exclusions.append(dict(block=block, population=population, old_town=town,
                                   region_targets=sorted(t[0] for t in targets)))
            continue
        county, _, crosswalk_row = targets[0]
        pumas[puma] += population
        counties[county] += population
        relations[puma, county] += population
        locators[puma, county].update((
            f'ct_tabblock2020:tl_2020_09_tabblock20.dbf:record={record}',
            f'ct_block_assignment2020:BlockAssign_ST09_CT_MCD.txt:row={baf_row}',
            f'tract_puma2020:csv:row={tract_row}',
            f'ct_county_crosswalk:csv:row={crosswalk_row}'))
    _require(len(relations) == 26 and all(v > 0 for v in relations.values())
             and len(exclusions) == 9, 'CT observed relation/zero-exclusion coverage differs')
    official = {k[2:]: v[1] for k, v in puma_control.items() if k.startswith('09')}
    _require(dict(pumas) == official and len(pumas) == 25, 'CT PUMA population controls differ')
    _require(set(towns) <= set(town_control) and all(towns[k] == v[1]
             for k, v in town_control.items()), 'CT MCD population controls differ')
    opm_sums = defaultdict(int)
    for town, (row, population, _) in town_control.items():
        if row['COUSUB'] == '00000':
            _require(population == 0, 'positive pseudo-MCD control')
            continue
        _require(row['BASENAME'] in opm and len(crosswalk[town]) == 1,
                 'OPM control town absent or ambiguous')
        label, observed, _ = opm[row['BASENAME']]
        county, expected_label, _ = crosswalk[town][0]
        _require(population == observed and label == expected_label, 'OPM town control differs')
        opm_sums[county] += observed
    _require(dict(counties) == dict(opm_sums) == summaries and sum(pumas.values()) ==
             sum(pop for pop, _ in blocks.values()) == CT_STATE_POPULATION,
             'CT independent region/state controls differ')
    excluded = [{'state_fips': k[:2], 'puma_code': k[2:], 'population': v[1]}
                for k, v in puma_control.items() if k.startswith('66')]
    _require(excluded == [{'state_fips': '66', 'puma_code': '00100', 'population': 153836}],
             'Census extra-universe PUMA control differs')
    national = {(k[:2], k[2:]): v[1] for k, v in puma_control.items() if not k.startswith('66')}
    return CTPopulation(
        [dict(state_fips='09', puma_code=p, county_geoid=c, population=n,
              reference_locators=compact_source_locators(locators[p, c]))
         for (p, c), n in sorted(relations.items())], dict(pumas), dict(counties), national,
        dict(block_records=len(blocks), zero_population_exclusions=sorted(exclusions,
             key=lambda r: r['block']), mcd_controls=len(town_control), opm_towns=len(opm),
             national_puma_keys=len(national), excluded_puma_controls=excluded,
             puma_marginals=dict(pumas), county_marginals=dict(counties),
             mcd_marginals={k: towns[k] for k in sorted(town_control)},
             state_population=sum(pumas.values()), accepted_basis='Census 2020 block POP20'))


def validate_ct_original(kind, file):
    '''Validate each complete original at import as well as the later joined boundary.'''
    _require(kind in CT_ORIGINAL_LIMITS and
             0 < file.stat().st_size <= CT_ORIGINAL_LIMITS[kind], 'CT original byte bound differs')
    readers = {
        'ct_tabblock2020': block_populations,
        'ct_block_assignment2020': block_towns,
        'ct_county_crosswalk': town_regions,
        'tract_puma2020': tract_pumas,
        'ct_opm_population2020': opm_controls,
    }
    if kind in readers:
        readers[kind](file)
    elif kind in {'census_puma_population2020', 'census_ct_mcd_population2020'}:
        census_controls(file, puma=kind == 'census_puma_population2020')
    else:
        raise ValueError('unknown CT original kind')


def replace_geocorr_basis(ct, intersections, puma_totals, county_totals, reference_id,
                          *, original_literals=None):
    '''Replace CT integer evidence only; published fields keep their rejected old basis.'''
    original_pumas = {(r['state_fips'], r['puma_code']): r['population'] for r in puma_totals}
    original_counties = {r['county_geoid']: r['population'] for r in county_totals}
    _require(len(original_pumas) == len(puma_totals)
             and len(original_counties) == len(county_totals),
             'original Geocorr control keys duplicate')
    seen, puma_sums, county_sums = set(), defaultdict(int), defaultdict(int)
    for row in intersections:
        key = row['state_fips'], row['puma_code'], row['county_geoid']
        _require(key not in seen, 'original Geocorr intersection key duplicates')
        seen.add(key)
        puma_sums[key[:2]] += row['intersection_population']
        county_sums[key[2]] += row['intersection_population']
    _require(dict(puma_sums) == original_pumas and dict(county_sums) == original_counties
             and all(n > 0 for n in (*original_pumas.values(), *original_counties.values())),
             'original Geocorr integer controls differ before CT replacement')
    _require(set(original_pumas) == set(ct.national_puma_totals) and all(
        population == ct.national_puma_totals[key] for key, population in original_pumas.items()
        if key[0] != '09'), 'independent national PUMA/non-CT control differs')
    old = {(r['puma_code'], r['county_geoid']): r for r in intersections
           if r['state_fips'] == '09'}
    accepted = {(r['puma_code'], r['county_geoid']): r for r in ct.relations}
    _require(len(old) == 27 and len(accepted) == 26 and set(accepted) <= set(old),
             'CT new positive key lacks genuine published-field provenance')
    assertions = []
    for (puma, county), row in sorted(old.items()):
        population = accepted[puma, county]['population'] if (puma, county) in accepted else None
        assertion = dict(row, original_area_population=original_pumas['09', puma],
                         original_county_population=original_counties[county],
                         accepted_population=population, disposition='rejected_population_basis',
                         cause='unknown')
        if original_literals is not None:
            assertion['published_literal_tokens'] = original_literals['09', puma, county]
        assertions.append(assertion)
    rows = []
    kinds = ('ct_tabblock2020', 'ct_block_assignment2020', 'tract_puma2020',
             'ct_county_crosswalk', 'census_puma_population2020',
             'census_ct_mcd_population2020', 'ct_opm_population2020')
    ids = [f'{reference_id}:{kind}' for kind in kinds]
    complete = [f'{kind}:complete-original' for kind in kinds]
    for row in intersections:
        if row['state_fips'] != '09':
            rows.append(row)
            continue
        key = row['puma_code'], row['county_geoid']
        if key in accepted:
            basis = accepted[key]
            rows.append(dict(row, intersection_population=basis['population'],
                             reference_ids=sorted(set(row['reference_ids'] + ids)),
                             reference_locators=sorted(set(row['reference_locators'] + complete +
                                                           basis['reference_locators']))))
    updated_controls = []
    for controls, key, values, kind in [
        (puma_totals, 'puma_code', ct.puma_totals, 'census_puma_population2020'),
        (county_totals, 'county_geoid', ct.county_totals, 'ct_opm_population2020'),
    ]:
        updated = []
        for row in controls:
            if row['state_fips'] != '09':
                updated.append(row)
                continue
            _require(row[key] in values, 'CT independent control coverage differs')
            locator = (f'{kind}:html:GEOID=09{row[key]}' if key == 'puma_code' else
                       f'{kind}:Sheet1:summary-label=' + next(
                           name for name, code in SUMMARY_NAMES.items() if code == row[key]))
            updated.append(dict(row, population=values[row[key]],
                                reference_ids=sorted(set(row['reference_ids'] + ids)),
                                reference_locators=sorted(set(
                                    row['reference_locators'] + complete + [locator]))))
        updated_controls.append(updated)
    return rows, *updated_controls, dict(ct.diagnostics, geocorr_assertions=assertions,
                                         geocorr_population_basis_adopted=False)
