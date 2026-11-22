# NAICS evaluation data — Stage 5 findings: TRI parent links

Stage 5 of `specs/naics-evaluation-data-roadmap.md` builds O7 and O8 from EPA's Toxics
Release Inventory (TRI) parent data. O7 is the parent-link target. O8 is the holding-company
table. The spec is `specs/tri-parent-links.md`. The plan is
`specs/plans/13-tri-parent-links.md`.

This file records the preflight first. Later tasks add the run results.

## Preflight (Task 4, 2026-11-19)

The preflight reads three raw files and checks three things before any build trusts them.
E7 checks the NAICS fields. E8 checks the parent fields. E9 checks the data license.
No check stopped the stage. The `measure` command listed no stop and no ask.

### Snapshot and raw files

EPA's basic data files page said "Includes reporting forms processed as of: November 5,
2025". The snapshot date is 2025-11-05. The owner downloaded the three files in a browser.
The controller imported each one with `import-file`, after a go-ahead per file.

| Year | Path under `data/raw/` | Bytes | SHA-256 |
|---|---|---:|---|
| 2022 | `epa_tri/basic/2022/2025-11-05/2022_us.csv` | 62,646,049 | `baba5a2ab530d1d02fe1019bdddcd1aa2621cca245abfdc5de71562ce0dad5ae` |
| 2023 | `epa_tri/basic/2023/2025-11-05/2023_us.csv` | 61,601,087 | `4f9d689effb212528256b7f1c6dba8ce1adf90f616591175f93a9050de40d982` |
| 2024 | `epa_tri/basic/2024/2025-11-05/2024_us.csv` | 60,550,684 | `06dfa3a67bb4c5bd38d9e9f0f7b8bff10b95254a63169423632d7f6f251e1506` |

The manifest has three new lines. Each has client `manual-import` and `source_url` null.
Each flags `retrieved_at` as a proxy (the time of import, not of the browser download).
The first 1,549,274 bytes of the manifest are unchanged (SHA-256 `0c610ce1…bb71`).

### Page facts (read 2026-11-18, Task 1)

- The page gives no per-year link. One inline script builds the URL:
  `https://data.epa.gov/efservice/downloads/tri/mv_tri_basic_download/${year}_${geography}/csv`.
  Two drop-down lists supply `year` (1987 to 2024) and `geography` (`US` is the U.S. file).
- `HEAD` requests to the three data URLs answered `500` with a 84-byte JSON error body.
  The browser user agent gave the same result. The endpoint does not serve `HEAD`.
- A `GET` of the 2022 URL (headers only, nothing written) answered `200`, `Transfer-Encoding:
  chunked`, no `Content-Length`, and `Content-Disposition: attachment; filename="2022_us.csv"`.
- Consequence: `acquire` refuses every EPA file, because it needs a `Content-Length` to
  check the size. The owner downloads in a browser and `import-file` records the file.
- The owner chose EPA's own file name, `{year}_us.csv`, as the registered name (2026-11-19).
  The browser saved the 2023 and 2024 files under that pattern.

### Layout

All three files have the same 122-column header, no byte-order mark and no invalid UTF-8
line. The layout is in `src/embedding_data/tri_layouts.json`. The mapped cells are
`1. YEAR`, `2. TRIFD`, `36. DOC_CTRL_NUM`, `49. FORM TYPE`, `8. ST`, `21. FEDERAL FACILITY`,
`30. PRIMARY NAICS`, `31. NAICS 2` to `35. NAICS 6`, `15. PARENT CO NAME`,
`16. PARENT CO DB NUM` and `17. STANDARD PARENT CO NAME`. The `YEAR` column holds only the
file's year in every row. No two logical fields share a cell.

The value sets are `R`, `A`, `YES`, `NO`, `NA` (no parent) and `NA` (no D&B number), in
every year. A scan of the parent name, standardized name and D&B columns found no other
placeholder. Blank cells are also read as "none". Every observed form type and federal value
lies in a set.

