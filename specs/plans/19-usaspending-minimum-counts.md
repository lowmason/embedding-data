# USAspending Headline Minimum Counts Implementation Plan

**Status: COMPLETE (2026-11-23)** — executed via subagent-driven-development; deferred items in specs/deferred_items.md, or specs/completed/deferred_items.md once archived

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure fiscal-year recurrence of the Stage 14 vendor-link cells, set one headline
minimum count for `supplier_share` and one for `buyer_share` by the committed band rule,
record the decision and amend spec R7.3 and V9.

**Architecture:** One offline script, `scripts/measure_usaspending_minimum_counts.py`,
authenticates the pinned Stage 14 run by its detached pin and by the SHA-256 and size of the
four files it reads. It recounts the pooled and per-year cells from the eligible pairs and
checks the recount against the support table, the targets and `report.json` before any curve.
Then it bands the testable cells of each measure and year pair with the V9 rule, copied from
the Stage 3 script, and prints one sorted JSON line of aggregates. Tests publish tiny bundles
through the frozen `vendor_link_targets.estimate` and one genuine V12 fixture chain. The
controller runs the script twice on real data, and the decision record transcribes the output.

**Tech Stack:** Python 3.14, Polars, argparse, pytest, uv. No new dependency.

**Spec:** `specs/usaspending-minimum-counts.md` (owner-approved 2026-11-22, merged in
lowmason/embedding-data#49, `fd43236`).

> Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 21 — on plan
> completion, tick the stage and re-validate later stages against what shipped.

> Deviation: the Stage 21 Consumes line (roadmap `:272`) names only `report.json` and the
> Stage 14 findings, and the O26 cost cell (roadmap `:75`) says "one pass over the family's
> `n_unweighted` counts". Under D1 the measurement also reads `vendor_link_pairs.parquet` (the
> UEI pair table), `vendor_link_support.parquet` and `vendor_links.parquet` of the run, and it
> recomputes per-year firm counts (owner, D1, 2026-11-22; spec "Rollout").

> Deviation: the Stage 21 Exit (roadmap `:274`) names "the headline minimum count" in the
> singular. The decision gives one minimum for `supplier_share` and one for `buyer_share`,
> and it reports for each target how many rows meet its own minimum (spec "Two minimums").
> The rest of the Exit holds as written.

Roadmap line numbers are as of `fd43236`. Roadmap `:276` still says
`ROUTING: brainstorming` for Stage 21. The approved spec governs. The completion protocol ticks
the stage and puts this stamp under its entry, which cites both Deviation notes:

```text
> Stage 21: COMPLETE (<date>) — implemented by plan 19 (specs/plans/completed/19-usaspending-minimum-counts.md). Its two Deviation notes record the wider Consumes and cost and the two minimums. Its Handoff section names what O18 consumes.
> Next: resume the roadmap.
```

## Global Constraints

- **Branch.** Cut a new branch from `main` at or after the merge that lands this plan, in a
  worktree (using-git-worktrees). Merge through a PR that the owner approves, with a merge
  commit. Never rebase or squash the branch after Task 5 Step 3, because the decision record
  cites the rule commit by its SHA. Take a later `main` in by a merge, never a rebase.
- **Script frozen after Task 5 Step 4.** Once the first real run has executed, a finding
  against the script from any later review (the final whole-branch review included) follows
  OC3: only a fix toward the written rule, then both real runs again at the new commit, and
  the decision record discloses it.
- **Frozen software.** Change no file in `vendor_link_bundle.SOFTWARE_FILES`
  (`src/embedding_data/vendor_link_bundle.py:58-85`, 26 files, including `pyproject.toml` and
  `uv.lock`), the Stage 6 `FROZEN_MODULES` and `TARGET_MODULES`, the Stage 7 to 9 software,
  `cli.py` or `code_references.py`. Add no dependency, marker or console entry point. New code
  goes in `scripts/` and `tests/` only. `tests/conftest.py` may gain one `SLOW_TESTS` entry
  (Task 4).
- **Frozen records.** Do not edit `scripts/measure_ita_minimum_counts.py`,
  `scripts/reconcile_usaspending_vendor_links.py` or
  `specs/naics-evaluation-data-stage-14-findings.md`. The Stage 14 findings keep their old
  label "O18" for the minimum count.
- **Leave alone.** The bundles `stage14_vendor_links_20261121_r1`,
  `stage14_vendor_links_20261122_r2` and `stage14_vendor_links_20261122_r2_replay` under
  `data/derived/usaspending/vendor-links/`. The evidence directory
  `/Users/lowell/.cache/embedding-data/stage-20/`. The worktrees and branches
  `.claude/worktrees/stage-19-wage-minimum-earners`, `.worktrees/stage-18-tri-hardening` and
  `/Users/lowell/.codex/worktrees/acs-targets-design/embedding-data`.
- **Offline and credential-free.** The script uses no network, no `.env`, no HTTP client, no
  upstream builder and no `verify` run. Its only third-party import is `polars`. Its only
  `embedding_data` imports are `target_contract`, `usaspending_raw` (for `WINDOW`),
  `vendor_link_pairs` and `vendor_link_targets`. Importing them loads `httpx` but constructs
  no client.
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
  `MIN_BAND_CELLS = 50`, `WILSON_Z = 1.959963984540054`,
  `YEAR_PAIRS = ((2024, 2025), (2025, 2026))`. `WINDOW` (2024 to 2026), `MEASURES` and
  `INTRA_LABEL` are imported from the frozen modules, never retyped.
- **Columns read** (spec "Inputs"), each with its type from the frozen schemas
  (`vendor_link_pairs.PAIR_SCHEMA`, `vendor_link_targets.SUPPORT_SCHEMA`,
  `target_contract.TARGET_SCHEMA`):
  - `vendor_link_pairs.parquet`: `prime_uei`, `sub_uei`, `n_reports`, `n_fy2024`,
    `n_fy2025`, `n_fy2026`, `prime_node_id`, `sub_node_id`, `pair_status`.
  - `vendor_link_support.parquet`: `unit_a`, `unit_b`, `s_suppliers`, `b_buyers`, `l_pairs`,
    `l_fy2024`, `l_fy2025`, `l_fy2026`.
  - `vendor_links.parquet`: `measure`, `unit_a`, `unit_b`, `n_unweighted`, `flags`.
  - `report.json`: `n_unweighted_distribution` only.
- **Tests.** Red → green on synthetic bundles. Every test passes `--data-dir` under
  `tmp_path` and never reads the real tree. No real count from the Stage 14 findings appears in
  the script or a fixture.
