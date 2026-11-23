# Evaluation protocol, Section 5: USAspending vendor links

Status: PROPOSED (2026-11-23). Written in a brainstorming session. The section text is Section 5
of [the evaluation protocol](evaluation-protocol.md), with its own Status PROPOSED.

Roadmap: `specs/naics-evaluation-data-roadmap.md`, Stage 23 (Track C, O18). The design adds
Section 5 to [the evaluation protocol](evaluation-protocol.md). This file holds its provenance,
the owner's decision, the measurements and the pointer edits. The protocol file holds the rules.

## Design provenance

A brainstorming session with the owner on 2026-11-23. The inputs read were:

- in this repository at `32f3ccf`: the roadmap's Stage 23 entry and its "Choices made";
  `specs/evaluation-protocol.md` (Rules for every family, Sections 1 to 4, "Families with no
  section", "What this repository does not decide"); the Stage 16 spec
  `specs/completed/evaluation-protocol-ita-relatedness.md` and its findings; the Stage 24 spec
  `specs/completed/acs-wage-protocol-section.md`; the
  [V9 USAspending decision](findings/v9-usaspending-minimum-counts.md); the Stage 20 acceptance
  finding `specs/findings/stage-14-usaspending-vendor-links.md`;
  `specs/naics-evaluation-data-stage-14-findings.md` ("E6 status", "For the resume and O18");
  the Stage 14 spec `specs/completed/usaspending-vendor-links.md` (Intent, estimand, Limits,
  source spec amendment); "Rules for every new family" of
  `specs/uncovered-uses-evidence-sources.md`; `specs/deferred_items.md` (sections
  `15-usaspending-vendor-links`, `16-usaspending-vendor-links` and
  `19-usaspending-minimum-counts`);
- in naics-embedder (`~/Projects/naics-embedder`) at `2b2029c`: the completed relatedness spec
  `specs/completed/relatedness-artifact.md` (§4.1, the role list, which names USAspending
  subawards as unassigned) and its split settings `conf/data/relatedness_panel.yaml`.

naics-embedder has no spec that assigns this family at `2b2029c`. The roadmap resume of
2026-11-23 ruled that Stage 23 does not consume one: the section names the relatedness spec as
the place that assigns and scores the family, and the family stays unscored until the owner
names that spec at a commit.

**Owner decision (2026-11-23).** The id continues from P4–P7 of the Stage 16 spec.

| Id | Question | Decision |
| --- | --- | --- |
| P8 | Which roles does the section grant: judge only, or judge and select (as co-ownership's CO3)? | "Judge only". No part of the family selects. The R8.4 exclusion stays whole |

The owner also confirmed the approach: one thin section in the protocol, with the design
history in this file ("Yes, write it").

**My calls.** Choices made while writing, which the owner has not ruled on, are marked (my call).

## Intent

naics-embedder's relatedness artifact is one embedding of the NAICS 2022 codes. Co-ownership
judges it today, and TRI parent links may join as a second judge. The vendor links are a third
kind of evidence: two industries are close in practice when firms in one often sell to firms in
the other through federal subcontracts (Stage 14 spec, Intent).

The protocol says a family with no section is not scored (Rule 1). The Stage 14 spec's Limits
leave one question to this section: which families may judge one another. The V9 decision leaves
scoring, null models, splits and absent (zero) cells to it.

No consumer has assigned the family yet. So the section does two things now: it fixes the
evidence, the role and the conditions, and it states that no read is allowed until the owner
names the consuming spec in it. This is the shape of Section 2's W7.

**Success.** A later amendment can name naics-embedder's spec at a commit, and nothing else in
the section must change for a read to begin.

## Goals, non-goals and anti-goals

**Goals.**

1. State the family's one role: it judges and never selects or trains (P8).
2. Assign the split, the null model, the scores and the treatment of absent and diagonal cells
   to naics-embedder's relatedness spec, once the owner names it here.
3. Name the run, the pin, the two table hashes and the two count gates that a read uses.
4. State which families measure the same relation (CO7, AM4).

**Non-goals.**

- A scoring method, a metric, a null model, a margin or a reference.
- An amendment of naics-embedder's relatedness spec. That repository assigns its own roles.
- Any change to R8.4's text.
- A changed D2 rule or the live `acquire-sam-extract` request (`specs/deferred_items.md`).
- Any code, test or data change.

**Anti-goals.** The design fails, even if it merges, when it:

- lets any part of the family select a model, checkpoint, configuration or candidate;
- lets a row, or a quantity derived from one, train an embedder;
- lets a read begin before the owner names the consuming spec;
- restates a rule that the consuming spec owns, so that two repositories hold copies;
- lets `vendor_link_pairs.parquet`, which holds UEI pairs, leave this machine or enter a read.

## Approaches

| Approach | What it does | Trade-off | Decision |
| --- | --- | --- | --- |
| 1. Thin section, history apart | Section 5 in the protocol holds Evidence, Assignment and Conditions. Provenance and the decision live in this file. | Each rule has one home. The shared protocol file stays short while Stage 25 edits it too. | **Chosen** (owner, "Yes, write it") |
| 2. Thin section, history in the protocol | The same section, with provenance inside the protocol file, as Section 1 did. | One file, but longer, and the Stage 16 owner decision P6 rejected it for the same reason. | Rejected |
| 3. Wait for a consumer | Write nothing until naics-embedder assigns the family. | No placeholder rules, but the stage's Exit asks for the section now, and the roadmap resume ruled that the consuming spec is not a Consumes. | Rejected |

For the roles, the owner weighed judge only against a CO3-style grant, in which the validation
part selects for the relatedness artifact. Judge only keeps the R8.4 exclusion whole, matches the
relatedness spec's rule that selection reads co-ownership's validation part only (§4.1, from
U43), and grants
nothing that no consumer has asked for. A later amendment can add a grant. A grant cannot be
taken back after a read has used it.

## Design

The rules are Section 5 of [the evaluation protocol](evaluation-protocol.md). It follows Section
3's frame: Evidence, Assignment, Conditions, and what this repository does not decide. The points
below are the design choices behind it.

### Evidence

- **The first run.** A read uses `stage14_vendor_links_20261122_r2` (my call). Unlike Sections 3
  and 4, its four Parquets and `report.json` have the same bytes as the replay's. The reason to
  name it is that the V9 decision and the independent reconciler read it.
- **Two tables.** The section pins `vendor_links.parquet` (the targets) and
  `vendor_link_marginals.parquet` (`n_suppliers`, `n_buyers` and their sensitivity versions),
  as Section 3 pins co-ownership's targets and marginals for a null model (my call).
  `vendor_link_support.parquet` and `vendor_link_pairs.parquet` are not read. The pair table
  holds UEI pairs and stays on this machine (Stage 14 findings, "For the resume and O18").
- **`outputs.json` is hashed too**, as Section 2's W1 does, so the table hashes rest on the pin
  (my call). `report.json` is not pinned: the universe statement is also the `universe` column of
  every target row, and a count on 2026-11-23 found it equal to `report.json`'s.
- **Two gates.** The V9 decision gives `supplier_share` a minimum of 4 and `buyer_share` a minimum
  of 3, on `n_unweighted`. Every row still carries `size_gate_pending`, so the reader applies the
  gate from the Evidence table.

### Measurements

Read-only, on 2026-11-23, with no embedder output read. The scripts lived outside the repository.

1. The SHA-256 of `outputs.json`, `vendor_links.parquet` and `vendor_link_marginals.parquet` was
   recomputed from the bytes on disk. Each equals its inventory value.
2. The kept rows were recounted from `vendor_links.parquet` with the two minimums. They equal the
   V9 decision: 2,315 `supplier_share` rows, 2,234 `buyer_share` rows, 1,785 cells with both
   rows kept, and 42 and 15 kept rows with the intra-group label.
3. The `universe` column holds one value in all 16,614 rows, equal to `report.json`'s `universe`.
4. The industries were split under naics-embedder's committed salt and rule at `2b2029c` (the
   rule of the Stage 16 spec, "Measured split"):

| Count | Value |
| --- | ---: |
| Industries in a target row | 689 (339 validation, 350 sealed) |
| Kept `supplier_share` rows | 2,315: 47 diagonal, 500 both validation, 603 both sealed, 1,165 one in each part |
| Kept `buyer_share` rows | 2,234: 40 diagonal, 484 both validation, 598 both sealed, 1,112 one in each part |
| All published cells (8,307) | 88 diagonal, 1,895 both validation, 2,224 both sealed, 4,100 one in each part |

These counts depend on the salt and the run. They describe the evidence and set no rule.

### Assignment

- **Judge only (P8).** No part selects. The consuming spec may split the family, for example by
  its anchor rule and salt so that each industry sits in the same part as in co-ownership. A split
  only limits what the one opening reads and reports. No part is read before the opening (my
  call: under judge only, a part read early could only inform a choice, and that is selection).
- **No development measurement.** Sections 1 and 3 let a validation-part score be published as a
  development measurement. Section 5 has no such part (my call, from P8).
- **The assignment waits for the owner (VL4).** It is to naics-embedder's relatedness spec as its
  owner amends it, from the commit that the owner names, as in Section 2's W7.
- **Choices fixed before any value is read.** The consuming spec fixes which measures it reads,
  its null model and its scores before it reads any target value of the family (my call). Without
  this, a choice made after seeing values would act as selection on the judge.

### Conditions

Condition ids carry the prefix VL (my call, as CO and AM in Sections 3 and 4). The conditions
repeat a consuming-spec rule only where it is this repository's own limit (my call, as in Sections
1 and 3):

