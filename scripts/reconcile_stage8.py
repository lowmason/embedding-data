'''Independent offline Stage 8 controls; no mapping implementation imports.'''
import csv
import hashlib
import json
import platform
import re
import sys
from collections import defaultdict
from decimal import Decimal
from importlib.metadata import distributions, version
from pathlib import Path

import fastexcel
import polars as pl
import typer

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ('acs/core', 'acs/five_year', 'acs/vintage')
SCOPE = frozenset(
    '01 02 04 05 06 08 09 10 11 12 13 15 16 17 18 19 20 21 22 23 24 25 26 '
    '27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 44 45 46 47 48 49 50 '
    '51 53 54 55 56'.split()
)
CLI = 'src/embedding_data/cli.py'
OLD_CLI = '68778e16b7cc051745c1e34d3dee6a9fc044fd12b1f78103773984503e9f9742'
NEW_CLI = '32a86b3d07bf112fabc1edb01fd10a966e840c185642e55d00f35dfd435220b3'
GEO_PIN = '5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d'
TOLERANCE = 1e-12
ROUNDING = Decimal('0.000050000001')
TABLES = (
    'acs_code_lookup', 'acs_area_lookup', 'puma_county_factors', 'puma_msa_factors',
    'puma_msa_coverage', 'acs_core_canonical', 'acs_five_year_canonical', 'acs_vintage_canonical'
)
app = typer.Typer(pretty_exceptions_show_locals=False)
REFERENCE_NAMES = {
    'census_occupation_2018': 'census_occupation_2018.xlsx',
    'county_composition_2022': 'county_composition_2022.xls',
    'geocorr_county_totals': 'geocorr_county_totals.csv',
    'geocorr_county_totals_request': 'geocorr_county_totals_request.request.txt',
    'geocorr_county_totals_response': 'geocorr_county_totals_response.response.html',
    'geocorr_form': 'geocorr_form.html',
    'geocorr_help': 'geocorr_help.html',
    'geocorr_intersections': 'geocorr_intersections.csv',
    'geocorr_intersections_request': 'geocorr_intersections_request.request.txt',
    'geocorr_intersections_response': 'geocorr_intersections_response.response.html',
    'geocorr_puma_totals': 'geocorr_puma_totals.csv',
    'geocorr_puma_totals_request': 'geocorr_puma_totals_request.request.txt',
    'geocorr_puma_totals_response': 'geocorr_puma_totals_response.response.html',
    'industry_pairs_html': 'industry_pairs_html.html',
    'industry_tokens_html': 'industry_tokens_html.html',
    'ipums_ind_pairs': 'ipums_ind_pairs.xlsx',
    'ipums_ind_tokens': 'ipums_ind_tokens.xlsx',
    'ipums_occ_pairs': 'ipums_occ_pairs.xlsx',
    'msa_puma_2023_2020': 'msa_puma_2023_2020.xlsx',
    'occupation_pairs_html': 'occupation_pairs_html.html',
    'puma_composition_2020': 'puma_composition_2020.xls',
    'pums_annual_2024': 'pums_annual_2024.xls',
    'pums_annual_guide': 'pums_annual_guide.pdf',
    'pums_five_year_2024': 'pums_five_year_2024.xlsx',
    'pums_five_year_guide': 'pums_five_year_guide.pdf',
    'pums_industry_2017': 'pums_industry_2017.xlsx',
    'pums_industry_2022': 'pums_industry_2022.xlsx',
    'pums_occupation_2018': 'pums_occupation_2018.xlsx',
    'soc_tokens_html': 'soc_tokens_html.html',
    'usa_ind': 'usa_ind.html',
    'usa_indnaics': 'usa_indnaics.html',
    'usa_migplac1': 'usa_migplac1.html',
    'usa_migpuma1': 'usa_migpuma1.html',
    'usa_multyear': 'usa_multyear.html',
    'usa_occ': 'usa_occ.html',
    'usa_occsoc': 'usa_occsoc.html',
    'usa_puma': 'usa_puma.html',
    'usa_pwpuma00': 'usa_pwpuma00.html',
    'usa_pwstate2': 'usa_pwstate2.html'
}

STAGE7_NAMES = (
    'pyproject.toml', 'uv.lock', *(
        f'src/embedding_data/{name}.py' for name in (
            '__init__', 'ipums_verification_run', 'ipums_cli', 'cli', 'ipums_acceptance',
            'ipums_conversion', 'ipums_ddi', 'ipums_industry', 'ipums_parity', 'ipums_references',
            'ipums_census_access', 'ipums_totals', 'ipums_weights', 'ipums_delivery',
            'acs_benchmark_extract', 'cps_benchmark_extract', 'manifest', 'paths', 'target_io',
            'geography_references', 'geography_parsers', 'code_references',
            'osha_benchmark_download'
        )
    )
)
EXECUTING_NAMES = tuple(
    dict.fromkeys(
        (
            *STAGE7_NAMES, *(
                f'src/embedding_data/{name}.py' for name in (
                    'acs_mapping_contract', 'acs_mapping_inputs', 'acs_mapping_io',
                    'acs_mapping_references', 'acs_code_references', 'acs_code_mapping',
                    'acs_area_references', 'acs_geography_factors', 'acs_area_mapping',
                    'acs_mapping_companions', 'acs_mapping_bundle', 'acs_mapping', 'target_inputs',
                    'code_build', 'classification_tables', 'naics_relationships', 'filing_rules',
                    'ita_naics_mapping', 'ita_summary', 'ita_references', 'ita_catalog',
                    'osha_encoding', 'geography_build', 'geography_tables', 'geography_hud',
                    'geography_cli'
                )
            )
        )
    )
)

def require(condition, message):
    if not condition:
        raise ValueError(message)

def safe(path):
    path = Path(path).absolute()
    require('..' not in path.parts, 'unsafe path')
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), 'symlink refused')
    return path

def relative(root, name):
    require(
        isinstance(name, str) and bool(name) and not name.startswith('/') and all(
            p not in ('', '.', '..') for p in name.split('/')
        ), 'unsafe relative path'
    )
    return safe(root / name)

def digest(file):
    safe(file)
    value = hashlib.sha256()
    with file.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()

def record(file):
    require(safe(file).is_file(), 'missing regular file')
    return {'sha256': digest(file), 'size': file.stat().st_size}

def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result

def reject_constant(value):
    raise ValueError('nonfinite JSON number')

def loads(body):
    return json.loads(body, object_pairs_hook=unique, parse_constant=reject_constant)

def read(file):
    safe(file)
    return loads(file.read_bytes())

def write(file, value):
    with file.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')

def identities():
    names = (
        'scripts/reconcile_stage8.py', 'tests/test_stage8_reconciliation.py',
        'tests/acs_mapping_fixtures.py', 'pyproject.toml', 'uv.lock'
    )
    return {
        'files': {
            name: record(ROOT / name)
            for name in names
        },
        'python': platform.python_version(),
        'implementation': platform.python_implementation(),
        'dependencies': dict(sorted((d.metadata['Name'], d.version) for d in distributions()))
    }

