# Target contract and ITA area-mix slice

> For agentic workers: REQUIRED NEXT SKILL: writing-plans — plan this stage
> specification in a fresh session; do not plan the source spec or roadmap wholesale.

## Scope and adopted design

Stage 6 of [the roadmap](embedding-evaluation-data-spec-roadmap.md) implements
R7.1, R7.4, R7.3's count reporting, the ITA part of R7.2 area mix, R2.2 and
R2.8, and seeds V12 from [the source spec](embedding-evaluation-data-spec.md).
The owner approved these decisions on 2026-10-14:

- Assign counties across the entire ten-year ITA establishment table, 2016–2025.
- Prove the target pipeline with 2023 establishment shares within each county,
  using six-digit NAICS 2022. Other geographic levels are assignment attributes;
  they do not become target tables in this stage.
- Use a dedicated pipeline: offline preparation, explicit Census acquisition,
  then offline assignment and target construction through a shared writer.
- Preserve source-row order and multiplicity, including exact duplicates and
  repeated establishment IDs. The counting unit is a submitted establishment-year
  record, not an independently confirmed unique establishment.
- Include valid native-2022 industry observations with adopted compatible county
  assignments. Employment, hours and filing-rule flags remain diagnostics rather
  than target filters. Crosswalked and unresolved industry values remain excluded.
- Give each included record weight one, report cell counts, and use null standard
  errors with `se_method='none'`. No count threshold is set or passed here.
- Publish immutable assignments, the target, denominators, coverage/flag diagnostics
  and verified provenance. Require both an offline fixture contract and a measured
  production build before claiming Stage 6 completion.

The alternatives considered were extending Stage 3's verification runner, which
couples sampling to source rebuilding, and introducing a framework for all eight
families before their estimators exist. Reuse the existing verified interfaces
without adopting either architecture. Keep logical components independently
testable; do not refactor unrelated acquisition or classification code.

ACS/CPS transformations, other target families, employment-weighted ITA shares,
industry or geographic rollup targets, crosswalk-included target variants,
establishment deduplication/linkage, historical geography reconstruction, and the
V9 size gate remain outside this stage. Relatedness comes from observed records;
candidate ancestors and formal graph distances cannot produce target values.

## Selected inputs and inherited contracts

Explicitly select the following production inputs. Run IDs are required arguments,
not a latest-run lookup or an implicit alias:

| Input | Selected production identity | Contract |
| --- | --- | --- |
| Stacked source | `data/derived/osha/ita_300a_summary.parquet` | Stage 2's unchanged source, 3,206,055 rows; raw citations through `source_file` |
| Classification bundle | `data/derived/codes/stage4_v11_20261013_r2/` | `codes-ita-v1`; separate `ita_300a_canonical.parquet`, graph/path/concordance tables and inventories |
| Geography bundle | `data/derived/geography/stage5_geography_20261014/` | `geography-v1`; all six table schemas and inventories |
| Raw provenance | `data/raw/manifest.jsonl` | Hash-and-size-verified citations through `manifest.entry_for` |

