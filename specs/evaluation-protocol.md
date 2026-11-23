# Evaluation protocol

> Next step: resume naics-embedder's roadmap
> `specs/naics-artifact-redesign-roadmap.md`, which re-reads its gates here.
> The pointer edits in "Edits on approval" were applied with the approval. No
> plan was needed, because the spec adds no code (my call).

Status: APPROVED (2026-11-18, owner: "Approve the spec"). Written 2026-11-18. Section 2
added with the owner's approval of its design (2026-11-23, owner: "Approve"). Sections 3
and 4 added with the owner's approval of their design (2026-11-23, owner: "Approve the
design"). Section 5 added with the owner's approval of its design (2026-11-23,
owner: "Approve"). Section 6 added with the owner's approval of its design (2026-11-23,
owner: "Approve the design").

This is the successor evaluation-protocol spec that the
[source spec](embedding-evaluation-data-spec.md) requires "before any embedder
is scored" (Out of scope, "Evaluation protocol"). It has one section for each
evidence family or analysis file. A family with no section here is not scored. The first
section covers the ITA text–code pairs. Section 2 covers the ACS wage microdata, a
person-level analysis file *(owner, 2026-11-23)*. Sections 3 and 4 cover ITA
co-ownership and the 2023 ITA area mix (roadmap Stage 16). Section 5 covers the
USAspending vendor links (roadmap Stage 23). Section 6 covers the TRI parent links
(roadmap Stage 25).

## Design provenance

This provenance, the Intent, the Goals, the Approaches and "Edits on approval"
are Section 1's. Section 2 has its design in
[acs-wage-protocol-section.md](completed/acs-wage-protocol-section.md). Sections 3
and 4 have theirs in
[completed/evaluation-protocol-ita-relatedness.md](completed/evaluation-protocol-ita-relatedness.md).
Section 5 has its design in
[completed/evaluation-protocol-usaspending-vendor-links.md](completed/evaluation-protocol-usaspending-vendor-links.md).
Section 6 has its design in
[completed/evaluation-protocol-tri-parent-links.md](completed/evaluation-protocol-tri-parent-links.md).

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
different bytes, so one run must be named). The independent reconcilers of the
[Stage 10 finding](findings/stage-10-ita-establishment-targets.md) also ran on
the first run only. *(owner, 2026-11-18)*

| Item | Value |
| --- | --- |
| Run | `stage10_ita_establishment_20261116_r1` in `data/derived/osha/establishment-targets/` |
| Detached pin (SHA-256 of `outputs.json`) | `e19b0d58f61f106c3994aa6fe51f4fb71244188145dd90f8cccaa8dc8a8b09df` |
| `ita_text_pairs.parquet` | 644,265 rows, SHA-256 `60aad7642961e70b987e9d3222d660147861458e12ac52d71d2739d2d21e1e1c` |
| `ita_text_pair_codes.parquet` | 771,971 rows, SHA-256 `c8084e4ad297e3f78391e035ebe51119b07982639ae4daf47f1d47caeb1f8916` |
| Headline pairs | 239,364 pairs with `flag_headline = true`. Of these, 527 have `flag_headline_codes_conflict = true` (Stage 10 finding, "Text–code pairs"). A reader's C2 filter gives these counts *(owner, 2026-11-18)* |
| Copied headline pairs | 221,176 of the 239,364 (92.4%) have `flag_copied_title_any` or `flag_copied_index_any`: 25,846 with the title flag and 213,683 with the index flag. They hold 11,920 distinct `description_key` values *(owner, 2026-11-18)* |
| Headline pairs not copied | 18,188, with 7,567 distinct `description_key` values. Of these, 329 have `flag_headline_codes_conflict = true`. Text→code's headline score rests on these pairs *(owner, 2026-11-18)* |
| Count gate | Minimum 1 on `n_headline_records` of pairs with `flag_headline` (V9 decision). The headline rule needs at least one eligible record, so every headline pair meets it |