def inventory(data_dir, excluded):
    records = {}
    for family in ('raw', 'derived'):
        for file in safe(data_dir / family).rglob('*'):
            safe(file)
            if file.is_file() and not file.is_relative_to(excluded):
                name = file.relative_to(data_dir).as_posix()
                if name != 'raw/manifest.jsonl':
                    records[name] = record(file)
    return dict(sorted(records.items()))

def freeze(data_dir: Path, control_dir: Path) -> dict:
    data_dir, control_dir = safe(data_dir), safe(control_dir)
    require(
        not control_dir.exists()
        and not control_dir.with_name(control_dir.name + '.part').exists(), 'occupied control ID'
    )
    require(not data_dir.is_relative_to(control_dir), 'control directory contains data root')
    frozen = inventory(data_dir, control_dir)
    manifest = safe(data_dir / 'raw/manifest.jsonl').read_bytes()
    require(not manifest or manifest.endswith(b'\n'), 'manifest prefix lacks record boundary')
    result = {
        'files': frozen,
        'manifest_prefix': {
            'sha256': hashlib.sha256(manifest).hexdigest(),
            'size': len(manifest)
        },
        'reconciler': identities()
    }
    control_dir.mkdir(parents=True)
    try:
        with (control_dir / 'manifest-prefix.jsonl').open('xb') as stream:
            stream.write(manifest)
        write(control_dir / 'freeze.json', result)
    except BaseException:
        for file in control_dir.iterdir():
            file.unlink()
        control_dir.rmdir()
        raise
    return {'protected_file_count': len(frozen), 'manifest_prefix': result['manifest_prefix']}

def check_record(file, expected, context):
    require(record(file) == {k: expected[k] for k in ('sha256', 'size')}, context)

def manifest_records(data_dir, control_dir):
    frozen = read(control_dir / 'freeze.json')
    prefix = safe(control_dir / 'manifest-prefix.jsonl').read_bytes()
    saved = frozen['manifest_prefix']
    require(
        len(prefix) == saved['size'] and hashlib.sha256(prefix).hexdigest() == saved['sha256'],
        'manifest prefix control hash or length differs'
    )
    current = safe(data_dir / 'raw/manifest.jsonl').read_bytes()
    require(
        len(current) >= len(prefix) and current[:len(prefix)] == prefix,
        'manifest prefix prior bytes changed or truncated'
    )
    # Authenticate exact bytes before parsing either section.
    old = [loads(line) for line in prefix.splitlines()]
    suffix = [loads(line) for line in current[len(prefix):].splitlines()]
    require(len({r['path'] for r in old + suffix}) == len(old + suffix), 'duplicate manifest path')
    return frozen, old, suffix

def preservation(data_dir: Path, control_dir: Path) -> dict:
    data_dir, control_dir = safe(data_dir), safe(control_dir)
    frozen, old, suffix = manifest_records(data_dir, control_dir)
    require(frozen['reconciler'] == identities(), 'independent software identity changed')
    current = inventory(data_dir, control_dir)
    for name, expected in frozen['files'].items():
        require(current.get(name) == expected, 'protected file changed: ' + name)
    new_raw = {
        name.removeprefix('raw/'): value
        for name, value in current.items()
        if name.startswith('raw/') and name not in frozen['files']
    }
    appended = {r['path']: r for r in suffix}
    require(set(new_raw) == set(appended), 'new raw files and manifest suffix differ')
    for name, expected in appended.items():
        check_record(relative(data_dir / 'raw', name), expected, 'appended raw hash/size differs')
    roots = set()
    for name in appended:
        parts = name.split('/')
        require(
            len(parts) == 4 and parts[:2] == ['references', 'acs-mapping'],
            'unaccounted manifest suffix record'
        )
        roots.add('/'.join(parts[:3]))
    accounted = set()
    for root in roots:
        directory = relative(data_dir / 'raw', root)
        require(root + '/receipt.json' in appended, 'snapshot receipt not separately manifested')
        receipt = read(directory / 'receipt.json')
        require(
            receipt['reference_id'] == directory.name and receipt['reference_version']
            == 'acs-mapping-references-v1', 'snapshot receipt identity differs'
        )
        files = receipt['files']
        require(
            set(receipt['originals']) == set(REFERENCE_NAMES) and set(files) == set(
                REFERENCE_NAMES.values()
            ), 'complete registered reference set differs'
        )
        require(
            set(files) == {
                Path(r['citation']['path']).name
                for r in receipt['originals'].values()
            }, 'receipt original/file set differs'
        )
        citations = receipt['raw_citations']
        require(
            len(citations) == len(files) and len({r['path']
                                                  for r in citations}) == len(files),
            'receipt record count or unique paths differs'
        )
        expected_paths = {root + '/' + name for name in files}
        require({r['path'] for r in citations} == expected_paths, 'receipt citation paths differ')
        require(
            {p.name
             for p in directory.iterdir()} == set(files) | {'receipt.json'},
            'snapshot contains missing or extra paths'
        )
        for name, expected in files.items():
            path = root + '/' + name
            require(path in appended, 'snapshot file absent from suffix')
            check_record(relative(directory, name), expected, 'snapshot file hash/size differs')
            citation = next(r for r in citations if r['path'] == path)
            require(citation == appended[path], 'receipt citation differs from manifest suffix')
        for original in receipt['originals'].values():
            check_record(
                relative(directory,
                         Path(original['citation']['path']).name), original,
                'original receipt hash/size differs'
            )
        accounted.update(expected_paths | {root + '/receipt.json'})
    require(accounted == set(appended), 'manifest appends not fully receipt-accounted')
    return {
        'manifest_prefix_equal': True,
        'protected_files_equal': True,
        'manifest_appends_accounted': True,
        'appended_record_count': len(suffix)
    }

def authenticate_bundle(directory, pin):
    require(isinstance(pin, str) and re.fullmatch('[0-9a-f]{64}', pin), 'invalid external pin')
    require(digest(directory / 'outputs.json') == pin, 'external inventory pin differs')
    records = read(directory / 'outputs.json')
    require(
        {f.name
         for f in directory.iterdir()} == set(records) | {'outputs.json'},
        'bundle file set differs'
    )
    for name, expected in records.items():
        file = relative(directory, name)
        check_record(file, expected, 'bundle hash/size differs')
        if file.suffix == '.parquet' and 'schema' in expected:
            scan = pl.scan_parquet(file)
            schema = scan.collect_schema()
            require(
                expected.get('rows') == scan.select(pl.len()).collect().item() and expected.get(
                    'columns'
                ) == list(schema) and expected.get('schema') == {
                    c: str(t)
                    for c, t in schema.items()
                }, 'bundle row/schema inventory differs'
            )
    return read(directory / 'inputs.json')

def current_software(software, names):
    require(set(software['files']) == set(names), 'executing software file set differs')
    require(
        software['python'] == platform.python_version()
        and software['implementation'] == platform.python_implementation() and software.get(
            'uv_lock_sha256', software['files'].get('uv.lock', {}).get('sha256')
        ) == digest(ROOT / 'uv.lock'), 'executing Python/lock identity differs'
    )
    require(
        software['dependencies'] == identities()['dependencies'], 'dependency inventory differs'
    )
    for name, expected in software['files'].items():
        check_record(relative(ROOT, name), expected, 'executing software changed')

