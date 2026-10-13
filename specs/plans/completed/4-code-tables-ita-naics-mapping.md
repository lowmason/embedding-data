# Code tables and ITA NAICS mapping implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish verified NAICS 2022/SOC 2018 graphs, complete vintage relationships, and a separate ITA canonical table with supported candidates and conservative filing-rule diagnostics.

**Architecture:** Parse immutable official originals into small eager reference tables, validate their complete graphs and relationships, then build a unique mapping lookup. Join that lookup and a filing-rule lookup into the existing establishment table using lazy Polars; publish a complete, immutable bundle only after source parity and output checks pass.

**Tech Stack:** Python 3.14, Polars 2, fastexcel, httpx, Typer, pytest, Hypothesis; standard-library HTMLParser for GovInfo's preformatted rule editions. No dependency changes.

**Spec:** [specs/completed/code-tables-ita-naics-mapping.md](../../completed/code-tables-ita-naics-mapping.md), implementing the [source spec](../../embedding-evaluation-data-spec.md) R5.1 (ITA), R5.2, R5.4 (ITA), R2.5, R2.9 (industry), V11 (ITA).

> Roadmap: specs/embedding-evaluation-data-spec-roadmap.md, Stage 4 — on plan completion, tick the stage and re-validate later stages against what shipped.

**Status: COMPLETE (2026-10-13)** — executed via subagent-driven-development; nothing deferred. Task 0 was already committed at `ffaa576`; Tasks 1–8, measured acceptance, carried-item closure and final review are complete. Integration is a draft PR; resume the roadmap after merge.

## Reference-conflict resolution

The real-original self-review found that the official exemption list contains `5173` and `5181`, which are absent from NAICS 2007. The [reference preflight](../../findings/stage-4-filing-rule-reference-preflight.md) records original hashes, all-list membership comparisons, current OSHA authority, and the full official 2002→2007 relationships. The unamended design's strict expansion rejects that original. The proposal below preserves strict validation except for these two documented, explicitly interpreted legacy labels.

Adopted by D2: retain those original labels, acquire the complete NAICS 2002 structure/bridge as auxiliary rule references, and preserve both possible exemption outcomes for partial legacy coverage or mixed-predecessor merges. In particular, 2007 `517110` must not become wholly exempt merely because one 2002 predecessor is inside legacy `5181`. Preserve definite whole-node exemptions from valid 2007 listed groups. Native ITA vintages and canonical systems remain as approved.

D2 records the owner's approval of the exact Task 0 amendment and revised plan on 2026-10-13. The eight replacements are applied to the stage spec, and Tasks 1–8 implement that adopted contract. No weights, preferred predecessor or invented exemption resolves a merge. Execution uses an isolated worktree and the plan's milestone checks; the roadmap checkbox remains open until the Stage 4 exit holds.

## Global Constraints

The following constraints are copied from the stage design:

- "No new dependency is needed: use the existing Polars, fastexcel, httpx, and Typer stack."
- "Workbook inputs are small eager frames; establishment transformations are lazy Polars with method-style expressions, as R9 requires."
- "Preserve the existing `acquire_titles`, `read_titles`, and `parse_titles` interfaces for verification replay."
- "Read `ita_300a_summary.parquet` and retain every Stage 2 column unchanged."
- "The source summary and Stage 3 run directories are never rewritten."
- "All flags are nonnullable. Candidate lists are nonnull, including empty lists." This applies to NAICS mapping flags; filing-rule flags are explicitly nullable.
- "Malformed nonmissing source codes fail the build; the accepted ITA syntax is exactly six ASCII digits."
- "Do not explode candidate lists into establishment rows, deduplicate establishments, or filter unresolved rows."
- "No weights or preferred side resolve uncertain membership."
- "Build into a new staging directory and publish the bundle only after all checks succeed."
- "Every command test passes a temporary `--data-dir`; never rely on patching the import-bound default."
- "No new default test reads real data or uses a credential."

Source spec R9.2 also applies verbatim: "Every transformation is deterministic and runs offline from raw files. Tests use fixtures, with no network and no credentials."

## Decisions

- **D1** (owner, plan review, 2026-10-13): research a bounded legacy-vintage bridge and bring the exact proposed rule interpretation back for approval before implementing the filing flag. Applied in: reference-conflict investigation, Task 0 proposal and reference preflight. This was research authorization; adoption is recorded separately in D2.

- **D2** (owner, plan review, 2026-10-13): approve Plan 4's exact eight Task 0 spec replacements and revised implementation plan. Interpret only exemption labels `5173`/`5181` through the complete 2002→2007 bridge, retain mixed membership for 2007 `517110`, and require filing-result unanimity with separate provenance flags. Applied in: Task 0 (spec amendment), Tasks 2–4/6–8 and the stage spec's reference, membership, evaluation and reporting contracts.

## Entry evidence and source investigation

Planned against `main` at `6f8c190`, with a clean working tree. The plan-ID reporter scanned branches, remote-tracking refs and worktrees: highest 3, next free 4, no collisions, no plan for this spec. Fresh baseline: 284 pytest passed/one network canary deselected; two Behave scenarios/ten steps passed; ruff and lock checks passed.

Read plan 3's [Handoff](3-ita-verification.md#handoff-to-later-stages), the stage design, preflight, source spec and deferred ledger. Reuse `manifest.entry_for` for verified citations, `ita_references.existing_reference` for immutable reference checks, `ita_summary.summary_files` for release selection, and `ita_summary.harmonize_file`/`add_flags` for **read-only** source validation. Never call `build_summary_table` from this stage.

Planning inspected public originals only in temporary storage; it made no raw-manifest entry and changed no project data. These are source/layout observations, not completed Stage 4 output:

| Identity | Official original URL | Observed layout/count |
| --- | --- | --- |
| `naics_2007` | `https://www.census.gov/naics/reference_files_tools/2007/naics07.xls` | `Seq. No.`, `2007 NAICS US Code`, `2007 NAICS US Title`; 2,328 nodes/1,175 leaves |
| `naics_2002` (adopted auxiliary) | `https://www.census.gov/naics/reference_files_tools/2002/naics_2_6_02.txt` | Complete original text; `Code    2002 NAICS Title`; 2,341 nodes/1,179 leaves |
| `concordance_2002_2007` (adopted auxiliary) | `https://www.census.gov/naics/concordances/2002_to_2007_NAICS.xls` | 1,200 distinct pairs; complete 1,179/1,175 endpoint coverage |
| `naics_2012`, `naics_2017`, `naics_2022` | Existing `ita_references.TITLE_FILES` | Preserve existing full/leaf pins: 2,209/1,065; 2,196/1,057; 2,125/1,012 |
| `concordance_2007_2012` | `https://www.census.gov/naics/concordances/2007_to_2012_NAICS.xls` | Full concordance; multiline title headers; complete endpoint coverage required |
| `concordance_2012_2017` | `https://www.census.gov/naics/concordances/2012_to_2017_NAICS.xlsx` | Full concordance; cached original inspected |
| `concordance_2017_2022` | `https://www.census.gov/naics/concordances/2017_to_2022_NAICS.xlsx` | Full concordance; cached original inspected |
| `soc_2018` | `https://www.bls.gov/soc/2018/soc_structure_2018.xlsx` | Four code columns plus unheaded title column; 1,447 nodes/867 detailed; sheet order controls parents |
| `designated_2012` | `https://www.govinfo.gov/content/pkg/FR-2016-05-12/html/2016-10443.htm` | Final Appendix A to Subpart E: 66 listed groups |
| `designated_2017` | `https://www.govinfo.gov/content/pkg/FR-2023-07-21/html/2023-15091.htm` | Final Appendix A to Subpart E: 65 listed groups; stop before Appendix B |
| `partially_exempt_2007` | `https://www.govinfo.gov/content/pkg/FR-2014-09-18/html/2014-21514.htm` | Final Appendix A to Subpart B: 82 listed groups/2015-01-01 effect; **two labels fail 2007 membership**, despite OSHA FAQ's vintage guidance; see gate |

GovInfo hosts the official editions of the same rule publications cited by the design. Retain those complete original HTML bytes, not extracted text. FederalRegister.gov returned an HTTP-200 access challenge to scripted requests during planning; HTTP success alone is insufficient validation. The 2007 workbook is **not** at the tempting but nonexistent `2007NAICS/2007_NAICS_Structure.xls` URL. Census's live Downloadable Files panel supplied the URL above. This is reference discovery within approved scope, not a spec amendment.

Observed original SHA-256 values, for comparison during acquisition/import:

```text
naics_2007                 9eaa1fc4681ad22296b8f09603dc3674605eeb13b0fd631811d51704e1c2f463
naics_2002                 b05cb32865d9267eaca4c2df45b89605c02320c5d1794b0ba0304e2c1741edaf
concordance_2002_2007      a4b00b2195e318420962ba52b77f3c3122e83d893a9f804e820c151847ec85b1
concordance_2007_2012      302b8abcd78881f1ea5aa4c6c9104811bf8fa10d57b48d492939de5cacc8cfc5
concordance_2012_2017      17f463f7e8385df1cc762fadf0dd5c25910aa27034ca96275a906608399188f5
concordance_2017_2022      4662cc7ed9e7f3fb8a968e9504a7d06e448f5b65a349996a5627439df193eb30
soc_2018                  ade08af40923266f3a854842e888ca3e93c15b26a147c20a2b12a61f4c4f4077
designated_2012           ed7ea8e8533236ea0fcbafcb703f38007b75e97b472789f9a2ded55eac958866
designated_2017           fd0ae1f1c1462adf2863c2107da32e2a4d1d486503433f347237867edd401551
partially_exempt_2007     3418238856a56bf0da7bac73a1a07535a4f098e3212287a35048602968855a87
```

A changed public original must be explicitly investigated and recorded in the execution ledger; never replace an already manifested path. There is no runtime access to the personal classification cache. Optional original imports from that cache require comparing their bytes with its recorded source/hash first.

## Files and interfaces

| File | Responsibility |
| --- | --- |
| `src/embedding_data/classification_tables.py` | Shared table schemas, strict workbook header seams, NAICS/SOC graphs, graph closure and full paths |
| `src/embedding_data/naics_relationships.py` | Direct pair parsing/validation, degree-based link types, complete forward/reverse traversal |
| `src/embedding_data/filing_rules.py` | Original GovInfo appendices, vintage-specific expansion, periods and conservative evaluation |
| `src/embedding_data/code_references.py` | Registered identities/URLs/paths, immutable acquire/import and verified offline reads |
| `src/embedding_data/ita_naics_mapping.py` | Unique native lookup, all six mapping states and row-preserving enrichment |
| `src/embedding_data/code_build.py` | Input parity, staged bundle, reports, code/dependency/input/output hashes |
| `src/embedding_data/codes_cli.py` | `codes acquire`, `codes import-reference KIND FILE`, `codes build RUN_ID` |
| `src/embedding_data/cli.py` | Register the `codes` command group |
| `tests/code_fixtures.py` and `tests/fixtures/codes/` | Handwritten tiny structures/relations/rules plus original-layout workbook fixtures |
| `tests/test_classification_tables.py`, `test_naics_relationships.py`, `test_filing_rules.py`, `test_code_references.py`, `test_ita_naics_mapping.py`, `test_code_build.py`, `test_codes_cli.py` | Contract tests at the cheapest useful layer |
| `specs/findings/v11-ita-naics-mapping.md`, `README.md`, `CLAUDE.md` | Actual full-data evidence and shipped command/contracts documentation |

No change to `ita_summary.add_flags`: its Stage 2 output remains byte-identical. The deferred item's original location predates the approved separate-output design; close its industry-evaluation outcome through `filing_rules` and the enriched output, and record this placement in the plan deviation ledger/Handoff.

## Durable testing strategy

All new default tests are offline; retain the existing `network` exclusion and strict unknown-marker warning. Use handwritten expected outputs; mock HTTP/clock only. Workbook fixtures exercise fastexcel with original sheet shapes, not mocked `pl.read_excel`. Tiny original-format workbooks may be created once using the standard-library XLSX zip/XML format and committed; no test-writing dependency is added. Use in-memory raw-sheet frames for parser failures and tmp Parquet only for I/O/join/bundle checks.

| Invariant | Layer/fixture | Task |
| --- | --- | --- |
| Exact typed nodes/edges/paths, no invented roots, closed acyclic immediate parents, ranged sectors | Unit: small NAICS forests; SOC overflow `29-1221` under published `29-1210`; duplicate/orphan/cycle/ambiguous-column frames | 1 |
| Official pair membership and both-side complete coverage; 1:1/1:m/m:1/m:m; code reuse never shortcuts | Unit: tiny complete pair frames, missing/invalid endpoints; sorted/reordered rows | 2 |
| Final Appendix A only, complete lists and periods in their own vintage | Parser: preformatted original snippets, distracting preamble/Appendix B, challenge HTML, missing/duplicate list rows | 3 |
| Only two legacy labels admitted; full predecessor coverage, whole-node precedence and mixed membership retained | Unit: literal 5173/5181 bridge, three incoming predecessors of 517110, corrupt/missing predecessor and unsupported-label failures | 2–4 |
| Original bytes and manifest stay immutable; every input verified | HTTP/import integration: MockTransport, changed/missing/unrecorded originals, mismatched import, existing `.part` | 4 |
| Six mapping states, nonnull sorted lists/flags, singleton crosswalk and unknown flags persist | Unit: missing/known/unknown/mismatch keys; wrong width/non-ASCII/nonnumeric source | 5 |
| Null joins and exact duplicate multiplicity/order preserve source values | Property: shuffled/repeated source rows, unique lookup violations and unmatched keys | 5 |
| Filing uses peak size and nominal filing year; unanimity within interpretation before union | Unit: 2022/2023 boundary, classes 1/2/3/null, missing states, mixed/correlated candidates and missing bridge | 6 |
| Stale source fails, full multiset parity, no source rewrite, complete atomic bundle | Build integration: original fixtures, deliberate source cell/row/count/release change, failed stage and occupied run | 7 |
| CLI path is explicit, offline build cannot fetch, outputs deterministic across run names | CLI integration: temporary tree, forbidden-network boundary, logical frame equality across two builds | 7 |
| All actual input rows accounted for, full reference pins and manifest audit, no Stage 2/3 hash changes | Explicit full-data acceptance; not a default pytest test | 8 |

