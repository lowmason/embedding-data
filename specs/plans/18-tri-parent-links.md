# TRI Parent Links Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Stage 5's TRI parent-link bundle an exact replay check, a long-form acceptance
finding and README and CLAUDE.md run pins (O12).

**Architecture:** No code changes. A controller runs the existing offline commands of
`python -m embedding_data.tri_parent_links` from a new worktree whose venv reproduces the
software record of run `stage5_tri_parent_links_20261121_r1`. It re-verifies `r1`, builds one
replay with the same arguments, verifies the replay, compares the two runs and their
`inputs.json` files, checks preservation, then writes the finding and the pins.

**Tech Stack:** Python 3.14.0 (uv-managed), uv, the Stage 5 command group, `/usr/bin/time -l`, `du`.

**Spec:** `specs/completed/tri-parent-links.md`, for the rules and the command contract. Its
Out of scope (lines 70–71) leaves the replay, the full-data `compare-runs`, the long-form
finding and the run pins to O12, and lines 755–756 defer the README and `CLAUDE.md` pins to
O12. The scope of this plan is the roadmap's Stage 18 entry (Objective, Consumes, Produces,
Exit), which the owner approved on 2026-11-22.

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 18 — on plan completion, tick the stage and re-validate later stages against what shipped.

Scope: O12. Leaves out the TRI headline minimum count (O13), the TRI protocol section (O17)
and the R8.4 training-role amendment (roadmap, Stage 18 `Leaves out`).

Process: the controller runs every task itself, inline, because each task is an owner gate
or a command whose output decides the next step. No subagent is dispatched for a task.

## Global Constraints

- **Names.** `ROOT` is `/Users/lowell/Projects/embedding-data/data`. `W` is
  `/Users/lowell/Projects/embedding-data/.worktrees/stage-18-tri-hardening`, on branch
  `stage-18-tri-hardening`, cut from `origin/main` after this plan merges. `E` is
  `/Users/lowell/.cache/embedding-data/stage-18`, outside every checkout. `P` is
  `ROOT/derived/epa_tri/parent-links`. `R` is `ROOT/raw/epa_tri/basic`.
- **Selected run.** `stage5_tri_parent_links_20261121_r1`, detached pin
  `65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b`, snapshot (EPA
  "processed as of") 2025-11-05, built at `786ebcc` with `dirty: false`.
- **Replay run ID.** `stage5_tri_parent_links_20261121_r1_replay` (Settled Default 2).
- **Build arguments.** `--codes-run stage4_v11_20261013_r2 --codes-outputs-sha256
  15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a --processed-as-of
  2025-11-05 --data-dir /Users/lowell/Projects/embedding-data/data`.
- **Raw files.** `R/2022/2025-11-05/2022_us.csv` (SHA-256 `baba5a2ab530d1d02fe1019bdddcd1aa2621cca245abfdc5de71562ce0dad5ae`),
  `R/2023/2025-11-05/2023_us.csv` (`4f9d689effb212528256b7f1c6dba8ce1adf90f616591175f93a9050de40d982`)
  and `R/2024/2025-11-05/2024_us.csv` (`06dfa3a67bb4c5bd38d9e9f0f7b8bff10b95254a63169423632d7f6f251e1506`)
  (`specs/naics-evaluation-data-stage-5-findings.md`, "Snapshot and raw files").
- **Leave alone.** Never touch the `r1` bundle, the three raw files or their manifest lines.
  Do not edit `specs/naics-evaluation-data-stage-5-findings.md`,
  `scripts/reconcile_tri_parent_links.py` or `specs/deliverable-map.md` (Settled Defaults 3
  and 7). Never use the main checkout, the Stage 19 worktree
  (`.claude/worktrees/stage-19-wage-minimum-earners`) and its plan 17, the Codex worktree
  and branch `codex/acs-targets-design`, plans 9 and 10, or another session's branch.
