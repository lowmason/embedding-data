import csv
import io
from pathlib import Path
from zipfile import ZipFile

import polars as pl
from code_fixtures import write_xlsx

STATE_ROWS = [
    ['Census Bureau Region and Division Codes and FIPS Codes for States', None, None, None],
    ['Source: U.S. Census Bureau, Population Division', None, None, None],
    ['Internet Release Date: May 2026', None, None, None],
    [None, None, None, None],
    ['Region', 'Division', 'State (FIPS)', 'Name'],
    ['1', '0', '00', 'Northeast Region'],
    ['1', '1', '00', 'New England Division'],
    ['1', '1', '09', 'Connecticut'],
    ['3', '0', '00', 'South Region'],
    ['3', '5', '00', 'South Atlantic Division'],
    ['3', '5', '51', 'Virginia'],
    ['3', '6', '00', 'East South Central Division'],
    ['3', '6', '01', 'Alabama'],
    ['0', '0', '72', 'Puerto Rico'],
]
MEMBER_HEADER = [
    'CBSA Code', 'Metropolitan Division Code', 'CSA Code', 'CBSA Title',
    'Metropolitan/Micropolitan Statistical Area', 'Metropolitan Division Title',
    'CSA Title', 'County/County Equivalent', 'State Name', 'FIPS State Code',
    'FIPS County Code', 'Central/Outlying County',
]
MEMBER_ROWS = [
    ['Table with row headers in column A and column headers in row 3'] + [None] * 11,
    ['List 1. Fixture July 2023 delineations'] + [None] * 11,
    MEMBER_HEADER,
    ['10000', None, None, 'Fixture metropolitan', 'Metropolitan Statistical Area',
     None, None, 'Autauga County', 'Alabama', '01', '001', 'Central'],
    ['10000', None, None, 'Fixture metropolitan', 'Metropolitan Statistical Area',
     None, None, 'Alexandria city', 'Virginia', '51', '510', 'Outlying'],
    ['20000', None, None, 'Fixture micropolitan', 'Micropolitan Statistical Area',
     None, None, 'Capitol Planning Region', 'Connecticut', '09', '110', 'Central'],
    ['30000', None, None, 'Fixture excluded', 'Micropolitan Statistical Area',
     None, None, 'Adjuntas Municipio', 'Puerto Rico', '72', '001', 'Central'],
]
COUNTY_ROWS = [
    ['AL', '01001', 'Autauga County'],
    ['CT', '09110', 'Capitol Planning Region'],
    ['VA', '51001', 'Accomack County'],
    ['VA', '51510', 'Alexandria city'],
    ['PR', '72001', 'Adjuntas Municipio'],
]
FIXTURE_SCOPE = frozenset({'01', '09', '51'})
HUD_ROWS = [
    ['ZIP', 'COUNTY', 'BUS_RATIO', 'STATE'],
    ['00001', '01001', '1', 'AL'],
    ['00002', '01001', '0', 'AL'],
    ['00003', '01001', '0.6', 'AL'],
    ['00003', '72001', '0.4', 'PR'],
    ['00004', '01001', '0.5', 'AL'],
    ['00004', '51510', '0.5', 'VA'],
    ['00005', '72001', '1', 'PR'],
    ['00006', '01999', '1', 'AL'],
    ['00007', '09001', '1', 'CT'],
    ['00008', '60', '0', 'AS'],
    ['00009', '01001', '1', 'AL'],
    ['00009', '72001', '0', 'PR'],
]


def sheet(rows):
    return pl.DataFrame(rows, orient='row', schema={f'c{i}': pl.String
                                                for i in range(len(rows[0]))})


def write_counties(file: Path, rows=COUNTY_ROWS):
    text = io.StringIO()
    writer = csv.writer(text, delimiter='|', lineterminator='\n')
    writer.writerow(['USPS', 'GEOID', 'GEOIDFQ', 'ANSICODE', 'NAME', 'ALAND', 'AWATER',
                     'ALAND_SQMI', 'AWATER_SQMI', 'INTPTLAT', 'INTPTLONG'])
    for usps, code, title in rows:
        writer.writerow([usps, code, '0500000US' + code, '00000000', title,
                         '1', '0', '1', '0', '0', '0'])
    with ZipFile(file, 'w') as archive:
        archive.writestr('2025_Gaz_counties_national.txt', text.getvalue())


def originals(directory: Path) -> dict[str, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    files = {k: directory / name for k, name in {
        'states_2025': 'state-geocodes-v2025.xlsx',
        'counties_2025': '2025_Gaz_counties_national.zip',
        'cbsa_2023': 'list1_2023.xlsx',
        'hud_2025q4': 'ZIP-COUNTY_122025.xlsx',
    }.items()}
    write_xlsx(files['states_2025'], STATE_ROWS)
    write_counties(files['counties_2025'])
    write_xlsx(files['cbsa_2023'], MEMBER_ROWS)
    write_xlsx(files['hud_2025q4'], HUD_ROWS)
    return files


def source_frames(tmp_path):
    from embedding_data import geography_parsers as gp
    from embedding_data import ita_references

    files = originals(tmp_path / 'originals')

    def read(file):
        return pl.read_excel(file, has_header=False, drop_empty_rows=False,
                             read_options={'dtypes': 'string'})
    return {
        **gp.parse_states(read(files['states_2025']), scope=FIXTURE_SCOPE),
        'counties': gp.parse_counties(files['counties_2025']),
        'members': gp.parse_members(read(files['cbsa_2023'])),
        'hud': ita_references.read_hud(files['hud_2025q4']),
    }


def fixture_registry(files):
    from dataclasses import replace

    from embedding_data import geography_references as gr
    from embedding_data import manifest

    return {k: replace(gr.REGISTRY[k], sha256=manifest.sha256_file(file),
                       size=file.stat().st_size, fixture=True, state_scope=FIXTURE_SCOPE)
            for k, file in files.items()}


def seed_geography_tree(data_dir):
    from embedding_data import geography_references as gr

    files = originals(data_dir / 'originals')
    registry = fixture_registry(files)
    for kind, file in files.items():
        gr.import_reference(data_dir, kind, file, registry=registry)
    return registry
