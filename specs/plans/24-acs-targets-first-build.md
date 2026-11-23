# ACS targets, first full build under a memory guard: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 9

**Goal:** Land the 12 Codex commits, write the cause of the three failed builds into git, then run one guarded full-data ACS target build and one guarded `verify`, and record the outcome.

**Architecture:** One standard-library script, `scripts/stage9_guard.py`, has two roles. The supervisor process starts a child, samples its physical footprint, free disk and wall clock, and stops it by the spec's rules. The child process calls the same `acs_target_bundle` entry functions as the `acs_targets` CLI, turns the first SIGTERM into a `BaseException` so the build's own cleanup runs, dumps frame-only stack traces to its control directory, and writes a message-free failure record. Tests force every stop with stand-in children and, in a slow dry run, with the real build on the synthetic V12 fixture chain.

**Tech Stack:** Python 3.14 standard library (`subprocess`, `signal`, `os.wait4`, `ctypes` on `libproc`, `faulthandler`, `argparse`), pytest, the existing `embedding_data.acs_target_bundle` and `tests/acs_target_fixtures.py`.

**Spec:** `specs/acs-targets-first-build.md` (approved 2026-11-23). The targets themselves are governed by `specs/acs-targets.md`, which this plan does not change.

## Global Constraints

- Every command on the production root passes `--data-dir /Users/lowell/Projects/embedding-data/data`. The guard has no default data root.
- Before every commit, every full pytest run and every full-data command, run `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`. If it prints a line, read it: a shell wrapper that only contains that `pgrep` text is a false positive; a real `embedding_data.acs_targets` process is a stop. This binds this session too: no commit, full pytest run or push while the guarded build or `verify` runs.
- One full-data build at a time across all sessions, and one acquisition at a time.
- No change to `pyproject.toml`, `uv.lock`, any file in `acs_target_inputs.SOFTWARE_FILES`, any frozen module, or any acceptance script. No new module under `src/embedding_data/`. Never add a test tool to `pyproject.toml` or `uv.lock`.
- No test reads the real host's free space or carries `CHILD_TOKEN` for longer than one short `ps` check. Every test sets `launch_floor_bytes`, `disk_soft_bytes` and `disk_hard_bytes` to 0, or injects `free_bytes`, unless it forces a disk stop. Test children carry `TEST_TOKEN`, so other sessions' `pgrep` checks never see them. These tests run in every session's hooks, also after the production build has used its disk.
- Never edit a `.py` file while a full pytest run is going (the ACS reconciliation tests hash every `.py` file).
- Preserve every r1–r3 path and control: `stage9_acs_targets_20261019_r1`, `stage9_acs_targets_20261021_r2`, `stage9_acs_targets_20261021_r3` (their `.part` and `-scratch-*` directories under `data/derived/acs/targets/`) and `stage9_acceptance_20261019_r1`, `stage9_acceptance_20261021_r2`, `stage9_acceptance_20261021_r3` under `data/derived/acs/target-controls/`. Never reuse those run IDs.
- Leave alone: branch `codex/acs-targets-design` (head `1a6377d`) and its worktree `/Users/lowell/.codex/worktrees/acs-targets-design/embedding-data` (read only), and every worktree this session did not create (today `.claude/worktrees/stage-11-plan`).
- Plan 9's execution rules do not carry over: no `SKIP=coverage-check`, no D2 evidence-reuse receipt, no Codex worktree. Use the normal hooks.
- `/private/tmp` does not last. Keep nothing there that the plan needs later, apart from throwaway test roots. Use uv's default cache, not `/private/tmp/embedding-data-uv-cache`.
- Run profile: `POLARS_MAX_THREADS=1`, `POLARS_IDEAL_MORSEL_SIZE=8192`. The child runs from the run worktree's `.venv/bin/python`, never through `uv run`.
- Stop rules (spec section 2, verbatim values): physical footprint 24 GiB → SIGKILL at once; free disk under 50 GiB → SIGTERM, then wait up to 2 h; free disk under 20 GiB → SIGKILL; wall clock 48 h for `build` and 48 h for `verify` → SIGTERM, then wait up to 2 h; a SIGTERM grace period that ends → SIGKILL. Launch floor: at least 350 GiB free before the build, or stop and ask the owner.
- Each production write needs the owner's go-ahead: the build, the `verify` (both write guard controls under `data/derived/`) and any later cleanup. The supervisor never removes leftover scratch.
- Source rows never leave this machine or enter git. Controls and the findings file hold aggregates and frame locations only, never an exception message.
- The PR merges with a merge commit, never squash or rebase.

## Review Focus

1. **A second SIGTERM arrives while the build unwinds** (the parent-watch thread and the supervisor can both send one, and a person may press Ctrl-C). Expected: the unwind finishes and removes scratch and `.part`. Pinned by `test_second_sigterm_does_not_interrupt_cleanup` (Task 4).
2. **The supervisor dies mid-run** (the app quits, the terminal closes). Expected: the child stops cleanly within seconds, removes its scratch, and does not hold the host. Pinned by `test_child_stops_cleanly_when_supervisor_dies` (Task 4).
3. **Message text leaks through a path other than `failure.json`**: the default uncaught-exception print, `threading.excepthook`, `sys.unraisablehook` or a warning. Expected: a sentinel value in an exception message appears in no stdout, stderr or control file. Pinned by `test_no_message_text_reaches_any_output` (Task 4).
4. **An occupied or forbidden run ID**: an r1–r3 ID, an existing run, `.part` or control directory, or a missing `--data-dir`. Expected: refusal before any child starts, with nothing written. Pinned by `test_refusals_write_nothing` (Task 5).
5. **The temporary volume fills during `verify`**: `verify_bundle` re-derives every table in `tempfile.gettempdir()`, not in the data root. Expected: the disk floors watch that volume too. Pinned by `test_disk_floor_watches_the_temp_volume` (Task 5).

## Decisions

- **D1** (owner, plan review, 2026-11-23): this plan takes a plan id free of the parallel Stage 11 and Stage 15 plans. The owner chose 23. The Stage 11 session took 23 before the commit, so the plan is 24. Applied in: the file name, Task 1 Step 4, Task 9 Step 4.

The spec's four owner decisions and every "Claude's call" are in its "Owner decisions (2026-11-23)".

## Files

