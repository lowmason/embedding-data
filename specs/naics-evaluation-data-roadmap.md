# NAICS evaluation data — roadmap

> For agentic workers: REQUIRED SKILL: derive-roadmap — resume via its
> reconcile step; route each unticked stage per its ROUTING line; never plan
> this document wholesale.

## Outcomes

Source: the owner, 2026-11-16: "I need NAICS evaluation data only for now: the
targets that evaluate the NAICS embedder. SOC and geography targets can wait."
(`specs/redo-roadmap-prompt.md`), with the owner's Phase 3 and ranking answers of
the same day. Background: `specs/embedding-evaluation-data-spec.md` (old spec),
`specs/evaluation-targets-methodology.md` (its methodology; no critique file
exists), `specs/completed/embedding-evaluation-data-spec-roadmap.md` (old roadmap, parked),
`specs/findings/naics-evaluation-data-reset-review.md` (reset review).

Choices made:
- First answer: the ITA NAICS targets O1–O3. The 2023 ITA area mix and the NAICS 2022 graph are already built and delivered with it (owner, 2026-11-16).
- Smallest usable standard: plan 11 as specified. That is the pooled 2023–2025 native-2022 window, SE `none`, every target `size_gate_pending` and `verify` passing, with no minimum-count gate in the first answer.
- Target for the first answer: one session.
- Built inputs, cited and never rebuilt: `derived/osha/ita_300a_summary.parquet`, codes `stage4_v11_20261013_r2`, geography `stage5_geography_20261014`, Stage 6 `stage6_ita_area_mix_20261014_1000_csv` and its preparation, Stage 7 `stage7_ipums_verification_20261015_r2`, Stage 8 `stage8_acs_mapping_20261018_r7`, plan 11's merged software (PR #11, `118b231`) and its Gate 1 NAICS index files.
- Stage 1 process (owner, 2026-11-16): lighter. Stage 1 runs the first build, `verify` and the existing reconciliation script, and writes a one-screen findings file. The exact replay check, the preservation checks, the long-form acceptance finding, the README and CLAUDE.md run pins and plan 11's retirement move to Stage 4.
- Plans: plan 11 finishes in this roadmap (Stages 1 and 4). Plans 9 and 10 (ACS targets) stay on hold outside any roadmap, with their files and branch `codex/acs-targets-design` unchanged.
- Old roadmap: parked (the roadmap file only). Its Stages 9, 11, 12 and 13 are deferred items. Old Stage 10 continues here through plan 11. The spec and the methodology stay in place, because `CLAUDE.md` names the spec as the source of truth and plan 11 cites it.
- Repository: `embedding-data` continues the work. No sibling repository builds this system.
- Track B defaults (owner, 2026-11-16): free data only. A new spec that states how it amends R1.1 and the other three-source lines. Published aggregates admitted under a stated exception, with missing fields named and flagged, never filled.

| # | Outcome | Track | Rank | Cost (estimate; basis) |
|---|---|---|---|---|
| O1 | Text–code pairs: each employer's own industry text with each candidate NAICS 2022 code path, pooled 2023–2025 native-2022 window, on real ITA data | A | 1 | One plan-11 build gives O1–O3. Peak memory 5–8 GB, estimated by the Stage 10 final review, on a 36 GiB host. Run time measured by Stage 1 |
| O2 | Co-ownership: for two NAICS 2022 industries, the directional share of EINs with establishments in both | A | 2 | Same build as O1 |
| O3 | Cross-year links between ITA establishments under the adopted R2.7 rules | A | 3 | Same build as O1 |
| O4 | A minimum cell count for headline use of the NAICS targets, set from their observed counts (from spec V9, R7.3) | A | 4 | Small: one pass over the built `n_unweighted` counts. Measured by Stage 3 |
| O5 | For each of the six uses in Decision 2, a named free evidence source, or a recorded reason that none exists | B | 1 | Design sessions only. Nothing is downloaded |
| O6 | Evidence for KYB and anomaly detection | B | 2 | Unknown until Stage 2 names a source |
| O7 | Evidence for peer and competitor detection | B | 3 | Unknown until Stage 2 names a source |
| O8 | Evidence for holding-company classification | B | 4 | Unknown until Stage 2 names a source |
| O9 | Evidence for supply-chain dependency | B | 5 | Unknown until Stage 2 names a source |
| O10 | Evidence for look-alike prospecting | B | 6 | Unknown until Stage 2 names a source |
| O11 | Evidence for co-visitation | B | 7 | Unknown until Stage 2 names a source |

