# NAICS evaluation data — Stage 1 findings: ITA NAICS targets, first build

Stage 1 of `specs/naics-evaluation-data-roadmap.md` holds its Exit (2026-11-16). Plan 11
(`specs/plans/11-ita-establishment-targets.md`) ran Task 11 Steps 1, 3, 4, 6 (first run),
7 and 8 under D5 and D6. Stage 10 acceptance stays pending until Stage 4 writes
`specs/findings/stage-10-ita-establishment-targets.md`.

**Run.** `stage10_ita_establishment_20261116_r1` in
`data/derived/osha/establishment-targets/`. Owner go-ahead for Gate 2, with no Stage 9
freeze window open. `pgrep` printed nothing before each command.

| File | SHA-256 |
| --- | --- |
| `outputs.json` (detached pin) | `e19b0d58f61f106c3994aa6fe51f4fb71244188145dd90f8cccaa8dc8a8b09df` |
| `inputs.json` | `2225092a06f656a97933eb182e0b277c06f01b259e4dfd79626bc37368456b2d` |
| `report.json` | `7f1edba024bc7a290bb2682b95126450b921e6e3cba602aa9b887d3d2c587629` |

Executing commit `1f3abf0` (`dirty: false`). CPython 3.14.0, 63 distributions, 35
software files, `uv.lock` SHA-256 `f57c3280a7c8286711bf6804ca4c02f0a19619c9db52f33941b9c5b996cba8e5`.

**Measured cost** (`/usr/bin/time -l`, 36 GiB host). The bundle has 11 files,
160,736,016 bytes.

| Command | Wall time | Maximum RSS |
| --- | ---: | ---: |
| `build` | 53.86 s | 6,253,805,568 B |
| `verify` | 30.43 s | 6,398,885,888 B |
| `reconcile_stage10.py co-ownership` | 1.88 s | 471,384,064 B |
| `reconcile_stage10.py stage3` | 21.33 s | 2,920,824,832 B |

**Results.**
- `verify` with the pin: basis `adopted_v1_v3_finding`; source records, V1 and V2 `equal`.
- Rows: pairs 644,265; pair codes 771,971; pair members 3,206,055; NAICS paths 1,007;
  links 3,198,774; co-ownership 39,152; marginals 991; support 39,152.
- O1: pair records sum to 3,206,055 and to each year's V1 `n_rows`.
- O2: every co-ownership row has `size_gate_pending`. The reconciler reports equal:
  N 155,436 EINs, 39,152 cells and 991 industries on both sides.
- O3: the link table exists. The `stage3` reconciler reports V1 and V2 equal.
- Step 8: the summary, codes and both Stage 6 `outputs.json` hashes are unchanged, and
  their inventories verify. The manifest's first 3,007 lines equal the first snapshot.
  All 3,010 lines equal the Stage 1 snapshot (SHA-256 `0c610ce188e6ecc0a987db1726b34280c65bd7d42d3fbcd9448afeebdcddbb71`,
  2026-11-16T17:09:04Z). The audit reports 0 raw provenance discrepancies.

**For Stages 3 and 4.** Stage 3 reads the co-ownership `n_unweighted` counts of this
run. Stage 4 picks its own replay ID. `compare-runs` reads only tables and reports, so
only a `verify` of this run shows that Stage 4's checkout and venv keep the recorded
software identity. The plan 11 ledger's backup is
`/Users/lowell/.cache/agent-skills/handoffs/embedding-data/stage10-ledger-backup/workspace/`.
It holds 47 rulings: 44 `Ruling:` lines and 3 `Ruling (unclear):` lines.

**Not claimed.** Replay and `compare-runs`, the long-form finding, README and CLAUDE.md
pins, a V9 minimum count, scoring and null models. No output feeds embedder training,
curriculum, hard-negative mining or model selection (R8.4).
