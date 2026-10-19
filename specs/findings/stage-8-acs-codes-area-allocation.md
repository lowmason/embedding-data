# Stage 8 ACS codes and area allocation — measured science finding

Measured finding, 2026-10-19; r7 Phase A, both detached verifiers, ordered eight-table/substantive-report replay, both full independent reconciliations, preservation, identities, audit and final immutable science closure passed. The science is accepted and sealed at fixed source HEAD `1542f8d8f1db2e55f28b9cfec4b1306739589ce8`; the sealed r6 source HEAD was `7c7f9942c169b2fb35ecbb2cebd090b10daec3ca`. Task 10 repository completion remains PENDING and the seal records `adoption=false`. This finding records sealed science, not repository adoption, a Task 10 completion marker or execution approval. Stage 8 remains unticked and Stage 9–13 remain planned.

## Scope and selected inputs

The requirements are [the stage spec](../acs-codes-area-allocation.md) and [plan 8](../plans/8-acs-codes-area-allocation.md). Production root is `/Users/lowell/Projects/embedding-data/data`. Microdata, companions, person identifiers and private controls remain local and ignored. Only public metadata, aggregate measurements, inventories and schemas may enter git.

The selected upstream and run identities are recorded here. The external seal and matrix below establish measured science; repository adoption remains pending.

