'''Frozen offline evidence for five delivered IPUMS extracts, with detached verification.'''

import hashlib
import json
import platform
import re
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import distributions
from pathlib import Path

import polars as pl

from embedding_data import (
    ipums_acceptance,
    ipums_conversion,
    ipums_ddi,
    ipums_industry,
    ipums_parity,
    ipums_references,
    ipums_totals,
    ipums_weights,
    manifest,
    paths,
    target_io,
)

FORMAT_VERSION = 'ipums-verification-v1'
PROFILES = ('acs/core', 'acs/five_year', 'acs/vintage', 'cps/asec', 'cps/monthly')
TABLES = ('variable_inventory', 'sample_counts', 'flag_coverage', 'weight_diagnostics',
          'industry_frequencies', 'employment_comparisons', 'conversion_parity',
          'verification_checks')
OUTPUT_NAMES = {f'{name}.parquet' for name in TABLES} | {
    'weight_rules.json', 'inputs.json', 'report.json'}
SOFTWARE_ROOT = Path(__file__).resolve().parents[2]
SOFTWARE_FILES = ('pyproject.toml', 'uv.lock', *(
    f'src/embedding_data/{name}.py' for name in (
        '__init__', 'ipums_verification_run', 'ipums_cli', 'cli', 'ipums_acceptance',
        'ipums_conversion', 'ipums_ddi', 'ipums_industry', 'ipums_parity', 'ipums_references',
        'ipums_census_access', 'ipums_totals', 'ipums_weights', 'ipums_delivery',
        'acs_benchmark_extract', 'cps_benchmark_extract', 'manifest', 'paths', 'target_io',
        'geography_references', 'geography_parsers', 'code_references', 'osha_benchmark_download',
    )))
PARITY_SCHEMA = {'extract_key': pl.String, 'delivery_id': pl.String, 'schema_equal': pl.Boolean,
                 'values_equal': pl.Boolean, 'expected_rows': pl.UInt64, 'actual_rows': pl.UInt64}
CHECK_SCHEMA = {'extract_key': pl.String, 'delivery_id': pl.String, 'check': pl.String,
                'status': pl.String, 'evidence': pl.String}


class FidelityError(ValueError):
    '''Safe aggregate-only diagnostic identifying a failed delivery.'''


def run_directory(data_dir: Path, run_id: str) -> Path:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', run_id):
        raise ValueError('unsafe run ID')
    return target_io.relative_file(data_dir, f'derived/ipums/verification/{run_id}')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON object key')
        result[key] = value
    return result


def _read_json(file):
    return json.loads(file.read_text(encoding='utf-8'), object_pairs_hook=_unique_object)


def _selection(text):
    selection = json.loads(text, object_pairs_hook=_unique_object)
    if not isinstance(selection, dict) or set(selection) != set(PROFILES):
        raise ValueError('selection requires exactly five source/set profiles')
    for profile, item in selection.items():
        source, set_name = profile.split('/')
        collection = ipums_conversion.COLLECTIONS[source]
        if (not isinstance(item, dict) or set(item) != {'delivery', 'parquet'}
                or not isinstance(item['delivery'], str)
                or not re.fullmatch(rf'{collection}_[0-9]+', item['delivery'])
                or not isinstance(item['parquet'], str)):
            raise ValueError(f'{profile}: invalid delivery selection')
        expected = f'derived/{source}/{set_name}/{item["delivery"]}.parquet'
        if item['parquet'] != expected:
            raise ValueError(f'{profile}: selected Parquet must belong to the selected delivery')
    return selection


def _software():
    return {'files': {name: target_io.file_record(SOFTWARE_ROOT / name)
                      for name in SOFTWARE_FILES},
            'python': platform.python_version(),
            'implementation': platform.python_implementation(),
            'dependencies': dict(sorted((dist.metadata['Name'], dist.version)
                                        for dist in distributions()))}


def _git_label():
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=SOFTWARE_ROOT,
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _citation(data_dir, file):
    return json.loads(json.dumps(asdict(manifest.entry_for(paths.manifest_path(data_dir), file))))


