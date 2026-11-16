# NAICS evaluation data: reset review

Read-only review on 2026-11-16 at `dfb2262`. It supports the reset to
[naics-evaluation-data-roadmap.md](../naics-evaluation-data-roadmap.md).
Data root: `/Users/lowell/Projects/embedding-data/data`.

## What works today

| Piece | Works on real data | Artifact | Evidence |
|---|---|---|---|
| ITA Form 300A table | yes | `derived/osha/ita_300a_summary.parquet`: 3,206,055 rows, 2016–2025 | [V10](v10-ita-300a-totals.md) |
| NAICS 2022 graph and ITA canonical codes | yes | `derived/codes/stage4_v11_20261013_r2/`: 2,125 NAICS nodes, 2,105 edges, 4,603 concordance rows, 3,206,055 canonical rows | [V11](v11-ita-naics-mapping.md) |
| Geography references | yes | `derived/geography/stage5_geography_20261014/` | [Stage 5](stage-5-geography-reference-build.md) |
| ITA area mix, 2023 | yes | `derived/targets/stage6_ita_area_mix_20261014_1000_csv/ita_area_mix.parquet`: 126,958 cells, 3,065 counties × 978 NAICS industries | [Stage 6](stage-6-ita-area-mix-build.md) |
| IPUMS verification, ACS mapping | yes, as inputs only | `derived/ipums/verification/`, `derived/acs/mapping/stage8_acs_mapping_20261018_r7/` | [Stage 7](stage-7-ipums-extract-verification.md), [Stage 8](stage-8-acs-codes-area-allocation.md) |
| ACS targets | no | runs r1–r3 left only `.part` directories | [Stage 9](stage-9-acs-targets.md) |
| ITA text–code pairs, co-ownership, links | no | software merged (PR #11), passes on fixtures, no bundle | [plan 11](../plans/11-ita-establishment-targets.md) |
| CPS targets | no | converted Parquet only | none |

Of the six uncovered uses, only co-visitation has nearest coverage on real data:
the ITA area mix, which shows co-location, not visits. Co-ownership has no bundle.
Job-change flows are not built.

## Causes, largest first

1. **Order (scope).** The NAICS-only families were Stage 10 of 13. The old roadmap
   says of its order: "The Rollout's stated reason, registration blocking, no longer
   holds." `main` had no commit from 2026-10-22 to 2026-11-12 while Stage 9 stalled.
2. **Full scale in one step (scope, external).** Stage 9 builds 4 families × 2
   universes × 2 variants with all 80 replicate weights on 3,206,859 ACS core rows
   in one run. Run r1 died at 5,085 s (exit 137). Eight probes and 12 unpushed
   commits followed. No bundle exists.
3. **Early final-standard qualities (scope).** Manifests (Stage 1), a manifest audit
   (Stage 3), output manifests and V12 (Stage 6), then detached pins, replay builds,
   independent reconciliation and frozen software hashes. `specs/` holds 35,145
   Markdown lines against 23,434 source lines. Tests hold 37,210 lines and
   independent scripts 7,192.
4. **Process per stage (process).** Of 240 commits on `main`, 80 are docs or chore,
   against 68 feat, 50 fix and 28 test. There were 9 reconcile passes and 8 plan
   retirements. Plans hold 19,763 lines and findings 9,111. Stages 1–8 took 8 days.
5. **External limits.** The host has 36 GiB of memory. A 10,000-record Census batch
   was reset at 305.7 s, so Stage 6 used 1,114 batches of 1,000. Other sessions'
   test runs delayed Stage 9 probes on 2026-10-30 and 2026-11-01.

Line counts use `git ls-files` at `dfb2262`. Commit counts are non-merge commits on `main`.