- **Production root.** Only Task 5 reads real data, with
  `--data-dir /Users/lowell/Projects/embedding-data/data` passed explicitly. Nothing writes
  under `data/`. Real output goes to `$OUT` (Task 5) and never enters git.
- **Aggregates only.** R8.1 to R8.4 hold. Stdout, stderr and the decision record hold counts,
  rates, constants and pins only: no UEI, no amount and no list of cells. No embedder output,
  score or ranking is read.
- **Style.** 4-space indentation, single quotes, `'''` docstrings, ruff at 99 columns. Plan
  and record prose follows the plain technical English rule.

**Pinned input** (spec "Inputs"):

| File | Identity |
| --- | --- |
| `derived/usaspending/vendor-links/stage14_vendor_links_20261122_r2/outputs.json` | detached SHA-256 `248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be` |
| its `report.json` | inventory SHA-256 `040127fbb64d1dc7e2791f337506994092c4aab42abedfe3af94deff01f913d2` (Stage 20 finding) |
| its three read Parquet files | their records in that `outputs.json` (SHA-256 and size) |

## Review Focus

1. Ineligible pairs with null node IDs. Real pair tables hold many. Only eligible pairs need
   both node IDs, so a pair table with a `sub_ineligible` pair whose `sub_node_id` is null
   must pass every self-check (Task 3, golden bundle).
2. A firm whose only pair in FY t+1 is `sub_ineligible`, `prime_ineligible`, `intra_group` or
   `self_link` is not active in its role. Activity reads `P_{t+1}`, the eligible pairs with a
   report in t+1, never the whole pair table (Task 2).
3. A pair of a cell with `n_reports > 0` but `n_fy{t} = 0` is not in `P_t`. It neither adds to
   the base count nor makes the cell testable, even when its two firms are active in t+1
   (Task 2).
4. The lenient count uses per-year firm counts, the largest `S_t` or `B_t` over all three
   fiscal years (FY2026 included), never the support table's pair counts `l_fy{t}`. A cell
   with pooled `S = 3` and `S_t = 1` in each year is lenient at a minimum of 2 (Task 4).
5. An unexpected error whose message holds a UEI. Neither stdout nor stderr may carry it.
   Stderr gets the exception type and the frame locations only (Task 4).

## Decisions

- **D1** (owner, plan review, 2026-11-22): Approve plan 19 as committed at `dc18c5d`, with the OC1 defaults unchanged ("Approve plan 19"). Applied in: Owner Checkpoints (OC1), Global Constraints, Tasks 3 to 5.

## Owner Checkpoints

- **OC1 (plan review, settled by D1).** The defaults this plan sets where the spec or the
  brief leaves a choice:
  1. Real output goes to `$HOME/.cache/embedding-data/stage21-minimum-counts/<rule commit>/`
     (brief default, after the Stage 3 and Stage 19 precedents), outside the repository and
     outside `data/`.
  2. The script is `scripts/measure_usaspending_minimum_counts.py`. It copies the Stage 3
     band functions with its own constants, and a test pins them equal to the Stage 3 ones.
  3. Refusals that the spec does not list: a read column with another type, a target measure
     outside `MEASURES` or a cell without exactly one row of each measure, and a malformed
     `report.json`.
  4. When one measure has no minimum, the other measure's minimum and kept counts still
     print, `cells_meeting_both` is null and the exit is 1.
  5. A kept share divides by that measure's rows (rows) or by its summed `n_unweighted`
     (support).
- **OC2 (Task 5).** Exit 1, a measure whose top band misses `LEVEL` in either year pair,
  stops the stage. The owner decides. No constant changes.
- **OC3 (Task 5).** A refusal on real data stops the stage. A fix may only bring the script to
  the written rule, and the decision record discloses it. Anything else goes to the owner.

## File Structure

| File | Responsibility |
| --- | --- |
| `scripts/measure_usaspending_minimum_counts.py` (create) | Constants, band rule, per-year counts, authentication, self-checks, kept counts, CLI |
| `tests/test_measure_usaspending_minimum_counts.py` (create) | All tests and the small-bundle helpers. Loads the script with `importlib`, as `tests/test_measure_ita_minimum_counts.py:21-34` does |
| `tests/conftest.py` (modify, only if Task 4 Step 4 says so) | One `SLOW_TESTS` entry |
| `specs/findings/v9-usaspending-minimum-counts.md` (create) | The decision record |
| `specs/embedding-evaluation-data-spec.md` (modify) | R7.3 and V9 amendments |
| `CLAUDE.md`, `README.md`, `specs/deliverable-map.md` (modify) | Stale O26 lines |

---

### Task 1: Rule constants and band functions

**Files:**
- Create: `scripts/measure_usaspending_minimum_counts.py`
- Test: `tests/test_measure_usaspending_minimum_counts.py`

