# BEA Input–Output Tables Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one verified bundle of directed BEA commodity → industry shares (O9 input
shares, O10 customer shares) from the 2017 benchmark detail Use table, with a NAICS
candidate code table and the published totals, under a new published-aggregate contract.

**Architecture:** A standalone command group `python -m embedding_data.bea_io_tables`
(spec approach 1). New modules import reused ones unchanged. Acquisition and a preflight
(E1–E3) run on the recorded raw files and commit a layout registry before the contract,
the code table, the estimand, the bundle and V12 are written. One offline build reads the
two workbooks as strings, builds three tables, and publishes an exclusive `.part`
directory by rename.

**Tech Stack:** Python 3.14, Polars, fastexcel (already a dependency), Typer, httpx
(acquisition only), pytest, uv.

**Spec:** `specs/bea-input-output-tables.md` (owner-approved 2026-11-23; merged as
`623a294`, unchanged on `main` at `e49d4dc`).

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 15 — on plan completion, tick the stage and re-validate later stages against what shipped.

Scope: O9, O10 (first build). Leaves out the replay build, the full-data `compare-runs`, a
long-form finding, README and `CLAUDE.md` run pins, a headline minimum count, and O19
(protocol section). The spec's "Out of scope" governs.

Process: lighter (Stage 2 spec, "Rules for every new family"): one full-data build,
`verify`, the independent reconciler and a one-screen findings file. The controller runs
Task 1 Step 1, the two gated tasks (5 and 13) and Task 14 itself, because a dispatched
subagent cannot ask the owner for a go-ahead.

## Global Constraints

- **Stage numbers.** This plan is Stage 15 of `specs/naics-evaluation-data-roadmap.md`.
  Stage numbers in `CLAUDE.md` and in code are the old roadmap's: Stage 4 codes bundle,
  Stage 6 area mix, Stage 9 ACS, Stage 10 ITA establishment. Plan 15 in
  `specs/plans/completed/` is unrelated.
- **Branch.** Execute on a new branch cut from `main` at or after the merge that brings
  this plan, in a worktree under `.claude/worktrees/`.
- **Table identity.** BEA 2017 benchmark detail Use table, before redefinitions, at
  producer value, about 402 industries. Plus BEA's "BEA Industry and Commodity Codes and
  NAICS Concordance". No other table or benchmark.
- **Codes identity.** Codes run `stage4_v11_20261013_r2`, detached `outputs.json` SHA-256
  `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`. Stage 15 reads
  `naics_native_nodes.parquet`, `naics_concordance.parquet` and `naics_nodes.parquet`
  only. Stage 4 concordance codes are bare six-digit strings, and `link_type` is one of
  `1:1`, `1:m`, `m:1`, `m:m` (`src/embedding_data/naics_relationships.py:14-58`).
  Node IDs look like `naics:2017:national_industry:111110`.
- **Contract versions (verbatim).** `bea-io-codes-v1`, `bea-io-totals-v1`,
  `targets-published-v1`, and the layout version `bea-io-layout-v1`.
- **Target metadata (verbatim).** `source` `bea_io`, `family` `bea_io_use`,
  `unit_a_type` `bea_commodity_2017_detail`, `unit_a`
  `feature:bea_commodity_2017_detail:<c>`, `unit_b_type` `bea_industry_2017_detail`,
  `unit_b` `feature:bea_industry_2017_detail:<j>`, `measure` one of
  `use_value_usd_millions`, `input_share`, `customer_share`, `se` null, `se_method`
  `none`, `n_unweighted` and `n_weighted` null, `sample_set`
  `bea_io_2017_benchmark_detail_use_before_redefinitions_producer`, `vintage`
  `bea_io=2017_benchmark`.
- **Flags (verbatim).** Every row: `count_not_published`, `non_headline`,
  `published_aggregate`, `se_not_published`. Some rows: `diagonal`, `negative_value`,
  `share_outside_unit_interval`, `share_denominator_not_positive`,
  `unit_a_no_naics_member`, `unit_b_no_naics_member`. No `size_gate_pending`. Code-table
  flags: `not_in_concordance`, `no_naics_member`, `naics_partial_member`,
  `naics_shared`, `naics_expanded`, `crosswalk_one_to_many`, `crosswalk_many_to_one`,
  `crosswalk_many_to_many`, `naics_2022_unmapped`.
- **Universe (verbatim, `<snapshot>` is the ISO snapshot date).** "BEA benchmark
  input-output accounts, 2017 detail Use table before redefinitions at producer prices,
  retrieved <snapshot>. Values are BEA estimates for the whole U.S. economy in millions of
  dollars, as published, not counts of records. BEA codes follow NAICS 2017 and often
  stand for several NAICS industries. BEA publishes no standard errors or counts."
- **Estimand.** `input_share(c,j) = U(c,j) / T_j` and `customer_share(c,j) = U(c,j) /
  T_c`, with `T_c` the published intermediate-total column cell of row `c` and `T_j` the
  published intermediate-total row cell of column `j`. No total is recomputed.
- **Paths.** Raw files: `data/raw/bea/input-output/<snapshot ISO>/<BEA file name>`.
  Bundles: `data/derived/bea/input-output/<RUN_ID>/`. Findings:
  `specs/naics-evaluation-data-stage-15-findings.md`.
- **Runs.** Run IDs match `[A-Za-z0-9][A-Za-z0-9_-]*`. An existing final or
  `<RUN_ID>.part` fails. A later run never reuses, overwrites or deletes it.
- **Offline.** `import-file`, `build`, `verify` and `compare-runs` load no `.env`, read no
  credential, construct no HTTP client and run no upstream builder. Only `acquire` uses
  the network.
- **Diagnostics.** Success prints one sorted JSON line. Failure prints only
  `BEA input-output <command> failed: <reason>; run <run_id>; path <path>` to stderr and
  exits 2. `<reason>` is `validation`, `filesystem`, `network` or `unexpected`. It never
  prints exception text or row content. Unequal `compare-runs` exits 1.
- **Frozen code.** Edit no existing file under `src/` or `scripts/`, no existing test file,
  no `tests/conftest.py`, `pyproject.toml` or `uv.lock`. Stage 15 adds files only. Add no
  dependency. If a reused function cannot serve unchanged, stop and ask the owner.
- **Reused interfaces, imported unchanged.** `target_contract.TARGET_SCHEMA`,
  `TARGET_KEY_COLUMNS`, `valid_unit` (never `validate_targets` or `write_targets`);
  `target_io.stage`, `relative_file`, `file_record`, `inventory`, `verify_inventory`,
  `verify_raw`, `write_json`; `manifest.describe_file`, `append_entries`, `check_appendable`,
  `entry_for`, `read_manifest`, `sha256_file`; `paths`;
  `geography_references.safe_path`, `occupied`. Tests may also import, never edit,
  `tests/tri_fixtures.py` (`seed_codes_bundle`, `subprocess_modules`, `module_file`),
  `tests/target_fixtures.py` (`forbid_external_access`), `target_inputs`,
  `classification_tables`, `naics_relationships` and `code_build`. No module calls a TRI,
  Stage 10 or USAspending function.
- **Import closure.** `target_io` imports `geography_references`, which imports
  `osha_benchmark_download`, `ita_references` and `geography_parsers`. They load but are
  never called. `SOFTWARE_FILES` is the measured closure (Tasks 9 and 10), not a hand
  list. Importing the command module loads neither `dotenv` nor `ipumspy`.
- **Workbook reading.** `fastexcel.read_excel(bytes).load_sheet(sheet, header_row=None,
  dtypes='string').to_polars().rows()`, the pattern of
  `src/embedding_data/acs_code_references.py:600-601`. Planning probe, fastexcel 0.21.0:
  numeric cells come back as plain decimals with no exponent (`1234`, `-5.5`,
  `0.0000001`, `123456789012`). Empty cells come back as `None`. Codes stay strings.
- **Host rule (spec).** Run one acquisition at a time, because
  `manifest.append_entries` checks and then appends with no lock. Run one full-data
  build at a time. Before each acquisition, import and full-data build:
  1. Run `pgrep -fl 'embedding_data|embedding-data'` and show the owner its full,
     unfiltered output. It can match editors or agents whose command line holds the
     project path. The owner judges, and the run stops if it shows another acquisition
     or build.
  2. Run `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`.
     Stop if it prints anything. It can match another session's shell wrapper: read the
     hit and show it to the owner before deciding.
  3. The owner confirms that no other stage's acquisition or build is running and that
     no Stage 9 freeze window is open.
- **Commit protocol.** Before every commit and every full `pytest` run, run the Stage 9
  `pgrep` check above. If it prints anything, stop, leave the files uncommitted and tell
  the owner. Never skip a hook. `git add` only the task's files. The full suite hashes
  every `.py` file, so edit no `.py` file while it runs (about 20 minutes). Plans 9 and
  21 (Stage 9) also edit `CLAUDE.md` and `README.md`: rebase onto `main` before the
  Task 10 and Task 14 commits.
- **Production root.** Write to `/Users/lowell/Projects/embedding-data/data` only at the
  owner-gated steps of Tasks 5 and 13. Every production command passes
  `--data-dir /Users/lowell/Projects/embedding-data/data`. Tests use `tmp_path` roots
  and always pass the data root explicitly.
- **Acceptance values.** Real counts are measured, never gated. No test or gate contains
  a count from the real files.
- **Style.** Single quotes, `'''` docstrings, 4-space indents, 99 columns,
  `uv run --locked ruff check .` clean. Polars with method-style expressions. No pandas.
- **R8.4.** No table feeds embedder training, curriculum, hard-negative mining or model
  selection. The README section and the findings file say so.
- **Fixtures.** BEA workbooks in tests are synthetic, even if E2 allows redistribution.
  Fixture results show software readiness and are never benchmarks.

## Owner Checkpoints

1. **Frozen modules (any task).** If a reused function cannot serve unchanged, stop and
   ask the owner. Do not edit it.
2. **Page reads and probes (Task 1 Step 1).** Get the owner's go-ahead, with the URLs,
   before each page read and each `HEAD` request. No BEA data file body is fetched in
   Task 1.
3. **E3 (Task 1 Step 1, recorded in Task 5).** If BEA has released 2022 detail Use
   tables, stop before any fetch. The owner chooses between 2017 and 2022.
4. **Production writes (Task 5).** Get a go-ahead under the host rule before each file
   fetch or import. Get a go-ahead before reading any BEA PDF.
5. **Preflight stops and asks (Task 5).** Any E1 or E2 stop condition stops the stage.
   Report it and do nothing further. The owner records O9 and O10 as uncovered or
   promotes a named alternate. Ask the owner, and do not go on, when: more than 5% of Use
   table codes have no NAICS member; the value block uses more than one zero form; the
   concordance repeats a detail code; an aggregate concordance row carries NAICS codes;
   or the workbook has a structure that `bea_io_layout` cannot record. Never relax the
   reader to fit.
