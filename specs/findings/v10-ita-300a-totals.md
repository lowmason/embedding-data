# V10 (ITA): Form 300A rows per year against OSHA's published counts

Measured with `uv run embedding-data osha summary` (plan 2, Task 7), from the files the ITA
data page listed on 2026-10-12. The raw files were retrieved at 2026-10-13T03:28:59Z to
03:29:02Z (23:28 to 23:29 on 2026-10-12 at UTC-04:00); the stacked table was last written at
00:09 on 2026-10-13 (UTC-04:00) at commit `1d86f27`. Gaps are recorded, not tuned away
(spec V10).

## Raw files

Twelve files, 257,932,916 bytes, one per year 2016 to 2025 plus the two summary
dictionaries. Each is recorded in `data/raw/manifest.jsonl` (29 entries in all: 17 from
before this stage and these 12).

| Manifest path | SHA-256 (first 12) | Bytes | Through-date |
| --- | --- | --- | --- |
| `osha/summary/2025/ITA_300A_Summary_Data_2025_through_08-31-2026.csv` | `9ea2ee5d7265` | 88,383,913 | 2026-08-31 |
| `osha/summary/2024/ITA_300A_Summary_Data_2024_through_12-31-2025.zip` | `4cbce7ea32dd` | 23,855,931 | 2025-12-31 |
| `osha/summary/2023/ITA_300A_Summary_Data_2023_through_12-31-2024.zip` | `25da8bc426db` | 24,143,043 | 2024-12-31 |
| `osha/summary/2022/ITA-data-cy2022.zip` | `e396af8038d4` | 19,730,409 | none in the name |
| `osha/summary/2021/ITA-data-cy2021.zip` | `5a11abc7c085` | 19,431,073 | none in the name |
| `osha/summary/2020/ITA-Data-CY-2020.zip` | `eb704f2cc343` | 19,480,392 | none in the name |
| `osha/summary/2019/ITA Data CY 2019.zip` | `bf93ea7312bf` | 18,898,257 | none in the name |
| `osha/summary/2018/ITA Data CY 2018.zip` | `0bd2e8475a57` | 16,970,794 | none in the name |
| `osha/summary/2017/ITA Data CY 2017.zip` | `354fb246be90` | 14,682,864 | none in the name |
| `osha/summary/2016/ITA Data CY 2016.zip` | `9f41c720fb02` | 12,106,381 | none in the name |
| `osha/summary/summary_data_dictionary.pdf` | `54996d2febb7` | 127,028 | none in the name |
| `osha/summary/ITA_Data_Dictionary.pdf` | `710af4f89575` | 122,831 | none in the name |

The 2025 file runs through 2026-08-31, and the data page listed no newer release that day.
The 2023 and 2024 zips each hold one CSV whose name ends `_v2.csv`; the plan records OSHA's
re-posting of both files under unchanged zip names (the 2023 one on 2026-05-20), which this
run did not check.

## Rows per year

The command's totals lines, verbatim:

```text
2016: 214,978 rows from osha/summary/2016/ITA Data CY 2016.zip; no published count located
2017: 259,758 rows from osha/summary/2017/ITA Data CY 2017.zip; no published count located
2018: 289,534 rows from osha/summary/2018/ITA Data CY 2018.zip; no published count located
2019: 290,475 rows from osha/summary/2019/ITA Data CY 2019.zip; no published count located
2020: 293,391 rows from osha/summary/2020/ITA-Data-CY-2020.zip; no published count located
2021: 317,978 rows from osha/summary/2021/ITA-data-cy2021.zip; no published count located
2022: 346,799 rows from osha/summary/2022/ITA-data-cy2022.zip; no published count located
2023: 394,234 rows from osha/summary/2023/ITA_300A_Summary_Data_2023_through_12-31-2024.zip; OSHA published exactly 385,488 as of 2024-05-31 (OSHA 2023 Work-Related Injury and Illness Summary); gap +8,746
2024: 398,620 rows from osha/summary/2024/ITA_300A_Summary_Data_2024_through_12-31-2025.zip; OSHA published over 390,000 (OSHA 2024 Work-Related Injury and Illness Summary); gap +8,620
2025: 400,288 rows from osha/summary/2025/ITA_300A_Summary_Data_2025_through_08-31-2026.csv; no published count located
```

## Published counts

- 2023: exactly 385,488 establishments as of 2024-05-31 (OSHA 2023 Work-Related Injury
  and Illness Summary). The 2023 file runs through 2024-12-31, and the plan records a
  re-posting on 2026-05-20 with a `_v2` member (the zip's CSV is named `_v2.csv`; the date
  was not checked), so more rows than the count is expected. The table holds 394,234 rows,
  8,746 more.