| Path | Role | Task |
|---|---|---|
| `specs/plans/completed/10-acs-targets.md` | Plan 10, copied unchanged under a new status line | 1 |
| `specs/naics-evaluation-data-stage-9-findings.md` | New findings: cause, follow-up, lost evidence, run, limits | 2, 9 |
| `scripts/stage9_guard.py` | Supervisor, child and post-checks (standard library only) | 3, 4, 5 |
| `tests/test_stage9_guard.py` | Unit tests and the slow dry run | 3–6 |
| `tests/stage9_guard_children.py` | Stand-in child processes for stop tests | 4, 5 |
| `tests/stage9_guard_fixture_child.py` | Dry-run child shim that restores the fixture's patched registries | 6 |
| `tests/conftest.py` | Add the dry-run tests to `SLOW_TESTS` (not hashed by any run) | 6 |
| `CLAUDE.md`, `README.md` | Stage 9 paragraphs | 9 |
| `specs/plans/completed/9-acs-targets.md` | Plan 9, retired with a note | 9 |

Branch `feat/stage-9-acs-first-build`, development worktree `.worktrees/stage-9-build` (gitignored), run worktree `.worktrees/stage-9-run` (detached at the run commit). Create both with plain `git worktree add` from the main checkout, not with `EnterWorktree`.

---

### Task 1: Land the Codex commits and plan 10

**Files:**
- Create: `specs/plans/completed/10-acs-targets.md`

**Interfaces:**
- Consumes: branch `codex/acs-targets-design` at `1a6377d`; the untracked `specs/plans/10-acs-targets.md` in the Codex worktree.
- Produces: branch `feat/stage-9-acs-first-build` whose history contains `6a30106`…`1a6377d`.

- [ ] **Step 1: Check the host and create the worktree.** Run the `pgrep` check. In the main checkout run `git branch --show-current`, `git status --short` and `git reflog -5` and touch nothing there. Then:

```bash
git -C /Users/lowell/Projects/embedding-data fetch
git -C /Users/lowell/Projects/embedding-data worktree add .worktrees/stage-9-build -b feat/stage-9-acs-first-build origin/main
cd /Users/lowell/Projects/embedding-data/.worktrees/stage-9-build && uv sync --locked
```

Expected: `git rev-parse codex/acs-targets-design` prints `1a6377d…`.

- [ ] **Step 2: Merge the Codex branch unchanged.** In the development worktree:

```bash
git merge --no-ff codex/acs-targets-design -m "Merge codex/acs-targets-design: plan 10 cost fixes for the Stage 9 build"
```

Expected: no conflict. The merge-commit hook runs the full suite (about 20 minutes) and passes. Do not edit any `.py` file while it runs.

- [ ] **Step 3: Verify the merge (spec Verification 1, local part).**

```bash
git merge-base --is-ancestor 1a6377d HEAD && echo ancestor
git diff --stat 1a6377d HEAD -- src/embedding_data/acs_target_estimation.py src/embedding_data/acs_target_projection.py src/embedding_data/acs_target_tables.py tests/test_acs_target_assembly_spill.py tests/test_acs_target_estimator_spill.py tests/test_acs_target_ordered_merge.py tests/test_acs_target_projection_spill.py tests/test_acs_target_tables.py tests/test_acs_target_validation_spill.py
git diff --stat origin/main HEAD -- pyproject.toml uv.lock
git rev-parse codex/acs-targets-design
```

Expected: `ancestor`; both diffs empty; `1a6377d…` unchanged. `tests/conftest.py` keeps the line that `1a6377d` added.

- [ ] **Step 4: Copy plan 10 under a status line.** Copy the Codex worktree's `specs/plans/10-acs-targets.md` byte for byte to `specs/plans/completed/10-acs-targets.md`, then insert two lines at the top: a status line and a blank line. Wording (builder may adjust; the date is the execution date): `**Status: SHIPPED (<YYYY-MM-DD>)** — its tasks shipped in commits 6a30106…1a6377d, merged into main by plan 24. Plan 24 (specs/plans/24-acs-targets-first-build.md) replaces its open checkpoints.`

Check: `tail -n +3 specs/plans/completed/10-acs-targets.md | cmp - /Users/lowell/.codex/worktrees/acs-targets-design/embedding-data/specs/plans/10-acs-targets.md` prints nothing.

- [ ] **Step 5: Commit** (docs-only, so the hooks skip the tests).

```bash
git add specs/plans/completed/10-acs-targets.md
git commit -m "docs(specs): record plan 10 as shipped by the Codex merge"
```

---

### Task 2: Findings file, cause first

**Files:**
- Create: `specs/naics-evaluation-data-stage-9-findings.md`

**Interfaces:**
- Consumes (read only): `specs/findings/stage-9-acs-targets.md`; in the Codex worktree, `.sdd/9-acs-targets/progress.md`, `.sdd/10-acs-targets/progress.md`, `first-launch-proposal.md`, `disk-design-proposal.md`, and `probe*-result.md`, `probe*-launch-authorization.md`, `probe-report.md` in `.sdd/10-acs-targets/`.
- Produces: sections 1–3 of the findings file, and headings for sections 4–6 that say "Pending the run" (Task 9 fills them).

- [ ] **Step 1: Write sections 1–3** in the structure of spec section 4:
  1. *Cause of the three failed builds*, one subsection per run (r1, r2, r3): guard, outcome, evidence, and what stays unproven. Restate every figure in the spec's "Measured facts" table from its source, with file and line. Cite ledger files by path, line and the SHA-256 of the file at the time of reading (`shasum -a 256`), because they are gitignored. Keep "the exact operator is unproven" where the spec says so.
  2. *What followed*: plan 10 Tasks 1–5, the fixes (`55921b5`, `520d49f`, `65e7896`, `6a6e14a`, `4fb8868`, `1a6377d`) and probes 1–8, with each probe's outcome, wall time and peak where the source gives them.
  3. *Evidence that is lost*: every `/private/tmp` path that the old finding or the ledgers cite and no longer exists (check with `test -e`), what it held, and the dates it went (2026-10-28, 2026-11-01 partial deletions; 2026-11-20 reboot).

  Top status line: `Status: Stage 9 in progress. The cause section is committed before the build starts.` Write prose to the plain-technical-English rule. No source rows, no exception messages.

- [ ] **Step 2: Check every figure has a source.** Each of these strings appears in the file next to a citation: `5,084.6`, `26,600,947,712`, `52,441`, `9.26`, `24.19`, `218.9`, `24.03`, `221.9`, `530`, `16.45`, `25.11`, `17,316`, `14.90`, `17.78`, `24.54`, `5,973`, `14,020`, `16,766`, `11,302`, `17.34`, `96.79`, `5,465`, `3.18`. Where a source gives a different value from the spec, the findings use the source value and say that the spec differs.