The copied and not-copied counts come from one read-only count on the selected
run's `ita_text_pairs.parquet` on 2026-11-18. No finding records them. They are
counts only and contain no description text. They describe the evidence and set
no rule. The V9 count gate does not use the copied flags.

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
For co-ownership, Section 3 answers them. That spec is retired. It gets only
Section 3's dated pointer *(owner, 2026-11-23)*.

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

## Section 2: ACS wage microdata

The ACS wage microdata are a person-level analysis file, not a target family (source spec
R7.2). The rules for every family apply to the file as they apply to a family (my call).
Stage 17 built the file and Stage 19 set its minimum. The design is in
`specs/completed/acs-wage-protocol-section.md`. Its "Owner decisions" table holds Q1 to Q4
and the proposals marked (proposal, Q3). The owner approved the whole design on 2026-11-23
("Approve").

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

## Section 3: ITA co-ownership

Status: APPROVED (2026-11-23, owner: "Approve the design"). Design, decisions P4–P7
and measurements:
[completed/evaluation-protocol-ita-relatedness.md](completed/evaluation-protocol-ita-relatedness.md).

### Evidence

The R7.2 family "Co-ownership", built by Stage 10. For two NAICS 2022
industries a and b, the target value is J(a,b) / n(a): of the employers (EINs)
in industry a, the share that also operate in industry b in the same year,
2023 to 2025. A read uses the first run, the run that Section 1 reads (my call).

| Item | Value |
| --- | --- |
| Run | `stage10_ita_establishment_20261116_r1` in `data/derived/osha/establishment-targets/` |
| Detached pin (SHA-256 of `outputs.json`) | `e19b0d58f61f106c3994aa6fe51f4fb71244188145dd90f8cccaa8dc8a8b09df` |
| `ita_co_ownership.parquet` | 39,152 rows (directed cells), SHA-256 `ef823b0c5134556f6d522a45578202b645b2296f26e3e4ab76282bf37cde564a` |
| `co_ownership_marginals.parquet` | 991 rows (industries), SHA-256 `7b4a832573ddf3f737f4146e04580dba325dffbb62259ea864ef038c7661e893` |
| Employers | N = 155,436 EINs with an eligible record (Stage 10 finding, "Co-ownership"). 909 of the 991 industries appear in a target row (count of 2026-11-23) |
| Count gate | Minimum 1 on `n_unweighted` (J) in `ita_co_ownership.parquet` (V9 decision). Every published row meets it |
| Split, measured | Under naics-embedder's committed salt, 9,842 of the 19,576 co-owned industry pairs (50.3%) have one industry in each part. 5,159 have both in the sealed part (count of 2026-11-23) |

The split counts come from one read-only count on the selected run on
2026-11-23, at naics-embedder `2b2029c`. They describe the evidence and set no
rule. No other table of the bundle is part of a read. `co_ownership_support.parquet`
and the link table are not read.

### Assignment

For this family, naics-embedder's `specs/completed/relatedness-artifact.md`
decides:

- the split into a validation part and a sealed part, and the handling of
  mirror pairs. At `2b2029c` the unit is the anchor six-digit industry, from
  the code and a fixed salt alone;
- the null-model normalization and the choice of scores: the candidates, the
  relevance rule, the gain, the headline and every other report. At `2b2029c`
  a partner b is relevant to anchor a when J(a,b) ≥ 1, the gain is
  J(a,b) / m(b) with m from `n_multi_industry_employers`, and the headline is
  the mean NDCG@10 over anchors;
- the use of the marginals, including `n_employers_partial`, and of the
  padded-EIN sensitivity labels. At `2b2029c` it reads neither;
- the references, the margin and the decision rule;
- the logging of reads and the one opening of the sealed part.

The version read for this assignment is naics-embedder `2b2029c`. The
assignment is to that spec as its owner amends it, not to a frozen copy (my
call). The conditions below bind every version. If a later version conflicts
with a condition, the condition governs until the owner amends this section.

