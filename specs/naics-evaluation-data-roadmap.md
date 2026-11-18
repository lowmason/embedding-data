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

Amended 2026-11-18 (owner: "Yes, re-stage", then "Approve"): the roadmap runs parallel tracks and
reinstates the ACS and CPS work. That widens the Source beyond NAICS evaluation data. Old Stage 9
also covers commuting and migration targets, and old Stage 11 covers occupation flows. Geography
and SOC work therefore returns for those two tracks.

Choices made:
- First answer: the ITA NAICS targets O1–O3. The 2023 ITA area mix and the NAICS 2022 graph are already built and delivered with it (owner, 2026-11-16).
- Smallest usable standard: plan 11 as specified. That is the pooled 2023–2025 native-2022 window, SE `none`, every target `size_gate_pending` and `verify` passing, with no minimum-count gate in the first answer.
- Target for the first answer: one session.
- Built inputs, cited and never rebuilt: `derived/osha/ita_300a_summary.parquet`, codes `stage4_v11_20261013_r2`, geography `stage5_geography_20261014`, Stage 6 `stage6_ita_area_mix_20261014_1000_csv` and its preparation, Stage 7 `stage7_ipums_verification_20261015_r2`, Stage 8 `stage8_acs_mapping_20261018_r7`, plan 11's merged software (PR #11, `118b231`) and its Gate 1 NAICS index files.
- Stage 1 process (owner, 2026-11-16): lighter. Stage 1 runs the first build, `verify`, the existing reconciliation script and the preservation checks, and writes a one-screen findings file. The exact replay check, the long-form acceptance finding, the README and CLAUDE.md run pins and plan 11's retirement move to Stage 4.
- Plans: plan 11 finishes in this roadmap (Stages 1 and 4). Plans 9 and 10 (ACS targets) stay on hold outside any roadmap, with their files and branch `codex/acs-targets-design` unchanged. (Amended, owner, 2026-11-18: plans 9 and 10 return as Stage 9 of this roadmap. Their files and the branch stay unchanged until that stage's session reads them.)
- Old roadmap: parked (the roadmap file only). Its Stages 9, 11, 12 and 13 are deferred items. Old Stage 10 continues here through plan 11. The spec and the methodology stay in place, because `CLAUDE.md` names the spec as the source of truth and plan 11 cites it. (Amended, owner, 2026-11-18: old Stages 9 and 11 return here as Stages 9 and 11. Old Stages 12 and 13 stay deferred until both tick.)
- Repository: `embedding-data` continues the work. No sibling repository builds this system.
- Track B defaults (owner, 2026-11-16): free data only. A new spec that states how it amends R1.1 and the other three-source lines. Published aggregates admitted under a stated exception, with missing fields named and flagged, never filled.
- Parallel tracks (owner, 2026-11-18): Track B splits by source into Tracks B, C and D, and Tracks E, F and G are added. Each resume hands off the first ready stage of each track, each in its own session and worktree. A stage is ready when its `Consumes` are met. Each tick lands in its own PR. Resumes run one at a time, because each edits this file.
- Stage numbers (owner, 2026-11-18): Stages 9 and 11 keep their old numbers, because code, run IDs and findings cite them. New stages start at 14. Numbers 6 to 8, 10, 12 and 13 are unused here. Stage 14 comes before Stage 15, which follows the owner's 2026-11-16 ranking of O6 before O9 and O10. No dependency orders the tracks.
- Promoted from `specs/deferred_items.md` (owner, 2026-11-18): ACS targets (old Stage 9), CPS panel linkage and job-change flows (old Stage 11), and the `9890` item in section `7-ipums-extract-verification`, which Stage 11 settles first.
- Shared amendments (owner, 2026-11-18): whichever of Stages 5, 14 and 15 merges first applies items 1, 2 and 7 of the Stage 2 spec's amendment and the wording change in item 3. Each of the three adds its own rows under items 3 and 6. Stage 14 adds item 4 and Stage 15 adds item 5.
- Shared resources (owner, 2026-11-18): run one acquisition at a time, because `manifest.append_entries` checks and then appends with no lock. Run one full-data build at a time, because the Stage 9 build was killed with exit 137 (`specs/findings/stage-9-acs-targets.md`). Every session passes the production `--data-dir`.
- Frozen code (owner, 2026-11-18): frozen modules stay frozen, and new families add modules only. A family that needs a new dependency builds as a nested project with its own `pyproject.toml` and `uv.lock`. The selected runs record the root `pyproject.toml`, the root `uv.lock` and every installed distribution. A throwaway project showed that `uv` keeps a nested project out of the root lock. That test has not run in this repository.
- Protocol sections (owner, 2026-11-18): each new family needs its own section in `specs/evaluation-protocol.md` before it is scored. It is the last Ranked-list item of its track (O17 to O21) and is written after that track's first real build. Stage 16 frames its section like Section 1 of the protocol: evidence, assignment and the conditions this repository keeps. The scores may stay with naics-embedder, because the protocol lists them under "What this repository does not decide".

| # | Outcome | Track | Rank | Cost (estimate; basis) |
|---|---|---|---|---|
| O1 | Text–code pairs: each employer's own industry text with each candidate NAICS 2022 code path, pooled 2023–2025 native-2022 window, on real ITA data | A | 1 | One plan-11 build gives O1–O3. Peak memory 5–8 GB, estimated by the Stage 10 final review, on a 36 GiB host. Run time measured by Stage 1 |
| O2 | Co-ownership: for two NAICS 2022 industries, the directional share of EINs with establishments in both | A | 2 | Same build as O1 |
| O3 | Cross-year links between ITA establishments under the adopted R2.7 rules | A | 3 | Same build as O1 |
| O4 | A minimum cell count for headline use of the NAICS targets, set from their observed counts (from spec V9, R7.3) | A | 4 | Small: one pass over the built `n_unweighted` counts. Measured by Stage 3 |
| O5 | For each of the six uses in Decision 2, a named free evidence source, or a recorded reason that none exists | B | 1 | Design sessions only. Nothing is downloaded |
| O6 | Evidence for KYB and anomaly detection | C | 1 | USAspending subawards with SAM.gov entity NAICS. Needs a SAM.gov account that the owner creates. Terms risk E6. Size unknown (`specs/uncovered-uses-evidence-sources.md`) |
| O7 | Evidence for peer and competitor detection | B | 2 | EPA TRI parent links: one CSV per year, no account. One build gives O7 and O8. Size unknown (`specs/uncovered-uses-evidence-sources.md`) |
| O8 | Evidence for holding-company classification | B | 3 | Same build as O7 |
| O9 | Evidence for supply-chain dependency | D | 1 | BEA 2017 benchmark input–output tables: a few tables, no account, non-headline. One build gives O9 and O10. Small (estimate) (`specs/uncovered-uses-evidence-sources.md`) |
| O10 | Evidence for look-alike prospecting | D | 2 | Same build as O9 |
| O11 | Evidence for co-visitation | B | parked | None: uncovered, no free source (`specs/uncovered-uses-evidence-sources.md`). No build |
| O12 | TRI hardening: Stage 5's TRI bundle gets an exact replay check and a long-form acceptance finding (owner, 2026-11-16) | B | 4 | One replay build plus `compare-runs`. Estimate from Stage 5's measured run cost |
| O13 | A headline minimum count for the TRI family, set from its observed counts (owner, 2026-11-16) | B | 5 | Small: one pass over the TRI family's `n_unweighted` counts, like O4 |
| O14 | A scoring section in the evaluation protocol for ITA co-ownership and the 2023 ITA area mix, so that both can be scored (owner, 2026-11-18) | E | 1 | Design sessions only. No build and no download. Estimate; basis: Stage 2 had the same shape |
| O15 | ACS targets on real data: staffing patterns, workplace area mix, and commuting and migration flows in the shared schema (owner, 2026-11-18) | F | 1 | Unknown. Three full builds failed and their cause is unproven. Peak memory is the open question (`specs/findings/stage-9-acs-targets.md`). Measured by Stage 9 |
| O16 | CPS job-change flows on real data: linked person-months with CPS codes mapped to NAICS and SOC, then industry and occupation flows (owner, 2026-11-18) | G | 1 | Unknown: not started. The `9890` question comes first. Measured by Stage 11 |
| O17 | A protocol section for the TRI parent links (owner, 2026-11-18) | B | 6 | Design sessions only, after Stage 5's real build |
| O18 | A protocol section for the USAspending family (owner, 2026-11-18) | C | 2 | Design sessions only, after Stage 14's real build |
| O19 | A protocol section for the BEA family (owner, 2026-11-18) | D | 3 | Design sessions only, after Stage 15's real build |
| O20 | A protocol section for the ACS targets (owner, 2026-11-18) | F | 2 | Design sessions only, after Stage 9's real build |
| O21 | A protocol section for the CPS job-change flows (owner, 2026-11-18) | G | 2 | Design sessions only, after Stage 11's real build |

Tracks: A — ITA NAICS targets (known progression, complete). B — EPA TRI parent
links (research). C — USAspending subawards with SAM.gov (research). D — BEA
input–output tables (research). E — ITA evaluation-protocol section (research: the
choice of scores is open). F — ACS targets (research: the cause of the failed builds
is open). G — CPS job-change flows (research: the meaning of `9890` is open).

B, C and D were one track until 2026-11-18. They split because each answer stands
without the other, and the Stage 2 spec says the six uses give at most three
independent new families. E answers how to score a family, not what the data hold,
so it is split from A and from B to D. F and G split from each other and from A to
E. The ACS targets need no CPS helper, and the old Stage 12 that needs both stays
deferred.
Track order: none (owner, 2026-11-18). The owner's ranking of 2026-11-16 within the
old Track B (O7 and O8 first, then O6, then O9 and O10, then O12 and O13) holds
inside each track and sets the numbers of Stages 14 and 15. Ranks restart within each
track, and their relative order is unchanged.
O11 is uncovered and parked in `specs/deferred_items.md`.

## Stages

Order: the two core stages come first, in the owner's track order. Track A's later
stages follow in its ranking. No dependency changes this order. Stage 2 consumes
nothing from Stage 1. The order diverges from the old spec's Rollout, which put
ACS before the remaining ITA targets. The owner chose the ITA NAICS targets as the
first answer. The owner approved this partition on 2026-11-16. Stage 5, the first
promoted Track B item, follows Track A's Stages 3 and 4 (owner, 2026-11-16). From
2026-11-18 the tracks run in parallel (see Choices made). Stage numbers name stages and
do not set an order.

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

- [x] Stage 3: Headline minimum count for NAICS targets
      Objective: A minimum cell count for headline use of the NAICS targets is set from their observed counts.
      Outcomes: O4
      Track: A
      Consumes: Stage 1's verified bundle and findings file, including the bundle's text–code pair counts (plan 11's `headline_pair_record_distribution` report key, "the V9 handoff") (Resolved at resume, 2026-11-16: owner; spec R7.2). The 2023 ITA area mix `stage6_ita_area_mix_20261014_1000_csv`. Spec R7.3 and V9 in `specs/embedding-evaluation-data-spec.md`
      Produces: a committed minimum-count decision for the NAICS targets
      Exit: O4: a committed decision sets the minimum count from the observed `n_unweighted` distributions of the Stage 1 co-ownership target and the 2023 ITA area mix, and from the observed `n_records` distribution of Stage 1's headline text–code pairs (Resolved at resume, 2026-11-16: owner; spec R7.2, plan 11). It reports for each family how many cells, or headline pairs, meet it. Cross-year links are a support table, not an R7.2 family, and get no minimum count
      Leaves out: the minimum count for SOC, geography, ACS and CPS families → the deferred item for old Stage 13. The minimum count for each new Track B family → that family's own stages, O13 for TRI (Resolved at resume, 2026-11-16: Stage 2 spec, "Rules for every new family")
      ROUTING: brainstorming

> Stage 3: COMPLETE (2026-11-17) — implemented by plan 12 (specs/plans/completed/12-ita-naics-minimum-counts.md); decision in specs/findings/v9-ita-naics-minimum-counts.md. The text-pair gate counts `n_headline_records`, not the Exit's `n_records`, per that plan's Deviation note.
> Next: resume the roadmap.

- [x] Stage 4: ITA NAICS targets, hardening
      Objective: Stage 1's bundle gets its exact replay check, long-form acceptance finding and README and CLAUDE.md run pins, and plan 11 retires.
      Outcomes: O1, O2, O3 (hardening)
      Track: A
      Consumes: Stage 1's bundle, pin and findings file. Plan 11 Task 11 Steps 5, 6, 9 and 10. The plan 11 ledger's 47 rulings, 3 of them `Ruling (unclear):`, from the backup that the Stage 1 findings file names, for the Plan Completion Protocol (Resolved at resume, 2026-11-16: owner; Stage 1 findings, "For Stages 3 and 4")
      Produces: exact replay check: a replay bundle and its `compare-runs` result. Long-form acceptance finding: `specs/findings/stage-10-ita-establishment-targets.md`. README and CLAUDE.md run pins. Plan 11 in `specs/plans/completed/`
      Exit: `verify` of Stage 1's run with its detached pin passes from Stage 4's checkout and venv, because `compare-runs` does not check software identity (Resolved at resume, 2026-11-16: owner; Stage 1 findings, "For Stages 3 and 4"). The replay bundle's `verify` passes and `compare-runs` against Stage 1's run reports `"equal": true`. The long-form acceptance finding is committed. README and CLAUDE.md name the selected runs and pins. Plan 11 retires through the Plan Completion Protocol
      Leaves out: nothing
      ROUTING: writing-plans

> Stage 4: COMPLETE (2026-11-18) — implemented by plan 11 (specs/plans/completed/11-ita-establishment-targets.md).
> Next: resume the roadmap.

- [ ] Stage 5: TRI parent links, first build
      Objective: EPA TRI facility parent links are built once on real data as a new evidence family and verified.
      Outcomes: O7, O8
      Track: B
      Consumes: the Stage 2 spec `specs/uncovered-uses-evidence-sources.md` (Source 3, Rules for every new family, Source spec amendment) and `specs/naics-evaluation-data-stage-2-findings.md`. The official NAICS concordances of codes run `stage4_v11_20261013_r2`, for reporting years coded in NAICS 2017. The owner's go-ahead for each file fetch
      Produces: one verified TRI parent-link bundle under `data/derived/` with its detached pin. `specs/naics-evaluation-data-stage-5-findings.md`
      Exit: Preflight: open checks E7–E9 are settled before any data is trusted. A failed check stops the stage for an owner decision (Stage 2 spec, Rules for every new family). O7: the bundle relates two NAICS 2022 industries through facilities that report one parent, grouped by a parent identifier or EPA's standardized parent name and never by a name match of this project's own, and `verify` with the detached pin passes. O8: for each parent, the bundle lists its facilities' NAICS 2022 industries. Stage 5 adds its own rows under the Stage 2 spec's amendment items 3 (R1.1 "three core sources" and the TRI row) and 6 (the TRI R7.2 row). If Stage 5 merges first of Stages 5, 14 and 15, it also applies items 1 (introduction), 2 (Core principle) and 7 (`CLAUDE.md`) and the wording change in item 3 (Resolved at resume, 2026-11-18: owner). Items 4 (R1.2 free account) and 5 (R7.5 published aggregates) wait for Stages 14 and 15. The findings file records the run ID, the pin, and the wall time, maximum RSS and bundle size of the real run
      Leaves out: TRI hardening (replay check, long-form acceptance finding) → O12. Headline minimum count for the TRI family → O13. The R8.4 training-role amendment → a separate owner decision after naics-embedder's spec (reset prompt, Leave alone)
      ROUTING: brainstorming

- [ ] Stage 9: ACS targets, first full build
      Objective: One ACS target bundle is built on real data and verified, after the cause of the three failed full builds is written down.
      Outcomes: O15
      Track: F
      Consumes: plan 9 (`specs/plans/9-acs-targets.md`) with Tasks 1–9 merged at `3c3ccd0`. The Stage 9 finding `specs/findings/stage-9-acs-targets.md`, with the three failed runs (`stage9_acs_targets_20261019_r1`, `_20261021_r2`, `_20261021_r3`, each `.part` only) and eight probes. Plan 10 (untracked, only in the worktree `/Users/lowell/.codex/worktrees/acs-targets-design/embedding-data`) and the 12 unpushed commits on branch `codex/acs-targets-design`. The selected Stage 8 run `stage8_acs_mapping_20261018_r7` with its pins (`CLAUDE.md`, Stage 8). The owner's go-ahead for each production write
      Produces: one verified ACS target bundle under `data/derived/` with its detached pin, or the owner's decision to retire plan 9. `specs/naics-evaluation-data-stage-9-findings.md`
      Exit: O15: the cause of the three failed full builds is written down with its evidence. Then one ACS target bundle exists and `verify` with its detached pin passes, or the owner retires plan 9 and the findings file says so. The findings file records the run ID, the pin, and the wall time, maximum RSS and bundle size of the real run
      Leaves out: worker profiles and CPS cross-sections (old Stage 12), and the full build, size gate and comparators (old Stage 13) → deferred items, parked until Stages 9 and 11 tick. The ACS protocol section → O20
      ROUTING: brainstorming

- [ ] Stage 11: CPS job-change flows, first build
      Objective: CPS codes are mapped, person-months are linked and job-change flows are built once on real data and verified, after the 2026 meaning of ASEC industry code `9890` is settled.
      Outcomes: O16
      Track: G
      Consumes: the IPUMS deliveries verified by Stage 7 (`stage7_ipums_verification_20261015_r2`, `specs/findings/stage-7-ipums-extract-verification.md`, V6) and the Handoff to Stage 11 of `specs/plans/completed/7-ipums-extract-verification.md`. The `9890` item in `specs/deferred_items.md`, section `7-ipums-extract-verification`, and the deferred item for old Stage 11. Spec R4.3, R4.6–R4.9, R4.11, R5.1 and V11 for CPS in `specs/embedding-evaluation-data-spec.md`. The official concordances of codes run `stage4_v11_20261013_r2`. The owner's go-ahead for each production write
      Produces: one verified CPS job-change bundle under `data/derived/` with its detached pin, and the settled meaning of `9890`. `specs/naics-evaluation-data-stage-11-findings.md`
      Exit: O16: the 2026 meaning of `9890` is settled from an authoritative source, or recorded as unresolved with the owner's decision on its mapping, with no silent leaf assignment and no headline inclusion (the `9890` item's Done when). Then CPS codes are mapped to NAICS and SOC as candidate sets, linked person-month pairs and the CPS weight and SE helpers exist, the job-change flows are built on real data, and `verify` with the detached pin passes. The findings file records the run ID, the pin, and the wall time, maximum RSS and bundle size of the real run
      Leaves out: worker profiles and CPS cross-sections (old Stage 12), and the full build, size gate and comparators (old Stage 13) → deferred items, parked until Stages 9 and 11 tick. The CPS protocol section → O21
      ROUTING: brainstorming

- [ ] Stage 14: USAspending subawards with SAM.gov NAICS, first build
      Objective: USAspending subawards with SAM.gov entity NAICS are built once on real data as a new evidence family and verified.
      Outcomes: O6
      Track: C
      Consumes: the Stage 2 spec `specs/uncovered-uses-evidence-sources.md` (Source 2, Rules for every new family, Source spec amendment) and `specs/naics-evaluation-data-stage-2-findings.md`. The SAM.gov account that the owner creates, and its key, handled as Source 2, Owner gates, says. Not met on 2026-11-18. The official NAICS concordances of codes run `stage4_v11_20261013_r2`. The owner's go-ahead for each file fetch
      Produces: one verified USAspending bundle under `data/derived/` with its detached pin. `specs/naics-evaluation-data-stage-14-findings.md`
      Exit: Preflight: open checks E4–E6 are settled before any data is trusted. A failed check stops the stage for an owner decision (Stage 2 spec, Rules for every new family). O6: the bundle holds the evidence that Source 2 of the Stage 2 spec names, and `verify` with the detached pin passes. The stage adds amendment item 4 (R1.2 free account) and its rows under items 3 and 6. The findings file records the run ID, the pin, and the wall time, maximum RSS and bundle size of the real run
      Leaves out: replay check, long-form acceptance finding and headline minimum count → not staged. The owner decides at the resume after this stage reports, as for O12 and O13 in Track B. The USAspending protocol section → O18. The R8.4 training-role amendment → a separate owner decision after naics-embedder's spec (reset prompt, Leave alone)
      ROUTING: brainstorming

- [ ] Stage 15: BEA input–output tables, first build
      Objective: BEA benchmark input–output tables are built once on real data as a new non-headline evidence family and verified.
      Outcomes: O9, O10
      Track: D
      Consumes: the Stage 2 spec `specs/uncovered-uses-evidence-sources.md` (Source 1, Rules for every new family, Source spec amendment) and `specs/naics-evaluation-data-stage-2-findings.md`. The official NAICS concordances of codes run `stage4_v11_20261013_r2`. The owner's go-ahead for each file fetch
      Produces: one verified BEA bundle under `data/derived/` with its detached pin. `specs/naics-evaluation-data-stage-15-findings.md`
      Exit: Preflight: open checks E1–E3 are settled before any data is trusted. A failed check stops the stage for an owner decision (Stage 2 spec, Rules for every new family). O9 and O10: the bundle holds the evidence that Source 1 of the Stage 2 spec names for supply chain and look-alike. Each BEA value is taken as published, with the fields BEA does not supply null and flagged. `verify` with the detached pin passes. The stage adds amendment item 5 (R7.5 published aggregates) and its rows under items 3 and 6. The findings file records the run ID, the pin, and the wall time, maximum RSS and bundle size of the real run
      Leaves out: replay check, long-form acceptance finding and headline minimum count → not staged. BEA evidence stays non-headline. The owner decides at the resume after this stage reports, as for O12 and O13 in Track B. The BEA protocol section → O19. The R8.4 training-role amendment → a separate owner decision after naics-embedder's spec (reset prompt, Leave alone)
      ROUTING: brainstorming

- [ ] Stage 16: Evaluation-protocol section for ITA co-ownership and the 2023 area mix
      Objective: The evaluation protocol gets a section for ITA co-ownership and the 2023 ITA area mix, framed like Section 1.
      Outcomes: O14
      Track: E
      Consumes: `specs/evaluation-protocol.md`, approved 2026-11-18 (Section 1 as the model, "Families with no section", "What this repository does not decide"). The Stage 10 acceptance finding `specs/findings/stage-10-ita-establishment-targets.md` and the Stage 6 finding `specs/findings/stage-6-ita-area-mix-build.md`, with the runs and pins they record. The V9 decision `specs/findings/v9-ita-naics-minimum-counts.md`. Methodology K5 and K6 in `specs/evaluation-targets-methodology.md`. The Stage 10 spec `specs/completed/ita-establishment-targets.md` (Out of scope)
      Produces: an owner-approved, committed section in `specs/evaluation-protocol.md` for each of the two families. `specs/naics-evaluation-data-stage-16-findings.md`
      Exit: O14: the committed protocol has a section for each family that states the evidence (which run and pin to read), the assignment (who decides the split) and the conditions this repository keeps, as Section 1 does. It names who decides the scores. The findings file records the stage's measured cost in sessions. No source file, test or data file changed
      Leaves out: the scores, their intervals, the margin and the adoption decision, if they stay with naics-embedder (protocol, "What this repository does not decide"). Sections for the ACS and CPS families and each new evidence family → O17 to O21
      ROUTING: brainstorming

## Ranked list — Track B

Owner's order after Stage 2 (2026-11-16), with ranks restarted on 2026-11-18. O7 and O8
left the list as Stage 5. O11 is uncovered and parked in `specs/deferred_items.md`.

1. O12 — TRI hardening. One replay build plus `compare-runs`
2. O13 — TRI minimum count. Small: one pass over its counts
3. O17 — TRI protocol section. Design sessions only, after Stage 5's real build

## Ranked list — Track C

1. O18 — USAspending protocol section. Design sessions only, after Stage 14's real build

## Ranked list — Track D

1. O19 — BEA protocol section. Design sessions only, after Stage 15's real build

## Ranked list — Track F

1. O20 — ACS protocol section. Design sessions only, after Stage 9's real build

## Ranked list — Track G

1. O21 — CPS protocol section. Design sessions only, after Stage 11's real build

Track E has no Ranked list. Its one outcome is Stage 16.

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
the gap rubric over every outcome O1–O21, with evidence for each verdict (implementing
stage and plan, `> Deviation:` notes, `specs/deferred_items.md` entries). Ranked-list
items that the owner never promoted park as deferred items. Each unmet outcome either
becomes a new stage, keeping this roadmap live, or is deferred consciously with a
written why. Then move this file to `specs/completed/`.
