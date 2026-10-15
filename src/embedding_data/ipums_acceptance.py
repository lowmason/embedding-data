'''Measure aggregate acceptance evidence from parsed definitions, DDI and delivered data.

No acquisition or file writes occur here. A passing status covers these checks only:
Task 2/6 must separately prove complete raw-header and ordered CSV/Parquet parity.
'''

import re

import polars as pl

ACS_REQUESTED = frozenset((
    'PERWT REPWTP INDNAICS IND OCCSOC OCC EMPSTAT CLASSWKR GQ EDUC '
    'DEGFIELD DEGFIELD2 INCWAGE INCEARN UHRSWORK WKSWORK2 AGE SEX STATEFIP REGION PUMA '
    'COUNTYFIP MET2023 MET2023ERR PWSTATE2 PWPUMA00 PWMET23 PWMET23ERR TRANWORK TRANTIME '
    'MIGRATE1 MIGPLAC1 MIGPUMA1 MIGMET23 ').split())
MONTHLY_REQUESTED = frozenset((
    'CPSIDP CPSIDV MISH WTFINL LNKFW1MWT EARNWT IND OCC CLASSWKR '
    'EMPSAME ACTSAME LABFORCE EMPSTAT UHRSWORK1 EARNWEEK2 HOURWAGE2 PAIDHOUR ELIGORG AGE SEX '
    'EDUC STATEFIP REGION METFIPS COUNTY ').split())
ASEC_REQUESTED = frozenset((
    'CPSIDP CPSIDV ASECWT REPWTP IND OCC CLASSWKR INDLY OCCLY CLASSWLY '
    'LABFORCE EMPSTAT WKSWORK1 UHRSWORKLY INCWAGE AGE SEX EDUC STATEFIP REGION METFIPS COUNTY '
    'MIGRATE1 MIGSTA1 WHYMOVE ').split())
ACS_SAMPLES = {'core': {'us2023a', 'us2024a'}, 'vintage': {'us2022a'},
               'five_year': {'us2024c'}}
MONTH_NAMES = ('January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December')
KEY_SCHEMA = {'extract_key': pl.String, 'source': pl.String, 'set_name': pl.String}
DIMENSIONS = {'year': pl.Int64, 'month': pl.Int64, 'sample': pl.String, 'multyear': pl.Int64}
SAMPLE_SCHEMA = {**KEY_SCHEMA, **DIMENSIONS, 'sample_id': pl.String,
                 'sample_label': pl.String, 'rows': pl.UInt64}
FLAG_SCHEMA = {
    **KEY_SCHEMA, **DIMENSIONS, 'sample_id': pl.String, 'flag': pl.String,
    'present': pl.Boolean, 'dtype': pl.String, 'value': pl.String, 'category_label': pl.String,
    'applicability': pl.String, 'rows': pl.UInt64,
}
VARIABLE_SCHEMA = {
    **KEY_SCHEMA, 'variable': pl.String, 'requested': pl.Boolean, 'required': pl.Boolean,
    'detailed': pl.Boolean, 'replicate': pl.Boolean, 'quality_flag': pl.Boolean,
    'in_ddi': pl.Boolean, 'in_parquet': pl.Boolean, 'ddi_position': pl.UInt32,
    'parquet_position': pl.UInt32, 'dtype': pl.String, 'implied_decimals': pl.Int64,
    'label': pl.String,
}


def _profile(source, set_name):
    if source == 'acs' and set_name in ACS_SAMPLES:
        requested = set(ACS_REQUESTED)
        if set_name == 'five_year':
            requested.add('MULTYEAR')
        detailed = {'EMPSTATD', 'CLASSWKRD'}
        replicates = {f'REPWTP{number}' for number in range(1, 81)}
        automatic = {'YEAR', 'SAMPLE', 'INCWAGE_CPIU_2010'} | detailed
    elif source == 'cps' and set_name in {'monthly', 'asec'}:
        requested = set(MONTHLY_REQUESTED if set_name == 'monthly' else ASEC_REQUESTED)
        detailed = set()
        replicates = ({f'REPWTP{number}' for number in range(1, 161)}
                      if set_name == 'asec' else set())
        automatic = {'YEAR', 'MONTH'}
        if set_name == 'asec':
            automatic.add('INCWAGE_CPIU_2010')
    else:
        raise ValueError('unsupported IPUMS source/set profile')
    return requested, detailed, replicates, (requested - {'REPWTP'}) | automatic | replicates