**RY2022 foreign-parent columns.** The RY2022 file has the three foreign-parent columns, and
they hold data: 11,016 filled names, 7,251 filled D&B cells and 15,371 filled standardized
names. The spec expects them empty for RY2022. The layout keeps them unmapped for RY2022,
because the spec and the layout parser require it, and 40 CFR 372.3 starts the separate
foreign parent in RY2023. These fields are diagnostic. The stage does not stop. The build
reads no foreign parent name for RY2022.

### E7 and E8 measures (`measure`, exit 0)

Facility-year means one TRIFD in one reporting year. A form is one row of the file.
Case (a), (b) and (c) are the "no parent" cases of the spec's Owner keys.

| Measure | 2022 | 2023 | 2024 |
|---|---|---|---|
| rows (forms) | 80,040 | 78,647 | 77,295 |
| form R / form A | 71,005 / 9,035 | 69,809 / 8,838 | 68,567 / 8,728 |
| facility-years | 22,112 | 21,870 | 21,482 |
| single primary code in NAICS 2022 | 21,982 | 21,773 | 21,412 |
| single primary code outside NAICS 2022 | 22 | 10 | 9 |
| trigger rate (outside the set, share of facility-years) | 0.099% | 0.046% | 0.042% |
| several primary codes | 108 | 87 | 61 |
| no primary code | 0 | 0 | 0 |
| federal YES / NO (rows) | 1,127 / 78,913 | 1,158 / 77,489 | 1,112 / 76,183 |
| distinct state codes | 56 | 56 | 56 |
| invalid UTF-8 lines | 0 | 0 | 0 |
| document control numbers distinct / repeated / blank | 80,040 / 0 / 0 | 78,647 / 0 / 0 | 77,295 / 0 / 0 |
| NAICS 2 to NAICS 6 filled (rows) | 9,183 / 2,594 / 822 / 227 / 63 | 9,027 / 2,534 / 834 / 254 / 62 | 8,965 / 2,530 / 802 / 230 / 55 |
| facility-years with a standardized name | 18,448 | 18,222 | 17,871 |
| facility-years with a reported name | 16,121 | 15,909 | 15,627 |
| facility-years with a D&B number | 13,560 | 13,397 | 13,188 |
| standardized names with more than one D&B number | 630 | 617 | 611 |
| D&B numbers with more than one standardized name | 125 | 113 | 97 |
| standardized name differs from reported name (of facility-years with both) | 2,188 / 16,106 (13.6%) | 2,176 / 15,891 (13.7%) | 2,085 / 15,620 (13.3%) |
| case (a): reported "no parent", standardized name given | 2,342 | 2,331 | 2,251 |
| case (b): reported name, standardized name blank | 15 | 18 | 7 |
| case (c): D&B number, standardized name blank | 11 | 15 | 5 |

- **E7 trigger.** The rate stays far below the 1% line in every year. The trigger does not fire.
- **Case (a) is large.** About 10% of facility-years report "no parent" but carry an EPA
  standardized name. The spec says EPA's standardized name alone decides, so the headline key
  groups them under that name. Case (a) is counted, not a stop.
- **Several primary codes.** A facility-year whose forms give more than one primary code gets
  no NAICS node ID. The build excludes it with the reason `naics_conflict` (spec, Owner keys
  and Table).

### Document checks (read 2026-11-19)

