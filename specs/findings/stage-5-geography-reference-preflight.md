# Stage 5 geography reference preflight

Measured 2026-10-13 during Stage 5 design, before implementation. The owner
selected both metropolitan and micropolitan CBSAs; the roadmap exit now
distinguishes their types and gives counties outside all CBSAs no membership
edge. Stage 5 remains incomplete.

## Original inputs

Only original reference bytes were inspected. The county archive and CBSA
workbook are available in the personal geographic-codes source cache; both
hashes match its manifest. They are possible import sources, not production
dependencies on that skill. The state workbook was downloaded from Census
to a temporary file for inspection. These three inputs have not yet been
imported into this repository's raw manifest. The HUD workbook is already
manifested, and its current hash and size were verified through `entry_for`.

| Original | Official source | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `state-geocodes-v2025.xlsx` | [Census 2025 state, region and division codes](https://www2.census.gov/programs-surveys/popest/geographies/2025/state-geocodes-v2025.xlsx) | 14,700 | `327c7fa3dfeb6526b20cd3d1cef7f471ec08316e92b183f12c5b168bfed7da84` |
| `2025_Gaz_counties_national.zip` | [Census 2025 county Gazetteer](https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_counties_national.zip) | 138,993 | `4c90d0f805779923b5958ab13d0c1e9b99fe4932b786bfcf75dd739bb2dcb4ea` |
| `list1_2023.xlsx` | [Census July 2023 OMB delineations](https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx) | 143,798 | `952c4b1e78acbb54e6ec9412434b7602fedacbf021736351a63c181bdb753629` |
| `ZIP-COUNTY_122025.xlsx` | [HUD ZIP-county crosswalk catalog](https://www.huduser.gov/portal/datasets/usps_crosswalk.html), repository `data/raw/references/hud/2025Q4/` | 2,462,769 | `554379b618f21380bed6777a9c69845ac138843c1a57f951886d605bc9611c68` |

## Measured scope and compatibility

Read-only probes used the repository's Python environment, Polars,
fastexcel, ZipFile, and existing `ita_references.read_hud`. The administrative
scope is the 50 states plus DC. County GEOIDs are strings; membership GEOIDs
concatenate the delineation workbook's two-digit state and three-digit county
codes. The controller independently verified scope totals, unique county
assignments, county-membership coverage, HUD compatibility and input hashes.

| Measure | Result |
| --- | ---: |
| States/DC, divisions, regions | 51, 9, 4 |
| Scoped county-equivalents | 3,144 |
| Connecticut county-equivalents | 9 planning regions |
| Metropolitan CBSAs / member counties | 387 / 1,186 |
| Micropolitan CBSAs / member counties | 538 / 658 |
| All scoped CBSAs / member counties | 925 / 1,844 |
| Counties outside all CBSAs | 1,300 |
| CBSAs spanning multiple states | 59 |
| CBSA membership GEOIDs absent from the scoped county frame | 0 |
| HUD rows / distinct ZIPs | 54,571 / 39,494 |
| In-scope HUD county codes absent from the county frame | 0 |

The complete Gazetteer has 3,222 distinct GEOIDs, including 78 Puerto Rico
municipios. The complete delineation workbook has 935 CBSAs; exclusion of
Puerto Rico removes ten CBSAs and 71 county memberships. There are no
duplicate scoped county-to-CBSA assignments. Both metro and micro membership
must be kept; counties without either membership remain in the county table.

All 3,144 scoped county codes occur in HUD, but only 3,141 occur with positive
business share. A positive-share-only county inventory would omit valid
counties. The full HUD input also retains excluded territory rows and eight
recognized short, zero-share noncounty rows. Compatibility and scope must be
separate diagnostics; those rows never create hierarchy nodes.

## Parser and design implications

- The state workbook's header is Excel row 4: `Region`, `Division`,
  `State (FIPS)`, `Name`. Region and division rows use state code `00`,
  so preserve those rows when deriving official region/division titles.
- The county ZIP has one member, `2025_Gaz_counties_national.txt`, with
  pipe-delimited columns. The full county inventory comes from this original,
  not from HUD candidates or Stage 3's sampled geocodes.
- The CBSA workbook's header is Excel row 3. Metadata and trailing note rows
  are not memberships. Preserve the explicit metro/micro type. Metro-division
  and CSA columns do not create additional county-to-CBSA rows under this scope.
- Multi-state membership comes from county/state rows, not title suffixes.
  No CBSA is assigned a single administrative-state parent.
- The shared node ID includes `level`. Region/division codes overlap even
  though no scoped county-GEOID/CBSA-code collision occurs in these originals.
  `classification_tables.forest` remains unsuitable: its system and level
  checks and single-parent assumptions are classification-specific.
- Preserve all HUD ZIPs when building the production lookup so zero-business
  coverage remains distinguishable from an absent ZIP. Existing
  `zip_candidates` contains only ZIPs with positive business share.

These checks establish compatibility between the inspected 2025 county
inventory, 2023 delineations and 2025Q4 HUD reference. They do not establish
historical county geography or identical results from future Census address
service calls. Stage 3's common ACS2025 frame and cached exact-match-first
method remain adopted; Stage 6 performs full establishment assignment.

## Next checkpoint

The owner approved the design on 2026-10-13; the
[stage spec](../geography-hierarchy-county-reference.md) records its contracts.
Next is an implementation plan in a fresh writing-plans session.
The implementation must manifest original inputs, validate and publish the
production graph/reference bundle, test the stage exits, and record an actual
shipped Handoff before the stage is ticked and later entries are reconciled.