def _definition_errors(definition, source, set_name, expected):
    errors = []
    if definition.get('collection') != ('usa' if source == 'acs' else 'cps'):
        errors.append('collection does not match profile')
    if definition.get('dataFormat') != 'csv':
        errors.append('CSV delivery not requested')
    if definition.get('dataQualityFlags') is not True:
        errors.append('extract-wide data quality flags not evidenced')
    missing = sorted(expected - set(definition['variables']))
    if missing:
        errors.append('profile variables not requested: ' + ', '.join(missing))
    selection = ('EMPSTAT', '1') if source == 'acs' else ('LABFORCE', '2')
    expected_selections = {} if set_name == 'asec' else {selection[0]: {'general': [selection[1]]}}
    actual = {name: options['caseSelections'] for name, options in definition['variables'].items()
              if options.get('caseSelections')}
    if actual != expected_selections:
        errors.append('submitted case selections do not match profile')
    if source == 'acs' and set(definition['samples']) != ACS_SAMPLES[set_name]:
        errors.append('submitted ACS samples do not match profile')
    return errors


def _inventory(definition, ddi_variables, schema, keys, required, detailed, replicates):
    metadata = {variable['name']: variable for variable in ddi_variables}
    ddi_positions = {variable['name']: index for index, variable in enumerate(ddi_variables)}
    parquet_positions = {name: index for index, name in enumerate(schema)}
    names = sorted(set(metadata) | set(schema) | set(definition['variables']) | required)
    rows = []
    for name in names:
        variable = metadata.get(name, {})
        rows.append({
            **keys, 'variable': name, 'requested': name in definition['variables'],
            'required': name in required, 'detailed': name in detailed,
            'replicate': name in replicates, 'quality_flag': name.startswith('Q'),
            'in_ddi': name in metadata, 'in_parquet': name in schema,
            'ddi_position': ddi_positions.get(name),
            'parquet_position': parquet_positions.get(name),
            'dtype': str(schema[name]) if name in schema else None,
            'implied_decimals': variable.get('implied_decimals'), 'label': variable.get('label'),
        })
    return pl.DataFrame(rows, schema=VARIABLE_SCHEMA)


def _dimensions(frame, schema):
    expressions = []
    for name, dtype in DIMENSIONS.items():
        original = name.upper()
        expression = pl.col(original) if original in schema else pl.lit(None)
        if dtype == pl.Int64:
            lexical = expression.cast(pl.String)
            expression = pl.when(lexical.str.contains(r'^[0-9]+$')).then(lexical).otherwise(None)
        expressions.append(expression.cast(dtype, strict=False).alias(name))
    return frame.with_columns(expressions)


def _sample_mapping(definition, ddi, schema, source, set_name, catalog):
    requested = set(definition['samples'])
    errors = []
    mapping = {}
    if source == 'acs':
        variable = next((v for v in ddi['variables'] if v['name'] == 'SAMPLE'), {})
        numeric_sample = schema.get('SAMPLE', pl.Null).is_integer()
        for category in variable.get('categories', []):
            label = category['label'] or ''
            candidates = [sample_id for sample_id in requested if sample_id in catalog and
                          (label == catalog[sample_id] or label == sample_id)]
            if len(candidates) != 1:
                continue
            value = category['value']
            if numeric_sample and re.fullmatch(r'[0-9]+', value):
                value = str(int(value))
            if value in mapping:
                errors.append('ambiguous SAMPLE category: ' + value)
                mapping[value] = None
            else:
                mapping[value] = candidates[0]
        errors.extend(sorted(requested - set(mapping.values())))
        # Catalog descriptions establish public identity independently of DDI category labels.
        for sample_id in requested:
            label = catalog.get(sample_id, '')
            year = sample_id[2:6]
            is_five_year = bool(re.search(r'5[ -]year', label, re.I))
            if (year not in label or 'ACS' not in label or
                    is_five_year != (set_name == 'five_year') or
                    (set_name == 'five_year' and not all(y in label for y in ('2020', '2024')))):
                errors.append(sample_id)
    else:
        for sample_id in requested:
            match = re.fullmatch(r'cps([0-9]{4})_([0-9]{2})[bs]', sample_id)
            if match is None:
                errors.append(sample_id)
                continue
            year, month = int(match[1]), int(match[2])
            if year < 2025 or not 1 <= month <= 12:
                errors.append(sample_id)
                continue
            period = f'{year:04d}-{month:02d}'
            if period in mapping:
                errors.append('duplicate requested CPS period: ' + period)
            mapping[period] = sample_id
    return mapping, sorted(errors)


