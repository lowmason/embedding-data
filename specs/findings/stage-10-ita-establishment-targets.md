# Stage 10 ITA establishment targets: measured full-data build and replay

The full-data build of the Stage 10 bundle exists, and a second build of it matches. Run
`stage10_ita_establishment_20261116_r1` (the first run) and run
`stage10_ita_establishment_20261116_r1_replay` (the replay) both pass `verify`.
`compare-runs` finds the two bundles equal. Plan 11
(`specs/plans/11-ita-establishment-targets.md`) ran Task 11 in two roadmap stages. Stage 1
built and checked the first run on 2026-11-16, and its record is
`specs/naics-evaluation-data-stage-1-findings.md`. Stage 4 built the replay on 2026-11-18
and wrote this file.

Fixture tests show software readiness only. This file records the measured production
runs. It claims no more than the limits and the "Not claimed" section state.

## Selected runs and pins

Both runs live in `data/derived/osha/establishment-targets/`. The detached pin is the
SHA-256 of `outputs.json`. `verify` needs it as `--outputs-sha256`.

| Run | File | SHA-256 |
| --- | --- | --- |
| First: `stage10_ita_establishment_20261116_r1` | `outputs.json` (detached pin) | `e19b0d58f61f106c3994aa6fe51f4fb71244188145dd90f8cccaa8dc8a8b09df` |
| | `inputs.json` | `2225092a06f656a97933eb182e0b277c06f01b259e4dfd79626bc37368456b2d` |
| | `report.json` | `7f1edba024bc7a290bb2682b95126450b921e6e3cba602aa9b887d3d2c587629` |
| Replay: `stage10_ita_establishment_20261116_r1_replay` | `outputs.json` (detached pin) | `e38e820b6e999f751687918d8f578b0f9d69ce145bbcb672b966a19a78d536a4` |
| | `inputs.json` | `bb86ecbc8003775731b4deac79a8190780fe460daf486122ccdec225f8bf0883` |
| | `report.json` | `7f1edba024bc7a290bb2682b95126450b921e6e3cba602aa9b887d3d2c587629` |

The two `report.json` files have the same bytes. The two pins differ, because `inputs.json`
records the run ID and the creation time. Each bundle has 11 files: eight Parquet tables,
`inputs.json`, `report.json` and `outputs.json`. The first bundle is 160,736,016 bytes. The
replay bundle is 160,752,463 bytes.

The replay command was:

```bash
uv run --locked python -m embedding_data.ita_establishment_targets build stage10_ita_establishment_20261116_r1_replay --data-dir /Users/lowell/Projects/embedding-data/data --codes-run stage4_v11_20261013_r2 --codes-outputs-sha256 15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a
```

The verifiers are:

```bash
uv run --locked python -m embedding_data.ita_establishment_targets verify stage10_ita_establishment_20261116_r1 --data-dir /Users/lowell/Projects/embedding-data/data --outputs-sha256 e19b0d58f61f106c3994aa6fe51f4fb71244188145dd90f8cccaa8dc8a8b09df
uv run --locked python -m embedding_data.ita_establishment_targets verify stage10_ita_establishment_20261116_r1_replay --data-dir /Users/lowell/Projects/embedding-data/data --outputs-sha256 e38e820b6e999f751687918d8f578b0f9d69ce145bbcb672b966a19a78d536a4
uv run --locked python -m embedding_data.ita_establishment_targets compare-runs stage10_ita_establishment_20261116_r1 stage10_ita_establishment_20261116_r1_replay --data-dir /Users/lowell/Projects/embedding-data/data
```

## Execution identity

| Run | Executing commit | `dirty` | Created (UTC) |
| --- | --- | --- | --- |
| First | `1f3abf0761a6325dbbba5860764200793574ddd8` | false | 2026-11-16 17:16:43 |
| Replay | `be4e8dad1758e6eca2aca33f22604f38e4a5dd15` | false | 2026-11-18 16:10:06 |

