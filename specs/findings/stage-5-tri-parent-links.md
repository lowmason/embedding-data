# Stage 5 TRI parent links: measured replay and acceptance

A second build of the Stage 5 TRI parent-link bundle matches the first. Run
`stage5_tri_parent_links_20261121_r1` (the first run) and run
`stage5_tri_parent_links_20261121_r1_replay` (the replay) both pass `verify`, and
`compare-runs` finds the two bundles equal. Stage 5 built the first run on 2026-11-21 (22:00
EST, which is 03:00 UTC on 2026-11-22, the `created_at` below), and its record is
`specs/naics-evaluation-data-stage-5-findings.md`. Roadmap Stage 18 (O12, plan 18,
`specs/plans/completed/18-tri-parent-links.md`, in `specs/naics-evaluation-data-roadmap.md`)
built the replay on 2026-11-22 and wrote this file.

This file does not restate the Stage 5 counts. They are in the Stage 5 findings, sections
"Verification" and "Counts". The two runs share one `report.json`, so those counts hold for
both runs. This file claims no more than the limits and the "Not claimed" section state.

## Selected runs and pins

Both runs live in `data/derived/epa_tri/parent-links/`. The detached pin is the SHA-256 of
`outputs.json`. `verify` needs it as `--outputs-sha256`. The processed-as-of date (the EPA
snapshot) is 2025-11-05 for both runs.

| Run | File | SHA-256 |
| --- | --- | --- |
| First: `stage5_tri_parent_links_20261121_r1` | `outputs.json` (detached pin) | `65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b` |
| | `inputs.json` | `d8fa7cac350142bad2a5f8e1be411c43da5a683f4ee9e53fac147fdb9e1ca1ed` |
| | `report.json` | `dc002222c0d9fa652f5623ef089dc324a000625d8a23fd681b3d227ed98d6a6e` |
| Replay: `stage5_tri_parent_links_20261121_r1_replay` | `outputs.json` (detached pin) | `555f6b58099da43c054d828d27048f31a9e992ee32719c7e1462c59b30919cfc` |
| | `inputs.json` | `de6d096d7c752e6b70c675d369960d5a8b82a74042ab61ef471f41fe92446d10` |
| | `report.json` | `dc002222c0d9fa652f5623ef089dc324a000625d8a23fd681b3d227ed98d6a6e` |

Each bundle has 8 files: five Parquet tables, `inputs.json`, `report.json` and
`outputs.json`. The first bundle is 1,319,169 bytes. The replay bundle is 1,319,176 bytes.
The 7 extra bytes are the `_replay` suffix of the run ID in `inputs.json` (26,506 bytes
against 26,499). `outputs.json` and `report.json` have the same size in both bundles.

The five Parquet files and `report.json` have the same bytes in both runs. `inputs.json`
differs, because it records the run ID and the execution. `outputs.json` differs, because it
hashes `inputs.json`. So the two pins differ.

Each command ran from the Stage 18 worktree, prefixed by `/usr/bin/time -l`, with its standard
output and standard error sent to the evidence directory (see "Where the evidence lives").
The replay command was:

```bash
uv run --offline --locked python -m embedding_data.tri_parent_links build stage5_tri_parent_links_20261121_r1_replay --codes-run stage4_v11_20261013_r2 --codes-outputs-sha256 15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a --processed-as-of 2025-11-05 --data-dir /Users/lowell/Projects/embedding-data/data
```

The verifiers were:

```bash
uv run --offline --locked python -m embedding_data.tri_parent_links verify stage5_tri_parent_links_20261121_r1 --outputs-sha256 65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked python -m embedding_data.tri_parent_links verify stage5_tri_parent_links_20261121_r1_replay --outputs-sha256 555f6b58099da43c054d828d27048f31a9e992ee32719c7e1462c59b30919cfc --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked python -m embedding_data.tri_parent_links compare-runs stage5_tri_parent_links_20261121_r1 stage5_tri_parent_links_20261121_r1_replay --data-dir /Users/lowell/Projects/embedding-data/data
```

The whole-tree audit was `uv run --offline --locked embedding-data audit --data-dir
/Users/lowell/Projects/embedding-data/data`.