| Input | Historical selected identity / detached pin |
| --- | --- |
| Stage 4 codes | `stage4_v11_20261013_r2` / `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |
| Stage 5 geography | `stage5_geography_20261014` / `5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d` |
| Stage 7 verification | `stage7_ipums_verification_20261015_r2` / `db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc` |
| Stage 7 references | `stage7_ipums_references_20261015_r2` / `3163968dde603ba53f807976dd09b9e40d73235a98c6f36e4e02c67ec4239c9c` |
| Historical Stage 8 v1/39 receipt | `stage8_acs_references_20261017` / `795e98ecf5f6afb56309572ae1b5545dc16dd49f412093fb95bba366bf3e3b05` |
| Historical Stage 8 v2/46 receipt | `stage8_acs_references_20261018_r4` / `052135beb2e77d3cd14b4b800602be9ab36d54aaa43eaf05abffb4d5c14fd2d5` |
| r7 control / first / replay IDs | `stage8_acceptance_20261018_r7` / `stage8_acs_mapping_20261018_r7` / `stage8_acs_mapping_20261018_r7_replay`; both final bundles published, detached verified and science-sealed; repository adoption PENDING |
| r7 reference selection / receipt reuse | Phase A and final seal authenticated v1/39 and v2/46 byte equality and exact 87-citation manifest; repository adoption PENDING |
| r7 first / replay output pins | First `1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4`; replay `a115c5f7e2691ecbffe763bd1b6b9780fb6a71bc512a2691cf4014f9857b3565`. Both external builder pins were matched by detached verifiers and final seal; repository adoption PENDING |

The [Stage 7 finding](stage-7-ipums-extract-verification.md) records expected source baselines, not Stage 8 companion measurements:

| Profile / delivery | Historical rows / columns | Historical Parquet SHA-256 | r7 fidelity |
| --- | --- | --- | --- |
| `acs/core` / `usa_00001` | 3,206,859 / 147 | `c07f9e7abe2c5dfdb8f9488a1f574d4cf49ab7945c3ad2ffc9daec5eaba47d10` | Both detached verifiers and C1: 3,206,859 rows; ordered comparison equal; science sealed, adoption PENDING |
| `acs/five_year` / `usa_00003` | 7,456,212 / 148 | `c5846bde221e7785051a4a4075aa6a71cc267a1f4497168a96df05d7c50f78fe` | Both detached verifiers and C1: 7,456,212 rows; ordered comparison equal; science sealed, adoption PENDING |
| `acs/vintage` / `usa_00002` | 1,575,420 / 146 | `b6ffab7bd974f72b4fbc913f261779f5ce3145a915849bf92e946bb6b649240d` | Both detached verifiers and C1: 1,575,420 rows; ordered comparison equal; science sealed, adoption PENDING |

Stage 8 independently preserved all 12,238,491 rows in both verified companion sets. Stage 7 machine `measurement_status=unresolved` remains unchanged; its externally documented adoption is separate from machine status.

## Software and bounded decisions

For the sealed r6 attempt, `task-9-provenance-fix-review.md` approved the complete `187340e..7c7f994` source wave. Its normal hooked commit recorded 2,099 tests, zero failures/errors/skips, 1,147.409s; its earlier failed/interrupted hook remains failed evidence. The required r6 all-files run later passed 2,099 tests with zero failures/errors/skips, and the r6 artifact review passed. Those are historical software/review gates and do not accept mapping. The r7 two-path streaming-join correction committed as `1542f8d8f1db2e55f28b9cfec4b1306739589ce8` after review; fresh all-files, Behave, Ruff and lock checks passed. Its six-file operational package and review received an exact controller release for Phase A, then a narrow B1 release. A separate verifier-only recovery release covered the first bundle; the controller then authorized one B2 replay build, detached verification and comparison. Final closure reauthenticated source/package identities at the same clean HEAD; post-document hooks and whole-branch completion review remain PENDING.

| Decision | Exact approved boundary; preserve full machine diagnostics |
| --- | --- |
| D4 | PUMS `7640/49-90XX`, constituent `7550`, resolves through Census to SOC `49-9095`. Preserve erroneous `40-9095` as rejected evidence. No general repair or new special. |
| D5 | Only selected Stage5 run/pin may retain creator CLI hash `68778e16b7cc051745c1e34d3dee6a9fc044fd12b1f78103773984503e9f9742` against executing hash `32a86b3d07bf112fabc1edb01fd10a966e840c185642e55d00f35dfd435220b3`, also authenticated by Stage7/8 inventories. Every other identity remains strict. |
| D6 | Historical completion of the exact failed unfrozen snapshot under its 32-file ledger, adding only seven missing Geocorr kinds to 39. Retain original baseline and old/new software transitions. Bounded recovery is not a generic resume API. Strict UTF-8/CP1252-compatible decoding never transcodes original bytes. |
| D7 | Reject only exact Geocorr original `9d7ef74ba87b2b3bd4b22303c4c0910a4da0bca966721232c0e9b4461737e04d` assertions: row1136 `16/01300/16005` afact `0.669 `, row2428 `30/00500/30013` afact `0.5432 `, row2662 `34/01404/34013` afact2 `0.1252`. Stored factors derive from integer populations. Other discrepancies fail; cause stays unknown. |
| D8 | Under occupation HTML original `61862b9ac0e7bfc4500cc28c3664c50adfc8dc51517c7d81f0192fa37e73725c`, reject only rows692 `790/519160`,789 `9051/532031`,843 `9820/553010`; positive canonical pairs are `7905/519160`,`9050/532031`,`9825/553010`. Preserve literals/locators/support; no source repair or CPS rule. |
| D9 | CT-only Census block POP20 joins, exact PUMA/town/nine-planning-region controls, explicit verified zero exclusions. Preserve rejected Geocorr CT assertions. No whole-town/area weighting, residual fabrication, tolerance widening or legacy-county relabel. V2 adds seven originals to 46 while retaining strict historical v1/39 verification; output contract/dependencies/upstream files stay fixed. |
| C1 | Only migration/five-year/`us2024c`/release2024/component2022/literal `988+88888` is documented_unavailable, with positive DDI plus both authenticated documentary anchors. Preserve raw values, null state/factor and no allocation/split/frame-recoding claim. Exact UK/USSR positive foreign labels use existing migration `00001` compatibility; no fuzzy/numeric foreign heuristic. |
| D10 | Only native2017 `2970/33299M`,`2980/332MZ` follow agreeing PUMS ACS95/96 and full Census explicit2017 crosswalk I:K79/80. Include332996 under2970 and exclude under2980; four/nine possibilities. Full-detail D:E83/84 remain rejected membership assertions, causeunknown, excluded from positive support. All other admitted industry categories/vintages must agree across complete originals. |

D10 positive sets are `2970=[332992,332993,332994,332996]` and `2980=[332510,332613,332618,332911,332912,332913,332919,332991,332999]`. The intake's 4,195 selected category records are not a fine-industry332996 count. Runtime/independent readers preserve every agreeing PUMS/canonical locator, including Construction/Management duplicates. Titles and dates confer no additional authority. Cite the approved plan Decisions for exact documentary hashes and proposal identities.

## Historical attempts are not accepted mapping runs

Read `task-9-production-d9-report.md`, `task-9-r5-prebuild-failure-report.md`, `task-9-r6-failure-closure.md` and sealed evidence for chronology. Original/r2/r3/r4/r5/r6 controls contain 30 / 20 / 46 / 337 / 627 / 474 files. R6 closure authenticated the preceding five controls and externally sealed r6 at 28,965,065 bytes; r7 C1 and final science closure reauthenticated all six controls, nested/external seals and inventories. Never copy private controls into git.

R4 published the historical v2/46 receipt and accounted for 87 suffix records, then failed actual prebuild interpretation on 17 migration keys: 1,914 foreign-label records plus 2,520 selected suppression records. No mapping build existed. Its completed reference/geography/classification substeps were partial gates. Failure closure/preservation and sealing did not accept mapping.

R5 reused both receipts without imports/appends after reviewed role fixes. Prebuild failed before the first mapping build because independent industry provenance incorrectly required a unique physical support row; eight agreeing duplicate instances exposed the assumption. Runtime roles covered 36,229 keys, including the known 1,914 foreign + 2,520 unavailable records. Independent populations / 9,380 rounding assertions and candidate checks returned before provenance failed. Full independent role/person-frequency gates and actual builds/replay were not reached. R5 failure closure retained original baseline, exact 87 citations and old seals, then sealed the failure. New reviewed source fixes do not turn r5 into a passing run.

R6 continuation and its full actual prebuild passed under reviewed source and package. Its prebuild checked 1,062 lookup keys, 4,197 membership assertions, 6,349 observed keys, all 36,229 independent original role keys, all 9,380 published rounding assertions and exact D10 runtime/independent diagnostics. It measured 12,238,491 source rows and the 559830 profile counts 5,204 / 14,799 / 3,405; the population/factor subchecks and audit also passed. These were prebuild gates only. They did not verify completed companions, first/replay publication, detached pins, full postbuild person reconciliation or production acceptance. R7 reran the gates under its final source and fresh control.

R6 then failed during its first actual offline production mapping build, before completing the five-year companion. The wrapper exited 1 after 242.841693 seconds with no Python traceback; kernel logs explicitly record a no-paging-space kill of a python3.14 process in the build interval, although the launcher did not retain a direct child PID or raw signal. Installed Polars 2.0.0 compile-only evidence shows the nine `validate='m:1'` companion joins produce an in-memory fallback; the exact allocation at termination and a successful full-build memory bound remain unknown. The failed `.part` has seven retained files, 896,504,701 bytes, including an 890,354,614-byte core file and zero-byte five-year file. R6 was closed and sealed as **CLOSED_FAILED_FIRST_MAPPING_BUILD**: one mapping attempt, zero successful builds, no final/replay bundle, no `outputs.json` and no detached output pin. Stage 8 acceptance remained false. Its external seal is `9a458d220f176472bd9e42d11673c36194628b899fc0039236098912d26e6674`; original baseline, exact 87 citations, both receipts, upstreams and zero external access counts were preserved at closure. This history cannot fill r7 result cells.

## R7 measured milestones

**Phase A actual prebuild, stopped before build.** The authenticated Phase A report (`.sdd/8-acs-codes-area-allocation/task-9-r7-production-phase-a-report.md`) has SHA-256 `aa128caf9982ce892a4cf25c2830fe22bce50c7f3accf57f7fe06434fdbf28ea`; its science summary (`.sdd/8-acs-codes-area-allocation/task-9-r7-production-phase-a-science-summary.json`) has SHA-256 `57e4554869921cbcb43fbd8fa1fd0d6af9fb202ac0da061f15509d1b0cbcab80`. At clean source `1542f8d`, check-only exited 0 in 8.017327416 seconds, one apply exited 0 in 19.574190292 seconds, actual prebuild exited 0 in 85.784199375 seconds, and the final guard exited 0 in 8.960 seconds. The Phase A control milestone inventory was 39 files / 18,952,508 bytes, externally hashed as `7edd93d2e6783a5aa1e5fdc949f111dd74dbd4c5b981ba3a825ed6a18aff66a1`; it is not a final science seal.

Actual Phase A prebuild measured 12,238,491 source rows (3,206,859 core / 7,456,212 five-year / 1,575,420 vintage) and 559830 counts 5,204 / 14,799 / 3,405. It passed 1,062 lookup keys, 4,197 membership assertions, 6,349 observed keys, all 36,229 independent original role keys, exact equality for two D10 runtime/independent rejected-membership records, all 9,380 D7 rounding assertions with the three bounded rejections, CT's 49,926 blocks / 3,605,944 population / nine zero-ambiguity controls, V8 population 334,735,155 complete and 331,449,281 scoped, 7,754 role-expanded county factor rows and 2,328 MSA relations, and maximum closure `3.3306690738754696e-16`. Audit reported zero discrepancies and all eleven offline access counters were zero. Continuation and final collection preserved the original 5,490 files, exact prefix and 87 suffix records, both receipts, all six older seals and the seven-file r6 failed partial. These are prebuild measurements; companion fidelity, detached verification, replay and full postbuild reconciliation were still unmeasured at this milestone.

**Phase B1 first publication with timing-wrapper exit 1.** The authenticated B1 forensic report (`.sdd/8-acs-codes-area-allocation/task-9-r7-production-phase-b1-report.md`) has SHA-256 `30e38f30cb0e4ddfc13705beaa8ada3f7c23e23a44b631955e88b0b1ae2f68df`. A single first builder published `stage8_acs_mapping_20261018_r7` and emitted the external `outputs.json` pin `1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4`; the final directory contains 11 files / 3,625,607,149 bytes, with no first `.part` or replay path. The outer `/usr/bin/time -l` then encountered sandbox-denied `sysctl kern.clockrate`, so the harness recorded exit 1 after 468.336132375 seconds. The raw first-builder Python child wait status was not captured and remains unresolved despite the later verifier's separate direct exit 0. Builder stdout and guarded shutdown support publication. No maximum RSS or peak footprint was printed. The published report claimed companion rows 3,206,859 / 7,456,212 / 1,575,420; the later detached verifier measured these same row counts below. B1 preservation and eleven zero access counters were reported; final closure was still PENDING at that checkpoint. The narrow verifier-only release (`.sdd/8-acs-codes-area-allocation/task-9-r7-b1-detached-verifier-release.md`), SHA-256 `ec457f412855e13f0e943c76984c9b3d234cf04aa6b41c68de169217c01c5544`, authorized detached verification of this existing bundle only.

The root-recomputed B1 first-bundle inventory has SHA-256 `c605a1aceaa8f15639d695b31f8cb73898e49988d128216c3fbae51fd8c5cd01`; the B1 control milestone inventory is 57 files / 18,988,223 bytes, SHA-256 `8e08e2ac800340f099f4bf444c324b4257f390fe70f8c0f2f49d587370370540`. These are physical published-file records, not accepted logical schemas or replay results:

| B1 published file | Bytes | SHA-256 |
| --- | ---: | --- |
| `acs_area_lookup.parquet` | 5,300,143 | `505acc3447039069f2266c5c0a0f09b1b460006ce4d8b831b50d1d94eca646fc` |
| `acs_code_lookup.parquet` | 116,423 | `4b09b6963c3a2d9cc4c062fc62860bb6be0468f510ef2d3b7fccf445d53e397d` |
| `acs_core_canonical.parquet` | 910,539,068 | `971866f3366af95876f7c17614c0e814b01773aaaff635e4beeab37fae5f7276` |
| `acs_five_year_canonical.parquet` | 2,260,787,201 | `98ff0f9cfb03bd3a6899f8b49f913e1a4b466edbaf9404244e5e15d6239ad782` |
| `acs_vintage_canonical.parquet` | 443,408,757 | `6ee43cfcb420f65b24e16cce35479d905f2de6e85606bda80b88955f857122e1` |
| `inputs.json` | 4,441,380 | `85caba077df6116b941016d8020c613b68a1de57a8dcdf19dea38d49fa3fb7ee` |
| `outputs.json` | 56,393 | `1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4` |
| `puma_county_factors.parquet` | 609,709 | `b4ffb5c81d9c0ddca0032667474de32f8ec509956f8ea2be3ccaa7a71de80ec0` |
| `puma_msa_coverage.parquet` | 48,988 | `610e1aa0c776bc031fe3f4a2a138ded9f54f80b5cb48755dcf5647bca4da7f7b` |
| `puma_msa_factors.parquet` | 74,824 | `e716184b9e74d51b08f0e7771780a64fc9118c4030e56edbb63728e8db352557` |
| `report.json` | 224,263 | `1133d5511d47b8a3f42a8ccef586defd6a532286b56dd0cc3bec47814fe5f180` |

**B1 detached first-bundle verification: PASS, stopped before replay.** The authenticated detached report (`.sdd/8-acs-codes-area-allocation/task-9-r7-production-phase-b1-detached-report.md`) has SHA-256 `ffb1f30c18617816e9f9049ab3cde5a1feff3fbd9ff9c5865cdf5b492e5a1dd0`; its evidence JSON (`.sdd/8-acs-codes-area-allocation/task-9-r7-production-phase-b1-detached-evidence.json`) has SHA-256 `71e33ff77782af324b3ab535a7ec94d2f7c3c26d2834295141fb7cc3c0b45233`. One released public verifier used the original external pin `1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4`, returned `status=verified` and the identical `outputs_sha256`, and had a directly captured Python child exit 0 after 326.852940750 seconds. Its own direct wait used no time utility. All eleven offline counters were zero. This does not supply the raw child exit from the earlier first build's failed timing wrapper.

| First verifier reported table | Rows |
| --- | ---: |
| `acs_area_lookup` | 36,229 |
| `acs_code_lookup` | 1,062 |
| `acs_core_canonical` | 3,206,859 |
| `acs_five_year_canonical` | 7,456,212 |
| `acs_vintage_canonical` | 1,575,420 |
| `puma_county_factors` | 7,754 |
| `puma_msa_coverage` | 2,462 |
| `puma_msa_factors` | 2,328 |

The verifier's `mapping_gate` and `factor_gate` both say `status=measured`, `adopted=false`; composition conflicts are zero, factor conservation is `pass`, and `limits.full_data_acceptance=false`. Exact 11-file first bundle and prior 57 control files were unchanged, as were all 39 Phase A files, original 5,490 files/prefix/exact 87 citations, both receipts, six older controls, seven-file r6 failed partial and full manifest. The B1 detached-checkpoint r7 control milestone inventory was **70 files / 19,013,302 bytes**, SHA-256 `d81d2e9f2807ca577f3b2089d51a472d593669c1b1a9fe2daf34246063ad3574`; it was not a science-closure seal. No rebuild or replay ran at this checkpoint. B2 replay and comparison followed below.

**Phase B2 replay, detached verification and logical comparison: PASS, stopped before reconciliation.** The authenticated B2 report (`.sdd/8-acs-codes-area-allocation/task-9-r7-production-phase-b2-report.md`) has SHA-256 `3920ba9adfbee537da253e19b38ff7283b8fbff2bd18525c6d5e3595adab308f`; its evidence JSON (`.sdd/8-acs-codes-area-allocation/task-9-r7-production-phase-b2-evidence.json`) has SHA-256 `e295a311efd672dbe8eb4701d164ae19328ed5f93993d42875842d42146f78ef`. One fresh replay build emitted external `outputs.json` pin `a115c5f7e2691ecbffe763bd1b6b9780fb6a71bc512a2691cf4014f9857b3565`; the replay verifier returned `verified` with the same pin. Direct Python child waits, without a time utility, recorded preflight exit 0 / 10.861692959 seconds, build exit 0 / 424.940705250 seconds, verifier exit 0 / 342.604351500 seconds, and comparison exit 0 / 741.333820916 seconds. All eleven offline access counters were zero in every phase and final collection. The original first-build timing-wrapper exit 1, unavailable raw builder child status and unavailable peak memory remain historical facts; B2 did not re-run that build.

The replay verifier reported the same eight row counts as the first verifier: area lookup 36,229, code lookup 1,062, core companion 3,206,859, five-year companion 7,456,212, vintage companion 1,575,420, county factors 7,754, MSA coverage 2,462 and MSA factors 2,328. The comparison returned `equal=true`, `substantive_report_equal=true`, and `schema_equal=true` / `values_equal=true` for every one of the eight ordered logical tables. Its `trust_established=false` means comparison by itself does not authenticate either bundle; the two separate detached verifier results provide their respective pin checks. Both verifiers keep mapping and factor gates `status=measured`, `adopted=false`, factor conservation `pass`, composition conflicts zero and `limits.full_data_acceptance=false`. Logical replay is not a physical-byte equality requirement.

The replay physical inventory (`.sdd/8-acs-codes-area-allocation/task-9-r7-production-phase-b2-replay-bundle-inventory.json`), SHA-256 `a2c555a961d6e25791e3a6ee7cca7776c4502507db06452f2c3d3429a900bc7e`, has eleven files / 3,625,607,163 bytes. The first bundle's separate eleven files / 3,625,607,149 bytes remained byte-exact. Identical Parquet hashes and different run-specific JSON hashes are physical observations; the complete ordered-table and substantive-report comparison is the logical replay evidence.

| B2 replay published file | Bytes | SHA-256 |
| --- | ---: | --- |
| `acs_area_lookup.parquet` | 5,300,143 | `505acc3447039069f2266c5c0a0f09b1b460006ce4d8b831b50d1d94eca646fc` |
| `acs_code_lookup.parquet` | 116,423 | `4b09b6963c3a2d9cc4c062fc62860bb6be0468f510ef2d3b7fccf445d53e397d` |
| `acs_core_canonical.parquet` | 910,539,068 | `971866f3366af95876f7c17614c0e814b01773aaaff635e4beeab37fae5f7276` |
| `acs_five_year_canonical.parquet` | 2,260,787,201 | `98ff0f9cfb03bd3a6899f8b49f913e1a4b466edbaf9404244e5e15d6239ad782` |
| `acs_vintage_canonical.parquet` | 443,408,757 | `6ee43cfcb420f65b24e16cce35479d905f2de6e85606bda80b88955f857122e1` |
| `inputs.json` | 4,441,387 | `ef95cff08c4348b5a892f448c9e32c69bb400ded86853267b8cf63dab9e19345` |
| `outputs.json` | 56,393 | `a115c5f7e2691ecbffe763bd1b6b9780fb6a71bc512a2691cf4014f9857b3565` |
| `puma_county_factors.parquet` | 609,709 | `b4ffb5c81d9c0ddca0032667474de32f8ec509956f8ea2be3ccaa7a71de80ec0` |
| `puma_msa_coverage.parquet` | 48,988 | `610e1aa0c776bc031fe3f4a2a138ded9f54f80b5cb48755dcf5647bca4da7f7b` |
| `puma_msa_factors.parquet` | 74,824 | `e716184b9e74d51b08f0e7771780a64fc9118c4030e56edbb63728e8db352557` |
| `report.json` | 224,270 | `4862695fae7be4adace0ac897b5d8dfeb100a581bc818005df3e9dec7bc35c8d` |

The current r7 control milestone inventory is **93 files / 19,056,816 bytes**, SHA-256 `2e7e02efd44c951e26846beb64c0ac4702c3543369f803552a5977b6ccf78582`. Its prior 70 files and all 39 Phase A files were unchanged. Both bundle partials were absent; original 5,490 files, prefix/exact 87 citations, both receipts, six older controls, seven-file r6 failed partial and full manifest stayed unchanged. This is not a final science-closure seal. Full independent reconciliation of BOTH companion sets and final preservation/audit/history/seal closure remained PENDING at that checkpoint.

**Phase C1 independent science reconciliation: PASS, before final closure.** The authenticated C1 report (`.sdd/8-acs-codes-area-allocation/task-9-r7-production-phase-c1-report.md`) has SHA-256 `2ec6cd8c3948e7d9c2481ecc3fff88702baa9c6f6711a7fbef98f2d88c6e3156`; evidence JSON (`.sdd/8-acs-codes-area-allocation/task-9-r7-production-phase-c1-evidence.json`) has SHA-256 `043e55f51ce1aff41d7ddc158e0579833d705feb622322815c335918056b5bbf`. Committed independent reconciler `scripts/reconcile_stage8.py` SHA-256 `8a07314aeac4276d74b3e005ea845aa0d60346c7a39e7de71e25db3afc323ac4` checked BOTH externally pinned bundles against original sources and references. Its two complete aggregate stdout files are byte-identical, **794,347 bytes each**, SHA-256 `7a94523b1f1985ff8d18bbb8418e3bfb5d889d3ade65fb0de98da0cff526cd83`; each has `failure_count=0`, and `code_frequencies_equal`, `population_reconciliation_equal`, `role_status_counts_equal` and `candidate_memberships_equal` all true. Direct child exits were 0 for preflight / 13.139248916 seconds, first reconcile / 32.699943042, replay reconcile / 34.863845625, preservation / 7.892628875, audit / 1.486677709 and identity recheck / 15.302597125. All eleven denied-seam counters stayed zero. The 123-file / 20,840,974-byte C1 control inventory (`.sdd/8-acs-codes-area-allocation/task-9-r7-production-phase-c1-control-inventory.json`) has SHA-256 `78c8ec537737b227b7907118fda3d9a2fb971417cebbf323cea2b6970651add9`; it is a milestone snapshot, not the final seal.

C1 independently reconciled all **12,238,491** ordered source rows across core / five-year / vintage (**3,206,859 / 7,456,212 / 1,575,420**), including original ordered schema prefixes, every source value/order/duplicate, source SHA-256 and zero-based UInt64 ordinal, annotations, source Q frequencies, classification candidates/provenance, role status and allocation, and complete population arithmetic. Industry and occupation unparseable counts are zero in each profile. Population totals are **334,735,155** complete and **331,449,281** scoped, with 7,754 role-expanded county factor rows and 2,328 MSA relations, closure error `3.3306690738754696e-16` and published Decimal rounding bound `0.000050000001`. CT uses 2020 Census block POP20, 49,926 blocks and 3,605,944 population; D7's three and D10's two bounded rejected assertions retain their original locators and unknown causes. The independent science audit (`.sdd/8-acs-codes-area-allocation/task-9-r7-science-audit.md`), SHA-256 `6c6891359b0b2781759285356d0a3ad9b58147101ca7708d497955155ae67815`, found no new source contradiction, unexplained person-key gap or failed independent arithmetic through C1.

C1 preserved the original **5,490 files / 6,694,161,286 bytes**, exact **1,491,443-byte prefix** and 87 accounted suffix citations with **zero new raw appends**, both receipts, six prior sealed controls (30/20/46/337/627/474 files), seven r6 failed partial files / 896,504,701 bytes, all prior 93 r7 control files and both eleven-file bundles. Both `.part` paths were absent and whole-tree audit found **zero raw provenance discrepancies**. Selected Stage 4/5/7/reference pins, 54 executing members and seven independent members, source/review/release identities, dependency/lock identities and exact D5 compatibility were checked. At that checkpoint, C1 evidence set `acceptance_pending=true`; no complete history copy, final science seal, tracked adoption or Task 10 completion had occurred. The first-build timing-wrapper exit 1 and unavailable raw builder child status remain historical.

**Final science closure: `SCIENCE_CLOSED_PASS`; repository completion PENDING.** The external immutable science seal (`.sdd/8-acs-codes-area-allocation/task-9-r7-final-science-seal.json`) is **451,990 bytes**, SHA-256 `b09d1a56308f09d6e99f97070c02ffbbc0523d6c595f7901bb0e01a999bd3ddf`, at the same clean source HEAD `1542f8d8f1db2e55f28b9cfec4b1306739589ce8`. It records a complete **880-file / 40,485,134-byte** r7 control inventory with canonical inventory SHA-256 `7af71e3b57c6c07867224259f49563c20e0cd3b75e1d99f54b4cea4f92cc221a`; its `control_files` serialize to that hash. The seal is mode 0444 with macOS `UF_IMMUTABLE` and excludes itself from the inventory. Its external proof is **427,930 bytes**, SHA-256 `932eee4679d0a66f6cb201892cfa71f10fa9cc04754c5c1bc8703a7645f886db`; final reauthentication is SHA-256 `a0375f923a99d3be7a2f7342d8e5a32760ee47ea8309d4baf1bd61c7c2d5f423`; complete history inventory is SHA-256 `50d258d9330a8279e4544b1de3927b2aab0e4f0e8c0c357427e0b51c5c30821e`. The external, ignored closure proof report (`/Users/lowell/Projects/embedding-data/data/derived/acs/mapping-controls/stage8_acceptance_20261018_r7/r7-final-science-report.md`) is **2,282 bytes**, SHA-256 `9965c7dcc8991cd9cf77757db15f9c49fffc86054c287cfa4e2581d27b352fc2`.

Closure reauthenticated both external bundle pins and physical inventories, direct detached checks, eight ordered logical table pairs and substantive-report equality, both complete C1 aggregates, all 123 prior r7 control files, original 5,490 files / 6,694,161,286 bytes, exact 87-accounted citation suffix, six older sealed controls, r6 failed partial, source/software/dependencies and eleven zero external-access counters. It copied complete ignored Task 9 history, operational originals, source-check output, all 227 tracked source/test/specification/dependency files, closure scripts and audit logs byte-exact into the external history; fresh whole-tree audit remained zero. The closure preparation direct child exited 0 in 13.707034666993422 seconds and final reauthentication took 12.744108457991388 seconds. The seal declares rows 1–19 science PASS and row 20 preservation PASS / repository completion PENDING, `adoption=false` and `task10_repository_completion=PENDING`. It does not resolve the historical B1 timing-wrapper exit 1, unavailable original Python child wait status or unavailable peak RSS.

**Independent V8 whole-county check.** The read-only full-source report (`.sdd/8-acs-codes-area-allocation/task-10-v8-split-measure.md`), SHA-256 `76955b277c2392e68b747c2ae2697337c409aea19f7b2bf716d91f66170f3eb0`, independently rehashed the selected v2/46 receipt and all 46 originals, read the complete original 2020 PUMA and 2022 county composition workbooks, reconstructed CT from seven official originals, and compared every accepted relation with its county's group. Its measurement script `/private/tmp/stage8_v8_split_measure.py` has SHA-256 `6de7e106260a959d691abf1e05bfa65f1339133a06f3730bca8394c41f066122`; its JSON result `/private/tmp/stage8_v8_split_measure.json` has SHA-256 `08ea3a33e0a9771b876361fc36224fa05aee21595b4a15daf93b10a0cbd622ab`. On the complete selected set, **zero of 3,222 counties** belong to more than one composition group and **zero of 4,689 accepted PUMA–county relations** disagree with the county's group. All **2,486 PUMAs**, **3,222 counties** and **1,027 groups** reconcile their integer marginals and group populations; complete population is **334,735,155**, with **331,449,281** in domestic scope excluding Puerto Rico. CT has **26 accepted positive relations** reconstructed from blocks in place of **27 original Geocorr CT relations**; the one disputed Geocorr assertion remains preserved as rejected evidence. Nine ambiguous CT blocks have **zero population** and are excluded under the exact CT rule. The output's **7,754 role-expanded county factor rows** are distinct from the **4,689 unique residence PUMA–county relations** checked here. This establishes the whole-county group rule only for the selected **2020 PUMA definitions and reference set**; it makes no inference for another vintage.

## Actual r7 scientific acceptance matrix — science sealed, repository adoption PENDING

The independent science audit (`.sdd/8-acs-codes-area-allocation/task-9-r7-science-audit.md`) assessed all twenty planned gates against Phase A/B1/B2/C1 evidence; final closure reauthenticated that chain at one unchanged source. PASS below means sealed measured science, not final Stage 8 repository adoption. Row 20 separates sealed preservation from pending tracked completion.

| Gate | Required measurement | Actual r7 |
| --- | --- | --- |
| Selected trust | Complete Stage 4/5/7 inventories/raw/schemas/software/dependencies and exact D5 compatibility | PASS — C1 selected pins, 54 executing/7 independent members, dependencies and exact D5 pair |
| References/cache | All 46 originals / receipt; historical v1/39; exact citation set; cached client count 0 | PASS — v2/46 and v1/39 authenticated, 87 exact citations, zero appends/11 external calls |
| Classification | Complete originals; admitted relation endpoints/membership; exact D4/D8/D10 positive/rejected evidence | PASS — 1,062 lookup/4,197 membership/6,349 observed keys; C1 candidate memberships equal |
| ACS V11 | All 12,238,491 rows; zero unparseable; mapped/missing/special partitions | PASS — 12,238,491 rows, zero industry/occupation unparseable in all profiles; 559830 special retained |
| Special cross-check | Remeasure 559830 core 5,204 / five-year 14,799 / vintage 3,405; investigate disagreement | PASS — exact 5,204 / 14,799 / 3,405 match Phase A, C1 and selected Stage 7 |
| Aggregation reasons | Documented category_design/disclosure plus unknown counts/locators; candidate lengths | PASS — among 1,062 lookup keys, 30 `category_design`, 32 `disclosure`, 607 unknown and 393 not applicable; exact source-row status/length partitions and original locators below |
| Vintage/provenance | Delivered versus interview scheme, source recoding, SOC2018, retained singleton flags | PASS — annual 2022 native2017; delivered 2023–24/five-year native2022; component recoding and flags checked |
| Original fidelity | Three complete ordered prefix schemas/values/order/multiplicity; source SHA and UInt64 ordinal | PASS — BOTH C1 original-prefix/annotation checks for 3,206,859 / 7,456,212 / 1,575,420 rows |
| Q/source evidence | Every Q type/value, core String/all-null 2023 QMIGRAT1, five-year Int64, vintage absence; null/unavailable retained | PASS — C1 original Q dtype/value frequencies and annotation statuses equal |
| Roles | Disjoint statuses per profile/sample/release/component/role; complete keys; bounded C1; zero unknowns | PASS — all 73 component-level status rows and 36,229 Phase A keys; C1 role partitions/allocation flags equal |
| Residence factors | Exact integer intersections and independent PUMA/county controls, all applicable keys, closure<=1e-12 | PASS — 7,754 role-expanded county factor rows; complete/scoped population 334,735,155 / 331,449,281; max closure 3.33e-16 |
| V8 | Full PUMA→group AND county→group checks; counts/splits/membership/populations; no fabricated weights | PASS — 0/3,222 multi-group counties and 0/4,689 accepted relation/group mismatches; 2,486 PUMAs, 1,027 groups, population 334,735,155 complete / 331,449,281 scoped; selected 2020 definitions only |
| Frame compatibility | Nine CT regions, no relabel, county/CBSA type/nonmembership retained; distinct frame years | PASS — CT 49,926 blocks / 3,605,944 population; nine explicit zero exclusions; distinct frames retained |
| MSA intersections | Complete before scope; both conditioning directions; whole-MSA/PUMA integers; non-MSA residual including absent PUMAs | PASS — 2,328 MSA relations and independent whole-population/residual arithmetic |
| Published rounding | Independent decimal-bound diagnostics, exact D7 rejections; no tolerance widening | PASS — all 9,380 assertions, three bounded rejections, Decimal bound 0.000050000001 |
| Atomic publication | Fresh final/partial/race checks; no mapping bundle on failure; owned cleanup only | PASS — r6 failed partial retained; r7 first/replay final eleven-file bundles; both partial paths absent |
| Offline chain | Fixture readiness cited separately; actual network/.env/credential/IPUMS constructor counts0 | PASS — actual guarded build/verify/reconcile phases show all eleven counters zero |
| Detached/replay | Two external pins/verifiers; eight ordered logical tables and substantive report equality | PASS — both detached verifiers; B2 eight schema/value pairs and substantive report equal |
| Independent reconcile | Full source frequencies/flags/statuses/candidates/provenance and population/group/MSA arithmetic | PASS — BOTH C1 direct exits 0, byte-identical aggregates, failure_count 0 and all four equality flags true |
| Preservation/repository | Original inventory/prefix, exact accounted suffix, all seals, audit 0, required checks/reviews | Scientific preservation and external seal PASS — 880-file control inventory, original/87/six old seals/r6 partial/both bundles unchanged, audit 0; post-document checks, whole-branch review and Task 10 repository completion PENDING |

Original beforestate: 5,490 protected files / 6,694,161,286 bytes; 1,491,443-byte manifest prefix SHA256 `86b2ab169a9d248fd9bfd7b69b632b4f3a8b6fcb0214c80e0a07d978d43601c4`. Historical whole-manifest boundary: 1,548,012 bytes SHA256 `57eaff0ffb7c3da57aaf9ba0d7efd732515e64081bb7581766ada5706a427ea5`. A later whole manifest never replaces that baseline. C1 and final seal reauthenticated the original inventory/prefix, all six older seals, r6 failed partial and exact 87 citation bytes, with audit zero.

## Inventories, schemas, environment and timings

The public-safe raw/reference/software/environment inventories and full ordered schemas below are part of this finding. C1 authenticated these identities; the final immutable science seal authenticated the complete control history. Post-document review/checks remain PENDING. Git label is informational, never a replacement for executing hashes.

The code declares eleven files: eight Parquets plus inputs/report/outputs JSON. `outputs.json` inventories the other ten and excludes itself; externally captured SHA authenticates it. The brief's ten-file output inventory refers to payload, not total bundle size.

| Published artifact | Rows / ordered fields | First bytes / SHA-256 | Replay bytes / SHA-256 |
| --- | --- | --- | --- |
| `acs_code_lookup.parquet` | 1,062 / 28 | 116,423 / `4b09b6963c3a2d9cc4c062fc62860bb6be0468f510ef2d3b7fccf445d53e397d` | 116,423 / `4b09b6963c3a2d9cc4c062fc62860bb6be0468f510ef2d3b7fccf445d53e397d` |
| `acs_area_lookup.parquet` | 36,229 / 20 | 5,300,143 / `505acc3447039069f2266c5c0a0f09b1b460006ce4d8b831b50d1d94eca646fc` | 5,300,143 / `505acc3447039069f2266c5c0a0f09b1b460006ce4d8b831b50d1d94eca646fc` |
| `puma_county_factors.parquet` | 7,754 / 20 | 609,709 / `b4ffb5c81d9c0ddca0032667474de32f8ec509956f8ea2be3ccaa7a71de80ec0` | 609,709 / `b4ffb5c81d9c0ddca0032667474de32f8ec509956f8ea2be3ccaa7a71de80ec0` |
| `puma_msa_factors.parquet` | 2,328 / 19 | 74,824 / `e716184b9e74d51b08f0e7771780a64fc9118c4030e56edbb63728e8db352557` | 74,824 / `e716184b9e74d51b08f0e7771780a64fc9118c4030e56edbb63728e8db352557` |
| `puma_msa_coverage.parquet` | 2,462 / 12 | 48,988 / `610e1aa0c776bc031fe3f4a2a138ded9f54f80b5cb48755dcf5647bca4da7f7b` | 48,988 / `610e1aa0c776bc031fe3f4a2a138ded9f54f80b5cb48755dcf5647bca4da7f7b` |
| `acs_core_canonical.parquet` | 3,206,859 / 261 | 910,539,068 / `971866f3366af95876f7c17614c0e814b01773aaaff635e4beeab37fae5f7276` | 910,539,068 / `971866f3366af95876f7c17614c0e814b01773aaaff635e4beeab37fae5f7276` |
| `acs_five_year_canonical.parquet` | 7,456,212 / 262 | 2,260,787,201 / `98ff0f9cfb03bd3a6899f8b49f913e1a4b466edbaf9404244e5e15d6239ad782` | 2,260,787,201 / `98ff0f9cfb03bd3a6899f8b49f913e1a4b466edbaf9404244e5e15d6239ad782` |
| `acs_vintage_canonical.parquet` | 1,575,420 / 260 | 443,408,757 / `6ee43cfcb420f65b24e16cce35479d905f2de6e85606bda80b88955f857122e1` | 443,408,757 / `6ee43cfcb420f65b24e16cce35479d905f2de6e85606bda80b88955f857122e1` |
| `inputs.json` | metadata JSON | 4,441,380 / `85caba077df6116b941016d8020c613b68a1de57a8dcdf19dea38d49fa3fb7ee` | 4,441,387 / `ef95cff08c4348b5a892f448c9e32c69bb400ded86853267b8cf63dab9e19345` |
| `report.json` | metadata JSON | 224,263 / `1133d5511d47b8a3f42a8ccef586defd6a532286b56dd0cc3bec47814fe5f180` | 224,270 / `4862695fae7be4adace0ac897b5d8dfeb100a581bc818005df3e9dec7bc35c8d` |
| `outputs.json` | metadata JSON | 56,393 / `1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4` | 56,393 / `a115c5f7e2691ecbffe763bd1b6b9780fb6a71bc512a2691cf4014f9857b3565` |

First and replay physical inventories are recorded separately above. Full ordered schemas from the first `outputs.json` are printed below and B2 found exact ordered schema equality for all eight tables; repository adoption remains PENDING. Phase A/B1/B2/C1 and final closure process durations are measured milestones. Post-document check durations and raw first-build child wait status remain PENDING. Keep old failed-generation durations explicitly historical.

## Public-safe selected inputs and measured inventories

All tables in this section are metadata and aggregate counts. They contain no person rows or person identifiers. The first bundle `inputs.json` and `outputs.json` supply the machine records; C1 independently reauthenticated selection and the original source, and the final seal reauthenticated C1. These are measured inputs for this finding; external adoption remains false.

### Selected delivery and reference provenance

| Profile | Delivery | Derived Parquet | Rows | Bytes | SHA-256 |
| --- | --- | --- | --- | --- | --- |
| `acs/core` | `usa_00001` | `derived/acs/core/usa_00001.parquet` | 3,206,859 | 407,645,356 | `c07f9e7abe2c5dfdb8f9488a1f574d4cf49ab7945c3ad2ffc9daec5eaba47d10` |
| `acs/five_year` | `usa_00003` | `derived/acs/five_year/usa_00003.parquet` | 7,456,212 | 752,123,449 | `c5846bde221e7785051a4a4075aa6a71cc267a1f4497168a96df05d7c50f78fe` |
| `acs/vintage` | `usa_00002` | `derived/acs/vintage/usa_00002.parquet` | 1,575,420 | 200,200,044 | `b6ffab7bd974f72b4fbc913f261779f5ce3145a915849bf92e946bb6b649240d` |

The complete selected raw delivery citations are the three manifest-covered files per profile below. A proxy retrieval timestamp or client version remains identified as a proxy in the machine citation, not a claimed original acquisition time.

| Profile | Raw citation path | Bytes | SHA-256 | Proxy fields |
| --- | --- | --- | --- | --- |
| `acs/core` | `acs/core/usa_00001/extract.json` | 6,659 | `5394b7d0cbcec71cecd849ec50d171e8c0c76abf2c56baefc8f66e7d203dc9f0` | `retrieved_at,client_version` |
| `acs/core` | `acs/core/usa_00001/usa_00001.xml` | 449,737 | `ce129099372484716d693c106f0cdee92f4d7c7372acd0fbcd68ae1e7c28ad7d` | `retrieved_at,client_version` |
| `acs/core` | `acs/core/usa_00001/usa_00001.csv.gz` | 491,119,125 | `dbb8abfb4dbf452f09a12452d79dfb039fbde651af7f9a5bd875210c2805911c` | `retrieved_at,client_version` |
| `acs/five_year` | `acs/five_year/usa_00003/extract.json` | 6,832 | `5c49e4c56bc0f404a83d61c01f8c32296e62aa643a874bdf4277119b8e1fce39` | `retrieved_at,client_version` |
| `acs/five_year` | `acs/five_year/usa_00003/usa_00003.xml` | 450,834 | `3658e08209eac0bc3432f50985bd99f91b7d6991f72e4c134be6088e4bffaa22` | `retrieved_at,client_version` |
| `acs/five_year` | `acs/five_year/usa_00003/usa_00003.csv.gz` | 901,233,906 | `defca652f18e1e04d85e057b81bcd8b435902ca7a0dd689f8ba73c311662b227` | `retrieved_at,client_version` |
| `acs/vintage` | `acs/vintage/usa_00002/extract.json` | 6,643 | `0941b8409e55ed9d2d655b633e5bcb2c8660951cbcb0b28dd65fd055a1130cb4` | `retrieved_at,client_version` |
| `acs/vintage` | `acs/vintage/usa_00002/usa_00002.xml` | 447,921 | `0276884128a98e8ffbc7c230fa0666512aae833d644bbaf41dd2a99c301b5001` | `retrieved_at,client_version` |
| `acs/vintage` | `acs/vintage/usa_00002/usa_00002.csv.gz` | 241,298,593 | `cda19c04e961aaa86e687d22a8f355905efe90a393f0c8d71de624556e71b8b8` | `retrieved_at,client_version` |

Selected upstream detached pins and reference receipts:

| Selected item | Run/identity | External SHA-256 |
| --- | --- | --- |
| Stage 4 codes | `stage4_v11_20261013_r2` | `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |
| Stage 5 geography | `stage5_geography_20261014` | `5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d` |
| Stage 7 verification | `stage7_ipums_verification_20261015_r2` | `db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc` |
| Stage 7 references | `stage7_ipums_references_20261015_r2` | `3163968dde603ba53f807976dd09b9e40d73235a98c6f36e4e02c67ec4239c9c` |
| Stage 8 v1/39 receipt (91,673 bytes) | `stage8_acs_references_20261017` | `795e98ecf5f6afb56309572ae1b5545dc16dd49f412093fb95bba366bf3e3b05` |
| Stage 8 v2/46 receipt (110,315 bytes) | `stage8_acs_references_20261018_r4` | `052135beb2e77d3cd14b4b800602be9ab36d54aaa43eaf05abffb4d5c14fd2d5` |

