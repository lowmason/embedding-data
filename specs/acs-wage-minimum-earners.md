# Minimum headline earners for the ACS wage microdata

> Next step: writing-plans, in a fresh session, against this file.

Status: DRAFT (2026-11-22), awaiting the owner's approval.

Design spec for Stage 19 of `specs/naics-evaluation-data-roadmap.md` (outcome O23). It sets
the minimum number of headline earners that a category of the ACS wage microdata needs before
a panel uses it as headline evidence. Owner decisions are dated 2026-11-22 and come from the
Stage 19 design session. Items marked **My call** are the designer's proposals that the owner
did not decide separately.

## Design provenance

A brainstorming session with the owner on 2026-11-22, in this repository at `ad4676c`. The
inputs read were:

- the Stage 19 roadmap entry, the Stage 3 design `specs/completed/ita-naics-minimum-counts.md`
  and its decision `specs/findings/v9-ita-naics-minimum-counts.md`;
- the Stage 17 design `specs/completed/acs-wage-microdata.md` and its finding
  `specs/naics-evaluation-data-stage-17-findings.md`;
- R7.3, V9 and the Rollout sentence of `specs/embedding-evaluation-data-spec.md`;
- from the run `stage17_acs_wage_microdata_20261119_r1`: the SHA-256 of `outputs.json` and of
  `report.json`, the key names of `report.json`, the key names of one `categories` entry, the
  number of headline categories for each year (233) and the Parquet schema (footer only). No
  per-category count, no wage value and no other file of the run was read.

## Owner decisions (2026-11-22)

| # | Decision | Owner's words |
|---|---|---|
| D1 | The measurement may read wage values and weights from `acs_wage_persons.parquet`, in place, and it outputs aggregates only. | "Yes, read wages" |
| D2 | The rule is approach A: the replicate-weight standard error (SE) of each category's mean log wage in each year. | "A: replicate SE" |
| D3 | The SE target is 0.05 log points. | "0.05 log points" |

## Intent

naics-embedder's wage panel will score ACS industry categories. A category with few headline
earners has a noisy wage level. A panel that scores it measures sampling noise as well as the
embedding. Before naics-embedder scores the panel, each category needs a minimum count for
headline use. R7.3 says that a minimum comes "by measurement, not argument".

ACS is a probability sample, and the file carries `PERWT` and the 80 replicate weights
`REPWTP1` to `REPWTP80`. So the sampling error of a category's wage level can be measured with
the official ACS method. The rule is: **a category is headline evidence in a year when
categories of its size measure their mean log wage to within the SE target.** The minimum is
the smallest headline count at which that holds, by the band rule below.

**Why not the Stage 3 rule.** Stage 3 asked whether a cell recurs in the next year. All 233
headline categories have headline rows in both 2023 and 2024. So every category recurs, and
that rule always gives a minimum of 1. It carries no information here. Stage 3 also rejected a
precision rule (its approach C) only because ITA is a filing universe, not a sample. That
reason does not apply to ACS.

## Goals

1. Measure, for each year, the replicate-weight SE of each headline category's weighted mean
   `log_wage_2010`.
2. Set one minimum number of headline earners from those SEs by the rule below.
3. Report, for each year, how many categories meet the minimum, and their share of categories
   and of headline rows.
4. Record the decision in a decision record and amend the spec's R7.3, V9 and Rollout sentence
   so that they cover the wage file's minimum.

## Non-goals

- The protocol section for the file (O24) and the wage panel itself (naics-embedder's panel
  spec). What a panel does with a category below the minimum belongs to O24.
- A minimum for each node. The minimum applies to each category (roadmap Exit).
- Minimums for any target family, including the ACS worker-profile family.
- An SE for any quantity other than the category's mean log wage, such as a regression
  coefficient net of covariates.
- Rebuilding or editing the Stage 17 runs, or relabeling their `report.json`.

## Anti-goals

- **A rule picked after seeing its result.** The rule and every constant are committed before
  the first run on real data. No constant changes after that run. A failed rule goes to the
  owner, never to a retuned constant.
  *Disclosure (2026-11-22):* before the owner fixed the SE target, the session had seen these
  figures and no others about category size or wages:
  - The Stage 17 design's pooled pre-build figures (`specs/completed/acs-wage-microdata.md`,
    "The headline funnel"). The smallest category has 89 headline earners over both years, and
    the median category has 2,045.
  - The built totals in the Stage 17 finding: 1,278,878 headline rows (2023: 639,002;
    2024: 639,876) over 233 categories in each year.
  - A table from the designer that gave the earners each target would need: about 700 for
    0.03, 250 for 0.05 and 60 for 0.10. It was argument, not measurement. It assumed a
    within-category spread of 0.6 log points and a design effect of 1.7, and it used no data
    from the run.
  No per-category count, no SE and no wage value had been read.
