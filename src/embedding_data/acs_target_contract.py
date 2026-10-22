'''Frozen ACS products and aggregate-only schema, key and membership contracts.'''

import hashlib
import json
import re
from dataclasses import asdict, dataclass

import polars as pl

from embedding_data.acs_mapping_contract import CODE_SCHEMA, NATURAL_KEYS, validate_table
from embedding_data.target_contract import (
    TARGET_KEY_COLUMNS,
    TARGET_SCHEMA,
    valid_unit,
    validate_targets,
)

SCHEMA_VERSION = 'acs-targets-v1'
RULE_VERSION = 'acs-target-rules-v1'
REPLICATES = tuple(range(1, 81))
MEASURES = ('annual_average_total', 'forward_share')
SELECTED_NODE_FRAMES = {
    'naics_national_industry': ('naics', 2022, 'national_industry'),
    'soc_detailed': ('soc', 2018, 'detailed'),
    'county': ('geography', 2025, 'county'),
    'cbsa': ('geography', 2023, 'cbsa'),
}
MSA_DELINEATION = 'July 2023'
S, I, U, F = pl.String, pl.Int64, pl.UInt64, pl.Float64  # noqa: E741
LS, LU8 = pl.List(S), pl.List(pl.UInt8)
TARGET_STAT_KEY_COLUMNS = [name for name in TARGET_KEY_COLUMNS if name != 'se_method']
STAT_KEY_COLUMNS = ['view', *TARGET_STAT_KEY_COLUMNS]
CELL_KEY_COLUMNS = [name for name in STAT_KEY_COLUMNS if name != 'measure']
STAT_KEY_SCHEMA = {'view': S, **{name: TARGET_SCHEMA[name] for name in TARGET_STAT_KEY_COLUMNS}}
CELL_KEY_SCHEMA = {name: dtype for name, dtype in STAT_KEY_SCHEMA.items() if name != 'measure'}
UNIT_SCHEMA = {
    'unit_type': S,
    'unit': S,
    'kind': S,
    **{'code_' + name: dtype for name, dtype in CODE_SCHEMA.items()},
    'node_id': S,
    'node_system': S,
    'node_vintage': I,
    'node_level': S,
    'node_code': S,
    'node_title': S,
    'area_type': S,
    'state_fips': S,
    'area_code': S,
    'puma_vintage': I,
    'population_year': I,
    'county_composition_year': I,
    'county_inventory_vintage': I,
    'msa_delineation': S,
    'cbsa_type': S,
    'roles': LS,
    'area_lookup_ids': LS,
    'factor_keys': LS,
    'reference_ids': LS,
    'reference_locators': LS,
}
SUPPORT_SCHEMA = {
    **STAT_KEY_SCHEMA,
    'record_kind': S,
    'component_year': I,
    'product_id': S,
    'pool_divisor': pl.UInt8,
    'n_unweighted': U,
    'denominator_n_unweighted': U,
    'cell_weight_sum_exact': S,
    'denominator_weight_sum_exact': S,
    'cell_mass': F,
    'denominator_mass': F,
    'fractional_support_mass': F,
    'denominator_fractional_support_mass': F,
    'native_coverage_n': U,
    'native_coverage_mass': F,
    'point_status': S,
    'point_reason': S,
    'se_status': S,
    'se_reason': S,
    'undefined_replicates': LU8,
    'support_semantics': S,
    'flags': LS,
}
REPLICATE_SCHEMA = {
    **STAT_KEY_SCHEMA,
    'product_id': S,
    'replicate': pl.UInt8,
    'numerator_sum_exact': S,
    'denominator_sum_exact': S,
    'pool_divisor': pl.UInt8,
    'numerator': F,
    'denominator': F,
    'estimate': F,
    'status': S,
    'reason': S,
}
DIAGNOSTIC_SCHEMA = {
    'source': S,
    'profile': S,
    'delivery_id': S,
    'source_parquet_sha256': S,
    'sample_id': S,
    'component_year': I,
    'family': S,
    'dimension': S,
    'base_universe': S,
    'evidence_policy': S,
    'view': S,
    'product_id': S,
    'partition_kind': S,
    'variable': S,
    'raw_dtype': S,
    'raw_value': S,
    'evidence_status': S,
    'reason': S,
    'n_unweighted': U,
    'weight_sum_exact': S,
    'weighted_mass': F,
    'reference_ids': LS,
    'reference_locators': LS,
}
RESIDUAL_SCHEMA = {
    'source': S,
    'family': S,
    'workplace_unit_type': S,
    'workplace_unit': S,
    'code_unit_type': S,
    'code_unit': S,
    'sample_set': S,
    'vintage': S,
    'universe': S,
    'product_id': S,
    'component_year': I,
    'replicate': pl.UInt8,
    'residual_type': S,
    'pool_divisor': pl.UInt8,
    'weighted_mass': F,
    'n_input_support': U,
    'fractional_support_mass': F,
    'flags': LS,
}
AUXILIARY_SCHEMAS = {
    'target_units': UNIT_SCHEMA,
    'target_support': SUPPORT_SCHEMA,
    'replicate_estimates': REPLICATE_SCHEMA,
    'eligibility_diagnostics': DIAGNOSTIC_SCHEMA,
    'allocation_residuals': RESIDUAL_SCHEMA,
}
AUXILIARY_KEYS = {
    'target_units': ['unit_type', 'unit'],
    'target_support': [*STAT_KEY_COLUMNS, 'record_kind', 'component_year'],
    'replicate_estimates': [*STAT_KEY_COLUMNS, 'replicate'],
    'eligibility_diagnostics': list(DIAGNOSTIC_SCHEMA)[:18],
    'allocation_residuals': list(RESIDUAL_SCHEMA)[:13],
}
TARGET_TABLES = ('targets_observed', 'targets_canonical', 'targets_allocated_area_mix')
_VALIDATION_PREFIX = ['source', 'family', 'unit_a_type', 'unit_a']
_VALIDATION_CHUNK_ROWS = 4096


