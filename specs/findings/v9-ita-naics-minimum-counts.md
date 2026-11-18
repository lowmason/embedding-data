# V9 (ITA NAICS): headline minimum counts for three families

Measured on 2026-11-17 with `scripts/measure_ita_minimum_counts.py` (plan 12, Task 8)
at the rule commit in section 2. This record discharges spec R7.3 and V9 for three families
only: ITA co-ownership, the 2023 ITA area mix and ITA text–code pairs. The design is in
`specs/ita-naics-minimum-counts.md`. The record holds counts, rates, run IDs and pins only.

## 1. Decision

Every family gets a headline minimum of 1. The rule in section 2 gives each minimum from the
curves in section 5. A cell meets the gate when its published count is at least its
family's minimum. Consumers filter on the published column below.

| Family | Minimum | Published count the minimum applies to |
| --- | --- | --- |
| Co-ownership | 1 | `n_unweighted` (`J`, pooled 2023–2025) in `ita_co_ownership.parquet` |
| Area mix | 1 | `n_unweighted` (2023 records) in `ita_area_mix.parquet` |
| Text pairs | 1 | `n_headline_records` of pairs with `flag_headline` in `ita_text_pairs.parquet` |

Every band, including count 1, reaches `LEVEL` in every year pair. The run found no top band
below `LEVEL`, so the no-minimum stop did not apply. The spec names a minimum of 1 a valid
result. The band closest to `LEVEL` is co-ownership 2023 → 2024, count 1, at 94.84% against 90.00%.

## 2. Rule and constants

Recurrence rule (spec "The rule"): a cell is headline evidence when cells of its count recur in
the next year. The year pair's minimum is the lowest starting count of a band that reaches
`LEVEL`, where every higher band also reaches it. The family's minimum is the largest minimum
over its year pairs.

| Constant | Value | Meaning |
| --- | --- | --- |
| `LEVEL` | 0.90 | Lowest recurrence rate a band may have and still support the minimum |
| `TOP_BAND` | 10 | Counts of this size and more form one top band |
| `MIN_BAND_CELLS` | 50 | A band below the top band with fewer testable cells merges into the next higher band |
| 95% Wilson interval | z = 1.959963984540054 | Reported for each band. It does not enter the rule |

Rule commit: `d15384fd8913468e9767ab407b7b2d705cab61ba`. The script, its tests and these
constants were committed there before the first real run. Both real runs ran at this commit.

**OC3 disclosure.** No OC3 fix was made. The script is unchanged since the rule commit.
The rule commit `d15384f` ("fix(scripts): exit 2 with a fixed reason on an unexpected error")
carries the last script change. It landed before the first real run, so it is not an OC3 fix.

One band merged. In co-ownership 2024 → 2025, count 9 had fewer than `MIN_BAND_CELLS` testable
cells and merged upward, so that top band starts at 9 and is written `9+`. Every other top band
starts at 10.

## 3. Inputs

The script read three bundles in place and rebuilt none. It checked each detached
`outputs.json` SHA-256 first.

| Input | Run ID | Directory under `--data-dir` | Detached `outputs.json` SHA-256 |
| --- | --- | --- | --- |
| Establishment targets (Stage 10) | `stage10_ita_establishment_20261116_r1` | `derived/osha/establishment-targets/` | `e19b0d58f61f106c3994aa6fe51f4fb71244188145dd90f8cccaa8dc8a8b09df` |
| Area mix (Stage 6) | `stage6_ita_area_mix_20261014_1000_csv` | `derived/targets/` | `084292b6835eb09ce27ecc4a3aef03a6f43bfe7b39b815665c29190a431e2473` |
| Codes (Stage 4) | `stage4_v11_20261013_r2` | `derived/codes/` | `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |

The script also checked that the `inputs.json` of the establishment and area-mix bundles name
the codes run and its `ita_300a_canonical.parquet`. The SHA-256 of that table is
`2c64e783c8874cbe78809c0629a08faa7a0bf965d7680279350a64928a1f32ab`.

## 4. Run

Both runs used this command, from the worktree root, under `/usr/bin/time -l`.
Each run exited 0 and printed one sorted JSON line.

```bash
uv run --offline --locked python scripts/measure_ita_minimum_counts.py \
  --data-dir /Users/lowell/Projects/embedding-data/data \
  --establishment-run stage10_ita_establishment_20261116_r1 \
  --establishment-outputs-sha256 e19b0d58f61f106c3994aa6fe51f4fb71244188145dd90f8cccaa8dc8a8b09df \
  --area-mix-run stage6_ita_area_mix_20261014_1000_csv \
  --area-mix-outputs-sha256 084292b6835eb09ce27ecc4a3aef03a6f43bfe7b39b815665c29190a431e2473 \
  --codes-run stage4_v11_20261013_r2 \
  --codes-outputs-sha256 15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a
