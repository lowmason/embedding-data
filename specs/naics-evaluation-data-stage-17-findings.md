# ACS wage microdata — Stage 17 findings: first build and replay

Plan 14 (`specs/plans/completed/14-acs-wage-microdata.md`) ran Task 9 on 2026-11-19. The
spec is `specs/completed/acs-wage-microdata.md`. Both runs verify, and the replay is equal to
the first run.
This finding records measured results only. It adopts no headline minimum count.

**Runs.** `stage17_acs_wage_microdata_20261119_r1` and `..._r1_replay`, in
`data/derived/acs/wage-microdata/`. The control directory is
`data/derived/acs/wage-microdata-controls/stage17_acs_wage_microdata_20261119_r1/`. Its
`freeze.json` has SHA-256 `00e27a9b222e987add096ff504e42ad7a1bf0e5a22ea80c51fa68e38db146882`
and records 31,623 files and no earlier wage microdata run.

| File | First run SHA-256 | Replay SHA-256 |
| --- | --- | --- |
| `outputs.json` (detached pin) | `6cb253e2e5c2e48a5b31d2790a0378636d3b6ef9197cfb2d33cca2813ac201d1` | `f4e47d9c2e0d3274bc047372d440d73276df56b627d1d4c7c6da9a939a0658e8` |
| `inputs.json` | `a27c750cabfe0c66a8b0e525d7bc12610899c8605c669f7a48f3d89764f7d780` | `a25a0139ca7787e7dd1ace040018a3d65105bd00d08bae07995f0a10db9bab38` |
| `report.json` | `32ad9b698c9b940760d74eec0ae3b234abd14ba4c08ca07f04770a8f11e413bd` | same |
| `acs_wage_persons.parquet` | `a94471492dc91aebe3a3436e8d738d399520791b0eace6f01a719fad10fd5ff2` | same |

The two `inputs.json` files differ in the run ID and in `execution.created_at`, the time of
each build (2026-11-20T02:20:15Z and 2026-11-20T02:21:47Z). Executing commit `a800dd5`
(`dirty: false`). CPython 3.14.0, 63 distributions, 19 software files, `uv.lock` SHA-256
`f57c3280a7c8286711bf6804ca4c02f0a19619c9db52f33941b9c5b996cba8e5`. Inputs: Stage 8 run
`stage8_acs_mapping_20261018_r7` (pin `1ec97010…75f4`) and Stage 4 run
`stage4_v11_20261013_r2` (pin `15b95846…9c3a`).

**Gates.** The owner gave the go-ahead for the freeze and first build (Gate 1) and for the
replay (Gate 2). Each time the owner confirmed that no Stage 9 freeze window was open and no
other stage would write under `data/` until the window closed. The window ran from the freeze
(about 21:19) to the preservation check. The narrow `pgrep` (Stage 9 tools) printed nothing
before each command. The broad `pgrep` showed only test and mutant runs of other worktrees.
The Codex seat of the final review ran read-only Polars checks on the Stage 8 core table
before Gate 1 and printed aggregates only. This finding cites none of those figures.

**Measured cost** (`/usr/bin/time -l`, 36 GiB host). Each bundle has 4 files:
376,684,787 B (first run) and 376,684,794 B (replay).

| Command | Wall time | Maximum RSS |
| --- | ---: | ---: |
| Stage 8 `verify` (preflight) | 381.42 s | 26,595,229,696 B |
| `freeze` | 18.17 s | 106,987,520 B |
| `build` (first run) | 16.86 s | 5,831,901,184 B |
| `verify` (first run) | 9.40 s | 9,388,736,512 B |
| `reconcile_stage17.py reconcile` | 2.12 s | 4,657,381,376 B |
| `build` (replay) | 16.82 s | 5,534,482,432 B |
| `verify` (replay) | 10.57 s | 9,182,920,704 B |
| `compare-runs` | 1.88 s | 7,057,244,160 B |
| `reconcile_stage17.py preservation` | 19.60 s | 114,589,696 B |
| `embedding-data audit` | 4.01 s | 175,505,408 B |

**Spec items.**
1. Both `verify` calls pass with their pins. `compare-runs`: `equal`, `report_equal`, and
   table schema and values equal; `trust_established` is false. The Parquet and `report.json`
   are byte-identical.
2. 3,035,086 rows (2023: 1,512,735; 2024: 1,522,351). `industry_node_level` is the level of
   the join node in `industry_node_code` (owner, 2026-11-19), not the level of the delivered
   node.
3. `flag_headline` is true on 1,278,878 rows (2023: 639,002; 2024: 639,876), over 233
   categories in each year. The funnel is 3,035,086, 2,126,596, 1,575,068, 1,496,864 and
   1,278,878. 31 categories share 11 nodes.
4. The independent reconciler is `equal` with no mismatch over 3,035,086 rows. It compares
   every carried column and recomputes the ten new columns.
5. The build, `verify` and the reconciler check the headline rules. None reports a headline
   row with an allocation, without full time and full year, with a false `flag_wage_salary`
   or with a shared node.
6. The build, `verify` and the reconciler check the node rule against the Stage 4 NAICS
   2022 tables. None reports a failure.
7. `preservation` is `preserved`: nothing changed, missing or added, and the manifest
   (3,017 lines) is equal. `audit` reports 0 raw provenance discrepancies. The directory
   lists before and after differ only by the new `wage-microdata/` and its two runs.
8. `report.json` holds counts only. Its text values are 528 `INDNAICS` category codes, the
   contract name and five funnel step names. The literal check, `git ls-files` filtered by
   `parquet`, `csv`, `gz` and `jsonl`, prints 24 paths. All 24 are Stage 8 test fixtures
   under `tests/fixtures/acs_mapping/`. None is under `data/`, and this stage adds none. The
   owner ruled on 2026-11-19 that the check reads "no file from `data/` and none added by
   this stage". On that reading, item 8 is met.
9. No fixture result appears here as evidence.

**Top codes.** In each of 2023 and 2024 the flagged `INCWAGE` has one value in each of 51
states (50 states and DC). It equals IPUMS USA's published value for every one of these 102
cells. IPUMS also lists Puerto Rico (284,000 in both years). The core table has no Puerto
Rico row. Source: the `acs_topcodes_2023.xls` and `acs_topcodes_2024.xls` files linked from
`https://usa.ipums.org/usa/volii/top_bottom_codes.shtml` (section "Values Exceeding Top
codes, by State" of `https://usa.ipums.org/usa-action/variables/INCWAGE`), accessed
2026-11-19. Flagged rows: 18,439 (2023) and 18,937 (2024).

**Not claimed.** A headline minimum count for each category (O23), a protocol section (O24),
a panel result, and any fixture result as evidence. No output feeds embedder training,
curriculum, hard-negative mining or model selection (R8.4).
