# Geography hierarchy and county reference

## Scope and adopted design

Stage 5 of [the roadmap](embedding-evaluation-data-spec-roadmap.md) implements
R6.1, R6.2 and R6.4 and supplies the production references for the adopted R2.8
method in [the source spec](embedding-evaluation-data-spec.md). The owner
approved the design on 2026-10-13:

- Include both metropolitan and micropolitan CBSAs, preserving their types.
  Counties outside both types have no CBSA membership edge.
- Use a dedicated geography builder with Stage 4's shared node/edge schemas
  and immutable-bundle provenance conventions.
- Keep the administrative hierarchy and CBSA membership as separate typed
  relationships; no CBSA has a forced state parent.
- Supply complete county/CBSA references and a HUD candidate/eligibility
  lookup, including zero-business-share and incompatible/excluded diagnostics.
- Acquire/import original references separately from an offline build.

The [reference preflight](findings/stage-5-geography-reference-preflight.md)
settles the original layouts, hashes, scope counts and compatibility checks.
It is design evidence, not a completed production build.

This is one geography-reference cycle. Establishment assignment and targets
remain Stage 6; PUMA allocation and V8 remain Stage 8. Historical geography,
metro divisions, CSAs, ZIP-to-ZCTA conversion and a generic graph-framework
refactor are outside this stage. No relatedness target is inferred from the
hierarchy.

## Inputs and reference boundary

Use repository-owned acquisition/import, parsing, geography validation,
HUD lookup and build orchestration. Follow existing manifest and publication
patterns without extending classification validators to geography. Use the
existing Polars, fastexcel, httpx and Typer dependencies. Reference inputs are
small eager frames; production consumers can use the published Parquets lazily.

The four production originals are:

