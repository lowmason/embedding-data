# ACS wage microdata for naics-embedder's economic panel

**Status: COMPLETE (2026-11-19)** — implemented by [plan 14](../plans/completed/14-acs-wage-microdata.md); measured runs in the [Stage 17 finding](../naics-evaluation-data-stage-17-findings.md).

> Next step: derive-roadmap adds this work to
> `specs/naics-evaluation-data-roadmap.md` as a new track (see Roadmap
> placement). That stage then goes to writing-plans against this file. Do not
> plan this file before the roadmap has its stage.

Status: APPROVED (2026-11-18, owner: "Approve"). Written 2026-11-18.

## Design provenance

A brainstorming session with the owner on 2026-11-18, in this repository. The
inputs read were:

- this repository at `fc6adfa`: `specs/deliverable-map.md`, the source spec
  (R7.2, R7.4, R8.1, R8.4), `specs/naics-evaluation-data-roadmap.md`,
  `specs/evaluation-protocol.md`, the Stage 8 finding and
  `src/embedding_data/acs_benchmark_extract.py`;
- the Stage 8 core table `acs_core_canonical.parquet` of run
  `stage8_acs_mapping_20261018_r7`, through read-only queries on 2026-11-18;
- the Stage 4 table `ita_300a_canonical.parquet` of run `stage4_v11_20261013_r2`,
  through one read-only query;
- in naics-embedder at `8329e55`: `specs/naics-artifact-redesign.md` (Reqs 25,
  26 and 29, and proposal P2), `specs/naics-representation-split.md` (Reqs 20
  to 24), `specs/completed/economic-candidates.md` (§4.2) and
  `src/naics_embedder/panels/regressor.py` (`DECISION_LEVEL = 6`);
- the IPUMS USA pages for `INCWAGE` and for the sample IDs, read on 2026-11-18.

## Owner decisions (2026-11-18)

| # | Decision | Owner's words |
|---|---|---|
| D1 | Build an input for a person-level wage panel from the ACS microdata. Wages are the outcome. Industry and person covariates are the predictors. | "Wages as dependent variable and a 6-digit NAICS code plus additional covariates such as sex, age, occupation (maybe sector-level dummies?) and whatever else would be a nice addition." |
| D2 | Each ACS industry category takes the coordinates of its own NAICS node. No person gets a node that covers fewer industries than the code ACS delivered. | "If ACS is mostly 4-digit, why can't we just use those embeddings?" |
| D3 | Person rows, not aggregate cells. | "Aggregate cells are not microdata." |
| D4 | This repository builds the file in a new stage. naics-embedder does not read the Stage 8 table directly. | "New stage here" |
| D5 | The owner's view: the file does not change how naics-embedder designs its embeddings. A heads-up went to naics-embedder's Stage 3 session on 2026-11-18. | "I dont think it affects the design of the embeddinings, because it does not have all codes." |
| D6 | A category's own node is the deepest node that holds exactly its industries (Stage 8's common node), not the node of the delivered code. Example: the delivered code `6231` joins at `623110`, its only six-digit descendant. The file also carries the delivered node. | "Deepest node" |

**Proposals the owner did not correct.** Each was put to the owner as a
proposal in the session. The owner went on without correcting it.

| # | Proposal |
|---|---|
| P1 | Leave out the 31 categories whose node is also the node of another category. Keep the other 55 mixtures in the headline, with a flag that says that their coordinates are approximate. |
| P2 | Keep sector dummies out of the shared covariates. The reference already holds the sector indicators. Sector dummies in the covariates give the candidate part of the industry signal before the comparison starts. |
| P3 | Headline rows have no allocated value in any field used, work full time for the full year, and work for an employer for wages or a salary. |
| P4 | The outcome is the log of annual wage income in constant 2010 dollars. |
| P5 | Recommendations for naics-embedder's panel spec: the seen regime fits on 2023 and scores 2024, the held-out regime leaves out whole categories, and the panel has its own decision rule and margin record. |

**Ideas that the session dropped.**

