# ITA Establishment Targets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one immutable, offline Stage 10 bundle with ITA establishment links,
deduplicated text–code pairs and the co-ownership target. Add detached verification
and replay comparison.

**Architecture:** A standalone command group `python -m embedding_data.ita_establishment_targets`
(spec approach 1). New modules import frozen Stage 2–6 functions and never edit them.
One build keys every source record once into owned scratch, derives the three products,
gates them against the adopted V1/V2 tables, and publishes an exclusive `.part`
directory by rename.

**Tech Stack:** Python 3.14, Polars (lazy), Typer, httpx (acquisition only),
`pl.read_excel` (calamine), pytest, uv.

**Spec:** `specs/ita-establishment-targets.md` (owner-approved, commit `49b394c`).

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 1 — tick Stage 1 when its Exit holds; on plan completion, tick Stage 4 and re-validate later stages against what shipped. (Moved from Stage 10 of the parked `specs/completed/embedding-evaluation-data-spec-roadmap.md` on 2026-11-16.)

Process: lighter — first build (Gate 2), verify, the reconciliation script and the preservation checks, plus a one-screen findings file with measured wall time, peak memory and bundle size. The replay build, the long-form finding, the README/CLAUDE.md pins and plan 11's retirement go to Stage 4.

## Global Constraints

- **Branch.** Execute on a new branch cut from `main` at or after `e1470e7`, the
  merge of lowmason/embedding-data#8. That commit is the first on `main` with the
  spec and this plan.
