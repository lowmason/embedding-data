# TRI Parent Links Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one verified bundle that relates NAICS 2022 industries through shared EPA
TRI U.S. parents (O7) and lists each parent's industries (O8), from the RY2022–2024
basic data files.

**Architecture:** A standalone command group `python -m embedding_data.tri_parent_links`
(spec approach 1). New modules import reused ones unchanged. A preflight settles E7–E9 on
the recorded raw files and records each year's header layout before the reader, the
estimators and the bundle are written against it. One offline build reduces form rows to
facility-years, derives the O7 target, its companions and the O8 table, and publishes an
exclusive `.part` directory by rename.

**Tech Stack:** Python 3.14, Polars (lazy), Typer, httpx (acquisition only), pytest, uv.

**Spec:** `specs/tri-parent-links.md` (owner-approved 2026-11-18; approved text at
`61b3c4b`, on `main` at merge `e6e12b2`).

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 5 — on plan completion, tick the stage and re-validate later stages against what shipped.

Scope: O7, O8 (first build). Leaves out O12 (replay build, full-data `compare-runs`,
long-form finding, README and `CLAUDE.md` run pins), O13 (minimum count) and O17
(protocol section).

Process: lighter (Stage 2 spec, "Rules for every new family"): one full-data build,
`verify`, the independent reconciler and a one-screen findings file. The controller runs
the two gated tasks (4 and 13) and Task 14 itself, because a dispatched subagent cannot
ask the owner for a go-ahead.

## Global Constraints

- **Stage numbers.** This plan is Stage 5 of `specs/naics-evaluation-data-roadmap.md`.
  Stage numbers in `CLAUDE.md` and in code are the old roadmap's: Stage 4 codes bundle,
  Stage 6 area mix, Stage 9 ACS, Stage 10 ITA establishment.
  `specs/plans/completed/5-geography-hierarchy-county-reference.md` is unrelated.
- **Branch.** Execute on a new branch cut from `main` at or after the merge that brings
  this plan, in a worktree under `.claude/worktrees/`.
- **Window.** Reporting years `(2022, 2023, 2024)`, native NAICS 2022, EPA's complete
  dataset only. The basic data files page is
  `https://www.epa.gov/toxics-release-inventory-tri-program/tri-basic-data-files-calendar-years-1987-present`.
  Preliminary-dataset pages are out of scope. The old 2024 preliminary URL redirects to
  `.../2025-tri-preliminary-dataset-basic-data-files`, and `acquire` never reads it.
- **Codes identity.** Codes run `stage4_v11_20261013_r2`, detached `outputs.json` SHA-256
  `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`. Stage 5 reads its
  `naics_nodes.parquet` only. Node IDs look like `naics:2022:national_industry:111110`.
- **Contract versions (verbatim).** `tri-facility-years-v1`, `tri-parent-links-v1`,
  `targets-v1`, and the header layout version `tri-headers-v1`.
- **Target metadata (verbatim).** `source` `epa_tri`, `family` `tri_parent_links`,
  `unit_a_type` and `unit_b_type` `naics_national_industry`, `measure` `owner_share`,
  `se` null, `se_method` `none`, `sample_set` `tri_basic_ry2022_2024`, `vintage`
  `naics=2022`. Labels: `size_gate_pending` on every row,
  `numerator:dnb_key_sensitivity:true`, `numerator:federal_sensitivity:true`.
- **Universe (verbatim, `{date}` is the ISO snapshot date).** "EPA Toxics Release
  Inventory basic data files, U.S. files for reporting years 2022–2024, forms processed
  as of {date}. TRI is a program-selected population of facilities that meet its
  reporting criteria, not a frame of all establishments or firms. Codes are self-reported
  primary NAICS 2022 codes, one per facility. A facility can contain more than one
  establishment. An owner is EPA's standardized highest-level U.S. parent, or the
  facility itself when it reports none. Federal facilities are excluded."
- **Paths.** Raw files: `data/raw/epa_tri/basic/<RY>/<processed-as-of, ISO>/<EPA file name>`.
  Bundles: `data/derived/epa_tri/parent-links/<RUN_ID>/`. Findings:
  `specs/naics-evaluation-data-stage-5-findings.md`.
- **Runs.** Run IDs match `[A-Za-z0-9][A-Za-z0-9_-]*`. An existing final or
  `<RUN_ID>.part` fails. A later run never reuses, overwrites or deletes it.
- **Offline.** `import-file`, `build`, `verify` and `compare-runs` load no `.env`, read no
  credential, construct no HTTP client and run no upstream builder. Only `acquire` uses
  the network.
- **Diagnostics.** Success prints one sorted JSON line. Failure prints only
  `TRI parent links <command> failed: <reason>; run <run_id>; path <path>` to stderr and
  exits 2. `<reason>` is `validation`, `filesystem`, `network` or `unexpected`. It never
  prints exception text or row content. Unequal `compare-runs` exits 1.
- **No D&B numbers out.** No bundle file, report, success line or failure line holds a
  Dun & Bradstreet number. D&B numbers exist only in memory during a build.
- **Frozen code.** Edit no existing file under `src/` or `scripts/`, no existing test file,
  no `tests/conftest.py`, `pyproject.toml` or `uv.lock`. Stage 5 adds files only. Add no
  dependency. If a reused function cannot serve unchanged, stop and ask the owner.
- **Reused interfaces, imported unchanged.** `target_contract.write_targets`,
  `validate_targets`, `TARGET_SCHEMA`, `TARGET_KEY_COLUMNS`; `target_io.stage`,
  `relative_file`, `file_record`, `inventory`, `verify_inventory`, `write_json`;
  `manifest.describe_file`, `append_entries`, `check_appendable`, `entry_for`,
  `read_manifest`, `sha256_file`; `paths`; `osha_encoding.decode_line`;
  `geography_references.safe_path`, `occupied`. Tests may also import
  `tests/ita_establishment_fixtures.py`, `tests/ita_fixtures.py`, `code_build`,
  `ita_summary`, `target_inputs` and `classification_tables`, and never edit them.
- **Import closure.** `target_io` imports `geography_references`, which imports
  `osha_benchmark_download`, `ita_references` and `geography_parsers`. Those modules load
  but are never called. `SOFTWARE_FILES` is the measured closure (Task 9 and Task 10
  tests), not a hand list. Importing the command module loads neither `dotenv` nor
  `ipumspy`.
- **`through_date` reuse.** Stage 5 manifest entries put EPA's "processed as of" date in
  `through_date`. The frozen docstring at `src/embedding_data/manifest.py:8` says the field
  is "the submission through-date an OSHA ITA summary file's name carries". This plan and
  the findings file record the departure. Planning-time search, 2026-11-18:
  `grep -rn through_date src scripts features` matches only `manifest.py:8, 31, 51, 68`,
  `ita_catalog.py:91, 122` (parses file names), `ita_summary.py:46, 320` (the same parser),
  `osha_benchmark_download.py:237` (writes) and `code_build.py:323` (lists `ita_catalog`
  for hashing). `grep -rnE "\.through_date|\['through_date'\]" src scripts` finds no
  reader. Only tests read the field, and only for OSHA or the manifest
  (`tests/test_osha_benchmark_download.py:375, 425`, `tests/test_manifest.py:144, 162`).
  These sites copy whole entries with `asdict` and carry the field unread:
  `code_build.py:46-47`, `geography_build.py:77, 128`, `ipums_verification_run.py:111`,
  `ita_index_references.py:263`, `target_io.py:91`, `target_inputs.py:205`,
  `ita_verification_run.py:47, 193, 203` and `ita_establishment_bundle.py:279`.
  `target_io.verify_raw` compares whole entries, so the field is part of citation equality
  there, not a read.
- **Host rule (spec).** Run one acquisition at a time, because
  `manifest.append_entries` checks and then appends with no lock. Run one full-data
  build at a time. Before each acquisition and each full-data build:
  1. Run `pgrep -fl 'embedding_data|embedding-data'` and show the owner its full,
     unfiltered output. It can match editors or agents whose command line holds the
     project path. The owner judges, and the run stops if it shows another acquisition
     or build.
  2. Run `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`.
     Stop if it prints anything.
  3. The owner confirms that no other stage's acquisition or build is running and that
     no Stage 9 freeze window is open. Evidence: `scripts/stage9_independent_io.py:144-146`
     inventories every file under `raw/` and `derived/`. Lines 285-292 fail on a new
     file that no manifest append explains (`'unaccounted new immutable files'`). A
     manifest-recorded TRI raw file passes. A bundle or a leftover `.part` fails.
- **Commit protocol.** Before every commit and every full `pytest` run, run the Stage 9
  `pgrep` check above. If it prints anything, stop, leave the files uncommitted and tell
  the owner. Never skip a hook. `git add` only the task's files: the main checkout holds
  the owner's untracked `specs/SAM.gov-Signed-Terms-of-Use.pdf`.
- **Merging.** Stage 9's checker hashes every `.py` file under `src`, `scripts`, `tests`
  and `features` of the checkout it runs from. The PR merges under the owner's standing
  PR-lifecycle rule, with the Stage 9 `pgrep` check run right before the merge.
- **Production root.** Write to `/Users/lowell/Projects/embedding-data/data` only at the
  owner-gated steps of Tasks 4 and 13. Every production command passes
  `--data-dir /Users/lowell/Projects/embedding-data/data`. Tests use `tmp_path` roots
  and always pass the data root explicitly.
- **Acceptance values.** The real counts are measured, never gated. No test or gate
  contains a count from the real files. The 1,012 national-industry nodes are a property
  of the pinned bundle and of the committed Stage 4 fixture originals.
- **Style.** Single quotes, `'''` docstrings, 4-space indents, 99 columns,
  `uv run --locked ruff check .` clean. Polars lazy with method-style expressions. No
  pandas.
- **R8.4.** No table feeds embedder training, curriculum, hard-negative mining or model
  selection. The README section and the findings file say so.
- **Fixtures.** TRI CSVs are synthetic, with made-up D&B numbers. Fixture results show
  software readiness and are never benchmarks.

## Owner Checkpoints

1. **Frozen modules (any task).** If a reused function cannot serve unchanged, stop and
   ask the owner. Do not edit it.
2. **Page read (Task 1 Step 1).** Before reading the basic data files page and sending
   one `HEAD` request for each window year, get the owner's go-ahead with the URLs. No
   TRI data file is fetched in Task 1.
3. **Production writes (Task 4).** Get a go-ahead under the host rule before each file
   fetch or import. Get a go-ahead before reading EPA's documentation PDF.
4. **Preflight stops (Task 4).** A failed E7–E9 check stops the stage. Report it and do
   nothing further. The owner records O7 and O8 as uncovered or promotes a named
   alternate. A blank standardized parent field leaves the owner a choice between the
   D&B key and an uncovered verdict. More than 1% of a year's facility-years outside the
   NAICS 2022 set is a trigger to ask the owner, not a failure.