6. **Full-data run (Task 13).** Get a go-ahead under the host rule before the build and
   before any cleanup of a failed run's staging. If `verify`, the reconciler or a
   preservation check fails, stop, change no code and ask the owner.
7. **Plan review (planning session, before execution).** The plan is committed on its
   branch and the owner reviews it. The PR opens only after the owner approves, and a
   record of that approval is committed first.

## Review Focus

1. **Numeric cells stored at full precision.** BEA files store values as numeric `<v>`
   cells, which can carry 17 significant digits, a sign or an exponent. The person
   expects the build and the independent reconciler to read the same number, and no
   cell to be lost. Test: Task 3 `test_numeric_cells_read_as_their_stored_number`.
2. **Two snapshots on disk.** A later download lands beside the first. The person expects
   the build to read only the `--snapshot` files, and to fail on a missing or extra file
   under that date. Test: Task 1 `test_snapshot_selection_ignores_other_dates`.
3. **Concordance cells and rows.** One detail code can list several NAICS codes in one
   cell, or (if E1 records it) on continuation rows. The person expects every listed code
   in `naics_2017_published`, and a build failure, not a silent drop, for a row the
   registry does not explain. Test: Task 3
   `test_concordance_collects_every_listed_code_and_refuses_unexplained_rows`.
4. **A code in both roles.** Most BEA codes are both a commodity row and an industry
   column, often with different titles. The person expects one code-table row with both
   unit strings, and both titles kept in the totals table. Test: Task 8
   `test_code_in_both_roles_has_one_row_and_both_titles_survive`.
5. **Killed build.** A leftover `<RUN_ID>.part` makes a rerun with that ID fail and stay
   byte-identical. A fresh ID builds. Test: Task 9
   `test_leftover_staging_is_refused_and_untouched`.

## Decisions

- **D1** (owner, plan review, 2026-11-23): Approve plan 22 as committed at `c73f820`, with Settled Defaults 1–24 unchanged ("Approve plan 22"). Applied in: Settled Defaults.

## Settled Defaults (for owner review)

1. **Layout record.** The spec's "registry constant" is the committed JSON file
   `src/embedding_data/bea_io_layout.json`, loaded by `bea_io_layout`. It records what
   the spec names: the member, the sheet, the header rows, the code and title columns,
   the codes and roles of the total, final-demand and value-added lines, and the zero
   marker. It does not list the commodity and industry codes: every other code in the
   block is a commodity row or an industry column. So the synthetic V12 workbook uses the
   production layout unchanged, and a changed code list shows in the report, the gap
   check and the code table. `SOFTWARE_FILES` hashes the JSON.
2. **Header and footer rows.** Rows are compared exactly after trailing empty cells are
   dropped. A row with no cells left is dropped from the footer.
3. **Own download.** `bea_io_raw` streams with httpx itself, in the shape of
   `tri_raw._download` (`src/embedding_data/tri_raw.py:234-262`), and does not import
   `tri_raw`. Publication is an exclusive `.part`, then `os.link`.
4. **Missing `Content-Length`.** `acquire` refuses that file and records nothing for it.
   The owner then downloads it in a browser and uses `import-file`.
5. **Snapshot date.** `acquire --snapshot` must equal `date.today()` (local). `import-file`
   takes the owner's browser download date and refuses a future date.
6. **Existing raw files.** `acquire` keeps a file that is recorded and verifies, and does
   not download it again. It refuses an unrecorded file, a recorded file that is
   missing, and a `.part`. `import-file` refuses any existing destination.
7. **Import naming.** `import-file` publishes under the registered file name of `KIND`,
   not the local name. Its entry has `client` `manual-import`, `client_version` the
   `embedding-data` version, `source_url` null, `proxies` `('retrieved_at',)` and
   `through_date` null.
8. **Codes selector.** Own literals in `bea_io_selection`. Tests compare them with
   `target_inputs.CODE_SCHEMAS`, `classification_tables.NODE_SCHEMA`,
   `naics_relationships.RELATION_SCHEMA` and `code_build.SCHEMA_VERSION`.
9. **Reuse beyond the spec's list.** `target_contract.valid_unit`, `target_io.verify_raw`,
   `geography_references.safe_path` and `occupied`, and `manifest.check_appendable` and
   `read_manifest`, each imported unchanged. `target_io` already loads them. Test helpers
   are listed under Global Constraints.
10. **Rounding bound.** `k` in `0.5 × (k + 1)` is the number of nonzero published cells
    in the line. Zero cells carry no rounding. With all 400-odd cells, the bound would be
    about 200 million dollars and would miss a misread line.
11. **Zero cells.** E1 records one zero marker. A cell is zero when it equals the marker
    or parses to 0. A blank cell is valid only when the marker is the empty string. A
    second zero form is an owner ask (Owner Checkpoint 5).
12. **Totals table.** It keeps every non-commodity × industry cell of the block whose text
    is not empty. A zero-marker cell that is not empty is kept with value 0.0.
13. **Exact gap arithmetic.** Gaps are `decimal.Decimal(total) − Σ Decimal(cell)` from the
    cell strings, never Float64. The report records each gap as the fixed-point string
    `format(gap.normalize(), 'f')`, so cell texts `'1234'` and `'1234.0'` give one string.
    It counts lines by `ceil(|gap|)`.
14. **`naics_shared`.** Computed on the published codes with the partial marker removed,
    as the spec's "listed" says, not on the expanded candidates.
15. **Title of a dual-role code.** The commodity row's title. The report counts codes whose
    row and column titles differ. The totals table keeps both titles.
16. **Concordance parse.** A NAICS cell splits on the registered separators. Each token is
    stripped of surrounding whitespace, then must be 2–6 ASCII digits, with or without
    the registered partial marker at its end. A repeated detail code fails. A row with a
    blank detail code and a nonblank NAICS cell is a continuation row only when the
    registry says so. Otherwise it fails.
17. **5% trigger.** The denominator is the union of Use-table commodity and industry
    codes. Concordance detail codes that the Use table lacks are counted in the report
    (`concordance_only_codes`) and get no code-table row.
18. **Share distributions.** For each share measure: rows, null values, values below 0,
    values above 1, and nearest-rank quantiles `sorted[ceil(q × n) − 1]` (q = 0 uses
    index 0) at q in 0, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99 and 1, over the
    non-null values.
19. **`compare-runs`.** It compares the three Parquets in physical order, `report.json`
    exactly, and `inputs.json` without `run_id` and `execution`. A replay at a later
    commit with the same software is then equal.
20. **Published-aggregate writer.** `write_published_targets` returns the file record of
    `target_io.file_record` plus `schema_version`. The bundle stores it in
    `report['tables']`.
21. **Failure path.** The data-relative path (`raw/bea/input-output`,
    `derived/bea/input-output/<run_id>`), as TRI does.
22. **Preservation baseline.** Task 5 records the manifest's byte length and SHA-256 in
    the findings file. `/private/tmp` is not durable, so no copy is kept there.
23. **Reconciler reader.** It reads XLSX with `zipfile` and `xml.etree`, not fastexcel,
    so that it is independent of the build's reader. It reads code, title and NAICS cells
    by their raw text, and applies `repr(float(v))` only to value cells.
24. **E3 read first.** The E3 page read runs in Task 1 Step 1, before any data file is
    fetched, so a released 2022 benchmark stops the stage before any 2017 file lands.
    Task 5 records it in the findings file.

---

## File Map

| Path | Task | Responsibility |
| --- | --- | --- |
| `src/embedding_data/bea_io_raw.py` | 1 | Raw registry, layout, `acquire`, `import_file`, snapshot selection |
| `src/embedding_data/bea_io_tables.py` | 1, 10 | Typer command group |
| `src/embedding_data/bea_io_selection.py` | 2 | Stage 4 codes selector |
| `src/embedding_data/bea_io_layout.py` | 3 | Layout model, loader, workbook rows |
| `src/embedding_data/bea_io_reader.py` | 3 | Use and concordance scans, strict readers, line gaps |
| `scripts/preflight_bea.py` | 4 | E1 data checks |
| `src/embedding_data/bea_io_layout.json` | 5 | Production layout |
| `src/embedding_data/published_target_contract.py` | 6 | `targets-published-v1` |
| `src/embedding_data/bea_io_code_table.py` | 7 | Code table |
| `src/embedding_data/bea_io_targets.py` | 8 | Targets, totals, validation, report |
| `src/embedding_data/bea_io_bundle.py` | 9 | Build, verify, compare, software identity |
| `scripts/reconcile_bea_io_tables.py` | 12 | Independent recount |
| `tests/bea_fixtures.py` | 1–3, 11 | XLSX and ZIP writers, synthetic tables, V12 chain |
| `tests/test_bea_io_*.py`, `tests/test_published_target_contract.py`, `tests/test_preflight_bea.py`, `tests/test_reconcile_bea_io_tables.py` | 1–12 | Tests |
| `README.md` | 10 | Command contract section |
| `specs/naics-evaluation-data-stage-15-findings.md` | 5, 13, 14 | Preflight, run and handoff |
| `specs/embedding-evaluation-data-spec.md`, `CLAUDE.md` | 14 | Source spec amendment |
| `specs/naics-evaluation-data-roadmap.md`, `specs/deferred_items.md`, `specs/history.md`, `specs/bea-input-output-tables.md` | 14 | Completion records, spec retirement |

---

### Task 1: Raw BEA files and acquisition commands

**Files:**
- Create: `src/embedding_data/bea_io_raw.py`
- Create: `src/embedding_data/bea_io_tables.py`
- Create: `tests/bea_fixtures.py`
- Test: `tests/test_bea_io_raw.py`, `tests/test_bea_io_cli.py`

**Interfaces:**
- Consumes: `manifest`, `paths`, `geography_references.safe_path`, `occupied`.
- Produces in `bea_io_raw`:
  - `SOURCE = 'bea'`, `SUBDIR = 'input-output'`, `KINDS = ('use-detail', 'concordance')`,
    `USER_AGENT: str` (Step 1), `TIMEOUT = httpx.Timeout(600.0, connect=15.0)`,
    `CHUNK_SIZE = 1024 * 1024`
  - `@dataclass(frozen=True) class RawFile: url: str | None; file_name: str`
  - `REGISTRY: dict[str, RawFile]`, one per kind, from Step 1. `url` is None when no URL
    serves the file with a `Content-Length`.
  - `today = date.today`, a module global looked up at call time (test seam)
  - `snapshot_dir(data_dir: Path, snapshot: date) -> Path`:
    `paths.raw_dir(data_dir, SOURCE) / SUBDIR / snapshot.isoformat()`
  - `raw_path(data_dir: Path, kind: str, snapshot: date) -> Path`
  - `make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client`, a module
    global (test seam): `follow_redirects=True`, headers `User-Agent: USER_AGENT` and
    `Accept-Encoding: identity`, `TIMEOUT`
  - `acquire(data_dir: Path, *, snapshot: date) -> dict` returning
    `{'downloaded': [paths], 'kept': [paths], 'import_required': [kinds]}`
  - `import_file(data_dir: Path, kind: str, original: Path, *, snapshot: date) -> Path`
  - `select_files(data_dir: Path, snapshot: date) -> dict[str, Path]`
  - `citations(data_dir: Path, files: dict[str, Path]) -> list[dict]`: each
    `asdict(manifest.entry_for(...))` read back through JSON, sorted by `path`