def _selected_inputs(data_dir, selection):
    ipums_conversion._safe_path(data_dir)
    ipums_conversion._safe_path(paths.manifest_path(data_dir))
    result = {}
    for profile in PROFILES:
        source, set_name = profile.split('/')
        item = selection[profile]
        name = item['delivery']
        directory = target_io.relative_file(data_dir, f'raw/{source}/{set_name}/{name}')
        csv_gz = ipums_conversion._verify_delivery(
            data_dir, directory, ipums_conversion.COLLECTIONS[source])
        parquet = target_io.relative_file(data_dir, item['parquet'])
        if parquet.with_name(parquet.name + '.part').exists():
            raise ValueError(f'{profile}: incomplete selected Parquet')
        result[profile] = {
            'delivery_id': name, 'parquet': item['parquet'],
            'parquet_record': target_io.file_record(parquet),
            'raw_citations': [_citation(data_dir, file) for file in (
                directory / 'extract.json', directory / f'{name}.xml', csv_gz)],
            'definition': ipums_ddi.read_definition(directory / 'extract.json'),
            'ddi': ipums_ddi.read_ddi(directory / f'{name}.xml'),
        }
    return result


def _reference_inputs(data_dir, reference_id):
    receipt = ipums_references.check_references(data_dir, reference_id)
    file = data_dir / 'raw/references/ipums-verification' / reference_id / 'receipt.json'
    return {'reference_id': reference_id, 'receipt': receipt,
            'receipt_citation': _citation(data_dir, file)}


def _reference_file(data_dir, reference_id, kind):
    return (data_dir / 'raw/references/ipums-verification' / reference_id
            / ipums_references.REGISTRY[kind].filename)


def _acs_context(frame, universe):
    return frame.lazy().with_columns(
        pl.lit('annual').alias('period'), pl.col('year').alias('period_start'),
        pl.col('year').alias('period_end'), pl.concat_list('year').alias('period_years'),
        pl.lit(universe, dtype=pl.String).alias('universe'),
        pl.lit('residence').alias('geography_basis'),
        pl.when(pl.col('state_fips').is_in(sorted(ipums_references.ACS_COMPARISON_STATES)))
        .then(pl.lit('50_states_dc')).otherwise(pl.lit('outside_50_states_dc'))
        .alias('geography_scope')).collect()


def _acs_references(data_dir, reference_id):
    frames, evidence = [], {}
    for year in (2023, 2024):
        metadata = _reference_file(data_dir, reference_id, f'acs_{year}_b23025_metadata')
        html = ipums_references.PublicHTML(metadata.read_text())
        text = ' '.join(html.text).casefold()
        labels = [' '.join(row[1:]).casefold() for table in html.tables for row in table
                  if row and row[0].strip() == 'B23025_004E']
        proven = (len(labels) == 1 and '16 years and over' in text
                  and 'civilian labor force' in labels[0]
                  and re.search(r'\bemployed\b', labels[0]) is not None)
        evidence[str(year)] = {'universe_status': 'documented' if proven else 'unresolved',
                               'metadata_kind': f'acs_{year}_b23025_metadata'}
        frame = ipums_references.parse_acs_levels(
            _reference_file(data_dir, reference_id, f'acs_{year}_employment'), year)
        frames.append(_acs_context(frame, ipums_totals.ACS_UNIVERSE if proven else None))
    annual = pl.concat([frame.lazy() for frame in frames]).collect()
    pooled = annual.lazy().group_by('state_fips').agg(
        pl.col('published').sum().truediv(2).alias('published'),
        pl.col('year').n_unique().alias('_years'),
    ).with_columns(
        pl.when(pl.col('_years').eq(2)).then(pl.col('published')).otherwise(None)
        .alias('published'), pl.lit(None, dtype=pl.Int64).alias('year'),
        pl.lit('persons').alias('units'), pl.lit('annual_average').alias('period'),
        pl.lit(2023, dtype=pl.Int64).alias('period_start'),
        pl.lit(2024, dtype=pl.Int64).alias('period_end'),
        pl.lit([2023, 2024], dtype=pl.List(pl.Int64)).alias('period_years'),
        pl.lit(ipums_totals.ACS_UNIVERSE if all(
            item['universe_status'] == 'documented' for item in evidence.values()) else None,
            dtype=pl.String).alias('universe'),
        pl.lit('residence').alias('geography_basis'),
        pl.when(pl.col('state_fips').is_in(sorted(ipums_references.ACS_COMPARISON_STATES)))
        .then(pl.lit('50_states_dc')).otherwise(pl.lit('outside_50_states_dc'))
        .alias('geography_scope'),
    ).select(annual.columns).collect()
    return pl.concat([annual.lazy(), pooled.lazy()]).collect(), evidence