The v2 receipt contains 46 public originals. Each row gives the receipt identity, original manifest citation, exact byte size and public authority URL. The receipt also records edition, parser contract and proxy retrieval information.

| Reference kind | Raw citation path | Bytes | SHA-256 | Authority URL |
| --- | --- | --- | --- | --- |
| `census_ct_mcd_population2020` | `references/acs-mapping/stage8_acs_references_20261018_r4/census-ct-cousub2020-pop100.html` | 167,188 | `475f9509cedaf42fef2d7e2bc59891f732e3233b2158c6b22e71e9dacf865a3f` | https://tigerweb.geo.census.gov/tigerwebmain/Files/acs26/tigerweb_acs26_cousub_2020_tab20_ct.html |
| `census_occupation_2018` | `references/acs-mapping/stage8_acs_references_20261018_r4/census_occupation_2018.xlsx` | 160,312 | `fca2818d691c32777a4cd733a9ab77c8c5bd47adcacd7ac3aa149bebd45b5f7f` | https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2018-occupation-code-list-and-crosswalk.xlsx |
| `census_puma_population2020` | `references/acs-mapping/stage8_acs_references_20261018_r4/census-puma2020-pop100.html` | 1,949,300 | `70993afd338e51246142432723306fec63b927df15e0537cb388741d1e9d8894` | https://tigerweb.geo.census.gov/tigerwebmain/Files/acs26/tigerweb_acs26_puma_2020_tab20_us.html |
| `county_composition_2022` | `references/acs-mapping/stage8_acs_references_20261018_r4/county_composition_2022.xls` | 294,912 | `bd42f18ee36a10d91404be78106e60c613b6ec8ce53e9bc5860753af497ffadf` | https://usa.ipums.org/usa/resources/volii/county_migpuma_pwpuma_2022.xls |
| `ct_block_assignment2020` | `references/acs-mapping/stage8_acs_references_20261018_r4/BlockAssign_ST09_CT.zip` | 1,205,420 | `1125c49564224cced90844ab2345df9a2c191a0084c5029ff53ddc9c320c54ba` | https://www2.census.gov/geo/docs/maps-data/data/baf2020/BlockAssign_ST09_CT.zip |
| `ct_county_crosswalk` | `references/acs-mapping/stage8_acs_references_20261018_r4/ct_cou_to_cousub_crosswalk.txt` | 22,091 | `13ad002564e30e6dcd1df112fdaa985f2cd0cdb908f7f3017cd2723db294cff8` | https://www2.census.gov/geo/docs/reference/ct_change/ct_cou_to_cousub_crosswalk.txt |
| `ct_opm_population2020` | `references/acs-mapping/stage8_acs_references_20261018_r4/ct-opm-2020-planning-pop.xlsx` | 21,088 | `1a3ba5ff53aa5bb4b3ec68178cfa24a0ba5d1294c15ce4bb03b5e86ee660c391` | https://portal.ct.gov/opm/-/media/opm/igpp/org/cogs/2020-census-population-by-planning-region.xlsx?hash=CC2974EA5238511D82466EA6757581F8&rev=ac73c0fee0b7449fbc055f0fdde8af17 |
| `ct_tabblock2020` | `references/acs-mapping/stage8_acs_references_20261018_r4/tl_2020_09_tabblock20.zip` | 61,439,410 | `a935a5a85717389ded782debd15d7019705d7fc0777548d22cc09552208ac6b1` | https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_09_tabblock20.zip |
| `geocorr_county_totals` | `references/acs-mapping/stage8_acs_references_20261018_r4/geocorr_county_totals.csv` | 153,234 | `ad91effe25b29321a54469aa310eae470688165c85ff0b606de2018eea579e26` | https://mcdc.missouri.edu/cgi-bin/broker?state=Al01&state=Ak02&state=Az04&state=Ar05&state=Ca06&state=Co08&state=Ct09&state=De10&state=Dc11&state=Fl12&state=Ga13&state=Hi15&state=Id16&state=Il17&state=In18&state=Ia19&state=Ks20&state=Ky21&state=La22&state=Me23&state=Md24&state=Ma25&state=Mi26&state=Mn27&state=Ms28&state=Mo29&state=Mt30&state=Ne31&state=Nv32&state=Nh33&state=Nj34&state=Nm35&state=Ny36&state=Nc37&state=Nd38&state=Oh39&state=Ok40&state=Or41&state=Pa42&state=Ri44&state=Sc45&state=Sd46&state=Tn47&state=Tx48&state=Ut49&state=Vt50&state=Va51&state=Wa53&state=Wv54&state=Wi55&state=Wy56&state=Pr72&_PROGRAM=apps.geocorr2022.sas&_SERVICE=MCDC_long&_debug=0&g1_=county&g2_=state&wtvar=pop20&nozerob=1&fileout=1&filefmt=csv&lstfmt=html&title=&afacts2=on&counties=&metros=&places=&oropt=&latitude=&longitude=&distance=&kiloms=0&locname= |
| `geocorr_county_totals_request` | `references/acs-mapping/stage8_acs_references_20261018_r4/geocorr_county_totals_request.request.txt` | 806 | `ce04cdcf435c283042d63327bfb6b6d9a0b2df23dd87d004af410110c19a48a3` | https://mcdc.missouri.edu/cgi-bin/broker?state=Al01&state=Ak02&state=Az04&state=Ar05&state=Ca06&state=Co08&state=Ct09&state=De10&state=Dc11&state=Fl12&state=Ga13&state=Hi15&state=Id16&state=Il17&state=In18&state=Ia19&state=Ks20&state=Ky21&state=La22&state=Me23&state=Md24&state=Ma25&state=Mi26&state=Mn27&state=Ms28&state=Mo29&state=Mt30&state=Ne31&state=Nv32&state=Nh33&state=Nj34&state=Nm35&state=Ny36&state=Nc37&state=Nd38&state=Oh39&state=Ok40&state=Or41&state=Pa42&state=Ri44&state=Sc45&state=Sd46&state=Tn47&state=Tx48&state=Ut49&state=Vt50&state=Va51&state=Wa53&state=Wv54&state=Wi55&state=Wy56&state=Pr72&_PROGRAM=apps.geocorr2022.sas&_SERVICE=MCDC_long&_debug=0&g1_=county&g2_=state&wtvar=pop20&nozerob=1&fileout=1&filefmt=csv&lstfmt=html&title=&afacts2=on&counties=&metros=&places=&oropt=&latitude=&longitude=&distance=&kiloms=0&locname= |
| `geocorr_county_totals_response` | `references/acs-mapping/stage8_acs_references_20261018_r4/geocorr_county_totals_response.response.html` | 3,939 | `56b794b02fc188efa5e8c05ec7515dde63e0bf6b6c5c8d0277a5319c44ec7864` | https://mcdc.missouri.edu/cgi-bin/broker?state=Al01&state=Ak02&state=Az04&state=Ar05&state=Ca06&state=Co08&state=Ct09&state=De10&state=Dc11&state=Fl12&state=Ga13&state=Hi15&state=Id16&state=Il17&state=In18&state=Ia19&state=Ks20&state=Ky21&state=La22&state=Me23&state=Md24&state=Ma25&state=Mi26&state=Mn27&state=Ms28&state=Mo29&state=Mt30&state=Ne31&state=Nv32&state=Nh33&state=Nj34&state=Nm35&state=Ny36&state=Nc37&state=Nd38&state=Oh39&state=Ok40&state=Or41&state=Pa42&state=Ri44&state=Sc45&state=Sd46&state=Tn47&state=Tx48&state=Ut49&state=Vt50&state=Va51&state=Wa53&state=Wv54&state=Wi55&state=Wy56&state=Pr72&_PROGRAM=apps.geocorr2022.sas&_SERVICE=MCDC_long&_debug=0&g1_=county&g2_=state&wtvar=pop20&nozerob=1&fileout=1&filefmt=csv&lstfmt=html&title=&afacts2=on&counties=&metros=&places=&oropt=&latitude=&longitude=&distance=&kiloms=0&locname= |
| `geocorr_form` | `references/acs-mapping/stage8_acs_references_20261018_r4/geocorr_form.html` | 27,061 | `96ce8006b044529e8c23209e3d17de8921df2465dabaa3dd216c8367c0e94b40` | https://mcdc.missouri.edu/applications/geocorr2022.html |
| `geocorr_help` | `references/acs-mapping/stage8_acs_references_20261018_r4/geocorr_help.html` | 22,163 | `fb2ada9e6d64ab738ee1155b2ab600441527d66c05efcd4bd02602fe56cd88d0` | https://mcdc.missouri.edu/applications/docs/geocorr2022-help.html |
| `geocorr_intersections` | `references/acs-mapping/stage8_acs_references_20261018_r4/geocorr_intersections.csv` | 499,769 | `9d7ef74ba87b2b3bd4b22303c4c0910a4da0bca966721232c0e9b4461737e04d` | https://mcdc.missouri.edu/cgi-bin/broker?state=Al01&state=Ak02&state=Az04&state=Ar05&state=Ca06&state=Co08&state=Ct09&state=De10&state=Dc11&state=Fl12&state=Ga13&state=Hi15&state=Id16&state=Il17&state=In18&state=Ia19&state=Ks20&state=Ky21&state=La22&state=Me23&state=Md24&state=Ma25&state=Mi26&state=Mn27&state=Ms28&state=Mo29&state=Mt30&state=Ne31&state=Nv32&state=Nh33&state=Nj34&state=Nm35&state=Ny36&state=Nc37&state=Nd38&state=Oh39&state=Ok40&state=Or41&state=Pa42&state=Ri44&state=Sc45&state=Sd46&state=Tn47&state=Tx48&state=Ut49&state=Vt50&state=Va51&state=Wa53&state=Wv54&state=Wi55&state=Wy56&state=Pr72&_PROGRAM=apps.geocorr2022.sas&_SERVICE=MCDC_long&_debug=0&g1_=puma22&g2_=county&wtvar=pop20&nozerob=1&fileout=1&filefmt=csv&lstfmt=html&title=&afacts2=on&counties=&metros=&places=&oropt=&latitude=&longitude=&distance=&kiloms=0&locname= |
| `geocorr_intersections_request` | `references/acs-mapping/stage8_acs_references_20261018_r4/geocorr_intersections_request.request.txt` | 807 | `8bedf2792bef29b55490c28ee0ef242c5edccb1e3c5b4abfad9cd1f0e9cb8b11` | https://mcdc.missouri.edu/cgi-bin/broker?state=Al01&state=Ak02&state=Az04&state=Ar05&state=Ca06&state=Co08&state=Ct09&state=De10&state=Dc11&state=Fl12&state=Ga13&state=Hi15&state=Id16&state=Il17&state=In18&state=Ia19&state=Ks20&state=Ky21&state=La22&state=Me23&state=Md24&state=Ma25&state=Mi26&state=Mn27&state=Ms28&state=Mo29&state=Mt30&state=Ne31&state=Nv32&state=Nh33&state=Nj34&state=Nm35&state=Ny36&state=Nc37&state=Nd38&state=Oh39&state=Ok40&state=Or41&state=Pa42&state=Ri44&state=Sc45&state=Sd46&state=Tn47&state=Tx48&state=Ut49&state=Vt50&state=Va51&state=Wa53&state=Wv54&state=Wi55&state=Wy56&state=Pr72&_PROGRAM=apps.geocorr2022.sas&_SERVICE=MCDC_long&_debug=0&g1_=puma22&g2_=county&wtvar=pop20&nozerob=1&fileout=1&filefmt=csv&lstfmt=html&title=&afacts2=on&counties=&metros=&places=&oropt=&latitude=&longitude=&distance=&kiloms=0&locname= |
| `geocorr_intersections_response` | `references/acs-mapping/stage8_acs_references_20261018_r4/geocorr_intersections_response.response.html` | 3,946 | `a97f324837c87ed0d96991185831d28f050e333d10712c3f4b83d1f03a9b414b` | https://mcdc.missouri.edu/cgi-bin/broker?state=Al01&state=Ak02&state=Az04&state=Ar05&state=Ca06&state=Co08&state=Ct09&state=De10&state=Dc11&state=Fl12&state=Ga13&state=Hi15&state=Id16&state=Il17&state=In18&state=Ia19&state=Ks20&state=Ky21&state=La22&state=Me23&state=Md24&state=Ma25&state=Mi26&state=Mn27&state=Ms28&state=Mo29&state=Mt30&state=Ne31&state=Nv32&state=Nh33&state=Nj34&state=Nm35&state=Ny36&state=Nc37&state=Nd38&state=Oh39&state=Ok40&state=Or41&state=Pa42&state=Ri44&state=Sc45&state=Sd46&state=Tn47&state=Tx48&state=Ut49&state=Vt50&state=Va51&state=Wa53&state=Wv54&state=Wi55&state=Wy56&state=Pr72&_PROGRAM=apps.geocorr2022.sas&_SERVICE=MCDC_long&_debug=0&g1_=puma22&g2_=county&wtvar=pop20&nozerob=1&fileout=1&filefmt=csv&lstfmt=html&title=&afacts2=on&counties=&metros=&places=&oropt=&latitude=&longitude=&distance=&kiloms=0&locname= |
| `geocorr_puma_totals` | `references/acs-mapping/stage8_acs_references_20261018_r4/geocorr_puma_totals.csv` | 215,815 | `b29e5804353c71070346d80b50f208a9d417e4d6841866a5f5d1d8b6a8182fa2` | https://mcdc.missouri.edu/cgi-bin/broker?state=Al01&state=Ak02&state=Az04&state=Ar05&state=Ca06&state=Co08&state=Ct09&state=De10&state=Dc11&state=Fl12&state=Ga13&state=Hi15&state=Id16&state=Il17&state=In18&state=Ia19&state=Ks20&state=Ky21&state=La22&state=Me23&state=Md24&state=Ma25&state=Mi26&state=Mn27&state=Ms28&state=Mo29&state=Mt30&state=Ne31&state=Nv32&state=Nh33&state=Nj34&state=Nm35&state=Ny36&state=Nc37&state=Nd38&state=Oh39&state=Ok40&state=Or41&state=Pa42&state=Ri44&state=Sc45&state=Sd46&state=Tn47&state=Tx48&state=Ut49&state=Vt50&state=Va51&state=Wa53&state=Wv54&state=Wi55&state=Wy56&state=Pr72&_PROGRAM=apps.geocorr2022.sas&_SERVICE=MCDC_long&_debug=0&g1_=puma22&g2_=state&wtvar=pop20&nozerob=1&fileout=1&filefmt=csv&lstfmt=html&title=&afacts2=on&counties=&metros=&places=&oropt=&latitude=&longitude=&distance=&kiloms=0&locname= |
| `geocorr_puma_totals_request` | `references/acs-mapping/stage8_acs_references_20261018_r4/geocorr_puma_totals_request.request.txt` | 806 | `c59a902a963db701a37e847bbb75551fb3d6a86e1dac2a72e2748e99f11b67f0` | https://mcdc.missouri.edu/cgi-bin/broker?state=Al01&state=Ak02&state=Az04&state=Ar05&state=Ca06&state=Co08&state=Ct09&state=De10&state=Dc11&state=Fl12&state=Ga13&state=Hi15&state=Id16&state=Il17&state=In18&state=Ia19&state=Ks20&state=Ky21&state=La22&state=Me23&state=Md24&state=Ma25&state=Mi26&state=Mn27&state=Ms28&state=Mo29&state=Mt30&state=Ne31&state=Nv32&state=Nh33&state=Nj34&state=Nm35&state=Ny36&state=Nc37&state=Nd38&state=Oh39&state=Ok40&state=Or41&state=Pa42&state=Ri44&state=Sc45&state=Sd46&state=Tn47&state=Tx48&state=Ut49&state=Vt50&state=Va51&state=Wa53&state=Wv54&state=Wi55&state=Wy56&state=Pr72&_PROGRAM=apps.geocorr2022.sas&_SERVICE=MCDC_long&_debug=0&g1_=puma22&g2_=state&wtvar=pop20&nozerob=1&fileout=1&filefmt=csv&lstfmt=html&title=&afacts2=on&counties=&metros=&places=&oropt=&latitude=&longitude=&distance=&kiloms=0&locname= |
| `geocorr_puma_totals_response` | `references/acs-mapping/stage8_acs_references_20261018_r4/geocorr_puma_totals_response.response.html` | 3,945 | `f8bcad0fff5e576dd0d793c4c2ebfd439c719651adeaf0a5863dce3fe163c319` | https://mcdc.missouri.edu/cgi-bin/broker?state=Al01&state=Ak02&state=Az04&state=Ar05&state=Ca06&state=Co08&state=Ct09&state=De10&state=Dc11&state=Fl12&state=Ga13&state=Hi15&state=Id16&state=Il17&state=In18&state=Ia19&state=Ks20&state=Ky21&state=La22&state=Me23&state=Md24&state=Ma25&state=Mi26&state=Mn27&state=Ms28&state=Mo29&state=Mt30&state=Ne31&state=Nv32&state=Nh33&state=Nj34&state=Nm35&state=Ny36&state=Nc37&state=Nd38&state=Oh39&state=Ok40&state=Or41&state=Pa42&state=Ri44&state=Sc45&state=Sd46&state=Tn47&state=Tx48&state=Ut49&state=Vt50&state=Va51&state=Wa53&state=Wv54&state=Wi55&state=Wy56&state=Pr72&_PROGRAM=apps.geocorr2022.sas&_SERVICE=MCDC_long&_debug=0&g1_=puma22&g2_=state&wtvar=pop20&nozerob=1&fileout=1&filefmt=csv&lstfmt=html&title=&afacts2=on&counties=&metros=&places=&oropt=&latitude=&longitude=&distance=&kiloms=0&locname= |
| `industry_pairs_html` | `references/acs-mapping/stage8_acs_references_20261018_r4/industry_pairs_html.html` | 171,735 | `9826b6e0319402ea21b56ba124aafd7d4452efab8aef831db6643a44e1107b94` | https://usa.ipums.org/usa/volii/indtoindnaics.shtml |
| `industry_tokens_html` | `references/acs-mapping/stage8_acs_references_20261018_r4/industry_tokens_html.html` | 165,282 | `673f5883dc3db6402d050a2a7970b8aa2aadfee9babc6560668297142b133591` | https://usa.ipums.org/usa/volii/indnaics.shtml |
| `ipums_ind_pairs` | `references/acs-mapping/stage8_acs_references_20261018_r4/ipums_ind_pairs.xlsx` | 41,868 | `4d3f571905a9eddd905213878351c284ecf80ee48733e79cb9375181d70679a8` | https://usa.ipums.org/usa/resources/volii/ind_indnaics_crosswalk_2023.xlsx |
| `ipums_ind_tokens` | `references/acs-mapping/stage8_acs_references_20261018_r4/ipums_ind_tokens.xlsx` | 33,193 | `96c767a70c1bf707d828fb186e4711a58b9dff73dc2bba99a7038127e75048c0` | https://usa.ipums.org/usa/resources/volii/indnaics_crosswalk_2023.xlsx |
| `ipums_occ_pairs` | `references/acs-mapping/stage8_acs_references_20261018_r4/ipums_occ_pairs.xlsx` | 175,786 | `f95672c481af85302bc2f445888e2f5e493afffa6d88a5ca042b66a39cfc34f1` | https://usa.ipums.org/usa/resources/volii/occ_occsoc_crosswalk_2000_onward.xlsx |
| `msa_puma_2023_2020` | `references/acs-mapping/stage8_acs_references_20261018_r4/msa_puma_2023_2020.xlsx` | 226,680 | `80763eaf73cbda1b59818bdbf7650058eebbe18fa8a697599e645b3df235258f` | https://usa.ipums.org/usa/resources/volii/MSA2023_PUMA2020_crosswalk.xlsx |
| `occupation_pairs_html` | `references/acs-mapping/stage8_acs_references_20261018_r4/occupation_pairs_html.html` | 284,695 | `61862b9ac0e7bfc4500cc28c3664c50adfc8dc51517c7d81f0192fa37e73725c` | https://usa.ipums.org/usa/volii/occtooccsoc18.shtml |
| `puma_composition_2020` | `references/acs-mapping/stage8_acs_references_20261018_r4/puma_composition_2020.xls` | 237,568 | `022e4784cb08dcf01acfa4f680564cd26ba79e867f6643ee683577fde0b37a5d` | https://usa.ipums.org/usa/resources/volii/puma_migpuma1_pwpuma00_2020.xls |
| `pums_annual_2024` | `references/acs-mapping/stage8_acs_references_20261018_r4/pums_annual_2024.xls` | 1,526,784 | `f8c945c383322f123b5d409fd1cd1352f23ace3c0ffff5de0bc1cf414886d40d` | https://www2.census.gov/programs-surveys/acs/tech_docs/pums/code_lists/ACSPUMS2024CodeLists.xls |
| `pums_annual_guide` | `references/acs-mapping/stage8_acs_references_20261018_r4/pums_annual_guide.pdf` | 433,635 | `70d485604dfd89534eef7d491a219ab7d336f98e724732985a0a859eac5d9787` | https://www2.census.gov/programs-surveys/acs/tech_docs/pums/2024ACS_PUMS_User_Guide.pdf |
| `pums_five_year_2024` | `references/acs-mapping/stage8_acs_references_20261018_r4/pums_five_year_2024.xlsx` | 616,820 | `634fdd565249d72f09a8f75d82fe4193b20a09d898ef64a4b8e8039348d52994` | https://www2.census.gov/programs-surveys/acs/tech_docs/pums/code_lists/ACSPUMS2020_2024CodeLists.xlsx |
| `pums_five_year_guide` | `references/acs-mapping/stage8_acs_references_20261018_r4/pums_five_year_guide.pdf` | 474,159 | `77f9b74efef7cb9d3eb8ffa4dc875df9e15765432d6134ead3691a5fe8b35e1a` | https://www2.census.gov/programs-surveys/acs/tech_docs/pums/2020_2024ACS_PUMS_User_Guide.pdf |
| `pums_industry_2017` | `references/acs-mapping/stage8_acs_references_20261018_r4/pums_industry_2017.xlsx` | 44,781 | `6f569f8bfcd1955db2f75ed4ec31dc836dea7faebf24375567107b725967f4d2` | https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2018-ACS-PUMS-and-2018-SIPP-Public-Use-Industry-Code-List.xlsx |
| `pums_industry_2022` | `references/acs-mapping/stage8_acs_references_20261018_r4/pums_industry_2022.xlsx` | 46,539 | `e6f9ec64ed2519c667a032d9766b460e50cf0ac085b7dd00ae97a98dc588816d` | https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2023-ACS-PUMS-and-2024-SIPP-Public-Use-Industry-Code-List.xlsx |
| `pums_occupation_2018` | `references/acs-mapping/stage8_acs_references_20261018_r4/pums_occupation_2018.xlsx` | 73,419 | `20cc7112cf96c7a3648b579cc0b2af239bea1c9094885a0d986959888695fe0a` | https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2018-ACS-PUMS-and-2018-SIPP-Public-Use-Occupation-Code-List.xlsx |
| `soc_tokens_html` | `references/acs-mapping/stage8_acs_references_20261018_r4/soc_tokens_html.html` | 177,378 | `9e6411ca71a2800d3506ad44ab310ac3fd9d481551bd8077d7a6f74a4350ab5b` | https://usa.ipums.org/usa/volii/occsoc18.shtml |
| `tract_puma2020` | `references/acs-mapping/stage8_acs_references_20261018_r4/2020_Census_Tract_to_2020_PUMA.txt` | 1,709,076 | `5262f460b2c8dbe86b00549e916317b1791fdc595c9af72ab18f6f6a67040531` | https://www2.census.gov/geo/docs/maps-data/data/rel2020/2020_Census_Tract_to_2020_PUMA.txt |
| `usa_ind` | `references/acs-mapping/stage8_acs_references_20261018_r4/usa_ind.html` | 34,308 | `147cefcc41439a71e65f24cc6639658d776b371d1d6e7815c9a132d64df8f629` | https://usa.ipums.org/usa-action/variables/IND |
| `usa_indnaics` | `references/acs-mapping/stage8_acs_references_20261018_r4/usa_indnaics.html` | 17,708 | `a0303298f735f23f5fd7a7121e2a3195031514418baa4db4401ac0eb83356076` | https://usa.ipums.org/usa-action/variables/INDNAICS |
| `usa_migplac1` | `references/acs-mapping/stage8_acs_references_20261018_r4/usa_migplac1.html` | 58,299 | `3f8433e2e44807402493690c6f6f50aa8afd3e0ec84338892556baf07d789bab` | https://usa.ipums.org/usa-action/variables/MIGPLAC1 |
| `usa_migpuma1` | `references/acs-mapping/stage8_acs_references_20261018_r4/usa_migpuma1.html` | 36,902 | `de71f01455d2e25c4fdfa71dd16eebb117354b0f25c3110374edc152a7a712ef` | https://usa.ipums.org/usa-action/variables/MIGPUMA1 |
| `usa_multyear` | `references/acs-mapping/stage8_acs_references_20261018_r4/usa_multyear.html` | 19,040 | `c5ca34d092f6eea9c893f44275a9eaac3aeb608e1d5c40e244bf128432ced661` | https://usa.ipums.org/usa-action/variables/MULTYEAR |
| `usa_occ` | `references/acs-mapping/stage8_acs_references_20261018_r4/usa_occ.html` | 38,814 | `01d2590bfddea084efda3d774fbd4bc00e6584c2399877f165afb8de326a8eca` | https://usa.ipums.org/usa-action/variables/OCC |
| `usa_occsoc` | `references/acs-mapping/stage8_acs_references_20261018_r4/usa_occsoc.html` | 17,833 | `594e43c53c97ffee9fa089925baaa1777bdc6e942ba78d2b4cb594f5ca3b8a9e` | https://usa.ipums.org/usa-action/variables/OCCSOC |
| `usa_puma` | `references/acs-mapping/stage8_acs_references_20261018_r4/usa_puma.html` | 22,757 | `74de7ba7bc0c85e08d783ab1e90aa8f9bf9df9ba0cfc12fb0a91d4a4bf775739` | https://usa.ipums.org/usa-action/variables/PUMA |
| `usa_pwpuma00` | `references/acs-mapping/stage8_acs_references_20261018_r4/usa_pwpuma00.html` | 24,962 | `fba5d8ae2504ec8bda09a80644cae1ab92ed9e1bf99d1760b85ecce27f28bfcb` | https://usa.ipums.org/usa-action/variables/PWPUMA00 |
| `usa_pwstate2` | `references/acs-mapping/stage8_acs_references_20261018_r4/usa_pwstate2.html` | 30,382 | `19ed2ea26cd166b8aaa5c790183c259cee4a1d0e1066fdacd4273c677a541b80` | https://usa.ipums.org/usa-action/variables/PWSTATE2 |