- Produces in `bea_io_tables`: `app` (Typer, `pretty_exceptions_enable=False`,
  `pretty_exceptions_show_locals=False`), `DataRoot`, `NO_RUN = '-'`,
  `RAW = 'raw/bea/input-output'`, `BUNDLES = 'derived/bea/input-output'`,
  `_reason(error) -> str`, `_invoke(command, run_id, path, operation)`, and the commands
  `acquire --snapshot DATE` and `import-file KIND FILE --snapshot DATE`. Copy the shape of
  `src/embedding_data/tri_parent_links.py:24-80` with the Stage 15 failure line.
- Produces in `tests/bea_fixtures.py`:
  `@dataclass(frozen=True) class Stored: text: str` (a numeric cell whose `<v>` text is
  written verbatim),
  `write_workbook(file: Path, sheets: dict[str, list[list[str | int | float | Stored | None]]]) -> None`
  (inline strings for `str`, numeric `<v>` cells for `int`, `float` (`repr`) and
  `Stored`, empty for None, any number of sheets, column letters past `Z`), and
  `write_zip(file: Path, members: dict[str, bytes]) -> None`. Do not edit or import
  `tests/code_fixtures.py`, whose writer has only one sheet, inline strings and 26
  columns.

**Rules:**
- `acquire` refuses `snapshot != today()`. It checks every destination before any
  download (Settled Default 6). A symlink anywhere in a destination path fails. A kind
  whose `url` is None goes to `import_required`. For each other missing kind it streams
  the body into `<destination>.part`, opened `'xb'`. No `Content-Length` raises
  `ValueError('download has no Content-Length')`. A `Content-Encoding` other than
  `identity` raises `ValueError('encoded download')`. A
  `response.num_bytes_downloaded` that differs from `Content-Length` raises
  `httpx.RemoteProtocolError`. It then describes the `.part` bytes, calls
  `manifest.check_appendable`, links, and appends. `finally` unlinks the `.part`.
  Entries: `client='httpx'`, `client_version=version('httpx')`, `source_url=<url>`,
  `through_date=None`. Nothing goes to stdout.
- `import_file` refuses an unknown kind, an original that is a symlink, not a regular
  file or empty, a snapshot after `today()`, and an existing destination or `.part`. It
  copies through an exclusive `.part`, compares SHA-256 with the original, links and
  records as in Settled Default 7.
- `select_files` requires `snapshot_dir` to be a real directory holding exactly the two
  registered file names, each a regular file that `manifest.entry_for` verifies. Any
  other state raises `ValueError` (`'raw file is not recorded'`,
  `'missing or extra raw file'`, `'raw file changed'`).

- [ ] **Step 1: Find the URLs and read E3 (controller, Owner Checkpoints 2 and 3)**

Make a new empty scratch directory with `mktemp -d /private/tmp/stage15-bea-pages.XXXXXX`.
Ask the owner's go-ahead, with the URL, before each request below. Save nothing under the
data root.
1. E3 (read): read BEA's Input-Output Accounts page
   (`https://www.bea.gov/data/industries/input-output-accounts-data`) and its release
   schedule. Record whether any 2022 benchmark detail table has been released, and any
   scheduled date. If one has been released, stop (Owner Checkpoint 3).
2. Send one `curl -sSI -H 'Accept-Encoding: identity' -A 'embedding-data BEA acquisition'`
   (`HEAD`) to the concordance URL
   `https://www.bea.gov/sites/default/files/2023-10/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx`.
   On 403, retry once with the browser string in `osha_benchmark_download.USER_AGENT`.
   The string that BEA served becomes `USER_AGENT`, as a literal.
3. Send one `HEAD` to `https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesIO.zip`
   the same way.

For each, record the final URL after redirects, the status, `Content-Length`,
`Content-Encoding`, `Content-Disposition` and `Content-Type`. The registered file name is
the `Content-Disposition` file name, or else the final URL's last path segment, decoded.
A URL that does not resolve, or sends no `Content-Length`, gets `url=None`. Then ask the
owner where the browser download of that kind will come from, and register the file name
that the owner's browser saves. Fetch no body. Read no ZIP listing: E1 names the member in
Task 5. Record all facts in the Task 1 commit message body. Task 5 copies them to the
findings file. Delete the scratch directory.

- [ ] **Step 2: Write the failing tests**

```python
SNAPSHOT = date(2026, 11, 24)

def test_acquire_downloads_and_records_each_registered_file(data_directory, monkeypatch):
    # REGISTRY patched to two test URLs; today patched to SNAPSHOT; make_client patched to
    # an httpx.MockTransport sending stream=httpx.ByteStream(...) with Content-Length
    result = bea_io_raw.acquire(data_directory, snapshot=SNAPSHOT)
    assert [p.relative_to(data_directory).as_posix() for p in result['downloaded']] == [
        f'raw/bea/input-output/2026-11-24/{bea_io_raw.REGISTRY[k].file_name}'
        for k in bea_io_raw.KINDS]
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [(e.client, e.source_url, e.through_date, e.proxies) for e in entries] == [
        ('httpx', URLS[k], None, ()) for k in bea_io_raw.KINDS]

def test_acquire_refuses_another_date(data_directory, monkeypatch): ...   # ValueError

@pytest.mark.parametrize('body', ['short', 'absent_length', 'gzip_encoded'])
def test_acquire_refuses_a_short_unsized_or_encoded_body(body, data_directory, monkeypatch):
    ...   # raises; no final file, no .part, no manifest line

def test_acquire_lists_a_kind_without_url_as_import_required(data_directory, monkeypatch):
    ...   # REGISTRY['concordance'].url None: result['import_required'] == ['concordance']

def test_acquire_keeps_a_recorded_file_and_refuses_unrecorded_or_missing(...): ...
    # recorded and intact: kept, not requested; unrecorded file, recorded and absent, or a
    # .part sibling: raises before any body request, bytes unchanged

def test_import_file_records_a_proxy_retrieval_time(data_directory, tmp_path):
    original = tmp_path / 'download (1).xlsx'
    ...
    path = bea_io_raw.import_file(data_directory, 'concordance', original, snapshot=SNAPSHOT)
    assert path.name == bea_io_raw.REGISTRY['concordance'].file_name
    entry = manifest.entry_for(paths.manifest_path(data_directory), path)
    assert (entry.client, entry.source_url, entry.proxies, entry.through_date) == (
        'manual-import', None, ('retrieved_at',), None)

@pytest.mark.parametrize('case', ['unknown_kind', 'future_date', 'existing', 'symlink', 'empty'])
def test_import_file_refuses(case, data_directory, tmp_path): ...

def test_snapshot_selection_ignores_other_dates(data_directory, tmp_path):
    # import both kinds under 2026-11-24 and again under 2027-01-05 (today patched)
    assert bea_io_raw.select_files(data_directory, SNAPSHOT) == {
        k: bea_io_raw.raw_path(data_directory, k, SNAPSHOT) for k in bea_io_raw.KINDS}
    # an extra file under 2026-11-24, a kind missing under it, or changed bytes each raise
```

In `tests/test_bea_io_cli.py`:

```python
def test_acquire_and_import_print_one_json_line(cli_runner, data_directory, ...): ...
def test_import_failure_prints_only_the_fixed_line(cli_runner, data_directory, tmp_path):
    result = cli_runner.invoke(bea_io_tables.app, [
        'import-file', 'make-table', str(file), '--snapshot', '2026-11-24',
        '--data-dir', str(data_directory)])
    assert result.exit_code == 2
    assert result.output.strip() == (
        'BEA input-output import-file failed: validation; run -; path raw/bea/input-output')
```

Add one test for the fixture writer: `test_write_workbook_round_trips_through_fastexcel`.
A two-sheet workbook with a string, an int, a negative float and a cell in column `AB`
reads back through the Global Constraints pattern as `('x', '12', '-0.5', ...)`.

- [ ] **Step 3: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_bea_io_raw.py tests/test_bea_io_cli.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'embedding_data.bea_io_raw'`.

- [ ] **Step 4: Implement `bea_io_raw`, the two commands and the fixture writers**

- [ ] **Step 5: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_bea_io_raw.py tests/test_bea_io_cli.py -q`
Expected: all pass.

- [ ] **Step 6: Commit**

Files: the two modules, `tests/bea_fixtures.py` and both tests. Message:
`feat: acquire and import BEA input-output files`, with the Step 1 facts in the body.

---

### Task 2: Codes selector

**Files:**
- Create: `src/embedding_data/bea_io_selection.py`
- Test: `tests/test_bea_io_selection.py`

**Interfaces:**
- Consumes: `target_io.relative_file`, `verify_inventory`; `manifest.sha256_file`; in tests,
  `tri_fixtures.seed_codes_bundle(data_dir, directory) -> (run, pin)`.
- Produces in `bea_io_selection`:
  - `RUN_ID`, `PIN` (the regexes of `tri_codes.py:22-23`), `CODES_SCHEMA_VERSION = 'codes-ita-v1'`
  - `CODE_TABLES` (the twelve Stage 4 names), `INVENTORY_NAMES` (their Parquets plus
    `inputs.json` and `report.json`)
  - `NODE_SCHEMA` and `RELATION_SCHEMA`, literal copies of the Stage 4 schemas
  - `TABLE_FILES = ('naics_native_nodes.parquet', 'naics_concordance.parquet', 'naics_nodes.parquet')`
  - `@dataclass(frozen=True) class SelectedCodes: data_dir: Path; codes_run: str;
    codes_outputs_sha256: str; outputs: dict; nodes_2017: pl.DataFrame;
    crosswalk: pl.DataFrame; nodes_2022: frozenset[str]`, with `verify(self) -> None`
    (reselect and refuse any difference) and `provenance(self) -> dict` returning
    `{'run_id', 'outputs_sha256', 'outputs'}`
  - `nodes_2017`: columns `node_id`, `level`, `code`, the rows with `system == 'naics'`
    and `vintage == 2017`, sorted by `code`, `level`
  - `crosswalk`: columns `source_code`, `target_code`, `link_type`, the rows with
    `source_vintage == 2017` and `target_vintage == 2022`, sorted
  - `nodes_2022`: `node_id` of `naics_nodes.parquet` rows with `system == 'naics'`,
    `vintage == 2022`, `level == 'national_industry'`
  - `select_codes(data_dir: Path, codes_run: str, *, codes_outputs_sha256: str) -> SelectedCodes`

