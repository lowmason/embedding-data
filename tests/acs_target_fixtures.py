'''Small synthetic primitives shared by ACS target tests.'''

from embedding_data.target_contract import TARGET_SCHEMA

def minimal_target(**changes) -> dict:
    row = dict(
        zip(
            TARGET_SCHEMA,
            (
                'acs',
                'staffing_pattern',
                'acs_industry_category',
                'feature:acs_industry_category:industry-a',
                'acs_occupation_category',
                'feature:acs_occupation_category:occupation-a',
                'forward_share',
                0.25,
                0.0,
                'replicate',
                2,
                25.0,
                'annual-core-2023-2024',
                'acs-naics2022-soc2018',
                'civilian_employed:strict',
                ['size_gate_pending'],
            ),
            strict=True,
        )
    )
    return row | changes


def weights(point: str, overrides: dict[int, str] | None = None) -> dict[str, str]:
    overrides = overrides or {}
    return {'PERWT': point} | {f'REPWTP{r}': overrides.get(r, point) for r in range(1, 81)}


def authenticated_mapping(tmp_path, monkeypatch, prepare_acs=None) -> dict:
    '''Build a real pinned mapping from authenticated temporary upstreams.'''
    from pathlib import Path

    from acs_mapping_fixtures import build_fixture_mapping, seed_reconciliation_inputs

    fixture = seed_reconciliation_inputs(tmp_path, monkeypatch, prepare_acs=prepare_acs)
    response = build_fixture_mapping(fixture, 'mapping', monkeypatch)
    return {'data_dir': fixture.data_dir, 'request': fixture.request,
            'mapping': Path(response['directory']),
            'mapping_outputs_sha256': response['outputs_sha256']}

# Literal delivered DDI categories, kept independent of the production rules table.
FLAG_LABELS = {
    'QEMPSTAT': ['Original entry or Inapplicable (not in universe)', 'Failed edit',
                 'Illegible', 'Missing', 'Allocated', 'Illegible', 'Missing',
                 'Original entry illegible', 'Original entry missing or failed edit'],
    'QCLASSWK': ['Original entry or Inapplicable (not in universe)', 'Failed edit',
                 'Illegible', 'Missing', 'Allocated', 'Illegible', 'Missing',
                 'Original entry illegible', 'Original entry missing or failed edit'],
    'QIND': ['Original entry or Inapplicable (not in universe)', 'Failed edit',
             'Illegible', 'Missing', 'Allocated', 'Illegible', 'Missing',
             'Original entry illegible', 'Original entry missing or failed edit'],
    'QOCC': ['Entered as written', 'Failed edit', 'Illegible', 'Missing', 'Allocated',
             'Illegible', 'Missing', 'Original entry illegible',
             'Original entry missing or failed edit'],
    'QMIGRAT1': ['Not allocated', 'Failed edit', 'Illegible', 'Missing', 'Allocated',
                 'Illegible', 'Missing', 'Original entry illegible',
                 'Original entry missing or failed edit'],
    'QMIGPLC1': ['Not allocated', 'Failed edit', 'Failed edit/illegible',
                 'Failed edit/missing', 'Failed edit', 'Illegible',
                 'Failed edit/missing', 'Illegible', 'Illegible/missing or failed edit'],
    'QPWSTAT2': {0: 'Not allocated', 4: 'Allocated'},
    'QTRANWOR': {0: 'Not allocated', 4: 'Allocated'},
}


def target_delivery(profile, ddi, frame):
    '''Manifest exact delivered category spellings before genuine upstream conversion.'''
    import polars as pl
    from acs_mapping_fixtures import _reconciliation_delivery

    ddi, frame = _reconciliation_delivery(profile, ddi, frame)
    categories = {
        'EMPSTATD': {'00': 'N/A', '10': 'At work', '12': 'Has job, not working'},
        'CLASSWKRD': {'00': 'N/A', '22': 'Wage/salary, private',
                      '23': 'Wage/salary at non-profit'},
        'MIGRATE1': {'0': 'N/A', '1': 'Same house', '2': 'Moved within state',
                     '3': 'Moved between states', '4': 'Abroad one year ago', '9': 'Unknown'},
        'TRANWORK': {
            '00': 'N/A', '10': 'Auto, truck, or van', '11': 'Auto', '12': 'Driver',
            '13': 'Passenger', '14': 'Truck', '15': 'Van', '20': 'Motorcycle',
            '31': 'Bus', '32': 'Bus or trolley bus', '33': 'Bus or streetcar',
            '34': 'Light rail, streetcar, or trolley (Carro público in PR)',
            '35': 'Streetcar or trolley car (publico in Puerto Rico, 2000)',
            '36': 'Subway or elevated', '37': 'Long-distance train or commuter train',
            '38': 'Taxicab or ride-hailing services', '39': 'Ferryboat',
            '50': 'Bicycle', '60': 'Walked only', '70': 'Other', '80': 'Worked at home'},
    }
    for name, labels in FLAG_LABELS.items():
        categories[name] = {str(k): v for k, v in
                            (labels.items() if isinstance(labels, dict) else enumerate(labels))}
    ddi['variables'] = [v for v in ddi['variables'] if v['name'] not in categories]
    for name, labels in categories.items():
        ddi['variables'].append({'name': name, 'label': name, 'implied_decimals': 0,
                                'categories': [{'value': k, 'label': v}
                                               for k, v in labels.items()], 'instructions': []})
    expressions = [pl.lit(22).alias('CLASSWKRD'), pl.lit(2).alias('MIGRATE1'),
                   pl.lit(10).alias('TRANWORK')]
    for name in FLAG_LABELS:
        value, dtype = ('0', pl.String) if name == 'QMIGRAT1' else (0, pl.Int64)
        expressions.append(pl.lit(value, dtype=dtype).alias(name))
    # Preserve delivery-specific String evidence and annual missingness.
    frame = frame.with_columns(expressions).with_columns(
        pl.when(pl.lit(profile == 'core')).then(pl.lit(None, dtype=pl.String))
        .otherwise(pl.col('QMIGRAT1')).alias('QMIGRAT1'))
    return ddi, frame


