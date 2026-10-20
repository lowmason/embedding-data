'''Independent lexical-source eligibility and bounded Decimal acceptance calculations.'''

import gzip
import hashlib
import importlib.util
import json
import math
import re
import shutil
import xml.etree.ElementTree as ET
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path

import polars as pl

_spec = importlib.util.spec_from_file_location(
    'stage9_independent_io', Path(__file__).with_name('stage9_independent_io.py')
)
io = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(io)
WEIGHTS = ['PERWT', *('REPWTP' + str(r) for r in range(1, 81))]
QFIELDS = ('QEMPSTAT', 'QIND', 'QOCC', 'QCLASSWK', 'QMIGRAT1', 'QMIGPLC1', 'QPWSTAT2', 'QTRANWOR')
PAIR = ['unit_a_type', 'unit_a', 'unit_b_type', 'unit_b']
STAT = ['view', 'source', 'family', *PAIR, 'measure', 'sample_set', 'vintage', 'universe']
DIAG_KEY = [
    'source',
    'profile',
    'delivery_id',
    'source_parquet_sha256',
    'sample_id',
    'component_year',
    'family',
    'dimension',
    'base_universe',
    'evidence_policy',
    'view',
    'product_id',
    'partition_kind',
    'variable',
    'raw_dtype',
    'raw_value',
    'evidence_status',
    'reason',
]
ALLOCATION_FLAGS = [
    'flag_geographic_allocation',
    'allocation_conditional_sampling_se',
    'allocation_error_unquantified',
    'mapping_uncertainty_unquantified',
    'population2020',
    'puma2020',
    'county_composition2022',
    'county_inventory2025',
    'msa_delineation_July_2023',
]
TRANSPORT = (
    '10',
    '11',
    '12',
    '13',
    '14',
    '15',
    '20',
    '31',
    '32',
    '33',
    '34',
    '35',
    '36',
    '37',
    '38',
    '39',
    '50',
    '60',
    '70',
)


def close_share(actual: float, expected: float) -> bool:
    return math.isfinite(actual) and math.isfinite(expected) and abs(actual - expected) <= 1e-12


def close_allocated_or_se(actual: float, expected: float) -> bool:
    return (
        math.isfinite(actual)
        and math.isfinite(expected)
        and abs(actual - expected) <= 1e-8 + 1e-12 * abs(expected)
    )


def decimal_text(value):
    text = format(value, 'f')
    return (text.rstrip('0').rstrip('.') if '.' in text else text) if value else '0'


def products():
    """The spec's 22 observed, 12 canonical and 16 allocated scientific products."""
    definitions = []
    for view in ('observed', 'canonical', 'allocated_county', 'allocated_msa'):
        if view in ('observed', 'canonical'):
            definitions.append(
                (
                    'staffing_pattern',
                    'industry_occupation',
                    view,
                    ('acs-' if view == 'observed' else '') + 'naics2022-soc2018',
                )
            )
        for dimension, code in (('industry', 'naics2022'), ('occupation', 'soc2018')):
            suffix = {
                'observed': 'puma2020',
                'canonical': 'puma2020',
                'allocated_county': 'county2025',
                'allocated_msa': 'msa2023',
            }[view]
            definitions.append(
                (
                    'area_mix',
                    dimension,
                    view,
                    ('' if view == 'canonical' else 'acs-') + code + '-' + suffix,
                )
            )
    definitions.append(('commuting_flow', 'flow', 'observed', 'residence2020-work-migration2020'))
    result = []
    periods = [
        (family, dim, view, vintage, policy, [2023, 2024])
        for family, dim, view, vintage in definitions
        for policy in ('strict', 'sensitivity')
    ]
    periods += [
        ('migration_flow', 'flow', 'observed', 'work-migration2020-residence2020', policy, years)
        for policy, years in [
            ('strict', [2024]),
            ('sensitivity', [2024]),
            ('sensitivity', [2023, 2024]),
        ]
    ]
    for family, dim, view, vintage, policy, years in periods:
        for universe in ('civilian_employed', 'private_wage_salary'):
            identity = {
                'family': family,
                'dimension': dim,
                'view': view,
                'vintage': vintage,
                'evidence_policy': policy,
                'years': years,
                'base_universe': universe,
                'sample_set': 'annual-2024' if years == [2024] else 'annual-core-2023-2024',
                'pool_divisor': len(years),
            }
            encoded = json.dumps(
                identity,
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=False,
                allow_nan=False,
            ).encode()
            result.append(dict(identity, product_id=hashlib.sha256(encoded).hexdigest()))
    return result


