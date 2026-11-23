# Evaluation protocol, Section 2: ACS wage microdata

> Next step: on the owner's approval, apply "The section" and "Edits on approval" in one docs
> commit, write the findings file, tick Stage 24 of the roadmap and retire this file to
> `specs/completed/`. No plan is needed, because the stage changes no code (my call, after
> Stage 2 and the protocol spec itself).

Status: DRAFT (2026-11-23). Awaiting the owner's approval.

This is the stage spec for Stage 24 of `specs/naics-evaluation-data-roadmap.md` (Track H,
outcome O24). It adds a section for the ACS wage microdata to `specs/evaluation-protocol.md`.
The section text is in "The section" below and moves into the protocol on approval.

## Design provenance

A brainstorming session with the owner on 2026-11-23. The inputs read were:

- in this repository at `f6b339f`: the roadmap's Stage 24 entry and its "Choices made";
  `specs/evaluation-protocol.md` (Section 1, "Rules for every family", "Families with no
  section", "What this repository does not decide"); the source spec's R7.2, R7.3, R7.4,
  R8.1, R8.4 and V9 paragraphs; the Stage 17 spec `specs/completed/acs-wage-microdata.md`
  (Owner decisions, Non-goals, Design, "Handoff to naics-embedder");
  `specs/naics-evaluation-data-stage-17-findings.md`; the
  [V9 ACS wage decision](findings/v9-acs-wage-minimum-earners.md); the Handoffs of plan 14
  and plan 17;
- the `outputs.json` and `report.json` of run `stage17_acs_wage_microdata_20261119_r1`,
  read on 2026-11-23. No person row was read;
- in naics-embedder (`~/Projects/naics-embedder`) at `2b2029c`:
  `specs/naics-artifact-redesign-roadmap.md` (gates G1 to G6, and the decision that the
  economic chain ends at its Stage 3 with no adopted candidate) and
  `specs/naics-artifact-redesign.md` (Req 29, "Later panels").

naics-embedder has no wage panel spec at `2b2029c`. The roadmap resume of 2026-11-23 ruled
that this spec does not consume one: the section names it as the place that decides the
scores.

**Owner decisions (2026-11-23).**

| Id | Question | Decision |
| --- | --- | --- |
| Q1 | What may the selecting part choose? | "b": the panel's own settings and also which embedder candidate goes forward. A sealed part judges and is opened once |
| Q2 | Where is the split itself fixed? | "a": in naics-embedder's wage panel spec, under limits that this section sets |
| Q3 | The drafted assignment and conditions, shown in chat as W1 to W8 | Not corrected. The owner said "write the spec". The spec numbers them W1 to W9, because roles split out of the headline-rows condition. W9 (fixtures) is the chat's W8 |
| Q4 | Three texts say the file only judges (R8.1's owner paragraph, the `CLAUDE.md` Stage 17 paragraph and the retired Stage 17 spec's anti-goal). Record an exception for Q1, or rely on the section alone? | "a": record the exception in R8.1, R8.4 and `CLAUDE.md`, as the ITA exception was recorded |

**My calls.** Choices made while writing, which the owner has not ruled on, are marked
(my call). The proposals that the owner did not correct in Q3 are marked (proposal, Q3).

## Intent

naics-embedder's economic artifact gives NAICS codes coordinates that replace one-hot
encodings in later models. The Stage 17 file lets a person-level wage panel test those
coordinates inside a model with many covariates (Stage 17 spec, Intent). The protocol's
first rule is "no section, no score". So the file needs a section before any panel scores a
candidate on it.

Amended R8.4 says that the file "only judge[s] and never train[s]" and that its section
"states which part selects and which part judges". Section 1 could delegate its split to an
approved naics-embedder spec. No wage panel spec exists yet, so this section must state the
roles itself. It leaves the split, the regimes and the scores to that later spec.

**Success.** A naics-embedder session can write its wage panel spec against this section
alone. It knows which run and hashes to read, which rows count, what each part may do, what
must stay on this machine and what makes a read allowed.

## Goals, non-goals and anti-goals

**Goals.**

1. State the evidence: the run, its pin, the table hash and the Stage 19 minimum.
2. State the roles: which part selects, what it may select, and which part judges.
3. State the conditions this repository keeps, including the in-place read under R8.1.
4. Name naics-embedder's wage panel spec as the place that decides the split, the regimes
   and the scores, and state when a read becomes allowed.

**Non-goals.**

- The wage panel: its split, regimes, comparators, metrics, margin and decision. These
  belong to naics-embedder's wage panel spec (Stage 17 spec, Non-goals).
- A section for any other family. Stages 16, 23 and 25 write those.
- Any change to R8.4's text beyond the exception sentence of Q4. Any change to the Stage 19
  minimum or to a Stage 17 bundle.
- Any source, test or data change, and any full-data command.

**Anti-goals.** The design fails, even if it merges, when it:

- lets a person row, or a result for one person, leave this machine (R8.1);
- lets the file train, build a curriculum or mine examples for an embedder (R8.4);
- forbids the panel's own regression fit by treating it as training;
- restates the split or the regimes, so that two repositories hold copies;
- allows a read before the wage panel spec exists and is named here;
- adds a second size gate beside the V9 minimum.

## Approaches

The approach for the whole section follows Section 1 (protocol, Approaches: thin
delegation). Two choices were open.

**Q1: what the selecting part may choose.**

| Option | What it does | Trade-off | Decision |
| --- | --- | --- | --- |
| a. Panel settings only | The selecting part tunes the panel itself. Embedder candidates are chosen elsewhere. | Strictest reading of "only judge". The panel can never choose a winner. | Rejected |
| b. Panel settings and the candidate | The selecting part also chooses which candidate goes forward. A sealed part judges, opened once. | Matches naics-embedder's growth panel (validation selects, outer sets judge) and R8.4's "split first". | **Chosen** (Q1) |

**Q2: where the split is fixed.**

| Option | What it does | Trade-off | Decision |
| --- | --- | --- | --- |
| a. Panel spec, under limits here | naics-embedder's wage panel spec fixes the split. This section sets its limits and holds all reads until that spec is named here. | One home for the split. The file stays unscored until the spec exists. | **Chosen** (Q2) |
| b. Here | This section fixes a split, such as 2023 selects and 2024 judges. | Concrete now, but it fixes panel design here. A year split cannot express the held-out regime, which leaves out whole categories. | Rejected |

## The section

On approval, the text between the two rules below goes into `specs/evaluation-protocol.md`
after Section 1 and before "Families with no section". If Stage 16's section merges first,
the builder renumbers this section and its condition IDs stay unchanged (my call).

----

## Section 2: ACS wage microdata

The ACS wage microdata are a person-level analysis file, not a target family (source spec
R7.2). The rules for every family apply to the file as they apply to a family (my call).
Stage 17 built the file and Stage 19 set its minimum. The design is in
`specs/completed/acs-wage-protocol-section.md`.

### Evidence

A read uses the first run (my call). The replay
`stage17_acs_wage_microdata_20261119_r1_replay` has a byte-identical Parquet and
`report.json`, but its own pin. The Stage 19 decision read the first run.

| Item | Value |
| --- | --- |
| Run | `stage17_acs_wage_microdata_20261119_r1` in `data/derived/acs/wage-microdata/` |
| Detached pin (SHA-256 of `outputs.json`) | `6cb253e2e5c2e48a5b31d2790a0378636d3b6ef9197cfb2d33cca2813ac201d1` |
| `acs_wage_persons.parquet` | 3,035,086 rows, SHA-256 `a94471492dc91aebe3a3436e8d738d399520791b0eace6f01a719fad10fd5ff2` |
| `report.json` | SHA-256 `32ad9b698c9b940760d74eec0ae3b234abd14ba4c08ca07f04770a8f11e413bd` |
| Headline rows | 1,278,878 rows with `flag_headline = true`: 639,002 in 2023 and 639,876 in 2024, over 233 categories in each year (Stage 17 finding) |
| Count gate | Minimum 400 headline rows for each category (`INDNAICS`) in each year, applied to `headline_rows` of each `categories` entry of `report.json`, keyed by `INDNAICS` and `YEAR` ([V9 ACS wage decision](findings/v9-acs-wage-minimum-earners.md)) |
| Rows that meet the gate | 2023: 183 of 233 categories, 626,564 headline rows (98.05%). 2024: 178 of 233 categories, 625,828 headline rows (97.80%) |
| Depth of the join node | 262,711 headline rows (20.5%) join at a six-digit node. The rest join at sector, subsector, industry-group or five-digit nodes (`report.json`, `node_levels`) |

The `INDNAICS` strings in `report.json` and in the file carry space padding. A reader
matches on the delivered strings.

### Assignment

The file has a **selecting part** and a **judging part** *(owner, Q1, 2026-11-23)*.

- The selecting part chooses the panel's own settings and which embedder candidate goes
  forward. This is the exception that R8.1 and R8.4 record *(owner, Q4, 2026-11-23)*.
- The judging part is sealed. It judges and is opened once.

naics-embedder's wage panel spec, when the owner names it in this section (W7), decides
*(owner, Q2, 2026-11-23)*:

- the split into the two parts, within W4;
- the regimes, such as a seen regime and a held-out regime;
- the comparators, the metrics, the headline, the reference, the margin and the decision
  rule;
- how rows of mixed depth are scored, and how a category that meets the gate in one year
  but not the other is handled;
- the logging of reads and the one opening of the judging part.

The Stage 17 spec's "Handoff to naics-embedder" lists recommendations for that spec. They
bind nothing.

### Conditions this repository keeps

- **W1. Check the hashes before the first read.** The reader computes the SHA-256 of
  `outputs.json`, `acs_wage_persons.parquet` and `report.json` and compares each with the
  Evidence table. `report.json` is checked because W4's gate reads its counts (my call). A mismatch stops the read. This comparison is the required form. `verify` is not
  required, because it refuses both runs after any change to a file in
  `acs_wage_inputs.SOFTWARE_FILES` (my call, as Section 1's C1).
- **W2. Read in place (R8.1).** The read runs on the machine that built the file, this Mac.
  Person rows and every result for a single person stay on that machine and out of every
  repository. Such results include predictions, residuals, folds, cached features and
  debug output. Only aggregate scores and decisions leave it.
- **W3. Publish scores, not wage tables** (proposal, Q3). A published result holds no mean
  wage, wage quantile or wage distribution of a category. Such a table is evaluation data
  that could later tune a model (R8.4). The Stage 19 decision follows the same rule.
- **W4. Headline rows and the gate.** Every row that the panel reads, to fit or to score,
  has `flag_headline = true`. A headline score counts only rows whose category has at
  least 400 headline rows in the row's own year. Category-years below 400 stay out of the
  headline score. A panel may report them apart, labeled as below the gate (proposal, Q3).
  Whether rows of a category-year below 400 may enter a fit is the panel spec's choice
  (Assignment), because the gate is a floor for headline use, not for fitting (my call). The count gate is the only size gate. The Stage 19 decision found
  categories where the count gate and the category's own SE disagree: 23 in 2023 and 29 in
  2024 (its section 6). These are a disclosure, not a second gate, because the per-category
  SEs stay on this machine and are not pinned evidence (proposal, Q3). The 31 categories
  that share a node have no headline rows and are never scored.
- **W5. Roles.**
  - The split is fixed and recorded in the wage panel spec before any wage value of the
    file is read for the panel, and it never moves after a read.
  - The selecting part selects. The judging part judges. No row of the judging part is read
    for selection.
  - "Opened once" means one logged opening. Several candidates and seeds may be scored
    inside it. A second opening needs a recorded reason.
  - Only the judging part is reported as evaluation. A selecting-part score may be
    published as a development measurement. It is labeled as not evaluation, and W3 and
    W6 apply to it.
  - **Fitting the panel's own regression is part of judging, not training** (my call). The
    panel fits its covariates and a candidate's coordinates to wages, and that fit belongs
    to the judging instrument. No row trains an embedder, builds a curriculum or mines
    hard negatives.
- **W6. State the universe with every published score.** The statement names the run and
  the pin, and says at least this:
  - The rows are ACS 2023–2024 one-year earners from IPUMS USA. Headline rows are
    employees who work full time for the full year and have no allocated value in the nine
    headline fields.
  - The outcome is the natural log of annual wage income in constant 2010 dollars.
    Top-coded wages stay in the headline.
  - Industry is a Census category, joined at the deepest node that holds exactly its
    industries. The node depth is mixed. Mixture categories have approximate coordinates.
  - The minimum of 400 headline rows applies to each category in each year.
  - IPUMS USA is cited as its terms require (R8.2).
- **W7. No read until the owner names the panel spec here** (proposal, Q3). A read is
  allowed only after the owner amends this section to name naics-embedder's approved wage
  panel spec and the commit read. Until then the file is not scored. After that, the
  assignment is to that spec as its owner amends it, not to a frozen copy, as in Section 1
  (my call). The conditions here bind every version. If a later version conflicts with a
  condition, the condition governs until the owner amends this section. W5 still fixes the
  split once a read has happened. A new bundle, such as a
  rebuild or a file with ACS 2025, also needs an amendment of the Evidence table before
  any read of it.
- **W8. No candidate trained on ACS 2023–2024 is judged on this file.** This is the
  Stage 17 spec's Handoff ("Relatedness") and naics-embedder's split Req 23.
- **W9. Fixtures are not evidence.** A score from fixture tables shows software readiness.
  It is never reported as a result.

### What this repository does not decide

The split, the regimes, the scores, their intervals, the margin and the adoption decision.
It also does not check naics-embedder's selection log. That repository's own rules guard
the order of reads.

----

## Edits on approval

One docs commit applies these, with the section above. Edits 4 to 7 record the owner's
exception of Q4. The others are pointers.

1. **`specs/evaluation-protocol.md`, introduction.** "It has one section for each evidence
   family" gains "or analysis file". "No other family has a section yet" becomes a sentence
   that names Section 2 for the ACS wage microdata.
2. **`specs/evaluation-protocol.md`, "Families with no section".** No change to the list.
   The ACS wage microdata are not a family, so they were not in it.
3. **Source spec, Out of scope, "Evaluation protocol".** After "It covers the ITA text–code
   pairs", add: "Section 2 covers the ACS wage microdata. *(owner, 2026-11-23)*"
4. **Source spec, R8.4 owner paragraph** (Q4). Add, tagged *(owner, 2026-11-23)*: "One
   exception: the selecting part of the ACS wage microdata may select which embedder
   candidate goes forward. No row trains, builds a curriculum or mines examples. The
   section is [Section 2 of the evaluation protocol](evaluation-protocol.md)."
5. **Source spec, R8.1 owner paragraph** (Q4). "to judge an economic candidate of
   naics-embedder" becomes "to judge an economic candidate of naics-embedder or, on its
   selecting part, to select one", with the tag *(owner, 2026-11-23)* after the sentence.
6. **`CLAUDE.md`, Stage 17 paragraph** (Q4). "It only judges and never trains (R8.4)."
   gains the exception, as the Stage 10 paragraph's "One exception" line does. "No
   protocol section (O24) exists yet, so no panel result is claimed." becomes a sentence
   that points to Section 2 and says that no panel result is claimed until the owner names
   the panel spec there (W7).
7. **`README.md`, Stage 17 section** (Q4). "Under R8.4 the file only judges and never
   trains." gains the same exception. "No protocol section (O24) exists yet." becomes the
   same pointer.
8. **`specs/naics-evaluation-data-stage-24-findings.md`.** New. It records the owner
   decisions, the measured cost in sessions and what is not claimed.
9. **Roadmap.** Tick Stage 24 and add its completion note, as Stage 2's was added. Track H
   has no later stage, so the re-validation of the Rollout line finds nothing to change.
10. **This file.** Status becomes "COMPLETE (date)", and the file moves to
   `specs/completed/`.

Findings, retired specs and retired plans are records and are not edited.

## Constraints

- No source file, test or data file changes. The Stage 17 software hashes stay as recorded.
- No full-data command. The only data reads are the hash of `outputs.json`, the hash of
  `report.json` and its aggregate keys. No person row is read.
- The commit hook skips the test suites for changes under `specs/` and root-level Markdown.
  No flag is used to skip a hook.
- Before each commit, run `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`
  and stop if it prints anything.
- Stages 16, 23 and 25 also edit `specs/evaluation-protocol.md`. The second of them to merge
  resolves the conflict by hand, in the introduction and in the section numbers.

## Verification: observable outcomes

- [ ] The protocol on `main` has the section, between Section 1 and "Families with no
      section".
- [ ] The SHA-256 of the run's `outputs.json` equals the pin. The Parquet and
      `report.json` hashes in the Evidence table equal the values in that `outputs.json`.
- [ ] The row, headline, gate and node-depth counts equal `report.json`, the Stage 17
      finding and the V9 ACS wage decision.
- [ ] `CLAUDE.md`, `README.md` and the source spec point to the section.
- [ ] `git diff --stat` for the change lists only Markdown files.
- [ ] A reader can answer from the section alone: which run and hashes to read, which rows
      count, what each part may do, what stays on this machine, and whether a read is
      allowed yet.

## Left to the builder

- The exact wording of the pointer sentences, within the limits above.
- The section number, if Stage 16 merges first.

## Rollout

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 24 — on plan completion, tick the stage and re-validate later stages against what shipped.

Stage 24 has no plan. The owner's approval of this file stands in for plan completion, as it
did for Stage 2. The stage is ticked in the same PR as the edits above.