This assignment answers, for co-ownership, the places where the Stage 10 spec
defers to the protocol: its Out of scope line on embedding scoring, null-model
normalization, data splits and acceptance thresholds; its note that the
scoring protocol can use the partial-employer counts with n(a); and its Handoff
line on the counts and marginals for a null model. It also answers methodology
K6-Q1 by assignment. That spec is retired. It gets only a dated pointer to this
section, after its amendment of 2026-11-18 *(owner, 2026-11-23)*.

### Conditions this repository keeps

- **CO1. Check the pin before the first read.** The reader computes the
  SHA-256 of each of the two tables and compares it with the value above. A
  mismatch stops the read. `verify` is not required (as Section 1, C1).
- **CO2. Read the published cells as headline evidence.** Every row of
  `ita_co_ownership.parquet` meets the count gate. J is `n_unweighted`, which
  counts unreconstructed EINs only. A count that admits zero-padded EINs is a
  sensitivity. It never replaces J and never adds a pair.
- **CO3. Roles (G6).** The validation part selects, for naics-embedder's
  relatedness artifact only (my call: the scope that the relatedness spec, §7,
  asks for, as the Stage 10 amendment limited its exception to the text→code
  artifact). The sealed part judges and is opened once. No co-ownership row, and no quantity derived from one, enters
  training, curriculum construction or hard-negative mining. The split comes
  first, and a part depends on the industry code alone, so a rebuilt table
  keeps each industry in its part. Only the sealed part is reported as
  evaluation. This extends the Stage 10 amendment's selection exception to
  co-ownership, on the same basis: R8.4's second sentence, "A family used for
  tuning is split first, and only its held-out part is reported as
  evaluation." R8.4 itself is unchanged *(owner, 2026-11-23)*. As in Section 1,
  C3 (my calls):
  - "Opened once" means one logged opening. Several arms and seeds may be
    scored inside it. A second opening needs a recorded reason.
  - A validation-part score may be published as a development measurement. It
    is labeled as not evaluation, and CO5 applies to it.
- **CO4. Report the mirror pairs.** A pair whose industries fall in different
  parts is seen from the validation part through one end. Every published
  sealed score states the share of its relevant pairs that cross the parts. It
  also gives, labeled as a sensitivity, a sealed score that rests only on pairs
  with both industries in the sealed part. The headline and the decision rule
  are the relatedness spec's and do not change. How the restricted score is
  computed is also the relatedness spec's *(owner, 2026-11-23)*.
- **CO5. State the universe with every published score.** The statement names
  the run and the pin, and says at least this: ITA is a program-selected filing
  population and represents no wider set of establishments or firms. Codes are
  self-reported and unvalidated. Only native NAICS 2022 codes from filing years
  2023 to 2025 count, which drops 41.8% of the 2024 and 2025 records, so an
  employer's industry set can be partial and J can be undercounted. An EIN is a
  tax-filing entity, not a whole firm, so relations across a firm's EINs are
  missed. The filing rule can over-represent designated industries. n(a) pools
  presence over three years, and J needs both industries in the same year.
- **CO6. A new bundle needs an amendment.** A rebuild has a new pin. The owner
  amends the Evidence table before any read of it. A read of another table of
  the bundle also needs an amendment that adds its hash.
- **CO7. A family that measures the same relation never trains what
  co-ownership judges** (my call). TRI parent links are one
  (`specs/completed/tri-parent-links.md`, lines 705–706). Each later family's
  section says whether it is one.
- **CO8. Fixtures are not evidence.** A score from fixture tables shows
  software readiness. It is never reported as a result.

### What this repository does not decide

The scores, their intervals, the reference, the margin and the adoption
decision. It also does not check naics-embedder's selection log.

## Section 4: 2023 ITA area mix

Status: APPROVED (2026-11-23, owner: "Approve the design"). Design, decisions P4–P7
and measurements:
[completed/evaluation-protocol-ita-relatedness.md](completed/evaluation-protocol-ita-relatedness.md).

### Evidence

