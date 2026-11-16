# Reset this project's roadmap for a faster first answer

Updated 2026-11-16. This file also holds the new-evidence-sources brief that was `specs/refactor-part-1.md` (commit `685e827`). That brief is now the section [Uncovered uses](#uncovered-uses).

Owner focus:

I need NAICS evaluation data only for now: the targets that evaluate the NAICS embedder. SOC and geography targets can wait. Check these points before you rely on them:

1. Spec R7.2 names two NAICS-only target families, and both come from ITA: text–code pairs and co-ownership. Stage 10 builds both.
2. Plan 11's Stage 10 software merged into `main` as lowmason/embedding-data#11 (`118b231`). Find how much of plan 11 is finished. Find if its bundle runs on real ITA data. Do not change the merged branch `claude/vigilant-mirzakhani-bee453` or its worktree.
   - Status on 2026-11-16: Tasks 1 to 10 are merged. Task 11 Gate 1 ran: three Census NAICS index files are in `data/raw/references/naics/` and in the manifest. Gates 2 to 4 (first build, replay build, cleanup) have not run. No bundle exists under `data/derived/osha/establishment-targets/`. Plan 11 is not retired.
3. If the finished plan 11 gives my first answer, say so. Then propose "finish plan 11" as the default for question 6. Plan 11's remaining work is its owner-gated Task 11 steps.
4. Stages 4 and 6 are ticked. Find which NAICS outputs they give on real data today. Examples are the canonical NAICS code paths and the one-year ITA area-mix target.
5. Three other families also evaluate NAICS, but they need ACS or CPS work: staffing pattern, worker profile and industry job-change flows. Ask me if any of them belongs in my first answer. My default is no.
6. Branch `codex/acs-targets-design` holds Stage 9 work (ACS targets). Include it with the live plans in question 6.
   - Status on 2026-11-16: the branch merged `main` at `4a26be6` and adds `1a6377d`. It has no upstream and was never pushed. Plan 9 (`specs/plans/9-acs-targets.md`) is on `main`. The branch's worktree also has an untracked `specs/plans/10-acs-targets.md`.

## Context

- This project's roadmap came from a spec that the describe-critique-methodology skill synthesized from deep-research critiques.
- The derive-roadmap skill partitioned that spec with its gap analysis (§1). The roadmap does too much work before the owner gets a usable answer.
- derive-roadmap now has a New-Project Entry (§7). §7 stages a project by outcomes. Each track's core stage runs on real data at the smallest usable standard. Later qualities go to later stages or to a Ranked list.
- Your task has four phases. Review what is built. Find what makes the work slow. Ask the owner what comes first. Then replace the old roadmap with an outcome-first roadmap.
- The section [Uncovered uses](#uncovered-uses) holds a design task for new evidence sources. You do not do that task. Phases 1, 3 and 4 use it as input.
- On 2026-11-14 the pre-commit hooks changed (lowmason/embedding-data#10). A commit skips the `slow` tests and prose-only changes. A push runs the full suite.

## Entry override

The owner gives this instruction directly. It replaces derive-roadmap's entry order for this session only.

1. Do not resume the existing roadmap with §5. The owner asks for a new roadmap, not a reconcile.
2. Treat the owner's Phase 3 answer as the request for §7. Do not make a second offer.
3. Judge "nothing built" against the outcomes that the owner names. Do not judge it against the repository.
4. Record built pieces as inputs, under `Choices made` and in each stage's `Consumes`. Built pieces do not block §7.
5. Park an old roadmap with §5's Parking rule only after the owner approves the new partition.

Follow every other derive-roadmap rule.

## Hard limits

- Phases 1 to 3 are read-only. Write no file. Make no commit. Change no branch.
- Send no request to an external data source, for example SEC, BLS, IPUMS or OSHA. Download nothing.
- Start no cloud or GPU resource.
- Do not edit files under `~/.claude/skills/` or `~/.claude/agents/`. These files are live links to another repository. Report process causes only.
- Do not plan, spec or brainstorm a stage. Write no code. This limit includes the design task in [Uncovered uses](#uncovered-uses).
- Delete no code, data or documents. Parking moves documents. Parking deletes nothing.
- Obey this repository's CLAUDE.md. If it conflicts with this prompt, ask the owner.

## Phase 1: Inventory (read-only)

Find these items and record them:

1. Each file under `specs/` that has the roadmap header (`REQUIRED SKILL: derive-roadmap`). A repository can have more than one roadmap.
2. For each roadmap, the ticked stages with their stamp dates, and the unticked stages.
3. Each plan in `specs/plans/` that is not in `specs/plans/completed/`. Give its state: not started, partly executed, or executed but not retired.
4. Open branches, worktrees (`git worktree list`), open PRs (`gh pr list`) and uncommitted changes.
5. The unticked entries in `specs/deferred_items.md`.
6. What works today. For each piece, state if it runs end to end on real data. Name the artifact that it makes: a path, a table or a figure.
   - Code that passes tests only on fixtures does not count as working.
   - Code that only downloads inputs does not count as an outcome.
7. Real data on disk that a new stage can use. Give the path, the size or row count, and the date range. Use a file listing or a cheap read. Do not run a pipeline.
8. A sibling repository under `~/Projects/` for the same system. Name it if it exists.
9. For each of the six uses in [Decision 2](#decisions), check its "Nearest existing coverage" against item 6. Record which coverage works on real data today.

## Phase 2: Diagnosis (read-only)

Find what makes the work slow. Count each measure from git and from the files. Do not estimate a measure that you can count. Count git-tracked files only (`git ls-files`).

- Calendar: the first commit date, the date of each stage stamp, the days for each stage, and ticked stages against all stages.
- Effort mix: commits by Conventional Commit type. Compare `docs(specs)`, `docs(plans)` and `docs(evidence)` with `feat`, `fix` and `test`.
- Size: Markdown lines under `specs/` against non-test source lines. Test lines against source lines.
- Rework: resume passes that added no stamp, inserted sub-stages (for example 1a or 2a1), plans that no session executed, and superseded plans.
- Process: review rounds, fix commits after a review, and evidence records for each plan.
- Order: the number of stages before the first stage that answers an owner question. Quote the reason for this order from the roadmap.
- Early qualities: Exit criteria before the first answer that need a final-standard quality. Examples are provenance, `observable_at` or point-in-time keys, manifests, hash-bound evidence, full validation suites, deployment and scheduling.
- Detours: infrastructure or environment work that no outcome needs.
- External limits: rate limits, data access and compute. Use only measured or published figures.

Put each cause in one of these three groups:

- Scope: the breadth of the spec, early qualities, and a stage order that follows the method's structure, not the owner's value.
- Process: the cost that the shared workflow skills add to each stage.
- External: limits outside the project.

Report the 3 to 5 largest causes. Give each cause its numbers and its file references. Keep the review short. The goal is a decision, not a report.

## Phase 3: One message to the owner, then stop

Send one message with these four parts:

1. What works today. Use a table with the columns Piece, Works on real data (yes or no), Artifact and Evidence.
2. The causes from Phase 2, largest first.
3. Candidate outcomes, unranked.
   - Write one line for each outcome. Say what the owner gets, not how it is built.
   - Take the candidates from the spec, the unticked stages and the owner focus line.
   - Include each of the six uses in [Decision 2](#decisions) as a candidate.
   - Mark each candidate with its source file.
   - Give a rough cost and its basis when the cost is material.
4. These questions. Give a proposed default for each question, so that the owner can answer "defaults, except …".
   1. What is the first question that you want answered? If the owner focus line has text, restate it. Ask the owner to confirm it or change it.
   2. What is the smallest standard that makes that answer usable? Examples are a subset of series, one period, or a descriptive estimate before a full model.
   3. What is your target for the first answer, in sessions or in days?
   4. Which built pieces do you keep as inputs?
   5. For each roadmap: park it (the default) or keep it live? Say how many deferred items parking adds.
   6. For each live plan: finish it, retire it as superseded, or keep it? The writing-plans Plan Completion Protocol covers executed plans only. For a plan that is not executed, propose a disposition. A plan that the owner finishes or keeps needs a home. Propose one: a stage of the new roadmap, or a note in the new roadmap that the plan stays outside any roadmap.
   7. Which process do you want for the first stage: the current process or a lighter process? Name the steps that a lighter process skips.
   8. If a sibling repository exists, which repository continues the work?
   9. Do any of the six uncovered uses belong in the new roadmap? If yes, confirm or change each default in [Defaults to flag](#defaults-to-flag). Propose that section's recommended default for each.

Stop after this message. Wait for the owner's answer. Do not start Phase 4 without it.

## Phase 4: The new roadmap

Do these steps after the owner answers:

1. If the current branch is the default branch, create a branch before the first write.
2. Run derive-roadmap §7 with the entry override, up to its one message.
   - `Source` is the owner's words, with the date.
   - Give the new roadmap a new kebab-case name. Do not use the old roadmap's filename.
   - §7's message gives the outcomes, the tracks, the cost notes, the proposed name and a request to rank. If the owner ranked in Phase 3, show that ranking and ask for a confirmation.
3. After the owner confirms the name, save the Phase 1 table and the Phase 2 causes as `specs/findings/<new-name>-reset-review.md`. Keep this file to one screen.
4. Write the roadmap with §7's remaining steps.
   - `Background` lists the old spec, its methodology and critique files, the old roadmap and the reset review. Background gives facts and costs. Background adds no outcome.
   - Put each early quality from Phase 2 in the core stage's `Leaves out`. Exception: a quality that the owner asked for in the first answer.
   - Record the owner's process choice for the first stage as one line under `Choices made`.
5. If the owner put an uncovered use in the new roadmap, give that use a stage.
   - The stage cites [Decision 2](#decisions) as its source.
   - Its first step is a brainstorming session. That session receives [Handoff for the design stage](#handoff-for-the-design-stage).
   - Record the owner's Phase 3 answers on the three defaults in the stage.
   - Do not brainstorm the stage in this session.
6. Present the partition for approval, per derive-roadmap §4.
7. After the approval, apply the owner's Phase 3 answers:
   - Park each roadmap that the owner chose to park, per derive-roadmap §5 Parking. Parking moves the old roadmap, spec, methodology and critique files to `specs/completed/`.
   - Apply the owner's disposition to each live plan.
8. Update each link to a moved file. Read the new roadmap's `Background` line and the reset review. Each link must resolve to the file's new path.
9. Commit the reset review, the new roadmap, the parked files and the plan changes on the branch.
10. End with derive-roadmap's "Next:" line for Stage 1. Under it, add one line for the receiver to carry: `Process: <the owner's process choice for Stage 1>`. Then stop.

## Uncovered uses

This section was `specs/refactor-part-1.md` (commit `685e827`). The owner had that file deleted on 2026-11-16, after its text moved here. The original brief is also at `~/.cache/agent-skills/handoffs/embedding-data/2026-11-14-uncovered-graph-uses.md`. It holds a design task for new evidence sources. The reset session uses this section as input only.

Line numbers below refer to `specs/embedding-evaluation-data-spec.md` at commit `147802f`. Read that version with `git show 147802f:specs/embedding-evaluation-data-spec.md`. On `main`, Stage 10 added 3 lines to R2.6, in lines 223 to 231. So each cited line after 231 is 3 lines lower on `main`.

### Decisions

**Decision 1 (context only, recorded elsewhere).**

- *You said (2026-11-14, in a naics-embedder session):* "go with one blended space". This chose between two offered options, one blended space or one view per relation. The chosen option was described as: "You get one table and one cosine, easy to publish and use. Each use gets distances partly shaped by relations it doesn't care about. It can be judged with the data you have: train on some edge families, and judge on the families held out." The owner was asked next whether one source could train and another judge, or one source be split at random. The owner said: "Agreed with different families, falling back to one split."
- *Reading:* naics-embedder's "type 1" artifact is one industry-relatedness embedding over the 2,125 NAICS 2022 codes. It trains on NAICS tree edges plus some embedding-data families. It is judged on whole families held out from its training, chosen from a different source where possible. Where no other family can judge, one family is split, part training and part judging.
- *Home:* naics-embedder's revised representation-split spec, being brainstormed there.
- *Approval:* there. Record nothing for it here. Its conflict with R8.4 is under [Leave alone](#leave-alone).

**Decision 2.**

- *You said (2026-11-14):* "for now, disregard graph embedding uses for which ~/Projects/embedding-data have no coverage--but for those uses (firm-level data, input-output tables), provide a blurb I can use with brainstorming in that repo." The uses come from the owner's list of what type 1 is for. The owner's words are in quotes. The other columns are the sender's reading.

  | Use | Data it needs | Nearest existing coverage |
  |---|---|---|
  | KYB and anomaly detection: "Comparing a company's self-reported NAICS code against the embedding of its transaction network or vendor graph" | firm-to-firm transactions or vendor links | none |
  | Peer and competitor detection: "often combined with subsidiary ownership graphs" | links between a parent and its subsidiaries, across EINs | partial: R7.2 co-ownership (line 521) covers the industries one EIN operates together, not parent-subsidiary links |
  | Holding-company classification: "aggregating the graph embeddings of its child entities" | the same ownership links, with each subsidiary's NAICS | partial: same |
  | Supply-chain dependency: "NAICS codes are connected via input-output tables or B2B transaction graphs" | directed industry-to-industry flows of goods, services or payments | worker flows only: R7.2 job-change flows, industry → industry (line 517) |
  | Look-alike prospecting: "embed customer industry graphs" | firm-to-customer-industry links | none |
  | Co-visitation and foot traffic: "predict which types of businesses people visit sequentially" | visit sequences between establishment types | partial: R7.2 area mix gives co-location, not visits |

  Asked whether the partly covered uses (peer, holding-company, co-visitation) are in scope, the owner answered "All six."
- *Reading:* the design task looks for sources of the missing data for all six uses. Whether naics-embedder's type 1 ignores these uses meanwhile is recorded in naics-embedder, not here.
- *Home:* the new design spec's intent and scope section: the uses and the data each lacks.
- *Approval:* the owner's review of that spec.

### Defaults to flag

The reset session asks these in Phase 3 question 9. The design stage asks again only about a default that the owner did not answer. Do not proceed on them silently.

1. **Free data only?** R1.2 (line 117) and lines 14-16: "Every input is free to access ... no paid data". Commercial transaction graphs and foot-traffic panels are usually paid.
   - *Recommended default:* keep free-only. If no free source covers a use, record the use as uncovered, with the sources considered and why each fails. That is an acceptable result.
   - *Effect if wrong:* the uses that need paid data stay uncovered, or the project takes on licensing terms it was built to avoid.
2. **New spec, or an amendment of this one?** The spec fixes the source count at three (lines 9, 91, 106, 117, and `CLAUDE.md:7`). Its header routes it to derive-roadmap (lines 3-4).
   - *Recommended default:* a new spec under `specs/` that states how it amends R1.1 and the other three-source lines. Commit it through the repository's usual workflow.
   - *Effect if wrong:* two specs disagree on the source list, or the approved spec is rewritten under a brainstorm.
3. **Published aggregates.** Input-output tables are published aggregates with no records, standard errors or unweighted counts. The Core principle says targets are "computed from records in the three sources" (lines 90-91). R7.1 (line 506) requires a standard error and counts. R7.3 (line 525) requires an unweighted count.
   - *Recommended default:* admit published aggregates under a stated exception. Name and flag the missing fields. Do not fill them.
   - *Effect if wrong:* input-output data are excluded without a decision, or the evidence contract weakens for every family.

### Constraints and traps

- **Direction:** R7.2 writes its flows as a → b (lines 517-519). R7.4's schema (line 529) has `unit_a` and `unit_b`, but it states no direction convention. The approved Stage 10 spec emits co-ownership as a directional share in both directions. Store new flows directed.
- **Observed, never assumed** (lines 90-91): no target is derived from code structure. A new family must meet this rule.
- **Rejected sources** (lines 636-651): do not propose one again without a new reason. The spec notes the H-1B LCA and PERM files (line 650) as candidates for a later mixed-depth extension.
- **Ownership crosses EINs.** R7.2's co-ownership is within one EIN (line 521). A company-name fallback does not establish it (lines 247-248). A parent-subsidiary source links different EINs, which that family cannot hold. Stage 10's software defines the family and merged in lowmason/embedding-data#11, but its bundle is not built yet. Whether an ownership source joins that family or becomes a new family is the owner's question, after Stage 10 ships.
- **Codes:** a new source must reach NAICS 2022 through R5 (line 448). Input-output tables from BEA (the Bureau of Economic Analysis) use BEA industry codes. These codes are coarser than six-digit NAICS and use an older NAICS basis. This lead is unverified: check BEA's current benchmark tables and their NAICS concordance.
- **Licensing:** the repository is public (`lowmason/embedding-data`). Derived data stay in the gitignored `data/`. Code, specs and committed test fixtures are public, and R9.2 (lines 567-568) makes every test run from fixtures. A new source's terms must allow aggregates to leave the machine (R8.1, line 539). Its fixtures must be redistributable or synthetic. R8.3 (line 547) shows that "every output is an aggregate" is not universal.
- **Shared spec edits:** Stage 10 amended R2.6 in the source spec (lines 223-231 on `main`). Keep the design spec's edits away from R2.6.

### Owner gates

- The design stage downloads nothing and signs up for no account. It may read a source's public documentation pages. It asks the owner before it fetches any file, including a concordance.
- The spec's own gates: Rollout (line 655) and Verification (line 570).

### Leave alone

- **R8.4 and its restatements:** R8.4 (lines 550-554). On `main` at `118b231`: `CLAUDE.md:231`, `:335` and `:368`, `README.md:423-424`, `:775`, `:954` and `:1046`, `specs/evaluation-targets-methodology.md:64-67` and `:222-224`, and the Stage 10 spec's anti-goal (`specs/ita-establishment-targets.md:124`). Decision 1 needs some families to train type 1, and its fallback splits one family between training and judging. R8.4 as written forbids the first. The roadmap gives tuning splits to the successor evaluation-protocol spec (`specs/embedding-evaluation-data-spec-roadmap.md:128`). That amendment is a separate owner decision, after naics-embedder's spec proposes which families train. Specify new families as evaluation targets under R8.4 as written, and note that their role may change.
- **naics-embedder:** read its specs if useful. Edit nothing.
- **Other branches:** `codex/acs-targets-design` (Stage 9 ACS targets) and the merged Stage 10 branch `claude/vigilant-mirzakhani-bee453`. Edit neither. Read the approved Stage 10 spec at `specs/ita-establishment-targets.md` on `main`.
- **Existing R7.2 families:** do not change their definitions.

### Handoff for the design stage

Use the brainstorming skill in `~/Projects/embedding-data` on new evidence sources. Read `specs/embedding-evaluation-data-spec.md` at `147802f` first. Produce a design, sized by brainstorming, for sources that would supply the data missing for the uses in [Decision 2](#decisions). Apply this section's defaults, constraints, gates and leave-alone list. Record Decision 2 in its Home. Do not record Decision 1, because the naics-embedder session records it. Stop at the owner-approved, committed spec. Do not plan, download data or build.