- **Stage 9 host rule.** Before every commit, every full `pytest` run and every
  full-data command, run
  `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`.
  If it prints anything, stop. Leave the files uncommitted and tell the owner.
  Never skip a hook. At commit, `coverage-check` runs the suite without the `slow`
  tests and skips a commit whose files are all under `specs/` or root-level
  Markdown. `coverage-check-full` runs the whole suite before a push and on a merge
  commit (lowmason/embedding-data#10).
  The check cannot see an open Stage 9 freeze window. That is enough for commits,
  which write nothing under `data/`. Production writes need the owner's
  confirmation (Owner Checkpoints).
- **Leave alone.** Do not read or write Stage 9's worktree
  (`/Users/lowell/.codex/worktrees/acs-targets-design/embedding-data`),
  `specs/plans/9-acs-targets.md`, Stage 9's uncommitted plan 10, its probes or its
  evidence under `/private/tmp`. Do not read
  `data/derived/osha/verification/v1_v3_20261013_scopefix/`. Write nothing in the
  primary checkout `/Users/lowell/Projects/embedding-data` except the four gated
  production writes.
- **Merging.** Stage 9's checker hashes every `.py` file under `src`, `scripts`,
  `tests` and `features` of the checkout it runs from. Do not merge Stage 10 into
  `main` or any Stage 9 checkout without the owner. Avoiding a merge between a Stage 9
  freeze and its preservation check is Stage 9's responsibility.
- **Commit protocol.** Each task's commit step is: run the `pgrep` check, then
  `git add <the task's files>`, then `git commit` with the given message and the
  `Co-Authored-By` trailer from the session's attribution rule.
- **Production root.** Write to `/Users/lowell/Projects/embedding-data/data` only at
  the four owner-gated steps of Task 11. Tests use `tmp_path` roots and always pass
  `data_dir` or `--data-dir` explicitly.
- **Frozen code.** Edit no existing file under `src/` or `scripts/`. The only
  existing `.py` file that changes is `tests/code_fixtures.py` (Task 2). Do not edit
  `pyproject.toml` or `uv.lock`: Stages 4 to 9 record the `uv.lock` hash, and Stages
  6 to 9 also hash `pyproject.toml`. Add no dependency and no console script. If a
  reused function cannot serve unchanged,
  stop and ask the owner (spec "Frozen modules").
- **Reused interfaces, imported unchanged.** `ita_verification.normalize_key`,
  `with_keys`, `PLACEHOLDERS`, `description_report`, `link_report`;
  `ita_references.read_titles`, `existing_reference`, `reference_path`, `TITLE_FILES`;
  `ita_area_mix.eligible_industry`; `target_contract.write_targets`, `validate_targets`,
  `TARGET_SCHEMA`, `TARGET_KEY_COLUMNS`; `target_io` (all public functions);
  `target_inputs.CODE_SCHEMAS`, `CANONICAL_SCHEMA`, `require_source_parity`,
  `validate_native`; `code_build.check_source`, `SCHEMA_VERSION`; `manifest`;
  `osha_benchmark_download.download`, `make_client`; `classification_tables.PATH_SCHEMA`,
  `naics_tables`; `geography_references.safe_path`, `occupied`.
- **No IPUMS imports.** Do not import `ipums_parity` or any `ipums_*`/`acs_*` module.
  `ipums_parity` pulls in `ipumspy`. Importing the Stage 10 command module must not
  load `dotenv` or `ipumspy`.
- **No upstream builders on production.** Never run `osha`,
  `ita_summary.build_summary_table`, `code_build.build`, verification `sample` or any
  other upstream builder against the production root. Tests may run them in `tmp_path`.
- **Acceptance values.** The only exact acceptance values are 3,206,055 source records
  and the integer columns of the `## V1` and `## V2` tables in
  `specs/findings/v1-v3-ita-verification.md`. All other counts are design-time recon,
  including the spec's 49,575, 29,067, about 644,265, 537,857, 106,408, 239,364, 8,110,
  19,576, about 39,152 and 6,516, and the recon counts in this plan. Never put one in a
  test or gate. The index registry counts in Task 2 are parser registrations that the
  spec requires, not acceptance values.
- **Production identities.** Codes run `stage4_v11_20261013_r2`, detached `outputs.json`
  SHA-256 `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`.
  Adopted Stage 2 summary `derived/osha/ita_300a_summary.parquet`, SHA-256
  `6335cda7adb40a41c4a11d57d22048999449ac8d078a2ec0291f0198cd9136a8`, 139,930,636 bytes.
- **Contract versions (verbatim).** `ita-establishment-links-v1`, `ita-text-pairs-v1`,
  `ita-co-ownership-v1`, `naics-index-v1`, `targets-v1`.
- **Runs.** Bundles live in `data/derived/osha/establishment-targets/<RUN_ID>/`. Run IDs
  match `[A-Za-z0-9][A-Za-z0-9_-]*`. An existing final or `<RUN_ID>.part` fails. A
  later run never reuses, overwrites or deletes it.
- **Offline.** `import-reference`, `build`, `verify` and `compare-runs` load no `.env`,
  read no credential and construct no HTTP client. Only `acquire-references` uses the
  network.
- **Diagnostics.** The command group prints a fixed reason, the run ID and the path on
  failure. It never prints exception text, EINs, names or addresses.
- **Style.** Single quotes, `'''` docstrings, 4-space indents, 99 columns,
  `uv run --locked ruff check .` clean. Polars lazy with method-style expressions.
  No pandas.
- **R8.4.** No output feeds embedder training, curriculum, hard-negative mining or
  model selection. The README section and the finding say so.
- **Fixtures.** Fixture results show software readiness. They are never benchmarks.

## Owner Checkpoints

1. **Frozen modules (any task).** If a reused function cannot serve unchanged, stop
   and ask the owner. Do not edit it.
2. **Index parsing (Task 2, Task 11).** D2 settles the cross-reference rows. If the
   bytes acquired in Task 11 differ from the registered size or SHA-256, or a parse
   fails, stop and ask the owner. Never relax the parser to fit.
3. **Production writes (Task 11).** Get a go-ahead before each of: (1) the index
   acquisition or import, (2) the first full-data build, (3) the replay build, (4) any
   cleanup of a failed run's leftover staging. Each time, the owner confirms that no
   Stage 9 freeze window is open. The controller runs Task 11 itself, because a
   dispatched subagent cannot ask the owner for a go-ahead.

## Review Focus

1. **Variant spellings.** Case, repeated or non-breaking spaces and full-width forms
   under one EIN make one pair. Every delivered original is kept and the record count
   is exact. Test: Task 5 `test_variant_spellings_share_one_pair`.
2. **EIN spellings.** `12-3456789` and `123456789` are one employer. The 8-digit
   `23456789` joins only the padded sensitivity. Test: Task 6
   `test_ein_spellings_count_once`.
3. **Exact duplicate rows.** Pairs and members keep both rows. The link table collapses
   them into one base record that lists both source rows. Test: Task 7
   `test_exact_duplicates_collapse_only_for_links`.
4. **Killed build.** A leftover `<RUN_ID>.part` makes a rerun with that ID fail and stay
   byte-identical. A fresh ID builds. Test: Task 8
   `test_leftover_staging_is_refused_and_untouched`.
5. **Index whitespace.** Official entries can carry trailing spaces (64 in 2017,
   recon). A description without the space still gets the copied-index flag. Test:
   Task 4 `test_index_whitespace_still_flags_copy`.

## Decisions

- **D1** (owner, brief, 2026-11-13): The planning session may download the three public Census NAICS index files to a scratch folder outside `data/`, only to fix URLs, layout and counts. Nothing is recorded, and production acquisition downloads the registered originals again. Applied in: Task 2 (registered facts), Task 11 (acquisition).
- **D2** (owner, planning stop-and-ask, 2026-11-14): Each official index file ends with 25 cross-reference rows whose code is `******`. Keep them as a counted cross-reference class with the delivered code, and include their entries in the copied-index flags. Registered row counts are 19,280 / 20,082 / 20,398, each with 25 cross-references. The owner approved the amendment wording at plan review on 2026-11-14. Applied in: Task 2 (spec amendment).
- **D3** (owner, plan review, 2026-11-14): Approve plan 11 with every settled default unchanged. Commit the plan on `claude/nervous-maxwell-7ab7f8` and do not merge to `main` until the owner decides. Applied in: Global Constraints (Branch, Merging).
- **D4** (owner, after plan review, 2026-11-14): Merge the spec and this plan into `main` through lowmason/embedding-data#8 (merge commit `e1470e7`), and delete the remote planning branch. Execution starts from `main`. Applied in: Global Constraints (Branch).
- **D5** (owner, brief, 2026-11-16): Plan 11 finishes in `specs/naics-evaluation-data-roadmap.md` as Stages 1 and 4, with the lighter Stage 1 process. Stage 1 runs Task 11 Step 1 (a new snapshot), Step 3 (the first run's ID only), Step 4 (Gate 2), Step 6 for the first run only (`verify`, no `compare-runs`), Steps 7 and 8, and Step 8a, which writes `specs/naics-evaluation-data-stage-1-findings.md`. Stage 4 runs Steps 5, 6 (the replay's `verify` and `compare-runs`), 9 and 10, then the Plan Completion Protocol. When Stage 1's Exit holds, Stage 1 ticks its roadmap box with the stamp `> Stage 1: COMPLETE (<date>) — implemented by plan 11 (specs/plans/11-ita-establishment-targets.md), Task 11 first build; findings in specs/naics-evaluation-data-stage-1-findings.md.` and changes `Stage 1` to `Stage 4` in this plan's Roadmap line. Stage 1 does not run the Plan Completion Protocol. Applied in: header (Process line), Task 11.
- **D6** (owner, brief, 2026-11-16): Preservation (Task 11 Step 8) runs in Stage 1, reversing `cbeaf2b`'s move to Stage 4. Applied in: `specs/naics-evaluation-data-roadmap.md` (Choices made, Stage 1 Exit and Leaves out, Stage 4), Task 11 Step 8.

## Settled Defaults (for owner review)

- **Integration.** This branch (spec and plan) is not merged to `main` during
  planning. The owner chooses merge, PR or keep at plan review.
- **Gate scope.** When the selected Stage 2 source is the adopted summary, the V1/V2
  constants and 3,206,055 are mandatory, and explicit expectations are refused. Any
  other source needs explicit `expectations=` through the Python API, which only
  tests use. The command group cannot build a non-adopted source. `report.json`
  records the basis.
- **Index strings.** Index entries keep their delivered strings, including leading
  and trailing spaces. Only keys are normalized.
- **Index pins.** The registry pins each original's size and SHA-256, as Stage 5 does.
  Changed Census bytes fail acquisition and need an owner decision.
- **Verify identity.** `verify` requires the current executing software identity to
  equal the build's recorded identity, as Stage 6 does.
- **Scratch.** Build scratch lives in `<RUN_ID>.part/.scratch/`, not in the system
  temporary directory. A killed build then leaves one owned path for gate 4, and the
  build writes nothing outside its own run. `verify` writes nothing under the data
  root, so it uses `tempfile.TemporaryDirectory()`.
- **Index registry scope.** For the adopted source, `build` and `verify` also require
  the production index registry. A fixture registry cannot produce a bundle that
  verifies with the adopted basis.

---

## File Map

| Path | Task | Responsibility |
| --- | --- | --- |
| `src/embedding_data/ita_establishment_expected.py` | 1 | Adopted V1/V2 constants, `Expectations`, gate check |
| `src/embedding_data/ita_index_references.py` | 2 | Index registry, parser, acquisition, import, reader |
| `src/embedding_data/ita_establishment_inputs.py` | 3 | Codes-only selector |
| `src/embedding_data/ita_establishment_records.py` | 4 | Keyed records, copied-text flags, V1 and index counts |
| `src/embedding_data/ita_text_pairs.py` | 5 | Pair tables, accounting, validator |
| `src/embedding_data/ita_co_ownership.py` | 6 | Co-ownership estimator, companions, validator |
| `src/embedding_data/ita_establishment_links.py` | 7 | Distinct records, links, statuses, V2 counts, validator |
| `src/embedding_data/ita_establishment_bundle.py` | 8 | Build, verify, compare, software identity |
| `src/embedding_data/ita_establishment_targets.py` | 9 | Typer command group |
| `scripts/reconcile_stage10.py` | 10 | Independent co-ownership and Stage 3 cross-checks |
| `tests/ita_establishment_fixtures.py` | 2, 4, 5, 8, 10 | Frame builders, originals seeding, index workbooks, fixture chain |
| `tests/test_ita_establishment_*.py`, `tests/test_ita_index_references.py`, `tests/test_ita_text_pairs.py`, `tests/test_ita_co_ownership.py`, `tests/test_reconcile_stage10.py` | 1–10 | Tests |
| `tests/code_fixtures.py` | 2 | `write_xlsx` gains `sheet='Fixture'` keyword |
| `specs/ita-establishment-targets.md` | 2 | D2 amendment |
| `specs/embedding-evaluation-data-spec.md` | 4 | R2.6 amendment |
| `README.md`, `CLAUDE.md` | 9, 11 | Stage 10 commands, then selected runs |
| `specs/findings/stage-10-ita-establishment-targets.md` | 11 | Measured acceptance |

---

### Task 1: Adopted reproduction constants

**Files:**
- Create: `src/embedding_data/ita_establishment_expected.py`
- Test: `tests/test_ita_establishment_expected.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `SOURCE_RECORDS = 3_206_055`, `YEARS = tuple(range(2016, 2026))`
  - `YEAR_PAIRS = ((2016, 2017), (2017, 2018), (2018, 2019), (2019, 2020), (2020, 2021), (2021, 2022), (2022, 2023), (2023, 2024), (2023, 2025), (2024, 2025))`, the V2 table order
  - `V1_COLUMNS = ('n_rows', 'n_empty', 'n_placeholder', 'n_copied_any', 'n_native_title_match', 'n_vintage_unknown', 'n_employer_unknown', 'n_employer_company', 'n_ein_padded', 'n_mojibake', 'n_repeat_rows', 'n_repeat_excess')`
  - `V2_COLUMNS = ('n_cohort_ids', 'n_raw_reappeared', 'n_unique_cohort_ids', 'n_reappeared', 'n_same_ein_address', 'n_same_ein_address_including_padded', 'n_same_raw_ein_address', 'n_reappeared_ein_unknown', 'n_reappeared_ein_conflict', 'n_reappeared_address_conflict', 'n_base_missing_id_rows', 'n_later_missing_id_rows', 'n_unique_address_matches', 'n_address_matches_different_id')`
  - `V1: dict[int, dict[str, int]]`, `V2: dict[tuple[int, int], dict[str, int]]`: integer literals
  - `ADOPTED_SOURCE = {'path': 'derived/osha/ita_300a_summary.parquet', 'sha256': '6335cda7adb40a41c4a11d57d22048999449ac8d078a2ec0291f0198cd9136a8', 'size': 139930636}`
  - `@dataclass(frozen=True) class Expectations: basis: str; source_records: int; v1: dict[int, dict[str, int]]; v2: dict[tuple[int, int], dict[str, int]]`, with `to_json(self) -> dict` and `@classmethod from_json(cls, value: dict) -> Expectations`. JSON keys are `'2016'` for years and `'2016-2017'` for pairs.
  - `ADOPTED_BASIS = 'adopted_v1_v3_finding'`, `ADOPTED = Expectations(ADOPTED_BASIS, SOURCE_RECORDS, V1, V2)`
  - `expectations_for(source: dict, explicit: Expectations | None = None) -> Expectations`.
    Its `source` has `sha256` and `size`. For the adopted source it returns `ADOPTED`
    and raises `ValueError` when `explicit` is given. For any other source it requires
    `explicit`, whose basis must not be `ADOPTED_BASIS`.
  - `check_reproduction(expected: Expectations, *, source_records: int, v1: pl.DataFrame, v2: pl.DataFrame) -> dict`.
    `v1` has `year_filing_for` and `V1_COLUMNS`. `v2` has `base_year`, `later_year`
    and `V2_COLUMNS`. Raises `ValueError` with `'source record count differs'`,
    `'V1 reproduction differs'` or `'V2 reproduction differs'`. Returns
    `{'basis': ..., 'source_records': 'equal', 'v1': 'equal', 'v2': 'equal'}`.

- [ ] **Step 1: Write the failing tests**

```python
FINDING = Path(__file__).parents[1] / 'specs/findings/v1-v3-ita-verification.md'

def finding_table(heading: str) -> list[dict[str, str]]:
    '''Rows of the first table after the line equal to heading, before the next `## `.'''

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

def test_adopted_source_refuses_explicit_expectations(): ...   # ValueError
def test_other_source_requires_explicit_expectations(): ...    # ValueError without; returned with
def test_expectations_round_trip_json(): ...                  # from_json(to_json(ADOPTED)) == ADOPTED
def test_check_reproduction(): ...
    # frames built from ADOPTED pass; one V2 cell + 1 raises 'V2 reproduction differs';
    # source_records - 1 raises 'source record count differs'
```

`finding_table` must match the heading line exactly. The finding also holds a
`### V1 after exact duplicate collapse (diagnostic)` table, which must never be read.

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_ita_establishment_expected.py -q`
Expected: FAIL, `ModuleNotFoundError: embedding_data.ita_establishment_expected`.

- [ ] **Step 3: Implement the module**

Transcribe `V1` and `V2` as integer literals from the finding's `## V1` and `## V2`
tables. Do not parse the finding at import time. The test is the independent check.

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_ita_establishment_expected.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Files: the module and its test. Message: `feat: record adopted Stage 10 V1/V2 reproduction values`.

---

### Task 2: NAICS index references

**Files:**
- Create: `src/embedding_data/ita_index_references.py`
- Create: `tests/ita_establishment_fixtures.py`
- Modify: `tests/code_fixtures.py` (`write_xlsx`)
- Modify: `specs/ita-establishment-targets.md` (D2 amendment)
- Test: `tests/test_ita_index_references.py`

**Registered facts (D1 scratch fetch, 2026-11-14).** The scratch files are not
evidence and may be gone. These facts are the record.

| kind | URL | relative | sheet | header | bytes | SHA-256 | rows | `******` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `naics_index_2012` | `https://www.census.gov/naics/2012NAICS/2012_NAICS_Index_File.xls` | `naics/2012_NAICS_Index_File.xls` | `2012NAICS` | `NAICS12`, `INDEX ITEM DESCRIPTION` | 2,177,024 | `c688f221987497db897bbc0e641156997d4e2f528e4fd390a3ad983b13462a23` | 19,280 | 25 |
| `naics_index_2017` | `https://www.census.gov/naics/2017NAICS/2017_NAICS_Index_File.xlsx` | `naics/2017_NAICS_Index_File.xlsx` | `2017NAICS` | `NAICS17`, `INDEX ITEM DESCRIPTION` | 509,235 | `fb3b428300f698aa3d623e1a0edc50aaa3b729e930b7cdc22851825f487fb1ac` | 20,082 | 25 |
| `naics_index_2022` | `https://www.census.gov/naics/2022NAICS/2022_NAICS_Index_File.xlsx` | `naics/2022_NAICS_Index_File.xlsx` | `2022NAICS` | `NAICS22`, `INDEX ITEM DESCRIPTION` | 499,358 | `6506b37b9546dd9cec1f8b79e0b38b68e547a5cce5fd6f8332d35024dbd6cd63` | 20,398 | 25 |

- All three returned HTTP 200 over HTTP/2 to `osha_benchmark_download.USER_AGENT`,
  with no `Content-Length` and `Last-Modified: Mon, 13 Jul 2026 19:46:10 GMT`. The
  scripted path works, so `import-reference` is the fallback, not the plan.
- Each file has one sheet, two columns and the header in row 1. No code or entry is
  null. No `(code, entry)` row repeats. The 25 `******` rows are the last rows of each
  sheet. Two cross-reference texts differ in 2012 ("Laboratories (see specific type)",
  "Tailors--see …"). None equals a NAICS title key.
- Every other code is a six-digit leaf of its own vintage (recon: they cover 1,065 of
  1,065, 1,055 of 1,057 and 1,010 of 1,012 leaves). Entries with leading or trailing
  spaces: 28, 64, 66 (recon).
- `pl.read_excel(file, sheet_id=0, has_header=False, read_options={'dtypes': 'string'})`
  read all three, including the 2012 `.xls`. Fixtures write `.xlsx` only, so the
  `.xls` path is first exercised in Task 11.

**Interfaces:**
- Consumes: `ita_references.read_titles`, `existing_reference`, `reference_path`;
  `ita_verification.normalize_key`; `osha_benchmark_download.download`, `make_client`;
  `manifest`.
- Produces:
  - `INDEX_VERSION = 'naics-index-v1'`, `CROSS_REFERENCE = '******'`,
    `INDEX_SCHEMA = {'vintage': pl.Int64, 'code': pl.String, 'entry': pl.String}`
  - `@dataclass(frozen=True) class IndexReference: kind: str; vintage: int; url: str; relative: str; sheet: str; header: tuple[str, str]; sha256: str; size: int; expected_rows: int; expected_cross_references: int`
  - `REGISTRY: dict[str, IndexReference]`, holding the table above
  - `leaves_by_vintage(titles: pl.DataFrame) -> dict[int, frozenset[str]]`: six-digit codes per vintage
  - `parse_index(file: Path, reference: IndexReference, leaves: frozenset[str]) -> pl.DataFrame`
  - `acquire(data_dir: Path, *, registry: dict[str, IndexReference] = REGISTRY) -> list[Path]`
  - `import_reference(data_dir: Path, kind: str, original: Path, *, registry: dict[str, IndexReference] = REGISTRY) -> Path`
  - `read_index(data_dir: Path, titles: pl.DataFrame, *, registry: dict[str, IndexReference] = REGISTRY) -> pl.DataFrame`: `INDEX_SCHEMA` rows, vintages ascending, file order within a vintage
  - `citations(data_dir: Path, *, registry: dict[str, IndexReference] = REGISTRY) -> list[dict]`: `asdict(manifest.entry_for(...))` per original, sorted by path
  - Module global `make_client`, looked up at call time (test seam)
  - `tests/code_fixtures.py`: `write_xlsx(file: Path, rows: list[list[str | None]], *, sheet: str = 'Fixture') -> None`
  - `tests/ita_establishment_fixtures.py`:
    - `import_stage4_originals(data_dir: Path, directory: Path, kinds: tuple[str, ...] | None = None) -> None`.
      It reads `tests/fixtures/acs_mapping/upstream/stage4-originals.zip` and checks each
      member's size and SHA-256 against `provenance.json`, as
      `acs_mapping_fixtures._authenticated_codes` does. It then imports the selected
      kinds (all when `None`) through `code_references.import_reference`.
    - `seed_structure_titles(data_dir: Path, directory: Path) -> None` imports
      `naics_2012`, `naics_2017` and `naics_2022` only.
    - `write_index_workbook(file: Path, sheet: str, header: tuple[str, str], rows: list[tuple[str, str]]) -> None`
    - `INDEX_ROWS: dict[int, list[tuple[str, str]]]`: per vintage, a few real
      six-digit leaves of that vintage with any nonempty entries, plus two
      cross-reference rows, one of them `('******', 'Wholesale -- see type of product ')`
      with the trailing space
    - `fixture_index_registry(directory: Path, rows: dict[int, list[tuple[str, str]]] = INDEX_ROWS) -> dict[str, IndexReference]`.
      It writes `naics/<vintage>_fixture_index.xlsx` workbooks with the official sheet
      names and headers. It returns a registry with their real sizes and SHA-256,
      URLs `https://fixture.test/naics/<name>` and counts that match `rows`.

**Parser rules.** `parse_index` applies them in this order:
1. The workbook has exactly one sheet, named `reference.sheet`, with exactly two columns.
2. Row 1, stripped, equals `reference.header`. Otherwise it raises
   `'ambiguous or unexpected index header'`.
3. In the body, `code` is the stripped cell and `entry` is the delivered cell, unchanged.
4. It fails on a null or blank code, on a null entry, or when
   `normalize_key(entry) == ''`. It fails on a code that is neither in `leaves` nor
   exactly `CROSS_REFERENCE`. It fails when the body row count differs from
   `expected_rows` or the `******` count differs from `expected_cross_references`.
5. It keeps every row in file order, with no deduplication.

**Acquisition and import rules.** Mirror `code_references.preflight`,
`publish_original`, `acquire` and `import_reference`, with these differences:
- Preflight every kind before any download. A symlink or a `.part` sibling fails. A
  present but unrecorded file fails (`ita_references.existing_reference` raises). A
  present recorded file passes `manifest.entry_for` and the pin check, then is skipped.
- Download into `tempfile.TemporaryDirectory()` with
  `with make_client() as client: download(client, reference.url, file)`.
- Before publishing, check size and SHA-256 against the registry pin, then
  `parse_index` with `leaves_by_vintage(ita_references.read_titles(data_dir))`.
- Publish to `raw/references/<relative>` through an exclusive `.part`, a hash recheck,
  `os.link` and `manifest.append_entries`, with a `finally` that unlinks the `.part`.
  Acquired entries use client `httpx`. Imported entries use client `manual-import` with
  proxies `('retrieved_at',)`. `source_url` is the registry URL.
- On import, already-recorded identical bytes return the path. Different bytes fail.
- `read_index` calls `manifest.entry_for`, the pin check and `parse_index` for each kind.

- [ ] **Step 1: Add the `sheet` keyword to `tests/code_fixtures.py::write_xlsx`**

The default `'Fixture'` keeps every existing caller's output byte-identical.

- [ ] **Step 2: Write the failing tests**

- `test_parse_keeps_cross_references_and_delivered_entries`: three leaf rows (one entry
  with a trailing space) and two `******` rows give five rows in `INDEX_SCHEMA`. Code
  `******` is kept, and the trailing space survives in `entry`.
- `test_parse_refuses`, parametrized: wrong sheet name; an extra sheet; three columns;
  header `NAICS 22`; blank code; entry `'   '`; non-leaf `111111`; five-digit `11111`;
  row count off by one; cross-reference count off by one. Each raises `ValueError`.
- `test_entries_sharing_text_across_codes_are_kept`: one entry under two codes gives
  two rows.
- `test_production_registry_records_inspected_originals`: `REGISTRY` equals the
  registered-facts table field by field.
- `test_acquire_downloads_missing_and_records_once`: seed the structure titles, then
  serve the fixture workbooks through `httpx.MockTransport`. Patch
  `ita_index_references.make_client` with
  `partial(osha_benchmark_download.make_client, transport=...)` and build each response
  with `stream=httpx.ByteStream(...)`. The second `acquire` sends no request. The
  manifest gains three `httpx` entries.
- `test_acquire_refuses_unrecorded_present_file`: no request is sent.
- `test_acquire_refuses_changed_bytes`: served bytes differ from the pin. It raises
  `ValueError`, and nothing is published or recorded.
- `test_import_records_proxy_time`: `manual-import` with proxies `('retrieved_at',)`.
  Identical re-import returns the path. Different bytes fail.
- `test_read_index_verifies_manifest_and_pin`: a published file changed by one byte
  fails `read_index`.

- [ ] **Step 3: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_ita_index_references.py -q`
Expected: FAIL, module not found.

- [ ] **Step 4: Implement `ita_index_references.py` and the fixture helpers**

- [ ] **Step 5: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_ita_index_references.py tests/test_code_build.py tests/test_codes_cli.py -q`
Expected: all pass, and existing `write_xlsx` callers are unchanged.

- [ ] **Step 6: Apply the D2 amendment to `specs/ita-establishment-targets.md`**

Leave the status line untouched. In "Parsing", replace:

```
- A code that is not a six-digit leaf of that vintage's official structure.
- An entry count that differs from the registered expected count.
```

with:

```
- A code that is neither a six-digit leaf of that vintage's official structure
  nor the exact cross-reference marker `******`.
- An entry count or a cross-reference count that differs from its registered
  expected count.
```

Replace:

```
The leaf rule above is an assumption about the official files that this
design could not inspect. The plan's acquisition task inspects the actual
originals first. If they contain rows with non-leaf, special or
other-vintage codes, the plan stops and asks the owner. It neither refuses
the official file nor drops those rows silently.
```

with:

```
Each official index file ends with 25 cross-reference rows whose code is
`******`, such as "Wholesale -- see type of product". The parser keeps them
with the delivered code and counts them. Their entries are official index
entries, so they take part in the copied-index flags. Every other row is a
six-digit leaf of its own vintage. *(owner, plan 11, 2026-11-14)*
```

- [ ] **Step 7: Commit**

Files: the module, `tests/ita_establishment_fixtures.py`, `tests/code_fixtures.py`,
the test file and the spec. Message: `feat: register and parse official NAICS index originals`.

---

### Task 3: Codes-only input selection

**Files:**
- Create: `src/embedding_data/ita_establishment_inputs.py`
- Test: `tests/test_ita_establishment_inputs.py`

**Interfaces:**
- Consumes: `target_inputs.CODE_SCHEMAS`, `require_source_parity`, `validate_native`;
  `code_build.check_source`, `SCHEMA_VERSION`; `target_io.relative_file`,
  `verify_inventory`, `verify_raw`, `file_record`; `manifest.sha256_file`.
- Produces:
  - `@dataclass(frozen=True) class SelectedCodes: data_dir: Path; codes_run: str; codes_outputs_sha256: str; directory: Path; tables: dict[str, Path]; summary: Path; provenance: dict`,
    with `verify(self) -> None`. `verify` reselects and raises
    `ValueError('selected codes inputs changed')` on any difference.
  - `select_codes(data_dir: Path, codes_run: str, *, codes_outputs_sha256: str) -> SelectedCodes`
  - `tables` maps every `CODE_SCHEMAS` name to its Parquet path.
  - `provenance` keys:
    - `codes`: `run_id`, `outputs_sha256`, `outputs` (the parsed `outputs.json`)
    - `raw`: verified bundle citations plus `check_source` citations, sorted by path.
      A path cited twice with different content raises `ValueError`.
    - `source_parquet` and `canonical`: `{'path': <data-relative>, **target_io.file_record(...)}`
    - `source_years`: `[2016, …, 2025]`
    - `source_rows`: an int

**Selection steps.** Each failure raises a `ValueError` with a fixed message.
1. Check the run-ID regex and the pin regex `[0-9a-f]{64}`. The directory is
   `derived/codes/<run>` through `target_io.relative_file`.
2. Require `manifest.sha256_file(outputs.json) == pin`.
3. The file set is exactly the `CODE_SCHEMAS` Parquets plus `inputs.json`,
   `report.json` and `outputs.json`. Run `target_io.verify_inventory`.
4. `inputs` and `report` have `schema_version == code_build.SCHEMA_VERSION`, and
   `inputs['run_id']` equals the run. The report's table set, each table's ordered
   schema and its row count match `CODE_SCHEMAS` and the files. Reimplement these
   checks, because `target_inputs._bundle` is private and needs a geography run.
5. Run `target_io.verify_raw(data_dir, inputs['raw'])`.
6. The source path is `derived/osha/ita_300a_summary.parquet`. Its current SHA-256
   and size equal `inputs['source_parquet']`.
7. Run `code_build.check_source(data_dir, work)` in a `tempfile.TemporaryDirectory()`.
   Each returned citation equals the bundle citation at its path. Source years are
   exactly 2016–2025.
8. Run `target_inputs.require_source_parity(summary, canonical)`.
9. Run `target_inputs.validate_native(pl.scan_parquet(canonical), pl.read_parquet(naics_nodes))`.
10. Run steps 1–9 twice. Unequal snapshots raise
    `'selected codes inputs changed during validation'`.

- [ ] **Step 1: Write the failing tests**

Use `target_fixtures.seed_inputs(tmp_path)`. It builds a toy Stage 4 bundle named
`fixture_codes`, which suffices because the selector reads no titles.

- `test_selects_pinned_codes_bundle`: `tables` keys equal `CODE_SCHEMAS`.
  `provenance['source_rows'] == 21`. Raw paths include every summary release.
- `test_needs_no_geography`: delete `derived/geography/fixture_geography/` and selection
  still succeeds.
- `test_selected_defects_are_refused`, parametrized over the `corrupt_selected` defects
  `detached_hash`, `file_hash`, `size`, `missing_file`, `extra_file`, `schema`,
  `row_count`, `raw_bytes`, `source_hash`, `source_order`, `canonical_order`,
  `native_flags` and `native_node_level`. After corruption, call `select_codes` with
  `selected.provenance['codes']['outputs_sha256']`, which `corrupt_selected` repins.
  Expect `ValueError` or `FileNotFoundError`.
- `test_unsafe_run_id_and_pin_refused`: `'../x'` and a 63-character pin.
- `test_verify_detects_change`: after selection, change `report.json` and repin, then
  `verify()` raises.

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_ita_establishment_inputs.py -q`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement `ita_establishment_inputs.py`**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_ita_establishment_inputs.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: select pinned Stage 4 codes for Stage 10 without geography`.

---

### Task 4: Keyed records, copied-text flags and V1 counts

**Files:**
- Create: `src/embedding_data/ita_establishment_records.py`
- Modify: `tests/ita_establishment_fixtures.py` (frame builders)
- Modify: `specs/embedding-evaluation-data-spec.md` (R2.6 amendment)
- Test: `tests/test_ita_establishment_records.py`

**Interfaces:**
- Consumes: `ita_verification.with_keys`, `normalize_key`; `ita_summary.COLUMNS`;
  `target_inputs.CANONICAL_SCHEMA`; Task 2 `INDEX_SCHEMA`; Task 1 `V1_COLUMNS`.
- Produces:
  - `SOURCE_COLUMNS = tuple(ita_summary.COLUMNS)`, the 24 Stage 2 columns
  - `COPY_FLAGS = ('flag_copied_title_any', 'flag_copied_title_native', 'flag_copied_index_any', 'flag_copied_index_native')`
  - `text_keys(titles: pl.DataFrame, index: pl.DataFrame) -> pl.DataFrame`. Schema is
    `{'kind': String ('title' | 'index'), 'vintage': Int64, 'key': String}`, unique and
    sorted. An empty key raises `ValueError`.
  - `keyed_records(canonical: pl.LazyFrame, keys: pl.DataFrame) -> pl.LazyFrame`.
    Columns are `source_row: UInt64` (0-based physical position) first, then the 38
    canonical columns in order, then the columns `with_keys` appends in its order,
    then `COPY_FLAGS`.
  - `v1_counts(records: pl.LazyFrame) -> pl.DataFrame`: `year_filing_for` plus
    `V1_COLUMNS`, all Int64, sorted by year
  - `index_counts(records: pl.LazyFrame) -> pl.DataFrame`: by year, Int64 columns
    `n_copied_index_any`, `n_copied_index_native`, `n_copied_title_and_index_any`,
    `n_copied_title_only_any`, `n_copied_index_only_any`
  - `tests/ita_establishment_fixtures.py`:
    - `canonical_frame(rows: list[dict]) -> pl.LazyFrame` returns every
      `CANONICAL_SCHEMA` column in order and type. Defaults: year 2023, a usable
      9-digit EIN, a complete address, `native('332312')`, all flags false.
    - `native(code: str) -> dict`, `crosswalked(code: str, year: int | None, candidates: list[str]) -> dict`
      and `unresolved(code: str | None, year: int | None) -> dict` return mapping
      fields consistent with `ita_naics_mapping.build_lookup`.
    - `naics_reference(codes: list[str]) -> tuple[pl.DataFrame, pl.DataFrame]`
      returns `(nodes, code_paths)` from `classification_tables.naics_tables` for the
      codes and all their ancestors, using sector ranges `31-33`, `44-45` and `48-49`.

**Rules.**
- `keyed_records` applies `with_keys` to the row-indexed canonical frame. `with_keys`
  reads only the eight text fields and keeps every other column. Its keys therefore
  equal those from the 24 summary columns alone (spec "Record keys").
- An `_any` flag is true when `description_key` is a key of that kind in any vintage.
  A `_native` flag is null when `naics_year` is null. Otherwise it is true when
  `(naics_year, description_key)` is a key of that kind. An empty key never matches.
- V1 counts copy `ita_verification.description_report` exactly:

| column | count of rows (per year) where |
| --- | --- |
| `n_rows` | all |
| `n_empty`, `n_placeholder` | `flag_empty`, `flag_placeholder` |
| `n_copied_any` | `flag_copied_title_any` |
| `n_native_title_match` | `flag_copied_title_native` is true |
| `n_vintage_unknown` | `naics_year` is null |
| `n_employer_unknown` | `employer_key` is null |
| `n_employer_company` | `employer_key` starts with `company:` |
| `n_ein_padded`, `n_mojibake` | `flag_ein_padded`, `flag_suspected_mojibake` |
| `n_repeat_rows` | sum of group sizes above 1 for groups `(year, employer_key, description_key)` with known employer and nonempty key |
| `n_repeat_excess` | sum of `size − 1` over the same groups, 0 when there is none |

- [ ] **Step 1: Write the failing tests**

- `test_keys_match_stage3_semantics`: every `with_keys` column equals the one computed
  on `frame.select(SOURCE_COLUMNS)`. `source_row` is `0..n-1` as UInt64.
- `test_copy_flags`, one row each:
  - own-vintage title: any T, native T
  - another vintage's title: any T, native F
  - title with null `naics_year`: any T, native null
  - six-digit index entry
  - cross-reference entry
  - empty description: both `_any` F
  - placeholder `N/A`
- `test_index_whitespace_still_flags_copy` (Review Focus 5): the index entry is
  `'Wholesale -- see type of product '` and the description is
  `'  wholesale -- SEE type of product'`, so `flag_copied_index_any` is true.
- `test_v1_counts_equal_stage3_description_report`: two years with repeats, company
  fallback, a padded EIN, mojibake (`Ã`), an unknown vintage and an empty description.
  `v1_counts` equals `description_report(frame.select(SOURCE_COLUMNS), titles)` on
  `V1_COLUMNS`, both cast to Int64.
- `test_index_counts_partition_overlap`: title only, index only, and both.
- `test_text_keys_refuse_empty_key`.

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_ita_establishment_records.py -q`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement the module and the frame builders**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_ita_establishment_records.py -q`
Expected: all pass.

- [ ] **Step 5: Apply the R2.6 amendment to `specs/embedding-evaluation-data-spec.md`**

Replace:

```
`not specified`, `-`, `--`, and `.` are flagged. Identity to any official
2012, 2017 or 2022 NAICS title at levels 2–6 is flagged as copied text;
native-vintage identity is also reported, with unknown vintage kept
unknown. Suspected mojibake is flagged rather than automatically repaired.
```

with:

```
`not specified`, `-`, `--`, and `.` are flagged. Identity to any official
2012, 2017 or 2022 NAICS title at levels 2–6, or to any official 2012, 2017
or 2022 NAICS index entry, is flagged as copied text. Titles and index
entries are flagged separately. Native-vintage identity is also reported,
with unknown vintage kept unknown. *(owner, Stage 10 design, 2026-11-13;
[stage spec](ita-establishment-targets.md))* Suspected mojibake is flagged
rather than automatically repaired.
```

- [ ] **Step 6: Commit**

Message: `feat: key ITA records and flag copied title and index text`.

---

### Task 5: Text–code pair tables

**Files:**
- Create: `src/embedding_data/ita_text_pairs.py`
- Test: `tests/test_ita_text_pairs.py`

**Interfaces:**
- Consumes: Task 4 `keyed_records` output; `ita_area_mix.eligible_industry`;
  `classification_tables.PATH_SCHEMA`; Stage 4 `naics_nodes` and `code_paths` frames.
- Produces:
  - `PAIRS_VERSION = 'ita-text-pairs-v1'`
  - `PAIR_SCHEMA`, ordered as the spec's `ita_text_pairs.parquet` table:
    `pair_id` String, `pair_kind` String, `employer_key` String, `employer_basis` String,
    `description_key` String, `original_strings` List(String), `representative_string`
    String, `n_records` UInt64, `n_headline_records` UInt64, `first_year` Int64,
    `last_year` Int64, `n_years` UInt64, then the Boolean flags `flag_headline`,
    `flag_headline_codes_conflict`, `flag_empty`, `flag_placeholder`,
    `flag_copied_title_any`, `flag_copied_index_any`, `flag_suspected_mojibake`,
    `flag_employer_unknown`, `flag_employer_company_fallback`, then
    `n_records_ein_padded` UInt64
  - `PAIR_CODE_SCHEMA`, ordered as the spec's `ita_text_pair_codes.parquet` table:
    `pair_id`, `naics_code` String, `naics_year` Int64, `naics_mapping_status`,
    `naics_2022_candidates` List(String), `naics_2022_candidate_node_ids` List(String),
    `naics_2022_node_id`, `naics_deepest_common_node_id`, `flag_naics_crosswalked`,
    `flag_naics_ambiguous`, `flag_naics_unresolved`, `flag_headline_basis`,
    `flag_copied_title_native`, `flag_copied_index_native`, `n_records` UInt64,
    `n_records_year_from_dictionary` UInt64, `years` List(Int64)
  - `MEMBER_SCHEMA = {'source_row': pl.UInt64, 'pair_id': pl.String}`; `PATH_SCHEMA = classification_tables.PATH_SCHEMA`
  - `pair_id(kind: str, fields: tuple[str, ...]) -> str`
  - `@dataclass(frozen=True) class TextPairs: pairs: pl.LazyFrame; pair_codes: pl.LazyFrame; members: pl.LazyFrame; paths: pl.LazyFrame; report: dict`
  - `require_single_mapping_state(records: pl.LazyFrame) -> None`
  - `build_pairs(records: pl.LazyFrame, nodes: pl.DataFrame, code_paths: pl.DataFrame) -> TextPairs`
  - `validate_pairs(result: TextPairs, records: pl.LazyFrame, code_paths: pl.DataFrame) -> None`

**Rules the spec leaves open:**
- **Pair ID.** `pair_id` is the SHA-256 hex digest of the parts
  `[b'ita-text-pairs-v1', kind, *fields]`, each encoded as UTF-8 and prefixed by its
  byte length as 8 big-endian bytes. Employer fields are
  `(employer_key, description_key)`. Unknown-employer fields are `(str(source_row),)`.
  Compute it once per pair, not per record.
- **Originals.** `original_strings` holds the distinct `industry_description` values.
  A null is kept as one element. Sort with nulls first, then by Polars String order,
  which is code-point order.
- **Representative.** `representative_string` is the most frequent original, with null
  counted as a value. Ties go to the first in `original_strings` order. It is null only
  when that original is null, and such a pair is always `flag_empty`.
- **Conflict flag.** `flag_headline_codes_conflict` is `flag_headline` and more than one
  distinct `naics_2022_node_id` among eligible records. It is false otherwise.
- **Candidate nodes.** Map each candidate code to the `nodes` row with vintage 2022,
  level `national_industry` and that code. A missing node raises `ValueError`.
- **Headline basis.** `flag_headline_basis` is `eligible_industry()` on the row's
  mapping fields. An eligible record outside 2023–2025 raises `ValueError`.
- **Dictionary counts.** `n_records_year_from_dictionary` counts
  `naics_year_from_dictionary` true. Null counts as false.
- **Mapping state.** `require_single_mapping_state` raises
  `'contradictory mapping states'` when one `(naics_code, naics_year)` key has more
  than one distinct tuple of `ita_naics_mapping.MAPPING_SCHEMA` values. `build_pairs`
  calls it first.
- **Paths.** `paths` holds the Stage 4 `code_paths` rows whose `node_id` is any
  candidate node ID or scalar node in `pair_codes`, sorted by `node_id`. A referenced
  node without a path raises `ValueError`.
- **Sort orders.** Pairs by `pair_id`. Pair codes by `pair_id`, `naics_code`,
  `naics_year`, with nulls first. Members by `source_row`.
- **Report keys.**
  - `n_pairs`, `n_records`
  - `records_by_year_status_basis`: rows of `year_filing_for`, `naics_mapping_status`,
    `flag_headline_basis`, `n`
  - `pairs_by_kind_headline_text`: rows of `pair_kind`, `flag_headline`, `text_state`
    (`empty` | `placeholder` | `text`), `n`
  - `headline_pairs_by_node_count`: rows of `n_headline_nodes`, `n`
  - `headline_pair_record_distribution`: `count`, `min`, `p25`, `median`, `p75`,
    `p95` and `max` of `n_records` over headline pairs (the V9 handoff)

**Validator checks.** Each failure raises `ValueError`.
- Ordered schemas are exact and `pair_id` is unique.
- Members hold each `source_row` `0..N−1` exactly once, where N is the record count.
- Every member `pair_id` exists. Each pair's member count equals its `n_records`, which
  equals the sum of its pair-code `n_records`. The sum of `n_records` is N.
- Each pair has at least one pair-code row, and `(pair_id, naics_code, naics_year)` is
  unique.
- Headline invariants hold, with `n_headline_records` equal to the basis rows'
  `n_records`. The conflict flag is true exactly when a headline pair has more than one
  distinct basis node.
- Unknown-employer pairs have `n_records == 1`, a null `employer_key` and
  `flag_employer_unknown`.
- Path rows equal the Stage 4 rows, and the referenced node set equals the path set.

- [ ] **Step 1: Write the failing tests**

- `test_pair_id_encoding`:
  - `pair_id('employer', ('ein:123456789', 'steel mill')) == '7a0f1cef9cf5bc5d79af3a2993a46c15767dd0f3d208a8233fca9a07aac0d6f1'`
  - `pair_id('unknown_employer', ('17',)) == 'ac9816baa66533d9e4744c9321d083fae0633e0c70c6735c2a0af22d73064587'`
- `test_every_record_in_exactly_one_pair`.
- `test_unknown_employers_never_group`: two blank-EIN, blank-company rows with one
  description give two pairs.
- `test_variant_spellings_share_one_pair` (Review Focus 1): one EIN with
  `'Steel Mill'`, `'steel  mill'`, `'STEEL MILL'` and `'Ｓｔｅｅｌ Mill'` gives one
  pair. `original_strings` holds all four in code-point order. `n_records == 4`, and
  the representative follows the tie rule.
- `test_headline_rule`:
  - native 2023 plus crosswalked 2019 under one pair: headline, and the crosswalked
    code row has `flag_headline_basis` false
  - empty, placeholder and unknown-employer pairs with native codes: not headline
  - company-fallback pair: headline, with `flag_employer_company_fallback`
- `test_headline_code_conflict_keeps_both_nodes`: 238220 (2023) and 238210 (2024) in
  one pair.
- `test_null_description_pair`: `original_strings == [None]`, representative null,
  `flag_empty`.
- `test_contradictory_mapping_state_fails`.
- `test_paths_cover_candidates_and_scalars`: an ambiguous crosswalked row with two
  candidates yields both paths. An unresolved row with empty candidates yields none.
- `test_validator_rejects_row_loss`: a dropped member row raises `ValueError`.

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_ita_text_pairs.py -q`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement `ita_text_pairs.py`**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_ita_text_pairs.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: build deduplicated ITA text-code pair tables`.

---

### Task 6: Co-ownership target

**Files:**
- Create: `src/embedding_data/ita_co_ownership.py`
- Test: `tests/test_ita_co_ownership.py`

**Interfaces:**
- Consumes: Task 4 records; `eligible_industry`; `TARGET_SCHEMA`, `TARGET_KEY_COLUMNS`,
  `validate_targets`.
- Produces:
  - `CO_OWNERSHIP_VERSION = 'ita-co-ownership-v1'`, `YEARS = (2023, 2024, 2025)`,
    `SAMPLE_SET = 'ita_300a_2023_2025'`, `TOLERANCE = 1e-12`
  - `UNIVERSE`: the spec's universe statement, verbatim, as one string
  - `METADATA = dict(source='osha_ita', family='co_ownership', unit_a_type='naics_national_industry', unit_b_type='naics_national_industry', measure='employer_share', se_method='none', sample_set=SAMPLE_SET, vintage='naics=2022', universe=UNIVERSE)`
  - `SIZE_LABEL = 'size_gate_pending'`, `PADDED_LABEL = 'numerator:ein_padded_sensitivity:true'`
  - `MARGINAL_SCHEMA = {'node_id': String, 'n_employers': UInt64, 'n_multi_industry_employers': UInt64, 'n_records': UInt64, 'n_employers_including_padded': UInt64, 'n_employers_partial': UInt64}`
  - `SUPPORT_SCHEMA = {'unit_a': String, 'unit_b': String, 'j_employers': UInt64, 'j_2023': UInt64, 'j_2024': UInt64, 'j_2025': UInt64, 'j_including_padded': UInt64}`
  - `EXCLUSIONS = ('year_outside_window', 'industry_ineligible', 'ein_unusable', 'ein_padded')`
  - `RECORD_FLAGS = ('flag_employment', 'flag_hours_per_employee', 'flag_below_filing_size', 'flag_naics_year_unknown', 'flag_outside_filing_industry', 'flag_outside_filing_rule', 'flag_filing_rule_label_bridged', 'flag_filing_reference_ambiguous', 'naics_year_from_dictionary')`
  - `@dataclass(frozen=True) class CoOwnership: targets: pl.LazyFrame; marginals: pl.LazyFrame; support: pl.LazyFrame; report: dict`
  - `estimate(records: pl.LazyFrame) -> CoOwnership`
  - `validate_co_ownership(result: CoOwnership, nodes: pl.DataFrame) -> None`

**Rules.** The estimand is spec "Eligibility and estimand". These are the choices it
leaves open:
- **Exclusion reasons.** Each record gets the first reason in `EXCLUSIONS` order that
  applies, or `eligible`. The reasons are: year not in `YEARS`; not
  `eligible_industry()`; `ein_key` null; `flag_ein_padded`.
- **Employer identity.** An employer is its `ein_key`. The padded-admitted population
  is the eligible records plus the `ein_padded` exclusions.
- **Multi-industry.** `n_multi_industry_employers(a)` counts EINs with `a ∈ S(e,t)` and
  `|S(e,t)| ≥ 2` for some year t.
- **Record count.** `n_records(a)` counts eligible records in `a`, with multiplicity.
- **Partial sets.** `n_employers_partial(a)` counts EINs in `n(a)` with some year t
  where `a ∈ S(e,t)` and a record of the same `ein_key`, not padded, in year t has the
  reason `industry_ineligible`.
- **Marginal rows.** There is one marginal row per node with `n(a) ≥ 1`, sorted by
  `node_id`. Nodes reached only through padded EINs get no row. The report counts them.
- **Target rows.** A target row has `value = J/n(a)`, `n_unweighted = J`,
  `n_weighted = float(J)` and a null `se`. Its `flags` are the sorted unique list of
  `size_gate_pending`, plus `PADDED_LABEL` when `j_including_padded != J`. Rows are
  sorted by `TARGET_KEY_COLUMNS`.
- **Support rows.** There is one support row per target cell, sorted by `unit_a`,
  `unit_b`.
- **Report keys.** `N`, `N_including_padded`, `partition_by_year` (every year with
  every reason and `eligible`), `eligible_flags_by_year` (`n_true` and `n_null` per
  `RECORD_FLAGS` entry), `n_cells`, `n_cells_padded_label`, `n_sensitivity_only_cells`
  (ordered pairs with padded J ≥ 1 and J = 0), `n_padded_only_nodes`,
  `cell_count_distribution` and `marginal_employer_distribution`.

**Validator checks**, beyond `validate_targets`:
- Ordered companion schemas are exact, and every row matches `METADATA`.
- Both units are 2022 `national_industry` node IDs from `nodes`, and
  `unit_a != unit_b`.
- Each `(b,a)` mirror exists with equal `n_unweighted`. `n_unweighted ≥ 1`,
  `n_weighted == float(n_unweighted)` and `se` is null.
- `|value − J/n(a)| ≤ TOLERANCE`, using the marginals, and
  `J ≤ min(n(a), n(b))`.
- Support rows match targets 1:1 with `j_employers == n_unweighted`, and
  `max(j_t) ≤ J ≤ Σ j_t`. Also `j_including_padded ≥ J`, and `PADDED_LABEL` is in
  `flags` exactly when they differ. `size_gate_pending` is always in `flags`.
- Marginal `node_id` values are unique. `n_employers ≥ 1`. The multi, partial and
  padded counts obey their bounds against `n_employers`.
  `n_multi_industry_employers ≥ max_b J(a,b)`, and it is 0 exactly when `a` has no
  target row.

- [ ] **Step 1: Write the failing tests**

- `test_same_year_rule`: an EIN with 238220 in 2023 and 722511 in 2024 forms no cell.
  The same pair within 2025 forms one.
- `test_each_ein_counts_once`: three records in 238220 and two in 722511 across years
  for one EIN give `J == 1`, `n(238220) == 1` and marginal `n_records == 3`.
- `test_mirror_rows_and_values`: e1 has `{a,b}`, e2 has `{a,b}` and e3 has `{a,c}` in
  one year. Then `(a,b)` is 2/3, `(b,a)` is 1, `(a,c)` is 1/3 and `(c,a)` is 1. There
  is no diagonal cell.
- `test_ein_spellings_count_once` (Review Focus 2):
  - `'12-3456789'` in a and `'123456789'` in b, same year: `J(a,b) == 1`.
  - `'023456789'` in a and padded `'23456789'` in b, same year: `j_including_padded(a,b) == 2`
    and `PADDED_LABEL` on both directions.
  - `N == 2`, `n(a) == 2`, `n(b) == 1`.
- `test_partial_industry_sets`: an ineligible record in the same year counts. One in
  another year does not.
- `test_exclusion_partition`: one record per reason. Counts by year sum to the rows.
- `test_validator_rejects_broken_mirror` and `test_validator_rejects_value_mismatch`.
- `test_targets_pass_shared_writer`: `target_contract.write_targets` into `tmp_path`
  succeeds.

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_ita_co_ownership.py -q`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement `ita_co_ownership.py`**

Deduplicate `(ein_key, year, node)` before the self-join on `(ein_key, year)`, so record
multiplicity never enters J.

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_ita_co_ownership.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: estimate directional ITA co-ownership shares`.

---

### Task 7: Establishment links

**Files:**
- Create: `src/embedding_data/ita_establishment_links.py`
- Test: `tests/test_ita_establishment_links.py`

**Interfaces:**
- Consumes: Task 4 records and `SOURCE_COLUMNS`; Task 1 `YEAR_PAIRS`, `V2_COLUMNS`;
  Task 5 `build_pairs` (one test only).
- Produces:
  - `LINKS_VERSION = 'ita-establishment-links-v1'`
  - `STATUSES = ('missing_id', 'ambiguous_id', 'conflict', 'confirmed_same_id', 'confirmed_changed_id', 'weaker_same_id', 'no_candidate')`, in precedence order
  - `REASONS = ('reason_later_id_ambiguous', 'reason_ein_unknown', 'reason_ein_reconstructed', 'reason_ein_conflict', 'reason_address_incomplete', 'reason_address_conflict')`
  - `LINK_SCHEMA`, ordered: `base_year` Int64, `later_year` Int64, `base_row` UInt64,
    `base_rows` List(UInt64), `later_row` UInt64, `base_establishment_id` Int64,
    `later_establishment_id` Int64, `status` String, the six `REASONS` (Boolean),
    `flag_id_reappears_elsewhere` Boolean
  - `distinct_records(records: pl.LazyFrame, year: int) -> pl.LazyFrame`: one row per
    distinct record, with `base_row`, `source_rows`, the key columns, `id_unique` and
    `tuple_eligible`
  - `@dataclass(frozen=True) class Links: links: pl.LazyFrame; v2: pl.DataFrame; report: dict`.
    `v2` has `base_year`, `later_year` and `V2_COLUMNS`, all Int64, in `YEAR_PAIRS`
    order. It holds pre-conflict counts, as `check_reproduction` expects.
  - `build_links(records: pl.LazyFrame) -> Links`
  - `validate_links(links: pl.LazyFrame, records: pl.LazyFrame) -> None`

**Definitions** for each year pair s→t:
- **Distinct record.** The source rows of one year that are equal on all 24
  `SOURCE_COLUMNS`, with nulls equal. `source_rows` is sorted, and `base_row` is its
  first element.
- **`id_unique`.** The ID is non-null and no other distinct record of the year has it.
- **`tuple_eligible`.** `id_unique`, `ein_key` non-null, not `flag_ein_padded`,
  `address_key` non-null, `name_key != ''`, and the tuple
  `(ein_key, name_key, address_key)` occurs on exactly one distinct record of the year.
  The tuple count includes null-ID, competing-ID and padded records, because V2 computes
  its window before the unique-ID filter.
- **Same-ID candidate.** The base ID is non-null and present in t. The candidate is
  later-unique when that ID is `id_unique` in t.
- **Confirmed same-ID (pre-conflict).** The base is `id_unique` and the candidate is
  later-unique. Both `ein_key` values are non-null and equal, and neither side is
  padded. The base `address_key` is non-null and equals the later one.
- **Confirmed changed-ID (pre-conflict).** Base and later are both `tuple_eligible`,
  their tuples are equal and their IDs differ.
- **Conflict.** The base has both confirmed kinds, which always point to different
  records. Or its confirmed successor is also the confirmed successor of another base
  record.
- **Status.** The first status in `STATUSES` order that applies.
- **`later_row` and `later_establishment_id`.** The confirmed successor's for
  `confirmed_*`. The unique same-ID record's for `weaker_same_id` with a later-unique
  candidate. Null otherwise.
- **Reasons.** Reasons are false on every status except `weaker_same_id`. When the later
  ID is ambiguous, only `reason_later_id_ambiguous` is true. Otherwise:
  `reason_ein_unknown` when either `ein_key` is null; `reason_ein_reconstructed` when
  either side is padded; `reason_ein_conflict` when both are non-null and differ;
  `reason_address_incomplete` when either `address_key` is null;
  `reason_address_conflict` when both are non-null and differ.
- **`flag_id_reappears_elsewhere`.** The status is `confirmed_changed_id` and the base
  ID is present in t.

**V2 counts.** For each pair they must equal `ita_verification.link_report` on the same
24-column frame.

| V2 column | Stage 10 computation |
| --- | --- |
| `n_cohort_ids` | distinct non-null IDs in s |
| `n_raw_reappeared` | of those, also present in t |
| `n_unique_cohort_ids` | base distinct records with `id_unique` |
| `n_reappeared` | of those, ID `id_unique` in t |
| `n_same_ein_address` | pre-conflict confirmed same-ID |
| `n_same_ein_address_including_padded` | `n_reappeared` and `ein_key`s non-null and equal and base address non-null and equal (padding allowed) |
| `n_same_raw_ein_address` | the previous, and raw `ein` equal |
| `n_reappeared_ein_unknown` | `n_reappeared` and either `ein_key` null |
| `n_reappeared_ein_conflict` | `n_reappeared` and both non-null and different |
| `n_reappeared_address_conflict` | `n_reappeared` and (base address null, or both non-null and different). A null later address with a non-null base is not counted, which is V2's null logic |
| `n_base_missing_id_rows`, `n_later_missing_id_rows` | source rows (not distinct) with a null ID in s and in t |
| `n_unique_address_matches` | base `tuple_eligible` records whose tuple equals that of a later `tuple_eligible` record |
| `n_address_matches_different_id` | pre-conflict confirmed changed-ID |

**Report, per pair.**
- The V2 counts, the status counts and `n_base_records`.
- `n_conflict_with_same_link`, `n_conflict_with_changed_link` and
  `n_conflict_both_links`.
- Two identities, which fail the build when they do not hold:
  - `n_same_ein_address − confirmed_same_id == n_conflict_with_same_link`
  - `n_address_matches_different_id − confirmed_changed_id == n_conflict_with_changed_link`
- The status counts sum to `n_base_records`.

**Validator checks.**
- The schema is exact. Keys are sorted and unique, and the year pairs are exactly
  `YEAR_PAIRS`.
- Each pair's `base_row` set equals that of `distinct_records(records, s)`.
  `base_rows` is sorted, with `base_row` first.
- Each `status` is in `STATUSES`.
- The reason, `later_row` and flag rules above hold. A null base ID holds exactly when
  the status is `missing_id`.

- [ ] **Step 1: Write the failing tests**

- `test_v2_counts_equal_stage3_link_report`: base 2023 and later 2024 hold exact
  duplicates, null IDs in both years, a competing ID in each year, a padded EIN, an
  unknown EIN and an EIN conflict. They also hold a base-null address with a later
  address, a base address with a later-null address, a changed-ID tuple, and a tuple
  collision caused by a null-ID record. Every `V2_COLUMNS` value equals
  `link_report(frame.select(SOURCE_COLUMNS), 2023, 2024)`.
- `test_status_precedence`: one base record per status, checking status, `later_row`
  and reasons.
- `test_conflict_two_successors` and `test_conflict_shared_successor`: both conflict
  shapes give `later_row` null and satisfy the report identities.
- `test_exact_duplicates_collapse_only_for_links` (Review Focus 3): two identical 2023
  rows give one link row with both source rows. `build_pairs` keeps `n_records == 2`
  and two member rows.
- `test_weaker_reasons`: an ambiguous later ID; an unknown EIN; address conflict
  together with reconstruction.
- `test_relocation_is_weaker_not_conflict`: same ID and EIN with a different address
  gives `weaker_same_id` with `reason_address_conflict`.
- `test_validator_rejects_missing_base_record`.

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_ita_establishment_links.py -q`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement `ita_establishment_links.py`**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_ita_establishment_links.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: link ITA establishments across filing years`.

---

### Task 8: Bundle build, verify and compare

**Files:**
- Create: `src/embedding_data/ita_establishment_bundle.py`
- Modify: `tests/ita_establishment_fixtures.py` (fixture chain)
- Test: `tests/test_ita_establishment_bundle.py`

**Interfaces:**
- Consumes: Tasks 1–7.
- Produces:
  - `TABLES = ('ita_establishment_links', 'ita_text_pairs', 'ita_text_pair_codes', 'ita_text_pair_members', 'naics_2022_paths', 'ita_co_ownership', 'co_ownership_marginals', 'co_ownership_support')`
  - `FILES = (*(name + '.parquet' for name in TABLES), 'inputs.json', 'report.json')`
  - `CONTRACTS = {'links': 'ita-establishment-links-v1', 'pairs': 'ita-text-pairs-v1', 'co_ownership': 'ita-co-ownership-v1', 'index': 'naics-index-v1', 'targets': 'targets-v1'}`
  - `SOFTWARE_FILES: tuple[str, ...]`: repo-relative `src/embedding_data/__init__.py`
    and every `embedding_data` module that importing this module loads, plus
    `pyproject.toml` and `uv.lock`
  - `freeze_software() -> dict`, shaped like `acs_target_inputs.freeze_target_software`:
    `files`, `python`, `python_full`, `implementation`, `dependencies`, `uv_lock_sha256`
  - `ordered_equal(first: pl.LazyFrame, second: pl.LazyFrame) -> dict` returns
    `{'schema_equal', 'values_equal', 'first_rows', 'second_rows'}`. It joins on a row
    index and uses `ne_missing`, as `ita_target_build._equal` does.
  - `run_directory(data_dir: Path, run_id: str) -> Path`: `derived/osha/establishment-targets/<run_id>`
  - `build(data_dir: Path, run_id: str, *, codes_run: str, codes_outputs_sha256: str, index_registry: dict = ita_index_references.REGISTRY, expectations: Expectations | None = None) -> dict`
    returns `{'run_id', 'directory', 'outputs_sha256'}`
  - `verify_bundle(directory: Path, data_dir: Path, *, expected_outputs_sha256: str) -> dict`
    returns `{'run_id', 'outputs_sha256', 'reproduction', 'rows'}`
  - `compare_runs(first: Path, second: Path) -> dict` returns
    `{'equal', 'tables', 'report_equal', 'trust_established': False}`
  - fixtures:
    - `golden_releases() -> dict[int, list[dict[str, str]]]`
    - `@dataclass class EstablishmentInputs: codes_run: str; codes_outputs_sha256: str; index_registry: dict; expectations: Expectations`
    - `seed_establishment_inputs(data_dir: Path, directory: Path) -> EstablishmentInputs`
    - `stage3_expectations(data_dir: Path) -> Expectations` with basis
      `fixture_stage3_recomputation`. It runs `ita_verification.description_report` and
      `link_report` over `YEAR_PAIRS` on the fixture summary with `read_titles`.

**Build sequence:**
1. `final, staging = target_io.stage(run_root, run_id, data_dir)`.
2. In `try`, with `scratch = staging / '.scratch'`:
   1. Run `select_codes`, `read_titles` and `read_index(..., registry=index_registry)`.
   2. Run `expectations_for(provenance['source_parquet'], expectations)`. For the
      adopted source, also require `index_registry == ita_index_references.REGISTRY`,
      or raise `'adopted source requires the production index registry'`.
   3. Build `text_keys`. Sink `keyed_records` to `scratch/records.parquet` and rescan it.
   4. Run `build_pairs` with `validate_pairs`, `build_links` with `validate_links`, and
      `estimate` with `validate_co_ownership`.
   5. Run `check_reproduction` with `v1_counts`, `links.v2` and the record count.
3. Write the tables in their defined orders: `write_targets` for `ita_co_ownership` and
   `sink_parquet` for the rest. Rescan each, rerun its validator on the serialized
   frames, and require `ordered_equal` against the in-memory result.
4. Remove `scratch` after `geography_references.safe_path`.
5. Write `inputs.json` with `target_io.write_json`. It holds:
   - `run_id`, `CONTRACTS`
   - `codes`: `run_id`, `outputs_sha256`, `outputs`
   - `source_parquet`, `canonical`
   - `raw`: the selected raw citations, the three title citations
     (`manifest.entry_for` on `ita_references.TITLE_FILES` paths) and the index
     citations, merged and sorted. A conflicting path fails.
   - `index_references`: `{kind: asdict(reference)}`
   - `expectations.to_json()`
   - `rules`: fixed short strings naming the headline, co-ownership and link rules
   - `software`: `freeze_software()`
   - `execution`: `commit`, `dirty`, `created_at`, as Stage 6 `_execution` does
6. Write `report.json` with:
   - `CONTRACTS` and the reproduction result
   - `v1_by_year`, `index_by_year`
   - the pairs, links and co-ownership reports
   - `tables`: `{name: {rows, columns, schema}}`
   - `limits`: the spec's "Methodological limits" bullets as strings
   - `universe`, and `size_gate: 'pending'`
   It holds no run ID, no time and no file hash, so replays compare equal.
7. Recheck before publication: `selected.verify()`, `freeze_software()` unchanged,
   `target_io.verify_raw(data_dir, inputs['raw'])` and the index pins.
8. `outputs.json` is `target_io.inventory(staging, list(FILES))`. The staging file set
   must equal `FILES` plus `outputs.json`, and `final` must be unoccupied. Then
   `staging.rename(final)`.
- `finally`: if `staging` exists, call `safe_path` and then `shutil.rmtree(staging)`.
  Nothing else under the run root is touched.

**Verify sequence:**
1. Refuse a name ending in `.part`. Require the 64-hex pin to equal
   `sha256(outputs.json)`, the exact file set and `verify_inventory`. All of this
   happens before any recomputation.
2. Read the JSON strictly, refusing duplicate keys and NaN. Each file's text must equal
   its canonical `write_json` form.
3. `inputs['run_id']` equals the directory name, and the contracts are equal. Reselect
   the recorded codes run and pin, and rebuild the registry from `index_references`.
   For an adopted source, recorded expectations must equal `ADOPTED` and recorded
   `index_references` must equal `REGISTRY`. Otherwise the expectations' basis must
   differ from `ADOPTED_BASIS`.
4. Recorded `software` must equal `freeze_software()`. Otherwise raise
   `'executing software differs from the build'`.
5. Recompute every product in a `tempfile.TemporaryDirectory()`, never under
   `data_dir`. Each table must pass `ordered_equal`. The report must equal the
   recorded report. The recomputed inputs, with the recorded `execution`, must equal
   the recorded inputs.

**Compare.** Both names must be published. Each must pass `verify_inventory` against its
own `outputs.json`. Run `ordered_equal` per table and an exact report comparison.
`equal` is the report result and every table result together. A comparison
establishes replay, not trust.

**Fixture releases.** `golden_releases` keeps `ita_fixtures.record(year)` for every year
2016–2025 and adds the rows below. Use only codes present in the 2012, 2017 and 2022
structures: 111110, 238210, 238220, 332312, 423110, 722511. Give every added row its own
`id`, `establishment_id`, `establishment_name` and `street_address` unless a case shares
them. Never use an all-same-digit EIN, which `ein_key` treats as unusable.

| Case | Rows |
| --- | --- |
| copied title | 2023: description `Soybean Farming`, code 111110 |
| copied index (cross-reference) | 2023: `Wholesale -- see type of product`, code 423110 |
| placeholder | 2023: `N/A` |
| unknown employer | 2023: `ein=''`, `company_name=''` |
| padded EIN in a labeled cell | 2023: EIN `23456789` with records in 238220 and 722511 |
| co-owned pair | 2023: EIN `123456789` with records in 238220 and 722511 |
| headline code conflict | EIN `345678912`, one description, 238220 in 2023 and 238210 in 2024 |
| mixed native and crosswalked | the default rows: 2019–2022 take dictionary 2012, 2023–2025 native 332312 |
| confirmed same-ID | ID 501, EIN `567891234`, `River Plant`, `5 River Rd` in 2023 and 2024 |
| changed-ID | the default rows (ID = year, same EIN, name and address) |
| shared-successor conflict | 2024: ID 701 `East Plant` and ID 702 `East Annex`, EIN `456789123`, `10 Oak St`. 2025: ID 701 `East Annex`, same EIN and address |

`seed_establishment_inputs` steps:
1. Run `write_release(data_dir, year, year_file(year, rows))` for each year, then
   `ita_summary.build_summary_table(data_dir)`.
2. `import_stage4_originals(data_dir, directory)` with all 13 kinds, then
   `code_build.build(data_dir, 'fixture_codes')`.
3. Import the `fixture_index_registry(directory)` originals through
   `ita_index_references.import_reference`.
4. `stage3_expectations(data_dir)`.

- [ ] **Step 1: Write the failing tests**

Use a module-scoped seeded root with one built run `first`.
- `test_build_publishes_complete_bundle`: the file set is `FILES` plus `outputs.json`.
  The returned pin equals `sha256(outputs.json)`. `ita_co_ownership` passes
  `validate_targets`. The basis is `fixture_stage3_recomputation`. Member rows equal
  the source rows.
- `test_verify_authenticates_pin_first`: with a wrong pin, a patched `select_codes`
  that raises `AssertionError` is never called, and the call raises `ValueError`.
- `test_verify_detects_table_tamper`: copy the bundle, change one value in one
  Parquet, rewrite `outputs.json` and pass its new pin. Recomputation fails.
- `test_occupied_names_refused`: an existing final and an existing `.part`.
- `test_leftover_staging_is_refused_and_untouched` (Review Focus 4): a leftover
  `<id>.part/` with one file. Building with that ID fails, and the file's bytes are
  unchanged. A fresh ID builds.
- `test_failure_cleans_only_own_staging`: `ita_co_ownership.estimate` patched to raise
  leaves neither `<id>.part` nor `<id>`. Other run directories are unchanged.
- `test_reproduction_mismatch_fails_build`: one V2 expectation + 1 raises `ValueError`
  and no final appears.
- `test_adopted_source_gate`: patch `ADOPTED_SOURCE` and `ADOPTED` to the fixture
  summary's identity and values, and `ita_index_references.REGISTRY` to the fixture
  registry. Explicit expectations are refused, and so is a registry other than
  `REGISTRY`. Without explicit expectations, the build succeeds with the basis
  `adopted_v1_v3_finding` and verifies. With `REGISTRY` restored, the same bundle's
  `verify` fails on its recorded `index_references`.
- `test_changed_software_refused_before_publication`: `freeze_software` returns a
  different value on its second call, and no final appears.
- `test_compare_runs_equal_and_unequal`: a `replay` build compares equal. A tampered
  copy does not.
- `test_software_files_cover_loaded_modules`: a subprocess imports the bundle module
  and lists the files of loaded modules named `embedding_data` or `embedding_data.*`.
  That set plus `pyproject.toml` and `uv.lock` equals `set(SOFTWARE_FILES)`. `dotenv`
  and `ipumspy` are not loaded.

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_ita_establishment_bundle.py -q`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement the bundle module and the fixture chain**

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run --locked pytest tests/test_ita_establishment_bundle.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Message: `feat: publish and verify immutable Stage 10 bundles`.

---

### Task 9: Command group and documentation

**Files:**
- Create: `src/embedding_data/ita_establishment_targets.py`
- Modify: `src/embedding_data/ita_establishment_bundle.py` (`SOFTWARE_FILES` gains the
  command module) and `tests/test_ita_establishment_bundle.py` (the coverage test
  imports the command module)
- Modify: `README.md`, `CLAUDE.md`
- Test: `tests/test_ita_establishment_cli.py`

**Interfaces:**
- Consumes: Task 2 `acquire`, `import_reference`; Task 8 `build`, `verify_bundle`,
  `compare_runs`, `run_directory`.
- Produces: Typer `app`, built with `pretty_exceptions_enable=False` and
  `pretty_exceptions_show_locals=False`, and runnable as
  `python -m embedding_data.ita_establishment_targets`. Every command requires
  `--data-dir`.

| Command | Calls | Success output |
| --- | --- | --- |
| `acquire-references` | `acquire(data_dir)` | JSON list of data-relative paths |
| `import-reference KIND FILE` | `import_reference(data_dir, kind, file)` | JSON path |
| `build RUN_ID --codes-run R --codes-outputs-sha256 P` | `build(data_dir, run_id, codes_run=R, codes_outputs_sha256=P)` | JSON result |
| `verify RUN_ID --outputs-sha256 P` | `verify_bundle(run_directory(data_dir, run_id), data_dir, expected_outputs_sha256=P)` | JSON result |
| `compare-runs FIRST SECOND` | `compare_runs(...)` on both run directories | JSON result, exit 1 when not equal |

- **Output.** Success prints one `json.dumps(..., sort_keys=True)` line.
- **Failure.** Any exception prints exactly
  `ITA establishment <command> failed: <reason>; run <run_id>; path <path>` to stderr
  and exits 2.
  - `<reason>`: `validation` for `ValueError`, `filesystem` for `OSError`, `network`
    for `httpx.HTTPError`, `unexpected` for anything else.
  - `<run_id>` is `-` for acquire and import.
  - `<path>` is the run directory or `raw/references/naics`.
- **No overrides.** The command group never passes `index_registry` or
  `expectations`.
- **Exit codes.** Raise the compare-runs `typer.Exit(1)` outside the guarded call, as
  `acs_targets.py` does. A catch-all inside the guard would turn it into the fixed
  failure line with exit 2.

- [ ] **Step 1: Write the failing tests**

- `test_help_lists_exactly_five_commands`.
- `test_data_dir_is_required`: exit 2 with a usage error.
- `test_commands_wire_arguments`: patch the five module functions with recorders. Each
  command passes exactly the arguments in the table.
- `test_failure_message_is_fixed`: a patched `build` raises
  `ValueError('EIN 123456789 at 1 Main St')`. stderr equals the fixed line and holds no
  `123456789`. Exit 2.
- `test_compare_unequal_exits_1`.
- Update `test_software_files_cover_loaded_modules` so it imports
  `embedding_data.ita_establishment_targets`.

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_ita_establishment_cli.py tests/test_ita_establishment_bundle.py::test_software_files_cover_loaded_modules -q`
Expected: FAIL, module not found.

- [ ] **Step 3: Implement the command module and add it to `SOFTWARE_FILES`**

- [ ] **Step 4: Run the tests and see them pass**

Run: the Step 2 command.
Expected: all pass.

- [ ] **Step 5: Document the commands**

- **`README.md`.** Add a section `## ITA establishment targets (Stage 10)` after
  "ITA assignment and 2023 area-mix targets". Include:
  - the five commands and the exact production invocations, with
    `--data-dir /Users/lowell/Projects/embedding-data/data`, the codes run and its pin
  - the eight tables and three JSON files
  - the reproduction gate and its scope
  - the owner go-ahead for each production write, and the Stage 9 coordination rule
  - scratch inside `.part`, and the rule that leftovers need the owner (gate 4)
  - the R8.4 exclusion
  - the statement that full-data acceptance is pending until the finding exists
- **`CLAUDE.md`.** Add a paragraph `**ITA establishment targets (Stage 10).**` after
  the Stage 9 paragraph. Include:
  - the module and commands, and the explicit `--data-dir`
  - the codes pin and the adopted source hash
  - the gate scope and the D2 cross-reference rule
  - the frozen-module rule and the Stage 9 `pgrep` check
  - the statement that measured acceptance is pending

- [ ] **Step 6: Commit**

Message: `feat: expose offline Stage 10 ITA establishment commands`.

---

### Task 10: V12 chain and independent reconciliation

**Files:**
- Modify: `tests/ita_establishment_fixtures.py` (`run_establishment_v12`)
- Create: `scripts/reconcile_stage10.py`
- Test: `tests/test_ita_establishment_v12.py`, `tests/test_reconcile_stage10.py`

**Interfaces:**
- Consumes: Task 8 fixture chain and API; `target_fixtures.forbid_external_access`.
- Produces:
  - `run_establishment_v12(tmp_path: Path, monkeypatch) -> dict` returns `data_dir`,
    `first`, `replay`, `first_pin` and `replay_pin`. It first calls
    `target_fixtures.forbid_external_access` and also forbids `httpx.Client` and
    `httpx.AsyncClient`. It then seeds the inputs, builds `first` and `replay` through
    the Python API with the fixture registry and expectations, verifies both and
    compares them.
  - `scripts/reconcile_stage10.py`: `main(argv: list[str] | None = None) -> int`, with
    two subcommands. Each takes `--data-dir D --run RUN_ID --outputs-sha256 P`, prints
    one JSON line, and returns 0 when equal and 1 otherwise.
    - `co-ownership` checks the pin with `hashlib`. It reads the canonical path from
      `inputs.json` and computes N, `n(a)` and `J(a,b)` with plain Python sets over
      `pl.read_parquet(canonical, columns=[...]).iter_rows()`. It uses its own EIN
      normalization and its own eligibility predicate, written from the spec text. It
      compares them with the bundle's `n_unweighted`, marginal `n_employers` and
      report `N`.
    - `stage3` runs `ita_verification.description_report(summary, read_titles(D))` and
      `link_report` for `YEAR_PAIRS` on the Stage 2 summary. It compares their integer
      V1/V2 columns with `report.json`.
  - **Independence.** The script imports no `ita_co_ownership`, `ita_area_mix`,
    `ita_establishment_records`, `ita_establishment_links` or `ita_text_pairs`.

**Reimplemented rules**, from the spec and not from code:
- **EIN.** Strip, remove `-`, and require `^[0-9]{8,9}$`. Zero-fill to 9. An
  all-same-digit result is unusable. The EIN is padded when the stripped,
  hyphen-free value has 8 digits.
- **Eligibility.** Year in 2023–2025, status `native_2022`, a non-null node, the three
  NAICS flags false (null is ineligible), and a usable unpadded EIN.

- [ ] **Step 1: Write the failing tests**

- `test_ita_establishment_raw_to_target_offline`: run the chain.
  - Both verifies pass, `compare_runs` is equal and the basis is the fixture basis.
  - Pairs: `flag_copied_title_any`, `flag_copied_index_any` (the cross-reference text),
    a placeholder, an unknown employer, `n_records_ein_padded > 0`, a headline pair
    with a non-basis code row, and a conflict pair.
  - Co-ownership: a cell 238220 → 722511 carrying `PADDED_LABEL`.
  - Links: the statuses `confirmed_same_id`, `confirmed_changed_id` and `conflict`.
  - `inputs['raw']` holds three index and three title citations.
  - `inputs['software']['files']` holds the command module.
- `test_reconcile_co_ownership_matches_fixture` returns 0.
- `test_reconcile_detects_difference`: patch the script's canonical reader to drop one
  eligible row. It returns 1.
- `test_reconcile_stage3_matches_fixture` returns 0.
- `test_reconciler_is_independent`: an AST import scan finds none of the forbidden
  modules.

- [ ] **Step 2: Run the tests and see them fail**

Run: `uv run --locked pytest tests/test_ita_establishment_v12.py tests/test_reconcile_stage10.py -q`
Expected: FAIL, missing helper and script.

- [ ] **Step 3: Implement the chain helper and the script**

- [ ] **Step 4: Run the tests and see them pass**

Run: the Step 2 command.
Expected: all pass.

- [ ] **Step 5: Run the software checkpoint**

Run the `pgrep` check, then:
- `uv run --locked pytest`: every test passes, with the `network` canary deselected.
- `uv run --locked behave`: every scenario passes.
- `uv run --locked ruff check .`: clean.
- `git diff --name-status main...HEAD -- src scripts tests`: only `A` lines, plus
  `M tests/code_fixtures.py`.

- [ ] **Step 6: Commit**

Message: `test: add Stage 10 raw-to-target V12 chain and reconciliation`.

---

### Task 11: Full-data acceptance (owner-gated)

**Files:**
- Create (Stage 1): `specs/naics-evaluation-data-stage-1-findings.md`
- Modify (Stage 1): `specs/naics-evaluation-data-roadmap.md` (Stage 1 tick and stamp),
  this plan's Roadmap line
- Create (Stage 4): `specs/findings/stage-10-ita-establishment-targets.md`
- Modify (Stage 4): `README.md`, `CLAUDE.md` (selected runs and pins)

`ROOT` below is `/Users/lowell/Projects/embedding-data/data`. Run every command from the
execution checkout. Run the `pgrep` check before each command. Each step names the
roadmap stage that runs it (D5).

- [ ] **Step 1 (Stage 1): Snapshot (read-only)**

Stage 1 takes this snapshot again before Gate 2 and keeps the first one (2026-11-15,
before Gate 1). Record these for the finding:
- the SHA-256 and line count of `ROOT/raw/manifest.jsonl`
- whether `ROOT/derived/osha/establishment-targets/` exists
- the SHA-256 of the Stage 2 summary, the codes `outputs.json` and both Stage 6 target
  `outputs.json` files

Expected Stage 6 pins: `stage6_ita_area_mix_20261014_1000_csv` is
`084292b6835eb09ce27ecc4a3aef03a6f43bfe7b39b815665c29190a431e2473`, and `_replay` is
`78fd21e37ba0c5b1cd396ff0961b557650788fdccd3c84a911e8c6c3b7fabe71`.

- [ ] **Step 2 (done 2026-11-16, before Stage 1): GATE 1, index acquisition**

Ask the owner for a go-ahead and confirm that no Stage 9 freeze window is open. Then:

```bash
uv run --locked python -m embedding_data.ita_establishment_targets acquire-references --data-dir /Users/lowell/Projects/embedding-data/data
```

Expected: three paths under `raw/references/naics/` and three new manifest lines with
the registered SHA-256. If Census refuses, the owner downloads the files by hand. Under
the same go-ahead, run `import-reference naics_index_<year> <file> --data-dir …` per
kind. If bytes or counts differ from the registry, stop and ask (checkpoint 2).

- [ ] **Step 3 (Stage 1): Choose a fresh run ID**

Use `stage10_ita_establishment_<YYYYMMDD>_r1`. Confirm that neither a final nor a
`.part` exists for it. Stage 4 picks the replay ID and checks it the same way.

- [ ] **Step 4 (Stage 1): GATE 2, first build**

Build from a committed checkout: `git status --porcelain --untracked-files=normal` prints
nothing at launch, and nothing in the checkout outside `.sdd/` changes until the JSON
line prints, because `inputs.json` records `dirty` for good. After the go-ahead, run the
build in the background and record wall time and maximum resident set size:

```bash
/usr/bin/time -l uv run --locked python -m embedding_data.ita_establishment_targets build <RUN> --data-dir /Users/lowell/Projects/embedding-data/data --codes-run stage4_v11_20261013_r2 --codes-outputs-sha256 15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a
```

Expected: one JSON line with `outputs_sha256`. If the process dies and leaves
`<RUN>.part`, leave it in place. Ask the owner (gate 4), record the event, and use a
new ID afterwards.

- [ ] **Step 5 (Stage 4): GATE 3, replay build**

Repeat Step 4 with the replay ID after its own go-ahead.

- [ ] **Step 6 (Stage 1: first run's `verify`; Stage 4: replay's `verify` and `compare-runs`): Verify and compare**

`verify` reruns every product, so record its wall time and maximum resident set size as
Step 4 does. Run it from the checkout and venv that built the run, with no `uv sync` or
`--with` overlay in between: the recorded software identity includes every installed
distribution.

```bash
/usr/bin/time -l uv run --locked python -m embedding_data.ita_establishment_targets verify <RUN> --data-dir /Users/lowell/Projects/embedding-data/data --outputs-sha256 <pin>
```

- `verify` for each run reports the basis `adopted_v1_v3_finding`.
- `compare-runs <RUN> <REPLAY> --data-dir …` reports `"equal": true` and exits 0.

- [ ] **Step 7 (Stage 1): Independent checks**

- `uv run --locked python scripts/reconcile_stage10.py co-ownership --data-dir … --run <RUN> --outputs-sha256 <pin>`
  reports equal.
- `uv run --locked python scripts/reconcile_stage10.py stage3 --data-dir … --run <RUN> --outputs-sha256 <pin>`
  reports equal.
- From `report.json`, pair records sum to 3,206,055 in total, and to each year's V1
  `n_rows`.

- [ ] **Step 8 (Stage 1): Preservation**

- The summary, codes and both Stage 6 `outputs.json` SHA-256 values equal the snapshot,
  and `target_io.verify_inventory` passes on each bundle.
- The manifest's first 3,007 lines are byte-identical to the first snapshot
  (2026-11-15), and only the three Gate 1 index lines were added. All 3,010 lines are
  byte-identical to the Stage 1 snapshot: `build` and `verify` append nothing.
- `uv run --locked embedding-data audit --data-dir /Users/lowell/Projects/embedding-data/data`
  reports zero discrepancies.

- [ ] **Step 8a (Stage 1): Findings file, tick and commit**

- Write `specs/naics-evaluation-data-stage-1-findings.md`, one screen: the run ID, the
  `outputs.json` pin, the `inputs.json` and `report.json` SHA-256, the Stage 1 snapshot
  values, the wall time and maximum RSS of `build` and `verify`, the bundle size, the
  Step 7 and Step 8 outcomes, and where the ledger's backup lives.
- Tick the roadmap's Stage 1 box, put the D5 stamp under it, and change `Stage 1` to
  `Stage 4` in this plan's Roadmap line.
- Commit. Message: `docs: record Stage 1 first build of the ITA NAICS targets`.
- Do not run the Plan Completion Protocol or tick any Task 11 box. Stage 4 does both.

- [ ] **Step 9 (Stage 4): Write the finding and update the docs**

`specs/findings/stage-10-ita-establishment-targets.md` records:
- the index originals (path, size, SHA-256, retrieval)
- the run IDs, the `outputs.json` pins, and the `inputs.json`/`report.json` SHA-256
- the executing commit and the software identity summary
- wall time and maximum RSS
- the V1/V2 reproduction, and the reconciliation and preservation outcomes
- the pair, link and co-ownership distributions, N and the exclusion partition
- the limits (spec "Methodological limits")
- what is not claimed: V9 size gate, scoring, null models and Stage 13

Then put the selected runs and pins into the README section and the `CLAUDE.md`
paragraph. Do not tick the roadmap's Stage 4. The Plan Completion Protocol does that.

- [ ] **Step 10 (Stage 4): Commit**

Message: `docs: record Stage 10 full-data acceptance`.
