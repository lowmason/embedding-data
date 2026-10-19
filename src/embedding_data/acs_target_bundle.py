'''Offline ACS target publication, detached reconstruction and ordered logical replay.'''

import json
import math
import re
import shutil
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir

import polars as pl

from embedding_data import acs_mapping_bundle, ipums_parity, manifest, target_io
from embedding_data.acs_mapping_contract import SelectionRequest
from embedding_data.acs_mapping_inputs import _read_json, require_detached
from embedding_data.acs_mapping_io import publish_directory, safe_path
from embedding_data.acs_target_contract import (
    AUXILIARY_KEYS,
    PRODUCTS,
    RULE_VERSION,
    SCHEMA_VERSION,
    SELECTED_NODE_FRAMES,
    observed_counterpart,
)
from embedding_data.acs_target_inputs import freeze_target_software, select_targets
from embedding_data.acs_target_projection import ALLOCATION_FLAGS
from embedding_data.acs_target_rules import read_rules, required_flags
from embedding_data.acs_target_tables import (
    TABLES,
    derive_tables,
    validate_complete_tables,
    write_tables,
)
from embedding_data.acs_target_weights import WEIGHT_NAMES, weighted_source

FILES = tuple(name + '.parquet' for name in TABLES) + ('inputs.json', 'report.json')
LIMITS = {
    'evaluation_inputs_only': True,
    'training_mining_model_selection_permitted': False,
    'full_data_acceptance': False,
    'external_scientific_acceptance': False,
    'size_gate': 'size_gate_pending',
    'minimum_count': None,
    'allocation': 'workplace mixes only; population allocation does not infer individual location',
    'sampling_se': 'allocation-conditional; excludes allocation error and mapping uncertainty',
    'migration': ('domestic geographic movement; '
                  'no prior-job or job-related movement interpretation'),
    'canonical': 'supported scalar leaves only; supported-subset denominators',
    'shares': 'condition on identified eligible pairs under identical numerator restrictions',
    'non_msa': 'micropolitan and no_cbsa retained separately without renormalization',
    'puma_specific_allocation_flags': 'undelivered; no evidence inferred',
    'other_profiles': 'authenticated only; only core produces targets',
}


def run_directory(data_dir: Path, run_id: str) -> Path:
    if not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', run_id):
        raise ValueError('unsafe run ID')
    directory = Path(data_dir) / 'derived/acs/targets' / run_id
    safe_path(directory)
    return directory


def _reserve(data_dir, run_id):
    final = run_directory(data_dir, run_id)
    staging = final.with_name(run_id + '.part')
    for path in (final, staging):
        safe_path(path)
        if path.exists():
            raise FileExistsError(path)
    final.parent.mkdir(parents=True, exist_ok=True)
    safe_path(final.parent)
    staging.mkdir()
    return final, staging


def _write_json(path, value):
    safe_path(path)
    encoded = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(encoded + '\n')


def _members(directory, with_inventory):
    safe_path(directory)
    expected = set(FILES) | ({'outputs.json'} if with_inventory else set())
    if {path.name for path in directory.iterdir()} != expected:
        raise ValueError('missing or extra bundle paths')
    for path in directory.iterdir():
        safe_path(path)
        if not path.is_file():
            raise ValueError('bundle member is not a regular file')


def _input_evidence(selected, scratch):
    rules = {
        profile: asdict(read_rules(source))
        for profile, source in selected.upstream.sources.items()
    }
    with weighted_source(selected, scratch) as source:
        weights = {
            'variables': list(WEIGHT_NAMES),
            'point': 'PERWT',
            'variance': list(WEIGHT_NAMES[1:]),
            'factor': 1,
            'interpretation': 'Stage7 literal CSV weights; no implied-decimal rescaling',
            'diagnostics': source.diagnostics.to_dicts(),
            'rules': source.rules,
        }
    return {'version': RULE_VERSION, 'sources': rules}, weights


