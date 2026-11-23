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

Amended again 2026-11-18 (owner: "Approve as drafted"): Track H adds the ACS wage microdata of the
approved spec `specs/completed/acs-wage-microdata.md`. It is a person-level input for naics-embedder's
wage panel, not a target family (that spec, "Amendments to the source spec", item 2).

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
- Protocol sections (owner, 2026-11-18): each new family needs its own section in `specs/evaluation-protocol.md` before it is scored. It is the last Ranked-list item of its track (O17 to O21, and O24) and is written after that track's first real build. Stage 16 frames its section like Section 1 of the protocol: evidence, assignment and the conditions this repository keeps. The scores may stay with naics-embedder, because the protocol lists them under "What this repository does not decide".
- Track H (owner, 2026-11-18): the "Roadmap placement" section of `specs/completed/acs-wage-microdata.md`, approved on 2026-11-18, proposed the track. Track H reads Stage 8 in place and does not wait for Stage 9. Stage 17 goes to writing-plans against that spec, as its header says. Stage 17 keeps the replay check of the spec's Verification item 1, which the owner approved with the spec. Stages 1, 5, 14 and 15 left replay to a later stage or item.
- Resume after Stages 5 and 17 (owner, 2026-11-22, "Approve"): Tracks B and H keep their rankings. O12 becomes Stage 18 and O23 becomes Stage 19. O12 goes first in Track B because a change to a file in `tri_bundle.SOFTWARE_FILES` (it includes `pyproject.toml`, `uv.lock` and the shared Stage 4 to 6 modules) makes `verify` refuse Stage 5's run, so the replay can no longer be compared with it (plan 13, Handoff). Both Stage 17 gate readings stand (Stage 19, Consumes).
- Resume after Stage 14 (owner, 2026-11-22, "Approve as drafted"): Stage 14's Leaves out becomes O25 (USAspending hardening) and O26 (USAspending headline minimum count). Track C ranks O25, O26, O18, as Track B does. O25 becomes Stage 20. It goes first for the reason O12 did: a change to a file in `vendor_link_bundle.SOFTWARE_FILES` (26 files, among them `pyproject.toml`, `uv.lock` and `sam_raw.py`) makes `verify` refuse Stage 14's run (plan 15, Handoff). D2 stays: a blank or invalid last update date makes a firm `dnb_era_record`, so 6,403 firms get no industry (`specs/naics-evaluation-data-stage-14-findings.md`, "The cost of D2"). The live `acquire-sam-extract` request stays deferred (`specs/deferred_items.md`, section `15-usaspending-vendor-links`).
- Resume after Stage 20 (owner, 2026-11-22, "Approve"): Track C keeps its ranking, O26 then O18. O26 becomes Stage 21. Stage 20 found the replay equal to Stage 14's run, with both `verify` runs passing. Its replay build took 25.83 s and 966 MB (`specs/findings/stage-14-usaspending-vendor-links.md`, "Measured cost").
- Resume after Stage 18 (owner, 2026-11-22, "Approve as drafted"): Track B keeps its ranking, O13 then O17. O13 becomes Stage 22. Stage 18 found the replay equal to Stage 5's run, with both `verify` runs passing. Its replay build took 4.83 s and 1,475 MB, and another session's test run may have loaded it. Only the replay's `verify` (3.14 s, 1,509 MB) started on an idle host (`specs/findings/stage-5-tri-parent-links.md`, "Measured cost"). No other stage entry changed: plan 18's Handoff names only O13, O17 and its traps.

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
| O18 | A protocol section for the USAspending family (owner, 2026-11-18) | C | 4 | Design sessions only, after Stage 14's real build |
| O19 | A protocol section for the BEA family (owner, 2026-11-18) | D | 3 | Design sessions only, after Stage 15's real build |
| O20 | A protocol section for the ACS targets (owner, 2026-11-18) | F | 2 | Design sessions only, after Stage 9's real build |
| O21 | A protocol section for the CPS job-change flows (owner, 2026-11-18) | G | 2 | Design sessions only, after Stage 11's real build |
| O22 | A person-level file of ACS 2023–2024 wage earners for naics-embedder's wage panel: the wage outcome, person covariates, survey weights, each person's NAICS node, flags and a headline column (owner, 2026-11-18) | H | 1 | Moderate (estimate): a lazy scan of 3,035,086 rows and about 120 of the 261 columns of the 910 MB Stage 8 core table, run twice for the replay. Stage 8's `verify_bundle` took about 6 minutes for each run in Stage 9. Peak memory measured by Stage 17 |
| O23 | A minimum number of headline earners for each category, set from the built counts, as O4 did for the ITA targets (owner, 2026-11-18) | H | 2 | Small: one pass over Stage 17's counts, like O4 |
| O24 | A protocol section for the ACS wage microdata (owner, 2026-11-18) | H | 3 | Design sessions only, after Stage 17's real build and O23 |
| O25 | USAspending hardening: Stage 14's bundle gets an exact replay check, a long-form acceptance finding and README and CLAUDE.md run pins (owner, 2026-11-22) | C | 2 | Small: one replay build plus `compare-runs`. Stage 14's build took 29.6 s and 961 MB (plan 15, Handoff) |
| O26 | A headline minimum count for the USAspending family, set from its observed counts (owner, 2026-11-22) | C | 3 | Small: one pass over the family's `n_unweighted` counts, like O4 and O13 |

