# ACS targets: first full build under a memory guard

Status: APPROVED (2026-11-23, owner: "Approve, 48 h"). Written 2026-11-23.

This is the stage spec for Stage 9 of `specs/naics-evaluation-data-roadmap.md` (Track F,
outcome O15). It does not replace the approved ACS targets spec `specs/acs-targets.md` or
change any target that spec defines. It decides how this stage finishes plan 9: what the
first full build must prove, how it runs, and what happens if it fails.

> Next step: writing-plans, in a fresh session, against this file.

## Design provenance

A brainstorming session with the owner on 2026-11-23, in this repository at `b78d781`, then
`32f3ccf`. The inputs read were:

- the Stage 9 entry of `specs/naics-evaluation-data-roadmap.md` and its "Choices made";
- `specs/findings/stage-9-acs-targets.md` (r1 and the small diagnostics only);
- `specs/plans/9-acs-targets.md`, Tasks 10 and 11;
- in the worktree `/Users/lowell/.codex/worktrees/acs-targets-design/embedding-data`, read
  only: the untracked `specs/plans/10-acs-targets.md`, the 12 commits of branch
  `codex/acs-targets-design` that main lacks (`6a30106` to `1a6377d`), and the gitignored
  ledgers `.sdd/9-acs-targets/progress.md` and `.sdd/10-acs-targets/` (among them
  `progress.md`, `first-launch-proposal.md`, `disk-design-proposal.md` and the probe 1 to 8
  authorizations and results);
- the data root, through metadata only: `data/raw/acs/`, the Stage 8 run directory, and the
  r1 to r3 paths under `data/derived/acs/targets/` and `data/derived/acs/target-controls/`.

Recon results that shaped the design:

- The Codex branch merges into main with no conflict (`git merge-tree`). Of the 66 files in
  `acs_target_inputs.SOFTWARE_FILES`, only the three it changes differ from main:
  `acs_target_estimation.py`, `acs_target_projection.py` and `acs_target_tables.py`. No other
  module or script outside Stage 9 names these three, so no other selected run hashes them.
- `pyproject.toml` and `uv.lock` are the same on the branch and on main.
- `verify_bundle` calls `derive_tables` again (`acs_target_bundle.py:388`). A verify costs
  about as much as a build.
- Every `/private/tmp/stage9*` directory is gone. The probe guardian, its drivers and the
  probe 6 kept set were deleted outside this repository. The evidence paths under
  `/private/tmp` that the old finding cites no longer exist.
- All inputs are on this machine: the three IPUMS ACS deliveries (1.5 GB) and the Stage 8
  run (3.4 GB). Stage 9 downloads nothing.

## Owner decisions (2026-11-23)

1. **Acceptance scope A.** Stage 9 needs one build on real data and a passing `verify` with
   its detached pin, as the roadmap Exit says. Replay, `compare-runs`, the six-group
   independent reconciliation and the freeze and preservation gate leave this stage. A later
   hardening outcome takes them, as O12 and O25 did for TRI and USAspending. (Owner: "A".)
2. **Failure rule 1.** The stage makes one attempt. If the guarded build or its `verify`
   fails, the stage stops. The findings file records where and why. The owner then chooses:
   a reviewed fix and a new run, retiring plan 9, or a redesign. No fix is made inside this
   stage without that choice. (Owner: "1".)
3. **Approach I.** The build runs directly under a new guard wrapper, with no probe first.
   (Owner: "I".)
4. **Deadline 48 h** each for the build and for `verify`, and approval of this spec with the
   calls marked "Claude's call". (Owner: "Approve, 48 h".)

## Intent

O15 asks for the ACS targets on real data: staffing patterns, the workplace area mix, and
commuting and migration flows in the shared schema. Plan 9 built the software in October
2026. Three full builds then failed on memory, and plan 10 and seven probes fixed the costs
they found. No run has yet gone from start to a published bundle on the final code.