**Selector checks, in order:** run ID and pin syntax; the SHA-256 of
`derived/codes/<run>/outputs.json` equals the pin; `target_io.verify_inventory` with
`INVENTORY_NAMES`; `inputs.json` and `report.json` have `schema_version ==
CODES_SCHEMA_VERSION`, and `inputs.json` has `run_id == codes_run`; each of the three
`TABLE_FILES` has exactly its schema, and its rows and schema equal
`report['tables'][name]`; every 2017→2022 `link_type` is one of the four strings; every
`target_code` of the crosswalk is the code of a `nodes_2022` ID. No other file is read.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.fixture(scope='module')
def codes(tmp_path_factory):
    root = tmp_path_factory.mktemp('codes')
    run, pin = tri_fixtures.seed_codes_bundle(root / 'data', root / 'originals')
    return root / 'data', run, pin

def test_constants_match_stage4():
    assert set(bea_io_selection.CODE_TABLES) == set(target_inputs.CODE_SCHEMAS)
    assert bea_io_selection.NODE_SCHEMA == classification_tables.NODE_SCHEMA
    assert bea_io_selection.RELATION_SCHEMA == naics_relationships.RELATION_SCHEMA
    assert bea_io_selection.CODES_SCHEMA_VERSION == code_build.SCHEMA_VERSION

def test_select_codes_reads_2017_nodes_the_crosswalk_and_2022_leaves(codes):
    selected = bea_io_selection.select_codes(data_dir, run, codes_outputs_sha256=pin)
    assert 'naics:2022:national_industry:111110' in selected.nodes_2022
    assert set(selected.crosswalk['link_type']) <= {'1:1', '1:m', 'm:1', 'm:m'}
    assert selected.nodes_2017.filter(pl.col('level') == 'national_industry').height > 0

def test_select_codes_reads_no_ita_data(codes, tmp_path): ...
    # on a copy without derived/osha/ita_300a_summary.parquet and raw/osha: same result

@pytest.mark.parametrize('mutation', ['run_id', 'pin_syntax', 'wrong_pin', 'extra_file',
                                      'changed_byte', 'schema_version', 'recorded_run_id'])
def test_select_codes_refuses(codes, tmp_path, mutation): ...   # ValueError, on a copy

def test_verify_detects_a_later_change(codes, tmp_path): ...
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_bea_io_selection.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement `bea_io_selection`**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_bea_io_selection.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: select the pinned Stage 4 NAICS tables for BEA`.

---

### Task 3: Layout model, workbook rows and readers

**Files:**
- Create: `src/embedding_data/bea_io_layout.py`
- Create: `src/embedding_data/bea_io_reader.py`
- Modify: `tests/bea_fixtures.py`
- Test: `tests/test_bea_io_layout.py`, `tests/test_bea_io_reader.py`

**Layout JSON.** One object, `version`, `use` and `concordance`. Row and column indexes are
0-based positions in the sheet as fastexcel reads it with `header_row=None`.

```json
{"version": "bea-io-layout-v1",
 "use": {"member": null, "sheet": "...",
         "header_rows": [["..."]], "code_row": 5, "title_row": 6,
         "code_column": 0, "title_column": 1, "first_row": 7, "first_column": 2,
         "row_roles": {"T005": "total", "V00100": "value_added"},
         "column_roles": {"T001": "total", "F01000": "final_demand"},
         "intermediate_total_row": "T005", "intermediate_total_column": "T001",
         "footer": [["..."]], "zero_marker": ""},
 "concordance": {"member": null, "sheet": "...", "header_rows": [["..."]],
                 "code_column": 3, "naics_column": 6, "first_row": 5,
                 "separators": [", "], "partial_marker": null, "no_member": ["n.a."],
                 "continuation": false}}
```

`header_rows` holds every row before `first_row` other than `code_row` and `title_row`,
trimmed (Settled Default 2). The values above are placeholders; Task 5 records the real
ones.

**Interfaces:**
- Consumes: `bea_io_raw.select_files`.
- Produces in `bea_io_layout`:
  - `LAYOUT_VERSION = 'bea-io-layout-v1'`,
    `PRODUCTION_FILE = Path(__file__).with_name('bea_io_layout.json')`
  - `ROW_ROLES = ('value_added', 'total')`, `COLUMN_ROLES = ('final_demand', 'total')`
  - frozen dataclasses `UseLayout`, `ConcordanceLayout` (fields as the JSON, tuples for
    lists) and `Layout(use: UseLayout, concordance: ConcordanceLayout)`
  - `parse_layout(value: dict) -> Layout`, `layout_json(layout: Layout) -> dict`, with
    `parse_layout(layout_json(x)) == x`
  - `load_layout(file: Path = PRODUCTION_FILE) -> Layout`. A missing file raises
    `ValueError('production BEA layout is not recorded')`.
  - `trim(row: tuple[str | None, ...]) -> tuple[str | None, ...]`: trailing None and `''`
    dropped
  - `workbook_bytes(file: Path, member: str | None) -> bytes`: the file, or the one ZIP
    member of that exact name. A missing member raises `ValueError`.
  - `workbook_rows(file: Path, member: str | None, sheet: str) -> list[tuple[str | None, ...]]`
- Produces in `bea_io_reader`:
  - `NUMBER = re.compile(r'-?[0-9]+(\.[0-9]+)?')`
  - `@dataclass(frozen=True) class UseScan: rows: pl.DataFrame; columns: pl.DataFrame;
    cells: pl.DataFrame; problems: dict[str, int]; unknown_texts: dict[str, int]`.
    `rows` and `columns` have `code`, `title`, `role` (`commodity` or `industry` for the
    interior lines, else the registered role) and `position`. `cells` has `row_code`,
    `column_code`, `text` (`''` for an empty cell) and `value` (Float64: the number, 0.0
    for a zero cell, null for unknown text), one row per block cell.
  - `scan_use(rows: list[tuple], layout: UseLayout) -> UseScan`: never raises on data.
    Problem keys: `header_rows_differ`, `footer_differs`, `cells_right_of_block`,
    `duplicate_codes`, `missing_registered_codes`, `blank_code_inside_block`.
  - `read_use(file: Path, layout: UseLayout) -> UseScan`: scans and raises `ValueError`
    when any problem count or `unknown_texts` is nonzero.
  - `@dataclass(frozen=True) class ConcordanceScan: codes: pl.DataFrame; problems:
    dict[str, int]; unknown_tokens: dict[str, int]`. `codes` has `bea_code` and
    `naics_published` (List(String), sorted, unique, as published).
  - `scan_concordance(rows, layout: ConcordanceLayout) -> ConcordanceScan`, and
    `read_concordance(file: Path, layout: ConcordanceLayout) -> ConcordanceScan`, strict
    like `read_use`. Problem keys: `header_rows_differ`, `repeated_codes`,
    `unexplained_rows`, `blank_naics_cells`.
  - `line_gaps(scan: UseScan, layout: UseLayout) -> pl.DataFrame` with `line`
    (`commodity` or `industry`), `code`, `cells` (Int64: nonzero cells summed), `total`
    (String, the published total text), `gap` (String, Settled Default 13) and
    `within_bound` (Boolean), sorted by `line`, `code` (Settled Defaults 10 and 13)
- Produces in `tests/bea_fixtures.py`: `TEST_LAYOUT: bea_io_layout.Layout`, a small
  synthetic layout with codes like `T005`, `T001`, `V00100`, `F01000`, and
  `use_sheet(commodities: dict[str, str], industries: dict[str, str], cells: dict[tuple[str, str], int | float | str], extra: dict[tuple[str, str], int | float | str], layout: UseLayout) -> list[list]`
  that lays the synthetic table out in `layout`, with every registered line, totals
  computed from the cells unless `extra` sets them, header rows and footer.

**`parse_layout` checks:** version; every role in its tuple; both intermediate totals are
registered with role `total`; `code_row`, `title_row`, `first_row` distinct, with the
first two below `first_row`; `code_column` and `title_column` distinct and below
`first_column`; `zero_marker` a string with no digit; concordance columns distinct;
separators nonempty and distinct; `partial_marker` null or a nonempty string with no digit
and no separator; `no_member` entries equal their own strip; `continuation` a Boolean.
Each failure raises `ValueError`.

**Scan rules (spec "Reading"):**
- The trimmed rows before `first_row`, other than the code and title rows, must equal
  `header_rows`.
- Column codes are the `code_row` cells from `first_column` to the first empty cell.
  Row codes are the `code_column` cells from `first_row` to the first empty cell. Every
  later row is footer, compared with `footer` after trimming and dropping empty rows.
  Any nonempty cell right of the last column is a problem.
- A code that is registered takes its registered role. Every other row code is a
  commodity, every other column code an industry. A registered code that is absent, or
  a code that appears twice in its axis, is a problem.
- A cell text is a number when it matches `NUMBER` fully, or zero when it equals
  `zero_marker`. An empty cell is zero only when `zero_marker` is `''`. Every other text
  goes to `unknown_texts`.
- Concordance: rows from `first_row` on. A row with a nonblank `code_column` cell is a
  detail row. A row with a blank code cell and a blank NAICS cell is skipped. A row with
  a blank code cell and a nonblank NAICS cell continues the previous detail row when
  `continuation` is true, and is `unexplained_rows` otherwise. A NAICS cell in
  `no_member` gives no code. A blank NAICS cell on a detail row is `blank_naics_cells`
  unless `''` is in `no_member`. Each other cell splits by Settled Default 16. A token
  that is not a valid form goes to `unknown_tokens`.

- [ ] **Step 1: Write the failing tests**

`tests/test_bea_io_layout.py`: `test_layout_json_round_trip`,
`test_parse_layout_refuses` (parametrized over every check above),
`test_load_layout_refuses_a_missing_file`, and
`test_workbook_rows_reads_a_zip_member_and_refuses_a_missing_one`.

`tests/test_bea_io_reader.py`:

```python
def test_numeric_cells_read_as_their_stored_number(tmp_path):
    stored = ['0.10000000000000001', '1234.5678901234567', '-0.5', '1E-3',
              '12345678901234567890', '-0']
    # write each as bea_fixtures.Stored(text) in a TEST_LAYOUT block; read_use returns
    # each cell's text and value
    for text, cell in zip(stored, cells):
        assert Decimal(cell['text']) == Decimal(repr(float(text)))
        assert cell['value'] == float(text)