Both runs record CPython 3.14.0 (`3.14.0 (main, Oct 14 2025, 21:10:22) [Clang 20.1.4 ]`),
63 installed distributions, 35 software files and the `uv.lock` SHA-256
`f57c3280a7c8286711bf6804ca4c02f0a19619c9db52f33941b9c5b996cba8e5`. Stage 4 changes no file
in that software list.

Stage 4 built the replay from a new worktree venv (`uv sync --locked`, run once). Before
any run, the first run's recorded `software` equalled the live `freeze_software()`. That
equality covers Python, all 63 distributions, all 35 file hashes and the lock hash. The
first run then passed `verify` again from the Stage 4 checkout (Step 4b). So the first
run verifies under the replay's identity, which `compare-runs` alone cannot show.

The first run's commit is an ancestor of `main` through the merge of Stage 1 (merge commit
`22c38c5`). The replay's commit is on branch `stage-4-ita-naics-hardening`, the branch of
the Stage 4 pull request.

## Index originals

The three official Census NAICS index files came from Gate 1 on 2026-11-16. The registry
in `ita_index_references` pins each size and SHA-256. The manifest holds one line per file.
Each file ends with 25 `******` cross-reference rows (D2), kept with the delivered code.

| Vintage | Path under `data/raw/` | Size (bytes) | SHA-256 | Retrieved (UTC) | Rows |
| --- | --- | ---: | --- | --- | ---: |
| 2012 | `references/naics/2012_NAICS_Index_File.xls` | 2,177,024 | `c688f221987497db897bbc0e641156997d4e2f528e4fd390a3ad983b13462a23` | 2026-11-16 14:57:37 | 19,280 |
| 2017 | `references/naics/2017_NAICS_Index_File.xlsx` | 509,235 | `fb3b428300f698aa3d623e1a0edc50aaa3b729e930b7cdc22851825f487fb1ac` | 2026-11-16 14:57:37 | 20,082 |
| 2022 | `references/naics/2022_NAICS_Index_File.xlsx` | 499,358 | `6506b37b9546dd9cec1f8b79e0b38b68e547a5cce5fd6f8332d35024dbd6cd63` | 2026-11-16 14:57:38 | 20,398 |

The source URLs are `https://www.census.gov/naics/<year>NAICS/<year>_NAICS_Index_File.<ext>`.
The row counts include the 25 cross-reference rows.

## Measured cost

The host has 36 GiB of memory. `/usr/bin/time -l` measured each command.

| Stage | Command | Wall time | Maximum RSS |
| --- | --- | ---: | ---: |
| 1 | `build` (first run) | 53.86 s | 6,253,805,568 B |
| 1 | `verify` (first run) | 30.43 s | 6,398,885,888 B |
| 1 | `reconcile_stage10.py co-ownership` | 1.88 s | 471,384,064 B |
| 1 | `reconcile_stage10.py stage3` | 21.33 s | 2,920,824,832 B |
| 4 | `verify` (first run, Step 4b) | 35.26 s | 6,065,078,272 B |
| 4 | `build` (replay, Step 5) | 65.83 s | 5,197,430,784 B |
| 4 | `verify` (replay, Step 6) | 36.00 s | 5,987,008,512 B |
| 4 | `compare-runs` | 3.86 s | 2,615,279,616 B |
| 4 | preservation script (Step 6a) | 1.62 s | 123,551,744 B |
| 4 | `embedding-data audit` (Step 6a) | 12.02 s | 175,800,320 B |

## Results

**Reproduction.** For the first run (twice) and the replay, `verify` reports the basis
`adopted_v1_v3_finding`. The source-record count, V1 and V2 all report `equal`. V1 is the
per-year table of ITA description content and V2 is the per-year-pair table of
establishment-ID persistence, both in `specs/findings/v1-v3-ita-verification.md`. The
source has 3,206,055 records.

**Row counts.** Both runs have the same counts:

| Table | Rows |
| --- | ---: |
| `ita_text_pairs` | 644,265 |
| `ita_text_pair_codes` | 771,971 |
| `ita_text_pair_members` | 3,206,055 |
| `naics_2022_paths` | 1,007 |
| `ita_establishment_links` | 3,198,774 |
| `ita_co_ownership` | 39,152 |
| `co_ownership_marginals` | 991 |
| `co_ownership_support` | 39,152 |

