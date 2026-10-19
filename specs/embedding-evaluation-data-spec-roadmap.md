# Embedding evaluation data — roadmap

> For agentic workers: REQUIRED SKILL: derive-roadmap — resume via its
> reconcile step; route each unticked stage per its ROUTING line; never plan
> this document wholesale.

Source spec: `specs/embedding-evaluation-data-spec.md`. Derived 2026-10-12
against `main` at `af7bf21`, with pytest (44) and Behave (2) passing and five
live IPUMS extracts on disk (`usa_00001`–`00003`, `cps_00001`–`00002`).

Resumed 2026-10-13 after plan 4: Stages 5–13 reconciled against its
[Handoff](plans/completed/4-code-tables-ita-naics-mapping.md#handoff-to-later-stages)
and [V11 finding](findings/v11-ita-naics-mapping.md); partition retained.
The explicitly selected Stage 4 bundle is
`data/derived/codes/stage4_v11_20261013_r2/`, with `inputs.json`, `report.json`
and detached `outputs.json`; consumer contracts below cite that Handoff
(Resolved at resume, 2026-10-13).

Resumed 2026-10-14 after plan 5: Stages 6–13 reconciled against its
[Handoff](plans/completed/5-geography-hierarchy-county-reference.md#handoff-to-later-stages)
and [production finding](findings/stage-5-geography-reference-build.md);
partition retained. The selected `geography-v1` bundle is
`data/derived/geography/stage5_geography_20261014/`; its six table names,
exact schemas and verified `inputs.json`, `report.json` and detached
`outputs.json` inventories are recorded there. Common-frame references do
not settle historical compatibility or freeze future Census Current responses
(plan 5, Handoff) (Resolved at resume, 2026-10-14).

Resumed 2026-10-15 after plan 6, merged through PR #5 (`1e899dc`):
Stages 7–13 revalidated against its
[Handoff](plans/completed/6-target-contract-ita-area-mix.md#handoff-to-later-stages)
and [production finding](findings/stage-6-ita-area-mix-build.md); partition
retained. Stages 7–8 require no amendment from that Handoff. The selected
preparation is `stage6_ita_assignment_20261014_1000_csv`, with first/replay
targets `stage6_ita_area_mix_20261014_1000_csv` / `_replay`, under the explicit
root `/Users/lowell/Projects/embedding-data/data`. Exact detached pins,
inventories and frozen-evidence limits remain in those records
(plan 6, Handoff) (Resolved at resume, 2026-10-15).

Resumed 2026-10-16 after plan 7, merged through PR #6 (`ea2d19c`):
Stages 8–13 reconciled against its
[Handoff](plans/completed/7-ipums-extract-verification.md#handoff-to-later-stages),
[measured finding](findings/stage-7-ipums-extract-verification.md) and source
spec; partition retained. The selected reference is
`stage7_ipums_references_20261015_r2` (`ipums-public-references-v3`, 27
originals), with runs `stage7_ipums_verification_20261015_r2` / `_replay`.
Their detached pins, schemas and independent evidence inventories remain in
the finding. Always pass `/Users/lowell/Projects/embedding-data/data`
explicitly. Old v2 snapshots and diagnostic runs remain historical evidence
under their frozen contracts and do not satisfy the current v3 contract.
Relevant code/dependency changes require fresh measurement IDs; doc-only
commits leave frozen file hashes unchanged (plan 7, Handoff)
(Resolved at resume, 2026-10-16).

## Gap analysis

`acs` = `src/embedding_data/acs_benchmark_extract.py`, `cps` =
`src/embedding_data/cps_benchmark_extract.py`, `osha` =
`src/embedding_data/osha_benchmark_download.py`.

| Req | Verdict | Evidence | Note |
| --- | --- | --- | --- |
| R1.1 | implemented-differently | `acs:44`, `cps:52`, `osha:38` | ACS, CPS acquired; ITA acquisition is 2025 case detail, not 300A → S2 |
| R1.2 | implemented-as-specified | `acs:134`, `cps:166`, `cli.py:7`; key tests in `tests/test_acs_benchmark_extract.py`, `tests/test_cps_benchmark_extract.py` | |
| R1.3 | out-of-repo | IPUMS account; extracts delivered | Satisfied; owner confirmed registration complete 2026-10-12 |
| R1.4 | implemented-differently | raw `.csv.gz`/`.xml`/`extract.json` kept; `osha:148` | No manifest; re-run overwrites `extract.json` (`acs:148`, `cps:186`) and reconverts every `*.csv.gz` (`acs:158`, `cps:198`) → S1 |
| R2.1 | missing | `osha:38` hardcodes one case-detail CSV | → S2 |
| R2.2 | missing | no ITA targets | → S6 |
| R2.3 | missing | none found | → S2 |
| R2.4 | missing | case detail carries these fields per case, 2025 only | → S2 |
| R2.5 | missing | none found | → S4 |
| R2.6 | missing | none found | V1 → S3; build → S10 |
| R2.7 | missing | none found | V2 → S3; build → S10 |
| R2.8 | missing | none found | V3 → S3; reference → S5; assignment → S6 |
| R2.9 | missing | none found | → S2 |
| R3.1 | implemented-as-specified | `acs:44`; SAMPLE 202301, 202401 | DDI SAMPLE labels end at 2024: no 2025 ACS yet |
| R3.2 | implemented-as-specified (acquisition) | SAMPLE 202403 "2020-2024, ACS 5-year"; MULTYEAR 2020–2024 | V4 unrecorded → S7; use rule → S13 |
| R3.3 | implemented-as-specified (acquisition) | `usa_00002`, SAMPLE 202201 | Codes → S8; comparator target → S13 |
| R3.4 | implemented-as-specified | US samples only, `acs:44` | |
| R3.5 | implemented-as-specified | `acs:50`, `acs:89`, `acs:91`; every name delivered incl. 80 REPWTP | V5 unrecorded → S7 |
| R3.6 | missing | EMPSTATD, CLASSWKRD delivered | → S9 |
| R3.7 | missing | none found | → S9 |
| R3.8 | missing | QIND, QOCC delivered | → S9 |
| R3.9 | missing (string half implemented) | `acs:66` | Parser → S8 |
| R3.10 | missing | none found | → S9 |
| R3.11 | missing | none found | Crosswalks → S8; use → S9 |
| R4.1 | implemented-as-specified | `cps:84`; `tests/test_cps_properties.py`; 20 samples 2025-01…2026-09, no 2025-10 | |
| R4.2 | implemented-as-specified | `cps:49`; `cps2025_03s`, `cps2026_03s` | |
| R4.3 | implemented-differently | `cps:147`, `cps:175` | `--start` admits pre-2025 months → S1; transition guard → S11 |
| R4.4 | missing | none found | Aug–Sep 2026 months already delivered → S12 |
| R4.5 | implemented-as-specified | `cps:52`; CLASSWLY, REGION, 160 REPWTP delivered | V5 unrecorded → S7 |
| R4.6 | missing (padding half implemented) | `cps:74`, `cps:133` | Census-list mapping → S11, after V6 |
| R4.7 | missing | none found | → S11 |
| R4.8 | missing | none found | → S11 |
| R4.9 | missing | none found | V6 → S7; build → S11 |
| R4.10 | missing | none found | → S12 |
| R4.11 | missing | none found | V7 → S7; build → S11, S12 |
| R4.12 | missing (variables requested) | `cps:52` | → S12 |
| R5.1 | missing | none found | ITA → S4; ACS → S8; CPS → S11 |
| R5.2 | missing | none found | → S4 |
| R5.3 | missing | none found | → S8 |
| R5.4 | missing | none found | ITA vintages → S4; ACS 2022 comparator → S8 |
| R6.1 | missing | none found | → S5 |
| R6.2 | missing | none found | → S5 |
| R6.3 | missing | none found | V8 → S8 |
| R6.4 | missing | none found | → S5 |
| R7.1 | missing | none found | → S6 |
| R7.2 | missing | none found | All eight families; first in S6 |
| R7.3 | missing | none found | Counts → S6; gate → S13 (V9) |
| R7.4 | missing | none found | → S6 |
| R8.1 | implemented-as-specified | `.gitignore:25` | |
| R8.2 | missing | README links terms only | → S13 |
| R8.3 | implemented-as-specified | permission; nothing to build | |
| R8.4 | out-of-repo | `naics-embedder` owns training | Tuning split belongs to the successor evaluation-protocol spec |
| R9.1 | implemented-as-specified | `cli.py`; `acs:95`, `cps:123` | Names `acs`, `cps` only; `osha` → S2 amendment |
| R9.2 | implemented-as-specified | `tests/conftest.py`; suites pass offline | |
| V1–V3 | missing | no 300A data | → S3 |
| V4 | missing (evidence in hand) | `usa_00003.xml` SAMPLE labels | Unrecorded → S7 |
| V5 | missing (evidence in hand) | delivered column sets | Unrecorded; `vintage` lacks flag `QMIGRAT1` (not a requested name) → S7 |
| V6, V7 | missing | none found | → S7 |
| V8 | missing | none found | → S8 |
| V9 | missing | none found | → S13 |
| V10 | missing | none found | ITA → S2; ACS, CPS → S7 |
| V11 | missing | none found | ITA → S4; ACS → S8; CPS → S11 |
| V12 | missing | none found | Seeded S6; extended per family stage; completed S13 |
| — | in-code-but-not-in-spec | `osha` case-detail command | Kept; recorded in spec as acquired, feeding no target → S2 |
| — | in-code-but-not-in-spec | Parquet written into `data/raw` (`acs:95`, `cps:123`, `osha:113`) | Moves out of `data/raw` → S1 |
| — | in-code-but-not-in-spec | `cps --start` | Retained; R4.4 motivates later starts; floor per R4.3 → S1 |

**Owner answers to the batched questions (2026-10-12).**

- Order follows the spec's Rollout: the ITA vertical slice first, then ACS,
  then CPS.
- Case detail is kept and recorded in the spec as acquired, feeding no target.
- The seven pre-manifest raw files are backfilled. Each entry gets its
  SHA-256 and extract number. Retrieval time (file mtime) and client version
  (`uv.lock`) are flagged as proxies.
- Converted Parquet moves out of `data/raw`.

**Order versus the spec.** The order follows the spec's Rollout by owner
decision: an ITA vertical slice (S2–S6), then ACS (S7–S9), the remaining ITA
targets (S10), CPS (S11–S12), and the V9 gate (S13). The Rollout's stated
reason, registration blocking, no longer holds. Its rule that V4 and V5 run
before any IPUMS download is trusted does hold, and that rule decides several
placements:

- ACS code parsing and PUMA allocation sit in S8, after S7. S4 and S5 carry
  only what the ITA slice needs.
- V6's answer can widen the CPS code mapping, so R4.6 sits in S11, after S7.
- V3's choice decides which county reference S5 ingests.

## Stages

- [x] Stage 1: Raw provenance and safe re-runs
      Objective: Every raw file has a manifest entry, and no command can overwrite or reconvert a delivered file.
      Spec: R1.4, R1.2, R1.3, R4.3, Rollout
      Gap closed: R1.4; R4.3 (sample floor); Parquet-in-raw drift; spec staleness on R1.3 and Rollout registration
      Consumes: existing `acs`, `cps`, `osha` commands; raw files in `data/raw`
      Produces: raw-manifest writer and reader (later output manifests cite raw inputs by its hashes); derived-Parquet location outside `data/raw`; per-extract output layout safe to re-run
      Exit: manifest entries exist for all seven pre-existing raw files, with SHA-256 and extract number, and retrieval time and client version flagged as proxies; no Parquet remains under `data/raw`; a test shows a second run leaves an earlier `extract.json` and its data byte-identical; `cps --start 2024-12` exits non-zero; spec amendment records registration complete and the 2026-10-12 submissions
      ROUTING: writing-plans

      > Stage 1: COMPLETE (2026-10-12) — implemented by plan 1 (specs/plans/completed/1-raw-provenance.md). Its Handoff section names what Stages 2, 3, 4, 5, 6 and 7 consume.
      > Next: resume the roadmap.

- [x] Stage 2: ITA 300A acquisition and stacked establishment table
      Objective: Every Form 300A summary file from 2016 on is acquired and stacked into one harmonized establishment-year table.
      Spec: R2.1, R2.3, R2.4, R2.9, R1.1, R9.1, V10 (ITA)
      Gap closed: R1.1; R2.1; R2.3; R2.4; R2.9; V10 (ITA); `osha` command drift
      Consumes: Stage 1 manifest writer and derived location; `osha` helpers `make_client`, `download` (the `.part` rename) and `decode_line`, and the convert-once and recorded-file traps (plan 1, Handoff; Resolved at resume, 2026-10-12)
      Produces: stacked 300A Parquet keyed on `year_filing_for` with R2.4 columns, harmonized size codes and `naics_year`, R2.9 flags; current-year through-date in the manifest
      Exit: every year 2016–2025 appears with its raw file hashed in the manifest; size code `2` never co-occurs with `21`/`22` after harmonization; flagged rows are retained, not dropped; rows per year are compared with OSHA's published submission counts and the gaps recorded; a re-acquired current-year file is recorded as a new entry, leaving the earlier file and its entry unchanged (plan 1, Handoff; Resolved at resume, 2026-10-12); spec amendment adds `osha` to R9.1 and records case detail as acquired, feeding no target
      ROUTING: writing-plans

      > Stage 2: COMPLETE (2026-10-13) — implemented by plan 2 (specs/plans/completed/2-ita-300a-summaries.md). Its Handoff section names what Stages 3, 4, 6 and 10 consume.
      > Next: resume the roadmap.

- [x] Stage 3: ITA verification
      Objective: Settle the three open ITA facts by measurement before any ITA target is built.
      Spec: V1, V2, V3; R2.6, R2.7, R2.8; R2.3 (the "2023 data" wording; plan 2, Handoff; Resolved at resume, 2026-10-13)
      Gap closed: V1, V2, V3 (the open markers on R2.6, R2.7, R2.8)
      Consumes: Stage 1 manifest writer, and `manifest.entry_for`, which does not re-hash the file it cites (plan 1, Handoff; Resolved at resume, 2026-10-12); Stage 2 stacked table `data/derived/osha/ita_300a_summary.parquet` (`ita_summary.COLUMNS`; each row's `source_file` resolves through `manifest.entry_for`). For V2 and R2.7: `establishment_id` is present from 2016 and defined per user account, `ein` is almost all null in 2016–2018, 2021's shared record `id`s were not examined, and the "2023 data" wording of R2.3 and R2.7 predates these facts. For V1 and V3: descriptions, ZIPs and EINs are stored as delivered, and their defects were seen only in sampled rows (plan 2, Handoff; `specs/findings/v10-ita-300a-totals.md`; Resolved at resume, 2026-10-13)
      Produces: recorded decisions on R2.6 cleaning rules, R2.7 link key, R2.8 county-assignment method; official NAICS title files (2012, 2017, 2022) acquired under the manifest for V1; the manifest audit of `specs/deferred_items.md` section `1-raw-provenance`, item "Manifest audit" (plan 1, Handoff; Resolved at resume, 2026-10-12), which `build_summary_table`'s own hash check covers for the summary inputs only (plan 2, Handoff; Resolved at resume, 2026-10-13)
      Exit: a committed finding reports V1's per-year shares, V2's ID-persistence and address-match shares, and V3's match rates and county agreement; spec amendments replace the three open markers with the adopted rules; the "Manifest audit" item's Done-when holds and the item is ticked
      ROUTING: writing-plans

      > Stage 3: COMPLETE (2026-10-13) — implemented by plan 3 (specs/plans/completed/3-ita-verification.md). Its [Handoff section](plans/completed/3-ita-verification.md#handoff-to-later-stages) names what Stages 4, 5, 6, 7 and 10 consume.
      > Next: resume the roadmap.

- [x] Stage 4: Code tables and ITA NAICS mapping
      Objective: NAICS 2022 and SOC 2018 node and edge tables exist, and every ITA row has a supported canonical mapping or an explicit missing/unresolved state without imputation.
      Spec: R5.1, R5.2, R5.4, R2.5, R2.9 (industry half), V11 (ITA); stage design in `specs/completed/code-tables-ita-naics-mapping.md`
      Gap closed: R5.1 (ITA); R5.2; R5.4 (ITA vintages); R2.5; R2.9 (industry half); V11 (ITA)
      Consumes: Stage 1 manifest; Stage 2 table (`naics_code`, `naics_year`). Pre-2023 vintages are the dictionary's 2012, marked `naics_year_from_dictionary`. From 2023, coded rows with no usable vintage have a null `naics_year` and are flagged `flag_naics_year_unknown`, and 2012 codes persist in the 2024 and 2025 files. Plan 2's P8 records the filing rule's appendix versions (plan 2, Handoff; `specs/findings/v10-ita-300a-totals.md`; Resolved at resume, 2026-10-13); Stage 3 manifested 2012/2017/2022 title inputs and `ita_references` acquisition/reader/parser contracts, with title-only comparison and unknown-vintage limits (plan 3, [Handoff](plans/completed/3-ita-verification.md#handoff-to-later-stages); Resolved at resume, 2026-10-13)
      Produces: NAICS and SOC node and edge tables and their schema convention (reused by Stage 5); the candidate-set representation; 2012/2017→2022 concordance as flagged candidate sets; ITA records carrying native and canonical codes; R2.9's industry half per `specs/deferred_items.md` section `2-ita-300a-summaries`, item "Industry half of the R2.9 filing-rule flag" (plan 2, Handoff; Resolved at resume, 2026-10-13)
      Exit: V11 accounts for every ITA row by mapping status and reports unresolved counts, including unknown vintages and code/vintage mismatches; only officially supported nodes or candidate sets are asserted (R2.5; `specs/findings/stage-4-ita-code-preflight.md`; owner, at Stage 4 design, 2026-10-13); a fixture with a malformed code fails the build; no concordance relationship is resolved to one side; sectors 31–33, 44–45, and 48–49 are each one node; the "Industry half of the R2.9 filing-rule flag" item's Done-when holds and the item is ticked
      ROUTING: brainstorming

      > Stage 4: COMPLETE (2026-10-13) — implemented by plan 4 (specs/plans/completed/4-code-tables-ita-naics-mapping.md). Its [Handoff section](plans/completed/4-code-tables-ita-naics-mapping.md#handoff-to-later-stages) names what Stages 5, 6, 8, 10 and 11 consume, and revalidates all remaining stages.
      > Next: resume the roadmap.

- [x] Stage 5: Geography hierarchy and county reference
      Objective: Typed geography nodes and edges exist for both paths, together with the county-assignment reference Stage 3 chose.
      Spec: R6.1, R6.2, R6.4, R2.8 (method); stage design in `specs/completed/geography-hierarchy-county-reference.md`
      Gap closed: R6.1; R6.2; R6.4
      Consumes: Stage 1 manifest; Stage 3 adopted R2.8/R6 method and compatibility decisions, manifested 2025Q4 HUD workbook, `ita_references.import_hud`/`read_hud` and `ita_county_verification.zip_candidates` contracts, and common 2025 Census county frame (plan 3, Handoff; Resolved at resume, 2026-10-13); selected Stage 4 bundle's typed node/edge and root-through-node path conventions, with `classification_tables.forest` single-parent validation confined to classification graphs (plan 4, [Handoff](plans/completed/4-code-tables-ita-naics-mapping.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-13)
      Produces: county, state, division, region, and CBSA nodes with typed edges; full production geography and county-assignment references beyond Stage 3's verification inputs (plan 3, Handoff; Resolved at resume, 2026-10-13)
      Exit: every county-equivalent nests in exactly one state, division, and region; metropolitan and micropolitan CBSAs are both included with their types distinguished, and multi-state CBSAs appear as cross-state edges; counties outside all CBSAs carry no CBSA edge (owner, Stage 5 design, 2026-10-13); Connecticut planning regions are the county-equivalents; no Puerto Rico or island-area nodes
      ROUTING: brainstorming

> Stage 5: COMPLETE (2026-10-14) — implemented by plan 5 (specs/plans/completed/5-geography-hierarchy-county-reference.md). Its [Handoff section](plans/completed/5-geography-hierarchy-county-reference.md#handoff-to-later-stages) revalidates Stages 6–13.
> Next: resume the roadmap.

- [x] Stage 6: Target contract and ITA area-mix slice
      Objective: One ITA year runs end to end into an area-mix target in the shared output schema, with its manifest.
      Spec: R7.1, R7.2 (area mix, ITA), R7.3, R7.4, R2.2, R2.8, V12, Rollout
      Gap closed: R7.1; R7.3 (counts reported); R7.4; R2.2; R2.8; R7.2 area mix (ITA); V12 (seeded)
      Consumes: Stage 1 manifest; Stage 2 upstream summary. Each row cites its raw input by `source_file` through `manifest.entry_for`, and every `osha summary` run rebuilds the table. Flagged rows are kept, `size_class` is the one size scheme in every year, and the V10 (ITA) gaps are in `specs/findings/v10-ita-300a-totals.md` (plan 2, Handoff; Resolved at resume, 2026-10-13); Stage 3 adopted R2.8/R6/R7 decisions, verified-citation contract and `ita_verification_run` prepare/check/acquire/measure interfaces; frozen sample and request/response schemas, method-specific scope diagnostics and replay/input-hash limits for `v1_v3_20261013_scopefix` (plan 3, Handoff; Resolved at resume, 2026-10-13); selected Stage 4 bundle's separate `ita_300a_canonical.parquet` and verified inventories, preserving source values/flags, nonnull sorted finest-candidate sets, unknown-vintage/mismatch unresolved states, singleton-crosswalk provenance, nullable filing decisions and independent filing-reference flags under V11's exact schema and nominal-cycle limits (plan 4, [Handoff](plans/completed/4-code-tables-ita-naics-mapping.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-13); selected `geography-v1` Stage 5 bundle and all six table schemas/inventories in the production finding above; complete county inventory, typed administrative/CBSA paths with distinct vintages and metro/micro types, no forced CBSA state parent, and geography-specific validation; HUD eligibility from all original positive candidates before scope checks, compatible original-singleton fallback only, diagnostic maxima/ties, absent versus zero-business ZIPs and independent scope/legacy/incompatibility flags; Stage 3 exact Census-first precedence and separate delivered-state veto, with the common-frame and Census Current limits above (plan 5, [Handoff](plans/completed/5-geography-hierarchy-county-reference.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-14)
      Produces: target writer (long schema, flags, output manifest with raw hashes and code, crosswalk, and transformation versions); full-table establishment county assignment beyond Stage 3's sample (plan 3, Handoff; Resolved at resume, 2026-10-13), including Census acquisition while Stage 4 canonical data stays separate (plan 5, [Handoff](plans/completed/5-geography-hierarchy-county-reference.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-14); V12 offline contract-test harness that each later family stage extends
      Exit: area-mix Parquet for one ITA year in the R7.4 schema, every row carrying `se_method`, `n_unweighted`, `n_weighted`, and the ITA universe statement; its manifest lists the `source_file` values it read, each with its SHA-256 (plan 2, Handoff; Resolved at resume, 2026-10-13); V12 passes for this family from fixtures, offline, without credentials; no target is labeled as passing a size gate
      ROUTING: brainstorming

> Stage 6: COMPLETE (2026-10-15) — implemented by plan 6 (specs/plans/completed/6-target-contract-ita-area-mix.md). Its [Handoff section](plans/completed/6-target-contract-ita-area-mix.md#handoff-to-later-stages) names what Stages 9–13 consume.
> Next: resume the roadmap.

- [x] Stage 7: IPUMS extract verification
      Objective: The five delivered IPUMS extracts are verified before any ACS or CPS transformation reads them.
      Spec: V4, V5, V6, V7, V10 (ACS, CPS); R3.2, R3.5, R4.5, R4.9, R4.11; Design provenance (XA, XC)
      Gap closed: V4; V5; V6; V7; V10 (ACS, CPS); the open markers on R3.2, R3.5, R4.5, R4.9, R4.11
      Consumes: Stage 1 manifest and derived Parquet, with the derived layout, proxied backfill entries, `.part` interrupted deliveries, and the caution against reading the legacy `extract.json` `version` (plan 1, Handoff; `specs/deferred_items.md` section `1-raw-provenance`, item "Legacy `extract.json` version"; Resolved at resume, 2026-10-12); Stage 3 `manifest_audit.audit`/`embedding-data audit`, verified `manifest.entry_for` versus lookup-only `recorded_entry_for`, and zero-discrepancy whole-tree audit closing "Manifest audit"; V4–V7, IPUMS transformations and historical delivery/version semantics remain unverified (plan 3, Handoff; Resolved at resume, 2026-10-13)
      Produces: written finding with sample IDs, accepted names, weight-storage rule, INDLY scheme verdict, and totals gaps; the 2022 Census industry code list acquired under the manifest; script corrections if any; ACS and CPS convert-if-absent per `specs/deferred_items.md` section `1-raw-provenance`, item "ACS and CPS convert-if-absent" (plan 1, Handoff; Resolved at resume, 2026-10-12)
      Exit: finding committed; the five open markers carry verified markers citing it; XA and XC standing cites the finding (plan 1 already recorded the 2026-10-12 submissions; owner, at resume, 2026-10-12); ACS state employment and CPS monthly employment gaps against published levels are recorded, not tuned away; the "ACS and CPS convert-if-absent" item's Done-when holds and the item is ticked
      ROUTING: writing-plans

> Stage 7: COMPLETE (2026-10-15) — implemented by plan 7 (specs/plans/completed/7-ipums-extract-verification.md). Its [Handoff section](plans/completed/7-ipums-extract-verification.md#handoff-to-later-stages) names what Stages 8–13 consume.
> Next: resume the roadmap.

- [x] Stage 8: ACS codes and area allocation
      Objective: Every ACS industry and occupation value is mapped or explicitly accounted under V11, and every applicable in-scope ACS microdata area allocates to counties by population weight.
      Spec: R5.1, R5.3, R5.4 (ACS 2022 comparator), R3.9, R3.11, R6.3, V8, V11 (ACS); stage design in `specs/completed/acs-codes-area-allocation.md` (owner-approved architecture, 2026-10-16)
      Gap closed: R5.1 (ACS); R5.3; R5.4 (ACS comparator); R3.9; R3.11 (crosswalks); R6.3; V8; V11 (ACS)
      Consumes: selected Stage 4 bundle's canonical node/path tables, native/auxiliary NAICS nodes, complete four-bridge `naics_concordance.parquet`, and `naics_relationships.candidates` forward/reverse traversal with sorted finest candidates and no code-equality shortcut across vintages, weights or preferred side; its ITA source exception leaves ACS mixed-depth parsing and V11 completeness intact (plan 4, [Handoff](plans/completed/4-code-tables-ita-naics-mapping.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-13); selected Stage 5 bundle's complete `county_reference`, county nodes and typed `county_cbsa` membership, including Connecticut planning regions, both CBSA types and non-CBSA counties; `cbsa_reference.state_fips` is a member-derived set, with schemas/inventories as cited above, historical PUMA compatibility still unresolved and classification single-parent validation inapplicable (plan 5, [Handoff](plans/completed/5-geography-hierarchy-county-reference.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-14); selected Stage 7 ACS identities, ordered schemas, SAMPLE/MULTYEAR partitions and actual flag domains in `variable_inventory`, `sample_counts` and `flag_coverage`; `ipums_ddi.read_definition`/`read_ddi`, `ipums_acceptance.measure_acceptance` and `ipums_verification_run.verify_bundle`. The finding's [flag/type evidence](findings/stage-7-ipums-extract-verification.md#allocation-flags-and-actual-typedomain-traps) governs raw INDNAICS/OCCSOC lexical values and delivery/year-specific QMIGRAT1 types and missingness; unknown applicability remains unavailable. Source files stay unchanged; ACS parsing, PUMA allocation and V11 completion remain here (plan 7, [Handoff](plans/completed/7-ipums-extract-verification.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-16)
      Produces: INDNAICS and OCCSOC parser; ACS records (core, five-year, vintage) carrying native and canonical codes; residence, place-of-work, and migration PUMA→county factors; PUMA–MSA intersection weights
      Exit: V11 reports zero unparseable codes in all three ACS extracts, with the source spec's approved ACS `559830` special counted separately and retaining empty candidates; OCCSOC `X` codes record a documented reason or explicit unknown with provenance; all valid applicable in-scope PUMA, PWPUMA00, and MIGPUMA1 keys in all three extracts have complete county factors summing to 1, while documented unavailable/foreign/territory states retain separate status counts; V8's finding is recorded (owner, Stage 8 design, 2026-10-16)

> Stage 8: COMPLETE (2026-10-19) — implemented by plan 8 (specs/plans/completed/8-acs-codes-area-allocation.md). Its Handoff section names what Stages 9–13 consume.
> Next: resume the roadmap.

- [ ] Stage 9: ACS targets
      Objective: ACS staffing-pattern, area-mix, commuting, and migration targets are built in the shared schema.
      Spec: R3.6, R3.7, R3.8, R3.10, R3.11, R7.2 (staffing pattern, area mix, commuting, migration — ACS rows)
      Gap closed: R3.6; R3.7; R3.8; R3.10; R3.11 (use); R7.2 ACS rows except worker profile
      Consumes: Stage 8 parser, canonical codes, and allocation factors, preserving ambiguity, unknown-vintage and singleton-crosswalk provenance independently of candidate cardinality (plan 4, [Handoff](plans/completed/4-code-tables-ita-naics-mapping.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-13); selected Stage 5 bundle's typed relationships and rollups together with Stage 8 allocations, retaining metro/micro type and missing CBSA membership without a forced CBSA state parent (plan 5, [Handoff](plans/completed/5-geography-hierarchy-county-reference.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-14); Stage 6 `targets-v1` APIs `target_contract.TARGET_SCHEMA`, `TARGET_KEY_COLUMNS`, `validate_targets` and `write_targets(frame, destination)`, returning a serialized inventory for one sorted file in caller-owned staging; `tests.target_fixtures.run_ita_v12(data_dir, monkeypatch) -> Path` is the raw-to-target extension seam. ACS membership, eligibility, weights, allocation, estimation and uncertainty remain family work; the selected ITA example supplies no ACS defaults or outputs (plan 6, [Handoff](plans/completed/6-target-contract-ita-area-mix.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-15); Stage 7's adopted factor-1 CSV weights, per-variable exact diagnostics and annual 2023/2024 plus pooled civilian resident age-16+ ACS comparison contexts. `ipums_weights.measure_weights`/`scan_numeric_csv` provide Decimal38 scans at observed lexical scale; `ipums_conversion.decompressed_csv` owns temporary-file lifetime. Keep these scans separate from original-converter fidelity. The [V7 finding](findings/stage-7-ipums-extract-verification.md#v7-csvddiparquet-weight-interpretation) retains legitimate negative replicates and household/replicate design limits; PERWT employment agreement does not validate those designs, and missing flags remain unavailable. No estimation, allocation, replicate-SE or target helper is inherited (plan 7, [Handoff](plans/completed/7-ipums-extract-verification.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-16)
      Produces: ACS universe, pooling, replicate-SE, and allocation-flag helpers reused by Stage 12 and Stage 13
      Exit: each family is built for the civilian headline universe and the private wage-and-salary universe, in headline and allocation-included variants, with replicate SEs; area mixes use workplace geography with work-from-home excluded; no metro is assigned from MET2023 alone; V12 covers each family
      ROUTING: brainstorming

- [ ] Stage 10: ITA establishment targets
      Objective: ITA text–code pairs and co-ownership targets are built on cleaned descriptions and linked establishments.
      Spec: R2.6, R2.7, R7.2 (text–code pairs, co-ownership)
      Gap closed: R2.6; R2.7; R7.2 text–code pairs and co-ownership
      Consumes: Stage 2 table (`ein`, `company_name`); Stage 3 adopted R2.6/R2.7 decisions and `ita_verification` normalization/title/employer/linkage contracts; measured unknown-employer, padded-EIN, early-year coverage and duplicate/collision diagnostics, including missing-ID counts (plan 3, Handoff; Resolved at resume, 2026-10-13); selected Stage 4 bundle's canonical candidates and `code_paths` keyed by `node_id`, preserving singleton-crosswalk and independent filing-reference provenance; unresolved candidate unions/common ancestors remain possibilities, with unresolved text–code inclusion left to this stage's design (plan 4, [Handoff](plans/completed/4-code-tables-ita-naics-mapping.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-13); Stage 6 shared writer/V12 seam and, where needed, selected all-year `ita_county_assignments.parquet` with its exact 38-column canonical prefix and `(canonical_sha256, source_row)` identity, preserving all source positions, original strings and duplicate multiplicity. Shipped verification APIs are `ita_assignment_prepare.check_preparation`, `ita_assignment_acquire.read_evidence(...).verify()` and `ita_target_build.verify_bundle`; assignment records supply neither confirmed links nor deduplicated text pairs, leaving inclusion/linkage/V12 work here (plan 6, [Handoff](plans/completed/6-target-contract-ita-area-mix.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-15); Stage 7 revalidates the preserved Stage 2–6 source/bundle pins and existing contracts, introducing no new ITA behavior or authority to rebuild, change eligibility or amend R2/R7/V12 (plan 7, [Handoff](plans/completed/7-ipums-extract-verification.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-16)
      Produces: establishment-link table across years; text–code pair table; co-ownership target
      Exit: every pair keeps the original string, a normalized key, empty, placeholder, and copied-title flags; full 2022 paths are carried for every supported candidate without asserting a scalar canonical code or full observed path for unresolved rows (plan 4, [Handoff](plans/completed/4-code-tables-ita-naics-mapping.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-13); pairs are deduplicated on employer and normalized description; links satisfy the adopted R2.7 confirmation and ambiguity rules measured in Stage 3 (plan 3, Handoff; Resolved at resume, 2026-10-13); V12 covers both families
      ROUTING: brainstorming

- [ ] Stage 11: CPS panel linkage and job-change flows
      Objective: CPS codes map to NAICS and SOC, and job-change flows count only respondent-reported job changes.
      Spec: R4.3, R4.6, R4.7, R4.8, R4.9, R4.11, R5.1, R7.2 (job-change flows), V11 (CPS)
      Gap closed: R4.3 (transition guard); R4.6; R4.7; R4.8; R4.9; R4.11 (link weights, ASEC replicates, bootstrap); R5.1 (CPS); R7.2 job-change flows; V11 (CPS)
      Consumes: selected Stage 4 bundle's canonical NAICS/SOC node schemas, root-to-leaf paths with workbook-derived SOC parentage, and complete relationship/candidate APIs; auxiliary 2002/2007 rule references admit no additional CPS source schemes (plan 4, [Handoff](plans/completed/4-code-tables-ita-naics-mapping.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-13); Stage 6 generic schema/validator/writer and V12 extension seam, anchored by the selected immutable measured example above; CPS parsing, linkage, job-change guards, membership/support/weights/uncertainty and allocation/dependent-coding flags remain this stage's responsibility, with no inherited ITA precision rule (plan 6, [Handoff](plans/completed/6-target-contract-ita-area-mix.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-15); selected Stage 7 [IND/INDLY × 2025/2026 native-2022 matrix](findings/stage-7-ipums-extract-verification.md#v6-field--and-year-specific-asec-industry-evidence), full official 2017/2022 leaves and separately documented specials; `ipums_references.parse_industry_list`/`parse_industry_metadata` and `check_references`. The Jan-2025 Census PDF and IPUMS 2025-onward codebook support documentary adoption; machine `native_vintage` remains unknown, shared membership proves no vintage, and raw short strings stay distinct from normalized four-character storage. Preserve 9890 outside-list status and resolve its 2026 meaning through the `7-ipums-extract-verification` [deferred item](deferred_items.md#7-ipums-extract-verification--2026-10-15) before mapping. The [guard finding](findings/stage-7-ipums-extract-verification.md#job-change-guard-coverage) retains reversed EMPSAME/ACTSAME numbering, NIU/refused/unknown states and three MISH exceptions; linkage-weight gaps and WTFINL comparison limits remain in V7/V10, with October 2025 absent, never zero. No CPS parser, linkage, flow, concordance or SE helper is inherited; later-needed concordances remain candidate-set work (plan 7, [Handoff](plans/completed/7-ipums-extract-verification.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-16)
      Produces: CPS code mapping; linked person-month pairs; CPS weight and SE helpers reused by Stage 12
      Exit: V11 reports zero unparseable CPS codes; monthly and ASEC job-change flows report the share of linked pairs with a usable flag; September–November 2025 links are flagged and excluded from month-to-month rates; a test shows no December 2024 to January 2025 pair can form; bootstrap SEs are labeled approximate; V12 covers the family
      ROUTING: brainstorming

- [ ] Stage 12: Worker profiles and CPS cross-sections
      Objective: Worker profiles, the CPS staffing check, and CPS state-migration targets are built.
      Spec: R4.4, R4.10, R4.11, R4.12, R7.2 (worker profile, staffing pattern CPS check, migration CPS rows)
      Gap closed: R4.4; R4.10; R4.11 (cross-section and earner weights); R4.12; R7.2 worker profile, CPS staffing check, CPS migration
      Consumes: Stage 9 ACS helpers; Stage 11 CPS mapping and weight helpers, retaining dependent-coding, allocation and other source-imputation flags independently of candidate unanimity (plan 4, [Handoff](plans/completed/4-code-tables-ita-naics-mapping.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-13); geographic outputs through these helpers retain metro/micro type and the common-frame limits above independently of R4.4 CPS metro eligibility (plan 5, [Handoff](plans/completed/5-geography-hierarchy-county-reference.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-14); Stage 6 feature `unit_b_type`/`unit_b` syntax, sorted-key writer, metadata/SE validation and V12 extension seam; estimands, universes, selected membership, weights and uncertainty remain family work, with Stage 9/11 helpers consumed only after they ship (plan 6, [Handoff](plans/completed/6-target-contract-ita-area-mix.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-15); Stage 7 verified current/ASEC variable and weight coverage through those later helpers, with QOCCLY present/QINDLY absent and source-specific QMIGRAT1 types/domains per the [flag finding](findings/stage-7-ipums-extract-verification.md#allocation-flags-and-actual-typedomain-traps). Missing flags remain unavailable; 9890 and other special/unknown states require explicit treatment before eligibility or targets. No metro eligibility, panel-link success, job-change rate, causal result or SE is inherited from Stage 7 (plan 7, [Handoff](plans/completed/7-ipums-extract-verification.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-16)
      Produces: profile tables using the feature-for-`unit_b` schema; ASEC state-to-state flows with the job-related subset
      Exit: CPS earnings use EARNWEEK2 and HOURWAGE2 with the lowest topcode across analyzed months; ASEC flows carry replicate SEs; any CPS metro-level target refuses records outside the R4.4 rule (tested); V12 covers each family
      ROUTING: brainstorming

- [ ] Stage 13: Full build, size gate, and comparators
      Objective: The first full build sets the headline cell-count gate and adds the five-year and vintage comparators.
      Spec: V9, V12, R3.2, R3.3, R7.3, R8.2
      Gap closed: V9; V12 (complete); R3.2 (use rule); R3.3 (comparator target); R7.3 (gate); R8.2
      Consumes: every prior stage's targets and helpers (plan Handoffs); Stage 8 vintage-extract codes; selected `codes-ita-v1` Stage 4 bundle's input/output inventories and verified source/reference/software provenance, including V11's extra CLI/commit hashes; detached output checksums and logical fresh-run determinism remain distinct, with the source summary's physical hash pinned (plan 4, [Handoff](plans/completed/4-code-tables-ita-naics-mapping.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-13); selected `geography-v1` Stage 5 bundle's verified raw/software/output inventories and production finding above, keeping logical repeatability separate from immutable physical run hashes and retaining the Census Current limit; geography reference completion settles no target family, V9 gate or IPUMS/comparator verification (plan 5, [Handoff](plans/completed/5-geography-hierarchy-county-reference.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-14); selected Stage 6 preparation/first/replay pins and inventories, `ita_target_build.verify_bundle`, shared writer and seeded V12 path. Exact ordered four-table replay is separate from physical run hashes; cell counts, county eligible denominators (including zero-eligible counties) and positive true/null flag support have distinct meanings. Preserve all-year multiplicity and the separate county-2025/CBSA-July-2023/HUD-2025Q4/mutable Current frames and coverage limits. Count reporting is Stage 6's closure; V9, comparators, citations and all-eight-family V12 remain open, with ITA null SE/none and `size_gate_pending` explicit (plan 6, [Handoff](plans/completed/6-target-contract-ita-area-mix.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-15); selected Stage 7 physical inventories, exact ordered eight-table replay, independent aggregate checks and scoped V4–V7/V10 closures. `ipums_verification_run.verify_bundle(directory, data_dir, expected_outputs_sha256=...)` supplies detached trust; `compare_runs(first, second)` establishes logical repeatability only. The finding retains source versions, unknown legacy API versions, DDI/dataset/client versions and mutable publication vintages separately. These verification diagnostics establish no coverage-to-accuracy inference or R7/R8 target construction; citations, comparators, V9 and full V12 remain here, with the evaluation-training/model-selection exclusion intact (plan 7, [Handoff](plans/completed/7-ipums-extract-verification.md#handoff-to-later-stages)) (Resolved at resume, 2026-10-16)
      Produces: the headline minimum count; the complete eight-family offline contract test
      Exit: a recorded decision sets the V9 minimum from observed distributions; every five-year result sits beside its 2023–2024 counterpart; the 2022 vintage comparator is built; IPUMS citations appear in README and output manifests; V12 covers all eight families offline
      ROUTING: brainstorming

## Stage-spec stamp

Each stage spec's Rollout note carries this line, and writing-plans copies it
verbatim into the stage plan's header (for a writing-plans stage, the plan
header carries it directly):

> Roadmap: specs/embedding-evaluation-data-spec-roadmap.md, Stage N — on plan
> completion, tick the stage and re-validate later stages against what shipped.

## Completion

Retire this roadmap only after a conformance audit of the accumulated system:
re-run the gap rubric over every numbered requirement (R1.1–R9.2, V1–V12),
with evidence per verdict (implementing stage and plan, `> Deviation:` notes,
`specs/deferred_items.md` entries). Each unmet requirement either becomes a new
stage, keeping this roadmap live, or is deferred consciously with a written why.
Then move this file to `specs/completed/` beside the retired spec.
