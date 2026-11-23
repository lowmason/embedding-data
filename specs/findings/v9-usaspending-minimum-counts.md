# V9 (USAspending): headline minimum counts for the vendor links

Measured on 2026-11-22 with `scripts/measure_usaspending_minimum_counts.py` (plan 19, Task 5)
at the rule commit in section 2. This record discharges spec R7.3 and V9 for one family only:
the USAspending vendor links of roadmap Stage 14. R7.3 asks for a headline minimum count set by
measurement. V9 sets it for each family after its first full build. Roadmap Stage 21 delivers
it as outcome O26. The design is in `specs/completed/usaspending-minimum-counts.md`. The record holds
counts, rates, constants, run IDs and pins only. It holds no UEI (the SAM.gov unique entity ID
of a firm), no amount, no node ID and no list of cells.

## 1. Decision

`supplier_share` gets a headline minimum of 4, and `buyer_share` gets a minimum of 3. The rule
in section 2 gives each minimum from the curves in section 5. A row of `vendor_links.parquet`
meets its gate when its `n_unweighted` is at least its measure's minimum. Consumers filter on
that published column.

A cell is an ordered pair of NAICS 2022 national industries. `unit_a` is the supplier industry
(the subcontractor's industry), and `unit_b` is the buyer industry (the prime's industry). Each
cell has one row of each measure. Both counts pool FY2024 to FY2026:

- `supplier_share`: its `n_unweighted` counts the distinct subcontractors in the supplier
  industry that eligible pairs link to primes in the buyer industry.
- `buyer_share`: its `n_unweighted` counts the distinct primes in the buyer industry that
  eligible pairs link to subcontractors in the supplier industry.

| Measure | Minimum | Published count the minimum applies to | Rows that meet it | Share of rows | Share of support |
| --- | ---: | --- | ---: | ---: | ---: |
| `supplier_share` | 4 | `n_unweighted` of the `supplier_share` rows in `vendor_links.parquet` | 2,315 of 8,307 | 0.2787 | 0.8310 |
| `buyer_share` | 3 | `n_unweighted` of the `buyer_share` rows in `vendor_links.parquet` | 2,234 of 8,307 | 0.2689 | 0.7190 |

Support is the sum of `n_unweighted` over a measure's rows (section 6). Shares are rounded to
4 decimals.

The two rows of one cell are separate targets. One row can meet its gate while the other row
misses its gate. 1,785 cells have both rows kept.

FY2025 → FY2026 sets both minimums. Each measure's minimum is the larger of its two year-pair
minimums:

- `supplier_share`: 3 for `2024-2025` and 4 for `2025-2026`.
- `buyer_share`: 2 for `2024-2025` and 3 for `2025-2026`.

A minimum of 1 would have been a valid result. The spec names it a measured outcome, not a
broken rule. But no count-1 band reaches `LEVEL`. The four count-1 bands have rates from
0.6786 to 0.7609 (section 5). Every top band reaches `LEVEL` in both year pairs, so the
no-minimum stop did not apply.

The deciding bands are close to `LEVEL`. In `supplier_share` `2025-2026`, band 4 is at 0.9074
and band 3 is at 0.8825. In `buyer_share` `2025-2026`, band 3 is at 0.9235 and band 2 is at
0.8343. The lower Wilson bounds of the two deciding bands are 0.8669 and 0.8934, below
`LEVEL`. The rule uses the point estimate, so the interval does not enter it.

## 2. Rule and constants

Recurrence rule (spec "The rule"): a cell is headline evidence when cells of its count recur
in the next fiscal year.

**Per-year counts.** `P` is the set of eligible pairs of the pair table (`pair_status` is
`eligible`). A pair links one prime and one subcontractor. `P_t` holds the pairs of `P` with a
usable report in fiscal year `t` (`n_fy{t} > 0`). For a cell and a fiscal year `t`:

- `S_t` counts the distinct subcontractors of the cell's pairs in `P_t`.
- `B_t` counts the distinct primes of the cell's pairs in `P_t`.
- `L_t` counts the cell's pairs in `P_t`.

Firm industries and pair status stay as the bundle set them for the whole window.

