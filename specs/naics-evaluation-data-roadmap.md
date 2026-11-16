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
- Stage 1 process (owner, 2026-11-16): lighter. Stage 1 runs the first build, `verify`, the existing reconciliation script and the preservation checks, and writes a one-screen findings file. The exact replay check, the long-form acceptance finding, the README and CLAUDE.md run pins and plan 11's retirement move to Stage 4.
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
| O6 | Evidence for KYB and anomaly detection | B | 4 | USAspending subawards with SAM.gov entity NAICS. Needs a SAM.gov account that the owner creates. Terms risk E6. Size unknown (`specs/uncovered-uses-evidence-sources.md`) |
| O7 | Evidence for peer and competitor detection | B | 2 | EPA TRI parent links: one CSV per year, no account. One build gives O7 and O8. Size unknown (`specs/uncovered-uses-evidence-sources.md`) |
| O8 | Evidence for holding-company classification | B | 3 | Same build as O7 |
| O9 | Evidence for supply-chain dependency | B | 5 | BEA 2017 benchmark input–output tables: a few tables, no account, non-headline. One build gives O9 and O10. Small (estimate) (`specs/uncovered-uses-evidence-sources.md`) |
| O10 | Evidence for look-alike prospecting | B | 6 | Same build as O9 |
| O11 | Evidence for co-visitation | B | parked | None: uncovered, no free source (`specs/uncovered-uses-evidence-sources.md`). No build |
| O12 | TRI hardening: Stage 5's TRI bundle gets an exact replay check and a long-form acceptance finding (owner, 2026-11-16) | B | 7 | One replay build plus `compare-runs`. Estimate from Stage 5's measured run cost |
| O13 | A headline minimum count for the TRI family, set from its observed counts (owner, 2026-11-16) | B | 8 | Small: one pass over the TRI family's `n_unweighted` counts, like O4 |

Tracks: A — ITA NAICS targets (known progression). B — Evidence for six uncovered
uses (research). B is split from A because each answer stands without the other.
Track order: A, then B (owner, 2026-11-16). After Stage 2 reported, the owner
re-ranked Track B (2026-11-16): O7 and O8 (TRI) first, then O6, then O9 and O10,
then the new O12 and O13.
O11 is uncovered and parked in `specs/deferred_items.md`.

## Stages

Order: the two core stages come first, in the owner's track order. Track A's later
stages follow in its ranking. No dependency changes this order. Stage 2 consumes
nothing from Stage 1. The order diverges from the old spec's Rollout, which put
ACS before the remaining ITA targets. The owner chose the ITA NAICS targets as the
first answer. The owner approved this partition on 2026-11-16. Stage 5, the first
promoted Track B item, follows Track A's Stages 3 and 4 (owner, 2026-11-16).

- [x] Stage 1: ITA NAICS targets, first build
      Objective: Plan 11's bundle is built once on real ITA data and verified.
      Outcomes: O1, O2, O3
      Track: A
      Consumes: plan 11 (`specs/plans/11-ita-establishment-targets.md`) with Tasks 1–10 merged in PR #11 (`118b231`) and Task 11 Step 2 (Gate 1) done on 2026-11-16: three NAICS index files in `raw/references/naics/` and their three manifest lines (3,010 lines in all). Its spec `specs/ita-establishment-targets.md`. Codes run `stage4_v11_20261013_r2` with detached pin `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` and the adopted Stage 2 summary (SHA-256 `6335cda7adb40a41c4a11d57d22048999449ac8d078a2ec0291f0198cd9136a8`). The plan 11 execution ledger, 44 rulings, in the gitignored `.sdd/11-ita-establishment-targets/` of worktree `.claude/worktrees/vigilant-mirzakhani-bee453`. The owner's go-ahead for each production write and a confirmed closed Stage 9 freeze window (`CLAUDE.md`, Stage 10)
      Produces: one verified Stage 10 bundle in `data/derived/osha/establishment-targets/<RUN_ID>/` with its detached `outputs.json` pin. `specs/naics-evaluation-data-stage-1-findings.md`
      Exit: O1: the bundle's text–code pair tables exist, `verify` with the detached pin passes, and pair records sum to 3,206,055 and to each year's V1 `n_rows` (plan 11 Task 11 Step 7). O2: the bundle's co-ownership `targets-v1` rows exist, each `size_gate_pending`, and `scripts/reconcile_stage10.py co-ownership` reports equal. O3: the bundle's establishment-link table exists and `scripts/reconcile_stage10.py stage3` reports equal. Plan 11 Task 11 Step 8 (preservation) passes (owner, 2026-11-16). The findings file records the run ID, the pin, and the wall time, maximum RSS and bundle size of the real run
      Leaves out: exact replay check (Task 11 Steps 5–6: replay build and `compare-runs`) → Stage 4. Long-form acceptance finding (Step 9) → Stage 4. README and CLAUDE.md run pins (Step 9) → Stage 4. Plan 11 retirement → Stage 4. Headline minimum count → Stage 3 (O4)
      ROUTING: writing-plans