- **Category means in the open.** The output and the decision record hold counts, SEs and pass
  flags only, never a category's mean wage. A published mean wage for each category would be
  an evaluation target that an embedder could fit (R8.4). **My call.**
- **Person values leave the machine.** Only aggregates leave the script (R8.1).
- **Embedder results as input.** No embedder output, score or ranking is read (R8.4).
- **A broken Stage 17.** Change no file in `acs_wage_inputs.SOFTWARE_FILES`
  (`src/embedding_data/acs_wage_inputs.py:61-81`, 19 files, including `pyproject.toml` and
  `uv.lock`). A change makes `verify` refuse both Stage 17 runs.

## Inputs (pinned, read in place, never rebuilt)

| Input | Identity |
|---|---|
| Stage 17 run `stage17_acs_wage_microdata_20261119_r1` (`data/derived/acs/wage-microdata/`) | detached `outputs.json` SHA-256 `6cb253e2e5c2e48a5b31d2790a0378636d3b6ef9197cfb2d33cca2813ac201d1` |
| Its `report.json` | must match its record in `outputs.json` (SHA-256 `32ad9b698c9b940760d74eec0ae3b234abd14ba4c08ca07f04770a8f11e413bd`) |
| Its `acs_wage_persons.parquet` | must match its record in `outputs.json` (SHA-256 `a94471492dc91aebe3a3436e8d738d399520791b0eace6f01a719fad10fd5ff2`) |

The script reads no other file of the run and does not run `verify`. The replay run is
byte-identical in both files (Stage 17 finding), so it adds nothing. **My call:** the script
reads the first run only.

Columns read from the Parquet: `YEAR` (Int64), `INDNAICS` (String), `flag_headline`
(Boolean), `log_wage_2010` (Float64), `PERWT` (Float64) and `REPWTP1` to `REPWTP80` (Int64).
Weights use their literal values (factor 1), as in Stage 7.

## Approaches considered

**What the measurement may read** (owner picked wage values, D1). A rule from `report.json`
counts alone would have to assume how spread out wages are. That is argument, which R7.3
forbids. The cost is one read of 84 columns of a 377 MB Parquet, more than the roadmap's
estimate of "one pass over the counts".

**How to turn wages into a minimum** (owner picked A, D2):

| Approach | What a category must show | Trade-off |
|---|---|---|
| **A. Replicate-weight SE** | The SE of its weighted mean `log_wage_2010` in one year is at or below a fixed target | Measures sampling noise directly, with the ACS method. Works for each year on its own. The target is a chosen number, in wage units |
| B. Year-to-year replication | Its 2023 and 2024 means agree within a tolerance, after the overall shift is removed | Closest to Stage 3, and it matches the seen regime. But real wage change inside an industry counts as noise |
| C. Split-half within a year | Two random halves give means that agree within a tolerance | Simple. It ignores the survey design, so it understates the noise that A measures |

**The SE target** (owner picked 0.05, D3). The alternatives were 0.03 and 0.10. At 0.05, a
category's 95% interval is about ±10% of its geometric mean wage.

## The rule

### SE of one category in one year

For a category `c` (one delivered `INDNAICS` string) and a year `y`, take the headline rows
(`flag_headline` true) with that `INDNAICS` and `YEAR`. Let `x_i` be `log_wage_2010`.

- Full-sample estimate: `θ = Σ PERWT_i · x_i / Σ PERWT_i`.
- Replicate estimates, for `r` = 1 to 80: `θ_r = Σ REPWTPr_i · x_i / Σ REPWTPr_i`.
- `SE = sqrt( 4/80 · Σ_r (θ_r − θ)² )`, the ACS successive-difference formula.

A category meets the target in year `y` when `SE ≤ SE_TARGET`.

**Undefined SE (My call).** The SE is undefined, and the category misses the target, when
any of these holds:

- it has fewer than 2 headline rows in the year. With one row, every `θ_r` equals `θ`, so the
  formula gives an SE of exactly 0 by construction;
- all its `log_wage_2010` values in the year are equal, which also gives an SE of 0 by
  construction;
