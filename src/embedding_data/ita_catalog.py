'''Find the Form 300A summary files and data dictionaries listed on OSHA's ITA data page.

The page (https://www.osha.gov/itadata) links each year's summary file with the text
"<year> Summary Data" and each summary data dictionary with text beginning "Summary Data
Dictionary"; case-detail links are ignored. The current year's file name carries its
submission through-date (ITA_300A_Summary_Data_2025_through_08-31-2026.csv), and OSHA
renames the file as it grows, so a re-acquired release arrives under a new name.
'''

import re
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit

PAGE_URL = 'https://www.osha.gov/itadata'
FIRST_YEAR = 2016

RELEASE_TEXT = re.compile(r'^(\d{4}) Summary Data$')
DICTIONARY_TEXT = re.compile(r'^Summary Data Dictionary\b')
THROUGH_DATE = re.compile(r'through[ _](\d{2})-(\d{2})-(\d{4})')


@dataclass(frozen=True)
class SummaryRelease:
    year: int
    url: str


@dataclass(frozen=True)
class Catalog:
    releases: tuple[SummaryRelease, ...]
    dictionaries: tuple[str, ...]


class AnchorParser(HTMLParser):
    '''Collect each anchor's href and its whitespace-collapsed text.'''

    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[tuple[str, str]] = []
        self.href: str | None = None
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == 'a':
            self.href = dict(attrs).get('href')
            self.text = []

    def handle_data(self, data: str) -> None:
        if self.href is not None:
            self.text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == 'a' and self.href is not None:
            self.anchors.append((self.href, ' '.join(''.join(self.text).split())))
            self.href = None


def parse_catalog(html: str, base_url: str = PAGE_URL) -> Catalog:
    '''Every summary release and summary data dictionary the page links to, in page order.'''
    parser = AnchorParser()
    parser.feed(html)
    releases, dictionaries = [], []
    for href, text in parser.anchors:
        if match := RELEASE_TEXT.match(text):
            releases.append(SummaryRelease(int(match[1]), urljoin(base_url, href)))
        elif DICTIONARY_TEXT.match(text):
            dictionaries.append(urljoin(base_url, href))
    if not releases:
        raise ValueError(
            f'{base_url}: no "<year> Summary Data" links; the page layout may have changed'
        )
    return Catalog(tuple(releases), tuple(dictionaries))


def file_name(url: str) -> str:
    '''The file name at the end of url, percent-escapes decoded (ITA Data CY 2016.zip).'''
    return unquote(PurePosixPath(urlsplit(url).path).name)


def through_date(name: str) -> date | None:
    '''The submission through-date a summary file name carries, or None.'''
    match = THROUGH_DATE.search(name)
    if match is None:
        return None
    month, day, year = (int(part) for part in match.groups())
    return date(year, month, day)


def check_complete(catalog: Catalog) -> None:
    '''Refuse a catalog missing a year since 2016, or whose current file has no through-date.'''
    years = {release.year for release in catalog.releases}
    current = max(years)
    missing = [year for year in range(FIRST_YEAR, current + 1) if year not in years]
    if missing:
        raise ValueError('no summary file listed for ' + ', '.join(map(str, missing)))
    current_names = [file_name(r.url) for r in catalog.releases if r.year == current]
    if not any(through_date(name) for name in current_names):
        raise ValueError(f'the {current} summary file names no through-date: {current_names}')
