# ACS Wage Minimum Headline Earners Implementation Plan

**Status: COMPLETE (2026-11-23)** — executed via subagent-driven-development; deferred items in specs/deferred_items.md, or specs/completed/deferred_items.md once archived

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure the replicate-weight SE of each headline category's mean log wage in the
Stage 17 wage file, set one minimum number of headline earners by the committed band rule,
record the decision and amend spec R7.3, V9 and Rollout.

**Architecture:** One offline script, `scripts/measure_acs_wage_minimum_earners.py`, imports
only the standard library and Polars. It authenticates the pinned Stage 17 run, reads 85
columns of the person table lazily, filtered to headline rows, and recounts them against
`report.json`. Then it computes each category's SE with `math.fsum` sums, bands the categories
and applies the rule. It prints one sorted JSON line. Tests publish tiny hand-made bundles and
one genuine fixture-chain bundle. The controller runs the script twice on real data, and the
decision record transcribes the output without any per-category SE.

**Tech Stack:** Python 3.14, Polars, argparse, pytest, uv. No new dependency.

**Spec:** `specs/acs-wage-minimum-earners.md` (owner-approved 2026-11-22, merged in
lowmason/embedding-data#43, `3382744`).

> Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 19 — on plan
> completion, tick the stage and re-validate later stages against what shipped.

> Deviation: the Stage 19 Consumes line (roadmap `:248`) names only `report.json` and the
> Stage 17 finding, and the O23 cost cell (roadmap `:71`) says "one pass over Stage 17's
> counts". Under D1 the measurement also reads `acs_wage_persons.parquet`, which costs more
> (owner, D1, 2026-11-22; spec "Rollout"). The Exit still holds as written, because the
> minimum and its bands are counted in `headline_rows`. The Stage 19 completion stamp cites
> this note.

Roadmap `:252` still says `ROUTING: brainstorming` for Stage 19. The approved spec governs.
The completion protocol ticks the stage and stamps it.

## Global Constraints

- **Branch.** Cut a new branch from `main` at or after the merge that lands this plan, in a
  worktree (using-git-worktrees). Merge through a PR that the owner approves.
- **Script frozen after Task 4 Step 4.** Once the first real run has executed, a finding
  against the script from any later review (the final whole-branch review included) follows
  OC3: only a fix toward the written rule, then both real runs again at the new commit, and
  the decision record discloses it.
- **Frozen software.** Change no file in `acs_wage_inputs.SOFTWARE_FILES`
  (`src/embedding_data/acs_wage_inputs.py:61-81`, 19 files, including `pyproject.toml` and
  `uv.lock`), the Stage 6 `FROZEN_MODULES` and `TARGET_MODULES`, the Stage 7 to 9 software,
  `cli.py` or `code_references.py`. Add no dependency, marker or console entry point. New code
  goes in `scripts/` and `tests/` only. `tests/conftest.py` may gain one `SLOW_TESTS` entry
  (Task 3).
- **Leave alone.** The Stage 17 runs `stage17_acs_wage_microdata_20261119_r1` and
  `..._r1_replay` and their control directory. `specs/completed/acs-wage-microdata.md`,
  `specs/naics-evaluation-data-stage-17-findings.md` and `tests/test_reconcile_stage17.py`.
  The Codex worktree and branch `codex/acs-targets-design`. Plans 9 and 10.
- **Offline and credential-free.** The script uses no network, no `.env`, no HTTP client, no
  upstream builder and no `verify` run. It imports no `embedding_data` module.
- **Freeze window.** Before every real-data run, every full pytest run and every commit, run
  `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`. If it prints
  anything, stop, leave files uncommitted and tell the owner.
- **Commit protocol.** `pgrep` check, then `git add` of the task's files, then `git commit`
  with the given message and the session's `Co-Authored-By` trailer. Never skip a hook.
- **Rule before data.** The script, its tests and the constants below are committed before the
  first real run. No constant changes after that run. A fix that only makes the script match
  the written rule is allowed, and the decision record discloses it. Any change to the written
  rule goes to the owner.
- **Constants** (spec "From SEs to a minimum"): `SE_TARGET = 0.05`, `LEVEL = 0.90`,
  `BAND_STARTS = (1, 50, 100, 200, 400, 800, 1600)`, `MIN_BAND_CATEGORIES = 10`,
  `REPLICATE_FACTOR = 4 / 80`, `REPLICATES = 80`, `YEARS = (2023, 2024)`.
- **Columns read** (85, spec "Inputs"): `YEAR` (Int64), `INDNAICS` (String), `flag_headline`
  (Boolean), `log_wage_2010` (Float64), `PERWT` (Float64) and `REPWTP1` to `REPWTP80` (Int64).
  The spec's "84 columns" (`:121`) is a slip. Weights use their literal values (factor 1).
- **Tests.** Red → green on synthetic bundles. Every test passes `--data-dir` under
  `tmp_path` and never reads the real tree. No real count appears in a fixture.
- **Production root.** Only Task 4 reads real data, with
  `--data-dir /Users/lowell/Projects/embedding-data/data` passed explicitly. Nothing writes
  under `data/`. Real output goes to `OUT=$HOME/.cache/embedding-data/stage19-minimum-earners`
  and never enters git, because it holds per-category SEs.
- **Aggregates only.** R8.1 to R8.4 hold. The output holds counts, SEs, flags and category
  codes only, never a mean wage or a person value. The decision record holds no SE of a single
  category. No embedder output, score or ranking is read.
- **Style.** 4-space indentation, single quotes, `'''` docstrings, ruff at 99 columns.

**Pinned input** (spec "Inputs"):

| File | Identity |
| --- | --- |
| `derived/acs/wage-microdata/stage17_acs_wage_microdata_20261119_r1/outputs.json` | detached SHA-256 `6cb253e2e5c2e48a5b31d2790a0378636d3b6ef9197cfb2d33cca2813ac201d1` |
| its `report.json` | inventory SHA-256 `32ad9b698c9b940760d74eec0ae3b234abd14ba4c08ca07f04770a8f11e413bd` |
| its `acs_wage_persons.parquet` | inventory SHA-256 `a94471492dc91aebe3a3436e8d738d399520791b0eace6f01a719fad10fd5ff2` |

## Review Focus

1. Row order or thread count changes the output. Polars float `group_by().sum()` can
   reorder additions across threads, so the last bits of an SE move. A shuffled person table
   must give byte-identical output apart from its own pin (Task 3).
2. Space-padded `INDNAICS` strings. `'6231'` and `'6231  '` are two categories, and the
   output keeps each string as delivered (Tasks 2, 3).
3. The report and the Parquet disagree on the set of `(INDNAICS, YEAR)` keys, not only on a
   count. A headline key absent from `categories`, or present there with `headline_rows` 0,
   must refuse (Task 2).
4. A report whose year set is not `{2023, 2024}`. The script must refuse, never print a
   one-year minimum (Task 2).
5. A negative or zero replicate weight on one row while the denominator stays positive. The
   SE stays defined. Only a denominator of zero or less makes it undefined (Task 1).

## Decisions

- **D1** (owner, plan review, 2026-11-22): Approve plan 17 as committed at `0e4aa28`, with the OC1 defaults, the 85-column reading and the refusals that the spec does not list unchanged ("Approve plan 17"). Applied in: Owner Checkpoints (OC1), Global Constraints, Task 2.

## Owner Checkpoints

- **OC1 (plan review, settled by D1).** The defaults this plan sets where the spec leaves a choice: an SE
  that is undefined for two reasons counts once, under the first reason in the spec's order.
  Kept shares divide by that year's headline categories and headline rows. Categories with no
  headline rows are counted apart as `shared_node_categories`. Sums use `math.fsum`.
- **OC2 (Task 4).** Exit 1, a top band that fails in either year, stops the stage. The owner
  decides. No constant changes.
- **OC3 (Task 4).** A refusal on real data stops the stage. A fix may only bring the script to
  the written rule, and the decision record discloses it. Anything else goes to the owner.

## File Structure

| File | Responsibility |
| --- | --- |
| `scripts/measure_acs_wage_minimum_earners.py` (create) | Constants, SE and band functions, authentication, self-checks, report, CLI |
| `tests/test_measure_acs_wage_minimum_earners.py` (create) | All tests and the small-bundle helpers. Loads the script with `importlib`, as `tests/test_reconcile_stage17.py:36-41` does |
| `tests/conftest.py` (modify, only if Task 3 Step 4 says so) | One `SLOW_TESTS` entry |
| `specs/findings/v9-acs-wage-minimum-earners.md` (create) | The decision record |
| `specs/embedding-evaluation-data-spec.md` (modify) | R7.3, V9 and Rollout amendments |
| `CLAUDE.md`, `README.md`, `specs/deliverable-map.md` (modify) | Stale O23 lines |

---

### Task 1: Rule constants and pure functions

**Files:**
- Create: `scripts/measure_acs_wage_minimum_earners.py`
- Test: `tests/test_measure_acs_wage_minimum_earners.py`

**Interfaces:**
- Produces, in the script module:
  - The constants of Global Constraints, plus `REPLICATE_COLUMNS = tuple(f'REPWTP{r}' for r in
    range(1, 81))`, `READ_SCHEMA` (an ordered `dict[str, pl.DataType]` of the 85 columns) and
    `UNDEFINED = ('fewer_than_two_rows', 'constant_wage',
    'replicate_denominator_not_positive')`, in the spec's order.
  - `category_se(rows: pl.DataFrame) -> tuple[float | None, str | None]`. `rows` holds one
    category-year's headline rows with `log_wage_2010`, `PERWT` and `REPWTP1` to `REPWTP80`.
    It returns `(se, None)` or `(None, reason)`, where `reason` is the first entry of
    `UNDEFINED` that holds.
  - `meets_target(se: float | None) -> bool`: `se is not None and se <= SE_TARGET`.
  - A **category record**: `{'INDNAICS': str, 'YEAR': int, 'headline_rows': int, 'se': float |
    None, 'undefined': str | None, 'meets_se_target': bool}`.
  - `bands(records: list[dict]) -> list[dict]`, over one year's records. Each band is
    `{'start': int, 'next_start': int | None, 'categories': int, 'meeting': int, 'share': float
    | None, 'passes': bool}`. `next_start` is None for the top band. `share` is
    `meeting / categories`, None when `categories` is 0.
  - `year_minimum(bands: list[dict]) -> int | None`.
  - `overall_minimum(minimums: list[int | None]) -> int | None`: the largest, or None when any
    is None.

Sums, so that two runs give byte-identical output: take each product `w_i · x_i`
elementwise in Polars, then add each list with `math.fsum`, which is correctly rounded and
does not depend on order. Sum `PERWT` with `math.fsum` too. Sum each `REPWTPr` as an Int64,
which is exact. Then `θ = Σ PERWT·x / Σ PERWT`, `θ_r` likewise, and
`SE = math.sqrt(REPLICATE_FACTOR * math.fsum((θ_r - θ) ** 2 for r))`.

A band passes when `categories > 0` and
`Fraction(meeting, categories) >= Fraction('0.90')`, so 9 of 10 passes exactly. Banding puts
each record at the largest start not above its `headline_rows`. Merging is the one algorithm
the signatures leave open:

```python
merged, current = [], None
for index, start in enumerate(BAND_STARTS):
    current = add(current, raw[start], start=start)  # keeps the first start; sums the counts
    top = index == len(BAND_STARTS) - 1
    if top or current['categories'] >= MIN_BAND_CATEGORIES:
        merged.append(close(current, next_start=None if top else BAND_STARTS[index + 1]))
        current = None
```

`year_minimum` walks the bands from the top down while `passes` is true and returns the
`start` of the last band it passed, or None when the top band fails.

- [x] **Step 1: Write the failing tests**

Add `load_script()` (copy `tests/test_reconcile_stage17.py:36-41`, script path
`scripts/measure_acs_wage_minimum_earners.py`, assertion message
`'measurement script is missing'`), a `script` fixture and two helpers:
`rows(x, perwt, replicates)`, which returns a typed `pl.DataFrame` where `replicates` is one
list of 80 weights per row, and `record(rows, meets)`, which returns a category record.

```python
def test_rule_constants_are_the_committed_values(script):
    assert (script.SE_TARGET, script.LEVEL, script.MIN_BAND_CATEGORIES) == (0.05, 0.90, 10)
    assert script.BAND_STARTS == (1, 50, 100, 200, 400, 800, 1600)
    assert script.REPLICATE_FACTOR == 4 / 80 and script.YEARS == (2023, 2024)
    assert len(script.READ_SCHEMA) == 85

def test_se_matches_hand_computed_case(script):
    odd, even = [2, 1], [1, 2]   # weights of rows 1 and 2 in odd and even replicates
    frame = rows([0.0, 1.0], [1.0, 1.0],
                 [[odd[i] if r % 2 else even[i] for r in range(1, 81)] for i in (0, 1)])
    se, reason = script.category_se(frame)
    assert reason is None and se == pytest.approx(1 / 3, abs=1e-15)
```

Theta is 0.5, `θ_r` alternates between 1/3 and 2/3, and `SE = sqrt(4/80 · 80/36) = 1/3`.

- `test_one_row_is_undefined`: one row gives `(None, 'fewer_than_two_rows')`.
- `test_equal_wages_are_undefined`: three rows with `x` 10.5 give
  `(None, 'constant_wage')`.
- `test_nonpositive_replicate_denominator_is_undefined`: two rows with wages 10.0 and 11.0,
  whose `REPWTP7` weights are `3` and `-3`, give `(None, 'replicate_denominator_not_positive')`. Two rows whose `REPWTP7`
  are both 0 give the same.
- `test_first_undefined_reason_wins`: one row with a negative `REPWTP1` gives
  `'fewer_than_two_rows'`.
- `test_negative_replicate_weight_with_positive_denominator_is_defined`: two rows with wages
  10.0 and 11.0 and `REPWTP7` weights `5` and `-1` give a finite SE and reason None.
- `test_equal_weights_give_zero_se`: three rows with wages 10.0, 10.5 and 11.25 (exact in
  binary) and integer weights equal across rows in every replicate give `(0.0, None)`, and
  `meets_target(0.0)` is true.
- `test_meets_target_boundary`: `meets_target(0.05)` is true, `meets_target(0.0500001)` and
  `meets_target(None)` are false.
- `test_bands_merge_short_bands_upward`: counts `[3]*12 + [60]*4 + [150]*9 + [300]*2 +
  [2000]*15` give `[(1, 50, 12), (50, 200, 13), (200, None, 17)]` as
  `(start, next_start, categories)`. The 50 band (4) merges into the 100 band. The 200 band
  (2) and the empty 400 and 800 bands chain into the top band, which starts at 200.
- `test_short_top_band_stays`: counts `[3]*20 + [2000]*4` give
  `[(1, 50, 20), (50, None, 4)]`. The empty bands 50 to 800 merge into the top band.
- `test_empty_top_band_fails`: counts `[3]*20` give a last band `(50, None, 0)` with
  `share` None and `passes` false, and `year_minimum` None.
- `test_share_equal_to_level_passes`: 10 categories in one band, 9 meeting, give `share` 0.9
  and `passes` true. 8 meeting give `passes` false.
- `test_year_minimum_is_start_of_trailing_passing_run`: bands that pass, fail, pass, pass give
  the third band's start. All passing gives 1.
- `test_no_minimum_when_top_band_fails`: pass, pass, fail gives None.
- `test_overall_minimum_is_largest_year`: `[1, 200]` gives 200, `[50, None]` gives None.

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_acs_wage_minimum_earners.py -v`
Expected: FAIL with "measurement script is missing".

- [x] **Step 3: Implement the constants and the functions**

The module docstring states the rule in two sentences, cites the spec and says that the
script imports only the standard library and Polars.

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_measure_acs_wage_minimum_earners.py -v`
Expected: all PASS.

- [x] **Step 5: Commit**

```bash
git add scripts/measure_acs_wage_minimum_earners.py tests/test_measure_acs_wage_minimum_earners.py
git commit -m "feat(scripts): add the Stage 19 SE and band rule functions"
```

### Task 2: Small bundles, authentication and self-checks

**Files:**
- Modify: `scripts/measure_acs_wage_minimum_earners.py`
- Test: `tests/test_measure_acs_wage_minimum_earners.py`

**Interfaces:**
- Consumes in the tests (unchanged): `acs_wage_fixtures.core_row` for typed `PERWT` and
  `REPWTP1` to `REPWTP80` values. `embedding_data.acs_wage_bundle.FILES`.
  `embedding_data.target_io.inventory` and `write_json`. `embedding_data.manifest.sha256_file`.
- Produces in the test file:
  - `person(INDNAICS: str, YEAR: int, log_wage_2010: float, *, headline=True, **weights) ->
    dict`: the 85 read columns, taken from `core_row(YEAR=YEAR, INDNAICS=INDNAICS)` and
    overridden by `weights`.
  - `golden_people() -> list[dict]`: for each year in `(2023, 2024)`, nine categories of two
    rows (wages 10.0 and 11.0, the default weights) and one category of 1,600 rows (wages
    alternating 10.0 and 11.0). One small category is `'6231  '`, and another is `'6231'`.
    Every category also has one non-headline row. Equal default weights give every SE 0, so
    every category meets the target, the ten categories merge into one top band starting at
    1, and the minimum is 1.
  - `report_for(people: list[dict]) -> dict`: `{'categories': [...], 'headline_categories':
    {...}}` with `categories` entries `{'INDNAICS', 'YEAR', 'rows', 'headline_rows'}` sorted by
    `INDNAICS` and `YEAR`, as `acs_wage_rules` builds them (`:289-333`).
  - `publish(root: Path, people: list[dict], report: dict | None = None) -> dict`: writes
    `root/'data'/'derived/acs/wage-microdata/fixture'/` with `acs_wage_persons.parquet` cast
    to `READ_SCHEMA`, `report.json` (`report_for(people)` by default), `inputs.json` (`{}`)
    and `outputs.json` from `target_io.inventory(directory, list(FILES))`. Returns
    `{'data_dir', 'directory', 'run': 'fixture', 'pin'}`.
  - `rehash(directory: Path) -> str`, `forge_persons(bundle: dict, change) -> str` and
    `forge_report(bundle: dict, change) -> str`, after `tests/test_reconcile_stage17.py:108-131`.
- Produces in the script:
  - `class Refused(Exception)`, whose message is a fixed reason.
  - `@dataclass(frozen=True) class Inputs` with `report: Path`, `persons: Path`,
    `outputs_sha256: str`, `report_sha256: str` and `persons_sha256: str`.
  - `authenticate(data_dir: Path, run_id: str, pin: str) -> Inputs`. The run directory is
    `data_dir / 'derived/acs/wage-microdata' / run_id`.
  - `load_report(file: Path) -> dict`, which validates shape and years.
  - `headline_frame(persons: Path) -> pl.DataFrame`: a lazy scan of `READ_SCHEMA`'s columns,
    filtered to `flag_headline`, collected.
  - `self_check(report: dict, headline: pl.DataFrame) -> None`.

Checks in order, each with its fixed reason:

1. The run ID matches `[A-Za-z0-9][A-Za-z0-9_-]*` and the pin `[0-9a-f]{64}`:
   `'unsafe run id or pin'`.
2. `outputs.json` exists and its SHA-256 equals the pin: `'outputs pin differs'`.
3. `report.json` matches its inventory record in SHA-256 **and** size:
   `'report differs from its inventory'`. Then the Parquet likewise:
   `'person table differs from its inventory'`. No other file of the run is read.
4. `report.json` has a list `categories` of objects with a string `INDNAICS`, an integer
   `YEAR` and a non-negative integer `headline_rows`, no key twice, and an object
   `headline_categories` of integers: `'report is malformed'`.
5. The keys of `headline_categories` are exactly `'2023'` and `'2024'`, and every
   `categories` `YEAR` is in `YEARS`: `'report years differ from 2023 and 2024'`.
6. The Parquet schema has each `READ_SCHEMA` column with that exact type:
   `'person table columns differ from the contract'`.
7. The recount `(INDNAICS, YEAR, headline_rows)` of headline rows equals, as a set, the
   report entries with `headline_rows > 0`: `'headline recount differs from the report'`.
8. For each year, the number of categories with headline rows equals `headline_categories`:
   `'headline category count differs from the report'`.
9. Every headline row has a finite `log_wage_2010` and `PERWT > 0`:
   `'headline row has a non-finite wage or a non-positive weight'`.

- [x] **Step 1: Write the helpers and the failing tests**

Add a `golden` fixture: `publish(tmp_path, golden_people())`.

- `test_authenticate_returns_pinned_files`: `inputs.persons` is the bundle's
  `acs_wage_persons.parquet`, and `inputs.outputs_sha256 == golden['pin']`.
- `test_unsafe_run_id_refused`: run `'../fixture'`. Reason `'unsafe run id or pin'`.
- `test_wrong_pin_refused`: `'0' * 64`. Reason `'outputs pin differs'`.
- `test_changed_report_refused` and `test_changed_persons_refused`: change the file and do not
  rehash. Their reasons from check 3.
- `test_size_is_checked`: edit `outputs.json` so that the report record's `size` is size + 1
  and its `sha256` is unchanged. Do not rehash. Pass the SHA-256 of the edited `outputs.json`
  as the pin. Reason `'report differs from its inventory'`.
- `test_pin_is_checked_before_files`: a changed Parquet and a wrong pin give
  `'outputs pin differs'`.
- `test_malformed_report_refused`, parametrized over a missing `categories`, a string
  `headline_rows` and one entry written twice. Reason `'report is malformed'`.
- `test_one_year_report_refused`: drop `'2024'` from `headline_categories` and its entries.
  Reason `'report years differ from 2023 and 2024'`.
- `test_retyped_column_refused`: cast `REPWTP5` to Float64. Reason
  `'person table columns differ from the contract'`.
- `test_recount_differs_refused`, parametrized: one entry's `headline_rows` plus 1; the
  `'6231  '` entry renamed `'6231 '`; a headline category's entry set to `headline_rows` 0.
  Reason `'headline recount differs from the report'`.
- `test_headline_category_count_refused`: `headline_categories['2023']` plus 1. Its reason.
- `test_bad_wage_or_weight_refused`, parametrized over `log_wage_2010` NaN, `inf` and `PERWT`
  0 on one headline row (report unchanged, rehashed). Its reason.
- `test_non_headline_rows_are_not_checked`: a non-headline row with `log_wage_2010` NaN and
  `PERWT` 0 passes `self_check`.
- `test_padded_strings_stay_distinct`: `headline_frame` of the golden bundle has 20
  `(INDNAICS, YEAR)` keys, and both `'6231'` and `'6231  '` occur.

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_acs_wage_minimum_earners.py -v -k "authenticate or refused or checked or padded"`
Expected: FAIL with `AttributeError: ... has no attribute 'authenticate'` (or the function
named first).

- [x] **Step 3: Implement `Refused`, `Inputs`, `authenticate`, `load_report`,
  `headline_frame` and `self_check`**

Hash with `hashlib.file_digest`, as `scripts/reconcile_stage17.py:108-110` does. Unlike its
`inventory_file`, also compare `stat().st_size` with the record's `size`.

- [x] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_measure_acs_wage_minimum_earners.py -v`
Expected: all PASS.

- [x] **Step 5: Commit**

```bash
git add scripts/measure_acs_wage_minimum_earners.py tests/test_measure_acs_wage_minimum_earners.py
git commit -m "feat(scripts): authenticate and recount the Stage 17 wage bundle"
```

### Task 3: Category records, kept counts and command line

**Files:**
- Modify: `scripts/measure_acs_wage_minimum_earners.py`
- Modify: `tests/conftest.py` (only if Step 4 says so)
- Test: `tests/test_measure_acs_wage_minimum_earners.py`

**Interfaces:**
- Consumes: everything above. In the chain test: `acs_mapping_fixtures.forbid_external_access`,
  `acs_wage_fixtures.wage_mapping` and `embedding_data.acs_wage_bundle.build`, as in
  `tests/test_reconcile_stage17.py:44-53`.
- Produces:
  - `category_records(headline: pl.DataFrame) -> list[dict]`: one category record per
    `(YEAR, INDNAICS)` of the headline rows, sorted by `YEAR` then `INDNAICS`, each from
    `category_se`.
  - `kept(records: list[dict], report: dict, year: int, minimum: int | None) -> dict` with
    keys `headline_categories`, `headline_rows`, `shared_node_categories` (that year's report
    entries with `headline_rows` 0), `kept_categories`, `kept_category_share`,
    `kept_headline_rows`, `kept_headline_row_share`, `count_meets_se_misses`,
    `count_misses_se_meets` and `missed` (a list of `{'INDNAICS', 'headline_rows'}` for the
    headline categories below the minimum, sorted by `INDNAICS`). A category meets the count
    when its `headline_rows` is at least the minimum. The two shares divide by that year's
    headline categories and headline rows, as Python floats from integers. With `minimum`
    None, every key after `shared_node_categories` is None.
  - `measure(data_dir: Path, run_id: str, pin: str) -> dict`. All checks of Task 2 run before
    any SE.
  - `main(argv: list[str] | None = None) -> int`. Options, all required: `--data-dir`,
    `--run`, `--outputs-sha256`. It prints exactly one line,
    `json.dumps(result, sort_keys=True, allow_nan=False)`, and nothing else on stdout.

Output shape (key names fixed):

```text
{"complete": bool,
 "constants": {"se_target", "level", "band_starts", "min_band_categories",
               "replicate_factor", "years"},
 "inputs": {"run", "outputs_sha256", "report_sha256", "persons_sha256"},
 "years": {"2023" | "2024": {"bands": [<Task 1 band>], "minimum": int | null,
                             "undefined": {<each UNDEFINED reason>: int},
                             "kept": <kept dict>}},
 "minimum": int | null,
 "categories": [<category record>]}
```

`complete` is true when `minimum` is not None. Exit 0 when complete. Exit 1 when it is not,
with every band printed (OC2). On `Refused`, print only `{"complete": false, "reason":
<fixed reason>}` and exit 2. Any other exception prints `{"complete": false, "reason":
"measurement failed"}` and exits 2, so no exception text reaches the output.

- [x] **Step 1: Write the failing tests**

> Deviation: the `template` fixture wraps `acs_wage_fixtures.prepare_wage_delivery` so that `REPWTP37` is the integer 127. The unchanged chain fixture delivers the text `-2.5`, which converts to Float64 and fails the Int64 column contract (spec `:114`). The output-key test exempts the three `UNDEFINED` reason names, because `constant_wage` holds `wage`. Source: ledger, Task 3 rulings.

Add `run_main(script, capsys, bundle, pin=None)`, which calls `main` and returns the status
and the parsed line after checking that the line equals
`json.dumps(json.loads(line), sort_keys=True)`.

- `test_kept_counts_and_disagreements`: four 2023 records with `headline_rows` 30, 60, 60, 90
  and `meets_se_target` false, true, false, true, a report with one shared-node 2023 entry
  and minimum 50 give `{'headline_categories': 4, 'headline_rows': 240,
  'shared_node_categories': 1, 'kept_categories': 3, 'kept_category_share': 0.75,
  'kept_headline_rows': 210, 'kept_headline_row_share': 0.875, 'count_meets_se_misses': 1,
  'count_misses_se_meets': 0, 'missed': [{'INDNAICS': <first>, 'headline_rows': 30}]}`.
  Minimum None gives None in the last seven keys.
- `test_golden_run_exits_zero`: status 0, `complete` true, `minimum` 1, each year's
  `minimum` 1 with one band `(1, None, 10)`, every `undefined` count 0, `constants` equal to
  `{'se_target': 0.05, 'level': 0.9, 'band_starts': [1, 50, 100, 200, 400, 800, 1600],
  'min_band_categories': 10, 'replicate_factor': 0.05, 'years': [2023, 2024]}`, and `inputs`
  holding the golden pins.
- `test_failing_top_band_exits_one`: in 2024, two small categories keep one headline row each.
  Status 1, `complete` false, `minimum` None, the 2024 band has 8 of 10 meeting,
  `undefined['fewer_than_two_rows']` 2 for 2024, and the 2023 bands still print.
- `test_refusal_exits_two`: wrong pin gives exactly
  `{'complete': False, 'reason': 'outputs pin differs'}`.
- `test_shuffled_rows_give_identical_output`: forge the Parquet with
  `frame.sample(fraction=1.0, shuffle=True, seed=7)`, and give the 1,600-row categories
  varied `PERWT` and replicate weights so that their SEs are not 0. Before and after, the
  outputs without `inputs` are equal as strings of `json.dumps(..., sort_keys=True)`.
- `test_two_runs_are_byte_identical`: two `main` calls print equal lines.
- `test_output_holds_no_means_or_person_values`: every category record has exactly the keys of
  a category record. No key anywhere in the output contains `mean`, `theta` or `wage`. With
  wages 10.25 and 11.75 and equal weights in one category, no float in the output equals
  10.25, 11.75 or their weighted mean 11.0.
- `test_writes_nothing_under_data_dir`: the sorted `(relative path, SHA-256)` list of every
  file under `data_dir` is equal before and after `main`.
- `test_script_imports_are_offline`: parse the script with `ast`. Its only third-party import
  is `polars`. No import names `embedding_data`, `httpx`, `dotenv`, `ipumspy`, `requests`,
  `urllib`, `socket`, `subprocess` or `typer`.
- `test_genuine_chain_bundle_passes_the_checks`: a module-scoped `template` fixture copied from
  `tests/test_reconcile_stage17.py:43-53` builds one genuine Stage 17 bundle. `main` on it
  returns 0 or 1, never 2, and its `inputs.report_sha256` equals the bundle inventory's
  `report.json` record.

- [x] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_measure_acs_wage_minimum_earners.py -v -k "kept or exits or rows or runs or output or writes or imports or chain"`
Expected: FAIL with `AttributeError` on `kept`, `category_records` or `main`.

- [x] **Step 3: Implement `category_records`, `kept`, `measure` and `main`**

> Deviation: the catch-all in `main` is `except (Exception, pl.exceptions.PanicException)`. A Polars panic is a `BaseException`, so `except Exception` would let it exit 1, the status of the OC2 stop. Source: ledger, Task 3 review 1.

Iterate the headline frame's groups with `partition_by('YEAR', 'INDNAICS', as_dict=True)` and
sort the records afterwards, so group order never reaches the output. The
`if __name__ == '__main__': sys.exit(main())` guard closes the file.

- [x] **Step 4: Run the tests and lint, and time the chain test**

Run: `uv run --locked pytest tests/test_measure_acs_wage_minimum_earners.py -v --durations=5`
Expected: all PASS. If `test_genuine_chain_bundle_passes_the_checks` takes 60 s or more,
setup included, add its node ID to `SLOW_TESTS` in `tests/conftest.py`.
Run: `uv run --locked ruff check scripts/measure_acs_wage_minimum_earners.py tests/test_measure_acs_wage_minimum_earners.py`
Expected: `All checks passed!`

- [x] **Step 5: Commit**

```bash
git add scripts/measure_acs_wage_minimum_earners.py tests/test_measure_acs_wage_minimum_earners.py
git commit -m "feat(scripts): report the Stage 19 minimum earners as one JSON line"
```

Add `tests/conftest.py` to the `git add` if Step 4 changed it.

### Task 4: Rule commit and two real runs (controller only)

The controller runs this task itself, not a subagent.

**Files:** none in the repository. Outputs go to `$OUT` (Global Constraints).

- [x] **Step 1: Full checks**

> Deviation: the full pytest run used the repo's xdist overlay (`uv run --locked --with-requirements tests/xdist-requirements.txt pytest -n 7 --hypothesis-profile=parallel`), because a serial run takes far longer. 8,647 tests passed. Source: ledger, Task 4.

Run the `pgrep` check (no output), then `uv run --locked pytest`, `uv run --locked behave`
and `uv run --locked ruff check .`.
Expected: all pass, the `network` canary deselected.

- [x] **Step 2: Review before data**

Dispatch requesting-code-review over the branch (`main...HEAD`). Review against the spec's
"The rule" and "What gets built" item 1 and this plan's Review Focus. Resolve every finding
and rerun Step 1. This review guards the Anti-goal "a rule picked after seeing its result".

- [x] **Step 3: Record the rule commit and check the pinned records**

Run: `git status --porcelain` (expected: no output), then `git rev-parse HEAD`. Keep the SHA as
the rule commit. Every real run runs at this commit, on a clean tree. Then:

```bash
D=/Users/lowell/Projects/embedding-data/data/derived/acs/wage-microdata/stage17_acs_wage_microdata_20261119_r1
shasum -a 256 "$D/outputs.json"
python3 -c "import json,sys; o=json.load(open(sys.argv[1])); print(o['report.json']['sha256'], o['acs_wage_persons.parquet']['sha256'])" "$D/outputs.json"
```

Expected: `6cb253e2…c201d1`, then `32ad9b69…11e413bd a9447149…10fd5ff2` (the Pinned input
table). Read nothing else of the run.

- [x] **Step 4: First real run**

```bash
OUT=$HOME/.cache/embedding-data/stage19-minimum-earners
mkdir -p "$OUT" && touch "$OUT/start"
pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'
/usr/bin/time -l uv run --offline --locked python scripts/measure_acs_wage_minimum_earners.py --data-dir /Users/lowell/Projects/embedding-data/data --run stage17_acs_wage_microdata_20261119_r1 --outputs-sha256 6cb253e2e5c2e48a5b31d2790a0378636d3b6ef9197cfb2d33cca2813ac201d1 > "$OUT/run1.json" 2> "$OUT/run1.time"; echo "exit $?"
```

In a restricted workspace, prefix `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache`.

- Exit 0: continue.
- Exit 1: stop (OC2). Report every band of both years to the owner. Change no constant.
- Exit 2: stop (OC3). Read the reason. A fix toward the written rule restarts at Step 1 with a
  new rule commit, and the decision record discloses it.

- [x] **Step 5: Second real run and identity**

Repeat Step 4's commands with `run2.json` and `run2.time`. Then:

```bash
shasum -a 256 "$OUT/run1.json" "$OUT/run2.json"
cmp "$OUT/run1.json" "$OUT/run2.json" && echo identical
find /Users/lowell/Projects/embedding-data/data -newer "$OUT/start" -print
```

Expected: two equal digests, `identical`, and no output from `find`.

### Task 5: Decision record, spec amendments and stale lines

**Files:**
- Create: `specs/findings/v9-acs-wage-minimum-earners.md`
- Modify: `specs/embedding-evaluation-data-spec.md:540-545`, `:637-643`, `:706-707`
- Modify: `CLAUDE.md:420-421`, `README.md:705-706`, `specs/deliverable-map.md:11`

Line numbers are as of `0e7cbd4`. Plan 16 (Stage 20) also edits `CLAUDE.md` and `README.md`,
so find each passage by its quoted text.

- [x] **Step 1: Write the decision record**

> Deviation: the record holds an unnumbered "Terms used in this record" list before section 1. Its section 2 states that the bands at 1, 50 and 100 merged into one band in both years, and that the minimum is the same under either reading of the merge step. Source: ledger, Task 5.

Plain technical English, beside `specs/findings/v9-ita-naics-minimum-counts.md`. All values
come from `$OUT/run1.json` and `$OUT/run1.time`. Sections in order:

1. Decision: the minimum, and the published column it applies to (`headline_rows` of each
   `categories` entry of `report.json`, keyed by `INDNAICS` and `YEAR`; spec "Where the
   minimum applies"). A minimum of 1 is a measured outcome.
2. Rule and constants: the SE formula, the undefined-SE guards with this plan's
   first-reason default, the five constants and the rule commit from Task 4 Step 3. Disclose
   any fix made under OC3.
3. Inputs: the run ID and the three SHA-256 values of the Pinned input table. The script read
   85 columns (the spec's "84" is a slip).
4. Run: the full command, both output SHA-256 values, and the wall time and maximum RSS of
   run 1. The output stays on this machine, because it holds per-category SEs.
5. Bands: for each year, one table of `start`–`next_start`, categories, meeting, share and
   pass, then the year's minimum and the undefined-SE counts by reason.
6. Kept counts: for each year, the `kept` values except `missed`, and both disagreement
   tallies.
7. Categories below the minimum: for each year, the `missed` list (`INDNAICS` and
   `headline_rows`), and the count of `shared_node_categories`. No SE of a single category.
8. Deviation: the Consumes line and the cost (this plan's Deviation note).
9. Disclosure: quote the spec's Anti-goals disclosure (`specs/acs-wage-minimum-earners.md:80-91`)
   and state that planning read no further data of the run.
10. Limits: the spec's seven Limits.
11. Not claimed: no Stage 17 bundle is relabeled, no protocol section (O24), no minimum for any
    target family, no panel result.

- [x] **Step 2: Amend the spec**

Use the execution date for `<date>`. In R7.3 (`:540-545`), after
`*(owner, plan 12, 2026-11-17)*`, append on the same paragraph:

```markdown
The ACS wage microdata are not a target family. The
[V9 ACS wage decision](findings/v9-acs-wage-minimum-earners.md) sets their minimum
number of headline earners for each category. *(owner, plan 17, <date>)*
```

In V9 (`:637-643`), after `*(owner, plan 12, 2026-11-17)*`, append, indented as a list
continuation:

```markdown
  The [V9 ACS wage decision](findings/v9-acs-wage-minimum-earners.md) covers the ACS
  wage microdata after their first full build. *(owner, plan 17, <date>)*
```

In Rollout (`:706-707`), after `*(owner, plan 12, 2026-11-17)*`, append:

```markdown
V9 sets the ACS wage microdata's minimum number of headline earners before any
embedder is scored on that file. *(owner, plan 17, <date>)*
```

- [x] **Step 3: Change the stale lines**

Change only the O23 part. O24 stays open in every line.

- `CLAUDE.md:420-421`: replace `No headline minimum count (O23) and no protocol section (O24)
  exist yet, so no panel result is claimed.` with ``The minimum number of headline earners
  for each category (O23) is in `specs/findings/v9-acs-wage-minimum-earners.md`. No protocol
  section (O24) exists yet, so no panel result is claimed.``
- `README.md:705-706`: replace `No headline minimum count (O23) and no protocol section (O24)
  exist yet.` with `[The V9 ACS wage decision](specs/findings/v9-acs-wage-minimum-earners.md)
  sets the minimum number of headline earners for each category (O23). No protocol section
  (O24) exists yet.`
- `specs/deliverable-map.md:11`: in the Status cell, replace `No count gate yet (O23)` with
  `Count gate set: minimum <M> headline earners per category, met by <k2023> of <c2023>
  categories in 2023 and <k2024> of <c2024> in 2024 (Stage 19)`, from `kept`. In the "Still
  blocked by" cell, replace `Its section in [the evaluation protocol](evaluation-protocol.md)
  (O24), its count gate (O23) and naics-embedder's wage panel spec` with `Its section in
  [the evaluation protocol](evaluation-protocol.md) (O24) and naics-embedder's wage panel
  spec`.

- [x] **Step 4: Check that no frozen file changed**

```bash
uv run --locked python -c "import subprocess; from embedding_data.acs_wage_inputs import SOFTWARE_FILES; changed = set(subprocess.run(['git', 'diff', '--name-only', 'main...HEAD'], capture_output=True, text=True, check=True).stdout.split()); print(sorted(changed & set(SOFTWARE_FILES)) or 'none frozen'); print(sorted(changed))"
```

Expected: `none frozen`, then only the files of this plan's File Structure.

- [x] **Step 5: Commit**

```bash
git add specs/findings/v9-acs-wage-minimum-earners.md specs/embedding-evaluation-data-spec.md CLAUDE.md README.md specs/deliverable-map.md
git commit -m "docs(specs): record the V9 ACS wage minimum earners"
```

## Handoff to later stages

- **O24 (Track H, the ACS wage microdata protocol section; no stage yet).** It consumes
  `specs/findings/v9-acs-wage-minimum-earners.md`: a minimum of 400 headline earners for each
  category, in both years. The minimum applies to `headline_rows` of each `categories` entry of
  Stage 17's `report.json`, keyed by `INDNAICS` and `YEAR`. In 2023, 183 of 233 categories meet it.
  In 2024, 178 of 233 meet it. This is what the roadmap's Produces states. Traps for the protocol
  section:
  - The lowest band of each year merged the bands at 1, 50 and 100, so the record shows one band
    from 1 to 199 (15 categories in 2023, 19 in 2024). The minimum is the same under either reading
    of the merge step.
  - The count gate and a category's own SE disagree for a few categories: 2 and 21 in 2023, 0 and 29
    in 2024 (the record's section 6). The protocol section decides what that means.
  - The record shows `INDNAICS` codes without their space padding. The delivered strings keep it.
  - The SE of each single category sits only in
    `$HOME/.cache/embedding-data/stage19-minimum-earners/run1.json` on this machine. It never enters
    git.
  - `scripts/measure_acs_wage_minimum_earners.py` is frozen at rule commit `f060526`. A change to it
    needs both real runs again and a disclosure in the record.
  - Nothing was deferred into this stage.