def test_scan_use_assigns_roles_and_reads_every_block_cell(tmp_path): ...
    # cells.height == len(rows) * len(columns); roles of T005, V00100, T001, F01000

@pytest.mark.parametrize('defect', ['header_row', 'footer', 'cell_right_of_block',
    'duplicate_code', 'missing_total', 'unknown_text', 'blank_with_marker'])
def test_read_use_refuses(defect, tmp_path): ...

def test_blank_cell_is_zero_only_with_an_empty_marker(tmp_path): ...

def test_concordance_collects_every_listed_code_and_refuses_unexplained_rows(tmp_path):
    # '1111A0': '111110, 111120*' ; continuation row '111191' under continuation=True
    scan = bea_io_reader.read_concordance(file, layout)
    assert scan.codes.row(by_predicate=pl.col('bea_code') == '1111A0',
                          named=True)['naics_published'] == ['111110', '111120*', '111191']
    # the same continuation row under continuation=False raises ValueError

@pytest.mark.parametrize('token', ['3361-3363', '31-33', '33611x', 'all', '1111**'])
def test_concordance_refuses_unregistered_token_forms(token, tmp_path): ...

def test_line_gaps_use_exact_decimals_and_nonzero_cell_counts(tmp_path):
    # a row of 0.4 + 0.4 + 0 with total 1: cells == 2, gap == '0.2', within bound 1.5
    # a row of 1 + 1 with total 4: gap == '2', bound 1.5, within_bound False
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_bea_io_layout.py tests/test_bea_io_reader.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement `bea_io_layout`, `bea_io_reader` and the fixture helpers**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_bea_io_layout.py tests/test_bea_io_reader.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: add the BEA layout model and workbook readers`.

---

### Task 4: Preflight script

**Files:**
- Create: `scripts/preflight_bea.py`
- Test: `tests/test_preflight_bea.py`

**Interfaces:**
- Consumes: `bea_io_raw.select_files`, `bea_io_selection.select_codes`,
  `bea_io_layout.parse_layout`, `workbook_rows`, `trim`, `bea_io_reader.scan_use`,
  `scan_concordance`, `line_gaps`.
- Produces `scripts/preflight_bea.py` with four subcommands. Each takes `--data-dir` and
  `--snapshot`, reads only manifested files (and, for `measure`, the pinned Stage 4
  Parquets), and prints one JSON object. Exit 0 when no stop condition holds, 1 when one
  does, 2 on a refusal (unrecorded file, unreadable layout).
  - `inspect`: for each kind, the path, size and SHA-256; for a ZIP, every member with
    its size; for each workbook (the file, or each `.xlsx` member), its sheet names and
    dimensions.
  - `rows --kind KIND [--member M] --sheet S --start A --stop B`: rows `A` to `B − 1` as
    JSON arrays of strings and nulls.
  - `draft --kind use-detail ...` with `--member`, `--sheet`, `--code-row`,
    `--title-row`, `--code-column`, `--title-column`, `--first-row`, `--first-column`,
    or `--kind concordance ...` with `--member`, `--sheet`, `--code-column`,
    `--naics-column`, `--first-row`: prints the `use` or `concordance` object with the
    header rows and footer copied from the sheet, every row and column code with its
    title, and `row_roles`, `column_roles`, the totals, `zero_marker`, `separators`,
    `partial_marker`, `no_member` and `continuation` left for the controller to fill.
  - `measure --layout FILE --codes-run ID --codes-outputs-sha256 PIN`: the E1 measures
    below, then `stops`, `asks` and `ok`.

**`measure` output (spec E1):** concordance: header rows, the NAICS column header text
(edition), detail codes, NAICS codes by digit count, rows with a partial marker, detail
codes with no member and their titles, NAICS codes listed under more than one BEA code,
unknown token forms with counts, NAICS 2017 codes not in `nodes_2017`, problems. Use
table: sheet, header rows, commodity, industry, final-demand, value-added and total code
lists, cell text forms (number, zero marker, empty, unknown with counts), negative cells,
the largest gap and the count of lines by `ceil(|gap|)` for each axis, Use-table codes
absent from the concordance, and concordance codes absent from the Use table.
`no_member_share` is the Settled Default 17 rate.

**Stops:** any unknown token form; a NAICS code not in `nodes_2017`; any line with
`within_bound` false; any unknown cell text; any scan problem. **Asks:**
`no_member_share` above 0.05; more than one text form among cells that are zero. The
NAICS edition and the table's existence are document checks the controller reads from
the output.

- [ ] **Step 1: Write the failing tests**

`tests/test_preflight_bea.py` imports synthetic workbooks with `bea_io_raw.import_file`
(today patched) and uses `tri_fixtures.seed_codes_bundle`. It loads the script by path
with `importlib.util.spec_from_file_location`.

```python
def test_inspect_lists_zip_members_and_sheets(...): ...
def test_draft_copies_header_rows_and_lists_every_code(...): ...
def test_measure_counts_a_small_known_table(...):
    report = run_measure(...)
    assert report['use']['industry_codes'] == ['111CA', '2122A0', 'S00102']
    assert report['use']['negative_cells'] == 1
    assert report['concordance']['shared_naics'] == {'212221': ['2122A0', '2122B0']}
    assert report['ok'] is True

@pytest.mark.parametrize('stop', ['range_token', 'not_a_2017_code', 'gap_above_bound',
                                  'unknown_text', 'header_rows_differ'])
def test_measure_reports_each_stop_and_exits_1(stop, ...): ...
def test_measure_asks_above_five_percent_and_exits_0(...): ...
def test_preflight_refuses_an_unrecorded_file(...): ...   # exit 2
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_preflight_bea.py -q`
Expected: FAIL, the script does not exist.

- [ ] **Step 3: Implement `scripts/preflight_bea.py`**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_preflight_bea.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: add the BEA preflight checks`.

---

### Task 5: Acquisition, preflight and production layout (controller, owner-gated)

**Files:**
- Create: `src/embedding_data/bea_io_layout.json`
- Create: `specs/naics-evaluation-data-stage-15-findings.md` (Preflight section)
- Test: `tests/test_bea_io_layout.py` (one test added)

- [ ] **Step 1: Preservation baseline**

Record the byte length and SHA-256 of `data/raw/manifest.jsonl`. Run
`uv run --locked embedding-data audit --data-dir /Users/lowell/Projects/embedding-data/data`.
Expected: exit 0, no discrepancy. Both go into the findings file in Step 8.

- [ ] **Step 2: Acquire or import (Owner Checkpoint 4, host rule)**

Run the host-rule checks and get the go-ahead for the fetch. Then run:

```bash
uv run --locked python -m embedding_data.bea_io_tables acquire --snapshot DATE --data-dir /Users/lowell/Projects/embedding-data/data
```

Expected: one JSON line. For each kind in `import_required`, or refused by `acquire`, the
owner downloads the file in a browser from the source Task 1 recorded. Then run, with a
go-ahead per file and the host-rule checks:

```bash
uv run --locked python -m embedding_data.bea_io_tables import-file KIND FILE --snapshot DATE --data-dir /Users/lowell/Projects/embedding-data/data
```

Both files go under one snapshot date. If they are obtained on different days, ask the
owner which date names the snapshot. Record each file's path, size and SHA-256.

- [ ] **Step 3: Inspect and draft**

Run `uv run --locked python scripts/preflight_bea.py inspect --data-dir /Users/lowell/Projects/embedding-data/data --snapshot DATE`.
Find the one workbook and sheet holding the 2017 detail Use table, before redefinitions,
at producer value. If the Use file is a ZIP, name the one member (spec "Inputs"). If none
exists at about 402 industries, or two candidates do, stop (Owner Checkpoint 5). Read rows
with `rows`, then run `draft` for each kind. Write the draft layout in a scratch directory.
Fill `row_roles` and `column_roles` from BEA's own titles of each line: total,
final-demand and value-added lines. Fill the two intermediate totals: the commodity
intermediate-use total column and the industry intermediate-input total row. Fill the
zero marker and the concordance token fields from what the rows show.

- [ ] **Step 4: Measure**

Run `measure` with the draft layout, codes run `stage4_v11_20261013_r2` and its pin. Adjust
the draft until no unknown cell text remains that is a form of zero, and the token fields
match the forms in the file. Never add a range, exclusion or wildcard form. Keep the final
JSON output.

- [ ] **Step 5: Document checks (read; Owner Checkpoint 4 for any PDF)**

Read the BEA pages named in the spec. Save no document under the data root and register
none. For each, record the URL, the read date and a quote of fewer than 15 words:
- E1: the concordance's NAICS edition, from its header and from BEA's page.
- E2: BEA's reuse terms or public-domain statement for these tables and its date, and
  its citation guidance. Record the basis that passes (owner decision 4): an explicit
  BEA statement, or else 17 U.S.C. § 105 with no BEA statement that restricts reuse.
- E3: the Task 1 Step 1 record.

- [ ] **Step 6: Decide (Owner Checkpoint 5)**

If `measure` lists any stop, or the edition is not NAICS 2017, or a BEA statement
restricts publishing aggregates, stop the stage. Report to the owner and do no further
task. If `asks` is not empty, ask the owner before going on.

- [ ] **Step 7: Write the failing test**

```python
def test_production_layout_is_recorded():
    layout = bea_io_layout.load_layout()
    assert layout.use.intermediate_total_row in layout.use.row_roles
    assert layout.use.intermediate_total_column in layout.use.column_roles
```

Run: `uv run --locked pytest tests/test_bea_io_layout.py::test_production_layout_is_recorded -q`
Expected: FAIL, `production BEA layout is not recorded`.

- [ ] **Step 8: Commit the layout**

Save the final draft as `src/embedding_data/bea_io_layout.json` in `layout_json` form, then
run the test again. Expected: PASS. Write the findings file's Preflight section:
1. The snapshot date, and each raw file's path, size, SHA-256 and source (URL or browser
   import).
2. The Task 1 facts and the ZIP member, if any.
3. The `measure` output for E1 as a short table, with the 5% rate and the special codes.
4. The document checks E1–E3 and the E2 basis.
5. The preservation baseline of Step 1.

Commit the layout, the test and the findings file with the message
`feat: record the measured BEA layout and preflight`.

---

### Task 6: Published-aggregate contract

**Files:**
- Create: `src/embedding_data/published_target_contract.py`
- Test: `tests/test_published_target_contract.py`

**Interfaces:**
- Consumes: `target_contract.TARGET_SCHEMA`, `TARGET_KEY_COLUMNS`, `valid_unit`;
  `target_io.file_record`; `geography_references.occupied`.
- Produces:
  - `SCHEMA_VERSION = 'targets-published-v1'`
  - `validate_published_targets(frame: pl.LazyFrame | pl.DataFrame) -> None`
  - `write_published_targets(frame: pl.LazyFrame | pl.DataFrame, destination: Path) -> dict`

