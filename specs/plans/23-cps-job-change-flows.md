# CPS Job-Change Flows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one verified bundle of CPS industry→industry and occupation→occupation job-change flows (monthly and ASEC) from the Stage 7 CPS deliveries, with every CPS code mapped to NAICS 2022 or SOC 2018 candidate sets, and settle how `9890` and `9840` are treated (O16).

**Architecture:** A standalone command group `python -m embedding_data.cps_job_flows` (spec approach 1: one family, one bundle). New modules only. `build` reads the Stage 7 CPS Parquets in place, recovers literal Decimal weights from the raw CSVs, maps codes through new readers of two Census list workbooks, links person-months on `CPSIDV`, applies the guards, estimates totals, forward shares and SEs, and publishes an exclusive `.part` directory by rename. The module split, the bundle lifecycle and the command group copy TRI (`tri_bundle.py`, `tri_codes.py`, `tri_parent_links.py`).

**Tech Stack:** Python 3.14, Polars (lazy), Typer, httpx (reference acquisition only), fastexcel (workbook reads), standard `decimal`, `math`, `random`; pytest, hypothesis; uv.

**Spec:** `specs/cps-job-change-flows.md` (owner-approved 2026-11-23; approved text at `ac549b7`, on `main` at merge `52728aa`).

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 11 — on plan completion, tick the stage and re-validate later stages against what shipped.

Scope: O16, first build. Leaves out worker profiles, the CPS staffing check and CPS state migration (old Stage 12), the size gate, comparators and full V12 (old Stage 13), the CPS protocol section (O21), a replay build and the long-form acceptance finding, any metro-level CPS target, any canonical single-leaf view and any correction of the respondent guard (spec, Out of scope).

Process: software readiness first (Tasks 2–14, tests and the fixture chain), then the reference acquisition (Task 15), then the full-data build (Task 16) and completion (Task 17). The controller runs Tasks 15–17 itself, inline, because each needs the owner's go-ahead and a dispatched subagent cannot ask for one. Tasks 1–14 may go to subagents.

## Global Constraints

- **Numbers.** This plan is roadmap Stage 11. `CLAUDE.md` and code use the old roadmap's stage numbers. Plan 23 is this plan.
- **Roots.** `ROOT` is `/Users/lowell/Projects/embedding-data/data`. A worktree has no `data/`, so every read of existing data and every `--data-dir` uses `ROOT`. Execute on a new branch cut from `origin/main` after this plan merges, in a worktree under `.claude/worktrees/`. Never switch the main checkout's branch: it is shared with other sessions.
- **Contract versions (verbatim).** `cps-job-flows-v1` for this stage's bundle and its auxiliary Parquets, `targets-v1` for `cps_job_flows.parquet`, `cps-job-flows-references-v1` for the reference receipt.
- **Upstream identities.** Hashed against the on-disk files on 2026-11-23 while planning. Each pin is the SHA-256 of that run's `outputs.json`, or of the receipt's `receipt.json`.

  | Input | ID | Pin |
  | --- | --- | --- |
  | Stage 7 run | `stage7_ipums_verification_20261015_r2` | `db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc` |
  | Stage 7 receipt | `stage7_ipums_references_20261015_r2` | `3163968dde603ba53f807976dd09b9e40d73235a98c6f36e4e02c67ec4239c9c` |
  | Stage 8 receipt | `stage8_acs_references_20261018_r4` | `052135beb2e77d3cd14b4b800602be9ab36d54aaa43eaf05abffb4d5c14fd2d5` |
  | Stage 8 mapping run (OD1) | `stage8_acs_mapping_20261018_r7` | `1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4` |
  | Stage 4 codes run | `stage4_v11_20261013_r2` | `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |
  | Stage 11 receipt | chosen at acquisition | recorded at acquisition |

- **Deliveries.** Monthly `cps_00001` (`derived/cps/monthly/cps_00001.parquet`) and ASEC `cps_00002` (`derived/cps/asec/cps_00002.parquet`), read through the Stage 7 `inputs.json` records (`deliveries['cps/monthly']`, `deliveries['cps/asec']`: `parquet`, `parquet_record`, `raw_citations`, `ddi`). The monthly file has 20 samples: 2025-01 to 2025-09 and 2025-11 to 2026-09. October 2025 is absent. The ASEC file has March 2025 and March 2026. Row counts (922,115 and 276,854) are design-time facts, not gates.
- **Census list workbooks (originals under `ROOT/raw/`).** Industry: `references/ipums-verification/stage7_ipums_references_20261015_r2/census_industry_2022.xlsx`, sheet `'2022 Census Ind Code List '` (trailing space), columns B title, D code, E NAICS expression, read with `fastexcel` `header_row=None, dtypes='string'`. Occupation: `references/acs-mapping/stage8_acs_references_20261018_r4/census_occupation_2018.xlsx`, sheet `'2018 Census Occ Code List'`, columns B title, C code, D SOC token. A row is data when its code cell, stripped, matches `^\d{4}$`. The industry sheet has 268 data rows and 266 distinct codes. The occupation sheet has 570. 38 occupation rows have an X token and two have `none` (`9830`, `9920`). 19 industry rows carry `exc.`.
- **Value classes (spec, Code mapping).** `0000` is not in universe. `9890` in an industry field and `9840` in an occupation field are the two specials, with label `Armed Forces` and empty candidates. A value on the list is mapped. Any other value fails the build. A list row with status `no_soc_equivalent` or `no_naics_equivalent` that is delivered fails the build. Values stay delivered four-character strings: `'170'`, `' 170'` and `'0170 '` are unparseable.
- **Frozen DDI rules.** DDI category values are strings and the Parquet columns are Int64. The frozen map is `int(value)`. A delivered value outside a variable's DDI set, and a null in `EMPSTAT`, `EMPSAME`, `ACTSAME`, `MISH`, `CPSIDV` or a used flag, fail the build. Labels as delivered: `EMPSAME` `01 No`, `02 Yes`, `96 Refused`, `97 Don't know`, `99 NIU`; `ACTSAME` `01 Yes`, `02 No`, `96 Refused`, `97 Don't Know` (capital K), `99 NIU`; `EMPSTAT` `10 At work`, `12 Has job, not at work last week`, `21 Unemployed, experienced worker`, `22 Unemployed, new worker`.
- **Flag classes by label text (spec, Evidence policies; frozen per file and variable).** `No change or children or armed forces` is `nonallocation`. `Value to blank`, `Blank to value`, `Value to value` are `edited`. `Allocated`, `Value to allocated value`, `Blank to allocated value` are `allocated`. `Blank to longitudinal value` is `longitudinal`. Delivered label sets: `QEMPSTAT` 0–6 (5 is `Blank to allocated value`, 6 is `Blank to longitudinal value`), monthly `QIND` and `QOCC` 0–7 (5 is `Value to allocated value`, 7 is `Blank to longitudinal value`), ASEC `QIND`, `QOCC` 0–7 and `QOCCLY` 0–1 (`0` and `Allocated`). Any other label fails rule validation. A null flag is `unavailable`, never `nonallocation`.
- **Guards (spec, Guard).** Read at the later month. Occupation: `EMPSAME` 1 is `changed`. `EMPSAME` 2 with `ACTSAME` 2 is `changed`. `EMPSAME` 2 with `ACTSAME` 1 is `same`. `EMPSAME` 2 with `ACTSAME` 96, 97 or 99 is `unusable`. `EMPSAME` 96, 97 or 99 is `unusable`. Industry: `changed` only for `EMPSAME` 1. `same` for `EMPSAME` 2 with `ACTSAME` 1, 2 or 96/97/99, and `unusable` for `EMPSAME` 96, 97 or 99.
- **Products, policies, measures (spec).** Products `monthly_ee`, `monthly_ue`, `asec_retro`. Dimensions `industry`, `occupation`. Policies `strict` (monthly only) and `sensitivity`. Measures `average_total` and `forward_share`. `k` is 18 for monthly (one-month link months 2025-01→02 through 2025-08→09, and 2025-11→12 through 2026-08→09) and 2 for ASEC. Bootstrap `B = 200`, ASEC replicates `REPWTP1`–`REPWTP160` (never the unnumbered `REPWTP`). Bootstrap seed `20261123` (Settled Default SD4).
- **Target metadata (spec, Outputs; verbatim).** `source` `cps`, `family` `job_change_flow`, `unit_*_type` `cps_industry_category` or `cps_occupation_category`, `unit_*` `feature:<unit_type>:<code>`, `vintage` `census-industry-2022` or `census-occupation-2018`, `universe` `<product>:<policy>`, `sample_set` `cps-basic-2025-01-to-2026-09` or `cps-asec-2025-2026`, `se` null with `se_method` `none` when undefined, otherwise `bootstrap` (monthly) or `replicate` (ASEC). Flags, sorted and distinct, from a frozen registry: `size_gate_pending` always, `bootstrap_approximate` on monthly rows, `unguarded_upper_bound` on `asec_retro` rows, `special_military` on rows with a special end.
- **Paths.** Bundle `ROOT/derived/cps/job-flows/<RUN_ID>/`. References `ROOT/raw/references/cps-job-flows/<REFERENCE_ID>/`. Findings `specs/naics-evaluation-data-stage-11-findings.md`. Run and reference IDs match `[A-Za-z0-9][A-Za-z0-9_-]*`. An existing final or `.part` name fails. Build scratch is `<RUN_ID>.part/.scratch`. Verify uses a temporary directory outside `ROOT`. Both remove the decompressed CSV copies.
- **Offline and diagnostics (spec, Commands).** Only `acquire-references` uses the network. No command reads `IPUMS_API_KEY`, loads `.env` or constructs an IPUMS client. The four offline commands construct no HTTP client and run no upstream builder. Success prints one sorted JSON line. Failure prints only `CPS job flows <command> failed: <reason>; run <run_id>; path <path>` to stderr and exits 2, with `<reason>` one of `validation`, `filesystem`, `network`, `unexpected`. It never prints exception text or row content. An unequal `compare-runs` exits 1.
- **Weights (spec, Estimation).** Literal CSV values at factor 1. Sums are exact Decimal. Publication arithmetic (SD5): `total = float(S) / k` where `S` is the exact Decimal sum, `share = total_ab / total_a` in Float64, and every replicate statistic uses the same two formulas.
- **Frozen code.** Add files only. Edit no existing file under `src/`, `scripts/` or `tests/`, no `tests/conftest.py`, `pyproject.toml`, `uv.lock`, `cli.py` or `code_references.py`. Stage 6 `FROZEN_MODULES` and `TARGET_MODULES` and the Stage 7–9 software files stay frozen. Add no dependency. If a reused function cannot serve unchanged, stop and ask the owner. Tests may import the existing fixture modules (`code_fixtures`, `acs_mapping_fixtures`, `ipums_fixtures`, `vendor_link_fixtures`) and never edit them.
- **Reused unchanged.** `target_contract.validate_targets`, `write_targets`, `TARGET_SCHEMA`; `target_io.stage`, `inventory`, `verify_inventory`, `verify_raw`, `file_record`, `write_json`, `relative_file`; `manifest.entry_for`, `describe_file`, `append_entries`, `check_appendable`, `read_manifest`, `sha256_file`; `paths`; `geography_references.safe_path`, `occupied`; `osha_benchmark_download.USER_AGENT`; `ipums_weights.measure_weights`, `scan_numeric_csv`; `ipums_conversion.decompressed_csv`; `ipums_parity.compare_ordered`; `acs_code_references.parse_membership_expression` (NAICS expressions only). Stage 7 ran `measure_weights` and `scan_numeric_csv` on these two CSVs (`ipums_verification_run.py:252-256`), so they serve CPS.
- **Import closure (measured 2026-11-23).** Importing `acs_code_references` or `ipums_weights` loads the `dotenv` and `ipumspy` modules, and `ipums_references` loads `dotenv`. Loading a module reads no `.env` and builds no client. OD5 asks the owner to accept this. Either way, a test proves that no offline command calls `dotenv.load_dotenv` or `IpumsApiClient`. `SOFTWARE_FILES` is the measured import closure of `embedding_data.cps_job_flows` plus `pyproject.toml` and `uv.lock`, not a hand list.
- **Privacy.** `cps_linked_pairs.parquet` is IPUMS microdata. It stays on this machine and never enters git. Every other file is aggregate. `report.json`, logs, the findings file and failure lines hold counts and shares, never a `CPSIDV`, a `CPSID`, a household or a row. Fixtures are synthetic. No output feeds embedder training, curriculum, hard-negative mining or model selection (R8.4).
- **Research downloads are not originals.** Never import files under `/tmp/cps_research_dl/`. Reference bytes come only through `acquire-references` or an owner browser download plus `import-reference`.
- **Host rule (spec).** Run one acquisition or full-data build at a time, across all sessions. Before every commit, full pytest run, acquisition and full-data command, run `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'` and stop if it prints anything, after reading the hit: another session's shell wrapper can match. Also run `pgrep -fl 'embedding_data|embedding-data'`, show the owner its output, and stop if another run shows. Each production write needs the owner's go-ahead, which also confirms no Stage 9 freeze window is open.
- **Full pytest.** It takes about 20 minutes and hashes every `.py` file. Edit no `.py` file while it runs. Task 13's chain test carries `@pytest.mark.slow` in its own file (the marker is registered in `tests/conftest.py`, which stays untouched), so the commit hook skips it and the pre-push hook runs it.
- **Commands in steps.** `uv run --offline --locked pytest <path> -v` and `uv run --offline --locked ruff check src tests scripts`. Single quotes, 99 columns, 4-space indentation, `'''` docstrings (CPS and test files use 4 spaces).

