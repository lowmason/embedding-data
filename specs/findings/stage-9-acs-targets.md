# Stage 9 ACS targets: first full-data attempt

**Task 10 remains in progress. This attempt failed before publication; no Stage 9 scientific acceptance is recorded.** On 2026-10-20 the first builder for `stage9_acs_targets_20261019_r1` returned exit 137 after 5,084.622348209 seconds with empty stdout/stderr. No first or replay final exists. Replay, detached target verification, exact replay and the six-group independent target reconciliation were not run. This finding is an incremental record pending the controller's memory-feasibility diagnosis and subsequent reviewed resolution; it is not a completion or adoption record.

## Execution identity and selected inputs

Worktree: `/Users/lowell/.codex/worktrees/acs-targets-design/embedding-data`; branch `codex/acs-targets-design`; executing commit `24cb1cc0cf4d167d4aa8df74d920559bc42c8f3f`. All repository commands supplied that working directory. Data root: `/Users/lowell/Projects/embedding-data/data`. The actual inherited Codex runtime was used; no unavailable Claude-model routing is claimed. No production source, test, configuration, dependency, frozen helper, upstream bundle or original was edited.

| Physical selection | Run or receipt | Detached SHA-256 |
| --- | --- | --- |
| Mapping consumed | `stage8_acs_mapping_20261018_r7` | `1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4` |
| Mapping replay, independent upstream evidence only | `stage8_acs_mapping_20261018_r7_replay` | `a115c5f7e2691ecbffe763bd1b6b9780fb6a71bc512a2691cf4014f9857b3565` |
| Codes | `stage4_v11_20261013_r2` | `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |
| Geography | `stage5_geography_20261014` | `5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d` |
| IPUMS verification | `stage7_ipums_verification_20261015_r2` | `db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc` |
| IPUMS reference receipt | `stage7_ipums_references_20261015_r2` | `3163968dde603ba53f807976dd09b9e40d73235a98c6f36e4e02c67ec4239c9c` |

The approved specification is byte-identical to commit `4b5d1965c0de04104fbfa1bd048b1748bd9f8a0a`. All 54 executing members in both selected Stage 8 inventories, all 25 selected Stage 7 members and the 57 distinct executing/independent members in the selected Stage 8 finding match their recorded sizes/hashes and approved-spec-commit blobs. Exact D5 alone permits the selected geography's historical CLI hash `68778e16b7cc051745c1e34d3dee6a9fc044fd12b1f78103773984503e9f9742` against executing hash `32a86b3d07bf112fabc1edb01fd10a966e840c185642e55d00f35dfd435220b3`, corroborated by Stage 7 and both Stage 8 inventories; every other selected geography implementation hash matches. No new exception was introduced.

The following are read-only counts from authenticated source/companion Parquet metadata, not accepted Stage 9 estimator outputs. Only core is authorized to produce targets.

| Profile / delivery | Original rows | Companion rows | Original columns | Original Parquet SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `acs/core` / `usa_00001` | 3,206,859 | 3,206,859 | 147 | `c07f9e7abe2c5dfdb8f9488a1f574d4cf49ab7945c3ad2ffc9daec5eaba47d10` |
| `acs/five_year` / `usa_00003` | 7,456,212 | 7,456,212 | 148 | `c5846bde221e7785051a4a4075aa6a71cc267a1f4497168a96df05d7c50f78fe` |
| `acs/vintage` / `usa_00002` | 1,575,420 | 1,575,420 | 146 | `b6ffab7bd974f72b4fbc913f261779f5ce3145a915849bf92e946bb6b649240d` |

D2 readiness reuses the exact passing final-state receipt: 2,526 tests passed, one unchanged network canary deselected, 94% coverage, 4,236.12 seconds, exit 0. The full 19,241-byte log was read and rehashed (`6cd21ac7006d853443b651360a1cf8428cda314462b1cbdd983490507e9f105f`). All 258 tested file sizes/hashes, full CPython identity, dependencies, lock/configuration and approved default selection match canonical identity `aac7aa79f7faba3712b049161945ee258e4df85f676cc51619b9def28c74ff68` before these documentation edits. Behave (one feature/two scenarios/ten steps), Ruff, offline lock (63 packages) and all applicable mechanical hooks passed in matching-state evidence read in full. Redundant coverage hooks were actually Skipped under owner D2; they were not rerun or represented as new passes. Full source/runtime/dependency inventories are retained in the pinned independent freeze and exact tested-identity control.

## Actual command outcomes and preservation

All uv invocations used explicit `--directory`, `--offline --locked`, explicit data root and the selected pins. No artificial process timeout, acquisition, conversion recovery, upstream rebuild or refresh was introduced. Scientific tolerances and software stayed frozen.

| Gate | Measured outcome | Elapsed seconds |
| --- | --- | ---: |
| Unoccupied first/replay/control/partial readiness | PASS before reservation | metadata check |
| Selected first Stage 8 public verification | PASS: exit 0, status verified, exact external pin, stderr empty | 360.455577583 |
| Selected replay Stage 8 public verification | PASS: exit 0, status verified, exact external pin, stderr empty | 363.743737959 |
| Independent preservation freeze | PASS: exit 0; 8,020 files / 15,119,953,696 bytes; software inventory 168 members | 21.404201833 |
| Detached freeze hash and response check | PASS before first build; independently repeated by controller | hash check |
| First Stage 9 build | FAIL: direct uv-child exit 137, stdout/stderr empty, no final | 5,084.622348209 |
| Replay build | NOT RUN after first failure | — |
| Detached target pins and both target public verifiers | NOT RUN: no outputs.json or final bundles | — |
| Exact ordered eight-table/substantive-report replay | NOT RUN: no target tables or report | — |
| Both independent target reconciliations | NOT RUN: no authenticated target bundles | — |
| Unchanged public preservation command after failure | FAIL: exit 2, `unaccounted new immutable files` | 7.183722584 |
| Separate read-only preservation components | PASS for all 8,020 pre-existing files, 168 software members, runtime/dependencies, exact raw-manifest bytes/prefix; zero suffix bytes | 6.210055041 |
| Raw provenance audit after failure | PASS: exit 0, `0 raw provenance discrepancies`, stderr empty | 2.011589167 |
| Independent finding review / final completion protocol | PENDING controller work | — |

Control directory: `data/derived/acs/target-controls/stage9_acceptance_20261019_r1`. Independently captured `freeze.json` SHA-256 `7785398fe0e958c993b42ca38c562ae944b031a3025da21ed5a6eec391afb35c` agrees with external `freeze.sha256` and exact `freeze-response.json`. Frozen raw-manifest prefix is 1,548,012 bytes / SHA-256 `57eaff0ffb7c3da57aaf9ba0d7efd732515e64081bb7581766ada5706a427ea5`; postfailure bytes equal the complete frozen prefix, with zero appends and no Stage 9 raw append.

First build started `2026-10-20T20:02:29.883117Z`; the uv process returned 137 after the stated duration. Direct wait did not capture a Python exception. Reported child-use deltas were 5,856.506317 user CPU seconds and 5,949.445471 system CPU seconds; cumulative completed-child maximum RSS was 26,600,947,712 native Darwin bytes. Numeric ps snapshots are instantaneous observations, not per-phase peaks. The immediate termination cause is independently confirmed by the narrowly scoped, PID-matched macOS kernel record at `2026-10-20 17:27:12.919 EDT` (`21:27:12.919 UTC`): memorystatus killed the largest compressed process, `python3.14 [67134]`, with reported accounting of 52,441 MB. The 162-byte `termination-kernel.log` has SHA-256 `5569cb5e1a9f9d47a85016a619cb688117e135d0113cd72dc309293e52570666`. This establishes a memory-pressure kill, not the exact source operator that created or retained memory. Kernel compressed-process accounting and maximum child RSS are distinct measures. A matching OS resource report corroborates large footprint and Polars asynchronous write/spill stacks, but its earlier `Action taken: none` is not itself kill evidence and its report-wide write totals are not exact build-only totals. The 10,611-byte diagnostic report snapshot has SHA-256 `e69b6170359a89137a5359bed9d3a0a4796d45c0096270a9fcef9b6d43c9c55a`. No fatal-time Python function/product trace exists. The controller continues a separate bounded diagnostic; no unchanged full build retry, source patch, operator-cause claim or full-data feasibility claim follows.

The first final and replay final are absent. The first `.part` remains empty, and execution-owned scratch `stage9_acs_targets_20261019_r1-scratch-w7xqvgqx/ipums-02b701ko/usa_00001.csv` remains (1,626,775,026 bytes; local checksum recorded in the component-preservation control). It contains source data, stays local and is not published or committed. Replay `.part` and replay scratch are absent. All these histories are preserved without cleanup or overwrite.

The unchanged checker fails at `scripts/stage9_independent_io.py:292`: its exact additions-vs-manifest-suffix comparison finds the owned scratch CSV while the suffix is empty. Subsequent explicit no-partial/no-scratch requirements at lines 304–306 would also remain unsatisfied. The CLI's common error envelope labels this as an authentication/control failure in gate 1; it is not an executed target-math reconciliation. The component check establishes old-byte preservation separately and does not override or relabel the failing full preservation gate.

## Bounded diagnostic r2: native-only baseline, no acceptance

A separate controller-reviewed diagnostic `native_100k_product0_r2` completed with child exit 0 in **12.913312708 seconds**, without a diagnostic safety stop. It consumed the deterministic first **100,000 source rows** and their genuinely aligned original/companion slice, using PERWT plus all 80 numbered replicate weights with their recorded Decimal dtypes. This is a resource experiment on a source slice, not a target build, replay, verifier, scientific reconciliation or full-data feasibility result.

The isolated observed product index 0 / ID `52407c90b0462ad4ea53b53139303d9c13837cfc2402fc763787ae8e7b7bdf79` stopped after unchanged native aggregation. Raw-numeric-to-original and original-to-companion slice alignment events both passed for 100,000 rows. Instrumented execution events show completion of the native weight-scale collection, the two-plan native cell/denominator collection and native diagnostic collection. The result contains **2,920,860 internal long-form native aggregate rows** and **62,451 denominator rows**; these include component/replicate records and are not published target-cell counts. No numeric reconciliation or estimator acceptance is implied.

The external 0.25-second monitor recorded 50 resource samples and a sampled peak physical footprint of **4,773,877,520 bytes (about 4.45 GiB)**. The experiment's conservative stop limits were 8,589,934,592 physical-footprint bytes (8 GiB) and 600 seconds; neither stop fired. This sampled physical-footprint metric differs from RSS and is not a guarantee of the true instantaneous peak. It cannot be extrapolated to the full 3,206,859-row core, all products, retained canonical/allocated aggregates or final multi-plan collection, and it does not identify the operator responsible for the earlier full-build kill.

The baseline deliberately used first-N rows, consumed-input hash authentication instead of rerunning production selection/public authentication, an observed/native unit subset, one observed product and a stop immediately after native aggregation. It did not call public build, verification or publication. Those diagnostic shortcuts remain explicit and cannot satisfy any production acceptance gate. Production code, source data and frozen upstream helpers were unchanged.

Evidence remains under `/private/tmp/stage9-task10-20261020-r1/diagnostic-owned/native_100k_product0_r2`. Its nine-file `evidence-inventory.json` was independently rehashed to SHA-256 `1746568b703b4dea869ff9e7ec5685a359bb9c0e5685aaa30a6839e9116f1274`; all nine listed sizes/hashes match. It pins configuration, phase/resource logs, slice-artifact inventory, result and supervisor receipt; the slice CSV stays local. Result pin: `736941cc4160077409e2071d87b71b5919da7cfd3ab4a7f3172523084b0023b1`; supervisor receipt pin: `6b68879acf775ae01b679e65a851fb7915d1d05f2c56e2e18e3074aaecda6761`. The recorded transient driver identity was 21,833 bytes / SHA-256 `2c75d4e35d08d541587c4bdcc3dc9b34398aa33ab6324672c7a92ee03636e661`. This evidence is separate from the preserved 49-file failed-attempt snapshot.

The controller subsequently released the r3 first-product retention experiment and r4 500,000-row scaling experiment described below. These do not change the baseline's non-acceptance scope or establish full-data feasibility. Task 10 remains in progress; all full-data acceptance gates below remain open.

## Bounded diagnostics r3 and r4: first-product retention and scaling

The controller released one r3 first-product run on the same first 100,000 rows, then one r4 run changing the prefix size to 500,000. Both retained the 8 GiB sampled physical-footprint stop, 600-second deadline and explicit `acceptance=false`. These are diagnostic scopes, not public build/verify/replay or scientific-acceptance scopes. Driver revisions, preparation contracts, metadata checks and execution receipts identify what ran. Fresh read-only reviewer `task10_diagnostic_review` (actual inherited Codex runtime; named task-reviewer unavailable) approved the r3 single-command segment and r4 two-change scaling revision with no findings; the r2 identity-comparison fix was addressed with no new issues. The preserved `scoped-reviews.md` records exact reviewed driver hashes and scope. These approvals cover the specified bounded diagnostic commands, not production implementation, the measured finding, scientific acceptance or Task 10 completion. Node-load timing and metadata-collection differences from the production path remain explicit diagnostic limitations.

| Diagnostic | Rows and reached scope | Direct child outcome | Elapsed seconds | Largest sampled physical footprint |
| --- | --- | --- | ---: | ---: |
| `first_product_100k_r3` | First 100,000 rows; observed native plus canonical aggregate retained, same denominator validation/estimate and five-plan collections | Exit 0, no safety stop | 34.153138875 | 5,832,481,704 bytes (~5.43 GiB) |
| `first_product_500k_r4` | First 500,000 rows; stopped within first observed native cell/denominator collection | Supervisor stop, child exit -9; `diagnostic_physical_footprint_limit` | 17.981484042 | 9,939,037,248 bytes (~9.26 GiB) |

For r3, the slice-artifact hash/size inventory exactly matches r2. The raw-numeric/original and original/companion slice alignments passed for 100,000 rows; required PERWT and REPWTP1–80 Decimal checks passed. Native and canonical aggregates remained retained while validation, estimation and the original concurrent five-plan output collections ran in production order. The first-product slice produced the following in-memory diagnostic row counts; no final bundle was published or independently reconciled.

| Materialized diagnostic item | Observed | Canonical |
| --- | ---: | ---: |
| Native long-form aggregate component/replicate rows | 2,920,860 | 24,057 |
| Native long-form denominator rows | 62,451 | 1,215 |
| In-memory target rows | 24,040 | 198 |
| In-memory support rows | 72,120 | 594 |
| In-memory replicate estimate rows | 1,923,200 | 15,840 |
| In-memory eligibility diagnostic rows | 38 | 43 |
| Typed empty residual rows | 0 | 0 |

The r3 external monitor retained 132 samples. Its highest sample's explicit latest-phase label was the observed five-plan `pl.collect_all`, with both native/canonical aggregates and preceding frames retained. The separate event and supervisor clocks have different starts; phase association uses the recorded latest-event label, not an equality of elapsed times. This is evidence about the controlled slice's retained/materialized footprint, not proof of which allocation generated the bytes or the earlier fatal full-build operator. Later products, global concatenation/sort, final bundle validation and publication were not executed.

For r4, both ordered slice alignments passed for 500,000 rows, and the weight-scale validation returned all 81 Decimal weight fields. `aggregate_native` entered at child-event 10.235262 seconds; its weight-scale checks completed and both `_native_groups` lazy constructors returned. The actual two-plan cell/denominator `pl.collect_all` entered at `acs_target_estimation.py:110` at 11.467942 seconds and has no exit event. The external monitor's latest-phase label remained this native materialization through the intentional stop. Canonical construction/aggregation, estimation and output collection were not reached. No completed r4 native aggregate counts or `result.json` exist.

The last three r4 physical-footprint samples were 4,843,510,840 bytes at supervisor 17.355836 seconds, 7,222,715,296 bytes at 17.612032 seconds and 9,939,037,248 bytes at 17.876749 seconds. The last crossed the 8,589,934,592-byte guard. Rapid growth between 0.25-second samples accounts for overshoot; this sampled stop is not a hard kernel allocation cap. Seventy resource samples were retained, the physical metric remained available, RSS fallback was not used and the 600-second deadline did not trigger. The supervisor intentionally killed only its diagnostic child. **This was not another natural macOS memorystatus kill.**

These experiments establish that the 500,000-row prefix exceeded the local diagnostic budget during first native concurrent cell/denominator collection, before canonical retention or output materialization could be necessary. They narrow a source-level engineering boundary to that collection. They do not identify a particular Rust operator, the unrestricted peak, linear/full-source scaling, full-data feasibility or the exact fatal phase of the original 84-minute attempt. The earlier full-build cause remains the separately confirmed kernel memory-pressure kill. No eligibility, universe, weight, numerical bound or scientific contract changed.

The diagnostic shortcuts remain consumed-member hash authentication rather than production selection/public authentication, deterministic first-N rows, observed/native units plus pinned canonical scalar nodes, one observed product and its counterpart, and no later products, full-bundle validation or publication. Frozen software/full-Python/dependency and consumed source/mapping/code-node identity checks are recorded in the diagnostic evidence. No source edit, upstream helper change, unchanged full retry or cleanup of original failed paths occurred. The only removed artifacts were each exited diagnostic's own slice/spill directories, whose hashes were retained; original failure history remains intact.

The r3 reviewed driver identity is 27,925 bytes / SHA-256 `d8ae6640956f7395fba4ae56b690d3768e689428485e135551bf1784e0c37806`; r4 is 27,939 bytes / SHA-256 `9491d7b54212ab3021e40e5276b1bfed1b699d29b8171f3c5a876ac1798321e9`. Their independently authenticated per-run evidence-inventory pins are `94018db059bfab2fb3ac44c6bfb9329ce9598a1bde997a7f94f6d742837c5b16` (nine members) and `027e48d8c36890ebf5c42d5e95dbee52be5cd75f3be0e11eb3d459d24a2d9f73` (eight members). Supervisor receipt pins are `69ee160ca07259b9609cd85a6fb067315a1e486a214b2ce9eeede847f8bdf55d` and `85a1c9f277060a4509686e8ae4b39487586876cbce7bb5e5e85950f24e36ad1b` respectively. Closed r2–r4 aggregate/metadata evidence is separately preserved under `diagnostic-r2-r4-evidence`, with 47-file `diagnostic-r2-r4-evidence-inventory-v2.json` detached pin `7714d27225f1f598493a894bba8b4b05a3c7ea46d7f4cdcb83cd0649817331d1`. The earlier 46-file diagnostic inventory (`881029e93194a42a86b07d2ed15518e24c7ccfa08c4e4b06030c027ccc7f27f5`) is preserved unchanged; v2 adds the scoped-review summary. No slice microdata are copied into that evidence snapshot or git; the original 49-file attempt snapshot is unchanged.

The controller has opened a separate read-only assessment of owned aggregate spilling and downstream materialization contracts. No fix has been selected or implemented by this record. Task 10, source-resolution design and independent finding review remain in progress; all full-data acceptance gates below remain unrun or unsatisfied as previously recorded.

## Scientific acceptance matrix

No target cell, empty product, unavailable SE or numerical discrepancy has been measured from a published Stage 9 bundle. All six scientific groups remain NOT RUN. Zero failure counters on an unrun group are not passes.

| Required independent group | Status and unmeasured evidence |
| --- | --- |
| 1. Source weights/Q alignment and disjoint funnels | NOT RUN: exact lexical 81-weight alignment, Q raw-domain/status partitions, overlapping reasons, disjoint excluded counts/masses, annual closure, undelivered evidence and civilian 559830 controls remain unmeasured for Stage 9 |
| 2. Universes/all 50 products/periods/denominators | NOT RUN: both universes, strict/sensitivity policy membership, paired restrictions, annual contribution support and empty/nonempty outcomes remain unmeasured |
| 3. Native Decimal sums/all 80 replicates/shares/SEs | NOT RUN: exact native totals, paired replicate numerator/denominator statistics, signed replicates and full 80-replicate SEs remain unmeasured |
| 4. Canonical supported leaves/provenance/coverage | NOT RUN: supported scalar membership, strict exclusions, whole-product/denominator losses and supported-subset denominators remain unmeasured |
| 5. County/MSA/micro/no-CBSA allocation and support | NOT RUN: full/80-replicate conservation, typed county-to-CBSA rollups, separate residuals, nonadditive input vs fractional support remain unmeasured |
| 6. Undefined reasons/replicate numbers/empty products/tolerances | NOT RUN: undefined points/SEs, affected replicate numbers, legitimate empty explanations and complete table comparisons remain unmeasured |

Frozen acceptance bounds remain exact schemas/identities/keys/counts/native Decimal sums; share absolute tolerance `1e-12`; allocated masses and SEs `abs(actual - expected) <= 1e-8 + 1e-12 * abs(expected)`. Logical replay requires exact ordered values/schemas across eight tables and exact substantive report content, omitting only top-level run ID/creation time. No bound, eligibility rule, cell, replicate or product was changed or omitted to make this attempt pass.

The expected eleven-member output contract remains eight Parquets (`targets_observed`, `targets_canonical`, `targets_allocated_area_mix`, `target_units`, `target_support`, `replicate_estimates`, `eligibility_diagnostics`, `allocation_residuals`) plus `inputs.json`, `report.json`, `outputs.json`. **None is present in a final bundle, and no actual Stage 9 output schema, inventory, hash or target pin is available.** The first three expected target tables retain unchanged ordered `targets-v1`; the five auxiliaries retain `acs-targets-v1`. These are frozen requirements, not measured outputs.

## Complete declared product registry: outcomes unmeasured

All 50 declared products are listed below to distinguish absence of measurement from legitimate emptiness. For every row, target-row count, empty/nonempty classification, support distributions and undefined-SE counts are **UNMEASURED**, not zero. This registry is read from reviewed software and is not estimator acceptance. Matched 2024 sensitivity is listed separately beside strict 2024 migration; pooled 2023–2024 sensitivity is a distinct product. No strict pooled migration or allocated flow is declared.

| Product ID | View | Family / dimension | Base universe | Policy | Years / divisor | Target/empty/support/SE outcomes |
| --- | --- | --- | --- | --- | --- | --- |
| `52407c90b0462ad4ea53b53139303d9c13837cfc2402fc763787ae8e7b7bdf79` | observed | staffing_pattern / industry_occupation | civilian_employed | strict | 2023,2024 / 2 | UNMEASURED |
| `0def1be053d838a2851cd00ee464efaffce0fc52ec772676978edf7a8c03f9a9` | observed | staffing_pattern / industry_occupation | private_wage_salary | strict | 2023,2024 / 2 | UNMEASURED |
| `fd42a6de23643e114b08850122a66e0c50dcadcbdb2633354da0d72fdc660d6a` | observed | staffing_pattern / industry_occupation | civilian_employed | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `1e4e346daae2d07f8781fcc901885fa17c7178013f544d469822799b1cbf4b94` | observed | staffing_pattern / industry_occupation | private_wage_salary | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `62dc8d653f76d49ea49c50f0051bc03e1a7f20cba41f3f4a81e0fb19b47d8b48` | observed | area_mix / industry | civilian_employed | strict | 2023,2024 / 2 | UNMEASURED |
| `2e0b2c37c641748639433d27ef24cdd3ef1de06483bb41d47d6b67ee24c13062` | observed | area_mix / industry | private_wage_salary | strict | 2023,2024 / 2 | UNMEASURED |
| `07adc49fc0ff01cdf996b05b2b66053ab63c929006713f532638de0efb3e0061` | observed | area_mix / industry | civilian_employed | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `7c7240c1170240394294a432f1acbd22e4bb681a84fb8b4f88d941a13626e791` | observed | area_mix / industry | private_wage_salary | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `ae8af6931ba0fa3c4bc985b7ffc22a0c21f20788d9156729dd1a78f13f97e7f9` | observed | area_mix / occupation | civilian_employed | strict | 2023,2024 / 2 | UNMEASURED |
| `1d7f813147d95213ead814388368a94e15a21fad68b069e138d49be479199182` | observed | area_mix / occupation | private_wage_salary | strict | 2023,2024 / 2 | UNMEASURED |
| `e539779582bf1418b074304820500e78cbbe38a7e37bf3cde986f9c2494c00db` | observed | area_mix / occupation | civilian_employed | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `59bc8c5a7b1e6529f1a4fa8147aed3a37450c2f60b9ce55ff949855d00a54e74` | observed | area_mix / occupation | private_wage_salary | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `8d38d5d4875b7d3082d94d3d1e442153feb841e1a66bc852dd64598b4ca7116a` | observed | commuting_flow / flow | civilian_employed | strict | 2023,2024 / 2 | UNMEASURED |
| `150b962cb0d0a88013519cbb23585b138cf89ca680cc2fa680b55dc3a527f68c` | observed | commuting_flow / flow | private_wage_salary | strict | 2023,2024 / 2 | UNMEASURED |
| `0642ada2184209bd821dcd25010510e01483598b9cc8249234e1c9a1d509f974` | observed | commuting_flow / flow | civilian_employed | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `58c923806c16789ec3660510d39a8a82ba5dea5cc6315cd23dd128bb711fa28e` | observed | commuting_flow / flow | private_wage_salary | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `8e01bf27ee12c09a800c8b5000047a7c2063c9dacc998e89c9e25b87668aeecb` | canonical | staffing_pattern / industry_occupation | civilian_employed | strict | 2023,2024 / 2 | UNMEASURED |
| `ab24c89a53a9b9da3457e676f035543c2d36597e4c9d508973410e5f3ca0fc86` | canonical | staffing_pattern / industry_occupation | private_wage_salary | strict | 2023,2024 / 2 | UNMEASURED |
| `54690d6c7b89804038d8fdb44e930a86109ec9aae0d5cdc3b830a37f9d7852d6` | canonical | staffing_pattern / industry_occupation | civilian_employed | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `066ffda43021b2e21c9e9759877809bf5a3018061c36074670e4d3265e51b6f4` | canonical | staffing_pattern / industry_occupation | private_wage_salary | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `b5e02fb1343a37c4b003897b5e047cbed999db88a822d42e6b6624f0bb3cf330` | canonical | area_mix / industry | civilian_employed | strict | 2023,2024 / 2 | UNMEASURED |
| `81caaebedab0585d03f37289290b75e4b484f077186175cb1d6a10d97c50c17e` | canonical | area_mix / industry | private_wage_salary | strict | 2023,2024 / 2 | UNMEASURED |
| `3de1b026c7dc771c930e16f2b1223cd63e37912d9fef44ad1cce49ccf92b9d5c` | canonical | area_mix / industry | civilian_employed | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `9a678be657761765d3c0617b5c3ff5793f455ed6789459949d45549fd4acec8c` | canonical | area_mix / industry | private_wage_salary | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `03c4e852e7c35b4e2ee16e2d5de21a61c95979e9dee440a1943958a55394790a` | canonical | area_mix / occupation | civilian_employed | strict | 2023,2024 / 2 | UNMEASURED |
| `68b87ba188b67790bc34baff20d9918de79c4b26fa4cc7df4c240d7237c46583` | canonical | area_mix / occupation | private_wage_salary | strict | 2023,2024 / 2 | UNMEASURED |
| `0cb6a14431a56a1156e3d3bb2c10dd8dc3fc89121d792e3d3939e0cdb65e0bf5` | canonical | area_mix / occupation | civilian_employed | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `b1f18161ae0701ccab92affc1939cae6b72b3bd34439d03e142e06da877860bb` | canonical | area_mix / occupation | private_wage_salary | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `1cf742bc62d8c5b2e7588a47929886832e7c723137dc5d74a11106e0afd2fef6` | allocated_county | area_mix / industry | civilian_employed | strict | 2023,2024 / 2 | UNMEASURED |
| `7c1329241c1ffbe942756fda0f836f6cc4aadabca2d100767060a54493c50fc9` | allocated_county | area_mix / industry | private_wage_salary | strict | 2023,2024 / 2 | UNMEASURED |
| `84e8e3574ae28ac210bb7c7d382ab109357a055c5c09b4d73ae54d315874a662` | allocated_county | area_mix / industry | civilian_employed | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `808375a8d4f933432cdc0083b4e98310d3e3f4a09c15548bbbf8a0ceebac91f0` | allocated_county | area_mix / industry | private_wage_salary | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `992f2e995790413833b100f65ac767f999c7d5f6c0024a47e1497d1552684643` | allocated_county | area_mix / occupation | civilian_employed | strict | 2023,2024 / 2 | UNMEASURED |
| `60c853c1186c2f2aad461981a239738d952f433ee092a9933a7391aac383a530` | allocated_county | area_mix / occupation | private_wage_salary | strict | 2023,2024 / 2 | UNMEASURED |
| `406d98d587a00973efcffc35c49df4d346936cbc1a58e29872ec3f4dd4beee4a` | allocated_county | area_mix / occupation | civilian_employed | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `40fc9397159b11868dd4a3d9c75a00637c6e3a5ff40263b5b4aadd59f9dbb4c1` | allocated_county | area_mix / occupation | private_wage_salary | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `878a0c6d4057f864d131d709a310fd083191d861116f022c07357e0197ee7bb5` | allocated_msa | area_mix / industry | civilian_employed | strict | 2023,2024 / 2 | UNMEASURED |
| `192e239b08015c2860ca5a731250d2ebfaa8fdc291baed0f851f24e58813f023` | allocated_msa | area_mix / industry | private_wage_salary | strict | 2023,2024 / 2 | UNMEASURED |
| `b21127f2e23bd38c6975408f84081a43cc1249bca5cde38d6200e4ce8911828f` | allocated_msa | area_mix / industry | civilian_employed | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `9fd979730ce62913c12d45c58861532a6a8dfe988a29be6a332fffa76a2dcafd` | allocated_msa | area_mix / industry | private_wage_salary | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `a5394408f668c0b54e12d2cf250df5a1cbaf3f2c3702faa3a38be4d9d3a385f0` | allocated_msa | area_mix / occupation | civilian_employed | strict | 2023,2024 / 2 | UNMEASURED |
| `57803b68e494106a4130cded650152942f3f76555aa5eeea0604a3953fe35ecb` | allocated_msa | area_mix / occupation | private_wage_salary | strict | 2023,2024 / 2 | UNMEASURED |
| `a59666bd9f85df08dafe6fc62ebe4784c47d7e20a0b6fd18d5c84ccdacc1833a` | allocated_msa | area_mix / occupation | civilian_employed | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `a01d7aeb62612362e2b1d51c7083ccf5b32683e5df8d86777c5b26b4fbdb30e9` | allocated_msa | area_mix / occupation | private_wage_salary | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `6dba282015514413b9c234ce9538874ae370ea768658e413452c8299063c0c05` | observed | migration_flow / flow | civilian_employed | strict | 2024 / 1 | UNMEASURED |
| `9c1a46892bcbe15133eae87f9209e076c96a6fb0143f5fbb8cc0b3037ec4600d` | observed | migration_flow / flow | private_wage_salary | strict | 2024 / 1 | UNMEASURED |
| `746b9eae50fcd25c53f8cf504b3d8fe3abf0d45a861c9dead512ec9213745b09` | observed | migration_flow / flow | civilian_employed | sensitivity | 2024 / 1 | UNMEASURED |
| `0ab18ab35d847bec60de87a0c7b4f90b246fe8dcc8082f881b42a13aa59996e2` | observed | migration_flow / flow | private_wage_salary | sensitivity | 2024 / 1 | UNMEASURED |
| `46e6e74db5ef8a5bed908ed63ddd02f010b3135921d11e8b78c02d140ebc30c0` | observed | migration_flow / flow | civilian_employed | sensitivity | 2023,2024 / 2 | UNMEASURED |
| `c24782ebf53daaf5c382b3eb82a83544b46272182df26f88766e7cb62df59464` | observed | migration_flow / flow | private_wage_salary | sensitivity | 2023,2024 / 2 | UNMEASURED |

## Scoped review of this failed-attempt record

Fresh read-only reviewer `task10_finding_review`, using the actual inherited Codex runtime, reviewed this failed-attempt finding and the README/CLAUDE checkpoint against base `24cb1cc0cf4d167d4aa8df74d920559bc42c8f3f`: Spec Compliant / Quality Approved, with no Critical, Important or Minor findings. The reviewer rehashed all 49 first-attempt and 47 diagnostic-v2 evidence members, matched the review-candidate documents, checked actual command/diagnostic records and checked the prior coverage evidence plus 258 tested inputs (only README/CLAUDE documentation differed). No test suite was rerun for this review. Its approval is limited to this documentary failed-attempt checkpoint; it is not Task 10 completion, scientific acceptance, full-data feasibility, source-fix approval or whole-branch review. The controller-supplied summary and these limits are retained in `.sdd/9-acs-targets/task-10-failed-attempt-review.md`.

## Limits and remaining work

No comparison to a published reference total, ratio or SE was completed. In particular Stage 7's age-16+ resident context is not adopted as a Stage 9 workplace estimand or substituted for a matched universe/period benchmark. No eligibility tuning or external agreement is claimed.

The approved scientific limits remain binding: literal factor-1 PERWT and numbered REPWTP1–80, Decimal native sums and one division by declared k; strict 2024 and matched 2024 migration versus separately pooled sensitivity; supported canonical leaves and denominators; workplace-only population allocation; separate 2020 population/PUMAs, 2022 composition, 2025 county inventory and July 2023 delineations including all nine Connecticut regions. Sampling SEs are conditional on fixed allocation factors and quantify neither allocation error nor mapping uncertainty. Shares condition on identified eligible pairs. Migration is domestic geographic movement, not prior-job or job-related movement. Every future target retains `size_gate_pending`; no minimum count is chosen. Evaluation data cannot be used for embedder training, mining or model selection.

Fixture/repository readiness remains separate from full-data feasibility and acceptance. Earlier Stage 7/8 statuses, seals and adoption records are unchanged. Later-stage CPS/ITA targets, worker profiles, five-year/vintage comparisons, V9 and full eight-family V12 remain outside this attempt. Stage 9 is unticked; Task 11 completion and final integration were not performed.

The 49-file / 8,370,586-byte immutable first-attempt control snapshot is independently inventoried by `attempt-1-evidence-inventory.json`, detached SHA-256 `31d4637bdfc33f6a2130f314ab98f29787f5fa1e666ce7b011427d62f3a94278`. It includes the freeze/prefix, completed command logs/receipts, tested identity, resource snapshots, component check, product registry, source metadata, narrowly scoped kernel evidence, diagnostic-report snapshot and structured `validation_report.md`. The inventory excludes itself and its detached hash, and later diagnostic additions are separate evidence rather than a rewrite of this snapshot. No scratch microdata are copied into this snapshot or git.

Local timing/status/full-log/checksum evidence is also retained in `/private/tmp/stage9-task10-20261020-r1`; the incremental implementer report is `.sdd/9-acs-targets/task-10-report.md`. The controller owns further diagnosed resolution, independent review, the ledger and any final commit. No failed path may be reused or overwritten; subsequent execution requires fresh IDs/controls and the applicable reviewed-software/freshness gates.
