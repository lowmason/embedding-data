# Headline minimum counts for the ITA NAICS targets

Design spec for Stage 3 of `specs/naics-evaluation-data-roadmap.md`. It discharges spec
R7.3 and V9 (`specs/embedding-evaluation-data-spec.md`) for three families only: ITA
co-ownership, the 2023 ITA area mix and ITA text–code pairs. Owner decisions are dated
2026-11-16/17 and come from the Stage 3 design session. Items marked **My call** are the
designer's proposals that the owner did not decide separately.

## Intent

Every NAICS target has an unweighted count, and most counts are tiny. The median cell
count is 1 for co-ownership and for the area mix. Before naics-embedder scores an embedder
on these families (its gates G3 and G5), each family needs a minimum count for headline
use. R7.3 says the minimum comes "by measurement, not argument". Every ITA target has SE
`none`, so no sampling theory gives the number.

The owner chose a measured rule: **a cell is headline evidence when cells of its count
recur in the next year.** A relation that recurs is not a one-year coding accident. The
minimum count is the smallest count at which recurrence reaches a level fixed before the
deciding curves are measured.

## Goals

1. Measure, for each family, how often a cell recurs in the next year as a function of
   its count in the base year.
2. Set one minimum count per family from those curves by the rule below.
3. Report, for each family, how many published cells (or headline pairs) meet the minimum,
   and their share of cells and of support.
4. Record the decision in `specs/findings/v9-ita-naics-minimum-counts.md` and amend the
   spec's R7.3, V9 and Rollout sentence to allow a gate per family.

## Non-goals

- Minimum counts for SOC, geography, ACS, CPS or Track B families. Those stay with the
  deferred item for old Stage 13 and with each new family's stages (O13 for TRI).
- Cross-year links get no minimum. They are a support table, not an R7.2 family.
- Scoring, null models, splits or any treatment of absent (zero) cells. Scoring belongs to
  naics-embedder and to the successor evaluation-protocol spec.
- Rebuilding or relabeling any bundle. `size_gate_pending` stays in the published Stage 1
  and Stage 6 bundles.
- Methodology K9's other open questions (CV rules, shrinkage, precision weights).

## Anti-goals

- **A rule picked after seeing its result.** The level, the bands and every other rule
  constant are committed before the first run on real data. No constant changes after
  that run. A failed rule goes to the owner (below), never to a retuned constant.
  *Disclosure (owner, 2026-11-17):* during design, the owner saw plain recurrence curves
  for co-ownership before fixing `LEVEL`. They came from the published per-year counts in
  `co_ownership_support.parquet`, with no testability filter. For 2023 → 2024, recurrence
  at counts 1, 2, 3, 4, 5, 6 and 10+ was 29%, 53%, 68%, 80%, 84%, 93% and 99%. For
  2024 → 2025, it was 68%, 93%, 98%, 100%, 99%, 100% and 100%. The designer also saw
  counts 7–9, the cell count of each band and the number of years each pooled cell
  appears in before proposing `TOP_BAND` and `MIN_BAND_CELLS`. No testable curve, no
  area-mix or text-pair curve and no minimum had been measured.
- **Embedder results as input.** No embedder output, score or ranking is read. Choosing a
  minimum against scores is selection on evaluation data (R8.4).
- **A broken Stage 4.** Stage 4 must `verify` the Stage 1 run from its own checkout and
  venv. Any change to a file that the Stage 1 bundle records as software breaks that.

## Inputs (pinned, read in place, never rebuilt)