- [ ] **Step 3: Commit** (docs-only).

```bash
git add specs/naics-evaluation-data-stage-9-findings.md
git commit -m "docs(findings): write the cause of the three failed Stage 9 builds"
```

---

### Task 3: Guard measurement primitives

**Files:**
- Create: `scripts/stage9_guard.py` (module docstring, constants, measurement functions)
- Test: `tests/test_stage9_guard.py`

**Interfaces:**
- Produces, in `scripts/stage9_guard.py` (tests import it with `sys.path.insert(0, str(PROJECT_ROOT / 'scripts'))`, as other script tests do):
  - `GiB = 1024 ** 3`
  - `OLD_RUN_IDS: tuple[str, ...]` = the three r1–r3 target run IDs
  - `OLD_CONTROL_IDS: tuple[str, ...]` = the three `stage9_acceptance_*` control names
  - `phys_footprint(pid: int) -> int` — `ri_phys_footprint` from `proc_pid_rusage(pid, RUSAGE_INFO_V2, …)` through `ctypes`; raises `ProcessLookupError` for a reaped pid.
  - `free_bytes(path: Path) -> int` — `statvfs` `f_bavail * f_frsize`.
  - `watched_volumes(data_dir: Path, temp_dir: Path) -> dict` — `{'data': str, 'temp': str, 'same_device': bool}`.
  - `git_state(repository: Path) -> dict` — `{'head': str, 'porcelain': str}`.
  - `manifest_prefix(manifest: Path) -> dict` — `{'bytes': int, 'sha256': str}`.
  - `check_manifest_prefix(manifest: Path, prefix: dict, written: list[str]) -> dict` — `{'prefix_equal': bool, 'appended_lines': int, 'names_written_path': bool}`; `written` holds data-root-relative path prefixes this run wrote.
  - `preserved_inventory(data_dir: Path) -> dict[str, int]` — relative path → size for every file and directory under `derived/acs/targets/` whose top name starts with an `OLD_RUN_IDS` entry and under `derived/acs/target-controls/` whose top name is in `OLD_CONTROL_IDS`.
  - `bundle_size(directory: Path) -> dict` — `{'files': int, 'bytes': int}`, exact byte sum.
  - `last_phase(phase_log: Path) -> dict | None` — parses the last `faulthandler` dump in the file; returns `{'frames': [{'file', 'line', 'function'}, …], 'innermost_embedding_data': {'file', 'line', 'function'} | None}`.

- [ ] **Step 1: Write the failing tests.**

```python
def test_footprint_grows_with_allocation():
    # spawn `python -c` that allocates and touches 512 MiB, then blocks on stdin
    # before = footprint sample before the allocation signal, after = after it
    assert after - before >= 400 * 1024 ** 2

def test_footprint_of_reaped_pid_raises():
    with pytest.raises(ProcessLookupError):
        guard.phys_footprint(reaped_pid)

def test_manifest_prefix_detects_rewrite_and_allows_append(tmp_path):
    # write 3 lines, take prefix; append 1 line → prefix_equal True, appended_lines 1
    # rewrite byte 0 → prefix_equal False
    # append a line whose "path" starts with derived/acs/targets/<run> → names_written_path True

def test_preserved_inventory_covers_only_old_runs(tmp_path):
    # old .part, old -scratch-x, old control dir with files, plus a new run dir
    assert set(inventory) == {old paths} and no key starts with the new run ID

def test_bundle_size_is_exact(tmp_path):
    assert guard.bundle_size(d) == {'files': 11, 'bytes': sum_of_sizes}

def test_last_phase_reads_the_last_dump(tmp_path):
    # file with two faulthandler blocks ("Thread 0x… (most recent call first):"
    # then '  File "…/embedding_data/acs_target_tables.py", line 911 in derive_tables')
    assert result['innermost_embedding_data'] == {
        'file': '…/embedding_data/acs_target_tables.py', 'line': 911,
        'function': 'derive_tables'}  # from the LAST block, not the first

def test_watched_volumes_records_both(tmp_path):
    assert set(guard.watched_volumes(tmp_path, Path(tempfile.gettempdir()))) == {
        'data', 'temp', 'same_device'}
```

- [ ] **Step 2: Run them and see them fail.** `uv run --locked pytest tests/test_stage9_guard.py -v` → FAIL with `ModuleNotFoundError: No module named 'stage9_guard'`.

- [ ] **Step 3: Implement the functions above.** Standard library only. `faulthandler` writes the innermost frame first under "most recent call first", so `innermost_embedding_data` is the first frame of the last block whose path contains `/embedding_data/`.

- [ ] **Step 4: Run them and see them pass.** Same command → PASS.

- [ ] **Step 5: Commit** (`pgrep` check first; the commit hook runs the fast suite).

```bash
git add scripts/stage9_guard.py tests/test_stage9_guard.py
git commit -m "feat(stage9): add guard measurement primitives"
```

---

### Task 4: The guarded child

**Files:**
- Modify: `scripts/stage9_guard.py`
- Create: `tests/stage9_guard_children.py`
- Test: `tests/test_stage9_guard.py`

