# USAspending Vendor Links Hardening Implementation Plan

**Status: COMPLETE (2026-11-22)** — executed via executing-plans; deferred items in specs/deferred_items.md

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Stage 14's USAspending vendor-link bundle an exact replay check, a long-form
acceptance finding and README and CLAUDE.md run pins (O25).

**Architecture:** No code changes. A controller runs the existing offline commands of
`python -m embedding_data.usaspending_vendor_links` from a new worktree whose venv
reproduces the software record of run `stage14_vendor_links_20261122_r2`. It re-verifies
`r2`, builds one replay with the same arguments, verifies the replay, compares the two
runs and their `inputs.json` files, checks preservation, then writes the finding and the
pins.

**Tech Stack:** Python 3.14.0 (uv-managed), uv, the Stage 14 command group, `/usr/bin/time -l`, `du`.

**Spec:** `specs/completed/usaspending-vendor-links.md`, for the rules and the command
contract. Its lines 961–962 defer the run pins to a hardening stage, and its Out of scope
(line 79) leaves the replay and the long-form finding to the resume. The scope of this plan
is the roadmap's Stage 20 entry (Objective, Consumes, Produces, Exit), which the owner
approved on 2026-11-22.

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 20 — on plan completion, tick the stage and re-validate later stages against what shipped.

Scope: O25. Leaves out the USAspending headline minimum count (O26), the protocol section
(O18), a changed D2 rule, the live `acquire-sam-extract` request and the R8.4 training-role
amendment (roadmap, Stage 20 `Leaves out`).

Process: the controller runs every task itself, inline, because each task is an owner gate
or a command whose output decides the next step. No subagent is dispatched.

## Global Constraints

- **Names.** `ROOT` is `/Users/lowell/Projects/embedding-data/data`. `W` is
  `/Users/lowell/Projects/embedding-data/.worktrees/stage-20-usaspending-hardening`, on
  branch `stage-20-usaspending-hardening`, cut from `origin/main` after this plan merges.
  `E` is `/Users/lowell/.cache/embedding-data/stage-20`, outside every checkout. `V` is
  `ROOT/derived/usaspending/vendor-links`.
- **Selected run.** `stage14_vendor_links_20261122_r2`, detached pin
  `248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be`, snapshot `2026-11-19`,
  extract month `2026-10`, built at `1eddb3e` with `dirty: false`.
- **Replay run ID.** `stage14_vendor_links_20261122_r2_replay` (Settled Default 2).
- **Build arguments.** `--codes-run stage4_v11_20261013_r2 --codes-outputs-sha256
  15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a --snapshot 2026-11-19
  --sam-month 2026-10 --data-dir /Users/lowell/Projects/embedding-data/data`.
- **Leave alone.** Never touch `stage14_vendor_links_20261121_r1`, which `verify` refuses
  and nothing cites. Compare against `r2` only. Never touch the raw files under
  `ROOT/raw/usaspending/subcontracts/2026-11-19/` and
  `ROOT/raw/sam/entity-extract/public-monthly-v2/2026-10/`, or their manifest lines. Do not
  edit `specs/naics-evaluation-data-stage-14-findings.md`,
  `scripts/reconcile_usaspending_vendor_links.py` or the O6 row of the roadmap. Never use the
  main checkout, the Codex worktree or another session's branch.
- **Software identity.** `vendor_link_bundle.SOFTWARE_FILES` lists 26 files, among them
  `pyproject.toml`, `uv.lock` and `sam_raw.py`. `verify` refuses a run when any of them,
  the Python identity or the installed distributions differ from the run's recorded
  `software`. The recorded Python is `3.14.0 (main, Oct 14 2025, 21:10:22) [Clang 20.1.4 ]`,
  CPython, 63 distributions, `uv_lock_sha256` `f57c3280…`. Only the uv-managed
  `/Users/lowell/.local/share/uv/python/cpython-3.14.0-macos-aarch64-none/bin/python3.14`
  matches. Homebrew's 3.14.8 does not. Never run `uv sync` again, and never use a `--with`
  overlay, after Task 1.
- **Clean tree.** `inputs.json` records `dirty` from `git status --porcelain
  --untracked-files=normal` in `W`. Every log, time file and JSON line goes to `E`, never
  into `W`. Until Task 4 ends, edit no tracked file in `W` and tick no box in this plan.
  Track progress in the session's task list. Run each check script from a heredoc
  (`uv run --offline --locked python - <<'EOF'`) or keep it in `E`. `.gitignore` already
  ignores `__pycache__/`.
