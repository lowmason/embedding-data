# Headline minimum count for the TRI parent links

> Next step: writing-plans, in a fresh session, against this file.

Status: APPROVED (2026-11-22, owner: "Yes"). Written 2026-11-22. The owner's approval of
this spec approves every constant and rule in it, the designer's calls included. So the plan
needs no owner stop between the rule commit and the first real run.

Design spec for Stage 22 of `specs/naics-evaluation-data-roadmap.md` (outcome O13). It sets
the headline minimum count for the one target of the TRI parent-link family,
`tri_parent_links` (measure `owner_share`). Owner decisions are dated 2026-11-22 and come from
the Stage 22 design session. Items marked **My call** are the designer's proposals that the
owner did not decide separately.

## Design provenance

A brainstorming session with the owner on 2026-11-22, in this repository at `b93efca`. The
inputs read were:

- the Stage 22 roadmap entry, the O13 row of the roadmap's outcome table and the Stage-spec
  stamp.
- the handoff brief `2026-11-22-stage-22-tri-minimum-counts.md` (outside the repository).
- the Stage 3 design `specs/completed/ita-naics-minimum-counts.md` and its decision
  `specs/findings/v9-ita-naics-minimum-counts.md`.
- the Stage 19 design `specs/acs-wage-minimum-earners.md`, the Stage 21 design
  `specs/usaspending-minimum-counts.md`, and the amendment steps of
  `specs/plans/17-acs-wage-minimum-earners.md` and `specs/plans/19-usaspending-minimum-counts.md`.
