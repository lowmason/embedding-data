'''Independent offline Stage 8 controls; no mapping implementation imports.'''
import csv
import hashlib
import io
import json
import platform
import re
import sys
from collections import defaultdict
from decimal import Decimal
from html.parser import HTMLParser
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
MAX_GEOCORR_BYTES = 32 * 1024 * 1024
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

FOREIGN_PLACE_LABELS = frozenset(
    (
        'Abroad (unknown) or at sea', 'Afghanistan', 'Africa', 'Africa, nec', 'Albania',
        'Argentina', 'Asia, nec', 'Atlantic Islands', 'Australia', 'Austria', 'Azores', 'Belgium',
        'Belize/British Honduras', 'Bolivia', 'Bosnia and Herzegovinia', 'Brazil',
        'British West Indies', 'Bulgaria', 'Canada', 'Central America, nec', 'Chile', 'China',
        'Colombia', 'Costa Rica', 'Cuba', 'Denmark', 'Dominican Republic', 'Eastern Africa',
        'Ecuador', 'Egypt', 'El Salvador', 'England', 'English Canada', 'Estonia', 'Ethiopia',
        'Europe, ns', 'Finland', 'France', 'French Canada', 'Germany', 'Greece', 'Guatemala',
        'Haiti',
        'Honduras', 'Hungary', 'Iceland', 'India', 'Iran', 'Iraq', 'Ireland', 'Israel/Palestine',
        'Italy', 'Jamaica', 'Japan', 'Jordan', 'Kenya', 'Korea', 'Latvia', 'Lebanon', 'Lithuania',
        'Luxembourg', 'Mexico', 'Nepal', 'Netherlands', 'New Zealand', 'Nicaragua', 'Nigeria',
        'Northern Africa', 'Northern Ireland', 'Norway', 'Other Caribbean and North America',
        'Other Eastern Europe', 'Other Northern Europe', 'Other Northern or Eastern Europe',
        'Other South East Asia', 'Other West Indies', 'Other Western Asia', 'Other Western Europe',
        'Pacific Islands (Australia and New Zealand Subregions, not specified, '
        'Oceania and at Sea: ACS)',
        'Pakistan', 'Panama', 'Paraguay', 'Peru', 'Philippines', 'Poland', 'Portugal', 'Romania',
        'Saudi Arabia', 'Scotland', 'South Africa (Union of)', 'South America, nec', 'Spain',
        'Sweden', 'Switzerland', 'Syria', 'Taiwan', 'Thailand', 'Turkey', 'Ukraine',
        'United Arab Emirates', 'Uruguay', 'Venezuela', 'Vietnam', 'Wales', 'Western Africa'
    )
)
FOREIGN_WORK_LABELS = frozenset(
    (
        'Abroad', 'Canada', 'Eastern Asia', 'Europe', 'Iraq', 'Mexico', 'Other Americas',
        'Other, nec', 'South Central, South East, and Western Asia'
    )
)
CT_REFERENCE_NAMES = {
    'ct_tabblock2020': 'tl_2020_09_tabblock20.zip',
    'ct_block_assignment2020': 'BlockAssign_ST09_CT.zip',
    'ct_county_crosswalk': 'ct_cou_to_cousub_crosswalk.txt',
    'tract_puma2020': '2020_Census_Tract_to_2020_PUMA.txt',
    'census_puma_population2020': 'census-puma2020-pop100.html',
    'census_ct_mcd_population2020': 'census-ct-cousub2020-pop100.html',
    'ct_opm_population2020': 'ct-opm-2020-planning-pop.xlsx',
}


def reference_names(version):
    require(version in ('acs-mapping-references-v1', 'acs-mapping-references-v2'),
            'unknown reference version')
    return (dict(REFERENCE_NAMES) if version == 'acs-mapping-references-v1' else
            {**REFERENCE_NAMES, **CT_REFERENCE_NAMES})


RECONCILER_VERSION = 'stage8-independent-v2'

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
                    'acs_ct_population',
                    'acs_mapping_companions', 'acs_mapping_bundle', 'acs_mapping', 'target_inputs',
                    'code_build', 'classification_tables', 'naics_relationships', 'filing_rules',
                    'ita_naics_mapping', 'ita_summary', 'ita_references', 'ita_catalog',
                    'osha_encoding', 'geography_build', 'geography_tables', 'geography_hud',
                    'geography_cli'
                )
            ), 'tests/test_acs_ct_population.py', 'tests/test_acs_source_rules.py'
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