- **Host rule** (`specs/plans/completed/15-usaspending-vendor-links.md:134-148`). Run one
  full-data command at a time on this host. `verify` and `compare-runs` count as
  full-data commands here, because each recomputes or rescans the bundle at about 955 MB.
  `audit` reads the whole raw tree. Before each of them and before the build:
  1. Run `pgrep -fl 'embedding_data|embedding-data'` and show the owner its full,
     unfiltered output. Stop if it shows another acquisition or build, for example a
     Stage 18 TRI build.
  2. Run `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`.
     Stop if it prints anything.
- **Production writes.** The replay build is the only write under `ROOT`. It needs the
  owner's go-ahead and the owner's confirmation that no Stage 9 freeze window is open
  (plan 15, Owner Checkpoints item 6). So does any cleanup of a failed run's staging.
  `verify`, `compare-runs`, `audit` and the identity checks write nothing under `ROOT` and
  need no go-ahead.
- **Long-running commands.** Run `build`, both `verify` runs, `compare-runs` and `audit`
  with `run_in_background`, or in the owner's terminal. A foreground call is killed after
  2 to 10 minutes, and a killed `build` leaves a `.part` that blocks the run ID.
- **Order.** Do not merge or rebase `origin/main` into the branch before Task 4 ends. A
  merge between the build and the replay's `verify` can pull in a software change.
- **Commits.** Before every commit, merge and push, run the Stage 9 `pgrep` check (step 2
  above). Stop if it prints anything. The merge in Task 5 and the push in Task 6 can run
  the full-suite hook `coverage-check-full`. Never skip a hook. Never amend or rebase the commit that the replay
  records as `execution.commit`. The finding cites it.
- **On any failure.** Stop. Change no code. Report the failing step and its output to the
  owner. Never rerun a failed build under the same run ID.

## Review Focus

1. **Software changed on `main` before execution.** Plans 9 and 10, Stage 18 or a lock bump
   can land before this plan runs and change one of the 26 files. The owner expects the
   run to stop before any data command, not a replay that `verify` refuses. Pinned by
   Task 1 Step 2, at the execution HEAD.
2. **The wrong venv.** A command that uses the main checkout's `.venv`, a set
   `UV_PROJECT_ENVIRONMENT` or a venv on Homebrew's 3.14.8 records another checkout's
   commit, dirty state, files or Python. The owner expects `PROJECT_ROOT` to be `W` and the
   live software to equal `r2`'s record. Pinned by Task 1 Step 4.
3. **A stray file in `W`.** A time log in the worktree makes the replay record
   `dirty: true`. The owner expects `dirty: false`, as `r2` has. Pinned by Task 3 Step 1
   and Task 4 Step 3.
4. **Software that `compare-runs` cannot see.** It skips `inputs.json` (D3), so `equal`
   says nothing about software. The owner expects proof that both runs record the same
   software. Pinned by Task 4 Step 3.
5. **A parallel run.** A Stage 18 build or a parallel manifest append during this stage.
   The owner expects the host rule to stop the run, and every appended manifest line to be
   shown. Pinned by the host rule before each command, and by Task 4 Step 4.

## Decisions

The brief carries no decision. The owner's approval of Stage 20 and of keeping D2
(2026-11-22, "Approve as drafted") is in the roadmap's Choices made, bullet "Resume after
Stage 14".

- **D1** (owner, plan review, 2026-11-22): Approve plan 16 as committed at `0b30760`, with the five Settled Defaults unchanged ("Approve plan 16"). Applied in: Settled Defaults.

## Settled Defaults (for owner review)

1. **Spec field.** `specs/completed/usaspending-vendor-links.md`, Stage 14's spec, as the
   header states. Stage 20 has no stage spec of its own.
2. **Replay run ID.** `stage14_vendor_links_20261122_r2_replay`, the `<first>_replay` form
   of the Stage 10 and Stage 17 replays. A published run ID is permanent.
3. **Stale text.** The finding states the two corrections that the Stage 20 Consumes line
   records, and cites the source of each. The findings file's Status line (line 3) and the
   reconciler docstring (line 6) stay unedited. The docstring fix rides with the next change
   to the script (deferred item, section `15-usaspending-vendor-links`).
4. **Finding file name.** `specs/findings/stage-14-usaspending-vendor-links.md`. The name
   matches the run IDs (`stage14_…`) and the family's build stage. It does not collide with
   the old roadmap's `stage-10-…` name. Stage 18 can follow the same form
   (`stage-5-tri-parent-links.md`).