def _bls_references(data_dir, reference_id):
    # This parser validates the separately frozen series title, units and A-1 universe.
    return ipums_references.parse_bls_levels(
        _reference_file(data_dir, reference_id, 'cps_employment')).lazy().with_columns(
        pl.lit('monthly').alias('period'),
        pl.col('year').mul(100).add(pl.col('month')).alias('period_start'),
        pl.col('year').mul(100).add(pl.col('month')).alias('period_end'),
        pl.concat_list('year').alias('period_years'),
        pl.lit(ipums_totals.CPS_UNIVERSE).alias('universe'),
        pl.lit('residence').alias('geography_basis'),
        pl.lit('50_states_dc').alias('geography_scope')).collect()


def _delivery_columns(frame, profile, item):
    return frame.lazy().with_columns(pl.lit(profile).alias('extract_key'),
                                     pl.lit(item['delivery_id']).alias('delivery_id')).collect()


def _comparisons(measured, published, profile, item, references, kinds):
    source, set_name = profile.split('/')
    keys = (['state_fips', 'period', 'period_start', 'period_end'] if source == 'acs'
            else ['year', 'month'])
    result = ipums_totals.compare_levels(measured, published, keys)
    provenance = {kind: references['receipt']['originals'][kind] for kind in kinds}
    return _delivery_columns(result, profile, item).lazy().with_columns(
        pl.lit(source).alias('source'), pl.lit(set_name).alias('set_name'),
        pl.lit(json.dumps(provenance, sort_keys=True)).alias('published_provenance'),
        pl.lit(json.dumps(item['raw_citations'], sort_keys=True)).alias('delivery_provenance'),
        pl.lit('WTFINL differs from the official composite estimator' if source == 'cps'
               else 'PERWT annual and complete two-year average; no allocation filter')
        .alias('estimator_note')).collect()


def _measure_profile(data_dir, staging, profile, item, catalog, lists, published, references):
    source, set_name = profile.split('/')
    name = item['delivery_id']
    raw = data_dir / 'raw' / source / set_name / name
    parquet = data_dir / item['parquet']
    tables = {}
    with ipums_conversion.decompressed_csv(raw / f'{name}.csv.gz', staging) as csv:
        original = ipums_conversion.scan_delivered_csv(csv, source)
        parity = ipums_parity.compare_ordered(original, pl.scan_parquet(parquet))
        if not parity['schema_equal'] or not parity['values_equal']:
            target_io.write_json(staging / 'failure.json', {
                'extract_key': profile, 'delivery_id': name, 'conversion_parity': parity})
            raise FidelityError(f'{profile}/{name}: full ordered conversion fidelity failed')
        accepted = ipums_acceptance.measure_acceptance(
            item['definition'], item['ddi'], pl.scan_parquet(parquet), source, set_name, catalog)
        status = accepted['status']
        status['raw_header_parity'] = 'pass'
        for table in ('variable_inventory', 'sample_counts', 'flag_coverage'):
            tables[table] = _delivery_columns(accepted[table], profile, item)
        diagnostics, rules = ipums_weights.measure_weights(csv, item['ddi'], source, set_name)
        rules['parquet_parity'] = 'pass_all_delivered_variables'
        tables['weight_diagnostics'] = _delivery_columns(diagnostics, profile, item)
        if profile in ('acs/core', 'cps/monthly'):
            numeric = ipums_weights.scan_numeric_csv(csv, diagnostics, source)
            if source == 'acs':
                measured = ipums_totals.acs_employment(numeric)
                kinds = ['acs_2023_employment', 'acs_2024_employment',
                         'acs_2023_b23025_metadata', 'acs_2024_b23025_metadata']
            else:
                measured = ipums_totals.cps_employment(numeric)
                kinds = ['cps_employment', 'bls_series_metadata', 'bls_a1_metadata']
            tables['employment_comparisons'] = _comparisons(
                measured, published[source], profile, item, references, kinds)
        if profile == 'cps/asec':
            lexical = pl.scan_csv(csv, schema_overrides={
                'YEAR': pl.Int64, 'IND': pl.String, 'INDLY': pl.String},
            ).select('YEAR', 'IND', 'INDLY')
            tables['industry_frequencies'] = _delivery_columns(
                ipums_industry.industry_frequencies(lexical, item['ddi'], lists), profile, item)
    return tables, status, rules, {'extract_key': profile, 'delivery_id': name, **parity}