def _inputs(selected, run_id, created_at, evidence):
    rules, weights = evidence
    return {
        'schema_version': SCHEMA_VERSION,
        'run_id': run_id,
        'created_at': created_at,
        'mapping': {
            'run_id': selected.mapping_run,
            'outputs_sha256': selected.mapping_outputs_sha256,
        },
        'selected_upstreams': selected.provenance['selected_upstreams'],
        'sources': selected.provenance['sources'],
        'mapping_provenance': selected.provenance['mapping'],
        'rules': rules,
        'weights': weights,
        'products': [asdict(product) for product in PRODUCTS],
        'evidence_requirements': {
            product.product_id: list(required_flags(product.family, product.base_universe))
            for product in PRODUCTS
        },
        'universes': {
            'civilian_employed': {'EMPSTATD': [10, 12]},
            'private_wage_salary': {'EMPSTATD': [10, 12], 'CLASSWKRD': [22, 23]},
        },
        'frames': acs_mapping_bundle.FRAMES,
        'unit_frames': SELECTED_NODE_FRAMES,
        'allocation_flags': ALLOCATION_FLAGS,
        'units': {
            'schema': 'target_units.parquet',
            'complete_aggregate_registry': True,
            'keys': AUXILIARY_KEYS['target_units'],
        },
        'software': selected.software,
        'limits': LIMITS,
    }


def _read_tables(directory):
    return {name: pl.read_parquet(directory / (name + '.parquet')) for name in TABLES}


def _report(tables, selected, run_id, created_at):
    support = tables['target_support']
    diagnostics = tables['eligibility_diagnostics']
    residuals = tables['allocation_residuals']
    source = selected.upstream.sources['acs/core']
    year_counts = dict(
        pl.scan_parquet(source.parquet).group_by('YEAR').len().collect().iter_rows()
    )
    expected_hash = source.parquet_record['sha256']
    invalid = diagnostics.filter(
        pl.col('source_parquet_sha256').ne(expected_hash)
        | pl.col('delivery_id').ne(source.delivery_id)
        | pl.col('profile').ne('acs/core')
        | pl.col('component_year').is_in(list(year_counts)).not_()
        | pl.col('sample_id').ne(
            pl.concat_str(pl.lit('us'), pl.col('component_year').cast(pl.String), pl.lit('a'))
        )
    )
    if invalid.height:
        raise ValueError('diagnostic source sample/year identity differs')
    products = []
    for product in PRODUCTS:
        cells = support.filter(
            pl.col('product_id').eq(product.product_id)
            & pl.col('component_year').eq(0)
            & pl.col('record_kind').eq('cell')
        )
        defined = cells.filter(pl.col('point_status').eq('defined'))
        funnel = diagnostics.filter(
            pl.col('product_id').eq(product.product_id)
            & pl.col('partition_kind').eq('first_exclusion')
        )
        closure = []
        for year in sorted(year_counts):
            actual = funnel.filter(pl.col('component_year').eq(year))['n_unweighted'].sum()
            expected = year_counts.get(year, 0)
            if actual != expected:
                raise ValueError('disjoint eligibility funnel does not close')
            closure.append({'year': year, 'input_rows': expected, 'partition_rows': actual})
        products.append(
            {
                'product': asdict(product),
                'target_rows': defined.height,
                'supported_statistics': cells.height,
                'empty_reason': None if defined.height else 'no_positive_eligible_supported_cells',
                'funnel_closure': closure,
            }
        )

    def partition(frame, keys, expressions):
        return (
            frame.lazy()
            .group_by(keys)
            .agg(expressions)
            .sort(keys, nulls_last=False)
            .collect()
            .to_dicts()
        )

    return {
        'schema_version': SCHEMA_VERSION,
        'run_id': run_id,
        'created_at': created_at,
        'tables': {
            name: {
                'rows': frame.height,
                'columns': frame.columns,
                'schema': {key: str(dtype) for key, dtype in frame.schema.items()},
            }
            for name, frame in tables.items()
        },
        'products': products,
        'diagnostic_partitions': partition(
            diagnostics,
            [
                'product_id',
                'component_year',
                'partition_kind',
                'variable',
                'evidence_status',
                'reason',
            ],
            [pl.col('n_unweighted').sum(), pl.col('weighted_mass').sum()],
        ),
        'support_distributions': partition(
            support,
            [
                'product_id',
                'component_year',
                'measure',
                'record_kind',
                'point_status',
                'se_status',
                'se_reason',
            ],
            [
                pl.len().alias('rows'),
                pl.col('n_unweighted').min().alias('n_min'),
                pl.col('n_unweighted').max().alias('n_max'),
            ],
        ),
        'allocation_residuals': partition(
            residuals,
            ['product_id', 'component_year', 'replicate', 'residual_type'],
            [pl.col('weighted_mass').sum(), pl.col('fractional_support_mass').sum()],
        ),
        'allocation_conservation': _allocation_conservation(tables),
        'limits': LIMITS,
    }