- **Software identity.** `tri_bundle.SOFTWARE_FILES` (`src/embedding_data/tri_bundle.py:57-82`)
  lists 24 files, among them `pyproject.toml`, `uv.lock`, the shared Stage 4 to 6 modules
  and every `tri_*` module. `verify` refuses a run when any of them, the Python identity or
  the installed distributions differ from the run's recorded `software`
  (`tri_bundle.py:151-161`, `:448-450`). The recorded Python is
  `3.14.0 (main, Oct 14 2025, 21:10:22) [Clang 20.1.4 ]`, CPython, 63 distributions,
  `uv_lock_sha256` `f57c3280a7c8286711bf6804ca4c02f0a19619c9db52f33941b9c5b996cba8e5`.
  `.python-version` says only `3.14`. Only the uv-managed
  `/Users/lowell/.local/share/uv/python/cpython-3.14.0-macos-aarch64-none/bin/python3.14`
  matches (plan 16, Global Constraints). Never run `uv sync` again, and never use a `--with`
  overlay, after Task 1.
- **Clean tree.** `inputs.json` records `dirty` from `git status --porcelain
  --untracked-files=normal` in `W`. Every log, time file, JSON line and the ledger
  (`E/progress.md`) go to `E`, never into `W`. `.sdd/` is not gitignored. Until Task 4 ends,
  edit no tracked file in `W` and tick no box in this plan. Track progress in the session's
  task list. Run each check script from a heredoc (`uv run --offline --locked python -
  <<'EOF'`) or keep it in `E`.