def historical_cli_allowed(family, name, recorded, actual, request, stage7, stage8):
    '''D5 is a single historical creator entrypoint, bound to two current inventories.'''
    return (
        family == 'geography' and name == CLI and recorded == OLD_CLI and actual == NEW_CLI
        and request.get('geography_run') == 'stage5_geography_20261014' and request.get(
            'geography_outputs_sha256'
        ) == GEO_PIN and stage7.get('files', {}).get(CLI,
                                                     {}).get('sha256') == NEW_CLI and stage8.get(
                                                         'files', {}
                                                     ).get(CLI, {}).get('sha256') == NEW_CLI
    )

def table_contracts(directory):
    keys = {
        'acs_code_lookup': ('system', 'source_scheme', 'paired_census_code', 'source_token'),
        'acs_area_lookup': (
            'profile', 'sample_id', 'release_year', 'component_year', 'role', 'source_state_code',
            'source_area_code'
        ),
        'puma_county_factors': ('area_type', 'state_fips', 'area_code', 'county_geoid'),
        'puma_msa_factors': ('state_fips', 'puma_code', 'msa_code'),
        'puma_msa_coverage': ('state_fips', 'puma_code')
    }
    frames = {
        'population_year': 2020,
        'puma_vintage': 2020,
        'county_composition_year': 2022,
        'county_inventory_vintage': 2025,
        'msa_delineation': 'July 2023'
    }
    for name, natural in keys.items():
        frame = pl.read_parquet(directory / (name + '.parquet'))
        require(not frame.select(natural).is_duplicated().any(), 'duplicate lookup/reference key')
        require(
            frame.equals(frame.sort(natural, nulls_last=False)), 'reference key ordering differs'
        )
        for column, dtype in frame.schema.items():
            if column in frames:
                require(frame[column].eq(frames[column]).all(), 'geographic frame differs')
            if 'population' in column:
                require(dtype == pl.Int64, 'integer population dtype differs')
            if name.startswith('puma_') and (
                'factor' in column or 'fraction' in column
            ) and column != 'factor_key' and not column.startswith('flag_'):
                require(dtype == pl.Float64, 'factor Float64 dtype differs')
            if isinstance(dtype, pl.List):
                require(
                    dtype in (pl.List(pl.String), pl.List(pl.List(pl.String))),
                    'list reference/candidate type differs'
                )
                for value in frame[column].to_list():
                    require(
                        value is not None and all(v is not None for v in value),
                        'null reference/candidate list or element'
                    )
                    if dtype == pl.List(pl.String):
                        require(
                            value == sorted(set(value)), 'reference/candidate set ordering differs'
                        )
        if name in ('acs_code_lookup', 'acs_area_lookup'):
            identity = 'code_lookup_id' if name == 'acs_code_lookup' else 'area_lookup_id'
            for row in frame.iter_rows(named=True):
                encoded = json.dumps(
                    [row[k] for k in natural],
                    ensure_ascii=False,
                    separators=(',', ':'),
                    allow_nan=False
                ).encode()
                require(
                    row[identity] == hashlib.sha256(encoded).hexdigest(),
                    'lookup natural-key identity differs'
                )

def upstreams(data_dir, inputs):
    request = inputs['selected_upstreams']['request']
    selected = {}
    for family, key in (
        ('codes', 'codes'), ('geography', 'geography'), ('ipums/verification', 'ipums')
    ):
        run = request[key + '_run']
        require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]*', run), 'unsafe selected run')
        directory = relative(data_dir, 'derived/' + family + '/' + run)
        selected[key] = authenticate_bundle(directory, request[key + '_outputs_sha256'])
    receipt = selected['ipums']['references']['receipt_citation']
    receipt_file = relative(data_dir / 'raw', receipt['path'])
    check_record(receipt_file, receipt, 'selected Stage7 reference receipt differs')
    require(digest(receipt_file) == request['ipums_references_receipt_sha256'],
            'selected Stage7 reference receipt pin differs')
    current_software(inputs['software'], EXECUTING_NAMES)
    current_software(selected['ipums']['software'], STAGE7_NAMES)
    diagnostics = []
    for key in ('codes', 'geography'):
        upstream = selected[key]
        require(
            upstream['python'] == sys.version and upstream['uv_lock_sha256'] == digest(
                ROOT / 'uv.lock'
            ), 'upstream Python/lock identity differs'
        )
        for name, expected in upstream['dependencies'].items():
            require(version(name) == expected, 'upstream dependency differs')
        for name, expected in upstream['implementation'].items():
            actual = digest(relative(ROOT, name))
            if actual == expected:
                continue
            require(
                historical_cli_allowed(
                    key, name, expected, actual, request, selected['ipums']['software'],
                    inputs['software']
                ), 'unapproved historical upstream software mismatch'
            )
            diagnostics.append(
                {
                    'rule': 'D5',
                    'historical_sha256': OLD_CLI,
                    'executing_sha256': NEW_CLI
                }
            )
    for profile in PROFILES:
        source = inputs['sources'][profile]
        authority = selected['ipums']['deliveries'][profile]
        require(
            all(
                source[k] == authority[k] for k in
                ('delivery_id', 'parquet', 'parquet_record', 'raw_citations', 'ddi', 'definition')
            ), 'source selection differs'
        )
    return selected, diagnostics

def workbook(file, sheet):
    return list(
        fastexcel.read_excel(file.read_bytes()).load_sheet(
            sheet, header_row=None, dtypes='string'
        ).to_polars().iter_rows()
    )

def csv_rows(file):
    with file.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.reader(stream, strict=True))
    require(len(rows) > 2, 'empty Geocorr original')
    require(all(len(row) == len(rows[0]) for row in rows), 'Geocorr width differs')
    return [dict(zip(rows[0], row, strict=True)) for row in rows[2:]]

def integer(value):
    require(isinstance(value, str) and re.fullmatch('[0-9]+', value), 'noninteger population')
    return int(value)

def keyed(rows, keys, values):
    result = {}
    for row in rows:
        key = tuple(row[k] for k in keys)
        require(key not in result, 'duplicate reference natural key')
        result[key] = tuple(row[k] for k in values)
    return result

def rounding(value, numerator, denominator, scale=1):
    require(denominator > 0, 'nonpositive population denominator')
    require(
        abs(Decimal(str(value)) - Decimal(numerator) * scale / Decimal(denominator)) <= ROUNDING,
        'published rounding outside decimal bound'
    )

def reference_geography(data_dir, upstream, directory):
    '''Authenticate the complete 2025 original before domestic-scope comparisons.'''
    import io
    from zipfile import ZipFile
    original = upstream['references']['counties_2025']['relative']
    matches = [r for r in upstream['raw'] if r['path'] == original
               or r['path'].endswith('/' + original)]
    require(len(matches) == 1, 'county original citation missing or ambiguous')
    file = relative(data_dir / 'raw', matches[0]['path'])
    check_record(file, matches[0], 'county original hash/size differs')
    with ZipFile(file) as archive:
        require(archive.namelist() == ['2025_Gaz_counties_national.txt'],
                'county original archive member differs')
        body = archive.read('2025_Gaz_counties_national.txt').decode('utf-8-sig')
    rows = csv.DictReader(io.StringIO(body), delimiter='|')
    require({'USPS', 'GEOID', 'NAME'} <= set(rows.fieldnames), 'county original header differs')
    counties = set()
    for row in rows:
        if not any(v and v.strip() for v in row.values()):
            continue
        geoid = row['GEOID'].strip()
        require(re.fullmatch('[0-9]{5}', geoid) and geoid[:2] in SCOPE | {'72'}
                and geoid not in counties, 'invalid/duplicate full county inventory code')
        counties.add(geoid)
    require({c for c in counties if c.startswith('09')} == {f'091{i}0' for i in range(1, 10)},
            '2025 county inventory must preserve all nine CT planning regions')
    selected = pl.read_parquet(directory / 'county_reference.parquet')
    require(set(selected['county_geoid']) == {c for c in counties if c[:2] in SCOPE},
            'selected county table differs from complete original domestic scope')
    return counties


