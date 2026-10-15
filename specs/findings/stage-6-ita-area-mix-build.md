# Measured Stage 6 ITA assignment and 2023 area-mix build

Measured 2026-10-15. Stage 6 is complete on `codex/stage6-ita-area-mix`.
The selected full-data preparation, fresh Census acquisition, offline target build
and cached replay passed production data acceptance with **PASS-WITH-WARNINGS**.
Both public bundle verifiers, fresh repository checks, normal commit hooks and
independent task/whole-branch reviews passed. Plan/spec retirement and the Stage 6
roadmap stamp are recorded below; repository integration remains a separate choice.

The all-year assignment preserves all **3,206,055 submitted 2016–2025 records**.
The 2023 target has **126,958 observed county/industry cells**, supported by
**324,191 eligible submitted records**, covering **3,065 counties and 978 native
NAICS 2022 industries**. The denominator sidecar has **3,069 counties**: four have
assigned records but zero eligible records and therefore no target cells.
The counting unit is a submitted establishment-year record, including duplicate
multiplicity; it is not a confirmed unique establishment or an employment-weighted
population estimate.

## Selected immutable inputs and executions

Every data path below is relative to the explicit production root
`/Users/lowell/Projects/embedding-data/data`. Raw requests, responses and assignment
rows remain in this ignored local tree; this finding contains aggregates and
inventories, not addresses. Required run IDs are explicit, with no latest-run alias.

