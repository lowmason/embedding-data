# Stage 11 findings: CPS job-change flows, first build

This file records facts from the first full-data build of the CPS job-change flows.
The design is in [the stage spec](cps-job-change-flows.md). The plan was
`specs/plans/23-cps-job-change-flows.md`. Every number here comes from the published
`report.json`, the published tables, the command logs or the checks listed below. Fixture
results are software readiness and never benchmarks. Nothing here validates the
targets for any use.

## Selected run

| Item | Value |
| --- | --- |
| Run ID | `stage11_cps_job_flows_20261124_r1` |
| Detached output pin | `0c815cbeb701bceeb3e1b13dac3678c8142e89bda4c48aa26d4524e79b77e69e` |
| Bundle | `derived/cps/job-flows/stage11_cps_job_flows_20261124_r1/` |
| Built at commit | `2fdf373` (`dirty: false`), 2026-11-24 18:09 UTC |
| Contracts | `cps-job-flows-v1`, `targets-v1`, `cps-job-flows-references-v1` |
| Python | CPython 3.14.0, `uv.lock` SHA-256 `f57c3280a7c8286711bf6804ca4c02f0a19619c9db52f33941b9c5b996cba8e5` |
| References snapshot | `stage11_cps_references_20261124_r1` |
| References receipt pin | `89c59cfa3fa8b4d70bc726b00628db23287b5cc998b05fc8ee71910fafff6c2d` |

Upstream inputs (pins are the SHA-256 of each `outputs.json` or `receipt.json`):