**Replay comparison.** `compare-runs` exits 0 and reports `"equal": true`,
`"report_equal": true` and `"trust_established": false`. Each of the eight tables has
equal schema, equal row count and equal values. The comparison joins the two frames by row
position and counts a null against a value as a difference, so row order counts. Equality
does not authenticate either run. The two `verify` runs do.

Byte-level, six Parquet files and `report.json` are identical between the runs.
`ita_text_pairs.parquet` (39,674,722 and 39,692,464 bytes) and
`ita_text_pair_members.parquet` (56,289,497 and 56,288,195 bytes) differ in bytes but not
in values. `inputs.json` and `outputs.json` differ, as the run ID and creation time
require. This record does not diagnose why the two Parquet files differ in bytes.

**Independent checks (Stage 1, first run).** `reconcile_stage10.py co-ownership` reports
equal: N 155,436 EINs, 39,152 cells and 991 industries on both sides. `reconcile_stage10.py
stage3` reports V1 and V2 equal, with no differences. Pair records sum to 3,206,055 in
total and to each year's V1 `n_rows`. Every co-ownership row has `size_gate_pending`. Stage
4 did not rerun the reconcilers on the replay. The replay's tables equal the first run's
by `compare-runs`.

**Preservation.** Stage 1 (Step 8) and Stage 4 (Step 6a, after the replay) both found
these unchanged:
- The Stage 2 summary, SHA-256 `6335cda7adb40a41c4a11d57d22048999449ac8d078a2ec0291f0198cd9136a8`
  (139,930,636 bytes).
- The codes `outputs.json`, `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`.
- The two Stage 6 `outputs.json` files, `084292b6835eb09ce27ecc4a3aef03a6f43bfe7b39b815665c29190a431e2473`
  and `78fd21e37ba0c5b1cd396ff0961b557650788fdccd3c84a911e8c6c3b7fabe71`. The codes
  inventory and both Stage 6 inventories pass `target_io.verify_inventory`.
- The manifest, SHA-256 `0c610ce188e6ecc0a987db1726b34280c65bd7d42d3fbcd9448afeebdcddbb71`,
  3,010 lines. `build`, `verify` and `compare-runs` append nothing to it.
- The first run's `outputs.json`.

After the replay, `establishment-targets/` holds exactly the two runs and no `.part`
directory. The whole-tree audit exits 0 with 0 raw provenance discrepancies. The Stage 1
scratch script `stage1_checks.py`, run again on the replay, reports `"all_ok": true`. Its
Step 7 values equal the Stage 1 values.

## Distributions

Counts only. This file contains no EIN, name, address or description. The first run and
the replay share one `report.json`, so these values hold for both.

### Text–code pairs

There are 644,265 pairs over 3,206,055 records. A headline pair has at least one record
with a native 2022 code, a description that is not empty or a placeholder, and a known
employer (spec, headline rule). There are 239,364 of them. Each has 1 to 18,512
records, with median 3, p25 1, p75 5 and p95 14. Of these, 238,837 have one headline node
and 527 have two to 17.

| Pair kind | Text state | Headline | Pairs |
| --- | --- | --- | ---: |
| employer | text | yes | 239,364 |
| employer | text | no | 289,140 |
| employer | empty | no | 9,312 |
| employer | placeholder | no | 41 |
| unknown employer | text | no | 98,384 |
| unknown employer | empty | no | 8,024 |

The exclusion partition sorts every record by filing year and mapping status. Only
`native_2022` records have the headline basis. All 3,206,055 records appear once.