def _json_normalized(value):
    # JSON stores tuple-valued product periods as lists.
    return json.loads(json.dumps(value, allow_nan=False))


def _recheck(selected, evidence):
    selected.verify()
    if freeze_target_software() != selected.software:
        raise ValueError('executing target software changed before publication')
    current_rules = {
        profile: asdict(read_rules(source))
        for profile, source in selected.upstream.sources.items()
    }
    if current_rules != evidence[0]['sources'] or evidence[0]['version'] != RULE_VERSION:
        raise ValueError('target rules changed before publication')


def build(
    data_dir: Path,
    run_id: str,
    mapping_run: str,
    *,
    expected_mapping_outputs_sha256: str,
    request: SelectionRequest,
) -> dict:
    final, staging = _reserve(data_dir, run_id)
    try:
        with TemporaryDirectory(prefix=run_id + '-scratch-', dir=final.parent) as temporary:
            scratch = Path(temporary)
            safe_path(scratch)
            selected = select_targets(
                Path(data_dir),
                mapping_run,
                expected_mapping_outputs_sha256=expected_mapping_outputs_sha256,
                request=request,
            )
            evidence = _input_evidence(selected, scratch)
            tables = derive_tables(selected, scratch)
            table_records = write_tables(staging, tables)
            created_at = datetime.now(UTC).isoformat()
            _write_json(staging / 'inputs.json', _inputs(selected, run_id, created_at, evidence))
            serialized = _read_tables(staging)
            report = _report(serialized, selected, run_id, created_at)
            _write_json(staging / 'report.json', report)
            if _read_json(staging / 'inputs.json') != _json_normalized(
                _inputs(selected, run_id, created_at, evidence)
            ):
                raise ValueError('serialized input evidence differs')
            if _read_json(staging / 'report.json') != _json_normalized(
                _report(serialized, selected, run_id, created_at)
            ):
                raise ValueError('serialized report differs')
            _recheck(selected, evidence)
            _members(staging, False)
            if table_records != {
                name: target_io.file_record(staging / (name + '.parquet')) for name in TABLES
            }:
                raise ValueError('serialized table bytes changed before publication')
            if _read_json(staging / 'inputs.json') != _json_normalized(
                _inputs(selected, run_id, created_at, evidence)
            ):
                raise ValueError('input evidence changed before publication')
            if _read_json(staging / 'report.json') != _json_normalized(report):
                raise ValueError('report changed before publication')
            _write_json(staging / 'outputs.json', target_io.inventory(staging, list(FILES)))
            _members(staging, True)
            pin = manifest.sha256_file(staging / 'outputs.json')
            publish_directory(staging, final)
            return {'run_id': run_id, 'directory': str(final), 'outputs_sha256': pin}
    finally:
        if staging.exists():
            safe_path(staging)
            shutil.rmtree(staging)


