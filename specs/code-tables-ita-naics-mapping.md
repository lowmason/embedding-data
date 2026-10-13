# Code tables and ITA NAICS mapping

## Scope and decisions

Stage 4 of [the roadmap](embedding-evaluation-data-spec-roadmap.md) implements
R5.1 (ITA), R5.2, R5.4 (ITA vintages), R2.5, R2.9's industry flag, and V11
(ITA) in [the source spec](embedding-evaluation-data-spec.md). It produces the
canonical classification graphs, reusable NAICS mapping references, and an
enriched establishment-year table. Geography, ACS/CPS parsers, target builders,
and the shared target writer remain in their existing later stages.

The owner approved this design on 2026-10-13:

- Use shared typed node/edge tables and a reusable mapping lookup.
- Join mappings into a separate ITA output without expanding or dropping rows.
- For unknown vintages, preserve reference-supported candidate unions without
  selecting a vintage. Known-vintage mismatches remain unresolved.
- Retain all source codes, vintages, and rows; flag unresolved source defects.
- Assert a filing-rule result only when all supported possibilities agree.

The [preflight finding](findings/stage-4-ita-code-preflight.md) verified all ten
raw releases and raw/derived aggregate parity. It found 66,365 rows absent from
their recorded vintage and 2,670 rows with unknown vintage. Of these disjoint
groups, 9,173 and 2,297 rows respectively have codes absent from all three
supported structures. The owner-approved amendment to R2.5 and the roadmap exit
replaces zero-unmapped with complete accounting and explicit unresolved states.
This is an ITA exception; R5.3/V11's requirements for ACS and CPS remain intact.

## Architecture and inputs

Keep the acquisition boundary separate from offline parsing and transformation.
Repository-owned modules cover reference acquisition/import, classification
graphs, NAICS relationships, filing-rule evaluation, and build orchestration.
Reuse the existing manifest/download contracts and validated classification
patterns; do not introduce a runtime dependency on personal skills directories.

The implementation plan may divide these responsibilities into modules, but
must preserve these boundaries and the public table contracts below. No new
dependency is needed: use the existing Polars, fastexcel, httpx, and Typer stack.
Workbook inputs are small eager frames; establishment transformations are lazy
Polars with method-style expressions, as R9 requires.

Consume Stage 3's `ita_references.TITLE_FILES`, manifested 2012/2017/2022
structure workbooks, and its verified-citation contracts. Preserve the existing
`acquire_titles`, `read_titles`, and `parse_titles` interfaces for verification
replay. Title-only parsing is not a parent or concordance source.

Required raw references are:

| Reference | Authority and use |
| --- | --- |
| NAICS 2012, 2017, 2022 structures | Existing manifested Census originals; native membership and canonical hierarchy |
| NAICS 2012 to 2017 concordance | Full official Census relationship file; compose with 2017 to 2022 |
| NAICS 2017 to 2022 concordance | Full official Census relationship file; canonical candidates |
| NAICS 2007 structure and 2007 to 2012 concordance | Official Census originals; auxiliary membership and exemption bridge |
| NAICS 2002 complete code/title text and full 2002 to 2007 concordance | Official Census originals; bounded interpretation of exemption labels `5173` and `5181` only; no new ITA native vintage. *(owner, plan 4, 2026-10-13)* |
| SOC 2018 structure | Original BLS structure workbook; canonical occupation hierarchy |
| Historical and current designated-industry lists | Original 2016 and 2023 rule publications, including their appendices; effective-period and list membership |
| Partially exempt industry list | Official OSHA Subpart B list and its explicit 2007-vintage guidance |

