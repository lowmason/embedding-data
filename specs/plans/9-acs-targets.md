# ACS Targets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build authenticated, offline ACS staffing-pattern, workplace area-mix, commuting and migration targets with exact pooling, all 80 replicate estimates, separate canonical/allocated views, and measured full-data acceptance.

**Architecture:** Add a standalone ACS target pipeline around the shipped Stage 8 selection/verification APIs and Stage 6 single-file target writer. Keep source identity, family membership, native Decimal aggregates, and geographic projections at separate grains; share rules, estimation and publication across explicit family definitions. Publish eight aggregate Parquets and three JSON records, with independent acceptance calculations outside the production package.

**Tech Stack:** Python >=3.14, existing locked Polars >=2.0.0, Typer, pytest/Hypothesis and Behave; standard-library Decimal, gzip, CSV, XML and hashing. No dependency or test-configuration changes.

**Spec:** [specs/acs-targets.md](../acs-targets.md), owner-approved complete written design on 2026-10-19 at `4b5d1965c0de04104fbfa1bd048b1748bd9f8a0a`.

Roadmap: specs/embedding-evaluation-data-spec-roadmap.md, Stage 9 — on plan completion, tick the stage and re-validate later stages against what shipped.

## Global Constraints

- Work exclusively in `/Users/lowell/.codex/worktrees/acs-targets-design/embedding-data`, branch `codex/acs-targets-design`; explicitly set every repository command's working directory to that root. Reuse this worktree. Do not switch or write the primary checkout `/Users/lowell/Projects/embedding-data` or create another worktree.
- Planning entry: branch and HEAD verified as above; `git status --short` was empty. The writing-plans entry checker returned `next free: 9`, `collisions: none`, and no overlapping live plans.
- The source data root is explicitly `/Users/lowell/Projects/embedding-data/data`. Production-data writes are limited to fresh Stage 9 output/control directories during the later execution phase; upstream files and the existing raw-manifest prefix remain immutable. Planning authorizes no production-data operations.
- “Production transformations are deterministic lazy Polars; small public reference tables may be eager.”
- “Keep family definitions small and explicit.” No configuration language or general target framework.
- “Only the core produces Stage 9 targets.” Five-year/vintage/CPS authentication adds no family or period.
- “Source identity is `(source_parquet_sha256, source_row)`, with zero-based UInt64 positions within each source Parquet.” Preserve source order, all original values and duplicate multiplicity; do not expand or rewrite companions.
- “Code lookup natural keys remain `(system, source_scheme, paired_census_code, source_token)`.”
- “Area lookup keys remain `(profile, sample_id, release_year, component_year, role, source_state_code, source_area_code)`.”
- Preserve the seven-field Stage 8 `SelectionRequest`, `acs_mapping_inputs.select_inputs(...).verify()`, full upstream authentication, and `acs_mapping_bundle.verify_bundle(..., expected_outputs_sha256=...)` unchanged. Bind the mapping's recorded upstream request to the explicit request; no latest alias, inferred pin or mixed-run fallback.
- D5 is solely the exact historical Stage 5 creator-CLI compatibility already implemented by Stage 8. No new stale-software exception or upstream inventory/status rewrite. Frozen upstream executing files, including `cli.py`, `target_io.py`, conversion, selection, classification/geography builders and Stage 7/8 modules, must remain byte-identical.
- “Adopt Stage 7 literal CSV weights at factor 1.” “PERWT supplies point estimates; exactly REPWTP1 through REPWTP80 supply variance replicates.” REPWTP is a helper; household weights are not person estimators.
- “Aggregate native weighted masses with Decimal arithmetic before Float64 publication.” Retain signed replicate weights/ratios, with no clipping, missing-replicate removal or alternative SE.
- `civilian_employed`: EMPSTATD `{10,12}`. `private_wage_salary`: that universe plus CLASSWKRD `{22,23}`. Validate these against each selected DDI; add no household, GQ, age, earnings or hours restriction.
- Staffing retains temporarily absent workers. Workplace mixes/commuting require EMPSTATD `10`, applicable domestic endpoints, and an applicable TRANWORK category excluding `80`; N/A is not non-home work. This exclusion also applies to sensitivity.
- Migration requires MIGRATE1 `{2,3}` and applicable domestic prior/current endpoints; prior uses work/migration PUMA and current uses residence PUMA. No stayer self-loops, inferred endpoint, prior-job interpretation or job-related movement claim.
- Every family requires QEMPSTAT/QIND/QOCC evidence; private additionally QCLASSWK; workplace/commuting additionally QPWSTAT2/QTRANWOR; migration additionally QMIGRAT1/QMIGPLC1. Classify nonallocation, allocated, edited/failed-edit, unavailable, not-applicable separately using each delivered DDI and substantive applicability. Unknown labels/values fail rule validation.
- Strict migration uses annual 2024 (`k=1`). Matched sensitivity also uses 2024 (`k=1`); pooled sensitivity uses 2023–2024 (`k=2`). Other products use 2023–2024 (`k=2`), strict and sensitivity, for both universes.
- Canonical views require frozen supported scalar nodes at NAICS six-digit/SOC detailed level for every used code dimension, with supported-subset denominators. Singleton candidates, prefixes, common ancestors or a chosen crosswalk side cannot supply a leaf. Preserve every mapping/provenance flag. Crosswalked/imputed observations cannot enter strict canonical products.
- County/MSA products allocate workplace area mixes only, using work/migration county factors followed by typed county-to-CBSA membership. No allocated flows, canonical allocated products, residence-factor substitution, MET2023/PWMET23/MIGMET23 assignment or MSA renormalization.
- “Keep 2020 population/PUMAs, 2022 county composition, 2025 county inventory and July 2023 delineations distinct, including all nine Connecticut planning regions.” Non-MSA mass distinguishes micropolitan from no-CBSA counties.
- Publish only `annual_average_total` and `forward_share`. Shares condition on identified eligible pairs. Every denominator uses its numerator's exact restrictions. Publish positive-full-weight cells only; do not densify missing pairs.
- “All targets retain `size_gate_pending`; no minimum count is chosen here.” Allocation-conditional sampling SEs quantify neither allocation error nor mapping uncertainty.
- Eight Parquets plus `inputs.json`, `report.json`, `outputs.json`; only three target tables use exact ordered `targets-v1`. Preserve `TARGET_SCHEMA`, `TARGET_KEY_COLUMNS`, `validate_targets`, `write_targets(frame, destination)` unchanged.
- “Authenticate the external inventory pin before trusting any bundle content.” Exclusive owned staging, safe IDs/paths, no symlinks/replacement, fresh input/software rechecks; failure publishes no new final and cleanup touches only execution-owned temporary paths.
- “Output evidence is aggregate.” No person/household identifiers, source positions or microdata audit rows in published bundles or git. Complete aggregate category/area registries are permitted. Never use evaluation inputs for embedder training, mining or model selection.
- Build/verify/compare run offline, with explicit `--data-dir`, no environment-file access or live clients, acquisition, conversion recovery, upstream rebuild or automatic refresh. The module CLI has exactly `build`, `verify`, `compare-runs`; do not register it in the frozen top-level CLI.
- Hermetic tests join normal pytest, with temporary roots and guarded external access. “No new dependency or test-configuration edit is needed for this design.” No new marker/default exclusion; the existing network canary stays deselected.
- Owner D2 governs all verification and commit steps: run focused tests during development and one complete coverage-enabled suite for each final tested source state. Reuse its recorded passing evidence for identical source/tests/fixtures/configuration/dependencies/runtime/test selection; only then may subsequent all-files or commit invocations set `SKIP=coverage-check`, with every other hook active. Any relevant change invalidates reuse. Documentation-only changes use applicable document/diff checks unless tests consume the changed document. No marker, default exclusion, coverage threshold, hook configuration or scientific gate changes. See Verification execution policy below.
- Full-data independent comparisons: exact schemas/identities/keys/counts and native Decimal sums; shares absolute tolerance `1e-12`; allocated masses and SEs `abs(actual - expected) <= 1e-8 + 1e-12 * abs(expected)`. Never widen these after measuring. Logical replay remains exact across all eight ordered tables and substantive reports, excluding only top-level run ID/creation time.
- Stage 9 stays unticked throughout planning and software-only readiness. Completion requires full-data first/replay, detached verification, independent reconciliation, preservation, repository checks, recorded review and the completion protocol. Later-stage Consumes reconciliation belongs to the subsequent roadmap resume.

## Decisions

- **D1** (owner, plan review, 2026-10-19): “Approved. Review specs/plans/9-acs-targets.md against the approved spec and shipped upstream contracts. Fix any gaps in the same replacement worktree, keeping this session planning-only.” Approval authorizes this plan review and technical corrections; it does not authorize implementation or production-data operations in this session. Applied in: Global Constraints and Planning self-review and execution handoff. The written Stage 9 spec remains binding; the review corrections below introduce no spec amendment.

- **D2** (owner, 2026-10-19, this execution chat): after the controller recommended one complete coverage run per unchanged source state, focused checks during development, independent review and separate integration-test profiling, the owner replied “Yes.” This amends execution procedure only. It supersedes redundant full-suite invocations and the prior blanket prohibition on skipping the coverage hook, solely under the evidence-reuse conditions below. All scientific requirements, tests, full default-suite membership, external guards, detached verification, full-data acceptance and independent reviews remain binding. No test/hook/dependency configuration change is authorized or needed.

- **D3** (owner, 2026-10-19, execution chat): owner replied “Approved” to the proposed test-only guard-reinstallation fix after D2 profiling. Implement bounded/idempotent reinstallation in `tests/acs_target_fixtures.py` with regression coverage in `tests/test_acs_target_v12.py`; preserve every protected path, transport/bound-client seam, counter-before-denial behavior, inherited original-then-counted installation order, monkeypatch restoration and real authenticated raw chain. Reprofile the same representative synthetic case, run one fresh complete coverage gate under D2, and independently review before marking this follow-up complete. Production authentication/estimators, frozen upstream files, fixture scope/raw setup, test exclusions/configuration/dependencies and completed Tasks1–8 remain unchanged. Task9 remains next after this approved follow-up.

## Verification execution policy — owner D2

1. During implementation and each review fix, run the covering focused tests. Finish source changes and self-review before starting long gates. Do not repeat a completed focused run merely because it also appears in a later task's checklist.
2. At a software-readiness, pre-production or final integration checkpoint, require one complete coverage-enabled default suite for the final tested source state. The normal commit coverage hook can supply this gate; alternatively run the explicit coverage command below to retain visible test counts, durations and warnings. Do not run plain full pytest, all-files coverage and commit coverage on identical tested bytes.
3. Record the tested commit/tree plus any worktree differences, command, exit status/log, Python/dependency/lock identity, test selection and COVERAGE_THRESHOLD. Compare current bytes before reuse: include production code, scripts, tests/helpers/fixture originals, Behave features/steps, configuration, dependencies and any additional files those checks consume. A commit SHA alone or an unchanged production module alone is insufficient. Source/test/fixture/config/dependency/runtime/selection changes invalidate the receipt. Failed, incomplete, truncated or unidentifiable evidence cannot be reused. A failed gate must be resolved and its amended code checked.
4. If that exact tested state already has passing complete coverage evidence, subsequent all-files and commit invocations may set `SKIP=coverage-check`; all other hooks remain active. Log this explicit owner-authorized reuse, the receipt and the actual Skipped status. Do not claim the skipped hook ran. Never use this exception to skip a missing full gate, a focused regression, independent review or any scientific acceptance check. No global SKIP setting or hook/config edit.
5. Documentation-only changes require document/link/diff checks. Reuse the prior software receipt only after confirming no tested input changed; run a relevant focused check if tests consume the document. If another hook changes executable/tested files, the receipt is invalid and the changed state needs appropriate focused tests and a new complete coverage gate before production/integration.
6. Tasks8/10/11 may cite the same valid receipt across checkpoints. Task8's historical three broad passes remain recorded honestly; they are not rerun or erased. Task9 implementation will change tested files and therefore requires a fresh receipt. Pure finding, plan, retirement or Handoff edits do not by themselves require another hour-long suite. Relevant changes to frozen executing science software still require fresh science IDs and all existing acceptance gates.

One explicit full gate, when no valid receipt exists (record the current threshold; do not lower it):

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache UV_OFFLINE=1 uv run --offline --locked pytest --cov=embedding_data --cov-report=term-missing --cov-fail-under="${COVERAGE_THRESHOLD:-0}" --durations=20
```

After confirming a valid matching receipt, run mechanical all-files checks and the normal commit with only the redundant coverage invocation omitted:

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache UV_OFFLINE=1 SKIP=coverage-check uv run --offline --locked pre-commit run --all-files
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache UV_OFFLINE=1 SKIP=coverage-check git commit -m 'TASK-SPECIFIC MESSAGE'
```

A normal commit without SKIP remains the default if it is supplying the one required coverage gate. Behave, Ruff and lock checks remain required, with reuse of identical-state results recorded. Reviewers use the implementer's retained test evidence rather than rerunning it without a concrete unresolved doubt.

Separate performance work preserves the current tests and trust semantics. Measure one representative guarded synthetic case with cProfile/durations and source-backed call counts before changing implementation. No production data, broad-suite profiling, new exclusion/marker, cloned-upstream replacement or authentication memoization is part of D2. Record measured attribution separately from optimization hypotheses; any later implementation follows a scoped approved design and preserves all invariants.


### D2 runtime investigation — measured synthetic case

At unchanged software commit `ab87d45ad308115a0d13fa8a2cc79e5b82d967c6`, one fresh guarded `test_raw_to_all_four_acs_families_is_offline_and_replayable` completed under cProfile: **1 passed in 996.38 seconds**, call-phase duration996.22s; profile-accounted time992.565s. This is a diagnostic run with instrumentation overhead, not a new full-suite or production acceptance gate. Existing uninstrumented Task8 V12-containing focused runs are recorded separately. Raw profile/logs remain local: `/private/tmp/stage9-runtime-v12.prof`, `/private/tmp/stage9-runtime-v12.log`; aggregate function summary is copied to the ignored SDD workspace.

| Profiled boundary | Calls | Cumulative seconds |
| --- | ---: | ---: |
| Stage9 `select_targets` | 32 | 842.145 |
| Stage8 `verify_bundle` | 66 | 605.027 |
| Stage9 `derive_tables` | 4 | 427.621 |
| Counted file guard `check` | 3,536,169 | 385.983 |

These timings overlap and must not be added. In particular, target derivation includes authenticated weight-source preparation;427.621s is not an exclusive estimator time. cProfile measured200estimator calls (50products ×4derivations), and the complete profile recorded3,875,785,210calls including library/guard overhead. These tiny-fixture measurements do not establish production scalability.

The exact nested-verification count is source-backed and measured: each successful Stage9 build/verify has initial selection1 + input-evidence weighted-source selection3 + derivation weighted-source selection3 + closing recheck1 =8selectors. Two builds and two verifiers therefore invoke32selectors; each takes2mapping snapshots, giving64Stage8verifications. Explicit upstream verification and target comparison add2, for66verifications/67Stage8derivations including the initial mapping build. Relevant boundaries: `acs_target_weights.py:74,90,94`, `acs_target_inputs.py:52,76,113–114`, `acs_target_bundle.py:102,273,297,364,421`, `acs_target_tables.py:44`. The initial read-only audit's18count omitted the weighted-source checks and is superseded; its lifecycle55count was similarly incomplete and is not retained as evidence.

The guard was installed4times. Each installation captures already-patched open functions (`tests/acs_target_fixtures.py:459–484`), so safe fixture file reads pass through nested wrappers. The measured `check` executed3,536,169times; `guarded_open` has451,076primitive calls and3,536,169total recursive calls, with396.776cumulative seconds. This identifies a test-only optimization candidate: make guard reinstallation replace its own wrappers while retaining original-then-counted installation semantics, all protected paths/bound client/transport seams, counter-before-denial behavior and monkeypatch restoration. A subsequent implementation should first test repeated installation and exact counted refusals; it must retain the real raw chain and zero-access assertions. No such implementation is included in D2.

After that isolated fixture change, reprofile the same case before choosing production optimizations. Reducing repeated full upstream reconstruction requires a separate design that preserves detached authority and fresh drift checks at every existing boundary; do not memoize away those guarantees. Likewise, moving schema/serialization or mathematical cases to cheap layers must preserve their assertions and at least one real authenticated end-to-end chain. No tests, markers, default selections, frozen upstream files or production estimators changed during this investigation.

An initial attempt to profile retained temporary inputs stopped at the existing Stage7 reference-vintage check because the original fixture's scoped synthetic-reference registrations were no longer active. No validator was weakened; the successful measurement used the complete original fresh guarded fixture instead.


### D3 guard-reinstallation follow-up — completed 2026-10-20

