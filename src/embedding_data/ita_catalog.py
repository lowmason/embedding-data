'''Find the Form 300A summary files and data dictionaries listed on OSHA's ITA data page.

The page (https://www.osha.gov/itadata) links each year's summary file with the text
"<year> Summary Data" and each summary data dictionary with text beginning "Summary Data
Dictionary"; case-detail links are ignored. The current year's file name carries its
submission through-date (ITA_300A_Summary_Data_2025_through_08-31-2026.csv), and OSHA
renames the file as it grows, so a re-acquired release arrives under a new name.
'''

import re
from collections import Counter
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
    '''The file name at the end of url, percent-escapes decoded (ITA Data CY 2016.zip).

    A name that is empty, . or .., or that decodes to hold a slash or backslash, is
    refused, so no link can place a file outside the directory it is written to.
    '''
    name = unquote(PurePosixPath(urlsplit(url).path).name)
    if name in ('', '.', '..') or '/' in name or '\\' in name:
        raise ValueError(f'{url}: {name!r} is not a plain file name')
    return name


def through_date(name: str) -> date | None:
    '''The submission through-date a summary file name carries, or None.

    A through-date that is not a real date (through_02-30-2026) is refused, naming the file.
    '''
    match = THROUGH_DATE.search(name)
    if match is None:
        return None
    month, day, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError as error:
        raise ValueError(f'{name}: the through-date is not a real date ({error})') from None


def check_complete(catalog: Catalog) -> None:
    '''Refuse a catalog that cannot be acquired as listed, before anything is downloaded.

    That is one that lists a year twice or misses one since 2016, names a through-date
    that is not a real date, or whose current file has no through-date.
    '''
    years = Counter(release.year for release in catalog.releases)
    repeated = sorted(year for year, count in years.items() if count > 1)
    if repeated:
        raise ValueError('more than one summary file listed for ' + ', '.join(map(str, repeated)))
    current = max(years)
    missing = [year for year in range(FIRST_YEAR, current + 1) if year not in years]
    if missing:
        raise ValueError('no summary file listed for ' + ', '.join(map(str, missing)))
    names = {release.year: file_name(release.url) for release in catalog.releases}
    # Every year's name is read, so a malformed through-date fails here, not after a download.
    dates = {year: through_date(name) for year, name in names.items()}
    if dates[current] is None:
        raise ValueError(f'the {current} summary file names no through-date: {names[current]}')