- 2024: "over 390,000" (OSHA 2024 Work-Related Injury and Illness Summary), with no as-of
  date. The file runs through 2025-12-31. The table holds 398,620 rows, 8,620 more than the
  lower bound, so the true gap is at most that.
- OSHA's "Comparison Between OSHA ITA Data and BLS SOII Estimates" says "In 2024, OSHA
  collected summary data from over 370,000 establishments" without naming the data year;
  it is listed here and not used as a comparison.
- J.J. Keller reported "more than 300,000" establishments for 2022. That is not an OSHA
  publication and is not used.
- No OSHA-published count was located for 2016–2022 or for 2025. The 2025 file has a
  through-date (2026-08-31) but no count to set beside it; the 2016–2022 file names carry
  neither.

## Values the full files carried that the fixtures did not

The fixtures were built from the first ~900 rows of each file. The live build stopped on
structure twice (plan Task 7 Step 3), and the owner decided how each case is handled (plan
decisions D8–D11, implemented in Tasks 7a and 7b). The build has no filter step, and the
2024 and 2025 table counts equal the row counts a diagnostic read from their CSVs (398,620
and 400,288).

| File | Rows | Delivered value | Stored as |
| --- | --- | --- | --- |
| 2023 | 2,297 | `naics_year` blank beside a six-digit `naics_code` (the first build rejected any non-null undefined vintage and accepted this file) | `naics_year` null, `flag_naics_year_unknown` true |
| 2024 | 203 | `naics_year` `0` beside a six-digit code | the same |
| 2025 | 170 | `naics_year` `0` on 167 rows and `2025` on 3, beside six-digit codes | the same |
| 2019 | 1 | `establishment_type` text `Executive and Legislative Offices` (id 857641, County Executive Office) | `establishment_type` null |
| 2024 | 1 | `total_hours_worked` `8.62847E+11` (id 2886593, 133 employees) | 862,847,000,000; `flag_hours_per_employee` true |
| 2025 | 3 | `total_hours_worked` `1.40142E+11`, `1.00551E+11`, `1.19759E+11` (ids 2994045, 2997600, 2993505) | 140,142,000,000; 100,551,000,000; 119,759,000,000; flagged |

Every other file and column passed the structural checks.

## Observed in the stacked table

The table has 3,206,055 rows over ten years. `size_class` holds only `1`, `2` and `3`, with
no nulls.

| Year | Rows | size 2 | size 21 | size 22 | naics 2012 | naics 2017 | naics 2022 | naics code null | ein null | est. id null | duplicate ids | repeated est. ids | flag employment | flag hours | flag below size |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2016 | 214,978 | 152,311 | 0 | 0 | 214,978 | 0 | 0 | 0 | 214,978 | 0 | 0 | 2 | 1,315 | 7,290 | 35,459 |
| 2017 | 259,758 | 188,655 | 0 | 0 | 259,758 | 0 | 0 | 0 | 259,756 | 0 | 0 | 2 | 448 | 9,393 | 41,399 |
| 2018 | 289,534 | 212,799 | 0 | 0 | 289,534 | 0 | 0 | 0 | 287,579 | 0 | 0 | 5,300 | 650 | 10,403 | 44,226 |
| 2019 | 290,475 | 216,345 | 0 | 0 | 290,475 | 0 | 0 | 0 | 52,009 | 0 | 0 | 0 | 592 | 10,740 | 40,482 |
| 2020 | 293,391 | 210,812 | 0 | 0 | 293,391 | 0 | 0 | 0 | 31,901 | 0 | 0 | 12 | 1,112 | 11,112 | 50,449 |
| 2021 | 317,978 | 234,368 | 0 | 0 | 317,978 | 0 | 0 | 0 | 31,042 | 0 | 4,082 | 4,084 | 1,199 | 22,819 | 47,472 |
| 2022 | 346,799 | 247,894 | 227 | 65 | 346,799 | 0 | 0 | 0 | 36,459 | 0 | 0 | 0 | 1,250 | 13,152 | 60,471 |
| 2023 | 394,234 | 62,305 | 150,483 | 55,981 | 11,756 | 21,887 | 358,294 | 0 | 40,543 | 0 | 0 | 6 | 2,121 | 17,852 | 83,403 |
| 2024 | 398,620 | 41,833 | 168,310 | 60,452 | 164,137 | 11,964 | 222,316 | 0 | 43,260 | 0 | 0 | 0 | 1,635 | 28,719 | 86,627 |
| 2025 | 400,288 | 34,625 | 158,522 | 60,982 | 144,472 | 12,335 | 243,311 | 0 | 46,062 | 0 | 0 | 0 | 4,517 | 16,795 | 103,814 |