5. **Full-data run (Task 13).** Get a go-ahead under the host rule before the build and
   before any cleanup of a failed run's staging. If `verify`, the reconciler or a
   preservation check fails, stop, change no code and ask the owner.

## Review Focus

1. **Two EPA snapshots of one year on disk.** EPA revises earlier years, so a later
   snapshot lands beside the first. The person expects the build to read only the
   `--processed-as-of` snapshot, and to fail on a missing or doubled file under that
   date. Test: Task 1 `test_snapshot_selection_ignores_other_dates`.
2. **Parent name spellings.** `' Acme Corp '` and `'Acme Corp'` are one owner after the
   strip. `'ACME CORP'` stays a separate owner and appears only in the collision count.
   Test: Task 7 `test_name_spellings_join_only_after_the_strip`.
3. **D&B numbers in outputs.** Every fixture D&B number is absent from every bundle file
   and from a failure line. Test: Task 11
   `test_no_dnb_number_in_any_bundle_byte_or_failure_line`.
4. **Raw encodings.** A file with a UTF-8 BOM, CRLF line ends and one Windows-1252 byte
   reads with the same header and values as a plain UTF-8 file, and no row is lost.
   Test: Task 5 `test_bom_crlf_and_cp1252_read_like_plain_utf8`.
5. **Killed build.** A leftover `<RUN_ID>.part` makes a rerun with that ID fail and stay
   byte-identical. A fresh ID builds. Test: Task 9
   `test_leftover_staging_is_refused_and_untouched`.

## Decisions

None.

## Settled Defaults (for owner review)

1. **Preflight first.** Task 4 (acquisition, preflight and layout) comes before the
   reader, estimators and bundle. The V12 fixture needs "the recorded header layout",
   and the Stage 2 rule says each build stage starts with its preflight. This puts the
   first production write in the middle of execution.
2. **Layout record.** The spec's "registry constant" is the committed JSON file
   `src/embedding_data/tri_layouts.json`, loaded by `tri_layout`. The preflight's
   `measure` reads the same file, so nothing is copied by hand into the build.
   `SOFTWARE_FILES` hashes it.
3. **Own download.** `tri_raw` streams with httpx itself. `osha_benchmark_download.download`
   skips the length check when `Content-Length` is absent, replaces an existing
   destination and echoes to stdout. Publication follows
   `ita_index_references.publish_original`: an exclusive `.part`, then `os.link`.
4. **Missing `Content-Length`.** `acquire` refuses that file and records nothing. The
   owner then downloads in a browser and uses `import-file`.
5. **Existing raw files.** `acquire` keeps a file that is recorded and verifies, and does
   not download it again. It refuses an unrecorded file, a recorded file that is
   missing, and a `.part`. `import-file` refuses any existing destination.
6. **Import naming.** `import-file` publishes under the registered EPA file name for the
   year, not the local name. Its entry has `client` `manual-import`, `client_version` the
   `embedding-data` version, `source_url` null and `proxies` `('retrieved_at',)`.
7. **Codes selector.** It makes only the spec's checks. The twelve table names, the node
   schema and `codes-ita-v1` are literals in `tri_codes`. Tests compare them with
   `target_inputs.CODE_SCHEMAS`, `classification_tables.NODE_SCHEMA` and
   `code_build.SCHEMA_VERSION`.
8. **E7 1% trigger.** For each year, the numerator is facility-years whose one distinct
   primary value is not a NAICS 2022 national-industry code. The denominator is all
   facility-years of that year. Missing and conflicting primaries are measured, not
   counted in the trigger.
9. **Encoding.** A file that starts with a UTF-8 BOM, or holds bytes that are not valid
   UTF-8, is transcoded line by line through `osha_encoding.decode_line` into
   `<RUN_ID>.part/.scratch/`, with the BOM removed. The report lists transcoded years.
10. **Blank cells.** Every CSV field reads as a string, and an empty field reads as `''`,
    never null.
11. **Strict values.** A blank TRIFD, or a form-type or federal-flag value outside the
    year's registered sets, fails the build. Form-type and federal values compare as
    delivered. Parent and D&B values compare after stripping surrounding whitespace.
12. **Usable D&B number.** A stripped value that is not in the year's "no D&B" strings.
    No digit pattern is imposed. The preflight reports values that are not nine ASCII
    digits.
13. **Territories.** State values `AS`, `GU`, `MP`, `PR`, `UM` and `VI`, counted in the
    report only. E7 records every state value present.
14. **Report counts.** Fill rates are recorded as counts with their denominators. `N` is
    recorded overall and for each year.
15. **`compare-runs`.** It compares the five Parquets in physical order and `report.json`
    exactly. `report.json` holds no run ID, time, commit or path. `inputs.json` is not
    compared.
16. **Fixture chain.** It calls the Stage 10 helper's parts (`golden_releases`,
    `write_release`, `year_file`, `ita_summary.build_summary_table`,
    `import_stage4_originals`, `code_build.build`) and skips its index import and Stage 3
    expectations.
17. **Reconciler layout.** The reconciler holds its own literal column map and value
    sets. A test checks that they equal the committed layout.
18. **Amendment item 2.** The Stage 2 spec's exact text cites R7.5, which Stages 14 and 15
    add. If Stage 5 applies item 2 first, the reference points forward until then. Task 14
    gives the drafted `CLAUDE.md` text for item 7.
19. **Reuse beyond the spec's list.** The spec's list adds `manifest.check_appendable` and
    `read_manifest`, and `geography_references.safe_path` and `occupied`, which
    `target_io` already imports. Each is imported unchanged.
20. **Failure path.** The failure line prints the data-relative path
    (`raw/epa_tri/basic`, `derived/epa_tri/parent-links/<run_id>`). Stage 10 printed the
    absolute run path.
21. **Universe date.** The universe statement and `processed_as_of` use the ISO date
    (`2025-11-05`), as the raw path does.

---

## File Map

| Path | Task | Responsibility |
| --- | --- | --- |
| `src/embedding_data/tri_raw.py` | 1 | Page catalog, raw layout, `acquire`, `import_file`, snapshot selection |
| `src/embedding_data/tri_parent_links.py` | 1, 10 | Typer command group |
| `src/embedding_data/tri_codes.py` | 2 | Codes selector |
| `src/embedding_data/tri_layout.py` | 3 | Header layout model and loader |
| `src/embedding_data/tri_layouts.json` | 4 | Production header layouts |
| `src/embedding_data/tri_reader.py` | 5 | Raw CSV reader |
| `src/embedding_data/tri_facility_years.py` | 6 | Reduction, eligibility, owner keys, year report |
| `src/embedding_data/tri_parent_link_targets.py` | 7 | O7 target, marginals, support, validator |
| `src/embedding_data/tri_parent_industries.py` | 8 | O8 table |
| `src/embedding_data/tri_bundle.py` | 9 | Build, verify, compare, software identity |
| `scripts/preflight_tri.py` | 3 | E7/E8 data checks |
| `scripts/reconcile_tri_parent_links.py` | 12 | Independent recount |
| `tests/tri_fixtures.py` | 2, 5, 11 | Codes bundle seeding, synthetic TRI CSVs, V12 chain |
| `tests/fixtures/epa_tri/basic_data_files.html` | 1 | Trimmed copy of the EPA page |
| `tests/test_tri_*.py`, `tests/test_preflight_tri.py`, `tests/test_reconcile_tri_parent_links.py` | 1–12 | Tests |
| `README.md` | 10 | Command contract section |
| `specs/naics-evaluation-data-stage-5-findings.md` | 4, 13, 14 | Preflight, run and handoff |
| `specs/embedding-evaluation-data-spec.md`, `CLAUDE.md` | 14 | Source spec amendment |
| `specs/naics-evaluation-data-roadmap.md`, `specs/deferred_items.md`, `specs/history.md` | 14 | Completion records |

---

### Task 1: Raw TRI files and acquisition commands

**Files:**
- Create: `src/embedding_data/tri_raw.py`
- Create: `src/embedding_data/tri_parent_links.py`
- Create: `tests/fixtures/epa_tri/basic_data_files.html`
- Test: `tests/test_tri_raw.py`, `tests/test_tri_cli.py`

**Interfaces:**
- Consumes: `manifest`, `paths`, `geography_references.safe_path`, `occupied`.
- Produces in `tri_raw`:
  - `SOURCE = 'epa_tri'`, `WINDOW = (2022, 2023, 2024)`, `PAGE_URL` (the page above),
    `USER_AGENT: str` (Step 1), `TIMEOUT = httpx.Timeout(600.0, connect=15.0)`,
    `CHUNK_SIZE = 1024 * 1024`
  - `@dataclass(frozen=True) class Catalog: processed_as_of: date; urls: dict[int, str]`,
    window years only
  - `parse_page(html: str, page_url: str) -> Catalog`
  - `file_name(year: int) -> str`: the registered EPA file name (Step 1)
  - `snapshot_dir(data_dir: Path, year: int, processed_as_of: date) -> Path`:
    `paths.raw_dir(data_dir, SOURCE) / 'basic' / str(year) / processed_as_of.isoformat()`
  - `raw_path(data_dir: Path, year: int, processed_as_of: date) -> Path`:
    `snapshot_dir(...) / file_name(year)`
  - `make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client`, a module
    global looked up at call time (test seam): `follow_redirects=True`, `USER_AGENT`,
    `TIMEOUT`
  - `acquire(data_dir: Path) -> list[Path]`, in window order
  - `import_file(data_dir: Path, year: int, original: Path, *, processed_as_of: date) -> Path`
  - `select_files(data_dir: Path, processed_as_of: date) -> dict[int, Path]`
  - `citations(data_dir: Path, files: dict[int, Path]) -> list[dict]`: each
    `asdict(manifest.entry_for(...))` read back through JSON, sorted by `path`
- Produces in `tri_parent_links`: `app` (Typer, `pretty_exceptions_enable=False`,
  `pretty_exceptions_show_locals=False`), the `--data-dir` option type `DataRoot`,
  `NO_RUN = '-'`, `RAW = 'raw/epa_tri/basic'`, `_reason(error) -> str`,
  `_invoke(command, run_id, path, operation)`, and the commands `acquire` and
  `import-file YEAR FILE --processed-as-of DATE`. Copy the shape of
  `src/embedding_data/ita_establishment_targets.py:32-60` with the Stage 5 failure line.

**Rules:**
- `parse_page` raises `ValueError` when the "processed as of" date is missing or appears
  with two different values, or when a window year's U.S. link is missing or repeated.
