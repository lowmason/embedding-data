# Evaluation protocol

> Next step: resume naics-embedder's roadmap
> `specs/naics-artifact-redesign-roadmap.md`, which re-reads its gates here.
> The pointer edits in "Edits on approval" were applied with the approval. No
> plan was needed, because the spec adds no code (my call).

Status: APPROVED (2026-11-18, owner: "Approve the spec"). Written 2026-11-18.

This is the successor evaluation-protocol spec that the
[source spec](embedding-evaluation-data-spec.md) requires "before any embedder
is scored" (Out of scope, "Evaluation protocol"). It has one section for each
evidence family. A family with no section here is not scored. The first section
covers the ITA text–code pairs. No other family has a section yet.

## Design provenance

A brainstorming session with the owner on 2026-11-18. The inputs read were:

- the source spec, R7.2, R7.3, R8.4, V9 and Out of scope, at `c2dacb4`;
- the Stage 10 spec `specs/completed/ita-establishment-targets.md`, with its
  amendment of 2026-11-18, and the
  [Stage 10 finding](findings/stage-10-ita-establishment-targets.md);
- the [V9 ITA NAICS decision](findings/v9-ita-naics-minimum-counts.md);
- in naics-embedder (`~/Projects/naics-embedder`) at `81fc3c7`:
  `specs/naics-artifact-redesign.md` (Reqs 26 and 28, rulings U27 and U28),
  `specs/naics-artifact-redesign-roadmap.md` (gates G2 to G5) and the approved
  `specs/text-to-code-ita-panel.md` (last changed at `94e2747`).

**Owner decisions (2026-11-18).**

| Id | Question | Decision |
| --- | --- | --- |
| P1 | What scope does the first protocol spec have? | "ITA pairs only" |
| P2 | How is it built? | "Confirm approach": a thin spec that delegates split and scoring and keeps the read conditions here |
| P3 | When is R8.4 amended? | "Wait for Stage 6 spec". R8.4 is unchanged by this spec |

**My calls.** Choices made while writing, which the owner has not ruled on, are
marked (my call).

## Intent

naics-embedder's text→code artifact answers an owner who describes an
establishment and asks for its NAICS code. Its judge is the ITA text–code
pairs, which are text that real employers wrote for that purpose.

Two documents claimed the rules for that judge:

- The Stage 10 spec's Out of scope line gives data splits to "the successor
  evaluation-protocol specification", and three of its lines leave the use of
  the copied-text flags to "the scoring protocol". Its amendment of 2026-11-18
  already names naics-embedder's spec as the home of the split.
- naics-embedder's owner ruling U28 gives the split and the scoring of ITA
  pairs to text→code's own spec, which is approved and fixes both.

No real pair can be read while that conflict stands. naics-embedder holds its
text→code stages on a gate, G4: this spec must exist and must assign ITA split
and scoring to text→code's spec. This spec settles who decides what. It does
not design a scoring method.

**Success.** A naics-embedder roadmap resume can cite this file at a commit on
`main` and record G4 as open for the ITA pairs.

## Goals, non-goals and anti-goals

**Goals.**

1. Assign the split and the scoring of the ITA text–code pairs to
   naics-embedder's text→code spec.
2. State the conditions that this repository keeps for every read of the pairs.
3. Name the run, the pin and the two table hashes that a read uses.
4. State that every other family stays unscored until it has a section.

**Non-goals.**

- A scoring method, a metric, a margin or a reference. These are text→code's.
- A protocol for co-ownership, the area mix, or any ACS, CPS or new family.
- Any change to R8.4.
- Any code, test or data change.

**Anti-goals.** The design fails, even if it merges, when it:

- restates the split or scoring rules, so that two repositories hold copies;
- lets a reader treat this spec as a protocol for a family with no section;
- lets any pair train an embedder;
- weakens a limit of the Stage 10 amendment of 2026-11-18.

## Approaches