The R7.2 family "Area mix", built by Stage 6. For a county and a NAICS 2022
industry, the target value is the industry's share of the county's submitted
2023 records. A read uses the first build (my call: the replay's
`ita_area_mix.parquet` has equal values but different bytes).

| Item | Value |
| --- | --- |
| Run | `stage6_ita_area_mix_20261014_1000_csv` in `data/derived/targets/` |
| Detached pin (SHA-256 of `outputs.json`) | `084292b6835eb09ce27ecc4a3aef03a6f43bfe7b39b815665c29190a431e2473` |
| `ita_area_mix.parquet` | 126,958 rows (county × industry cells), SHA-256 `0d6ac274226434fc0fcf5b3f467baebe23be2c36695b83c1d24288b98edee604` |
| Support | 324,191 eligible 2023 records in 3,065 counties and 978 industries. The median cell holds one record (Stage 6 finding; methodology K5) |
| Count gate | Minimum 1 on `n_unweighted` in `ita_area_mix.parquet` (V9 decision). Every published row meets it |

No other table of the bundle is part of a read. The counties with eligible
records are the 3,065 counties with a cell. `county_denominators.parquet` has
four more counties, which have no eligible record.

### Assignment

The area mix has one role: it trains naics-embedder's relatedness embedding
(`specs/completed/relatedness-artifact.md`, §4.1 and §4.7, at `2b2029c`), and
only after R8.4 is amended to allow it (AM2). It has no split, no validation
part and no score. The relatedness spec decides how training uses it: the edges,
their weights and thresholds, and the model. The assignment is to that spec as
its owner amends it. The conditions below bind every version.

### Conditions this repository keeps

- **AM1. Check the pin before the first read**, as CO1, for the one table.
- **AM2. No training read before R8.4 allows it.** R8.4 says that benchmark
  tables are never training data. This section grants nothing under R8.4. A
  real read for training waits for the owner's separate R8.4 decision (G1)
  *(owner, 2026-11-23)*. Fixture tables may be read before it.
- **AM3. It never judges and never selects the relatedness embedding.** No
  score on the area mix is reported as an evaluation of it. No part of the area
  mix, and no held-out set of its counties or cells, selects its model,
  checkpoint or configuration. For any other embedder, the area mix has no role
  until the owner amends this section (my call; Rule 1).
- **AM4. A family that measures the same relation never judges what the area
  mix trains** (my call). The relatedness spec names one, the ACS workplace
  area mix (§4.1). Each later family's section says whether it is one.
- **AM5. State the universe with a trained artifact.** Its provenance names the
  run and the pin, and its description says at least this: ITA is a
  program-selected filing population. The cells count submitted 2023 records,
  duplicates included, with self-reported native NAICS 2022 codes and county
  assignments in the 2025 county frame, in the 50 states and DC. Most cells
  hold one record.
- **AM6. A new bundle needs an amendment**, as CO6.

### What this repository does not decide

The training use, the model and its selection, which read co-ownership's
validation part. The R8.4 decision is the owner's, apart from this section.

## Section 5: USAspending vendor links

Status: APPROVED (2026-11-23, owner: "Approve"). Design, decisions P10 and P11 and measurements:
[completed/evaluation-protocol-usaspending-vendor-links.md](completed/evaluation-protocol-usaspending-vendor-links.md).

### Evidence

The R7.2 family "Vendor links", built by Stage 14 and replayed by Stage 20. A cell
is an ordered pair (s, d) of NAICS 2022 national industries: s is the supplier
industry (the subcontractor's) and d is the buyer industry (the prime's). Each
cell has two rows. `supplier_share` is S(s,d) / n_sup(s): of the subcontractors
in s with an eligible pair, the share linked to a prime in d. `buyer_share` is
B(s,d) / n_buy(d): of the primes in d with an eligible pair, the share linked to
a subcontractor in s. `n_unweighted` is S(s,d) or B(s,d). Fiscal years 2024 to
2026 are pooled. A read uses the first run (my call: the replay's tables have the
same bytes, and the V9 decision and the reconciler read the first run).

