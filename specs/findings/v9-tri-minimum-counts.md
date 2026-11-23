# V9 (TRI): headline minimum count for the parent links

Measured on 2026-11-23 with `scripts/measure_tri_minimum_counts.py` (plan 20, Task 5) at the
rule commit in section 2. This record discharges spec R7.3 and V9 for one family only: the
TRI parent links of roadmap Stage 5. TRI is EPA's Toxics Release Inventory. R7.3 asks for a
headline minimum count set by measurement. V9 sets it for each family after its first full
build. Roadmap Stage 22 delivers it as outcome O13. The design is in
`specs/tri-minimum-counts.md`. The record holds counts, rates, constants, run IDs and pins
only. It holds no TRIFD (EPA's stable TRI facility ID), no parent name, no owner key, no node
ID and no list of cells.

## 1. Decision

The TRI parent-link family gets a headline minimum of 1. The rule in section 2 gives the
minimum from the curves in section 5. A row of `tri_parent_links.parquet` meets its gate when
its `n_unweighted` is at least 1. Consumers filter on that published column.

A cell is an ordered pair of distinct NAICS 2022 industries. `n_unweighted` is the number of
distinct owners that have an eligible facility in each of the two industries in the same
reporting year. An owner is EPA's standardized U.S. parent company. An owner counts once,
even when it links the pair in several of the years 2022 to 2024. The family has one target
and one measure, `owner_share`, so it has one minimum.

| Measure | Minimum | Published count the minimum applies to | Rows that meet it | Share of rows | Share of support |
| --- | ---: | --- | ---: | ---: | ---: |
| `owner_share` | 1 | `n_unweighted` of `tri_parent_links.parquet` | 14,204 of 14,204 | 1.0000 | 1.0000 |

Support is the sum of `n_unweighted` over the rows. It is 22,686 (section 6). Shares are
rounded to 4 decimals.

Both mirror rows of an industry pair have the same `n_unweighted`. So they meet or miss the
gate together. The 14,204 kept rows are 7,102 industry pairs.

A minimum of 1 is a measured outcome. The spec names it a valid result. It means that cells
with a count of 1 already recur at `LEVEL` or more. The count-1 band has a rate of 0.9673 in
2022 → 2023 and 0.9841 in 2023 → 2024, against a `LEVEL` of 0.90 (section 5). Every higher
band has a rate above the count-1 band in both year pairs. So no top band missed `LEVEL`, and
the stop for a family without a minimum did not apply. The gate removes no published row.

The count-1 bands are the closest to `LEVEL`. Their lower Wilson bounds are 0.9634 and 0.9812,
also above `LEVEL`. The rule uses the point estimate, so the interval does not enter it. The
intervals are also too narrow (section 9).

## 2. Rule and constants

Recurrence rule (spec "The rule"): a cell is headline evidence when cells of its count recur
in the next reporting year.

**Per-year counts.** `E` is the set of eligible facility-years of `tri_facility_years.parquet`
(`exclusion_reason` is null). Each has a reporting year `t` (2022, 2023 or 2024), a TRIFD, a
node `naics_2022_node_id` (the facility's NAICS 2022 industry) and an owner `owner_key`. For
an ordered pair of distinct nodes `(a,b)`, `j_t(a,b)` is the number of distinct owners with a
facility-year of `E` at node `a` and one at node `b` in year `t`. It equals `j_{t}` of
`tri_parent_link_support.parquet` (a self-check). An owner `facility:<TRIFD>` has one
facility-year in each year. So it never forms a cell.

**Base, recurring, staying and testable cells.**

- A base cell of year `t` has `j_t(a,b) ≥ 1`.
- A base cell recurs when `j_{t+1}(a,b) ≥ 1`. Any owner counts, the same owner included.
  This is recurrence through any owner.
- A facility-year of `E` in year `t` is staying when its TRIFD also has a facility-year of
  `E` in year `t+1` under the same owner key.
- A base cell is testable when one owner has a staying facility-year at node `a` and a
  staying facility-year at node `b` in year `t`.

Exits do not count. A facility that leaves TRI makes no cell testable. A facility that files
an ineligible facility-year in `t+1` (`naics_conflict`, `naics_not_2022` or `federal`) makes
no cell testable either. The node of the `t+1` facility-year does not enter testability,
because a changed code is what the test looks for. The Stage 5 findings record 0 owner-key
changes, so an owner keeps its facilities in every year. The test cannot see a change of
ownership.

**Band rule.** For each year pair:

1. Put each testable cell into a band by its base-year count `j_t(a,b)`. The bands are 1 to 9
   and `10+`.
2. Upward merge. Merge each band below `10+` with fewer than `MIN_BAND_CELLS` testable cells
   into the next higher band. Repeat until each band below the top has enough cells. A merged
   band starts at its lowest count.
3. Downward merge. If the top band now has fewer than `MIN_BAND_CELLS` testable cells and a
   band lies below it, merge the top band once into the band directly below it. The merged
   band starts at the start of the lower band.
4. Total check. A year pair with fewer than `MIN_BAND_CELLS` testable cells in total gets no
   minimum (reason `too_few_testable_cells`).
5. Divide a band's recurring cells by its testable cells to get its rate.
6. Take the lowest starting count of a band that reaches `LEVEL`, where every higher band also
   reaches `LEVEL`. That count is the year pair's minimum.

The family minimum is the larger of the two year-pair minimums. If a year pair gets no minimum
under step 4, or its top band misses `LEVEL` (reason `top_band_misses_level`), the family gets
no minimum. The stage then stops for the owner, and no fallback applies. Rates use the point
estimate.

| Constant | Value | Meaning |
| --- | --- | --- |
| `LEVEL` | 0.90 | Lowest recurrence rate a band may have and still support the minimum |
| `TOP_BAND` | 10 | Counts of this size and more form one top band |
| `MIN_BAND_CELLS` | 50 | A band with fewer testable cells merges (steps 2 and 3), and a year pair with fewer gets no minimum (step 4) |
| `WILSON_Z` | 1.959963984540054 | The z of the 95% Wilson interval. The interval is reported for each band. It does not enter the rule |
| `YEAR_PAIRS` | `((2022, 2023), (2023, 2024))` | The reporting-year pairs RY2022 → RY2023 (`2022-2023`) and RY2023 → RY2024 (`2023-2024`) |

Rule commit: `b282dd7c6c2f186d7e22593dfa405e1fe1af5868`. The script, its tests and these
constants were committed there before the first real run, on a clean tree. Both real runs ran
at this commit.

**OC3 disclosure.** OC3 is plan 20's owner checkpoint for a refusal on real data. It allows
only a fix toward the written rule, and this record must disclose that fix. No OC3 fix was
made. `scripts/measure_tri_minimum_counts.py`, its test file, `src/`, `pyproject.toml` and
`uv.lock` are unchanged since the rule commit. The rule commit `b282dd7` ("fix(scripts): print
only the reason when Polars panics in the Stage 22 measurement") carries the last script
change. It landed before the first real run, so it is not an OC3 fix. Both runs exited 0, so
OC2 (the stop when the family has no minimum) did not apply. The branch took in `origin/main`
afterwards, by the merge commit `31a90b0`. That merge added the Stage 21 script and test files
and no other code.

**Merges.** The downward merge and the total check did not act. In each year pair the output
shows two upward merges. Count 7 merged into count 8 (band `7–8`), and count 9 merged into the
top band (band `9+`). So each top band starts at 9, not at `TOP_BAND`. The rule merges a band
only when it has fewer than `MIN_BAND_CELLS` testable cells. The output does not hold the band
sizes before these merges. `before_downward_merge` is null in both year pairs, so no band was
merged downward. Each year pair has far more than `MIN_BAND_CELLS` testable cells (12,464 and
11,882), and each top band has 100 or more.

## 3. Inputs

The script read one Stage 5 bundle in place and rebuilt nothing. It checked the detached
`outputs.json` SHA-256 first. Then it checked each of the four files it read against its record
(SHA-256 and size) in `outputs.json`, before it trusted any content.

| Input | Value |
| --- | --- |
| Run ID | `stage5_tri_parent_links_20261121_r1` |
| Directory under `--data-dir` | `derived/epa_tri/parent-links/` |
| Detached `outputs.json` SHA-256 | `65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b` |

The four read files, with the SHA-256 values from `inputs.files` of the output:

| File | SHA-256 |
| --- | --- |
| `report.json` | `dc002222c0d9fa652f5623ef089dc324a000625d8a23fd681b3d227ed98d6a6e` |
| `tri_facility_years.parquet` | `6af624e3bf4159944a742182b0be0c6f8ff1445f83de85afa7b64b390e66d8ab` |
| `tri_parent_link_support.parquet` | `ae64765bbdd57d5c23ef0ef9fce0e6997a51d01f14491bf309b55ebe0e02310b` |
| `tri_parent_links.parquet` | `331392fe80e8688cbd0230e7fb6abe44d06d7d047851fbedf0a84462e60efab5` |

The `report.json` SHA-256 equals its record in the Stage 18 finding
(`specs/findings/stage-5-tri-parent-links.md`). The script read only the columns that the spec
lists under "Inputs". The replay `stage5_tri_parent_links_20261121_r1_replay` was not read. The
Stage 18 finding shows that its five Parquet files and its `report.json` have the same bytes as
those of the first run.

Before any curve, each run passed every self-check of the spec. The script stops on any
difference, and both runs exited 0. The checks are:

- The facility-year keys (`reporting_year`, `trifd`) are unique. Every year is in 2022 to 2024.
  Every eligible row has an owner key and a node.
- The TRIFDs of `E` with more than one distinct owner key number `owner_key_changes` of
  `report.json`.
- The distinct owners of `E`, pooled and by year, equal `n_owners.headline` and
  `owners_by_year.<year>.headline` of `report.json`.
- The pooled recount over `E` gives the cells of `tri_parent_link_support.parquet`, and for
  every cell the same `j_owners`, `j_2022`, `j_2023` and `j_2024`.
- `tri_parent_links.parquet` has one row for each support cell. Every `measure` is
  `owner_share`. Each `n_unweighted` equals the cell's `j_owners`.
- The `n_unweighted` distribution, recomputed with the bundle's own `distribution` function,
  equals `n_unweighted_distribution` of `report.json`.

The script did not recheck `j_dnb`, `j_including_federal` and the two sensitivity labels. They
need private columns that no published table holds. It read the labels from `flags` as
published, only to count kept rows.

## 4. Run

Both runs used this command, from the worktree root, under `/usr/bin/time -l`. `OUT` was
`$HOME/.cache/embedding-data/stage22-minimum-counts/b282dd7`. Run 2 wrote `run2.json` and
`run2.time`. Each run exited 0 and printed one sorted JSON line with `complete` true.

```bash
/usr/bin/time -l uv run --offline --locked python scripts/measure_tri_minimum_counts.py \
  --data-dir /Users/lowell/Projects/embedding-data/data \
  --run stage5_tri_parent_links_20261121_r1 \
  --outputs-sha256 65159b8374d36beec136ae6a7779a5763bf8ced9360e2a365b67b138e10b7f8b \
  > "$OUT/run1.json" 2> "$OUT/run1.time"
```

| Run | Output SHA-256 |
| --- | --- |
| 1 | `4a5cfd7b480e4076ebad14225685ba2fa969e5e210548477928e037fd9a85e53` |
| 2 | `4a5cfd7b480e4076ebad14225685ba2fa969e5e210548477928e037fd9a85e53` |

The two outputs are byte-identical (4,193 bytes each, `cmp` reported `identical`). The check of
Task 5 Step 5 (`find` under the data tree for files newer than the start marker) printed
nothing, so the runs wrote nothing under `data/`. The output stays in `$OUT`, outside the
repository and outside `data/`. It never enters git, and this record cites it by its SHA-256
only.

Run 1 took 0.18 s wall time (0.20 s user, 0.23 s system). Its maximum resident set size was
185,171,968 bytes (0.19 GB). Both figures come from `/usr/bin/time -l`, which wrapped `uv run`.

The wall time is not called loaded. A saved process list holds the output of
`pgrep -fl 'embedding_data|embedding-data'`, taken right before and right after each run. All
four lists have the same six lines. Each line is a `/bin/zsh -c` wrapper whose command text
runs `while pgrep -f "cov=embedding_data" >/dev/null; do sleep 5; done; echo hook-finished`.
That text contains `embedding_data`, so the broad pattern matches it. No list holds any other
process, so none shows another job. The narrow freeze-window check
(`pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`) printed
nothing before each run.

## 5. Curves

Each table is one year pair. A band groups testable cells by their base-year count
`j_t(a,b)`. Terms:

- **Base cells:** cells with `j_t(a,b) ≥ 1`.
- **Testable:** base cells with one owner that has staying facility-years at both industries
  (section 2).
- **Recurring:** testable cells that recur in the next year.
- **Rate:** recurring divided by testable.
- **95% Wilson interval:** the interval around the rate. It is for readers only.

A band written `7–8` merged count 7 into count 8. A band written `9+` is the top band, which
started at 9 after count 9 merged into it. Rates and bounds are rounded to 4 decimals. The
JSON output holds full precision. Every count in the tables is even, because both mirror rows
of an industry pair are cells.

### RY2022 → RY2023 (`2022-2023`)

| Band | Base cells | Testable | Recurring | Rate | 95% Wilson interval |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 9,330 | 8,818 | 8,530 | 0.9673 | 0.9634–0.9709 |
| 2 | 2,192 | 2,184 | 2,172 | 0.9945 | 0.9904–0.9969 |
| 3 | 710 | 710 | 710 | 1.0000 | 0.9946–1.0000 |
| 4 | 320 | 320 | 320 | 1.0000 | 0.9881–1.0000 |
| 5 | 140 | 140 | 140 | 1.0000 | 0.9733–1.0000 |
| 6 | 82 | 82 | 82 | 1.0000 | 0.9552–1.0000 |
| 7–8 | 110 | 110 | 110 | 1.0000 | 0.9663–1.0000 |
| 9+ | 100 | 100 | 100 | 1.0000 | 0.9630–1.0000 |
| All | 12,984 | 12,464 | 12,164 | | |

Minimum for this year pair: **1**.

### RY2023 → RY2024 (`2023-2024`)

| Band | Base cells | Testable | Recurring | Rate | 95% Wilson interval |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 9,242 | 8,294 | 8,162 | 0.9841 | 0.9812–0.9866 |
| 2 | 2,198 | 2,188 | 2,186 | 0.9991 | 0.9967–0.9997 |
| 3 | 658 | 658 | 658 | 1.0000 | 0.9942–1.0000 |
| 4 | 320 | 320 | 320 | 1.0000 | 0.9881–1.0000 |
| 5 | 130 | 130 | 130 | 1.0000 | 0.9713–1.0000 |
| 6 | 104 | 104 | 104 | 1.0000 | 0.9644–1.0000 |
| 7–8 | 86 | 86 | 86 | 1.0000 | 0.9572–1.0000 |
| 9+ | 102 | 102 | 102 | 1.0000 | 0.9637–1.0000 |
| All | 12,840 | 11,882 | 11,748 | | |

Minimum for this year pair: **1**.

The downward merge did not happen in either year pair (`before_downward_merge` is null), so
there is no second table of bands before it. The family minimum is the larger of the two
year-pair minimums, which is 1.

## 6. Kept counts

"Kept" means that a row's `n_unweighted` is at least the minimum (1). "Support" is the sum of
`n_unweighted` over the rows. A kept row is "lenient" when its largest single-year count
(`j_2022`, `j_2023` or `j_2024`) is below the minimum. Shares are rounded to 4 decimals.

| Value | `owner_share` |
| --- | ---: |
| Minimum | 1 |
| `rows` (published rows) | 14,204 |
| `support` (sum of `n_unweighted`) | 22,686 |
| `kept_rows` | 14,204 |
| `kept_row_share` | 1.0000 |
| `kept_support` | 22,686 |
| `kept_support_share` | 1.0000 |
| `lenient_kept_rows` | 0 |
| `dnb_rows` (rows with the D&B label) | 8,050 |
| `kept_dnb_rows` | 8,050 |
| `federal_rows` (rows with the federal label) | 40 |
| `kept_federal_rows` | 40 |

The 14,204 kept rows are 7,102 industry pairs, half of the kept rows (section 1).

The D&B label is `numerator:dnb_key_sensitivity:true`. A row carries it when its count under
the D&B owner key (built from Dun & Bradstreet numbers) differs from `n_unweighted`. The federal
label is `numerator:federal_sensitivity:true`. A row carries it when its count with federal
facilities included differs from `n_unweighted`. Both labels stay as the bundle published them.
Rows with a label are gated on their published `n_unweighted`, like the other rows. All 8,050
rows with the D&B label and all 40 rows with the federal label are kept.

No kept row is lenient. The eighth Limit says that the gate is "a little lenient", because it
uses pooled counts and the curves use single-year counts (section 9). Here `lenient_kept_rows`
is 0. With a minimum of 1 this is expected. A published cell has at least one owner in some
single year, so its largest single-year count is at least 1.

The pooled `n_unweighted` distribution follows, as `report.json` gives it. The script
recomputed it from the targets with the bundle's own definition, and the two agreed. The keys
`ge_k` count the rows with `n_unweighted` of `k` or more. The percentiles are nearest-rank
values, so they are whole numbers.

| Key | Value |
| --- | ---: |
| `count` | 14,204 |
| `min` | 1 |
| `p25` | 1 |
| `median` | 1 |
| `p75` | 2 |
| `p90` | 3 |
| `max` | 50 |
| `ge_1` | 14,204 |
| `ge_2` | 4,034 |
| `ge_3` | 1,652 |
| `ge_5` | 490 |
| `ge_10` | 94 |

The kept rows agree with this distribution. `ge_1` equals `count`, so a minimum of 1 keeps all
14,204 rows. The rows with a count of exactly 1 number 10,170 (`ge_1` less `ge_2`). These
figures equal those that the Stage 5 findings publish.

## 7. Deviation

Plan 20 records one `> Deviation:` note in its header. It is quoted here. Its roadmap line
numbers are as of `89949ef`. Section 4 gives the cost.

> Deviation: the Stage 22 Consumes line (roadmap `:286`) names `report.json` and the
> per-cell `n_unweighted` column of `tri_parent_links`. The O13 cost cell (roadmap `:63`) says
> "one pass over the TRI family's `n_unweighted` counts, like O4". Under D1 the measurement
> also reads `tri_facility_years.parquet` and `tri_parent_link_support.parquet` of the run, and
> it recomputes per-year owner counts (owner, D1, 2026-11-22, spec "Rollout").

The measurement read more than the roadmap's Consumes line names, as the owner decided (D1 of
the spec, reporting-year recurrence with a TRIFD link). The roadmap Exit holds as written: one
minimum, from the observed `n_unweighted` counts split by reporting year. Section 6 reports how
many cells meet it.

## 8. Disclosure: figures seen at design time

The spec records under Anti-goals what the design session had seen before the rule was fixed.
The spec text follows, word for word.

> *Disclosure (2026-11-22):* before the rule was fixed, the session had seen these figures
> about the family and no others. All are published in the Stage 5 findings, which the owner
> can also read:
> - `n_unweighted` per row: 14,204 rows, minimum 1, median 1, 75th percentile 2, 90th
>   percentile 3, maximum 50. 4,034 rows have 2 or more, 1,652 have 3 or more, 490 have 5 or
>   more and 94 have 10 or more.
> - Facility-years by year and exclusion reason: eligible 21,534, 21,324 and 20,974,
>   `federal` 448, 449 and 438, `naics_conflict` 108, 87 and 61, `naics_not_2022` 22, 10 and
>   9, totals 22,112, 21,870 and 21,482.
> - Owners: headline 8,684 (8,080, 7,952 and 7,818 by year), D&B key 12,850, federal
>   included 8,700, 0 owner-key changes, 0 parent-name collisions, 4,566 U.S. parents (median 2
>   facilities and 1 industry, at most 477 facilities and 63 industries).
> - 405 industries in the marginals, 264 D&B-only cells, 298 federal-only cells and 102
>   partial owners.
> - Facility-years with a D&B number: 13,560, 13,397 and 13,188 (section "E7 and E8
>   measures").
>
> The downward merge of a thin top band (below) was proposed because only 94 rows (47
> industry pairs) have a pooled count of 10 or more. The session had also seen the V9 curves
> of the three ITA families. No per-year count, no testable count, no recurrence rate and no
> minimum for this family had been measured. Nobody opened `report.json` or any Parquet file
> of the run during design.

Planning read no data of the run either. The plan's tests use small synthetic bundles under a
temporary `--data-dir`, and no test reads the real tree. Planning ran the frozen `estimate`
(`tri_parent_link_targets.estimate`) on synthetic fixture records only. Task 5 first read the
run after the rule commit. Its Step 3 hashed `outputs.json` and read the `report.json` record
in it. Then the two real runs read the four files of section 3.

## 9. Limits

These are the nine Limits of the spec, copied as written. Section 6 gives the measured
leniency.

- Recurrence measures whether the self-reported codes that hold a cell up stay the same among
  facilities that keep filing. It does not measure truth. A facility with a wrong code that
  files the same code every year recurs every year.
- **E8 time basis.** EPA's standardized parent is the current owner at the snapshot, not the
  owner in each year. So the test cannot see a change of ownership, and a cell can rest on an
  ownership that did not hold in the base year.
- Testability keeps only cells with a linking pair of facilities that both file eligibly
  again. Facilities that leave TRI are out, and so are ineligible refiles. The published
  counts bound the `naics_*` refiles only: 97 `naics_*` facility-years in RY2023 and 70 in
  RY2024. They do not bound a facility that turns `federal`.
- RY2024 completeness depends on the snapshot (2025-11-05). Under this rule a missing RY2024
  report removes a cell from the test. It does not count as a failure.
- Codes are self-reported and unvalidated.
- TRI is a program-selected population, mostly industrial. It is not a frame of
  establishments or firms. Cells that the bundle does not emit get no statement.
- Mirrored cells count each industry pair twice, so the Wilson intervals are too narrow.
- The gate applies to counts pooled over three reporting years, so it is a little lenient
  (measured).
- The minimum is a reliability floor for headline use. It is not a coefficient-of-variation
  rule.

Notes on the Limits:

- The 97 and 70 come from the Stage 5 published counts (RY2023: 87 `naics_conflict` plus 10
  `naics_not_2022`. RY2024: 61 plus 9). This measurement did not recount them.
- The seventh Limit applies to every interval in section 5. 50 cells are 25 industry pairs,
  and the interval counts each pair twice. So the true uncertainty of a rate is wider than its
  interval shows.
- The eighth Limit is measured in section 6. No kept row is lenient (`lenient_kept_rows` is
  0).

## 10. Not claimed

- No Stage 5 bundle is rebuilt or relabeled. `size_gate_pending` stays on every row of
  `stage5_tri_parent_links_20261121_r1` and of its replay.
- No protocol section for the family (O17, its section in `specs/evaluation-protocol.md`).
  Scoring, null models, splits and the treatment of absent (zero) cells belong to it.
- No minimum for the marginal, support, parent-industry or facility-year tables
  (`tri_parent_link_marginals`, `tri_parent_link_support`, `tri_parent_industries`,
  `tri_facility_years`). They are support, not targets.
- No minimum for the cells that exist only under a sensitivity (264 under the D&B key and 298
  with federal facilities, from the Stage 5 findings). They are not published rows.
- No minimum for any other family.
- No embedder result. No embedder output, score or ranking was read (R8.4, which keeps
  benchmark tables out of embedder training).
- A row that meets the gate is not a true relation. Recurrence measures how stable the
  self-reported codes are that hold a cell up. It is not accuracy, truth or a
  coefficient-of-variation rule. Section 9 states what the curves measure.
