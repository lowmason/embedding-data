'''Strict original-layout parsing and complete-reference validation.'''

import pytest

pytest_plugins = ['acs_mapping_fixtures']


def test_genuine_layouts_and_native_group_states(population_case):
    from embedding_data.acs_area_references import read_area_evidence

    evidence = read_area_evidence(population_case.snapshot, population_case.selected)
    assert evidence.puma_groups['group_state_code'].to_list() == ['001', '001', '009', '072']
    assert evidence.puma_groups['group_state_fips'].to_list() == ['01', '01', '09', '72']
    assert evidence.intersections['intersection_population'].to_list() == [60, 40, 300, 200, 10]
    assert evidence.reference_provenance['excluded_states'] == ['72']


def test_full_county_original_retains_pr_and_all_nine_ct_regions(population_case):
    from embedding_data.acs_area_references import read_full_county_original

    frame = read_full_county_original(population_case.selected)
    assert '72001' in frame['county_geoid']
    assert set(frame.filter(frame['state_fips'].eq('09'))['county_geoid']) == {
        f'091{i}0' for i in range(1, 10)
    }


@pytest.mark.parametrize(
    'kind,column,value',
    [
        ('geocorr_intersections', 'pop20', '-1'),
        ('geocorr_intersections', 'pop20', '1.1'),
        ('geocorr_intersections', 'pop20', ''),
        ('geocorr_intersections', 'afact', '0.600051'),
        ('geocorr_intersections', 'afact2', '0.999949'),
        ('geocorr_intersections', 'state', '99'),
        ('geocorr_intersections', 'county', '09001'),
        ('geocorr_puma_totals', 'pop20', '0'),
    ],
)
def test_invalid_original_fails_even_with_honest_repin(population_case, kind, column, value):
    from embedding_data.acs_area_references import read_area_evidence

    snapshot = population_case.mutate_csv(kind, column, value)
    with pytest.raises(ValueError):
        read_area_evidence(snapshot, population_case.selected)


@pytest.mark.parametrize('column,value', [('afact', '0.60005'), ('afact2', '0.99995')])
def test_published_fraction_rounding_boundary_is_inclusive(population_case, column, value):
    from embedding_data.acs_area_references import read_area_evidence

    snapshot = population_case.mutate_csv('geocorr_intersections', column, value)
    read_area_evidence(snapshot, population_case.selected)


@pytest.mark.parametrize('field', ['published_percent_puma', 'published_percent_msa'])
@pytest.mark.parametrize('delta,valid', [(0.00005, True), (0.000052, False)])
def test_percentage_rounding_boundary_uses_0_to_100_scale(population_case, field, delta, valid):
    from dataclasses import replace

    import polars as pl

    from embedding_data.acs_area_references import validate_area_evidence

    msa = population_case.evidence.msa_intersections
    if field == 'published_percent_puma':
        value = 60 + delta
    else:
        value = 60 / 260 * 100 + delta
    altered = msa.with_columns(
        pl.when(pl.col('state_fips').eq('01'))
        .then(pl.lit(value))
        .otherwise(pl.col(field))
        .alias(field)
    )
    evidence = replace(population_case.evidence, msa_intersections=altered)
    if valid:
        validate_area_evidence(evidence)
    else:
        with pytest.raises(ValueError, match='rounding'):
            validate_area_evidence(evidence)


def test_pr_population_is_validated_before_exclusion(population_case):
    from dataclasses import replace

    import polars as pl

    from embedding_data.acs_area_references import validate_area_evidence

    frame = population_case.evidence.intersections.with_columns(
        pl.when(pl.col('state_fips').eq('72'))
        .then(pl.lit(9))
        .otherwise(pl.col('intersection_population'))
        .alias('intersection_population')
    )
    with pytest.raises(ValueError, match='population'):
        validate_area_evidence(replace(population_case.evidence, intersections=frame))


def test_original_hash_change_is_refused(population_case):
    from embedding_data.acs_area_references import read_area_evidence

    population_case.snapshot.files['geocorr_intersections'].write_text('changed')
    with pytest.raises(ValueError, match='original'):
        read_area_evidence(population_case.snapshot, population_case.selected)


@pytest.mark.parametrize('column', ['state', 'pop20'])
def test_unexpected_csv_headers_and_labels_fail(population_case, column):
    import csv

    from embedding_data.acs_area_references import read_area_evidence

    file = population_case.snapshot.files['geocorr_intersections']
    with file.open(newline='') as source:
        rows = list(csv.reader(source))
    if column == 'state':
        rows[0][0] = 'unexpected'
    else:
        rows[1][rows[0].index(column)] = 'Different population'
    with file.open('w', newline='') as output:
        csv.writer(output).writerows(rows)
    snapshot = population_case.repin()
    with pytest.raises(ValueError, match='header|label'):
        read_area_evidence(snapshot, population_case.selected)


def test_native_foreign_group_state_is_not_truncated(population_case):
    from dataclasses import replace

    import polars as pl

    from embedding_data.acs_area_references import validate_area_evidence

    groups = population_case.evidence.puma_groups.with_columns(
        pl.lit('101').alias('group_state_code')
    )
    with pytest.raises(ValueError, match='group-state'):
        validate_area_evidence(replace(population_case.evidence, puma_groups=groups))