def verify_bundle(
    directory: Path,
    data_dir: Path,
    *,
    expected_outputs_sha256: str,
    mapping_run: str,
    expected_mapping_outputs_sha256: str,
) -> dict:
    directory = Path(directory)
    safe_path(directory / 'outputs.json')
    require_detached(directory / 'outputs.json', expected_outputs_sha256)
    _members(directory, True)
    inventory = _read_json(directory / 'outputs.json')
    target_io.verify_inventory(directory, inventory, set(FILES))
    if inventory != target_io.inventory(directory, list(FILES)):
        raise ValueError('output inventory records differ')
    inputs, report = (_read_json(directory / name) for name in ('inputs.json', 'report.json'))
    identity = {'run_id': mapping_run, 'outputs_sha256': expected_mapping_outputs_sha256}
    if inputs.get('mapping') != identity:
        raise ValueError('explicit mapping identity differs')
    if inputs.get('run_id') != directory.name or report.get('run_id') != directory.name:
        raise ValueError('bundle run identity differs')
    selected = select_targets(
        Path(data_dir),
        mapping_run,
        expected_mapping_outputs_sha256=expected_mapping_outputs_sha256,
        request=SelectionRequest(**inputs['selected_upstreams']['request']),
    )
    # Detached verification never creates directories inside the authenticated bundle.
    with _verification_scratch() as scratch:
        evidence = _input_evidence(selected, scratch)
        expected_inputs = _inputs(selected, directory.name, inputs['created_at'], evidence)
        if inputs != _json_normalized(expected_inputs):
            raise ValueError('input provenance, rule registry or software differs')
        actual = _read_tables(directory)
        validate_complete_tables(actual)
        if report != _json_normalized(
            _report(actual, selected, directory.name, report['created_at'])
        ):
            raise ValueError('substantive report differs from reconstruction')
        reconstructed = derive_tables(selected, scratch)
        for name in TABLES:
            expected = reconstructed[name]
            if isinstance(expected, pl.LazyFrame):
                expected = expected.collect()
            if list(actual[name].schema.items()) != list(expected.schema.items()) or not actual[
                name
            ].equals(expected):
                raise ValueError(name + ': ordered table differs from reconstruction')
        if report != _json_normalized(
            _report(actual, selected, directory.name, report['created_at'])
        ):
            raise ValueError('substantive report differs from reconstruction')
        _recheck(selected, evidence)
    # Reauthenticate the same physical bytes after reconstruction to reject drift.
    require_detached(directory / 'outputs.json', expected_outputs_sha256)
    _members(directory, True)
    target_io.verify_inventory(directory, inventory, set(FILES))
    return {
        'status': 'verified',
        'run_id': directory.name,
        'outputs_sha256': expected_outputs_sha256,
        'mapping': identity,
        'limits': LIMITS,
    }


def substantive_report(report):
    return {key: value for key, value in report.items() if key not in {'run_id', 'created_at'}}


def compare_runs(
    first: Path,
    second: Path,
    *,
    data_dir: Path,
    mapping_run: str,
    expected_mapping_outputs_sha256: str,
) -> dict:
    acs_mapping_bundle.verify_bundle(
        acs_mapping_bundle.run_directory(data_dir, mapping_run),
        data_dir,
        expected_outputs_sha256=expected_mapping_outputs_sha256,
    )
    for directory in (Path(first), Path(second)):
        _members(directory, True)
        inputs = _read_json(directory / 'inputs.json')
        if inputs.get('mapping') != {
            'run_id': mapping_run,
            'outputs_sha256': expected_mapping_outputs_sha256,
        }:
            raise ValueError('compared target mapping identity differs')
    tables = {
        name: ipums_parity.compare_ordered(
            pl.scan_parquet(Path(first) / (name + '.parquet')),
            pl.scan_parquet(Path(second) / (name + '.parquet')),
        )
        for name in TABLES
    }
    reports_equal = substantive_report(
        _read_json(Path(first) / 'report.json')
    ) == substantive_report(_read_json(Path(second) / 'report.json'))
    return {
        'equal': reports_equal
        and all(row['values_equal'] and row['schema_equal'] for row in tables.values()),
        'tables': tables,
        'substantive_report_equal': reports_equal,
        'trust_established': False,
    }