## Execution identity

| Run | Executing commit | `dirty` | Created (UTC) |
| --- | --- | --- | --- |
| First | `786ebcc983a5fa96388455855d1377370f7cbbd5` | false | 2026-11-22 03:00:06 |
| Replay | `0f517d7bfc75c871ce2ff125b59274d9c07f0fe1` | false | 2026-11-22 23:16:43 |

Both commits are on `main`. The replay commit is the `origin/main` merge of PR 48, from which
the Stage 18 worktree was cut. No commit landed on the Stage 18 branch before the build. The
worktree later took `origin/main` (PR 49, one docs file) by fast-forward, after Task 4 ended.

Both runs record CPython 3.14.0 (`3.14.0 (main, Oct 14 2025, 21:10:22) [Clang 20.1.4 ]`), 63
installed distributions, the 24 files of `tri_bundle.SOFTWARE_FILES` and the `uv.lock` SHA-256
`f57c3280a7c8286711bf6804ca4c02f0a19619c9db52f33941b9c5b996cba8e5`. `git diff --quiet 786ebcc
HEAD` over those 24 files exited 0 before the first run's re-verification (Task 1), before the
build (Task 3) and before the replay's `verify` (Task 4). It also exited 0 for `origin/main`
(`fd43236`) before the fast-forward.

Stage 18 built the replay from a new worktree venv (`uv sync --locked` on the uv-managed
CPython 3.14.0, run once). The first run's recorded `software` equalled the live
`freeze_software()` three times: before its re-verification (Task 1 Step 4), before the build
(Task 3 Step 1) and before the replay's `verify` (Task 4 Step 1). That equality covers Python,
all 63 distributions, all 24 file hashes and the lock hash. The first run then passed `verify`
again from the Stage 18 checkout. So the first run verifies under the replay's identity, which
`compare-runs` alone cannot show.

The two `inputs.json` files have the same top-level keys, and those keys are
`tri_bundle.INPUT_FIELDS`. Only `run_id` and `execution` differ, and in `execution` only
`commit` and `created_at` differ (see Results).

## Measured cost

The host has 36 GiB of memory. `/usr/bin/time -l` measured each Stage 18 command, and the MB
beside each byte count is 10^6 bytes. The Stage 5 values come from the Stage 5 findings
("Full-data build"). Stage 5 recorded no `verify`, `compare-runs` or `audit` cost.

| Stage | Command | Wall time | Maximum RSS |
| --- | --- | ---: | ---: |
| 5 | `build` (first run) | 3.52 s | 1,589,870,592 B (1,590 MB) |
| 18 | `verify` (first run, Task 2) | 4.64 s | 1,506,492,416 B (1,506 MB) |
| 18 | `build` (replay, Task 3) | 4.83 s | 1,474,576,384 B (1,475 MB) |
| 18 | `verify` (replay, Task 4) | 3.14 s | 1,508,884,480 B (1,509 MB) |
| 18 | `compare-runs` | 0.62 s | 352,403,456 B (352 MB) |
| 18 | `embedding-data audit` | 6.52 s | 175,669,248 B (176 MB) |

`du -sk` gives 1,308 KB for each bundle, the size Stage 5 recorded for the first run.

The host-rule check (`pgrep -fl 'embedding_data|embedding-data'`) ran just before each
command. It listed another session's test run before four of the five commands:
- Before the first run's `verify` (Task 2) and before the build: a pre-commit hook of another
  session, running pytest (`-m 'not network and not slow'`) with 7 pytest-xdist workers on
  temporary data directories. The list at the build gate is saved as `pgrep-build.txt`
  (23:14:44 UTC), and the list just before launch as `pgrep-build-prelaunch.txt` (23:16:34
  UTC). The ledger summarizes the Task 2 list (process IDs and command). It reached the owner
  late, at the build gate, after that `verify` had run.
- Before the replay's `verify`: only the `pgrep` command's own `tee` (23:17:17 UTC). The host
  was idle when that check ran.