def flag_labels(name):
    '''Delivered lexical code/label authorities, authored independently of estimator rules.'''
    if name in ('QPWSTAT2', 'QTRANWOR'):
        return {'0': 'Not allocated', '4': 'Allocated'}
    if name == 'QMIGPLC1':
        labels = [
            'Not allocated',
            'Failed edit',
            'Failed edit/illegible',
            'Failed edit/missing',
            'Failed edit',
            'Illegible',
            'Failed edit/missing',
            'Illegible',
            'Illegible/missing or failed edit',
        ]
    else:
        original = {'QOCC': 'Entered as written', 'QMIGRAT1': 'Not allocated'}.get(
            name, 'Original entry or Inapplicable (not in universe)'
        )
        labels = [
            original,
            'Failed edit',
            'Illegible',
            'Missing',
            'Allocated',
            'Illegible',
            'Missing',
            'Original entry illegible',
            'Original entry missing or failed edit',
        ]
    return dict(zip(map(str, range(9)), labels, strict=True))


def flag_status(label):
    if 'failed edit' in label.lower():
        return 'edited_failed_edit'
    if label in ('Allocated',):
        return 'allocated'
    if label in (
        'Not allocated',
        'Entered as written',
        'Original entry or Inapplicable (not in universe)',
    ):
        return 'nonallocation'
    return 'unavailable'


def delivered_categories(file):
    root = ET.parse(file).getroot()
    variables = {}
    for variable in root.iter():
        if variable.tag.rsplit('}', 1)[-1] != 'var':
            continue
        name = variable.attrib['name']
        io.require(name not in variables, 'duplicate delivered DDI variable')
        values = {}
        for category in variable:
            if category.tag.rsplit('}', 1)[-1] == 'catgry':
                fields = {
                    c.tag.rsplit('}', 1)[-1]: ''.join(c.itertext()).strip() for c in category
                }
                key = fields.get('catValu')
                io.require(key is not None and key not in values, 'invalid delivered DDI domain')
                values[key] = fields.get('labl', '')
        variables[name] = values
    return variables


def aligned_batches(left, right):
    '''Align ordered rows without assuming equal physical scan batch boundaries.'''
    a, b = next(left, None), next(right, None)
    while a is not None and b is not None:
        count = min(a.height, b.height)
        if count:
            yield a.head(count), b.head(count)
        a = a.slice(count) if count < a.height else next(left, None)
        b = b.slice(count) if count < b.height else next(right, None)
    io.require(a is None and b is None, 'lexical source position count differs')


def prepare_sources(data_dir, mapping_directory, mapping_inputs, scratch):
    """Scan gzip CSV lexically, check all original positions, and retain core's wide weights."""
    summaries, core = {}, None
    for profile, source in mapping_inputs['sources'].items():
        citations = source['raw_citations']
        xml = [c for c in citations if c['path'].endswith('.xml')]
        csvs = [c for c in citations if c['path'].endswith('.csv.gz')]
        io.require(len(xml) == len(csvs) == 1, 'expected one raw DDI and gzip CSV')
        categories = delivered_categories(io.relative(data_dir / 'raw', xml[0]['path']))
        metadata = {v['name']: v for v in source['ddi']['variables']}
        for name, values in categories.items():
            io.require(
                name in metadata
                and values == {v['value']: v['label'] for v in metadata[name]['categories']},
                'raw DDI differs from frozen metadata',
            )
        for name in QFIELDS:
            if name in categories:
                io.require(categories[name] == flag_labels(name), 'unknown delivered Q labels')
        for name, expected in {
            'EMPSTATD': {'00': 'N/A', '10': 'At work', '12': 'Has job, not working'},
            'CLASSWKRD': {'22': 'Wage/salary, private', '23': 'Wage/salary at non-profit'},
            'MIGRATE1': {'2': 'Moved within state', '3': 'Moved between states'},
            'TRANWORK': {'00': 'N/A', '80': 'Worked at home'},
        }.items():
            io.require(
                all(categories.get(name, {}).get(k) == v for k, v in expected.items()),
                'universe categories disagree with delivered DDI',
            )
        original = io.relative(data_dir, source['parquet'])
        companion = mapping_directory / ('acs_' + profile.split('/')[1] + '_canonical.parquet')
        count = io.stage8.original_prefix(original, companion)
        io.stage8.source_identity(source, companion)
        raw_file = scratch / (profile.replace('/', '-') + '.csv')
        with gzip.open(io.relative(data_dir / 'raw', csvs[0]['path']), 'rb') as compressed:
            with raw_file.open('xb') as output:
                shutil.copyfileobj(compressed, output)
        raw = pl.scan_csv(raw_file, infer_schema=False, null_values='')
        raw_schema, original_schema = raw.collect_schema(), pl.read_parquet_schema(original)
        io.require(list(raw_schema) == list(original_schema), 'raw/original column order differs')
        io.require(all(w in raw_schema for w in WEIGHTS), 'missing numbered replicate weights')
        # No source×replicate expansion: validate one bounded row batch, then wide lazy grouping.
        scale = 0
        for lexical, converted in aligned_batches(
            raw.collect_batches(chunk_size=65536),
            pl.scan_parquet(original).collect_batches(chunk_size=65536),
        ):
            io.require(lexical.height == converted.height, 'lexical source position count differs')
            comparisons = lexical.select(
                pl.col(n).cast(t, strict=True) for n, t in original_schema.items()
            )
            io.require(comparisons.equals(converted), 'lexical/original value or order mismatch')
            for name in WEIGHTS:
                for value in lexical[name]:
                    io.require(
                        value is not None and re.fullmatch(r'-?[0-9]+(?:\.[0-9]+)?', value),
                        'invalid lexical estimator weight',
                    )
                    number = Decimal(value)
                    fractional = max(0, -number.as_tuple().exponent)
                    scale = max(scale, fractional)
                    io.require(
                        len(number.as_tuple().digits) <= 38, 'weight exceeds Decimal38 precision'
                    )
                    io.require(name != 'PERWT' or number >= 0, 'negative full weight')
        io.require(scale <= 38, 'weight scale exceeds Decimal38')
        q_summaries = {}
        scan = pl.scan_parquet(original)
        for name in QFIELDS:
            if name not in original_schema:
                q_summaries[name] = {'dtype': None, 'domain': []}
                continue
            io.require(original_schema[name] in (pl.Int64, pl.String), 'unsupported Q dtype')
            observed = scan.group_by(name).len().sort(name, nulls_last=False).collect()
            domain = {str(v) for v in observed[name] if v is not None}
            io.require(domain <= set(categories.get(name, {})), 'unknown raw Q value')
            q_summaries[name] = {
                'dtype': str(original_schema[name]),
                'domain': observed.to_dicts(),
            }
        summaries[profile] = {'rows': count, 'q_partitions': q_summaries, 'weight_scale': scale}
        if profile == 'acs/core':
            frame = pl.concat(
                [
                    pl.scan_parquet(companion).select(pl.exclude(WEIGHTS)),
                    raw.select(pl.col(w).cast(pl.Decimal(38, scale)) for w in WEIGHTS),
                ],
                how='horizontal',
            )
            core = (frame, original_schema, categories, source, xml[0])
    io.require(core is not None, 'core source absent')
    return core, summaries