**Interfaces:**
- Produces, in the script module:
  - The constants of Global Constraints, `COUNTS = ('base_cells', 'testable_cells',
    'recurring_cells')`, and `MEASURES` and `WINDOW` imported unchanged.
  - Copied unchanged in behavior from `scripts/measure_ita_minimum_counts.py:76-162`:
    `wilson(recurring: int, testable: int) -> tuple[float, float] | None`,
    `raw_counts(cells: pl.DataFrame) -> dict[int, dict]`,
    `close_band(pending: dict, high: int | None) -> dict`,
    `bands(cells: pl.DataFrame) -> list[dict]`,
    `pair_minimum(bands: list[dict]) -> int | None`, and
    `measure_minimum(minimums: list[int | None]) -> int | None` (Stage 3's `family_minimum`).
  - A **cells frame** has `base_count` (UInt64), `testable` and `recurs` (Boolean), one row
    per base cell. A **band** is `{'low', 'high', 'base_cells', 'testable_cells',
    'recurring_cells', 'rate', 'wilson_low', 'wilson_high'}`, as in Stage 3.

- [x] **Step 1: Write the failing tests**

Add `load_script()` (copy `tests/test_measure_ita_minimum_counts.py:24-29`, script path
`scripts/measure_usaspending_minimum_counts.py`, assertion message
`'measurement script is missing'`), a `script` fixture, `cells(*groups)` and `band(low, high,
rate)` (copy `:37-56`).

```python
def test_rule_constants_are_the_committed_values(script):
    assert (script.LEVEL, script.TOP_BAND, script.MIN_BAND_CELLS) == (0.90, 10, 50)
    assert script.WILSON_Z == 1.959963984540054
    assert script.YEAR_PAIRS == ((2024, 2025), (2025, 2026))
    assert script.MEASURES == ('supplier_share', 'buyer_share')
```

- `test_bands_merge_short_bands_upward`: the frame and expected bands of
  `tests/test_measure_ita_minimum_counts.py:64-70`.
- `test_empty_top_band_gives_no_minimum`: `cells((1, 60, 60, 0))` gives bands
  `[(1, 1, 60), (2, None, 0)]` as `(low, high, testable_cells)`, the last with `rate` None,
  and `pair_minimum` None.
- `test_rate_equal_to_level_passes`: `cells((1, 50, 45, 0), (10, 50, 45, 0))` gives
  `pair_minimum` 1. `cells((1, 50, 44, 0), (10, 50, 45, 0))` gives 2.
- `test_pair_minimum_is_start_of_trailing_passing_run`: bands with rates 0.95, 0.5, 0.95,
  0.95 and lows 1, 2, 3, 10 give 3. All four at 0.95 give 1.
- `test_untestable_cells_never_count_as_recurring`: a frame of 60 cells with `base_count` 1,
  `testable` false and `recurs` true (built directly, since `cells` cannot express it) gives
  one band `(1, None)` with `base_cells` 60, `testable_cells` 0 and `recurring_cells` 0.
- `test_measure_minimum_is_largest_and_needs_every_pair`: `[1, 3]` gives 3, `[2, None]` and
  `[]` give None.
- `test_band_rule_matches_stage_3`: load `scripts/measure_ita_minimum_counts.py` inside the
  test with `importlib` under the module name `stage3_measure`. For each frame of the tests
  above, `script.bands(frame) == stage3.bands(frame)` and the two `pair_minimum` results are
  equal. `script.measure_minimum(m) == stage3.family_minimum(m)` for the three lists above.

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_usaspending_minimum_counts.py -v`
Expected: FAIL with "measurement script is missing".

- [x] **Step 3: Implement the constants and the band functions**

The module docstring states the rule in three sentences, cites
`specs/usaspending-minimum-counts.md` and says that the band functions are copied from the
Stage 3 script so that the Stage 21 constants govern. Define
`YEAR_PAIRS = tuple(zip(WINDOW, WINDOW[1:]))`.

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_measure_usaspending_minimum_counts.py -v`
Expected: all PASS.

- [x] **Step 5: Commit**

```bash
git add scripts/measure_usaspending_minimum_counts.py tests/test_measure_usaspending_minimum_counts.py
git commit -m "feat(scripts): add the Stage 21 band rule"
```

> Deviation: the task review found three gaps in the mutant step (no `WILSON_Z` mutant, none
> for "the interval does not enter the rule", no `[None, 3]` shape). A fix round added mutants
> 31 to 33 and one test, in a second commit `ce029e0`
> (`test(scripts): cover a missing minimum in either year pair`).

### Task 2: Per-year counts, testable cells and recurrence

**Files:**
- Modify: `scripts/measure_usaspending_minimum_counts.py`
- Test: `tests/test_measure_usaspending_minimum_counts.py`

**Interfaces:**
- Consumes in the tests (unchanged): `vendor_link_pairs.PAIR_SCHEMA`, `FIRM_STATUSES` and
  `validate_pairs`, and `vendor_link_codes.NODE_PREFIX`.
- Produces in the test file, copied from `tests/test_vendor_link_targets.py:46-111`:
  `node(code: str) -> str`, `uei(name: str) -> str`, `link(prime, sub, *, intra=False,
  fy=(1, 0, 0), amount='0.00') -> dict` and `pair_frame(firms: dict[str, str], *links) ->
  pl.DataFrame`. `firms` maps a firm name to a six-digit code or to an ineligible firm status.
- Produces in the script:
  - `eligible_pairs(pairs: pl.LazyFrame) -> pl.LazyFrame`: the pairs with `pair_status`
    `'eligible'` (`vendor_link_pairs.PAIR_STATUSES[-1]`), with `prime_uei`, `sub_uei`,
    `unit_a` (from `sub_node_id`), `unit_b` (from `prime_node_id`) and `n_fy2024` to
    `n_fy2026`.
  - `pooled_counts(eligible: pl.LazyFrame) -> pl.DataFrame`: `unit_a`, `unit_b`,
    `s_suppliers`, `b_buyers`, `l_pairs` (UInt64), sorted by cell.
  - `year_counts(eligible: pl.LazyFrame) -> pl.DataFrame`: `unit_a`, `unit_b`, `year`
    (Int64), `s`, `b`, `l` (UInt64), one row for each cell and year of `WINDOW` with `l ≥ 1`,
    sorted by `unit_a`, `unit_b`, `year`.
  - `cells(eligible: pl.LazyFrame, base: int) -> dict[str, pl.DataFrame]`: for each measure,
    the cells frame of the base cells of FY `base` with `unit_a` and `unit_b` too, sorted by
    cell. `base_count` is `s` for `supplier_share` and `b` for `buyer_share`. `testable` and
    `recurs` are equal across the two measures.

Rule (spec "The rule"): `P_t` is the eligible pairs with `n_fy{t} > 0`. A base cell of FY t
has a pair in `P_t`. It recurs when a pair of `P_{t+1}` has the same cell. It is testable when
one of its `P_t` pairs has a subcontractor that is the subcontractor of some `P_{t+1}` pair
and a prime that is the prime of some `P_{t+1}` pair. Mark each `P_t` pair active with two
semi-joins against the distinct `sub_uei` and `prime_uei` of `P_{t+1}`, then group by cell.

- [x] **Step 1: Write the failing tests**

Use `S, D, E = '541512', '541511', '236220'` and `FIRMS = {'P1': D, 'P2': D, 'P3': E,
'U1': S, 'U2': S, 'U3': E, 'X': 'not_in_sam'}`. A cell `(node(S), node(D))` is written `SD`.
`A–B (f24, f25, f26)` is `link('A', 'B', fy=(f24, f25, f26))`, so `A` is the prime. "An
intra-group `A–B`" adds `intra=True`.

- `test_year_counts_follow_each_fiscal_year`: links `P1–U1 (1, 1, 0)`, `P1–U2 (1, 0, 0)` and
  `P2–U1 (0, 0, 2)` give `year_counts` rows `(SD, 2024, s 2, b 1, l 2)`,
  `(SD, 2025, 1, 1, 1)` and `(SD, 2026, 1, 1, 1)`, and `pooled_counts` `(SD, 2, 2, 3)`.
- `test_only_eligible_pairs_are_counted`: adding `P1–X (1, 1, 1)` and an intra-group
  `P2–U2 (1, 1, 1)` leaves both frames of the test above unchanged.
- `test_same_pair_recurs`: `P1–U1 (1, 1, 0)` gives one 2024 `supplier_share` cell with
  `base_count` 1, `testable` and `recurs` true.
- `test_subcontractor_that_is_only_a_prime_next_year_is_not_testable`: `P1–U1 (1, 0, 0)`,
  `U1` as the prime of `U1–U3 (0, 1, 0)` and `P1–U3 (0, 1, 0)` give `SD` in 2024 with
  `testable` and `recurs` false.
- `test_both_firms_active_elsewhere_is_testable_without_recurring`: `P1–U1 (1, 0, 0)`,
  `P1–U3 (0, 1, 0)` and `P3–U1 (0, 1, 0)` give `SD` in 2024 with `testable` true and `recurs`
  false.
- `test_activity_through_an_ineligible_pair_does_not_count`: `P1–U1 (1, 0, 0)`, an intra-group
  `P3–U1 (0, 1, 0)` and `P1–X (0, 1, 0)` give `SD` in 2024 with `testable` false.
- `test_pair_without_a_base_year_report_is_not_in_the_base_year`: `P1–U1 (0, 1, 1)`,
  `P2–U2 (1, 0, 0)` and `P3–U3 (0, 1, 0)` give, for 2024, exactly one cell, `SD`, with
  `supplier_share` `base_count` 1, `testable` false and `recurs` true.
- `test_each_measure_takes_its_own_base_count`: `P1–U1 (1, 1, 0)` and `P1–U2 (1, 1, 0)` give
  `SD` in 2024 with `base_count` 2 for `supplier_share` and 1 for `buyer_share`, and equal
  `testable` and `recurs`.
- `test_second_year_pair_reads_fy2025_and_fy2026`: `P1–U1 (0, 1, 1)` gives no 2024 cell and,
  for 2025, `SD` with `testable` and `recurs` true.

Each test builds `eligible_pairs(pair_frame(firms, *links).lazy())`.

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_usaspending_minimum_counts.py -v`
Expected: the Task 1 tests PASS. The new tests FAIL with
`AttributeError: ... has no attribute 'eligible_pairs'`.

- [x] **Step 3: Implement `eligible_pairs`, `pooled_counts`, `year_counts` and `cells`**

Firm counts use `n_unique` of the UEI cast to UInt64, as `vendor_link_targets._support`
(`src/embedding_data/vendor_link_targets.py:103-112`) counts them. Sort every result, so group
order never reaches the output.

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_measure_usaspending_minimum_counts.py -v`
Expected: all PASS.

- [x] **Step 5: Commit**

```bash
git add scripts/measure_usaspending_minimum_counts.py tests/test_measure_usaspending_minimum_counts.py
git commit -m "feat(scripts): count vendor-link cells by fiscal year"
```

### Task 3: Small bundles, authentication and self-checks

**Files:**
- Modify: `scripts/measure_usaspending_minimum_counts.py`
- Test: `tests/test_measure_usaspending_minimum_counts.py`

**Interfaces:**
- Consumes in the tests (unchanged): `vendor_link_targets.estimate`,
  `vendor_link_bundle.TABLES` and `FILES`, `target_io.inventory` and `write_json`, and
  `manifest.sha256_file`.
- Produces in the test file:
  - `golden_links()`, over the `FIRMS` of Task 2: `P1–U1 (1, 1, 1)`,
    `P1–U2 (1, 1, 0)`, `P2–U3 (2, 1, 1)`, `P2–X (1, 0, 0)` (a `sub_ineligible` pair with a
    null `sub_node_id`) and an intra-group `P2–U1 (1, 0, 0)`. Its cells are `SD` and `ED`.
    Every base cell of both year pairs is testable and recurs. The `buyer_share` row of `SD`
    carries `INTRA_LABEL`.
  - `failing_links()`: `P1–U1 (1, 0, 0)`, `P1–U3 (0, 1, 1)` and `P3–U1 (0, 1, 1)`. Its one
    2024 base cell is testable and does not recur. Both 2025 base cells are testable and
    recur.
  - `publish(root: Path, links: list[dict], *, firms=FIRMS, run='fixture') -> dict`: builds
    `pair_frame(firms, *links)`, runs `estimate(table, snapshot=date(2026, 11, 19),
    month='2026-10')`, and writes `root/'data'/'derived/usaspending/vendor-links'/run/` with
    the four tables under their `TABLES` names, `report.json` (the estimate's report),
    `inputs.json` (`{}`) and `outputs.json` (`target_io.inventory(directory, list(FILES))`).
    Returns `{'data_dir', 'directory', 'run', 'pin'}`.
  - `rehash(directory: Path) -> str`, `forge_table(bundle: dict, name: str, change) -> str` and
    `forge_report(bundle: dict, change) -> str`. Each forge applies `change` to one file,
    rewrites `outputs.json` from the inventory and returns the new pin, so the script trusts
    the changed file and a self-check must find the change.
- Produces in the script:
  - `class Refused(Exception)`, whose message is a fixed reason.
  - `@dataclass(frozen=True) class Inputs` with `directory: Path`, `outputs_sha256: str` and
    `files: dict[str, str]`, the SHA-256 of each of the four read files.
  - `authenticate(data_dir: Path, run_id: str, pin: str) -> Inputs`. The run directory is
    `data_dir / 'derived/usaspending/vendor-links' / run_id`.
  - `@dataclass(frozen=True) class Checked` with `eligible: pl.LazyFrame`, `years:
    pl.DataFrame`, `targets: pl.DataFrame` and `distributions: dict[str, dict]` (the report
    entries).
  - `self_check(inputs: Inputs) -> Checked`.

Checks in order, each with its fixed reason. A later check never runs when an earlier one
refuses.

1. The run ID matches `[A-Za-z0-9][A-Za-z0-9_-]*` and the pin `[0-9a-f]{64}`, both with
   `fullmatch`: `'unsafe run id or pin'`.
2. `outputs.json` exists and its SHA-256 equals the pin: `'outputs pin differs'`.
3. In the order `report.json`, `vendor_link_pairs.parquet`, `vendor_link_support.parquet`,
   `vendor_links.parquet`: the file exists and has a record in `outputs.json`, and its SHA-256
   and its size equal that record: `'<name> differs from its inventory'`. Hash only these four
   files, with `hashlib.file_digest`. Do not call `target_io.verify_inventory`, which reads
   every file of the run.
4. Each Parquet holds every read column with its frozen type:
   `'<name> columns differ from the contract'`.
5. `(prime_uei, sub_uei)` is unique over the whole pair table: `'pair keys are not unique'`.
6. Every eligible pair has a non-null `prime_node_id` and `sub_node_id`:
   `'an eligible pair lacks a node'`. Ineligible pairs are not checked.
7. Every eligible pair has `n_reports == n_fy2024 + n_fy2025 + n_fy2026`:
   `'pair report counts differ from their fiscal years'`.
8. `pooled_counts` equals the support table's cells and `s_suppliers`, `b_buyers` and
   `l_pairs`: `'pooled recount differs from the support table'`.
9. For every support cell and year of `WINDOW`, `year_counts`' `l` (0 when absent) equals
   `l_fy{t}`: `'fiscal-year recount differs from the support table'`.
10. Every target `measure` is in `MEASURES`. For each measure, its rows' `(unit_a, unit_b,
    n_unweighted)`, sorted, equal the support's `(unit_a, unit_b, s_suppliers)` for
    `supplier_share` and `(unit_a, unit_b, b_buyers)` for `buyer_share`:
    `'target rows differ from the support table'`.
11. `report.json` is a JSON object whose `n_unweighted_distribution` is an object with
    exactly the keys of `MEASURES`, each an object: `'report is malformed'`.
12. For each measure, `json.loads(json.dumps(_distribution(series)))` equals its report
    entry, where `series` is that measure's `n_unweighted`, named `n_unweighted`:
    `'report distribution differs from the targets'`. The round trip makes a float median
    compare equal to its JSON form.

- [x] **Step 1: Write the helpers and the failing tests**

Add a `golden` fixture, `publish(tmp_path, golden_links())`.

- `test_authenticate_returns_pinned_files`: `inputs.outputs_sha256 == golden['pin']`, and
  `inputs.files` equals the `sha256` of the four records in `outputs.json`.
- `test_unsafe_run_id_or_pin_refused`, parametrized over run `'../fixture'`, `'fixture/'`,
  `'-fixture'`, `'fixture\n'`, and pins `'A' * 64` and `'0' * 63`. Reason
  `'unsafe run id or pin'`.
- `test_wrong_or_missing_pin_refused`: pin `'0' * 64`, and a deleted `outputs.json`. Reason
  `'outputs pin differs'`.
- `test_changed_file_refused`, parametrized over the four read files: append one byte and do
  not rehash. Reason `'<name> differs from its inventory'`.
- `test_size_is_checked`: set the pair table record's `size` to size + 1 in `outputs.json`,
  keep its `sha256` and pass the SHA-256 of the edited `outputs.json`. Reason
  `'vendor_link_pairs.parquet differs from its inventory'`.
- `test_missing_record_refused`: delete the support record from `outputs.json`, then pass its
  new SHA-256. Reason `'vendor_link_support.parquet differs from its inventory'`.
- `test_pin_is_checked_before_files`: a changed pair table and a wrong pin give
  `'outputs pin differs'`.
- `test_unread_files_are_never_read`: append bytes to `inputs.json` and
  `vendor_link_marginals.parquet` without a rehash. `self_check(authenticate(...))` passes.
- `test_retyped_or_missing_column_refused`, parametrized: `n_fy2025` cast to Int64 in the pair
  table, and `l_fy2026` dropped from the support table. Reasons from check 4.
- `test_golden_passes_with_a_null_ineligible_node`: `self_check` of the golden bundle returns
  a `Checked`, although `P2–X` has a null `sub_node_id`.
- `test_self_check_refusals`, parametrized over a forge and its reason (checks 5 to 12): a
  duplicated pair row; a null `sub_node_id` on `P1–U1`; `n_reports` plus 1 on `P1–U1`; a
  dropped support row; `s_suppliers` plus 1; `l_fy2025` plus 1 on `SD` (check 8 passes and
  check 9 refuses); a `supplier_share` `n_unweighted` plus 1; a dropped `buyer_share` row; one
  row's `measure` set to `'other_share'`; `n_unweighted_distribution` deleted; the
  `buyer_share` entry deleted; `buyer_share` `max` plus 1.

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_usaspending_minimum_counts.py -v`
Expected: the earlier tests PASS. The new tests FAIL with
`AttributeError: ... has no attribute 'authenticate'`.

- [x] **Step 3: Implement `Refused`, `Inputs`, `authenticate`, `Checked` and `self_check`**

Scan each Parquet lazily for its read columns only. Collect the support and target tables,
which are small, and keep the pair table lazy until `eligible_pairs`.

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_measure_usaspending_minimum_counts.py -v`
Expected: all PASS.

- [x] **Step 5: Commit**

```bash
git add scripts/measure_usaspending_minimum_counts.py tests/test_measure_usaspending_minimum_counts.py
git commit -m "feat(scripts): authenticate and recount the Stage 14 vendor-link bundle"
```

### Task 4: Kept counts, the result and the command line

**Files:**
- Modify: `scripts/measure_usaspending_minimum_counts.py`
- Modify: `tests/conftest.py` (only if Step 4 says so)
- Test: `tests/test_measure_usaspending_minimum_counts.py`

**Interfaces:**
- Consumes: everything above. In the tests: `vendor_link_fixtures.run_vendor_link_v12` and
  `target_fixtures.forbid_external_access`.
- Produces:
  - `published(targets: pl.DataFrame, years: pl.DataFrame) -> dict[str, pl.DataFrame]`: for
    each measure, one row per target row with `unit_a`, `unit_b`, `count` (`n_unweighted`),
    `largest_year_count` (the largest `s` for `supplier_share` or `b` for `buyer_share` over
    the cell's `year_counts` rows) and `intra_group` (`flags` contains `INTRA_LABEL`).
  - `kept(rows: pl.DataFrame, minimum: int | None) -> dict` with keys `rows`, `support` (sum
    of `count`), `intra_group_rows`, `kept_rows`, `kept_row_share`, `kept_support`,
    `kept_support_share`, `lenient_kept_rows` (kept with `largest_year_count < minimum`) and
    `kept_intra_group_rows`. A row is kept when `count >= minimum`. With `minimum` None, the
    last six keys are None.
  - `curve(cells: pl.DataFrame) -> dict`: the summed `COUNTS`, `bands` and `minimum`, as
    `scripts/measure_ita_minimum_counts.py:582-589`.
  - `summarize(year_pair_cells: dict[str, dict[str, pl.DataFrame]], rows: dict[str,
    pl.DataFrame], distributions: dict[str, dict]) -> dict`. `year_pair_cells[measure]` maps
    `'2024-2025'` and `'2025-2026'` to cells frames. It returns `{'measures': {...},
    'cells_meeting_both': int | None}`. `cells_meeting_both` counts the cells whose two rows
    are both kept, None when either minimum is None.
  - `measure(inputs: Inputs) -> dict`. `self_check` runs before any curve.
  - `main(argv: list[str] | None = None) -> int`. Options, all required: `--data-dir`,
    `--run`, `--outputs-sha256`. It prints exactly one line,
    `json.dumps(result, sort_keys=True, allow_nan=False)`, and nothing else on stdout.

Output shape (key names fixed):

```text
{"complete": bool,
 "constants": {"level", "top_band", "min_band_cells", "wilson_z", "year_pairs"},
 "inputs": {"run", "outputs_sha256", "files": {<the four read files>: sha256}},
 "measures": {"supplier_share" | "buyer_share": {
     "year_pairs": {"2024-2025" | "2025-2026": <curve>},
     "minimum": int | null,
     "n_unweighted_distribution": <its report.json entry, unchanged>,
     "published": <kept dict>}},
 "cells_meeting_both": int | null}
```

`complete` is true when both minimums are not None. Exit 0 when complete. Exit 1 when it is
not, with every curve printed (OC2). On `Refused`, print only `{"complete": false, "reason":
<fixed reason>}` and exit 2. Any other exception prints `{"complete": false, "reason":
"unexpected error"}` and exits 2. Its stderr holds the exception's type name and one
`file:line in function` line per frame from `traceback.extract_tb`, never the message.

- [x] **Step 1: Write the failing tests**

Add `run_main(script, capsys, bundle, pin=None)`, which calls `main`, checks that stdout is
one line equal to `json.dumps(json.loads(line), sort_keys=True)`, and returns the status, the
parsed line and stderr.

- `test_kept_counts`: rows `(count, largest_year_count, intra_group)` `(1, 1, F)`,
  `(2, 1, T)`, `(3, 3, F)`, `(5, 2, T)` and minimum 2 give `{'rows': 4, 'support': 11,
  'intra_group_rows': 2, 'kept_rows': 3, 'kept_row_share': 0.75, 'kept_support': 10,
  'kept_support_share': 10 / 11, 'lenient_kept_rows': 1, 'kept_intra_group_rows': 2}`.
  Minimum None gives None in the last six keys.
- `test_lenient_count_uses_firm_counts_of_every_year`: publish with
  `firms=FIRMS | {'U4': S, 'U5': S, 'U6': S}` and links `P1–U1 (1, 0, 0)`, `P1–U2 (0, 1, 0)`,
  `P1–U6 (0, 0, 1)` (cell `SD`) and `P3–U4 (1, 0, 1)`, `P3–U5 (0, 0, 1)` (cell `SE`).
  `published` of the checked bundle gives `supplier_share` rows `(SD, count 3, largest 1)` and
  `(SE, count 2, largest 2)`. `kept(..., 2)` of those rows has `lenient_kept_rows` 1.
- `test_two_measures_get_different_minimums`: `summarize` with, for both year pairs,
  `supplier_share` cells `cells((1, 100, 0, 0), (10, 60, 60, 0))` and `buyer_share` cells
  `cells((1, 100, 100, 0), (10, 60, 60, 0))`, rows for the cells `('a', 'x')`, `('b', 'x')`
  and `('c', 'x')` with supplier counts 1, 2, 5 and buyer counts 1, 1, 1 (`largest_year_count`
  equal to the count, `intra_group` false), and empty distributions, gives minimums 2 and 1,
  supplier `kept_rows` 2, buyer `kept_rows` 3 and `cells_meeting_both` 2.
- `test_one_measure_without_a_minimum`: as above, but `buyer_share` 2025-2026 cells
  `cells((1, 100, 100, 0), (10, 60, 30, 0))`. Buyer minimum None, buyer `kept_rows` None,
  supplier minimum 2 with its kept counts, `cells_meeting_both` None.
- `test_golden_run_exits_zero`: status 0, `complete` true, both minimums 1, each curve one
  band `(1, None)` with base, testable and recurring cells 2, 2, 2, `constants` equal to
  `{'level': 0.9, 'top_band': 10, 'min_band_cells': 50, 'wilson_z': 1.959963984540054,
  'year_pairs': [[2024, 2025], [2025, 2026]]}`, `inputs.files` equal to the four records,
  `supplier_share` `published` with `rows` 2, `support` 3, `intra_group_rows` 0, `kept_rows`
  2 and `lenient_kept_rows` 0, `buyer_share` `published` with `rows` 2, `support` 2,
  `intra_group_rows` 1 and `kept_intra_group_rows` 1, `cells_meeting_both` 2, and each
  `n_unweighted_distribution` equal to its `report.json` entry.
- `test_failing_top_band_exits_one`: `publish(tmp_path, failing_links())` gives status 1,
  `complete` false, both minimums None, a `2024-2025` curve of one band with 1 testable and 0
  recurring cells and minimum None, a `2025-2026` minimum 1, and `cells_meeting_both` None.
- `test_refusal_prints_only_the_reason`: a wrong pin gives status 2 and exactly
  `{'complete': False, 'reason': 'outputs pin differs'}`.
- `test_unexpected_error_hides_its_message`: patch `script.year_counts` to raise
  `ValueError(uei('P1'))`. Status 2, `{'complete': False, 'reason': 'unexpected error'}`,
  `'ValueError'` in stderr, and `uei('P1')` in neither stdout nor stderr.
- `test_shuffled_pairs_give_identical_output`: forge the pair table with
  `frame.sample(fraction=1.0, shuffle=True, seed=7)`. The outputs without `inputs` are equal
  as `json.dumps(..., sort_keys=True)` strings.
- `test_two_runs_are_byte_identical`: two `main` calls print equal lines.
- `test_output_holds_no_uei_amount_or_cell`: the output line holds no golden UEI and no
  `vendor_link_codes.NODE_PREFIX`, so it lists no cell, and no key anywhere contains `uei` or
  `amount`.
- `test_writes_nothing_under_data_dir`: the sorted `(relative path, SHA-256)` list of every
  file under `data_dir` is equal before and after `main`.
- `test_runs_offline`: under `forbid_external_access(monkeypatch)`, with
  `httpx.Client.__init__` and `httpx.AsyncClient.__init__` patched to raise, `main` on the
  golden bundle returns 0.
- `test_script_imports`: parse the script with `ast`. The module of every `import` and
  `from` is in `sys.stdlib_module_names` (by its first dotted part), is `polars`, or is one of
  `embedding_data.target_contract`,
  `embedding_data.usaspending_raw`, `embedding_data.vendor_link_pairs` and
  `embedding_data.vendor_link_targets`.
- `test_genuine_chain_bundles_pass_the_checks`: a module-scoped `v12` fixture runs
  `run_vendor_link_v12(tmp_path_factory.mktemp('minimum-v12'), patches)` inside
  `pytest.MonkeyPatch.context()`, after `tests/test_reconcile_usaspending_vendor_links.py:52-58`
  but not autouse. `main` on each of the two runs with its pin returns 0 or 1, never 2. The
  two outputs without `inputs` are equal, and `inputs.files['report.json']` equals the first
  run's inventory record.

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_usaspending_minimum_counts.py -v`
Expected: the earlier tests PASS. The new tests FAIL with `AttributeError` on `published`,
`kept`, `summarize` or `main`.

- [x] **Step 3: Implement `published`, `kept`, `curve`, `summarize`, `measure` and `main`**

`measure` calls `cells(checked.eligible, base)` for each base year of `YEAR_PAIRS`. The
`if __name__ == '__main__': sys.exit(main())` guard closes the file.

- [x] **Step 4: Run the tests and lint, and time the chain test**

Run: `uv run --locked pytest tests/test_measure_usaspending_minimum_counts.py -v --durations=5`
Expected: all PASS. If `test_genuine_chain_bundles_pass_the_checks` takes 60 s or more,
setup included, add its node ID to `SLOW_TESTS` in `tests/conftest.py`.
Run: `uv run --locked ruff check scripts/measure_usaspending_minimum_counts.py tests/test_measure_usaspending_minimum_counts.py`
Expected: `All checks passed!`

- [x] **Step 5: Commit**

```bash
git add scripts/measure_usaspending_minimum_counts.py tests/test_measure_usaspending_minimum_counts.py
git commit -m "feat(scripts): report the Stage 21 minimum counts as one JSON line"
```

Add `tests/conftest.py` to the `git add` if Step 4 changed it.

### Task 5: Rule commit and two real runs (controller only)

The controller runs this task itself, not a subagent.

**Files:** none in the repository. Outputs go to `$OUT`.

- [x] **Step 1: Full checks**

Run the freeze-window `pgrep` check (no output), then `uv run --locked pytest`,
`uv run --locked behave` and `uv run --locked ruff check .`.
Expected: all pass, the `network` canary deselected.

> Deviation: the full suite ran through the repository's xdist overlay (the commit hook's
> command), not a bare `uv run --locked pytest`, because a serial run takes hours. It ran
> at the same time as Step 2's pre-data review, with the tree kept quiet. Result at
> `588ae5a`: ruff pass, behave 2 scenarios pass, pytest 8666 passed.