**Base, recurring and testable cells.**

- A base cell of fiscal year `t` has at least one pair in `P_t`.
- A base cell recurs when any pair of `P_{t+1}` links the same two industries (owner decision
  D2 of the spec). The same pair counts.
- A base cell is testable when one of its pairs in `P_t` has two firms that stay active in
  their roles. The pair's subcontractor must be the subcontractor of some pair of `P_{t+1}`.
  The pair's prime must be the prime of some pair of `P_{t+1}`.

Exits do not count, as in the ITA V9 decision. A firm that stops contracting makes no cell
testable. The roles are fixed. A subcontractor that is only a prime in `t+1` does not make a
cell testable. Both measures share the testable and recurrence tests. Only the base-year count
differs: `S_t` for `supplier_share` and `B_t` for `buyer_share`.

**Band rule.** For each measure and year pair:

1. Put each testable cell into a band by its base-year count. The bands are 1 to 9 and `10+`.
2. Merge each band below `10+` with fewer than `MIN_BAND_CELLS` testable cells into the next
   higher band. Repeat until each band has enough cells or is the top band. A merged band
   starts at its lowest count.
3. Divide a band's recurring cells by its testable cells to get its rate.
4. Take the lowest starting count of a band that reaches `LEVEL`, where every higher band also
   reaches `LEVEL`. That count is the year pair's minimum.

A measure's minimum is the larger of its two year-pair minimums. If the top band misses
`LEVEL` in either year pair, the measure gets no minimum, and the stage stops for the owner.

| Constant | Value | Meaning |
| --- | --- | --- |
| `LEVEL` | 0.90 | Lowest recurrence rate a band may have and still support the minimum |
| `TOP_BAND` | 10 | Counts of this size and more form one top band |
| `MIN_BAND_CELLS` | 50 | A band below the top band with fewer testable cells merges into the next higher band |
| `WILSON_Z` | 1.959963984540054 | The z of the 95% Wilson interval. The interval is reported for each band. It does not enter the rule |
| `YEAR_PAIRS` | `((2024, 2025), (2025, 2026))` | The fiscal-year pairs FY2024 → FY2025 (`2024-2025`) and FY2025 → FY2026 (`2025-2026`) |

Rule commit: `588ae5a33af0d39445b4348fff6ce7f623c24f7b`. The script, its tests and these
constants were committed there before the first real run, on a clean tree. Both real runs ran
at this commit.

**OC3 disclosure.** OC3 is plan 19's owner checkpoint for a refusal on real data. It allows
only a fix toward the written rule, and this record must disclose that fix. No OC3 fix was
made. The script, its tests and `src/` are unchanged since the rule commit. The rule commit
`588ae5a` ("feat(scripts): report the Stage 21 minimum counts as one JSON line") carries the
last script change. It landed before the first real run, so it is not an OC3 fix. Both runs
exited 0, so OC2 (the stop when a measure has no minimum) did not apply.

One band merged. In `buyer_share` `2024-2025`, count 9 had fewer than `MIN_BAND_CELLS` testable
cells and merged upward. So that top band starts at 9 and is written `9+`. Every other top band
starts at 10.

## 3. Inputs

The script read one Stage 14 bundle in place and rebuilt nothing. It checked the detached
`outputs.json` SHA-256 first. Then it checked each read file against its record (SHA-256 and
size) in `outputs.json`, before it trusted any content.

| Input | Value |
| --- | --- |
| Run ID | `stage14_vendor_links_20261122_r2` |
| Directory under `--data-dir` | `derived/usaspending/vendor-links/` |
| Detached `outputs.json` SHA-256 | `248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be` |

The four read files, with the SHA-256 values from `inputs.files` of the output:

| File | SHA-256 |
| --- | --- |
| `report.json` | `040127fbb64d1dc7e2791f337506994092c4aab42abedfe3af94deff01f913d2` |
| `vendor_link_pairs.parquet` | `db9e70f9e09a667b319b0aa5db09cbff3af6b47b0e0b1d508d82e6444bd9903e` |
| `vendor_link_support.parquet` | `1e45184dedeede42c06b3623d39587810158c9b056af24ca9e2d3083d67ccfe2` |
| `vendor_links.parquet` | `a1e22e7321b82df9a6db84348da087502f0424eb999c35e0679a326d30bddfbd` |