REPORT_MASS_KEYS = ['product_id', 'view', 'component_year', 'replicate']
REPORT_UNIT_ORDER = ['unit_a_type', 'unit_a', 'unit_b_type', 'unit_b']


def _public_mass_summaries(tables):
    support = tables['target_support'].lazy().filter(
        pl.col('family').eq('area_mix') & pl.col('measure').eq('annual_average_total')
        & pl.col('record_kind').eq('cell')).with_columns(
            pl.lit(0, dtype=pl.UInt8).alias('replicate'),
            pl.col('cell_mass').alias('_mass'), pl.col('cell_weight_sum_exact').alias('_exact'))
    replicates = (tables['replicate_estimates'].lazy().filter(
        pl.col('family').eq('area_mix') & pl.col('measure').eq('annual_average_total'))
        .with_columns(pl.lit(0, dtype=pl.Int64).alias('component_year'),
            pl.col('numerator').alias('_mass'), pl.col('numerator_sum_exact').alias('_exact')))
    columns = [*REPORT_MASS_KEYS, *REPORT_UNIT_ORDER, 'pool_divisor', '_mass', '_exact']
    public = pl.concat([support.select(columns), replicates.select(columns)])
    native = public.filter(pl.col('view').eq('observed'))
    scale = native.select(pl.col('_exact').str.split('.').list.get(1, null_on_oob=True)
                          .str.len_chars().max()).collect().item() or 0
    native = native.group_by(REPORT_MASS_KEYS).agg(
        pl.col('_exact').cast(pl.Decimal(38, scale)).sum().alias('_raw'),
        pl.col('pool_divisor').first()).with_columns(
            (pl.col('_raw').cast(pl.Float64) / pl.col('pool_divisor')).alias('mass'),
            pl.col('_raw').cast(pl.String).str.replace(r'(\.\d*?)0+$', '${1}')
            .str.replace(r'\.$', '').replace('-0', '0').alias('native_weight_sum_exact'))
    allocated = (public.filter(pl.col('view').is_in(['allocated_county', 'allocated_msa']))
        .sort([*REPORT_MASS_KEYS, *REPORT_UNIT_ORDER]).with_columns(
            pl.col('_mass').cum_sum().over(REPORT_MASS_KEYS, order_by=REPORT_UNIT_ORDER)
            .alias('_cumulative')).group_by(REPORT_MASS_KEYS).agg(
                pl.col('_cumulative').last().alias('mass')).with_columns(
                    pl.lit(None, dtype=pl.String).alias('native_weight_sum_exact')))
    columns = [*REPORT_MASS_KEYS, 'mass', 'native_weight_sum_exact']
    return pl.concat([native.select(columns), allocated.select(columns)]).sort(
        REPORT_MASS_KEYS).collect()