@dataclass(frozen=True)
class Product:
    product_id: str
    family: str
    dimension: str
    view: str
    base_universe: str
    evidence_policy: str
    years: tuple[int, ...]
    sample_set: str
    pool_divisor: int
    vintage: str


def _product_id(identity: dict) -> str:
    encoded = json.dumps(
        identity, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False
    )
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def _products() -> tuple[Product, ...]:
    # Each template fixes a scientific product; only named policy/universe pairs expand.
    templates = [
        ('staffing_pattern', 'industry_occupation', 'observed', 'acs-naics2022-soc2018'),
        ('area_mix', 'industry', 'observed', 'acs-naics2022-puma2020'),
        ('area_mix', 'occupation', 'observed', 'acs-soc2018-puma2020'),
        ('commuting_flow', 'flow', 'observed', 'residence2020-work-migration2020'),
        ('staffing_pattern', 'industry_occupation', 'canonical', 'naics2022-soc2018'),
        ('area_mix', 'industry', 'canonical', 'naics2022-puma2020'),
        ('area_mix', 'occupation', 'canonical', 'soc2018-puma2020'),
        ('area_mix', 'industry', 'allocated_county', 'acs-naics2022-county2025'),
        ('area_mix', 'occupation', 'allocated_county', 'acs-soc2018-county2025'),
        ('area_mix', 'industry', 'allocated_msa', 'acs-naics2022-msa2023'),
        ('area_mix', 'occupation', 'allocated_msa', 'acs-soc2018-msa2023'),
    ]
    definitions = [
        (family, dimension, view, vintage, policy, (2023, 2024))
        for family, dimension, view, vintage in templates
        for policy in ('strict', 'sensitivity')
    ]
    definitions.extend(
        ('migration_flow', 'flow', 'observed', 'work-migration2020-residence2020', policy, years)
        for policy, years in [
            ('strict', (2024,)),
            ('sensitivity', (2024,)),
            ('sensitivity', (2023, 2024)),
        ]
    )
    products = []
    for family, dimension, view, vintage, policy, years in definitions:
        for universe in ('civilian_employed', 'private_wage_salary'):
            identity = dict(
                family=family,
                dimension=dimension,
                view=view,
                vintage=vintage,
                evidence_policy=policy,
                years=years,
                base_universe=universe,
                sample_set='annual-2024' if years == (2024,) else 'annual-core-2023-2024',
                pool_divisor=len(years),
            )
            products.append(Product(product_id=_product_id(identity), **identity))
    return tuple(products)


PRODUCTS = _products()


def observed_counterpart(product: Product) -> Product:
    '''Return the unique observed baseline with the same declared scientific restrictions.'''
    fields = (
        'family',
        'dimension',
        'base_universe',
        'evidence_policy',
        'years',
        'sample_set',
        'pool_divisor',
    )
    matches = [
        candidate
        for candidate in PRODUCTS
        if candidate.view == 'observed'
        and all(getattr(candidate, name) == getattr(product, name) for name in fields)
    ]
    if len(matches) != 1:
        raise ValueError('product has no unique observed counterpart')
    return matches[0]


def _lazy(frame: pl.DataFrame | pl.LazyFrame) -> pl.LazyFrame:
    return frame.lazy() if isinstance(frame, pl.DataFrame) else frame


def _reject(lf: pl.LazyFrame, checks: dict[str, pl.Expr]) -> None:
    failures = (
        lf.select([expr.fill_null(False).any().alias(name) for name, expr in checks.items()])
        .collect()
        .row(0, named=True)
    )
    for name, failed in failures.items():
        if failed:
            raise ValueError(name)


def _validation_partitions(frames, prefix=None):
    '''Yield complete actual prefixes from every side, retaining all original rows.'''
    prefix = _VALIDATION_PREFIX if prefix is None else prefix
    frames = [_lazy(frame) for frame in frames]
    registry = pl.concat([lf.select(prefix) for lf in frames]).unique().sort(
        prefix, nulls_last=False)
    batches = registry.collect_batches(chunk_size=_VALIDATION_CHUNK_ROWS, maintain_order=True,
                                       engine='streaming', lazy=True)
    try:
        for batch in batches:
            for values in batch.iter_rows():
                predicate = pl.all_horizontal([
                    pl.col(name).eq_missing(value) for name, value in zip(prefix, values,
                                                                         strict=True)])
                yield tuple(lf.filter(predicate) for lf in frames)
    finally:
        del batches


def _validate_key_order(lf, keys, message):
    '''Check original serialized key order across batches without sorting away corruption.'''
    batches = _lazy(lf).select(keys).collect_batches(
        chunk_size=_VALIDATION_CHUNK_ROWS, maintain_order=True, engine='streaming', lazy=True)
    previous = None
    try:
        for batch in batches:
            for values in batch.iter_rows():
                # Optional keys use the existing nulls-first lexicographic order.
                current = tuple((value is not None, value) for value in values)
                if previous is not None and current < previous:
                    raise ValueError(message)
                previous = current
    finally:
        del batches


def _unique(lf: pl.LazyFrame, keys: list[str], description: str) -> None:
    if 'workplace_unit' in keys:
        prefix = ['source', 'family', 'workplace_unit_type', 'workplace_unit',
                  'code_unit_type', 'code_unit']
    elif 'source_parquet_sha256' in keys:
        prefix = ['source', 'profile', 'delivery_id', 'source_parquet_sha256',
                  'sample_id', 'component_year']
    else:
        prefix = [name for name in _VALIDATION_PREFIX if name in keys]
    if not prefix:
        partitions = [(lf,)]
    else:
        partitions = _validation_partitions([lf], prefix)
    for (part,) in partitions:
        if part.group_by(keys).len().filter(pl.col('len').gt(1)).select(pl.len()).collect().item():
            raise ValueError('duplicate ' + description)


