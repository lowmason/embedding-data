# NAICS evaluation data — Stage 24 findings: protocol section for the ACS wage microdata

Stage 24 of `specs/naics-evaluation-data-roadmap.md` holds its Exit (2026-11-23). The owner
approved the stage spec `specs/completed/acs-wage-protocol-section.md` on 2026-11-23
("Approve"). Its section is now Section 2 of `specs/evaluation-protocol.md`. Stage 24 has no
plan.

**What the section states.**

| Exit item | Where |
| --- | --- |
| Evidence: run, pin and Stage 19 minimum | Section 2, Evidence: run `stage17_acs_wage_microdata_20261119_r1`, pin `6cb253e2…01d1`, the Parquet and `report.json` hashes, and the minimum of 400 headline rows for each category in each year |
| Assignment: which part selects and which part judges (R8.4) | Section 2, Assignment: the selecting part chooses the panel's settings and the candidate that goes forward. The sealed judging part judges and is opened once |
| Conditions, including the in-place read under R8.1 | Section 2, W1 to W9. W2 is the in-place read |
| Who decides the scores | naics-embedder's wage panel spec, once the owner names it in Section 2 (W7). No such spec exists at naics-embedder `2b2029c` |

**Owner decisions this stage.**

| Id | Decision |
| --- | --- |
| Q1 | The selecting part may choose the panel's settings and which embedder candidate goes forward ("b") |
| Q2 | naics-embedder's wage panel spec fixes the split, under limits in the section ("a") |
| Q3 | The drafted assignment and conditions, not corrected ("write the spec") |
| Q4 | Record the Q1 exception in R8.1, R8.4, `CLAUDE.md` and `README.md` ("a") |

**Measured cost.** One design session on 2026-11-23. One subagent read the draft as a
builder:

| Subagent | Model | Tokens | Wall time |
| --- | --- | ---: | ---: |
| Builder check of the stage spec | Opus | 149,436 | 195 s |

The check raised five points. The owner settled one (Q4). The other four are marked as my
calls in the stage spec.

**Data reads.** The SHA-256 of the run's `outputs.json` and `report.json`, and the aggregate
keys of `report.json`. Both hashes equal the recorded values. No person row was read, no
full-data command ran and no file was downloaded.

**For later work.**
- **naics-embedder.** The wage file stays unscored until its wage panel spec exists and the
  owner names it, at a commit, in Section 2 (W7). That spec decides the split, the regimes,
  the comparators, the metrics, the margin and the decision. It also decides how a category
  that meets the gate in only one year is handled.
- **Stage 16.** Its in-flight draft also numbers new sections from 2. Whichever of Stages
  16, 23, 24 and 25 merges later renumbers its sections in `specs/evaluation-protocol.md`.
  The condition IDs W1 to W9 stay unchanged.

**Not claimed.** No panel result, score or ranking. No source, test or data file changed.
The Stage 17 runs and the Stage 19 record are unchanged. No output feeds embedder training,
curriculum or hard-negative mining (R8.4). The only selection allowed is on the selecting
part, under the exception of 2026-11-23.