5. **No reconciler run on the replay.** The Exit does not ask for one. The reconciler was
   equal on `r2`, and `compare-runs` shows the replay's tables and report equal to `r2`'s.
   The finding states this limit. A run would cost about 24 s and 375 MB if the owner wants
   it.

---

### Task 1: Execution worktree and identity (read-only)

**Files:** none in the repository. Evidence goes to `E`.

- [x] **Step 1: Create the worktree and the venv**

> Deviation: `origin/main` was `3d0c63d` (the merge of PR 45, after this plan merged), so `W` and `REPLAY_COMMIT` are `3d0c63d`. Step 2 showed none of the 26 files changed. The ledger stayed in `E`, not in `W/.sdd/`, because `.sdd/` is not gitignored and would make the replay record `dirty: true`.

```bash
git -C /Users/lowell/Projects/embedding-data fetch origin
git -C /Users/lowell/Projects/embedding-data worktree add -b stage-20-usaspending-hardening /Users/lowell/Projects/embedding-data/.worktrees/stage-20-usaspending-hardening origin/main
git -C /Users/lowell/Projects/embedding-data/.worktrees/stage-20-usaspending-hardening branch --unset-upstream
mkdir -p /Users/lowell/.cache/embedding-data/stage-20
```

From `W`, with `UV_PROJECT_ENVIRONMENT` unset, run once:
`uv sync --locked --python /Users/lowell/.local/share/uv/python/cpython-3.14.0-macos-aarch64-none/bin/python3.14`.
Expected: `W/.venv` exists, and `git status --porcelain` in `W` prints nothing.

- [x] **Step 2: Software files unchanged since `1eddb3e`**

From `W`, list the 26 entries of `SOFTWARE_FILES` from `src/embedding_data/vendor_link_bundle.py`
and run `git diff --quiet 1eddb3e HEAD -- <those files>`.
Expected: exit 0. Any other exit: stop and ask the owner.

- [x] **Step 3: Snapshot (read-only)**

Copy `ROOT/raw/manifest.jsonl` to `E/manifest-baseline.jsonl`. Write to `E/snapshot.json`:
the SHA-256, byte size and line count of that copy, the
SHA-256 of `outputs.json` of `r1`, `r2` and `ROOT/derived/codes/stage4_v11_20261013_r2`, and
the sorted entry names of `V`.
Expected: the `r2` hash is the selected pin, the codes hash is
`15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`, and `V` holds exactly
`stage14_vendor_links_20261121_r1` and `stage14_vendor_links_20261122_r2`. The replay ID and
`<replay ID>.part` do not exist. Any difference: stop and ask.

- [x] **Step 4: Live identity equals `r2`'s record**

From `W`, run `uv run --offline --locked python` with a script that prints one JSON line to
`E/identity-1.json`:
- `project_root`: `str(paths.PROJECT_ROOT)`
- `python_full`: `sys.version`
- `dependencies`: the count of `freeze_software()['dependencies']`
- `software_equal`: whether `freeze_software()` equals the `software` of
  `V/stage14_vendor_links_20261122_r2/inputs.json`

Expected: `project_root` is `W`, `python_full` is
`3.14.0 (main, Oct 14 2025, 21:10:22) [Clang 20.1.4 ]`, `dependencies` is 63 and
`software_equal` is true. Any difference: stop and ask. Do not try to repair the venv.

---

### Task 2: Re-verify `r2` from the Stage 20 checkout (read-only)

**Files:** none. Evidence goes to `E`.

The Exit needs this, because `compare-runs` does not check software identity. A failure
here blocks the replay.

- [x] **Step 1: Host rule**

Run both `pgrep` checks (Global Constraints, "Host rule") and show the owner the first one's
full output.

- [x] **Step 2: Verify**

From `W`, in the background:

```bash
/usr/bin/time -l uv run --offline --locked python -m embedding_data.usaspending_vendor_links verify stage14_vendor_links_20261122_r2 --outputs-sha256 248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be --data-dir /Users/lowell/Projects/embedding-data/data > /Users/lowell/.cache/embedding-data/stage-20/verify-r2.out 2> /Users/lowell/.cache/embedding-data/stage-20/verify-r2.err
```