| Reference | Edition and registered relative path under `raw/references/` |
| --- | --- |
| [Census state/region/division workbook](https://www2.census.gov/programs-surveys/popest/geographies/2025/state-geocodes-v2025.xlsx) | Vintage 2025; `geography/2025/state-geocodes-v2025.xlsx` |
| [Census county Gazetteer](https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_counties_national.zip) | Vintage 2025; `geography/2025/2025_Gaz_counties_national.zip` |
| [Census OMB delineation workbook](https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx) | July 2023; `geography/2023/list1_2023.xlsx` |
| [HUD ZIP-county workbook](https://www.huduser.gov/portal/datasets/usps_crosswalk.html) | Existing 2025Q4 original; `hud/2025Q4/ZIP-COUNTY_122025.xlsx` |

The preflight records the exact bytes and SHA-256 values for the full-data
acceptance run. Fixture registries may supply small originals with explicit
fixture expectations; fixture outputs are never represented as production.
A deliberate change of production source edition or original bytes requires
a distinct source identity and recorded decision, not replacement of an
existing original or silent adoption of a newly fetched release.

Retain original bytes and record official source URL, SHA-256, size,
acquisition/import time, client and client version in the raw manifest.
Imports mark acquisition time as a proxy rather than inventing the source's
retrieval date. Cached originals in the personal geographic-codes skill may
be imported after source/hash verification. Its derived CSVs and directory
layout are not production inputs or runtime dependencies. The state workbook
was inspected in a temporary file; acquire it from its registered official
source or import verified original bytes, rather than depending on that file.

Check all registered destinations before acquisition starts. Refuse changed
or missing recorded originals, unrecorded existing destinations, conflicting
imports, symlinks and occupied partial files. Validate a new original before
publishing it and recording provenance. A fully cached acquisition performs
no HTTP requests. The build requires all four manifested inputs and never
downloads a missing reference.

Preserve Stage 3's `import_hud`, `read_hud` and `zip_candidates` interfaces
and verification artifacts. Reuse `read_hud` for its validated normalized
schema; extend production compatibility in the new geography boundary.
The HUD API is not required. This stage makes no Census geocoder requests.

## Geography frame and original parsing

The administrative frame is 2025, compatible with Stage 3's common ACS2025
county frame. OMB membership remains the July 2023 delineation. HUD remains
2025Q4. These are distinct reference identities; do not label all three as
one vintage or claim historical county geography for older filing addresses.

Read codes as strings and join by codes. State FIPS has two digits, county
GEOID has five, and CBSA code has five; region and division codes have one.
Official titles retain their wording and Unicode, with surrounding formatting
whitespace removed. Names are labels, never membership keys.

- Read the state workbook's `Region`, `Division`, `State (FIPS)` and `Name`
  header. Its region and division rows use state `00`; retain them to obtain
  official titles and division-to-region relationships. Identify exactly the
  50 states plus DC as administrative scope. Territory rows create no nodes.
- Read the sole county archive member `2025_Gaz_counties_national.txt` as
  pipe-delimited text. Derive state FIPS from GEOID and resolve it against the
  state reference. Derive `state_usps` from consistent Gazetteer FIPS/USPS pairs;
  require one abbreviation per state and one state per abbreviation. Every scoped Gazetteer
  county-equivalent is included, irrespective of HUD coverage or CBSA membership.
  Connecticut contains its nine planning regions, not the retired counties.
- Read the delineation workbook's explicit CBSA code/title/type, state/county
  FIPS and central/outlying county columns. Metadata and recognized footer rows
  are not memberships. Validate every data row before applying administrative
  scope. Accept only the explicit central/outlying membership roles. Include
  both official CBSA types; ignore metro-division and CSA
  relationships for this graph. Every scoped membership must resolve to the
  complete county frame, with no duplicate or contradictory county assignment.
- Read the HUD original through `read_hud`. Keep every normalized row, including
  excluded territory and recognized short zero-share noncounty records.
  Reference syntax errors, nonfinite/out-of-range ratios and duplicate
  ZIP/county pairs remain build failures. A syntactically valid HUD county code
  absent from the frame is retained with compatibility diagnostics.

Refuse ambiguous/missing headers, malformed data rows, duplicate reference
keys, missing titles, contradictory administrative relationships, unsupported
CBSA types and county-membership mismatches. A malformed data row is not a
footer merely because its code fails a pattern. No guessed padding, title-based
membership, legacy Connecticut recoding or majority allocation repairs a
reference defect.

## Typed graph contract

Publish `geography_nodes.parquet` with Stage 4's exact node schema:

| Column | Type | Geography meaning |
| --- | --- | --- |
| `node_id` | String | `geography:vintage:level:code` |
| `system` | String | `geography` |
| `vintage` | Int64 | 2025 for administrative nodes; 2023 for CBSA nodes |
| `level` | String | `region`, `division`, `state`, `county` or `cbsa` |
| `code` | String | Official code at that level; `county` includes county-equivalents |
| `title` | String | Official title |

Publish `geography_edges.parquet` with the exact schema
`child_id:String, parent_id:String, edge_type:String`, directed child to parent:

| `edge_type` | Required endpoints |
| --- | --- |
| `county_state` | 2025 county to its sole 2025 state |
| `state_division` | 2025 state to its sole 2025 division |
| `division_region` | 2025 division to its sole 2025 region |
| `county_cbsa` | 2025 county to its 2023 CBSA, when membership exists |

Regions and CBSAs have no parent. Do not add a national root, CBSA-to-state
edges, transitive administrative edges or invented memberships. Cross-state
CBSAs emerge from member counties with different administrative states. A
county has exactly one administrative parent and at most one CBSA membership;
both can coexist. Validate full namespaced node IDs, known endpoints, distinct
edges, allowed endpoint types/vintages, exact administrative parentage,
reference parity and absence of cycles. Node uniqueness includes `level`.

Do not call `classification_tables.forest`: its system/level, uniqueness,
same-vintage and single-parent rules are classification-specific. Geography
uses the shared schemas, not the classification forest contract. The graph
and county reference carry both paths; there is no additional paths output.
The root-through-node convention remains region/division/state/county for
the administrative path and CBSA/county for membership. Never concatenate
these branches into one asserted path.

## County and CBSA reference contracts

Publish `county_reference.parquet`, one row per scoped county GEOID. It is the
complete inventory and downstream rollup lookup, including counties outside
all CBSAs. Its exact schema is:

| Columns | Type and nullability |
| --- | --- |
| `county_id`, `county_geoid`, `county_title` | String, nonnull |
| `county_vintage` | Int64, nonnull; 2025 |
| `state_id`, `state_fips`, `state_usps`, `state_title` | String, nonnull |
| `division_id`, `division_code`, `division_title` | String, nonnull |
| `region_id`, `region_code`, `region_title` | String, nonnull |
| `cbsa_id`, `cbsa_code`, `cbsa_type`, `cbsa_role` | String, nullable together |
| `cbsa_vintage` | Int64, null without membership; otherwise 2023 |

`cbsa_type` is `metropolitan` or `micropolitan`; `cbsa_role` is `central` or
`outlying`, from the original. Outside all CBSAs, every CBSA field is null
and no `county_cbsa` edge exists. Administrative IDs/titles and nonnull CBSA
IDs must agree exactly with the graph and references. A failed membership
join must raise rather than produce a false non-CBSA county.

Publish `cbsa_reference.parquet`, one row per scoped CBSA code:
`cbsa_id:String, cbsa_code:String, cbsa_title:String, cbsa_type:String,
cbsa_vintage:Int64, n_counties:Int64, state_fips:List(String)`, all nonnull.
The vintage is 2023; `state_fips` is sorted/distinct and derived from all member
counties. Counts, type and state set must agree with `county_reference` and
the graph. A cross-state CBSA has more than one state in this list.

## HUD candidates and ZIP eligibility contracts

Publish `hud_zip_county.parquet`, preserving exactly the normalized `read_hud`
rows and values:
`zip_key:String, county_geoid:String, bus_ratio:Float64,
noncounty_geography:Boolean`. Add nonnull Boolean columns
`county_in_frame`, `flag_county_out_of_scope`, `flag_county_incompatible`
and `flag_county_legacy_ct`.

`county_in_frame` is membership in the full scoped county inventory.
Out-of-scope geography means the recognized excluded prefixes
`60`, `64`, `66`, `68`, `69`, `70`, `72`, `74`, `78`, including the existing
short noncounty exceptions. A county is incompatible when it is absent from
the frame and is neither excluded nor a recognized noncounty record.
Legacy `090*` Connecticut county codes retain a separate legacy flag as well
as incompatibility. No diagnostic removes a HUD row or changes its ratio.

Publish `hud_zip_lookup.parquet`, one row for every ZIP in the full HUD input:

| Columns | Type and contract |
| --- | --- |
| `zip_key` | String, nonnull, unique |
| `n_hud_rows`, `n_business_counties` | Int64, nonnull; all rows and positive-share rows respectively |
| `business_counties` | List(String), nonnull, sorted; empty for no positive share |
| `max_business_ratio` | Float64, null only with no positive share |
| `dominant_candidates` | List(String), nonnull, sorted; all positive candidates tied for the maximum, or empty |
| `zip_dominant_county` | String, nullable; only a unique maximum, diagnostic only |
| `zip_single_candidate` | String, nullable; only exactly one original positive candidate |
| `zip_fallback_county` | String, nullable; singleton only when in the scoped county frame |
| `eligibility_status` | String, nonnull; defined below |
| `flag_zip_zero_business`, `flag_zip_multiple_counties`, `flag_zip_has_out_of_scope`, `flag_zip_has_incompatible`, `flag_zip_legacy_ct` | Boolean, nonnull |

Count and aggregate **all** positive-share rows before any scope or
compatibility filtering. `business_counties` and maxima include excluded and
incompatible candidates. The three `has`/legacy diagnostics refer to those
positive candidates. Exactly one candidate means one original county, not one
survivor of filtering. A ZIP with two positive candidates remains ambiguous
even if one is excluded. Zero-share candidates do not establish eligibility.

The status is `zero_business` for zero positive candidates; `multiple_counties`
for two or more; for exactly one it is `out_of_scope`, `incompatible_county`
or `eligible` according to that candidate. Only `eligible` has a nonnull
`zip_fallback_county`. The independent flags preserve overlapping diagnostics.
Maxima and ties never choose a headline county from multiple candidates.

Every ZIP present in HUD has a lookup row, including all-zero ZIPs. A missing
ZIP is represented by no row; consumers must distinguish that absence from
`zero_business`. Empty candidate lists are empty, not null. Existing
`zip_candidates` can supply positive-candidate diagnostics, but cannot alone
provide the full ZIP inventory or complete frame eligibility.

Consumers retain Stage 3's method precedence and scope rules: an excluded
exact Census result remains flagged/unassigned and is not redirected to HUD;
a valid in-scope exact Census result can assign despite ambiguous/excluded
HUD. Delivered-state exclusion remains a separate veto. This bundle validates
HUD eligibility and supplies geography lookup; it does not execute or redefine
the Census/HUD method selector.

## Build, provenance and downstream use

Publish the six Parquets above beneath `derived/geography/<run_id>/` with
schema version `geography-v1`. Require an explicit safe run ID; refuse an
existing final directory or its `.part` directory. Write in staging and
publish only after validation and a final input/destination integrity check.
Do not add an implicit latest-run alias or mix files from separate runs.

Sort nodes by `node_id`, edges by child/parent/type, county/CBSA references by
their official codes, HUD candidates by ZIP/county and the ZIP lookup by ZIP.
List fields have deterministic order. The same inputs and transformation
versions must reproduce logical table content. Physical Parquet hashes are
recorded for each run without assuming byte identity across separate runs.

Include `inputs.json` with verified raw citations, exact source editions,
URLs, hashes and sizes, all registry/parser/transformation/CLI module versions
or hashes, package/Python/dependency versions and lockfile identity. Explicitly
record the 2025 administrative frame, July 2023 OMB membership and 2025Q4 HUD
quarter. Cite originals through hash-verifying `manifest.entry_for`, not the
lookup-only `recorded_entry_for`.

Include `report.json` with exact schemas, row counts, graph validation,
metro/micro and multi-state counts, non-CBSA county counts, HUD candidate/status
and diagnostic counts, and source-scope exclusions. Include detached
`outputs.json` hashing/sizing all six Parquets and the first two JSON files,
excluding itself. Recheck cited originals before final publication. A failed
build publishes no final bundle and reports a clear actionable error.

Stage 6 selects and verifies one complete bundle, then uses `county_reference`
and `hud_zip_lookup` for full establishment county assignment and area rollups.
The source establishment table, Stage 3 verification inputs and Stage 4 bundles
remain separate. Code tables are not rebuilt or required as input data for
this geography build; their shared schema convention is the dependency.
Later PUMA/geography consumers can use the same complete county inventory.

## Validation and acceptance

Tests run offline without credentials and use small genuine-layout reference
fixtures. Cover both CBSA types, multiple states sharing a CBSA, a non-CBSA
county, an independent-city/county-equivalent row, Connecticut planning
regions, territory exclusion, shared numeric codes at different levels,
malformed originals, missing endpoints, duplicate/contradictory parentage and
cycles. Verify graph/reference parity rather than testing counts alone.

HUD fixtures cover absent versus all-zero ZIPs, one valid positive candidate,
multiple candidates, maximum ties, an excluded singleton, an incompatible
singleton, legacy CT, recognized short zero-share noncounty rows, and mixed
valid/excluded positive candidates that must remain ambiguous. Test preservation
of rows/ratios and explicit eligibility nulls. Do not modify Stage 3's method
selector; its existing precedence tests remain in force.

Bundle tests cover missing/changed/unrecorded originals, conflicting imports,
occupied run/partial names, zero-network cached acquisition, offline-build
network refusal, immutable earlier outputs, inventories and logical repeatability.
Keep existing suites passing; relevant build/tests/checks must be freshly run
before completion is claimed.

For the inspected four production originals, full-data acceptance must verify:

- 51 states/DC, nine divisions, four regions and 3,144 county-equivalents,
  including exactly nine Connecticut planning regions and no retired CT counties.
- 925 CBSAs: 387 metropolitan and 538 micropolitan. County memberships are
  1,186 metro and 658 micro; 1,300 counties have no CBSA membership.
- 59 multi-state CBSAs; no missing member county and no duplicate membership.
- Derived graph totals of 4,133 nodes and 5,048 edges, with complete typed
  relationship/reference parity and no Puerto Rico or island-area nodes.
- All 54,571 normalized HUD rows and all 39,494 ZIPs retained, with zero
  unexpected in-scope county codes, no filtered-to-singleton assignment, and
  all scope/compatibility decisions reported.
- Every output has verified original/software provenance and detached hashes;
  a second named build has logically equal content and leaves the first intact.

Write a committed full-data finding identifying the selected bundle, source
hashes, exact schemas/counts, integrity checks, exclusions, uncertainty and
common-frame limits. A fixture pass or design preflight does not meet this gate.

## Rollout and completion

Next skill: writing-plans in a fresh session, scoped to this Stage 5 spec.
The plan header must carry the following line verbatim:

> Roadmap: specs/embedding-evaluation-data-spec-roadmap.md, Stage 5 — on plan completion, tick the stage and re-validate later stages against what shipped.

Plan completion requires the verified production bundle and finding, relevant
passing checks, review resolution, an actual-shipped `Handoff to later stages`,
and the normal plan/spec retirement protocol. The Handoff revalidates every
remaining Stage 6–13, naming exact bundle selection, schemas, typed edges,
metro/micro scope, HUD singleton/zero-share/compatibility contracts and limits
for consumers. Tick Stage 5 and stamp its implementing plan only after those
gates hold; reconcile later entries from that Handoff through derive-roadmap.
Any add/split/drop/reorder remains an owner decision. The source spec and
roadmap remain live.