**Rules (spec "Published-aggregate contract"):** every check of
`target_contract.validate_targets` (`src/embedding_data/target_contract.py:38-76`), with
the same messages, except:
- `n_unweighted` and `n_weighted` may be null only together, and only on a row whose flags
  contain `count_not_published` and `published_aggregate`.
- `value` may be null only on a row flagged `share_denominator_not_positive`.
- A row flagged `se_not_published` has `se` null and `se_method` `none`.

The writer sorts by `TARGET_KEY_COLUMNS`, refuses an occupied destination, sinks, re-reads
and revalidates, checks the sort and the row count, and returns Settled Default 20's
record.

- [ ] **Step 1: Write the failing tests**

```python
def test_null_counts_need_both_flags(): ...      # each flag alone: ValueError; both: ok
def test_counts_are_null_together(): ...         # one null, one not: ValueError
def test_null_value_needs_its_flag(): ...
def test_se_not_published_needs_null_se_and_none(): ...

@pytest.mark.parametrize('case', TARGETS_V1_CASES)
def test_agrees_with_targets_v1_on_rows_without_exemptions(case):
    # TARGETS_V1_CASES: a valid row and one defect per validate_targets check (schema
    # order, null metadata, blank metadata, nonfinite value, negative n_weighted, bad se,
    # unsorted flags, invalid unit, duplicate keys)
    assert outcome(target_contract.validate_targets, case) == outcome(
        published_target_contract.validate_published_targets, case)

def test_writer_sorts_validates_and_records_the_version(tmp_path):
    record = published_target_contract.write_published_targets(frame, tmp_path / 't.parquet')
    assert record['schema_version'] == 'targets-published-v1'
    assert record['rows'] == frame.height
def test_writer_refuses_an_occupied_destination(tmp_path): ...
```

`outcome` returns `None` or the `ValueError` message.

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_published_target_contract.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement `published_target_contract`**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_published_target_contract.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: add the targets-published-v1 contract`.

---

### Task 7: Code table

**Files:**
- Create: `src/embedding_data/bea_io_code_table.py`
- Test: `tests/test_bea_io_code_table.py`

**Interfaces:**
- Consumes: `UseScan`, `ConcordanceScan`, `SelectedCodes`, `ConcordanceLayout.partial_marker`.
- Produces:
  - `CODES_CONTRACT = 'bea-io-codes-v1'`
  - `CODE_SCHEMA = {'bea_code': pl.String, 'title': pl.String, 'commodity_unit': pl.String, 'industry_unit': pl.String, 'is_commodity': pl.Boolean, 'is_industry': pl.Boolean, 'naics_2017_published': pl.List(pl.String), 'naics_2017_candidates': pl.List(pl.String), 'naics_2022_candidates': pl.List(pl.String), 'flags': pl.List(pl.String)}`
  - `commodity_unit(code: str) -> str`, `industry_unit(code: str) -> str` (the verbatim
    `feature:` strings)
  - `build_code_table(use: UseScan, concordance: ConcordanceScan, codes: SelectedCodes, *, partial_marker: str | None) -> pl.DataFrame`
  - `validate_code_table(table: pl.DataFrame) -> None`
  - `code_table_report(table: pl.DataFrame, use: UseScan, concordance: ConcordanceScan) -> dict`:
    counts by flag, by number of NAICS 2017 and of NAICS 2022 candidates,
    `title_differs_by_role`, `concordance_only_codes`, and `no_member_share`

**Rules (spec "Code table"):** one row per interior Use code (commodity rows and industry
columns, not registered lines), sorted by `bea_code`. Title by Settled Default 15. A code
absent from the concordance gets empty lists and `not_in_concordance`,
`no_naics_member`. A published six-digit code must be a 2017 `national_industry` code in
`nodes_2017`. A shorter one must be a 2017 node code at any level, and expands to the 2017
national industries whose code starts with it (`naics_expanded`). Either failure raises
`ValueError`. Each candidate maps through `crosswalk` to `naics:2022:national_industry:`
IDs, all kept. Flags by the spec's list, with `naics_shared` by Settled Default 14 and a
crosswalk flag for each link type `1:m`, `m:1`, `m:m` met. `validate_code_table` checks
the exact schema, unique codes, sorted unique lists and flags, and both unit strings
present exactly when the role is.

- [ ] **Step 1: Write the failing tests**

Use the real Stage 4 fixture bundle (`seed_codes_bundle`, module scope) and small typed
scans. Pick the 2017 codes for the link-type cases from its `crosswalk` in the test setup,
not by hand.

```python
def test_six_digit_code_is_its_own_candidate(...): ...
def test_shorter_code_expands_to_its_national_industries(...):
    row = table.row(by_predicate=pl.col('bea_code') == '3361MV', named=True)
    assert row['naics_2017_candidates'] == sorted(
        f'naics:2017:national_industry:{c}' for c in fixture_2017_leaves_under('3361'))
    assert 'naics_expanded' in row['flags']
def test_special_code_has_no_member_and_is_not_a_failure(...): ...
def test_shared_code_is_flagged_on_both_bea_codes(...): ...
@pytest.mark.parametrize('link', ['1:m', 'm:1', 'm:m'])
def test_crosswalk_links_keep_every_target_and_flag_their_type(link, ...): ...
def test_partial_marker_is_kept_as_published_and_flagged(...): ...
def test_unofficial_or_unknown_code_fails(...): ...   # '999999' and '3399' not in 2017
def test_2017_code_without_crosswalk_row_is_flagged_unmapped(...): ...
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_bea_io_code_table.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement `bea_io_code_table`**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_bea_io_code_table.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: build the BEA code table with NAICS candidate sets`.

---

### Task 8: Targets, totals and validation

**Files:**
- Create: `src/embedding_data/bea_io_targets.py`
- Test: `tests/test_bea_io_targets.py`

**Interfaces:**
- Consumes: `UseScan`, `UseLayout`, `line_gaps`, the code table,
  `validate_published_targets`.
- Produces:
  - `TOTALS_CONTRACT = 'bea-io-totals-v1'`, the target metadata constants of Global
    Constraints, `MEASURES = ('use_value_usd_millions', 'input_share', 'customer_share')`,
    `ROW_FLAGS` (the four every-row flags)
  - `TOTALS_SCHEMA = {'row_code': pl.String, 'column_code': pl.String, 'row_title': pl.String, 'column_title': pl.String, 'row_role': pl.String, 'column_role': pl.String, 'value': pl.Float64}`
  - `universe(snapshot: date) -> str`
  - `check_gaps(gaps: pl.DataFrame) -> None`: `ValueError('total gap above the rounding bound')`
  - `build_targets(use: UseScan, layout: UseLayout, codes: pl.DataFrame, *, snapshot: date) -> pl.DataFrame`
  - `build_totals(use: UseScan) -> pl.DataFrame`, sorted by `row_code`, `column_code`
  - `validate_products(targets: pl.DataFrame, codes: pl.DataFrame, totals: pl.DataFrame, use: UseScan) -> None`
  - `targets_report(use: UseScan, codes: pl.DataFrame, targets: pl.DataFrame, gaps: pl.DataFrame) -> dict`

**Rules (spec "Use targets"):** three rows per nonzero commodity × industry cell. `T_c` and
`T_j` per the Estimand constraint. A share whose total is zero or negative has a null
value and `share_denominator_not_positive`. Other flags by the spec's list.
`share_outside_unit_interval` on a non-null share below 0 or above 1. Diagonal compares
BEA codes, never unit strings. `unit_a_no_naics_member` and `unit_b_no_naics_member` come
from the code table's `no_naics_member`. `validate_products` fails on a duplicate code, a
Use code missing from the code table, measures that do not cover the same cells, a share
outside `[0, 1]` without its flag, and a contract failure. Totals by Settled Default 12.
The report holds the spec's list: code counts by role; nonzero, zero, negative and
diagonal cells; cells and value whose commodity or industry has no NAICS member; the
largest gap and the line counts by `ceil(|gap|)`; Settled Default 18's distributions.

- [ ] **Step 1: Write the failing tests**

```python
def test_both_shares_use_their_published_totals(): ...
    # U=30, T_j=120, T_c=60: input_share 0.25, customer_share 0.5, value 30.0
def test_zero_cells_get_no_rows_and_three_measures_cover_the_same_cells(): ...
def test_diagonal_is_by_bea_code(): ...
def test_negative_cell_and_share_outside_the_interval_are_flagged(): ...
def test_nonpositive_total_gives_a_null_share_and_keeps_the_row(): ...
def test_every_row_has_the_fixed_metadata_and_four_flags(): ...
def test_code_in_both_roles_has_one_row_and_both_titles_survive():
    # code 'X1' is a commodity titled 'Widgets' and an industry titled 'Widget makers'
    assert codes.filter(pl.col('bea_code') == 'X1').height == 1
    assert row['commodity_unit'] == 'feature:bea_commodity_2017_detail:X1'
    assert row['industry_unit'] == 'feature:bea_industry_2017_detail:X1'
    assert {'Widgets', 'Widget makers'} <= set(totals['row_title']) | set(totals['column_title'])
