# ITA Form 300A Acquisition and Stacked Establishment Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/embedding-evaluation-data-spec-roadmap.md, Stage 2 — on plan
> completion, tick the stage and re-validate later stages against what shipped.

**Goal:** Every Form 300A summary file from 2016 on is acquired and stacked into one harmonized establishment-year table.

**Architecture:** Three new modules sit behind the existing `osha` command.
- `ita_catalog` turns OSHA's ITA data page into a list of yearly summary releases and dictionaries. It is pure and tested against a recorded copy of the page.
- `osha_encoding` moves the existing mixed-encoding line decoder out of `osha_benchmark_download` so the new modules can share it.
- `ita_summary` holds the offline transformation. For each year it picks the latest recorded raw file, transcodes it, harmonizes the columns, checks its structure and flags its records. It then rebuilds one stacked Parquet table and reports rows per year beside OSHA's published counts.

`osha` gains sets like `acs` and `cps`: `summary`, `case-detail`, or both by default. The manifest gains an optional `through_date`. The live download of about 258 MB runs once, behind an owner gate.

**Tech Stack:** Python 3.14, Typer, httpx 0.28.1 (HTTP/2), Polars 2.0, stdlib `html.parser` and `zipfile`, pytest, ruff. No new dependencies.

**Spec:** `specs/embedding-evaluation-data-spec.md`. Stage 2 covers R2.1, R2.3, R2.4, R2.9, R1.1, R9.1 and V10 (ITA). The spec stays live after this plan: per the roadmap's Completion section it retires with the roadmap, so Plan Completion Protocol step 5 must not move it.

## Global Constraints

- R1.4: "Raw downloads are immutable and kept as delivered: ITA zip and CSV files; IPUMS `.csv.gz` data with its `.xml` DDI codebook and the submitted definition (`extract.json`). A manifest records each raw file's source URL or IPUMS sample IDs, extract number, retrieval time, SHA-256, and client version. Transformations read raw files and write derived Parquet; nothing edits a raw file."
- R2.1: "Acquire every Form 300A summary file from 2016 through the current year from the ITA data page. The current-year file grows while submissions continue — the 2025 file covers submissions through 2026-08-31 — so record its through-date and re-acquire until OSHA moves it to the historical list."
- R2.3: "Stack all years into one establishment-year table keyed on `year_filing_for`, harmonizing three dictionary changes introduced with the 2023 data: `establishment_id`, added to link summary and case-detail files; the split of size code `2` into `21` and `22`; and NAICS codes that may be 2012, 2017, or 2022 vintage, identified by `naics_year`." (Task 8 amends this to match the delivered files.)
- R2.4: "Retain `establishment_name`, `establishment_id`, `ein`, `company_name`, `street_address`, `city`, `state`, `zip_code`, `naics_code`, `naics_year`, `industry_description`, `establishment_type`, `size`, `annual_average_employees`, `total_hours_worked`, and `year_filing_for`. Injury and illness counts stay in the raw files; they are not benchmark inputs."
- R2.9: "Flag, never drop, implausible records: hours per employee outside a plausible annual range, zero or missing employment, and establishments whose size and industry place them outside the filing rule."
- Core principle: "Values a source imputed … are flagged at ingestion". A `naics_year` the dictionary supplies is marked, never presented as delivered.
- R9.1: "Ingestion streams each CSV to Parquet with polars, keeping alphanumeric code columns as strings. Transformations are lazy polars with method-style expressions."
- R9.2: "Every transformation is deterministic and runs offline from raw files. Tests use fixtures, with no network and no credentials."
- R8.3: "ITA files are public, so ITA-derived tables may contain establishment-level rows."
- V10 (ITA): "Compare ITA rows per year with OSHA's published submission counts" and "record the gap rather than tuning it away."
- R2.5 and R2.6 are out of scope here (Stages 4 and 10). Codes and descriptions are stored as delivered: no NAICS mapping, no description normalization, and no ZIP or EIN padding.
- Style: single-quoted strings, `'''` docstrings, 99 columns, and ruff rules E, F, I and Q. Every file this plan touches uses 4-space indentation. If `ruff check` reorders imports, accept `uv run --locked ruff check --fix .`.
- Test seams: OSHA tests patch `osha_benchmark_download.make_client` with a `partial` that injects an `httpx.MockTransport`. Downloaded bodies must use `stream=httpx.ByteStream(...)` (the existing `streamed()` helper). Every command test passes `--data-dir` (the `data_directory` fixture).
- Never run `osha` against the network outside Task 7. The pre-commit hook runs the full pytest suite on every commit, so every task's commit must leave the suite green.
- The real data tree is `/Users/lowell/Projects/embedding-data/data`. `data/` is gitignored, so a git worktree has none, and `paths.DATA_DIR` there points at an empty tree. Every step that touches real data (Task 2 Step 4, Task 7) names that root explicitly, as plan 1's Task 7 did, and never relies on the default.
- Baseline before Task 1: `uv run --locked pytest` shows 96 passed, and `uv run --locked behave` shows 2 scenarios passed.

## Decisions

- **D1** (owner, roadmap, 2026-10-12): the case-detail download is kept and recorded in the spec as acquired, feeding no target. Applied in: Task 6 (docstring, README); Task 8 (spec amendment A1).
- **D2** (owner, plan review, 2026-10-12): the industry half of R2.9's filing-rule flag is deferred to Stage 4, which builds the NAICS vintage concordances it needs. Stage 2 ships the size half, `flag_below_filing_size`. Applied in: Task 4; Notes for the completion Handoff (deferred item and Stage 4 bullet).
- **D3** (owner, plan review, 2026-10-12): plausible annual hours per average employee are 500–4,000, inclusive. Applied in: Task 4 (`HOURS_PER_EMPLOYEE`).
- **D4** (owner, plan review, 2026-10-12): a bare `uv run embedding-data osha` runs both sets, mirroring `cps`. CLAUDE.md warns against running `osha` unless asked. Applied in: Task 6.
- **D5** (owner, plan review, 2026-10-12): the plan is committed on branch `stage-2-ita-300a`, created from `main`, and execution works on that branch. Applied in: execution setup.
- **D6** (owner, plan review, 2026-10-12): the remaining planning defaults (P2–P7 and P9–P14) and Task 8's amendments A1–A3, word for word, are approved as written. Task 8 applies them without asking again. Applied in: Tasks 1–8.

**Planning defaults (approved at plan review; P1 by D4, P8 by D2 and D3, the rest by D6):**

- **P1. Command surface.** `uv run embedding-data osha [summary] [case-detail]` mirrors `acs` and `cps`, and runs both sets by default. The existing case-detail tests pass `case-detail` explicitly. `--data-dir` is unchanged.
- **P2. Discovery.** Releases come from the live ITA data page (`https://www.osha.gov/itadata`), not a hardcoded list.
  - An anchor whose text reads `<year> Summary Data` is a release. Text beginning `Summary Data Dictionary` marks a dictionary.
  - The year comes from the link text.
  - The run refuses a page that skips a year after 2016, or whose current-year file names no through-date.
- **P3. Raw layout.** A summary file goes to `raw/osha/summary/<year>/<OSHA's file name>`, with percent-escapes decoded (`ITA Data CY 2016.zip`). The two summary dictionaries go to `raw/osha/summary/`. Case-detail paths are unchanged.
- **P4. Through-date in the manifest.** `ManifestEntry` gains `through_date: str | None = None`, an ISO date parsed from the file name (`..._through_08-31-2026.csv`). Lines written before the field existed still read.
- **P5. One raw file per year, rebuilt every run.**
  - A year uses its only file. When a year has several, it uses the one whose name carries the latest through-date; two files in a year without distinct through-dates fail the build.
  - The table is rebuilt on every `summary` run, through a `.part` rename. This is not convert-once, unlike case detail (plan 1, Handoff, trap 1).
  - Each row's `source_file` is its raw file's manifest path, and an input with no manifest entry fails the build.
  - A summary file on disk but not in the manifest stops the acquisition, because `raw_backfill` records only the case-detail files.
- **P6. Size.** `size` keeps the native code (1, 2, 21, 22, 3).
  - `size_class` merges 21 and 22 into 2, so it is one scheme in every year: 1 is <20 employees, 2 is 20–249 and 3 is 250+.
  - Code 2 is never split using `annual_average_employees`, because `size` is peak employment. A split would be imputation.
  - Evidence: the first ~900 rows of each of the 2023, 2024 and 2025 files hold 2 alongside 21 and 22.
- **P7. NAICS vintage before 2023.** The files lack `naics_year`, and the Summary Data Dictionary says data through 2022 use 2012 NAICS. Those rows get `naics_year = 2012` with `naics_year_from_dictionary = true`, wherever a code is present.
- **P8. R2.9 flags.** All three are kept on every row; no row is dropped.
  - `flag_employment`: annual average employment is missing, zero or negative.
  - `flag_hours_per_employee`: hours per average employee fall outside **[500, 4,000]** (inclusive), or hours are missing. It is null where `flag_employment` is set. 500 is about 10 hours a week all year; 4,000 is about 77.
  - `flag_below_filing_size`: `size_class` is 1, which is outside the filing rule in every industry.
  - **The industry half of the filing rule is deferred to Stage 4.** The rule's lists use fixed NAICS vintages, and no concordance exists yet:
    - The 20–249 designated list (29 CFR 1904 Subpart E, App. A) uses 2012-era codes through the 2022 data. Its 2024-01-01 version uses 2017 codes: `4521`/`4529` became `4522`/`4523`, and `7213` was dropped.
    - The partially exempt list (Subpart B, App. A) uses pre-2012 codes such as `5181`.
    - Per the dictionary, most codes from 2023 on are labelled 2022.
  - Prefix matching now would mis-flag establishments. *Alternative:* evaluate the industry half now only where a record's vintage matches the list's, and leave it null elsewhere.
- **P9. Fail on structure, flag records.** The build fails on any of these:
  - a zip that does not hold exactly one CSV;
  - a required column missing after lowercasing headers;
  - a row filed for another year;
  - a fraction that is not zero (the 2019 file writes `452990.00`);
  - a NAICS code that is not six digits;
  - a size code or NAICS vintage the dictionary does not define.
- **P10. Columns.** The table keeps R2.4's columns plus `id` (OSHA's record number), `source_file`, `naics_year_from_dictionary`, `size_class` and the three flags. Injury counts, submission timestamps and change reasons stay in the raw files.
- **P11. Same-name replacement at the source is not detected.** OSHA re-posted the 2016–2020 zips on 2025-11-25, and the 2023 and 2024 zips on 2026-05-20 with `_v2` members, under unchanged names. A path has one manifest entry forever, so a refreshed file under an old name is not fetched. This becomes a deferred item.
- **P12. V10 counts.** The code holds only figures OSHA published, with an unambiguous year:
  - 2023: exactly 385,488, as of 2024-05-31 (OSHA 2023 Work-Related Injury and Illness Summary).
  - 2024: over 390,000, as-of not stated (OSHA 2024 Work-Related Injury and Illness Summary).

  The finding file records the rest:
  - The ITA–SOII comparison PDF's "In 2024, OSHA collected summary data from over 370,000 establishments" does not name its data year.
  - J.J. Keller's ">300,000" for 2022 is not OSHA's figure.
  - No count was located for 2016–2022 or 2025.
  - Each gap is recorded with both dates (the count's as-of and the file's through-date), not treated as an error.
- **P13. Live canary.** One `@pytest.mark.network` test fetches the live page and checks that it still parses and is complete. `addopts` deselects it by default, and unknown markers become errors.
- **P14. Spec amendments.** Task 8's A1–A3 wording, approved at plan review (D6).

---

## File structure

| File | Responsibility |
| --- | --- |
| `src/embedding_data/ita_catalog.py` (new) | Parse the ITA page into releases and dictionaries; file names; through-dates; completeness check |
| `src/embedding_data/osha_encoding.py` (new) | The mixed UTF-8/Windows-1252 line decoder, moved from `osha_benchmark_download` |
| `src/embedding_data/ita_summary.py` (new) | Offline: transcode, harmonize, check, flag, choose one file per year, stack, report |
| `src/embedding_data/manifest.py` | Optional `through_date` field |
| `src/embedding_data/osha_benchmark_download.py` | The `osha` command: sets, summary acquisition, case-detail acquisition |
| `tests/fixtures/osha/itadata.html` (new) | Recorded excerpt of the ITA page |
| `tests/ita_fixtures.py` (new) | Miniature summary files in every published format |
| `tests/test_ita_catalog.py`, `tests/test_ita_summary.py` (new) | Catalog and transformation tests |
| `tests/test_manifest.py`, `tests/test_osha_benchmark_download.py`, `tests/test_cli.py` | Extended |
| `pyproject.toml` | `network` marker, deselected by default |
| `README.md`, `CLAUDE.md` | Docs |
| `specs/findings/v10-ita-300a-totals.md` (new) | V10 finding from the live run |
| `specs/embedding-evaluation-data-spec.md` | Amendments A1–A3 |

---

### Task 1: Read the ITA data page (`ita_catalog`) and add a live canary

**Files:**
- Create: `src/embedding_data/ita_catalog.py`
- Create: `tests/fixtures/osha/itadata.html`
- Create: `tests/test_ita_catalog.py`
- Modify: `pyproject.toml` (`[tool.pytest.ini_options]`)

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `ita_catalog.PAGE_URL: str`, `ita_catalog.FIRST_YEAR: int` (2016).
  - `SummaryRelease(year: int, url: str)` and `Catalog(releases: tuple[SummaryRelease, ...], dictionaries: tuple[str, ...])`, both frozen dataclasses.
  - `parse_catalog(html: str, base_url: str = PAGE_URL) -> Catalog`, which raises `ValueError` when the page has no release links.
  - `file_name(url: str) -> str`, with percent-escapes decoded.
  - `through_date(name: str) -> datetime.date | None`.
  - `check_complete(catalog: Catalog) -> None`, which raises `ValueError`.