def required_flags(product):
    names = ['QEMPSTAT', 'QIND', 'QOCC']
    if product['base_universe'] == 'private_wage_salary':
        names.append('QCLASSWK')
    if product['family'] in ('area_mix', 'commuting_flow'):
        names += ['QPWSTAT2', 'QTRANWOR']
    if product['family'] == 'migration_flow':
        names += ['QMIGRAT1', 'QMIGPLC1']
    return names


def semantic_frame(core):
    frame, schema, categories, _, _ = core

    def codes(name, values):
        tokens = values if schema[name] == pl.String else [int(v) for v in values]
        return pl.col(name).is_in(tokens).fill_null(False)

    usable = {
        d: pl.col(d + '_code_lookup_id').is_not_null()
        & pl.col(field).is_not_null()
        & pl.col(field).str.strip_chars().ne('')
        for d, field in [('industry', 'INDNAICS'), ('occupation', 'OCCSOC')]
    }
    applicable = {
        'QEMPSTAT': codes(
            'EMPSTATD', [v for v in categories['EMPSTATD'] if v not in ('00', '99')]
        ),
        'QCLASSWK': codes(
            'CLASSWKRD', [v for v in categories['CLASSWKRD'] if v not in ('00', '98', '99')]
        ),
        'QIND': usable['industry'],
        'QOCC': usable['occupation'],
        'QMIGRAT1': codes('MIGRATE1', ['1', '2', '3', '4']),
        'QTRANWOR': codes('TRANWORK', [*TRANSPORT, '80']),
    }
    for q, role, field in [
        ('QPWSTAT2', 'workplace', 'PWSTATE2'),
        ('QMIGPLC1', 'migration', 'MIGPLAC1'),
    ]:
        applicable[q] = (
            pl.col(role + '_state_fips').is_not_null()
            & ~pl.col(role + '_area_status').is_in(['foreign', 'territory'])
            & pl.col(field).is_not_null()
        )
    for name in QFIELDS:
        value = pl.col(name).cast(pl.String) if name in schema else pl.lit(None, pl.String)
        meanings = {key: flag_status(label) for key, label in categories.get(name, {}).items()}
        frame = frame.with_columns(
            pl.when(applicable[name].fill_null(False))
            .then(value.replace_strict(meanings, default='unavailable', return_dtype=pl.String))
            .otherwise(pl.lit('not_applicable'))
            .alias('_q_' + name)
        )
    expressions = []
    for dimension, kind in [
        ('industry', 'acs_industry_category'),
        ('occupation', 'acs_occupation_category'),
    ]:
        expressions += [
            pl.lit(kind).alias(dimension + '_kind'),
            pl.concat_str(
                pl.lit('feature:' + kind + ':'), pl.col(dimension + '_code_lookup_id')
            ).alias(dimension + '_unit'),
        ]
    for role in ('residence', 'workplace', 'migration'):
        kind = 'residence_puma' if role == 'residence' else 'work_migration_puma'
        expressions += [
            pl.lit(kind).alias(role + '_kind'),
            pl.concat_str(
                pl.lit('geography:2020:' + kind + ':'),
                pl.col(role + '_state_fips'),
                pl.col(role + '_area_code'),
            ).alias(role + '_unit'),
        ]
    return frame.with_columns(expressions), codes, usable