| Year | concorded | invalid_native_code | native_2022 | unknown_vintage_candidates | unknown_vintage_unmapped | Total |
|---|---:|---:|---:|---:|---:|---:|
| 2016 | 213,432 | 1,546 | 0 | 0 | 0 | 214,978 |
| 2017 | 257,540 | 2,218 | 0 | 0 | 0 | 259,758 |
| 2018 | 280,813 | 8,721 | 0 | 0 | 0 | 289,534 |
| 2019 | 280,168 | 10,307 | 0 | 0 | 0 | 290,475 |
| 2020 | 288,231 | 5,160 | 0 | 0 | 0 | 293,391 |
| 2021 | 301,664 | 16,314 | 0 | 0 | 0 | 317,978 |
| 2022 | 338,902 | 7,897 | 0 | 0 | 0 | 346,799 |
| 2023 | 33,643 | 0 | 358,294 | 0 | 2,297 | 394,234 |
| 2024 | 171,908 | 4,343 | 222,166 | 203 | 0 | 398,620 |
| 2025 | 147,238 | 9,859 | 243,021 | 170 | 0 | 400,288 |

In 2024 and 2025, 333,721 of 798,908 records (41.8%) lack the native 2022 basis.

### Co-ownership

N is 155,436 EINs: the EINs with at least one eligible record. An eligible record has a
2023–2025 filing year, a valid native 2022 industry and a usable, unreconstructed EIN.
When zero-padded EINs are admitted, N is 160,043. The table has 39,152 rows (directed
cells) over 991 industries.

| Measure | Count | Min | p25 | Median | p75 | p95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `n_unweighted` per cell | 39,152 | 1 | 1 | 1 | 2 | 7 | 217 |
| Employers `n(a)` per industry | 991 | 1 | 19 | 61 | 149 | 650 | 9,612 |

Padded-EIN sensitivity: 2,056 cells carry the `numerator:ein_padded_sensitivity:true`
label, and 640 further cells exist only when padded EINs count. No industry exists only
under padded EINs. Every row keeps `size_gate_pending`.

The partition sorts every record by filing year and eligibility. Its cells sum to
3,206,055. The industry-ineligible counts equal the non-`native_2022` counts above in
each year.

| Year | eligible | ein_padded | ein_unusable | industry_ineligible | year_outside_window | Total |
|---|---:|---:|---:|---:|---:|---:|
| 2016 | 0 | 0 | 0 | 0 | 214,978 | 214,978 |
| 2017 | 0 | 0 | 0 | 0 | 259,758 | 259,758 |
| 2018 | 0 | 0 | 0 | 0 | 289,534 | 289,534 |
| 2019 | 0 | 0 | 0 | 0 | 290,475 | 290,475 |
| 2020 | 0 | 0 | 0 | 0 | 293,391 | 293,391 |
| 2021 | 0 | 0 | 0 | 0 | 317,978 | 317,978 |
| 2022 | 0 | 0 | 0 | 0 | 346,799 | 346,799 |
| 2023 | 292,160 | 26,852 | 39,282 | 35,940 | 0 | 394,234 |
| 2024 | 189,680 | 7,195 | 25,291 | 176,454 | 0 | 398,620 |
| 2025 | 211,108 | 10 | 31,903 | 157,267 | 0 | 400,288 |

### Links

The link table has one row per year pair and base record: 3,198,774 rows. Each year pair's
status counts sum to its base records. The link table collapses exact duplicate source
rows into one base record. That removes 1,227 rows, all in 2021 (317,978 records, 316,751
base records). The year 2023 links to both 2024 and 2025, so it is a base year twice.

| Year pair | Base records | no_candidate | weaker_same_id | confirmed_same_id | confirmed_changed_id | ambiguous_id | conflict | missing_id |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2016-2017 | 214,978 | 85,684 | 129,292 | 0 | 0 | 2 | 0 | 0 |
| 2017-2018 | 259,758 | 99,825 | 159,929 | 2 | 0 | 2 | 0 | 0 |
| 2018-2019 | 289,534 | 107,122 | 176,477 | 635 | 0 | 5,300 | 0 | 0 |
| 2019-2020 | 290,475 | 100,387 | 43,954 | 140,054 | 6,078 | 0 | 2 | 0 |
| 2020-2021 | 293,391 | 101,766 | 52,975 | 132,401 | 6,233 | 12 | 4 | 0 |
| 2021-2022 | 316,751 | 122,394 | 50,152 | 132,525 | 10,040 | 1,630 | 10 | 0 |
| 2022-2023 | 346,799 | 140,383 | 50,838 | 146,485 | 9,075 | 0 | 18 | 0 |
| 2023-2024 | 394,234 | 159,845 | 59,276 | 160,575 | 14,528 | 6 | 4 | 0 |
| 2023-2025 | 394,234 | 201,068 | 46,346 | 133,758 | 13,044 | 6 | 12 | 0 |
| 2024-2025 | 398,620 | 153,979 | 45,739 | 184,348 | 14,541 | 0 | 13 | 0 |
| Total | 3,198,774 | 1,272,453 | 814,978 | 1,030,783 | 73,539 | 6,958 | 63 | 0 |

