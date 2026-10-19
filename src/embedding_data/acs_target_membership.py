'''Explicit native pair membership and separate disjoint/overlapping diagnostics.'''

from dataclasses import dataclass

import polars as pl

from embedding_data.acs_target_contract import DIAGNOSTIC_SCHEMA, Product
from embedding_data.acs_target_rules import SUBSTANTIVE_FIELDS, FlagRules, required_flags

UNUSABLE_SUBSTANTIVE_CODES = {
    'EMPSTATD': {'00', '99'},
    'CLASSWKRD': {'00', '98', '99'},
}

FAMILY_INPUTS = {
    ('staffing_pattern', 'industry_occupation'): (('industry', 'occupation'), ()),
    ('area_mix', 'industry'): (('industry',), ('workplace',)),
    ('area_mix', 'occupation'): (('occupation',), ('workplace',)),
    ('commuting_flow', 'flow'): ((), ('residence', 'workplace')),
    ('migration_flow', 'flow'): ((), ('residence', 'migration')),
}


@dataclass(frozen=True)
class FamilyRows:
    members: pl.LazyFrame
    diagnostics: pl.LazyFrame
    product: Product


def _in_codes(name, codes, schema):
    # DDI lexical 00 denotes numeric 0 only in an actually numeric delivered column.
    values = list(codes) if schema[name] == pl.String else [int(v) for v in codes]
    return pl.col(name).is_in(values).fill_null(False)


def _attach_units(frame, units):
    for prefix, kind in [('industry', 'acs_industry_category'),
                         ('occupation', 'acs_occupation_category')]:
        lookup = units.filter(pl.col('unit_type').eq(kind)).select(
            pl.col('code_code_lookup_id').alias(prefix + '_code_lookup_id'),
            pl.col('unit_type').alias(prefix + '_unit_type'),
            pl.col('unit').alias(prefix + '_unit'))
        frame = frame.join(lookup.lazy(), on=prefix + '_code_lookup_id', how='left',
                           validate='m:1', maintain_order='left')
    areas = units.filter(pl.col('kind').eq('native_area')).select(
        'unit_type', 'unit', 'factor_keys').explode('factor_keys').drop_nulls('factor_keys')
    for role in ('residence', 'workplace', 'migration'):
        lookup = areas.select(pl.col('factor_keys').alias(role + '_factor_key'),
                              pl.col('unit_type').alias(role + '_unit_type'),
                              pl.col('unit').alias(role + '_unit'))
        frame = frame.join(lookup.lazy(), on=role + '_factor_key', how='left',
                           validate='m:1', maintain_order='left')
    return frame


def _evidence(frame, rules, schema, usable):
    checks = [pl.col(name).cast(pl.String).is_not_null().and_(
        pl.col(name).cast(pl.String).is_in(list(
            rules.domains.get(name, {}).get('values', {}))).not_()).any().alias(name)
        for name in SUBSTANTIVE_FIELDS if name in schema]
    if checks and any(frame.select(checks).collect().row(0)):
        raise ValueError('unexpected nonmissing flag domain value')
    applicable_categories = {name: _in_codes(name, [
        code for code in rules.universe_categories[name]['values'] if code not in excluded],
        schema)
        for name, excluded in UNUSABLE_SUBSTANTIVE_CODES.items()}
    domestic_states = {role: pl.col(role + '_state_fips').is_not_null().and_(
        pl.col(role + '_area_status').is_in(['foreign', 'territory']).not_()).and_(
            pl.col(field).is_not_null()) for role, field in
        [('workplace', 'PWSTATE2'), ('migration', 'MIGPLAC1')]}
    expressions = []
    for name in SUBSTANTIVE_FIELDS:
        domain = rules.domains.get(name, {})
        raw = pl.col(name).cast(pl.String) if name in schema else pl.lit(None, dtype=pl.String)
        applicable = {
            'QEMPSTAT': applicable_categories['EMPSTATD'],
            'QCLASSWK': applicable_categories['CLASSWKRD'],
            'QIND': usable['industry'], 'QOCC': usable['occupation'],
            'QMIGRAT1': _in_codes('MIGRATE1', ('1', '2', '3', '4'), schema),
            'QMIGPLC1': domestic_states['migration'],
            'QPWSTAT2': domestic_states['workplace'],
            'QTRANWOR': _in_codes('TRANWORK',
                [*rules.universe_categories['TRANWORK']['eligible'], '80'], schema),
        }[name].fill_null(False)
        statuses = {value: evidence['status']
                    for value, evidence in domain.get('values', {}).items()}
        status = pl.when(applicable).then(raw.replace_strict(
            statuses, default='unavailable', return_dtype=pl.String)).otherwise(
                pl.lit('not_applicable'))
        expressions.append(status.alias('_evidence_' + name))
    return frame.with_columns(expressions)


