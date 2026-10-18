'''Strict complete population originals for the separate Stage 8 geographic frames.'''

import csv
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import fastexcel
import polars as pl

from embedding_data import geography_parsers as gp
from embedding_data import manifest, target_io
from embedding_data.acs_mapping_inputs import SelectedInputs
from embedding_data.acs_mapping_io import safe_path
from embedding_data.acs_mapping_references import (
    GEOCORR_COUNTY_TOTALS_HEADERS,
    GEOCORR_INTERSECTIONS_HEADERS,
    GEOCORR_PUMA_TOTALS_HEADERS,
    WORKBOOK_LAYOUTS,
    ReferenceSnapshot,
)

S = pl.String
POPULATION_DTYPE = pl.Int64
F = pl.Float64
LS = pl.List(S)
REFERENCE_FIELDS = {'reference_ids': LS, 'reference_locators': LS}
PUMA_KEY = ['state_fips', 'puma_code']
COUNTY_KEY = ['state_fips', 'county_geoid']
GROUP_KEY = ['group_state_fips', 'group_code']
INTERSECTION_SCHEMA = dict(
    state_fips=S,
    puma_code=S,
    county_geoid=S,
    intersection_population=POPULATION_DTYPE,
    published_area_factor=F,
    published_county_factor=F,
    **REFERENCE_FIELDS,
)
PUMA_TOTAL_SCHEMA = dict(
    state_fips=S, puma_code=S, population=POPULATION_DTYPE, **REFERENCE_FIELDS
)
COUNTY_TOTAL_SCHEMA = dict(
    state_fips=S, county_geoid=S, population=POPULATION_DTYPE, **REFERENCE_FIELDS
)
PUMA_GROUP_SCHEMA = dict(
    state_fips=S,
    puma_code=S,
    group_state_code=S,
    group_state_fips=S,
    group_code=S,
    **REFERENCE_FIELDS,
)
COUNTY_GROUP_SCHEMA = dict(
    state_fips=S,
    county_geoid=S,
    group_state_code=S,
    group_state_fips=S,
    group_code=S,
    **REFERENCE_FIELDS,
)
MSA_INTERSECTION_SCHEMA = dict(
    state_fips=S,
    puma_code=S,
    msa_code=S,
    puma_population=POPULATION_DTYPE,
    msa_population=POPULATION_DTYPE,
    intersection_population=POPULATION_DTYPE,
    published_percent_puma=F,
    published_percent_msa=F,
    **REFERENCE_FIELDS,
)
# This correspondence belongs only to the composition workbooks. MIGPLAC1 uses
# a different encoding, including 110 for PR; it must never use this map.
COMPOSITION_STATES = {'0' + state: state for state in gp.SCOPE | {'72'}}
ROUNDING_BOUND = Decimal('0.00005') + Decimal('0.000000000001')


class CompositionConflict(ValueError):
    '''V8 requires official population intersections for conflicting source memberships.'''

    def __init__(self, diagnostics):
        super().__init__(
            'V8 county/group composition disagrees; official population '
            'intersections and a reviewed reference contract are required'
        )
        self.diagnostics = diagnostics


@dataclass(frozen=True)
class AreaEvidence:
    intersections: pl.DataFrame
    puma_totals: pl.DataFrame
    county_totals: pl.DataFrame
    puma_groups: pl.DataFrame
    county_groups: pl.DataFrame
    msa_intersections: pl.DataFrame
    reference_provenance: dict
    scope_states: tuple[str, ...]


def _code(value, width):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{' + str(width) + '}', value):
        raise ValueError(f'invalid {width}-digit geographic code: {value!r}')
    return value


def _state(value):
    value = _code(value, 2)
    if value not in gp.SCOPE | {'72'}:
        raise ValueError('unknown or foreign reference state')
    return value


def _population(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9]+', value):
        raise ValueError('population must be a nonnegative lexical integer')
    result = int(value)
    if result > 2**63 - 1:
        raise ValueError('population exceeds Int64')
    return result


def _published(value, maximum):
    try:
        number = Decimal(value.strip())
    except (InvalidOperation, AttributeError) as error:
        raise ValueError('invalid published population fraction') from error
    if not number.is_finite() or not Decimal(0) <= number <= maximum:
        raise ValueError('published fraction outside its scale')
    return float(number)


def _frame(rows, schema, key):
    frame = pl.DataFrame(rows, schema=schema)
    if 'group_code' in schema and frame.select(key).is_duplicated().any():
        raise CompositionConflict(
            {
                'conflicting_memberships': frame.filter(
                    frame.select(key).is_duplicated()
                ).to_dicts(),
                'v8_adopted': False,
            }
        )
    if frame.is_empty() or frame.select(key).is_duplicated().any():
        raise ValueError('empty reference or duplicate population/composition key')
    return frame.sort(key, nulls_last=False)