> Stage 1: COMPLETE (2026-11-16) — implemented by plan 11 (specs/plans/11-ita-establishment-targets.md), Task 11 first build; findings in specs/naics-evaluation-data-stage-1-findings.md.

- [x] Stage 2: Evidence sources for six uncovered uses
      Objective: For each of the six uses, decide which free source could supply the missing evidence, or record that none exists.
      Outcomes: O5
      Track: B
      Consumes: source: Decision 2 in `specs/redo-roadmap-prompt.md` (section Uncovered uses). The brainstorming session receives that section's "Handoff for the design stage", with its Constraints and traps, Owner gates and Leave alone lists. The old spec at `147802f`. The owner's answers on the three Defaults to flag (2026-11-16): (1) free data only, and a use with no free source is recorded as uncovered, with the sources considered and why each fails; (2) a new spec under `specs/` that states how it amends R1.1 and the other three-source lines; (3) published aggregates admitted under a stated exception, with missing fields named and flagged, never filled
      Produces: an owner-approved, committed design spec under `specs/`. `specs/naics-evaluation-data-stage-2-findings.md`
      Exit: O5: the committed spec gives each of the six uses a named free source or an uncovered verdict with the sources considered. The findings file records each verdict and the stage's measured cost in sessions. No file was downloaded
      Leaves out: fetching or building any source → Ranked list items O6–O11. The R8.4 training-role amendment → a separate owner decision after naics-embedder's spec (reset prompt, Leave alone)
      ROUTING: brainstorming
> Stage 2: COMPLETE (2026-11-16) — implemented by spec specs/uncovered-uses-evidence-sources.md, approved by the owner (no plan). Findings in specs/naics-evaluation-data-stage-2-findings.md.

- [ ] Stage 3: Headline minimum count for NAICS targets
      Objective: A minimum cell count for headline use of the NAICS targets is set from their observed counts.
      Outcomes: O4
      Track: A
      Consumes: Stage 1's verified bundle and findings file. The 2023 ITA area mix `stage6_ita_area_mix_20261014_1000_csv`. Spec R7.3 and V9 in `specs/embedding-evaluation-data-spec.md`
      Produces: a committed minimum-count decision for the NAICS targets
      Exit: O4: a committed decision sets the minimum count from the observed `n_unweighted` distributions of the Stage 1 co-ownership target and the 2023 ITA area mix, and reports for each family how many cells meet it
      Leaves out: the minimum count for SOC, geography, ACS and CPS families → the deferred item for old Stage 13. The minimum count for each new Track B family → that family's own stages, O13 for TRI (Resolved at resume, 2026-11-16: Stage 2 spec, "Rules for every new family")
      ROUTING: brainstorming

