# Evaluation protocol: TRI parent links

Status: PROPOSED (2026-11-23). Written in a brainstorming session with the owner.

Roadmap: `specs/naics-evaluation-data-roadmap.md`, Stage 25 (Track B, O17). The design adds
Section 5 to [the evaluation protocol](evaluation-protocol.md). This file holds its provenance, the
owner's decisions, the measurements and the pointer edits. The protocol file holds the rules.

## Design provenance

A brainstorming session with the owner on 2026-11-23. The inputs read were:

- in this repository at `32f3ccf`: the roadmap's Stage 25 entry and "Choices made";
  `specs/evaluation-protocol.md` (Sections 1 to 4, "Families with no section", Handoff); the
  Stage 16 design `specs/completed/evaluation-protocol-ita-relatedness.md`; the TRI spec
  `specs/completed/tri-parent-links.md` (Anti-goals, Limits, lines 705–706, Handoff); the
  Stage 5 findings `specs/naics-evaluation-data-stage-5-findings.md` ("Full-data build", "For
  O12, O13 and O17"); the Stage 18 finding `specs/findings/stage-5-tri-parent-links.md`; the V9
  TRI decision `specs/findings/v9-tri-minimum-counts.md`; plan 20's Handoff
  (`specs/plans/completed/20-tri-minimum-counts.md`); `specs/deferred_items.md`, sections
  `18-tri-parent-links` and `20-tri-minimum-counts`;
- in naics-embedder (`~/Projects/naics-embedder`) at `2b2029c`: the completed relatedness spec
  `specs/completed/relatedness-artifact.md` (§4.1, §4.6, §4.8 and the table of roles), its split
  code `src/naics_embedder/panels/relatedness_split.py` and its split settings
  `conf/data/relatedness_panel.yaml`.

Two read-only measurements were made on the selected run. Neither reads an embedder output.

1. The SHA-256 of `outputs.json` and of the two tables named in the Evidence table were recomputed
   from the bytes on disk. Each equals its inventory value.
2. The split of TRI pairs under naics-embedder's committed salt and rule (see "Measured split").

**Owner decisions (2026-11-23).** The ids continue from the protocol's P1–P7.

| Id | Question | Decision |
| --- | --- | --- |
| P8 | naics-embedder's relatedness spec lets TRI join as a second judge (§4.1). Its join path reads TRI's validation part: a margin record with fresh reference reads, and a validation test of the forward candidate (§4.6). The TRI spec and the Stage 5 findings exclude TRI from model selection. May TRI's validation part select? | "Allow selection": for naics-embedder's relatedness artifact only, as CO3 allows for co-ownership |
| P9 | How is it written? | "Approach 1": one thin section in the protocol, with the design history in this file, applied in this session in one docs-only PR |

**My calls.** Choices made while writing, which the owner has not ruled on, are marked (my call).
Points marked (proposal) wait for the owner's ruling on this design.

## Intent

naics-embedder's relatedness artifact is one embedding of the NAICS 2022 codes. ITA co-ownership
judges it (protocol Section 3). Its spec plans a second judge from another source: TRI parent
links (relatedness spec §4.1). A candidate must beat the reference on every judging family, so a
second judge can only make the test harder. TRI may join only when it is built, count-gated and has
a protocol section. Stages 5, 18 and 22 met the first two. This stage writes the section.

The TRI parent links measure a directional relatedness share of the same shape as co-ownership:
for two NAICS 2022 industries a and b, the share of owners in a that also operate a TRI facility in
b in the same reporting year. Section 3 answers the open questions for that shape by assignment
("Families with no section"). This section follows it.

**Success.** A naics-embedder relatedness amendment can cite the protocol at a commit on `main` as
TRI's protocol section, with selection on TRI's validation part allowed (P8).

## Goals, non-goals and anti-goals

**Goals.**

1. Assign the split, the null model, the scores and the margin for TRI to naics-embedder's
   relatedness spec.
2. Let selection read TRI's validation part, under the limits of CO3 (P8).
3. Name the run, the pin and the table hashes that a read uses.
4. State what holds reads until the relatedness spec admits TRI.
5. Answer by name each place where the TRI spec and the V9 TRI decision defer to the protocol.

**Non-goals.**

- A scoring method, a metric, a null model, a gain, a margin or a reference. These are the
  relatedness spec's.
- A training role for TRI. R8.4's text is unchanged.
- A role for TRI in any artifact other than the relatedness artifact.
- Sections for USAspending (Stage 23), BEA, ACS or CPS.
- Any code, test or data change.

**Anti-goals.** The design fails, even if it merges, when it:

- restates the relatedness spec's rules, so that two repositories hold copies;
- lets a TRI row, or a quantity derived from one, train an embedder;
- lets a sensitivity count (D&B key, federal facilities in) replace the headline count or add a
  pair;
- hides that the sealed read shares pairs with the validation part, or that TRI and co-ownership
  share pairs;
- weakens a condition of Section 3 for co-ownership.

## Approaches

| Approach | What it does | Trade-off | Decision |
| --- | --- | --- | --- |
| 1. Thin section, history apart | Section 5 in the protocol assigns split and scoring to the relatedness spec and keeps the read conditions. Provenance, decisions and measurements live in this file. | Each rule has one home. The shared protocol file stays short, which matters because Stage 23 also edits it. A reader needs this file only for the why. | **Chosen** (P9) |
| 2. Thin section, history in the protocol | The same section, with provenance and decisions inside the protocol file, as Section 1 did. | One file, but it grows by a few hundred lines and gives Stage 23 a larger file to merge into. | Rejected |
| 3. Fold TRI into Section 3 | One section, "co-ownership and TRI parent links", under one set of conditions. | Fewer words, but it rewords an approved section, breaks Rule 2 (one section for each family), and mixes two populations with different limits: ITA filers keyed by EIN, and EPA's standardized parents with the E8 time basis. | Rejected |

## Design

The rules are Section 5 of [the evaluation protocol](evaluation-protocol.md). It follows Section 3's
frame: Evidence, Assignment, Conditions, and what this repository does not decide. The points below
are the design choices behind it.

### Evidence

- **The first run, for its pin.** A read uses `stage5_tri_parent_links_20261121_r1`. Unlike the ITA
  bundles, the replay `stage5_tri_parent_links_20261121_r1_replay` has five Parquet files and a
  `report.json` with the same bytes as the first run's (Stage 18 finding). The table hashes are
  the same in both runs. Only the detached `outputs.json` differs, so one run is named for its pin
  (my call). The V9 TRI decision also read the first run.
- **Only the tables a read uses.** `tri_parent_links.parquet` (the target, with J as
  `n_unweighted`) and `tri_parent_link_marginals.parquet` (n(a) and the other marginals for a null
  model). These match the two tables that Section 3 pins for co-ownership (my call). The support
  table, the facility-year table and the parent-industry table (O8) are not read. A read of another
  table needs an amendment that adds its hash (my call, as CO6).

### Measured split

naics-embedder's rule puts a six-digit code in the validation part when the first 8 bytes of
SHA-256(`salt` + NUL + `code`), as a big-endian integer, are even. The committed salt is
`4bfd5195916df66d0e1c619c6507f2ad` (`conf/data/relatedness_panel.yaml` at `2b2029c`). The
relatedness spec gives TRI the same rule and salt, so an industry is in the same part in both
families (§4.1). Every TRI unit is a six-digit national industry.

The count script was first checked on `ita_co_ownership.parquet` of the Stage 10 run. It reproduced
Stage 16's counts exactly: 909 industries (440 validation, 469 sealed) and 19,576 pairs (4,575 /
5,159 / 9,842). Applied to `tri_parent_links.parquet` of the selected run on 2026-11-23:

| Count | Value |
| --- | ---: |
| Industries in a target row | 359 (173 validation, 186 sealed) |
| Industries with a marginal row | 405 |
| Unordered industry pairs | 7,102 |
| Both industries in validation | 1,497 |
| Both industries in sealed | 2,048 |
| One industry in each part | 3,557 (50.1%) |
| Directed rows whose anchor is sealed | 7,653 |
| Of these, rows whose mirror's anchor is in validation | 3,557 (46.5%) |
| TRI pairs that are also co-owned pairs in Section 3's table | 2,497 of 7,102 (35.2%) |
| TRI industries that also appear in a co-ownership target row | 354 of 359 |

The crossing share is close to co-ownership's 50.3%, so the mirror-pair report of CO4 applies with
the same weight. The overlap shows that TRI is not independent of co-ownership: about a third of
its pairs are also co-owned pairs in ITA. These counts depend on the salt and the run. They
describe the evidence and set no rule.

### Assignment

- **To the relatedness spec, as its owner amends it**, not to a frozen copy, as in Sections 1 and 3
  (my call). The version read is naics-embedder `2b2029c`. There TRI has no role yet: its table of
  roles says "Nothing yet", and §4.1 admits TRI as a judge only through an amendment of that spec,
  made before the sealed opening, with TRI's own margin record first.