| Item | Value |
| --- | --- |
| Run | `stage14_vendor_links_20261122_r2` in `data/derived/usaspending/vendor-links/` |
| Detached pin (SHA-256 of `outputs.json`) | `248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be` |
| `vendor_links.parquet` | 16,614 rows (8,307 cells, two rows each), SHA-256 `a1e22e7321b82df9a6db84348da087502f0424eb999c35e0679a326d30bddfbd` |
| `vendor_link_marginals.parquet` | 689 rows (industries), SHA-256 `33c269a035b2bf450692d6f5941ab649bfdc94348db2823e965f9cc92045fc0a` |
| Firms | 28,410 subcontractors in 686 industries and 2,215 primes in 195 industries, in eligible pairs (`report.json`; marginals, count of 2026-11-23) |
| Count gates | `supplier_share`: minimum 4 on `n_unweighted`, met by 2,315 of 8,307 rows. `buyer_share`: minimum 3, met by 2,234 of 8,307 rows. 1,785 cells keep both rows ([V9 USAspending decision](findings/v9-usaspending-minimum-counts.md)) |
| Diagonal | 88 cells have s = d. 47 `supplier_share` rows and 40 `buyer_share` rows of them meet their gates |
| Split, measured | Under naics-embedder's committed salt at `2b2029c`, the 689 industries split 339 validation and 350 sealed. 1,165 of the 2,268 kept off-diagonal `supplier_share` rows have one industry in each part (count of 2026-11-23) |

The diagonal and split counts come from one read-only count on the selected run
on 2026-11-23. They describe the evidence and set no rule. Every row carries
`size_gate_pending`, so a reader applies the gates from this table. No other
table of the bundle is part of a read.

### Assignment

The family **judges only** *(owner, P10, 2026-11-23)*. No part of it selects.
It counts in the consuming spec's decision through one opening, in which the
reference, the margin and the test all run *(owner, P11, 2026-11-23)*.

naics-embedder's relatedness spec `specs/completed/relatedness-artifact.md`, or
the spec to which it assigns the family, as the owner names it in this section
(VL4), decides within VL3:

- which of the two measures it reads, and whether its reports split the family,
  for example by its anchor rule and salt. A split only divides what the one
  opening reports;
- the null model and the choice of scores: the candidates, the relevance rule,
  the gain, the headline and every other report;
- the treatment of diagonal cells and of absent (zero) cells, which the bundle
  does not emit;
- the use of the marginals and of the intra-group sensitivity;
- the reference arms, the rule that picks the reference, the margin rule and the
  decision rule;
- the logging of the one opening.

At `2b2029c` the relatedness spec lists USAspending subawards as unassigned
(§4.1). Its panel reads co-ownership only and refuses a pair emitted in one
direction (§4.2), and vendor-link cells are directed. So the consuming spec may
be a new panel spec that the relatedness spec points to (my call). After the
owner names it, the assignment is to that spec as its owner amends it, not to a
frozen copy, as in Section 3 (my call). The conditions below bind every
version. If a later version conflicts with a condition, the condition governs
until the owner amends this section.

### Conditions this repository keeps

- **VL1. Check the pin before the first read.** The reader computes the SHA-256
  of `outputs.json` and of the two tables and compares each with the Evidence
  table. A mismatch stops the read. `verify` is not required (as Section 1, C1).
- **VL2. Headline evidence and the gates.** A row is headline evidence when its
  `n_unweighted` is at least its measure's minimum: 4 for `supplier_share` and 3
  for `buyer_share`. The two rows of a cell are gated apart. A headline score
  counts only headline rows. Rows below the gate may be reported apart, labeled
  as below the gate (my call, as Section 2, W4). `n_unweighted` excludes
  intra-group pairs. A count that admits them, such as the rows labeled
  `numerator:intra_group_sensitivity:true` or the marginals' `_including_intra_group`
  columns, is a sensitivity. It never replaces `n_unweighted` and never adds a
  cell. The 7 cells that exist only under that sensitivity are not published
  and are never scored.
