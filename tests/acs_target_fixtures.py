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