Tracks: A — ITA NAICS targets (known progression, complete). B — EPA TRI parent
links (research). C — USAspending subawards with SAM.gov (research). D — BEA
input–output tables (research). E — ITA evaluation-protocol section (research: the
choice of scores is open). F — ACS targets (research: the cause of the failed builds
is open). G — CPS job-change flows (research: the meaning of `9890` is open). H — ACS
wage microdata (research: O23 and O24 depend on the counts of the first build).

B, C and D were one track until 2026-11-18. They split because each answer stands
without the other, and the Stage 2 spec says the six uses give at most three
independent new families. E answers how to score a family, not what the data hold,
so it is split from A and from B to D. F and G split from each other and from A to
E. The ACS targets need no CPS helper, and the old Stage 12 that needs both stays
deferred. H splits from F because it reads Stage 8 in place and needs no Stage 9 output.
The person-level file stands without the ACS targets, and the targets stand without it.
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
do not set an order. Stages 18 and 19 were promoted from the Ranked lists of Tracks B and H
on 2026-11-22, Stages 20 and 21 from Track C's later that day, and Stage 22 from Track B's
after Stage 18 (see Choices made).

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

- [x] Stage 5: TRI parent links, first build
      Objective: EPA TRI facility parent links are built once on real data as a new evidence family and verified.
      Outcomes: O7, O8
      Track: B
      Consumes: the Stage 2 spec `specs/uncovered-uses-evidence-sources.md` (Source 3, Rules for every new family, Source spec amendment) and `specs/naics-evaluation-data-stage-2-findings.md`. The official NAICS concordances of codes run `stage4_v11_20261013_r2`, for reporting years coded in NAICS 2017. The owner's go-ahead for each file fetch
      Produces: one verified TRI parent-link bundle under `data/derived/` with its detached pin. `specs/naics-evaluation-data-stage-5-findings.md`
      Exit: Preflight: open checks E7–E9 are settled before any data is trusted. A failed check stops the stage for an owner decision (Stage 2 spec, Rules for every new family). O7: the bundle relates two NAICS 2022 industries through facilities that report one parent, grouped by a parent identifier or EPA's standardized parent name and never by a name match of this project's own, and `verify` with the detached pin passes. O8: for each parent, the bundle lists its facilities' NAICS 2022 industries. Stage 5 adds its own rows under the Stage 2 spec's amendment items 3 (R1.1 "three core sources" and the TRI row) and 6 (the TRI R7.2 row). If Stage 5 merges first of Stages 5, 14 and 15, it also applies items 1 (introduction), 2 (Core principle) and 7 (`CLAUDE.md`) and the wording change in item 3 (Resolved at resume, 2026-11-18: owner). Items 4 (R1.2 free account) and 5 (R7.5 published aggregates) wait for Stages 14 and 15. The findings file records the run ID, the pin, and the wall time, maximum RSS and bundle size of the real run
      Leaves out: TRI hardening (replay check, long-form acceptance finding) → O12. Headline minimum count for the TRI family → O13. The R8.4 training-role amendment → a separate owner decision after naics-embedder's spec (reset prompt, Leave alone)
      ROUTING: brainstorming