- **VL3. Roles (P10).**
  - Every read judges. No row, part or score of the family selects a model,
    checkpoint, configuration or candidate.
  - Before it reads any target value of the family, the consuming spec fixes
    which measures it reads, its null model, its scores, its reference arms, the
    rule that picks the reference and the margin rule (my call).
  - **All at the opening (P11).** No part of the family is read before the
    opening, by any arm, and no candidate is tested on it before then. Inside the
    opening, the reference arms are scored first. The fixed rules then pick the
    reference and set the margin from those scores. Only then is a candidate
    scored, and no candidate result changes the reference or the margin.
  - The family is opened once. "Opened once" means one logged opening. Several
    arms and seeds may be scored inside it. A second opening needs a recorded
    reason. No development measurement is published (my call).
  - No row, and no quantity derived from one, enters training, curriculum
    construction or hard-negative mining. R8.4 is unchanged, and this role stays
    until the owner amends this section, whatever R8.4 later allows.
  - The role covers naics-embedder's relatedness artifact only. For any other
    embedder, the family has no role until the owner amends this section (my
    call; Rule 1).
- **VL4. No read until the owner names the consuming spec here.** A read is
  allowed only after the owner amends this section to name naics-embedder's spec
  that assigns the family, and the commit read (as Section 2, W7). Until then
  the family is not scored.
- **VL5. State the universe with every published score.** The statement names
  the run and the pin, and gives the `universe` text of the target rows. It also
  says at least this: the minimums are 4 for `supplier_share` and 3 for
  `buyer_share`, on counts pooled over fiscal years 2024 to 2026; one SAM.gov
  extract (`2026-10`) gives each firm one industry for the whole window; join
  coverage is 0.810 for primes and 0.662 for subcontractors (Stage 14 findings);
  FY2026 is short in the `2026-11-19` snapshot; and subaward reporting moved from
  FSRS.gov to SAM.gov on 2025-03-08, inside FY2025.
- **VL6. Same relation.** Vendor links measure a supplier-to-buyer relation. It
  differs from the relation of ITA co-ownership and TRI parent links, and intra-
  group pairs are excluded to keep it apart from ownership (Stage 14 spec,
  Limits). It also differs from the co-location that the area mixes measure. BEA
  input–output tables, which are not built, measure the same relation (Stage 2
  spec, Direction). So a BEA family never trains an embedding that the vendor
  links judge (my call, as CO7 and AM4).
- **VL7. A new bundle or another table needs an amendment.** A rebuild, a later
  snapshot or a new SAM.gov extract has a new pin. The owner amends the Evidence
  table before any read of it. A read of another table of the bundle also needs
  an amendment that adds its hash. `vendor_link_pairs.parquet` holds UEI pairs
  and stays on this machine.
- **VL8. Fixtures are not evidence.** A score from fixture tables shows software
  readiness. It is never reported as a result.

### What this repository does not decide

The measures read, the null model, the scores, their intervals, the reference,
the margin and the adoption decision. It also does not check naics-embedder's
log of the opening.

## Section 6: TRI parent links

Status: APPROVED (2026-11-23, owner: "Approve the design"). Design, decisions P8, P9, P12
and P13 and measurements:
[completed/evaluation-protocol-tri-parent-links.md](completed/evaluation-protocol-tri-parent-links.md).

### Evidence

The family "TRI parent links" of `specs/uncovered-uses-evidence-sources.md`, built
by roadmap Stage 5 (outcome O7). For two NAICS 2022 industries a and b, the
target value `owner_share` is J(a,b) / n(a): of the owners with an eligible TRI
facility in industry a, the share that also operate one in industry b in the
same reporting year, 2022 to 2024. An owner is EPA's standardized U.S. parent, or
the facility itself when it reports none. A read uses the first run. The
replay's tables have the same bytes, so the run is named for its pin only (my
call).