## Owner decisions needed at plan review

Each is a default of this plan. Task 1 applies the spec edits that follow from the answers. A different answer rewrites the Task 1 block and the code task named.

- **OD1. A fifth pinned input: the Stage 8 mapping run (Tasks 1, 5).** The spec's cross-check reads "the Stage 8 code lookup", but its Inputs table lists only the v2/46 reference receipt. Default: add `stage8_acs_mapping_20261018_r7` with its pin, read only `acs_code_lookup.parquet`, and assert that its `inputs.json` records receipt `stage8_acs_references_20261018_r4`. The Inputs and Commands tables change from four to five upstream pairs. Alternative: re-parse the PUMS workbook, which needs Stage 8's private row readers.
- **OD2. Industry `9920` (Tasks 1, 4).** The list row `9920` ("Unemployed, last worked 5 years ago or earlier or never worked") has no NAICS. Default: status `no_naics_equivalent`, empty candidates, and a delivered `9920` fails the build, as the spec does for SOC `none`. No delivered value carries it.
- **OD3. New list readers instead of reuse (Tasks 1, 3, 4).** The spec names `ipums_references.parse_industry_list` and the Stage 8 occupation-list parser, and says: "If a reused function cannot serve unchanged, stop and ask the owner." Evidence: `parse_industry_list` returns code and title only, drops `9920` and returns 265 rows where the spec counts 266. Stage 8's row readers (`_industry_rows`, `_full_occupation`, `_selected_full_industry`) are private and take Stage 8 snapshot types. Default: new readers in `cps_flow_lists.py`, with `parse_industry_list` as a test cross-check only, and `parse_membership_expression` reused for NAICS expressions.
- **OD4. `exc.` rows (Tasks 1, 3).** 19 industry rows have an `exc.` clause (for example `3118 exc. 311811`, `2980`, `3875`). The four membership types do not cover an exclusion. Default: a row takes its types from its positive clause, its candidates exclude the excepted codes, and the source expression stays beside the set. No fifth type.
- **OD5. Import closure (Tasks 5, 12).** Default: reuse `parse_membership_expression` and `ipums_weights` as the spec requires, accept that their imports load the `dotenv` and `ipumspy` modules, and prove that no `.env` is read and no client is built. Alternative: copy the 40-line expression parser into `cps_flow_lists.py`, which removes `dotenv` but not `ipumspy` (`ipums_weights` needs it through `ipums_conversion`).
- **OD6. Bootstrap scope (Tasks 1, 9).** The spec draws "from the sorted list of households that contribute any eligible link to the product". A product covers both dimensions. Default: one list per product, the union of `CPSID` over links that are eligible for either dimension under sensitivity with positive weight, one fresh `random.Random(seed)`, and one set of draws for every variant of the product. Alternative: one list per product, dimension and policy, which makes strict and sensitivity draws unrelated.
- **OD7. `cps_linked_pairs.parquet` scope (Tasks 1, 10).** Default: monthly one-month and two-month links only. ASEC persons are not links, and their product membership is counted in `cps_flow_diagnostics.parquet`. Alternative: add ASEC persons with link type `asec_last_year`.

## Settled Defaults (for owner review)

- **SD1. Weights.** Decimal weights come from the raw CSV through `measure_weights` and `scan_numeric_csv`, joined to the Parquet by row position after `compare_ordered` proves all non-weight columns equal (the Stage 9 pattern, `acs_target_weights.py`). The ASEC replicate columns are read only for the eligible rows.
- **SD2. Flags.** Classified by label text (Global Constraints), not by number.
- **SD3. Funnels.** First-exclusion order, disjoint, summing to the source total. Monthly employed→employed: `weight_null`, `weight_zero`, `not_employed_both`, `code_not_in_universe`, `guard_unusable`, `no_change_reported`, `coding_noise`, then `eligible`. Monthly unemployed→employed: `weight_null`, `weight_zero`, `origin_new_worker_22`, `origin_not_unemployed_21`, `destination_not_employed`, `code_not_in_universe`, then `eligible`. Funnels count one-month links only: a two-month link enters no product and is counted in the `links` diagnostics. ASEC: `weight_nonpositive`, `not_employed`, `last_year_code_not_in_universe`, `current_code_not_in_universe`, `same_category`, then `eligible`. The usable-guard share is over employed→employed one-month links with positive weight.
- **SD4. Seed and draws.** Seed `20261123`. For each product: sorted `CPSID` list of length `H`, a fresh `random.Random(20261123)`, then for replicate `r = 1..200`, `rng.choices(range(H), k=H)` counted per index. Every full-sample cell gets all 200 (or 160) replicate rows, zero-filled where a draw missed it.
- **SD5. Publication arithmetic.** Global Constraints, Weights. The bootstrap SE is `sqrt(fsum((x - mean)² ) / (B - 1))` with `mean = fsum(x) / B`. The ASEC SE is `sqrt((4/160) × fsum((x_r − x)²))`.
- **SD6. Reference staging.** Acquired and owner-imported originals share one `.part` staging directory and one `staging-state.json`. The snapshot publishes when all seven kinds are present. A refused kind (HTTP 403) does not stop the others.

## Owner Checkpoints

1. **Plan review** (now): the owner answers OD1–OD7 and approves the Settled Defaults. Task 1 then applies the spec edits.
2. **Before Task 15:** the owner's go-ahead for the reference acquisition, and for each browser import, with the `pgrep` output shown and a confirmed closed Stage 9 freeze window (spec, Host rule).
3. **A failed anchor or a `strict_subset`/failed X check that differs from design time** (Tasks 15, 16): the owner decides. No one loosens a validator.
4. **Before Task 16:** the owner's go-ahead for the full-data build, the same checks, and a fresh run ID.
5. **Any cleanup of a failed run's staging:** its own go-ahead.

## Decisions

None. The brief took no decision after spec approval. The owner's answers to OD1–OD7 are logged here as `D<n>` lines at plan review, each as `- **D<n>** (owner, plan review, YYYY-MM-DD): <decision>. Applied in: <Task N>.`

## Review Focus

Spec silence on these inputs is not permission to break. Each line has its test in the named task.

1. **A cell that a bootstrap draw or a replicate misses.** Its numerator is 0 in that replicate and the row exists. Dropping the row shrinks the SE with no error. Test: `test_every_cell_has_every_replicate_row_zero_filled` (Task 9).
2. **The missing October 2025.** September 2025 and November 2025 are consecutive delivered months. A match with `MISH` rising by one must form no link, and one rising by two is the unweighted two-month link only. Test: `test_september_to_november_mish_plus_one_forms_no_link` (Task 6).
3. **A repeated `CPSIDV` inside one month.** A join would multiply rows and double a flow. The build fails. Test: `test_duplicate_cpsidv_within_a_month_fails` (Task 6).
4. **A delivered code that is short, padded or lower-case.** `'170'` must fail as unparseable, never join `0170` by accident. Test: `test_unpadded_code_is_unparseable` (Task 6).
5. **A person whose only evidence is allocated.** A record with `QIND` `Blank to allocated value` or a special end must reach `sensitivity` with its reason and never `strict`, even on the diagonal. Test: `test_allocated_and_special_ends_never_reach_strict` (Task 7).

## Schemas

The spec leaves the exact columns of the auxiliary tables to this plan. Every table is written with fixed ordered columns. `outputs.json` records them. Every `Parquet` here uses `cps-job-flows-v1`, except `cps_job_flows.parquet` (`targets-v1`). Periods: a monthly period is `YYYY-MM>YYYY-MM` (earlier month first), an ASEC period is `asec-YYYY`, and `all` spans every period.

**`cps_category_units.parquet`**, one row per list row (266 industry codes, 570 occupation codes) plus the two specials, sorted by `unit_type`, `code`:

| Column | Type | Meaning |
| --- | --- | --- |
| `unit` | String | `feature:<unit_type>:<code>` |
| `unit_type` | String | `cps_industry_category` or `cps_occupation_category` |
| `code` | String | Delivered four-character code |
| `vintage` | String | `census-industry-2022` or `census-occupation-2018` |
| `label` | String | Census title, stripped; `Armed Forces` for a special |
| `status` | String | `mapped`, `special_military`, `no_soc_equivalent`, `no_naics_equivalent` |
| `source_expression` | String, null | Delivered NAICS expression or SOC token |
| `membership_types` | List(String) | Sorted distinct subset of `whole`, `part`, `several`, `group`, `x_residual` |
| `candidates` | List(String) | Sorted six-digit NAICS or detailed SOC codes; empty for a special or `none` |
| `candidate_node_ids` | List(String) | Stage 4 node IDs, same order |
| `x_token` | String, null | The X token as written |
| `x_cross_check` | String, null | `equal`, `strict_subset`, `not_delivered_no_pums_list` |
| `evidence_monthly`, `evidence_asec_current`, `evidence_asec_last_year` | String, null | Specials only: `settled` or `unresolved_owner_decision` |
| `bls_evidence` | String, null | Specials only: `pt. 92811` or `55-0000`, cited, never a candidate |
| `list_locator` | String | `<kind>:<sheet>!<columns>:row=<n>` |
| `pums_locator` | String, null | X rows only |
| `reference_id` | String | Receipt that holds the list |

**`cps_flow_support.parquet`**, sorted by all columns in order:
`product` String, `dimension` String, `policy` String, `kind` String (`cell`, `denominator`, `undefined_share`), `unit_a` String, `unit_b` String null (null for `denominator`), `period` String, `n_unweighted` UInt64, `mass` Float64 (exact Decimal sum, undivided, converted with `float`), `reason` String null, `replicates` List(UInt16) null. `cell` and `denominator` rows exist for every period that contributes. An `undefined_share` row has period `all`, the full-sample mass and reason `nonpositive_denominator`, or reason `replicate_share_undefined` with the replicate numbers.

**`cps_flow_replicates.parquet`**, sorted by `product`, `dimension`, `policy`, `unit_a`, `unit_b`, `replicate`:
`product`, `dimension`, `policy`, `unit_a`, `unit_b` (String), `replicate` UInt16 (1-based), `numerator` Float64 (replicate total / k), `denominator` Float64 (replicate origin total / k), `estimate` Float64 null (`numerator / denominator`, null when the denominator is not positive), `status` String (`defined`, `denominator_nonpositive`).

**`cps_flow_diagnostics.parquet`**, sorted by all columns in order:
`topic` String (`value_class`, `links`, `weight`, `funnel`, `guard`, `evidence`, `special`), `product` String null, `dimension` String null, `policy` String null, `period` String, `reason` String, `exclusive` Boolean (true for first-exclusion funnels that sum to a source total, false for overlapping counts), `count` UInt64, `count_cpsidp` UInt64 null (only for `links`).

**`cps_linked_pairs.parquet`** (OD7), sorted by `month_a`, `link_type`, `CPSIDV`:
`CPSIDV` Int64, `CPSID` Int64, `month_a` String (`YYYY-MM`), `month_b` String, `link_type` String (`one_month`, `two_month`), `source_row_a` UInt64, `source_row_b` UInt64 (positions in the monthly Parquet), `mish_a` Int64, `mish_b` Int64, `empstat_a`, `empstat_b` Int64, `ind_a`, `ind_b`, `occ_a`, `occ_b` String, `qempstat_a`, `qempstat_b`, `qind_a`, `qind_b`, `qocc_a`, `qocc_b` Int64 null, `empsame_b`, `actsame_b` Int64, `guard_industry`, `guard_occupation` String null (null unless employed in both months), `weight_a` Float64 null, `weight_status` String (`positive`, `null`, `zero`, `not_linkable`), `products` List(String) (sorted `<product>:<dimension>:<policy>`).

**`inputs.json`** keys: `run_id`, `contracts`, `upstream` (each of the six: ID, pin, verified inventory, `manifest.entry_for` citations of every raw file read), `deliveries` (selected IDs, Parquet and raw hashes, sample IDs), `rules` (guard table, flag table, value-class rules, DDI maps, funnel order, flag registry), `divisors` (`monthly_k`, `asec_k`, the 18 link months), `bootstrap` (`seed`, `replicates`, `scope`), `software` (the measured file hashes, Python identity, installed distributions, `uv_lock_sha256`), `execution` (`commit`, `dirty`, `created_at`).

