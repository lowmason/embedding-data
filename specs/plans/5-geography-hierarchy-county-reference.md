# Geography hierarchy and county reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a verified, immutable geography-v1 bundle containing the complete 2025 county inventory, both July 2023 CBSA types, typed geography relationships, and the complete 2025Q4 HUD candidate/eligibility lookup.

**Architecture:** Parse manifested official originals into small eager Polars frames, validate administrative and CBSA relationships separately, and derive six deterministic tables. Acquire/import references separately from the offline builder; publish a named bundle only after table validation, provenance inventories, and final integrity checks. Preserve Stage 3 interfaces and reuse Stage 4's node/edge schemas without its classification validator.

**Tech Stack:** Python >=3.14; existing Polars >=2.0.0, fastexcel >=0.21.0, httpx >=0.28.1 and Typer >=0.27.3; pytest; standard-library csv, zipfile, pathlib and dataclasses. No dependency or lockfile changes.

**Spec:** [specs/geography-hierarchy-county-reference.md](../geography-hierarchy-county-reference.md), implementing R6.1, R6.2, R6.4 and the reference portion of R2.8 in [the source spec](../embedding-evaluation-data-spec.md). Read the stage spec and [reference preflight](../findings/stage-5-geography-reference-preflight.md) before execution.

> Roadmap: specs/embedding-evaluation-data-spec-roadmap.md, Stage 5 — on plan completion, tick the stage and re-validate later stages against what shipped.

## Global Constraints

The following requirements are copied verbatim from the stage spec:

- "Use the existing Polars, fastexcel, httpx and Typer dependencies."
- "Reference inputs are small eager frames; production consumers can use the published Parquets lazily."
- "The administrative frame is 2025, compatible with Stage 3's common ACS2025 county frame. OMB membership remains the July 2023 delineation. HUD remains 2025Q4."
- "Read codes as strings and join by codes."
- "Official titles retain their wording and Unicode, with surrounding formatting whitespace removed."
- "Names are labels, never membership keys."
- "Preserve Stage 3's `import_hud`, `read_hud` and `zip_candidates` interfaces and verification artifacts."
- "The build requires all four manifested inputs and never downloads a missing reference."
- "A fully cached acquisition performs no HTTP requests."
- "No guessed padding, title-based membership, legacy Connecticut recoding or majority allocation repairs a reference defect."
- "Do not call `classification_tables.forest`: its system/level, uniqueness, same-vintage and single-parent rules are classification-specific."
- "No relatedness target is inferred from the hierarchy."
- "Count and aggregate **all** positive-share rows before any scope or compatibility filtering."
- "Maxima and ties never choose a headline county from multiple candidates."
- "Every ZIP present in HUD has a lookup row, including all-zero ZIPs."
- "Empty candidate lists are empty, not null."
- "Require an explicit safe run ID; refuse an existing final directory or its `.part` directory."
- "Do not add an implicit latest-run alias or mix files from separate runs."
- "Cite originals through hash-verifying `manifest.entry_for`, not the lookup-only `recorded_entry_for`."
- "Recheck cited originals before final publication."
- "Code tables are not rebuilt or required as input data for this geography build; their shared schema convention is the dependency."

Source spec R9.2 also applies verbatim: "Every transformation is deterministic and runs offline from raw files. Tests use fixtures, with no network and no credentials."

Every command test supplies a temporary `--data-dir`. No default test reads the real data tree, personal reference cache, `.env`, or a credential. Stage 6 establishment assignment/targets and Stage 8 PUMA allocation/V8 are outside this plan. Historical geography, metro divisions, CSAs, ZIP-to-ZCTA conversion and a graph-framework refactor remain outside scope. The source establishment table and all Stage 3/4 artifacts are protected inputs, not builder inputs.

## Decisions

- **D1** (owner, plan review, 2026-10-14): Approve plan 5 as written. Applied in: Tasks 1–6 and Global Constraints. The owner's 2026-10-13 design choices remain recorded in the stage spec; no spec amendment is introduced.

## Entry evidence and implementation boundaries

Planned on `main` at `21bf03e` with a clean working tree. The writing-plans ID reporter found highest ID 4, next free 5, and no collisions across refs/worktrees. Fresh baseline: 476 pytest tests passed, one network canary deselected; one Behave feature/two scenarios/ten steps passed; ruff and offline lock checks passed.

Read the roadmap and completed plans 3/4 through their Handoffs and shipped interfaces. Existing files are flat modules, not a `classification_tables/` package:

- `classification_tables.py:5` and `:8`: ordered `NODE_SCHEMA`/`EDGE_SCHEMA`, import directly. `forest` is not reusable here.
- `ita_references.py:23`: `reference_path(data_dir: Path, relative: str) -> Path`; `:26`: `existing_reference(data_dir: Path, file: Path) -> bool`; `:85`: `read_hud(file: Path) -> pl.DataFrame`. The HUD output is exactly `zip_key:String, county_geoid:String, bus_ratio:Float64, noncounty_geography:Boolean`.
- `ita_county_verification.py:18`: `zip_candidates(frame: pl.DataFrame) -> pl.DataFrame` excludes all-zero ZIPs and suppresses legacy-CT singletons. Preserve it; the new lookup cannot be built from its output alone.
- `manifest.py:39`, `:85`, `:97`, `:118`: `describe_file`, `check_appendable`, `append_entries`, and verified `entry_for`.
- `code_references.py:158`: model acquisition on its exclusive partial-file copy and no-overwrite hard-link publication, using geography's registry and validators. Never delegate to classification parsing. The older HUD importer remains untouched.
- `code_build.py:198`: model named/staged bundles on this convention, including detached checksums. Capture original citations before parsing, include geography CLI hashes, and compare citations at publication. Directory rename follows the existing final-check convention; do not claim a filesystem race-proof transaction.

Original-layout probes during planning found two traps to preserve in tests. The state header is physical Excel row 5, but the fourth nonempty row when empty rows are dropped; locate its unique exact contents instead of relying on the preflight's compressed row number. CBSA metadata/header/footer rows also shift when blank rows are dropped. Its recognized footer texts are specified in Task 1; an invalid membership code never makes a row a footer. Original FIPS cells already contain `01`, `001`, etc.; no padding is needed.

Planning validation used only a temporary source/test rehearsal tree: all 53 listed fixture tests passed, all 16 Python listings and three production-verifier scripts parsed, and the plan's current prose links/placeholder scan passed. A read-only rehearsal of the parser/transform listings against the four inspected originals reproduced 4,133 nodes, 5,048 edges, 3,144 counties, 925 CBSAs, 54,571 HUD rows and 39,494 ZIPs, with the preflight's type/membership/scope counts and zero unexpected in-scope HUD codes. It published no bundle, appended no manifest entries and did not implement this plan in the repository. Production acceptance, review, stage ticking and retirement remain execution gates.

## File map

| File | Responsibility |
| --- | --- |
| `src/embedding_data/geography_parsers.py` | Strict original-layout state, Gazetteer and OMB parsing; normalized internal frames |
| `src/embedding_data/geography_tables.py` | Complete county/CBSA references, typed graphs, separate graph validation and source parity |
| `src/embedding_data/geography_hud.py` | Preserve normalized HUD rows; candidate diagnostics and unfiltered singleton eligibility |
| `src/embedding_data/geography_references.py` | Pinned production identities, immutable acquire/import, verified offline reference reads |
| `src/embedding_data/geography_build.py` | Six-table staged bundle, source/software/output inventories and reports |
| `src/embedding_data/geography_cli.py` | `geography acquire`, `import-reference KIND FILE`, `build RUN_ID` |
| `src/embedding_data/cli.py` | Register the new subgroup |
| `tests/geography_fixtures.py` | Tiny genuine-layout XLSX/ZIP originals and explicit fixture registry |
| `tests/test_geography_parsers.py`, `tests/test_geography_tables.py`, `tests/test_geography_hud.py` | Pure contract tests and malformed-reference cases |
| `tests/test_geography_references.py`, `tests/test_geography_build.py`, `tests/test_geography_cli.py` | Immutable I/O, offline CLI and publication contracts |
| `specs/findings/stage-5-geography-reference-build.md` | Actual production acceptance evidence and explicit bundle selection |
| `README.md`, `CLAUDE.md` | Shipped commands and consumer contracts |

Do not modify `classification_tables.py`, `ita_references.py`, `ita_county_verification.py`, their tests, `pyproject.toml`, `uv.lock`, or unrelated backlog items to make geography work.

## Durable testing strategy

Mock only acquisition/network/clock or a final-publication mutation boundary; run actual fastexcel parsers, transforms, manifest operations and Parquet I/O. Tests use handwritten expected facts rather than recomputing the transform. Produce XLSX with existing `code_fixtures.write_xlsx`, a dependency-free standard-library zip/XML helper. These fixtures intentionally use valid synthetic CBSA labels and IDs and are explicitly marked as fixtures in provenance.

| Invariant | Cheapest layer / fixture | Task |
| --- | --- | --- |
| Unique exact headers; fixed string widths; official Unicode retained; only recognized footers skipped | Pure raw-sheet frames and tiny original-layout XLSX/ZIP | 1 |
| Duplicate keys, malformed rows even outside scope, unsupported CBSA type/role and bad archives fail | Parametrized parser mutations | 1 |
| Complete county inventory, typed dual paths, cross-state CBSA, metro/micro, non-CBSA, independent city and CT planning region | Four scoped counties plus excluded PR county; explicit expected edges/IDs | 2 |
| Endpoints, namespaced IDs including level, exact parents, cycles, source parity and membership join failures | Mutated tiny graph/reference tables | 2 |
| Full HUD row/ratio parity, absent vs zero-business, singleton/ties/mixed scope and legacy compatibility | Handwritten normalized HUD rows and status expectations | 3 |
| Pin verification, all-destination preflight, idempotent exact imports, changed/missing/unrecorded originals, symlinks, partial ownership | Tmp raw tree; MockTransport for download only | 4 |
| Six exact schemas, deterministic order, provenance, eight detached inventory entries and logical repeatability | Tmp full original-to-bundle integration | 5 |
| Offline builder refuses network, missing original, changed input and occupied final/partial; earlier output bytes immutable | Tmp CLI/build plus injected publication-boundary changes | 5 |
| Exact production counts, source exclusions and compatibility; second run agrees logically and earlier sources/runs remain intact | Explicit real-root acceptance commands, outside default pytest | 6 |

All new tests are unmarked, fast, offline fixture tests. Retain `network` marker registration, its default exclusion, and the unknown-marker error. No new live canary is needed for pinned originals. No CI exists; the exact default/pre-merge commands are:

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest -m 'not network'
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked behave
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked ruff check .
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv lock --offline --check
```

Run focused red/green tests within each task. Run the complete command group at the parsing/reference boundary (Task 4), publication boundary (Task 5), and production/review boundary (Task 6); inspect actual output at each checkpoint. Before execution use using-git-worktrees, keep the real root explicit in Task 6, and record deviations as they occur. Workers own only listed task files, are not alone in the repository, and must accommodate others' changes. Execute Tasks 1–6 in order, with task-scoped reviews and a final whole-branch review through requesting-code-review. Saving this plan executes none of them.

---

### Task 1: Strict original parsers and genuine-layout fixtures

**Files:** Create `src/embedding_data/geography_parsers.py`, `tests/geography_fixtures.py`, `tests/test_geography_parsers.py`. Reuse `tests/code_fixtures.py:79` without editing it.

**Interfaces:** Consumes raw `pl.DataFrame` sheets with all cells read as strings and an original `Path` for the Gazetteer. Produces `parse_states(raw, *, scope=SCOPE) -> dict[str, pl.DataFrame]` with `states`, `divisions`, `regions`, `excluded_states`; `parse_counties(file: Path) -> pl.DataFrame`; `parse_members(raw: pl.DataFrame) -> pl.DataFrame`; constants `SCOPE`, `EXCLUDED`, and internal schemas. All codes remain strings; all source rows are validated before scope filtering.

- [ ] **Step 1: Create fixtures and the failing parser tests.** Put the following complete fixture module in `tests/geography_fixtures.py`. The membership fixtures deliberately include synthetic metro/micro IDs; titles never drive joins.

```python
import csv
import io
from pathlib import Path
from zipfile import ZipFile

import polars as pl
from code_fixtures import write_xlsx