def populations(directory, files, county_inventory):
    intersections = csv_rows(files['geocorr_intersections'])
    pumas = {
        k: integer(v[0])
        for k, v in keyed(
            csv_rows(files['geocorr_puma_totals']), ('state', 'puma22'), ('pop20', )
        ).items()
    }
    counties = {
        k: integer(v[0])
        for k, v in keyed(
            csv_rows(files['geocorr_county_totals']), ('state', 'county'), ('pop20', )
        ).items()
    }
    require(set(s for s, _ in pumas) <= SCOPE | {'72'}, 'invalid reference state')
    require({c for _, c in counties} <= county_inventory,
            'county population control absent from complete 2025 original')
    keyed(intersections, ('state', 'puma22', 'county'), ('pop20', ))
    sums_puma, sums_county = defaultdict(int), defaultdict(int)
    groups = keyed(
        [
            {
                'state': r[0],
                'puma': r[1],
                'group_state': r[2][1:],
                'group': r[3]
            } for r in workbook(files['puma_composition_2020'], 'PUMA_POWPUMA_MIGPUMA')[1:]
        ], ('state', 'puma'), ('group_state', 'group')
    )
    county_groups = keyed(
        [
            {
                'state': r[0],
                'county': r[0] + r[1],
                'group_state': r[2][1:],
                'group': r[3]
            }
            for r in workbook(files['county_composition_2022'], 'MIGPUMA-POWPUMA 2022 Lookup')[1:]
        ], ('state', 'county'), ('group_state', 'group')
    )
    require(
        set(groups) == set(pumas) and set(county_groups) == set(counties),
        'composition/control keys differ'
    )
    totals_group, county_group_totals = defaultdict(int), defaultdict(int)
    for key, pop in pumas.items():
        totals_group[groups[key]] += pop
    for key, pop in counties.items():
        county_group_totals[county_groups[key]] += pop
    require(totals_group == county_group_totals, 'county-to-group totals differ')
    expected, pooled = {}, defaultdict(int)
    for row in intersections:
        state, puma, county = row['state'], row['puma22'], row['county']
        pop = integer(row['pop20'])
        require(county[:2] == state, 'county namespace differs')
        require(
            groups[state, puma] == county_groups[state, county], 'county/group direction differs'
        )
        sums_puma[state, puma] += pop
        sums_county[state, county] += pop
        rounding(row['afact'], pop, pumas[state, puma])
        rounding(row['afact2'], pop, counties[state, county])
        if state in SCOPE:
            expected['residence', state, puma, county] = (
                pop, pumas[state, puma], counties[state, county]
            )
        pooled[*groups[state, puma], county] += pop
    require(
        dict(sums_puma) == pumas and dict(sums_county) == counties,
        'integer intersections do not reconcile to independent controls'
    )
    for (state, code, county), pop in pooled.items():
        if state in SCOPE:
            expected['work_migration', state, code, county] = (
                pop, totals_group[state, code], counties[county[:2], county]
            )
    county_frame = pl.read_parquet(directory / 'puma_county_factors.parquet')
    actual = keyed(
        county_frame.to_dicts(), ('area_type', 'state_fips', 'area_code', 'county_geoid'), (
            'intersection_population', 'area_population', 'county_population'
        )
    )
    require(actual == expected, 'county population relations differ from originals')
    closure = defaultdict(float)
    for row in county_frame.iter_rows(named=True):
        n, total = row['intersection_population'], row['area_population']
        require(
            county_frame.schema['factor'] == pl.Float64 and row['factor'] == n / total,
            'county factor differs from exact integer ratio'
        )
        require(
            row['flag_fractional_split'] == (n != total) and row['flag_geographic_allocation'],
            'county allocation provenance differs'
        )
        closure[row['area_type'], row['state_fips'], row['area_code']] += row['factor']
    maximum = max(abs(value - 1) for value in closure.values())
    msa_rows = workbook(files['msa_puma_2023_2020'], 'MSA2023_PUMA2020_crosswalk')[1:]
    msa_expected, msa_totals, msa_sum, allocated = {}, {}, defaultdict(int), defaultdict(int)
    for row in msa_rows:
        state, puma, msa = row[2], row[4], row[0]
        total, whole, pop = integer(row[7]), integer(row[6]), integer(row[8])
        require(
            pumas[state, puma] == total and msa_totals.get(msa, whole) == whole,
            'MSA original controls differ'
        )
        msa_totals[msa] = whole
        msa_sum[msa] += pop
        allocated[state, puma] += pop
        rounding(row[9], pop, whole, 100)
        rounding(row[10], pop, total, 100)
        if state in SCOPE:
            key = state, puma, msa
            require(key not in msa_expected, 'duplicate MSA relation')
            msa_expected[key] = total, whole, pop
    require(
        dict(msa_sum) == msa_totals and all(allocated[k] <= pumas[k]
                                            for k in allocated), 'MSA integer closure differs'
    )
    msa_frame = pl.read_parquet(directory / 'puma_msa_factors.parquet')
    require(
        keyed(
            msa_frame.to_dicts(), ('state_fips', 'puma_code', 'msa_code'), (
                'puma_population', 'msa_population', 'intersection_population'
            )
        ) == msa_expected, 'MSA population differs from original workbook'
    )
    reverse = defaultdict(float)
    for row in msa_frame.iter_rows(named=True):
        n, p, m = row['intersection_population'], row['puma_population'], row['msa_population']
        require(
            all(
                msa_frame.schema[f] == pl.Float64
                for f in ('puma_to_msa_factor', 'msa_to_puma_factor')
            ) and row['puma_to_msa_factor'] == n / p and row['msa_to_puma_factor'] == n / m,
            'MSA factor differs from integer ratio'
        )
        reverse[row['msa_code']] += n / m
    maximum = max(maximum, max(abs(v - 1) for v in reverse.values()))
    coverage = pl.read_parquet(directory / 'puma_msa_coverage.parquet')
    require(
        keyed(
            coverage.to_dicts(), ('state_fips', 'puma_code'), (
                'puma_population', 'msa_population', 'non_msa_population'
            )
        ) == {
            k: (pop, allocated[k], pop - allocated[k])
            for k, pop in pumas.items() if k[0] in SCOPE
        }, 'MSA residual differs from independent controls'
    )
    for row in coverage.iter_rows(named=True):
        p = row['puma_population']
        require(
            row['msa_fraction'] == row['msa_population'] / p and row['non_msa_fraction']
            == row['non_msa_population'] / p, 'MSA coverage ratio differs'
        )
    require(maximum <= TOLERANCE, 'factor closure exceeds 1e-12')
    return {
        'closure_max': maximum,
        'county_relations': len(expected),
        'msa_relations': len(msa_expected),
        'scoped_puma_population': sum(v for k, v in pumas.items() if k[0] in SCOPE),
        'complete_puma_population': sum(pumas.values()),
        'excluded_states': sorted({s
                                   for s, _ in pumas} - SCOPE)
    }, pumas, groups

