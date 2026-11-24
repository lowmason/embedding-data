# CPS job-change flows

**Status: COMPLETE (2026-11-24)** — implemented by [plan 23](../plans/completed/23-cps-job-change-flows.md); the measured run is in the [Stage 11 findings](../naics-evaluation-data-stage-11-findings.md).

> Next step: writing-plans in a fresh session against this file. Do not acquire
> or import a reference, and do not build, before the plan exists and the owner
> gives the go-ahead for each write.

Status: the owner approved this committed spec on 2026-11-23 ("Approve the
spec"), including every call marked "My call" and the proposed refinement of
decision 5. Stage 11 design session of
[the roadmap](../naics-evaluation-data-roadmap.md), 2026-11-23. The owner made the
seven decisions below in this session. Calls marked "My call" were made while
writing this file. A builder check by a separate reviewer read the draft before
the owner did. It raised three questions, which the owner answered as decisions
5–7.

## Scope and governing contracts

Stage 11 builds the CPS job-change flows once on real data and verifies them
(outcome O16, Track G). It does four things:

1. It settles the 2026 meaning of ASEC industry code `9890`, as far as
   authoritative sources allow, and treats it and its occupation partner `9840`
   explicitly.
2. It maps CPS Census industry and occupation categories to NAICS 2022 and
   SOC 2018 candidate sets.
3. It links adjacent CPS person-months on `CPSIDV`.
4. It builds industry→industry and occupation→occupation job-change flows from
   the monthly panel and the ASEC, with weights and standard errors.

R4.3, R4.6–R4.9, R4.11, R5.1, R7.1, R7.4, R8, R9 and V11 of
[the source spec](../embedding-evaluation-data-spec.md) govern this stage. Its
amendments are listed under [Source spec amendment](#source-spec-amendment).
Section K8 of [the methodology](../evaluation-targets-methodology.md) gives the
estimands. The ACS targets spec ([Stage 9](../acs-targets.md)) is the model for
category units, evidence policies, the support and replicate tables, and the
undefined-SE rules. The TRI spec ([Stage 5](tri-parent-links.md)) is
the model for the commands, the bundle, the host rule and acceptance.

### Owner decisions (2026-11-23)

1. **Unit: Census categories** ("A: Census categories"). Every flow runs from
   one Census category to another. A companion registry gives each category's
   official NAICS 2022 or SOC 2018 candidate set. The flows carry no
   single-leaf NAICS or SOC view.
2. **ASEC flows: separate and unguarded** ("A: Separate, unguarded"). ASEC
   flows run from last year's longest job to the current job. They count only
   different categories, are labeled unguarded, are described as an upper bound
   on job change, and are never pooled with the monthly flows.
3. **`9890` and `9840`: explicit special** ("A: Explicit special"). Both keep
   their original values, rows and Census label. Their NAICS and SOC candidate
   sets are empty. They are reported apart from mapped and unparseable codes and
   never enter a headline product. Monthly `9890` is cited as settled. ASEC 2026
   `9890` is recorded as unresolved under this decision.
4. **One family, one bundle** ("Yes, approach 1"). New modules, one command
   group, one bundle. See [Approaches](#approaches).
5. **"X" occupation categories: residual with a cross-check** ("Residual +
   cross-check"). No official list names the members of the 38 categories whose
   SOC entry is an X token. Their candidates are the residual rule under
   [Candidate sets](#candidate-sets), checked against Stage 8's ACS PUMS
   "Combines" lists. Any disagreement stops the build for the owner. A
   design-time measurement led to a refinement of what counts as agreement,
   which the owner approved with this spec.
6. **Industry moves need a new employer** ("Industry needs new employer").
   Monthly industry flows count only employer changes (`EMPSAME` 01).
   Occupation flows count either guard. This amends R4.8's wording.
7. **All ASEC flows are sensitivity only** ("Sensitivity only"). Every
   employed ASEC row has `QIND`, `QOCC` and `QOCCLY` 0, so the flags give no
   allocation evidence for workers. No ASEC product has a strict version.

### Proposals played back in the session

These were played back to the owner during the session with no objection. The
owner approved them with this file.

- Measures are a pooled average total and a forward share, as in Stage 9.
- Monthly employed→employed moves with a reported change form one product.
  Same-category moves stay in it. Unemployed→employed moves form a separate
  product.
- The headline counts only codes with no allocation, edit or carry-forward flag
  at either end. Sensitivity includes the rest, with reasons kept apart.
- ASEC industry flows have no headline version, because no `QINDLY` is
  delivered. Decision 7 extends this to every ASEC flow.
- September→November 2025 links are kept as unweighted counts with a flag and
  stay out of every weighted flow.

### Out of scope

- Worker profiles, the CPS staffing check and CPS state migration (old
  Stage 12). The size gate, comparators and full eight-family V12 (old
  Stage 13). Both stay deferred until Stages 9 and 11 tick. → item:
  embedding-evaluation-data-spec-roadmap
- The CPS protocol section (O21). No flow is scored here.
- A replay build and the long-form acceptance finding. They belong to a later
  hardening outcome, as O12 and O25 did for TRI and USAspending.
- Any metro-level CPS target (R4.4).
- A canonical single-leaf view, an allocation of a category's mass over its
  candidates, or any rollup by code prefix.
- Any correction of the respondent guard (K8-Q1).

## Intent

The flows tell an embedding evaluation which industries and occupations workers
actually move between. That is observed relatedness, independent of the code
trees. R7.2 lists the family as evaluating NAICS and SOC. Stage 11 produces the
first real CPS bundle, so that O21 can decide how it is read and scored.

### Goals

- Every delivered CPS industry and occupation value is mapped, not in universe
  (`0000`) or one of the two named specials. Any other value fails the build.
- Linked pairs, guards and weights follow R4.7, R4.8 and R4.11 exactly, with the
  share of linked pairs with a usable guard reported for every product.
- Every target carries its weighted total, its forward share, its SE method,
  its unweighted count and `size_gate_pending`.
- One verified bundle with a detached pin, and a findings file with the run's
  wall time, maximum RSS and bundle size.

### Non-goals

- Transition rates out of employment, or into or out of the labor force. The
  monthly extract holds labor-force members only.
- Causal statements about why workers move.
- A minimum count. V9 sets it later from this bundle's counts.

### Anti-goals

These would make the stage a failure even if every check passed:

- A flow that counts a code difference with no reported job change as a monthly
  job change. Dependent interviewing carries codes forward, so such a difference
  is coding noise (R4.8).
- Any NAICS or SOC code assigned to `9890` or `9840`, or either code in a
  headline product.
- Pooling unguarded ASEC differences with guarded monthly changes.
- A September→November 2025 link inside a month-to-month weighted flow.
- A category mapped to one candidate by picking, truncating or guessing.
- Person-level rows leaving this machine, or any output feeding embedder
  training, curriculum, hard-negative mining or model selection (R8.4).

## What the design session found

All counts are read-only aggregates over the Stage 7 CPS Parquets
(`data/derived/cps/monthly/cps_00001.parquet`, 922,115 rows, and
`data/derived/cps/asec/cps_00002.parquet`, 276,854 rows), taken on 2026-11-23
for design. They are not benchmarks. The build remeasures them.

**Codes outside the official lists.** Every delivered value is on its list,
`0000` or one military code:

| Field | Outside the list | Rows |
| --- | --- | --- |
| Monthly `IND` | `0000` / `9890` | 3,668 / 116 |
| Monthly `OCC` | `0000` / `9840` | 3,668 / 116 |
| ASEC `IND` | `0000` / `9890` | 139,603 / 20 |
| ASEC `OCC` | `0000` / `9840` | 139,603 / 20 |
| ASEC `INDLY` | `0000` / `9890` | 136,344 / 625 |
| ASEC `OCCLY` | `0000` / `9840` | 136,344 / 625 |

The 2022 industry list has 266 codes and the 2018 occupation list has 570.
`9890` and `9840` occur on exactly the same rows. All 116 monthly rows are
`EMPSTAT` 21 (unemployed, with a last job). So in the monthly panel the pair can
only be the origin of an unemployed→employed move. In the ASEC, 277 of the 625
last-year rows are current armed-forces members (`EMPSTAT` 1, current codes
`0000`). The rest are civilians who held the code last year.

**What the sources say about `9890` and `9840`.** A research pass on 2026-11-23
read these public documents. None has been acquired yet.

| Source | `9890` | `9840` |
| --- | --- | --- |
| Census 2026 basic monthly `cps_industry_codes.csv` and `cps_occupation_codes.csv` | "Armed Forces", NAICS blank. No 9670–9870 | "Armed Forces", SOC blank. No 9800–9830 |
| Census 2025 basic record layout with code list | "Armed Forces", NAICS blank | "Armed Forces", SOC blank |
| Census 2026 ASEC technical document (`cpsmar26.pdf`) | Absent. Lists 9670–9870 for its military recodes | "Military Specific Occupations", SOC `55-0000` |
| Census 2025 ASEC technical document (`cpsmar25.pdf`) | "Military", NAICS 928110, in a list headed "Starting January 2020" | "Military Specific Occupations", SOC `55-0000` |
| Census `IndustryCodes_Jan2025.pdf` | Absent. Lists 9670–9870 | — |
| BLS 2022 Census industry list for CPS from January 2025 | "Armed Forces (last job)", "Part of 92811" | — |
| BLS 2018 Census occupation list for CPS from January 2020 | — | "Armed Forces (last job)", SOC `55-0000` |
| IPUMS CPS codes, 2020+ tab and 2025+ tab | "Armed Forces" on the 2020+ tab. Absent from the 2025+ tab | "Armed Forces" on the 2020+ tab |

So `9840` is settled for both files and both years. Monthly `9890` is settled
by the Census 2026 basic code list. No 2026 ASEC document defines `9890`, and
the `INDLY` universe is not limited to civilians, so ASEC 2026 `9890` stays
unresolved.

**Linkage and guards (monthly).** Adjacent months linked on `CPSIDV` with
`MISH` advancing by one:

- 530,017 linked one-month pairs. 508,823 are employed in both months.
- The guards read at the later month. Of the employed pairs, `EMPSAME` reports a
  different employer in 8,717, and `ACTSAME` reports changed duties in 6,247:
  14,964 guarded changes in all. 6,549 of them change industry and 8,201 change
  occupation.
- 29,761 employed pairs show a code difference with no reported change. That is
  coding noise under R4.8.
- 41,926 employed pairs have no usable guard (`EMPSAME` NIU, refused or don't
  know, or same employer with `ACTSAME` not usable).
- 5,567 pairs move from unemployed to employed. 5,214 of the origins report a
  last job.
- The 6,549 guarded industry changes fall in 3,943 origin→destination cells.
  2,704 cells hold one record, and the largest holds 777.
- 14,656 of the 14,964 guarded changes have `QIND` 0 at both ends, and 14,389
  have `QOCC` 0 at both ends.
- September→November 2025 gives 19,498 `CPSIDV` matches, all with `MISH`
  advancing by two.

**Linking weight.** IPUMS places `LNKFW1MWT` on the earlier month of a pair
("eligible to link to the next month"). Every September 2025 and September 2026
row has a null `LNKFW1MWT`, because no October follows. No earlier-month row of
a one-month pair is null. So September→November 2025 links have no linking
weight. 271,196 rows have a zero weight.

**ASEC.** 127,584 currently employed persons report a last-year job. 22,179 of
them have a different industry and 14,520 a different occupation. Every
employed ASEC row (130,865) has `QIND`, `QOCC` and `QOCCLY` 0. The allocated
values occur only on rows that are not employed or are armed forces.

**Same-employer industry differences.** 1,339 of the 6,549 guarded industry
changes come from a same-employer duty change. Industry differs in 21% of
duty-change pairs but in 0.35% of `same` pairs, which suggests re-coding
rather than a move (decision 6).

**X occupation categories.** 38 rows of the 2018 occupation list give an X
token as their SOC entry. No official list names their members (decision 5).
37 occur in the CPS data, with about 6.8% of employed weight.

**Leaf coverage (why the unit is the category).** 63 of 266 industry categories
(19% of employed `WTFINL` weight) map to exactly one six-digit NAICS 2022 code.
430 of 570 occupation categories (74%) map to exactly one detailed SOC 2018
code. A flow with both ends single-leaf keeps about 4% of industry mass.

## Approaches

1. **One family, one bundle (picked by the owner).** New modules for code
   mapping, linkage, guards, weights and SEs, flows and the bundle. One command
   group. `build` reads the Stage 7 CPS Parquets in place under the Stage 7
   run's detached pin and reuses the Stage 7 and Stage 8 list parsers unchanged.
   It matches the roadmap's "one verified CPS job-change bundle". Old Stage 12
   can import the helper modules and read the unit registry.
2. **Two bundles**, a CPS mapping bundle and then a flows bundle, as Stages 8
   and 9 split ACS. The mapping becomes reusable on its own, at the cost of two
   pins, two verifiers and two production builds. Rejected.
3. **Extend Stage 8's ACS mapping.** Ruled out, because Stage 8's modules are
   frozen and accept ACS schemes only.

## Selected inputs and trust boundary

### Inputs

| Input | Identity | Pin |
| --- | --- | --- |
| Stage 7 verification run | `stage7_ipums_verification_20261015_r2` | `db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc` |
| Stage 7 references receipt | `stage7_ipums_references_20261015_r2` | `3163968dde603ba53f807976dd09b9e40d73235a98c6f36e4e02c67ec4239c9c` |
| Stage 8 references receipt (v2/46) | `stage8_acs_references_20261018_r4` | `052135beb2e77d3cd14b4b800602be9ab36d54aaa43eaf05abffb4d5c14fd2d5` |
| Stage 8 ACS mapping run | `stage8_acs_mapping_20261018_r7` | `1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4` *(owner, plan 23, 2026-11-23)* |
| Stage 4 codes run | `stage4_v11_20261013_r2` | `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |
| Stage 11 references receipt | New, see below | Recorded at acquisition |

- **CPS microdata.** The two Stage 7-selected deliveries, `cps_00001` (monthly)
  and `cps_00002` (ASEC), read in place as their existing Parquets. `build`
  authenticates the Stage 7 pin first, then checks that each Parquet and raw
  triple matches the hashes that Stage 7's `inputs.json` and the manifest
  record. It never reconverts, re-downloads or calls IPUMS. It does not run
  Stage 7's full `verify_bundle`: authentication is the `outputs.json` hash
  check plus these file hashes, nothing more.
- **Official lists.** `census_industry_2022` from the Stage 7 receipt and
  `census_occupation_2018` from the Stage 8 v2/46 receipt. These are the full
  Census lists that R4.6 names. They supply every candidate set.
- **Cross-check evidence.** The PUMS member lists in `acs_code_lookup.parquet` of the Stage 8 mapping run, which parsed `pums_occupation_2018` of the v2/46 receipt, for the X-category cross-check only (decision 5). The run's `inputs.json` must record the receipt `stage8_acs_references_20261018_r4`. Nothing else of that run is read, and the lists supply no member. *(owner, plan 23, 2026-11-23)*
- **Classification nodes.** `naics_nodes`, `soc_nodes` and `code_paths` of the
  Stage 4 codes run. Every candidate must be a NAICS 2022 national industry or a
  SOC 2018 detailed occupation node there.
- **Documentary evidence already frozen.** `asec_2025_documentation`,
  `asec_2026_documentation`,
  `cps_jan2025_industry_documentation`,
  `cps_lnkfw1mwt`, `cps_empsame`, `cps_actsame` and `ind_2025_codes` in the
  Stage 7 receipt. The frozen `asec_2026_documentation` is byte-identical to
  the `cpsmar26.pdf` that the research pass read. The `cpsmar25.pdf` online on
  2026-11-23 differs in bytes from the frozen `asec_2025_documentation`.
  Stage 11 cites the frozen copy, whose appendix A-9 labels `9890` "Military"
  (Stage 7, V6).

### Stage 11 references

**My call:** a new reference set, acquired or imported once, with its own
receipt under `raw/references/cps-job-flows/<REFERENCE_ID>/`. It holds the
evidence for the two specials that no earlier receipt holds:

| Kind | Source |
| --- | --- |
| `cps_basic_2026_industry_codes` | `https://www2.census.gov/programs-surveys/cps/datasets/2026/basic/cps_industry_codes.csv` |
| `cps_basic_2026_occupation_codes` | `https://www2.census.gov/programs-surveys/cps/datasets/2026/basic/cps_occupation_codes.csv` |
| `cps_basic_2025_layout_codes` | `https://www2.census.gov/programs-surveys/cps/datasets/2025/basic/2025_Basic_CPS_Public_Use_Record_Layout_plus_IO_Code_list.txt` |
| `bls_cps_industry_2022` | `https://www.bls.gov/cps/2022-census-industry-titles-and-code-list.xlsx` |
| `bls_cps_occupation_2018` | `https://www.bls.gov/cps/2018-census-occupation-classification-titles-and-code-list.xlsx` |
| `ipums_cps_ind_2020_codes` | `https://cps.ipums.org/cps/codes/ind_2020_codes.shtml` |
| `ipums_cps_occ_2020_codes` | `https://cps.ipums.org/cps/codes/occ_2020_codes.shtml` |

- BLS refuses non-browser clients. When `acquire-references` is refused for a
  kind, the owner downloads it in a browser and `import-reference` records the
  exact bytes, with the import time flagged as a proxy, as TRI and Stage 7 do.
- Each original is validated on registration: the expected rows or anchors that
  carry `9890` and `9840` must be present with the labels above. A changed
  original fails and needs a new reference ID.
- Acquisition and import are production writes. Each needs the owner's
  go-ahead and the host rule below.

### Reused interfaces and frozen modules

- Frozen modules stay frozen: Stage 6 `FROZEN_MODULES` and `TARGET_MODULES`,
  the Stage 7–9 software files, `cli.py` and `code_references.py`. Stage 11 adds
  modules only.
- Reuse unchanged: `acs_code_references.parse_membership_expression` (NAICS expressions only), `manifest.entry_for`, `target_contract.validate_targets` and `write_targets`, and `ipums_weights`'s Decimal scan. Stage 11 reads the two Census list workbooks with its own readers: `ipums_references.parse_industry_list` returns no NAICS column and drops `9920`, and Stage 8's row readers are private and take Stage 8 snapshot types. `parse_industry_list` is a test cross-check only. *(owner, plan 23, 2026-11-23)* If a reused function
  cannot serve unchanged, stop and ask the owner. Never edit it.
- Stage 8 accepts ACS schemes only, and its `559830` special grants nothing to
  CPS. Stage 11 states its own scheme and specials.

## Code mapping

### Values

Every delivered `IND`, `OCC`, `INDLY` and `OCCLY` value falls in exactly one
class, decided per field:

| Class | Rule | Treatment |
| --- | --- | --- |
| Mapped | On the 2022 industry list (industry fields) or the 2018 occupation list (occupation fields) | Category unit with its candidate set |
| Not in universe | `0000` | Not a category. Excluded from every product with a counted reason |
| Special | `9890` in an industry field, `9840` in an occupation field | Category unit with empty candidates, `special_military` |
| Unparseable | Anything else | The build fails (V11) |

Values stay the delivered zero-padded four-character strings. The ASEC fields
use the 2022 industry scheme in both years, as V6 measured (R4.9). No field is
recoded because its job refers to the previous calendar year.

### Candidate sets

- Parse each list row's NAICS or SOC expression. Expand it to the set of NAICS
  2022 national industries or SOC 2018 detailed occupations it stands for, using
  the Stage 4 nodes and paths, never code prefixes.
- Record the membership type: `whole` (one finest code), `part` (part of one
  code, a `P` marker), `several` (a list of codes) or `group` (a code above the
  finest level, which expands to all its finest descendants). A row can carry more than one type. Keep them all. A row with an `exc.` clause takes its types from its positive clause and its candidates exclude the excepted codes. No type records the exclusion: the source expression stays beside the set. *(owner, plan 23, 2026-11-23)*
- An expression the parser does not support fails the build. Never truncate,
  guess or pick one side.
- Keep the source expression, the list locator and the reference ID beside each
  set.

**X occupation categories (decision 5).** 38 rows of the 2018 occupation list
give an X token as their SOC entry, for example `0960` → `13-20XX`, `8225` →
`51-4XXX` and `9760` → `53-71XX`. The list, its 2010→2018 crosswalk sheet, the
CPS basic list and the BLS list name no members. 37 of them occur in the CPS
data, with about 6.8% of employed weight.

1. **Residual rule.** Take the X rows from narrowest to widest (more fixed
   digits first). Each row's candidates are the SOC 2018 detailed codes that
   match the token as written, with each X standing for any digit, minus every
   detailed code that a non-X row claims and every code already in a narrower
   X row's residual. Two token pairs overlap (`8025`/`8225` and `8865`/`8990`),
   so the order matters. Matching uses the Stage 4 detailed nodes, not
   arithmetic on code digits.
2. **Cross-check (refinement of decision 5, approved by the owner).**
   Compare each residual with the member list for the same Census category in
   Stage 8's ACS PUMS occupation data (`pums_occupation_2018`, v2/46 receipt, as
   parsed in the Stage 8 code lookup). The PUMS list sometimes merges several
   full-Census categories into one. The check passes when the residual is not
   empty, the residual is a subset of the PUMS list, and every extra PUMS member
   is claimed by another row of the full Census list. The PUMS lists are
   evidence only and never supply members.
3. **Stop rule.** A failed check, or a delivered X category with no PUMS list,
   fails the build with a fixed reason. The owner decides each such case.
4. **Measured at design time (2026-11-23).** The refined check passes for all
   37 X categories that occur in the CPS data. 30 residuals equal their PUMS
   list exactly. 7 are strict subsets whose extra members belong to other
   Census rows: `1240`, `1970`, `3090`, `7100`, `7640`, `7750` and `8990`.
   `8865` has no PUMS list and no CPS row. Under decision 5 as first worded
   ("any disagreement stops the build"), these 7 categories, about 23,000
   monthly rows, would stop the first build.
5. **Registry.** Membership type `x_residual`, the token, the cross-check
   outcome and both locators.

**Rows with SOC `none`.** **My call:** list rows whose SOC entry is `none`
(`9830` and `9920`) are kept in the registry with status `no_soc_equivalent`
and empty candidates. A delivered value with that status fails the build. None
occurs in the selected deliveries. The industry list row `9920` has no NAICS entry. It is kept with status `no_naics_equivalent`, empty candidates and the same failing rule. *(owner, plan 23, 2026-11-23)*

### Specials

- `9890` gets the label "Armed Forces" and `9840` the label "Armed Forces",
  each with empty candidates and null nodes.
- Each special unit records its evidence status by file: `monthly`:
  `settled` (Census 2026 basic code lists). `asec_current` and
  `asec_last_year`: `settled` for `9840` (Census 2026 ASEC appendix B),
  `unresolved_owner_decision` for `9890`.
- The BLS "(last job)" equivalents (part of NAICS 92811, SOC `55-0000`) are kept
  as cited evidence only. They are never candidates.
- Specials enter sensitivity products only, flagged `special_military`. They
  never enter a strict product.
- `report.json` counts specials by field, file and year, apart from mapped and
  unparseable values. A V11 summary states zero unparseable values.

### Unit identity

**My call:** category units use the feature form that Stage 9 used, which
`targets-v1` accepts:

- `unit_a_type` and `unit_b_type`: `cps_industry_category` or
  `cps_occupation_category`.
- `unit_a` and `unit_b`: `feature:cps_industry_category:<code>` or
  `feature:cps_occupation_category:<code>`, with the delivered four-character
  code.
- `vintage`: `census-industry-2022` or `census-occupation-2018`.

The unit registry, not the flows, carries labels, candidates, membership types,
special status and evidence.

## Linkage

- Order each person's monthly records by `MISH` within `CPSIDV`. Keep `CPSIDP`
  for the linkage-rate comparison only (R4.7).
- **One-month link:** the same `CPSIDV` in consecutive delivered months, with
  `MISH` rising by one and the earlier `MISH` not 4 or 8.
- **Two-month link:** September 2025 to November 2025, the same `CPSIDV`, with
  `MISH` rising by two. It is flagged `two_month_link`. It has no linking weight,
  so it never enters a weighted flow. It is counted in diagnostics only.
- No other gap forms a link. The window starts in January 2025, so no December
  2024 to January 2025 pair can form (R4.3). The build refuses any selected
  monthly sample before January 2025, and a test proves no such pair forms.
- The linking weight is `LNKFW1MWT` on the earlier month. A one-month link with
  a null or zero weight is counted with its reason and contributes to no
  weighted flow.
- Report the number of links on `CPSIDV` and on `CPSIDP`, by month pair.
- `CPSIDV` already requires sex and race to match and age to change plausibly.
  The build does not re-check these.

## Products

### Guard (monthly employed→employed)

The guards read at the later month of a link. `EMPSAME` uses 01 = No and
02 = Yes. `ACTSAME` uses 01 = Yes and 02 = No. Freeze these codes against the
delivered DDI. An unexpected value fails the build.

Each dimension has its own guard (decision 6). Industry is a property of the
employer, so only an employer change admits an industry move.

| Later-month reading | Occupation guard | Industry guard |
| --- | --- | --- |
| `EMPSAME` 01 | `changed` (different employer) | `changed` |
| `EMPSAME` 02 and `ACTSAME` 02 | `changed` (changed duties) | `same` |
| `EMPSAME` 02 and `ACTSAME` 01 | `same` | `same` |
| `EMPSAME` 02 and `ACTSAME` 96, 97 or 99 | `unusable` | `same` |
| `EMPSAME` 96, 97 or 99 | `unusable` | `unusable` |

A pair with guard `same` and a code difference in that dimension is counted as
coding noise and excluded. Same-employer industry differences after a duty
change (1,339 at design time) are counted separately inside that noise. The
three delivered `EMPSAME` values in `MISH` 1 or 5 are kept as source exceptions
and counted. The usable-guard share is `changed` plus `same` over all eligible
employed→employed links, reported for each dimension and product.

### Product matrix

| Product | File | Pair | Eligibility | Diagonal |
| --- | --- | --- | --- | --- |
| `monthly_ee` | Monthly | Category at t → category at t+1 | One-month link, `EMPSTAT` 10 or 12 in both months, guard `changed`, positive weight | Kept |
| `monthly_ue` | Monthly | Last-job category at t → category at t+1 | One-month link, `EMPSTAT` 21 at t, 10 or 12 at t+1, positive weight | Kept |
| `asec_retro` | ASEC | `INDLY`/`OCCLY` → `IND`/`OCC` | `EMPSTAT` 10 or 12, last-year code not `0000`, the two codes differ | Absent by definition |

Each product is built twice, for industry and for occupation. Each dimension
uses its own codes and its own eligibility. `monthly_ue` needs no guard,
because the person had no job at t. `EMPSTAT` 22 (no last job) is excluded with
a counted reason.

### Evidence policies

| Policy | Rule |
| --- | --- |
| `strict` | Monthly products only. Both ends mapped (not special). `QEMPSTAT` and the dimension's own flag (`QIND` or `QOCC`) show nonallocation at both months |
| `sensitivity` | The same substantive eligibility, also admitting allocated, edited, longitudinal and unavailable flag evidence and the specials. The only policy for `asec_retro` |

- Interpret each flag through its own delivered DDI labels, per file. Monthly
  `QIND`/`QOCC` 0 is nonallocation. 2, 3, 5, 6 and 7 are edit, allocation and
  longitudinal categories. An unknown label fails rule validation.
- **ASEC (decision 7).** No `QINDLY` is delivered, and every employed ASEC row
  has `QIND`, `QOCC` and `QOCCLY` 0, so the flags give no allocation evidence
  for workers. `asec_retro` has a sensitivity version only, in both dimensions.
  `report.json` still records the ASEC flag values by `EMPSTAT`.
- A missing flag is unavailable evidence, never nonallocation.
- Sensitivity inclusion reasons are counted separately. A record may have more
  than one.

## Estimation

### Weights

Weights are the literal CSV values at factor 1 (R4.11, V7). Sum them with
Decimal arithmetic before the Float64 publication, in a fixed order.

| Product | Point weight | Divisor k |
| --- | --- | --- |
| `monthly_ee`, `monthly_ue` | `LNKFW1MWT` on the earlier month | 18 one-month link months |
| `asec_retro` | `ASECWT` | 2 (ASEC 2025 and 2026) |

**My call on k.** The 18 one-month link months are January→February through
August→September 2025 (8) and November→December 2025 through August→September
2026 (10). September 2026 has no following month. k belongs to the product, not
to a cell. The divisor list is frozen in `inputs.json`.

### Measures

For eligible records with origin category a and destination category b:

```text
total(a→b) = sum(weight × 1[a, b]) / k
denominator(a) = sum over b of total(a→b), same records and restrictions
forward_share(a→b) = total(a→b) / denominator(a)
```

Publish two measures: `average_total` (the monthly average or annual average)
and `forward_share`. A share is the ratio of pooled totals, not a mean of
period shares. Unobserved cells are absent, never zero. No share is a
probability of moving, a population-wide rate or a reverse share.

### Standard errors

- **ASEC.** The successive-difference replicate formula with `REPWTP1`–`REPWTP160`:
  `SE = sqrt((4/160) × sum over r of (θ_r − θ)²)`. Each replicate recomputes the
  whole statistic, with numerator and denominator both changing. The unnumbered
  `REPWTP` is an availability helper, never a replicate. Negative replicate
  weights are kept. `se_method` is `replicate`.
- **Monthly.** A household-cluster bootstrap, labeled approximate (R4.11).
  **My call on its design (K8-Q3 stays open):**
  - The cluster is `CPSID`, the household, across all months.
  - B = 200 replicates. Each draws households with replacement from the sorted
    list of households that contribute any eligible link to the product, using
    the standard library's `random.Random` with a fixed integer seed recorded in
    `inputs.json`. No new dependency is added. A product covers both dimensions and both policies, so the list is the union over them, with positive weight, and one set of draws serves every variant of the product. *(owner, plan 23, 2026-11-23)*
  - A replicate's weight is `LNKFW1MWT` times the household's draw count.
  - SE is the standard deviation of the B replicate statistics (divisor B − 1).
    `se_method` is `bootstrap`, and every row carries `bootstrap_approximate`.
- **Undefined estimates (as in Stage 9).** A nonpositive full-sample
  denominator gives no share. Its reason is recorded and no point is published.
  When the point is defined but any replicate ratio is undefined, keep the
  point with `se` null and `se_method` `none`, and record the reason and the
  replicate numbers. Never drop replicates or substitute another SE. A total's
  replicate is always defined.
- SEs are conditional on the mapping and the linkage. They exclude coding,
  guard and linkage error.

### Support

- `n_unweighted` counts contributing links or persons with positive weight. It
  is not divided by k.
- `n_weighted` is the cell's weighted mass divided by k.
- Every target keeps `size_gate_pending`. No minimum count is set here.

## Outputs

### Target metadata

- `source`: `cps`. `family`: `job_change_flow`.
- `universe`: product and policy, for example `monthly_ee:strict` or
  `asec_retro:sensitivity`.
- `sample_set`: `cps-basic-2025-01-to-2026-09` or `cps-asec-2025-2026`, with the
  sample IDs in the registry.
- `flags`: sorted and distinct, from a frozen registry: `size_gate_pending`
  always, `bootstrap_approximate` on monthly rows, `unguarded_upper_bound` on
  `asec_retro` rows, `special_military` on rows with a special end. Flags never
  identify a variant on their own.

### Bundle

**My call on location:** `data/derived/cps/job-flows/<RUN_ID>/`.

| File | Contents |
| --- | --- |
| `cps_job_flows.parquet` | `targets-v1` rows for all products, dimensions and policies |
| `cps_category_units.parquet` | One row per category unit: field scheme, code, label, candidates, membership types, special status and evidence by file, list locators |
| `cps_flow_support.parquet` | Cell and denominator counts and masses, by period contribution, and undefined-point reasons |
| `cps_flow_replicates.parquet` | Every replicate numerator, denominator, estimate and status, for 160 ASEC and 200 bootstrap replicates |
| `cps_flow_diagnostics.parquet` | Aggregate funnels by product, period and reason: links on `CPSIDV` and `CPSIDP`, two-month links, null and zero weights, guard states, coding noise, usable-guard share, flag evidence, specials |
| `cps_linked_pairs.parquet` | Person-level monthly links (one-month and two-month), with codes, guards, flags, weight, link type and product membership. ASEC persons are not in it *(owner, plan 23, 2026-11-23)* |
| `inputs.json` | Selected identities, pins, citations, frozen rules, registries, seed, divisors, software and dependencies |
| `report.json` | V11 summary, counts by class, eligibility funnels, usable-guard shares, the `n_unweighted` distribution for V9 |
| `outputs.json` | Detached inventory of the other eight files. Excludes itself |

- Only `cps_job_flows.parquet` uses `targets-v1`. Write it with
  `write_targets` unchanged. The other Parquets have fixed, versioned, ordered
  schemas recorded in `outputs.json`. The plan fixes their exact columns before
  the tests.
- First-exclusion funnels are disjoint and sum to source totals. Overlapping
  evidence counts are labeled as overlapping.
- `cps_linked_pairs.parquet` is IPUMS microdata. It stays on this machine and
  never enters git. Every other file is aggregate.
- `inputs.json` records each pin and verified inventory, `manifest.entry_for`
  citations, the contract versions (`cps-job-flows-v1`, `targets-v1`), and the
  hashes of the new and reused modules, dependency versions, Python version,
  `uv.lock` hash, execution commit and dirty flag. A change to any software file
  makes `verify` refuse the run.

### Commands

**My call on names:** `uv run python -m embedding_data.cps_job_flows`, separate
from the frozen top-level CLI.

| Command | Network | Purpose |
| --- | --- | --- |
| `acquire-references REFERENCE_ID` | Yes | Acquire the Stage 11 references |
| `import-reference REFERENCE_ID KIND FILE` | No | Register an owner-downloaded original |
| `build RUN_ID` with the five upstream IDs and pins and the Stage 11 references receipt ID and pin *(owner, plan 23, 2026-11-23)* | No | Build one immutable bundle |
| `verify RUN_ID --outputs-sha256 PIN` | No | Authenticate the pin, then recompute and compare every table |
| `compare-runs FIRST SECOND` | No | Exact logical comparison, omitting run ID and time |

- Every command takes an explicit `--data-dir`. Production passes
  `--data-dir /Users/lowell/Projects/embedding-data/data`.
- Only `acquire-references` uses the network. No command reads `IPUMS_API_KEY`,
  loads `.env` or constructs an IPUMS client. The offline commands construct no
  HTTP client and run no upstream builder.
- Success prints one sorted JSON line. Failure prints only `CPS job flows
  <command> failed: <reason>; run <run_id>; path <path>` and exits 2. It never
  prints row content. An unequal comparison exits 1.
- `build` stages into an exclusive `<RUN_ID>.part`, rechecks every pin and the
  software identity before publication, and renames only after every check
  passes. An existing final or partial fails. Failure cleans only the run's own
  staging.

## Verification and acceptance

### Automated tests

Write the failing tests first. Small typed frames cover:

- Every value class per field, including `0000`, both specials and an
  unparseable value that fails.
- Candidate expansion for each membership type, and an unsupported expression
  that fails.
- The X residual rule, a residual that differs from the PUMS list, an empty
  residual and a missing PUMS list, each failing with its reason.
- A delivered value whose list row has SOC `none`, which fails.
- One-month links, the `MISH` 4→5 refusal, the September→November two-month
  link, a refused pre-2025 sample and the impossible December 2024→January 2025
  pair.
- Each guard state for both dimensions, including a same-employer duty change
  that moves occupation but counts an industry difference as noise, coding
  noise, the `MISH` 1/5 exceptions and the usable-guard shares.
- `monthly_ue`, `EMPSTAT` 22 exclusion, and `asec_retro`'s off-diagonal rule.
- Strict and sensitivity policies, the missing `QINDLY` case and an unknown flag
  label that fails.
- Specials in sensitivity only.
- Pooled totals and shares with fixed divisors, Decimal sums, the ASEC replicate
  formula, the seeded bootstrap and every undefined-SE case.
- Occupied run names, changed pins, changed software, and `compare-runs` equal
  and unequal.

**Fixture chain.** With no network and no credentials: synthetic monthly and
ASEC CSV deliveries, recorded in a temporary manifest, converted by the
unchanged converter, real Stage 4 and Stage 7 bundles from the existing fixture
helpers, the Stage 11 references imported from small committed public
originals or synthetic stand-ins, then `build`, `verify`, a second `build` and
`compare-runs`. The fixture contains at least one guarded employer change, one
duty change, one coding-noise pair, one unusable guard, one unemployed→employed
move, one `9890`/`9840` origin, one September→November link and one ASEC
difference. Fixture results are software readiness, never benchmarks.

### Independent reconciler

`scripts/reconcile_cps_job_flows.py`, written apart from the build modules and
importing none of them. It reads the Stage 7 Parquets, the two Census
workbooks and the Stage 4 SOC detailed nodes directly. It recomputes the value
classes, the X residual sets, the links, both dimensions' guard states,
eligibility, every point total and share, and the ASEC replicate SEs, and
compares them exactly with the bundle. It does not recompute the bootstrap,
which shares the build's algorithm. It reports equal or unequal.

### Host rule

- Run one acquisition at a time and one full-data build at a time, across all
  sessions.
- Before every commit, full pytest run, acquisition and full-data command, run
  `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`
  and stop if it prints anything. Also run `pgrep -fl
  'embedding_data|embedding-data'` and stop if another run shows.
- Each production write needs the owner's go-ahead: each reference acquisition
  or import, the build, and any cleanup of a failed run's staging. Each
  go-ahead also confirms that no Stage 9 freeze window is open.

### Full-data acceptance

1. Acquire or import the Stage 11 references. Record the receipt pin.
2. Build the first run with a fresh ID under `/usr/bin/time -l`.
3. Verify it with its detached pin.
4. Run the independent reconciler. It must report equal.
5. Confirm preservation: every earlier raw file is byte-identical, the manifest
   keeps its earlier bytes as a prefix, the raw audit reports zero
   discrepancies, and the Stage 4, 7 and 8 bundles and the CPS Parquets are
   byte-identical.
6. Write `specs/naics-evaluation-data-stage-11-findings.md`: the run ID, the
   pin, the reference receipt, the `9890`/`9840` outcome with its sources, the
   wall time, maximum RSS and bundle size, the usable-guard shares, the
   linkage rates and the main counts.

No replay build runs in this stage.

## Methodological limits

- Industry flows see only employer changes. A transfer to another establishment
  of the same employer in a different industry is lost.
- X-category candidates rest on a residual rule and an ACS cross-check, not on a
  published CPS member list.
- ASEC flags give no allocation evidence for workers, so no ASEC flow can claim
  to be free of imputed codes.
- Dependent interviewing and the guard can miss real employer changes or report
  false ones (K8-Q1). No correction is applied.
- ASEC differences have no guard. They mix job changes with coding noise and
  miss same-category changes. They are an upper bound (K8-Q2).
- The bootstrap has no strata or PSUs. Monthly SEs may be too small.
- `LNKFW1MWT` was built for adjacent-month links of the whole population. The
  extract holds labor-force members only, so moves into or out of the labor
  force are not seen.
- `WTFINL`-based levels differ from published totals (V10). Flows inherit any
  group-specific difference.
- A category is not a NAICS or SOC code. Comparing a category with codes is the
  reader's step, through the candidate sets.
- Rotation-group and month-in-sample effects are not modeled.
- The sources disagree about `9890` in 2026. The ASEC treatment rests on the
  owner's decision, not on a document.

## Source spec amendment

The plan applies these to [the source spec](../embedding-evaluation-data-spec.md),
`CLAUDE.md` and [the methodology](../evaluation-targets-methodology.md) when the
stage ships, each marked *(owner, Stage 11 design, 2026-11-23;
[stage spec](cps-job-change-flows.md))*:

- **V11.** After the ACS `559830` exception, add: "CPS industry `9890` and
  occupation `9840` are the narrow documented armed-forces specials. Preserve
  the original values and every row, leave candidates empty and nodes null, and
  report them separately from mapped and unparseable codes. They enter no
  headline product and admit no other unsupported value."
- **R4.7.** Add: "`LNKFW1MWT` sits on the earlier month of a link. September
  2025 has none, so September-to-November 2025 links are unweighted and enter
  no weighted flow."
- **R4.8.** After "excluded.", add: "An industry move counts only when
  `EMPSAME` reports a different employer. A same-employer duty change admits an
  occupation move only."
- **R5.3.** Add: "A CPS occupation category whose SOC entry is an X token takes
  as candidates the detailed codes matching the token minus those that other
  list rows and narrower X rows claim. Each set must be a subset of the ACS
  PUMS member list, whose extra members other Census rows claim. A failed check
  fails the build."
- **R4.9.** Replace "Special-code 9890 remains outside-list, with 2026 meaning
  unresolved" with: "`9890` is the CPS Armed Forces code. Census settles it for
  the 2026 basic monthly files. No 2026 ASEC document defines it, so its ASEC
  2026 meaning stays unresolved by owner decision."
- **Methodology K8.** Point step 7 and "The measure for flows ... is not
  designed" to this spec.
- **`CLAUDE.md`.** A Stage 11 section with the commands, the bundle and the
  rules above. Run pins wait for the later hardening outcome.
- **`specs/deferred_items.md`.** Tick the `9890` item in section
  `7-ipums-extract-verification` and the old Stage 11 item, citing the findings
  file.

## Left to the builder

- The split of the new code into modules, and the function names.
- The exact ordered columns of the auxiliary Parquets and the report keys.
- The validation anchors for each Stage 11 reference.
- The README section with the command contract.
- The plan number. Several stages are planned in parallel, so take the next
  free number when the plan is written.

## Rollout and later-stage handoff

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 11

- On plan completion, tick Stage 11 and re-validate later stages against what
  shipped. Do not tick it on design or planning completion.
- Order: software readiness (tests and the fixture chain) comes first, then the
  reference acquisition, then the full-data build.
- The shipped handoff gives:
  - **A later hardening outcome:** the run ID, pin and reference receipt, so a
    replay build uses the same inputs and `compare-runs`.
  - **V9 for this family:** the `n_unweighted` distribution in `report.json` and
    the `size_gate_pending` state.
  - **O21 (CPS protocol section):** the products, policies, flags, the
    usable-guard shares, the unguarded upper-bound label, the specials and the
    R8.4 exclusion from training and model selection.
  - **Old Stage 12:** the helper modules and the unit registry.