- **Host rule** (`specs/plans/completed/13-tri-parent-links.md:112-125`, and Owner
  Checkpoints item 5 at `:165-167`). Run one full-data command at a time on this host.
  `verify` counts as one here, because it recomputes every table from the three raw files
  (Stage 5's build took 3.52 s and 1.59 GB). `audit` reads the whole raw tree. Before the
  build, each `verify`, `compare-runs` and `audit`:
  1. Run `pgrep -fl 'embedding_data|embedding-data'` and show the owner its full,
     unfiltered output. Stop if it shows another acquisition or build.
  2. Run `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`.
     Stop if it prints anything.
- **Production writes.** The replay build is the only write under `ROOT`. It needs the
  owner's go-ahead and the owner's confirmation that no other stage's acquisition or build
  is running and that no Stage 9 freeze window is open (plan 13, Host rule item 3). So does
  any cleanup of a failed run's staging. `verify`, `compare-runs`, `audit` and the identity
  checks write nothing under `ROOT` and need no go-ahead.
- **Long-running commands.** Run `build`, both `verify` runs, `compare-runs` and `audit` with
  `run_in_background`, or in the owner's terminal. A killed `build` leaves a `.part` that
  blocks the run ID and holds D&B numbers (Review Focus 5).
- **Order.** Do not merge or rebase `origin/main` into the branch before Task 4 ends. A merge
  between the build and the replay's `verify` can pull in a software change.
- **Commits.** Before every commit, merge and push, run the Stage 9 `pgrep` check (step 2
  above). Stop if it prints anything. Every file this plan changes is under `specs/` or is
  root-level Markdown, so the commit hook skips its tests. The merge in Task 5 and the push
  in Task 6 can still run the full-suite hook `coverage-check-full`, because they carry
  other sessions' commits from `origin/main`. Never skip a hook. Never amend or rebase the
  commit that the replay records as `execution.commit`. The finding cites it.
- **No row content.** The finding, the evidence lines and the commit messages hold hashes,
  counts and command output lines only, never a row, a parent name or a D&B number.
- **On any failure.** Stop. Change no code. Report the failing step and its output to the
  owner. Never rerun a failed build under the same run ID.

## Review Focus

1. **Software changed on `main` before execution.** At planning (`dae8f4e`), `git diff
   --quiet 786ebcc origin/main` over the 24 files exits 0. No live plan edits one of them:
   plan 9 only checks that `target_contract.py` is unchanged, plan 17 names `pyproject.toml`
   only as a Stage 17 identity input, and plan 10 names none. A lock bump or a shared-module
   change can still land first. The owner expects the run to stop before any data command,
   not a replay that `verify` refuses. Pinned by Task 1 Step 2, at the execution HEAD. The
   owner may then choose to cut `W` from the last `main` commit where the diff is empty.
2. **The wrong venv.** A command that uses the main checkout's `.venv`, a set
   `UV_PROJECT_ENVIRONMENT` or a venv on Homebrew's Python records another checkout's
   commit, dirty state, files or Python. The owner expects `PROJECT_ROOT` to be `W` and the
   live software to equal `r1`'s record. Pinned by Task 1 Step 4.
3. **A stray file in `W`.** A time log or a ledger in the worktree makes the replay record
   `dirty: true`. The owner expects `dirty: false`, as `r1` has. Pinned by Task 3 Steps 1
   and 3, and Task 4 Step 4.
4. **Selection and software that `compare-runs` cannot see.** It does not compare
   `inputs.json` (`tri_bundle.py:474-498`), so `equal` says nothing about the raw
   citations, the layouts or the software. The owner expects proof that both runs record
   the same inputs. Pinned by Task 4 Step 3.
5. **A killed or failed build.** It leaves `P/<replay ID>.part/.scratch/`, which holds
   transcoded copies of the raw files and so D&B numbers, and a Stage 9 freeze check would
   fail on it. The owner expects the run to stop, the `.part` to stay until the owner's
   go-ahead for cleanup, and no rerun under the same ID. Pinned by Task 3 Step 3 and
   Task 4 Step 4 (no `.part` in `P`).

## Decisions

The brief carries no decision. The owner's approval of Stage 18 (2026-11-22, "Approve") is
in the roadmap's Choices made, bullet "Resume after Stages 5 and 17". The run-pin amendment
(owner, 2026-11-22) is in the entry's Produces.

## Settled Defaults (for owner review)

1. **Spec field.** `specs/completed/tri-parent-links.md`, Stage 5's spec, as the header
   states. Stage 18 has no stage spec of its own.
2. **Replay run ID.** `stage5_tri_parent_links_20261121_r1_replay`, the `<first>_replay` form
   of the Stage 10, 17 and 20 replays. A published run ID is permanent.
3. **Stale text.** The finding states the corrections that the Stage 18 Consumes line
   records, and cites the source of each (Task 5 Step 1, section 5). The Stage 5 findings
   file and the reconciler stay unedited. The docstring fix becomes a deferred item in
   section `18-tri-parent-links` and rides with the next change to the script, as Stage 20
   did for its reconciler.
4. **Finding file name.** `specs/findings/stage-5-tri-parent-links.md`. The name matches the
   run IDs (`stage5_…`) and the family's build stage, as Stage 20's
   `stage-14-usaspending-vendor-links.md` does. `specs/findings/` also holds two
   `stage-5-geography-*` files from the old roadmap's Stage 5. The suffix tells them apart,
   and the finding's first paragraph names `specs/naics-evaluation-data-roadmap.md`.
5. **No reconciler run on the replay.** The Exit does not ask for one. The reconciler was
   equal on `r1`, and `compare-runs` shows the replay's tables and report equal to `r1`'s.
   The finding states this limit. The Stage 5 findings record no reconciler cost.
6. **CLAUDE.md placement.** `CLAUDE.md` has no TRI section (only the overview at line 7
   names the family). Task 5 adds one paragraph, `**TRI parent links (roadmap Stage 5).**`,
   at the end of the file, after the USAspending section. That avoids Stage 19's edit near
   the Stage 17 section.
7. **Stale passages the entry does not name.** `specs/deliverable-map.md:13` still says
   "Not built. Roadmap Stage 5, ready". Plan 17 edits line 11 of that file. This plan does
   not edit it and adds a deferred item in section `18-tri-parent-links`. The brief's second
   passage is already resolved: the USAspending spec is now
   `specs/completed/usaspending-vendor-links.md`, and its link to `tri-parent-links.md`
   (line 42) resolves, because both files are in `specs/completed/`.

---

### Task 1: Execution worktree and identity (read-only)

**Files:** none in the repository. Evidence goes to `E`.

- [ ] **Step 1: Create the worktree and the venv**

```bash
git -C /Users/lowell/Projects/embedding-data fetch origin
git -C /Users/lowell/Projects/embedding-data worktree add -b stage-18-tri-hardening /Users/lowell/Projects/embedding-data/.worktrees/stage-18-tri-hardening origin/main
git -C /Users/lowell/Projects/embedding-data/.worktrees/stage-18-tri-hardening branch --unset-upstream
mkdir -p /Users/lowell/.cache/embedding-data/stage-18
```

From `W`, with `UV_PROJECT_ENVIRONMENT` unset, run once:
`uv sync --locked --python /Users/lowell/.local/share/uv/python/cpython-3.14.0-macos-aarch64-none/bin/python3.14`.
Expected: `W/.venv` exists, and `git status --porcelain` in `W` prints nothing.

- [ ] **Step 2: Software files unchanged since `786ebcc`**

From `W`, list the 24 entries of `SOFTWARE_FILES` from `src/embedding_data/tri_bundle.py`
and run `git diff --quiet 786ebcc HEAD -- <those files>`.
Expected: exit 0. Any other exit: stop and ask the owner (Review Focus 1).

- [ ] **Step 3: Snapshot (read-only)**

Copy `ROOT/raw/manifest.jsonl` to `E/manifest-baseline.jsonl`. Write to `E/snapshot.json`:
- the SHA-256, byte size and line count of that copy
- the SHA-256 of `outputs.json` of `r1` and of `ROOT/derived/codes/stage4_v11_20261013_r2`
- the sorted entry names of `P`
- every file under `R`, by relative path, with its SHA-256

Expected: the `r1` hash is the selected pin, and the codes hash is
`15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`. `P` holds exactly
`stage5_tri_parent_links_20261121_r1`. The replay ID and `<replay ID>.part` do not exist.
Each `R/<RY>/2025-11-05/` holds exactly `<RY>_us.csv`, with the SHA-256 in Global
Constraints, "Raw files". Any difference: stop and ask. A file under another snapshot date
does not change the selection: show it to the owner and continue.

- [ ] **Step 4: Live identity equals `r1`'s record**

From `W`, run `uv run --offline --locked python` with a script that prints one JSON line to
`E/identity-1.json`:
- `project_root`: `str(paths.PROJECT_ROOT)`
- `python_full`: `sys.version`
- `dependencies`: the count of `tri_bundle.freeze_software()['dependencies']`
- `software_equal`: whether `tri_bundle.freeze_software()` equals the `software` of
  `P/stage5_tri_parent_links_20261121_r1/inputs.json`

Expected: `project_root` is `W`, `python_full` is
`3.14.0 (main, Oct 14 2025, 21:10:22) [Clang 20.1.4 ]`, `dependencies` is 63 and
`software_equal` is true. Any difference: stop and ask. Do not try to repair the venv.

---

### Task 2: Re-verify `r1` from the Stage 18 checkout (read-only)

**Files:** none. Evidence goes to `E`.

The Exit needs this, because `compare-runs` does not check software identity. A failure
here blocks the replay.

- [ ] **Step 1: Host rule**

Run both `pgrep` checks (Global Constraints, "Host rule") and show the owner the first one's
full output.

- [ ] **Step 2: Verify**

From `W`, in the background, and write the exit code to `E/verify-r1.rc`:

```bash
/usr/bin/time -l uv run --offline --locked python -m embedding_data.tri_parent_links verify stage5_tri_parent_links_20261121_r1 --outputs-sha256 65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b --data-dir /Users/lowell/Projects/embedding-data/data > /Users/lowell/.cache/embedding-data/stage-18/verify-r1.out 2> /Users/lowell/.cache/embedding-data/stage-18/verify-r1.err
```

Expected: exit 0 and one JSON line with `outputs_sha256` the selected pin, `processed_as_of`
`2025-11-05` and `rows` `{"tri_facility_years": 65464, "tri_parent_industries": 7777,
"tri_parent_link_marginals": 405, "tri_parent_link_support": 14204, "tri_parent_links":
14204}` (the Stage 5 findings, "Verification"). Record the wall time and maximum resident
set size from the `.err` file. Stage 5 recorded no `verify` cost, so this is the first.

---

### Task 3: Replay build (owner gate)

**Files:** none. Evidence goes to `E`. The bundle goes to `P/stage5_tri_parent_links_20261121_r1_replay/`.

- [ ] **Step 1: Clean state and identity again**

In `W`, `git status --porcelain --untracked-files=normal` prints nothing. Repeat Task 1
Steps 2 and 4, writing `E/identity-2.json`. Expected: as in Task 1.

- [ ] **Step 2: Go-ahead**

Run both `pgrep` checks, show the owner the first one's full output and save it as
`E/pgrep-build.txt`. Confirm that neither `P/stage5_tri_parent_links_20261121_r1_replay` nor
its `.part` exists. Ask the owner for the go-ahead, and for the confirmation that no other
stage's acquisition or build is running and that no Stage 9 freeze window is open. Wait for
all three.

- [ ] **Step 3: Build**

From `W`, in the background, and write the exit code to `E/build-replay.rc`:

```bash
/usr/bin/time -l uv run --offline --locked python -m embedding_data.tri_parent_links build stage5_tri_parent_links_20261121_r1_replay --codes-run stage4_v11_20261013_r2 --codes-outputs-sha256 15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a --processed-as-of 2025-11-05 --data-dir /Users/lowell/Projects/embedding-data/data > /Users/lowell/.cache/embedding-data/stage-18/build-replay.out 2> /Users/lowell/.cache/embedding-data/stage-18/build-replay.err
```

Expected: exit 0 and one JSON line with `run_id`, `directory`
(`derived/epa_tri/parent-links/stage5_tri_parent_links_20261121_r1_replay`) and
`outputs_sha256`. Call the pin `REPLAY_PIN`. It differs from `r1`'s pin, because
`inputs.json` records the run ID and the execution. `P` holds no `.part`, and
`git status --porcelain --untracked-files=normal` in `W` prints nothing. Record the wall
time and maximum RSS, then `du -sk` of the replay directory and of `r1`, and the file count
and byte total of each. A failure: stop, leave the `.part` in place, and ask the owner.

---

### Task 4: Verify, compare and preservation (read-only)

**Files:** none. Evidence goes to `E`.

- [ ] **Step 1: Verify the replay**

Run both `pgrep` checks and show the owner the first one's output. Repeat Task 1 Steps 2
and 4 (`E/identity-3.json`). Then, from `W`, in the background (`E/verify-replay.rc`):

```bash
/usr/bin/time -l uv run --offline --locked python -m embedding_data.tri_parent_links verify stage5_tri_parent_links_20261121_r1_replay --outputs-sha256 REPLAY_PIN --data-dir /Users/lowell/Projects/embedding-data/data > /Users/lowell/.cache/embedding-data/stage-18/verify-replay.out 2> /Users/lowell/.cache/embedding-data/stage-18/verify-replay.err
```

Expected: exit 0, `outputs_sha256` is `REPLAY_PIN`, and `processed_as_of` and `rows` equal
Task 2's. Record wall time and maximum RSS.

- [ ] **Step 2: Compare**

Run both `pgrep` checks. Then, from `W`, in the background (`E/compare.rc`):

```bash
/usr/bin/time -l uv run --offline --locked python -m embedding_data.tri_parent_links compare-runs stage5_tri_parent_links_20261121_r1 stage5_tri_parent_links_20261121_r1_replay --data-dir /Users/lowell/Projects/embedding-data/data > /Users/lowell/.cache/embedding-data/stage-18/compare.out 2> /Users/lowell/.cache/embedding-data/stage-18/compare.err
```

Expected: exit 0 and one JSON line with `"equal": true`, `"report_equal": true`,
`"trust_established": false`, and for each of the five tables of `tri_bundle.TABLES`
`schema_equal` and `values_equal` true with equal `first_rows` and `second_rows`. Exit 1 or
any unequal table: stop and ask.

- [ ] **Step 3: Compare the two `inputs.json` files**

This covers what `compare-runs` skips. In `uv run --offline --locked python`, load both
`inputs.json` files and write one JSON line to `E/inputs-compare.json`. It must hold:
- the top-level keys are the same set, and equal `tri_bundle.INPUT_FIELDS`
- the keys whose values differ are exactly `execution` and `run_id`
- in `execution`, the keys are the same set, and those whose values differ are exactly
  `commit` and `created_at`
- `dirty` is false in both
- `contracts`, `codes`, `raw`, `processed_as_of`, `window`, `layouts`, `rules` and
  `software` are each equal

Also record the SHA-256 of `inputs.json` and `report.json` of both runs. The two
`report.json` hashes are equal. Any other result: stop and ask.

- [ ] **Step 4: Preservation**

1. `ROOT/raw/manifest.jsonl` has the Task 1 SHA-256 and line count. If other stages appended
   lines in the meantime, its first bytes equal `E/manifest-baseline.jsonl` byte for byte.
   Show the owner every line after them, for the owner to account for. `build`, `verify`
   and `compare-runs` append nothing.
2. The `outputs.json` SHA-256 of `r1` and of the codes bundle equal the snapshot.
3. `P` holds exactly `r1` and the replay, and no `.part`.
4. Every file under `R` has the path and SHA-256 that the snapshot recorded, and `R` holds
   no other file.
5. Run both `pgrep` checks. Then, in the background:
   `uv run --offline --locked embedding-data audit --data-dir /Users/lowell/Projects/embedding-data/data`.
   Expected: exit 0 with zero raw provenance discrepancies.
6. `git status --porcelain --untracked-files=normal` in `W` prints nothing.

Write the outcomes to `E/snapshot-after.json`.

---

### Task 5: Acceptance finding and run pins

**Files:**
- Create: `specs/findings/stage-5-tri-parent-links.md`
- Modify: `README.md` (section "TRI parent links (roadmap Stage 5)", last paragraph)
- Modify: `CLAUDE.md` (new last paragraph)

Now merge `origin/main` into the branch (Task 4 has ended). Place each edit by its quoted
anchor text, not by line number, because Stage 19 edits both files in parallel. Fill
`REPLAY_PIN`, `REPLAY_COMMIT` and the measured values from `E`.

- [ ] **Step 1: Write the finding**

Model it on `specs/findings/stage-14-usaspending-vendor-links.md`. Cite
`specs/naics-evaluation-data-stage-5-findings.md` for the counts. Do not restate them.
Sections:
1. **Selected runs and pins.** A table: `r1` and the replay, each with the SHA-256 of
   `outputs.json` (the detached pin), `inputs.json` and `report.json`. File count (8) and
   byte total of each bundle. The replay, both `verify` and the `compare-runs` commands,
   exactly as run.
2. **Execution identity.** Both commits, `dirty` and `created_at`, and the shared Python,
   63 distributions, 24 software files and `uv.lock` SHA-256. That `r1`'s record equalled
   the live `freeze_software()` before each command (Task 1 Step 4, Task 3 Step 1, Task 4
   Step 1), and that the two `inputs.json` files differ only as Task 4 Step 3 shows.
3. **Measured cost.** Wall time and maximum RSS of the Task 2 `verify`, the replay build, the
   replay `verify`, `compare-runs` and `audit`, beside Stage 5's build (3.52 s, 1,589,870,592
   bytes, 1,308 KB by `du -sk`). Name every other session's job that the `pgrep` lists
   showed, and mark the wall times as loaded if there was one.