| Approach | What it does | Trade-off | Decision |
| --- | --- | --- | --- |
| 1. Thin delegation | Assign split and scoring to text→code's spec. Keep only the read conditions here. | Smallest document. Each rule has one home. Readers need both repositories. | **Chosen** (P2) |
| 2. Restate the rules | Copy the split, scoring and margin rules into this repository. | Self-contained, but the copies drift, and U28 gave the rules to text→code's spec. | Rejected |
| 3. Umbrella protocol | Write all families now, with empty sections where no design exists. | One document for everything, but it invites content nobody designed, and only ITA families are built. | Rejected |

## Rules for every family

1. **No section, no score.** An embedder is scored against a family only after
   that family has a section in this file.
2. **One file, one section for each family** (my call). A later family adds a
   section through its own design session. It does not get a separate protocol
   file.
3. **Roles come from R8.4.** A section states which table or part selects and
   which judges. It allows training only if R8.4, as amended at that time,
   allows it.
4. **Verified evidence only.** A section names a run and its detached pin. A
   read checks the files against that pin first (see condition C1 for the
   form).
5. **The count gate comes first.** A family that has unweighted counts gets a
   section only after its V9 minimum count is decided (source spec R7.3). A
   family with no unweighted count, such as a published aggregate, says so in
   its section (my call).

## Section 1: ITA text–code pairs

### Evidence

The R7.2 family "Text–code pairs", built by Stage 10. A read uses the first
run (my call: the replay's `ita_text_pairs.parquet` has equal values but
different bytes, so one run must be named).

| Item | Value |
| --- | --- |
| Run | `stage10_ita_establishment_20261116_r1` in `data/derived/osha/establishment-targets/` |
| Detached pin (SHA-256 of `outputs.json`) | `e19b0d58f61f106c3994aa6fe51f4fb71244188145dd90f8cccaa8dc8a8b09df` |
| `ita_text_pairs.parquet` | 644,265 rows, SHA-256 `60aad7642961e70b987e9d3222d660147861458e12ac52d71d2739d2d21e1e1c` |
| `ita_text_pair_codes.parquet` | 771,971 rows, SHA-256 `c8084e4ad297e3f78391e035ebe51119b07982639ae4daf47f1d47caeb1f8916` |
| Count gate | Minimum 1 on `n_headline_records` of pairs with `flag_headline` (V9 decision). The headline rule needs at least one eligible record, so every headline pair meets it |

### Assignment

For this family, naics-embedder's `specs/text-to-code-ita-panel.md` decides:

- the split into a validation part and a sealed part;
- the query text, the candidates and the rank rule;
- the metrics, the headline, the copied report and every other report;
- the use of the copied-text flags and of the mojibake, company-fallback and
  code-conflict flags. At `94e2747`, a pair with `flag_copied_title_any` or
  `flag_copied_index_any` is out of the headline score and is reported apart,
  and the other flags are reported as counts;
- the reference, the margin and the decision rule;
- the logging of reads and the one opening of the sealed part.

The version read for this assignment is naics-embedder `94e2747`. The
assignment is to that spec as its owner amends it, not to a frozen copy (my
call). The conditions below bind every version. If a later version conflicts
with a condition, the condition governs until the owner amends this section.

For the ITA pairs only, this assignment answers the places where the Stage 10
spec defers to the protocol: its Out of scope line on data splits, scoring and
acceptance thresholds, and its three lines on the use of the copied-text and
other flags (Accepted proposals, Intent, and the note under the headline rule).
For co-ownership, those questions stay open (Families with no section). That
spec is retired and is not edited.

A condition repeats a rule of text→code's spec in two places only, C2 and C3.
Both are this repository's own limits: what counts as headline evidence, and
the roles that the amendment allows (my call).

### Conditions this repository keeps

- **C1. Check the pin before the first read.** The reader computes the SHA-256
  of each of the two tables and compares it with the value above. A mismatch
  stops the read. This comparison is the required form. `verify` is not
  required, because it also needs this repository's recorded software
  environment (my call).
- **C2. Read headline evidence only.** Pairs with `flag_headline = true`, and
  for each such pair its code rows with `flag_headline_basis = true`. No other
  pair or code row is scored.