def identities():
    names = (
        'scripts/reconcile_stage8.py', 'tests/test_stage8_reconciliation.py',
        'tests/test_acs_source_rules.py',
        'tests/acs_mapping_fixtures.py', 'tests/test_acs_ct_population.py',
        'pyproject.toml', 'uv.lock'
    )
    return {
        'version': RECONCILER_VERSION,
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
    created = []
    try:
        prefix_file = control_dir / 'manifest-prefix.jsonl'
        with prefix_file.open('xb') as stream:
            created.append(prefix_file)
            stream.write(manifest)
        freeze_file = control_dir / 'freeze.json'
        with freeze_file.open('x', encoding='utf-8') as stream:
            created.append(freeze_file)
            stream.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    except BaseException:
        for file in created:
            file.unlink(missing_ok=True)
        try:
            control_dir.rmdir()
        except OSError:
            pass  # Concurrent/unowned entries must survive this invocation's failure.
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

def _preservation(data_dir: Path, control_dir: Path) -> dict:
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
            receipt['reference_id'] == directory.name, 'snapshot receipt identity differs'
        )
        require(
            re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]*', directory.name),
            'unsafe reference snapshot ID'
        )
        names = reference_names(receipt['reference_version'])
        collection = (None if receipt['reference_version'] == 'acs-mapping-references-v1' else
                      'acs-mapping-references-v2')
        require(all(appended[root + '/' + name]['collection'] == collection
                    for name in set(names.values()) | {'receipt.json'}),
                'snapshot collection/reference version differs')
        requests = receipt['request_files']
        expected_requests = {kind for kind in names if kind.endswith('_request')}
        require(set(requests) == expected_requests, 'receipt request inventory differs')
        for kind, request in requests.items():
            filename = names[kind]
            require(
                request == {
                    'filename': filename,
                    'method': 'GET',
                    **receipt['files'][filename]
                }, 'receipt request record differs'
            )
        for original in receipt['originals'].values():
            require(
                original['authority_url'] == original['citation']['source_url'],
                'receipt original authority/citation differs'
            )
        files = receipt['files']
        require(
            set(receipt['originals']) == set(names) and set(files) == set(
                names.values()
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
        for kind, original in receipt['originals'].items():
            name = names[kind]
            path = root + '/' + name
            require(original['citation']['path'] == path, 'registered original kind/path differs')
            require(
                original['citation'] == appended[path],
                'original citation differs from authenticated manifest suffix'
            )
            require(
                {k: original[k]
                 for k in ('sha256', 'size')} == files[name],
                'registered original/file hash or size differs'
            )
            check_record(relative(directory, name), original, 'original receipt hash/size differs')
        accounted.update(expected_paths | {root + '/receipt.json'})
    require(accounted == set(appended), 'manifest appends not fully receipt-accounted')
    return {
        'manifest_prefix_equal': True,
        'protected_files_equal': True,
        'manifest_appends_accounted': True,
        'appended_record_count': len(suffix)
    }


def preservation(data_dir: Path, control_dir: Path) -> dict:
    try:
        return _preservation(data_dir, control_dir)
    except (KeyError, TypeError, AttributeError, IndexError, OSError) as error:
        raise ValueError('preservation evidence has a malformed record or missing file') from error


def composition_state(value):
    require(isinstance(value, str) and re.fullmatch('0[0-9]{2}', value)
            and value[1:] in SCOPE | {'72'}, 'unknown composition state namespace/code')
    return value[1:]


def authenticate_bundle(directory, pin):
    require(isinstance(pin, str) and re.fullmatch('[0-9a-f]{64}', pin), 'invalid external pin')
    require(digest(directory / 'outputs.json') == pin, 'external inventory pin differs')
    records = read(directory / 'outputs.json')
    actual_names = {f.name for f in directory.iterdir()}
    require(actual_names == set(records) | {'outputs.json'}, 'bundle file set differs')
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

def key_sha256(values):
    return hashlib.sha256(
        json.dumps(values, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    ).hexdigest()

def scalar_controls(row, members, canonical, paths, forward, kind, partial):
    common = []
    for level in zip(*paths):
        if len(set(level)) != 1:
            break
        common.append(level[0])
    scalar = None
    if kind == 'finest' and not partial and len(members) == len(canonical) == 1:
        candidate = next(iter(canonical))
        reverse = {left for left, rights in forward.items() if candidate in rights}
        if row['native_vintage'] != 2017 or reverse == members:
            scalar = candidate
    node = paths[0][-1] if scalar else None
    require(
        row['canonical_common_node_id'] == (
            common[-1] if common else None
        ) and row['canonical_scalar_code'] == scalar and row['canonical_scalar_node_id'] == node,
        'canonical common/scalar assertion differs from independent membership'
    )

def missing_code_controls(scan, prefix, token, system):
    missing = scan.filter(pl.col(token).is_null())
    strings = (
        'code_lookup_id', 'native_node_id', 'canonical_common_node_id', 'canonical_scalar_code',
        'canonical_scalar_node_id', 'special_reason', 'rule_version'
    )
    lists = (
        'native_finest_candidates', 'canonical_finest_candidates', 'canonical_candidate_paths',
        'aggregation_markers', 'aggregation_reasons', 'reference_ids', 'reference_locators'
    )
    flags = (
        'flag_aggregate', 'flag_partial', 'flag_exception', 'flag_vintage_crosswalk',
        'flag_reference_ambiguity'
    )
    expected_native = pl.col(prefix + '_delivered_scheme').str.extract('([0-9]{4})$',
                                                                       1).cast(pl.Int64)
    expressions = [pl.col(prefix + '_' + c).is_null() for c in strings]
    expressions.extend(pl.col(prefix + '_' + c).list.len().eq(0) for c in lists)
    expressions.extend(pl.col(prefix + '_' + c).eq(False) for c in flags)
    expressions.extend(
        (
            pl.col(prefix + '_mapping_status').eq('missing'), pl.col(prefix
                                                                     + '_source_token').is_null(),
            pl.col(prefix + '_aggregation_type').eq('missing'),
            pl.col(prefix + '_aggregation_reason_status').eq('not_applicable'),
            pl.col(prefix + '_native_vintage').eq(expected_native),
            pl.col(prefix + '_canonical_vintage').eq(2022 if system == 'naics' else 2018)
        )
    )
    all_true(missing, pl.all_horizontal(expressions), 'missing classification annotations differ')

def role_allocation_controls(scan, county_factors, role):
    support = county_factors.group_by('factor_key').agg(
        pl.col('intersection_population').gt(0).sum().alias('__positive_support')
    )
    joined = scan.join(
        support.lazy(),
        left_on=role + '_factor_key',
        right_on='factor_key',
        how='left',
        validate='m:1'
    )
    applicable = pl.col(role + '_area_status').eq('applicable')
    split = pl.when(applicable).then(pl.col('__positive_support').gt(1)).otherwise(False)
    all_true(
        joined,
        pl.col(role + '_flag_geographic_allocation').eq(applicable).and_(
            pl.col(role + '_flag_fractional_split').eq(split)
        ), 'role geographic allocation/split flag differs from independent positive support'
    )

def observed_lookup_coverage(measurements, codes):
    expected = set()
    for measured in measurements.values():
        for prefix, system in (('industry', 'naics'), ('occupation', 'soc')):
            for row in measured['codes'][prefix]['frequency_partitions']:
                if row['source_token'] is not None:
                    scheme = (
                        'naics2017' if row['YEAR'] == 2022 else 'naics2022'
                    ) if system == 'naics' else 'soc2018'
                    expected.add((system, scheme, row['paired_code'], row['source_token']))
    actual = set(
        codes.select('system', 'source_scheme', 'paired_census_code', 'source_token').iter_rows()
    )
    require(
        actual == expected, 'code lookup key coverage differs from original source frequencies'
    )

def emit(operation, *args):
    try:
        result = operation(*args)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(
            json.dumps({
                'status': 'failed',
                'error': str(error)
            }, allow_nan=False),
            file=sys.stderr
        )
        raise typer.Exit(1) from None
    print(json.dumps(result, sort_keys=True, allow_nan=False))

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
                    if column in ('reference_ids', 'reference_locators'):
                        require(bool(value), 'reference provenance list is empty')
                    if dtype == pl.List(pl.String):
                        require(
                            value == sorted(set(value)), 'reference/candidate set ordering differs'
                        )
        if 'factor_key' in frame.columns:
            for row in frame.iter_rows(named=True):
                expected = key_sha256(
                    [row['area_type'], row['state_fips'], row['area_code'], 2020]
                )
                if name == 'acs_area_lookup' and row['area_status'] != 'applicable':
                    expected = None
                require(row['factor_key'] == expected, 'factor key identity differs')
        if name in ('acs_code_lookup', 'acs_area_lookup'):
            version = 'acs-code-rules-v1' if name == 'acs_code_lookup' else 'acs-area-rules-v1'
            require(frame['rule_version'].eq(version).all(), 'mapping rule version differs')
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
    require(
        digest(receipt_file) == request['ipums_references_receipt_sha256'],
        'selected Stage7 reference receipt pin differs'
    )
    current_software(inputs['software'], EXECUTING_NAMES)
    current_software(selected['ipums']['software'], STAGE7_NAMES)
    diagnostics = []
    for key in ('codes', 'geography'):
        upstream = selected[key]
        require(
            inputs['selected_upstreams']['provenance'][key]['inputs'] == upstream,
            'historical upstream inventory copy differs'
        )
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

def geocorr_text(file):
    require(file.name in {'geocorr_intersections.csv', 'geocorr_puma_totals.csv',
                         'geocorr_county_totals.csv'}, 'unknown registered Geocorr CSV')
    body = safe(file).read_bytes()
    require(len(body) <= MAX_GEOCORR_BYTES, 'Geocorr original exceeds byte bound')
    try:
        text, decoder = body.decode('utf-8-sig'), 'utf-8-sig'
    except UnicodeDecodeError:
        try:
            text, decoder = body.decode('cp1252'), 'cp1252'
        except UnicodeDecodeError as error:
            raise ValueError('unsupported Geocorr CSV encoding') from error
    require('\x00' not in text, 'unsupported Geocorr CSV encoding: NUL text')
    return text, decoder


def csv_rows(file):
    text, _ = geocorr_text(file)
    rows = list(csv.reader(io.StringIO(text, newline=''), strict=True))
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


def geocorr_rounding_assertion(pin, number, row, column, numerator, denominator):
    require(denominator > 0, 'nonpositive population denominator')
    error = abs(Decimal(row[column]) - Decimal(numerator) / Decimal(denominator))
    known = {
        1136: ('16', '01300', '16005', 'afact', '0.669 ', 87018, 130062),
        2428: ('30', '00500', '30013', 'afact', '0.5432 ', 84414, 155387),
        2662: ('34', '01404', '34013', 'afact2', '0.1252', 108182, 863728),
    }
    observed = (row['state'], row['puma22'], row['county'], column, row[column],
                numerator, denominator)
    if (pin == '9d7ef74ba87b2b3bd4b22303c4c0910a4da0bca966721232c0e9b4461737e04d'
            and number in known and column == known[number][3]):
        require(known[number] == observed, 'D7 rounding assertion tuple differs')
    if error <= ROUNDING:
        return None
    require(pin == '9d7ef74ba87b2b3bd4b22303c4c0910a4da0bca966721232c0e9b4461737e04d'
            and known.get(number) == (row['state'], row['puma22'], row['county'],
                                     column, row[column], numerator, denominator),
            'published rounding outside decimal bound')
    return {'original_sha256': pin, 'row': number, 'state_fips': row['state'],
            'puma_code': row['puma22'], 'county_geoid': row['county'], 'column': column,
            'literal_token': row[column], 'numerator': numerator, 'denominator': denominator,
            'absolute_error': str(error), 'cause': 'unknown', 'disposition': 'rejected_assertion',
            'reference_locator': f'geocorr_intersections:csv:row:{number}'}

def reference_geography(data_dir, upstream, directory):
    '''Authenticate the complete 2025 original before domestic-scope comparisons.'''
    import io
    from zipfile import ZipFile
    original = upstream['references']['counties_2025']['relative']
    matches = [
        r for r in upstream['raw'] if r['path'] == original or r['path'].endswith('/' + original)
    ]
    require(len(matches) == 1, 'county original citation missing or ambiguous')
    file = relative(data_dir / 'raw', matches[0]['path'])
    check_record(file, matches[0], 'county original hash/size differs')
    with ZipFile(file) as archive:
        require(
            archive.namelist() == ['2025_Gaz_counties_national.txt'],
            'county original archive member differs'
        )
        body = archive.read('2025_Gaz_counties_national.txt').decode('utf-8-sig')
    rows = csv.DictReader(io.StringIO(body), delimiter='|')
    require({'USPS', 'GEOID', 'NAME'} <= set(rows.fieldnames), 'county original header differs')
    counties = set()
    for row in rows:
        if not any(v and v.strip() for v in row.values()):
            continue
        geoid = row['GEOID'].strip()
        require(
            re.fullmatch('[0-9]{5}', geoid) and geoid[:2] in SCOPE | {'72'}
            and geoid not in counties, 'invalid/duplicate full county inventory code'
        )
        counties.add(geoid)
    require(
        {c
         for c in counties if c.startswith('09')} == {f'091{i}0'
                                                      for i in range(1, 10)},
        '2025 county inventory must preserve all nine CT planning regions'
    )
    selected = pl.read_parquet(directory / 'county_reference.parquet')
    require(
        set(selected['county_geoid']) == {c
                                          for c in counties if c[:2] in SCOPE},
        'selected county table differs from complete original domestic scope'
    )
    return counties

def ct_population(files):
    '''Reconstruct D9 from originals with independent byte/CSV/HTML/workbook checks.'''
    import stat
    import struct
    from zipfile import BadZipFile, ZipFile

    limits = dict(zip(CT_REFERENCE_NAMES, (64 * 1024 * 1024, 2 * 1024 * 1024,
                      32 * 1024, 2 * 1024 * 1024, 2 * 1024 * 1024, 256 * 1024, 32 * 1024),
                      strict=True))
    require(all(0 < files[k].stat().st_size <= v for k, v in limits.items()),
            'CT original byte bound differs')

    def unsigned(value, width=None):
        require(isinstance(value, str) and re.fullmatch(
            '[0-9]+' if width is None else '[0-9]{' + str(width) + '}', value),
            'invalid CT integer/code token')
        return int(value) if width is None else value

    def member(file, name, expected, compression, cap):
        require(0 < file.stat().st_size <= cap, 'CT archive byte bound differs')
        try:
            with ZipFile(file) as archive:
                entries = archive.infolist()
                require(len(entries) == len(expected)
                        and {m.filename for m in entries} == expected,
                        'CT archive exact member inventory differs')
                for m in entries:
                    mode = m.external_attr >> 16
                    require('/' not in m.filename and '\\' not in m.filename and not m.is_dir()
                            and not stat.S_ISLNK(mode)
                            and (not stat.S_IFMT(mode) or stat.S_ISREG(mode))
                            and not m.flag_bits & 1 and m.compress_type == compression
                            and 0 < m.file_size <= cap
                            and 0 < m.compress_size <= m.file_size + 1024,
                            'unsafe CT archive member')
                require(archive.getinfo(name).file_size <= 8 * 1024 * 1024,
                        'CT selected member too large')
                return archive.read(name)
        except (BadZipFile, OSError, RuntimeError) as error:
            raise ValueError('invalid CT archive') from error

    def csv_table(body, header, delimiter=','):
        reader = csv.DictReader(io.StringIO(body.decode('utf-8-sig'), newline=''),
                                delimiter=delimiter, strict=True)
        require([c.replace('\n', ' ').strip() for c in reader.fieldnames] == header,
                'CT source header differs')
        rows = []
        for row in reader:
            require(None not in row, 'CT CSV width differs')
            rows.append({k.replace('\n', ' ').strip(): v for k, v in row.items()})
        return rows

    def controls(file, header):
        parser = OccupationHTMLRows()
        parser.feed(file.read_text(encoding='utf-8'))
        require(parser.rows[0] == header, 'Census control header differs')
        result = {}
        for values in parser.rows[1:]:
            require(len(values) == len(header), 'Census control width differs')
            row = dict(zip(header, values, strict=True))
            key = unsigned(row['GEOID'], 7 if 'PUMA' in row else 10)
            expected = unsigned(row['STATE'], 2) + (unsigned(row['PUMA'], 5) if 'PUMA' in row else
                       unsigned(row['COUNTY'], 3) + unsigned(row['COUSUB'], 5))
            require(key == expected and key not in result, 'duplicate/inconsistent CT control key')
            unsigned(row['POP100'])
            result[key] = row
        return result

    tiger_names = {f'tl_2020_09_tabblock20.{x}' for x in (
        'cpg', 'dbf', 'prj', 'shp', 'shp.ea.iso.xml', 'shx', 'shp.iso.xml')}
    tiger = files['ct_tabblock2020']
    require(member(tiger, 'tl_2020_09_tabblock20.cpg', tiger_names, 0, 64 * 1024 * 1024)
            == b'UTF-8', 'CT encoding differs')
    body = member(tiger, 'tl_2020_09_tabblock20.dbf', tiger_names, 0, 64 * 1024 * 1024)
    require(len(body) >= 578 and body[0] == 3 and body[29] == 0, 'CT DBF header differs')
    count, start, size = struct.unpack_from('<IHH', body, 4)
    require(count == 49926 and (start, size) == (577, 137)
            and len(body) == start + size * count + 1 and body[start - 1] == 13 and body[-1] == 26,
            'CT DBF physical bounds differ')
    expected_fields = (
        ('STATEFP20', 'C', 2), ('COUNTYFP20', 'C', 3), ('TRACTCE20', 'C', 6),
        ('BLOCKCE20', 'C', 4), ('GEOID20', 'C', 15), ('NAME20', 'C', 10),
        ('MTFCC20', 'C', 5), ('UR20', 'C', 5), ('UACE20', 'C', 5), ('UATYPE20', 'C', 5),
        ('FUNCSTAT20', 'C', 1), ('ALAND20', 'N', 14), ('AWATER20', 'N', 14),
        ('INTPTLAT20', 'C', 11), ('INTPTLON20', 'C', 12), ('HOUSING20', 'N', 12),
        ('POP20', 'N', 12))
    offsets, offset = {}, 1
    for i, (name, kind, width) in enumerate(expected_fields):
        field = body[32 + 32 * i:64 + 32 * i]
        require((field[:11].split(b'\0')[0].decode('ascii'), chr(field[11]), field[16], field[17])
                == (name, kind, width, 0), 'CT DBF descriptors differ')
        offsets[name] = slice(offset, offset + width)
        offset += width
    blocks = {}
    for i in range(count):
        raw = body[start + i * size:start + (i + 1) * size]
        require(raw[0] == 32, 'CT deleted/invalid record')
        keys = [raw[offsets[n]].decode('ascii').strip(' ') for n in (
            'STATEFP20', 'COUNTYFP20', 'TRACTCE20', 'BLOCKCE20', 'GEOID20')]
        for token, width in zip(keys, (2, 3, 6, 4, 15), strict=True):
            unsigned(token, width)
        require(keys[0] == '09' and ''.join(keys[:4]) == keys[4] and keys[4] not in blocks,
                'CT duplicate/inconsistent block key')
        blocks[keys[4]] = unsigned(raw[offsets['POP20']].decode('ascii').strip(' '))
    baf_names = {f'BlockAssign_ST09_CT_{n}.txt' for n in (
        'INCPLACE_CDP', 'AIANNH', 'VTD', 'MCD', 'CD', 'SLDL', 'SDSEC', 'SLDU', 'SDELM', 'SDUNI')}
    baf_rows = csv_table(member(files['ct_block_assignment2020'], 'BlockAssign_ST09_CT_MCD.txt',
                        baf_names, 8, 2 * 1024 * 1024), ['BLOCKID', 'COUNTYFP', 'COUSUBFP'], '|')
    baf = {}
    for row in baf_rows:
        key = unsigned(row['BLOCKID'], 15)
        town = '09' + unsigned(row['COUNTYFP'], 3) + unsigned(row['COUSUBFP'], 5)
        require(key.startswith(town[:5]) and key not in baf, 'CT BAF key differs')
        baf[key] = town
    require(len(baf) == 49926 and set(baf) == set(blocks), 'CT BAF/block inventories differ')
    tract_rows = csv_table(files['tract_puma2020'].read_bytes(),
                           ['STATEFP', 'COUNTYFP', 'TRACTCE', 'PUMA5CE'])
    tracts = {}
    for row in tract_rows:
        key = (unsigned(row['STATEFP'], 2) + unsigned(row['COUNTYFP'], 3)
               + unsigned(row['TRACTCE'], 6))
        require(key not in tracts, 'duplicate CT/national tract key')
        tracts[key] = unsigned(row['PUMA5CE'], 5)
    require(len(tracts) == 85452 and sum(k.startswith('09') for k in tracts) == 883,
            'national tract control coverage differs')
    xheader = ('STATEFP (INCITS38)|OLD_COUNTYFP (INCITS31)|OLD_COUNTY_NAMELSAD|'
               'NEW_COUNTYFP (INCITS31)|NEW_COUNTY_NAMELSAD|COUSUBFP|OLD_COUSUB_GEOID|'
               'NEW_COUSUB_GEOID|COUSUB_NAMELSAD|COUSUBNS (INCITS446)|COUSUB_LSAD|'
               'COUSUB_FUNCSTAT|COUSUB_CLASSFP').split('|')
    crosswalk, glossary = defaultdict(list), []
    crosswalk_rows = csv_table(files['ct_county_crosswalk'].read_bytes(), xheader, '|')
    for row in crosswalk_rows:
        if row[xheader[0]] != '09':
            require(all(v is None for k, v in row.items() if k != xheader[0]),
                    'CT glossary shape differs')
            glossary.append(row[xheader[0]])
            continue
        require(not glossary, 'CT body follows glossary')
        town = '09' + unsigned(row[xheader[1]], 3) + unsigned(row['COUSUBFP'], 5)
        county = '09' + unsigned(row[xheader[3]], 3)
        require(row['OLD_COUSUB_GEOID'] == town and row['NEW_COUSUB_GEOID'] ==
                county + row['COUSUBFP'] and county not in [r[0] for r in crosswalk[town]],
                'CT crosswalk duplicate/component key differs')
        crosswalk[town].append((county, row['NEW_COUNTY_NAMELSAD']))
    require(len(glossary) == 9 and glossary[0] == 'GLOSSARY', 'CT glossary differs')
    require(len(crosswalk) == 173 and sum(map(len, crosswalk.values())) == 174,
            'CT crosswalk coverage differs')
    pumas, counties, towns, relations = (defaultdict(int) for _ in range(4))
    excluded = []
    for block, pop in blocks.items():
        town = baf[block]
        towns[town] += pop
        require(block[:11] in tracts, 'CT block tract unmatched')
        puma = tracts[block[:11]]
        targets = crosswalk.get(town, [])
        if len(targets) != 1:
            require(pop == 0 and town == '0900100000' and sorted(t[0] for t in targets) ==
                    ['09120', '09190'], 'positive/unexplained CT ambiguity')
            excluded.append({'block': block, 'population': pop, 'old_town': town})
            continue
        county = targets[0][0]
        pumas[puma] += pop
        counties[county] += pop
        relations[puma, county] += pop
    require(len(relations) == 26 and all(n > 0 for n in relations.values())
            and len(excluded) == 9, 'CT relation/zero-exclusion coverage differs')
    pc = controls(files['census_puma_population2020'],
                  ('MTFCC OID GEOID STATE PUMA BASENAME NAME LSADC FUNCSTAT POP100 HU100 '
                   'AREALAND AREAWATER CENTLAT CENTLON INTPTLAT INTPTLON').split())
    mc = controls(files['census_ct_mcd_population2020'],
                  ('MTFCC OID GEOID STATE COUNTY COUSUB COUSUBNS BASENAME NAME LSADC FUNCSTAT '
                   'COUSUBCC POP100 HU100 AREALAND AREAWATER UR CNECTA NECTA NECTADIV '
                   'CENTLAT CENTLON INTPTLAT INTPTLON').split())
    require(len(pc) == 2487 and len(mc) == 173 and all(r['STATE'] == '09' for r in mc.values()),
            'Census control coverage differs')
    require(dict(pumas) == {k[2:]: unsigned(r['POP100']) for k, r in pc.items()
                           if r['STATE'] == '09'} and len(pumas) == 25,
            'CT independent PUMA marginals differ')
    require(set(towns) <= set(mc)
            and all(towns[k] == unsigned(r['POP100']) for k, r in mc.items()),
            'CT independent MCD marginals differ')
    book = fastexcel.read_excel(files['ct_opm_population2020'].read_bytes())
    require(book.sheet_names == ['Sheet1'], 'OPM worksheet differs')
    rows = book.load_sheet(0, header_row=None, dtypes='string').to_polars().rows()
    require(rows[:3] == [(None, '2020 Census Population By Planning Region', None, None, None),
                         (None, None, None, None, None),
                         ('TOWN', 'Planning Region', '2020 Population',
                          'Population by Planning Region', None)], 'OPM header differs')
    town_controls, region_controls = {}, {}
    names = {'Capitol': ('09110', 'Capitol'),
             'Greater Bridgeport': ('09120', 'Greater Bridgeport'),
             'Lower Connecticut River Valley': ('09130', 'Lower CT River Valley'),
             'Naugatuck Valley': ('09140', 'Naugatuck Valley'),
             'Northeastern Connecticut': ('09150', 'Northeast CT'),
             'Northwest Hills': ('09160', 'Northwest Hills'),
             'South Central Connecticut': ('09170', 'South Central'),
             'Southeastern Connecticut': ('09180', 'Southeastern CT'),
             'Western Connecticut': ('09190', 'Western CT')}
    summaries = {label: code for code, label in names.values()}
    summaries['Northeastern CT'] = summaries.pop('Northeast CT')
    for name, label, value, total, summary in rows[3:]:
        if name and label:
            require(name not in town_controls, 'duplicate OPM town')
            town_controls[name] = label, unsigned(value)
        if summary and total:
            require(summary in summaries and summaries[summary] not in region_controls,
                    'OPM summary differs')
            region_controls[summaries[summary]] = unsigned(total)
    require(len(town_controls) == 169 and len(region_controls) == 9,
            'OPM control coverage differs')
    opm_sums = defaultdict(int)
    for key, row in mc.items():
        pop = unsigned(row['POP100'])
        if row['COUSUB'] == '00000':
            require(pop == 0, 'positive pseudo-MCD control')
            continue
        require(row['BASENAME'] in town_controls and len(crosswalk[key]) == 1,
                'OPM town absent/ambiguous')
        county, label = crosswalk[key][0]
        require(label.endswith(' Planning Region') and label[:-16] in names,
                'Census region title differs')
        expected_county, expected_label = names[label[:-16]]
        require(county == expected_county and town_controls[row['BASENAME']] ==
                (expected_label, pop), 'OPM town population/region differs')
        opm_sums[county] += pop
    require(dict(counties) == dict(opm_sums) == region_controls and
            sum(pumas.values()) == sum(blocks.values()) == 3605944,
            'CT region/state control differs')
    outside = {k: unsigned(r['POP100']) for k, r in pc.items() if r['STATE'] == '66'}
    require(outside == {'6600100': 153836}, 'extra-universe PUMA control differs')
    national = {(r['STATE'], r['PUMA']): unsigned(r['POP100']) for r in pc.values()
                if r['STATE'] != '66'}
    indexes = defaultdict(lambda: defaultdict(set))
    baf_positions = {r['BLOCKID']: n for n, r in enumerate(baf_rows, 2)}
    tract_positions = {r['STATEFP'] + r['COUNTYFP'] + r['TRACTCE']: n
                       for n, r in enumerate(tract_rows, 2)}
    crosswalk_positions = {(r['OLD_COUSUB_GEOID'], '09' + r[xheader[3]]): n
                           for n, r in enumerate(crosswalk_rows, 2) if r[xheader[0]] == '09'}
    for n, block in enumerate(blocks, 1):
        targets = crosswalk.get(baf[block], [])
        if len(targets) != 1:
            continue
        key = tracts[block[:11]], targets[0][0]
        for prefix, number in (
            ('ct_tabblock2020:tl_2020_09_tabblock20.dbf:record', n),
            ('ct_block_assignment2020:BlockAssign_ST09_CT_MCD.txt:row', baf_positions[block]),
            ('tract_puma2020:csv:row', tract_positions[block[:11]]),
            ('ct_county_crosswalk:csv:row', crosswalk_positions[baf[block], targets[0][0]]),
        ):
            indexes[key][prefix].add(number)
    source_locators = {}
    from itertools import groupby
    for key, sources in indexes.items():
        targets = []
        for prefix, numbers in sorted(sources.items()):
            ranges = []
            for _, group in groupby(enumerate(sorted(numbers)), lambda pair: pair[1] - pair[0]):
                values = [pair[1] for pair in group]
                ranges.append(str(values[0]) if len(values) == 1 else f'{values[0]}-{values[-1]}')
            targets.append(prefix + '-ranges=' + ','.join(ranges))
        source_locators[key] = targets
    return {'source_locators': source_locators,
            'relations': dict(relations), 'pumas': dict(pumas), 'counties': dict(counties),
            'national_pumas': national, 'state_population': sum(pumas.values()),
            'zero_population_exclusions': sorted(excluded, key=lambda r: r['block']),
            'block_records': len(blocks), 'mcd_controls': len(mc), 'opm_towns': len(town_controls)}


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
    original_pumas, original_counties = dict(pumas), dict(counties)
    ct = ct_population(files) if 'ct_tabblock2020' in files else None
    ct_assertions = []
    if ct is not None:
        keyed(intersections, ('state', 'puma22', 'county'), ('pop20',))
        original_puma_sums, original_county_sums = defaultdict(int), defaultdict(int)
        for original in intersections:
            population = integer(original['pop20'])
            original_puma_sums[original['state'], original['puma22']] += population
            original_county_sums[original['state'], original['county']] += population
        require(dict(original_puma_sums) == original_pumas
                and dict(original_county_sums) == original_counties
                and all(n > 0 for n in (*original_pumas.values(), *original_counties.values())),
                'original Geocorr integer controls differ before CT replacement')
    rejected_rounding = []
    geocorr_pin = digest(files['geocorr_intersections'])
    for number, row in enumerate(intersections, 3):
        state, puma, county = row['state'], row['puma22'], row['county']
        for column, denominator in [('afact', original_pumas[state, puma]),
                                    ('afact2', original_counties[state, county])]:
            assertion = geocorr_rounding_assertion(
                geocorr_pin, number, row, column, integer(row['pop20']), denominator)
            if assertion:
                rejected_rounding.append(assertion)
    if ct is not None:
        require(set(pumas) == set(ct['national_pumas']) and all(
            pop == ct['national_pumas'][key] for key, pop in pumas.items() if key[0] != '09'),
            'national PUMA/non-CT controls differ')
        old_ct = {(r['puma22'], r['county']): r for r in intersections if r['state'] == '09'}
        require(len(old_ct) == 27 and len(ct['relations']) == 26 and
                set(ct['relations']) <= set(old_ct), 'CT relation published provenance absent')
        for key, row in sorted(old_ct.items()):
            ct_assertions.append({'puma_code': key[0], 'county_geoid': key[1],
                                  'original_population': integer(row['pop20']),
                                  'accepted_population': ct['relations'].get(key),
                                  'literal_afact': row['afact'], 'literal_afact2': row['afact2']})
        updated = []
        for row in intersections:
            row = dict(row)
            if row['state'] == '09':
                key = row['puma22'], row['county']
                if key not in ct['relations']:
                    continue
                row['pop20'] = str(ct['relations'][key])
            updated.append(row)
        intersections = updated
        pumas = {**pumas, **{('09', k): v for k, v in ct['pumas'].items()}}
        counties = {**counties, **{('09', k): v for k, v in ct['counties'].items()}}
    require(set(s for s, _ in pumas) <= SCOPE | {'72'}, 'invalid reference state')
    require(
        {c
         for _, c in counties} <= county_inventory,
        'county population control absent from complete 2025 original'
    )
    require(
        all(
            re.fullmatch('[0-9]{2}', st) and re.fullmatch('[0-9]{5}', code)
            for st, code in set(pumas) | set(counties)
        ), 'reference code width differs'
    )
    keyed(intersections, ('state', 'puma22', 'county'), ('pop20', ))
    sums_puma, sums_county = defaultdict(int), defaultdict(int)
    groups = keyed(
        [
            {
                'state': r[0],
                'puma': r[1],
                'group_state': composition_state(r[2]),
                'group': r[3]
            } for r in workbook(files['puma_composition_2020'], 'PUMA_POWPUMA_MIGPUMA')[1:]
        ], ('state', 'puma'), ('group_state', 'group')
    )
    county_groups = keyed(
        [
            {
                'state': r[0],
                'county': r[0] + r[1],
                'group_state': composition_state(r[2]),
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
    published = {}
    for row in intersections:
        state, puma, county = row['state'], row['puma22'], row['county']
        pop = integer(row['pop20'])
        require(county[:2] == state, 'county namespace differs')
        require(
            groups[state, puma] == county_groups[state, county], 'county/group direction differs'
        )
        sums_puma[state, puma] += pop
        sums_county[state, county] += pop
        published[state, puma, county] = float(row['afact']), float(row['afact2'])
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
        expected_published = published[row['state_fips'], row['area_code'], row['county_geoid']
                                       ] if row['area_type'] == 'residence' else (None, None)
        require(
            (row['published_area_factor'], row['published_county_factor']) == expected_published,
            'published county factors differ from original columns'
        )
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
    msa_published = {}
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
            msa_published[key] = float(row[10]), float(row[9])
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
            (row['published_percent_puma'], row['published_percent_msa']
             ) == msa_published[row['state_fips'], row['puma_code'], row['msa_code']],
            'published MSA percentages differ from original columns'
        )
        require(
            row['flag_geographic_allocation'] and row['flag_fractional_split'] == (n != p),
            'MSA allocation provenance differs'
        )
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
        'published_rounding_decimal_bound': str(ROUNDING),
        'rejected_geocorr_rounding_assertions': rejected_rounding,
        'ct_population_basis': (None if ct is None else {
            'state_population': ct['state_population'], 'block_records': ct['block_records'],
            'zero_population_exclusions': ct['zero_population_exclusions'],
            'geocorr_assertions': ct_assertions, 'accepted_basis': 'Census 2020 block POP20'}),
        'geocorr_selected_decoders': {
            kind: geocorr_text(files[kind])[1] for kind in
            ('geocorr_intersections', 'geocorr_puma_totals', 'geocorr_county_totals')
        },
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
    require(
        actual.get('source_row') == pl.UInt64 and actual.get('source_parquet_sha256') == pl.String,
        'source identity dtype differs'
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
    expected_samples = {
        'acs/core': {'us2023a', 'us2024a'},
        'acs/vintage': {'us2022a'},
        'acs/five_year': {'us2024c'}
    }
    require(
        set(source['definition']['samples']) == expected_samples[profile],
        'source definition product/sample identity differs'
    )
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
    sample = pl.col('SAMPLE').cast(pl.String).replace_strict(mapping)
    valid_component = component.is_between(2020, 2024) if five else component.eq(release)
    all_true(
        scan,
        sample.str.slice(2, 4).cast(pl.Int64).eq(release).and_(valid_component),
        'source release/component identity is unsupported'
    )
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
        missing_code_controls(scan, prefix, token, system)
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
    used = False
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
        used = used or available
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
    citations = [r for r in source['raw_citations'] if r['path'].endswith('.xml')]
    require(len(citations) == 1, 'allocation requires one authenticated DDI citation')
    references = ['ddi:sha256:' + citations[0]['sha256']] if used else []
    all_true(
        scan,
        pl.col('source_flag_reference_ids').eq_missing(
            pl.lit(references, dtype=pl.List(pl.String))
        ), 'source flag citation assertion differs'
    )
    return result

def document(file):
    import html
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', file.read_text())))

def role_measurements(source, companion, areas, files, pumas, groups, county_factors):
    scan = pl.scan_parquet(companion)
    domestic = categories(source, 'STATEFIP')
    by_label = {label: code for code, label in domestic.items() if code in SCOPE | {'72'}}
    require(
        len(by_label) == sum(c in SCOPE | {'72'}
                             for c in domestic), 'ambiguous domestic DDI labels'
    )
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
            require(
                re.fullmatch('[0-9]{1,' + str(width) + '}',
                             str(row['source_state_code'])) and re.fullmatch(
                                 '[0-9]{1,5}', str(row['source_area_code'])
                             ), 'unparseable source geographic role code'
            )
            state, area = str(row['source_state_code']).zfill(width), str(row['source_area_code']
                                                                          ).zfill(5)
            require(
                row['area_type'] == ('residence' if role == 'residence' else
                                     'work_migration') and row['source_allocation_evidence_status']
                == 'unavailable', 'role type/source allocation availability differs'
            )
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
                    positives = (FOREIGN_WORK_LABELS if role == 'workplace'
                                 else FOREIGN_PLACE_LABELS)
                    require(
                        label in positives or label in territory and label != 'Puerto Rico',
                        'foreign label lacks positive documented category evidence'
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
        require(
            expected.join(grouped.drop('len'), on=keys + fields, how='anti',
                          nulls_equal=True).is_empty(), 'extra area lookup keys are unobserved'
        )
        role_allocation_controls(scan, county_factors, role)
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
            require(
                not re.search('[XY]', token) or bool(expressions),
                'letter occupation category lacks explicit terminal members'
            )
            if not expressions:
                expected = 'none' if (root, token) == ('9830', '55-9830') else token
                require(full.get(root) == expected, 'full Census occupation pair differs')
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

def native_identifier(nodes, members, token_code, paths):
    if not members:
        return None
    identifiers = {r['code']: r['node_id'] for r in nodes}
    if token_code in identifiers:
        return identifiers[token_code]
    native_paths = []
    for member in sorted(members):
        if nodes[0]['system'] == 'soc':
            native_paths.append(paths[identifiers[member]])
            continue
        ancestors = [
            r for r in nodes if (
                r['code'][:2] <= member[:2] <= r['code'][-2:]
                if '-' in r['code'] else member.startswith(r['code'])
            )
        ]
        ancestors.sort(key=lambda r: 2 if '-' in r['code'] else len(r['code']))
        require(ancestors and ancestors[-1]['code'] == member, 'native hierarchy leaf absent')
        native_paths.append([r['node_id'] for r in ancestors])
    common = []
    for level in zip(*native_paths):
        if len(set(level)) != 1:
            break
        common.append(level[0])
    return common[-1] if common else None

def geographic_identifiers(directory, geographic_directory):
    counties = {
        r['county_geoid']: r['county_id']
        for r in pl.read_parquet(geographic_directory / 'county_reference.parquet').to_dicts()
    }
    msas = {
        r['cbsa_code']: r['cbsa_id']
        for r in pl.read_parquet(geographic_directory / 'cbsa_reference.parquet').to_dicts()
        if r['cbsa_type'] == 'metropolitan'
    }
    nodes = set(pl.read_parquet(geographic_directory / 'geography_nodes.parquet')['node_id'])
    for name, natural, identifier, authority in (
        ('puma_county_factors', 'county_geoid', 'county_node_id', counties), (
            'puma_msa_factors', 'msa_code', 'msa_node_id', msas
        )
    ):
        for row in pl.read_parquet(directory / (name + '.parquet')).iter_rows(named=True):
            require(
                row[natural] in authority and row[identifier] == authority[row[natural]
                                                                           ] and row[identifier]
                in nodes, 'geographic node differs from authenticated natural identity'
            )

D8_OCCUPATION_HTML_PIN = '61862b9ac0e7bfc4500cc28c3664c50adfc8dc51517c7d81f0192fa37e73725c'
D8_SUPPORT_PINS = {
    'ipums_occ_pairs': 'f95672c481af85302bc2f445888e2f5e493afffa6d88a5ca042b66a39cfc34f1',
    'census_occupation_2018': 'fca2818d691c32777a4cd733a9ab77c8c5bd47adcacd7ac3aa149bebd45b5f7f',
    'pums_occupation_2018': '20cc7112cf96c7a3648b579cc0b2af239bea1c9094885a0d986959888695fe0a',
    'pums_annual_2024': 'f8c945c383322f123b5d409fd1cd1352f23ace3c0ffff5de0bc1cf414886d40d',
    'pums_five_year_2024': '634fdd565249d72f09a8f75d82fe4193b20a09d898ef64a4b8e8039348d52994',
}
D8_HTML_ASSERTIONS = (
    (692, '790', '519160', '7905',
     'Computer Numerically Controlled Tool Operators And Programmers', 683, 568, 736),
    (789, '9051', '532031', '9050', 'Flight Attendants', 780, 627, 823),
    (843, '9820', '553010', '9825',
     'Military Enlisted Tactical Operations and Air/Weapons Specialists and Crew Members',
     834, 665, 878),
)

class OccupationHTMLRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.cell = [], None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.rows.append([])
        if tag in ('td', 'th'):
            self.cell = ''

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.rows[-1].append(self.cell.strip())
            self.cell = None


def rejected_occupation_html(files):
    require(digest(files['occupation_pairs_html']) == D8_OCCUPATION_HTML_PIN,
            'D8 occupation HTML original pin differs')
    require(all(digest(files[k]) == v for k, v in D8_SUPPORT_PINS.items()),
            'D8 occupation supporting original pin differs')
    parser = OccupationHTMLRows()
    parser.feed(files['occupation_pairs_html'].read_text())
    rejected = []
    for n, literal, token, canonical, title, xr, cr, pr in D8_HTML_ASSERTIONS:
        require(len(parser.rows[n - 1]) == 15
                and [parser.rows[n - 1][i] for i in (6, 13, 14)] == [literal, token, title],
                'D8 occupation HTML assertion differs')
        support = []
        for kind, sheet, row, c, t in (
            ('ipums_occ_pairs', 'Codes without Descriptions', xr, 7, 14),
            ('ipums_occ_pairs', 'Codes with Descriptions', xr, 13, 27),
            ('census_occupation_2018', '2018 Census Occ Code List', cr, 2, 3),
            ('pums_occupation_2018', 'ACS', pr, 0, 1),
            ('pums_annual_2024', 'Occupation', pr, 0, 1),
            ('pums_five_year_2024', 'OCCP & SOCP', pr, 0, 1),
        ):
            values = workbook(files[kind], sheet)[row - 1]
            require(values[c] == canonical and values[t].replace('-', '') == token,
                    'D8 occupation support differs')
            support.append({'kind': kind, 'original_sha256': D8_SUPPORT_PINS[kind],
                            'reference_locator': f'{kind}:{sheet}:row={row}:'
                            f'columns={c + 1},{t + 1}',
                            'values': list(values)})
        rejected.append({'row': n, 'literal_code': literal, 'literal_token': token,
                         'supported_code': canonical, 'title': title,
                         'original_sha256': D8_OCCUPATION_HTML_PIN,
                         'reference_locator': f'occupation_pairs_html:tr={n}',
                         'disposition': 'rejected_assertion', 'supporting_assertions': support})
    return rejected


def occupation_pair_validation(files):
    admitted = {(r[0], r[1].replace('-', '')) for r in workbook(
        files['pums_occupation_2018'], 'ACS') if r[0] and r[1] and r[0].isdigit()}
    parser = OccupationHTMLRows()
    parser.feed(files['occupation_pairs_html'].read_text())
    assertions = [(r[6], r[13], f'occupation_pairs_html:tr={n}')
                  for n, r in enumerate(parser.rows, 1) if len(r) == 15]
    for sheet, c, t in [('Codes without Descriptions', 7, 14),
                        ('Codes with Descriptions', 13, 27)]:
        assertions.extend((r[c], r[t], f'ipums_occ_pairs:{sheet}:row={n}') for n, r in
                          enumerate(workbook(files['ipums_occ_pairs'], sheet), 1) if n > 1)
    rejected = []
    for code, token, locator in assertions:
        if code in (None, '', '-'):
            continue
        require(re.fullmatch('[0-9]{1,4}', code) is not None,
                'malformed paired occupation reference key')
        if code.zfill(4) == '0000' or token == '-':
            continue
        if (code.zfill(4), token) in admitted:
            continue
        if not rejected and locator.startswith('occupation_pairs_html:'):
            rejected = rejected_occupation_html(files)
        require(any(r['reference_locator'] == locator and r['literal_code'] == code
                    and r['literal_token'] == token and (r['supported_code'], token) in admitted
                    for r in rejected), 'unapproved paired occupation assertion')
    return rejected


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
    for (year, _, _), expression in pairs.items():
        leaf_members(expression, [r for r in native if r['vintage'] == year], paths)
    occupation, rejected = occupation_authorities(files)
    for row in codes.iter_rows(named=True):
        system = row['system']
        scheme = row['source_scheme']
        require(
            scheme in ({'naics2017', 'naics2022'}
                       if system == 'naics' else {'soc2018'}), 'native delivered scheme differs'
        )
        year = int(scheme[-4:])
        require(row['native_vintage'] == year, 'native vintage differs from delivered scheme')
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
        kind = (
            'special' if special else 'source_aggregate'
            if markers else 'whole_node' if aggregate else 'finest'
        )
        require(
            row['flag_aggregate'] == aggregate and row['aggregation_type'] == kind and row[
                'flag_exception'] == ('Z' in markers) and row['flag_reference_ambiguity'] is False,
            'singleton/aggregation/reference provenance differs'
        )
        partial = system == 'naics' and (
            'P' in token or bool(re.search(r'(?:Part of|Pts\.|pt\.)', pairs[year, pair, token]))
        )
        require(row['flag_partial'] == partial, 'partial-category provenance differs')
        require(
            row['canonical_vintage'] == (2022 if system == 'naics' else 2018),
            'canonical classification vintage differs'
        )
        canonical = set().union(*(forward[c] for c in members)) if year == 2017 else members
        require(
            row['native_finest_candidates'] == sorted(members
                                                      ) and row['canonical_finest_candidates']
            == sorted(canonical), 'candidate membership differs from original reference arithmetic'
        )
        native_nodes = soc if system == 'soc' else [r for r in native if r['vintage'] == year]
        expected_native = native_identifier(native_nodes, members, node_code, paths)
        require(
            row['native_node_id'] == expected_native,
            'native node differs from authenticated native hierarchy'
        )
        nodes = soc if system == 'soc' else [r for r in native if r['vintage'] == 2022]
        identifiers = {r['code']: r['node_id'] for r in nodes}
        expected_paths = [paths[identifiers[c]] for c in sorted(canonical)]
        require(
            row['canonical_candidate_paths'] == expected_paths,
            'canonical candidate paths differ from authenticated Stage4 graph'
        )
        scalar_controls(row, members, canonical, expected_paths, forward, kind, partial)
    return {'D4_rejected_constituents': rejected,
            'D8_rejected_occupation_html_assertions': occupation_pair_validation(files),
            'candidate_memberships_equal': True}

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

def locator_target(locator):
    '''Compare semantic original targets; raw-token/formatting decorations are not authority.'''
    match = re.match(r'^([^:]+):(.+?)!([A-Z]+(?::[A-Z]+)?):row=([0-9]+)(?::|$)', locator)
    if match:
        return f'{match[1]}:{match[2]}!{match[3]}:row:{int(match[4])}'
    return locator

def check_provenance(row, targets, reference_ids):
    require(
        set(row['reference_ids']) == set(reference_ids),
        'reference identities differ from selected original evidence'
    )
    require(
        {locator_target(v)
         for v in row['reference_locators']} == targets,
        'reference locator targets differ from independent original evidence'
    )

def code_provenance(codes, files, inputs, selected, data_dir, code_directory):
    from html.parser import HTMLParser

    class PairRows(HTMLParser):

        def __init__(self):
            super().__init__()
            self.rows, self.cell = [], None

        def handle_starttag(self, tag, attrs):
            if tag == 'tr':
                self.rows.append([])
            if tag in ('td', 'th'):
                self.cell = ''

        def handle_data(self, text):
            if self.cell is not None:
                self.cell += text

        def handle_endtag(self, tag):
            if tag in ('td', 'th') and self.cell is not None:
                if self.rows:
                    self.rows[-1].append(self.cell.strip())
                self.cell = None

    cache = {}

    def rows(kind, sheet):
        key = kind, sheet
        if key not in cache:
            cache[key] = workbook(files[kind], sheet)
        return cache[key]

    for year in (2017, 2022):
        kind = f'census_industry_{year}'
        original = selected['ipums']['references']['receipt']['originals'][kind]
        file = relative(data_dir / 'raw', original['citation']['path'])
        check_record(file, original['citation'], 'selected Census original provenance differs')
        files[kind] = file
    html_pairs = PairRows()
    html_pairs.feed(files['occupation_pairs_html'].read_text())
    highlighted = highlighted_occupation_rows(files['pums_occupation_2018'])
    for row in codes.iter_rows(named=True):
        pair, token, system, year = (
            row[k] for k in ('paired_census_code', 'source_token', 'system', 'native_vintage')
        )
        targets = set()
        if system == 'naics':
            editions = [(f'pums_industry_{year}', 'ACS')]
            if year == 2022:
                editions += [('pums_annual_2024', 'Industry'), ('pums_five_year_2024', 'Industry')]
            for kind, sheet in editions:
                matched = [
                    (n, r) for n, r in enumerate(rows(kind, sheet), 1)
                    if len(r) >= 5 and r[2] == pair and (r[4] or '').strip() == token
                ]
                require(len(matched) == 1, 'reference original industry pair target absent')
                targets.add(f'{kind}:{sheet}!C:E:row:{matched[0][0]}')
            kind = f'census_industry_{year}'
            sheet = ('2017 Census Industry Code List' if year == 2017
                     else '2022 Census Ind Code List ')
            matched = [n for n, r in enumerate(rows(kind, sheet), 1) if r[3] == pair]
            require(len(matched) == 1, 'Census reference industry target absent')
            targets.add(f'{kind}:{sheet}!D:E:row:{matched[0]}')
            targets.add('industry_tokens_html:Legend:M,P,S,Z')
            require(
                all(
                    v in document(files['industry_tokens_html']) for v in (
                        'Multiple NAICS codes', 'Part of a NAICS code', 'Not specified Industry',
                        'Exception to NAICS code'
                    )
                ), 'reference industry legend target absent'
            )
            for n, r in enumerate(rows('ipums_ind_tokens', 'Sheet 1'), 1):
                if n > 1 and (r[7 if year == 2017 else 8] or '').strip() == token:
                    targets.add(f'ipums_ind_tokens:Sheet 1!H:I:row:{n}')
            ids = {k for k, _ in editions} | {kind, 'industry_tokens_html'}
            if any(v.startswith('ipums_ind_tokens:') for v in targets):
                ids.add('ipums_ind_tokens')
        else:
            full_codes = set()
            editions = [
                ('pums_occupation_2018', 'ACS'), ('pums_annual_2024', 'Occupation'),
                ('pums_five_year_2024', 'OCCP & SOCP')
            ]
            primary_number = None
            for kind, sheet in editions:
                original_rows = rows(kind, sheet)
                matched = [
                    (n, r) for n, r in enumerate(original_rows, 1)
                    if r[0] == pair and (r[1] or '').strip().replace('-', '') == token
                ]
                require(len(matched) == 1, 'reference original occupation pair target absent')
                n, _ = matched[0]
                if kind == 'pums_occupation_2018':
                    primary_number = n
                targets.add(f'{kind}:{sheet}!A:C:row:{n}')
                constituents = set()
                cursor = n
                while cursor < len(original_rows) and original_rows[cursor][0] is None:
                    value = (original_rows[cursor][1] or '').strip()
                    if value and value != 'Combines:':
                        targets.add(f'{kind}:{sheet}!B:C:row:{cursor + 1}')
                        match = re.match(r'([0-9]{4}) - ', original_rows[cursor][2] or '')
                        if match:
                            constituents.add(match[1])
                    cursor += 1
                full_codes.update(constituents or {pair})
            for n, r in enumerate(rows('census_occupation_2018', '2018 Census Occ Code List'), 1):
                if r[2] in full_codes:
                    targets.add(f'census_occupation_2018:2018 Census Occ Code List!C:D:row:{n}')
            for sheet, c, t in [
                ('Codes without Descriptions', 7, 14), ('Codes with Descriptions', 13, 27)
            ]:
                for n, r in enumerate(rows('ipums_occ_pairs', sheet), 1):
                    if n > 1 and (r[c] or '').zfill(4) == pair and r[t] == token:
                        targets.add(f'ipums_occ_pairs:{sheet}!H:AB:row:{n}')
            for n, r in enumerate(html_pairs.rows, 1):
                if len(r) == 15 and r[6].zfill(4) == pair and r[13] == token:
                    targets.add(f'occupation_pairs_html:tr={n}')
            targets.update(
                {
                    'soc_tokens_html:aggregate-code-explanation',
                    'usa_occsoc:description:aggregate-code-explanation'
                }
            )
            require(
                all(
                    'confidentiality' in document(files[k])
                    for k in ('soc_tokens_html', 'usa_occsoc')
                ), 'reference occupation explanation target absent'
            )
            ids = {k
                   for k, _ in editions} | {
                       'census_occupation_2018', 'ipums_occ_pairs', 'occupation_pairs_html',
                       'soc_tokens_html', 'usa_occsoc'
                   }
            if row['aggregation_reasons'] == ['disclosure']:
                require(primary_number in highlighted, 'reference disclosure target absent')
                targets.update(
                    {
                        'pums_occupation_2018:ACS!A884:highlighting-confidentiality',
                        f'pums_occupation_2018:xl/styles.xml:ACS-row={primary_number}:theme7-tint'
                    }
                )
            if (pair, token) == ('9830', '559830'):
                for kind, page in [('pums_annual_guide', 17), ('pums_five_year_guide', 18)]:
                    require(
                        files[kind].read_bytes().startswith(b'%PDF-'),
                        'reference selected documentary original absent'
                    )
                    ids.add(kind)
                    targets.add(f'{kind}:physical-page={page}:VIII.I:SOCP=559830')
        ids.add('stage4_codes:' + inputs['selected_upstreams']['request']['codes_run'])
        for name in ('naics_native_nodes' if system == 'naics' else 'soc_nodes', 'code_paths'):
            targets.add(
                f'stage4_codes:{name}.parquet:sha256=' + digest(
                    code_directory / (name + '.parquet')
                )
            )
        check_provenance(row, targets, ids)

def geographic_provenance(directory, files, inputs):
    '''Rebuild citation support unions from original natural keys, separately from factors.'''
    reference_id = inputs['references']['reference_id']

    def original_rows(kind, sheet=None):
        if sheet is None:
            return [(r, f'{kind}:csv:row:{n}') for n, r in enumerate(csv_rows(files[kind]), 3)]
        return [
            (r, f'{kind}:{sheet}:row:{n}')
            for n, r in enumerate(workbook(files[kind], sheet)[1:], 2)
        ]

    pumas = {
        (r['state'], r['puma22']): {target}
        for r, target in original_rows('geocorr_puma_totals')
    }
    counties = {r['county']: {target} for r, target in original_rows('geocorr_county_totals')}
    groups, group_targets = {}, {}
    for r, target in original_rows('puma_composition_2020', 'PUMA_POWPUMA_MIGPUMA'):
        key = r[0], r[1]
        groups[key] = composition_state(r[2]), r[3]
        group_targets[key] = {target}
    county_groups = {
        r[0] + r[1]: {target}
        for r, target in original_rows('county_composition_2022', 'MIGPUMA-POWPUMA 2022 Lookup')
    }
    ct = ct_population(files) if 'ct_tabblock2020' in files else None
    ct_complete = {kind + ':complete-original' for kind in CT_REFERENCE_NAMES}
    if ct is not None:
        for state, puma in pumas:
            if state == '09':
                pumas[state, puma].update(ct_complete | {
                    f'census_puma_population2020:html:GEOID=09{puma}'})
        labels = dict(zip(('09110', '09120', '09130', '09140', '09150', '09160', '09170',
                           '09180', '09190'), ('Capitol', 'Greater Bridgeport',
                           'Lower CT River Valley', 'Naugatuck Valley', 'Northeastern CT',
                           'Northwest Hills', 'South Central', 'Southeastern CT', 'Western CT'),
                          strict=True))
        for county in counties:
            if county.startswith('09'):
                counties[county].update(ct_complete | {
                    'ct_opm_population2020:Sheet1:summary-label=' + labels[county]})
    denominators, numerators, support = defaultdict(set), defaultdict(set), {}
    for key, group in groups.items():
        denominators[group].update(pumas[key] | group_targets[key])
    for r, target in original_rows('geocorr_intersections'):
        key, county = (r['state'], r['puma22']), r['county']
        intersection_targets = {target}
        if ct is not None and key[0] == '09':
            relation = key[1], county
            if relation not in ct['relations']:
                continue
            intersection_targets.update(ct_complete | set(ct['source_locators'][relation]))
        support['residence', *key, county] = intersection_targets | pumas[key] | counties[county]
        numerators[*groups[key], county].update(
            intersection_targets | group_targets[key] | pumas[key])
    for (state, code, county), targets in numerators.items():
        support['work_migration', state, code, county] = (
            targets | denominators[state, code]
            | county_groups[county] | counties[county]
        )
    factor_support = defaultdict(set)
    for row in pl.read_parquet(directory / 'puma_county_factors.parquet').to_dicts():
        key = tuple(row[k] for k in ('area_type', 'state_fips', 'area_code', 'county_geoid'))
        targets = support[key]
        ids = {reference_id + ':' + t.split(':', 1)[0] for t in targets}
        check_provenance(row, targets, ids)
        factor_support[key[:3]].update(targets)
    msa_support, coverage = {}, defaultdict(set)
    for r, target in original_rows('msa_puma_2023_2020', 'MSA2023_PUMA2020_crosswalk'):
        key = r[2], r[4], r[0]
        msa_support[key] = {target}
        coverage[key[:2]].add(target)
    for name in ('puma_msa_factors', 'puma_msa_coverage'):
        for row in pl.read_parquet(directory / (name + '.parquet')).to_dicts():
            key = row['state_fips'], row['puma_code']
            targets = msa_support[*key, row['msa_code']] if name == 'puma_msa_factors' else (
                pumas[key] | coverage[key] | {'msa_puma_2023_2020:complete-original'}
            )
            check_provenance(
                row, targets, {reference_id + ':' + t.split(':', 1)[0]
                               for t in targets}
            )
    for row in pl.read_parquet(directory / 'acs_area_lookup.parquet').to_dicts():
        source = inputs['sources'][row['profile']]
        role = row['role']
        state, area, width = {
            'residence': ('STATEFIP', 'PUMA', 2),
            'workplace': ('PWSTATE2', 'PWPUMA00', 2),
            'migration': ('MIGPLAC1', 'MIGPUMA1', 3)
        }[role]
        kind = 'usa_' + area.lower()
        state_kind = 'usa_' + state.lower()
        ddi = [r for r in source['raw_citations'] if r['path'].endswith('.xml')]
        require(len(ddi) == 1, 'reference delivered DDI identity ambiguous')
        ddi = ddi[0]
        code = str(row['source_state_code']).zfill(width)
        labels = {str(c).zfill(width): label for c, label in categories(source, state).items()}
        require(code in labels, 'reference source state target absent')
        label = labels[code]
        targets = {
            f"{ddi['path']}#variables/{area}",
            f"{ddi['path']}#variables/{state}/categories/{code}={label}",
            f'{kind}#description_section', f'{kind}#codes_section',
            f'{kind}#comparability_section', 'usa_multyear#description_section'
        }
        kinds = {kind, 'usa_multyear'}
        if role != 'residence':
            targets.update(
                {f'{state_kind}#description_section', f'{state_kind}#comparability_section'}
            )
            kinds.add(state_kind)
        for fips, domestic_label in categories(source, 'STATEFIP').items():
            if fips in SCOPE | {'72'} and domestic_label == label:
                targets.add(f"{ddi['path']}#variables/STATEFIP/categories/{fips}={label}")
        if row['area_status'] == 'applicable':
            targets.update(factor_support[row['area_type'], row['state_fips'], row['area_code']])
        for target in targets:
            if '#' in target and not target.startswith(ddi['path'] + '#'):
                original_kind, anchor = target.split('#', 1)
                require(
                    anchor in files[original_kind].read_text(),
                    'reference document semantic section absent'
                )
                kinds.add(original_kind)
            elif ':' in target:
                kinds.add(target.split(':', 1)[0])
        ids = {reference_id + ':' + k for k in kinds}
        ids.add(f"ddi:{source['delivery_id']}:{ddi['sha256']}")
        check_provenance(row, targets, ids)

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
    geographic_identifiers(directory, geo_directory)
    codes = pl.read_parquet(directory / 'acs_code_lookup.parquet')
    areas = pl.read_parquet(directory / 'acs_area_lookup.parquet')
    independent_lookup(codes, files)
    classification = candidate_memberships(
        codes, files,
        data_dir / 'derived/codes' / inputs['selected_upstreams']['request']['codes_run']
    )
    code_directory = data_dir / 'derived/codes' / inputs['selected_upstreams']['request'][
        'codes_run']
    code_provenance(codes, dict(files), inputs, selected, data_dir, code_directory)
    geographic_provenance(directory, files, inputs)
    require(
        set(codes['system']) <= {'naics', 'soc'}
        and set(areas['profile']) <= set(PROFILES) and set(
            areas['role']
        ) <= {'residence', 'workplace', 'migration'}, 'unknown lookup system/profile/role'
    )
    county_factors = pl.read_parquet(directory / 'puma_county_factors.parquet')
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
            'source_industry_recoding': pl.scan_parquet(companion).group_by(
                'acs_sample_id', 'acs_component_year', 'flag_source_industry_recoded'
            ).len().sort('acs_sample_id', 'acs_component_year',
                         'flag_source_industry_recoded').collect().to_dicts(),
            'role_allocation_flags': {
                role: pl.scan_parquet(companion).group_by(
                    role + '_area_status', role + '_flag_source_geography_recoded',
                    role + '_flag_geographic_allocation', role + '_flag_fractional_split'
                ).len().sort(
                    role + '_area_status',
                    role + '_flag_source_geography_recoded',
                    role + '_flag_geographic_allocation',
                    role + '_flag_fractional_split',
                    nulls_last=False
                ).collect().to_dicts()
                for role in ('residence', 'workplace', 'migration')
            },
            'roles': role_measurements(
                source, companion, areas, files, pumas, groups, county_factors
            )
        }
    observed_lookup_coverage(measurements, codes)
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
    emit(freeze, data_dir, control_dir)

@app.command('preservation')
def preservation_command(
    data_dir: Path = typer.Option(...), control_dir: Path = typer.Option(...)
):
    emit(preservation, data_dir, control_dir)

@app.command('reconcile')
def reconcile_command(
    data_dir: Path = typer.Option(...),
    control_dir: Path = typer.Option(...),
    run_id: str = typer.Option(...),
    outputs_sha256: str = typer.Option(...)
):
    emit(reconcile, data_dir, run_id, outputs_sha256, control_dir)

if __name__ == '__main__':
    app()