def _sample_counts(base, keys, source, mapping, catalog):
    counts = base.group_by(list(DIMENSIONS)).agg(pl.len().cast(pl.UInt64).alias('rows')).collect()
    rows = []
    for group in counts.iter_rows(named=True):
        lookup = (group['sample'] if source == 'acs' else
                  f"{group['year']:04d}-{group['month']:02d}"
                  if group['year'] is not None and group['month'] is not None else None)
        sample_id = mapping.get(lookup)
        rows.append({**keys, **group, 'sample_id': sample_id,
                     'sample_label': catalog.get(sample_id)})
    return pl.DataFrame(rows, schema=SAMPLE_SCHEMA).sort(list(DIMENSIONS))


def _cps_study_evidence(mapping, notes, set_name):
    unknown, mismatch, absent = [], [], []
    for period, sample_id in sorted(mapping.items()):
        year, month = map(int, period.split('-'))
        month_label = f'{MONTH_NAMES[month - 1]} {year}'
        relevant = [note for note in notes if sample_id in note or period in note or
                    month_label.casefold() in note.casefold()]
        if not relevant:
            absent.append(sample_id)
        types = set()
        for note in relevant:
            if re.search(r'\bASEC\b', note, re.I):
                types.add('asec')
            if re.search(r'\bmonthly\b', note, re.I):
                types.add('monthly')
        if types - {set_name}:
            mismatch.append(sample_id)
        elif set_name not in types:
            unknown.append(sample_id)
    return absent, unknown, mismatch


