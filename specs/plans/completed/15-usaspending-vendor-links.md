# USAspending Vendor Links Implementation Plan

**Status: COMPLETE (2026-11-22)** — executed via subagent-driven-development; deferred items in specs/deferred_items.md, or specs/completed/deferred_items.md once archived

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one verified bundle that relates NAICS 2022 industries as supplier and buyer
through federal contract subawards (O6), from USAspending FY2024–2026 subaward downloads
joined by UEI to one SAM.gov public monthly entity extract.

**Architecture:** A standalone command group `python -m embedding_data.usaspending_vendor_links`
(spec build approach 1). New modules import reused ones unchanged. The document checks run
before any code or download. A preflight then settles E4 and E5 on the recorded raw files
and records the subaward header registry before the targets, the bundle and V12 are written
against it. One offline build streams the ZIP files, assigns report, firm and pair statuses,
derives the O6 target and its companions, and publishes an exclusive `.part` directory by
rename.

**Tech Stack:** Python 3.14, Polars 2.0 (lazy), Typer, httpx (acquisition only), standard
`zipfile` and `csv`, pytest, uv.

**Spec:** `specs/usaspending-vendor-links.md` (owner-approved 2026-11-18; approved text at
`4054d81`, on `main` at merge `48a37a8`).

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 14 — on plan completion, tick the stage and re-validate later stages against what shipped.

Scope: O6 (first build). Leaves out the replay build, a full-data `compare-runs`, the
long-form finding and the headline minimum count (the resume after Stage 14 decides), the
protocol section (O18) and the R8.4 training-role amendment.

Process: lighter (Stage 2 spec, "Rules for every new family"): one full-data build,
`verify`, the independent reconciler and a one-screen findings file. The controller runs
Task 1 (document checks), Task 9 (acquisition and data checks), Task 15 (full-data build)
and Task 16 (completion) itself, because a dispatched subagent cannot ask the owner for a
go-ahead.

## Global Constraints

- **Stage numbers.** This plan is Stage 14 of `specs/naics-evaluation-data-roadmap.md`.
  Stage numbers in `CLAUDE.md` and in code are the old roadmap's: Stage 4 codes bundle,
  Stage 6 area mix, Stage 9 ACS, Stage 10 ITA establishment. Plan 13 is roadmap Stage 5
  (TRI). `specs/plans/completed/5-geography-hierarchy-county-reference.md` is unrelated.
- **Branch.** Execute on a new branch cut from `main` at or after the merge that brings
  this plan, in a worktree under `.claude/worktrees/`.