- `acquire` reads the page, then checks every destination before any download (Settled
  Default 5). A symlink anywhere in a destination path fails. Then for each missing year
  it streams the body into `<destination>.part`, opened `'xb'`. A missing
  `Content-Length` raises `ValueError('download has no Content-Length')`. A byte count
  that differs raises `httpx.RemoteProtocolError`. It then builds the entry from the
  `.part` bytes, calls `manifest.check_appendable`, publishes with
  `os.link(partial, destination)` and appends the entry. `finally` unlinks the `.part`.
  Entries: `client='httpx'`, `client_version=version('httpx')`, `source_url=<year URL>`,
  `through_date=catalog.processed_as_of`. Nothing is written to stdout, and nothing of
  the page is saved.
- `import_file` refuses a year outside `WINDOW`, and an original that is a symlink, not a
  regular file, or empty. It refuses an existing destination or `.part`. It copies
  through an exclusive `.part`, compares the copy's SHA-256 with the original's, then
  links and records it as in Settled Default 6, with `through_date=processed_as_of`.
- `select_files` requires each year's `snapshot_dir` to be a real directory holding
  exactly one entry, named `file_name(year)`, a regular file that `manifest.entry_for`
  verifies. Any other state raises `ValueError` (`'raw file is not recorded'`,
  `'missing or extra raw file'`, `'raw file changed'`).

- [ ] **Step 1: Read the EPA page (controller, Owner Checkpoint 2)**

Make a new empty scratch directory outside the repository and the data root, with
`mktemp -d /private/tmp/stage5-epa-page.XXXXXX`. Fetch the page HTML into it with
`curl -sS -D page.headers -o page.html -A 'embedding-data TRI acquisition' "$PAGE_URL"`.
If the status is 403, retry once with the browser string in
`osha_benchmark_download.USER_AGENT`. Record which one was served: that string becomes
`USER_AGENT`, as a literal. Read `page.html` as data and record:
1. The "processed as of" sentence and its date.
2. How the page addresses one year's U.S. file: an `href`, a `data-*` attribute, an
   `<option value>` or a script literal. Write the rule that `parse_page` applies.
3. The resolved URL for 2022, 2023 and 2024.

Send one `curl -sSI` (`HEAD`) per window URL. Record the status, `Content-Length`,
`Content-Disposition` and `Content-Type`. The EPA file name is the
`Content-Disposition` file name, or else the URL's last path segment. Record the naming
rule that `file_name` applies. Fetch no body.

Stop and ask the owner if the static HTML gives no rule for a year's URL, or if no file
name can be fixed. Record all facts in the Task 1 commit message body. Task 4 copies them
to the findings file.

- [ ] **Step 2: Write the fixture page**

Copy `page.html` to `tests/fixtures/epa_tri/basic_data_files.html`. Keep only the element
that holds the "processed as of" sentence and the elements that carry the U.S. links for
2021–2024, plus one non-U.S. link of 2024 if the page lists state files. Do not change
anything inside the kept elements. Delete the scratch directory.

- [ ] **Step 3: Write the failing tests**

```python
PAGE = Path(__file__).parent / 'fixtures/epa_tri/basic_data_files.html'
RECORDED = date(...)   # the Step 1 date

def test_parse_page_reads_the_snapshot_date_and_window_links():
    catalog = tri_raw.parse_page(PAGE.read_text(), tri_raw.PAGE_URL)
    assert catalog.processed_as_of == RECORDED
    assert sorted(catalog.urls) == [2022, 2023, 2024]
    assert all(url.startswith('https://') for url in catalog.urls.values())

@pytest.mark.parametrize('edit', ['drop_date', 'second_date', 'drop_2023', 'repeat_2024'])
def test_parse_page_refuses_an_unreadable_catalog(edit): ...   # ValueError

def test_acquire_downloads_and_records_each_window_file(data_directory, monkeypatch):
    # make_client patched to an httpx.MockTransport: the page, then three bodies sent with
    # stream=httpx.ByteStream(...) and a Content-Length header
    files = tri_raw.acquire(data_directory)
    assert [f.relative_to(data_directory).as_posix() for f in files] == [
        f'raw/epa_tri/basic/{y}/{RECORDED.isoformat()}/{tri_raw.file_name(y)}'
        for y in tri_raw.WINDOW]
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [(e.client, e.source_url, e.through_date, e.proxies) for e in entries] == [
        ('httpx', URLS[y], RECORDED.isoformat(), ()) for y in tri_raw.WINDOW]

@pytest.mark.parametrize('length', ['short', 'absent'])
def test_acquire_refuses_a_short_or_unsized_body(length, data_directory, monkeypatch): ...
    # raises; no final file, no .part, no manifest line

def test_acquire_keeps_a_recorded_file_and_refuses_unrecorded_or_missing(...): ...
    # recorded and intact: not requested again; unrecorded file, or recorded and absent,
    # or a .part sibling: raises before any body request, bytes unchanged

def test_import_file_records_a_proxy_retrieval_time(data_directory, tmp_path):
    original = tmp_path / 'download (1).csv'
    ...
    path = tri_raw.import_file(data_directory, 2023, original,
                               processed_as_of=date(2025, 11, 5))
    assert path.name == tri_raw.file_name(2023)
    entry = manifest.entry_for(paths.manifest_path(data_directory), path)
    assert (entry.client, entry.source_url, entry.proxies, entry.through_date) == (
        'manual-import', None, ('retrieved_at',), '2025-11-05')

def test_import_file_refuses_other_years_existing_paths_and_symlinks(...): ...

def test_snapshot_selection_ignores_other_dates(data_directory, tmp_path):
    # import every window year under 2025-11-05 and again under 2026-06-01
    assert tri_raw.select_files(data_directory, date(2025, 11, 5)) == {
        y: tri_raw.raw_path(data_directory, y, date(2025, 11, 5)) for y in tri_raw.WINDOW}
    # an extra file in one 2025-11-05 directory, a year missing under it, or changed bytes
    # each raise ValueError
```

In `tests/test_tri_cli.py`:

```python
def test_acquire_and_import_print_one_json_line(cli_runner, data_directory, ...): ...
def test_import_failure_prints_only_the_fixed_line(cli_runner, data_directory, tmp_path):
    result = cli_runner.invoke(tri_parent_links.app, [
        'import-file', '2021', str(file), '--processed-as-of', '2025-11-05',
        '--data-dir', str(data_directory)])
    assert result.exit_code == 2
    assert result.output.strip() == (
        'TRI parent links import-file failed: validation; run -; path raw/epa_tri/basic')
```

- [ ] **Step 4: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_tri_raw.py tests/test_tri_cli.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'embedding_data.tri_raw'`.

- [ ] **Step 5: Implement `tri_raw` and the two commands**

- [ ] **Step 6: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_tri_raw.py tests/test_tri_cli.py -q`
Expected: all pass.

- [ ] **Step 7: Confirm that nothing reads `through_date` across sources**

Run: `grep -rnE "\.through_date|\['through_date'\]|get\('through_date'\)" src scripts`
Expected: no output. If a line appears, stop and ask the owner before committing.

- [ ] **Step 8: Commit**

Files: the two modules, the fixture page and both tests. Message:
`feat: acquire and import EPA TRI basic data files`, with the Step 1 facts in the body.

---

### Task 2: Codes selector

**Files:**
- Create: `src/embedding_data/tri_codes.py`
- Create: `tests/tri_fixtures.py`
- Test: `tests/test_tri_codes.py`

**Interfaces:**
- Consumes: `target_io.relative_file`, `verify_inventory`; `manifest.sha256_file`.
- Produces in `tri_codes`:
  - `RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')`, `PIN = re.compile(r'[0-9a-f]{64}')`
  - `CODES_SCHEMA_VERSION = 'codes-ita-v1'`
  - `CODE_TABLES = ('naics_nodes', 'naics_edges', 'soc_nodes', 'soc_edges', 'naics_native_nodes', 'naics_concordance', 'filing_rules', 'code_paths', 'filing_rule_labels', 'filing_rule_membership', 'ita_naics_lookup', 'ita_300a_canonical')`
  - `INVENTORY_NAMES = {name + '.parquet' for name in CODE_TABLES} | {'inputs.json', 'report.json'}`
  - `NODE_SCHEMA = {'node_id': pl.String, 'system': pl.String, 'vintage': pl.Int64, 'level': pl.String, 'code': pl.String, 'title': pl.String}`
  - `NODE_PREFIX = 'naics:2022:national_industry:'`
  - `@dataclass(frozen=True) class SelectedNodes: data_dir: Path; codes_run: str; codes_outputs_sha256: str; outputs: dict; node_ids: frozenset[str]`,
    with `verify(self) -> None` (reselect and refuse any difference) and
    `provenance(self) -> dict` returning
    `{'run_id': ..., 'outputs_sha256': ..., 'outputs': ...}`
  - `select_nodes(data_dir: Path, codes_run: str, *, codes_outputs_sha256: str) -> SelectedNodes`
- Produces in `tests/tri_fixtures.py`:
  `seed_codes_bundle(data_dir: Path, directory: Path) -> tuple[str, str]`, which returns
  the codes run ID and its detached pin. It calls, in order: for each `(year, rows)` of
  `ita_establishment_fixtures.golden_releases().items()`,
  `ita_fixtures.write_release(data_dir, year, ita_fixtures.year_file(year, rows))`; then
  `ita_summary.build_summary_table(data_dir)`;
  `ita_establishment_fixtures.import_stage4_originals(data_dir, directory)`;
  `code_build.build(data_dir, ita_establishment_fixtures.CODES_RUN)`.

**Selector checks, in order:** run ID and pin syntax; the SHA-256 of
`derived/codes/<run>/outputs.json` equals the pin; `target_io.verify_inventory` with
`INVENTORY_NAMES`; `inputs.json` and `report.json` have `schema_version ==
CODES_SCHEMA_VERSION` and `inputs.json` has `run_id == codes_run`;
`naics_nodes.parquet` has exactly `NODE_SCHEMA`, and its rows and schema equal
`report['tables']['naics_nodes.parquet']`. `node_ids` are the `node_id` values with
`system == 'naics'`, `vintage == 2022` and `level == 'national_industry'`. Each starts
with `NODE_PREFIX`, and none repeats. No other file is read: no raw citation, source
summary or canonical table.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.fixture(scope='module')
def codes(tmp_path_factory):
    root = tmp_path_factory.mktemp('codes')
    run, pin = seed_codes_bundle(root / 'data', root / 'originals')
    return root / 'data', run, pin

def test_constants_match_stage4():
    assert set(tri_codes.CODE_TABLES) == set(target_inputs.CODE_SCHEMAS)
    assert tri_codes.NODE_SCHEMA == classification_tables.NODE_SCHEMA
    assert tri_codes.CODES_SCHEMA_VERSION == code_build.SCHEMA_VERSION

def test_select_nodes_reads_the_national_industries(codes):
    data_dir, run, pin = codes
    selected = tri_codes.select_nodes(data_dir, run, codes_outputs_sha256=pin)
    assert len(selected.node_ids) == 1012
    assert 'naics:2022:national_industry:111110' in selected.node_ids