This stage has two jobs. First, it writes the cause of each failed build into git, because
that history now exists only in gitignored ledgers on one disk. Second, it runs the final
code once, guarded, and either publishes a verified bundle or stops with a measured reason.

## Goals, non-goals and anti-goals

Goals:

- The cause of r1, r2 and r3 is written down with its evidence, in
  `specs/naics-evaluation-data-stage-9-findings.md`, before the new build starts.
- The 12 Codex commits reach main unchanged, through this stage's branch.
- One guarded build publishes a bundle, and `verify` with its detached pin passes.
- The findings file records the run ID, the detached pin, and the wall time, maximum RSS and
  bundle size of the build, and the same three figures for its `verify`.

Non-goals:

- Replay, `compare-runs`, the independent reconciliation (`scripts/reconcile_stage9.py`) and
  the freeze and preservation gate (decision 1).
- A probe before the build (decision 3).
- Any change to a target, product, rule, tolerance, schema or refusal of `specs/acs-targets.md`.
- Worker profiles, CPS cross-sections, the size gate and comparators (old Stages 12 and 13),
  and the ACS protocol section (O20). These stay where the roadmap put them.
- A streaming redesign of the estimator. It is one of the owner's options after a failure,
  not work of this stage.

Anti-goals (a failure even if a bundle appears):

- A run that changes or removes an r1, r2 or r3 path, or reuses one of their run IDs.
- A run that changes a byte of `pyproject.toml`, `uv.lock` or any file another selected run
  hashes. Stage 5, 14 and 17 `verify` would then refuse their runs.
- A run whose processes do not match the Stage 9 `pgrep` pattern, so other sessions cannot
  see it and commit or run full tests while it holds the host.
- A second attempt, or a fix, started inside this stage without the owner's choice.
- A claim of scientific acceptance. The bundle is verified, not reconciled.

## Measured facts: the three failed builds

This summary comes from the ledgers. The findings file restates each figure from its source
and cites the file and line, or marks it as lost where its source was in `/private/tmp`.

| Run | Date | Guard | Outcome | Cause, as far as the evidence goes |
|---|---|---|---|---|
| `stage9_acs_targets_20261019_r1` | 2026-10-20 | none | Exit 137 after 5,084.6 s. Maximum child RSS 26,600,947,712 bytes | A macOS memorystatus kill of `python3.14` (52,441 MB compressed accounting, kernel log hash in the old finding). Small diagnostics on the first 100,000 and 500,000 rows narrowed the growth to the two-plan native cell and denominator `collect_all` (`acs_target_estimation.py:110`): 500,000 rows passed 9.26 GiB there. On the Codex tip, `derive_tables` calls `_aggregate_native_spilled` (`acs_target_tables.py:911`, `:926`), and no production code calls `aggregate_native`, which holds that `collect_all`. Probes 1 to 7 passed native aggregation under the guard. The exact operator is unproven |
| `stage9_acs_targets_20261021_r2` | 2026-10-21 | 24 GiB physical footprint, one thread, default morsel size | Guard stop at 24.19 GiB after 218.9 s, empty scratch | Input selection. A selector-only diagnostic at the default morsel size (100,000) crossed 24.03 GiB at 221.9 s inside `select_targets`. The same diagnostic with `POLARS_IDEAL_MORSEL_SIZE=8192` finished in 530 s at 16.45 GiB. The exact operator is unproven |
| `stage9_acs_targets_20261021_r3` | 2026-10-21 | 24 GiB, one thread, morsel 8192, 8 h | Guard stop at 25.11 GiB after 17,316 s (4.8 h) | The replicate sink of the first county industry product (`1cf742bc…`). Its phases were slow: native binding about 10 min, wide-to-long 86 min, a per-county validator about 24 min, estimation 15 min. Plan 10 Tasks 1 to 5 targeted these |

What followed r3, all on synthetic data or under `acceptance=false`:

| Item | Commit | Result |
|---|---|---|
| Plan 10 Tasks 1–5: slice conversion, one-pass validator, vectorized reader, checked concatenation, shared native binding | `6a30106`–`f85d6bd` | Synthetic gates met, reader at 79.3 s against an 80 s bound (D8) |
| Probe 1, product C | `f85d6bd` | Passed. Compute 44 min, compute peak 14.90 GiB, global peak 17.78 GiB in `select_targets` |
| Probe 2, four units | `f85d6bd` | Guard stop at 24.54 GiB after 5,973 s: a full sort in the `allocation_residuals` sink of an MSA product |
| Plan 10 Task 7: ordered residual sink | `55921b5` | Fixes probe 2 |
| Probe 3, four units | `55921b5` | Passed. Compute peaks 14.57–16.47 GiB |
| Probe 4, 11 light units and occupation group `ae8af693` | `55921b5` | Production refusal `prospective-writer-footer-bytes` after 14,020 s |
| O1, footer bound | `520d49f` | Fixes probe 4 |
| Probe 5 | `520d49f` | Assembly deadline after 16,766 s |
| A1, assembly by fragment row runs | `65e7896` | Fixes probe 5 |
| Probe 6, occupation group | `65e7896` | Passed. 11,302 s, compute peak 17.34 GiB, 96.79 GiB of uncompressed product files |
| C1, one ordered file per table | `6a6e14a` | — |
| Probe 7, assembly and tail on probe 6's files | `6a6e14a` | Passed. 5,465 s, peak 3.18 GiB |
| D1, ZSTD compression of merged outputs | `4fb8868` | Synthetic ratio 36 times. Real ratio unmeasured |
| Probe 8, four occupation groups | `4fb8868` | Approved 2026-10-31. Not launched: on 2026-11-01 its pre-launch check found probe 4 tooling deleted. Owner: "Not now" |
| Slow marker for one test | `1a6377d` | — |

The roadmap's "eight probes" are these probes 1 to 8, of which seven ran.

Open risks that only the full build can measure:

- **Memory.** Six heavy groups never ran: three occupation and three industry groups of the
  `private_wage_salary` universe and the `sensitivity` policy. Probe 6 inferred about
  20.8 GiB for a group 1.2 times its size. That is under the 24 GiB guard.
- **Disk.** Without compression the build would need about 725 GiB. D1 keeps it under the
  409 GiB free today if real data compresses better than about 2 times.
- **Time.** About 20–25 h for the build and about the same for `verify`, extrapolated from
  probes 3 to 7 (`first-launch-proposal.md`, section 2).

## Approaches

Considered with the owner on 2026-11-23:

| Approach | Trade-off | Outcome |
|---|---|---|
| I. Guarded build directly | A small new wrapper. A late failure loses up to about a day of host time, but records where it stopped | **Picked by the owner** |
| II. Rebuild probe 8, then the guarded build | About 12 h more and the most tooling. Measures 3 of the 6 unmeasured heavy groups and the real compression ratio first | Not picked: rule 1 already caps the loss at one attempt, and the build measures more |
| III. The CLI unguarded, as plan 9 Step 2 | No tooling. A kernel kill runs no cleanup, so hundreds of GiB of scratch would stay in the data root, as r1's did | Ruled out |

Acceptance scopes B (plan 9 Task 10 in full) and C (A plus one independent reconciliation)
were also considered. B costs about 80–100 h and a freeze window that blocks every other
session's production writes, and the frozen preservation checker refuses any retained `.part`
path, so it would always fail on the r1 to r3 leftovers. C brings the freeze window back.

## Design

### 1. Land the code

A new branch from main merges `codex/acs-targets-design` as it is. The Codex branch and its
worktree stay unchanged. The merge brings the 12 commits and nothing else. The branch then
adds this stage's own files (below) and reaches main through one PR. Pushing the branch puts
the 12 Codex commits on GitHub for the first time. They hold code and tests only, no data.
The PR merges with a merge commit, never a squash or a rebase, because the old finding, the
ledgers and this spec cite the Codex commit hashes.

