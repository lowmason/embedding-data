import copy
import json
from pathlib import Path

import polars as pl
import pytest

from embedding_data import ita_establishment_expected as expected

FINDING = Path(__file__).parents[1] / 'specs/findings/v1-v3-ita-verification.md'


def finding_table(heading: str) -> list[dict[str, str]]:
    '''Rows of the first table after the line equal to heading, before the next `## `.'''
    lines = FINDING.read_text(encoding='utf-8').splitlines()
    start = [index for index, line in enumerate(lines) if line == heading]
    assert len(start) == 1, f'heading {heading!r} must appear once'
    header, rows = None, []
    for line in lines[start[0] + 1:]:
        if line.startswith('## '):
            break
        if not line.startswith('|'):
            if header is not None:
                break
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if header is None:
            header = cells
        elif not all(set(cell) <= set('-: ') for cell in cells):
            rows.append(dict(zip(header, cells, strict=True)))
    return rows


def v1_frame(value: expected.Expectations) -> pl.DataFrame:
    return pl.DataFrame(
        [dict(year_filing_for=year, **cells) for year, cells in value.v1.items()],
        schema={'year_filing_for': pl.Int64, **{c: pl.Int64 for c in expected.V1_COLUMNS}})


def v2_frame(value: expected.Expectations) -> pl.DataFrame:
    return pl.DataFrame(
        [dict(base_year=base, later_year=later, **cells)
         for (base, later), cells in value.v2.items()],
        schema={'base_year': pl.Int64, 'later_year': pl.Int64,
                **{c: pl.Int64 for c in expected.V2_COLUMNS}})


def check(value=expected.ADOPTED, *, source_records=None, v1=None, v2=None):
    return expected.check_reproduction(
        value,
        source_records=value.source_records if source_records is None else source_records,
        v1=v1_frame(value) if v1 is None else v1,
        v2=v2_frame(value) if v2 is None else v2)


def other_expectations(basis='fixture_basis') -> expected.Expectations:
    v1 = copy.deepcopy(expected.V1)
    v1[2016]['n_rows'] += 7
    v2 = copy.deepcopy(expected.V2)
    v2[(2016, 2017)]['n_cohort_ids'] += 5
    return expected.Expectations(basis, expected.SOURCE_RECORDS + 7, v1, v2)


def test_v1_constants_match_adopted_table():
    rows = finding_table('## V1')
    assert [int(row['year_filing_for']) for row in rows] == list(expected.YEARS)
    for row in rows:
        assert expected.V1[int(row['year_filing_for'])] == {
            column: int(row[column]) for column in expected.V1_COLUMNS}


def test_v2_constants_match_adopted_table():
    rows = finding_table('## V2')
    assert [(int(r['base_year']), int(r['later_year'])) for r in rows] == list(expected.YEAR_PAIRS)
    for row in rows:
        key = (int(row['base_year']), int(row['later_year']))
        assert expected.V2[key] == {column: int(row[column]) for column in expected.V2_COLUMNS}


def test_source_total_is_sum_of_v1_rows():
    assert sum(year['n_rows'] for year in expected.V1.values()) == expected.SOURCE_RECORDS
    assert expected.SOURCE_RECORDS == 3_206_055


def test_constant_shapes():
    assert expected.YEARS == tuple(range(2016, 2026))
    assert tuple(expected.V1) == expected.YEARS
    assert tuple(expected.V2) == expected.YEAR_PAIRS
    assert len(expected.YEAR_PAIRS) == 10
    assert all(tuple(cells) == expected.V1_COLUMNS for cells in expected.V1.values())
    assert all(tuple(cells) == expected.V2_COLUMNS for cells in expected.V2.values())
    assert all(type(number) is int
               for cells in [*expected.V1.values(), *expected.V2.values()]
               for number in cells.values())


def test_adopted_source_identity():
    assert expected.ADOPTED_SOURCE == {
        'path': 'derived/osha/ita_300a_summary.parquet',
        'sha256': '6335cda7adb40a41c4a11d57d22048999449ac8d078a2ec0291f0198cd9136a8',
        'size': 139930636}
    assert expected.ADOPTED_BASIS == 'adopted_v1_v3_finding'
    assert expected.ADOPTED == expected.Expectations(
        expected.ADOPTED_BASIS, expected.SOURCE_RECORDS, expected.V1, expected.V2)


def adopted_source() -> dict:
    return {key: expected.ADOPTED_SOURCE[key] for key in ('sha256', 'size')}