def classify_product(base, product, codes, usable):
    family, dimension = product['family'], product['dimension']
    dimensions = (
        ['industry', 'occupation']
        if family == 'staffing_pattern'
        else ([dimension] if family == 'area_mix' else [])
    )
    roles = {
        'staffing_pattern': [],
        'area_mix': ['workplace'],
        'commuting_flow': ['residence', 'workplace'],
        'migration_flow': ['residence', 'migration'],
    }[family]
    checks = [
        (
            (~pl.col('acs_component_year').is_in(product['years']))
            | pl.col('acs_sample_id').ne(
                pl.concat_str(
                    pl.lit('us'), pl.col('acs_component_year').cast(pl.String), pl.lit('a')
                )
            ),
            'outside_declared_period',
        ),
        (~codes('EMPSTATD', ['10', '12']), 'outside_civilian_universe'),
    ]
    if product['base_universe'] == 'private_wage_salary':
        checks.append((~codes('CLASSWKRD', ['22', '23']), 'outside_private_universe'))
    checks += [(~usable[d], 'unusable_' + d + '_category') for d in dimensions]
    if family == 'migration_flow':
        checks += [
            (codes('MIGRATE1', [v]), label)
            for v, label in [
                ('1', 'stayer'),
                ('9', 'unknown_movement'),
                ('4', 'moved_from_abroad'),
                ('0', 'movement_not_applicable'),
            ]
        ]
        checks.append((~codes('MIGRATE1', ['2', '3']), 'unknown_movement'))
    if family in ('area_mix', 'commuting_flow'):
        checks += [
            (~codes('EMPSTATD', ['10']), 'not_at_work'),
            (codes('TRANWORK', ['80']), 'worked_at_home'),
            (~codes('TRANWORK', list(TRANSPORT)), 'unusable_transport'),
        ]
    for role in roles:
        checks.append(
            (
                pl.col(role + '_area_status').ne('applicable').fill_null(True),
                pl.concat_str(
                    pl.lit(role + '_'),
                    pl.col(role + '_area_status').fill_null('documented_unavailable'),
                ),
            )
        )
        checks.append((pl.col(role + '_unit').is_null(), role + '_documented_unavailable'))
    required = required_flags(product)
    if product['evidence_policy'] == 'strict':
        checks += [
            (
                pl.col('_q_' + q).ne('nonallocation'),
                pl.concat_str(pl.lit('required_' + q + '_'), pl.col('_q_' + q)),
            )
            for q in required
        ]
    branch = pl.when(checks[0][0]).then(pl.lit(checks[0][1]))
    for condition, reason in checks[1:]:
        branch = branch.when(condition.fill_null(True)).then(
            pl.lit(reason) if isinstance(reason, str) else reason
        )
    frame = base.with_columns(branch.otherwise(pl.lit('eligible')).alias('_reason'))
    boolean_columns = [n for n, t in base.collect_schema().items() if t == pl.Boolean]
    flags = [pl.lit('size_gate_pending')]
    flags += [
        pl.when(pl.col(n).fill_null(False)).then(pl.lit(n)).otherwise(None)
        for n in boolean_columns
    ]
    flags += [
        pl.when(pl.col('_q_' + q).is_in(['allocated', 'edited_failed_edit', 'unavailable']))
        .then(pl.concat_str(pl.lit('source_evidence_' + q + '_'), pl.col('_q_' + q)))
        .otherwise(None)
        for q in required
    ]
    flags += [pl.lit(role + '_puma_specific_evidence_unavailable') for role in roles]
    left, right = {
        'staffing_pattern': ('industry', 'occupation'),
        'area_mix': ('workplace', dimension),
        'commuting_flow': ('residence', 'workplace'),
        'migration_flow': ('migration', 'residence'),
    }[family]
    frame = frame.with_columns(
        pl.col(left + '_kind').alias('unit_a_type'),
        pl.col(left + '_unit').alias('unit_a'),
        pl.col(right + '_kind').alias('unit_b_type'),
        pl.col(right + '_unit').alias('unit_b'),
        pl.concat_list(flags).list.drop_nulls().list.unique().list.sort().alias('_flags'),
    )
    return frame, dimensions, roles, boolean_columns