Tracks: A — ITA NAICS targets (known progression). B — Evidence for six uncovered
uses (research). B is split from A because each answer stands without the other.
Track order: A, then B (owner, 2026-11-16). B's ranks 2–7 are provisional until
Stage 2 reports.

## Stages

Order: the two core stages come first, in the owner's track order. Track A's later
stages follow in its ranking. No dependency changes this order. Stage 2 consumes
nothing from Stage 1. The order diverges from the old spec's Rollout, which put
ACS before the remaining ITA targets. The owner chose the ITA NAICS targets as the
first answer. The owner approved this partition on 2026-11-16.

- [ ] Stage 1: ITA NAICS targets, first build
      Objective: Plan 11's bundle is built once on real ITA data and verified.
      Outcomes: O1, O2, O3
      Track: A
      Consumes: plan 11 (`specs/plans/11-ita-establishment-targets.md`) with Tasks 1–10 merged in PR #11 (`118b231`) and Task 11 Step 2 (Gate 1) done on 2026-11-16: three NAICS index files in `raw/references/naics/` and their three manifest lines (3,010 lines in all). Its spec `specs/ita-establishment-targets.md`. Codes run `stage4_v11_20261013_r2` with detached pin `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` and the adopted Stage 2 summary (SHA-256 `6335cda7adb40a41c4a11d57d22048999449ac8d078a2ec0291f0198cd9136a8`). The plan 11 execution ledger, 44 rulings, in the gitignored `.sdd/11-ita-establishment-targets/` of worktree `.claude/worktrees/vigilant-mirzakhani-bee453`. The owner's go-ahead for each production write and a confirmed closed Stage 9 freeze window (`CLAUDE.md`, Stage 10)
      Produces: one verified Stage 10 bundle in `data/derived/osha/establishment-targets/<RUN_ID>/` with its detached `outputs.json` pin. `specs/naics-evaluation-data-stage-1-findings.md`
      Exit: O1: the bundle's text–code pair tables exist, `verify` with the detached pin passes, and pair records sum to 3,206,055 and to each year's V1 `n_rows` (plan 11 Task 11 Step 7). O2: the bundle's co-ownership `targets-v1` rows exist, each `size_gate_pending`, and `scripts/reconcile_stage10.py co-ownership` reports equal. O3: the bundle's establishment-link table exists and `scripts/reconcile_stage10.py stage3` reports equal. The findings file records the run ID, the pin, and the wall time, maximum RSS and bundle size of the real run
      Leaves out: exact replay check (Task 11 Steps 5–6: replay build and `compare-runs`) → Stage 4. Preservation checks (Step 8, including the whole-tree audit) → Stage 4. Long-form acceptance finding (Step 9) → Stage 4. README and CLAUDE.md run pins (Step 9) → Stage 4. Plan 11 retirement → Stage 4. Headline minimum count → Stage 3 (O4)
      ROUTING: writing-plans

