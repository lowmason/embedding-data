# Development history

## 12-ita-naics-minimum-counts — 2026-11-17
Plan: specs/plans/completed/12-ita-naics-minimum-counts.md · Spec: specs/completed/ita-naics-minimum-counts.md (retired) · Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 3

Differences from the design:
- Ruling (Task 1): (unclear) Task 1 merged band low starts at the raw band index (1) even when leading raw bands are empty — plan test test_band_rate_and_wilson pins low=1 and spec line 183 'A merged band starts at its lowest count' reads either way — if wrong, only a band label changes when counts 1..k are empty, which real ITA data (many count-1 cells) will not produce. Owner kept it at the gate, 2026-11-17.
- Ruling (Task 4): Task 4 check_co_ownership refuses a targets table with a repeated cell (stricter than 'set') — fail-closed, and published targets are unique under the targets-v1 contract — if wrong, a real run refuses with exit 2 and OC3 stops for the owner, no wrong number is published.
- Ruling (Task 5): Task 5 check_area_mix treats a missing partition_by_year year as eligible 0 and takes the last of duplicate entries — the frozen _report builds entries by group_by (no duplicates), and a missing year with eligible rows still refuses because the recount is nonzero — if wrong, only a year with zero eligible rows and no entry passes, which changes no count.
- Ruling (Task 7): argparse usage errors exit 2 with empty stdout, same code as a refusal — the Task 8 command line is fixed and empty stdout distinguishes the two — if wrong, a typo in the command reads as a refusal and stops for the owner, never as a result.
- Deviation: the text-pair gate counts `n_headline_records`, not the Stage 3 Exit's `n_records`. Source: plan, header.
- Deviation (Task 8): one unrelated Hypothesis deadline flake in the full pytest run; the file passed alone. Source: plan, Task 8.
- Deviation (Task 9): the owner approved two extra docs fixes, so `README.md` also changes. Source: plan, Task 9.
- Decision D1 (spec amendment): a text pair is testable only when a linked eligible successor belongs to the same pair. Source: plan, `## Decisions`.