- **Everything the relatedness spec decides for co-ownership, it decides for TRI**: the split and
  the handling of mirror pairs; the null-model normalization and the choice of scores (candidates,
  relevance rule, gain, headline, other reports); the treatment of absent (zero) cells; the use of
  the marginals, including `n_multi_industry_owners` and `n_owners_partial`, and of the two
  sensitivity labels; the references, the margin and the decision rule; the logging of reads and
  the one opening of the sealed part. This section does not say how the co-ownership gain carries
  over to TRI, because at `2b2029c` the relatedness spec does not say it either.
- **What holds reads until TRI is admitted** (proposal, see "Open for the owner", Q-A). Condition
  TR8 asks the owner to amend Section 5 to name the relatedness spec's commit that admits TRI,
  before any real read. This repeats W7's pattern for the wage panel spec. The alternative is to
  rely on the relatedness spec's own rule (§4.1), which already forbids a read before its
  amendment.

The assignment answers these deferrals by name:

- the V9 TRI decision, section 10 ("Not claimed"): scoring, null models, splits and the treatment
  of absent (zero) cells;
- the TRI spec's Handoff, the O17 line: the counts and marginals for any null model, the two
  sensitivity labels, the universe statement, the E8 time basis and the R8.4 exclusion. The first
  two are assigned. The universe statement and the E8 time basis enter TR6. The R8.4 exclusion is
  kept for training and narrowed for selection by P8 (TR3).

### Conditions

The conditions repeat a relatedness-spec rule only where it is this repository's own limit, as in
Sections 1 and 3 (my call):

- what counts as headline evidence (TR2);
- the roles under R8.4 (TR3, P8);
- the mirror-pair report (TR4, as CO4 under P5);
- the same-relation rule (TR5);
- the universe statement (TR6).

Condition ids carry the prefix TR (my call, as CO and AM).

- **TR2, headline evidence.** J is `n_unweighted`: distinct owners under EPA's standardized U.S.
  parent name, federal facilities out, each owner counted once over reporting years 2022 to 2024,
  with both industries in the same year. The D&B-key count and the count with federal facilities
  in are sensitivities. 8,050 of the 14,204 rows (56.7%) carry the D&B label and 40 carry the
  federal label (V9 TRI decision, section 6). Cells that exist only under a sensitivity (264 under
  the D&B key, 298 with federal facilities) are not published and never become pairs.
- **TR3, roles (P8).** The validation part selects, for the relatedness artifact only. The rest is
  CO3, applied to TRI: the sealed part judges and is opened once; no row trains, builds a curriculum
  or mines hard negatives; the split comes first and depends on the code alone; only the sealed part
  is reported as evaluation. The basis is R8.4's second sentence, as for CO3. R8.4 is unchanged.
- **TR5, same relation.** CO7 names TRI as a family that measures the relation co-ownership judges.
  TR5 states the rule in both directions: neither family trains an embedding that the other judges.
  Neither trains at all today, so the rule binds only a later R8.4 amendment. TRI does not measure
  the area mix's relation (co-location in a county), so AM4 does not apply to it (my call). Whether
  the USAspending shares measure TRI's relation is Stage 23's to say.
- **TR6, universe.** Built from the `universe` string of `report.json`, the E8 time basis and the
  TRI spec's Limits (my call).

## Edits

### Edits to the protocol file in this design commit

1. Add Section 5 (TRI parent links) after Section 4, with `Status: PROPOSED`.
2. Under "Design provenance", add that Section 5 has its design in this file.
3. In the introduction and the Status line, name Section 5 as proposed.
4. In "Families with no section", say that the TRI parent links have Section 5.
5. In the Handoff, add a line for TRI.

### Edits on approval

One docs commit applies these. Each edit is a pointer, a status or an exception sentence, not a
rule change.

1. **Protocol, Section 5 and the Status line.** Change Section 5's status to "APPROVED (date,
   owner)".
2. **This file.** Change Status to "APPROVED (date, owner)", then move it to `specs/completed/`
   with a COMPLETE stamp, as Stage 16 did (my call).
3. **Source spec** `specs/embedding-evaluation-data-spec.md`, the introduction (line 17) and Out of
   scope, "Evaluation protocol" (line 691): add that Section 5 covers the TRI parent links.
4. **`CLAUDE.md`**, TRI paragraph: after "No output may feed embedder training, curriculum,
   hard-negative mining or model selection (R8.4).", add one exception sentence: selection for
   naics-embedder's relatedness artifact may read the validation part of the parent links, split by
   anchor industry (owner, P8, 2026-11-23), and reads follow Section 5 of the protocol.
5. **`README.md`**, TRI section (lines 598–600): the same exception sentence after "Under R8.4, no
   TRI table may feed embedder training, curriculum, hard-negative mining or model selection."