def test_select_nodes_reads_no_ita_data(codes, tmp_path):
    # copy the data root, delete derived/osha/ita_300a_summary.parquet and raw/osha,
    # then select_nodes on the copy still returns the same node_ids

@pytest.mark.parametrize('mutation', ['run_id', 'pin_syntax', 'wrong_pin', 'extra_file',
                                      'changed_byte', 'schema_version', 'recorded_run_id'])
def test_select_nodes_refuses(codes, tmp_path, mutation): ...   # ValueError, on a copy

def test_verify_detects_a_later_change(codes, tmp_path): ...
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_tri_codes.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'embedding_data.tri_codes'`.

- [ ] **Step 3: Implement `tri_codes` and `seed_codes_bundle`**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_tri_codes.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Files: `tri_codes.py`, `tests/tri_fixtures.py`, `tests/test_tri_codes.py`. Message:
`feat: select the pinned Stage 4 NAICS nodes for TRI`.

---

### Task 3: Header layout model and preflight script

**Files:**
- Create: `src/embedding_data/tri_layout.py`
- Create: `scripts/preflight_tri.py`
- Test: `tests/test_tri_layout.py`, `tests/test_preflight_tri.py`

**Layout JSON.** One object, `version` and `years`. Each year holds `header` (the exact
header row), `columns` and `values`:

```json
{"version": "tri-headers-v1", "years": {"2022": {
  "header": ["..."],
  "columns": {"reporting_year": "...", "trifd": "...", "document_control_number": "...",
              "form_type": "...", "state": "...", "federal": "...", "primary_naics": "...",
              "other_naics": ["...", "...", "...", "...", "..."],
              "parent_name": "...", "parent_dnb": "...", "standardized_parent": "...",
              "foreign_parent_name": null, "foreign_parent_dnb": null,
              "standardized_foreign_parent": null},
  "values": {"form_r": ["..."], "form_a": ["..."], "federal_yes": ["..."],
             "federal_no": ["..."], "no_parent": ["", "..."], "no_dnb": ["", "..."]}}}}
```

**Interfaces:**
- Consumes: `tri_raw.WINDOW`, `tri_raw.select_files`, `tri_codes.select_nodes`.
- Produces in `tri_layout`:
  - `LAYOUT_VERSION = 'tri-headers-v1'`,
    `PRODUCTION_FILE = Path(__file__).with_name('tri_layouts.json')`
  - `FIELDS = ('reporting_year', 'trifd', 'document_control_number', 'form_type', 'state', 'federal', 'primary_naics', 'parent_name', 'parent_dnb', 'standardized_parent')`
  - `FOREIGN_FIELDS = ('foreign_parent_name', 'foreign_parent_dnb', 'standardized_foreign_parent')`
  - `VALUE_SETS = ('form_r', 'form_a', 'federal_yes', 'federal_no', 'no_parent', 'no_dnb')`
  - `@dataclass(frozen=True) class HeaderLayout: year: int; header: tuple[str, ...]; columns: dict[str, str | None]; other_naics: tuple[str, ...]; values: dict[str, frozenset[str]]`
  - `parse_layouts(value: dict) -> dict[int, HeaderLayout]`
  - `layouts_json(layouts: dict[int, HeaderLayout]) -> dict`, with sorted value lists, so
    that `parse_layouts(layouts_json(x)) == x`
  - `load_layouts(file: Path = PRODUCTION_FILE) -> dict[int, HeaderLayout]`. A missing
    file raises `ValueError('production header layout is not recorded')`.
- Produces `scripts/preflight_tri.py` with two subcommands. Both take `--data-dir` and
  `--processed-as-of`. Exit 0 when no stop condition holds, 1 when one does, 2 on a
  refusal.
  - `headers`: for each window year it prints the selected file's path and SHA-256, the
    exact header row, BOM presence, the count of lines that are not valid UTF-8, the CSV
    record count, and hint lists of header cells for each logical field. A hint matches
    a normalized cell: leading `<digits>.` and spaces removed, upper case, `_` read as a
    space. Hints are not decisions.
  - `measure --layout FILE --codes-run ID --codes-outputs-sha256 PIN`: reads a draft
    layout that may hold null columns and empty value sets. It prints the E7 and E8
    measures of the spec's preflight table for each year. It also prints value counts of
    `form_type`, `federal` and `state`, the 20 most frequent stripped values of
    `parent_name` and `standardized_parent`, and the 20 most frequent `parent_dnb` values
    that are not nine ASCII digits. Then it prints `stops` (failed stop conditions),
    `asks` (the 1% trigger) and `ok`.

**`parse_layouts` checks:** `version == LAYOUT_VERSION`; years exactly `WINDOW`; header
cells nonblank and unique; every mapped column is a header cell; `FIELDS` all mapped;
`other_naics` holds 5 distinct cells; `FOREIGN_FIELDS` null for 2022 and mapped for
2023 and 2024; every value set present; `form_r` and `form_a` disjoint and nonempty;
`federal_yes` and `federal_no` disjoint, with `federal_yes` nonempty; `no_parent` and
`no_dnb` entries equal their own strip. Each failure raises `ValueError`.

**Stop conditions in `measure`:** a year with no `primary_naics`, `federal` or
`standardized_parent` column; a year in which the standardized parent is blank or a
"no parent" string for every facility-year that reports a parent name. The 1% trigger
uses Settled Default 8. Document checks are not in the script.

- [ ] **Step 1: Write the failing tests**

`tests/test_tri_layout.py`: `test_layout_json_round_trip`,
`test_parse_layouts_refuses` (parametrized over every check above) and
`test_load_layouts_refuses_a_missing_file`.

`tests/test_preflight_tri.py` writes synthetic CSVs with an invented numbered header and
imports them with `tri_raw.import_file`. It uses a codes bundle from `seed_codes_bundle`.

```python
def test_headers_prints_exact_rows_bom_and_utf8_counts(...):
    report = run_headers(...)
    assert report['2022']['header'] == HEADER_2022
    assert report['2023']['bom'] is True
    assert report['2024']['invalid_utf8_lines'] == 1

def test_measure_counts_a_small_known_window(...):
    # 2022: 3 facilities, 5 forms (R and A), one primary conflict, one code outside 2022
    report = run_measure(...)
    assert report['years']['2022']['facility_years'] == 3
    assert report['years']['2022']['naics_not_2022'] == 1
    assert report['years']['2022']['naics_conflict'] == 1
    assert report['years']['2022']['case_a'] == 1 ...

@pytest.mark.parametrize('stop', ['no_primary', 'no_federal', 'no_standardized',
                                  'standardized_always_blank'])
def test_measure_reports_each_stop_and_exits_1(stop, ...): ...

def test_measure_asks_above_one_percent_and_exits_0(...): ...
def test_preflight_refuses_an_unrecorded_file(...): ...   # exit 2
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_tri_layout.py tests/test_preflight_tri.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'embedding_data.tri_layout'`.

- [ ] **Step 3: Implement `tri_layout` and `scripts/preflight_tri.py`**

The script imports `tri_raw`, `tri_codes`, `manifest` and `paths`, and reads the CSVs
with Python's `csv` module through `osha_encoding.decode_line`.

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_tri_layout.py tests/test_preflight_tri.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: add the TRI header layout model and preflight checks`.

---

### Task 4: Acquisition, preflight and production layout (controller, owner-gated)

**Files:**
- Create: `src/embedding_data/tri_layouts.json`
- Create: `specs/naics-evaluation-data-stage-5-findings.md` (Preflight section)
- Test: `tests/test_tri_layout.py` (one test added)

- [ ] **Step 1: Preservation baseline**

Copy `data/raw/manifest.jsonl` to a new scratch directory outside the data root, and
record its SHA-256 and byte length. Run
`uv run --locked embedding-data audit --data-dir /Users/lowell/Projects/embedding-data/data`.
Expected: exit 0, no discrepancy.

- [ ] **Step 2: Acquire or import (Owner Checkpoint 3, host rule)**

Run the host-rule checks and get the go-ahead for the fetch. Then run:

```bash
uv run --locked python -m embedding_data.tri_parent_links acquire --data-dir /Users/lowell/Projects/embedding-data/data
```

Expected: one JSON line listing three paths under `raw/epa_tri/basic/`. If `acquire`
refuses (no `Content-Length`, a short body, a changed page), the owner downloads each
file in a browser from the complete-data page. Run `import-file YEAR FILE
--processed-as-of DATE` for each one, with the page's date, a go-ahead per file and the
host-rule checks. Record each file's path, size and SHA-256.

- [ ] **Step 3: Headers**

Run `uv run --locked python scripts/preflight_tri.py headers --data-dir /Users/lowell/Projects/embedding-data/data --processed-as-of DATE`.
Write a draft layout in the scratch directory from its output. Copy each header row
exactly. Map each logical field to one cell, and leave a field null when no cell holds
it.

- [ ] **Step 4: Measure**

Run `measure` with the draft layout, the codes run and its pin. Fill the six value sets
from its value counts: the form-type strings for Form R and Form A, the federal
yes and no strings, and the "no parent" and "no D&B" strings. Run `measure` again until
every observed form-type and federal value falls in a set. Keep the final JSON output.

- [ ] **Step 5: Document checks (read; Owner Checkpoint 3 for the PDF)**

Read the EPA pages named in the spec. Get a go-ahead before reading the documentation
PDF. Save no document under the data root and register none. For each check, record the
URL, the read date and a quote of fewer than 15 words:
- E7: the NAICS edition for each window year.
- E8: the time basis of the standardized parent name.
- E9: EPA's data license statement and its date, and any TRI-specific terms on the basic
  data files page or in the documentation.

- [ ] **Step 6: Decide (Owner Checkpoint 4)**

If `measure` lists any stop, or a document check fails its stop condition, stop the
stage. Report to the owner and do no further task. If `asks` is not empty, ask the owner
before going on. A "current owner" time basis is recorded as a limit and does not stop.

- [ ] **Step 7: Write the failing test**

```python
def test_production_layout_covers_the_window():
    layouts = tri_layout.load_layouts()
    assert sorted(layouts) == [2022, 2023, 2024]
    assert all(layout.columns['standardized_parent'] for layout in layouts.values())
```

Run: `uv run --locked pytest tests/test_tri_layout.py::test_production_layout_covers_the_window -q`
Expected: FAIL, `production header layout is not recorded`.

- [ ] **Step 8: Commit the layout**

Save the final draft as `src/embedding_data/tri_layouts.json` in `layouts_json` form,
then run the test again. Expected: PASS. Write the findings file's Preflight section:
1. The snapshot date, and each raw file's path, size and SHA-256.
2. The Task 1 page facts.
3. The `measure` output as a table for each year: E7, E8, the counts of cases (a), (b)
   and (c), and the trigger rate.