def aggregate(frame):
    values = (
        frame.group_by(*PAIR, 'YEAR')
        .agg(
            pl.len().alias('_n'),
            *(pl.col(w).sum() for w in WEIGHTS),
            pl.col('_flags').explode().drop_nulls().unique().sort().alias('_flags'),
        )
        .collect()
    )
    return {
        tuple(r[n] for n in PAIR) + (r['YEAR'],): {
            'weights': [r[w] for w in WEIGHTS],
            'n': r['_n'],
            'fraction': float(r['_n']),
            'flags': set(r['_flags']),
        }
        for r in values.iter_rows(named=True)
    }


def zero(allocated=False):
    return {
        'weights': [0.0 if allocated else Decimal(0) for _ in WEIGHTS],
        'n': 0,
        'fraction': 0.0,
        'flags': set(),
    }


def add(left, right):
    with localcontext() as context:
        context.prec = 80
        weights = [a + b for a, b in zip(left['weights'], right['weights'], strict=True)]
    return {
        'weights': weights,
        'n': left['n'] + right['n'],
        'fraction': left['fraction'] + right['fraction'],
        'flags': left['flags'] | right['flags'],
    }


def complete_components(annual, product):
    allocated = product['view'].startswith('allocated')
    result = dict(annual)
    for pair in sorted({k[:4] for k in annual}):
        pooled = zero(allocated)
        for year in product['years']:
            value = annual.get((*pair, year), zero(allocated))
            result[*pair, year] = value
            pooled = add(pooled, value)
        result[*pair, 0] = pooled
    return result


def denominator_groups(cells, allocated=False):
    result = {}
    for key in sorted(cells):
        denominator = key[:2] + (key[4],)
        result[denominator] = add(result.get(denominator, zero(allocated)), cells[key])
    return result


def canonical_filter(frame, dimensions, product, nodes):
    accepted = pl.lit(True)
    for dimension in dimensions:
        supported = pl.col(dimension + '_canonical_scalar_node_id').is_in(nodes[dimension])
        accepted &= supported.fill_null(False)
        if product['evidence_policy'] == 'strict':
            for field in (
                dimension + '_flag_vintage_crosswalk',
                dimension + '_source_allocated',
                'flag_source_' + dimension + '_recoded',
            ):
                if field in frame.collect_schema():
                    accepted &= ~pl.col(field).fill_null(False)
    return accepted


def diagnostic_rows(
    frame,
    product,
    source,
    ddi_citation,
    schema,
    *,
    partition,
    reason,
    variable=None,
    evidence=None,
    raw=None,
):
    keys = ['YEAR', '_raw', '_evidence', '_diagnostic_reason']
    grouped = (
        frame.with_columns(
            (
                raw
                if raw is not None
                else pl.col(variable).cast(pl.String)
                if variable in schema
                else pl.lit(None, pl.String)
            ).alias('_raw'),
            (evidence if evidence is not None else pl.lit(None, pl.String)).alias('_evidence'),
            reason.alias('_diagnostic_reason'),
        )
        .group_by(keys)
        .agg(pl.len().alias('_n'), pl.col('PERWT').sum().alias('_sum'))
        .collect()
    )
    rows = []
    for value in grouped.iter_rows(named=True):
        row = dict(
            source='acs',
            profile='acs/core',
            delivery_id=source['delivery_id'],
            source_parquet_sha256=source['parquet_record']['sha256'],
            sample_id='us' + str(value['YEAR']) + 'a',
            component_year=value['YEAR'],
            **{
                n: product[n]
                for n in (
                    'family',
                    'dimension',
                    'base_universe',
                    'evidence_policy',
                    'view',
                    'product_id',
                )
            },
            partition_kind=partition,
            variable=variable,
            raw_dtype=(
                'String'
                if variable == '_canonical_denominator'
                else str(schema[variable])
                if variable in schema
                else None
            ),
            raw_value=value['_raw'],
            evidence_status=value['_evidence'],
            reason=value['_diagnostic_reason'],
            n_unweighted=value['_n'],
            weight_sum_exact=decimal_text(value['_sum']),
            weighted_mass=float(value['_sum']) / product['pool_divisor'],
            reference_ids=[ddi_citation['path']] if partition == 'evidence' else [],
            reference_locators=[f'dataDscr/var[@name="{variable}"]']
            if partition == 'evidence'
            else [],
        )
        rows.append(row)
    return rows


