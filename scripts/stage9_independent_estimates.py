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
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import NamedTuple

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
                values[key] = fields.get('labl') or None
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
    grouped = _diagnostic_plan(
        frame, variable=variable, evidence=evidence, raw=raw, reason=reason, schema=schema
    ).collect()
    return [
        _diagnostic_record(
            value, product, source, ddi_citation, schema, partition=partition, variable=variable
        )
        for value in grouped.iter_rows(named=True)
    ]


def _diagnostic_plan(frame, *, variable, evidence, raw, reason, schema):
    keys = ['YEAR', '_raw', '_evidence', '_diagnostic_reason']
    return (
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
    )


def _diagnostic_record(value, product, source, ddi_citation, schema, *, partition, variable):
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
    return row


def expected_native(base, core, product, nodes, codes, usable):
    eligible, baseline, plans = _native_plans(base, core, product, nodes, codes, usable)
    coverage = (
        denominator_groups(complete_components(aggregate(baseline), product))
        if baseline is not None
        else {}
    )
    diagnostics = [row for args, kwargs in plans for row in diagnostic_rows(*args, **kwargs)]
    return complete_components(aggregate(eligible), product), coverage, diagnostics


def _diagnostic_request(*args, **kwargs):
    return [(args, kwargs)]


def _native_plans(base, core, product, nodes, codes, usable):
    frame, dimensions, roles, booleans = classify_product(base, product, codes, usable)
    _, schema, _, source, citation = core
    diagnostics = _diagnostic_request(
        frame,
        product,
        source,
        citation,
        schema,
        partition='first_exclusion',
        reason=pl.col('_reason'),
    )
    for q in QFIELDS:
        diagnostics += _diagnostic_request(
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
        diagnostics += _diagnostic_request(
            frame.filter(pl.col(name).fill_null(False)),
            product,
            source,
            citation,
            schema,
            partition='limitation',
            reason=pl.lit(name),
        )
    for role in roles:
        diagnostics += _diagnostic_request(
            frame,
            product,
            source,
            citation,
            schema,
            partition='limitation',
            reason=pl.lit(role + '_puma_specific_evidence_unavailable'),
        )
    diagnostics += _diagnostic_request(
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
    baseline = None
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
        accepted = canonical_filter(eligible, dimensions, product, nodes)
        diagnostics += _diagnostic_request(
            eligible.filter(~accepted),
            product,
            source,
            citation,
            schema,
            partition='coverage',
            reason=pl.lit('canonical_unsupported_or_policy_excluded'),
        )
        baseline_accepted = canonical_filter(baseline, dimensions, product, nodes)
        diagnostics += _diagnostic_request(
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
    return eligible, baseline, diagnostics


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
    denominator = denominator_groups(cells, product['view'].startswith('allocated'))
    return _finalize_values(cells, coverage, product, denominator)


def _finalize_values(cells, coverage, product, denominator, *, include_status=True):
    '''All 80 ratios and SDR errors are recomputed from independently grouped native sums.'''
    allocated = product['view'].startswith('allocated')
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
        if include_status and key[2] == 0 and float(value['weights'][0]) <= 0 and value['n'] > 0
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


class _FactTable(NamedTuple):
    owner: Path
    paths: tuple[Path, ...]
    schema: pl.Schema
    keys: tuple[str, ...]
    product_id: str
    weight_kind: str | None


class _NativeFacts(NamedTuple):
    owner: Path
    cells: _FactTable
    denominators: _FactTable
    coverage: _FactTable | None
    diagnostics: _FactTable


def _fact_schema(keys, weight_kind):
    return pl.Schema(
        {
            **dict.fromkeys(keys, pl.String),
            'component_year': pl.Int64,
            'weights': pl.List(pl.String if weight_kind == 'decimal_text' else pl.Float64),
            'n': pl.UInt64,
            'fraction': pl.Float64,
            'flags': pl.List(pl.String),
        }
    )


def _check_product(product, batch_rows):
    io.require(type(batch_rows) is int and batch_rows > 0, 'invalid batch_rows')
    io.require(
        isinstance(product, dict) and type(product.get('pool_divisor')) is int
        and type(product.get('years')) is list
        and all(type(year) is int for year in product['years'])
        and product in products(),
        'product identity/years/divisor differs',
    )
    return 'float64' if product['view'].startswith('allocated') else 'decimal_text'


@contextmanager
def _owned(workspace, label):
    workspace = io.safe(Path(workspace))
    io.require(workspace.is_dir(), 'workspace must be an existing directory')
    io.identifier(label)
    owner = io.safe(workspace / label)
    owner.mkdir()
    try:
        yield owner
    except BaseException:
        shutil.rmtree(owner)
        raise


def _sink(frame, path):
    io.safe(path)
    with path.open('xb') as output:
        frame.sink_parquet(output, engine='streaming', maintain_order=True)


class _FactWriter:
    '''Bounded aggregate rows; paths alone survive between flushed fragments.'''

    def __init__(self, owner, label, schema, keys, product_id, kind, batch_rows):
        self.owner, self.label, self.schema = owner, label, pl.Schema(schema)
        self.keys, self.product_id, self.kind = tuple(keys), product_id, kind
        self.batch_rows, self.rows, self.paths = batch_rows, [], []

    def append(self, row):
        io.require(set(row) == set(self.schema), 'output row/schema columns differ')
        self.rows.append(row)
        if len(self.rows) == self.batch_rows:
            self.flush()

    def flush(self):
        path = self.owner / f'{self.label}-{len(self.paths):08d}.parquet'
        _sink(pl.DataFrame(self.rows, schema=self.schema).lazy(), path)
        self.paths.append(path)
        self.rows.clear()

    def finish(self, *, sort=False):
        if self.rows or not self.paths:
            self.flush()
        if sort:
            path = self.owner / (self.label + '-ordered.parquet')
            _sink(pl.scan_parquet(self.paths, glob=False).sort(self.keys, nulls_last=False), path)
            for old in self.paths:
                old.unlink()
            self.paths = [path]
        return _FactTable(
            self.owner, tuple(self.paths), self.schema, self.keys, self.product_id, self.kind
        )


def _rows(frame, batch_rows):
    for batch in frame.collect_batches(
        chunk_size=batch_rows, engine='streaming', maintain_order=True, lazy=True
    ):
        yield from batch.iter_rows(named=True)


def _fact_rows(table, product, batch_rows, *, pair):
    kind = _check_product(product, batch_rows)
    keys = tuple([*(PAIR if pair else PAIR[:2]), 'component_year'])
    io.require(
        table.product_id == product['product_id'] and table.weight_kind == kind,
        'fact product/weight kind differs',
    )
    schema = _fact_schema(PAIR if pair else PAIR[:2], kind)
    io.require(table.schema == schema and table.keys == keys, 'fact schema/grain differs')
    owner = io.safe(table.owner)
    io.require(owner.is_dir() and bool(table.paths), 'missing fact owner/paths')
    for path in table.paths:
        path = io.safe(Path(path))
        io.require(path.is_relative_to(owner) and path.is_file(), 'unsafe fact path')
        io.require(pl.read_parquet_schema(path) == schema, 'physical fact schema differs')
    previous, current, components = None, None, []
    expected = sorted([0, *product['years']])
    for row in _rows(pl.scan_parquet(table.paths, glob=False), batch_rows):
        key = tuple(row[n] for n in keys)
        io.require(all(v is not None for v in key), 'null fact key')
        io.require(previous is None or key > previous, 'duplicate/out-of-order fact key')
        group = key[:-1]
        if group != current:
            if current is not None:
                io.require(components == expected, 'missing final component')
            current, components = group, []
        components.append(key[-1])
        io.require(components == expected[: len(components)], 'invalid component order/year')
        weights = row['weights']
        io.require(
            weights is not None
            and len(weights) == len(WEIGHTS)
            and all(v is not None for v in weights),
            'invalid weight vector length/null',
        )
        if kind == 'decimal_text':
            io.require(all(re.fullmatch(r'-?[0-9]+(?:\.[0-9]+)?', text) for text in weights),
                       'noncanonical decimal vector')
            try:
                values = [Decimal(v) for v in weights]
            except InvalidOperation as exc:
                raise ValueError('invalid decimal vector') from exc
            io.require(
                all(
                    v.is_finite() and decimal_text(v) == text
                    for v, text in zip(values, weights, strict=True)
                ),
                'noncanonical/nonfinite decimal vector',
            )
        else:
            values = weights
            io.require(all(math.isfinite(v) for v in values), 'nonfinite float vector')
        io.require(
            row['n'] is not None
            and row['fraction'] is not None
            and math.isfinite(row['fraction']),
            'invalid support value',
        )
        flags = row['flags']
        io.require(
            flags is not None
            and all(isinstance(v, str) for v in flags)
            and flags == sorted(set(flags)),
            'invalid flags',
        )
        previous = key
        yield (
            key,
            {'weights': values, 'n': row['n'], 'fraction': row['fraction'], 'flags': set(flags)},
        )
    if current is not None:
        io.require(components == expected, 'missing final component')


def _fact_row(keys, key, value, kind):
    return dict(zip(keys, key, strict=True)) | {
        'weights': [decimal_text(v) for v in value['weights']]
        if kind == 'decimal_text'
        else value['weights'],
        'n': value['n'],
        'fraction': value['fraction'],
        'flags': sorted(value['flags']),
    }


def _complete_annual_rows(rows, product):
    '''One actual pair carry; undeclared, repeated and disordered tails fail immediately.'''
    pair, annual, previous = None, {}, None
    for row in rows:
        key = tuple(row[n] for n in [*PAIR, 'YEAR'])
        io.require(all(v is not None for v in key), 'null annual key')
        io.require(previous is None or key > previous, 'duplicate/out-of-order annual key')
        io.require(key[-1] in product['years'], 'undeclared annual year')
        if pair is not None and key[:4] != pair:
            yield pair, complete_components(annual, product)
            annual = {}
        pair, previous = key[:4], key
        annual[key] = {
            'weights': [row[w] for w in WEIGHTS],
            'n': row['_n'],
            'fraction': float(row['_n']),
            'flags': set(row['_flags']),
        }
        io.require(len(annual) <= len(product['years']), 'oversized annual carry')
    if pair is not None:
        yield pair, complete_components(annual, product)


def _complete_native_facts(frame, product, workspace, *, batch_rows=4096, label='cells'):
    io.require(_check_product(product, batch_rows) == 'decimal_text', 'native product required')
    with _owned(workspace, 'completed-' + io.identifier(label)) as owner:
        annual = owner / 'annual.parquet'
        grouped = (
            frame.group_by(*PAIR, 'YEAR')
            .agg(
                pl.len().alias('_n'),
                *(pl.col(w).sum() for w in WEIGHTS),
                pl.col('_flags').explode().drop_nulls().unique().sort().alias('_flags'),
            )
            .sort([*PAIR, 'YEAR'])
        )
        _sink(grouped, annual)
        keys = [*PAIR, 'component_year']
        writer = _FactWriter(
            owner,
            'cells',
            _fact_schema(PAIR, 'decimal_text'),
            keys,
            product['product_id'],
            'decimal_text',
            batch_rows,
        )
        for _, completed in _complete_annual_rows(
            _rows(pl.scan_parquet(annual), batch_rows), product
        ):
            for key in sorted(completed):
                writer.append(_fact_row(keys, key, completed[key], 'decimal_text'))
        result = writer.finish()
        annual.unlink()
        return result


def _denominator_facts(cells, product, workspace, *, label='denominators', batch_rows=4096):
    kind = _check_product(product, batch_rows)
    with _owned(workspace, 'independent-' + io.identifier(label)) as owner:
        keys = [*PAIR[:2], 'component_year']
        writer = _FactWriter(
            owner,
            'denominators',
            _fact_schema(PAIR[:2], kind),
            keys,
            product['product_id'],
            kind,
            batch_rows,
        )
        current, values = None, {}
        for key, cell in _fact_rows(cells, product, batch_rows, pair=True):
            if current is not None and key[:2] != current:
                for year in sorted(values):
                    writer.append(_fact_row(keys, (*current, year), values[year], kind))
                values = {}
            current = key[:2]
            year = key[-1]
            values[year] = add(values.get(year, zero(kind == 'float64')), cell)
        if current is not None:
            for year in sorted(values):
                writer.append(_fact_row(keys, (*current, year), values[year], kind))
        return writer.finish()


def _group_facts(table, product, batch_rows, *, pair):
    group, values = None, {}
    for key, value in _fact_rows(table, product, batch_rows, pair=pair):
        if group is not None and key[:-1] != group:
            yield group, values
            values = {}
        group = key[:-1]
        values[key] = value
    if group is not None:
        yield group, values


class _FactMerge:
    def __init__(self, groups):
        self.groups = iter(groups)
        self.current = next(self.groups, None)

    def take(self, key):
        while self.current is not None and self.current[0] < key:
            self.current = next(self.groups, None)
        if self.current is not None and self.current[0] == key:
            return self.current[1]
        return {}

    def drain(self):
        for _ in self.groups:
            pass
        self.current = None


def _finalize_disk(cells, denominators, coverage, product, workspace, *, schemas, batch_rows=4096):
    _check_product(product, batch_rows)
    io.require(
        set(schemas) >= {'target_support', 'replicate_estimates', 'targets'},
        'missing independent output schema',
    )
    if coverage is not None:
        io.require(product['view'] == 'canonical', 'coverage only for canonical product')
    with _owned(workspace, 'independent-final-' + product['product_id']) as owner:
        keys = {
            'target_support': [*STAT, 'record_kind', 'component_year'],
            'replicate_estimates': [*STAT, 'replicate'],
            'targets': [n for n in STAT if n != 'view'],
        }
        writers = {
            name: _FactWriter(
                owner, name, schemas[name], key, product['product_id'], None, batch_rows
            )
            for name, key in keys.items()
        }
        den_groups = iter(_group_facts(denominators, product, batch_rows, pair=False))
        den = next(den_groups, None)
        cov = _FactMerge(
            _group_facts(coverage, product, batch_rows, pair=False) if coverage is not None else []
        )

        emitted_a = None

        def emit_status(group):
            a, values = group
            rows, _, _ = _finalize_values({}, cov.take(a), product, values)
            for row in rows:
                writers['target_support'].append(row)

        for pair, values in _group_facts(cells, product, batch_rows, pair=True):
            while den is not None and den[0] < pair[:2]:
                if emitted_a != den[0]:
                    emit_status(den)
                den = next(den_groups, None)
            io.require(den is not None and den[0] == pair[:2], 'missing matching denominator')
            if emitted_a != den[0]:
                emit_status(den)
                emitted_a = den[0]
            output = _finalize_values(
                values, cov.take(pair[:2]), product, den[1], include_status=False
            )
            for name, rows in zip(writers, output, strict=True):
                for row in rows:
                    writers[name].append(row)
        if den is not None:
            if emitted_a != den[0]:
                emit_status(den)
            for group in den_groups:
                emit_status(group)
        cov.drain()
        return {name: writer.finish(sort=True) for name, writer in writers.items()}


def _expected_native_disk(
    base, core, product, nodes, codes, usable, workspace, *, diagnostic_schema, batch_rows=4096
):
    io.require(_check_product(product, batch_rows) == 'decimal_text', 'native product required')
    with _owned(workspace, 'independent-native-' + product['product_id']) as owner:
        eligible, baseline, plans = _native_plans(base, core, product, nodes, codes, usable)
        cells = _complete_native_facts(eligible, product, owner, batch_rows=batch_rows)
        denominators = _denominator_facts(cells, product, owner, batch_rows=batch_rows)
        coverage = None
        if baseline is not None:
            baseline_cells = _complete_native_facts(
                baseline, product, owner, batch_rows=batch_rows, label='baseline'
            )
            coverage = _denominator_facts(
                baseline_cells, product, owner, label='coverage', batch_rows=batch_rows
            )
            shutil.rmtree(baseline_cells.owner)
        writer = _FactWriter(
            owner,
            'diagnostics',
            diagnostic_schema,
            DIAG_KEY,
            product['product_id'],
            None,
            batch_rows,
        )
        for args, kwargs in plans:
            frame, _, source, citation, schema = args
            plan = _diagnostic_plan(
                frame,
                variable=kwargs.get('variable'),
                evidence=kwargs.get('evidence'),
                raw=kwargs.get('raw'),
                reason=kwargs['reason'],
                schema=schema,
            )
            for value in _rows(plan, batch_rows):
                writer.append(
                    _diagnostic_record(
                        value,
                        product,
                        source,
                        citation,
                        schema,
                        partition=kwargs['partition'],
                        variable=kwargs.get('variable'),
                    )
                )
        diagnostics = writer.finish(sort=True)
        return _NativeFacts(owner, cells, denominators, coverage, diagnostics)


class _AllocationFacts(NamedTuple):
    owner: Path
    cells: _FactTable
    denominators: _FactTable
    residuals: _FactTable
    diagnostics: _FactTable
    measurements: _FactTable


def _allocation_ordered(table, owner, label, keys, batch_rows):
    path = owner / (label + '.parquet')
    _sink(pl.scan_parquet(table.paths, glob=False).sort(keys, nulls_last=False), path)
    return _rows(pl.scan_parquet(path, glob=False), batch_rows)


def _allocation_reduce(rows, keys, *, metadata=False, residual=False):
    '''One complete vector carry; input order is the original independent arithmetic order.'''
    current, value, previous_origin, origin_n, first_n = None, None, None, None, None
    for row in rows:
        key = tuple(row[n] for n in keys)
        if key != current:
            if current is not None:
                if residual:
                    value['n'] = first_n
                yield current, value
            current, value = key, zero(True)
            previous_origin, origin_n, first_n = None, None, row['n']
        incoming = {n: row[n] for n in ('weights', 'n', 'fraction')} | {'flags': set(row['flags'])}
        if metadata:
            value['fraction'] += incoming['fraction']
            value['flags'] |= incoming['flags']
            if previous_origin != row['origin']:
                value['n'] += incoming['n']
                previous_origin, origin_n = row['origin'], incoming['n']
            io.require(origin_n == incoming['n'], 'inconsistent native origin support')
        else:
            value = add(value, incoming)
    if current is not None:
        if residual:
            value['n'] = first_n
        yield current, value


def _allocation_summary(table, product, owner, label, batch_rows, *, residual=False):
    group = (
        ['code_unit_type', 'code_unit', 'component_year']
        if residual
        else ['unit_b_type', 'unit_b', 'component_year']
    )
    order = group + (['workplace_unit', 'residual_type', 'replicate'] if residual else PAIR[:2])
    rows = _allocation_ordered(table, owner, label, order, batch_rows)
    current, vector = None, None
    decimal = table.weight_kind == 'decimal_text'
    for row in rows:
        key = tuple(row[n] for n in group)
        if key != current:
            if current is not None:
                yield current, vector
            current, vector = key, [Decimal(0) if decimal else 0.0] * 81
        if residual:
            vector[row['replicate']] += row['weighted_mass']
        else:
            values = [Decimal(v) for v in row['weights']] if decimal else row['weights']
            with localcontext() as context:
                context.prec = 80
                vector = [a + b for a, b in zip(vector, values, strict=True)]
    if current is not None:
        yield current, vector


def _allocation_measurements(
    native, county, metro, residuals, observed, product, owner, batch_rows
):
    schema = pl.Schema(
        {
            'product_id': pl.String,
            'code_unit_type': pl.String,
            'code_unit': pl.String,
            'component_year': pl.Int64,
            'replicate': pl.UInt8,
            'check': pl.String,
            'expected_mass': pl.Float64,
            'actual_mass': pl.Float64,
            'status': pl.String,
            '_check_order': pl.UInt8,
        }
    )
    keys = ('code_unit_type', 'code_unit', 'component_year', 'replicate', '_check_order')
    writer = _FactWriter(
        owner, 'measurements', schema, keys, product['product_id'], None, batch_rows
    )
    summaries = [
        iter(_allocation_summary(table, product, owner, label, batch_rows, residual=is_residual))
        for table, label, is_residual in [
            (county, 'county-summary', False),
            (metro, 'metro-summary', False),
            (residuals, 'residual-summary', True),
        ]
    ]
    heads = [next(stream, None) for stream in summaries]
    k = product['pool_divisor']
    for key, native_vector in _allocation_summary(
        native.cells, observed, owner, 'native-summary', batch_rows
    ):
        values = []
        for i, head in enumerate(heads):
            io.require(head is None or head[0] >= key, 'unexpected allocation summary key')
            if head is not None and head[0] == key:
                values.append(head[1])
                heads[i] = next(summaries[i], None)
            else:
                values.append([0.0] * 81)
        for rep in range(81):
            county_mass = values[0][rep] / k
            comparisons = [('native_to_county', float(native_vector[rep]) / k, county_mass)]
            if product['view'] == 'allocated_msa':
                comparisons.append(
                    (
                        'county_to_msa_and_residuals',
                        county_mass,
                        math.fsum((values[1][rep] / k, values[2][rep])),
                    )
                )
            for order, (check, expected, actual) in enumerate(comparisons):
                writer.append(
                    dict(
                        product_id=product['product_id'],
                        code_unit_type=key[0],
                        code_unit=key[1],
                        component_year=key[2],
                        replicate=rep,
                        check=check,
                        expected_mass=expected,
                        actual_mass=actual,
                        status='pass' if close_allocated_or_se(actual, expected) else 'fail',
                        _check_order=order,
                    )
                )
    io.require(all(head is None for head in heads), 'unexpected allocation summary tail')
    return writer.finish()


def _allocation_disk(
    native,
    product,
    factors,
    counties,
    workspace,
    *,
    residual_schema,
    diagnostic_schema,
    batch_rows=4096,
):
    '''Persist independently ordered aggregate allocation facts with bounded Python carries.'''
    _check_product(product, batch_rows)
    io.require(
        product['family'] == 'area_mix'
        and product['view'] in ('allocated_county', 'allocated_msa'),
        'allocation requires declared allocated area_mix product',
    )
    match = (
        'family',
        'dimension',
        'base_universe',
        'evidence_policy',
        'years',
        'sample_set',
        'pool_divisor',
    )
    observed = next(
        p for p in products() if p['view'] == 'observed' and all(p[n] == product[n] for n in match)
    )
    io.require(
        native.cells.product_id == observed['product_id'] and native.coverage is None,
        'allocation native counterpart differs',
    )
    # Validate all authenticated public relations before filtering zero contributions.
    for relations in factors.values():
        seen = set()
        for county, factor in relations:
            io.require(county not in seen, 'duplicate county factor')
            seen.add(county)
            io.require(
                type(factor) in (int, float) and math.isfinite(factor) and 0 <= factor <= 1,
                'invalid county factor',
            )
            io.require(county in counties, 'unknown allocation county')
    for membership in counties.values():
        kind, identity = membership['cbsa_type'], membership['cbsa_id']
        io.require(
            kind in (None, 'metropolitan', 'micropolitan')
            and (
                (kind is None and identity is None)
                or (kind is not None and isinstance(identity, str) and bool(identity))
            ),
            'invalid typed county membership',
        )
    with _owned(workspace, 'independent-allocation-' + product['product_id']) as owner:
        contribution_schema = pl.Schema(
            {
                **dict.fromkeys(
                    [
                        'source_a_type',
                        'origin',
                        'code_type',
                        'code',
                        'county_id',
                        'cbsa_type',
                        'cbsa_id',
                        'residual_kind',
                    ],
                    pl.String,
                ),
                'component': pl.Int64,
                'weights': pl.List(pl.Float64),
                'n': pl.UInt64,
                'fraction': pl.Float64,
                'flags': pl.List(pl.String),
            }
        )
        contributions = _FactWriter(
            owner,
            'contributions',
            contribution_schema,
            (),
            product['product_id'],
            None,
            batch_rows,
        )
        for key, value in _fact_rows(native.cells, observed, batch_rows, pair=True):
            a_type, origin, code_type, code, component = key
            io.require(a_type == 'work_migration_puma', 'wrong native workplace type')
            relations = factors.get(origin, [])
            io.require(
                relations and close_share(sum(f for _, f in relations), 1.0),
                'workplace factors do not cover native origin',
            )
            for county, factor in sorted(relations):
                if factor == 0:
                    continue
                membership = counties[county]
                flags = value['flags'] | set(ALLOCATION_FLAGS)
                if factor < 1:
                    flags.add('flag_fractional_split')
                contributions.append(
                    dict(
                        source_a_type=a_type,
                        origin=origin,
                        code_type=code_type,
                        code=code,
                        component=component,
                        county_id=county,
                        cbsa_type=membership['cbsa_type'],
                        cbsa_id=membership['cbsa_id'],
                        residual_kind=(
                            'micropolitan'
                            if membership['cbsa_type'] == 'micropolitan'
                            else 'no_cbsa'
                        ),
                        weights=[float(w) * factor for w in value['weights']],
                        n=value['n'],
                        fraction=value['n'] * factor,
                        flags=sorted(flags),
                    )
                )
        contributions = contributions.finish()
        checked_denominators = _denominator_facts(
            native.cells, observed, owner, label='native-denominator-check', batch_rows=batch_rows
        )
        supplied = iter(_fact_rows(native.denominators, observed, batch_rows, pair=False))
        for expected in _fact_rows(checked_denominators, observed, batch_rows, pair=False):
            io.require(next(supplied, None) == expected, 'native denominator closure differs')
        io.require(next(supplied, None) is None, 'native denominator closure has extra tail')
        keys = [*PAIR, 'component_year']

        def fact_writer(label):
            return _FactWriter(
                owner,
                label,
                _fact_schema(PAIR, 'float64'),
                keys,
                product['product_id'],
                'float64',
                batch_rows,
            )

        county_writer = fact_writer('county')
        county_group = ['county_id', 'code_type', 'code', 'component']
        county_rows = _allocation_ordered(
            contributions,
            owner,
            'county-view',
            [*county_group, 'source_a_type', 'origin'],
            batch_rows,
        )
        for key, value in _allocation_reduce(county_rows, county_group):
            county_writer.append(_fact_row(keys, ('county', *key), value, 'float64'))
        county_cells = county_writer.finish()
        residual_keys = list(residual_schema)[:13]
        residual_writer = _FactWriter(
            owner,
            'residuals',
            residual_schema,
            residual_keys,
            product['product_id'],
            None,
            batch_rows,
        )
        metro_writer = fact_writer('metro')
        if product['view'] == 'allocated_msa':
            metro_group = ['cbsa_id', 'code_type', 'code', 'component']
            metadata = _allocation_reduce(
                (
                    r
                    for r in _allocation_ordered(
                        contributions,
                        owner,
                        'metadata-view',
                        [*metro_group, 'origin', 'county_id'],
                        batch_rows,
                    )
                    if r['cbsa_type'] == 'metropolitan'
                ),
                metro_group,
                metadata=True,
            )
            rollup_schema = pl.Schema({**contribution_schema})
            rollups = _FactWriter(
                owner, 'county-rollups', rollup_schema, (), product['product_id'], None, batch_rows
            )
            for key, value in _fact_rows(county_cells, product, batch_rows, pair=True):
                membership = counties[key[1]]
                if membership['cbsa_type'] == 'metropolitan':
                    rollups.append(
                        dict(
                            source_a_type='county',
                            origin=key[1],
                            code_type=key[2],
                            code=key[3],
                            component=key[4],
                            county_id=key[1],
                            cbsa_type='metropolitan',
                            cbsa_id=membership['cbsa_id'],
                            residual_kind=None,
                            **{n: value[n] for n in ('weights', 'n', 'fraction')},
                            flags=sorted(value['flags']),
                        )
                    )
            mass = iter(
                _allocation_reduce(
                    _allocation_ordered(
                        rollups.finish(),
                        owner,
                        'rollup-view',
                        [*metro_group, 'county_id'],
                        batch_rows,
                    ),
                    metro_group,
                )
            )
            for key, value in metadata:
                mass_row = next(mass, None)
                io.require(
                    mass_row is not None and mass_row[0] == key,
                    'metropolitan metadata/mass keys differ',
                )
                value['weights'] = mass_row[1]['weights']
                metro_writer.append(_fact_row(keys, ('cbsa', *key), value, 'float64'))
            io.require(next(mass, None) is None, 'unexpected metropolitan mass tail')
            residual_group = ['origin', 'code_type', 'code', 'component', 'residual_kind']
            residual_rows = (
                r
                for r in _allocation_ordered(
                    contributions,
                    owner,
                    'residual-view',
                    [*residual_group, 'county_id'],
                    batch_rows,
                )
                if r['cbsa_type'] != 'metropolitan'
            )
            for key, value in _allocation_reduce(residual_rows, residual_group, residual=True):
                for rep in range(81):
                    residual_writer.append(
                        dict(
                            source='acs',
                            family='area_mix',
                            workplace_unit_type='work_migration_puma',
                            workplace_unit=key[0],
                            code_unit_type=key[1],
                            code_unit=key[2],
                            component_year=key[3],
                            residual_type=key[4],
                            replicate=rep,
                            sample_set=product['sample_set'],
                            vintage=product['vintage'],
                            product_id=product['product_id'],
                            universe=product['base_universe'] + ':' + product['evidence_policy'],
                            pool_divisor=product['pool_divisor'],
                            weighted_mass=value['weights'][rep] / product['pool_divisor'],
                            n_input_support=value['n'],
                            fractional_support_mass=value['fraction'],
                            flags=sorted(value['flags']),
                        )
                    )
        metro_cells = metro_writer.finish()
        residuals = residual_writer.finish(sort=True)
        cells = county_cells if product['view'] == 'allocated_county' else metro_cells
        denominators = _denominator_facts(cells, product, owner, batch_rows=batch_rows)
        diagnostic_schema = pl.Schema(diagnostic_schema)
        io.require(
            native.diagnostics.product_id == observed['product_id']
            and native.diagnostics.schema == diagnostic_schema
            and native.diagnostics.weight_kind is None,
            'native diagnostic identity/schema differs',
        )
        diagnostics_writer = _FactWriter(
            owner,
            'diagnostics',
            diagnostic_schema,
            DIAG_KEY,
            product['product_id'],
            None,
            batch_rows,
        )
        for path in native.diagnostics.paths:
            io.require(
                io.safe(path).is_relative_to(io.safe(native.diagnostics.owner))
                and pl.read_parquet_schema(path) == diagnostic_schema,
                'invalid native diagnostic path/schema',
            )
        for row in _rows(pl.scan_parquet(native.diagnostics.paths, glob=False), batch_rows):
            io.require(
                all(
                    row[n] == observed[n]
                    for n in (
                        'family',
                        'dimension',
                        'base_universe',
                        'evidence_policy',
                        'view',
                        'product_id',
                    )
                ),
                'native diagnostic row identity differs',
            )
            diagnostics_writer.append(
                row
                | {
                    n: product[n]
                    for n in (
                        'family',
                        'dimension',
                        'base_universe',
                        'evidence_policy',
                        'view',
                        'product_id',
                    )
                }
            )
        diagnostics = diagnostics_writer.finish(sort=True)
        measurements = _allocation_measurements(
            native, county_cells, metro_cells, residuals, observed, product, owner, batch_rows
        )
        return _AllocationFacts(owner, cells, denominators, residuals, diagnostics, measurements)
