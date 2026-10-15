import polars as pl
import pytest
from geography_fixtures import (
    COUNTY_ROWS,
    FIXTURE_SCOPE,
    MEMBER_ROWS,
    STATE_ROWS,
    sheet,
    source_frames,
    write_counties,
)

from embedding_data import geography_parsers as gp

def test_original_layouts_and_string_codes(tmp_path):
    sources = source_frames(tmp_path)
    assert sources['states']['state_fips'].to_list() == ['01', '09', '51']
    assert sources['regions']['region_title'].to_list() == ['Northeast Region', 'South Region']
    assert sources['excluded_states']['state_fips'].to_list() == ['72']
    assert sources['counties']['county_geoid'].to_list() == [
        '01001', '09110', '51001', '51510', '72001']
    assert sources['members'].filter(pl.col('county_geoid').eq('51510')).item(
        0, 'cbsa_role') == 'outlying'
    assert set(sources['members']['cbsa_type']) == {'metropolitan', 'micropolitan'}


@pytest.mark.parametrize(('row', 'column', 'value'), [
    (3, 0, '1000'), (3, 3, ''), (3, 4, 'Unknown Statistical Area'),
    (3, 9, '1'), (3, 10, '01'), (3, 11, 'Unknown'),
    (6, 9, '7'), (6, 4, 'Unknown Statistical Area'),
])
def test_bad_membership_is_not_filtered_or_a_footer(row, column, value):
    rows = [list(r) for r in MEMBER_ROWS]
    rows[row][column] = value
    with pytest.raises(ValueError):
        gp.parse_members(sheet(rows))


def test_state_header_is_unique_and_content_located():
    assert gp.parse_states(sheet(STATE_ROWS), scope=FIXTURE_SCOPE)['states'].height == 3
    for rows in (STATE_ROWS + [STATE_ROWS[4]], STATE_ROWS[:4] + STATE_ROWS[5:],
                 STATE_ROWS + [STATE_ROWS[7]]):
        with pytest.raises(ValueError):
            gp.parse_states(sheet(rows), scope=FIXTURE_SCOPE)


def test_missing_state_title_and_contradictory_division_fail():
    for row, column, value in [(7, 3, ''), (7, 0, '3'), (7, 2, '9')]:
        rows = [list(r) for r in STATE_ROWS]
        rows[row][column] = value
        with pytest.raises(ValueError):
            gp.parse_states(sheet(rows), scope=FIXTURE_SCOPE)


def test_duplicate_and_contradictory_membership_fail():
    changed = list(MEMBER_ROWS[3])
    changed[0] = '20000'
    for last in (MEMBER_ROWS[3], changed):
        with pytest.raises(ValueError):
            gp.parse_members(sheet(MEMBER_ROWS + [last]))


@pytest.mark.parametrize(('column', 'value'), [
    pytest.param(3, 'Contradictory metropolitan title', id='title'),
    pytest.param(4, 'Micropolitan Statistical Area', id='type'),
])
def test_cbsa_description_contradiction_with_distinct_counties_fails(column, value):
    rows = [list(row) for row in MEMBER_ROWS]
    rows[4][column] = value
    with pytest.raises(ValueError, match='CBSA title/type contradicts'):
        gp.parse_members(sheet(rows))


def test_only_known_footers_with_empty_other_cells_are_accepted():
    footer = [gp.CBSA_FOOTERS[0]] + [None] * 11
    assert gp.parse_members(sheet(MEMBER_ROWS + [footer])).height == 4
    footer[9] = '01'
    with pytest.raises(ValueError):
        gp.parse_members(sheet(MEMBER_ROWS + [footer]))
    with pytest.raises(ValueError):
        gp.parse_members(sheet(MEMBER_ROWS + [['Note: unknown'] + [None] * 11]))


def test_county_unicode_duplicate_and_abbreviation_constraints(tmp_path):
    file = tmp_path / 'counties.zip'
    write_counties(file, [['AL', '01001', '  Doña Ana fixture  ']])
    assert gp.parse_counties(file).item(0, 'county_title') == 'Doña Ana fixture'
    for rows in (COUNTY_ROWS + [COUNTY_ROWS[0]], [['AL', '1001', 'Bad']],
                 [['AL', '01001', 'A'], ['XX', '01003', 'B']],
                 [['AL', '01001', 'A'], ['AL', '09110', 'B']], [['AL', '01001', '']]):
        write_counties(file, rows)
        with pytest.raises(ValueError):
            gp.parse_counties(file)


def test_county_archive_member_and_header_are_strict(tmp_path):
    from zipfile import ZipFile

    file = tmp_path / 'counties.zip'
    for name, body in [('unexpected.txt', 'USPS|GEOID|NAME\nAL|01001|A\n'),
                       ('2025_Gaz_counties_national.txt', 'USPS|NAME\nAL|A\n')]:
        with ZipFile(file, 'w') as archive:
            archive.writestr(name, body)
        with pytest.raises(ValueError):
            gp.parse_counties(file)
