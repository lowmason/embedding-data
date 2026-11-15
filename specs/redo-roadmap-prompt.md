# Reset this project's roadmap for a faster first answer

Owner focus:

I need NAICS evaluation data only for now: the targets that evaluate the NAICS embedder. SOC and geography targets can wait. Check these points before you rely on them:

1. Spec R7.2 names two NAICS-only target families, and both come from ITA: text–code pairs and co-ownership. Stage 10 builds both.
2. Branch `claude/vigilant-mirzakhani-bee453` holds Stage 10 work from plan 11, about 29 commits ahead of `main`. Find how much of plan 11 it finished. Find if its bundle runs on real ITA data. Do not change that branch or its worktree.
3. If the finished plan 11 gives my first answer, say so. Then propose "finish plan 11" as the default for question 6.
4. Stages 4 and 6 are ticked. Find which NAICS outputs they give on real data today. Examples are the canonical NAICS code paths and the one-year ITA area-mix target.
5. Three other families also evaluate NAICS, but they need ACS or CPS work: staffing pattern, worker profile and industry job-change flows. Ask me if any of them belongs in my first answer. My default is no.
6. Branch `codex/acs-targets-design` holds Stage 9 work (ACS targets). Include it with the live plans in question 6.

## Context

- This project's roadmap came from a spec that the describe-critique-methodology skill synthesized from deep-research critiques.
- The derive-roadmap skill partitioned that spec with its gap analysis (§1). The roadmap does too much work before the owner gets a usable answer.
- derive-roadmap now has a New-Project Entry (§7). §7 stages a project by outcomes. Each track's core stage runs on real data at the smallest usable standard. Later qualities go to later stages or to a Ranked list.
- Your task has four phases. Review what is built. Find what makes the work slow. Ask the owner what comes first. Then replace the old roadmap with an outcome-first roadmap.

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
- Do not plan, spec or brainstorm a stage. Write no code.
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
5. Present the partition for approval, per derive-roadmap §4.
6. After the approval, apply the owner's Phase 3 answers:
   - Park each roadmap that the owner chose to park, per derive-roadmap §5 Parking. Parking moves the old roadmap, spec, methodology and critique files to `specs/completed/`.
   - Apply the owner's disposition to each live plan.
7. Update each link to a moved file. Read the new roadmap's `Background` line and the reset review. Each link must resolve to the file's new path.
8. Commit the reset review, the new roadmap, the parked files and the plan changes on the branch.
9. End with derive-roadmap's "Next:" line for Stage 1. Under it, add one line for the receiver to carry: `Process: <the owner's process choice for Stage 1>`. Then stop.