**`report.json`** keys: `schema_version`, `run_id`, `contracts`, `v11` (`unparseable_values` 0 and the fixed statement "zero unparseable CPS values"), `value_classes` (`<file>/<field>`: `mapped`, `not_in_universe`, `special`), `specials` (`<file>/<field>/<year>`), `x_categories` (counts of the three `x_cross_check` values), `linkage` (`one_month` and `two_month`, by month pair, `cpsidv` and `cpsidp` counts, and `other_gap_matches`), `weights` (`null`, `zero`, `positive` link counts), `funnels` (`<product>:<dimension>` → reason → count), `usable_guard_share` (`monthly_ee:industry` and `monthly_ee:occupation` as shares, and `monthly_ue` and `asec_retro` as the string `not_applicable`, because neither product uses a guard), `guard_source_exceptions` (`empsame_in_mish_1_or_5`), `asec_flags_by_empstat` (`<variable>` → `<EMPSTAT>` → `<value>` → count), `n_unweighted_distribution` (`<product>:<dimension>:<policy>`: `cells`, `min`, `max`, `p10`, `p25`, `p50`, `p75`, `p90`, and `at_least` with keys `1`, `2`, `5`, `10`, `20`, `30`, `50`, `100`), `tables` (`<file>`: `rows`).

## File Map

All new, under `src/embedding_data/` unless stated. Each test file sits in `tests/` as `test_<module>.py`.

| File | Responsibility | Task |
| --- | --- | --- |
| `cps_flow_references.py` | Stage 11 reference registry, validators, acquisition, import, receipt | 2 |
| `cps_flow_lists.py` | Readers of the two Census list workbooks, NAICS candidates, membership types | 3 |
| `cps_flow_units.py` | SOC candidates, X residuals, PUMS cross-check, the unit registry | 4 |
| `cps_flow_inputs.py` | Selection and authentication of the five upstreams, DDI rules, software identity | 5 |
| `cps_flow_linkage.py` | Value classes, the monthly panel, one-month and two-month links | 6 |
| `cps_flow_guards.py` | Guards, flag classes, product eligibility, evidence policies, funnels | 7 |
| `cps_flow_weights.py` | Decimal weight recovery aligned to the Parquets | 8 |
| `cps_flow_estimation.py` | Totals, shares, ASEC replicate SEs, the seeded bootstrap, undefined cases | 9 |
| `cps_flow_targets.py` | `targets-v1` rows and the four companion tables, the report | 10 |
| `cps_flow_bundle.py` | Build, verify, compare, `SOFTWARE_FILES` | 11 |
| `cps_job_flows.py` | Typer command group | 12 |
| `scripts/reconcile_cps_job_flows.py` | Independent reconciler, standard library and Polars only | 14 |
| `tests/cps_flow_fixtures.py` | Shared synthetic fixtures and the chain seed | 2, 13 |
| `README.md` (modify) | Command contract section | 12 |

### Task 1: Stage spec amendment (owner-approved at plan review)