- [ ] **Step 1: Record the page fixture**

Create `tests/fixtures/osha/itadata.html` with exactly this content. The two card bodies are copied verbatim from the page as fetched on 2026-10-12, tab indentation included:

```html
<!-- Excerpt of https://www.osha.gov/itadata as fetched 2026-10-12: the "Current ITA Data"
and "Historical Data" cards, verbatim. A U.S. government work. -->
<html><body>
<div class="usa-card__header">
<h4 class="usa-card__heading">Current ITA Data</h4>
</div>

<div class="usa-card__body">
<p>Download current ITA Summary and Case Detail Data, covering 2025 work-related injuries and illnesses submitted from 1/1/2026 through 8/31/2026.</p>

<ul>
	<li><a href="/sites/default/largefiles/ITA_300A_Summary_Data_2025_through_08-31-2026.csv" title="2025 Summary Data - CSV">2025 Summary Data</a> <span class="label label-primary">NEW</span></li>
	<li><a href="/sites/default/files/summary_data_dictionary.pdf" title="Injury Tracking Application (ITA) 300A Summary Data Dictionary - PDF">Summary Data Dictionary</a></li>
	<li><a href="/sites/default/largefiles/ITA_Case_Detail_Data_2025_through_08-31-2026.csv" title="2025 Case Detail Data - CSV">2025 Case Detail Data</a> <span class="label label-primary">NEW</span></li>
	<li><a href="/sites/default/files/case_detail_data_dictionary_2026.pdf" title="Injury Tracking Application (ITA) Case Detail Data Dictionary - PDF">Case Detail Data Dictionary</a></li>
</ul>
</div>

<div class="usa-card__header">
<h4 class="usa-card__heading">Historical Data</h4>
</div>

<div class="usa-card__body">
<p>Work-related injuries and illnesses submitted by employers to the ITA each year. The ITA collects one year of data at a time. Summary data has been collected by the ITA since 2016. Case Detail data has been collected since 2023.</p>

<ul>
	<li><a href="/sites/default/files/ITA_300A_Summary_Data_2024_through_12-31-2025.zip" title="ITA 300A Summary Data 2024 through 12-31-2025 - ZIP">2024 Summary Data</a></li>
	<li><a href="/sites/default/files/ITA_Case_Detail_Data_2024_through_12-31-2025.zip" title="ITA Case Detail Data 2024 through 12-31-2025 - ZIP">2024 Case Detail Data</a></li>
	<li><a href="/sites/default/files/ITA_300A_Summary_Data_2023_through_12-31-2024.zip" target="_self" title="ITA 300A Summary Data 2023 through 12-31-2024 - ZIP">2023 Summary Data</a></li>
	<li><a href="/sites/default/largefiles/ITA_Case_Detail_Data_2023_through_12-31-2023OIICS.zip" title="2023 ITA Case Detail Data - ZIP">2023 Case Detail Data</a></li>
	<li><a href="/sites/default/files/ITA-data-cy2022.zip" target="_self" title="2022 Summary Data - ZIP">2022 Summary Data</a></li>
	<li><a href="/sites/default/files/ITA-data-cy2021.zip" target="_self" title="2021 Summary Data - ZIP">2021 Summary Data</a></li>
	<li><a href="/sites/default/files/ITA-Data-CY-2020.zip" target="_self" title="2020 Summary Data - ZIP">2020 Summary Data</a></li>
	<li><a href="/sites/default/files/ITA%20Data%20CY%202019.zip" target="_self" title="2019 Summary Data - ZIP">2019 Summary Data</a></li>
	<li><a href="/sites/default/files/ITA%20Data%20CY%202018.zip" target="_self" title="2018 Summary Data - ZIP">2018 Summary Data</a></li>
	<li><a href="/sites/default/files/ITA%20Data%20CY%202017.zip" target="_self" title="2017 Summary Data - ZIP">2017 Summary Data</a></li>
	<li><a href="/sites/default/files/ITA%20Data%20CY%202016.zip" target="_self" title="2016 Summary Data - ZIP">2016 Summary Data</a></li>
	<li><a href="/sites/default/files/ITA_Data_Dictionary.pdf" target="_self" title="Injury Tracking Application Data Dictionary - PDF">Summary Data Dictionary (2016-2023 Data)</a></li>
	<li><a href="/sites/default/files/case_detail_data_dictionary.pdf" title="Injury Tracking Application Data Dictionary - PDF">Case Detail Data Dictionary (2023-2024 Data) </a></li>
</ul>
</div>
</body></html>
```

- [ ] **Step 2: Register the `network` marker**

In `pyproject.toml`, replace the `[tool.pytest.ini_options]` table with:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m 'not network'"
markers = [
    "network: fetches a live osha.gov page; deselected by default, run with -m network",
]
filterwarnings = ["error::pytest.PytestUnknownMarkWarning"]
```

- [ ] **Step 3: Write the failing tests**

Create `tests/test_ita_catalog.py`:

```python
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


@pytest.mark.network
def test_the_live_page_still_lists_every_summary_year():
    '''Canary for a page relayout; run deliberately with `pytest -m network`.'''
    with osha.make_client() as client:
        page = client.get(ita_catalog.PAGE_URL)
    page.raise_for_status()

    catalog = ita_catalog.parse_catalog(page.text, str(page.url))

    ita_catalog.check_complete(catalog)
    assert catalog.dictionaries
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_ita_catalog.py -v`
Expected: collection fails with `ImportError: cannot import name 'ita_catalog'`.

- [ ] **Step 5: Write the module**

Create `src/embedding_data/ita_catalog.py`:

```python
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
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_ita_catalog.py -v`
Expected: every test passes. The canary is reported as deselected (`1 deselected`).

Run: `uv run --locked pytest`
Expected: all tests pass, with `1 deselected`.

- [ ] **Step 7: Lint and commit**

```bash
uv run --locked ruff check .
git add pyproject.toml src/embedding_data/ita_catalog.py tests/fixtures/osha/itadata.html tests/test_ita_catalog.py
git commit -m "feat(osha): read Form 300A releases from the ITA data page

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Record a release's through-date in the manifest

**Files:**
- Modify: `src/embedding_data/manifest.py`
- Test: `tests/test_manifest.py`

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `ManifestEntry.through_date: str | None = None`, an ISO date, and the dataclass's last field.
  - `manifest.describe_file(..., through_date: datetime.date | None = None)`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_manifest.py`, change the datetime import to:

```python
from datetime import UTC, date, datetime, timedelta, timezone
```

and append:

```python
def test_through_date_is_recorded_as_an_iso_date(raw_file, data_directory):
    manifest_path = paths.manifest_path(data_directory)
    entry = describe(raw_file, data_directory, through_date=date(2026, 8, 31))

    manifest.append_entries(manifest_path, [entry])

    assert json.loads(manifest_path.read_text())['through_date'] == '2026-08-31'
    assert manifest.read_manifest(manifest_path) == [entry]


def test_a_line_recorded_before_through_date_existed_still_reads(data_directory):
    manifest_path = paths.manifest_path(data_directory)
    manifest_path.parent.mkdir(parents=True)
    stage_1_line = {
        'path': 'osha/case_detail_data_dictionary_2026.pdf', 'sha256': ABC_SHA256,
        'size': 3, 'retrieved_at': '2026-10-12T15:28:00+00:00', 'client': 'httpx',
        'client_version': '0.28.1', 'source_url': 'https://www.osha.gov/x.pdf',
        'collection': None, 'extract_number': None, 'samples': [], 'proxies': [],
    }
    manifest_path.write_text(json.dumps(stage_1_line) + '\n')

    [entry] = manifest.read_manifest(manifest_path)

    assert entry.path == 'osha/case_detail_data_dictionary_2026.pdf'
    assert entry.through_date is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_manifest.py -v`
Expected: `test_through_date_is_recorded_as_an_iso_date` fails with `TypeError: describe_file() got an unexpected keyword argument 'through_date'`, and `test_a_line_recorded_before_through_date_existed_still_reads` fails with `AttributeError` on `through_date`.

- [ ] **Step 3: Implement**

In `src/embedding_data/manifest.py`:

1. Append to the module docstring, before its closing `'''`, the sentence: `` `through_date` is the submission through-date an OSHA ITA summary file's name carries. ``
2. Change `from datetime import UTC, datetime` to `from datetime import UTC, date, datetime`.
3. Add the last dataclass field after `proxies: tuple[str, ...] = ()`:

```python
    through_date: str | None = None
```

4. In `describe_file`, add the keyword parameter after `proxies: Iterable[str] = (),`:

```python
    through_date: date | None = None,
```

and add this argument to the `ManifestEntry(...)` call, after `proxies=tuple(proxies),`:

```python
        through_date=None if through_date is None else through_date.isoformat(),
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_manifest.py -v`
Expected: all pass.

Confirm that the real manifest still reads. This is read-only:

Run: `uv run --locked python -c "from pathlib import Path; from embedding_data import manifest, paths; print(len(manifest.read_manifest(paths.manifest_path(Path('/Users/lowell/Projects/embedding-data/data')))))"`
Expected: `17`. A `0` means the path is wrong: stop.

Run: `uv run --locked pytest`
Expected: all pass, `1 deselected`.

- [ ] **Step 5: Commit**

```bash
uv run --locked ruff check .
git add src/embedding_data/manifest.py tests/test_manifest.py
git commit -m "feat(manifest): record a release's through-date

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Harmonize one year's summary file (`ita_summary`)

**Files:**
- Create: `src/embedding_data/osha_encoding.py`
- Modify: `src/embedding_data/osha_benchmark_download.py` (move the decoder out)
- Create: `src/embedding_data/ita_summary.py`
- Create: `tests/ita_fixtures.py`
- Create: `tests/test_ita_summary.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `osha_encoding.decode_line(raw: bytes) -> str`. It stays importable as `osha_benchmark_download.decode_line`.
  - `ita_summary.transcode(raw_file: Path, utf8_path: Path) -> None`.
  - `ita_summary.harmonize(lf: pl.LazyFrame, year: int, source_file: str) -> pl.LazyFrame`.
  - `ita_summary.check_summary(lf: pl.LazyFrame, year: int, source_file: str) -> None`.
  - `ita_summary.harmonize_file(raw_file: Path, year: int, source_file: str, utf8_path: Path) -> pl.LazyFrame`.
  - The constants `ita_summary.SIZE_CLASS`, `NAICS_YEARS` and `DICTIONARY_NAICS_YEAR`.
  - `tests/ita_fixtures.py`: `OLD_COLUMNS`, `COLUMNS_2023`, `COLUMNS_2024`, `COLUMNS_2025`, `RELEASE_NAMES`, `MEMBER_NAMES`, `record`, `csv_bytes`, `zipped` and `year_file`.

The harmonized frame has exactly these columns, in this order:
- the integer columns `id`, `establishment_id`, `establishment_type`, `size`, `annual_average_employees`, `total_hours_worked` and `year_filing_for`, all Int64;
- the text columns `establishment_name`, `company_name`, `ein`, `street_address`, `city`, `state`, `zip_code` and `industry_description`, all String;
- `naics_code` (String), `naics_year` (Int64), `naics_year_from_dictionary` (Boolean), `size_class` (Int64) and `source_file` (String).

- [ ] **Step 1: Move the decoder into `osha_encoding`**

Create `src/embedding_data/osha_encoding.py`:

```python
'''Decode OSHA ITA CSV lines that mix UTF-8 and Windows-1252 bytes.

Most non-ASCII text in the ITA files is Windows-1252, a few rows are UTF-8, and one line
can hold both. Each line is decoded as UTF-8, and only the bytes UTF-8 rejects are decoded
as Windows-1252; its five undefined bytes still raise.
'''

import codecs

def cp1252_fallback(error: UnicodeDecodeError) -> tuple[str, int]:
    '''Decode only the bytes UTF-8 rejected as Windows-1252; its five undefined bytes raise.'''
    return error.object[error.start:error.end].decode('cp1252'), error.end


codecs.register_error('osha-cp1252-fallback', cp1252_fallback)


def decode_line(raw: bytes) -> str:
    '''Decode one raw CSV line that may mix UTF-8 and Windows-1252 bytes.'''
    return raw.decode('utf-8', errors='osha-cp1252-fallback')
```

(The single blank line after the import is ruff's `lines-after-imports = 1`.)

In `src/embedding_data/osha_benchmark_download.py`, make these changes:
- Delete `import codecs`.
- Delete the `cp1252_fallback` function, the `codecs.register_error(...)` line and the `decode_line` function.
- Add `from embedding_data.osha_encoding import decode_line` after `from embedding_data import manifest, paths`.

Run: `uv run --locked pytest tests/test_osha_benchmark_download.py -q`
Expected: all pass. `osha.decode_line` still resolves through the import.

- [ ] **Step 2: Write the fixture builders**

Create `tests/ita_fixtures.py`:

```python
'''Miniature Form 300A summary files in each format OSHA has published (2016-2025).