4. **Results.** The `rows` of both `verify` runs and the preservation outcomes. Quote
   verbatim the `compare-runs` JSON line, the `E/inputs-compare.json` line and the
   `E/identity-3.json` line, so that the evidence does not depend on `E`, a cache
   directory, surviving.
5. **Corrections to earlier text.** Neither file is edited.
   1. The "Partial owners" limit of the Stage 5 findings (line 201) cites "spec 470–474" and
      calls the reading a ruling marked unclear. The owner settled it on 2026-11-21: the
      spec, lines 472–480, marked *(owner, plan 13, 2026-11-21)*, says that an excluded
      facility-year belongs to each standardized parent name that it lists, else to
      `facility:<TRIFD>`. The build and the reconciler use that reading. How many `naics_*`
      facility-years name more than one parent is still not measured.
   2. The docstring (line 3) of `scripts/reconcile_tri_parent_links.py` names
      `specs/tri-parent-links.md`. The spec is at `specs/completed/tri-parent-links.md`.
      The script is not in `tri_bundle.SOFTWARE_FILES`, so `verify` does not hash it. The
      fix rides with the next change to the script. End the item with the marker
      `→ item: 18-tri-parent-links — <date>`, where `<date>` is the date in the heading of
      the section that Task 6 Step 1 appends.