This stage adds no module under `src/embedding_data/`. It changes no file in
`acs_target_inputs.SOFTWARE_FILES`, no frozen module, no acceptance script and neither
`pyproject.toml` nor `uv.lock`.

Plan 10 enters git as `specs/plans/completed/10-acs-targets.md`, its text unchanged under a
new status line that says its tasks shipped in the merged commits and that this stage
replaces its open checkpoints. Plan 9 retires at stage completion with a note that this
spec's plan replaced its Tasks 10 and 11. *(Claude's call: both plans are history the
roadmap names; neither should stay "live".)*

### 2. The guard wrapper

One new script, `scripts/stage9_guard.py`, with tests in `tests/test_stage9_guard.py`. It
runs the unchanged `acs_targets build` or `acs_targets verify` command under supervision.
It uses the standard library only.

Two processes:

- **The supervisor** starts the child, samples it and stops it if a limit is reached. It
  never imports Polars or the estimator.
- **The child** installs a SIGTERM handler that raises an exception, then calls the same
  unchanged entry functions that the `acs_targets build` and `verify` commands call, with the
  same arguments. The exception unwinds the build's own `try` and `TemporaryDirectory`, so
  the build removes its scratch and staging as it does for any failure. The child's command
  line contains `embedding_data.acs_targets`, so the Stage 9 `pgrep` pattern finds it. The
  child exits if its supervisor dies.

