# ACS Wage Microdata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 17 — on plan
> completion, tick the stage and re-validate later stages against what shipped.

**Goal:** Build, verify and replay one person-level Parquet of the ACS 2023–2024 wage
earners of the pinned Stage 8 core table, with outcome, covariates, weights, NAICS node
and flags, behind a new offline command group.

**Architecture:** A standalone command group `python -m embedding_data.acs_wage_microdata`
(`build`, `verify`, `compare-runs`) after the Stage 10 contract. Four new modules split the
work: pure Polars rules, checks against the Stage 4 NAICS graph, pinned input selection,
and the bundle lifecycle. The build authenticates Stage 8 and Stage 4 by their detached
pins and inventories, streams the derivation into exclusive staging and publishes by
rename. A new independent script reconciles the bundle with Stage 8 and proves
preservation. Tasks 9 and 10 run the gated production build, replay and finding, then
apply the spec's amendments.

**Tech Stack:** Python 3.14, Polars 2.0.0 (lazy, streaming `sink_parquet` and
`collect_batches`), Typer, pytest and Hypothesis, uv. Existing helpers: `target_io`,
`manifest`, `paths`, `ipums_ddi`.

**Spec:** `specs/acs-wage-microdata.md` (owner-approved 2026-11-18). Read it with this plan.
Its sections "Design", "Constraints" and "Verification: observable outcomes" govern every
task.

## Global Constraints

- **Where to work.** Execute in a new worktree cut from `main` after this plan merges.
  Never work in the primary checkout `/Users/lowell/Projects/embedding-data`, which other
  sessions share.
- **Frozen code.** "Frozen modules stay frozen. The stage adds modules only. The root
  `uv.lock` and `pyproject.toml` do not change, and no new dependency is needed." Edit no
  existing file under `src/`, `scripts/` or `features/`. Edit no existing test or fixture
  file, except to append entries to `SLOW_TESTS` in `tests/conftest.py`. Do not register
  the command group in `src/embedding_data/cli.py`: tests pin its SHA-256
  (`32a86b3d07bf112fabc1edb01fd10a966e840c185642e55d00f35dfd435220b3`).
- **Imports.** From `embedding_data`, the Stage 17 modules import only `manifest`,
  `paths`, `target_io`, `geography_references` (for `safe_path` and `occupied`, which
  `target_io` already loads), `ipums_ddi` and each other. Never import `acs_mapping_*`,
  `acs_target_*`, `ipums_parity`, `ipums_conversion` or `ita_establishment_*`. They load
  `dotenv` or `ipumspy`, or a large build tree. Tests may import any module.
- **Offline.** No command loads `.env`, reads a credential, builds an HTTP client or calls
  an upstream builder. No command rebuilds or edits Stage 8 or an earlier bundle.
- **Host rule (spec, verbatim).** "Run one full-data build at a time. Before every commit,
  every full pytest run and every full-data command, run `pgrep -fl
  'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'` and stop if it prints
  anything." If it prints anything, leave the work uncommitted and tell the owner. Never
  skip a hook.