def validate_statistic_keys(frame: pl.DataFrame | pl.LazyFrame) -> None:
    '''SE method and audit flags never distinguish another logical statistic.'''
    _unique(_lazy(frame), TARGET_STAT_KEY_COLUMNS, 'logical statistic key')


def _list_checks(name: str, dtype: pl.DataType) -> dict[str, pl.Expr]:
    values = pl.col(name)
    checks = {
        name + ': null list or list element': values.is_null().or_(
            values.list.eval(pl.element().is_null()).list.any()
        )
    }
    if isinstance(dtype.inner, pl.List):
        checks[name + ': empty path or null path element'] = values.list.eval(
            pl.element()
            .list.len()
            .eq(0)
            .or_(pl.element().list.eval(pl.element().is_null()).list.any())
        ).list.any()
    else:
        checks[name + ': list must be sorted distinct'] = values.ne(
            values.list.unique().list.sort()
        )
    return checks


def _decimal_invalid(column: str) -> pl.Expr:
    # Canonical fixed-point strings preserve exact sums without accepting exponent/NaN syntax.
    return (
        pl.col(column)
        .str.contains(r'^-?(0|[1-9][0-9]*)(\.[0-9]*[1-9])?$')
        .not_()
        .or_(pl.col(column).eq('-0'))
    )


def validate_auxiliary(name: str, frame: pl.DataFrame | pl.LazyFrame) -> None:
    '''Check exact ordered types, null-safe grains and explicit per-table value domains.'''
    _validate_auxiliary_rows(name, frame)
    lf = _lazy(frame)
    _unique(lf, AUXILIARY_KEYS[name], name + ' key')
    _validate_key_order(lf, AUXILIARY_KEYS[name], name + ': key sort differs')


def _validate_auxiliary_rows(name, frame):
    if name not in AUXILIARY_SCHEMAS:
        raise ValueError('unknown auxiliary table: ' + name)
    schema, lf = AUXILIARY_SCHEMAS[name], _lazy(frame)
    if list(lf.collect_schema().items()) != list(schema.items()):
        raise ValueError(name + ': ordered schema differs')
    nullable = {
        'target_units': set(UNIT_SCHEMA) - {'unit_type', 'unit', 'kind'},
        'target_support': {
            'unit_b_type',
            'unit_b',
            'cell_weight_sum_exact',
            'denominator_weight_sum_exact',
            'cell_mass',
            'fractional_support_mass',
            'native_coverage_n',
            'native_coverage_mass',
            'point_reason',
            'se_reason',
        },
        'replicate_estimates': {
            'numerator_sum_exact',
            'denominator_sum_exact',
            'estimate',
            'reason',
        },
        'eligibility_diagnostics': {'variable', 'raw_dtype', 'raw_value', 'evidence_status'},
        'allocation_residuals': set(),
    }[name]
    checks = {}
    for column, dtype in schema.items():
        if column not in nullable:
            checks[column + ': unexpected null'] = pl.col(column).is_null()
        if dtype == F:
            checks[column + ': nonfinite float'] = pl.col(column).is_finite().not_()
        if dtype == S:
            checks[column + ': blank metadata'] = pl.col(column).str.strip_chars().eq('')
        if isinstance(dtype, pl.List):
            checks.update(_list_checks(column, dtype))
    _reject(lf, checks)
    validators = {
        'target_units': _validate_units,
        'target_support': _validate_support,
        'replicate_estimates': _validate_replicates,
        'eligibility_diagnostics': _validate_diagnostics,
        'allocation_residuals': _validate_residuals,
    }
    validators[name](lf)