- **Window.** Fiscal years `(2024, 2025, 2026)`, by subaward action date, 2023-10-01 to
  2026-09-30. The fiscal year of a date is its calendar year, plus one when its month is
  October or later (the spec's "calendar year of the date plus three months"). Contract
  subawards only. The build refuses any other window.
- **Codes identity.** Codes run `stage4_v11_20261013_r2`, detached `outputs.json` SHA-256
  `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`. Stage 14 reads its
  `naics_nodes.parquet` only, never the concordance. Node IDs look like
  `naics:2022:national_industry:541511`.
- **Contract versions (verbatim).** `vendor-link-pairs-v1`, `vendor-links-v1`,
  `targets-v1`. Registry versions: `usaspending-subaward-headers-v1` and
  `sam-extract-layout-v1`.
- **Target metadata (verbatim).** `source` `usaspending_sam`, `family` `vendor_links`,
  `unit_a_type` and `unit_b_type` `naics_national_industry`, `measure` `supplier_share` or
  `buyer_share`, `se` null, `se_method` `none`, `sample_set`
  `usaspending_subcontracts_fy2024_2026`, `vintage` `naics=2022`. Labels:
  `size_gate_pending` on every row, `numerator:intra_group_sensitivity:true`. `unit_a` is
  always the supplier industry and `unit_b` the buyer industry.
- **Universe (verbatim; `{snapshot}` is the ISO snapshot date, `{month}` is `YYYY-MM`).**
  "USAspending.gov contract subaward reports (FFATA subcontracts) with subaward action
  dates in federal fiscal years 2024–2026, downloaded under snapshot {snapshot}, joined by
  UEI to the SAM.gov public monthly entity extract of {month}. The population is federal
  prime contractors and the subcontractors they report, not a frame of firms or of
  business-to-business trade. A link is a distinct prime–subcontractor pair. Links within
  one corporate group, as the reported parent UEIs show, are excluded. Industries are each
  firm's self-reported primary NAICS 2022 code in SAM.gov at the extract date, not at the
  subaward date. Links, codes and amounts are self-reported and unvalidated."
- **Status strings (verbatim, in check order).** Report: `uei_unusable`,
  `action_date_invalid`, `outside_window`, `usable`. Firm: `not_in_sam`, `dnb_era_record`,
  `naics_missing`, `naics_conflict`, `naics_not_2022`, `eligible`. Pair: `self_link`,
  `intra_group`, `prime_ineligible`, `sub_ineligible`, `eligible`.
- **Value rules (verbatim).** Whitespace for every strip is the ASCII set
  `WHITESPACE = ' \t\n\r\x0b\x0c'`, in the build and in the reconciler alike. A UEI is
  usable when its stripped value matches `^[A-Z0-9]{12}$`. A primary code is blank
  (absence) when its stripped value is empty, and malformed when it is not blank and does
  not match `^[0-9]{6}$`. The subaward type must equal `sub-contract` as delivered. The D&B
  cutoff is `2022-04-04`: a record last updated before it is a `dnb_era_record`.
- **Paths.** Raw subawards: `data/raw/usaspending/subcontracts/<snapshot>/FY<YYYY>/<file name>`.
  Raw extract: `data/raw/sam/entity-extract/public-monthly-v2/<YYYY-MM>/<file name>`.
  Bundles: `data/derived/usaspending/vendor-links/<RUN_ID>/`. Findings:
  `specs/naics-evaluation-data-stage-14-findings.md`.
- **Runs.** Run IDs match `[A-Za-z0-9][A-Za-z0-9_-]*`. An existing final or
  `<RUN_ID>.part` fails. A later run never reuses, overwrites or deletes it.
- **Offline.** `import-subawards`, `import-sam-extract`, `build`, `verify` and
  `compare-runs` load no `.env`, read no credential, construct no HTTP client and run no
  upstream builder. `acquire-subawards` uses the network with no key.
  `acquire-sam-extract` is the only command that reads the key.
- **Diagnostics.** Success prints one sorted JSON line. Failure prints only
  `USAspending vendor links <command> failed: <reason>; run <run_id>; path <path>` to
  stderr and exits 2. `<reason>` is `validation`, `filesystem`, `network` or `unexpected`.
  It never prints exception text, row content, a URL or the key. Unequal `compare-runs`
  exits 1.
- **Key handling (spec "Key handling").** The key comes from `SAM_API_KEY`, an explicit
  `--env-file` or a hidden `--prompt`, and never populates the process environment. It is
  added only to the first wire URL, as `api_key`. Transport logging is muted while it is
  in use. A response body or redirect `Location` that holds it is refused and nothing from
  it is written. No error, log record, printed line, manifest entry or written file holds
  it.
- **No D&B Open Data.** The extract reader keeps only registered positions. No name,
  address or other D&B Open Data field enters a frame, a scratch file, a table, a report,
  the findings file or a printed line. No SAM.gov record last updated before 2022-04-04
  gives an industry.
- **No row values out of the preflight.** Preflight output and the findings file hold
  counts, shares, header cells, value shapes and tallies of coded values (subaward type,
  registration status, EVS source). Never a UEI, a name, an address or an amount.
  `vendor_link_pairs.parquet` holds UEIs (spec). Whether any table leaves the machine is
  E6.
- **Frozen code.** Edit no existing file under `src/` or `scripts/`, no existing test file,
  no `tests/conftest.py`, `pyproject.toml` or `uv.lock`. Stage 14 adds files only. Add no
  dependency. Import nothing from `ipums_census_access`: it imports `dotenv` at module top
  and its useful helpers are private. If a reused function cannot serve unchanged, stop
  and ask the owner.
- **Reused interfaces, imported unchanged.** `target_contract.write_targets`,
  `validate_targets`, `TARGET_SCHEMA`, `TARGET_KEY_COLUMNS`; `target_io.stage`,
  `relative_file`, `file_record`, `inventory`, `verify_inventory`, `write_json`,
  `verify_raw`; `manifest.describe_file`, `append_entries`, `check_appendable`,
  `entry_for`, `read_manifest`, `sha256_file`; `paths`; `geography_references.safe_path`,
  `occupied`; `osha_benchmark_download.USER_AGENT` (a string). Tests may also import
  `tests/ita_establishment_fixtures.py`, `tests/ita_fixtures.py`,
  `tests/target_fixtures.py`, `code_build`, `ita_summary`, `target_inputs` and
  `classification_tables`, and never edit them.
- **Import closure.** `target_io` imports `geography_references`, which imports
  `osha_benchmark_download`, `ita_references` and `geography_parsers`. Those modules load
  but are never called. `SOFTWARE_FILES` is the measured closure (Tasks 11 and 12), not a
  hand list. Importing the command module loads neither `dotenv` nor `ipumspy`.
- **Live-key guard.** `cli_runner` removes only `IPUMS_API_KEY`. Every new test module
  imports the autouse fixture `no_live_sam` from `tests/vendor_link_fixtures.py`
  (`from vendor_link_fixtures import no_live_sam  # noqa: F401`). It deletes `SAM_API_KEY`
  and makes both `make_client` seams raise, so a missed patch fails instead of spending one
  of the owner's 10 daily requests. Key tests set the fake key `FAKE_KEY` themselves.
- **Host rule (spec).** Run one acquisition at a time, because `manifest.append_entries`
  checks and then appends with no lock. Each of the four raw files is one acquisition. Run
  one full-data build at a time. Before each acquisition and each full-data build:
  1. Run `pgrep -fl 'embedding_data|embedding-data'` and show the owner its full,
     unfiltered output. It can match editors or agents whose command line holds the
     project path. The owner judges, and the run stops if it shows another acquisition or
     build.
  2. Run `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`.
     Stop if it prints anything.
  3. The owner confirms that no other stage's acquisition or build is running and that
     no Stage 9 freeze window is open. Evidence: `scripts/stage9_independent_io.py:144-149`
     inventories every file under `raw/` and `derived/`. Lines 290-292 fail on a new file
     that no manifest append explains (`'unaccounted new immutable files'`). A
     manifest-recorded raw file passes. A bundle or a `.part` that holds files fails. An
     empty `.part` directory is not seen.
- **Commit protocol.** Before every commit and every full `pytest` run, run the Stage 9
  `pgrep` check above. If it prints anything, stop, leave the files uncommitted and tell
  the owner. Never skip a hook. `git add` only the task's files.
- **Merging.** Stage 9's checker hashes every `.py` file under `src`, `scripts`, `tests`
  and `features` of the checkout it runs from. The PR merges under the owner's standing
  PR-lifecycle rule, with the Stage 9 `pgrep` check run right before the merge.
- **Long-running commands.** A foreground tool call is killed after 2 to 10 minutes, and a
  kill skips `finally`. A killed download then leaves a `.part` that makes every retry
  refuse the directory, and its removal needs the owner's go-ahead. So every controller
  command that can run longer than 2 minutes (`acquire-subawards`, which can poll for 4
  hours, the preflight's `measure`, the full-data `build`, `verify` and the reconciler)
  runs with `run_in_background`, or in the owner's own terminal.
- **Production root.** Write to `/Users/lowell/Projects/embedding-data/data` only at the
  owner-gated steps of Tasks 9 and 15. Every production command passes
  `--data-dir /Users/lowell/Projects/embedding-data/data`. Tests use `tmp_path` roots and
  always pass the data root explicitly.
- **Acceptance values.** The real counts are measured, never gated, except the spec's
  preflight triggers. No test contains a count from the real files. The 1,012
  national-industry nodes are a property of the pinned bundle and of the committed Stage 4
  fixture originals.
- **Style.** Single quotes, `'''` docstrings, 4-space indents, 99 columns,
  `uv run --locked ruff check .` clean. Polars with method-style expressions. No pandas.
- **R8.4.** No table feeds embedder training, curriculum, hard-negative mining or model
  selection. The README section and the findings file say so.
- **Fixtures.** Subaward files and extracts are synthetic, with made-up UEIs and no name or
  address values. Fixture results show software readiness and are never benchmarks.

## Owner Checkpoints

1. **Frozen modules (any task).** If a reused function cannot serve unchanged, stop and
   ask the owner. Do not edit it.
2. **Document reads (Task 1).** Get a go-ahead before downloading GSA's extract layout
   spreadsheet. Get a go-ahead before opening any usaspending.gov page in a browser,
   because the page calls the USAspending API. The owner may instead read the page and
   paste its text. The owner reads and pastes every sam.gov page: the accepted terms
   prohibit automated gathering from the SAM.gov website, the spec says this stage never
   reads a SAM.gov web page, and the terms page needs a login. Pages on open.gsa.gov may
   be fetched.
3. **Document stops (Task 1).** E6 fails its stop condition; the download filter does not
   select by subaward action date; the layout has no UEI, primary NAICS or last update
   date field. Each stops the stage before any code. Report and do nothing further.
4. **Production writes (Task 9).** Get a go-ahead under the host rule before each of the
   four fetches or imports. Before the extract, the owner chooses the path: the API with a
   key (`acquire-sam-extract`, after confirming the key is less than 90 days old) or a
   browser download and `import-sam-extract`. The plan assumes no key.
5. **Preflight stops (Task 9).** A failed E4 or E5 check, or a trigger, stops the stage.
   Report it and do nothing further. The owner records O6 as uncovered or promotes a named
   alternate. Never relax a registry or a reader to fit.
6. **Full-data run (Task 15).** Get a go-ahead under the host rule before the build and
   before any cleanup of a failed run's staging. If `verify`, the reconciler or a
   preservation check fails, stop, change no code and ask the owner.

## Review Focus

1. **Extra ZIP members.** USAspending can split one download into several CSV files, and a
   ZIP can carry a readme. The person expects every CSV member read once, in name order,
   and any other member to fail the build. Test: Task 6
   `test_every_csv_member_is_read_and_other_members_fail`.
2. **Free-text columns.** A subaward row with a quoted comma and a quoted newline in a
   description column is one report, with its UEI columns unshifted. Test: Task 6
   `test_quoted_newline_and_comma_keep_one_report`.
3. **Padded and lower-case UEIs.** `' ABC123DEF456 '` in the subaward file joins the
   extract row `'ABC123DEF456  '`. A lower-case UEI is `uei_unusable`, never upper-cased.
   Test: Task 7 `test_padded_ueis_join_after_the_strip_and_lower_case_is_unusable`.
4. **Key in an error path.** A transport error whose text holds the wire URL gives the
   fixed failure line, and the key is in no output, log record or file. Test: Task 3
   `test_transport_error_line_holds_no_key`.
5. **Killed build.** A leftover `<RUN_ID>.part` makes a rerun with that ID fail and stay
   byte-identical. A fresh ID builds. Test: Task 11
   `test_leftover_staging_is_refused_and_untouched`.

## Decisions

- **D1** (owner, plan review, 2026-11-18): Run the document checks, acquisition and the data checks (Tasks 1 and 9) before the targets, the bundle and V12, so that V12 uses the header layout that E4 records. The first build stays after V12. This amends the stage spec's Rollout bullet ("Approve"). Applied in: task order (Tasks 1–13), Task 16 Step 6 (spec amendment).
- **D2** (owner, plan review, 2026-11-18): A blank or invalid last update date on any extract row of a UEI makes that firm `dnb_era_record`, and the report counts such rows (Settled Default 12, "Exclude, count"). Applied in: Task 7.
- **D3** (owner, plan review, 2026-11-18): `compare-runs` compares the four Parquets and `report.json` exactly and skips `inputs.json` (Settled Default 19, "Skip inputs.json"). Applied in: Task 11.
- **D4** (owner, plan review, 2026-11-18): Approve plan 15 as committed at `d1769a2`, with the other Settled Defaults unchanged ("Approve plan 15"). Applied in: Settled Defaults.

## Settled Defaults (for owner review)

1. **Preflight first (a spec-level change).** The spec's Rollout says "Software readiness
   (tests and the V12 fixture) comes before full-data acceptance". Its full-data
   acceptance list starts with the document checks, acquisition and the data checks. Its
   V12 extension requires "synthetic subaward CSVs in the recorded header layout", and
   only E4 records that layout. The two texts cannot both hold. Plan 13 met the same
   conflict and the owner approved this order there (plan 13, D1). This plan runs the
   data checks as Task 9, before the targets, the bundle and V12. The first build stays
   after V12. The owner approved this order and the wording as D1. Task 16 Step 6 amends
   the Rollout bullet with the exact text shown there.
2. **Document checks before any code.** The spec runs them before any acquisition. This
   plan runs them as Task 1, before any code too, so a failed E6 wastes no work.
3. **Registries are committed JSON.** `src/embedding_data/sam_extract_layout.json` is
   written in Task 5 from the Task 1 spreadsheet read, before acquisition.
   `src/embedding_data/usaspending_subaward_headers.json` is written in Task 9 from E4
   data. `vendor_link_layouts` loads both. `SOFTWARE_FILES` hashes both.
4. **The preflight shares the build's code.** Unlike plan 13, `measure` imports the
   readers and status functions, so the 1% trigger, the malformed-code count and join
   coverage are exactly what the build will see. The reconciler stays the independent
   check. The preflight's scratch is a `tempfile.TemporaryDirectory()` outside the data
   root. It writes nothing under the data root.
5. **Own key module.** `sam_access` follows the `ipums_census_access` pattern and imports
   nothing from it. It imports `dotenv` inside `read_credential` only.
6. **SAM response handling.** The API answers with a ZIP body, or with at most one
   redirect. A redirect `Location` that holds any spelling of the key is refused. The
   target is fetched with no key and must answer 200. A body that does not start with the
   ZIP signature `PK\x03\x04` (a JSON error, for example) is refused before any byte is
   written. The content type is not checked. The body streams to `.part` behind an echo scan that holds back
   `len(longest spelling) - 1` bytes, so no complete spelling reaches disk. No automatic
   retry, because each attempt spends one daily request. `source_url` is the key-free API
   URL, never a redirect URL.
7. **Extract path (brief default).** Task 9's go-ahead asks the owner which path to use.
   No step assumes that a key exists.
8. **Subaward reading.** Each CSV member streams from `ZipFile.open` through a UTF-8 text
   wrapper (a leading BOM is removed and reported) into `csv.reader`. The reader checks
   the exact header and the field count of every record. It writes only the mapped
   columns and a row digest to Parquet parts in scratch, never a full copy. A byte that is
   not UTF-8 fails the build. The preflight reports it first, and the owner decides. No
   transcoding is built unless the owner asks.
9. **Extract reading.** The one member streams line by line. The reader checks the BOF
   and EOF framing lines, the delimiter count of every data line (no quote handling) and
   the record end marker if the layout names one. It keeps only registered positions and
   writes no scratch copy.
10. **Duplicates.** `row_digest` is the SHA-256 of
    `json.dumps(record, ensure_ascii=False, separators=(',', ':'))` over all fields in
    header order. Duplicate rows are rows minus distinct digests over the whole window,
    counted in the file year of the later copy.
11. **Amounts.** A stripped amount matching `^-?[0-9]{1,36}(\.[0-9]{1,2})?$` becomes
    `Decimal(38, 2)`. Anything else, blank included, adds nothing to a sum and is counted
    (`amount_unparseable`). It is never rounded and never fails the build. A pair whose
    amounts all fail has `amount_sum` 0.
12. **Dates.** A date is valid only when its stripped value round-trips exactly through
    the registry's `date_format`. A blank or invalid last update date on any row of a UEI
    makes that firm `dnb_era_record`, because the record cannot be shown to postdate the
    cutoff. The report counts such rows (`last_update_date_invalid`). The EVS rule applies
    only when the layout maps `evs_source`. Its D&B values are the layout set `evs_dnb`,
    from E5.
13. **Optional subaward fields.** `prime_parent_uei`, `sub_parent_uei`, `report_id`,
    `subaward_naics` and `prime_naics` may be null in the registry. At least one parent
    field must be mapped. A null parent field disables only the group conditions that
    need it, and the report lists missing fields.
14. **Triggers.** The 1% trigger divides the distinct UEIs on usable reports with status
    `naics_not_2022` by those with status `naics_conflict`, `naics_not_2022` or
    `eligible`, pooled over roles and the window. Coverage divides the distinct prime UEIs
    on usable reports with status `eligible` by all distinct prime UEIs on usable reports,
    and the same for subcontractors, pooled over the window. Both appear by fiscal year in
    the report.
15. **Subaward acquisition.** Task 1 fixes the request body. Polling waits
    `POLL_SECONDS = 30` between requests, at most `MAX_POLLS = 480` times (4 hours). A
    `failed` status, a timeout, or an occupied destination directory raises before any file
    is written. No automatic retry. The ZIP download follows redirects (no key is
    involved). `source_url` is the status response's `file_url`.
16. **Import naming.** `import-subawards` publishes under the original's name, which must
    match `^[A-Za-z0-9][A-Za-z0-9_.-]*\.zip$`. `import-sam-extract` requires the name
    `SAM_PUBLIC_UTF-8_MONTHLY_V2_<YYYYMMDD>.ZIP` with `YYYY-MM` equal to `--month`. Import
    entries have `client` `manual-import`, `client_version` the `embedding-data` version,
    `source_url` null and `proxies` `('retrieved_at',)`. `through_date` is null on every
    Stage 14 entry.
17. **Codes selector.** `vendor_link_codes` makes only the spec's checks, the same ones
    plan 13 lists for `tri_codes` (the Stage 5 selector is not on `main`). The table names,
    the node schema and `codes-ita-v1` are literals. Tests compare them with
    `target_inputs.CODE_SCHEMAS`, `classification_tables.NODE_SCHEMA` and
    `code_build.SCHEMA_VERSION`.
18. **Fixture chain.** It calls the Stage 10 helper's parts (`golden_releases`,
    `write_release`, `year_file`, `ita_summary.build_summary_table`,
    `import_stage4_originals`, `code_build.build`) and skips its index import and Stage 3
    expectations.
19. **`compare-runs`.** It compares the four Parquets in physical order and `report.json`
    exactly. `report.json` holds no run ID, time, commit, path or UEI. `inputs.json` is not
    compared, as in plan 13.
20. **Failure path.** The failure line prints the data-relative path
    (`raw/usaspending/subcontracts`, `raw/sam/entity-extract/public-monthly-v2`,
    `derived/usaspending/vendor-links/<run_id>`).
21. **`CLAUDE.md` item 7.** When another stage applied item 7 first, Task 16 appends
    Stage 14's module to that line instead of skipping it, so `CLAUDE.md` names every
    network command group.
22. **Reconciler registries.** The reconciler holds its own literal registries. A test
    checks that they equal the committed JSON.
23. **Reuse beyond the spec's list.** `target_io.verify_raw`, `manifest.check_appendable`
    and `read_manifest`, `geography_references.safe_path` and `occupied`, and the string
    `osha_benchmark_download.USER_AGENT` are imported unchanged. `target_io` already loads
    the first group, and `ipums_census_access` imports the user-agent string the same way.
24. **The key stays with the owner.** `--prompt` needs a real terminal, so the owner runs
    `acquire-sam-extract` in the owner's own terminal (Task 9 Step 3). The key never
    enters the controller's context.

---

## File Map

| Path | Task | Responsibility |
| --- | --- | --- |
| `src/embedding_data/usaspending_raw.py` | 2 | Subaward request, polling, download, import, snapshot selection, citations |
| `src/embedding_data/usaspending_vendor_links.py` | 2, 3, 12 | Typer command group |
| `src/embedding_data/sam_access.py` | 3 | Key reading and protected extract transport |
| `src/embedding_data/sam_raw.py` | 3 | Extract layout on disk, acquisition, import, month selection |
| `src/embedding_data/vendor_link_codes.py` | 4 | Codes selector |
| `src/embedding_data/vendor_link_layouts.py` | 5 | Registry model and loaders |
| `src/embedding_data/sam_extract_layout.json` | 5 | Production extract layout |
| `src/embedding_data/usaspending_subaward_headers.json` | 9 | Production subaward header registry |
| `src/embedding_data/vendor_link_readers.py` | 6 | Subaward and extract readers |
| `src/embedding_data/vendor_link_pairs.py` | 7 | Report, firm and pair statuses; accounting |
| `src/embedding_data/vendor_link_targets.py` | 10 | O6 target, marginals, support, validator |
| `src/embedding_data/vendor_link_bundle.py` | 11 | Build, verify, compare, software identity |
| `scripts/preflight_usaspending_sam.py` | 8 | E4/E5 data checks |
| `scripts/reconcile_usaspending_vendor_links.py` | 14 | Independent recount |
| `tests/vendor_link_fixtures.py` | 2–14 | Live-key guard, codes seeding, synthetic ZIPs, V12 chain |
| `tests/test_usaspending_raw.py`, `test_sam_access.py`, `test_sam_raw.py`, `test_vendor_link_*.py`, `test_usaspending_vendor_links_cli.py`, `test_preflight_usaspending_sam.py`, `test_reconcile_usaspending_vendor_links.py` | 2–14 | Tests |
| `README.md` | 12 | Command contract section |
| `specs/naics-evaluation-data-stage-14-findings.md` | 1, 9, 16 | Document checks, preflight, run and handoff |
| `specs/embedding-evaluation-data-spec.md`, `CLAUDE.md` | 16 | Source spec amendment |
| `specs/usaspending-vendor-links.md` | 16 | Rollout amendment, then retired |
| `specs/naics-evaluation-data-roadmap.md`, `specs/deferred_items.md`, `specs/history.md` | 16 | Completion records |

---

### Task 1: Document checks (controller, owner-gated)

**Files:**
- Create: `specs/naics-evaluation-data-stage-14-findings.md` (Document checks section)

No code and no data file in this task. Make one new empty scratch directory outside the
repository and the data root, with `mktemp -d /private/tmp/stage14-docs.XXXXXX`. Read
every document there as data. Save none under the data root and register none. For each
read, record in the findings file the URL (or repository path and commit), the read date
and the exact text the plan needs. Quotes of prose stay under 15 words. Field names,
enum values and code lines are copied exactly.

**Planning-time reads (2026-11-18, through a summarizing fetch tool, so unverified).**
Step 1 and Step 2 re-read each one from the source and correct the drafts below.
- `usaspending_api/api_contracts/contracts/v2/bulk_download/awards.md`: `filters`
  requires `agencies`, `date_range` and `date_type` (`action_date` or
  `last_modified_date`). `sub_award_types` takes `grant` or `procurement`. `file_format`
  defaults to `csv`. The response has `status_url`, `file_name`, `file_url`.
- `usaspending_api/download/v2/request_validations.py`: `sub_award_types` appends
  `elasticsearch_sub_awards` and `prime_award_types` appends `prime_awards` to
  `download_types`. An `agencies` entry named `All` is dropped. A range longer than 366
  days raises `date_range total days must be within a year`.
- `usaspending_api/api_contracts/contracts/v2/download/status.md`:
  `GET /api/v2/download/status?file_name=...`, `status` one of `failed`, `finished`,
  `ready`, `running`, and `file_url`.
- `https://open.gsa.gov/api/sam-entity-extracts-api/`: base URL
  `https://api.sam.gov/data-services/v1/extracts`; the key parameter is `api_key`. A
  monthly public UTF-8 request is
  `fileType=ENTITY&sensitivity=PUBLIC&frequency=MONTHLY&date=MM/YYYY&charset=UTF8`. The
  UTF-8 file name is `SAM_PUBLIC_UTF-8_MONTHLY_V2_YYYYMMDD.ZIP`. The page does not say
  whether the file comes directly or by redirect, or how many past months are kept. A
  non-federal user with no role gets 10 requests a day. The layout document is
  `SAM Master Extract Mapping v6.0 Public File V2 Layout.xlsx`.

Draft request body (FY2024), to confirm in Step 1:

```json
{"filters": {"sub_award_types": ["procurement"], "date_type": "action_date",
             "date_range": {"start_date": "2023-10-01", "end_date": "2024-09-30"},
             "agencies": [{"type": "awarding", "tier": "toptier", "name": "All"}]},
 "file_format": "csv"}
```

- [x] **Step 1: USAspending API source (E4 filter read)**

Read the `fedspendingtransparency/usaspending-api` source at the current `master` commit,
and record that commit. Fetch each file with
`gh api repos/fedspendingtransparency/usaspending-api/contents/<path> --jq .content | base64 --decode > <file>`.
The worktree guard refuses a command line that holds the substring of the version-control
tool's name, as the raw-content host and the raw media type do. Never open a
usaspending.gov page and never call the API. Record:
1. The request fields and the `agencies` shape that selects all agencies.
2. Whether an absent or empty `prime_award_types` keeps `prime_awards` out of
   `download_types`, so the ZIP holds subawards only.
3. How the 366-day check counts the length. FY2024 runs 2023-10-01 to 2024-09-30 and
   spans 29 February, so it must pass.
4. **E4 filter read.** Follow `elasticsearch_sub_awards` to the code that turns
   `date_type: action_date` and `date_range` into a query. Record the field it filters on.
   The design needs the subaward's own action date (`sub_action_date`).
5. The download column list for subawards: the CSV header names that carry the prime UEI,
   a prime parent UEI if any, the subcontractor UEI, the subcontractor parent UEI, the
   subaward action date, the amount, the type, a report identifier, the subaward NAICS and
   the prime award NAICS. Record the value that the type column carries for a contract
   subaward. These are hints. E4 data decide (Task 9).
6. The status response fields and their values.
7. Whether one download can be split into several CSV files, and how the files are named.

Write the final request body as `REQUEST_BODY` text into the findings file. Task 2 copies
it.

- [x] **Step 2: Entity Extracts API page**

Read `https://open.gsa.gov/api/sam-entity-extracts-api/` with `curl -sS -o extracts.html`
and read the HTML as data. Record: the `api_key` parameter; the exact request form for one
public monthly V2 UTF-8 file for a given month; the file naming rule; anything the page
says about the response (file body, redirect or JSON); how many past monthly files are
kept (E5); the rate limits (E5); the sentence on where the key comes from, and any expiry
or rotation statement. Task 3 copies the request form into `sam_access.extract_url`.

- [x] **Step 3: Extract layout spreadsheet (E5 read; Owner Checkpoint 2)**

Show the owner the spreadsheet's URL from the page and get the go-ahead. Download it with
`curl` into the scratch directory. Read it with a short script kept in a second new scratch
directory, using only `zipfile` and `xml.etree.ElementTree`, run as
`python3 -I <script> <file>`. Record:
1. The layout name and version.
2. The file framing: the delimiter, whether fields are ever quoted, the header (BOF) and
   trailer (EOF) records and their exact leading text, and any end-of-record marker.
3. The number of fields in one data record.
4. The 1-based positions of the UEI, the registration status (or extract code), the last
   update date and its format, the primary NAICS, the NAICS code string and its format,
   and the EVS source if the layout has it.
5. Every position that holds D&B Open Data (name, address, city, state, county code, ZIP,
   country), as the layout or the terms mark it. Task 5 records these as
   `restricted_positions`.

- [x] **Step 4: Terms (E6 read; Owner Checkpoint 2 for usaspending.gov)**

Read and record:
1. The live SAM.gov terms of use, and the key-rotation rule in them. The owner reads the
   page and pastes its text, as on 2026-11-18.
2. The D&B terms on `https://open.gsa.gov/api/entity-api/` (fetched).
3. Any statement about redistributing public entity data on open.gsa.gov (fetched) or on
   SAM.gov Data Services (the owner reads and pastes).
4. USAspending's terms or licensing page. Get a go-ahead before opening it in the built-in
   browser, or ask the owner to paste its text.

E6 asks three things (spec preflight table): whether a statement restricts publishing
aggregates or UEI-level rows derived from public subaward or public entity data; whether a
statement forbids the API access that the two acquisition commands use; whether a
statement forbids downloading the public extract, which carries name and address fields,
for this use.

> Deviation: The owner waived the read of the live USAspending page, so E6 stayed open when Task 1 closed (commit `ec3118e`). The owner closed E6 on 2026-11-19, after pasting the SAM.gov terms of use and saying "Yes, close E6" (commit `b30502f`). This was before any download.

- [x] **Step 5: Decide (Owner Checkpoint 3)**

Stop the stage and report to the owner when:
- E6 meets its stop condition. A failed terms check never becomes "build it but keep the
  aggregates local".
- Step 1 item 4 shows that `action_date` does not filter on the subaward action date
  (owner decides).
- The layout has no UEI, primary NAICS or last update date field.

Ask the owner before going on when Step 1 item 2 shows that prime awards cannot be kept
out of the ZIP, or when the request body differs from the draft in more than its values.

- [x] **Step 6: Commit**

Write the findings file with a title, a one-line status ("Stage 14 in progress"), and a
`## Document checks` section holding Steps 1–4. Commit it with the message
`docs(specs): record the Stage 14 document checks`. Delete both scratch directories.

---

### Task 2: Subaward raw files and commands

**Files:**
- Create: `src/embedding_data/usaspending_raw.py`
- Create: `src/embedding_data/usaspending_vendor_links.py`
- Create: `tests/vendor_link_fixtures.py`
- Test: `tests/test_usaspending_raw.py`, `tests/test_usaspending_vendor_links_cli.py`

**Interfaces:**
- Consumes: `manifest`, `paths`, `geography_references.safe_path`, `occupied`.
- Produces in `usaspending_raw`:
  - `SOURCE = 'usaspending'`, `WINDOW = (2024, 2025, 2026)`,
    `API_ROOT = 'https://api.usaspending.gov'`, `REQUEST_PATH = '/api/v2/bulk_download/awards/'`,
    `STATUS_PATH = '/api/v2/download/status'`, `POLL_SECONDS = 30`, `MAX_POLLS = 480`,
    `TIMEOUT = httpx.Timeout(600.0, connect=15.0)`, `CHUNK_SIZE = 1024 * 1024`,
    `USER_AGENT = 'embedding-data USAspending acquisition'`,
    `SAFE_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.zip')`,
    `ZIP_SIGNATURE = b'PK\x03\x04'`
  - `fiscal_year_range(fiscal_year: int) -> tuple[date, date]`: `(date(fy - 1, 10, 1), date(fy, 9, 30))`
  - `request_body(fiscal_year: int) -> dict`: Task 1's `REQUEST_BODY` with that range
  - `snapshot_dir(data_dir: Path, snapshot: date, fiscal_year: int) -> Path`:
    `paths.raw_dir(data_dir, SOURCE) / 'subcontracts' / snapshot.isoformat() / f'FY{fiscal_year}'`
  - `make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client` and
    `sleep = time.sleep`, module globals looked up at call time (test seams).
    `follow_redirects=True`, `trust_env=False`, headers `User-Agent: USER_AGENT` and
    `Accept-Encoding: identity`, `TIMEOUT`
  - `publish_partial(data_dir: Path, partial: Path, destination: Path, *, client: str, client_version: str, source_url: str | None, proxies: tuple[str, ...]) -> Path`:
    entry from the `.part` bytes with `retrieved_at=datetime.now(UTC)`,
    `manifest.check_appendable`, `os.link(partial, destination)`, append. Shared with
    `sam_raw`.
  - `acquire(data_dir: Path, fiscal_year: int, *, snapshot: date) -> Path`
  - `import_file(data_dir: Path, fiscal_year: int, original: Path, *, snapshot: date) -> Path`
  - `select_files(data_dir: Path, snapshot: date) -> dict[int, Path]`
  - `citations(data_dir: Path, files: Iterable[Path]) -> list[dict]`: each
    `asdict(manifest.entry_for(...))` read back through JSON, sorted by `path`
- Produces in `usaspending_vendor_links`: `app` (Typer, `pretty_exceptions_enable=False`,
  `pretty_exceptions_show_locals=False`), the option type `DataRoot`, `NO_RUN = '-'`,
  `SUBAWARDS = 'raw/usaspending/subcontracts'`,
  `EXTRACTS = 'raw/sam/entity-extract/public-monthly-v2'`, `_reason(error) -> str`,
  `_invoke(command, run_id, path, operation)`, and the commands
  `acquire-subawards FY --snapshot DATE` and `import-subawards FY FILE --snapshot DATE`.
  Copy the shape of `src/embedding_data/ita_establishment_targets.py:20-60` with the
  Stage 14 failure line. Dates are parsed with `date.fromisoformat`. A bad date fails with
  `validation`.
- Produces in `tests/vendor_link_fixtures.py`:
  - `FAKE_KEY = 'FAKEKEYfake0123456789ABCDEFghij'`
  - `no_live_sam` (an autouse pytest fixture): `monkeypatch.delenv('SAM_API_KEY', raising=False)`,
    and `usaspending_raw.make_client` replaced by a function that raises
    `AssertionError('live client')`. Task 3 adds `sam_access.make_client`.
  - `zip_bytes(members: dict[str, bytes]) -> bytes`

**Rules:**
- `acquire` refuses a year outside `WINDOW`. Before any request it checks that
  `snapshot_dir` is absent or an empty real directory, with no symlink in its path. Then it
  POSTs `request_body(fiscal_year)` to `API_ROOT + REQUEST_PATH`. The response JSON must
  hold a `file_name` that matches `SAFE_NAME`. It polls
  `GET API_ROOT + STATUS_PATH?file_name=<file_name>`. `ready` and `running` call
  `sleep(POLL_SECONDS)` and poll again. `finished` takes `file_url`. `failed` raises
  `ValueError('download request failed')`. Any other value raises `ValueError`. More than
  `MAX_POLLS` polls raise `ValueError('download request timed out')`.
- The download streams `file_url` into `<destination>.part`, opened `'xb'`, where
  `destination = snapshot_dir / file_name`. A missing `Content-Length` raises
  `ValueError('download has no Content-Length')`. A `Content-Encoding` other than
  `identity` raises `ValueError('encoded download')`. When
  `response.num_bytes_downloaded` differs from `Content-Length`, it raises
  `httpx.RemoteProtocolError`. The first four bytes must be `ZIP_SIGNATURE` and
  `zipfile.is_zipfile` must hold, else `ValueError('download is not a ZIP file')`. Then
  `publish_partial` with `client='httpx'`, `client_version=version('httpx')`,
  `source_url=file_url`, `proxies=()`. `finally` unlinks the `.part`. Nothing goes to
  stdout.
- `import_file` refuses a year outside `WINDOW`; an original that is a symlink, not a
  regular file, empty, not a ZIP, or whose name does not match `SAFE_NAME`; and an
  occupied `snapshot_dir`. It copies through an exclusive `.part`, compares the copy's
  SHA-256 with the original's, then calls `publish_partial` as Settled Default 16 says.
- `select_files` requires each window year's `snapshot_dir` to be a real directory
  holding exactly one entry: a regular `.zip` file that `manifest.entry_for` verifies. Any
  other state raises `ValueError` (`'raw file is not recorded'`,
  `'missing or extra raw file'`, `'raw file changed'`).

- [x] **Step 1: Write the failing tests**

```python
from vendor_link_fixtures import no_live_sam  # noqa: F401

@pytest.mark.parametrize('fy, start, end', [(2024, '2023-10-01', '2024-09-30'),
                                            (2025, '2024-10-01', '2025-09-30'),
                                            (2026, '2025-10-01', '2026-09-30')])
def test_request_body_selects_contract_subawards_by_action_date(fy, start, end):
    body = usaspending_raw.request_body(fy)
    assert body['filters']['sub_award_types'] == ['procurement']
    assert body['filters']['date_type'] == 'action_date'
    assert body['filters']['date_range'] == {'start_date': start, 'end_date': end}
    assert not body['filters'].get('prime_award_types')
    assert (date.fromisoformat(end) - date.fromisoformat(start)).days + 1 <= 366

def test_acquire_polls_then_downloads_and_records(data_directory, monkeypatch):
    # MockTransport: POST -> {'file_name': NAME, 'status_url': ..., 'file_url': URL};
    # status 'running' twice, then 'finished'; the ZIP body sent with
    # stream=httpx.ByteStream(body) and a Content-Length header. sleep records its calls.
    path = usaspending_raw.acquire(data_directory, 2025, snapshot=date(2026, 11, 20))
    assert path.relative_to(data_directory).as_posix() == (
        f'raw/usaspending/subcontracts/2026-11-20/FY2025/{NAME}')
    assert slept == [30, 30]
    entry = manifest.entry_for(paths.manifest_path(data_directory), path)
    assert (entry.client, entry.source_url, entry.proxies, entry.through_date) == (
        'httpx', URL, (), None)

@pytest.mark.parametrize('case', ['failed', 'timed_out', 'short', 'unsized', 'gzip',
                                  'not_zip', 'unsafe_name'])
def test_acquire_refuses_and_leaves_nothing(case, data_directory, monkeypatch): ...
    # raises; no final file, no .part, no manifest line

def test_acquire_refuses_an_occupied_destination_before_any_request(...): ...
    # a file (or a .part) in snapshot_dir: raises; the transport saw no request

def test_import_records_a_proxy_retrieval_time(data_directory, tmp_path):
    entry = ...   # as above, with ('manual-import', None, ('retrieved_at',), None)

def test_import_refuses_other_years_existing_paths_symlinks_and_bad_names(...): ...

def test_snapshot_selection_ignores_other_snapshots(data_directory, tmp_path):
    # import every window year under 2026-11-20 and again under 2027-01-05
    assert usaspending_raw.select_files(data_directory, date(2026, 11, 20)) == {...}
    # an extra file in one 2026-11-20 directory, a missing year, or changed bytes each
    # raise ValueError
```

In `tests/test_usaspending_vendor_links_cli.py`:

```python
def test_acquire_and_import_print_one_json_line(cli_runner, data_directory, ...): ...
def test_import_failure_prints_only_the_fixed_line(cli_runner, data_directory, tmp_path):
    result = cli_runner.invoke(usaspending_vendor_links.app, [
        'import-subawards', '2023', str(file), '--snapshot', '2026-11-20',
        '--data-dir', str(data_directory)])
    assert result.exit_code == 2
    assert result.output.strip() == ('USAspending vendor links import-subawards failed: '
                                     'validation; run -; path raw/usaspending/subcontracts')
```

- [x] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_usaspending_raw.py tests/test_usaspending_vendor_links_cli.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'embedding_data.usaspending_raw'`.

- [x] **Step 3: Implement `usaspending_raw`, the two commands and the fixture helpers**

- [x] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_usaspending_raw.py tests/test_usaspending_vendor_links_cli.py -q`
Expected: all pass.

- [x] **Step 5: Commit**

Message: `feat: acquire and import USAspending contract subaward downloads`.

---

### Task 3: SAM.gov extract, key handling and commands

**Files:**
- Create: `src/embedding_data/sam_access.py`
- Create: `src/embedding_data/sam_raw.py`
- Modify: `src/embedding_data/usaspending_vendor_links.py`, `tests/vendor_link_fixtures.py`
- Test: `tests/test_sam_access.py`, `tests/test_sam_raw.py`,
  `tests/test_usaspending_vendor_links_cli.py`

**Interfaces:**
- Consumes: `usaspending_raw.publish_partial`, `citations`; `osha_benchmark_download.USER_AGENT`.
- Produces in `sam_access`:
  - `CREDENTIAL = 'SAM_API_KEY'`, `KEY_PARAMETER = 'api_key'`,
    `EXTRACTS_URL = 'https://api.sam.gov/data-services/v1/extracts'`,
    `TIMEOUT = httpx.Timeout(600.0, connect=15.0)`, `CHUNK_SIZE = 1024 * 1024`
  - `quiet_transport()`: a context manager that sets `logging.disable(sys.maxsize)` and
    restores the previous level (the pattern of `ipums_census_access._quiet_transport`)
  - `read_credential(*, env_file: Path | None = None, prompt: bool = False) -> str`: the
    environment first, then `dotenv.dotenv_values(env_file, interpolate=False)` (imported
    inside the function), then `getpass` with `GetPassWarning` as an error and only when
    `sys.stdin.isatty()`. A blank value or one with a control character raises
    `ValueError('SAM_API_KEY unavailable or invalid; use the environment, --env-file or --prompt')`
  - `extract_url(month: str) -> str`: the key-free request URL from Task 1 Step 2, with
    `date=MM/YYYY` from `month`
  - `make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client`, a module
    global (test seam): `follow_redirects=False`, `trust_env=False`, `event_hooks={}`,
    headers `User-Agent: osha_benchmark_download.USER_AGENT` and `Accept-Encoding: identity`
  - `spellings(credential: str) -> tuple[bytes, ...]`: the UTF-8 bytes of the key and of
    its `quote(..., safe='')`, `quote_plus(..., safe='')`, JSON-escaped and HTML-escaped
    forms
  - `contains_echo(text: str, credential: str) -> bool`: the key in `text`, `unquote`,
    `unquote_plus` or `html.unescape` of either
  - `scan_chunks(chunks: Iterable[bytes], spellings: tuple[bytes, ...]) -> Iterator[bytes]`:
    yields the bytes that are safe to write, holding back
    `max(len(s) for s in spellings) - 1` bytes, and raises
    `ValueError('credential echoed by response')` when the held-back tail joined to the next
    chunk holds a spelling
  - `fetch_extract(url: str, credential: str, partial: Path) -> str`: streams the file
    into `partial` and returns the delivered file name
- Produces in `sam_raw`:
  - `SOURCE = 'sam'`, `NAME = re.compile(r'SAM_PUBLIC_UTF-8_MONTHLY_V2_(\d{4})(\d{2})\d{2}\.ZIP')`
  - `parse_month(value: str) -> str`: `YYYY-MM` with month `01`–`12`, else `ValueError`
  - `month_dir(data_dir: Path, month: str) -> Path`:
    `paths.raw_dir(data_dir, SOURCE) / 'entity-extract' / 'public-monthly-v2' / month`
  - `acquire(data_dir: Path, month: str, *, credential: str) -> Path`
  - `import_file(data_dir: Path, original: Path, *, month: str) -> Path`
  - `select_extract(data_dir: Path, month: str) -> Path`
- Produces in `usaspending_vendor_links`: `acquire-sam-extract --month YYYY-MM
  [--env-file PATH] [--prompt]` and `import-sam-extract FILE --month YYYY-MM`. Only
  `acquire-sam-extract` calls `sam_access.read_credential`.
- `tests/vendor_link_fixtures.py`: `no_live_sam` also replaces `sam_access.make_client`.

**`fetch_extract` rules.** Everything runs inside `quiet_transport()`. The wire URL is
`httpx.URL(url).copy_add_param(KEY_PARAMETER, credential)`, built inside the scope.
1. A 3xx answer needs a `Location`. `contains_echo(location, credential)` refuses it.
   The target is fetched once, with no key. A second 3xx refuses.
2. The final answer must be 200, with `Content-Encoding` `identity` or absent and a
   `Content-Length`.
3. The first chunk must start with `usaspending_raw.ZIP_SIGNATURE` before any byte is
   written. The body then streams into `partial`, opened `'xb'`, through `scan_chunks`.
4. The written length must equal `Content-Length`, and `zipfile.is_zipfile(partial)` must
   hold.
5. The file name is the `Content-Disposition` `filename`, or else the last path segment
   of the redirect target. It must fully match `sam_raw.NAME`.
6. Any exception inside the scope is caught. The handler only sets a flag. After the
   scope, a flagged run removes `partial` if this call created it, then raises
   `ValueError('SAM.gov extract request failed; details suppressed')` outside any handler,
   so no `__context__` keeps the wire URL or a body.

**`sam_raw` rules.** `acquire` requires `month_dir` to be absent or an empty real
directory before the request, fetches into `month_dir / 'download.part'`, requires the
name's `YYYY-MM` to equal `month`, and publishes `month_dir / name` with
`client='httpx'`, `client_version=version('httpx')`, `source_url=extract_url(month)`.
`import_file` and `select_extract` follow Task 2's rules, with `NAME` in place of
`SAFE_NAME` and its month check.

- [x] **Step 1: Write the failing tests**

In `tests/test_sam_access.py` (all with `httpx.MockTransport`, `FAKE_KEY` and bodies sent
with `stream=httpx.ByteStream(...)`):

```python
def test_key_is_sent_only_in_the_first_wire_url(tmp_path, monkeypatch):
    # direct ZIP and one-redirect cases: request 1 has api_key=FAKE_KEY; the redirect
    # target request has no api_key and no FAKE_KEY anywhere in its URL or headers
    ...

def test_key_reaches_no_file_log_line_or_error(cli_runner, data_directory, caplog, ...):
    caplog.set_level(logging.DEBUG)
    # run acquire-sam-extract through the CLI with SAM_API_KEY=FAKE_KEY
    assert FAKE_KEY not in result.output and FAKE_KEY not in caplog.text
    assert not any(FAKE_KEY.encode() in f.read_bytes()
                   for f in data_directory.rglob('*') if f.is_file())

@pytest.mark.parametrize('case', ['body_echo', 'body_echo_across_chunks', 'quoted_echo',
                                  'location_echo', 'location_percent_echo', 'json_body',
                                  'second_redirect', 'no_length', 'short', 'bad_name'])
def test_refused_responses_leave_nothing(case, tmp_path, monkeypatch):
    with pytest.raises(ValueError) as error:
        sam_access.fetch_extract(URL, FAKE_KEY, tmp_path / 'download.part')
    assert FAKE_KEY not in str(error.value) and error.value.__context__ is None
    assert not (tmp_path / 'download.part').exists()

@pytest.mark.parametrize('cut', range(1, len(FAKE_KEY)))
def test_holdback_writes_no_complete_spelling(cut):
    chunks = [b'PK\x03\x04 lead ' + FAKE_KEY[:cut].encode(), FAKE_KEY[cut:].encode() + b' tail']
    written = bytearray()
    with pytest.raises(ValueError):
        for part in sam_access.scan_chunks(chunks, sam_access.spellings(FAKE_KEY)):
            written.extend(part)
    assert FAKE_KEY.encode() not in written

def test_transport_error_line_holds_no_key(cli_runner, data_directory, monkeypatch, caplog):
    # the transport raises httpx.ConnectError(f'failed {request.url}')
    assert result.exit_code == 2
    assert result.output.strip() == ('USAspending vendor links acquire-sam-extract failed: '
                                     'validation; run -; path '
                                     'raw/sam/entity-extract/public-monthly-v2')
    assert FAKE_KEY not in result.output + caplog.text

def test_read_credential_order_and_refusals(tmp_path, monkeypatch):
    # environment wins over --env-file; --env-file leaves os.environ unchanged; --prompt
    # without a terminal, a blank value and a control character raise, without the value
```

In `tests/test_sam_raw.py`:

```python
def test_acquire_records_the_key_free_url(data_directory, monkeypatch):
    entry = manifest.entry_for(...)
    assert entry.source_url == sam_access.extract_url('2026-11')
    assert 'api_key' not in entry.source_url and entry.through_date is None

def test_acquire_refuses_an_occupied_month_before_any_request(...): ...
def test_import_requires_the_utf8_name_and_month(data_directory, tmp_path):
    # SAM_PUBLIC_MONTHLY_V2_20261102.ZIP (ASCII variant) and the UTF-8 name of 2026-10
    # with --month 2026-11 both raise ValueError
def test_month_selection_ignores_other_months(data_directory, tmp_path): ...
```

- [x] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_sam_access.py tests/test_sam_raw.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'embedding_data.sam_access'`.

- [x] **Step 3: Implement `sam_access`, `sam_raw` and the two commands**

- [x] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_sam_access.py tests/test_sam_raw.py tests/test_usaspending_vendor_links_cli.py -q`
Expected: all pass.

- [x] **Step 5: Commit**

Message: `feat: acquire and import the SAM.gov public extract without exposing the key`.

---

### Task 4: Codes selector

**Files:**
- Create: `src/embedding_data/vendor_link_codes.py`
- Modify: `tests/vendor_link_fixtures.py`
- Test: `tests/test_vendor_link_codes.py`

**Interfaces:**
- Consumes: `target_io.relative_file`, `verify_inventory`; `manifest.sha256_file`.
- Produces in `vendor_link_codes`:
  - `RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')`, `PIN = re.compile(r'[0-9a-f]{64}')`
  - `CODES_SCHEMA_VERSION = 'codes-ita-v1'`
  - `CODE_TABLES = ('naics_nodes', 'naics_edges', 'soc_nodes', 'soc_edges', 'naics_native_nodes', 'naics_concordance', 'filing_rules', 'code_paths', 'filing_rule_labels', 'filing_rule_membership', 'ita_naics_lookup', 'ita_300a_canonical')`
  - `INVENTORY_NAMES = {name + '.parquet' for name in CODE_TABLES} | {'inputs.json', 'report.json'}`
  - `NODE_SCHEMA = {'node_id': pl.String, 'system': pl.String, 'vintage': pl.Int64, 'level': pl.String, 'code': pl.String, 'title': pl.String}`
  - `NODE_PREFIX = 'naics:2022:national_industry:'`
  - `@dataclass(frozen=True) class SelectedNodes: data_dir: Path; codes_run: str; codes_outputs_sha256: str; outputs: dict; node_ids: frozenset[str]`,
    with `verify(self) -> None` (reselect and refuse any difference) and
    `provenance(self) -> dict` returning `{'run_id', 'outputs_sha256', 'outputs'}`
  - `select_nodes(data_dir: Path, codes_run: str, *, codes_outputs_sha256: str) -> SelectedNodes`
- Produces in `tests/vendor_link_fixtures.py`:
  `seed_codes_bundle(data_dir: Path, directory: Path) -> tuple[str, str]` (run ID, pin),
  calling, in order: for each `(year, rows)` of
  `ita_establishment_fixtures.golden_releases().items()`,
  `ita_fixtures.write_release(data_dir, year, ita_fixtures.year_file(year, rows))`; then
  `ita_summary.build_summary_table(data_dir)`;
  `ita_establishment_fixtures.import_stage4_originals(data_dir, directory)`;
  `code_build.build(data_dir, ita_establishment_fixtures.CODES_RUN)`.

**Selector checks, in order:** run ID and pin syntax; the SHA-256 of
`derived/codes/<run>/outputs.json` equals the pin; `target_io.verify_inventory` with
`INVENTORY_NAMES`; `inputs.json` and `report.json` have
`schema_version == CODES_SCHEMA_VERSION` and `inputs.json` has `run_id == codes_run`;
`naics_nodes.parquet` has exactly `NODE_SCHEMA`, and its rows and schema equal
`report['tables']['naics_nodes.parquet']`. `node_ids` are the `node_id` values with
`system == 'naics'`, `vintage == 2022` and `level == 'national_industry'`. Each starts with
`NODE_PREFIX`, and none repeats. No other file is read.

- [x] **Step 1: Write the failing tests**

```python
@pytest.fixture(scope='module')
def codes(tmp_path_factory):
    root = tmp_path_factory.mktemp('codes')
    run, pin = seed_codes_bundle(root / 'data', root / 'originals')
    return root / 'data', run, pin

def test_constants_match_stage4():
    assert set(vendor_link_codes.CODE_TABLES) == set(target_inputs.CODE_SCHEMAS)
    assert vendor_link_codes.NODE_SCHEMA == classification_tables.NODE_SCHEMA
    assert vendor_link_codes.CODES_SCHEMA_VERSION == code_build.SCHEMA_VERSION

def test_select_nodes_reads_the_national_industries(codes):
    selected = vendor_link_codes.select_nodes(data_dir, run, codes_outputs_sha256=pin)
    assert len(selected.node_ids) == 1012
    assert 'naics:2022:national_industry:541511' in selected.node_ids

def test_select_nodes_reads_no_ita_data(codes, tmp_path): ...
    # on a copy without derived/osha/ita_300a_summary.parquet and raw/osha: same node_ids

@pytest.mark.parametrize('mutation', ['run_id', 'pin_syntax', 'wrong_pin', 'extra_file',
                                      'changed_byte', 'schema_version', 'recorded_run_id'])
def test_select_nodes_refuses(codes, tmp_path, mutation): ...   # ValueError, on a copy

def test_verify_detects_a_later_change(codes, tmp_path): ...
```

- [x] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_vendor_link_codes.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [x] **Step 3: Implement `vendor_link_codes` and `seed_codes_bundle`**

- [x] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_vendor_link_codes.py -q`
Expected: all pass.

- [x] **Step 5: Commit**

Message: `feat: select the pinned Stage 4 NAICS nodes for vendor links`.

---

### Task 5: Registry model and the extract layout

**Files:**
- Create: `src/embedding_data/vendor_link_layouts.py`
- Create: `src/embedding_data/sam_extract_layout.json`
- Test: `tests/test_vendor_link_layouts.py`

**Registry JSON.**

```json
{"version": "usaspending-subaward-headers-v1", "years": {"2024": {
  "member_pattern": "...", "header": ["..."], "date_format": "%Y-%m-%d",
  "columns": {"prime_uei": "...", "sub_uei": "...", "action_date": "...", "amount": "...",
              "subaward_type": "...", "prime_parent_uei": null, "sub_parent_uei": "...",
              "report_id": null, "subaward_naics": null, "prime_naics": null}}}}
```

```json
{"version": "sam-extract-layout-v1", "layout": "...", "member_pattern": "...",
 "encoding": "utf-8", "delimiter": "|", "field_count": 0, "bof_prefix": "...",
 "eof_prefix": "...", "record_end": null, "date_format": "%Y%m%d",
 "positions": {"uei": 0, "registration_status": 0, "last_update_date": 0,
               "primary_naics": 0, "naics_code_string": 0, "evs_source": null},
 "evs_dnb": [], "restricted_positions": [0]}
```

**Interfaces:**
- Consumes: `usaspending_raw.WINDOW`.
- Produces in `vendor_link_layouts`:
  - `SUBAWARD_VERSION = 'usaspending-subaward-headers-v1'`,
    `EXTRACT_VERSION = 'sam-extract-layout-v1'`,
    `SUBAWARD_FILE = Path(__file__).with_name('usaspending_subaward_headers.json')`,
    `EXTRACT_FILE = Path(__file__).with_name('sam_extract_layout.json')`
  - `SUBAWARD_REQUIRED = ('prime_uei', 'sub_uei', 'action_date', 'amount', 'subaward_type')`,
    `SUBAWARD_OPTIONAL = ('prime_parent_uei', 'sub_parent_uei', 'report_id', 'subaward_naics', 'prime_naics')`,
    `EXTRACT_REQUIRED = ('uei', 'registration_status', 'last_update_date', 'primary_naics', 'naics_code_string')`,
    `EXTRACT_OPTIONAL = ('evs_source',)`
  - `@dataclass(frozen=True) class SubawardLayout: year: int; member_pattern: str; header: tuple[str, ...]; date_format: str; columns: dict[str, str | None]`,
    with the property `missing -> tuple[str, ...]` (unmapped optional fields)
  - `@dataclass(frozen=True) class ExtractLayout: layout: str; member_pattern: str; encoding: str; delimiter: str; field_count: int; bof_prefix: str; eof_prefix: str; record_end: str | None; date_format: str; positions: dict[str, int | None]; evs_dnb: frozenset[str]; restricted_positions: frozenset[int]`
  - `parse_subaward_layouts(value: dict, *, draft: bool = False) -> dict[int, SubawardLayout]`;
    `draft=True` allows null required columns (preflight only)
  - `subaward_layouts_json(layouts: dict[int, SubawardLayout]) -> dict`, so that
    `parse_subaward_layouts(subaward_layouts_json(x)) == x`
  - `load_subaward_layouts(file: Path = SUBAWARD_FILE) -> dict[int, SubawardLayout]`. A
    missing file raises `ValueError('production subaward header registry is not recorded')`.
  - `parse_extract_layout(value: dict) -> ExtractLayout`, `extract_layout_json(layout) -> dict`,
    `load_extract_layout(file: Path = EXTRACT_FILE) -> ExtractLayout`

**`parse_subaward_layouts` checks:** `version == SUBAWARD_VERSION`; years exactly
`WINDOW`; header cells nonblank and unique; every mapped column is a header cell and no
cell is mapped twice; every `SUBAWARD_REQUIRED` entry mapped (unless `draft`); at least one
of the two parent fields mapped (unless `draft`); `member_pattern` compiles;
`date_format` round-trips `date(2024, 2, 29)` through `strftime` and `strptime`.

**`parse_extract_layout` checks:** `version == EXTRACT_VERSION`; `encoding == 'utf-8'`;
`delimiter` is one character; `field_count >= 1`; every mapped position is in
`1..field_count` and distinct; every `EXTRACT_REQUIRED` entry mapped; no mapped position is
in `restricted_positions`; `evs_dnb` is empty when `evs_source` is null; `bof_prefix` and
`eof_prefix` nonblank and different; `member_pattern` compiles; `date_format` round-trips.
Each failure raises `ValueError`.

- [x] **Step 1: Write the failing tests**

`test_subaward_layout_json_round_trip`, `test_extract_layout_json_round_trip`,
`test_parse_subaward_layouts_refuses` and `test_parse_extract_layout_refuses` (each
parametrized over every check above), `test_draft_allows_null_required_columns`,
`test_a_null_prime_parent_is_listed_as_missing`,
`test_load_subaward_layouts_refuses_a_missing_file`, and:

```python
def test_production_extract_layout_keeps_clear_of_dnb_positions():
    layout = vendor_link_layouts.load_extract_layout()
    mapped = {p for p in layout.positions.values() if p is not None}
    assert layout.restricted_positions and not mapped & layout.restricted_positions
```

- [x] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_vendor_link_layouts.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [x] **Step 3: Implement `vendor_link_layouts` and write `sam_extract_layout.json`**

Copy every value of the layout from the findings file's Task 1 Step 3 record. Do not
guess a value that the record does not hold: stop and ask the owner instead.

- [x] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_vendor_link_layouts.py -q`
Expected: all pass.

- [x] **Step 5: Commit**

Message: `feat: add the vendor-link registry model and the SAM.gov extract layout`.

---

### Task 6: Subaward and extract readers

**Files:**
- Create: `src/embedding_data/vendor_link_readers.py`
- Modify: `tests/vendor_link_fixtures.py`
- Test: `tests/test_vendor_link_readers.py`

**Interfaces:**
- Consumes: `vendor_link_layouts.SubawardLayout`, `ExtractLayout`.
- Produces in `vendor_link_readers`:
  - `SUBAWARD_SCHEMA = {'file_year': pl.Int64, 'member': pl.String, 'record': pl.UInt64, 'prime_uei': pl.String, 'prime_parent_uei': pl.String, 'sub_uei': pl.String, 'sub_parent_uei': pl.String, 'action_date': pl.String, 'amount': pl.String, 'subaward_type': pl.String, 'report_id': pl.String, 'subaward_naics': pl.String, 'prime_naics': pl.String, 'row_digest': pl.String}`
  - `EXTRACT_SCHEMA = {'line': pl.UInt64, 'uei': pl.String, 'registration_status': pl.String, 'last_update_date': pl.String, 'primary_naics': pl.String, 'naics_code_string': pl.String, 'evs_source': pl.String}`
  - `BATCH_ROWS = 200_000`, `FIELD_SIZE_LIMIT = 1 << 30`
  - `@dataclass(frozen=True) class SubawardRead: rows: pl.LazyFrame; members: dict[int, tuple[str, ...]]; records: dict[int, int]; bom: dict[int, bool]`
  - `read_subawards(files: dict[int, Path], layouts: dict[int, SubawardLayout], scratch: Path) -> SubawardRead`:
    rows in `SUBAWARD_SCHEMA`, ordered by `file_year`, `member`, `record`
  - `read_extract(file: Path, layout: ExtractLayout) -> pl.DataFrame` in `EXTRACT_SCHEMA`,
    in line order
  - `subaward_headers(file: Path) -> dict`: for the preflight `headers` mode. For each
    member: `name`, `header` (the first record), `bom`, `utf8_valid`, `records`,
    `ragged` (records whose field count differs from the header's)
  - `extract_summary(file: Path, layout: ExtractLayout) -> dict`: `member`,
    `data_lines`, `field_counts` (a tally), `bof_matches`, `eof_matches`,
    `record_end_matches`, and `bof` and `eof` text only when they match their prefix
- Produces in `tests/vendor_link_fixtures.py`:
  - `TEST_SUBAWARD_LAYOUTS: dict[int, SubawardLayout]` and `TEST_EXTRACT_LAYOUT: ExtractLayout`:
    invented, test-owned registries with a 30-cell header, a free-text `description` cell,
    a 40-field extract with restricted positions
  - `subaward_record(layout: SubawardLayout, **fields: str) -> list[str]`: a full record
    in header order; unmapped cells `''`; keyword names are logical fields or, with the
    prefix `cell_`, raw header cells
  - `write_subaward_zip(file: Path, layout: SubawardLayout, members: dict[str, list[list[str]]], *, bom: bool = False, extra: dict[str, bytes] | None = None) -> None`
  - `extract_line(layout: ExtractLayout, **fields: str) -> str`: restricted positions hold
    `DNB_SENTINEL = 'DNB-SENTINEL-NAME'`, other unmapped positions `''`
  - `write_extract_zip(file: Path, layout: ExtractLayout, lines: list[str], *, member: str, bof: str | None = None, eof: str | None = None) -> None`:
    one ZIP member named `member`, with default BOF and EOF lines built from the layout's
    prefixes

**Subaward rules.** For each window year: open the ZIP. A directory entry, or a member that
does not fully match `layout.member_pattern`, raises `ValueError('unexpected ZIP member')`.
No member raises `ValueError('no subaward CSV member')`. Read members in name order through
`io.TextIOWrapper(archive.open(name), encoding='utf-8-sig', newline='')` and
`csv.reader`, with `csv.field_size_limit(FIELD_SIZE_LIMIT)` set and restored. The first
record must equal `list(layout.header)`, else `ValueError('changed header')`. Each later
record must have `len(layout.header)` fields, else `ValueError('ragged subaward record')`.
`UnicodeDecodeError` becomes `ValueError('subaward file is not UTF-8')` and `csv.Error`
becomes `ValueError('malformed subaward CSV')`. `record` counts data records from 1 in each
member. An unmapped optional field reads as `''`. `row_digest` follows Settled Default 10.
Write batches of `BATCH_ROWS` to `scratch / 'subawards' / f'{year}-{index:03d}-{batch:05d}.parquet'`.
The scanned row count must equal the records counted, else `ValueError('row count differs')`.

**Extract rules.** Exactly one member fully matching `layout.member_pattern`, else
`ValueError('unexpected extract member')`. Read lines through a text wrapper with
`layout.encoding`, removing one trailing `'\n'` and then one trailing `'\r'`. The first line
must start with `bof_prefix` and the last with `eof_prefix`, else
`ValueError('missing extract framing')`. Every other line is a data line:
`line.split(layout.delimiter)` must give `field_count` fields, else
`ValueError('wrong field count')`, and when `record_end` is set the last field must equal
it, else `ValueError('missing record end')`. Keep only the mapped positions (1-based), as
delivered. An unmapped `evs_source` reads as `''`. Discard the split list line by line.

- [x] **Step 1: Write the failing tests**

```python
def test_reads_the_mapped_columns_as_strings(tmp_path): ...
    # UEI '0ABC123DEF45', amount '1200.50', NAICS '000000' keep their exact text;
    # schema == SUBAWARD_SCHEMA

def test_every_csv_member_is_read_and_other_members_fail(tmp_path):
    # members 'Contracts_Subawards_1.csv' (2 rows) and '..._2.csv' (1 row): 3 rows, member
    # order kept; adding 'readme.txt', or a directory entry, raises 'unexpected ZIP member'

def test_quoted_newline_and_comma_keep_one_report(tmp_path):
    record = subaward_record(layout, prime_uei='AAAAAAAAAAA1', sub_uei='BBBBBBBBBBB2',
                             cell_description='Line one,\nline "two"')
    rows = read(...).collect()
    assert rows.height == 1 and rows['sub_uei'].item() == 'BBBBBBBBBBB2'

@pytest.mark.parametrize('change', ['renamed_cell', 'added_cell', 'swapped_cells', 'ragged'])
def test_changed_header_or_ragged_record_fails(change, tmp_path): ...

def test_bom_is_removed_and_reported(tmp_path): ...
def test_bytes_that_are_not_utf8_fail(tmp_path): ...
def test_row_digest_marks_identical_rows_only(tmp_path): ...
    # two identical records: one digest; a difference in an unmapped cell: two digests

def test_scratch_holds_only_the_mapped_columns(tmp_path):
    # a 'Fixture Name Co' value in an unmapped cell is in no scratch Parquet byte

def test_extract_keeps_only_registered_positions(tmp_path):
    frame = vendor_link_readers.read_extract(file, TEST_EXTRACT_LAYOUT)
    assert list(frame.schema.items()) == list(EXTRACT_SCHEMA.items())
    assert DNB_SENTINEL not in frame.write_csv()

@pytest.mark.parametrize('defect', ['no_bof', 'no_eof', 'short_line', 'long_line',
                                    'no_record_end', 'second_member'])
def test_extract_framing_and_field_count_failures(defect, tmp_path): ...
```

- [x] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_vendor_link_readers.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [x] **Step 3: Implement `vendor_link_readers` and the fixture helpers**

- [x] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_vendor_link_readers.py -q`
Expected: all pass.

- [x] **Step 5: Commit**

Message: `feat: stream USAspending subaward and SAM.gov extract ZIP files`.

---

### Task 7: Report, firm and pair statuses

**Files:**
- Create: `src/embedding_data/vendor_link_pairs.py`
- Test: `tests/test_vendor_link_pairs.py`

**Interfaces:**
- Consumes: `vendor_link_readers.SUBAWARD_SCHEMA`, `EXTRACT_SCHEMA`;
  `vendor_link_layouts.SubawardLayout`, `ExtractLayout`; `vendor_link_codes.NODE_PREFIX`.
- Produces in `vendor_link_pairs`:
  - `CONTRACT = 'vendor-link-pairs-v1'`, `WHITESPACE = ' \t\n\r\x0b\x0c'`,
    `UEI_PATTERN = r'^[A-Z0-9]{12}$'`, `CODE_PATTERN = r'^[0-9]{6}$'`,
    `AMOUNT_PATTERN = r'^-?[0-9]{1,36}(\.[0-9]{1,2})?$'`, `AMOUNT_TYPE = pl.Decimal(38, 2)`,
    `DNB_CUTOFF = date(2022, 4, 4)`, `SUBCONTRACT = 'sub-contract'`, `WINDOW = (2024, 2025, 2026)`
  - `REPORT_STATUSES`, `FIRM_STATUSES`, `PAIR_STATUSES`: the Global Constraints tuples
  - `subaward_types(rows: pl.LazyFrame) -> dict[str, int]`: delivered type value counts
  - `check_subaward_types(rows: pl.LazyFrame) -> None`: raises
    `ValueError('subaward type is not sub-contract')` when any row's value differs
  - `reports(rows: pl.LazyFrame, layouts: dict[int, SubawardLayout]) -> pl.LazyFrame`:
    `SUBAWARD_SCHEMA` plus `prime` and `sub` (stripped), `prime_parent` and `sub_parent`
    (stripped, null unless they match the UEI rule), `action` (Date, null when invalid),
    `fiscal_year` (Int64), `amount_value` (`AMOUNT_TYPE`, null when unparseable),
    `report_status`
  - In the functions below, `usable` is the `reports` output filtered to
    `report_status == 'usable'`.
  - `count_malformed(usable: pl.LazyFrame, extract: pl.DataFrame, layout: ExtractLayout) -> dict[str, int]`:
    `read_rows` (malformed primary codes on rows of UEIs that reach firm steps 3–5) and
    `unread_rows` (malformed codes on every other extract row)
  - `FIRM_SCHEMA = {'uei': pl.String, 'is_prime': pl.Boolean, 'is_sub': pl.Boolean, 'firm_status': pl.String, 'node_id': pl.String, 'n_extract_rows': pl.UInt64, 'flag_mixed_blank': pl.Boolean, 'flag_last_update_invalid': pl.Boolean, 'flag_code_not_in_string': pl.Boolean}`
  - `firms(usable: pl.LazyFrame, extract: pl.DataFrame, layout: ExtractLayout, node_ids: frozenset[str]) -> pl.DataFrame`:
    one row per distinct UEI on usable reports, sorted by `uei`. It raises
    `ValueError('malformed primary NAICS code')` when `count_malformed(...)['read_rows'] > 0`.
  - `PAIR_SCHEMA = {'prime_uei': pl.String, 'sub_uei': pl.String, 'n_reports': pl.UInt64, 'n_fy2024': pl.UInt64, 'n_fy2025': pl.UInt64, 'n_fy2026': pl.UInt64, 'prime_status': pl.String, 'sub_status': pl.String, 'prime_node_id': pl.String, 'sub_node_id': pl.String, 'flag_intra_group': pl.Boolean, 'pair_status': pl.String, 'amount_sum': AMOUNT_TYPE}`
  - `pairs(usable: pl.LazyFrame, firm_table: pl.DataFrame) -> pl.DataFrame`, sorted by
    `prime_uei`, `sub_uei`
  - `validate_pairs(table: pl.DataFrame, usable_reports: int) -> None`
  - `report_counts(reported: pl.LazyFrame, firm_table: pl.DataFrame, pair_table: pl.DataFrame, extract: pl.DataFrame, layouts: dict[int, SubawardLayout], layout: ExtractLayout, node_ids: frozenset[str]) -> dict`

**Report rules (spec "Report rules").** Statuses in `REPORT_STATUSES` order. A date is
valid when the stripped value parses with the row's year layout `date_format` and
formats back to the same text. `fiscal_year` is the year, plus one when the month is 10 or
later. Every row is kept. Duplicate rows are counted and kept.

**Corporate group (spec).** A pair is intra-group when any of its usable reports has
`sub_parent == prime`, `prime_parent == sub`, or both parents non-null and equal. A null
parent never forms a group.

**Firm rules (spec "Firm table").** Join extract rows to a UEI on the stripped extract
`uei`. Statuses in `FIRM_STATUSES` order:
- `dnb_era_record` when any row's stripped last update date is invalid or before
  `DNB_CUTOFF`, or its stripped `evs_source` is in `layout.evs_dnb`.
- `naics_missing` when no row has a non-blank stripped primary code.
- `naics_conflict` when the non-blank codes are not all equal.
- `naics_not_2022` when the one code is not `NODE_PREFIX + code` in `node_ids`.

`node_id` is set only for `eligible` firms. `flag_mixed_blank`: blank and non-blank rows
both present. `flag_code_not_in_string`: the one code is not among the six-digit runs of
`naics_code_string` (`str.extract_all(r'[0-9]+')`, kept when six long).

**Pair rules (spec "Pair table and eligibility").** Statuses in `PAIR_STATUSES` order.
`n_fy<year>` counts usable reports by their own fiscal year. `amount_sum` sums
`amount_value` over the pair's usable reports, 0 when none parse. `flag_intra_group`
records the group test for every pair, whatever its status. Node IDs come from the firm
table and are null unless that firm is eligible.

**`validate_pairs`:** exact schema; unique sorted key; `sum(n_reports) == usable_reports`;
`n_reports == n_fy2024 + n_fy2025 + n_fy2026`; each status from its tuple; the pair status
agrees with the self test, `flag_intra_group` and the two firm statuses in spec order;
node IDs non-null exactly for eligible firms.

**`report_counts` keys** (the preflight prints them and `report.json` stores them):
- `reports`: `by_file_year` (keys `'2024'`, `'2025'`, `'2026'`) and `total`, each with
  `rows`, `by_status` (the four statuses, summing to `rows`), `duplicate_rows`,
  `outside_file_year` (valid date, fiscal year differs from the file year),
  `amount_unparseable` (usable rows), `blank_uei` and `malformed_uei` (each
  `{'prime', 'sub'}`), `by_month` (`YYYY-MM` of valid dates), `distinct_report_ids` (null
  when unmapped), `subaward_naics_equal_prime` (`{'both', 'equal'}`, null when either is
  unmapped)
- `usable_by_fiscal_year`
- `firms`: `prime`, `subcontractor` and `all`, each a disjoint tally of `FIRM_STATUSES`;
  `mixed_blank`, `last_update_invalid`, `code_not_in_string`
- `pairs`: a disjoint tally of `PAIR_STATUSES` and `total`
- `join_coverage`: `prime` and `subcontractor`, each `{'eligible', 'total', 'share'}`, and
  `by_fiscal_year` in the same shape
- `trigger`: `{'naics_not_2022', 'with_code', 'share'}` (Settled Default 14)
- `extract`: `rows`, `by_registration_status`, `rows_per_uei` (`'1'`, `'2'`, `'3+'`),
  `last_update_by_year` (plus `'invalid'`), `evs_source` (a tally, null when unmapped),
  `primary_codes` (`{'blank', 'well_formed', 'in_2022', 'malformed'}` over all rows),
  `malformed_unread_rows`
- `missing_fields`: `subawards` by year and `extract`

- [x] **Step 1: Write the failing tests**

Unit tests use small typed frames built in `SUBAWARD_SCHEMA` and `EXTRACT_SCHEMA`, and a
node set of real 2022 codes (`541511`, `541512`, `236220`, `336411`).

```python
@pytest.mark.parametrize('prime, sub, date_, status', [
    ('', 'BBBBBBBBBBB2', '2024-01-05', 'uei_unusable'),
    ('AAAAAAAAAAA1', 'bbbbbbbbbbb2', '2024-01-05', 'uei_unusable'),
    ('AAAAAAAAAAA1', 'BBBBBBBBBBB2', '2024-02-30', 'action_date_invalid'),
    ('', 'BBBBBBBBBBB2', '', 'uei_unusable'),
    ('AAAAAAAAAAA1', 'BBBBBBBBBBB2', '2023-09-30', 'outside_window'),
    ('AAAAAAAAAAA1', 'BBBBBBBBBBB2', '2023-10-01', 'usable')])
def test_report_statuses_follow_the_spec_order(prime, sub, date_, status): ...

def test_fiscal_year_boundaries():
    # 2024-09-30 -> 2024, 2024-10-01 -> 2025; a FY2025 report in the FY2024 file counts
    # under 2025 and in outside_file_year

def test_a_sub_grant_row_fails(): ...   # check_subaward_types raises

@pytest.mark.parametrize('condition', ['sub_parent_is_prime', 'prime_parent_is_sub',
                                       'equal_parents'])
def test_each_corporate_group_condition(condition): ...
def test_blank_parents_form_no_group(): ...
def test_a_null_prime_parent_column_disables_two_conditions(): ...

@pytest.mark.parametrize('rows, status', [
    (none, 'not_in_sam'), (updated_2022_04_03, 'dnb_era_record'),
    (evs_dnb, 'dnb_era_record'), (invalid_update, 'dnb_era_record'),
    (blank_code, 'naics_missing'), (two_codes, 'naics_conflict'),
    (code_517311, 'naics_not_2022'), (updated_2022_04_04, 'eligible'),
    (agreeing_rows, 'eligible'), (blank_and_coded_rows, 'eligible')])
def test_firm_statuses_follow_the_spec_order(rows, status): ...

def test_padded_ueis_join_after_the_strip_and_lower_case_is_unusable():
    # subaward ' ABC123DEF456 ' joins extract 'ABC123DEF456  '; 'abc123def456' is
    # uei_unusable and never joins

def test_malformed_code_on_a_read_firm_fails_and_elsewhere_is_counted():
    # '54151A' on a row of a usable-report UEI: firms raises
    # the same code on an unread extract row, in naics_code_string or in subaward_naics:
    # counted in count_malformed()['unread_rows'] or the report, no failure
    # a dnb_era_record UEI with a malformed code: counted, no failure

@pytest.mark.parametrize('case, status', [
    (same_uei, 'self_link'), (group, 'intra_group'), (prime_not_in_sam, 'prime_ineligible'),
    (sub_conflict, 'sub_ineligible'), (both_eligible, 'eligible'),
    (self_link_in_group, 'self_link')])
def test_pair_statuses_follow_the_spec_order(case, status): ...

def test_amount_sum_keeps_cents_and_skips_unparseable_amounts():
    # '100.50', '-20', '1,000', '' -> Decimal('80.50') and amount_unparseable == 2

def test_validate_pairs_catches_lost_or_multiplied_reports(): ...
def test_report_counts_partitions_sum_to_their_totals(): ...
```

- [x] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_vendor_link_pairs.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [x] **Step 3: Implement `vendor_link_pairs`**

> Deviation: the `trigger` report key also holds `by_fiscal_year` beside its pooled keys (commit `2a60661`). The brief named the pooled keys only. Settled Default 14 and spec line 747 ask for the share by fiscal year (controller ruling, Task 7 review).

- [x] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_vendor_link_pairs.py -q`
Expected: all pass.

- [x] **Step 5: Commit**

Message: `feat: assign subaward report, firm and pair statuses`.

---

### Task 8: Preflight script

**Files:**
- Create: `scripts/preflight_usaspending_sam.py`
- Modify: `tests/vendor_link_fixtures.py`
- Test: `tests/test_preflight_usaspending_sam.py`

**Interfaces:**
- Consumes: `usaspending_raw.select_files`, `WINDOW`; `sam_raw.select_extract`;
  `vendor_link_codes.select_nodes`; `vendor_link_layouts`; `vendor_link_readers`;
  `vendor_link_pairs`; `manifest`; `paths`.
- Produces in `tests/vendor_link_fixtures.py`:
  `seed_raw(data_dir: Path, directory: Path, subawards: dict[int, dict[str, list[list[str]]]], extract_lines: list[str], *, snapshot: date, month: str, subaward_layouts, extract_layout, extract_member: str) -> None`.
  It writes the three ZIPs and the extract in `directory` and imports them with
  `usaspending_raw.import_file` and `sam_raw.import_file`. The extract file is named
  `SAM_PUBLIC_UTF-8_MONTHLY_V2_<YYYYMM>02.ZIP` from `month`.
- Produces `scripts/preflight_usaspending_sam.py` with two subcommands. Both take
  `--data-dir`, `--snapshot DATE` and `--sam-month YYYY-MM`, and print one JSON object.
  Exit 0 when no stop holds, 1 when one does, 2 on a refusal (an unrecorded or changed raw
  file, an unreadable registry). Tests load the script with
  `importlib.util.spec_from_file_location`.
  - `headers`: for each window year, the selected file's path and SHA-256 and
    `subaward_headers(file)`, plus `HINTS` matches: for each logical field, the header
    cells whose lower-case text, with `_` read as a space, contains every keyword of
    `HINTS[field]`. For the extract: path, SHA-256 and
    `extract_summary(file, load_extract_layout())`, plus, for each mapped position, the 10
    most frequent value shapes (`A` for a letter, `9` for a digit, other characters kept)
    and, for `registration_status` and `evs_source`, the value tally. Hints are not
    decisions.
  - `measure --registry FILE --codes-run ID --codes-outputs-sha256 PIN`: reads the draft
    registry with `parse_subaward_layouts(..., draft=True)` and the committed extract
    layout. It reads in a `tempfile.TemporaryDirectory()`. It prints `e4` (header rows,
    mapped columns, `subaward_types`, the shapes of `action_date` and `amount`, and the
    `reports` keys of `report_counts`), `e5` (the `firms`, `join_coverage`, `trigger` and
    `extract` keys, and `count_malformed`), then `stops`, `asks` and `ok`. When
    `count_malformed(...)['read_rows'] > 0`, `firms` would raise, so `measure` prints the
    E4 keys, the `extract` key and the malformed counts, lists the stop and skips the
    firm-dependent keys.
  - `HINTS = {'prime_uei': ('prime', 'uei'), 'prime_parent_uei': ('prime', 'parent', 'uei'), 'sub_uei': ('sub', 'uei'), 'sub_parent_uei': ('sub', 'parent', 'uei'), 'action_date': ('action', 'date'), 'amount': ('amount',), 'subaward_type': ('type',), 'report_id': ('report',), 'subaward_naics': ('naics',), 'prime_naics': ('naics',)}`

**Stops in `measure`:** a year with no `prime_uei`, `sub_uei` or `action_date` column; a
year with neither parent column (owner decides); `count_malformed(...)['read_rows'] > 0`
(owner decides, decision 4). **Asks:** the 1% trigger (`trigger.share > 0.01`); prime or
subcontractor coverage below 0.5; a year with no `subaward_type` or `amount` column; any
delivered type other than `sub-contract`. Document checks are not in the script.

- [x] **Step 1: Write the failing tests**

The tests write and import synthetic ZIPs with `seed_raw`, `TEST_SUBAWARD_LAYOUTS` and
`TEST_EXTRACT_LAYOUT`. The script takes
the extract layout from `load_extract_layout`, which the tests patch to
`TEST_EXTRACT_LAYOUT`. They use a codes bundle from `seed_codes_bundle`.

```python
def test_headers_prints_exact_rows_members_and_hints(...):
    report = run(['headers', ...])
    assert report['subawards']['2024']['members'][0]['header'] == list(HEADER_2024)
    assert report['extract']['bof_matches'] is True

def test_measure_counts_a_small_known_window(...):
    # 2024: 5 rows (one blank UEI, one outside window), 2 firms per role, one not in SAM
    report = run(['measure', ...])
    assert report['e4']['reports']['by_file_year']['2024']['by_status'] == {
        'uei_unusable': 1, 'action_date_invalid': 0, 'outside_window': 1, 'usable': 3}
    assert report['e5']['join_coverage']['subcontractor'] == {'eligible': 1, 'total': 2,
                                                              'share': 0.5}

@pytest.mark.parametrize('stop', ['no_sub_uei', 'no_parent_columns', 'malformed_read_code'])
def test_measure_reports_each_stop_and_exits_1(stop, ...): ...

@pytest.mark.parametrize('ask', ['above_one_percent', 'low_coverage', 'sub_grant_value'])
def test_measure_asks_and_exits_0(ask, ...): ...

def test_output_holds_no_uei_or_dnb_value(...):
    # no fixture UEI and no DNB_SENTINEL in either subcommand's output
def test_preflight_writes_nothing_under_the_data_root(...): ...
def test_preflight_refuses_an_unrecorded_file(...): ...   # exit 2
```

- [x] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_preflight_usaspending_sam.py -q`
Expected: FAIL, the script does not exist.

- [x] **Step 3: Implement the script**

- [x] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_preflight_usaspending_sam.py -q`
Expected: all pass.

- [x] **Step 5: Commit**

Message: `feat: add the USAspending and SAM.gov preflight checks`.

---

### Task 9: Acquisition, data checks and the subaward registry (controller, owner-gated)

**Files:**
- Create: `src/embedding_data/usaspending_subaward_headers.json`
- Modify: `specs/naics-evaluation-data-stage-14-findings.md` (Preflight section)
- Test: `tests/test_vendor_link_layouts.py` (one test added)

- [x] **Step 1: Preservation baseline**

Copy `data/raw/manifest.jsonl` to a new scratch directory outside the data root, and record
its SHA-256 and byte length. Run
`uv run --locked embedding-data audit --data-dir /Users/lowell/Projects/embedding-data/data`.
Expected: exit 0, no discrepancy.

- [x] **Step 2: Subaward files (Owner Checkpoint 4, host rule)**

Choose the snapshot label (`DATE`, ISO) with the owner. For each fiscal year, run the
host-rule checks, get the go-ahead, then run:

```bash
uv run --locked python -m embedding_data.usaspending_vendor_links acquire-subawards FY --snapshot DATE --data-dir /Users/lowell/Projects/embedding-data/data
```

Run it in the background (Global Constraints, "Long-running commands"). Expected: one JSON
line with a path under `raw/usaspending/subcontracts/DATE/FY<FY>/`.
If it refuses, the owner downloads that year in a browser from USAspending's Custom Award
Data page, with the Task 1 filters. Then run
`import-subawards FY FILE --snapshot DATE --data-dir ...` with its own go-ahead. Record
each file's path, size and SHA-256.

- [x] **Step 3: Extract (Owner Checkpoint 4, host rule)**

Ask the owner which path to use and which month (`YYYY-MM`, the latest available). For the
API path, the owner confirms the key exists and is less than 90 days old. The key never
passes through the controller: the owner runs this command in the owner's own terminal,
from this worktree, and types the key at the hidden prompt (`--prompt` needs a real
terminal). The controller then checks the result:

```bash
uv run --locked python -m embedding_data.usaspending_vendor_links acquire-sam-extract --month YYYY-MM --prompt --data-dir /Users/lowell/Projects/embedding-data/data
```

For the browser path, the owner downloads `SAM_PUBLIC_UTF-8_MONTHLY_V2_<YYYYMMDD>.ZIP` from
SAM.gov Data Services, then run `import-sam-extract FILE --month YYYY-MM --data-dir ...`.
Record the file's path, size and SHA-256.

> Deviation: The owner used the browser path. The browser download was a ZIP around the real extract ZIP, so the owner chose "Yes, import inner ZIP", and `import-sam-extract` recorded the inner ZIP with a proxy retrieval time (2026-11-19). The real member name carries a hex suffix, so the owner approved ("Approved for both") a change of the layout's member pattern (commits `b1f8095`, `634906b`). The owner then chose "Skip and count them" for 276 extract lines with the wrong field count. That overrides the spec rule that such a line fails the build (commits `5836d3c`, `f151645`, `0c9e52b`). Task 16 amended the spec text.

- [x] **Step 4: Headers**

Run `uv run --locked python scripts/preflight_usaspending_sam.py headers --data-dir /Users/lowell/Projects/embedding-data/data --snapshot DATE --sam-month YYYY-MM`
in the background (Global Constraints, "Long-running commands").
Write a draft registry in the scratch directory: copy each year's header row exactly, set
`member_pattern` to fit the observed member names of all three years, map each logical
field to one cell, and leave a field null when no cell holds it. Set `date_format` from
the shapes. Check the extract summary against the committed layout: every data line has
`field_count` fields and the framing matches.

- [x] **Step 5: Measure**

Run `measure` with the draft registry, the codes run and its pin, in the background. Keep
the final JSON output.

- [x] **Step 6: Decide (Owner Checkpoint 5)**

If `measure` lists any stop, stop the stage. Report to the owner and do no further task.
If `asks` is not empty, ask the owner before going on. Also stop and ask when: a ZIP holds
a member that is not a subaward CSV (the spec makes it fail every build); a year is not
valid UTF-8; the extract differs from the committed layout (field count, framing,
positions); the action date or amount shapes show a format the registry cannot express. A
missing optional field is recorded and does not stop.

- [x] **Step 7: Write the failing test**

```python
def test_production_subaward_registry_covers_the_window():
    layouts = vendor_link_layouts.load_subaward_layouts()
    assert sorted(layouts) == [2024, 2025, 2026]
    assert all(layout.columns['prime_uei'] and layout.columns['sub_uei']
               for layout in layouts.values())
```

Run: `uv run --locked pytest tests/test_vendor_link_layouts.py::test_production_subaward_registry_covers_the_window -q`
Expected: FAIL, `production subaward header registry is not recorded`.

- [x] **Step 8: Commit the registry and the preflight**

Save the final draft as `src/embedding_data/usaspending_subaward_headers.json` in
`subaward_layouts_json` form, then run the test again. Expected: PASS. Add a `## Preflight`
section to the findings file:
1. The snapshot label and extract month, and each raw file's path, size and SHA-256.
2. The member names, the registry's mapped cells and missing fields for each year.
3. E4 for each year: rows by status, blank and malformed UEIs by side, rows outside the
   file year, duplicate rows, rows by month (as a short table), the subaward-NAICS
   diagnostic.
4. E5: extract rows by registration status, rows per UEI, the last-update distribution,
   EVS values, primary-code shares, the malformed counts, join coverage by role, and the
   trigger rate.
5. The outcome of each stop and ask, and the owner's words for any ask.

Commit the registry, the test and the findings file with the message
`feat: record the measured subaward header registry and preflight`.

---

### Task 10: Vendor-link target (O6)

**Files:**
- Create: `src/embedding_data/vendor_link_targets.py`
- Test: `tests/test_vendor_link_targets.py`

**Interfaces:**
- Consumes: `vendor_link_pairs.PAIR_SCHEMA` and the `pairs` output;
  `target_contract.validate_targets`, `TARGET_SCHEMA`.
- Produces:
  - `CONTRACT = 'vendor-links-v1'`, `TOLERANCE = 1e-12`
  - `METADATA` (the constant target columns), `SIZE_LABEL = 'size_gate_pending'`,
    `INTRA_LABEL = 'numerator:intra_group_sensitivity:true'`, `UNIVERSE` (Global
    Constraints, with `{snapshot}` and `{month}`)
  - `MARGINAL_SCHEMA`: `node_id` String, then UInt64 `n_suppliers`, `n_buyers`,
    `n_supplier_pairs`, `n_buyer_pairs`, `n_suppliers_partial`, `n_buyers_partial`,
    `n_suppliers_including_intra_group`, `n_buyers_including_intra_group`
  - `SUPPORT_SCHEMA`: `unit_a`, `unit_b` String, then UInt64 `s_suppliers`, `b_buyers`,
    `l_pairs`, `l_fy2024`, `l_fy2025`, `l_fy2026`, `s_including_intra_group`,
    `b_including_intra_group`, `l_including_intra_group`, then `amount_sum`
    `Decimal(38, 2)`, then `n_reports` UInt64
  - `@dataclass(frozen=True) class VendorLinks: targets: pl.DataFrame; marginals: pl.DataFrame; support: pl.DataFrame; report: dict`
  - `estimate(pair_table: pl.DataFrame, *, snapshot: date, month: str) -> VendorLinks`
  - `validate_vendor_links(result: VendorLinks, pair_table: pl.DataFrame, node_ids: frozenset[str]) -> None`

**Algorithm (spec "Estimand").** `P` holds pairs with status `eligible`. The sensitivity
set `P+` adds pairs with status `intra_group` whose `prime_status` and `sub_status` are both
`eligible`. Over `P`, with `s = sub_node_id` and `d = prime_node_id`:
- `n_sup(s)`: distinct `sub_uei`; `n_buy(d)`: distinct `prime_uei`.
- `S(s,d)`: distinct `sub_uei` in cell `(s,d)`; `B(s,d)`: distinct `prime_uei`;
  `L(s,d)`: pairs; `l_fy<year>`: pairs with `n_fy<year> > 0`; `amount_sum` and
  `n_reports`: sums over the cell's pairs.
- The same five counts over `P+` give the `_including_intra_group` columns.
- `n_supplier_pairs(s) = Σ_d L(s,d)` and `n_buyer_pairs(d) = Σ_s L(s,d)`.
- `n_suppliers_partial(s)`: subcontractors in `n_sup(s)` that also have a pair with status
  `prime_ineligible`. `n_buyers_partial(d)`: primes in `n_buy(d)` that also have a pair with
  status `sub_ineligible`.

For each cell with `L >= 1`, emit `supplier_share` (`value = S / n_sup(s)`,
`n_unweighted = S`) and `buyer_share` (`value = B / n_buy(d)`, `n_unweighted = B`), with
`n_weighted = float(n_unweighted)`. Flags are sorted: `INTRA_LABEL` when the row's
sensitivity count (`S` or `B` over `P+`) differs from `n_unweighted`, and always
`SIZE_LABEL`. The diagonal is emitted. Marginal rows exist for each node with
`n_sup > 0` or `n_buy > 0`, sorted by `node_id`. Support rows are sorted by `unit_a`,
`unit_b`.

**`report` keys:** `n_suppliers`, `n_buyers`, `n_pairs` (each over `P` and over `P+`),
`diagonal` (`{'cells', 'pairs', 'share_of_pairs'}`), `cells_only_intra_group` (cells with
`L = 0` over `P` and `L >= 1` over `P+`), `n_unweighted_distribution` for each measure
(`count`, `min`, `p25`, `median`, `p75`, `p90`, `max`, and the counts at 1, 2, 3, 5 and 10
or more), `subcontractors_per_prime` and `primes_per_subcontractor` over `P` (the same
shape).

**Validator (spec "Validation"):** `validate_targets`; `METADATA` on every row; each unit in
`node_ids`; exactly one `supplier_share` and one `buyer_share` row for each `(s,d)`;
`1 <= S <= n_sup(s)`, `1 <= B <= n_buy(d)`, `max(S, B) <= L <= S * B`;
`|value - ratio| <= TOLERANCE`; `Σ_d L(s,d) == n_supplier_pairs(s)` and
`Σ_s L(s,d) == n_buyer_pairs(d)`; the support rows are exactly the target cells, with
`s_suppliers` and `b_buyers` equal to the `n_unweighted` values; the marginal rows agree
with the counts the pair table implies.

- [x] **Step 1: Write the failing tests**

```python
def test_each_firm_counts_once_however_many_reports_or_years(): ...
    # sub u (541511) with prime p (236220): 3 reports over FY2024 and FY2026
    assert support_row(s, d)['s_suppliers'] == 1 and support_row(s, d)['l_fy2025'] == 0

def test_firm_in_both_roles_counts_in_each_role(): ...
def test_diagonal_cell_is_emitted(): ...
def test_firm_shares_and_pair_counts_differ_for_a_large_prime():
    # prime p in d has 4 subs in s; prime q in d has 1 sub in s; n_sup(s) = 5, n_buy(d) = 2
    assert target('supplier_share', s, d)['value'] == 1.0
    assert target('buyer_share', s, d)['value'] == 1.0
    assert support_row(s, d)['l_pairs'] == 5

def test_values_are_ratios_of_firm_counts():
    # n_sup(s) = 4 with S(s,d) = 1: value 0.25, n_unweighted 1

def test_intra_group_sensitivity_counts_and_label(): ...
    # an intra_group pair raises s_including_intra_group and adds INTRA_LABEL; a cell
    # only under P+ is counted in report['cells_only_intra_group'] and not listed
def test_intra_group_pair_with_an_ineligible_firm_stays_out_of_the_sensitivity(): ...
def test_partial_counterparty_sets_are_counted_per_industry(): ...
def test_amount_sum_and_reports_sum_over_the_cell(): ...
def test_metadata_flags_and_universe():
    assert row['universe'] == UNIVERSE.format(snapshot='2026-11-20', month='2026-11')

@pytest.mark.parametrize('break_', ['missing_measure', 'value', 's_above_n', 'l_below_max',
                                    'l_above_product', 'unknown_node', 'pair_sum',
                                    'support_differs', 'marginal_differs'])
def test_validator_rejects(break_): ...
```

- [x] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_vendor_link_targets.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [x] **Step 3: Implement the module**

- [x] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_vendor_link_targets.py -q`
Expected: all pass.

- [x] **Step 5: Commit**

Message: `feat: estimate vendor-link firm shares with companions`.

---

### Task 11: Bundle build, verify and compare

**Files:**
- Create: `src/embedding_data/vendor_link_bundle.py`
- Modify: `tests/vendor_link_fixtures.py`
- Test: `tests/test_vendor_link_bundle.py`

**Interfaces:**
- Consumes: Tasks 2–10; `target_contract.write_targets`; `target_io.stage`, `inventory`,
  `verify_inventory`, `write_json`, `file_record`, `relative_file`, `verify_raw`;
  `manifest`; `geography_references.safe_path`, `occupied`; `seed_raw` (tests).
- Produces:
  - `TABLES = ('vendor_links', 'vendor_link_marginals', 'vendor_link_support', 'vendor_link_pairs')`,
    `FILES = (*(t + '.parquet' for t in TABLES), 'inputs.json', 'report.json')`
  - `CONTRACTS = {'pairs': 'vendor-link-pairs-v1', 'vendor_links': 'vendor-links-v1', 'targets': 'targets-v1', 'subaward_headers': 'usaspending-subaward-headers-v1', 'extract_layout': 'sam-extract-layout-v1'}`
  - `SOFTWARE_ROOT = paths.PROJECT_ROOT`; `SOFTWARE_FILES: tuple[str, ...]`, the measured
    import closure (Step 3) plus `src/embedding_data/usaspending_subaward_headers.json`,
    `src/embedding_data/sam_extract_layout.json`, `pyproject.toml` and `uv.lock`
  - `run_directory(data_dir: Path, run_id: str) -> Path`:
    `paths.derived_dir(data_dir, 'usaspending') / 'vendor-links' / run_id`
  - `freeze_software() -> dict`, in the shape of
    `ita_establishment_bundle.freeze_software` (`src/embedding_data/ita_establishment_bundle.py:166-176`)
  - `ordered_equal(first: pl.LazyFrame, second: pl.LazyFrame) -> dict`, the semantics of
    Stage 10's (lines 179-202), written here
  - `build(data_dir: Path, run_id: str, *, codes_run: str, codes_outputs_sha256: str, snapshot: date, sam_month: str, subaward_layouts: dict[int, SubawardLayout] | None = None, extract_layout: ExtractLayout | None = None) -> dict`,
    returning `{'run_id', 'directory', 'outputs_sha256'}`. `None` means the committed
    registry: `build` and `verify_bundle` then call
    `vendor_link_layouts.load_subaward_layouts()` and `load_extract_layout()` at call time,
    looked up on the module, so that tests can patch both loaders.
  - `verify_bundle(directory: Path, data_dir: Path, *, expected_outputs_sha256: str, subaward_layouts=None, extract_layout=None) -> dict`
  - `compare_runs(first: Path, second: Path) -> dict`:
    `{'equal', 'tables', 'report_equal', 'trust_established': False}`
- Produces in `tests/vendor_link_fixtures.py`:
  - `subprocess_modules(name: str, *, prefix: str | None = 'embedding_data') -> set[str]`:
    imports `name` in a fresh `sys.executable` process and returns the names in its
    `sys.modules`, only those that start with `prefix` unless `prefix` is None
  - `module_file(module: str) -> str`: `embedding_data` maps to
    `src/embedding_data/__init__.py`, and `embedding_data.x` to `src/embedding_data/x.py`

**`inputs.json`:** `run_id`, `contracts`, `codes` (`SelectedNodes.provenance()`), `raw`
(`{'subawards': citations, 'extract': citation}`), `snapshot`, `sam_month`, `window`,
`registries` (`{'subaward_headers': ..., 'extract_layout': ...}` in their JSON forms),
`rules` (one sentence each for `report`, `corporate_group`, `firm`, `pair`, `measure`, from
the spec), `software`, `execution` (`commit`, `dirty`, `created_at`).

**`report.json`:** `contracts`, `snapshot`, `sam_month`, `window`, the `report_counts`
keys, the Task 10 report keys, `bom` (the years whose CSV members start with a BOM),
`tables` (rows, columns and schema of each table), `limits` (the spec's Methodological limits
bullets, verbatim), `universe`, `size_gate` `'pending'`. No run ID, time, commit, path or
UEI.

**Build order:** `target_io.stage`; `scratch = staging / '.scratch'`; `freeze_software()`;
`select_nodes`; `usaspending_raw.select_files`; `sam_raw.select_extract`; `read_subawards`;
`check_subaward_types`; `reports`; `read_extract`; `firms`; `pairs`; `validate_pairs`;
`report_counts` (on the same frames); `estimate`; `validate_vendor_links`. Then write the targets with `write_targets` and the
other tables with `write_parquet`. Re-read every table, validate it again and compare it
with `ordered_equal`. Remove the scratch. Write `inputs.json` and `report.json`. Recheck the
codes selection, the software and the raw citations (`verify_raw`). Write `outputs.json`.
Check the exact file set, refuse an occupied final name, and rename. `finally`: remove only
this run's staging.

**Verify order:** a `.part` name fails; pin syntax; the SHA-256 of `outputs.json`; the
exact file set; `verify_inventory`; `outputs == target_io.inventory(...)`; strict canonical
JSON; run ID and contracts. The recorded registries must equal the supplied ones. The
recorded software must equal `freeze_software()`. Recompute everything in
`tempfile.TemporaryDirectory()` from the recorded codes run and pin, snapshot and month.
Compare each table in order, then the report, then `inputs.json` with the recorded
`execution`.

- [x] **Step 1: Write the failing tests**

Use a module fixture: `seed_codes_bundle`, then `seed_raw` with a small three-year window
in the test registries.

```python
def test_build_publishes_the_exact_file_set_and_detached_pin(built): ...
    # 7 files; outputs.json excludes itself; the pin equals sha256(outputs.json)
def test_verify_passes_then_refuses_a_changed_byte_report_or_pin(built, tmp_path): ...
@pytest.mark.parametrize('change', ['raw_byte', 'header', 'sub_grant', 'malformed_code',
                                    'occupied_final', 'codes_pin', 'other_registry',
                                    'missing_year'])
def test_build_refuses(change, ...): ...
def test_leftover_staging_is_refused_and_untouched(built, tmp_path):
    # create <id>.part with one file; build with <id> raises; the .part bytes are unchanged
    # and no <id> exists; build with a fresh ID succeeds
def test_software_change_before_publication_fails_without_a_final(monkeypatch, ...): ...
def test_failure_removes_only_its_own_staging(...): ...
def test_compare_runs_equal_and_unequal(...): ...
def test_report_has_no_run_identity_or_uei(built): ...
def test_software_files_cover_the_bundle_import_closure():
    loaded = subprocess_modules('embedding_data.vendor_link_bundle')
    assert {module_file(m) for m in loaded} <= set(vendor_link_bundle.SOFTWARE_FILES)
```

- [x] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_vendor_link_bundle.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [x] **Step 3: Implement `vendor_link_bundle`**

Get the closure with `uv run --locked python -c "import sys, embedding_data.vendor_link_bundle, embedding_data.usaspending_vendor_links; print(sorted(m for m in sys.modules if m.startswith('embedding_data')))"`.
Write `SOFTWARE_FILES` as a sorted literal of those files plus the four named ones.

- [x] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_vendor_link_bundle.py -q`
Expected: all pass.

- [x] **Step 5: Commit**

Message: `feat: build, verify and compare vendor-link bundles`.

---

### Task 12: Complete command group and README

**Files:**
- Modify: `src/embedding_data/usaspending_vendor_links.py`
- Modify: `README.md` (new section before `## Data sources`)
- Test: `tests/test_usaspending_vendor_links_cli.py`

**Interfaces:**
- Consumes: `vendor_link_bundle.build`, `verify_bundle`, `compare_runs`, `run_directory`.
- Produces the commands
  `build RUN_ID --codes-run ID --codes-outputs-sha256 PIN --snapshot DATE --sam-month YYYY-MM`,
  `verify RUN_ID --outputs-sha256 PIN` and `compare-runs FIRST SECOND`, each with
  `--data-dir`. `compare-runs` exits 1 outside the `_invoke` guard, as Stage 10 does
  (`src/embedding_data/ita_establishment_targets.py:96-106`). The failure path is
  `derived/usaspending/vendor-links/<run_id>` (Settled Default 20).
- Test seam: the committed subaward registry holds the real header, so every test in this
  task patches `vendor_link_layouts.load_subaward_layouts` and `load_extract_layout` to
  return `TEST_SUBAWARD_LAYOUTS` and `TEST_EXTRACT_LAYOUT`, and seeds data with `seed_raw`
  in those registries. The offline test does the same.

- [x] **Step 1: Write the failing tests**

```python
def test_help_lists_exactly_seven_commands(cli_runner): ...
    # acquire-subawards, acquire-sam-extract, import-subawards, import-sam-extract, build,
    # verify, compare-runs
def test_build_verify_and_compare_print_one_sorted_json_line(cli_runner, ...): ...
def test_build_failure_prints_only_the_fixed_line(cli_runner, ...):
    assert result.output.strip() == ('USAspending vendor links build failed: validation; '
                                     'run bad; path derived/usaspending/vendor-links/bad')
def test_unequal_compare_exits_1(cli_runner, ...): ...
def test_offline_commands_open_no_connection_and_read_no_key(cli_runner, monkeypatch, ...):
    forbid_external_access(monkeypatch)   # tests/target_fixtures.py
    monkeypatch.setattr(httpx.Client, '__init__', no_client)
    monkeypatch.setattr(sam_access, 'read_credential', forbidden)
    monkeypatch.setenv('SAM_API_KEY', FAKE_KEY)
    # import-subawards, import-sam-extract, build, verify, compare-runs all succeed
def test_command_module_loads_no_dotenv_ipumspy_or_census_access():
    loaded = subprocess_modules('embedding_data.usaspending_vendor_links', prefix=None)
    assert not {'dotenv', 'ipumspy', 'embedding_data.ipums_census_access'} & loaded
def test_software_files_equal_the_command_import_closure():
    closure = {module_file(m)
               for m in subprocess_modules('embedding_data.usaspending_vendor_links')}
    assert set(vendor_link_bundle.SOFTWARE_FILES) == closure | {
        'src/embedding_data/usaspending_subaward_headers.json',
        'src/embedding_data/sam_extract_layout.json', 'pyproject.toml', 'uv.lock'}
```

- [x] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_usaspending_vendor_links_cli.py -q`
Expected: FAIL, no `build` command.

- [x] **Step 3: Add the three commands**

- [x] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_usaspending_vendor_links_cli.py tests/test_vendor_link_bundle.py -q`
Expected: all pass.

- [x] **Step 5: Write the README section**

Merge `main` into the branch first: plans 13 and 14 add sections in the same place. Place
the section by its anchor (before `## Data sources`), not by line number. Heading
`## USAspending vendor links (roadmap Stage 14)`. Contents:
1. What O6 measures, and a link to `specs/usaspending-vendor-links.md`.
2. The command table from the spec's "Module and commands".
3. The offline rule, the failure line, which commands use the network and that only
   `acquire-sam-extract` reads the key. Never run either acquisition command unless the
   owner asks.
4. Key handling: `SAM_API_KEY`, `--env-file`, `--prompt`, the 90-day rotation, and that
   the key never reaches a file, log, manifest or output.
5. The production commands with `RUN_ID`, `RUN_PIN`, `DATE` and `YYYY-MM` placeholders,
   the codes run `stage4_v11_20261013_r2` and its pin, and
   `--data-dir /Users/lowell/Projects/embedding-data/data`.
6. The host rule.
7. The R8.4 exclusion, and that whether any table leaves the machine follows E6.
8. That selected run pins wait for a hardening stage.

- [x] **Step 6: Commit**

Message: `feat: add vendor-link build, verify and compare commands`.

---

### Task 13: V12 fixture chain

**Files:**
- Modify: `tests/vendor_link_fixtures.py`
- Test: `tests/test_vendor_link_v12.py`

**Interfaces:**
- Consumes: `seed_codes_bundle`, `seed_raw`, `subaward_record`, `extract_line`,
  `vendor_link_bundle`, `forbid_external_access`, and the production registries
  (`load_subaward_layouts`, `load_extract_layout`).
- Produces in `tests/vendor_link_fixtures.py`:
  - `V12_SNAPSHOT = date(2026, 11, 20)`, `V12_MONTH = '2026-11'`,
    `V12_RUNS = ('v12_first', 'v12_second')`
  - `v12_inputs() -> tuple[dict[int, dict[str, list[list[str]]]], list[str]]`: the
    subaward members by year in the production header layout, and the extract lines in the
    production extract layout. The extract file name is
    `SAM_PUBLIC_UTF-8_MONTHLY_V2_20261102.ZIP`.
  - `run_vendor_link_v12(tmp_path: Path, monkeypatch) -> dict` with keys `data_dir`,
    `first`, `second` (bundle directories), `first_pin`, `second_pin`,
    `first_verification`, `second_verification` and `comparison`. External access is
    blocked first, as in `ita_establishment_fixtures.run_establishment_v12`.

**Required cases (spec "V12 extension"):** a self-link; an intra-group pair by each of the
three conditions; a subcontractor not in SAM.gov; a record last updated before
2022-04-04, on a prime, so that `prime_ineligible` occurs; a missing code; a code conflict; a well-formed code outside NAICS 2022
(`517311`); a malformed code (`54151A`) on an extract row that no usable report reaches; a
blank UEI; a malformed UEI; a report outside the window; a duplicate row; a diagonal cell;
a firm in both roles; a prime with several subcontractors in one industry; a report in
each fiscal year. Use real 2022 codes such as `541511`, `541512`, `236220` and `336411`.
When the production registry maps no prime parent field, include only the first group
condition, and the test checks that the report lists the field as missing.

- [x] **Step 1: Write the failing tests**

```python
def test_v12_chain_is_offline_verified_and_replay_equal(tmp_path, monkeypatch):
    result = run_vendor_link_v12(tmp_path, monkeypatch)
    assert result['comparison']['equal'] is True
    assert result['first_verification']['outputs_sha256'] == result['first_pin']

def test_v12_fixture_holds_every_required_case(tmp_path, monkeypatch):
    pairs = pl.read_parquet(result['first'] / 'vendor_link_pairs.parquet')
    report = json.loads((result['first'] / 'report.json').read_text())
    assert set(pairs['pair_status']) == set(PAIR_STATUSES)
    assert report['reports']['total']['duplicate_rows'] == 1
    assert report['extract']['malformed_unread_rows'] == 1
    assert {'not_in_sam', 'dnb_era_record', 'naics_missing', 'naics_conflict',
            'naics_not_2022', 'eligible'} <= set(report['firms']['all'])
    # plus: every report status, a diagonal cell, a usable report in each fiscal year

def test_no_name_or_address_value_in_any_bundle_byte(tmp_path, monkeypatch):
    for file in result['first'].iterdir():
        assert DNB_SENTINEL.encode() not in file.read_bytes()
```

- [x] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_vendor_link_v12.py -q`
Expected: FAIL, `ImportError: cannot import name 'run_vendor_link_v12'`.

- [x] **Step 3: Implement `v12_inputs` and `run_vendor_link_v12`**

- [x] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_vendor_link_v12.py -q`
Expected: all pass. If one test takes 60 s or more, report it to the owner: marking it
`slow` means editing `tests/conftest.py`, which this plan does not do.

- [x] **Step 5: Commit**

Message: `test: add the vendor-link V12 raw-to-replay fixture chain`.

---

### Task 14: Independent reconciler

**Files:**
- Create: `scripts/reconcile_usaspending_vendor_links.py`
- Test: `tests/test_reconcile_usaspending_vendor_links.py`

**Interfaces:**
- Consumes: nothing from Stage 14 modules. It imports only the standard library and
  `polars`, to read Parquet. No `embedding_data` import.
- Produces:
  `python scripts/reconcile_usaspending_vendor_links.py --data-dir D --run ID --outputs-sha256 PIN`.
  It prints one sorted JSON line of counts and booleans, never a UEI. It exits 0 when
  everything is equal, 1 when something differs and 2 on a refusal. Module constants
  `SUBAWARD_HEADERS: dict` and `EXTRACT_LAYOUT: dict` hold its own literal registries, in
  the JSON forms of Task 5. Tests load the script with
  `importlib.util.spec_from_file_location`.

**Independence:** it checks the pin, reads `inputs.json` for the four raw paths and their
SHA-256, and checks each raw file's hash. It reads `derived/codes/<run>/outputs.json`,
checks it against the recorded codes pin and the `naics_nodes.parquet` record, and reads
the national-industry node IDs. It reads the ZIP members with `zipfile`, `csv.reader` and
`str.split`, applies the rules with `WHITESPACE`, `re` and `decimal.Decimal`, and with
plain Python sets and dicts recomputes:
- the report, firm and pair statuses
- `n_sup`, `n_buy`, `S`, `B`, `L` and the yearly `l` counts
- the intra-group sensitivity and the partial counts
- `amount_sum` and `n_reports`

It compares them exactly with the four tables (values within `1e-12`), and with
`report['reports'][*]['by_status']`, `report['firms']`, `report['pairs']` and the counts
in `report['join_coverage']`.

- [x] **Step 1: Write the failing tests**

```python
def test_reconciler_registries_equal_the_committed_json():
    assert reconcile.SUBAWARD_HEADERS == json.loads(vendor_link_layouts.SUBAWARD_FILE.read_text())
    assert reconcile.EXTRACT_LAYOUT == json.loads(vendor_link_layouts.EXTRACT_FILE.read_text())
def test_reconciler_imports_no_embedding_data_module():
    tree = ast.parse(SCRIPT.read_text())
    assert not [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                and 'embedding_data' in ast.unparse(n)]
def test_reconciler_reports_equal_on_the_v12_bundle(tmp_path, monkeypatch): ...  # exit 0
def test_reconciler_detects_a_changed_count(tmp_path, monkeypatch): ...
    # copy the bundle, add 1 to one s_suppliers, rewrite outputs.json; the new pin: exit 1
def test_reconciler_refuses_a_wrong_pin(tmp_path, monkeypatch): ...   # exit 2
```

- [x] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_reconcile_usaspending_vendor_links.py -q`
Expected: FAIL, the script does not exist.

- [x] **Step 3: Implement the script from the spec's text**

Write it from the spec's sections, not from the build modules.

> Deviation: the first real-data run of the reconciler (Task 15) refused, because it read the extract at CRLF only and the delivered extract has LF line ends. The owner approved a fix on 2026-11-22. The reconciler now ends a line at LF and drops one CR before it (commits `2fd4a1b`, `9fd0a5b`). That was the second fix round of Task 14. The first one followed its review (commit `620f836`).

- [x] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_reconcile_usaspending_vendor_links.py -q`
Expected: all pass.

- [x] **Step 5: Full suite**

Run the Stage 9 `pgrep` check, then `uv run --locked behave` and
`uv run --locked pre-commit run coverage-check-full --hook-stage pre-push --all-files`.
Expected: every scenario and test passes (the `network` canary is deselected).

- [x] **Step 6: Commit**

Message: `feat: add the independent vendor-link reconciler`.

---

### Task 15: First full-data build and acceptance (controller, owner-gated)

**Files:** none changed. Results go to the findings file in Task 16.

- [x] **Step 1: Clean execution state**

The worktree holds every task's commit and `git status --porcelain` prints nothing, so
`execution.dirty` is false. Use `uv run --locked` from this worktree's own `.venv` for
every command in this task, with no overlay, and change nothing in the venv between Steps 3
and 5.

- [x] **Step 2: Go-ahead (Owner Checkpoint 6, host rule)**

Choose a fresh run ID `stage14_vendor_links_<YYYYMMDD>_r1` and confirm that neither it nor
`<id>.part` exists under `data/derived/usaspending/vendor-links/`.

- [x] **Step 3: Build**

```bash
/usr/bin/time -l uv run --offline --locked python -m embedding_data.usaspending_vendor_links build RUN_ID --codes-run stage4_v11_20261013_r2 --codes-outputs-sha256 15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a --snapshot DATE --sam-month YYYY-MM --data-dir /Users/lowell/Projects/embedding-data/data
```

Run it in the background (Global Constraints, "Long-running commands"). Expected: one JSON
line with `outputs_sha256`. Record the wall time and the maximum resident set size. Record
the bundle size with `du -sk`.

> Deviation: Steps 3 to 6 ran twice. The first build, `stage14_vendor_links_20261121_r1` (pin `c9d71dd95b717048a54a4701bf88a7cb670d59b1342adac0ce4a207267fe1610`, commit `620f836`), passed all four steps. The final whole-branch review then found that `sam_raw` would record a wrapped extract ZIP and use up its month. The owner chose "Fix now, rebuild" (2026-11-22). The fix changes `sam_raw.py`, which `verify` hashes, so `verify` now refuses `r1`. The second build, `stage14_vendor_links_20261122_r2` (pin `248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be`, commit `1eddb3e`), passed all four steps again, and its `report.json` equals that of `r1`. `r1` stays on disk as superseded.

- [x] **Step 4: Verify**

```bash
uv run --offline --locked python -m embedding_data.usaspending_vendor_links verify RUN_ID --outputs-sha256 RUN_PIN --data-dir /Users/lowell/Projects/embedding-data/data
```

Run it in the background. Expected: exit 0 and one JSON line.

- [x] **Step 5: Reconcile**

```bash
uv run --offline --locked python scripts/reconcile_usaspending_vendor_links.py --data-dir /Users/lowell/Projects/embedding-data/data --run RUN_ID --outputs-sha256 RUN_PIN
```

Run it in the background. Expected: exit 0, with every comparison true.

- [x] **Step 6: Preservation**

1. The current `data/raw/manifest.jsonl` starts with the bytes of the Task 9 baseline
   copy, and the lines after them include the four Stage 14 entries. Other stages run in
   parallel, so show the owner any other appended line for the owner to account for.
2. `uv run --locked embedding-data audit --data-dir /Users/lowell/Projects/embedding-data/data`
   exits 0.
3. `derived/osha/ita_300a_summary.parquet` has SHA-256
   `6335cda7adb40a41c4a11d57d22048999449ac8d078a2ec0291f0198cd9136a8` and 139,930,636
   bytes.
4. Each bundle below passes `target_io.verify_inventory(directory, outputs, set(outputs))`
   against its own `outputs.json`, and that file's SHA-256 equals the pin. The Stage 6 pins
   are from `specs/findings/stage-6-ita-area-mix-build.md:26-33`. Add any Stage 5 TRI
   bundle that `specs/naics-evaluation-data-stage-5-findings.md` names by then, with its
   pin.

| Bundle | Detached pin |
| --- | --- |
| `derived/codes/stage4_v11_20261013_r2` | `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |
| `derived/osha/assignment-inputs/stage6_ita_assignment_20261014_1000_csv` | `84b29be17bae26e4cd7bb372108f95641936be4b73b794667957ed39de990d48` |
| `derived/targets/stage6_ita_area_mix_20261014_1000_csv` | `084292b6835eb09ce27ecc4a3aef03a6f43bfe7b39b815665c29190a431e2473` |
| `derived/targets/stage6_ita_area_mix_20261014_1000_csv_replay` | `78fd21e37ba0c5b1cd396ff0961b557650788fdccd3c84a911e8c6c3b7fabe71` |
| `derived/osha/establishment-targets/stage10_ita_establishment_20261116_r1` | `e19b0d58f61f106c3994aa6fe51f4fb71244188145dd90f8cccaa8dc8a8b09df` |
| `derived/osha/establishment-targets/stage10_ita_establishment_20261116_r1_replay` | `e38e820b6e999f751687918d8f578b0f9d69ce145bbcb672b966a19a78d536a4` |

- [x] **Step 7: On any failure**

Stop. Change no code. Report the failing step to the owner. Any cleanup of a failed run's
staging needs its own go-ahead.

---

### Task 16: Findings, amendments and completion (controller)

**Files:**
- Modify: `specs/naics-evaluation-data-stage-14-findings.md`
- Modify: `specs/embedding-evaluation-data-spec.md`, `CLAUDE.md`
- Modify: `specs/usaspending-vendor-links.md` (Rollout bullet)
- Modify at completion: `specs/naics-evaluation-data-roadmap.md`, `specs/deferred_items.md`,
  `specs/history.md`; move this plan and the spec to their `completed/` folders

Merge `main` into the branch before Step 2: plans 13 and 14 edit the same lines. Place
every edit by its quoted anchor text, not by line number. `<date>` is the execution date.

- [x] **Step 1: Finish the findings file (one screen)**

Add these sections:
1. The run ID, the detached pin, the snapshot label, the extract month, and the wall time,
   maximum RSS and bundle size of the real run.
2. The `verify` and reconciler outcomes and the preservation results.
3. The main counts: reports by status for each year, distinct UEIs by role and firm
   status, pairs by status, join coverage, target rows, the diagonal, cells only under
   the intra-group sensitivity, and partial counts.
4. "For the resume and O18", as the spec's Rollout lists them: the run ID, pin, snapshot
   label and extract month; the `n_unweighted` distributions and `size_gate_pending`; the
   firm counts, pair counts and marginals; the intra-group label; the universe statement;
   join coverage; the diagonal; the R8.4 exclusion.

Fixture results are not benchmarks.

> Deviation: the findings file is longer than one screen. It also records the measured cost of D2 (6,403 firms). A read-only, counts-only check that the owner approved on 2026-11-22 measured it, and the owner kept D2.

- [x] **Step 2: Check which shared amendment items are still open**

Run: `git fetch origin && git show origin/main:specs/embedding-evaluation-data-spec.md | grep -c "Evidence sources admitted by"`.
If the count is 0, apply the shared items of Step 3 and Step 4 in full. Otherwise another
stage applied them first: apply only Stage 14's own items.

- [x] **Step 3: Amend `specs/embedding-evaluation-data-spec.md`**

Shared item 1 (introduction; only when Step 2 counted 0). Replace:

```
code harmonization, geography hierarchy, and output tables they share. The
```

with:

```
code harmonization, geography hierarchy, and output tables they share. Evidence
sources admitted by [the evidence-sources spec](uncovered-uses-evidence-sources.md)
add further families, each adopted by its own roadmap stage. The
```

Shared item 2 (Core principle; only when Step 2 counted 0). Replace:

```
from records in the three sources. No target is derived from the NAICS, SOC, or
```

with:

```
from records in the admitted sources (R1.1), or taken as published from an admitted
published aggregate (R7.5). No target is derived from the NAICS, SOC, or
```

Shared item 3 wording (only when Step 2 counted 0). Replace
`**R1.1** The required path draws on exactly three sources:` with
`**R1.1** The required path draws on three core sources:`.

Stage 14 item 3 (always). After the last row of the R1.1 table, add:

```
| USAspending.gov contract subawards, joined by UEI to the SAM.gov public entity extract | Prime–subcontractor firm pair | Fiscal years 2024–2026, one SAM.gov monthly snapshot | Industries linked as supplier and buyer through federal subcontracts |
```

Stage 14 item 4 (always). Replace `**R1.2** All three sources are free. ITA files are U.S.
government works` with
`**R1.2** All sources are free. A free account or API key is allowed. Its key is handled
like `IPUMS_API_KEY`. ITA files are U.S. government works`, keeping the line breaks of the
paragraph. The rest of R1.2 stays.

Stage 14 item 6 (always). After the last row of the R7.2 family table, add:

```
| Vendor links | USAspending subcontracts; SAM.gov entity NAICS | supplier industry → buyer industry, as firm shares | NAICS |
```

In the sentence that starts `The co-ownership family is *(added at synthesis)*`, replace
`; the others are *(chosen; D)*.` with
`; the vendor links family is *(owner, Stage 14 design, 2026-11-18; [stage spec](completed/usaspending-vendor-links.md))*; the others are *(chosen; D)*.`
The link points to the spec's retired path (Step 7).

Stage 14 R8.3 sentence (only if E6 passed in Task 1). At the end of the R8.3 paragraph,
append:

```
USAspending subaward data and the SAM.gov public entity extract are public. Tables derived from them may contain UEI pairs. They read no Dun & Bradstreet Open Data field, use no SAM.gov record last updated before 2022-04-04, and publish no name or address.
```

- [x] **Step 4: Amend `CLAUDE.md` (item 7)**

When Step 2 counted 0, replace:

```
embeddings from three sources: OSHA ITA Form 300A summaries, ACS via IPUMS USA, and CPS via IPUMS CPS.
```

with:

```
embeddings from three core sources: OSHA ITA Form 300A summaries, ACS via IPUMS USA, and CPS via IPUMS CPS. Evidence sources admitted by `specs/uncovered-uses-evidence-sources.md` add further families, each adopted by its own roadmap stage, starting with USAspending vendor links (roadmap Stage 14, `python -m embedding_data.usaspending_vendor_links`).
```

Otherwise, in the sentence that starts `Evidence sources admitted by`, insert
`, and USAspending vendor links (roadmap Stage 14, `python -m embedding_data.usaspending_vendor_links`)`
before its final period (Settled Default 21).

- [x] **Step 5: Commit**

Message: `docs(specs): record the Stage 14 findings and source spec amendment`.

- [x] **Step 6: Amend the stage spec's Rollout (Settled Default 1)**

In `specs/usaspending-vendor-links.md`, replace:

```
- Software readiness (tests and the V12 fixture) comes before full-data
  acceptance. Do not tick Stage 14 on design or planning completion.
```

with:

```
- The document checks, acquisition and the preflight's data checks (full-data
  acceptance steps 1 to 3) come first, because the V12 fixture uses the header
  layout that E4 records. Software readiness (tests and the V12 fixture) then
  comes before the full-data build *(owner, plan 15, <date>)*. Do not tick
  Stage 14 on design or planning completion.
```

Leave the spec's Status line unchanged. Commit with
`docs(specs): record the preflight-first order in the vendor-links spec`.

- [x] **Step 7: Plan Completion Protocol**

Run the writing-plans Plan Completion Protocol, including step 3a. The
`## Handoff to later stages` section gives:
- The resume after Stage 14: the run ID, pin, snapshot label and extract month, so a
  replay could use the same raw files, and the `n_unweighted` distributions in
  `report.json` for a minimum count.
- O18: the firm counts, pair counts and marginals, the intra-group label, the universe
  statement, join coverage, the diagonal and the R8.4 exclusion.
- Roadmap re-validation: Stage 14 read only `naics_nodes.parquet` and not the Stage 4
  concordance that its `Consumes` line names. The O6 cost note in the roadmap and the
  USAspending row of `specs/deliverable-map.md` still say the account is missing. Record
  these differences. Do not edit those texts.

Retire the spec to `specs/completed/` and re-point its relative links.

> Deviation: the final whole-branch review (two seats) ran before this step. It found the wrapped-ZIP import (fixed, see Task 15), the preflight tallies (fixed: the registration status and the EVS source count as coded only inside a closed domain) and D2 (kept, cost recorded). The fix wave is commits `012b3a9`, `fc35ae1`, `de92a71` and `1eddb3e`. At the gate the owner kept three declined-to-judge lines as built (the `SAM_API_KEY` order, skip-and-count and the two code-string readings), and the untested live `acquire-sam-extract` request is deferred → item: 15-usaspending-vendor-links — 2026-11-22.

- [x] **Step 8: Integrate**

Run the Stage 9 `pgrep` check, then open the PR and follow the owner's PR-lifecycle rule.

---

## Handoff to later stages

Stage 14 feeds one Ranked-list item of Track C (O18) and the resume after Stage 14. The
roadmap's Stage 14 entry leaves the resume to the owner. None is a staged stage yet, so none
has a `Consumes` line. Three items were deferred (`specs/deferred_items.md`, section
`15-usaspending-vendor-links`) → item: 15-usaspending-vendor-links — 2026-11-22.

- **The resume after Stage 14 (replay check, acceptance finding, headline minimum count).**
  It consumes run `stage14_vendor_links_20261122_r2`, pin
  `248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be`, snapshot `2026-11-19`,
  extract month `2026-10`, built at commit `1eddb3e` with `dirty: false`. The build took
  29.6 s and 961 MB, so a replay costs little. Run `build` with a new run ID and the same
  arguments (codes run `stage4_v11_20261013_r2`, its Stage 4 pin, `--snapshot 2026-11-19`,
  `--sam-month 2026-10`), then `compare-runs`. The three subaward files and the extract in
  `data/raw/` are manifest-recorded, so a replay reads the same bytes. Trap:
  `vendor_link_bundle.SOFTWARE_FILES` lists 26 files, among them `sam_raw.py`,
  `pyproject.toml` and `uv.lock`. A change to any of them makes `verify` refuse the run.
  That is why the first run, `r1`, is superseded. Run the replay from a tree where those
  files are byte-identical. The independent reconciler ran on `r2` only, and `compare-runs`
  skips `inputs.json` (decision D3), so it does not compare the software record. For a
  minimum count, `report.json` holds `n_unweighted_distribution`: median 1 (buyer share) and
  2 (supplier share), 90th percentile 6 and 11, maximum 260 and 1,101. 4,810 of 8,307
  buyer-share cells and 4,025 supplier-share cells have `n_unweighted` 1. Every row has
  `size_gate_pending`, and no minimum is set. Deferred into the resume: the D2 rule and the
  live `acquire-sam-extract` request (the section above).
- **O18 (USAspending protocol section).** It reads `report.json`, the marginals and the
  findings file: 48,989 firms (32,578 eligible), 107,994 pairs (67,524 eligible), 689
  industries, 8,307 cells (16,614 rows), the intra-group label
  (`numerator:intra_group_sensitivity:true`, 71 rows), the `universe` string, join coverage
  (prime 0.810 and subcontractor 0.662, pooled), the diagonal (88 cells and 6,180 pairs,
  9.2%) and the R8.4 exclusion. Traps: D2 gives 6,403 active registrations with one valid
  NAICS 2022 code no industry (the findings file, "The cost of D2"). The extract is one month
  and the subaward files are one snapshot. 276 extract lines are skipped and counted, and
  they touch 16 firms, all `not_in_sam`. `vendor_link_pairs.parquet` holds UEI pairs and
  stays on this machine. The release of any table is the owner's decision (E6). The extract
  came by the browser path, so `acquire-sam-extract` and its key were never used against the
  real API.
- **Roadmap re-validation.** Stage 14 read only `naics_nodes.parquet` of the Stage 4 bundle.
  It did not read the Stage 4 concordance that its `Consumes` line names. The O6 row in the
  roadmap still says that the family needs an owner-created account and that its size is
  unknown. The family is now built, E6 is closed and the browser path needed no key. The O6
  row is not edited here. The USAspending row of `specs/deliverable-map.md` said "Not built"
  and "not ready". The owner asked for it to be updated, and it was, on 2026-11-22.
