# Headline minimum counts for the USAspending vendor links

> Next step: writing-plans, in a fresh session, against this file.

Status: DRAFT for owner review. Written 2026-11-22. The owner's approval of this spec
approves every constant and rule in it, the designer's calls included. So the plan needs no
owner stop between the rule commit and the first real run.

Design spec for Stage 21 of `specs/naics-evaluation-data-roadmap.md` (outcome O26). It sets
the headline minimum count for the two targets of the USAspending vendor-link family,
`supplier_share` and `buyer_share`. Owner decisions are dated 2026-11-22 and come from the
Stage 21 design session. Items marked **My call** are the designer's proposals that the owner
did not decide separately.

## Design provenance

A brainstorming session with the owner on 2026-11-22, in this repository at `dae8f4e`. The
inputs read were:

- the Stage 21 roadmap entry and the roadmap's Choices made.
- the Stage 3 design `specs/completed/ita-naics-minimum-counts.md`, its decision
  `specs/findings/v9-ita-naics-minimum-counts.md` and the Stage 19 design
  `specs/acs-wage-minimum-earners.md`.
- the Stage 14 design `specs/completed/usaspending-vendor-links.md`, the Stage 14 findings
  `specs/naics-evaluation-data-stage-14-findings.md` and the Stage 20 finding
  `specs/findings/stage-14-usaspending-vendor-links.md`.
- "Rules for every new family" in `specs/uncovered-uses-evidence-sources.md`.
- R7.3, V9 and the Rollout sentence of `specs/embedding-evaluation-data-spec.md`, and the
  amendment steps of `specs/plans/17-acs-wage-minimum-earners.md`.
- the source of `src/embedding_data/vendor_link_targets.py` and
  `src/embedding_data/vendor_link_bundle.py` (table names, report keys, `SOFTWARE_FILES`) and
  the function names of `scripts/measure_ita_minimum_counts.py`.

No file under `data/` was opened. No command read or wrote `data/`.

## Owner decisions (2026-11-22)

| # | Decision | Owner's words |
|---|---|---|
| D1 | The test is fiscal-year recurrence (approach A). The measurement reads the pair table of the Stage 14 run in place, and it outputs aggregates only. | "A: FY recurrence" |
| D2 | A cell recurs in the next fiscal year when any eligible pair links its two industries in that year. The same pair counts. | "Any pair" |

### Proposals played back and not corrected (2026-11-22)

The session played these back after D1. The owner did not correct them and answered D2. They
appear below as **My call** items.

1. Per-year counts come from the eligible pairs with a usable report in that fiscal year.
   Firm industries and pair status stay as the bundle set them for the whole window. A
   self-check comes first.
2. A cell is testable only when one of its pairs has both firms still in an eligible pair the
   next year. Exits do not count, as in V9. Both measures share this test.
3. Each measure gets its own curve and its own minimum.
4. V9's constants and band rule carry over.
5. The gate applies to each row's published `n_unweighted`. The 71 rows with the intra-group
   label are gated like the others. The 7 cells that exist only under the intra-group
   sensitivity are not rows and get no gate.

After D2, the session proposed to keep both year pairs and a measurement script in
`scripts/`. The owner then asked for this spec ("Write the spec").

## Intent

naics-embedder will score its relatedness embedding against the vendor-link targets. Most
cells are tiny. The median `n_unweighted` is 1 for `buyer_share` and 2 for `supplier_share`
(Stage 14 findings, "For the resume and O18"). A cell that one firm holds up can be a one-off
subcontract. A score that treats such cells as headline evidence measures noise as well as the
embedding. R7.3 says that the minimum for headline use comes "by measurement, not argument".
Every vendor-link target has SE `none`, because the counts come from all reports, not from a
sample.

The rule is: **a cell is headline evidence when cells of its count recur in the next fiscal
year.** A trade relation between two industries that firm pairs show again is not a one-off.
The minimum count is the smallest count at which recurrence reaches a level fixed before the
deciding curves are measured.

**What recurrence measures here.** In V9 the count and the code came from the same filing
each year, so recurrence tested whether a code was stable. Here each firm has one industry
from one SAM.gov extract, so a firm's code cannot change between years. Recurrence tests
whether the relation between two industries persists among firms that still contract. The
rule keeps V9's shape, but it answers this different question.