def _validate_units(lf: pl.LazyFrame) -> None:
    # Complete aggregate registries are small reference tables, not microdata rows.
    frame = lf.collect()
    code_rows = frame.filter(pl.col('kind').eq('observed_code')).select(
        [pl.col('code_' + name).alias(name) for name in CODE_SCHEMA]
    )
    validate_table('code', code_rows.sort(NATURAL_KEYS['code'], nulls_last=False))
    node_fields = [name for name in UNIT_SCHEMA if name.startswith('node_')]
    area_fields = ['area_type', 'state_fips', 'area_code', 'puma_vintage']
    frame_fields = [
        'population_year',
        'county_composition_year',
        'county_inventory_vintage',
        'msa_delineation',
        'cbsa_type',
    ]
    for row in frame.iter_rows(named=True):
        kind = row['kind']
        if kind not in {'observed_code', 'native_area', 'selected_node'}:
            raise ValueError('unsupported unit kind')
        if not valid_unit(row['unit_type'], row['unit']):
            raise ValueError('invalid typed unit')
        if kind == 'observed_code':
            system = row['code_system']
            expected = {'naics': 'acs_industry_category', 'soc': 'acs_occupation_category'}.get(
                system
            )
            if (
                row['unit_type'] != expected
                or row['unit'] != f"feature:{expected}:{row['code_code_lookup_id']}"
            ):
                raise ValueError('observed unit contradicts code record')
            if any(row[name] is not None for name in node_fields + area_fields + frame_fields):
                raise ValueError('observed code has unrelated unit fields')
            if row['roles'] or row['area_lookup_ids'] or row['factor_keys']:
                raise ValueError('observed code has unrelated area lists')
            for candidate, path in zip(
                row['code_canonical_finest_candidates'],
                row['code_canonical_candidate_paths'],
                strict=True,
            ):
                leaf_level = 'national_industry' if system == 'naics' else 'detailed'
                expected_leaf = (f'{system}:{row["code_canonical_vintage"]}:'
                                 f'{leaf_level}:{candidate}')
                if path[-1] != expected_leaf:
                    raise ValueError('misaligned canonical candidate paths')
            scalar, scalar_node = (
                row['code_canonical_scalar_code'],
                row['code_canonical_scalar_node_id'],
            )
            if (scalar is None) != (scalar_node is None):
                raise ValueError('incomplete canonical scalar identity')
            if scalar is not None and (
                row['code_canonical_finest_candidates'] != [scalar]
                or row['code_canonical_candidate_paths'][0][-1] != scalar_node
            ):
                raise ValueError('canonical scalar contradicts candidate path')
        else:
            for name, dtype in CODE_SCHEMA.items():
                expected = [] if isinstance(dtype, pl.List) else None
                if row['code_' + name] != expected:
                    raise ValueError('unit has unrelated code fields')
        if kind == 'native_area':
            area_type = row['area_type']
            expected = {'residence': 'residence_puma', 'work_migration': 'work_migration_puma'}
            if area_type not in expected or any(row[name] is None for name in area_fields):
                raise ValueError('incomplete native area identity')
            unit_type = expected[area_type]
            if (
                row['unit_type'] != unit_type
                or row['puma_vintage'] != 2020
                or not re.fullmatch(r'[0-9]{2}', row['state_fips'])
                or not re.fullmatch(r'[0-9]{5}', row['area_code'])
                or row['unit']
                != f"geography:2020:{unit_type}:{row['state_fips']}{row['area_code']}"
            ):
                raise ValueError('native area identity contradicts unit')
            allowed_roles = (
                {'residence'} if area_type == 'residence' else {'workplace', 'migration'}
            )
            if not row['roles'] or not set(row['roles']).issubset(allowed_roles):
                raise ValueError('native area roles contradict area type')
            if not row['area_lookup_ids'] or not row['factor_keys']:
                raise ValueError('native area missing lookup/factor provenance')
            if any(row[name] is not None for name in node_fields + frame_fields):
                raise ValueError('native area has unrelated node fields')
        if kind == 'selected_node':
            if any(row[name] is None for name in node_fields) or row['unit'] != row['node_id']:
                raise ValueError('incomplete selected node identity')
            system, vintage, level, code = row['unit'].split(':', 3)
            expected_type = level if system == 'geography' else system + '_' + level
            if (
                row['node_system'] != system
                or row['node_vintage'] != int(vintage)
                or row['node_level'] != level
                or row['node_code'] != code
                or row['unit_type'] != expected_type
                or row['unit_type']
                not in {'naics_national_industry', 'soc_detailed', 'county', 'cbsa'}
            ):
                raise ValueError('selected node fields contradict typed unit')
            if (system, int(vintage), level) != SELECTED_NODE_FRAMES[row['unit_type']]:
                raise ValueError('selected node contradicts frozen system/vintage/level frame')
            if any(row[name] is not None for name in area_fields[:3]):
                raise ValueError('selected node has unrelated native area fields')
            if row['unit_type'] in {'county', 'cbsa'}:
                frames = {'population_year': 2020, 'puma_vintage': 2020,
                          'county_composition_year': 2022, 'county_inventory_vintage': 2025}
                if any(row[name] != value for name, value in frames.items()):
                    raise ValueError('allocated unit registry has incomplete distinct frames')
                if row['unit_type'] == 'cbsa' and row['msa_delineation'] != MSA_DELINEATION:
                    raise ValueError('allocated MSA contradicts frozen delineation frame')
            elif any(row[name] is not None for name in frame_fields + ['puma_vintage']):
                raise ValueError('classification node has unrelated geographic frames')
            if row['unit_type'] == 'cbsa' and row['cbsa_type'] not in {
                'metropolitan',
                'micropolitan',
            }:
                raise ValueError('selected CBSA missing typed membership')
            if row['unit_type'] != 'cbsa' and row['cbsa_type'] is not None:
                raise ValueError('non-CBSA has CBSA membership')


def _validate_statistics(lf: pl.LazyFrame) -> None:
    _reject(
        lf,
        {
            'unsupported statistic source': pl.col('source').ne('acs'),
            'unsupported measure': pl.col('measure').is_in(MEASURES).not_(),
            'unsupported view': pl.col('view')
            .is_in(['observed', 'canonical', 'allocated_county', 'allocated_msa'])
            .not_(),
            'unsupported pool divisor': pl.col('pool_divisor').is_in([1, 2]).not_(),
        },
    )