| Check | Source | Result | Quote |
|---|---|---|---|
| E7 NAICS edition | [EPA NAICS 2022 page](https://www.epa.gov/toxics-release-inventory-tri-program/adoption-2022-north-american-industry-classification-system), page dated 2026-10-13 | RY2022 uses the 2022 edition. The page names no edition for RY2023 or RY2024. | "implemented the 2022 codes for TRI Reporting Year 2022" |
| E7 NAICS edition | [Basic data files documentation](https://www.epa.gov/system/files/documents/2025-09/basic_data_files_documentation_august_2024.pdf) (August 2024, updated for RY2023) | The PDF names no NAICS edition for any year. No stop. | none (no edition named) |
| E8 time basis | Same PDF, field 17 | The standardized parent reflects the current owner, not the owner at the end of the reporting year. Recorded as a limit. | "best reflect the current ultimate U.S. parent company" |
| E9 license | [EPA data license](https://edg.epa.gov/EPA_Data_License.html), no date on the page | Public domain by default. It names no reuse limit and no third-party identifier rule. | "by default in the public domain" |
| E9 TRI terms | The basic data files page (updated 2026-01-28) and the PDF | No TRI-specific terms in either. | none found |

The measured share of facility-years outside the NAICS 2022 set is below 0.1% in every year.
This supports the 2022 edition for RY2023 and RY2024, but EPA's pages do not say it.
The spec stops the stage only when EPA names an edition other than 2022. EPA names none,
so E7 does not stop the stage.

### `through_date` departure

Stage 5 manifest entries put EPA's "processed as of" date in `through_date`. The frozen
docstring at `src/embedding_data/manifest.py:8` says the field is the submission
through-date that an OSHA ITA summary file name carries. The frozen docstring stays
unchanged. A search on 2026-11-18 (`grep -rnE "\.through_date|\['through_date'\]" src
scripts`) found no code that reads the field from an entry. Only `ita_catalog` and
`ita_summary` parse a through-date, and they parse file names. Several modules copy whole
entries and carry the field unread. `target_io.verify_raw` compares whole entries, so the
field is part of citation equality there. It is not a read.

## Full-data build (Task 13, 2026-11-21)

The build, `verify`, the independent reconciler and the preservation checks ran once on the
real files. Every check passed. Fixture results show software readiness. They are not
benchmarks.

| Item | Value |
|---|---|
| Run ID | `stage5_tri_parent_links_20261121_r1` |
| Detached pin (SHA-256 of `outputs.json`) | `65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b` |
| Snapshot date (EPA "processed as of") | 2025-11-05 |
| Codes run and pin | `stage4_v11_20261013_r2`, `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |
| Executing source | commit `786ebcc`, `dirty: false` |
| Wall time | 3.52 s (6.25 s user, 1.17 s system) |
| Maximum resident set size | 1,589,870,592 bytes |
| Bundle size | 1,308 KB (`du -sk`) |

The host also ran a commit hook of another session and other jobs during the build, so the
time and the memory figure are upper bounds for a quiet host.

### Verification

- `verify` exited 0. Rows: `tri_facility_years` 65,464, `tri_parent_industries` 7,777,
  `tri_parent_link_marginals` 405, `tri_parent_link_support` 14,204, `tri_parent_links` 14,204.
- `scripts/reconcile_tri_parent_links.py` exited 0 with `equal` true. It recomputed the
  facility-years, the eligibility, the owner counts, the marginals, the support, the targets,
  both sensitivities, the partial owners and the O8 table from the raw files and compared
  them exactly with the bundle.
- `embedding-data audit` exited 0 (0 raw provenance discrepancies). The ITA summary keeps
  SHA-256 `6335cda7…36a8` and 139,930,636 bytes. The six Stage 4, 6 and 10 bundles of the
  plan's preservation table pass `verify_inventory`, and each `outputs.json` has its pin.
- The first 1,549,274 bytes of `raw/manifest.jsonl` hash to the Task 4 baseline value
  (`0c610ce1…bb71`). The baseline copy in `/private/tmp` was gone by then, so the check used
  the hash from the ledger. Seven lines follow: the three TRI lines of Task 4 and four lines
  that other stages wrote (one SAM entity extract and three USAspending subcontract files).

### Counts

| Facility-years | 2022 | 2023 | 2024 |
|---|---:|---:|---:|
| eligible | 21,534 | 21,324 | 20,974 |
| `federal` | 448 | 449 | 438 |
| `naics_conflict` | 108 | 87 | 61 |
| `naics_not_2022` | 22 | 10 | 9 |
| `naics_missing`, `parent_conflict` | 0 | 0 | 0 |
| total | 22,112 | 21,870 | 21,482 |

The totals and the `naics_*` rows equal the E7 measures of the preflight.

- **Owners `N`.** Headline 8,684 (8,080, 7,952 and 7,818 by year). D&B key 12,850 (11,937,
  11,799, 11,569). Federal facilities in 8,700 (8,095, 7,968, 7,833). Owner-key changes 0.
  Parent-name collisions 0 (keys and names).
- **Parents.** 4,566 U.S. parents. The median parent has 2 facilities and 1 industry. The
  most facilities for one parent is 477 and the most industries is 63. `facilities_per_parent`
  counts each TRIFD once.
- **Targets.** 14,204 rows. The marginals cover 405 industries. 264 cells exist only under
  the D&B key and 298 only with federal facilities in. 102 owners are partial, that is, an
  excluded facility-year of theirs might add an industry that the target cannot see.
- **`n_unweighted`.** Minimum 1, median 1, 75th percentile 2, 90th percentile 3, maximum 50.
  4,034 rows have 2 or more, 1,652 have 3 or more, 490 have 5 or more and 94 have 10 or more.
  Every row has `size_gate_pending`. No minimum count is applied. The headline minimum for
  this family is not set here.

### Limits

- **E8 time basis.** EPA's standardized parent reflects the current owner, not the owner at
  the end of each reporting year (documentation field 17, quoted above). Pooled years show
  ownership at the snapshot date. The D&B sensitivity count shows how much the grouping
  matters: it has 12,850 owners against 8,684.
- **`through_date`.** See the departure above. No code reads the field.
- **Partial owners.** The spec's Owner keys text (spec 470–474) can be read two ways for a
  facility-year that has a `naics_*` reason and names several parents. The build and the
  reconciler read it so that every excluded facility-year belongs to each standardized parent
  name that it lists, and to `facility:<TRIFD>` when it lists none. The `federal` reason
  stays out. The ledger records this as a ruling marked unclear, and the final reviewer
  agreed. The two readings differ only for a `naics_*` facility-year that names more than one
  parent. This run did not measure how many exist. No facility-year has the reason
  `parent_conflict`.
- **RY2022 foreign-parent columns.** They hold data but stay unmapped, as the preflight
  section says. The build reads no foreign parent name for RY2022.
- **Reconciler coverage.** The independent reconciler does not recompute the report fields
  `case_a`, `case_b`, `case_c`, `with_parent`, `with_usable_dnb`, the name-collision counts,
  `in_territories`, `n_unweighted_distribution` and `parents.*`. Its "equal" does not cover
  them. They come from the build and from the unit tests.
- **Territories.** The territory set is `AS`, `GU`, `MP`, `PR`, `UM` and `VI`, as plan
  default 13 says. The final review found `UM` missing, and commit `786ebcc` added it before
  the run. The three files hold no `UM` row.
- **`acquire`.** EPA's endpoint sends no `Content-Length`, so `acquire` refuses every file
  (see Page facts). `import-file` is the path that works now.
- **Basis.** TRI is a program-selected population. The `universe` string in `report.json`
  and in every target row says so. Coverage does not validate accuracy.

### For O12, O13 and O17

- **O12.** Run `stage5_tri_parent_links_20261121_r1`, pin
  `65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b`, snapshot 2025-11-05.
- **O13.** The `n_unweighted` distribution above (`report.json`, `n_unweighted_distribution`)
  and `size_gate_pending` on every row.
- **O17.** The counts and the marginals above. Both sensitivity labels
  (`numerator:dnb_key_sensitivity:true` and `numerator:federal_sensitivity:true`). The
  `universe` statement. The E8 time basis. The R8.4 exclusion: no TRI table feeds embedder
  training, curriculum, hard-negative mining or model selection.
- The stage read only `naics_nodes.parquet` of the Stage 4 bundle. It did not read the
  Stage 4 concordance that the roadmap's Consumes line names.