def _sample_status(counts, definition, ddi, source, set_name, catalog, mapping):
    observed = set(counts['sample_id'].drop_nulls())
    requested = set(definition['samples'])
    unmapped = counts.filter(pl.col('sample_id').is_null())
    year_mismatch = []
    for group in counts.iter_rows(named=True):
        sample_id = group['sample_id']
        if sample_id is not None and source == 'acs' and group['year'] != int(sample_id[2:6]):
            year_mismatch.append(sample_id)
        if (source == 'acs' and set_name == 'five_year'
                and group['multyear'] not in range(2020, 2025)):
            year_mismatch.append('five_year MULTYEAR outside 2020-2024 or missing')
    notes = '\n'.join(ddi.get('study_notes', []))
    type_unknown, type_mismatch = [], []
    if source == 'acs':
        study_unknown = sorted(sample_id for sample_id in requested
                               if sample_id not in notes and
                               catalog.get(sample_id, '\0') not in notes)
    else:
        study_unknown, type_unknown, type_mismatch = _cps_study_evidence(
            mapping, ddi.get('study_notes', []), set_name)
    time_notes = ' '.join(str(note.get(field) or '') for note in ddi.get('time_notes', [])
                          if note.get('kind') == 'timePrd' for field in ('text', 'date'))
    periods = sorted({f"{row['year']:04d}-{row['month']:02d}"
                      for row in counts.iter_rows(named=True)
                      if row['year'] is not None and row['month'] is not None})
    required_times = (sorted(str(year) for year in counts['year'].drop_nulls().unique())
                      if source == 'acs' else periods)
    # A year-only CPS note cannot corroborate an individual requested month.
    covered_years = set(re.findall(r'(?<![0-9])[0-9]{4}(?![0-9])', time_notes))
    for start, end in re.findall(r'([0-9]{4})\s*[-–]\s*([0-9]{4})', time_notes):
        if 0 <= int(end) - int(start) <= 100:
            covered_years.update(str(year) for year in range(int(start), int(end) + 1))
    time_unknown = [period for period in required_times
                    if (period not in covered_years if source == 'acs'
                        else period not in time_notes)]
    calendar = set()
    if source == 'cps' and set_name == 'monthly' and mapping:
        requested_months = [int(period[:4]) * 12 + int(period[5:]) - 1 for period in mapping]
        calendar = {f'{index // 12:04d}-{index % 12 + 1:02d}'
                    for index in range(min(requested_months), max(requested_months) + 1)}
    return {
        'periods_not_requested': sorted(calendar - set(mapping)),
        'periods_absent': sorted(calendar - set(periods)),
        'ddi_sample_type_unknown': type_unknown, 'ddi_sample_type_mismatch': type_mismatch,
        'samples_missing': sorted(requested - observed),
        'samples_unmapped': unmapped.select(list(DIMENSIONS)).to_dicts(),
        'sample_year_mismatch': sorted(set(year_mismatch)),
        'sample_study_notes_unknown': study_unknown, 'ddi_time_unknown': time_unknown,
        'periods_observed': periods,
        'periods_missing': sorted(set(mapping) - set(periods)) if source == 'cps' else [],
        'periods_unexpected': sorted(set(periods) - set(mapping)) if source == 'cps' else [],
        'multyears_observed': sorted(counts['multyear'].drop_nulls().unique().to_list()),
        'multyears_missing': (sorted(set(range(2020, 2025)) -
                                    set(counts['multyear'].drop_nulls()))
                              if set_name == 'five_year' else []),
    }


def _flag_coverage(base, counts, ddi_variables, schema, keys, flags):
    metadata = {variable['name']: variable for variable in ddi_variables}
    rows = []
    for flag in sorted(flags):
        categories = {category['value']: category['label']
                      for category in metadata.get(flag, {}).get('categories', [])}
        if flag in schema:
            frequencies = (base.group_by(*DIMENSIONS, pl.col(flag).cast(pl.String).alias('value'))
                           .agg(pl.len().cast(pl.UInt64).alias('rows')).collect())
        else:
            frequencies = counts.select(*DIMENSIONS, pl.lit(None, dtype=pl.String).alias('value'),
                                        'rows')
        groups = {tuple(row[name] for name in DIMENSIONS): row['sample_id']
                  for row in counts.iter_rows(named=True)}
        for group in frequencies.iter_rows(named=True):
            rows.append({
                **keys, **group,
                'sample_id': groups[tuple(group[name] for name in DIMENSIONS)],
                'flag': flag, 'present': flag in schema,
                'dtype': str(schema[flag]) if flag in schema else None,
                'category_label': categories.get(group['value']), 'applicability': 'unknown',
            })
    return pl.DataFrame(rows, schema=FLAG_SCHEMA).sort([*DIMENSIONS, 'flag', 'value'])