Milestone command (run after each task's focused checks):

```bash
uv run --locked pytest
uv run --locked behave
uv run --locked ruff check .
uv lock --check
```

In a restricted workspace use `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache` and `--offline` with the installed environment. No new network canary is required for fixed original parsers. Do not run acquisition against the real root during ordinary tests.

## Execution order and checkpoints

Task 0 applies only the approved exact amendment; Tasks 1–3 establish reference semantics; Task 4 adds acquisition using those real validators; Tasks 5–6 establish row semantics; Task 7 publishes the bundle; Task 8 measures and completes the stage. Each task ends in its own commit and verified checkpoint. Execute in order. Subagent implementers own only their task's listed files, are not alone in the codebase, and must accommodate rather than revert others' edits. Use task-scoped review gates when executing through subagent-driven-development.

Before Task 1, use using-git-worktrees and run the baseline. The actual data root is the original checkout's `/Users/lowell/Projects/embedding-data/data`, not a worktree-relative default; only the explicit Task 8 command uses it. No implementation on `main` without owner authorization. No code is implemented by saving this plan.

### Task 0: Apply the exact approved bounded-bridge amendment

**Files:** Modify `specs/code-tables-ita-naics-mapping.md` only after approval; update this plan's Decisions/adoption status. The umbrella source spec and roadmap remain live and unchanged.

**Gate resolved:** D2 approves these exact eight policy/schema replacements and the revised plan on 2026-10-13. They have been applied without changing the stage spec's original approval/status line. The replace/with blocks remain below as the adoption audit trail; do not apply them again. No further interpretation is invented during execution.

- [x] **Step 1: Verify review preconditions.** Confirm the owner has approved this exact proposal, record a separate D2 adoption decision, and verify each old block below occurs exactly once in the current stage spec. A changed old block requires a reviewed reconciliation, never a fuzzy replacement.
- [x] **Step 2: Apply the following exact replacements in order.** Each pair changes only the named paragraph/table row. They describe a bounded auxiliary rule reference; neither canonical systems nor ITA native vintages are broadened.

**Auxiliary originals — replace:**

```text
| NAICS 2007 structure and 2007 to 2012 concordance | Official Census originals; auxiliary membership and exemption bridge |
```

**With:**

```text
| NAICS 2007 structure and 2007 to 2012 concordance | Official Census originals; auxiliary membership and exemption bridge |
| NAICS 2002 complete code/title text and full 2002 to 2007 concordance | Official Census originals; bounded interpretation of exemption labels `5173` and `5181` only; no new ITA native vintage. *(owner, plan 4, 2026-10-13)* |
```

**Nominal vintage and documented legacy labels — replace:**

```text
The [OSHA exempt list](https://www.osha.gov/recordkeeping/presentations/exempttable)
and [FAQ 2-4](https://www.osha.gov/faq/2-4) establish the 2007 exemption vintage.
```

**With:**

```text
The [OSHA regulatory appendix](https://www.osha.gov/laws-regs/regulations/standardnumber/1904/1904SubpartBAppA)
and [FAQ 2-4](https://www.osha.gov/faq/2-4) describe the nominal exemption
basis as NAICS 2007. The original appendix nevertheless contains `5173` and
`5181`, which are absent from the official 2007 structure and present in
2002. Preserve both published labels and interpret only these documented
exceptions through the complete official 2002-to-2007 relation, under the
possibility-set contract below. This is a conservative reference
interpretation for R2.9, not an assertion of OSHA's intended treatment of a
merged industry's individual establishments. See the
[reference preflight](findings/stage-4-filing-rule-reference-preflight.md). *(owner, plan 4, 2026-10-13)*
```

**Auxiliary structure and complete coverage — replace:**

```text
Native 2012/2017 structures retain Stage 3's full/six-digit checks. Validate the
2007 auxiliary structure and bridge against their acquired official originals,
including complete endpoint membership and parent closure; record their counts
and hashes in the Stage 4 finding. The 2007 vintage is an auxiliary rule
reference, not an inferred ITA vintage or a new canonical system.
```

**With:**

```text
Native 2012/2017 structures retain Stage 3's full/six-digit checks. Validate
the 2002 and 2007 auxiliary structures and both 2002-to-2007 and
2007-to-2012 bridges against their acquired official originals, including
complete endpoint membership and parent closure. Require 2,341/1,179
full/finest nodes for the pinned 2002 text and 2,328/1,175 for 2007; record
counts and hashes in the Stage 4 finding. Both are auxiliary rule references,
not inferred ITA native vintages or new canonical systems. *(owner, plan 4, 2026-10-13)*
```

**Original labels and full membership possibilities — replace:**

```text
Build a versioned list table with `rule_id:String`, `vintage:Int64`,
`code:String`, `effective_from:Date`, `effective_to:Date` (nullable), and
`source_file:String`. Rule IDs are `designated_2012`, `designated_2017`, and
`partially_exempt_2007`; `(rule_id, code)` is unique. Expand listed
sectors/groups to valid finest codes using that list's own structure. Verify
every listed code; prefix matching across
vintages is forbidden. Preserve historical list differences from the official
texts rather than updating an old list in place.
```

**With:**

```text
Keep `filing_rules.parquet` as the definite-member projection with
`rule_id:String`, `vintage:Int64`, `code:String`, `effective_from:Date`,
`effective_to:Date` (nullable), and `source_file:String`. Rule IDs remain
`designated_2012`, `designated_2017`, and `partially_exempt_2007`;
`(rule_id, code)` is unique. A row in this table asserts definite membership,
not merely one supported possibility.

Publish `filing_rule_labels.parquet` with `rule_id:String`,
`vintage:Int64`, `listed_code:String`, `label_vintage:Int64`,
`flag_rule_label_legacy:Boolean`, and `source_file:String`;
`(rule_id, listed_code)` is unique. Retain every original published label.
The rule's nominal vintage remains in `vintage`; `label_vintage` is 2002
only for the two allowlisted exemption labels `5173` and `5181`, and
otherwise equals the rule vintage. Validate each label in its interpreted
structure; every other unmatched label is a reference error. Original
code/title text remains archived in the cited raw publication.

Publish `filing_rule_membership.parquet` with all definite-table fields
plus `membership_candidates:List(Boolean)` and
`flag_rule_label_bridged:Boolean`. Include exactly one row for every finest
code in each rule's own vintage, including nonmembers. Possibilities are
nonnull, sorted and duplicate-free, and exactly `[false]`, `[true]`, or
`[false, true]`; flags are nonnullable. The definite table is exactly the
`[true]` projection of this complete membership relation.

For the exemption rule, expand the 80 valid listed groups within NAICS
2007 by validated ancestry. Expand only legacy labels `5173` and `5181`
within NAICS 2002 into their finest leaves. For each 2007 finest code,
retain every 2002 predecessor from the complete direct official relation.
If a valid 2007 listed group covers it, membership is `[true]`. Otherwise,
its possibilities are the union of each predecessor's membership in the
expanded legacy-label set. A merge with covered and uncovered predecessors
therefore yields `[false, true]`. Set `flag_rule_label_bridged` when at
least one predecessor belongs to that legacy set, even when a whole-node
2007 exemption already establishes `[true]`. Missing predecessors or
incomplete endpoint coverage fail reference validation; they never create
false unanimity.

The pinned inputs yield `[false, true]` for 2007 `517110`: predecessor
`518111` belongs to legacy `5181`, while `517110` and `517510` do not.
Never promote this partial coverage to a whole-node exemption. Other legacy
successors already sit under valid listed 2007 groups `5179` or `5191`.
No list-wide vintage replacement, numeric prefix matching across vintages,
preferred predecessor, allocation weight, or inferred industry is permitted.
Preserve the official lists' historical versions and periods. *(owner, plan 4, 2026-10-13)*
```

**Evaluation consumes membership possibilities — replace:**

```text
Use `size_class`, which reflects peak-employment size, never annual-average
employment to infer a size class. For each reference-supported native
interpretation, traverse the official relationships directly into the
designated and exempt lists' own vintages. Do not route through canonical 2022
and back when a direct vintage path exists. Preserve every rule-native
candidate. For each native-vintage interpretation, evaluate the Cartesian
product of its designated-list and exemption-list candidates, then union
evaluations across the supported interpretations. Do not mix candidates from
different native-vintage interpretations before this evaluation. This is a
conservative unweighted possibility set, not evidence about which part of a
split the establishment occupies. No weights or preferred side resolve
uncertain membership. Size class 3 needs only the exemption candidates.
```

**With:**

```text
Use `size_class`, which reflects peak-employment size, never annual-average
employment to infer a size class. For each reference-supported native
interpretation, traverse the official relationships directly into the
designated and exempt rules' own vintages, retaining every rule-native
candidate. Do not route through canonical 2022 and back when a direct path
exists. For each interpretation, form the designated membership possibilities
and the exemption membership possibilities from the complete membership
relation, then evaluate their Cartesian product. Union the resulting outcomes
across interpretations; never pool candidates across different native-vintage
interpretations before evaluating them. Size class 3 needs only exemption
possibilities. These are conservative unweighted possibilities, not evidence
about which predecessor or part of a split an establishment occupies.
No weights or preferred side resolve uncertain membership. *(owner, plan 4, 2026-10-13)*
```

**Record reference provenance separately from final unanimity — replace:**

```text
Keep `flag_below_filing_size` unchanged. Add
`flag_outside_filing_rule:Boolean` as true for size class 1, otherwise the
industry result for size classes 2/3, otherwise null. Preserve uncertainty
instead of treating null as false. A missing bridge for an otherwise supported
code fails reference validation; it cannot produce a falsely unanimous result
from partial coverage. These are filing-universe diagnostics under R2.2/R2.9;
they neither drop rows nor establish that an observed submission was improper.
```

**With:**

```text
Keep `flag_below_filing_size` unchanged. Add
`flag_outside_filing_rule:Boolean` as true for size class 1, otherwise the
industry result for size classes 2/3, otherwise null. Preserve uncertainty
instead of treating null as false. Add nonnullable
`flag_filing_rule_label_bridged:Boolean` when an evaluated exemption
candidate is marked bridged, and `flag_filing_reference_ambiguous:Boolean`
when an evaluated exemption candidate has `[false, true]` membership.
These provenance flags persist even if the final filing outcome is unanimous;
for statuses that evaluate no industry membership, both are false.
An ambiguous membership can still produce `determinate` outside status when
both possibilities give the same result. Actual outcome disagreement remains
`candidate_disagreement` with nullable industry/rule results.
A missing bridge or membership row for an otherwise supported code fails
reference validation. These are filing-universe diagnostics under R2.2/R2.9;
they neither drop rows nor establish that an observed submission was improper.
Native NAICS uncertainty flags and admitted ITA vintages remain unchanged. *(owner, plan 4, 2026-10-13)*
```

**Bundle tables — replace:**

```text
- validated native/auxiliary NAICS structures, `naics_concordance.parquet`,
  the versioned filing lists, and `code_paths.parquet`;
```

**With:**

```text
- validated native/auxiliary NAICS structures, `naics_concordance.parquet`,
  `filing_rules.parquet`, `filing_rule_labels.parquet`,
  `filing_rule_membership.parquet`, and `code_paths.parquet`; *(owner, plan 4, 2026-10-13)*
```

**Report reference ambiguity and labels — replace:**

```text
The report partitions all input rows by filing year and mapping status, with
missing, unresolved, ambiguous, and crosswalked counts reported separately.
It reports candidate-count distributions and each filing-rule state, including
null results and vintage uncertainty. Counts must reconcile to the full input;
flags can overlap and are not disjoint report partitions.
```

**With:**

```text
The report partitions all input rows by filing year and mapping status, with
missing, unresolved, ambiguous, and crosswalked counts reported separately.
It reports candidate-count distributions and each filing-rule state, including
null results and vintage uncertainty. Also report original label counts,
legacy-label counts, definite/nonmember/mixed rule-native membership counts,
and each record-level reference provenance flag by filing year. Counts must
reconcile to the full input; flags can overlap and are not disjoint report
partitions. The finding must distinguish this adopted conservative
reference interpretation from an externally confirmed legal interpretation
and document the mixed-predecessor limit. *(owner, plan 4, 2026-10-13)*
```

- [x] **Step 3: Verify the amendment.** Compare the stage spec diff with only the eight approved replacements, resolve all local links, and run `git diff --check`. Source-spec requirements and roadmap stage order remain unchanged. All schema/interface changes below must match the adopted text.
- [x] **Step 4: Commit/checkpoint.** `git add specs/code-tables-ita-naics-mapping.md specs/plans/4-code-tables-ita-naics-mapping.md` then `git commit -m 'docs(specs): adopt bounded legacy exemption-label interpretation'`. Begin Task 1 only after this checkpoint.

### Task 1: Strict classification forests and canonical paths

**Files:** Create `src/embedding_data/classification_tables.py`, `tests/test_classification_tables.py`, `tests/code_fixtures.py`; add tiny original-layout workbook fixtures under `tests/fixtures/codes/` alongside the tests that use them.

**Interfaces:** `naics_tables(titles: pl.DataFrame, vintage: int) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]`; `soc_tables(raw: pl.DataFrame) -> tuple[...]`; `forest(nodes: pl.DataFrame, edges: pl.DataFrame) -> pl.DataFrame` returns paths after validation; `below_header(raw, needles) -> pl.DataFrame`; `column(body, *needles) -> str`. Structures use the exact node/edge schema in the design; paths have `node_id:String, path:List(String)`. All later references call these repository functions.

- [x] **Step 1: Add failing graph/parser tests and handwritten fixture helpers.** Start with this fixture and tests; the SOC test intentionally asserts a published overflow parent that prefix surgery cannot supply.

```python
# tests/code_fixtures.py
import polars as pl

def titles(vintage: int, leaves=('111111', '111112')) -> pl.DataFrame:
    codes = ['11', '111', '1111', '11111', *leaves]
    return pl.DataFrame({
        'vintage': [vintage] * len(codes), 'code': codes,
        'title': [f'Fixture {code}' for code in codes],
    }, schema={'vintage': pl.Int64, 'code': pl.String, 'title': pl.String})

def soc_sheet() -> pl.DataFrame:
    return pl.DataFrame([
        ['Major Group', 'Minor Group', 'Broad Group', 'Detailed Occupation', None],
        ['29-0000', None, None, None, 'Healthcare Practitioners'],
        [None, '29-1200', None, None, 'Health Diagnosing Practitioners'],
        [None, None, '29-1210', None, 'Physicians'],
        [None, None, None, '29-1221', 'Pediatricians'],
    ], orient='row', schema={f'c{i}': pl.String for i in range(5)})

# tests/test_classification_tables.py
import polars as pl
import pytest
from embedding_data import classification_tables as ct
from code_fixtures import soc_sheet, titles

def test_naics_exact_graph_and_path():
    nodes, edges, paths = ct.naics_tables(titles(2022), 2022)
    assert nodes.schema == ct.NODE_SCHEMA
    assert edges.schema == ct.EDGE_SCHEMA
    assert paths.schema == ct.PATH_SCHEMA
    assert paths.filter(pl.col('node_id').str.ends_with(':111111'))['path'][0].to_list() == [
        'naics:2022:sector:11', 'naics:2022:subsector:111',
        'naics:2022:industry_group:1111', 'naics:2022:industry:11111',
        'naics:2022:national_industry:111111',
    ]

def test_soc_uses_workbook_parent_not_code_prefix():
    nodes, edges, paths = ct.soc_tables(soc_sheet())
    assert nodes.height == 4
    assert edges.filter(pl.col('child_id').str.ends_with(':29-1221'))['parent_id'][0] == (
        'soc:2018:broad:29-1210'
    )

@pytest.mark.parametrize('sector,subsector', [('31-33', '311'), ('44-45', '441'), ('48-49', '491')])
def test_ranges_are_one_sector(sector, subsector):
    frame = pl.DataFrame({'vintage': [2022, 2022], 'code': [sector, subsector],
                          'title': ['Fixture sector', 'Fixture subsector']})
    nodes, edges, paths = ct.naics_tables(frame, 2022)
    assert nodes.filter(pl.col('level').eq('sector'))['code'].to_list() == [sector]
    assert edges['parent_id'].to_list() == [f'naics:2022:sector:{sector}']

def test_duplicate_and_orphan_refused():
    frame = titles(2022)
    with pytest.raises(ValueError, match='duplicate'):
        ct.naics_tables(pl.concat([frame, frame.tail(1)]), 2022)
    with pytest.raises(ValueError, match='parent'):
        ct.naics_tables(frame.filter(pl.col('code').ne('11111')), 2022)
```

Add parametrized failure frames for missing titles, invalid code syntax/ranges, two populated SOC code columns, missing SOC upper level, duplicate SOC codes, duplicate/unknown edge endpoints, contradictory immediate levels and a cycle. Include an ambiguous header frame with two code columns matching the same vintage. Expected errors are `ValueError` naming the defect; no silently deduplicated structures.

- [x] **Step 2: Verify red.** Run `uv run --locked pytest tests/test_classification_tables.py -q`; expect import failure for the absent repository module, not a fixture typo.

- [x] **Step 3: Implement the graph and strict parser seams.** Put the following code in `classification_tables.py`. Keep production count pins in Task 4's reference reader, so tiny unit forests remain genuine inputs to these pure functions.

```python
import re
import polars as pl

NODE_SCHEMA = {name: pl.String for name in ['node_id', 'system']}
NODE_SCHEMA.update(vintage=pl.Int64, level=pl.String, code=pl.String, title=pl.String)
EDGE_SCHEMA = {name: pl.String for name in ['child_id', 'parent_id', 'edge_type']}
PATH_SCHEMA = {'node_id': pl.String, 'path': pl.List(pl.String)}
NAICS_LEVELS = {2: 'sector', 3: 'subsector', 4: 'industry_group',
                5: 'industry', 6: 'national_industry'}
SOC_LEVELS = ('major', 'minor', 'broad', 'detailed')

def below_header(raw: pl.DataFrame, needles: tuple[str, ...]) -> pl.DataFrame:
    for i, row in enumerate(raw.rows()):
        cells = [str(x).strip() for x in row if x is not None and str(x).strip()]
        if len(cells) >= 2 and all(x.lower() in ' | '.join(cells).lower() for x in needles):
            names = [str(x).strip() if x is not None and str(x).strip() else f'c{j}'
                     for j, x in enumerate(row)]
            if len(set(names)) != len(names):
                raise ValueError('ambiguous duplicate header')
            body = raw.slice(i + 1)
            body.columns = names
            return body
    raise ValueError('required workbook header missing')

def column(body: pl.DataFrame, *needles: str) -> str:
    matches = [name for name in body.columns if all(
        token.lower() in name.split('\n', 1)[0].lower() for token in needles
    )]
    if len(matches) != 1:
        raise ValueError(f'ambiguous or missing column: {needles}')
    return matches[0]

def forest(nodes: pl.DataFrame, edges: pl.DataFrame) -> pl.DataFrame:
    if nodes.schema != NODE_SCHEMA or edges.schema != EDGE_SCHEMA or nodes.is_empty():
        raise ValueError('incompatible or empty graph schema')
    if any(nodes[c].null_count() for c in nodes.columns):
        raise ValueError('null node field')
    if nodes['node_id'].n_unique() != nodes.height or nodes.select(
        'system', 'vintage', 'code'
    ).is_duplicated().any():
        raise ValueError('duplicate node')
    if nodes.filter(pl.col('title').str.strip_chars().eq('')).height:
        raise ValueError('missing title')
    records = {r['node_id']: r for r in nodes.iter_rows(named=True)}
    parents = {}
    for child, parent, kind in edges.iter_rows():
        if child in parents or child not in records or parent not in records or kind != 'hierarchy':
            raise ValueError('duplicate child or missing parent/edge endpoint')
        parents[child] = parent
    for identifier, node in records.items():
        levels = tuple(NAICS_LEVELS.values()) if node['system'] == 'naics' else SOC_LEVELS
        if node['system'] not in ('naics', 'soc') or node['level'] not in levels:
            raise ValueError('unsupported classification level')
        depth = levels.index(node['level'])
        if (identifier in parents) != (depth > 0):
            raise ValueError('missing parent or parent on root')
        if depth:
            parent = records[parents[identifier]]
            if (parent['system'], parent['vintage'], parent['level']) != (
                node['system'], node['vintage'], levels[depth - 1]
            ):
                raise ValueError('contradictory immediate parent level')
        if identifier != f"{node['system']}:{node['vintage']}:{node['level']}:{node['code']}":
            raise ValueError('incompatible node_id')
    paths = []
    for identifier in sorted(records):
        chain, cursor = [], identifier
        while cursor is not None:
            if cursor in chain:
                raise ValueError('cycle in hierarchy')
            chain.append(cursor)
            cursor = parents.get(cursor)
        paths.append((identifier, list(reversed(chain))))
    return pl.DataFrame(paths, schema=PATH_SCHEMA, orient='row').sort('node_id')

def naics_tables(titles: pl.DataFrame, vintage: int):
    rows, edges = [], []
    selected = titles.filter(pl.col('vintage').eq(vintage))
    for code, title in selected.select('code', 'title').iter_rows():
        if code is None or not re.fullmatch(r'(?:[0-9]{2,6}|31-33|44-45|48-49)', code):
            raise ValueError('invalid NAICS structure code')
        width = 2 if '-' in code else len(code)
        level = NAICS_LEVELS[width]
        identifier = f'naics:{vintage}:{level}:{code}'
        rows.append((identifier, 'naics', vintage, level, code, title))
        if width > 2:
            prefix = code[:2]
            sector = next((r for r in ('31-33', '44-45', '48-49')
                           if int(r[:2]) <= int(prefix) <= int(r[-2:])), prefix)
            parent_code = sector if width == 3 else code[:-1]
            parent_level = NAICS_LEVELS[width - 1]
            edges.append((identifier, f'naics:{vintage}:{parent_level}:{parent_code}', 'hierarchy'))
    nodes = pl.DataFrame(rows, schema=NODE_SCHEMA, orient='row').sort('node_id')
    edge_frame = pl.DataFrame(edges, schema=EDGE_SCHEMA, orient='row').sort('child_id', 'parent_id')
    return nodes, edge_frame, forest(nodes, edge_frame)

def soc_tables(raw: pl.DataFrame):
    body = below_header(raw, ('major group', 'minor group', 'broad group', 'detailed occupation'))
    code_cols = [column(body, word) for word in ('major', 'minor', 'broad', 'detailed')]
    other = [c for c in body.columns if c not in code_cols]
    if len(other) != 1:
        raise ValueError('ambiguous SOC title column')
    rows, edges, current = [], [], {}
    for row in body.iter_rows(named=True):
        present = [(i, str(row[c]).strip()) for i, c in enumerate(code_cols)
                   if row[c] is not None and str(row[c]).strip()]
        if not present:
            continue
        if len(present) != 1:
            raise ValueError('multiple SOC codes in one row')
        depth, code = present[0]
        if re.fullmatch(r'[0-9]{6}', code):
            code = code[:2] + '-' + code[2:]
        if not re.fullmatch(r'[0-9]{2}-[0-9]{4}', code):
            raise ValueError('invalid SOC code')
        pattern_depth = 0 if code.endswith('0000') else 1 if code.endswith('00') else (
            2 if code.endswith('0') else 3
        )
        if pattern_depth != depth:
            raise ValueError('contradictory SOC column/level')
        level = SOC_LEVELS[depth]
        identifier = f'soc:2018:{level}:{code}'
        title = None if row[other[0]] is None else str(row[other[0]]).strip()
        rows.append((identifier, 'soc', 2018, level, code, title))
        if depth:
            if depth - 1 not in current:
                raise ValueError('missing SOC workbook parent')
            parent_id = current[depth - 1]
            if parent_id.rsplit(':', 1)[1][:2] != code[:2]:
                raise ValueError('contradictory SOC major group')
            edges.append((identifier, parent_id, 'hierarchy'))
        current[depth] = identifier
        for deeper in range(depth + 1, 4):
            current.pop(deeper, None)
    nodes = pl.DataFrame(rows, schema=NODE_SCHEMA, orient='row').sort('node_id')
    edge_frame = pl.DataFrame(edges, schema=EDGE_SCHEMA, orient='row').sort('child_id', 'parent_id')
    return nodes, edge_frame, forest(nodes, edge_frame)
```

The generic forest validator deliberately validates classification single parentage only; Stage 5 reuses the **schemas**, not this restriction for cross-state CBSA edges. Add a SOC test where a valid column-level code occurs under a contradictory major group; don't invent a prefix parent when nesting is absent.

- [x] **Step 4: Verify green and original-layout reads.** Run focused tests, then the milestone. Read the small XLSX fixtures through `pl.read_excel(..., has_header=False, read_options={'dtypes': 'string'})`; assert the same expected graph as the in-memory raw sheets. The SOC overflow must remain parented by nesting.
- [x] **Step 5: Commit/checkpoint.** `git add src/embedding_data/classification_tables.py tests/test_classification_tables.py tests/code_fixtures.py tests/fixtures/codes` then `git commit -m 'feat(codes): add validated classification forests and paths'`.

### Task 2: Complete direct relationships and reversible traversal

> Deviation: the owner approved shared degree-classification extraction; `b720046` preserves the parser and validator’s different window partitions. The shipped chain includes auxiliary 2002 as required by D2, despite the old four-vintage interface sentence.


**Files:** Create `src/embedding_data/naics_relationships.py`, `tests/test_naics_relationships.py`; extend `tests/code_fixtures.py`.

**Interfaces:** `parse_concordance(raw, source_vintage, target_vintage, source_file) -> pl.DataFrame`; `validate_relationships(relations, structures) -> None`; `candidates(relations, source_vintage, source_code, target_vintage) -> list[str]`. `structures` is the concatenation of validated NAICS node tables for 2007/2012/2017/2022. Traversal moves monotonically along the adjacent-vintage chain, not through canonical 2022 and back.

- [x] **Step 1: Write the failing relationship tests.** Hand-authored fixture pairs:

```python
# Append to tests/code_fixtures.py
def pair_sheet(source, target, pairs):
    rows = [[f'{source} NAICS Code', f'{source} NAICS Title\n(piece in {target})',
             f'{target} NAICS Code', f'{target} NAICS Title']]
    rows += [[a, 'Fixture source', b, 'Fixture target'] for a, b in pairs]
    return pl.DataFrame(rows, orient='row', schema={f'c{i}': pl.String for i in range(4)})

def toy_reference_tables():
    from embedding_data.classification_tables import naics_tables
    from embedding_data.naics_relationships import parse_concordance, validate_relationships
    native = []
    for v in (2002, 2007, 2012, 2017, 2022):
        leaves = ('111111', '111112', '111113') if v == 2022 else ('111111', '111112')
        nodes, edges, paths = naics_tables(titles(v, leaves), v)
        native.append(nodes)
        if v == 2022:
            canonical_paths = paths
    structures = pl.concat(native)
    frames = [parse_concordance(pair_sheet(a, b, pairs), a, b, f'fixture_{a}_{b}.xlsx')
              for a, b, pairs in [
                  (2002, 2007, [('111111', '111111'), ('111112', '111112')]),
                  (2007, 2012, [('111111', '111111'), ('111112', '111112')]),
                  (2012, 2017, [('111111', '111111'), ('111111', '111112'), ('111112', '111112')]),
                  (2017, 2022, [('111111', '111111'), ('111112', '111112'), ('111112', '111113')]),
              ]]
    relations = pl.concat(frames)
    validate_relationships(relations, structures)
    return structures, relations, canonical_paths

# tests/test_naics_relationships.py
import polars as pl
import pytest
from embedding_data import naics_relationships as nr
from code_fixtures import pair_sheet

def test_split_merge_degrees_and_reverse_candidates():
    pairs = [('111111', '111111'), ('111111', '111112'), ('111112', '111112')]
    out = nr.parse_concordance(pair_sheet(2012, 2017, pairs), 2012, 2017, 'fixture.xls')
    assert out['link_type'].to_list() == ['1:m', 'm:m', 'm:1']
    assert nr.candidates(out, 2012, '111111', 2017) == ['111111', '111112']
    assert nr.candidates(out, 2017, '111112', 2012) == ['111111', '111112']

def test_two_hops_and_equal_codes_do_not_shortcut():
    a = nr.parse_concordance(pair_sheet(2012, 2017, [('111111', '111111')]),
                             2012, 2017, 'a.xls')
    b = nr.parse_concordance(pair_sheet(2017, 2022, [('111111', '111111'),
                                                   ('111111', '111112')]),
                             2017, 2022, 'b.xls')
    assert nr.candidates(pl.concat([a, b]), 2012, '111111', 2022) == ['111111', '111112']
    with pytest.raises(ValueError, match='bridge'):
        nr.candidates(a, 2012, '111111', 2022)
```

Add a full 2×2 reshuffle expecting all `m:m`, a 1:1 recode, duplicated official pair rows expecting one distinct pair, and endpoint/missing-coverage failures against tiny structures. Reordering pair-sheet data rows must leave sorted logical outputs identical; include multiline title headers so a title's explanatory target-year text cannot select a code column.

- [x] **Step 2: Verify red.** `uv run --locked pytest tests/test_naics_relationships.py -q` fails for absent module.
- [x] **Step 3: Implement the complete pair relation and traversal.**

```python
import polars as pl
from embedding_data.classification_tables import below_header, column

CHAIN = (2002, 2007, 2012, 2017, 2022)
RELATION_SCHEMA = {'source_vintage': pl.Int64, 'target_vintage': pl.Int64,
                   'source_code': pl.String, 'target_code': pl.String,
                   'link_type': pl.String, 'source_file': pl.String}

def parse_concordance(raw, source_vintage, target_vintage, source_file):
    body = below_header(raw, (str(source_vintage), str(target_vintage), 'code'))
    source = column(body, str(source_vintage), 'code')
    target = column(body, str(target_vintage), 'code')
    pairs = body.select(*[
        pl.col(c).cast(pl.String).str.strip_chars().str.replace(r'\.0$', '').alias(name)
        for c, name in [(source, 'source_code'), (target, 'target_code')]
    ]).filter(pl.any_horizontal(pl.all().is_not_null()))
    if pairs.is_empty() or pairs.filter(pl.any_horizontal([
        pl.col(c).str.contains(r'^[0-9]{6}$').not_().fill_null(True)
        for c in pairs.columns
    ])).height:
        raise ValueError('invalid or incomplete concordance endpoint')
    pairs = pairs.unique().sort('source_code', 'target_code')
    outgoing = pl.col('target_code').n_unique().over('source_code').gt(1)
    incoming = pl.col('source_code').n_unique().over('target_code').gt(1)
    return pairs.with_columns(
        source_vintage=pl.lit(source_vintage, dtype=pl.Int64),
        target_vintage=pl.lit(target_vintage, dtype=pl.Int64),
        source_file=pl.lit(source_file),
        link_type=pl.when(outgoing.and_(incoming)).then(pl.lit('m:m'))
        .when(outgoing).then(pl.lit('1:m')).when(incoming).then(pl.lit('m:1'))
        .otherwise(pl.lit('1:1')),
    ).select(list(RELATION_SCHEMA))

def validate_relationships(relations, structures):
    if relations.schema != RELATION_SCHEMA:
        raise ValueError('incompatible relationship schema')
    if any(relations[c].null_count() for c in relations.columns) or relations.filter(
        pl.col('source_file').str.strip_chars().eq('')
    ).height:
        raise ValueError('null relationship field or empty provenance')
    if relations.select('source_vintage', 'target_vintage', 'source_code', 'target_code').is_duplicated().any():
        raise ValueError('duplicate relationship pair')
    partition = ['source_vintage', 'target_vintage']
    outgoing = pl.col('target_code').n_unique().over([*partition, 'source_code']).gt(1)
    incoming = pl.col('source_code').n_unique().over([*partition, 'target_code']).gt(1)
    expected = pl.when(outgoing.and_(incoming)).then(pl.lit('m:m')).when(outgoing).then(
        pl.lit('1:m')
    ).when(incoming).then(pl.lit('m:1')).otherwise(pl.lit('1:1'))
    if relations.filter(pl.col('link_type').ne(expected)).height:
        raise ValueError('corrupt relationship degree classification')
    if set(relations.select('source_vintage', 'target_vintage').unique().iter_rows()) != set(zip(CHAIN, CHAIN[1:])):
        raise ValueError('missing or extra vintage bridge')
    for source, target in zip(CHAIN, CHAIN[1:]):
        pair = relations.filter(pl.col('source_vintage').eq(source).and_(pl.col('target_vintage').eq(target)))
        for vintage, name in [(source, 'source_code'), (target, 'target_code')]:
            leaves = set(structures.filter(pl.col('vintage').eq(vintage).and_(
                pl.col('level').eq('national_industry')
            ))['code'].to_list())
            if not leaves or set(pair[name].to_list()) != leaves:
                raise ValueError(f'{vintage}: invalid endpoint or incomplete bridge coverage')

def candidates(relations, source_vintage, source_code, target_vintage):
    if source_vintage not in CHAIN or target_vintage not in CHAIN:
        raise ValueError('unsupported bridge vintage')
    codes = {source_code}
    start, stop = CHAIN.index(source_vintage), CHAIN.index(target_vintage)
    step = 1 if stop > start else -1
    for i in range(start, stop, step):
        a, b = CHAIN[i], CHAIN[i + step]
        source, target = min(a, b), max(a, b)
        pair = relations.filter(pl.col('source_vintage').eq(source).and_(pl.col('target_vintage').eq(target)))
        left, right = ('source_code', 'target_code') if step == 1 else ('target_code', 'source_code')
        if not codes.issubset(set(pair[left].to_list())):
            raise ValueError('missing bridge for supported candidate')
        codes = set(pair.filter(pl.col(left).is_in(sorted(codes)))[right].to_list())
    return sorted(codes)
```

The validation boundary recalculates degree classifications within each vintage pair, so a corrupted stored relationship cannot claim 1:1. Its regression changes the first split row's `link_type` to `1:1` and expects `ValueError` matching `degree`.

- [x] **Step 4: Verify green.** Run the focused suite and milestone, including both-side complete coverage and shuffled-pair determinism.
- [x] **Step 5: Commit/checkpoint.** `git add src/embedding_data/naics_relationships.py tests/test_naics_relationships.py tests/code_fixtures.py` then `git commit -m 'feat(codes): preserve complete NAICS vintage relationships'`.

### Task 3: Original filing lists and versioned expansion

**Files:** Create `src/embedding_data/filing_rules.py`, `tests/test_filing_rules.py`; add small preformatted rule HTML fixtures under `tests/fixtures/codes/`.

**Interfaces:** `parse_rule(text: str, rule_id: str) -> list[str]` returns original labels; `expand_rule(codes, rule_id, structures, source_file) -> pl.DataFrame` remains a strict native expansion; `rule_tables(listed, structures, relations, sources) -> dict[str, pl.DataFrame]` produces labels, definite memberships and complete membership possibilities under Task 0's D2-adopted schemas. `legacy_membership(whole, legacy_leaves, predecessors) -> dict[str, tuple[list[bool], bool]]` preserves all incoming paths. Task 6 extends this same module with evaluation.

- [x] **Step 1: Write parser tests before implementation.**

```python
import polars as pl
import pytest
from embedding_data import filing_rules as fr
from code_fixtures import toy_reference_tables

@pytest.fixture
def filing_fixture():
    structures, relations, paths = toy_reference_tables()
    listed = {'designated_2012': ['111111'], 'designated_2017': ['111112'],
              'partially_exempt_2007': ['111112']}
    tables = fr.rule_tables(listed, structures, relations, {k: f'{k}.htm' for k in listed})
    return structures, relations, tables['membership']

def test_final_appendix_a_is_bounded_before_b():
    html = '''<html><pre>Discussion of Appendix A to Subpart E of Part 1904
9999........... Preamble example
Appendix A to Subpart E of Part 1904--Designated Industries
NAICS Industry
11............. Fixture agriculture
31-33.......... Fixture manufacturing
Appendix B to Subpart E of Part 1904--Other Submission
9999........... Must not enter Appendix A
</pre></html>'''
    assert fr.parse_rule(html, 'designated_2017', expected_count=2) == ['11', '31-33']
    with pytest.raises(ValueError, match='count'):
        fr.parse_rule(html, 'designated_2017')

@pytest.mark.parametrize('html', [
    '<html><title>Request Access</title></html>',
    '<html><pre>Appendix A to Subpart E of Part 1904\n11...... A\n11...... B</pre></html>',
])
def test_challenge_or_duplicate_list_refused(html):
    with pytest.raises(ValueError):
        fr.parse_rule(html, 'designated_2012', expected_count=2)

def test_bounded_bridge_preserves_mixed_predecessors_and_whole_exemptions():
    predecessors = {'517110': {'517110', '517510', '518111'},
                    '517911': {'517310'}, '517919': {'518111', '517910'},
                    '519130': {'518112', '519110'}, '541110': {'541110'}}
    bits = fr.legacy_membership({'517911', '517919', '519130'},
                                {'517310', '518111', '518112'}, predecessors)
    assert bits['517110'] == ([False, True], True)
    assert bits['517911'] == ([True], True)
    assert bits['517919'] == ([True], True)
    assert bits['519130'] == ([True], True)
    assert bits['541110'] == ([False], False)
    with pytest.raises(ValueError, match='predecessor'):
        fr.legacy_membership(set(), {'518111'}, {'517110': set()})
```

Add expansion tests with the tiny Task 1 forest: `11` expands to both leaves; an absent listed node fails; multiple overlapping listed nodes cannot generate duplicate membership. Assert exact Date types and closed/open effective intervals. Include missing list row, invalid code-like row, missing title and page-break/continued-title fixtures.

- [x] **Step 2: Verify red.** `uv run --locked pytest tests/test_filing_rules.py -q` fails for absent module.
- [x] **Step 3: Implement original-text parsing and native-vintage expansion.**

```python
import re
from datetime import date
from html.parser import HTMLParser
import polars as pl
from embedding_data.classification_tables import naics_tables

RULES = {
    'designated_2012': (2012, date(2017, 1, 1), date(2023, 12, 31), 'E', 66),
    'designated_2017': (2017, date(2024, 1, 1), None, 'E', 65),
    'partially_exempt_2007': (2007, date(2015, 1, 1), None, 'B', 82),
}
RULE_SCHEMA = {'rule_id': pl.String, 'vintage': pl.Int64, 'code': pl.String,
               'effective_from': pl.Date, 'effective_to': pl.Date, 'source_file': pl.String}

class OriginalText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)

def parse_rule(text, rule_id, *, expected_count=None):
    if rule_id not in RULES:
        raise ValueError('unknown rule identity')
    reader = OriginalText()
    reader.feed(text)
    original = ''.join(reader.parts)
    part, count = RULES[rule_id][3:]
    heading = f'Appendix A to Subpart {part} of Part 1904'
    # The final enacted appendix follows the discussions and proposed tables.
    start = original.rfind(heading)
    challenge = re.search(r'<title>[^<]*(?:request access|access denied)', text, re.IGNORECASE)
    if start < 0 or challenge:
        raise ValueError('original final appendix missing or challenge HTML')
    tail = original[start + len(heading):]
    next_appendix = re.search(r'^Appendix [A-Z] to Subpart [A-Z]', tail, re.MULTILINE)
    if next_appendix:
        tail = tail[:next_appendix.start()]
    dotted_lines = [line for line in tail.splitlines()
                    if re.match(r'^[^ \t].*\.{2,}', line)]
    entries = [re.fullmatch(r'([0-9]{2,6}|31-33|44-45|48-49)\.{2,}[ \t]+(\S.*)', line)
               for line in dotted_lines]
    if any(match is None for match in entries):
        raise ValueError('malformed or untitled final-table row')
    codes = [match[1] for match in entries]
    if len(codes) != (count if expected_count is None else expected_count):
        raise ValueError('filing appendix count changed')
    if len(codes) != len(set(codes)):
        raise ValueError('duplicate listed rule code')
    return sorted(codes)

def expand_rule(codes, rule_id, structures, source_file):
    vintage, start, end, part, count = RULES[rule_id]
    native = structures.filter(pl.col('vintage').eq(vintage))
    known = set(native['code'].to_list())
    if not codes or len(codes) != len(set(codes)) or not set(codes).issubset(known):
        raise ValueError('invalid or duplicate listed rule node')
    # Reconstruct paths from validated native parentage, not cross-vintage prefix matching.
    titles = native.select('vintage', 'code', 'title')
    nodes, edges, paths = naics_tables(titles, vintage)
    listed_ids = set(native.filter(pl.col('code').is_in(codes))['node_id'].to_list())
    leaves = native.filter(pl.col('level').eq('national_industry'))
    path_of = dict(paths.iter_rows())
    members = [r['code'] for r in leaves.iter_rows(named=True)
               if listed_ids.intersection(path_of[r['node_id']])]
    if not members:
        raise ValueError('empty expanded rule')
    return pl.DataFrame([
        (rule_id, vintage, code, start, end, source_file) for code in sorted(members)
    ], schema=RULE_SCHEMA, orient='row')

def validate_rules(rules, structures):
    if rules.schema != RULE_SCHEMA or rules.select('rule_id', 'code').is_duplicated().any():
        raise ValueError('incompatible or duplicate rule membership')
    if any(rules[c].null_count() for c in rules.columns if c != 'effective_to'):
        raise ValueError('null required rule field')
    if set(rules['rule_id'].to_list()) != set(RULES):
        raise ValueError('missing or extra rule identity')
    for identity, (vintage, start, end, part, count) in RULES.items():
        group = rules.filter(pl.col('rule_id').eq(identity))
        leaves = set(structures.filter(pl.col('vintage').eq(vintage).and_(
            pl.col('level').eq('national_industry')
        ))['code'].to_list())
        if not set(group['code'].to_list()).issubset(leaves) or group.filter(
            pl.col('vintage').ne(vintage).or_(pl.col('effective_from').ne(start)).or_(
                pl.col('effective_to').ne_missing(pl.lit(end, dtype=pl.Date))
            )
        ).height:
            raise ValueError('invalid rule vintage, period or endpoint')
        if group['source_file'].n_unique() != 1 or group['source_file'][0].strip() == '':
            raise ValueError('invalid rule provenance')

LEGACY_LABELS = {'5173': 2002, '5181': 2002}
LABEL_SCHEMA = {'rule_id': pl.String, 'vintage': pl.Int64, 'listed_code': pl.String,
                'label_vintage': pl.Int64, 'flag_rule_label_legacy': pl.Boolean,
                'source_file': pl.String}
MEMBERSHIP_SCHEMA = {**RULE_SCHEMA, 'membership_candidates': pl.List(pl.Boolean),
                     'flag_rule_label_bridged': pl.Boolean}

def legacy_membership(whole, legacy_leaves, predecessors):
    result = {}
    for code, incoming in sorted(predecessors.items()):
        if not incoming:
            raise ValueError('missing legacy predecessor coverage')
        touched = bool(set(incoming).intersection(legacy_leaves))
        bits = {True} if code in whole else {p in legacy_leaves for p in incoming}
        result[code] = (sorted(bits), touched)
    return result

def rule_tables(listed, structures, relations, sources):
    label_rows, membership_rows = [], []
    for identity, codes in listed.items():
        vintage, start, end, part, count = RULES[identity]
        native = structures.filter(pl.col('vintage').eq(vintage))
        known = set(native['code'].to_list())
        exceptions = set(codes).difference(known)
        if identity != 'partially_exempt_2007' and exceptions:
            raise ValueError('invalid nonexemption listed rule node')
        if not exceptions.issubset(LEGACY_LABELS):
            raise ValueError('unsupported legacy rule label')
        valid = sorted(set(codes).intersection(known))
        if not codes or len(codes) != len(set(codes)):
            raise ValueError('empty or duplicate original rule labels')
        whole = set(expand_rule(valid, identity, structures, sources[identity])['code'].to_list()) if valid else set()
        leaves = set(native.filter(pl.col('level').eq('national_industry'))['code'].to_list())
        bits = {code: ([code in whole], False) for code in leaves}
        for code in codes:
            label_rows.append((identity, vintage, code,
                               LEGACY_LABELS[code] if code in exceptions else vintage,
                               code in exceptions, sources[identity]))
        if exceptions:
            old = structures.filter(pl.col('vintage').eq(2002))
            if not exceptions.issubset(set(old['code'].to_list())):
                raise ValueError('legacy label missing from 2002 structure')
            old_nodes, old_edges, old_paths = naics_tables(old.select('vintage', 'code', 'title'), 2002)
            exception_ids = set(old.filter(pl.col('code').is_in(sorted(exceptions)))['node_id'].to_list())
            paths_by_id = dict(old_paths.iter_rows())
            legacy_leaves = {code for identifier, code in old.filter(
                pl.col('level').eq('national_industry')
            ).select('node_id', 'code').iter_rows() if exception_ids.intersection(paths_by_id[identifier])}
            bridge = relations.filter(pl.col('source_vintage').eq(2002).and_(
                pl.col('target_vintage').eq(2007)
            ))
            predecessors = {}
            for source, target in bridge.select('source_code', 'target_code').iter_rows():
                predecessors.setdefault(target, set()).add(source)
            if set(predecessors) != leaves or not legacy_leaves.issubset(set(bridge['source_code'].to_list())):
                raise ValueError('incomplete legacy bridge')
            bits = legacy_membership(whole, legacy_leaves, predecessors)
        for code in sorted(leaves):
            possibilities, touched = bits[code]
            membership_rows.append((identity, vintage, code, start, end, sources[identity],
                                    possibilities, touched))
    labels = pl.DataFrame(label_rows, schema=LABEL_SCHEMA, orient='row').sort('rule_id', 'listed_code')
    membership = pl.DataFrame(membership_rows, schema=MEMBERSHIP_SCHEMA, orient='row').sort('rule_id', 'code')
    definite = membership.filter(pl.col('membership_candidates').list.len().eq(1).and_(
        pl.col('membership_candidates').list.contains(True)
    )).select(list(RULE_SCHEMA))
    validate_rules(definite, structures)
    validate_membership(membership, structures)
    return {'labels': labels, 'rules': definite, 'membership': membership}

def validate_membership(membership, structures):
    if membership.schema != MEMBERSHIP_SCHEMA or membership.select('rule_id', 'code').is_duplicated().any():
        raise ValueError('incompatible or duplicate rule possibilities')
    if any(membership[c].null_count() for c in membership.columns if c != 'effective_to'):
        raise ValueError('null required membership field')
    if set(membership['rule_id'].to_list()) != set(RULES):
        raise ValueError('missing membership rule identity')
    for identity, (vintage, start, end, part, count) in RULES.items():
        group = membership.filter(pl.col('rule_id').eq(identity))
        leaves = set(structures.filter(pl.col('vintage').eq(vintage).and_(
            pl.col('level').eq('national_industry')
        ))['code'].to_list())
        if set(group['code'].to_list()) != leaves:
            raise ValueError('incomplete rule membership coverage')
        if group.filter(pl.col('vintage').ne(vintage).or_(pl.col('effective_from').ne(start)).or_(
            pl.col('effective_to').ne_missing(pl.lit(end, dtype=pl.Date))
        )).height:
            raise ValueError('invalid membership vintage or period')
        for possibilities, touched in group.select('membership_candidates', 'flag_rule_label_bridged').iter_rows():
            if possibilities not in ([False], [True], [False, True]):
                raise ValueError('invalid or empty membership possibility set')
            if len(possibilities) > 1 and (identity != 'partially_exempt_2007' or not touched):
                raise ValueError('unexplained reference membership ambiguity')
```

The final-table dotted rows are individually validated; horizontal whitespace cannot consume a newline and disguise a missing title. Wrapped titles, published separators and `[[Page ...]]` markers remain outside the code rows. Production group counts stay pinned; the expected-count parameter is a pure parser fixture seam. `expand_rule` remains strict: only `rule_tables` can interpret the two allowlisted original exemption labels through validated 2002 ancestry. Every other unmatched label fails. Definite memberships are the `[True]` projection of the complete possibilities table; mixed membership never enters that projection.

- [x] **Step 4: Verify green and official-format boundary.** Run focused checks and milestone. The 2023 fixture includes an Appendix B distraction; its codes must never enter `designated_2017`. Periods use nominal submission dates (filing year plus one) and inclusive `effective_to`.
- [x] **Step 5: Commit/checkpoint.** `git add src/embedding_data/filing_rules.py tests/test_filing_rules.py tests/fixtures/codes` then `git commit -m 'feat(codes): parse versioned filing-industry appendices'`.

### Task 4: Registered immutable reference acquisition and import

> Deviation: `8f5d67d` adds staged-copy hash verification and atomic no-overwrite hard-link publication; `412a0d4` makes cleanup conditional on exclusive staging ownership. Both refinements have reproduced regression evidence and clean review.


**Files:** Create `src/embedding_data/code_references.py`, `tests/test_code_references.py`. Existing Stage 3 readers remain unchanged.

**Interfaces:** `Reference(kind, url, relative, family, vintage=None, target=None, expected=None)`; `REGISTRY: dict[str, Reference]`; `reference_path(data_dir, reference) -> Path`; `parse_naics_text(text, vintage) -> pl.DataFrame`; `parse_reference(file, reference) -> pl.DataFrame | list[str]`; `acquire(data_dir, *, registry=REGISTRY) -> list[Path]`; `import_reference(data_dir, kind, original, *, registry=REGISTRY) -> Path`; `read_references(data_dir, *, registry=REGISTRY) -> dict[str, pl.DataFrame]`. The injectable registry is a library fixture seam, never a CLI option or runtime skill dependency. The reader returns structures, SOC nodes, relations, original group counts, definite rules, original labels and complete membership possibilities.

- [x] **Step 1: Write failing acquisition/import tests.** Use a committed tiny actual XLSX matching Task 1's NAICS fixture and a fixture registry with explicit small counts. Include this immutable import test:

```python
from dataclasses import replace
from pathlib import Path
import pytest
from embedding_data import code_references as cr, manifest, paths

def test_import_is_original_bytes_and_verified_idempotent(tmp_path):
    original = tmp_path / 'original.xlsx'
    original.write_bytes((Path(__file__).parent /
                          'fixtures/codes/naics_2022_tiny.xlsx').read_bytes())
    reference = replace(cr.REGISTRY['naics_2022'], relative='naics/fixture.xlsx', expected=(6, 2))
    registry = {reference.kind: reference}
    destination = cr.import_reference(tmp_path, reference.kind, original, registry=registry)
    assert destination.read_bytes() == original.read_bytes()
    citation = manifest.entry_for(paths.manifest_path(tmp_path), destination)
    assert citation.proxies == ('retrieved_at',)
    before = paths.manifest_path(tmp_path).read_bytes()
    assert cr.import_reference(tmp_path, reference.kind, original, registry=registry) == destination
    assert paths.manifest_path(tmp_path).read_bytes() == before
    destination.write_bytes(b'changed')
    with pytest.raises(ValueError, match='SHA-256'):
        cr.import_reference(tmp_path, reference.kind, original, registry=registry)
```

Add a streamed `httpx.MockTransport` response carrying the actual workbook bytes. Call acquisition twice: one request, unchanged manifest/raw bytes on replay. Then independently test missing recorded original, existing unrecorded original, different valid import bytes under one identity, invalid HTML masquerading as XLSX, challenge HTML for a rule, interrupted `.part`, and an invalid second registered destination: batch preflight must issue zero HTTP requests. Set a temporary registry's BLS URL, remove `BLS_CONTACT_EMAIL`, and assert the missing SOC acquisition names manual import before any BLS request. Existing/imported SOC must read offline without that environment variable.

- [x] **Step 2: Verify red.** `uv run --locked pytest tests/test_code_references.py -q` fails for absent module.
- [x] **Step 3: Implement registry, validators and acquisition boundary.** Registry literals use the exact official URLs in Entry evidence. New paths: `naics/naics07.xls`, `naics/<original concordance filename>`, `soc/soc_structure_2018.xlsx`, and `filing-rules/<FR document ID>.htm`. Existing 2012/2017/2022 paths stay `naics/<TITLE_FILES basename>`.

```python
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
import httpx
import polars as pl
from embedding_data import ita_references, manifest, paths
from embedding_data.classification_tables import naics_tables, soc_tables
from embedding_data.naics_relationships import parse_concordance, validate_relationships
from embedding_data.filing_rules import parse_rule, rule_tables
from embedding_data.osha_benchmark_download import download, USER_AGENT

@dataclass(frozen=True)
class Reference:
    kind: str
    url: str
    relative: str
    family: str
    vintage: int | None = None
    target: int | None = None
    expected: tuple[int, int] | int | None = None

REGISTRY = {
    f'naics_{v}': Reference(f'naics_{v}', url, 'naics/' + url.rsplit('/', 1)[1],
                          'naics', v, expected=counts)
    for v, url, counts in [(v, ita_references.TITLE_FILES[v], counts)
                          for v, counts in [(2012, (2209, 1065)), (2017, (2196, 1057)),
                                            (2022, (2125, 1012))]]
}
REGISTRY['naics_2007'] = Reference(
    'naics_2007', 'https://www.census.gov/naics/reference_files_tools/2007/naics07.xls',
    'naics/naics07.xls', 'naics', 2007, expected=(2328, 1175),
)
REGISTRY['naics_2002'] = Reference(
    'naics_2002', 'https://www.census.gov/naics/reference_files_tools/2002/naics_2_6_02.txt',
    'naics/naics_2_6_02.txt', 'naics_text', 2002, expected=(2341, 1179),
)
for source, target, suffix in [(2002, 2007, 'xls'), (2007, 2012, 'xls'), (2012, 2017, 'xlsx'), (2017, 2022, 'xlsx')]:
    filename = f'{source}_to_{target}_NAICS.{suffix}'
    kind = f'concordance_{source}_{target}'
    REGISTRY[kind] = Reference(kind, 'https://www.census.gov/naics/concordances/' + filename,
                               'naics/' + filename, 'concordance', source, target)
REGISTRY['soc_2018'] = Reference(
    'soc_2018', 'https://www.bls.gov/soc/2018/soc_structure_2018.xlsx',
    'soc/soc_structure_2018.xlsx', 'soc', 2018, expected=(1447, 867),
)
for kind, issue, document, count in [
    ('designated_2012', '2016-05-12', '2016-10443', 66),
    ('designated_2017', '2023-07-21', '2023-15091', 65),
    ('partially_exempt_2007', '2014-09-18', '2014-21514', 82),
]:
    REGISTRY[kind] = Reference(kind, f'https://www.govinfo.gov/content/pkg/FR-{issue}/html/{document}.htm',
                               f'filing-rules/{document}.htm', 'rule', expected=count)

def reference_path(data_dir, reference):
    return ita_references.reference_path(data_dir, reference.relative)

def parse_naics_text(text, vintage):
    import re
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    heading = f'Code    {vintage} NAICS Title'
    if lines.count(heading) != 1:
        raise ValueError('missing or ambiguous NAICS text header')
    rows = []
    for line in lines[lines.index(heading) + 1:]:
        match = re.fullmatch(r'([0-9]{2,6}|31-33|44-45|48-49)[ \t]+(\S.*)', line)
        if not match:
            raise ValueError('malformed NAICS text code/title row')
        rows.append((vintage, match[1], match[2]))
    return pl.DataFrame(rows, schema={'vintage': pl.Int64, 'code': pl.String,
                                       'title': pl.String}, orient='row')

def parse_reference(file, reference):
    if reference.family == 'rule':
        return parse_rule(file.read_text(encoding='utf-8'), reference.kind,
                          expected_count=reference.expected)
    if reference.family == 'naics_text':
        titles = parse_naics_text(file.read_text(encoding='utf-8'), reference.vintage)
        nodes, edges, graph_paths = naics_tables(titles, reference.vintage)
        actual = (nodes.height, nodes.filter(pl.col('level').eq('national_industry')).height)
        if actual != reference.expected:
            raise ValueError(f'{reference.kind}: structure counts changed: {actual}')
        return nodes
    raw = pl.read_excel(file, has_header=False, read_options={'dtypes': 'string'})
    if reference.family == 'concordance':
        return parse_concordance(raw, reference.vintage, reference.target,
                                 'references/' + reference.relative)
    if reference.family == 'naics':
        titles = ita_references.parse_titles(raw, reference.vintage)
        nodes, edges, graph_paths = naics_tables(titles, reference.vintage)
        finest = 'national_industry'
    elif reference.family == 'soc':
        nodes, edges, graph_paths = soc_tables(raw)
        finest = 'detailed'
    else:
        raise ValueError('unsupported reference family')
    actual = (nodes.height, nodes.filter(pl.col('level').eq(finest)).height)
    if actual != reference.expected:
        raise ValueError(f'{reference.kind}: structure counts changed: {actual}')
    return nodes

def preflight(data_dir, registry):
    result = {}
    for kind, reference in registry.items():
        destination = reference_path(data_dir, reference)
        if destination.is_symlink() or destination.with_name(destination.name + '.part').exists():
            raise ValueError(f'{kind}: symlink or interrupted reference')
        result[kind] = ita_references.existing_reference(data_dir, destination)
    return result

def publish_original(data_dir, reference, original, *, imported):
    destination = reference_path(data_dir, reference)
    if ita_references.existing_reference(data_dir, destination):
        if manifest.sha256_file(original) != manifest.sha256_file(destination):
            raise ValueError('registered original already has different bytes')
        return destination
    parse_reference(original, reference)
    citation = manifest.describe_file(
        original, original.parent, retrieved_at=datetime.now(UTC),
        client='manual-import' if imported else 'httpx',
        client_version=version('embedding-data') if imported else version('httpx'),
        source_url=reference.url, proxies=('retrieved_at',) if imported else (),
    )
    citation = replace(citation, path=destination.relative_to(paths.manifest_path(data_dir).parent).as_posix())
    manifest.check_appendable(paths.manifest_path(data_dir), [citation])
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + '.part')
    if partial.exists():
        raise ValueError('interrupted reference already exists')
    try:
        with partial.open('xb') as output, original.open('rb') as source:
            shutil.copyfileobj(source, output)
        # Re-check immediately before the publish boundary; never overwrite a destination.
        if destination.exists() or destination.is_symlink():
            raise ValueError('reference destination appeared during import')
        partial.rename(destination)
        manifest.append_entries(paths.manifest_path(data_dir), [citation])
    finally:
        partial.unlink(missing_ok=True)
    return destination

def import_reference(data_dir, kind, original, *, registry=REGISTRY):
    if kind not in registry:
        raise ValueError('unknown registered reference identity')
    preflight(data_dir, {kind: registry[kind]})
    return publish_original(data_dir, registry[kind], original, imported=True)

def acquire(data_dir, *, registry=REGISTRY):
    existing = preflight(data_dir, registry)
    missing_bls = any(not existing[k] and r.url.startswith('https://www.bls.gov/')
                      for k, r in registry.items())
    contact = os.environ.get('BLS_CONTACT_EMAIL', '').strip()
    if missing_bls and not contact:
        raise ValueError('set BLS_CONTACT_EMAIL or import-reference soc_2018 ORIGINAL')
    acquired = []
    with httpx.Client(http2=True, follow_redirects=True, timeout=120,
                      headers={'User-Agent': USER_AGENT}) as client:
        for kind, reference in registry.items():
            if existing[kind]:
                acquired.append(reference_path(data_dir, reference))
                continue
            headers = {'User-Agent': f'embedding-data-reference/0.1 (contact: {contact})'} if (
                reference.url.startswith('https://www.bls.gov/')
            ) else {'User-Agent': USER_AGENT}
            client.headers.update(headers)
            with tempfile.TemporaryDirectory() as temporary:
                original = Path(temporary) / Path(reference.relative).name
                download(client, reference.url, original)
                acquired.append(publish_original(data_dir, reference, original, imported=False))
    return acquired

def read_references(data_dir, *, registry=REGISTRY):
    parsed = {}
    for kind, reference in registry.items():
        file = reference_path(data_dir, reference)
        manifest.entry_for(paths.manifest_path(data_dir), file)
        parsed[kind] = parse_reference(file, reference)
    structures = pl.concat([parsed[f'naics_{v}'] for v in (2002, 2007, 2012, 2017, 2022)])
    relations = pl.concat([parsed[f'concordance_{a}_{b}'] for a, b in [(2002, 2007), (2007, 2012), (2012, 2017), (2017, 2022)]])
    validate_relationships(relations, structures)
    identities = ('designated_2012', 'designated_2017', 'partially_exempt_2007')
    rules = rule_tables({k: parsed[k] for k in identities}, structures, relations,
                        {k: 'references/' + registry[k].relative for k in identities})
    return {'structures': structures.sort('vintage', 'node_id'),
            'soc_nodes': parsed['soc_2018'], 'relations': relations.sort(
                'source_vintage', 'target_vintage', 'source_code', 'target_code'),
            'rule_groups': pl.DataFrame([
                (k, len(parsed[k])) for k in ('designated_2012', 'designated_2017', 'partially_exempt_2007')
            ], schema={'rule_id': pl.String, 'listed_groups': pl.Int64}, orient='row').sort('rule_id'),
            'rules': rules['rules'], 'rule_labels': rules['labels'], 'rule_membership': rules['membership']}
```

Task 1's edges/paths can be regenerated from validated nodes during build; SOC edges require its original sheet nesting, so Task 7 re-reads the verified SOC original and calls `soc_tables`, rather than deriving SOC edges from sorted nodes. Add reader failures for all missing/changed originals and incomplete full bridges. `preflight` runs even if all originals exist, and valid cached reads cannot require contact or network.

- [x] **Step 4: Verify green.** Focused tests and milestone. Verify each parser through genuine fixture bytes and each malformed original leaves no published raw file/manifest entry.
- [x] **Step 5: Commit/checkpoint.** `git add src/embedding_data/code_references.py tests/test_code_references.py` then `git commit -m 'feat(codes): acquire and import immutable official references'`.

### Task 5: Native lookup, uncertainty states and row-preserving join

> Deviation: Task 2 already supplied the complete toy references, so no redundant fixture edit was made. The shipped lookup additionally verifies native forests, canonical paths and full relationships before state construction.


**Files:** Create `src/embedding_data/ita_naics_mapping.py`, `tests/test_ita_naics_mapping.py`; extend `tests/code_fixtures.py` with the complete four-vintage toy relation.

**Interfaces:** `build_lookup(keys, structures, relations, code_paths) -> pl.DataFrame`; `enrich(source: pl.LazyFrame, lookup: pl.DataFrame) -> pl.LazyFrame`. Keys have `naics_code:String, naics_year:Int64`. The lookup retains those keys, including nulls, and every mapping column in the design's exact order/dtype. Auxiliary 2002/2007 structures are not admitted source vintages; a nonnull ITA vintage outside 2012/2017/2022 still fails.

- [x] **Step 1: Write failing state, provenance and join tests.** Build toy structures with leaves `111111,111112` for 2007/2012/2017 and `111111,111112,111113` for 2022. The complete pairs are: 2007→2012 `A→A,B→B`; 2012→2017 `A→A,A→B,B→B`; 2017→2022 `A→A,B→B,B→C`, with A/B/C denoting the three literal leaf codes.

```python
import polars as pl
import pytest
from embedding_data import ita_naics_mapping as mapping
from code_fixtures import toy_reference_tables

@pytest.fixture
def toy_references():
    return toy_reference_tables()

def test_all_states_and_unknown_singleton(toy_references):
    structures, relations, paths = toy_references
    keys = pl.DataFrame({'naics_code': [None, '111111', '111112', '111113', '111113', '999999'],
                         'naics_year': [2012, 2022, 2012, 2012, None, None]},
                        schema={'naics_code': pl.String, 'naics_year': pl.Int64})
    out = mapping.build_lookup(keys, structures, relations, paths)
    rows = {(r['naics_code'], r['naics_year']): r for r in out.to_dicts()}
    assert rows[(None, 2012)]['naics_mapping_status'] == 'missing_code'
    assert rows[('111111', 2022)]['naics_mapping_status'] == 'native_2022'
    assert rows[('111112', 2012)]['naics_2022_candidates'] == ['111112', '111113']
    assert rows[('111112', 2012)]['flag_naics_crosswalked'] is True
    assert rows[('111113', 2012)]['naics_mapping_status'] == 'invalid_native_code'
    unknown = rows[('111113', None)]
    assert unknown['naics_2022_candidates'] == ['111113']
    assert unknown['naics_2022_code'] is None
    assert unknown['flag_naics_unresolved'] is True
    assert rows[('999999', None)]['naics_mapping_status'] == 'unknown_vintage_unmapped'
    assert out.schema == mapping.LOOKUP_SCHEMA

@pytest.mark.parametrize('code,year', [('11111', 2012), ('１１１１１１', 2012), ('ABCDEF', 2012), ('111111', 2025)])
def test_malformed_or_incompatible_key_fails(toy_references, code, year):
    structures, relations, paths = toy_references
    keys = pl.DataFrame({'naics_code': [code], 'naics_year': [year]},
                        schema={'naics_code': pl.String, 'naics_year': pl.Int64})
    with pytest.raises(ValueError):
        mapping.build_lookup(keys, structures, relations, paths)
```

The `toy_references` fixture wraps Task 2's `toy_reference_tables`; expected candidate values above remain handwritten.

Add singleton historical recode, known mismatch valid in another vintage, unknown code supported in all three, candidates crossing sectors (null common ancestor), missing code with null vintage, and conflicting lookup duplicates. A property test permutes a source frame containing repeated identical rows and null-vintage keys; `enrich(...).select(source.columns)` must equal the input **in its current order**, with all multiplicities/flags unchanged. Unmatched lookup keys and reserved temporary-column collisions fail.

- [x] **Step 2: Verify red.** `uv run --locked pytest tests/test_ita_naics_mapping.py -q` fails for absent module.
- [x] **Step 3: Implement the unique lookup and join.**

```python
import re
import polars as pl
from embedding_data.naics_relationships import candidates

KEY_SCHEMA = {'naics_code': pl.String, 'naics_year': pl.Int64}
MAPPING_SCHEMA = {
    'naics_mapping_status': pl.String, 'naics_matching_vintages': pl.List(pl.Int64),
    'naics_2022_candidates': pl.List(pl.String), 'naics_2022_code': pl.String,
    'naics_2022_node_id': pl.String, 'naics_deepest_common_node_id': pl.String,
    'flag_naics_crosswalked': pl.Boolean, 'flag_naics_ambiguous': pl.Boolean,
    'flag_naics_unresolved': pl.Boolean,
}
LOOKUP_SCHEMA = {**KEY_SCHEMA, **MAPPING_SCHEMA}

def build_lookup(keys, structures, relations, code_paths):
    if keys.schema != KEY_SCHEMA or keys.is_duplicated().any():
        raise ValueError('incompatible or duplicate lookup key')
    leaves = {v: set(structures.filter(pl.col('vintage').eq(v).and_(
        pl.col('level').eq('national_industry')
    ))['code'].to_list()) for v in (2012, 2017, 2022)}
    path_of = dict(code_paths.iter_rows())
    canonical_nodes = {code: identifier for identifier, code in structures.filter(
        pl.col('vintage').eq(2022).and_(pl.col('level').eq('national_industry'))
    ).select('node_id', 'code').iter_rows()}
    rows = []
    for code, vintage in keys.iter_rows():
        if vintage is not None and vintage not in leaves:
            raise ValueError('incompatible nonnull NAICS vintage')
        if code is not None and not re.fullmatch(r'[0-9]{6}', code):
            raise ValueError('malformed source NAICS code')
        matching = [v for v in leaves if code in leaves[v]]
        interpretations = []
        if code is None:
            status, unresolved = 'missing_code', False
        elif vintage is not None:
            if code not in leaves[vintage]:
                status, unresolved = 'invalid_native_code', True
            else:
                status, unresolved = ('native_2022' if vintage == 2022 else 'concorded'), False
                interpretations = [vintage]
        else:
            status = 'unknown_vintage_candidates' if matching else 'unknown_vintage_unmapped'
            unresolved, interpretations = True, matching
        possible = sorted({target for v in interpretations for target in candidates(relations, v, code, 2022)})
        scalar = possible[0] if vintage is not None and interpretations and len(possible) == 1 else None
        chains = [path_of[canonical_nodes[target]] for target in possible]
        common = None
        for group in zip(*chains):
            if len(set(group)) != 1:
                break
            common = group[0]
        rows.append((code, vintage, status, matching, possible, scalar,
                     canonical_nodes[scalar] if scalar else None, common,
                     bool(possible) and any(v != 2022 for v in interpretations),
                     len(possible) > 1, unresolved))
    return pl.DataFrame(rows, schema=LOOKUP_SCHEMA, orient='row').sort('naics_code', 'naics_year', nulls_last=False)

def enrich(source, lookup):
    names = source.collect_schema().names()
    if '_code_row' in names or any(c in names for c in MAPPING_SCHEMA):
        raise ValueError('mapping output/temporary column collision')
    if lookup.schema != LOOKUP_SCHEMA or lookup.select(*KEY_SCHEMA).is_duplicated().any():
        raise ValueError('duplicate or incompatible mapping lookup')
    joined = source.with_row_index('_code_row').join(
        lookup.lazy(), on=list(KEY_SCHEMA), how='left', nulls_equal=True,
        validate='m:1', maintain_order='left',
    )
    if joined.select(pl.col('naics_mapping_status').is_null().any()).collect().item():
        raise ValueError('missing mapping lookup result')
    return joined.sort('_code_row').drop('_code_row').select(*names, *MAPPING_SCHEMA)
```

Before lookup construction, require Tasks 1/2's validated references; a missing canonical node/path or a supported code missing its bridge remains a build error. Add an exact corruption regression rather than catching `KeyError` and converting it to an unresolved source state.

- [x] **Step 4: Verify green.** Focused suite and milestone. Assert lists/flags never null, all candidates are canonical finest nodes, and unknown singleton never fills either canonical scalar column.
- [x] **Step 5: Commit/checkpoint.** `git add src/embedding_data/ita_naics_mapping.py tests/test_ita_naics_mapping.py tests/code_fixtures.py` then `git commit -m 'feat(ita): retain supported canonical candidates and uncertainty'`.

### Task 6: Filing-rule diagnostics on supported interpretations

> Deviation: boundary/correlation tests reuse complete five-vintage fixtures with an unrelated 2022 split retained. The controller repeated all required locked milestone commands because the initial report omitted `--locked`; all 427 tests and other checks passed.


**Files:** Extend `src/embedding_data/filing_rules.py`, `tests/test_filing_rules.py`.

**Interfaces:** `evaluate(year, code, vintage, size_class, structures, relations, rules) -> dict`; `build_filing_lookup(keys, structures, relations, rules) -> pl.DataFrame`; `add_filing_flags(source, lookup) -> pl.LazyFrame`. Here `rules` is the complete `MEMBERSHIP_SCHEMA` possibilities table, not the definite-members projection. Lookup keys are `year_filing_for:Int64, naics_code:String, naics_year:Int64, size_class:Int64`. Added columns: `filing_industry_status:String`, `flag_outside_filing_industry:Boolean` (nullable), `flag_outside_filing_rule:Boolean` (nullable), `flag_filing_rule_label_bridged:Boolean`, `flag_filing_reference_ambiguous:Boolean` (both nonnullable).

- [x] **Step 1: Write failing evaluator tests.** Use the complete toy relationship fixtures plus native rule memberships. Explicitly test this truth table; all sources/graphs are tiny validated tables.

```python
@pytest.mark.parametrize('size,code,vintage,status,industry,overall', [
    (None, '111111', 2012, 'missing_size', None, None),
    (1, None, None, 'not_applicable_below_size', None, True),
    (2, None, 2012, 'missing_code', None, None),
    (2, '999999', 2012, 'invalid_native_code', None, None),
    (3, '999999', None, 'unknown_vintage_unmapped', None, None),
])
def test_filing_status_precedence(filing_fixture, size, code, vintage, status, industry, overall):
    structures, relations, rules = filing_fixture
    result = fr.evaluate(2022, code, vintage, size, structures, relations, rules)
    assert result == {'filing_industry_status': status,
                      'flag_outside_filing_industry': industry,
                      'flag_outside_filing_rule': overall,
                      'flag_filing_rule_label_bridged': False,
                      'flag_filing_reference_ambiguous': False}

@pytest.mark.parametrize('size,status,outside', [(2, 'determinate', True),
                                               (3, 'candidate_disagreement', None)])
def test_reference_ambiguity_can_survive_final_unanimity(filing_fixture, size, status, outside):
    structures, relations, membership = filing_fixture
    selected = pl.col('rule_id').eq('partially_exempt_2007').and_(pl.col('code').eq('111112'))
    membership = membership.with_columns(
        membership_candidates=pl.when(selected).then(pl.lit([False, True], dtype=pl.List(pl.Boolean))).otherwise(
            pl.col('membership_candidates')
        ), flag_rule_label_bridged=selected,
    )
    result = fr.evaluate(2022, '111112', 2012, size, structures, relations, membership)
    assert result['filing_industry_status'] == status
    assert result['flag_outside_filing_industry'] is outside
    assert result['flag_filing_reference_ambiguous'] is True
    assert result['flag_filing_rule_label_bridged'] is True
```

Add all-in/all-out/mixed evaluations, known singleton and unknown singleton, class 3's exemption-only traversal, class 2's Cartesian possibilities, and bridge-corruption failure. Boundary fixture: original designated_2012 contains `111111`; designated_2017 omits it but contains `111112`; make the tested code 1:1 and nonexempt. Filing years 2022/2023 yield opposite results. Change `annual_average_employees` while retaining size class and assert identical flags.

For the correlation regression, use 2012→2017 `111111→111112,111112→111111`, 2007→2012 identity pairs, and 2017→2022 identity pairs. Designated_2012 and exempt_2007 each contain only `111111`. An unknown-vintage `111111` in filing year 2022, size class 2, is **outside in every interpretation**: native 2012 is both designated/exempt; native 2017/2022 is neither. Pooling candidates across interpretations would invent a designated/nonexempt combination and incorrectly return null. Assert determinate true and preserve mapping's unknown/unresolved flags in the enriched table.

- [x] **Step 2: Verify red.** Run the focused evaluator tests; expect missing `evaluate`, not failed fixture coverage.
- [x] **Step 3: Implement direct-vintage conservative evaluation and unique join.** Append this to `filing_rules.py`:

```python
from itertools import product
from embedding_data.naics_relationships import candidates

FILING_KEYS = {'year_filing_for': pl.Int64, 'naics_code': pl.String,
               'naics_year': pl.Int64, 'size_class': pl.Int64}
FILING_COLUMNS = {'filing_industry_status': pl.String,
                  'flag_outside_filing_industry': pl.Boolean, 'flag_outside_filing_rule': pl.Boolean,
                  'flag_filing_rule_label_bridged': pl.Boolean, 'flag_filing_reference_ambiguous': pl.Boolean}
FILING_LOOKUP_SCHEMA = {**FILING_KEYS, **FILING_COLUMNS}

def active_rule(rules, family, nominal_date):
    selected = rules.filter(pl.col('rule_id').str.starts_with(family).and_(
        pl.col('effective_from').le(nominal_date)
    ).and_(pl.col('effective_to').is_null().or_(pl.col('effective_to').ge(nominal_date))))
    identities = selected.select('rule_id', 'vintage').unique()
    if identities.height != 1:
        raise ValueError('unsupported or overlapping filing-rule period')
    rule_id, vintage = identities.row(0)
    return vintage, {code: (possibilities, touched) for code, possibilities, touched in selected.select(
        'code', 'membership_candidates', 'flag_rule_label_bridged'
    ).iter_rows()}

def evaluate(year, code, vintage, size_class, structures, relations, rules):
    if year is None:
        raise ValueError('missing filing year')
    if code is not None and not re.fullmatch(r'[0-9]{6}', code):
        raise ValueError('malformed source NAICS code')
    nominal = date(year + 1, 1, 1)
    designated_vintage, designated = active_rule(rules, 'designated_', nominal)
    exempt_vintage, exempt = active_rule(rules, 'partially_exempt_', nominal)
    leaves = {v: set(structures.filter(pl.col('vintage').eq(v).and_(
        pl.col('level').eq('national_industry')
    ))['code'].to_list()) for v in (2012, 2017, 2022)}
    if vintage is not None and vintage not in leaves:
        raise ValueError('incompatible native vintage')
    if size_class not in (None, 1, 2, 3):
        raise ValueError('unsupported harmonized size class')
    outside, bridged, reference_ambiguous = None, False, False
    if size_class is None:
        status = 'missing_size'
    elif size_class == 1:
        status = 'not_applicable_below_size'
    elif code is None:
        status = 'missing_code'
    elif vintage is not None and code not in leaves[vintage]:
        status = 'invalid_native_code'
    else:
        interpretations = [vintage] if vintage is not None else [v for v in leaves if code in leaves[v]]
        if not interpretations:
            status = 'unknown_vintage_unmapped'
        else:
            evaluations = set()
            for native in interpretations:
                exemption = candidates(relations, native, code, exempt_vintage)
                if not set(exemption).issubset(exempt):
                    raise ValueError('missing rule membership candidate')
                bridged = bridged or any(exempt[e][1] for e in exemption)
                reference_ambiguous = reference_ambiguous or any(len(exempt[e][0]) > 1 for e in exemption)
                exempt_bits = {bit for e in exemption for bit in exempt[e][0]}
                if size_class == 3:
                    evaluations.update(exempt_bits)
                else:
                    designation = candidates(relations, native, code, designated_vintage)
                    if not set(designation).issubset(designated):
                        raise ValueError('missing designated membership candidate')
                    designated_bits = {bit for d in designation for bit in designated[d][0]}
                    evaluations.update(not d or e for d, e in product(designated_bits, exempt_bits))
            if len(evaluations) == 1:
                status, outside = 'determinate', evaluations.pop()
            else:
                status = 'candidate_disagreement'
    return {'filing_industry_status': status, 'flag_outside_filing_industry': outside,
            'flag_outside_filing_rule': True if size_class == 1 else outside,
            'flag_filing_rule_label_bridged': bridged,
            'flag_filing_reference_ambiguous': reference_ambiguous}

def build_filing_lookup(keys, structures, relations, rules):
    if keys.schema != FILING_KEYS or keys.is_duplicated().any():
        raise ValueError('duplicate or incompatible filing lookup key')
    validate_membership(rules, structures)
    rows = []
    for row in keys.iter_rows(named=True):
        result = evaluate(row['year_filing_for'], row['naics_code'], row['naics_year'],
                          row['size_class'], structures, relations, rules)
        rows.append({**row, **result})
    return pl.DataFrame(rows, schema=FILING_LOOKUP_SCHEMA).sort(list(FILING_KEYS), nulls_last=False)

def add_filing_flags(source, lookup):
    names = source.collect_schema().names()
    if '_filing_row' in names or any(c in names for c in FILING_COLUMNS):
        raise ValueError('filing output/temporary column collision')
    if lookup.schema != FILING_LOOKUP_SCHEMA or lookup.select(*FILING_KEYS).is_duplicated().any():
        raise ValueError('duplicate or incompatible filing lookup')
    joined = source.with_row_index('_filing_row').join(
        lookup.lazy(), on=list(FILING_KEYS), how='left', nulls_equal=True,
        validate='m:1', maintain_order='left',
    )
    if joined.select(pl.col('filing_industry_status').is_null().any()).collect().item():
        raise ValueError('missing filing lookup result')
    return joined.sort('_filing_row').drop('_filing_row').select(*names, *FILING_COLUMNS)
```

Rule validation runs once at lookup construction. Missing bridge coverage on any otherwise supported native code is detected globally before short-circuit statuses; Tasks 4/7 call `validate_relationships` first. Never fill nullable filing flags with false, and never overwrite `flag_below_filing_size` or any mapping flag.

- [x] **Step 4: Verify green.** Focused suite and milestone. Require explicit assertions on null dtypes, boundary years, the correlated unknown-vintage regression, untouched size flag and row multiplicity.
- [x] **Step 5: Commit/checkpoint.** `git add src/embedding_data/filing_rules.py tests/test_filing_rules.py` then `git commit -m 'feat(ita): evaluate filing industries only on candidate unanimity'`.

### Task 7: Verified source parity, staged bundle and CLI

> Deviation: final review reproduced an uncaught fastexcel workbook failure; `ccd138f` catches `FastExcelError` specifically and verifies clean exit 2 without publication through a real invalid-workbook CLI regression. Public interfaces and schemas remain unchanged.


**Files:** Create `src/embedding_data/code_build.py`, `src/embedding_data/codes_cli.py`, `tests/test_code_build.py`, `tests/test_codes_cli.py`; modify `src/embedding_data/cli.py`; extend `tests/code_fixtures.py` with actual-original fixture construction.

**Interfaces:** `check_source(data_dir: Path, work: Path) -> tuple[pl.LazyFrame, list[dict]]` verifies schema, selected raw inventory and full-row multiset parity without rewriting the source; `report(table: Path) -> dict` returns aggregate diagnostics; `build(data_dir: Path, run_id: str, *, registry=REGISTRY) -> Path` publishes the bundle. CLI commands use the public `codes_cli.app` and always pass explicit `data_dir`. No CLI registry override.

- [x] **Step 1: Write failing end-to-end tests with a real fixture tree.** Prepare the fixture originals once, using this dependency-free XLSX writer in `tests/code_fixtures.py`; commit the small XLSX files produced for Tasks 1/4. This writes reference fixtures only, never production inputs.

```python
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile

def write_xlsx(file: Path, rows: list[list[str | None]]) -> None:
    namespace = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    sheet_rows = []
    for i, row in enumerate(rows, 1):
        cells = ''.join(f'<c r="{chr(65 + j)}{i}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
                        for j, value in enumerate(row) if value is not None)
        sheet_rows.append(f'<row r="{i}">{cells}</row>')
    with ZipFile(file, 'w') as archive:
        archive.writestr('[Content_Types].xml', '''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>''')
        archive.writestr('_rels/.rels', '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>''')
        archive.writestr('xl/workbook.xml', f'''<workbook xmlns="{namespace}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Fixture" sheetId="1" r:id="rId1"/></sheets></workbook>''')
        archive.writestr('xl/_rels/workbook.xml.rels', '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>''')
        archive.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{namespace}"><sheetData>' +
                         ''.join(sheet_rows) + '</sheetData></worksheet>')
```

Define `seed_code_tree(data_dir) -> dict[str, Reference]` using the exact toy tables/pairs from Task 5, this writer, and the actual `import_reference` fixture registry. The helper must record every original, not mock `read_references`. Its source summary is built once through the real Stage 2 pipeline in the **temporary root**, using the following raw fixture writer:

```python
import csv
import io
from datetime import UTC, datetime
from dataclasses import replace
from embedding_data import code_references as cr, ita_summary, manifest, paths

def seed_code_tree(data_dir):
    originals = data_dir / 'originals'
    originals.mkdir(parents=True)
    registry = dict(cr.REGISTRY)
    for v in (2002, 2007, 2012, 2017, 2022):
        leaves = ('111111', '111112', '111113') if v == 2022 else ('111111', '111112')
        frame = titles(v, leaves)
        file = originals / f'naics_{v}.xlsx'
        write_xlsx(file, [[f'{v} NAICS Code', f'{v} NAICS Title'],
                          *[list(r) for r in frame.select('code', 'title').iter_rows()]])
        kind = f'naics_{v}'
        registry[kind] = replace(registry[kind], relative=f'naics/fixture_{v}.xlsx', family='naics',
                                 expected=(frame.height, len(leaves)))
        cr.import_reference(data_dir, kind, file, registry=registry)
    for a, b, pairs in [
        (2002, 2007, [('111111', '111111'), ('111112', '111112')]),
        (2007, 2012, [('111111', '111111'), ('111112', '111112')]),
        (2012, 2017, [('111111', '111111'), ('111111', '111112'), ('111112', '111112')]),
        (2017, 2022, [('111111', '111111'), ('111112', '111112'), ('111112', '111113')]),
    ]:
        kind = f'concordance_{a}_{b}'
        file = originals / f'{kind}.xlsx'
        write_xlsx(file, [list(r) for r in pair_sheet(a, b, pairs).iter_rows()])
        registry[kind] = replace(registry[kind], relative=f'naics/{kind}.xlsx')
        cr.import_reference(data_dir, kind, file, registry=registry)
    file = originals / 'soc.xlsx'
    write_xlsx(file, [list(r) for r in soc_sheet().iter_rows()])
    registry['soc_2018'] = replace(registry['soc_2018'], relative='soc/fixture.xlsx', expected=(4, 1))
    cr.import_reference(data_dir, 'soc_2018', file, registry=registry)
    for kind, part, code in [('designated_2012', 'E', '11'), ('designated_2017', 'E', '11'),
                             ('partially_exempt_2007', 'B', '111112')]:
        file = originals / f'{kind}.htm'
        file.write_text(f'<html><pre>Appendix A to Subpart {part} of Part 1904\n'
                        f'NAICS Industry\n{code}...... Fixture title\n</pre></html>')
        registry[kind] = replace(registry[kind], expected=1)
        cr.import_reference(data_dir, kind, file, registry=registry)
    for year in (2022, 2023):
        directory = paths.raw_dir(data_dir, 'osha') / 'summary' / str(year)
        directory.mkdir(parents=True)
        raw = directory / f'fixture_{year}.zip'
        row = {name: 'Fixture' for name in ita_summary.TEXT_COLUMNS}
        row.update(year_filing_for=str(year), id='1', establishment_id='1', establishment_type='1',
                   size='2', annual_average_employees='30', total_hours_worked='60000', naics_code='111112')
        if year >= 2023:
            row['naics_year'] = '2017'
        csv_text = io.StringIO()
        writer = csv.DictWriter(csv_text, fieldnames=list(row))
        writer.writeheader()
        writer.writerows([row, row])  # Deliberate identical rows, not an accidental fixture duplicate.
        with ZipFile(raw, 'w') as archive:
            archive.writestr('fixture.csv', csv_text.getvalue())
        entry = manifest.describe_file(raw, paths.manifest_path(data_dir).parent,
                                        retrieved_at=datetime(2026, 10, 13, tzinfo=UTC),
                                        client='fixture', client_version='1', source_url='https://www.osha.gov/fixture')
        manifest.append_entries(paths.manifest_path(data_dir), [entry])
    ita_summary.build_summary_table(data_dir)  # Fixture setup only; production code_build never calls this.
    return registry
```

Initial integration test:

```python
import json
import polars as pl
import pytest
from polars.testing import assert_frame_equal
from embedding_data import code_build, ita_summary, manifest, paths
from code_fixtures import seed_code_tree

def test_bundle_retains_duplicates_source_bytes_and_logical_determinism(tmp_path):
    registry = seed_code_tree(tmp_path)
    source = paths.derived_dir(tmp_path, 'osha') / ita_summary.TABLE_NAME
    original_hash = manifest.sha256_file(source)
    one = code_build.build(tmp_path, 'fixture_one', registry=registry)
    two = code_build.build(tmp_path, 'fixture_two', registry=registry)
    assert manifest.sha256_file(source) == original_hash
    output = pl.read_parquet(one / 'ita_300a_canonical.parquet')
    assert output.height == 4
    assert_frame_equal(output.select(ita_summary.COLUMNS), pl.read_parquet(source))
    for filename in one.glob('*.parquet'):
        assert_frame_equal(pl.read_parquet(filename), pl.read_parquet(two / filename.name))
    diagnostics = json.loads((one / 'report.json').read_text())
    assert diagnostics['input_rows'] == 4
    checksums = json.loads((one / 'outputs.json').read_text())
    assert checksums['ita_300a_canonical.parquet']['sha256'] == manifest.sha256_file(one / 'ita_300a_canonical.parquet')
    with pytest.raises(ValueError, match='exists'):
        code_build.build(tmp_path, 'fixture_one', registry=registry)
```

Add build failures for changed source value with valid code, dropped duplicate, invented duplicate, removed source column, extra source column, wrong dtype, stale raw release selection, incompatible vintage, malformed source code, corrupted/missing reference, and occupied staging run. None publishes the final run. Inject a `sink_parquet` failure at the filesystem boundary and assert earlier run/source bytes survive; test unfinished staging is refused rather than silently reused. CLI integration uses `CliRunner` on top-level `cli.app`, explicit tmp `--data-dir`, and a fixture registry dependency injection. Block HTTP transport while calling `codes build`; actual parsers and transforms run. All success/failure commands must avoid credential reads and produce clean error messages.

- [x] **Step 2: Verify red.** Run `uv run --locked pytest tests/test_code_build.py tests/test_codes_cli.py -q`; expected absent module/group.
- [x] **Step 3: Implement source parity and aggregate reporting.** Production source validation reads raw files into a temporary directory under staging, then compares **full original-column multisets**, including duplicate counts. The input Parquet itself is never regenerated.

```python
# src/embedding_data/code_build.py
import json
import re
import sys
import tempfile
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
import polars as pl
from embedding_data import code_references as cr, ita_summary, manifest, paths
from embedding_data.classification_tables import naics_tables, soc_tables
from embedding_data.ita_naics_mapping import KEY_SCHEMA, MAPPING_SCHEMA, build_lookup, enrich
from embedding_data.filing_rules import FILING_KEYS, FILING_COLUMNS, build_filing_lookup, add_filing_flags

SCHEMA_VERSION = 'codes-ita-v1'
SUMMARY_SCHEMA = {
    c: pl.String if c in [*ita_summary.TEXT_COLUMNS, 'naics_code', 'source_file'] else (
        pl.Boolean if c.startswith('flag_') or c == 'naics_year_from_dictionary' else pl.Int64
    ) for c in ita_summary.COLUMNS
}

def check_source(data_dir, work):
    table = paths.derived_dir(data_dir, 'osha') / ita_summary.TABLE_NAME
    lf = pl.scan_parquet(table)
    if lf.collect_schema() != SUMMARY_SCHEMA:
        raise ValueError('incompatible Stage 2 summary schema')
    selected = ita_summary.summary_files(data_dir)
    if sorted(selected) != list(range(min(selected), max(selected) + 1)):
        raise ValueError('incomplete source year inventory')
    citations = []
    observed = set(lf.select('year_filing_for', 'source_file').unique().collect().iter_rows())
    expected_inventory = set()
    for year, file in selected.items():
        entry = manifest.entry_for(paths.manifest_path(data_dir), file)
        citations.append(asdict(entry))
        expected_inventory.add((year, entry.path))
        raw = ita_summary.harmonize_file(file, year, entry.path, work / f'{year}.csv')
        expected = ita_summary.add_flags(raw).select(ita_summary.COLUMNS).group_by(
            ita_summary.COLUMNS
        ).agg(_n=pl.len().cast(pl.Int64))
        actual = lf.filter(pl.col('year_filing_for').eq(year)).group_by(
            ita_summary.COLUMNS
        ).agg(_n=pl.len().cast(pl.Int64))
        mismatches = actual.join(expected, on=ita_summary.COLUMNS, how='full',
                                 nulls_equal=True, coalesce=True, suffix='_raw').filter(
            pl.col('_n').ne_missing(pl.col('_n_raw'))
        ).select(pl.len()).collect().item()
        if mismatches:
            raise ValueError('stale Stage 2 summary: raw/full-row multiset mismatch')
    if observed != expected_inventory or not observed:
        raise ValueError('stale Stage 2 summary: selected source inventory differs')
    return lf, citations

def report(table):
    lf = pl.scan_parquet(table)
    total = lf.select(pl.len().cast(pl.Int64)).collect().item()
    def counts(columns):
        return lf.group_by(columns).agg(n=pl.len().cast(pl.Int64)).sort(
            columns, nulls_last=False
        ).collect().to_dicts()
    mapping = counts(['year_filing_for', 'naics_mapping_status'])
    filing = counts(['year_filing_for', 'filing_industry_status',
                     'flag_outside_filing_industry', 'flag_outside_filing_rule',
                     'flag_filing_rule_label_bridged', 'flag_filing_reference_ambiguous'])
    distribution = lf.with_columns(candidate_count=pl.col('naics_2022_candidates').list.len()).group_by(
        'year_filing_for', 'candidate_count'
    ).agg(n=pl.len().cast(pl.Int64)).sort('year_filing_for', 'candidate_count').collect().to_dicts()
    flags = lf.group_by('year_filing_for').agg(*[
        pl.col(c).sum().cast(pl.Int64).alias(c) for c in MAPPING_SCHEMA if c.startswith('flag_')
    ]).sort('year_filing_for').collect().to_dicts()
    if not total or sum(r['n'] for r in mapping) != total or sum(r['n'] for r in filing) != total:
        raise ValueError('report partitions do not account for every input row')
    return {'schema_version': SCHEMA_VERSION, 'input_rows': total, 'mapping': mapping,
            'filing': filing, 'candidate_counts': distribution, 'mapping_flags': flags,
            'filing_period_basis': 'nominal filing cycle: filing year plus one; actual submission dates unavailable'}

def write_json(file, payload):
    file.write_text(json.dumps(payload, sort_keys=True, indent=2) + '\n', encoding='utf-8')

def validate_canonical(table, expected_schema):
    lf = pl.scan_parquet(table)
    if lf.collect_schema() != expected_schema:
        raise ValueError('published canonical schema differs')
    nonnull = ['naics_mapping_status', 'naics_matching_vintages', 'naics_2022_candidates',
               'flag_naics_crosswalked', 'flag_naics_ambiguous', 'flag_naics_unresolved',
               'filing_industry_status', 'flag_filing_rule_label_bridged', 'flag_filing_reference_ambiguous']
    if lf.select(pl.any_horizontal([pl.col(c).is_null() for c in nonnull]).any()).collect().item():
        raise ValueError('null mapping contract field')
    states = ['missing_code', 'native_2022', 'concorded', 'invalid_native_code',
              'unknown_vintage_candidates', 'unknown_vintage_unmapped']
    length = pl.col('naics_2022_candidates').list.len()
    bad = pl.col('naics_mapping_status').is_in(states).not_().or_(
        pl.col('flag_naics_ambiguous').ne(length.gt(1))
    ).or_(pl.col('naics_year').is_null().and_(
        pl.any_horizontal(pl.col('naics_2022_code').is_not_null(), pl.col('naics_2022_node_id').is_not_null())
    )).or_(pl.col('naics_mapping_status').is_in([
        'missing_code', 'invalid_native_code', 'unknown_vintage_unmapped'
    ]).and_(length.ne(0)))
    if lf.filter(bad).select(pl.len()).collect().item():
        raise ValueError('invalid published mapping state or scalar assertion')
```

The library validates a root's selected release inventory and contiguous years, so tiny fixture roots exercise the same implementation. Task 8 additionally pins the actual production window to 2016–2025 and its measured counts. An empty inventory fails through `summary_files`; an interior missing year fails the contiguous-range check.

- [x] **Step 4: Implement staged publication and code/dependency provenance.** Append this orchestrator; keep raw full-row checks inside the lifetime of their temporary CSVs:

```python
def build(data_dir, run_id, *, registry=cr.REGISTRY):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', run_id):
        raise ValueError('run ID must contain only ASCII letters, digits, underscore or hyphen')
    root = paths.derived_dir(data_dir, 'codes')
    final, staging = root / run_id, root / (run_id + '.part')
    if final.exists() or staging.exists() or final.is_symlink() or staging.is_symlink():
        raise ValueError('run or staging name already exists')
    refs = cr.read_references(data_dir, registry=registry)
    source = paths.derived_dir(data_dir, 'osha') / ita_summary.TABLE_NAME
    source_hash = manifest.sha256_file(source)
    manifest_hash = manifest.sha256_file(paths.manifest_path(data_dir))
    root.mkdir(parents=True, exist_ok=True)
    staging.mkdir()
    with tempfile.TemporaryDirectory(dir=staging) as work:
        lf, raw_citations = check_source(data_dir, Path(work))
    native = refs['structures']
    naics_nodes, naics_edges, naics_paths = naics_tables(
        native.select('vintage', 'code', 'title'), 2022,
    )
    soc_original = cr.reference_path(data_dir, registry['soc_2018'])
    manifest.entry_for(paths.manifest_path(data_dir), soc_original)
    soc_nodes, soc_edges, soc_paths = soc_tables(pl.read_excel(
        soc_original, has_header=False, read_options={'dtypes': 'string'},
    ))
    lookup = build_lookup(lf.select(*KEY_SCHEMA).unique().collect(), native,
                          refs['relations'], naics_paths)
    filing_lookup = build_filing_lookup(lf.select(*FILING_KEYS).unique().collect(), native,
                                        refs['relations'], refs['rule_membership'])
    canonical = add_filing_flags(enrich(lf, lookup), filing_lookup)
    expected_schema = {**SUMMARY_SCHEMA, **MAPPING_SCHEMA, **FILING_COLUMNS}
    if canonical.collect_schema() != expected_schema:
        raise ValueError('incompatible canonical output schema')
    tables = {
        'naics_nodes': naics_nodes, 'naics_edges': naics_edges,
        'soc_nodes': soc_nodes, 'soc_edges': soc_edges,
        'naics_native_nodes': native, 'naics_concordance': refs['relations'],
        'filing_rules': refs['rules'], 'code_paths': pl.concat([naics_paths, soc_paths]).sort('node_id'),
        'filing_rule_labels': refs['rule_labels'], 'filing_rule_membership': refs['rule_membership'],
        'ita_naics_lookup': lookup,
    }
    for name, frame in tables.items():
        frame.write_parquet(staging / (name + '.parquet'))
    canonical.sink_parquet(staging / 'ita_300a_canonical.parquet')
    validate_canonical(staging / 'ita_300a_canonical.parquet', expected_schema)
    diagnostics = report(staging / 'ita_300a_canonical.parquet')
    if diagnostics['input_rows'] != lf.select(pl.len()).collect().item():
        raise ValueError('canonical row count changed')
    diagnostics['tables'] = {}
    for file in sorted(staging.glob('*.parquet')):
        frame = pl.scan_parquet(file)
        diagnostics['tables'][file.name] = {
            'rows': frame.select(pl.len()).collect().item(),
            'schema': {name: str(dtype) for name, dtype in frame.collect_schema().items()},
        }
    reference_counts = refs['rule_membership'].group_by('rule_id').agg(
        rule_native_codes=pl.len().cast(pl.Int64),
        definite_members=pl.col('membership_candidates').list.len().eq(1).and_(
            pl.col('membership_candidates').list.contains(True)
        ).sum().cast(pl.Int64),
        mixed_memberships=pl.col('membership_candidates').list.len().eq(2).sum().cast(pl.Int64),
        label_bridge_codes=pl.col('flag_rule_label_bridged').sum().cast(pl.Int64),
    )
    label_counts = refs['rule_labels'].group_by('rule_id').agg(
        listed_groups=pl.len().cast(pl.Int64),
        legacy_labels=pl.col('flag_rule_label_legacy').sum().cast(pl.Int64),
    )
    diagnostics['rule_counts'] = label_counts.join(reference_counts, on='rule_id', validate='1:1').sort(
        'rule_id'
    ).to_dicts()
    citations = raw_citations + [asdict(manifest.entry_for(paths.manifest_path(data_dir),
                    cr.reference_path(data_dir, reference))) for reference in registry.values()]
    code_files = sorted({Path(__file__), *[Path(module.__file__) for module in [
        cr, ita_summary, manifest, paths,
        __import__('embedding_data.classification_tables', fromlist=['forest']),
        __import__('embedding_data.naics_relationships', fromlist=['candidates']),
        __import__('embedding_data.filing_rules', fromlist=['evaluate']),
        __import__('embedding_data.ita_naics_mapping', fromlist=['enrich']),
        __import__('embedding_data.ita_references', fromlist=['parse_titles']),
        __import__('embedding_data.ita_catalog', fromlist=['through_date']),
        __import__('embedding_data.osha_encoding', fromlist=['decode_line']),
    ]]})
    inventory = {
        'schema_version': SCHEMA_VERSION, 'run_id': run_id,
        'source_parquet': {'path': source.relative_to(data_dir).as_posix(),
                           'sha256': source_hash, 'size': source.stat().st_size},
        'raw': sorted(citations, key=lambda r: r['path']),
        'references': {kind: asdict(reference) for kind, reference in sorted(registry.items())},
        'implementation': {file.relative_to(paths.PROJECT_ROOT).as_posix(): manifest.sha256_file(file)
                           for file in code_files},
        'dependencies': {name: version(name) for name in ['embedding-data', 'polars', 'fastexcel', 'httpx', 'typer']},
        'python': sys.version, 'uv_lock_sha256': manifest.sha256_file(paths.PROJECT_ROOT / 'uv.lock'),
    }
    write_json(staging / 'inputs.json', inventory)
    write_json(staging / 'report.json', diagnostics)
    # Detached checksum inventory avoids a self-referential hash in report.json/inputs.json.
    write_json(staging / 'outputs.json', {file.name: {'sha256': manifest.sha256_file(file),
                                                     'size': file.stat().st_size}
                                          for file in sorted(staging.iterdir()) if file.is_file()})
    if manifest.sha256_file(source) != source_hash or manifest.sha256_file(paths.manifest_path(data_dir)) != manifest_hash:
        raise ValueError('source table or raw manifest changed during build')
    for citation in citations:
        manifest.entry_for(paths.manifest_path(data_dir), paths.manifest_path(data_dir).parent / citation['path'])
    if final.exists() or final.is_symlink():
        raise ValueError('run destination appeared during build')
    staging.rename(final)
    return final
```

An unsuccessful staging directory remains incomplete and its name is refused on a rerun; use a new run ID after investigating. All temporary raw CSVs are removed on context exit. `outputs.json` checksums every produced Parquet and both JSON records; it excludes itself by construction. This extra checksum inventory makes the design's output-hash requirement concrete; describe it in the actual Handoff. The report records original/expanded rule counts and each table's actual schema/row count; the staged canonical file passes explicit mapping state/list/flag/null checks before publication.

- [x] **Step 5: Implement and register the CLI group.**

```python
# src/embedding_data/codes_cli.py
from pathlib import Path
import httpx
import polars as pl
import typer
from embedding_data import code_build, code_references, paths

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)

@app.callback()
def codes():
    '''Acquire official code references and build immutable canonical ITA bundles.'''

def invoke(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except (OSError, ValueError, KeyError, httpx.HTTPError, pl.exceptions.PolarsError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(2) from None

@app.command('acquire')
def acquire(data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')):
    for file in invoke(code_references.acquire, data_dir, registry=code_references.REGISTRY):
        typer.echo(file)

@app.command('import-reference')
def import_reference(kind: str, file: Path,
                     data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')):
    typer.echo(invoke(code_references.import_reference, data_dir, kind, file,
                      registry=code_references.REGISTRY))

@app.command('build')
def build(run_id: str, data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')):
    typer.echo(invoke(code_build.build, data_dir, run_id, registry=code_references.REGISTRY))
```

In `cli.py`, add `codes_cli` to the existing import tuple and `app.add_typer(codes_cli.app, name='codes')` after the existing registrations. Existing extract commands stay direct registered commands; only the new multi-command group is mounted.

- [x] **Step 6: Verify green and publication invariants.** Run the focused suites and milestone. Assert all bundle filenames, exact schemas, every output checksum, full source order/multiplicity and frozen earlier run bytes. Check `codes --help`, all three command helps and clean failure exits. The offline fixture build must work with blank credentials and prohibited HTTP. Run twice with different run IDs and compare logical Parquet frames, not JSON run IDs or physical writer bytes.
- [x] **Step 7: Commit/checkpoint.** `git add src/embedding_data/code_build.py src/embedding_data/codes_cli.py src/embedding_data/cli.py tests/test_code_build.py tests/test_codes_cli.py tests/code_fixtures.py` then `git commit -m 'feat(codes): publish verified canonical ITA bundles offline'`.

### Task 8: Full-data V11 evidence, final review and Stage 4 completion

> Deviation: after the reviewed CLI correction, acceptance was repeated under fresh run `stage4_v11_20261013_r2` at `ccd138f`. The first run’s fifteen files remain byte-identical; reports and all canonical columns match logically across 33 slices despite different physical Parquet bytes. The measured finding and documentation were refreshed at `78f9300`.


**Files:** Create `specs/findings/v11-ita-naics-mapping.md`; modify `README.md`, `CLAUDE.md`, this plan, `specs/deferred_items.md`, and the roadmap's Stage 4 checkbox/stamp at completion. Retire this stage spec and plan only after the completion gate. The source spec and roadmap remain live.

**Interfaces:** Actual produced `inputs.json`, `report.json`, `outputs.json` and typed Parquet tables; no fixture/preflight substitute for measured V11. Aggregate committed evidence contains no establishment names, addresses, EINs or IPUMS microdata.

- [x] **Step 1: Prepare actual originals without altering Stage 2/3.** Read the actual raw manifest, verify the three existing title originals and the full-data source hash. Import verified cached public 2012→2017, 2017→2022 and SOC originals if downloads are blocked; use their recorded source SHA-256 values from Entry evidence and the skill cache manifest, never its CSVs. Acquire/import the 2007 workbook/bridge and the three complete GovInfo originals through the registered commands. If a server returns an access challenge, obtain the original from its public download/browser and use `codes import-reference KIND FILE`; do not archive the challenge as a valid original. Retain all recorded bytes/entries.

These are authorized public reference acquisitions necessary for Stage 4. No private data is transmitted. If a transport constraint or an unavailable original requires owner input, complete independent work first and surface the precise missing original and source. Do not mark the stage complete with missing references.

```bash
uv run --locked embedding-data codes acquire --data-dir /Users/lowell/Projects/embedding-data/data
uv run --locked embedding-data audit --data-dir /Users/lowell/Projects/embedding-data/data
```

Before an optional cache import, compute its SHA-256 and compare with the exact value above. Example for the known SOC original, with the skill path used only as an execution-time **original import source**, not in package code:

```bash
uv run --locked embedding-data codes import-reference soc_2018 /Users/lowell/.agents/skills/classification-codes/sources/soc_structure_2018.xlsx --data-dir /Users/lowell/Projects/embedding-data/data
```

- [x] **Step 2: Run actual offline acceptance under a fresh run ID.** Use `stage4_v11_20261013` when execution is on 2026-10-13; otherwise record the actual date and choose an unused matching ID. An occupied run/staging name is refused, not cleaned up or replaced automatically. Snapshot the source table and every Stage 3 verification file hash before this build and compare afterward; the snapshot can live outside the raw tree.

```bash
uv run --locked embedding-data codes build stage4_v11_20261013 --data-dir /Users/lowell/Projects/embedding-data/data
uv run --locked embedding-data audit --data-dir /Users/lowell/Projects/embedding-data/data
```

Acceptance assertions (run from the execution checkout; pass the recorded actual run ID if it differs):

```python
import json
from pathlib import Path
import polars as pl
from embedding_data import classification_tables as ct, ita_summary, manifest
from embedding_data.ita_naics_mapping import MAPPING_SCHEMA
from embedding_data.filing_rules import FILING_COLUMNS

root = Path('/Users/lowell/Projects/embedding-data/data')
run = root / 'derived/codes/stage4_v11_20261013'
inputs = json.loads((run / 'inputs.json').read_text())
diagnostics = json.loads((run / 'report.json').read_text())
assert diagnostics['input_rows'] == 3_206_055
assert sum(r['n'] for r in diagnostics['mapping']) == 3_206_055
assert sum(r['n'] for r in diagnostics['filing']) == 3_206_055
nodes = pl.read_parquet(run / 'naics_nodes.parquet')
soc = pl.read_parquet(run / 'soc_nodes.parquet')
assert nodes.height == 2125 and nodes.filter(pl.col('level').eq('national_industry')).height == 1012
assert soc.height == 1447 and soc.filter(pl.col('level').eq('detailed')).height == 867
assert nodes.filter(pl.col('level').eq('sector')).height == 20
assert soc.filter(pl.col('level').eq('major')).height == 23
assert nodes.filter(pl.col('code').is_in(['31-33', '44-45', '48-49'])).height == 3
labels = pl.read_parquet(run / 'filing_rule_labels.parquet')
membership = pl.read_parquet(run / 'filing_rule_membership.parquet')
assert labels.height == 213 and labels['flag_rule_label_legacy'].sum() == 2
assert membership.height == 3297
mixed = membership.filter(pl.col('membership_candidates').list.len().eq(2))
assert mixed.select('rule_id', 'code').rows() == [('partially_exempt_2007', '517110')]
assert mixed['membership_candidates'][0].to_list() == [False, True]
ct.forest(nodes, pl.read_parquet(run / 'naics_edges.parquet'))
ct.forest(soc, pl.read_parquet(run / 'soc_edges.parquet'))
source = root / 'derived/osha' / ita_summary.TABLE_NAME
assert manifest.sha256_file(source) == inputs['source_parquet']['sha256']
out = pl.scan_parquet(run / 'ita_300a_canonical.parquet')
assert out.select('year_filing_for').unique().sort('year_filing_for').collect()['year_filing_for'].to_list() == list(range(2016, 2026))
assert out.collect_schema() == {**pl.scan_parquet(source).collect_schema(), **MAPPING_SCHEMA, **FILING_COLUMNS}
assert out.select(pl.col('naics_code').is_null().sum()).collect().item() == 0
expected_states = {'invalid_native_code': 66_365, 'unknown_vintage_candidates': 373,
                   'unknown_vintage_unmapped': 2_297, 'missing_code': 0}
counts = out.group_by('naics_mapping_status').len().collect()
actual_states = dict(counts.iter_rows())
for status, expected in expected_states.items():
    assert actual_states.get(status, 0) == expected, (status, actual_states.get(status, 0))
assert out.select(pl.col('flag_naics_unresolved').sum()).collect().item() == 69_035
assert out.filter(pl.col('naics_year').is_null()).select(
    pl.col('naics_2022_code').is_not_null().sum()
).collect().item() == 0
for name, record in json.loads((run / 'outputs.json').read_text()).items():
    assert manifest.sha256_file(run / name) == record['sha256']
    assert (run / name).stat().st_size == record['size']
print('Stage 4 full-data graph, schema, state, row accounting and checksum checks passed')
```

The state counts are expectations from the pinned preflight, not values to force into output. On any discrepancy, reproduce and diagnose whether the references, selected releases, source transformation or implementation changed. New input releases require a newly recorded inventory and evidence rather than silently reusing these counts. Also verify row-by-row source order: scan source and canonical original columns in fixed 100,000-row slices and use `polars.testing.assert_frame_equal` for each slice, including the final short slice. This guards order as well as the build's multiset parity without loading both entire tables into memory.

- [x] **Step 3: Commit a measured V11 finding and user documentation.** The finding must state the actual run/schema version, execution commit, code/dependency/lock hashes, all cited raw/reference hashes and counts, source/output hashes, graph/coverage refusals, per-year mapping states, candidate-count distributions, crosswalk/ambiguity/unresolved diagnostics and filing outcomes including nulls. Explain known mismatch vs unknown support, the adopted ITA source exception, singleton flags and no imputation/allocation. State the nominal filing-cycle limitation for late submissions and that the flags diagnose filing universe rather than whether an observed submission was improper. Cite the original Census/BLS/GovInfo references and the stage/source spec.

Include exact columns/dtypes, all bundle filenames, and what `outputs.json` covers. Record the unchanged source/Stage 3 hashes and zero-discrepancy raw audit. README documents the three commands, contact/import fallback and immutable run IDs; CLAUDE.md updates planned-vs-built status and offline build guidance. Geography, targets, output target writer, ACS/CPS parsers and headline-inclusion rules remain their existing later-stage responsibilities. Preserve the source spec's Core principle and the stricter later-source V11 scope.

```bash
git add specs/findings/v11-ita-naics-mapping.md README.md CLAUDE.md
git commit -m 'docs(ita): record full-data canonical mapping and filing evidence'
```

- [x] **Step 4: Review the whole branch before completion markup.** Use requesting-code-review and its current controller-specific recipe, with the plan and stage/source specs and `git merge-base main HEAD` as the base. Review uncommitted changes as well. Resolve every merged finding through receiving-code-review, rerun the affected checks/full-data measurement under a new run ID when code or dependencies change, and commit fixes. A missing official bridge, silently changed source, unmatched lookup, ambiguous selected vintage or unjustified determinate flag blocks Stage 4 completion.

- [x] **Step 5: Run the completion gate and close the carried industry item.** Use writing-plans' Plan Completion Protocol: resolve-before-defer, mark actual completed steps/deviations, then tick `specs/deferred_items.md` section `2-ita-300a-summaries`, item "Industry half of the R2.9 filing-rule flag" with `→ done in plan 4`. Its Done-when is evaluation with concordance candidate sets, verified by Tasks 6–8. Record the approved separate-output placement instead of claiming `ita_summary.add_flags` changed. Append only genuine remaining deferred items, with size and a concrete closure/revisit condition; no empty backlog section.

- [x] **Step 6: Record what actually shipped and tick/stamp only Stage 4.** Add `## Handoff to later stages` to this plan based on the implementation ledger, deviations and actual finding. Re-validate **every** unticked stage, recording the result; use the consumer checklist below. Changed paths/schema/interface names, parser refusals, checksum boundaries, nullable flags, unknown-vintage candidate limits, and any introduced-then-reverted interface each get a factual bullet. Do not present this plan's proposed contracts as shipped.

| Unticked stage | Completion-time check against actual output |
| --- | --- |
| 5 | Shared node-ID/typed edge convention, child→parent direction, root behavior; classification-only single-parent validator must not constrain CBSA geography. Exact schema/version/path contract. |
| 6 | Actual canonical bundle/run selection, verified raw/source/output citations, native values and flags, empty/multiple candidates, unknown singleton restrictions, filing null semantics and separate legacy/reference-ambiguity flags; county assignment/target writer remain Stage 6. |
| 7 | Check whether reference/manifest changes affect the audit contracts or IPUMS assumptions. Unless execution changes them, record no dependency or scope change; this plan verifies no IPUMS extract. |
| 8 | Actual canonical nodes/paths, sorted finest candidate convention, direct full concordances and native structures. ITA unresolved exceptions do not relax ACS parsing requirements. |
| 9 | Confirm Stage 8 remains its code/allocation dependency; identify any shared uncertainty flag contract relevant to later transformations without adding work here. |
| 10 | Actual canonical mapping/path retrieval; unresolved rows assert neither a scalar canonical code nor a full observed path; candidate unions are uncertain and singleton crosswalks remain flagged. Rule-reference uncertainty persists independently of the final filing result. R2.6/R2.7 consumers from Stage 3 remain valid. |
| 11 | Actual NAICS/SOC schemas/path conventions and reusable relationship/candidate contracts; CPS Census-list/transition parsing remains this stage's work after Stage 7 verification. |
| 12 | Confirm Stage 11 remains its occupation-mapping dependency; shared candidate uncertainty does not clear CPS dependent-coding/allocation flags. |
| 13 | Actual reference/transformation version and provenance boundaries for later output manifests; no sample-size gate, target or evaluation decision shipped here. |

Completion's re-validation creates the factual Handoff. Amend later roadmap entries only at a subsequent **derive-roadmap resume**, using these actual bullets; any stage addition/split/drop/reorder is an owner scope decision under that skill. The current session ticks/stamps Stage 4 and stops at its integration handoff. This distinction implements the roadmap line without prematurely asserting later-stage contracts.

Under Stage 4 in `specs/embedding-evaluation-data-spec-roadmap.md`, change `[ ]` to `[x]` and insert, using the actual completion date and actual consumer-stage list:

```markdown
> Stage 4: COMPLETE (YYYY-MM-DD) — implemented by plan 4 (specs/plans/completed/4-code-tables-ita-naics-mapping.md). Its Handoff section names what Stages 5, 6, 8, 10 and 11 consume.
> Next: resume the roadmap.
```

The date token above is the protocol's stamp template; fill it from the actual completion date, never the planning date by default. Cite later stages' spec refs rather than restating their requirements. Do not tick Stage 4 unless the actual V11 finding, graph/reference checks, row accounting, industry-item closure and final review all hold.

- [x] **Step 7: Backlog health, retirement and deliberate integration.** Run `uv run --no-project --python 3.13 python /Users/lowell/.agents/skills/writing-plans/scripts/deferred_stats.py` from the repo root and report its summary (open count, closure rate, aged tail). If its size/age trigger fires, present the skill's read-only triage proposal; disposition remains the owner's choice and does not block completion.

Retire this plan to `specs/plans/completed/4-code-tables-ita-naics-mapping.md`. Retire the stage spec to `specs/completed/code-tables-ita-naics-mapping.md`, marked complete, **only after** checking no other live plan implements it. Fix relative links for their new depth, including links in the preflight and roadmap Stage 4 design reference that point to the retiring stage spec. The umbrella source spec/roadmap stay live. Commit completion/retirement specs atomically according to writing-plans (`chore(specs): retire plan 4` for retirement).

Run the milestone once more after code/review changes, verify specs link targets and `git diff --check`, then use finishing-a-development-branch for merge/PR/keep/discard and worktree cleanup. End with the integration-outcome roadmap resume instruction; do not plan or execute a later stage in this session.

## Planning self-review and execution acceptance

| Stage requirement | Implementing task/evidence |
| --- | --- |
| R5.1 (ITA): native plus canonical; exact canonical vintages | 1, 5, 7; exact dtypes/native column parity |
| R5.2: five/four levels, official graphs/ranged sectors, full paths | 1, 4, 7, 8; exact node counts/closure and SOC overflow fixture |
| R5.4: complete 2012/2017 relationships, no chosen split side | 2, 5; complete endpoint coverage and handwritten two-hop/degree tests |
| R2.5: retained native values, explicit supported/unknown/mismatch/unresolved states | 5, 7, 8; six-state partition and pinned full-data accounting |
| R2.9 industry half: vintage-correct lists, peak size, null uncertainty | 0, 3, 6, 8; D2-adopted legacy-label amendment, full predecessor coverage and explicit membership sets; period boundary/correlated-interpretation tests and carried-item closure remain required |
| V11 (ITA): every row accounted for with official support or explicit unresolved state | 7, 8; measured finding, 3,206,055 source-preserved rows and checksum inventory |
| R9.2 and original immutability | 4, 7; genuine fixture-byte CLI, forbidden HTTP, verified citations and source hash equality |
| Roadmap completion/handoff | 8 Steps 5–7; actual-shipped Handoff, Stage 4 stamp, retirement and later resume |

Before handing this plan to execution, scan for absent interfaces, contradictory types, unspecified references and placeholder implementation steps; compile Python fences as a syntax check and review the stage spec section-by-section against this table. Baseline success does not verify future code. Execution must independently establish every red/green and full-data gate above.

Planning verification: the original strict expansion failed on the two documented labels, motivating D1's bounded research. The proposed prototypes now preserve all 213 original labels, exactly two interpreted as legacy, and full five-vintage graph/bridge coverage. Their complete rule-membership relation has 3,297 rows and one mixed 2007 leaf (`517110`); real-reference examples verify null class-3 and unanimous class-2 results with ambiguity flags retained. Two genuine-fixture offline bundles remain logically identical and preserve source rows/duplicates. Python fences, amendment old-block matches and local links are checked before review. The owner approved Task 0 and the revised plan through D2; all eight approved spec replacements are applied and their exact match, local links and Python fences are verified. No production code or raw manifest/data shipped or changed at this documentation checkpoint.


## Execution handoff

> Historical approved starting handoff, retained as the audit trail. Execution is complete; use the actual-shipped Handoff below for roadmap reconciliation.


Task 0's eight approved spec replacements and D2 adoption record are applied
and committed; its replace/with blocks remain an audit trail and must not be
reapplied. Start implementation at **Task 1**, in an isolated worktree after
the baseline checks. Tasks 1–8, the full-data V11 finding, carried industry-item
closure, final review and Stage 4 completion/handoff remain outstanding.

Following the owner's planning-to-execution workflow, use a fresh session
against this saved plan. Recommended execution: subagent-driven-development
(the plan header's default), with a fresh implementer and task-scoped review
for each task's explicit files/interfaces. Use executing-plans if the owner
chooses inline execution. The approved plan is the complete handoff; no
additional planning-session context or reapproval of D2 is needed.


## Execution completion evidence

Approved checkpoint `ffaa576` was verified before execution; Task 0’s replacements were not reapplied. Isolation prerequisite `453b0fa` added `.worktrees/` to the ignore rules. Reviewed task checkpoints were `f27e8ac`, `14befd6`, `49b131c`, `412a0d4`, `ec74d70`, `6508d43`, and `fdfeaa1`; the owner-directed Task 2 refinement is `b720046`. Each task has RED/GREEN, milestone and spec/quality review evidence in the execution ledger. Runtime model aliases were adapted to the available standard/capable models; no workflow gate was skipped.

The whole-branch review found one Important CLI exception issue. Its reproduced regression and fix are `ccd138f`; scoped final re-review approved the code with no remaining findings. Refreshed V11/documentation review approved `78f9300`, with no new findings. The Codex CLI second opinion was skipped under requesting-code-review’s controller-is-Codex rule, not represented as a completed second review. No review finding, skipped step or new item is deferred.

The actual [V11 finding](../../findings/v11-ita-naics-mapping.md) records selected run `stage4_v11_20261013_r2`, schema `codes-ita-v1`, execution commit `ccd138fcf8606085cf3d13821bf01f86ab35f7f2`, all 23 raw citations, implementation/CLI/dependency/lock hashes, exact schemas and every output hash. Acceptance retains 3,206,055 rows across 2016–2025, including 69,035 unresolved rows. It verifies complete graphs/relationships, all 213 original labels, 3,297 rule-native membership rows and sole mixed leaf 2007 `517110`.

Source `ita_300a_summary.parquet` SHA-256 remains `6335cda7adb40a41c4a11d57d22048999449ac8d078a2ec0291f0198cd9136a8`. All 24 Stage 3 files and all fifteen files of the first Stage 4 run are unchanged. Full raw/source multiset parity, 33 bounded source-order slices, input/output hashes, zero-discrepancy raw audits and zero-HTTP cached acquisition passed. The controller independently reran full acceptance for both measurements. Fresh milestone after the code fix: 476 pytest passed, one network canary deselected; two Behave scenarios/ten steps, ruff and locked dependencies passed.

The carried industry filing-rule item is closed by the separate canonical output, not by changing `ita_summary.add_flags`. The source summary and all Stage 3 modules/artifacts remain intact. The completion gate had no unresolved owner questions or leftover findings. No other live plan implements this stage spec. Plan/spec retirement, local-link validation and the Stage 4 stamp belong to the atomic retirement commit. Integration is a draft PR; the owned worktree is removed after the branch is durable, following the owner’s cleanup instruction.

## Handoff to later stages

Revalidated **every remaining stage (5–13)** on 2026-10-13 against the actual selected bundle and measured [V11 finding](../../findings/v11-ita-naics-mapping.md), under the [source spec](../../embedding-evaluation-data-spec.md). The actual root is `/Users/lowell/Projects/embedding-data/data`; selected bundle is `derived/codes/stage4_v11_20261013_r2/`. Existing or `.part` run IDs are refused. The first `stage4_v11_20261013/` run is retained, not replaced. No later stage was planned or executed here. Later roadmap-entry amendments belong to the subsequent derive-roadmap resume; this Handoff is completion evidence only.

The bundle contains twelve Parquets: `naics_nodes`, `naics_edges`, `soc_nodes`, `soc_edges`, `naics_native_nodes`, `naics_concordance`, `code_paths`, `filing_rules`, `filing_rule_labels`, `filing_rule_membership`, `ita_naics_lookup`, and `ita_300a_canonical`. It also contains `inputs.json`, `report.json` and `outputs.json`. The detached inventory hashes/sizes all twelve Parquets and the first two JSON records, excluding itself. The finding records its own hash, execution commit and the extra CLI hashes outside the build’s transformation-module inventory. There is no run-selection alias or automatic latest-run resolver. Consumers must select an explicit verified bundle.

- **Stage 5 — compatible, consumes shared graph convention.** Under R5.2/R6, shipped node schema is `node_id:String, system:String, vintage:Int64, level:String, code:String, title:String`; identifiers are `system:vintage:level:code`. Edge schema is `child_id:String, parent_id:String, edge_type:String`, direction child to parent. Classification edges use `hierarchy`; roots have no parent and no invented common root. `code_paths.parquet` is `node_id:String, path:List(String)`, root through node. `classification_tables.forest` enforces classification single parentage only: geography must reuse the typed schema without applying that restriction to cross-state CBSA relationships. Native/auxiliary NAICS tables are complete for 2002/2007/2012/2017/2022; canonical is 2022, SOC 2018. Stage 3’s county/reference decisions remain valid; full production geography remains Stage 5.

- **Stage 6 — compatible dependency, needs factual consumer amendment at resume.** Under R2.5/R2.9/R7, consume the selected separate canonical table and its inventories rather than assuming the Stage 2 summary was enriched. Canonical schema is every Stage 2 column in original order plus the exact nine mapping and five filing columns documented in V11. Native values, order, duplicates and original flags are retained. `naics_matching_vintages:List(Int64)` and `naics_2022_candidates:List(String)` are nonnull; candidates are sorted distinct finest codes. Empty lists assert no mapping. Unknown vintages stay null/unresolved even for singleton unions and never fill `naics_2022_code` or `naics_2022_node_id`; known mismatches remain empty/unresolved. Singleton historical crosswalks remain flagged. Filing industry/combined flags are nullable; size class 1 has null industry result and true combined outside result, preserving the original size flag. `flag_filing_rule_label_bridged` and `flag_filing_reference_ambiguous` are nonnullable provenance independent of final unanimity, and false when no membership is evaluated. County assignment, target writer and headline inclusion remain this stage’s responsibilities. All raw/source/output citations are verified; nominal filing year plus one cannot resolve late submission dates.

- **Stage 7 — compatible, no dependency or scope change.** R1/R3/R4 verification and `manifest_audit.audit`/`manifest.entry_for` contracts remain unchanged. Ten new registered public originals are appended with local import-time retrieval proxies; all thirteen required originals replay offline with zero HTTP calls, and whole-tree raw audits have zero discrepancies. This checks provenance existence/bytes, not IPUMS extract contents, weight storage, delivery semantics or V4–V7. No IPUMS extract was verified or transformed here.

- **Stage 8 — compatible dependency, needs factual consumer amendment at resume.** Under R5.1/R5.3/R5.4/R6.3, consume canonical node/path tables, complete direct four-bridge `naics_concordance.parquet`, native/auxiliary structure nodes and the sorted finest-candidate convention. Relationship schema is `source_vintage:Int64, target_vintage:Int64, source_code:String, target_code:String, link_type:String, source_file:String`; complete endpoint coverage and degree-derived 1:1/1:m/m:1/m:m are validated. `naics_relationships.candidates` traverses every adjacent path forward/reverse; equality never shortcuts a vintage relationship. No weights or preferred sides are supplied. ITA’s six-ASCII-digit parser and explicitly unresolved source exception do not relax ACS mixed-depth parsing or its zero-unparseable V11 exit. ACS parsers and allocations remain Stage 8.

- **Stage 9 — compatible, no dependency or scope change.** Stage 8 remains its parser/allocation dependency under R3/R7. Candidate ambiguity, unknown vintage and singleton crosswalk provenance must not be cleared merely because a candidate list has one element. This stage shipped no ACS transformation, allocation factor, target or headline-inclusion decision; the source Core principle remains binding.

- **Stage 10 — compatible dependency, needs factual consumer amendment at resume.** Under R2.6/R2.7/R7.2, canonical path retrieval is by `code_paths.node_id` for every supported candidate. Unresolved rows assert neither a scalar canonical code nor a full observed path; unknown candidate unions and deepest common ancestors are conditional possibilities, not corrected observations. Singleton historical mappings remain crosswalked. The two rule-reference provenance flags persist independently of final filing result. Stage 3’s normalization, employer fallback, reconstructed-EIN, unique-ID and ambiguity contracts remain valid; its source table/artifacts were preserved. Inclusion of unresolved text–code rows needs the later target design, not a fabricated path here.

- **Stage 11 — compatible dependency, needs factual consumer amendment at resume.** Under R4/R5/R7, consume actual canonical NAICS/SOC schemas, full root-to-leaf path convention and reusable complete relationship/candidate APIs. SOC parents follow original workbook nesting, including overflow broad groups; numeric prefix surgery is refused. All 1,447 SOC nodes/867 detailed codes and 2,125 NAICS nodes/1,012 finest codes are present. CPS Census-list parsing, V6 transition interpretation and panel/flow construction remain this stage’s work after Stage 7 verification. Auxiliary 2002/2007 rule references are not new admitted ITA native vintages or CPS source schemes.

- **Stage 12 — compatible, no dependency or scope change.** Stage 11 remains the occupation/industry mapping dependency under R4/R7, alongside Stage 9 helpers. Candidate unanimity never clears CPS dependent-coding, allocation or other source-imputation flags. No CPS cross-section, profile or migration target shipped here.

- **Stage 13 — compatible, no dependency or scope change.** Under R7/R8 and V9/V12, later output manifests can cite `codes-ita-v1` bundle inputs/outputs, verified original/source hashes, reference definitions, implementation/dependency/lock versions and the measured finding’s extra CLI/commit provenance. Output checksums are detached and logical determinism differs from physical Parquet-byte identity between fresh runs. The source summary’s physical hash is intentionally pinned. No target, sample-size gate, comparator, embedder training data or evaluation decision shipped in Stage 4.

No public interface was introduced then removed or renamed. Private reference validation and degree-expression helpers strengthen existing contracts. Parser refusals include malformed/ambiguous originals, missing titles/parents, duplicates, incompatible source schema/vintage, malformed nonmissing ITA syntax, incomplete bridge/member coverage, changed/unrecorded/missing originals, unmatched lookup keys and occupied/incomplete run names. None becomes an invented unresolved reference result. All current stage exits remain in force; factual downstream Consumes/path/uncertainty amendments are the next derive-roadmap reconciliation, and any split/add/drop/reorder remains an owner scope decision.
