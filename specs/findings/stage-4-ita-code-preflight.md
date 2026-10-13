# Stage 4 ITA code preflight

Measured 2026-10-13 against `main` at `606f339`. This is design-input evidence
for Stage 4 of `specs/embedding-evaluation-data-spec-roadmap.md`, not a completed
V11 finding, canonical mapping, or benchmark target. No raw source file, derived table,
raw-manifest entry, or roadmap completion status was changed. The owner adopted
the row-retention policy below; R2.5 and the Stage 4 exit now record it.

## Method and scope

Read the three manifested official structure workbooks through
`ita_references.read_titles(data_dir)`, retaining their six-digit codes and
vintages. That reader verifies each input's current SHA-256 and size, and its
full/six-digit row counts. Select each year's raw summary release with
`ita_summary.summary_files(data_dir)`, verify it through `manifest.entry_for`,
and run `harmonize_file` using temporary UTF-8 files under `/private/tmp`.
Aggregate only code, vintage, and filing year; no establishment identifiers,
addresses, descriptions, or IPUMS microdata enter this finding.

For nonmissing codes with a known `naics_year`, compare `(naics_year,
naics_code)` with official six-digit membership in that vintage. Separately
compare the code with membership in the union of 2012, 2017, and 2022. A code
found only in another vintage does not establish the record's actual vintage.
For unknown-vintage rows, count membership in that same union without choosing
a vintage. Null source codes are counted separately.

Repeat the aggregates against the existing
`data/derived/osha/ita_300a_summary.parquet`. The raw and derived per-year
results are exactly equal. The check does not call `build_summary_table`, so
it preserves the physical Parquet bytes pinned by Stage 3's verification runs.
The measured input root is `/Users/lowell/Projects/embedding-data/data`.

## Results

"Absent native" means a known-vintage code is absent from that vintage's
official six-digit structure. "Absent all three" is a subset of that count.
"Unknown valid any" is a subset of unknown-vintage rows, not of absent-native
rows. Counts describe rows, including duplicate source rows retained by Stage 2.

| Filing year | Rows | Absent native | Absent all three | Unknown vintage | Unknown valid any |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2016 | 214,978 | 1,546 | 771 | 0 | 0 |
| 2017 | 259,758 | 2,218 | 1,465 | 0 | 0 |
| 2018 | 289,534 | 8,721 | 516 | 0 | 0 |
| 2019 | 290,475 | 10,307 | 2,444 | 0 | 0 |
| 2020 | 293,391 | 5,160 | 1,081 | 0 | 0 |
| 2021 | 317,978 | 16,314 | 809 | 0 | 0 |
| 2022 | 346,799 | 7,897 | 1,716 | 0 | 0 |
| 2023 | 394,234 | 0 | 0 | 2,297 | 0 |
| 2024 | 398,620 | 4,343 | 281 | 203 | 203 |
| 2025 | 400,288 | 9,859 | 90 | 170 | 170 |
| **Total** | **3,206,055** | **66,365** | **9,173** | **2,670** | **373** |

No source code is missing in these releases. Of the 66,365 absent-native rows,
57,192 have a code found in at least one other supported vintage. Of the
2,670 unknown-vintage rows, 2,297 have a code absent from all three structures.
These disjoint categories yield 11,470 rows with a code absent from all three
structures, regardless of the recorded vintage.

## Design implications and adopted policy

The original Stage 4 exit required zero unmapped ITA codes, including unknown
vintages. The data cannot meet that exit through official 2012/2017/2022
concordances alone. R2.5's original claim that published invalid codes are
missing was also insufficient to describe these measured releases: six-digit
format does not imply official code membership. These observations do not authorize
correcting vintages, truncating codes, allocating across a concordance, or
imputing codes from descriptions.

**Adopted by the owner, 2026-10-13:** retain all source rows and native values;
map supported native codes through the official relationships; explicitly flag
unknown vintage and code/vintage mismatch; retain truly unresolved codes with
no asserted canonical node or candidate set. Report all mapping states and
unresolved counts. Malformed input and reference corruption remain build errors.
The amended Stage 4 exit and R2.5 carry an explicit ITA exception for documented
unresolved source codes. Other sources' parsing requirements remain subject to
their own later verification. The owner subsequently approved shared typed
node/edge tables, a reusable mapping lookup and separate ITA output, flagged
candidate unions for unknown vintages, unresolved known-vintage mismatches, and
filing-rule results only on unanimity. The written
[Stage 4 design](../completed/code-tables-ita-naics-mapping.md) defines those contracts.
Stage 4 remains unticked, and no implementation has shipped.

R2.9 additionally needs a 2007-vintage reference bridge. OSHA explicitly says
its partially exempt list uses NAICS 2007 and that exemption status persists
across later code changes. The existing Stage 3 title references cover only
2012, 2017, and 2022. Stage 2's plan already records the historical designated
list change; the Stage 4 design must preserve each list's own vintage and
effective period. Sources: [OSHA exempt-industry list](https://www.osha.gov/recordkeeping/presentations/exempttable),
[OSHA FAQ 2-3](https://www.osha.gov/faq/2-3),
[OSHA FAQ 2-4](https://www.osha.gov/faq/2-4),
and [Census concordances](https://www.census.gov/naics/concordances/concordances.html).

## Verified source inventory

Summary paths are relative to `data/raw/`. Every current file matched its
existing manifest entry; no new retrieval was performed.

| Filing year | Raw path | SHA-256 |
| --- | --- | --- |
| 2016 | `osha/summary/2016/ITA Data CY 2016.zip` | `9f41c720fb02f78788f1090e5fc885fdb09343fc349c4ae4c80cc9165d83742f` |
| 2017 | `osha/summary/2017/ITA Data CY 2017.zip` | `354fb246be90d6bac3d4a7c94e44f90d40f1d3ff73f911d37691ae98a87de0fb` |
| 2018 | `osha/summary/2018/ITA Data CY 2018.zip` | `0bd2e8475a5766baba8883a1258a92168c43c5ff551c853b1992641814b4dc2f` |
| 2019 | `osha/summary/2019/ITA Data CY 2019.zip` | `bf93ea7312bfe34d903c1272f15c785a61b8c8bbc6df6e09f0d3fe372205ac6e` |
| 2020 | `osha/summary/2020/ITA-Data-CY-2020.zip` | `eb704f2cc343adc7710b48204015ac11c3018fae684f44747158d731e713899b` |
| 2021 | `osha/summary/2021/ITA-data-cy2021.zip` | `5a11abc7c085f07f08f130c25bf78c85581b2379fb8b514f728bfcdf5d61b4a3` |
| 2022 | `osha/summary/2022/ITA-data-cy2022.zip` | `e396af8038d40d74b96ebb6ee9b561bbcb8907ee66adff089402a676c919e6ef` |
| 2023 | `osha/summary/2023/ITA_300A_Summary_Data_2023_through_12-31-2024.zip` | `25da8bc426db219a7a5fe872e73830afebdfac87c460f8cf6561658e7103b487` |
| 2024 | `osha/summary/2024/ITA_300A_Summary_Data_2024_through_12-31-2025.zip` | `4cbce7ea32dd4060f442a528670936e552d1b731925f320d9d25a168f9b60b1d` |
| 2025 | `osha/summary/2025/ITA_300A_Summary_Data_2025_through_08-31-2026.csv` | `9ea2ee5d7265cddf753d22633af17d4aaba4ab81629341462a8c9912d19a99fc` |

The three structure workbooks and hashes are unchanged from plan 3's
[manifested official title inventory](../plans/completed/3-ita-verification.md#manifested-official-title-inputs).