def test_adopted_source_returns_adopted():
    assert expected.expectations_for(adopted_source()) is expected.ADOPTED


def test_adopted_source_refuses_explicit_expectations():
    with pytest.raises(ValueError):
        expected.expectations_for(adopted_source(), other_expectations())
    with pytest.raises(ValueError):
        expected.expectations_for(adopted_source(), expected.ADOPTED)


def test_other_source_requires_explicit_expectations():
    explicit = other_expectations()
    other = {'sha256': 'f' * 64, 'size': 12}
    with pytest.raises(ValueError):
        expected.expectations_for(other)
    assert expected.expectations_for(other, explicit) is explicit


def test_other_source_refuses_adopted_basis():
    other = {'sha256': 'f' * 64, 'size': 12}
    with pytest.raises(ValueError):
        expected.expectations_for(other, other_expectations(expected.ADOPTED_BASIS))
    with pytest.raises(ValueError):
        expected.expectations_for(other, expected.ADOPTED)


def test_adopted_source_needs_both_hash_and_size():
    explicit = other_expectations()
    same_hash = {'sha256': expected.ADOPTED_SOURCE['sha256'], 'size': 12}
    same_size = {'sha256': 'f' * 64, 'size': expected.ADOPTED_SOURCE['size']}
    for source in (same_hash, same_size):
        with pytest.raises(ValueError):
            expected.expectations_for(source)
        assert expected.expectations_for(source, explicit) is explicit


def test_expectations_round_trip_json():
    assert expected.Expectations.from_json(expected.ADOPTED.to_json()) == expected.ADOPTED
    other = other_expectations()
    assert expected.Expectations.from_json(json.loads(json.dumps(other.to_json()))) == other


def test_expectations_json_keys():
    value = json.loads(json.dumps(expected.ADOPTED.to_json()))
    assert value['basis'] == 'adopted_v1_v3_finding'
    assert value['source_records'] == 3_206_055
    assert list(value['v1']) == [str(year) for year in expected.YEARS]
    assert list(value['v2']) == ['2016-2017', '2017-2018', '2018-2019', '2019-2020',
                                 '2020-2021', '2021-2022', '2022-2023', '2023-2024',
                                 '2023-2025', '2024-2025']
    assert value['v1']['2021']['n_ein_padded'] == 12440
    assert value['v2']['2023-2025']['n_same_raw_ein_address'] == 133795


def test_to_json_is_its_own_json_form():
    value = expected.ADOPTED.to_json()
    assert all(isinstance(key, str) for key in value['v1'])
    assert all(isinstance(key, str) for key in value['v2'])
    assert json.loads(json.dumps(value)) == value


def test_expectations_are_frozen():
    with pytest.raises(AttributeError):
        expected.ADOPTED.basis = 'changed'


def test_check_reproduction():
    assert check() == {
        'basis': 'adopted_v1_v3_finding', 'source_records': 'equal',
        'v1': 'equal', 'v2': 'equal'}
    v2 = v2_frame(expected.ADOPTED).with_columns(
        pl.when(pl.col('base_year').eq(2023) & pl.col('later_year').eq(2025))
        .then(pl.col('n_reappeared').add(1)).otherwise(pl.col('n_reappeared'))
        .alias('n_reappeared'))
    with pytest.raises(ValueError, match='V2 reproduction differs'):
        check(v2=v2)
    with pytest.raises(ValueError, match='source record count differs'):
        check(source_records=expected.SOURCE_RECORDS - 1)


def test_check_reproduction_v1_cell_differs():
    v1 = v1_frame(expected.ADOPTED).with_columns(
        pl.when(pl.col('year_filing_for').eq(2021))
        .then(pl.col('n_ein_padded').add(1)).otherwise(pl.col('n_ein_padded'))
        .alias('n_ein_padded'))
    with pytest.raises(ValueError) as caught:
        check(v1=v1)
    assert str(caught.value) == 'V1 reproduction differs'


def test_check_reproduction_every_cell_is_compared():
    for column in expected.V1_COLUMNS:
        v1 = v1_frame(expected.ADOPTED).with_columns(pl.col(column).sub(1))
        with pytest.raises(ValueError, match='V1 reproduction differs'):
            check(v1=v1)
    for column in expected.V2_COLUMNS:
        v2 = v2_frame(expected.ADOPTED).with_columns(pl.col(column).add(1))
        with pytest.raises(ValueError, match='V2 reproduction differs'):
            check(v2=v2)