6. **`specs/deliverable-map.md`**, the TRI row (line 13): replace "Its section in the evaluation
   protocol (O17)" with the assigned role and a pointer to Section 5. Keep "R8.4, if it trains".
7. **Retired TRI spec** `specs/completed/tri-parent-links.md` (proposal, see "Open for the
   owner", Q-B): one dated pointer line after its anti-goal "Lets any table feed embedder training,
   curriculum, hard-negative mining or model selection (R8.4)" (line 124). The line says that
   Section 5 of the protocol lets selection for naics-embedder's relatedness artifact read the
   parent links' validation part (owner, P8, 2026-11-23). The anti-goal is not reworded.
8. **`specs/naics-evaluation-data-stage-25-findings.md`**: a new one-screen file. It records the
   stage's cost in sessions, the two measurements and what is not claimed.
9. **Roadmap**: tick Stage 25 and add its COMPLETE stamp, as Stage 16's PR did (my call).

Findings and retired plans are records and are not edited. The Stage 5 findings keep their line
"no TRI table feeds embedder training, curriculum, hard-negative mining or model selection". The
V9 TRI decision keeps its "Not claimed" section. R8.4's text is unchanged.

## Open for the owner

- **Q-A. What holds reads until the relatedness spec admits TRI?** (TR8)
  - *Owner names the commit here (proposal).* Before any real read, the owner amends Section 5 to
    name the relatedness spec's commit that admits TRI. This is W7's pattern. This repository keeps
    the gate, and the protocol names the exact text that governs TRI. The cost is one more docs
    amendment here when naics-embedder amends its spec.
  - *Rely on the relatedness spec.* Its §4.1 already forbids a read before its amendment. No second
    amendment is needed, but this repository then learns of the join only from the other repository.
- **Q-B. Does the retired TRI spec get a dated pointer?** (edit 7)
  - *Add pointer (proposal).* Stage 16's P7 gave the retired Stage 10 spec the same kind of
    pointer, because naics-embedder reads its gates from that text. The TRI spec's anti-goal says
    no table may feed model selection, so a reader of that file alone would see a rule that P8 has
    narrowed.
  - *No pointer.* The retired spec stays untouched. The protocol, `CLAUDE.md`, the README and the
    deliverable map carry the exception.

## Constraints

- No source file, test or data file changes. Every software hash recorded by a selected run stays
  as recorded. In particular, no file in `tri_bundle.SOFTWARE_FILES` changes.
- The commit hooks skip the test suites for changes under `specs/` and root-level Markdown. No flag
  is used to skip a hook. Before each commit, run the Stage 9 `pgrep` check.
- R8.4's text is unchanged.
- Stage 23 also edits `specs/evaluation-protocol.md`. Keep the edits outside Section 5 small and
  local. If Stage 23's section merges first, renumber at the merge and keep this design's content
  (my call).

## Verification: observable outcomes

- [ ] The protocol file on `main` has Section 5, with Status APPROVED.
- [ ] Each Evidence value equals the selected run's `outputs.json`, and the SHA-256 of that file
      equals the pin.
- [ ] The split counts equal a recount with the salt at naics-embedder `2b2029c`, and the same
      script reproduces Stage 16's co-ownership counts.
- [ ] A reader can answer from the protocol alone: who decides TRI's split, null model and scores;
      which part selects and which judges; what holds reads until TRI is admitted; which run, pin
      and tables to read.
- [ ] "Families with no section" names Section 5 for TRI.
- [ ] `CLAUDE.md`, `README.md`, the source spec and the deliverable map point to Section 5.
- [ ] R8.4's text is unchanged.
- [ ] `git diff --stat` for the change lists only Markdown files.
- [ ] Stage 25 is ticked in the roadmap, and the findings file exists.

## Left to the builder

- The exact wording of the pointer sentences, within the limits above.

## Handoff

- **naics-embedder.** An amendment of the relatedness spec admits TRI as a second judge (§4.1). It
  cites Section 5 at a commit on `main`. TRI then needs its own margin record before any candidate
  read on TRI (§4.6), and the superiority level becomes 97.5%. TR4 asks for the same mirror-pair
  report as CO4.
- **Stage 23.** Section 5 is a second worked case of Section 3's shape. If Stage 23 merges first,
  renumber at the merge. Stage 23 says whether the USAspending shares measure TRI's relation (TR5).
- **R8.4.** Unchanged. TRI has no training role, and none is proposed.

## Rollout note

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 25 — on plan completion, tick the stage and re-validate later stages against what shipped.

No plan is needed, because the design adds no code (my call, as for Sections 1 and 3). The edits on
approval stand in for the plan, and the PR that applies them completes the stage.