> Stage 5: COMPLETE (2026-11-21) — implemented by plan 13 (specs/plans/completed/13-tri-parent-links.md). Its Handoff section names what O12, O13 and O17 consume. Stage 5 read only `naics_nodes.parquet` of the Stage 4 bundle. It did not read the Stage 4 concordance that its Consumes line names.
> Next: resume the roadmap.

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

- [x] Stage 14: USAspending subawards with SAM.gov NAICS, first build
      Objective: USAspending subawards with SAM.gov entity NAICS are built once on real data as a new evidence family and verified.
      Outcomes: O6
      Track: C
      Consumes: the Stage 2 spec `specs/uncovered-uses-evidence-sources.md` (Source 2, Rules for every new family, Source spec amendment) and `specs/naics-evaluation-data-stage-2-findings.md`. The SAM.gov account that the owner creates, and its key, handled as Source 2, Owner gates, says. The account exists (Resolved at resume, 2026-11-18: owner). The official NAICS concordances of codes run `stage4_v11_20261013_r2`. The owner's go-ahead for each file fetch
      Produces: one verified USAspending bundle under `data/derived/` with its detached pin. `specs/naics-evaluation-data-stage-14-findings.md`
      Exit: Preflight: open checks E4–E6 are settled before any data is trusted. A failed check stops the stage for an owner decision (Stage 2 spec, Rules for every new family). O6: the bundle holds the evidence that Source 2 of the Stage 2 spec names, and `verify` with the detached pin passes. The stage adds amendment item 4 (R1.2 free account) and its rows under items 3 and 6. The findings file records the run ID, the pin, and the wall time, maximum RSS and bundle size of the real run
      Leaves out: replay check, long-form acceptance finding and headline minimum count → not staged. The owner decides at the resume after this stage reports, as for O12 and O13 in Track B. The USAspending protocol section → O18. The R8.4 training-role amendment → a separate owner decision after naics-embedder's spec (reset prompt, Leave alone)
      ROUTING: brainstorming

> Stage 14: COMPLETE (2026-11-22) — implemented by plan 15 (specs/plans/completed/15-usaspending-vendor-links.md). Its Handoff section names what O18 and the resume after Stage 14 consume. Stage 14 read only `naics_nodes.parquet` of the Stage 4 bundle. It did not read the Stage 4 concordance that its Consumes line names. The O6 row in this roadmap still says that the family needs an owner-created account and that its size is unknown. The family is now built, E6 is closed and the browser path needed no key. The O6 row is not edited. The USAspending row of `specs/deliverable-map.md` was updated at the owner's request (2026-11-22).
> Next: resume the roadmap.

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
      Leaves out: the scores, their intervals, the margin and the adoption decision, if they stay with naics-embedder (protocol, "What this repository does not decide"). Sections for the ACS and CPS families and each new evidence family → O17 to O21. The section for the ACS wage microdata → O24
      ROUTING: brainstorming

- [x] Stage 17: ACS wage microdata, first build
      Objective: One person-level file of ACS 2023–2024 wage earners is built from Stage 8 on real data, verified and replayed.
      Outcomes: O22
      Track: H
      Consumes: the approved spec `specs/completed/acs-wage-microdata.md` (Owner decisions, Design, Amendments to the source spec, Constraints, Verification). The selected Stage 8 run `stage8_acs_mapping_20261018_r7` with its detached pin `1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4` (`CLAUDE.md`, Stage 8). The NAICS 2022 node table of codes run `stage4_v11_20261013_r2`, with detached pin `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`. The owner's go-ahead for each production write
      Produces: one verified bundle in `data/derived/acs/wage-microdata/<RUN_ID>/` with its detached pin. A replay bundle and its `compare-runs` result. `specs/naics-evaluation-data-stage-17-findings.md`
      Exit: O22: items 1 to 9 of the spec's "Verification: observable outcomes" hold. The stage applies items 1 to 4 of the spec's "Amendments to the source spec". The findings file records the run ID, the pin, and the wall time, maximum RSS and bundle size of the real run
      Leaves out: the minimum number of headline earners for each category → O23. The protocol section for the file → O24. The wage panel itself → naics-embedder's panel spec (spec, Non-goals and "Handoff to naics-embedder"). New IPUMS variables, CPS and ACS 2025 → not staged (spec, Non-goals)
      ROUTING: writing-plans