The `report.json` SHA-256 equals its record in the Stage 20 finding
(`specs/findings/stage-14-usaspending-vendor-links.md`). The script read only the
`n_unweighted_distribution` entry of `report.json` and only the columns of the spec's "Inputs"
table. The replay `stage14_vendor_links_20261122_r2_replay` was not read. The Stage 20 finding
shows that its four Parquet files and its `report.json` have the same bytes as those of the
first run.

Before any curve, each run passed every self-check of the spec:

- The pair keys (`prime_uei`, `sub_uei`) are unique.
- Each eligible pair has both node IDs. Its `n_reports` equals the sum of its three
  fiscal-year counts.
- The pooled recount gives the cells and the `s_suppliers`, `b_buyers` and `l_pairs` of
  `vendor_link_support.parquet`.
- Each fiscal-year pair count `L_t` equals `l_fy{t}`.
- Each `supplier_share` row's `n_unweighted` equals `s_suppliers`. Each `buyer_share` row's
  `n_unweighted` equals `b_buyers`.
- The recomputed `n_unweighted` distribution of each measure equals its `report.json` entry.

## 4. Run

Both runs used this command, from the worktree root, under `/usr/bin/time -l`. `OUT` was
`$HOME/.cache/embedding-data/stage21-minimum-counts/588ae5a`. Run 2 wrote `run2.json` and
`run2.time`. Each run exited 0 and printed one sorted JSON line with `complete` true.

```bash
/usr/bin/time -l uv run --offline --locked python scripts/measure_usaspending_minimum_counts.py \
  --data-dir /Users/lowell/Projects/embedding-data/data \
  --run stage14_vendor_links_20261122_r2 \
  --outputs-sha256 248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be \
  > "$OUT/run1.json" 2> "$OUT/run1.time"
```

| Run | Output SHA-256 |
| --- | --- |
| 1 | `8b2e0e82719d37cf92c7f5de5b7e5de911e5408771df5ee45db1bf46d2c57ee6` |
| 2 | `8b2e0e82719d37cf92c7f5de5b7e5de911e5408771df5ee45db1bf46d2c57ee6` |

The two outputs are byte-identical (`cmp` reported `identical`). `find` under the data tree
found no file newer than the start marker, so the runs wrote nothing under `data/`. The output
stays in `$OUT`, outside the repository and outside `data/`. It never enters git, and this
record cites it by its SHA-256 only.

Run 1 took 0.36 s wall time (0.48 s user, 0.34 s system). Its maximum resident set size was
278,904,832 bytes (0.28 GB). Both figures come from `/usr/bin/time -l`, which wrapped `uv run`.

## 5. Curves

Each table is one measure and year pair. A band groups testable cells by their base-year count:
`S_t` for `supplier_share` and `B_t` for `buyer_share`. Terms:

- **Base cells:** cells with at least one pair in `P_t`.
- **Testable:** base cells with a pair whose two firms stay active in their roles in the next
  year (section 2).
- **Recurring:** testable cells that recur in the next year.
- **Rate:** recurring divided by testable.
- **95% Wilson interval:** the interval around the rate. It is for readers only.

Both measures share the cells of a year pair. So the "All" row of a year pair is the same for
both measures. Only the bands differ. Rates and bounds are rounded to 4 decimals. The JSON
output holds full precision.

### `supplier_share`, FY2024 → FY2025 (`2024-2025`)