def test_totals_keep_final_demand_value_added_and_corner_cells(): ...
def test_gap_above_the_bound_fails_and_inside_it_passes(): ...
def test_report_distributions_use_nearest_rank(): ...
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_bea_io_targets.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement `bea_io_targets`**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_bea_io_targets.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: derive BEA input and customer shares with published totals`.

---

### Task 9: Bundle build, verify and compare

**Files:**
- Create: `src/embedding_data/bea_io_bundle.py`
- Test: `tests/test_bea_io_bundle.py`

**Interfaces:**
- Consumes: Tasks 1–8; `target_io`; `manifest`; `geography_references.safe_path`,
  `occupied`; in tests, `tri_fixtures.subprocess_modules`, `module_file`.
- Produces:
  - `TABLES = ('bea_io_use_targets', 'bea_io_codes', 'bea_io_totals')`,
    `FILES = (*(t + '.parquet' for t in TABLES), 'inputs.json', 'report.json')`
  - `CONTRACTS = {'codes': 'bea-io-codes-v1', 'totals': 'bea-io-totals-v1', 'targets': 'targets-published-v1', 'layout': 'bea-io-layout-v1'}`
  - `SOFTWARE_FILES: tuple[str, ...]`: the measured import closure (Step 3) plus
    `src/embedding_data/bea_io_layout.json`, `pyproject.toml` and `uv.lock`
  - `run_directory(data_dir: Path, run_id: str) -> Path`:
    `paths.derived_dir(data_dir, 'bea') / 'input-output' / run_id`
  - `freeze_software() -> dict` and `ordered_equal(first, second) -> dict`, with the
    semantics of `tri_bundle.py:151-187`, written here
  - `build(data_dir: Path, run_id: str, *, codes_run: str, codes_outputs_sha256: str, snapshot: date, layout: Layout | None = None) -> dict`
    returning `{'run_id', 'directory', 'outputs_sha256'}`. `None` means `load_layout()`.
  - `verify_bundle(directory: Path, data_dir: Path, *, expected_outputs_sha256: str, layout: Layout | None = None) -> dict`
  - `compare_runs(first: Path, second: Path) -> dict`:
    `{'equal', 'tables', 'report_equal', 'inputs_equal', 'trust_established': False}`

**`inputs.json`:** `run_id`, `contracts`, `codes` (`SelectedCodes.provenance()`), `raw`
(`bea_io_raw.citations`), `snapshot`, `layout` (`layout_json`), `rules` (one sentence each
for `estimand`, `zero_cells`, `rounding_bound`, `naics_candidates`, from the spec),
`software`, `execution` (`commit`, `dirty`, `created_at`).

**`report.json`:** `contracts`, `snapshot`, `codes` (`code_table_report`), `use`
(`targets_report`), `tables` (each table's record, the targets with `schema_version`),
`limits` (the spec's Methodological limits bullets, verbatim), `universe`,
`headline` `'non_headline'`. No run ID, time, commit or path.

**Build order:** `target_io.stage`; `freeze_software()`; `select_codes`; `select_files`;
`read_use`; `read_concordance`; `line_gaps`; `check_gaps`; `build_code_table`;
`validate_code_table`; `build_targets`; `build_totals`; `validate_products`. Write the
targets with `write_published_targets` and the other two with `write_parquet`. Re-read
each table, validate it again, and compare it with `ordered_equal`. Write `inputs.json`
and `report.json`. Recheck the codes selection, the software and the raw citations.
Write `outputs.json` (`target_io.inventory` of the five files). Check the exact file set,
refuse an occupied final name, and rename. `finally`: remove only this run's staging.

**Verify order:** a `.part` name fails; pin syntax; the SHA-256 of `outputs.json`; the
exact file set; `verify_inventory`; strict canonical JSON (as `tri_bundle._read_json`);
run ID and contracts; recorded layout equals the supplied layout; recorded software
equals `freeze_software()`; `target_io.verify_raw` on the citations. Recompute in a
`tempfile.TemporaryDirectory()` from the recorded codes run, pin and snapshot. Compare each
table in order, then the report, then `inputs.json` with the recorded `execution`.

- [ ] **Step 1: Write the failing tests**

Module fixture: `seed_codes_bundle`, then a small synthetic Use workbook and concordance in
the production layout (`bea_fixtures.use_sheet` with `load_layout().use`), imported for
one snapshot.

```python
def test_build_publishes_the_exact_file_set_and_detached_pin(built): ...
    # 6 files; outputs.json lists the other five; pin == sha256(outputs.json)
def test_verify_passes_then_refuses_a_changed_byte_report_or_pin(built, tmp_path): ...
@pytest.mark.parametrize('change', ['raw_byte', 'header_row', 'occupied_final',
                                    'codes_pin', 'other_layout', 'gap_above_bound'])
def test_build_refuses(change, ...): ...
def test_leftover_staging_is_refused_and_untouched(built, tmp_path):
    # create <id>.part with one file; build with <id> raises; the .part bytes are unchanged
    # and no <id> exists; build with a fresh ID succeeds
def test_software_change_before_publication_fails_without_a_final(monkeypatch, ...): ...
def test_failure_removes_only_its_own_staging(...): ...
def test_compare_runs_equal_and_unequal(...): ...
    # two builds: equal; a third from a changed cell: unequal, tables names the differences
def test_report_has_no_run_identity(built): ...
def test_software_files_cover_the_bundle_import_closure():
    loaded = subprocess_modules('embedding_data.bea_io_bundle')
    assert {module_file(m) for m in loaded} <= set(bea_io_bundle.SOFTWARE_FILES)
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_bea_io_bundle.py -q`
Expected: FAIL, `ModuleNotFoundError`.

- [ ] **Step 3: Implement `bea_io_bundle`**

Get the closure with `uv run --locked python -c "import sys, embedding_data.bea_io_bundle, embedding_data.bea_io_tables; print(sorted(m for m in sys.modules if m.startswith('embedding_data')))"`.
Write `SOFTWARE_FILES` as a sorted literal of those files plus the three named ones.

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_bea_io_bundle.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: build, verify and compare BEA input-output bundles`.

---

### Task 10: Complete command group and README

**Files:**
- Modify: `src/embedding_data/bea_io_tables.py`
- Modify: `README.md` (new section after "USAspending vendor links (roadmap Stage 14)")
- Test: `tests/test_bea_io_cli.py`

**Interfaces:**
- Consumes: `bea_io_bundle.build`, `verify_bundle`, `compare_runs`, `run_directory`.
- Produces the commands
  `build RUN_ID --codes-run ID --codes-outputs-sha256 PIN --snapshot DATE`,
  `verify RUN_ID --outputs-sha256 PIN` and `compare-runs FIRST SECOND`, each with
  `--data-dir`. `compare-runs` exits 1 outside the `_invoke` guard, as
  `tri_parent_links.py:107-120` does. `--snapshot` is parsed with `date.fromisoformat`. A
  bad date fails with `validation`.

- [ ] **Step 1: Write the failing tests**

```python
def test_help_lists_exactly_five_commands(cli_runner): ...
    # acquire, import-file, build, verify, compare-runs
def test_build_verify_and_compare_print_one_sorted_json_line(cli_runner, ...): ...
def test_build_failure_prints_only_the_fixed_line(cli_runner, ...):
    assert result.exit_code == 2
    assert result.output.strip() == ('BEA input-output build failed: validation; '
                                     'run bad; path derived/bea/input-output/bad')
def test_unequal_compare_exits_1(cli_runner, ...): ...
def test_offline_commands_open_no_connection(cli_runner, monkeypatch, ...):
    forbid_external_access(monkeypatch)
    monkeypatch.setattr(httpx.Client, '__init__', no_client)
    # import-file, build, verify, compare-runs all succeed
def test_command_module_loads_no_dotenv_or_ipumspy():
    loaded = subprocess_modules('embedding_data.bea_io_tables', prefix=None)
    assert 'dotenv' not in loaded and 'ipumspy' not in loaded
def test_software_files_equal_the_command_import_closure():
    closure = {module_file(m) for m in subprocess_modules('embedding_data.bea_io_tables')}
    assert set(bea_io_bundle.SOFTWARE_FILES) == closure | {
        'src/embedding_data/bea_io_layout.json', 'pyproject.toml', 'uv.lock'}
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_bea_io_cli.py -q`
Expected: FAIL, no `build` command.

- [ ] **Step 3: Add the three commands**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_bea_io_cli.py tests/test_bea_io_bundle.py -q`
Expected: all pass.

- [ ] **Step 5: Write the README section**

Heading `## BEA input-output tables (roadmap Stage 15)`. Contents:
1. What O9 and O10 measure, and a link to `specs/bea-input-output-tables.md`.
2. The command table from the spec's "Module and commands".
3. The offline rule, the failure line, and that only `acquire` uses the network.
4. The production commands with `RUN_ID`, `RUN_PIN` and `DATE` placeholders, the codes
   run `stage4_v11_20261013_r2` and its pin, and
   `--data-dir /Users/lowell/Projects/embedding-data/data`.
5. The host rule.
6. The R8.4 exclusion and the non-headline status.
7. That selected run pins wait for the owner's decision on hardening.

- [ ] **Step 6: Commit**

Message: `feat: add BEA build, verify and compare commands`.

---

### Task 11: V12 fixture chain

**Files:**
- Modify: `tests/bea_fixtures.py`
- Test: `tests/test_bea_io_v12.py`

**Interfaces:**
- Consumes: `seed_codes_bundle`, `write_workbook`, `write_zip`, `use_sheet`,
  `bea_io_layout.load_layout`, the CLI app, `forbid_external_access`.
- Produces in `tests/bea_fixtures.py`:
  - `V12_SNAPSHOT = date(2026, 11, 24)`, `V12_RUNS = ('v12_first', 'v12_second')`
  - `v12_files(directory: Path) -> dict[str, Path]`: the synthetic Use file (a ZIP with
    the registered member when the production layout names one) and concordance, in the
    production layout
  - `run_bea_v12(tmp_path: Path, monkeypatch, cli_runner) -> dict` with keys `data_dir`,
    `first`, `second` (bundle directories), `first_pin`, `second_pin`,
    `first_verification`, `second_verification` and `comparison`. External access is
    blocked first. It runs `import-file` (with `today` patched), `build`, `verify`, a
    second `build` and `compare-runs` through the CLI.

**Required cases (spec "V12 extension"):** a special code with no NAICS member; a shorter
NAICS code; a NAICS code shared by two BEA codes; a 2017 code with a `1:m` link to 2022; a
diagonal cell; a negative cell; a zero total; a rounding gap inside the bound. Also a
partial marker if the production layout registers one, and a continuation row if it allows
them. Every registered total, final-demand and value-added line appears. One BEA code
cell and one single-code NAICS cell are written as `int`, as real files may store them.
Use real 2017 codes from the fixture bundle, chosen in the helper from `crosswalk` and
`nodes_2017`.

- [ ] **Step 1: Write the failing tests**

```python
def test_v12_chain_is_offline_verified_and_replay_equal(tmp_path, monkeypatch, cli_runner):
    result = run_bea_v12(tmp_path, monkeypatch, cli_runner)
    assert result['comparison']['equal'] is True
    assert result['first_verification']['outputs_sha256'] == result['first_pin']

def test_v12_fixture_holds_every_required_case(tmp_path, monkeypatch, cli_runner):
    codes = pl.read_parquet(result['first'] / 'bea_io_codes.parquet')
    targets = pl.read_parquet(result['first'] / 'bea_io_use_targets.parquet')
    flags = set(codes['flags'].explode().drop_nulls()) | set(targets['flags'].explode())
    assert {'no_naics_member', 'naics_expanded', 'naics_shared', 'crosswalk_one_to_many',
            'diagonal', 'negative_value', 'share_denominator_not_positive'} <= flags
    report = json.loads((result['first'] / 'report.json').read_text())
    # the largest gap is above 0 and inside the bound
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_bea_io_v12.py -q`
Expected: FAIL, `ImportError: cannot import name 'run_bea_v12'`.

