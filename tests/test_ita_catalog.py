import re
from datetime import date
from pathlib import Path

import pytest

from embedding_data import ita_catalog
from embedding_data import osha_benchmark_download as osha

PAGE_HTML = (Path(__file__).parent / 'fixtures/osha/itadata.html').read_text()
FILES = 'https://www.osha.gov/sites/default/files/'
LARGE_FILES = 'https://www.osha.gov/sites/default/largefiles/'
CURRENT_NAME = 'ITA_300A_Summary_Data_2025_through_08-31-2026.csv'


def test_the_recorded_page_lists_each_summary_year_once():
    catalog = ita_catalog.parse_catalog(PAGE_HTML)

    assert [release.year for release in catalog.releases] == [2025, *range(2024, 2015, -1)]
    assert catalog.releases[0].url == LARGE_FILES + CURRENT_NAME
    assert catalog.releases[-1].url == FILES + 'ITA%20Data%20CY%202016.zip'
    assert not any('Case_Detail' in release.url for release in catalog.releases)


def test_both_summary_dictionaries_are_found_and_case_detail_ones_ignored():
    catalog = ita_catalog.parse_catalog(PAGE_HTML)

    assert catalog.dictionaries == (
        FILES + 'summary_data_dictionary.pdf',
        FILES + 'ITA_Data_Dictionary.pdf',
    )


def test_file_name_decodes_percent_escapes():
    assert ita_catalog.file_name(FILES + 'ITA%20Data%20CY%202016.zip') == 'ITA Data CY 2016.zip'


@pytest.mark.parametrize(
    'url',
    [
        FILES + '..%2F..%2Fx.zip',
        FILES + '..%5Cx.zip',
        FILES + '%2E%2E',
        FILES + '%2E',
        'https://www.osha.gov',
    ],
    ids=['slash', 'backslash', 'parent', 'current', 'empty'],
)
def test_a_file_name_that_could_leave_its_directory_is_refused(url):
    with pytest.raises(ValueError, match=re.escape(url)):
        ita_catalog.file_name(url)


@pytest.mark.parametrize(
    ('name', 'expected'),
    [
        (CURRENT_NAME, date(2026, 8, 31)),
        ('ITA_300A_Summary_Data_2023_through_12-31-2024.zip', date(2024, 12, 31)),
        ('ITA 300A Summary Data 2023 through 12-31-2024_v2.csv', date(2024, 12, 31)),
        ('ITA Data CY 2016.zip', None),
        ('ITA-data-cy2021.zip', None),
    ],
)
def test_through_date_reads_the_date_a_file_name_carries(name, expected):
    assert ita_catalog.through_date(name) == expected


@pytest.mark.parametrize(
    'name',
    [
        'ITA_300A_Summary_Data_2025_through_02-30-2026.csv',
        'ITA_300A_Summary_Data_2025_through_13-45-2026.csv',
    ],
)
def test_a_through_date_that_does_not_exist_is_refused_naming_the_file(name):
    with pytest.raises(ValueError, match=re.escape(name)):
        ita_catalog.through_date(name)


def test_a_page_without_summary_links_is_refused():
    with pytest.raises(ValueError, match='layout may have changed'):
        ita_catalog.parse_catalog('<html><body><a href="/x.pdf">Report</a></body></html>')


def test_the_recorded_catalog_is_complete():
    ita_catalog.check_complete(ita_catalog.parse_catalog(PAGE_HTML))


def test_a_skipped_year_is_refused():
    page = '\n'.join(line for line in PAGE_HTML.splitlines() if '2019 Summary Data' not in line)

    with pytest.raises(ValueError, match='no summary file listed for 2019'):
        ita_catalog.check_complete(ita_catalog.parse_catalog(page))


def test_a_current_year_without_a_through_date_is_refused():
    page = PAGE_HTML.replace(CURRENT_NAME, 'ITA_300A_Summary_Data_2025.csv')

    with pytest.raises(ValueError, match='the 2025 summary file names no through-date'):
        ita_catalog.check_complete(ita_catalog.parse_catalog(page))


def test_a_historical_through_date_that_does_not_exist_is_refused():
    listed = 'ITA_300A_Summary_Data_2023_through_12-31-2024.zip'
    malformed = listed.replace('12-31-2024', '02-30-2024')
    page = PAGE_HTML.replace(listed, malformed)

    with pytest.raises(ValueError, match=re.escape(malformed)):
        ita_catalog.check_complete(ita_catalog.parse_catalog(page))


def test_a_year_listed_twice_is_refused():
    page = PAGE_HTML + '<a href="/sites/default/files/ITA-data-cy2023.zip">2023 Summary Data</a>'

    with pytest.raises(ValueError, match='more than one summary file listed for 2023'):
        ita_catalog.check_complete(ita_catalog.parse_catalog(page))


@pytest.mark.network
def test_the_live_page_still_lists_every_summary_year():
    '''Canary for a page relayout; run deliberately with `pytest -m network`.'''
    with osha.make_client() as client:
        page = client.get(ita_catalog.PAGE_URL)
    page.raise_for_status()

    catalog = ita_catalog.parse_catalog(page.text, str(page.url))

    ita_catalog.check_complete(catalog)
    assert catalog.dictionaries