def _checks(profile, item, status):
    return [
        (profile, item['delivery_id'], 'ordered_csv_parquet_fidelity', 'pass',
         'all delivered columns, ordered values and duplicate multiplicity'),
        (profile, item['delivery_id'], 'accepted_definition_and_composition', status['status'],
         'see report acceptance diagnostics'),
        (profile, item['delivery_id'], 'weight_storage_interpretation', 'unresolved',
         'CSV units and parity measured; family design, sentinels and adoption require review'),
        (profile, item['delivery_id'], 'flag_semantics', 'unresolved',
         'typed category coverage retained; allocation applicability is unknown'),
    ]


def _recheck(data_dir, inputs):
    selection = _selection(inputs['selection']['text'])
    if hashlib.sha256(inputs['selection']['text'].encode()).hexdigest() != inputs['selection'][
            'sha256']:
        raise ValueError('frozen selection bytes/hash differ')
    if _selected_inputs(data_dir, selection) != inputs['deliveries']:
        raise ValueError('selected delivery inputs changed')
    if _reference_inputs(data_dir, inputs['references']['reference_id']) != inputs['references']:
        raise ValueError('selected references changed')
    if _software() != inputs['software']:
        raise ValueError('executing software or dependency identity changed')


def measure(data_dir: Path, run_id: str, reference_id: str, selection_file: Path) -> Path:
    '''Publish aggregates only after initial validation, full fidelity and final revalidation.'''
    data_dir, selection_file = Path(data_dir), Path(selection_file)
    ipums_conversion._safe_path(selection_file)
    text = selection_file.read_bytes().decode('utf-8')
    selection = _selection(text)
    inputs = {'format_version': FORMAT_VERSION, 'run_id': run_id,
              'created_at': datetime.now(UTC).isoformat(),
              'git_commit_informational': _git_label(),
              'selection': {'text': text, 'sha256': hashlib.sha256(text.encode()).hexdigest()},
              'deliveries': _selected_inputs(data_dir, selection),
              'references': _reference_inputs(data_dir, reference_id), 'software': _software()}
    final, staging = target_io.stage(run_directory(data_dir, run_id).parent, run_id, data_dir)
    target_io.write_json(staging / 'inputs.json', inputs)
    catalog = ipums_references.parse_sample_catalog(
        _reference_file(data_dir, reference_id, 'usa_samples'))
    lists = {vintage: ipums_references.parse_industry_list(
        _reference_file(data_dir, reference_id, f'census_industry_{vintage}'), vintage)
        for vintage in (2017, 2022)}
    industry_metadata = {str(vintage): ipums_references.parse_industry_metadata(
        _reference_file(data_dir, reference_id, f'census_industry_{vintage}'), vintage)
        for vintage in (2017, 2022)}
    acs, reference_context = _acs_references(data_dir, reference_id)
    published = {'acs': acs, 'cps': _bls_references(data_dir, reference_id)}
    pieces = {name: [] for name in TABLES}
    acceptance, weight_rules, parity, checks = {}, {}, [], []
    for profile in PROFILES:
        item = inputs['deliveries'][profile]
        tables, status, rules, comparison = _measure_profile(
            data_dir, staging, profile, item, catalog, lists, published, inputs['references'])
        acceptance[profile], weight_rules[profile] = status, rules
        parity.append(comparison)
        checks.extend(_checks(profile, item, status))
        for name, table in tables.items():
            pieces[name].append(table)
    pieces['conversion_parity'] = [pl.DataFrame(parity, schema=PARITY_SCHEMA)]
    checks.append(('cps/asec', inputs['deliveries']['cps/asec']['delivery_id'],
                   'industry_native_scheme', 'unresolved',
                   'membership alone does not prove native vintage or harmonization'))
    pieces['verification_checks'] = [pl.DataFrame(checks, schema=CHECK_SCHEMA, orient='row')]
    contracts = {}
    for name, frames in pieces.items():
        table = pl.concat([frame.lazy() for frame in frames], how='diagonal_relaxed').collect()
        file = staging / f'{name}.parquet'
        table.write_parquet(file)
        contracts[file.name] = {key: value for key, value in target_io.file_record(file).items()
                                if key in ('rows', 'schema', 'columns')}
    inputs['aggregate_contracts'] = contracts
    target_io.write_json(staging / 'inputs.json', inputs)
    target_io.write_json(staging / 'weight_rules.json', weight_rules)
    report = {
        'format_version': FORMAT_VERSION,
        'status': ('fail' if any(s['status'] == 'fail' for s in acceptance.values())
                   else 'unresolved'),
        'acceptance': acceptance, 'acs_reference_context': reference_context,
        'industry_reference_metadata': industry_metadata,
        'unresolved': ['weight-family design/sentinel review and production storage adoption',
                       'quality-flag allocation applicability',
                       'ASEC native industry scheme and delivered harmonization'],
        'scope': 'measurement evidence only; no benchmark acceptance or target construction',
    }
    target_io.write_json(staging / 'report.json', report)
    _recheck(data_dir, inputs)
    if selection_file.read_bytes() != text.encode():
        raise ValueError('selection file changed during measurement')
    target_io.write_json(staging / 'outputs.json',
                         target_io.inventory(staging, sorted(OUTPUT_NAMES)))
    verify_bundle(staging, data_dir, expected_outputs_sha256=manifest.sha256_file(
        staging / 'outputs.json'))
    if final.exists() or final.is_symlink():
        raise ValueError('run name became occupied before publication')
    staging.rename(final)
    return final