- [x] **Step 2: Review before data**

Run `git fetch origin`, then dispatch requesting-code-review over the branch
(`origin/main...HEAD`). Review against the spec's
"The rule" and "What gets built" item 1 and this plan's Review Focus. Resolve every finding
and rerun Step 1. This review guards the Anti-goal "a rule picked after seeing its result".

- [x] **Step 3: Record the rule commit and check the pinned records**

Run: `git status --porcelain` (expected: no output), then `git rev-parse HEAD`. Keep the SHA as
the rule commit. Every real run runs at this commit, on a clean tree. Then:

```bash
D=/Users/lowell/Projects/embedding-data/data/derived/usaspending/vendor-links/stage14_vendor_links_20261122_r2
shasum -a 256 "$D/outputs.json"
python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['report.json']['sha256'])" "$D/outputs.json"
```

Expected: `248943dc…a7a2be`, then `040127fb…01f913d2` (the Pinned input table). Read nothing
else of the run.

- [x] **Step 4: First real run**

```bash
OUT=$HOME/.cache/embedding-data/stage21-minimum-counts/$(git rev-parse --short HEAD)
mkdir -p "$OUT" && touch "$OUT/start"
pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'
pgrep -fl 'embedding_data|embedding-data'
```

The first `pgrep` must print nothing. Look at each line of the second. Its own shell and an
idle project Python match it. Stop if a line shows a full-data build or another full-data
measurement (spec "Constraints"). Then:

```bash
/usr/bin/time -l uv run --offline --locked python scripts/measure_usaspending_minimum_counts.py --data-dir /Users/lowell/Projects/embedding-data/data --run stage14_vendor_links_20261122_r2 --outputs-sha256 248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be > "$OUT/run1.json" 2> "$OUT/run1.time"; echo "exit $?"
```

In a restricted workspace, prefix `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache`.

- Exit 0: continue.
- Exit 1: stop (OC2). Report both measures' curves to the owner. Change no constant.
- Exit 2: stop (OC3). Read the reason. A fix toward the written rule restarts at Step 1 with a
  new rule commit, and the decision record discloses it.

- [x] **Step 5: Second real run and identity**

Repeat the run command of Step 4 with `run2.json` and `run2.time`. Then:

```bash
shasum -a 256 "$OUT/run1.json" "$OUT/run2.json"
cmp "$OUT/run1.json" "$OUT/run2.json" && echo identical
find /Users/lowell/Projects/embedding-data/data -newer "$OUT/start" -print
```

Expected: two equal digests, `identical`, and no output from `find`. Check that
`inputs.files['report.json']` in `run1.json` is `040127fb…01f913d2`.

### Task 6: Decision record, spec amendments and stale lines

**Files:**
- Create: `specs/findings/v9-usaspending-minimum-counts.md`
- Modify: `specs/embedding-evaluation-data-spec.md` (R7.3 and V9)
- Modify: `CLAUDE.md`, `README.md`, `specs/deliverable-map.md`