- Before `compare-runs` (23:17:32 UTC) and before `audit` (23:17:49 UTC): a Stage 19 session's
  pytest run. A `ps` call in the session showed that it ran one test file
  (`tests/test_measure_acs_wage_minimum_earners.py`) and was a few seconds old. The saved
  `pgrep` lines are cut to a fixed width and do not hold the file name or the process age.

None of these was an acquisition or a build, so the host rule did not stop the run. The owner
chose to start the build without waiting for the hook to end ("Go now (loaded)") and confirmed
that no other stage's acquisition or build was running and that no Stage 9 freeze window was
open.

The saved lists show an overlap with the command itself for the Task 2 `verify` only. The hook
was listed before it started and again at 23:14:44 UTC, after it ended at 23:14:31 UTC. For the
build, `compare-runs` and `audit`, no list was taken after the command ended. So the saved
evidence does not show whether the other job was still running, and those three wall times may
carry load. The replay's `verify` started on an idle host. No Stage 18 wall time is a
controlled, unloaded baseline.

## Results

**Reproduction.** Both `verify` runs exit 0 with the same `processed_as_of` (2025-11-05) and
the same `rows`:

| Table | Rows |
| --- | ---: |
| `tri_parent_links` | 14,204 |
| `tri_parent_link_marginals` | 405 |
| `tri_parent_link_support` | 14,204 |
| `tri_parent_industries` | 7,777 |
| `tri_facility_years` | 65,464 |

These equal the Stage 5 findings ("Verification").

**Replay comparison.** `compare-runs` exits 0. Its output line is:

```json
{"equal": true, "report_equal": true, "tables": {"tri_facility_years": {"first_rows": 65464, "schema_equal": true, "second_rows": 65464, "values_equal": true}, "tri_parent_industries": {"first_rows": 7777, "schema_equal": true, "second_rows": 7777, "values_equal": true}, "tri_parent_link_marginals": {"first_rows": 405, "schema_equal": true, "second_rows": 405, "values_equal": true}, "tri_parent_link_support": {"first_rows": 14204, "schema_equal": true, "second_rows": 14204, "values_equal": true}, "tri_parent_links": {"first_rows": 14204, "schema_equal": true, "second_rows": 14204, "values_equal": true}}, "trust_established": false}
```

`compare-runs` compares the tables in row order, so row order counts. It first checks that each
bundle matches its own `outputs.json` inventory, but it does not check a detached pin. So
equality does not authenticate either run. The two `verify` runs do.

**The two `inputs.json` files.** `compare-runs` skips `inputs.json`. A separate check loaded
both files. Its output line is:

```json
{"commit": {"r1": "786ebcc983a5fa96388455855d1377370f7cbbd5", "replay": "0f517d7bfc75c871ce2ff125b59274d9c07f0fe1"}, "created_at": {"r1": "2026-11-22T03:00:06.329554+00:00", "replay": "2026-11-22T23:16:43.093701+00:00"}, "differing_keys": ["execution", "run_id"], "dirty": {"r1": false, "replay": false}, "equal": {"codes": true, "contracts": true, "layouts": true, "processed_as_of": true, "raw": true, "rules": true, "software": true, "window": true}, "execution_differing_keys": ["commit", "created_at"], "execution_keys_same": true, "pass": true, "report_sha256_equal": true, "sha256": {"inputs.json": {"r1": "d8fa7cac350142bad2a5f8e1be411c43da5a683f4ee9e53fac147fdb9e1ca1ed", "replay": "de6d096d7c752e6b70c675d369960d5a8b82a74042ab61ef471f41fe92446d10"}, "report.json": {"r1": "dc002222c0d9fa652f5623ef089dc324a000625d8a23fd681b3d227ed98d6a6e", "replay": "dc002222c0d9fa652f5623ef089dc324a000625d8a23fd681b3d227ed98d6a6e"}}, "top_level_keys_equal_input_fields": true, "top_level_keys_same": true}
```

**Live identity before the replay's `verify`.** The identity check (Task 4 Step 1) printed:

```json
{"dependencies": 63, "project_root": "/Users/lowell/Projects/embedding-data/.worktrees/stage-18-tri-hardening", "python_full": "3.14.0 (main, Oct 14 2025, 21:10:22) [Clang 20.1.4 ]", "software_equal": true}
```

