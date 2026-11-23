# Evaluation protocol: ITA co-ownership and the 2023 ITA area mix

Status: PROPOSED (2026-11-23). Written in a brainstorming session. A builder check raised three
points. One was the owner's to rule (P7). The other two are folded in as my calls: CO3 and AM3
are scoped to the relatedness artifact, and the Handoff notes that Stage 23 has no consuming
spec yet. The owner has not yet approved the committed design.

Roadmap: `specs/naics-evaluation-data-roadmap.md`, Stage 16 (Track E, O14). The design adds
Sections 2 and 3 to [the evaluation protocol](evaluation-protocol.md). This file holds their
provenance, the owner's decisions and the pointer edits. The protocol file holds the rules.

## Design provenance

A brainstorming session with the owner on 2026-11-23. The inputs read were:

- in this repository at `f6b339f`: the roadmap's Stage 16 entry and "Choices made";
  `specs/evaluation-protocol.md` (approved 2026-11-18); the Stage 10 finding
  `specs/findings/stage-10-ita-establishment-targets.md`; the Stage 6 finding
  `specs/findings/stage-6-ita-area-mix-build.md`; the V9 decision
  `specs/findings/v9-ita-naics-minimum-counts.md`; methodology K5 and K6 in
  `specs/evaluation-targets-methodology.md`; the retired Stage 10 spec
  `specs/completed/ita-establishment-targets.md` (amendment, Out of scope, co-ownership target,
  Handoff); the retired Stage 6 spec `specs/completed/target-contract-ita-area-mix.md`; R8.4 of
  `specs/embedding-evaluation-data-spec.md`; the "Leave alone" section of
  `specs/redo-roadmap-prompt.md`;
- in naics-embedder (`~/Projects/naics-embedder`) at `2b2029c`: the completed relatedness spec
  `specs/completed/relatedness-artifact.md` (last changed at `35697db`), its §7 requests to this
  repository, its split code `src/naics_embedder/panels/relatedness_split.py`, its split settings
  `conf/data/relatedness_panel.yaml`, and gates G1, G4 and G6 of
  `specs/naics-artifact-redesign-roadmap.md`.

Two read-only measurements were made on the selected runs. Neither reads an embedder output.

1. The SHA-256 of each detached `outputs.json` and of each table named in the Evidence tables was
   recomputed from the bytes on disk. Each equals the inventory value.
2. The split of co-owned pairs under naics-embedder's committed salt and rule (see
   "Measured split" below).

**Owner decisions (2026-11-23).** The ids continue from the protocol's P1–P3.

| Id | Question | Decision |
| --- | --- | --- |
| P4 | naics-embedder's relatedness spec asks for G6 (selection may read co-ownership's validation part) and G1 (R8.4 amended so that the area mix may train). Which does Stage 16 carry? | "G6 in, G1 out" |
| P5 | Splitting by anchor industry puts 50.3% of co-owned pairs in both parts, one end in each. What does the co-ownership section require? | "Report it beside": the headline stays as naics-embedder designed it. Every sealed score also states the crossing share and a sealed score restricted to pairs with both industries sealed, labeled as a sensitivity |
| P6 | How is it written? | "Approach 1": two thin sections in the protocol, with the design history in this file, applied in this session in one docs-only PR |
| P7 | The retired Stage 10 spec says "Co-ownership and the link table keep the full exclusion", and naics-embedder reads G6 from that line. Does it get a dated pointer amendment, as G2's exception did? | "Add pointer" |

**My calls.** Choices made while writing, which the owner has not ruled on, are marked (my call).

## Intent

naics-embedder's relatedness artifact is one embedding of the NAICS 2022 codes. It is judged on
ITA co-ownership and trains on the NAICS tree and the 2023 ITA area mix (relatedness spec, U42).
Its Stages 6b and 7 are held on two of this repository's gates:

- **G4.** No protocol section exists for co-ownership or the area mix.
- **G6.** The Stage 10 amendment of 2026-11-18 allows selection on the text–code pairs only. It
  says: "Co-ownership and the link table keep the full exclusion."