Expected: exit 0 and one JSON line with `rows` `{"vendor_links": 16614,
"vendor_link_marginals": 689, "vendor_link_support": 8307, "vendor_link_pairs": 107994}`
(the Stage 14 findings, "Checks"). Record the wall time and maximum resident set size from
the `.err` file.

---

### Task 3: Replay build (owner gate)

**Files:** none. Evidence goes to `E`. The bundle goes to `V/stage14_vendor_links_20261122_r2_replay/`.

- [x] **Step 1: Clean state and identity again**

In `W`, `git status --porcelain --untracked-files=normal` prints nothing. Repeat Task 1
Steps 2 and 4, writing `E/identity-2.json`. Expected: as in Task 1.

- [x] **Step 2: Go-ahead**

Run both `pgrep` checks and show the owner the first one's full output. Confirm that neither
`V/stage14_vendor_links_20261122_r2_replay` nor its `.part` exists. Ask the owner for the
go-ahead and the confirmation that no Stage 9 freeze window is open. Wait for both.

- [x] **Step 3: Build**

> Deviation: another session's pre-commit hook (7 pytest-xdist workers on temporary data directories) was on the host. It is not an acquisition or a build, and the owner said "don't wait, start the build now". The finding marks every Stage 20 wall time as loaded.

From `W`, in the background:

```bash
/usr/bin/time -l uv run --offline --locked python -m embedding_data.usaspending_vendor_links build stage14_vendor_links_20261122_r2_replay --codes-run stage4_v11_20261013_r2 --codes-outputs-sha256 15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a --snapshot 2026-11-19 --sam-month 2026-10 --data-dir /Users/lowell/Projects/embedding-data/data > /Users/lowell/.cache/embedding-data/stage-20/build-replay.out 2> /Users/lowell/.cache/embedding-data/stage-20/build-replay.err
```

Expected: exit 0 and one JSON line with `run_id`, `directory` and `outputs_sha256`. Call the
pin `REPLAY_PIN`. It differs from `r2`'s pin, because `inputs.json` records the run ID and
the execution. Record the wall time and maximum RSS, then `du -sk` of the replay directory
and of `r2`, and the byte total of the files in each.

---

### Task 4: Verify, compare and preservation (read-only)

**Files:** none. Evidence goes to `E`.

- [x] **Step 1: Verify the replay**

Run both `pgrep` checks and show the owner the first one's output. Repeat Task 1 Steps 2
and 4 (`E/identity-3.json`). Then, from `W`, in the background:

```bash
/usr/bin/time -l uv run --offline --locked python -m embedding_data.usaspending_vendor_links verify stage14_vendor_links_20261122_r2_replay --outputs-sha256 REPLAY_PIN --data-dir /Users/lowell/Projects/embedding-data/data > /Users/lowell/.cache/embedding-data/stage-20/verify-replay.out 2> /Users/lowell/.cache/embedding-data/stage-20/verify-replay.err
```

Expected: exit 0, and its `rows` equal Task 2's. Record wall time and maximum RSS.

- [x] **Step 2: Compare**

Run both `pgrep` checks. Then, from `W`, in the background:

```bash
/usr/bin/time -l uv run --offline --locked python -m embedding_data.usaspending_vendor_links compare-runs stage14_vendor_links_20261122_r2 stage14_vendor_links_20261122_r2_replay --data-dir /Users/lowell/Projects/embedding-data/data > /Users/lowell/.cache/embedding-data/stage-20/compare.out 2> /Users/lowell/.cache/embedding-data/stage-20/compare.err
```

Expected: exit 0 and one JSON line with `"equal": true`, `"report_equal": true`,
`"trust_established": false`, and for each of the four tables `schema_equal` and
`values_equal` true with equal `first_rows` and `second_rows`. Exit 1 or any unequal table:
stop and ask.

- [x] **Step 3: Compare the two `inputs.json` files**

This covers what D3 skips. In `uv run --offline --locked python`, load both `inputs.json`
files and write one JSON line to `E/inputs-compare.json`. It must hold:
- the top-level keys are the same set
- the keys whose values differ are exactly `execution` and `run_id`
- in `execution`, the keys whose values differ are exactly `commit` and `created_at`
- `dirty` is false in both
- `software` is equal, and so are `contracts`, `codes`, `raw`, `snapshot`, `sam_month`,
  `window`, `registries` and `rules`

Also record the SHA-256 of `inputs.json` and `report.json` of both runs. The two
`report.json` hashes are equal. Any other result: stop and ask.

- [x] **Step 4: Preservation**