Headers, column order, quoting, BOM, member names and number formats copy the delivered
files; the values are invented. year_file(year) renders records as that year's file does.
'''

import io
import zipfile

OLD_COLUMNS = (
    'id', 'company_name', 'establishment_name', 'ein', 'street_address', 'city', 'state',
    'zip_code', 'naics_code', 'industry_description', 'annual_average_employees',
    'total_hours_worked', 'no_injuries_illnesses', 'total_deaths', 'total_dafw_cases',
    'total_djtr_cases', 'total_other_cases', 'total_dafw_days', 'total_djtr_days',
    'total_injuries', 'total_poisonings', 'total_respiratory_conditions',
    'total_skin_disorders', 'total_hearing_loss', 'total_other_illnesses', 'establishment_id',
    'establishment_type', 'size', 'year_filing_for', 'created_timestamp', 'change_reason',
)
NEW_COLUMNS = (
    'id', 'establishment_name', 'establishment_id', 'ein', 'company_name', 'street_address',
    'city', 'state', 'zip_code', 'naics_code', 'naics_year', 'industry_description',
    'establishment_type', 'size', 'annual_average_employees', 'total_hours_worked',
    'no_injuries_illnesses', 'total_deaths', 'total_dafw_cases', 'total_djtr_cases',
    'total_other_cases', 'total_dafw_days', 'total_djtr_days', 'total_injuries',
    'total_skin_disorders', 'total_respiratory_conditions', 'total_poisonings',
    'total_hearing_loss', 'total_other_illnesses',
)
COLUMNS_2023 = (*NEW_COLUMNS, 'created_timestamp', 'change_reason', 'year_filing_for')
COLUMNS_2024 = (*NEW_COLUMNS, 'change_reason', 'created_timestamp', 'year_filing_for')
COLUMNS_2025 = (
    'ID', 'establishment_name', 'establishment_ID', *NEW_COLUMNS[3:],
    'date_submitted', 'Change_reason', 'year_filing_for',
)

RELEASE_NAMES = {
    **{year: f'ITA Data CY {year}.zip' for year in range(2016, 2020)},
    2020: 'ITA-Data-CY-2020.zip',
    2021: 'ITA-data-cy2021.zip',
    2022: 'ITA-data-cy2022.zip',
    2023: 'ITA_300A_Summary_Data_2023_through_12-31-2024.zip',
    2024: 'ITA_300A_Summary_Data_2024_through_12-31-2025.zip',
    2025: 'ITA_300A_Summary_Data_2025_through_08-31-2026.csv',
}
MEMBER_NAMES = {
    **{year: f'ITA Data CY {year}.csv' for year in range(2016, 2021)},
    2021: 'ITA 2021 data.csv',
    2022: 'CY 2022.csv',
    2023: 'ITA 300A Summary Data 2023 through 12-31-2024_v2.csv',
    2024: 'ITA_300A_Summary_Data_2024_through_12-31-2025_v2.csv',
}


def record(year: int, **fields: str) -> dict[str, str]:
    '''One establishment-year, numbers formatted as that year's file writes them.'''
    def number(value: int) -> str:
        return f'{value}.00' if year == 2019 else str(value)

    values = {
        'id': number(year * 10),
        'establishment_id': number(year),
        'establishment_name': 'Acme Plant 7',
        'company_name': 'Acme Holdings, Inc.',
        'ein': '' if year <= 2018 else '012345678',
        'street_address': '1 Main St',
        'city': 'Springfield',
        'state': 'IL',
        'zip_code': '02134',
        'naics_code': number(332312),
        'naics_year': '2022',
        'industry_description': 'Fabricated structural metal',
        'establishment_type': '1',
        'size': number(2 if year <= 2022 else 22),
        'annual_average_employees': number(100),
        'total_hours_worked': number(200_000),
        'year_filing_for': number(year),
        'created_timestamp': '1/1/2024',
        'date_submitted': '2/16/2026',
        'change_reason': '',
    }
    values.update(fields)
    return values


def cell(value: str, quote_text: bool) -> str:
    '''One CSV field: quoted if it holds a comma or quote, or is text in a quoted file.'''
    is_number = value.replace('.', '', 1).isdigit()
    if ',' in value or '"' in value or (quote_text and value and not is_number):
        return '"' + value.replace('"', '""') + '"'
    return value


def csv_bytes(columns, records, *, quote_text=False, bom=False, zero='0') -> bytes:
    '''CRLF CSV of records in column order; columns a record lacks (injury counts) get zero.'''
    header = ','.join(f'"{column}"' if quote_text else column for column in columns)
    rows = [
        ','.join(cell(values.get(column.lower(), zero), quote_text) for column in columns)
        for values in records
    ]
    text = '\r\n'.join([header, *rows]) + '\r\n'
    return (b'\xef\xbb\xbf' if bom else b'') + text.encode('utf-8')