def _validate_support(lf: pl.LazyFrame) -> None:
    _validate_statistics(lf)
    cell = pl.col('record_kind').eq('cell')
    allocated = pl.col('view').is_in(['allocated_county', 'allocated_msa'])
    canonical = pl.col('view').eq('canonical')
    defined = pl.col('point_status').eq('defined')
    se_defined = pl.col('se_status').eq('defined')
    denominator_status = pl.col('record_kind').eq('denominator_status')
    checks = {
        'unsupported support record kind': pl.col('record_kind')
        .is_in(['cell', 'denominator_status'])
        .not_(),
        'null cell endpoint': cell.and_(
            pl.col('unit_b_type').is_null().or_(pl.col('unit_b').is_null())
        ),
        'invalid denominator status': denominator_status.and_(
            pl.col('unit_b_type')
            .is_not_null()
            .or_(pl.col('unit_b').is_not_null())
            .or_(pl.col('measure').ne('forward_share'))
            .or_(pl.col('n_unweighted').ne(0))
            .or_(pl.col('denominator_n_unweighted').eq(0))
            .or_(pl.col('component_year').eq(0).and_(pl.col('denominator_mass').gt(0)))
            .or_(pl.col('point_status').ne('nonpositive_denominator'))
        ),
        'invalid pooled point domain': pl.col('component_year')
        .eq(0)
        .and_(cell)
        .and_(
            defined.and_(
                pl.col('cell_mass')
                .le(0)
                .or_(pl.col('measure').eq('forward_share').and_(pl.col('denominator_mass').le(0)))
            )
            .or_(
                pl.col('point_status').eq('no_positive_cell_mass').and_(
                    pl.col('cell_mass').gt(0).or_(pl.col('measure').eq('forward_share')
                        .and_(pl.col('denominator_mass').le(0))))
            )
            .or_(
                pl.col('point_status')
                .eq('nonpositive_denominator')
                .and_(pl.col('measure').ne('forward_share').or_(pl.col('denominator_mass').gt(0)))
            )
        ),
        'invalid full cell mass': cell.and_(
            pl.col('cell_mass').is_null().or_(pl.col('cell_mass').lt(0))
        ),
        'missing fractional cell support': cell.and_(pl.col('fractional_support_mass').is_null()),
        'negative fractional support': pl.col('fractional_support_mass')
        .lt(0)
        .or_(pl.col('denominator_fractional_support_mass').lt(0)),
        'unsupported point status': pl.col('point_status')
        .is_in(['defined', 'no_positive_cell_mass', 'nonpositive_denominator'])
        .not_(),
        'invalid point reason': defined.ne(pl.col('point_reason').is_null()),
        'unsupported SE status': pl.col('se_status')
        .is_in(['defined', 'undefined_point', 'undefined_replicates'])
        .not_(),
        'invalid SE reason': se_defined.ne(pl.col('se_reason').is_null()),
        'invalid affected replicate': pl.col('undefined_replicates')
        .list.eval(pl.element().is_in(REPLICATES).not_())
        .list.any(),
        'inconsistent undefined replicate status': pl.col('se_status')
        .eq('undefined_replicates')
        .ne(pl.col('undefined_replicates').list.len().gt(0))
        .and_(pl.col('se_status').ne('undefined_point')),
        'undefined point must have undefined SE': pl.col('point_status')
        .eq('nonpositive_denominator')
        .ne(pl.col('se_status').eq('undefined_point')),
        'noncanonical coverage fields': canonical.ne(
            pl.col('native_coverage_n').is_not_null()
        ).or_(canonical.ne(pl.col('native_coverage_mass').is_not_null())),
        'negative native coverage mass': pl.col('native_coverage_mass').lt(0),
        'missing size gate flag': pl.col('flags').list.contains('size_gate_pending').not_(),
    }
    for column in ['cell_weight_sum_exact', 'denominator_weight_sum_exact']:
        required = cell if column.startswith('cell') else pl.lit(True)
        checks[column + ': native exact/allocated null'] = allocated.and_(
            pl.col(column).is_not_null()
        ).or_(allocated.not_().and_(required).and_(pl.col(column).is_null()))
        checks[column + ': invalid exact decimal'] = _decimal_invalid(column)
    _reject(lf, checks)


def _validate_replicates(lf: pl.LazyFrame) -> None:
    _validate_statistics(lf)
    defined = pl.col('status').eq('defined')
    allocated = pl.col('view').is_in(['allocated_county', 'allocated_msa'])
    checks = {
        'unsupported replicate number': pl.col('replicate').is_in(REPLICATES).not_(),
        'unsupported replicate status': pl.col('status')
        .is_in(['defined', 'zero_denominator', 'nonfinite_ratio'])
        .not_(),
        'invalid replicate denominator status': pl.col('measure').eq('forward_share').and_(
            pl.col('denominator').eq(0).ne(pl.col('status').eq('zero_denominator'))),
        'invalid replicate reason': defined.ne(pl.col('reason').is_null()),
        'invalid replicate estimate nullability': defined.ne(pl.col('estimate').is_not_null()),
        'total replicate must be defined': pl.col('measure')
        .eq('annual_average_total')
        .and_(defined.not_()),
    }
    for column in ['numerator_sum_exact', 'denominator_sum_exact']:
        checks[column + ': native exact/allocated null'] = allocated.ne(pl.col(column).is_null())
        checks[column + ': invalid exact decimal'] = _decimal_invalid(column)
    _reject(lf, checks)


def _validate_diagnostics(lf: pl.LazyFrame) -> None:
    _reject(
        lf,
        {
            'unsupported diagnostic partition': pl.col('partition_kind')
            .is_in(['first_exclusion', 'evidence', 'limitation', 'coverage'])
            .not_(),
            'missing evidence dimensions': pl.col('partition_kind')
            .eq('evidence')
            .and_(
                pl.any_horizontal(
                    pl.col('variable').is_null(),
                    pl.col('raw_dtype').is_null(),
                    pl.col('evidence_status').is_null(),
                )
            ),
            'invalid exact diagnostic mass': _decimal_invalid('weight_sum_exact'),
            'negative diagnostic mass': pl.col('weighted_mass').lt(0),
            'unsupported diagnostic source': pl.col('source').ne('acs'),
            'invalid diagnostic source year': pl.col('component_year').is_in([2023, 2024]).not_(),
        },
    )


def _validate_residuals(lf: pl.LazyFrame) -> None:
    _reject(
        lf,
        {
            'unsupported residual type': pl.col('residual_type')
            .is_in(['micropolitan', 'no_cbsa'])
            .not_(),
            'unsupported residual replicate': pl.col('replicate').is_in([0, *REPLICATES]).not_(),
            'unsupported residual pool': pl.col('pool_divisor').is_in([1, 2]).not_(),
            'negative residual fractional support': pl.col('fractional_support_mass').lt(0),
            'unsupported residual source': pl.col('source').ne('acs'),
        },
    )


def _anti_join(left: pl.LazyFrame, right: pl.LazyFrame, keys: list[str], message: str) -> None:
    if (
        left.join(right.select(keys).unique(), on=keys, how='anti', nulls_equal=True)
        .select(pl.len())
        .collect()
        .item()
    ):
        raise ValueError(message)