The authoritative consumer details are the [Stage 4 handoff](plans/completed/4-code-tables-ita-naics-mapping.md#handoff-to-later-stages),
[V11 inventory and measurement](findings/v11-ita-naics-mapping.md),
[Stage 5 handoff](plans/completed/5-geography-hierarchy-county-reference.md#handoff-to-later-stages),
[geography production finding](findings/stage-5-geography-reference-build.md),
[Stage 3 handoff](plans/completed/3-ita-verification.md#handoff-to-later-stages),
and [adopted county finding](findings/v1-v3-ita-verification.md).
Carry their exact schemas, nullable fields, independent flags and provenance
limits forward. The current detached `outputs.json` hashes are:

- Stage 4: `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`.
- Stage 5: `5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d`.

A selected-bundle verifier checks the detached inventory, every listed file's
hash and size, schema/version, row counts, referenced raw bytes and required
node relationships before using it. Selection of a different run requires its
own verified inventory and must appear explicitly in the output provenance.
Do not mix runs. Check the source summary and canonical table against the selected
Stage 4 source hash and source-row parity, including multiplicity and order.
Do not call `osha`, `build_summary_table` or verification `sample` to prepare
Stage 6. Leave source summaries and all previous bundles and verification runs
unchanged. The read-only checking seams may use temporary harmonized fixtures;
they never replace a production source.

Stage 4 candidate lists remain nonnull, sorted possibilities. Unknown-vintage
unions, including singletons, never supply canonical scalar/node IDs. Known-vintage
mismatches are not repaired by another vintage. Historical singleton crosswalks
retain `flag_naics_crosswalked`; no candidate is allocated or selected as observed.
Nullable filing decisions do not become false. Preserve original `size` and the
harmonized `size_class`; annual-average employment does not reconstruct peak size.

The recorded V11 inputs contain 358,294 `native_2022` records in 2023 and 222,166
in 2024 before geography eligibility. This motivated 2023; these are upstream
measurements, not completed targets. The Stage 2 [V10 finding](findings/v10-ita-300a-totals.md)
records submission-count gaps and source defects; do not tune counts to published
levels or infer that filings outside a nominal rule were improper.

## Pipeline and immutable run boundary

Expose a `targets` command group under the existing `embedding-data` entry point:

| Planned command | Behavior |
| --- | --- |
| `targets prepare-ita ASSIGNMENT_RUN_ID --codes-run CODES_RUN_ID --geography-run GEOGRAPHY_RUN_ID --data-dir ROOT` | Offline verification and frozen full-table requests/mapping |
| `targets acquire-ita ASSIGNMENT_RUN_ID --data-dir ROOT` | Explicit acquisition/resume of the frozen Census requests |
| `targets build-ita ASSIGNMENT_RUN_ID TARGET_RUN_ID --year 2023 --data-dir ROOT` | Fully offline publication of all-year assignments and the selected-year target |

Stage 6 supports only `--year 2023`; another year fails before publication.
Expanding the target years belongs to later explicitly designed build work.
An input with no eligible 2023 records fails before publishing an empty target.
There is no automatic acquisition from `prepare-ita` or `build-ita`.

Freeze preparation under `data/derived/osha/assignment-inputs/<assignment_run_id>/`.
Acquire original catalogs/responses under
`data/raw/references/census-geocoder/ita-assignment/<assignment_run_id>/`.
Publish the combined assignment/target bundle under
`data/derived/targets/<target_run_id>/`. A new target run may replay the same frozen
assignment inputs; it must verify them afresh and cite the same cached evidence.

Use the existing safe run-ID/path conventions. Prepare and build write new
`.part` directories and rename only after complete validation. An occupied final
or staging name fails without overwriting it; a leftover `.part` is an interrupted
run that must be inspected and removed before a new attempt. Acquisition may resume
an existing preparation by validating already published raw receipts and fetching
only missing batches. Existing immutable raw files are never overwritten.

### Preparation and request identity

Freeze the canonical table's physical hash and a source index with contiguous
zero-based `source_row: UInt64` and `request_id: String`, one row per canonical
source row. Its key is `(canonical_sha256, source_row)`. Preserve the table's
original ordering and repeated rows; neither `id` nor `establishment_id` is assumed
unique. Stage 3's exact-distinct sample and whole-row hash are not substitutes
for this production identity.

A request ID is the SHA-256 of a versioned, unambiguous UTF-8 serialization of the
four fields actually submitted: delivered street, city, state and the existing
Stage 3 `zip_key` normalization. Encode a four-element JSON array with fixed
serialization, mapping null submitted fields to empty strings. Keep the original
delivered fields in the source. Do not casefold, NFKC-normalize, repair, or use
linkage's normalized full-address key to merge distinct submitted requests.
Verify hash-to-tuple uniqueness, and preserve the many-to-one row mapping.

Freeze `request_index.parquet` with `request_id`, the four nonnull submitted
string fields, and `n_source_rows: UInt64`. Include every distinct submitted tuple,
including partial/blank and delivered-state-excluded tuples, as Stage 3 did;
incomplete addresses remain diagnostic, not invented complete addresses. Sort by
request ID and write headerless UTF-8 CSV batches of at most 1,000 rows using
the existing CSV quoting/order contract: ID, street, city, state, ZIP. Response
IDs must exactly cover these requests, even where the service reports no match.

Preparation's `inputs.json` records source/bundle inventories, exact source-index,
request-index and request-file hashes, normalization/identity versions, dependency
and implementation hashes, lock hash and observed row/request totals. Publish a
detached inventory for the other preparation files. Code/dependency changes to
preparation or assignment invalidate resume/build and require new preparation;
there is no silent mixed-version resume. Unrelated changes to a later estimator
may produce a new target run with their own recorded implementation inventory.

Owner amendment (2026-10-14): use a Stage 6 operational batch limit of 1,000,
within the unchanged Census service maximum of 10,000. The original immutable
`stage6_ita_assignment_20261014` preparation and its acquisition controls remain
unchanged, with their original software identity and incomplete status. After a
peer reset before response headers on its full first batch and a successful
1,000-record diagnostic, create `stage6_ita_assignment_20261014_1000` under the
amended software. Preserve identical source-row/request identities and submitted
tuples; only the request partition and its recorded software/provenance change.
Do not import diagnostic subset responses into either production acquisition.
For the measured 1,113,538 requests, expect 1,114 batches (1,113 of 1,000 and
one of 538); verify the actual files. Selected upstream runs, Current options,
sequential execution, 600-second timeout and explicit verified resume are retained.
Acceptance uses new target IDs `stage6_ita_area_mix_20261014_1000` and
`stage6_ita_area_mix_20261014_1000_replay`.

The read-only design workload estimate was 1,113,538 distinct submitted tuples
across 3,206,055 source rows, before any request filtering. It is a planning bound,
not a count of completed calls. Deduplicating public request tuples changes call
volume; it never changes record counts in assignment or targets.

### Census acquisition and offline replay

Reuse Stage 3's batch request format, response parser, exact response-ID validation,
manifested original download and receipt conventions. Resolve `Public_AR_Current`
and `ACS2025_Current` uniquely from manifested service catalogs; record the selected
names and returned IDs, rather than assuming the formerly measured IDs 4 and 425
will remain available. If an option is unavailable or ambiguous, stop without
substituting another benchmark/vintage.

For every batch, record request hash, response path/hash/size, original acquisition
time and the chosen options. Verify cached bytes and exact expected IDs on both
resume and offline build. A missing, extra, repeated or malformed response ID is
a failed acquisition, not an unmatched address. Cache paths include the assignment
run and request hash. Stage 3's sample receipts are not automatically reused as
a cross-run address cache. Production acquisition for this stage creates its own
receipts; earlier verification responses remain untouched.

Keep acquisition sequential with the existing client timeout/error behavior.
A transport or validation failure stops the invocation; an explicit re-run resumes
from verified completed batches. Do not add blind retries or change a frozen
request to make a response pass. Incomplete raw `.part` downloads are never cited.
Record acquisition start/end and preserve each receipt's original time.

Current address ranges may change between batches or resumed requests. Catalog
snapshots identify the requested options, not an immutable service address frame.
Offline determinism means replay of verified cached evidence, not identical
answers from future Census requests.

## Full-table county assignment

The offline builder applies this precedence to every source row:

1. Normalize delivered state only for the adopted scope check. PR/VI/GU/AS/MP/UM
   veto assignment, independent of method diagnostics.
2. A Census `Match` plus `Exact` returned county in an excluded territory prefix
   (60/66/69/72/74/78) remains unassigned and cannot fall through to HUD.
3. Otherwise a `Match` plus `Exact` county present in the selected complete county
   inventory supplies the assignment.
4. Otherwise the selected HUD lookup may supply `zip_fallback_county` only with
   `eligibility_status='eligible'`: exactly one original positive-BUS county,
   compatible with that inventory and in scope.
5. All remaining rows stay unassigned with explicit reasons.

Retain raw geocode status, match type and returned county alongside the chosen
assignment. Report exact-match, non-exact, tie and no-match coverage separately
from assignment eligibility. Preserve method-specific returned-county scope,
legacy Connecticut and incompatible-county flags, and delivered-state scope
independently. A compatible exact Census assignment is not vetoed by an excluded
or ambiguous HUD alternative. An incompatible/non-exact Census alternative does
not prevent an otherwise eligible adopted HUD fallback.

HUD cardinality is evaluated on all original positive candidates before scope
checks. A usable county plus an excluded candidate is still ambiguous. Preserve
every candidate, diagnostic maximum/tie, absent ZIP versus present zero-business
ZIP, and all original independent flags. Largest-share selection, zero-share
selection and invented old-Connecticut bridges never supply assignments.

Derive assigned county/state/division/region IDs and optional CBSA membership only
from the selected `county_reference`. Preserve the 2025 administrative and July
2023 CBSA frames separately, both metro/micro types and central/outlying roles.
Non-CBSA counties have null CBSA fields; multi-state CBSAs have no scalar state
parent. This is a common reference frame for old addresses, not historical county
geography. Source delivered state remains separate from derived state.

### Assignment artifact

`ita_county_assignments.parquet` preserves all 38 Stage 4 canonical columns with
their exact types/order, followed by these additions under `ita-assignment-v1`:

- `source_row: UInt64`, `request_id: String` (nonnull, source order preserved).
- `zip_key: String` (nullable normalized source ZIP); `geocode_status: String`
  (nonnull), `match_type: String` and `geocode_county_geoid: String` (nullable,
  using the Stage 3 parser's status/null conventions).
- All selected `hud_zip_lookup` columns except its already represented `zip_key`,
  with existing types. For absent ZIPs set `eligibility_status='absent'`, zero row
  and positive-candidate counts, empty candidate lists, false lookup flags and
  null candidate/max/fallback scalars. Preserve presence through the status.
- All `county_reference` columns in their published order/types. They describe
  the chosen county; all are null when unassigned, and optional CBSA fields stay
  nullable for assigned non-CBSA counties.
- `assignment_method: String`, one of `census_exact`, `hud_singleton`, `unassigned`;
  `assignment_reason: String`, a nonnull reason from the precedence above.
- Nonnullable Boolean flags: `flag_delivered_state_out_of_scope`,
  `flag_geocode_county_out_of_scope`, `flag_geocode_county_incompatible`,
  `flag_geocode_county_legacy_ct`, `flag_request_incomplete`, and
  `flag_assignment_hud`. Excluded returned counties are distinct from in-scope
  incompatible counties. Legacy CT is recorded independently.

Reject overlapping appended column names or a schema mismatch. Preserve HUD's
original-singleton `zip_single_candidate` and `zip_fallback_county` meanings;
null does not assert that a candidate never existed. Reports include every
assignment reason, scope/method partition and independent flag count by filing
year. Disjoint row-accounting totals and overlapping diagnostic flags are named
separately.

## Area-mix estimator and coverage

Select filing year 2023 from the assignment artifact. An eligible record has
`naics_mapping_status='native_2022'`, a valid nonnull six-digit
`naics_2022_node_id`, no crosswalk/ambiguity/unresolved flag, and a nonnull chosen
county under the adopted assignment rule. Referenced nodes must exist in the
selected bundles with the expected system, vintage and level. Consistent native
rows cannot be silently repaired if their scalar/flags contradict their status.

For county `a` and industry `b`, let `C(a,b)` count eligible submitted records,
including preserved duplicates, and `D(a)` count all eligible records in that
county. Emit `value = C(a,b) / D(a)` only for observed cells with `C(a,b)>0`.
Use the same eligibility population in numerator and denominator. Shares sum
to one within each county with `D(a)>0`; no Cartesian product or synthetic zero
cell is emitted. An industry’s geographic distribution is a different estimand.

Each record contributes one: `n_unweighted=C(a,b)` and
`n_weighted=float(C(a,b))`. These are cell support counts, not denominator counts
or employment totals. Set `se=null` and `se_method='none'`; neither a zero SE nor
a bootstrap of filings is a claim about representative population precision.

Do not filter on employment/hours anomalies, below-size/outside-rule flags,
nullable filing decisions or independent filing-reference flags. Preserve and
report them, including null counts. Crosswalked/unknown/mismatched industries
and unassigned geography are diagnostic exclusions. They never become guessed
industries/counties, fractional candidates, ancestors or an unknown-category
headline cell. The adopted compatible HUD singleton is an allowed county method
under R2.8 and remains explicitly marked.

`county_denominators.parquet` has `sample_set: String`, `county_id: String`,
`n_assigned: UInt64`, `n_eligible: UInt64`, and `n_excluded_industry: UInt64`.
Include every county with assigned records in the selected year, including those
with zero eligible records. Here `D(a)=n_eligible` and
`n_assigned=n_eligible+n_excluded_industry`. Unassigned geography appears in the
global/year coverage report because no county denominator can contain it.

`target_flag_counts.parquet` has `scope: String` (`numerator` or `denominator`),
`county_id: String`, `naics_2022_node_id: String` (null only for denominator rows),
`flag_name: String`, `flag_state: String` (`true` or `null`), and `n: UInt64`.
For each participating source/assignment diagnostic Boolean column, emit positive
counts of true and null values for each cell and county denominator; false counts
are recoverable from the associated support count. Include source provenance
Booleans such as `naics_year_from_dictionary`. Empty diagnostics have the exact
typed schema. Do not coerce source null flags to false.

The report records source/assigned/eligible/excluded counts by year and, for 2023,
mapping-status × assignment-status counts, duplicate full-record and repeated-ID
diagnostics, county denominator distributions and cell-count distributions.
Count exclusions once in disjoint partitions, while retaining overlapping reasons
and flags separately. A repeated ID is a diagnostic, not an assertion that rows
describe the same establishment. Neither source nor target is tuned to OSHA's
published submission counts.

## Shared target contract

`targets-v1` uses exactly R7.4's columns in this physical order:

| Column | Type | Nullability / Stage 6 value |
| --- | --- | --- |
| `source` | String | Nonnull; `osha_ita` |
| `family` | String | Nonnull; `area_mix` |
| `unit_a_type` | String | Nonnull; `county` |
| `unit_a` | String | Nonnull; selected geography county node ID |
| `unit_b_type` | String | Nonnull; `naics_national_industry` |
| `unit_b` | String | Nonnull; selected six-digit NAICS 2022 node ID |
| `measure` | String | Nonnull; `establishment_share` |
| `value` | Float64 | Nonnull, finite; `C(a,b)/D(a)` |
| `se` | Float64 | Nullable; null for `none` |
| `se_method` | String | Nonnull; `none` |
| `n_unweighted` | UInt64 | Nonnull; `C(a,b)` |
| `n_weighted` | Float64 | Nonnull, finite/nonnegative; `float(C(a,b))` |
| `sample_set` | String | Nonnull; `ita_300a_2023` |
| `vintage` | String | Nonnull; `naics=2022;county=2025` |
| `universe` | String | Nonnull; explicit universe below |
| `flags` | List(String) | Nonnull sorted/distinct nonempty flag strings |

An empty flag list is valid for the shared contract. ITA rows always contain
`size_gate_pending`; additionally encode nonzero true/null support flags from
`target_flag_counts` as `<scope>:<flag_name>:<flag_state>` for both the numerator
and its denominator. The companion table carries counts; labels do not imply
that all contributing records were flagged. Assignment provenance is included,
even when county and industry outputs are determinate.

The ITA universe states: OSHA ITA Form 300A is a program-selected filing subset,
not a frame representative of all establishments; voluntary/outside-rule filings
are retained and reported employment is unvalidated. This target counts submitted
2023 establishment-year records with preserved duplicate multiplicity, valid
native NAICS 2022 industries and adopted compatible county assignments in the
common 2025 frame, within the 50 states and DC. It is conditional on that eligibility
population. Every target row carries this statement, and the manifest records
the full eligibility and counting rules. No row claims to pass a size gate.

The shared writer validates exact schema, nonempty metadata and typed unit IDs,
finite values, nonnegative counts and unique keys across every column except
`value`, `se`, counts and `flags`. `se_method` admits `none`, `replicate` or
`bootstrap`: `none` requires null SE; the others require finite nonnegative SE.
It does not hardcode ITA's fraction range or census-unit counts for other families.
Family-specific validators check referenced units, measure, share bounds, support
counts and normalization. Later profiles use `unit_b_type` to identify a feature
and `unit_b` for its feature identity under the same schema; this stage implements
no profile estimator. ITA text pairs and hierarchy tables remain separate.

Sort targets lexicographically by their key columns and diagnostics by their
documented keys. Identical cached inputs/software produce identical logical rows
and canonical JSON; physical Parquet hashes are inventories of a particular run,
not a promise of stable serialization across dependency versions.

## Output manifest, error handling and publication

A target run contains `ita_county_assignments.parquet`, `ita_area_mix.parquet`,
`county_denominators.parquet`, `target_flag_counts.parquet`, `inputs.json`,
`report.json` and detached `outputs.json`. The last hashes the other six files,
including byte sizes, row counts and exact schemas for Parquets, and excludes
itself. Record its detached checksum in the production finding.

The manifest inventories all consumed raw `source_file` values across the ten-year
assignment, dictionaries and selected upstream raw references, Census catalogs
and every raw response, using `manifest.entry_for` verified hash/size citations.
It also identifies the 2023 target-specific source-file subset. Cite the source
summary and canonical physical hashes, selected bundle detached hashes and
inventories, all frozen preparation files and receipts, code/crosswalk/normalization/
assignment/estimator versions, implementation hashes, dependency versions, lock
hash and execution commit. Upstream inventories provide transitive provenance;
record it explicitly rather than substituting only a derived-file hash for raw
citations. `recorded_entry_for` is lookup-only and cannot verify target provenance.

Use `ita-assignment-inputs-v1`, `ita-assignment-v1`, `targets-v1` and
`ita-area-mix-v1` as distinct versioned preparation, assignment, schema and
estimator contracts. Record HUD 2025Q4, administrative 2025, CBSA July 2023 and
Census selected options separately; one generic vintage must not erase them.
Manifest appends outside this run do not invalidate an otherwise unchanged set
of cited files; validate the cited entries and pinned input bytes.

Missing/changed bytes, incompatible versions/schema, malformed requests/responses,
invalid response-ID sets, missing/incorrectly typed graph nodes, contradictory
canonical states, row loss/multiplication, invalid estimates or counts, and
occupied output names fail before final publication. Report a useful path/run/batch
and reason without printing establishment addresses. A service no-match, ambiguous
HUD ZIP, known-vintage industry mismatch, out-of-scope result or missing CBSA edge
is an expected retained diagnostic when its upstream contract permits it.

No network or credentials are used by offline commands. Raw downloads and prior
production artifacts remain immutable, and requests/assignments stay in the
gitignored local data tree. Share aggregates, not IPUMS microdata; do not feed
evaluation targets to embedder training, architecture tuning or model selection.

## Verification and completion evidence

Follow red → green for pipeline/library behavior and reuse existing fixtures and
test seams. This spec defines observable outcomes; the fresh writing-plans session
chooses task boundaries and exact test commands.

1. **Frozen identity and provenance:** duplicate full rows/repeated IDs survive;
   identical submitted tuples share a request; source order and counts are exact.
   Distinct submitted strings do not merge under linkage normalization. Changed
   source/bundle/request/cache bytes, wrong sizes or schemas and mixed software
   contracts fail. Catalog/request/receipt hashes are checked on resume and replay.
2. **Assignment rules:** exact compatible Census wins; compatible HUD singletons
   work after non-exact/no-match/incompatible alternatives. Exact excluded Census
   and delivered-state vetoes hold. Test multiple positive counties including an
   excluded candidate, zero-business versus absent ZIP, tied maxima, legacy CT,
   unexpected incompatible counties, metro/micro and non-CBSA counties, cross-state
   membership, incomplete fields and preserved independent flags.
3. **Estimator and writer:** hand-calculated fixture numerators/denominators and
   preserved duplicates agree with output. Industry exclusions and geography
   exclusions have exact disjoint coverage counts. Shares sum to one per eligible
   county with explicit tolerance, within `1e-12` for small fixtures. Counts and
   no-SE/null semantics agree; employment/hour/outside-rule anomalies remain
   included when industry/geography are eligible. Check true/null flag support in
   both numerator and denominator, sorted flags, node IDs, uniqueness and schema.
   Do not impose a minimum cell count.
4. **V12 vertical slice:** fixture original raw summaries/dictionaries pass through
   existing conversion/harmonization, fixture official code mapping and geography
   reference construction, frozen requests with fixture original Census responses,
   full-table assignment, one area-mix target and verified manifest. Network and
   credential access are unavailable. Fixture acquisition may use a mock transport;
   offline preparation/build never call it. Later family stages extend the harness
   with their own raw-to-target paths rather than claiming all V12 is done here.
5. **Failure/publication behavior:** incomplete or malformed acquisitions cannot
   masquerade as no-match, cached receipts resume without another call, interrupted
   staging is not a final run, occupied names never overwrite, and validation
   failure publishes no final target bundle. Replay gives identical logical outputs
   and canonical JSON apart from explicitly identified run IDs/provenance times.
6. **Production milestone:** verify selected real input inventories, prepare/acquire
   all-year requests, build the actual 2023 target, and commit a measured finding
   at `specs/findings/stage-6-ita-area-mix-build.md`. Record selected runs, raw/request/
   response/software/output inventories and detached checksum; all-ten-year row
   accounting, method/scope coverage, 2023 eligibility/denominators, duplicate/flag
   counts, cell-count distributions and cached replay evidence. Verify protected
   prior artifacts remain unchanged and run the whole-tree manifest audit.

The pipeline commands are planned, not existing capabilities. A fixture result
cannot satisfy the production milestone. Run repository pytest, Behave, ruff and
lock checks at implementation completion and record their observed outputs.
The finding must distinguish conditional coverage from county accuracy and from
representativeness of all establishments. Current-service variability remains a
recorded limit even after a successful cached replay.

## Rollout and later-stage handoff

The owner approved this design on 2026-10-14. Planning follows review of this
written spec; implementation and production acquisition belong to that plan.

> Roadmap: specs/embedding-evaluation-data-spec-roadmap.md, Stage 6 — on plan completion, tick the stage and re-validate later stages against what shipped.

Stage 6 completion requires the measured all-year assignment and 2023 target
milestone, verified output manifest and this family's offline V12 path. R7.3 is
closed only for count reporting; V9 and the gate remain Stage 13. Mark only the
Stage 6 roadmap item complete after those outcomes are verified.

The implementation plan's Handoff must identify the selected assignment/target
bundle and its verified inventories; the `targets-v1` schema, writer and validator
interfaces; per-family estimator/uncertainty responsibilities; flag/denominator
semantics; and the fixture harness extension point. Revalidate Stage 9 ACS area
mix and other families, Stage 10 ITA pairs, Stages 11–12 CPS estimators and Stage 13
full-build count-gate work against the actual shipped APIs. Keep ACS replicate
weights and allocation variants, CPS weight/uncertainty rules and text-pair tables
in their own stages. Do not treat this one-year native-industry slice as all-year
headline coverage or as completion of all eight V12 families.