| Input | ID | Pin |
| --- | --- | --- |
| Stage 7 run | `stage7_ipums_verification_20261015_r2` | `db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc` |
| Stage 7 receipt | `stage7_ipums_references_20261015_r2` | `3163968dde603ba53f807976dd09b9e40d73235a98c6f36e4e02c67ec4239c9c` |
| Stage 8 receipt | `stage8_acs_references_20261018_r4` | `052135beb2e77d3cd14b4b800602be9ab36d54aaa43eaf05abffb4d5c14fd2d5` |
| Stage 8 mapping run | `stage8_acs_mapping_20261018_r7` | `1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4` |
| Stage 4 codes run | `stage4_v11_20261013_r2` | `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |

The monthly delivery is `cps_00001` (922,115 rows) and the ASEC delivery is `cps_00002`.
Both were read in place from the Stage 7 Parquets. The owner gave the go-ahead for the
reference acquisition, each of the two BLS imports and the build on 2026-11-24.

## References

`acquire-references` fetched five of the seven reference originals (the Census 2025 layout
and 2026 industry and occupation code lists, and the two IPUMS code pages). BLS refused the
other two. The owner downloaded `2022-census-industry-titles-and-code-list.xlsx` (SHA-256
`1961e60881102732de686a6276beb7e88c61b1948d890ba20ecb26a5f2199a0c`) and
`2018-census-occupation-classification-titles-and-code-list.xlsx` (SHA-256
`501a3a6917d3b6e922f5ef8a2435221d3bac7a52254984e93d9c41ad4d20c844`) in a browser.
Both imports passed their anchor checks as written, so no anchor was loosened. The import
time of each BLS file is a proxy for the browser download time. The manifest grew by 8
lines (seven originals and the receipt), and its earlier 1,553,281 bytes are a byte-identical
prefix.

## Cost

| Command | Wall time | Maximum resident set size |
| --- | --- | --- |
| `build` | 19.4 s | 6.97 GB |
| `verify` | 17.9 s | 7.19 GB |
| `scripts/reconcile_cps_job_flows.py` | 12.9 s | 1.75 GB |

The bundle is 85,080 KiB. The replicates table is 75 MB of it. No memory kill occurred.

## Tables

| Table | Rows |
| --- | --- |
| `cps_category_units` | 838 |
| `cps_flow_diagnostics` | 189 |
| `cps_flow_replicates` | 8,090,400 |
| `cps_flow_support` | 93,124 |
| `cps_job_flows` | 87,408 (54,888 monthly, 32,520 ASEC; 3,033 with a null standard error) |
| `cps_linked_pairs` | 549,515 |

## Checks

- `verify` exits 0 with the detached pin.
- The independent reconciler (`scripts/reconcile_cps_job_flows.py`, standard library, Polars and
  fastexcel only) is equal on all seven checks: `value_classes`, `x_residuals`, `links`,
  `guards`, `eligibility`, `targets` and `asec_se`. It never recomputes a bootstrap standard
  error.
- No replay build ran, by the stage spec. `compare-runs` has no second run to compare.
- Preservation: the SHA-256 of both CPS Parquets, both raw `.csv.gz` and `.xml` files and
  the `outputs.json` of the Stage 4, 7 and 8 runs are identical before and after. The
  manifest is byte-identical, and `embedding-data audit` reports 0 raw provenance
  discrepancies.
- The software suite passed before the build (9,984 tests, 2 behave scenarios).
- The Codex second-opinion seat of the final review was not run.

## Data gates

| Gate | Result |
| --- | --- |
| Unparseable CPS values | 0 |
| Registry | 266 industry and 570 occupation categories, plus the two specials (838 rows) |
| X cross-check | 30 `equal`, 7 `strict_subset` (`1240`, `1970`, `3090`, `7100`, `7640`, `7750`, `8990`), 1 `not_delivered_no_pums_list` (`8865`) |
| One-month links with a positive linking weight | 530,017 (null 0, zero 0) |
| September to November 2025 two-month links | 19,498 on `CPSIDV` (19,703 on `CPSIDP`), counted in no flow |
| `9890` and `9840` | 220 target rows, all in sensitivity universes (`asec_retro` 176, `monthly_ue` 44), none in a strict universe |
| `EMPSAME` 1 or 2 in `MISH` 1 or 5 | 3 source exceptions, kept and counted |
| Funnel `weight_null` and `weight_zero` | 0 |

All gates match the design-time values. No stop condition fired.

### The specials by source and year

| Source | Field | Special rows |
| --- | --- | --- |
| Monthly | `IND` and `OCC` (each) | 38 in 2025, 78 in 2026 |
| ASEC | `IND` and `OCC` (each) | 7 in 2025, 13 in 2026 |
| ASEC | `INDLY` and `OCCLY` (each) | 339 in 2025, 286 in 2026 |

The monthly `9890` and `9840` meaning is settled by the Census 2026 basic code lists.
The ASEC 2026 `9890` meaning stays unresolved by owner decision. The build treats both as
armed-forces specials, keeps every row and gives them no node or candidate.

## Usable guard

| Product | Usable-guard share |
| --- | --- |
| `monthly_ee`, industry | 0.9253 |
| `monthly_ee`, occupation | 0.9176 |
| `monthly_ue`, `asec_retro` | not applicable |

The share is `changed` plus `same` over all eligible employed-to-employed links, and it lives
in `report.json` only.

## Funnels (links or persons, by product and reason)

| Product | Eligible | Main exclusions |
| --- | --- | --- |
| `monthly_ee`, industry | 8,717 | no change reported 458,031; guard unusable 37,985; not employed both 21,194; coding noise 4,090 |
| `monthly_ee`, occupation | 14,964 | no change reported 447,993; guard unusable 41,926; not employed both 21,194; coding noise 3,940 |
| `monthly_ue`, industry and occupation | 5,214 (each) | origin not unemployed 513,516; destination not employed 10,013; origin new worker 1,274 |
| `asec_retro`, industry | 22,179 | same category 105,405; not employed 145,989; last-year code not in the universe 3,281 |
| `asec_retro`, occupation | 14,520 | same category 113,064; not employed 145,989; last-year code not in the universe 3,281 |

Every funnel row carries period `all`. The spec asks for funnels by product, period and
reason. The plan schema allows `all`, so a per-period split is not built.

## Linkage by month pair

| Month pair | `CPSIDV` links | `CPSIDP` matches |
| --- | --- | --- |
| 2025-01 to 2025-02 | 31,272 | 31,527 |
| 2025-02 to 2025-03 | 30,149 | 30,399 |
| 2025-03 to 2025-04 | 30,121 | 30,359 |
| 2025-04 to 2025-05 | 29,827 | 30,084 |
| 2025-05 to 2025-06 | 29,690 | 29,952 |
| 2025-06 to 2025-07 | 29,548 | 29,873 |
| 2025-07 to 2025-08 | 30,193 | 30,509 |
| 2025-08 to 2025-09 | 31,410 | 31,668 |
| 2025-11 to 2025-12 | 28,166 | 28,400 |
| 2025-12 to 2026-01 | 28,438 | 28,697 |
| 2026-01 to 2026-02 | 29,094 | 29,295 |
| 2026-02 to 2026-03 | 28,552 | 28,760 |
| 2026-03 to 2026-04 | 28,248 | 28,472 |
| 2026-04 to 2026-05 | 29,566 | 29,800 |
| 2026-05 to 2026-06 | 29,332 | 29,563 |
| 2026-06 to 2026-07 | 28,660 | 28,937 |
| 2026-07 to 2026-08 | 28,789 | 29,186 |
| 2026-08 to 2026-09 | 28,962 | 29,244 |
| 2025-09 to 2025-11 (two-month) | 19,498 | 19,703 |

The 18 one-month pairs hold 530,017 `CPSIDV` links and 534,725 `CPSIDP` matches. No month
pair has an `other_gap_matches` count above 0. `CPSIDP` and `CPSIDV` have no zero, null or
repeated value inside a month.

## Support (`n_unweighted` per cell)

Every product has a median of 1 unweighted record per cell, so most cells are thin. The
table gives, for each product and policy, the number of cells, the largest cell and the
number of cells with at least 5, 10 and 30 unweighted records.

| Product | Cells | Max | At least 5 | At least 10 | At least 30 |
| --- | --- | --- | --- | --- | --- |
| `monthly_ee`, industry, strict | 3,279 | 372 | 241 | 107 | 27 |
| `monthly_ee`, industry, sensitivity | 3,413 | 372 | 253 | 108 | 27 |
| `monthly_ee`, occupation, strict | 5,492 | 227 | 422 | 198 | 56 |
| `monthly_ee`, occupation, sensitivity | 5,878 | 228 | 429 | 201 | 56 |
| `monthly_ue`, industry, strict | 1,785 | 372 | 105 | 38 | 10 |
| `monthly_ue`, industry, sensitivity | 2,353 | 402 | 132 | 48 | 11 |
| `monthly_ue`, occupation, strict | 2,214 | 80 | 106 | 42 | 10 |
| `monthly_ue`, occupation, sensitivity | 3,030 | 84 | 128 | 43 | 13 |
| `asec_retro`, industry, sensitivity | 9,651 | 114 | 852 | 295 | 38 |
| `asec_retro`, occupation, sensitivity | 6,609 | 92 | 570 | 189 | 27 |

Every target keeps `size_gate_pending`. The headline minimum is V9's decision and is not
set here.

## Rulings and choices made during execution

These decisions were taken while the plan ran. Each is recorded with its cost if wrong in
the plan's completion record.

- A one-month link month outside the 18 frozen months, or an ASEC year outside 2025 and 2026,
  fails the build. This keeps the fixed divisors honest. It did not fire on the delivery.
- A two-month link has a null `weight_a` and status `not_linkable`. The spec says such a link
  has no linking weight.
- The evidence and special diagnostics count the eligible rows of a product frame only. The
  final review found that counting every row made the product labels meaningless, and
  `report.json` `specials` still counts every row by file, field and year.
- `guard_source_exceptions` counts monthly panel rows (any `EMPSTAT`, weight or link status)
  with `MISH` 1 or 5 and `EMPSAME` 1 or 2. The count is 3.
- A transport failure in `acquire-references` stops the acquisition and prints `network`.
  A 403 refusal still lets the other kinds proceed.
- The support and replicates tables carry bare codes in `unit_a` and `unit_b`. The targets
  table carries `feature:<type>:<code>`.

## Not claimed

- Industry flows see only employer changes. A transfer to another establishment of the
  same employer in a different industry is lost.
- X-category candidates rest on a residual rule and an ACS cross-check, not on a published
  CPS member list.
- ASEC flags give no allocation evidence for workers, so no ASEC flow is free of imputed codes.
- Dependent interviewing and the guard can miss real employer changes or report false ones
  (K8-Q1). No correction is applied.
- ASEC differences have no guard. They are an upper bound (K8-Q2).
- The bootstrap has no strata or PSUs, so monthly standard errors may be too small.
- `LNKFW1MWT` was built for adjacent-month links of the whole population. The extract holds
  labor-force members only, so moves into or out of the labor force are not seen.
- `WTFINL`-based levels differ from published totals (V10). Flows inherit any group-specific
  difference.
- A category is not a NAICS or SOC code. The reader compares a category with codes through
  the candidate sets.
- Rotation-group and month-in-sample effects are not modeled.
- The sources disagree about `9890` in 2026. The ASEC treatment rests on the owner's
  decision, not on a document.
- The independent reconciler does not compare the evidence and special diagnostics,
  `asec_flags_by_empstat`, the industry candidate sets or `n_unweighted_distribution`. It
  does not re-check the Stage 7 run pin or the two receipt pins, which the build
  authenticates. It does not restate the rule that a repeated `CPSIDV` fails the build. The
  build and its tests check those items.
- The final review did not run the Codex second opinion.
- Coverage of the targets does not validate their accuracy or representativeness.
- No output may feed embedder training, curriculum, hard-negative mining or model selection
  (R8.4). `cps_linked_pairs.parquet` holds person identifiers, stays on this machine and
  never enters git.
