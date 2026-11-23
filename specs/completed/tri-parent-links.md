# TRI parent links

**Status: COMPLETE (2026-11-21)** — implemented by [plan 13](../plans/completed/13-tri-parent-links.md); the measured run is in the [Stage 5 findings](../naics-evaluation-data-stage-5-findings.md).

> Next step: writing-plans in a fresh session against this file. Do not fetch
> any TRI file, and do not build, before the plan exists and the owner gives
> the go-ahead for each write.

Status: the owner approved this committed spec on 2026-11-18 ("Approve the
spec"), including every call marked "My call". Stage 5 design session of
[the roadmap](../naics-evaluation-data-roadmap.md). On 2026-11-18 the owner chose
all five decisions below ("Accept all picks"), with the calls listed under
Accepted proposals. Calls marked "My call" elsewhere in this file were made
while writing it. A
builder check by a separate reviewer raised four questions on 2026-11-18. Two
follow from the owner's decisions (the "no parent" basis and partial owners).
Two are process calls (document checks and the Stage 9 freeze window). All four
are answered in place. No TRI file was fetched for this design.

## Scope and governing contracts

Stage 5 builds Source 3 of
[the evidence-sources spec](../uncovered-uses-evidence-sources.md) (the Stage 2
spec) once on real data and verifies it. It serves two uses from one evidence
family:

- **O7, peer and competitor detection.** For two NAICS 2022 industries, the
  share of owners in one industry that also operate a TRI facility in the
  other. An owner is a facility's U.S. parent.
- **O8, holding-company classification.** For each parent, the NAICS 2022
  industries of its facilities.

The Stage 2 spec's "Rules for every new family" govern this stage. R5, R7.1,
R7.4, R8 and R9 of [the source spec](../embedding-evaluation-data-spec.md) govern
codes, outputs, provenance, disclosure, leakage and offline operation. The
Stage 10 spec ([completed](ita-establishment-targets.md)) is the
model for the measure, the bundle and the commands.

### Owner decisions (2026-11-18)

| # | Decision | Choice |
|---|---|---|
| 1 | Year window | **Reporting years (RY) 2022–2024, native NAICS 2022, from EPA's complete dataset only.** No preliminary dataset. No earlier years. |
| 2 | Parent key | **EPA's standardized U.S. parent name.** The reported parent Dun & Bradstreet (D&B) number gives a sensitivity count. |
| 3 | Measure | **Mirror Stage 10:** `J(a,b) / n(a)`, each owner counted once, same-year co-presence, both directions, counts and marginals beside the target. |
| 4 | Federal facilities | **Excluded from the headline cells.** A sensitivity count includes them. |
| 5 | Build approach | **One standalone command group and one bundle** (see [Approaches](#approaches)). |

### Accepted proposals (owner, "Accept all picks", 2026-11-18)

- Each facility-year uses its primary NAICS code only. Its other reported
  codes stay in the facility table as diagnostics.
- A facility-year whose forms disagree on the primary NAICS code or on the
  parent keeps every value, is flagged and is excluded from headline cells. No
  value is picked.
- A facility that reports no parent is its own owner. It counts in `n(a)` and
  never joins another facility. "No parent" means no standardized parent name
  (see [Owner keys](#owner-keys)).
- Only the U.S. parent forms groups. The foreign parent stays a field.
- The O8 table is a companion table, because `targets-v1` cannot hold a parent
  unit.
- `compare-runs` is built and fixture-tested in this stage, so O12 only runs
  it.
- The preflight stops the stage only when a coverage condition fails. Measured
  rates are recorded, not gated.
- The outputs publish no D&B number.

### Out of scope

- The replay build, a full-data `compare-runs`, the long-form acceptance finding
  and README and `CLAUDE.md` run pins: O12, TRI hardening.
- The headline minimum count: O13. Every target row keeps
  `size_gate_pending`.
- Scoring, null-model normalization, data splits and acceptance thresholds: the
  family's protocol section, O17. The family is not scored until that section
  exists (protocol, "Families with no section").
- The R8.4 training-role amendment: a separate owner decision after
  naics-embedder's spec.
- Foreign-parent grouping, relations between a facility's own secondary codes,
  RY2021 and earlier, RY2025, and preliminary datasets.
- Facility names, addresses, chemicals and release quantities.
- Any change to a frozen module, an earlier stage's artifact or a raw file.

## Intent

naics-embedder judges its industry-relatedness embedding on evidence families
it never trained on. This repository has no evidence for peer detection or
holding-company classification across firms. ITA co-ownership stays within one
EIN, so it cannot see two subsidiaries with different EINs under one parent.
TRI facilities name their highest-level U.S. parent. Two industries are close
in practice when one parent operates facilities in both. The tree can place
them far apart.

### Goals

- One verified bundle that relates NAICS 2022 industries through shared U.S.
  parents (O7) and lists each parent's industries (O8).
- Counts and marginals that let O13 set a minimum count and O17 choose scores
  with no rebuild.
- A preflight that settles open checks E7–E9 before any data is trusted.

### Non-goals

- A firm-level ownership graph. The parent is the top of the U.S. tree only.
- Coverage outside TRI's reporting population.
- Any score, threshold or embedding comparison.

### Anti-goals

The design fails, even if it runs, when it:

- Groups facilities by a name match of this project's own. Groups come only
  from EPA's standardized parent name or the reported D&B number, compared as
  exact strings.
- Lets two facility-years with no standardized parent name form a shared
  group.
- Picks one value when a facility-year's forms disagree.
- Lets a code that is not a native NAICS 2022 national industry enter a
  headline cell.
- Derives a relation from NAICS code structure.
- Publishes a D&B number.
- Edits a frozen module or an earlier stage's artifact.
- Lets any table feed embedder training, curriculum, hard-negative mining or
  model selection (R8.4).
  *Pointer (owner, P13, 2026-11-23): Section 6 of
  [the evaluation protocol](../evaluation-protocol.md) lets selection for
  naics-embedder's relatedness artifact read the validation part of the parent
  links (P8). This anti-goal is not reworded.*

## What the design session found

Read on 2026-11-18 from public HTML pages and the Federal Register. No TRI file
and no PDF was fetched.

1. **TRI uses NAICS 2022 codes from RY2022.** Forms for RY2022 were due on
   2023-07-01. The change "does not affect the universe of TRI reporting
   facilities"
   ([EPA](https://www.epa.gov/toxics-release-inventory-tri-program/adoption-2022-north-american-industry-classification-system)).
2. **The codified parent definition also starts with RY2022.** 40 CFR 372.3
   defines the parent as the highest-level company of the facility's ownership
   hierarchy as of December 31 of the reporting year. The U.S. parent applies
   from RY2022, and a separate foreign parent from RY2023. A 50:50 joint
   venture is its own parent. A federal facility's parent is its highest-level
   federal agency. Parent names follow EPA's standardized naming conventions
   ([87 FR 63950](https://www.govinfo.gov/content/pkg/FR-2022-10-21/html/2022-22833.htm)).
3. **The complete dataset ends at RY2024.** The basic data files page lists
   1987–2024 and "includes reporting forms processed as of: November 5, 2025".
   Each file is CSV and holds the 100 most-used fields of Form R and Form A.
   EPA revises earlier years in place, so each download is a snapshot. The
   download link runs through JavaScript, so no fixed URL for a year is known
   ([basic data files](https://www.epa.gov/toxics-release-inventory-tri-program/tri-basic-data-files-calendar-years-1987-present)).
4. **One row is one chemical form, not one facility.** A facility files one
   form for each reported chemical. A multi-establishment facility can file
   more than one form for one chemical. A form-type field marks Form A rows
   *(unverified: search summaries of EPA documentation)*.
5. **The standardized parent name may show today's owner.** EPA's
   documentation describes it as developed "to best reflect the current ultimate
   U.S. parent company" *(unverified: search summary of the August 2024
   documentation PDF)*. If so, it can group a 2022 facility under its owner at
   the time of the file, not as of December 31, 2022. The reported D&B number
   follows the regulation's date.
6. **EPA data are public domain by default.** EPA's
   [data license](https://edg.epa.gov/EPA_Data_License.html) says "all data
   produced by the U.S EPA is by default in the public domain". It names no
   reuse restriction and says nothing about third-party identifiers such as D&B
   numbers.
7. **Field names.** The documentation names `PARENT CO NAME`,
   `PARENT CO DB NUM` and a standardized parent name field, with "NA" for a
   parent that has no D&B number *(unverified: search summaries)*. Headers
   carry a numbered prefix in some copies.

**Consequence for the roadmap.** The roadmap's Consumes line for Stage 5 lists
the Stage 4 concordances "for reporting years coded in NAICS 2017". No year in
the chosen window uses NAICS 2017. Stage 5 reads the Stage 4 bundle's
`naics_nodes.parquet` only and does not read its concordance. Plan completion
re-validates the roadmap against this.

## Approaches

| Approach | What it does | Trade-off | Decision |
|---|---|---|---|
| 1. Standalone command group, one bundle | New `python -m embedding_data.tri_parent_links` with acquisition, import, build, verify and compare commands. New modules import reused ones. | Matches Stages 8–10. Leaves every frozen module unchanged. Needs no new dependency. | **Chosen** (owner, 2026-11-18) |
| 2. New commands in the Stage 10 module | Reuses Stage 10's wiring. | Stage 10 records its module hashes. Edits make its `verify` fail. | Rejected |
| 3. Two bundles, one for O7 and one for O8 | Separate runs. | Both read one facility-year table. The selection and provenance code would exist twice. | Rejected |
| 4. Nested project with its own lock | Isolates dependencies. | Only needed for a new dependency. Polars and httpx are already in the root project. Adds a second lock for no gain. | Rejected |

## Selected inputs and trust boundary

### Inputs

| Input | Identity | Use |
|---|---|---|
| TRI basic data files | The U.S. file for each of RY2022, RY2023 and RY2024, from one EPA snapshot, manifest-recorded | Facility-years, codes, parents |
| Stage 4 codes bundle | `stage4_v11_20261013_r2`, detached `outputs.json` SHA-256 `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` | `naics_nodes.parquet`: the 1,012 NAICS 2022 national-industry node IDs, for example `naics:2022:national_industry:111110` |

### Codes selection

**My call:** Stage 5 has its own codes selector. It checks the run ID and pin
syntax, authenticates the detached pin, verifies the bundle inventory with
`target_io.verify_inventory`, checks the schema version and run identity, and
reads `naics_nodes.parquet`. It does not call Stage 10's `select_codes`,
because that function also re-checks the ITA source summary. Stage 5 reads no
ITA data.

### Reused interfaces

Stage 5 imports these and never edits them:

- `target_contract.write_targets`, `validate_targets`, `TARGET_SCHEMA` and
  `TARGET_KEY_COLUMNS` (Stage 6).
- `target_io` (`stage`, `relative_file`, `file_record`, `inventory`,
  `verify_inventory`, `write_json`).
- `manifest` (`describe_file`, `append_entries`, `entry_for`,
  `sha256_file`).
- `paths`.
- `osha_encoding.decode_line`, only if E7 finds bytes that are not valid UTF-8.
- The Stage 10 fixture helper that builds a real Stage 4 bundle
  (`tests/ita_establishment_fixtures.py`), for the V12 fixture.

### Frozen modules

Stage 6's `FROZEN_MODULES` and `TARGET_MODULES`, the Stage 7–9 software files,
the Stage 10 modules recorded in its bundle's `SOFTWARE_FILES`, `cli.py` and
`code_references.py` stay unchanged. So does any test file that an earlier
stage hashes. Stage 5 adds modules only. If the plan finds that a reused
function cannot serve unchanged, it stops and asks the owner.

### What Stage 5 does not consume

- The Stage 4 concordance, ITA data, Stage 5 geography (old roadmap), Stage 6
  assignments, Stage 7–9 IPUMS artifacts and Stage 10 bundles.
- No upstream builder runs.

## Raw TRI files

### Acquisition and import

- `acquire` downloads the U.S. basic data file for each window year (network).
  It reads the "processed as of" date from the basic data files page. It writes
  each file to `.part`, renames it only after its length matches
  `Content-Length`, then records it. The plan's first task finds the download
  URL by reading the page's HTML. Each download needs the owner's go-ahead.
- `import-file YEAR FILE --processed-as-of DATE` registers a file that the owner
  downloaded in a browser (offline). Its `retrieved_at` is the import time,
  flagged as a proxy, as Stage 3 does for HUD.
- Both refuse an existing path. Raw files are never replaced.

### Layout and manifest

**My call:** `data/raw/epa_tri/basic/<RY>/<processed-as-of>/<EPA file name>`.
A later EPA snapshot lands beside the earlier one under its own date. The
manifest entry records the source URL (null for an import), retrieval time,
SHA-256, size, client and version. **My call:** its `through_date` field holds
EPA's "processed as of" date. That field has the same meaning for OSHA (the
date up to which submissions are included), and `manifest.py` is frozen. No
code reads `through_date` across sources. The plan confirms this with a search.

### Snapshot selection

**My call:** `build` takes `--processed-as-of DATE`. For each window year it
selects the one manifested file under that date. A missing or extra file fails
the build. The window is the constant RY2022–2024. The build refuses any other
window.

### Reading

- Every column is read as a string. Codes stay strings (R9.1).
- A registry constant records each window year's exact header row, taken from
  the preflight. The build maps the columns it needs by exact header text. A
  changed header fails the build.
- Each row's reporting-year field must equal the file's year. A mismatch fails
  the build.
- If E7 finds bytes that are not valid UTF-8, the build transcodes through
  `osha_encoding.decode_line` unchanged into owned temporary UTF-8 files. If
  that function cannot serve unchanged, the plan stops and asks the owner.

Columns used (names *unverified* until E7 and E8): reporting year, facility ID
(TRIFD), document control number, form type, state, federal-facility flag,
primary NAICS, NAICS 2 to NAICS 6, parent name, parent D&B number,
standardized parent name, and from RY2023 the foreign parent name, foreign
parent D&B number and standardized foreign parent name.

## Preflight: open checks E7–E9

The preflight runs after the three files are recorded and before any build. It
has two parts. **My calls:**

- **Data checks.** A script, `scripts/preflight_tri.py`, reads only the
  manifested files and the pinned Stage 4 nodes, offline, and prints a JSON
  report.
- **Document checks**, marked "(read)" below. The operator reads the named EPA
  pages and records the URL, the read date and a short quote in the findings
  file. Reading the documentation PDF needs the owner's go-ahead. These
  documents are not manifest-registered and are not stored under the data
  root, because no build step reads them. `acquire` reads the "processed as
  of" date from the basic data files page and does not save the page. The date
  lives in the raw path and the manifest's `through_date`.

The results of both parts go into the Stage 5 findings file. Each covered
verdict holds only while these checks pass.
A failed check stops the stage. The owner then records O7 and O8 as uncovered
or promotes a named alternate, and the Stage 2 spec's verdict table is amended.

| Check | Measures and records | Stops the stage when |
|---|---|---|
| **E7** codes | Each year's exact header row. Rows by form type. The primary NAICS field. The share of facility-years whose primary code is a six-digit NAICS 2022 national industry. Secondary-code fill. The federal-facility field and its distinct values. Bytes that are not valid UTF-8. State codes present. Document control number uniqueness. | A window year has no primary NAICS field. A window year has no federal-facility field, because decision 4 depends on it. EPA's documentation names a NAICS edition other than 2022 for a window year (read). More than 1% of a year's facility-years have a primary code outside the NAICS 2022 national-industry set (**my call:** a trigger to ask the owner, not an acceptance threshold). |
| **E8** parents | The parent fields present by year. The exact strings that mean "no parent" or "no D&B number" (for example `NA` and blank). Fill rates of the standardized name and the D&B number. Standardized names with more than one D&B number, and D&B numbers with more than one standardized name (counts only). The share of facility-years whose standardized name differs from the reported name. The counts of cases (a), (b) and (c) under [Owner keys](#owner-keys). EPA's documented time basis of the standardized name (read). | A window year has no standardized parent field. Or the field is blank for every facility-year that reports a parent. The owner then chooses between the D&B key and an uncovered verdict. A "current owner" time basis is recorded as a limit and does not stop the stage. |
| **E9** terms | EPA's data license statement and its date (read). Any TRI-specific terms on the basic data files page or in the documentation (read). | An EPA statement restricts publishing aggregates or facility-level rows. A failed terms check never becomes "build it but keep the aggregates local" (Stage 2 rule). |

## Facility-year table

### Reduction

Rows are grouped by reporting year and TRIFD. Form R and Form A rows both
count. For each facility-year the build keeps:

- The form count, by form type.
- The sorted distinct primary NAICS values, after stripping surrounding
  whitespace.
- The sorted distinct NAICS 2 to NAICS 6 values (diagnostic).
- The sorted distinct standardized parent names, after stripping surrounding
  whitespace and dropping the E8 "no parent" strings. No case folding and no
  other normalization.
- The sorted distinct federal-flag values and state codes.
- From RY2023, the sorted distinct standardized foreign parent names
  (diagnostic).

D&B numbers are read only to compute the sensitivity counts. They are not
stored in any output.

### Rules for mixed forms

- **My call:** if some forms name a parent and others give a "no parent"
  string, the facility-year keeps the named parent and sets
  `flag_parent_mixed_blank`. A blank is absence, not a competing value.
- **My call:** if any form marks the facility as federal, the facility-year is
  federal.

### Eligibility

An eligible facility-year has exactly one primary NAICS value, that value is a
NAICS 2022 national-industry code in the selected Stage 4 nodes, it has at most
one standardized parent name, and it is not federal. Exclusion reasons are
disjoint and checked in this order:

1. `naics_missing`: no primary NAICS value.
2. `naics_conflict`: more than one primary NAICS value.
3. `naics_not_2022`: the one value is not a NAICS 2022 national-industry code.
4. `parent_conflict`: more than one standardized parent name.
5. `federal`: a federal facility.

### Owner keys

- Headline: `parent:<standardized name>` when the facility-year names a parent,
  else `facility:<TRIFD>`.
- D&B sensitivity: `dnb:<number>` when the facility-year's forms give exactly
  one usable D&B number, else `facility:<TRIFD>`.

Keys are compared as exact strings. A facility-year with no standardized parent
name never shares a key with another facility.

**My call: EPA's standardized name alone decides "no parent".** The owner chose
it as the key (decision 2). The reported parent name is a diagnostic only. Three
cases follow, and E8 counts each:

- (a) The reported parent is a "no parent" string, but EPA gives a standardized
  name. The facility-year is grouped under EPA's name, as EPA's own resolution.
- (b) The reported parent is named, but the standardized name is blank. The
  facility-year is self-owned and is not in the O8 table. This can only lower
  `J`.
- (c) The D&B sensitivity reads the D&B field alone. A usable D&B number groups
  facility-years under the sensitivity even when the standardized name is
  blank.

### Table

`tri_facility_years.parquet`, one row per facility-year in the window, sorted
by `reporting_year`, `trifd`:

| Column | Type | Meaning |
|---|---|---|
| `reporting_year` | Int64 | 2022, 2023 or 2024 |
| `trifd` | String | EPA facility ID, as delivered |
| `n_forms`, `n_form_r`, `n_form_a` | UInt64 | Forms in the file |
| `primary_naics_values` | List(String) | Distinct delivered primary codes |
| `other_naics_values` | List(String) | Distinct delivered NAICS 2 to NAICS 6 codes |
| `naics_2022_node_id` | String | The national-industry node ID, or null unless the facility-year has exactly one valid primary code |
| `parent_names` | List(String) | Distinct standardized U.S. parent names |
| `foreign_parent_names` | List(String) | Distinct standardized foreign parent names, empty for RY2022 |
| `federal_values`, `state_values` | List(String) | Distinct delivered values |
| `flag_parent_mixed_blank` | Boolean | Some forms name the parent, others give a "no parent" string |
| `owner_key` | String | Headline owner key, null when excluded |
| `exclusion_reason` | String | One of the five reasons, null when eligible |

## Parent-link target (O7)

### Estimand

Let `O` be the set of headline owner keys with at least one eligible
facility-year. For owner `o` and year `t`, let `S(o,t)` be the set of
`naics_2022_node_id` values of its eligible facility-years in year `t`. Then:

- `n(a)` = number of owners `o` with `a` in `S(o,t)` for some `t`.
- `J(a,b)` = number of owners `o` with both `a` and `b` in `S(o,t)` for the
  same `t`, for `a ≠ b`.
- `N` = number of owners in `O`.

Each owner counts at most once in `n(a)` and once in `J(a,b)`, however many
facilities, forms or years it has. A self-owned facility has one code a year,
so it can count in `n(a)` but never in `J(a,b)`.

For each ordered pair `(a,b)` with `J(a,b) > 0` and `a ≠ b`, emit one target
row with `value = J(a,b) / n(a)`. Both directions are emitted. No zero cells
and no diagonal cells are emitted. `0 < value ≤ 1`.

The D&B sensitivity recomputes `n`, `J` and `N` with the D&B owner keys over
the same eligible facility-years. The federal sensitivity recomputes them with
headline keys over the eligible facility-years plus those excluded only as
`federal`.

### Target rows

`tri_parent_links.parquet`, written by `target_contract.write_targets`:

| Column | Value |
|---|---|
| `source` | `epa_tri` |
| `family` | `tri_parent_links` |
| `unit_a_type`, `unit_b_type` | `naics_national_industry` |
| `unit_a`, `unit_b` | NAICS 2022 national-industry node IDs from the selected bundle |
| `measure` | `owner_share` |
| `value` | `J(a,b) / n(a)` |
| `se`, `se_method` | null, `none` |
| `n_unweighted` | `J(a,b)` |
| `n_weighted` | `float(J(a,b))` |
| `sample_set` | `tri_basic_ry2022_2024` |
| `vintage` | `naics=2022` |
| `universe` | Statement below |
| `flags` | `size_gate_pending`, plus the support labels below |

Support labels: add `numerator:dnb_key_sensitivity:true` when the D&B
sensitivity `J` differs from `J(a,b)`. Add
`numerator:federal_sensitivity:true` when the federal sensitivity `J` differs.

Universe statement (one string, with the snapshot date filled in): "EPA Toxics
Release Inventory basic data files, U.S. files for reporting years 2022–2024,
forms processed as of <date>. TRI is a program-selected population of
facilities that meet its reporting criteria, not a frame of all establishments
or firms. Codes are self-reported primary NAICS 2022 codes, one per facility. A
facility can contain more than one establishment. An owner is EPA's
standardized highest-level U.S. parent, or the facility itself when it reports
none. Federal facilities are excluded."

### Companion tables

`tri_parent_link_marginals.parquet`, sorted by `node_id`:

| Column | Type | Meaning |
|---|---|---|
| `node_id` | String | Industry `a` |
| `n_owners` | UInt64 | `n(a)` |
| `n_parent_owners` | UInt64 | Owners in `n(a)` keyed by a parent name |
| `n_multi_industry_owners` | UInt64 | Owners in `n(a)` with `a` and another industry in the same year |
| `n_facilities` | UInt64 | Distinct TRIFDs with an eligible facility-year in `a` |
| `n_facility_years` | UInt64 | Eligible facility-years in `a` |
| `n_owners_dnb` | UInt64 | `n(a)` under the D&B sensitivity |
| `n_owners_including_federal` | UInt64 | `n(a)` under the federal sensitivity |
| `n_owners_partial` | UInt64 | Owners in `n(a)` that, in at least one year with an eligible facility-year in `a`, also had a facility-year excluded as `naics_missing`, `naics_conflict`, `naics_not_2022` or `parent_conflict` in that same year |

`n_parent_owners` lets the scoring protocol use parent-only denominators with
no rebuild.

Partial industry sets are measured per industry, not per cell, as in Stage 10.
An owner with an excluded facility-year may operate an industry that the target
cannot see. It can only be missing from some `J(a,b)`. It can never inflate
one. So no per-cell label is derived from it. An excluded facility-year belongs
to the owner key it would have had: its one standardized parent name, else
`facility:<TRIFD>`. **My call:** a `parent_conflict` facility-year belongs to
each of its named parents. So does a facility-year that is excluded for another
partial reason (`naics_missing`, `naics_conflict` or `naics_not_2022`) and names
several parents: it belongs to each standardized parent name that it lists, else
to `facility:<TRIFD>`. The reason order only classifies the facility-year. It does
not change who owns it *(owner, plan 13, 2026-11-21)*. Facility-years excluded as
`federal` are not counted here, because the federal sensitivity covers them.

`tri_parent_link_support.parquet`, one row per target cell, sorted by
`unit_a`, `unit_b`:

| Column | Type | Meaning |
|---|---|---|
| `unit_a`, `unit_b` | String | Same node IDs as the target row |
| `j_owners` | UInt64 | `J(a,b)` |
| `j_2022`, `j_2023`, `j_2024` | UInt64 | Same-year co-presence by year |
| `j_dnb` | UInt64 | `J(a,b)` under the D&B sensitivity |
| `j_including_federal` | UInt64 | `J(a,b)` under the federal sensitivity |

Cells that exist only under a sensitivity are counted in the report, not
listed.

### Validation

Beyond `validate_targets`, a family validator checks:

- Every unit is a NAICS 2022 national-industry node in the selected bundle.
- `unit_a ≠ unit_b`, and each `(a,b)` row has its `(b,a)` mirror with equal
  `n_unweighted`.
- `n_unweighted = J(a,b) ≥ 1`, and `value` equals `J(a,b) / n(a)` within
  floating tolerance.
- `J(a,b) ≤ min(n(a), n(b))`.
- The support and marginal tables agree with the target rows.

## Parent industry table (O8)

`tri_parent_industries.parquet`, one row per parent and industry, sorted by
`parent_name`, `node_id`. It covers eligible facility-years with a
`parent:` owner key only. Self-owned facilities are not parents.

| Column | Type | Meaning |
|---|---|---|
| `parent_name` | String | EPA's standardized U.S. parent name |
| `node_id` | String | NAICS 2022 national-industry node ID |
| `n_facilities` | UInt64 | Distinct TRIFDs of the parent in this industry |
| `n_facility_years` | UInt64 | Eligible facility-years |
| `f_2022`, `f_2023`, `f_2024` | UInt64 | Facilities by year |

A parent with one industry has one row. The table lists the parent's child
industries. It does not give the parent's own industry, which TRI does not
report.

## Bundle, commands and provenance

### Module and commands

**My call on names:** module `embedding_data.tri_parent_links`, run as
`uv run python -m embedding_data.tri_parent_links`. It is separate from the
frozen top-level CLI. The plan may split it into several new modules.

| Command | Network | Purpose |
|---|---|---|
| `acquire` | Yes | Download the window's U.S. basic data files |
| `import-file YEAR FILE --processed-as-of DATE` | No | Register an owner-downloaded file |
| `build RUN_ID --codes-run ID --codes-outputs-sha256 PIN --processed-as-of DATE` | No | Build one immutable bundle |
| `verify RUN_ID --outputs-sha256 PIN` | No | Authenticate the pin, then recompute and compare every table |
| `compare-runs FIRST SECOND` | No | Exact logical comparison of two bundles, omitting run ID and time |

Every command takes an explicit `--data-dir`. Every production command passes
`--data-dir /Users/lowell/Projects/embedding-data/data`. Offline commands load
no environment file, read no credential, construct no HTTP client and run no
upstream builder. Success prints one sorted JSON line. Failure prints a short,
fixed reason with the command, run ID and path, and exits 2. It never prints row
content. Unequal comparison exits 1.

### Bundle

**My call on location:** `data/derived/epa_tri/parent-links/<RUN_ID>/`.

| File | Contents |
|---|---|
| `tri_parent_links.parquet` | `targets-v1` rows (O7) |
| `tri_parent_link_marginals.parquet` | Industry marginals |
| `tri_parent_link_support.parquet` | Cell support |
| `tri_parent_industries.parquet` | Parent industries (O8) |
| `tri_facility_years.parquet` | Facility-years |
| `inputs.json` | Selection and provenance |
| `report.json` | Accounting and distributions |
| `outputs.json` | Detached inventory of the other seven files |

`outputs.json` records the byte size, SHA-256, row count and exact schema of
every Parquet, and the hashes of both other JSON files. It excludes itself. The
findings file records its detached checksum.

`inputs.json` records:

- The codes run ID, detached pin and verified inventory.
- `manifest.entry_for` citations for the three TRI files, with the snapshot
  date.
- The window and the header registry version.
- Contract versions `tri-facility-years-v1`, `tri-parent-links-v1` and
  `targets-v1`.
- Implementation hashes of the new modules and every reused module, dependency
  versions, Python version, `uv.lock` hash, execution commit and dirty flag.

`report.json` records, by reporting year:

- Rows by form type, facility-years, and facility-years by exclusion reason in
  disjoint partitions that sum to the total.
- `N` for the headline, the D&B sensitivity and the federal sensitivity.
- Parent and D&B fill rates, and the counts of standardized names with more
  than one D&B number and of D&B numbers with more than one standardized name.
- Facility-years with `flag_parent_mixed_blank`, with foreign parents and with
  secondary codes. Facility-years in territories.
- Facilities whose owner key changes across years.
- The counts of the "no parent" cases (a), (b) and (c), and partial owners.
- Standardized names that collide under case folding and whitespace collapse
  (a count only, never merged).
- Cells that exist only under a sensitivity.
- The distribution of `n_unweighted` over target rows, for O13 (the V9
  handoff), and the distributions of facilities and industries per parent.

### Run boundary and failure

- `build` stages into an exclusive `<RUN_ID>.part` and renames only after every
  check passes. An existing final or partial name fails and is never reused.
- `build` rechecks the pinned inputs and the software identity just before
  publication. Any change fails the run.
- Failure cleans only the run's own staging.
- Expected data states are retained diagnostics, not failures: excluded
  facility-years, mixed blanks and self-owned facilities.
- Changed raw bytes, a changed header, a reporting-year mismatch, row loss or
  multiplication and invalid estimates are failures.

## Verification and acceptance

### Automated tests

Write the failing tests first. Small typed frames cover:

- Facility-year reduction across Form R and Form A rows, and multi-form
  facilities.
- Each exclusion reason and its order.
- The mixed-blank parent rule and the any-form federal rule.
- "No parent" strings never forming a shared group.
- Same-year co-presence, one count per owner, mirror rows and no diagonal.
- Both sensitivity counts and their support labels.
- The three "no parent" cases (a), (b) and (c), and partial owners, including
  a `parent_conflict` facility-year that counts for each named parent.
- The O8 table, including self-owned facilities left out.
- Header refusal, reporting-year mismatch, occupied run names, changed pins
  and changed software.
- `compare-runs` equal and unequal.

**V12 extension.** A fixture chain with no network: synthetic TRI CSVs in the
recorded header layout, `import-file` into a temporary data directory, a real
Stage 4 bundle from the Stage 10 fixture helper, then `build`, `verify`, a
second `build` and `compare-runs`. **My call:** the TRI CSVs are synthetic,
with made-up D&B numbers. The fixture contains at least: a multi-form facility,
a primary-code conflict, a parent conflict, a mixed blank, a self-owned
facility, a federal facility, a code outside NAICS 2022, a D&B grouping that
differs from the name grouping, a same-year co-owned pair, a cross-year
non-pair and an RY2023 foreign parent. Fixture results are software readiness,
never benchmarks.

### Independent reconciler

`scripts/reconcile_tri_parent_links.py` is written separately from the build
modules and does not import them. It reads the three cited raw files and the
pinned Stage 4 nodes directly. It recomputes the facility-year reduction,
eligibility, `n(a)`, `J(a,b)`, `N`, both sensitivities, the partial-owner
counts and the O8 counts. It
compares them exactly with the bundle and reports equal or unequal.

### Host rule

- Run one acquisition at a time, because `manifest.append_entries` checks and
  then appends with no lock. Run one full-data build at a time.
- Before each acquisition and each full-data build, confirm with the owner that
  no other stage's acquisition or build is running, and run
  `pgrep -fl 'embedding_data|embedding-data'`. Stop if it shows another run.
- **My call: no write inside a Stage 9 freeze window.** Each go-ahead also
  confirms that no Stage 9 freeze window is open, as `CLAUDE.md` required for
  Stage 10. Stage 9's preservation check (`scripts/stage9_independent_io.py`)
  fails on any new file under `data/raw` or `data/derived` that no manifest
  append explains. A recorded TRI raw file passes it. A TRI bundle or a
  leftover `.part` written inside the window fails it. Also run
  `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`
  and stop if it prints anything.
- Each production write needs the owner's go-ahead first: each file fetch or
  import, the build, and any cleanup of a failed run's staging.

### Full-data acceptance

1. Acquire or import the three files. Record their hashes.
2. Run the preflight. Record E7–E9 in the findings file. Stop on a failed check.
3. Build the first run with a fresh ID under `/usr/bin/time -l`, to measure wall
   time and maximum RSS.
4. Verify it with its detached pin.
5. Run the independent reconciler. It must report equal.
6. Confirm preservation. Every earlier raw file is byte-identical. The manifest
   keeps its earlier bytes as a prefix. The raw audit
   (`uv run embedding-data audit --data-dir ...`) reports zero discrepancies.
   The Stage 2 summary and the Stage 4, Stage 6 and Stage 10 bundles are
   byte-identical.
7. Write `specs/naics-evaluation-data-stage-5-findings.md`: the run ID, the
   pin, the snapshot date, the wall time, maximum RSS and bundle size of the
   real run, the preflight outcomes and the main counts.

No replay build runs in this stage (O12).

## Methodological limits

- TRI is a program-selected population, mostly industrial. No product here
  represents all establishments or firms.
- A facility can contain several establishments. One primary code per facility
  hides the others. Secondary codes are diagnostics only.
- The parent is the top of the U.S. tree only. The middle of the tree is lost.
  One global firm can appear as several U.S. parents, because the foreign
  parent is not used for grouping.
- If E8 confirms that the standardized name shows the current owner, pooled
  years reflect ownership at the snapshot date, not as of each December 31. The
  D&B sensitivity count shows how much the grouping matters.
- EPA's standardization can split one parent under two names or merge two. This
  project cannot measure either. A self-owned facility that actually has a
  parent can only lower `J`.
- Codes are self-reported and unvalidated.
- `n(a)` pools presence over three years. `J(a,b)` requires the same year.
- State and municipal parents stay in, because no field marks them. Federal
  facilities are out.
- EPA revises earlier years. A later snapshot is a new run with a new pin.
- TRI parent links and ITA co-ownership measure close relations. Neither should
  judge an embedding that the other trained.
- Counts come from all filed forms, not a sample. Standard errors are `none`.

## Source spec amendment

The plan applies this amendment to
[the source spec](../embedding-evaluation-data-spec.md) and `CLAUDE.md` when the
stage ships. It follows the Stage 2 spec's amendment list.

**Always (TRI's own rows).**

- Item 3, a new R1.1 row:

  | Source | Unit | Years | Role |
  | --- | --- | --- | --- |
  | EPA Toxics Release Inventory (TRI) basic data files | Facility-year | Reporting years 2022–2024 | Industries that one U.S. parent operates together, and each parent's industries |

- Item 6, a new R7.2 row, marked *(owner, Stage 5 design, 2026-11-18;
  [stage spec](tri-parent-links.md))*:

  | Family | Built from | Units | Evaluates |
  | --- | --- | --- | --- |
  | TRI parent links | EPA TRI | industry × industry within a U.S. parent, and parent × industry | NAICS |

- **My call:** after R8.3, add: "TRI files are EPA data, in the public domain by
  default under EPA's data license. TRI-derived tables may contain facility-year
  and parent rows. They publish no Dun & Bradstreet number." The plan adds this
  only if E9 passes.

**Only if no other stage has applied them first.** Stages 5, 14 and 15 share
these. The first of them to merge applies them (roadmap, Choices made). Before
it edits, the plan checks `main`. If the source spec's introduction already
contains "Evidence sources admitted by", these are done, and the plan adds only
TRI's rows.

- Item 1 (introduction), item 2 (Core principle), and item 7 (`CLAUDE.md`,
  "from three sources"), with the Stage 2 spec's exact text.
- The wording change in item 3: "exactly three sources" becomes "three core
  sources".

Items 4 (R1.2 free account) and 5 (R7.5 published aggregates) belong to
Stages 14 and 15.

## Left to the builder

- The split of the new code into modules, and the function names.
- The exact header registry, once E7 records the headers.
- The download URL, once the plan reads the page's HTML.
- Report key names beyond those named here.
- The README section with the command contract. Run pins in README and
  `CLAUDE.md` wait for O12.
- The plan number. Several stages are planned in parallel, so take the next
  free number when the plan is written.

## Rollout and later-stage handoff

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 5 — on plan completion, tick the stage and re-validate later stages against what shipped.

- Acquisition and the preflight (full-data acceptance steps 1 and 2) come first,
  because the V12 fixture uses the header layout that E7 records. Software
  readiness (tests and the V12 fixture) then comes before the full-data build
  *(owner, plan 13, 2026-11-18)*. Do not tick Stage 5 on design or
  planning completion.
- The roadmap re-validation notes that Stage 5 did not consume the Stage 4
  concordance (see [What the design session found](#what-the-design-session-found)).
- The shipped handoff gives:
  - **O12 (TRI hardening):** the run ID, pin and snapshot date, so the replay
    build uses the same raw files and `compare-runs`.
  - **O13 (TRI minimum count):** the `n_unweighted` distribution in
    `report.json` and the `size_gate_pending` state.
  - **O17 (TRI protocol section):** the counts and marginals for any null
    model, the two sensitivity labels, the universe statement, the E8 time
    basis, and the R8.4 exclusion from training and model selection.

After the owner approves this committed spec, use a fresh session with
writing-plans against `specs/tri-parent-links.md`. This conversation is not a
dependency.