| Band | Base cells | Testable | Recurring | Rate | 95% Wilson interval |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 3,021 | 1,936 | 1,406 | 0.7262 | 0.7059–0.7456 |
| 2 | 931 | 797 | 696 | 0.8733 | 0.8484–0.8946 |
| 3 | 453 | 419 | 388 | 0.9260 | 0.8969–0.9474 |
| 4 | 296 | 289 | 281 | 0.9723 | 0.9463–0.9859 |
| 5 | 162 | 158 | 154 | 0.9747 | 0.9367–0.9901 |
| 6 | 150 | 149 | 147 | 0.9866 | 0.9524–0.9963 |
| 7 | 106 | 104 | 104 | 1.0000 | 0.9644–1.0000 |
| 8 | 70 | 70 | 69 | 0.9857 | 0.9234–0.9975 |
| 9 | 67 | 67 | 66 | 0.9851 | 0.9202–0.9974 |
| 10+ | 546 | 546 | 545 | 0.9982 | 0.9897–0.9997 |
| All | 5,802 | 4,535 | 3,856 | | |

Minimum for this year pair: **3**.

### `supplier_share`, FY2025 → FY2026 (`2025-2026`)

| Band | Base cells | Testable | Recurring | Rate | 95% Wilson interval |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 3,029 | 1,674 | 1,136 | 0.6786 | 0.6559–0.7006 |
| 2 | 926 | 706 | 581 | 0.8229 | 0.7931–0.8493 |
| 3 | 465 | 400 | 353 | 0.8825 | 0.8472–0.9105 |
| 4 | 288 | 270 | 245 | 0.9074 | 0.8669–0.9365 |
| 5 | 172 | 168 | 159 | 0.9464 | 0.9013–0.9716 |
| 6 | 137 | 132 | 129 | 0.9773 | 0.9353–0.9922 |
| 7 | 116 | 113 | 106 | 0.9381 | 0.8776–0.9697 |
| 8 | 81 | 78 | 78 | 1.0000 | 0.9531–1.0000 |
| 9 | 60 | 59 | 59 | 1.0000 | 0.9389–1.0000 |
| 10+ | 546 | 542 | 540 | 0.9963 | 0.9866–0.9990 |
| All | 5,820 | 4,142 | 3,386 | | |

Minimum for this year pair: **4**.

### `buyer_share`, FY2024 → FY2025 (`2024-2025`)

| Band | Base cells | Testable | Recurring | Rate | 95% Wilson interval |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 3,614 | 2,463 | 1,874 | 0.7609 | 0.7436–0.7773 |
| 2 | 829 | 735 | 666 | 0.9061 | 0.8829–0.9251 |
| 3 | 407 | 393 | 379 | 0.9644 | 0.9411–0.9787 |
| 4 | 251 | 243 | 236 | 0.9712 | 0.9417–0.9860 |
| 5 | 142 | 142 | 142 | 1.0000 | 0.9737–1.0000 |
| 6 | 107 | 107 | 107 | 1.0000 | 0.9653–1.0000 |
| 7 | 74 | 74 | 74 | 1.0000 | 0.9507–1.0000 |
| 8 | 52 | 52 | 52 | 1.0000 | 0.9312–1.0000 |
| 9+ | 326 | 326 | 326 | 1.0000 | 0.9884–1.0000 |
| All | 5,802 | 4,535 | 3,856 | | |

Minimum for this year pair: **2**.

### `buyer_share`, FY2025 → FY2026 (`2025-2026`)

| Band | Base cells | Testable | Recurring | Rate | 95% Wilson interval |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 3,567 | 2,080 | 1,486 | 0.7144 | 0.6946–0.7334 |
| 2 | 847 | 694 | 579 | 0.8343 | 0.8048–0.8601 |
| 3 | 433 | 405 | 374 | 0.9235 | 0.8934–0.9456 |
| 4 | 242 | 236 | 225 | 0.9534 | 0.9185–0.9738 |
| 5 | 149 | 146 | 145 | 0.9932 | 0.9622–0.9988 |
| 6 | 117 | 116 | 113 | 0.9741 | 0.9267–0.9912 |
| 7 | 68 | 68 | 68 | 1.0000 | 0.9465–1.0000 |
| 8 | 63 | 63 | 62 | 0.9841 | 0.9154–0.9972 |
| 9 | 50 | 50 | 50 | 1.0000 | 0.9287–1.0000 |
| 10+ | 284 | 284 | 284 | 1.0000 | 0.9867–1.0000 |
| All | 5,820 | 4,142 | 3,386 | | |

Minimum for this year pair: **3**.