```

| Run | Output SHA-256 |
| --- | --- |
| 1 | `46afb6f08a2cd82b3eb50152f6ab8ab05c9ffe078a3ba0681258003557d1bd0f` |
| 2 | `46afb6f08a2cd82b3eb50152f6ab8ab05c9ffe078a3ba0681258003557d1bd0f` |

The two outputs are byte-identical (`cmp` reported `identical`). `find` under the data tree
found no file newer than the start marker, so the runs wrote nothing under `data/`.

Run 1 took 2.03 s wall time (3.00 s user, 1.10 s system). Its maximum resident set size was
1,286,881,280 bytes (1.29 GB). Both figures come from `/usr/bin/time -l`, which wrapped `uv run`.

## 5. Curves

Each table is one family and year pair. A band groups testable cells by their base-year count.
Terms:

- **Base cells:** cells with a base-year count of at least 1.
- **Testable:** cells with a visible link from a base-year record to an eligible successor
  record in the next year (spec "Testable cells").
- **Recurring:** testable cells that recur in the next year.
- **Rate:** recurring divided by testable.
- **95% Wilson interval:** the interval around the rate. It is for readers only.

Rates and bounds are shown to two decimals. The JSON output holds full precision.

### Co-ownership, 2023 → 2024 (`2023-2024`)

| Band | Base cells | Testable | Recurring | Rate | 95% Wilson interval |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 20,650 | 1,900 | 1,802 | 94.84% | 93.75%–95.75% |
| 2 | 4,430 | 942 | 918 | 97.45% | 96.24%–98.28% |
| 3 | 1,738 | 544 | 542 | 99.63% | 98.67%–99.90% |
| 4 | 966 | 422 | 418 | 99.05% | 97.59%–99.63% |
| 5 | 602 | 296 | 296 | 100.00% | 98.72%–100.00% |
| 6 | 360 | 230 | 230 | 100.00% | 98.36%–100.00% |
| 7 | 252 | 174 | 174 | 100.00% | 97.84%–100.00% |
| 8 | 204 | 150 | 150 | 100.00% | 97.50%–100.00% |
| 9 | 142 | 122 | 122 | 100.00% | 96.95%–100.00% |
| 10+ | 746 | 672 | 672 | 100.00% | 99.43%–100.00% |
| All | 30,090 | 5,452 | 5,324 | | |

Minimum for this year pair: **1**.

### Co-ownership, 2024 → 2025 (`2024-2025`)

| Band | Base cells | Testable | Recurring | Rate | 95% Wilson interval |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 12,802 | 7,052 | 6,798 | 96.40% | 95.94%–96.81% |
| 2 | 2,318 | 1,870 | 1,860 | 99.47% | 99.02%–99.71% |
| 3 | 882 | 794 | 786 | 98.99% | 98.02%–99.49% |
| 4 | 432 | 416 | 416 | 100.00% | 99.09%–100.00% |
| 5 | 278 | 274 | 274 | 100.00% | 98.62%–100.00% |
| 6 | 168 | 164 | 164 | 100.00% | 97.71%–100.00% |
| 7 | 90 | 90 | 90 | 100.00% | 95.91%–100.00% |
| 8 | 72 | 72 | 72 | 100.00% | 94.93%–100.00% |
| 9+ | 300 | 298 | 298 | 100.00% | 98.73%–100.00% |
| All | 17,342 | 11,030 | 10,758 | | |

Minimum for this year pair: **1**.

### Area mix, 2023 → 2024 (`2023-2024`)

| Band | Base cells | Testable | Recurring | Rate | 95% Wilson interval |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 79,249 | 11,400 | 11,118 | 97.53% | 97.22%–97.80% |
| 2 | 21,107 | 5,250 | 5,167 | 98.42% | 98.04%–98.72% |
| 3 | 8,936 | 3,048 | 3,016 | 98.95% | 98.52%–99.26% |
| 4 | 4,771 | 1,941 | 1,926 | 99.23% | 98.73%–99.53% |
| 5 | 2,983 | 1,363 | 1,356 | 99.49% | 98.94%–99.75% |
| 6 | 1,952 | 998 | 996 | 99.80% | 99.27%–99.95% |
| 7 | 1,419 | 778 | 776 | 99.74% | 99.07%–99.93% |
| 8 | 1,042 | 638 | 637 | 99.84% | 99.12%–99.97% |
| 9 | 732 | 462 | 461 | 99.78% | 98.78%–99.96% |
| 10+ | 4,767 | 3,468 | 3,462 | 99.83% | 99.62%–99.92% |
| All | 126,958 | 29,346 | 28,915 | | |

Minimum for this year pair: **1**.

### Area mix, 2024 → 2025 (`2024-2025`)

| Band | Base cells | Testable | Recurring | Rate | 95% Wilson interval |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 54,303 | 23,675 | 23,277 | 98.32% | 98.15%–98.48% |
| 2 | 13,956 | 8,410 | 8,349 | 99.27% | 99.07%–99.43% |
| 3 | 5,500 | 3,827 | 3,812 | 99.61% | 99.35%–99.76% |
| 4 | 2,977 | 2,225 | 2,217 | 99.64% | 99.29%–99.82% |
| 5 | 1,849 | 1,431 | 1,427 | 99.72% | 99.28%–99.89% |
| 6 | 1,197 | 949 | 949 | 100.00% | 99.60%–100.00% |
| 7 | 847 | 675 | 674 | 99.85% | 99.17%–99.97% |
| 8 | 652 | 526 | 526 | 100.00% | 99.27%–100.00% |
| 9 | 463 | 382 | 381 | 99.74% | 98.53%–99.95% |
| 10+ | 2,839 | 2,335 | 2,333 | 99.91% | 99.69%–99.98% |
| All | 84,583 | 44,435 | 43,945 | | |

Minimum for this year pair: **1**.

### Text pairs, 2023 → 2024 (`2023-2024`)

| Band | Base cells | Testable | Recurring | Rate | 95% Wilson interval |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 134,027 | 17,038 | 16,994 | 99.74% | 99.65%–99.81% |
| 2 | 9,248 | 1,551 | 1,548 | 99.81% | 99.43%–99.93% |
| 3 | 3,580 | 695 | 694 | 99.86% | 99.19%–99.97% |
| 4 | 1,980 | 446 | 445 | 99.78% | 98.74%–99.96% |
| 5 | 1,244 | 273 | 273 | 100.00% | 98.61%–100.00% |
| 6 | 868 | 233 | 233 | 100.00% | 98.38%–100.00% |
| 7 | 671 | 161 | 161 | 100.00% | 97.67%–100.00% |
| 8 | 524 | 145 | 144 | 99.31% | 96.20%–99.88% |
| 9 | 399 | 107 | 107 | 100.00% | 96.53%–100.00% |
| 10+ | 2,960 | 1,018 | 1,017 | 99.90% | 99.45%–99.98% |
| All | 155,501 | 21,667 | 21,616 | | |

Minimum for this year pair: **1**.

### Text pairs, 2024 → 2025 (`2024-2025`)

| Band | Base cells | Testable | Recurring | Rate | 95% Wilson interval |
| --- | ---: | ---: | ---: | ---: | --- |
| 1 | 65,847 | 27,690 | 27,674 | 99.94% | 99.91%–99.96% |
| 2 | 4,531 | 2,156 | 2,155 | 99.95% | 99.74%–99.99% |
| 3 | 1,822 | 931 | 930 | 99.89% | 99.39%–99.98% |
| 4 | 1,019 | 496 | 496 | 100.00% | 99.23%–100.00% |
| 5 | 677 | 371 | 369 | 99.46% | 98.06%–99.85% |
| 6 | 436 | 236 | 236 | 100.00% | 98.40%–100.00% |
| 7 | 376 | 208 | 207 | 99.52% | 97.33%–99.92% |
| 8 | 277 | 157 | 157 | 100.00% | 97.61%–100.00% |
| 9 | 199 | 100 | 100 | 100.00% | 96.30%–100.00% |
| 10+ | 1,766 | 931 | 930 | 99.89% | 99.39%–99.98% |
| All | 76,950 | 33,276 | 33,254 | | |

Minimum for this year pair: **1**.

Each family's minimum is the largest of its two year-pair minimums, so each is 1.

## 6. Kept counts

"Kept" means the cell's published count is at least the family's minimum. "Support" is the
sum of the published count the gate applies to. A kept cell is "lenient" when its largest
single-year count is below the minimum. Co-ownership and text-pair counts pool three years,
so the gate can be a little lenient for those two families (spec "Where the minimum applies").

| Family | Cells | Support | Kept cells | Kept cell share | Kept support | Kept support share | `lenient_kept_cells` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Co-ownership | 39,152 | 91,866 | 39,152 | 100.00% | 91,866 | 100.00% | 0 |
| Area mix | 126,958 | 324,191 | 126,958 | 100.00% | 324,191 | 100.00% | 0 |
| Text pairs | 239,364 | 751,891 | 239,364 | 100.00% | 751,891 | 100.00% | 0 |

Cells are directed co-ownership industry pairs, 2023 county × industry area-mix cells and
headline text pairs. A minimum of 1 keeps every published cell. No kept cell is lenient.

## 7. Deviation: the text-pair gate counts `n_headline_records`

The roadmap's Stage 3 Exit names `n_records`. The text-pair gate counts `n_headline_records`
instead, as the owner decided on 2026-11-17. Section 1 and section 6 use that column. The plan
records the change as a `> Deviation:` note against the Stage 3 Exit. The spec states the reason
("The text-pair count"):

> **The text-pair count** (owner picked `n_headline_records`, 2026-11-17): the roadmap's
> Stage 3 Exit names `n_records`. `n_records` pools all ten years, including 2016–2022
> records whose codes were crosswalked and carry no headline label. 47% of headline pairs
> have such records, and the median `n_records` is 3 against a median
> `n_headline_records` of 1. The recurrence test measures headline records, so the gate
> counts the same thing. This is a recorded deviation from the Exit wording.

## 8. Disclosure: curves seen at design time

The owner saw plain co-ownership curves before fixing `LEVEL`. The spec records this under
Anti-goals. The design-time curves had no testability filter. The curves in section 5 count
testable cells only, so the two sets differ. The spec text follows.

> *Disclosure (owner, 2026-11-17):* during design, the owner saw plain recurrence curves
> for co-ownership before fixing `LEVEL`. They came from the published per-year counts in
> `co_ownership_support.parquet`, with no testability filter. For 2023 → 2024, recurrence
> at counts 1, 2, 3, 4, 5, 6 and 10+ was 29%, 53%, 68%, 80%, 84%, 93% and 99%. For
> 2024 → 2025, it was 68%, 93%, 98%, 100%, 99%, 100% and 100%. The designer also saw
> counts 7–9, the cell count of each band and the number of years each pooled cell
> appears in before proposing `TOP_BAND` and `MIN_BAND_CELLS`. No testable curve, no
> area-mix or text-pair curve and no minimum had been measured.

## 9. Limits

These are the eight Limits of the spec, copied as written. The text-pair Limit (third) is the
one that amendment D1 added.

- Recurrence measures code persistence among establishments that refiled visibly. It
  measures neither truth nor establishment exits. An establishment that files the same
  wrong code every year recurs.
- Testability keeps only cells with a visible link. Establishments that relocate or file
  in older NAICS editions are under-represented in the curves.
- A text pair is testable only when a linked successor kept its description. Pairs whose
  establishments reword their descriptions are under-represented in the text-pair curves.
  *(owner, plan 12, 2026-11-17)*
- Co-ownership and text-pair gates apply to three-year pooled counts, which makes them a
  little lenient (measured, above).
- ITA is a program-selected filing population. Filing-rule changes between years can move
  recurrence.
- The 2025 release runs through 08-31-2026. The 2023 and 2024 releases run through 12-31
  of the following year. The shorter window can leave out late 2025 filers.
- Confirmed links need a usable, unreconstructed EIN and a complete address. Records
  without them never have a visible link. So area-mix records with an unusable EIN and
  every text pair with a company-name fallback employer are never testable.
- The minimum is a reliability floor for headline use. It is not a coefficient-of-variation
  rule, and it says nothing about cells that the bundles do not emit.

## 10. Not claimed

- No bundle is relabeled or rebuilt. `size_gate_pending` stays in the published Stage 10
  establishment bundle and the published Stage 6 bundle.
- No minimum is set for other families: SOC, geography, ACS, CPS and Track B families
  keep their own stages. Cross-year links get no minimum.
- No scoring, null model, split or treatment of absent (zero) cells. No embedder output, score
  or ranking was read (R8.4).
- Recurrence is not accuracy, truth or a coefficient-of-variation rule. Section 9 states
  what the curves measure.