4. The document checks.
5. The `through_date` departure (Global Constraints).

Commit the layout, the test and the findings file with the message
`feat: record the measured TRI header layouts and preflight`.

---

### Task 5: Raw CSV reader

**Files:**
- Create: `src/embedding_data/tri_reader.py`
- Modify: `tests/tri_fixtures.py`
- Test: `tests/test_tri_reader.py`

**Interfaces:**
- Consumes: `tri_layout.HeaderLayout`, `load_layouts`; `osha_encoding.decode_line`;
  `tri_raw.import_file`, `select_files`.
- Produces in `tri_reader`:
  - `READ_SCHEMA = {'year': pl.Int64, 'reporting_year': pl.String, 'trifd': pl.String, 'form_type': pl.String, 'state': pl.String, 'federal': pl.String, 'primary_naics': pl.String, 'naics_2': pl.String, 'naics_3': pl.String, 'naics_4': pl.String, 'naics_5': pl.String, 'naics_6': pl.String, 'parent_name': pl.String, 'parent_dnb': pl.String, 'standardized_parent': pl.String, 'standardized_foreign_parent': pl.String}`
  - `needs_transcoding(file: Path) -> bool`: a leading UTF-8 BOM, or a line that is not
    valid UTF-8
  - `read_year(file: Path, layout: HeaderLayout, scratch: Path) -> pl.LazyFrame` in
    `READ_SCHEMA`. For 2022, `standardized_foreign_parent` is `''`.
  - `read_window(files: dict[int, Path], layouts: dict[int, HeaderLayout], scratch: Path) -> tuple[pl.LazyFrame, list[int]]`:
    the rows of all years in window order, and the transcoded years
- Produces in `tests/tri_fixtures.py`:
  - `tri_row(year: int, trifd: str, **fields: str | bool) -> dict[str, str]`: a full row keyed by
    the production layout's header cells. Unmapped cells are `''`. `form='R'` or `'A'`
    and `federal=True` or `False` take the first sorted registered value. Other keyword
    names are the logical fields of `READ_SCHEMA`.
  - `write_tri_csv(file: Path, year: int, rows: list[dict[str, str]], *, bom: bool = False, newline: str = '\n', encoding: str = 'utf-8') -> None`
  - `seed_tri_files(data_dir: Path, directory: Path, rows: dict[int, list[dict[str, str]]], processed_as_of: date) -> dict[int, Path]`:
    writes and imports each year's file
  - `rows_frame(records: list[dict]) -> pl.LazyFrame` in `READ_SCHEMA`, for unit tests

**Rules:** the header row is read with `csv.reader` and must equal `layout.header`
exactly, else `ValueError('changed header')`. A transcoded copy goes to
`scratch / f'{year}.utf8.csv'`, line by line through `decode_line`, with a leading BOM
removed. Scan with `pl.scan_csv(source, infer_schema=False, missing_utf8_is_empty_string=True)`.
Select the mapped cells and rename them to `READ_SCHEMA` names. The Polars row count must
equal the `csv.reader` record count, else `ValueError('row count differs')`. Each
`reporting_year`, stripped, must equal `str(year)`, else
`ValueError('reporting year mismatch')`.

- [ ] **Step 1: Write the failing tests**

```python
def test_reads_the_mapped_columns_as_strings(...):
    # D&B '001234567' and NAICS '325199' keep their exact text; schema == READ_SCHEMA
def test_blank_cells_read_as_empty_strings(...): ...   # '' and never null
@pytest.mark.parametrize('change', ['renamed_cell', 'added_column', 'swapped_order'])
def test_changed_header_fails(change, ...): ...
def test_reporting_year_mismatch_fails(...): ...
def test_bom_crlf_and_cp1252_read_like_plain_utf8(tmp_path):
    rows = [tri_row(2023, 'T1', parent_name='Café Holdings', ...), ...]
    plain = read(write_tri_csv(..., rows))
    odd = read(write_tri_csv(..., rows, bom=True, newline='\r\n', encoding='cp1252'))
    assert odd.collect().equals(plain.collect())
    assert transcoded == [2023]
def test_quoted_newline_keeps_one_record_and_ragged_row_fails(...): ...
def test_transcoded_copies_stay_in_scratch(...): ...
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_tri_reader.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'embedding_data.tri_reader'`.

- [ ] **Step 3: Implement `tri_reader` and the fixture helpers**

If `decode_line` cannot decode the fixture's Windows-1252 byte unchanged, stop and ask
the owner (Owner Checkpoint 1).

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_tri_reader.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: read TRI basic data files by their recorded layout`.

---

### Task 6: Facility-year table

**Files:**
- Create: `src/embedding_data/tri_facility_years.py`
- Test: `tests/test_tri_facility_years.py`

**Interfaces:**
- Consumes: `tri_reader.READ_SCHEMA`; `tri_layout.HeaderLayout`;
  `tri_codes.NODE_PREFIX`.
- Produces:
  - `CONTRACT = 'tri-facility-years-v1'`
  - `EXCLUSIONS = ('naics_missing', 'naics_conflict', 'naics_not_2022', 'parent_conflict', 'federal')`
  - `TABLE_SCHEMA`, in this order: `reporting_year` Int64, `trifd` String, `n_forms`,
    `n_form_r` and `n_form_a` UInt64, `primary_naics_values` and `other_naics_values`
    List(String), `naics_2022_node_id` String, `parent_names` and
    `foreign_parent_names` List(String), `federal_values` and `state_values`
    List(String), `flag_parent_mixed_blank` Boolean, `owner_key` String,
    `exclusion_reason` String
  - `PRIVATE = {'_candidate_key': pl.String, '_membership_keys': pl.List(pl.String), '_dnb_key': pl.String, '_reported_names': pl.List(pl.String), '_usable_dnb': pl.List(pl.String)}`
  - `reduce(rows: pl.LazyFrame, layouts: dict[int, HeaderLayout], node_ids: frozenset[str]) -> pl.DataFrame`:
    `TABLE_SCHEMA` then `PRIVATE`, sorted by `reporting_year`, `trifd`
  - `public(frame: pl.DataFrame) -> pl.DataFrame`: the `TABLE_SCHEMA` columns only
  - `validate_facility_years(table: pl.DataFrame, source_rows: int) -> None`
  - `year_report(rows: pl.LazyFrame, frame: pl.DataFrame, layouts: dict[int, HeaderLayout]) -> dict[str, dict]`,
    keyed by year string

**Reduction rules (spec "Facility-year table").** Group by `year` and `trifd` as
delivered. `n_form_r` and `n_form_a` count rows whose `form_type` is in `form_r` or
`form_a`. List columns hold sorted distinct values:
- NAICS columns: stripped, blanks dropped.
- `parent_names` and `foreign_parent_names`: the standardized fields, stripped, with the
  year's `no_parent` strings dropped.
- `federal_values` and `state_values`: as delivered.
- `_reported_names`: `parent_name`, stripped, with `no_parent` strings dropped.
- `_usable_dnb`: stripped `parent_dnb` values not in `no_dnb`.

Further rules:
- `flag_parent_mixed_blank` is true when one row names a standardized parent and
  another row gives a `no_parent` string.
- A facility-year is federal when any row's `federal` value is in `federal_yes`.
- Exclusions apply in `EXCLUSIONS` order.
- `naics_2022_node_id` is `NODE_PREFIX + code` when exactly one primary value exists and
  that ID is in `node_ids`, else null.
- `_candidate_key` is `'parent:' + name` for exactly one parent name,
  `'facility:' + trifd` for none, and null for more than one.
- `owner_key` is `_candidate_key` when eligible, else null.
- `_membership_keys` is `['parent:' + n for n in parent_names]`, or
  `['facility:' + trifd]` when there is none.
- `_dnb_key` is `'dnb:' + value` for exactly one usable value, else `'facility:' + trifd`.

**Failures:** a blank TRIFD, or a form-type or federal value outside the registered sets,
raises `ValueError`. `validate_facility_years` requires the exact schema, a unique sorted
key, `sum(n_forms) == source_rows`, `n_forms == n_form_r + n_form_a`, `owner_key` null
exactly when `exclusion_reason` is not null, and a non-null node ID exactly for the
eligible rows and the `parent_conflict` and `federal` rows.

**`year_report` keys for each year:** `rows`, `rows_by_form_type` (`form_r`, `form_a`),
`facility_years`, `facility_years_by_reason` (`eligible` plus the five reasons; the parts
sum to `facility_years`), `with_parent`, `with_usable_dnb`,
`names_with_several_dnb`, `dnb_with_several_names` (counted over rows that carry both),
`mixed_blank`, `with_foreign_parent`, `with_secondary_codes`, `in_territories`,
`case_a`, `case_b`, `case_c`. Case (a): `_reported_names` is empty and `parent_names` is
not. Case (b): `_reported_names` is not empty and `parent_names` is. Case (c):
exactly one usable D&B number and `parent_names` empty.

- [ ] **Step 1: Write the failing tests**

```python
def test_form_r_and_form_a_rows_reduce_to_one_facility_year():
    # three rows of T1 in 2023 (two R, one A), primary ' 325199', '325199', '325199'
    row = reduce_one(...)
    assert (row['n_forms'], row['n_form_r'], row['n_form_a']) == (3, 2, 1)
    assert row['primary_naics_values'] == ['325199']
    assert row['naics_2022_node_id'] == 'naics:2022:national_industry:325199'

@pytest.mark.parametrize('rows, reason', [
    (no_primary, 'naics_missing'), (two_primaries, 'naics_conflict'),
    (primary_999999, 'naics_not_2022'), (two_parents, 'parent_conflict'),
    (federal_form, 'federal'), (no_primary_and_federal, 'naics_missing'),
    (two_primaries_two_parents, 'naics_conflict'), (bad_code_two_parents, 'naics_not_2022'),
    (two_parents_federal, 'parent_conflict')])
def test_exclusion_reasons_follow_the_spec_order(rows, reason): ...

def test_mixed_blank_keeps_the_named_parent_and_flags(): ...
    # owner_key == 'parent:Acme Corp', flag_parent_mixed_blank is True
def test_any_federal_form_makes_the_facility_year_federal(): ...
def test_no_parent_strings_never_share_a_key():
    # T1 and T2 both give a no_parent string in 2023
    assert keys == ['facility:T1', 'facility:T2']
def test_dnb_key_needs_exactly_one_usable_number(): ...   # none, one, two, 'NA' ignored
def test_unregistered_values_and_blank_trifd_fail(): ...
def test_foreign_parent_names_are_empty_for_2022(): ...
def test_public_table_keeps_no_dnb_or_reported_names():
    assert list(public(frame).schema.items()) == list(TABLE_SCHEMA.items())