- [ ] **Step 3: Implement `v12_files` and `run_bea_v12`**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_bea_io_v12.py -q`
Expected: all pass. If one test takes 60 s or more, report it to the owner: marking it
`slow` means editing `tests/conftest.py`, which this plan does not do.

- [ ] **Step 5: Commit**

Message: `test: add the BEA V12 raw-to-replay fixture chain`.

---

### Task 12: Independent reconciler

**Files:**
- Create: `scripts/reconcile_bea_io_tables.py`
- Test: `tests/test_reconcile_bea_io_tables.py`

**Interfaces:**
- Consumes: nothing from Stage 15 modules. It imports only the standard library and
  `polars`. No `embedding_data` import.
- Produces: `python scripts/reconcile_bea_io_tables.py --data-dir D --run ID --outputs-sha256 PIN`.
  It prints one sorted JSON line of counts and booleans. It exits 0 when everything is
  equal, 1 when something differs and 2 on a refusal. Module constant
  `LAYOUT: dict` is its own literal copy of the committed layout JSON.

**Independence:** it checks the pin, reads `inputs.json` for the two raw paths and their
SHA-256, and checks each raw file's hash. It reads `derived/codes/<run>/outputs.json`,
checks it against the recorded codes pin and the three Parquets' records, and reads them
with Polars. It reads the workbooks with `zipfile` and `xml.etree` (Settled Default 23):
shared strings (every `<t>` of an `<si>`), inline strings and numeric `<v>` cells. A
numeric value cell reads as `repr(float(v))`. A numeric code, title or NAICS cell reads as
its raw `<v>` text. From the spec's text, with plain Python, it recomputes the code table,
the three measures, the totals table, the gaps with `decimal.Decimal` (formatted as in
Settled Default 13), and the report counts. It compares them exactly with the bundle's three tables and
`report.json`'s counts and distributions.

- [ ] **Step 1: Write the failing tests**

```python
def test_reconciler_layout_equals_the_committed_layout():
    assert reconcile.LAYOUT == bea_io_layout.layout_json(bea_io_layout.load_layout())
def test_reconciler_imports_no_embedding_data_module():
    tree = ast.parse(SCRIPT.read_text())
    assert not [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                and 'embedding_data' in ast.unparse(n)]
def test_reconciler_reports_equal_on_the_v12_bundle(tmp_path, monkeypatch, cli_runner): ...
def test_reconciler_gap_strings_equal_the_build_on_whole_number_cells(tmp_path, ...):
    # a line of int cells (1 + 1, total 3): the reconciler's gap string == report's == '1'
def test_reconciler_detects_a_changed_share(tmp_path, monkeypatch, cli_runner): ...
    # copy the bundle, change one input_share, rewrite outputs.json; new pin: exit 1
def test_reconciler_refuses_a_wrong_pin(tmp_path, monkeypatch, cli_runner): ...   # exit 2
```

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_reconcile_bea_io_tables.py -q`
Expected: FAIL, the script does not exist.

- [ ] **Step 3: Implement the script from the spec's text**

Write it from the spec's sections, not from the build modules.

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_reconcile_bea_io_tables.py -q`
Expected: all pass.

- [ ] **Step 5: Full suite**

Run the Stage 9 `pgrep` check, then `uv run --locked behave` and
`uv run --locked pre-commit run coverage-check-full --hook-stage pre-push --all-files`.
Expected: every scenario and test passes (the `network` canary is deselected).

- [ ] **Step 6: Commit**

Message: `feat: add the independent BEA input-output reconciler`.

---

### Task 13: First full-data build and acceptance (controller, owner-gated)

**Files:** none changed. Results go to the findings file in Task 14.

- [ ] **Step 1: Clean execution state**

The worktree holds every task's commit and `git status --porcelain` prints nothing, so
`execution.dirty` is false. Use `uv run --locked` from this worktree's own `.venv` for
every command in this task, with no overlay, and change nothing in the venv between
Steps 3 and 5.

- [ ] **Step 2: Go-ahead (Owner Checkpoint 6, host rule)**

Choose a fresh run ID `stage15_bea_io_<YYYYMMDD>_r1` and confirm that neither it nor
`<id>.part` exists under `data/derived/bea/input-output/`.

- [ ] **Step 3: Build**

```bash
/usr/bin/time -l uv run --offline --locked python -m embedding_data.bea_io_tables build RUN_ID --codes-run stage4_v11_20261013_r2 --codes-outputs-sha256 15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a --snapshot DATE --data-dir /Users/lowell/Projects/embedding-data/data
```

Expected: one JSON line with `outputs_sha256`. Record the wall time, the maximum resident
set size and the bundle size (`du -sk`). Save `pgrep -fl 'embedding_data|embedding-data'`
right after, so the findings can say whether the host was idle.

- [ ] **Step 4: Verify**

```bash
uv run --offline --locked python -m embedding_data.bea_io_tables verify RUN_ID --outputs-sha256 RUN_PIN --data-dir /Users/lowell/Projects/embedding-data/data
```

Expected: exit 0 and one JSON line.

- [ ] **Step 5: Reconcile**

```bash
uv run --offline --locked python scripts/reconcile_bea_io_tables.py --data-dir /Users/lowell/Projects/embedding-data/data --run RUN_ID --outputs-sha256 RUN_PIN
```

Expected: exit 0, with every comparison true.

- [ ] **Step 6: Preservation**

1. The first `N` bytes of the current `data/raw/manifest.jsonl` hash to the Task 5
   baseline, where `N` is its recorded byte length. The lines after them include the two
   BEA entries. Show the owner any other appended line to account for.
2. `uv run --locked embedding-data audit --data-dir /Users/lowell/Projects/embedding-data/data`
   exits 0.
3. `derived/codes/stage4_v11_20261013_r2` passes
   `target_io.verify_inventory(directory, outputs, set(outputs))` against its own
   `outputs.json`, and that file's SHA-256 is
   `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`.

- [ ] **Step 7: On any failure**

Stop. Change no code. Report the failing step to the owner. Any cleanup of a failed run's
staging needs its own go-ahead.

---

### Task 14: Findings, source spec amendment and completion (controller)

**Files:**
- Modify: `specs/naics-evaluation-data-stage-15-findings.md`
- Modify: `specs/embedding-evaluation-data-spec.md`
- Modify: `CLAUDE.md`
- Modify at completion: `specs/naics-evaluation-data-roadmap.md`, `specs/deferred_items.md`,
  `specs/history.md`; move this plan and the spec to their `completed/` folders

- [ ] **Step 1: Finish the findings file (one screen)**

Add these sections:
1. The run ID, the detached pin, the snapshot date, and the wall time, maximum RSS and
   bundle size of the real run, with the `pgrep` list taken after it.
2. The `verify` and reconciler outcomes and the preservation results.
3. The main counts: commodity, industry, final-demand and value-added codes; nonzero,
   negative and diagonal cells; target rows; code-table flags; the largest gap.
4. "For the resume and O19", as the spec's Rollout lists them: the run ID, pin and
   snapshot date; the share distributions; the totals table; the code-table flags; the
   universe statement; the non-headline status; the R8.4 exclusion. Note that protocol
   VL6 calls BEA tables "not built", which O19 updates.

Fixture results are not benchmarks.

- [ ] **Step 2: Amend `specs/embedding-evaluation-data-spec.md`**

Item 5, R7.5. Replace:

```
The ACS wage microdata have their own schema, outside the long schema above.
*(owner, plan 14, 2026-11-19)*
```

with:

```
The ACS wage microdata have their own schema, outside the long schema above.
*(owner, plan 14, 2026-11-19)*

**R7.5** A target taken from a published aggregate table keeps the published value.
It names each R7.1 or R7.3 field the publisher does not supply, sets it to null and
flags it. It never fills or models that field. *(owner, Stage 2 default 3,
2026-11-16)* Such targets use the R7.4 columns under schema version
`targets-published-v1`. *(owner, Stage 15 design, 2026-11-23)*
```

Item 3. After the USAspending row of the R1.1 table, add:

```
| BEA benchmark input–output accounts, detail Use table | BEA detail commodity × industry | 2017 benchmark | Published commodity flows to buying industries (non-headline) |
```

Item 6. After the Vendor links row of the R7.2 table, add:

```
| Input–output use | BEA 2017 benchmark Use table | commodity → buying industry, as input and customer shares | NAICS (non-headline) |
```

and in the sentence below the table replace
`the vendor links family is *(owner, Stage 14 design, 2026-11-18; [stage spec](completed/usaspending-vendor-links.md))*; the others`
with
`the vendor links family is *(owner, Stage 14 design, 2026-11-18; [stage spec](completed/usaspending-vendor-links.md))*; the input–output use family is *(owner, Stage 15 design, 2026-11-23; [stage spec](completed/bea-input-output-tables.md))*; the others`.
The link points to the spec's retired path (Step 5).

R8.3 sentence (only because E2 passed in Task 5). Append to the R8.3 paragraph, after
`and publish no name or address.`, the sentence for the basis Task 5 recorded:
- BEA statement: ` BEA input–output tables are public under BEA's own statement. Tables derived from them may contain every published cell. They cite BEA.`
- 17 U.S.C. § 105: ` BEA input–output tables are public as U.S. government works (17 U.S.C. § 105), and no BEA statement restricts their reuse. Tables derived from them may contain every published cell. They cite BEA.`

- [ ] **Step 3: Amend `CLAUDE.md`**

Replace
``and USAspending vendor links (roadmap Stage 14, `python -m embedding_data.usaspending_vendor_links`).``
with
``USAspending vendor links (roadmap Stage 14, `python -m embedding_data.usaspending_vendor_links`), and BEA input-output tables (roadmap Stage 15, `python -m embedding_data.bea_io_tables`).``

After the "TRI parent links (roadmap Stage 5)" section, add a section
`**BEA input-output tables (roadmap Stage 15).**` like it: the five commands and which
one uses the network, `--data-dir`, the failure line and exit codes, the bundle path and
files, the layout JSON and its hash in `bea_io_bundle.SOFTWARE_FILES`, a link to the
findings file for the run, the non-headline status, no `size_gate_pending`, and the R8.4
exclusion. Name no run ID, pin, snapshot or commit: run pins wait for the owner's
decision on hardening (spec "Out of scope" and "Left to the builder").

- [ ] **Step 4: Commit**

Message: `docs(specs): record the Stage 15 BEA findings and source spec amendment`.

- [ ] **Step 5: Plan Completion Protocol**

Run the writing-plans Plan Completion Protocol, including step 3a. The
`## Handoff to later stages` section gives:
- The resume after Stage 15: the run ID, pin and snapshot date, for a hardening stage if
  the owner stages one (replay with the same raw files and `compare-runs`).
- O19: the share distributions in `report.json`, the totals table, the code-table flags,
  the universe statement, the non-headline status, the R8.4 exclusion, and the VL6
  wording.

Retire the spec to `specs/completed/` and re-point moved links.

- [ ] **Step 6: Integrate**

Run the Stage 9 `pgrep` check, then open the PR and follow the owner's PR-lifecycle rule.