def expected_native(base, core, product, nodes, codes, usable):
    frame, dimensions, roles, booleans = classify_product(base, product, codes, usable)
    _, schema, _, source, citation = core
    diagnostics = diagnostic_rows(
        frame,
        product,
        source,
        citation,
        schema,
        partition='first_exclusion',
        reason=pl.col('_reason'),
    )
    for q in QFIELDS:
        diagnostics += diagnostic_rows(
            frame,
            product,
            source,
            citation,
            schema,
            partition='evidence',
            reason=pl.col('_q_' + q),
            variable=q,
            evidence=pl.col('_q_' + q),
        )
    for name in booleans:
        diagnostics += diagnostic_rows(
            frame.filter(pl.col(name).fill_null(False)),
            product,
            source,
            citation,
            schema,
            partition='limitation',
            reason=pl.lit(name),
        )
    for role in roles:
        diagnostics += diagnostic_rows(
            frame,
            product,
            source,
            citation,
            schema,
            partition='limitation',
            reason=pl.lit(role + '_puma_specific_evidence_unavailable'),
        )
    diagnostics += diagnostic_rows(
        frame.filter(pl.col('OCCSOC').eq('559830')),
        product,
        source,
        citation,
        schema,
        partition='limitation',
        reason=pl.when(codes('EMPSTATD', ['10', '12']))
        .then(pl.lit('559830_civilian_special'))
        .otherwise(pl.lit('559830_outside_civilian')),
    )
    eligible = frame.filter(pl.col('_reason').eq('eligible'))
    coverage = {}
    if product['view'] == 'canonical':
        baseline = eligible
        if product['family'] == 'staffing_pattern':
            baseline = baseline.filter(
                pl.col('industry_canonical_scalar_node_id').is_in(nodes['industry'])
            )
            baseline = baseline.with_columns(
                pl.col('industry_canonical_scalar_node_id').alias('unit_a'),
                pl.lit('naics_national_industry').alias('unit_a_type'),
            )
        coverage = denominator_groups(complete_components(aggregate(baseline), product))
        accepted = canonical_filter(eligible, dimensions, product, nodes)
        diagnostics += diagnostic_rows(
            eligible.filter(~accepted),
            product,
            source,
            citation,
            schema,
            partition='coverage',
            reason=pl.lit('canonical_unsupported_or_policy_excluded'),
        )
        baseline_accepted = canonical_filter(baseline, dimensions, product, nodes)
        diagnostics += diagnostic_rows(
            baseline.filter(~baseline_accepted),
            product,
            source,
            citation,
            schema,
            partition='coverage',
            reason=pl.lit('canonical_denominator_loss'),
            variable='_canonical_denominator',
            raw=pl.col('unit_a'),
        )
        eligible = eligible.filter(accepted)
        for dimension in dimensions:
            side = (
                'a' if product['family'] == 'staffing_pattern' and dimension == 'industry' else 'b'
            )
            eligible = eligible.with_columns(
                pl.lit(
                    'naics_national_industry' if dimension == 'industry' else 'soc_detailed'
                ).alias('unit_' + side + '_type'),
                pl.col(dimension + '_canonical_scalar_node_id').alias('unit_' + side),
            )
    return complete_components(aggregate(eligible), product), coverage, diagnostics


def allocation(native, product, factors, counties, *, measurements=None):
    '''County first, then typed MSA; source-support sets prevent county double counting.'''
    county = {}
    contributions = defaultdict(list)
    residual = defaultdict(list)
    for key in sorted(native):
        _, origin, code_type, code, year = key
        origin_factors = factors.get(origin, [])
        io.require(
            origin_factors and close_share(sum(f for _, f in origin_factors), 1.0),
            'workplace factors do not cover native origin',
        )
        for county_id, factor in sorted(origin_factors):
            if factor == 0:
                continue
            facts = counties[county_id]
            value = native[key]
            flags = value['flags'] | set(ALLOCATION_FLAGS)
            if factor < 1:
                flags.add('flag_fractional_split')
            contribution = {
                'weights': [float(w) * factor for w in value['weights']],
                'n': value['n'],
                'fraction': value['n'] * factor,
                'flags': flags,
            }
            destination = ('county', county_id, code_type, code, year)
            county[destination] = add(county.get(destination, zero(True)), contribution)
            if facts['cbsa_type'] == 'metropolitan':
                contributions['cbsa', facts['cbsa_id'], code_type, code, year].append(
                    (origin, county_id, contribution)
                )
            else:
                kind = 'micropolitan' if facts['cbsa_type'] == 'micropolitan' else 'no_cbsa'
                residual[origin, code_type, code, year, kind].append((county_id, contribution))
    if product['view'] == 'allocated_county':
        allocation_checks(native, county, {}, [], product, measurements)
        return county, []
    metro = {}
    county_rollups = defaultdict(list)
    for county_key in sorted(county):
        membership = counties[county_key[1]]
        if membership['cbsa_type'] == 'metropolitan':
            county_rollups['cbsa', membership['cbsa_id'], *county_key[2:]].append(
                county[county_key]
            )
    for key in sorted(contributions):
        dest = zero(True)
        seen = set()
        for origin, county_id, value in sorted(contributions[key], key=lambda r: (r[0], r[1])):
            dest['fraction'] += value['fraction']
            dest['flags'] |= value['flags']
            if origin not in seen:
                dest['n'] += value['n']
                seen.add(origin)
        # Sum already allocated counties in their explicit typed county order.
        for value in county_rollups[key]:
            dest['weights'] = [
                a + b for a, b in zip(dest['weights'], value['weights'], strict=True)
            ]
        metro[key] = dest
    rows = []
    for (origin, code_type, code, year, kind), entries in sorted(residual.items()):
        combined = zero(True)
        for _, value in sorted(entries):
            combined = add(combined, value)
        # n is input support, so one origin is counted only once per residual kind.
        combined['n'] = entries[0][1]['n']
        for rep in range(81):
            rows.append(
                dict(
                    source='acs',
                    family='area_mix',
                    workplace_unit_type='work_migration_puma',
                    workplace_unit=origin,
                    code_unit_type=code_type,
                    code_unit=code,
                    sample_set=product['sample_set'],
                    vintage=product['vintage'],
                    universe=product['base_universe'] + ':' + product['evidence_policy'],
                    product_id=product['product_id'],
                    component_year=year,
                    replicate=rep,
                    residual_type=kind,
                    pool_divisor=product['pool_divisor'],
                    weighted_mass=combined['weights'][rep] / product['pool_divisor'],
                    n_input_support=combined['n'],
                    fractional_support_mass=combined['fraction'],
                    flags=sorted(combined['flags']),
                )
            )
    allocation_checks(native, county, metro, rows, product, measurements)
    return metro, rows


