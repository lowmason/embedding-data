# ITA establishment targets

**Status: COMPLETE (2026-11-18)** — implemented by [plan 11](../plans/completed/11-ita-establishment-targets.md); measured runs in the [Stage 10 finding](../findings/stage-10-ita-establishment-targets.md).

The owner approved the headline window, the index-entry flag, the co-ownership
measure, the build approach and the Stage 9 write coordination on 2026-11-13.
The owner then approved this written specification, including every call
marked "My call", on 2026-11-13. At that approval, Stage 10 implementation and measured
acceptance remained planned.

**Amendment: selection on the validation part (owner, 2026-11-18).** The
anti-goal against model selection now has one exception. Checkpoint and
candidate selection for the text→code artifact of `naics-embedder` may read the
validation part of the headline text–code pairs. Its basis is the second
sentence of R8.4: "A family used for tuning is split first, and only its
held-out part is reported as evaluation." R8.4 itself is unchanged. The limits:

- The split comes first. It groups pairs by `description_key`, so no normalized
  description is in both parts. `naics-embedder` defines it in its
  `specs/text-to-code-ita-panel.md`.
- Only the sealed part is reported as evaluation. It is read once, to judge.
- No pair and no ITA description enters training, curriculum construction or
  hard-negative mining.
- The exception covers the text–code pair tables only. Co-ownership and the
  link table keep the full exclusion.
- A real read still waits for the successor evaluation-protocol specification
  (source spec, Out of scope).

**Pointer (owner, 2026-11-23).** Section 3 of
[the evaluation protocol](../evaluation-protocol.md) extends this exception to the
validation part of co-ownership, for the relatedness artifact of `naics-embedder`
only, under its conditions CO3 and CO4. The link table keeps the full exclusion.

## Scope and governing contracts

Stage 10 of [the roadmap](embedding-evaluation-data-spec-roadmap.md)
implements R2.6, R2.7 and the text–code pair and co-ownership rows of R7.2 in
[the source spec](../embedding-evaluation-data-spec.md). R7.1, R7.4, R8 and R9
govern outputs, provenance, disclosure, leakage and offline operation. The
adopted V1–V3 rules in
[the V1–V3 finding](../findings/v1-v3-ita-verification.md) govern text keys,
employer keys and linkage.

Stage 10 produces three products from data that is already on disk:

1. **Establishment-link table.** It links establishment records across filing
   years under the adopted R2.7 rules. It is a standalone product. Neither
   target in this stage reads it.
2. **Text–code pair tables.** They pair each employer's own industry text with
   every candidate NAICS 2022 code path. Pairs are deduplicated on employer and
   normalized description. Under R7.4, ITA pairs are separate tables, not
   `targets-v1` rows.
3. **Co-ownership target.** It measures, for two NAICS 2022 industries, how
   often one employer (EIN) operates establishments in both. It is the only
   `targets-v1` family in this stage.

### Owner decisions (2026-11-13)

- **Headline window: 2023–2025 native-2022 records, pooled (option B).** The
  Core principle excludes crosswalked codes from headline targets. Every
  2016–2022 record carries a 2012 code crosswalked to 2022, as do about 40% of
  2024–2025 records. Only 823,481 records carry a native 2022 code: 358,294 in
  2023, 222,166 in 2024 and 243,021 in 2025. A pair's headline codes come only
  from its native records. An EIN co-owns two industries only when it filed
  native records in both in the same year.