> Stage 17: COMPLETE (2026-11-19) — implemented by plan 14 (specs/plans/completed/14-acs-wage-microdata.md). Its Handoff section names what O23 and O24 consume.
> Next: resume the roadmap.

- [x] Stage 18: TRI parent links, hardening
      Objective: Stage 5's TRI bundle gets its exact replay check, a long-form acceptance finding and README and CLAUDE.md run pins.
      Outcomes: O12
      Track: B
      Consumes: Stage 5's run `stage5_tri_parent_links_20261121_r1`, detached pin `65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b`, snapshot 2025-11-05, built at `786ebcc` with `dirty: false`, and its build arguments: codes run `stage4_v11_20261013_r2`, its Stage 4 pin and `--processed-as-of 2025-11-05` (plan 13, Handoff). A checkout in which every file of `tri_bundle.SOFTWARE_FILES` is byte-identical to the one that built Stage 5's run (Resolved at resume, 2026-11-22: owner; plan 13, Handoff). `specs/naics-evaluation-data-stage-5-findings.md` and the spec `specs/completed/tri-parent-links.md`. The owner's go-ahead for each production write under the Host rule of plan 13 (`specs/plans/completed/13-tri-parent-links.md`, Owner Checkpoints item 5). Recorded at resume, 2026-11-22, for the acceptance finding: the independent reconciler's "equal" does not cover the report fields that the findings file's Limits ("Reconciler coverage") names. The findings file's "Partial owners" limit (line 201) predates the owner's reading at spec lines 472–480 *(owner, plan 13, 2026-11-21)*. The docstring of `scripts/reconcile_tri_parent_links.py` (line 3) names the old spec path, and the script is not in `tri_bundle.SOFTWARE_FILES`
      Produces: a replay bundle under a new run ID and its `compare-runs` result. A committed long-form acceptance finding under `specs/findings/`. README and CLAUDE.md run pins (Resolved at resume, 2026-11-22: owner; `specs/completed/tri-parent-links.md:70-71` and `:755-756`)
      Exit: O12: `verify` of Stage 5's run with its detached pin passes from Stage 18's checkout and venv. The replay bundle's `verify` with its own detached pin passes, and `compare-runs` against Stage 5's run reports equal. The acceptance finding is committed and records the replay run ID, its pin, and the wall time, maximum RSS and bundle size of the replay. README and CLAUDE.md name the selected TRI runs and their pins
      Leaves out: the TRI headline minimum count → O13. The TRI protocol section → O17. The R8.4 training-role amendment → a separate owner decision after naics-embedder's spec (reset prompt, Leave alone)
      ROUTING: writing-plans
> Stage 18: COMPLETE (2026-11-22) — implemented by plan 18 (specs/plans/completed/18-tri-parent-links.md). Its Handoff section names what O13 and O17 consume.
> Next: resume the roadmap.

- [ ] Stage 19: Minimum headline earners for the ACS wage microdata
      Objective: A minimum number of headline earners for each category is set from Stage 17's built counts.
      Outcomes: O23
      Track: H
      Consumes: `report.json` of `stage17_acs_wage_microdata_20261119_r1` (detached pin `6cb253e2e5c2e48a5b31d2790a0378636d3b6ef9197cfb2d33cca2813ac201d1`), with its `categories`, `headline_categories`, `funnel`, `flags`, `node_levels` and `shared_nodes` keys, and `specs/naics-evaluation-data-stage-17-findings.md` (plan 14, Handoff). The O4 decision `specs/findings/v9-ita-naics-minimum-counts.md` as the model. Both Stage 17 gate readings stand: `industry_node_level` is the level of the join node, and spec item 8 reads "no file from `data/` and none added by this stage" (Resolved at resume, 2026-11-22: owner; `specs/history.md`, plan 14 Gate answer). Traps: the `INDNAICS` strings in `categories` are space-padded, the counts are unweighted rows, a category that shares a node is not headline, and headline rows join at mixed depths (plan 14, Handoff)
      Produces: a committed minimum-count decision for the headline earners of the ACS wage microdata
      Exit: O23: a committed decision sets the minimum number of headline earners for each category from the observed `headline_rows` counts of Stage 17's run. The minimum applies to each category, not to each node (plan 14, Handoff). The decision reports, for each year, how many categories meet it
      Leaves out: the protocol section for the file → O24. The wage panel itself → naics-embedder's panel spec
      ROUTING: brainstorming