1. `ROOT/raw/manifest.jsonl` has the Task 1 SHA-256 and line count. If other stages appended
   lines in the meantime, its first bytes equal `E/manifest-baseline.jsonl` byte for byte.
   Show the owner every line after them, for the owner to account for. `build`, `verify`
   and `compare-runs` append nothing.
2. The `outputs.json` SHA-256 of `r1`, `r2` and the codes bundle equal the snapshot.
3. `V` holds exactly `r1`, `r2` and the replay, and no `.part`.
4. Run both `pgrep` checks. Then, in the background:
   `uv run --offline --locked embedding-data audit --data-dir /Users/lowell/Projects/embedding-data/data`.
   Expected: exit 0 with zero raw provenance discrepancies.

---

### Task 5: Acceptance finding and run pins

**Files:**
- Create: `specs/findings/stage-14-usaspending-vendor-links.md`
- Modify: `README.md` (section "USAspending vendor links (roadmap Stage 14)")
- Modify: `CLAUDE.md` (section "USAspending vendor links (roadmap Stage 14)")

Now merge `origin/main` into the branch (Task 4 has ended). Place each edit by its quoted
anchor text, not by line number. Fill `REPLAY_PIN`, `REPLAY_COMMIT` and the measured values
from `E`.

- [x] **Step 1: Write the finding**

Model it on `specs/findings/stage-10-ita-establishment-targets.md`. Cite
`specs/naics-evaluation-data-stage-14-findings.md` for the counts. Do not restate them.
Sections:
1. **Selected runs and pins.** A table: `r2` and the replay, each with the SHA-256 of
   `outputs.json` (the detached pin), `inputs.json` and `report.json`. File count and byte
   total of each bundle. The replay, both `verify` and the `compare-runs` commands, exactly
   as run.
2. **Execution identity.** Both commits, `dirty`, `created_at`, and the shared Python,
   63 distributions, 26 software files and `uv.lock` SHA-256. That `r2`'s record equalled
   the live `freeze_software()` before each command (Task 1 Step 4, Task 3 Step 1, Task 4
   Step 1), and that the two `inputs.json` files differ only as Task 4 Step 3 shows.
3. **Measured cost.** Wall time and maximum RSS of the Task 2 `verify`, the replay build, the
   replay `verify` and `compare-runs`, beside Stage 14's build (29.6 s, 961 MB) and `verify`
   (28.8 s, 955 MB). `du -sk` of both bundles (Stage 14 recorded 1,720 KB for `r2`).
4. **Results.** The `rows` of both `verify` runs and the preservation outcomes. Quote
   verbatim the `compare-runs` JSON line, the `E/inputs-compare.json` line and the
   `E/identity-3.json` line, so that the evidence does not depend on `E`, a cache
   directory, surviving.
5. **Corrections to earlier text.** The findings file's Status line (line 3) says "Stage 14
   in progress". Stage 14 completed on 2026-11-22 (the roadmap's Stage 14 stamp, and the
   spec's Status line). The docstring of `scripts/reconcile_usaspending_vendor_links.py`
   (line 6) names `specs/usaspending-vendor-links.md`. The spec is at
   `specs/completed/usaspending-vendor-links.md`. Neither file is edited. The docstring fix
   is deferred (`specs/deferred_items.md`, section `15-usaspending-vendor-links`).
   → item: 15-usaspending-vendor-links — 2026-11-22
