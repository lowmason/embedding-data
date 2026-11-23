# V9 (ACS wage microdata): minimum headline earners for each category

Measured on 2026-11-22 with `scripts/measure_acs_wage_minimum_earners.py` (plan 17, Stage 19)
at the rule commit in section 2. This record discharges spec R7.3 and V9 for the ACS wage
microdata only. The design is in `specs/completed/acs-wage-minimum-earners.md`. The record holds counts,
run IDs and pins only. It holds no SE of a single category and no mean wage.

Terms used in this record:

- **Headline earner:** one row of the Stage 17 wage file with `flag_headline` true. The record
  counts headline earners as `headline_rows`.
- **Category:** one delivered `INDNAICS` string.
- **SE:** the standard error of a category's weighted mean `log_wage_2010` in one year.
- **Band:** a range of category sizes, counted in `headline_rows`. A band runs from its start up
  to, but not including, the next start.

## 1. Decision

The minimum is 400 headline earners, in both 2023 and 2024. A category meets the gate in a
year when its published count of headline rows in that year is at least 400. Consumers filter
on the published column below.

| File | Minimum | Published count the minimum applies to |
| --- | ---: | --- |
| `report.json` of the Stage 17 run `stage17_acs_wage_microdata_20261119_r1` | 400 | `headline_rows` of each entry in `categories`, keyed by `INDNAICS` and `YEAR` |

In both years, the band from 200 to 400 fails and every band from 400 up passes. The year's
minimum is therefore 400 in each year, and the larger of the two is 400. The share of the
200–400 band that meets `SE_TARGET` is 60.00% in 2023 and 77.78% in 2024. The level it must
reach is 90.00%. The top band passes in both years, so the no-minimum stop did not apply.

The minimum can take only a band start as its value. The 200–400 band holds categories that
meet `SE_TARGET` and categories that miss it. The rule does not split that band.

## 2. Rule and constants

The rule is in the spec ("The rule"). For a category and a year, take the headline rows with
that `INDNAICS` and `YEAR`. Let `x_i` be `log_wage_2010`.

- Full-sample estimate: `θ = Σ PERWT_i · x_i / Σ PERWT_i`.
- Replicate estimate, for `r` = 1 to 80: `θ_r = Σ REPWTPr_i · x_i / Σ REPWTPr_i`.
- `SE = sqrt( 4/80 · Σ_r (θ_r − θ)² )`, the ACS successive-difference formula.

Weights use their literal values (factor 1). A category meets the target in a year when
`SE ≤ SE_TARGET`.

The SE is undefined, and the category misses the target, in three cases. They are listed here
in the order that the script uses:

1. The category has fewer than 2 headline rows in the year (`fewer_than_two_rows`).
2. All its `log_wage_2010` values in the year are equal (`constant_wage`).
3. A replicate denominator is zero or negative (`replicate_denominator_not_positive`).

These guards remove only cases that are degenerate by arithmetic. They add no row floor.

The spec leaves four choices open. The plan fixed them as defaults (plan decision OC1):

- An SE that is undefined for two reasons counts once, under the first reason in the order
  above.
- A kept share divides by that year's headline categories or headline rows.
- A category with no headline rows is counted apart, as `shared_node_categories`.
- Sums use `math.fsum`. It is correctly rounded, so the output does not depend on row order.

Every undefined-SE count is 0 in both years (section 5). The first-reason default therefore
changed no count.

| Constant | Value | Meaning |
| --- | --- | --- |
| `SE_TARGET` | 0.05 | Largest SE, in log points, that counts as meeting the target |
| `LEVEL` | 0.90 | Share of a band's categories that must meet `SE_TARGET` for the band to pass |
| `BAND_STARTS` | 1, 50, 100, 200, 400, 800, 1600 | Start of each band. The last band is `1600+` |
| `MIN_BAND_CATEGORIES` | 10 | A band below the top band with fewer categories merges into the next higher band |
| `REPLICATE_FACTOR` | 4/80 | The ACS successive-difference factor (0.05 in the output) |

The script also fixes `REPLICATES` = 80 and `YEARS` = (2023, 2024).

The script bands each year on its own:

1. Each headline category goes into the band that holds its `headline_rows` for that year.
2. The script merges short bands from the lowest band upward (greedy). A band below the top
   band with fewer than `MIN_BAND_CATEGORIES` categories merges into the next higher band.
   The script then checks the merged band and merges it again if it is still short. A merged
   band keeps its lowest start. The top band stays however few categories it holds.
3. A band passes when at least `LEVEL` of its categories meet `SE_TARGET`.
4. The year's minimum is the lowest start of a passing band whose higher bands all pass.
5. The run's minimum is the larger of the two years' minimums.