| Input | Identity |
| --- | --- |
| Stage 1 bundle `stage10_ita_establishment_20261116_r1` (`data/derived/osha/establishment-targets/`) | detached `outputs.json` SHA-256 `e19b0d58f61f106c3994aa6fe51f4fb71244188145dd90f8cccaa8dc8a8b09df` |
| Stage 6 bundle `stage6_ita_area_mix_20261014_1000_csv` (`data/derived/targets/`), including `ita_county_assignments.parquet` | detached `outputs.json` SHA-256 `084292b6835eb09ce27ecc4a3aef03a6f43bfe7b39b815665c29190a431e2473` |
| Codes run `stage4_v11_20261013_r2`, its `ita_300a_canonical` table, as the Stage 1 build read it | detached pin `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |
| Any other file the measurement reads | must match its record in one of the inventories above, or in the Stage 1 `inputs.json` |

## Approaches considered

**How to turn counts into a minimum** (owner picked A):

| Approach | What it measures | Trade-off |
| --- | --- | --- |
| A. Cross-year recurrence | Whether cells of count k appear again next year | Needs a measurement script. Area mix is a 2023-only target, but Stage 6 assigned counties to every year's records |
| B. Support coverage | The k at which kept cells hold a fixed share of support | Cheap, decision record only. The share is itself picked, so it is close to "argument" |
| C. Relative error | Poisson CV ≈ 1/√n | Simple. Treats ITA as a sample, which the universe statement denies |

**What counts as recurrence** (owner picked any employer): recurrence through any
employer or establishment, including the same one filing again. It measures persistence.
"A different employer only" measures replication, but it has no meaning for text pairs,
and the count already measures breadth across employers.

**The level** (owner picked 90%): 80% and 95% were the alternatives. At 90%, about one
cell in ten at the minimum may be a one-year accident.

**The text-pair count** (owner picked `n_headline_records`, 2026-11-17): the roadmap's
Stage 3 Exit names `n_records`. `n_records` pools all ten years, including 2016–2022
records whose codes were crosswalked and carry no headline label. 47% of headline pairs
have such records, and the median `n_records` is 3 against a median
`n_headline_records` of 1. The recurrence test measures headline records, so the gate
counts the same thing. This is a recorded deviation from the Exit wording.

**What makes a cell testable** (owner picked code changes only, 2026-11-17): the builder
check found that the first draft treated exits unevenly. It counted an establishment that
stops filing inside a still-filing employer as a failure for co-ownership and text pairs,
but not for the area mix. The alternative, "exits count" for all three families, gives
higher minimums but mixes population churn with coding accidents.

## The rule

### Base counts and recurrence, per family

| Family | Cell | Base count in year t | Recurs in year t+1 when |
| --- | --- | --- | --- |
| Co-ownership | ordered industry pair `(a, b)` | `j_t`: EINs with eligible records in both `a` and `b` in year t | `j_{t+1} ≥ 1` |
| Area mix | county × industry | eligible records in year t (Stage 6 rule: county assigned, `eligible_industry()`) | the cell has at least one eligible record in t+1 |
| Text pairs | headline pair (employer × description) | the pair's eligible records in year t | the pair has an eligible record in t+1 whose NAICS 2022 node is one of the pair's year-t headline nodes |

Text-pair recurrence requires a matching node because a text pair is a label. The owner
decided "any employer". For text pairs this means the pair's own employer, because a pair
belongs to one employer. **My call:** a match against any year-t node, so a pair that
already conflicts in year t can still recur.

Co-ownership direction: `j_t` is symmetric, so both directed cells of one industry pair
have the same base count and the same outcome. **My call:** count directed cells, as the
published table does, so the curves and the kept counts use the same unit.

### Testable cells

A cell enters the test only when year t+1 could show it. Records filed in older NAICS
editions are ineligible, and in 2024 and 2025 about 40% of records are. A cell that
vanishes for that reason says nothing about the relation.

**Owner decision (2026-11-17): code changes only.** The test asks whether an
establishment that refiled visibly kept its code. An establishment that stops filing, or
that refiles with an ineligible code, makes no cell testable. Closures, sales and drops
below the filing size are changes in the filing population, not coding accidents.

All three families use one mechanism, a **visible link**. A year-t record has a visible
link when all of these hold:

1. Its `source_row` is in the `base_rows` of a row of Stage 1's
   `ita_establishment_links.parquet` for the year pair t → t+1.
2. That row's `status` is `confirmed_same_id` or `confirmed_changed_id`. These are the
   adopted R2.7 confirmations. No new linkage rule is written.
3. The row's `later_row` is a t+1 record that is eligible for the family (table below).

| Family | An eligible t+1 record | A cell is testable when |
| --- | --- | --- |
| Co-ownership | is eligible under plan 11's co-ownership classification | at least one of its year-t EINs has a year-t record in `a` and a year-t record in `b` that both have visible links |
| Area mix | has an assigned county and passes `eligible_industry()` | at least one of its year-t records has a visible link |
| Text pairs | passes `eligible_industry()` and belongs to the same pair | at least one of the pair's eligible year-t records has a visible link |

**Owner decision (plan 12 review, 2026-11-17): same pair.** A text pair's linked
successor must belong to the same pair, so the establishment kept its description. A
successor with a reworded description makes no pair testable. Description churn is not
a coding accident. *(owner, plan 12, 2026-11-17)*

Recurrence still counts any employer or establishment. A testable cell recurs when the
condition in the previous table holds, through the linked record or through any other.

**A minimum of 1 is a valid result.** ITA filers often carry their codes forward. If cells
with a count of 1 already recur at `LEVEL` or more, every published cell meets the gate.
That is a measured outcome, not a broken rule, and it is no reason to change the rule.

Coverage, from the Stage 1 report (link rows, not an outcome): confirmed statuses cover
175,103 of 394,234 rows for 2023 → 2024 (44.4%) and 198,889 of 398,620 rows for
2024 → 2025 (49.9%).

### Year pairs

| Family | Year pairs |
| --- | --- |
| Co-ownership | 2023 → 2024, 2024 → 2025 |
| Area mix | 2023 → 2024, 2024 → 2025 |
| Text pairs | 2023 → 2024, 2024 → 2025 |

**My call:** the area mix also uses 2024 → 2025. The Stage 6 assignment table covers
every year, so the second pair costs nothing extra and gives the same protection as for
the other families. The 2024 area-mix counts are measurements, not targets.

### From curves to a minimum

Constants, committed before the first real run:

| Constant | Value | Decided by |
| --- | --- | --- |
| `LEVEL` | 0.90 | owner |
| `TOP_BAND` | 10: counts of 10 and more form one band | **My call** |
| `MIN_BAND_CELLS` | 50 testable cells | **My call** |

1. For each family and year pair, group testable cells into bands by base count:
   1, 2, …, 9 and `10+`.
2. Merge any band below `10+` with fewer than `MIN_BAND_CELLS` testable cells into the
   next higher band. Repeat until every band has at least `MIN_BAND_CELLS` cells or is the
   top band. A merged band starts at its lowest count.
3. The year pair's minimum is the lowest starting count k of a band whose recurrence rate
   is at least `LEVEL`, where every higher band also reaches `LEVEL`.
4. The family's minimum is the largest minimum over its year pairs.
5. **No minimum without the level.** If the top band misses `LEVEL` in any year pair,
   the family gets no minimum. The stage stops, and the owner decides. The level is
   never lowered after a run. **My call:** a top band with no testable cells counts as
   missing `LEVEL`.

Recurrence rates use the point estimate. **My call:** the report also gives each band's
95% Wilson interval for readers, but the interval does not enter the rule.

### Where the minimum applies

| Family | Published count the minimum applies to |
| --- | --- |
| Co-ownership | `n_unweighted` (`J`, pooled 2023–2025) in `ita_co_ownership.parquet` |
| Area mix | `n_unweighted` (2023 records) in `ita_area_mix.parquet` |
| Text pairs | `n_headline_records` of pairs with `flag_headline` in `ita_text_pairs.parquet` |

A cell meets the gate when its published count is at least its family's minimum.
Consumers filter on that column. **My call:** no pass-list file, because the gate is one
comparison on a published column.

The curves use single-year counts. Co-ownership `J` and text-pair `n_headline_records`
pool three years, so they are never smaller than any single-year count. The gate is
therefore a little lenient for those two families. The report measures this: the number
of kept cells whose largest single-year count is below the minimum.

## What gets built

1. **A measurement script** in `scripts/` (name left to the plan), with tests in
   `tests/` that load it the way `tests/test_reconcile_stage10.py` loads its script.
   - Arguments: `--data-dir` and each input's run ID and detached pin. Nothing defaults to
     the real data tree.
   - It checks every detached pin first, then the record of each file it reads, before
     it trusts any content. A failure prints a fixed reason and exits nonzero.
   - **Self-checks, before any curve.** Its recount must equal the published counts
     exactly: co-ownership `j_2023`, `j_2024` and `j_2025` for every cell in
     `co_ownership_support.parquet`, area-mix 2023 `n_unweighted` for every cell, and the
     same set of cells, and text-pair `n_headline_records` as the sum of its per-year
     counts for every headline pair. Any difference stops the run.
   - It reuses the frozen software unchanged: `ita_area_mix.eligible_industry()`, the key
     functions the Stage 1 build used (`ita_establishment_records.keyed_records` and the
     `ita_verification` keys it applies) and Stage 1's link table. `ita_area_mix.estimate`
     refuses years other than 2023. So the script counts area-mix cells with the same
     filters it applies: year, county assigned and `eligible_industry()`.
   - Before it joins Stage 6 assignments to keyed records or links on `source_row`, it
     checks that `year_filing_for` and `naics_code` agree on every joined row.
   - Output: one sorted JSON line on stdout and nothing else. It holds the rule constants,
     input pins, per family and year pair the bands with base cells, testable cells,
     recurring cells, rate and Wilson interval, the per-pair and family minimums, and per
     family the kept cells, their share of cells and of support, and the lenient-kept
     count. **My call:** "share of support" is the kept cells' share of the summed
     published count that the gate applies to. No EIN, employer key, description or
     company string appears in it.
   - It writes nothing under `data/`.
2. **Two real runs.** The plan runs the script twice on the pinned inputs. The two outputs
   must be byte-identical. The decision record gives their SHA-256, the command and the
   wall time and maximum RSS of one run (`/usr/bin/time -l`).
3. **The decision record** `specs/findings/v9-ita-naics-minimum-counts.md`. It gives the
   rule and constants with the commit that fixed them before the first run, the inputs and
   pins, the curves, each family's minimum, the kept counts, the lenient-kept counts, the
   recorded deviation from the Exit wording (`n_headline_records`), the design-time
   disclosure under Anti-goals and the limits below.
4. **Spec amendments** in `specs/embedding-evaluation-data-spec.md`:
   - R7.3 (lines 528–530): the minimum is set per family. It is set for ITA co-ownership,
     the 2023 ITA area mix and ITA text–code pairs by the decision record. It stays open
     for the other families.
   - V9 (lines 609–611): after each family's first full build, report its count
     distribution and set its headline minimum in a recorded decision. Until a family's
     decision exists, none of its targets is described as passing or failing a size gate.
   - Rollout (line 672): V9 sets each family's gate after that family's first full build
     and before any embedder is scored on that family.
5. **One `CLAUDE.md` sentence** (**My call**). It says that the published bundles keep
   `size_gate_pending` and that the three ITA NAICS minimums live in the decision record.

## Constraints

- **Frozen software.** Change none of the 35 files in
  `ita_establishment_bundle.SOFTWARE_FILES`. These include `pyproject.toml` and `uv.lock`. Do not change the Stage 6
  `FROZEN_MODULES`/`TARGET_MODULES`, the Stage 7–9 software, `cli.py` or
  `code_references.py`. Add no dependency and no console entry point. New files go in
  `scripts/` and `tests/` only.
- **Offline and credential-free.** No network, no `.env`, no HTTP client, no upstream
  builder, no `verify` rerun inside the script.
- **Freeze window.** Before every real-data run, every full pytest run and every commit,
  run `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'` and
  stop if it prints anything (`CLAUDE.md`, Stage 10).
