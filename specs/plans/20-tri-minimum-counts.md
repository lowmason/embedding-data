# TRI Headline Minimum Count Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure reporting-year recurrence of the Stage 5 TRI parent-link cells, set one
headline minimum count for `tri_parent_links` by the committed band rule, record the decision
and amend spec R7.3 and V9.

**Architecture:** One offline script, `scripts/measure_tri_minimum_counts.py`, authenticates
the first Stage 5 run by its detached pin and by the SHA-256 and size of the four files it
reads. It recounts the per-year cells from the eligible facility-years and checks the recount
against the support table, the targets and `report.json` before any curve. Then it bands the
testable cells of each year pair with the V9 rule, copied from the Stage 3 script. Two new
steps follow: one downward merge of a thin top band, and no minimum for a year pair with too
few testable cells. It prints one sorted JSON line of aggregates. Tests publish small bundles
through the frozen `tri_facility_years.reduce` and `tri_parent_link_targets.estimate` and one
genuine V12 fixture chain. The controller runs the script twice on real data, and the decision
record transcribes the output.

**Tech Stack:** Python 3.14, Polars, argparse, pytest, uv. No new dependency.

**Spec:** `specs/tri-minimum-counts.md` (owner-approved 2026-11-22, merged in
lowmason/embedding-data#54, `89949ef`).

> Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 22 — on plan
> completion, tick the stage and re-validate later stages against what shipped.

> Deviation: the Stage 22 Consumes line (roadmap `:286`) names `report.json` and the
> per-cell `n_unweighted` column of `tri_parent_links`. The O13 cost cell (roadmap `:63`) says
> "one pass over the TRI family's `n_unweighted` counts, like O4". Under D1 the measurement
> also reads `tri_facility_years.parquet` and `tri_parent_link_support.parquet` of the run, and
> it recomputes per-year owner counts (owner, D1, 2026-11-22, spec "Rollout").

Roadmap line numbers are as of `89949ef`. Roadmap `:290` still says `ROUTING: brainstorming`
for Stage 22. The approved spec governs. The roadmap Exit holds as written: one minimum, from
the observed `n_unweighted` counts split by reporting year. The completion protocol ticks the
stage and puts this stamp under its entry, which cites the Deviation note:

```text
> Stage 22: COMPLETE (<date>) — implemented by plan 20 (specs/plans/completed/20-tri-minimum-counts.md). Its Deviation note records the wider Consumes and cost. Its Handoff section names what O17 consumes.
> Next: resume the roadmap.
```

## Global Constraints

- **Branch.** Cut a new branch from `main` at or after the merge that lands this plan, in a
  worktree (using-git-worktrees). Never rebase or squash the branch after Task 5 Step 3,
  because the decision record cites the rule commit by its SHA. Take a later `main` in by a
  merge, never a rebase. The branch merges only through Task 7.
- **Script frozen after Task 5 Step 4.** Once the first real run has executed, a finding
  against the script from any later review (the final whole-branch review included) follows
  OC3: only a fix toward the written rule, then both real runs again at the new commit, and
  the decision record discloses it.
- **Frozen software.** Change no file in `tri_bundle.SOFTWARE_FILES`
  (`src/embedding_data/tri_bundle.py:57-82`, 24 files, including `pyproject.toml` and
  `uv.lock`), the Stage 6 `FROZEN_MODULES` and `TARGET_MODULES`, the Stage 7 to 9 software,
  `cli.py` or `code_references.py`. Change neither the Python build nor the installed
  distributions. Add no dependency, marker or console entry point. New code goes in
  `scripts/` and `tests/` only. `tests/conftest.py` may gain one `SLOW_TESTS` entry (Task 4).
- **Frozen records.** Do not edit `scripts/measure_ita_minimum_counts.py`,
  `tests/minimum_count_fixtures.py`, `specs/naics-evaluation-data-stage-5-findings.md` or
  `specs/findings/stage-5-tri-parent-links.md`.
- **Leave alone.** The runs under `data/derived/epa_tri/parent-links/`, the raw tree under
  `data/`, `data/raw/manifest.jsonl` and the evidence directory
  `/Users/lowell/.cache/embedding-data/stage-18/`. The sibling worktrees and their branches:
  `.claude/worktrees/stage-19-wage-minimum-earners` (`worktree-stage-19-wage-minimum-earners`),
  `.claude/worktrees/stage-21-usaspending-minimum-counts`
  (`worktree-stage-21-usaspending-minimum-counts`) and
  `/Users/lowell/.codex/worktrees/acs-targets-design/embedding-data`
  (`codex/acs-targets-design`). Their work is partly uncommitted. Recheck them with
  `git worktree list --porcelain` before any edit of a shared file (Task 6).
- **Offline and credential-free.** The script uses no network, no `.env`, no HTTP client, no
  upstream builder and no `verify` run. Its only third-party import is `polars`. Its only
  `embedding_data` imports are `target_contract` (`TARGET_SCHEMA`), `tri_facility_years`
  (`TABLE_SCHEMA`) and `tri_parent_link_targets` (`YEARS`, `SUPPORT_SCHEMA`, `METADATA`,
  `DNB_LABEL`, `FEDERAL_LABEL`, `distribution`). Importing them loads `httpx` but constructs
  no client. The script imports no private name (a leading underscore), so the recount stays
  independent of the code it checks. `distribution` is the one reused function (spec "What
  gets built", item 1).
- **Freeze window.** Before every real-data run, every full pytest run and every commit, run
  `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`. If it prints
  anything, stop, leave files uncommitted and tell the owner.
- **Commit protocol.** `pgrep` check, then `git add` of the task's files, then `git commit`
  with the given message and the session's `Co-Authored-By` trailer. Never skip a hook.
- **Rule before data.** The script, its tests and the constants below are committed before the
  first real run. No constant changes after that run. A fix that only makes the script match
  the written rule is allowed, and the decision record discloses it. Any change to the written
  rule goes to the owner.
- **Constants** (spec "From curves to a minimum"): `LEVEL = 0.90`, `TOP_BAND = 10`,
  `MIN_BAND_CELLS = 50`, `WILSON_Z = 1.959963984540054`, and
  `YEAR_PAIRS = tuple(zip(YEARS, YEARS[1:]))`, which is `((2022, 2023), (2023, 2024))`.
  `YEARS` is imported from `tri_parent_link_targets`, never retyped.
- **Absence reasons** (fixed strings): `'too_few_testable_cells'` (spec step 4) and
  `'top_band_misses_level'` (spec step 8).
- **Columns read** (spec "Inputs"), each with its type from the frozen schemas
  (`tri_facility_years.TABLE_SCHEMA`, `tri_parent_link_targets.SUPPORT_SCHEMA`,
  `target_contract.TARGET_SCHEMA`):
  - `tri_facility_years.parquet`: `reporting_year` (Int64), `trifd`, `naics_2022_node_id`,
    `owner_key`, `exclusion_reason` (String).
  - `tri_parent_link_support.parquet`: `unit_a`, `unit_b` (String), `j_owners`, `j_2022`,
    `j_2023`, `j_2024` (UInt64).
  - `tri_parent_links.parquet`: `measure`, `unit_a`, `unit_b` (String), `n_unweighted`
    (UInt64), `flags` (List(String)).
  - `report.json`: `n_unweighted_distribution`, `owner_key_changes`, `n_owners.headline` and
    `owners_by_year.<year>.headline`. `owners_by_year` is keyed by the year as a string
    (`'2022'`). Each value of `n_owners` and `owners_by_year` is a dict keyed by variant
    (`src/embedding_data/tri_parent_link_targets.py:258-261`, `:277-278`).
- **Tests.** Red → green on synthetic bundles. Every test passes `--data-dir` under
  `tmp_path` and never reads the real tree. No real count from the Stage 5 findings appears in
  the script or a fixture.
- **Production root.** Only Task 5 reads real data, with
  `--data-dir /Users/lowell/Projects/embedding-data/data` passed explicitly. Nothing writes
  under `data/`. Real output goes to `$OUT` (Task 5) and never enters git.
- **Aggregates only.** R8.1 to R8.4 hold. Stdout, stderr and the decision record hold counts,
  rates, constants and pins only: no TRIFD, no parent name, no owner key, no node ID and no
  list of cells. No embedder output, score or ranking is read.
- **Style.** 4-space indentation, single quotes, `'''` docstrings, ruff at 99 columns. Plan
  and record prose follows the plain technical English rule.

**Pinned input** (spec "Inputs"):

| File | Identity |
| --- | --- |
| `derived/epa_tri/parent-links/stage5_tri_parent_links_20261121_r1/outputs.json` | detached SHA-256 `65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b` |
| its `report.json` | inventory SHA-256 `dc002222c0d9fa652f5623ef089dc324a000625d8a23fd681b3d227ed98d6a6e` (Stage 18 finding) |
| its three read Parquet files | their records in that `outputs.json` (SHA-256 and size) |

## Review Focus

1. Excluded facility-years have a null `owner_key`, and the three `naics_*` reasons also have
   a null `naics_2022_node_id`. The real table holds hundreds in each year. Only rows of `E`
   need both, so a bundle with one excluded row of each of the five reasons must pass every
   self-check (Task 3, golden bundle).
2. An empty or thin top band is the common case here: the real pooled maximum is 50, and
   single-year counts are smaller. After the upward merge, 60 testable cells at count 1 give
   bands `(1, 1)` and `(2, None)` with 0 testable cells. Stage 3 stops there with no minimum.
   Spec step 3 merges that top band down, so the year pair can get minimum 1 (Task 1, and the
   golden run of Task 4).
3. One owner with two facilities at one node in year t, of which one leaves and one stays. The
   owner still has a staying facility-year at that node, so the cell stays testable. The cell
   counts the owner once in `j_t` (Task 2).
4. A TRIFD whose `owner_key` changes between t and t+1 is not staying. The bundle then reports
   `owner_key_changes` 1, and the self-check must pass. Real data has 0, so only a fixture
   exercises this (Tasks 2 and 3).
5. An unexpected error whose message holds a TRIFD or an owner key. Neither stdout nor stderr
   may carry it. Stderr gets the exception type and the frame locations only (Task 4).

## Decisions

None.

## Owner Checkpoints

- **OC1 (plan review).** The defaults this plan sets where the spec or the brief leaves a
  choice:
  1. Real output goes to `$HOME/.cache/embedding-data/stage22-minimum-counts/<rule commit>/`,
     outside the repository and outside `data/`, after the Stage 21 precedent. It is not the
     leave-alone `stage-18/` directory.
  2. The script is `scripts/measure_tri_minimum_counts.py`. It copies the Stage 3 band
     functions, so that its own constants govern, and a test pins them equal to the Stage 3
     ones. Loading the Stage 3 script instead would make its constants drive `bands` and
     `pair_minimum` and would run its ITA imports.
  3. Refusals that the spec does not list: a read column with another type, and a malformed
     `report.json`.
  4. With no family minimum, the script still prints every curve, the kept counts are null,
     and the exit is 1. The two absence reasons are the fixed strings of Global Constraints.
  5. A kept share divides by the target rows (rows) or by their summed `n_unweighted`
     (support).
  6. On an unexpected error, stderr holds the exception type name and one
     `file:line in function` line per frame, never the message.
- **OC2 (Task 5).** Exit 1 (a year pair with too few testable cells, or a top band that misses
  `LEVEL`) stops the stage. The owner decides. No constant changes, and no fallback applies.
- **OC3 (Task 5).** A refusal on real data stops the stage. A fix may only bring the script to
  the written rule, and the decision record discloses it. Anything else goes to the owner.
- **OC4 (Task 7).** The owner approves the PR before it merges.

## File Structure

| File | Responsibility |
| --- | --- |
| `scripts/measure_tri_minimum_counts.py` (create) | Constants, band rule, per-year counts, authentication, self-checks, kept counts, CLI |
| `tests/test_measure_tri_minimum_counts.py` (create) | All tests and the small-bundle helpers. Loads the script with `importlib`, as `tests/test_measure_ita_minimum_counts.py:21-29` does |
| `tests/conftest.py` (modify, only if Task 4 Step 4 says so) | One `SLOW_TESTS` entry |
| `specs/findings/v9-tri-minimum-counts.md` (create) | The decision record |
| `specs/embedding-evaluation-data-spec.md` (modify) | R7.3 and V9 amendments |
| `CLAUDE.md`, `README.md`, `specs/deliverable-map.md` (modify) | Stale O13 lines |

---

### Task 1: Rule constants, band functions and the year-pair curve

**Files:**
- Create: `scripts/measure_tri_minimum_counts.py`
- Test: `tests/test_measure_tri_minimum_counts.py`

**Interfaces:**
- Produces, in the script module:
  - The constants of Global Constraints, `YEARS` imported unchanged, and
    `COUNTS = ('base_cells', 'testable_cells', 'recurring_cells')`.
  - Copied unchanged in behavior from `scripts/measure_ita_minimum_counts.py:76-162`:
    `wilson(recurring: int, testable: int) -> tuple[float, float] | None`,
    `raw_counts(cells: pl.DataFrame) -> dict[int, dict]`,
    `close_band(pending: dict, high: int | None) -> dict`,
    `bands(cells: pl.DataFrame) -> list[dict]`,
    `pair_minimum(bands: list[dict]) -> int | None` and
    `family_minimum(minimums: list[int | None]) -> int | None`.
  - New: `merge_thin_top(found: list[dict]) -> tuple[list[dict], list[dict] | None]`. It
    returns the bands after spec step 3, and the two bands before the merge, or None when no
    merge happens.
  - New: `curve(cells: pl.DataFrame) -> dict` with keys `base_cells`, `testable_cells`,
    `recurring_cells` (summed over the bands), `bands` (after step 3),
    `before_downward_merge` (the second value of `merge_thin_top`), `minimum` and `reason`
    (None or an absence reason).
  - A **cells frame** has `base_count` (UInt64), `testable` and `recurs` (Boolean), one row
    per base cell. A **band** is `{'low', 'high', 'base_cells', 'testable_cells',
    'recurring_cells', 'rate', 'wilson_low', 'wilson_high'}`, as in Stage 3.

The new steps run on the output of `bands`, never inside it. `merge_thin_top` merges when the
last band has fewer than `MIN_BAND_CELLS` testable cells and at least one band lies below it.
It sums the `COUNTS` of the last two bands, keeps the lower band's `low`, and closes the sum
with `close_band(pending, None)`. It never averages two rates. `curve` runs `bands`, then
`merge_thin_top`, then the total check: fewer than `MIN_BAND_CELLS` testable cells give
minimum None and `'too_few_testable_cells'`, and `pair_minimum` is not called. Otherwise
`minimum` is `pair_minimum` of the merged bands, and None gives `'top_band_misses_level'`.

- [ ] **Step 1: Write the failing tests**

Add `load_script()` (copy `tests/test_measure_ita_minimum_counts.py:24-29`, script path
`scripts/measure_tri_minimum_counts.py`, assertion message `'measurement script is missing'`),
a `script` fixture, `cells(*groups)` and `band(low, high, rate)` (copy `:37-56`). Write a band
as `(low, high, testable_cells, recurring_cells)` below.

```python
def test_rule_constants_are_the_committed_values(script):
    assert (script.LEVEL, script.TOP_BAND, script.MIN_BAND_CELLS) == (0.90, 10, 50)
    assert script.WILSON_Z == 1.959963984540054
    assert script.YEAR_PAIRS == ((2022, 2023), (2023, 2024))
```

- `test_band_functions_match_stage_3`: load `scripts/measure_ita_minimum_counts.py` inside
  the test with `importlib` under the module name `stage3_measure`. For each frame of this
  task, `script.bands(frame) == stage3.bands(frame)` and the two `pair_minimum` results are
  equal. `script.wilson(73, 80) == stage3.wilson(73, 80)`, and `family_minimum` agrees on
  `[1, 3]`, `[2, None]` and `[]`.
- `test_bands_merge_short_bands_upward`: the frame and expected bands of
  `tests/test_measure_ita_minimum_counts.py:64-70`, through `script.bands`.
- `test_curve_merges_the_thin_top_band_down`: `curve` of the same frame gives bands
  `[(1, 1, 200, 0), (2, 3, 60, 0), (4, 4, 60, 0), (5, None, 60, 0)]` and
  `before_downward_merge` `[(5, 9, 55, 0), (10, None, 5, 0)]`.
- `test_empty_top_band_merges_down`: `cells((1, 60, 60, 0))` gives bands
  `[(1, None, 60, 60)]` with rate 1.0, `before_downward_merge`
  `[(1, 1, 60, 60), (2, None, 0, 0)]`, minimum 1 and reason None. Stage 3's
  `pair_minimum(bands(frame))` is None for the same frame.
- `test_merged_rate_sums_counts`: `cells((1, 60, 30, 0), (9, 60, 53, 0), (10, 20, 20, 0))`
  gives `before_downward_merge` `[(2, 9, 60, 53), (10, None, 20, 20)]`, bands
  `[(1, 1, 60, 30), (2, None, 80, 73)]`, a top rate of `73 / 80`, a top Wilson interval of
  `wilson(73, 80)` and minimum 2. `pair_minimum(bands(frame))` is 10.
- `test_downward_merge_can_stop_a_passing_pair`:
  `cells((1, 60, 60, 0), (9, 60, 40, 0), (10, 20, 20, 0))` gives a top band
  `(2, None, 80, 60)` with rate 0.75, minimum None and reason `'top_band_misses_level'`.
  `pair_minimum(bands(frame))` is 10.
- `test_merged_lower_band_keeps_its_start`: `cells((1, 30, 30, 0), (3, 30, 30, 0),
  (10, 10, 10, 0))` gives bands `[(1, None, 70, 70)]` and minimum 1.
- `test_full_top_band_is_not_merged`: `cells((1, 60, 60, 0), (10, 50, 45, 0))` gives
  `before_downward_merge` None, bands `[(1, 1, 60, 60), (2, None, 50, 45)]` and minimum 1. A
  rate equal to `LEVEL` passes.
- `test_too_few_testable_cells_give_no_minimum`, parametrized over `cells((1, 49, 49, 0))`,
  `cells((1, 0, 0, 60))` and `cells()`: minimum None, reason `'too_few_testable_cells'` and
  `before_downward_merge` None. The first gives bands `[(1, None, 49, 49)]` with rate 1.0,
  so it would pass `pair_minimum` alone.
- `test_fifty_testable_cells_are_enough`: `cells((1, 50, 50, 0))` gives minimum 1 and reason
  None.
- `test_pair_minimum_is_start_of_trailing_passing_run`: bands with lows 1, 2, 3, 10 and rates
  0.95, 0.5, 0.95, 0.95 give 3. All four at 0.95 give 1.
- `test_family_minimum_is_largest_and_needs_both_pairs`: `[1, 3]` gives 3, `[2, None]` and
  `[]` give None.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_tri_minimum_counts.py -v`
Expected: FAIL with "measurement script is missing".

- [ ] **Step 3: Implement the constants, the copied band functions, `merge_thin_top` and `curve`**

The module docstring states the rule in three sentences and cites
`specs/tri-minimum-counts.md`. It says that the band functions are copied from the Stage 3
script so that the Stage 22 constants govern, and that the downward merge and the total check
run after `bands`. The docstring of the copied `bands` keeps its Stage 3 meaning: the top band
keeps its cells there, and `merge_thin_top` merges it later.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_measure_tri_minimum_counts.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/measure_tri_minimum_counts.py tests/test_measure_tri_minimum_counts.py
git commit -m "feat(scripts): add the Stage 22 band rule"
```

### Task 2: Per-year counts, staying facility-years and testable cells

**Files:**
- Modify: `scripts/measure_tri_minimum_counts.py`
- Test: `tests/test_measure_tri_minimum_counts.py`

**Interfaces:**
- Consumes in the tests (unchanged): `tri_fixtures.rows_frame`, `tri_facility_years.reduce`,
  `public` and `EXCLUSIONS`, `tri_layout.load_layouts`, `tri_codes.NODE_PREFIX` and
  `tri_parent_link_targets.estimate`.
- Produces in the test file:
  - `N1` to `N10`: `NODE_PREFIX` plus `'325199'`, `'311111'`, `'212311'`, `'221114'`,
    `'324110'`, `'325211'`, `'331110'`, `'562211'`, `'336111'` and `'336112'`.
    `NODES = frozenset({N1, …, N10})`, `LAYOUTS = load_layouts()` and
    `DAY = date(2025, 11, 5)`. Made-up D&B numbers `PINE, ROCK, SLATE = '110000111',
    '220000222', '330000333'`.
  - `form(year, trifd, node, parent='', dnb='', **fields) -> dict` and
    `excluded(reason, year, trifd, *parents) -> list[dict]`, copied from
    `tests/test_tri_parent_link_targets.py:47-68` with `A, B = N1, N2`.
  - `table(records: list[dict]) -> pl.DataFrame`:
    `public(reduce(rows_frame(records), LAYOUTS, NODES))`.
  - `golden_records() -> list[dict]`: Pine (`PINE`) owns `T1` to `T8` at `N1` to `N8` in each
    of 2022, 2023 and 2024. `T11` is self-owned at `N3` in each year. Rock owns `T9` at `N1`
    (`ROCK`) and `T10` at `N2` (`SLATE`) in 2022 and 2023. Tin owns `T13` at `N2` in 2023,
    plus `excluded('federal', 2023, 'T14', 'Tin')`. Zinc has
    `excluded(reason, 2023, 'T15', 'Zinc')` to `'T17'` for `naics_missing`, `naics_conflict`
    and `naics_not_2022`, and `excluded('parent_conflict', 2023, 'T18', 'Zinc', 'Quartz')`.
- Produces in the script:
  - `eligible_facility_years(table: pl.LazyFrame) -> pl.DataFrame`: the rows with a null
    `exclusion_reason`, as `year` (Int64), `trifd`, `node` and `owner` (String), sorted by
    `year` and `trifd`.
  - `recount(eligible: pl.DataFrame) -> pl.DataFrame`: `unit_a`, `unit_b`, `j_owners`,
    `j_2022`, `j_2023`, `j_2024` (UInt64), one row per ordered pair of distinct nodes with
    `j_owners ≥ 1`, sorted by `unit_a` and `unit_b`.
  - `year_cells(eligible: pl.DataFrame, counts: pl.DataFrame, base: int) -> pl.DataFrame`:
    `unit_a`, `unit_b`, `base_count` (UInt64), `testable` and `recurs` (Boolean), one row per
    cell of `counts` with `j_{base} ≥ 1`, sorted by `unit_a` and `unit_b`.

Rule (spec "The rule"). `recount` reduces the rows to distinct `(owner, year, node)` before
the self-join on `(owner, year)`. `j_t` counts the distinct owners of the pairs in year t.
`j_owners` counts the distinct owners over all years, never a sum of the `j_t`. In
`year_cells`, a year-t row is staying when a year t+1 row has the same `trifd` and the same
`owner`. Reduce the year-t rows to `(owner, node, staying)`, with `staying` true when any row
of that owner and node stays, before the self-join on `owner`. A cell is testable when one
owner has `staying` true at both of its nodes. `base_count` is `j_t` and `recurs` is
`j_{t+1} ≥ 1`, both from `counts`.

- [ ] **Step 1: Write the helpers and the failing tests**

`A–B` below means one facility-year each of `A` and `B`. "2022 Pine T1@N1, T2@N2" means
`form(2022, 'T1', N1, 'Pine', PINE)` and `form(2022, 'T2', N2, 'Pine', PINE)`. Each test runs
`eligible_facility_years(table(records).lazy())`, then `recount`, then `year_cells`. "The
2022 cell" means the row `(N1, N2)` of `year_cells(..., 2022)`.

- `test_recount_equals_the_frozen_support`: for `golden_records()`, `recount` equals
  `estimate(reduce(rows_frame(records), LAYOUTS, NODES), processed_as_of=DAY).support`
  selected to `unit_a`, `unit_b`, `j_owners`, `j_2022`, `j_2023`, `j_2024`.
- `test_year_counts_follow_each_reporting_year`: 2022 and 2023 Pine T1@N1, T2@N2, and 2023
  Rock T9@N1, T10@N2, give exactly the rows `(N1, N2)` and `(N2, N1)`, each with `j_owners` 2,
  `j_2022` 1, `j_2023` 2 and `j_2024` 0.
- `test_facility_owner_forms_no_cell`: self-owned `T11` at `N1` in all three years and 2022
  Pine T1@N3, T2@N4 give exactly the rows `(N3, N4)` and `(N4, N3)`.
- `test_two_facilities_at_one_node_count_once`: 2022 Pine T1@N1, T3@N1, T2@N2, and 2023 Pine
  T3@N1, T2@N2 (`T1` leaves). The 2022 cell has `j_2022` 1, `base_count` 1, `testable` true
  and `recurs` true.
- `test_cell_recurs_through_the_same_owner`: 2022 and 2023 Pine T1@N1, T2@N2 give the 2022
  cell `testable` true and `recurs` true.
- `test_facility_that_leaves_makes_no_cell_testable`: 2022 Pine T1@N1, T2@N2, then 2023 Pine
  T1@N1 and Rock T9@N1, T10@N2. The 2022 cell has `testable` false and `recurs` true.
- `test_ineligible_refile_makes_no_cell_testable`, parametrized over `EXCLUSIONS`: 2022 Pine
  T1@N1, T2@N2, then 2023 Pine T1@N1 and `excluded(reason, 2023, 'T2', 'Pine')`, with
  `'Quartz'` as a second parent for `parent_conflict`. The 2022 cell has `testable` false.
- `test_changed_code_makes_a_testable_cell_that_fails`: 2022 Pine T1@N1, T2@N2, then 2023 Pine
  T1@N1, T2@N3. The 2022 cell has `testable` true and `recurs` false.
- `test_cell_recurs_through_another_owner`: the records of the test above plus 2023 Rock
  T9@N1, T10@N2. The 2022 cell has `testable` true and `recurs` true.
- `test_owner_key_change_is_not_staying`: 2022 Rock T9@N1, T10@N2, then 2023
  `form(2023, 'T9', N1, 'Slate', SLATE)` and Rock T10@N2. The 2022 cell has `testable` false
  and `recurs` false, and the frozen `estimate(...).report['owner_key_changes']` is 1.
- `test_second_year_pair_reads_2023_and_2024`: 2023 and 2024 Pine T1@N1, T2@N2 give no row
  for base 2022 and, for base 2023, the cell with `testable` true and `recurs` true.
- `test_mirror_rows_share_counts_and_outcome`: for `golden_records()` and both base years,
  each row of `year_cells` joined to its mirror `(unit_b, unit_a)` has equal `base_count`,
  `testable` and `recurs`, and every row has a mirror.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_tri_minimum_counts.py -v`
Expected: the Task 1 tests PASS. The new tests FAIL with
`AttributeError: ... has no attribute 'eligible_facility_years'`.

- [ ] **Step 3: Implement `eligible_facility_years`, `recount` and `year_cells`**

Owner counts use `n_unique` cast to UInt64. Sort every result, so group order never reaches
the output.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_measure_tri_minimum_counts.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/measure_tri_minimum_counts.py tests/test_measure_tri_minimum_counts.py
git commit -m "feat(scripts): count TRI parent-link cells by reporting year"
```

### Task 3: Small bundles, authentication and self-checks

**Files:**
- Modify: `scripts/measure_tri_minimum_counts.py`
- Test: `tests/test_measure_tri_minimum_counts.py`

**Interfaces:**
- Consumes in the tests (unchanged): `tri_parent_link_targets.estimate` and
  `validate_parent_links`, `tri_parent_industries.build_parent_industries`,
  `tri_bundle.TABLES` and `FILES`, `target_contract.write_targets`, `target_io.inventory` and
  `write_json`, and `manifest.sha256_file`.
- Produces in the test file:
  - `code_change_records() -> list[dict]`: Pine owns `T1` to `T8` at `N1` to `N8` in 2022. In
    2023 and 2024, `T1` is at `N9`, `T2` at `N10` and `T3` to `T8` are unchanged.
  - `publish(root: Path, records: list[dict], *, run='fixture') -> dict`: reduces the
    records with `NODES`, runs `estimate(frame, processed_as_of=DAY)` and
    `validate_parent_links`, and writes `root/'data'/'derived/epa_tri/parent-links'/run/`.
    `tri_parent_links.parquet` goes through `write_targets`. The other four `TABLES` are
    `estimate`'s marginals and support, `build_parent_industries(frame)` and `public(frame)`.
    It writes `report.json` (the estimate's report) and `inputs.json` (`{}`) with
    `write_json`, then `outputs.json` as `write_json` of
    `target_io.inventory(directory, list(FILES))`. Returns `{'data_dir', 'directory', 'run',
    'pin'}`.
  - `rehash(directory: Path) -> str`, `forge_table(bundle: dict, name: str, change) -> str` and
    `forge_report(bundle: dict, change) -> str`. Each forge applies `change` to one file,
    rewrites `outputs.json` from the inventory and returns the new pin, so the script trusts
    the changed file and a self-check must find the change.
- Produces in the script:
  - `class Refused(Exception)`, whose message is a fixed reason.
  - `@dataclass(frozen=True) class Inputs` with `directory: Path`, `outputs_sha256: str` and
    `files: dict[str, str]`, the SHA-256 of each of the four read files.
  - `authenticate(data_dir: Path, run_id: str, pin: str) -> Inputs`. The run directory is
    `data_dir / 'derived/epa_tri/parent-links' / run_id`.
  - `@dataclass(frozen=True) class Checked` with `eligible: pl.DataFrame`, `counts:
    pl.DataFrame` (the `recount`), `targets: pl.DataFrame` (the read target columns) and
    `distribution: dict` (the report entry).
  - `self_check(inputs: Inputs) -> Checked`.

Checks in order, each with its fixed reason. A later check never runs when an earlier one
refuses.

1. The run ID matches `[A-Za-z0-9][A-Za-z0-9_-]*` and the pin `[0-9a-f]{64}`, both with
   `fullmatch`: `'unsafe run id or pin'`.
2. `outputs.json` exists and its SHA-256 equals the pin: `'outputs pin differs'`.
3. In the order `report.json`, `tri_facility_years.parquet`,
   `tri_parent_link_support.parquet`, `tri_parent_links.parquet`: the file exists and has a
   record in `outputs.json`, and its SHA-256 and its size equal that record:
   `'<name> differs from its inventory'`. Hash only these four files, with
   `hashlib.file_digest`. Do not call `target_io.verify_inventory`, which reads every file of
   the run. Stage 3's `check_inventory` checks no size, so do not copy it.
4. Each Parquet holds every read column with its frozen type:
   `'<name> columns differ from the contract'`.
5. `report.json` is a JSON object. `n_unweighted_distribution` is an object.
   `owner_key_changes` is an `int` and not a `bool`. `n_owners` is an object whose
   `'headline'` is such an `int`. `owners_by_year` is an object with an object under each of
   `'2022'`, `'2023'` and `'2024'`, each with such an `int` under `'headline'`:
   `'report is malformed'`.
6. `(reporting_year, trifd)` has no null and no repeat over the whole table:
   `'facility-year keys are not unique'`.
7. Every `reporting_year` is in `YEARS`: `'reporting year outside the window'`.
8. Every row of `E` has a non-null `owner_key` and `naics_2022_node_id`:
   `'an eligible facility-year lacks an owner or node'`. Excluded rows are not checked.
9. The TRIFDs of `E` with more than one distinct `owner_key` number `owner_key_changes`
   (`src/embedding_data/tri_parent_link_targets.py:274-275`):
   `'owner key changes differ from the report'`.
10. The distinct owners of `E`, `facility:` keys included, equal `n_owners['headline']`, and
    those of each year equal `owners_by_year[str(year)]['headline']`:
    `'owner counts differ from the report'`.
11. `recount` equals the support table's `unit_a`, `unit_b`, `j_owners`, `j_2022`, `j_2023` and
    `j_2024`, row for row after sorting: `'recount differs from the support table'`.
12. Every `measure` is `METADATA['measure']`, and the targets' sorted
    `(unit_a, unit_b, n_unweighted)` equal the support's `(unit_a, unit_b, j_owners)`:
    `'target rows differ from the support table'`.
13. `json.loads(json.dumps(distribution(values)))` equals `n_unweighted_distribution`, where
    `values` is the targets' `n_unweighted` as a list:
    `'report distribution differs from the targets'`.

- [ ] **Step 1: Write the helpers and the failing tests**

Add a `golden` fixture, `publish(tmp_path, golden_records())`.

- `test_authenticate_returns_pinned_files`: `inputs.outputs_sha256 == golden['pin']`, and
  `inputs.files` equals the `sha256` of the four records in `outputs.json`.
- `test_unsafe_run_id_or_pin_refused`, parametrized over run `'../fixture'`, `'fixture/'`,
  `'-fixture'`, `'fixture\n'`, and pins `'A' * 64` and `'0' * 63`. Reason
  `'unsafe run id or pin'`.
- `test_wrong_or_missing_pin_refused`: pin `'0' * 64`, and a deleted `outputs.json`. Reason
  `'outputs pin differs'`.
- `test_changed_file_refused`, parametrized over the four read files: append one byte and do
  not rehash. Reason `'<name> differs from its inventory'`.
- `test_size_is_checked`: set the facility-year record's `size` to size + 1 in
  `outputs.json`, keep its `sha256` and pass the SHA-256 of the edited `outputs.json`. Reason
  `'tri_facility_years.parquet differs from its inventory'`.
- `test_missing_record_refused`: delete the support record from `outputs.json`, then pass its
  new SHA-256. Reason `'tri_parent_link_support.parquet differs from its inventory'`.
- `test_pin_is_checked_before_files`: a changed support table and a wrong pin give
  `'outputs pin differs'`.
- `test_unread_files_are_never_read`: append bytes to `inputs.json`,
  `tri_parent_link_marginals.parquet` and `tri_parent_industries.parquet` without a rehash.
  `self_check(authenticate(...))` passes.
- `test_retyped_or_missing_column_refused`, parametrized: `reporting_year` cast to Int32 in the
  facility-year table, `j_2024` dropped from the support table, and `n_unweighted` cast to
  Int64 in the targets. Reasons from check 4.
- `test_golden_passes_with_excluded_rows`: `self_check` of the golden bundle returns a
  `Checked` with `eligible.height` 32, although its five excluded rows have a null
  `owner_key` and three have a null node.
- `test_owner_key_change_passes_the_self_check`: publish the records of
  `test_owner_key_change_is_not_staying` (Task 2). `self_check` returns a `Checked`, and the
  bundle's `report.json` has `owner_key_changes` 1.
- `test_unread_report_keys_are_not_checked`: `forge_report` that sets `n_owners['dnb']` and
  `owners_by_year['2023']['federal']` to `-1`. `self_check` passes.
- `test_self_check_refusals`, parametrized over a forge and the reason of its check:
  - check 5: `n_unweighted_distribution` deleted, `owners_by_year['2024']` deleted, and
    `n_owners['headline']` set to `'4'`.
  - check 6: a facility-year row appended a second time.
  - check 7: the `reporting_year` of the first row set to 2021.
  - check 8: the `owner_key`, or the node, of the first eligible row set to null.
  - check 9: `owner_key_changes` plus 1.
  - check 10: `n_owners['headline']` plus 1, and `owners_by_year['2023']['headline']` plus 1.
  - check 11: a dropped support row, `j_2023` plus 1 on the first support row, and `j_owners`
    plus 1 on the first support row.
  - check 12: a dropped target row, the first target's `measure` set to `'other_share'`, and
    the first target's `n_unweighted` plus 1.
  - check 13: the distribution's `max` plus 1.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_tri_minimum_counts.py -v`
Expected: the earlier tests PASS. The new tests FAIL with
`AttributeError: ... has no attribute 'authenticate'`.

- [ ] **Step 3: Implement `Refused`, `Inputs`, `authenticate`, `Checked` and `self_check`**

Scan each Parquet lazily for its read columns only (`pl.scan_parquet(...).select(...)`), and
check the types from `collect_schema()` before collecting. All three tables are small, so
collect them once.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_measure_tri_minimum_counts.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/measure_tri_minimum_counts.py tests/test_measure_tri_minimum_counts.py
git commit -m "feat(scripts): authenticate and recount the Stage 5 TRI bundle"
```

### Task 4: Kept counts, the result and the command line

**Files:**
- Modify: `scripts/measure_tri_minimum_counts.py`
- Modify: `tests/conftest.py` (only if Step 4 says so)
- Test: `tests/test_measure_tri_minimum_counts.py`

**Interfaces:**
- Consumes: everything above. In the tests: `tri_fixtures.run_tri_v12` and
  `target_fixtures.forbid_external_access`.
- Produces:
  - `published(targets: pl.DataFrame, counts: pl.DataFrame) -> pl.DataFrame`: one row per
    target row with `count` (`n_unweighted`, UInt64), `largest_year_count` (the largest of
    the cell's `j_2022`, `j_2023` and `j_2024`, UInt64), `dnb_label` and `federal_label`
    (Boolean: `flags` contains `DNB_LABEL` or `FEDERAL_LABEL`).
  - `kept(rows: pl.DataFrame, minimum: int | None) -> dict` with keys `rows`, `support` (sum
    of `count`), `dnb_rows`, `federal_rows`, `kept_rows`, `kept_row_share`, `kept_support`,
    `kept_support_share`, `lenient_kept_rows` (kept with `largest_year_count < minimum`),
    `kept_dnb_rows` and `kept_federal_rows`. A row is kept when `count >= minimum`. With
    `minimum` None, the last seven keys are None.
  - `summarize(year_pair_cells: dict[str, pl.DataFrame], rows: pl.DataFrame,
    distribution: dict) -> dict`. `year_pair_cells` maps `'2022-2023'` and `'2023-2024'` to
    cells frames. It returns `{'year_pairs': {label: curve(...)}, 'minimum':
    family_minimum(...), 'n_unweighted_distribution': distribution, 'published': kept(...)}`.
  - `measure(inputs: Inputs) -> dict`. `self_check` runs before any curve.
  - `main(argv: list[str] | None = None) -> int`. Options, all required: `--data-dir`,
    `--run`, `--outputs-sha256`. It prints exactly one line,
    `json.dumps(result, sort_keys=True, allow_nan=False)`, and nothing else on stdout.

Output shape (key names fixed):

```text
{"complete": bool,
 "constants": {"level", "top_band", "min_band_cells", "wilson_z", "year_pairs"},
 "inputs": {"run", "outputs_sha256", "files": {<the four read files>: sha256}},
 "year_pairs": {"2022-2023" | "2023-2024": <curve>},
 "minimum": int | null,
 "n_unweighted_distribution": <its report.json entry, unchanged>,
 "published": <kept dict>}
```

`complete` is true when `minimum` is not None. Exit 0 when complete. Exit 1 when it is not,
with every curve printed (OC2). On `Refused`, print only `{"complete": false, "reason":
<fixed reason>}` and exit 2. Any other exception prints `{"complete": false, "reason":
"unexpected error"}` and exits 2. Its stderr holds the exception's type name and one
`file:line in function` line per frame from `traceback.extract_tb`, never the message.

- [ ] **Step 1: Write the failing tests**

Add `run_main(script, capsys, bundle, pin=None)`, which calls `main`, checks that stdout is
one line equal to `json.dumps(json.loads(line), sort_keys=True)`, and returns the status, the
parsed line and stderr.

- `test_kept_counts`: rows `(count, largest_year_count, dnb_label, federal_label)`
  `(1, 1, F, F)` twice, `(2, 1, T, F)` twice and `(3, 3, F, T)` twice, with minimum 2, give
  `{'rows': 6, 'support': 12, 'dnb_rows': 2, 'federal_rows': 2, 'kept_rows': 4,
  'kept_row_share': 4 / 6, 'kept_support': 10, 'kept_support_share': 10 / 12,
  'lenient_kept_rows': 2, 'kept_dnb_rows': 2, 'kept_federal_rows': 2}`. Minimum None gives
  None in the last seven keys.
- `test_lenient_count_reads_every_year`: publish 2022 Pine T1@N1, T2@N2, 2023 Rock T9@N1,
  T10@N2 (both `ROCK`), and 2024 Oak T21@N3, T22@N4 and Elm T23@N3, T24@N4. `published` of the
  checked bundle gives the two rows of `(N1, N2)` with `count` 2 and `largest_year_count` 1,
  and the two rows of `(N3, N4)` with `count` 2 and `largest_year_count` 2. `kept(rows, 2)` has
  `kept_rows` 4 and `lenient_kept_rows` 2. The `(N3, N4)` cell is in no curve.
- `test_golden_run_exits_zero`: status 0, `complete` true and `minimum` 1. Each year pair has
  `base_cells`, `testable_cells` and `recurring_cells` 56, bands `[(1, None, 56, 56)]` with
  rate 1.0, `before_downward_merge` `[(1, 1, 54, 54), (2, None, 2, 2)]`, minimum 1 and reason
  None. `constants` is `{'level': 0.9, 'top_band': 10, 'min_band_cells': 50, 'wilson_z':
  1.959963984540054, 'year_pairs': [[2022, 2023], [2023, 2024]]}`. `inputs.files` equals the
  four records. `published` is `{'rows': 56, 'support': 58, 'dnb_rows': 2, 'federal_rows': 2,
  'kept_rows': 56, 'kept_row_share': 1.0, 'kept_support': 58, 'kept_support_share': 1.0,
  'lenient_kept_rows': 0, 'kept_dnb_rows': 2, 'kept_federal_rows': 2}`.
  `n_unweighted_distribution` equals its `report.json` entry.
- `test_changed_codes_exit_one`: `publish(tmp_path, code_change_records())` gives status 1,
  `complete` false and `minimum` None. The `2022-2023` curve has 56 base and testable cells
  and 30 recurring cells, bands `[(1, None, 56, 30)]`, minimum None and reason
  `'top_band_misses_level'`. The `2023-2024` minimum is 1. `published['kept_rows']` is None.
- `test_too_few_cells_exit_one`: publish 2022 and 2023 Pine T1@N1, T2@N2. Status 1. The
  `2022-2023` curve has 2 testable and 2 recurring cells, rate 1.0, minimum None and reason
  `'too_few_testable_cells'`. The `2023-2024` curve has 2 base cells, 0 testable cells and the
  same reason.
- `test_refusal_prints_only_the_reason`: a wrong pin gives status 2 and exactly
  `{'complete': False, 'reason': 'outputs pin differs'}`.
- `test_unexpected_error_hides_its_message`: patch `script.year_cells` to raise
  `ValueError('parent:Pine T1')`. Status 2, `{'complete': False, 'reason':
  'unexpected error'}`, `'ValueError'` in stderr, and neither `'Pine'` nor `'T1'` in stdout or
  stderr.
- `test_shuffled_facility_years_give_identical_output`: forge the facility-year table with
  `frame.sample(fraction=1.0, shuffle=True, seed=7)`. The outputs without `inputs` are equal
  as `json.dumps(..., sort_keys=True)` strings.
- `test_two_runs_are_byte_identical`: two `main` calls print equal lines.
- `test_output_holds_no_identifier`: collect every key and string value of the golden output.
  None is a golden TRIFD or parent name (`'Pine'`, `'Rock'`, `'Tin'`, `'Zinc'`, `'Quartz'`),
  and none contains `'parent:'`, `'facility:'` or `NODE_PREFIX`.
- `test_writes_nothing_under_data_dir`: the sorted `(relative path, SHA-256)` list of every
  file under `data_dir` is equal before and after `main`.
- `test_runs_offline`: under `forbid_external_access(monkeypatch)`, with
  `httpx.Client.__init__` and `httpx.AsyncClient.__init__` patched to raise, `main` on the
  golden bundle returns 0.
- `test_script_imports`: parse the script with `ast`. The module of every `import` and `from`
  is in `sys.stdlib_module_names` (by its first dotted part), is `polars`, or is one of
  `embedding_data.target_contract`, `embedding_data.tri_facility_years` and
  `embedding_data.tri_parent_link_targets`. No imported name starts with `_`.
- `test_genuine_chain_bundles_pass_the_checks`: a module-scoped `v12` fixture runs
  `run_tri_v12(tmp_path_factory.mktemp('minimum-v12'), patch)` inside
  `pytest.MonkeyPatch.context()`, as `tests/test_tri_v12.py:43-50` does. `main` on each of
  the two runs with its pin returns 1, and every year pair has reason
  `'too_few_testable_cells'`. The two outputs without `inputs` are equal, and
  `inputs.files['report.json']` equals the first run's inventory record.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_tri_minimum_counts.py -v`
Expected: the earlier tests PASS. The new tests FAIL with `AttributeError` on `published`,
`kept`, `summarize` or `main`.

- [ ] **Step 3: Implement `published`, `kept`, `summarize`, `measure` and `main`**

`measure` builds `year_cells(checked.eligible, checked.counts, base)` for each base year of
`YEAR_PAIRS`, labeled `f'{base}-{later}'`. The `if __name__ == '__main__': sys.exit(main())`
guard closes the file.

- [ ] **Step 4: Run the tests and lint, and time the chain test**

Run: `uv run --locked pytest tests/test_measure_tri_minimum_counts.py -v --durations=5`
Expected: all PASS. If `test_genuine_chain_bundles_pass_the_checks` takes 60 s or more,
setup included, add its node ID to `SLOW_TESTS` in `tests/conftest.py`.
Run: `uv run --locked ruff check scripts/measure_tri_minimum_counts.py tests/test_measure_tri_minimum_counts.py`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add scripts/measure_tri_minimum_counts.py tests/test_measure_tri_minimum_counts.py
git commit -m "feat(scripts): report the Stage 22 minimum count as one JSON line"
```

Add `tests/conftest.py` to the `git add` if Step 4 changed it.

### Task 5: Rule commit and two real runs (controller only)

The controller runs this task itself, not a subagent.

**Files:** none in the repository. Outputs go to `$OUT`.

- [ ] **Step 1: Full checks**

Run the freeze-window `pgrep` check (no output), then `uv run --locked pytest`,
`uv run --locked behave` and `uv run --locked ruff check .`.
Expected: all pass, the `network` canary deselected.

- [ ] **Step 2: Review before data**

Run `git fetch origin`, then dispatch requesting-code-review over the branch
(`origin/main...HEAD`). Review against the spec's "The rule" and "What gets built" item 1 and
this plan's Review Focus. Resolve every finding and rerun Step 1. This review guards the
Anti-goal "a rule picked after seeing its result".

- [ ] **Step 3: Record the rule commit and check the pinned records**

Run: `git status --porcelain` (expected: no output), then `git rev-parse HEAD`. Keep the SHA as
the rule commit. Every real run runs at this commit, on a clean tree. Then:

```bash
D=/Users/lowell/Projects/embedding-data/data/derived/epa_tri/parent-links/stage5_tri_parent_links_20261121_r1
shasum -a 256 "$D/outputs.json"
python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['report.json']['sha256'])" "$D/outputs.json"
```

Expected: `65159b83…10b7f8b`, then `dc002222…ed98d6a6e` (the Pinned input table). Read nothing
else of the run.

- [ ] **Step 4: First real run**

```bash
OUT=$HOME/.cache/embedding-data/stage22-minimum-counts/$(git rev-parse --short HEAD)
mkdir -p "$OUT" && touch "$OUT/start"
pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'
pgrep -fl 'embedding_data|embedding-data' > "$OUT/run1.pgrep-before"; cat "$OUT/run1.pgrep-before"
```

The first `pgrep` must print nothing. Look at each line of the second. Its own shell and an
idle project Python match it. Stop if a line shows a full-data build or another full-data
measurement (spec "Constraints"). Then:

```bash
/usr/bin/time -l uv run --offline --locked python scripts/measure_tri_minimum_counts.py --data-dir /Users/lowell/Projects/embedding-data/data --run stage5_tri_parent_links_20261121_r1 --outputs-sha256 65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b > "$OUT/run1.json" 2> "$OUT/run1.time"; echo "exit $?"
pgrep -fl 'embedding_data|embedding-data' > "$OUT/run1.pgrep-after"; cat "$OUT/run1.pgrep-after"
```

In a restricted workspace, prefix `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache`.

- Exit 0: continue.
- Exit 1: stop (OC2). Report the curves of both year pairs to the owner. Change no constant.
- Exit 2: stop (OC3). Read the reason. A fix toward the written rule restarts at Step 1 with a
  new rule commit, and the decision record discloses it.

- [ ] **Step 5: Second real run and identity**

Repeat Step 4 with `run2` in place of `run1` in every file name. Then:

```bash
shasum -a 256 "$OUT/run1.json" "$OUT/run2.json"
cmp "$OUT/run1.json" "$OUT/run2.json" && echo identical
find /Users/lowell/Projects/embedding-data/data -newer "$OUT/start" -print
```

Expected: two equal digests, `identical`, and no output from `find`. Check that
`inputs.files['report.json']` in `run1.json` is `dc002222…ed98d6a6e`.

### Task 6: Decision record, spec amendments and stale lines

**Files:**
- Create: `specs/findings/v9-tri-minimum-counts.md`
- Modify: `specs/embedding-evaluation-data-spec.md` (R7.3 and V9)
- Modify: `CLAUDE.md`, `README.md`, `specs/deliverable-map.md`

Plans 17 (Stage 19) and 19 (Stage 21) also edit these shared files and append to R7.3 and V9.
Find each passage by its quoted text, never by a line number. Before Step 2:

```bash
git worktree list --porcelain
git -C /Users/lowell/Projects/embedding-data/.claude/worktrees/stage-19-wage-minimum-earners status --short
git -C /Users/lowell/Projects/embedding-data/.claude/worktrees/stage-21-usaspending-minimum-counts status --short
git -C /Users/lowell/.codex/worktrees/acs-targets-design/embedding-data status --short
git fetch origin
for b in worktree-stage-19-wage-minimum-earners worktree-stage-21-usaspending-minimum-counts codex/acs-targets-design; do git log --oneline origin/main.."$b"; git diff --stat origin/main..."$b" -- CLAUDE.md README.md specs/deliverable-map.md specs/embedding-evaluation-data-spec.md; done
git show origin/main:specs/embedding-evaluation-data-spec.md | grep -n -E -A 8 '^\*\*R7\.3\*\*|V9 — minimum cell counts'
```

Change nothing in a sibling worktree or branch. If plan 17's or plan 19's sentences have merged
into `origin/main`, merge `origin/main` into this branch (never rebase) and append after them.
If a sibling branch holds unmerged edits to the same passage, append after the last owner tag
on `origin/main` and tell the owner at Task 7 that the later merge will need a manual join.

- [ ] **Step 1: Write the decision record**

Plain technical English, beside `specs/findings/v9-ita-naics-minimum-counts.md`, with the
same section style. All values come from `$OUT/run1.json`, `$OUT/run1.time` and the two
`run1.pgrep-*` lists. Sections in order:

1. Decision: the minimum and the published column it applies to (`n_unweighted` of
   `tri_parent_links.parquet`). A minimum of 1 is a measured outcome. Both mirror rows of an
   industry pair meet or miss the gate together.
2. Rule and constants: the per-year counts, the staying and testable rule, recurrence through
   any owner, the band rule with the downward merge and the total check, the constants, and
   the rule commit from Task 5 Step 3. Disclose any fix made under OC3.
3. Inputs: the run ID, the detached pin and the four file SHA-256 values from `inputs.files`.
   The replay is not read (spec "Inputs").
4. Run: the full command, both output SHA-256 values, and the wall time and maximum RSS of
   run 1. Call the wall time "loaded" only if `run1.pgrep-after` lists another job, and name no
   process that a saved line does not hold. The output stays in `$OUT` and never enters git.
5. Curves: for each year pair, one table of `low`–`high`, base cells, testable cells,
   recurring cells, rate and Wilson interval. When `before_downward_merge` is not null, a
   second table gives those two bands. Then the year-pair minimum or its reason.
6. Kept counts: every `published` value, the kept industry pairs (half of `kept_rows`), the
   lenient kept rows and the kept rows among the rows with each sensitivity label.
7. Deviation: this plan's Deviation note (Consumes and cost).
8. Disclosure: quote the spec's Anti-goals disclosure (`specs/tri-minimum-counts.md:120-141`)
   and state that planning read no data of the run. Planning ran the frozen `estimate` on
   synthetic fixture records only.
9. Limits: the spec's nine Limits. The mirrored-cells item says that the Wilson intervals are
   too narrow, because each industry pair counts twice.
10. Not claimed: no Stage 5 bundle is rebuilt or relabeled, and `size_gate_pending` stays on
    every row. No protocol section (O17). No minimum for the marginal, support,
    parent-industry or facility-year tables, or for the cells that exist only under a
    sensitivity. No minimum for any other family. No embedder result. A row that meets the
    gate is not a true relation (spec "What recurrence measures here").

- [ ] **Step 2: Amend the spec**

Use the execution date for `<date>`. In R7.3, after the last owner tag of the paragraph
(`*(owner, plan 12, 2026-11-17)*`, or a later plan's tag if it has merged), append on the same
paragraph:

```markdown
The [V9 TRI decision](findings/v9-tri-minimum-counts.md) sets it for the TRI parent-link
family. That family is no longer among the families whose minimum stays open.
*(owner, plan 20, <date>)*
```

In V9, after the last owner tag of the item, append, indented as a list continuation:

```markdown
  The [V9 TRI decision](findings/v9-tri-minimum-counts.md) covers the TRI parent-link family
  after its first full build. *(owner, plan 20, <date>)*
```

Rollout stays unchanged (spec "What gets built", item 4).

- [ ] **Step 3: Change the stale lines**

- `CLAUDE.md`, section "TRI parent links (roadmap Stage 5)": replace the sentence (it wraps
  after `count`) ``Every target keeps `size_gate_pending`, and no headline minimum count
  (O13) exists yet.`` with ``Every target keeps `size_gate_pending`. The headline minimum
  count (O13) is in `specs/findings/v9-tri-minimum-counts.md`.``
- `README.md`, section "TRI parent links (roadmap Stage 5)": after ``The [Stage 5
  finding](specs/findings/stage-5-tri-parent-links.md) records the replay, the exact
  commands, the cost and what is not claimed.``, append ``[The V9 TRI
  decision](specs/findings/v9-tri-minimum-counts.md) sets the headline minimum count for
  `tri_parent_links` (O13). A row meets the gate when its `n_unweighted` is at least the
  minimum. The published targets keep `size_gate_pending`.``
- `specs/deliverable-map.md`, the row "EPA TRI parent links": in the Status cell, replace
  ``No count gate yet`` with ``Count gate set (Stage 22): minimum <M>, met by <k> of <r>
  rows``, from `published`. Replace the "Still blocked by" cell with ``Its section in [the
  evaluation protocol](evaluation-protocol.md) (O17). R8.4, if it trains``.

- [ ] **Step 4: Check that no frozen file changed**

```bash
git fetch origin
uv run --locked python -c "import subprocess; from embedding_data.tri_bundle import SOFTWARE_FILES; changed = set(subprocess.run(['git', 'diff', '--name-only', 'origin/main...HEAD'], capture_output=True, text=True, check=True).stdout.split()); frozen = set(SOFTWARE_FILES) | {'scripts/measure_ita_minimum_counts.py', 'tests/minimum_count_fixtures.py', 'specs/naics-evaluation-data-stage-5-findings.md', 'specs/findings/stage-5-tri-parent-links.md'}; print(sorted(changed & frozen) or 'none frozen'); print(sorted(changed))"
```

Expected: `none frozen`, then only the files of this plan's File Structure (and the plan file
itself, after the completion protocol).

- [ ] **Step 5: Commit**

```bash
git add specs/findings/v9-tri-minimum-counts.md specs/embedding-evaluation-data-spec.md CLAUDE.md README.md specs/deliverable-map.md
git commit -m "docs(specs): record the V9 TRI minimum count"
```

### Task 7: Pull request (after the Plan Completion Protocol)

Run this task last: after the final whole-branch review and after the Plan Completion
Protocol has committed its markup, roadmap tick and stamp, Handoff section, history entry and
retire commit. The spec's Rollout overrides step 1 of the standing PR rule
(`~/Projects/agent-skills/rules/pr-lifecycle.md:17`), which turns on auto-merge as soon as a
PR opens. This repository has no CI, so auto-merge would merge at once, before the owner sees
the minimum.

- [ ] **Step 1: Bring in `main`**

Run `git fetch origin`. If `origin/main` has moved, run `git merge origin/main` (never rebase)
and rerun Task 5 Step 1 (tests, Behave, ruff). Do not rerun the real runs, because the script
did not change.

- [ ] **Step 2: Push and open the PR**

Run the freeze-window `pgrep` check. Push with `git push -u origin <branch>`, then open the PR
against `main` with `gh pr create`. The body gives the minimum, the kept rows and support with
their shares, the lenient count, the link to the decision record and the R7.3 and V9
amendments, says that the owner approves before the merge, and ends with the session's PR
attribution line. Bind the PR (`ccd_pr` `get_status`, then `bind_pr` if needed). Do not turn
on Auto-fix (`set_monitor`). With no CI, it would act only on review comments, and a fix that
it pushed to the script after the rule commit would skip OC3.

- [ ] **Step 3: Stop for the owner (OC4)**

Do not call `ccd_pr` `set_auto_merge`, do not run `gh pr merge --auto`, and do not merge. Ask
the owner to approve the PR, and end the turn.

- [ ] **Step 4: Merge after approval**

Only after the owner's approval in chat or on GitHub, and while
`gh pr view <n> --json state` shows `OPEN`: run `gh pr merge <n> --merge --delete-branch`.
Never `--squash` or `--rebase`, because the decision record cites the rule commit by its SHA.

- [ ] **Step 5: Verify and clean up**

Follow steps 2 to 4 of the standing PR rule. With no CI checks, report exactly
`PR merged, remote deleted`. Clean up the worktree by the case that matches how it was made,
and end with the resume handoff, routing to no next stage.