def test_check_reproduction_source_count_is_checked_first():
    v1 = v1_frame(expected.ADOPTED).with_columns(pl.col('n_rows').add(1))
    with pytest.raises(ValueError) as caught:
        check(source_records=expected.SOURCE_RECORDS + 1, v1=v1)
    assert str(caught.value) == 'source record count differs'


def test_check_reproduction_v1_is_checked_before_v2():
    v1 = v1_frame(expected.ADOPTED).with_columns(pl.col('n_empty').add(1))
    v2 = v2_frame(expected.ADOPTED).with_columns(pl.col('n_cohort_ids').add(1))
    with pytest.raises(ValueError) as caught:
        check(v1=v1, v2=v2)
    assert str(caught.value) == 'V1 reproduction differs'


def test_check_reproduction_row_order_does_not_matter():
    check(v1=v1_frame(expected.ADOPTED).reverse(), v2=v2_frame(expected.ADOPTED).reverse())


def test_check_reproduction_missing_and_extra_rows():
    v1 = v1_frame(expected.ADOPTED)
    v2 = v2_frame(expected.ADOPTED)
    with pytest.raises(ValueError, match='V1 reproduction differs'):
        check(v1=v1.filter(pl.col('year_filing_for').ne(2025)))
    with pytest.raises(ValueError, match='V1 reproduction differs'):
        check(v1=v1.filter(pl.col('year_filing_for').ne(2025)).vstack(
            v1.filter(pl.col('year_filing_for').eq(2024))))
    with pytest.raises(ValueError, match='V1 reproduction differs'):
        check(v1=v1.vstack(v1.head(1)))
    with pytest.raises(ValueError, match='V2 reproduction differs'):
        check(v2=v2.filter(pl.col('later_year').ne(2025) | pl.col('base_year').ne(2023)))
    with pytest.raises(ValueError, match='V2 reproduction differs'):
        check(v2=v2.vstack(v2.head(1)))


def test_check_reproduction_extra_year_row_differs():
    v1 = v1_frame(expected.ADOPTED)
    extra = v1.filter(pl.col('year_filing_for').eq(2025)).with_columns(
        pl.lit(2026, dtype=pl.Int64).alias('year_filing_for'))
    with pytest.raises(ValueError) as caught:
        check(v1=v1.vstack(extra))
    assert str(caught.value) == 'V1 reproduction differs'


def test_check_reproduction_extra_pair_row_differs():
    v2 = v2_frame(expected.ADOPTED)
    extra = v2.filter(pl.col('base_year').eq(2024) & pl.col('later_year').eq(2025)).with_columns(
        pl.lit(2025, dtype=pl.Int64).alias('base_year'),
        pl.lit(2026, dtype=pl.Int64).alias('later_year'))
    with pytest.raises(ValueError) as caught:
        check(v2=v2.vstack(extra))
    assert str(caught.value) == 'V2 reproduction differs'


def test_check_reproduction_pair_keys_are_not_swapped():
    v2 = copy.deepcopy(expected.V2)
    v2[(2023, 2025)], v2[(2024, 2025)] = v2[(2024, 2025)], v2[(2023, 2025)]
    swapped = expected.Expectations('swapped', expected.SOURCE_RECORDS, expected.V1, v2)
    with pytest.raises(ValueError, match='V2 reproduction differs'):
        check(v2=v2_frame(swapped))


def test_check_reproduction_compares_with_the_given_expectations():
    other = other_expectations()
    assert check(other) == {
        'basis': 'fixture_basis', 'source_records': 'equal', 'v1': 'equal', 'v2': 'equal'}
    with pytest.raises(ValueError, match='source record count differs'):
        expected.check_reproduction(
            other, source_records=expected.SOURCE_RECORDS,
            v1=v1_frame(other), v2=v2_frame(other))
    with pytest.raises(ValueError, match='V1 reproduction differs'):
        expected.check_reproduction(
            other, source_records=other.source_records,
            v1=v1_frame(expected.ADOPTED), v2=v2_frame(other))
    with pytest.raises(ValueError, match='V2 reproduction differs'):
        expected.check_reproduction(
            other, source_records=other.source_records,
            v1=v1_frame(other), v2=v2_frame(expected.ADOPTED))


def test_check_reproduction_ignores_extra_columns():
    v1 = v1_frame(expected.ADOPTED).with_columns(extra=pl.lit('x'))
    v2 = v2_frame(expected.ADOPTED).with_columns(share=pl.lit(0.5))
    assert check(v1=v1, v2=v2)['v1'] == 'equal'