def _allocation_conservation(tables):
    '''Measure every conservation comparison reconstructible from serialized aggregates.'''
    summaries = _public_mass_summaries(tables)
    residual_keys = ['product_id', 'component_year', 'replicate', 'residual_type']
    residual_order = ['workplace_unit_type', 'workplace_unit', 'code_unit_type', 'code_unit']
    residuals = tables['allocation_residuals'].lazy().filter(
        pl.col('component_year').eq(0) | pl.col('replicate').eq(0)).sort(
            [*residual_keys, *residual_order]).with_columns(
                pl.col('weighted_mass').cum_sum().over(residual_keys, order_by=residual_order)
                .alias('_cumulative')).group_by(residual_keys).agg(
                    pl.col('_cumulative').last().alias('mass')).sort(residual_keys).collect()
    residual_index = {(r['product_id'], r['component_year'], r['replicate'], r['residual_type']):
                      r['mass'] for r in residuals.iter_rows(named=True)}
    measurements, product_counts = [], []
    for observed in PRODUCTS:
        if observed.family != 'area_mix' or observed.view != 'observed':
            continue
        county = next(p for p in PRODUCTS if p.view == 'allocated_county'
                      and observed_counterpart(p) == observed)
        msa = next(p for p in PRODUCTS if p.view == 'allocated_msa'
                   and observed_counterpart(p) == observed)
        def index(product):
            return {(r['component_year'], r['replicate']): r for r in summaries.filter(
                pl.col('product_id').eq(product.product_id)).iter_rows(named=True)}
        native, counties, metros = index(observed), index(county), index(msa)
        keys = set(native) | set(counties) | set(metros)
        keys.update((year, rep) for product_id, year, rep, _ in residual_index
                    if product_id == msa.product_id)
        count_before = len(measurements)
        for year, rep in sorted(keys):
            native_mass = native.get((year, rep), {}).get('mass', 0.0)
            county_mass = counties.get((year, rep), {}).get('mass', 0.0)
            metro_mass = metros.get((year, rep), {}).get('mass', 0.0)
            micro_mass = residual_index.get((msa.product_id, year, rep, 'micropolitan'), 0.0)
            no_cbsa_mass = residual_index.get((msa.product_id, year, rep, 'no_cbsa'), 0.0)
            for check, expected, actual in [
                ('native_to_county', native_mass, county_mass),
                ('county_to_msa_and_residuals', county_mass,
                 math.fsum((metro_mass, micro_mass, no_cbsa_mass)))]:
                difference = actual - expected
                tolerance = 1e-8 + 1e-12 * abs(expected)
                if (not all(math.isfinite(v) for v in (expected, actual, difference))
                        or abs(difference) > tolerance):
                    raise ValueError('serialized allocation conservation differs')
                measurements.append({'observed_product_id': observed.product_id,
                    'county_product_id': county.product_id, 'msa_product_id': msa.product_id,
                    'component_year': year, 'replicate': rep, 'check': check,
                    'expected_mass': expected, 'actual_mass': actual, 'difference': difference,
                    'absolute_error': abs(difference), 'tolerance': tolerance, 'status': 'pass',
                    'native_weight_sum_exact': native.get((year, rep), {}).get(
                        'native_weight_sum_exact') if check == 'native_to_county' else None,
                    'metropolitan_mass': metro_mass if check != 'native_to_county' else None,
                    'micropolitan_mass': micro_mass if check != 'native_to_county' else None,
                    'no_cbsa_mass': no_cbsa_mass if check != 'native_to_county' else None})
        product_counts.append({'observed_product_id': observed.product_id,
            'serialized_check_count': len(measurements) - count_before})
    return {'absolute_tolerance': 1e-8, 'relative_tolerance': 1e-12,
        'mass_semantics': 'annual_average_contribution; native raw Decimal sums divided once',
        'serialized_scope': 'annual/full and pooled/full plus pooled replicates1..80',
        'serialized_check_count': len(measurements), 'serialized_failure_count': 0,
        'products': product_counts, 'measurements': measurements,
        'internal_annual_replicates': {
            'status': 'checked_during_projection_and_denominator_reconstruction',
            'weights': 'full0 and replicates1..80 for every annual/pooled component',
            'serialized_annual_replicate_target_values_available': False}}


@contextmanager
def _verification_scratch():
    # Resolve only the OS temp alias before creating our own directory, never input paths.
    root = Path(gettempdir()).resolve(strict=True)
    safe_path(root)
    with TemporaryDirectory(prefix='acs-target-verify-', dir=root) as temporary:
        scratch = Path(temporary)
        safe_path(scratch)
        yield scratch