def _verify_outputs(directory, expected_outputs_sha256):
    ipums_conversion._safe_path(directory)
    if {file.name for file in directory.iterdir()} != OUTPUT_NAMES | {'outputs.json'}:
        raise ValueError('missing or extra output paths')
    inventory_file = target_io.relative_file(directory, 'outputs.json')
    if (not re.fullmatch(r'[0-9a-f]{64}', expected_outputs_sha256)
            or manifest.sha256_file(inventory_file) != expected_outputs_sha256):
        raise ValueError('detached outputs checksum differs')
    inventory = _read_json(inventory_file)
    target_io.verify_inventory(directory, inventory, OUTPUT_NAMES)
    inputs = _read_json(directory / 'inputs.json')
    if inputs.get('format_version') != FORMAT_VERSION:
        raise ValueError('unsupported verification inputs version')
    expected_contracts = {f'{name}.parquet' for name in TABLES}
    if set(inputs.get('aggregate_contracts', {})) != expected_contracts:
        raise ValueError('aggregate contracts incomplete')
    for name, contract in inputs['aggregate_contracts'].items():
        record = target_io.file_record(directory / name)
        if set(contract) != {'rows', 'schema', 'columns'} or any(
                record[key] != value for key, value in contract.items()):
            raise ValueError(f'{name}: frozen aggregate schema or row count differs')
        if not {'rows', 'schema', 'columns'}.issubset(inventory[name]):
            raise ValueError('output inventory omits Parquet contract')
    return inputs


def verify_bundle(directory: Path, data_dir: Path, *, expected_outputs_sha256: str) -> dict:
    '''Verify a separately pinned aggregate inventory and all selected source/software bytes.'''
    inputs = _verify_outputs(Path(directory), expected_outputs_sha256)
    _recheck(Path(data_dir), inputs)
    return {'status': 'verified', 'run_id': inputs['run_id'],
            'outputs_sha256': expected_outputs_sha256,
            'measurement_status': _read_json(Path(directory) / 'report.json')['status']}


def compare_runs(first: Path, second: Path) -> dict:
    '''Compare ordered logical aggregates and interpretation; inventory pins are descriptive.'''
    first, second = Path(first), Path(second)
    pins = [manifest.sha256_file(directory / 'outputs.json') for directory in (first, second)]
    for directory, pin in zip((first, second), pins, strict=True):
        _verify_outputs(directory, pin)
    comparisons = {name: ipums_parity.compare_ordered(
        pl.scan_parquet(first / f'{name}.parquet'), pl.scan_parquet(second / f'{name}.parquet'))
        for name in TABLES}
    interpretation_equal = all(_read_json(first / name) == _read_json(second / name)
                               for name in ('weight_rules.json', 'report.json'))
    return {'equal': interpretation_equal and all(
        item['schema_equal'] and item['values_equal'] for item in comparisons.values()),
        'tables': comparisons, 'interpretation_equal': interpretation_equal,
        'outputs_sha256': pins, 'comparison_scope': 'logical outputs; no external detached trust'}