"Duplicate ids" and "repeated est. ids" count rows whose `id`, or non-null
`establishment_id`, also appears on another row of the same year, not the extra rows.

- **Size codes.** Code `2` is present in every year. Codes `21` and `22` first appear in
  large numbers with the 2023 file (150,483 and 55,981 rows), and code `2` stays beside
  them in 2023 (62,305 rows), 2024 (41,833) and 2025 (34,625). The 2022 file already
  carries 227 rows of `21` and 65 of `22`; the 2016–2021 files carry none.
- **`naics_year`.** Files before 2023 carry no `naics_year`: no row before 2023 with a
  code has a delivered one, so all of them (every row has a code) took 2012 from the
  dictionary, marked `naics_year_from_dictionary`. From 2023 the vintages are mixed.
  2012 is 3.0% of 2023 rows, 41.2% of 2024 and 36.1% of 2025. 2022 is 90.9%, 55.8% and
  60.8%. 2017 is 5.6%, 3.0% and 3.1%. A code with no usable vintage, flagged by
  `flag_naics_year_unknown`, is 2,297 rows in 2023, 203 in 2024 and 170 in 2025, 2,670 in
  all.
- **`ein` null.** 100.0% of 2016 rows (214,978 of 214,978), 99.999% of 2017 (259,756 of
  259,758) and 99.3% of 2018 (287,579 of 289,534). From 2019 it is 17.9%, then 10.9%,
  9.8%, 10.5%, 10.3%, 10.9% and 11.5% (2020 to 2025).
- **`establishment_id`.** Non-null on every row of every year from 2016 (0 null). Within
  a year it repeats on 2 rows in 2016 and 2017, 5,300 in 2018, 12 in 2020, 4,084 in 2021
  and 6 in 2023; it does not repeat in 2019, 2022, 2024 or 2025.
- **Duplicate record `id`s.** Only 2021 has any: 4,082 rows share an `id`, and 4,084 rows
  repeat an `establishment_id` in 2021. Whether they are the same rows, or identical, was
  not examined.
- **Null values.** `establishment_type` is null on 29,518, 36,670 and 44,876 rows in
  2016, 2017 and 2018, then on at most 2,957 rows a year (2,957 in 2019, 447 in 2025).
  `total_hours_worked` is null on 3, 4, 5 and 1 rows in 2016, 2017, 2018 and 2022, and on
  none in other years. `size` is never null.
- **Flags.** The counts are in the table. `flag_hours_per_employee` is null exactly where
  `flag_employment` is set: the two counts are equal in all ten years, from 448 rows in
  2017 to 4,517 in 2025. Flagged rows are kept. Some stored hours are implausible. The
  largest `total_hours_worked` is 16,831,620,723,179 (2019, id 1059547, 7 employees, as read
  from the built table), and
  the largest in 2024 is 862,847,000,000 (the scientific-notation row, 133 employees).
  Both rows have `flag_hours_per_employee` set.

## Consequences for later stages

- **Stage 3 (V2 `establishment_id` persistence; the pre-2023 link on `ein`).**
  `establishment_id` is non-null on every row of every year, 2016 to 2025. Within a year it
  repeats on 2 rows in 2016 and 2017, 5,300 in 2018, 12 in 2020, 4,084 in 2021 and 6 in
  2023. V2 checks whether a 2023 `establishment_id` reappears in 2024 and 2025 with the
  same `ein` and address, and `ein` is null on 10.3% of 2023 rows, 10.9% of 2024 and 11.5%
  of 2025. R2.7 links the earlier years on `ein` plus name and address, and `ein` is null
  on 99.3% to 100.0% of 2016–2018 rows and 17.9% of 2019 rows. Record `id` repeats within
  2021 (4,082 rows).
- **Stage 4 (`naics_year` mix; the deferred industry half of the filing-rule flag).**
  Before 2023 every row's vintage is the dictionary's 2012 (214,978 to 346,799 rows a
  year). From 2023 each file mixes vintages. 2022 is the majority label (90.9%, 55.8% and
  60.8% of 2023 to 2025 rows), but 2012 is 41.2% of 2024 rows and 36.1% of 2025 rows, and
  2017 is 3.0% to 5.6%. 2,670 rows have a code and no usable vintage (2,297, 203 and 170
  in 2023 to 2025).
- **Stage 10 (`ein`-based dedup and co-ownership).** R2.6 deduplicates on `ein`, else
  `company_name`, and R7.2's co-ownership family is built within an employer (`ein`).
  `ein` is null on 99.3% to 100.0% of 2016–2018 rows (1,955 of 289,534 rows in 2018 carry
  one), 17.9% of 2019 rows and 9.8% to 11.5% of 2020–2025 rows. The null share of
  `company_name`, R2.6's fallback, was not measured.