Each measure's minimum is the larger of its two year-pair minimums: 4 for `supplier_share` and 3
for `buyer_share`.

## 6. Kept counts

"Kept" means that a row's `n_unweighted` is at least its measure's minimum. "Support" is the
sum of `n_unweighted` over the rows. A kept row is "lenient" when its largest single-year count
(`S_t` or `B_t`, FY2024 to FY2026) is below the minimum. The intra-group rows carry the label
`numerator:intra_group_sensitivity:true`. Shares are rounded to 4 decimals.

| Value | `supplier_share` | `buyer_share` |
| --- | ---: | ---: |
| Minimum | 4 | 3 |
| `rows` (published rows) | 8,307 | 8,307 |
| `support` (sum of `n_unweighted`) | 50,936 | 26,109 |
| `kept_rows` | 2,315 | 2,234 |
| `kept_row_share` | 0.2787 | 0.2689 |
| `kept_support` | 42,330 | 18,773 |
| `kept_support_share` | 0.8310 | 0.7190 |
| `lenient_kept_rows` | 525 | 437 |
| `intra_group_rows` (rows with the intra-group label) | 52 | 19 |
| `kept_intra_group_rows` | 42 | 15 |

1,785 cells have both rows kept (`cells_meeting_both`). Each measure has one row for each
cell.

The gate is lenient for some rows, because it uses pooled counts and the curves use single-year
counts (spec "Leniency"). 525 of the 2,315 kept `supplier_share` rows are lenient. 437 of the
2,234 kept `buyer_share` rows are lenient. A lenient row meets the minimum with its pooled
count, but in no single fiscal year.

The 52 `supplier_share` rows and 19 `buyer_share` rows with the intra-group label are the 71
labeled rows of the spec. They are gated like the other rows. The 7 cells that exist only under
the intra-group sensitivity are not published rows and get no gate.

The pooled `n_unweighted` distribution of each measure follows, as `report.json` gives it. The
script recomputed it from the targets with the bundle's own definition, and the two agreed. Keys
`1`, `2`, `3` and `5` count rows with exactly that `n_unweighted`. `10+` counts rows with 10 or
more. The quantiles use Polars' `nearest` interpolation.

| Key | `supplier_share` | `buyer_share` |
| --- | ---: | ---: |
| `count` | 8,307 | 8,307 |
| `min` | 1 | 1 |
| `p25` | 1.0 | 1.0 |
| `median` | 2.0 | 1.0 |
| `p75` | 4.0 | 3.0 |
| `p90` | 11.0 | 6.0 |
| `max` | 1,101 | 260 |
| `1` | 4,025 | 4,810 |
| `2` | 1,320 | 1,263 |
| `3` | 647 | 645 |
| `5` | 311 | 223 |
| `10+` | 931 | 481 |

The kept rows agree with this distribution. For `supplier_share`, 8,307 rows less the 4,025,
1,320 and 647 rows with counts 1, 2 and 3 leave 2,315. For `buyer_share`, 8,307 rows less the
4,810 and 1,263 rows with counts 1 and 2 leave 2,234.

## 7. Deviations

Plan 19 records two `> Deviation:` notes in its header. Both are quoted here. Their roadmap
line numbers are as of `fd43236`.

### Consumes and cost

The measurement read more than the roadmap's Consumes line names, as the owner decided (D1 of
the spec, fiscal-year recurrence). Section 4 gives the cost.

> Deviation: the Stage 21 Consumes line (roadmap `:272`) names only `report.json` and the
> Stage 14 findings, and the O26 cost cell (roadmap `:75`) says "one pass over the family's
> `n_unweighted` counts". Under D1 the measurement also reads `vendor_link_pairs.parquet` (the
> UEI pair table), `vendor_link_support.parquet` and `vendor_links.parquet` of the run, and it
> recomputes per-year firm counts (owner, D1, 2026-11-22; spec "Rollout").

### The singular Exit

Section 1 gives the two minimums. Section 6 gives the kept rows of each target.

> Deviation: the Stage 21 Exit (roadmap `:274`) names "the headline minimum count" in the
> singular. The decision gives one minimum for `supplier_share` and one for `buyer_share`,
> and it reports for each target how many rows meet its own minimum (spec "Two minimums").
> The rest of the Exit holds as written.