- [x] Stage 20: USAspending vendor links, hardening
      Objective: Stage 14's USAspending bundle gets its exact replay check, a long-form acceptance finding and README and CLAUDE.md run pins.
      Outcomes: O25
      Track: C
      Consumes: Stage 14's run `stage14_vendor_links_20261122_r2`, detached pin `248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be`, snapshot `2026-11-19`, extract month `2026-10`, built at `1eddb3e` with `dirty: false`, and its build arguments: codes run `stage4_v11_20261013_r2`, its Stage 4 pin, `--snapshot 2026-11-19` and `--sam-month 2026-10` (plan 15, Handoff). A checkout in which every file of `vendor_link_bundle.SOFTWARE_FILES` is byte-identical to the one that built Stage 14's run (plan 15, Handoff). D2 stays (Resolved at resume, 2026-11-22: owner). `specs/naics-evaluation-data-stage-14-findings.md` and the spec `specs/completed/usaspending-vendor-links.md`. The owner's go-ahead for each production write and the owner's confirmation that no Stage 9 freeze window is open. Recorded at resume, 2026-11-22, for the acceptance finding: `compare-runs` skips `inputs.json` (D3), so it does not compare the software record. The independent reconciler ran on `r2` only. `r1` is superseded and stays on disk, and nothing cites it. The findings file's Status line (line 3) still says "Stage 14 in progress". The docstring of `scripts/reconcile_usaspending_vendor_links.py` (line 6) names the old spec path. Its fix rides with the next change to the script (`specs/deferred_items.md`, section `15-usaspending-vendor-links`)
      Produces: a replay bundle under a new run ID and its `compare-runs` result. A committed long-form acceptance finding under `specs/findings/`. README and CLAUDE.md run pins. README has no Stage 14 pin yet, and CLAUDE.md names `r2` only
      Exit: O25: `verify` of Stage 14's run with its detached pin passes from Stage 20's checkout and venv, because `compare-runs` does not check software identity. The replay bundle's `verify` with its own detached pin passes, and `compare-runs` against Stage 14's run reports equal. The acceptance finding is committed and records the replay run ID, its pin, and the wall time, maximum RSS and bundle size of the replay. README and CLAUDE.md name the selected USAspending runs and their pins
      Leaves out: the USAspending headline minimum count → O26. The USAspending protocol section → O18. A changed D2 rule and the live `acquire-sam-extract` request → `specs/deferred_items.md`. The R8.4 training-role amendment → a separate owner decision after naics-embedder's spec (reset prompt, Leave alone)
      ROUTING: writing-plans

> Stage 20: COMPLETE (2026-11-22) — implemented by plan 16 (specs/plans/completed/16-usaspending-vendor-links.md). Its Handoff section names what O26 and O18 consume.
> Next: resume the roadmap.

- [x] Stage 21: Headline minimum count for the USAspending family
      Objective: A headline minimum count for the USAspending vendor-link targets is set from their observed counts.
      Outcomes: O26
      Track: C
      Consumes: `report.json` of `stage14_vendor_links_20261122_r2` (detached pin `248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be`), whose bytes equal those of the replay `stage14_vendor_links_20261122_r2_replay` (detached pin `d08ed4cb396fae172ebde8be65fe6dfc492cb4c2731ad4308cfcf7cd55fd6055`), with its `n_unweighted_distribution` (plan 16, Handoff; plan 15, Handoff). The sections "Full-data build" and "For the resume and O18" of `specs/naics-evaluation-data-stage-14-findings.md`. The Stage 20 finding `specs/findings/stage-14-usaspending-vendor-links.md` holds no counts. The O4 decision `specs/findings/v9-ita-naics-minimum-counts.md` as the model, and "Rules for every new family" of the Stage 2 spec `specs/uncovered-uses-evidence-sources.md`. Trap: a change to any file in `vendor_link_bundle.SOFTWARE_FILES` makes `verify` refuse both runs (plan 16, Handoff)
      Produces: a committed minimum-count decision for the USAspending family
      Exit: O26: a committed decision sets the headline minimum count from the observed `n_unweighted` distributions of the family's buyer-share and supplier-share targets. It reports for each target how many cells meet it. The published bundles keep `size_gate_pending`
      Leaves out: the USAspending protocol section → O18. A changed D2 rule and the live `acquire-sam-extract` request → `specs/deferred_items.md`. The R8.4 training-role amendment → a separate owner decision after naics-embedder's spec (reset prompt, Leave alone)
      ROUTING: brainstorming