def allocation_checks(native, county, metro, residuals, product, measurements):
    if measurements is None:
        measurements = []
    native_vectors, county_vectors, metro_vectors = {}, {}, {}
    with localcontext() as context:
        context.prec = 80
        for key in sorted(native):
            group = key[2:]
            vector = native_vectors.setdefault(group, [Decimal(0)] * 81)
            native_vectors[group] = [
                a + b for a, b in zip(vector, native[key]['weights'], strict=True)
            ]
    for cells, destination in ((county, county_vectors), (metro, metro_vectors)):
        for key in sorted(cells):
            vector = destination.setdefault(key[2:], [0.0] * 81)
            destination[key[2:]] = [
                a + b for a, b in zip(vector, cells[key]['weights'], strict=True)
            ]
    residual_vectors = {}
    for row in sorted(
        residuals,
        key=lambda r: (
            r['workplace_unit'],
            r['residual_type'],
            r['code_unit_type'],
            r['code_unit'],
            r['component_year'],
            r['replicate'],
        ),
    ):
        group = row['code_unit_type'], row['code_unit'], row['component_year']
        vector = residual_vectors.setdefault(group, [0.0] * 81)
        vector[row['replicate']] += row['weighted_mass']
    k = product['pool_divisor']
    for group, native_vector in sorted(native_vectors.items()):
        code_type, code, year = group
        for rep in range(81):
            county_mass = county_vectors.get(group, [0.0] * 81)[rep] / k
            metro_mass = metro_vectors.get(group, [0.0] * 81)[rep] / k
            residual_mass = residual_vectors.get(group, [0.0] * 81)[rep]
            comparisons = [('native_to_county', float(native_vector[rep]) / k, county_mass)]
            if product['view'] == 'allocated_msa':
                comparisons.append(
                    (
                        'county_to_msa_and_residuals',
                        county_mass,
                        math.fsum((metro_mass, residual_mass)),
                    )
                )
            for check, expected, actual in comparisons:
                measurements.append(
                    {
                        'product_id': product['product_id'],
                        'code_unit_type': code_type,
                        'code_unit': code,
                        'component_year': year,
                        'replicate': rep,
                        'check': check,
                        'expected_mass': expected,
                        'actual_mass': actual,
                        'status': 'pass' if close_allocated_or_se(actual, expected) else 'fail',
                    }
                )


def statistic_metadata(product, pair, measure):
    return dict(
        view=product['view'],
        source='acs',
        family=product['family'],
        **dict(zip(PAIR, pair, strict=True)),
        measure=measure,
        sample_set=product['sample_set'],
        vintage=product['vintage'],
        universe=product['base_universe'] + ':' + product['evidence_policy'],
    )