The link statuses are evidence labels, not a verdict on whether two records describe one
establishment. Weaker evidence and conflicts never count as confirmed.

## Rulings

The ledger of plan 11 holds the rulings made during execution. Six of them carry the
label "unclear". On 2026-11-18 the owner settled them.

- The owner kept the five live unclear readings (ledger lines 36, 45, 46, 66 and 68).
  D7 settles two: `compare-runs` prints both run IDs and both paths on failure, and
  `import-reference` prints a data-relative path as a JSON string. D8 settles the
  `n_multi_industry_employers` reading: the EIN has industry `a` and at least one other
  industry in the same year. D9 settles two link readings: `later_row` is the confirmed
  successor for confirmed rows and null for `conflict`, and an ambiguous later ID sets
  only `reason_later_id_ambiguous`.
- D10 settles a separate Task 5 note that the ledger flagged for the owner. Only a
  pair-code row with an empty candidate list references no path. An unresolved row that
  keeps candidates references their paths.
- The spec now states D8, D9 and D10 (`specs/ita-establishment-targets.md`).
- The ledger's sixth unclear ruling (line 55, the `LIMITS` bullet) was superseded during
  Task 8. Fix `2e756f2` restored the spec bullet word for word. Every other ledger ruling
  stays as executed.

## Limits

The `limits` list in `report.json`, which carries the spec's "Methodological limits":

1. ITA is a program-selected filing population. No product here represents all establishments or firms.
2. Codes are self-reported and unvalidated. A pair is a noisy label.
3. Copied-text flags catch exact normalized identity only. Near-copies and reworded index entries stay unflagged.
4. Restricting to native 2022 codes drops about 40% of 2024–2025 records. Some employers' industry sets are partial, so co-ownership can be undercounted. The marginals table measures this per industry.
5. An EIN is a tax-filing entity. One firm can hold several EINs, so co-ownership within EIN can miss relationships across a firm.
6. Which establishments file is shaped by the filing rule. Co-ownership can over-represent designated industries (methodology K6, assumption 6).
7. Linkage uses exact address equality. Relocations and address reformatting break confirmation. Probabilistic linkage stays out of scope.
8. The marginal n(a) pools presence over three years. An employer that left industry a in 2024 still counts in n(a). J(a,b) requires both industries in the same year.

The measured value for limit 4 is 41.8% (333,721 of 798,908 records).

## Not claimed

- Every co-ownership row keeps `size_gate_pending`. This stage sets no minimum count. The
  headline minimum counts are in `specs/findings/v9-ita-naics-minimum-counts.md`.
- No scoring, no null models and no Stage 13 work.
- The reconcilers did not run on the replay. The replay rests on `verify` and
  `compare-runs`.
- No cause is given for the byte differences in two replay Parquet files.
- Coverage and agreement between runs do not show accuracy or representativeness.
- No Stage 10 output feeds embedder training, curriculum, hard-negative mining or model
  selection (R8.4).

## Where the evidence lives

The plan 11 ledger and every command's `.out`, `.err` and `.times` files live in the
git-ignored `.sdd/11-ita-establishment-targets/` folder. Step 12 copies it to
`/Users/lowell/.cache/agent-skills/handoffs/embedding-data/stage10-ledger-backup/workspace/`.
The Stage 4 files start with `stage-4-`.