- any replicate denominator `Σ REPWTPr_i` is zero or negative.

The output counts the undefined SEs for each year and each reason. These guards remove only the
cases that are degenerate by arithmetic. They add no row floor: a floor such as 30 rows would
be argument, not measurement (R7.3). Small categories with defined SEs keep them, and their
noise is a stated limit.

### From SEs to a minimum

Constants, committed before the first real run:

| Constant | Value | Decided by |
|---|---|---|
| `SE_TARGET` | 0.05 log points | owner (D3) |
| `LEVEL` | 0.90: the share of a band's categories that must meet `SE_TARGET` | **My call**, Stage 3's level |
| `BAND_STARTS` | 1, 50, 100, 200, 400, 800, 1600. A band runs from its start up to the next start, and the last band is `1600+` | **My call** |
| `MIN_BAND_CATEGORIES` | 10 | **My call** |
| `REPLICATE_FACTOR` | 4/80 | ACS method |

The owner's approval of this spec approves every constant and rule in it, the designer's calls
included. So the plan needs no owner stop between the rule commit and the first real run.

For each year separately:

1. Put each headline category into the band that holds its `headline_rows` for that year.
2. Merge any band below the top band with fewer than `MIN_BAND_CATEGORIES` categories into the
   next higher band. Repeat until every band has at least `MIN_BAND_CATEGORIES` categories or
   is the top band. A merged band starts at its lowest start.
3. A band passes when at least `LEVEL` of its categories meet `SE_TARGET`.
4. The year's minimum is the lowest start of a passing band whose higher bands all pass.

Then:

5. The minimum is the larger of the two years' minimums.
6. **No minimum without the level.** If the top band fails in either year, Stage 19 sets no
   minimum. The stage stops, and the owner decides. No constant changes after a run. A top band
   with no categories counts as failing.

**A minimum of 1 is a valid result.** If every band passes, every headline category meets the
gate. That is a measured outcome, not a broken rule.

**My call:** band starts double so that each band covers the same ratio of counts. The SE
shrinks with about 1/√n, so equal ratios give bands of similar change in SE. The minimum can
therefore take only a band start as its value. The decision record states this coarseness.

### Where the minimum applies

A category meets the gate in year `y` when its `headline_rows` for `y` in `report.json`
(`categories` entries, keyed by `INDNAICS` and `YEAR`) is at least the minimum. The 31
categories that share a node have no headline rows, so they never meet it. Consumers compare
one published column. **My call:** no pass-list file.

The count gate and a category's own SE can disagree. The output reports both tallies for each
year: categories that meet the count but miss `SE_TARGET`, and categories that miss the count
but meet `SE_TARGET`.

## What gets built

1. **A measurement script** in `scripts/` (name left to the plan), with tests in `tests/` that
   load it the way `tests/test_reconcile_stage17.py` loads its script.
   - Arguments: `--data-dir`, `--run` and `--outputs-sha256`. Nothing defaults to the real
     data tree.
   - It checks the detached pin first. Then `report.json` and `acs_wage_persons.parquet` must
     match their records (SHA-256 and size) in `outputs.json`, before any content is trusted.
     A failure prints a fixed reason and exits nonzero.
   - It reads the Parquet through a lazy scan of the columns above, filtered to headline rows.
   - **Self-checks, before any SE.** For every `categories` entry of `report.json`, the
     recount of headline rows for that `INDNAICS` and `YEAR` must equal `headline_rows`. The
     number of categories with headline rows must equal `headline_categories` for each year.
     Every headline row must have a finite `log_wage_2010` and a positive `PERWT`. Any
     difference stops the run.
   - Keys keep the delivered `INDNAICS` strings, including their space padding.
   - The sums are exact or taken in a fixed row order, so two runs give byte-identical output.
   - Output: one sorted JSON line on stdout and nothing else. It holds the rule constants, the
     input pins and, for each year, the bands (start, categories, categories meeting
     `SE_TARGET`, share, pass), the year's minimum, the count of undefined SEs, and the kept
     categories with their share of categories and of headline rows. It also holds the
     minimum and, for each category and year, `INDNAICS`, `YEAR`, `headline_rows`, `SE` and
     whether it meets `SE_TARGET`. It holds no mean wage and no person value.
   - It writes nothing under `data/`. Its JSON output never enters git. The decision record cites
     only the output's SHA-256, as Stage 3 did. **My call:** a category's SE times the square
     root of its count gives about its wage spread, which is close to the worker-profile
     family's wage signal. So the per-category SEs stay on this machine.