Code commit `7021b95dd1ecdab4fedb9f7ff96c4dab7863e1a4` changes only `tests/acs_target_fixtures.py` and `tests/test_acs_target_v12.py`. Reinstallation replaces directly owned wrappers using callable self-identity; foreign wrappers remain opaque even if `functools.wraps` copies helper metadata. Protected paths, counter-before-denial behavior, transport and bound-client probes, inherited guard composition, and nested MonkeyPatch restoration are preserved. Production code, authentication, estimators, test configuration, and the real raw chain are unchanged.

Deterministic TDD reproduced growing work before the fix: four installations gave 1/2/3/4 checks through builtins/io and 2/4/6/8 through Path.open. Final work stays 1/1/1/1 and 2/2/2/2 respectively. The final focused check passed 20 tests, with two targeted deselections, in 0.82s. Full-suite selection retains every default test.

| Same-case instrumented comparison | Before | After |
| --- | ---: | ---: |
| Test elapsed seconds | 996.38 | 709.43 |
| Guard `check` calls | 3,536,169 | 892,618 |
| Guard `check` cumulative seconds | 385.983 | 101.535 |
| Actual `_io.open` calls | 451,406 | 451,406 |
| Stage 8 verify / derive calls | 66 / 67 | 66 / 67 |
| Target derivations | 4 | 4 |

The single-case instrumented elapsed reduction is about 28.8%; this is not a universal speedup or production-scaling claim. Cumulative boundaries overlap. The successful raw-chain test retains all four families, both detached target verifiers, exact replay, and measured zero network, environment-file, and live-client attempts. The baseline profile is preserved; after artifacts are `/private/tmp/stage9-guard-after.prof` and `.log`, with an aggregate summary retained in the ignored SDD workspace.

Exactly one fresh complete coverage gate ran on the final tested state: **2,484 passed, one existing network canary deselected, 94% coverage in 3,551.69s (59m11s), exit 0**. No warning or failure summary appeared. Behave passed one feature, two scenarios, and ten steps; Ruff and lock checks passed. The matching 222-file/Python/dependency/platform/threshold/selection fingerprint has digest `fa265292f1411249454bc703003968793f9be331c4d03a441542d536eca3d95b`. Receipts matched after coverage, hooks, and commit; the controller and independent reviewer checked them. All-files and commit hooks explicitly recorded redundant Coverage Check as Skipped under D2; all other applicable hooks passed. The commit's routine unstaged-plan warning was accounted for by successful stash/restore. No second broad gate ran.

Fresh read-only `guard_reinstallation_review` (inherited runtime; no Claude-model claim) reviewed `f9b4766..7021b95`: spec compliant, quality Approved, no Critical/Important/Minor findings. The complete report, tested/current receipts, and profile summaries are in `.sdd/9-acs-targets/`. The controller rehashed all 57 recorded local Stage 8 executing/independent members: no mismatch. Tasks 1–8 remain complete, Task 9 remains next, Stage 9 remains unticked, and production science acceptance remains pending. No additional optimization or production-data operation occurred.

---

## Read before execution