STATE_ROWS = [
    ['Census Bureau Region and Division Codes and FIPS Codes for States', None, None, None],
    ['Source: U.S. Census Bureau, Population Division', None, None, None],
    ['Internet Release Date: May 2026', None, None, None],
    [None, None, None, None],
    ['Region', 'Division', 'State (FIPS)', 'Name'],
    ['1', '0', '00', 'Northeast Region'],
    ['1', '1', '00', 'New England Division'],
    ['1', '1', '09', 'Connecticut'],
    ['3', '0', '00', 'South Region'],
    ['3', '5', '00', 'South Atlantic Division'],
    ['3', '5', '51', 'Virginia'],
    ['3', '6', '00', 'East South Central Division'],
    ['3', '6', '01', 'Alabama'],
    ['0', '0', '72', 'Puerto Rico'],
]
MEMBER_HEADER = [
    'CBSA Code', 'Metropolitan Division Code', 'CSA Code', 'CBSA Title',
    'Metropolitan/Micropolitan Statistical Area', 'Metropolitan Division Title',
    'CSA Title', 'County/County Equivalent', 'State Name', 'FIPS State Code',
    'FIPS County Code', 'Central/Outlying County',
]
MEMBER_ROWS = [
    ['Table with row headers in column A and column headers in row 3'] + [None] * 11,
    ['List 1. Fixture July 2023 delineations'] + [None] * 11,
    MEMBER_HEADER,
    ['10000', None, None, 'Fixture metropolitan', 'Metropolitan Statistical Area',
     None, None, 'Autauga County', 'Alabama', '01', '001', 'Central'],
    ['10000', None, None, 'Fixture metropolitan', 'Metropolitan Statistical Area',
     None, None, 'Alexandria city', 'Virginia', '51', '510', 'Outlying'],
    ['20000', None, None, 'Fixture micropolitan', 'Micropolitan Statistical Area',
     None, None, 'Capitol Planning Region', 'Connecticut', '09', '110', 'Central'],
    ['30000', None, None, 'Fixture excluded', 'Micropolitan Statistical Area',
     None, None, 'Adjuntas Municipio', 'Puerto Rico', '72', '001', 'Central'],
]
COUNTY_ROWS = [
    ['AL', '01001', 'Autauga County'],
    ['CT', '09110', 'Capitol Planning Region'],
    ['VA', '51001', 'Accomack County'],
    ['VA', '51510', 'Alexandria city'],
    ['PR', '72001', 'Adjuntas Municipio'],
]
FIXTURE_SCOPE = frozenset({'01', '09', '51'})
HUD_ROWS = [
    ['ZIP', 'COUNTY', 'BUS_RATIO', 'STATE'],
    ['00001', '01001', '1', 'AL'],
    ['00002', '01001', '0', 'AL'],
    ['00003', '01001', '0.6', 'AL'],
    ['00003', '72001', '0.4', 'PR'],
    ['00004', '01001', '0.5', 'AL'],
    ['00004', '51510', '0.5', 'VA'],
    ['00005', '72001', '1', 'PR'],
    ['00006', '01999', '1', 'AL'],
    ['00007', '09001', '1', 'CT'],
    ['00008', '60', '0', 'AS'],
    ['00009', '01001', '1', 'AL'],
    ['00009', '72001', '0', 'PR'],
]


def sheet(rows):
    return pl.DataFrame(rows, orient='row', schema={f'c{i}': pl.String
                                                for i in range(len(rows[0]))})


def write_counties(file: Path, rows=COUNTY_ROWS):
    text = io.StringIO()
    writer = csv.writer(text, delimiter='|', lineterminator='\n')
    writer.writerow(['USPS', 'GEOID', 'GEOIDFQ', 'ANSICODE', 'NAME', 'ALAND', 'AWATER',
                     'ALAND_SQMI', 'AWATER_SQMI', 'INTPTLAT', 'INTPTLONG'])
    for usps, code, title in rows:
        writer.writerow([usps, code, '0500000US' + code, '00000000', title,
                         '1', '0', '1', '0', '0', '0'])
    with ZipFile(file, 'w') as archive:
        archive.writestr('2025_Gaz_counties_national.txt', text.getvalue())