The spec's wording of step 2 ("Repeat until every band has at least `MIN_BAND_CATEGORIES`
categories or is the top band") can read two ways. So this record states the algorithm that
the script runs.

The merge ran in both years. The bands at 1, 50 and 100 merged into one band that starts at 1
and runs to 200. It holds 15 categories in 2023 and 19 in 2024. No other band merged. Every
band in section 5 has at least 10 categories.

The merge does not change the minimum, for three reasons:

- The 200–400 band holds 35 categories in 2023 and 36 in 2024. It never merges upward.
- It fails in both years, so the run of passing bands that ends at the top band starts at 400.
- Under either reading of the merge, a lower band that joined the 200–400 band would add
  categories that mostly miss the target (0 of 15 meet it in 2023 and 1 of 19 in 2024). Such
  a band could only lower the share of the 200–400 band.

Rule commit: `f060526d3dc6c78b030391bfdc12dd3b72077afe`. The script, its tests and these
constants were committed there before the first real run. Both real runs ran at this commit,
with a clean working tree. No constant changed after the first real run.

**OC3 disclosure.** OC3 is the plan's rule for a script change after the first real run. Such a
change may only move the script toward the written rule. Both real runs must then repeat at the
new commit, and this record must disclose the change. No OC3 fix was made. The script is
unchanged since the rule commit. The rule commit `f060526` ("fix(scripts): print the fixed line
and exit 2 when Polars panics") carries the last script change. It landed before the first real
run, so it is not an OC3 fix.

## 3. Inputs

The script read the Stage 17 run in place and rebuilt nothing. It checked the detached
`outputs.json` SHA-256 first. Then it checked that `report.json` and the person table match
their records in `outputs.json`. It ran no `verify`. It read the first run only, because the
replay run is byte-identical in both files (Stage 17 finding).

| Input | Identity |
| --- | --- |
| Run ID | `stage17_acs_wage_microdata_20261119_r1` |
| `derived/acs/wage-microdata/stage17_acs_wage_microdata_20261119_r1/outputs.json` | detached SHA-256 `6cb253e2e5c2e48a5b31d2790a0378636d3b6ef9197cfb2d33cca2813ac201d1` |
| its `report.json` | inventory SHA-256 `32ad9b698c9b940760d74eec0ae3b234abd14ba4c08ca07f04770a8f11e413bd` |
| its `acs_wage_persons.parquet` | inventory SHA-256 `a94471492dc91aebe3a3436e8d738d399520791b0eace6f01a719fad10fd5ff2` |

The script read 85 columns of the person table: `YEAR`, `INDNAICS`, `flag_headline`,
`log_wage_2010`, `PERWT` and `REPWTP1` to `REPWTP80`. The spec says 84 columns. That is a
slip, because the five named columns and 80 replicate weights make 85.

The script stopped on any difference between the person table and `report.json`. For each
year, it recounted the headline rows of each category and the number of categories. The run
exited 0 with `complete` true, so every check passed. Each year has 233 categories with
headline rows.

## 4. Run

Both runs used this command. Each run exited 0 and printed one sorted JSON line of 70,020
bytes.

```bash
uv run --offline --locked python scripts/measure_acs_wage_minimum_earners.py \
  --data-dir /Users/lowell/Projects/embedding-data/data \
  --run stage17_acs_wage_microdata_20261119_r1 \
  --outputs-sha256 6cb253e2e5c2e48a5b31d2790a0378636d3b6ef9197cfb2d33cca2813ac201d1
```

| Run | Output SHA-256 |
| --- | --- |
| 1 | `19396d79915f4add0baebf5865b5a83a912ba0f1cb2126a2976aef448ea4657b` |
| 2 | `19396d79915f4add0baebf5865b5a83a912ba0f1cb2126a2976aef448ea4657b` |

The two outputs are byte-identical (`cmp` reported them identical). `find` under the data tree
found no file newer than the start marker, so the runs wrote nothing under `data/`.

Run 1 took 3.27 s wall time. Its maximum resident set size was 3,056,549,888 bytes (3.06 GB).
Run 2 took 3.25 s and had a maximum resident set size of 3,016,982,528 bytes.

The output holds the SE of every category. It stays on this machine and never enters git.
This record cites only its SHA-256.

## 5. Bands

Each table is one year. A band holds categories by their `headline_rows` for that year.
"Meeting" is the number of categories in the band that meet `SE_TARGET`. "Share" is meeting
divided by categories. A band passes when its share is at least 90.00%. Shares are shown to two
decimals. The JSON output holds full precision. The 1–200 band is the merge of the bands at 1,
50 and 100 (section 2).

### 2023

| Band | Categories | Meeting | Share | Passes |
| --- | ---: | ---: | ---: | --- |
| 1–200 | 15 | 0 | 0.00% | no |
| 200–400 | 35 | 21 | 60.00% | no |
| 400–800 | 50 | 48 | 96.00% | yes |
| 800–1600 | 46 | 46 | 100.00% | yes |
| 1600+ | 87 | 87 | 100.00% | yes |
| All | 233 | 202 | | |

Minimum for 2023: **400**.

| Undefined SE, by reason | Categories |
| --- | ---: |
| `fewer_than_two_rows` | 0 |
| `constant_wage` | 0 |
| `replicate_denominator_not_positive` | 0 |

### 2024

| Band | Categories | Meeting | Share | Passes |
| --- | ---: | ---: | ---: | --- |
| 1–200 | 19 | 1 | 5.26% | no |
| 200–400 | 36 | 28 | 77.78% | no |
| 400–800 | 46 | 46 | 100.00% | yes |
| 800–1600 | 45 | 45 | 100.00% | yes |
| 1600+ | 87 | 87 | 100.00% | yes |
| All | 233 | 207 | | |

Minimum for 2024: **400**.

| Undefined SE, by reason | Categories |
| --- | ---: |
| `fewer_than_two_rows` | 0 |
| `constant_wage` | 0 |
| `replicate_denominator_not_positive` | 0 |

The run's minimum is the larger of the two years' minimums: **400**.

## 6. Kept counts

"Kept" means the category's `headline_rows` is at least the minimum of 400. The kept category
share divides by the year's 233 headline categories. The kept headline row share divides by the
year's headline rows.

| Value | 2023 | 2024 |
| --- | ---: | ---: |
| Headline categories | 233 | 233 |
| Headline rows | 639,002 | 639,876 |
| Kept categories | 183 | 178 |
| Kept category share | 78.54% | 76.39% |
| Kept headline rows | 626,564 | 625,828 |
| Kept headline row share | 98.05% | 97.80% |

The count gate and a category's own SE can disagree. The two tallies are:

| Disagreement | 2023 | 2024 |
| --- | ---: | ---: |
| Meets the count, misses `SE_TARGET` (`count_meets_se_misses`) | 2 | 0 |
| Misses the count, meets `SE_TARGET` (`count_misses_se_meets`) | 21 | 29 |

A category in the first row passes the gate, but its own SE is above 0.05. A category in the
second row fails the gate, but its own SE is at or below 0.05.

## 7. Categories below the minimum

Each table lists the categories of one year whose `headline_rows` is below 400. There are 50 in
2023 (233 minus 183 kept) and 55 in 2024 (233 minus 178 kept). The delivered `INDNAICS` strings
carry space padding. The tables leave it out. A consumer matches on the delivered strings, with
their padding.

The 31 `shared_node_categories` are different. They share a node, so they have no headline rows.
They are not among the 233 headline categories and not in the tables. They never meet the gate.
The count is 31 in both years, as the spec says.

The tables hold no SE of a single category.

### 2023

| `INDNAICS` | `headline_rows` |
| --- | ---: |
| `1133` | 274 |
| `113M` | 342 |
| `114` | 92 |
| `2121` | 310 |
| `2122` | 335 |
| `3122` | 100 |
| `3131` | 53 |
| `3133` | 43 |
| `31411` | 236 |
| `314Z` | 305 |
| `3162` | 135 |
| `316M` | 113 |
| `3212` | 232 |
| `32199M` | 207 |
| `3241M` | 158 |
| `3253` | 280 |
| `32711` | 129 |
| `32712` | 167 |
| `3314` | 320 |
| `3321` | 304 |
| `3322` | 270 |
| `33299M` | 340 |
| `3365` | 215 |
| `3369` | 227 |
| `4232` | 336 |
| `4235` | 233 |
| `42393` | 299 |
| `4241` | 203 |
| `42491` | 318 |
| `4251` | 292 |
| `42S` | 333 |
| `45913` | 117 |
| `45914` | 180 |
| `45921` | 276 |
| `4593` | 200 |
| `45942` | 343 |
| `483` | 388 |
| `486` | 333 |
| `487` | 126 |
| `5122` | 183 |
| `532M2` | 319 |
| `62131` | 304 |
| `6243` | 390 |
| `7115` | 351 |
| `71395` | 84 |
| `721M` | 338 |
| `7224` | 390 |
| `811192` | 399 |
| `8114` | 379 |
| `812111` | 137 |

### 2024

| `INDNAICS` | `headline_rows` |
| --- | ---: |
| `1133` | 300 |
| `113M` | 328 |
| `114` | 90 |
| `2121` | 368 |
| `2122` | 334 |
| `311811` | 347 |
| `3122` | 85 |
| `3131` | 46 |
| `3133` | 46 |
| `31411` | 186 |
| `314Z` | 297 |
| `3162` | 124 |
| `316M` | 84 |
| `3212` | 202 |
| `32199M` | 138 |
| `3241M` | 190 |
| `3253` | 288 |
| `32711` | 145 |
| `32712` | 172 |
| `3314` | 333 |
| `3321` | 259 |
| `3322` | 362 |
| `3328` | 354 |
| `33299M` | 249 |
| `3365` | 244 |
| `3369` | 238 |
| `4232` | 337 |
| `4235` | 279 |
| `42393` | 291 |
| `4239Z` | 392 |
| `4241` | 195 |
| `4245` | 365 |
| `42491` | 260 |
| `4251` | 299 |
| `4582` | 397 |
| `45913` | 96 |
| `45914` | 144 |
| `45921` | 288 |
| `4593` | 198 |
| `45941` | 388 |
| `45942` | 375 |
| `486` | 348 |
| `487` | 150 |
| `5122` | 175 |
| `532M2` | 306 |
| `62131` | 288 |
| `6243` | 340 |
| `7115` | 289 |
| `71395` | 90 |
| `721M` | 368 |
| `7224` | 381 |
| `811192` | 377 |
| `8112` | 317 |
| `8114` | 369 |
| `812111` | 137 |

## 8. Deviation: the measurement reads the person table

The roadmap's Stage 19 Consumes line (roadmap `:248`) names only `report.json` and the Stage 17
finding. The O23 cost cell (roadmap `:71`) says "one pass over Stage 17's counts". Under D1 the
measurement also reads `acs_wage_persons.parquet`, which costs more. D1 is the owner's decision
that the measurement may read wage values (owner, D1, 2026-11-22, spec "Approaches considered"
and "Rollout"). The cost is the read in section 4: 3.27 s wall time and a maximum resident set size
of 3,056,549,888 bytes in run 1. The Exit still holds as written, because the minimum and its
bands are counted in `headline_rows`.

## 9. Disclosure: figures seen at design time

Before the owner fixed the SE target, the design session had seen some figures about category
size and wages. The spec records this under Anti-goals ("A rule picked after seeing its
result"). The text follows.

> *Disclosure (2026-11-22):* before the owner fixed the SE target, the session had seen these
> figures and no others about category size or wages:
> - The Stage 17 design's pooled pre-build figures (`specs/completed/acs-wage-microdata.md`,
>   "The headline funnel"). The smallest category has 89 headline earners over both years, and
>   the median category has 2,045.
> - The built totals in the Stage 17 finding: 1,278,878 headline rows (2023: 639,002;
>   2024: 639,876) over 233 categories in each year.
> - A table from the designer that gave the earners each target would need: about 700 for
>   0.03, 250 for 0.05 and 60 for 0.10. It was argument, not measurement. It assumed a
>   within-category spread of 0.6 log points and a design effect of 1.7, and it used no data
>   from the run.
>
> No per-category count, no SE and no wage value had been read.

Planning read no further data of the run. The rule and every constant were committed at
`f060526` before the first real run. No constant changed after that run.

## 10. Limits

These are the seven Limits of the spec, copied as written. Section 1 shows how the fifth Limit
applies: the minimum of 400 is a band start.

- The SE measures sampling noise in a category's weighted mean log wage. It does not measure
  coding error, allocation or how well a panel's model fits.
- The SE is for the mean without covariates. A panel that conditions on covariates estimates a
  different quantity, with a different SE.
- Replicate SEs are themselves noisy in small categories. A category with only a few rows can
  meet the target by chance. The guards catch only the cases that are degenerate by arithmetic.
- Top-coded wages stay in the headline (Stage 17 design). They narrow the spread at the top, so
  SEs in high-wage categories can be a little low.
- The minimum can take only a band start as its value.
- The 31 categories that share a node have no headline rows and are not measured.
- The minimum is a reliability floor for headline use. It says nothing about the approximate
  coordinates of mixture categories.

## 11. Not claimed

- No Stage 17 bundle is relabeled, rebuilt or edited. The `report.json` of the run is unchanged.
- No protocol section exists for the file (O24). What a panel does with a category below the
  minimum belongs to O24.
- No minimum is set for any target family, including the ACS worker-profile family. The wage
  file is not a target family.
- No panel result is claimed. No embedder output, score or ranking was read (R8.4).
- No mean wage of a category is published here or in the output (R8.4).
- The SE is not accuracy, truth or a measure of a panel's fit. Section 10 states what it
  measures.