Its relatedness spec (§7) asks this repository for both sections and for G6. It also asks for G1,
the R8.4 decision that lets the area mix train.

Stages 23 and 25 of this roadmap consume the co-ownership section as the model for a directional
relatedness share (USAspending and TRI). So the section must answer the open questions for that
shape: null-model normalization and the choice of scores ("Families with no section").

**Success.** A naics-embedder roadmap resume can cite the protocol at a commit on `main` and record
G4 as open for co-ownership and the area mix, and G6 as open. G1 stays closed.

## Goals, non-goals and anti-goals

**Goals.**

1. Assign the split, the null model and the scoring of co-ownership to naics-embedder's
   relatedness spec.
2. Let selection read co-ownership's validation part, under stated limits (G6, P4).
3. State the area mix's one role: it trains relatedness once R8.4 allows it, and it never judges or
   selects.
4. Name the run, the pin and the table hashes that each read uses.
5. Answer by name each place where the Stage 10 spec defers co-ownership to the protocol.

**Non-goals.**

- A scoring method, a metric, a null model, a margin or a reference. These are the relatedness
  spec's.
- Any change to R8.4's text. G1 is a separate owner decision (P4; roadmap, "Leave alone").
- Sections for TRI, USAspending, ACS, CPS or the ACS wage microdata, or their roles.
- Any code, test or data change.

**Anti-goals.** The design fails, even if it merges, when it:

- restates the relatedness spec's rules, so that two repositories hold copies;
- lets a co-ownership row, or a quantity derived from one, train an embedder;
- lets the area mix judge or select, or train before R8.4 allows it;
- hides that the sealed read shares pairs with the validation part;
- weakens a limit of the Stage 10 amendment of 2026-11-18 for the text–code pairs.

## Approaches

| Approach | What it does | Trade-off | Decision |
| --- | --- | --- | --- |
| 1. Thin delegation, history apart | Sections 2 and 3 in the protocol assign split and scoring to the relatedness spec and keep the read conditions. Provenance and decisions live in this file. | Each rule has one home. The shared protocol file stays short for Stages 23 to 25. A reader needs this file only for the why. | **Chosen** (P6) |
| 2. Thin delegation, history in the protocol | The same sections, with provenance and decisions inside the protocol file, as Section 1 did. | One file, but it doubles in size and gives later stages a long file to merge into. | Rejected |
| 3. Restate the relatedness rules | Copy the anchor split, the NDCG@10 headline and the lift gain into this repository. | Self-contained, but the copies drift. Section 1 rejected the same approach. | Rejected |

## Design

The rules are Sections 2 and 3 of [the evaluation protocol](evaluation-protocol.md). They follow
Section 1's frame: Evidence, Assignment, Conditions, and what this repository does not decide.
The points below are the design choices behind them.

### Evidence

- **The first runs.** Co-ownership reads `stage10_ita_establishment_20261116_r1`, the run that
  Section 1 reads (my call). The area mix reads `stage6_ita_area_mix_20261014_1000_csv`, the first
  build (my call). In both replays, a Parquet file has equal values but different bytes, so one
  run must be named. The V9 decision and the relatedness spec also name these two runs.
- **Only the tables a read uses.** Co-ownership pins `ita_co_ownership.parquet` and
  `co_ownership_marginals.parquet`, the two tables that the relatedness spec reads (§4.2). The area
  mix pins `ita_area_mix.parquet` only (relatedness spec §5). A read of another table of either
  bundle needs an amendment that adds its hash (my call).
- **Counties with eligible records.** The relatedness spec's C counts them. In the selected run,
  they are the 3,065 counties with a cell. `county_denominators.parquet` has 3,069 rows, and four
  of them have no eligible record (Stage 6 finding). So C needs no second table (my call).

### Measured split

naics-embedder's rule puts a six-digit code in the validation part when the first 8 bytes of
SHA-256(`salt` + NUL + `code`), as a big-endian integer, are even. The committed salt is
`4bfd5195916df66d0e1c619c6507f2ad` (`conf/data/relatedness_panel.yaml` at `2b2029c`). Applied to
`ita_co_ownership.parquet` of the selected run on 2026-11-23:

| Count | Value |
| --- | ---: |
| Industries in a target row | 909 (440 validation, 469 sealed) |
| Industries with a marginal row | 991 |
| Unordered co-owned pairs | 19,576 |
| Both industries in validation | 4,575 |
| Both industries in sealed | 5,159 |
| One industry in each part | 9,842 (50.3%) |

Of the 20,160 directed rows whose anchor is sealed, 9,842 (48.8%) have a mirror row whose anchor
is in validation. Cosine similarity is symmetric, so selection on validation can lift the sealed
score on those pairs. The relatedness spec accepted the mirror pairs because co-ownership never
trains (§4.3). G6 now lets co-ownership select, so the owner required a sensitivity report (P5).
These counts depend on the salt and the run. They describe the evidence and set no rule.

### Assignment

- **Co-ownership** goes to the relatedness spec as its owner amends it, not to a frozen copy, as in
  Section 1 (my call). The version read is naics-embedder `2b2029c`. The conditions bind every
  version.
- **The shape questions.** Null-model normalization (K6-Q1) and the choice of scores are assigned,
  not answered. At `2b2029c` the relatedness spec answers them with the gain J(a,b)/m(b) and a mean
  NDCG@10 headline. A later directional relatedness share can copy this shape (Handoff).
- **The area mix** has no split and no scoring. Its section assigns its use in training (edges,
  weights, thresholds) to the relatedness spec, and states that it never judges or selects.

### Conditions

The conditions repeat a relatedness-spec rule only where it is this repository's own limit (my
call, as in Section 1):

- what counts as headline evidence (the unpadded J; every published cell);
- the roles under R8.4 (G6's limits; the area mix's wait for G1);
- the universe statement;
- the mirror-pair report (P5).

Condition ids carry a family prefix: CO1 to CO8 for co-ownership and AM1 to AM6 for the area mix.
Section 1's C1 to C6 keep their ids (my call). The prefixes keep a citation such as "C1" from
naming two conditions.

**Same relation, no self-judging** (CO7, AM4; my call). A family that measures the same relation as
the judge must not train what that judge scores. The TRI spec states this for TRI parent links and
co-ownership (`specs/completed/tri-parent-links.md`, lines 705–706). The relatedness spec states it
for the ACS workplace area mix and the ITA area mix (§4.1). The two conditions state the rule
generally. Which later families measure the same relation is left to their own sections. This
section assigns no role to TRI, USAspending or ACS.

## Edits

### Edits to the protocol file in this design commit

1. Add Section 2 (co-ownership) and Section 3 (area mix) after Section 1, each with
   `Status: PROPOSED`.
2. Under "Design provenance", add one line: that provenance, Intent, Goals, Approaches and "Edits
   on approval" are Section 1's, and Sections 2 and 3 have theirs in this file.
3. In the introduction, replace "No other family has a section yet" with a sentence that names
   Sections 2 and 3.
4. In Section 1's Assignment, replace "For co-ownership, those questions stay open (Families with
   no section)" with a pointer to Section 2.
5. In "Families with no section", remove co-ownership and the area mix. Say that Section 2 answers
   the shape questions by assignment.
6. In the Handoff, say that G4 opens for co-ownership and the area mix with Sections 2 and 3, that
   G6 opens with CO3, and that G1 stays closed.

### Edits on approval

One docs commit applies these. Each edit is a pointer or a status, not a rule change.

1. **Protocol, Sections 2 and 3.** Change both statuses to "APPROVED (date, owner)".
2. **This file.** Change Status to "APPROVED (date, owner)".
3. **Source spec**, the introduction (line 17) and Out of scope, "Evaluation protocol"
   (line 686): add that Sections 2 and 3 cover co-ownership and the 2023 area mix.
4. **`CLAUDE.md`**, Stage 10 paragraph: add that selection for naics-embedder's relatedness
   artifact may also read co-ownership's validation part, and that reads of co-ownership follow
   Section 2. Stage 6 paragraph: add that reads of the
   2023 area mix follow Section 3, which allows training only after R8.4 is amended.