def _citation(reference_id, kind, locator):
    return {'reference_ids': [f'{reference_id}:{kind}'], 'reference_locators': [locator]}


def _workbook(snapshot, kind):
    workbook = fastexcel.read_excel(snapshot.files[kind].read_bytes())
    expected = WORKBOOK_LAYOUTS[kind]
    if set(workbook.sheet_names) != set(expected):
        raise ValueError(f'{kind}: exact registered worksheet identity differs')
    sheet, (width, header) = next(iter(expected.items()))
    frame = workbook.load_sheet(sheet, header_row=None, dtypes='string').to_polars()
    rows = list(frame.iter_rows())
    if frame.width != width or not rows or rows[0] != header:
        raise ValueError(f'{kind}: exact registered header differs')
    for number, row in enumerate(rows[1:], 2):
        if any(value is None for value in row):
            raise ValueError(f'{kind}: missing original field at row {number}')
        yield row, _citation(snapshot.reference_id, kind, f'{kind}:{sheet}:row:{number}')


def _geocorr(snapshot, kind):
    headers = {
        'geocorr_intersections': GEOCORR_INTERSECTIONS_HEADERS,
        'geocorr_puma_totals': GEOCORR_PUMA_TOTALS_HEADERS,
        'geocorr_county_totals': GEOCORR_COUNTY_TOTALS_HEADERS,
    }[kind]
    with snapshot.files[kind].open(encoding='utf-8-sig', newline='') as source:
        rows = list(csv.reader(source, strict=True))
    source, target = {
        'geocorr_intersections': ('puma22', 'county'),
        'geocorr_puma_totals': ('puma22', 'state'),
        'geocorr_county_totals': ('county', 'state'),
    }[kind]
    expected_labels = {
        'state': 'State code',
        'puma22': 'PUMA (2022)',
        'stab': 'State abbr.',
        'CountyName': 'County name',
        'PUMA22name': 'PUMA22 name',
        'pop20': 'Total population (2020 Census)',
        'afact': f'{source}-to-{target} allocation factor',
        'afact2': f'{target}-to-{source} allocation factor',
    }
    # The all-state generator calls the county key "County code"; its CT-only
    # preflight calls the same current key "Connecticut planning region".
    county_labels = {'County code', 'Connecticut planning region'}
    if len(rows) < 3 or rows[0] != headers or len(rows[1]) != len(headers):
        raise ValueError(f'{kind}: Geocorr header/label/body differs')
    labels = dict(zip(headers, rows[1], strict=True))
    if any(labels[key] != value for key, value in expected_labels.items() if key in labels):
        raise ValueError(f'{kind}: Geocorr descriptive labels differ')
    if 'county' in labels and labels['county'] not in county_labels:
        raise ValueError('Geocorr county frame label differs')
    for number, values in enumerate(rows[2:], 3):
        if len(values) != len(headers):
            raise ValueError('Geocorr original row width differs')
        yield (
            dict(zip(headers, values, strict=True)),
            _citation(snapshot.reference_id, kind, f'{kind}:csv:row:{number}'),
        )


def read_full_county_original(selected: SelectedInputs) -> pl.DataFrame:
    '''Authenticate and read the cited Stage 5 original, including excluded PR.'''
    provenance = selected.provenance['geography']
    relative = provenance['inputs']['references']['counties_2025']['relative']
    citations = provenance['inputs']['raw']
    candidates = [
        item
        for item in citations
        if item['path'].endswith('/' + relative) or item['path'] == relative
    ]
    if len(candidates) != 1:
        raise ValueError('selected county original citation is absent or ambiguous')
    target_io.verify_raw(selected.data_dir, candidates)
    file = target_io.relative_file(selected.data_dir / 'raw', candidates[0]['path'])
    safe_path(file)
    frame = gp.parse_counties(file)
    ct = frame.filter(pl.col('state_fips').eq('09'))
    if ct.height and set(ct['county_geoid']) != {f'091{i}0' for i in range(1, 10)}:
        raise ValueError('county original must retain all nine CT planning regions')
    return frame


def _compositions(snapshot, kind):
    puma = kind == 'puma_composition_2020'
    key = 'puma_code' if puma else 'county_geoid'
    rows = []
    for values, citation in _workbook(snapshot, kind):
        state, code, native, group = values
        state = _state(state)
        code = _code(code, 5 if puma else 3)
        if native not in COMPOSITION_STATES:
            raise ValueError('unknown native composition group-state code')
        rows.append(
            dict(
                state_fips=state,
                **{key: code if puma else state + code},
                group_state_code=native,
                group_state_fips=COMPOSITION_STATES[native],
                group_code=_code(group, 5),
                **citation,
            )
        )
    schema = PUMA_GROUP_SCHEMA if puma else COUNTY_GROUP_SCHEMA
    return _frame(rows, schema, ['state_fips', key])