def test_validator_catches_lost_or_multiplied_rows(): ...
def test_year_report_counts_cases_a_b_c_and_partitions(): ...
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_tri_facility_years.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'embedding_data.tri_facility_years'`.

- [ ] **Step 3: Implement `tri_facility_years`**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_tri_facility_years.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: reduce TRI forms to facility-years with owner keys`.

---

### Task 7: Parent-link target (O7)

**Files:**
- Create: `src/embedding_data/tri_parent_link_targets.py`
- Test: `tests/test_tri_parent_link_targets.py`

**Interfaces:**
- Consumes: `tri_facility_years.reduce` output (with `PRIVATE` columns);
  `target_contract.validate_targets`, `TARGET_SCHEMA`.
- Produces:
  - `CONTRACT = 'tri-parent-links-v1'`, `YEARS = (2022, 2023, 2024)`,
    `TOLERANCE = 1e-12`
  - `METADATA`, `SIZE_LABEL`, `DNB_LABEL`, `FEDERAL_LABEL` and
    `UNIVERSE = '... {date} ...'` (Global Constraints)
  - `MARGINAL_SCHEMA`: `node_id` String, then UInt64 `n_owners`, `n_parent_owners`,
    `n_multi_industry_owners`, `n_facilities`, `n_facility_years`, `n_owners_dnb`,
    `n_owners_including_federal`, `n_owners_partial`
  - `SUPPORT_SCHEMA`: `unit_a`, `unit_b` String, then UInt64 `j_owners`, `j_2022`,
    `j_2023`, `j_2024`, `j_dnb`, `j_including_federal`
  - `@dataclass(frozen=True) class ParentLinks: targets: pl.DataFrame; marginals: pl.DataFrame; support: pl.DataFrame; report: dict`
  - `estimate(frame: pl.DataFrame, *, processed_as_of: date) -> ParentLinks`
  - `validate_parent_links(result: ParentLinks, node_ids: frozenset[str]) -> None`
  - `name_collisions(names: Iterable[str]) -> dict[str, int]`: keys `keys` and `names`.
    It groups distinct names by `' '.join(name.casefold().split())` and counts groups
    with more than one name, and the names in them.

**Algorithm (spec "Estimand").** Presence is the distinct `(owner, year, node)` set over:
- headline: eligible rows, keyed by `owner_key`
- D&B: eligible rows, keyed by `_dnb_key`
- federal: eligible rows plus rows whose reason is `federal`, keyed by `_candidate_key`

`n(a)` is the count of distinct owners with `a` in some year. `J(a,b)` is the count of
distinct owners with `a` and `b` in one year, for `a != b`. `j_<year>` counts distinct
owners in that year. A target row exists for each headline `J >= 1`, in both directions:
`value = J / n(a)`, `n_unweighted = J`, `n_weighted = float(J)`. Flags are sorted:
`DNB_LABEL` when `j_dnb != j_owners`, `FEDERAL_LABEL` when
`j_including_federal != j_owners`, and always `SIZE_LABEL`. Marginal rows exist for each
node with headline `n(a) >= 1`.
- `n_multi_industry_owners`: owners with `a` and another node in one year.
- `n_parent_owners`: owners whose key starts with `parent:`.
- `n_owners_partial`: owners with an eligible facility-year in `a` in a year `t`, who
  also own, through `_membership_keys`, a facility-year excluded as `naics_missing`,
  `naics_conflict`, `naics_not_2022` or `parent_conflict` in year `t`.

**`report` keys:** `n_owners` (`headline`, `dnb`, `federal`), `owners_by_year` (the same
three for each year), `partial_owners` (distinct owners with any partial node),
`cells_only_dnb`, `cells_only_federal`, `n_unweighted_distribution` (`count`, `min`,
`p25`, `median`, `p75`, `p90`, `max`, and the counts at 1, 2, 3, 5 and 10 or more),
`owner_key_changes` (TRIFDs whose eligible owner key differs between years),
`parent_name_collisions` (`name_collisions` over all `parent_names`).

**Validator (spec "Validation"):** `validate_targets`; `METADATA` on every row; each unit
is in `node_ids`; `unit_a != unit_b`; each `(a,b)` has a `(b,a)` mirror with equal
`n_unweighted`; `n_unweighted >= 1`; `|value - J / n(a)| <= TOLERANCE`;
`J <= min(n(a), n(b))`; the support rows are exactly the target cells, with
`j_owners == n_unweighted`; the marginal `n_owners` equals the `n(a)` that the values
imply.

- [ ] **Step 1: Write the failing tests**

```python
def test_same_year_co_presence_counts_each_owner_once():
    # parent P: two facilities in a and one in b in 2022, and a, b again in 2023
    assert support_row(a, b) == {'j_owners': 1, 'j_2022': 1, 'j_2023': 1, 'j_2024': 0, ...}
    assert target(a, b)['value'] == 1.0 and target(b, a)['value'] == 1.0

def test_cross_year_presence_is_not_a_pair(): ...   # a in 2022, b in 2023: no row
def test_mirror_rows_and_no_diagonal(): ...
def test_self_owned_facility_counts_in_n_only(): ...
def test_value_is_j_over_n_a():
    # n(a) = 2, n(b) = 1, J = 1
    assert (target(a, b)['value'], target(b, a)['value']) == (0.5, 1.0)
def test_dnb_sensitivity_counts_and_label(): ...
    # same D&B, two names: a cell counted in report['cells_only_dnb'] and not listed
    # one name, two D&B numbers: the row carries DNB_LABEL with j_dnb == 0
def test_federal_sensitivity_counts_and_label(): ...
def test_partial_owners_count_conflicts_for_each_named_parent(): ...
    # a parent_conflict facility-year naming P and Q in 2023 makes P and Q partial for their
    # 2023 nodes; a federal exclusion and an exclusion in another year do not
def test_name_spellings_join_only_after_the_strip():
    # ' Acme Corp ' (a) and 'Acme Corp' (b) in 2023: one owner, J(a,b) == 1
    # 'ACME CORP' (c): a separate owner, no (a,c) row
    assert result.report['parent_name_collisions'] == {'keys': 1, 'names': 2}
def test_metadata_flags_and_universe():
    assert row['flags'] == sorted(row['flags'])
    assert row['universe'] == UNIVERSE.format(date='2025-11-05')
@pytest.mark.parametrize('break_', ['no_mirror', 'diagonal', 'j_above_min', 'value',
                                    'unknown_node', 'support_differs', 'marginal_differs'])
def test_validator_rejects(break_): ...
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_tri_parent_link_targets.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement the module**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_tri_parent_link_targets.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: estimate TRI parent-link shares with companions`.

---

### Task 8: Parent industry table (O8)

**Files:**
- Create: `src/embedding_data/tri_parent_industries.py`
- Test: `tests/test_tri_parent_industries.py`

**Interfaces:**
- Consumes: `tri_facility_years.reduce` output.
- Produces:
  - `SCHEMA = {'parent_name': pl.String, 'node_id': pl.String, 'n_facilities': pl.UInt64, 'n_facility_years': pl.UInt64, 'f_2022': pl.UInt64, 'f_2023': pl.UInt64, 'f_2024': pl.UInt64}`
  - `build_parent_industries(frame: pl.DataFrame) -> pl.DataFrame`: eligible rows with a
    `parent:` owner key, sorted by `parent_name`, `node_id`. `parent_name` is the key
    without its `parent:` prefix. `f_<year>` counts distinct TRIFDs in that year.
  - `validate_parent_industries(table: pl.DataFrame, frame: pl.DataFrame) -> None`
  - `parent_report(table: pl.DataFrame) -> dict`: the distributions of facilities and of
    industries per parent, in the shape of `n_unweighted_distribution`

- [ ] **Step 1: Write the failing tests**

```python
def test_one_row_per_parent_and_industry(): ...
    # P: T1 in a for 2022 and 2023, T2 in a for 2023, T3 in b for 2024
    assert rows == [('P', a, 2, 3, 1, 2, 0), ('P', b, 1, 1, 0, 0, 1)]
def test_self_owned_and_excluded_facility_years_are_left_out(): ...
def test_validator_rejects_counts_that_differ_from_the_facility_years(): ...
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_tri_parent_industries.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement the module**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_tri_parent_industries.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: list the NAICS 2022 industries of each TRI parent`.

---

### Task 9: Bundle build, verify and compare

**Files:**
- Create: `src/embedding_data/tri_bundle.py`
- Test: `tests/test_tri_bundle.py`

**Interfaces:**
- Consumes: Tasks 1–8; `target_contract.write_targets`; `target_io.stage`,
  `inventory`, `verify_inventory`, `write_json`, `file_record`, `relative_file`;
  `manifest`; `geography_references.safe_path`, `occupied`.
- Produces:
  - `TABLES = ('tri_parent_links', 'tri_parent_link_marginals', 'tri_parent_link_support', 'tri_parent_industries', 'tri_facility_years')`,
    `FILES = (*(t + '.parquet' for t in TABLES), 'inputs.json', 'report.json')`
  - `CONTRACTS = {'facility_years': 'tri-facility-years-v1', 'parent_links': 'tri-parent-links-v1', 'targets': 'targets-v1', 'headers': 'tri-headers-v1'}`
  - `SOFTWARE_FILES: tuple[str, ...]`: the measured import closure (Step 3) plus
    `src/embedding_data/tri_layouts.json`, `pyproject.toml` and `uv.lock`
  - `run_directory(data_dir: Path, run_id: str) -> Path`:
    `paths.derived_dir(data_dir, 'epa_tri') / 'parent-links' / run_id`
  - `freeze_software() -> dict`, in the shape of
    `ita_establishment_bundle.freeze_software` (`src/embedding_data/ita_establishment_bundle.py:166-176`)
  - `ordered_equal(first: pl.LazyFrame, second: pl.LazyFrame) -> dict`, the same
    semantics as Stage 10's (lines 179-202), written here
  - `build(data_dir: Path, run_id: str, *, codes_run: str, codes_outputs_sha256: str, processed_as_of: date, layouts: dict[int, HeaderLayout] | None = None) -> dict`,
    returning `{'run_id', 'directory', 'outputs_sha256'}`. `None` means
    `tri_layout.load_layouts()`.
  - `verify_bundle(directory: Path, data_dir: Path, *, expected_outputs_sha256: str, layouts: dict[int, HeaderLayout] | None = None) -> dict`
  - `compare_runs(first: Path, second: Path) -> dict`:
    `{'equal', 'tables', 'report_equal', 'trust_established': False}`

**`inputs.json`:** `run_id`, `contracts`, `codes` (`SelectedNodes.provenance()`), `raw`
(`tri_raw.citations`), `processed_as_of`, `window`, `layouts` (`layouts_json`), `rules`
(one sentence each for `facility_year`, `eligibility`, `owner`, `measure`, from the spec),
`software`, `execution` (`commit`, `dirty`, `created_at`).