2. **Two real runs.** The plan runs the script twice on the pinned input. The two outputs must
   be byte-identical. The decision record gives their SHA-256, the command, and the wall time
   and maximum RSS of one run (`/usr/bin/time -l`).
3. **The decision record** `specs/findings/v9-acs-wage-minimum-earners.md` (**My call**,
   beside the Stage 3 record). It gives the rule and constants with the commit that fixed them
   before the first run, the inputs and pins, the bands for each year, the minimum, the kept
   counts for each year, both disagreement tallies, the categories that miss the gate in each
   year, the design-time disclosure above and the limits below. It gives no SE for a single
   category.
4. **Spec amendments** in `specs/embedding-evaluation-data-spec.md`:
   - R7.3: the ACS wage microdata are not a target family. Their minimum number of headline
     earners for each category is set by the decision record.
   - V9: the same decision covers the wage file, after its first full build.
   - Rollout: V9 sets the wage file's minimum before any embedder is scored on that file.
5. **Stale lines.** These say that O23 does not exist yet. Each is changed to name the
   decision record: `CLAUDE.md:420-421`, `README.md:705-706` and `specs/deliverable-map.md:11`
   (its status and next-step cells).

## Constraints

- **Frozen software.** Change no file in `acs_wage_inputs.SOFTWARE_FILES`, the Stage 6
  `FROZEN_MODULES` and `TARGET_MODULES`, the Stage 7 to 9 software, `cli.py` or
  `code_references.py`. Add no dependency and no console entry point. New files go in
  `scripts/` and `tests/` only.
- **Offline and credential-free.** No network, no `.env`, no HTTP client, no upstream builder
  and no `verify` run inside the script.
- **Freeze window.** Before each real run, each full pytest run and each commit, run
  `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'` and stop if it
  prints anything (`CLAUDE.md`, Stage 17).
- **No write gate.** The script writes nothing under `data/`, so no owner write gate applies.
  A design that needs a rebuild of Stage 17 needs a fresh run ID and new owner gates.
- **Rule before data.** The script, its tests and its constants are committed before the first
  real run. The decision record cites that commit. **My call:** a later code fix that only
  makes the script match this written rule is allowed, and the decision record discloses it.
  Any change to the written rule goes to the owner.
- **Tests.** Red → green on small synthetic bundles in a temporary `--data-dir`: the SE formula
  against a hand-computed case, each of the three undefined-SE cases, banding and merging, the monotone rule, the
  no-minimum stop, the self-check failures, the pin refusals and the absence of means in the
  output. No test reads the real tree.
- **Aggregates only.** R8.1 to R8.4 hold. The output and the decision record contain counts,
  SEs, flags and category codes only.

## Limits (for the decision record)

- The SE measures sampling noise in a category's weighted mean log wage. It does not measure
  coding error, allocation or how well a panel's model fits.
- The SE is for the mean without covariates. A panel that conditions on covariates estimates a
  different quantity, with a different SE.
- Replicate SEs are themselves noisy in small categories. A category with only a few rows can
  meet the target by chance. The guards catch only the cases that are degenerate by arithmetic.
- Top-coded wages stay in the headline (Stage 17 design). They narrow the spread at the top, so
  SEs in high-wage categories can be a little low.
- The minimum can take only a band start as its value.
- The 31 categories that share a node have no headline rows and are not measured.
- The minimum is a reliability floor for headline use. It says nothing about the approximate
  coordinates of mixture categories.

## Left to the builder

- The script's name, its internal structure and the JSON key names.
- How it sums exactly or in a fixed order.
- Fixture design, and the exact wording of the amendments and the stale-line changes within
  the meaning above.

## Rollout

The plan executes in a fresh session. The decision record, the spec amendments and the
stale-line changes land in one branch with the script.

Stage 19's Consumes line names only `report.json` and the Stage 17 finding, and its cost
estimate is "one pass over Stage 17's counts". Under D1 the measurement also reads
`acs_wage_persons.parquet`, which costs more. So the plan records a `> Deviation:` note
against the Stage 19 Consumes line and cost (owner, D1, 2026-11-22), and the stamp cites that
note. The Exit still holds as written, because the minimum and its bands are counted in
`headline_rows`.

> Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 19 — on plan
> completion, tick the stage and re-validate later stages against what shipped.