- the Stage 5 design `specs/completed/tri-parent-links.md`, the Stage 5 findings
  `specs/naics-evaluation-data-stage-5-findings.md` (sections "Counts", "Limits" and "For O12,
  O13 and O17") and the Stage 18 finding `specs/findings/stage-5-tri-parent-links.md`.
- "Rules for every new family" in `specs/uncovered-uses-evidence-sources.md`.
- R7.3, V9 and the Rollout sentence of `specs/embedding-evaluation-data-spec.md`.
- the source of `src/embedding_data/tri_parent_link_targets.py`,
  `src/embedding_data/tri_facility_years.py` and `src/embedding_data/tri_bundle.py` (table
  names, schemas, report keys, `SOFTWARE_FILES`), `target_io.inventory`, and the README
  section "TRI parent links (roadmap Stage 5)" with its host rule.

No file under `data/` was opened. No command read or wrote `data/`. `verify` was not run.

## Owner decisions (2026-11-22)

| # | Decision | Owner's words |
|---|---|---|
| D1 | The test is reporting-year recurrence with a TRIFD link (approach A1). The measurement reads the facility-year, support and target tables and `report.json` of the Stage 5 run in place. It outputs aggregates only. | "A1: TRIFD recurrence" |

### Proposals played back and not corrected (2026-11-22)

After D1, the session played back the rule below. The owner answered "Approved". The
proposals appear below as **My call** items:

1. Two year pairs, RY2022 → RY2023 and RY2023 → RY2024.
2. A testable cell recurs when any owner shows it in the next year.
3. V9's constants carry over. A top band with fewer than 50 testable cells merges into the
   band below it. A year pair with fewer than 50 testable cells in total gets no minimum.
4. The family minimum is the larger of the two year-pair minimums. A top band that misses the
   level stops the stage, with no fallback.
5. Both mirror rows of an industry pair count as cells, as in V9.
6. The gate applies to the published `n_unweighted`. Rows with a sensitivity label are gated
   like the others. Cells that exist only under a sensitivity get no gate.
7. Self-checks against the published tables and `report.json` come before any curve.
8. The script reads the first run only, checks the detached pin and each file record first,
   and outputs no TRIFD, no parent name and no cell list.

## Intent

naics-embedder will score its relatedness embedding against the TRI parent-link target. Most
cells are tiny. The median `n_unweighted` is 1, the 75th percentile is 2 and the 90th
percentile is 3 (Stage 5 findings, "Counts"). A cell that one owner holds up can come from one
facility's coding accident. A score that treats such cells as headline evidence measures noise
as well as the embedding. R7.3 says that the minimum for headline use comes "by measurement,
not argument". Every TRI target has SE `none`, because the counts come from all reports, not
from a sample.

The rule is: **a cell is headline evidence when cells of its count recur in the next reporting
year.** The minimum count is the smallest count at which recurrence reaches a level fixed
before the deciding curves are measured.

**What recurrence measures here.** A cell `(a,b)` counts the owners with an eligible facility
in industry `a` and one in industry `b` in the same year. EPA's standardized parent is the
current owner (E8), and the Stage 5 run measured 0 owner-key changes. So an owner keeps its
facilities in every year, and the test cannot see a change of ownership. Testability (below)
needs both linking facilities to file eligibly again. When both keep their codes, the cell
recurs through the same owner. So a testable cell fails only when a linking facility moves to
another eligible NAICS 2022 code and no other owner shows the cell. TRI uses NAICS 2022 codes
in every year of the window (Stage 5 design, "TRI uses NAICS 2022 codes from RY2022"), so a
code change is the facility's own report, not a change of edition. The test therefore measures
how stable the self-reported codes are that hold a cell up. This is V9's meaning, not
Stage 21's. A minimum that this test sets says that a cell is not a one-year coding accident.
It does not say that the relation is true.

## Goals

1. Measure, for each reporting-year pair, how often a cell recurs in the next year as a
   function of its owner count in the base year.
2. Set one minimum count for `tri_parent_links` from those curves by the rule below.
3. Report how many published target rows meet the minimum, and their share of rows and of
   support.
4. Record the decision in a decision record, and amend R7.3 and V9 so that they cover the TRI
   family.

## Non-goals

- The protocol section for the family (O17). Scoring, null models, splits and the treatment of
  absent (zero) cells belong to it.
- A minimum for `tri_parent_link_marginals`, `tri_parent_link_support`,
  `tri_parent_industries` or `tri_facility_years`. They are support, not targets.
- A minimum for the cells that exist only under a sensitivity (264 under the D&B key, 298 with
  federal facilities). They are not published rows.
- Rebuilding or relabeling either Stage 5 run. `size_gate_pending` stays on every row.
- The open question of how many `naics_*` facility-years name more than one parent (plan 18,
  Handoff). It affects only the partial-owner count, which no part of this rule reads.
- Minimums for any other family.
- The R8.4 training-role amendment (a separate owner decision after naics-embedder's spec).

## Anti-goals

- **A rule picked after seeing its result.** The rule and every constant are committed before
  the first run on real data. No constant changes after that run. A failed rule goes to the
  owner, never to a retuned constant.
  *Disclosure (2026-11-22):* before the rule was fixed, the session had seen these figures
  about the family and no others. All are published in the Stage 5 findings, which the owner
  can also read:
  - `n_unweighted` per row: 14,204 rows, minimum 1, median 1, 75th percentile 2, 90th
    percentile 3, maximum 50. 4,034 rows have 2 or more, 1,652 have 3 or more, 490 have 5 or
    more and 94 have 10 or more.
  - Facility-years by year and exclusion reason: eligible 21,534, 21,324 and 20,974,
    `federal` 448, 449 and 438, `naics_conflict` 108, 87 and 61, `naics_not_2022` 22, 10 and
    9, totals 22,112, 21,870 and 21,482.
  - Owners: headline 8,684 (8,080, 7,952 and 7,818 by year), D&B key 12,850, federal
    included 8,700, 0 owner-key changes, 0 parent-name collisions, 4,566 U.S. parents (median 2
    facilities and 1 industry, at most 477 facilities and 63 industries).
  - 405 industries in the marginals, 264 D&B-only cells, 298 federal-only cells and 102
    partial owners.
  - Facility-years with a D&B number: 13,560, 13,397 and 13,188 (section "E7 and E8
    measures").

  The downward merge of a thin top band (below) was proposed because only 94 rows (47
  industry pairs) have a pooled count of 10 or more. The session had also seen the V9 curves
  of the three ITA families. No per-year count, no testable count, no recurrence rate and no
  minimum for this family had been measured. Nobody opened `report.json` or any Parquet file
  of the run during design.
- **Identifiers leave the script.** The facility-year table holds TRIFDs, and its
  `owner_key` holds standardized parent names. The output and the decision record hold counts,
  rates and constants only. They hold no TRIFD, no parent name, no owner key and no list of
  cells.
- **Embedder results as input.** No embedder output, score or ranking is read (R8.4).
- **A broken Stage 5.** Change no file in `tri_bundle.SOFTWARE_FILES`
  (`src/embedding_data/tri_bundle.py:57-82` at the design commit, 24 files, including
  `pyproject.toml` and `uv.lock`). Change neither the Python build nor the installed
  distributions. Any of these makes `verify` refuse both Stage 5 runs.
- **Edited records.** Do not edit `scripts/measure_ita_minimum_counts.py`,
  `tests/minimum_count_fixtures.py`, `specs/naics-evaluation-data-stage-5-findings.md` or
  `specs/findings/stage-5-tri-parent-links.md`. Their records cite them as they are.

## Inputs (pinned, read in place, never rebuilt)

| Input | Identity |
|---|---|
| Stage 5 run `stage5_tri_parent_links_20261121_r1` (`data/derived/epa_tri/parent-links/`) | detached `outputs.json` SHA-256 `65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b` |
| Its `report.json` | must match its record in `outputs.json`. Its SHA-256 is `dc002222c0d9fa652f5623ef089dc324a000625d8a23fd681b3d227ed98d6a6e` (Stage 18 finding) |
| Its `tri_facility_years.parquet`, `tri_parent_link_support.parquet` and `tri_parent_links.parquet` | each must match its record (`sha256` and `size`) in `outputs.json` |

The script reads no other file of the run, reads no Stage 4 file and does not run `verify`.
`verify` costs about 1.5 GB and rebuilds the estimate. The pin and record checks are enough
for a read in place, as in Stage 21. **My call:** the script reads the first run only. The
replay `stage5_tri_parent_links_20261121_r1_replay` (pin
`555f6b58099da43c054d828d27048f31a9e992ee32719c7e1462c59b30919cfc`) has the same bytes in all
five Parquet files and in `report.json` (Stage 18 finding), so it adds nothing.

Columns read:

| File | Columns |
|---|---|
| `tri_facility_years.parquet` | `reporting_year`, `trifd`, `naics_2022_node_id`, `owner_key`, `exclusion_reason` |
| `tri_parent_link_support.parquet` | `unit_a`, `unit_b`, `j_owners`, `j_2022`, `j_2023`, `j_2024` |
| `tri_parent_links.parquet` | `measure`, `unit_a`, `unit_b`, `n_unweighted`, `flags` |
| `report.json` | `n_unweighted_distribution`, `owner_key_changes`, `n_owners.headline`, `owners_by_year.<year>.headline` |

`tri_facility_years.parquet` is the published table. It has no D&B number and no private
column. The bundle's private columns (`_candidate_key`, `_dnb_key` and the others) were never
written, so the script cannot read them.

## Approaches considered

**What test sets the minimum** (owner picked A1, D1):

| Approach | What it measures | Trade-off |
|---|---|---|
| **A1. Recurrence with a TRIFD link** | Whether cells of owner count k in year t appear again in year t+1, among cells whose linking facilities file eligibly again | V9's shape and V9's owner rule that exits do not count. A TRIFD is EPA's stable facility ID, so it links two years with no new linking rule. It reads the facility-year table, which goes beyond the roadmap's Consumes line |
| A2. Plain recurrence | The same, from the support table alone | No new read. But a facility that drops below TRI's reporting thresholds then counts as a failure, which the owner rejected for V9 |
| B. Count distribution only | The k at which kept cells hold a picked share of support | Reads nothing new. But the threshold is picked, not measured, so it needs an R7.3 exception. Stages 3 and 21 rejected it for that reason |

Three other tests were dropped:

- **D&B agreement**, that is, whether a cell also holds under the D&B owner key. About 39% of
  facility-years have no D&B number (13,560 of 22,112 have one in RY2022, Stage 5 findings,
  "E7 and E8 measures"). Their D&B key falls back to `facility:<TRIFD>`. So the test would
  measure D&B coverage, not the cell.
- **A random split of owners into halves.** It is circular: a cell with pooled count k appears
  in both halves only through its k.
- **A Poisson error.** It treats the counts as a sample, but they come from all reports.

**How it is built** (one sensible way, as in Stages 3, 19 and 21). A measurement script in
`scripts/` keeps the work outside the hashed software of every bundle. A new module or command
in `src/` would add software for a one-off measurement. A gate column would rebuild the Stage 5
bundle. An extension of the Stage 3 script would change a script that the V9 record cites as
unchanged.

### Where this follows or departs from Stages 3 and 21

| Point | Stage 3 (V9, ITA) | Stage 21 (USAspending) | Stage 22 (TRI) |
|---|---|---|---|
| What recurrence tests | code stability (codes filed each year) | whether a trade relation lasts (one fixed code per firm) | code stability, as V9 (owners are fixed, codes filed each year) |
| The link that makes a cell testable | visible links of an EIN's records | both firms still active in their roles | both TRIFDs file eligibly again under the same owner key |
| Cells | directed, mirrored | directed supplier → buyer, not mirrored | directed, mirrored, as V9 |
| What 50 cells are | 25 industry pairs | 50 observations | 25 industry pairs |
| Constants | `LEVEL` 0.90, `TOP_BAND` 10, `MIN_BAND_CELLS` 50 | V9's | V9's |
| Small lower bands | merge upward | merge upward | merge upward |
| A small top band | stands | stands | merges once into the band below (**new**) |
| A year pair with too few cells | not covered | not covered | no minimum, and the stage stops (**new**) |
| Minimums | one for each family | one for each measure (a singular-Exit deviation) | one, and the Exit holds as written |
| Self-checks | recount of the published counts | recount of all published counts | recount of the headline counts only. The sensitivity counts and labels need private columns and are read as published |
| Rollout sentence | wrote it | unchanged | unchanged |

## The rule

### Per-year counts

Let `E` be the eligible facility-years of `tri_facility_years.parquet` (`exclusion_reason` is
null). Each has a reporting year `t`, a TRIFD, a node `naics_2022_node_id` and an owner
`owner_key`. For a year `t` in 2022, 2023 and 2024, and an ordered pair of distinct nodes
`(a,b)`:

- `j_t(a,b)`: distinct owners with a facility-year of `E` in year `t` at node `a` and one at
  node `b`.

This is the Stage 5 estimand restricted to one year, and it equals the support table's
`j_{t}` (self-check). An owner `facility:<TRIFD>` has one facility-year in each year, so it
never forms a cell. Every cell comes from an owner `parent:<name>`.

### Recurrence and testable cells

A **base cell** of year t is a cell with `j_t(a,b) ≥ 1`.

A base cell **recurs** when `j_{t+1}(a,b) ≥ 1`. Any owner counts, the same owner included
(**My call**, as V9's "any employer").

A facility-year of `E` in year t is **staying** when its TRIFD also has a facility-year of `E`
in year t+1 under the same owner key. A base cell is **testable** when one owner has a staying
facility-year at node `a` and a staying facility-year at node `b` in year t. This is V9's owner
rule that exits do not count. A facility that leaves TRI, or that files an ineligible
facility-year in t+1 (`naics_conflict`, `naics_not_2022`, `federal`), makes no cell testable.
The node of the t+1 facility-year does not enter testability. A changed code is what the test
looks for.

With 0 owner-key changes, "under the same owner key" holds for every TRIFD that stays
eligible. The rule keeps the condition so that it stays correct if a TRIFD did change its key.

**A minimum of 1 is a valid result.** If cells with a count of 1 already recur at `LEVEL` or
more, every published row meets the gate. That is a measured outcome, not a broken rule.

### Year pairs

RY2022 → RY2023 (`2022-2023`) and RY2023 → RY2024 (`2023-2024`) (**My call**). These are the
only two pairs in the window.

### From curves to a minimum

Constants, committed before the first real run:

| Constant | Value | Decided by |
|---|---|---|
| `LEVEL` | 0.90 | the owner for V9, carried over (**My call**) |
| `TOP_BAND` | 10: counts of 10 and more form one band | V9, carried over (**My call**) |
| `MIN_BAND_CELLS` | 50 testable cells | V9, carried over (**My call**) |
| 95% Wilson interval | z = 1.959963984540054, for readers only | V9, carried over |

For each year pair:

1. Put each testable cell into a band by its base-year count `j_t(a,b)`. The bands are 1, 2,
   …, 9 and `10+`.
2. **Upward merge (V9).** Merge any band below `10+` with fewer than `MIN_BAND_CELLS`
   testable cells into the next higher band. Repeat until every band below the top has at
   least `MIN_BAND_CELLS` cells. A merged band starts at its lowest count.
3. **Downward merge (new, My call).** If the top band now has fewer than `MIN_BAND_CELLS`
   testable cells and a band lies below it, merge the top band into the band directly below
   it. The merged band starts at the lower band's start. After step 2 that lower band has at
   least `MIN_BAND_CELLS` cells, so one merge is enough and no loop is needed.
4. **Too few cells (new, My call).** If the year pair has fewer than `MIN_BAND_CELLS`
   testable cells in total, it gets no minimum. After step 3, this is the only way that the
   top band can have fewer than `MIN_BAND_CELLS` cells, including none.
5. A band's rate is its recurring cells divided by its testable cells.
6. The year pair's minimum is the lowest starting count of a band whose rate is at least
   `LEVEL`, where every higher band also reaches `LEVEL`.

Then:

7. The family minimum is the larger of the two year-pair minimums.
8. **No minimum without the level.** If a year pair gets no minimum under step 4, or if its
   top band misses `LEVEL`, the family gets no minimum. The stage stops, and the owner
   decides. No constant changes after a run. **My call:** no fallback is agreed in advance,
   for example a minimum from one year pair alone. A fallback chosen for the case where one
   year fails would be a rule chosen to rescue a result. V9, Stage 19 and Stage 21 have the
   same stop.

Rates use the point estimate. The Wilson interval does not enter the rule.

**Why the downward merge.** V9 lets a small top band stand. With few large cells, a top band
of a few testable cells can miss `LEVEL` through one or two code changes and stop the stage.
The merge stops a few cells from deciding the top band. It has a cost: the merged rate mixes
two bands. So the merge can move the minimum by one band either way, or turn a pass into a
stop. For example, a band at 9 with 60 testable cells at rate 0.88 and a top band with 20
cells at rate 1.0 merge to a rate of about 0.91 and a minimum of 9, although the cells at 9
alone miss `LEVEL`. The decision record reports the bands before the downward merge as well,
so a reader can see its effect.

**Mirrored cells (My call).** Both rows `(a,b)` and `(b,a)` of an industry pair are cells, as
in V9's co-ownership curves. The two have the same `j_t`, the same testability and the same
outcome. So a band's rate is the same as it would be over industry pairs. But 50 cells are 25
industry pairs, and the Wilson interval counts each pair twice, so it is too narrow. The
decision record says so.

**One minimum.** The family has one target and one measure, so it gets one minimum. The
roadmap Exit names "the headline minimum count", in the singular, and it holds as written.

### Where the minimum applies

A row of `tri_parent_links.parquet` meets the gate when its `n_unweighted` is at least the
minimum. `n_unweighted` is `J(a,b)`, the owners pooled over RY2022–2024. Both mirror rows of
an industry pair have the same `n_unweighted`, so they meet or miss the gate together. **My
call:** no pass-list file, because the gate is one comparison on a published column.

**The sensitivity labels (My call).** Rows that carry `numerator:dnb_key_sensitivity:true` or
`numerator:federal_sensitivity:true` are gated on their published `n_unweighted`, which uses
the headline owner key and excludes federal facilities. The labels stay as they are. The 264
D&B-only and 298 federal-only cells are not published rows, so no gate applies to them. The
measurement uses `E` only, which is the headline set.

**Leniency.** The curves use single-year counts, and the gate uses pooled counts. A pooled
count is never smaller than any single-year count, so the gate is a little lenient. The output
measures this: the kept rows whose largest single-year count (`j_2022`, `j_2023` or `j_2024`)
is below the minimum.

## What gets built

1. **A measurement script** in `scripts/` (name left to the plan), with tests in `tests/` that
   load it the way `tests/test_measure_ita_minimum_counts.py` loads its script.
   - Arguments: `--data-dir`, `--run` and `--outputs-sha256`. Nothing defaults to the real data
     tree.
   - It checks the detached pin first. Then each file it reads must match its record
     (`sha256` and `size`) in `outputs.json`, before any content is trusted. A failure prints a
     fixed reason and exits nonzero.
   - **Self-checks, before any curve.** Any difference stops the run.
     - Facility-years: `(reporting_year, trifd)` is unique, every year is in 2022–2024, and
       every row of `E` has an `owner_key` and a `naics_2022_node_id`.
     - The TRIFDs of `E` with more than one distinct `owner_key` number `owner_key_changes`
       of `report.json`. This is the bundle's own definition.
     - The distinct owners of `E`, pooled and by year, equal `n_owners.headline` and
       `owners_by_year.<year>.headline` of `report.json`.
     - The pooled recount over `E` gives the same set of cells as
       `tri_parent_link_support.parquet`, and for every cell the same `j_owners`, `j_2022`,
       `j_2023` and `j_2024`.
     - `tri_parent_links.parquet` has one row for each support cell, every `measure` is
       `owner_share`, and each `n_unweighted` equals the cell's `j_owners`.
     - The distribution of `n_unweighted`, recomputed with the bundle's own definition
       (`tri_parent_link_targets.distribution`, unchanged), equals `n_unweighted_distribution`
       of `report.json`.

     Not rechecked: `j_dnb`, `j_including_federal` and the two sensitivity labels. They need
     the private `_dnb_key` and `_candidate_key` columns, which no published table holds. The
     script reads the labels from `flags` as published, only to count kept rows.
   - It reads the Parquet files through lazy scans of the columns above.
   - Output: one sorted JSON line on stdout and nothing else. It holds:
     - the rule constants and the input pins.
     - for each year pair: the base cells and testable cells in total, the bands (start, end,
       base cells, testable cells, recurring cells, rate and Wilson interval) and the
       year-pair minimum or its absence with the reason. When the downward merge happens,
       it also gives the two bands as they were after the upward merge.
     - the family minimum, the pooled `n_unweighted` distribution as `report.json` gives it,
       and the kept counts: the rows, the support (the sum of `n_unweighted`), the kept rows
       and their share, the kept support and its share, the lenient kept rows, and the kept
       rows among the rows with each sensitivity label.

     It holds no TRIFD, no parent name, no owner key and no cell list.
   - It writes nothing under `data/`. The JSON output never enters git. The decision record
     cites its SHA-256, as Stages 3 and 21 did.
2. **Two real runs.** The plan runs the script twice on the pinned input. The two outputs must
   be byte-identical. The decision record gives their SHA-256, the command, and the wall time
   and maximum RSS of one run (`/usr/bin/time -l`). **My call:** save a
   `pgrep -fl 'embedding_data|embedding-data'` list right after each run. The record calls a
   wall time "loaded" only if that list shows another job.
3. **The decision record** `specs/findings/v9-tri-minimum-counts.md` (**My call**, beside the
   other V9 records). It gives the rule and constants with the commit that fixed them before
   the first run, the inputs and pins, the curve of each year pair, the minimum, the kept
   counts, the lenient count, the number of kept industry pairs (half the kept rows), the
   design-time disclosure above, the Consumes deviation below and the limits below.
4. **Spec amendments** in `specs/embedding-evaluation-data-spec.md`:
   - R7.3: the decision record sets the minimum for the TRI parent-link family. "Every other
     family" then no longer includes it.
   - V9: the same decision covers the TRI parent-link family after its first full build.
   - Rollout: no change (**My call**, as in Stage 21). Its sentence already sets "each
     family's cell-count gate" before any embedder is scored on that family, and TRI parent
     links are a family.

   Plans 17 (Stage 19) and 19 (Stage 21) append sentences to the same two paragraphs. At the
   design commit, `origin/main` is `b93efca` and holds neither. At execution, run
   `git fetch origin`, read R7.3 and V9 in
   `git show origin/main:specs/embedding-evaluation-data-spec.md`, merge `origin/main` into
   the branch if either has merged (never rebase), and append after the last owner tag of each
   paragraph. Find each passage by its quoted text, never by a line number.
5. **Stale lines.** Each is changed to name the decision record. The line numbers hold at the
   design commit only. Find each passage by its quoted text.
   - `CLAUDE.md:489-490`, section "TRI parent links (roadmap Stage 5)": "Every target keeps
     `size_gate_pending`, and no headline minimum count (O13) exists yet." Keep
     `size_gate_pending`, and name the decision record for O13.
   - `specs/deliverable-map.md:13`, the row "EPA TRI parent links". Its Status cell ends "No
     count gate yet". Its "Still blocked by" cell begins "Its count gate (O13, on the Ranked
     list)", and "on the Ranked list" is already stale, because O13 left the list as Stage 22.
     After the change, the Status cell names the count gate (Stage 22) with the minimum and
     its kept rows. The row is then blocked only by O17 and by R8.4, if the family trains.
   - `README.md`, section "TRI parent links (roadmap Stage 5)". It has no minimum-count
     sentence. Add one that names the decision record and says that the published targets
     keep `size_gate_pending` (**My call**, as in Stage 21).

## Constraints

- **Frozen software.** Change no file in `tri_bundle.SOFTWARE_FILES`, the Stage 6
  `FROZEN_MODULES` and `TARGET_MODULES`, the Stage 7 to 9 software, `cli.py` or
  `code_references.py`. Add no dependency and no console entry point. New files go in
  `scripts/` and `tests/` only. The script may import from `embedding_data`. It may load the
  band functions of `scripts/measure_ita_minimum_counts.py` unchanged, or copy them (left to
  the builder). The downward merge is new, so it is new code either way.
- **Offline and credential-free.** No network, no `.env`, no HTTP client, no upstream builder
  and no `verify` run inside the script.
- **Freeze window.** Before each real run, each full pytest run and each commit, run
  `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'` and stop if it
  prints anything (`CLAUDE.md`, README host rule part 3).
- **Host rule.** README's host rule governs production writes: acquisitions, imports, builds
  and cleanup. The script reads the run in place and writes nothing under `data/`, so it is
  not a production write. Part 2 (the owner judges the broad `pgrep` list), part 4 (owner
  confirmation) and part 5 (owner go-ahead) do not apply. **My call:** follow parts 1 and 3,
  as Stage 21 does. Run one real run at a time. Before each, also run
  `pgrep -fl 'embedding_data|embedding-data'`, and the person who runs the script looks at
  each match. The pattern also matches its own shell and any Python process in a project venv,
  so a match alone is no stop. Do not start while a full-data build or another full-data
  measurement runs (roadmap, "Shared resources").
- **Sibling work.** The Stage 19 and Stage 21 worktrees and branches, and the Codex branch
  `codex/acs-targets-design`, are not touched. Before editing a shared file (`CLAUDE.md`,
  `README.md`, `specs/deliverable-map.md`, `specs/embedding-evaluation-data-spec.md`), run
  `git status --short` in each sibling worktree, and `git log` and `git diff` against `main`
  on each sibling branch. Their work is partly uncommitted.
- **Leave alone.** The TRI runs under `data/derived/epa_tri/parent-links/`, the raw tree
  under `data/`, `data/raw/manifest.jsonl` and the Stage 18 evidence directory
  `/Users/lowell/.cache/embedding-data/stage-18/`.
- **Rule before data.** The script, its tests and its constants are committed before the first
  real run. The decision record cites that commit. **My call:** a later code fix that only
  makes the script match this written rule is allowed, and the decision record discloses it.
  Any change to the written rule goes to the owner.
- **Tests.** Red → green on small synthetic bundles in a temporary `--data-dir`, through the
  script's functions and its command line. They cover:
  - the per-year counts, and an owner `facility:<TRIFD>` that forms no cell.
  - the staying rule: a facility that leaves, or that files an ineligible facility-year in
    t+1, makes no cell testable. A facility that stays with a changed code makes a testable
    cell that fails.
  - recurrence through the same owner and through another owner.
  - banding, the upward merge, the one downward merge, and the stop for a year pair with fewer
    than `MIN_BAND_CELLS` testable cells.
  - the monotone rule and the stop for a top band that misses `LEVEL`.
  - the mirrored cells, the lenient count and the kept counts among labeled rows.
  - each self-check failure, the pin and record refusals, and determinism.
  - an output that holds none of the fixture TRIFDs or parent names.

  No test reads the real tree.
- **Aggregates only.** R8.1 to R8.4 hold. The output and the decision record contain counts,
  rates and constants only.

## Limits (for the decision record)

- Recurrence measures whether the self-reported codes that hold a cell up stay the same among
  facilities that keep filing. It does not measure truth. A facility with a wrong code that
  files the same code every year recurs every year.
- **E8 time basis.** EPA's standardized parent is the current owner at the snapshot, not the
  owner in each year. So the test cannot see a change of ownership, and a cell can rest on an
  ownership that did not hold in the base year.
- Testability keeps only cells with a linking pair of facilities that both file eligibly
  again. Facilities that leave TRI are out, and so are ineligible refiles. The published
  counts bound the `naics_*` refiles only: 97 `naics_*` facility-years in RY2023 and 70 in
  RY2024. They do not bound a facility that turns `federal`.
- RY2024 completeness depends on the snapshot (2025-11-05). Under this rule a missing RY2024
  report removes a cell from the test. It does not count as a failure.
- Codes are self-reported and unvalidated.
- TRI is a program-selected population, mostly industrial. It is not a frame of
  establishments or firms. Cells that the bundle does not emit get no statement.
- Mirrored cells count each industry pair twice, so the Wilson intervals are too narrow.
- The gate applies to counts pooled over three reporting years, so it is a little lenient
  (measured).
- The minimum is a reliability floor for headline use. It is not a coefficient-of-variation
  rule.

## Left to the builder

- The script's name, its internal structure and the JSON key names.
- Whether it loads the Stage 3 band functions or copies them.
- Fixture design, and the exact wording of the amendments and the stale-line changes within the
  meaning above.

## Rollout

The plan executes in a fresh session. The decision record, the spec amendments and the
stale-line changes land in one branch with the script.

**My call, as plan 19:** the branch merges through a PR that the owner approves, with a merge
commit. So the owner sees the measured minimum before the R7.3 and V9 amendments land. The
decision record cites the rule commit by its SHA, so the branch is never squashed or rebased
after that commit. A later `main` comes in by a merge.

Stage 22's Consumes line names `report.json` and says that the per-cell counts are the
`n_unweighted` column of `tri_parent_links`. The O13 cost estimate is "one pass over the TRI
family's `n_unweighted` counts, like O4". Under D1 the measurement also reads
`tri_facility_years.parquet` and `tri_parent_link_support.parquet`. So the plan records a
`> Deviation:` note against the Stage 22 Consumes line and cost (owner, D1, 2026-11-22). The
stamp cites the note. The Exit holds as written: the minimum comes from the observed
`n_unweighted` counts, split by reporting year, and the decision reports how many cells meet
it.

> Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 22 — on plan
> completion, tick the stage and re-validate later stages against what shipped.