def _product_registry(products: tuple[Product, ...]) -> pl.DataFrame:
    schema = {
        'product_id': S,
        'source': S,
        'family': S,
        'dimension': S,
        'view': S,
        'base_universe': S,
        'evidence_policy': S,
        'sample_set': S,
        'vintage': S,
        'universe': S,
        'pool_divisor': pl.UInt8,
        'years': pl.List(I),
    }
    rows = []
    seen = set()
    for product in products:
        if product not in PRODUCTS or product.product_id in seen:
            raise ValueError('invalid or duplicate declared product')
        identity = asdict(product)
        product_id = identity.pop('product_id')
        if _product_id(identity) != product_id:
            raise ValueError('product identity hash differs')
        seen.add(product_id)
        rows.append(
            identity
            | {
                'product_id': product_id,
                'source': 'acs',
                'universe': product.base_universe + ':' + product.evidence_policy,
            }
        )
    return pl.DataFrame(rows, schema=schema)


def _endpoint_types(product: Product) -> tuple[str, str]:
    canonical = product.view == 'canonical'
    industry = 'naics_national_industry' if canonical else 'acs_industry_category'
    occupation = 'soc_detailed' if canonical else 'acs_occupation_category'
    if product.family == 'staffing_pattern':
        return industry, occupation
    if product.family == 'commuting_flow':
        return 'residence_puma', 'work_migration_puma'
    if product.family == 'migration_flow':
        return 'work_migration_puma', 'residence_puma'
    area = {
        'observed': 'work_migration_puma',
        'canonical': 'work_migration_puma',
        'allocated_county': 'county',
        'allocated_msa': 'cbsa',
    }[product.view]
    return area, industry if product.dimension == 'industry' else occupation


def validate_cross_tables(
    tables: dict[str, pl.DataFrame | pl.LazyFrame], products: tuple[Product, ...]
) -> None:
    '''Validate aggregate grains and membership; numeric reconciliation belongs to Task 7.'''
    if set(tables) != set(AUXILIARY_SCHEMAS) | set(TARGET_TABLES):
        raise ValueError('bundle table names differ')
    for name in AUXILIARY_SCHEMAS:
        _validate_auxiliary_rows(name, tables[name])
    registry = _product_registry(products).lazy()
    units = _lazy(tables['target_units'])
    support = _lazy(tables['target_support'])
    replicates = _lazy(tables['replicate_estimates'])
    diagnostics = _lazy(tables['eligibility_diagnostics'])
    residuals = _lazy(tables['allocation_residuals'])
    product_keys = [
        'product_id',
        'source',
        'family',
        'view',
        'sample_set',
        'vintage',
        'universe',
        'pool_divisor',
    ]
    for name, lf in [('support', support), ('replicate', replicates)]:
        _anti_join(lf, registry, product_keys, name + ' has unknown product metadata')
    for name, lf in [('support', support), ('residual', residuals)]:
        selected = lf.join(registry.select('product_id', 'years'), on='product_id', how='left')
        _reject(
            selected,
            {
                name + ': invalid component year': pl.col('years')
                .is_null()
                .or_(
                    pl.col('component_year')
                    .ne(0)
                    .and_(pl.col('years').list.contains(pl.col('component_year')).not_())
                )
            },
        )
    diagnostic_keys = [
        'product_id',
        'source',
        'family',
        'dimension',
        'base_universe',
        'evidence_policy',
        'view',
    ]
    _anti_join(diagnostics, registry, diagnostic_keys, 'diagnostic has unknown product metadata')
    residual_keys = [
        'product_id',
        'source',
        'family',
        'sample_set',
        'vintage',
        'universe',
        'pool_divisor',
    ]
    _anti_join(
        residuals,
        registry.filter(pl.col('view').eq('allocated_msa')),
        residual_keys,
        'residual must belong to allocated MSA product',
    )
    typed_products = pl.DataFrame(
        [
            {
                'product_id': p.product_id,
                'expected_a': _endpoint_types(p)[0],
                'expected_b': _endpoint_types(p)[1],
            }
            for p in products
        ],
        schema={'product_id': S, 'expected_a': S, 'expected_b': S},
    ).lazy()
    checked_support = support.join(typed_products, on='product_id', how='left')
    _reject(
        checked_support,
        {
            'support endpoints contradict product': pl.col('unit_a_type')
            .ne(pl.col('expected_a'))
            .or_(
                pl.col('record_kind')
                .eq('cell')
                .and_(pl.col('unit_b_type').ne(pl.col('expected_b')))
            )
        },
    )
    for side in ('a', 'b'):
        endpoints = support.select(
            pl.col('unit_' + side + '_type').alias('unit_type'),
            pl.col('unit_' + side).alias('unit'),
        ).filter(pl.col('unit').is_not_null())
        _anti_join(
            endpoints, units, ['unit_type', 'unit'], 'support endpoint missing from unit registry'
        )
    for prefix in ('workplace', 'code'):
        endpoints = residuals.select(
            pl.col(prefix + '_unit_type').alias('unit_type'),
            pl.col(prefix + '_unit').alias('unit'),
        )
        _anti_join(
            endpoints, units, ['unit_type', 'unit'], 'residual endpoint missing from unit registry'
        )
    checked_residuals = residuals.join(
        typed_products.select('product_id', 'expected_b'), on='product_id', how='left'
    ).join(
        units.select(pl.col('unit_type').alias('workplace_unit_type'),
                     pl.col('unit').alias('workplace_unit'),
                     pl.col('kind').alias('workplace_kind'),
                     pl.col('roles').alias('workplace_roles')),
        on=['workplace_unit_type', 'workplace_unit'], how='left',
    )
    _reject(checked_residuals, {
        'residual endpoints contradict product dimension or native workplace provenance':
            pl.col('workplace_unit_type').ne('work_migration_puma')
            .or_(pl.col('code_unit_type').ne(pl.col('expected_b')))
            .or_(pl.col('workplace_kind').ne('native_area').fill_null(True))
            .or_(pl.col('workplace_roles').list.contains('workplace').not_().fill_null(True))
    })
    msa_support = support.filter(pl.col('view').eq('allocated_msa')).join(
        units.select(
            pl.col('unit_type').alias('unit_a_type'), pl.col('unit').alias('unit_a'), 'cbsa_type'
        ),
        on=['unit_a_type', 'unit_a'],
        how='left',
    )
    _reject(
        msa_support,
        {
            'allocated MSA support requires metropolitan membership': pl.col('cbsa_type')
            .ne('metropolitan')
            .fill_null(True)
        },
    )
    # Typed metropolitan membership distinguishes views within the shared allocated file.
    target_frames = []
    for name in TARGET_TABLES:
        lf = _lazy(tables[name])
        if list(lf.collect_schema().items()) != list(TARGET_SCHEMA.items()):
            raise ValueError('targets schema must match exact ordered targets-v1 types')
        if name == 'targets_allocated_area_mix':
            lf = lf.join(
                units.select(
                    pl.col('unit_type').alias('unit_a_type'),
                    pl.col('unit').alias('unit_a'),
                    'cbsa_type',
                ),
                on=['unit_a_type', 'unit_a'],
                how='left',
            )
            _reject(
                lf,
                {
                    'allocated target requires county or metropolitan CBSA': pl.col('unit_a_type')
                    .ne('county')
                    .and_(
                        pl.col('unit_a_type')
                        .ne('cbsa')
                        .or_(pl.col('cbsa_type').ne('metropolitan').fill_null(True))
                    )
                },
            )
            lf = lf.with_columns(
                pl.when(pl.col('unit_a_type').eq('county'))
                .then(pl.lit('allocated_county'))
                .otherwise(pl.lit('allocated_msa'))
                .alias('view')
            )
        else:
            lf = lf.with_columns(
                pl.lit('observed' if name == 'targets_observed' else 'canonical').alias('view')
            )
        target_frames.append(lf.select('view', *TARGET_SCHEMA))
    targets = pl.concat(target_frames)
    # This is implied by target-to-pooled membership, but reject it before filtering.
    _anti_join(targets, registry,
               ['source', 'family', 'view', 'sample_set', 'vintage', 'universe'],
               'target has unknown product metadata')
    for name, lf in [('target', targets), ('replicate', replicates)]:
        for side in ('a', 'b'):
            endpoints = lf.select(
                pl.col('unit_' + side + '_type').alias('unit_type'),
                pl.col('unit_' + side).alias('unit'),
            )
            _anti_join(endpoints, units, ['unit_type', 'unit'],
                       name + ' endpoint missing from unit registry')
    for name in AUXILIARY_SCHEMAS:
        _unique(_lazy(tables[name]), AUXILIARY_KEYS[name], name + ' key')
        _validate_key_order(tables[name], AUXILIARY_KEYS[name], name + ': key sort differs')
    for name in TARGET_TABLES:
        lf = _lazy(tables[name])
        for (part,) in _validation_partitions([lf]):
            validate_targets(part)
        validate_statistic_keys(lf)
    native_scales = _native_numeric_scales(support)
    for support_part, replicate_part, target_part in _validation_partitions(
            [support, replicates, targets]):
        _validate_statistic_relationships(support_part, replicate_part, target_part, native_scales)