Use the [Census concordance catalog](https://www.census.gov/naics/concordances/concordances.html),
[Census reference files](https://www.census.gov/naics/), and
[BLS SOC 2018 workbook](https://www.bls.gov/soc/2018/soc_structure_2018.xlsx).
Acquire complete workbooks, not changes-only concordances. Historical lists
come from the [2016 rule](https://www.federalregister.gov/documents/2016/05/12/2016-10443/improve-tracking-of-workplace-injuries-and-illnesses)
and [2023 rule](https://www.federalregister.gov/documents/2023/07/21/2023-15091/improve-tracking-of-workplace-injuries-and-illnesses).
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

Archive original bytes under `raw/references/`, with official source URLs,
SHA-256, acquisition/import time, and client version in the raw manifest.
Existing files must match their recorded hashes and sizes; absent-but-recorded,
unrecorded existing, or conflicting originals fail before acquisition. Imports
retain original bytes and flag local import time as a retrieval-time proxy.
An authenticated download is not required. If an official server blocks a
download, import its original public workbook with its registered source identity.
The offline build never fetches a missing reference.

The personal classification skill's source cache can supply original public
workbooks during import, after verifying its recorded source/hash. The cached
2012-to-2017, 2017-to-2022, and SOC 2018 originals were checked during design;
their hashes match that skill's manifest. Do not use its derived CSVs as
unmanifested production inputs or rebuild its data as part of this stage.

Read `ita_300a_summary.parquet` and retain every Stage 2 column unchanged.
Verify every unique `source_file` against the raw manifest and check that the
table's year/source inventory matches Stage 2's selected releases. Refuse a
stale or incompatible table instead of silently rebuilding it. A deliberate
Stage 2 refresh is separate from this build because Stage 3 pins its physical
Parquet bytes. Record the input Parquet hash in the build inventory.

## Classification graph contract

Canonical node tables cover all five levels of NAICS 2022 and all four levels
of SOC 2018. The shared schema is:

| Column | Type | Meaning |
| --- | --- | --- |
| `node_id` | String | `system:vintage:level:code`; globally unique |
| `system` | String | `naics` or `soc`; future geography can use the same convention |
| `vintage` | Int64 | 2022 or 2018 respectively |
| `level` | String | NAICS: `sector`, `subsector`, `industry_group`, `industry`, `national_industry`; SOC: `major`, `minor`, `broad`, `detailed` |
| `code` | String | Official code; ranges and SOC hyphens retained |
| `title` | String | Official title without workbook formatting markers |

Edges have `child_id:String`, `parent_id:String`, and `edge_type:String`.
For these classification forests, `edge_type` is `hierarchy` and the direction
is child to parent. Every nonroot has exactly one immediate parent; roots have
none. Stage 5 can add its own relationship types without assuming that every
geographic node has one parent. Do not add an invented root or use these edges
to manufacture observed relatedness targets.

Build NAICS parentage only from validated official membership and its sector
range definitions. `31-33`, `44-45`, and `48-49` are each one sector node.
Build SOC parentage from workbook nesting; trailing-zero/prefix patterns are
checks, not authority for replacing a published parent. Reject missing parents,
cycles, duplicate codes, missing titles, ambiguous headers, and contradictory
structure. Never silently deduplicate invalid structure rows.

For the existing pinned inputs, require 2,125 NAICS 2022 nodes (1,012 finest
codes, 20 sectors) and 1,447 SOC 2018 nodes (867 detailed, 23 major groups).
Native 2012/2017 structures retain Stage 3's full/six-digit checks. Validate
the 2002 and 2007 auxiliary structures and both 2002-to-2007 and
2007-to-2012 bridges against their acquired official originals, including
complete endpoint membership and parent closure. Require 2,341/1,179
full/finest nodes for the pinned 2002 text and 2,328/1,175 for 2007; record
counts and hashes in the Stage 4 finding. Both are auxiliary rule references,
not inferred ITA native vintages or new canonical systems. *(owner, plan 4, 2026-10-13)*

Publish `code_paths.parquet` with `node_id:String` and
`path:List(String)`: each path lists node IDs from its sector/major root through
the node itself. Candidate paths remain separate paths; never choose one path
for an ambiguous set. Consumers can retrieve every candidate's full path.

## NAICS relationships and candidate convention

Publish the direct official relationships in `naics_concordance.parquet`:
`source_vintage:Int64`, `target_vintage:Int64`, `source_code:String`,
`target_code:String`, `link_type:String`, and `source_file:String`.
`link_type` records `1:1`, `1:m`, `m:1`, or `m:m` according to the complete
pair relation's endpoint degrees. Preserve all distinct official code pairs
and their provenance. Source titles describing pieces do not become join keys
or allocation weights. Validate every endpoint and complete finest-code
coverage on both sides. A valid native code with a missing relationship is
reference corruption and fails the build, rather than becoming a source exception.

Compose 2012 to 2017 to 2022 over every path. Deduplicate only identical final
candidate codes; preserve the direct relationship tables needed to reconstruct
all paths. Code equality across vintages never bypasses the concordance.
Reverse traversal for rule evaluation retains every predecessor, including
the multiple predecessors of a merge. No uniform, employment, or title-based
allocation is introduced.

The common candidate convention is a sorted, duplicate-free `List(String)`
of canonical finest-level codes, with status and provenance flags alongside it.
An empty list asserts no candidate. It must not be presented as a successfully
resolved candidate set. A single-element crosswalk still carries its crosswalk
flag; a many-to-one relationship is not a native observation.

Publish a unique lookup on `(naics_code, naics_year)`, including a deliberate
null-vintage key. The lookup includes source keys plus:

| Column | Type | Meaning |
| --- | --- | --- |
| `naics_mapping_status` | String | One of the states below |
| `naics_matching_vintages` | List(Int64) | Supported vintages whose finest-code structure contains the delivered code; evidence, never correction |
| `naics_2022_candidates` | List(String) | Every supported canonical possibility |
| `naics_2022_code` | String, nullable | Single canonical code only for a valid known-vintage singleton |
| `naics_2022_node_id` | String, nullable | Corresponding canonical leaf node for that singleton |
| `naics_deepest_common_node_id` | String, nullable | Deepest canonical ancestor shared by every candidate; null for empty sets or no common sector |
| `flag_naics_crosswalked` | Boolean | A candidate-producing interpretation traverses a vintage relationship |
| `flag_naics_ambiguous` | Boolean | More than one canonical candidate |
| `flag_naics_unresolved` | Boolean | Nonmissing code has unknown vintage or is invalid in its recorded vintage |

The common ancestor describes the candidate set; it does not replace that set
or assert that the source observed a complete aggregate node. It is conditional
on the supported interpretations whenever vintage is unknown.

| Status | Rule |
| --- | --- |
| `missing_code` | Native code is null; empty candidates, null canonical scalar/path ancestor, and unresolved false; reported separately |
| `native_2022` | Known 2022 vintage and valid finest code; singleton, crosswalked false |
| `concorded` | Known valid 2012/2017 code; all official 2022 candidates, crosswalked true |
| `invalid_native_code` | Known vintage but code absent from its finest structure; empty candidates, null canonical scalar, unresolved true |
| `unknown_vintage_candidates` | Null vintage and at least one supported structure contains the code; union each matching vintage's complete mapping, unresolved true |
| `unknown_vintage_unmapped` | Null vintage and no supported structure contains the code; empty candidates, unresolved true |

Unknown-vintage support means possibilities under 2012/2017/2022, not a finding
that the record's true vintage belongs to that set. Its native vintage and
`flag_naics_year_unknown` remain unchanged. Even a singleton candidate union
does not populate the canonical scalar or clear unresolved status. A code valid
only in another vintage never rescues `invalid_native_code`; matching-vintage
diagnostics can explain that mismatch without rewriting it.

All flags are nonnullable. Candidate lists are nonnull, including empty lists.
Malformed nonmissing source codes fail the build; the accepted ITA syntax is
exactly six ASCII digits. Known vintage means 2012, 2017, or 2022 under Stage
2's harmonized contract; an incompatible input schema or other nonnull vintage
fails rather than broadening that contract silently.

Sort node, edge, path, relationship, rule, and lookup tables by their declared
keys; use a fixed column order. Workbook row order remains authoritative while
deriving SOC parents, before sorting the validated graph.

Join the unique lookup to the ITA table with explicit null-key handling. Keep
the input row multiplicities, order, identifiers, native values, and original
flags. A missing lookup result is a build error. Do not explode candidate lists
into establishment rows, deduplicate establishments, or filter unresolved rows.

## Filing-rule evaluation

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

The designated 20–249 list uses NAICS 2012 for 2016–2022 filing years and
NAICS 2017 for the 2023 filing year onward: the revised rule became effective
2024-01-01 for submissions in 2024. The original designated version became
effective 2017-01-01 for the initial 2016-data submission cycle. The partially
exempt list uses NAICS 2007 from 2015-01-01 throughout this data window.
These bindings use the nominal filing cycle (filing year plus one), not each
record's actual submission date; Stage 2 does not retain submission timestamps.
State that limitation for late filings in the finding. Record the periods
explicitly and test the
2022/2023 filing-year boundary. Unsupported filing years fail this stage's
evaluator until a recorded rule version covers them.

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

- Size class 2: outside when not designated or partially exempt.
- Size class 3: outside when partially exempt.
- Size class 1: the existing `flag_below_filing_size` already proves that
  the establishment is below the routine filing threshold.

For size classes 2/3, set `flag_outside_filing_industry:Boolean` to true or
false only when every supported evaluation gives that result. Disagreement,
missing code, invalid native code, unknown vintage with no supported
interpretation, or missing size yields null. Unknown vintage with supported
interpretations can yield a unanimous result, while its vintage/unresolved
flags remain set. Record `filing_industry_status:String` as `determinate`,
`candidate_disagreement`, `missing_code`, `invalid_native_code`,
`unknown_vintage_unmapped`, `missing_size`, or `not_applicable_below_size`.
`filing_industry_status` does not replace NAICS uncertainty flags. Resolve
status in this order: missing size; class 1 (not applicable); missing code;
known invalid code; unsupported unknown vintage; candidate disagreement;
otherwise determinate. No industry membership is asserted for class 1.

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

## Build surface, outputs, and provenance

Provide `embedding-data codes acquire`, `codes import-reference KIND FILE`,
and `codes build RUN_ID`, each with an explicit `--data-dir` option using the
repository default convention. Acquisition/import uses a registered reference
identity and official source URL. Build is deterministic and offline, requires
all manifested references and the Stage 2 input, and never reads credentials.
The implementation plan specifies command signatures and parser seams.

Publish a complete bundle under `data/derived/codes/<run_id>/`:

- `naics_nodes.parquet`, `soc_nodes.parquet`, and their edge tables;
- validated native/auxiliary NAICS structures, `naics_concordance.parquet`,
  `filing_rules.parquet`, `filing_rule_labels.parquet`,
  `filing_rule_membership.parquet`, and `code_paths.parquet`; *(owner, plan 4, 2026-10-13)*
- `ita_naics_lookup.parquet` and `ita_300a_canonical.parquet`;
- `inputs.json` and `report.json`.

Build into a new staging directory and publish the bundle only after all
checks succeed. Refuse an existing run or staging name; retain earlier runs
byte-identically. The source summary and Stage 3 run directories are never
rewritten. Record a schema/transformation version, run ID, raw input citations
and verified hashes, source Parquet hash, implementation hashes, dependency
versions, and output hashes. These build records support later manifests;
Stage 6 still implements the R7 target writer.

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

Commit a V11 (ITA) finding from the full offline build with actual raw and
reference hashes, counts, schema/version, the adopted source exception, and
the remaining uncertainty. Do not relabel preflight or fixture results as that
build. Structural completeness must hold even when source defects remain.

## Test strategy and acceptance

Use the cheapest layer that falsifies each invariant. Handwritten expected
values and small workbook/HTML fixtures exercise real parsers and transforms;
mock only HTTP/clock boundaries. Do not derive expected mappings by running
the implementation's concordance algorithm again.

| Invariant | Check layer and fixture | Marker |
| --- | --- | --- |
| Original references are immutable and verified before use | Acquisition/import integration; temporary manifest, changed/missing/unrecorded originals, streamed MockTransport responses | Default offline |
| Workbook or rule-layout drift fails loudly | Parser unit; ambiguous headers, missing titles, duplicate codes, incomplete lists and HTML impostors | Default offline |
| Nodes/edges have exact schemas and closed, acyclic parentage | Graph unit; tiny forests, orphan/cycle/duplicate cases, three ranged sectors | Default offline |
| SOC published nesting controls parentage | Parser/graph unit; fixture covering broad-group overflow rather than a fabricated prefix parent | Default offline |
| Every concordance endpoint is valid and all finest endpoints covered | Relationship unit; complete and deliberately incomplete tiny vintages | Default offline |
| Splits, merges, reshuffles, and code reuse retain every relationship | Mapping unit; hand-authored 1:1, 1:m, m:1, m:m and two-hop expected candidate sets | Default offline |
| Unknown vintage never becomes a selected vintage | Mapping unit; conflicting interpretations, singleton union, no supported vintage, and known mismatch valid elsewhere | Default offline |
| Every row has exactly one mapping status; malformed syntax fails | Mapping unit; all six states, null source, non-ASCII digit, wrong-width and nonnumeric codes | Default offline |
| Mapping joins preserve exact source rows and duplicate multiplicities | Transform/property; repeated IDs, identical rows, null-vintage keys, shuffled inputs and duplicate lookup refusal | Default offline |
| Filing version and peak-size boundaries are respected | Evaluator unit; 2022/2023 filings, classes 1/2/3/null, annual-average employment contradicting peak size | Default offline |
| Filing candidates yield a result only on unanimity | Evaluator unit; all-in/all-out/mixed candidates, exempt/designated combinations, unknown singleton union, missing bridge | Default offline |
| Sorted candidates and logical outputs are deterministic | Property/integration; reordered parsed concordance rows, repeated builds with distinct run IDs, canonical frame equality; preserve SOC sheet nesting | Default offline |
| A failed bundle is not published and existing runs/source bytes survive | Build integration; temp tree, staged failure, repeated name, source-table hash checks | Default offline |
| Raw references through graph/mapping/filing outputs work offline | CLI integration; small original-format fixtures, temp data root and a forbidden-network boundary | Default offline |

Keep ordinary tests independent of the real data tree and personal skill
cache. Every command test passes a temporary `--data-dir`; never rely on
patching the import-bound default. Missing/reference-corrupt inputs must fail
before publishing outputs, and fixture assertions include exact dtypes, list
contents, null semantics, row counts, and preserved source columns.

The default automated checks are:

```bash
uv run --locked pytest
uv run --locked behave
uv run --locked ruff check .
uv lock --check
```

The existing pytest configuration excludes `network`. No new default test
reads real data or uses a credential. If a reference-discovery canary is added,
mark it `network` and keep it opt-in; fixed workbook parsing does not require a
new live test. The full-data acceptance run is an explicit offline build with
the actual root, followed by the read-only manifest audit, graph/count/schema
checks and the committed finding. It is not a default pytest test. Require
unchanged Stage 2/3 input hashes and all 3,206,055 retained rows for the pinned
releases; changed releases need a newly recorded input inventory and counts.

Completion requires all graph and reference checks, full-row accounting,
supported candidate provenance, explicit unresolved/null diagnostics, the
V11 finding, and closure of the deferred item "Industry half of the R2.9
filing-rule flag". Use test-driven-development for library/pipeline changes
and the plan's milestone verification before marking completion.

## Rollout and later-stage handoff

The written implementation plan carries this line verbatim:

> Roadmap: specs/embedding-evaluation-data-spec-roadmap.md, Stage 4 — on plan completion, tick the stage and re-validate later stages against what shipped.

Plan completion records actual shipped schemas, output paths, reference and
transformation versions, mapping states, full-data counts, limitations, and
filing-rule null semantics in `## Handoff to later stages`. Stage 5 consumes
the node/edge convention; Stages 6, 8, 10, and 11 consume mapping/reference
contracts appropriate to their existing scope. The handoff must explicitly
tell Stage 6/10 consumers that unresolved rows do not assert a canonical code
or full path, candidate unions are uncertain, and crosswalk flags persist even
for singleton results. Later target design handles their inclusion rules under
the source spec's Core principle.

Tick Stage 4 only after the plan has shipped and its exit holds. Then
re-validate every unticked stage against that plan's actual Handoff; amend
contracts or raise a scope change through derive-roadmap as required. This
design session does not stamp completion or amend later stages as if interfaces
already existed. The source spec and roadmap stay live; this stage spec retires
through the plan-completion protocol when no live plan still implements it.