6. **Limits.** `compare-runs` does not compare `inputs.json`, and Task 4 Step 3 covers it.
   The independent reconciler ran on `r1` only (Settled Default 5), and its "equal" does not
   cover the report fields that the Stage 5 findings list under "Reconciler coverage". The
   E8 time basis: EPA's standardized parent names the current owner. The RY2022
   foreign-parent columns hold data but stay unmapped. One EPA snapshot (2025-11-05).
   `acquire` refuses every EPA file, so a later snapshot enters through `import-file` and a
   new run.
7. **Not claimed.** No headline minimum count (O13), no protocol section (O17), no scoring.
   Every target keeps `size_gate_pending`. Agreement between two runs does not show accuracy
   or representativeness. Under R8.4 no output feeds embedder training, curriculum,
   hard-negative mining or model selection. The outputs publish no D&B number.
8. **Where the evidence lives.** The bundles under `P`, the files in `E`, the Stage 5
   findings, plan 13 and this plan.

- [ ] **Step 2: README pins**

In `README.md`, replace:

```
benchmarks. This README holds no run ID or pin yet. The owner-gated full-data run records
its results in `specs/naics-evaluation-data-stage-5-findings.md`. The selected run IDs
and detached pins wait for O12, the later TRI hardening step. O12 also runs the replay
build and a full-data `compare-runs`.
```