- [ ] Stage 4: ITA NAICS targets, hardening
      Objective: Stage 1's bundle gets its exact replay check, long-form acceptance finding and README and CLAUDE.md run pins, and plan 11 retires.
      Outcomes: O1, O2, O3 (hardening)
      Track: A
      Consumes: Stage 1's bundle, pin and findings file. Plan 11 Task 11 Steps 5, 6, 9 and 10. The plan 11 ledger's 47 rulings, 3 of them `Ruling (unclear):`, from the backup that the Stage 1 findings file names, for the Plan Completion Protocol (Resolved at resume, 2026-11-16: owner; Stage 1 findings, "For Stages 3 and 4")
      Produces: exact replay check: a replay bundle and its `compare-runs` result. Long-form acceptance finding: `specs/findings/stage-10-ita-establishment-targets.md`. README and CLAUDE.md run pins. Plan 11 in `specs/plans/completed/`
      Exit: `verify` of Stage 1's run with its detached pin passes from Stage 4's checkout and venv, because `compare-runs` does not check software identity (Resolved at resume, 2026-11-16: owner; Stage 1 findings, "For Stages 3 and 4"). The replay bundle's `verify` passes and `compare-runs` against Stage 1's run reports `"equal": true`. The long-form acceptance finding is committed. README and CLAUDE.md name the selected runs and pins. Plan 11 retires through the Plan Completion Protocol
      Leaves out: nothing
      ROUTING: writing-plans

- [ ] Stage 5: TRI parent links, first build
      Objective: EPA TRI facility parent links are built once on real data as a new evidence family and verified.
      Outcomes: O7, O8
      Track: B
      Consumes: the Stage 2 spec `specs/uncovered-uses-evidence-sources.md` (Source 3, Rules for every new family, Source spec amendment) and `specs/naics-evaluation-data-stage-2-findings.md`. The official NAICS concordances of codes run `stage4_v11_20261013_r2`, for reporting years coded in NAICS 2017. The owner's go-ahead for each file fetch
      Produces: one verified TRI parent-link bundle under `data/derived/` with its detached pin. `specs/naics-evaluation-data-stage-5-findings.md`
      Exit: Preflight: open checks E7–E9 are settled before any data is trusted. A failed check stops the stage for an owner decision (Stage 2 spec, Rules for every new family). O7: the bundle relates two NAICS 2022 industries through facilities that report one parent, grouped by a parent identifier or EPA's standardized parent name and never by a name match of this project's own, and `verify` with the detached pin passes. O8: for each parent, the bundle lists its facilities' NAICS 2022 industries. As the first adopting stage, Stage 5 applies the Stage 2 spec's amendment items 1 (introduction), 2 (Core principle), 3 (R1.1 "three core sources" and the TRI row), 6 (the TRI R7.2 row) and 7 (`CLAUDE.md`). Items 4 (R1.2 free account) and 5 (R7.5 published aggregates) wait for the O6 and O9 stages that need them. The findings file records the run ID, the pin, and the wall time, maximum RSS and bundle size of the real run
      Leaves out: TRI hardening (replay check, long-form acceptance finding) → O12. Headline minimum count for the TRI family → O13. The R8.4 training-role amendment → a separate owner decision after naics-embedder's spec (reset prompt, Leave alone)
      ROUTING: brainstorming

## Ranked list — Track B

Owner's order after Stage 2 (2026-11-16). O7 and O8 left the list as Stage 5. O11
is uncovered and parked in `specs/deferred_items.md`.

1. O6 — USAspending with SAM.gov. Owner-created account, terms risk E6, size unknown
2. O9 — BEA 2017 benchmark tables. Small, no account, non-headline. Same build as O10
3. O10 — same build as O9
4. O12 — TRI hardening. One replay build plus `compare-runs`
5. O13 — TRI minimum count. Small: one pass over its counts

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
the gap rubric over every outcome O1–O13, with evidence for each verdict (implementing
stage and plan, `> Deviation:` notes, `specs/deferred_items.md` entries). Ranked-list
items that the owner never promoted park as deferred items. Each unmet outcome either
becomes a new stage, keeping this roadmap live, or is deferred consciously with a
written why. Then move this file to `specs/completed/`.