5. **`README.md`**, the Stage 10 and Stage 6 sections: the same two sentences.
6. **`specs/deliverable-map.md`**, the co-ownership and area-mix rows: replace "Role not assigned"
   and the pending protocol cell with the assigned roles and a pointer to Sections 2 and 3.
7. **`specs/naics-evaluation-data-stage-16-findings.md`**: a new one-screen file. It records the
   stage's cost in sessions, the two measurements and what is not claimed.
8. **Roadmap**: tick Stage 16 and add its COMPLETE stamp, as Stage 22's PR did (my call).
9. **Retired Stage 10 spec** `specs/completed/ita-establishment-targets.md`, after its amendment
   block (lines 11–27): one dated pointer line (P7). Section 2 of the protocol extends the
   selection exception to co-ownership's validation part, for naics-embedder's relatedness
   artifact only. The link table keeps the full exclusion. The amendment of 2026-11-18 is not
   reworded. G2's exception, written into the same retired spec (`e03ec67`), is the precedent.

Findings and retired plans are records and are not edited. The retired Stage 10 spec gets only
the pointer of edit 9. R8.4's text is unchanged.

## Constraints

- No source file, test or data file changes. Every software hash recorded by a selected run stays
  as recorded.
- The commit hooks skip the test suites for changes under `specs/` and root-level Markdown. No
  flag is used to skip a hook.
- R8.4's text is unchanged (P4).
- Stages 23, 24 and 25 also edit `specs/evaluation-protocol.md`. Keep the edits outside Sections 2
  and 3 small and local. If another stage's section merges first, renumber at the merge and keep
  this design's content (my call).

## Verification: observable outcomes

- [ ] The protocol file on `main` has Sections 2 and 3, each with Status APPROVED.
- [ ] Each Evidence value equals the selected run's `outputs.json`, and the SHA-256 of each
      `outputs.json` equals its pin.
- [ ] The split counts equal a recount with the salt at naics-embedder `2b2029c`.
- [ ] A reader can answer from the protocol alone: who decides co-ownership's split, null model and
      scores; which part selects and which judges; what the area mix may do and when; which run,
      pin and tables to read; which families are still unscored.
- [ ] "Families with no section" no longer lists co-ownership or the area mix.
- [ ] `CLAUDE.md`, `README.md`, the source spec and the deliverable map point to Sections 2 and 3.
- [ ] The retired Stage 10 spec's only change is the dated pointer of edit 9.
- [ ] R8.4's text is unchanged.
- [ ] `git diff --stat` for the change lists only Markdown files.
- [ ] Stage 16 is ticked in the roadmap, and the findings file exists.

## Left to the builder

- The exact wording of the pointer sentences, within the limits above.

## Handoff

- **naics-embedder.** A roadmap resume re-reads G4 and G6 at one commit of this repository. G4
  opens for co-ownership (judging and selection) and for the area mix (role stated). G6 opens under
  CO3 and CO4. G1 stays closed, so Stage 7's training on the area mix stays held. CO4 asks the
  relatedness spec for one new report beside its headline. Its decision rule is unchanged.
- **Stages 23 and 25.** Section 2 is their model. They assign the null model and the scores to the
  consuming spec, name their run, pin and tables, and keep CO-style conditions. Each says whether
  its family measures the same relation as co-ownership (CO7). A family split by anchor industry
  measures its own crossing share, as here. The assignment needs a consuming spec. At `2b2029c`
  the relatedness spec lets TRI join as a second judge (§4.1), but lists USAspending subawards as
  unassigned. So Stage 23 finds no consuming spec yet. That is Stage 23's to resolve, not this
  stage's (builder check).
- **Stage 24.** It adds its own section. If it merges first, renumber at the merge.
- **R8.4 (G1).** A separate owner decision. The relatedness spec has now named the area mix as the
  one family that trains, so the decision can be made.

## Rollout note

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 16 — on plan completion, tick the stage and re-validate later stages against what shipped.

No plan is needed, because the design adds no code (my call, as for Section 1). The edits on
approval stand in for the plan, and the PR that applies them completes the stage.