def source_code_frequencies(file: Path, paired: str, token: str) -> pl.DataFrame:
    frame = pl.scan_parquet(file)
    component = 'MULTYEAR' if 'MULTYEAR' in frame.collect_schema() else 'YEAR'
    return (
        frame.select(
            'YEAR', 'SAMPLE',
            pl.col(component).alias('component_year'),
            pl.col(paired).cast(pl.String).str.zfill(4).alias('paired_code'),
            pl.col(token).str.strip_chars(' ').alias('source_token')
        ).group_by('YEAR', 'SAMPLE', 'component_year', 'paired_code', 'source_token').len().sort(
            'YEAR', 'SAMPLE', 'component_year', 'paired_code', 'source_token', nulls_last=False
        ).collect()
    )

def categories(source, name):
    matches = [v for v in source['ddi']['variables'] if v['name'] == name]
    require(len(matches) == 1, 'missing/ambiguous delivered DDI variable')
    values = matches[0].get('categories', [])
    require(len({str(c['value']) for c in values}) == len(values), 'duplicate DDI category')
    return {str(c['value']): c['label'] for c in values}

def all_true(frame, expression, message):
    require(frame.select(expression.fill_null(False).all()).collect().item(), message)

def original_prefix(source_file, companion):
    source, target = pl.scan_parquet(source_file), pl.scan_parquet(companion)
    schema, actual = source.collect_schema(), target.collect_schema()
    require(
        list(actual.items())[:len(schema)] == list(schema.items()),
        'original ordered schema prefix differs'
    )
    source_count = source.select(pl.len()).collect().item()
    require(source_count == target.select(pl.len()).collect().item(), 'source row count differs')
    batches = zip(
        source.collect_batches(chunk_size=65536, engine='streaming'),
        target.select(list(schema)).collect_batches(chunk_size=65536, engine='streaming'),
        strict=True
    )
    for left, right in batches:
        require(left.equals(right), 'original values/order/duplicate multiplicity differs')
    all_true(
        target.with_row_index('__ordinal'),
        pl.col('source_row').eq(pl.col('__ordinal')), 'source ordinal identity differs'
    )
    all_true(
        target,
        pl.col('source_parquet_sha256').eq(digest(source_file)), 'source hash annotation differs'
    )
    return source_count

def source_identity(source, companion):
    scan = pl.scan_parquet(companion)
    profile = source['profile']
    five = profile == 'acs/five_year'
    samples = categories(source, 'SAMPLE')
    mapping = {}
    for sample in source['definition']['samples']:
        label = '2020-2024, ACS 5-year' if five else sample[2:6] + ' ACS'
        matches = [code for code, text in samples.items() if text == label]
        require(len(matches) == 1, 'sample lacks positive delivered DDI label')
        mapping[str(int(matches[0]))
                if scan.collect_schema()['SAMPLE'].is_integer() else matches[0]] = sample
    release = pl.col('YEAR').cast(pl.Int64)
    component = pl.col('MULTYEAR' if five else 'YEAR').cast(pl.Int64)
    native = pl.when(release.eq(2022)).then(pl.lit('naics2017')).otherwise(pl.lit('naics2022'))
    interview = pl.when(component.lt(2023)).then(pl.lit('naics2017')).otherwise(
        pl.lit('naics2022')
    )
    all_true(
        scan,
        pl.all_horizontal(
            pl.col('acs_profile').eq(profile),
            pl.col('acs_release_year').eq(release),
            pl.col('acs_component_year').eq(component),
            pl.col('acs_sample_id').eq(pl.col('SAMPLE').cast(pl.String).replace_strict(mapping)),
            pl.col('industry_delivered_scheme').eq(native),
            pl.col('industry_interview_scheme').eq(interview),
            pl.col('occupation_delivered_scheme').eq('soc2018'),
            pl.col('flag_source_industry_recoded').eq(native.ne(interview))
        ), 'source profile/sample/component/delivered/interview identity differs'
    )

def code_measurements(source, companion, codes):
    counts = {}
    scan = pl.scan_parquet(companion)
    for prefix, system, pair, token in (
        ('industry', 'naics', 'IND', 'INDNAICS'), ('occupation', 'soc', 'OCC', 'OCCSOC')
    ):
        expected = source_code_frequencies(source, pair, token)
        require(
            expected.equals(source_code_frequencies(companion, pair, token)),
            'source/companion code frequencies differ'
        )
        grouped = scan.select(
            pl.col(prefix + '_delivered_scheme').alias('source_scheme'),
            pl.col(pair).cast(pl.String).str.zfill(4).alias('paired_census_code'),
            pl.col(token).str.strip_chars(' ').alias('source_token'), *[
                pl.col(prefix + '_' + c).alias(c) for c in codes.columns
                if c not in ('system', 'source_scheme', 'paired_census_code', 'source_token')
            ]
        ).group_by(pl.all()).len().collect()
        missing = grouped.filter(pl.col('source_token').is_null())
        require(
            not missing.filter(pl.col('mapping_status').ne('missing')).height,
            'real null source token must remain missing'
        )
        own = grouped.filter(pl.col('source_token').is_not_null()).drop('len').with_columns(
            pl.lit(system).alias('system')
        ).select(codes.columns)
        expected_lookup = codes.filter(pl.col('system').eq(system))
        require(
            own.join(expected_lookup, on=codes.columns, how='anti', nulls_equal=True).is_empty(),
            'companion code/status/reason/candidate assertions differ'
        )
        status = scan.group_by(prefix + '_mapping_status').len().sort(prefix + '_mapping_status'
                                                                      ).collect().to_dicts()
        reasons = scan.group_by(prefix + '_aggregation_reason_status').len().sort(
            prefix + '_aggregation_reason_status'
        ).collect().to_dicts()
        lengths = scan.group_by(
            pl.col(prefix + '_canonical_finest_candidates').list.len().alias('candidate_length')
        ).len().sort('candidate_length').collect().to_dicts()
        counts[prefix] = {
            'frequency_partitions': expected.to_dicts(),
            'status': status,
            'aggregation_reasons': reasons,
            'candidate_lengths': lengths,
            'unparseable': 0
        }
    return counts