- what counts as headline evidence (the two gates, the intra-group sensitivity);
- the role under R8.4 (P8);
- the wait for the owner to name the consuming spec (VL4);
- the universe statement;
- the same-relation rule (VL6).

**Mirror pairs.** CO4 asks co-ownership for a crossing-share report, because its validation part
selects and cosine similarity is symmetric. Under judge only, no part of the vendor links selects,
so CO4's reason does not apply to them directly. Selection on co-ownership's validation part
still tunes the same industry vectors. The section records the measured split as evidence and
does not require a crossing report (my call). The consuming spec may report one.

**Same relation (VL6).** Vendor links measure a supplier-to-buyer relation between industries. The
Stage 14 spec states that this differs from the relation that TRI parent links and ITA co-ownership
measure, and the build excludes intra-group pairs to keep vendor links apart from ownership. The
area mixes measure co-location in counties, which also differs. BEA input–output tables, which are
not built, use the same supplier → buyer convention (Stage 2 spec, Direction) and measure the same
relation. So a BEA family never trains an embedding that the vendor links judge (my call, as CO7
and AM4).

## Edits

### Edits to the protocol file in this design commit

1. Add Section 5 after Section 4, with `Status: PROPOSED`.
2. Under "Design provenance", add that Section 5 has its design in this file.
3. In the introduction, add a sentence that names Section 5.
4. In "Families with no section", say that the USAspending vendor links have Section 5 and stay
   unscored until VL4 is met.