> Stage 21: COMPLETE (2026-11-23) — implemented by plan 19 (specs/plans/completed/19-usaspending-minimum-counts.md). Its two Deviation notes record the wider Consumes and cost and the two minimums. Its Handoff section names what O18 consumes.
> Next: resume the roadmap.

- [x] Stage 22: Headline minimum count for the TRI family
      Objective: A headline minimum count for the TRI parent-link targets is set from their observed counts.
      Outcomes: O13
      Track: B
      Consumes: `report.json` of `stage5_tri_parent_links_20261121_r1` (detached pin `65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b`), whose bytes equal those of the replay `stage5_tri_parent_links_20261121_r1_replay` (detached pin `555f6b58099da43c054d828d27048f31a9e992ee32719c7e1462c59b30919cfc`), with its `n_unweighted_distribution` (plan 18, Handoff; plan 13, Handoff). That key summarizes the 14,204 cells of the one target table, `tri_parent_links`, by quantiles and thresholds only. The per-cell counts are the `n_unweighted` column of that table. The sections "Counts" and "For O12, O13 and O17" of `specs/naics-evaluation-data-stage-5-findings.md`. The Stage 18 finding `specs/findings/stage-5-tri-parent-links.md` adds no counts. The O4 decision `specs/findings/v9-ita-naics-minimum-counts.md` as the model, and "Rules for every new family" of the Stage 2 spec `specs/uncovered-uses-evidence-sources.md`. Not measured: how many `naics_*` facility-years name more than one parent (plan 18, Handoff). Traps: a change to any of the 24 files in `tri_bundle.SOFTWARE_FILES`, the Python build or the installed distributions makes `verify` refuse both runs. `verify` costs about 1.5 GB and counts as a full-data command under the Host rule (plan 18, Handoff)
      Produces: a committed minimum-count decision for the TRI family
      Exit: O13: a committed decision sets the headline minimum count from the observed `n_unweighted` distribution of the `tri_parent_links` target. It reports how many cells meet it. The published bundles keep `size_gate_pending`
      Leaves out: the TRI protocol section → O17. The R8.4 training-role amendment → a separate owner decision after naics-embedder's spec (reset prompt, Leave alone)
      ROUTING: brainstorming

> Stage 22: COMPLETE (2026-11-23) — implemented by plan 20 (specs/plans/completed/20-tri-minimum-counts.md). Its Deviation note records the wider Consumes and cost. Its Handoff section names what O17 consumes.
> Next: resume the roadmap.

## Ranked list — Track B

Owner's order after Stage 2 (2026-11-16), with ranks restarted on 2026-11-18. O7 and O8
left the list as Stage 5, O12 as Stage 18 and O13 as Stage 22 (owner, 2026-11-22). O11 is
uncovered and parked in `specs/deferred_items.md`.

1. O17 — TRI protocol section. Design sessions only, after Stage 5's real build

## Ranked list — Track C

Owner's order at the resume after Stage 14 (2026-11-22). O25 left the list as Stage 20, and O26
as Stage 21 (owner, 2026-11-22).

1. O18 — USAspending protocol section. Design sessions only, after Stage 14's real build

## Ranked list — Track D

1. O19 — BEA protocol section. Design sessions only, after Stage 15's real build

## Ranked list — Track F

1. O20 — ACS protocol section. Design sessions only, after Stage 9's real build

## Ranked list — Track G

1. O21 — CPS protocol section. Design sessions only, after Stage 11's real build

## Ranked list — Track H

The order that `specs/completed/acs-wage-microdata.md` ("Roadmap placement") proposed, ranked by the
owner on 2026-11-18. O23 left the list as Stage 19 (owner, 2026-11-22).

1. O24 — ACS wage microdata protocol section. Design sessions only, after Stage 17's real build and O23

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
the gap rubric over every outcome O1–O26, with evidence for each verdict (implementing
stage and plan, `> Deviation:` notes, `specs/deferred_items.md` entries). Ranked-list
items that the owner never promoted park as deferred items. Each unmet outcome either
becomes a new stage, keeping this roadmap live, or is deferred consciously with a
written why. Then move this file to `specs/completed/`.