Plans 17 and 18 also edit `CLAUDE.md`, and plan 17 appends to R7.3 and V9. Find each passage
by its quoted text, never by a line number. Before Step 2, run `git fetch origin` and read
R7.3 and V9 in `git show origin/main:specs/embedding-evaluation-data-spec.md`. If plan 17's
sentences have merged, merge `origin/main` into the branch (never rebase) and append after
them.

- [x] **Step 1: Write the decision record**

Plain technical English, beside `specs/findings/v9-ita-naics-minimum-counts.md`, with the
same section style. All values come from `$OUT/run1.json` and `$OUT/run1.time`. Sections in
order:

1. Decision: a table of the two measures, each minimum, and the published column it applies
   to (`n_unweighted` of that measure's rows in `vendor_links.parquet`). A minimum of 1 is a
   measured outcome. The two rows of one cell are separate targets.
2. Rule and constants: the per-year counts, the role-fixed testable rule, recurrence through
   any eligible pair (D2), the band rule, the five constants, and the rule commit from Task 5
   Step 3. Disclose any fix made under OC3.
3. Inputs: the run ID, the detached pin and the four file SHA-256 values from `inputs.files`.
   The replay is not read (spec "Inputs").
4. Run: the full command, both output SHA-256 values, and the wall time and maximum RSS of
   run 1. The output stays in `$OUT` and never enters git.
5. Curves: for each measure and year pair, one table of `low`–`high`, base cells, testable
   cells, recurring cells, rate and Wilson interval, then the year-pair minimum.
6. Kept counts: for each measure, every `published` value, the lenient kept rows and the
   kept rows among the intra-group rows. Then `cells_meeting_both`.
7. Deviations: this plan's two Deviation notes (Consumes and cost, and the singular Exit).
8. Disclosure: quote the spec's Anti-goals disclosure
   (`specs/usaspending-minimum-counts.md:109-123`) and state that planning read no data of the
   run.
9. Limits: the spec's nine Limits.
10. Not claimed: no Stage 14 bundle is rebuilt or relabeled, and `size_gate_pending` stays on
    every row. No protocol section (O18). No minimum for the marginal, support or pair
    tables, for the 7 cells only under the sensitivity, or for any other family (TRI is O13).
    No embedder result.

- [x] **Step 2: Amend the spec**

Use the execution date for `<date>`. In R7.3, after the last owner tag of the paragraph
(`*(owner, plan 12, 2026-11-17)*`, or plan 17's tag if it has merged), append on the same
paragraph:

```markdown
The [V9 USAspending decision](findings/v9-usaspending-minimum-counts.md) sets it for the
USAspending vendor-link family, with one value for `supplier_share` and one for
`buyer_share`. That family is no longer among the families whose minimum stays open.
*(owner, plan 19, <date>)*
```

In V9, after the last owner tag of the item, append, indented as a list continuation:

```markdown
  The [V9 USAspending decision](findings/v9-usaspending-minimum-counts.md) covers the
  USAspending vendor-link family after its first full build. *(owner, plan 19, <date>)*
```

Rollout stays unchanged (spec "What gets built", item 4).

- [x] **Step 3: Change the stale lines**

- `CLAUDE.md`, section "USAspending vendor links (roadmap Stage 14)": replace the sentence
  (it wraps after `count`)
  ``Every target keeps `size_gate_pending`, and no headline minimum count (O26) exists yet.``
  with ``Every target keeps `size_gate_pending`. The headline minimum counts (O26), one for
  `supplier_share` and one for `buyer_share`, are in
  `specs/findings/v9-usaspending-minimum-counts.md`.``
- `README.md`, section "USAspending vendor links (roadmap Stage 14)": after ``The superseded
  `stage14_vendor_links_20261121_r1` stays on disk and is not cited.``, append
  ``[The V9 USAspending decision](specs/findings/v9-usaspending-minimum-counts.md) sets one
  headline minimum count for `supplier_share` and one for `buyer_share` (O26). A row meets
  its gate when its `n_unweighted` is at least its measure's minimum. The published targets
  keep `size_gate_pending`.``
- `specs/deliverable-map.md`, the row "USAspending subawards with SAM.gov NAICS": in the
  Status cell, replace ``Not replayed. No count gate yet`` with ``Replayed (Stage 20). Count
  gates set (Stage 21): `supplier_share` minimum <Ms>, met by <ks> of <rs> rows,
  `buyer_share` minimum <Mb>, met by <kb> of <rb> rows``, from `published`. Replace the
  "Still blocked by" cell with ``Its section in [the evaluation protocol](evaluation-protocol.md)
  (O18). R8.4, if it trains``.

> Deviation: `origin/main` had rewritten the map's USAspending Status cell (Stage 20 replay),
> so the edit kept that text and added the Stage 21 sentence after it, in place of the
> `Not replayed. No count gate yet` swap. The map's as-of header stays unchanged.

- [x] **Step 4: Check that no frozen file changed**

```bash
git fetch origin
uv run --locked python -c "import subprocess; from embedding_data.vendor_link_bundle import SOFTWARE_FILES; changed = set(subprocess.run(['git', 'diff', '--name-only', 'origin/main...HEAD'], capture_output=True, text=True, check=True).stdout.split()); frozen = set(SOFTWARE_FILES) | {'scripts/measure_ita_minimum_counts.py', 'scripts/reconcile_usaspending_vendor_links.py', 'specs/naics-evaluation-data-stage-14-findings.md'}; print(sorted(changed & frozen) or 'none frozen'); print(sorted(changed))"
```

Expected: `none frozen`, then only the files of this plan's File Structure (and the plan file
itself, after the completion protocol).

- [x] **Step 5: Commit**

```bash
git add specs/findings/v9-usaspending-minimum-counts.md specs/embedding-evaluation-data-spec.md CLAUDE.md README.md specs/deliverable-map.md
git commit -m "docs(specs): record the V9 USAspending minimum counts"
```

> Deviation: `origin/main` moved during execution (plans 18 and 20 merged), so a merge commit
> `bde4be0` (`chore: merge origin/main into the Stage 21 branch`) came before this commit,
> and no commit was rebased. The task review then found that the copied seventh Limit
> understated the measured leniency. A hand fix added one sentence with the two measured
> shares in a second commit `9fa10c0`
> (`docs(specs): state the measured leniency in the V9 USAspending record`).

## Handoff to later stages

- **O18 (USAspending protocol section).** It reads the decision record
  `specs/findings/v9-usaspending-minimum-counts.md` and the amended R7.3 and V9 of
  `specs/embedding-evaluation-data-spec.md`. The decision gives two minimums, not the one that
  the roadmap's Exit names (this plan's second Deviation note). `supplier_share` has minimum 4
  and `buyer_share` has minimum 3. A row meets its gate when its `n_unweighted` is at least its
  measure's minimum. The gate keeps 2,315 and 2,234 of 8,307 rows, and 1,785 cells have both
  rows kept. The rule commit is `588ae5a`, and the script is
  `scripts/measure_usaspending_minimum_counts.py`. Both real runs printed the same bytes
  (SHA-256 `8b2e0e82719d37cf92c7f5de5b7e5de911e5408771df5ee45db1bf46d2c57ee6`) under
  `$HOME/.cache/embedding-data/stage21-minimum-counts/588ae5a`, outside git. The measurement
  read more than the roadmap's Consumes line names (this plan's first Deviation note): the pair,
  support and target Parquets of the run, besides `report.json`. The published bundles keep
  `size_gate_pending`. No output may feed embedder training (R8.4).
- **Traps.** The script is frozen at `588ae5a`. A fix toward the written rule needs both real
  runs again at the new commit, and the record then discloses it (Global Constraints, OC3). The
  script refuses any run but the pinned one, so a new Stage 14 run needs a new pin and a new
  measurement. A change to any file in `vendor_link_bundle.SOFTWARE_FILES` makes the Stage 14
  `verify` refuse the run. The gate is lenient: 525 of the 2,315 kept `supplier_share` rows and
  437 of the 2,234 kept `buyer_share` rows meet their minimum in no single fiscal year (record,
  section 9).
- **Still deferred.** The script's docstring names `specs/usaspending-minimum-counts.md`, which
  now sits in `specs/completed/`. The frozen script keeps the old path until its next rule
  commit (`specs/deferred_items.md`, section `19-usaspending-minimum-counts`).
