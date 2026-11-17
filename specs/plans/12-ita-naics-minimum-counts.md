# ITA NAICS Minimum Counts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure next-year recurrence curves for the three ITA NAICS families and set
one headline minimum count per family by the committed rule. Record the decision and
amend spec R7.3, V9 and Rollout.

**Architecture:** One offline script, `scripts/measure_ita_minimum_counts.py`, reads the
pinned Stage 1, Stage 6 and codes bundles in place. It authenticates them, recounts the
published counts exactly, finds testable cells through Stage 1's confirmed links, bands
them and applies the rule. It prints one sorted JSON line. A test fixture publishes tiny
input bundles with the frozen builders. The controller runs the script twice on real
data, and the decision record transcribes the output.

**Tech Stack:** Python 3.14, Polars, argparse, pytest, uv. No new dependency.

**Spec:** `specs/ita-naics-minimum-counts.md` (owner-approved, merged in lowmason/embedding-data#17 and #18, `ace8559`; amended by D1 in Task 6).

> Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 3 — on plan
> completion, tick the stage and re-validate later stages against what shipped.

> Deviation: the Stage 3 Exit names the observed `n_records` distribution of headline
> text–code pairs. This plan gates `n_headline_records` instead (owner, 2026-11-17, spec
> "The text-pair count"). The Stage 3 completion stamp cites this note.

## Global Constraints

- **Branch.** Cut a new branch from `main` at or after the merge that lands this plan,
  in a worktree (using-git-worktrees). Merge through a PR that the owner approves.
- **Script frozen after Task 8.** Once the first real run has executed, a finding against
  the script from any later review (the final whole-branch review included) follows OC3:
  only a fix toward the written rule, then both real runs again at the new commit, and
  the decision record discloses it.
- **Frozen software.** Change none of the 35 files in
  `ita_establishment_bundle.SOFTWARE_FILES`, which include `pyproject.toml` and `uv.lock`.
  Do not change the Stage 6 `FROZEN_MODULES`/`TARGET_MODULES`, the Stage 7–9 software,
  `cli.py` or `code_references.py`. Add no dependency and no console entry point. New
  code goes in `scripts/` and `tests/` only. If a reused function cannot serve unchanged,
  stop and ask the owner.
- **Offline and credential-free.** The script uses no network, no `.env`, no HTTP client,
  no upstream builder and no `verify` rerun.
- **Freeze window.** Before every real-data run, every full pytest run and every commit,
  run `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`. If it
  prints anything, stop, leave files uncommitted and tell the owner.
- **Commit protocol.** `pgrep` check, then `git add` of the task's files, then `git commit`
  with the given message and the session's `Co-Authored-By` trailer. Never skip a hook.
- **Rule before data.** The script, its tests and the constants `LEVEL = 0.90`,
  `TOP_BAND = 10` and `MIN_BAND_CELLS = 50` are committed before the first real run. No
  constant changes after that run. A fix that only makes the script match the written
  rule is allowed, and the decision record discloses it. Any change to the written rule
  goes to the owner.
- **Tests.** Red → green on small synthetic fixtures. Every test passes `--data-dir` (or a
  `data_dir`) under `tmp_path` and never reads the real tree.
- **Production root.** Only Task 8 reads real data, with
  `--data-dir /Users/lowell/Projects/embedding-data/data` passed explicitly. Nothing writes
  under `data/`.
- **Aggregates only.** R8.1–R8.4 hold. Output and decision record hold counts, rates,
  run IDs and pins only: no EIN, employer key, description or company string. No
  embedder output, score or ranking is read.
- **Leave alone.** Plans 9 and 10, the Stage 9 worktree
  (`/Users/lowell/.codex/worktrees/acs-targets-design/embedding-data`) and branch
  `codex/acs-targets-design`.
- **Style.** 4-space indentation, single quotes, `'''` docstrings, ruff at 99 columns.

**Pinned inputs** (spec "Inputs"):

| Role | Run ID | Directory under `--data-dir` | Detached `outputs.json` SHA-256 |
| --- | --- | --- | --- |
| establishment targets | `stage10_ita_establishment_20261116_r1` | `derived/osha/establishment-targets/` | `e19b0d58f61f106c3994aa6fe51f4fb71244188145dd90f8cccaa8dc8a8b09df` |
| area mix | `stage6_ita_area_mix_20261014_1000_csv` | `derived/targets/` | `084292b6835eb09ce27ecc4a3aef03a6f43bfe7b39b815665c29190a431e2473` |
| codes | `stage4_v11_20261013_r2` | `derived/codes/` | `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |

## Review Focus

1. A record whose only confirmed link is 2023 → 2025 (no 2024 filing). The Stage 1 link
   table holds that pair, because `ita_establishment_expected.YEAR_PAIRS` includes
   `(2023, 2025)`. The cell must not be testable (Task 3).
2. Exact duplicate year-t rows. Only the first is `base_row`. Every duplicate is in
   `base_rows`, and every one must count as linked (Task 3).
3. A confirmed link whose successor is ineligible for the family (a crosswalked code, no
   county for the area mix, or another pair for text pairs under D1). It must not make
   the cell testable (Tasks 3, 4, 5, 6).
4. A Stage 6 bundle built on another canonical table. Its `source_row` numbers mean other
   records, so the run must refuse before any count (Tasks 2, 5).
5. A family whose top band misses `LEVEL`. The run must print every curve, give that
   family a null minimum and exit 1, never 0 and never a crash (Task 7).

## Decisions

- **D1** (owner, plan review, 2026-11-17): a text pair is testable only when the linked successor of one of its eligible year-t records passes `eligible_industry()` and belongs to the same pair. A reworded description makes no pair testable, because description churn is not a coding accident. Applied in: Task 6 (spec amendment), Task 9.

## Owner Checkpoints

- **OC1 (plan review, settled by D1).** The approved spec let a reworded description make
  a text pair testable and non-recurring, which measures description churn as well as
  code change. The owner requires the successor to stay in the pair. Task 6 amends the
  stage spec and implements the rule before the Task 8 rule commit.
- **OC2 (Task 8).** A family with no minimum stops the stage. The owner decides. No
  constant changes.
- **OC3 (Task 8).** A refusal on real data stops the stage. A fix may only bring the
  script to the written rule, and the decision record discloses it. Anything else goes to
  the owner.

## File Structure

| File | Responsibility |
| --- | --- |
| `scripts/measure_ita_minimum_counts.py` (create) | Rule constants and functions, authentication, recounts and self-checks, per-family cells, report, CLI |
| `tests/minimum_count_fixtures.py` (create) | Builds in-memory published frames with the frozen builders and publishes them as three tiny bundles |
| `tests/test_measure_ita_minimum_counts.py` (create) | All tests. Loads the script with `importlib`, as `tests/test_reconcile_stage10.py` does |
| `specs/ita-naics-minimum-counts.md` (modify) | The D1 amendment: text-pair testability and one Limit |
| `specs/findings/v9-ita-naics-minimum-counts.md` (create) | The decision record |
| `specs/embedding-evaluation-data-spec.md` (modify) | R7.3, V9 and Rollout amendments |
| `CLAUDE.md` (modify) | One sentence |

---

### Task 1: Rule constants and curve-to-minimum functions

**Files:**
- Create: `scripts/measure_ita_minimum_counts.py`
- Test: `tests/test_measure_ita_minimum_counts.py`

**Interfaces:**
- Produces, in the script module:
  - Constants `LEVEL = 0.90`, `TOP_BAND = 10`, `MIN_BAND_CELLS = 50`,
    `WILSON_Z = 1.959963984540054`, `YEAR_PAIRS = ((2023, 2024), (2024, 2025))`,
    `FAMILIES = ('co_ownership', 'area_mix', 'text_pairs')`.
  - A **cells frame**: one row per base cell of one family and year pair, with
    `base_count: UInt64` (at least 1), `testable: Boolean` and `recurs: Boolean`, plus
    the family's key columns.
  - `bands(cells: pl.DataFrame) -> list[dict]`. Each dict has `low: int`,
    `high: int | None` (None for the band that reaches `TOP_BAND`), `base_cells`,
    `testable_cells`, `recurring_cells` (testable cells that recur), `rate: float | None`
    (`recurring_cells / testable_cells`, None when `testable_cells` is 0), `wilson_low`
    and `wilson_high` (None with `rate`).
  - `wilson(recurring: int, testable: int) -> tuple[float, float] | None`: the 95% Wilson
    interval with `WILSON_Z`, None when `testable` is 0.
  - `pair_minimum(bands: list[dict]) -> int | None`.
  - `family_minimum(minimums: list[int | None]) -> int | None`: the largest, or None when
    any is None.

- [ ] **Step 1: Write the failing tests**

Add `load_script()` (copy the pattern from `tests/test_reconcile_stage10.py`, script path
`scripts/measure_ita_minimum_counts.py`, assertion message
`'measurement script is missing'`), a `script` fixture and a helper
`cells(*groups)` that takes `(base_count, n_testable, n_recurring, n_untestable)` tuples
and returns a cells frame.

```python
def test_rule_constants_are_the_committed_values(script):
    assert (script.LEVEL, script.TOP_BAND, script.MIN_BAND_CELLS) == (0.90, 10, 50)
    assert script.YEAR_PAIRS == ((2023, 2024), (2024, 2025))

def test_bands_merge_short_bands_upward(script):
    found = script.bands(cells((1, 200, 0, 7), (2, 30, 0, 0), (3, 30, 0, 0), (4, 60, 0, 0),
                               (5, 10, 0, 0), (9, 45, 0, 0), (10, 2, 0, 0), (12, 2, 0, 0),
                               (40, 1, 0, 0)))
    assert [(b['low'], b['high'], b['testable_cells']) for b in found] == [
        (1, 1, 200), (2, 3, 60), (4, 4, 60), (5, 9, 55), (10, None, 5)]
    assert found[0]['base_cells'] == 207

def test_short_bands_chain_into_the_top_band(script):
    found = script.bands(cells(*[(k, 50, 0, 0) for k in range(1, 8)],
                               (8, 20, 0, 0), (9, 10, 0, 0), (11, 500, 0, 0)))
    assert [(b['low'], b['high'], b['testable_cells']) for b in found] == [
        *[(k, k, 50) for k in range(1, 8)], (8, None, 530)]

def test_band_rate_and_wilson(script):
    (band,) = script.bands(cells((10, 50, 45, 3)))
    assert (band['low'], band['high'], band['recurring_cells']) == (1, None, 45)
    assert band['rate'] == 0.9
    assert (band['wilson_low'], band['wilson_high']) == pytest.approx(
        (0.7863976856252035, 0.9565242350681096))

def test_wilson_reference_values(script):
    assert script.wilson(9, 10) == pytest.approx((0.5958499732047615, 0.9821237869049271))
    assert script.wilson(50, 50) == pytest.approx((0.9286524008666414, 1.0))
    assert script.wilson(0, 0) is None
```

Add a helper `band(low, high, rate)` that returns a band dict, and:

- `test_pair_minimum_is_start_of_trailing_passing_run`: rates 0.5 (1–1), 0.95 (2–3),
  0.85 (4–4), 0.92 (5–9), 0.99 (10+) give `5`.
- `test_pair_minimum_of_one_is_valid`: every band at or above 0.9 gives `1`.
- `test_rate_equal_to_level_passes`: 0.9 (1–9) and 0.9 (10+) give `1`.
- `test_no_minimum_when_top_band_misses_level`: 0.95 then 0.89 (10+) gives `None`. A top
  band with `rate` None also gives `None`.
- `test_family_minimum_is_largest_over_year_pairs`: `[1, 3]` gives `3`, `[2, None]` gives
  `None`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_ita_minimum_counts.py -v`
Expected: FAIL with "measurement script is missing" (the `load_script` assertion).

- [ ] **Step 3: Implement the constants and the four functions**

The module docstring states the rule in two sentences and cites the spec. Banding uses
`min(base_count, TOP_BAND)`. Merging is the one algorithm the signature leaves open:

```python
merged, current = [], None
for index in range(1, TOP_BAND + 1):           # raw bands 1..9 and TOP_BAND (= 10+)
    current = add(current, raw[index], low=index)   # keeps the first low; sums the counts
    if index == TOP_BAND or current['testable_cells'] >= MIN_BAND_CELLS:
        merged.append(close(current, high=None if index == TOP_BAND else index))
        current = None
```

`pair_minimum` walks the bands from the top down while `rate` is not None and
`rate >= LEVEL`, and returns the `low` of the last band it passed, or None if it passed
none. Compute `rate` and Wilson in Python from integers, never from Polars floats.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_measure_ita_minimum_counts.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/measure_ita_minimum_counts.py tests/test_measure_ita_minimum_counts.py
git commit -m "feat(scripts): add the V9 minimum-count rule functions"
```

### Task 2: Fixture bundles and input authentication

**Files:**
- Create: `tests/minimum_count_fixtures.py`
- Modify: `scripts/measure_ita_minimum_counts.py`
- Test: `tests/test_measure_ita_minimum_counts.py`

**Interfaces:**
- Consumes (frozen, unchanged): `ita_establishment_fixtures.canonical_frame`, `native`,
  `crosswalked`, `naics_reference`. `ita_establishment_records.keyed_records`,
  `KEY_SCHEMA`. `ita_establishment_links.build_links`. `ita_text_pairs.build_pairs`.
  `ita_co_ownership.estimate`. `ita_area_mix.estimate`. `target_io.inventory`,
  `write_json`. `manifest.sha256_file`.
- Produces in `tests/minimum_count_fixtures.py`:
  - `row(year: int, establishment: int, code: str, description: str, *, ein='123456789', mapping: dict | None = None, **changes) -> dict`:
    a canonical override row. `establishment` sets `establishment_id` and a distinct
    name and street, so equal establishments in later years make same-ID links.
    `mapping` defaults to `native(code)`.
  - `golden_rows() -> list[dict]`: one EIN, establishment 1 at `238220`
    ("Plumbing contractor") and establishment 2 at `722511` ("Restaurant"), each filing
    2023, 2024 and 2025.
  - `@dataclass(frozen=True) class Frames` with `canonical`, `links`, `pairs`, `members`,
    `co_ownership`, `support`, `assignments`, `area_mix` (all `pl.DataFrame`),
    `establishment_report: dict` (`{'pairs': {'records_by_year_status_basis': ...}}`) and
    `area_mix_report: dict` (`{'partition_by_year': ...}`).
  - `build_frames(rows: list[dict], counties: list[str | None] | None = None) -> Frames`:
    runs the frozen builders on `canonical_frame(rows)`. Keyed records come from
    `keyed_records(canonical, pl.DataFrame(schema=KEY_SCHEMA))`. Assignments are the
    canonical rows with `source_row`, `county_id` (default `'county:2025:39035'` for
    every row), `assignment_method` and `assignment_reason`.
  - `@dataclass(frozen=True) class Published` with `data_dir`, `establishment`,
    `area_mix` and `codes` (bundle directories) and `establishment_pin`, `area_mix_pin`
    and `codes_pin`, and `argv(self) -> list[str]` (the seven CLI options of Task 7).
  - `publish(root: Path, frames: Frames) -> Published`: writes the three bundles under
    `root / 'data'` with the run IDs `fixture_stage10`, `fixture_stage6` and
    `fixture_codes`. File names equal the real bundles' names: `ita_establishment_links`,
    `ita_text_pairs`, `ita_text_pair_members`, `ita_co_ownership` and
    `co_ownership_support` (`.parquet`) with `inputs.json` and `report.json`.
    `ita_county_assignments` and `ita_area_mix` (`.parquet`) with `inputs.json` and
    `report.json`. `ita_300a_canonical.parquet`. Each `inputs.json` records the canonical
    table as
    `{'path': 'derived/codes/fixture_codes/ita_300a_canonical.parquet', 'sha256': ...}`.
    The Stage 1 `inputs.json` adds `codes: {'run_id', 'outputs_sha256'}`.
  - `republish(directory: Path) -> str`: rewrites `outputs.json` from the current files
    and returns its new SHA-256.
- Produces in the script:
  - `class Refused(Exception)`, whose message is a fixed reason.
  - `@dataclass(frozen=True) class Inputs` with `Path` fields `canonical`, `links`,
    `pairs`, `members`, `co_ownership`, `support`, `establishment_report`, `assignments`,
    `area_mix`, `area_mix_report`.
  - `authenticate(data_dir: Path, establishment: tuple[str, str], area_mix: tuple[str, str], codes: tuple[str, str]) -> Inputs`:
    each tuple is `(run_id, outputs_sha256)`.

Authentication order, each step with its fixed reason:

1. Every run ID matches `[A-Za-z0-9][A-Za-z0-9_-]*` and every pin matches `[0-9a-f]{64}`:
   `'unsafe run id or pin'`.
2. The three detached pins, in table order: `'establishment-target pin differs'`,
   `'area-mix pin differs'`, `'codes pin differs'`.
3. Every file the script reads matches its `sha256` record in its own `outputs.json`:
   `'file differs from its inventory'`.
4. Cross-bundle identity. Both `inputs.json` files record `canonical.path` as
   `derived/codes/<codes run>/ita_300a_canonical.parquet` and `canonical.sha256` as the
   codes inventory's record. The Stage 1 `codes.run_id` and `codes.outputs_sha256` equal
   the codes selection. Otherwise: `'inputs name another canonical table or codes run'`.

- [ ] **Step 1: Write the fixture module and the failing tests**

Add a `published` fixture: `publish(tmp_path, build_frames(golden_rows()))`. In every
later task, build a test's rows as `golden_rows()` plus changes, so that each family
keeps some eligible support. `ita_area_mix.estimate` raises when no 2023 record is
eligible, and the other frozen builders can refuse an empty family.

- `test_fixture_builds_frozen_tables`: the golden `support` has two rows with `j_2023`,
  `j_2024` and `j_2025` all 1, and `frames.links` has `confirmed_same_id` rows for
  `(2023, 2024)` and `(2024, 2025)`.
- `test_authenticate_returns_pinned_files`:
  `inputs.canonical == published.codes / 'ita_300a_canonical.parquet'` and
  `inputs.assignments == published.area_mix / 'ita_county_assignments.parquet'`.
- `test_wrong_pin_refused`, parametrized over the three roles with `'0' * 64`: raises
  `Refused` with that role's reason.
- `test_changed_file_refused`: rewrite `ita_co_ownership.parquet` without one row and do
  not republish. Reason `'file differs from its inventory'`.
- `test_pins_are_checked_before_files`: a changed Stage 6 file and a wrong codes pin
  give `'codes pin differs'`.
- `test_establishment_inputs_naming_other_canonical_refused` and
  `test_area_mix_inputs_naming_other_canonical_refused`: set that bundle's
  `canonical.sha256` to `'1' * 64`, republish and pass the new pin. Reason
  `'inputs name another canonical table or codes run'`.
- `test_unsafe_run_id_refused`: run ID `'../fixture_codes'`. Reason
  `'unsafe run id or pin'`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_ita_minimum_counts.py -v -k "fixture or authenticate or refused or pins"`
Expected: `test_fixture_builds_frozen_tables` PASS. The others FAIL with
`AttributeError: ... has no attribute 'authenticate'`.

- [ ] **Step 3: Implement `Refused`, `Inputs` and `authenticate`**

Hash with `hashlib.file_digest`, as `scripts/reconcile_stage10.py` does.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_measure_ita_minimum_counts.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/measure_ita_minimum_counts.py tests/minimum_count_fixtures.py tests/test_measure_ita_minimum_counts.py
git commit -m "feat(scripts): authenticate the pinned minimum-count inputs"
```

### Task 3: Records and visible links

**Files:**
- Modify: `scripts/measure_ita_minimum_counts.py`
- Test: `tests/test_measure_ita_minimum_counts.py`

**Interfaces:**
- Consumes: `ita_establishment_records.keyed_records`, `KEY_SCHEMA`;
  `ita_area_mix.eligible_industry`; `ita_co_ownership.YEARS`;
  `ita_establishment_links.CONFIRMED`.
- Produces:
  - `record_frame(canonical: pl.LazyFrame) -> pl.DataFrame`. Applies
    `keyed_records(canonical, pl.DataFrame(schema=KEY_SCHEMA))`. With no title or index
    keys, the copied-text flags are all false, and no rule reads them. Keeps the 2023–2025
    rows, with columns `source_row` (UInt64), `year_filing_for`, `naics_code`,
    `naics_2022_node_id`, `ein_key`, `industry_eligible` (`eligible_industry()`) and
    `employer_eligible`. A record is `employer_eligible` when its year is in
    `ita_co_ownership.YEARS`, it passes `eligible_industry()`, `ein_key` is not null and
    `flag_ein_padded.fill_null(True)` is false. This is the co-ownership classification
    in the `ita_co_ownership` docstring.
  - `confirmed_links(links: pl.LazyFrame, records: pl.DataFrame) -> pl.DataFrame` with
    columns `base_year`, `source_row` and `later_row`. It keeps rows whose
    `(base_year, later_year)` is in `YEAR_PAIRS` (filter on **both** columns) and whose
    `status` is in `CONFIRMED`, and it explodes `base_rows` into `source_row`. It refuses
    with `'link rows disagree with canonical rows'` unless each
    `(base_year, source_row)` occurs once, each `source_row` is a record of `base_year` and
    each `later_row` is a record of `base_year + 1`.
  - `visible(links: pl.DataFrame, eligible_rows: pl.Series) -> pl.DataFrame` with columns
    `base_year` and `source_row`: the links whose `later_row` is in `eligible_rows`.

- [ ] **Step 1: Write the failing tests**

Build frames with `build_frames` and derive records and links through the new functions.

- `test_record_frame_keeps_2023_to_2025`: golden rows plus one 2022 row with
  `mapping=crosswalked('238220', 2017, ['238220'])`. A native 2022 code in 2022 would make
  `build_pairs` refuse the fixture. The frame has 6 rows, and every golden record has
  `industry_eligible` and `employer_eligible` true.
- `test_two_year_link_is_not_visible`: establishment 1 files 2023 and 2025 only. Guard:
  `frames.links` has a `confirmed_same_id` row for `(2023, 2025)`. Then
  `confirmed_links(...)` holds no row for establishment 1's 2023 source row.
- `test_duplicate_rows_link_through_base_rows`: two 2023 rows of establishment 1 with
  equal `id` (equal on all 24 summary columns) and one 2024 row. `confirmed_links` holds
  both 2023 source rows with the same `later_row`.
- `test_unconfirmed_links_are_not_visible`: establishment 1 moves to another street in
  2024. Guard: its link status is `weaker_same_id`. `confirmed_links` holds no row for
  its 2023 source row and still holds establishment 2's.
- `test_ineligible_successor_is_not_visible`: the 2024 row of establishment 1 is
  `crosswalked('238220', 2017, ['238220'])`.
  `visible(links, records.filter('industry_eligible')['source_row'])` excludes its 2023
  row and keeps establishment 2's 2023 row.
- `test_link_year_disagreement_refused`: point one `later_row` at a 2023 row. Raises
  `Refused('link rows disagree with canonical rows')`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_ita_minimum_counts.py -v -k "record_frame or link or successor"`
Expected: FAIL with `AttributeError` on `record_frame`.

- [ ] **Step 3: Implement `record_frame`, `confirmed_links` and `visible`**

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_measure_ita_minimum_counts.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/measure_ita_minimum_counts.py tests/test_measure_ita_minimum_counts.py
git commit -m "feat(scripts): find visible links for the minimum-count test"
```

### Task 4: Co-ownership recount, self-check and cells

**Files:**
- Modify: `scripts/measure_ita_minimum_counts.py`
- Test: `tests/test_measure_ita_minimum_counts.py`

**Interfaces:**
- Consumes: `record_frame`, `confirmed_links`, `visible` (Task 3).
- Produces:
  - `co_ownership_counts(records: pl.DataFrame) -> pl.DataFrame` with columns `unit_a`,
    `unit_b`, `j_2023`, `j_2024` and `j_2025` (UInt64), sorted by `unit_a` and `unit_b`.
    It has one row per directed cell with some `j_t >= 1`. `j_t` counts the distinct
    `ein_key` values with both nodes among their `employer_eligible` year-t records.
  - `check_co_ownership(counts: pl.DataFrame, support: pl.DataFrame, targets: pl.DataFrame) -> None`:
    `counts` must equal `support`'s `unit_a`, `unit_b` and `j_*` columns row for row
    after sorting. `targets` must hold the same `(unit_a, unit_b)` set. Otherwise it
    raises `Refused('co-ownership recount differs')`.
  - `co_ownership_cells(records: pl.DataFrame, links: pl.DataFrame, base_year: int) -> pl.DataFrame`:
    a cells frame keyed by `unit_a` and `unit_b`. `base_count` is `j_t`, and `recurs` is
    `j_{t+1} >= 1`. `testable` holds when some EIN of the cell has year-t
    `employer_eligible` records at both nodes that are in
    `visible(links, employer-eligible source rows)`.

- [ ] **Step 1: Write the failing tests**

Nodes are `naics:2022:national_industry:<code>`.

- `test_co_ownership_counts_equal_frozen_support`: on the golden frames plus a second
  EIN with `238220` and `722511` in 2024 only, `check_co_ownership` passes and returns
  None.
- `test_co_ownership_recount_difference_refused`: support with `j_2024` plus 1 on its
  first row raises `Refused('co-ownership recount differs')`. So do targets without
  their first row.
- `test_co_ownership_testable_needs_both_industries_linked`: EIN A has `238220` linked
  2023 → 2024 and `722511` in 2023 only. EIN B has both linked. Cell
  (`238220`, `722511`) for 2023 has `base_count` 2 and `testable` true. With EIN B
  removed it has `base_count` 1 and `testable` false.
- `test_co_ownership_recurs_through_any_employer`: EIN A holds the pair in 2023, both
  linked, and refiles in 2024 as `238210` and `722513`. EIN B holds the pair in 2024
  only. The 2023 cell is testable and recurs.
- `test_co_ownership_crosswalked_successor_is_not_testable`: EIN A's 2024 row of
  establishment 2 is crosswalked. The 2023 cell is not testable.
- `test_co_ownership_directed_cells_agree`: both directions of each pair have equal
  `base_count`, `testable` and `recurs`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_ita_minimum_counts.py -v -k co_ownership`
Expected: FAIL with `AttributeError` on `co_ownership_counts`.

- [ ] **Step 3: Implement the three functions**

Count `j_t` by deduplicating to `(ein_key, year, node)` and self-joining on
`(ein_key, year)` with `unit_a != unit_b`, as `ita_co_ownership` does.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_measure_ita_minimum_counts.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/measure_ita_minimum_counts.py tests/test_measure_ita_minimum_counts.py
git commit -m "feat(scripts): measure co-ownership recurrence"
```

### Task 5: Area-mix assignments, self-check and cells

**Files:**
- Modify: `scripts/measure_ita_minimum_counts.py`
- Test: `tests/test_measure_ita_minimum_counts.py`

**Interfaces:**
- Consumes: `record_frame`, `confirmed_links`, `visible` (Task 3);
  `ita_area_mix.eligible_industry`.
- Produces:
  - `assignment_frame(assignments: pl.LazyFrame, records: pl.DataFrame) -> pl.DataFrame`
    with columns `source_row`, `year_filing_for`, `county_id`, `naics_2022_node_id` and
    `area_eligible` (`county_id` not null and `eligible_industry()`), for 2023–2025. It
    refuses with `'assignment rows disagree with canonical rows'` unless its 2023–2025
    `source_row` set equals the records' set, each once, and `year_filing_for` and
    `naics_code` agree on every joined row (`eq_missing`).
  - `area_mix_counts(assigned: pl.DataFrame, year: int) -> pl.DataFrame` with columns
    `county_id`, `naics_2022_node_id` and `n_unweighted` (UInt64) over the year's
    `area_eligible` rows.
  - `check_area_mix(assigned: pl.DataFrame, area_mix: pl.DataFrame, report: dict) -> None`:
    the 2023 counts equal `area_mix`'s `unit_a`, `unit_b` and `n_unweighted` as sets of
    rows, and each year's `area_eligible` total equals `eligible` in that year's
    `report['partition_by_year']` entry. Otherwise it raises
    `Refused('area-mix recount differs')`.
  - `area_mix_cells(assigned: pl.DataFrame, links: pl.DataFrame, base_year: int) -> pl.DataFrame`:
    a cells frame keyed by `county_id` and `naics_2022_node_id`. `recurs` holds when the
    cell has an `area_eligible` record in t+1. `testable` holds when one of its year-t
    records is in `visible(links, area-eligible source rows)`.

- [ ] **Step 1: Write the failing tests**

- `test_area_mix_counts_equal_frozen_estimate`: `check_area_mix` passes on golden frames
  with two counties.
- `test_area_mix_recount_difference_refused`: `n_unweighted` plus 1 on the first row,
  the first row dropped, and the 2024 `eligible` plus 1 in the report each raise
  `Refused('area-mix recount differs')`.
- `test_assignment_disagreement_refused`: one assignment row with another `naics_code`,
  and one 2023 assignment row dropped, each raise
  `Refused('assignment rows disagree with canonical rows')`.
- `test_area_mix_successor_without_county_is_not_testable`: establishment 1's 2024 row
  has `county_id` None. Its 2023 cell is not testable.
- `test_area_mix_recurs_through_another_record`: establishment 1 is linked 2023 → 2024
  and refiles as `238210`. Another EIN files `238220` in the same county in 2024 only.
  The 2023 cell (county, `238220`) is testable and recurs.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_ita_minimum_counts.py -v -k "area_mix or assignment"`
Expected: FAIL with `AttributeError` on `assignment_frame`.

- [ ] **Step 3: Implement the four functions**

`ita_area_mix.estimate` refuses other years, so count with its filters: year, county
assigned and `eligible_industry()`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_measure_ita_minimum_counts.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/measure_ita_minimum_counts.py tests/test_measure_ita_minimum_counts.py
git commit -m "feat(scripts): measure area-mix recurrence"
```

### Task 6: Text-pair members, self-check and cells (with the D1 spec amendment)

**Files:**
- Modify: `specs/ita-naics-minimum-counts.md` (the "Testable cells" table and Limits)
- Modify: `scripts/measure_ita_minimum_counts.py`
- Test: `tests/test_measure_ita_minimum_counts.py`

**Interfaces:**
- Consumes: `record_frame` and `confirmed_links` (Task 3).
- Produces:
  - `pair_frame(members: pl.LazyFrame, pairs: pl.LazyFrame, records: pl.DataFrame) -> pl.DataFrame`
    with columns `source_row`, `pair_id`, `year_filing_for`, `naics_2022_node_id`,
    `industry_eligible` and `flag_headline`. It reads the published members and
    `flag_headline` and never recomputes a pair ID. It refuses with
    `'pair members disagree with canonical rows'` unless every record has exactly one
    member row and every member `pair_id` is in `pairs`.
  - `text_pair_counts(paired: pl.DataFrame) -> pl.DataFrame` with columns `pair_id`,
    `n_2023`, `n_2024` and `n_2025` (UInt64): the `industry_eligible` records of each
    headline pair by year, zero-filled.
  - `check_text_pairs(paired: pl.DataFrame, counts: pl.DataFrame, pairs: pl.DataFrame, report: dict) -> None`:
    for every headline pair, `n_headline_records == n_2023 + n_2024 + n_2025`, with the
    same set of headline pairs on both sides. Each year's `industry_eligible` total over
    all records equals the summed `n` of the year's `flag_headline_basis` rows in
    `report['pairs']['records_by_year_status_basis']`. Otherwise it raises
    `Refused('text-pair recount differs')`.
  - `text_pair_cells(paired: pl.DataFrame, links: pl.DataFrame, base_year: int) -> pl.DataFrame`:
    a cells frame keyed by `pair_id` over the headline pairs with at least one eligible
    year-t record. `base_count` is the number of those records. `recurs` holds when the
    pair has an eligible t+1 record whose node is one of its year-t nodes. `testable`
    holds when one of its eligible year-t records has a confirmed link (`links`) whose
    `later_row` is `industry_eligible` **and has the same `pair_id`** (D1). Join `links`
    to `paired` on `source_row` and again on `later_row` to compare the two pair IDs.

- [ ] **Step 1: Amend the stage spec (D1)**

Leave the spec's status line unchanged. In "Testable cells", replace the table row:

```markdown
| Text pairs | passes `eligible_industry()` | at least one of the pair's eligible year-t records has a visible link |
```

with:

```markdown
| Text pairs | passes `eligible_industry()` and belongs to the same pair | at least one of the pair's eligible year-t records has a visible link |
```

Directly after that table, before "Recurrence still counts any employer or
establishment.", insert:

```markdown
**Owner decision (plan 12 review, 2026-11-17): same pair.** A text pair's linked
successor must belong to the same pair, so the establishment kept its description. A
successor with a reworded description makes no pair testable. Description churn is not
a coding accident. *(owner, plan 12, 2026-11-17)*
```

In "Limits", after the bullet that starts "Testability keeps only cells with a visible
link.", insert:

```markdown
- A text pair is testable only when a linked successor kept its description. Pairs whose
  establishments reword their descriptions are under-represented in the text-pair curves.
  *(owner, plan 12, 2026-11-17)*
```

- [ ] **Step 2: Write the failing tests**

- `test_text_pair_counts_equal_frozen_pairs`: `check_text_pairs` passes on the golden
  frames.
- `test_text_pair_recount_difference_refused`: `n_headline_records` plus 1 on a headline
  pair, and the 2024 basis `n` plus 1 in the report, each raise
  `Refused('text-pair recount differs')`.
- `test_member_disagreement_refused`: members without their first row raise
  `Refused('pair members disagree with canonical rows')`.
- `test_text_pair_recurs_only_on_a_year_t_node`: establishment 1 files
  "Plumbing contractor" at `238220` in 2023 and at `238210` in 2024. The 2023 cell is
  testable and does not recur.
- `test_conflicting_pair_recurs_on_either_node`: two 2023 establishments of one EIN with
  that description at `238220` and `238210`. A 2024 record at `238210` recurs. A 2024
  record at `238290` does not.
- `test_non_headline_pairs_are_not_cells`: a pair with description `'N/A'` has no row.
- `test_reworded_successor_is_not_testable`: establishment 1 keeps `238220` in 2024
  under the description "Plumbing and heating". The 2023 "Plumbing contractor" cell is
  not testable.
- `test_same_pair_successor_makes_pair_testable`: two 2023 establishments of one EIN file
  "Plumbing contractor" at `238220`. In 2024 establishment 1 rewords its description and
  establishment 2 keeps it. The 2023 cell is testable and recurs.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_ita_minimum_counts.py -v -k "text_pair or member or pair_recurs or reworded or same_pair"`
Expected: FAIL with `AttributeError` on `pair_frame`.

- [ ] **Step 4: Implement the four functions**

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_measure_ita_minimum_counts.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add specs/ita-naics-minimum-counts.md scripts/measure_ita_minimum_counts.py tests/test_measure_ita_minimum_counts.py
git commit -m "feat(scripts): measure text-pair recurrence within the same pair"
```

### Task 7: Kept counts, report and command line

**Files:**
- Modify: `scripts/measure_ita_minimum_counts.py`
- Test: `tests/test_measure_ita_minimum_counts.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `kept(published: pl.DataFrame, minimum: int | None) -> dict`. The input has `count`
    and `largest_year_count` (UInt64), one row per published cell or headline pair. The
    output keys are `cells`, `support` (sum of `count`), `kept_cells`,
    `kept_cell_share`, `kept_support`, `kept_support_share` and `lenient_kept_cells`
    (kept rows with `largest_year_count < minimum`). The five `kept_*`/`lenient_*` values
    are None when `minimum` is None. Shares are Python floats from integers.
  - Published counts per family. Co-ownership: `ita_co_ownership` `n_unweighted`, with
    the largest of `support`'s `j_2023`, `j_2024` and `j_2025`. Area mix: `ita_area_mix`
    `n_unweighted`, with itself as the largest. Text pairs: `n_headline_records` of
    `flag_headline` pairs, with the largest of `text_pair_counts`.
  - `measure(inputs: Inputs) -> dict`, which returns the `constants` and `families` keys.
    All self-checks run before any cells frame.
  - `main(argv: list[str] | None = None) -> int`, which adds `inputs` from its arguments
    and `complete`. Options, all required:
    `--data-dir`, `--establishment-run`, `--establishment-outputs-sha256`,
    `--area-mix-run`, `--area-mix-outputs-sha256`, `--codes-run`,
    `--codes-outputs-sha256`. It prints exactly one line,
    `json.dumps(result, sort_keys=True)`, and nothing else on stdout.

Output shape (key names fixed):

```text
{"complete": bool,
 "constants": {"level", "top_band", "min_band_cells", "wilson_z"},
 "inputs": {"establishment_targets" | "area_mix" | "codes": {"run", "outputs_sha256"}},
 "families": {<family>: {
     "year_pairs": {"2023-2024" | "2024-2025": {"base_cells", "testable_cells",
                    "recurring_cells", "bands": [<Task 1 band dict>], "minimum"}},
     "minimum": int | null,
     "published": <kept dict>}}}
```

`complete` is true when all three families have a minimum. Exit 0 when `complete`.
Exit 1 when it is not, with every curve printed (OC2). On `Refused`, print only
`{"complete": false, "reason": <fixed reason>}` and exit 2.

- [ ] **Step 1: Write the failing tests**

- `test_kept_counts_cells_support_and_lenient`: counts `[2, 3, 1]`, largest `[1, 3, 1]`,
  minimum 2 give `{'cells': 3, 'support': 6, 'kept_cells': 2, 'kept_cell_share': 2/3,
  'kept_support': 5, 'kept_support_share': 5/6, 'lenient_kept_cells': 1}`. Minimum None
  gives `cells` 3, `support` 6 and the other five None.
- `test_cli_golden_run_exits_zero`: `main(published.argv())` returns 0 and prints one
  line equal to `json.dumps(json.loads(line), sort_keys=True)`. `complete` is true, each
  family's `minimum` is 1, `inputs` holds the three published pins and `constants` equals
  `{'level': 0.9, 'top_band': 10, 'min_band_cells': 50, 'wilson_z': 1.959963984540054}`.
- `test_cli_without_recurrence_exits_one`: in 2024 and 2025 establishment 1 refiles as
  `238210` and establishment 2 as `722513`. Exit 1, `complete` false, every family
  `minimum` None, and `families.co_ownership.year_pairs['2023-2024'].bands` not empty.
- `test_cli_refusal_exits_two`: wrong establishment pin. Exit 2 and output exactly
  `{'complete': False, 'reason': 'establishment-target pin differs'}`.
- `test_self_check_refusal_prints_no_curves`: support `j_2023` plus 1, republished and
  passed with the new pin. Exit 2 and reason `'co-ownership recount differs'`.
- `test_two_runs_are_byte_identical`: two `main` calls print equal lines.
- `test_output_holds_no_identifiers`: no EIN, company name, establishment name or
  description of the fixture rows occurs in the line.
- `test_cli_writes_nothing_under_data_dir`: the sorted `(relative path, SHA-256)` list of
  every file under `data_dir` is equal before and after `main`.
- `test_script_imports_are_offline`: parse the script with `ast`. No import names
  `httpx`, `dotenv`, `ipumspy`, `requests`, `urllib`, `socket`, `subprocess` or `typer`.
  No `embedding_data` import names `ita_establishment_bundle`, `ita_target_build`,
  `ita_establishment_targets`, `targets_cli` or `cli`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_ita_minimum_counts.py -v -k "kept or cli or runs or output or imports"`
Expected: FAIL with `AttributeError` on `kept` and `main`.

- [ ] **Step 3: Implement `kept`, `measure` and `main`**

`measure` scans each authenticated Parquet with only the columns it needs. The
`if __name__ == '__main__': sys.exit(main())` guard closes the file.

- [ ] **Step 4: Run the tests and lint**

Run: `uv run --locked pytest tests/test_measure_ita_minimum_counts.py -v`
Expected: all PASS.
Run: `uv run --locked ruff check scripts/measure_ita_minimum_counts.py tests/minimum_count_fixtures.py tests/test_measure_ita_minimum_counts.py`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add scripts/measure_ita_minimum_counts.py tests/test_measure_ita_minimum_counts.py
git commit -m "feat(scripts): report the V9 minimum counts as one JSON line"
```

### Task 8: Rule commit and two real runs (controller only)

The controller runs this task itself, not a subagent. Task 6's spec amendment (D1) must
be committed first.

**Files:** none in the repository. Outputs go to
`OUT=$HOME/.cache/embedding-data/stage3-minimum-counts` (outside the repository and
`data/`).

- [ ] **Step 1: Full checks**

Run the `pgrep` check (no output), then `uv run --locked pytest`, `uv run --locked behave`
and `uv run --locked ruff check .`.
Expected: all pass, the `network` canary deselected.

- [ ] **Step 2: Review before data**

Dispatch requesting-code-review over the branch (`main...HEAD`). Review against the
spec's "The rule" and "What gets built" item 1 and this plan's Review Focus. Resolve every
finding and rerun Step 1. This review guards Anti-goal "a rule picked after seeing its
result": after the first real run, only fixes toward the written rule are allowed.

- [ ] **Step 3: Record the rule commit**

Run: `git status --porcelain` (expected: no output), then `git rev-parse HEAD`. Keep the
SHA as the rule commit. Every real run runs at this commit, on a clean tree.

- [ ] **Step 4: First real run**

```bash
mkdir -p "$OUT" && touch "$OUT/start"
pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'
/usr/bin/time -l uv run --offline --locked python scripts/measure_ita_minimum_counts.py --data-dir /Users/lowell/Projects/embedding-data/data --establishment-run stage10_ita_establishment_20261116_r1 --establishment-outputs-sha256 e19b0d58f61f106c3994aa6fe51f4fb71244188145dd90f8cccaa8dc8a8b09df --area-mix-run stage6_ita_area_mix_20261014_1000_csv --area-mix-outputs-sha256 084292b6835eb09ce27ecc4a3aef03a6f43bfe7b39b815665c29190a431e2473 --codes-run stage4_v11_20261013_r2 --codes-outputs-sha256 15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a > "$OUT/run1.json" 2> "$OUT/run1.time"; echo "exit $?"
```

In a restricted workspace, prefix `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache`.

- Exit 0: continue.
- Exit 1: stop (OC2). Report the curves to the owner. Change no constant.
- Exit 2: stop (OC3). Read the reason. A fix toward the written rule restarts at Step 1
  with a new rule commit, and the decision record discloses it.

- [ ] **Step 5: Second real run and identity**

Repeat Step 4's commands with `run2.json` and `run2.time`. Then:

```bash
shasum -a 256 "$OUT/run1.json" "$OUT/run2.json"
cmp "$OUT/run1.json" "$OUT/run2.json" && echo identical
find /Users/lowell/Projects/embedding-data/data -newer "$OUT/start" -print
```

Expected: two equal digests, `identical`, and no output from `find`.

### Task 9: Decision record, spec amendments and CLAUDE.md

**Files:**
- Create: `specs/findings/v9-ita-naics-minimum-counts.md`
- Modify: `specs/embedding-evaluation-data-spec.md:528-530`, `:609-612`, `:672-673`
- Modify: `CLAUDE.md` (end of the "ITA establishment targets (Stage 10)" paragraph)

- [ ] **Step 1: Write the decision record**

Plain technical English. All values come from `$OUT/run1.json` and `$OUT/run1.time`.
Sections in order:

1. Decision: one line per family with its minimum and the published column it applies to
   (spec "Where the minimum applies").
2. Rule and constants: `LEVEL`, `TOP_BAND`, `MIN_BAND_CELLS`, the 95% Wilson interval
   (report only), and the rule commit from Task 8 Step 3. Disclose any fix made under OC3.
3. Inputs: the three run IDs and pins, and canonical SHA-256 `2c64e783c8874cbe78809c0629a08faa7a0bf965d7680279350a64928a1f32ab`.
4. Run: the full command, both output SHA-256 values, and the wall time and maximum RSS
   of run 1.
5. Curves: per family and year pair, one table of bands (`low`–`high`, base, testable,
   recurring, rate, Wilson interval), then that pair's minimum.
6. Kept counts: per family, the `published` values, including `lenient_kept_cells`.
7. Deviation: the text-pair gate counts `n_headline_records`, not the Exit's
   `n_records` (spec "The text-pair count").
8. Disclosure: the design-time co-ownership curves, quoted from the spec's Anti-goals.
9. Limits: the spec's eight Limits, including the D1 limit that Task 6 adds.
10. Not claimed: no bundle is relabeled, `size_gate_pending` stays, no minimum for other
    families, no scoring.

- [ ] **Step 2: Amend the spec**

Use the execution date for `<date>`. Replace R7.3:

```markdown
**R7.3** Every target reports its unweighted count. The minimum count for
headline use is *(open — resolved by measurement, not argument, discharged by
V9)*; it is set from observed distributions, not picked here.
```

with:

```markdown
**R7.3** Every target reports its unweighted count. The minimum count for
headline use is set for each family from its observed distributions, not picked
here. The [V9 ITA NAICS decision](findings/v9-ita-naics-minimum-counts.md) sets
it for ITA co-ownership, the 2023 ITA area mix and ITA text–code pairs. For every
other family it stays *(open — resolved by measurement, not argument, discharged
by V9)*. *(owner, plan 12, <date>)*
```

Replace V9:

```markdown
- **V9 — minimum cell counts** *(discharges R7.3)*. After the first full build,
  report unweighted-count distributions for every family and set the headline
  minimum in a recorded decision. Until then, no target is described as passing
  or failing a size gate.
```

with:

```markdown
- **V9 — minimum cell counts** *(discharges R7.3 family by family)*. After each
  family's first full build, report its unweighted-count distribution and set its
  headline minimum in a recorded decision. Until a family's decision exists, none
  of its targets is described as passing or failing a size gate. The
  [V9 ITA NAICS decision](findings/v9-ita-naics-minimum-counts.md) covers ITA
  co-ownership, the 2023 ITA area mix and ITA text–code pairs. *(owner, plan 12,
  <date>)*
```

Replace the Rollout sentence:

```markdown
V9 sets the cell-count gate after the first full build and before any embedder
is scored.
```

with:

```markdown
V9 sets each family's cell-count gate after that family's first full build and
before any embedder is scored on that family. *(owner, plan 12, <date>)*
```

- [ ] **Step 3: Add the CLAUDE.md sentence**

Append to the "ITA establishment targets (Stage 10)" paragraph:

```markdown
The published Stage 6 and Stage 10 bundles keep `size_gate_pending`, and
`specs/findings/v9-ita-naics-minimum-counts.md` holds the headline minimum counts for ITA
co-ownership, the 2023 ITA area mix and ITA text–code pairs.
```

- [ ] **Step 4: Check that no frozen file changed**

```bash
uv run --locked python -c "import subprocess; from embedding_data.ita_establishment_bundle import SOFTWARE_FILES; changed = set(subprocess.run(['git', 'diff', '--name-only', 'main...HEAD'], capture_output=True, text=True, check=True).stdout.split()); print(sorted(changed & set(SOFTWARE_FILES)) or 'none frozen'); print(sorted(changed))"
```

Expected: `none frozen`, then only the seven files of this plan's File Structure.

- [ ] **Step 5: Commit**

```bash
git add specs/findings/v9-ita-naics-minimum-counts.md specs/embedding-evaluation-data-spec.md CLAUDE.md
git commit -m "docs(specs): record the V9 ITA NAICS minimum counts"
```