with:

```
benchmarks. The measured production runs are `stage5_tri_parent_links_20261121_r1` (the
first run) and `stage5_tri_parent_links_20261121_r1_replay`. Their detached pins, which
`verify` needs as `--outputs-sha256`, are
`65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b` and `REPLAY_PIN`. Both
pass `verify`, and `compare-runs` finds them equal. The first run's counts are in
`specs/naics-evaluation-data-stage-5-findings.md`. The
[Stage 5 finding](specs/findings/stage-5-tri-parent-links.md) records the replay, the exact
commands, the cost and what is not claimed.
```

- [ ] **Step 3: CLAUDE.md pins**

Append this paragraph to the end of `CLAUDE.md`, after one blank line. At planning the file
ends with the USAspending section. Stage 21 may reword that section's last sentence, so do
not anchor on it.

```
**TRI parent links (roadmap Stage 5).** `python -m embedding_data.tri_parent_links` exposes
`acquire`, `import-file`, `build`, `verify` and `compare-runs`, separate from the frozen
top-level CLI. Always pass an explicit `--data-dir`. Only `acquire` uses the network, and it
refuses every EPA file because EPA's endpoint sends no `Content-Length`: the owner downloads
in a browser and `import-file` records the exact bytes. The other four load no `.env`, read
no credential and construct no HTTP client. Failure prints only `TRI parent links <command>
failed: <reason>; run <run_id>; path <path>` and exits 2. An unequal `compare-runs` exits 1.
A bundle lives in `derived/epa_tri/parent-links/<RUN_ID>/` (five Parquets, `inputs.json`,
`report.json` and the detached `outputs.json`). Build scratch in `<RUN_ID>.part/.scratch/`
holds transcoded raw copies with D&B numbers, and the outputs publish none. The selected runs
are `stage5_tri_parent_links_20261121_r1` and `stage5_tri_parent_links_20261121_r1_replay`,
with detached pins `65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b` and
`REPLAY_PIN`, built from snapshot `2025-11-05` and codes run `stage4_v11_20261013_r2` (pin
`15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`) at commits `786ebcc` and
`REPLAY_COMMIT` (both `dirty: false`). Both pass `verify`, and `compare-runs` finds them
equal. A change to any file in `tri_bundle.SOFTWARE_FILES` (24 files, including
`pyproject.toml`, `uv.lock` and the shared Stage 4 to 6 modules), the Python build or the
installed distributions makes `verify` refuse both runs. Each production write needs the
owner's go-ahead under README's host rule. The
[Stage 5 finding](specs/findings/stage-5-tri-parent-links.md) records the commands, the cost
and the limits. No output may feed embedder training, curriculum, hard-negative mining or
model selection (R8.4). Every target keeps `size_gate_pending`, and no headline minimum count
(O13) exists yet.
```