**Files:**
- Modify: `specs/cps-job-change-flows.md` (the spec's status line, lines 1–15, stays untouched)

**Interfaces:**
- Consumes: the owner's answers to OD1–OD4, OD6 and OD7. OD5 changes no spec text.
- Produces: a spec that matches Tasks 3–10. Replace `<review date>` in each tag with the date of the owner's approval. A different owner answer rewrites the block it governs before this task runs.

- [ ] **Step 1: Apply the eight edits.** Each replaces the Old text with the New text in `specs/cps-job-change-flows.md`.

  **A1 (OD1), Inputs table.** After the row that starts `| Stage 8 references receipt (v2/46) |`, insert
  `| Stage 8 ACS mapping run | `stage8_acs_mapping_20261018_r7` | `1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4` *(owner, plan 23, <review date>)* |`

  **A2 (OD1), Cross-check evidence bullet.** Old: "`pums_occupation_2018` from the Stage 8 v2/46\n  receipt, for the X-category cross-check only (decision 5). It supplies no\n  member." New: "The PUMS member lists in `acs_code_lookup.parquet` of the Stage 8 mapping run, which parsed `pums_occupation_2018` of the v2/46 receipt, for the X-category cross-check only (decision 5). The run's `inputs.json` must record the receipt `stage8_acs_references_20261018_r4`. Nothing else of that run is read, and the lists supply no member. *(owner, plan 23, <review date>)*"

  **A3 (OD1), Commands table.** Old: "`build RUN_ID` with the four upstream IDs and pins". New: "`build RUN_ID` with the five upstream IDs and pins and the Stage 11 references receipt ID and pin *(owner, plan 23, <review date>)*".

  **A4 (OD3), Reused interfaces bullet.** Old: "Reuse unchanged, where they serve: `ipums_references.parse_industry_list`,\n  the Stage 8 occupation-list and membership-expression parsers in\n  `acs_code_references`, `manifest.entry_for`,\n  `target_contract.validate_targets` and\n  `write_targets`, and `ipums_weights`'s Decimal scan." New: "Reuse unchanged: `acs_code_references.parse_membership_expression` (NAICS expressions only), `manifest.entry_for`, `target_contract.validate_targets` and `write_targets`, and `ipums_weights`'s Decimal scan. Stage 11 reads the two Census list workbooks with its own readers: `ipums_references.parse_industry_list` returns no NAICS column and drops `9920`, and Stage 8's row readers are private and take Stage 8 snapshot types. `parse_industry_list` is a test cross-check only. *(owner, plan 23, <review date>)*" The next sentence ("If a reused function cannot serve unchanged, stop and ask the owner. Never edit it.") stays.

  **A5 (OD4), membership types.** Old: "A row can carry\n  more than one type. Keep them all." New: "A row can carry more than one type. Keep them all. A row with an `exc.` clause takes its types from its positive clause and its candidates exclude the excepted codes. No type records the exclusion: the source expression stays beside the set. *(owner, plan 23, <review date>)*"

  **A6 (OD2), Rows with SOC `none`.** After "None\noccurs in the selected deliveries." add: "The industry list row `9920` has no NAICS entry. It is kept with status `no_naics_equivalent`, empty candidates and the same failing rule. *(owner, plan 23, <review date>)*"

  **A7 (OD6), bootstrap.** Old: "list of households that contribute any eligible link to the product, using" New: "list of households that contribute any eligible link to the product (a product covers both dimensions and both policies, so the list is the union over them, with positive weight, and one set of draws serves every variant of the product), using *(owner, plan 23, <review date>)*"

  **A8 (OD7), Bundle table.** Old: "| `cps_linked_pairs.parquet` | Person-level linked pairs, with codes, guards, flags, weight, link type and product membership |" New: "| `cps_linked_pairs.parquet` | Person-level monthly links (one-month and two-month), with codes, guards, flags, weight, link type and product membership. ASEC persons are not in it *(owner, plan 23, <review date>)* |"

- [ ] **Step 2: Verify.** Run `grep -c 'owner, plan 23' specs/cps-job-change-flows.md`. Expected: `8`. Run `git diff -U0 specs/cps-job-change-flows.md | grep '^@@'`. Expected: no hunk starts before line 240.
- [ ] **Step 3: Commit** `docs(specs): amend the Stage 11 spec after plan 23 review`. The hook skips tests for a `specs/`-only commit.

### Task 2: Stage 11 references (acquire, import, validate, receipt)

**Files:**
- Create: `src/embedding_data/cps_flow_references.py`, `tests/test_cps_flow_references.py`, `tests/cps_flow_fixtures.py`

**Interfaces:**
- Consumes: `manifest`, `paths`, `target_io`, `geography_references.safe_path`/`occupied`, `osha_benchmark_download.USER_AGENT`.
- Produces (`cps_flow_references.py`):
  - `PARSER_VERSION = 'cps-job-flows-references-v1'`, `MAX_ORIGINAL_BYTES = 32 * 1024 * 1024`.
  - `@dataclass(frozen=True) class Reference: url: str; filename: str`, and `REGISTRY: dict[str, Reference]` with the seven kinds and URLs of the spec's "Stage 11 references" table. Filenames: `cps_industry_codes.csv`, `cps_occupation_codes.csv`, `2025_Basic_CPS_Public_Use_Record_Layout_plus_IO_Code_list.txt`, `2022-census-industry-titles-and-code-list.xlsx`, `2018-census-occupation-classification-titles-and-code-list.xlsx`, `ind_2020_codes.shtml`, `occ_2020_codes.shtml`.
  - `validate_original(kind: str, file: Path) -> None` (raises `ValueError`).
  - `make_client() -> httpx.Client` (`timeout=60`, `follow_redirects=False`, `trust_env=False`, `User-Agent` header).
  - `acquire(data_dir: Path, reference_id: str) -> Path`, `import_reference(data_dir: Path, reference_id: str, kind: str, original: Path) -> Path`, `check_references(data_dir: Path, reference_id: str) -> dict` (the receipt).
  - `special_evidence(receipt: dict) -> dict[str, dict]` keyed `'9890'` and `'9840'`, each `{'label': 'Armed Forces', 'monthly': 'settled', 'asec_current': ..., 'asec_last_year': ..., 'bls': ...}`. `'9840'` has `settled` for both ASEC keys and `bls` `55-0000`. `'9890'` has `unresolved_owner_decision` for both and `bls` `pt. 92811`.
- Produces (`tests/cps_flow_fixtures.py`): `no_live_clients` (autouse; makes `cps_flow_references.make_client` raise `AssertionError`, and `dotenv.load_dotenv` and `ipumspy.IpumsApiClient` raise `AssertionError('offline CPS job flows')`) and `reference_originals(directory: Path) -> dict[str, Path]`, which writes small valid synthetic originals for the seven kinds.

- [ ] **Step 1: Write the failing tests** in `tests/test_cps_flow_references.py` (import `no_live_clients` with `# noqa: F401`; patch `make_client` with `patch.object` and a `partial` that injects `httpx.MockTransport`, whose responses use `stream=httpx.ByteStream(...)`):
  - `test_registry_holds_the_seven_kinds_with_the_spec_urls`: the keys and URLs equal the spec table exactly.
  - `test_each_original_must_carry_its_anchor` (parametrized over the kinds): a valid synthetic original passes. Anchors: industry CSV (read as `utf-8-sig`, header `ROW_TYPE`, `Industry 2025 Description`, `2022 Industry Code`, `2022 NAICS Code`) needs a `detail` row with code `9890`, description `Armed Forces` and an empty NAICS cell, and no row with a code in `9670 9680 9690 9770 9780 9790 9870`. Occupation CSV (header `ROW_TYPE`, `2020 Census Public Use Occupation Code`, `2018 SOC Code`, `Description (2020 Census Occupation Code)`) needs a `detail` row with code `9840`, empty SOC and `Armed Forces`, and no code in `9800`–`9830`. The layout text needs a line matching `Armed Forces\t+9890` and a line matching `^9840\t+Armed Forces`. Each BLS workbook (all sheets, every string cell) needs one sheet row holding the code and a cell starting `Armed Forces (last job)`, plus `Part of 92811` (industry) or `55-0000` (occupation). Each IPUMS page needs `<dt>9890</dt>` or `<dt>9840</dt>` followed by `<dd>Armed Forces</dd>`. A changed label (`Military`) raises `ValueError`.
  - `test_acquire_publishes_a_manifested_snapshot_and_receipt`: seven GETs with `User-Agent` equal to `USER_AGENT`, a final directory with seven originals and `receipt.json`, eight new manifest entries (receipt entry has `client` `embedding-data` and no `source_url`), `retrieved_at_is_proxy` false, and `check_references` returns the receipt.
  - `test_refused_kind_leaves_staging_and_import_completes_it`: a 403 for `bls_cps_industry_2022` makes `acquire` raise `ValueError` naming the kind while the other six originals sit in `<id>.part` with `staging-state.json`. `import_reference` of that kind completes the snapshot with `retrieved_at_is_proxy` true, manifest `client` `manual-import` and `proxies` `['retrieved_at']`.
  - `test_import_of_a_staged_kind_and_an_occupied_final_fail`: importing a kind twice raises. An occupied final is verified, not replaced (`acquire` returns it). An occupied `.part` without state raises.
  - `test_changed_original_fails_check_and_needs_a_fresh_id`: rewriting one byte of a published original makes `check_references` raise.
  - `test_special_evidence_statuses`: `'9840'` is `settled` in `asec_current` and `asec_last_year`, `'9890'` is `unresolved_owner_decision` in both, and both are `settled` in `monthly`.
- [ ] **Step 2: Run** `uv run --offline --locked pytest tests/test_cps_flow_references.py -v`. Expected: FAIL (`ModuleNotFoundError: embedding_data.cps_flow_references`).
- [ ] **Step 3: Implement the module.** Copy the lifecycle of `ipums_references.py` (`_publish`, `check_references`, the manifest entries with `describe_file`, the receipt keys `reference_id`, `parser_version`, `originals`, `files`, `raw_citations`), but with this registry and root `raw/references/cps-job-flows/`. Differences (SD6): `acquire` and `import_reference` share one `.part` and one `staging-state.json` (per kind: `request` record and file record), so an import can finish what `acquire` began. `acquire` tries every missing kind, then raises `ValueError('refused: <kinds>')` if any failed. The snapshot publishes when all seven kinds are present. Originals above `MAX_ORIGINAL_BYTES`, a `Content-Length` mismatch and a redirect fail. Read workbooks with `fastexcel` (all sheets, string dtype).
- [ ] **Step 4: Run** the same command. Expected: all pass. Run `uv run --offline --locked ruff check src tests`.
- [ ] **Step 5: Commit** `feat(cps-flows): register, validate and receipt the Stage 11 references`.

### Task 3: Census list readers and NAICS candidate sets

**Files:**
- Create: `src/embedding_data/cps_flow_lists.py`, `tests/test_cps_flow_lists.py`
- Modify: `tests/cps_flow_fixtures.py` (add helpers)

**Interfaces:**
- Consumes: `acs_code_references.parse_membership_expression(expression: str, nodes: pl.DataFrame, paths: pl.DataFrame) -> list[str]` (reused unchanged, `nodes` needs `node_id`, `level`, `code`; `paths` needs `node_id`, `path`).
- Produces (`cps_flow_lists.py`):
  - `@dataclass(frozen=True) class ListRow: code: str; title: str; expression: str | None; locator: str`.
  - `read_industry_list(file: Path, kind: str = 'census_industry_2022') -> list[ListRow]` (266 rows, sorted by code), `read_occupation_list(file: Path, kind: str = 'census_occupation_2018') -> list[ListRow]` (570 rows, sorted by code; `expression` is the SOC token).
  - `naics_candidates(expression: str, nodes: pl.DataFrame, paths: pl.DataFrame) -> list[str]`, `membership_types(expression: str, nodes: pl.DataFrame) -> list[str]`.
- Produces (`tests/cps_flow_fixtures.py`): `industry_list_workbook(file: Path, rows: list[list[str | None]]) -> None` and `occupation_list_workbook(...)`, both through `code_fixtures.write_xlsx` with the real sheet names (`'2022 Census Ind Code List '`, `'2018 Census Occ Code List'`) and the real column layout, and `tree_frames() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]` (`naics_nodes`, `soc_nodes`, `paths` with the Stage 4 columns). The fixture tree:
  - NAICS: `21`>`211`>`2111`>`21112`>`211120`; `31-33`>`311`>`3118`>`31181`>{`311811`,`311812`,`311813`}; `3118`>`31183`>`311830`; `311`>`3114`>`31141`>`311411`; `333`>`3332`>`33324`>`333242`, and `3334`>`33341`>`333415`. Levels `sector`, `subsector`, `industry_group`, `industry`, `national_industry`.
  - SOC: `13-0000`>`13-2000`>{`13-2050`>{`13-2051`,`13-2052`,`13-2054`}, `13-2090`>`13-2099`}; `25-0000`>`25-1000`>{`25-1010`>`25-1011`, `25-1020`>`25-1021`}; `51-0000`>`51-4000`>{`51-4030`>{`51-4031`,`51-4032`}, `51-4040`>`51-4041`, `51-4090`>`51-4099`}. Levels `major`, `minor`, `broad`, `detailed`.

- [ ] **Step 1: Write the failing tests.**
  - `test_industry_reader_collapses_section_and_whitespace_duplicates`: rows in the real shape for `0770` (a section row with the title in column A and an empty column B, then a detail row with the title in column B) and `7570` (two rows whose titles differ by trailing whitespace) give one `ListRow` each with the stripped column-B title. A fixture of 268 data rows with 266 distinct codes returns 266 rows. Two rows of one code with different expressions raise `ValueError`. `9920` has `expression is None`, and the seven military codes carry `pt. 92811`.
  - `test_industry_reader_requires_the_exact_sheet_name`: a workbook whose sheet is `Fixture` raises.
  - `test_industry_reader_agrees_with_parse_industry_list`: on `tests/fixtures/acs_mapping/classification/census_industry_2022.xlsx`, the reader's `(code, title)` pairs minus `9920` equal `ipums_references.parse_industry_list(file, 2022)`. This import is for the test only.
  - `test_occupation_reader_reads_x_and_none_tokens`: tokens `13-20XX`, `51-4XXX`, `none` come back unchanged and the locator reads `census_occupation_2018:2018 Census Occ Code List!B:D:row=<n>`. A duplicate code or a token such as `13-2X54` raises.
  - `test_naics_candidates_expand_each_membership_type`: `311811` gives `['311811']`; `Part of 311` gives every 311 national industry; `3118 exc. 311811` gives `['311812', '311813', '311830']`; `Part of 31, 32, 33` gives every national industry under `31-33`; `3332, 3334` gives `['333242', '333415']`; `not a code` raises `ValueError`.
  - `test_membership_types_keep_every_type`: `311811` → `['whole']`; `311` → `['group']`; `Part of 311` → `['group', 'part']`; `3332, 3334, Part of 333` → `['group', 'part', 'several']`; `311811, 311812` → `['several']`; `3118 exc. 311811` → `['group']`.
- [ ] **Step 2: Run** `uv run --offline --locked pytest tests/test_cps_flow_lists.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement.** A row is data when its code cell, stripped, matches `^\d{4}$`. The industry title is the stripped column B of a row that has one. Rows of one code must agree on the stripped expression (null equals null) and on the title after whitespace collapse, else `ValueError`. Token shapes accepted for occupation: `^(?:\d{2}-\d{4}|\d{2}-\d{3}X|\d{2}-\d{2}XX|\d{2}-\dXXX|none)$`. `membership_types`: split the clause before ` exc. ` on commas and `and`, strip the `Part of`, `Pts.` and `pt.` markers; `part` if a marker was present, `several` if two or more tokens, `whole` if exactly one unmarked token that is a `national_industry` node, `group` if any token is not one. Return sorted.
- [ ] **Step 4: Run** the tests, then `ruff check`. Expected: pass.
- [ ] **Step 5: Commit** `feat(cps-flows): read the Census industry and occupation lists`.

### Task 4: SOC candidates, X residuals, PUMS cross-check and the unit registry

**Files:**
- Create: `src/embedding_data/cps_flow_units.py`, `tests/test_cps_flow_units.py`

**Interfaces:**
- Consumes: `cps_flow_lists.ListRow`, `naics_candidates`, `membership_types`; `cps_flow_references.special_evidence`; `tree_frames()`.
- Produces (`cps_flow_units.py`):
  - `soc_candidates(token: str, soc_nodes: pl.DataFrame, paths: pl.DataFrame) -> list[str]`: all detailed descendants of the node with that code (any level); an unknown code raises `ValueError`.
  - `x_matches(token: str, detailed_codes: list[str]) -> list[str]`: detailed codes that match the token with each `X` standing for one digit.
  - `x_residuals(rows: list[ListRow], soc_nodes, paths) -> dict[str, list[str]]`: for each X row, keyed by Census code. Order the X rows by the number of fixed digits, descending, then by token. A residual is the token's matches minus every detailed code that a non-X row claims and minus every earlier X residual.
  - `read_pums_lists(lookup_file: Path) -> dict[str, tuple[list[str], str]]`: rows with `system == 'soc'` of `acs_code_lookup.parquet`, `paired_census_code` → (`canonical_finest_candidates`, locator joined by `|`). A repeated code raises.
  - `cross_check(residuals: dict[str, list[str]], pums: dict[str, list[str]], claimed_elsewhere: dict[str, set[str]], delivered: set[str]) -> dict[str, str]`. Outcomes `equal`, `strict_subset`, `not_delivered_no_pums_list`. Fixed failure messages (`ValueError`): `x residual is empty`, `x residual is not within the PUMS list`, `x PUMS extra member is not claimed by another row`, `x category has no PUMS list`. A delivered X category with no PUMS list fails. An undelivered one with no list passes.
  - `build_units(industry: list[ListRow], occupation: list[ListRow], *, naics_nodes, soc_nodes, paths, pums: dict, delivered: dict[str, set[str]], evidence: dict[str, dict], references: dict[str, str]) -> pl.DataFrame`: the `cps_category_units.parquet` frame with the ordered schema of the Schemas section. `delivered` has keys `industry` and `occupation`. `references` has `industry`, `occupation` and `special` receipt IDs.

- [ ] **Step 1: Write the failing tests** (fixture tree; the occupation rows are `ListRow`s):
  - `test_x_matches_use_detailed_nodes_only`: `51-403X` matches `['51-4031', '51-4032']` and `51-4XXX` matches all of `51-4031`, `51-4032`, `51-4041`, `51-4099`.
  - `test_residuals_order_narrow_before_wide_and_subtract_claims`: rows `8025` `51-403X`, `8225` `51-4XXX`, and a non-X row `7000` `51-4040` claim. Residual `8025` is `['51-4031', '51-4032']` and residual `8225` is `['51-4099']`. The two sets and the claim are disjoint.
  - `test_broad_and_minor_tokens_claim_all_detailed_descendants`: a non-X row with `25-1000` claims `25-1011` and `25-1021`, so an X row `25-10XX` leaves an empty residual and fails the check with `x residual is empty`.
  - `test_cross_check_outcomes`: equal list gives `equal`. A PUMS list with one extra member claimed by another row gives `strict_subset`. An undelivered X category with no PUMS list gives `not_delivered_no_pums_list`.
  - `test_cross_check_failures_have_fixed_reasons`: each of the four messages, by a residual that is empty, a residual member missing from the PUMS list, an extra PUMS member that no row claims, and a delivered category without a list.
  - `test_read_pums_lists_reads_only_soc_rows`: a frame with a NAICS row and two SOC rows returns the two; a repeated `paired_census_code` raises.
  - `test_registry_statuses_and_specials`: `9830` and `9920` (occupation) are `no_soc_equivalent` with empty candidates, industry `9920` is `no_naics_equivalent` (OD2), and the two extra rows (`9890` industry, `9840` occupation) are `special_military` with label `Armed Forces`, empty candidates, `evidence_monthly` `settled`, ASEC evidence per `special_evidence` and `bls_evidence` `pt. 92811` or `55-0000`.
  - `test_registry_schema_order_and_unit_strings`: columns and dtypes equal the Schemas section exactly. `unit` is `feature:cps_industry_category:0170` style. Rows are sorted by `unit_type`, `code`. A non-X SOC token for a detailed node has types `['whole']`, a broad one `['group']`, an X row `['x_residual']` with `x_token` set.
  - `test_candidates_must_be_stage4_nodes`: an expression that expands to a code missing from the nodes raises `ValueError`.
- [ ] **Step 2: Run** `uv run --offline --locked pytest tests/test_cps_flow_units.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement.** Claims of non-X rows come from `soc_candidates`. Never use arithmetic on code digits for membership: X matching tests the Stage 4 detailed node codes. `candidate_node_ids` come from the node frames by code. Industry rows use `naics_candidates` and `membership_types` (OD4). A candidate must be a `national_industry` or `detailed` node.
- [ ] **Step 4: Run** the tests, then `ruff check`. Expected: pass.
- [ ] **Step 5: Commit** `feat(cps-flows): derive category candidates, X residuals and the unit registry`.

### Task 5: Select and authenticate the upstreams; freeze the DDI rules

**Files:**
- Create: `src/embedding_data/cps_flow_inputs.py`, `tests/test_cps_flow_inputs.py`
- Modify: `tests/cps_flow_fixtures.py` (add `seed_upstreams`)

**Interfaces:**
- Consumes: `target_io.file_record`/`verify_raw`/`relative_file`, `manifest.sha256_file`, `cps_flow_references.check_references`.
- Produces (`cps_flow_inputs.py`):
  - `@dataclass(frozen=True) class InputRequest` with twelve `str` fields in this order: `stage7_run`, `stage7_outputs_sha256`, `stage7_receipt`, `stage7_receipt_sha256`, `stage8_receipt`, `stage8_receipt_sha256`, `stage8_mapping_run`, `stage8_mapping_outputs_sha256`, `codes_run`, `codes_outputs_sha256`, `cps_receipt`, `cps_receipt_sha256`.
  - `@dataclass(frozen=True) class Delivery: delivery_id: str; parquet: Path; parquet_record: dict; csv_gz: Path; ddi: dict; raw_citations: list[dict]`.
  - `@dataclass(frozen=True) class SelectedInputs` with `data_dir`, `request`, `monthly: Delivery`, `asec: Delivery`, `industry_workbook: Path`, `occupation_workbook: Path`, `pums_lookup: Path`, `naics_nodes: Path`, `soc_nodes: Path`, `code_paths: Path`, `cps_receipt: dict`, `provenance: dict` (what `inputs.json` records under `upstream` and `deliveries`), and `verify(self) -> None` (reselects and refuses any difference).
  - `select_inputs(data_dir: Path, request: InputRequest) -> SelectedInputs`.
  - `DDI_LABELS: dict[str, dict[str, dict[int, str]]]` (file `monthly` or `asec` → variable → int value → delivered label, for `EMPSTAT`, `EMPSAME`, `ACTSAME`, `QEMPSTAT`, `QIND`, `QOCC`, and `QOCCLY` in ASEC), `FLAG_CLASS_BY_LABEL: dict[str, str]` (the four classes of Global Constraints), and `check_ddi(file: str, ddi: dict) -> dict` (verifies every frozen label set against the delivered DDI, converting string values with `int`, and returns the rules recorded in `inputs.json`).
- Produces (`tests/cps_flow_fixtures.py`): `seed_upstreams(tmp_path: Path, *, monthly: list[dict], asec: list[dict]) -> SeededUpstreams` (fields `data_dir`, `request`, `reference_id`) and `monthly_row(**fields) -> dict`, `asec_row(**fields) -> dict`, which fill every column of the two Parquets with neutral defaults. The seed writes hand-made upstreams in the production conventions, so the tests stay fast (the real chain is Task 13):
  - Two CPS raw triples (`extract.json`, `.xml` with the real DDI labels, `.csv.gz` with the weights as decimal text) under `raw/cps/<set>/cps_0000N/`, recorded in the manifest, and Parquets converted with `ipums_conversion.convert(..., 'cps')`.
  - A Stage 7 run directory with `inputs.json` (`format_version` `ipums-verification-v1`, `run_id`, `references` with `reference_id`/`receipt`/`receipt_citation`, `deliveries` for `cps/monthly` and `cps/asec` with `delivery_id`, `parquet`, `parquet_record`, `raw_citations`, `ddi`), `report.json` and `outputs.json`.
  - Stage 7 and Stage 8 receipts (`receipt.json` with `files` and `raw_citations`) that hold a small industry and occupation workbook, a Stage 8 mapping run with `acs_code_lookup.parquet`, `inputs.json` (`run_id`, `references` with `reference_id`/`receipt_sha256`), `report.json`, `outputs.json`, a Stage 4 directory with `naics_nodes.parquet`, `soc_nodes.parquet`, `code_paths.parquet`, `inputs.json`, `report.json`, `outputs.json`, and a Stage 11 receipt built from `reference_originals`.

- [ ] **Step 1: Write the failing tests.**
  - `test_select_inputs_authenticates_all_six_pins`: `select_inputs` returns a `SelectedInputs` whose `provenance` names the six IDs and pins, and `verify()` passes.
  - `test_a_wrong_pin_for_each_upstream_fails` (parametrized over the six pins): `ValueError` containing `checksum differs`.
  - `test_changed_parquet_raw_csv_or_manifest_entry_fails`: flipping one byte of a Parquet, of a raw CSV, or editing a manifest line each raise `ValueError`.
  - `test_each_run_must_record_the_requested_receipt` (OD1): a Stage 7 `inputs.json` or a Stage 8 mapping `inputs.json` that names another receipt ID raises.
  - `test_only_the_used_files_are_read`: the Stage 8 mapping `outputs.json` also lists `acs_core_canonical.parquet`, which is absent from disk. Selection passes. A missing or changed `acs_code_lookup.parquet` raises.
  - `test_ddi_labels_are_frozen`: `check_ddi` returns int-keyed maps for the delivered labels, and raises for a changed `EMPSAME` label, a `QEMPSTAT` set that has a `Value to allocated value`, an ASEC `QOCCLY` with a third category, and an unknown flag label.
  - `test_stage4_schemas_and_pins_match_tri_codes`: the repeated constants (`CODES_SCHEMA_VERSION`, `NODE_SCHEMA`) equal `tri_codes`'s.
  - `test_provenance_cites_the_frozen_documentary_originals`: `provenance` holds a verified manifest citation for each of `asec_2025_documentation`, `asec_2026_documentation`, `cps_jan2025_industry_documentation`, `cps_lnkfw1mwt`, `cps_empsame`, `cps_actsame` and `ind_2025_codes` of the Stage 7 receipt. Stage 11 cites these frozen copies, not the online ones.
- [ ] **Step 2: Run** `uv run --offline --locked pytest tests/test_cps_flow_inputs.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement.** Authentication is the `outputs.json` SHA-256 against the pin, then a partial inventory check: for the Stage 7 run only `inputs.json`; for the mapping run `acs_code_lookup.parquet` and `inputs.json`; for Stage 4 the three node tables, `inputs.json` and `report.json`. The record in `outputs.json` must equal the file (SHA-256, size, rows and schema for a Parquet). A receipt is authenticated by its `receipt.json` hash, then each used original against `receipt['files']` and `target_io.verify_raw` on its citation. Each CPS delivery is authenticated by `parquet_record` equal to `target_io.file_record(parquet)` and `verify_raw` on its three raw citations. Do not run Stage 7's `verify_bundle`. `verify()` reselects and compares by `==`. Repeat the Stage 4 constants as `tri_codes.py` does.
- [ ] **Step 4: Run** the tests, then `ruff check`. Expected: pass.
- [ ] **Step 5: Commit** `feat(cps-flows): authenticate the five upstreams and freeze the DDI rules`.

### Task 6: Value classes, the monthly panel and links

**Files:**
- Create: `src/embedding_data/cps_flow_linkage.py`, `tests/test_cps_flow_linkage.py`

**Interfaces:**
- Consumes: the unit registry frame of Task 4 (`unit_type`, `code`, `status`).
- Produces (`cps_flow_linkage.py`):
  - `NOT_IN_UNIVERSE = '0000'`, `SPECIALS = {'industry': '9890', 'occupation': '9840'}`, `LINK_COLUMNS` (the 24 ordered link columns below).
  - `classify_codes(frame: pl.LazyFrame, field: str, dimension: str, units: pl.DataFrame) -> pl.LazyFrame`: adds `<field>_class` (`mapped`, `not_in_universe`, `special`). A value that is none of these, or whose registry status is `no_soc_equivalent` or `no_naics_equivalent`, raises `ValueError` at collection.
  - `count_value_classes(frame: pl.LazyFrame, file: str, fields: dict[str, str], units: pl.DataFrame) -> dict` (`{'<file>/<field>': {'mapped': n, 'not_in_universe': n, 'special': n}}` and specials by year).
  - `monthly_panel(monthly: pl.LazyFrame) -> pl.LazyFrame`: adds `source_row` (UInt64) and `month_index` (`YEAR * 12 + MONTH - 1`). It raises for a sample before 2025-01, an `ASECFLAG` of 1, a repeated `CPSIDV` inside one month, a null in `CPSIDV`, `MISH` or `EMPSTAT`, or a `MISH` outside 1–8.
  - `monthly_links(panel: pl.LazyFrame) -> pl.LazyFrame` with `LINK_COLUMNS`: `CPSIDV`, `CPSID`, `source_row_a`, `source_row_b`, `month_a`, `month_b` (`YYYY-MM`), `link_type`, `mish_a`, `mish_b`, `empstat_a`, `empstat_b`, `ind_a`, `ind_b`, `occ_a`, `occ_b`, `qempstat_a`, `qempstat_b`, `qind_a`, `qind_b`, `qocc_a`, `qocc_b`, `empsame_b`, `actsame_b`, plus `CPSIDP` of the earlier month as `cpsidp_a`.
  - `link_counts(panel: pl.LazyFrame) -> pl.DataFrame` (`month_a`, `month_b`, `link_type`, `cpsidv`, `cpsidp`, `other_gap_matches`).
- A **one-month link** has the same `CPSIDV` in calendar months `m` and `m + 1`, `MISH` rising by one, and the earlier `MISH` not 4 or 8. The **two-month link** is only September 2025 → November 2025 with `MISH` rising by two. `other_gap_matches` counts `CPSIDV` matches for those same month pairs that fail the `MISH` rule. The `CPSIDP` count applies the same rules on `CPSIDP`.

- [ ] **Step 1: Write the failing tests** (small typed frames):
  - `test_each_value_class_per_field`: monthly `IND` values `0170` (mapped), `0000` (not in universe), `9890` (special); `OCC` `9840` special. `9840` in an `IND` field and `1234` in any field raise.
  - `test_unpadded_code_is_unparseable` (Review Focus 4): `'170'`, `' 170'` and `'0170 '` raise.
  - `test_delivered_no_equivalent_statuses_fail`: a delivered industry `9920` and occupation `9830` raise.
  - `test_value_class_counts_by_field_file_and_year`.
  - `test_one_month_link_needs_mish_plus_one_and_refuses_4_to_5`: `MISH` 1→2 links, 4→5 does not even when the months are adjacent, and 8→1 does not.
  - `test_september_to_november_two_month_link`: `MISH` 1→3 forms one `two_month` link with `link_type` `two_month`.
  - `test_september_to_november_mish_plus_one_forms_no_link` (Review Focus 2): the pair counts in `other_gap_matches` and forms no link.
  - `test_pre_2025_sample_is_refused_and_no_december_pair_forms`: a December 2024 row raises, and with it removed no link carries `month_a` `2024-12`.
  - `test_duplicate_cpsidv_within_a_month_fails` (Review Focus 3).
  - `test_asecflag_one_is_refused_and_null_or_two_pass`.
  - `test_link_counts_report_cpsidv_and_cpsidp_by_month_pair`: two persons whose `CPSIDV` match but `CPSIDP` differ count once in `cpsidv` and zero in `cpsidp`.
- [ ] **Step 2: Run** `uv run --offline --locked pytest tests/test_cps_flow_linkage.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement** lazily with Polars (join of the panel to itself on `CPSIDV` and the month rule). Validation of the panel collects only aggregates. The value-class check collects a count of failing rows and raises a fixed message with no value in it.
- [ ] **Step 4: Run** the tests, then `ruff check`. Expected: pass.
- [ ] **Step 5: Commit** `feat(cps-flows): classify codes and link adjacent person-months`.

### Task 7: Guards, product eligibility and evidence policies

**Files:**
- Create: `src/embedding_data/cps_flow_guards.py`, `tests/test_cps_flow_guards.py`

**Interfaces:**
- Consumes: `cps_flow_inputs.FLAG_CLASS_BY_LABEL`, `DDI_LABELS`; `cps_flow_linkage.classify_codes`; one-month links with a `weight_status` column (`positive`, `null`, `zero`, Task 8). Two-month links never reach `product_frame`. An ASEC frame also carries `weight_status` (`null` and `zero` both give `weight_nonpositive`).
- Produces (`cps_flow_guards.py`):
  - `guard_expr(dimension: str, empsame: pl.Expr, actsame: pl.Expr) -> pl.Expr` (`changed`, `same`, `unusable`, from the Guards table).
  - `flag_class_expr(file: str, variable: str, value: pl.Expr) -> pl.Expr`: the class of a flag value by its label, `unavailable` for null, and a failing expression (`ValueError` at collection) for a value outside the delivered set.
  - `product_frame(frame: pl.LazyFrame, product: str, dimension: str, *, units: pl.DataFrame) -> pl.LazyFrame`: one row per link or ASEC person with `unit_a`, `unit_b` (four-character codes), `reason` (the first-exclusion reason of SD3, or `eligible`), `strict` (Boolean, always false for `asec_retro`), `inclusion_reasons` (List(String)), `special` (Boolean) and, for industry, `noise_after_duty_change` (Boolean).
  - `funnel(frame: pl.LazyFrame, product: str, dimension: str) -> pl.DataFrame` (`reason`, `count`; sums to the source total).
  - `usable_guard_share(links: pl.LazyFrame) -> dict[str, float]` (`industry`, `occupation`): `(changed + same) / total` over employed→employed one-month links with positive weight.
  - `asec_flag_counts(asec: pl.LazyFrame) -> dict` (`<variable>` → `<EMPSTAT>` → `<value>` → count, for `QIND`, `QOCC`, `QOCCLY`, `QEMPSTAT`).
- `inclusion_reasons` entries: `special_military`, `flag_unavailable:<VARIABLE>`, `flag:<VARIABLE>:<class>` for a non-`nonallocation` class at either end (variables `QEMPSTAT` and `QIND` or `QOCC`), and `asec_no_flag_evidence` for every ASEC row. `strict` is true only for a `monthly_*` row with reason `eligible` and no inclusion reason.

- [ ] **Step 1: Write the failing tests:**
  - `test_guard_table_for_both_dimensions`: all 25 `(EMPSAME, ACTSAME)` pairs over `{1, 2, 96, 97, 99}` give the Global Constraints table for occupation and industry.
  - `test_monthly_ee_admits_only_a_changed_guard_with_positive_weight`.
  - `test_duty_change_moves_occupation_but_industry_difference_is_noise`: `EMPSAME` 2 and `ACTSAME` 2 with both codes different is `eligible` for occupation and `coding_noise` for industry, with `noise_after_duty_change` true.
  - `test_each_exclusion_reason_in_funnel_order`: one link per reason of SD3 for each product and dimension, and the funnel counts equal one each.
  - `test_funnel_is_disjoint_and_sums_to_the_source_total` (hypothesis over small random frames).
  - `test_monthly_ue_uses_the_last_job_origin`: origin `EMPSTAT` 21 and destination 10 is `eligible`, with no guard needed. Origin 22 gives `origin_new_worker_22`, and origin 30 gives `origin_not_unemployed_21`.
  - `test_asec_retro_is_off_diagonal_and_sensitivity_only`: `INDLY` equal to `IND` gives `same_category`, `INDLY` `0000` gives `last_year_code_not_in_universe`, and `strict` is false for every row, even when every delivered ASEC flag is 0 (no `QINDLY` is delivered, so the flags are no allocation evidence for workers).
  - `test_allocated_and_special_ends_never_reach_strict` (Review Focus 5): a diagonal link with `QIND` 6 (`Blank to allocated value`) is `eligible`, not `strict`, with reason `flag:QIND:allocated`. A special origin in `monthly_ue` has `special_military`. A null flag has `flag_unavailable:QIND`.
  - `test_an_unknown_flag_value_fails_rule_validation`: `QIND` 9 raises.
  - `test_usable_guard_share_and_mish_exceptions`: the share equals `(changed + same) / total` on a fixed frame, and the three delivered `EMPSAME` values in `MISH` 1 or 5 are counted as source exceptions by `guard_source_exceptions(links) -> int` and stay in the frame.
  - `test_asec_flag_counts_cover_every_empstat`.
- [ ] **Step 2: Run** `uv run --offline --locked pytest tests/test_cps_flow_guards.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement** with Polars expressions. Add `guard_source_exceptions(links: pl.LazyFrame) -> int` (links whose `mish_b` is 1 or 5 and whose `empsame_b` is 1 or 2).
- [ ] **Step 4: Run** the tests, then `ruff check`. Expected: pass.
- [ ] **Step 5: Commit** `feat(cps-flows): guards, product eligibility and evidence policies`.

### Task 8: Decimal weights aligned to the Parquets

**Files:**
- Create: `src/embedding_data/cps_flow_weights.py`, `tests/test_cps_flow_weights.py`

**Interfaces:**
- Consumes: `SelectedInputs`; `ipums_weights.measure_weights(csv_path, ddi, source, set_name)` and `scan_numeric_csv(csv_path, diagnostics, source)`; `ipums_conversion.decompressed_csv(csv_gz, directory)`; `ipums_parity.compare_ordered`.
- Produces (`cps_flow_weights.py`):
  - `@dataclass(frozen=True) class WeightedSource: monthly: pl.LazyFrame; asec: pl.LazyFrame; diagnostics: dict[str, pl.DataFrame]; rules: dict[str, dict]`. `monthly` has `source_row` (UInt64) and `LNKFW1MWT` (Decimal). `asec` has `source_row`, `ASECWT` and `REPWTP1`–`REPWTP160` (Decimal).
  - `weighted_sources(selected: SelectedInputs, scratch: Path)`, a context manager yielding a `WeightedSource`. It calls `selected.verify()` on entry and on exit, and removes the decompressed CSV copies on exit.
  - `weight_status_expr(weight: pl.Expr, link_type: pl.Expr) -> pl.Expr`: `not_linkable` for `two_month`, else `null`, `zero` or `positive`.

- [ ] **Step 1: Write the failing tests** (`seed_upstreams` with small frames):
  - `test_weights_are_the_literal_csv_text`: ten weights `0.1` sum to exactly `Decimal('1.0')` in the monthly frame. The Float64 Parquet sum is not `1.0`, which shows the recovery is needed.
  - `test_positional_alignment_failure_is_refused`: with `ipums_parity.compare_ordered` patched to report `values_equal` false, entering the context raises `ValueError`.
  - `test_required_weight_names_are_exact`: ASEC needs `ASECWT` and exactly `REPWTP1`–`REPWTP160`. A CSV with `REPWTP161` or without `REPWTP160` raises. The unnumbered `REPWTP` is ignored.
  - `test_negative_full_weight_fails_but_a_negative_replicate_is_kept`: a negative `ASECWT` or `LNKFW1MWT` raises, a negative `REPWTP7` is returned unchanged, and a null `LNKFW1MWT` stays null.
  - `test_link_weight_status_values`: `positive`, `zero`, `null`, `not_linkable`.
  - `test_scratch_is_empty_after_exit_and_verify_runs_twice`: the scratch directory holds nothing after the block, and `verify` was called on entry and on exit.
- [ ] **Step 2: Run** `uv run --offline --locked pytest tests/test_cps_flow_weights.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement** the Stage 9 pattern (`acs_target_weights.py`): decompress each CSV into `scratch`, measure, scan with `with_row_index('source_row')`, and prove all non-weight columns equal to the Parquet row by row before any join. The frames stay lazy, so a caller filters to eligible rows before it collects the 160 replicate columns.
- [ ] **Step 4: Run** the tests, then `ruff check`. Expected: pass.
- [ ] **Step 5: Commit** `feat(cps-flows): recover literal Decimal weights from the raw CSVs`.

### Task 9: Totals, shares, replicate SEs, the seeded bootstrap and undefined cases

**Files:**
- Create: `src/embedding_data/cps_flow_estimation.py`, `tests/test_cps_flow_estimation.py`

**Interfaces:**
- Consumes: eligible records as small Polars frames (collected after the filter, so the 160 ASEC replicate columns stay small).
- Produces (`cps_flow_estimation.py`):
  - `MONTHLY_K = 18`, `ASEC_K = 2`, `BOOTSTRAP_B = 200`, `ASEC_R = 160`, `BOOTSTRAP_SEED = 20261123`.
  - `@dataclass(frozen=True) class Variant: product: str; dimension: str; policy: str`.
  - `@dataclass(frozen=True) class Estimates: targets: pl.DataFrame; support: pl.DataFrame; replicates: pl.DataFrame`. `targets` has `product`, `dimension`, `policy`, `unit_a`, `unit_b`, `measure`, `value`, `se`, `se_method`, `n_unweighted`, `n_weighted`. `support` and `replicates` have the ordered columns of the Schemas section.
  - `household_draws(households: list[int], *, seed: int = BOOTSTRAP_SEED, replicates: int = BOOTSTRAP_B) -> pl.DataFrame` (`replicate` UInt16, `CPSID` Int64, `draws` UInt32; the list must be sorted and unique, else `ValueError`).
  - `estimate_monthly(records: pl.DataFrame, variant: Variant, draws: pl.DataFrame) -> Estimates`: `records` has `CPSID`, `unit_a`, `unit_b`, `period`, `weight` (Decimal).
  - `estimate_asec(records: pl.DataFrame, variant: Variant) -> Estimates`: `records` has `unit_a`, `unit_b`, `period`, `weight` (Decimal, the `ASECWT`) and `rep1`–`rep160` (Decimal).
  - `replicate_se(point: float, replicates: list[float | None]) -> float | None` (the ASEC formula), `bootstrap_se(replicates: list[float | None]) -> float | None`.
- Arithmetic (SD4, SD5): `S` is the exact Decimal sum of weights over a cell, `total = float(S) / k`, `share = total_ab / total_a`. The monthly replicate weight is `weight × draws` for the record's household, exact in Decimal. Every full-sample cell gets all `B` (or 160) replicate rows, zero-filled.

- [ ] **Step 1: Write the failing tests:**
  - `test_pooled_totals_and_shares_with_fixed_divisors`: cells `a→b` weight 36, `a→c` weight 72 with `k = 18` give totals 2.0 and 4.0 and shares `1/3` and `2/3`, `n_weighted` 2.0 and 4.0, and `n_unweighted` as the record counts (not divided by `k`).
  - `test_share_is_the_ratio_of_pooled_totals`: two periods with different denominators. The share equals pooled `S_ab / S_a`, not the mean of the two period shares.
  - `test_decimal_sums_do_not_drift`: ten records of weight `0.1`, `k = 1`, give `average_total` exactly `1.0`.
  - `test_asec_replicate_se_formula`: replicates that all differ from the point by exactly 1 give `sqrt((4/160) × 160) = 2.0`. A negative replicate weight stays in the sum. The unnumbered `REPWTP` is never a replicate (the frame has only `rep1`–`rep160`).
  - `test_every_cell_has_every_replicate_row_zero_filled` (Review Focus 1): a cell whose only household is drawn in some replicates and not in others has `B` replicate rows, with `numerator` 0.0 where it was not drawn. The row count equals cells × 200 (monthly) or cells × 160 (ASEC).
  - `test_bootstrap_draws_are_pinned_and_reproducible`: two calls are equal. For `H = 3`, replicate 1 equals `Counter(random.Random(20261123).choices(range(3), k=3))` computed in the test. Each replicate's draws sum to `H`. An unsorted or duplicated list raises.
  - `test_bootstrap_se_uses_b_minus_one`: replicates `[1.0, 2.0, 3.0]` give `1.0`.
  - `test_strict_and_sensitivity_share_the_same_draws`: with one `draws` frame, the strict replicate numerator of a cell equals the hand-summed weight × draws of the strict records alone.
  - `test_nonpositive_denominator_publishes_no_share`: records with weights `+1` and `-1` for one origin give the `average_total` row, no `forward_share` row, and a support row of kind `undefined_share` with reason `nonpositive_denominator`.
  - `test_undefined_replicate_ratio_keeps_the_point_with_null_se`: an ASEC replicate whose origin total is not positive gives the share row with `se` null and `se_method` `none`, a support row with reason `replicate_share_undefined` and the replicate numbers, and a replicate row with `status` `denominator_nonpositive` and `estimate` null. `average_total` keeps its SE.
  - `test_unobserved_cells_are_absent`.
- [ ] **Step 2: Run** `uv run --offline --locked pytest tests/test_cps_flow_estimation.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement.** The monthly replicate frame joins `records` to `draws` on `CPSID`, so memory is replicates × eligible records. The bootstrap SE is `sqrt(fsum((x - mean)**2) / (B - 1))` with `mean = fsum(x) / B`. The ASEC SE is `sqrt((4 / 160) * fsum((x_r - x)**2))`. `se_method` is `bootstrap` or `replicate` when `se` is not null and `none` otherwise.
- [ ] **Step 4: Run** the tests, then `ruff check`. Expected: pass.
- [ ] **Step 5: Commit** `feat(cps-flows): estimate flows, replicate SEs and the seeded bootstrap`.

### Task 10: Target rows, companion tables and the report

**Files:**
- Create: `src/embedding_data/cps_flow_targets.py`, `tests/test_cps_flow_targets.py`

**Interfaces:**
- Consumes: `Estimates` and `Variant` (Task 9), the unit registry (Task 4), the funnel, guard and link counts (Tasks 6, 7).
- Produces (`cps_flow_targets.py`):
  - `COMPANION_SCHEMAS: dict[str, dict[str, pl.DataType]]` for the five companion Parquets, exactly as in the Schemas section.
  - `target_rows(estimates: dict[Variant, Estimates], units: pl.DataFrame) -> pl.DataFrame` (`TARGET_SCHEMA`, metadata and flags per Global Constraints).
  - `support_table(estimates: dict[Variant, Estimates]) -> pl.DataFrame`, `replicates_table(estimates: dict[Variant, Estimates]) -> pl.DataFrame`.
  - `diagnostics_table(parts: dict) -> pl.DataFrame`, with `parts` keys `value_classes`, `links`, `weights`, `funnels`, `guards`, `evidence`, `specials` (the outputs of Tasks 6 and 7).
  - `linked_pairs_table(links: pl.DataFrame) -> pl.DataFrame` (the monthly links with `guard_industry`, `guard_occupation`, `weight_a`, `weight_status` and `products`).
  - `n_unweighted_distribution(targets: pl.DataFrame) -> dict` (keys of the Schemas section).
  - `build_report(*, run_id: str, parts: dict, tables: dict[str, pl.DataFrame]) -> dict` (the `report.json` keys).

- [ ] **Step 1: Write the failing tests:**
  - `test_target_rows_pass_the_contract_with_frozen_metadata`: `write_targets` accepts the frame. Exact strings: `source` `cps`, `family` `job_change_flow`, `unit_a` `feature:cps_industry_category:0170`, `vintage` `census-industry-2022`, `universe` `monthly_ee:strict`, `sample_set` `cps-basic-2025-01-to-2026-09` (monthly) or `cps-asec-2025-2026` (ASEC).
  - `test_flags_follow_the_registry`: monthly rows carry `bootstrap_approximate` and `size_gate_pending`, ASEC rows carry `unguarded_upper_bound`, a row with a `9890` or `9840` end carries `special_military` and exists only in `sensitivity`. Flags are sorted and distinct.
  - `test_se_method_follows_the_se`: `bootstrap` or `replicate` when `se` is set, `none` when it is null.
  - `test_companion_tables_have_the_fixed_ordered_schemas`: each frame's `schema` equals `COMPANION_SCHEMAS[name]` in order, and rows are sorted as the Schemas section says.
  - `test_diagnostics_label_exclusive_funnels_and_overlaps`: funnel rows are `exclusive` true and sum to the source total of their product and dimension. Evidence, guard-noise and special rows are `exclusive` false.
  - `test_n_unweighted_distribution_has_the_fixed_keys`: `cells`, `min`, `max`, `p10`, `p25`, `p50`, `p75`, `p90`, and `at_least` with keys `1`, `2`, `5`, `10`, `20`, `30`, `50`, `100`.
  - `test_report_has_the_fixed_keys_and_no_row_content`: the keys equal the Schemas list, `v11['unparseable_values']` is 0, and `json.dumps(report)` contains no fixture `CPSIDV` or `CPSID`.
- [ ] **Step 2: Run** `uv run --offline --locked pytest tests/test_cps_flow_targets.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement.** Pure functions over the computed pieces. `n_weighted` of a `forward_share` row is the cell's mass divided by `k`, the same as its `average_total` value. Percentiles use the nearest-rank method on the sorted `n_unweighted` of the `average_total` rows.
- [ ] **Step 4: Run** the tests, then `ruff check`. Expected: pass.
- [ ] **Step 5: Commit** `feat(cps-flows): assemble the target rows, companion tables and report`.

### Task 11: Build, verify and compare the bundle

**Files:**
- Create: `src/embedding_data/cps_flow_bundle.py`, `tests/test_cps_flow_bundle.py`

**Interfaces:**
- Consumes: Tasks 2–10.
- Produces (`cps_flow_bundle.py`):
  - `SCHEMA_VERSION = 'cps-job-flows-v1'`, `TABLES` (the six names of the Schemas section), `FILES = (*(name + '.parquet' for name in TABLES), 'inputs.json', 'report.json')`, `SOFTWARE_ROOT = paths.PROJECT_ROOT`, `SOFTWARE_FILES: tuple[str, ...]` (the measured closure of this module and its imports, plus `pyproject.toml` and `uv.lock`; Task 12 adds the command module).
  - `run_directory(data_dir: Path, run_id: str) -> Path` (`derived/cps/job-flows/<run_id>`, `ValueError` for an unsafe ID).
  - `freeze_software() -> dict` (file records, `python`, `python_full`, `implementation`, `dependencies`, `uv_lock_sha256`, as `tri_bundle.freeze_software`).
  - `build(data_dir: Path, run_id: str, request: InputRequest) -> dict` (`run_id`, `directory`, `outputs_sha256`).
  - `verify_bundle(directory: Path, data_dir: Path, *, expected_outputs_sha256: str) -> dict`.
  - `compare_runs(first: Path, second: Path) -> dict` (`equal`, `tables`, `report_equal`, `trust_established` false).
- Flow of `build` (copy `tri_bundle.build`): `target_io.stage` → `freeze_software` → `select_inputs` → read both lists, the nodes and the PUMS lists → delivered code sets from the two Parquets → `build_units` → `check_ddi` for both files → inside `weighted_sources(selected, staging / '.scratch')`: monthly panel, links, weights, `product_frame` per product and dimension, households and `household_draws` per product (OD6), `estimate_monthly` and `estimate_asec` per variant → `cps_flow_targets` tables and report → write the six Parquets (`write_targets` for `cps_job_flows`) → remove `.scratch` → `inputs.json`, `report.json` → recheck (`selected.verify()`, `freeze_software()` equal, receipts) → `outputs.json` over the other eight files → rename `<run>.part` to `<run>`. `finally` removes only its own staging.
- `verify_bundle` copies `tri_bundle.verify_bundle`: authenticate the pin, the exact file set and the inventory, read the six IDs and pins from `inputs.json`, require recorded `software` equal to `freeze_software()`, recompute every table in a temporary directory outside `data_dir`, compare each in physical order with an `ordered_equal` of its own, then compare `report.json` and `inputs.json` (with the recorded `execution`).
- `compare_runs` checks each bundle against its own `outputs.json`, then compares the six tables in order and `report.json` without its `run_id`. It does not compare `inputs.json`, as TRI. Equality establishes replay, not trust.

- [ ] **Step 1: Write the failing tests** (`seed_upstreams` with a fixture that holds at least one guarded employer change, one duty change, one coding-noise pair, one unusable guard, one unemployed→employed move, one `9890` and `9840` origin, one September→November link and one ASEC difference):
  - `test_build_publishes_exactly_the_bundle_files`: the final directory holds the eight files plus `outputs.json`, `outputs.json` lists the other eight and not itself, and the returned pin equals its SHA-256.
  - `test_occupied_final_or_partial_name_fails_before_writing`.
  - `test_failure_cleans_only_its_own_staging`: a forced failure removes `<run>.part` and leaves another run's `.part` alone.
  - `test_pins_and_software_are_rechecked_before_publication`: a pin or software change during the build prevents publication and leaves no final.
  - `test_verify_accepts_the_published_bundle`: returns `run_id`, the pin and row counts.
  - `test_verify_refuses_a_wrong_pin_a_changed_table_and_a_changed_upstream_pin`.
  - `test_a_changed_software_file_makes_verify_refuse`: patch `SOFTWARE_ROOT` to a copy that holds one changed `SOFTWARE_FILES` entry.
  - `test_two_builds_compare_equal_and_a_changed_weight_compares_unequal`: `compare_runs` of a build and a replay is `equal` true. A replay from a seed that differs by one weight gives `equal` false.
  - `test_the_fixture_exercises_every_spec_case`: the report shows each reason of SD3 at least once for the cases the fixture holds, and the monthly Parquet's two specials appear only with `special_military`.
  - `test_software_files_equal_the_measured_import_closure`: `subprocess_modules('embedding_data.cps_flow_bundle')` mapped with `module_file` (both from `vendor_link_fixtures`), plus `pyproject.toml` and `uv.lock`, equals `set(SOFTWARE_FILES)`.
- [ ] **Step 2: Run** `uv run --offline --locked pytest tests/test_cps_flow_bundle.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement** as described. Stage every row-level intermediate under `.scratch` or in memory, never under `ROOT` outside the staging directory. Release the decompressed CSVs before the rename.
- [ ] **Step 4: Run** the tests, then `ruff check`. Expected: pass.
- [ ] **Step 5: Commit** `feat(cps-flows): build, verify and compare the job-flow bundle`.

### Task 12: Command group, README and the offline guarantees

**Files:**
- Create: `src/embedding_data/cps_job_flows.py`, `tests/test_cps_job_flows_cli.py`
- Modify: `src/embedding_data/cps_flow_bundle.py` (add `src/embedding_data/cps_job_flows.py` to `SOFTWARE_FILES`), `README.md` (a "CPS job-change flows" section)

**Interfaces:**
- Consumes: `cps_flow_bundle`, `cps_flow_references`, `cps_flow_inputs.InputRequest`.
- Produces: `python -m embedding_data.cps_job_flows` with exactly the commands `acquire-references REFERENCE_ID`, `import-reference REFERENCE_ID KIND FILE`, `build RUN_ID`, `verify RUN_ID --outputs-sha256 PIN`, `compare-runs FIRST SECOND`. Every command takes `--data-dir`. `build` takes `--stage7-run`, `--stage7-outputs-sha256`, `--stage7-receipt`, `--stage7-receipt-sha256`, `--stage8-receipt`, `--stage8-receipt-sha256`, `--stage8-mapping-run`, `--stage8-mapping-outputs-sha256`, `--codes-run`, `--codes-outputs-sha256`, `--cps-receipt`, `--cps-receipt-sha256`. Module constants `NO_RUN = '-'`, `RAW = 'raw/references/cps-job-flows'`, `BUNDLES = 'derived/cps/job-flows'`. Copy `tri_parent_links.py` (`_invoke`, `_reason`, the failure line, `typer.Exit(1)` outside the guard).

- [ ] **Step 1: Write the failing tests** (model: `tests/test_tri_cli.py`; use `typer.testing.CliRunner`, the `no_live_clients` fixture and `data_directory`):
  - `test_the_five_commands_are_exactly_these`.
  - `test_acquire_and_import_print_one_sorted_json_line` (patched `make_client`).
  - `test_build_verify_compare_round_trip`: `build` prints `run_id`, `directory` (data-relative) and `outputs_sha256`. `verify` with that pin exits 0. `compare-runs` of a build and a replay exits 0 with `equal` true.
  - `test_failure_prints_only_the_fixed_line_and_exits_2`: a wrong pin gives stderr exactly `CPS job flows build failed: validation; run r1; path derived/cps/job-flows/r1`, empty stdout, no exception text.
  - `test_unequal_comparison_exits_1`.
  - `test_no_offline_command_reads_env_or_builds_a_client`: with `dotenv.load_dotenv` and `ipumspy.IpumsApiClient` patched to raise, a full round trip still succeeds. `make_client` is called only by `acquire-references`.
  - `test_import_closure_is_the_recorded_one` (OD5): in a subprocess, importing `embedding_data.cps_job_flows` gives `('dotenv' in modules, 'ipumspy' in modules) == (True, True)`. If the owner chose the alternative, the expected value is `(False, True)`.
  - `test_software_files_equal_the_measured_import_closure`: the closure of `embedding_data.cps_job_flows` plus `pyproject.toml` and `uv.lock` equals `set(SOFTWARE_FILES)`.
- [ ] **Step 2: Run** `uv run --offline --locked pytest tests/test_cps_job_flows_cli.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement** the command module, update `SOFTWARE_FILES`, and write the README section with the production invocations. Use `--data-dir /Users/lowell/Projects/embedding-data/data` and the pins of Global Constraints, leave the Stage 11 receipt and run pins as `<...>` until Tasks 15 and 16, and state the host rule.
- [ ] **Step 4: Run** `uv run --offline --locked pytest tests/test_cps_job_flows_cli.py tests/test_cps_flow_bundle.py -v`, then `ruff check`. Expected: pass.
- [ ] **Step 5: Commit** `feat(cps-flows): add the command group and the README contract`.

### Task 13: The V12 fixture chain (raw files to a replay-equal bundle, offline)

**Files:**
- Create: `tests/test_cps_flow_v12.py`
- Modify: `tests/cps_flow_fixtures.py` (add `cps_flow_case`, `seed_cps_chain`, `run_cps_flow_v12`)

**Interfaces:**
- Consumes: the existing chain helpers, imported and never edited: `acs_mapping_fixtures` (`_authenticated_deliveries`, `_authenticated_codes`, `seed_reconciliation_inputs`, `build_fixture_mapping`, `forbid_external_access`), `acs_target_fixtures.install_counted_guards`, `ipums_fixtures` (definition, DDI and CSV writers), `vendor_link_fixtures.subprocess_modules`.
- Produces: `cps_flow_case() -> dict` (the synthetic persons below), `seed_cps_chain(tmp_path, monkeypatch) -> SeededChain` (real Stage 4, Stage 7 and Stage 8 bundles, the two CPS deliveries, the Stage 11 receipt) and `run_cps_flow_v12(data_dir, monkeypatch) -> dict` (the build, `verify`, replay build, `compare_runs` results and the external-access counts).

- [ ] **Step 1: Probe the existing helpers (no code yet).** Read `tests/acs_mapping_fixtures.py` lines 728–872 and 969–1023. Confirm and write down as a comment above `seed_cps_chain`: (a) `_authenticated_deliveries` writes the two CPS deliveries from constants (`EMPSTAT` 10, `IND` `0170`, `OCC` `0010`) and has no CPS hook, (b) the chain's Stage 4 bundle holds the full NAICS 2022 and SOC 2018 trees (`naics_nodes` 2,125 rows, `soc_nodes` 1,447, from `tests/fixtures/acs_mapping/upstream/stage4-originals.zip`), (c) the chain's Stage 7 and Stage 8 receipts hold the committed Census list workbooks in `tests/fixtures/acs_mapping/classification/`. If (b) or (c) is false, stop and ask the owner: a CPS build then needs a different list source.
- [ ] **Step 2: Write the failing test** `test_raw_to_job_flows_is_offline_and_replayable` with `@pytest.mark.slow` (the marker is registered, and `tests/conftest.py` stays untouched). It runs `run_cps_flow_v12` and asserts:
  - The chain is genuine: raw CSV, `.xml` and `extract.json` triples recorded in a temporary manifest, converted by the unchanged `ipums_conversion.convert`, a real Stage 7 run (`ipums_verification_run.measure`), Stage 4 and Stage 8 bundles, and the Stage 11 references imported through `import_reference` from `reference_originals`.
  - `build`, `verify` with the detached pin, a second `build` and `compare_runs` all succeed, with `equal` true and `trust_established` false.
  - The counted guards (`install_counted_guards`) show zero network, environment-file and live-client attempts.
  - The fixture cases appear in the report: a guarded employer change (`monthly_ee` industry and occupation), a duty change (occupation eligible, industry `coding_noise` with `noise_after_duty_change`), a coding-noise pair, an unusable guard, an unemployed→employed move, a `9890`/`9840` origin that exists only in `sensitivity` with `special_military`, a September→November 2025 link counted in `linkage.two_month` and in no flow, and an ASEC difference that carries `unguarded_upper_bound`.
  - Only `cps_linked_pairs.parquet` has a `CPSIDV` column. `report.json` and `inputs.json` hold no fixture `CPSIDV`.
  - Mutations fail: a wrong pin, and a changed `SOFTWARE_FILES` entry, make `verify` raise.
- [ ] **Step 3: Implement the fixtures.** `cps_flow_case` returns monthly and ASEC rows built with `monthly_row` and `asec_row`. Use only industry and occupation codes that the committed lists hold (`0170` crop production, `0180`, `1190`; `0020`, `0040`, `0010`) plus `0000`, `9890` and `9840`. Persons: P1 employer change January→February 2025 (`EMPSAME` 1, both codes differ); P2 duty change (`EMPSAME` 2, `ACTSAME` 2, occupation and industry differ); P3 coding noise (`EMPSAME` 2, `ACTSAME` 1, industry differs); P4 unusable guard (`EMPSAME` 99); P5 unemployed (`EMPSTAT` 21, last-job `0170`) → employed; P6 `EMPSTAT` 21 with `9890` and `9840` → employed; P7 September→November 2025 with `MISH` 1→3; P8 employer change with `QIND` 6 (sensitivity only); P9 September `MISH` 3 → November `MISH` 4 (no link); ASEC rows with `INDLY` `0170` and `IND` `0180`, one with equal codes, one with `INDLY` `0000`, and one armed-forces row with `9890`. Weights are decimal text such as `1500.1234`. September 2025 rows have a null `LNKFW1MWT`. `seed_cps_chain` copies the structure of `seed_reconciliation_inputs`: it calls `_authenticated_deliveries` with `test_ipums_acceptance.PROFILES` monkeypatched to the three ACS profiles, writes the two CPS deliveries itself in the same raw layout, adds their two keys to `selection.json`, then continues as the original.
- [ ] **Step 4: Run** `uv run --offline --locked pytest tests/test_cps_flow_v12.py -v`. Expected: pass. Record the wall time. Run `ruff check`.
- [ ] **Step 5: Commit** `test(cps-flows): add the V12 fixture chain`.

### Task 14: The independent reconciler

**Files:**
- Create: `scripts/reconcile_cps_job_flows.py`, `tests/test_reconcile_cps_job_flows.py`

**Interfaces:**
- Consumes: a published bundle, the Stage 7 Parquets and raw CSVs, the two Census workbooks and Stage 4 `soc_nodes.parquet` (all located through the bundle's `inputs.json`).
- Produces: `python scripts/reconcile_cps_job_flows.py --data-dir ROOT --run RUN_ID --outputs-sha256 PIN` printing one sorted JSON line `{'checks': {...}, 'equal': bool}` and exiting 0 (equal), 1 (unequal) or 2 (error). It imports no `embedding_data` module. Only the standard library (`json`, `gzip`, `csv`, `decimal`, `math`, `hashlib`), `polars` and `fastexcel`. It restates the spec's rules (guard table, funnel order, flag classes, `k`, SE formula) itself.
- Checks: `value_classes`, `x_residuals` (against `cps_category_units`), `links` (the pairs and the link counts against `cps_linked_pairs` and the diagnostics), `guards` (both dimensions), `eligibility` (the funnel counts), `targets` (every `average_total` and `forward_share` value, `n_unweighted` and `n_weighted`, from exact Decimal sums with `float(S) / k`) and `asec_se` (the replicate SE of every ASEC row). It never recomputes a bootstrap SE.

- [ ] **Step 1: Write the failing tests:**
  - `test_script_imports_no_embedding_data_module`: parse the script with `ast` and assert that no import names `embedding_data`.
  - `test_reconciler_is_equal_on_a_seeded_build`: build with `seed_upstreams`, run the script, and expect exit 0 and every check true.
  - `test_each_check_detects_its_mutation` (parametrized): in a copy of the bundle, change one `average_total` value (`targets`), one `guard_industry` (`guards`), one X candidate (`x_residuals`), one `link_type` (`links`) and one ASEC `se` (`asec_se`). The matching check is false and the exit code is 1. A changed bootstrap `se` leaves the result equal.
  - `test_exit_codes_for_equal_unequal_and_error`: a wrong pin or a missing run exits 2.
- [ ] **Step 2: Run** `uv run --offline --locked pytest tests/test_reconcile_cps_job_flows.py -v`. Expected: FAIL (script missing).
- [ ] **Step 3: Implement** the script as a standalone module with a `main(argv)` function, written from the spec and not from the build modules. Read weights from the raw CSV text with `decimal.Decimal`, aligned to the Parquet by row number.
- [ ] **Step 4: Run** the tests, then `ruff check scripts tests`. Expected: pass.
- [ ] **Step 5: Commit** `feat(cps-flows): add the independent reconciler`.

### Task 15: Acquire or import the Stage 11 references (controller, owner-gated)

**Files:** none in git. Raw originals under `ROOT/raw/references/cps-job-flows/<REFERENCE_ID>/` and manifest lines.

- [ ] **Step 1: Software readiness.** On the execution branch, run `uv run --locked pytest` and `uv run --locked behave`, after the `pgrep` checks of the Host rule. Expected: every test and scenario passes. Stop if anything fails.
- [ ] **Step 2: Owner go-ahead.** Show the owner the full output of both `pgrep` commands and ask for the go-ahead to acquire, which also confirms that no Stage 9 freeze window is open. Choose a fresh ID `stage11_cps_references_<YYYYMMDD>_r1` and check that `ROOT/raw/references/cps-job-flows/` holds no such name. Record the baseline: `wc -c < ROOT/raw/manifest.jsonl` and `shasum -a 256 ROOT/raw/manifest.jsonl`.
- [ ] **Step 3: Acquire.**

  ```bash
  uv run --offline --locked python -m embedding_data.cps_job_flows acquire-references <REFERENCE_ID> --data-dir /Users/lowell/Projects/embedding-data/data
  ```

  Expected: one JSON line and a published snapshot, or `CPS job flows acquire-references failed: validation; ...`. A refusal names the refused kinds in staging (BLS refuses non-browser clients).
- [ ] **Step 4: Import each refused kind.** The owner downloads the original in a browser into a new, empty directory outside every checkout. Ask for the go-ahead of each import, then run `import-reference <REFERENCE_ID> <KIND> <FILE> --data-dir ...`. The last import publishes the snapshot.
- [ ] **Step 5: Handle an anchor failure.** A failed validator names the kind. Stop. Show the owner the message and the original's relevant cells, and let the owner decide. Never import a file from `/tmp/cps_research_dl/`, never loosen an anchor to pass, and use a new reference ID after any change.
- [ ] **Step 6: Record and preserve.** Record `shasum -a 256 ROOT/raw/references/cps-job-flows/<REFERENCE_ID>/receipt.json` as the receipt pin. Check that `head -c <baseline size> ROOT/raw/manifest.jsonl | shasum -a 256` equals the baseline hash, and that `uv run embedding-data audit --data-dir ROOT` exits 0 with zero discrepancies.
- [ ] **Step 7: Commit** the receipt ID and pin in the README placeholders of Task 12 (`docs(cps-flows): record the Stage 11 references receipt`).

### Task 16: First full-data build, verification and acceptance (controller, owner-gated)

**Files:** none in git. Bundle under `ROOT/derived/cps/job-flows/<RUN_ID>/`. Logs under `/Users/lowell/.cache/embedding-data/stage-11/`, outside every checkout, so the tree stays clean (`inputs.json` records `dirty`).

- [ ] **Step 1: Pre-flight.** The tree is clean and the branch is committed. Run `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'` and `pgrep -fl 'embedding_data|embedding-data'`, show the owner both outputs, and ask for the go-ahead to build, which also confirms no Stage 9 freeze window. Choose a fresh `RUN_ID = stage11_cps_job_flows_<YYYYMMDD>_r1` and check that neither it nor its `.part` exists.
- [ ] **Step 2: Baselines.** Record `shasum -a 256` of both CPS Parquets, both raw `.csv.gz` and `.xml` files, the `outputs.json` of the Stage 4, 7 and 8 runs, and the manifest size and hash. Run `uv run embedding-data audit --data-dir ROOT`. Expected: exit 0.
- [ ] **Step 3: Build** under `/usr/bin/time -l`:

  ```bash
  /usr/bin/time -l uv run --offline --locked python -m embedding_data.cps_job_flows build <RUN_ID> --data-dir /Users/lowell/Projects/embedding-data/data --stage7-run stage7_ipums_verification_20261015_r2 --stage7-outputs-sha256 db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc --stage7-receipt stage7_ipums_references_20261015_r2 --stage7-receipt-sha256 3163968dde603ba53f807976dd09b9e40d73235a98c6f36e4e02c67ec4239c9c --stage8-receipt stage8_acs_references_20261018_r4 --stage8-receipt-sha256 052135beb2e77d3cd14b4b800602be9ab36d54aaa43eaf05abffb4d5c14fd2d5 --stage8-mapping-run stage8_acs_mapping_20261018_r7 --stage8-mapping-outputs-sha256 1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4 --codes-run stage4_v11_20261013_r2 --codes-outputs-sha256 15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a --cps-receipt <REFERENCE_ID> --cps-receipt-sha256 <RECEIPT_PIN>
  ```

  Expected: one JSON line with `outputs_sha256`, and the `time` report in the log. Record the wall time, the "maximum resident set size" and `du -sk` of the bundle. A failure leaves `<RUN_ID>.part` only if cleanup itself failed. Never delete staging without the owner's go-ahead. A memory kill (exit 137) is a finding, not a retry: stop and report, as Stage 9 did.
- [ ] **Step 4: Verify** (no replay build runs in this stage) with the detached pin: `... cps_job_flows verify <RUN_ID> --outputs-sha256 <PIN> --data-dir ...`. Expected: exit 0.
- [ ] **Step 5: Reconcile:** `uv run --offline --locked python scripts/reconcile_cps_job_flows.py --data-dir ... --run <RUN_ID> --outputs-sha256 <PIN>`. Expected: exit 0 with `equal` true.
- [ ] **Step 6: Check the data gates** in `report.json` and report each result, never smooth it over: `v11.unparseable_values` is 0, the registry has 266 industry and 570 occupation codes plus the two specials, `x_categories` reads 30 `equal`, 7 `strict_subset` and 1 `not_delivered_no_pums_list` (design time: `1240`, `1970`, `3090`, `7100`, `7640`, `7750`, `8990` are the strict subsets, `8865` has no list), `9890` and `9840` appear only as sensitivity ends, September→November 2025 shows about 19,498 two-month matches and no flow, and the one-month link count is near 530,017. A different X outcome or a failed cross-check stops the stage for an owner decision (decision 5).
- [ ] **Step 7: Preserve.** Repeat Step 2's hashes and `audit`: every earlier raw file is byte-identical, the manifest keeps its earlier bytes as a prefix (`head -c`), the audit reports zero discrepancies, and the Stage 4, 7 and 8 bundles and the CPS Parquets are byte-identical. Record the `pgrep` list taken after the command.

### Task 17: Findings, source-spec amendments and plan completion (controller)

**Files:**
- Create: `specs/naics-evaluation-data-stage-11-findings.md`
- Modify: `specs/embedding-evaluation-data-spec.md`, `specs/evaluation-targets-methodology.md`, `CLAUDE.md`, `specs/deferred_items.md`, `specs/naics-evaluation-data-roadmap.md`, this plan (markup)

- [ ] **Step 1: Write the findings file.** Facts only, from `report.json`, the logs and Task 16: the run ID and pin, the references receipt ID and pin, the `9890` and `9840` outcome with each source and year (monthly settled by the Census 2026 basic code lists, ASEC 2026 `9890` recorded as unresolved by owner decision), wall time, maximum RSS, bundle size, the usable-guard shares, the linkage rates by month pair, the funnels, the X cross-check counts, the `n_unweighted` distribution, and what is not claimed (the spec's Methodological limits, one line each). Link it from the roadmap entry.
- [ ] **Step 2: Apply the source-spec amendments** exactly as the stage spec's "Source spec amendment" section words them, each tagged *(owner, Stage 11 design, 2026-11-23; [stage spec](cps-job-change-flows.md))*: V11 (after the ACS `559830` exception), R4.7, R4.8, R5.3 and R4.9 in `specs/embedding-evaluation-data-spec.md`, and the K8 step 7 pointer in `specs/evaluation-targets-methodology.md`.
- [ ] **Step 3: CLAUDE.md.** Add a "CPS job-change flows (roadmap Stage 11)" section in the style of the TRI and Stage 14 sections: the five commands, the bundle files, the offline rules, the guard and value-class rules, the software-identity rule and its consequence for `verify`, the host rule, and R8.4. Run pins wait for the later hardening outcome, so cite the findings file for them.
- [ ] **Step 4: Deferred items.** Tick the `9890` item in section `7-ipums-extract-verification` and the old Stage 11 item with `→ done <date>`, citing the findings file.
- [ ] **Step 5: Run the Plan Completion Protocol** of the writing-plans skill: the resolve-before-defer gate, the markup of this plan, `specs/deferred_items.md`, step 3a (the roadmap stamp `> Stage 11: COMPLETE (<date>) — implemented by plan 23 (specs/plans/completed/23-cps-job-change-flows.md). Its Handoff section names what O21, the V9 headline minimum and old Stage 12 consume.` and `> Next: resume the roadmap.`, and the `## Handoff to later stages` section for O21 (products, policies, flags, usable-guard shares, the unguarded upper-bound label, the specials, R8.4), the later hardening outcome (run ID, pin, receipt), V9 (the `n_unweighted` distribution and `size_gate_pending`) and old Stage 12 (the helper modules and the unit registry)), the backlog report and the retirement commit.
- [ ] **Step 6: Open the PR** under the standing PR lifecycle (enable Auto-fix and auto-merge, verify the merge, clean up). The docs-only commits skip the coverage hook by themselves.