def read_area_evidence(snapshot: ReferenceSnapshot, selected: SelectedInputs) -> AreaEvidence:
    '''Validate complete originals and controls before any domestic scope filtering.'''
    if manifest.sha256_file(snapshot.directory / 'receipt.json') != snapshot.receipt_sha256:
        raise ValueError('area reference receipt changed')
    if json.loads((snapshot.directory / 'receipt.json').read_text()) != snapshot.receipt:
        raise ValueError('area reference receipt object differs')
    for kind, file in snapshot.files.items():
        safe_path(file)
        if manifest.sha256_file(file) != snapshot.receipt['originals'][kind]['sha256']:
            raise ValueError('area original differs from authenticated receipt')
    full_counties = read_full_county_original(selected)
    intersections, puma_totals, county_totals = [], [], []
    for row, citation in _geocorr(snapshot, 'geocorr_intersections'):
        intersections.append(
            dict(
                state_fips=_state(row['state']),
                puma_code=_code(row['puma22'], 5),
                county_geoid=_code(row['county'], 5),
                intersection_population=_population(row['pop20']),
                published_area_factor=_published(row['afact'], 1),
                published_county_factor=_published(row['afact2'], 1),
                **citation,
            )
        )
    for kind, key, output in [
        ('geocorr_puma_totals', 'puma22', puma_totals),
        ('geocorr_county_totals', 'county', county_totals),
    ]:
        for row, citation in _geocorr(snapshot, kind):
            # Control-query factors have other denominators, but still obey [0,1].
            _published(row['afact'], 1)
            _published(row['afact2'], 1)
            output.append(
                dict(
                    state_fips=_state(row['state']),
                    **{'puma_code' if key == 'puma22' else 'county_geoid': _code(row[key], 5)},
                    population=_population(row['pop20']),
                    **citation,
                )
            )
    msa = []
    for row, citation in _workbook(snapshot, 'msa_puma_2023_2020'):
        msa.append(
            dict(
                state_fips=_state(row[2]),
                puma_code=_code(row[4], 5),
                msa_code=_code(row[0], 5),
                puma_population=_population(row[7]),
                msa_population=_population(row[6]),
                intersection_population=_population(row[8]),
                published_percent_puma=_published(row[10], 100),
                published_percent_msa=_published(row[9], 100),
                **citation,
            )
        )
    evidence = AreaEvidence(
        _frame(intersections, INTERSECTION_SCHEMA, [*PUMA_KEY, 'county_geoid']),
        _frame(puma_totals, PUMA_TOTAL_SCHEMA, PUMA_KEY),
        _frame(county_totals, COUNTY_TOTAL_SCHEMA, COUNTY_KEY),
        _compositions(snapshot, 'puma_composition_2020'),
        _compositions(snapshot, 'county_composition_2022'),
        _frame(msa, MSA_INTERSECTION_SCHEMA, [*PUMA_KEY, 'msa_code']),
        {
            'reference_id': snapshot.reference_id,
            'receipt_sha256': snapshot.receipt_sha256,
            'originals': snapshot.receipt['originals'],
            'excluded_states': sorted(set(row['state_fips'] for row in puma_totals) - gp.SCOPE),
        },
        tuple(sorted(gp.SCOPE)),
    )
    if not set(evidence.county_totals['county_geoid']).issubset(
        set(full_counties['county_geoid'])
    ):
        raise ValueError('county controls absent from current complete inventory')
    validate_area_evidence(evidence)
    return evidence


def _keys(frame, keys):
    return set(frame.select(keys).iter_rows())