def _validate_statistic_relationships(support, replicates, targets, native_scales):
    '''Keep every view, component and b code for a denominator together.'''
    pooled = support.filter(pl.col('component_year').eq(0).and_(pl.col('record_kind').eq('cell')))
    _anti_join(targets, pooled, STAT_KEY_COLUMNS, 'target missing pooled cell support')
    _anti_join(replicates, pooled, STAT_KEY_COLUMNS, 'orphan replicate statistic')
    all_cells = support.filter(pl.col('record_kind').eq('cell'))
    _anti_join(all_cells, pooled, STAT_KEY_COLUMNS, 'annual support missing pooled cell')
    status_fields = [
        'point_status',
        'point_reason',
        'se_status',
        'se_reason',
        'undefined_replicates',
    ]
    pooled_status = support.filter(pl.col('component_year').eq(0)).select(
        *STAT_KEY_COLUMNS, 'record_kind', *status_fields
    )
    _anti_join(
        support,
        pooled_status,
        [*STAT_KEY_COLUMNS, 'record_kind', *status_fields],
        'annual support differs from pooled status',
    )
    counts = replicates.group_by(STAT_KEY_COLUMNS).agg(pl.len().alias('replicate_count'))
    _reject(
        pooled.join(counts, on=STAT_KEY_COLUMNS, how='left', nulls_equal=True),
        {
            'supported statistic requires exactly 80 replicates': pl.col('replicate_count')
            .is_null()
            .or_(pl.col('replicate_count').ne(len(REPLICATES)))
        },
    )
    _anti_join(
        replicates,
        pooled,
        [*STAT_KEY_COLUMNS, 'product_id', 'pool_divisor'],
        'replicate product differs from support',
    )
    _anti_join(
        targets,
        pooled.filter(pl.col('point_status').eq('defined')),
        STAT_KEY_COLUMNS,
        'published target has undefined or withheld point support',
    )
    _anti_join(pooled.filter(pl.col('point_status').eq('defined')), targets,
               STAT_KEY_COLUMNS, 'defined support missing target')
    affected = replicates.group_by(STAT_KEY_COLUMNS).agg(
        pl.col('replicate').filter(pl.col('status').ne('defined')).sort()
        .alias('actual_undefined_replicates'))
    _reject(pooled.join(affected, on=STAT_KEY_COLUMNS, how='left', nulls_equal=True), {
        'support affected replicates differ from replicate statuses':
            pl.col('undefined_replicates').ne(pl.col('actual_undefined_replicates'))})
    target_status = targets.join(
        pooled.select(*STAT_KEY_COLUMNS, 'se_status'),
        on=STAT_KEY_COLUMNS,
        how='left',
        nulls_equal=True,
    )
    _reject(
        target_status,
        {
            'target SE method contradicts pooled support': pl.col('se_status')
            .eq('defined')
            .ne(pl.col('se_method').eq('replicate')),
            'target missing pending size gate': pl.col('flags')
            .list.contains('size_gate_pending')
            .not_(),
        },
    )

    _validate_numeric_relationships({'target_support': support}, targets, pooled, replicates,
                                    native_scales=native_scales)