- [ ] Stage 2: Evidence sources for six uncovered uses
      Objective: For each of the six uses, decide which free source could supply the missing evidence, or record that none exists.
      Outcomes: O5
      Track: B
      Consumes: source: Decision 2 in `specs/redo-roadmap-prompt.md` (section Uncovered uses). The brainstorming session receives that section's "Handoff for the design stage", with its Constraints and traps, Owner gates and Leave alone lists. The old spec at `147802f`. The owner's answers on the three Defaults to flag (2026-11-16): (1) free data only, and a use with no free source is recorded as uncovered, with the sources considered and why each fails; (2) a new spec under `specs/` that states how it amends R1.1 and the other three-source lines; (3) published aggregates admitted under a stated exception, with missing fields named and flagged, never filled
      Produces: an owner-approved, committed design spec under `specs/`. `specs/naics-evaluation-data-stage-2-findings.md`
      Exit: O5: the committed spec gives each of the six uses a named free source or an uncovered verdict with the sources considered. The findings file records each verdict and the stage's measured cost in sessions. No file was downloaded
      Leaves out: fetching or building any source → Ranked list items O6–O11. The R8.4 training-role amendment → a separate owner decision after naics-embedder's spec (reset prompt, Leave alone)
      ROUTING: brainstorming

- [ ] Stage 3: Headline minimum count for NAICS targets
      Objective: A minimum cell count for headline use of the NAICS targets is set from their observed counts.
      Outcomes: O4
      Track: A
      Consumes: Stage 1's verified bundle and findings file. The 2023 ITA area mix `stage6_ita_area_mix_20261014_1000_csv`. Spec R7.3 and V9 in `specs/embedding-evaluation-data-spec.md`
      Produces: a committed minimum-count decision for the NAICS targets
      Exit: O4: a committed decision sets the minimum count from the observed `n_unweighted` distributions of the Stage 1 co-ownership target and the 2023 ITA area mix, and reports for each family how many cells meet it
      Leaves out: the minimum count for SOC, geography, ACS and CPS families → the deferred item for old Stage 13
      ROUTING: brainstorming

- [ ] Stage 4: ITA NAICS targets, hardening
      Objective: Stage 1's bundle gets its exact replay check, preservation checks, long-form acceptance finding and README and CLAUDE.md run pins, and plan 11 retires.
      Outcomes: O1, O2, O3 (hardening)
      Track: A
      Consumes: Stage 1's bundle, pin and findings file. Plan 11 Task 11 Steps 5, 6, 8, 9 and 10. The plan 11 ledger's rulings, for the Plan Completion Protocol
      Produces: exact replay check: a replay bundle and its `compare-runs` result. Preservation checks: the Step 8 results. Long-form acceptance finding: `specs/findings/stage-10-ita-establishment-targets.md`. README and CLAUDE.md run pins. Plan 11 in `specs/plans/completed/`
      Exit: the replay bundle's `verify` passes and `compare-runs` against Stage 1's run reports `"equal": true`. Plan 11 Task 11 Step 8 (preservation, including the whole-tree audit) passes. The long-form acceptance finding is committed. README and CLAUDE.md name the selected runs and pins. Plan 11 retires through the Plan Completion Protocol
      Leaves out: nothing
      ROUTING: writing-plans

## Ranked list — Track B

Provisional order (owner, 2026-11-16). Re-ranked when Stage 2 reports.

1. O6 — unknown until Stage 2 names a source
2. O7 — unknown until Stage 2 names a source
3. O8 — unknown until Stage 2 names a source
4. O9 — unknown until Stage 2 names a source
5. O10 — unknown until Stage 2 names a source
6. O11 — unknown until Stage 2 names a source

## Stage-spec stamp

Each stage spec's Rollout note carries this line, and writing-plans copies it
verbatim into the stage plan's header (for a writing-plans stage, the plan
header carries it directly):

> Roadmap: specs/naics-evaluation-data-roadmap.md, Stage N — on plan
> completion, tick the stage and re-validate later stages against what shipped.

Plan 11 carries Stages 1 and 4. Stage 1 is ticked when its Exit holds. Plan 11's
completion ticks Stage 4.

## Completion

Retire this roadmap only after a conformance audit of the accumulated system: re-run
the gap rubric over every outcome O1–O11, with evidence for each verdict (implementing
stage and plan, `> Deviation:` notes, `specs/deferred_items.md` entries). Ranked-list
items that the owner never promoted park as deferred items. Each unmet outcome either
becomes a new stage, keeping this roadmap live, or is deferred consciously with a
written why. Then move this file to `specs/completed/`.
