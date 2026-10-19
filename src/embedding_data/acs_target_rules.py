'''Validate delivered ACS evidence against explicit variable-specific DDI meanings.'''

from copy import deepcopy
from dataclasses import dataclass

import polars as pl

from embedding_data.acs_mapping_contract import SourceInput
from embedding_data.acs_target_contract import RULE_VERSION

# These are delivered code/label pairs, not a nonzero allocation heuristic.
FLAG_VALUES = {
    'QEMPSTAT': {
        '0': ('Original entry or Inapplicable (not in universe)', 'nonallocation'),
        '1': ('Failed edit', 'edited_failed_edit'),
        '2': ('Illegible', 'unavailable'),
        '3': ('Missing', 'unavailable'),
        '4': ('Allocated', 'allocated'),
        '5': ('Illegible', 'unavailable'),
        '6': ('Missing', 'unavailable'),
        '7': ('Original entry illegible', 'unavailable'),
        '8': ('Original entry missing or failed edit', 'edited_failed_edit'),
    },
    'QCLASSWK': {
        '0': ('Original entry or Inapplicable (not in universe)', 'nonallocation'),
        '1': ('Failed edit', 'edited_failed_edit'),
        '2': ('Illegible', 'unavailable'),
        '3': ('Missing', 'unavailable'),
        '4': ('Allocated', 'allocated'),
        '5': ('Illegible', 'unavailable'),
        '6': ('Missing', 'unavailable'),
        '7': ('Original entry illegible', 'unavailable'),
        '8': ('Original entry missing or failed edit', 'edited_failed_edit'),
    },
    'QIND': {
        '0': ('Original entry or Inapplicable (not in universe)', 'nonallocation'),
        '1': ('Failed edit', 'edited_failed_edit'),
        '2': ('Illegible', 'unavailable'),
        '3': ('Missing', 'unavailable'),
        '4': ('Allocated', 'allocated'),
        '5': ('Illegible', 'unavailable'),
        '6': ('Missing', 'unavailable'),
        '7': ('Original entry illegible', 'unavailable'),
        '8': ('Original entry missing or failed edit', 'edited_failed_edit'),
    },
    'QOCC': {
        '0': ('Entered as written', 'nonallocation'),
        '1': ('Failed edit', 'edited_failed_edit'),
        '2': ('Illegible', 'unavailable'),
        '3': ('Missing', 'unavailable'),
        '4': ('Allocated', 'allocated'),
        '5': ('Illegible', 'unavailable'),
        '6': ('Missing', 'unavailable'),
        '7': ('Original entry illegible', 'unavailable'),
        '8': ('Original entry missing or failed edit', 'edited_failed_edit'),
    },
    'QMIGRAT1': {
        '0': ('Not allocated', 'nonallocation'),
        '1': ('Failed edit', 'edited_failed_edit'),
        '2': ('Illegible', 'unavailable'),
        '3': ('Missing', 'unavailable'),
        '4': ('Allocated', 'allocated'),
        '5': ('Illegible', 'unavailable'),
        '6': ('Missing', 'unavailable'),
        '7': ('Original entry illegible', 'unavailable'),
        '8': ('Original entry missing or failed edit', 'edited_failed_edit'),
    },
    'QMIGPLC1': {
        '0': ('Not allocated', 'nonallocation'),
        '1': ('Failed edit', 'edited_failed_edit'),
        '2': ('Failed edit/illegible', 'edited_failed_edit'),
        '3': ('Failed edit/missing', 'edited_failed_edit'),
        '4': ('Failed edit', 'edited_failed_edit'),
        '5': ('Illegible', 'unavailable'),
        '6': ('Failed edit/missing', 'edited_failed_edit'),
        '7': ('Illegible', 'unavailable'),
        '8': ('Illegible/missing or failed edit', 'edited_failed_edit'),
    },
    'QPWSTAT2': {'0': ('Not allocated', 'nonallocation'), '4': ('Allocated', 'allocated')},
    'QTRANWOR': {'0': ('Not allocated', 'nonallocation'), '4': ('Allocated', 'allocated')},
}
SUBSTANTIVE_FIELDS = {
    'QEMPSTAT': 'EMPSTATD',
    'QCLASSWK': 'CLASSWKRD',
    'QIND': 'INDNAICS',
    'QOCC': 'OCCSOC',
    'QMIGRAT1': 'MIGRATE1',
    'QMIGPLC1': 'MIGPLAC1',
    'QPWSTAT2': 'PWSTATE2',
    'QTRANWOR': 'TRANWORK',
}
UNIVERSE_CODES = {
    'EMPSTATD': {'00': 'N/A', '10': 'At work', '12': 'Has job, not working'},
    'CLASSWKRD': {'00': 'N/A', '22': 'Wage/salary, private', '23': 'Wage/salary at non-profit'},
    'MIGRATE1': {
        '0': 'N/A',
        '1': 'Same house',
        '2': 'Moved within state',
        '3': 'Moved between states',
        '4': 'Abroad one year ago',
        '9': 'Unknown',
    },
    'TRANWORK': {
        '00': 'N/A',
        '10': 'Auto, truck, or van',
        '11': 'Auto',
        '12': 'Driver',
        '13': 'Passenger',
        '14': 'Truck',
        '15': 'Van',
        '20': 'Motorcycle',
        '31': 'Bus',
        '32': 'Bus or trolley bus',
        '33': 'Bus or streetcar',
        '34': 'Light rail, streetcar, or trolley (Carro público in PR)',
        '35': 'Streetcar or trolley car (publico in Puerto Rico, 2000)',
        '36': 'Subway or elevated',
        '37': 'Long-distance train or commuter train',
        '38': 'Taxicab or ride-hailing services',
        '39': 'Ferryboat',
        '50': 'Bicycle',
        '60': 'Walked only',
        '70': 'Other',
        '80': 'Worked at home',
    },
}