## Goals

1. Measure, for each measure and each fiscal-year pair, how often a cell recurs in the next
   fiscal year as a function of its firm count in the base year.
2. Set one minimum count for each measure from those curves by the rule below.
3. Report, for each measure, how many published target rows meet its minimum, and their share
   of rows and of support.
4. Record the decision in a decision record, and amend R7.3 and V9 so that they cover the
   vendor-link family.

## Non-goals

- The protocol section for the family (O18). Scoring, null models, splits and the treatment
  of absent (zero) cells belong to it.
- A minimum for the marginal, support or pair tables. They are support, not targets.
- Rebuilding or relabeling either Stage 14 run. `size_gate_pending` stays on every row.
- A changed D2 rule and the live `acquire-sam-extract` request (`specs/deferred_items.md`,
  section `15-usaspending-vendor-links`).
- Minimums for any other family, including TRI parent links (O13).
- Whether any table may leave the machine (E6, the owner's decision).

## Anti-goals

- **A rule picked after seeing its result.** The rule and every constant are committed before
  the first run on real data. No constant changes after that run. A failed rule goes to the
  owner, never to a retuned constant.
  *Disclosure (2026-11-22):* before the rule was fixed, the session had seen these figures
  about the family and no others. All are published in the Stage 14 findings, which the owner
  can also read:
  - `n_unweighted` per cell: median 1 (`buyer_share`) and 2 (`supplier_share`), p90 6 and 11,
    maximum 260 and 1,101. 4,810 of 8,307 `buyer_share` cells and 4,025 `supplier_share`
    cells have count 1.
  - Usable reports by fiscal year: 227,218 (FY2024), 177,666 (FY2025) and 117,644 (FY2026).
  - Pair statuses (67,524 eligible, 22,569 `sub_ineligible`, 17,722 `prime_ineligible`, 147
    intra-group and 32 self links), 28,410 suppliers and 2,215 buyers, 8,307 cells in 689
    industries, 7 cells only under the sensitivity, 71 rows with the intra-group label, and
    the diagonal (88 cells, 6,180 pairs).

  The session had also seen the V9 curves of the three ITA families. No per-year S or B, no
  testable count, no recurrence rate and no minimum for this family had been measured. Nobody
  opened `report.json` or any Parquet file of the run during design.
- **UEIs leave the script.** The pair table holds UEIs. The output and the decision record
  hold counts, rates and constants only. They hold no UEI, no amount and no list of cells.
- **Embedder results as input.** No embedder output, score or ranking is read (R8.4).
- **A broken Stage 14.** Change no file in `vendor_link_bundle.SOFTWARE_FILES`
  (`src/embedding_data/vendor_link_bundle.py:58-85`, 26 files, including `pyproject.toml` and
  `uv.lock`). A change makes `verify` refuse both Stage 14 runs.
- **Edited records.** Do not edit `scripts/measure_ita_minimum_counts.py`,
  `scripts/reconcile_usaspending_vendor_links.py` or
  `specs/naics-evaluation-data-stage-14-findings.md`. Their records cite them as they are. The
  frozen Stage 14 findings call the minimum count "O18", and that old label stays there. O26
  is the minimum count, and O18 is the protocol section.

## Inputs (pinned, read in place, never rebuilt)

| Input | Identity |
|---|---|
| Stage 14 run `stage14_vendor_links_20261122_r2` (`data/derived/usaspending/vendor-links/`) | detached `outputs.json` SHA-256 `248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be` |
| Its `report.json` | must match its record in `outputs.json`. Its SHA-256 is `040127fbb64d1dc7e2791f337506994092c4aab42abedfe3af94deff01f913d2` (Stage 20 finding) |
| Its `vendor_link_pairs.parquet`, `vendor_link_support.parquet` and `vendor_links.parquet` | each must match its record (SHA-256 and size) in `outputs.json` |

The script reads no other file of the run, reads no Stage 4 file and does not run `verify`.
**My call:** it reads the first run only. The replay `stage14_vendor_links_20261122_r2_replay`
has the same bytes in all four Parquet files and in `report.json` (Stage 20 finding), so it
adds nothing.

Columns read:

| File | Columns |
|---|---|
| `vendor_link_pairs.parquet` | `prime_uei`, `sub_uei`, `n_reports`, `n_fy2024`, `n_fy2025`, `n_fy2026`, `prime_node_id`, `sub_node_id`, `pair_status` |
| `vendor_link_support.parquet` | `unit_a`, `unit_b`, `s_suppliers`, `b_buyers`, `l_pairs`, `l_fy2024`, `l_fy2025`, `l_fy2026` |
| `vendor_links.parquet` | `measure`, `unit_a`, `unit_b`, `n_unweighted`, `flags` |
| `report.json` | `n_unweighted_distribution`, with one entry for each measure |

## Approaches considered

**What test sets the minimum** (owner picked A, D1):

| Approach | What it measures | Trade-off |
|---|---|---|
| **A. Fiscal-year recurrence** | Whether cells of firm count k in FY t appear again in FY t+1 | A real measurement in V9's shape. It recomputes per-year firm counts from the UEI pair table, which costs more than the roadmap's "one pass over counts". The short FY2026 is likely to set the minimum |
| B. Count distribution only | The k at which kept cells hold a picked share of support | Cheap, and it matches the roadmap's Consumes line. But the threshold is picked, not measured, so it needs an R7.3 exception. Stage 3 rejected it for that reason |

Two other tests were dropped. A random split of firms into halves is circular: a cell with
pooled count k appears in both halves only through its k. A Poisson error treats the counts as
a sample, but they come from all reports.

**What counts as recurrence** (owner picked any pair, D2):

| Choice | A cell recurs in FY t+1 when | Trade-off |
|---|---|---|
| **Any pair** | any eligible pair links `s` to `d` in FY t+1, the same pair included | Measures persistence, with the same rule as V9's "any employer". A multi-year subcontract with a new report each year recurs, even when one firm's SAM code is wrong |
| A different pair only | only a pair that did not report in the cell in FY t links `s` to `d` | Measures whether other firms repeat the relation. The count already measures how many firms show it, so this counts breadth twice and pushes the minimum up |

**How it is built** (one sensible way, as in Stages 3 and 19). A measurement script in
`scripts/` keeps the work outside the hashed software of every bundle. A new module or command
in `src/` would add software for a one-off measurement. A gate column would rebuild the
Stage 14 bundle. An extension of the Stage 3 script would change a script that the V9 record
cites as unchanged.

## The rule

### Per-year counts

Let `P` be the eligible pairs of the pair table (`pair_status` is `eligible`). Each has a
subcontractor `u` with node `ind(u)` (`sub_node_id`) and a prime `p` with node `ind(p)`
(`prime_node_id`). For a fiscal year `t` in 2024, 2025 and 2026, let `P_t` be the pairs in `P`
with `n_fy{t} > 0`. For a cell `(s,d)`:

- `S_t(s,d)`: distinct subcontractors `u` with `ind(u) = s` in a pair of `P_t` with a prime in
  `d`.
- `B_t(s,d)`: distinct primes `p` with `ind(p) = d` in a pair of `P_t` with a subcontractor in
  `s`.
- `L_t(s,d)`: pairs of `P_t` with a subcontractor in `s` and a prime in `d`.

These are the Stage 14 estimand restricted to one fiscal year. **My call:** firm industries and
pair status stay as the bundle set them for the whole window. So a pair that is intra-group by
any one report is out of every year, as it is out of the headline cells.

### Recurrence and testable cells

A **base cell** of FY t is a cell with `L_t(s,d) ≥ 1`.

A base cell **recurs** when `L_{t+1}(s,d) ≥ 1` (owner, D2). The same pair counts. The outcome
is the same for both measures.

A firm is **active in its role** in FY t+1 when it has that role in some pair of `P_{t+1}`. A
subcontractor must be the subcontractor of some pair, and a prime must be the prime of some
pair. A base cell is **testable** when at least one of its pairs in `P_t` has a subcontractor
and a prime that are both active in their roles in FY t+1. This carries over V9's owner rule
that exits do not count. A firm that stops contracting, or that no prime reports any more,
makes no cell testable. Both measures share this test.

**My call:** the roles are fixed. A subcontractor that appears only as a prime in FY t+1 does
not make the cell testable. The cell is a supplier → buyer relation, and that firm no longer
supplies.

**A minimum of 1 is a valid result.** If cells with a count of 1 already recur at `LEVEL` or
more, every published row of that measure meets the gate. That is a measured outcome, not a
broken rule.

### Year pairs

FY2024 → FY2025 (`2024-2025`) and FY2025 → FY2026 (`2025-2026`). **My call:** both pairs, as
V9 kept the shorter 2025 release. FY2026 is short (see Limits), so the second pair will
probably set the minimum.

### From curves to a minimum

Constants, committed before the first real run:

| Constant | Value | Decided by |
|---|---|---|
| `LEVEL` | 0.90 | the owner for V9, carried over (**My call**) |
| `TOP_BAND` | 10: counts of 10 and more form one band | V9, carried over (**My call**) |
| `MIN_BAND_CELLS` | 50 testable cells | V9, carried over (**My call**) |
| 95% Wilson interval | z = 1.959963984540054, for readers only | V9, carried over |

For each measure separately, and for each year pair:

1. Put each testable cell into a band by its base-year count: `S_t(s,d)` for `supplier_share`
   and `B_t(s,d)` for `buyer_share`. The bands are 1, 2, …, 9 and `10+`.
2. Merge any band below `10+` with fewer than `MIN_BAND_CELLS` testable cells into the next
   higher band. Repeat until every band has at least `MIN_BAND_CELLS` cells or is the top
   band. A merged band starts at its lowest count.
3. A band's rate is its recurring cells divided by its testable cells.
4. The year pair's minimum is the lowest starting count of a band whose rate is at least
   `LEVEL`, where every higher band also reaches `LEVEL`.

Then, for each measure:

5. The measure's minimum is the larger of its two year-pair minimums.
6. **No minimum without the level.** If the top band misses `LEVEL` in either year pair, that
   measure gets no minimum. The stage stops, and the owner decides. No constant changes after a
   run. A top band with no testable cells counts as missing `LEVEL`. **My call:** no fallback
   is agreed in advance, for example a minimum from FY2024 → FY2025 alone. A fallback chosen
   for the case where the short year fails would be a rule chosen to rescue a result. V9 and
   Stage 19 have the same stop.

Rates use the point estimate. The Wilson interval does not enter the rule.

**Two minimums (My call).** `supplier_share` counts subcontractors and `buyer_share` counts
primes. One prime can buy from many supplier industries, so the two counts behave differently.
So each measure gets its own minimum. The roadmap Exit names "the headline minimum count" of
the family, in the singular. The decision gives one value for each of the two targets that the
Exit names, and it reports for each target how many rows meet its value. The plan records this
as a `> Deviation:` note against the Stage 21 Exit wording, so that a reader of the roadmap
sees two values.

### Where the minimum applies

A row of `vendor_links.parquet` meets the gate when its `n_unweighted` is at least its
measure's minimum. `n_unweighted` is `S(s,d)` for `supplier_share` and `B(s,d)` for
`buyer_share`, pooled over FY2024–FY2026. Each measure has one row for each cell. **My call:**
no pass-list file, because the gate is one comparison on a published column.

The two rows of one cell can differ: one can meet its gate while the other misses. Each row is
its own target.

**The intra-group label (My call).** The 71 rows that carry
`numerator:intra_group_sensitivity:true` are gated on their published `n_unweighted`, which
excludes intra-group pairs. The label stays as it is. The 7 cells that exist only under the
intra-group sensitivity are not published rows, so no gate applies to them. The measurement
uses the eligible pairs only, which are the headline set.

**Leniency.** The curves use single-year counts, and the gate uses pooled counts. A pooled
count is never smaller than any single-year count, so the gate is a little lenient. The output
measures this: for each measure, the kept rows whose largest single-year count is below the
minimum.

## What gets built

1. **A measurement script** in `scripts/` (name left to the plan), with tests in `tests/` that
   load it the way `tests/test_measure_ita_minimum_counts.py` loads its script.
   - Arguments: `--data-dir`, `--run` and `--outputs-sha256`. Nothing defaults to the real data
     tree.
   - It checks the detached pin first. Then each file it reads must match its record (SHA-256
     and size) in `outputs.json`, before any content is trusted. A failure prints a fixed
     reason and exits nonzero.
   - **Self-checks, before any curve.** Any difference stops the run.
     - The pair keys `(prime_uei, sub_uei)` are unique. Each eligible pair has both node IDs,
       and its `n_reports` equals `n_fy2024 + n_fy2025 + n_fy2026`.
     - The pooled recount over `P` gives the same set of cells as
       `vendor_link_support.parquet`, and for every cell the same `s_suppliers`, `b_buyers`
       and `l_pairs`.
     - For every cell and fiscal year, `L_t(s,d)` equals `l_fy{t}`.
     - For every cell, the `supplier_share` row's `n_unweighted` equals `s_suppliers`, and the
       `buyer_share` row's `n_unweighted` equals `b_buyers`.
     - For each measure, the distribution of `n_unweighted`, recomputed with the bundle's own
       definition (`vendor_link_targets._distribution`, unchanged), equals its entry in
       `n_unweighted_distribution` of `report.json`.
   - It reads the Parquet files through lazy scans of the columns above.
   - Output: one sorted JSON line on stdout and nothing else. It holds:
     - the rule constants and the input pins.
     - for each measure and year pair: the bands (start, base cells, testable cells, recurring
       cells, rate and Wilson interval) and the year-pair minimum.
     - for each measure: its minimum, the pooled `n_unweighted` distribution as `report.json`
       gives it, and the kept counts. The kept counts are the rows, the support (the sum of
       `n_unweighted`), the kept rows and their share, the kept support and its share, the
       lenient kept rows, and the kept rows among the 71 with the intra-group label.
     - the number of cells whose two rows both meet their gates.

     It holds no UEI, no amount and no cell list.
   - It writes nothing under `data/`. The JSON output never enters git. The decision record
     cites its SHA-256, as Stage 3 did.
2. **Two real runs.** The plan runs the script twice on the pinned input. The two outputs must
   be byte-identical. The decision record gives their SHA-256, the command, and the wall time
   and maximum RSS of one run (`/usr/bin/time -l`).
3. **The decision record** `specs/findings/v9-usaspending-minimum-counts.md` (**My call**,
   beside the other V9 records). It gives the rule and constants with the commit that fixed
   them before the first run, the inputs and pins, the curves for each measure and year pair,
   each measure's minimum, the kept counts, the lenient counts, the design-time disclosure
   above, the Consumes deviation below and the limits below.
4. **Spec amendments** in `specs/embedding-evaluation-data-spec.md`:
   - R7.3: the decision record sets the minimum for the vendor-link family, one value for
     `supplier_share` and one for `buyer_share`. "Every other family" then no longer includes
     it.
   - V9: the same decision covers the vendor-link family after its first full build.
   - Rollout: no change (**My call**). Its sentence already sets "each family's cell-count
     gate" before any embedder is scored on that family, and vendor links are a family. Stage 3
     wrote that general sentence. Stage 19 needed its own sentence because the wage file is not
     a family.

   The Stage 19 plan (`specs/plans/17-acs-wage-minimum-earners.md`, Step 2 of its amendment
   task) edits the same two paragraphs. Re-read the spec on the current `main` before the
   edit, and keep any Stage 19 sentence that has merged.
5. **Stale lines.** Each is changed to name the decision record:
   - `CLAUDE.md:464-465`: "Every target keeps `size_gate_pending`, and no headline minimum
     count (O26) exists yet." Keep `size_gate_pending`, and name the decision record for O26.
   - `specs/deliverable-map.md:14`, the USAspending row. Its Status cell says "Not replayed. No
     count gate yet", and Stage 20 already made "Not replayed" stale. Its "Still blocked by"
     cell names the resume after Stage 14 (replay check, acceptance finding, headline minimum
     count, the D2 rule), which is done. After the change, the row names the replay
     (Stage 20) and the two minimums with their kept counts. It is then blocked only by O18
     and by R8.4, if the family trains.
   - `README.md`, section "USAspending vendor links (roadmap Stage 14)". It has no
     minimum-count sentence. Add one that names the decision record and says that the
     published targets keep `size_gate_pending` (**My call**).

## Constraints

- **Frozen software.** Change no file in `vendor_link_bundle.SOFTWARE_FILES`, the Stage 6
  `FROZEN_MODULES` and `TARGET_MODULES`, the Stage 7 to 9 software, `cli.py` or
  `code_references.py`. Add no dependency and no console entry point. New files go in
  `scripts/` and `tests/` only. The script may import from `embedding_data`. It may load the
  band functions of `scripts/measure_ita_minimum_counts.py` unchanged, or copy them (left to
  the builder).
- **Offline and credential-free.** No network, no `.env`, no HTTP client, no upstream builder
  and no `verify` run inside the script.
- **Freeze window.** Before each real run, each full pytest run and each commit, run
  `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'` and stop if it
  prints anything (`CLAUDE.md`, Stages 10 and 17).
- **No write gate.** The script reads the run in place and writes nothing under `data/`, so no
  owner write gate applies. It is not a build. **My call:** before the real runs, also run
  `pgrep -fl 'embedding_data|embedding-data'` and look at each match. The pattern also matches
  its own shell and any Python process in a project venv, so a match alone is no stop. Do not
  start while a full-data build or another full-data measurement runs (roadmap, "Shared
  resources").
- **Rule before data.** The script, its tests and its constants are committed before the first
  real run. The decision record cites that commit. **My call:** a later code fix that only
  makes the script match this written rule is allowed, and the decision record discloses it.
  Any change to the written rule goes to the owner.
- **Tests.** Red → green on small synthetic bundles in a temporary `--data-dir`, through the
  script's functions and its command line. They cover the per-year counts, the role-fixed
  testable rule (a subcontractor that is only a prime in FY t+1 does not make a cell
  testable), recurrence through the same pair, banding and merging, the monotone rule, the
  no-minimum stop for one measure, two measures with different minimums, the lenient count,
  each self-check failure, the pin and record refusals, determinism, and an output that holds
  none of the fixture UEIs. No test reads the real tree.
- **Aggregates only.** R8.1 to R8.4 hold. The output and the decision record contain counts,
  rates and constants only.

## Limits (for the decision record)

- Recurrence measures whether a relation between two industries persists among firms that
  still contract in their roles. It does not measure truth. A firm with a wrong SAM code that
  keeps the same contract recurs every year.
- Industries come from one SAM.gov extract (`2026-10`). Each firm's code at the extract date
  applies to every year. A code change over time is not seen.
- Testability keeps only cells with a pair whose two firms stay active in their roles. Cells
  of firms that leave federal contracting, or that switch roles, are under-represented in the
  curves.
- FY2026 is short. The snapshot (`2026-11-19`) came seven weeks after FY2026 ended, so late
  reports are missing. FY2026 has 117,644 usable reports, against 227,218 in FY2024. This
  pulls FY2025 → FY2026 recurrence down.
- Subaward reporting moved from FSRS.gov to SAM.gov on 2025-03-08, inside FY2025. A change in
  reporting can move recurrence.
- Pair status is pooled. A pair that is intra-group by one report is out of every year.
- The gate applies to counts pooled over three fiscal years, so it is a little lenient
  (measured).
- The population is federal prime contractors and the subcontractors that they report. It is
  not a frame of firms or of trade.
- The minimum is a reliability floor for headline use. It is not a coefficient-of-variation
  rule, and it says nothing about cells that the bundle does not emit.

## Left to the builder

- The script's name, its internal structure and the JSON key names.
- Whether it loads the Stage 3 band functions or copies them.
- Fixture design, and the exact wording of the amendments and the stale-line changes within the
  meaning above.

## Rollout

The plan executes in a fresh session. The decision record, the spec amendments and the
stale-line changes land in one branch with the script.

Stage 21's Consumes line names `report.json` and the Stage 14 findings. Its cost estimate is
"one pass over the family's `n_unweighted` counts". Under D1 the measurement also reads three
Parquet files of the run, and one of them is the UEI pair table. So the plan records a
`> Deviation:` note against the Stage 21 Consumes line and cost (owner, D1, 2026-11-22). It
records a second `> Deviation:` note against the Exit's singular "the headline minimum count",
because the decision gives one value for each measure (see "Two minimums"). The stamp cites
both notes. The rest of the Exit holds as written. The minimums come from the observed
`n_unweighted` counts, split by fiscal year, and the decision reports for each target how many
rows meet its minimum.

> Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 21 — on plan
> completion, tick the stage and re-validate later stages against what shipped.