def measure_acceptance(definition: dict, ddi: dict, frame: pl.LazyFrame, source: str,
                       set_name: str, sample_catalog: dict) -> dict:
    '''Return variable_inventory, sample_counts, flag_coverage DataFrames and JSON status.

    extract_key is the source/set profile identity; the caller freezes the actual delivery
    identity and raw-header parity separately. Source types are inspected, never replaced.
    Flag applicability remains unknown: a category label is evidence, not an allocation rule.
    '''
    expected, detailed, replicates, required = _profile(source, set_name)
    schema = frame.collect_schema()
    keys = {'extract_key': f'{source}/{set_name}', 'source': source, 'set_name': set_name}
    requested = set(definition['variables'])
    required |= requested - {'REPWTP'}
    ddi_names = [variable['name'] for variable in ddi['variables']]
    flags = {name for name in set(schema) | set(ddi_names) if name.startswith('Q')}
    if 'MIGRATE1' in requested:
        flags.add('QMIGRAT1')
    missing_flags = sorted(flags - set(schema))
    order_equal = ([name for name in ddi_names if name in schema] ==
                   [name for name in schema if name in ddi_names])
    base = _dimensions(frame, schema)
    mapping, catalog_mismatch = _sample_mapping(definition, ddi, schema, source, set_name,
                                                sample_catalog)
    counts = _sample_counts(base, keys, source, mapping,
                            sample_catalog if source == 'acs' else {})
    selection_name, selection_code = (('EMPSTAT', '1') if source == 'acs' else ('LABFORCE', '2'))
    invalid_selection = pl.lit(False)
    if set_name != 'asec':
        invalid_selection = (
            pl.col(selection_name).cast(pl.String).ne(selection_code).fill_null(True)
            if selection_name in schema else pl.lit(True))
    unexpected_count = (pl.len() if set_name != 'asec' and selection_name not in schema
                        else invalid_selection.sum())
    selection_counts = frame.select(
        pl.len().cast(pl.UInt64).alias('rows'),
        unexpected_count.cast(pl.UInt64).alias('selection_unexpected_rows'),
    ).collect().row(0, named=True)
    observed_replicates = {name for name in set(schema) | set(ddi_names)
                           if name.startswith('REPWTP')}
    status = {
        **keys, **selection_counts,
        'raw_header_parity': 'external_required',
        'definition_errors': _definition_errors(definition, source, set_name, expected),
        'required_missing_ddi': sorted(required - set(ddi_names)),
        'required_missing_parquet': sorted(required - set(schema)),
        'replicates_missing': sorted(replicates - (set(schema) & set(ddi_names))),
        'replicates_unexpected': sorted(observed_replicates - replicates),
        'ddi_parquet_order_equal': order_equal,
        'ddi_only_nonflags': sorted(set(ddi_names) - set(schema) - flags),
        'parquet_only_nonflags': sorted(set(schema) - set(ddi_names) - flags),
        'missing_flags': missing_flags,
        'flags_without_ddi': sorted((flags & set(schema)) - set(ddi_names)),
        'sample_catalog_mismatch': catalog_mismatch if source == 'acs' else [],
        'requested_sample_errors': catalog_mismatch if source == 'cps' else [],
        **_sample_status(counts, definition, ddi, source, set_name, sample_catalog, mapping),
        'ordered_parquet_schema': [{'name': name, 'dtype': str(dtype)}
                                   for name, dtype in schema.items()],
        'submitted_samples': sorted(definition['samples']),
        'requested_names': sorted(requested),
        'evidence_scope': 'these submitted definitions and deliveries; earlier requests unknown',
    }
    failures = ('definition_errors', 'required_missing_ddi', 'required_missing_parquet',
                'replicates_missing', 'replicates_unexpected', 'ddi_only_nonflags',
                'requested_sample_errors', 'ddi_sample_type_mismatch',
                'parquet_only_nonflags', 'sample_catalog_mismatch', 'samples_missing',
                'samples_unmapped', 'sample_year_mismatch', 'periods_missing',
                'periods_unexpected', 'multyears_missing', 'selection_unexpected_rows')
    unresolved = ('missing_flags', 'flags_without_ddi', 'sample_study_notes_unknown',
                  'ddi_time_unknown', 'ddi_sample_type_unknown')
    failed = status['rows'] == 0 or not order_equal or any(status[name] for name in failures)
    status['status'] = ('fail' if failed else 'unresolved' if
                        any(status[name] for name in unresolved) else 'pass')
    inventory = _inventory(definition, ddi['variables'], schema, keys,
                           required, detailed, replicates)
    flag_coverage = _flag_coverage(base, counts, ddi['variables'], schema, keys, flags)
    status['aggregate_schemas'] = {
        name: [{'name': column, 'dtype': str(dtype)} for column, dtype in result.schema.items()]
        for name, result in [('variable_inventory', inventory), ('sample_counts', counts),
                             ('flag_coverage', flag_coverage)]
    }
    return {'variable_inventory': inventory, 'sample_counts': counts,
            'flag_coverage': flag_coverage, 'status': status}
