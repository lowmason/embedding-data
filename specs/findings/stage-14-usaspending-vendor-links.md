# Stage 14 USAspending vendor links: measured replay and acceptance

A second build of the Stage 14 bundle matches the first. Run
`stage14_vendor_links_20261122_r2` (the first run) and run
`stage14_vendor_links_20261122_r2_replay` (the replay) both pass `verify`, and
`compare-runs` finds the two bundles equal. Stage 14 built the first run on 2026-11-22, and
its record is `specs/naics-evaluation-data-stage-14-findings.md`. Roadmap Stage 20 (O25,
plan 16, `specs/plans/completed/16-usaspending-vendor-links.md`) built the replay on
2026-11-22 and wrote this file.

This file does not restate the Stage 14 counts. They are in the Stage 14 findings,
sections "Full-data build" and "For the resume and O18". The two runs share one
`report.json`, so those counts hold for both runs. This file claims no more than the limits
and the "Not claimed" section state.

## Selected runs and pins

Both runs live in `data/derived/usaspending/vendor-links/`. The detached pin is the SHA-256
of `outputs.json`. `verify` needs it as `--outputs-sha256`.

| Run | File | SHA-256 |
| --- | --- | --- |
| First: `stage14_vendor_links_20261122_r2` | `outputs.json` (detached pin) | `248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be` |
| | `inputs.json` | `c3e924b696a10b97d08800062b30dd610476315156132366bbbdcc4317a47a2c` |
| | `report.json` | `040127fbb64d1dc7e2791f337506994092c4aab42abedfe3af94deff01f913d2` |
| Replay: `stage14_vendor_links_20261122_r2_replay` | `outputs.json` (detached pin) | `d08ed4cb396fae172ebde8be65fe6dfc492cb4c2731ad4308cfcf7cd55fd6055` |
| | `inputs.json` | `b3a9e1d0bd8f3d4aff24ca0d89a9053928f2ab3f8702d3c85b37b15cc8b8997f` |
| | `report.json` | `040127fbb64d1dc7e2791f337506994092c4aab42abedfe3af94deff01f913d2` |

Each bundle has 7 files: four Parquet tables, `inputs.json`, `report.json` and
`outputs.json`. The first bundle is 1,748,810 bytes. The replay bundle is 1,748,817 bytes.
The 7 extra bytes are the `_replay` suffix of the run ID in `inputs.json`.

The four Parquet files and `report.json` have the same bytes in both runs.
`inputs.json` differs, because it records the run ID and the execution. `outputs.json`
differs, because it hashes `inputs.json`. So the two pins differ.