6. **Limits.** `compare-runs` skips `inputs.json` (D3), and Task 4 Step 3 covers it. The
   independent reconciler ran on `r2` only (Settled Default 5). `r1` is superseded, stays on
   disk and is not cited. D2 stays, with its cost in the Stage 14 findings ("The cost of
   D2"). One snapshot and one monthly extract.
7. **Not claimed.** No headline minimum count (O26), no protocol section (O18), no scoring.
   Every target keeps `size_gate_pending`. Under R8.4 no output feeds embedder training,
   curriculum, hard-negative mining or model selection. `vendor_link_pairs.parquet` holds
   UEI pairs and stays on this machine.
8. **Where the evidence lives.** The bundles under `V`, the logs in `E`, the Stage 14
   findings, plan 15 and this plan.

- [x] **Step 2: README pins**

In `README.md`, replace:

```
benchmarks. This section names no run pin. The selected run pins wait for a hardening stage,
if the owner promotes one.
```

with:

```
benchmarks. The measured production runs are `stage14_vendor_links_20261122_r2` (the first
run) and `stage14_vendor_links_20261122_r2_replay`. Their detached pins, which `verify` needs
as `--outputs-sha256`, are
`248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be` and `REPLAY_PIN`. Both
pass `verify`, and `compare-runs` finds them equal. The
[Stage 14 finding](specs/findings/stage-14-usaspending-vendor-links.md) records the exact
commands, the cost and what is not claimed. The superseded `stage14_vendor_links_20261121_r1`
stays on disk and is not cited.
```

- [x] **Step 3: CLAUDE.md pins**

In `CLAUDE.md`, after the sentence that ends `is equal on all 87 checks.`, insert:

```
The replay `stage14_vendor_links_20261122_r2_replay`, with detached pin `REPLAY_PIN`, was
built at commit `REPLAY_COMMIT` (`dirty: false`) with the same arguments. Both runs pass
`verify`, `compare-runs` finds them equal, and their `inputs.json` files differ only in the
run ID and the execution commit and time. The
[Stage 14 finding](specs/findings/stage-14-usaspending-vendor-links.md) records the commands,
the cost and the limits.
```

- [x] **Step 4: Commit**

> Deviation: the merge of `origin/main` was a no-op. The final review found three claims in the finding that went past the evidence, and commit `91e3380` scoped them. It changes no value.

Run the Stage 9 `pgrep` check. Then:

```bash
git add specs/findings/stage-14-usaspending-vendor-links.md README.md CLAUDE.md
git commit -m "docs: record the Stage 20 replay of the USAspending vendor links"
```

---

### Task 6: Completion and integration

**Files:**
- Modify: this plan, `specs/naics-evaluation-data-roadmap.md`, `specs/deferred_items.md`
  (ticking pass only), `specs/history.md`
- Move: this plan to `specs/plans/completed/`

- [x] **Step 1: Plan Completion Protocol**

Run the writing-plans Plan Completion Protocol, including step 3a. The
`## Handoff to later stages` section gives:
- **O26 (USAspending headline minimum count).** It reads `report.json` of `r2`, whose bytes
  equal the replay's, and its `n_unweighted_distribution` (plan 15, Handoff). Name both
  runs and pins.
- **O18 (USAspending protocol section).** The selected runs and pins, the finding's path,
  and the D3 limit with the Task 4 Step 3 check that covers it.
- Deferred items stay open: the live `acquire-sam-extract` request and the reconciler
  docstring (section `15-usaspending-vendor-links`).

Leave the spec where it is: it is already in `specs/completed/`.

- [x] **Step 2: Integrate**

Run the Stage 9 `pgrep` check. Push the branch and open the PR under the owner's
PR-lifecycle rule. No commit lands on the branch before the build, so `REPLAY_COMMIT` is
the `origin/main` commit that Task 1 cut `W` from, and it stays reachable from `main`.
Merge with a merge commit (`gh pr merge --merge`), as the repository's history does. Then
run the post-merge cleanup for `W`.

## Handoff to later stages

- **O26 (USAspending headline minimum count).** It reads `report.json` of
  `stage14_vendor_links_20261122_r2` (pin
  `248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be`), whose bytes equal the
  replay's (`stage14_vendor_links_20261122_r2_replay`, pin
  `d08ed4cb396fae172ebde8be65fe6dfc492cb4c2731ad4308cfcf7cd55fd6055`, SHA-256 `040127fb…`
  for both). Its `n_unweighted_distribution` is what plan 15's Handoff names. The CLAUDE.md
  sentence that still calls the minimum count O18 is a deferred item
  (`specs/deferred_items.md`, section `16-usaspending-vendor-links`).
- **O18 (USAspending protocol section).** The selected runs and pins are above. The finding
  is `specs/findings/stage-14-usaspending-vendor-links.md`. `compare-runs` skips
  `inputs.json` (D3), so equality says nothing about software. The Task 4 Step 3 check
  (the finding's Results, "The two `inputs.json` files") shows that only `run_id` and
  `execution.commit`/`created_at` differ.
- **Traps.** A change to any of the 26 files in `vendor_link_bundle.SOFTWARE_FILES`, the
  Python build or the installed distributions makes `verify` refuse both runs. Only uv's
  CPython 3.14.0 reproduces the record. `compare-runs` costs 0.76 s and 258 MB, not the
  955 MB this plan assumed, so it is not a full-data command in cost.
- **Still deferred.** The live `acquire-sam-extract` request and the reconciler docstring
  (`specs/deferred_items.md`, section `15-usaspending-vendor-links`).