- **A random six-digit code for each person, drawn from QCEW employment
  shares** (the owner's question). The drawn code depends only on the
  category, not on the wage. So it carries no wage information beyond the
  category. The panel could then measure only the category signal, and it
  would count the embedding's six-digit detail as noise. The draw also breaks
  the rule that mixed-depth codes are "never truncated or guessed".
- **Aggregate cells.** See D3.
- **naics-embedder reads the Stage 8 table directly.** See D4.

## Intent

naics-embedder's economic artifact gives the 2,125 NAICS 2022 codes coordinates
that replace one-hot encodings in later models. Today one panel judges it: the
growth panel. That panel uses national QCEW cells, with two covariates for each
row. The owner wants a second test inside a person-level model with many
covariates, because that is the kind of model the artifact serves. This
repository holds the ACS microdata and their verified code annotations, so the
input for that test belongs here.

The file holds one row for each ACS 2023–2024 wage earner. Each row has the
outcome, the person covariates, the survey weights, the person's industry node
and flags. A headline column marks the rows a panel scores. naics-embedder reads
the file in place on this machine. It writes its own panel spec later, in its
own session.

**Why the panel works at category level.** ACS codes industry from a worker's
own words into 264 Census categories. No person-level source in this repository
has both six-digit codes and wages (Measured facts). The economic candidates already give
coordinates to every node, from sector to six digits. The economic decision has
never scored any node above six digits.

## Goals, non-goals and anti-goals

**Goals.**

- One verified, pinned, person-level file of ACS 2023–2024 wage earners. It
  holds the outcome, the covariates, the weights, the industry node, the flags
  and a headline column.
- A link from every row back to its Stage 8 source row.
- Amendments to the source spec that let naics-embedder read the file in place
  on this machine.

**Non-goals.**

- The panel itself: its splits, regimes, comparators, metrics, margin and
  decision. These belong to naics-embedder's panel spec.
- The section for this file in `specs/evaluation-protocol.md`, and the minimum
  number of headline earners for each category. Each is a later item in this
  track (Roadmap placement).
- New IPUMS variables, such as race, Hispanic origin, marital status or
  citizenship. Each needs a new extract with the owner's go-ahead.
- CPS. CPS uses the same Census categories, its sample is much smaller, and its
  mapping to NAICS is not built.
- ACS 2025. The IPUMS sample page lists no 2025 ACS sample on 2026-11-18. It
  says that Census has not announced a release date for the 2025 one-year PUMS.
- Embedding coordinates, or any join to them, in this repository.

**Anti-goals.** The work fails, even if every check passes, when it:

- gives a person a node that covers fewer industries than the code ACS
  delivered (D6);
- fills, models or corrects an allocated value. Census allocations stay
  flagged and out of the headline;
- lets a person row, or a result for one person, leave this machine or enter a
  repository;
- lets the file train, tune or mine examples for an embedder (R8.4);
- rebuilds or edits Stage 8 or an earlier bundle, or edits a frozen module.

## Measured facts

The Stage 8 core table of `stage8_acs_mapping_20261018_r7`, read on 2026-11-18.
"Earners" means rows with `INCWAGE > 0`. No such row has the N/A code 999999 or
the missing code 999998.

**How the 264 categories match NAICS nodes** (shares of earners weighted by
`PERWT`):

| Category type | Categories | Earners | Coordinates |
|---|---|---|---|
| One six-digit code (`finest`, or `whole_node` at national-industry level) | 62 | 19.5% | Exact |
| One whole 4-digit industry group | 72 | 21.3% | Exact |
| One whole 5-digit industry | 29 | 9.2% | Exact |
| One whole 3-digit subsector or sector | 15 | 11.2% | Exact |
| A mixture (`source_aggregate`) with a node of its own | 55 | 27.3% | Approximate: the smallest node that holds the category |
| A mixture whose node is also another category's node | 31 | 11.5% | None: 11 nodes, so several categories get one vector |

The scalar code field of Stage 8 is filled only for codes delivered at six
digits (5 categories). The other 57 single-code categories are codes at the top
of a chain where each node has one child, such as `6231` → `62311` → `623110`.
Their common node is the bottom of that chain. For 86 `whole_node` categories
the common node is deeper than the delivered node. For every mixture the two
are equal. On the headline rows, the common node puts 63 categories and
262,711 rows (20.5%) at six digits. The delivered node would put 6 categories
and 11,760 rows there (D6).

Mixtures are not spread evenly. They hold 91% of utilities earners, 87% of
accommodation and food, 81% of public administration, 62% of finance, 55% of
manufacturing, 47% of health care and 36% of education. The 31 categories that
share a node include schools (`611M1`), public administration (`92MP`), finance
(`52M2`, `52M3`) and the seven military categories (`92811P1` to `92811P7`).

**The headline funnel** (unweighted rows, 2023 and 2024 pooled):

| Step | Rows |
|---|---|
| Earners | 3,035,086 (2023: 1,512,735; 2024: 1,522,351) |
| No allocated value in the nine fields that the headline reads | 2,126,596 |
| Also full time (`UHRSWORK` ≥ 35) and full year (`WKSWORK2` = 6) | 1,575,068 |
| Also works for an employer (`CLASSWKRD` 22, 23, 25, 27 or 28) | 1,496,864 |
| Also not in a category that shares its node | 1,278,878 (2023: 639,002; 2024: 639,876) |

The headline has 233 categories in each year. Pooled over both years, the
smallest category has 89 headline earners, and the median category has 2,045.
24.5% of earners have an allocated wage, and 18.1% have an allocated industry
(weighted).

**Top codes.** IPUMS states that ACS top-codes `INCWAGE` at the 99.5th percentile
in each state. Values above that cut are replaced by the state mean of the
values above it. In the table, the highest value in each state and year is
shared by 1.22% (2023) and 1.24% (2024) of earners. That value is the
replacement mean. About 1.5% of headline rows have it.

**Other sources** (for the record):

- CPS codes industry with the 2022 Census industry code list, so it has the
  same kind of mixtures.
- ITA: 96.4% of the 3,206,055 establishment-year records map to exactly one NAICS
  2022 six-digit code. ITA has no wages.

## Approaches

| Approach | What it gives | Cost | Verdict |
|---|---|---|---|
| Aggregate cells: category × age band × sex × education × occupation group × year, with each cell's mean, spread and counts | Exact person-level squared error for any model whose prediction is the same across a cell. No change to R8.1 | Banded covariates, coarse occupation, and no interactions that were not planned | Rejected (D3) |
| naics-embedder reads the Stage 8 table in place | No build here | A 910 MB table with 261 columns. naics-embedder must reimplement this repository's flag rules, and nobody here verifies them | Rejected (D4) |
| **A person-level wage file, built and verified here** | One small pinned file. The rules on allocation, top codes and shared nodes sit beside the invariants that govern them | A new stage, with build, verify and replay | **Chosen** (D3, D4) |

## Design

### Rows

Every Stage 8 core row with `INCWAGE > 0`: 3,035,086 rows, in Stage 8 source
order. The file keeps rows that are not headline, so that a panel can report
what each exclusion does. A later change to the panel's population then needs
no rebuild (my call).

### Columns

Delivered columns keep their Stage 8 names, types and values. New columns are
marked *new*.

| Group | Columns |
|---|---|
| Link | `source_parquet_sha256`, `source_row`, `YEAR`, `acs_sample_id` |
| Weights | `PERWT`, `REPWTP1` to `REPWTP80` |
| Outcome | `INCWAGE`, `INCWAGE_CPIU_2010`, *new* `log_wage_2010`: the natural log of `INCWAGE_CPIU_2010`, as Float64 |
| Work | `UHRSWORK`, `WKSWORK2`, `CLASSWKR`, `CLASSWKRD` |
| Person | `SEX`, `AGE`, `EDUC`, `EDUCD`, `DEGFIELD`, `DEGFIELDD`, `STATEFIP`, `REGION`, `GQ` |
| Occupation | `OCC`, `OCCSOC`, `occupation_canonical_common_node_id`, `occupation_aggregation_type` |
| Industry | `IND`, `INDNAICS`, `industry_canonical_common_node_id`, `industry_aggregation_type`, `industry_canonical_finest_candidates`, `industry_native_node_id`, *new* `industry_node_code`, *new* `industry_node_level`, *new* `industry_delivered_node_code`, *new* `flag_industry_shared_node` |
| Allocation | `QINCWAGE`, `QIND`, `QOCC`, `QUHRSWOR`, `QWKSWORK2`, `QAGE`, `QSEX`, `QEDUC`, `QCLASSWK`, `QDEGFIELD`, *new* `flag_any_allocated` |
| Edits | *new* `flag_incwage_topcoded` |
| Population | *new* `flag_full_time_full_year`, *new* `flag_wage_salary`, *new* `flag_headline` |

The file leaves out household identifiers (`SERIAL`, `CBSERIAL`, `PERNUM`),
`PUMA`, county, the workplace and migration geography, and `CLUSTER` and
`STRATA`. The replicate weights carry the variance. Fewer identifying fields
lower the disclosure risk (my call).

Occupation enters a panel as a category, not as coordinates. So occupation
mixtures need no rule (my call).

### Rules for the new columns

- **`industry_node_code`**: the code part of `industry_canonical_common_node_id`,
  unchanged, such as `5614`, `623110` or `31-33`. This is the join key (D6).
  naics-embedder keys a combined sector by its first code (`31`). Its panel
  spec maps the key.
- **`industry_delivered_node_code`**: the code part of `industry_native_node_id`,
  such as `6231`. A panel may score it as a check on D6. It is never the
  headline join key.
- **`industry_node_level`**: the level part of the same ID, such as
  `industry_group`.
- **`flag_industry_shared_node`**: true when another `INDNAICS` category among
  the file's rows has the same common node. The measured value is 31
  categories on 11 nodes.
- **`flag_any_allocated`**: true when any of the ten Q columns above is not `0`.
  The headline reads nine of them. `QDEGFIELD` is carried for panels that use
  field of degree, and it does not enter the headline (my call).
- **`flag_full_time_full_year`**: `UHRSWORK` ≥ 35 and `WKSWORK2` = 6, which IPUMS
  labels 50–52 weeks. The builder confirms the label from the delivered DDI.
- **`flag_wage_salary`**: `CLASSWKRD` is 22, 23, 25, 27 or 28: private for-profit,
  private nonprofit, federal, state or local employees. Self-employed people
  (13 and 14) and unpaid family workers (29) are outside the headline. The
  delivered DDI files 29 under `CLASSWKR` = 2, so a rule on `CLASSWKR` alone
  would admit 1,266 unpaid family workers with a positive wage (my call).
- **`flag_incwage_topcoded`**: `INCWAGE` equals the highest `INCWAGE` of its
  state and year among the file's rows. A state with no value above its cut
  would get a false flag on its highest real value. The builder compares the
  flagged values once with IPUMS's "Values Exceeding Top codes, by State" page,
  for the years that page lists, and records the result in the finding. The
  page is not a manifested reference, and no command reads it. A mismatch is
  recorded, not a stop, because the flag is diagnostic and top-coded rows stay
  in the headline (my call). The measured share of earners at the highest
  value runs from 0.68% to 1.59% across states and years.
- **`flag_headline`**: no allocated value in the nine headline fields,
  full time and full year, an employee by `flag_wage_salary`, and no shared node.
- **Top-coded rows stay in the headline** (my call). The value is a Census edit:
  the state mean of reported values above the cut, not a model of one person.
  Leaving those rows out would cut off the top of the wage range, most of all in
  finance. The panel can report a run without them.

### Bundle and commands

A new command group, `python -m embedding_data.acs_wage_microdata`, separate
from the frozen top-level CLI. It has exactly `build`, `verify` and
`compare-runs`. It follows the Stage 10 contract:

- an explicit `--data-dir`;
- the mapping run and its detached pin
  (`1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4` for
  `stage8_acs_mapping_20261018_r7`), checked before any content is read;
- offline work: no `.env`, no credential, no HTTP client and no upstream
  builder;
- refusal of an occupied final or `.part` path, a symlink or an unsafe ID;
- exclusive staging, and a clean-up of only its own temporary paths on failure;
- one sorted JSON line on success, a fixed diagnostic and exit 2 on failure,
  and exit 1 for an unequal comparison.

The bundle is `derived/acs/wage-microdata/<RUN_ID>/`, with
`acs_wage_persons.parquet`, `inputs.json`, `report.json` and a detached
`outputs.json`. `report.json` holds aggregate counts only: the funnel, the
counts for each category and year, and the flag counts.

### Amendments to the source spec

The stage's plan applies these when the stage merges.

1. **R8.1** gains: "One person-level analysis file, the ACS wage microdata, may
   be read in place on the machine that built it, under its detached pin, to
   judge an economic candidate of naics-embedder. The file never leaves that
   machine and never enters a repository. The reader's results for single
   persons, such as predictions, residuals, cached folds and debug output, are
   bound by the same rule. Only aggregate scores and decisions are shared."
2. **R7.2 and R7.4**: the wage microdata are a person-level analysis file, not a
   target family. They have their own schema, outside the long target schema.
   The worker-profile family of R7.2 is unchanged.
3. **R8.4**: the file only judges, and never trains. The protocol section for the
   file states which part selects and which part judges.
4. **`CLAUDE.md`**: the invariant line "only aggregates are shared" names the R8.1
   exception. The deliverable map gains a row for the file, with "Yes" in the
   Economic column.

## Handoff to naics-embedder

A later naics-embedder session writes the wage panel spec (its P2, Req 29 "Later
panels"). These points come from this session. That spec decides each of them.

- **Rows.** `flag_headline = true`.
- **Comparators.** Covariates alone; covariates plus the candidate's node
  coordinates; covariates plus category one-hot; covariates plus ancestor
  indicators from the sector down to one level above each row's node; and the
  text-only table.
- **Regimes.** The seen regime fits on 2023 and scores 2024. The held-out regime
  leaves out whole categories. The spec says how to group the 15 categories at
  subsector or sector level, which have no 4-digit parent.
- **Decision.** Its own decision rule over rows of mixed depth, and its own
  margin record. 20.5% of headline rows join at six digits, and the rest join
  at coarser nodes. The margins of 2026-10-17 are not read.
- **Join.** `industry_node_code` to the codebook, with `31-33`, `44-45` and
  `48-49` keyed by their first code. For a single-child chain, the ancestor
  indicators down to one level above the node identify the category, as they
  do for single-child six-digit codes in the growth panel.
- **Machine.** The read runs on this Mac, under the file's pin.
- **Relatedness.** Req 23 keeps the relatedness artifact out, because it trains
  on ACS 2023–2024. A final year outside that window, such as ACS 2025, would
  need a new file and a new pin.

## Constraints

- Frozen modules stay frozen. The stage adds modules only. The root `uv.lock`
  and `pyproject.toml` do not change, and no new dependency is needed.
- Run one full-data build at a time. Before every commit, every full pytest run
  and every full-data command, run `pgrep -fl
  'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'` and stop if
  it prints anything.
- The build reads the Stage 8 core table in place, through a lazy scan that
  selects only the columns above. The Stage 9 build was killed by memory
  pressure (exit 137), so the builder measures peak memory on the first
  full-data build and records it.
- Every production command passes `--data-dir
  /Users/lowell/Projects/embedding-data/data`.

## Verification: observable outcomes

1. `verify` passes with the detached pin. A replay build passes `verify`, and
   `compare-runs` reports equal.
2. The file has 3,035,086 rows: 1,512,735 for 2023 and 1,522,351 for 2024.
3. `flag_headline` is true on 1,278,878 rows (2023: 639,002; 2024: 639,876), over
   233 categories in each year. If the build differs, the finding explains the
   rule that differs before anything is adopted.
4. An independent reconciler joins every row to its Stage 8 row through
   `source_row` and finds every carried column equal.
5. No headline row has an allocated value in the nine headline fields, is not
   full time and full year, has `flag_wage_salary` false, or has a shared node.
6. Every `industry_node_code` and `industry_delivered_node_code` names a node in
   the Stage 4 NAICS 2022 node table. Each delivered node is the node itself or
   an ancestor whose chain down to the join node has one child at each level.
7. The Stage 8 bundle, the raw manifest and every earlier bundle are
   byte-identical before and after the stage.
8. `git ls-files` lists no data file. `report.json` holds aggregate counts only.
9. A fixture chain shows software readiness. It is never reported as evidence.

## Left to the builder

- Module names and exact CLI options, after the Stage 10 pattern.
- Fixture design.
- Confirmation of the `WKSWORK2` and `CLASSWKRD` labels from the delivered DDI.
- How the build checks the Stage 8 run before reading it. Stage 9's
  `acs_mapping_bundle.verify_bundle` is the precedent. It took about 6 minutes
  for each run in Stage 9.

## Roadmap placement

A proposal for derive-roadmap:

- **Track H: ACS wage microdata.** It is independent of Tracks A to G. It reads
  Stage 8 in place and does not wait for Stage 9.
- **O22.** The wage microdata, first build (this spec). Stage 17.
- **O23.** A minimum number of headline earners for each category, set from the
  built counts, as O4 did for the ITA targets.
- **O24.** A protocol section for the file in `specs/evaluation-protocol.md`, after
  the build and O23.