def _native_numeric_scales(support):
    native = support.filter(pl.col('record_kind').eq('cell') &
                            pl.col('view').is_in(['observed', 'canonical']))
    return {column: native.select(
        pl.col(column).str.split('.').list.get(1, null_on_oob=True).str.len_chars().max()
    ).collect().item() or 0
        for column in ('cell_weight_sum_exact', 'denominator_weight_sum_exact')}


def _validate_numeric_relationships(tables, targets, pooled, replicates, *, native_scales=None):
    '''Reconcile each point, paired variance vector and exact native support decomposition.'''
    from embedding_data.acs_target_estimation import replicate_se

    total = pl.col('measure').eq('annual_average_total')
    joined = targets.join(pooled, on=STAT_KEY_COLUMNS, how='left', nulls_equal=True,
                          suffix='_support')
    expected_value = pl.when(total).then(pl.col('cell_mass')).otherwise(
        pl.col('cell_mass') / pl.col('denominator_mass'))
    _reject(joined, {
        'target point differs from support': pl.col('value').ne(expected_value),
        'target weighted support differs': pl.col('n_weighted').ne(pl.col('cell_mass')),
        'target count differs from support': pl.col('n_unweighted').ne(
            pl.col('n_unweighted_support')),
        'target flags differ from support': pl.col('flags').ne(pl.col('flags_support')),
    })
    rep = replicates.join(pooled.select(*STAT_KEY_COLUMNS, 'cell_mass', 'denominator_mass'),
                          on=STAT_KEY_COLUMNS, how='left', nulls_equal=True)
    expected_rep = pl.when(total).then(pl.col('numerator')).otherwise(
        pl.col('numerator') / pl.col('denominator'))
    _reject(rep, {'replicate estimate differs from sums': pl.col('status').eq('defined').and_(
        pl.col('estimate').ne(expected_rep))})
    vectors = replicates.group_by(STAT_KEY_COLUMNS).agg(
        pl.col('estimate').sort_by('replicate').alias('_values'))
    se = joined.join(vectors, on=STAT_KEY_COLUMNS, how='left', nulls_equal=True).with_columns(
        pl.struct('value', '_values').map_elements(
            lambda row: replicate_se(row['value'], tuple(row['_values'])),
            return_dtype=F, skip_nulls=False).alias('_expected_se'))
    _reject(se, {'target SE differs from paired replicates':
                pl.col('se').eq_missing(pl.col('_expected_se')).not_()})
    support = _lazy(tables['target_support']).filter(pl.col('record_kind').eq('cell'))
    native = support.filter(pl.col('view').is_in(['observed', 'canonical']))
    for lf, exact, mass in [(native, 'cell_weight_sum_exact', 'cell_mass'),
                            (native, 'denominator_weight_sum_exact', 'denominator_mass'),
                            (replicates.filter(pl.col('view').is_in(['observed', 'canonical'])),
                             'numerator_sum_exact', 'numerator'),
                            (replicates.filter(pl.col('view').is_in(['observed', 'canonical'])),
                             'denominator_sum_exact', 'denominator')]:
        _reject(lf, {mass + ': exact native sum differs': pl.col(mass).ne(
            pl.col(exact).cast(F) / pl.col('pool_divisor'))})
    # Decimal aggregation occurs before Float64, matching the native estimator contract.
    for column in ('cell_weight_sum_exact', 'denominator_weight_sum_exact'):
        scale = (_native_numeric_scales(support) if native_scales is None
                 else native_scales)[column]
        annual = native.filter(pl.col('component_year').ne(0)).group_by(STAT_KEY_COLUMNS).agg(
            pl.col(column).cast(pl.Decimal(38, scale)).sum().alias('_annual_sum'),
            pl.len().alias('_annual_count'))
        checked = native.filter(pl.col('component_year').eq(0)).join(
            annual, on=STAT_KEY_COLUMNS, how='left', nulls_equal=True)
        _reject(checked, {'native annual support does not close to pooled':
            pl.col(column).cast(pl.Decimal(38, scale)).ne(pl.col('_annual_sum'))
            .or_(pl.col('_annual_count').ne(pl.col('pool_divisor')))})
    annual_n = support.filter(pl.col('component_year').ne(0)).group_by(STAT_KEY_COLUMNS).agg(
        pl.col('n_unweighted').sum().alias('_annual_n'),
        pl.col('denominator_n_unweighted').sum().alias('_annual_denominator_n'))
    _reject(pooled.join(annual_n, on=STAT_KEY_COLUMNS, how='left', nulls_equal=True), {
        'annual counts differ from pooled support': pl.col('n_unweighted').ne(pl.col('_annual_n'))
            .or_(pl.col('denominator_n_unweighted').ne(pl.col('_annual_denominator_n')))})
    denominator_keys = [name for name in STAT_KEY_COLUMNS if name not in {'unit_b', 'unit_b_type'}]
    groups = support.group_by(*denominator_keys, 'component_year').agg(
        pl.col('denominator_mass').n_unique().alias('_mass_versions'),
        pl.col('denominator_n_unweighted').n_unique().alias('_count_versions'))
    _reject(groups, {'denominator group differs across cells': pl.col('_mass_versions').ne(1)
                    .or_(pl.col('_count_versions').ne(1))})