## 8. Disclosure: figures seen at design time

The spec records under Anti-goals what the design session had seen before the rule was fixed.
The spec text follows.

> *Disclosure (2026-11-22):* before the rule was fixed, the session had seen these figures
> about the family and no others. All are published in the Stage 14 findings, which the owner
> can also read:
> - `n_unweighted` per cell: median 1 (`buyer_share`) and 2 (`supplier_share`), p90 6 and 11,
>   maximum 260 and 1,101. 4,810 of 8,307 `buyer_share` cells and 4,025 `supplier_share`
>   cells have count 1.
> - Usable reports by fiscal year: 227,218 (FY2024), 177,666 (FY2025) and 117,644 (FY2026).
> - Pair statuses (67,524 eligible, 22,569 `sub_ineligible`, 17,722 `prime_ineligible`, 147
>   intra-group and 32 self links), 28,410 suppliers and 2,215 buyers, 8,307 cells in 689
>   industries, 7 cells only under the sensitivity, 71 rows with the intra-group label, and
>   the diagonal (88 cells, 6,180 pairs).
>
> The session had also seen the V9 curves of the three ITA families. No per-year S or B, no
> testable count, no recurrence rate and no minimum for this family had been measured. Nobody
> opened `report.json` or any Parquet file of the run during design.

Planning read no data of the run either. The plan's tests use small synthetic bundles under a
temporary `--data-dir`, and no test reads the real tree. Task 5 first read the run after the
rule commit. Its Step 3 hashed `outputs.json` and read its `report.json` record. Then the two
real runs read the four files of section 3.

## 9. Limits

These are the nine Limits of the spec, copied as written. Section 6 gives the measured
leniency.

The seventh Limit says the gate is "a little lenient". The measurement shows more than that. 525 of
the 2,315 kept `supplier_share` rows (0.2268) meet the minimum in no single fiscal year. So do 437
of the 2,234 kept `buyer_share` rows (0.1956).

- Recurrence measures whether a relation between two industries persists among firms that
  still contract in their roles. It does not measure truth. A firm with a wrong SAM code that
  keeps the same contract recurs every year.
- Industries come from one SAM.gov extract (`2026-10`). Each firm's code at the extract date
  applies to every year. A code change over time is not seen.
- Testability keeps only cells with a pair whose two firms stay active in their roles. Cells
  of firms that leave federal contracting, or that switch roles, are under-represented in the
  curves.
- FY2026 is short. The snapshot (`2026-11-19`) came seven weeks after FY2026 ended, so late
  reports are missing. FY2026 has 117,644 usable reports, against 227,218 in FY2024. This
  pulls FY2025 → FY2026 recurrence down.
- Subaward reporting moved from FSRS.gov to SAM.gov on 2025-03-08, inside FY2025. A change in
  reporting can move recurrence.
- Pair status is pooled. A pair that is intra-group by one report is out of every year.
- The gate applies to counts pooled over three fiscal years, so it is a little lenient
  (measured).
- The population is federal prime contractors and the subcontractors that they report. It is
  not a frame of firms or of trade.
- The minimum is a reliability floor for headline use. It is not a coefficient-of-variation
  rule, and it says nothing about cells that the bundle does not emit.

## 10. Not claimed

- No Stage 14 bundle is rebuilt or relabeled. `size_gate_pending` stays on every row of
  `stage14_vendor_links_20261122_r2` and of its replay.
- No protocol section for the family (O18, its section in `specs/evaluation-protocol.md`).
  Scoring, null models, splits and the treatment of absent (zero) cells belong to it.
- No minimum for the marginal, support or pair tables. They are support, not targets.
- No gate for the 7 cells that exist only under the intra-group sensitivity.
- No minimum for any other family. The TRI parent links have their own outcome (O13).
- No embedder result. No embedder output, score or ranking was read (R8.4, which keeps
  benchmark tables out of embedder training).
- Recurrence is not accuracy, truth or a coefficient-of-variation rule. Section 9 states what
  the curves measure.