def originals(directory: Path) -> dict[str, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    files = {k: directory / name for k, name in {
        'states_2025': 'state-geocodes-v2025.xlsx',
        'counties_2025': '2025_Gaz_counties_national.zip',
        'cbsa_2023': 'list1_2023.xlsx',
        'hud_2025q4': 'ZIP-COUNTY_122025.xlsx',
    }.items()}
    write_xlsx(files['states_2025'], STATE_ROWS)
    write_counties(files['counties_2025'])
    write_xlsx(files['cbsa_2023'], MEMBER_ROWS)
    write_xlsx(files['hud_2025q4'], HUD_ROWS)
    return files


def source_frames(tmp_path):
    from embedding_data import geography_parsers as gp, ita_references

    files = originals(tmp_path / 'originals')
    def read(file):
        return pl.read_excel(file, has_header=False, drop_empty_rows=False,
                             read_options={'dtypes': 'string'})
    return {
        **gp.parse_states(read(files['states_2025']), scope=FIXTURE_SCOPE),
        'counties': gp.parse_counties(files['counties_2025']),
        'members': gp.parse_members(read(files['cbsa_2023'])),
        'hud': ita_references.read_hud(files['hud_2025q4']),
    }
```

In `tests/test_geography_parsers.py`:

```python
import polars as pl
import pytest
from geography_fixtures import (COUNTY_ROWS, FIXTURE_SCOPE, MEMBER_ROWS, STATE_ROWS,
                                sheet, source_frames, write_counties)

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
```

- [ ] **Step 2: Run the red test.**

Run: `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_geography_parsers.py -q`. Expected: collection fails because `geography_parsers` does not exist; never accept a dependency/fixture failure as the intended red.

- [ ] **Step 3: Implement the strict parser boundary.** Create `geography_parsers.py` with the following code. The fixed scope list is an explicit administrative contract, checked against the state original; it is not a code-to-title lookup.

```python
import csv
import io
import re
from pathlib import Path
from zipfile import ZipFile

import polars as pl

SCOPE = frozenset('01 02 04 05 06 08 09 10 11 12 13 15 16 17 18 19 20 21 22 '
                  '23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 '
                  '42 44 45 46 47 48 49 50 51 53 54 55 56'.split())
EXCLUDED = frozenset('60 64 66 68 69 70 72 74 78'.split())
STATE_SCHEMA = {c: pl.String for c in ['state_fips', 'state_title', 'division_code',
                                     'region_code']}
DIVISION_SCHEMA = {c: pl.String for c in ['division_code', 'division_title', 'region_code']}
REGION_SCHEMA = {c: pl.String for c in ['region_code', 'region_title']}
COUNTY_SCHEMA = {c: pl.String for c in ['county_geoid', 'county_title', 'state_fips',
                                      'state_usps']}
MEMBER_SCHEMA = {c: pl.String for c in ['county_geoid', 'state_fips', 'cbsa_code',
                                      'cbsa_title', 'cbsa_type', 'cbsa_role']}
STATE_HEADER = ('Region', 'Division', 'State (FIPS)', 'Name')
MEMBER_HEADER = ('CBSA Code', 'Metropolitan Division Code', 'CSA Code', 'CBSA Title',
                 'Metropolitan/Micropolitan Statistical Area', 'Metropolitan Division Title',
                 'CSA Title', 'County/County Equivalent', 'State Name', 'FIPS State Code',
                 'FIPS County Code', 'Central/Outlying County')
CBSA_FOOTERS = (
    "Note: The Office of Management and Budget's (OMB's) 2020 Standards for Delineating "
    'Core Based Statistical Areas are at <https://www.federalregister.gov/documents/'
    '2021/07/16/2021-15159/2020-standards-for-delineating-core-based-statistical-areas>.',
    'Source: File prepared by U.S. Census Bureau, Population Division, based on OMB, '
    'July 2023 delineations <https://www.whitehouse.gov/wp-content/uploads/2023/07/'
    'OMB-Bulletin-23-01.pdf>.',
)


def text(value):
    return '' if value is None else str(value).strip()


def code(value, width, label):
    value = text(value)
    if not re.fullmatch(r'[0-9]{' + str(width) + '}', value):
        raise ValueError(f'{label}: expected {width} ASCII digits, received {value!r}')
    return value


def title(value, label):
    value = text(value)
    if not value:
        raise ValueError(f'{label}: missing title')
    return value


def body(raw, header):
    rows = [tuple(text(x) for x in row) for row in raw.rows()]
    hits = [i for i, row in enumerate(rows) if row == header]
    if len(hits) != 1:
        raise ValueError('missing or ambiguous exact reference header')
    return [row for row in rows[hits[0] + 1:] if any(row)]


def frame(rows, schema, key):
    result = pl.DataFrame(rows, schema=schema, orient='row')
    if result.is_empty() or result[key].n_unique() != result.height:
        raise ValueError(f'empty or duplicate {key}')
    return result.sort(key)


def parse_states(raw: pl.DataFrame, *, scope=SCOPE) -> dict[str, pl.DataFrame]:
    regions, divisions, states, excluded = [], [], [], []
    for r, d, s, name in body(raw, STATE_HEADER):
        r, d, s = code(r, 1, 'region'), code(d, 1, 'division'), code(s, 2, 'state')
        name = title(name, 'state/region/division')
        if s in EXCLUDED:
            excluded.append((s, name, d, r))
        elif s == '00' and r in '1234' and d == '0':
            regions.append((r, name))
        elif s == '00' and r in '1234' and d in '123456789':
            divisions.append((d, name, r))
        elif s in scope and r in '1234' and d in '123456789':
            states.append((s, name, d, r))
        else:
            raise ValueError('unsupported or contradictory administrative row')
    result = {'regions': frame(regions, REGION_SCHEMA, 'region_code'),
              'divisions': frame(divisions, DIVISION_SCHEMA, 'division_code'),
              'states': frame(states, STATE_SCHEMA, 'state_fips'),
              'excluded_states': pl.DataFrame(excluded, schema=STATE_SCHEMA, orient='row')}
    if excluded and result['excluded_states']['state_fips'].n_unique() != len(excluded):
        raise ValueError('duplicate excluded state')
    if set(result['states']['state_fips']) != set(scope):
        raise ValueError('state inventory does not equal the explicit administrative scope')
    region_keys = set(result['regions']['region_code'])
    division_parents = dict(result['divisions'].select('division_code', 'region_code').rows())
    if not set(division_parents.values()).issubset(region_keys):
        raise ValueError('division has no region reference')
    for s, name, d, r in states:
        if division_parents.get(d) != r:
            raise ValueError('state division/region relationships disagree')
    return result


def parse_counties(file: Path) -> pl.DataFrame:
    member = '2025_Gaz_counties_national.txt'
    with ZipFile(file) as archive:
        if archive.namelist() != [member]:
            raise ValueError('county archive must contain exactly the registered text member')
        contents = archive.read(member).decode('utf-8-sig')
    reader = csv.reader(io.StringIO(contents), delimiter='|')
    header = [text(x) for x in next(reader, [])]
    if len(header) != len(set(header)) or not {'USPS', 'GEOID', 'NAME'}.issubset(header):
        raise ValueError('missing or ambiguous county header')
    rows = []
    for values in reader:
        if not any(text(x) for x in values):
            continue
        if len(values) != len(header):
            raise ValueError('malformed county row width')
        row = dict(zip(header, values, strict=True))
        geoid = code(row['GEOID'], 5, 'county GEOID')
        usps = text(row['USPS'])
        if not re.fullmatch('[A-Z]{2}', usps) or geoid[:2] not in SCOPE | EXCLUDED:
            raise ValueError('unrecognized county state/USPS syntax')
        rows.append((geoid, title(row['NAME'], 'county'), geoid[:2], usps))
    result = frame(rows, COUNTY_SCHEMA, 'county_geoid')
    pairs = result.select('state_fips', 'state_usps').unique()
    if pairs['state_fips'].n_unique() != pairs.height or pairs['state_usps'].n_unique() != pairs.height:
        raise ValueError('Gazetteer FIPS/USPS pairs are not one-to-one')
    return result


def parse_members(raw: pl.DataFrame) -> pl.DataFrame:
    types = {'Metropolitan Statistical Area': 'metropolitan',
             'Micropolitan Statistical Area': 'micropolitan'}
    roles = {'Central': 'central', 'Outlying': 'outlying'}
    rows = []
    for row in body(raw, MEMBER_HEADER):
        if row[0] in CBSA_FOOTERS and not any(row[1:]):
            continue
        cbsa = code(row[0], 5, 'CBSA')
        state, county = code(row[9], 2, 'membership state'), code(row[10], 3, 'membership county')
        if state not in SCOPE | EXCLUDED or row[4] not in types or row[11] not in roles:
            raise ValueError('unsupported CBSA type, role or state')
        title(row[7], 'member county')
        title(row[8], 'member state')
        rows.append((state + county, state, cbsa, title(row[3], 'CBSA'),
                     types[row[4]], roles[row[11]]))
    result = frame(rows, MEMBER_SCHEMA, 'county_geoid')
    descriptions = result.select('cbsa_code', 'cbsa_title', 'cbsa_type').unique()
    if descriptions['cbsa_code'].n_unique() != descriptions.height:
        raise ValueError('CBSA title/type contradicts another membership')
    return result
```

- [ ] **Step 4: Run green tests and lint the new files.** Run the focused command from Step 2, then `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked ruff check src/embedding_data/geography_parsers.py tests/geography_fixtures.py tests/test_geography_parsers.py`. Expected: all parser cases pass and no lint errors after formatting/import fixes. Formatting may change the listings' wrapping, never their contracts.
- [ ] **Step 5: Commit and review the parser deliverable.**

```bash
git add src/embedding_data/geography_parsers.py tests/geography_fixtures.py tests/test_geography_parsers.py
git commit -m 'feat(geography): parse strict original reference layouts'
```

### Task 2: Complete county/CBSA references and separately validated typed graphs

**Files:** Create `src/embedding_data/geography_tables.py`, `tests/test_geography_tables.py`.

**Interfaces:** Consumes Task 1's source-frame dictionary. Produces `assemble(sources: dict[str, pl.DataFrame]) -> dict[str, pl.DataFrame]` with `geography_nodes`, `geography_edges`, `county_reference`, `cbsa_reference`; `validate_graph(nodes, edges) -> None`; `validate_tables(tables, sources) -> None`; `SCHEMAS` with the four exact output contracts. No paths Parquet is produced.

- [ ] **Step 1: Write relationship tests with explicit expected facts.**

```python
import polars as pl
import pytest
from geography_fixtures import source_frames

from embedding_data import geography_tables as gt


def test_both_paths_full_inventory_and_cross_state_cbsa(tmp_path):
    sources = source_frames(tmp_path)
    tables = gt.assemble(sources)
    gt.validate_tables(tables, sources)
    assert {k: f.schema for k, f in tables.items()} == gt.SCHEMAS
    counties = tables['county_reference']
    assert counties['county_geoid'].to_list() == ['01001', '09110', '51001', '51510']
    assert tables['geography_nodes'].height == 14
    assert tables['geography_edges'].height == 13
    assert counties.filter(pl.col('county_geoid').eq('51001')).select(
        'cbsa_id', 'cbsa_code', 'cbsa_type', 'cbsa_role', 'cbsa_vintage').null_count().row(0) == (
            1, 1, 1, 1, 1)
    metro = tables['cbsa_reference'].filter(pl.col('cbsa_code').eq('10000')).row(0, named=True)
    assert metro['state_fips'] == ['01', '51']
    assert metro['n_counties'] == 2
    assert metro['cbsa_type'] == 'metropolitan'
    assert tables['cbsa_reference'].filter(pl.col('cbsa_code').eq('20000')).item(
        0, 'cbsa_type') == 'micropolitan'
    edges = set(tables['geography_edges'].rows())
    assert ('geography:2025:county:51510', 'geography:2025:state:51', 'county_state') in edges
    assert ('geography:2025:county:51510', 'geography:2023:cbsa:10000', 'county_cbsa') in edges
    assert not any('72001' in child or kind == 'cbsa_state' for child, parent, kind in edges)
    assert {'geography:2025:region:1', 'geography:2025:division:1'}.issubset(
        set(tables['geography_nodes']['node_id']))


@pytest.mark.parametrize('name', ['geography_nodes', 'geography_edges',
                                  'county_reference', 'cbsa_reference'])
def test_output_reference_parity_is_checked(tmp_path, name):
    sources = source_frames(tmp_path)
    tables = gt.assemble(sources)
    tables[name] = tables[name].slice(1)
    with pytest.raises(ValueError):
        gt.validate_tables(tables, sources)


def test_membership_join_failure_is_not_a_non_cbsa_county(tmp_path):
    sources = source_frames(tmp_path)
    sources['members'] = sources['members'].with_columns(
        pl.when(pl.col('county_geoid').eq('01001')).then(pl.lit('01003'))
        .otherwise(pl.col('county_geoid')).alias('county_geoid'))
    with pytest.raises(ValueError, match='member county'):
        gt.assemble(sources)


def test_orphan_duplicate_parent_wrong_id_and_cycle_fail(tmp_path):
    tables = gt.assemble(source_frames(tmp_path))
    nodes, edges = tables['geography_nodes'], tables['geography_edges']
    county_edge = edges.filter(pl.col('edge_type').eq('county_state')).head(1)
    for invalid in [pl.concat([edges, county_edge]),
                    pl.concat([edges, county_edge.with_columns(
                        pl.lit('geography:2025:state:51').alias('parent_id'))]),
                    edges.with_columns(pl.lit('missing').alias('parent_id')),
                    pl.concat([edges, pl.DataFrame(
                        [('geography:2025:state:01', 'geography:2025:county:01001',
                          'state_division')], schema=gt.EDGE_SCHEMA, orient='row')]),
                    edges.filter(pl.col('child_id').ne('geography:2025:county:01001'))]:
        with pytest.raises(ValueError):
            gt.validate_graph(nodes, invalid)
    with pytest.raises(ValueError):
        gt.validate_graph(nodes.with_columns(pl.lit('bad').alias('node_id')), edges)


def test_admin_parent_is_not_a_cbsa_parent_and_titles_must_agree(tmp_path):
    sources = source_frames(tmp_path)
    tables = gt.assemble(sources)
    bad_edge = pl.DataFrame([('geography:2023:cbsa:10000', 'geography:2025:state:01',
                             'county_state')], schema=gt.EDGE_SCHEMA, orient='row')
    with pytest.raises(ValueError):
        gt.validate_graph(tables['geography_nodes'], pl.concat([tables['geography_edges'], bad_edge]))
    tables['county_reference'] = tables['county_reference'].with_columns(
        pl.lit('wrong official title').alias('state_title'))
    with pytest.raises(ValueError):
        gt.validate_tables(tables, sources)
```

- [ ] **Step 2: Verify red.** Run `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_geography_tables.py -q`. Expected: missing `geography_tables`, not a parser/fixture defect.
- [ ] **Step 3: Implement exact schemas, source assembly and graph validation.**

```python
import re
from collections import Counter, defaultdict

import polars as pl

from embedding_data.classification_tables import EDGE_SCHEMA, NODE_SCHEMA
from embedding_data.geography_parsers import EXCLUDED, SCOPE

COUNTY_SCHEMA = {c: pl.String for c in ['county_id', 'county_geoid', 'county_title']}
COUNTY_SCHEMA['county_vintage'] = pl.Int64
COUNTY_SCHEMA.update({c: pl.String for c in [
    'state_id', 'state_fips', 'state_usps', 'state_title', 'division_id', 'division_code',
    'division_title', 'region_id', 'region_code', 'region_title', 'cbsa_id', 'cbsa_code',
    'cbsa_type', 'cbsa_role']})
COUNTY_SCHEMA['cbsa_vintage'] = pl.Int64
CBSA_SCHEMA = {c: pl.String for c in ['cbsa_id', 'cbsa_code', 'cbsa_title', 'cbsa_type']}
CBSA_SCHEMA.update(cbsa_vintage=pl.Int64, n_counties=pl.Int64, state_fips=pl.List(pl.String))
SCHEMAS = {'geography_nodes': NODE_SCHEMA, 'geography_edges': EDGE_SCHEMA,
           'county_reference': COUNTY_SCHEMA, 'cbsa_reference': CBSA_SCHEMA}
EDGE_ENDPOINTS = {
    'county_state': (('county', 2025), ('state', 2025)),
    'state_division': (('state', 2025), ('division', 2025)),
    'division_region': (('division', 2025), ('region', 2025)),
    'county_cbsa': (('county', 2025), ('cbsa', 2023)),
}


def identifier(level, code):
    return f'geography:{2023 if level == "cbsa" else 2025}:{level}:{code}'


def validate_graph(nodes: pl.DataFrame, edges: pl.DataFrame) -> None:
    if nodes.schema != NODE_SCHEMA or edges.schema != EDGE_SCHEMA or nodes.is_empty():
        raise ValueError('incompatible or empty geography graph')
    if any(nodes[c].null_count() for c in nodes.columns) or any(
            edges[c].null_count() for c in edges.columns):
        raise ValueError('null graph field')
    if (nodes['node_id'].n_unique() != nodes.height or
            nodes.select('system', 'vintage', 'level', 'code').is_duplicated().any() or
            edges.is_duplicated().any()):
        raise ValueError('duplicate node or edge')
    records = {r['node_id']: r for r in nodes.iter_rows(named=True)}
    adjacency = defaultdict(list)
    for child, parent, kind in edges.rows():
        if child not in records or parent not in records:
            raise ValueError('missing graph endpoint')
        adjacency[child].append(parent)
    visited, active = set(), set()

    def visit(node):
        if node in active:
            raise ValueError('cycle in geography graph')
        if node in visited:
            return
        active.add(node)
        for parent in adjacency[node]:
            visit(parent)
        active.remove(node)
        visited.add(node)

    for node in records:
        visit(node)
    for node in records.values():
        width = {'region': 1, 'division': 1, 'state': 2, 'county': 5, 'cbsa': 5}.get(node['level'])
        if (width is None or node['system'] != 'geography' or
                node['vintage'] != (2023 if node['level'] == 'cbsa' else 2025) or
                not re.fullmatch(r'[0-9]{' + str(width) + '}', node['code']) or
                node['node_id'] != identifier(node['level'], node['code']) or
                not node['title'].strip()):
            raise ValueError('invalid namespaced geography node')
    degree = Counter()
    for child, parent, kind in edges.rows():
        a, b = records[child], records[parent]
        actual = ((a['level'], a['vintage']), (b['level'], b['vintage']))
        if EDGE_ENDPOINTS.get(kind) != actual:
            raise ValueError('unsupported edge type/endpoint levels or vintages')
        if kind == 'county_state' and a['code'][:2] != b['code']:
            raise ValueError('county administrative state contradicts its GEOID')
        degree[(child, kind)] += 1
    required = {'county': 'county_state', 'state': 'state_division', 'division': 'division_region'}
    for node, record in records.items():
        kind = required.get(record['level'])
        if kind and degree[(node, kind)] != 1:
            raise ValueError('missing or contradictory administrative parent')
        if degree[(node, 'county_cbsa')] > 1:
            raise ValueError('contradictory county-to-CBSA membership')


def assemble(sources: dict[str, pl.DataFrame]) -> dict[str, pl.DataFrame]:
    states = {r['state_fips']: r for r in sources['states'].iter_rows(named=True)}
    divisions = {r['division_code']: r for r in sources['divisions'].iter_rows(named=True)}
    regions = {r['region_code']: r for r in sources['regions'].iter_rows(named=True)}
    counties = sources['counties'].filter(pl.col('state_fips').is_in(list(states)))
    members = sources['members'].filter(pl.col('state_fips').is_in(list(states)))
    for frame in [sources['counties'], sources['members']]:
        unknown = set(frame['state_fips']) - set(states) - EXCLUDED
        if unknown or not set(states).issubset(SCOPE):
            raise ValueError('scoped county/membership state absent from state reference')
    if (counties['county_geoid'].n_unique() != counties.height or
            members['county_geoid'].n_unique() != members.height):
        raise ValueError('duplicate county or membership reference key')
    if not set(members['county_geoid']).issubset(set(counties['county_geoid'])):
        raise ValueError('member county is absent from the complete county frame')
    if counties.filter(pl.col('state_fips').eq('09').and_(
            pl.col('county_geoid').str.contains(r'^091[1-9]0$').not_())).height:
        raise ValueError('Connecticut frame must contain planning regions')
    by_county = {r['county_geoid']: r for r in members.iter_rows(named=True)}
    cbsa_members = defaultdict(list)
    for r in members.iter_rows(named=True):
        cbsa_members[r['cbsa_code']].append(r)
    node_rows, edge_rows, county_rows, cbsa_rows = [], [], [], []

    def node(level, value, name):
        node_rows.append((identifier(level, value), 'geography',
                          2023 if level == 'cbsa' else 2025, level, value, name))

    for r, item in regions.items():
        node('region', r, item['region_title'])
    for d, item in divisions.items():
        r = item['region_code']
        if r not in regions:
            raise ValueError('division region is absent')
        node('division', d, item['division_title'])
        edge_rows.append((identifier('division', d), identifier('region', r), 'division_region'))
    for s, item in states.items():
        d, r = item['division_code'], item['region_code']
        if d not in divisions or divisions[d]['region_code'] != r:
            raise ValueError('state division/region contradicts the reference')
        node('state', s, item['state_title'])
        edge_rows.append((identifier('state', s), identifier('division', d), 'state_division'))
    for item in counties.iter_rows(named=True):
        c, s = item['county_geoid'], item['state_fips']
        state = states[s]
        d, r = state['division_code'], state['region_code']
        membership = by_county.get(c)
        node('county', c, item['county_title'])
        edge_rows.append((identifier('county', c), identifier('state', s), 'county_state'))
        cbsa = membership['cbsa_code'] if membership else None
        if membership:
            edge_rows.append((identifier('county', c), identifier('cbsa', cbsa), 'county_cbsa'))
        county_rows.append((identifier('county', c), c, item['county_title'], 2025,
                            identifier('state', s), s, item['state_usps'], state['state_title'],
                            identifier('division', d), d, divisions[d]['division_title'],
                            identifier('region', r), r, regions[r]['region_title'],
                            identifier('cbsa', cbsa) if membership else None, cbsa,
                            membership['cbsa_type'] if membership else None,
                            membership['cbsa_role'] if membership else None,
                            2023 if membership else None))
    for c, items in cbsa_members.items():
        labels = {(r['cbsa_title'], r['cbsa_type']) for r in items}
        if len(labels) != 1:
            raise ValueError('contradictory CBSA title/type')
        name, kind = next(iter(labels))
        node('cbsa', c, name)
        cbsa_rows.append((identifier('cbsa', c), c, name, kind, 2023, len(items),
                          sorted({r['state_fips'] for r in items})))
    output = {
        'geography_nodes': pl.DataFrame(node_rows, schema=NODE_SCHEMA, orient='row').sort('node_id'),
        'geography_edges': pl.DataFrame(edge_rows, schema=EDGE_SCHEMA, orient='row').sort(
            'child_id', 'parent_id', 'edge_type'),
        'county_reference': pl.DataFrame(county_rows, schema=COUNTY_SCHEMA, orient='row').sort(
            'county_geoid'),
        'cbsa_reference': pl.DataFrame(cbsa_rows, schema=CBSA_SCHEMA, orient='row').sort('cbsa_code'),
    }
    validate_graph(output['geography_nodes'], output['geography_edges'])
    return output


def validate_tables(tables, sources) -> None:
    validate_graph(tables['geography_nodes'], tables['geography_edges'])
    expected = assemble(sources)
    for name, schema in SCHEMAS.items():
        if tables[name].schema != schema or not tables[name].equals(expected[name]):
            raise ValueError(f'{name}: exact source/graph/reference parity failed')
```

`validate_tables` deliberately checks rebuilt source parity as well as generic graph invariants; handwritten fixture expectations independently check the assembler. Expected-table comparison also enforces all-together CBSA nullability, official titles/IDs, count/state-set parity, and deterministic order. Source parsers remain the authority for duplicate and malformed original rows.

- [ ] **Step 4: Verify green and mutation rejection.** Run `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_geography_parsers.py tests/test_geography_tables.py -q`, then focused ruff for the new files. Expected: all pass, including deliberately invalid graphs/references. Keep the 14-node/13-edge fixture expectations distinct from production acceptance.
- [ ] **Step 5: Commit and review the graph/reference deliverable.**

```bash
git add src/embedding_data/geography_tables.py tests/test_geography_tables.py
git commit -m 'feat(geography): build complete typed graph and county references'
```

### Task 3: Full HUD candidate diagnostics and ZIP eligibility

**Files:** Create `src/embedding_data/geography_hud.py`, `tests/test_geography_hud.py`.

**Interfaces:** Consumes `read_hud`'s validated four-column frame and Task 2's complete county reference. Produces `annotate(hud: pl.DataFrame, counties: pl.DataFrame) -> pl.DataFrame`; `lookup(candidates: pl.DataFrame) -> pl.DataFrame`; exact `HUD_SCHEMA`, `LOOKUP_SCHEMA`, and `SCHEMAS`. It does not assign establishments or invoke the Stage 3 selector.

- [ ] **Step 1: Write the failing eligibility tests.**

```python
import polars as pl
from geography_fixtures import source_frames
from polars.testing import assert_frame_equal

from embedding_data import geography_hud as gh, geography_tables as gt


def test_hud_inventory_ratios_and_all_statuses(tmp_path):
    sources = source_frames(tmp_path)
    counties = gt.assemble(sources)['county_reference']
    candidates = gh.annotate(sources['hud'], counties)
    table = gh.lookup(candidates)
    assert candidates.schema == gh.HUD_SCHEMA
    assert table.schema == gh.LOOKUP_SCHEMA
    assert_frame_equal(candidates.select(sources['hud'].columns), sources['hud'])
    assert table['zip_key'].to_list() == [f'{i:05}' for i in range(1, 10)]
    assert table['eligibility_status'].to_list() == [
        'eligible', 'zero_business', 'multiple_counties', 'multiple_counties',
        'out_of_scope', 'incompatible_county', 'incompatible_county',
        'zero_business', 'eligible']
    assert table.filter(pl.col('zip_key').eq('99999')).is_empty()
    rows = {r['zip_key']: r for r in table.iter_rows(named=True)}
    assert rows['00002']['business_counties'] == []
    assert rows['00002']['dominant_candidates'] == []
    assert rows['00002']['max_business_ratio'] is None
    assert rows['00003']['business_counties'] == ['01001', '72001']
    assert rows['00003']['zip_dominant_county'] == '01001'
    assert rows['00003']['zip_single_candidate'] is None
    assert rows['00003']['zip_fallback_county'] is None
    assert rows['00003']['flag_zip_has_out_of_scope'] is True
    assert rows['00004']['dominant_candidates'] == ['01001', '51510']
    assert rows['00004']['zip_dominant_county'] is None
    assert rows['00005']['zip_single_candidate'] == '72001'
    assert rows['00007']['zip_single_candidate'] == '09001'
    assert rows['00007']['flag_zip_legacy_ct'] is True
    assert rows['00007']['flag_zip_has_incompatible'] is True
    assert rows['00008']['n_hud_rows'] == 1
    assert rows['00008']['flag_zip_has_out_of_scope'] is False
    assert candidates.filter(pl.col('county_geoid').eq('60')).item(
        0, 'flag_county_out_of_scope') is True
    assert rows['00009']['n_hud_rows'] == 2
    assert rows['00009']['n_business_counties'] == 1
    assert rows['00009']['zip_fallback_county'] == '01001'
    assert rows['00009']['flag_zip_has_out_of_scope'] is False
    assert all(r['zip_fallback_county'] is None for r in rows.values()
               if r['eligibility_status'] != 'eligible')


def test_reordered_candidates_produce_identical_sorted_lookup(tmp_path):
    sources = source_frames(tmp_path)
    counties = gt.assemble(sources)['county_reference']
    one = gh.annotate(sources['hud'], counties)
    two = gh.annotate(sources['hud'].reverse(), counties)
    assert_frame_equal(one, two)
    assert_frame_equal(gh.lookup(one), gh.lookup(two))
```

- [ ] **Step 2: Verify red.** Run `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_geography_hud.py -q`. Expected: missing `geography_hud`.
- [ ] **Step 3: Implement row-preserving diagnostics and original-candidate aggregation.**

```python
from collections import defaultdict

import polars as pl

from embedding_data.geography_parsers import EXCLUDED

NORMALIZED_SCHEMA = {'zip_key': pl.String, 'county_geoid': pl.String,
                     'bus_ratio': pl.Float64, 'noncounty_geography': pl.Boolean}
HUD_SCHEMA = {**NORMALIZED_SCHEMA, **{c: pl.Boolean for c in [
    'county_in_frame', 'flag_county_out_of_scope', 'flag_county_incompatible',
    'flag_county_legacy_ct']}}
LOOKUP_SCHEMA = {'zip_key': pl.String, 'n_hud_rows': pl.Int64,
                 'n_business_counties': pl.Int64, 'business_counties': pl.List(pl.String),
                 'max_business_ratio': pl.Float64, 'dominant_candidates': pl.List(pl.String),
                 'zip_dominant_county': pl.String, 'zip_single_candidate': pl.String,
                 'zip_fallback_county': pl.String, 'eligibility_status': pl.String}
LOOKUP_SCHEMA.update({c: pl.Boolean for c in ['flag_zip_zero_business',
    'flag_zip_multiple_counties', 'flag_zip_has_out_of_scope',
    'flag_zip_has_incompatible', 'flag_zip_legacy_ct']})
SCHEMAS = {'hud_zip_county': HUD_SCHEMA, 'hud_zip_lookup': LOOKUP_SCHEMA}


def annotate(hud: pl.DataFrame, counties: pl.DataFrame) -> pl.DataFrame:
    if hud.schema != NORMALIZED_SCHEMA:
        raise ValueError('incompatible normalized read_hud schema')
    inventory = counties['county_geoid'].to_list()
    output = hud.with_columns(
        county_in_frame=pl.col('county_geoid').is_in(inventory),
        flag_county_out_of_scope=pl.col('county_geoid').str.slice(0, 2).is_in(sorted(EXCLUDED)),
        flag_county_legacy_ct=pl.col('county_geoid').str.contains(r'^090[0-9]{2}$'),
    ).with_columns(flag_county_incompatible=pl.col('county_in_frame').not_().and_(
        pl.col('flag_county_out_of_scope').not_()).and_(pl.col('noncounty_geography').not_()))
    return output.select(list(HUD_SCHEMA)).sort('zip_key', 'county_geoid')


def lookup(candidates: pl.DataFrame) -> pl.DataFrame:
    if candidates.schema != HUD_SCHEMA:
        raise ValueError('incompatible geography HUD candidate schema')
    groups = defaultdict(list)
    for row in candidates.iter_rows(named=True):
        groups[row['zip_key']].append(row)
    result = []
    for zip_key, items in sorted(groups.items()):
        positive = [r for r in items if r['bus_ratio'] > 0]
        n = len(positive)
        business = sorted(r['county_geoid'] for r in positive)
        maximum = max((r['bus_ratio'] for r in positive), default=None)
        dominant = sorted(r['county_geoid'] for r in positive if r['bus_ratio'] == maximum)
        single = positive[0] if n == 1 else None
        if n == 0:
            status = 'zero_business'
        elif n > 1:
            status = 'multiple_counties'
        elif single['flag_county_out_of_scope']:
            status = 'out_of_scope'
        elif not single['county_in_frame']:
            status = 'incompatible_county'
        else:
            status = 'eligible'
        result.append((zip_key, len(items), n, business, maximum, dominant,
                       dominant[0] if len(dominant) == 1 else None,
                       single['county_geoid'] if single else None,
                       single['county_geoid'] if status == 'eligible' else None, status,
                       n == 0, n > 1,
                       any(r['flag_county_out_of_scope'] for r in positive),
                       any(r['flag_county_incompatible'] for r in positive),
                       any(r['flag_county_legacy_ct'] for r in positive)))
    return pl.DataFrame(result, schema=LOOKUP_SCHEMA, orient='row').sort('zip_key')
```

The bounded eager grouping is intentional for this small reference. It preserves all candidate identities before computing eligibility; no downstream consumer may turn `zip_dominant_county` into a fallback assignment. A unique maximum across multiple candidates remains only a diagnostic.

- [ ] **Step 4: Verify green and Stage 3 precedence regressions.** Run `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_geography_hud.py tests/test_ita_county_verification.py tests/test_ita_references.py -q`, then focused ruff. Expected: new HUD contracts and unchanged Census/HUD precedence tests pass. No changes to the old selector/importer/parser or its fixtures.
- [ ] **Step 5: Commit and review the HUD lookup deliverable.**

```bash
git add src/embedding_data/geography_hud.py tests/test_geography_hud.py
git commit -m 'feat(geography): preserve full HUD inventory and singleton eligibility'
```

### Task 4: Pinned acquisition/import and verified offline reference reads

**Files:** Create `src/embedding_data/geography_references.py`, `tests/test_geography_references.py`; append the fixture registry/seed helpers below to `tests/geography_fixtures.py`.

**Interfaces:** Consumes Tasks 1/3 parsers, existing manifest primitives and `ita_references.existing_reference`. Produces frozen `Reference`, `REGISTRY`, `reference_path(data_dir, reference) -> Path`, `preflight(data_dir, registry) -> dict[str, bool]`, `parse_reference(file, reference) -> dict[str, pl.DataFrame]`, `import_reference(data_dir, kind, original, *, registry=REGISTRY) -> Path`, `acquire(data_dir, *, registry=REGISTRY) -> list[Path]`, `read_sources(data_dir, *, registry=REGISTRY) -> dict[str, pl.DataFrame]`. Production identities require inspected hashes/sizes. Fixture replacements explicitly carry fixture identity and scope, not production claims.

- [ ] **Step 1: Add fixture registry/seed helpers and failing immutable-reference tests.** Append this code to `tests/geography_fixtures.py`:

```python
def fixture_registry(files):
    from dataclasses import replace

    from embedding_data import geography_references as gr, manifest

    return {k: replace(gr.REGISTRY[k], sha256=manifest.sha256_file(file),
                       size=file.stat().st_size, fixture=True, state_scope=FIXTURE_SCOPE)
            for k, file in files.items()}


def seed_geography_tree(data_dir):
    from embedding_data import geography_references as gr

    files = originals(data_dir / 'originals')
    registry = fixture_registry(files)
    for kind, file in files.items():
        gr.import_reference(data_dir, kind, file, registry=registry)
    return registry
```

In `tests/test_geography_references.py`:

```python
from dataclasses import replace
from pathlib import Path

import httpx
import polars as pl
import pytest
from fastexcel import FastExcelError
from geography_fixtures import fixture_registry, originals, seed_geography_tree

from embedding_data import geography_references as gr, manifest, paths


def test_import_idempotence_pins_and_proxy_provenance(tmp_path):
    files = originals(tmp_path / 'originals')
    registry = fixture_registry(files)
    file = files['states_2025']
    dest = gr.import_reference(tmp_path, 'states_2025', file, registry=registry)
    before = paths.manifest_path(tmp_path).read_bytes()
    assert gr.import_reference(tmp_path, 'states_2025', file, registry=registry) == dest
    assert dest.read_bytes() == file.read_bytes()
    assert paths.manifest_path(tmp_path).read_bytes() == before
    entry = manifest.entry_for(paths.manifest_path(tmp_path), dest)
    assert entry.proxies == ('retrieved_at',)
    assert entry.client == 'manual-import'
    assert entry.source_url == registry['states_2025'].url
    conflict = tmp_path / 'different.xlsx'
    conflict.write_bytes(b'different bytes')
    with pytest.raises(ValueError):
        gr.import_reference(tmp_path, 'states_2025', conflict, registry=registry)


@pytest.mark.parametrize('defect', ['changed', 'missing', 'symlink', 'partial'])
def test_manifested_original_defects_fail_before_http(tmp_path, monkeypatch, defect):
    registry = seed_geography_tree(tmp_path)
    file = gr.reference_path(tmp_path, registry['cbsa_2023'])
    if defect == 'changed':
        file.write_bytes(b'changed')
    elif defect == 'missing':
        file.unlink()
    elif defect == 'symlink':
        file.unlink()
        file.symlink_to(tmp_path / 'absent')
    else:
        file.with_name(file.name + '.part').write_bytes(b'occupied')
    monkeypatch.setattr(gr, 'make_client', lambda: pytest.fail('HTTP reached before preflight'))
    with pytest.raises((ValueError, FileNotFoundError)):
        gr.acquire(tmp_path, registry=registry)


def test_unrecorded_destination_and_ancestor_symlink_are_refused(tmp_path):
    files = originals(tmp_path / 'originals')
    registry = fixture_registry(files)
    dest = gr.reference_path(tmp_path, registry['states_2025'])
    dest.parent.mkdir(parents=True)
    dest.write_bytes(files['states_2025'].read_bytes())
    with pytest.raises(ValueError, match='provenance'):
        gr.acquire(tmp_path, registry=registry)
    dest.unlink()
    dest.parent.rmdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    dest.parent.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        gr.acquire(tmp_path, registry=registry)


def test_cached_acquisition_has_zero_http_and_offline_reads(tmp_path, monkeypatch):
    registry = seed_geography_tree(tmp_path)
    monkeypatch.setattr(gr, 'make_client', lambda: pytest.fail('cached acquisition needs no client'))
    assert len(gr.acquire(tmp_path, registry=registry)) == 4
    assert gr.read_sources(tmp_path, registry=registry)['hud'].height == 12


def test_acquisition_uses_registered_urls_and_missing_hud_blocks_first(tmp_path, monkeypatch):
    files = originals(tmp_path / 'originals')
    registry = fixture_registry(files)
    requests = []

    def respond(request):
        requests.append(str(request.url))
        kind = next(k for k, r in registry.items() if r.url == str(request.url))
        payload = files[kind].read_bytes()
        return httpx.Response(200, headers={'Content-Length': str(len(payload))},
                              stream=httpx.ByteStream(payload))

    monkeypatch.setattr(gr, 'make_client', lambda: httpx.Client(transport=httpx.MockTransport(respond)))
    with pytest.raises(ValueError, match='import-reference hud_2025q4'):
        gr.acquire(tmp_path, registry=registry)
    assert requests == []
    gr.import_reference(tmp_path, 'hud_2025q4', files['hud_2025q4'], registry=registry)
    gr.acquire(tmp_path, registry=registry)
    assert requests == [r.url for k, r in registry.items() if k != 'hud_2025q4']
    assert all(manifest.entry_for(paths.manifest_path(tmp_path),
               gr.reference_path(tmp_path, r)).proxies == ()
               for k, r in registry.items() if k != 'hud_2025q4')


def test_invalid_original_is_validated_before_publication(tmp_path):
    files = originals(tmp_path / 'originals')
    registry = fixture_registry(files)
    file = files['cbsa_2023']
    file.write_bytes(b'invalid workbook')
    registry['cbsa_2023'] = replace(registry['cbsa_2023'],
                                  sha256=manifest.sha256_file(file), size=file.stat().st_size)
    with pytest.raises((FastExcelError, pl.exceptions.PolarsError)):
        gr.import_reference(tmp_path, 'cbsa_2023', file, registry=registry)
    assert not gr.reference_path(tmp_path, registry['cbsa_2023']).exists()
    assert not paths.manifest_path(tmp_path).exists()


def test_hud_geoid_variant_preserves_logical_workbook_basename(tmp_path):
    from code_fixtures import write_xlsx

    files = originals(tmp_path / 'originals')
    alias = tmp_path / 'browser_download.xlsx'
    write_xlsx(alias, [['ZIP', 'GEOID', 'BUS_RATIO'], ['00001', '01001', '1']])
    files['hud_2025q4'] = alias
    registry = fixture_registry(files)
    dest = gr.import_reference(tmp_path, 'hud_2025q4', alias, registry=registry)
    assert dest.name == 'ZIP-COUNTY_122025.xlsx'
    assert gr.parse_reference(dest, registry['hud_2025q4'])['hud'].item(
        0, 'county_geoid') == '01001'


def test_exclusive_partial_failure_preserves_competing_bytes(tmp_path, monkeypatch):
    files = originals(tmp_path / 'originals')
    registry = fixture_registry(files)
    dest = gr.reference_path(tmp_path, registry['states_2025'])
    partial = dest.with_name(dest.name + '.part')
    open_path = Path.open

    def occupied(file, mode='r', *args, **kwargs):
        if file == partial and mode == 'xb':
            file.write_bytes(b'competitor')
        return open_path(file, mode, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', occupied)
    with pytest.raises(FileExistsError):
        gr.import_reference(tmp_path, 'states_2025', files['states_2025'], registry=registry)
    assert partial.read_bytes() == b'competitor'
    assert not dest.exists()
```

- [ ] **Step 2: Verify red.** Run `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_geography_references.py -q`. Expected: missing `geography_references`.
- [ ] **Step 3: Implement the new geography reference boundary.**

```python
import os
import shutil
import tempfile
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import httpx
import polars as pl

from embedding_data import geography_parsers as gp
from embedding_data import ita_references, manifest, paths
from embedding_data.osha_benchmark_download import USER_AGENT, download


@dataclass(frozen=True)
class Reference:
    kind: str
    url: str
    relative: str
    edition: str
    sha256: str
    size: int
    downloadable: bool = True
    fixture: bool = False
    state_scope: frozenset[str] = gp.SCOPE


REGISTRY = {
    'states_2025': Reference(
        'states_2025', 'https://www2.census.gov/programs-surveys/popest/geographies/2025/'
        'state-geocodes-v2025.xlsx', 'geography/2025/state-geocodes-v2025.xlsx', '2025',
        '327c7fa3dfeb6526b20cd3d1cef7f471ec08316e92b183f12c5b168bfed7da84', 14700),
    'counties_2025': Reference(
        'counties_2025', 'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/'
        '2025_Gazetteer/2025_Gaz_counties_national.zip',
        'geography/2025/2025_Gaz_counties_national.zip', '2025',
        '4c90d0f805779923b5958ab13d0c1e9b99fe4932b786bfcf75dd739bb2dcb4ea', 138993),
    'cbsa_2023': Reference(
        'cbsa_2023', 'https://www2.census.gov/programs-surveys/metro-micro/geographies/'
        'reference-files/2023/delineation-files/list1_2023.xlsx',
        'geography/2023/list1_2023.xlsx', 'July 2023',
        '952c4b1e78acbb54e6ec9412434b7602fedacbf021736351a63c181bdb753629', 143798),
    'hud_2025q4': Reference(
        'hud_2025q4', ita_references.HUD_SOURCE, 'hud/2025Q4/ZIP-COUNTY_122025.xlsx', '2025Q4',
        '554379b618f21380bed6777a9c69845ac138843c1a57f951886d605bc9611c68', 2462769,
        downloadable=False),
}


def occupied(file):
    return file.exists() or file.is_symlink()


def safe_path(file, data_dir):
    root, file = Path(data_dir).absolute(), Path(file).absolute()
    if not file.is_relative_to(root):
        raise ValueError('registered destination escapes data directory')
    for candidate in [root, *file.parents, file]:
        if candidate.is_relative_to(root) and candidate.is_symlink():
            raise ValueError(f'{candidate}: symlink in registered destination')


def reference_path(data_dir, reference):
    return ita_references.reference_path(data_dir, reference.relative)


def verify_pin(file, reference):
    if file.is_symlink() or file.stat().st_size != reference.size or (
            manifest.sha256_file(file) != reference.sha256):
        raise ValueError(f'{reference.kind}: original differs from registered bytes; '
                         'record a distinct source identity and decision')


def preflight(data_dir, registry):
    if set(registry) != set(REGISTRY):
        raise ValueError('geography requires all four registered reference identities')
    safe_path(paths.manifest_path(data_dir), data_dir)
    result = {}
    for kind, reference in registry.items():
        file = reference_path(data_dir, reference)
        safe_path(file, data_dir)
        partial = file.with_name(file.name + '.part')
        if occupied(partial):
            raise ValueError(f'{kind}: occupied reference partial')
        result[kind] = ita_references.existing_reference(data_dir, file)
        if result[kind]:
            verify_pin(file, reference)
    return result


def parse_reference(file, reference):
    verify_pin(file, reference)
    if reference.kind == 'counties_2025':
        return {'counties': gp.parse_counties(file)}
    if reference.kind == 'hud_2025q4':
        # read_hud's GEOID variant requires the registered workbook basename.
        with tempfile.TemporaryDirectory() as directory:
            logical = Path(directory) / Path(reference.relative).name
            shutil.copyfile(file, logical)
            verify_pin(logical, reference)
            return {'hud': ita_references.read_hud(logical)}
    raw = pl.read_excel(file, has_header=False, drop_empty_rows=False,
                        read_options={'dtypes': 'string'})
    if reference.kind == 'states_2025':
        return gp.parse_states(raw, scope=reference.state_scope)
    if reference.kind == 'cbsa_2023':
        return {'members': gp.parse_members(raw)}
    raise ValueError('unknown geography reference parser')


def publish_original(data_dir, reference, original, *, imported):
    file = reference_path(data_dir, reference)
    if original.is_symlink():
        raise ValueError('import source must be original bytes, not a symlink')
    verify_pin(original, reference)
    parse_reference(original, reference)
    if ita_references.existing_reference(data_dir, file):
        verify_pin(file, reference)
        return file
    citation = manifest.describe_file(
        original, original.parent, retrieved_at=datetime.now(UTC),
        client='manual-import' if imported else 'httpx',
        client_version=version('embedding-data') if imported else version('httpx'),
        source_url=reference.url, proxies=('retrieved_at',) if imported else ())
    citation = replace(citation, path=file.relative_to(paths.manifest_path(data_dir).parent).as_posix())
    if (citation.sha256, citation.size) != (reference.sha256, reference.size):
        raise ValueError('original changed during validation')
    manifest.check_appendable(paths.manifest_path(data_dir), [citation])
    safe_path(file, data_dir)
    file.parent.mkdir(parents=True, exist_ok=True)
    partial = file.with_name(file.name + '.part')
    output = partial.open('xb')  # If this fails, this invocation does not own cleanup.
    try:
        with output, original.open('rb') as source:
            shutil.copyfileobj(source, output)
        verify_pin(partial, reference)
        safe_path(file, data_dir)
        if occupied(file):
            raise ValueError('reference destination appeared during publication')
        os.link(partial, file)
        manifest.append_entries(paths.manifest_path(data_dir), [citation])
    finally:
        partial.unlink(missing_ok=True)
    return file


def import_reference(data_dir, kind, original, *, registry=REGISTRY):
    if kind not in registry:
        raise ValueError('unknown registered geography identity')
    preflight(data_dir, registry)
    return publish_original(data_dir, registry[kind], Path(original), imported=True)


def make_client():
    return httpx.Client(http2=True, follow_redirects=True, timeout=120,
                        headers={'User-Agent': USER_AGENT})


def acquire(data_dir, *, registry=REGISTRY):
    existing = preflight(data_dir, registry)
    if any(not existing[k] and not r.downloadable for k, r in registry.items()):
        raise ValueError('import-reference hud_2025q4 ORIGINAL before acquiring references')
    if all(existing.values()):
        return [reference_path(data_dir, r) for r in registry.values()]
    with make_client() as client:
        for kind, reference in registry.items():
            if existing[kind]:
                continue
            with tempfile.TemporaryDirectory() as directory:
                original = Path(directory) / Path(reference.relative).name
                download(client, reference.url, original)
                publish_original(data_dir, reference, original, imported=False)
    return [reference_path(data_dir, r) for r in registry.values()]


def read_sources(data_dir, *, registry=REGISTRY):
    existing = preflight(data_dir, registry)
    missing = [k for k, present in existing.items() if not present]
    if missing:
        raise ValueError(f'missing manifested geography originals: {missing}; acquire/import first')
    result = {}
    for reference in registry.values():
        file = reference_path(data_dir, reference)
        manifest.entry_for(paths.manifest_path(data_dir), file)
        result.update(parse_reference(file, reference))
    return result
```

All registered destinations are checked before acquisition requests. HUD acquisition is an explicit import because its registered URL is a catalog, not an unauthenticated binary download. Imports into the new boundary preserve Stage 3's existing original path and provenance; the existing Stage 3 command is still supported. No personal skill path enters runtime code.

- [ ] **Step 4: Run green reference tests and the first full milestone.** Run the focused command from Step 2, then the complete four-command group in Durable testing strategy. Expected: all new/old tests, Behave, lint and lock checks pass. The invalid-workbook test accepts only the reader exception families also handled by Task 5's CLI boundary.
- [ ] **Step 5: Commit and review the reference deliverable.**

```bash
git add src/embedding_data/geography_references.py tests/geography_fixtures.py tests/test_geography_references.py
git commit -m 'feat(geography): acquire and import pinned immutable originals'
```

### Task 5: Offline immutable bundle, provenance/report inventories and CLI

**Files:** Create `src/embedding_data/geography_build.py`, `src/embedding_data/geography_cli.py`, `tests/test_geography_build.py`, `tests/test_geography_cli.py`. Modify `src/embedding_data/cli.py:5` imports and subgroup registration after `codes` at line 31.

**Interfaces:** Consumes the complete four-identity registry and all previous pure transforms. Produces `build(data_dir: Path, run_id: str, *, registry=gr.REGISTRY) -> Path`, `SCHEMA_VERSION = 'geography-v1'`, `write_json(file, payload) -> None`, `report(tables, sources) -> dict`, and the `geography` command group. Final bundles contain exactly six Parquets and `inputs.json`, `report.json`, `outputs.json`; no source establishment/code bundle is read or rebuilt.

- [ ] **Step 1: Write failing build and CLI contracts.** In `tests/test_geography_build.py`:

```python
import json

import polars as pl
import pytest
from geography_fixtures import seed_geography_tree
from polars.testing import assert_frame_equal

from embedding_data import geography_build as gb, geography_references as gr, manifest


def test_full_bundle_exact_inventory_and_repeatability(tmp_path):
    registry = seed_geography_tree(tmp_path)
    one = gb.build(tmp_path, 'fixture_one', registry=registry)
    original_hashes = {f.name: manifest.sha256_file(f) for f in one.iterdir()}
    two = gb.build(tmp_path, 'fixture_two', registry=registry)
    assert {f.name: manifest.sha256_file(f) for f in one.iterdir()} == original_hashes
    expected = {name + '.parquet' for name in gb.SCHEMAS} | {'inputs.json', 'report.json'}
    assert {f.name for f in one.iterdir()} == expected | {'outputs.json'}
    inventory = json.loads((one / 'outputs.json').read_text())
    assert set(inventory) == expected
    for name, entry in inventory.items():
        assert entry == {'sha256': manifest.sha256_file(one / name),
                         'size': (one / name).stat().st_size}
    for name, schema in gb.SCHEMAS.items():
        a, b = pl.read_parquet(one / (name + '.parquet')), pl.read_parquet(two / (name + '.parquet'))
        assert a.schema == schema
        assert_frame_equal(a, b)
    inputs = json.loads((one / 'inputs.json').read_text())
    assert inputs['fixture'] is True
    assert inputs['schema_version'] == 'geography-v1'
    assert len(inputs['raw']) == 4
    assert 'src/embedding_data/geography_cli.py' in inputs['implementation']
    assert set(inputs['reference_frames']) == {'administrative', 'omb', 'hud'}
    report = json.loads((one / 'report.json').read_text())
    assert report['non_cbsa_counties'] == 1
    assert report['multi_state_cbsas'] == 1
    assert report['tables']['hud_zip_county.parquet']['rows'] == 12
    assert report['tables']['hud_zip_lookup.parquet']['rows'] == 9
    assert report['source_scope_exclusions']['county_rows'] == 1
    assert report['source_scope_exclusions']['membership_rows'] == 1


@pytest.mark.parametrize('run_id', ['../escape', 'bad/name', '', '.hidden', 'unicode_é'])
def test_unsafe_run_id_fails_before_build(tmp_path, run_id):
    with pytest.raises(ValueError, match='run ID'):
        gb.build(tmp_path, run_id)


@pytest.mark.parametrize('suffix', ['', '.part'])
def test_occupied_name_preserves_existing_bytes(tmp_path, suffix):
    registry = seed_geography_tree(tmp_path)
    occupied = tmp_path / 'derived/geography' / ('occupied' + suffix)
    occupied.mkdir(parents=True)
    (occupied / 'keep').write_bytes(b'unchanged')
    with pytest.raises(ValueError):
        gb.build(tmp_path, 'occupied', registry=registry)
    assert (occupied / 'keep').read_bytes() == b'unchanged'


def test_missing_input_never_acquires(tmp_path, monkeypatch):
    registry = seed_geography_tree(tmp_path)
    gr.reference_path(tmp_path, registry['cbsa_2023']).unlink()
    monkeypatch.setattr(gr, 'acquire', lambda *a, **k: pytest.fail('offline build acquired'))
    with pytest.raises((ValueError, FileNotFoundError)):
        gb.build(tmp_path, 'missing', registry=registry)
    assert not (tmp_path / 'derived/geography/missing').exists()


@pytest.mark.parametrize('defect', ['original', 'destination'])
def test_final_integrity_check_refuses_mid_build_changes(tmp_path, monkeypatch, defect):
    registry = seed_geography_tree(tmp_path)
    final = tmp_path / 'derived/geography/changed'
    write = gb.write_json

    def mutate(file, payload):
        write(file, payload)
        if file.name == 'outputs.json':
            if defect == 'original':
                gr.reference_path(tmp_path, registry['cbsa_2023']).write_bytes(b'changed')
            else:
                final.mkdir()
                (final / 'competitor').write_bytes(b'preserve')

    monkeypatch.setattr(gb, 'write_json', mutate)
    with pytest.raises(ValueError):
        gb.build(tmp_path, 'changed', registry=registry)
    assert not (final / 'geography_nodes.parquet').exists()
    assert (tmp_path / 'derived/geography/changed.part').exists()
    if defect == 'destination':
        assert (final / 'competitor').read_bytes() == b'preserve'
```

In `tests/test_geography_cli.py`:

```python
import httpx
import pytest
from geography_fixtures import seed_geography_tree
from typer.testing import CliRunner

from embedding_data import cli, geography_references as gr


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('network or credential access prohibited')

    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', forbidden)
    monkeypatch.setattr(cli.acs_benchmark_extract, 'load_dotenv', forbidden)
    monkeypatch.setattr(cli.cps_benchmark_extract, 'load_dotenv', forbidden)
    monkeypatch.delenv('IPUMS_API_KEY', raising=False)


@pytest.mark.parametrize('command', [[], ['acquire'], ['import-reference'], ['build']])
def test_geography_help(command):
    result = CliRunner().invoke(cli.app, ['geography', *command, '--help'])
    assert result.exit_code == 0
    assert 'Usage' in result.output


def test_cached_cli_and_offline_build(tmp_path, monkeypatch):
    registry = seed_geography_tree(tmp_path)
    monkeypatch.setattr(gr, 'REGISTRY', registry)
    runner = CliRunner()
    assert runner.invoke(cli.app, ['geography', 'acquire', '--data-dir', str(tmp_path)]).exit_code == 0
    result = runner.invoke(cli.app, ['geography', 'build', 'cli_fixture',
                                   '--data-dir', str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert (tmp_path / 'derived/geography/cli_fixture/outputs.json').exists()
    repeat = runner.invoke(cli.app, ['geography', 'build', 'cli_fixture',
                                   '--data-dir', str(tmp_path)])
    assert repeat.exit_code == 2
    assert 'already exists' in repeat.output


def test_missing_reference_is_actionable_without_traceback(tmp_path):
    result = CliRunner().invoke(cli.app, ['geography', 'build', 'missing', '--data-dir', str(tmp_path)])
    assert result.exit_code == 2
    assert 'missing manifested geography originals' in result.output
    assert 'Traceback' not in result.output
```

- [ ] **Step 2: Verify red.** Run `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_geography_build.py tests/test_geography_cli.py -q`. Expected: missing builder/CLI subgroup.
- [ ] **Step 3: Implement the builder and concise CLI boundary.** Create `geography_build.py`:

```python
import json
import re
import sys
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

import polars as pl

from embedding_data import geography_hud as gh, geography_references as gr, geography_tables as gt
from embedding_data import manifest, paths

SCHEMA_VERSION = 'geography-v1'
SCHEMAS = {**gt.SCHEMAS, **gh.SCHEMAS}


def write_json(file, payload):
    file.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + '\n',
                    encoding='utf-8')


def report(tables, sources):
    counties, cbsa = tables['county_reference'], tables['cbsa_reference']
    hud, lookup = tables['hud_zip_county'], tables['hud_zip_lookup']
    scoped_states = counties['state_fips'].unique().to_list()
    excluded_members = sources['members'].filter(pl.col('state_fips').is_in(scoped_states).not_())
    return {
        'schema_version': SCHEMA_VERSION, 'graph_validation': 'passed',
        'tables': {name + '.parquet': {'rows': frame.height,
                   'schema': {c: str(t) for c, t in frame.schema.items()}}
                   for name, frame in sorted(tables.items())},
        'cbsa_types': cbsa.group_by('cbsa_type').agg(
            n_cbsas=pl.len().cast(pl.Int64), n_counties=pl.col('n_counties').sum()).sort(
                'cbsa_type').to_dicts(),
        'multi_state_cbsas': cbsa.filter(pl.col('state_fips').list.len().gt(1)).height,
        'non_cbsa_counties': counties.filter(pl.col('cbsa_id').is_null()).height,
        'hud_statuses': lookup.group_by('eligibility_status').agg(
            n_zips=pl.len().cast(pl.Int64)).sort('eligibility_status').to_dicts(),
        'hud_candidate_diagnostics': {c: int(hud[c].sum()) for c in hud.columns
                                      if c.startswith('flag_') or c == 'noncounty_geography'},
        'hud_zip_diagnostics': {c: int(lookup[c].sum()) for c in lookup.columns if c.startswith('flag_')},
        'hud_unexpected_in_scope_county_codes': hud.filter(
            pl.col('flag_county_incompatible')).get_column('county_geoid').n_unique(),
        'source_scope_exclusions': {
            'state_rows': sources['excluded_states'].height,
            'county_rows': sources['counties'].height - counties.height,
            'membership_rows': excluded_members.height,
            'cbsa_codes_without_scoped_members': len(set(sources['members']['cbsa_code']) -
                                                      set(cbsa['cbsa_code'])),
        },
        'limits': ['2025 common administrative frame, not historical address geography',
                   'July 2023 OMB membership; both CBSA types retained',
                   'HUD 2025Q4 singleton eligibility only; maxima are diagnostics',
                   'No establishment assignment, target construction or PUMA allocation'],
    }


def build(data_dir: Path, run_id: str, *, registry=gr.REGISTRY) -> Path:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', run_id):
        raise ValueError('run ID must contain only ASCII letters, digits, underscore or hyphen')
    root = paths.derived_dir(data_dir, 'geography')
    final, staging = root / run_id, root / (run_id + '.part')
    for file in [final, staging]:
        gr.safe_path(file, data_dir)
        if gr.occupied(file):
            raise ValueError('run or staging name already exists')
    existing = gr.preflight(data_dir, registry)
    if not all(existing.values()):
        missing = [k for k, present in existing.items() if not present]
        raise ValueError(f'missing manifested geography originals: {missing}; acquire/import first')
    manifest_file = paths.manifest_path(data_dir)
    manifest_hash = manifest.sha256_file(manifest_file)
    citations = [asdict(manifest.entry_for(manifest_file, gr.reference_path(data_dir, r)))
                 for r in registry.values()]
    module_names = ['geography_parsers', 'geography_tables', 'geography_hud',
                    'geography_references', 'geography_build', 'geography_cli', 'cli',
                    'classification_tables', 'ita_references', 'manifest', 'paths',
                    'osha_benchmark_download']
    code_files = [Path(__import__('embedding_data.' + name, fromlist=['__file__']).__file__)
                  for name in module_names]
    code_hashes = {file.relative_to(paths.PROJECT_ROOT).as_posix(): manifest.sha256_file(file)
                   for file in sorted(code_files)}
    lock_hash = manifest.sha256_file(paths.PROJECT_ROOT / 'uv.lock')
    sources = gr.read_sources(data_dir, registry=registry)
    tables = gt.assemble(sources)
    tables['hud_zip_county'] = gh.annotate(sources['hud'], tables['county_reference'])
    tables['hud_zip_lookup'] = gh.lookup(tables['hud_zip_county'])
    gt.validate_tables(tables, sources)
    root.mkdir(parents=True, exist_ok=True)
    staging.mkdir()
    for name, frame in tables.items():
        if frame.schema != SCHEMAS[name]:
            raise ValueError(f'{name}: incompatible output schema')
        frame.write_parquet(staging / (name + '.parquet'))
    published = {name: pl.read_parquet(staging / (name + '.parquet')) for name in SCHEMAS}
    gt.validate_tables(published, sources)
    for name in SCHEMAS:
        if published[name].schema != SCHEMAS[name] or not published[name].equals(tables[name]):
            raise ValueError(f'{name}: serialized content or schema differs')
    inventory = {
        'schema_version': SCHEMA_VERSION, 'run_id': run_id,
        'fixture': any(r.fixture for r in registry.values()),
        'reference_frames': {'administrative': '2025', 'omb': 'July 2023', 'hud': '2025Q4'},
        'raw': sorted(citations, key=lambda r: r['path']),
        'references': {k: {**asdict(r), 'state_scope': sorted(r.state_scope)}
                       for k, r in sorted(registry.items())},
        'implementation': code_hashes,
        'dependencies': {name: version(name) for name in ['embedding-data', 'polars', 'fastexcel',
                                                         'httpx', 'typer']},
        'python': sys.version,
        'uv_lock_sha256': lock_hash,
    }
    write_json(staging / 'inputs.json', inventory)
    write_json(staging / 'report.json', report(published, sources))
    names = [name + '.parquet' for name in SCHEMAS] + ['inputs.json', 'report.json']
    write_json(staging / 'outputs.json', {
        name: {'sha256': manifest.sha256_file(staging / name), 'size': (staging / name).stat().st_size}
        for name in sorted(names)})
    if manifest.sha256_file(manifest_file) != manifest_hash:
        raise ValueError('raw manifest changed during geography build')
    for citation in citations:
        file = manifest_file.parent / citation['path']
        current = asdict(manifest.entry_for(manifest_file, file))
        if current != citation:
            raise ValueError('cited original changed during geography build')
    if any(manifest.sha256_file(paths.PROJECT_ROOT / name) != checksum
           for name, checksum in code_hashes.items()) or (
            manifest.sha256_file(paths.PROJECT_ROOT / 'uv.lock') != lock_hash):
        raise ValueError('implementation or lockfile changed during geography build')
    gr.preflight(data_dir, registry)
    gr.safe_path(final, data_dir)
    if gr.occupied(final):
        raise ValueError('run destination appeared during build')
    staging.rename(final)
    return final
```

Create `geography_cli.py`:

```python
from pathlib import Path
from zipfile import BadZipFile

import httpx
import polars as pl
import typer
from fastexcel import FastExcelError

from embedding_data import geography_build, geography_references, paths

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@app.callback()
def geography():
    '''Acquire official geography originals and build immutable offline reference bundles.'''


def invoke(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except (OSError, ValueError, KeyError, BadZipFile, httpx.HTTPError,
            pl.exceptions.PolarsError, FastExcelError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(2) from None


@app.command('acquire')
def acquire(data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')):
    for file in invoke(geography_references.acquire, data_dir,
                       registry=geography_references.REGISTRY):
        typer.echo(file)


@app.command('import-reference')
def import_reference(kind: str, file: Path,
                     data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')):
    typer.echo(invoke(geography_references.import_reference, data_dir, kind, file,
                      registry=geography_references.REGISTRY))


@app.command('build')
def build(run_id: str, data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')):
    typer.echo(invoke(geography_build.build, data_dir, run_id,
                      registry=geography_references.REGISTRY))
```

In `cli.py`, replace its existing `from embedding_data import (...)` block with:

```python
from embedding_data import (
    acs_benchmark_extract,
    codes_cli,
    cps_benchmark_extract,
    geography_cli,
    manifest_audit,
    osha_benchmark_download,
)
```

Add this line after `app.add_typer(codes_cli.app, name='codes')`:

```python
app.add_typer(geography_cli.app, name='geography')
```

The code inventory intentionally includes the CLI and reused parser/schema modules. Import these modules only after their definitions exist; module import does not execute acquisition or load credentials. JSON source citations use the existing provenance dataclass, while reference scope is converted to a sorted JSON list.

- [ ] **Step 4: Run green and the second full milestone.** Run focused build/CLI tests, then the complete four-command group in Durable testing strategy. Expected: all pass; no production inputs/outputs changed. Confirm errors from malformed ZIP/XLSX originals are concise exit-2 messages. Preserve failed staging for inspection; no automatic deletion or reuse of occupied names.
- [ ] **Step 5: Commit and review publication/CLI.**

```bash
git add src/embedding_data/geography_build.py src/embedding_data/geography_cli.py src/embedding_data/cli.py tests/test_geography_build.py tests/test_geography_cli.py
git commit -m 'feat(geography): publish verified offline geography bundles'
```

### Task 6: Verified production acceptance, documentation, review and stage completion

**Files:** Create `specs/findings/stage-5-geography-reference-build.md`; modify `README.md`, `CLAUDE.md`; after all exit gates/review resolution modify this plan, `specs/deferred_items.md` as applicable, and Stage 5's entry in `specs/embedding-evaluation-data-spec-roadmap.md`. Retire this plan and the stage spec through writing-plans' Plan Completion Protocol. The source spec and roadmap remain live.

**Interfaces:** Consumes reviewed Tasks 1–5, the four pinned public originals and the real data root. Produces explicitly selected `data/derived/geography/stage5_geography_20261013/`, independent comparison bundle `stage5_geography_20261013_repeat/`, a committed measured finding and an actual-shipped Handoff. If either run name is occupied, retain it and select two new safe names consistently in the acceptance commands/finding/Handoff; never delete or reuse an earlier bundle.

- [ ] **Step 1: Capture protected artifacts, then import/acquire the original references.** These are execution-only production commands. Run from the execution worktree; every production command supplies the original checkout's data directory. No OSHA download, summary rebuild, verification sample/geocode command, or codes build is part of acceptance.

Capture the source summary and every Stage 3/4 artifact's bytes before acquisition/build:

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python - <<'PY'
import json
from pathlib import Path
from embedding_data import manifest

data = Path('/Users/lowell/Projects/embedding-data/data')
files = [data / 'derived/osha/ita_300a_summary.parquet']
for directory in [data / 'derived/osha/verification', data / 'derived/codes',
                  data / 'raw/references']:
    files.extend(sorted(file for file in directory.rglob('*') if file.is_file()))
assert all(file.is_file() for file in files)
receipt = {str(file): {'sha256': manifest.sha256_file(file), 'size': file.stat().st_size}
           for file in files}
Path('/private/tmp/stage5-geography-protected-before.json').write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(f'Protected {len(receipt)} source/verification/classification/original-reference files')
PY
```

Optional original-cache imports avoid re-downloading the two inspected Census originals. Check these files against the preflight/personal `MANIFEST.md` source/hash records first; the new registered pins independently enforce exact bytes. Import only the original files below, never skill-derived CSVs. If the cache paths are unavailable, omit the two import commands and let `acquire` fetch their registered official URLs. The state workbook is acquired freshly from its official URL; do not depend on the temporary planning file.

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data geography import-reference counties_2025 /Users/lowell/.agents/skills/geographic-codes/sources/2025_Gaz_counties_national.zip --data-dir /Users/lowell/Projects/embedding-data/data
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data geography import-reference cbsa_2023 /Users/lowell/.agents/skills/geographic-codes/sources/2023_list1_2023.xlsx --data-dir /Users/lowell/Projects/embedding-data/data
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --locked embedding-data geography acquire --data-dir /Users/lowell/Projects/embedding-data/data
```

`uv --offline` controls package resolution, not HTTP inside the application. The acquire command deliberately may fetch only missing registered Census originals. It uses no credential; HUD is already manifested. If HUD is absent, stop acquisition and import the registered 2025Q4 original through `geography import-reference hud_2025q4 ORIGINAL --data-dir ...`; no different quarter/bytes satisfy this production identity. A source pin mismatch is a source-identity/design issue to record and resolve, never a reason to replace old bytes or loosen the pin.

Expected: all four raw paths are manifest-covered, source URLs/hashes/sizes match the preflight, cached references are untouched, and re-running cached acquisition performs zero HTTP requests as covered by Task 4.

- [ ] **Step 2: Build two new bundles offline.**

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data geography build stage5_geography_20261013 --data-dir /Users/lowell/Projects/embedding-data/data
```

Expected: the first command exits 0, prints its final directory, and leaves no partial. Capture this bundle's nine physical hashes before building the comparison run:

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python - <<'PY'
import json
from pathlib import Path
from embedding_data import manifest

one = Path('/Users/lowell/Projects/embedding-data/data/derived/geography/stage5_geography_20261013')
Path('/private/tmp/stage5-geography-first-bundle.json').write_text(json.dumps(
    {f.name: {'sha256': manifest.sha256_file(f), 'size': f.stat().st_size}
     for f in sorted(one.iterdir())}, sort_keys=True, indent=2) + '\n')
PY
```

Then build the comparison run:

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data geography build stage5_geography_20261013_repeat --data-dir /Users/lowell/Projects/embedding-data/data
```

Expected: exit 0, a distinct final directory containing nine files, and no comparison partial. Verify first-run physical immutability and logical equality with Step 3.

- [ ] **Step 3: Verify full-data acceptance and generate the measured finding only on success.** Run this complete verifier after both builds. It asserts exact inspected-production counts, typed source parity and all original/physical inventories; it compares logical table content rather than assuming separate Parquet files are byte-identical. All failures must be resolved or explicitly returned to the owner; a fixture pass cannot replace this gate.

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python - <<'PY'
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl
from polars.testing import assert_frame_equal

from embedding_data import geography_build as gb, geography_hud as gh
from embedding_data import geography_references as gr, geography_tables as gt
from embedding_data import manifest, paths

data = Path('/Users/lowell/Projects/embedding-data/data')
one = data / 'derived/geography/stage5_geography_20261013'
two = data / 'derived/geography/stage5_geography_20261013_repeat'
expected_names = {n + '.parquet' for n in gb.SCHEMAS} | {'inputs.json', 'report.json', 'outputs.json'}
sources = gr.read_sources(data)
tables = {n: pl.read_parquet(one / (n + '.parquet')) for n in gb.SCHEMAS}
gt.validate_tables(tables, sources)
for name, schema in gb.SCHEMAS.items():
    assert tables[name].schema == schema, name
    assert_frame_equal(tables[name], pl.read_parquet(two / (name + '.parquet')))
assert_frame_equal(tables['hud_zip_county'].select(list(gh.NORMALIZED_SCHEMA)), sources['hud'])
assert_frame_equal(tables['hud_zip_lookup'], gh.lookup(tables['hud_zip_county']))
nodes, edges = tables['geography_nodes'], tables['geography_edges']
county, cbsa = tables['county_reference'], tables['cbsa_reference']
assert nodes.height == 4133 and edges.height == 5048
assert nodes.filter(pl.col('level').eq('state')).height == 51
assert nodes.filter(pl.col('level').eq('division')).height == 9
assert nodes.filter(pl.col('level').eq('region')).height == 4
assert county.height == 3144 and cbsa.height == 925
ct = county.filter(pl.col('state_fips').eq('09'))
assert set(ct['county_geoid']) == {f'091{i}0' for i in range(1, 10)}
assert not set(county['state_fips']) & gr.gp.EXCLUDED
assert cbsa.filter(pl.col('cbsa_type').eq('metropolitan')).height == 387
assert cbsa.filter(pl.col('cbsa_type').eq('micropolitan')).height == 538
assert county.filter(pl.col('cbsa_type').eq('metropolitan')).height == 1186
assert county.filter(pl.col('cbsa_type').eq('micropolitan')).height == 658
assert county.filter(pl.col('cbsa_id').is_null()).height == 1300
assert cbsa.filter(pl.col('state_fips').list.len().gt(1)).height == 59
assert edges.filter(pl.col('edge_type').eq('county_state')).height == 3144
assert edges.filter(pl.col('edge_type').eq('state_division')).height == 51
assert edges.filter(pl.col('edge_type').eq('division_region')).height == 9
assert edges.filter(pl.col('edge_type').eq('county_cbsa')).height == 1844
assert tables['hud_zip_county'].height == 54571
assert tables['hud_zip_lookup'].height == 39494
assert tables['hud_zip_county'].filter(pl.col('flag_county_incompatible')).is_empty()
assert tables['hud_zip_lookup'].filter(pl.col('n_business_counties').ne(1).and_(
    pl.col('zip_fallback_county').is_not_null())).is_empty()
assert tables['hud_zip_lookup'].filter(pl.col('eligibility_status').ne('eligible').and_(
    pl.col('zip_fallback_county').is_not_null())).is_empty()
assert sources['counties'].height == 3222
assert sources['members'].height == 1915
assert sources['members']['cbsa_code'].n_unique() == 935
for bundle in [one, two]:
    assert {f.name for f in bundle.iterdir()} == expected_names
    assert not bundle.with_name(bundle.name + '.part').exists()
    inputs = json.loads((bundle / 'inputs.json').read_text())
    report = json.loads((bundle / 'report.json').read_text())
    outputs = json.loads((bundle / 'outputs.json').read_text())
    assert inputs['fixture'] is False
    assert inputs['schema_version'] == report['schema_version'] == 'geography-v1'
    assert report == gb.report(tables, sources)
    assert report['hud_unexpected_in_scope_county_codes'] == 0
    assert report['source_scope_exclusions']['county_rows'] == 78
    assert report['source_scope_exclusions']['membership_rows'] == 71
    assert report['source_scope_exclusions']['cbsa_codes_without_scoped_members'] == 10
    assert set(outputs) == expected_names - {'outputs.json'}
    for name, record in outputs.items():
        assert record == {'sha256': manifest.sha256_file(bundle / name),
                          'size': (bundle / name).stat().st_size}
    cited = {r['path']: r for r in inputs['raw']}
    assert len(cited) == 4
    for reference in gr.REGISTRY.values():
        entry = asdict(manifest.entry_for(paths.manifest_path(data), gr.reference_path(data, reference)))
        assert (entry['sha256'], entry['size']) == (reference.sha256, reference.size)
        assert entry['source_url'] == reference.url
        # JSON represents tuple-valued provenance fields as arrays.
        assert cited[entry['path']] == json.loads(json.dumps(entry))
    assert inputs['uv_lock_sha256'] == manifest.sha256_file(paths.PROJECT_ROOT / 'uv.lock')
    for relative, checksum in inputs['implementation'].items():
        assert manifest.sha256_file(paths.PROJECT_ROOT / relative) == checksum
before = json.loads(Path('/private/tmp/stage5-geography-protected-before.json').read_text())
for path, record in before.items():
    file = Path(path)
    assert {'sha256': manifest.sha256_file(file), 'size': file.stat().st_size} == record
first = json.loads(Path('/private/tmp/stage5-geography-first-bundle.json').read_text())
assert {f.name: {'sha256': manifest.sha256_file(f), 'size': f.stat().st_size}
        for f in one.iterdir()} == first
inputs = json.loads((one / 'inputs.json').read_text())
report = json.loads((one / 'report.json').read_text())
lines = [
    '# Stage 5 production geography reference build', '',
    f'Measured {datetime.now(ZoneInfo("America/New_York")).date().isoformat()} '
    'after implementation; schema `geography-v1`.', '',
    f'Selected bundle: `data/{one.relative_to(data).as_posix()}/`.',
    f'Logical-repeat bundle: `data/{two.relative_to(data).as_posix()}/`.',
    f'Detached outputs.json SHA-256: `{manifest.sha256_file(one / "outputs.json")}`.', '',
    'All four original citations, software hashes, lock identity and eight detached output '
    'entries were verified. Source summary and all captured Stage 3/4 files are unchanged; '
    'the first bundle retained its nine original physical hashes after the second build.', '',
    '## Original citations', '', '| Path | Edition | Bytes | SHA-256 |',
    '| --- | --- | ---: | --- |',
]
for kind, reference in sorted(gr.REGISTRY.items()):
    lines.append(f'| raw/references/{reference.relative} | {reference.edition} | '
                 f'{reference.size} | `{reference.sha256}` |')
lines.extend(['', '## Exact schemas and counts', '', '```json',
              json.dumps(report['tables'], indent=2, sort_keys=True), '```', '',
              '## Graph, scope and HUD diagnostics', '', '```json',
              json.dumps({k: v for k, v in report.items() if k not in ['tables', 'limits']},
                         indent=2, sort_keys=True), '```', '',
              '## Limits and downstream contract', '',
              'The administrative frame is 2025, OMB membership is July 2023, and HUD is '
              '2025Q4. This is a common-frame reference, not historical county geography '
              'for older filing addresses. Both metropolitan and micropolitan CBSAs are '
              'included; no CBSA has a forced state parent. County inventory includes '
              'counties with no CBSA membership and counties without positive HUD share.', '',
              'HUD rows/ratios and every ZIP are retained. Positive candidates are counted '
              'before scope/compatibility checks; mixed valid/excluded candidates remain '
              'ambiguous. Dominant shares are diagnostic. Only an eligible original '
              'singleton supplies zip_fallback_county. Missing ZIP and all-zero ZIP are '
              'distinct. Scope/legacy/noncounty flags remain independent.', '',
              'Stage 6 must verify and select this complete bundle, preserve Stage 3 exact '
              'Census-first precedence and delivered-state exclusion, and perform full '
              'establishment assignment. Stage 8 owns PUMA allocation/V8. No relatedness '
              'target or allocation is inferred here. Future Census Current calls may '
              'change; these reference bytes do not freeze address-service responses.', '',
              'Requirements: [source spec](../embedding-evaluation-data-spec.md) '
              'R2.8/R6.1/R6.2/R6.4 and the Stage 5 design. '
              'Layout evidence: [preflight](stage-5-geography-reference-preflight.md).', ''])
finding = paths.PROJECT_ROOT / 'specs/findings/stage-5-geography-reference-build.md'
finding.write_text('\n'.join(lines), encoding='utf-8')
print(json.dumps({'selected': str(one), 'finding': str(finding),
                  'nodes': nodes.height, 'edges': edges.height,
                  'counties': county.height, 'cbsas': cbsa.height,
                  'hud_rows': tables['hud_zip_county'].height,
                  'hud_zips': tables['hud_zip_lookup'].height,
                  'protected_files': len(before)}, indent=2))
PY
```

Use America/New_York for the finding/completion date if host local time differs. Review the generated finding against fresh command output, including all schemas, source exclusions, status/flag counts and limits. If final review changes code, rebuild with new safe run IDs and regenerate this evidence against the reviewed implementation; never relabel an old run as the new code.

- [ ] **Step 4: Document shipped commands and consumer selection, then rerun checks.** Append the following section to `README.md` in the command/reference area:

````markdown
## Geography reference bundles

`geography acquire` verifies every registered destination before downloading missing
official Census originals. HUD 2025Q4 is imported separately when absent:

```bash
uv run embedding-data geography import-reference hud_2025q4 ZIP-COUNTY_122025.xlsx --data-dir data
uv run embedding-data geography acquire --data-dir data
uv run --offline --locked embedding-data geography build NEW_RUN_ID --data-dir data
```

Use the intended data root explicitly when running from a worktree. Existing originals,
final run names and `.part` names are immutable. Cached acquisition makes no HTTP request;
build is offline and refuses missing or changed manifested inputs. Changed original bytes
require a distinct source identity and recorded decision.

Each `derived/geography/<run_id>/` bundle contains six Parquets: `geography_nodes`,
`geography_edges`, `county_reference`, `cbsa_reference`, `hud_zip_county`, and
`hud_zip_lookup`, plus `inputs.json`, `report.json`, and detached `outputs.json`.
Select a complete run explicitly and verify its inventories; there is no latest alias.
The [production finding](specs/findings/stage-5-geography-reference-build.md) records
the selected run, original hashes, schemas, counts and limitations.

Administrative nodes use the 2025 frame. Both July 2023 metropolitan and micropolitan
CBSA memberships are present; counties outside all CBSAs remain in the county reference.
Administrative edges and county-to-CBSA edges are separate typed relationships. HUD
2025Q4 retains all candidates and ZIPs, including zero-business ZIPs. Only an original,
compatible positive singleton is eligible for fallback; a dominant share is diagnostic.
Missing ZIPs differ from present all-zero ZIPs. Full establishment assignment and PUMA
allocation are later stages; these references do not assert historical address geography.
````

In `CLAUDE.md`, replace the exact sentence:

```text
Geography allocation, ACS/CPS code parsers, targets and the shared target writer remain planned.
```

with:

```text
Geography reference bundles now supply the complete 2025 county inventory, July 2023 metropolitan/micropolitan membership and 2025Q4 HUD eligibility; PUMA allocation, full establishment assignment, ACS/CPS code parsers, targets and the shared target writer remain planned.
```

Add this paragraph after the Stage 4 bundle guidance:

```markdown
**Geography bundle (Stage 5).** `geography acquire` and `geography import-reference KIND FILE`
register verified original bytes; `geography build RUN_ID --data-dir ROOT` builds offline.
Use the real root explicitly in worktrees. The selected production run and its original,
software and output inventories are in
`specs/findings/stage-5-geography-reference-build.md`. Six Parquets use `geography-v1`,
shared node/edge schemas and dedicated geography validation. Both metro and micro CBSAs
retain type and central/outlying roles; their counties may span states. Complete county
inventory is independent of HUD/CBSA coverage. HUD retains every ZIP and row; compute
eligibility from all original positive candidates before scope checks. `zip_dominant_county`
is diagnostic; only `eligible` has `zip_fallback_county`. Preserve Stage 3 selector/importer
interfaces and exact Census-first/delivered-state rules. This stage supplies references;
Stage 6 assigns establishments and Stage 8 allocates PUMAs. Never rebuild source summaries,
Stage 3 verification artifacts or Stage 4 code bundles to prepare geography references.
```

Run the complete four-command group in Durable testing strategy, inspect output, and run `git diff --check`. Commit the finding/docs with:

```bash
git add specs/findings/stage-5-geography-reference-build.md README.md CLAUDE.md
git commit -m 'docs(geography): record verified production bundle and consumer limits'
```

- [ ] **Step 5: Resolve final review and completion leftovers before any stage tick.** Use requesting-code-review on the whole execution branch against this plan and stage spec, then receiving-code-review to assess findings. Fix material findings and rerun relevant checks/production acceptance if code changes. Batch owner questions for genuinely blocked leftovers; do not tick/retire while unanswered. Apply writing-plans' resolve-before-defer gate, close any prior backlog items actually delivered by this plan, and append only consciously deferred items with paths, size and closure conditions. No currently open ledger item is intentionally solved by this plan; no empty deferred section is appended.

- [ ] **Step 6: Record actual-shipped Handoff for every later stage, tick/stamp Stage 5, and retire.** Once all preceding gates hold, apply writing-plans' Plan Completion Protocol and verification-before-completion. Record what shipped from the deviation ledger as well as final code; an interim interface later reverted still belongs in the applicable bullet. Cite the stage spec/finding rather than restating requirements. Do not pre-fill this section with completion claims during planning.

The final `## Handoff to later stages` must cover each remaining entry:

| Later stage | Required actual-shipped audit in plan 5's Handoff |
| --- | --- |
| 6 | Exact selected geography run and verified inventories; all six names/schemas and `geography-v1`; full county/CBSA lookup, four edge types and vintages; metro/micro/non-CBSA and multi-state semantics; `hud_zip_lookup` singleton/zero-share/absent/compatibility contracts. Preserve Stage 3 method precedence and separate delivered-state veto; full-table assignment/Census acquisition and targets remain here. Stage 4 canonical data stays separate. |
| 7 | This stage's manifest-backed geography references do not verify IPUMS extracts, sample/weight rules or historical delivery versions. Record unchanged dependencies or actual cross-cutting provenance differences/deferred items. |
| 8 | Complete `county_reference`, county nodes and typed county-to-CBSA membership from one selected bundle, including CT planning regions and both types. Name `cbsa_reference.state_fips` as a member-derived set. PUMA factors/intersections/V8 remain future work; common-frame references do not resolve historical PUMA compatibility. |
| 9 | Consume Stage 5 rollups/typed relationships through the selected bundle and Stage 8 allocations; preserve both CBSA types and absence of membership. No forced CBSA state parent, MET2023-only metro assignment, majority allocation or relatedness target supplied by this build. |
| 10 | Stage 5 adds no employer/linkage/text inclusion rule. Existing Stage 3/4/6 dependencies persist; record unchanged scope or any actual shared-interface difference. |
| 11 | Stage 5 adds no CPS scheme, linkage or weight rule; keep Stage 4 classification validation separate from geography. Existing Stage 6/7 dependencies persist. |
| 12 | Later geographic outputs must preserve metro/micro type, common-frame limits and R4.4 CPS metro eligibility independently; this geography reference does not make every CPS record metro-eligible. Existing Stage 9/11 helpers remain the dependency. |
| 13 | Name the selected geography bundle's verified raw/software/output inventories and production finding, plus logical repeatability versus physical run hashes. Stage 5 supplies no target family, V9 gate or IPUMS/comparator verification. |

For each row state differences from Stage 5's roadmap `Produces`, actual traps/refusals, and any deferred item by its `specs/deferred_items.md` section; say explicitly when none applies. Cross-cutting traps include the classification single-parent refusal, Excel header indexing and strict footer handling, HUD logical basename, all-positive-before-filtering rule, and separately stamped reference frames. This table is the completion checklist, not a claim that those interfaces have shipped.

Tick only Stage 5's `- [ ]` box in `specs/embedding-evaluation-data-spec-roadmap.md`, preserving the entry's content, and place this stamp beneath it using the actual completion date:

```text
> Stage 5: COMPLETE (2026-10-13) — implemented by plan 5 (specs/plans/completed/5-geography-hierarchy-county-reference.md). Its Handoff section revalidates Stages 6–13.
> Next: resume the roadmap.
```

The date above is the planning date; substitute the verified execution completion date when different. Mark completed plan steps, add actual deviation/skipped notes and the complete status header, then run:

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --no-project --python 3.13 python /Users/lowell/.agents/skills/writing-plans/scripts/deferred_stats.py
```

Report backlog open count/closure rate/aged tail; apply the read-only triage proposal if its threshold is met. Move this plan to `specs/plans/completed/` and, when no other live plan implements it, mark and move the stage spec to `specs/completed/`. Re-point their relative links at the new depth, including the stage spec's roadmap/source/preflight links, and Stage 5's live stage-design path to the retired spec. Commit the retirement as `chore(specs): retire plan 5`. Perform finishing-a-development-branch only after this completion chain; choose integration deliberately and clean the execution worktree.

Revalidating later stages in this execution session means the actual-shipped Handoff above. Reconcile later roadmap entries from those bullets through derive-roadmap on the next resume; do not rewrite, add/split/drop/reorder, design or plan a later stage here. End with `Next: resume the roadmap.`

## Self-review and execution handoff

Spec coverage: scope/reference boundaries and original parsing are covered by Global Constraints and Tasks 1/4; graph and county/CBSA contracts by Task 2; HUD candidate/eligibility and method boundaries by Task 3; deterministic build/provenance and publication by Task 5; offline/regression/full-data acceptance, documentation and rollout/completion by Task 6. The source spec/roadmap remain live. No requirement is deferred by this plan.

The placeholder scan is clear. Function names, reference keys, schemas, registry fields, output filenames and CLI arguments are consistent across tasks and were exercised in a temporary fixture rehearsal. Production verifier scripts parse; their acceptance assertions must still run against published production bundles during execution. The preflight is design evidence, and the temporary read-only transform rehearsal does not meet the production gate.

Plan review is approved by D1. Recommended execution handoff: `/clear` or a fresh session, then subagent-driven-development on this file. Its six explicit interfaces and independently reviewable parser, graph, HUD, I/O and publication contracts suit fresh task workers. Inline execution through executing-plans is also available if the owner chooses it; continue in task order with the same milestone/review/completion gates.
