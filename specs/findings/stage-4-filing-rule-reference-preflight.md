# Stage 4 filing-rule reference preflight

Measured 2026-10-13 against `main` at `6f8c190` while planning Stage 4 of
[the roadmap](../embedding-evaluation-data-spec-roadmap.md). This is reference
compatibility evidence, not a completed V11 finding, an adopted rule
interpretation, or a canonical ITA build. No project raw file, raw-manifest
entry, source Parquet, or Stage 3 verification run was changed.

## Conflict with the approved design

The [stage design](../completed/code-tables-ita-naics-mapping.md#filing-rule-evaluation)
binds the partially exempt list to NAICS 2007, requires every listed node to
exist in that vintage, and treats a missing supported reference relationship
as a build error. The complete official 2014 rule appendix contains 82 listed
groups. Two of them are absent from Census's complete 2007 structure:

| Published label | Published title | 2007 membership | 2002 membership |
| --- | --- | --- | --- |
| `5173` | Telecommunications Resellers | Absent | Present |
| `5181` | Internet Service Providers and Web Search Portals | Absent | Present |

The other 80 listed groups exist in the 2007 structure. Both designated
lists validate in their prescribed vintage: 66 groups in NAICS 2012 and
65 groups in NAICS 2017. The 2023 final Appendix A must be bounded before
the separate Appendix B; including both would produce 169 rows.

The [2014 official rule edition](https://www.govinfo.gov/content/pkg/FR-2014-09-18/html/2014-21514.htm)
and [current OSHA regulatory appendix](https://www.osha.gov/laws-regs/regulations/standardnumber/1904/1904SubpartBAppA)
both publish the two legacy labels. [OSHA FAQ 2-4](https://www.osha.gov/faq/2-4)
describes the exemption list as NAICS 2007 and preserves exemption despite
subsequent code revisions. The rule's economic analysis also discusses the
2002-to-2007 restructuring. Those statements do not make the two labels
valid 2007 nodes or authorize treating a partial relationship as a whole
industry exemption.

## Method and reproducibility

Read original public references in temporary storage, outside the project
data tree. Workbooks were read with
`pl.read_excel(..., has_header=False, read_options={'dtypes': 'string'})`.
The existing `ita_references.parse_titles` read all 2,328 NAICS 2007 nodes,
including 1,175 six-digit leaves. Parse original GovInfo HTML using the
standard-library `HTMLParser`; take the final enacted Appendix A heading,
bound it before the next appendix, and read its dotted code/title rows.
Compare every original listed group with the structure's complete code set.
No descriptions, industry codes, or vintages were inferred from ITA records.

For additional reference-only investigation, read Census's full NAICS 2002
code/title text and complete 2002-to-2007 concordance. The text contains
2,341 nodes/1,179 six-digit leaves. The direct relation has 1,200 distinct
pairs covering all 1,179 source and 1,175 target leaves. These are proposed
auxiliary references; they have not been acquired into the project manifest.

| Public original | SHA-256 |
| --- | --- |
| [NAICS 2007 complete code workbook](https://www.census.gov/naics/reference_files_tools/2007/naics07.xls) | `9eaa1fc4681ad22296b8f09603dc3674605eeb13b0fd631811d51704e1c2f463` |
| [2014 rule original HTML](https://www.govinfo.gov/content/pkg/FR-2014-09-18/html/2014-21514.htm) | `3418238856a56bf0da7bac73a1a07535a4f098e3212287a35048602968855a87` |
| [NAICS 2002 complete code/title text](https://www.census.gov/naics/reference_files_tools/2002/naics_2_6_02.txt) | `b05cb32865d9267eaca4c2df45b89605c02320c5d1794b0ba0304e2c1741edaf` |
| [Complete 2002-to-2007 concordance](https://www.census.gov/naics/concordances/2002_to_2007_NAICS.xls) | `a4b00b2195e318420962ba52b77f3c3122e83d893a9f804e820c151847ec85b1` |

The official Census Downloadable Files panel supplied `naics07.xls`'s URL.
A guessed `2007NAICS/2007_NAICS_Structure.xls` URL returns 404. Direct
OSHA exempt-table requests returned 403; the accessible regulatory appendix
and FAQ above provide the current authority comparison. Scripted
FederalRegister.gov requests returned access-challenge HTML with status 200;
the corresponding GovInfo originals were accessible and parsed successfully.
An HTML challenge check must use the page title/required structure, because
the real 2023 rule itself contains the ordinary words “request access.”

## Official relationships and why a simple repair is unsafe

The complete official bridge gives:

| 2002 leaf | 2007 candidate(s) |
| --- | --- |
| `517310` | `517911` |
| `518111` | `517110`, `517919` |
| `518112` | `519130` |

The 2007 `517110` leaf has three 2002 predecessors: `517110`, `517510`,
and `518111`. Only the last is inside the legacy listed group `5181`.
Consequently, expanding `5181` to every target and declaring all of 2007
`517110` exempt would assert more than the relationship supports. This is
an inference from the official relation, not an adopted interpretation of
OSHA's rule. It affects the certainty of industry diagnostics and cannot be
settled by dropping the invalid labels or by numeric prefix matching.

The other legacy successors sit under explicitly listed 2007 groups
`5179` or `5191`. A bounded legacy-label bridge therefore needs to preserve
partial coverage and the nonlegacy predecessors of merges, even when many
of its target codes already have a whole-group exemption.

## Proposed bounded resolution

**Research authorized by the owner, 2026-10-13:** develop the bounded bridge
and bring the exact interpretation back for approval. This authorization
does not adopt the interpretation or permit production implementation.

The exact proposed amendment is
[Task 0 of Plan 4](../plans/completed/4-code-tables-ita-naics-mapping.md#task-0-apply-the-exact-approved-bounded-bridge-amendment).
It preserves every original label, admits only the two documented legacy
exceptions, and requires complete official structures and relationships.
The entire exemption list retains its nominal 2007 vintage; neither the
whole list nor an ITA row is reclassified as 2002.

For a 2007 finest code `b`, let `W` be the valid 2007 listed groups'
whole-node expansion, `L` the two legacy labels' 2002 leaf expansion, and
`P(b)` every official 2002 predecessor. The proposed membership is:

```text
{true}                         if b belongs to W
union of {p belongs to L}       otherwise, for every p in P(b)
```

There must be at least one predecessor, and the full bridge must cover
every source/target finest code. This yields `{false}`, `{true}`, or
`{false, true}` without weights or a preferred predecessor. Retain a
bridge provenance flag whenever a predecessor belongs to `L`, including
cases in which whole-node membership already determines `{true}`.

Three proposed table contracts make that interpretation inspectable:

| Table | What it asserts |
| --- | --- |
| `filing_rule_labels.parquet` | Original labels, nominal rule vintage, interpreted label vintage, legacy-label flag and raw source citation |
| `filing_rule_membership.parquet` | Complete rule-native finest-code coverage, explicit Boolean membership possibilities, periods, source citation and bridge flag |
| `filing_rules.parquet` | Exactly the definite `{true}` projection; a mixed possibility is never asserted as definite membership |

The evaluator consumes those possibilities within each supported native
interpretation and emits a Boolean result only on unanimity. Add separate
`flag_filing_rule_label_bridged` and `flag_filing_reference_ambiguous`
diagnostics; both survive a determinate final result. Missing size, below-size,
missing code, invalid native code or unsupported unknown vintage does not
evaluate industry membership, so these two provenance flags are false for
those statuses. Native mapping/vintage flags remain independent.

## Prototype verification of the proposed contract

Temporary execution of the proposed plan snippets validated all five
official NAICS structures and all four complete adjacent-vintage bridges.
It retained all 213 original labels (66 + 65 + 82), with exactly two marked
as legacy. The following counts describe **proposed reference outputs**,
not an adopted filing interpretation or a completed ITA build:

| Rule | Finest-code membership rows | Definite true | Mixed | Bridge flag |
| --- | ---: | ---: | ---: | ---: |
| designated 2012 | 1,065 | 689 | 0 | 0 |
| designated 2017 | 1,057 | 683 | 0 | 0 |
| partially exempt 2007 | 1,175 | 252 | 1 | 4 |
| **Total** | **3,297** | **1,624** | **1** | **4** |

The sole mixed code is 2007 `517110`. The four bridge-marked codes are
`517110`, `517911`, `517919`, and `519130`; the latter three have definite
membership under the valid 2007 groups. No legacy label was dropped or
expanded wholesale across a merge.

Two real-reference evaluator examples, using filing year 2022 and a valid
2012-native `517110`, demonstrate the proposed diagnostic behavior:

| Harmonized peak-size class | Proposed industry status | Proposed outside flag | Bridge flag | Reference ambiguity flag |
| --- | --- | --- | --- | --- |
| 2 (20–249) | `determinate` | true | true | true |
| 3 (250+) | `candidate_disagreement` | null | true | true |

The class-2 designated-list possibilities already establish an outside
result irrespective of the mixed exemption membership. Class 3 depends
on that membership, so its result stays null. These are checks of the
proposed conservative algorithm, not determinations about an observed
submission or whether an individual establishment is legally exempt.

Two genuine-original-format fixture bundles also retained source rows and
duplicates, source bytes, exact schemas, and logical determinism. The
experiments wrote only temporary files. At the prototype checkpoint the stage/source specs, raw manifest/data
and Stage 3 runs were unchanged; D2 subsequently authorizes the eight
stage-spec documentation replacements recorded below. Project raw
manifest/data and Stage 3 verification runs remain untouched.

## Review status

The owner approved the exact eight spec replacements and revised Plan 4
on 2026-10-13 (D2). Task 0 applies that conservative reference interpretation
and its schemas to the stage spec; the original conflict and prototype
measurements above remain the evidence trail. This adopts an evaluation
policy, not an externally confirmed legal interpretation. Implementation
Tasks 1–8 still require execution and verification. ITA's admitted native
vintages and canonical NAICS 2022 system remain as approved; the roadmap
Stage 4 checkbox and carried industry-flag item remain open.