**`report.json`:** `contracts`, `processed_as_of`, `by_year` (`year_report`, plus
`transcoded`), the Task 7 report keys, `parents` (`parent_report`), `tables` (rows,
columns and schema of each table), `limits` (the spec's Methodological limits bullets,
verbatim), `universe`, `size_gate` `'pending'`. No run ID, time, commit, path or D&B
number.

**Build order:** `target_io.stage`; `scratch = staging / '.scratch'`; `freeze_software()`;
`select_nodes`; `select_files`; `read_window`; `reduce`; `validate_facility_years`;
`estimate`; `validate_parent_links`; `build_parent_industries`;
`validate_parent_industries`. Then write the targets with `write_targets` and the other
tables with `sink_parquet`. Re-read every table, validate it again and compare it with
`ordered_equal`. Remove the scratch. Write `inputs.json` and `report.json`. Recheck the
codes selection, the software and the raw citations. Write `outputs.json`. Check the
exact file set, refuse an occupied final name, and rename. `finally`: remove only this
run's staging.

**Verify order:** a `.part` name fails; pin syntax; the SHA-256 of `outputs.json`; the
exact file set; `verify_inventory`; `outputs == target_io.inventory(...)`; strict
canonical JSON; run ID and contracts. The recorded layouts must equal the supplied
layouts. The recorded software must equal `freeze_software()`. Recompute everything in
`tempfile.TemporaryDirectory()` from the recorded codes run and pin and the recorded
`processed_as_of`. Compare each table in order, then the report, then `inputs.json` with
the recorded `execution`.

- [ ] **Step 1: Write the failing tests**

Use a module fixture: `seed_codes_bundle`, then `seed_tri_files` with a small three-year
window.

```python
def test_build_publishes_the_exact_file_set_and_detached_pin(built): ...
    # 8 files; outputs.json excludes itself; the pin equals sha256(outputs.json)
def test_verify_passes_then_refuses_a_changed_byte_report_or_pin(built, tmp_path): ...
@pytest.mark.parametrize('change', ['raw_byte', 'header', 'occupied_final',
                                    'codes_pin', 'other_layout'])
def test_build_refuses(change, ...): ...
def test_leftover_staging_is_refused_and_untouched(built, tmp_path):
    # create <id>.part with one file; build with <id> raises; the .part bytes are unchanged
    # and no <id> exists; build with a fresh ID succeeds
def test_software_change_before_publication_fails_without_a_final(monkeypatch, ...): ...
def test_failure_removes_only_its_own_staging(...): ...
def test_compare_runs_equal_and_unequal(...): ...
def test_report_has_no_run_identity(built): ...
def test_software_files_cover_the_bundle_import_closure():
    loaded = subprocess_modules('embedding_data.tri_bundle')
    assert {module_file(m) for m in loaded} <= set(tri_bundle.SOFTWARE_FILES)
```

Add two helpers to `tests/tri_fixtures.py`:
- `subprocess_modules(name: str, *, prefix: str | None = 'embedding_data') -> set[str]`:
  imports `name` in a fresh `sys.executable` process and returns the names in its
  `sys.modules`, only those that start with `prefix` unless `prefix` is None.
- `module_file(module: str) -> str`: `embedding_data` maps to
  `src/embedding_data/__init__.py`, and `embedding_data.x` to `src/embedding_data/x.py`.

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_tri_bundle.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement `tri_bundle`**

Get the closure with `uv run --locked python -c "import sys, embedding_data.tri_bundle, embedding_data.tri_parent_links; print(sorted(m for m in sys.modules if m.startswith('embedding_data')))"`.
Write `SOFTWARE_FILES` as a sorted literal of those files plus the three named ones.

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_tri_bundle.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: build, verify and compare TRI parent-link bundles`.

---

### Task 10: Complete command group and README

**Files:**
- Modify: `src/embedding_data/tri_parent_links.py`
- Modify: `README.md` (new section after "ITA establishment targets (Stage 10)")
- Test: `tests/test_tri_cli.py`

**Interfaces:**
- Consumes: `tri_bundle.build`, `verify_bundle`, `compare_runs`, `run_directory`.
- Produces the commands
  `build RUN_ID --codes-run ID --codes-outputs-sha256 PIN --processed-as-of DATE`,
  `verify RUN_ID --outputs-sha256 PIN` and `compare-runs FIRST SECOND`, each with
  `--data-dir`. `compare-runs` exits 1 outside the `_invoke` guard, as Stage 10 does
  (`src/embedding_data/ita_establishment_targets.py:96-106`). The failure path is
  `derived/epa_tri/parent-links/<run_id>` (Settled Default 20). `--processed-as-of` is
  parsed with `date.fromisoformat`. A bad date fails with `validation`.

- [ ] **Step 1: Write the failing tests**

```python
def test_help_lists_exactly_five_commands(cli_runner): ...
    # acquire, import-file, build, verify, compare-runs
def test_build_verify_and_compare_print_one_sorted_json_line(cli_runner, ...): ...
def test_build_failure_prints_only_the_fixed_line(cli_runner, ...):
    assert result.exit_code == 2
    assert result.output.strip() == ('TRI parent links build failed: validation; '
                                     f'run bad; path derived/epa_tri/parent-links/bad')
def test_unequal_compare_exits_1(cli_runner, ...): ...
def test_offline_commands_open_no_connection(cli_runner, monkeypatch, ...):
    forbid_external_access(monkeypatch)   # tests/target_fixtures.py
    monkeypatch.setattr(httpx.Client, '__init__', no_client)
    # import-file, build, verify, compare-runs all succeed
def test_command_module_loads_no_dotenv_or_ipumspy():
    loaded = subprocess_modules('embedding_data.tri_parent_links', prefix=None)
    assert 'dotenv' not in loaded and 'ipumspy' not in loaded
def test_software_files_equal_the_command_import_closure():
    closure = {module_file(m) for m in subprocess_modules('embedding_data.tri_parent_links')}
    assert set(tri_bundle.SOFTWARE_FILES) == closure | {
        'src/embedding_data/tri_layouts.json', 'pyproject.toml', 'uv.lock'}
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_tri_cli.py -q`
Expected: FAIL, no `build` command.

- [ ] **Step 3: Add the three commands**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_tri_cli.py tests/test_tri_bundle.py -q`
Expected: all pass.

- [ ] **Step 5: Write the README section**

Heading `## TRI parent links (roadmap Stage 5)`. Contents:
1. What O7 and O8 measure, and a link to `specs/tri-parent-links.md`.
2. The command table from the spec's "Module and commands".
3. The offline rule, the failure line, and that only `acquire` uses the network.
4. The production commands with `RUN_ID`, `RUN_PIN` and `DATE` placeholders, the codes
   run `stage4_v11_20261013_r2` and its pin, and
   `--data-dir /Users/lowell/Projects/embedding-data/data`.
5. The host rule.
6. The R8.4 exclusion.
7. That selected run pins wait for O12.

- [ ] **Step 6: Commit**

Message: `feat: add TRI build, verify and compare commands`.

---

### Task 11: V12 fixture chain

**Files:**
- Modify: `tests/tri_fixtures.py`
- Test: `tests/test_tri_v12.py`

**Interfaces:**
- Consumes: `seed_codes_bundle`, `seed_tri_files`, `tri_row`, `tri_bundle`,
  `forbid_external_access`.
- Produces in `tests/tri_fixtures.py`:
  - `V12_DATE = date(2025, 11, 5)`, `V12_RUNS = ('v12_first', 'v12_second')`
  - `V12_DNB: tuple[str, ...]`: every made-up D&B number in the fixture
  - `v12_rows() -> dict[int, list[dict[str, str]]]`
  - `run_tri_v12(tmp_path: Path, monkeypatch) -> dict` with keys `data_dir`, `first`,
    `second` (bundle directories), `first_pin`, `second_pin`, `first_verification`,
    `second_verification` and `comparison`. External access is blocked first, as in
    `ita_establishment_fixtures.run_establishment_v12`.

**Required cases (spec "V12 extension"):** a multi-form facility; a primary-code
conflict; a parent conflict; a mixed blank; a self-owned facility; a federal facility; a
code outside NAICS 2022; a D&B grouping that differs from the name grouping; a
same-year co-owned pair; a cross-year non-pair; an RY2023 foreign parent. Use real 2022
codes such as `325199`, `331110` and `562211`.

- [ ] **Step 1: Write the failing tests**

```python
def test_v12_chain_is_offline_verified_and_replay_equal(tmp_path, monkeypatch):
    result = run_tri_v12(tmp_path, monkeypatch)
    assert result['comparison']['equal'] is True
    assert result['first_verification']['outputs_sha256'] == result['first_pin']

def test_v12_fixture_holds_every_required_case(tmp_path, monkeypatch):
    years = pl.read_parquet(result['first'] / 'tri_facility_years.parquet')
    assert (years['n_forms'] >= 2).any()
    assert set(years['exclusion_reason'].drop_nulls()) == {
        'naics_conflict', 'naics_not_2022', 'parent_conflict', 'federal'}
    assert years['flag_parent_mixed_blank'].any()
    assert years.filter(pl.col('reporting_year') == 2023)['foreign_parent_names'].list.len().max() > 0
    # plus: a facility: owner key, a support row with j_dnb != j_owners, and no row for
    # the cross-year non-pair

def test_no_dnb_number_in_any_bundle_byte_or_failure_line(tmp_path, monkeypatch, cli_runner):
    for file in result['first'].iterdir():
        body = file.read_bytes()
        assert not any(number.encode() in body for number in V12_DNB)
    # a build that fails on a changed header prints a line without any V12_DNB number
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_tri_v12.py -q`
Expected: FAIL, `ImportError: cannot import name 'run_tri_v12'`.

- [ ] **Step 3: Implement `v12_rows` and `run_tri_v12`**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_tri_v12.py -q`
Expected: all pass. If one test takes 60 s or more, report it to the owner: marking it
`slow` means editing `tests/conftest.py`, which this plan does not do.

- [ ] **Step 5: Commit**

Message: `test: add the TRI V12 raw-to-replay fixture chain`.

---

### Task 12: Independent reconciler

**Files:**
- Create: `scripts/reconcile_tri_parent_links.py`
- Test: `tests/test_reconcile_tri_parent_links.py`

**Interfaces:**
- Consumes: nothing from Stage 5 modules. It imports only the standard library and
  `polars`, to read Parquet. No `embedding_data` import.
- Produces: `python scripts/reconcile_tri_parent_links.py --data-dir D --run ID --outputs-sha256 PIN`.
  It prints one sorted JSON line of counts and booleans, never a name, TRIFD or D&B
  number. It exits 0 when everything is equal, 1 when something differs and 2 on a
  refusal. Module constant `LAYOUT: dict[str, dict]` holds its own literal column map
  and value sets, in the shape of `tri_layout.layouts_json(...)['years']`. Tests load
  the script by path with `importlib.util.spec_from_file_location`.

**Independence:** it checks the pin, reads `inputs.json` for the three raw paths and
their SHA-256, and checks each raw file's hash. It reads `derived/codes/<run>/outputs.json`,
checks it against the recorded codes pin and the `naics_nodes.parquet` record, and reads
the national-industry node IDs. It reads the CSVs with `csv.reader` and its own decoding:
UTF-8 with a BOM stripped, and a per-line Windows-1252 fallback. With plain Python sets
and dicts it recomputes:
- the public facility-year rows
- eligibility
- `n(a)`, `J(a,b)` and the yearly `j`
- `N` for headline, D&B and federal
- both sensitivities and the partial-owner counts
- the O8 counts

It compares them exactly with the bundle's five tables and with `report['n_owners']`,
`report['by_year'][*]['rows_by_form_type']` and `['facility_years_by_reason']`.

- [ ] **Step 1: Write the failing tests**

```python
def test_reconciler_layout_equals_the_committed_layout():
    assert reconcile.LAYOUT == tri_layout.layouts_json(tri_layout.load_layouts())['years']