- **Index-entry copy flag (option A).** OSHA's
  [ITA Data Users Guide](https://www.osha.gov/sites/default/files/ITA_data_users_guide.pdf)
  (January 2025, page 6) states that the ITA collects "a text industry
  description (often one of the NAICS index titles)". The adopted copied-text
  flag compares only official titles at levels 2–6. Stage 10 adds a flag for
  identity with official Census NAICS index entries and amends R2.6 (see
  [Source spec amendment](#source-spec-amendment)).
- **Co-ownership measure: directional shares (option 1).** The value is
  `J(a,b) / n(a)`: of the employers that operate in industry a, the share that
  also operate in industry b in the same year. Counts and marginals ship beside
  the target, so a later null-model normalization needs no rebuild.
- **Build approach: one standalone command group and one bundle (approach 1).**
  This follows the Stage 8 and Stage 9 pattern (see [Approaches](#approaches)).
- **Stage 9 coordination: go-ahead per write (option A).** The plan asks the
  owner before each write to the production data root (see
  [Host rule and Stage 9 coordination](#host-rule-and-stage-9-coordination)).

### Accepted proposals (owner did not correct, 2026-11-13)

- The pair tables cover all 3,206,055 source records. Each record belongs to
  exactly one pair.
- Pairs are keyed by employer key and description key across all ten years,
  as R2.6 states. Each pair lists every code observed under it.
- When a pair has more than one headline code, it keeps all of them with a
  conflict flag. It never picks one.
- A record with an unknown employer is its own pair, flagged, and is never
  merged.
- Empty and placeholder pairs stay in the table but are not headline pairs.
  Copied-text flags stay as flags. The successor scoring protocol decides how
  to use them (methodology K6-Q2).
- Headline co-ownership uses unreconstructed EINs only. Zero-padded EINs give a
  separate sensitivity count. Company names never establish co-ownership.
- Links cover each consecutive year pair and 2023→2025, with explicit
  conflict handling and no multi-year chains.
- Stage 10 reads the pinned Stage 4 bundle. It needs no Stage 5 geography and
  no Stage 6 county assignment.

### Out of scope

- Embedding scoring, null-model normalization of co-ownership, data splits and
  acceptance thresholds: the successor evaluation-protocol specification.
- Probabilistic record linkage (methodology K6-Q3) and persistent establishment
  identifiers across more than two years.
- Crosswalk-included co-ownership variants and pre-2023 headline products.
- Near-copy detection of titles or index entries (only exact normalized
  identity is flagged).
- V9 minimum cell counts and complete eight-family V12: Stage 13.
- Any change to Stage 2–9 code, bundles, findings or raw files.
- Any embedder training, curriculum, hard-negative mining or model-selection
  use (R8.4). The one exception is selection on the validation part of the
  text–code pairs. *(owner, amendment, 2026-11-18)*

## Intent

`naics-embedder` is built to respect the NAICS tree. These products test it
against observed evidence instead:

- **Text–code pairs** test whether an embedding places an employer's own
  description of its industry near the code the employer reported. Each pair
  carries full 2022 code paths, so the scoring protocol can score it at every
  level. Descriptions are often coarser than codes.
- **Co-ownership** tests whether industries that one owner operates together
  sit close together. Two industries can be far apart in the tree but share
  owners.
- **The link table** discharges R2.7. It makes cross-year establishment
  identity available to later work with explicit confidence states.

The pair table is worth little if it rewards recall of taxonomy text. ITA
descriptions repeat heavily. The 3.2 million records hold only 49,575 distinct
original strings and 29,067 distinct normalized keys. OSHA says the text is
often a NAICS index title. The copied-text flags let the scoring protocol
separate independent text from taxonomy text.

Anti-goals. The design fails, even if it runs, when it:

- Counts copied taxonomy text as independent employer text without a flag.
- Lets a crosswalked or unresolved code enter a headline product.
- Treats a company-name match as co-ownership.
- Picks one code when a pair or record has several possibilities.
- Confirms a link that the adopted R2.7 rule does not confirm.
- Edits a frozen module or an earlier stage's artifact.
- Lets any table feed embedder training, or lets any table feed model
  selection outside the validation part of the text–code pairs. *(owner,
  amendment, 2026-11-18)*

## Approaches

| Approach | What it does | Trade-off | Decision |
| --- | --- | --- | --- |
| 1. Standalone command group, one bundle | New `python -m embedding_data.<module>` group with its own acquisition, build, verify and compare commands. New modules import the reused ones. | Matches Stages 8 and 9. Leaves every frozen module untouched. | **Chosen** |
| 2. New commands in Stage 6's `targets` group | Reuses the existing CLI wiring. | Edits `targets_cli.py` and `cli.py`. Stage 6 records both in its software identity, and Stage 8's D5 rule pins `cli.py`. Their verifiers would fail. | Rejected |
| 3. Three commands and three bundles | Links, pairs and co-ownership each get a run. | Better isolation, but the selection, provenance and verification code exists three times. Pairs and co-ownership read the same keyed source. No consumer needs the split. | Rejected |

## Selected inputs and trust boundary

### Inputs

| Input | Identity | Use |
| --- | --- | --- |
| Stage 4 codes bundle | `stage4_v11_20261013_r2`, detached `outputs.json` SHA-256 `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` | `ita_300a_canonical.parquet` (38 columns), `code_paths.parquet`, `naics_nodes.parquet` |
| Stage 2 source summary | Cited by the Stage 4 bundle's `inputs.json` | Source parity and raw citations |
| NAICS title originals | `references/naics/*_NAICS_Structure.xls(x)`, already manifest-recorded (Stage 3) | Copied-title flags through `ita_references.read_titles` |
| NAICS index originals | New. Census index files for 2012, 2017 and 2022 | Copied-index flags |

`build` takes the codes run ID and its detached pin as explicit arguments, as
Stages 8 and 9 do. A different codes run needs its own pin.

### Selection

**My call:** Stage 10 uses a codes-only selector in a new module. It
authenticates the detached codes pin, verifies the bundle inventory, verifies
every raw citation with `manifest.entry_for`, and checks Stage 2 source parity
against the canonical table. It reuses public checks from `target_io`,
`manifest`, `code_build.check_source` and `target_inputs.require_source_parity`.
It does not call `target_inputs.select`, because that function also requires a
Stage 5 geography run, which Stage 10 does not consume.

### Reused interfaces

Stage 10 imports these and never edits them:

- `ita_verification.normalize_key`, `ein_key`, `zip_key`, `with_keys`,
  `PLACEHOLDERS`, `unique_ids` and `link_report` (Stage 3).
- `ita_references.read_titles` (Stage 3).
- `ita_area_mix.eligible_industry()` (Stage 6). Stage 6 and Stage 10 then use
  one definition of a headline industry.
- `target_contract.write_targets`, `validate_targets`, `TARGET_SCHEMA` and
  `TARGET_KEY_COLUMNS` (Stage 6).
- `tests.target_fixtures` raw-to-target V12 seam (Stage 6).

### Frozen modules

Stage 6 records the hashes of 26 preparation modules and five target modules
as its software identity (`ita_assignment_prepare.FROZEN_MODULES` and
`TARGET_MODULES`). Stages 7–9 record their own software files, and Stage 8's D5
decision pins `cli.py`. Stage 10 adds new modules only. It does not edit any
module in those lists, `cli.py`, `code_references.py` or any test file that an
earlier stage hashes. If the plan finds that a reused function cannot serve
unchanged, it stops and asks the owner.

### What Stage 10 does not consume

- Stage 5 geography and Stage 6 county assignments. No product here has a
  geographic unit.
- Stage 7–9 IPUMS artifacts.
- No upstream builder runs. Stage 10 never rebuilds the source summary, the
  Stage 4 bundle or any verification artifact.

## NAICS index references

### Acquisition

Register three new public originals, one per vintage: the official Census
NAICS index files for 2012, 2017 and 2022. The plan's acquisition task fixes
the exact official URLs, filenames and expected entry counts after it inspects
the actual originals. Census refused automated page requests during this
design session. The Stage 4 acquisition client did download census.gov files,
so the plan must confirm which path works.

- `acquire-references` downloads only missing originals. It is the only
  network command in this stage. It uses the existing browser user agent.
- `import-reference KIND FILE` imports exact original bytes that the owner
  downloaded by hand. It records the import time as a flagged proxy.
- Originals go to `raw/references/naics/` under their official names, beside
  the structure files. Each gets a manifest entry with SHA-256, size, source
  URL and retrieval time.
- Existing originals are never re-downloaded or replaced. A present but
  unrecorded original stops the command.

### Parsing

The parser returns `vintage: Int64, code: String, entry: String`. It keeps
every official row, including entries that share text across codes.

The parser fails loudly on:

- An ambiguous or unexpected header.
- An empty code or an empty entry.
- A code that is neither a six-digit leaf of that vintage's official structure
  nor the exact cross-reference marker `******`.
- An entry count or a cross-reference count that differs from its registered
  expected count.

It never substitutes a local lookup or a partial file.

Each official index file ends with 25 cross-reference rows whose code is
`******`, such as "Wholesale -- see type of product". The parser keeps them
with the delivered code and counts them. Their entries are official index
entries, so they take part in the copied-index flags. Every other row is a
six-digit leaf of its own vintage. *(owner, plan 11, 2026-11-14)*

### Index keys

An index key is `normalize_key(entry)`. One key can belong to several codes.
The flags compare keys only. They do not use the index codes to infer or
correct a record's code.

## Text–code pair tables

### Record keys

Apply `ita_verification.with_keys` to the canonical table's first 24 columns,
which are the Stage 2 summary columns. That reproduces the Stage 3 semantics
exactly. Each record then has:

- `description_key`: NFKC, Unicode casefold, collapsed and trimmed whitespace,
  with punctuation kept.
- `employer_key`: `ein:<ein_key>` for a usable EIN (including padded),
  else `company:<company_key>`, else null.
- The existing `flag_empty`, `flag_placeholder`, `flag_ein_padded` and
  `flag_suspected_mojibake`.

Record copied-text flags:

| Flag | True when the description key equals |
| --- | --- |
| `flag_copied_title_any` | an official 2012, 2017 or 2022 title key at levels 2–6 |
| `flag_copied_title_native` | a title key of the record's own `naics_year`, or null when `naics_year` is null |
| `flag_copied_index_any` | an official 2012, 2017 or 2022 index key |
| `flag_copied_index_native` | an index key of the record's own `naics_year`, or null when `naics_year` is null |

An empty key never matches a title or index key.

### Pair identity

- A record with a non-null `employer_key` belongs to the pair
  `(employer_key, description_key)`. This pools all ten years.
- A record with a null `employer_key` is its own pair, identified by its
  source row. It carries `flag_employer_unknown`.
- `pair_id` is a deterministic function of the pair key and its kind.
  **My call:** a SHA-256 of a versioned, length-prefixed encoding. It contains
  no EIN or company text in clear form.

Every source record belongs to exactly one pair. The sum of `n_records` over
all pairs is 3,206,055.

Read-only recon on the selected tables (not acceptance values): 537,857
known-employer groups and 106,408 unknown-employer records, so about 644,265
pairs. 239,364 known-employer, nonempty, nonplaceholder groups have native
2023–2025 records.

### Headline rule

A pair is a headline pair (`flag_headline = true`) when all of these hold:

1. At least one of its records passes `eligible_industry()`, that is, a native
   2022 code with a non-null node and no crosswalk, ambiguity or unresolved
   flag (these records all fall in 2023–2025).
2. Its description key is not empty and not a placeholder.
3. Its employer is known.

The third condition is **my call**. An unknown-employer record cannot be
deduplicated, so it cannot be protected against multi-unit stamping.

A headline pair's headline codes are the codes of its eligible records only.
Its crosswalked and unresolved records stay in the table as context. If a
headline pair has more than one distinct headline node, `flag_headline_codes_conflict`
is true and every headline node is kept.

Copied-text, mojibake, padded-EIN and company-fallback flags do not change
`flag_headline`. They are data for the scoring protocol.

### Tables

`ita_text_pairs.parquet`: one row per pair, sorted by `pair_id`.

| Column | Type | Meaning |
| --- | --- | --- |
| `pair_id` | String | Pair identity |
| `pair_kind` | String | `employer` or `unknown_employer` |
| `employer_key` | String, nullable | Null for `unknown_employer` |
| `employer_basis` | String | `ein`, `company` or `unknown` |
| `description_key` | String | Normalized key |
| `original_strings` | List(String) | Distinct delivered strings, sorted by code point. A null description is kept as one null element, sorted first |
| `representative_string` | String | Most frequent original, with ties going to the first by code point |
| `n_records` | UInt64 | Source records in the pair |
| `n_headline_records` | UInt64 | Records that pass `eligible_industry()` |
| `first_year`, `last_year` | Int64 | Filing-year range |
| `n_years` | UInt64 | Distinct filing years |
| `flag_headline` | Boolean | Headline rule above |
| `flag_headline_codes_conflict` | Boolean | More than one headline node |
| `flag_empty`, `flag_placeholder` | Boolean | From the key |
| `flag_copied_title_any`, `flag_copied_index_any` | Boolean | From the key |
| `flag_suspected_mojibake` | Boolean | Any original flagged |
| `flag_employer_unknown` | Boolean | `employer_basis = unknown` |
| `flag_employer_company_fallback` | Boolean | `employer_basis = company` |
| `n_records_ein_padded` | UInt64 | Records whose EIN key was zero-padded |

`ita_text_pair_codes.parquet`: one row per pair and observed native code,
sorted by `pair_id`, `naics_code`, `naics_year` with nulls first.

| Column | Type | Meaning |
| --- | --- | --- |
| `pair_id` | String | Parent pair |
| `naics_code`, `naics_year` | String, Int64 nullable | Native code and vintage as delivered |
| `naics_mapping_status` | String | Stage 4 status |
| `naics_2022_candidates` | List(String) | Sorted finest candidates. Empty asserts nothing |
| `naics_2022_candidate_node_ids` | List(String) | Node IDs of those candidates, same order |
| `naics_2022_node_id` | String, nullable | Scalar node only where Stage 4 asserts one |
| `naics_deepest_common_node_id` | String, nullable | Describes the candidate set, not an observation |
| `flag_naics_crosswalked`, `flag_naics_ambiguous`, `flag_naics_unresolved` | Boolean | Stage 4 provenance |
| `flag_headline_basis` | Boolean | These records pass `eligible_industry()` |
| `flag_copied_title_native`, `flag_copied_index_native` | Boolean, nullable | Null when `naics_year` is null |
| `n_records` | UInt64 | Records with this code under this pair |
| `n_records_year_from_dictionary` | UInt64 | Of those, records whose `naics_year` the Stage 2 dictionary supplied |
| `years` | List(Int64) | Sorted distinct filing years |

Mapping fields depend only on `(naics_code, naics_year)` through the Stage 4
lookup. The build fails if one key shows two mapping states.

`ita_text_pair_members.parquet`: one row per source record, sorted by
`source_row`. Columns: `source_row: UInt64`, `pair_id: String`. It proves the
exactly-one-pair property and lets later work trace a pair to its records.

`naics_2022_paths.parquet`: the exact Stage 4 `code_paths` rows for every node
that any pair-code row references, as a candidate or as a scalar node. Schema
`node_id: String, path: List(String)`, root to node. This carries the full
2022 path for every supported candidate. A pair-code row references no path only when its candidate list is empty. An unresolved row that keeps unknown-vintage candidates references their paths. *(owner, plan 11, 2026-11-18)*

### Accounting

The report reconciles pair tables to records in disjoint partitions:

- Records by year × mapping status × headline basis.
- Pairs by kind × headline × empty/placeholder.
- Headline pairs by number of headline nodes.

It also reproduces the adopted V1 table exactly, by filing year: `n_rows`,
`n_empty`, `n_placeholder`, `n_copied_any`, `n_native_title_match`,
`n_vintage_unknown`, `n_employer_unknown`, `n_employer_company`,
`n_ein_padded`, `n_mojibake`, `n_repeat_rows` and `n_repeat_excess`. A
mismatch fails the build. The expected values are independent of the build
(see [Expected values for the V1 and V2 gates](#expected-values-for-the-v1-and-v2-gates)). It adds the new index counts by year, with
title-and-index overlap shown separately.

## Co-ownership target

### Eligibility and estimand

An eligible record:

- Has `year_filing_for` in 2023, 2024 or 2025.
- Passes `ita_area_mix.eligible_industry()`.
- Has a non-null `ein_key` and `flag_ein_padded = false`.

Let `E` be the set of EINs with at least one eligible record. For EIN `e` and
year `t`, let `S(e,t)` be the set of `naics_2022_node_id` values on its
eligible records in year `t`. Then:

- `n(a)` = number of EINs `e` with `a` in `S(e,t)` for some `t`.
- `J(a,b)` = number of EINs `e` with both `a` and `b` in `S(e,t)` for the
  same `t`, for `a ≠ b`.
- `N` = number of EINs in `E`.

Each EIN counts at most once in `n(a)` and once in `J(a,b)`, however many
records or years it has. Duplicate records and repeated establishment IDs do
not add weight. The pooled unit is the employer, not the record.

For each ordered pair `(a,b)` with `J(a,b) > 0` and `a ≠ b`, emit one target
row with `value = J(a,b) / n(a)`. Both directions are emitted. No zero cells
and no diagonal cells are emitted. `0 < value ≤ 1` because every EIN counted
in `J(a,b)` is counted in `n(a)`.

Read-only recon (not acceptance values): 8,110 EINs span two or more eligible
industries in the same year, giving 19,576 unordered industry pairs, so about
39,152 target rows. 6,516 unordered pairs have `J ≥ 2`.

### Target rows

| Column | Value |
| --- | --- |
| `source` | `osha_ita` |
| `family` | `co_ownership` |
| `unit_a_type`, `unit_b_type` | `naics_national_industry` |
| `unit_a`, `unit_b` | Six-digit NAICS 2022 node IDs from the selected bundle |
| `measure` | `employer_share` |
| `value` | `J(a,b) / n(a)` |
| `se`, `se_method` | null, `none` |
| `n_unweighted` | `J(a,b)` |
| `n_weighted` | `float(J(a,b))` |
| `sample_set` | `ita_300a_2023_2025` |
| `vintage` | `naics=2022` |
| `universe` | Statement below |
| `flags` | `size_gate_pending`, plus support labels below |

Universe statement: OSHA ITA Form 300A is a program-selected filing subset,
not a frame representative of all establishments or firms. Voluntary and
outside-rule filings are retained, and reported codes and employment are
unvalidated. This target counts employers identified by a usable,
unreconstructed EIN that filed 2023–2025 establishment-year records with valid
native NAICS 2022 industries. An EIN is a tax-filing entity, not necessarily a
whole firm. It is conditional on that eligibility population.

Support labels follow the Stage 6 pattern. For each directed cell, add
`numerator:ein_padded_sensitivity:true` when the padded-EIN sensitivity count
differs from `J(a,b)`.

Partial industry sets are measured per industry, not per cell. An EIN that
filed ineligible records (crosswalked, ambiguous, unresolved or otherwise not
native 2022) in the same year as its eligible records may own industries that
the target cannot see. Such an EIN can only be missing from some `J(a,b)`. It
can never inflate one. An EIN already counted in `J(a,b)` shows nothing about
an undercount of `J(a,b)`. So no per-cell label is derived from it. **My
call:** the marginals table reports these EINs per industry, and the scoring
protocol can use them with `n(a)`.

### Companion tables

`co_ownership_marginals.parquet`, sorted by `node_id`:

| Column | Type | Meaning |
| --- | --- | --- |
| `node_id` | String | Industry `a` |
| `n_employers` | UInt64 | `n(a)` |
| `n_multi_industry_employers` | UInt64 | EINs in `n(a)` with `a` and at least one other industry in the same year *(owner, plan 11, 2026-11-18)* |
| `n_records` | UInt64 | Eligible records in `a` |
| `n_employers_including_padded` | UInt64 | `n(a)` with padded EINs admitted |
| `n_employers_partial` | UInt64 | EINs in `n(a)` that, in at least one year with an eligible record in `a`, also filed an ineligible record in that same year |

`co_ownership_support.parquet`, one row per directed cell, sorted by
`unit_a`, `unit_b`:

| Column | Type | Meaning |
| --- | --- | --- |
| `unit_a`, `unit_b` | String | Same node IDs as the target row |
| `j_employers` | UInt64 | `J(a,b)` |
| `j_2023`, `j_2024`, `j_2025` | UInt64 | Same-year co-presence by year |
| `j_including_padded` | UInt64 | `J(a,b)` with padded EINs admitted |

The report records `N`, `N` with padded EINs, and the counts of eligible and
excluded records by year and exclusion reason in disjoint partitions. It also
records record-level source flags among eligible records (R2.9 flags, filing
flags, `naics_year_from_dictionary`) by year. **My call:** these flags are not
broken down per cell, because the counting unit is the employer.

### Validation

A co-ownership validator checks, beyond `validate_targets`:

- Every unit is a NAICS 2022 national-industry node in the selected bundle.
- `unit_a ≠ unit_b`, and each `(a,b)` row has its `(b,a)` mirror with equal
  `n_unweighted`.
- `n_unweighted = J(a,b) ≥ 1`, and `value` equals `J(a,b) / n(a)` within
  floating tolerance.
- `J(a,b) ≤ min(n(a), n(b))`.
- Support and marginal tables agree with the target rows.

## Establishment-link table

### Year pairs and records

Build links for the nine consecutive year pairs, 2016→2017 through
2024→2025, and for 2023→2025. These are exactly the ten pairs in the adopted
V2 table.

Within each year, exact duplicate records (all 24 Stage 2 columns equal)
collapse for linkage only. A distinct record is identified by its sorted list
of source rows. Its smallest source row is its reference.

### Candidate and confirmed links

For base year `s` and later year `t`:

- **Same-ID candidate.** The base record's `establishment_id` appears in
  year `t`.
- **Confirmed same-ID link.** The ID is unique in both years, both records
  have the same usable unreconstructed EIN, and both have the same complete
  normalized full address. This is the adopted R2.7 rule.
- **Confirmed changed-ID link.** Both records have a non-null ID that is
  unique in its year. The tuple (usable unreconstructed EIN, non-empty
  normalized establishment name, complete normalized full address) is unique
  among all distinct records of each year and matches across the years. The
  two IDs differ.

Both confirmed kinds use the V2 eligible population: records whose IDs are
unique in their year. This is conservative and reproduces V2 exactly. A
record with a competing same-ID record never confirms a link.

### Status

Each base distinct record gets exactly one status per year pair, by this
precedence:

| Order | Status | Rule |
| --- | --- | --- |
| 1 | `missing_id` | Base `establishment_id` is null |
| 2 | `ambiguous_id` | Base ID is not unique in year `s` |
| 3 | `conflict` | Two confirmed-grade links point it to different successors, or its confirmed successor is also the confirmed successor of another base record |
| 4 | `confirmed_same_id` | Confirmed same-ID link, no conflict |
| 5 | `confirmed_changed_id` | Confirmed changed-ID link, no conflict |
| 6 | `weaker_same_id` | Same-ID candidate that is not confirmed |
| 7 | `no_candidate` | None of the above |

A `weaker_same_id` row carries the reasons as separate Boolean columns:
`reason_later_id_ambiguous`, `reason_ein_unknown`, `reason_ein_reconstructed`,
`reason_ein_conflict`, `reason_address_incomplete` and
`reason_address_conflict`. Several reasons can be true. When the later ID is not unique, `reason_later_id_ambiguous` is the only reason set. *(owner, plan 11, 2026-11-18)* Weaker evidence and
conflicts never count as confirmed. Relocation can break address confirmation
without proving a different establishment.

### Table

`ita_establishment_links.parquet`, one row per year pair and base distinct
record, sorted by `base_year`, `later_year`, `base_row`:

| Column | Type | Meaning |
| --- | --- | --- |
| `base_year`, `later_year` | Int64 | Year pair |
| `base_row` | UInt64 | Smallest source row of the base record |
| `base_rows` | List(UInt64) | All source rows of the base record |
| `later_row` | UInt64, nullable | Successor's smallest source row: the confirmed successor for a confirmed status, the unique same-ID candidate for `weaker_same_id`, otherwise null (`conflict` included) *(owner, plan 11, 2026-11-18)* |
| `base_establishment_id`, `later_establishment_id` | Int64, nullable | Delivered IDs |
| `status` | String | One status from the table above |
| `reason_*` | Boolean | Weaker-evidence reasons |
| `flag_id_reappears_elsewhere` | Boolean | A confirmed changed-ID link whose base ID also appears in year `t` |

### Reconciliation gate

Before conflict handling, the build reproduces the adopted V2 table exactly
for all ten pairs. Confirmed same-ID links equal `n_same_ein_address`, and
confirmed changed-ID links equal `n_address_matches_different_id`. For
example, 2023→2024 has 160,579 and 14,532. The candidate and diagnostic counts
also match V2. After conflict handling, the report shows that the statuses
partition the base records and that conflicts account for the exact
difference. A mismatch fails the build.

### Expected values for the V1 and V2 gates

A gate that compares the build with a recomputation from the same code proves
little. **My call:** the expected values are integer constants transcribed
from the adopted V1 and V2 tables in
[the V1–V3 finding](../findings/v1-v3-ita-verification.md), committed in a
Stage 10 module. A unit test checks the constants against the finding's
Markdown tables, so a transcription error fails the suite. The build compares
its own counts, computed by the new Stage 10 code, with those constants.
`ita_verification.link_report` and `description_report` serve as a second,
independent cross-check in the full-data acceptance. They are not the source
of the expected values. Stage 10 does not read the Stage 3 verification run
directory. Those artifacts stay untouched evidence.

## Bundle, commands and provenance

### Module and commands

**My call on names:** module `embedding_data.ita_establishment_targets`, run
as `uv run python -m embedding_data.ita_establishment_targets`. It is
separate from the top-level CLI. Commands:

| Command | Network | Purpose |
| --- | --- | --- |
| `acquire-references` | Yes | Download missing NAICS index originals |
| `import-reference KIND FILE` | No | Register an owner-downloaded original |
| `build RUN_ID --codes-run ID --codes-outputs-sha256 PIN` | No | Build one immutable bundle |
| `verify RUN_ID --outputs-sha256 PIN` | No | Authenticate the pin, then recompute and compare every table |
| `compare-runs FIRST SECOND` | No | Exact logical comparison of two bundles |

Every command takes an explicit `--data-dir`. Offline commands load no
environment file and use no credentials or network client. They never run an
upstream builder.

### Bundle

**My call on location:** `data/derived/osha/establishment-targets/<RUN_ID>/`.

| File | Contents |
| --- | --- |
| `ita_establishment_links.parquet` | Link table |
| `ita_text_pairs.parquet` | Pairs |
| `ita_text_pair_codes.parquet` | Pair codes |
| `ita_text_pair_members.parquet` | Record-to-pair membership |
| `naics_2022_paths.parquet` | Referenced Stage 4 paths |
| `ita_co_ownership.parquet` | `targets-v1` rows, written by `write_targets` |
| `co_ownership_marginals.parquet` | Industry marginals |
| `co_ownership_support.parquet` | Directed-cell support |
| `inputs.json` | Selection and provenance |
| `report.json` | Accounting, reproductions and distributions |
| `outputs.json` | Detached inventory of the other ten files |

`outputs.json` records the byte size, SHA-256, row count and exact schema of
every Parquet and the hash of both other JSON files. It excludes itself. The
production finding records its detached checksum.

`inputs.json` records:

- The codes run ID, detached pin and verified inventory.
- The source summary and canonical physical hashes.
- `manifest.entry_for` citations for every consumed raw file: the Stage 4
  bundle's raw citations, the title originals and the index originals.
- Contract versions `ita-establishment-links-v1`, `ita-text-pairs-v1`,
  `ita-co-ownership-v1`, `naics-index-v1` and `targets-v1`.
- Implementation hashes of the new modules and every reused module,
  dependency versions, Python version, `uv.lock` hash and execution commit.

### Run boundary and failure

- `build` stages into an exclusive `<RUN_ID>.part` directory and renames only
  after every check passes. An existing final or partial name fails. It is
  never reused or overwritten.
- `build` rechecks the pinned inputs and the software identity just before
  publication. Any change fails the run.
- Failure cleans only the run's own staging. It reports a short, fixed reason
  with the run ID and path. It never prints EINs, names or addresses.
- Expected data states are retained diagnostics, not failures: unknown
  employers, empty text, unresolved codes, conflicts and weaker links.
- Malformed references, changed bytes, contradictory mapping states, row loss
  or multiplication, invalid estimates and failed reproductions are failures.

## Verification and acceptance

### Automated tests

Write the failing tests first for library code. Small typed frames cover:

- Index parsing refusals and key collisions.
- Each copied-text flag, including null native identity for unknown vintage.
- Pair identity: every record in exactly one pair, unknown employers alone,
  blank employers never grouped.
- Headline rule, including mixed native and crosswalked groups and headline
  code conflicts.
- Co-ownership: same-year rule, one count per EIN, mirror rows, padded
  exclusion and sensitivity, per-industry partial-set counts, no diagonal.
- Link statuses and precedence, including both conflict shapes, exact
  duplicates and missing IDs.
- Refusals for occupied run names, changed pins, changed software and
  contradictory mapping states.

**V12 extension.** Extend the raw-to-target fixture pattern: fixture raw
files, Stage 2 conversion, a real Stage 4 bundle build, fixture index
originals, then the Stage 10 build, `verify` and a replay compare. The fixture
forbids external access.

The fixture builds its Stage 4 bundle from the committed exact public Stage 4
originals that Stage 8's V12 chain already uses
(`tests/fixtures/acs_mapping/upstream/stage4-originals.zip`). It does not use
Stage 6's toy code tree. The reason is that the frozen `ita_references.read_titles`
reads the three official structure files at their official paths and checks
their full official counts. Toy structures cannot pass it. The fixture's ITA
rows therefore use real NAICS codes. It contains at least one each of: a copied title, a
copied index entry, a placeholder, an unknown employer, a padded EIN, a mixed
native and crosswalked pair, a headline code conflict, a co-owned pair, a
confirmed same-ID link, a changed-ID link and a link conflict. **My call:**
the fixture uses tiny index workbooks in the official layout. It does not
commit the full Census files. Fixture results are software readiness, never
benchmarks.

### Full-data acceptance

Each step that writes to the production data root needs the owner's
go-ahead first (see [Host rule and Stage 9 coordination](#host-rule-and-stage-9-coordination)).

1. Acquire or import the three index originals. Record their hashes.
2. Build a first run and a replay run with fresh IDs.
3. Verify both with their detached pins.
4. Compare the two runs. All eight tables and the report content must be
   equal, apart from run ID and time.
5. Confirm the V1 reproduction and the pre-conflict V2 reproduction.
6. Reconcile co-ownership independently: a second, separately written
   computation of `n(a)`, `J(a,b)` and `N` from the canonical table must match
   exactly.
7. Confirm that pair accounting sums to 3,206,055 records in total and by
   year.
8. Confirm preservation: the Stage 2 summary, the Stage 4 bundle, both Stage 6
   target bundles and every earlier raw file are byte-identical. The manifest
   keeps its earlier prefix, and the raw audit reports zero discrepancies.
9. Record the measured results, pins and limits in
   `specs/findings/stage-10-ita-establishment-targets.md`.

### Host rule and Stage 9 coordination

Stage 9 full-data acceptance shares this host and this data root. Stage 10's
full test suite, coverage gate and full-data builds must not run while a
Stage 9 full-data run is active. Check for an active run before each such
step. Stage 10 never reads or writes Stage 9 paths, plans, probes or evidence.

Stage 9's acceptance gate (`scripts/stage9_independent_io.py`, `preservation`)
fails on any new file under `data/raw` or `data/derived` that appears between
its freeze and its preservation check, unless a raw-manifest append accounts
for it. Stage 10 cannot see whether such a window is open.

**Owner decision (2026-11-13): go-ahead per write.** The plan stops and asks
the owner before each Stage 10 write to the production data root:

1. The index acquisition or import.
2. The first full-data build.
3. The replay build.
4. Any cleanup of a failed run's own staging.

The owner confirms each time that no Stage 9 freeze window is open. Code,
tests and fixture runs need no go-ahead, because they use temporary data
directories. Files that Stage 10 writes before Stage 9's next freeze become
part of what that freeze records.

Stage 9's checker also hashes every `.py` file under `src`, `scripts`, `tests`
and `features` of the checkout it runs from. The Stage 9 worktree must not
merge Stage 10 code between a freeze and its preservation check. That is
Stage 9's responsibility. Stage 10 only records it.

## Methodological limits

- ITA is a program-selected filing population. No product here represents
  all establishments or firms.
- Codes are self-reported and unvalidated. A pair is a noisy label.
- Copied-text flags catch exact normalized identity only. Near-copies and
  reworded index entries stay unflagged.
- Restricting to native 2022 codes drops about 40% of 2024–2025 records. Some
  employers' industry sets are partial, so co-ownership can be undercounted.
  The marginals table measures this per industry.
- An EIN is a tax-filing entity. One firm can hold several EINs, so
  co-ownership within EIN can miss relationships across a firm.
- Which establishments file is shaped by the filing rule. Co-ownership can
  over-represent designated industries (methodology K6, assumption 6).
- Linkage uses exact address equality. Relocations and address reformatting
  break confirmation. Probabilistic linkage stays out of scope.
- The marginal `n(a)` pools presence over three years. An employer that left
  industry a in 2024 still counts in `n(a)`. `J(a,b)` requires both
  industries in the same year.

## Source spec amendment

The plan applies this amendment to R2.6 in the source spec, replacing the
sentence that begins "Identity to any official":

> Identity to any official 2012, 2017 or 2022 NAICS title at levels 2–6, or
> to any official 2012, 2017 or 2022 NAICS index entry, is flagged as copied
> text. Titles and index entries are flagged separately. Native-vintage
> identity is also reported, with unknown vintage kept unknown. *(owner,
> Stage 10 design, 2026-11-13; [stage spec](ita-establishment-targets.md))*

R7.2's co-ownership row needs no amendment. This spec defines its measure.

## Rollout and later-stage handoff

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 1 — tick Stage 1 when its Exit holds; on plan completion, tick Stage 4 and re-validate later stages against what shipped. (Moved from Stage 10 of the parked `specs/completed/embedding-evaluation-data-spec-roadmap.md` on 2026-11-16.)

- Plan number 10 is taken by an uncommitted Stage 9 file. The Stage 10 plan
  takes the next free number after 10.
- Keep this as one Stage 10 implementation cycle. Separate software readiness
  (tests and V12 fixture) from full-data acceptance.
- Do not tick Stage 10 or retire this spec on design or planning completion.
- Stage 9 remains in execution through its own plan. Stage 10 does not wait
  for it and does not touch it. Stages 11–13 keep their order.

The shipped Handoff must give exact schemas, APIs, pins and limits for:

- Stage 11 and Stage 12: no new ITA behavior. The shared writer and frozen
  modules are unchanged.
- Stage 13: the bundle's detached pins and inventories, the pair and
  co-ownership count distributions for V9, both families' V12 coverage, and
  the `size_gate_pending` state.
- The successor evaluation protocol: copied-text flags, headline flags, the
  co-ownership counts and marginals for any null-model normalization, and the
  R8.4 exclusion from training and model selection, with the amendment's one
  exception for the text–code pairs. *(owner, amendment, 2026-11-18)*

After the owner approves this committed spec, use a fresh session with
writing-plans against `specs/ita-establishment-targets.md`. The brainstorming
dialogue is not a dependency.