- **C3. Roles.** The validation part selects. The sealed part judges and is
  opened once. No pair, and no ITA description, enters training, curriculum
  construction or hard-negative mining. The split unit is `description_key`,
  so one normalized description is in one part only. Only the sealed part is
  reported as evaluation. This is the Stage 10 amendment of 2026-11-18. Two
  points make it exact (my calls):
  - "Opened once" means one logged opening. Several arms and seeds may be
    scored inside it. A second opening needs a recorded reason, as text→code's
    spec requires.
  - A validation-part score may be published as a development measurement. It
    is labeled as not evaluation, and C4 applies to it.
- **C4. State the universe with every published score.** The statement names
  the run and the pin, and says at least this: ITA is a program-selected filing
  population and represents no wider set of establishments. Codes are
  self-reported and unvalidated. A pair's headline codes are native NAICS 2022
  codes from filing years 2023 to 2025. Its text is the most frequent string
  over all of its records, which can include filing years 2016 to 2022. The
  copied flags catch exact normalized identity only.
- **C5. A new bundle needs an amendment.** A rebuild, for example after OSHA
  extends the 2025 file, has a new pin. The owner amends the Evidence table
  before any read of it. Text→code's split depends on the key alone, so an old
  description keeps its part.
- **C6. Fixtures are not evidence.** A score from fixture tables shows software
  readiness. It is never reported as a result.

### What this repository does not decide

The scores, their intervals, the margin and the adoption decision. It also does
not check naics-embedder's selection log. That repository's own rules guard the
order of reads.

## Families with no section

These are not scored until a section exists: ITA co-ownership, the 2023 ITA
area mix, every ACS and CPS family, and each new family of
`specs/uncovered-uses-evidence-sources.md`. For co-ownership and the area mix,
the open design questions include null-model normalization and the choice of
scores (Stage 10 spec, Out of scope, and methodology K5 and K6).

## Edits on approval

One docs commit applies these. Each edit is a pointer, not a rule change.

1. **Source spec, Out of scope, "Evaluation protocol".** Add: "The successor
   spec is [evaluation-protocol.md](evaluation-protocol.md). It covers the ITA
   text–code pairs. Every other family waits for its own section there.
   *(owner, 2026-11-18)*"
2. **Source spec, introduction.** After "belongs to a successor spec (see Out
   of scope)", add the same link.
3. **`CLAUDE.md`, Stage 10 paragraph.** Add one sentence: reads of the
   text–code pairs follow `specs/evaluation-protocol.md`, Section 1.
4. **`README.md`, Stage 10 section.** Add the same sentence after the R8.4
   exception.
5. **This file.** Change Status to "APPROVED (date, owner)".

Findings, retired specs and retired plans are records and are not edited.

## Constraints

- No source file, test or data file changes. The Stage 10 software hashes stay
  as recorded.
- The commit hooks skip the test suites for changes under `specs/` and
  root-level Markdown. No flag is used to skip a hook.
- R8.4's text is unchanged (P3).

## Verification: observable outcomes

- [ ] This file is on `main` with Status APPROVED.
- [ ] The source spec's Out of scope bullet links to this file and names its
      scope.
- [ ] `CLAUDE.md` and `README.md` point to Section 1 for reads of the pairs.
- [ ] `git diff --stat` for the change lists only Markdown files.
- [ ] The four values in the Evidence table equal the values in the selected
      run's `outputs.json`, and the SHA-256 of that file equals the pin.
- [ ] A reader can answer from this file alone: who decides the split, who
      decides the scoring, which run and pin to read, and which families are
      still unscored.

## Left to the builder

- The exact wording of the pointer sentences, within the limits above.
- The place of the new sentence inside the `README.md` Stage 10 section.

## Handoff

- **naics-embedder.** A roadmap resume re-reads G2 (opened by
  lowmason/embedding-data#21), G3 and G5 (the V9 decision of 2026-11-17) and G4
  (this file) at one commit of this repository. G4 opens for the ITA pairs
  only. For the relatedness families it stays closed.
- **Later families.** Each adds a section here through its own design session,
  after its build and its count gate.
- **R8.4.** A separate owner decision, after naics-embedder's relatedness spec
  names the families that train.