Read this plan and [the approved stage spec](../acs-targets.md), not the brainstorming dialogue. Read `AGENTS.md`/`CLAUDE.md` in this worktree. Source requirements are [R3.6–R3.11](../embedding-evaluation-data-spec.md#r3--acs-microdata-through-ipums-usa), R7.1/R7.2/R7.4, R8/R9 and V12. Stage 9's reconciled Consumes are in [the roadmap](../embedding-evaluation-data-spec-roadmap.md).

Shipped upstream contracts take precedence over provisional old task text:

- [Plan 8 Handoff](completed/8-acs-codes-area-allocation.md#handoff-to-later-stages) and [Stage 8 actual APIs, complete ordered schemas and selected inventories](../findings/stage-8-acs-codes-area-allocation.md#handoff-to-later-stages--actual-apis).
- [Plan 4 Handoff](completed/4-code-tables-ita-naics-mapping.md#handoff-to-later-stages): `system:vintage:level:code`, complete candidate/path evidence, singleton-crosswalk uncertainty.
- [Plan 5 Handoff](completed/5-geography-hierarchy-county-reference.md#handoff-to-later-stages): typed county/CBSA membership, metro/micro and missing-CBSA cases, separate frames.
- [Plan 6 Handoff](completed/6-target-contract-ita-area-mix.md#handoff-to-later-stages): immutable generic writer and raw-to-target fixture seam; ITA weights/SEs supply no ACS defaults.
- [Plan 7 Handoff](completed/7-ipums-extract-verification.md#handoff-to-later-stages) and [weight finding](../findings/stage-7-ipums-extract-verification.md#v7-csvddiparquet-weight-interpretation): literal CSV weights, exact lexical scan, negative replicates and separate converter-fidelity evidence.

### Selected identities (copy exactly)

| Input | Run / delivery | Detached inventory or receipt SHA-256 |
| --- | --- | --- |
| Mapping first | `stage8_acs_mapping_20261018_r7` | `1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4` |
| Mapping independent replay evidence | `stage8_acs_mapping_20261018_r7_replay` | `a115c5f7e2691ecbffe763bd1b6b9780fb6a71bc512a2691cf4014f9857b3565` |
| Codes | `stage4_v11_20261013_r2` | `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |
| Geography | `stage5_geography_20261014` | `5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d` |
| IPUMS verification | `stage7_ipums_verification_20261015_r2` | `db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc` |
| IPUMS reference receipt | `stage7_ipums_references_20261015_r2` | `3163968dde603ba53f807976dd09b9e40d73235a98c6f36e4e02c67ec4239c9c` |

| Source | Delivery | Rows | Original Parquet SHA-256 |
| --- | --- | ---: | --- |
| `acs/core` | `usa_00001` | 3,206,859 | `c07f9e7abe2c5dfdb8f9488a1f574d4cf49ab7945c3ad2ffc9daec5eaba47d10` |
| `acs/five_year` | `usa_00003` | 7,456,212 | `c5846bde221e7785051a4a4075aa6a71cc267a1f4497168a96df05d7c50f78fe` |
| `acs/vintage` | `usa_00002` | 1,575,420 | `b6ffab7bd974f72b4fbc913f261779f5ce3145a915849bf92e946bb6b649240d` |

The immutable Stage 8 science seal is `b09d1a56308f09d6e99f97070c02ffbbc0523d6c595f7901bb0e01a999bd3ddf`; its 880-file control inventory pin is `7af71e3b57c6c07867224259f49563c20e0cd3b75e1d99f54b4cea4f92cc221a`. Preserve those controls and conservative machine adoption fields. D5 allows only selected geography's old `cli.py` hash `68778e16b7cc051745c1e34d3dee6a9fc044fd12b1f78103773984503e9f9742` against current `32a86b3d07bf112fabc1edb01fd10a966e840c185642e55d00f35dfd435220b3`, corroborated by selected Stage 7/8 software. All other identities remain strict.

### Frozen interfaces to consume

```text
# Existing modules; do not change these signatures or their implementations.
SelectionRequest(codes_run, codes_outputs_sha256, geography_run,
                 geography_outputs_sha256, ipums_run, ipums_outputs_sha256,
                 ipums_references_receipt_sha256)
acs_mapping_inputs.select_inputs(data_dir: Path, request: SelectionRequest) -> SelectedInputs
SelectedInputs.verify() -> None
acs_mapping_bundle.verify_bundle(directory: Path, data_dir: Path,
                                *, expected_outputs_sha256: str) -> dict
ipums_weights.measure_weights(csv_path: Path, ddi: dict, source: str,
                              set_name: str) -> tuple[pl.DataFrame, dict]
ipums_weights.scan_numeric_csv(csv_path: Path, diagnostics: pl.DataFrame,
                               source: str) -> pl.LazyFrame
ipums_conversion.decompressed_csv(csv_gz: Path, directory: Path)  # context manager yielding Path
validate_targets(frame: pl.LazyFrame | pl.DataFrame) -> None
write_targets(frame: pl.LazyFrame | pl.DataFrame, destination: Path) -> dict
acs_mapping_io.safe_path(file: Path) -> None
acs_mapping_io.publish_directory(staging: Path, final: Path) -> None
```

`SelectedInputs.sources['acs/core']` is a `SourceInput(profile, delivery_id, parquet, parquet_record, raw_citations, definition, ddi)`. Mapping `inputs.json` records `selected_upstreams.request`, `sources`, `references`, `frames`, `rules`, `software`. Mapping tables are `acs_code_lookup`, `acs_area_lookup`, `puma_county_factors`, `puma_msa_factors`, `puma_msa_coverage`, `acs_core_canonical`, `acs_five_year_canonical`, `acs_vintage_canonical`. Read companions in place; selected `.codes`/`.geography` dictionaries provide real node and county/CBSA tables. Do not call `_derive`, `annotate_source`, a builder or converter to prepare production targets.

## File responsibilities and task order

All paths below are relative to the explicitly selected worktree. Future tool calls must set that absolute working directory; shell examples below run there, never in the primary checkout.

| File(s) | Responsibility / owning task |
| --- | --- |
| `src/embedding_data/acs_target_contract.py` | Product dataclasses/registry, ordered output schemas, keys/versions, aggregate validators (1) |
| `src/embedding_data/acs_target_inputs.py` | Mapping/upstream selection binding, strict rules/software identity and rechecks (2) |
| `src/embedding_data/acs_target_rules.py` | Delivered DDI/domain validation, substantive applicability and evidence statuses (3) |
| `src/embedding_data/acs_target_units.py` | Observed-category, native-area and selected-node unit registry (3) |
| `src/embedding_data/acs_target_weights.py` | Owned lexical weight scan and exact positional alignment (4) |
| `src/embedding_data/acs_target_membership.py` | Five small pair definitions (staffing, two mixes, commuting, migration), eligibility/funnels (4) |
| `src/embedding_data/acs_target_estimation.py` | Decimal native cell/denominator aggregation, pooling, all 80 statistics/SEs (5) |
| `src/embedding_data/acs_target_projection.py` | Supported-leaf projection, deterministic county/MSA allocation and residuals (6) |
| `src/embedding_data/acs_target_tables.py` | Eight-table assembly, cross-table invariants, reports and serialization (7) |
| `src/embedding_data/acs_target_bundle.py` | Exclusive eleven-file build, reconstructing detached verifier, logical comparison (7) |
| `src/embedding_data/acs_targets.py` | Standalone three-command Typer module, explicit options and fixed safe errors (8) |
| `tests/acs_target_fixtures.py` | Hand-labeled small cases plus authenticated raw-to-target chain; no production data (1–8) |
| `tests/test_acs_target_{contract,inputs,rules,units,weights,membership,estimation,projection,tables,bundle,cli,v12}.py` | Normal-suite contract/invariant tests, one file per responsibility (1–8) |
| `tests/test_acs_targets_reconciliation.py` | Independent acceptance and adversarial self-consistent corruption tests (9) |
| `scripts/stage9_independent_io.py` | Independent pin/inventory/software/preservation controls, no production imports (9) |
| `scripts/stage9_independent_estimates.py` | Independent raw/DDI eligibility and Decimal/statistical calculation (9) |
| `scripts/reconcile_stage9.py` | Explicit offline acceptance/control command group (9–10) |
| `specs/findings/stage-9-acs-targets.md` | Actual measured aggregate finding, created only after measurement (10) |
| `README.md`, `CLAUDE.md` | Commands/readiness docs (8); measured facts and limits only after acceptance (10) |
| This plan, `specs/deferred_items.md`, roadmap, retiring stage spec | Completion-protocol edits only after all gates (11) |

Dependencies: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11. Keep commits small within a task; task boundaries are independently reviewable deliverables. Once 8 passes, software is ready, with scientific acceptance still pending. Task 10 is explicit production measurement during execution, never part of this planning session.

## Concrete aggregate contracts (freeze before tests)

### Products, target keys and unit IDs

A `Product` is frozen and has fields `product_id:str`, `family:str`, `dimension:str`, `view:str`, `base_universe:str`, `evidence_policy:str`, `years:tuple[int,...]`, `sample_set:str`, `pool_divisor:int`, `vintage:str`. `dimension` is `industry_occupation`, `industry`, `occupation`, or `flow`. `view` is `observed`, `canonical`, `allocated_county`, `allocated_msa`. IDs are canonical JSON hashes of those fields excluding product_id. Publish the complete registry, including empty products, in inputs/report; product_id is an audit join key, not a substitute for shared target metadata.

Use sample sets `annual-core-2023-2024` (`us2023a`,`us2024a`, k=2) and `annual-2024` (`us2024a`, k=1). Universe is exactly `<base_universe>:<evidence_policy>`. Define the explicit 22 observed products: staffing 4; industry/occupation workplace mixes 8; commuting 4; migration strict-2024 2, sensitivity-2024 2, sensitivity-pooled 2. Add 12 canonical products (staffing 4, native mixes 8) and 16 allocated products (county mixes 8, MSA mixes 8): **50 products**, two measures each, with legitimate empty products recorded. Never add strict pooled migration or canonical flows.

Unit identifiers:

```python
def observed_unit(system: str, code_lookup_id: str) -> tuple[str, str]:
    kind = {'naics': 'acs_industry_category', 'soc': 'acs_occupation_category'}[system]
    return kind, f'feature:{kind}:{code_lookup_id}'


def puma_unit(area_type: str, state_fips: str, area_code: str) -> tuple[str, str]:
    kind = {'residence': 'residence_puma', 'work_migration': 'work_migration_puma'}[area_type]
    return kind, f'geography:2020:{kind}:{state_fips}{area_code}'
```

Canonical IDs/types come verbatim from selected Stage 4 nodes (`naics_national_industry`, `soc_detailed`); counties use `county` and selected Stage 5 IDs, MSAs use type `cbsa` and selected metropolitan IDs (preserve `cbsa_type` in registry). Workplace and migration roles may share a work/migration unit; their role lookup IDs/locators are unioned in the unit registry and family direction keeps their use distinct.

Freeze `vintage` strings by product dimension/view, with separate typed frames in inputs: observed staffing `acs-naics2022-soc2018`; native observed industry/occupation mix `acs-naics2022-puma2020` / `acs-soc2018-puma2020`; commuting `residence2020-work-migration2020`; migration `work-migration2020-residence2020`; canonical staffing `naics2022-soc2018`; canonical mixes `naics2022-puma2020` / `soc2018-puma2020`; allocated mixes `acs-naics2022-county2025` / `acs-soc2018-county2025`, or `acs-naics2022-msa2023` / `acs-soc2018-msa2023`. Allocated registry records population2020, PUMA2020, composition2022 and July2023 separately rather than implying the short string is one common vintage.

Define `observed_counterpart(product:Product)->Product` by matching family, dimension, base_universe, evidence_policy, years, sample_set and pool_divisor against the unique observed product; view/vintage/product_id intentionally differ. It is the explicit comparison baseline for canonical/allocated coverage, not a join on equal product_id.

`STAT_KEY_SCHEMA` is ordered `view:String` followed by `TARGET_SCHEMA` fields in `TARGET_KEY_COLUMNS` order with `se_method` removed: source, family, unit_a_type, unit_a, unit_b_type, unit_b, measure, sample_set, vintage, universe. `CELL_KEY_SCHEMA` removes measure from that schema. TARGET_STAT_KEY_COLUMNS names the shared single-file key without se_method; STAT_KEY_COLUMNS adds view for auxiliaries, and CELL_KEY_COLUMNS then removes measure. At most one target per logical statistic key, even across different se_method values. Flags never identify a variant.

### Auxiliary ordered schemas

Implement these literal ordered dictionaries in `acs_target_contract.py`. `S=pl.String`, `I=pl.Int64`, `U=pl.UInt64`, `F=pl.Float64`, `B=pl.Boolean`, `LS=pl.List(S)`, `LU8=pl.List(pl.UInt8)`. Schema version is `acs-targets-v1`; eligibility/estimation rules are `acs-target-rules-v1`. Stage 8 `CODE_SCHEMA` is imported unchanged to preserve every field and its order.

```python
STAT_KEY_SCHEMA = {
    'view': S,
    **{name: TARGET_SCHEMA[name] for name in TARGET_KEY_COLUMNS if name != 'se_method'},
}
CELL_KEY_SCHEMA = {name: dtype for name, dtype in STAT_KEY_SCHEMA.items() if name != 'measure'}
UNIT_SCHEMA = {
    'unit_type': S, 'unit': S, 'kind': S,
    **{'code_' + name: dtype for name, dtype in CODE_SCHEMA.items()},
    'node_id': S, 'node_system': S, 'node_vintage': I, 'node_level': S,
    'node_code': S, 'node_title': S,
    'area_type': S, 'state_fips': S, 'area_code': S, 'puma_vintage': I,
    'population_year': I, 'county_composition_year': I,
    'county_inventory_vintage': I, 'msa_delineation': S, 'cbsa_type': S,
    'roles': LS, 'area_lookup_ids': LS, 'factor_keys': LS,
    'reference_ids': LS, 'reference_locators': LS,
}
SUPPORT_SCHEMA = {
    **STAT_KEY_SCHEMA, 'record_kind': S, 'component_year': I, 'product_id': S,
    'pool_divisor': pl.UInt8, 'n_unweighted': U, 'denominator_n_unweighted': U,
    'cell_weight_sum_exact': S, 'denominator_weight_sum_exact': S,
    'cell_mass': F, 'denominator_mass': F,
    'fractional_support_mass': F, 'denominator_fractional_support_mass': F,
    'native_coverage_n': U, 'native_coverage_mass': F,
    'point_status': S, 'point_reason': S, 'se_status': S, 'se_reason': S,
    'undefined_replicates': LU8, 'support_semantics': S, 'flags': LS,
}
REPLICATE_SCHEMA = {
    **STAT_KEY_SCHEMA, 'product_id': S, 'replicate': pl.UInt8,
    'numerator_sum_exact': S, 'denominator_sum_exact': S,
    'pool_divisor': pl.UInt8, 'numerator': F, 'denominator': F,
    'estimate': F, 'status': S, 'reason': S,
}
DIAGNOSTIC_SCHEMA = {
    'source': S, 'profile': S, 'delivery_id': S, 'source_parquet_sha256': S,
    'sample_id': S, 'component_year': I, 'family': S, 'dimension': S,
    'base_universe': S, 'evidence_policy': S, 'view': S, 'product_id': S,
    'partition_kind': S, 'variable': S, 'raw_dtype': S, 'raw_value': S,
    'evidence_status': S, 'reason': S, 'n_unweighted': U,
    'weight_sum_exact': S, 'weighted_mass': F,
    'reference_ids': LS, 'reference_locators': LS,
}
RESIDUAL_SCHEMA = {
    'source': S, 'family': S, 'workplace_unit_type': S, 'workplace_unit': S,
    'code_unit_type': S, 'code_unit': S, 'sample_set': S, 'vintage': S,
    'universe': S, 'product_id': S, 'component_year': I,
    'replicate': pl.UInt8, 'residual_type': S, 'pool_divisor': pl.UInt8,
    'weighted_mass': F, 'n_input_support': U, 'fractional_support_mass': F,
    'flags': LS,
}
```

Nullability and grains:

- Unit key `(unit_type,unit)` unique. `kind` is `observed_code`, `native_area` or `selected_node`. For observed_code all `code_*` fields mirror one complete Stage 8 code record, including its nullable fields; unrelated scalar geographic/node fields are null. Other kinds have null unrelated code scalars, with every unrelated code list typed `[]`, never a null list. Native areas have area_type/state/area/vintage and associated role/factor/lookup lists. Selected nodes have all node fields, appropriate frames and CBSA type where applicable. Canonical selected nodes' complete source-category provenance stays in observed units and authenticated input mapping, with aggregate coverage in support; no invented single source mapping for a leaf that receives several categories.
- All list containers/elements are nonnull. Set-valued lists sort distinct; `code_canonical_candidate_paths` retains candidate alignment and root-to-leaf path order. Enforce Stage 8 candidate/path lengths and field equality for observed units.
- Support key: `STAT_KEY + record_kind + component_year`; component_year `0` means pooled, otherwise an annual component in that product. `cell` records cover both measures, including supported-but-unpublished cells. `denominator_status` uses measure `forward_share` and null unit_b_type/unit_b, and is emitted only for nonpositive full denominators with identified input support. Those two null key fields are forbidden on cell records. Null-safe key equality is explicit; no null target key is ever emitted.
- Native exact fields store unpooled Decimal sums as canonical decimal strings; cell_mass/denominator_mass are their annual-average contribution (`sum/k`) or pooled value. Allocated exact fields are null; allocation first consumes authenticated exact native sums. n counts are not divided by k. Fractional support is sum of positive factors per input position, separately labeled and not a person count; native fractional support equals n.
- Canonical native_coverage_n/native_coverage_mass record the **denominator baseline** from observed_counterpart(product), before the used code dimensions' supported-leaf restriction. For an area mix, group by the same native workplace unit. For staffing, group otherwise eligible observed source positions whose industry scalar equals that canonical industry, before the occupation-leaf restriction; several observed industry categories may contribute. Repeat that baseline on both measures' support rows, without summing repeated baselines across cells. Report whole-product loss separately, including rows with no supported industry and no canonical denominator group. Counts/masses lost under source evidence policy are already excluded from both sides. Fields are null for noncanonical views. Use internal source-position sets for membership reconciliation; do not equate observed/canonical unit IDs or product_id values.
- Point status is `defined` for publishable full points, `no_positive_cell_mass` for a finite statistic withheld by the positive-cell rule, or `nonpositive_denominator` for an undefined full forward share; reason is null only for defined. SE status is `defined`, `undefined_point` or `undefined_replicates`; reason is null only for defined. A finite but unpublished zero-cell statistic may still have a defined SE in audit support. Pooled support owns final point/SE statuses; annual contribution rows repeat those **pooled** statuses/reasons/affected-replicate lists, with annual masses/counts only. They never invent annual point estimates/SEs. Nonpositive full denominators make the full share and its SE undefined, but do not suppress independently defined replicate ratios.
- Replicate key `STAT_KEY + replicate`, exact 1..80 for each supported cell/statistic, including undefined point/SE cases. `status=defined` requires finite estimate and null reason; other statuses `zero_denominator`, `nonfinite_ratio` require null estimate and nonnull reason. Replicate status is evaluated independently of full-point publication/definition: a finite ratio remains defined even when the full denominator is nonpositive. Native numerator/denominator exact strings are unpooled sums with k explicit. Published numerator and denominator floats are annual-average masses (`raw_sum/k`); the total replicate estimate is numerator, while the share replicate estimate is numerator/denominator. Divide exactly once. Totals retain denominator context but their estimate/SE is independent of ratio validity.
- Diagnostics key is all dimensions through reason (source hash is aggregate provenance, never a row identity). partition_kind is `first_exclusion` (one disjoint partition including eligible per product/year), `evidence` (overlapping variable/status/raw-value counts), `limitation` (overlapping provenance/559830/undelivered-PUMA-evidence), or `coverage` (projection losses). raw_value may be null for unavailable evidence; variable/raw_dtype/evidence_status may be null outside evidence partitions unless the diagnostic names a specific variable/evidence status; non-evidence rows must not fabricate nonallocation. Weighted_mass is annual contribution at that product's k; weight_sum_exact is raw native sum. All product/source identity strings, partition_kind, reason and n are required. Never sum overlapping partitions as a funnel.
- Residual key is all dimensions through residual_type; replicate `0` is full and 1..80 numbered replicates; component_year `0` is pooled, annual years are also retained. residual_type `micropolitan` or `no_cbsa`. A group can supply both: nonadditive n_input_support is separately labeled. Residuals contain annual-average mass (`unpooled allocated mass/k`), not an extra target measure. Emit residuals for allocated_msa products only; the county branch returns a typed empty residual frame, avoiding duplicate residual products for the same evidence/universe/period.
- All numeric publication fields must be finite when nonnull; signed replicate numerators/denominators/estimates/residuals are allowed. Full supported cell masses are nonnegative and publication requires `>0`; a nonpositive denominator does not manufacture a share. No source-row/household columns are allowed in any auxiliary schema.
- Sort targets using the unchanged writer; sort auxiliary tables by the declared keys with nulls first. Validate exact column order/dtypes, key uniqueness and all cross-table membership/status relationships on serialized reread.

### Internal seams and lifecycle

`SelectedTargets` is frozen with fields `data_dir:Path`, `mapping_run:str`, `mapping_outputs_sha256:str`, `request:SelectionRequest`, `upstream:SelectedInputs`, `mapping_directory:Path`, `tables:dict[str,Path]`, `provenance:dict`, `software:dict`; `.verify()->None` repeats authenticated selection and compares snapshots. Do not expose mutable local data as a substitute for that verifier.

`FlagRules` is frozen with `version:str`, `domains:dict`, `references:dict`, `universe_categories:dict`. Domains record each variable's original dtype, delivered value/label, substantive applicability and classified status. `read_rules(source:SourceInput)->FlagRules` validates selected DDI; it does not read live documentation.

`WeightedSource` is frozen with `frame:pl.LazyFrame`, `diagnostics:pl.DataFrame`, `rules:dict`; `weighted_source(selected:SelectedTargets,scratch:Path)` is a context manager yielding it while its decompressed CSV and owned temporary scan remain alive. The frame is the core companion plus exact 81 weight replacements at the identical source positions. No lazy computation escapes that lifetime unless materialized to an owned temporary aggregate.

`FamilyRows` is frozen with `members:pl.LazyFrame`, `diagnostics:pl.LazyFrame`, `product:Product`. Members retain source identity internally, native units, relevant scalar/node/factor keys, provenance flags and exact 81 weights; not published. `family_rows(frame:pl.LazyFrame, product:Product, rules:FlagRules, units:pl.DataFrame)->FamilyRows` implements each explicit pair. `canonical_rows(rows:FamilyRows,nodes:dict[str,pl.DataFrame])->FamilyRows` filters before reaggregation.

Required family inputs are exhaustive; do not apply all three role lookups to every family:

| Family / dimension | Usable pair code dimensions | Required domestic role endpoints | At-work/non-home transport rule |
| --- | --- | --- | --- |
| staffing_pattern / industry_occupation | industry and occupation | none | no |
| area_mix / industry | industry | workplace only | yes |
| area_mix / occupation | occupation | workplace only | yes |
| commuting_flow / flow | none | residence and workplace | yes |
| migration_flow / flow | none | migration and residence | no; require domestic MIGRATE1 2/3 |

All required Q flags still follow the spec's family/universe matrix. Strict QIND/QOCC evidence requires their associated substantive fields to be applicable/usable even when a code dimension is not a pair endpoint. Sensitivity retains the approved family substantive/endpoint rules; do not add unused geography, transportation, or pair-code restrictions. Known unused fields/statuses remain diagnostic, never inferred as clean. Unknown nonmissing flag values still fail global rule validation.

`AggregateSet` is frozen with `cells:pl.LazyFrame`, `denominators:pl.LazyFrame`, `diagnostics:pl.LazyFrame`, `product:Product`. Internal cell/denominator masses use long columns `component_year:Int64` (0 or annual), `replicate:UInt8` (0..80), `sum_exact:String` (native) or `mass:Float64` (allocated **unpooled** mass), `n_unweighted:UInt64`, `fractional_support_mass:Float64`, keys/unit/provenance. `aggregate_native(rows:FamilyRows)->AggregateSet` computes native sums without Float conversion. Every internal annual/pooled sum_exact or allocated mass is **unpooled with respect to k**: annual rows sum that year, component_year=0 sums all declared years. County/MSA factors multiply those raw sums; only estimate and residual serialization apply k, exactly once. Never feed published annual-average masses back into allocation. `allocate_area_mix(native:AggregateSet,county_factors:pl.DataFrame,counties:pl.DataFrame,product:Product)->tuple[AggregateSet,pl.LazyFrame]` returns allocated aggregates and residual rows. `estimate(aggregates:AggregateSet)->dict[str,pl.LazyFrame]` returns `targets`, `support`, `replicates`. `derive_tables(selected:SelectedTargets,scratch:Path)->dict[str,pl.DataFrame|pl.LazyFrame]` returns exactly the eight named output tables; spill bounded aggregates to an owned temporary directory if needed, never source/companion files.

## Automated invariant map

This is the develop-testing-strategy plan for this stage. All listed pytest files are hermetic, unmarked, and collected by the existing default command. Expected values below are handwritten, not produced by production eligibility/estimation helpers. Use temporary data roots, genuine manifested synthetic deliveries and public-original reference fixtures at the integration layer.

| Invariant | Cheapest layer and fixture | Exact focused command (prefix each with `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked`) |
| --- | --- | --- |
| Exact ordered schemas, unique logical keys across SE variants, sorted lists/metadata, unit membership | 1–3 row serialization/unit cases; flags-only and se_method-only collisions | `pytest tests/test_acs_target_contract.py tests/test_acs_target_units.py -q` |
| Selected mapping pin/request/source/software equality; no relaxed D5 | Real authenticated Stage 8 fixture; wrong pin/request/receipt/source/software mutations | `pytest tests/test_acs_target_inputs.py -q` |
| Every required Q flag, raw type/domain, NIU/edited/allocated/missing and unknown refusal | Hand-labeled DDI + tiny applicable/NIU records | `pytest tests/test_acs_target_rules.py tests/test_acs_target_membership.py -q` |
| Civilian/private membership, absence vs at-work, home exclusion, domestic migration, periods/matched sensitivity | Truth-table source cases, null String 2023 QMIGRAT1 and String 0/4 in 2024 | `pytest tests/test_acs_target_membership.py -q` |
| Literal factor-1 weights and original positional alignment, 81 required columns, invalid lexemes/overflow | Small manifested gzip/DDI/Parquet + companion; duplicates and signed weights | `pytest tests/test_acs_target_weights.py -q` |
| Unequal-year pooling, correct ratio denominator/covariance, all 80 replicates, no missing-year divisor change | Hand arithmetic with different annual masses and interior replicate 37 | `pytest tests/test_acs_target_estimation.py -q` |
| Undefined full/replicate denominators; signed finite ratios retained; unavailable SE labeled | Zero denominators, negative replicate mass, full positive cells with an undefined replicate | `pytest tests/test_acs_target_estimation.py tests/test_acs_target_tables.py -q` |
| No mapping fan-out/dedup, canonical scalar-vs-singleton support and own denominators | Duplicate positions, ambiguous candidates, flagged scalar and 559830 | `pytest tests/test_acs_target_projection.py -q` |
| County/MSA conservation for full/80 replicates, nonadditive input counts, zero factors, CT/cross-state frames | Rational 1/4,1/2,1/4 factors, two counties in one MSA, micro/no-CBSA; nine CT controls | `pytest tests/test_acs_target_projection.py -q` |
| Exclusive output/staging, symlinks, corruption, detached authority first, reconstruction of rules/report | Real fixture bundle + self-consistent semantic mutations, concurrent final directory | `pytest tests/test_acs_target_bundle.py tests/test_acs_target_cli.py -q` |
| Genuine raw→conversion→4/5/7/8→four family targets→replay/detached verification; zero access attempts | Authenticated Stage 8 fixture extension and Stage 6 seam | `pytest tests/test_acs_target_v12.py tests/test_target_contract_v12.py -q` |
| Independent science detects wrong mass/ratio/replicate/coverage/residual after repinning | Independently implemented raw/DDI/reference calculations and adversarial fixture bundle | `pytest tests/test_acs_targets_reconciliation.py -q` |
| Exact manifest prefix, all selected upstream bytes and accounted suffix | Freeze/preservation fixture mutations (including JSON-equivalent byte changes) | `pytest tests/test_acs_targets_reconciliation.py -q` |
| Production science beyond fixtures | Explicit later first/replay, public verifiers and independent full-data command | Task 10 commands; never pytest against the real root |

### Task 1: Freeze product, schema and statistic identity contracts

**Files:**

- Create: `src/embedding_data/acs_target_contract.py`
- Create: `tests/acs_target_fixtures.py`
- Test (create): `tests/test_acs_target_contract.py`

**Interfaces:** Consumes unchanged Stage 8 `CODE_SCHEMA` and Stage 6 `TARGET_SCHEMA`/`TARGET_KEY_COLUMNS`/`validate_targets`. Produces `Product`, `PRODUCTS:tuple[Product,...]`, the five auxiliary schema dictionaries above, `TARGET_STAT_KEY_COLUMNS:list[str]`, `STAT_KEY_COLUMNS:list[str]`, `CELL_KEY_COLUMNS:list[str]`, `observed_counterpart(product:Product)->Product`, `validate_auxiliary(name:str,frame:pl.DataFrame|pl.LazyFrame)->None`, `validate_statistic_keys(frame:pl.DataFrame|pl.LazyFrame)->None`, and `validate_cross_tables(tables:dict[str,pl.DataFrame|pl.LazyFrame],products:tuple[Product,...])->None`. `validate_cross_tables` gains its value reconciliation in Task 7; Task 1 implements structural/key/unit checks only, with tests for that contract. Fixtures produce `minimal_target(**changes)->dict` and `weights(point:str,overrides:dict[int,str]|None=None)->dict[str,str]`.

- [ ] **Step 1: Write independent key/schema regression tests and fixture primitives.**

```python
# tests/acs_target_fixtures.py
from embedding_data.target_contract import TARGET_SCHEMA


def minimal_target(**changes):
    row = dict(zip(TARGET_SCHEMA, (
        'acs', 'staffing_pattern', 'acs_industry_category',
        'feature:acs_industry_category:industry-a', 'acs_occupation_category',
        'feature:acs_occupation_category:occupation-a', 'forward_share',
        0.25, 0.0, 'replicate', 2, 25.0, 'annual-core-2023-2024',
        'acs-naics2022-soc2018', 'civilian_employed:strict', ['size_gate_pending'],
    ), strict=True))
    return row | changes


def weights(point, overrides=None):
    overrides = overrides or {}
    return {'PERWT': point} | {
        f'REPWTP{r}': overrides.get(r, point) for r in range(1, 81)
    }
```

```python
# tests/test_acs_target_contract.py
import polars as pl
import pytest
from acs_target_fixtures import minimal_target
from embedding_data.acs_target_contract import PRODUCTS, validate_statistic_keys
from embedding_data.target_contract import TARGET_SCHEMA


def test_flags_or_se_method_cannot_identify_another_statistic():
    first = minimal_target()
    for changed in (
        minimal_target(flags=['allocated_source', 'size_gate_pending']),
        minimal_target(se=None, se_method='none'),
    ):
        frame = pl.DataFrame([first, changed], schema=TARGET_SCHEMA)
        with pytest.raises(ValueError, match='logical statistic'):
            validate_statistic_keys(frame)


def test_declared_products_freeze_periods_without_observed_year_inference():
    assert len(PRODUCTS) == 50
    observed = [p for p in PRODUCTS if p.view == 'observed']
    assert len(observed) == 22
    migration = [p for p in observed if p.family == 'migration_flow']
    assert sorted((p.evidence_policy, p.years, p.pool_divisor) for p in migration) == (
        [('sensitivity', (2023, 2024), 2)] * 2
        + [('sensitivity', (2024,), 1)] * 2
        + [('strict', (2024,), 1)] * 2
    )
```

Also write literal ordered-schema assertions for all five auxiliaries (compare ordered `(name,dtype)` pairs to the dictionaries printed above, not two imports of the same constant). Parametrize duplicate keys, null lists/elements, misaligned paths, forbidden microdata field, extra/missing/reordered columns, nonfinite floats, unsupported replicate numbers and undefined reasons. Empty typed tables must pass; null required scalars must fail.

- [ ] **Step 2: Run the new contract tests red.** Run `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_target_contract.py -q`. Expect import/undefined-contract failure before implementation; afterward any wrong shape/key must still fail its specific regression.

- [ ] **Step 3: Implement the declared dataclasses/registries and validators.** Use exact schemas and literal product templates; expand only the two named universes/evidence policies/views from the product matrix, not data-driven periods. Implement the key check as follows, while preserving the generic writer:

```python
TARGET_STAT_KEY_COLUMNS = [name for name in TARGET_KEY_COLUMNS if name != 'se_method']
STAT_KEY_COLUMNS = ['view', *TARGET_STAT_KEY_COLUMNS]
CELL_KEY_COLUMNS = [name for name in STAT_KEY_COLUMNS if name != 'measure']


def validate_statistic_keys(frame):
    lf = frame.lazy() if isinstance(frame, pl.DataFrame) else frame
    duplicate = (lf.group_by(TARGET_STAT_KEY_COLUMNS).len()
                 .filter(pl.col('len').gt(1)).select(pl.len()).collect().item())
    if duplicate:
        raise ValueError('duplicate logical statistic key')
```

For cross-table checks use view=observed for targets_observed and view=canonical for targets_canonical. In targets_allocated_area_mix, derive view=allocated_county only from unit_a_type='county', and view=allocated_msa only from unit_a_type='cbsa' whose registry membership is metropolitan; reject every other type/membership. The shared allocated filename alone cannot identify view. Then form the full auxiliary statistic key. A target must join exactly one pooled cell-support row and 80 replicate records on that view/key; every endpoint must join exactly one registry row. Anti-joins detect orphans; key validations precede joins. Validate numeric/status/null rules explicitly, never cast malformed output into compliance.

- [ ] **Step 4: Run focused checks green and preserve existing target-contract behavior.** Run `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_target_contract.py tests/test_target_contract.py -q`; expect all selected tests pass. Check empty product registry and typed empty auxiliaries serialize/reread with no schema drift.

- [ ] **Step 5: Commit the contract deliverable and approved plan.** `git add specs/plans/9-acs-targets.md src/embedding_data/acs_target_contract.py tests/acs_target_fixtures.py tests/test_acs_target_contract.py`; `git commit -m 'feat: define ACS target products and aggregate contracts'`. Keep normal hooks. Including the approved plan here makes the later git mv retirement valid even when the planning session left it untracked. Record the task review/checkpoint before Task 2; no Stage 9 tick.

### Task 2: Authenticate mapping selection and freeze Stage 9 software

**Files:**

- Create: `src/embedding_data/acs_target_inputs.py`
- Modify: `tests/acs_target_fixtures.py`
- Test (create): `tests/test_acs_target_inputs.py`

**Interfaces:** Consumes seven-field `SelectionRequest`, `acs_mapping_inputs.select_inputs`, `.verify()`, and public Stage 8 `verify_bundle`. Produces `SelectedTargets` as defined above; `select_targets(data_dir:Path,mapping_run:str,*,expected_mapping_outputs_sha256:str,request:SelectionRequest)->SelectedTargets`; `freeze_target_software()->dict`. Test fixture `authenticated_mapping(tmp_path:Path,monkeypatch,prepare_acs=None)->dict` wraps `seed_reconciliation_inputs(...,prepare_acs=...)` then `build_fixture_mapping(...,'mapping',...)`, returning data_dir, request, mapping path and detached build-response pin. It uses real existing fixture upstream selection, not a mocked SelectedInputs.

- [ ] **Step 1: Write authenticated selection tests.**

```python
import pytest
from acs_target_fixtures import authenticated_mapping
from embedding_data.acs_target_inputs import select_targets


def test_wrong_mapping_pin_is_rejected(tmp_path, monkeypatch):
    fixture = authenticated_mapping(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='checksum|pin'):
        select_targets(fixture['data_dir'], 'mapping',
                       expected_mapping_outputs_sha256='0' * 64,
                       request=fixture['request'])
```

Add cases mutating exactly one request field (including receipt pin), a recorded source identity/count, a companion byte, an upstream file, current software/dependency identity, or mapping recorded rules. For self-consistent metadata mutation recompute the local inventory and pass its new detached pin; selection must still reject request/rules/software disagreement. Verify selected core is the exact Stage 7 SourceInput and mapping companion path; `.verify()` detects a later mutation. A nonselected replay can never supply a missing first-run file. Existing Stage 8 tests retain the narrow D5 positive/negative cases; add a Stage 9 test requiring the exact inherited compatibility diagnostic in provenance, without inventing another exception.

- [ ] **Step 2: Run `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_target_inputs.py -q` red.** Expect missing new selector; no data/root fallback is permitted to make it pass.

- [ ] **Step 3: Implement selection binding and rechecks.** The security-relevant order is explicit:

```python
upstream = acs_mapping_inputs.select_inputs(data_dir, request)
upstream.verify()
directory = acs_mapping_bundle.run_directory(data_dir, mapping_run)
verified = acs_mapping_bundle.verify_bundle(
    directory, data_dir, expected_outputs_sha256=expected_mapping_outputs_sha256)
recorded = acs_mapping_inputs._read_json(directory / 'inputs.json')
if recorded['selected_upstreams']['request'] != asdict(request):
    raise ValueError('mapping upstream selection differs from explicit request')
if recorded['selected_upstreams']['provenance'] != upstream.provenance:
    raise ValueError('mapping upstream provenance differs')
```

Authenticate before reading mapping content. Require each recorded source definition/DDI/raw citation/Parquet identity to equal selected SourceInput after normalizing only its relative Path representation. Require mapped rules/frames to equal frozen Stage 8 constants. Enumerate all eight mapped tables by their exact names; no file discovery fallback. Record both selected physical pins and mapping's original software snapshot, then freeze current Stage 9 software separately.

`freeze_target_software` inventories existing `acs_mapping_inputs.SOFTWARE_FILES` plus unchanged `target_contract.py` and every new `acs_target_*`/`acs_targets.py` member introduced by this plan; include only members that exist at this task checkpoint, expanding the literal member list as later files land. Also freeze pyproject/lock, Python full identity and all installed distribution versions. Before production measurement the list is complete and frozen; no missing-file skip at runtime. Independent acceptance code gets its own complete inventory in Task 9. Rechecks compare new snapshot equality, not only git labels; later source/docs commits cannot substitute for file hashes.

- [ ] **Step 4: Run focused selector and original Stage 8 selector tests green.** `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_target_inputs.py tests/test_acs_mapping_inputs.py -q`. Expect all pass, real fixture provenance authenticated, zero external accesses. Verify `git diff -- src/embedding_data/acs_mapping_inputs.py src/embedding_data/cli.py src/embedding_data/target_contract.py` is empty.

- [ ] **Step 5: Commit.** `git add src/embedding_data/acs_target_inputs.py tests/acs_target_fixtures.py tests/test_acs_target_inputs.py`; `git commit -m 'feat: bind ACS targets to authenticated mapping selections'`. Review before continuing.

### Task 3: Validate delivered evidence rules and build complete aggregate units

**Files:**

- Create: `src/embedding_data/acs_target_rules.py`
- Create: `src/embedding_data/acs_target_units.py`
- Modify: `src/embedding_data/acs_target_inputs.py`
- Modify: `tests/acs_target_fixtures.py`
- Test (create): `tests/test_acs_target_rules.py`
- Test (create): `tests/test_acs_target_units.py`

**Interfaces:** Consumes selected SourceInput.ddi, complete Stage 8 CODE_SCHEMA/AREA_SCHEMA and selected node tables. Produces `FlagRules`, `read_rules(source:SourceInput)->FlagRules`, `classify_flag(value:str|None,variable:str,applicable:bool,rules:FlagRules)->str`, `required_flags(family:str,base_universe:str)->tuple[str,...]`, `build_units(selected:SelectedTargets)->pl.DataFrame`, `observed_unit` and `puma_unit` exactly as above. Evidence status is `nonallocation`, `allocated`, `edited_failed_edit`, `unavailable`, `not_applicable`. Rules preserve separate Stage 8 annotations; do not overwrite them.

- [ ] **Step 1: Write per-variable/domain/applicability tests before rules.**

```python
# A direct tiny dictionary tests semantics independently of a full bundle.
import pytest
from embedding_data.acs_target_rules import FlagRules, classify_flag, required_flags


def test_zero_needs_substantive_applicability_and_missing_is_unavailable():
    rules = FlagRules('acs-target-rules-v1', {
        'QIND': {'dtype': 'Int64', 'values': {
            '0': {'label': 'Original entry or Inapplicable (not in universe)',
                  'status': 'nonallocation'},
            '1': {'label': 'Allocated', 'status': 'allocated'},
        }},
    }, {}, {})
    assert classify_flag('0', 'QIND', True, rules) == 'nonallocation'
    assert classify_flag('0', 'QIND', False, rules) == 'not_applicable'
    assert classify_flag(None, 'QIND', True, rules) == 'unavailable'
    with pytest.raises(ValueError, match='domain'):
        classify_flag('9', 'QIND', True, rules)


def test_required_evidence_is_family_and_universe_specific():
    assert set(required_flags('migration_flow', 'private_wage_salary')) == {
        'QEMPSTAT', 'QIND', 'QOCC', 'QCLASSWK', 'QMIGRAT1', 'QMIGPLC1',
    }
```

Add a case for every flag in the Global Constraints, both original integer/string storage, missing variable and null values, separately labeled failed edits, unknown nonmissing values, unknown DDI labels, duplicate DDI values, and ambiguous zero on a substantive NIU. Unknown domain values fail even in sensitivity or outside substantive eligibility; do not let the exclusion funnel conceal malformed delivered evidence. Freeze all delivered label/value pairs in the rules record; classification must not use a generic nonzero Boolean or infer from another variable/delivery.

For units test `observed_unit('soc','special')` is a feature unit and accepts an authenticated empty-candidate 559830 record, whose scalar remains null; two source lookup keys sharing a token remain different category IDs. Verify every CODE_SCHEMA field/path/locator survives verbatim, role-use lists union without duplicate registry rows, and selected canonical/county/MSA IDs have exact reference membership. Alter candidate/path alignment or node level and expect failure.

- [ ] **Step 2: Run rules/units tests red.** `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_target_rules.py tests/test_acs_target_units.py -q`; expect missing implementation.

- [ ] **Step 3: Implement exact DDI validation and the unit registry.** At execution, authenticated delivered DDI is the authority: inspect its exact category labels, codes, instructions and original dtypes, then author an explicit field-specific value/label/status table in `read_rules`; tests pin those pairs and their DDI locators. Do not acquire documentation or choose a new interpretation. A pair whose meaning cannot be classified into the five approved statuses raises ValueError and stops that run for investigation; no broad string-substring matcher or numeric-range membership. Preserve raw DDI metadata in inputs, including not-applicable/unavailable distinctions. Category-set validation is exact:

```python
UNIVERSE_CODES = {
    'EMPSTATD': {'10': 'At work', '12': 'Has job, not working'},
    'CLASSWKRD': {'22': 'Wage/salary, private', '23': 'Wage/salary at non-profit'},
}


def classify_flag(value, variable, applicable, rules):
    domain = rules.domains.get(variable)
    if value is not None and (domain is None or value not in domain['values']):
        raise ValueError('unexpected nonmissing flag domain value')
    if not applicable:
        return 'not_applicable'
    if value is None or domain is None:
        return 'unavailable'
    return domain['values'][value]['status']
```

Validate selected DDI EMPSTATD/CLASSWKRD code labels against the owner-adopted sets (retain exact full delivered wording in inputs; a documented typography-only label difference is checked explicitly rather than expanding membership). Validate MIGRATE1 2/3 and TRANWORK home/NIU/applicable categories independently from their Q flags. The 2023 all-null String QMIGRAT1 remains unavailable; 2024 String 0/4 is independently documented. PUMA-specific allocation flags are undelivered and are reported as a limitation, never invented as clean.

Build units by unique native code_lookup_id and normalized physical area definition, then selected nodes actually used by permitted projections. Preserve complete category records. Join role/area provenance many-to-one after uniqueness checks; coalesce only identical physical identity, not lookup keys. Use typed empty list expressions for inapplicable lists. Never explode candidates into target membership.

- [ ] **Step 4: Run rules/units and selected contract tests green.** `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_target_rules.py tests/test_acs_target_units.py tests/test_acs_target_contract.py -q`; expect all pass, with integer/string evidence and all required flags covered.

- [ ] **Step 5: Commit.** `git add src/embedding_data/acs_target_rules.py src/embedding_data/acs_target_units.py src/embedding_data/acs_target_inputs.py tests/acs_target_fixtures.py tests/test_acs_target_rules.py tests/test_acs_target_units.py`; `git commit -m 'feat: define delivered ACS evidence and aggregate unit identities'`. Review the explicit DDI table and metadata before Task 4.

### Task 4: Align exact weights and construct explicit family memberships

**Files:**

- Create: `src/embedding_data/acs_target_weights.py`
- Create: `src/embedding_data/acs_target_membership.py`
- Modify: `src/embedding_data/acs_target_inputs.py`
- Modify: `tests/acs_target_fixtures.py`
- Test (create): `tests/test_acs_target_weights.py`
- Test (create): `tests/test_acs_target_membership.py`

**Interfaces:** Consumes `SelectedTargets`, `FlagRules`, `Product`, unit registry and the unchanged lexical scan/decompression APIs. Produces `WeightedSource`/`weighted_source(selected,scratch)` and `FamilyRows`/`family_rows(frame,product,rules,units)` defined above. Test fixtures add `membership_frame(records:list[dict])->pl.LazyFrame`, `membership_rules()->FlagRules` and `membership_units()->pl.DataFrame`: explicit synthetic records/DDI/units for mathematical tests only, never a selected-input replacement in bundle tests. Add `prepare_target_delivery(profile:str,ddi:dict,frame:pl.LazyFrame)->tuple[dict,pl.LazyFrame]` in the new fixture module now, so Tasks7–9 can compose it through authenticated_mapping before Task8; it supplies the usable substantive fields and exact synthetic Q/category domains described by the Task8 raw-chain fixture (including its converter-produced Int64 migration flag, with production String cases kept in direct unit tests), in raw CSV/DDI before conversion. No generated source/companion is patched after publication. Default fixture year/sample is annual2024/us2024a; each row has source hash/UInt64 position, year/sample, usable observed/scalar code keys, three role annotations, original EMPSTATD/CLASSWKRD/TRANWORK/MIGRATE1 and required Q values, plus exact Decimal weights.

- [ ] **Step 1: Write weight alignment and hand-labeled membership tests.** Build a tiny manifested gzip with identical repeated source records at distinct positions and weights `100.25`, `-2.5` on an interior replicate. Use actual unchanged conversion and actual Stage 8 fixture mapping for alignment tests. Assert exact decimal PERWT is 100.25, never 1.0025, original source row count/order/hash match and REPWTP remains excluded from the 81 estimator weights. Mutate a raw row, companion row, nonweight value, count/order, source hash, required weight null, missing/extra numbered replicate, exponent, invalid lexeme and Decimal38 overflow; each must fail before aggregation. Read required raw scan columns positionally, compare nonweights with original Parquet/companion using exact ordered parity, and consume the lazy scan before the temporary CSV closes.

Write the following truth-table test using a local `membership_frame` that assigns all Q flags String `'0'`, EMPSTATD=10, CLASSWKRD=22, MIGRATE1=2, applicable domestic roles and TRANWORK=10 unless explicitly overridden. Each override remains visible in source evidence; evidence classification comes from the separately handwritten fixture rules.

```python
import polars as pl
from acs_target_fixtures import membership_frame, membership_rules, membership_units
from embedding_data.acs_target_contract import PRODUCTS
from embedding_data.acs_target_membership import family_rows


def test_workplace_excludes_absent_home_and_niu_in_both_policies():
    frame = membership_frame([
        {'source_row': 0},
        {'source_row': 1, 'EMPSTATD': 12},
        {'source_row': 2, 'TRANWORK': 80},
        {'source_row': 3, 'TRANWORK': 0},
        {'source_row': 4, 'QTRANWOR': '4'},
    ])
    products = [p for p in PRODUCTS if p.view == 'observed'
                and p.family == 'area_mix' and p.dimension == 'industry'
                and p.base_universe == 'civilian_employed']
    observed = {}
    for product in products:
        rows = family_rows(frame, product, membership_rules(), membership_units())
        observed[product.evidence_policy] = rows.members.select('source_row').collect().to_series().to_list()
    assert observed == {'strict': [0], 'sensitivity': [0, 4]}
```

Add explicit unused-role regression cases so the exclusion funnel cannot shrink the approved universes:

```python
import pytest


@pytest.mark.parametrize('family,dimension,changes', [
    ('staffing_pattern', 'industry_occupation', {
        'EMPSTATD': 12, 'TRANWORK': 0, 'MIGRATE1': 1,
        'residence_area_status': 'niu_or_unidentifiable', 'residence_factor_key': None,
        'workplace_area_status': 'foreign', 'workplace_factor_key': None,
        'migration_area_status': 'documented_unavailable', 'migration_factor_key': None,
    }),
    ('area_mix', 'industry', {
        'residence_area_status': 'niu_or_unidentifiable', 'residence_factor_key': None,
        'migration_area_status': 'foreign', 'migration_factor_key': None,
    }),
    ('commuting_flow', 'flow', {
        'MIGRATE1': 1, 'migration_area_status': 'niu_or_unidentifiable',
        'migration_factor_key': None,
    }),
    ('migration_flow', 'flow', {
        'EMPSTATD': 12, 'TRANWORK': 80, 'workplace_area_status': 'foreign',
        'workplace_factor_key': None,
    }),
])
def test_unused_roles_do_not_exclude_eligible_pairs(family, dimension, changes):
    product = next(p for p in PRODUCTS if p.view == 'observed'
                   and p.family == family and p.dimension == dimension
                   and p.base_universe == 'civilian_employed' and p.evidence_policy == 'strict')
    rows = family_rows(membership_frame([{'source_row': 0} | changes]), product,
                       membership_rules(), membership_units())
    assert rows.members.select('source_row').collect().to_series().to_list() == [0]
```

Also hand-label staffing's temporarily absent inclusion; armed forces exclusion independent of OCCSOC 559830; private codes22/23 included and both self-employment classes excluded; every required Q flag individually allocated/edited/null; QCLASSWK only required in private; extra family-specific flags do not contaminate staffing; foreign/territory/NIU endpoints and unknown movers excluded; stayers never form self-loops; equal numeric residence/work-migration codes retain different typed endpoints. For migration expect strict2024 and matched2024 rows only from2024, pooled sensitivity from both years, with 2023 null-QMIGRAT1 counted unavailable. Sensitivity never restores a required unusable category/endpoint.

- [ ] **Step 2: Run weight/membership tests red.** `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_target_weights.py tests/test_acs_target_membership.py -q`; expect missing weight/membership implementation.

- [ ] **Step 3: Implement owned exact scanning and the five pair builders.**

```python
# Inside weighted_source(selected, scratch); imports come from the frozen seams.
source = selected.upstream.sources['acs/core']
csv_citations = [item for item in source.raw_citations if item['path'].endswith('.csv.gz')]
if len(csv_citations) != 1:
    raise ValueError('one authenticated core CSV is required')
raw_csv = target_io.relative_file(selected.data_dir / 'raw', csv_citations[0]['path'])
with ipums_conversion.decompressed_csv(raw_csv, scratch) as csv_path:
    diagnostics, weight_rules = ipums_weights.measure_weights(csv_path, source.ddi, 'acs', 'core')
    numeric = ipums_weights.scan_numeric_csv(csv_path, diagnostics, 'acs')
    names = ['PERWT', *(f'REPWTP{r}' for r in range(1, 81))]
    required = diagnostics.filter(pl.col('variable').is_in(names))
    if set(required['variable']) != set(names):
        raise ValueError('missing required person or replicate weights')
    if required.select(pl.col('null_rows').sum()).item():
        raise ValueError('required weight is missing')
    indexed = numeric.with_row_index('source_row').with_columns(
        pl.col('source_row').cast(pl.UInt64))
    companion = pl.scan_parquet(selected.tables['acs_core_canonical'])
    original = pl.scan_parquet(source.parquet).with_row_index('source_row').with_columns(
        pl.col('source_row').cast(pl.UInt64))
    all_weight_names = set(diagnostics['variable'])
    nonweights = ['source_row', *[name for name in pl.scan_parquet(source.parquet)
                                 .collect_schema().names() if name not in all_weight_names]]
    for left, right in ((indexed, original), (original, companion)):
        compared = ipums_parity.compare_ordered(left.select(nonweights), right.select(nonweights))
        if not compared['values_equal']:
            raise ValueError('ordered source values differ before exact-weight alignment')
    identity_bad = companion.select(
        pl.col('source_parquet_sha256').ne(source.parquet_record['sha256']).any()).collect().item()
    if identity_bad:
        raise ValueError('companion source hash differs')
    frame = (companion.drop(names).join(indexed.select('source_row', *names),
             on='source_row', how='left', validate='1:1', maintain_order='left'))
    yield WeightedSource(frame, diagnostics, weight_rules)
    selected.verify()
```

Before yielding, additionally validate ordered source/companion schemas and row counts against recorded evidence; the ordered nonweight comparison above is the minimum alignment code. Mandatory pre-join validation includes: compare schema/row count, ordered source_row range, original source hash and every nonweight column, using the shipped ordered-parity seam and source prefix schema. Joins must declare one-to-one cardinality, retain companion order and preserve original values. Recheck selected bytes after the scan. Reject numerical errors rather than filtering bad records. Do not let Polars expressions outlive decompressed_csv; materialize native aggregates within the context. Household diagnostics can be retained as provenance but never enter target weights. Reject unexpected numbered ACS person replicates outside 1..80; REPWTP itself remains an availability helper.

Implement small explicit family branches returning unit_a/unit_b and denominator grain (same unit_a, code dimension and product). Apply ordered first-exclusion precedence: outside declared period; outside civilian universe; outside private universe when applicable; family substantive unusable code/mover/at-work/transport rules; residence endpoint status; workplace endpoint status; migration endpoint status; required Q evidence failure (strict only); eligible. Task6 canonical_rows partitions the remaining eligible records into unsupported-leaf versus eligible for canonical views and reconciles that additional exclusion without double counting. Evaluate endpoint exclusions only for the roles in the required-family-input table; distinguish each required role's niu/foreign/territory/unavailable reason. Missing unused roles must pass the regression cases above. Use the exact substantive family rules from the spec; evidence is evaluated with associated-field applicability, not a numeric zero shortcut. In sensitivity preserve allocated/edited/unavailable inclusion reasons as overlapping diagnostics. A not-applicable flag cannot certify strict nonallocation; do not treat it as an allocation event or fill missing geography.

For each product/year the first-exclusion partition includes all selected core rows of that annual source, including out-of-period rows as that explicit reason. Keep disjoint counts separate from overlapping raw flag/evidence/limitation counts. This permits strict2024 products to account explicitly for excluded2023. Do not sum denominators over overlapping diagnostic partitions. Emit 559830 civilian/special combinations and unavailable PUMA-specific evidence separately. Native target flags are sorted unions of supported input provenance plus required `size_gate_pending`; a positive flag means some supporting evidence, not unanimity.

- [ ] **Step 4: Run focused checks green.** `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_target_weights.py tests/test_acs_target_membership.py tests/test_ipums_weights.py -q`; expect all pass. Verify each family/product's funnel n and exact weight sums close to its source-year totals, duplicate positions remain distinct, and every external-access counter is zero.

- [ ] **Step 5: Commit.** `git add src/embedding_data/acs_target_weights.py src/embedding_data/acs_target_membership.py src/embedding_data/acs_target_inputs.py tests/acs_target_fixtures.py tests/test_acs_target_weights.py tests/test_acs_target_membership.py`; `git commit -m 'feat: construct ACS family eligibility with exact aligned weights'`. Review before estimation.

### Task 5: Pool native totals and recompute all replicate statistics

**Files:**

- Create: `src/embedding_data/acs_target_estimation.py`
- Modify: `src/embedding_data/acs_target_inputs.py`
- Modify: `tests/acs_target_fixtures.py`
- Test (create): `tests/test_acs_target_estimation.py`

**Interfaces:** Consumes FamilyRows/Product with exact 81 weights and immutable membership. Produces `aggregate_native(rows:FamilyRows)->AggregateSet`, `estimate(aggregates:AggregateSet)->dict[str,pl.LazyFrame]`, plus pure `replicate_se(full:float,replicates:tuple[float|None,...])->float|None`. Returned dictionary keys are `targets`, `support`, `replicates`; support/replicate schemas are fixed above. Test fixture `estimate_case(records:list[dict],*,years:tuple[int,...]=(2023,2024),pool_divisor:int=2)->dict[str,pl.DataFrame]` uses declared synthetic family members with all 81 weights from `weights`, builds FamilyRows, then calls the actual native aggregate/estimate functions; expected values remain test literals.

- [ ] **Step 1: Write arithmetic and undefined-value tests.**

```python
from math import sqrt
import pytest
from acs_target_fixtures import estimate_case, weights


def test_ratio_of_pooled_totals_and_interior_replicate_covariance():
    result = estimate_case([
        {'year': 2023, 'a': 'industry', 'b': 'A', **weights('10', {37: '30'})},
        {'year': 2023, 'a': 'industry', 'b': 'B', **weights('30')},
        {'year': 2024, 'a': 'industry', 'b': 'A', **weights('100')},
        {'year': 2024, 'a': 'industry', 'b': 'B', **weights('100')},
    ])
    a = result['targets'].filter(
        (pl.col('unit_b') == 'feature:acs_occupation_category:A')
        & (pl.col('measure') == 'forward_share')).row(0, named=True)
    assert a['value'] == pytest.approx(11 / 24, rel=0, abs=1e-12)
    assert a['n_weighted'] == 55.0
    assert a['n_unweighted'] == 2
    assert a['se'] == pytest.approx(1 / (24 * sqrt(20)), rel=0, abs=1e-12)
    replicates = result['replicates'].filter(
        (pl.col('unit_b') == a['unit_b']) & (pl.col('measure') == 'forward_share'))
    assert replicates['replicate'].to_list() == list(range(1, 81))
    assert replicates.filter(pl.col('replicate') == 37)['estimate'].item() == 0.5
```

Include `import polars as pl` in that test file. For totals, the same A has full55, replicate37=65 and SE=sqrt(5). A cell supported only in2023 still divides by2; the2024-only product divides by1. Native exact sums are asserted as Decimal strings before Float64. Property tests can split one record into two positions whose Decimal weights sum to the original: masses/shares/SEs stay fixed, n changes, proving no dedup or weight normalization.

Test full denominator0: no fabricated share or zero target, explicit denominator_status/support, all replicate evidence retained. Test positive full share with replicate37 denominator0: point retained with `se=None`, `se_method='none'`, reason plus `[37]`; total SE remains defined if its numerator replicates are finite. Test a finite signed replicate ratio above1 (A=-10, B=5 gives ratio2) and negative denominators: keep signed estimate, no clipping. Change replicate1,37,80 independently to ensure all positions contribute. Add a full-denominator-zero fixture with finite replicate37 denominator to require that replicate's defined ratio is retained although the full share/SE is undefined. Assert support annual rows carry pooled statuses and only contribution masses differ. Missing replicate/invalid/nonfinite full input fails rather than producing an unavailable-SE explanation. No mean-of-annual-shares or independently combined numerator/denominator SE is accepted.

- [ ] **Step 2: Run `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_target_estimation.py -q` red.** Expect missing aggregation/estimator, then numeric regressions until exact behavior is implemented.

- [ ] **Step 3: Implement native Decimal grouping, denominator joins and complete estimation.** Group only eligible observed pair members by product/year/unit pair; aggregate exact PERWT and each numbered replicate, retain counts/mapping flag unions. Build denominators from those same eligible members at unit_a/dimension/product grain, never a broader population. Recheck join uniqueness before pairing cells/denominators. Retain annual raw sums and pooled raw sums; for each supported pooled statistic emit one support contribution per declared annual component, filling an absent component with exact zero mass and zero n. This fills contribution metadata only, never an unobserved target Cartesian product. Apply k from Product after summing, not from observed years. Use Decimal38 at verified source scale and an explicit overflow bound; for k=2 division retain one extra decimal place, failing unsupported precision rather than silently rounding exact native sums.

Core SE implementation (use ordered r=1..80, full estimate at matching measure):

```python
import math


def replicate_se(full, replicates):
    if len(replicates) != 80:
        raise ValueError('exactly 80 replicates required')
    if not math.isfinite(full):
        raise ValueError('nonfinite full estimate')
    if any(value is not None and not math.isfinite(value) for value in replicates):
        raise ValueError('undefined replicate must carry an explicit status')
    if any(value is None for value in replicates):
        return None
    return math.sqrt((4 / 80) * math.fsum((value - full) ** 2 for value in replicates))
```

Production aggregation remains lazy Polars; use this pure scalar function at the bounded 80-statistic finalization boundary, not a row-wise microdata callback. Shares use pooled numerator/denominator, and each replicate changes both. Native sums stay exact until final numeric evaluation. Full nonfinite estimates fail. Full n_weighted must satisfy the unchanged shared validator; never delete a negative-weight record to repair a mass. Zero/nonfinite replicate ratio creates explicit status; finite signed ratios are defined. An undefined ratio never disables an otherwise defined total SE. Compute each replicate statistic on its own terms even if the full share is undefined; keep finite replicate ratios and all numerator/denominator evidence. A mathematically defined full point with no positive cell mass stays unpublished but is retained in audit support. Publish full positive cells only, keep supported zero cells in diagnostics/support, and retain all80 per-measure replicate rows with reasons. Full denominator<=0 has no forward_share target; annual support contributions are not interpreted as annual estimates with their own SEs.

- [ ] **Step 4: Run estimator and shared validation tests green.** `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_target_estimation.py tests/test_acs_target_contract.py tests/test_target_contract.py -q`; expect all pass, exact native sums and fixed k validated, all80 numbers retained.

- [ ] **Step 5: Commit.** `git add src/embedding_data/acs_target_estimation.py src/embedding_data/acs_target_inputs.py tests/acs_target_fixtures.py tests/test_acs_target_estimation.py`; `git commit -m 'feat: estimate pooled ACS totals shares and replicate uncertainty'`. Review arithmetic independently before projections.

### Task 6: Project supported leaves and conserve county/MSA mass

**Files:**

- Create: `src/embedding_data/acs_target_projection.py`
- Modify: `src/embedding_data/acs_target_inputs.py`
- Modify: `tests/acs_target_fixtures.py`
- Test (create): `tests/test_acs_target_projection.py`

**Interfaces:** Consumes FamilyRows, AggregateSet, node tables, Stage 8 county factors and selected Stage 5 county_reference/typed county_cbsa membership. Produces `canonical_rows(rows:FamilyRows,nodes:dict[str,pl.DataFrame])->FamilyRows`, `allocate_area_mix(native:AggregateSet,county_factors:pl.DataFrame,counties:pl.DataFrame,product:Product)->tuple[AggregateSet,pl.LazyFrame]`. For allocated_msa compute county contributions first and roll those masses into selected metropolitan nodes; residual frame uses RESIDUAL_SCHEMA. Test fixture `projection_case()->dict` has the rational case below, including source positions and synthetic declared node tables for unit testing, distinct from authenticated V12.

- [ ] **Step 1: Write handwritten supported-leaf and conservation tests.** Canonical tests include two candidates with no scalar, one candidate without supported scalar, a valid detailed scalar, aggregate/partial flags on a scalar, a crosswalked scalar and approved559830 empty candidates. Strict canonical excludes crosswalked/source-recoded or imputed observations in each code dimension actually used; sensitivity preserves them if supported and otherwise eligible. Both retain provenance flags; subset denominator must be rebuilt. Make two observed categories map to one leaf without multiplying positions; staffing requires support on both used code dimensions, while each native area mix requires only its used dimension's supported leaf.

Rational allocation fixture uses k=2 with annual raw W1/codeA sums100 in2023 and100 in2024 (pooled raw200, published annual-average100), with counties C1/C2/C3 factors1/4,1/2,1/4 and an explicit C0 factor0. C1 and C2 belong to the same cross-state metropolitan CBSA, C3 to a micropolitan CBSA. W2/codeA has annual raw60 in each year (pooled raw120, annual-average60) and goes entirely to a no-CBSA county. Repeat with codeB to check denominators; use distinct signed interior replicate masses. Hand expectations: W1 A county masses25/50/25, metropolitan75, micropolitan residual25; W2 no-CBSA residual60. Zero C0 has no mass/support target. MSA n counts each W1 input position once, rather than adding its C1+C2 counts. Native n, allocated input n and fractional support mass are separate assertions.

```python
import polars as pl
import pytest
from acs_target_fixtures import projection_case
from embedding_data.acs_target_projection import allocate_area_mix
from embedding_data.acs_target_estimation import estimate


def test_workplace_allocation_keeps_metro_micro_and_no_cbsa_mass():
    case = projection_case()
    allocated, residuals = allocate_area_mix(
        case['native'], case['factors'], case['counties'], case['msa_product'])
    full = allocated.cells.filter((pl.col('replicate') == 0)
                                  & (pl.col('component_year') == 0)).collect()
    assert full.filter(pl.col('unit_b') == case['code_a'])['mass'].sum() == 150.0
    published = estimate(allocated)['targets'].collect()
    a_total = published.filter((pl.col('unit_b') == case['code_a'])
                               & (pl.col('measure') == 'annual_average_total'))
    assert a_total['value'].sum() == 75.0
    residual = residuals.filter((pl.col('replicate') == 0)
                               & (pl.col('component_year') == 0)
                               & (pl.col('code_unit') == case['code_a'])).collect()
    assert dict(residual.select('residual_type', 'weighted_mass').rows()) == {
        'micropolitan': 25.0, 'no_cbsa': 60.0,
    }
    assert full['n_unweighted'].max() == case['w1_input_count']
```

Add conservation for each annual/pooled component and every r0..80, factor1 still allocated, all-zero relation versus no relation, zero support, entirely absent MSA row, strict/sensitivity metadata and all nine CT planning regions. Reject use of residence MSA factor or invalid factor key, unknown county/CBSA, duplicate county membership and missing positive-factor coverage. Test exact logical repeatability at different Polars thread counts in fresh subprocesses using the same synthetic aggregate input; no network or real data.

- [ ] **Step 2: Run `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_target_projection.py -q` red.** Expect missing projections, followed by conservation/count regressions until implemented.

- [ ] **Step 3: Implement supported-subset reaggregation and deterministic factor reductions.** Canonical membership joins the frozen scalar ID to the selected node table and checks `level=='national_industry'` / `level=='detailed'` as actual selected node fields. Require the selected scalar node's system, vintage and level (NAICS2022 national_industry / SOC2018 detailed), not merely matching ID syntax. Native category candidate lists remain untouched. Reaggregate canonical FamilyRows and their denominators through Task5. Compute lost n/mass at whole-product and denominator grains against corresponding observed members using source-position membership internally; only aggregates are emitted. Preserve mapping flags even if the scalar exists.

For allocated area mixes, first aggregate by workplace factor_key + code category/year/r. Multiply exact native aggregates converted at this boundary by the selected factor. These are unpooled raw native sums, so factor application does not divide by k. estimate later divides the destination numerator and denominator exactly once; residual serialization divides its raw masses once. Keep only factor>0 for input-support counts; factor0 relations stay in reconciliation, with no support. Sort by destination key, source workplace unit, code unit, year/r and county ID; reduce Float64 contributions by an ordered cumulative operation rather than an unordered parallel group sum:

```python
# contributions has one row per destination/native group/county after bounded joins.
order = ['origin_workplace_unit', 'county_node_id']
keys = ['product_id', 'component_year', 'replicate', 'unit_a', 'unit_b']
ordered = contributions.sort(keys + order)
reduced = (ordered.with_columns(
    pl.col('contribution').cum_sum().over(keys, order_by=order).alias('mass'))
    .unique(subset=keys, keep='last', maintain_order=True))
```

Use full declared destination keys (including unit types and dimension) in implementation, not the shortened illustrative keys where ambiguity could occur. Construct metropolitan contributions by rolling the deterministic county masses through typed membership. For n, separately collapse positive county relationships by `(native workplace group,destination MSA)` before summing native-group counts; never sum county counts into MSA n. Fractional support sums positive factors times native n, so it can be additive while input n is not. Denominators are reaggregated at each county/MSA's own eligible destination/code grain, full and all replicates, with identical restrictions. Residuals keep micro/no-CBSA separately and never renormalize listed MSAs.

Compare native mass to counties, and counties to MSA+micro+no-CBSA at every component/r. Frame fields and allocation-conditional uncertainty limits enter both inputs and target/support flags; retain strict source evidence without claiming native county/MSA geography. No flow projection or residence-factor allocation path exists.

- [ ] **Step 4: Run projection/estimation tests green.** `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_target_projection.py tests/test_acs_target_estimation.py -q`; expect conservation, supported-subset denominators, nonadditive counts and exact repeatability pass. Independent numerical tolerances do not excuse replay differences.

- [ ] **Step 5: Commit.** `git add src/embedding_data/acs_target_projection.py src/embedding_data/acs_target_inputs.py tests/acs_target_fixtures.py tests/test_acs_target_projection.py`; `git commit -m 'feat: add supported ACS leaf and allocated area-mix views'`. Review before bundle assembly.

### Task 7: Assemble, publish and reconstruct the eleven-file bundle

**Files:**

- Create: `src/embedding_data/acs_target_tables.py`
- Create: `src/embedding_data/acs_target_bundle.py`
- Modify: `src/embedding_data/acs_target_contract.py`
- Modify: `src/embedding_data/acs_target_inputs.py`
- Modify: `tests/acs_target_fixtures.py`
- Test (create): `tests/test_acs_target_tables.py`
- Test (create): `tests/test_acs_target_bundle.py`

**Interfaces:** Consumes Tasks1–6 and unchanged single-file target writer, inventory helpers, safe_path and publish_directory. Produces:

```text
derive_tables(selected: SelectedTargets, scratch: Path) -> dict[str, pl.DataFrame | pl.LazyFrame]
write_tables(staging: Path, tables: dict[str, pl.DataFrame | pl.LazyFrame]) -> dict
build(data_dir: Path, run_id: str, mapping_run: str, *,
      expected_mapping_outputs_sha256: str, request: SelectionRequest) -> dict
verify_bundle(directory: Path, data_dir: Path, *, expected_outputs_sha256: str,
              mapping_run: str, expected_mapping_outputs_sha256: str) -> dict
compare_runs(first: Path, second: Path, *, data_dir: Path, mapping_run: str,
             expected_mapping_outputs_sha256: str) -> dict
run_directory(data_dir: Path, run_id: str) -> Path
```

Build returns run_id, directory, outputs_sha256. Verify returns status verified, physical pin, selected mapping identity and explicit limits, without treating process success as external scientific acceptance. Compare returns equal, per-table ordered schema/value status, substantive_report_equal, `trust_established=False`; mapping authentication does not authenticate the compared target bundles.

- [ ] **Step 1: Write bundle/cross-table adversarial tests.** Use authenticated_mapping plus full rule/estimator fixture extension. Build first/replay, independently hash each outputs.json, invoke both public verifiers, compare all eight tables, and check exact eleven-file inventory. A wrong external pin must fail before parsing deliberately malformed inputs.json. Rehash after modifying a valid target, support denominator, replicate37, missing-SE reason, unit mapping field, rule registry, diagnostic partition or residual; verification must reject semantic corruption even when file hashes agree with the replacement inventory. Test both county and metropolitan rows in the shared allocated file, requiring distinct correct auxiliary views without flags-based identification. Test duplicate logical key with differing flags/SE method, a target without matching pooled support/80 records, an orphan unit, and a false report count.

```python
import hashlib
from pathlib import Path
from embedding_data import acs_target_bundle as bundle


def test_two_detached_verifiers_and_exact_eight_table_replay(target_runs):
    first, replay = target_runs['first'], target_runs['replay']
    for directory in (first, replay):
        pin = hashlib.sha256((directory / 'outputs.json').read_bytes()).hexdigest()
        result = bundle.verify_bundle(
            directory, target_runs['data_dir'], expected_outputs_sha256=pin,
            mapping_run=target_runs['mapping_run'],
            expected_mapping_outputs_sha256=target_runs['mapping_pin'])
        assert result['status'] == 'verified'
    compared = bundle.compare_runs(
        first, replay, data_dir=target_runs['data_dir'],
        mapping_run=target_runs['mapping_run'],
        expected_mapping_outputs_sha256=target_runs['mapping_pin'])
    assert compared['equal'] is True
    assert len(compared['tables']) == 8
    assert compared['substantive_report_equal'] is True
    assert compared['trust_established'] is False
```

`target_runs` is a pytest fixture defined in tests/acs_target_fixtures.py at Task7 and imported into the test module. It uses the Task4 prepare_target_delivery callback before raw conversion: build the real authenticated raw fixture once per test, use two fresh Stage9 IDs and independently captured mapping pin. Refuse unsafe IDs, final/partial occupancy, parent/final/file symlinks, extra bundle files and publication races (including a concurrently created empty final directory). A forced post-build input/software/rule mutation must leave no new final. Pre-existing partial content and unrelated temporary files must remain unchanged.

- [ ] **Step 2: Run tables/bundle tests red.** `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_target_tables.py tests/test_acs_target_bundle.py -q`; expect missing assembly/publication functions.

- [ ] **Step 3: Implement orchestration, cross-table validation and no-replacement publication.** Reserve `derived/acs/targets/<id>.part` with exclusive mkdir and reject finals/partials/symlink ancestors before creation. Use new Stage9 reserve logic, because Stage8 reserve_run is hardwired to `derived/acs/mapping`; reuse only safe_path and exclusive publish_directory unchanged. Keep an ownership flag so cleanup never removes an unreserved/pre-existing partial. The bundle reserves an exclusive TemporaryDirectory beside its owned staging and passes that Path as scratch to derive_tables/weighted_source. Temporary CSVs/spills live only inside that directory, separate from the final eleven files; all paths pass safe_path and cleanup removes only that owned scratch.

```python
TABLES = (
    'targets_observed', 'targets_canonical', 'targets_allocated_area_mix',
    'target_units', 'target_support', 'replicate_estimates',
    'eligibility_diagnostics', 'allocation_residuals',
)
FILES = tuple(name + '.parquet' for name in TABLES) + ('inputs.json', 'report.json')
```

Derive all50 products with two measures using one core selection and shared rules/scan lifetime. Merge county/MSA target rows in allocated_area_mix while preserving explicit auxiliary view. Write only the three target frames via write_targets; auxiliary tables use exact schemas, declared key sorts and serialized reread. Reconcile native annual/pooled support, per-measure replicates/SE methods, denominator groups, defined/undefined statuses, unit membership, coverage and residual conservation. Do not collect full person-level rows eagerly; eager tables are small public references or bounded aggregates.

Inputs records run/time, schema/rule versions, explicit mapping/upstream request and detached pins, selected original sources/raw citations/DDIs and IPUMS citations, complete product/universe/evidence/unit/frame registries, exact weight interpretation/scale diagnostics, target/software/lock/dependency inventories and all methodological limits. It records the full executing member list, including new modules. Report records all50 product nonempty/empty counts and reasons, disjoint funnel closure, overlapping evidence counts, annual/pooled support distributions, canonical loss, full/replicate allocation conservation, residuals and SE availability/reasons. Avoid nested run-specific times/IDs in substantive report content; only its top-level run_id/created_at are omitted by comparison. Timings belong to external acceptance controls, not logically compared report statistics.

Before publication validate all tables and reconstruct report from serialized output, rerun SelectedTargets.verify and current software/rules equality, then write outputs.json over exactly the ten other files. Recheck no extra/missing path, obtain detached pin and publish with native exclusive rename. Finally cleanup only execution-owned staging/scratch if still present. Never mutate a selected bundle or append raw manifest records.

Verifier authenticates outputs.json first, checks exact member inventory/order/schema/row/hash records and strict JSON (reject duplicate keys/nonfinite constants), binds explicit mapping run/pin, reads authenticated target request, runs select_targets, recreates all rules/tables/support/replicates/report, and compares exact ordered outputs. Rechecks inputs/software after reconstruction. Equality checks do not silently cast or reorder a published table before comparison; canonical serialization order is part of the contract.

Comparison requires explicit data_dir/mapping run/pin, authenticates that mapping, checks each target inputs' recorded mapping identity matches it, and compares all eight ordered logical tables plus substantive report. It deliberately does not claim detached target trust. Do not drop other metadata differences to make replay pass.

- [ ] **Step 4: Run bundle, table and existing publication checks green.** `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_target_tables.py tests/test_acs_target_bundle.py tests/test_acs_mapping_io.py tests/test_target_contract.py -q`; expect all pass, exact replay and no replacement. Recheck frozen upstream diff is empty.

- [ ] **Step 5: Commit.** `git add src/embedding_data/acs_target_contract.py src/embedding_data/acs_target_tables.py src/embedding_data/acs_target_bundle.py src/embedding_data/acs_target_inputs.py tests/acs_target_fixtures.py tests/test_acs_target_tables.py tests/test_acs_target_bundle.py`; `git commit -m 'feat: publish and reconstruct authenticated ACS target bundles'`. Review before exposing commands.

### Task 8: Expose offline commands and the real four-family V12 chain

**Files:**

- Create: `src/embedding_data/acs_targets.py`
- Modify: `src/embedding_data/acs_target_inputs.py`
- Modify: `tests/acs_target_fixtures.py`
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Test (create): `tests/test_acs_target_cli.py`
- Test (create): `tests/test_acs_target_v12.py`

**Interfaces:** Module `app:typer.Typer` exposes exactly build, verify, compare-runs. `run_acs_target_v12(data_dir:Path,monkeypatch)->dict[str,Path|str|dict]` in the new fixture module returns data_dir, mapping_run/pin, request, first/replay directories and detached controls. It composes `_authenticated_deliveries`/`seed_reconciliation_inputs(prepare_acs=...)`, actual Stage4/5/7 builders/selectors, unchanged conversion, actual Stage8 build/verify and Task7. Private fixture helper use is test-only and explicitly named; no private production builder prepares real data. The seed helper always returns tmp_path/data: pass data_dir.parent to it and assert returned data_dir equals the requested root, rather than silently nesting a second data directory.

- [ ] **Step 1: Write command and actual raw-chain tests.** CLI tests use CliRunner with a temporary explicit data root and inherited external guards, and require missing data-dir/mapping-run/mapping-pin to fail before work. Build also requires all seven upstream request fields. Verify requires its target detached pin as well. Compare requires both target IDs plus data-dir/mapping run/pin; unequal report/table returns nonzero. Help lists exactly three commands and top-level cli.py bytes remain unchanged.

Extend manifested synthetic ACS records before CSV conversion so family rules have usable raw variables and delivered DDI categories: use real supported observed industry/occupation pairs from committed exact public originals already used by the Stage8 fixture. Include EMPSTATD10/12 and armed-forces controls, CLASSWKRD22/23 and self-employed controls, domestic mover/stayer/foreign/territory endpoints, TRANWORK home/NIU/non-home, and each required Q status. Preserve all nine CT regions and Puerto Rico controls from the real Stage5/8 fixture originals. Include null QMIGRAT1 in2023 and documented0/4 in2024, duplicate core records and all80 weights with a signed interior replicate. Preserve the dtype actually produced by unchanged conversion: on this tiny numeric/null CSV, QMIGRAT1 is Int64. Separate direct small-frame membership/rule tests cover the selected production shape (all-null String in2023, String0/4 in2024), including source raw-value/type diagnostics. The raw-chain fixture demonstrates the real converter/selector/estimator path, not identity with every production schema; its own measured source schema remains authoritative. Do not monkeypatch INFER_SCHEMA_LENGTH/schema overrides, add a bogus nonnumeric flag to force inference, pad a large fake microdata file, or edit the converted Parquet/companion to manufacture String storage. Use literal `IND=8780`, `INDNAICS='811192'` (Car washes), verified in committed `census_industry_2022.xlsx`, worksheet `2022 Census Ind Code List ` row317 D/E and `ipums_ind_pairs.xlsx` sheet1 row419; and `OCC=20`, `OCCSOC='111021'`, verified in `census_occupation_2018.xlsx` sheet2 row16 C/D and `ipums_occ_pairs.xlsx` sheet1 row7. Expected selected leaf IDs are `naics:2022:national_industry:811192` and `soc:2018:detailed:11-1021`. Record these public locators in the fixture, preserving source strings and zero-padding interpretation; do not derive expected membership from the production mapper. Synthetic fixture populations remain explicit.

```python
from acs_target_fixtures import run_acs_target_v12
from embedding_data import acs_target_bundle as bundle


def test_raw_to_all_four_acs_families_is_offline_and_replayable(tmp_path, monkeypatch):
    result = run_acs_target_v12(tmp_path / 'data', monkeypatch)
    families = set(pl.read_parquet(result['first'] / 'targets_observed.parquet')['family'])
    assert families == {'staffing_pattern', 'area_mix', 'commuting_flow', 'migration_flow'}
    assert result['external_access_counts'] == {
        'network': 0, 'environment_file': 0, 'live_client': 0,
    }
    compared = bundle.compare_runs(
        result['first'], result['replay'], data_dir=result['data_dir'],
        mapping_run=result['mapping_run'],
        expected_mapping_outputs_sha256=result['mapping_pin'])
    assert compared['equal'] is True
```

Add imports (`polars as pl`) and assert independent detached verification for both bundles. Count actual attempted access seams before raising, covering socket/HTTP, dotenv/env-file reads and bound module-local live client constructors. Guard Path/open on the actual environment-file path and real production data root, permitting only temporary fixture roots; merely patching one global library name is insufficient when modules bound aliases. Verify production .env/data are never touched. Existing Stage8 seed/build fixture helpers reinstall forbid_external_access internally, so a one-time counter patch is insufficient: in the new wrapper, monkeypatch only the old fixture module's guard function with a wrapper that first invokes its original guard and then reinstalls the counted guards at all bound seams. Keep that wrapper active through setup, both builds and verifiers. A separate guard self-test deliberately invokes each intercepted seam, checks its counter increments before raising, and makes no external call; the raw-chain test starts fresh counters and requires all zero. Never report a constant zero dictionary as measured access evidence. Invoke existing `tests.target_fixtures.run_ita_v12(tmp_path/'ita-data',monkeypatch)->Path` in the shared extension test at its own distinct temporary root, rather than merging ITA behavior into ACS.

- [ ] **Step 2: Run CLI/V12 tests red.** `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_target_cli.py tests/test_acs_target_v12.py tests/test_target_contract_v12.py -q`; expect absent CLI/fixture chain failures.

- [ ] **Step 3: Implement standalone commands and guarded fixture composition.** Mirror fixed safe diagnostics from the existing standalone ACS mapping module; no raw row values/exception locals in errors. Require these options:

```text
build RUN_ID --data-dir ROOT --mapping-run ID --mapping-outputs-sha256 PIN
  --codes-run ID --codes-outputs-sha256 PIN
  --geography-run ID --geography-outputs-sha256 PIN
  --ipums-run ID --ipums-outputs-sha256 PIN --ipums-references-sha256 PIN
verify RUN_ID --data-dir ROOT --mapping-run ID --mapping-outputs-sha256 PIN
  --outputs-sha256 PIN
compare-runs FIRST_ID SECOND_ID --data-dir ROOT --mapping-run ID
  --mapping-outputs-sha256 PIN
```

Use Annotated[Path,typer.Option('--data-dir')] with no default and pass every argument into the Task7 public APIs. Failure exits2 with `ACS target validation failed.`; unequal comparison exits1. Report aggregate success JSON only. No env loading or acquisition command exists.

README documents fixture software readiness, exact selected upstream pins, explicit data root, standalone commands, publication refusals and the distinction between native/strict, canonical and population-allocated products. CLAUDE.md gains only Stage9 software behavior now, leaving measured full-data status pending. Include factor1/pooling/sampling-SE limits, identified-flow denominator interpretation, 2024 strict migration/matched sensitivity and size_gate_pending. Do not publish microdata or describe fixtures as scientific acceptance.

- [ ] **Step 4: Run software-readiness checks green.** `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_target_cli.py tests/test_acs_target_v12.py tests/test_target_contract_v12.py tests/test_acs_mapping_v12.py -q`; expect genuine raw-chain replay and zero external attempts. Satisfy Task11 repository checks before the production checkpoint under D2; reuse identical-state evidence instead of repeating the broad suite. No new marker, dependency, lock or frozen top-level CLI change is allowed.

- [ ] **Step 5: Commit the software-ready interface.** `git add src/embedding_data/acs_targets.py src/embedding_data/acs_target_inputs.py tests/acs_target_fixtures.py tests/test_acs_target_cli.py tests/test_acs_target_v12.py README.md CLAUDE.md`; `git commit -m 'feat: expose offline ACS targets and authenticated family V12'`. Record software readiness only; Stage9 science acceptance and roadmap completion remain open.

### Task 9: Build independent acceptance and preservation controls

**Files:**

- Create: `scripts/stage9_independent_io.py`
- Create: `scripts/stage9_independent_estimates.py`
- Create: `scripts/reconcile_stage9.py`
- Modify: `tests/acs_target_fixtures.py`
- Test (create): `tests/test_acs_targets_reconciliation.py`

**Interfaces:** `freeze(data_dir:Path,control_dir:Path,*,mapping_run:str,mapping_outputs_sha256:str,request:dict[str,str],first_run:str,replay_run:str)->dict`; `preservation(data_dir:Path,control_dir:Path,*,expected_freeze_sha256:str)->dict`; `reconcile(data_dir:Path,run_id:str,outputs_sha256:str,control_dir:Path,*,expected_freeze_sha256:str)->dict`. CLI exposes `freeze`, `preservation`, `reconcile`, all requiring explicit data-dir/control-dir. Freeze requires mapping ID/pin, all seven upstream options from the build command, and --first-run/--replay-run. Preservation/reconcile require --freeze-sha256; reconcile additionally takes target RUN_ID/--outputs-sha256. Request is an independent dictionary with exactly the seven SelectionRequest field names; scripts never import that production class. Freeze authenticates mapping/upstreams against this explicit selection before any target output exists, writes an exclusive freeze-response.json with its returned freeze_sha256 after freeze.json is finalized, and returns that same result. Production commands supply this plan's selected pins; authenticated hermetic fixtures supply their own explicitly captured pins with identical checks, never a selected-object mock or a production-only bypass. Results are aggregate JSON with failure_count and complete gate matrix; failures exit nonzero and never silently filter mismatches.

- [ ] **Step 1: Write independent reconciliation/preservation failures first.** Import the script through importlib.util with external access blocked. Freeze a real authenticated fixture before Stage9 build, explicitly passing its seven-field request, mapping pin and two fresh target IDs; independently hash freeze.json and pass expected_freeze_sha256 to preservation/reconcile. Reconcile the first/replay independently, and require all six acceptance groups below. Rehash a target bundle after changing one eligible count, annual divisor, numerator, denominator, interior replicate, SE/method, unsupported canonical leaf, Q status, residual, overlapping partition label or allocated support count. The independent calculation must reject every corruption even when production verification is deliberately not invoked by that test.

```python
import ast
from pathlib import Path


def test_acceptance_scripts_import_no_production_package():
    root = Path(__file__).resolve().parents[1]
    for name in ('stage9_independent_io.py', 'stage9_independent_estimates.py',
                 'reconcile_stage9.py', 'reconcile_stage8.py'):
        tree = ast.parse((root / 'scripts' / name).read_text())
        modules = [n.module or '' for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        modules += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        assert not any(m.startswith('embedding_data') for m in modules)
```

Test a wrong detached freeze pin and self-consistent mutation of both freeze metadata and its saved prefix: the previously captured external pin must reject both. Test manifest-prefix whitespace mutation that parses to identical JSON, truncation, changed selected original, changed upstream/seal/control bytes, unsafe/symlink control paths and occupied control directory. A legitimate manifested immutable append after freeze is separately accounted, never confused with an immutable-file mutation. Stage9 itself must append zero raw records. Assert the independent arithmetic uses the exact frozen tolerances and catches errors beyond them; exact key/count/Decimal discrepancies always fail, however small the float gap.

- [ ] **Step 2: Run `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_targets_reconciliation.py -q` red.** Expect missing independent script or failed corruption detection, not production data access.

- [ ] **Step 3: Implement independent source calculations and byte preservation.** Read raw gzip CSV with independent all-String lexical scanning, parse DDI XML directly, and authenticate manifested definition/DDI/CSV plus original/companion Parquet identities/order/counts against selected metadata. Independently construct Decimal38 weights from lexical values and verify source position alignment; never use production WeightedSource, family_rows, read_rules, aggregate_native, estimate, allocation helpers or copied production expected tables. Independently author exact selected DDI flag/category tables and family truth rules, cross-check them with frozen metadata, and compare product registry to the spec matrix rather than trusting the output's registry as its own oracle.

Use bounded lazy grouping of independent source scans and fixed eligibility masks to avoid materializing a source×80×product expansion. Native expected sums use Decimal before Float64; compute all numbered ratios/SEs independently. Read authenticated Stage8 code/area/factor tables and selected node/county membership as frozen upstream facts, check their full physical/reference inventories, then independently check each Stage9 supported scalar, denominator/coverage reduction and county/MSA/residual contribution. Apply explicit sorted accumulation for independent allocated expectations. It may use Polars/stdlib but no production estimator or eligibility helper; independence is about separate rule/calculation paths, not artificial library diversity.

Freeze the numerical predicates literally in scripts/stage9_independent_estimates.py; exact Decimal sums/counts/keys/schemas use equality before these Float64 checks. Missing values match only when both are None, with status/reason checked separately. These pure predicates are part of Task9's produced interface:

```python
import math


def close_share(actual: float, expected: float) -> bool:
    return (math.isfinite(actual) and math.isfinite(expected)
            and abs(actual - expected) <= 1e-12)


def close_allocated_or_se(actual: float, expected: float) -> bool:
    return (math.isfinite(actual) and math.isfinite(expected)
            and abs(actual - expected) <= 1e-8 + 1e-12 * abs(expected))
```

Tests require close_share(0.5 + 1e-10,0.5) to be false and close_allocated_or_se(1e8 + 0.001,1e8) to be false. When using pytest.approx in handwritten fixtures, set rel=0 for an absolute-only bound; its default relative tolerance must not weaken the specified test. Exact logical replay never uses either numerical predicate.

The reconciliation result must contain these six groups, including all failing cells/counts rather than only examples:

1. Source/weight alignment, complete raw Q value/dtype/domain partitions, annual support and disjoint funnel closure.
2. Both universes, all50 declared products/periods/evidence policies and every eligible denominator.
3. Exact native Decimal cell/denominator sums; both measures, all80 numerator/denominator/statistic values and SEs.
4. Canonical supported-leaf membership, retained source flags, within-denominator and whole-product coverage loss.
5. County allocation and typed metropolitan/micro/no-CBSA mass/support for full and all80 replicates, zero factors and absent MSA controls.
6. Exact undefined-point/SE reasons and affected replicate numbers, nonempty/empty product counts and unchanged numerical tolerances.

Freeze inventories all existing raw/derived upstream bytes, including selected Stage2–8 artifacts, prior failed/history controls/seals and originals. Validate all explicit run IDs/paths first and refuse occupied control/final/partial paths. The only excluded paths are the exact new control directory and two explicitly named fresh target directories; never exclude an entire targets/history tree or wildcard. At final preservation, require each new final to contain exactly its eleven declared files and require both partials and execution-owned scratch to be absent. Authenticate freeze.json with the caller-supplied external pin before trusting its inventory/prefix/software/selection records. Capture exact raw-manifest prefix bytes/length/hash, executing source/lock/dependencies/Python and independent script identities. Preserve byte checks separately from append accounting. Account any later manifest suffix line against its exact immutable file; report Stage9 appended0. Refuse to overwrite controls; produce fresh checkpoint files or exclusive subdirectories for results, never rewrite historical before-state. Reports/artifacts remain aggregate; per-cell discrepancies are allowed, source positions/identifiers are not published.

- [ ] **Step 4: Run independent acceptance tests green.** `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_targets_reconciliation.py -q`; expect success on the real fixture chain and rejection of every semantic/byte mutation. Require an independent review of rules/math and import independence before measuring production.

- [ ] **Step 5: Commit complete acceptance software.** `git add scripts/stage9_independent_io.py scripts/stage9_independent_estimates.py scripts/reconcile_stage9.py tests/test_acs_targets_reconciliation.py tests/acs_target_fixtures.py`; `git commit -m 'test: add independent ACS target acceptance and preservation controls'`. Keep execution and independent software frozen throughout the next task; if relevant code changes, use fresh controls and fresh first/replay run IDs.

### Task 10: Measure fresh full-data first/replay and record scientific acceptance

**Files:**

- Create after measurement: `specs/findings/stage-9-acs-targets.md`
- Modify after measurement: `README.md`
- Modify after measurement: `CLAUDE.md`

**Interfaces:** Consumes frozen reviewed software, selected Stage8 first/replay pins and every public/independent API from Tasks7–9. Produces authenticated first/replay target bundles, detached pins, exact ordered eight-table replay, full independent gate matrices, preservation controls and a committed aggregate finding. These are future execution actions; this planning session stops before them.

- [ ] **Step 1: Verify execution identity, readiness and unoccupied prospective paths.** In the implementation worktree run branch/HEAD/status and satisfy Task11 repository checks plus the independent acceptance tests under D2; reuse valid identical-state results rather than rerunning them. Record the executing commit and complete transformation/acceptance software, lock, Python and dependencies. Confirm frozen upstream files match the approved spec commit's blobs and selected Stage7/8 inventories; verify exact D5. Confirm neither prospective run nor partial/control path exists. Inspect any occupied path and choose fresh IDs; never remove/overwrite. Run both selected Stage8 public verifiers before selection, using their exact detached pins; do not build or repair upstreams.

- [ ] **Step 2: Freeze preservation controls and build first/replay with explicit inputs.** The following is a concrete prospective command sequence for execution; use it only after Tasks1–9 and reviews. Each uv command supplies the implementation working directory explicitly as well as the actual data root. The shell itself must also have the implementation worktree as its tool working directory. `set -C` refuses overwriting redirected controls. If IDs are occupied, change all three selections consistently to fresh reviewed IDs and record that selection in the finding.

```bash
set -euo pipefail
set -C
STAGE9_WORKTREE=/Users/lowell/.codex/worktrees/acs-targets-design/embedding-data
STAGE9_DATA=/Users/lowell/Projects/embedding-data/data
STAGE9_FIRST=stage9_acs_targets_20261019_r1
STAGE9_REPLAY=stage9_acs_targets_20261019_r1_replay
STAGE9_CONTROL="$STAGE9_DATA/derived/acs/target-controls/stage9_acceptance_20261019_r1"
STAGE9_MAPPING=stage8_acs_mapping_20261018_r7
STAGE9_MAPPING_PIN=1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4

UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv --directory "$STAGE9_WORKTREE" run --offline --locked python -m embedding_data.acs_mapping verify "$STAGE9_MAPPING" --data-dir "$STAGE9_DATA" --outputs-sha256 "$STAGE9_MAPPING_PIN"
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv --directory "$STAGE9_WORKTREE" run --offline --locked python -m embedding_data.acs_mapping verify stage8_acs_mapping_20261018_r7_replay --data-dir "$STAGE9_DATA" --outputs-sha256 a115c5f7e2691ecbffe763bd1b6b9780fb6a71bc512a2691cf4014f9857b3565

STAGE9_BUILD_ARGS=(
  --data-dir "$STAGE9_DATA"
  --mapping-run "$STAGE9_MAPPING" --mapping-outputs-sha256 "$STAGE9_MAPPING_PIN"
  --codes-run stage4_v11_20261013_r2
  --codes-outputs-sha256 15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a
  --geography-run stage5_geography_20261014
  --geography-outputs-sha256 5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d
  --ipums-run stage7_ipums_verification_20261015_r2
  --ipums-outputs-sha256 db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc
  --ipums-references-sha256 3163968dde603ba53f807976dd09b9e40d73235a98c6f36e4e02c67ec4239c9c
)
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv --directory "$STAGE9_WORKTREE" run --offline --locked python scripts/reconcile_stage9.py freeze "${STAGE9_BUILD_ARGS[@]}" --control-dir "$STAGE9_CONTROL" --first-run "$STAGE9_FIRST" --replay-run "$STAGE9_REPLAY"
STAGE9_FREEZE_PIN=$(shasum -a 256 "$STAGE9_CONTROL/freeze.json" | awk '{print $1}')
printf '%s\n' "$STAGE9_FREEZE_PIN" > "$STAGE9_CONTROL/freeze.sha256"
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv --directory "$STAGE9_WORKTREE" run --offline --locked python - "$STAGE9_CONTROL/freeze-response.json" "$STAGE9_FREEZE_PIN" <<'PYCODE'
import json
from pathlib import Path
import sys
if json.loads(Path(sys.argv[1]).read_text())['freeze_sha256'] != sys.argv[2]:
    raise SystemExit('independent freeze checksum differs from captured response')
PYCODE
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv --directory "$STAGE9_WORKTREE" run --offline --locked python -m embedding_data.acs_targets build "$STAGE9_FIRST" "${STAGE9_BUILD_ARGS[@]}" > "$STAGE9_CONTROL/first-build-response.json"
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv --directory "$STAGE9_WORKTREE" run --offline --locked python -m embedding_data.acs_targets build "$STAGE9_REPLAY" "${STAGE9_BUILD_ARGS[@]}" > "$STAGE9_CONTROL/replay-build-response.json"
```

The explicit response check above must pass before either build. Both builds must consume the same authenticated first Stage8 mapping; replay mapping remains independent upstream evidence, never a mixed-run source. Expected: each build returns success and publishes exactly eleven files, no partial remains, upstream/manifest bytes unchanged. A process exit alone is not acceptance; capture actual timing/exit evidence separately and retain failures honestly.

- [ ] **Step 3: Capture detached target pins independently and run both public verifiers.** Do not trust a build-response pin without independently hashing outputs.json. Keep the detached values outside each bundle in owned controls:

```bash
STAGE9_FIRST_PIN=$(shasum -a 256 "$STAGE9_DATA/derived/acs/targets/$STAGE9_FIRST/outputs.json" | awk '{print $1}')
STAGE9_REPLAY_PIN=$(shasum -a 256 "$STAGE9_DATA/derived/acs/targets/$STAGE9_REPLAY/outputs.json" | awk '{print $1}')
printf '%s\n' "$STAGE9_FIRST_PIN" > "$STAGE9_CONTROL/first-outputs.sha256"
printf '%s\n' "$STAGE9_REPLAY_PIN" > "$STAGE9_CONTROL/replay-outputs.sha256"
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv --directory "$STAGE9_WORKTREE" run --offline --locked python -m embedding_data.acs_targets verify "$STAGE9_FIRST" --data-dir "$STAGE9_DATA" --mapping-run "$STAGE9_MAPPING" --mapping-outputs-sha256 "$STAGE9_MAPPING_PIN" --outputs-sha256 "$STAGE9_FIRST_PIN" > "$STAGE9_CONTROL/first-public-verification.json"
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv --directory "$STAGE9_WORKTREE" run --offline --locked python -m embedding_data.acs_targets verify "$STAGE9_REPLAY" --data-dir "$STAGE9_DATA" --mapping-run "$STAGE9_MAPPING" --mapping-outputs-sha256 "$STAGE9_MAPPING_PIN" --outputs-sha256 "$STAGE9_REPLAY_PIN" > "$STAGE9_CONTROL/replay-public-verification.json"
```

Expected: independent hashes equal the corresponding build-response pins; each verifier reports status verified and the same explicit selected mapping. A different expected target pin or content/rule/software mutation must fail rather than accepting a self-described inventory.

- [ ] **Step 4: Perform exact replay, full independent reconciliation and preservation.**

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv --directory "$STAGE9_WORKTREE" run --offline --locked python -m embedding_data.acs_targets compare-runs "$STAGE9_FIRST" "$STAGE9_REPLAY" --data-dir "$STAGE9_DATA" --mapping-run "$STAGE9_MAPPING" --mapping-outputs-sha256 "$STAGE9_MAPPING_PIN" > "$STAGE9_CONTROL/ordered-replay.json"
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv --directory "$STAGE9_WORKTREE" run --offline --locked python scripts/reconcile_stage9.py reconcile "$STAGE9_FIRST" --data-dir "$STAGE9_DATA" --control-dir "$STAGE9_CONTROL" --outputs-sha256 "$STAGE9_FIRST_PIN" --freeze-sha256 "$STAGE9_FREEZE_PIN" > "$STAGE9_CONTROL/first-independent.json"
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv --directory "$STAGE9_WORKTREE" run --offline --locked python scripts/reconcile_stage9.py reconcile "$STAGE9_REPLAY" --data-dir "$STAGE9_DATA" --control-dir "$STAGE9_CONTROL" --outputs-sha256 "$STAGE9_REPLAY_PIN" --freeze-sha256 "$STAGE9_FREEZE_PIN" > "$STAGE9_CONTROL/replay-independent.json"
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv --directory "$STAGE9_WORKTREE" run --offline --locked python scripts/reconcile_stage9.py preservation --data-dir "$STAGE9_DATA" --control-dir "$STAGE9_CONTROL" --freeze-sha256 "$STAGE9_FREEZE_PIN" > "$STAGE9_CONTROL/final-preservation.json"
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv --directory "$STAGE9_WORKTREE" run --offline --locked embedding-data audit --data-dir "$STAGE9_DATA" > "$STAGE9_CONTROL/raw-audit.txt"
```

Expected: all eight ordered tables have exact values and ordered schemas, substantive reports exactly equal after only top-level run/time omission, both independent failure_count0, all six groups fully reconciled, protected bytes/prefix equal, suffix accounting complete and Stage9 raw appends0, no new provenance discrepancy. Legitimate empty products/unavailable SEs are explicit outcomes, not failed gates or omissions; unexplained emptiness or an absent reason fails acceptance. Investigate numerical failures; never widen frozen bounds or omit cells. Relevant fixes require reviewed software, fresh controls and fresh target runs; preserve failed finals/old controls and inspect occupied partials rather than editing their histories.

- [ ] **Step 5: Write the aggregate measured finding with an explicit acceptance matrix.** Include selected physical input/output pins and complete file inventories/schemas, executing/independent code identities, lock/dependencies/Python, source counts, all50 product periods/policies/universes and empty/nonempty counts, support distributions, excluded weighted mass/funnels, required Q raw-domain/status partitions, unknown/undelivered evidence, civilian559830 controls, native exact sums, canonical supported membership/loss, county/MSA full/80 conservation, micro/no-CBSA residuals, input versus fractional support, undefined points/SEs/replicate numbers, all verification/replay/independent/preservation results and their frozen tolerances. State matched2024 sensitivity next to strict2024 migration and pooled sensitivity separately. Published reference comparisons require matching universe/period and explicit gaps; do not tune eligibility to agree or reuse Stage7 age16+ resident context as this stage's workplace estimand. Document fixed-factor conditional sampling SE limits, common-frame limits, size_gate_pending, no training use and remaining later-stage scope.

Only record actual outcomes, including command failures/legitimate limitations. Hash local controls separately; do not commit microdata/control source rows. External recorded science acceptance does not rewrite older Stage7/8 bundle statuses or science seals. Update README/CLAUDE with only measured facts and selected IDs/pins.

- [ ] **Step 6: Review the measured finding independently and commit.** Request independent review of implementation and full-data calculation/finding using requesting-code-review and receiving-code-review; record reviewer scope/source and resolution. `git add specs/findings/stage-9-acs-targets.md README.md CLAUDE.md`; `git commit -m 'docs: record measured ACS target acceptance and limits'`. If acceptance is incomplete, record the actual open gate and continue resolution; do not mark Stage9 complete based on fixtures, command exits or a nearly finished plan.

### Task 11: Run repository gates, complete the protocol and hand off later stages

**Files:**

- Modify at completion: `specs/plans/9-acs-targets.md`
- Modify if protocol requires: `specs/deferred_items.md`
- Modify at completion: `specs/embedding-evaluation-data-spec-roadmap.md`
- Retire at completion: `specs/plans/completed/9-acs-targets.md`
- Modify before retirement: `specs/acs-targets.md`
- Retire at completion: `specs/completed/acs-targets.md`

**Interfaces:** Consumes completed software/science/review gates. Produces recorded complete checks, resolved/deferred partition, exact shipped Handoff, completion stamp and retired plan/spec according to writing-plans. Subsequent roadmap entry reconciliation is a separate fresh-session derive-roadmap resume.

- [ ] **Step 1: Satisfy the complete offline repository checks under D2 and read every result.** Reuse valid identical-state receipts; otherwise obtain one full coverage pass and the remaining checks. Tool working directory must be `/Users/lowell/.codex/worktrees/acs-targets-design/embedding-data` for every command:

```bash
# Obtain or cite the valid full coverage receipt defined in D2 first.
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked behave
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked ruff check .
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv lock --offline --check
# Only with that matching passing receipt:
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache UV_OFFLINE=1 SKIP=coverage-check uv run --offline --locked pre-commit run --all-files
```

Expected: pytest all default-selected tests pass (only the existing network canary deselected); every Behave scenario passes; ruff, lock check and every required hook pass (redundant coverage reuse is explicitly recorded as Skipped under D2). Record real counts and any warnings/failures, not guessed baseline numbers. Only the explicitly authorized redundant coverage-hook reuse in D2 is permitted; no marker/dependency/config changes or other hook omissions. If pre-commit fixes tracked code, re-review relevant changes and redo invalidated science with fresh IDs; a formatting fix to a frozen executing file is still an identity change.

- [ ] **Step 2: Resolve final whole-branch and measured-science review.** Follow requesting-code-review and receiving-code-review. Review against the approved spec plus this plan, especially required evidence, paired denominator membership, exact weights/80 replicates, source preservation, frozen interfaces and aggregate disclosure. Record actual reviewer identity/commit scope, findings and dispositions in the measured finding. Apply relevant repository model-routing guidance where the runtime supports the requested reviewer models; do not claim a model/review that did not run. Recheck full gates after code changes; purely documentary review edits require documentation/diff checks. Read verification-before-completion before reporting success.

- [ ] **Step 3: Run writing-plans' resolve-before-defer gate and final markup.** Gather skipped steps/review leftovers and resolve required owner input before retirement. Implement newly unblocked work, defer only with a closure condition, then tick completed plan steps and annotate actual deviations/skips. Run the deferred-items ticking pass even if nothing new is deferred. Keep the design status untouched until this actual completion protocol, and never silently change approved scientific requirements while resolving review.

- [ ] **Step 4: Write `Handoff to later stages` from what shipped, reconcile this stage's promises, then stamp Stage9.** This is execution-time completion work, not a prewritten claim. Cite the approved spec and actual measured finding. Give exact APIs, schema/version/null/key contracts, selected target pins, rule/product registries and refusal/limit contracts. Explain any differences from this plan/roadmap Produces, including reverted interim interfaces, traps and per-stage deferred references. Cover Stage12 (universe/evidence/pooling/replicate/allocation helpers only; no worker-profile estimator), Stage13 (those helpers with five-year/MULTYEAR/vintage provenance preserved; comparators, citations, V9 and full eight-family V12 remain there), and preservation for Stages10/11 (no new ITA eligibility/CPS parser/linkage/source-scheme shortcut).

Only after implementation/scientific acceptance/review and this shipped-contract reconciliation, apply the writing-plans stage tick/stamp with retired plan path `specs/plans/completed/9-acs-targets.md`. Later-stage entry amendments belong to derive-roadmap on resume, not speculative edits in this session. Keep the exact rollout meaning intact. Stage9's current planning state is unchecked.

- [ ] **Step 5: Report backlog health and retire the plan/spec.** Run from the implementation worktree:

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --no-project --python 3.13 python /Users/lowell/.agents/skills/writing-plans/scripts/deferred_stats.py
```

Report its actual summary and, if20+ open or any aged tail, the read-only triage proposal required by writing-plans. Then `git mv specs/plans/9-acs-targets.md specs/plans/completed/9-acs-targets.md`; retire the spec to specs/completed/ only when no other live plan implements it. Correct relative links for deeper paths and commit `chore(specs): retire plan 9` with protocol markup. Select integration deliberately via finishing-a-development-branch, honoring the owner's existing worktree/primary-checkout restrictions; do not merge/switch/remove this user-selected worktree without the applicable integration choice. End with roadmap-resume handoff, routing to no next stage.

## Plan review corrections — 2026-10-19

Owner approval and review scope are recorded in D1. This is a planning audit, not an implementation/code review or a scientific acceptance finding.

| Verified gap | Correction / task home | Governing evidence |
| --- | --- | --- |
| Raw versus annual-average masses were ambiguous across allocation, estimates and residuals | Internal masses stay unpooled; estimate/residual serialization divides once; a k=2 rational fixture checks raw150 versus published75 and separates annual/pooled rows (5–6) | Approved spec Shared estimation and Separate projections |
| A generic endpoint funnel could require unused roles | Exhaustive per-family input table and unused-role regression cases; required Q evidence remains independent (4) | Approved spec Family definitions and Required source-allocation evidence |
| One allocated file contains two auxiliary views | Determine county/MSA view from validated unit_a type and metropolitan membership; separate single-file TARGET_STAT_KEY_COLUMNS from view-bearing auxiliary STAT_KEY_COLUMNS (1,7) | Approved spec Unit and target metadata; unchanged target_contract valid_unit/key APIs |
| Annual audit rows/undefined full points could suppress valid replicate evidence or fabricate annual SEs | Repeat pooled statuses on contribution rows; retain each independently defined replicate ratio; total and ratio SE validity remain separate (1,5) | Approved spec Support and undefined estimates |
| Canonical coverage could join unrelated observed/canonical IDs or identical product IDs | Explicit observed_counterpart and source-membership denominator baseline; whole-product unmapped loss remains separate (1,6) | Approved spec Separate projections; Stage8 code lookup versus scalar-node distinction |
| Independent freeze could infer selection, hardcode production-only inputs or leave output exclusions unbound | Explicit seven-field request, first/replay IDs and detached freeze pin; exact paths only; identical authenticated fixture/production path (9–10) | Approved spec Selected inputs, Preservation and independent reconciliation; shipped seven-field SelectionRequest |
| Numerical tests could silently retain pytest.approx default relative tolerance | Set rel=0 in absolute-only examples and freeze exact independent share/allocation/SE predicates (5,9) | Approved spec independent numerical bounds and exact replay |
| Tiny CSV numeric/null flags do not retain an in-memory String dtype through unchanged inference | Keep the converter-produced Int64 fixture dtype; test production String/null domains directly with small frames and never patch frozen converter behavior (4,8) | Shipped ipums_conversion scan_delivered_csv and INFER_SCHEMA_LENGTH; planning-only in-memory read/write probe |
| The planning artifact may still be untracked when execution starts | Include the approved plan in Task1's first implementation commit so completion can retire it with git mv (1,11) | Current worktree status and writing-plans retirement protocol |
| Later fixture setup could be missing when Task7 begins or overwrite access counters | Prepare raw delivery callback in4, consume in7–9; wrap existing fixture guard reinstalls so counters measure actual attempts (4,7–8) | Shipped tests/acs_mapping_fixtures.py seed_reconciliation_inputs/build_fixture_mapping/forbid_external_access |

All selected pins, product scope, eleven-file bundle, required flags, numerical bounds, exact logical replay, frozen upstream APIs, roadmap rollout note and later-stage boundaries remain unchanged. No new owner scientific decision or spec amendment is inferred.

## Planning self-review and execution handoff

This plan's task coverage is explicit: selected trust/provenance and R7/R8/R9 in1–2/7–10; unit/evidence semantics and R3.6/R3.8 in3–4; exact weights/R3.7/uncertainty in4–5; workplace/migration R3.10 and R3.11 use in4/6; all four ACS R7.2 families and shared outputs in4–8; automated V12 extension in8; independent full-data acceptance/preservation in9–10; repository checks, reviews and later-stage handoff in11. The source spec's other families/roadmap stages are intentionally not implemented here.

The planning-only review compared the approved spec against the invariant map/tasks and checked cross-task signatures, keys, schemas, pins and commands against shipped code/finding. Artifact checks parse/compile executable Python examples without running pipeline code, syntax-check shell examples without executing them, verify symbolic ordered schemas against all28 shipped code fields, and independently reconcile the handwritten arithmetic. A separate in-memory CSV probe verified the unchanged converter's dtype inference constraint. Recheck mutable worktree state in the fresh execution session. These are planning-artifact checks; they do not claim implementation/test-suite completion, production measurement or Stage9 acceptance.

**Owner plan review:** approved on 2026-10-19 (D1), with an explicit request to audit/fix gaps while remaining planning-only. The review corrections above are covered by that request and preserve the approved spec. No further plan-approval request is needed for these corrections. Log any later owner decisions with date/source and exact home; spec-changing decisions require an explicit tagged amendment task, never an unreviewed spec edit. Execution still belongs to a fresh session; no approval statement in this planning artifact starts it.

**Recommended fresh-session execution:** after this planning-only review, open a fresh session (or `/clear`) in the same replacement worktree and use **subagent-driven-development** on this plan. The task boundaries separate authentication, evidence, estimation, projection, publication and independent science, making fresh task implementers and two-stage review useful. Inline execution via executing-plans is available if the owner chooses it. The new session must reverify branch/HEAD/status and read both plan and approved spec; this planning conversation is not a dependency. Stop this planning session at that handoff, with Stage9 unticked and no implementation/production-data operations performed.