- **Owner gates (roadmap Stage 17 `Consumes`).** Get the owner's go-ahead before each
  production write: (1) the preservation freeze and the first build, (2) the replay build,
  (3) any cleanup of a failed run's leftover staging. *Default, flagged at plan review:*
  each go-ahead also confirms that no Stage 9 freeze window is open and that no other
  stage's acquisition or full-data build is running. Show the owner the output of `pgrep
  -fl 'embedding_data|embedding-data'` at each go-ahead. The controller runs Task 9
  itself, because a subagent cannot ask the owner.
- **Stage 17's own preservation window.** *Default, flagged at plan review.* The window
  opens at the freeze (Task 9 Step 4) and closes at the preservation check (Step 10).
  Spec item 7 is strict: the manifest stays byte-identical, and no file appears outside
  the two runs and the control directory. During the window the owner holds every other
  stage's acquisition, build and other write under `data/`. Plan 13 (Stage 5 TRI) is
  merged and can run at any time. Run Steps 4 to 10 in one sitting where possible.
- **Production root.** Every production command passes `--data-dir
  /Users/lowell/Projects/embedding-data/data`. Every test passes a temporary data
  directory.
- **Production command form.** `uv run --offline --locked` from the execution worktree's
  own `.venv`. No `--with` overlay and no `uv sync` with other flags between the first
  build, its verify and the replay. The tree is clean (`git status --porcelain
  --untracked-files=normal` prints nothing), because `inputs.json` records `dirty`. The
  replay runs at the same commit.
- **Memory.** The build reads the Stage 8 core table through a lazy scan that selects only
  the contract columns and streams to Parquet. Record the `maximum resident set size` line
  of `/usr/bin/time -l` (bytes) for each production command. Do not record `peak memory
  footprint`, which measures the `uv` parent.
- **Immutability.** An existing final or `.part` path is never overwritten or deleted
  without gate 3. A killed build leaves its `.part`: inspect it, ask the owner, and use a
  fresh run ID.
- **Disclosure.** Person rows never leave this machine or enter git. `report.json` holds
  aggregate counts only. Findings, commit messages and PR text quote aggregates only. A
  failing command prints no exception text.
- **R8.4.** The file only judges and never trains, tunes or mines examples for an
  embedder.
- **Acceptance values.** The spec's measured counts (3,035,086 rows, 1,278,878 headline
  rows and the rest) appear only in Task 9's production checks. They never appear in a
  test or as a build refusal (spec item 3: a difference is explained in the finding).
- **Fixtures.** Fixture results show software readiness. They are never reported as
  evidence.
- **Style.** Single quotes, `'''` docstrings, 4-space indents, 99 columns, ruff clean.
- **Identities.** Contract `acs-wage-microdata-v1`. Bundle directory
  `derived/acs/wage-microdata/<RUN_ID>/`. Production run IDs
  `stage17_acs_wage_microdata_<YYYYMMDD>_r1` and `<first>_replay`. Run IDs match
  `[A-Za-z0-9][A-Za-z0-9_-]*`.
- **Leave alone.** naics-embedder. Plans 9 and 10 and the branch `codex/acs-targets-design`.
  Everything under `data/` outside Task 9. The spec's status line.

## Review Focus

1. **A deflated wage that is zero, negative or null, or an `INCWAGE` N/A code (999998,
   999999) on an earner row.** The build fails with reason `validation` and publishes
   nothing. It never writes `-inf` or NaN into `log_wage_2010`. Tests: Task 1
   `test_refuses_bad_wage_values`, Task 5 `test_build_failure_prints_only_the_fixed_line`.
2. **A build killed by the operating system (exit 137) leaves `<RUN>.part`.** A rerun with
   the same ID is refused and leaves the `.part` byte-identical. A fresh ID builds. Test:
   Task 4 `test_leftover_part_blocks_only_its_own_run_id`.
3. **A row allocated only in field of degree (`QDEGFIELD`).** It stays in the headline,
   with `flag_any_allocated` true. Tests: Task 1
   `test_qdegfield_alone_keeps_the_headline`, Task 6 control row AGE 43.
4. **Two categories that share a node, each present in one year only.** Both are flagged
   as shared, because the rule reads all of the file's rows. Test: Task 1
   `test_shared_node_spans_years`.
5. **A bundle edited after publication with a re-hashed inventory and a new pin.**
   `verify` refuses it, and `compare-runs` against the true replay prints `"equal":
   false` and exits 1. Tests: Task 4 `test_verify_refuses_a_rehashed_edit`, Task 5
   `test_compare_runs_exits_1_when_unequal`.

## Decisions

None.

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `src/embedding_data/acs_wage_rules.py` | Column contract, rule constants, derivation `wage_persons`, report `summarize` | 1 |
| `src/embedding_data/acs_wage_checks.py` | Headline invariants (spec item 5) and node checks against Stage 4 (item 6) | 2 |
| `src/embedding_data/acs_wage_inputs.py` | Pin and inventory authentication of Stage 8 and Stage 4, DDI labels, software identity, strict JSON | 3 |
| `src/embedding_data/acs_wage_bundle.py` | `run_directory`, `build`, `verify_bundle`, `compare_runs`, streaming `ordered_compare` | 4 |
| `src/embedding_data/acs_wage_microdata.py` | Typer command group | 5 |
| `scripts/reconcile_stage17.py` | Independent `reconcile`, `freeze` and `preservation` | 7, 8 |
| `tests/acs_wage_fixtures.py` | Synthetic core frames, the delivery hook, the chain template | 1, 3 |
| `tests/test_acs_wage_rules.py`, `test_acs_wage_checks.py`, `test_acs_wage_inputs.py`, `test_acs_wage_bundle.py`, `test_acs_wage_microdata.py`, `test_acs_wage_chain.py`, `test_reconcile_stage17.py` | Tests | 1–8 |
| `specs/naics-evaluation-data-stage-17-findings.md` | Production finding | 9 |
| `specs/embedding-evaluation-data-spec.md`, `CLAUDE.md`, `specs/deliverable-map.md`, `README.md` | Amendments and docs | 10 |

---

### Task 1: Rules and derivation

**Files:**
- Create: `src/embedding_data/acs_wage_rules.py`
- Create: `tests/acs_wage_fixtures.py`
- Test: `tests/test_acs_wage_rules.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `CONTRACT = 'acs-wage-microdata-v1'`, `TABLE = 'acs_wage_persons'`.
  - `CARRIED: tuple[str, ...]` — the 120 delivered columns of the spec's "Columns" table.
  - `NEW: dict[str, pl.DataType]` — the 10 new columns and their types.
  - `OUTPUT_COLUMNS: tuple[str, ...]` — 130 names in the order below.
  - `HEADLINE_ALLOCATION` (9 names), `ALLOCATION` (10 names), `FULL_TIME_HOURS = 35`,
    `FULL_YEAR_WKSWORK2 = 6`, `WAGE_SALARY_CLASSWKRD = (22, 23, 25, 27, 28)`,
    `INCWAGE_CODES = (999998, 999999)`, `RULE_COLUMNS: tuple[str, ...]`,
    `DDI_LABELS: dict[str, dict[str, str]]`, `RULES: dict[str, str]`.
  - `earners(core: pl.LazyFrame) -> pl.LazyFrame`
  - `check_inputs(earners: pl.LazyFrame) -> None`
  - `wage_persons(core: pl.LazyFrame) -> pl.LazyFrame`
  - `summarize(persons: pl.LazyFrame) -> dict`
  - Test helpers in `tests/acs_wage_fixtures.py`: `CORE_SCHEMA: dict[str, pl.DataType]`,
    `core_row(**overrides) -> dict`, `core_frame(rows: list[dict]) -> pl.LazyFrame`.

`OUTPUT_COLUMNS`, in this order (carried columns keep their Stage 8 names):

```text
source_parquet_sha256 source_row YEAR acs_sample_id
PERWT REPWTP1 … REPWTP80
INCWAGE INCWAGE_CPIU_2010 log_wage_2010
UHRSWORK WKSWORK2 CLASSWKR CLASSWKRD
SEX AGE EDUC EDUCD DEGFIELD DEGFIELDD STATEFIP REGION GQ
OCC OCCSOC occupation_canonical_common_node_id occupation_aggregation_type
IND INDNAICS industry_canonical_common_node_id industry_aggregation_type
  industry_canonical_finest_candidates industry_native_node_id industry_node_code
  industry_node_level industry_delivered_node_code flag_industry_shared_node
QINCWAGE QIND QOCC QUHRSWOR QWKSWORK2 QAGE QSEX QEDUC QCLASSWK QDEGFIELD flag_any_allocated
flag_incwage_topcoded
flag_full_time_full_year flag_wage_salary flag_headline
```

`NEW`: `log_wage_2010` Float64; `industry_node_code`, `industry_node_level`,
`industry_delivered_node_code` String; the six `flag_*` columns Boolean.

`DDI_LABELS` (the delivered DDI `usa_00001.xml`, read 2026-11-18):

```python
DDI_LABELS = {
    'WKSWORK2': {'6': '50-52 weeks'},
    'CLASSWKRD': {
        '13': 'Self-employed, not incorporated', '14': 'Self-employed, incorporated',
        '22': 'Wage/salary, private', '23': 'Wage/salary at non-profit',
        '25': 'Federal govt employee', '27': 'State govt employee',
        '28': 'Local govt employee', '29': 'Unpaid family worker',
    },
}
```

`RULE_COLUMNS`: `source_row`, `YEAR`, `STATEFIP`, `INCWAGE`, `INCWAGE_CPIU_2010`,
`UHRSWORK`, `WKSWORK2`, `CLASSWKRD`, `INDNAICS`, `industry_canonical_common_node_id`,
`industry_native_node_id` and the ten `ALLOCATION` columns.

`RULES` holds one plain sentence for each new column and for `rows`, copied from the spec's
"Rules for the new columns". It is recorded in `inputs.json`.

- [ ] **Step 1: Write the test helpers**

`CORE_SCHEMA` mirrors the production Stage 8 types: `source_row` UInt64; `PERWT`,
`INCWAGE_CPIU_2010` Float64; `industry_canonical_finest_candidates` List(String);
`source_parquet_sha256`, `acs_sample_id`, `OCCSOC`, `INDNAICS` and the node and type
columns String; every other carried column Int64. It adds `SERIAL` and `PUMA` (Int64),
which the derivation must drop. `core_row()` returns a 2023 full-time, full-year private
employee: `INCWAGE` 50000, `INCWAGE_CPIU_2010` 40000.0, `UHRSWORK` 40, `WKSWORK2` 6,
`CLASSWKR` 2, `CLASSWKRD` 22, `STATEFIP` 1, every Q column 0, `INDNAICS` `'6231'`,
common node `naics:2022:national_industry:623110`, delivered node
`naics:2022:industry_group:6231`. `core_frame` numbers `source_row` from 0 in list order
unless a row sets it.

- [ ] **Step 2: Write the failing tests**

```python
def test_output_columns_follow_the_spec_order():
    assert len(rules.CARRIED) == 120 and len(rules.OUTPUT_COLUMNS) == 130
    assert rules.OUTPUT_COLUMNS[:5] == ('source_parquet_sha256', 'source_row', 'YEAR',
                                         'acs_sample_id', 'PERWT')
    assert rules.OUTPUT_COLUMNS[-3:] == ('flag_full_time_full_year', 'flag_wage_salary',
                                          'flag_headline')
    assert set(rules.OUTPUT_COLUMNS) == set(rules.CARRIED) | set(rules.NEW)

def test_keeps_positive_wage_rows_in_source_order_and_drops_other_columns():
    # INCWAGE 0, 7, -1, 5 → rows with source_row 1 and 3 remain, in that order
    persons = rules.wage_persons(core_frame([...])).collect()
    assert persons['source_row'].to_list() == [1, 3]
    assert persons.columns == list(rules.OUTPUT_COLUMNS)   # SERIAL and PUMA gone

def test_carried_types_follow_the_input_schema():
    # an input with REPWTP37 as Float64 and OCC as String keeps those types
    schema = rules.wage_persons(frame).collect_schema()
    assert schema['REPWTP37'] == pl.Float64 and schema['OCC'] == pl.String
    assert schema['log_wage_2010'] == pl.Float64 and schema['flag_headline'] == pl.Boolean

@pytest.mark.parametrize('column', HEADLINE_ALLOCATION)
def test_each_headline_allocation_column_leaves_the_headline(column):
    row = rules.wage_persons(core_frame([core_row(**{column: 4})])).collect().row(0, named=True)
    assert row['flag_any_allocated'] is True and row['flag_headline'] is False

def test_qdegfield_alone_keeps_the_headline():
    row = ...(core_row(QDEGFIELD=4))
    assert row['flag_any_allocated'] is True and row['flag_headline'] is True

@pytest.mark.parametrize(('hours', 'weeks', 'expected'),
                         [(34, 6, False), (35, 6, True), (35, 5, False)])
def test_full_time_full_year_boundaries(hours, weeks, expected): ...

@pytest.mark.parametrize(('classwkrd', 'expected'), [(13, False), (14, False), (22, True),
    (23, True), (25, True), (27, True), (28, True), (29, False)])
def test_wage_salary_classes(classwkrd, expected): ...

def test_shared_node_spans_years():
    # category 'A' only in 2023 and 'B' only in 2024, both on one common node;
    # category 'C' on its own node in both years
    assert flags_by_category == {'A': True, 'B': True, 'C': False}

def test_topcode_flags_every_row_at_its_state_year_maximum():
    # state 1, 2023: 900, 900, 500 → True, True, False; state 1, 2024: 500 → True;
    # state 2, 2023: 700 → True
    ...

def test_node_parts_split_the_common_and_delivered_ids():
    # common 'naics:2022:sector:31-33', delivered 'naics:2022:sector:31-33'
    assert (row['industry_node_code'], row['industry_node_level'],
            row['industry_delivered_node_code']) == ('31-33', 'sector', '31-33')
    # common 'naics:2022:national_industry:623110', delivered 'naics:2022:industry_group:6231'
    assert (...) == ('623110', 'national_industry', '6231')

def test_log_wage_is_the_natural_log():
    assert row(INCWAGE_CPIU_2010=math.e)['log_wage_2010'] == pytest.approx(1.0)

@pytest.mark.parametrize('column', RULE_COLUMNS)
def test_refuses_a_null_rule_input(column):
    with pytest.raises(ValueError, match='null in a rule column'):
        rules.wage_persons(core_frame([core_row(**{column: None})])).collect()

@pytest.mark.parametrize('changes', [{'INCWAGE_CPIU_2010': 0.0},
    {'INCWAGE_CPIU_2010': -1.0}, {'INCWAGE': 999998}, {'INCWAGE': 999999}])
def test_refuses_bad_wage_values(changes):
    with pytest.raises(ValueError, match='wage value'): ...

def test_refuses_a_category_on_two_nodes(): ...          # match='more than one node'
def test_refuses_an_unparseable_node_id(): ...           # 'naics:2017:industry:11111',
                                                         # 'soc:2018:detailed:11-1021'
def test_refuses_source_rows_out_of_order(): ...         # match='source rows'
def test_refuses_a_missing_carried_column(): ...         # match='lacks a carried column'

def test_summarize_counts_the_funnel_flags_and_categories():
    # six rows built to hit each funnel step once in 2023 and once in 2024
    assert report == {expected dict written out in the test}

@settings(deadline=None)   # Polars aggregates on shared CPUs exceed 200 ms
@given(rows=st.lists(core_rows(), min_size=1, max_size=30))
def test_headline_is_the_conjunction_of_its_parts(rows):
    persons = rules.wage_persons(core_frame(rows)).collect()
    expected = ((~any nine Q != 0) & ftfy & wage_salary & ~shared)
    assert persons['flag_headline'].to_list() == expected
```

`core_rows()` is a Hypothesis strategy in the test file. It draws Q values from `{0, 4}`,
`UHRSWORK` from 30–40, `WKSWORK2` from 1–6, `CLASSWKRD` from the eight `DDI_LABELS`
codes, `STATEFIP` from 1–2, `YEAR` from 2023–2024, and `INDNAICS` from three categories,
two of which share a common node. It assigns `source_row` in list order.

`summarize` returns exactly these keys, with year keys as strings:

```python
{
    'contract': 'acs-wage-microdata-v1',
    'rows': {'total': int, 'by_year': {'2023': int, '2024': int}},
    'funnel': [  # cumulative, in this order
        {'step': 'earners', 'total': int, 'by_year': {...}},
        {'step': 'no_headline_allocation', ...},
        {'step': 'full_time_full_year', ...},
        {'step': 'wage_salary', ...},
        {'step': 'headline', ...},
    ],
    'flags': {name: {'total': int, 'by_year': {...}} for the six flag_* columns},
    'categories': [{'INDNAICS': str, 'YEAR': int, 'rows': int, 'headline_rows': int}],
    'headline_categories': {'2023': int, '2024': int},
    'shared_nodes': {'categories': int, 'nodes': int},
    'node_levels': {level: {'categories': int, 'headline_rows': int}},
}
```

`categories` is sorted by `INDNAICS`, then `YEAR`. The report has no run ID, time or
commit, so a replay can compare equal.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_acs_wage_rules.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'embedding_data.acs_wage_rules'`

- [ ] **Step 4: Implement `acs_wage_rules.py`**

- `earners(core)` refuses a core without every `CARRIED` column (`ValueError('core table
  lacks a carried column')`), keeps `INCWAGE > 0`, and selects `CARRIED` in order.
- `check_inputs(earners)` collects one row of aggregates and raises a `ValueError` with
  a fixed message that holds no data value:
  - `'null in a rule column'`;
  - `'wage value out of range'` for `INCWAGE_CPIU_2010 <= 0` or `INCWAGE` in
    `INCWAGE_CODES`;
  - `'source rows not strictly increasing'`;
  - `'category maps to more than one node'`, when an `INDNAICS` value has more than one
    common or delivered node;
  - `'unparseable NAICS 2022 node ID'`.
  A node ID must fully match
  `naics:2022:(sector|subsector|industry_group|industry|national_industry):(\d{2}-\d{2}|\d{2,6})`.
- `wage_persons(core)` calls `earners`, then `check_inputs`. It collects two small
  aggregates: the common nodes held by more than one `INDNAICS` value, and the maximum
  `INCWAGE` for each `STATEFIP` and `YEAR`. It returns a lazy plan that adds the `NEW`
  columns by splitting the node IDs and by joining the two aggregates with
  `maintain_order='left'`. It selects `OUTPUT_COLUMNS` and never collects person rows.
  `log_wage_2010` is `pl.col('INCWAGE_CPIU_2010').log()`.
- `summarize(persons)` computes the dict above with lazy aggregates.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_acs_wage_rules.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'
git add src/embedding_data/acs_wage_rules.py tests/acs_wage_fixtures.py tests/test_acs_wage_rules.py
git commit -m "feat(acs-wage): derive the wage microdata rows and flags"
```

### Task 2: Headline and node checks

**Files:**
- Create: `src/embedding_data/acs_wage_checks.py`
- Test: `tests/test_acs_wage_checks.py`

**Interfaces:**
- Consumes: `acs_wage_rules.HEADLINE_ALLOCATION`, `FULL_TIME_HOURS`,
  `FULL_YEAR_WKSWORK2`, `WAGE_SALARY_CLASSWKRD`; `core_frame`, `core_row` from Task 1.
- Produces:
  - `check_headline(persons: pl.LazyFrame) -> None` — spec item 5. Raises
    `ValueError('headline row breaks a headline rule')` when a headline row has a non-zero
    headline Q column, `UHRSWORK < 35`, `WKSWORK2 != 6`, `flag_wage_salary` false, or
    `flag_industry_shared_node` true.
  - `check_nodes(persons: pl.LazyFrame, nodes: pl.DataFrame, edges: pl.DataFrame) -> None`
    — spec item 6. `nodes` and `edges` have the Stage 4 `naics_nodes` and `naics_edges`
    schemas (`node_id, system, vintage, level, code, title` and `child_id, parent_id,
    edge_type`).

`check_nodes` reads the distinct (`industry_canonical_common_node_id`,
`industry_native_node_id`, `industry_node_code`, `industry_node_level`,
`industry_delivered_node_code`) tuples. It raises a `ValueError` with these fixed
messages:

- `'industry node is not a Stage 4 NAICS 2022 node'`: an ID is absent from `nodes` with
  `system == 'naics'` and `vintage == 2022`, or the node's `code` and `level` differ from
  the row's split parts.
- `'delivered node is not an ancestor of the join node'`: the delivered node differs from
  the join node and is not reached by walking up the `hierarchy` edges from the join node.
- `'delivered node chain branches'`: a node on the chain from the delivered node down to
  the join node's parent has more than one child in `edges`.

- [ ] **Step 1: Write the failing tests**

A test graph: `62 → 623 → 6231 → 62311 → 623110` (one child at each level) and
`561 → 5614 → {56141, 56142}`.

```python
def test_join_equal_to_delivered_passes(): ...                  # 5614 / 5614
def test_single_child_chain_passes(): ...                       # delivered 6231, join 623110
def test_branching_chain_is_refused(): ...                      # delivered 561, join 56141
def test_delivered_below_join_is_refused(): ...                 # delivered 62311, join 6231
def test_unknown_node_is_refused(): ...                         # join 999999
def test_split_parts_must_match_the_node_row(): ...             # code '6232' on node 6231
def test_headline_rows_obey_every_rule():
    rules.wage_persons(core_frame([...mixed rows...])).pipe(checks.check_headline)  # passes

@pytest.mark.parametrize('change', [{'QINCWAGE': 4}, {'UHRSWORK': 34}, {'WKSWORK2': 5},
    {'flag_wage_salary': False}, {'flag_industry_shared_node': True}])
def test_a_forged_headline_row_is_refused(change):
    # a derived frame with flag_headline forced true and one rule broken
    with pytest.raises(ValueError, match='headline rule'): ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_acs_wage_checks.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `acs_wage_checks.py`**

Both checks run lazy aggregates over the person rows. They collect only the distinct node
tuples and one row of headline violation counts. Build the parent map and child counts
from `edges` filtered to `edge_type == 'hierarchy'`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_acs_wage_checks.py tests/test_acs_wage_rules.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'
git add src/embedding_data/acs_wage_checks.py tests/test_acs_wage_checks.py
git commit -m "feat(acs-wage): check headline rules and NAICS 2022 nodes"
```

### Task 3: Pinned input selection and the fixture chain

**Files:**
- Create: `src/embedding_data/acs_wage_inputs.py`
- Modify: `tests/acs_wage_fixtures.py` (add the hook and the chain template)
- Test: `tests/test_acs_wage_inputs.py`

**Interfaces:**
- Consumes: `acs_wage_rules.DDI_LABELS`.
- Produces:
  - `MAPPING_FILES: frozenset[str]` — Stage 8's ten inventory names (the eight table
    Parquets, `inputs.json`, `report.json`).
  - `CODES_FILES: frozenset[str]` — Stage 4's fourteen inventory names (twelve Parquets,
    `inputs.json`, `report.json`).
  - `CORE_TABLE = 'acs_core_canonical.parquet'`.
  - `SOFTWARE_FILES: tuple[str, ...]` — every loaded `src/embedding_data/*.py` file of
    the command group, plus `pyproject.toml` and `uv.lock`. This task lists the modules
    that exist now. Tasks 4 and 5 each add their module. Task 5's test pins the final
    list.
  - `read_json(file: Path) -> dict` — strict: the root is an object, duplicate keys and
    non-finite numbers are refused.
  - `confirm_labels(ddi: dict) -> dict` — returns a copy of `DDI_LABELS` when every
    listed category of the `ipums_ddi.read_ddi` result has exactly that label. Otherwise
    raises `ValueError('delivered DDI labels differ')`.
  - `freeze_software() -> dict` — the Stage 10 shape: `files` (a `target_io.file_record`
    for each `SOFTWARE_FILES` name), `python`, `python_full`, `implementation`,
    `dependencies`, `uv_lock_sha256`.
  - `SelectedWageInputs` (frozen dataclass): `data_dir: Path`, `mapping_run: str`,
    `mapping_outputs_sha256: str`, `codes_run: str`, `codes_outputs_sha256: str`,
    `core: Path`, `naics_nodes: Path`, `naics_edges: Path`, `ddi: Path`,
    `labels: dict`, `provenance: dict`, with `verify(self) -> None`.
  - `select_wage_inputs(data_dir: Path, mapping_run: str, *, mapping_outputs_sha256: str,
    codes_run: str, codes_outputs_sha256: str) -> SelectedWageInputs`
  - Test helpers: `prepare_wage_delivery(profile, ddi, frame) -> tuple[dict, pl.LazyFrame]`,
    `CONTROLS: dict[int, dict]` (AGE marker to changes), `wage_mapping(tmp_path,
    monkeypatch) -> dict` with keys `data_dir`, `mapping_run` (`'mapping'`),
    `mapping_outputs_sha256`, `codes_run`, `codes_outputs_sha256`, and
    `copy_template(template: dict, tmp_path: Path) -> dict`.

**Default, flagged at plan review: how the build checks Stage 8** (spec, "Left to the
builder"). The build and `verify` check the detached pin first and then hash the whole
Stage 8 inventory (`target_io.verify_inventory`). They do not call
`acs_mapping_bundle.verify_bundle`, which re-derives every Stage 8 table (about 6 minutes
each in Stage 9). Stage 9 ran it twice in-process before its build was killed (exit 137),
and it would load `dotenv` and `ipumspy`. Task 9 runs Stage 8's public `verify` once, as a
read-only preflight, and the finding records it.

`select_wage_inputs` takes one snapshot, takes a second one, and refuses any difference
(`'selected inputs changed during validation'`). One snapshot does this, in order:

1. Refuse an unsafe run ID or a pin that is not 64 lowercase hex.
2. Mapping directory `derived/acs/mapping/<mapping_run>`, resolved with
   `target_io.relative_file`. Hash `outputs.json` against the pin before reading any other
   file (`'detached inventory checksum differs'`). Then run
   `target_io.verify_inventory(directory, outputs, MAPPING_FILES)`.
3. Read `inputs.json` with `read_json`. Refuse when
   `selected_upstreams.request.codes_run` or `.codes_outputs_sha256` differs from the
   explicit codes selection (`'codes selection differs from the mapping run'`).
4. Codes directory `derived/codes/<codes_run>`: the same pin check, then
   `verify_inventory(directory, outputs, CODES_FILES)`.
5. Take the one `raw_citations` entry of `sources['acs/core']` whose `path` ends in
   `.xml`. Check it with `target_io.verify_raw(data_dir, [entry])`. Read the file under
   `data_dir/'raw'` with `ipums_ddi.read_ddi`, then `confirm_labels`.
6. `provenance` = `{'mapping': {'run_id', 'outputs_sha256', 'outputs'}, 'codes': {...the
   same...}, 'ddi': <the verified manifest entry>}`.

`prepare_wage_delivery` starts from `acs_target_fixtures.prepare_target_delivery`. That
gives every core row `INDNAICS` `'113M'`, `IND` 190, non-null Q flags and the `REPWTP37`
float quirk. For profile `core` it then:

- adds `EDUCD`, `DEGFIELDD`, `QINCWAGE`, `QUHRSWOR`, `QWKSWORK2`, `QAGE`, `QSEX`, `QEDUC`
  and `QDEGFIELD` (Int64, 0) to the frame and, in the same order, to `ddi['variables']`.
  Stage 7 acceptance needs every Q flag in both;
- adds the `WKSWORK2` categories `0` to `6` (labels `N/A`, `1-13 weeks`, `14-26 weeks`,
  `27-39 weeks`, `40-47 weeks`, `48-49 weeks`, `50-52 weeks`) and the `CLASSWKRD`
  categories of `DDI_LABELS` that are not there yet;
- appends one control row for each `CONTROLS` entry. Each is a copy of the first 2023 row
  (the AGE 49 row copies the first 2024 row) with `INCWAGE` 50000,
  `INCWAGE_CPIU_2010` 40000.0, `UHRSWORK` 40, `WKSWORK2` 6, `CLASSWKR` 2, `CLASSWKRD` 22,
  every Q column 0, then the entry's changes:

| AGE | Changes | Expected in the wage file |
|---|---|---|
| 41 | none | headline |
| 42 | `QINCWAGE` 4 | allocated, not headline |
| 43 | `QDEGFIELD` 4 | allocated, headline |
| 44 | `UHRSWORK` 34 | not full time, not headline |
| 45 | `WKSWORK2` 5 | not full year, not headline |
| 46 | `CLASSWKR` 1, `CLASSWKRD` 14 | not wage/salary, not headline |
| 47 | `CLASSWKRD` 29 | not wage/salary, not headline |
| 48 | `INCWAGE` 0 | absent |
| 49 | 2024, `IND` 8780, `INDNAICS` `'811192'` | headline, node `811192` |
| 50 | `INCWAGE` 90000, two identical rows | headline, top-coded |

If Stage 7 `measure` or Stage 8 `build` refuses the hook's delivery, stop and report. Do
not edit a frozen module or an existing fixture.

`wage_mapping` calls `acs_target_fixtures.authenticated_mapping(tmp_path, monkeypatch,
prepare_acs=prepare_wage_delivery)` and reads the codes run and pin from its `request`.
Tests use a module-scoped template (`tmp_path_factory` and `pytest.MonkeyPatch.context()`,
as `tests/test_acs_target_inputs.py:15-27` does), `copy_template` for each test, and the
autouse guard `acs_mapping_fixtures.forbid_external_access`.

- [ ] **Step 1: Write the failing tests**

```python
def test_inventory_names_match_stages_8_and_4():
    assert inputs.MAPPING_FILES == set(acs_mapping_bundle.FILES)
    assert inputs.CODES_FILES == ita_establishment_inputs.INVENTORY_NAMES

def test_selects_the_pinned_mapping_codes_and_ddi(fixture):
    selected = select(fixture)
    assert selected.core == fixture['data_dir'] / 'derived/acs/mapping/mapping/acs_core_canonical.parquet'
    assert selected.labels == rules.DDI_LABELS
    assert set(selected.provenance) == {'mapping', 'codes', 'ddi'}

def test_wrong_mapping_pin_is_refused_before_inputs_are_read(fixture, monkeypatch):
    monkeypatch.setattr(inputs, 'read_json', forbidden)
    with pytest.raises(ValueError, match='detached inventory checksum differs'): ...

@pytest.mark.parametrize('edit', ['append_byte_to_core', 'add_extra_file', 'remove_report'])
def test_changed_mapping_inventory_is_refused(fixture, edit): ...

def test_codes_selection_must_equal_the_mapping_request(fixture): ...   # codes run 'other'
def test_wrong_codes_pin_is_refused(fixture): ...
def test_changed_ddi_bytes_are_refused(fixture): ...                     # verify_raw fails

def test_confirm_labels_refuses_one_changed_label():
    ddi = {'variables': [...DDI_LABELS with '22' relabeled 'Private'...]}
    with pytest.raises(ValueError, match='delivered DDI labels differ'): ...

@pytest.mark.parametrize('run_id', ['../mapping', '', '.hidden', 'a/b'])
def test_unsafe_run_ids_are_refused(fixture, run_id): ...

def test_symlinked_mapping_directory_is_refused(fixture): ...
def test_verify_detects_a_change_after_selection(fixture): ...           # append a byte

def test_read_json_is_strict(tmp_path):
    # duplicate key, NaN, a top-level list → ValueError each
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_acs_wage_inputs.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `acs_wage_inputs.py`**

Follow `src/embedding_data/ita_establishment_inputs.py` (`_snapshot`, `select_codes`)
for the double snapshot and the frozen dataclass. `SelectedWageInputs.verify()`
reselects with the same arguments and refuses any difference
(`'selected inputs changed'`).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_acs_wage_inputs.py -q --durations=5`
Expected: PASS. Note the template's setup time for Step 5.

- [ ] **Step 5: Mark slow tests and commit**

If a test's setup plus call takes 60 s or more, append its node ID to `SLOW_TESTS` in
`tests/conftest.py`.

```bash
pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'
git add src/embedding_data/acs_wage_inputs.py tests/acs_wage_fixtures.py tests/test_acs_wage_inputs.py tests/conftest.py
git commit -m "feat(acs-wage): select pinned Stage 8 and Stage 4 inputs"
```

### Task 4: Bundle build, verify and compare

**Files:**
- Create: `src/embedding_data/acs_wage_bundle.py`
- Test: `tests/test_acs_wage_bundle.py`

**Interfaces:**
- Consumes: `acs_wage_rules.wage_persons`, `summarize`, `CONTRACT`, `TABLE`, `RULES`;
  `acs_wage_checks.check_headline`, `check_nodes`;
  `acs_wage_inputs.select_wage_inputs`, `SelectedWageInputs`, `freeze_software`,
  `read_json`; `target_io.stage`, `write_json`, `inventory`, `verify_inventory`,
  `relative_file`; Task 3 test helpers.
- Produces:
  - `FILES = ('acs_wage_persons.parquet', 'inputs.json', 'report.json')`
  - `INPUT_FIELDS = frozenset({'run_id', 'contract', 'mapping', 'codes', 'ddi', 'labels',
    'rules', 'software', 'execution'})`
  - `run_directory(data_dir: Path, run_id: str) -> Path` —
    `paths.derived_dir(data_dir, 'acs') / 'wage-microdata' / run_id`, refusing an unsafe
    ID.
  - `ordered_compare(first: pl.LazyFrame, second: pl.LazyFrame, *, chunk_size: int =
    65536) -> dict` with keys `schema_equal`, `values_equal`, `first_rows`, `second_rows`.
  - `build(data_dir: Path, run_id: str, *, mapping_run: str, mapping_outputs_sha256: str,
    codes_run: str, codes_outputs_sha256: str) -> dict` with keys `run_id`, `directory`,
    `outputs_sha256`.
  - `verify_bundle(directory: Path, data_dir: Path, *, expected_outputs_sha256: str) ->
    dict` with keys `run_id`, `outputs_sha256`, `mapping_run`, `codes_run`, `rows`,
    `headline_rows`.
  - `compare_runs(first: Path, second: Path) -> dict` with keys `equal`, `table` (an
    `ordered_compare` result), `report_equal`, `trust_established` (always `False`).

`ordered_compare` streams both sides with `collect_batches(chunk_size=…,
maintain_order=True, lazy=True, engine='streaming')`. It holds one batch per side, the
same algorithm as `ipums_parity.compare_ordered`. That module cannot be imported here,
because it loads `ipumspy` (Global Constraints, Imports). Batch equality uses
`DataFrame.equals`, so a null against a value differs.

`build`, in order (model: `ita_establishment_bundle.build`):

1. `final, staging = target_io.stage(run_directory(...).parent, run_id, data_dir)`.
2. `software = freeze_software()`, then `selected = select_wage_inputs(...)`.
3. `wage_persons(pl.scan_parquet(selected.core)).sink_parquet(staging /
   'acs_wage_persons.parquet')`.
4. On the staged file: refuse an ordered schema other than `OUTPUT_COLUMNS` with the
   carried types of the core table and the `NEW` types. Refuse a `source_row` that is
   not strictly increasing, and a row count that differs from the core table's count of
   `INCWAGE > 0` rows (`'staged rows differ from the earners'`). The input check runs
   before the streaming join and sink, so only this check sees a reorder at scale. Then
   run `check_headline` and `check_nodes` with the Stage 4 tables.
5. Write `report.json` (`summarize` of the staged file) and `inputs.json`:
   `{'run_id', 'contract', 'mapping', 'codes', 'ddi'}` from the provenance, `labels`,
   `rules` (`RULES`), `software`, and `execution` = `{'commit', 'dirty', 'created_at'}`
   (`git rev-parse HEAD`, `git status --porcelain --untracked-files=normal`, UTC ISO time).
6. `selected.verify()` and `freeze_software() == software`, or refuse
   (`'executing software changed before publication'`).
7. Write `outputs.json` with `target_io.inventory(staging, list(FILES))`. Check the
   staged names, the final's absence, then rename. Return the pin
   (`manifest.sha256_file` of `outputs.json`).
8. In `finally`, remove the staging directory if it still exists, after
   `geography_references.safe_path(staging, data_dir)`.

`verify_bundle`, in order (model: `ita_establishment_bundle.verify_bundle`): refuse a
`.part` directory; refuse a malformed pin; hash `outputs.json` against the pin before
reading any other file; check the exact file set, `verify_inventory` and the inventory's
exact records; read `inputs.json` strictly with exactly `INPUT_FIELDS`, the directory's
run ID and `CONTRACT`; `select_wage_inputs` from the recorded runs and pins; require
`inputs['software'] == freeze_software()`; recompute `wage_persons` and compare it with
the published table by `ordered_compare`; run the step 4 order, count and both checks
on the published table; require `report.json ==
summarize(published)` and `inputs.json` equal to the recomputed inputs with the recorded
`execution`.

`compare_runs`: each side must be a published directory (not `.part`) that matches its
own `outputs.json` by `verify_inventory`. Compare the table with `ordered_compare` and
the reports exactly. Equality establishes replay, not trust.

- [ ] **Step 1: Write the failing tests**

`chain` is a per-test `copy_template` of the module-scoped Task 3 template, with the
autouse offline guard. `build(chain, run_id)` calls `acs_wage_bundle.build` with the
chain's mapping and codes runs and pins.

```python
def test_ordered_compare_streams_and_counts():
    # chunk_size=2: equal frames; a difference in the last batch; one extra row;
    # a renamed column; null against 0
    assert results == [(True, True), (True, False), (True, False), (False, False),
                       (True, False)]

def test_build_publishes_the_exact_file_set_and_pin(chain):
    result = build(chain, 'first')
    directory = Path(result['directory'])
    assert sorted(p.name for p in directory.iterdir()) == sorted([*FILES, 'outputs.json'])
    assert result['outputs_sha256'] == sha256(directory / 'outputs.json')

def test_rows_are_the_stage8_earners_in_order(chain):
    core = pl.read_parquet(stage8_core(chain)).filter(pl.col('INCWAGE') > 0)
    persons = pl.read_parquet(directory / 'acs_wage_persons.parquet')
    assert persons['source_row'].to_list() == core['source_row'].to_list()

def test_control_rows_get_their_expected_flags(chain):
    # one assertion per CONTROLS row, keyed by AGE (Task 3 table)

def test_report_holds_counts_and_no_run_identity(chain):
    report = json.loads((directory / 'report.json').read_text())
    assert set(report) == {'contract', 'rows', 'funnel', 'flags', 'categories',
                           'headline_categories', 'shared_nodes', 'node_levels'}
    text = json.dumps(report)
    assert 'first' not in text and 'created_at' not in text and 'commit' not in text

def test_inputs_record_pins_labels_rules_software_and_execution(chain): ...

@pytest.mark.parametrize('name', ['first', 'first.part'])
def test_occupied_run_path_is_refused_and_untouched(chain, name): ...

def test_leftover_part_blocks_only_its_own_run_id(chain):
    # a .part with one file: build('first') refused, bytes unchanged; build('second') passes

def test_failed_build_removes_only_its_staging(chain, monkeypatch):
    # summarize raises: no final, no .part, an existing sibling run unchanged

@pytest.mark.parametrize('distortion', ['reverse', 'drop_last_row'])
def test_build_refuses_reordered_or_missing_staged_rows(chain, monkeypatch, distortion):
    # monkeypatch acs_wage_rules.wage_persons to return the distorted plan
    with pytest.raises(ValueError, match='staged rows differ from the earners'): ...
    # no final and no .part remain

def test_symlinked_run_root_is_refused(chain): ...
def test_verify_passes_with_the_pin(chain): ...

def test_verify_refuses_a_wrong_pin_before_reading_inputs(chain, monkeypatch):
    monkeypatch.setattr(acs_wage_inputs, 'read_json', forbidden)

def test_verify_refuses_a_rehashed_edit(chain):
    # rewrite one AGE value, rewrite outputs.json with target_io.inventory, use the new pin
    with pytest.raises(ValueError, match='differs from the recomputation'): ...

def test_verify_refuses_changed_software(chain, monkeypatch): ...
def test_verify_refuses_a_part_directory(chain): ...

def test_replay_compares_equal(chain):
    assert compare_runs(first, replay) == {'equal': True, 'table': {...all True...},
                                           'report_equal': True, 'trust_established': False}

def test_compare_reports_a_rehashed_edit_as_unequal(chain): ...
def test_compare_refuses_an_inventory_mismatch(chain): ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_acs_wage_bundle.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `acs_wage_bundle.py`** as specified above.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_acs_wage_bundle.py -q --durations=5`
Expected: PASS

- [ ] **Step 5: Mark slow tests and commit**

```bash
pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'
git add src/embedding_data/acs_wage_bundle.py tests/test_acs_wage_bundle.py tests/conftest.py
git commit -m "feat(acs-wage): build, verify and compare wage microdata bundles"
```

### Task 5: Command group

**Files:**
- Create: `src/embedding_data/acs_wage_microdata.py`
- Test: `tests/test_acs_wage_microdata.py`

**Interfaces:**
- Consumes: `acs_wage_bundle.build`, `verify_bundle`, `compare_runs`, `run_directory`;
  `acs_wage_inputs.SOFTWARE_FILES`.
- Produces: `app` (Typer) with exactly three commands:

```text
build RUN_ID --data-dir ROOT --mapping-run ID --mapping-outputs-sha256 PIN --codes-run ID --codes-outputs-sha256 PIN
verify RUN_ID --data-dir ROOT --outputs-sha256 PIN
compare-runs FIRST_ID SECOND_ID --data-dir ROOT
```

Success prints one `json.dumps(result, sort_keys=True)` line. A failure prints only:

```text
ACS wage microdata <command> failed: <reason>; run <run_id>; path <path>
```

to stderr and exits 2. `<reason>` is `validation` (ValueError), `filesystem` (OSError) or
`unexpected`. `<path>` is the unvalidated run path, and both IDs, comma-joined, for
`compare-runs`. An unequal comparison prints its JSON line and exits 1, outside the
failure guard (model: `src/embedding_data/ita_establishment_targets.py`).

- [ ] **Step 1: Write the failing tests**

```python
def test_exactly_three_commands(): ...                  # {'build', 'verify', 'compare-runs'}
@pytest.mark.parametrize('argv', [...each command without --data-dir...])
def test_data_dir_is_required(cli_runner, argv): ...    # exit 2, Typer usage error
def test_options_reach_the_bundle_functions(cli_runner, monkeypatch, tmp_path): ...

def test_build_failure_prints_only_the_fixed_line(cli_runner, monkeypatch, tmp_path):
    # bundle.build raises ValueError('INCWAGE 123456 in row 7')
    assert result.exit_code == 2
    assert result.stderr == ('ACS wage microdata build failed: validation; run r1; '
                             f'path {tmp_path}/derived/acs/wage-microdata/r1\n')
    assert '123456' not in result.output

def test_compare_runs_exits_1_when_unequal(cli_runner, monkeypatch, tmp_path): ...
def test_top_level_cli_does_not_register_the_group():
    # the embedding_data.cli app has no command or group named like acs-wage

def test_module_runs_with_python_m(tmp_path):
    # subprocess `python -m embedding_data.acs_wage_microdata --help` exits 0

def test_software_files_cover_loaded_modules():
    # subprocess: import embedding_data.acs_wage_microdata, then list loaded
    # embedding_data module files; together with pyproject.toml and uv.lock they equal
    # SOFTWARE_FILES; 'dotenv' and 'ipumspy' are not in sys.modules

def test_real_commands_touch_no_network_env_or_builder(cli_runner, chain, monkeypatch):
    # target_fixtures.forbid_external_access plus denials of httpx.Client.__init__,
    # httpx.AsyncClient.__init__, code_build.build, geography_build.build and
    # acs_mapping_bundle.build; run build, verify and compare-runs through the CLI
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_acs_wage_microdata.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `acs_wage_microdata.py`**, then set
  `acs_wage_inputs.SOFTWARE_FILES` to the list that
  `test_software_files_cover_loaded_modules` reports.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_acs_wage_microdata.py tests/test_acs_wage_bundle.py tests/test_acs_wage_inputs.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'
git add src/embedding_data/acs_wage_microdata.py src/embedding_data/acs_wage_inputs.py tests/test_acs_wage_microdata.py tests/conftest.py
git commit -m "feat(acs-wage): add the offline wage microdata command group"
```

### Task 6: Fixture chain through the commands (spec item 9)

**Files:**
- Test: `tests/test_acs_wage_chain.py`

**Interfaces:**
- Consumes: `wage_mapping`, `CONTROLS` (Task 3); `app` (Task 5);
  `acs_target_fixtures.install_counted_guards`.

- [ ] **Step 1: Write the test**

```python
def test_raw_to_wage_microdata_is_offline_verified_and_replayable(tmp_path, monkeypatch):
    chain = wage_mapping(tmp_path, monkeypatch)        # raw → converter → Stages 4/5/7 → 8
    before = digests(chain['data_dir'])                # every file, wage-microdata excluded
    counts = {}
    install_counted_guards(monkeypatch, counts)
    first = invoke('build', 'first', ...)              # through CliRunner and app
    invoke('verify', 'first', '--outputs-sha256', first['outputs_sha256'], ...)
    replay = invoke('build', 'replay', ...)
    invoke('verify', 'replay', '--outputs-sha256', replay['outputs_sha256'], ...)
    compared = invoke('compare-runs', 'first', 'replay', ...)
    assert compared['equal'] is True and compared['trust_established'] is False
    assert all(count == 0 for count in counts.values())
    assert digests(chain['data_dir']) == before        # item 7, in the fixture
    persons = pl.read_parquet(first_directory / 'acs_wage_persons.parquet')
    # every CONTROLS row has its expected flags; AGE 48 is absent
    report = json.loads((first_directory / 'report.json').read_text())
    assert report['funnel'][-1]['total'] == persons['flag_headline'].sum()
```

- [ ] **Step 2: Run it**

Run: `uv run --locked pytest tests/test_acs_wage_chain.py -q --durations=3`
Expected: PASS. If setup plus call take 60 s or more, append the node ID to `SLOW_TESTS`.

- [ ] **Step 3: Commit**

```bash
pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'
git add tests/test_acs_wage_chain.py tests/conftest.py
git commit -m "test(acs-wage): prove the raw-to-bundle fixture chain"
```

### Task 7: Independent reconciler (spec item 4)

**Files:**
- Create: `scripts/reconcile_stage17.py`
- Test: `tests/test_reconcile_stage17.py`

**Interfaces:**
- Consumes: the published bundle format of Task 4 (file names and `inputs.json` fields),
  the Stage 8 and Stage 4 bundle formats. It imports no `embedding_data` module.
- Produces: an `argparse` program with required subcommands. This task adds `reconcile`:

```text
python scripts/reconcile_stage17.py reconcile --data-dir ROOT --run RUN_ID --outputs-sha256 PIN
```

It prints one `json.dumps(result, sort_keys=True)` line with `check` (`'persons'`), `run`,
`equal`, `rows`, `headline_rows` and `mismatches` (column name to count). It exits 0 only
when `equal` is true. A refusal prints `equal: false` and a fixed `reason`, and exits 1
(model: `scripts/reconcile_stage10.py`).

`reconcile`, with its own code only (standard library and Polars):

1. Hash `outputs.json` against the pin first. Check `acs_wage_persons.parquet`,
   `inputs.json` and `report.json` against their inventory records.
2. Read the recorded mapping run and pin. Hash Stage 8's `outputs.json` against that
   pin and the core table against its Stage 8 record. Do the same for the recorded
   codes run's `naics_nodes.parquet` and `naics_edges.parquet`.
3. Join the wage rows to Stage 8's rows through `source_row` (one to one). The `source_row`
   set must equal Stage 8's `INCWAGE > 0` rows, in the same order.
4. Compare every carried column, in groups of at most 20 columns, to bound memory.
5. Recompute the ten new columns from the Stage 8 columns with code written from the
   spec's "Rules for the new columns", not copied from `acs_wage_rules.py`. Compare them.
6. Recompute the funnel from the recomputed flags and compare it with `report.json`.
7. Check spec item 6 against the Stage 4 tables.

- [ ] **Step 1: Write the failing tests**

`chain_build` is Task 4's `chain` plus one `build` named `first`. Tests run the script in a
subprocess and parse its JSON line and exit code.

```python
def test_reconciler_imports_no_embedding_data_module():
    # AST scan of scripts/reconcile_stage17.py: no `embedding_data` import at all

def test_reconcile_reports_equal_on_a_fixture_build(chain_build): ...
def test_reconcile_counts_a_changed_carried_value(chain_build):
    # forged bundle: one AGE changed, inventory and pin rewritten
    assert result['equal'] is False and result['mismatches'] == {'AGE': 1}
def test_reconcile_counts_a_changed_flag(chain_build): ...  # {'flag_headline': 1}
def test_reconcile_refuses_a_wrong_pin(chain_build): ...    # exit 1, reason
def test_reconcile_refuses_a_missing_or_extra_row(chain_build): ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_reconcile_stage17.py -q`
Expected: FAIL (script missing)

- [ ] **Step 3: Implement `reconcile`** in `scripts/reconcile_stage17.py`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_reconcile_stage17.py -q --durations=3`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'
git add scripts/reconcile_stage17.py tests/test_reconcile_stage17.py tests/conftest.py
git commit -m "feat(acs-wage): add the independent Stage 17 reconciler"
```

### Task 8: Preservation controls (spec item 7)

**Files:**
- Modify: `scripts/reconcile_stage17.py` (add `freeze` and `preservation`)
- Test: `tests/test_reconcile_stage17.py`

**Interfaces:**
- Consumes: Task 7's program.
- Produces:

```text
python scripts/reconcile_stage17.py freeze --data-dir ROOT --control-dir DIR
python scripts/reconcile_stage17.py preservation --data-dir ROOT --control-dir DIR --freeze-sha256 PIN --runs FIRST,REPLAY
```

**Default, flagged at plan review.** No committed tool proves preservation for a stage
that adds only a derived directory. Stage 10 used an uncommitted script, and the Stage 8
and Stage 9 tools are bound to their own stages. This task adds one. Its control
directory is `ROOT/derived/acs/wage-microdata-controls/<FIRST_RUN_ID>`, after the Stage 8
`mapping-controls` precedent. Gate 1 covers writing it.

- `freeze` refuses a control directory that exists or that is not
  `ROOT/derived/acs/wage-microdata-controls/<ID>`. It creates the directory and writes
  `freeze.json`, then prints `{"freeze_sha256": …, "files": n}`. `freeze.json` holds:
  - `files`: SHA-256 and size of every regular file under `ROOT/raw` and `ROOT/derived`,
    except `raw/manifest.jsonl` and the `wage-microdata` and `wage-microdata-controls`
    trees;
  - `manifest`: the SHA-256, size and line count of `raw/manifest.jsonl`;
  - `runs`: the names under `derived/acs/wage-microdata/`.
  A symlink anywhere in the walk is refused.
- `preservation` hashes `freeze.json` against the pin first. It recomputes the walk and
  prints `{"status": "preserved" | "changed", "changed": [...], "missing": [...],
  "added": [...], "manifest_equal": bool, "runs": [...]}`, with paths only. `preserved`
  needs:
  - every frozen file equal, and no file added outside the named runs and the control
    directory;
  - the manifest's SHA-256 and size equal;
  - `wage-microdata/` holding exactly the frozen runs plus `--runs`, with no `.part`.
  It exits 0 only for `preserved`.

- [ ] **Step 1: Write the failing tests**

```python
def test_preserved_after_a_fixture_build(chain): ...
@pytest.mark.parametrize('damage', ['change_stage8_byte', 'add_stray_derived_file',
    'append_manifest_line', 'leave_part_directory', 'remove_raw_file'])
def test_preservation_reports_each_kind_of_change(chain, damage):
    assert result['status'] == 'changed' and exit_code == 1
def test_freeze_refuses_an_existing_or_misplaced_control_dir(chain): ...
def test_preservation_refuses_a_wrong_freeze_pin(chain): ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_reconcile_stage17.py -q`
Expected: FAIL on the new tests

- [ ] **Step 3: Implement `freeze` and `preservation`.**

- [ ] **Step 4: Run the full suite and lint**

```bash
pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'
uv run --locked pytest -q
uv run --locked behave
uv run --locked ruff check .
git diff --name-status main...HEAD -- src scripts tests features pyproject.toml uv.lock
```

Expected: pytest and Behave pass (the `network` canary deselected), ruff is clean, and the
diff shows only `A` lines, plus `M tests/conftest.py` if `SLOW_TESTS` grew.

- [ ] **Step 5: Commit**

```bash
pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'
git add scripts/reconcile_stage17.py tests/test_reconcile_stage17.py tests/conftest.py
git commit -m "feat(acs-wage): add Stage 17 preservation controls"
```

### Task 9: Production build, replay and finding (controller only)

**Files:**
- Create: `specs/naics-evaluation-data-stage-17-findings.md`

Run every command from the execution worktree with `ROOT=/Users/lowell/Projects/embedding-data/data`.
Run the spec's `pgrep` line before each command and stop if it prints anything. Write
each command's stdout, stderr and `time` output to the ledger
`.sdd/14-acs-wage-microdata/<step>.{out,err}`. `/usr/bin/time -l` writes to stderr.

- [ ] **Step 1: Preconditions.** `.sdd/` is not ignored in this repository. If `git
  check-ignore -q .sdd/` fails, append `.sdd/` to `$(git rev-parse
  --git-common-dir)/info/exclude`, a local file that is never committed. It applies to
  every worktree of this clone, including the primary checkout. Ledger files then cannot
  make the tree dirty. Tasks 1–8 are committed, and the full suite passed at this
  HEAD. `git status --porcelain --untracked-files=normal` prints nothing. Record
  `git rev-parse HEAD`. Choose `FIRST=stage17_acs_wage_microdata_<YYYYMMDD>_r1`,
  `REPLAY=${FIRST}_replay`, `CONTROL=$ROOT/derived/acs/wage-microdata-controls/$FIRST`.
  Confirm with `ls` that none of the three paths exists, and no `.part` beside them.

- [ ] **Step 2: GATE 1.** Ask the owner for the go-ahead for the freeze and the first
  build. Confirm that no Stage 9 freeze window is open and that no other stage's
  acquisition or full-data build is running. Show the output of `pgrep -fl
  'embedding_data|embedding-data'`. Tell the owner that Stage 17's preservation window
  opens at Step 4 and closes at Step 10, and that other stages' writes under `data/`
  wait until then.

- [ ] **Step 3: Stage 8 preflight (read-only).**

```bash
/usr/bin/time -l uv run --offline --locked python -m embedding_data.acs_mapping verify stage8_acs_mapping_20261018_r7 --outputs-sha256 1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4 --data-dir "$ROOT"
```

Expected: exit 0 and `"status": "verified"`. Otherwise stop and ask the owner.

- [ ] **Step 4: Freeze.**

```bash
uv run --offline --locked python scripts/reconcile_stage17.py freeze --data-dir "$ROOT" --control-dir "$CONTROL"
```

Record `freeze_sha256`.

- [ ] **Step 5: First build.**

```bash
/usr/bin/time -l uv run --offline --locked python -m embedding_data.acs_wage_microdata build "$FIRST" --data-dir "$ROOT" --mapping-run stage8_acs_mapping_20261018_r7 --mapping-outputs-sha256 1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4 --codes-run stage4_v11_20261013_r2 --codes-outputs-sha256 15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a
```

Expected: one JSON line with `outputs_sha256` (the first pin). Record the wall time and
`maximum resident set size`. If the build is killed and leaves `$FIRST.part`, leave it in
place, stop, record the event and ask the owner (gate 3). Use a new run ID afterwards.

- [ ] **Step 6: Verify the first run.**

```bash
/usr/bin/time -l uv run --offline --locked python -m embedding_data.acs_wage_microdata verify "$FIRST" --data-dir "$ROOT" --outputs-sha256 <first pin>
```

Expected: exit 0.

- [ ] **Step 7: Production counts (spec items 2 and 3).** From the first run's
  `report.json`:
  - `rows.total` is 3,035,086 (2023: 1,512,735; 2024: 1,522,351);
  - the `headline` funnel step is 1,278,878 (2023: 639,002; 2024: 639,876);
  - `headline_categories` is 233 for each year;
  - `shared_nodes` is 31 categories on 11 nodes.
  If any value differs, stop. The finding must explain the rule that differs before
  anything is adopted.

- [ ] **Step 8: Reconcile the first run (spec items 4 to 6).**

```bash
/usr/bin/time -l uv run --offline --locked python scripts/reconcile_stage17.py reconcile --data-dir "$ROOT" --run "$FIRST" --outputs-sha256 <first pin>
```

Expected: exit 0, `"equal": true`, empty `mismatches`.

- [ ] **Step 9: GATE 2 and the replay.** Ask for the replay go-ahead with the same two
  confirmations. Repeat Steps 5 and 6 with `$REPLAY` at the same commit and venv. Then
  compare:

```bash
/usr/bin/time -l uv run --offline --locked python -m embedding_data.acs_wage_microdata compare-runs "$FIRST" "$REPLAY" --data-dir "$ROOT"
```

Expected: exit 0, `"equal": true`, `"report_equal": true`, `"trust_established": false`.

- [ ] **Step 10: Preservation and repository checks (spec items 7 and 8).**

```bash
/usr/bin/time -l uv run --offline --locked python scripts/reconcile_stage17.py preservation --data-dir "$ROOT" --control-dir "$CONTROL" --freeze-sha256 <freeze pin> --runs "$FIRST,$REPLAY"
uv run --offline --locked embedding-data audit --data-dir "$ROOT"
git ls-files | grep -E '\.(parquet|csv|gz|jsonl)$'
```

Expected: `"status": "preserved"`, `0 raw provenance discrepancies`, and no output from
the `git ls-files` line. Confirm by reading `report.json` that it holds only counts.

- [ ] **Step 11: Top-code comparison (spec, `flag_incwage_topcoded`).** Run a read-only
  Polars query on the first run's table. For each `YEAR` and `STATEFIP` it gives the
  flagged `INCWAGE` value and its row count. Compare the values with IPUMS USA's "Values
  Exceeding Top codes, by State" page, for the years that page lists. Record the page's
  URL and the access date. A mismatch is recorded, not a stop. Record only state-level
  values.

- [ ] **Step 12: Bundle sizes.** Sum the bytes of each run's files.

- [ ] **Step 13: Write `specs/naics-evaluation-data-stage-17-findings.md`.** It is one
  screen, in the shape of `specs/naics-evaluation-data-stage-1-findings.md`. Include:
  - the run IDs, the three file hashes of each run (detached pin first), the executing
    commit with `dirty: false`, the Python version, and the counts of distributions and
    software files;
  - both owner go-aheads and their confirmations, and the `pgrep` notes;
  - a measured-cost table (command, wall time, maximum RSS) on the 36 GiB host, for the
    preflight, both builds, both verifies, the comparison, the reconciler and the
    preservation check;
  - the bundle sizes;
  - one line on each of spec items 1 to 9;
  - the top-code comparison;
  - `Not claimed`: no headline minimum count (O23), no protocol section (O24), no panel
    result, and no fixture result as evidence.

- [ ] **Step 14: Commit**

```bash
pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'
git add specs/naics-evaluation-data-stage-17-findings.md
git commit -m "docs: record the Stage 17 wage microdata build and replay"
```

### Task 10: Amendments and docs

**Files:**
- Modify: `specs/embedding-evaluation-data-spec.md:527`, `:536-542`, `:546-550`, `:557-561`
- Modify: `CLAUDE.md:232` and the end of `CLAUDE.md`
- Modify: `specs/deliverable-map.md:1`, `:3-18`
- Modify: `README.md` (a new section before `## Data sources`)

**Interfaces:**
- Consumes: the first pin, replay pin and run IDs of Task 9.

Line numbers are those of `main` at `2c2de1d`. Plan 13 (Stage 5) also edits `README.md`
(a section in the same place), the source spec and `CLAUDE.md`. Merge `main` into the
branch before this task, and place each edit by its quoted anchor text, not by line
number.

The spec gives amendment 1 verbatim and paraphrases items 2 to 4. The exact wording below
is shown to the owner at plan review. `<date>` is the execution date. Leave the spec's
status line alone.

- [ ] **Step 1: Amend the source spec (spec amendments 1 to 3).**

After R7.2's line `The co-ownership family is *(added at synthesis)*; the others are
*(chosen; D)*.`, add a new paragraph:

```markdown
The ACS wage microdata are a person-level analysis file, not a target family. The
worker-profile family above is unchanged. *(owner, plan 14, <date>)*
```

At the end of R7.4, after `crosswalk, and transformation versions. *(added at
synthesis)*`, add:

```markdown
The ACS wage microdata have their own schema, outside the long schema above.
*(owner, plan 14, <date>)*
```

At the end of R8.1, after `public-domain PUMS files instead. *(verified; USA)*`, add the
spec's sentence verbatim:

```markdown
One person-level analysis file, the ACS wage microdata, may be read in place on the
machine that built it, under its detached pin, to judge an economic candidate of
naics-embedder. The file never leaves that machine and never enters a repository. The
reader's results for single persons, such as predictions, residuals, cached folds and
debug output, are bound by the same rule. Only aggregate scores and decisions are
shared. *(owner, plan 14, <date>)*
```

At the end of R8.4, after `*(added at synthesis)*`, add:

```markdown
The ACS wage microdata only judge and never train. Their section in the evaluation
protocol states which part selects and which part judges. *(owner, plan 14, <date>)*
```

- [ ] **Step 2: Amend `CLAUDE.md` (spec amendment 4).** In line 232, replace
  `only aggregates are shared.` with `only aggregates are shared, except that
  naics-embedder may read the ACS wage microdata in place on this machine under their
  detached pin (R8.1).` Then append a short `**ACS wage microdata (Stage 17).**`
  paragraph after the Stage 10 paragraph. It names the command group and its three
  commands, the explicit `--data-dir`, the selected runs and pins from Task 9, the
  owner gates, the `pgrep` rule, the R8.1 and R8.4 limits, and the finding's path.

- [ ] **Step 3: Amend the deliverable map (spec amendment 4).** Refresh the line 1 stamp
  to `as of <date> at `<commit>``. Add this row after the `ACS and CPS worker profiles`
  row:

```markdown
| ACS wage microdata (person level) | Built and replayed (Stage 17). No count gate yet (O23) | No | No | **Yes.** It judges and never trains (R8.4). naics-embedder reads it in place on this machine under its pin (R8.1) | Its section in [the evaluation protocol](evaluation-protocol.md) (O24), its count gate (O23) and naics-embedder's wage panel spec |
```

- [ ] **Step 4: README.** Add `## ACS wage microdata (Stage 17)` before `## Data
  sources`, after the shape of `## ITA establishment targets (Stage 10)`
  (`README.md:285-441`): purpose, the command table, the exact production invocations of
  Task 9, the success and failure output, the bundle files, the owner gates and the
  `pgrep` rule, the limits (R8.1, R8.4), and the selected runs and pins.

- [ ] **Step 5: Check and commit.**

```bash
git diff --stat
uv run --locked pytest tests/test_acs_wage_microdata.py -q
pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'
git add specs/embedding-evaluation-data-spec.md CLAUDE.md specs/deliverable-map.md README.md
git commit -m "docs: apply the Stage 17 wage microdata amendments"
```

Expected: `git diff --stat` shows only the four files, and the source spec diff adds
exactly four paragraphs.

After Task 10, run the Plan Completion Protocol of writing-plans, including step 3a for
roadmap Stage 17 (O23 and O24 consume the counts in `report.json` and the finding).