**Interfaces:**
- Consumes: `embedding_data.acs_target_bundle.build`, `verify_bundle`, `run_directory`; `embedding_data.acs_mapping_contract.SelectionRequest`; `embedding_data.acs_targets` (tests only, for the option comparison).
- Produces:
  - `CHILD_TOKEN = 'embedding_data.acs_targets'`; `TEST_TOKEN = 'stage9_guard_test_child'` (matches no part of `PGREP_PATTERN`)
  - `PGREP_PATTERN = r'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`
  - `class GuardStop(BaseException)`, `class DirtyWorktree(Exception)`
  - `install_stop_handler() -> None` — the first SIGTERM raises `GuardStop`; every later SIGTERM is ignored.
  - `install_quiet_hooks() -> None` — `sys.excepthook`, `threading.excepthook`, `sys.unraisablehook` and `warnings.showwarning` write only the class name (and, for warnings, category, file and line) to stderr.
  - `start_parent_watch(parent_pid: int, interval: float = 5.0) -> threading.Thread` — daemon thread; when `os.getppid() != parent_pid` it sends SIGTERM to its own process once.
  - `failure_record(error: BaseException) -> dict` — `{'class': 'module.QualName', 'errno': int | None, 'frames': [{'file', 'line', 'function'}], 'chain': ['module.QualName', …]}` from `__cause__`/`__context__`. Never `str(error)`, `args` or source-line text.
  - `child_argv(prefix: list[str], command: str, options: list[str], *, control_dir: Path, repository: Path, parent_pid: int, phase_interval: float, token: str = CHILD_TOKEN) -> list[str]` — `prefix + ['child', token, command, *options, '--control-dir', …, '--repository', …, '--parent-pid', …, '--phase-interval', …]`.
  - `parse_operation(command: str, options: list[str]) -> Callable[[], dict]` — argparse with exactly the `acs_targets` command's arguments (`build`: `RUN_ID --data-dir --mapping-run --mapping-outputs-sha256 --codes-run --codes-outputs-sha256 --geography-run --geography-outputs-sha256 --ipums-run --ipums-outputs-sha256 --ipums-references-sha256`; `verify`: `RUN_ID --data-dir --mapping-run --mapping-outputs-sha256 --outputs-sha256`), all required. Returns a closure that makes the same call the CLI makes (`acs_targets.py:46` and `:55`).
  - `child_main(argv: list[str]) -> int` — `return run_child(argv, expected_token=CHILD_TOKEN)`.
  - `run_child(argv: list[str], *, expected_token: str) -> int` — order: `install_stop_handler()`, `install_quiet_hooks()`, `start_parent_watch`, `faulthandler.enable` and `faulthandler.dump_traceback_later(phase_interval, repeat=True)` both into `<control_dir>/phase.log`; refuse unless `argv[0] == expected_token` (`argv` is everything after `child`); raise `DirtyWorktree` if `git_state(repository)['porcelain']` is not empty; only then import `embedding_data`; run the operation; on success print `json.dumps(result, sort_keys=True, allow_nan=False)` to stdout and return 0; on any `BaseException` write `<control_dir>/failure.json`, print exactly `ACS target validation failed.` to stderr and return 2. Signal handlers and hooks are installed before the heavy import, so a stop during import is also clean.
  - The script's `__main__` dispatches `child` to `child_main(sys.argv[2:])`.
  - `tests/stage9_guard_children.py MODE [ignored argv…]` — stand-in children that use the real child helpers: `sleep` (blocks 60 s), `scratch DIR` (creates `DIR/x.part` and a `TemporaryDirectory(dir=DIR)`, then loops; removes `x.part` in `finally`), `stubborn` (catches `GuardStop` and sleeps), `alloc BYTES` (allocates and touches, then sleeps), `ok JSON` (prints JSON, exits 0), and `child-leak SENTINEL CONTROL_DIR REPOSITORY` (patches `stage9_guard.parse_operation` to return a closure that emits a warning, raises in a worker thread, triggers an unraisable `__del__` error and then raises in the main thread, all with the sentinel in the message, and then calls the real `run_child` with `TEST_TOKEN`). Each other mode writes `failure.json` on `BaseException` the way `run_child` does. Stand-ins are started with `TEST_TOKEN` in their argv.

- [ ] **Step 1: Write the failing tests.**

```python
def test_child_options_match_cli():
    import typer
    from embedding_data import acs_targets
    group = typer.main.get_command(acs_targets.app)
    for name in ('build', 'verify'):
        cli = {p.opts[0] for p in group.commands[name].params}
        assert guard_option_names(name) == cli   # read from parse_operation's parser

def test_child_makes_the_cli_call(monkeypatch, cli_runner, data_directory):
    # patch acs_target_bundle.build and verify_bundle with recorders returning
    # {'run_id': 'r', 'directory': 'd', 'outputs_sha256': 'a' * 64} / {'status': 'verified'}
    # invoke the CLI with CliRunner and parse_operation(...)() with the same argv
    assert recorded_cli_calls == recorded_guard_calls   # positional and keyword, both commands

def test_child_argv_matches_pgrep_pattern(tmp_path):
    argv = guard.child_argv(['/venv/bin/python', 'scripts/stage9_guard.py'], 'build',
                            ['r4', '--data-dir', str(tmp_path)], control_dir=tmp_path,
                            repository=tmp_path, parent_pid=1, phase_interval=60.0)
    assert re.search(guard.PGREP_PATTERN, ' '.join(argv))
    test_argv = guard.child_argv(..., token=guard.TEST_TOKEN)   # same arguments otherwise
    assert not re.search(guard.PGREP_PATTERN, ' '.join(test_argv))

def test_run_child_refuses_a_wrong_token(tmp_path):
    assert guard.run_child([guard.TEST_TOKEN, 'build', ...], expected_token=guard.CHILD_TOKEN) == 2

def test_live_child_command_line_is_visible():
    # the only test child that carries CHILD_TOKEN: [sys.executable, children, 'sleep', 'child', CHILD_TOKEN]
    command = subprocess.check_output(['ps', '-o', 'command=', '-p', str(proc.pid)], text=True)
    assert re.search(guard.PGREP_PATTERN, command)
    # terminate at once: other sessions' pgrep sees it while it lives

def test_guard_stop_escapes_except_exception():
    assert not issubclass(guard.GuardStop, Exception)

def test_second_sigterm_does_not_interrupt_cleanup(tmp_path):
    # 'scratch' stand-in; send SIGTERM, then a second SIGTERM 0.1 s later
    assert proc.wait(timeout=30) == 2
    assert not (tmp_path / 'x.part').exists() and list(tmp_path.glob('tmp*')) == []
    assert json.loads(failure.read_text())['class'].endswith('GuardStop')

def test_child_stops_cleanly_when_supervisor_dies(tmp_path):
    # an intermediate process starts the 'scratch' stand-in with parent watch at 0.5 s,
    # then is SIGKILLed
    assert child_gone_within(15)
    assert not (tmp_path / 'x.part').exists() and list(tmp_path.glob('tmp*')) == []

def test_no_message_text_reaches_any_output(tmp_path):
    sentinel = 'SENTINEL-4f1c-value'
    # run the 'child-leak' stand-in (it drives the real run_child) with control_dir=tmp_path
    assert sentinel not in stdout + stderr
    assert all(sentinel not in f.read_text(errors='replace')
               for f in tmp_path.rglob('*') if f.is_file())
    assert set(json.loads((tmp_path / 'failure.json').read_text())) == {
        'class', 'errno', 'frames', 'chain'}

def test_failure_record_keeps_errno(tmp_path):
    # OSError(errno.ENOSPC, 'SENTINEL') → record['errno'] == errno.ENOSPC, no message

def test_child_refuses_dirty_repository(tmp_path):
    # git init + commit + an untracked file; run_child(..., expected_token=TEST_TOKEN) with an operation that would fail loudly
    assert exit_code == 2
    assert failure['class'].endswith('DirtyWorktree')
    # no embedding_data module was imported (check sys.modules in a subprocess)
```