- [ ] **Step 4: Commit**

Run the Stage 9 `pgrep` check. Then:

```bash
git add specs/findings/stage-5-tri-parent-links.md README.md CLAUDE.md
git commit -m "docs: record the Stage 18 replay of the TRI parent links"
```

Expected: the coverage hooks print `Skipped`.

---

### Task 6: Completion and integration

**Files:**
- Modify: this plan, `specs/naics-evaluation-data-roadmap.md`, `specs/deferred_items.md`,
  `specs/history.md`
- Move: this plan to `specs/plans/completed/`

- [ ] **Step 1: Plan Completion Protocol**

Run the writing-plans Plan Completion Protocol, including step 3a. The new section
`18-tri-parent-links` of `specs/deferred_items.md` gets two items: the reconciler docstring
(Task 5 Step 1, correction 2) and the stale TRI row at `specs/deliverable-map.md:13`
(Settled Default 7). The `## Handoff to later stages` section gives:
- **O13 (TRI headline minimum count).** It reads `n_unweighted_distribution` in `report.json`
  of `r1` (plan 13, Handoff), whose bytes equal the replay's (Task 4 Step 3). Name both runs
  and pins.
- **O17 (TRI protocol section).** The selected runs and pins, the finding's path, the
  `compare-runs` limit with the Task 4 Step 3 check that covers it, and the settled
  partial-owner reading (correction 1).
- **Traps.** A change to any of the 24 files, the Python build or the installed
  distributions makes `verify` refuse both runs. Only uv's CPython 3.14.0 reproduces the
  record. The measured `verify` and `compare-runs` costs.

Leave the spec where it is: it is already in `specs/completed/`.

- [ ] **Step 2: Integrate**

Run the Stage 9 `pgrep` check. Push the branch and open the PR under the owner's
PR-lifecycle rule. No commit lands on the branch before the build, so `REPLAY_COMMIT` is
the `origin/main` commit that Task 1 cut `W` from, and it stays reachable from `main`.
Merge with a merge commit (`gh pr merge --merge`), as the repository's history does. Then
run the post-merge cleanup for `W`.