def allocation_measurements(source, companion):
    scan = pl.scan_parquet(companion)
    names = scan.collect_schema()
    result = {}
    zero_labels = {
        'QIND': 'Original entry or Inapplicable (not in universe)',
        'QOCC': 'Entered as written',
        'QMIGRAT1': 'Not allocated'
    }
    for field, prefix in (('QIND', 'industry'), ('QOCC', 'occupation'), ('QMIGRAT1', 'migration')):
        variables = {v['name']: v for v in source['ddi']['variables']}
        labels = {
            str(c['value']): c['label']
            for c in variables.get(field, {}).get('categories', [])
        }
        available = field in names and bool(labels)
        allocated = pl.lit(False)
        status = pl.lit('unavailable')
        if available:
            value = pl.col(field).cast(pl.String)
            allocated = value.is_in([c for c, label in labels.items() if label == 'Allocated'])
            status = pl.when(allocated).then(pl.lit('allocated'))
            if labels.get('0') == zero_labels[field]:
                status = status.when(value.eq('0')).then(pl.lit('not_allocated_or_niu'))
            status = status.otherwise(pl.lit('unavailable'))
        expected_flag = pl.when(allocated).then(True).otherwise(pl.lit(None, dtype=pl.Boolean))
        all_true(
            scan,
            pl.col(prefix + '_source_allocation_status').eq_missing(status).and_(
                pl.col(prefix + '_source_allocated').eq_missing(expected_flag)
            ), 'source allocation evidence differs from delivered Q categories'
        )
        result[field] = {
            'dtype': str(names[field]) if field in names else None,
            'counts': scan.group_by(field).len().sort(field, nulls_last=False).collect().to_dicts()
            if field in names else [],
            'status': scan.group_by(prefix + '_source_allocation_status').len().sort(
                prefix + '_source_allocation_status'
            ).collect().to_dicts()
        }
    return result

def document(file):
    import html
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', file.read_text())))

def role_measurements(source, companion, areas, files, pumas, groups):
    scan = pl.scan_parquet(companion)
    domestic = categories(source, 'STATEFIP')
    by_label = {label: code for code, label in domestic.items() if code in SCOPE | {'72'}}
    definitions = {
        'residence': set(pumas),
        'workplace': set(groups.values()),
        'migration': set(groups.values())
    }
    specials = {
        'workplace': {
            '00000': ('niu_or_unidentifiable', 'N/A or not identifiable'),
            '00001': ('foreign', 'Did not work in the United States or in Puerto Rico')
        },
        'migration': {
            '00000': (
                'niu_or_unidentifiable',
                'N/A (less than 1 year old or lived in same residence 1 year ago)'
            ),
            '00001': (
                'foreign', 'Did not live in the United States or in Puerto Rico one year ago'
            ),
            '00002': (
                'territory',
                'Lived in Puerto Rico one year ago and current residence is in the U.S.'
            )
        }
    }
    territory = {
        'Puerto Rico', 'Guam', 'Virgin Islands', 'Other US Possessions', 'U.S. outlying area'
    }
    statuses = {}
    for role, state_field, area_field, width in (
        ('residence', 'STATEFIP', 'PUMA', 2), ('workplace', 'PWSTATE2', 'PWPUMA00', 2), (
            'migration', 'MIGPLAC1', 'MIGPUMA1', 3
        )
    ):
        labels = categories(source, state_field)
        text = document(files['usa_' + area_field.lower()])
        require(
            all(s in text for s in ('2020 PUMAs', 'pre-2022 respondents', 'state-dependent')),
            'role frame documentation differs'
        )
        own = areas.filter(pl.col('profile').eq(source['profile']).and_(pl.col('role').eq(role)))
        for row in own.iter_rows(named=True):
            state, area = str(row['source_state_code']).zfill(width), str(row['source_area_code']
                                                                          ).zfill(5)
            require(state in labels, 'unknown DDI source state')
            label = labels[state]
            fips = by_label.get(label)
            special = specials.get(role, {}).get(area)
            if special:
                status, reason = special
                require(area + ' = ' + reason in text, 'special lacks original documentation')
                if status == 'niu_or_unidentifiable':
                    require(
                        label == 'N/A' or fips is not None or label in territory,
                        'incompatible NIU source state'
                    )
                elif status == 'territory':
                    require(label == 'Puerto Rico', 'incompatible PR special')
                else:
                    require(fips is None and label != 'N/A', 'incompatible foreign special')
                    state_doc = document(files['usa_' + state_field.lower()])
                    # Positive DDI label and public document evidence; no numeric-range inference.
                    require(
                        label in state_doc or label in {'Abroad', 'Canada', 'Mexico'}
                        or label in territory, 'foreign label lacks positive evidence'
                    )
                    if label in territory:
                        require(label != 'Puerto Rico', 'PR cannot be foreign')
                        status, reason = 'territory', label + ': ' + reason
            elif fips in SCOPE:
                status = 'applicable'
                reason = '2020 defined area; population allocation retains uncertainty'
            elif label in territory:
                status, reason = 'territory', label + ' outside 50-state/DC scope'
            else:
                raise ValueError('unexplained role state/area pairing')
            if not special:
                require((fips, area) in definitions[role], 'area absent from complete definitions')
            recoded = source['profile'] == 'acs/five_year' and row['component_year'] < 2022 and (
                status == 'applicable' or status == 'territory' and area not in specials.get(
                    role, {}
                )
            )
            require(
                row['area_status'] == status and row['status_reason'] == reason and row[
                    'state_fips'] == fips and row['area_code'] == area and row[
                        'flag_source_geography_recoded'] == recoded,
                'role status/reason/recoding differs from original documentation'
            )
        fields = [
            c for c in own.columns if c not in (
                'profile', 'sample_id', 'release_year', 'component_year', 'role',
                'source_state_code', 'source_area_code'
            )
        ]
        keys = ['acs_sample_id', 'acs_release_year', 'acs_component_year', state_field, area_field]
        grouped = scan.select(
            *[
                pl.col(c).cast(pl.String) if c in (state_field, area_field) else pl.col(c)
                for c in keys
            ], *[pl.col(role + '_' + c).alias(c) for c in fields]
        ).group_by(pl.all()).len().collect()
        expected = own.select(
            pl.col('sample_id').alias('acs_sample_id'),
            pl.col('release_year').alias('acs_release_year'),
            pl.col('component_year').alias('acs_component_year'),
            pl.col('source_state_code').alias(state_field),
            pl.col('source_area_code').alias(area_field), *fields
        )
        require(
            grouped.drop('len').join(expected, on=keys + fields, how='anti', nulls_equal=True
                                     ).is_empty(), 'companion role/status key frequencies differ'
        )
        statuses[role] = scan.group_by(role + '_area_status').len().sort(role + '_area_status'
                                                                         ).collect().to_dicts()
    return statuses

def reference_files(data_dir, reference):
    require(
        re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]*', reference['reference_id']), 'unsafe snapshot ID'
    )
    directory = data_dir / 'raw/references/acs-mapping' / reference['reference_id']
    require(
        digest(directory / 'receipt.json') == reference['receipt_sha256'],
        'reference receipt pin differs'
    )
    receipt = read(directory / 'receipt.json')
    require(receipt == reference['receipt'], 'selected receipt differs from original')
    return {
        kind: relative(directory,
                       Path(item['citation']['path']).name)
        for kind, item in receipt['originals'].items()
    }