def _diagnostic(frame, product, *, partition, reason, variable=None, rules=None):
    schema = frame.collect_schema()
    reference = (rules.references.get(variable, {}) if rules is not None else {})
    citation = reference.get('citation', {})
    frame = frame.with_columns(
        pl.lit('acs').alias('source'), pl.col('acs_profile').alias('profile'),
        pl.col('source_delivery_id').alias('delivery_id'),
        pl.col('acs_sample_id').alias('sample_id'),
        pl.col('acs_component_year').alias('component_year'),
        pl.lit(product.family).alias('family'), pl.lit(product.dimension).alias('dimension'),
        pl.lit(product.base_universe).alias('base_universe'),
        pl.lit(product.evidence_policy).alias('evidence_policy'),
        pl.lit(product.view).alias('view'), pl.lit(product.product_id).alias('product_id'),
        pl.lit(partition).alias('partition_kind'),
        pl.lit(variable, dtype=pl.String).alias('variable'),
        pl.lit(str(schema[variable]) if variable in schema else None,
               dtype=pl.String).alias('raw_dtype'),
        (pl.col(variable).cast(pl.String) if variable in schema else
         pl.lit(None, dtype=pl.String)).alias('raw_value'),
        (pl.col('_evidence_' + variable) if variable else
         pl.lit(None, dtype=pl.String)).alias('evidence_status'),
        reason.alias('reason'))
    keys = list(DIAGNOSTIC_SCHEMA)[:list(DIAGNOSTIC_SCHEMA).index('n_unweighted')]
    return frame.group_by(keys).agg(
        pl.len().cast(pl.UInt64).alias('n_unweighted'),
        pl.col('PERWT').sum().alias('_weight')).with_columns(
            pl.col('_weight').cast(pl.String).str.replace(r'(\.\d*?)0+$', '${1}')
                .str.replace(r'\.$', '').replace('-0', '0').alias('weight_sum_exact'),
            pl.col('_weight').cast(pl.Float64).truediv(product.pool_divisor).alias('weighted_mass'),
            pl.lit([citation['path']] if citation else [], dtype=pl.List(pl.String))
            .alias('reference_ids'),
            pl.lit([reference['locator']] if 'locator' in reference else [],
                   dtype=pl.List(pl.String)).alias('reference_locators')).select(
                       pl.col(name).cast(dtype) for name, dtype in DIAGNOSTIC_SCHEMA.items())