def zipped(member: str, data: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(member, data)
    return buffer.getvalue()


def year_file(year: int, records: list[dict[str, str]] | None = None) -> bytes:
    '''Records rendered as that year's raw file: zipped through 2024, a plain CSV in 2025.'''
    records = [record(year)] if records is None else records
    if year <= 2020:
        zero = '0.00' if year == 2019 else '0'
        data = csv_bytes(OLD_COLUMNS, records, quote_text=True, zero=zero)
    elif year <= 2022:
        data = csv_bytes(OLD_COLUMNS, records, bom=year == 2022)
    elif year <= 2024:
        data = csv_bytes(COLUMNS_2023 if year == 2023 else COLUMNS_2024, records)
    else:
        return csv_bytes(COLUMNS_2025, records)
    return zipped(MEMBER_NAMES[year], data)
```

- [ ] **Step 3: Write the failing tests**

Create `tests/test_ita_summary.py`:

```python
import io
import zipfile

import polars as pl
import pytest
from ita_fixtures import (
    COLUMNS_2023,
    MEMBER_NAMES,
    OLD_COLUMNS,
    RELEASE_NAMES,
    csv_bytes,
    record,
    year_file,
    zipped,
)
from polars.exceptions import InvalidOperationError

from embedding_data import ita_summary

HARMONIZED_SCHEMA = {
    'id': pl.Int64, 'establishment_id': pl.Int64, 'establishment_type': pl.Int64,
    'size': pl.Int64, 'annual_average_employees': pl.Int64, 'total_hours_worked': pl.Int64,
    'year_filing_for': pl.Int64, 'establishment_name': pl.String, 'company_name': pl.String,
    'ein': pl.String, 'street_address': pl.String, 'city': pl.String, 'state': pl.String,
    'zip_code': pl.String, 'industry_description': pl.String, 'naics_code': pl.String,
    'naics_year': pl.Int64, 'naics_year_from_dictionary': pl.Boolean,
    'size_class': pl.Int64, 'source_file': pl.String,
}


def harmonized(tmp_path, year, data, name=None):
    '''Write data as year's raw file under tmp_path and collect its harmonized rows.'''
    raw_file = tmp_path / (name or RELEASE_NAMES[year])
    raw_file.write_bytes(data)
    source_file = f'osha/summary/{year}/{raw_file.name}'
    utf8_path = tmp_path / f'{year}.utf8.csv'
    return ita_summary.harmonize_file(raw_file, year, source_file, utf8_path).collect()


def expected_row(year, **changes):
    row = {
        'id': year * 10, 'establishment_id': year, 'establishment_type': 1,
        'size': 2 if year <= 2022 else 22, 'annual_average_employees': 100,
        'total_hours_worked': 200_000, 'year_filing_for': year,
        'establishment_name': 'Acme Plant 7', 'company_name': 'Acme Holdings, Inc.',
        'ein': None if year <= 2018 else '012345678', 'street_address': '1 Main St',
        'city': 'Springfield', 'state': 'IL', 'zip_code': '02134',
        'industry_description': 'Fabricated structural metal', 'naics_code': '332312',
        'naics_year': 2012 if year <= 2022 else 2022,
        'naics_year_from_dictionary': year <= 2022, 'size_class': 2,
        'source_file': f'osha/summary/{year}/{RELEASE_NAMES[year]}',
    }
    row.update(changes)
    return row


@pytest.mark.parametrize('year', range(2016, 2026))
def test_every_published_format_harmonizes_to_one_schema(tmp_path, year):
    frame = harmonized(tmp_path, year, year_file(year))

    assert frame.schema == HARMONIZED_SCHEMA
    assert frame.rows(named=True) == [expected_row(year)]


def test_size_two_and_its_2023_split_share_one_harmonized_class(tmp_path):
    records = [
        record(2023, id=str(n), size=size) for n, size in enumerate(['1', '2', '21', '22', '3'])
    ]

    frame = harmonized(tmp_path, 2023, year_file(2023, records))

    assert frame['size'].to_list() == [1, 2, 21, 22, 3]
    assert frame['size_class'].to_list() == [1, 2, 2, 2, 3]


def test_naics_year_before_2023_comes_from_the_dictionary_and_says_so(tmp_path):
    records = [record(2022), record(2022, id='2', naics_code='')]

    frame = harmonized(tmp_path, 2022, year_file(2022, records))

    assert frame.select('naics_code', 'naics_year', 'naics_year_from_dictionary').rows() == [
        ('332312', 2012, True),
        (None, None, False),
    ]


def test_a_delivered_naics_year_is_kept_and_not_marked(tmp_path):
    records = [record(2024, naics_year='2012'), record(2024, id='2', naics_code='', naics_year='')]

    frame = harmonized(tmp_path, 2024, year_file(2024, records))

    assert frame.select('naics_code', 'naics_year', 'naics_year_from_dictionary').rows() == [
        ('332312', 2012, False),
        (None, None, False),
    ]


def test_a_fraction_that_is_not_zero_fails(tmp_path):
    data = year_file(2019, [record(2019, annual_average_employees='23.50')])

    with pytest.raises(InvalidOperationError):
        harmonized(tmp_path, 2019, data)


@pytest.mark.parametrize(
    ('fields', 'message'),
    [
        ({'year_filing_for': '2023'}, 'filed for a year other than 2024'),
        ({'naics_code': '33231'}, 'NAICS code that is not six digits'),
        ({'size': '4'}, 'size code the dictionary does not define'),
        ({'naics_year': '2007'}, 'NAICS vintage other than 2012, 2017 or 2022'),
    ],
    ids=['other-year', 'naics-code', 'size-code', 'naics-vintage'],
)
def test_rows_no_rule_covers_fail_the_build(tmp_path, fields, message):
    with pytest.raises(ValueError, match=message):
        harmonized(tmp_path, 2024, year_file(2024, [record(2024, **fields)]))


def test_a_missing_column_fails_the_build(tmp_path):
    columns = tuple(column for column in COLUMNS_2023 if column != 'naics_year')
    data = zipped(MEMBER_NAMES[2023], csv_bytes(columns, [record(2023)]))

    with pytest.raises(ValueError, match=r"missing columns \['naics_year'\]"):
        harmonized(tmp_path, 2023, data)


def test_a_zip_must_hold_exactly_one_csv(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('a.csv', b'id\r\n')
        archive.writestr('b.csv', b'id\r\n')

    with pytest.raises(ValueError, match='expected one CSV member'):
        harmonized(tmp_path, 2016, buffer.getvalue())


def test_bom_mojibake_and_windows_1252_bytes_survive_as_delivered(tmp_path):
    # 2022 opens with a UTF-8 BOM and carries UTF-8 mojibake of a Windows-1252 apostrophe;
    # other years carry raw Windows-1252 bytes. Text is kept as delivered, not repaired.
    data_2022 = year_file(2022, [record(2022, company_name='Farmerâ€™s Co-op')])
    text_2021 = csv_bytes(OLD_COLUMNS, [record(2021, company_name='Owner’s Choice')])
    data_2021 = zipped(MEMBER_NAMES[2021], text_2021.replace('’'.encode(), b'\x92'))

    frame_2022 = harmonized(tmp_path, 2022, data_2022)
    frame_2021 = harmonized(tmp_path, 2021, data_2021)

    assert frame_2022['company_name'].to_list() == ['Farmerâ€™s Co-op']
    assert frame_2022['id'].to_list() == [20220]
    assert frame_2021['company_name'].to_list() == ['Owner’s Choice']
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_ita_summary.py -v`
Expected: collection fails with `ImportError: cannot import name 'ita_summary'`.

- [ ] **Step 5: Write the module**

Create `src/embedding_data/ita_summary.py`:

```python
'''Stack the OSHA ITA Form 300A summary files into one establishment-year table (spec R2.3).

Each year's raw file (a zip holding one CSV, or the current year's plain CSV) is transcoded
to UTF-8, its headers are lowercased (2025 writes ID and establishment_ID), and the columns
spec R2.4 retains are cast: codes and text stay strings, counts become Int64. The 2019 file
writes every number with a zero fraction (452990.00), which is accepted; any other fraction
fails. Two dictionary changes are harmonized:

- size: code 2 (20-249 employees) was split into 21 (20-99) and 22 (100-249) with the 2023
  data, but the 2023 and later files still carry 2 for some establishments. size keeps the
  native code; size_class merges 21 and 22 into 2, one scheme in every year. Code 2 is
  never split, because size is peak employment, not the annual average.
- naics_year: delivered from the 2023 data on. Earlier files lack it, and the Summary Data
  Dictionary says data through 2022 use 2012 NAICS, so those rows take 2012 with
  naics_year_from_dictionary set.

establishment_id is present in every year's file and is kept as delivered; whether it
persists across years is spec V2's question. A file these rules do not cover fails the
build: a zip without exactly one CSV, a missing column, a row filed for another year, a
NAICS code that is not six digits, or an undocumented size code or NAICS vintage. Records
are flagged, never dropped (R2.9). Injury and illness counts, submission timestamps, and
change reasons stay in the raw files.
'''

import zipfile
from contextlib import ExitStack
from pathlib import Path

import polars as pl

from embedding_data.osha_encoding import decode_line

INTEGER_COLUMNS = [
    'id', 'establishment_id', 'establishment_type', 'size', 'annual_average_employees',
    'total_hours_worked', 'year_filing_for',
]
TEXT_COLUMNS = [
    'establishment_name', 'company_name', 'ein', 'street_address', 'city', 'state',
    'zip_code', 'industry_description',
]
REQUIRED_COLUMNS = [*INTEGER_COLUMNS, *TEXT_COLUMNS, 'naics_code']
NAICS_YEAR_FROM = 2023
DICTIONARY_NAICS_YEAR = 2012
NAICS_YEARS = [2012, 2017, 2022]
SIZE_CLASS = {1: 1, 2: 2, 21: 2, 22: 2, 3: 3}


def transcode(raw_file: Path, utf8_path: Path) -> None:
    '''Write raw_file's CSV, or the one CSV inside a zip, to utf8_path as UTF-8.'''
    with ExitStack() as stack:
        if raw_file.suffix.lower() == '.zip':
            archive = stack.enter_context(zipfile.ZipFile(raw_file))
            members = [name for name in archive.namelist() if name.lower().endswith('.csv')]
            if len(members) != 1:
                raise ValueError(f'{raw_file.name}: expected one CSV member, found {members}')
            source = stack.enter_context(archive.open(members[0]))
        else:
            source = stack.enter_context(raw_file.open('rb'))
        target = stack.enter_context(utf8_path.open('w', encoding='utf-8', newline=''))
        target.writelines(decode_line(line) for line in source)


def whole_number(column: str) -> pl.Expr:
    '''An Int64 column; a zero fraction (2019.00) is dropped and any other fraction fails.'''
    return pl.col(column).str.replace(r'\.0+$', '').cast(pl.Int64)


def harmonize(lf: pl.LazyFrame, year: int, source_file: str) -> pl.LazyFrame:
    '''The R2.4 columns of one year's file, typed, with size and NAICS vintage harmonized.'''
    lf = lf.rename(str.lower)
    names = lf.collect_schema().names()
    required = REQUIRED_COLUMNS + (['naics_year'] if year >= NAICS_YEAR_FROM else [])
    missing = [column for column in required if column not in names]
    if missing:
        raise ValueError(f'{source_file}: missing columns {missing}')
    naics_code = pl.col('naics_code').str.replace(r'\.0+$', '')
    if 'naics_year' in names:
        naics_year = whole_number('naics_year')
        from_dictionary = pl.lit(False)
    else:
        naics_year = pl.when(naics_code.is_not_null()).then(pl.lit(DICTIONARY_NAICS_YEAR))
        from_dictionary = naics_code.is_not_null()
    size_class = whole_number('size').replace_strict(
        SIZE_CLASS, default=None, return_dtype=pl.Int64
    )
    return lf.select(
        *(whole_number(column) for column in INTEGER_COLUMNS),
        *TEXT_COLUMNS,
        naics_code.alias('naics_code'),
        naics_year.cast(pl.Int64).alias('naics_year'),
        from_dictionary.alias('naics_year_from_dictionary'),
        size_class.alias('size_class'),
        pl.lit(source_file).alias('source_file'),
    )


def check_summary(lf: pl.LazyFrame, year: int, source_file: str) -> None:
    '''Fail on rows no harmonization rule covers, naming each kind and its count.'''
    labels = {
        'other_year': f'filed for a year other than {year}',
        'naics_code': 'with a NAICS code that is not six digits',
        'size': 'with a size code the dictionary does not define',
        'naics_year': 'with a NAICS vintage other than 2012, 2017 or 2022',
    }
    size, naics_year = pl.col('size'), pl.col('naics_year')
    counts = lf.select(
        other_year=pl.col('year_filing_for').ne_missing(year).sum(),
        naics_code=pl.col('naics_code').str.contains(r'^\d{6}$').not_().sum(),
        size=(size.is_not_null() & size.is_in(list(SIZE_CLASS)).not_()).sum(),
        naics_year=(naics_year.is_not_null() & naics_year.is_in(NAICS_YEARS).not_()).sum(),
    ).collect().row(0, named=True)
    problems = [f'{count:,} rows {labels[kind]}' for kind, count in counts.items() if count]
    if problems:
        raise ValueError(f'{source_file}: ' + '; '.join(problems))


def harmonize_file(
    raw_file: Path, year: int, source_file: str, utf8_path: Path,
) -> pl.LazyFrame:
    '''Transcode one raw summary file to utf8_path; return its checked, harmonized rows.

    The frame reads utf8_path lazily, so the caller keeps that file until the frame is
    collected or sunk. check_summary reads only the columns it checks, so a bad value in
    another integer column fails when the frame is collected or sunk.
    '''
    transcode(raw_file, utf8_path)
    lf = harmonize(pl.scan_csv(utf8_path, infer_schema=False), year, source_file)
    check_summary(lf, year, source_file)
    return lf
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_ita_summary.py -v`
Expected: all pass. That's 10 parametrized format cases plus the targeted cases.

Run: `uv run --locked pytest`
Expected: all pass, `1 deselected`.

- [ ] **Step 7: Commit**

```bash
uv run --locked ruff check .
git add src/embedding_data/osha_encoding.py src/embedding_data/osha_benchmark_download.py src/embedding_data/ita_summary.py tests/ita_fixtures.py tests/test_ita_summary.py
git commit -m "feat(osha): harmonize each Form 300A file format to one schema

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Flag implausible records (R2.9)

**Files:**
- Modify: `src/embedding_data/ita_summary.py`
- Test: `tests/test_ita_summary.py`

**Interfaces:**
- Consumes: Task 3's harmonized frame, with columns `annual_average_employees`, `total_hours_worked` and `size_class`.
- Produces:
  - `ita_summary.HOURS_PER_EMPLOYEE = (500, 4_000)`.
  - `ita_summary.add_flags(lf: pl.LazyFrame) -> pl.LazyFrame`, which adds the Boolean columns `flag_employment`, `flag_hours_per_employee` and `flag_below_filing_size`. The hours and filing-size flags are nullable.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ita_summary.py`:

```python
def test_implausible_records_are_flagged_not_dropped(tmp_path):
    cases = [  # (employees, hours, size) -> (employment, hours per employee, below size)
        (('100', '200000', '22'), (False, False, False)),  # 2,000 hours each
        (('100', '50000', '22'), (False, False, False)),   # 500, the inclusive lower bound
        (('100', '400000', '22'), (False, False, False)),  # 4,000, the inclusive upper bound
        (('100', '49900', '22'), (False, True, False)),    # 499
        (('100', '400100', '22'), (False, True, False)),   # 4,001
        (('100', '', '22'), (False, True, False)),         # hours missing
        (('0', '1000', '22'), (True, None, False)),        # zero employment: no ratio
        (('', '1000', '22'), (True, None, False)),         # employment missing: no ratio
        (('10', '20000', '1'), (False, False, True)),      # fewer than 20 at peak
        (('100', '200000', ''), (False, False, None)),     # size missing
    ]
    records = [
        record(2024, id=str(n), annual_average_employees=e, total_hours_worked=h, size=s)
        for n, ((e, h, s), _) in enumerate(cases)
    ]

    frame = ita_summary.add_flags(harmonized(tmp_path, 2024, year_file(2024, records)).lazy())
    flags = frame.select(
        'flag_employment', 'flag_hours_per_employee', 'flag_below_filing_size'
    ).collect()

    assert flags.rows() == [expected for _, expected in cases]
    assert flags.schema == {
        'flag_employment': pl.Boolean,
        'flag_hours_per_employee': pl.Boolean,
        'flag_below_filing_size': pl.Boolean,
    }
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --locked pytest tests/test_ita_summary.py::test_implausible_records_are_flagged_not_dropped -v`
Expected: FAIL with `AttributeError: module 'embedding_data.ita_summary' has no attribute 'add_flags'`.

- [ ] **Step 3: Implement**

In `src/embedding_data/ita_summary.py`, add after `SIZE_CLASS`:

```python
# Plausible annual hours worked per average employee, inclusive: about 10 to 77 hours a week.
HOURS_PER_EMPLOYEE = (500, 4_000)
```

and append:

```python
def add_flags(lf: pl.LazyFrame) -> pl.LazyFrame:
    '''Flag, never drop, the implausible records spec R2.9 names.

    flag_employment: annual average employment is missing, zero, or negative.
    flag_hours_per_employee: hours per average employee fall outside HOURS_PER_EMPLOYEE, or
        hours are missing; null where employment is flagged, since no ratio exists.
    flag_below_filing_size: fewer than 20 employees at peak (size_class 1), outside the
        filing rule in every industry. Whether a larger establishment's industry places it
        outside the rule needs NAICS vintage concordances and is not evaluated here.
    '''
    employees, hours = pl.col('annual_average_employees'), pl.col('total_hours_worked')
    no_employment = employees.is_null() | (employees <= 0)
    implausible_hours = hours.is_null() | (hours / employees).is_between(
        *HOURS_PER_EMPLOYEE
    ).not_()
    return lf.with_columns(
        flag_employment=no_employment,
        flag_hours_per_employee=pl.when(no_employment).then(None).otherwise(implausible_hours),
        flag_below_filing_size=pl.col('size_class') == 1,
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_ita_summary.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
uv run --locked ruff check .
git add src/embedding_data/ita_summary.py tests/test_ita_summary.py
git commit -m "feat(osha): flag implausible Form 300A records without dropping them

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Choose one file per year, stack them, and report totals (V10)

**Files:**
- Modify: `src/embedding_data/ita_summary.py`
- Modify: `tests/ita_fixtures.py` (add `write_release`)
- Test: `tests/test_ita_summary.py`

**Interfaces:**
- Consumes:
  - From Task 1: `ita_catalog.through_date(name) -> date | None`.
  - From Task 2: `manifest.describe_file(..., through_date=)` and `manifest.entry_for(manifest_path, raw_file) -> ManifestEntry`, which raises `KeyError`.
  - From Tasks 3 and 4: `harmonize_file` and `add_flags`.
  - `paths.raw_dir`, `paths.derived_dir` and `paths.manifest_path`.
- Produces:
  - `ita_summary.TABLE_NAME = 'ita_300a_summary.parquet'`.
  - `ita_summary.COLUMNS: list[str]`, the table's column order.
  - `summary_dir(data_dir: Path) -> Path` (`raw/osha/summary`).
  - `latest_release(year_dir: Path) -> Path`.
  - `summary_files(data_dir: Path) -> dict[int, Path]`.
  - `build_summary_table(data_dir: Path) -> Path`.
  - `PublishedCount`, `PUBLISHED_COUNTS`, `totals_report(table: Path) -> pl.DataFrame` and `report_lines(report: pl.DataFrame) -> list[str]`.
  - `tests/ita_fixtures.write_release(data_dir, year, data=None, name=None, *, recorded=True) -> Path`.

The stacked table's columns, in order:
- `year_filing_for` and `id`, both Int64;
- `establishment_id` (Int64);
- `establishment_name`, `company_name`, `ein`, `street_address`, `city`, `state`, `zip_code` and `naics_code`, all String;
- `naics_year` (Int64) and `naics_year_from_dictionary` (Boolean);
- `industry_description` (String);
- `establishment_type`, `size`, `size_class`, `annual_average_employees` and `total_hours_worked`, all Int64;
- `flag_employment`, `flag_hours_per_employee` and `flag_below_filing_size`, all Boolean;
- `source_file` (String).

Rows are sorted by `year_filing_for`, then `id`.

- [ ] **Step 1: Add the raw-tree fixture helper**

Append to `tests/ita_fixtures.py`, and add the imports at the top:

```python
from datetime import UTC, datetime
from pathlib import Path

from embedding_data import ita_catalog, manifest, paths
```

```python
RETRIEVED_AT = datetime(2026, 10, 12, tzinfo=UTC)


def write_release(
    data_dir: Path, year: int, data: bytes | None = None, name: str | None = None,
    *, recorded: bool = True,
) -> Path:
    '''Place a summary file at raw/osha/summary/<year>/<name> and, by default, record it.'''
    name = name or RELEASE_NAMES[year]
    path = paths.raw_dir(data_dir, 'osha') / 'summary' / str(year) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(year_file(year) if data is None else data)
    if recorded:
        manifest_path = paths.manifest_path(data_dir)
        entry = manifest.describe_file(
            path,
            manifest_path.parent,
            retrieved_at=RETRIEVED_AT,
            client='httpx',
            client_version='0.28.1',
            source_url=f'https://www.osha.gov/sites/default/files/{name}',
            through_date=ita_catalog.through_date(name),
        )
        manifest.append_entries(manifest_path, [entry])
    return path
```

- [ ] **Step 2: Write the failing tests**

In `tests/test_ita_summary.py`:
- Add `write_release` to the `from ita_fixtures import (...)` list.
- Add `from polars.testing import assert_frame_equal`.
- Append the following:

```python
TABLE_SCHEMA = {
    'year_filing_for': pl.Int64, 'id': pl.Int64, 'establishment_id': pl.Int64,
    'establishment_name': pl.String, 'company_name': pl.String, 'ein': pl.String,
    'street_address': pl.String, 'city': pl.String, 'state': pl.String, 'zip_code': pl.String,
    'naics_code': pl.String, 'naics_year': pl.Int64, 'naics_year_from_dictionary': pl.Boolean,
    'industry_description': pl.String, 'establishment_type': pl.Int64, 'size': pl.Int64,
    'size_class': pl.Int64, 'annual_average_employees': pl.Int64,
    'total_hours_worked': pl.Int64, 'flag_employment': pl.Boolean,
    'flag_hours_per_employee': pl.Boolean, 'flag_below_filing_size': pl.Boolean,
    'source_file': pl.String,
}
NEXT_2025 = 'ITA_300A_Summary_Data_2025_through_11-30-2026.csv'


def table_path(data_directory):
    return data_directory / 'derived/osha' / ita_summary.TABLE_NAME


def test_every_year_stacks_into_one_sorted_table_without_injury_counts(data_directory):
    write_release(data_directory, 2022)
    unsorted = [record(2023, id='5'), record(2023, id='3')]
    write_release(data_directory, 2023, year_file(2023, unsorted))
    write_release(data_directory, 2024)

    table = pl.read_parquet(ita_summary.build_summary_table(data_directory))

    assert table.columns == list(TABLE_SCHEMA)
    assert table.schema == TABLE_SCHEMA
    assert table.select('year_filing_for', 'id').rows() == [
        (2022, 20220), (2023, 3), (2023, 5), (2024, 20240),
    ]
    assert table['source_file'].unique(maintain_order=True).to_list() == [
        f'osha/summary/{year}/{RELEASE_NAMES[year]}' for year in (2022, 2023, 2024)
    ]


def test_each_year_uses_its_latest_release(data_directory):
    write_release(data_directory, 2025)
    newer = [record(2025, id=str(n)) for n in range(3)]
    write_release(data_directory, 2025, year_file(2025, newer), NEXT_2025)

    table = pl.read_parquet(ita_summary.build_summary_table(data_directory))

    assert table.height == 3
    assert table['source_file'].unique().to_list() == [f'osha/summary/2025/{NEXT_2025}']


def test_two_files_in_a_year_without_distinct_through_dates_fail(data_directory):
    write_release(data_directory, 2016)
    write_release(data_directory, 2016, name='ITA Data CY 2016 (1).zip')

    with pytest.raises(ValueError, match='distinct through-date'):
        ita_summary.build_summary_table(data_directory)


def test_hidden_files_and_partial_downloads_beside_a_release_are_ignored(data_directory):
    release = write_release(data_directory, 2016)
    (release.parent / '.DS_Store').write_bytes(b'\x00\x00\x00\x01Bud1')
    (release.parent / 'ITA Data CY 2016.zip.part').write_bytes(b'PK')

    table = pl.read_parquet(ita_summary.build_summary_table(data_directory))

    assert table['source_file'].to_list() == ['osha/summary/2016/ITA Data CY 2016.zip']


def test_an_unrecorded_raw_file_is_not_stacked(data_directory):
    write_release(data_directory, 2024, recorded=False)

    with pytest.raises(KeyError, match='not recorded'):
        ita_summary.build_summary_table(data_directory)

    assert not table_path(data_directory).exists()


def test_the_table_is_rebuilt_on_every_call(data_directory):
    write_release(data_directory, 2025)
    assert pl.read_parquet(ita_summary.build_summary_table(data_directory)).height == 1
    newer = [record(2025, id=str(n)) for n in range(3)]
    write_release(data_directory, 2025, year_file(2025, newer), NEXT_2025)

    assert pl.read_parquet(ita_summary.build_summary_table(data_directory)).height == 3


def test_a_failed_build_keeps_the_previous_table(data_directory):
    write_release(data_directory, 2025)
    table = ita_summary.build_summary_table(data_directory)
    before = table.read_bytes()
    bad = year_file(2025, [record(2025, annual_average_employees='23.50')])
    write_release(data_directory, 2025, bad, NEXT_2025)

    with pytest.raises(InvalidOperationError):
        ita_summary.build_summary_table(data_directory)

    assert table.read_bytes() == before
    assert sorted(path.name for path in table.parent.iterdir()) == [ita_summary.TABLE_NAME]


def test_rebuilding_unchanged_inputs_gives_the_same_table(data_directory):
    for year in (2019, 2022, 2025):
        write_release(data_directory, year)
    first = pl.read_parquet(ita_summary.build_summary_table(data_directory))

    second = pl.read_parquet(ita_summary.build_summary_table(data_directory))

    assert_frame_equal(first, second)


def test_totals_report_sets_rows_beside_published_counts(data_directory):
    write_release(data_directory, 2022)
    two_rows = [record(2023, id='1'), record(2023, id='2')]
    write_release(data_directory, 2023, year_file(2023, two_rows))
    write_release(data_directory, 2024)

    report = ita_summary.totals_report(ita_summary.build_summary_table(data_directory))

    assert report.select('year_filing_for', 'rows', 'published', 'gap').rows() == [
        (2022, 1, None, None),
        (2023, 2, 385_488, -385_486),
        (2024, 1, 390_000, -389_999),
    ]
    assert ita_summary.report_lines(report) == [
        '2022: 1 rows from osha/summary/2022/ITA-data-cy2022.zip; no published count located',
        '2023: 2 rows from osha/summary/2023/ITA_300A_Summary_Data_2023_through_12-31-2024.zip;'
        ' OSHA published exactly 385,488 as of 2024-05-31'
        ' (OSHA 2023 Work-Related Injury and Illness Summary); gap -385,486',
        '2024: 1 rows from osha/summary/2024/ITA_300A_Summary_Data_2024_through_12-31-2025.zip;'
        ' OSHA published over 390,000'
        ' (OSHA 2024 Work-Related Injury and Illness Summary); gap -389,999',
    ]
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_ita_summary.py -v`
Expected: the new tests fail with `AttributeError: module 'embedding_data.ita_summary' has no attribute 'build_summary_table'`. Tasks 3 and 4 tests still pass.

- [ ] **Step 4: Implement**

In `src/embedding_data/ita_summary.py`, extend the imports to:

```python
import tempfile
import zipfile
from contextlib import ExitStack
from dataclasses import asdict, dataclass
from pathlib import Path

import polars as pl

from embedding_data import manifest, paths
from embedding_data.ita_catalog import through_date
from embedding_data.osha_encoding import decode_line
```

add after `HOURS_PER_EMPLOYEE`:

```python
TABLE_NAME = 'ita_300a_summary.parquet'
COLUMNS = [
    'year_filing_for', 'id', 'establishment_id', 'establishment_name', 'company_name', 'ein',
    'street_address', 'city', 'state', 'zip_code', 'naics_code', 'naics_year',
    'naics_year_from_dictionary', 'industry_description', 'establishment_type', 'size',
    'size_class', 'annual_average_employees', 'total_hours_worked', 'flag_employment',
    'flag_hours_per_employee', 'flag_below_filing_size', 'source_file',
]


@dataclass(frozen=True)
class PublishedCount:
    '''An establishment count OSHA itself published for one filing year (spec V10).'''
    year_filing_for: int
    published: int
    qualifier: str
    as_of: str | None
    source: str


PUBLISHED_COUNTS = (
    PublishedCount(
        2023, 385_488, 'exactly', '2024-05-31',
        'OSHA 2023 Work-Related Injury and Illness Summary',
    ),
    PublishedCount(
        2024, 390_000, 'over', None, 'OSHA 2024 Work-Related Injury and Illness Summary',
    ),
)
PUBLISHED_SCHEMA = {
    'year_filing_for': pl.Int64, 'published': pl.Int64, 'qualifier': pl.String,
    'as_of': pl.String, 'source': pl.String,
}
```

and append:

```python
def summary_dir(data_dir: Path) -> Path:
    return paths.raw_dir(data_dir, 'osha') / 'summary'


def latest_release(year_dir: Path) -> Path:
    '''A year's only raw file, or the one whose name carries the latest through-date.

    Hidden files (a Finder .DS_Store) and interrupted .part downloads are not releases.
    '''
    files = sorted(
        path for path in year_dir.iterdir()
        if path.is_file() and not path.name.startswith('.') and not path.name.endswith('.part')
    )
    if len(files) == 1:
        return files[0]
    dates = {through_date(path.name): path for path in files}
    if not files or None in dates or len(dates) < len(files):
        raise ValueError(
            f'{year_dir}: cannot choose one of {[path.name for path in files]}; each file '
            'in a year needs a distinct through-date in its name'
        )
    return dates[max(dates)]


def summary_files(data_dir: Path) -> dict[int, Path]:
    '''The raw file each year's rows come from (raw/osha/summary/<year>/), by year.'''
    root = summary_dir(data_dir)
    year_dirs = (
        sorted(path for path in root.iterdir() if path.is_dir() and path.name.isdigit())
        if root.is_dir() else []
    )
    if not year_dirs:
        raise ValueError(f'{root}: no summary files to stack')
    return {int(year_dir.name): latest_release(year_dir) for year_dir in year_dirs}


def build_summary_table(data_dir: Path) -> Path:
    '''Rebuild the stacked table from each year's latest recorded raw file; return its path.

    Unlike the case-detail Parquet, the table is rebuilt on every call, because a new
    release replaces its year's rows. Each input must be in the manifest, and its manifest
    path becomes source_file. The table is written to a .part file, renamed on success.
    '''
    manifest_path = paths.manifest_path(data_dir)
    derived = paths.derived_dir(data_dir, 'osha')
    derived.mkdir(parents=True, exist_ok=True)
    table = derived / TABLE_NAME
    partial = table.with_name(table.name + '.part')
    with tempfile.TemporaryDirectory(dir=derived) as work:
        frames = []
        for year, raw_file in summary_files(data_dir).items():
            source_file = manifest.entry_for(manifest_path, raw_file).path
            utf8_path = Path(work) / f'{year}.csv'
            frames.append(harmonize_file(raw_file, year, source_file, utf8_path))
        try:
            (
                add_flags(pl.concat(frames))
                .select(COLUMNS)
                .sort('year_filing_for', 'id', maintain_order=True)
                .sink_parquet(partial)
            )
            partial.replace(table)
        finally:
            partial.unlink(missing_ok=True)
    return table


def totals_report(table: Path) -> pl.DataFrame:
    '''Rows and source file per year beside OSHA's published counts; gaps kept, not tuned.'''
    published = pl.LazyFrame(
        [asdict(count) for count in PUBLISHED_COUNTS], schema=PUBLISHED_SCHEMA
    )
    return (
        pl.scan_parquet(table)
        .group_by('year_filing_for')
        .agg(rows=pl.len().cast(pl.Int64), source_file=pl.col('source_file').first())
        .join(published, on='year_filing_for', how='left')
        .with_columns(gap=pl.col('rows') - pl.col('published'))
        .sort('year_filing_for')
        .collect()
    )


def report_lines(report: pl.DataFrame) -> list[str]:
    '''One line per year: rows, source file, and the published count and gap where known.'''
    lines = []
    for row in report.iter_rows(named=True):
        year, rows, source_file = row['year_filing_for'], row['rows'], row['source_file']
        line = f'{year}: {rows:,} rows from {source_file}'
        if row['published'] is None:
            line += '; no published count located'
        else:
            qualifier, published, source, gap, as_of_date = (
                row['qualifier'], row['published'], row['source'], row['gap'], row['as_of']
            )
            as_of = f' as of {as_of_date}' if as_of_date else ''
            line += (
                f'; OSHA published {qualifier} {published:,}{as_of} ({source}); gap {gap:+,}'
            )
        lines.append(line)
    return lines
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_ita_summary.py -v`
Expected: all pass.

Run: `uv run --locked pytest`
Expected: all pass, `1 deselected`.

- [ ] **Step 6: Commit**

```bash
uv run --locked ruff check .
git add src/embedding_data/ita_summary.py tests/ita_fixtures.py tests/test_ita_summary.py
git commit -m "feat(osha): stack each year's latest Form 300A release and report totals

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: The `osha` command acquires summaries and keeps case detail

**Files:**
- Modify: `src/embedding_data/osha_benchmark_download.py` (full replacement below)
- Modify: `tests/test_osha_benchmark_download.py`
- Modify: `tests/test_cli.py`
- Modify: `README.md`, `CLAUDE.md`

**Interfaces:**
- Consumes:
  - `ita_catalog.PAGE_URL`, `parse_catalog`, `check_complete`, `file_name` and `through_date`.
  - `ita_summary.summary_dir`, `build_summary_table`, `totals_report` and `report_lines`.
  - `manifest.describe_file(..., through_date=)`.
- Produces:
  - `uv run embedding-data osha [summary] [case-detail] [--data-dir DIR]`.
  - `osha_benchmark_download.SETS`, `acquire_summary(data_dir)`, `acquire_case_detail(data_dir)` and `record_download(...)`.
  - `osha_benchmark_download.file_name` stays importable, for `raw_backfill`. So do `DICTIONARY_URL`, `CSV_URL`, `make_client`, `download`, `decode_line`, `csv_to_parquet`, `is_recorded`, `refuse_replacement` and `BACKFILL_COMMAND`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_osha_benchmark_download.py`:

1. Extend the imports. Insert `from ita_fixtures import record, year_file` immediately before `from typer.main import get_command`; isort counts it as third-party. Then replace `from embedding_data import manifest, paths` with:

```python
from embedding_data import ita_catalog, ita_summary, manifest, paths
```

2. After `PDF_BYTES`, add:

```python
PAGE_HTML = (Path(__file__).parent / 'fixtures/osha/itadata.html').read_text()
CATALOG = ita_catalog.parse_catalog(PAGE_HTML)
SUMMARY_FILES = {release.url: year_file(release.year) for release in CATALOG.releases}
[CURRENT] = [release for release in CATALOG.releases if release.year == 2025]
CURRENT_NAME = 'ITA_300A_Summary_Data_2025_through_08-31-2026.csv'
NEXT_NAME = 'ITA_300A_Summary_Data_2025_through_11-30-2026.csv'
NEXT_URL = CURRENT.url.replace(CURRENT_NAME, NEXT_NAME)
```

3. Replace the `osha_server` function and the `run_cli` fixture with:

```python
def serve(page=PAGE_HTML, extra=None, requests=None):
    '''Serve the ITA page and every file it lists, refusing non-browser agents as OSHA does.'''
    bodies = {
        osha.CSV_URL: CSV_BYTES,
        osha.DICTIONARY_URL: PDF_BYTES,
        **SUMMARY_FILES,
        **{url: PDF_BYTES for url in CATALOG.dictionaries},
        **(extra or {}),
    }

    def handler(request):
        if requests is not None:
            requests.append(str(request.url))
        if not request.headers['User-Agent'].startswith('Mozilla/5.0'):
            return httpx.Response(403, html='<h1>403 ERROR</h1>')
        if request.url == ita_catalog.PAGE_URL:
            return httpx.Response(200, html=page)
        for url, body in bodies.items():
            if request.url == url:
                return streamed(body)
        return httpx.Response(404)

    return handler


osha_server = serve()
```

```python
@pytest.fixture
def run_cli(cli_app, cli_runner, data_directory):
    def invoke_cli(handler=osha_server, data_dir=None, sets=('case-detail',)):
        client_factory = partial(osha.make_client, transport=httpx.MockTransport(handler))
        arguments = [*sets, '--data-dir', str(data_dir or data_directory)]
        with patch.object(osha, 'make_client', client_factory):
            return cli_runner.invoke(cli_app, arguments)

    return invoke_cli
```

The existing tests keep their assertions. Each now runs `osha case-detail`.

4. Append:

```python
def summary_raw(data_directory):
    return data_directory / 'raw/osha/summary'


def test_summary_downloads_every_listed_year_and_records_its_through_date(
    run_cli, data_directory,
):
    result = run_cli(sets=('summary',))

    assert result.exit_code == 0, result.output
    raw = summary_raw(data_directory)
    for release in CATALOG.releases:
        file = raw / str(release.year) / ita_catalog.file_name(release.url)
        assert file.read_bytes() == SUMMARY_FILES[release.url]
    assert sorted(path.name for path in raw.iterdir() if path.is_file()) == [
        'ITA_Data_Dictionary.pdf', 'summary_data_dictionary.pdf',
    ]
    entries = {
        entry.path: entry.through_date
        for entry in manifest.read_manifest(paths.manifest_path(data_directory))
    }
    assert len(entries) == 12
    assert entries[f'osha/summary/2025/{CURRENT_NAME}'] == '2026-08-31'
    assert entries['osha/summary/2023/ITA_300A_Summary_Data_2023_through_12-31-2024.zip'] == (
        '2024-12-31'
    )
    assert entries['osha/summary/2016/ITA Data CY 2016.zip'] is None
    assert entries['osha/summary/summary_data_dictionary.pdf'] is None
    assert not (data_directory / 'raw/osha' / CSV_NAME).exists()


def test_summary_rebuilds_the_table_and_prints_totals(run_cli, data_directory):
    result = run_cli(sets=('summary',))

    assert result.exit_code == 0, result.output
    table = pl.read_parquet(data_directory / 'derived/osha' / ita_summary.TABLE_NAME)
    assert table['year_filing_for'].to_list() == list(range(2016, 2026))
    assert (
        '2023: 1 rows from osha/summary/2023/ITA_300A_Summary_Data_2023_through_12-31-2024.zip;'
        ' OSHA published exactly 385,488 as of 2024-05-31'
    ) in result.stdout
    assert (
        '2016: 1 rows from osha/summary/2016/ITA Data CY 2016.zip; no published count located'
    ) in result.stdout


def test_a_new_current_year_release_is_recorded_beside_the_earlier_one(
    run_cli, data_directory,
):
    first = run_cli(sets=('summary',))
    assert first.exit_code == 0, first.output
    manifest_path = paths.manifest_path(data_directory)
    before = manifest_path.read_bytes()
    earlier = summary_raw(data_directory) / '2025' / CURRENT_NAME
    newer = year_file(2025, [record(2025, id=str(n)) for n in range(3)])
    requests = []
    handler = serve(
        page=PAGE_HTML.replace(CURRENT_NAME, NEXT_NAME), extra={NEXT_URL: newer},
        requests=requests,
    )

    second = run_cli(handler, sets=('summary',))

    assert second.exit_code == 0, second.output
    assert requests == [ita_catalog.PAGE_URL, NEXT_URL]
    assert earlier.read_bytes() == SUMMARY_FILES[CURRENT.url]
    assert manifest_path.read_bytes().startswith(before)
    [added] = manifest.read_manifest(manifest_path)[12:]
    assert (added.path, added.through_date) == (f'osha/summary/2025/{NEXT_NAME}', '2026-11-30')
    table = pl.read_parquet(data_directory / 'derived/osha' / ita_summary.TABLE_NAME)
    rows_2025 = table.filter(pl.col('year_filing_for') == 2025)
    assert rows_2025.height == 3
    assert rows_2025['source_file'].unique().to_list() == [f'osha/summary/2025/{NEXT_NAME}']


def test_a_second_summary_run_requests_only_the_page(run_cli, data_directory):
    assert run_cli(sets=('summary',)).exit_code == 0
    requests = []

    result = run_cli(serve(requests=requests), sets=('summary',))

    assert result.exit_code == 0, result.output
    assert requests == [ita_catalog.PAGE_URL]
    assert 'exists, keeping it as delivered' in result.stdout


def test_a_missing_recorded_summary_file_is_refused_before_any_download(
    run_cli, data_directory,
):
    assert run_cli(sets=('summary',)).exit_code == 0
    (summary_raw(data_directory) / '2019/ITA Data CY 2019.zip').unlink()
    requests = []

    result = run_cli(serve(requests=requests), sets=('summary',))

    assert result.exit_code == 1, result.output
    assert 'will not re-download' in result.stderr
    assert requests == [ita_catalog.PAGE_URL]


def test_an_unrecorded_summary_file_is_refused_before_any_download(run_cli, data_directory):
    stray = summary_raw(data_directory) / '2016/ITA Data CY 2016.zip'
    stray.parent.mkdir(parents=True)
    stray.write_bytes(year_file(2016))
    requests = []

    result = run_cli(serve(requests=requests), sets=('summary',))

    assert result.exit_code == 1, result.output
    assert 'not recorded' in result.stderr
    assert requests == [ita_catalog.PAGE_URL]
    assert manifest.read_manifest(paths.manifest_path(data_directory)) == []


def test_a_page_that_skips_a_year_is_refused(run_cli, data_directory):
    page = '\n'.join(line for line in PAGE_HTML.splitlines() if '2019 Summary Data' not in line)

    result = run_cli(serve(page=page), sets=('summary',))

    assert result.exit_code == 1, result.output
    assert 'no summary file listed for 2019' in result.stderr
    assert not summary_raw(data_directory).exists()


def test_with_no_set_named_both_are_acquired(run_cli, data_directory):
    result = run_cli(sets=())

    assert result.exit_code == 0, result.output
    assert (data_directory / 'raw/osha' / CSV_NAME).exists()
    assert (data_directory / 'derived/osha' / ita_summary.TABLE_NAME).exists()


def test_an_unknown_set_is_rejected(run_cli):
    result = run_cli(no_requests, sets=('bogus',))

    assert result.exit_code == 2
    assert 'unknown set(s): bogus' in result.output
```

In `tests/test_cli.py`, replace `test_osha_help_describes_case_detail_download` with:

```python
def test_osha_help_describes_summaries_and_case_detail(cli_runner):
    result = cli_runner.invoke(cli.app, ['osha', '--help'])

    assert result.exit_code == 0, result.output
    assert 'OSHA ITA Form 300A summaries and case-detail' in result.output
    assert 'summary and/or case-detail' in result.output
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_osha_benchmark_download.py tests/test_cli.py -v`
Expected: the new summary tests fail, because `osha` takes no `summary` argument (exit code 2). The CLI help test fails. The existing case-detail tests also fail, because `case-detail` is an unexpected extra argument.

- [ ] **Step 3: Replace the command module**

Replace `src/embedding_data/osha_benchmark_download.py` with:

```python
'''Download OSHA ITA Form 300A summaries and case-detail data, and build their Parquet tables.

Usage:
    uv run embedding-data osha
    uv run embedding-data osha summary
    uv run embedding-data osha case-detail --data-dir /tmp/osha-data

summary: every Form 300A summary file the ITA data page (https://www.osha.gov/itadata)
    lists, 2016 through the current year, and the summary data dictionaries. A year's file
    goes to data/raw/osha/summary/<year>/ under the name OSHA gives it. The current year's
    name carries its submission through-date, so a later release arrives beside the
    earlier one and is recorded as a new manifest entry with its through-date. A summary
    file found on disk but not in the manifest stops the run, because nothing can record
    it after the fact; a file OSHA replaces under an unchanged name is not detected. Then
    data/derived/osha/ita_300a_summary.parquet is rebuilt from each year's latest release
    (embedding_data.ita_summary), and rows per year are printed beside OSHA's published
    submission counts.
case-detail: the 2025 case-detail CSV and its dictionary, one row per injury or illness
    (Forms 300 and 301), acquired but feeding no target. An existing case-detail file
    missing from the manifest draws a warning naming the backfill command. The CSV is
    converted to data/derived/osha only when that Parquet is absent; delete it to rebuild.

Raw files go to data/raw/osha, and each download is recorded in data/raw/manifest.jsonl
with its URL, retrieval time, SHA-256, and httpx version. A file that already exists there
is kept as delivered and not downloaded again, and one that is absent but still recorded
fails the run before any download, so the original is restored rather than replaced.
--data-dir moves the whole data root.

The CSVs mix encodings: most non-ASCII text is Windows-1252, a few rows are UTF-8
(embedding_data.osha_encoding). The case-detail CSV is transcoded to a temporary UTF-8 copy
beside the Parquet and sunk to Parquet. Code columns stay strings even where the data
dictionary calls them numeric (zip_code has already lost its leading zeros upstream;
SOC_code reads 00-9900 when unassigned); counts become Int64, dates and times become Date
and Time, and a value that does not parse fails the conversion.
'''

import shlex
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import httpx
import polars as pl
import polars.selectors as cs
import typer

from embedding_data import ita_catalog, ita_summary, manifest, paths
from embedding_data.ita_catalog import file_name
from embedding_data.osha_encoding import decode_line

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


SETS = ('summary', 'case-detail')
CSV_URL = (
    'https://www.osha.gov/sites/default/largefiles/'
    'ITA_Case_Detail_Data_2025_through_08-31-2026.csv'
)
DICTIONARY_URL = 'https://www.osha.gov/sites/default/files/case_detail_data_dictionary_2026.pdf'

# osha.gov's CloudFront distribution answers 403 to httpx's default and to descriptive
# user agents, and 200 to a browser one (checked 2026-10-12, over HTTP/2 and HTTP/1.1).
USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
)
TIMEOUT = httpx.Timeout(60.0, connect=15.0)
CHUNK_SIZE = 1024 * 1024
BACKFILL_COMMAND = 'uv run --locked python -m embedding_data.raw_backfill'

INTEGER_COLUMNS = [
    'ID', 'establishment_ID', 'naics_year', 'establishment_type', 'Size',
    'annual_average_employees', 'total_hours_worked', 'incident_outcome',
    'dafw_num_away', 'djtr_num_tr', 'type_of_incident', 'time_unknown', 'year_of_filing',
]
FLOAT_COLUMNS = ['SOC_probability']
DATE_COLUMNS = ['date_of_incident', 'date_of_death', 'date_submitted']
TIME_COLUMNS = ['time_started_work', 'time_of_incident']


def make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    '''HTTP/2 client that osha.gov will serve.'''
    return httpx.Client(
        http2=True,
        follow_redirects=True,
        headers={'User-Agent': USER_AGENT},
        timeout=TIMEOUT,
        transport=transport,
    )


def is_recorded(manifest_path: Path, raw_file: Path) -> bool:
    '''Whether the manifest has an entry for raw_file.'''
    path = raw_file.relative_to(manifest_path.parent).as_posix()
    return any(entry.path == path for entry in manifest.read_manifest(manifest_path))


def refuse_replacement(manifest_path: Path, raw_file: Path) -> None:
    '''Exit before any download: a replacement could differ from the recorded hash.'''
    recorded = manifest.entry_for(manifest_path, raw_file)
    typer.echo(
        f'{raw_file.name}: error: the raw file is missing but recorded in {manifest_path} '
        f'with SHA-256 {recorded.sha256[:12]}...; restore the original file (its hash must '
        'match) rather than downloading a replacement. This command will not re-download '
        'over an existing record.',
        err=True,
    )
    raise typer.Exit(code=1)


def refuse_unrecorded(manifest_path: Path, raw_file: Path) -> None:
    '''Exit before any download: an unrecorded summary file on disk has no provenance.'''
    typer.echo(
        f'{raw_file.name}: error: the file exists but is not recorded in {manifest_path}, so '
        'its provenance is unknown; move it aside so this command downloads and records it.',
        err=True,
    )
    raise typer.Exit(code=1)


def download(client: httpx.Client, url: str, destination: Path) -> None:
    '''Stream url to a .part file and rename it only once the body is complete.'''
    partial = destination.with_name(destination.name + '.part')
    try:
        with client.stream('GET', url) as response:
            response.raise_for_status()
            with partial.open('wb') as file:
                for chunk in response.iter_bytes(CHUNK_SIZE):
                    file.write(chunk)
        expected = response.headers.get('Content-Length')
        if expected is not None and response.num_bytes_downloaded != int(expected):
            raise httpx.RemoteProtocolError(
                f'{url}: received {response.num_bytes_downloaded:,} of {int(expected):,} bytes',
                request=response.request,
            )
        partial.replace(destination)
    finally:
        partial.unlink(missing_ok=True)
    size = destination.stat().st_size
    typer.echo(f'wrote {destination} ({response.http_version}, {size:,} bytes)')


def record_download(manifest_path: Path, destination: Path, url: str, **provenance) -> None:
    '''Hash a finished download and append its manifest entry.'''
    entry = manifest.describe_file(
        destination,
        manifest_path.parent,
        retrieved_at=datetime.now(UTC),
        client='httpx',
        client_version=version('httpx'),
        source_url=url,
        **provenance,
    )
    manifest.append_entries(manifest_path, [entry])


def csv_to_parquet(csv_path: Path, parquet_path: Path) -> Path:
    '''Transcode the raw CSV to a temporary UTF-8 copy beside parquet_path; sink typed Parquet.'''
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    utf8_path = parquet_path.with_suffix('.utf8.csv')
    partial = parquet_path.with_name(parquet_path.name + '.part')
    try:
        # Splitting on b'\n' is safe for both encodings: neither uses 0x0A inside a character.
        with csv_path.open('rb') as src, utf8_path.open('w', encoding='utf-8', newline='') as dst:
            dst.writelines(decode_line(line) for line in src)

        lf = pl.scan_csv(utf8_path, infer_schema=False).with_columns(
            cs.by_name(INTEGER_COLUMNS, require_all=False).cast(pl.Int64),
            cs.by_name(FLOAT_COLUMNS, require_all=False).cast(pl.Float64),
            cs.by_name(DATE_COLUMNS, require_all=False).str.to_date('%m/%d/%Y'),
            cs.by_name(TIME_COLUMNS, require_all=False).str.to_time('%H:%M'),
        )
        lf.sink_parquet(partial)
        partial.replace(parquet_path)
    finally:
        utf8_path.unlink(missing_ok=True)
        partial.unlink(missing_ok=True)
    return parquet_path


def acquire_summary(data_dir: Path) -> None:
    '''Download each listed summary file not yet on disk, then rebuild the stacked table.'''
    raw = ita_summary.summary_dir(data_dir)
    manifest_path = paths.manifest_path(data_dir)
    with make_client() as client:
        page = client.get(ita_catalog.PAGE_URL)
        page.raise_for_status()
        try:
            catalog = ita_catalog.parse_catalog(page.text, str(page.url))
            ita_catalog.check_complete(catalog)
        except ValueError as error:
            typer.echo(f'{ita_catalog.PAGE_URL}: error: {error}', err=True)
            raise typer.Exit(code=1) from None
        destinations = {
            release.url: raw / str(release.year) / file_name(release.url)
            for release in catalog.releases
        }
        destinations |= {url: raw / file_name(url) for url in catalog.dictionaries}
        for destination in destinations.values():
            recorded = is_recorded(manifest_path, destination)
            if not destination.exists() and recorded:
                refuse_replacement(manifest_path, destination)
            if destination.exists() and not recorded:
                refuse_unrecorded(manifest_path, destination)
        for url, destination in destinations.items():
            if destination.exists():
                typer.echo(f'{destination.name}: exists, keeping it as delivered')
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            download(client, url, destination)
            record_download(
                manifest_path, destination, url,
                through_date=ita_catalog.through_date(destination.name),
            )
    table = ita_summary.build_summary_table(data_dir)
    typer.echo(f'wrote {table}')
    for line in ita_summary.report_lines(ita_summary.totals_report(table)):
        typer.echo(line)


def acquire_case_detail(data_dir: Path) -> None:
    '''Download the case-detail CSV and dictionary if absent; convert the CSV once.'''
    raw = paths.raw_dir(data_dir, 'osha')
    raw.mkdir(parents=True, exist_ok=True)
    manifest_path = paths.manifest_path(data_dir)
    destinations = {url: raw / file_name(url) for url in (DICTIONARY_URL, CSV_URL)}
    for destination in destinations.values():
        if not destination.exists() and is_recorded(manifest_path, destination):
            refuse_replacement(manifest_path, destination)
    with make_client() as client:
        for url, destination in destinations.items():
            if destination.exists():
                typer.echo(f'{destination.name}: exists, keeping it as delivered')
                if not is_recorded(manifest_path, destination):
                    typer.echo(
                        f'{destination.name}: warning: not recorded in {manifest_path}; to '
                        f'record it, run {BACKFILL_COMMAND} '
                        f'--data-dir {shlex.quote(str(data_dir))}',
                        err=True,
                    )
                continue
            download(client, url, destination)
            record_download(manifest_path, destination, url)

    csv_path = raw / file_name(CSV_URL)
    parquet_path = paths.derived_dir(data_dir, 'osha') / csv_path.with_suffix('.parquet').name
    if parquet_path.exists():
        typer.echo(f'{parquet_path.name}: exists, not converting again')
        return
    typer.echo(f'wrote {csv_to_parquet(csv_path, parquet_path)}')


@app.command(help=__doc__.splitlines()[0])
def main(
    sets: Annotated[
        list[str] | None,
        typer.Argument(help='summary and/or case-detail (default: both)'),
    ] = None,
    data_dir: Annotated[
        Path,
        typer.Option('--data-dir', help='Data root holding raw/ and derived/.'),
    ] = paths.DATA_DIR,
) -> None:
    sets = sets or list(SETS)
    unknown = sorted(set(sets).difference(SETS))
    if unknown:
        raise typer.BadParameter('unknown set(s): ' + ', '.join(unknown), param_hint='sets')
    if 'summary' in sets:
        acquire_summary(data_dir)
    if 'case-detail' in sets:
        acquire_case_detail(data_dir)


if __name__ == '__main__':
    app()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_osha_benchmark_download.py tests/test_cli.py tests/test_raw_backfill.py -v`
Expected: all pass.

Run: `uv run --locked pytest`
Expected: all pass, `1 deselected`.

Run: `uv run embedding-data osha --help`
Expected: the help's first line reads "Download OSHA ITA Form 300A summaries and case-detail data, and build their Parquet tables.", and the argument help reads `summary and/or case-detail (default: both)`. This makes no network request.

- [ ] **Step 5: Update `README.md`**

1. In `## Current state`, replace these two sentences:

~~~text
The `osha` command downloads the
OSHA ITA case-detail CSV and its data dictionary and converts the CSV to Parquet.
~~~

with:

~~~text
The `osha` command acquires
every OSHA ITA Form 300A summary file from 2016 on and stacks them into one
establishment-year table, and downloads the case-detail CSV and its dictionary.
~~~

Then replace

~~~text
OSHA Form 300A ingestion, classification concordances, geography allocation,
~~~

with

~~~text
Classification concordances, geography allocation,
~~~

and replace

~~~text
The OSHA case-detail files under `data/raw/osha/` are a different input from the
Form 300A summaries required by the specification.
~~~

with

~~~text
The OSHA case-detail files are acquired but feed no target; the specification's
establishment data are the Form 300A summaries.
~~~

2. In `## Data sources`, change the ITA row's `2016–2025, planned` to `2016–2025`.

3. Insert this section immediately before `## OSHA case-detail download`:

~~~markdown
## OSHA Form 300A summaries

`uv run embedding-data osha summary` reads the [ITA data page](https://www.osha.gov/itadata)
and downloads every file it lists as `<year> Summary Data` from 2016 on, plus the two
summary data dictionaries, over HTTP/2:

| Path | Contents |
| --- | --- |
| `raw/osha/summary/<year>/<OSHA's file name>` | That year's summary file as delivered: a zip holding one CSV through 2024, a CSV for the current year |
| `raw/osha/summary/summary_data_dictionary.pdf`, `ITA_Data_Dictionary.pdf` | OSHA's field definitions (2024 on; 2016–2023) |
| `derived/osha/ita_300a_summary.parquet` | One row per establishment-year, all years stacked |

The current year's file name carries its submission through-date
(`..._2025_through_08-31-2026.csv`). OSHA renames the file as it grows, so a later
release is downloaded beside the earlier one and recorded as a new manifest entry with
its `through_date`; the earlier file and entry are untouched. The run refuses a page
that skips a year or whose current file names no through-date, and a summary file
found on disk but missing from the manifest. A file OSHA replaces under an unchanged
name is not detected.

The table is rebuilt on every run from each year's latest release. It keeps the
specification's R2.4 columns plus OSHA's record `id`, the raw file it came from
(`source_file`, the manifest path), and these harmonized columns:

- `size_class`: OSHA split size code `2` (20–249 employees) into `21` and `22` with the
  2023 data, but later files still use `2` for some establishments. `size` keeps the
  native code; `size_class` merges `21` and `22` back into `2`.
- `naics_year`: files before 2023 lack it; OSHA's dictionary says those years use 2012
  NAICS, so they get 2012 with `naics_year_from_dictionary` set.
- `flag_employment`, `flag_hours_per_employee` (outside 500–4,000 hours per average
  employee), and `flag_below_filing_size` (under 20 employees). Flagged rows are kept.

Codes, names, addresses, ZIP codes, and EINs stay as delivered. A file the
harmonization does not cover stops the build rather than being guessed at. After the
build the command prints rows per year beside OSHA's published submission counts. A
full first run downloads about 258 MB.
~~~

4. In `## OSHA case-detail download`, change the first sentence's `The \`osha\` command needs no account or key. It downloads two files` to `` `uv run embedding-data osha case-detail` needs no account or key. It downloads two files ``. Replace the code block

~~~text
uv run embedding-data osha
uv run embedding-data osha --data-dir /tmp/osha-data
~~~

with

~~~text
uv run embedding-data osha case-detail
uv run embedding-data osha case-detail --data-dir /tmp/osha-data
~~~

and replace

~~~text
These are case-detail records from Forms 300 and 301, not the Form 300A
establishment summaries required by the specification.
~~~

with

~~~text
These are case-detail records from Forms 300 and 301; they feed no target.
~~~

5. In `## Files and planned outputs`, change the `raw/osha/` row's contents to `OSHA downloads as delivered; summaries under \`raw/osha/summary/<year>/\``.

6. In `## Project layout`, replace the `osha_benchmark_download.py` line with these four lines, padded to the same column:

~~~text
src/embedding_data/osha_benchmark_download.py The osha command: Form 300A and case-detail downloads
src/embedding_data/ita_catalog.py            Form 300A releases listed on the ITA data page
src/embedding_data/ita_summary.py            Stacked, harmonized, flagged Form 300A table
src/embedding_data/osha_encoding.py          Mixed UTF-8 / Windows-1252 line decoding
~~~

- [ ] **Step 6: Update `CLAUDE.md`**

1. In `## What this repo is`, replace

~~~text
Only the IPUMS extract scripts (define → submit → download → CSV-to-Parquet) and an OSHA case-detail download (download → CSV-to-Parquet) exist so far; every raw file is recorded in an append-only manifest (`data/raw/manifest.jsonl`); OSHA Form 300A ingestion, code parsing, geography allocation, targets, and output manifests are planned, not built.
~~~

with

~~~text
So far the IPUMS extract scripts (define → submit → download → CSV-to-Parquet), the OSHA Form 300A summary acquisition with its stacked establishment-year table, and an OSHA case-detail download (download → CSV-to-Parquet) exist; every raw file is recorded in an append-only manifest (`data/raw/manifest.jsonl`); code parsing, geography allocation, targets, and output manifests are planned, not built.
~~~

2. In `## Commands`, add this line to the bash block after the `behave -n` line:

```bash
uv run --locked pytest -m network   # live osha.gov page canary; deselected by default
```

and change the **Expected baseline** sentence to: `**Expected baseline:** the full pytest suite (the one \`network\` canary deselected) and every Behave scenario pass; any failure is a regression.`

3. Replace the whole `**OSHA download.**` paragraph with:

~~~text
**OSHA download.** `osha` needs no key and takes sets like the IPUMS commands: `summary`, `case-detail`, or both by default. osha.gov's CloudFront returns 403 to non-browser user agents, so `USER_AGENT` is a browser string. `summary` reads the ITA data page (`ita_catalog`) for every `<year> Summary Data` link from 2016 on and refuses a page that skips a year or whose current file names no through-date. Each file goes to `raw/osha/summary/<year>/` under OSHA's name; the current year's name carries its through-date, so a later release lands beside the earlier one as a new manifest entry with `through_date`. A summary file on disk but unrecorded stops the run, because `raw_backfill` records only the case-detail files. `ita_summary.build_summary_table` then rebuilds `derived/osha/ita_300a_summary.parquet` on every run (never convert-once) from each year's latest-through-date file, harmonizing size (`size_class` merges 21/22 into 2; 2 is never split), `naics_year` (2012 from the dictionary before 2023, marked), and the R2.9 flags; structure it cannot harmonize fails the build, and an unrecorded input fails it too. For both sets, existing files in `data/raw/osha` are never re-downloaded (raw immutability), and a file absent but still recorded makes the run exit 1 before any download, naming the start of the recorded SHA-256. `case-detail` warns about an unrecorded existing file (its suggested `--data-dir` shell-quoted) and converts its CSV only when that Parquet is absent. Downloads go to `.part`, are renamed only after `num_bytes_downloaded` matches `Content-Length`, and are then recorded. The CSVs mix Windows-1252 and UTF-8 bytes, sometimes within one line; `osha_encoding.decode_line` transcodes them to temporary UTF-8 CSVs that are cast strictly (codes stay strings). A first summary run downloads about 258 MB, a case-detail run about 475 MB.
~~~

4. In `**CPS sample IDs come from the live IPUMS catalog…**`, replace `Apart from \`--help\`, do not run CPS commands, or ACS without \`--dry-run\`, unless the user asks — they call the IPUMS API with the real key.` with `Apart from \`--help\`, do not run CPS commands, ACS without \`--dry-run\`, or \`osha\` unless the user asks — the IPUMS commands call the API with the real key, and \`osha\` downloads up to about 730 MB from osha.gov into the real data tree.`

5. In `**Test seams.**`, after the sentence ending `leaves \`num_bytes_downloaded\` at 0.`, insert: `OSHA summary tests serve the recorded ITA page \`tests/fixtures/osha/itadata.html\` and bodies from \`tests/ita_fixtures.year_file\`, one per published file format; \`write_release\` places and records a raw summary file.`

- [ ] **Step 7: Commit**

```bash
uv run --locked ruff check .
git add src/embedding_data/osha_benchmark_download.py tests/test_osha_benchmark_download.py tests/test_cli.py README.md CLAUDE.md
git commit -m "feat(osha): acquire Form 300A summaries as the osha summary set

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Live acquisition and the V10 finding (owner gate)

**Files:**
- Create: `specs/findings/v10-ita-300a-totals.md`
- Writes (gitignored): `data/raw/osha/summary/**`, `data/raw/manifest.jsonl`, `data/derived/osha/ita_300a_summary.parquet`

**Interfaces:**
- Consumes: the `osha summary` command (Task 6) and `ita_summary.TABLE_NAME`.
- Produces: the real stacked table and a committed finding that Stages 3, 4 and 6 read.

The raw files this task downloads are immutable and recorded for good, so they must land in the main checkout's data tree, `/Users/lowell/Projects/embedding-data/data`, and never in a worktree's empty `data/`. Every command below names that root explicitly, as `REAL_DATA`, set again in each step because shell state does not carry over between commands. Run the commands from the checkout that holds Tasks 1–6 (the worktree, if one is in use).

- [ ] **Step 1: Ask for the go-ahead**

Stop and ask your human partner, word for word:

> Ready to run `uv run embedding-data osha summary --data-dir /Users/lowell/Projects/embedding-data/data`. It requests https://www.osha.gov/itadata and downloads about 258 MB into `/Users/lowell/Projects/embedding-data/data/raw/osha/summary/`: the 2016–2024 summary zips, the 2025 CSV and two dictionary PDFs. It appends their 12 entries to that tree's `raw/manifest.jsonl` and writes `derived/osha/ita_300a_summary.parquet`. Go ahead?

Wait for a clear yes.

- [ ] **Step 2: Record the starting state**

Run: `git status --short`
Expected: clean.

Run: `uv run --locked python -c "from pathlib import Path; from embedding_data import manifest, paths; print(len(manifest.read_manifest(paths.manifest_path(Path('/Users/lowell/Projects/embedding-data/data')))))"`
Expected: `17`. A `0` means the path is wrong: stop.

- [ ] **Step 3: Run the acquisition**

Run: `REAL_DATA=/Users/lowell/Projects/embedding-data/data; uv run embedding-data osha summary --data-dir "$REAL_DATA"`
Expected:
- 12 `wrote …` download lines;
- `wrote …/data/derived/osha/ita_300a_summary.parquet`;
- one totals line per year from 2016 to 2025 (more years if OSHA has posted one).

**If the build fails on structure** (a `ValueError` from `check_summary`, a missing column, a zip member count, or `InvalidOperationError` from a non-zero fraction), stop. Keep the downloaded files: they are recorded and immutable. Report the exact error to your human partner and change no code until they decide. The fixtures were built from the first ~900 rows of each file, so this is the place a full file can still surprise.

- [ ] **Step 4: Verify the manifest and the exit criteria**

Run:

```bash
uv run --locked python - <<'EOF'
from pathlib import Path
from embedding_data import manifest, paths
REAL_DATA = Path('/Users/lowell/Projects/embedding-data/data')
entries = manifest.read_manifest(paths.manifest_path(REAL_DATA))
summary = [e for e in entries if e.path.startswith('osha/summary/')]
print(len(entries), 'entries;', len(summary), 'summary')
for e in summary:
    print(e.path, e.sha256[:12], e.size, e.through_date)
EOF
```

Expected:
- `29 entries; 12 summary`.
- One file per year 2016–2025, each with a SHA-256.
- The 2025 file's `through_date` is `2026-08-31`, or a later date if OSHA has posted a new release. Record which.

Run the measurement script, keeping its whole output for the finding:

```bash
uv run --locked python - <<'EOF'
from pathlib import Path
import polars as pl
from embedding_data import ita_summary, paths
REAL_DATA = Path('/Users/lowell/Projects/embedding-data/data')
pl.Config(tbl_rows=-1, tbl_cols=-1, tbl_width_chars=250)
table = pl.scan_parquet(paths.derived_dir(REAL_DATA, 'osha') / ita_summary.TABLE_NAME)
print(table.select(pl.col('size_class').unique().sort()).collect())
print(table.group_by('year_filing_for').agg(
    rows=pl.len(),
    size_2=(pl.col('size') == 2).sum(),
    size_21=(pl.col('size') == 21).sum(),
    size_22=(pl.col('size') == 22).sum(),
    naics_2012=(pl.col('naics_year') == 2012).sum(),
    naics_2017=(pl.col('naics_year') == 2017).sum(),
    naics_2022=(pl.col('naics_year') == 2022).sum(),
    naics_missing=pl.col('naics_code').is_null().sum(),
    ein_missing=pl.col('ein').is_null().sum(),
    establishment_id_missing=pl.col('establishment_id').is_null().sum(),
    duplicate_ids=pl.col('id').is_duplicated().sum(),
    repeated_establishment_ids=pl.col('establishment_id').drop_nulls().is_duplicated().sum(),
    flag_employment=pl.col('flag_employment').sum(),
    flag_hours_per_employee=pl.col('flag_hours_per_employee').sum(),
    flag_below_filing_size=pl.col('flag_below_filing_size').sum(),
).sort('year_filing_for').collect())
EOF
```

Expected: the first frame lists only `1`, `2` and `3`, plus `null` if any size is missing. That shows `2` never sits beside `21`/`22` after harmonization. The second frame has one row per year.

- [ ] **Step 5: Write the finding**

Create `specs/findings/v10-ita-300a-totals.md`, filling every value from the Step 3 and Step 4 outputs:

```markdown
# V10 (ITA): Form 300A rows per year against OSHA's published counts

Measured <run date> with `uv run embedding-data osha summary` (plan 2, Task 7), from the
files the ITA data page listed that day. Gaps are recorded, not tuned away (spec V10).

## Raw files

<One line per year: manifest path, SHA-256 prefix, size, through-date. Note the 2025
through-date and whether OSHA had posted a release newer than 2026-08-31.>

## Rows per year

<The command's totals lines, verbatim.>

## Published counts

- 2023: exactly 385,488 establishments as of 2024-05-31 (OSHA 2023 Work-Related Injury
  and Illness Summary). The 2023 file runs through 2024-12-31 and was re-posted on
  2026-05-20 with a `_v2` member, so more rows than the count is expected.
- 2024: "over 390,000" (OSHA 2024 Work-Related Injury and Illness Summary), with no as-of
  date. The file runs through 2025-12-31.
- OSHA's "Comparison Between OSHA ITA Data and BLS SOII Estimates" says "In 2024, OSHA
  collected summary data from over 370,000 establishments" without naming the data year;
  it is listed here and not used as a comparison.
- J.J. Keller reported "more than 300,000" establishments for 2022. That is not an OSHA
  publication and is not used.
- No OSHA-published count was located for 2016–2022 or for 2025.

## Observed in the stacked table

<The measurement frame from Step 4, then one sentence each on:
- the size-code mix: code 2 beside 21/22 from 2023;
- the `naics_year` mix from 2023;
- `ein` missing shares by year, especially 2016–2018;
- `establishment_id` coverage, with repeated IDs within a year;
- duplicate record `id`s;
- flag counts.>

## Consequences for later stages

<One bullet each, stating only what the numbers show:
- Stage 3 (V2 `establishment_id` persistence; the pre-2023 link on `ein`);
- Stage 4 (`naics_year` mix; the deferred industry half of the filing-rule flag);
- Stage 10 (`ein`-based dedup and co-ownership).>
```

- [ ] **Step 6: Commit the finding**

```bash
git add specs/findings/v10-ita-300a-totals.md
git commit -m "docs(specs): record the V10 ITA totals finding

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Spec amendments and final verification

**Files:**
- Modify: `specs/embedding-evaluation-data-spec.md`

**Interfaces:**
- Consumes: the Task 7 finding, which confirms the facts that A2 states.
- Produces: the amended spec.

The wording below was approved at plan review (D6). Before editing, check that the Task 7 output still supports A2. That means `establishment_id` is present in every year, code `2` appears beside `21`/`22` from 2023, and there is no `naics_year` column before 2023. If any of these fails, stop and ask; don't edit A2's wording on your own. The status line stays untouched.

- [ ] **Step 1: Amendment A1 (R2.1, case detail; D1)**

Replace:

```text
**R2.1** Acquire every Form 300A summary file from 2016 through the current year
from the ITA data page. The current-year file grows while submissions continue —
the 2025 file covers submissions through 2026-08-31 — so record its through-date
and re-acquire until OSHA moves it to the historical list. *(verified; ITA)*
```

with:

```text
**R2.1** Acquire every Form 300A summary file from 2016 through the current year
from the ITA data page. The current-year file grows while submissions continue —
the 2025 file covers submissions through 2026-08-31 — so record its through-date
and re-acquire until OSHA moves it to the historical list. *(verified; ITA)* The
2025 case-detail file (Forms 300 and 301) is also acquired and converted; it feeds
no target. *(owner, plan 2, 2026-10-12)*
```

- [ ] **Step 2: Amendment A2 (R2.3, the delivered files)**

Replace:

```text
**R2.3** Stack all years into one establishment-year table keyed on
`year_filing_for`, harmonizing three dictionary changes introduced with the 2023
data: `establishment_id`, added to link summary and case-detail files; the split
of size code `2` into `21` and `22`; and NAICS codes that may be 2012, 2017, or
2022 vintage, identified by `naics_year`. *(verified; ITA)*
```

with:

```text
**R2.3** Stack all years into one establishment-year table keyed on
`year_filing_for`, harmonizing three dictionary changes introduced with the 2023
data: `establishment_id`, documented from then on as the link between summary and
case-detail files; the split of size code `2` into `21` and `22`; and NAICS codes
that may be 2012, 2017, or 2022 vintage, identified by `naics_year`. *(verified;
ITA)* The delivered files differ from that account. `establishment_id` is present
in every year from 2016; the 2016–2023 dictionary defines it per user account, and
OSHA assigns a new one when a profile is re-created. The 2023 and later files still
carry code `2` for some establishments, so a harmonized size class merges `21` and
`22` into `2` beside the native code, and `2` is never split. Files before 2023
carry no `naics_year`; the dictionary states that data through 2022 use 2012 NAICS,
so those rows take 2012, marked as supplied by the dictionary. *(owner, plan 2,
2026-10-12)*
```

- [ ] **Step 3: Amendment A3 (R9.1, the `osha` command)**

Replace:

```text
expressions. Each extract runs as a command of the package's console entry point
(`uv run embedding-data acs`, `uv run embedding-data cps`), with dependencies
declared in `pyproject.toml`. *(implemented; XA, XC)*
```

with:

```text
expressions. Each extract runs as a command of the package's console entry point
(`uv run embedding-data acs`, `uv run embedding-data cps`), with dependencies
declared in `pyproject.toml`. *(implemented; XA, XC)* ITA acquisition runs the same
way, as `uv run embedding-data osha`. *(owner, plan 2, 2026-10-12)*
```

- [ ] **Step 4: Final verification**

Run each command and confirm the output:

```bash
uv run --locked pytest
uv run --locked behave
uv run --locked ruff check .
uv lock --check
uv run --locked pre-commit run --all-files
```

Expected:
- pytest: all pass, `1 deselected`, and more than the 96-test baseline.
- Behave: 2 scenarios passed.
- ruff: `All checks passed!`.
- `uv lock --check`: the lockfile is up to date.
- pre-commit: every hook passes.

- [ ] **Step 5: Commit**

```bash
git add specs/embedding-evaluation-data-spec.md
git commit -m "docs(specs): amend R2.1, R2.3 and R9.1 for the Form 300A stage

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Notes for the completion Handoff

When the Plan Completion Protocol writes `## Handoff to later stages` (step 3a), carry the points below. Correct them from the deviation notes, the ledger and the Task 7 finding.

- **Stage 3 (ITA verification).**
  - **Inputs.** It consumes `data/derived/osha/ita_300a_summary.parquet` (`ita_summary.TABLE_NAME`) with the columns listed in Task 5. `source_file` resolves to a manifest entry through `manifest.entry_for`.
  - **`establishment_id` (V2).** It is present in every year from 2016, but the 2016–2023 dictionary defines it per user account, and the users guide says OSHA assigns a new ID when a profile is re-created.
  - **`ein`.** It is empty in essentially all sampled 2016–2018 rows, and 8-digit EINs (a lost leading zero) appear from 2021. Both bear on R2.7's pre-2023 link.
  - **ZIP codes.** They arrive with lost leading zeros (4-digit) in some years, and as ZIP+4 without a hyphen. That bears on V3.
  - **Descriptions.** `industry_description` is kept as delivered, including leading and trailing spaces (2019) and mojibake (2022). That bears on V1.
- **Stage 4 (code tables).** The industry half of R2.9's filing-rule flag is deferred here, with its `specs/deferred_items.md` entry. The appendix versions are:
  - Subpart E App. A through the 2022 data: 66 entries, including `4521`, `4529` and `7213`.
  - Subpart E App. A from 2024-01-01: 65 entries, with `4522`/`4523` and without `7213`.
  - Subpart B App. A: 82 entries in pre-2012 codes such as `5181`.

  `naics_year` before 2023 is 2012 from the dictionary (`naics_year_from_dictionary`), and the finding records the vintage mix from 2023. `naics_code` is a six-digit string or null, guaranteed by the build.
- **Stage 6 (target contract).** Cite raw inputs through each row's `source_file` and `manifest.entry_for`. The table is rebuilt on every `osha summary` run, so a target built from it should record which `source_file` values it used.
- **Stage 10 (ITA establishment targets).** The `ein` gaps above affect employer dedup (R2.6) and co-ownership (R7.2).
- **Deferred items to append** (confirmed at plan review: D2 for the first, D6 for the second):
  - The industry half of the filing-rule flag (Size: plan; Target: Stage 4; Done when: R2.9's industry half is evaluated with concordance candidate sets).
  - Same-name replacement at the source (Size: quick-fix; Revisit if: OSHA re-posts a file under an existing name and a stage needs the revision).