| Selection | Run or path | Detached outputs SHA-256 |
| --- | --- | --- |
| Stage 4 codes | `stage4_v11_20261013_r2` | `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |
| Stage 5 geography | `stage5_geography_20261014` | `5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d` |
| D5 preparation | `stage6_ita_assignment_20261014_1000_csv` | `84b29be17bae26e4cd7bb372108f95641936be4b73b794667957ed39de990d48` |
| First target | `stage6_ita_area_mix_20261014_1000_csv` | `084292b6835eb09ce27ecc4a3aef03a6f43bfe7b39b815665c29190a431e2473` |
| Cached replay | `stage6_ita_area_mix_20261014_1000_csv_replay` | `78fd21e37ba0c5b1cd396ff0961b557650788fdccd3c84a911e8c6c3b7fabe71` |

Preparation lives under `derived/osha/assignment-inputs/<assignment_run_id>/`;
target bundles live under `derived/targets/<target_run_id>/`. The source summary is
`derived/osha/ita_300a_summary.parquet`, 139,930,636 bytes, SHA-256
`6335cda7adb40a41c4a11d57d22048999449ac8d078a2ec0291f0198cd9136a8`.
The selected 38-column canonical table is
`derived/codes/stage4_v11_20261013_r2/ita_300a_canonical.parquet`, 156,025,783 bytes,
SHA-256 `2c64e783c8874cbe78809c0629a08faa7a0bf965d7680279350a64928a1f32ab`.
Both contain 3,206,055 rows; original source-column values and row order were
checked against the canonical table through the selected-input contract, and published assignments retain the exact
canonical prefix. Their physical serializations are separate inventories.

Preparation and both target executions record commit
`301ee6296070df4c7143413c2e2a7da24a5a5da1`. Both target executions record
`dirty=false`; their creation times are
`2026-10-15T10:18:47.961823+00:00` and
`2026-10-15T10:23:54.133280+00:00`. Both build commands exited 0.

The first target's immutable `inputs.json` (SHA-256
`71c03252f5b08c471a8aabc1ffe8596670a1a112448153ce6b30a2f80fc9f0fd`)
contains complete selected original citations, upstream bundle inventories,
source/canonical schemas, preparation inputs and outputs, acquisition evidence,
software hashes, versions, rules and execution metadata. Its `raw` inventory has
2,262 cited files; acquisition alone cites 2,233 files. The whole-tree audit
returned exactly `0 raw provenance discrepancies` with exit 0.

## Preparation, transport diagnosis and frozen preservation

The new preparation measured **1,113,538 distinct submitted tuples** and **1,114
request batches**: 1,113 batches of 1,000 records and a final batch of 538. This
matches the original design estimate; it is measured frozen workload, not a total
HTTP-call count. Source-index mappings cover all source rows, including incomplete
and delivered-excluded requests. Request-index `n_source_rows` sums to 3,206,055.

Two earlier preparations remain frozen:

- `stage6_ita_assignment_20261014`: original 10,000-record operational batches,
  112 request batches (111 full plus 3,538), detached outputs SHA-256
  `9052b183dbfbcc61e99e8d618cbc938b4257e397b717aa72d39ed12b10c7c95b`;
  115 inventory entries / 116 total preparation files.
- `stage6_ita_assignment_20261014_1000`: D4's owner-approved operational default
  amendment to 1,000, detached outputs SHA-256
  `e3a33f2bbb2a0b73586cf4ab308078cbb42b38179822148e998f6de1bc7f3145`;
  1,117 inventory entries / 1,118 preparation files, with all 283 completed old
  response/receipt pairs and raw controls preserved.

The instrumented original 10,000-record first-batch attempt observed a peer
connection reset before HTTP response headers at **305.749 seconds**. The client
was configured for 600 seconds; the trace did not identify the responsible remote
or intermediary component and did not establish a 600-second client timeout,
undocumented service cap or service outage. Smaller diagnostic requests succeeded,
but those responses were never production evidence.

The D4 preparation reached 283 completed batches before repeated HTTP 500s at
zero-based `batch_00283.csv`. Controlled bisection found one original record
sufficient to reproduce the error; it did not prove that this was the only
problematic record. A backslash adjacent to a quote isolated a wire-encoding
interaction. Value-preserving `escapechar='\\'` with `doublequote=True` passed
single-record and full-1,000 controls. These were diagnostic controls, not imported
raw receipts or completed production batches. The bounded official-document review
used the [Census API documentation](https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html)
and [May 2026 guide](https://www2.census.gov/geo/pdfs/maps-data/data/Census_Geocoder_User_Guide.pdf):
the published record bound was 10,000, but those reviewed passages supplied no
embedded-quote/backslash grammar or approximately 300-second transport rule.
Observed failures, rather than an invented documented parser rule, motivated D5.

D5 changed only the frozen `ita_assignment_prepare` module relative to each old
preparation; other implementation keys, dependencies, Python and lock contract
remained equal. Stage 3, request identity, original strings/punctuation, sequential
client behavior, timeout and Census options were retained. The new CSVs double
**42 literal backslashes in 29 of 1,114 files**; the remaining **1,085 files are
byte-identical** to D4. For every batch the new bytes equal the old bytes with
backslashes doubled, with exactly 42 added bytes overall. The old default CSV
reader and the new escape-aware strict reader produce exactly equal ordered
five-string tuples (ID, street, city, state, ZIP). Both source and request indexes
have exact schema/count/ordered-row equality across all three preparations.

The complete comparison is `/private/tmp/embedding-data-stage6-csv-prepared.json`,
SHA-256 `318ed6bf3552c3b7f77ae48505bf9b74918913eb84887c0187d6d7e16d02c19e`.
It preserves the complete per-run inventories and physical index checksums.
The common ordered logical index hashes are:

| Index | Rows | Ordered logical SHA-256 |
| --- | --- | --- |
| source_index.parquet | 3,206,055 | `73a9dc7b75f337294476014b7db5ac897a2946385d5cdcf626aa037b253a0847` |
| request_index.parquet | 1,113,538 | `17d1cd24a5bf112758d4e5fe1f8f164f59f20c2416fe33aea6caeec842dc91c0` |

Those logical hashes accompany exact comparisons under frozen Polars 2.0.0;
they do not assert identical physical Parquet bytes across preparations or future
library versions. The new preparation's principal inventory records are:

| File | Bytes | SHA-256 |
| --- | --- | --- |
| inputs.json | 226,669 | `be6e9fd28bd57756ad8d2fca999faeb7dd911a8d1d0b400d0feb891e92d3978f` |
| source_index.parquet | 111,238,847 | `87bccbc950b3caf69a21ba8236f9a46aeeacbf022215f2c8426b8bc5103ecd3f` |
| request_index.parquet | 57,088,451 | `baa1b2530c4093e4796a08a216f53e0aca446b36e44fc34b168c4472a2e5c3cf` |

Its pinned `outputs.json` inventories 1,114 CSVs and these three files (1,117
entries); `inputs.json` additionally records ordered batch rows/paths/hashes,
selected inputs, software and entry-point hashes. No source summary, old
preparation, prior bundle or verification run was rebuilt or overwritten. Old
and diagnostic responses were not imported into the new namespace.

## Completed fresh acquisition

The new raw root is
`raw/references/census-geocoder/ita-assignment/stage6_ita_assignment_20261014_1000_csv/`.
Acquisition remained sequential through the original client and its 600-second
timeout, using POST `/geocoder/geographies/addressbatch`. Frozen options were
benchmark **4 / Public_AR_Current** and vintage **425 / ACS2025_Current**.
Acquisition began **2026-10-15T02:55:28+00:00** and completed
**2026-10-15T10:14:31+00:00**. Response acquisition timestamps span
**02:55:49 through 10:13:41 UTC** on that date.

The execution ledger records 18 explicit CLI invocations: 17 stopped (12 traced
peer resets before headers around 300 seconds and five HTTP 502 responses), then
the final invocation completed. Each stop was followed by explicit inspection of
the frozen preparation, full cached evidence, completed prefix and protected
bytes before an authorized resume. Each failed batch passed unchanged on its next
invocation. No blind retry loop, altered frozen request, changed transport setting,
alternate Census option or inferred rate/connection cap was introduced. These
invocation/error counts are operational observations, distinct from the 1,114
completed request/response/receipt batches. They do not establish the responsible
remote component.

The new production response for formerly failing `batch_00283.csv` was acquired
at **2026-10-15T04:50:31+00:00**, bound to new request-file SHA-256
`83dfb6dc26c6c1888453bcb3b5801281421ed2f052154b7c72725b5b75b14637`.
All 1,114 batches completed in this fresh namespace.

Control-file inventories below are relative to that raw root. Retrieval timestamps,
source identities, request/response/receipt hashes and options are frozen evidence:

| Control | Bytes | SHA-256 |
| --- | --- | --- |
| benchmarks.json | 547 | `d3434b3cfc79fbc6b33f8452e719dffba1416b44a3817b3dfb721067416242ce` |
| vintages.json | 2,057 | `4b4235e3efd7142d2aa1564584619cb7cbf8712b1142aaa8661283fac895856d` |
| catalog-selection.json | 1,541 | `73d90d23348ba59c81034b0487456058f1e8da9105e4441a9f089494eb7d5e18` |
| acquisition-start.json | 273 | `b3faea752a6a57ffb978ab5502185210af22f233b257904fb058807a20a5eda8` |
| acquisition.json | 1,533,923 | `1db86adb180898c6af0a37ced1a6f41410b3de6cab787c246b4fa1818ded23dc` |

The pinned **`acquisition.json`** is the complete immutable evidence inventory:
1,114 request records, 1,114 response citations, 1,114 receipt citations, catalog,
selection and start citations, options, methods and acquisition time range.
Requests themselves live in the pinned preparation; immutable response and receipt
filenames are `<request-file-sha256>.csv` and `<request-file-sha256>.receipt.json`.
Each receipt binds the selected preparation/request, original response and frozen
selection. The target `inputs.json` embeds these inventories and cites the completion
file. This is the full inventory reference rather than a truncated listing of 1,114
rows. No `.part` artifact is cited as a completed delivery.

Census Current catalogs identify options; they do not freeze the service address
ranges across requests or resumes. Cached replay below proves deterministic reuse
of verified bytes, not equality of future live Census results.

## All-year row accounting and assignment coverage

Exact `source_row` identity is 3,206,055 unique positions **0 through 3,206,054**,
in source order, with the 38-column canonical prefix intact. One row remains for
every submission. The release paths below are relative to `raw/`; complete original
hashes and dictionary citations are in the selected `inputs.json` raw inventory.

| Year | Selected source file | Source rows | Census exact | HUD singleton | Unassigned |
| --- | --- | --- | --- | --- | --- |
| 2016 | `osha/summary/2016/ITA Data CY 2016.zip` | 214,978 | 134,664 | 59,408 | 20,906 |
| 2017 | `osha/summary/2017/ITA Data CY 2017.zip` | 259,758 | 165,945 | 70,282 | 23,531 |
| 2018 | `osha/summary/2018/ITA Data CY 2018.zip` | 289,534 | 183,906 | 79,087 | 26,541 |
| 2019 | `osha/summary/2019/ITA Data CY 2019.zip` | 290,475 | 187,017 | 77,391 | 26,067 |
| 2020 | `osha/summary/2020/ITA-Data-CY-2020.zip` | 293,391 | 190,200 | 77,013 | 26,178 |
| 2021 | `osha/summary/2021/ITA-data-cy2021.zip` | 317,978 | 199,134 | 89,188 | 29,656 |
| 2022 | `osha/summary/2022/ITA-data-cy2022.zip` | 346,799 | 226,238 | 89,636 | 30,925 |
| 2023 | `osha/summary/2023/ITA_300A_Summary_Data_2023_through_12-31-2024.zip` | 394,234 | 257,226 | 98,840 | 38,168 |
| 2024 | `osha/summary/2024/ITA_300A_Summary_Data_2024_through_12-31-2025.zip` | 398,620 | 260,865 | 102,562 | 35,193 |
| 2025 | `osha/summary/2025/ITA_300A_Summary_Data_2025_through_08-31-2026.csv` | 400,288 | 262,252 | 102,719 | 35,317 |

All-year totals: **2,067,447 Census exact**, **846,126 HUD singleton** and
**292,482 unassigned** = 3,206,055. Census exact-compatible assignment takes
precedence. HUD fallback requires exactly one county among **all original positive
business-share candidates**, then compatibility and scope checks. Largest-share,
zero-share selection and invented old-Connecticut bridges never supply assignments.
Delivered-state exclusions and returned-county exclusions remain separate flags.

Raw geocoder outcomes below are source-row-weighted outcomes after mapping distinct
request evidence back to submissions; an Exact response is not automatically an
adopted compatible county assignment:

| Year | Match / Exact | Match / Non_Exact | No_Match | Tie |
| --- | --- | --- | --- | --- |
| 2016 | 134,672 | 48,331 | 29,874 | 2,101 |
| 2017 | 165,954 | 56,346 | 35,152 | 2,306 |
| 2018 | 183,921 | 61,935 | 41,019 | 2,659 |
| 2019 | 187,027 | 60,947 | 40,068 | 2,433 |
| 2020 | 190,212 | 60,624 | 40,065 | 2,490 |
| 2021 | 199,159 | 71,567 | 43,592 | 3,660 |
| 2022 | 226,280 | 70,224 | 47,494 | 2,801 |
| 2023 | 257,265 | 79,185 | 54,527 | 3,257 |
| 2024 | 260,904 | 80,549 | 54,044 | 3,123 |
| 2025 | 262,299 | 79,466 | 55,344 | 3,179 |

Unassigned reasons and overlapping scope diagnostics are recorded for every year.
Here `absent`, `multiple_counties`, `out_of_scope` and `zero_business` abbreviate
`no_compatible_county:<reason>`. Delivered exclusion is the disjoint reason
`delivered_state_out_of_scope`; returned out-of-scope is a separate diagnostic,
not another disjoint reason column. Returned incompatible and legacy-CT flags,
and HUD incompatible/legacy-CT flags, are zero in all years.

| Year | Delivered exclusion | Absent | Multiple counties | Out of scope | Zero business | Returned out-of-scope flag |
| --- | --- | --- | --- | --- | --- | --- |
| 2016 | 956 | 1,047 | 18,373 | 1 | 529 | 69 |
| 2017 | 1,132 | 1,128 | 20,602 | 2 | 667 | 102 |
| 2018 | 1,556 | 1,275 | 22,969 | 1 | 740 | 137 |
| 2019 | 1,352 | 1,158 | 22,808 | 2 | 747 | 130 |
| 2020 | 1,502 | 1,280 | 22,641 | 1 | 754 | 131 |
| 2021 | 1,527 | 1,416 | 25,896 | 0 | 817 | 154 |
| 2022 | 1,453 | 1,612 | 27,005 | 0 | 855 | 172 |
| 2023 | 1,731 | 5,721 | 29,824 | 13 | 879 | 226 |
| 2024 | 1,736 | 1,453 | 31,139 | 1 | 864 | 192 |
| 2025 | 1,942 | 1,411 | 31,127 | 11 | 826 | 234 |

The following partition is disjoint within each year: unassigned geography,
assigned but excluded industry, and assigned eligible native industry. The latter
is an all-year diagnostic; only 2023 produces targets. All-year native-assigned
support is 749,454 and assigned excluded-industry support is 2,164,119. These are
not additional target families or years.

| Year | Assigned | Native eligible (diagnostic) | Assigned excluded industry | Unassigned geography |
| --- | --- | --- | --- | --- |
| 2016 | 194,072 | 0 | 194,072 | 20,906 |
| 2017 | 236,227 | 0 | 236,227 | 23,531 |
| 2018 | 262,993 | 0 | 262,993 | 26,541 |
| 2019 | 264,408 | 0 | 264,408 | 26,067 |
| 2020 | 267,213 | 0 | 267,213 | 26,178 |
| 2021 | 288,322 | 0 | 288,322 | 29,656 |
| 2022 | 315,874 | 0 | 315,874 | 30,925 |
| 2023 | 356,066 | 324,191 | 31,875 | 38,168 |
| 2024 | 363,427 | 202,977 | 160,450 | 35,193 |
| 2025 | 364,971 | 222,286 | 142,685 | 35,317 |

## 2023 eligibility, counts and support

Of **394,234** 2023 submissions, **257,226** receive Census exact-compatible
counties and **98,840** receive adopted HUD singleton counties: **356,066 assigned**.
The remaining **38,168** have unassigned geography. Among assigned records,
**324,191** have valid native six-digit NAICS 2022 membership and **31,875** are
excluded by industry status. The three disjoint totals reconcile to the source:
324,191 + 31,875 + 38,168 = 394,234. Eligible method supports are **234,697 Census**
and **89,494 HUD**; compatible singleton fallback is included and explicitly flagged.

| 2023 mapping status | Source records | Census exact | HUD singleton | Unassigned |
| --- | --- | --- | --- | --- |
| concorded | 33,643 | 21,271 | 8,615 | 3,757 |
| native_2022 | 358,294 | 234,697 | 89,494 | 34,103 |
| unknown_vintage_unmapped | 2,297 | 1,258 | 731 | 308 |

`concorded` and `unknown_vintage_unmapped` remain excluded; crosswalked,
ambiguous and unresolved flags are preserved even when an intermediate candidate
looks determinate. Eligibility uses selected graph membership, not code prefixes.
Employment, hours, filing flags, voluntary/outside-rule filings and nullable filing
decisions remain diagnostics; they are not added eligibility filters or employment
weights. Only assigned compatible counties and native industry support enter the
conditional 2023 numerator and denominator.

Each eligible record has weight one. A target cell's `value` is its
`n_unweighted` divided by eligible support in that county; `n_weighted` is the
same support represented as Float64. The sum of cell counts and the sum of county
`n_eligible` both equal **324,191**. Independent per-cell, per-county and
`n_assigned = n_eligible + n_excluded_industry` checks passed. Maximum absolute
per-county share-sum residual was **4.6629367034256575e-15**, below `1e-12`.
No synthetic zero cells are emitted. Four of the 3,069 assigned-record denominator
counties have no eligible support and no target cells.

| Distribution | Count | Min | p25 | Median | p75 | p95 | Max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Eligible records per denominator county | 3,069 | 0 | 8.0 | 23.0 | 70.0 | 493.0 | 7,880 |
| Eligible records per observed target cell | 126,958 | 1 | 1.0 | 1.0 | 2.0 | 8.0 | 695 |

All **126,958** cells have null standard errors, `se_method='none'` and
`size_gate_pending`. No count threshold is set or passed; V9 remains open.

Exact duplicates were measured on all 38 canonical columns, before appended
identity/assignment columns. Repeated-ID diagnostics exclude null IDs. No group
was collapsed or relinked:

| All-year diagnostic | Repeated groups | Rows in repeated groups | Excess beyond one per group |
| --- | --- | --- | --- |
| Exact canonical duplicates | 1,227 | 2,454 | 1,227 |
| Repeated id | 2,041 | 4,082 | 2,041 |
| Repeated establishment_id | 694,513 | 2,521,986 | 1,827,473 |

These are multiplicity diagnostics, not independent confirmations of establishment
identity. The source-row key, rather than `id` or `establishment_id`, preserves the
submission grain. Stage 10 text-pair/linkage work remains separate.

### Every Boolean diagnostic: true and null counts

The all-source values below are independently recorded in final QA; 2023 values
come from the published report's `flags_by_year`. Missing positive-support entries
mean zero, not a coercion of source nulls. False counts are the corresponding source
total minus true and null. Counts overlap across flags and must not be summed into
a disjoint exclusion total.

| Boolean column | All years true | All years null | 2023 true | 2023 null |
| --- | --- | --- | --- | --- |
| `naics_year_from_dictionary` | 2,012,913 | 0 | 0 | 0 |
| `flag_employment` | 14,839 | 0 | 2,121 | 0 |
| `flag_hours_per_employee` | 148,275 | 14,839 | 17,852 | 2,121 |
| `flag_below_filing_size` | 593,802 | 0 | 83,403 | 0 |
| `flag_naics_year_unknown` | 2,670 | 0 | 2,297 | 0 |
| `flag_naics_crosswalked` | 2,313,912 | 0 | 33,643 | 0 |
| `flag_naics_ambiguous` | 46,333 | 0 | 4,654 | 0 |
| `flag_naics_unresolved` | 69,035 | 0 | 2,297 | 0 |
| `flag_outside_filing_industry` | 278,124 | 683,129 | 34,089 | 92,317 |
| `flag_outside_filing_rule` | 871,926 | 89,327 | 117,492 | 8,914 |
| `flag_filing_rule_label_bridged` | 7,227 | 0 | 1,040 | 0 |
| `flag_filing_reference_ambiguous` | 6,643 | 0 | 949 | 0 |
| `flag_zip_zero_business` | 9,253 | 0 | 1,093 | 0 |
| `flag_zip_multiple_counties` | 706,304 | 0 | 84,659 | 0 |
| `flag_zip_has_out_of_scope` | 10,111 | 0 | 1,673 | 0 |
| `flag_zip_has_incompatible` | 0 | 0 | 0 | 0 |
| `flag_zip_legacy_ct` | 0 | 0 | 0 | 0 |
| `flag_delivered_state_out_of_scope` | 14,887 | 0 | 1,731 | 0 |
| `flag_geocode_county_out_of_scope` | 1,547 | 0 | 226 | 0 |
| `flag_geocode_county_incompatible` | 0 | 0 | 0 | 0 |
| `flag_geocode_county_legacy_ct` | 0 | 0 | 0 | 0 |
| `flag_request_incomplete` | 21,406 | 0 | 14,418 | 0 |
| `flag_assignment_hud` | 846,126 | 0 | 98,840 | 0 |

`target_flag_counts.parquet` contains **256,743** positive true/null support rows.
`scope='numerator'` is by county/industry; `scope='denominator'` is by county with
null industry ID. Support is calculated on eligible 2023 records, separately from
the all-source diagnostics above. There are 193,280 numerator true rows and 41,817
numerator null rows; denominator rows are 16,755 true and 4,891 null. Across each
scope, overlapping flag-support sums are 357,269 true and 80,308 null, not distinct
record totals. Labels such as `numerator:flag_assignment_hud:true` mean positive
support, not that every cell record has the flag. The sidecar retains the counts
needed to interpret those labels.

## Output contract, exact replay and inventories

Each selected target directory contains exactly seven files: four Parquets,
`inputs.json`, `report.json`, and detached `outputs.json`, which inventories the
other six. The Parquet grains and row counts are:

- `ita_county_assignments.parquet`: 3,206,055 source records, 38 original canonical
  columns followed by source/request identity, match/HUD diagnostics, typed county
  and administrative/CBSA fields, assignment method/reason and scope flags.
- `ita_area_mix.parquet`: 126,958 observed county/native-industry cells using the
  ordered 16-column `targets-v1` contract: `source`, `family`, `unit_a_type`,
  `unit_a`, `unit_b_type`, `unit_b`, `measure`, `value`, `se`, `se_method`,
  `n_unweighted`, `n_weighted`, `sample_set`, `vintage`, `universe`, `flags`.
- `county_denominators.parquet`: 3,069 rows, ordered fields `sample_set`, `county_id`,
  `n_assigned`, `n_eligible`, `n_excluded_industry`.
- `target_flag_counts.parquet`: 256,743 rows, ordered fields `scope`, `county_id`,
  `naics_2022_node_id`, `flag_name`, `flag_state`, `n`.

Metadata is `source='osha_ita'`, `family='area_mix'`, county to
`naics_national_industry`, `measure='establishment_share'`,
`sample_set='ita_300a_2023'`, `vintage='naics=2022;county=2025'`, with the full
conditional universe string in every target. Typed nodes, schemas, null/support
invariants, flags and publication inventory were checked by public validators.

Both public `ita_target_build.verify_bundle` checks passed. Replay compared all
four tables by exact ordered schemas, counts and values, then independently
streamed ordered Polars struct hashes under the same frozen Polars version:

| Parquet | Rows | Common ordered logical SHA-256 |
| --- | --- | --- |
| ita_county_assignments.parquet | 3,206,055 | `bfbd4302bee239f31a78e9d0704640ac65709800518cb20098c161f3eb39aeaa` |
| ita_area_mix.parquet | 126,958 | `6599b31b4d730b1909c5c029b3603dba6239d97841044193550ff6544955ccd8` |
| county_denominators.parquet | 3,069 | `bea2e75b4eb8762d0f6bbc4f5d8723adfd552c71aa860e8c9a312288271c3c13` |
| target_flag_counts.parquet | 256,743 | `a4b849c8c6a6b9c5fa37fed20c152ab0b023ed878230c99d9e55fef5d895bcf4` |

Acquisition/preparation evidence is **exactly identical**, including all catalogs,
selection/start/completion metadata, receipt/response times, options and hashes.
Reports are identical after only verified serialization inventory normalization.
The complete JSON normalization whitelist is:

1. `inputs.target_run_id`.
2. `inputs.execution.created_at`.
3. `report.tables.*.sha256` and `.size`, after verifying those serialization inventories.
4. `outputs.*.sha256` and `.size`, after verifying the consequential file inventories.

No acquisition timestamp/hash/option, execution commit/dirty flag, schema, ordered
column, row count, logical table content or other input/report field was waived.
The physical checksums below describe these two serializations. Some differ despite
exact logical equality; no claim is made that Parquet bytes are stable across
future builds or library versions.

### First production build

`derived/targets/stage6_ita_area_mix_20261014_1000_csv/`


| Inventoried file | Bytes | Physical SHA-256 |
| --- | --- | --- |
| county_denominators.parquet | 15,320 | `59b4a3cae06af94770b662c57ac7c1eab5371ba55d0a2deebbb5b9e7812887ea` |
| inputs.json | 4,797,383 | `71c03252f5b08c471a8aabc1ffe8596670a1a112448153ce6b30a2f80fc9f0fd` |
| ita_area_mix.parquet | 1,308,672 | `0d6ac274226434fc0fcf5b3f467baebe23be2c36695b83c1d24288b98edee604` |
| ita_county_assignments.parquet | 353,137,941 | `61f9321ea6a09d64e28e93256e72c527946e4151db3f81a9a426df39ad2ebb02` |
| report.json | 100,547 | `9c2b5fcc7b7d33b4ae776739b7d3d1c27559199b576b84c0263b4ef6605a61dd` |
| target_flag_counts.parquet | 410,550 | `a771af1e521bf02022d658ae7f09b0e35d9751563f620b7d6fbbcaec56cd2879` |

Detached `outputs.json` SHA-256: `084292b6835eb09ce27ecc4a3aef03a6f43bfe7b39b815665c29190a431e2473`.

### Cached offline replay

`derived/targets/stage6_ita_area_mix_20261014_1000_csv_replay/`


| Inventoried file | Bytes | Physical SHA-256 |
| --- | --- | --- |
| county_denominators.parquet | 15,320 | `59b4a3cae06af94770b662c57ac7c1eab5371ba55d0a2deebbb5b9e7812887ea` |
| inputs.json | 4,797,390 | `d54adc483ce9e458e6156031b59ac65ac25be0d64b725c1ab46753f7cc576d64` |
| ita_area_mix.parquet | 1,309,074 | `2a82bc11b7e65fb498e81666b0f6b87cba0f3a61b05fb2089809d6d25b83d11c` |
| ita_county_assignments.parquet | 353,418,450 | `aeb566c78009fb9d0e1a63d60cb4c76a65a63fdd99c5d559a2335e82121eb766` |
| report.json | 100,547 | `32457debef187973188365f398129897a7956c19c552b07a7769cc6a3843d648` |
| target_flag_counts.parquet | 411,623 | `0ad164c0e1a35fa1b557064c4484db9178e424641cc94d1ed600d6bf0c8c8350` |

Detached `outputs.json` SHA-256: `78fd21e37ba0c5b1cd396ff0961b557650788fdccd3c84a911e8c6c3b7fabe71`.

## Software, provenance and immutable-input checks

Contracts are `ita-assignment-inputs-v1`, `ita-request-v1`,
`ita-assignment-v1`, `ita-area-mix-v1`, and `targets-v1`; ZIP normalization is
`ita-verification-zip-v1`, codes are `codes-ita-v1`. The exact runtime is Python
`3.14.0 (main, Oct 14 2025, 21:10:22) [Clang 20.1.4 ]`. Recorded dependency versions
are embedding-data 0.1.0, Polars 2.0.0, fastexcel 0.21.0, HTTPX 0.28.1 and Typer 0.27.3.
The checked lock SHA-256 is
`f57c3280a7c8286711bf6804ca4c02f0a19619c9db52f33941b9c5b996cba8e5`;
`pyproject.toml` SHA-256 is
`0efd4c90ae3efb90d84e25fa8cec8242d870a702109e0abb1bea843753521594`.
Preparation `entry_points` additionally pins CLI implementation and pyproject bytes;
full dependency/implementation/lock inventories are embedded in the pinned
preparation and both target inputs. The target implementation inventory is:

| Module | SHA-256 |
| --- | --- |
| classification_tables | `856d92efe38a98bd7f047f4b96e40368e1bda6da3c052ccf2fde952b4c9803d3` |
| cli | `551c1f41fc861c1e7992b2c3db77a227166b875b856e05ad313fa71fd1edae85` |
| code_build | `0cfc516da2ce05412306f2c8046b37bb2b8b1177501616839a8196c5014a99c2` |
| code_references | `c6fd782cc408ce3db9053296ccab0652878bfa88a1f8cebbac46772ac8b5d728` |
| filing_rules | `23d9fad2ed790c6c8fe382b71dfb31ded49f27736d3a84e4f707d184e89fbc9a` |
| geography_build | `6cbb5d388a25977c06413372684a284166930378161d97cbeab5ead95b597afd` |
| geography_hud | `99124834430a7d8acc4443c42810f16cafa9ea1a4c0e1bdb7b5141f2fa23bf94` |
| geography_parsers | `d38cd177edda764f37e48d2e4dc0f0aba6a098cd068bda9fd9f7985894fd4d36` |
| geography_references | `7d189a5596fa216f5e89b254278c8dadb1b126914c210ad40426be0d6aa67fb9` |
| geography_tables | `4db3084f3dc50c28afe8af1d543e1bb368a2b88337848dd75e7af23e3d6715c6` |
| ita_area_mix | `89b867d4ff11482bf58b981deb7cb9a93941d5381d67bbb10f14ff3d155bffe3` |
| ita_assignment | `74ad2e5b9215f12e3d36fa8bc8533ab51937f46448816b54e7b63aa0fadc9ada` |
| ita_assignment_acquire | `3c8f2254fa6f2584b82be1d074ea8fd13d9934d0335d731a19f8b60bd3702911` |
| ita_assignment_prepare | `f828cc1cb911d299354dbc24cf3e75b23c3aee8f370c53c4958eb5458f73af0e` |
| ita_catalog | `325d4e132719f56a2e94049323ecd1763281df69ee60eae356259fea9b951f58` |
| ita_county_verification | `b7ce702f41ecd7a6008f1e90624576f5772f742c6f5bd8ffa16c964f5196830f` |
| ita_naics_mapping | `bde4a9ddde83b05a9b056631c53601aaeb0f539cae6fd99b49f2edc9cc9b897c` |
| ita_references | `2fbb723fdec6a712b76e82a687de76cc631b023e6ff8520419d9c920588b452c` |
| ita_summary | `082ccabe0ab00d7b03fcfbaea5e2622fced83b4cf1cdef2d51b9a5f5d05f6229` |
| ita_target_build | `8ea943a23759e138a5c47e28f6eb3192c07aa866fb2829183de6301c44b9faaa` |
| ita_verification | `5322a770c808972f1dcb6e640b04750d2f1337bc06a399bcfa87bb59d2464a38` |
| ita_verification_run | `fa4b75b6ad1667e19ce2e46bc77b0320d246cd34b96d818e9d330c9e9d955019` |
| manifest | `b734f4a81923838f21eed010350ddcc8c5b1a632d5defb6d115925273ab36b80` |
| naics_relationships | `e674cb5370d1b8582735e83fb035bc4efbd0ab5b0f0dfc5cc2a82bba1aa25254` |
| osha_benchmark_download | `2911f95a6d851e9dfa00a178df3942446dcf9670bc9799f7f82c9bac5beed2f8` |
| osha_encoding | `4e3efe187e25e1d2dd894207b9d7bdb719ae5543c740c208df401174e7ee6307` |
| paths | `9adc720b3dfe07a5801e41f5f1b7cbe1d1a9d2620b4c983ef5babc63d811a014` |
| target_contract | `15a0359f261d1f2885f1b7bed08f5ac295ae1715c3ca55b8509a3e22cae28f76` |
| target_inputs | `d999e1c8ec7390b2b0450ddd98ea296e368131cc60e072583b880096152898d8` |
| target_io | `19b1bf2818aa83bf27fd5b5c88a1157c3d1abab3918877935fe90218cc161aae` |
| targets_cli | `2121d39200f2e7a2f020e697b796b50d5563d29bef9bacab56044ddc1e217240` |

The expanded D5 before/after comparison reports **1,938 protected files, zero
changed or missing**, covering source summary, prior verification/code/geography/
target/preparation trees, prior raw originals and both earlier acquisition namespaces.
All **631** original manifest entries were independently reverified through
`manifest.entry_for`, and the final manifest begins with exactly the original
**317,417 bytes**. New files/appended entries were allowed; a changed whole-manifest
hash was not treated as damage. Thus earlier controls and all 283 D4 response/receipt
pairs remain byte-identical. The original snapshots were retained, not recaptured
or overwritten to fit later state.

- Protected baseline `/private/tmp/embedding-data-stage6-csv-protected-before.json`:
  SHA-256 `36d949f319dbe30bc556142dc1154e90640afaed485188cb664ed6c609eb2b47`.
- Original manifest `/private/tmp/embedding-data-stage6-csv-manifest-before.jsonl`:
  SHA-256 `7fea0da3cb2b1ca7829fb85670ca6b4ee3d098a5685e56e86f5fd3a8acfb35ff`.
- Actual final QA `/private/tmp/embedding-data-stage6-csv-validation.json`:
  SHA-256 `c4bce9cdd16647b626b8e495cec1a012f2e87b99dbf9432e2f6bd53af314efbb`,
  nonfixture `PASS-WITH-WARNINGS`; both public verifiers, ordered comparisons,
  independent reconciliation and protected checks passed.
- Structured analysis QA report
  `/private/tmp/embedding-data-stage6-csv-validation/validation_report.md`:
  SHA-256 `f464ee855749a92e9773d534468d0494f726b4b6f5bc6031efd2be225b70dd67`,
  records integrity/replay PASS and explicit accuracy, universe and size-gate warnings.
- Whole-tree audit `/private/tmp/embedding-data-stage6-csv-audit.log`:
  SHA-256 `177f3a76142e01c729abfeeb7ae7c444d3b969ef54cdfec893771f75bf7eac65`,
  exact `0 raw provenance discrepancies`, exit 0.

## Scope, limits and V12 readiness

These are conditional shares of submitted **2023** native-NAICS-2022 records with
adopted compatible county assignments, within the 50 states and DC, in the common
county-2025 frame. The ITA filing subset is program-selected; voluntary and
outside-rule submissions remain present, employment is unvalidated, and duplicate
multiplicity is retained. Coverage is neither county accuracy nor population
representativeness. This work does not validate geocodes against an external truth
set, infer historical county truth or estimate unique-establishment shares.

Administrative counties (2025), CBSA membership (July 2023), HUD ZIP support
(2025Q4), and mutable Census Current address data are distinct frames. Applying a
common retrospective frame across ten years does not reconstruct contemporaneous
historical geography. Offline determinism means replay of immutable evidence;
future live responses may differ. Ambiguity, scope, industry and filing diagnostics
must accompany downstream interpretation. No employment/hour filtering, weighting,
linkage/deduplication change, rollup target, extra target year, other target family,
ACS/CPS transformation or V9 gate is supplied here. Targets remain excluded from
embedder training, architecture tuning and model selection.

Separately, the real offline V12 fixture entry point
`tests.target_fixtures.run_ita_v12` produced **21 source rows and five eligible
records**, with a cached replay, four-table ordered parity and a reversed-row
negative control. It ran under external-access barriers in a disposable temporary
data root. Fixture readiness demonstrates the extension seam; it is not substituted
for the full-data evidence measured above.

## Handoff to later stages

The shipped API names below match actual code, rather than earlier proposed
`inputs`/`acquisition` module aliases:

- `target_inputs.select(data_dir, codes_run, geography_run, *,
  codes_outputs_sha256=None, geography_outputs_sha256=None)` returns frozen
  `SelectedInputs`; `.verify(data_dir)` rechecks selected bytes.
- `ita_assignment_prepare.prepare(...) -> Path` freezes a named preparation;
  `check_preparation(data_dir, assignment_run_id) -> PreparedInputs` supplies
  directory, selected inputs, inputs, source/request index paths and batch paths.
- `ita_assignment_acquire.acquire(data_dir, assignment_run_id) -> Path` returns
  the acquisition inventory; `read_evidence(data_dir, prepared) -> Evidence`
  supplies lazy responses/provenance and `.verify()` for frozen cached evidence.
- `ita_assignment.assign(canonical, source_index, responses, hud_lookup, counties)`
  returns a lazy all-year assignment; `assignment_schema`, `validate_assignments`
  and `assignment_report` preserve schema/diagnostics and physical row identity.
- `target_contract.TARGET_SCHEMA`, `validate_targets` and `write_targets` supply
  the generic ordered 16-column contract and serialized inventory. Per-family
  code still owns unit membership, estimator, eligibility, weights and uncertainty.
- `ita_area_mix.estimate(assignments, nodes, *, year=2023) -> AreaMix` returns
  targets, denominators, flag counts and report; `validate_area_mix` checks the
  family-specific support/membership contract.
- `ita_target_build.build(data_dir, assignment_run_id, target_run_id, *, year=2023)
  -> Path` and `verify_bundle(directory, data_dir) -> dict` implement immutable
  offline publication and verification. Another year and an empty eligible 2023
  population fail before publication; preparation/build acquire nothing.

[Implementation](../../src/embedding_data/ita_target_build.py),
[shared target contract](../../src/embedding_data/target_contract.py) and
[ITA estimator](../../src/embedding_data/ita_area_mix.py) define the shipped seams.
The selected bundles/pins above are the consumer selection. Denominator and flag
support must remain separate from cell values and from all-source diagnostics.
Stage 9 ACS, Stage 10 establishment work, Stage 11 CPS panel work and Stage 12
profiles/cross-sections may reuse writer/V12 contracts while supplying their own
family assumptions; Stage 13 consumes prior targets/helpers with their inventories.
This identifies consumers, not a new design for them. ITA `source_row` identity
and duplicate multiplicity are not Stage 10 linkage evidence. All-family coverage,
uncertainty choices and V9 size-gate work remain future scope under the source
spec and roadmap; this finding does not complete those items.

## Verification and completion status

| Gate | Actual result |
| --- | --- |
| Full fresh acquisition / both offline builds | Passed; 1,114 complete batches; both builds exit 0 |
| Public verifiers / exact ordered replay / independent reconciliation | Passed, nonfixture PASS-WITH-WARNINGS |
| Expanded protected bytes / original manifest citations and prefix | Passed; 1,938 unchanged files / 631 entries / 317,417 bytes |
| Whole-tree raw provenance audit | Passed; zero discrepancies, exit 0 |
| Final fresh full pytest | Passed; 883 passed, 1 deselected, 183.49 seconds; exit 0 |
| Final fresh Behave | Passed; 1 feature, 2 scenarios, 10 steps; exit 0 |
| Final fresh Ruff | Passed; `All checks passed!`, exit 0 |
| Final fresh lock check / normal commit hooks | Lock passed; 63 packages, exit 0. Normal applicable hooks, including full Coverage Check, passed on measured documentation commit `56ce059` |
| Independent Task 8 review and final whole-branch review | Both passed through `56ce059`; no outstanding Critical, Important or Minor findings |
| Plan/roadmap/spec completion protocol and integration decision | Plan/spec retired; only Stage 6 stamped complete; nothing deferred. Branch remains unmerged pending the integration choice |

Task 8 review covered `4aa6b55..56ce059`; final whole-branch review covered
`2035d1f8d91bf68b2a004a9d96be1c5a558ecfaf..56ce05909f8069ab21d76fc4df844bb1e95c2608`.
Both returned spec/quality approval without unresolved findings. Their report
SHA-256 identities were `afe8ea4c95d6eb37e97d3b8ae31171cdddc9d8f9aa6584f67e5350683cfd0b7e` and
`a9ccfa3cde8f921d6f03a7a8756cc09ba11ad022e19a72d0bfdde32662f25107`, respectively. A separate Codex CLI
second opinion was skipped because the controller is Codex, as its review recipe
requires; no completed second-opinion run is claimed.

The [completed plan and consumer handoff](../plans/completed/6-target-contract-ita-area-mix.md#handoff-to-later-stages)
and [completed stage spec](../completed/target-contract-ita-area-mix.md) record the
resolved D3/D4/D5 execution, all 43 completed steps and retirement. Resolve-before-defer
found no leftover requiring an owner decision and nothing to defer; no earlier
open backlog item was closed by this stage. Actual backlog statistics were
13 open, 2 ever closed (closure rate 13%), aged >45d: 0; oldest open three days.
The scientific warnings above remain interpretation limits. Stage 6 is complete
on its feature branch; integration is deliberate and the branch/worktree stay
preserved until that choice.