@pytest.mark.parametrize(
    'problem', ['header', 'sheet', 'negative', 'decimal', 'percent_low', 'percent_high']
)
def test_unexpected_workbook_layout_or_population_fails(population_case, problem):
    import fastexcel
    from acs_mapping_fixtures import write_public_layout

    from embedding_data.acs_area_references import read_area_evidence

    kind = 'msa_puma_2023_2020'
    file = population_case.snapshot.files[kind]
    workbook = fastexcel.read_excel(file.read_bytes())
    name = workbook.sheet_names[0]
    rows = [
        list(row)
        for row in workbook.load_sheet(0, header_row=None, dtypes='string').to_polars().iter_rows()
    ]
    if problem == 'sheet':
        name = 'Wrong sheet'
    elif problem == 'header':
        rows[0][6] = rows[0][6].strip()
    else:
        column, value = {
            'negative': (8, '-1'),
            'decimal': (8, '60.0'),
            'percent_low': (10, '-0.1'),
            'percent_high': (10, '100.0001'),
        }[problem]
        rows[1][column] = value
    write_public_layout(
        file, {'sheets': {name: {'rows': {str(i): row for i, row in enumerate(rows, 1)}}}}
    )
    with pytest.raises(ValueError):
        read_area_evidence(population_case.repin(), population_case.selected)


@pytest.mark.parametrize('value', [None, -1])
def test_null_and_negative_typed_population_fail(population_case, value):
    from dataclasses import replace

    import polars as pl

    from embedding_data.acs_area_references import validate_area_evidence

    frame = population_case.evidence.intersections.with_columns(
        pl.lit(value).cast(pl.Int64).alias('intersection_population')
    )
    with pytest.raises(ValueError):
        validate_area_evidence(replace(population_case.evidence, intersections=frame))


def test_duplicate_intersection_fails(population_case):
    from dataclasses import replace

    import polars as pl

    from embedding_data.acs_area_references import validate_area_evidence

    original = population_case.evidence.intersections
    frame = pl.concat([original, original.head(1)]).sort('state_fips', 'puma_code', 'county_geoid')
    with pytest.raises(ValueError, match='duplicate'):
        validate_area_evidence(replace(population_case.evidence, intersections=frame))


def test_ct_public_original_layout_fixture_contains_nine_regions():
    import base64
    import csv
    import hashlib
    import json
    from pathlib import Path

    directory = Path(__file__).parent / 'fixtures/acs_mapping/geography'
    file = directory / 'ct-county-control.csv'
    provenance = json.loads((directory / 'ct-inventory.json').read_text())
    original = base64.b64decode(provenance['body_base64'])
    assert hashlib.sha256(original).hexdigest() == provenance['sha256']
    assert hashlib.sha256(file.read_bytes()).hexdigest() == provenance['fixture_sha256']
    assert file.read_bytes() == b'\n'.join(
        row.rstrip(b' \t') for row in original.splitlines()
    ) + b'\n'
    with file.open(newline='') as source:
        rows = list(csv.DictReader(source))
    assert rows[0]['county'] == 'Connecticut planning region'
    assert {row['county'] for row in rows[1:]} == {f'091{i}0' for i in range(1, 10)}


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1.0, 1.1])
def test_nonfinite_or_out_of_range_typed_factors_fail(population_case, value):
    from dataclasses import replace

    import polars as pl

    from embedding_data.acs_area_references import validate_area_evidence

    frame = population_case.evidence.intersections.with_columns(
        pl.lit(value).alias('published_area_factor')
    )
    with pytest.raises(ValueError):
        validate_area_evidence(replace(population_case.evidence, intersections=frame))


def test_null_reference_list_element_fails(population_case):
    from dataclasses import replace

    import polars as pl

    from embedding_data.acs_area_references import validate_area_evidence

    frame = population_case.evidence.intersections.with_columns(
        pl.lit(['valid', None], dtype=pl.List(pl.String)).alias('reference_ids')
    )
    with pytest.raises(ValueError, match='reference list'):
        validate_area_evidence(replace(population_case.evidence, intersections=frame))


def test_actual_nationwide_geocorr_reader_preserves_single_byte_names(tmp_path):
    from types import SimpleNamespace

    from acs_mapping_fixtures import genuine_geocorr_bytes

    from embedding_data.acs_area_references import _geocorr
    body = genuine_geocorr_bytes()
    file = tmp_path / 'geocorr_intersections.csv'
    file.write_bytes(body)
    snapshot = SimpleNamespace(
        reference_id='actual_encoding', files={'geocorr_intersections': file}
    )
    rows = list(_geocorr(snapshot, 'geocorr_intersections'))
    assert len(rows) == 4690
    assert len({r['state'] for r, _ in rows}) == 52
    assert any('ó' in r['PUMA22name'] or 'ó' in r['CountyName'] for r, _ in rows)
    assert rows[-1][1]['reference_locators'] == ['geocorr_intersections:csv:row:4692']
    assert file.read_bytes() == body
