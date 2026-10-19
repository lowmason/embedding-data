# ACS codes and area allocation

**Status: COMPLETE (2026-10-19)** — implemented by [plan 8](../plans/completed/8-acs-codes-area-allocation.md); see the [measured finding](../findings/stage-8-acs-codes-area-allocation.md).

## Scope and approved decisions

Stage 8 of [the roadmap](../embedding-evaluation-data-spec-roadmap.md) implements
R3.9, R3.11's crosswalks, R5.1 (ACS), R5.3, R5.4 (ACS comparator), R6.3, V8 and
V11 (ACS) in [the source spec](../embedding-evaluation-data-spec.md). R3.10 supplies
the geographic-role keys. This is one mapping and reference-allocation cycle;
Stage 9 owns ACS target universes, pooling, estimation, replicate standard
errors and headline/sensitivity variants. Stage 13 owns comparator targets,
the size gate and complete eight-family V12 acceptance.

The owner approved the architecture on 2026-10-16:

- Publish separate, materialized companion Parquets for the three delivered
  ACS extracts, retaining every source column, row position and duplicate.
  Publish reusable code lookups and geographic factor tables separately.
- Keep raw strings beside parsed tokens, declared source schemes and canonical
  candidate sets. Classification possibilities have no allocation weights.
- Keep residence, workplace and migration roles distinct. Allocate geographic
  population with explicit numerators, denominators, vintages and provenance.
- Verify all three full extracts and an independent offline replay. Fixture
  readiness and design preflight are insufficient for stage completion.
- When official evidence does not identify an OCCSOC aggregation reason,
  record an explicit unknown reason and its provenance. This allowance does
  not relax source-supported candidate membership or the unparseable-code gate.
- Recognize ACS OCCSOC `559830` as the documented special value Military, Rank
  Not Specified. Preserve every such row and source value, with empty canonical
  candidates and no asserted canonical node. Count it separately from mapped
  codes and unparseable codes. This is the owner's narrow V11 clarification;
  it admits no other unknown or unsupported classification value.

The written design was owner-approved before implementation. Its production
reference snapshots, canonical companions, V8 and ACS V11 conclusions are now
measured in the finding linked above; this specification retains the original
architecture and its limits.

## Binding boundaries and selected inputs

Use the existing Polars, fastexcel, httpx and Typer stack. Production microdata
transforms are lazy Polars with method-style expressions; small public reference
tables may be eager. No personal skill directory is a runtime input. All IPUMS
microdata and companion Parquets remain local under ignored `data/`; only
aggregate findings and public-reference descriptions enter git. Mapping outputs
remain evaluation inputs and never become embedder training or model-selection
data.

The production data root is explicitly
`/Users/lowell/Projects/embedding-data/data`, including in a worktree. Consume
these selected inputs without rebuilding or editing them:

| Input | Selected identity and authority |
| --- | --- |
| Stage 4 classification bundle | `derived/codes/stage4_v11_20261013_r2/`; detached `outputs.json` SHA-256 `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`; [plan 4 Handoff](../plans/completed/4-code-tables-ita-naics-mapping.md#handoff-to-later-stages) |
| Stage 5 geography bundle | `derived/geography/stage5_geography_20261014/`; detached `outputs.json` SHA-256 `5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d`; [plan 5 Handoff](../plans/completed/5-geography-hierarchy-county-reference.md#handoff-to-later-stages) |
| Stage 7 verification | `derived/ipums/verification/stage7_ipums_verification_20261015_r2/`; detached `outputs.json` SHA-256 `db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc`; [measured finding](../findings/stage-7-ipums-extract-verification.md) |
| Stage 7 public references | `stage7_ipums_references_20261015_r2`, `ipums-public-references-v3`; receipt SHA-256 `3163968dde603ba53f807976dd09b9e40d73235a98c6f36e4e02c67ec4239c9c` |

The three ACS Parquets and their manifested raw CSV/DDI/definition triples are
identified by that Stage 7 selection and finding:

| Profile | Delivery | Rows | Original columns | Parquet SHA-256 |
| --- | --- | --- | --- | --- |
| `acs/core` | `usa_00001` | 3,206,859 | 147 | `c07f9e7abe2c5dfdb8f9488a1f574d4cf49ab7945c3ad2ffc9daec5eaba47d10` |
| `acs/five_year` | `usa_00003` | 7,456,212 | 148 | `c5846bde221e7785051a4a4075aa6a71cc267a1f4497168a96df05d7c50f78fe` |
| `acs/vintage` | `usa_00002` | 1,575,420 | 146 | `b6ffab7bd974f72b4fbc913f261779f5ce3145a915849bf92e946bb6b649240d` |

Verify the detached inventories, listed file sizes/hashes, schemas and applicable
raw-manifest citations before using them. Use
`ipums_verification_run.verify_bundle(..., expected_outputs_sha256=...)` for
the selected Stage 7 bundle. Its `measurement_status=unresolved` is expected;
the finding separately supplies the adopted source interpretations. Do not edit
that machine status or treat integrity verification as a new substantive finding.

Reuse Stage 4's canonical NAICS 2022/SOC 2018 nodes, native NAICS 2017/2022 nodes,
`code_paths` and complete NAICS relationships. `naics_relationships.candidates`
provides forward/reverse traversal; the ITA six-digit parser and source-defect
exception do not apply to ACS. Reuse Stage 5's complete county inventory and
typed county-to-CBSA membership, preserving metro/micro type and non-CBSA counties.
No geographic single-parent assumption or forced CBSA state parent is introduced.

Do not invoke extract submission, conversion recovery, upstream builders,
`osha`, `sample`, Census geocoding or a target build to prepare Stage 8.

## Public-reference boundary

Separate public acquisition/import from offline parsing, mapping and publication.
New originals live under `raw/references/acs-mapping/<reference_id>/` and enter
the append-only manifest. A versioned reference receipt records logical identity,
authority URL, edition, request parameters/body where applicable, exact returned
bytes, SHA-256, size, retrieval time, client/version and parser contract. Imports
preserve original bytes and mark local import time as a retrieval-time proxy.
Existing Stage 4/7 originals may be cited in place after verification; do not
duplicate or modify their frozen registries just to add Stage 8 references.

The required reference families are:

| Reference family | Primary source and use |
| --- | --- |
| IPUMS INDNAICS and IND-to-INDNAICS tables | [INDNAICS](https://usa.ipums.org/usa-action/variables/INDNAICS), [vintage code table and legend](https://usa.ipums.org/usa/volii/indnaics.shtml), and its linked IND crosswalk; exact source tokens, M/P/S/Z definitions and Census category correspondence |
| Census industry relationships and PUMS code lists | [Official lists and crosswalks](https://www.census.gov/topics/employment/industry-occupation/guidance/code-lists.html), including 2017/2022 industry originals already frozen in Stage 7 and PUMS-specific lists; code-to-code membership and published aggregation expressions |
| IPUMS OCCSOC and OCC-to-OCCSOC tables | [OCCSOC](https://usa.ipums.org/usa-action/variables/OCCSOC), [vintage code table](https://usa.ipums.org/usa/volii/occsoc18.shtml), [OCC crosswalk](https://usa.ipums.org/usa/volii/occtooccsoc18.shtml); SOC 2018 source categories, aggregation documentation and paired-code checks |
| Census occupation relationships and PUMS documentation | [Official lists](https://www.census.gov/topics/employment/industry-occupation/guidance/code-lists.html), 2018 occupation crosswalk and the relevant annual/five-year [PUMS documentation](https://www.census.gov/programs-surveys/acs/microdata/documentation.2024.html); supported SOC membership, representation and special values |
| Delivered-scheme and geographic applicability | IPUMS [IND](https://usa.ipums.org/usa-action/variables/IND), [MULTYEAR](https://usa.ipums.org/usa-action/variables/MULTYEAR), [PUMA](https://usa.ipums.org/usa-action/variables/PUMA), [PWPUMA00](https://usa.ipums.org/usa-action/variables/PWPUMA00), [MIGPUMA1](https://usa.ipums.org/usa-action/variables/MIGPUMA1), and corresponding state-variable documentation; role/year/special-code rules |
| Residence PUMA-to-county population | [Geocorr 2022](https://mcdc.missouri.edu/applications/geocorr2022.html), with [factor definitions](https://mcdc.missouri.edu/geography/PUMAs.html); 2020 PUMA intersections with compatible counties, weighted by 2020 Census population |
| Workplace/migration composition | [IPUMS 2020 POWPUMA definitions](https://usa.ipums.org/usa/volii/20pwpuma.shtml), including its PUMA and county composition workbooks; shared POW/MIG units and independent county-boundary checks |
| PUMA-to-MSA intersections | [IPUMS 2023 metropolitan-area page](https://usa.ipums.org/usa/volii/met2023.shtml), linked 2023-MSA/2020-PUMA workbook; all published intersections and their 2020 populations |

The implementation plan must inspect and pin the actual reference layouts before
writing parsers. A legend or title list alone does not prove candidate membership.
Require explicit code-to-code relations or documented aggregation expressions
resolved against official structure membership. Do not substitute title matching,
generic wildcard expansion or assumed marker meanings for missing evidence.
If the necessary membership evidence is absent, acquire stronger official evidence
or surface the specific gap; a guessed candidate table cannot meet V11.

Validate originals and the entire selected import/acquisition destination set.
Changed cached bytes, absent-but-recorded files, unrecorded occupied destinations,
symlinks, conflicting imports and occupied partials fail. Cached acquisition makes
zero HTTP calls. No offline command loads `.env`, requests credentials, instantiates
an IPUMS API client or retrieves missing references. Public browser downloads may
be imported under their registered identity when a server prevents direct access.

## Design preflight evidence and limits

The following exact public files were inspected on 2026-10-16 in temporary storage.
They are design evidence, not manifested production inputs. Production must acquire
or import and verify the selected originals under its own receipt; no build depends
on a temporary path.

| Original | SHA-256 | Observed layout |
| --- | --- | --- |
| [County-to-POW/MIG composition](https://usa.ipums.org/usa/resources/volii/county_migpuma_pwpuma_2022.xls) | `bd42f18ee36a10d91404be78106e60c613b6ec8ce53e9bc5860753af497ffadf` | 3,222 unique state/county keys; four columns; nine CT planning regions; 1,027 POW/MIG groups |
| [PUMA-to-POW/MIG composition](https://usa.ipums.org/usa/resources/volii/puma_migpuma1_pwpuma00_2020.xls) | `022e4784cb08dcf01acfa4f680564cd26ba79e867f6643ee683577fde0b37a5d` | 2,486 unique state/PUMA keys; four columns; the same 1,027 groups |
| [MSA/PUMA intersection workbook](https://usa.ipums.org/usa/resources/volii/MSA2023_PUMA2020_crosswalk.xlsx) | `80763eaf73cbda1b59818bdbf7650058eebbe18fa8a697599e645b3df235258f` | Eleven columns; source has both whole-MSA and whole-PUMA population denominators and two percentage columns |

The two composition workbooks use two-character residence state FIPS but
three-character native PWSTATE2/MIGPLAC1 state codes. Codes are strings; use the
published state correspondence rather than joining unequal representations or
treating foreign state/place codes as U.S. FIPS. Both workbooks include Puerto Rico;
R6.4 filtering is explicit and follows validation of the original relationships.

The current Geocorr form has SHA-256
`96ce8006b044529e8c23209e3d17de8921df2465dabaa3dd216c8367c0e94b40`.
Its `county` selector returned current Connecticut planning regions; `CTcounty`
separately names pre-2023 counties. Older 2023 blog instructions are insufficient
authority for the current interface. A successful Connecticut-only request used
source `puma22`, target `county`, weighting `pop20`, positive-population blocks,
CSV output and the second allocation factor. Its returned CSV SHA-256 is
`57a0937d0a8961efd61ecc1c382d3b34d6dfddca303169c610b8786ac0734e8e`.
It has a names row followed by a descriptive-label row, then records; the label
for `county` is Connecticut planning region. This slice proves neither nationwide
coverage nor production V8 acceptance.

Freeze Geocorr's form, complete request parameters, response page and resulting
CSV bytes together. The broker endpoint is `/cgi-bin/broker`, with `_PROGRAM`
`apps.geocorr2022.sas` and `_SERVICE` `MCDC_long`. Include the form's empty text
controls, including longitude/latitude: omitting them produced SAS macro errors
inside an HTTP 200 response during preflight. Validate application success and
returned data, not merely HTTP status. Generated CSV URLs are transient retrieval
locations; they are not stable reference identities. Freeze the geographic scope
and actual returned county namespace, and reject unexpected changes.

A targeted aggregate query over the three pinned source Parquets found OCCSOC
`559830` in 5,204 core, 14,799 five-year and 3,405 vintage rows. OCCSOC `999920`,
null OCCSOC, normalized INDNAICS `999920` and null INDNAICS each had zero rows in
that query. Census's [2024 PUMS guide, section VIII.I](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/2024ACS_PUMS_User_Guide.pdf)
identifies `559830` as a pseudo-code. These are a narrow design diagnostic and
the basis of the approved special-state rule, not a full V11 parsing measurement.

## Classification parsing and provenance

Select a delivered coding scheme from verified sample/product metadata, not
from whichever vintage makes a token match. Annual 2022 industry uses NAICS 2017;
annual 2023/2024 industry uses NAICS 2022; these ACS occupations use SOC 2018.
The delivered 2024 five-year product uses the release's 2022 industry scheme
across MULTYEAR components. Preserve MULTYEAR and the distinction between that
delivered scheme and the respondent's original interview-year coding. Do not
reconstruct a pre-recoding industry or call an earlier interview natively 2022.
Reference-backed source recoding provenance remains independent of any Stage 8
2017-to-2022 concordance flag.

`INDNAICS` and `OCCSOC` remain byte-for-byte logical strings in the original
column prefix. A separate token may remove documented ASCII padding; it must
not remove meaningful letters, suffix digits, leading zeros or arbitrary internal
characters. Validate paired IND/INDNAICS and OCC/OCCSOC correspondence under the
correct published product scheme. Paired Census-code normalization must follow
documented widths and retain the original typed source value in the companion.

Each code lookup records the scheme, normalized paired Census code and source
token as its unique key. Its contract includes:

| Fields | Contract |
| --- | --- |
| Native/canonical system and vintage | Explicit declared delivered scheme and canonical NAICS 2022 or SOC 2018; no vintage guessing |
| Mapping status | `mapped` or the approved `documented_special`; unknown/malformed/unsupported values prevent publication |
| Deepest native node; native finest candidates | Supported official node ID where one exists and sorted distinct finest-code possibilities |
| Canonical finest candidates; common node | Sorted distinct `List(String)` possibilities and their deepest common official ancestor, nullable if no common root; common ancestry never replaces candidates |
| Canonical scalar code/node | Only where an exact finest source category and supported one-to-one interpretation establish it; candidate cardinality alone is insufficient |
| Aggregation type/markers | Preserve the source category and every applicable M/P/S/Z marker, including combinations and discriminating suffixes; numeric mixed-depth codes are also explicit aggregates |
| OCCSOC aggregation reasons | Documented category-design/disclosure reason or reasons; explicit `unknown` status if per-code evidence is absent; nonaggregates are not applicable |
| Reference provenance | Reference IDs and original table/column/row or published rule locators sufficient to reconstruct every asserted relationship and reason |
| Transformation flags | Independent aggregate/partial/exception and vintage-crosswalk provenance; a singleton does not clear them |

Resolve a published coarse node through its official descendant relationships.
Resolve M/P/S/Z and X/Y categories through their documented constituent relations
or aggregation expressions, preserving exclusions and partial-category meaning.
Do not treat the full 2018 Census occupation list as interchangeable with the
PUMS list; public-use collapses require their explicit correspondence. SOC
parentage comes from the Stage 4 workbook-derived paths, including overflow
groups, rather than digit surgery.

Map every supported NAICS 2017 finest possibility through the complete official
2017-to-2022 relation and take the sorted union. Code equality does not bypass
the concordance. Preserve all possible canonical candidate paths separately;
give candidates no equal-share or other employment weights. Reference defects,
uncovered relation endpoints and contradictory paired-code mappings fail.

For OCCSOC `559830`, `mapping_status=documented_special`, native and canonical
candidate lists are empty, node/scalar/common-node fields are null, and a cited
special-value reason is required. It is never counted as a successful mapping.
All other nonmissing classification values must resolve under the strict parser;
the ITA unresolved-source exception is not inherited. A new purported special
value requires an explicit evidence-backed decision, not an automatic bypass.

Retain every delivered Q-prefixed flag and its original type/value. Source
allocation, source vintage recoding, Stage 8 concordance, source-assigned PUMA
vintage and Stage 8 geographic allocation remain distinct provenance dimensions.
Missing applicability is unavailable, never false. In particular, preserve Stage
7's source/product-specific QMIGRAT1 types, all-null 2023 core values and absence
from the vintage extract; five-year flags do not backfill annual records.

## Geography allocation contracts

Keep these role-specific source pairs in every companion: residence
`STATEFIP/PUMA`, workplace `PWSTATE2/PWPUMA00`, migration
`MIGPLAC1/MIGPUMA1`. Their raw columns remain untouched. Reference lookups normalize
only with documented state/area representations. Pair every area code with its
state and vintage; a five-digit PUMA code is not a national key.

For the delivered annual 2022/2023/2024 and 2024 five-year products, use the
documented 2020 PUMA/POW/MIG definitions. Earlier five-year interview components
whose geography Census assigned into the newer frame retain source-allocation
provenance. This does not validate Census's undocumented assignment method.
Do not import the mixed-vintage rule of the different 2018–2022 five-year product.

### Residence population factors

Acquire the complete scoped Geocorr intersection table for 2020 PUMAs and
counties, with 2020 Census population. Validate all keys, nonnegative integer
populations, unique source/target pairs and complete PUMA/county references.
For PUMA p and county c, publish the intersection population n(p,c), whole-PUMA
denominator N(p), and factor n(p,c)/N(p). Retain the original published factors
as diagnostics and check their documented rounding against these counts; use
integer counts as the authoritative arithmetic. Do not round factors for storage
or repair a missing intersection by renormalizing the remainder.

Each supported in-scope PUMA has positive N(p) and complete population closure.
A zero-population denominator has no allocatable factor and is an explicit
reference error if a selected record requires it. Any zero-population reference
intersection retained by the selected source remains distinguishable from an
absent relationship. Validate all source rows before applying U.S. scope.

### Workplace/migration factors and V8

Use both IPUMS composition originals. A resident PUMA must have one POW/MIG
group; a county must have one group if the documented whole-county rule holds.
V8 tests the county-to-group direction. A group may contain several whole counties;
it does not therefore identify one county.

Join the full residence-PUMA/county intersection populations to the PUMA-to-group
composition. For group g and county c, sum n(p,c) over every resident PUMA p in g.
Divide that sum by the total population across all resident PUMAs in g. This is
the common POW/MIG-to-county population factor. Never average the constituent
PUMA allocation factors without their population denominators. Check that the
resulting county memberships agree with the independent county composition and
that every group denominator and county population reconciles.

The V8 finding must record full-source checks, scope counts and any county split.
If the sources contradict the whole-county rule, preserve the evidence and refuse
the union-only derivation for affected units. Obtain an official population
intersection reference for the split before completing factors or adopting V8;
never fabricate weights or make majority assignments. Amend R6.3's open marker
only after the measured finding supports the adopted rule.

### MSA intersections and residual population

Preserve all IPUMS 2023-MSA/2020-PUMA intersections, with whole-MSA, whole-PUMA
and intersection 2020 population. The published percentage columns are on a
0–100 scale and have different denominators. For PUMA-to-MSA allocation use
intersection population divided by whole-PUMA population. Retain the reverse
MSA-conditioned fraction separately and label it accordingly.

MSA fractions within a PUMA may sum to less than one. Publish the non-MSA
population residual against the whole PUMA, including PUMAs absent from the MSA
intersection file. Do not rescale the listed MSA intersections to sum to one.
Check intersection-population closure for every MSA and reconcile PUMA totals
with the residence population reference. Rounding discrepancies in published
percentages have explicit bounds; integer population disagreement fails.

MSA references include metropolitan areas only. Non-MSA residual does not mean
no CBSA: micropolitan counties remain in Stage 5's typed county relationships.
Keep direct PUMA/MSA factors distinguishable from county-to-CBSA rollups; do not
assert independent allocations are observed individual locations or combine them
as independent probabilities. MET2023/PWMET23/MIGMET23 stay source diagnostics
and never substitute for the required population intersections.

### Scope, statuses and flags

Every source record gets an explicit lookup outcome for each role. Defined,
applicable in-scope geographic keys must have complete compatible county factors
summing to one. An unexpected missing key, incompatible in-scope county, invalid
state/area pairing or unexplained null is a failure, not a silent exclusion.

Recognized not-in-universe/unidentifiable and foreign/territory values have cited
statuses and separate counts. In particular, PWPUMA00 `00000`/`00001` and
MIGPUMA1 `00000`/`00001`/`00002` must be interpreted with their own role/state
documentation. Do not invent domestic counties for them, put them into factor
closure denominators, or convert unavailable values into no-migration or zero
flows. Work-from-home is preserved for Stage 9's workplace-mix eligibility rule.

Keep population year 2020, PUMA definition 2020, county-composition frame 2022,
Stage 5 administrative inventory 2025 and MSA delineation July 2023 separate.
Require compatible county identifiers, including all nine CT planning regions;
never relabel legacy CT counties. Identifier compatibility does not establish
historically identical boundaries or individual-location accuracy.

Every use of a factor retains geographic-allocation provenance even if its factor
is one; separately identify actual fractional splits. Source-assigned geography
and missing source-allocation evidence retain their own flags. This stage supplies
mapping status and provenance; Stage 9 decides family-specific eligibility.

## Output bundle and row preservation

Publish immutable `acs-mapping-v1` runs under `derived/acs/mapping/<run_id>/`.
The implementation plan freezes exact typed schemas consistent with these
contracts before implementing writers. The required public tables are:

| Table | Grain and required content |
| --- | --- |
| `acs_code_lookup.parquet` | One row per system/scheme/paired-Census-code/source-token key; the complete classification contract above, with nonnull sorted distinct candidate/reason/reference lists |
| `acs_area_lookup.parquet` | One row per observed profile/sample/component/role/state/area interpretation; normalized area identity, documented status, reference citations and source-assigned-geography provenance |
| `puma_county_factors.parquet` | One row per area type (`residence` or shared `work_migration`), state, area code and county; 2020 population numerator/denominator, Float64 factor, frame identities, county node and provenance |
| `puma_msa_factors.parquet` | One row per state/PUMA/MSA intersection; integer population quantities, both conditioned fractions, MSA node and distinct frame/provenance fields |
| `puma_msa_coverage.parquet` | One row per scoped residence PUMA, including those without MSA rows; whole population, MSA population and non-MSA residual |
| `acs_core_canonical.parquet` | All core source rows and columns in original order, followed by identity and code/geographic annotations |
| `acs_five_year_canonical.parquet` | All five-year source rows and columns, with MULTYEAR retained, followed by annotations |
| `acs_vintage_canonical.parquet` | All vintage source rows and columns, followed by annotations; absent original flags remain absent |

Each companion row has `source_parquet_sha256:String` and zero-based
`source_row:UInt64` as its identity. Preserve the ordered original schema as a
prefix, all original values/types, and duplicate multiplicity. Mapping fields
include raw-to-token interpretation, native/canonical codes and candidates,
aggregation/special/reason statuses and independent provenance flags. Geographic
annotations identify all three role lookups, statuses and source-vintage flags.
Use stable natural lookup keys or deterministic lookup IDs with checked uniqueness.
No mapping join may expand, drop or reorder person rows. Do not materialize a
cross-product of candidate industries, occupations or geographic roles.

Reference tables sort by their complete natural keys with explicit null ordering;
companions retain source order. Table schemas use String identifiers, Int64
vintages/population counts, Float64 derived factors, Boolean or explicitly nullable
Boolean flags, and typed nonnull lists. Missing, unknown and not-applicable states
remain distinct. Numeric arithmetic must not turn missing evidence into zero.

The bundle also contains `inputs.json`, `report.json` and `outputs.json`.
The report includes source row/partition counts; code status, aggregation,
candidate-cardinality and reason counts; `559830` counts; role applicability,
scope/coverage and allocation diagnostics; factor conservation; MSA residuals;
V8 checks and explicit limits. All partitions reconcile to source totals.

`inputs.json` freezes selected upstream detached pins, source/raw/reference hashes
and sizes, schemas, scheme/rule/transform versions, relevant executing module
hashes including its CLI, dependency versions, Python and lock hash. Git commit
identity is informational alongside actual file hashes. `outputs.json` hashes and
sizes every published table plus inputs/report, excluding itself. Record its
detached checksum outside the inventory; a verifier never trusts a checksum
recomputed solely from the bundle it is asked to trust.

## Command and publication boundary

Expose a separate `python -m embedding_data.acs_mapping` command group with
`acquire-references`, `import-reference`, `build`, `verify` and `compare-runs`,
explicit reference/run IDs and `--data-dir`. Build selects codes/geography/IPUMS
bundles and detached pins explicitly; the recorded selected pins above may be
named defaults, but alternate selections require independent pins and complete
compatibility checks. No latest-run alias or mixed-run fallback is allowed.

Use new Stage 8 modules for acquisition/strict reference parsing, code mapping,
geographic factors, companion annotation and bundle orchestration/verification.
Keep the existing extract commands intact. Stage 7's frozen software inventory
includes `cli.py`, `paths.py`, the extraction/conversion modules and several shared
helpers. Adding this module command avoids invalidating that inventory through
top-level registration. Do not weaken existing verifiers, rewrite historical
inventories or silently remeasure an upstream stage to accommodate new software.
If an indispensable shared dependency change is discovered, surface that deviation
and its fresh-upstream-verification requirement before proceeding.

Acquisition/import alone can contact public reference sources. Build, verify and
comparison are offline. A cached acquisition verifies and returns without HTTP.
Never retry an application-error page as if it were a valid empty crosswalk.

Reserve an exclusive caller-owned staging directory. Refuse occupied final or
partial names and unsafe/symlinked paths. Validate inputs before writing; write
and reread outputs; verify schema, values, coverage, references and inventories;
recheck all protected input/software hashes; then publish without replacement.
A failure leaves no final bundle and touches no earlier run. Own and clean only
the temporary files created by the failed operation. Inspect occupied/incomplete
runs and choose a fresh ID rather than overwriting or deleting evidence.

Expose a public verifier taking a separately supplied output-inventory checksum
and checking source/reference integrity plus the frozen software/dependency
contract. A second named build must yield exactly equal ordered logical tables
and equal substantive report content. Run IDs/timestamps may differ only in
explicit provenance fields; fresh physical Parquet hashes need not be equal.
Comparison establishes logical repeatability, separately from detached trust.

## Verification and measured acceptance

Follow red → green for pipeline/library behavior. The writing-plans session
chooses task boundaries and concrete tests, preserving these observable gates:

1. **Original parsing and membership:** genuine-layout public fixtures cover
   padded strings, numeric coarse nodes, every M/P/S/Z marker and combinations,
   suffix distinctions, X/Y aggregates, both documented reasons and unknown
   reason, the exact `559830` special, paired-code mismatch and malformed codes.
   Use source-backed expected memberships and official parentage. Missing or
   contradictory references and other purported specials fail.
2. **Vintage/provenance:** fixtures cover annual 2017/2022 industry, five-year
   release scheme versus MULTYEAR origin, full one-to-many/many-to-many candidate
   traversal, unchanged code strings whose content changed, singleton crosswalks,
   partial categories, and unavailable allocation flags. Flags do not clear just
   because candidate sets collapse or geographic factors equal one.
3. **Geographic arithmetic:** hand-calculated intersections cover a multi-county
   PUMA, several unequal-population PUMAs within one POW/MIG group, CT planning
   regions, native state-code representations, foreign/NIU/territory statuses,
   MSA partial overlap, a wholly non-MSA PUMA, and metropolitan/micropolitan
   distinctions. Check integer numerators and denominators exactly and derived
   factor closure within `1e-12`. Report source-percentage rounding independently.
   Missing intersections cannot pass by renormalization. A split-county fixture
   must reject the union-only POW/MIG derivation.
4. **Offline integration and failures:** fixture raw ACS CSV/DDI/definitions pass
   through the existing converter and Stage 8 mapping/allocation into all three
   companions and inventories. Check exact ordered original-column fidelity,
   duplicate preservation, source-row identity, status/flag accounting, detached
   verification, tampering, incomplete/occupied paths and repeatability. Disable
   network and credential access. This is Stage 8's contribution to the V12
   chain; target-family and complete V12 closure remain later stages.
5. **Production acceptance:** select and verify all actual inputs; acquire/import
   the complete public references; build all 12,238,491 source rows into the three
   companions; verify every observed classification/role key. V11 has zero
   unparseable codes, all true classifications have supported mappings and the
   approved special rows remain explicitly unmapped. Unknown aggregation-reason
   counts are published rather than invented. Every valid applicable scoped
   area has complete factors summing to one. Measure the full V8 reference checks,
   county compatibility, MSA closure/residuals, preserved source flags and every
   disjoint special/scope partition.
6. **Independent reconciliation and preservation:** perform a second offline
   named build and ordered logical comparison. Independently reconcile code
   frequencies and geographic populations/status counts, rather than relying
   only on the writer's own checks. Reverify selected upstream bundles and the
   source Parquet/raw hashes, preserve the earlier manifest as an exact prefix,
   account for every appended reference record and run the whole-tree raw audit.
   Run the applicable repository pytest, Behave, Ruff and lock checks and resolve
   review findings before stage completion.

Commit the actual measured finding to
`specs/findings/stage-8-acs-codes-area-allocation.md`. It records selected run and
replay IDs, exact schemas, raw/reference/software/output inventories, detached
checksums, independently reconciled counts, V8 evidence and scoped V11 closure.
Distinguish software completion from production data acceptance. Coverage and
population conservation do not establish individual geography accuracy, faithful
employment composition within a PUMA, undocumented source allocation quality or
target representativeness.

## Rollout and later-stage handoff

The implementation is complete under the retired plan linked above. Its
`Handoff to later stages` records the shipped APIs, selected pins and refusals;
the roadmap now marks Stage 8 complete. The source spec and roadmap remain live.

The completed Handoff revalidates every Stage 9–13:

- Stage 9 consumes the selected companions, exact mapping/role/factor APIs and
  independent ambiguity, special, source-imputation and allocation provenance;
  it owns membership, eligibility, estimates, uncertainty and family V12 paths.
- Stage 10 retains its ITA inputs and behavior; identify any actual shared API
  effect rather than assuming an ACS change authorizes an upstream rebuild.
- Stage 11 retains its CPS parser/linkage responsibilities and deferred 2026
  `9890` question; the ACS `559830` rule supplies no CPS special-code authority.
- Stage 12 consumes ACS work through Stage 9's later helpers and CPS work
  through Stage 11; Stage 8 alone supplies no worker-profile estimator.
- Stage 13 consumes the vintage comparator's complete flagged candidates and
  selected inventories while retaining comparator-target, citation, size-gate
  and complete V12 responsibilities.

The roadmap marks only Stage 8 complete. Reconcile later entries against the
actual Handoff through derive-roadmap at resume; no later stage is implemented
or marked complete by this stage. Any add/split/drop/reorder remains an owner
decision. The source spec and roadmap remain live.