- **Rule before data.** The script, its tests and its rule constants are committed before
  the first real run. The decision record cites that commit. **My call:** a later code fix
  that only makes the script match this written rule is allowed, and the decision record
  discloses it. Any change to the written rule goes to the owner.
- **Tests.** Red → green on small synthetic fixtures through the script's functions and its
  command line: banding and merging, the monotone rule, the no-minimum stop, each
  family's testability, the text-pair node match, the self-check failures and the pin
  refusals. Tests pass `--data-dir` to a temporary directory and never read the real tree.
- **Aggregates only.** R8.1–R8.4 hold. The output and the decision record contain counts
  and rates only.

## Limits (for the decision record)

- Recurrence measures code persistence among establishments that refiled visibly. It
  measures neither truth nor establishment exits. An establishment that files the same
  wrong code every year recurs.
- Testability keeps only cells with a visible link. Establishments that relocate or file
  in older NAICS editions are under-represented in the curves.
- A text pair is testable only when a linked successor kept its description. Pairs whose
  establishments reword their descriptions are under-represented in the text-pair curves.
  *(owner, plan 12, 2026-11-17)*
- Co-ownership and text-pair gates apply to three-year pooled counts, which makes them a
  little lenient (measured, above).
- ITA is a program-selected filing population. Filing-rule changes between years can move
  recurrence.
- The 2025 release runs through 08-31-2026. The 2023 and 2024 releases run through 12-31
  of the following year. The shorter window can leave out late 2025 filers.
- Confirmed links need a usable, unreconstructed EIN and a complete address. Records
  without them never have a visible link. So area-mix records with an unusable EIN and
  every text pair with a company-name fallback employer are never testable.
- The minimum is a reliability floor for headline use. It is not a coefficient-of-variation
  rule, and it says nothing about cells that the bundles do not emit.

## Left to the builder

- The script's name, its internal structure and the JSON key names.
- How it loads keyed records (the same functions as the Stage 1 build, proven equal by the
  self-checks).
- Fixture design and the exact wording of the spec amendments within the meaning above.

## Rollout

The plan executes in a fresh session. The decision record, the spec amendments and the
`CLAUDE.md` sentence land in one branch with the script. The `n_headline_records` change
departs from Stage 3's own Exit, which names `n_records`. So the plan records it as a
`> Deviation:` note against the Stage 3 Exit, and the Stage 3 stamp cites that note.

> Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 3 — on plan
> completion, tick the stage and re-validate later stages against what shipped.