Each command ran from the Stage 20 worktree, prefixed by `/usr/bin/time -l`, with its
standard output and standard error sent to the evidence directory (see "Where the evidence
lives"). The replay command was:

```bash
uv run --offline --locked python -m embedding_data.usaspending_vendor_links build stage14_vendor_links_20261122_r2_replay --codes-run stage4_v11_20261013_r2 --codes-outputs-sha256 15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a --snapshot 2026-11-19 --sam-month 2026-10 --data-dir /Users/lowell/Projects/embedding-data/data
```

The verifiers were:

```bash
uv run --offline --locked python -m embedding_data.usaspending_vendor_links verify stage14_vendor_links_20261122_r2 --outputs-sha256 248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked python -m embedding_data.usaspending_vendor_links verify stage14_vendor_links_20261122_r2_replay --outputs-sha256 d08ed4cb396fae172ebde8be65fe6dfc492cb4c2731ad4308cfcf7cd55fd6055 --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked python -m embedding_data.usaspending_vendor_links compare-runs stage14_vendor_links_20261122_r2 stage14_vendor_links_20261122_r2_replay --data-dir /Users/lowell/Projects/embedding-data/data
```

## Execution identity

| Run | Executing commit | `dirty` | Created (UTC) |
| --- | --- | --- | --- |
| First | `1eddb3e5f3d1e016a1f1d46245a4ebc6cc221f52` | false | 2026-11-22 19:43:48 |
| Replay | `3d0c63d67f01eaa06a08158f74a43636ad0c525a` | false | 2026-11-22 22:17:26 |

Both commits are on `main`. The replay commit is the `origin/main` merge of PR 45, from
which the Stage 20 worktree was cut. No commit landed on the Stage 20 branch before the
build.

Both runs record CPython 3.14.0 (`3.14.0 (main, Oct 14 2025, 21:10:22) [Clang 20.1.4 ]`),
63 installed distributions, the 26 files of `vendor_link_bundle.SOFTWARE_FILES` and the
`uv.lock` SHA-256 `f57c3280a7c8286711bf6804ca4c02f0a19619c9db52f33941b9c5b996cba8e5`.
`git diff --quiet 1eddb3e HEAD` over those 26 files exited 0 before each command, and each
file exists at both commits.

Stage 20 built the replay from a new worktree venv (`uv sync --locked` on the uv-managed
CPython 3.14.0, run once). The first run's recorded `software` equalled the live
`freeze_software()` three times: before its re-verification (Task 1 Step 4), before the
build (Task 3 Step 1) and before the replay's `verify` (Task 4 Step 1). That equality covers
Python, all 63 distributions, all 26 file hashes and the lock hash. The first run then
passed `verify` again from the Stage 20 checkout. So the first run verifies under the
replay's identity, which `compare-runs` alone cannot show.

The two `inputs.json` files have the same top-level keys. Only `run_id` and `execution`
differ, and in `execution` only `commit` and `created_at` differ (see Results).

## Measured cost

The host has 36 GiB of memory. `/usr/bin/time -l` measured each command. One MB here is
10^6 bytes.

| Stage | Command | Wall time | Maximum RSS |
| --- | --- | ---: | ---: |
| 14 | `build` (first run) | 29.6 s | 961 MB |
| 14 | `verify` (first run) | 28.8 s | 955 MB |
| 20 | `verify` (first run, Task 2) | 20.08 s | 925,106,176 B (925 MB) |
| 20 | `build` (replay, Task 3) | 25.83 s | 966,082,560 B (966 MB) |
| 20 | `verify` (replay, Task 4) | 24.81 s | 936,607,744 B (937 MB) |
| 20 | `compare-runs` | 0.76 s | 257,802,240 B (258 MB) |
| 20 | `embedding-data audit` | 7.34 s | 175,128,576 B (175 MB) |

`du -sk` gives 1,720 KB for each bundle, the size Stage 14 recorded for the first run.

Another session's pre-commit hook ran on the host during the replay build, its `verify`
and `compare-runs`. It was a fixture test run with 7 pytest-xdist workers, in another
worktree and on temporary data directories. It was not an acquisition or a build, so the
host rule did not stop the run. The owner chose to start the build without waiting for it
to end. The Stage 20 wall times carry that load.

## Results

**Reproduction.** Both `verify` runs exit 0 with the same `rows`:

| Table | Rows |
| --- | ---: |
| `vendor_links` | 16,614 |
| `vendor_link_marginals` | 689 |
| `vendor_link_support` | 8,307 |
| `vendor_link_pairs` | 107,994 |

These equal the Stage 14 findings ("Checks").

**Replay comparison.** `compare-runs` exits 0. Its output line is:

```json
{"equal": true, "report_equal": true, "tables": {"vendor_link_marginals": {"first_rows": 689, "schema_equal": true, "second_rows": 689, "values_equal": true}, "vendor_link_pairs": {"first_rows": 107994, "schema_equal": true, "second_rows": 107994, "values_equal": true}, "vendor_link_support": {"first_rows": 8307, "schema_equal": true, "second_rows": 8307, "values_equal": true}, "vendor_links": {"first_rows": 16614, "schema_equal": true, "second_rows": 16614, "values_equal": true}}, "trust_established": false}
```

The comparison joins the two frames by row position and counts a null against a value as a
difference, so row order counts. Equality does not authenticate either run. The two
`verify` runs do.

**The two `inputs.json` files.** `compare-runs` skips `inputs.json` (D3). A separate check
loaded both files. Its output line is:

```json
{"differing_keys": ["execution", "run_id"], "dirty": {"r2": false, "replay": false}, "equal": {"codes": true, "contracts": true, "raw": true, "registries": true, "rules": true, "sam_month": true, "snapshot": true, "software": true, "window": true}, "execution_differing_keys": ["commit", "created_at"], "execution_keys_same": true, "pass": true, "report_sha256_equal": true, "sha256": {"inputs.json": {"r2": "c3e924b696a10b97d08800062b30dd610476315156132366bbbdcc4317a47a2c", "replay": "b3a9e1d0bd8f3d4aff24ca0d89a9053928f2ab3f8702d3c85b37b15cc8b8997f"}, "report.json": {"r2": "040127fbb64d1dc7e2791f337506994092c4aab42abedfe3af94deff01f913d2", "replay": "040127fbb64d1dc7e2791f337506994092c4aab42abedfe3af94deff01f913d2"}}, "top_level_keys_same": true}
```

**Live identity before the replay's `verify`.** The identity check (Task 4 Step 1) printed:

```json
{"dependencies": 63, "project_root": "/Users/lowell/Projects/embedding-data/.worktrees/stage-20-usaspending-hardening", "python_full": "3.14.0 (main, Oct 14 2025, 21:10:22) [Clang 20.1.4 ]", "software_equal": true}
```

The checks before the first `verify` and before the build printed the same line.

**Preservation.** After the replay, `verify` and `compare-runs`:
- The manifest `data/raw/manifest.jsonl` has its baseline SHA-256
  `72232204e21ee406134e2fb3a6d8d5b50d26295af94116fcaa46d8cdaed20efe`, 1,552,347 bytes and
  3,017 lines. No line was appended. `build`, `verify` and `compare-runs` append nothing.
- The `outputs.json` SHA-256 values are unchanged: `r1`
  `c9d71dd95b717048a54a4701bf88a7cb670d59b1342adac0ce4a207267fe1610`, the first run
  `248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be` and the codes bundle
  `stage4_v11_20261013_r2` `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`.
- `vendor-links/` holds exactly `stage14_vendor_links_20261121_r1`, the first run and the
  replay, and no `.part` directory.
- The whole-tree audit (`embedding-data audit`) exits 0 with 0 raw provenance
  discrepancies.
- The Stage 20 worktree stayed clean (`git status --porcelain --untracked-files=normal`
  printed nothing) through the replay's `verify`.

## Corrections to earlier text

Two earlier texts are out of date. Neither file is edited.

1. The Status line (line 3) of `specs/naics-evaluation-data-stage-14-findings.md` says
   "Stage 14 in progress". Stage 14 completed on 2026-11-22. The roadmap's Stage 14 stamp
   and the Status line of `specs/completed/usaspending-vendor-links.md` record this.
2. The docstring (line 6) of `scripts/reconcile_usaspending_vendor_links.py` names
   `specs/usaspending-vendor-links.md`. The spec is at
   `specs/completed/usaspending-vendor-links.md`. The fix rides with the next change to the
   script (`specs/deferred_items.md`, section `15-usaspending-vendor-links`).

## Limits

- `compare-runs` skips `inputs.json` (D3), so its `equal` says nothing about software. The
  separate `inputs.json` check in Results covers that gap.
- The independent reconciler (`scripts/reconcile_usaspending_vendor_links.py`) ran on the
  first run only (Stage 14 findings, "Checks"). It did not run on the replay. The replay
  rests on `verify` and `compare-runs`, and its tables and report equal those of the first
  run.
- `stage14_vendor_links_20261121_r1` is superseded. It stays on disk, unchanged, and
  nothing cites it. `verify` refuses it, because `sam_raw.py` changed after it was built.
- D2 stays: a blank or invalid last update date makes a firm `dnb_era_record`. Its cost is
  in the Stage 14 findings ("The cost of D2").
- The family rests on one subaward snapshot (`2026-11-19`) and one monthly SAM extract
  (`2026-10`).
- The Stage 20 wall times ran beside another session's test run (see "Measured cost").

## Not claimed

- No headline minimum count (O26), no protocol section (O18) and no scoring.
- Every target keeps `size_gate_pending`.
- Agreement between two runs does not show accuracy or representativeness.
- No output feeds embedder training, curriculum, hard-negative mining or model selection
  (R8.4).
- `vendor_link_pairs.parquet` holds UEI pairs and stays on this machine.

## Where the evidence lives

- The bundles in `data/derived/usaspending/vendor-links/`.
- The `.out`, `.err` and `.rc` files of every command, the identity lines
  (`identity-1.json` to `identity-3.json`), `snapshot.json`, `snapshot-after.json`,
  `inputs-compare.json`, the manifest baseline and the plan 16 ledger (`progress.md`) in
  `/Users/lowell/.cache/embedding-data/stage-20/`, outside every checkout.
- The Stage 14 findings (`specs/naics-evaluation-data-stage-14-findings.md`), plan 15
  (`specs/plans/completed/15-usaspending-vendor-links.md`) and plan 16
  (`specs/plans/completed/16-usaspending-vendor-links.md`).