5. In the Handoff, add that Section 5 opens nothing in naics-embedder until the owner names the
   consuming spec under VL4.

### Edits on approval

One docs commit applies these. Each edit is a pointer or a status, not a rule change.

1. **Protocol, Section 5, and the protocol's Status line.** Change Section 5's status to
   "APPROVED (date, owner)", and add Section 5 to the protocol's Status line.
2. **This file.** Change Status to "APPROVED (date, owner)".
3. **Source spec**, the introduction (line 17) and Out of scope, "Evaluation protocol"
   (line 691): add that Section 5 covers the USAspending vendor links.
4. **`CLAUDE.md`**, the "USAspending vendor links (roadmap Stage 14)" paragraph: add that reads of
   the vendor links follow Section 5, which lets them judge only, and that no read is allowed
   until the owner names the consuming spec there.
5. **`README.md`**, the "USAspending vendor links (roadmap Stage 14)" section: the same sentence.
6. **`specs/deliverable-map.md`**, the USAspending row: in the Relatedness column, the role from
   Section 5 (judges only, after the owner names the consuming spec). In "Still blocked by",
   naics-embedder's assignment of the family and the owner's naming of it under VL4.
7. **`specs/naics-evaluation-data-stage-23-findings.md`**: a new one-screen file. It records the
   stage's cost in sessions, the measurements and what is not claimed.
8. **Roadmap**: tick Stage 23 and add its COMPLETE stamp, as Stage 16's PR did (my call).
9. **This file** moves to `specs/completed/`, as the Stage 16 and Stage 24 specs did.

The retired Stage 14 spec gets no pointer (my call). Its Limits line ("The protocol section, O18,
decides which families may judge one another") is answered by VL6, and no gate in naics-embedder
reads that spec. Findings and retired plans are records and are not edited. R8.4's text is
unchanged.

## Constraints

- No source file, test or data file changes. Every software hash recorded by a selected run stays
  as recorded.
- The commit hooks skip the test suites for changes under `specs/` and root-level Markdown. No
  flag is used to skip a hook.
- R8.4's text is unchanged (P8).
- Stage 25 (TRI) also adds a section to `specs/evaluation-protocol.md`. If it merges first, this
  section becomes Section 6, and the ids and pointers are renumbered at the merge, with no change
  to content (my call, as the Stage 16 and Stage 24 Constraints).

## Verification: observable outcomes

- [ ] The protocol file on `main` has Section 5 with Status APPROVED.
- [ ] Each Evidence value equals the selected run's `outputs.json`, and the SHA-256 of
      `outputs.json` equals the pin.
- [ ] The kept counts equal the V9 decision and a recount on the selected run.
- [ ] The split counts equal a recount with the salt at naics-embedder `2b2029c`.
- [ ] A reader can answer from the protocol alone: what role the family has; who decides the split
      and the scores; which run, pin, tables and gates to read; when a read may begin; which
      families measure the same relation.
- [ ] "Families with no section" names Section 5 for the vendor links.
- [ ] `CLAUDE.md`, `README.md`, the source spec and the deliverable map point to Section 5.
- [ ] R8.4's text is unchanged.
- [ ] `git diff --stat` for the change lists only Markdown files.
- [ ] Stage 23 is ticked in the roadmap, and the findings file exists.

## Left to the builder

- The exact wording of the pointer sentences, within the limits above.

## Handoff

- **naics-embedder.** The section opens nothing yet. A roadmap resume can record that a protocol
  section exists for the USAspending vendor links, with the role "judge only". G4 opens for the
  family only after the owner amends Section 5 under VL4 to name the relatedness spec, at a
  commit that assigns the family. That spec then fixes its measures, null model and scores before
  it reads any value (VL3).
- **Stage 25.** It adds its own section. If it merges first, renumber at the merge. TRI and the
  vendor links measure different relations (VL6), so neither section limits the other's role.
- **R8.4 (G1).** A separate owner decision. The vendor links stay out of training under P8 even if
  R8.4 changes, until the owner amends Section 5.

## Rollout note

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 23 — on plan completion, tick the stage and re-validate later stages against what shipped.

No plan is needed, because the design adds no code (my call, as for Sections 1 to 4). The edits on
approval stand in for the plan, and the PR that applies them completes the stage.