def _validate_frame(frame, schema, keys):
    if list(frame.schema.items()) != list(schema.items()) or frame.is_empty():
        raise ValueError('incompatible or empty area evidence schema')
    if 'group_code' in schema and frame.select(keys).is_duplicated().any():
        raise CompositionConflict(
            {
                'conflicting_memberships': frame.filter(
                    frame.select(keys).is_duplicated()
                ).to_dicts(),
                'v8_adopted': False,
            }
        )
    if frame.select(keys).is_duplicated().any() or any(
        frame[c].null_count() for c in frame.columns
    ):
        raise ValueError('duplicate key or null area evidence field')
    if not frame.equals(frame.sort(keys, nulls_last=False)):
        raise ValueError('area evidence natural-key sort differs')
    for row in frame.iter_rows(named=True):
        _state(row['state_fips'])
        for key in ('puma_code', 'county_geoid', 'group_code', 'msa_code'):
            if key in row:
                _code(row[key], 5)
        if 'county_geoid' in row and row['county_geoid'][:2] != row['state_fips']:
            raise ValueError('county state disagrees with residence state')
        for key, dtype in schema.items():
            if dtype == LS and (
                any(x is None for x in row[key]) or row[key] != sorted(set(row[key]))
            ):
                raise ValueError('invalid reference list')
            if dtype == F:
                _published(str(row[key]), 100 if key.startswith('published_percent') else 1)
            if dtype == POPULATION_DTYPE and row[key] < 0:
                raise ValueError('negative population')
        if (
            'group_state_code' in row
            and COMPOSITION_STATES.get(row['group_state_code']) != row['group_state_fips']
        ):
            raise ValueError('native group-state correspondence differs')


def check_rounding(published, numerator, denominator, scale=1):
    if denominator <= 0:
        raise ValueError('population denominator must be positive')
    difference = abs(Decimal(str(published)) - Decimal(numerator) * scale / Decimal(denominator))
    if difference > ROUNDING_BOUND:
        raise ValueError('published factor outside four-decimal rounding bound')


def validate_area_evidence(evidence: AreaEvidence) -> None:
    '''Reconcile complete independent integer controls, including excluded states.'''
    for frame, schema, keys in [
        (evidence.intersections, INTERSECTION_SCHEMA, [*PUMA_KEY, 'county_geoid']),
        (evidence.puma_totals, PUMA_TOTAL_SCHEMA, PUMA_KEY),
        (evidence.county_totals, COUNTY_TOTAL_SCHEMA, COUNTY_KEY),
        (evidence.puma_groups, PUMA_GROUP_SCHEMA, PUMA_KEY),
        (evidence.county_groups, COUNTY_GROUP_SCHEMA, COUNTY_KEY),
        (evidence.msa_intersections, MSA_INTERSECTION_SCHEMA, [*PUMA_KEY, 'msa_code']),
    ]:
        _validate_frame(frame, schema, keys)
    if _keys(evidence.puma_totals, PUMA_KEY) != _keys(evidence.puma_groups, PUMA_KEY) or _keys(
        evidence.county_totals, COUNTY_KEY
    ) != _keys(evidence.county_groups, COUNTY_KEY):
        raise ValueError('independent control and composition keys differ')
    intersections = evidence.intersections
    for controls, keys in [(evidence.puma_totals, PUMA_KEY), (evidence.county_totals, COUNTY_KEY)]:
        totals = {
            tuple(row[k] for k in keys): row['population']
            for row in controls.iter_rows(named=True)
        }
        # Python integer sums cannot wrap around Int64 during reconciliation.
        sums = {}
        for row in intersections.iter_rows(named=True):
            key = tuple(row[k] for k in keys)
            sums[key] = sums.get(key, 0) + row['intersection_population']
        if sums != totals or any(value <= 0 for value in totals.values()):
            raise ValueError('intersection populations differ from independent controls')
    pumas = {
        tuple(row[k] for k in PUMA_KEY): row['population']
        for row in evidence.puma_totals.iter_rows(named=True)
    }
    counties = dict(evidence.county_totals.select('county_geoid', 'population').iter_rows())
    for row in intersections.iter_rows(named=True):
        pop = row['intersection_population']
        check_rounding(
            row['published_area_factor'], pop, pumas[(row['state_fips'], row['puma_code'])]
        )
        check_rounding(row['published_county_factor'], pop, counties[row['county_geoid']])
    msa_totals, msa_sums, puma_sums = {}, {}, {}
    for row in evidence.msa_intersections.iter_rows(named=True):
        key, code = (row['state_fips'], row['puma_code']), row['msa_code']
        if pumas.get(key) != row['puma_population']:
            raise ValueError('MSA PUMA population differs from independent control')
        if code in msa_totals and msa_totals[code] != row['msa_population']:
            raise ValueError('inconsistent whole MSA population')
        msa_totals[code] = row['msa_population']
        pop = row['intersection_population']
        msa_sums[code] = msa_sums.get(code, 0) + pop
        puma_sums[key] = puma_sums.get(key, 0) + pop
        check_rounding(row['published_percent_puma'], pop, row['puma_population'], 100)
        check_rounding(row['published_percent_msa'], pop, row['msa_population'], 100)
    if msa_sums != msa_totals or any(puma_sums[k] > pumas[k] for k in puma_sums):
        raise ValueError('MSA population intersections do not close exactly')