The checks before the first `verify` and before the build printed the same line.

**Preservation.** After the replay, `verify`, `compare-runs` and `audit`:
- The manifest `data/raw/manifest.jsonl` has its baseline SHA-256
  `72232204e21ee406134e2fb3a6d8d5b50d26295af94116fcaa46d8cdaed20efe`, 1,552,347 bytes and
  3,017 lines. No line was appended. `build`, `verify` and `compare-runs` append nothing.
- The `outputs.json` SHA-256 values are unchanged: the first run
  `65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b` and the codes bundle
  `stage4_v11_20261013_r2` `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`.
- `parent-links/` holds exactly `stage5_tri_parent_links_20261121_r1` and the replay, and no
  `.part` directory.
- The three raw files under `raw/epa_tri/basic/` keep their paths and SHA-256 values, and no
  other file is there.
- The whole-tree audit exits 0 with 0 raw provenance discrepancies.
- `git status --porcelain --untracked-files=normal` in the Stage 18 worktree printed nothing
  before the build (Task 3), right after the build and after the audit. The replay's
  `inputs.json` records `dirty: false`.

## Corrections to earlier text

Two earlier texts are out of date. Neither file is edited.

1. The "Partial owners" limit of the Stage 5 findings cites "spec 470–474" and calls the
   reading a ruling marked unclear. The owner settled it on 2026-11-21. The spec
   (`specs/completed/tri-parent-links.md`, lines 474–479, marked *(owner, plan 13,
   2026-11-21)*) says that an excluded facility-year belongs to each standardized parent name
   that it lists, else to `facility:<TRIFD>`. The build and the reconciler use that reading.
   How many `naics_*` facility-years name more than one parent is still not measured.
2. The docstring (line 3) of `scripts/reconcile_tri_parent_links.py` names
   `specs/tri-parent-links.md`. The spec is at `specs/completed/tri-parent-links.md`. The script
   is not in `tri_bundle.SOFTWARE_FILES`, so `verify` does not hash it. The fix rides with the
   next change to the script. → item: 18-tri-parent-links — 2026-11-22

## Limits

- `compare-runs` does not compare `inputs.json`, so its `equal` says nothing about software
  or raw citations. The separate `inputs.json` check in Results covers that gap.
- The independent reconciler (`scripts/reconcile_tri_parent_links.py`) ran on the first run
  only. It did not run on the replay. The replay rests on `verify` and `compare-runs`, and its
  tables and report equal those of the first run. The reconciler's "equal" does not cover the
  report fields that the Stage 5 findings list under "Reconciler coverage".
- E8 time basis: EPA's standardized parent names the current owner, not the owner at the end
  of each reporting year (Stage 5 findings, "Limits").
- The RY2022 foreign-parent columns hold data but stay unmapped.
- The family rests on one EPA snapshot (2025-11-05). `acquire` refuses every EPA file, because
  EPA's endpoint sends no `Content-Length`. A later snapshot enters through `import-file` and a
  new run.
- Another session's test run was on the host before four of the five Stage 18 commands. The
  saved evidence shows an overlap for the Task 2 `verify` only (see "Measured cost").

## Not claimed

- No headline minimum count (O13), no protocol section (O17) and no scoring.
- Every target keeps `size_gate_pending`.
- Agreement between two runs does not show accuracy or representativeness.
- No output feeds embedder training, curriculum, hard-negative mining or model selection
  (R8.4).
- The outputs publish no D&B number.

## Where the evidence lives

- The bundles in `data/derived/epa_tri/parent-links/`.
- The `.out`, `.err` and `.rc` files of every command, the identity lines
  (`identity-1.json` to `identity-3.json`), `snapshot.json`, `snapshot-after.json`,
  `inputs-compare.json`, the `pgrep` lists, the manifest baseline and the plan 18 ledger
  (`progress.md`) in `/Users/lowell/.cache/embedding-data/stage-18/`, outside every checkout.
- The Stage 5 findings (`specs/naics-evaluation-data-stage-5-findings.md`), plan 13
  (`specs/plans/completed/13-tri-parent-links.md`) and plan 18
  (`specs/plans/completed/18-tri-parent-links.md`).