def highlighted_occupation_rows(file):
    from xml.etree import ElementTree as ET
    from zipfile import ZipFile
    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    with ZipFile(file) as archive:
        styles = ET.fromstring(archive.read('xl/styles.xml'))
        fills = list(styles.find(ns + 'fills'))
        highlighted = set()
        for number, style in enumerate(styles.find(ns + 'cellXfs')):
            pattern = fills[int(style.get('fillId'))].find(ns + 'patternFill')
            color = pattern.find(ns + 'fgColor') if pattern is not None else None
            if color is not None and color.attrib == {'theme': '7', 'tint': '0.79998168889431442'}:
                require(pattern.get('patternType') == 'solid', 'highlighting pattern differs')
                highlighted.add(str(number))
        sheet = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
        return {
            int(re.search('[0-9]+', c.get('r'))[0])
            for c in sheet.iter(ns + 'c') if c.get('s') in highlighted
        }

def occupation_authorities(files):
    full = {
        r[2]: r[3]
        for r in workbook(files['census_occupation_2018'], '2018 Census Occ Code List')
        if len(r) > 3 and r[2] and re.fullmatch('[0-9]{4}', r[2])
    }
    require(full.get('7550') == '49-9095', 'D4 full Census constituent authority differs')
    primary = workbook(files['pums_occupation_2018'], 'ACS')
    highlighted = highlighted_occupation_rows(files['pums_occupation_2018'])
    require(
        highlighted and any('confidentiality reasons' in str(c) for row in primary
                            for c in row), 'occupation disclosure legend/styles absent'
    )
    result, rejected = {}, []
    for kind, sheet in (
        ('pums_occupation_2018', 'ACS'), ('pums_annual_2024', 'Occupation'), (
            'pums_five_year_2024', 'OCCP & SOCP'
        )
    ):
        rows = workbook(files[kind], sheet)
        root, token, expressions, number = None, None, [], None

        def finish():
            if root is None or root == '9920':
                return
            values = expressions or [token]
            marked = bool(re.search('[XY]', token)) or len(values) > 1
            reason = (
                'disclosure'
                if number in highlighted else 'category_design' if full.get(root, '').replace(
                    '-', ''
                ) == token.replace('-', '') and re.search('[XY]', token) else None
            ) if marked else None
            value = (token.replace('-', ''), sorted(set(values)), reason)
            require(
                root not in result or result[root] == value,
                'occupation editions contradict candidate membership'
            )
            result[root] = value

        for index, row in enumerate(rows, 1):
            if row[0] and re.fullmatch('[0-9]{4}', row[0]):
                finish()
                root, token, number = row[0], row[1].strip(), index
                expressions = []
            elif root and row[0] is None and row[1] and re.fullmatch(
                '[0-9]{2}-[0-9XY]{4}', row[1].strip()
            ):
                value = row[1].strip()
                match = re.match('([0-9]{4}) - ', row[2] or '')
                if match:
                    code = match[1]
                    require(code in full, 'missing explicit Census constituent')
                    if value != full[code]:
                        require(
                            root == '7640' and token == '49-90XX' and index == 707
                            and value == '40-9095' and code == '7550' and row[
                                2] == '7550 - Manufactured building and mobile home installers'
                            and full[code] == '49-9095', 'unapproved D4 constituent mismatch'
                        )
                        rejected.append(
                            {
                                'kind': kind,
                                'original_row': index,
                                'asserted': value,
                                'accepted': full[code]
                            }
                        )
                        value = full[code]
                if not re.search('[XY]', value):
                    expressions.append(value)
        finish()
    require(len(rejected) == 3, 'D4 must be independently checked in all three editions')
    return result, rejected

def leaf_members(expression, nodes, paths):
    # Only named authenticated nodes expand; letter tokens never become wildcards.
    by_code = {r['code']: r for r in nodes}
    leaves = [r for r in nodes if r['level'] in ('national_industry', 'detailed')]

    def named(code):
        require(code in by_code, 'unknown original classification membership node')
        node = by_code[code]
        if node['system'] == 'soc':
            return {r['code'] for r in leaves if node['node_id'] in paths[r['node_id']]}
        if '-' in code:
            first, last = code.split('-')
            return {r['code'] for r in leaves if first <= r['code'][:2] <= last}
        return {r['code'] for r in leaves if r['code'].startswith(code)}

    def union(part):
        part = re.sub(r'\b(?:Part of|Pts\.|pt\.)\s+', '', part)
        part = re.sub(r'\s+and\s+', ',', part)
        part = re.sub(r'\s+', '', part)
        for spelling, sector in (('31,32,33', '31-33'), ('44,45', '44-45'), ('48,49', '48-49')):
            part = part.replace(spelling, sector)
        result = set()
        for value in part.split(','):
            interval = re.fullmatch('([0-9]{6})-([0-9]{6})', value)
            if interval:
                first, last = interval.groups()
                require(
                    first in by_code and last in by_code and first <= last,
                    'invalid original membership interval'
                )
                result.update(r['code'] for r in leaves if first <= r['code'] <= last)
            else:
                result.update(named(value))
        return result

    clauses = expression.split(' exc. ')
    require(len(clauses) in (1, 2), 'unsupported original membership exclusion')
    positive = union(clauses[0])
    negative = union(clauses[1]) if len(clauses) == 2 else set()
    require(negative <= positive and positive - negative, 'invalid original membership exclusion')
    return positive - negative

def candidate_memberships(codes, files, code_directory):
    native = pl.read_parquet(code_directory / 'naics_native_nodes.parquet').to_dicts()
    soc = pl.read_parquet(code_directory / 'soc_nodes.parquet').to_dicts()
    paths = dict(pl.read_parquet(code_directory / 'code_paths.parquet').iter_rows())
    relations = pl.read_parquet(code_directory / 'naics_concordance.parquet').filter(
        pl.col('source_vintage').eq(2017).and_(pl.col('target_vintage').eq(2022))
    )
    forward = defaultdict(set)
    for left, right in relations.select('source_code', 'target_code').iter_rows():
        forward[left].add(right)
    pairs = {}
    for year in (2017, 2022):
        for row in workbook(files[f'pums_industry_{year}'], 'ACS'):
            if len(row) >= 5 and row[2] and re.fullmatch('[0-9]{4}', row[2]) and row[2] != '9920':
                pairs[year, row[2], row[4].strip(' ')] = row[3]
    occupation, rejected = occupation_authorities(files)
    for row in codes.iter_rows(named=True):
        year, system = row['native_vintage'], row['system']
        pair, token = row['paired_census_code'], row['source_token']
        if system == 'naics':
            nodes = [r for r in native if r['vintage'] == year]
            require((year, pair, token) in pairs, 'unmatched industry membership authority')
            members = leaf_members(pairs[year, pair, token], nodes, paths)
        else:
            require(
                pair in occupation and occupation[pair][0] == token,
                'unmatched occupation membership authority'
            )
            _, expressions, reason = occupation[pair]
            members = set() if (pair, token) == ('9830', '559830') else set().union(
                *[leaf_members(e, soc, paths) for e in expressions]
            )
            expected_reasons = [reason] if reason else []
            node_code = token[:2] + '-' + token[2:]
            aggregate = bool(re.search('[XY]', token)) or len(members) > 1 or bool(
                members and node_code not in members
            )
            require(
                row['aggregation_reasons'] == expected_reasons and row['aggregation_reason_status']
                == ('documented' if reason else 'unknown'
                    if aggregate else 'not_applicable'), 'occupation aggregation reasons differ'
            )
        markers = sorted(set(re.findall('[MPSZXY]', token)))
        node_code = token if system == 'naics' else token[:2] + '-' + token[2:]
        aggregate = bool(markers) or len(members) > 1 or bool(members and node_code not in members)
        special = system == 'soc' and (pair, token) == ('9830', '559830')
        kind = ('special' if special else 'source_aggregate' if markers
                else 'whole_node' if aggregate else 'finest')
        require(
            row['flag_aggregate'] == aggregate and row['aggregation_type'] == kind and row[
                'flag_exception'] == ('Z' in markers) and row['flag_reference_ambiguity'] is False,
            'singleton/aggregation/reference provenance differs'
        )
        canonical = set().union(*(forward[c] for c in members)) if year == 2017 else members
        require(
            row['native_finest_candidates'] == sorted(members
                                                      ) and row['canonical_finest_candidates']
            == sorted(canonical), 'candidate membership differs from original reference arithmetic'
        )
        nodes = soc if system == 'soc' else [r for r in native if r['vintage'] == 2022]
        identifiers = {r['code']: r['node_id'] for r in nodes}
        expected_paths = [paths[identifiers[c]] for c in sorted(canonical)]
        require(
            row['canonical_candidate_paths'] == expected_paths,
            'canonical candidate paths differ from authenticated Stage4 graph'
        )
    return {'D4_rejected_constituents': rejected, 'candidate_memberships_equal': True}