The three immutable public request records used by the selected receipt are:

| Request kind | Filename | Bytes | SHA-256 |
| --- | --- | --- | --- |
| `geocorr_county_totals_request` | `geocorr_county_totals_request.request.txt` | 806 | `ce04cdcf435c283042d63327bfb6b6d9a0b2df23dd87d004af410110c19a48a3` |
| `geocorr_intersections_request` | `geocorr_intersections_request.request.txt` | 807 | `8bedf2792bef29b55490c28ee0ef242c5edccb1e3c5b4abfad9cd1f0e9cb8b11` |
| `geocorr_puma_totals_request` | `geocorr_puma_totals_request.request.txt` | 806 | `c59a902a963db701a37e847bbb75551fb3d6a86e1dac2a72e2748e99f11b67f0` |

### Executing and independent software identities

Execution used `CPython` `3.14.0` at clean source HEAD `1542f8d8f1db2e55f28b9cfec4b1306739589ce8`; `uv.lock` SHA-256 is `f57c3280a7c8286711bf6804ca4c02f0a19619c9db52f33941b9c5b996cba8e5`. The selected Stage 5 historical/current CLI exception remains exactly D5; no other compatibility relaxation is inferred. The full 54-member executing inventory follows.

| Executing member | Bytes | SHA-256 |
| --- | --- | --- |
| `pyproject.toml` | 2,096 | `0efd4c90ae3efb90d84e25fa8cec8242d870a702109e0abb1bea843753521594` |
| `src/embedding_data/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `src/embedding_data/acs_area_mapping.py` | 18,833 | `238b21069adf9c03815d6c0511ba57b9727c665003ebf4a0df1732d8b2e2cee3` |
| `src/embedding_data/acs_area_references.py` | 36,470 | `92cf024a1b80c974c75beb024fc42f5ed90322c84149e4ca565a26fbe1dff60d` |
| `src/embedding_data/acs_benchmark_extract.py` | 5,700 | `4870380af801b6ece842a8eb6368070143bb4ac2d8d3055adf3fe3f9c6b70002` |
| `src/embedding_data/acs_code_mapping.py` | 11,818 | `12e70dd4aaf600c9520dbb4d0e53ae1333bcfea865aa14a9ac975be39dfa9924` |
| `src/embedding_data/acs_code_references.py` | 52,552 | `6f0403661478a93c8e924e4350f3673434da187d49498d9e7e1ab1fb96daa1d1` |
| `src/embedding_data/acs_ct_population.py` | 23,837 | `46323c97422f61570b0a56c45f0288e95e9abaec02902a884a1bc10b84f5b6fa` |
| `src/embedding_data/acs_geography_factors.py` | 14,616 | `22842b7c3abd75e6c1db6ce40e71d7a597d6efa66c06e68aa9e048803bbcd671` |
| `src/embedding_data/acs_mapping.py` | 3,818 | `0c034d45e7ba8441c369dc3a1b91e89d972d62e5f45a136fd7ead97f4f80263b` |
| `src/embedding_data/acs_mapping_bundle.py` | 12,013 | `71dea2644fb5d84091ad3d42b05ce5fca6655a7373b1270c392f9c32b67b3e0f` |
| `src/embedding_data/acs_mapping_companions.py` | 16,246 | `354878f20022e2b5c4a8b81926beaabe2429545b1711414fd9ddb1c6d96c5585` |
| `src/embedding_data/acs_mapping_contract.py` | 12,442 | `dd22e979c949938dddb0dedc273e0405f6034a70aac5653e28f68c90f046967a` |
| `src/embedding_data/acs_mapping_inputs.py` | 12,721 | `2a1092664fef122de03c978976d5cdd13d7e912bf78a95a37d28a54b716eb9bd` |
| `src/embedding_data/acs_mapping_io.py` | 2,341 | `e287256446f46dd072018198102969c8faeeb9fffd594e9c1e4bbb339f634e6d` |
| `src/embedding_data/acs_mapping_references.py` | 55,812 | `6c53700133ccf1cf469a621d58240d2cd6a10602430881d5dc61edf2196449e6` |
| `src/embedding_data/classification_tables.py` | 7,517 | `856d92efe38a98bd7f047f4b96e40368e1bda6da3c052ccf2fde952b4c9803d3` |
| `src/embedding_data/cli.py` | 1,228 | `32a86b3d07bf112fabc1edb01fd10a966e840c185642e55d00f35dfd435220b3` |
| `src/embedding_data/code_build.py` | 14,197 | `0cfc516da2ce05412306f2c8046b37bb2b8b1177501616839a8196c5014a99c2` |
| `src/embedding_data/code_references.py` | 10,716 | `c6fd782cc408ce3db9053296ccab0652878bfa88a1f8cebbac46772ac8b5d728` |
| `src/embedding_data/cps_benchmark_extract.py` | 8,300 | `94b0eeecc3e54212c3050563467f6d559901863914a74037fa3f67bac550537d` |
| `src/embedding_data/filing_rules.py` | 17,127 | `23d9fad2ed790c6c8fe382b71dfb31ded49f27736d3a84e4f707d184e89fbc9a` |
| `src/embedding_data/geography_build.py` | 7,523 | `6cbb5d388a25977c06413372684a284166930378161d97cbeab5ead95b597afd` |
| `src/embedding_data/geography_cli.py` | 1,522 | `4fe77ebf2dc2c1ab3bbd5c0415e0a72ce4025ba966a19f578dc5cd37a045c7ff` |
| `src/embedding_data/geography_hud.py` | 3,591 | `99124834430a7d8acc4443c42810f16cafa9ea1a4c0e1bdb7b5141f2fa23bf94` |
| `src/embedding_data/geography_parsers.py` | 7,368 | `d38cd177edda764f37e48d2e4dc0f0aba6a098cd068bda9fd9f7985894fd4d36` |
| `src/embedding_data/geography_references.py` | 7,951 | `7d189a5596fa216f5e89b254278c8dadb1b126914c210ad40426be0d6aa67fb9` |
| `src/embedding_data/geography_tables.py` | 9,318 | `4db3084f3dc50c28afe8af1d543e1bb368a2b88337848dd75e7af23e3d6715c6` |
| `src/embedding_data/ipums_acceptance.py` | 20,200 | `a9de214cfd05354ccb697cb66073415ab8ba63af0c4f410caf8f72f60114d46c` |
| `src/embedding_data/ipums_census_access.py` | 9,861 | `c29c862b4876e315b4a0d47c5730b08dfaaf79c53f5965d9fcb6d14a13eb698a` |
| `src/embedding_data/ipums_cli.py` | 3,234 | `11c22a71a572416fed2cebfebd446856e7585181b3decfc9b4eb08b9f8aee8fe` |
| `src/embedding_data/ipums_conversion.py` | 6,671 | `32ee0121b525e59603bdf89874a2f8b3cbada46f6b31427d58f18e4a0129f4b9` |
| `src/embedding_data/ipums_ddi.py` | 5,582 | `b445f7f7303f527f95d7edca3851ea92b5e1fb8335b5d9e1d2f95f9cf0a9ab26` |
| `src/embedding_data/ipums_delivery.py` | 4,290 | `0d2ab441967ac53df0af4fdbe43ce4b25014bac64f839d7275fb9b6e4ae6d395` |
| `src/embedding_data/ipums_industry.py` | 4,797 | `644f7d90702b8cee890df6ba8c34ae6f08bfb7d4fd6ef68856942c7a91705e10` |
| `src/embedding_data/ipums_parity.py` | 3,406 | `9c963b103635bd2911206ea49654bcfa8e8872f69e0ed766bec3c99589489a2a` |
| `src/embedding_data/ipums_references.py` | 34,488 | `5cb8d274a06fff9f73ce7fa5f3141b696bb05c5fcae22371a2282ecbbec8b8c8` |
| `src/embedding_data/ipums_totals.py` | 13,341 | `2c4ee4081015f49199a2e9c69bad442e80bf55e26965040063219f6dec80c523` |
| `src/embedding_data/ipums_verification_run.py` | 22,429 | `3034bb3b5fb1bd6ed7f40da2e5e59a22ef798e36b483bcd90bc911e544df2e2b` |
| `src/embedding_data/ipums_weights.py` | 10,062 | `1932d6254c294419cb94f94659b33fbd872dc0b15a1e0b520d3fc34b074b4767` |
| `src/embedding_data/ita_catalog.py` | 4,884 | `325d4e132719f56a2e94049323ecd1763281df69ee60eae356259fea9b951f58` |
| `src/embedding_data/ita_naics_mapping.py` | 5,105 | `bde4a9ddde83b05a9b056631c53601aaeb0f539cae6fd99b49f2edc9cc9b897c` |
| `src/embedding_data/ita_references.py` | 7,767 | `2fbb723fdec6a712b76e82a687de76cc631b023e6ff8520419d9c920588b452c` |
| `src/embedding_data/ita_summary.py` | 18,997 | `082ccabe0ab00d7b03fcfbaea5e2622fced83b4cf1cdef2d51b9a5f5d05f6229` |
| `src/embedding_data/manifest.py` | 5,009 | `b734f4a81923838f21eed010350ddcc8c5b1a632d5defb6d115925273ab36b80` |
| `src/embedding_data/naics_relationships.py` | 4,834 | `e674cb5370d1b8582735e83fb035bc4efbd0ab5b0f0dfc5cc2a82bba1aa25254` |
| `src/embedding_data/osha_benchmark_download.py` | 13,503 | `2911f95a6d851e9dfa00a178df3942446dcf9670bc9799f7f82c9bac5beed2f8` |
| `src/embedding_data/osha_encoding.py` | 804 | `4e3efe187e25e1d2dd894207b9d7bdb719ae5543c740c208df401174e7ee6307` |
| `src/embedding_data/paths.py` | 868 | `9adc720b3dfe07a5801e41f5f1b7cbe1d1a9d2620b4c983ef5babc63d811a014` |
| `src/embedding_data/target_inputs.py` | 12,591 | `d999e1c8ec7390b2b0450ddd98ea296e368131cc60e072583b880096152898d8` |
| `src/embedding_data/target_io.py` | 4,223 | `19b1bf2818aa83bf27fd5b5c88a1157c3d1abab3918877935fe90218cc161aae` |
| `tests/test_acs_ct_population.py` | 23,521 | `da651e263fb749f40b085cc635789dc736e1a3de201438459b79b72d8b2795b8` |
| `tests/test_acs_source_rules.py` | 7,003 | `b3af3b40b6d54fee7d82837179e48575864a64e62b48a08b2a0a59b1afc28d68` |
| `uv.lock` | 76,642 | `f57c3280a7c8286711bf6804ca4c02f0a19619c9db52f33941b9c5b996cba8e5` |

The seven independent reconciler/test/helper members were separately authenticated in C1:

| Independent member | Bytes | SHA-256 |
| --- | --- | --- |
| `pyproject.toml` | 2,096 | `0efd4c90ae3efb90d84e25fa8cec8242d870a702109e0abb1bea843753521594` |
| `scripts/reconcile_stage8.py` | 138,848 | `8a07314aeac4276d74b3e005ea845aa0d60346c7a39e7de71e25db3afc323ac4` |
| `tests/acs_mapping_fixtures.py` | 52,178 | `074e0d95c8a1686266ddd58a1aec17ae5d028629f67a0bebd374233e7a417b99` |
| `tests/test_acs_ct_population.py` | 23,521 | `da651e263fb749f40b085cc635789dc736e1a3de201438459b79b72d8b2795b8` |
| `tests/test_acs_source_rules.py` | 7,003 | `b3af3b40b6d54fee7d82837179e48575864a64e62b48a08b2a0a59b1afc28d68` |
| `tests/test_stage8_reconciliation.py` | 54,364 | `b5e068f111aa67e8b489e4d59fbc975945bf7a770b5a370a589e77bef9168405` |
| `uv.lock` | 76,642 | `f57c3280a7c8286711bf6804ca4c02f0a19619c9db52f33941b9c5b996cba8e5` |

The selected installed dependency versions (63 distributions) were frozen in both executing and independent identities:

| Distribution | Version |
| --- | --- |
| `annotated-doc` | `0.0.5` |
| `anyio` | `4.15.1` |
| `behave` | `1.3.3` |
| `certifi` | `2026.7.22` |
| `cfgv` | `3.5.0` |
| `chardet` | `7.6.0` |
| `charset-normalizer` | `3.5.2` |
| `click` | `8.5.0` |
| `colorama` | `0.4.6` |
| `coverage` | `7.16.2` |
| `cucumber-expressions` | `20.1.0` |
| `cucumber-tag-expressions` | `11.0.1` |
| `distlib` | `0.4.3` |
| `embedding-data` | `0.1.0` |
| `fastexcel` | `0.21.0` |
| `filelock` | `4.1.1` |
| `h11` | `0.16.0` |
| `h2` | `4.4.1` |
| `hpack` | `4.2.0` |
| `httpcore` | `1.0.9` |
| `httpx` | `0.28.1` |
| `hyperframe` | `6.1.0` |
| `hypothesis` | `6.169.0` |
| `identify` | `2.6.20` |
| `idna` | `3.20` |
| `importlib-metadata` | `4.13.0` |
| `iniconfig` | `2.3.1` |
| `ipumspy` | `0.8.2` |
| `markdown-it-py` | `4.2.0` |
| `mdurl` | `0.1.2` |
| `nodeenv` | `1.11.0` |
| `numpy` | `2.5.4` |
| `packaging` | `26.3` |
| `pandas` | `2.3.3` |
| `parse` | `1.22.3` |
| `parse_type` | `0.6.6` |
| `platformdirs` | `4.13.0` |
| `pluggy` | `1.6.0` |
| `polars` | `2.0.0` |
| `polars-runtime-32` | `2.0.0` |
| `pre_commit` | `4.6.2` |
| `pyarrow` | `23.0.1` |
| `Pygments` | `2.21.0` |
| `pytest` | `9.1.1` |
| `pytest-cov` | `7.1.0` |
| `python-dateutil` | `2.9.0.post0` |
| `python-discovery` | `1.6.2` |
| `python-dotenv` | `1.2.4` |
| `pytz` | `2026.5` |
| `PyYAML` | `6.0.3` |
| `requests` | `2.34.2` |
| `rich` | `15.0.0` |
| `ruff` | `0.17.0` |
| `shellingham` | `1.5.4` |
| `six` | `1.17.0` |
| `sortedcontainers` | `2.4.0` |
| `typer` | `0.27.3` |
| `typing_extensions` | `4.16.0` |
| `tzdata` | `2026.5` |
| `urllib3` | `2.8.0` |
| `virtualenv` | `21.14.7` |
| `yapf` | `0.43.0` |
| `zipp` | `4.1.1` |

### Full-data aggregate partitions

The C1 first/replay aggregate JSON is byte-identical (794,347 bytes; SHA-256 `7a94523b1f1985ff8d18bbb8418e3bfb5d889d3ade65fb0de98da0cff526cd83`). The following partitions are source-backed counts; zero unparseable codes in every profile. Candidate lengths are unweighted possibilities, never classification probabilities.

| Profile | System | Mapping status: count | Aggregation reason status: count | Candidate length: count |
| --- | --- | --- | --- | --- |
| `acs/core` | industry | mapped:3,206,859 | not_applicable:36,318, unknown:3,170,541 | 1:673,142, 2:553,275, 3:162,880, 4:467,737, 5:219,587, 6:188,083, 7:272,355, 8:132,631, 9:89,746, 10:44,318, 11:27,758, 12:8,623, 13:45,339, 14:35,121, 19:11,910, 30:26,531, 31:206,805, 35:17,206, 43:1,242, 54:285, 57:10,173, 69:2,134, 346:9,978 |
| `acs/core` | occupation | documented_special:5,204, mapped:3,201,655 | documented:461,068, not_applicable:2,094,688, unknown:651,103 | 0:5,204, 1:2,089,484, 2:461,149, 3:211,375, 4:250,018, 5:64,906, 6:53,578, 7:1,950, 8:17,551, 13:21,118, 37:30,526 |
| `acs/five_year` | industry | mapped:7,456,212 | not_applicable:84,834, unknown:7,371,378 | 1:1,579,565, 2:1,289,121, 3:379,237, 4:1,080,458, 5:510,251, 6:441,249, 7:623,720, 8:309,692, 9:207,309, 10:99,773, 11:67,088, 12:20,015, 13:104,025, 14:83,071, 19:30,371, 30:60,652, 31:479,090, 35:39,292, 43:2,203, 54:536, 57:22,970, 69:4,629, 346:21,895 |
| `acs/five_year` | occupation | documented_special:14,799, mapped:7,441,413 | documented:1,063,012, not_applicable:4,865,169, unknown:1,528,031 | 0:14,799, 1:4,850,370, 2:1,081,180, 3:493,525, 4:570,625, 5:152,329, 6:126,281, 7:4,781, 8:37,913, 13:49,024, 37:75,385 |
| `acs/vintage` | industry | mapped:1,575,420 | not_applicable:32,709, unknown:1,542,711 | 1:334,473, 2:243,106, 3:96,969, 4:229,872, 5:100,607, 6:98,780, 7:132,759, 8:68,105, 9:47,051, 10:16,557, 11:13,998, 12:4,301, 13:22,039, 14:17,305, 19:6,228, 30:12,875, 31:101,322, 35:8,509, 39:932, 42:8,826, 43:390, 54:117, 57:4,653, 69:996, 346:4,650 |
| `acs/vintage` | occupation | documented_special:3,405, mapped:1,572,015 | documented:223,314, not_applicable:1,028,509, unknown:323,597 | 0:3,405, 1:1,025,104, 2:226,830, 3:105,357, 4:119,897, 5:33,020, 6:26,169, 7:1,064, 8:8,550, 13:10,280, 37:15,744 |

The documented-reason cut has **lookup-key grain**, distinct from the source-row status counts above. The first bundle's sealed `acs_code_lookup.parquet` is **1,062 rows / 116,423 bytes**, SHA-256 `4b09b6963c3a2d9cc4c062fc62860bb6be0468f510ef2d3b7fccf445d53e397d`, under external `outputs.json` pin `1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4`. Its `aggregation_reasons` list and `aggregation_reason_status` yield this complete partition; `unknown` lists remain empty and are **not** assigned a motive.

| System | Reason status | Documented reason | Lookup keys |
| --- | --- | --- | ---: |
| NAICS | `not_applicable` | none | 15 |
| NAICS | `unknown` | unknown | 518 |
| SOC | `documented` | `category_design` | 30 |
| SOC | `documented` | `disclosure` | 32 |
| SOC | `not_applicable` | none | 378 |
| SOC | `unknown` | unknown | 89 |

Every lookup key carries exact `reference_locators` in that sealed table. For the documented SOC rows, the original `soc_tokens_html` aggregate-code explanation is SHA-256 `9e6411ca71a2800d3506ad44ab310ac3fd9d481551bd8077d7a6f74a4350ab5b`; the original `pums_occupation_2018` workbook is SHA-256 `20cc7112cf96c7a3648b579cc0b2af239bea1c9094885a0d986959888695fe0a`. A `category_design` row cites `soc_tokens_html:aggregate-code-explanation` and a precise workbook row such as `pums_occupation_2018:ACS!A:C:row=85:source_token_raw='13-20XX'`; a `disclosure` row cites `pums_occupation_2018:ACS!A884:highlighting-confidentiality` and its precise source-token row. The complete locators, not these examples alone, are retained per key in the pinned lookup. The source-row status counts above remain a separate measurement and do not imply that all documented rows share one reason.

Source Q evidence and allocation statuses, preserving literal null and unavailable cases:

| Profile | Q field | Source dtype | Source value: count | Annotation status: count |
| --- | --- | --- | --- | --- |
| `acs/core` | `QIND` | `Int64` | 0:2,642,199, 4:564,660 | allocated:564,660, not_allocated_or_niu:2,642,199 |
| `acs/core` | `QMIGRAT1` | `String` | None:1,598,838, '0':1,448,662, '4':159,359 | allocated:159,359, not_allocated_or_niu:1,448,662, unavailable:1,598,838 |
| `acs/core` | `QOCC` | `Int64` | 0:2,614,791, 4:592,068 | allocated:592,068, not_allocated_or_niu:2,614,791 |
| `acs/five_year` | `QIND` | `Int64` | 0:6,191,858, 4:1,264,354 | allocated:1,264,354, not_allocated_or_niu:6,191,858 |
| `acs/five_year` | `QMIGRAT1` | `Int64` | 0:6,744,653, 4:711,559 | allocated:711,559, not_allocated_or_niu:6,744,653 |
| `acs/five_year` | `QOCC` | `Int64` | 0:6,121,548, 4:1,334,664 | allocated:1,334,664, not_allocated_or_niu:6,121,548 |
| `acs/vintage` | `QIND` | `Int64` | 0:1,305,716, 4:269,704 | allocated:269,704, not_allocated_or_niu:1,305,716 |
| `acs/vintage` | `QMIGRAT1` | `None` | absent | unavailable:1,575,420 |
| `acs/vintage` | `QOCC` | `Int64` | 0:1,288,969, 4:286,451 | allocated:286,451, not_allocated_or_niu:1,288,969 |

Disjoint geographic role statuses:

| Profile | Role | Status: count |
| --- | --- | --- |
| `acs/core` | migration | applicable:351,232, foreign:16,848, niu_or_unidentifiable:2,838,489, territory:290 |
| `acs/core` | residence | applicable:3,206,859 |
| `acs/core` | workplace | applicable:3,144,393, foreign:1,395, niu_or_unidentifiable:61,031, territory:40 |
| `acs/five_year` | migration | applicable:866,935, documented_unavailable:2,520, foreign:34,083, niu_or_unidentifiable:6,551,913, territory:761 |
| `acs/five_year` | residence | applicable:7,456,212 |
| `acs/five_year` | workplace | applicable:7,300,147, foreign:3,052, niu_or_unidentifiable:152,951, territory:62 |
| `acs/vintage` | migration | applicable:190,129, foreign:7,738, niu_or_unidentifiable:1,377,386, territory:167 |
| `acs/vintage` | residence | applicable:1,575,420 |
| `acs/vintage` | workplace | applicable:1,542,648, foreign:702, niu_or_unidentifiable:32,060, territory:10 |

The full component-level role/status partition comes from the sealed external control `/Users/lowell/Projects/embedding-data/data/derived/acs/mapping-controls/stage8_acceptance_20261018_r7/r7-prebuild-role-status-rows.json` (14,535 bytes, SHA-256 `c1beea2b56650b3734d7b2abd98f069e3c5970d8e3eaf5ec0ca47ad96101407d`). Its **73 unique aggregate rows** cover every profile/sample/release/component/role/status combination. For each of the eight profile/sample/component sets, each role's disjoint status rows sum to that component's source-row count; across three roles the table sums to **36,715,473** role observations, three times the **12,238,491** selected source rows. The nine profile/role totals above are summaries of this complete partition. These are aggregate counts, not person rows or identifiers.

| Profile | Sample | Release year | Component year | Role | Area status | Rows |
| --- | --- | ---: | ---: | --- | --- | ---: |
| `acs/core` | `us2023a` | 2023 | 2023 | `migration` | `applicable` | 178,595 |
| `acs/core` | `us2023a` | 2023 | 2023 | `migration` | `foreign` | 8,599 |
| `acs/core` | `us2023a` | 2023 | 2023 | `migration` | `niu_or_unidentifiable` | 1,411,487 |
| `acs/core` | `us2023a` | 2023 | 2023 | `migration` | `territory` | 157 |
| `acs/core` | `us2023a` | 2023 | 2023 | `residence` | `applicable` | 1,598,838 |
| `acs/core` | `us2023a` | 2023 | 2023 | `workplace` | `applicable` | 1,567,307 |
| `acs/core` | `us2023a` | 2023 | 2023 | `workplace` | `foreign` | 725 |
| `acs/core` | `us2023a` | 2023 | 2023 | `workplace` | `niu_or_unidentifiable` | 30,777 |
| `acs/core` | `us2023a` | 2023 | 2023 | `workplace` | `territory` | 29 |
| `acs/core` | `us2024a` | 2024 | 2024 | `migration` | `applicable` | 172,637 |
| `acs/core` | `us2024a` | 2024 | 2024 | `migration` | `foreign` | 8,249 |
| `acs/core` | `us2024a` | 2024 | 2024 | `migration` | `niu_or_unidentifiable` | 1,427,002 |
| `acs/core` | `us2024a` | 2024 | 2024 | `migration` | `territory` | 133 |
| `acs/core` | `us2024a` | 2024 | 2024 | `residence` | `applicable` | 1,608,021 |
| `acs/core` | `us2024a` | 2024 | 2024 | `workplace` | `applicable` | 1,577,086 |
| `acs/core` | `us2024a` | 2024 | 2024 | `workplace` | `foreign` | 670 |
| `acs/core` | `us2024a` | 2024 | 2024 | `workplace` | `niu_or_unidentifiable` | 30,254 |
| `acs/core` | `us2024a` | 2024 | 2024 | `workplace` | `territory` | 11 |
| `acs/five_year` | `us2024c` | 2024 | 2020 | `migration` | `applicable` | 145,217 |
| `acs/five_year` | `us2024c` | 2024 | 2020 | `migration` | `foreign` | 4,169 |
| `acs/five_year` | `us2024c` | 2024 | 2020 | `migration` | `niu_or_unidentifiable` | 1,044,520 |
| `acs/five_year` | `us2024c` | 2024 | 2020 | `migration` | `territory` | 133 |
| `acs/five_year` | `us2024c` | 2024 | 2020 | `residence` | `applicable` | 1,194,039 |
| `acs/five_year` | `us2024c` | 2024 | 2020 | `workplace` | `applicable` | 1,164,838 |
| `acs/five_year` | `us2024c` | 2024 | 2020 | `workplace` | `foreign` | 411 |
| `acs/five_year` | `us2024c` | 2024 | 2020 | `workplace` | `niu_or_unidentifiable` | 28,787 |
| `acs/five_year` | `us2024c` | 2024 | 2020 | `workplace` | `territory` | 3 |
| `acs/five_year` | `us2024c` | 2024 | 2021 | `migration` | `applicable` | 182,871 |
| `acs/five_year` | `us2024c` | 2024 | 2021 | `migration` | `foreign` | 5,328 |
| `acs/five_year` | `us2024c` | 2024 | 2021 | `migration` | `niu_or_unidentifiable` | 1,291,518 |
| `acs/five_year` | `us2024c` | 2024 | 2021 | `migration` | `territory` | 177 |
| `acs/five_year` | `us2024c` | 2024 | 2021 | `residence` | `applicable` | 1,479,894 |
| `acs/five_year` | `us2024c` | 2024 | 2021 | `workplace` | `applicable` | 1,448,268 |
| `acs/five_year` | `us2024c` | 2024 | 2021 | `workplace` | `foreign` | 544 |
| `acs/five_year` | `us2024c` | 2024 | 2021 | `workplace` | `niu_or_unidentifiable` | 31,073 |
| `acs/five_year` | `us2024c` | 2024 | 2021 | `workplace` | `territory` | 9 |
| `acs/five_year` | `us2024c` | 2024 | 2022 | `migration` | `applicable` | 187,615 |
| `acs/five_year` | `us2024c` | 2024 | 2022 | `migration` | `documented_unavailable` | 2,520 |
| `acs/five_year` | `us2024c` | 2024 | 2022 | `migration` | `foreign` | 7,738 |
| `acs/five_year` | `us2024c` | 2024 | 2022 | `migration` | `niu_or_unidentifiable` | 1,377,386 |
| `acs/five_year` | `us2024c` | 2024 | 2022 | `migration` | `territory` | 161 |
| `acs/five_year` | `us2024c` | 2024 | 2022 | `residence` | `applicable` | 1,575,420 |
| `acs/five_year` | `us2024c` | 2024 | 2022 | `workplace` | `applicable` | 1,542,648 |
| `acs/five_year` | `us2024c` | 2024 | 2022 | `workplace` | `foreign` | 702 |
| `acs/five_year` | `us2024c` | 2024 | 2022 | `workplace` | `niu_or_unidentifiable` | 32,060 |
| `acs/five_year` | `us2024c` | 2024 | 2022 | `workplace` | `territory` | 10 |
| `acs/five_year` | `us2024c` | 2024 | 2023 | `migration` | `applicable` | 178,595 |
| `acs/five_year` | `us2024c` | 2024 | 2023 | `migration` | `foreign` | 8,599 |
| `acs/five_year` | `us2024c` | 2024 | 2023 | `migration` | `niu_or_unidentifiable` | 1,411,487 |
| `acs/five_year` | `us2024c` | 2024 | 2023 | `migration` | `territory` | 157 |
| `acs/five_year` | `us2024c` | 2024 | 2023 | `residence` | `applicable` | 1,598,838 |
| `acs/five_year` | `us2024c` | 2024 | 2023 | `workplace` | `applicable` | 1,567,307 |
| `acs/five_year` | `us2024c` | 2024 | 2023 | `workplace` | `foreign` | 725 |
| `acs/five_year` | `us2024c` | 2024 | 2023 | `workplace` | `niu_or_unidentifiable` | 30,777 |
| `acs/five_year` | `us2024c` | 2024 | 2023 | `workplace` | `territory` | 29 |
| `acs/five_year` | `us2024c` | 2024 | 2024 | `migration` | `applicable` | 172,637 |
| `acs/five_year` | `us2024c` | 2024 | 2024 | `migration` | `foreign` | 8,249 |
| `acs/five_year` | `us2024c` | 2024 | 2024 | `migration` | `niu_or_unidentifiable` | 1,427,002 |
| `acs/five_year` | `us2024c` | 2024 | 2024 | `migration` | `territory` | 133 |
| `acs/five_year` | `us2024c` | 2024 | 2024 | `residence` | `applicable` | 1,608,021 |
| `acs/five_year` | `us2024c` | 2024 | 2024 | `workplace` | `applicable` | 1,577,086 |
| `acs/five_year` | `us2024c` | 2024 | 2024 | `workplace` | `foreign` | 670 |
| `acs/five_year` | `us2024c` | 2024 | 2024 | `workplace` | `niu_or_unidentifiable` | 30,254 |
| `acs/five_year` | `us2024c` | 2024 | 2024 | `workplace` | `territory` | 11 |
| `acs/vintage` | `us2022a` | 2022 | 2022 | `migration` | `applicable` | 190,129 |
| `acs/vintage` | `us2022a` | 2022 | 2022 | `migration` | `foreign` | 7,738 |
| `acs/vintage` | `us2022a` | 2022 | 2022 | `migration` | `niu_or_unidentifiable` | 1,377,386 |
| `acs/vintage` | `us2022a` | 2022 | 2022 | `migration` | `territory` | 167 |
| `acs/vintage` | `us2022a` | 2022 | 2022 | `residence` | `applicable` | 1,575,420 |
| `acs/vintage` | `us2022a` | 2022 | 2022 | `workplace` | `applicable` | 1,542,648 |
| `acs/vintage` | `us2022a` | 2022 | 2022 | `workplace` | `foreign` | 702 |
| `acs/vintage` | `us2022a` | 2022 | 2022 | `workplace` | `niu_or_unidentifiable` | 32,060 |
| `acs/vintage` | `us2022a` | 2022 | 2022 | `workplace` | `territory` | 10 |

Role allocation and split flag partitions (each line is one measured combination; `null` remains distinct from false):

| Profile | Role | Status | Source recoded | Geographic allocation | Fractional split | Rows |
| --- | --- | --- | --- | --- | --- | --- |
| `acs/core` | migration | `applicable` | `False` | `True` | `False` | 239,138 |
| `acs/core` | migration | `applicable` | `False` | `True` | `True` | 112,094 |
| `acs/core` | migration | `foreign` | `False` | `False` | `False` | 16,848 |
| `acs/core` | migration | `niu_or_unidentifiable` | `False` | `False` | `False` | 2,838,489 |
| `acs/core` | migration | `territory` | `False` | `False` | `False` | 290 |
| `acs/core` | residence | `applicable` | `False` | `True` | `False` | 2,296,789 |
| `acs/core` | residence | `applicable` | `False` | `True` | `True` | 910,070 |
| `acs/core` | workplace | `applicable` | `False` | `True` | `False` | 2,089,354 |
| `acs/core` | workplace | `applicable` | `False` | `True` | `True` | 1,055,039 |
| `acs/core` | workplace | `foreign` | `False` | `False` | `False` | 1,395 |
| `acs/core` | workplace | `niu_or_unidentifiable` | `False` | `False` | `False` | 61,031 |
| `acs/core` | workplace | `territory` | `False` | `False` | `False` | 40 |
| `acs/five_year` | migration | `applicable` | `False` | `True` | `False` | 368,661 |
| `acs/five_year` | migration | `applicable` | `False` | `True` | `True` | 170,186 |
| `acs/five_year` | migration | `applicable` | `True` | `True` | `False` | 224,618 |
| `acs/five_year` | migration | `applicable` | `True` | `True` | `True` | 103,470 |
| `acs/five_year` | migration | `documented_unavailable` | `False` | `False` | `False` | 2,520 |
| `acs/five_year` | migration | `foreign` | `False` | `False` | `False` | 34,083 |
| `acs/five_year` | migration | `niu_or_unidentifiable` | `False` | `False` | `False` | 6,551,913 |
| `acs/five_year` | migration | `territory` | `False` | `False` | `False` | 761 |
| `acs/five_year` | residence | `applicable` | `False` | `True` | `False` | 3,426,698 |
| `acs/five_year` | residence | `applicable` | `False` | `True` | `True` | 1,355,581 |
| `acs/five_year` | residence | `applicable` | `True` | `True` | `False` | 1,915,990 |
| `acs/five_year` | residence | `applicable` | `True` | `True` | `True` | 757,943 |
| `acs/five_year` | workplace | `applicable` | `False` | `True` | `False` | 3,116,130 |
| `acs/five_year` | workplace | `applicable` | `False` | `True` | `True` | 1,570,911 |
| `acs/five_year` | workplace | `applicable` | `True` | `True` | `False` | 1,729,353 |
| `acs/five_year` | workplace | `applicable` | `True` | `True` | `True` | 883,753 |
| `acs/five_year` | workplace | `foreign` | `False` | `False` | `False` | 3,052 |
| `acs/five_year` | workplace | `niu_or_unidentifiable` | `False` | `False` | `False` | 152,951 |
| `acs/five_year` | workplace | `territory` | `False` | `False` | `False` | 50 |
| `acs/five_year` | workplace | `territory` | `True` | `False` | `False` | 12 |
| `acs/vintage` | migration | `applicable` | `False` | `True` | `False` | 130,299 |
| `acs/vintage` | migration | `applicable` | `False` | `True` | `True` | 59,830 |
| `acs/vintage` | migration | `foreign` | `False` | `False` | `False` | 7,738 |
| `acs/vintage` | migration | `niu_or_unidentifiable` | `False` | `False` | `False` | 1,377,386 |
| `acs/vintage` | migration | `territory` | `False` | `False` | `False` | 167 |
| `acs/vintage` | residence | `applicable` | `False` | `True` | `False` | 1,129,909 |
| `acs/vintage` | residence | `applicable` | `False` | `True` | `True` | 445,511 |
| `acs/vintage` | workplace | `applicable` | `False` | `True` | `False` | 1,026,776 |
| `acs/vintage` | workplace | `applicable` | `False` | `True` | `True` | 515,872 |
| `acs/vintage` | workplace | `foreign` | `False` | `False` | `False` | 702 |
| `acs/vintage` | workplace | `niu_or_unidentifiable` | `False` | `False` | `False` | 32,060 |
| `acs/vintage` | workplace | `territory` | `False` | `False` | `False` | 10 |

Industry source-geography recoding by sample/component:

| Profile | Sample | Component year | Industry source recoded | Rows |
| --- | --- | --- | --- | --- |
| `acs/core` | `us2023a` | 2023 | `False` | 1,598,838 |
| `acs/core` | `us2024a` | 2024 | `False` | 1,608,021 |
| `acs/five_year` | `us2024c` | 2020 | `True` | 1,194,039 |
| `acs/five_year` | `us2024c` | 2021 | `True` | 1,479,894 |
| `acs/five_year` | `us2024c` | 2022 | `True` | 1,575,420 |
| `acs/five_year` | `us2024c` | 2023 | `False` | 1,598,838 |
| `acs/five_year` | `us2024c` | 2024 | `False` | 1,608,021 |
| `acs/vintage` | `us2022a` | 2022 | `False` | 1,575,420 |

### Complete ordered output schemas

For each of the eight Parquets, positions are one-based and follow the exact `columns` order in the first bundle `outputs.json`; dtype comes from that file’s `schema`. B2 independently compared all eight ordered schemas and logical values against the replay. These are field names and types only.

<details><summary>acs_area_lookup.parquet — 36,229 rows, 20 ordered fields</summary>

```text
001 area_lookup_id: String
002 profile: String
003 sample_id: String
004 release_year: Int64
005 component_year: Int64
006 role: String
007 source_state_code: String
008 source_area_code: String
009 state_fips: String
010 area_code: String
011 area_type: String
012 puma_vintage: Int64
013 area_status: String
014 status_reason: String
015 factor_key: String
016 flag_source_geography_recoded: Boolean
017 source_allocation_evidence_status: String
018 reference_ids: List(String)
019 reference_locators: List(String)
020 rule_version: String
```

</details>

<details><summary>acs_code_lookup.parquet — 1,062 rows, 28 ordered fields</summary>

```text
001 code_lookup_id: String
002 system: String
003 source_scheme: String
004 native_vintage: Int64
005 canonical_vintage: Int64
006 paired_census_code: String
007 source_token: String
008 mapping_status: String
009 native_node_id: String
010 native_finest_candidates: List(String)
011 canonical_finest_candidates: List(String)
012 canonical_candidate_paths: List(List(String))
013 canonical_common_node_id: String
014 canonical_scalar_code: String
015 canonical_scalar_node_id: String
016 aggregation_type: String
017 aggregation_markers: List(String)
018 aggregation_reason_status: String
019 aggregation_reasons: List(String)
020 special_reason: String
021 flag_aggregate: Boolean
022 flag_partial: Boolean
023 flag_exception: Boolean
024 flag_vintage_crosswalk: Boolean
025 flag_reference_ambiguity: Boolean
026 reference_ids: List(String)
027 reference_locators: List(String)
028 rule_version: String
```

</details>

<details><summary>acs_core_canonical.parquet — 3,206,859 rows, 261 ordered fields</summary>

```text
001 YEAR: Int64
002 SAMPLE: Int64
003 SERIAL: Int64
004 CBSERIAL: Int64
005 HHWT: Float64
006 CLUSTER: Int64
007 REGION: Int64
008 STATEFIP: Int64
009 COUNTYFIP: Int64
010 PUMA: Int64
011 MET2023: Int64
012 MET2023ERR: Int64
013 STRATA: Int64
014 GQ: Int64
015 PERNUM: Int64
016 PERWT: Float64
017 REPWTP: Int64
018 SEX: Int64
019 AGE: Int64
020 EDUC: Int64
021 EDUCD: Int64
022 DEGFIELD: Int64
023 DEGFIELDD: Int64
024 DEGFIELD2: Int64
025 DEGFIELD2D: Int64
026 EMPSTAT: Int64
027 EMPSTATD: Int64
028 CLASSWKR: Int64
029 CLASSWKRD: Int64
030 OCC: Int64
031 OCCSOC: String
032 IND: Int64
033 INDNAICS: String
034 WKSWORK2: Int64
035 UHRSWORK: Int64
036 INCWAGE: Int64
037 INCWAGE_CPIU_2010: Float64
038 INCEARN: Int64
039 MIGRATE1: Int64
040 MIGRATE1D: Int64
041 MIGPLAC1: Int64
042 MIGPUMA1: Int64
043 MIGMET23: Int64
044 PWSTATE2: Int64
045 PWMET23: Int64
046 PWMET23ERR: Int64
047 PWPUMA00: Int64
048 TRANWORK: Int64
049 TRANTIME: Int64
050 QAGE: Int64
051 QSEX: Int64
052 QEDUC: Int64
053 QDEGFIELD: Int64
054 QCLASSWK: Int64
055 QEMPSTAT: Int64
056 QIND: Int64
057 QOCC: Int64
058 QUHRSWOR: Int64
059 QWKSWORK2: Int64
060 QINCEARN: Int64
061 QINCBUS: Int64
062 QINCWAGE: Int64
063 QMIGPLC1: Int64
064 QMIGRAT1: String
065 QPWSTAT2: Int64
066 QTRANTIM: Int64
067 QTRANWOR: Int64
068 REPWTP1: Int64
069 REPWTP2: Int64
070 REPWTP3: Int64
071 REPWTP4: Int64
072 REPWTP5: Int64
073 REPWTP6: Int64
074 REPWTP7: Int64
075 REPWTP8: Int64
076 REPWTP9: Int64
077 REPWTP10: Int64
078 REPWTP11: Int64
079 REPWTP12: Int64
080 REPWTP13: Int64
081 REPWTP14: Int64
082 REPWTP15: Int64
083 REPWTP16: Int64
084 REPWTP17: Int64
085 REPWTP18: Int64
086 REPWTP19: Int64
087 REPWTP20: Int64
088 REPWTP21: Int64
089 REPWTP22: Int64
090 REPWTP23: Int64
091 REPWTP24: Int64
092 REPWTP25: Int64
093 REPWTP26: Int64
094 REPWTP27: Int64
095 REPWTP28: Int64
096 REPWTP29: Int64
097 REPWTP30: Int64
098 REPWTP31: Int64
099 REPWTP32: Int64
100 REPWTP33: Int64
101 REPWTP34: Int64
102 REPWTP35: Int64
103 REPWTP36: Int64
104 REPWTP37: Int64
105 REPWTP38: Int64
106 REPWTP39: Int64
107 REPWTP40: Int64
108 REPWTP41: Int64
109 REPWTP42: Int64
110 REPWTP43: Int64
111 REPWTP44: Int64
112 REPWTP45: Int64
113 REPWTP46: Int64
114 REPWTP47: Int64
115 REPWTP48: Int64
116 REPWTP49: Int64
117 REPWTP50: Int64
118 REPWTP51: Int64
119 REPWTP52: Int64
120 REPWTP53: Int64
121 REPWTP54: Int64
122 REPWTP55: Int64
123 REPWTP56: Int64
124 REPWTP57: Int64
125 REPWTP58: Int64
126 REPWTP59: Int64
127 REPWTP60: Int64
128 REPWTP61: Int64
129 REPWTP62: Int64
130 REPWTP63: Int64
131 REPWTP64: Int64
132 REPWTP65: Int64
133 REPWTP66: Int64
134 REPWTP67: Int64
135 REPWTP68: Int64
136 REPWTP69: Int64
137 REPWTP70: Int64
138 REPWTP71: Int64
139 REPWTP72: Int64
140 REPWTP73: Int64
141 REPWTP74: Int64
142 REPWTP75: Int64
143 REPWTP76: Int64
144 REPWTP77: Int64
145 REPWTP78: Int64
146 REPWTP79: Int64
147 REPWTP80: Int64
148 source_parquet_sha256: String
149 source_row: UInt64
150 acs_profile: String
151 acs_sample_id: String
152 acs_release_year: Int64
153 acs_component_year: Int64
154 industry_delivered_scheme: String
155 industry_interview_scheme: String
156 occupation_delivered_scheme: String
157 flag_source_industry_recoded: Boolean
158 industry_source_allocation_status: String
159 occupation_source_allocation_status: String
160 industry_source_allocated: Boolean
161 occupation_source_allocated: Boolean
162 migration_source_allocation_status: String
163 migration_source_allocated: Boolean
164 source_flag_reference_ids: List(String)
165 industry_code_lookup_id: String
166 industry_source_token: String
167 industry_mapping_status: String
168 industry_native_vintage: Int64
169 industry_canonical_vintage: Int64
170 industry_paired_census_code: String
171 industry_native_node_id: String
172 industry_native_finest_candidates: List(String)
173 industry_canonical_finest_candidates: List(String)
174 industry_canonical_candidate_paths: List(List(String))
175 industry_canonical_common_node_id: String
176 industry_canonical_scalar_code: String
177 industry_canonical_scalar_node_id: String
178 industry_aggregation_type: String
179 industry_aggregation_markers: List(String)
180 industry_aggregation_reason_status: String
181 industry_aggregation_reasons: List(String)
182 industry_special_reason: String
183 industry_flag_aggregate: Boolean
184 industry_flag_partial: Boolean
185 industry_flag_exception: Boolean
186 industry_flag_vintage_crosswalk: Boolean
187 industry_flag_reference_ambiguity: Boolean
188 industry_reference_ids: List(String)
189 industry_reference_locators: List(String)
190 industry_rule_version: String
191 occupation_code_lookup_id: String
192 occupation_source_token: String
193 occupation_mapping_status: String
194 occupation_native_vintage: Int64
195 occupation_canonical_vintage: Int64
196 occupation_paired_census_code: String
197 occupation_native_node_id: String
198 occupation_native_finest_candidates: List(String)
199 occupation_canonical_finest_candidates: List(String)
200 occupation_canonical_candidate_paths: List(List(String))
201 occupation_canonical_common_node_id: String
202 occupation_canonical_scalar_code: String
203 occupation_canonical_scalar_node_id: String
204 occupation_aggregation_type: String
205 occupation_aggregation_markers: List(String)
206 occupation_aggregation_reason_status: String
207 occupation_aggregation_reasons: List(String)
208 occupation_special_reason: String
209 occupation_flag_aggregate: Boolean
210 occupation_flag_partial: Boolean
211 occupation_flag_exception: Boolean
212 occupation_flag_vintage_crosswalk: Boolean
213 occupation_flag_reference_ambiguity: Boolean
214 occupation_reference_ids: List(String)
215 occupation_reference_locators: List(String)
216 occupation_rule_version: String
217 residence_area_lookup_id: String
218 residence_state_fips: String
219 residence_area_code: String
220 residence_area_type: String
221 residence_puma_vintage: Int64
222 residence_area_status: String
223 residence_status_reason: String
224 residence_factor_key: String
225 residence_flag_source_geography_recoded: Boolean
226 residence_source_allocation_evidence_status: String
227 residence_reference_ids: List(String)
228 residence_reference_locators: List(String)
229 residence_rule_version: String
230 residence_flag_geographic_allocation: Boolean
231 residence_flag_fractional_split: Boolean
232 workplace_area_lookup_id: String
233 workplace_state_fips: String
234 workplace_area_code: String
235 workplace_area_type: String
236 workplace_puma_vintage: Int64
237 workplace_area_status: String
238 workplace_status_reason: String
239 workplace_factor_key: String
240 workplace_flag_source_geography_recoded: Boolean
241 workplace_source_allocation_evidence_status: String
242 workplace_reference_ids: List(String)
243 workplace_reference_locators: List(String)
244 workplace_rule_version: String
245 workplace_flag_geographic_allocation: Boolean
246 workplace_flag_fractional_split: Boolean
247 migration_area_lookup_id: String
248 migration_state_fips: String
249 migration_area_code: String
250 migration_area_type: String
251 migration_puma_vintage: Int64
252 migration_area_status: String
253 migration_status_reason: String
254 migration_factor_key: String
255 migration_flag_source_geography_recoded: Boolean
256 migration_source_allocation_evidence_status: String
257 migration_reference_ids: List(String)
258 migration_reference_locators: List(String)
259 migration_rule_version: String
260 migration_flag_geographic_allocation: Boolean
261 migration_flag_fractional_split: Boolean
```

</details>

<details><summary>acs_five_year_canonical.parquet — 7,456,212 rows, 262 ordered fields</summary>

```text
001 YEAR: Int64
002 MULTYEAR: Int64
003 SAMPLE: Int64
004 SERIAL: Int64
005 CBSERIAL: Int64
006 HHWT: Float64
007 CLUSTER: Int64
008 REGION: Int64
009 STATEFIP: Int64
010 COUNTYFIP: Int64
011 PUMA: Int64
012 MET2023: Int64
013 MET2023ERR: Int64
014 STRATA: Int64
015 GQ: Int64
016 PERNUM: Int64
017 PERWT: Float64
018 REPWTP: Int64
019 SEX: Int64
020 AGE: Int64
021 EDUC: Int64
022 EDUCD: Int64
023 DEGFIELD: Int64
024 DEGFIELDD: Int64
025 DEGFIELD2: Int64
026 DEGFIELD2D: Int64
027 EMPSTAT: Int64
028 EMPSTATD: Int64
029 CLASSWKR: Int64
030 CLASSWKRD: Int64
031 OCC: Int64
032 OCCSOC: String
033 IND: Int64
034 INDNAICS: String
035 WKSWORK2: Int64
036 UHRSWORK: Int64
037 INCWAGE: Int64
038 INCWAGE_CPIU_2010: Float64
039 INCEARN: Int64
040 MIGRATE1: Int64
041 MIGRATE1D: Int64
042 MIGPLAC1: Int64
043 MIGPUMA1: Int64
044 MIGMET23: Int64
045 PWSTATE2: Int64
046 PWMET23: Int64
047 PWMET23ERR: Int64
048 PWPUMA00: Int64
049 TRANWORK: Int64
050 TRANTIME: Int64
051 QAGE: Int64
052 QSEX: Int64
053 QEDUC: Int64
054 QDEGFIELD: Int64
055 QCLASSWK: Int64
056 QEMPSTAT: Int64
057 QIND: Int64
058 QOCC: Int64
059 QUHRSWOR: Int64
060 QWKSWORK2: Int64
061 QINCEARN: Int64
062 QINCBUS: Int64
063 QINCWAGE: Int64
064 QMIGPLC1: Int64
065 QMIGRAT1: Int64
066 QPWSTAT2: Int64
067 QTRANTIM: Int64
068 QTRANWOR: Int64
069 REPWTP1: Int64
070 REPWTP2: Int64
071 REPWTP3: Int64
072 REPWTP4: Int64
073 REPWTP5: Int64
074 REPWTP6: Int64
075 REPWTP7: Int64
076 REPWTP8: Int64
077 REPWTP9: Int64
078 REPWTP10: Int64
079 REPWTP11: Int64
080 REPWTP12: Int64
081 REPWTP13: Int64
082 REPWTP14: Int64
083 REPWTP15: Int64
084 REPWTP16: Int64
085 REPWTP17: Int64
086 REPWTP18: Int64
087 REPWTP19: Int64
088 REPWTP20: Int64
089 REPWTP21: Int64
090 REPWTP22: Int64
091 REPWTP23: Int64
092 REPWTP24: Int64
093 REPWTP25: Int64
094 REPWTP26: Int64
095 REPWTP27: Int64
096 REPWTP28: Int64
097 REPWTP29: Int64
098 REPWTP30: Int64
099 REPWTP31: Int64
100 REPWTP32: Int64
101 REPWTP33: Int64
102 REPWTP34: Int64
103 REPWTP35: Int64
104 REPWTP36: Int64
105 REPWTP37: Int64
106 REPWTP38: Int64
107 REPWTP39: Int64
108 REPWTP40: Int64
109 REPWTP41: Int64
110 REPWTP42: Int64
111 REPWTP43: Int64
112 REPWTP44: Int64
113 REPWTP45: Int64
114 REPWTP46: Int64
115 REPWTP47: Int64
116 REPWTP48: Int64
117 REPWTP49: Int64
118 REPWTP50: Int64
119 REPWTP51: Int64
120 REPWTP52: Int64
121 REPWTP53: Int64
122 REPWTP54: Int64
123 REPWTP55: Int64
124 REPWTP56: Int64
125 REPWTP57: Int64
126 REPWTP58: Int64
127 REPWTP59: Int64
128 REPWTP60: Int64
129 REPWTP61: Int64
130 REPWTP62: Int64
131 REPWTP63: Int64
132 REPWTP64: Int64
133 REPWTP65: Int64
134 REPWTP66: Int64
135 REPWTP67: Int64
136 REPWTP68: Int64
137 REPWTP69: Int64
138 REPWTP70: Int64
139 REPWTP71: Int64
140 REPWTP72: Int64
141 REPWTP73: Int64
142 REPWTP74: Int64
143 REPWTP75: Int64
144 REPWTP76: Int64
145 REPWTP77: Int64
146 REPWTP78: Int64
147 REPWTP79: Int64
148 REPWTP80: Int64
149 source_parquet_sha256: String
150 source_row: UInt64
151 acs_profile: String
152 acs_sample_id: String
153 acs_release_year: Int64
154 acs_component_year: Int64
155 industry_delivered_scheme: String
156 industry_interview_scheme: String
157 occupation_delivered_scheme: String
158 flag_source_industry_recoded: Boolean
159 industry_source_allocation_status: String
160 occupation_source_allocation_status: String
161 industry_source_allocated: Boolean
162 occupation_source_allocated: Boolean
163 migration_source_allocation_status: String
164 migration_source_allocated: Boolean
165 source_flag_reference_ids: List(String)
166 industry_code_lookup_id: String
167 industry_source_token: String
168 industry_mapping_status: String
169 industry_native_vintage: Int64
170 industry_canonical_vintage: Int64
171 industry_paired_census_code: String
172 industry_native_node_id: String
173 industry_native_finest_candidates: List(String)
174 industry_canonical_finest_candidates: List(String)
175 industry_canonical_candidate_paths: List(List(String))
176 industry_canonical_common_node_id: String
177 industry_canonical_scalar_code: String
178 industry_canonical_scalar_node_id: String
179 industry_aggregation_type: String
180 industry_aggregation_markers: List(String)
181 industry_aggregation_reason_status: String
182 industry_aggregation_reasons: List(String)
183 industry_special_reason: String
184 industry_flag_aggregate: Boolean
185 industry_flag_partial: Boolean
186 industry_flag_exception: Boolean
187 industry_flag_vintage_crosswalk: Boolean
188 industry_flag_reference_ambiguity: Boolean
189 industry_reference_ids: List(String)
190 industry_reference_locators: List(String)
191 industry_rule_version: String
192 occupation_code_lookup_id: String
193 occupation_source_token: String
194 occupation_mapping_status: String
195 occupation_native_vintage: Int64
196 occupation_canonical_vintage: Int64
197 occupation_paired_census_code: String
198 occupation_native_node_id: String
199 occupation_native_finest_candidates: List(String)
200 occupation_canonical_finest_candidates: List(String)
201 occupation_canonical_candidate_paths: List(List(String))
202 occupation_canonical_common_node_id: String
203 occupation_canonical_scalar_code: String
204 occupation_canonical_scalar_node_id: String
205 occupation_aggregation_type: String
206 occupation_aggregation_markers: List(String)
207 occupation_aggregation_reason_status: String
208 occupation_aggregation_reasons: List(String)
209 occupation_special_reason: String
210 occupation_flag_aggregate: Boolean
211 occupation_flag_partial: Boolean
212 occupation_flag_exception: Boolean
213 occupation_flag_vintage_crosswalk: Boolean
214 occupation_flag_reference_ambiguity: Boolean
215 occupation_reference_ids: List(String)
216 occupation_reference_locators: List(String)
217 occupation_rule_version: String
218 residence_area_lookup_id: String
219 residence_state_fips: String
220 residence_area_code: String
221 residence_area_type: String
222 residence_puma_vintage: Int64
223 residence_area_status: String
224 residence_status_reason: String
225 residence_factor_key: String
226 residence_flag_source_geography_recoded: Boolean
227 residence_source_allocation_evidence_status: String
228 residence_reference_ids: List(String)
229 residence_reference_locators: List(String)
230 residence_rule_version: String
231 residence_flag_geographic_allocation: Boolean
232 residence_flag_fractional_split: Boolean
233 workplace_area_lookup_id: String
234 workplace_state_fips: String
235 workplace_area_code: String
236 workplace_area_type: String
237 workplace_puma_vintage: Int64
238 workplace_area_status: String
239 workplace_status_reason: String
240 workplace_factor_key: String
241 workplace_flag_source_geography_recoded: Boolean
242 workplace_source_allocation_evidence_status: String
243 workplace_reference_ids: List(String)
244 workplace_reference_locators: List(String)
245 workplace_rule_version: String
246 workplace_flag_geographic_allocation: Boolean
247 workplace_flag_fractional_split: Boolean
248 migration_area_lookup_id: String
249 migration_state_fips: String
250 migration_area_code: String
251 migration_area_type: String
252 migration_puma_vintage: Int64
253 migration_area_status: String
254 migration_status_reason: String
255 migration_factor_key: String
256 migration_flag_source_geography_recoded: Boolean
257 migration_source_allocation_evidence_status: String
258 migration_reference_ids: List(String)
259 migration_reference_locators: List(String)
260 migration_rule_version: String
261 migration_flag_geographic_allocation: Boolean
262 migration_flag_fractional_split: Boolean
```

</details>

<details><summary>acs_vintage_canonical.parquet — 1,575,420 rows, 260 ordered fields</summary>

```text
001 YEAR: Int64
002 SAMPLE: Int64
003 SERIAL: Int64
004 CBSERIAL: Int64
005 HHWT: Float64
006 CLUSTER: Int64
007 REGION: Int64
008 STATEFIP: Int64
009 COUNTYFIP: Int64
010 PUMA: Int64
011 MET2023: Int64
012 MET2023ERR: Int64
013 STRATA: Int64
014 GQ: Int64
015 PERNUM: Int64
016 PERWT: Float64
017 REPWTP: Int64
018 SEX: Int64
019 AGE: Int64
020 EDUC: Int64
021 EDUCD: Int64
022 DEGFIELD: Int64
023 DEGFIELDD: Int64
024 DEGFIELD2: Int64
025 DEGFIELD2D: Int64
026 EMPSTAT: Int64
027 EMPSTATD: Int64
028 CLASSWKR: Int64
029 CLASSWKRD: Int64
030 OCC: Int64
031 OCCSOC: String
032 IND: Int64
033 INDNAICS: String
034 WKSWORK2: Int64
035 UHRSWORK: Int64
036 INCWAGE: Int64
037 INCWAGE_CPIU_2010: Float64
038 INCEARN: Int64
039 MIGRATE1: Int64
040 MIGRATE1D: Int64
041 MIGPLAC1: Int64
042 MIGPUMA1: Int64
043 MIGMET23: Int64
044 PWSTATE2: Int64
045 PWMET23: Int64
046 PWMET23ERR: Int64
047 PWPUMA00: Int64
048 TRANWORK: Int64
049 TRANTIME: Int64
050 QAGE: Int64
051 QSEX: Int64
052 QEDUC: Int64
053 QDEGFIELD: Int64
054 QCLASSWK: Int64
055 QEMPSTAT: Int64
056 QIND: Int64
057 QOCC: Int64
058 QUHRSWOR: Int64
059 QWKSWORK2: Int64
060 QINCEARN: Int64
061 QINCBUS: Int64
062 QINCWAGE: Int64
063 QMIGPLC1: Int64
064 QPWSTAT2: Int64
065 QTRANTIM: Int64
066 QTRANWOR: Int64
067 REPWTP1: Int64
068 REPWTP2: Int64
069 REPWTP3: Int64
070 REPWTP4: Int64
071 REPWTP5: Int64
072 REPWTP6: Int64
073 REPWTP7: Int64
074 REPWTP8: Int64
075 REPWTP9: Int64
076 REPWTP10: Int64
077 REPWTP11: Int64
078 REPWTP12: Int64
079 REPWTP13: Int64
080 REPWTP14: Int64
081 REPWTP15: Int64
082 REPWTP16: Int64
083 REPWTP17: Int64
084 REPWTP18: Int64
085 REPWTP19: Int64
086 REPWTP20: Int64
087 REPWTP21: Int64
088 REPWTP22: Int64
089 REPWTP23: Int64
090 REPWTP24: Int64
091 REPWTP25: Int64
092 REPWTP26: Int64
093 REPWTP27: Int64
094 REPWTP28: Int64
095 REPWTP29: Int64
096 REPWTP30: Int64
097 REPWTP31: Int64
098 REPWTP32: Int64
099 REPWTP33: Int64
100 REPWTP34: Int64
101 REPWTP35: Int64
102 REPWTP36: Int64
103 REPWTP37: Int64
104 REPWTP38: Int64
105 REPWTP39: Int64
106 REPWTP40: Int64
107 REPWTP41: Int64
108 REPWTP42: Int64
109 REPWTP43: Int64
110 REPWTP44: Int64
111 REPWTP45: Int64
112 REPWTP46: Int64
113 REPWTP47: Int64
114 REPWTP48: Int64
115 REPWTP49: Int64
116 REPWTP50: Int64
117 REPWTP51: Int64
118 REPWTP52: Int64
119 REPWTP53: Int64
120 REPWTP54: Int64
121 REPWTP55: Int64
122 REPWTP56: Int64
123 REPWTP57: Int64
124 REPWTP58: Int64
125 REPWTP59: Int64
126 REPWTP60: Int64
127 REPWTP61: Int64
128 REPWTP62: Int64
129 REPWTP63: Int64
130 REPWTP64: Int64
131 REPWTP65: Int64
132 REPWTP66: Int64
133 REPWTP67: Int64
134 REPWTP68: Int64
135 REPWTP69: Int64
136 REPWTP70: Int64
137 REPWTP71: Int64
138 REPWTP72: Int64
139 REPWTP73: Int64
140 REPWTP74: Int64
141 REPWTP75: Int64
142 REPWTP76: Int64
143 REPWTP77: Int64
144 REPWTP78: Int64
145 REPWTP79: Int64
146 REPWTP80: Int64
147 source_parquet_sha256: String
148 source_row: UInt64
149 acs_profile: String
150 acs_sample_id: String
151 acs_release_year: Int64
152 acs_component_year: Int64
153 industry_delivered_scheme: String
154 industry_interview_scheme: String
155 occupation_delivered_scheme: String
156 flag_source_industry_recoded: Boolean
157 industry_source_allocation_status: String
158 occupation_source_allocation_status: String
159 industry_source_allocated: Boolean
160 occupation_source_allocated: Boolean
161 migration_source_allocation_status: String
162 migration_source_allocated: Boolean
163 source_flag_reference_ids: List(String)
164 industry_code_lookup_id: String
165 industry_source_token: String
166 industry_mapping_status: String
167 industry_native_vintage: Int64
168 industry_canonical_vintage: Int64
169 industry_paired_census_code: String
170 industry_native_node_id: String
171 industry_native_finest_candidates: List(String)
172 industry_canonical_finest_candidates: List(String)
173 industry_canonical_candidate_paths: List(List(String))
174 industry_canonical_common_node_id: String
175 industry_canonical_scalar_code: String
176 industry_canonical_scalar_node_id: String
177 industry_aggregation_type: String
178 industry_aggregation_markers: List(String)
179 industry_aggregation_reason_status: String
180 industry_aggregation_reasons: List(String)
181 industry_special_reason: String
182 industry_flag_aggregate: Boolean
183 industry_flag_partial: Boolean
184 industry_flag_exception: Boolean
185 industry_flag_vintage_crosswalk: Boolean
186 industry_flag_reference_ambiguity: Boolean
187 industry_reference_ids: List(String)
188 industry_reference_locators: List(String)
189 industry_rule_version: String
190 occupation_code_lookup_id: String
191 occupation_source_token: String
192 occupation_mapping_status: String
193 occupation_native_vintage: Int64
194 occupation_canonical_vintage: Int64
195 occupation_paired_census_code: String
196 occupation_native_node_id: String
197 occupation_native_finest_candidates: List(String)
198 occupation_canonical_finest_candidates: List(String)
199 occupation_canonical_candidate_paths: List(List(String))
200 occupation_canonical_common_node_id: String
201 occupation_canonical_scalar_code: String
202 occupation_canonical_scalar_node_id: String
203 occupation_aggregation_type: String
204 occupation_aggregation_markers: List(String)
205 occupation_aggregation_reason_status: String
206 occupation_aggregation_reasons: List(String)
207 occupation_special_reason: String
208 occupation_flag_aggregate: Boolean
209 occupation_flag_partial: Boolean
210 occupation_flag_exception: Boolean
211 occupation_flag_vintage_crosswalk: Boolean
212 occupation_flag_reference_ambiguity: Boolean
213 occupation_reference_ids: List(String)
214 occupation_reference_locators: List(String)
215 occupation_rule_version: String
216 residence_area_lookup_id: String
217 residence_state_fips: String
218 residence_area_code: String
219 residence_area_type: String
220 residence_puma_vintage: Int64
221 residence_area_status: String
222 residence_status_reason: String
223 residence_factor_key: String
224 residence_flag_source_geography_recoded: Boolean
225 residence_source_allocation_evidence_status: String
226 residence_reference_ids: List(String)
227 residence_reference_locators: List(String)
228 residence_rule_version: String
229 residence_flag_geographic_allocation: Boolean
230 residence_flag_fractional_split: Boolean
231 workplace_area_lookup_id: String
232 workplace_state_fips: String
233 workplace_area_code: String
234 workplace_area_type: String
235 workplace_puma_vintage: Int64
236 workplace_area_status: String
237 workplace_status_reason: String
238 workplace_factor_key: String
239 workplace_flag_source_geography_recoded: Boolean
240 workplace_source_allocation_evidence_status: String
241 workplace_reference_ids: List(String)
242 workplace_reference_locators: List(String)
243 workplace_rule_version: String
244 workplace_flag_geographic_allocation: Boolean
245 workplace_flag_fractional_split: Boolean
246 migration_area_lookup_id: String
247 migration_state_fips: String
248 migration_area_code: String
249 migration_area_type: String
250 migration_puma_vintage: Int64
251 migration_area_status: String
252 migration_status_reason: String
253 migration_factor_key: String
254 migration_flag_source_geography_recoded: Boolean
255 migration_source_allocation_evidence_status: String
256 migration_reference_ids: List(String)
257 migration_reference_locators: List(String)
258 migration_rule_version: String
259 migration_flag_geographic_allocation: Boolean
260 migration_flag_fractional_split: Boolean
```

</details>

<details><summary>puma_county_factors.parquet — 7,754 rows, 20 ordered fields</summary>

```text
001 factor_key: String
002 area_type: String
003 state_fips: String
004 area_code: String
005 county_geoid: String
006 county_node_id: String
007 intersection_population: Int64
008 area_population: Int64
009 county_population: Int64
010 factor: Float64
011 published_area_factor: Float64
012 published_county_factor: Float64
013 population_year: Int64
014 puma_vintage: Int64
015 county_composition_year: Int64
016 county_inventory_vintage: Int64
017 flag_geographic_allocation: Boolean
018 flag_fractional_split: Boolean
019 reference_ids: List(String)
020 reference_locators: List(String)
```

</details>

<details><summary>puma_msa_coverage.parquet — 2,462 rows, 12 ordered fields</summary>

```text
001 state_fips: String
002 puma_code: String
003 puma_population: Int64
004 msa_population: Int64
005 non_msa_population: Int64
006 msa_fraction: Float64
007 non_msa_fraction: Float64
008 population_year: Int64
009 puma_vintage: Int64
010 msa_delineation: String
011 reference_ids: List(String)
012 reference_locators: List(String)
```

</details>

<details><summary>puma_msa_factors.parquet — 2,328 rows, 19 ordered fields</summary>

```text
001 state_fips: String
002 puma_code: String
003 msa_code: String
004 msa_node_id: String
005 puma_population: Int64
006 msa_population: Int64
007 intersection_population: Int64
008 puma_to_msa_factor: Float64
009 msa_to_puma_factor: Float64
010 published_percent_puma: Float64
011 published_percent_msa: Float64
012 population_year: Int64
013 puma_vintage: Int64
014 msa_delineation: String
015 county_inventory_vintage: Int64
016 flag_geographic_allocation: Boolean
017 flag_fractional_split: Boolean
018 reference_ids: List(String)
019 reference_locators: List(String)
```

</details>


## Handoff to later stages — actual APIs, repository adoption PENDING

Interfaces below were read from r6 committed source and checked against the reviewed r7 source at `1542f8d`; C1 and final seal reauthenticated the executing and independent member inventories. Consume the science-sealed production runs/pins only after repository adoption; adoption remains PENDING. No latest alias or mixed-run fallback is supplied.

### Trust and publication

`SelectionRequest(codes_run,codes_outputs_sha256,geography_run,geography_outputs_sha256,ipums_run,ipums_outputs_sha256,ipums_references_receipt_sha256)` has seven explicit fields in `acs_mapping_contract`. `acs_mapping_inputs.select_inputs(data_dir:Path,request:SelectionRequest)->SelectedInputs` authenticates complete upstream bundles and all five Stage7 deliveries in place; returns three ACS `.sources`, `.codes`/`.geography` paths, `.provenance`, frozen `.software`. `.verify()->None` repeats selection. Each SourceInput carries profile/delivery/Parquet/record/raw citations/definition/DDI.

`acs_mapping_bundle.build(data_dir,run_id,request,reference_id,*,expected_reference_receipt_sha256)->dict` returns run_id,directory,outputs_sha256. `verify_bundle(directory:Path,data_dir:Path,*,expected_outputs_sha256:str)->dict` authenticates the external pin first, reconstructs five references and all companion annotations, then rechecks inputs. `compare_runs(first:Path,second:Path)->dict` compares all eight ordered logical tables and substantive report, omitting only top-level report run_id/created_at; returns `trust_established=False`. Comparison is not authentication or a physical-byte equality guarantee.

The standalone `python -m embedding_data.acs_mapping` group exposes exactly acquire-references,import-reference,build,verify,compare-runs. Every command requires explicit `--data-dir`; build requires reference/upstream IDs and detached pins. No top-level CLI registration was added. V2 acquire/import requires explicit `--reference-version acs-mapping-references-v2`; default remains v1. Only acquisition retrieves public originals. Build/verify/comparison stay offline with no .env/credential/IPUMS construction. Occupied finals/partials and symlinks fail.

Verifier/report machine fields retain `mapping_gate.adopted=False`, `v8.adopted=False`, `limits.full_data_acceptance=False`; future finding adoption is external and never rewrites those conservative fields. Rule/table format stays acs-mapping-v1 / acs-code-rules-v1 / acs-area-rules-v1, while reference editions support v1 and v2.

### Stage 9: ACS target construction

Consume the selected three canonical companions plus five lookup/factor tables after repository adoption; their measured IDs, pins and schemas are above. `source_row` is zero-based UInt64 within `source_parquet_sha256`, not cross-delivery person linkage. Complete source columns precede the 114-field annotation suffix. `companion_schema(source_schema)` rejects collisions; `annotate_source(source,code_lookup,area_lookup,factors)->pl.LazyFrame` uses many-to-one order-preserving joins. `write_companion(frame,source,destination)->dict` sinks to caller staging and checks fidelity; `validate_companion(source,companion,code_lookup,area_lookup,factors)->dict` reconstructs every annotation. The fixed writer has no hidden lookup context; do not invent extra parameters or rely on interim interfaces.

`observed_code_keys(sources)` and `build_code_lookup(observed,evidence,selected)` produce unweighted native/canonical possibilities. Natural key `(system,source_scheme,paired_census_code,source_token)` hashes canonical JSON to code_lookup_id. Industry/occupation fields retain candidates, aligned root-to-leaf paths, native/common/scalar nodes and independent aggregate/partial/exception/vintage/reference-ambiguity flags. No candidate cross-product or equal-weight classification allocation follows. Singleton candidates do not erase flags; evidence determines scalar availability. Reason status documented/unknown/not_applicable retains empty unknown-reason lists and inspected locators. Lookup statuses mapped/documented_special differ from companion missing: missing has null lookup/scalars and typed empty lists. Only SOC2018 pair9830/559830 is the approved no-candidate special; malformed nonmissing codes fail.

`scheme_for(profile,sample_id,release_year,component_year)` keeps delivered versus interview industry scheme and source recoding independent. Five-year uses MULTYEAR; annual uses YEAR. Native annual 2022 NAICS 2017 crosswalks to 2022; later annual/five-year delivered schemes are 2022; SOC is 2018. Q evidence stays independent of candidates and geography. Contract allocation statuses include allocated,not_allocated,not_allocated_or_niu,not_applicable,unavailable; current annotations assign `*_source_allocated=True` only for positive allocated evidence and otherwise null, including ambiguous zero. Do not infer false/unallocated from missing evidence, another delivery or a singleton.

`observed_area_keys(sources)` and `build_area_lookup(observed,rules,evidence,factors)` retain full `(profile,sample_id,release_year,component_year,role,source_state_code,source_area_code)` identity and hashed area_lookup_id. Roles are residence/workplace/migration. Disjoint applicable/niu_or_unidentifiable/foreign/territory/documented_unavailable statuses have reasons/citations. Only applicable keys have factor_key. Raw lexical source-state/area, normalized state/area and source-geography-recoding flag have declared nullable cases. Geographic allocation/split, source recoding and source-imputation evidence stay distinct; role source allocation evidence is unavailable while original migration Q is separate. Foreign/suppressed states provide no factor.

`build_factor_tables(evidence,selected)->FactorTables` returns county,msa,coverage,diagnostics; `validate_factor_tables` reconstructs them. `factor_key(area_type,state_fips,area_code)` hashes `[area_type,state_fips,area_code,2020]`. Residence uses residence; work/migration share work_migration. Apply factors only within the intended estimator, not a person-level role/candidate cross-product. Float64 factors divide exact Int64 intersection populations by area populations; closure tolerance 1e-12. Factor use always means geographic allocation, even one; fractional split means multiple positive counties. A zero row differs from no relation. Residence published fields are nonnull; derived work/migration published fields may be null. Missing membership is never renormalized away.

MSA factors preserve both puma_to_msa_factor/msa_to_puma_factor. Coverage preserves explicit non_msa_population/non_msa_fraction, including PUMAs absent from MSA rows. Keep 2020 population/PUMAs, 2022 composition, 2025 inventory, July 2023 MSAs and CT planning regions distinct. Lists are typed/nonnull with no null elements; sets sort distinct while aligned paths retain root-to-leaf order. Reference tables sort natural keys/nulls first; companions preserve source order.

Stage 9 still owns membership/eligibility, civilian/private wage-and-salary universes, workplace work-from-home exclusion, headline/allocation-included variants, estimands, pooling, employment-weighted classification allocation if separately designed, replicate SEs and family V12. Stage 8 supplies no target/universe/SE helper, person-location inference, MET2023 shortcut or headline rule. Cite approved source spec and roadmap Stage 9 rather than converting parser flags into eligibility.

### Stage 10: ITA establishment targets

No shared upstream executing file or selected ITA artifact changed for Stage 8; D5 is only historical entrypoint provenance compatibility. Preserve selected Stage 2–6 source/assignment/target pins, targets-v1 writer/validator, canonical code/path and linkage interfaces from earlier handoffs. R6 and r7 science closure verified preservation. No authority follows to rebuild ITA, geocode, change eligibility/linkage, rewrite statuses or invoke upstream builders. Text-code/co-ownership membership/deduplication/linkage/family V12 remain Stage 10.

### Stage 11: CPS linkage and job-change flows

Stage 8 selection/parsers cover ACS and admit no CPS source scheme. Retain Stage4 canonical node/path/relationship interfaces and complete candidate semantics. ACS 559830, D4/D8/D10 and C1 grant no CPS bypass. Resolve [Stage7 deferred 2026 9890 authority](../deferred_items.md#7-ipums-extract-verification--2026-10-15) before CPS mapping. Preserve outside-list/unknown states, raw short codes, dependent interviewing/source-allocation, guard/MISH/link-weight limits. CPS parsing/linkage/estimation/uncertainty and CPS V11/V12 remain Stage 11.

### Stage 12: worker profiles and cross-sections

Consume ACS through future Stage 9 helpers and CPS through future Stage 11 helpers after they ship. Mapping evidence provides no worker-profile estimator or eligibility. Preserve independent ambiguity/source-imputation/source-recoding/allocation evidence and unavailable states. Earnings rules, membership, R4.4 CPS metro eligibility, weights/uncertainty/family V12 remain Stage 12; ACS MSA factors do not establish CPS metro eligibility.

### Stage 13: full build, size gate and comparators

Vintage companion supplies native 2017→canonical 2022 possibilities/path evidence with flags and exact source identity. Future five-year/vintage targets use Stage 9 universe/estimation/uncertainty helpers. Consume the measured physical raw/reference/software/output inventories and detached pins above only after final adoption, separately from logical replay. Keep source/target frames and recoding distinct. Comparator targets/citations, V9 minimum support and complete eight-family V12 remain Stage 13. Mapping outputs remain evaluation inputs, never embedder training or model-selection data.

### Contract nullability and keys for downstream joins

The code contract, alongside the measured full ordered schemas above, declares nullable code fields `native_node_id`, `canonical_common_node_id`, `canonical_scalar_code`, `canonical_scalar_node_id`, `special_reason`. Nullable area fields are `source_state_code`, `source_area_code`, `state_fips`, `area_code`, `factor_key`, `flag_source_geography_recoded`. County factors permit null `published_area_factor`/`published_county_factor` only for derived work/migration rows; MSA/coverage schema fields are nonnull. Companion missing-code defaults and source-allocation evidence have the additional null semantics described above. List columns never encode unavailable evidence with a null list or null element.

County natural key is `(area_type,state_fips,area_code,county_geoid)`, MSA key `(state_fips,puma_code,msa_code)`, coverage key `(state_fips,puma_code)`. The role-specific factor key is shared across all county intersections of one area; joining it directly expands into allocation rows and belongs in the later estimator, never in an identity-preserving person annotation join. Shared classification/geography nodes retain the selected Stage 4/5 IDs and typed relationships, with no invented root or forced CBSA state parent.

## Repository work remaining after science closure

The final immutable science closure is complete and reauthenticates both detached pins/bundle inventories, C1 aggregates, original beforestate and exact 87 citations, all six older seals, r6 failed partial, source/software/dependencies, zero external counters and audit zero. It archives complete history at unchanged reviewed source. PENDING for repository adoption: complete Task 10 plan/spec/roadmap documentation, post-document hooks/checks and final whole-branch review. The B1 wrapper exit 1 and unavailable raw first-builder child wait/peak memory remain explicit historical limits. Any executing/reference/dependency correction requires fresh IDs and full acceptance. This measured finding does not tick Stage 8, rewrite R6.3/V8, retire plan/spec, amend roadmap, invent deferral closures or authorize later-stage work.