def selected_target_fixture(tmp_path, monkeypatch):
    from embedding_data.acs_target_inputs import select_targets

    fixture = authenticated_mapping(tmp_path, monkeypatch, prepare_acs=target_delivery)
    return select_targets(fixture['data_dir'], 'mapping',
                          expected_mapping_outputs_sha256=fixture['mapping_outputs_sha256'],
                          request=fixture['request'])


def prepare_target_delivery(profile: str, ddi: dict, frame):
    '''Supply usable synthetic targets in raw originals before conversion.'''
    import polars as pl

    ddi, frame = target_delivery(profile, ddi, frame)
    frame = frame.with_columns(
        pl.lit(10).alias('EMPSTATD'), pl.lit('113M').alias('INDNAICS'),
        pl.lit(190).alias('IND'), pl.lit('111021').alias('OCCSOC'),
        pl.lit(20).alias('OCC'), pl.lit(1).alias('PWSTATE2'),
        pl.lit(100).alias('PWPUMA00'), pl.lit(1).alias('MIGPLAC1'),
        pl.lit(100).alias('MIGPUMA1'),
        pl.when(pl.col('YEAR').eq(2023)).then(None).otherwise(0)
        .cast(pl.Int64).alias('QMIGRAT1'),
        pl.lit('-2.5').alias('REPWTP37'))
    if profile == 'core':
        allocated = frame.filter(pl.col('YEAR').eq(2024)).head(1).with_columns(
            pl.lit(4, dtype=pl.Int64).alias('QMIGRAT1'))
        frame = pl.concat([frame, allocated])
    return ddi, frame


def membership_rules():
    '''Handwritten synthetic meanings, independently labeled for membership tests.'''
    from embedding_data.acs_target_rules import FlagRules

    statuses = {'0': 'nonallocation', '1': 'edited_failed_edit', '4': 'allocated'}
    domains = {name: {'dtype': 'String', 'values': {
        code: {'status': ('edited_failed_edit' if name == 'QMIGPLC1' and code == '4'
                          else status)} for code, status in statuses.items()}}
        for name in FLAG_LABELS}
    return FlagRules('acs-target-rules-v1', domains, {}, {
        'EMPSTATD': {'values': {'00': 'N/A', '10': 'At work',
            '12': 'Has job, not working', '14': 'Armed forces, at work',
            '15': 'Armed forces, has job, not working', '20': 'Unemployed',
            '30': 'Not in labor force', '99': 'Unknown/Illegible'}},
        'CLASSWKRD': {'values': {'00': 'N/A', '13': 'Self-employed, not incorporated',
            '14': 'Self-employed, incorporated', '22': 'Wage/salary, private',
            '23': 'Wage/salary at non-profit', '98': 'Illegible', '99': 'Unknown'}},
        'TRANWORK': {'eligible': ['10', '20', '31', '60'], 'home': ['80'],
                     'not_applicable': ['00']}})