def test_reconciler_imports_no_embedding_data_module():
    tree = ast.parse(SCRIPT.read_text())
    assert not [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                and 'embedding_data' in ast.unparse(n)]
def test_reconciler_reports_equal_on_the_v12_bundle(tmp_path, monkeypatch): ...  # exit 0
def test_reconciler_detects_a_changed_count(tmp_path, monkeypatch): ...
    # copy the bundle, add 1 to one n_owners, rewrite outputs.json; pass the new pin: exit 1
def test_reconciler_refuses_a_wrong_pin(tmp_path, monkeypatch): ...   # exit 2
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_reconcile_tri_parent_links.py -q`
Expected: FAIL, the script does not exist.

- [ ] **Step 3: Implement the script from the spec's text**

Write it from the spec's sections, not from the build modules.

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_reconcile_tri_parent_links.py -q`
Expected: all pass.

- [ ] **Step 5: Full suite**

Run the Stage 9 `pgrep` check, then `uv run --locked behave` and
`uv run --locked pre-commit run coverage-check-full --hook-stage pre-push --all-files`.
Expected: every scenario and test passes (the `network` canary is deselected).

- [ ] **Step 6: Commit**

Message: `feat: add the independent TRI parent-link reconciler`.

---

### Task 13: First full-data build and acceptance (controller, owner-gated)

**Files:** none changed. Results go to the findings file in Task 14.

- [ ] **Step 1: Clean execution state**

The worktree holds every task's commit and `git status --porcelain` prints nothing, so
`execution.dirty` is false. Use `uv run --locked` from this worktree's own `.venv` for
every command in this task, with no overlay, and change nothing in the venv between
Steps 3 and 5.

- [ ] **Step 2: Go-ahead (Owner Checkpoint 5, host rule)**

Choose a fresh run ID `stage5_tri_parent_links_<YYYYMMDD>_r1` and confirm that neither it
nor `<id>.part` exists under `data/derived/epa_tri/parent-links/`.

- [ ] **Step 3: Build**

```bash
/usr/bin/time -l uv run --offline --locked python -m embedding_data.tri_parent_links build RUN_ID --codes-run stage4_v11_20261013_r2 --codes-outputs-sha256 15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a --processed-as-of DATE --data-dir /Users/lowell/Projects/embedding-data/data
```

Expected: one JSON line with `outputs_sha256`. Record the wall time and the maximum
resident set size. Record the bundle size with `du -sk`.

- [ ] **Step 4: Verify**

```bash
uv run --offline --locked python -m embedding_data.tri_parent_links verify RUN_ID --outputs-sha256 RUN_PIN --data-dir /Users/lowell/Projects/embedding-data/data
```

Expected: exit 0 and one JSON line.

- [ ] **Step 5: Reconcile**

```bash
uv run --offline --locked python scripts/reconcile_tri_parent_links.py --data-dir /Users/lowell/Projects/embedding-data/data --run RUN_ID --outputs-sha256 RUN_PIN
```

Expected: exit 0, with every comparison true.

- [ ] **Step 6: Preservation**

1. The current `data/raw/manifest.jsonl` starts with the bytes of the Task 4 baseline
   copy. The only lines after them are the three TRI entries.
2. `uv run --locked embedding-data audit --data-dir /Users/lowell/Projects/embedding-data/data`
   exits 0.
3. `derived/osha/ita_300a_summary.parquet` has SHA-256
   `6335cda7adb40a41c4a11d57d22048999449ac8d078a2ec0291f0198cd9136a8` and 139,930,636
   bytes.
4. Each bundle below passes `target_io.verify_inventory` against its own `outputs.json`,
   and that file's SHA-256 equals the pin:

| Bundle | Detached pin |
| --- | --- |
| `derived/codes/stage4_v11_20261013_r2` | `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |
| `derived/targets/stage6_ita_area_mix_20261014_1000_csv` | `084292b6835eb09ce27ecc4a3aef03a6f43bfe7b39b815665c29190a431e2473` |
| `derived/targets/stage6_ita_area_mix_20261014_1000_csv_replay` | `78fd21e37ba0c5b1cd396ff0961b557650788fdccd3c84a911e8c6c3b7fabe71` |
| `derived/osha/establishment-targets/stage10_ita_establishment_20261116_r1` | `e19b0d58f61f106c3994aa6fe51f4fb71244188145dd90f8cccaa8dc8a8b09df` |
| `derived/osha/establishment-targets/stage10_ita_establishment_20261116_r1_replay` | `e38e820b6e999f751687918d8f578b0f9d69ce145bbcb672b966a19a78d536a4` |

- [ ] **Step 7: On any failure**

Stop. Change no code. Report the failing step to the owner. Any cleanup of a failed
run's staging needs its own go-ahead.

---

### Task 14: Findings, source spec amendment and completion (controller)

**Files:**
- Modify: `specs/naics-evaluation-data-stage-5-findings.md`
- Modify: `specs/embedding-evaluation-data-spec.md`
- Modify: `CLAUDE.md` (conditional, Step 4)
- Modify at completion: `specs/naics-evaluation-data-roadmap.md`, `specs/deferred_items.md`,
  `specs/history.md`; move this plan and the spec to their `completed/` folders

- [ ] **Step 1: Finish the findings file (one screen)**

Add these sections:
1. The run ID, the detached pin, the snapshot date, and the wall time, maximum RSS and
   bundle size of the real run.
2. The `verify` and reconciler outcomes and the preservation results.
3. The main counts: facility-years by reason for each year, `N` for the three keys,
   target rows, cells only under a sensitivity, and partial owners.
4. The E8 time basis as a limit, and the `through_date` departure.
5. "For O12, O13 and O17", as the spec's Rollout lists them: the run ID, pin and
   snapshot date; the `n_unweighted` distribution and `size_gate_pending`; the counts,
   marginals, both sensitivity labels, the universe statement, the E8 time basis and
   the R8.4 exclusion.

Fixture results are not benchmarks.

- [ ] **Step 2: Check which shared amendment items are still open**

Run: `git fetch origin && git show origin/main:specs/embedding-evaluation-data-spec.md | grep -c "Evidence sources admitted by"`.
If the count is 0, apply Steps 3 and 4 in full. Otherwise another stage applied the
shared items first: apply only the TRI rows of Step 3 (the R1.1 row, the R7.2 row and
its sentence, and the R8.3 sentence), and skip Step 4.

- [ ] **Step 3: Amend `specs/embedding-evaluation-data-spec.md`**

Shared item 1 (introduction). Replace:

```
code harmonization, geography hierarchy, and output tables they share. The
```

with:

```
code harmonization, geography hierarchy, and output tables they share. Evidence
sources admitted by [the evidence-sources spec](uncovered-uses-evidence-sources.md)
add further families, each adopted by its own roadmap stage. The
```

Shared item 2 (Core principle). Replace:

```
from records in the three sources. No target is derived from the NAICS, SOC, or
```

with:

```
from records in the admitted sources (R1.1), or taken as published from an admitted
published aggregate (R7.5). No target is derived from the NAICS, SOC, or
```

Shared item 3 wording. Replace
`**R1.1** The required path draws on exactly three sources:` with
`**R1.1** The required path draws on three core sources:`.

TRI item 3 (always). After the CPS row of the R1.1 table, add:

```
| EPA Toxics Release Inventory (TRI) basic data files | Facility-year | Reporting years 2022–2024 | Industries that one U.S. parent operates together, and each parent's industries |
```

TRI item 6 (always). After the Co-ownership row of the R7.2 table, add:

```
| TRI parent links | EPA TRI | industry × industry within a U.S. parent, and parent × industry | NAICS |
```

Replace
`The co-ownership family is *(added at synthesis)*; the others are *(chosen; D)*.` with
`The co-ownership family is *(added at synthesis)*; the TRI parent links family is *(owner, Stage 5 design, 2026-11-18; [stage spec](completed/tri-parent-links.md))*; the others are *(chosen; D)*.`
The link points to the spec's retired path (Step 6).

TRI R8.3 sentence (only if E9 passed in Task 4). Replace
`establishment-level rows. *(verified; ITA)*` with
`establishment-level rows. *(verified; ITA)* TRI files are EPA data, in the public domain by default under EPA's data license. TRI-derived tables may contain facility-year and parent rows. They publish no Dun & Bradstreet number.`

- [ ] **Step 4: Amend `CLAUDE.md` (shared item 7, only when Step 2 counted 0)**

Replace:

```
embeddings from three sources: OSHA ITA Form 300A summaries, ACS via IPUMS USA, and CPS via IPUMS CPS.
```

with:

```
embeddings from three core sources: OSHA ITA Form 300A summaries, ACS via IPUMS USA, and CPS via IPUMS CPS. Evidence sources admitted by `specs/uncovered-uses-evidence-sources.md` add further families, each adopted by its own roadmap stage, starting with EPA TRI parent links (roadmap Stage 5, `python -m embedding_data.tri_parent_links`).
```

- [ ] **Step 5: Commit**

Message: `docs(specs): record the Stage 5 TRI findings and source spec amendment`.

- [ ] **Step 6: Plan Completion Protocol**

Run the writing-plans Plan Completion Protocol, including step 3a. The `## Handoff to
later stages` section gives:
- O12: the run ID, pin and snapshot date.
- O13: the `n_unweighted` distribution in `report.json` and `size_gate_pending`.
- O17: the counts, marginals and sensitivity labels.

The roadmap stamp notes that Stage 5 read only `naics_nodes.parquet` and not the Stage 4
concordance that its Consumes line names. Retire the spec to `specs/completed/` and
re-point moved links.

- [ ] **Step 7: Integrate**

Run the Stage 9 `pgrep` check, then open the PR and follow the owner's PR-lifecycle
rule.