@dataclass(frozen=True)
class FlagRules:
    version: str
    domains: dict
    references: dict
    universe_categories: dict


def required_flags(family: str, base_universe: str) -> tuple[str, ...]:
    extras = {
        'staffing_pattern': (),
        'area_mix': ('QPWSTAT2', 'QTRANWOR'),
        'commuting_flow': ('QPWSTAT2', 'QTRANWOR'),
        'migration_flow': ('QMIGRAT1', 'QMIGPLC1'),
    }
    if family not in extras or base_universe not in {'civilian_employed', 'private_wage_salary'}:
        raise ValueError('unknown family or base universe')
    private = ('QCLASSWK',) if base_universe == 'private_wage_salary' else ()
    return ('QEMPSTAT', 'QIND', 'QOCC') + private + extras[family]


def classify_flag(value: str | None, variable: str, applicable: bool, rules: FlagRules) -> str:
    domain = rules.domains.get(variable)
    if value is not None and (domain is None or value not in domain['values']):
        raise ValueError('unexpected nonmissing flag domain value')
    if not applicable:
        return 'not_applicable'
    if value is None or domain is None:
        return 'unavailable'
    return domain['values'][value]['status']


def _categories(variable: dict) -> dict:
    categories = variable['categories']
    values = {record['value']: record['label'] for record in categories}
    if len(values) != len(categories) or any(value is None for value in values):
        raise ValueError('duplicate or missing DDI category value')
    return values


def read_rules(source: SourceInput) -> FlagRules:
    '''Retain delivered metadata and reject unknown domains before eligibility filtering.'''
    variables = {v['name']: v for v in source.ddi['variables']}
    if len(variables) != len(source.ddi['variables']):
        raise ValueError('duplicate DDI variable')
    schema = pl.read_parquet_schema(source.parquet)
    ddi_citations = [c for c in source.raw_citations if c['path'].endswith('.xml')]
    if len(ddi_citations) != 1:
        raise ValueError('expected one selected DDI citation')
    references, domains, universe = {}, {}, {}
    for name, expected in FLAG_VALUES.items():
        if name not in variables:
            if name in schema:
                raise ValueError('flag column missing DDI domain: ' + name)
            continue
        metadata = variables[name]
        if _categories(metadata) != {code: pair[0] for code, pair in expected.items()}:
            raise ValueError('unexpected DDI flag categories or labels: ' + name)
        dtype = schema.get(name)
        if dtype is not None and dtype not in {pl.Int64, pl.String}:
            raise ValueError('unsupported original flag dtype: ' + name)
        locator = f'dataDscr/var[@name="{name}"]'
        references[name] = {'citation': deepcopy(ddi_citations[0]), 'locator': locator}
        domains[name] = {
            'dtype': None if dtype is None else str(dtype),
            'substantive_variable': SUBSTANTIVE_FIELDS[name],
            'applicability': 'associated substantive field must be applicable and usable',
            'reference_locator': locator,
            'metadata': deepcopy(metadata),
            'values': {
                code: {
                    'label': label,
                    'status': status,
                    'reference_locator': locator + f'/catgry[catValu="{code}"]',
                }
                for code, (label, status) in expected.items()
            },
        }
    for name, expected in UNIVERSE_CODES.items():
        if name not in variables:
            raise ValueError('missing substantive DDI variable: ' + name)
        values = _categories(variables[name])
        if any(values.get(code) != label for code, label in expected.items()):
            raise ValueError('unexpected substantive DDI categories or labels: ' + name)
        if name in {'MIGRATE1', 'TRANWORK'} and values != expected:
            raise ValueError('unexpected substantive DDI category set: ' + name)
        universe[name] = {
            'metadata': deepcopy(variables[name]),
            'values': values,
            'dtype': str(schema[name]) if name in schema else None,
            'eligible': {
                'EMPSTATD': ['10', '12'],
                'CLASSWKRD': ['22', '23'],
                'MIGRATE1': ['2', '3'],
                'TRANWORK': [v for v in expected if v not in {'00', '80'}],
            }[name],
        }
        if name == 'TRANWORK':
            universe[name].update(home=['80'], not_applicable=['00'])
        references[name] = {
            'citation': deepcopy(ddi_citations[0]),
            'locator': f'dataDscr/var[@name="{name}"]',
        }
    # Domain validation is global: an ineligible record must not hide an unknown Q value.
    scan = pl.scan_parquet(source.parquet)
    checks = [
        pl.col(name)
        .cast(pl.String)
        .is_in(list(domain['values']))
        .not_()
        .fill_null(False)
        .any()
        .alias(name)
        for name, domain in domains.items()
        if name in schema
    ]
    if checks and any(scan.select(checks).collect().row(0)):
        raise ValueError('unexpected nonmissing flag domain value')
    references['limitations'] = {'undelivered_puma_specific_flags': True}
    return FlagRules(RULE_VERSION, domains, references, universe)