def finalize(cells, coverage, product):
    '''All 80 ratios and SDR errors are recomputed from independently grouped native sums.'''
    allocated = product['view'].startswith('allocated')
    denominator = denominator_groups(cells, allocated)
    support, replicates, targets = [], [], []
    k = product['pool_divisor']
    for pair in sorted({key[:4] for key in cells}):
        pooled = cells[*pair, 0]
        den = denominator[*pair[:2], 0]
        for measure in ('annual_average_total', 'forward_share'):
            metadata = statistic_metadata(product, pair, measure)
            total = measure == 'annual_average_total'
            masses = [float(v) / k for v in pooled['weights']]
            den_masses = [float(v) / k for v in den['weights']]
            point = (
                masses[0] if total else masses[0] / den_masses[0] if den_masses[0] > 0 else None
            )
            values, undefined = [], []
            for rep in range(1, 81):
                value = (
                    masses[rep]
                    if total
                    else masses[rep] / den_masses[rep]
                    if den_masses[rep] != 0
                    else None
                )
                reason = (
                    'zero_denominator'
                    if value is None
                    else 'nonfinite_ratio'
                    if not math.isfinite(value)
                    else None
                )
                if reason:
                    value = None
                    undefined.append(rep)
                values.append(value)
                replicates.append(
                    dict(
                        metadata,
                        product_id=product['product_id'],
                        replicate=rep,
                        numerator_sum_exact=None
                        if allocated
                        else decimal_text(pooled['weights'][rep]),
                        denominator_sum_exact=None
                        if allocated
                        else decimal_text(den['weights'][rep]),
                        pool_divisor=k,
                        numerator=masses[rep],
                        denominator=den_masses[rep],
                        estimate=value,
                        status='defined' if reason is None else reason,
                        reason=reason,
                    )
                )
            point_status = (
                'nonpositive_denominator'
                if point is None
                else 'defined'
                if masses[0] > 0
                else 'no_positive_cell_mass'
            )
            se_status = (
                'undefined_point'
                if point is None
                else 'undefined_replicates'
                if undefined
                else 'defined'
            )
            se = (
                math.sqrt(0.05 * math.fsum((value - point) ** 2 for value in values))
                if se_status == 'defined'
                else None
            )
            flags = sorted(pooled['flags'])
            for year in [0, *product['years']]:
                cell, d = cells[*pair, year], denominator[*pair[:2], year]
                baseline = coverage.get((*pair[:2], year))
                support.append(
                    dict(
                        metadata,
                        record_kind='cell',
                        component_year=year,
                        product_id=product['product_id'],
                        pool_divisor=k,
                        n_unweighted=cell['n'],
                        denominator_n_unweighted=d['n'],
                        cell_weight_sum_exact=None
                        if allocated
                        else decimal_text(cell['weights'][0]),
                        denominator_weight_sum_exact=None
                        if allocated
                        else decimal_text(d['weights'][0]),
                        cell_mass=float(cell['weights'][0]) / k,
                        denominator_mass=float(d['weights'][0]) / k,
                        fractional_support_mass=cell['fraction'],
                        denominator_fractional_support_mass=d['fraction'],
                        native_coverage_n=baseline['n'] if baseline else None,
                        native_coverage_mass=float(baseline['weights'][0]) / k
                        if baseline
                        else None,
                        point_status=point_status,
                        point_reason=None if point_status == 'defined' else point_status,
                        se_status=se_status,
                        se_reason=None if se_status == 'defined' else se_status,
                        undefined_replicates=undefined,
                        support_semantics='annual_average_contribution',
                        flags=sorted(cell['flags']),
                    )
                )
            if point_status == 'defined':
                targets.append(
                    dict(
                        {n: v for n, v in metadata.items() if n != 'view'},
                        value=point,
                        se=se,
                        se_method='replicate' if se is not None else 'none',
                        n_unweighted=pooled['n'],
                        n_weighted=masses[0],
                        flags=flags,
                    )
                )
    bad_pooled = {
        key[:2]
        for key, value in denominator.items()
        if key[2] == 0 and float(value['weights'][0]) <= 0 and value['n'] > 0
    }
    for (kind, unit, year), den in sorted(denominator.items()):
        if (kind, unit) in bad_pooled and den['n'] > 0:
            baseline = coverage.get((kind, unit, year))
            support.append(
                dict(
                    statistic_metadata(product, (kind, unit, None, None), 'forward_share'),
                    record_kind='denominator_status',
                    component_year=year,
                    product_id=product['product_id'],
                    pool_divisor=k,
                    n_unweighted=0,
                    denominator_n_unweighted=den['n'],
                    cell_weight_sum_exact=None if allocated else '0',
                    denominator_weight_sum_exact=None
                    if allocated
                    else decimal_text(den['weights'][0]),
                    cell_mass=0.0,
                    denominator_mass=float(den['weights'][0]) / k,
                    fractional_support_mass=0.0,
                    denominator_fractional_support_mass=den['fraction'],
                    native_coverage_n=baseline['n'] if baseline else None,
                    native_coverage_mass=float(baseline['weights'][0]) / k if baseline else None,
                    point_status='nonpositive_denominator',
                    point_reason='nonpositive_denominator',
                    se_status='undefined_point',
                    se_reason='undefined_point',
                    undefined_replicates=[],
                    support_semantics='annual_average_contribution',
                    flags=sorted(den['flags']),
                )
            )
    return support, replicates, targets