| Item | Value |
| --- | --- |
| Run | `stage5_tri_parent_links_20261121_r1` in `data/derived/epa_tri/parent-links/` |
| Detached pin (SHA-256 of `outputs.json`) | `65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b` |
| `tri_parent_links.parquet` | 14,204 rows (directed cells, 7,102 industry pairs), SHA-256 `331392fe80e8688cbd0230e7fb6abe44d06d7d047851fbedf0a84462e60efab5` |
| `tri_parent_link_marginals.parquet` | 405 rows (industries), SHA-256 `fe0e83e5c371a52ee4d80063de5e358f00aa941aadc6fd9afdafbef89f2bd261` |
| Owners | 8,684 headline owners (Stage 5 findings, "Counts"). 359 of the 405 industries appear in a target row |
| Count gate | Minimum 1 on `n_unweighted` (J) in `tri_parent_links.parquet` ([V9 TRI decision](findings/v9-tri-minimum-counts.md)). Every published row meets it |
| Split, measured | Under naics-embedder's committed salt, 3,557 of the 7,102 pairs (50.1%) have one industry in each part. 2,048 have both in the sealed part (count of 2026-11-23) |
| Overlap with Section 3 | 2,497 of the 7,102 TRI pairs are also co-owned pairs in `ita_co_ownership.parquet`, and 354 of the 359 industries also appear there (count of 2026-11-23) |

The split and overlap counts come from one read-only count on the selected runs
on 2026-11-23, at naics-embedder `2b2029c`. They describe the evidence and set no
rule. No other table of the bundle is part of a read.

### Assignment

For this family, naics-embedder's `specs/completed/relatedness-artifact.md`
decides what it decides for co-ownership (Section 3):

- the split into a validation part and a sealed part, and the handling of
  mirror pairs. At `2b2029c`, TRI uses the same rule and salt as co-ownership,
  so an industry is in the same part in both families (§4.1);
- the null-model normalization and the choice of scores: the candidates, the
  relevance rule, the gain, the headline, the treatment of absent (zero) cells
  and every other report;
- the use of the marginals, including `n_multi_industry_owners` and
  `n_owners_partial`, and of the D&B-key and federal sensitivity labels;
- the references, TRI's own margin record, the margin and the decision rule;
- the logging of reads and the one opening of the sealed part.

The version read for this assignment is naics-embedder `2b2029c`. There TRI has
no role yet. That spec admits TRI as a second judge only through its own
amendment, made before the sealed opening (§4.1). The assignment is to that spec
as its owner amends it, not to a frozen copy (my call). The conditions below
bind every version. If a later version conflicts with a condition, the
condition governs until the owner amends this section.

This assignment answers, for TRI, the places where the TRI spec and the V9 TRI
decision defer to the protocol: the decision's "Not claimed" line on scoring,
null models, splits and absent cells, and the TRI spec's Handoff line on the
counts and marginals for a null model and the two sensitivity labels. The
universe statement and the E8 time basis of that line enter TR6.

### Conditions this repository keeps

- **TR1. Check the pin before the first read.** The reader computes the SHA-256
  of each of the two tables and compares it with the value above. A mismatch
  stops the read. `verify` is not required (as Section 1, C1).
- **TR2. Read the published cells as headline evidence.** Every row of
  `tri_parent_links.parquet` meets the count gate. J is `n_unweighted`, which
  counts owners under EPA's standardized parent name, with federal facilities
  out. The count under the D&B key and the count with federal facilities in are
  sensitivities. They never replace J and never add a pair. 8,050 rows carry the
  D&B label and 40 the federal label.
- **TR3. Roles.** The validation part selects, for naics-embedder's relatedness
  artifact only *(owner, P8, 2026-11-23)*. The sealed part judges and is opened
  once. No TRI row, and no quantity derived from one, enters training,
  curriculum construction or hard-negative mining. The split comes first, and a
  part depends on the industry code alone. Only the sealed part is reported as
  evaluation. This extends CO3's selection exception to TRI, on the same basis:
  R8.4's second sentence. R8.4 itself is unchanged. As in CO3:
  - "Opened once" means one logged opening. Several arms and seeds may be
    scored inside it. A second opening needs a recorded reason.
  - A validation-part score may be published as a development measurement. It
    is labeled as not evaluation, and TR6 applies to it.