The CLI's `_invoke` (`acs_targets.py:21-29`) turns every exception into the one line
`ACS target validation failed.`, because a message can hold raw delivered values. The child
keeps that line on stderr, and it also records the exception's class, its `errno` if it is
an `OSError`, and its traceback frames (file, line, function), with no message text. That
separates a footer refusal, an `ENOSPC`, a closure error and a guard stop without exposing
a value. *(Claude's call.)*

The child refuses to start in a worktree that is not clean. The supervisor records `HEAD` and
`git status --porcelain` at launch and at exit in `result.json`. The bundle's own
`inputs.json` records file hashes but no commit, and adding one would change a hashed file.
*(Claude's call.)*

Run profile, the one r3 and the probes used: `POLARS_MAX_THREADS=1` and
`POLARS_IDEAL_MORSEL_SIZE=8192`. The child runs from the project venv's Python directly, not
through `uv run`, so the measured process is the build itself.

Stop rules *(Claude's call, set from the probes)*:

| Limit | Value | Action |
|---|---|---|
| Physical footprint | 24 GiB | SIGKILL at once |
| Free disk on the data volume, soft | under 50 GiB | SIGTERM, then wait up to 2 h for the child to exit |
| Free disk on the data volume, hard | under 20 GiB | SIGKILL |
| Wall clock | 48 h for `build`, 48 h for `verify` | SIGTERM, then wait up to 2 h |
| Grace period of a SIGTERM ends | 2 h | SIGKILL |

Memory keeps the 24 GiB limit of r2, r3 and all seven probes, so the new run is comparable
with them. The largest peak measured is 18.66 GiB (probe 4, input selection), and probe 6
inferred about 20.8 GiB for the largest unmeasured group. There is no soft memory stop: Python
runs a signal handler only when the current Polars call returns, and single phases have run
for 86 min, so a soft memory stop would almost always end in a kill anyway.

The wall-clock limit is a host-time budget, not a technical setting. The 20–25 h estimate
scales assembly linearly from probe 7, which covered 4 of the 50 products. The near-quadratic
growth that probe 5 found was in the assembly method that A1 replaced, and nothing has
measured the new method's growth at full scale. Under rule 1, a deadline stop ends the stage
with nothing published. 48 h is about twice the estimate. *(Owner, 2026-11-23: "Approve,
48 h".)*

Disk and time stops send SIGTERM and wait, because a clean exit removes the build's scratch
and a kill does not. A real `ENOSPC` raises an exception, and the build's cleanup handles it.
The two floors protect the host and other sessions, not the build. *(Claude's call, set from
the probes.)*

After a SIGKILL, the run's scratch and `.part` stay on disk, as r1 to r3's did. The
supervisor never removes them. Removal is a cleanup that needs the owner's go-ahead.

Measurements, written to a control directory outside the bundle:

| Figure | How it is measured |
|---|---|
| Wall time | Monotonic clock, from the child's start to its reaping |
| Maximum RSS | `ru_maxrss` of the child from `os.wait4` (bytes on macOS) |
| Peak physical footprint | The largest 250 ms sample of `ri_phys_footprint` from `proc_pid_rusage`, through `ctypes`. This is the guard metric r2 and r3 used |
| Disk low point | The smallest free-space sample of the data volume, every 30 s |
| Bundle size | The exact byte sum of the eleven published files, and their count |
| Outcome | Exit status, signal, stop reason and the last phase reached |

The control directory is `data/derived/acs/target-controls/<run_id>-guard/` for the build
and `<run_id>-verify-guard/` for `verify`. It holds the samples (JSON lines), the child's
stdout and stderr, and one `result.json`. It never holds source rows. The detached pin is the
SHA-256 of the published `outputs.json`, computed by the supervisor after the build exits,
not read from the build's response.

### 3. Run sequence

1. **Software ready.** The branch passes the full pytest suite, every Behave scenario, Ruff and
   `uv lock --check` on the exact commit that will run. The wrapper passes its own tests and a
   synthetic dry run: a guarded build and `verify` of the V12 fixture chain in a temporary data
   root, plus forced soft stop, hard stop, disk-floor and deadline stops that leave no scratch
   or (for the hard stop) only the paths a SIGKILL leaves.
2. **Cause first.** The findings file's cause section (above, restated from sources) is
   committed before the build starts, as the Exit orders.
3. **Host ready.** A dedicated worktree, clean, at that commit. Never the shared main checkout,
   because another session's branch switch there would change the executing files during a
   day-long run. The `pgrep` check prints nothing. No other session runs a full-data build or
   an acquisition. The host stays awake (`caffeinate -i -s` on the supervisor). Free disk is at
   least 350 GiB. *(Claude's call: with the 50 GiB soft floor, that leaves room for D1 at a
   real compression ratio of about 2.5 times or better. 409 GiB was free on 2026-11-23. If
   less than 350 GiB is free, the stage stops before launch and asks the owner.)*
4. **Build.** After the owner's go-ahead, one guarded `build` with fresh run ID
   `stage9_acs_targets_<YYYYMMDD>_r4` (the launch date; the next free `rN` if occupied) and the
   pinned upstreams of plan 9 Task 10 Step 2. The build authenticates the Stage 8 run itself, so
   the separate Stage 8 verifiers are not run. *(Claude's call: they add about 12 min and prove
   nothing the build does not.)*
5. **Verify.** After the build succeeds and the owner gives a second go-ahead, one guarded
   `verify` with the detached pin.
6. **Light checks.** `embedding-data audit --data-dir …` reports zero discrepancies. The raw
   manifest at the end starts with the exact bytes it had before the build, and no appended
   line names a path this run wrote. Other sessions may append in between, so the check is a
   prefix, not equality.
7. **Record.** The findings file gets the run section. The Stage 9 paragraphs of `CLAUDE.md`
   and `README.md` name the run, its pin and the build invocation, and drop the stale
   "Task 10 remains in progress" text.

If step 4 or 5 fails, the stage stops (decision 2). The findings file records the run ID, the
stop reason, the last phase, the measurements and what the failed run left on disk. Leftover
scratch stays until the owner says otherwise. Steps 6 and 7 still run.

### 4. The findings file

`specs/naics-evaluation-data-stage-9-findings.md`, separate from the old
`specs/findings/stage-9-acs-targets.md`, which stays unchanged. Sections:

1. Cause of the three failed builds: one subsection for each run, with the outcome, the
   evidence (file, line and hash where it still exists) and what stays unproven.
2. What followed: the plan 10 tasks, the fixes and the probes, as in the tables above.
3. Evidence that is lost: the `/private/tmp` paths and what they held.
4. The run: run ID, detached pin, executing commit with its clean status, the measurements of build
   and `verify`, the disk low point, and the per-product target row counts from `report.json`
   (aggregates only).
5. What is not claimed: no replay, no independent reconciliation, no preservation gate, no
   scientific acceptance, every target `size_gate_pending`, no training use (R8.4).
6. The limits of `specs/acs-targets.md` that bind every reader, by reference.

## Constraints

- Every command passes `--data-dir /Users/lowell/Projects/embedding-data/data`.
- One full-data build at a time across all sessions, and one acquisition at a time.
- Before every commit, every full pytest run and every full-data command, run
  `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'` and stop if it
  prints anything. While the guarded build or `verify` runs, this check stops other sessions,
  which is intended.
- Each production write needs the owner's go-ahead: the build and the `verify` (both write
  guard controls under `data/derived/`) and any later cleanup.
- Preserve every r1 to r3 path and control. Never reuse their run IDs.
- The guarded run opens no Stage 9 freeze window: this stage takes no freeze. The Stage 10, 14
  and 17 rules in `CLAUDE.md` ask other sessions to confirm that no window is open. Step 7's
  `CLAUDE.md` edit says that Stage 9's first build took none. The one-build-at-a-time rule and
  the `pgrep` check still apply while it runs.
- Every `.py` file under `scripts/` and `tests/` is part of the inventory that a later freeze
  records (`stage9_independent_io.software`). The new wrapper and its tests join it, which is
  expected and changes no selected run.
- No change to `pyproject.toml`, `uv.lock`, any frozen module or any acceptance script.
- Source rows never leave this machine or enter git. The controls and the findings hold
  aggregates only.
- The targets keep every limit of `specs/acs-targets.md`: literal factor-1 weights, Decimal
  native sums, supported canonical leaves, workplace-only allocation, conditional SEs, separate
  geographic frames, `size_gate_pending`, and no training, mining or model selection (R8.4).

## Verification: observable outcomes

1. Main contains the 12 Codex commits with the same tree content, and the Codex branch's
   head is still `1a6377d`.
2. The full suite and Behave pass on the commit that ran. The supervisor's `result.json`
   records that commit as `HEAD` with an empty `git status --porcelain`, at launch and at
   exit.
3. The wrapper's tests show each stop rule firing, the child matching the `pgrep` pattern,
   a SIGTERM stop leaving no scratch, and the failure record holding no exception message.
4. The cause section is in git before the build's start time.
5. Either: `data/derived/acs/targets/<run_id>/` holds eleven files, and the guarded `verify`
   with the supervisor's detached pin exits 0 with status verified. Or: the findings file
   records the failure and the owner's choice.
6. The findings file states the run ID, the pin, and the wall time, maximum RSS and bundle
   size, measured as section 2 defines them.
7. The raw audit reports zero discrepancies, and the manifest prefix check passes.
8. The r1 to r3 paths have the same names and sizes as before.

## Left to the builder

- The wrapper's internal structure, its event names and the exact `ctypes` binding.
- How the tests force each stop without a real 22 GiB process.
- The dry-run fixture's size, within the existing V12 chain.
- The wording of the plan 9 and plan 10 status notes.
- The order of the PR and the run, provided the run executes from a clean commit and the PR
  merges the same commit or a descendant that changes no executing file.

## Rollout

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 9

On plan completion, tick the stage and re-validate later stages against what shipped. Do not
tick Stage 9 on a published bundle alone: `verify` must pass, or the owner must retire plan 9
and the findings file must say so. The next roadmap resume should add the deferred hardening
(replay, `compare-runs`, independent reconciliation, preservation) as a new Track F outcome
before O20.