def family_rows(frame: pl.LazyFrame, product: Product, rules: FlagRules,
                units: pl.DataFrame) -> FamilyRows:
    '''Apply the approved first-exclusion order without imposing unused family roles.'''
    code_dimensions, roles = FAMILY_INPUTS[(product.family, product.dimension)]
    schema = frame.collect_schema()
    frame = _attach_units(frame, units)
    usable = {prefix: pl.col(prefix + '_unit').is_not_null().and_(
        pl.col(prefix + '_code_lookup_id').is_not_null()).and_(
        pl.col(field).is_not_null()).and_(pl.col(field).str.strip_chars().ne('')).fill_null(False)
        for prefix, field in [('industry', 'INDNAICS'), ('occupation', 'OCCSOC')]}
    frame = _evidence(frame, rules, schema, usable)
    required = required_flags(product.family, product.base_universe)
    in_period = pl.col('acs_component_year').is_in(product.years).and_(
        pl.col('acs_sample_id').eq(pl.concat_str(
            pl.lit('us'), pl.col('acs_component_year').cast(pl.String), pl.lit('a'))))
    exclusions = [(in_period.not_(), 'outside_declared_period'),
                  (_in_codes('EMPSTATD', ('10', '12'), schema).not_(),
                   'outside_civilian_universe')]
    if product.base_universe == 'private_wage_salary':
        exclusions.append((_in_codes('CLASSWKRD', ('22', '23'), schema).not_(),
                           'outside_private_universe'))
    for dimension in code_dimensions:
        exclusions.append((usable[dimension].not_(), 'unusable_' + dimension + '_category'))
    if product.family == 'migration_flow':
        exclusions.extend([(_in_codes('MIGRATE1', (code,), schema), reason)
                           for code, reason in [('1', 'stayer'), ('9', 'unknown_movement'),
                                                ('4', 'moved_from_abroad'),
                                                ('0', 'movement_not_applicable')]])
        exclusions.append((_in_codes('MIGRATE1', ('2', '3'), schema).not_(),
                           'unknown_movement'))
    if product.family in {'area_mix', 'commuting_flow'}:
        exclusions.extend([
            (_in_codes('EMPSTATD', ('10',), schema).not_(), 'not_at_work'),
            (_in_codes('TRANWORK', ('80',), schema), 'worked_at_home'),
            (_in_codes('TRANWORK', rules.universe_categories['TRANWORK']['eligible'], schema)
             .not_(), 'unusable_transport')])
    reason = pl.lit('eligible')
    if product.evidence_policy == 'strict':
        for name in reversed(required):
            status = pl.col('_evidence_' + name)
            reason = pl.when(status.ne('nonallocation')).then(
                pl.concat_str(pl.lit('required_' + name + '_'), status)).otherwise(reason)
    for role in reversed(roles):
        status = pl.col(role + '_area_status')
        reason = pl.when(status.ne('applicable').fill_null(True)).then(
            pl.concat_str(pl.lit(role + '_'), status.fill_null('documented_unavailable'))
        ).when(pl.col(role + '_unit').is_null()).then(
            pl.lit(role + '_documented_unavailable')).otherwise(reason)
    for condition, label in reversed(exclusions):
        reason = pl.when(condition.fill_null(True)).then(pl.lit(label)).otherwise(reason)
    frame = frame.with_columns(reason.alias('_first_exclusion'))
    diagnostics = [_diagnostic(frame, product, partition='first_exclusion',
                               reason=pl.col('_first_exclusion'))]
    for name in SUBSTANTIVE_FIELDS:
        diagnostics.append(_diagnostic(frame, product, partition='evidence', variable=name,
                                        reason=pl.col('_evidence_' + name), rules=rules))
    for name, dtype in schema.items():
        if dtype == pl.Boolean:
            diagnostics.append(_diagnostic(frame.filter(pl.col(name).fill_null(False)),
                product, partition='limitation', reason=pl.lit(name)))
    for role in roles:
        diagnostics.append(_diagnostic(frame, product, partition='limitation',
            reason=pl.lit(role + '_puma_specific_evidence_unavailable')))
    special = frame.filter(pl.col('OCCSOC').eq('559830'))
    diagnostics.append(_diagnostic(special, product, partition='limitation', reason=
        pl.when(_in_codes('EMPSTATD', ('10', '12'), schema)).then(
            pl.lit('559830_civilian_special')).otherwise(pl.lit('559830_outside_civilian'))))
    pair = {'staffing_pattern': ('industry', 'occupation'),
            'area_mix': ('workplace', product.dimension),
            'commuting_flow': ('residence', 'workplace'),
            'migration_flow': ('migration', 'residence')}[product.family]
    provenance = [pl.when(pl.col(name).fill_null(False)).then(pl.lit(name)).otherwise(None)
                  for name, dtype in schema.items() if dtype == pl.Boolean]
    evidence_flags = [pl.when(pl.col('_evidence_' + name).is_in(
        ['allocated', 'edited_failed_edit', 'unavailable'])).then(pl.concat_str(
            pl.lit('source_evidence_' + name + '_'), pl.col('_evidence_' + name)))
        .otherwise(None) for name in required]
    limitations = [pl.lit(role + '_puma_specific_evidence_unavailable') for role in roles]
    flags = pl.concat_list(pl.lit('size_gate_pending'), *provenance, *evidence_flags,
                           *limitations)
    members = frame.filter(pl.col('_first_exclusion').eq('eligible')).with_columns(
        *[pl.col(prefix + '_unit' + suffix).alias('unit_' + side + suffix)
          for side, prefix in zip(('a', 'b'), pair, strict=True) for suffix in ('_type', '')],
        flags.list.drop_nulls().list.unique().list.sort().alias('flags'))
    return FamilyRows(members, pl.concat(diagnostics).sort(
        list(DIAGNOSTIC_SCHEMA)[:list(DIAGNOSTIC_SCHEMA).index('n_unweighted')],
        nulls_last=False), product)