def independent_lookup(codes, files):
    '''Check admitted pairs and explicit special/reason semantics against original columns.'''
    pairs = {}
    for year in (2017, 2022):
        for row in workbook(files[f'pums_industry_{year}'], 'ACS'):
            if len(row) >= 5 and row[2] and re.fullmatch('[0-9]{4}', row[2]) and row[2] != '9920':
                pairs['naics', 'naics' + str(year), row[2], row[4].strip(' ')] = row[3]
    occupation = {}
    for row in workbook(files['pums_occupation_2018'], 'ACS'):
        if len(row) >= 3 and row[0] and re.fullmatch('[0-9]{4}', row[0]) and row[1]:
            occupation[row[0], row[1].strip().replace('-', '')] = row[1]
    for row in codes.iter_rows(named=True):
        system, scheme, pair, token = (
            row[c] for c in ('system', 'source_scheme', 'paired_census_code', 'source_token')
        )
        require(
            re.fullmatch('[0-9]{1,6}(?:[MPSZXY][0-9MPSZXY]*)?', token),
            'unparseable classification token'
        )
        special = system == 'soc' and (pair, token) == ('9830', '559830')
        require(
            row['mapping_status'] == ('documented_special' if special else 'mapped'),
            'special classification status differs'
        )
        if special:
            require(
                not row['native_finest_candidates'] and not row['canonical_finest_candidates']
                and row['special_reason'
                        ] == 'military_rank_not_specified', 'special candidates/reason differ'
            )
        else:
            require(
                bool(row['native_finest_candidates']) and bool(row['canonical_finest_candidates']),
                'mapped code lacks candidates'
            )
        if system == 'naics':
            require((system, scheme, pair, token) in pairs, 'unmatched original industry pair')
            expression = pairs[system, scheme, pair, token]
            aggregate = bool(re.search('[MPSZ]', token)) or len(
                row['native_finest_candidates']
            ) > 1 or bool(
                row['native_finest_candidates'] and token not in row['native_finest_candidates']
            )
            require(
                row['aggregation_reason_status'] == ('unknown' if aggregate else 'not_applicable')
                and not row['aggregation_reasons'], 'unknown industry aggregation reason altered'
            )
            require(
                row['flag_partial'] == (
                    'P' in token or bool(re.search(r'(?:Part of|Pts\.|pt\.)', expression))
                ), 'partial industry provenance differs'
            )
        else:
            require((pair, token) in occupation, 'unmatched original occupation pair')
        require(
            row['aggregation_markers'] == sorted(set(re.findall('[MPSZXY]', token))),
            'aggregation markers differ'
        )
        require(
            row['flag_vintage_crosswalk'] == (system == 'naics' and scheme == 'naics2017'),
            'vintage crosswalk provenance differs'
        )

def reconcile(data_dir: Path, run_id: str, outputs_sha256: str, control_dir: Path) -> dict:
    data_dir, control_dir = safe(data_dir), safe(control_dir)
    require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]*', run_id), 'unsafe run ID')
    directory = relative(data_dir, 'derived/acs/mapping/' + run_id)
    inputs = authenticate_bundle(directory, outputs_sha256)
    require(
        set(read(directory / 'outputs.json')) == {n + '.parquet'
                                                  for n in TABLES} | {
                                                      'inputs.json', 'report.json'
                                                  }, 'mapping inventory differs'
    )
    preserved = preservation(data_dir, control_dir)
    selected, compatibility = upstreams(data_dir, inputs)
    files = reference_files(data_dir, inputs['references'])
    geo_run = inputs['selected_upstreams']['request']['geography_run']
    geo_directory = data_dir / 'derived/geography' / geo_run
    counties = reference_geography(data_dir, selected['geography'], geo_directory)
    population, pumas, groups = populations(directory, files, counties)
    table_contracts(directory)
    codes = pl.read_parquet(directory / 'acs_code_lookup.parquet')
    areas = pl.read_parquet(directory / 'acs_area_lookup.parquet')
    independent_lookup(codes, files)
    classification = candidate_memberships(
        codes, files,
        data_dir / 'derived/codes' / inputs['selected_upstreams']['request']['codes_run']
    )
    measurements = {}
    for profile in PROFILES:
        source = inputs['sources'][profile]
        require(source['profile'] == profile, 'source profile differs')
        file = relative(data_dir, source['parquet'])
        check_record(file, source['parquet_record'], 'selected source hash/size differs')
        companion = directory / ('acs_' + profile.split('/')[1] + '_canonical.parquet')
        rows = original_prefix(file, companion)
        source_identity(source, companion)
        measurements[profile] = {
            'rows': rows,
            'codes': code_measurements(file, companion, codes),
            'allocation': allocation_measurements(source, companion),
            'roles': role_measurements(source, companion, areas, files, pumas, groups)
        }
    return {
        'code_frequencies_equal': True,
        'population_reconciliation_equal': True,
        'role_status_counts_equal': True,
        'failure_count': 0,
        'population': population,
        'classification': classification,
        'sources': measurements,
        'preservation': preserved,
        'software_compatibility': compatibility
    }

@app.command('freeze')
def freeze_command(data_dir: Path = typer.Option(...), control_dir: Path = typer.Option(...)):
    print(json.dumps(freeze(data_dir, control_dir), sort_keys=True, allow_nan=False))

@app.command('preservation')
def preservation_command(
    data_dir: Path = typer.Option(...), control_dir: Path = typer.Option(...)
):
    print(json.dumps(preservation(data_dir, control_dir), sort_keys=True, allow_nan=False))

@app.command('reconcile')
def reconcile_command(
    data_dir: Path = typer.Option(...),
    control_dir: Path = typer.Option(...),
    run_id: str = typer.Option(...),
    outputs_sha256: str = typer.Option(...)
):
    print(
        json.dumps(
            reconcile(data_dir, run_id, outputs_sha256, control_dir),
            sort_keys=True,
            allow_nan=False
        )
    )

if __name__ == '__main__':
    app()