def membership_frame(records: list[dict]):
    '''Explicit synthetic mathematical rows, never selected-input replacements.'''
    from decimal import Decimal

    import polars as pl

    from embedding_data.acs_mapping_contract import ANNOTATION_SCHEMA

    defaults = {name: ([] if isinstance(dtype, pl.List) else
                       False if dtype == pl.Boolean else None)
                for name, dtype in ANNOTATION_SCHEMA.items()}
    defaults.update(source_delivery_id='synthetic', source_parquet_sha256='a' * 64, source_row=0,
                    acs_profile='acs/core', acs_sample_id='us2024a',
                    acs_release_year=2024, acs_component_year=2024,
                    EMPSTATD=10, CLASSWKRD=22, TRANWORK=10, MIGRATE1=2,
                    INDNAICS='111110', OCCSOC='111021', PWSTATE2=1, MIGPLAC1=1)
    defaults.update({name: '0' for name in FLAG_LABELS})
    for prefix, key in [('industry', 'industry-a'), ('occupation', 'occupation-a')]:
        defaults.update({prefix + '_code_lookup_id': key,
                         prefix + '_source_token': defaults[
                             'INDNAICS' if prefix == 'industry' else 'OCCSOC'],
                         prefix + '_mapping_status': 'mapped',
                         prefix + '_canonical_scalar_node_id': 'node:' + key})
    for role in ('residence', 'workplace', 'migration'):
        defaults.update({role + '_area_status': 'applicable',
                         role + '_factor_key': ('residence' if role == 'residence'
                                                else 'work_migration') + ':01100',
                         role + '_state_fips': '01', role + '_area_code': '00100',
                         role + '_area_type': ('residence' if role == 'residence'
                                               else 'work_migration')})
    defaults.update({k: Decimal(v) for k, v in weights('100.25').items()})
    rows = [defaults | record for record in records]
    schema = {**ANNOTATION_SCHEMA, 'source_delivery_id': pl.String,
              **{name: pl.String for name in FLAG_LABELS},
              **{name: pl.Int64 for name in ('EMPSTATD', 'CLASSWKRD', 'TRANWORK',
                                             'MIGRATE1', 'PWSTATE2', 'MIGPLAC1')},
              'INDNAICS': pl.String, 'OCCSOC': pl.String,
              **{name: pl.Decimal(38, 2) for name in weights('1')}}
    return pl.DataFrame(rows, schema=schema).lazy()


def membership_units():
    import polars as pl

    from embedding_data.acs_target_contract import UNIT_SCHEMA

    rows = []
    for kind, key in [('acs_industry_category', 'industry-a'),
                      ('acs_occupation_category', 'occupation-a')]:
        row = {name: [] if isinstance(dtype, pl.List) else None
               for name, dtype in UNIT_SCHEMA.items()}
        row.update(unit_type=kind, unit=f'feature:{kind}:{key}', kind='observed_code',
                   code_code_lookup_id=key, code_mapping_status='mapped')
        rows.append(row)
    for kind in ('residence_puma', 'work_migration_puma'):
        row = {name: [] if isinstance(dtype, pl.List) else None
               for name, dtype in UNIT_SCHEMA.items()}
        row.update(unit_type=kind, unit=f'geography:2020:{kind}:0100100', kind='native_area',
                   factor_keys=[('residence' if kind == 'residence_puma'
                                 else 'work_migration') + ':01100'])
        rows.append(row)
    return pl.DataFrame(rows, schema=UNIT_SCHEMA)


def estimate_case(records: list[dict], *, years: tuple[int, ...] = (2023, 2024),
                  pool_divisor: int = 2) -> dict:
    from embedding_data.acs_target_estimation import aggregate_native, estimate

    rows = estimation_rows(records, years=years, pool_divisor=pool_divisor)
    return {name: lf.collect() for name, lf in estimate(aggregate_native(rows)).items()}


def estimation_rows(records, *, years=(2023, 2024), pool_divisor=2):
    from dataclasses import replace
    from decimal import Decimal

    import polars as pl

    from embedding_data.acs_target_contract import DIAGNOSTIC_SCHEMA, PRODUCTS
    from embedding_data.acs_target_membership import FamilyRows
    from embedding_data.acs_target_weights import WEIGHT_NAMES

    product = replace(next(p for p in PRODUCTS if p.family == 'staffing_pattern'
                           and p.view == 'observed'), years=years, pool_divisor=pool_divisor)
    values = []
    for i, record in enumerate(records):
        values.append({'source_parquet_sha256': 'synthetic', 'source_row': i,
                       'YEAR': record['year'], 'unit_a_type': 'acs_industry_category',
                       'unit_a': 'feature:acs_industry_category:' + record['a'],
                       'unit_b_type': 'acs_occupation_category',
                       'unit_b': 'feature:acs_occupation_category:' + record['b'],
                       'flags': record.get('flags', ['size_gate_pending']),
                       **{name: Decimal(record[name]) for name in WEIGHT_NAMES}})
    schema = {'source_parquet_sha256': pl.String, 'source_row': pl.UInt64,
              'YEAR': pl.Int64, 'unit_a_type': pl.String, 'unit_a': pl.String,
              'unit_b_type': pl.String, 'unit_b': pl.String, 'flags': pl.List(pl.String)}
    scale = max((max(0, -v[name].as_tuple().exponent)
                 for v in values for name in WEIGHT_NAMES if v[name].is_finite()), default=0)
    schema.update({name: pl.Decimal(38, scale) for name in WEIGHT_NAMES})
    return FamilyRows(pl.DataFrame(values, schema=schema).lazy(),
                      pl.DataFrame(schema=DIAGNOSTIC_SCHEMA).lazy(), product)