- [ ] **Step 2: Run them and see them fail.** `uv run --locked pytest tests/test_stage9_guard.py -v -k "child or sigterm or supervisor_dies or message or errno or guard_stop"` → FAIL on missing names.

- [ ] **Step 3: Implement the child interfaces above.** Use `traceback.extract_tb` and keep only `filename`, `lineno`, `name`.

- [ ] **Step 4: Run them and see them pass.** Same command → PASS. Then `uv run --locked pytest tests/test_stage9_guard.py -v` → all PASS.

- [ ] **Step 5: Commit** (`pgrep` check first).

```bash
git add scripts/stage9_guard.py tests/stage9_guard_children.py tests/test_stage9_guard.py
git commit -m "feat(stage9): add the guarded child with a message-free failure record"
```

---

### Task 5: The supervisor and its command line

**Files:**
- Modify: `scripts/stage9_guard.py`
- Test: `tests/test_stage9_guard.py`

**Interfaces:**
- Consumes: Task 3 primitives, Task 4 `child_argv`, `CHILD_TOKEN`.
- Produces:
  - `RUN_PROFILE = {'POLARS_MAX_THREADS': '1', 'POLARS_IDEAL_MORSEL_SIZE': '8192'}`
  - `@dataclass(frozen=True) class Limits` — `footprint_bytes = 24 * GiB`, `disk_soft_bytes = 50 * GiB`, `disk_hard_bytes = 20 * GiB`, `deadline_seconds = 48 * 3600`, `grace_seconds = 2 * 3600`, `launch_floor_bytes = 350 * GiB`, `footprint_interval = 0.25`, `disk_interval = 30.0`, `phase_interval = 60.0`.
  - `@dataclass(frozen=True) class Probes` — `footprint: Callable[[int], int]`, `free_bytes: Callable[[Path], int]`, `clock: Callable[[], float]`; `Probes.default()` uses `phys_footprint`, `free_bytes`, `time.monotonic`.
  - `class GuardRefusal(Exception)` with a fixed `reason` string.
  - `control_directory(data_dir: Path, run_id: str, command: str) -> Path` — `<data>/derived/acs/target-controls/<run_id>-guard` for `build`, `<run_id>-verify-guard` for `verify`.
  - `preflight(command: str, run_id: str, data_dir: Path, repository: Path, limits: Limits, probes: Probes) -> dict` — read-only. Refuses: a run ID that fails `acs_target_bundle`'s safe-ID pattern `[A-Za-z0-9][A-Za-z0-9_-]*`; a run ID in `OLD_RUN_IDS`; for `build`, an existing run directory, `.part` or any `<run_id>-scratch-*`; for `verify`, a missing run directory; an existing control directory; a non-empty `git status --porcelain`; a missing `<repository>/.venv/bin/python` (unless the caller passes a child prefix); for `build`, free data-volume bytes under `launch_floor_bytes`. Returns `{'free_bytes': {'data': int, 'temp': int}, 'volumes': …, 'git': …}`.
  - `supervise(command: str, options: list[str], *, data_dir: Path, repository: Path, limits: Limits = Limits(), probes: Probes | None = None, child_prefix: list[str] | None = None, token: str = CHILD_TOKEN) -> dict` — runs `preflight`, then creates the control directory with `mkdir(exist_ok=False)`, writes `preserved-before.json` (build only) and `launch.json` (`manifest_prefix`, `launch_git`, `limits`, `profile`, `volumes`, child argv, `started_at`) before the child starts, then starts the child with `RUN_PROFILE` added to its environment and stdout/stderr to `child.stdout`/`child.stderr`, samples, stops, reaps with `os.wait4`, and writes `result.json`. Returns the result.
  - Stop order on each tick: footprint ≥ `footprint_bytes` → SIGKILL, reason `footprint`. Every `disk_interval`: the lower free value of the data and temp volumes < `disk_hard_bytes` → SIGKILL `disk_hard`; < `disk_soft_bytes` → SIGTERM `disk_soft`; elapsed ≥ `deadline_seconds` → SIGTERM `deadline`. After a SIGTERM, elapsed since it ≥ `grace_seconds` → SIGKILL with `escalated: true` and the first reason kept. Footprint and hard-disk checks continue during the grace period. The supervisor never deletes anything.
  - `samples.jsonl`: one line per `disk_interval`, `{'t': seconds, 'footprint_max': int, 'footprint_last': int, 'free': {'data': int, 'temp': int}}`.
  - `result.json` keys: `command`, `run_id`, `data_dir`, `repository`, `launch_git`, `exit_git`, `python`, `profile`, `limits`, `volumes`, `started_at`, `ended_at`, `wall_seconds`, `max_rss_bytes`, `peak_footprint_bytes`, `disk_low_bytes` (`data`, `temp`), `exit_status`, `signal`, `stop_reason`, `escalated`, `last_phase`, `failure` (the child's `failure.json` or `null`), `manifest_prefix`, `preserved_inventory_sha256`, `response` (the child's stdout JSON or `null`), `outputs_sha256` (the supervisor's own SHA-256 of `<run>/outputs.json`, build only), `bundle` (`bundle_size`, build only), `verify_status` (verify only), `ok`.
  - `ok` is true only if the child exited 0 and, for `build`, the run directory holds eleven files and `response['outputs_sha256'] == outputs_sha256`; for `verify`, `response['status'] == 'verified'`.
  - `post_checks(run_id: str, data_dir: Path) -> dict` — reads the build control's `launch.json` (for the manifest prefix taken before the child started) and `preserved-before.json`; returns one flat dict: the keys of `check_manifest_prefix` (with `written` = the run directory, `.part`, scratch and both control directories) plus `'preserved_equal': bool`. Writes nothing.
  - CLI: `stage9_guard.py build RUN_ID <the acs_targets build options>`, `stage9_guard.py verify RUN_ID <the acs_targets verify options>`, `stage9_guard.py post-checks RUN_ID --data-dir D`, plus `--repository` (default: the script's repository root), `--preflight-only` (print `preflight` JSON, write nothing) and one override flag per `Limits` field. The supervisor prints `result.json`'s content as one JSON line. Exit 0 if `ok`, 1 otherwise, 2 on `GuardRefusal` (one line `Stage 9 guard refused: <reason>` on stderr).

- [ ] **Step 1: Write the failing tests** (stand-in children through `child_prefix=[sys.executable, CHILDREN, MODE, …]` and `token=TEST_TOKEN`; small `Limits` with all disk limits 0 unless forced; a fake `free_bytes` where needed).

```python
def test_footprint_limit_kills_at_once(tmp_path):
    result = supervise_standin('alloc', str(512 * 1024 ** 2),
                               limits=Limits(footprint_bytes=256 * 1024 ** 2, …))
    assert result['signal'] == signal.SIGKILL and result['stop_reason'] == 'footprint'
    assert result['peak_footprint_bytes'] >= 256 * 1024 ** 2 and not result['escalated']

def test_soft_disk_floor_sigterms_and_cleans(tmp_path):
    # free_bytes returns 40 GiB; 'scratch' stand-in in a data-root subdirectory
    assert result['stop_reason'] == 'disk_soft' and result['signal'] is None
    assert result['failure']['class'].endswith('GuardStop')
    assert no_part_or_scratch_left(tmp_path)

def test_hard_disk_floor_kills(tmp_path):        # free_bytes returns 10 GiB → SIGKILL, 'disk_hard'

def test_deadline_sigterms(tmp_path):            # deadline_seconds=1 → 'deadline', clean exit

def test_grace_expiry_escalates_to_kill(tmp_path):
    # 'stubborn' stand-in, deadline 1 s, grace 1 s
    assert result['signal'] == signal.SIGKILL and result['stop_reason'] == 'deadline'
    assert result['escalated'] is True

def test_disk_floor_watches_the_temp_volume(tmp_path):
    # free_bytes returns 1 TiB for the data path and 40 GiB for the temp path
    assert result['stop_reason'] == 'disk_soft'
    assert result['disk_low_bytes']['temp'] == 40 * GiB

@pytest.mark.parametrize('case', ['old_run_id', 'occupied_run', 'occupied_part',
    'occupied_scratch', 'occupied_control', 'missing_data_dir', 'unsafe_run_id',
    'dirty_repository', 'below_launch_floor'])
def test_refusals_write_nothing(tmp_path, case):
    before = snapshot(tmp_path)          # every path with its size and mtime
    with pytest.raises(GuardRefusal):    # or exit 2 through the CLI for missing_data_dir
        ...
    assert snapshot(tmp_path) == before and no_child_started

def test_launch_record_exists_while_the_child_runs(tmp_path):
    # 'sleep' stand-in; poll until the child is alive, then read launch.json
    assert launch['manifest_prefix']['bytes'] == manifest_size_before_launch
    assert launch['launch_git']['porcelain'] == ''

def test_supervisor_never_imports_polars(tmp_path):
    # run the supervisor CLI in a subprocess on an 'ok' stand-in, with a flag-free
    # wrapper that prints sorted(sys.modules) at exit
    assert not {'polars', 'embedding_data'} & top_level_modules

def test_result_records_measurements_and_git(tmp_path):
    # 'ok' stand-in that also prints the two RUN_PROFILE variables it sees
    assert result['ok'] is True and result['wall_seconds'] > 0 and result['max_rss_bytes'] > 0
    assert result['launch_git'] == result['exit_git'] and result['launch_git']['porcelain'] == ''
    assert result['response']['env'] == RUN_PROFILE
    assert (control / 'samples.jsonl').exists() and (control / 'child.stderr').exists()

def test_build_pin_is_the_supervisors_own_hash(tmp_path):
    # stand-in writes 11 files incl. outputs.json under the run directory and prints a response
    assert result['outputs_sha256'] == hashlib.sha256(outputs.read_bytes()).hexdigest()
    # a second case prints a wrong outputs_sha256 → result['ok'] is False, exit 1

def test_post_checks_detect_manifest_rewrite_and_preservation_change(tmp_path):
    # after a stand-in build: append an unrelated line → prefix_equal True, preserved_equal True
    # change one old .part file's size → preserved_equal False
```

- [ ] **Step 2: Run them and see them fail.** `uv run --locked pytest tests/test_stage9_guard.py -v` → new tests FAIL on missing names.

- [ ] **Step 3: Implement the supervisor interfaces above.** Reap with `os.wait4(pid, os.WNOHANG)` on each tick. `ru_maxrss` is in bytes on macOS. Read the child's `phase.log` through `last_phase` after reaping.

- [ ] **Step 4: Run them and see them pass.** `uv run --locked pytest tests/test_stage9_guard.py -v` → PASS. Then `uv run --locked ruff check scripts/stage9_guard.py tests/` → no findings.

- [ ] **Step 5: Commit** (`pgrep` check first).

```bash
git add scripts/stage9_guard.py tests/test_stage9_guard.py tests/stage9_guard_children.py
git commit -m "feat(stage9): add the guard supervisor, stop rules and post-checks"
```

---

### Task 6: Synthetic dry run on the V12 fixture chain

**Files:**
- Create: `tests/stage9_guard_fixture_child.py`
- Modify: `tests/test_stage9_guard.py`, `tests/conftest.py` (`SLOW_TESTS` only)

**Interfaces:**
- Consumes: `acs_target_fixtures.authenticated_mapping(tmp_path, monkeypatch, prepare_acs=prepare_target_delivery)` (returns `data_dir`, `request`, `mapping`, `mapping_outputs_sha256`); `stage9_guard.supervise`, `child_main`, `post_checks`, `Limits`, `Probes`.
- Fact measured at planning (2026-11-23): a fresh process cannot build the seeded fixture (`ipums_references` refuses the original), because the fixture patches five registries in-process. Restoring them in the child makes both `build` and `verify_bundle` pass (about 3.5 min on all cores). The five are `REGISTRY` of `embedding_data.acs_mapping_references`, `code_references`, `geography_references` and `ipums_references`, and `CT_REGISTRY` of `acs_mapping_references`.
- Produces: `tests/stage9_guard_fixture_child.py STATE_PICKLE child TEST_TOKEN …` — loads the pickle, sets each `(module, attribute)` to its value, then calls `stage9_guard.run_child(sys.argv[3:], expected_token=TEST_TOKEN)`, the same path as production `child_main`. It lives under `tests/` only, and `scripts/stage9_guard.py` never imports it. The dry run passes `child_prefix=[sys.executable, FIXTURE_CHILD, str(state_pickle)]` and `token=TEST_TOKEN`, so its minutes-long children stay invisible to other sessions' `pgrep` checks.

- [ ] **Step 1: Write the failing tests.** A module-scoped fixture seeds the chain once under `pytest.MonkeyPatch.context()`, pickles every `REGISTRY`/`CT_REGISTRY` attribute of each loaded `embedding_data.*` module, and makes a clean throwaway git repository to pass as `repository`. Tests use `Limits(launch_floor_bytes=0, disk_soft_bytes=0, disk_hard_bytes=0, phase_interval=0.5)` with the production footprint, deadline and grace values, except where a stop is forced, and `token=TEST_TOKEN`.

```python
def test_dry_run_guarded_build_and_verify(seeded):
    built = supervise('build', build_options(seeded, 'dry_r1'), …)
    assert built['ok'] is True and built['bundle']['files'] == 11
    assert built['outputs_sha256'] == sha256(run_dir / 'outputs.json')
    assert built['peak_footprint_bytes'] > 0 and built['max_rss_bytes'] > 0
    checked = supervise('verify', verify_options(seeded, 'dry_r1', built['outputs_sha256']), …)
    assert checked['ok'] is True and checked['verify_status'] == 'verified'
    checks = post_checks('dry_r1', seeded.data_dir)
    assert checks['prefix_equal'] and not checks['names_written_path'] and checks['preserved_equal']

@pytest.mark.parametrize('stop', ['disk_soft', 'deadline'])
def test_dry_run_soft_stop_leaves_no_scratch(seeded, stop):
    # probes flip (free_bytes → 40 GiB, or clock + 49 h) once <run>.part exists and 2 s passed
    assert result['stop_reason'] == stop and result['signal'] is None
    assert result['failure']['class'].endswith('GuardStop')
    assert not any(targets.glob(run + '*'))           # no final, .part or -scratch-*
    assert result['last_phase']['innermost_embedding_data'] is not None

@pytest.mark.parametrize('stop', ['footprint', 'disk_hard'])
def test_dry_run_hard_stop_leaves_only_sigkill_paths(seeded, stop):
    # probes flip (footprint → 25 GiB, or free_bytes → 10 GiB) under the same trigger
    assert result['signal'] == signal.SIGKILL and result['stop_reason'] == stop
    assert {p.name for p in targets.glob(run + '*')} <= {run + '.part'} | scratch_names(run)
    assert not (targets / run).exists()
    assert result['last_phase']['innermost_embedding_data'] is not None
```

Each forced-stop test uses its own run ID in the same seeded root. Each test also asserts, for its own run, that the raw manifest prefix from its `launch.json` holds; the module fixture's teardown asserts that `preserved_inventory` of the seeded root is unchanged (no reliance on test order under xdist).

- [ ] **Step 2: Run them and see them fail.** `uv run --locked pytest tests/test_stage9_guard.py -v -k dry_run` → FAIL (no shim).

- [ ] **Step 3: Write the shim** to the interface above. Add the four dry-run test node IDs (with the parametrized ones by base name) to `SLOW_TESTS` in `tests/conftest.py`.

- [ ] **Step 4: Run them and see them pass.** Same command → PASS. Record the wall time of the whole module in the task report. Then `uv run --locked pytest -m 'not network and not slow' tests/test_stage9_guard.py` deselects the dry run.

- [ ] **Step 5: Commit** (`pgrep` check first).

```bash
git add tests/stage9_guard_fixture_child.py tests/test_stage9_guard.py tests/conftest.py
git commit -m "test(stage9): dry-run the guard on the synthetic V12 chain"
```

---

### Task 7: Software and host ready

**Files:** none changed. This task fixes the run commit.

- [ ] **Step 1: Repository checks on the run commit** (spec section 3 step 1). In the development worktree, with a clean `git status --porcelain`, and after the `pgrep` check:

```bash
uv run --locked pytest
uv run --locked behave
uv run --locked ruff check .
uv lock --check
git diff --stat origin/main HEAD -- pyproject.toml uv.lock
```

Expected: every pytest test passes (the `network` canary deselected), every Behave scenario passes, Ruff prints nothing, the lock check passes, the diff is empty. Record `RUN_COMMIT=$(git rev-parse HEAD)` and the pytest totals.

- [ ] **Step 2: Confirm the cause section is in git** (Verification 4): `git log -1 --format='%H %cI' -- specs/naics-evaluation-data-stage-9-findings.md` names a commit that is an ancestor of `RUN_COMMIT`.

- [ ] **Step 3: Create the run worktree.**

```bash
git -C /Users/lowell/Projects/embedding-data worktree add --detach .worktrees/stage-9-run "$RUN_COMMIT"
cd /Users/lowell/Projects/embedding-data/.worktrees/stage-9-run && uv sync --locked && git status --porcelain
```

Expected: `git status --porcelain` prints nothing. Nothing writes into this worktree from now on: no `nohup.out`, no log, no test run.

- [ ] **Step 4: Preflight without writing.** Choose `RUN_ID=stage9_acs_targets_$(date +%Y%m%d)_r4`, or the next free `rN` if `preflight` reports it occupied.

```bash
STAGE9_DATA=/Users/lowell/Projects/embedding-data/data
STAGE9_MAPPING=stage8_acs_mapping_20261018_r7
STAGE9_MAPPING_PIN=1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4
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
.venv/bin/python scripts/stage9_guard.py build "$RUN_ID" "${STAGE9_BUILD_ARGS[@]}" --preflight-only
```

Shell state does not persist between tool calls, so repeat these assignments (and `RUN_ID`, `RUN_COMMIT`) at the top of every later command that uses them. Expected: exit 0 and a JSON line with `free_bytes.data` ≥ 375,809,638,400 (350 GiB). If it refuses on the launch floor, stop and ask the owner (spec section 3 step 3). The Stage 8 verifiers are not run (spec section 3 step 4).

---

### Task 8: Guarded build, then guarded verify (two owner gates)

**Files:** none in git. Writes under `data/derived/acs/` only after each go-ahead.

- [ ] **Step 1: Gate 1, the build.** Run the `pgrep` check and read any hit. Ask the owner, in one message: the run ID, `RUN_COMMIT`, the preflight free space, that no other session runs a full-data build or an acquisition, and that the run takes no Stage 9 freeze window. Wait for a clear go-ahead.

- [ ] **Step 2: Launch detached** from the run worktree, so the run outlives this session and the app (the child stops if its supervisor dies). The launch log goes outside both worktrees and `/private/tmp`:

```bash
mkdir -p "$HOME/Library/Logs/embedding-data"
cd /Users/lowell/Projects/embedding-data/.worktrees/stage-9-run
nohup caffeinate -i -s .venv/bin/python scripts/stage9_guard.py build "$RUN_ID" "${STAGE9_BUILD_ARGS[@]}" > "$HOME/Library/Logs/embedding-data/$RUN_ID-guard.launch.log" 2>&1 < /dev/null &
```

Expected within a minute: `pgrep -fl 'embedding_data\.acs_targets'` shows the child, and `data/derived/acs/target-controls/$RUN_ID-guard/samples.jsonl` grows. Then wait for `result.json` (a Monitor until-loop on its existence, or the owner resumes the session). Commit nothing and run no full suite meanwhile.

- [ ] **Step 3: Read the outcome.** From `result.json`: `ok`, `stop_reason`, `last_phase`, `failure`, the measurements and `outputs_sha256`. Check the pin independently: `shasum -a 256 "$STAGE9_DATA/derived/acs/targets/$RUN_ID/outputs.json"` equals `outputs_sha256`. If `ok` is false, skip to Task 9 (failure path): no second attempt and no fix (decision 2).

- [ ] **Step 4: Gate 2, the verify.** Ask the owner for the second go-ahead, with the build's figures, the bundle size and the current free space of the data and temp volumes next to the 350 GiB launch figure (verify re-derives every table in the temp volume).

- [ ] **Step 5: Launch the verify detached**, the same way:

```bash
nohup caffeinate -i -s .venv/bin/python scripts/stage9_guard.py verify "$RUN_ID" --data-dir "$STAGE9_DATA" --mapping-run "$STAGE9_MAPPING" --mapping-outputs-sha256 "$STAGE9_MAPPING_PIN" --outputs-sha256 "$STAGE9_PIN" > "$HOME/Library/Logs/embedding-data/$RUN_ID-verify-guard.launch.log" 2>&1 < /dev/null &
```

`STAGE9_PIN` is `outputs_sha256` from the build's `result.json`. Expected at the end: `result.json` in `$RUN_ID-verify-guard/` with `ok: true` and `verify_status: verified`. `launch_git` and `exit_git` in both results name `RUN_COMMIT` with an empty `porcelain` (Verification 2).

---

### Task 9: Light checks and the record

**Files:**
- Modify: `specs/naics-evaluation-data-stage-9-findings.md`, `CLAUDE.md`, `README.md`
- Move: `specs/plans/9-acs-targets.md` → `specs/plans/completed/9-acs-targets.md`

This task runs on success and on failure (spec section 3, last paragraph).

- [ ] **Step 1: Light checks** (spec section 3 step 6, Verifications 7 and 8), from the run worktree:

```bash
.venv/bin/python scripts/stage9_guard.py post-checks "$RUN_ID" --data-dir "$STAGE9_DATA"
uv run --locked embedding-data audit --data-dir "$STAGE9_DATA"
```

Expected: `prefix_equal: true`, `names_written_path: false`, `preserved_equal: true`; the audit exits 0 with zero discrepancies. Run `git -C .worktrees/stage-9-run status --porcelain` once more: empty.

- [ ] **Step 2: Fill findings sections 4–6** in the development worktree. Section 4 gives the run ID, the detached pin, `RUN_COMMIT` with its clean status, and for build and `verify` the wall time, maximum RSS, peak physical footprint and disk low point (data and temp), the bundle's file count and exact bytes, and the per-product target row counts from `report.json` (aggregates only). Section 5 states what is not claimed: no replay, no `compare-runs`, no independent reconciliation, no preservation gate, no scientific acceptance, every target `size_gate_pending`, no training use (R8.4). Section 6 binds every reader to the limits of `specs/acs-targets.md` by reference. Change the status line.

  On failure: section 4 instead gives the run ID, the stop reason, `escalated`, the last phase, the failure class and `errno`, the measurements, and the paths the run left (names and sizes, read-only). Then ask the owner to choose: a reviewed fix and a new run, retiring plan 9, or a redesign. Record the choice in the findings. Leftover scratch stays until the owner says otherwise.

- [ ] **Step 3: Update `CLAUDE.md` and `README.md`.** Replace the Stage 9 text that says "Task 10 remains in progress" (`CLAUDE.md`, "ACS target software (Stage 9)"; `README.md` near lines 1387–1428) with: the run ID, its detached pin, the guarded build and verify invocations (`stage9_guard.py` with `STAGE9_BUILD_ARGS` written out), a pointer to the new findings file, and the sentence that Stage 9's first build took no freeze window. Keep the r1 history as one sentence pointing at the findings file.

- [ ] **Step 4: Retire plan 9.** `git mv specs/plans/9-acs-targets.md specs/plans/completed/9-acs-targets.md` and add a status line under its title: plan 24 (`specs/plans/24-acs-targets-first-build.md`) replaced its Tasks 10 and 11. Re-point any relative link the move breaks. The move does not retire `specs/acs-targets.md`: it stays in `specs/`, because the findings (section 6), `CLAUDE.md` and the deferred old Stages 12–13 bind to it. Plan 9 gets no history entry or deferral scan of its own: its status note points at this plan, whose history entry covers it.

- [ ] **Step 5: Commit** (`pgrep` check first, after the guarded runs have exited).

```bash
git add specs/naics-evaluation-data-stage-9-findings.md CLAUDE.md README.md specs/plans/
git commit -m "docs(stage9): record the first guarded ACS target build"
```

---

### Task 10: One PR, merged with a merge commit

Run the Plan Completion Protocol first (tick the steps, deferred items, the roadmap tick and stamp, history, retire this plan), so the PR carries those commits. Tick Stage 9 only if `verify` passed, or the owner retired plan 9 and the findings say so (spec Rollout). Add a deferred item for the hardening (replay, `compare-runs`, `scripts/reconcile_stage9.py`, freeze and preservation), to become a Track F outcome before O20 at the next roadmap resume.

- [ ] **Step 1: Push and open the PR.** `pgrep` check, then `git push -u origin feat/stage-9-acs-first-build` (the pre-push hook runs the full suite). Open the PR with a body that names the 12 Codex commits and the run. Expected: GitHub shows `6a30106`…`1a6377d` in the PR's commits.

- [ ] **Step 2: Merge with a merge commit** under the pr-lifecycle rule, using `--merge`, never `--squash` or `--rebase`. Then confirm Verification 1 on `origin/main`: `git merge-base --is-ancestor 1a6377d origin/main` and `git rev-parse codex/acs-targets-design` is still `1a6377d…`.

- [ ] **Step 3: Clean up** this session's worktrees from the main checkout after the merge: `.worktrees/stage-9-run` and `.worktrees/stage-9-build` (`git worktree remove`), the local feature branch, and `git fetch --prune`. Leave the Codex worktree and branch, and every worktree this session did not create.