- **TR4. Report the mirror pairs**, as CO4. Every published sealed score states
  the share of its relevant pairs that cross the parts. It also gives, labeled
  as a sensitivity, a sealed score that rests only on pairs with both industries
  in the sealed part. How the restricted score is computed is the relatedness
  spec's.
- **TR5. Neither TRI nor co-ownership trains what the other judges.** They
  measure close relations (`specs/completed/tri-parent-links.md`, lines
  705–706; CO7). TRI does not measure the relation of the area mix, so AM4 does
  not apply to it (my call). The USAspending vendor links measure another
  relation (Section 5, VL6).
- **TR6. State the universe with every published score.** The statement names
  the run and the pin, and says at least this: TRI is a program-selected
  population of facilities that meet its reporting criteria, mostly industrial.
  It is not a frame of establishments or firms, and its pairs cover 359
  industries. Codes are self-reported primary NAICS 2022 codes, one per
  facility, from EPA's complete files for reporting years 2022 to 2024, processed
  as of 2025-11-05. An owner is EPA's standardized U.S. parent as of that
  snapshot, not as of each reporting year (E8), or the facility itself when it
  reports none. EPA's standardization can split one parent or merge two, and
  this project cannot measure either. Federal facilities are out. n(a) pools
  presence over three years, and J needs both industries in the same year.
  About a third of the pairs (2,497 of 7,102) are also co-owned pairs in
  Section 3, so a TRI score is not independent of a co-ownership score.
- **TR7. A new bundle needs an amendment.** A new snapshot or rebuild has a new
  pin. The owner amends the Evidence table before any read of it. A read of
  another table of the bundle also needs an amendment that adds its hash.
- **TR8. No read until the owner names the admitting commit here**
  *(owner, P12, 2026-11-23)*. A real read is allowed only after the owner amends this section
  to name the relatedness spec's commit that admits TRI as a judge. Fixture
  tables may be read before it.
- **TR9. Fixtures are not evidence.** A score from fixture tables shows
  software readiness. It is never reported as a result.

### What this repository does not decide

The scores, their intervals, the reference, the margin and the adoption
decision. It also does not check naics-embedder's selection log.

## Families with no section

These are not scored until a section exists: every other ACS family, every CPS
family, and each new family of
`specs/uncovered-uses-evidence-sources.md` other than the USAspending vendor
links and the TRI parent links. The vendor links have Section 5 and stay
unscored until the owner names their consuming spec there (VL4). The TRI parent
links have Section 6 and stay unscored until the owner names there the
relatedness spec's commit that admits them (TR8). For a directional relatedness
share, Section 3 answers the open design questions, null-model normalization
and the choice of scores, by assignment to the consuming spec.

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
- [ ] The headline-pair and conflict counts in the Evidence table equal the
      Stage 10 finding's counts and a count on the selected run's table.
- [ ] The copied and not-copied counts equal a count on the selected run's
      table, and the two sets of pairs and of keys sum to 239,364 and 19,487.
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
  through Section 1. With Sections 3 and 4, it opens for co-ownership and the
  2023 area mix, and G6 opens under CO3 and CO4 *(Stage 16)*. Section 5 opens
  nothing yet: G4 opens for the USAspending vendor links only after the owner
  names their consuming spec there (VL4) *(Stage 23)*.
- **TRI parent links.** An amendment of naics-embedder's relatedness spec admits
  TRI as a second judge (its §4.1) and cites Section 6. Under TR8 the owner then
  names that commit in Section 6 before any real read. G6's limits extend to TRI
  under TR3 *(Stage 25)*.
- **Later families.** Each adds a section here through its own design session,
  after its build and its count gate.
- **R8.4.** A separate owner decision, after naics-embedder's relatedness spec
  names the families that train. That spec now names one, the 2023 ITA area
  mix. G1 stays closed until the owner decides (Section 4, AM2).
