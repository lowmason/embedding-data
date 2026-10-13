# ITA V1–V3 verification evidence and adopted rules

Owner approved A1–A4 as proposed on 2026-10-13. The adopted rules and full measured evidence are recorded below.


All ten V1 filing years and all required V2 comparisons are measured. V1 empty descriptions range from **6.10% to 8.04%**, exact copied official titles from **14.78% to 22.38%**, and rows repeating an employer/description key from **53.13% to 58.80%**. The finite exact placeholder vocabulary flags 0.0030%–0.1063% by year; frequent generic valid descriptions remain text. Unknown employer shares range from 1.07% to 10.69%; early company-name fallback and missing EIN limit employer identity.

For the 2023 cohort, candidate ID reappearance is **55.77% in 2024** and **45.69% in 2025**, while conservative confirmed same-EIN/full-address links are **40.73%** and **33.93%** of all cohort IDs. Among eligible uniquely matched EIN/name/address tuples, changed-ID shares are **8.47%** and **9.19%**. Reappearance alone is not confirmed identity. Zero confirmed links for 2016→2017 reflects missing EIN evidence, despite 129,292 candidate IDs reappearing.

The complete V3 sample has **20,628 rows in 3,378 strata**, representing 3,204,828 exact-distinct ITA source rows. Exact compatible geocode coverage is **47.04% of sampled rows / 64.41% population-weighted**; compatible single-county HUD coverage is **38.73% / 76.64%**. The adopted exact-geocode-first, single-county-HUD-fallback rule can assign **61.14% / 91.08%**, respectively. Conditional single-county agreement is **4,717/4,718 = 99.9788% raw**, **99.9994% weighted**; dominant-county agreement is **8,579/8,835 = 97.1024% raw**, **98.2361% weighted**. Agreement supports comparison, not accuracy. No legacy Connecticut county result occurred in this sample or the selected HUD reference; that does not remove the general vintage compatibility requirement.

Official title parsing passed full-file checks: **2012 expected/actual 2,209; 2017 expected/actual 2,196; 2022 expected/actual 2,125**, with levels 2–6 and official ranged sector codes retained. Both full offline `measure` runs completed with exit 0. Canonical content hashes matched for V1, quality, V2, V3 strata, sample and full reports. Full `reports.json` canonical SHA256 is `1f43879a895450d7448dfb1876e08c4fe2e7e4e86977dd75f05d586e015644ba`; sample canonical SHA256 is `309021f3b113b219b134a8749b7b72e97760d5014e19c8ddc3916c238dbf8676`. Reproduction artifacts remain under `data/derived/osha/verification/v1_v3_20261013_scopefix`; detailed command/output and parity hashes are recorded in the ignored execution report `.sdd/3-ita-verification/final-fixes-report.md` (the original run history remains in `task-6-evidence-report.md`).


## Owner-approved returned-county scope correction and cache replay

On 2026-10-13 the owner approved D8: enforce existing R6.4/A4 scope using the returned county as well as the normalized delivered state. No cleaning, linkage or county method was newly selected; adopted A1–A4 below remain unchanged. The corrected full run is `v1_v3_20261013_scopefix`, with county-code SHA256 `b7ce702f41ecd7a6008f1e90624576f5772f742c6f5bd8ffa16c964f5196830f` from commit `1a7ec1b`. Original run `v1_v3_20261013`, its inventory, reports, samples, requests and immutable raw catalog/response files remain retained and unchanged.

Before any cache copy, canonical sample rows and all three request hashes, CSV bytes and IDs were verified identical to the original run; raw input receipts were identical. Five catalog/response files were copied to new relative raw paths, verified against original hashes and sizes, and recorded through `manifest.describe_file`/`append_entries` with the exact original source URL, client/version, retrieval timestamp, proxies and other receipt metadata. The new `geocoding.json` and report inventory explicitly record replay type, original run and both paths/receipts per copied file. Cached `acquire_geocodes` then regenerated the inventory and revalidated all 20,628 response IDs under an HTTP guard: **zero HTTP calls**. This is replay of original receipts, never fresh acquisition; acquisition_start/end in the inventory remain original response receipt times. Original mutable Current service limitations still apply.

The shipped `prepare` rebuilt the common derived summary Parquet, whose physical bytes differ from the old run's table hash. A second rebuild had the same canonical full-row hash `7667489f3b6a3820665a5081ecfe0b406d57e4a3a49ad8230d532b6b2d1b7c7f`; V1, quality and V2 aggregates also equal the original reports exactly. New inputs record the actual current shared-table hash after this parity rebuild; original inputs are never relabeled. The original run's frozen reports/cache remain evidence, but directly rerunning its old input check against the regenerated shared table would require the original physical table bytes and original code.

Assignment checks the county selected by exact-compatible Census first, otherwise compatible single-positive-BUS HUD, and excludes state prefixes **60/66/69/72/74/78** plus existing normalized delivered-state exclusions. A selected out-of-scope exact Census county is retained/flagged and cannot become an assignment; it does not silently redirect to HUD. Comparison checks both returned counties, separately for dominant and single diagnostics. `n_out_of_scope` continues to count excluded delivered state only; `n_geocode_out_of_scope`, `n_zip_single_out_of_scope` and `n_zip_dominant_out_of_scope` count each returned-method territory flag independently. Those flags can overlap and use all 20,628 sample rows (weighted denominator 3,204,828); they never change population/stratum denominators or raw Match/Non_Exact/No_Match/Tie classifications. `n_geocode_exact` and `n_zip_single_compatible` retain their coverage/vintage meaning and can include excluded geography; assignment and joint-comparison counts apply scope gates.

Measured correction: assignable rows **12,621 → 12,611**, weighted rows **2,919,085.75 → 2,919,075.75**, a decrease of ten in both. The affected HUD fallbacks comprise four Non_Exact and six No_Match rows with excluded PR/GU/VI counties despite NJ/AE/PW delivered state. No observed exact Census assignment was affected. Coverage, raw response statuses, ZIP candidate classes, both agreement numerators/denominators, all V1/V2/quality aggregates and all sample/population denominators are unchanged. All **3,378** stratum rows below have been regenerated from the corrected full `reports.json`.

| flag | raw_n | sample_denominator | raw_share | weighted_n | population_denominator | weighted_share |
| --- | --- | --- | --- | --- | --- | --- |
| n_out_of_scope | 719 | 20628 | 0.034855536164436686 | 14883.0 | 3204828.0 | 0.004643930969150295 |
| n_geocode_out_of_scope | 75 | 20628 | 0.0036358347876672484 | 1555.75 | 3204828.0 | 0.0004854394682023497 |
| n_zip_single_out_of_scope | 323 | 20628 | 0.015658328485553617 | 5390.125 | 3204828.0 | 0.0016818765312834262 |
| n_zip_dominant_out_of_scope | 423 | 20628 | 0.02050610820244328 | 9991.125 | 3204828.0 | 0.0031175229996742416 |

Both full offline measurements completed: all canonical Parquet/JSON outputs match between runs; final whole-tree audit reports **0 raw provenance discrepancies**. The full milestone suite passed **284 tests, 1 deselected**, **2 Behave scenarios/10 steps**, ruff and lock checks. The county regression was RED (26 failures) before implementation, GREEN afterward; direct duplicate-record and correct-hash/wrong-size manifest refusal tests exercise already-correct production branches.

## Inputs and versions

```json
{
  "geocoding": {
    "acquisition_end": "2026-10-13T14:43:59+00:00",
    "acquisition_start": "2026-10-13T14:32:59+00:00",
    "benchmark": "Public_AR_Current",
    "benchmark_id": "4",
    "benchmark_snapshot_limit": "Current address data can change between batches, including resumed acquisition; catalogs identify the request options, not a frozen address-source snapshot.",
    "catalogs": [
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "references/census-geocoder/v1_v3_20261013_scopefix/benchmarks.json",
        "proxies": [],
        "retrieved_at": "2026-10-13T14:20:37+00:00",
        "samples": [],
        "sha256": "d3434b3cfc79fbc6b33f8452e719dffba1416b44a3817b3dfb721067416242ce",
        "size": 547,
        "source_url": "https://geocoding.geo.census.gov/geocoder/benchmarks",
        "through_date": null
      },
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "references/census-geocoder/v1_v3_20261013_scopefix/vintages.json",
        "proxies": [],
        "retrieved_at": "2026-10-13T14:20:37+00:00",
        "samples": [],
        "sha256": "4b4235e3efd7142d2aa1564584619cb7cbf8712b1142aaa8661283fac895856d",
        "size": 2057,
        "source_url": "https://geocoding.geo.census.gov/geocoder/vintages?benchmark=4",
        "through_date": null
      }
    ],
    "replay": {
      "files": [
        {
          "copy": {
            "client": "httpx",
            "client_version": "0.28.1",
            "collection": null,
            "extract_number": null,
            "path": "references/census-geocoder/v1_v3_20261013_scopefix/benchmarks.json",
            "proxies": [],
            "retrieved_at": "2026-10-13T14:20:37+00:00",
            "samples": [],
            "sha256": "d3434b3cfc79fbc6b33f8452e719dffba1416b44a3817b3dfb721067416242ce",
            "size": 547,
            "source_url": "https://geocoding.geo.census.gov/geocoder/benchmarks",
            "through_date": null
          },
          "original": {
            "client": "httpx",
            "client_version": "0.28.1",
            "collection": null,
            "extract_number": null,
            "path": "references/census-geocoder/v1_v3_20261013/benchmarks.json",
            "proxies": [],
            "retrieved_at": "2026-10-13T14:20:37+00:00",
            "samples": [],
            "sha256": "d3434b3cfc79fbc6b33f8452e719dffba1416b44a3817b3dfb721067416242ce",
            "size": 547,
            "source_url": "https://geocoding.geo.census.gov/geocoder/benchmarks",
            "through_date": null
          }
        },
        {
          "copy": {
            "client": "httpx",
            "client_version": "0.28.1",
            "collection": null,
            "extract_number": null,
            "path": "references/census-geocoder/v1_v3_20261013_scopefix/vintages.json",
            "proxies": [],
            "retrieved_at": "2026-10-13T14:20:37+00:00",
            "samples": [],
            "sha256": "4b4235e3efd7142d2aa1564584619cb7cbf8712b1142aaa8661283fac895856d",
            "size": 2057,
            "source_url": "https://geocoding.geo.census.gov/geocoder/vintages?benchmark=4",
            "through_date": null
          },
          "original": {
            "client": "httpx",
            "client_version": "0.28.1",
            "collection": null,
            "extract_number": null,
            "path": "references/census-geocoder/v1_v3_20261013/vintages.json",
            "proxies": [],
            "retrieved_at": "2026-10-13T14:20:37+00:00",
            "samples": [],
            "sha256": "4b4235e3efd7142d2aa1564584619cb7cbf8712b1142aaa8661283fac895856d",
            "size": 2057,
            "source_url": "https://geocoding.geo.census.gov/geocoder/vintages?benchmark=4",
            "through_date": null
          }
        },
        {
          "copy": {
            "client": "httpx",
            "client_version": "0.28.1",
            "collection": null,
            "extract_number": null,
            "path": "references/census-geocoder/v1_v3_20261013_scopefix/926bb0cea8e783e4a80dcf5c5bf54130a75267dfbb17b9da3429d5653a2c1437.csv",
            "proxies": [],
            "retrieved_at": "2026-10-13T14:38:37+00:00",
            "samples": [],
            "sha256": "ec01d6973d81c4bbd7c1c59d06828d690321703249c1a8beddea8bbbe19ca88d",
            "size": 2143879,
            "source_url": "https://geocoding.geo.census.gov/geocoder/geographies/addressbatch",
            "through_date": null
          },
          "original": {
            "client": "httpx",
            "client_version": "0.28.1",
            "collection": null,
            "extract_number": null,
            "path": "references/census-geocoder/v1_v3_20261013/926bb0cea8e783e4a80dcf5c5bf54130a75267dfbb17b9da3429d5653a2c1437.csv",
            "proxies": [],
            "retrieved_at": "2026-10-13T14:38:37+00:00",
            "samples": [],
            "sha256": "ec01d6973d81c4bbd7c1c59d06828d690321703249c1a8beddea8bbbe19ca88d",
            "size": 2143879,
            "source_url": "https://geocoding.geo.census.gov/geocoder/geographies/addressbatch",
            "through_date": null
          }
        },
        {
          "copy": {
            "client": "httpx",
            "client_version": "0.28.1",
            "collection": null,
            "extract_number": null,
            "path": "references/census-geocoder/v1_v3_20261013_scopefix/9631f974891dd379c30a276388e2932d3e663c896edef85bc0afa4a7b12e8072.csv",
            "proxies": [],
            "retrieved_at": "2026-10-13T14:43:59+00:00",
            "samples": [],
            "sha256": "96749f76f51dc0861dd2a0302d9c145b56f0b7de96130ebf9cf9aaa7b903d4c2",
            "size": 2121171,
            "source_url": "https://geocoding.geo.census.gov/geocoder/geographies/addressbatch",
            "through_date": null
          },
          "original": {
            "client": "httpx",
            "client_version": "0.28.1",
            "collection": null,
            "extract_number": null,
            "path": "references/census-geocoder/v1_v3_20261013/9631f974891dd379c30a276388e2932d3e663c896edef85bc0afa4a7b12e8072.csv",
            "proxies": [],
            "retrieved_at": "2026-10-13T14:43:59+00:00",
            "samples": [],
            "sha256": "96749f76f51dc0861dd2a0302d9c145b56f0b7de96130ebf9cf9aaa7b903d4c2",
            "size": 2121171,
            "source_url": "https://geocoding.geo.census.gov/geocoder/geographies/addressbatch",
            "through_date": null
          }
        },
        {
          "copy": {
            "client": "httpx",
            "client_version": "0.28.1",
            "collection": null,
            "extract_number": null,
            "path": "references/census-geocoder/v1_v3_20261013_scopefix/213084b85ffea6e76bfe40923bd38d8870ffc33bcecb12cab3cca08b38732062.csv",
            "proxies": [],
            "retrieved_at": "2026-10-13T14:32:59+00:00",
            "samples": [],
            "sha256": "7905cbb4b4f175919609e521e05da0447637b24324e271aec7cbd7ae369c64a4",
            "size": 134167,
            "source_url": "https://geocoding.geo.census.gov/geocoder/geographies/addressbatch",
            "through_date": null
          },
          "original": {
            "client": "httpx",
            "client_version": "0.28.1",
            "collection": null,
            "extract_number": null,
            "path": "references/census-geocoder/v1_v3_20261013/213084b85ffea6e76bfe40923bd38d8870ffc33bcecb12cab3cca08b38732062.csv",
            "proxies": [],
            "retrieved_at": "2026-10-13T14:32:59+00:00",
            "samples": [],
            "sha256": "7905cbb4b4f175919609e521e05da0447637b24324e271aec7cbd7ae369c64a4",
            "size": 134167,
            "source_url": "https://geocoding.geo.census.gov/geocoder/geographies/addressbatch",
            "through_date": null
          }
        }
      ],
      "http_calls": 0,
      "kind": "verified immutable cache copy; no fresh acquisition",
      "original_receipt_metadata_preserved": true,
      "original_run_id": "v1_v3_20261013"
    },
    "responses": [
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "references/census-geocoder/v1_v3_20261013_scopefix/926bb0cea8e783e4a80dcf5c5bf54130a75267dfbb17b9da3429d5653a2c1437.csv",
        "proxies": [],
        "retrieved_at": "2026-10-13T14:38:37+00:00",
        "samples": [],
        "sha256": "ec01d6973d81c4bbd7c1c59d06828d690321703249c1a8beddea8bbbe19ca88d",
        "size": 2143879,
        "source_url": "https://geocoding.geo.census.gov/geocoder/geographies/addressbatch",
        "through_date": null
      },
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "references/census-geocoder/v1_v3_20261013_scopefix/9631f974891dd379c30a276388e2932d3e663c896edef85bc0afa4a7b12e8072.csv",
        "proxies": [],
        "retrieved_at": "2026-10-13T14:43:59+00:00",
        "samples": [],
        "sha256": "96749f76f51dc0861dd2a0302d9c145b56f0b7de96130ebf9cf9aaa7b903d4c2",
        "size": 2121171,
        "source_url": "https://geocoding.geo.census.gov/geocoder/geographies/addressbatch",
        "through_date": null
      },
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "references/census-geocoder/v1_v3_20261013_scopefix/213084b85ffea6e76bfe40923bd38d8870ffc33bcecb12cab3cca08b38732062.csv",
        "proxies": [],
        "retrieved_at": "2026-10-13T14:32:59+00:00",
        "samples": [],
        "sha256": "7905cbb4b4f175919609e521e05da0447637b24324e271aec7cbd7ae369c64a4",
        "size": 134167,
        "source_url": "https://geocoding.geo.census.gov/geocoder/geographies/addressbatch",
        "through_date": null
      }
    ],
    "vintage": "ACS2025_Current",
    "vintage_id": "425"
  },
  "inputs": {
    "algorithm": "ita-verification-v1",
    "code_sha256": {
      "ita_county_verification.py": "b7ce702f41ecd7a6008f1e90624576f5772f742c6f5bd8ffa16c964f5196830f",
      "ita_references.py": "2fbb723fdec6a712b76e82a687de76cc631b023e6ff8520419d9c920588b452c",
      "ita_summary.py": "082ccabe0ab00d7b03fcfbaea5e2622fced83b4cf1cdef2d51b9a5f5d05f6229",
      "ita_verification.py": "5322a770c808972f1dcb6e640b04750d2f1337bc06a399bcfa87bb59d2464a38",
      "ita_verification_run.py": "fa4b75b6ad1667e19ce2e46bc77b0320d246cd34b96d818e9d330c9e9d955019",
      "manifest.py": "b734f4a81923838f21eed010350ddcc8c5b1a632d5defb6d115925273ab36b80"
    },
    "hud_path": "references/hud/2025Q4/ZIP-COUNTY_122025.xlsx",
    "per_stratum": 8,
    "raw_inputs": [
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "osha/summary/2016/ITA Data CY 2016.zip",
        "proxies": [],
        "retrieved_at": "2026-10-13T03:29:02+00:00",
        "samples": [],
        "sha256": "9f41c720fb02f78788f1090e5fc885fdb09343fc349c4ae4c80cc9165d83742f",
        "size": 12106381,
        "source_url": "https://www.osha.gov/sites/default/files/ITA%20Data%20CY%202016.zip",
        "through_date": null
      },
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "osha/summary/2017/ITA Data CY 2017.zip",
        "proxies": [],
        "retrieved_at": "2026-10-13T03:29:01+00:00",
        "samples": [],
        "sha256": "354fb246be90d6bac3d4a7c94e44f90d40f1d3ff73f911d37691ae98a87de0fb",
        "size": 14682864,
        "source_url": "https://www.osha.gov/sites/default/files/ITA%20Data%20CY%202017.zip",
        "through_date": null
      },
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "osha/summary/2018/ITA Data CY 2018.zip",
        "proxies": [],
        "retrieved_at": "2026-10-13T03:29:01+00:00",
        "samples": [],
        "sha256": "0bd2e8475a5766baba8883a1258a92168c43c5ff551c853b1992641814b4dc2f",
        "size": 16970794,
        "source_url": "https://www.osha.gov/sites/default/files/ITA%20Data%20CY%202018.zip",
        "through_date": null
      },
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "osha/summary/2019/ITA Data CY 2019.zip",
        "proxies": [],
        "retrieved_at": "2026-10-13T03:29:01+00:00",
        "samples": [],
        "sha256": "bf93ea7312bfe34d903c1272f15c785a61b8c8bbc6df6e09f0d3fe372205ac6e",
        "size": 18898257,
        "source_url": "https://www.osha.gov/sites/default/files/ITA%20Data%20CY%202019.zip",
        "through_date": null
      },
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "osha/summary/2020/ITA-Data-CY-2020.zip",
        "proxies": [],
        "retrieved_at": "2026-10-13T03:29:01+00:00",
        "samples": [],
        "sha256": "eb704f2cc343adc7710b48204015ac11c3018fae684f44747158d731e713899b",
        "size": 19480392,
        "source_url": "https://www.osha.gov/sites/default/files/ITA-Data-CY-2020.zip",
        "through_date": null
      },
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "osha/summary/2021/ITA-data-cy2021.zip",
        "proxies": [],
        "retrieved_at": "2026-10-13T03:29:00+00:00",
        "samples": [],
        "sha256": "5a11abc7c085f07f08f130c25bf78c85581b2379fb8b514f728bfcdf5d61b4a3",
        "size": 19431073,
        "source_url": "https://www.osha.gov/sites/default/files/ITA-data-cy2021.zip",
        "through_date": null
      },
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "osha/summary/2022/ITA-data-cy2022.zip",
        "proxies": [],
        "retrieved_at": "2026-10-13T03:29:00+00:00",
        "samples": [],
        "sha256": "e396af8038d40d74b96ebb6ee9b561bbcb8907ee66adff089402a676c919e6ef",
        "size": 19730409,
        "source_url": "https://www.osha.gov/sites/default/files/ITA-data-cy2022.zip",
        "through_date": null
      },
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "osha/summary/2023/ITA_300A_Summary_Data_2023_through_12-31-2024.zip",
        "proxies": [],
        "retrieved_at": "2026-10-13T03:29:00+00:00",
        "samples": [],
        "sha256": "25da8bc426db219a7a5fe872e73830afebdfac87c460f8cf6561658e7103b487",
        "size": 24143043,
        "source_url": "https://www.osha.gov/sites/default/files/ITA_300A_Summary_Data_2023_through_12-31-2024.zip",
        "through_date": "2024-12-31"
      },
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "osha/summary/2024/ITA_300A_Summary_Data_2024_through_12-31-2025.zip",
        "proxies": [],
        "retrieved_at": "2026-10-13T03:29:00+00:00",
        "samples": [],
        "sha256": "4cbce7ea32dd4060f442a528670936e552d1b731925f320d9d25a168f9b60b1d",
        "size": 23855931,
        "source_url": "https://www.osha.gov/sites/default/files/ITA_300A_Summary_Data_2024_through_12-31-2025.zip",
        "through_date": "2025-12-31"
      },
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "osha/summary/2025/ITA_300A_Summary_Data_2025_through_08-31-2026.csv",
        "proxies": [],
        "retrieved_at": "2026-10-13T03:28:59+00:00",
        "samples": [],
        "sha256": "9ea2ee5d7265cddf753d22633af17d4aaba4ab81629341462a8c9912d19a99fc",
        "size": 88383913,
        "source_url": "https://www.osha.gov/sites/default/largefiles/ITA_300A_Summary_Data_2025_through_08-31-2026.csv",
        "through_date": "2026-08-31"
      },
      {
        "client": "manual-import",
        "client_version": "0.1.0",
        "collection": null,
        "extract_number": null,
        "path": "references/hud/2025Q4/ZIP-COUNTY_122025.xlsx",
        "proxies": [
          "retrieved_at"
        ],
        "retrieved_at": "2026-10-13T14:19:32+00:00",
        "samples": [],
        "sha256": "554379b618f21380bed6777a9c69845ac138843c1a57f951886d605bc9611c68",
        "size": 2462769,
        "source_url": "https://www.huduser.gov/portal/datasets/usps_crosswalk.html",
        "through_date": null
      },
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "references/naics/2012_NAICS_Structure.xls",
        "proxies": [],
        "retrieved_at": "2026-10-13T14:19:19+00:00",
        "samples": [],
        "sha256": "50eba48db4e11f863e015d4d2bbaaf618565bd94ef9b019fe62b9bbaddbaaafb",
        "size": 254976,
        "source_url": "https://www.census.gov/naics/2012NAICS/2012_NAICS_Structure.xls",
        "through_date": null
      },
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "references/naics/2017_NAICS_Structure.xlsx",
        "proxies": [],
        "retrieved_at": "2026-10-13T14:19:20+00:00",
        "samples": [],
        "sha256": "662b5a2bdff10938997acd7f59f84331527d6f06ff24d5533331581a00a94aad",
        "size": 95610,
        "source_url": "https://www.census.gov/naics/2017NAICS/2017_NAICS_Structure.xlsx",
        "through_date": null
      },
      {
        "client": "httpx",
        "client_version": "0.28.1",
        "collection": null,
        "extract_number": null,
        "path": "references/naics/2022_NAICS_Structure.xlsx",
        "proxies": [],
        "retrieved_at": "2026-10-13T14:19:20+00:00",
        "samples": [],
        "sha256": "217c9e0d4d74e7517bc288f5f308b73aa0de5ee787976a6dd222412be28ada22",
        "size": 88218,
        "source_url": "https://www.census.gov/naics/2022NAICS/2022_NAICS_Structure.xlsx",
        "through_date": null
      }
    ],
    "requests": {
      "0000.csv": "926bb0cea8e783e4a80dcf5c5bf54130a75267dfbb17b9da3429d5653a2c1437",
      "0001.csv": "9631f974891dd379c30a276388e2932d3e663c896edef85bc0afa4a7b12e8072",
      "0002.csv": "213084b85ffea6e76bfe40923bd38d8870ffc33bcecb12cab3cca08b38732062"
    },
    "sample_salt": "embedding-data:V3:2026-10-13:v1",
    "sample_sha256": "e0d84bb7e9561cf2646f89242222185cb537875db94864f217d3d73a94638af7",
    "table_sha256": "6335cda7adb40a41c4a11d57d22048999449ac8d078a2ec0291f0198cd9136a8",
    "title_counts": [
      {
        "len": 2209,
        "vintage": 2012
      },
      {
        "len": 2196,
        "vintage": 2017
      },
      {
        "len": 2125,
        "vintage": 2022
      }
    ],
    "versions": {
      "fastexcel": "0.21.0",
      "httpx": "0.28.1",
      "polars": "2.0.0"
    }
  }
}
```

## V1

| year_filing_for | n_rows | n_empty | n_placeholder | n_copied_any | n_native_title_match | n_vintage_unknown | n_employer_unknown | n_employer_company | n_ein_padded | n_mojibake | length_min | length_p25 | length_p50 | length_p75 | length_p95 | length_max | n_repeat_rows | n_repeat_excess | share_empty | share_placeholder | share_copied_any | share_repeat_rows | share_repeat_excess | share_employer_unknown | share_native_title_match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2016 | 214978 | 17277 | 34 | 39245 | 39230 | 0 | 15580 | 199398 | 0 | 0 | 0 | 18.0 | 32.0 | 49.0 | 75.0 | 253 | 123220 | 110955 | 0.08036636306970946 | 0.00015815571825954285 | 0.1825535636204635 | 0.5731749295276726 | 0.5161225799849287 | 0.07247253207304934 | 0.1824837890388784 |
| 2017 | 259758 | 20434 | 276 | 39574 | 39554 | 0 | 20781 | 238975 | 0 | 0 | 0 | 17.0 | 31.0 | 49.0 | 75.0 | 243 | 142026 | 127967 | 0.07866552714449603 | 0.0010625274293765735 | 0.15234949452952362 | 0.5467627561037581 | 0.4926393027356232 | 0.08000138590534267 | 0.15227249978826446 |
| 2018 | 289534 | 20778 | 130 | 46623 | 46603 | 0 | 30949 | 257633 | 0 | 0 | 0 | 18.0 | 32.0 | 49.0 | 77.0 | 255 | 153840 | 138070 | 0.07176359253144708 | 0.000448997354369435 | 0.1610277204058936 | 0.5313365615091837 | 0.4768697285983684 | 0.10689245477215112 | 0.16095864388983677 |
| 2019 | 290475 | 23223 | 95 | 42944 | 42923 | 0 | 4203 | 47806 | 0 | 0 | 0 | 18.0 | 32.0 | 50.0 | 77.0 | 255 | 162159 | 144992 | 0.07994836044410018 | 0.0003270505206988553 | 0.14784060590412257 | 0.5582545830105861 | 0.49915483260177296 | 0.014469403563129358 | 0.1477683105258628 |
| 2020 | 293391 | 21041 | 35 | 52578 | 52564 | 0 | 3139 | 28765 | 0 | 0 | 0 | 20.0 | 32.0 | 50.0 | 77.0 | 255 | 168025 | 150877 | 0.07171658298993493 | 0.0001192947295588481 | 0.17920795116414615 | 0.5726999124035843 | 0.5142523117614378 | 0.010699033031006404 | 0.1791602332723226 |
| 2021 | 317978 | 19404 | 25 | 59754 | 59721 | 0 | 3787 | 27330 | 12440 | 0 | 0 | 19.0 | 31.0 | 49.0 | 75.0 | 112 | 185835 | 166826 | 0.06102308964771148 | 7.862179144469115e-05 | 0.187918661039443 | 0.5844272245249671 | 0.5246463591820818 | 0.011909628968041814 | 0.187814880274736 |
| 2022 | 346799 | 26419 | 26 | 74820 | 72905 | 0 | 5136 | 31498 | 17987 | 0 | 0 | 20.0 | 32.0 | 50.0 | 76.0 | 250 | 195442 | 176018 | 0.07617957375886321 | 7.497138111701591e-05 | 0.215744566737505 | 0.5635598718566086 | 0.507550483132881 | 0.014809731285268989 | 0.21022263616677095 |
| 2023 | 394234 | 25640 | 57 | 85434 | 72398 | 2297 | 6670 | 34425 | 27708 | 0 | 0 | 20.0 | 32.0 | 50.0 | 76.0 | 234 | 222941 | 200097 | 0.0650375157901145 | 0.00014458418096866327 | 0.21670885819082067 | 0.5655042436725397 | 0.5075589624436249 | 0.016918885737912 | 0.1847184624059479 |
| 2024 | 398620 | 26796 | 12 | 89198 | 84392 | 203 | 8069 | 35314 | 13982 | 0 | 0 | 21.0 | 32.0 | 48.0 | 74.0 | 188 | 232769 | 210672 | 0.06722191560885053 | 3.010385831117355e-05 | 0.2237669961366715 | 0.5839370829361297 | 0.5285033365109628 | 0.020242336059404946 | 0.21181827080671758 |
| 2025 | 400288 | 27241 | 27 | 83024 | 77256 | 170 | 8094 | 38026 | 26 | 0 | 0 | 22.0 | 33.0 | 49.0 | 75.0 | 250 | 235372 | 213142 | 0.06805350147893517 | 6.745143496682389e-05 | 0.2074106643216884 | 0.5880066352226397 | 0.532471620433288 | 0.02022044128227676 | 0.1930830405030516 |

## Quality

| year_filing_for | n_company_empty | n_ein_unusable | n_zip_unusable | n_distinct_record_ids | n_distinct_establishment_ids | n_rows | n_distinct_rows | n_exact_duplicate_excess |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2016 | 15580 | 214978 | 172 | 214978 | 214977 | 214978 | 214978 | 0 |
| 2017 | 20781 | 259756 | 172 | 259758 | 259757 | 259758 | 259758 | 0 |
| 2018 | 30963 | 288582 | 228 | 289534 | 286884 | 289534 | 289534 | 0 |
| 2019 | 31491 | 52009 | 145 | 290475 | 290475 | 290475 | 290475 | 0 |
| 2020 | 29040 | 31904 | 396 | 293391 | 293385 | 293391 | 293391 | 0 |
| 2021 | 17076 | 31117 | 2100 | 315937 | 315936 | 317978 | 316751 | 1227 |
| 2022 | 15494 | 36634 | 2107 | 346799 | 346799 | 346799 | 346799 | 0 |
| 2023 | 19346 | 41095 | 14418 | 394234 | 394231 | 394234 | 394234 | 0 |
| 2024 | 19538 | 43383 | 1650 | 398620 | 398620 | 398620 | 398620 | 0 |
| 2025 | 19859 | 46120 | 0 | 400288 | 400288 | 400288 | 400288 | 0 |

## V2

| base_year | later_year | n_cohort_ids | n_raw_reappeared | n_unique_cohort_ids | n_reappeared | n_same_ein_address | n_same_ein_address_including_padded | n_same_raw_ein_address | n_reappeared_ein_unknown | n_reappeared_ein_conflict | n_reappeared_address_conflict | n_base_missing_id_rows | n_later_missing_id_rows | n_unique_address_matches | n_address_matches_different_id | share_raw_reappeared | share_same_ein_address | share_address_matches_different_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2016 | 2017 | 214977 | 129292 | 214976 | 129291 | 0 | 0 | 0 | 129291 | 0 | 3965 | 0 | 0 | 0 | 0 | 0.601422477753434 | 0.0 | None |
| 2017 | 2018 | 259757 | 159932 | 259756 | 157531 | 2 | 2 | 2 | 157529 | 0 | 8003 | 0 | 0 | 2 | 0 | 0.6156985182305 | 7.699503766982218e-06 | 0.0 |
| 2018 | 2019 | 286884 | 177598 | 284234 | 177112 | 635 | 635 | 635 | 176445 | 16 | 11583 | 0 | 0 | 634 | 0 | 0.6190585741972365 | 0.0022134381840743993 | 0.0 |
| 2019 | 2020 | 290475 | 184014 | 290475 | 184008 | 140056 | 140056 | 140056 | 34106 | 2022 | 8875 | 0 | 0 | 143794 | 6080 | 0.6334934159566228 | 0.48216197607367245 | 0.042282709987899354 |
| 2020 | 2021 | 293385 | 185386 | 293379 | 185179 | 132404 | 139236 | 132404 | 21031 | 4320 | 22348 | 0 | 0 | 132285 | 6236 | 0.6318864290948754 | 0.45129778277689725 | 0.047140643308009225 |
| 2021 | 2022 | 315936 | 183055 | 315121 | 182686 | 132532 | 139072 | 139072 | 17599 | 6837 | 21483 | 0 | 0 | 136339 | 10046 | 0.5794053225969816 | 0.4194900232958574 | 0.07368397890552227 |
| 2022 | 2023 | 346799 | 197342 | 346799 | 197342 | 146502 | 153998 | 153998 | 22745 | 4365 | 12762 | 0 | 0 | 150608 | 9092 | 0.5690385497074675 | 0.42244066447711787 | 0.06036863911611601 |
| 2023 | 2024 | 394231 | 219860 | 394228 | 219860 | 160579 | 168226 | 168226 | 23866 | 9579 | 20138 | 0 | 0 | 171544 | 14532 | 0.5576933320819519 | 0.40732210303096406 | 0.08471295994030686 |
| 2023 | 2025 | 394231 | 180123 | 394228 | 180123 | 133770 | 140354 | 133795 | 19211 | 3300 | 20330 | 0 | 0 | 141997 | 13056 | 0.4568970984016985 | 0.33931882576458977 | 0.09194560448460179 |
| 2024 | 2025 | 398620 | 230099 | 398620 | 230099 | 184358 | 192250 | 184378 | 24998 | 2964 | 11601 | 0 | 0 | 195188 | 14551 | 0.5772389744618935 | 0.46249059254427777 | 0.07454864028526344 |

## V3 sample totals

| n_ct_incomparable | n_geocode_exact | n_geocode_legacy_ct | n_geocode_no_match | n_geocode_non_exact | n_geocode_out_of_scope | n_geocode_tie | n_joint_dominant_agree | n_joint_dominant_comparable | n_joint_single_agree | n_joint_single_comparable | n_out_of_scope | n_population | n_proposed_assignable | n_sample | n_zip_covered | n_zip_dominant_out_of_scope | n_zip_single_compatible | n_zip_single_out_of_scope | share_ct_incomparable | share_geocode_exact | share_geocode_legacy_ct | share_geocode_no_match | share_geocode_non_exact | share_geocode_out_of_scope | share_geocode_tie | share_joint_dominant_agree | share_joint_dominant_comparable | share_joint_single_agree | share_joint_single_comparable | share_out_of_scope | share_proposed_assignable | share_zip_covered | share_zip_dominant_out_of_scope | share_zip_single_compatible | share_zip_single_out_of_scope | weighted_n_ct_incomparable | weighted_n_geocode_exact | weighted_n_geocode_legacy_ct | weighted_n_geocode_no_match | weighted_n_geocode_non_exact | weighted_n_geocode_out_of_scope | weighted_n_geocode_tie | weighted_n_joint_dominant_agree | weighted_n_joint_dominant_comparable | weighted_n_joint_single_agree | weighted_n_joint_single_comparable | weighted_n_out_of_scope | weighted_n_proposed_assignable | weighted_n_zip_covered | weighted_n_zip_dominant_out_of_scope | weighted_n_zip_single_compatible | weighted_n_zip_single_out_of_scope | weighted_share_ct_incomparable | weighted_share_geocode_exact | weighted_share_geocode_legacy_ct | weighted_share_geocode_no_match | weighted_share_geocode_non_exact | weighted_share_geocode_out_of_scope | weighted_share_geocode_tie | weighted_share_joint_dominant_agree | weighted_share_joint_dominant_comparable | weighted_share_joint_single_agree | weighted_share_joint_single_comparable | weighted_share_out_of_scope | weighted_share_proposed_assignable | weighted_share_zip_covered | weighted_share_zip_dominant_out_of_scope | weighted_share_zip_single_compatible | weighted_share_zip_single_out_of_scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 9703 | 0 | 4718 | 5994 | 75 | 213 | 8579 | 8835 | 4717 | 4718 | 719 | 3204828.0 | 12611 | 20628 | 14529 | 423 | 7990 | 323 | 0.0 | 0.47038006592980414 | 0.0 | 0.22871824704285437 | 0.2905759162303665 | 0.0036358347876672484 | 0.010325770796974986 | 0.9710243350311262 | 0.4283013379872019 | 0.9997880457821111 | 0.22871824704285437 | 0.034855536164436686 | 0.6113535000969555 | 0.7043339150668994 | 0.02050610820244328 | 0.3873375993794842 | 0.015658328485553617 | 0.0 | 2064165.5 | 0.0 | 441561.75 | 675039.875 | 1555.75 | 24060.875 | 2013745.25 | 2049904.25 | 1595203.125 | 1595212.625 | 14883.0 | 2919075.75 | 3162040.0 | 9991.125 | 2456027.0 | 5390.125 | 0.0 | 0.6440799631056643 | 0.0 | 0.13778017104194049 | 0.21063216965153825 | 0.0004854394682023497 | 0.007507696200856957 | 0.9823606395274316 | 0.6396300363077208 | 0.9999940446810343 | 0.4977529605332954 | 0.004643930969150295 | 0.9108369466317693 | 0.986648893481959 | 0.0031175229996742416 | 0.7663522036127992 | 0.0016818765312834262 |

## Interpretation

Counts retain their denominators. V1 flags overlap. V2 confirms only unique-ID links with a known matching EIN and address. V3 coverage differs from assignment and conditional agreement. Weighted V3 summaries estimate the distinct-row sampling population; they are not unweighted sample percentages or accuracy estimates.

## Scope, denominators and interpretation

Status: **ADOPTED — owner approved A1–A4 on 2026-10-13.** The cleaning, linkage and county rules below are adopted; the sample remains verification evidence rather than full-table target construction. Measurements use all ten delivered 2016–2025 ITA summary files. ITA is a program-selected filing population, not all establishments. The 2025 summary carries the source-file submission through-date 2026-08-31. No targets, county hierarchy or training pairs are built here.

V1 uses original source rows per filing year. Original length counts Unicode characters and treats null as zero, while flags compare NFKC/casefold/trimmed collapsed-whitespace keys without changing original strings or punctuation. Empty and finite exact-placeholder flags are separate; copied-any compares exact normalized identity against official NAICS titles at levels 2–6 in 2012/2017/2022. Native identity divides by rows with known vintage; unknown vintage never guesses a title vintage. Flags may overlap. Repetition rows are every row in employer/description groups of size > 1; excess is sum(size − 1) in nonempty-description/known-employer groups. Their shares divide by all source rows; they differ from exact duplicate row excess. Unknown employers never share a blank employer group. Company fallback and padded eight-digit EIN sensitivity are separate columns.

V2 raw reappearance divides by all distinct nonnull cohort establishment IDs, including IDs with conflicting rows. Confirmed links use eligible unique IDs after exact duplicate collapse, same usable unreconstructed EIN, and identical complete normalized full address; reported confirmation share uses the all-ID cohort denominator. The extra eligible denominator `n_unique_cohort_ids` excludes conflicting IDs. `n_reappeared` records candidate overlap among eligible unique IDs, not confirmed establishment identity. Reappeared unknown EIN and conflicts are diagnostics; missing EIN is unknown evidence. Address mismatch can reflect relocation, correction or changed formatting and does not prove a different establishment. Raw-EIN equality and reconstructed/padded sensitivity are separate from unreconstructed normalized-EIN confirmation. Changed-ID shares divide by uniquely matched usable unreconstructed EIN/name/full-address tuples in both years, with tuple multiplicity evaluated on all exact-distinct yearly rows before eligible-ID filtering. Original missing-ID row counts are reported and absent IDs cannot confirm links.

V3 population is the exact-distinct source-row table, including flagged/territory rows; sample stratifies by delivered filing year/state, ZIP format, and count of positive-BUS county candidates. Missing state has an explicit label; territory exclusion checks normalized delivered state and method-specific returned county prefixes separately. Deterministic hash rank uses the recorded descriptive salt; each stratum selects at most 8 rows, inclusion probability sample_n/population_n, weight population_n/sample_n. Every sample request receives exactly one validated response ID. All-sample raw shares use 20,628 rows. Weighted coverage divides weighted flag counts by 3,204,828 population rows. Conditional agreement divides agreeing exact-geocode/jointly-compatible rows by the corresponding joint comparable rows, with separately weighted numerators and denominators. Within a stratum all weights are equal, so its raw and weighted proportions coincide. Neither raw nor weighted county agreement estimates accuracy.

ZIP coverage means at least one positive business-share candidate, not a unique county. Single fallback requires exactly one positive candidate and compatible county geography. Dominant fallback is diagnostic only, never a headline assignment; tied maxima lack a dominant candidate. Raw HUD presence distinguishes unmapped ZIP from mapped zero-positive-BUS. Geography is the common ACS2025 frame even for older addresses, not their historical county boundaries. Old Connecticut county differences are geography-vintage incompatibility, not ordinary method errors; planning regions are required under R6.2. Scope excludes Puerto Rico/island areas under R6.4, including returned counties when delivered state is missing or conflicting. County coverage and raw match status remain diagnostic coverage, before scope assignment gates.

## Extra aggregate diagnostics

Conflicting key counts below use exact-distinct source rows, grouped by (year, key), retain only multiplicity > 1. `n_rows` counts every conflicting row, `n_excess` rows beyond one per key. Absent years have zero conflicting keys. Source IDs have no nulls in any year. 2021 record-ID and establishment-ID collisions are both retained.

### Conflicting establishment_id

| n_conflicting_keys | n_excess | n_rows | year_filing_for |
| --- | --- | --- | --- |
| 1 | 1 | 2 | 2016 |
| 1 | 1 | 2 | 2017 |
| 2650 | 2650 | 5300 | 2018 |
| 6 | 6 | 12 | 2020 |
| 815 | 815 | 1630 | 2021 |
| 3 | 3 | 6 | 2023 |

### Conflicting id

| n_conflicting_keys | n_excess | n_rows | year_filing_for |
| --- | --- | --- | --- |
| 814 | 814 | 1628 | 2021 |

### V1 after exact duplicate collapse (diagnostic)

| length_max | length_min | length_p25 | length_p50 | length_p75 | length_p95 | n_copied_any | n_ein_padded | n_employer_company | n_employer_unknown | n_empty | n_mojibake | n_native_title_match | n_placeholder | n_repeat_excess | n_repeat_rows | n_rows | n_vintage_unknown | share_copied_any | share_employer_unknown | share_empty | share_native_title_match | share_placeholder | share_repeat_excess | share_repeat_rows | year_filing_for |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 253 | 0 | 18.0 | 32.0 | 49.0 | 75.0 | 39245 | 0 | 199398 | 15580 | 17277 | 0 | 39230 | 34 | 110955 | 123220 | 214978 | 0 | 0.1825535636204635 | 0.07247253207304934 | 0.08036636306970946 | 0.1824837890388784 | 0.00015815571825954285 | 0.5161225799849287 | 0.5731749295276726 | 2016 |
| 243 | 0 | 17.0 | 31.0 | 49.0 | 75.0 | 39574 | 0 | 238975 | 20781 | 20434 | 0 | 39554 | 276 | 127967 | 142026 | 259758 | 0 | 0.15234949452952362 | 0.08000138590534267 | 0.07866552714449603 | 0.15227249978826446 | 0.0010625274293765735 | 0.4926393027356232 | 0.5467627561037581 | 2017 |
| 255 | 0 | 18.0 | 32.0 | 49.0 | 77.0 | 46623 | 0 | 257633 | 30949 | 20778 | 0 | 46603 | 130 | 138070 | 153840 | 289534 | 0 | 0.1610277204058936 | 0.10689245477215112 | 0.07176359253144708 | 0.16095864388983677 | 0.000448997354369435 | 0.4768697285983684 | 0.5313365615091837 | 2018 |
| 255 | 0 | 18.0 | 32.0 | 50.0 | 77.0 | 42944 | 0 | 47806 | 4203 | 23223 | 0 | 42923 | 95 | 144992 | 162159 | 290475 | 0 | 0.14784060590412257 | 0.014469403563129358 | 0.07994836044410018 | 0.1477683105258628 | 0.0003270505206988553 | 0.49915483260177296 | 0.5582545830105861 | 2019 |
| 255 | 0 | 20.0 | 32.0 | 50.0 | 77.0 | 52578 | 0 | 28765 | 3139 | 21041 | 0 | 52564 | 35 | 150877 | 168025 | 293391 | 0 | 0.17920795116414615 | 0.010699033031006404 | 0.07171658298993493 | 0.1791602332723226 | 0.0001192947295588481 | 0.5142523117614378 | 0.5726999124035843 | 2020 |
| 112 | 0 | 19.0 | 31.0 | 49.0 | 75.0 | 59563 | 12400 | 27210 | 3745 | 19365 | 0 | 59530 | 25 | 165675 | 183856 | 316751 | 0 | 0.18804360522934419 | 0.011823167093395127 | 0.06113635000363061 | 0.18793942244854792 | 7.892634908808496e-05 | 0.523044915406739 | 0.580443313517558 | 2021 |
| 250 | 0 | 20.0 | 32.0 | 50.0 | 76.0 | 74820 | 17987 | 31498 | 5136 | 26419 | 0 | 72905 | 26 | 176018 | 195442 | 346799 | 0 | 0.215744566737505 | 0.014809731285268989 | 0.07617957375886321 | 0.21022263616677095 | 7.497138111701591e-05 | 0.507550483132881 | 0.5635598718566086 | 2022 |
| 234 | 0 | 20.0 | 32.0 | 50.0 | 76.0 | 85434 | 27708 | 34425 | 6670 | 25640 | 0 | 72398 | 57 | 200097 | 222941 | 394234 | 2297 | 0.21670885819082067 | 0.016918885737912 | 0.0650375157901145 | 0.1847184624059479 | 0.00014458418096866327 | 0.5075589624436249 | 0.5655042436725397 | 2023 |
| 188 | 0 | 21.0 | 32.0 | 48.0 | 74.0 | 89198 | 13982 | 35314 | 8069 | 26796 | 0 | 84392 | 12 | 210672 | 232769 | 398620 | 203 | 0.2237669961366715 | 0.020242336059404946 | 0.06722191560885053 | 0.21181827080671758 | 3.010385831117355e-05 | 0.5285033365109628 | 0.5839370829361297 | 2024 |
| 250 | 0 | 22.0 | 33.0 | 49.0 | 75.0 | 83024 | 26 | 38026 | 8094 | 27241 | 0 | 77256 | 27 | 213142 | 235372 | 400288 | 170 | 0.2074106643216884 | 0.02022044128227676 | 0.06805350147893517 | 0.1930830405030516 | 6.745143496682389e-05 | 0.532471620433288 | 0.5880066352226397 | 2025 |

### Positive-BUS ZIP candidate classes

| county_count_class | n_sample | weighted_rows |
| --- | --- | --- |
| multiple | 6539 | 706013.0 |
| none | 6099 | 42788.0 |
| single | 7990 | 2456027.0 |

### Tied largest-share ZIP candidates

| n_sample | weighted_rows |
| --- | --- |
| 4 | 574.75 |

### Raw Census response status/type totals

| geocode_status | match_type | n_sample | weighted_rows |
| --- | --- | --- | --- |
| Match | Exact | 9703 | 2064165.5 |
| Match | Non_Exact | 5994 | 675039.875 |
| No_Match | None | 4718 | 441561.75 |
| Tie | None | 213 | 24060.875 |

### Source flags on original rows

| flag_below_filing_size | flag_employment | flag_hours_per_employee | flag_naics_year_unknown | n_rows | year_filing_for |
| --- | --- | --- | --- | --- | --- |
| 35459 | 1315 | 7290 | 0 | 214978 | 2016 |
| 41399 | 448 | 9393 | 0 | 259758 | 2017 |
| 44226 | 650 | 10403 | 0 | 289534 | 2018 |
| 40482 | 592 | 10740 | 0 | 290475 | 2019 |
| 50449 | 1112 | 11112 | 0 | 293391 | 2020 |
| 47472 | 1199 | 22819 | 0 | 317978 | 2021 |
| 60471 | 1250 | 13152 | 0 | 346799 | 2022 |
| 83403 | 2121 | 17852 | 2297 | 394234 | 2023 |
| 86627 | 1635 | 28719 | 203 | 398620 | 2024 |
| 103814 | 4517 | 16795 | 170 | 400288 | 2025 |

### Source flags after exact duplicate collapse

| flag_below_filing_size | flag_employment | flag_hours_per_employee | flag_naics_year_unknown | n_rows | year_filing_for |
| --- | --- | --- | --- | --- | --- |
| 35459 | 1315 | 7290 | 0 | 214978 | 2016 |
| 41399 | 448 | 9393 | 0 | 259758 | 2017 |
| 44226 | 650 | 10403 | 0 | 289534 | 2018 |
| 40482 | 592 | 10740 | 0 | 290475 | 2019 |
| 50449 | 1112 | 11112 | 0 | 293391 | 2020 |
| 47396 | 1199 | 22752 | 0 | 316751 | 2021 |
| 60471 | 1250 | 13152 | 0 | 346799 | 2022 |
| 83403 | 2121 | 17852 | 2297 | 394234 | 2023 |
| 86627 | 1635 | 28719 | 203 | 398620 | 2024 |
| 103814 | 4517 | 16795 | 170 | 400288 | 2025 |

### ZIP formats by original source year

| len | year_filing_for | zip_format |
| --- | --- | --- |
| 206376 | 2016 | five_digit |
| 172 | 2016 | invalid |
| 302 | 2016 | padded_four_digit |
| 8128 | 2016 | zip_plus_four |
| 242662 | 2017 | five_digit |
| 172 | 2017 | invalid |
| 43 | 2017 | padded_four_digit |
| 16881 | 2017 | zip_plus_four |
| 272567 | 2018 | five_digit |
| 228 | 2018 | invalid |
| 40 | 2018 | padded_four_digit |
| 16699 | 2018 | zip_plus_four |
| 270884 | 2019 | five_digit |
| 144 | 2019 | invalid |
| 1 | 2019 | missing |
| 52 | 2019 | padded_four_digit |
| 19394 | 2019 | zip_plus_four |
| 284601 | 2020 | five_digit |
| 396 | 2020 | invalid |
| 84 | 2020 | padded_four_digit |
| 8310 | 2020 | zip_plus_four |
| 277020 | 2021 | five_digit |
| 2100 | 2021 | invalid |
| 21388 | 2021 | padded_four_digit |
| 17470 | 2021 | zip_plus_four |
| 310922 | 2022 | five_digit |
| 2107 | 2022 | invalid |
| 23656 | 2022 | padded_four_digit |
| 10114 | 2022 | zip_plus_four |
| 379816 | 2023 | five_digit |
| 14418 | 2023 | invalid |
| 368738 | 2024 | five_digit |
| 1650 | 2024 | invalid |
| 28232 | 2024 | padded_four_digit |
| 400288 | 2025 | five_digit |

### Frequent residual descriptions

| description_key | len |
| --- | --- |
| mail and parcel delivery | 77701 |
| office equipment | 40252 |
| skilled nursing facilities | 36506 |
| hotels (except casino hotels) | 25509 |
| nursing homes | 24482 |
| assisted-living facilities without on-site nursing care facilities | 24192 |
| retail | 21982 |
| homecenter | 19093 |
| supermarkets and other grocery except convenience stores | 17968 |
| service to buildings and dwellings | 13232 |
| dollar stores | 12276 |
| distribution of electric power | 12063 |
| assisted-living facilities with on-site nursing facilities | 11808 |
| retail other | 11736 |
| hospitals, general medical and surgical | 11668 |
| supermarkets | 11552 |
| automobile dealers, new only or new and used | 10530 |
| commercial building construction general contractors | 10436 |
| electrical contractors | 9888 |
| group homes, intellectual and developmental disability | 9843 |
| sc and warehouse | 8304 |
| general freight trucking, long-distance, truckload (tl) | 7893 |
| retail store | 7869 |
| low voltage electrical work | 7579 |
| supermrkts & other grocery stores | 7333 |
| building materials supply dealers | 7203 |
| ready-mix concrete manufacturing and distributing | 7175 |
| heating, ventilation and air-conditioning (hvac) contractors | 6619 |
| retail grocery not including convenience stores | 6593 |
| pavement, highway, road, street, bridge or airport runway, construction | 6552 |

### EIN status by source year

| ein_category | len | year_filing_for |
| --- | --- | --- |
| missing | 214978 | 2016 |
| missing | 259756 | 2017 |
| unreconstructed_usable | 2 | 2017 |
| missing | 287579 | 2018 |
| other_invalid | 1003 | 2018 |
| unreconstructed_usable | 952 | 2018 |
| missing | 52009 | 2019 |
| unreconstructed_usable | 238466 | 2019 |
| missing | 31901 | 2020 |
| repeated_digit_invalid | 3 | 2020 |
| unreconstructed_usable | 261487 | 2020 |
| missing | 31042 | 2021 |
| other_invalid | 71 | 2021 |
| padded_usable | 12440 | 2021 |
| repeated_digit_invalid | 4 | 2021 |
| unreconstructed_usable | 274421 | 2021 |
| missing | 36459 | 2022 |
| other_invalid | 170 | 2022 |
| padded_usable | 17987 | 2022 |
| repeated_digit_invalid | 5 | 2022 |
| unreconstructed_usable | 292178 | 2022 |
| missing | 40543 | 2023 |
| other_invalid | 549 | 2023 |
| padded_usable | 27708 | 2023 |
| repeated_digit_invalid | 3 | 2023 |
| unreconstructed_usable | 325431 | 2023 |
| missing | 43260 | 2024 |
| other_invalid | 101 | 2024 |
| padded_usable | 13982 | 2024 |
| repeated_digit_invalid | 22 | 2024 |
| unreconstructed_usable | 341255 | 2024 |
| missing | 46062 | 2025 |
| other_invalid | 54 | 2025 |
| padded_usable | 26 | 2025 |
| repeated_digit_invalid | 4 | 2025 |
| unreconstructed_usable | 354142 | 2025 |

### Invalid EIN frequency aggregates

| ein_category | max_frequency | n_distinct_delivered_values | n_rows |
| --- | --- | --- | --- |
| missing | 1043589 | 1 | 1043589 |
| repeated_digit_invalid | 39 | 3 | 41 |
| other_invalid | 1003 | 161 | 1948 |

### Largest usable EIN frequency bins

| len | n_ein_keys |
| --- | --- |
| 33890 | 1 |
| 27985 | 1 |
| 20101 | 1 |
| 19615 | 1 |
| 18512 | 1 |
| 15733 | 1 |
| 14330 | 1 |
| 14112 | 1 |
| 12115 | 1 |
| 11285 | 1 |
| 11066 | 1 |
| 10209 | 1 |
| 9526 | 1 |
| 9493 | 1 |
| 9487 | 1 |
| 9245 | 1 |
| 8531 | 1 |
| 8032 | 1 |
| 7599 | 1 |
| 7121 | 1 |
| 6873 | 1 |
| 6538 | 1 |
| 5897 | 1 |
| 5630 | 1 |
| 5535 | 1 |
| 5380 | 1 |
| 5305 | 1 |
| 5032 | 1 |
| 4970 | 1 |
| 4888 | 1 |

### Sample ZIP availability from raw HUD join

| n_sample | weighted_rows | zip_availability |
| --- | --- | --- |
| 1878 | 9157.125 | mapped_zero_positive_bus |
| 14529 | 3162040.0 | positive_bus |
| 4221 | 33630.875 | unmapped_zip |

Generic valid residuals such as retail, nursing homes and mail and parcel delivery remain text; frequency or coarse detail is not evidence that they are junk. Residuals are nonempty, nonplaceholder, and not exact normalized official title identity; punctuation differences and near-title wording deliberately remain residual. EIN frequency tables contain no EIN values; usability checks are syntactic plausibility only and do not validate IRS ownership. Repeated-digit invalid and other invalid values cannot confirm links.

## Every V3 stratum

Each row retains its population_n and n_sample. Every method coverage/status/scope count uses n_sample for its within-stratum rate; agreement counts divide by their corresponding joint comparable count, undefined at zero. Multiply any count by population_n/n_sample for its weighted count. This supplies both raw and weighted evidence for every stratum without treating disproportionate sampling shares as population rates.


### Compact V3 coverage and agreement summary

| metric | raw_n | raw_denominator | raw_share | weighted_n | weighted_denominator | weighted_share |
| --- | --- | --- | --- | --- | --- | --- |
| Compatible exact geocode | 9703 | 20628 | 0.47038006592980414 | 2064165.5 | 3204828.0 | 0.6440799631056643 |
| Positive-BUS ZIP coverage | 14529 | 20628 | 0.7043339150668994 | 3162040.0 | 3204828.0 | 0.986648893481959 |
| Compatible single ZIP county | 7990 | 20628 | 0.3873375993794842 | 2456027.0 | 3204828.0 | 0.7663522036127992 |
| Proposed assignable | 12611 | 20628 | 0.6113535000969555 | 2919075.75 | 3204828.0 | 0.9108369466317693 |
| Single-county agreement | 4717 | 4718 | 0.9997880457821111 | 1595203.125 | 1595212.625 | 0.9999940446810343 |
| Dominant-county agreement (diagnostic) | 8579 | 8835 | 0.9710243350311262 | 2013745.25 | 2049904.25 | 0.9823606395274316 |

| n_ct_incomparable | n_geocode_exact | n_geocode_legacy_ct | n_geocode_no_match | n_geocode_non_exact | n_geocode_out_of_scope | n_geocode_tie | n_joint_dominant_agree | n_joint_dominant_comparable | n_joint_single_agree | n_joint_single_comparable | n_out_of_scope | n_proposed_assignable | n_sample | n_zip_covered | n_zip_dominant_out_of_scope | n_zip_single_compatible | n_zip_single_out_of_scope | population_n | stratum |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|AA\|five_digit\|none |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2016\|AA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|AA\|invalid\|none |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2016\|AE\|padded_four_digit\|none |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 2016\|AK\|five_digit\|multiple |
| 0 | 0 | 0 | 7 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 37 | 2016\|AK\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 658 | 2016\|AK\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|AK\|invalid\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 10 | 2016\|AK\|zip_plus_four\|single |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1051 | 2016\|AL\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 26 | 2016\|AL\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2494 | 2016\|AL\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|AL\|invalid\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 2 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 25 | 2016\|AL\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 99 | 2016\|AL\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 742 | 2016\|AR\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 29 | 2016\|AR\|five_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1373 | 2016\|AR\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|AR\|invalid\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 17 | 2016\|AR\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|AR\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 42 | 2016\|AR\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|AS\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 100 | 2016\|AZ\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 60 | 2016\|AZ\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4081 | 2016\|AZ\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|AZ\|invalid\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 2 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 9 | 2016\|AZ\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|AZ\|zip_plus_four\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 214 | 2016\|AZ\|zip_plus_four\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 588 | 2016\|CA\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 43 | 2016\|CA\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6674 | 2016\|CA\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2016\|CA\|invalid\|none |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2016\|CA\|padded_four_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 40 | 2016\|CA\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|CA\|zip_plus_four\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 632 | 2016\|CA\|zip_plus_four\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 5 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 1906 | 2016\|CO\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 28 | 2016\|CO\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2507 | 2016\|CO\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|CO\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2016\|CO\|padded_four_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 41 | 2016\|CO\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 64 | 2016\|CO\|zip_plus_four\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 147 | 2016\|CT\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 6 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 22 | 2016\|CT\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3395 | 2016\|CT\|five_digit\|single |
| 0 | 4 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 8 | 0 | 0 | 0 | 0 | 20 | 2016\|CT\|invalid\|none |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2016\|CT\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 76 | 2016\|CT\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2016\|Ca\|five_digit\|single |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2016\|DC\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 377 | 2016\|DC\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|DC\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|DC\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2016\|DC\|padded_four_digit\|single |
| 0 | 2 | 0 | 6 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 18 | 2016\|DC\|zip_plus_four\|single |
| 0 | 5 | 0 | 2 | 0 | 0 | 1 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 39 | 2016\|DE\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 6 | 2016\|DE\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 618 | 2016\|DE\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|DE\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2016\|DE\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|DE\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 14 | 2016\|DE\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 21 | 2016\|DE\|zip_plus_four\|single |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 1068 | 2016\|FL\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 70 | 2016\|FL\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 10752 | 2016\|FL\|five_digit\|single |
| 0 | 0 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2016\|FL\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|FL\|padded_four_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 107 | 2016\|FL\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 4 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 7 | 2016\|FL\|zip_plus_four\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 879 | 2016\|FL\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2016\|Fl\|five_digit\|multiple |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 11 | 2016\|Fl\|five_digit\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 2933 | 2016\|GA\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 36 | 2016\|GA\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4036 | 2016\|GA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|GA\|invalid\|none |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2016\|GA\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2016\|GA\|padded_four_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 137 | 2016\|GA\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 174 | 2016\|GA\|zip_plus_four\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2016\|GU\|five_digit\|none |
| 0 | 0 | 0 | 3 | 5 | 4 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 7 | 8 | 7 | 12 | 2016\|GU\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 2016\|GU\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2016\|Ga\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2016\|Ga\|five_digit\|single |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 8 | 2016\|HI\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 963 | 2016\|HI\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|HI\|invalid\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 35 | 2016\|HI\|zip_plus_four\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1128 | 2016\|IA\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 18 | 2016\|IA\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2711 | 2016\|IA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|IA\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2016\|IA\|padded_four_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 36 | 2016\|IA\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 71 | 2016\|IA\|zip_plus_four\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 358 | 2016\|ID\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 9 | 2016\|ID\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 865 | 2016\|ID\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|ID\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 14 | 2016\|ID\|zip_plus_four\|multiple |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 40 | 2016\|ID\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2112 | 2016\|IL\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 34 | 2016\|IL\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 7379 | 2016\|IL\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|IL\|invalid\|none |
| 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 17 | 2016\|IL\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|IL\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 145 | 2016\|IL\|padded_four_digit\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 46 | 2016\|IL\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 297 | 2016\|IL\|zip_plus_four\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1690 | 2016\|IN\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 49 | 2016\|IN\|five_digit\|none |
| 0 | 3 | 0 | 0 | 4 | 0 | 1 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4212 | 2016\|IN\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|IN\|invalid\|none |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2016\|IN\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 34 | 2016\|IN\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 140 | 2016\|IN\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2016\|Il\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2016\|In\|five_digit\|multiple |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 526 | 2016\|KS\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 14 | 2016\|KS\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2145 | 2016\|KS\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|KS\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 9 | 2016\|KS\|zip_plus_four\|multiple |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 50 | 2016\|KS\|zip_plus_four\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1398 | 2016\|KY\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 35 | 2016\|KY\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2209 | 2016\|KY\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|KY\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2016\|KY\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 36 | 2016\|KY\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 54 | 2016\|KY\|zip_plus_four\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 632 | 2016\|LA\|five_digit\|multiple |
| 0 | 0 | 0 | 7 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 42 | 2016\|LA\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2500 | 2016\|LA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|LA\|invalid\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 9 | 2016\|LA\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 82 | 2016\|LA\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 23 | 2016\|La\|five_digit\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 15 | 2016\|La\|five_digit\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 374 | 2016\|MA\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 42 | 2016\|MA\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3778 | 2016\|MA\|five_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 8 | 0 | 0 | 0 | 0 | 37 | 2016\|MA\|invalid\|none |
| 0 | 7 | 0 | 0 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 7 | 7 | 0 | 0 | 0 | 7 | 2016\|MA\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 110 | 2016\|MA\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 415 | 2016\|MD\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 9 | 2016\|MD\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1511 | 2016\|MD\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|MD\|invalid\|none |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2016\|MD\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 6 | 6 | 0 | 6 | 0 | 6 | 2016\|MD\|padded_four_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 20 | 2016\|MD\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 83 | 2016\|MD\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 9 | 2016\|ME\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2016\|ME\|five_digit\|none |
| 0 | 5 | 0 | 0 | 2 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1052 | 2016\|ME\|five_digit\|single |
| 0 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 3 | 2016\|ME\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 17 | 2016\|ME\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1623 | 2016\|MI\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 40 | 2016\|MI\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5743 | 2016\|MI\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|MI\|invalid\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 42 | 2016\|MI\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 143 | 2016\|MI\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 623 | 2016\|MN\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2016\|MN\|five_digit\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1671 | 2016\|MN\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|MN\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 31 | 2016\|MN\|zip_plus_four\|multiple |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 61 | 2016\|MN\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1403 | 2016\|MO\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 38 | 2016\|MO\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3717 | 2016\|MO\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|MO\|invalid\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 33 | 2016\|MO\|zip_plus_four\|multiple |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 110 | 2016\|MO\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 828 | 2016\|MS\|five_digit\|multiple |
| 0 | 0 | 0 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 23 | 2016\|MS\|five_digit\|none |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1126 | 2016\|MS\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|MS\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 28 | 2016\|MS\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|MS\|zip_plus_four\|none |
| 0 | 2 | 0 | 5 | 1 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 64 | 2016\|MS\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 94 | 2016\|MT\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 6 | 2016\|MT\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 746 | 2016\|MT\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|MT\|invalid\|none |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 2016\|MT\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|MT\|zip_plus_four\|none |
| 0 | 5 | 0 | 0 | 2 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 52 | 2016\|MT\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2016\|Ma\|five_digit\|single |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2 | 2 | 0 | 0 | 0 | 2 | 2016\|Mi\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2016\|Mi\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 3338 | 2016\|NC\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 76 | 2016\|NC\|five_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5544 | 2016\|NC\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|NC\|invalid\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 60 | 2016\|NC\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 146 | 2016\|NC\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 2 | 0 | 1 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 133 | 2016\|ND\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2016\|ND\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 772 | 2016\|ND\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|ND\|invalid\|none |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 14 | 2016\|ND\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 2 | 0 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 47 | 2016\|ND\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 527 | 2016\|NE\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 9 | 2016\|NE\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1316 | 2016\|NE\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|NE\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 15 | 2016\|NE\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 41 | 2016\|NE\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 109 | 2016\|NH\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 7 | 2016\|NH\|five_digit\|none |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1207 | 2016\|NH\|five_digit\|single |
| 0 | 2 | 0 | 3 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 7 | 0 | 0 | 0 | 0 | 7 | 2016\|NH\|invalid\|none |
| 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 2016\|NH\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 22 | 2016\|NH\|zip_plus_four\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 712 | 2016\|NJ\|five_digit\|multiple |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 30 | 2016\|NJ\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3736 | 2016\|NJ\|five_digit\|single |
| 0 | 3 | 0 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 41 | 2016\|NJ\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 2016\|NJ\|padded_four_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 22 | 2016\|NJ\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 140 | 2016\|NJ\|zip_plus_four\|single |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 60 | 2016\|NM\|five_digit\|multiple |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 16 | 2016\|NM\|five_digit\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1126 | 2016\|NM\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|NM\|invalid\|none |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2016\|NM\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 31 | 2016\|NM\|zip_plus_four\|single |
| 0 | 4 | 0 | 4 | 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 152 | 2016\|NV\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 15 | 2016\|NV\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1801 | 2016\|NV\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|NV\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2016\|NV\|padded_four_digit\|single |
| 0 | 3 | 0 | 2 | 0 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 5 | 5 | 0 | 0 | 0 | 5 | 2016\|NV\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 83 | 2016\|NV\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1515 | 2016\|NY\|five_digit\|multiple |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 104 | 2016\|NY\|five_digit\|none |
| 0 | 7 | 0 | 0 | 0 | 0 | 1 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8315 | 2016\|NY\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2016\|NY\|invalid\|none |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2016\|NY\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 23 | 2016\|NY\|padded_four_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 61 | 2016\|NY\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2016\|NY\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 332 | 2016\|NY\|zip_plus_four\|single |
| 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2016\|Ne\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 3261 | 2016\|OH\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 77 | 2016\|OH\|five_digit\|none |
| 0 | 6 | 0 | 0 | 1 | 0 | 1 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8183 | 2016\|OH\|five_digit\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2016\|OH\|invalid\|none |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2016\|OH\|padded_four_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 79 | 2016\|OH\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 2 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2016\|OH\|zip_plus_four\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 217 | 2016\|OH\|zip_plus_four\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 918 | 2016\|OK\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 19 | 2016\|OK\|five_digit\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1824 | 2016\|OK\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|OK\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|OK\|padded_four_digit\|none |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 29 | 2016\|OK\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 49 | 2016\|OK\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 728 | 2016\|OR\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 23 | 2016\|OR\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3037 | 2016\|OR\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|OR\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 18 | 2016\|OR\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2016\|OR\|zip_plus_four\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 112 | 2016\|OR\|zip_plus_four\|single |
| 0 | 2 | 0 | 2 | 1 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 5 | 5 | 5 | 0 | 5 | 0 | 5 | 2016\|Oh\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2016\|Ok\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2016\|Or\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2441 | 2016\|PA\|five_digit\|multiple |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 107 | 2016\|PA\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8779 | 2016\|PA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|PA\|invalid\|none |
| 0 | 0 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 2016\|PA\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2016\|PA\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 50 | 2016\|PA\|padded_four_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 62 | 2016\|PA\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 0 | 5 | 2016\|PA\|zip_plus_four\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 308 | 2016\|PA\|zip_plus_four\|single |
| 0 | 0 | 0 | 7 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 0 | 0 | 563 | 2016\|PR\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2016\|PR\|five_digit\|none |
| 0 | 1 | 0 | 7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 310 | 2016\|PR\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2016\|PR\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|PR\|padded_four_digit\|none |
| 0 | 0 | 0 | 4 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 0 | 0 | 9 | 2016\|PR\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 28 | 2016\|PR\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2016\|PW\|padded_four_digit\|single |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 91 | 2016\|RI\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2016\|RI\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 581 | 2016\|RI\|five_digit\|single |
| 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 4 | 2016\|RI\|invalid\|none |
| 0 | 2 | 0 | 1 | 1 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 4 | 4 | 0 | 0 | 0 | 4 | 2016\|RI\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 18 | 2016\|RI\|zip_plus_four\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 621 | 2016\|SC\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2016\|SC\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1420 | 2016\|SC\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|SC\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|SC\|padded_four_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 25 | 2016\|SC\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 47 | 2016\|SC\|zip_plus_four\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 371 | 2016\|SD\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2016\|SD\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 630 | 2016\|SD\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|SD\|invalid\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 22 | 2016\|SD\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|SD\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 35 | 2016\|SD\|zip_plus_four\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 1857 | 2016\|TN\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 23 | 2016\|TN\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3422 | 2016\|TN\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|TN\|invalid\|none |
| 0 | 4 | 0 | 1 | 2 | 0 | 1 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 71 | 2016\|TN\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|TN\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 181 | 2016\|TN\|zip_plus_four\|single |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 3854 | 2016\|TX\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 90 | 2016\|TX\|five_digit\|none |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 13153 | 2016\|TX\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2016\|TX\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2016\|TX\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2016\|TX\|padded_four_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 158 | 2016\|TX\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2016\|TX\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 590 | 2016\|TX\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 56 | 2016\|UT\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 7 | 2016\|UT\|five_digit\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 739 | 2016\|UT\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2016\|UT\|invalid\|none |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2016\|UT\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 41 | 2016\|UT\|zip_plus_four\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2653 | 2016\|VA\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 37 | 2016\|VA\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3302 | 2016\|VA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|VA\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|VA\|padded_four_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 5 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 72 | 2016\|VA\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 103 | 2016\|VA\|zip_plus_four\|single |
| 0 | 0 | 0 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2016\|VI\|five_digit\|none |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 17 | 2016\|VI\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2016\|VI\|invalid\|none |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 2 | 2 | 2 | 2 | 2 | 2016\|VI\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 43 | 2016\|VT\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 7 | 2016\|VT\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 453 | 2016\|VT\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2016\|VT\|invalid\|none |
| 0 | 5 | 0 | 1 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 7 | 7 | 7 | 0 | 7 | 0 | 7 | 2016\|VT\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 143 | 2016\|WA\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 16 | 2016\|WA\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1978 | 2016\|WA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|WA\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 9 | 2016\|WA\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 144 | 2016\|WA\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1948 | 2016\|WI\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 31 | 2016\|WI\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4413 | 2016\|WI\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|WI\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 65 | 2016\|WI\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2016\|WI\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 0 | 0 | 1 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 157 | 2016\|WI\|zip_plus_four\|single |
| 0 | 3 | 0 | 4 | 1 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 313 | 2016\|WV\|five_digit\|multiple |
| 0 | 1 | 0 | 6 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 16 | 2016\|WV\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 946 | 2016\|WV\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|WV\|invalid\|none |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 12 | 2016\|WV\|zip_plus_four\|multiple |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 25 | 2016\|WV\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 20 | 2016\|WY\|five_digit\|multiple |
| 0 | 1 | 0 | 6 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 14 | 2016\|WY\|five_digit\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 254 | 2016\|WY\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2016\|WY\|invalid\|none |
| 0 | 2 | 0 | 2 | 3 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 7 | 7 | 7 | 0 | 7 | 0 | 7 | 2016\|WY\|zip_plus_four\|single |
| 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2016\|al\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 9 | 2016\|fl\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2016\|ga\|five_digit\|multiple |
| 0 | 4 | 0 | 0 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 6 | 6 | 6 | 0 | 6 | 0 | 6 | 2016\|ga\|five_digit\|single |
| 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2016\|nc\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2016\|ny\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2016\|ny\|five_digit\|single |
| 0 | 3 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2016\|tn\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2016\|tx\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 2 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2016\|tx\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2017\|AA\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2017\|AA\|five_digit\|none |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2017\|AA\|five_digit\|single |
| 0 | 3 | 0 | 4 | 1 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 10 | 2017\|AK\|five_digit\|multiple |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 119 | 2017\|AK\|five_digit\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1077 | 2017\|AK\|five_digit\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2017\|AK\|zip_plus_four\|none |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 19 | 2017\|AK\|zip_plus_four\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1012 | 2017\|AL\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 30 | 2017\|AL\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2612 | 2017\|AL\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|AL\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 4 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 83 | 2017\|AL\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|AL\|zip_plus_four\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 201 | 2017\|AL\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 710 | 2017\|AR\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 23 | 2017\|AR\|five_digit\|none |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1338 | 2017\|AR\|five_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 46 | 2017\|AR\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|AR\|zip_plus_four\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 87 | 2017\|AR\|zip_plus_four\|single |
| 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2017\|AS\|five_digit\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 1 | 0 | 1 | 2017\|AS\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 96 | 2017\|AZ\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 56 | 2017\|AZ\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3936 | 2017\|AZ\|five_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 17 | 2017\|AZ\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 5 | 2017\|AZ\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 324 | 2017\|AZ\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2017\|Al\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2567 | 2017\|CA\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 173 | 2017\|CA\|five_digit\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 25450 | 2017\|CA\|five_digit\|single |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2017\|CA\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 118 | 2017\|CA\|zip_plus_four\|multiple |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 13 | 2017\|CA\|zip_plus_four\|none |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1788 | 2017\|CA\|zip_plus_four\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1978 | 2017\|CO\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 24 | 2017\|CO\|five_digit\|none |
| 0 | 5 | 0 | 2 | 0 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2529 | 2017\|CO\|five_digit\|single |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2017\|CO\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 98 | 2017\|CO\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|CO\|zip_plus_four\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 172 | 2017\|CO\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 171 | 2017\|CT\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 27 | 2017\|CT\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4016 | 2017\|CT\|five_digit\|single |
| 0 | 5 | 0 | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 30 | 2017\|CT\|invalid\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 10 | 2017\|CT\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 2 | 2017\|CT\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 178 | 2017\|CT\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2017\|Ca\|five_digit\|multiple |
| 0 | 4 | 0 | 2 | 0 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 6 | 6 | 6 | 0 | 6 | 0 | 6 | 2017\|Ca\|five_digit\|single |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2017\|DC\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 341 | 2017\|DC\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|DC\|zip_plus_four\|none |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 39 | 2017\|DC\|zip_plus_four\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 4 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 40 | 2017\|DE\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2017\|DE\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 607 | 2017\|DE\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|DE\|padded_four_digit\|none |
| 0 | 2 | 0 | 0 | 1 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 3 | 3 | 0 | 0 | 0 | 3 | 2017\|DE\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|DE\|zip_plus_four\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 54 | 2017\|DE\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1095 | 2017\|FL\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 67 | 2017\|FL\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 11193 | 2017\|FL\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|FL\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2017\|FL\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 126 | 2017\|FL\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 2 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 7 | 2017\|FL\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1190 | 2017\|FL\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2017\|Fl\|five_digit\|multiple |
| 0 | 5 | 0 | 1 | 0 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 6 | 6 | 6 | 0 | 6 | 0 | 6 | 2017\|Fl\|five_digit\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 3050 | 2017\|GA\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 38 | 2017\|GA\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4199 | 2017\|GA\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|GA\|padded_four_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 225 | 2017\|GA\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2017\|GA\|zip_plus_four\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 298 | 2017\|GA\|zip_plus_four\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2017\|GU\|five_digit\|none |
| 0 | 0 | 0 | 6 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 21 | 2017\|GU\|five_digit\|single |
| 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 2 | 2 | 2 | 2 | 2 | 2017\|GU\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 2 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 3 | 3 | 0 | 0 | 0 | 3 | 2017\|Ga\|five_digit\|multiple |
| 0 | 2 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 5 | 2017\|HI\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 929 | 2017\|HI\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|HI\|padded_four_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 57 | 2017\|HI\|zip_plus_four\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1036 | 2017\|IA\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 18 | 2017\|IA\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2579 | 2017\|IA\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 65 | 2017\|IA\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 155 | 2017\|IA\|zip_plus_four\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 414 | 2017\|ID\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 11 | 2017\|ID\|five_digit\|none |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 889 | 2017\|ID\|five_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 23 | 2017\|ID\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 74 | 2017\|ID\|zip_plus_four\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2446 | 2017\|IL\|five_digit\|multiple |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 38 | 2017\|IL\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8639 | 2017\|IL\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 140 | 2017\|IL\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2017\|IL\|zip_plus_four\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 627 | 2017\|IL\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 2 | 0 | 1 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1733 | 2017\|IN\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 42 | 2017\|IN\|five_digit\|none |
| 0 | 3 | 0 | 1 | 3 | 0 | 1 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4288 | 2017\|IN\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 110 | 2017\|IN\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2017\|IN\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 266 | 2017\|IN\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2017\|Id\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2017\|Il\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2017\|In\|five_digit\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 512 | 2017\|KS\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 19 | 2017\|KS\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2019 | 2017\|KS\|five_digit\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 24 | 2017\|KS\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2017\|KS\|zip_plus_four\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 127 | 2017\|KS\|zip_plus_four\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 1572 | 2017\|KY\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 33 | 2017\|KY\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2436 | 2017\|KY\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|KY\|invalid\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 100 | 2017\|KY\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|KY\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 127 | 2017\|KY\|zip_plus_four\|single |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 600 | 2017\|LA\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 41 | 2017\|LA\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2533 | 2017\|LA\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 51 | 2017\|LA\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|LA\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 189 | 2017\|LA\|zip_plus_four\|single |
| 0 | 3 | 0 | 0 | 5 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 23 | 2017\|La\|five_digit\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 15 | 2017\|La\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 385 | 2017\|MA\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 38 | 2017\|MA\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3951 | 2017\|MA\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 0 | 48 | 2017\|MA\|invalid\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 24 | 2017\|MA\|zip_plus_four\|multiple |
| 0 | 2 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 5 | 2017\|MA\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 281 | 2017\|MA\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 644 | 2017\|MD\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 11 | 2017\|MD\|five_digit\|none |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2250 | 2017\|MD\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2017\|MD\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 4 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 69 | 2017\|MD\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|MD\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 245 | 2017\|MD\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 11 | 2017\|ME\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 7 | 2017\|ME\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1096 | 2017\|ME\|five_digit\|single |
| 0 | 4 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 7 | 0 | 0 | 0 | 0 | 7 | 2017\|ME\|invalid\|none |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2 | 2 | 0 | 0 | 0 | 2 | 2017\|ME\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 64 | 2017\|ME\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2017\|MH\|five_digit\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1555 | 2017\|MI\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 39 | 2017\|MI\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5761 | 2017\|MI\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2017\|MI\|padded_four_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 129 | 2017\|MI\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 7 | 2017\|MI\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 384 | 2017\|MI\|zip_plus_four\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 2801 | 2017\|MN\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 39 | 2017\|MN\|five_digit\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6090 | 2017\|MN\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 117 | 2017\|MN\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2017\|MN\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 265 | 2017\|MN\|zip_plus_four\|single |
| 0 | 1 | 0 | 2 | 4 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 8 | 8 | 0 | 0 | 0 | 1304 | 2017\|MO\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 35 | 2017\|MO\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3662 | 2017\|MO\|five_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 87 | 2017\|MO\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2017\|MO\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 268 | 2017\|MO\|zip_plus_four\|single |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 11 | 2017\|MP\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 2017\|MP\|zip_plus_four\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 773 | 2017\|MS\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 24 | 2017\|MS\|five_digit\|none |
| 0 | 5 | 0 | 2 | 0 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1102 | 2017\|MS\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2017\|MS\|padded_four_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 69 | 2017\|MS\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 87 | 2017\|MS\|zip_plus_four\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 73 | 2017\|MT\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2017\|MT\|five_digit\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 665 | 2017\|MT\|five_digit\|single |
| 0 | 6 | 0 | 0 | 0 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 6 | 6 | 0 | 0 | 0 | 6 | 2017\|MT\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 56 | 2017\|MT\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 2017\|Mi\|five_digit\|multiple |
| 0 | 2 | 0 | 0 | 1 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2017\|Mi\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2017\|Mo\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 3415 | 2017\|NC\|five_digit\|multiple |
| 0 | 1 | 0 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 73 | 2017\|NC\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5345 | 2017\|NC\|five_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 170 | 2017\|NC\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2017\|NC\|zip_plus_four\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 297 | 2017\|NC\|zip_plus_four\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 123 | 2017\|ND\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2017\|ND\|five_digit\|none |
| 0 | 3 | 0 | 4 | 1 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 839 | 2017\|ND\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 9 | 2017\|ND\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 44 | 2017\|ND\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 474 | 2017\|NE\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 14 | 2017\|NE\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1245 | 2017\|NE\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 28 | 2017\|NE\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|NE\|zip_plus_four\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 7 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 76 | 2017\|NE\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 98 | 2017\|NH\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 10 | 2017\|NH\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1213 | 2017\|NH\|five_digit\|single |
| 0 | 3 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 7 | 0 | 0 | 0 | 0 | 7 | 2017\|NH\|invalid\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 10 | 2017\|NH\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 78 | 2017\|NH\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 784 | 2017\|NJ\|five_digit\|multiple |
| 0 | 0 | 0 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 29 | 2017\|NJ\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3729 | 2017\|NJ\|five_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 8 | 0 | 0 | 0 | 0 | 52 | 2017\|NJ\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|NJ\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 2017\|NJ\|padded_four_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 58 | 2017\|NJ\|zip_plus_four\|multiple |
| 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 2 | 2017\|NJ\|zip_plus_four\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 268 | 2017\|NJ\|zip_plus_four\|single |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 52 | 2017\|NM\|five_digit\|multiple |
| 0 | 3 | 0 | 1 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 17 | 2017\|NM\|five_digit\|none |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1068 | 2017\|NM\|five_digit\|single |
| 0 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 0 | 0 | 4 | 2017\|NM\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 77 | 2017\|NM\|zip_plus_four\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 4 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 153 | 2017\|NV\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 14 | 2017\|NV\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1861 | 2017\|NV\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2017\|NV\|padded_four_digit\|single |
| 0 | 3 | 0 | 2 | 0 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 5 | 5 | 0 | 0 | 0 | 5 | 2017\|NV\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 131 | 2017\|NV\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1494 | 2017\|NY\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 80 | 2017\|NY\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8790 | 2017\|NY\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|NY\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|NY\|padded_four_digit\|none |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 9 | 2017\|NY\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 149 | 2017\|NY\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 5 | 2017\|NY\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 0 | 0 | 1 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 857 | 2017\|NY\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 3 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 3197 | 2017\|OH\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 80 | 2017\|OH\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8636 | 2017\|OH\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2017\|OH\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2017\|OH\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 162 | 2017\|OH\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2017\|OH\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 414 | 2017\|OH\|zip_plus_four\|single |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 875 | 2017\|OK\|five_digit\|multiple |
| 0 | 0 | 0 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 19 | 2017\|OK\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1808 | 2017\|OK\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|OK\|padded_four_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 61 | 2017\|OK\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|OK\|zip_plus_four\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 133 | 2017\|OK\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 717 | 2017\|OR\|five_digit\|multiple |
| 0 | 1 | 0 | 5 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 17 | 2017\|OR\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2920 | 2017\|OR\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 46 | 2017\|OR\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2017\|OR\|zip_plus_four\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 209 | 2017\|OR\|zip_plus_four\|single |
| 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2 | 2 | 0 | 0 | 0 | 2 | 2017\|Oh\|five_digit\|multiple |
| 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2017\|Oh\|five_digit\|single |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2017\|Ok\|five_digit\|multiple |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 2420 | 2017\|PA\|five_digit\|multiple |
| 0 | 0 | 0 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 91 | 2017\|PA\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8620 | 2017\|PA\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2017\|PA\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|PA\|padded_four_digit\|none |
| 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2017\|PA\|padded_four_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 160 | 2017\|PA\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 11 | 2017\|PA\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 570 | 2017\|PA\|zip_plus_four\|single |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 0 | 0 | 483 | 2017\|PR\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 12 | 2017\|PR\|five_digit\|none |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 464 | 2017\|PR\|five_digit\|single |
| 0 | 0 | 0 | 7 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 14 | 2017\|PR\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|PR\|padded_four_digit\|none |
| 0 | 0 | 0 | 7 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 0 | 0 | 13 | 2017\|PR\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 6 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 66 | 2017\|PR\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2017\|PW\|padded_four_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2017\|Pa\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 93 | 2017\|RI\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 2 | 2017\|RI\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 675 | 2017\|RI\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 8 | 2017\|RI\|invalid\|none |
| 0 | 2 | 0 | 0 | 2 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 4 | 4 | 0 | 0 | 0 | 4 | 2017\|RI\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 51 | 2017\|RI\|zip_plus_four\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1021 | 2017\|SC\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 14 | 2017\|SC\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2440 | 2017\|SC\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2017\|SC\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 83 | 2017\|SC\|zip_plus_four\|multiple |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 148 | 2017\|SC\|zip_plus_four\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 349 | 2017\|SD\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 2 | 2017\|SD\|five_digit\|none |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 596 | 2017\|SD\|five_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 24 | 2017\|SD\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|SD\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 0 | 0 | 1 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 33 | 2017\|SD\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1808 | 2017\|TN\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 26 | 2017\|TN\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3409 | 2017\|TN\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 111 | 2017\|TN\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2017\|TN\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 195 | 2017\|TN\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 3926 | 2017\|TX\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 96 | 2017\|TX\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 13688 | 2017\|TX\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2017\|TX\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2017\|TX\|padded_four_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 276 | 2017\|TX\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 10 | 2017\|TX\|zip_plus_four\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 972 | 2017\|TX\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2017\|Tx\|five_digit\|single |
| 0 | 3 | 0 | 2 | 2 | 0 | 1 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 102 | 2017\|UT\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 12 | 2017\|UT\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1281 | 2017\|UT\|five_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 10 | 2017\|UT\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 117 | 2017\|UT\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2734 | 2017\|VA\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 37 | 2017\|VA\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3376 | 2017\|VA\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 155 | 2017\|VA\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 2 | 2017\|VA\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 248 | 2017\|VA\|zip_plus_four\|single |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2017\|VI\|five_digit\|none |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 25 | 2017\|VI\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|VI\|invalid\|none |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 2 | 2 | 2 | 2 | 2 | 2017\|VI\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 60 | 2017\|VT\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 12 | 2017\|VT\|five_digit\|none |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 562 | 2017\|VT\|five_digit\|single |
| 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 2 | 2017\|VT\|invalid\|none |
| 0 | 4 | 0 | 0 | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 5 | 5 | 0 | 0 | 0 | 5 | 2017\|VT\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 33 | 2017\|VT\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 201 | 2017\|WA\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 27 | 2017\|WA\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3065 | 2017\|WA\|five_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 29 | 2017\|WA\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2017\|WA\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 329 | 2017\|WA\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 2 | 0 | 1 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1953 | 2017\|WI\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 39 | 2017\|WI\|five_digit\|none |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4301 | 2017\|WI\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 102 | 2017\|WI\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2017\|WI\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 253 | 2017\|WI\|zip_plus_four\|single |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 306 | 2017\|WV\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 10 | 2017\|WV\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 906 | 2017\|WV\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 22 | 2017\|WV\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2017\|WV\|zip_plus_four\|none |
| 0 | 4 | 0 | 4 | 0 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 71 | 2017\|WV\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 23 | 2017\|WY\|five_digit\|multiple |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 8 | 2017\|WY\|five_digit\|none |
| 0 | 3 | 0 | 4 | 1 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 299 | 2017\|WY\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2017\|WY\|zip_plus_four\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 20 | 2017\|WY\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2017\|Wa\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2017\|al\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8 | 2017\|fl\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2017\|ga\|five_digit\|multiple |
| 0 | 4 | 0 | 0 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 6 | 6 | 6 | 0 | 6 | 0 | 6 | 2017\|ga\|five_digit\|single |
| 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2017\|nc\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2017\|ny\|five_digit\|multiple |
| 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2017\|tn\|five_digit\|single |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2017\|tx\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2018\|AA\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2018\|AA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|AA\|zip_plus_four\|none |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2018\|AE\|five_digit\|none |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2018\|AE\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2018\|AE\|padded_four_digit\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|AE\|padded_four_digit\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 12 | 2018\|AK\|five_digit\|multiple |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 115 | 2018\|AK\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1119 | 2018\|AK\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|AK\|invalid\|none |
| 0 | 0 | 0 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2018\|AK\|zip_plus_four\|none |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 29 | 2018\|AK\|zip_plus_four\|single |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1066 | 2018\|AL\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 22 | 2018\|AL\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2753 | 2018\|AL\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2018\|AL\|invalid\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 74 | 2018\|AL\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|AL\|zip_plus_four\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 179 | 2018\|AL\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|AP\|five_digit\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 860 | 2018\|AR\|five_digit\|multiple |
| 0 | 0 | 0 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 31 | 2018\|AR\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1606 | 2018\|AR\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|AR\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 45 | 2018\|AR\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|AR\|zip_plus_four\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 93 | 2018\|AR\|zip_plus_four\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|AS\|five_digit\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|AS\|five_digit\|single |
| 0 | 2 | 0 | 0 | 6 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 118 | 2018\|AZ\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 69 | 2018\|AZ\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5049 | 2018\|AZ\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|AZ\|invalid\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 15 | 2018\|AZ\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 279 | 2018\|AZ\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2018\|Al\|five_digit\|multiple |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2590 | 2018\|CA\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 179 | 2018\|CA\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 28193 | 2018\|CA\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2018\|CA\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2018\|CA\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2018\|CA\|padded_four_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 101 | 2018\|CA\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 11 | 2018\|CA\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1654 | 2018\|CA\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 2155 | 2018\|CO\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 26 | 2018\|CO\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2713 | 2018\|CO\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|CO\|invalid\|none |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2018\|CO\|padded_four_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 115 | 2018\|CO\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|CO\|zip_plus_four\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 177 | 2018\|CO\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 160 | 2018\|CT\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 29 | 2018\|CT\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4345 | 2018\|CT\|five_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 26 | 2018\|CT\|invalid\|none |
| 0 | 6 | 0 | 0 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 7 | 7 | 0 | 0 | 0 | 7 | 2018\|CT\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 4 | 0 | 0 | 0 | 0 | 4 | 2018\|CT\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 157 | 2018\|CT\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2018\|Ca\|five_digit\|multiple |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 12 | 2018\|Ca\|five_digit\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|DC\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 513 | 2018\|DC\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|DC\|invalid\|none |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2018\|DC\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 39 | 2018\|DC\|zip_plus_four\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 46 | 2018\|DE\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 6 | 2018\|DE\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 693 | 2018\|DE\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|DE\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|DE\|padded_four_digit\|none |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2 | 2 | 0 | 0 | 0 | 2 | 2018\|DE\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|DE\|zip_plus_four\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 42 | 2018\|DE\|zip_plus_four\|single |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 1211 | 2018\|FL\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 84 | 2018\|FL\|five_digit\|none |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 12609 | 2018\|FL\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2018\|FL\|invalid\|none |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|FL\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|FL\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 113 | 2018\|FL\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2018\|FL\|zip_plus_four\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1153 | 2018\|FL\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|FM\|five_digit\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|FM\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 5 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 10 | 2018\|Fl\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|Fl\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 185 | 2018\|Fl\|five_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 3447 | 2018\|GA\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 36 | 2018\|GA\|five_digit\|none |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4555 | 2018\|GA\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|GA\|invalid\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 210 | 2018\|GA\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2018\|GA\|zip_plus_four\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 274 | 2018\|GA\|zip_plus_four\|single |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 0 | 0 | 0 | 36 | 2018\|GU\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2018\|GU\|five_digit\|none |
| 0 | 0 | 0 | 7 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 31 | 2018\|GU\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 2018\|GU\|zip_plus_four\|single |
| 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2018\|Ga\|five_digit\|single |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 8 | 2018\|HI\|five_digit\|none |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2073 | 2018\|HI\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|HI\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 46 | 2018\|HI\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 3 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1176 | 2018\|IA\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 22 | 2018\|IA\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2822 | 2018\|IA\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|IA\|invalid\|none |
| 0 | 4 | 0 | 2 | 1 | 0 | 1 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 73 | 2018\|IA\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 163 | 2018\|IA\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 414 | 2018\|ID\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 9 | 2018\|ID\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 965 | 2018\|ID\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|ID\|invalid\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 26 | 2018\|ID\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|ID\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 62 | 2018\|ID\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 2686 | 2018\|IL\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 38 | 2018\|IL\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 9707 | 2018\|IL\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|IL\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|IL\|padded_four_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 118 | 2018\|IL\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 7 | 2018\|IL\|zip_plus_four\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 624 | 2018\|IL\|zip_plus_four\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1984 | 2018\|IN\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 47 | 2018\|IN\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4892 | 2018\|IN\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|IN\|invalid\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 107 | 2018\|IN\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 5 | 2018\|IN\|zip_plus_four\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 272 | 2018\|IN\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|Id\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2018\|In\|five_digit\|multiple |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 587 | 2018\|KS\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 18 | 2018\|KS\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2203 | 2018\|KS\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|KS\|invalid\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 30 | 2018\|KS\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 126 | 2018\|KS\|zip_plus_four\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1532 | 2018\|KY\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 27 | 2018\|KY\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2375 | 2018\|KY\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2018\|KY\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 74 | 2018\|KY\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 0 | 0 | 1 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 116 | 2018\|KY\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 710 | 2018\|LA\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 40 | 2018\|LA\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2826 | 2018\|LA\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|LA\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 41 | 2018\|LA\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|LA\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 161 | 2018\|LA\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 403 | 2018\|MA\|five_digit\|multiple |
| 0 | 2 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 48 | 2018\|MA\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4526 | 2018\|MA\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 43 | 2018\|MA\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 19 | 2018\|MA\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2018\|MA\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 255 | 2018\|MA\|zip_plus_four\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 758 | 2018\|MD\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 15 | 2018\|MD\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2619 | 2018\|MD\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|MD\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|MD\|padded_four_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 69 | 2018\|MD\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|MD\|zip_plus_four\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 210 | 2018\|MD\|zip_plus_four\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 16 | 2018\|ME\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 8 | 2018\|ME\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1321 | 2018\|ME\|five_digit\|single |
| 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2018\|ME\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 69 | 2018\|ME\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2018\|MH\|five_digit\|multiple |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1893 | 2018\|MI\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 34 | 2018\|MI\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6402 | 2018\|MI\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|MI\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|MI\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|MI\|padded_four_digit\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 138 | 2018\|MI\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2018\|MI\|zip_plus_four\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 406 | 2018\|MI\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2842 | 2018\|MN\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 39 | 2018\|MN\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6001 | 2018\|MN\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2018\|MN\|invalid\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 149 | 2018\|MN\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2018\|MN\|zip_plus_four\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 329 | 2018\|MN\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1521 | 2018\|MO\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 43 | 2018\|MO\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4039 | 2018\|MO\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|MO\|invalid\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 83 | 2018\|MO\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 3 | 2018\|MO\|zip_plus_four\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 216 | 2018\|MO\|zip_plus_four\|single |
| 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 7 | 7 | 7 | 7 | 7 | 7 | 2018\|MP\|five_digit\|single |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 912 | 2018\|MS\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 30 | 2018\|MS\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1196 | 2018\|MS\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|MS\|invalid\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 66 | 2018\|MS\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 76 | 2018\|MS\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 85 | 2018\|MT\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|MT\|five_digit\|none |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 666 | 2018\|MT\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|MT\|invalid\|none |
| 0 | 5 | 0 | 1 | 0 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 6 | 6 | 0 | 0 | 0 | 6 | 2018\|MT\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|MT\|zip_plus_four\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 55 | 2018\|MT\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|Ma\|five_digit\|single |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2 | 2 | 0 | 0 | 0 | 2 | 2018\|Mi\|five_digit\|multiple |
| 0 | 2 | 0 | 0 | 1 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2018\|Mi\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 3751 | 2018\|NC\|five_digit\|multiple |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 84 | 2018\|NC\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6129 | 2018\|NC\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2018\|NC\|invalid\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 185 | 2018\|NC\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2018\|NC\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 303 | 2018\|NC\|zip_plus_four\|single |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 106 | 2018\|ND\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2018\|ND\|five_digit\|none |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 807 | 2018\|ND\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|ND\|invalid\|none |
| 0 | 4 | 0 | 0 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 6 | 6 | 0 | 0 | 0 | 6 | 2018\|ND\|zip_plus_four\|multiple |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 47 | 2018\|ND\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 537 | 2018\|NE\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 11 | 2018\|NE\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1365 | 2018\|NE\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|NE\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|NE\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 26 | 2018\|NE\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|NE\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 90 | 2018\|NE\|zip_plus_four\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 115 | 2018\|NH\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 9 | 2018\|NH\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1343 | 2018\|NH\|five_digit\|single |
| 0 | 1 | 0 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 5 | 2018\|NH\|invalid\|none |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 9 | 2018\|NH\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 65 | 2018\|NH\|zip_plus_four\|single |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 920 | 2018\|NJ\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 25 | 2018\|NJ\|five_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4396 | 2018\|NJ\|five_digit\|single |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 34 | 2018\|NJ\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|NJ\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 2018\|NJ\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 47 | 2018\|NJ\|zip_plus_four\|multiple |
| 0 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 3 | 0 | 0 | 0 | 0 | 3 | 2018\|NJ\|zip_plus_four\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 256 | 2018\|NJ\|zip_plus_four\|single |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 51 | 2018\|NM\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 18 | 2018\|NM\|five_digit\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1199 | 2018\|NM\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|NM\|invalid\|none |
| 0 | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 6 | 6 | 0 | 0 | 0 | 6 | 2018\|NM\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|NM\|zip_plus_four\|none |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 82 | 2018\|NM\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 177 | 2018\|NV\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 14 | 2018\|NV\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2193 | 2018\|NV\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|NV\|invalid\|none |
| 0 | 3 | 0 | 1 | 0 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 4 | 4 | 0 | 0 | 0 | 4 | 2018\|NV\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 0 | 0 | 1 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 125 | 2018\|NV\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 4 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1629 | 2018\|NY\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 100 | 2018\|NY\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 9581 | 2018\|NY\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2018\|NY\|invalid\|none |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2018\|NY\|padded_four_digit\|none |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8 | 2018\|NY\|padded_four_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 134 | 2018\|NY\|zip_plus_four\|multiple |
| 0 | 3 | 0 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 10 | 2018\|NY\|zip_plus_four\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 775 | 2018\|NY\|zip_plus_four\|single |
| 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2018\|Ne\|five_digit\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 3647 | 2018\|OH\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 81 | 2018\|OH\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8753 | 2018\|OH\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2018\|OH\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|OH\|padded_four_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 170 | 2018\|OH\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2018\|OH\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 413 | 2018\|OH\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 871 | 2018\|OK\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 26 | 2018\|OK\|five_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1996 | 2018\|OK\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|OK\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 60 | 2018\|OK\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|OK\|zip_plus_four\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 128 | 2018\|OK\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 4 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 902 | 2018\|OR\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 31 | 2018\|OR\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3696 | 2018\|OR\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|OR\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 50 | 2018\|OR\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2018\|OR\|zip_plus_four\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 222 | 2018\|OR\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|Oh\|five_digit\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2018\|Ok\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|Ok\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2669 | 2018\|PA\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 114 | 2018\|PA\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 9464 | 2018\|PA\|five_digit\|single |
| 0 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 3 | 2018\|PA\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2018\|PA\|padded_four_digit\|multiple |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 164 | 2018\|PA\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 13 | 2018\|PA\|zip_plus_four\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 551 | 2018\|PA\|zip_plus_four\|single |
| 0 | 0 | 0 | 6 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 0 | 0 | 737 | 2018\|PR\|five_digit\|multiple |
| 0 | 0 | 0 | 7 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2018\|PR\|five_digit\|none |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 585 | 2018\|PR\|five_digit\|single |
| 0 | 0 | 0 | 0 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2018\|PR\|invalid\|none |
| 0 | 2 | 0 | 3 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 0 | 0 | 21 | 2018\|PR\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 82 | 2018\|PR\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|PW\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|Pa\|five_digit\|none |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|Pa\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 111 | 2018\|RI\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|RI\|five_digit\|none |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 690 | 2018\|RI\|five_digit\|single |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 8 | 2018\|RI\|invalid\|none |
| 0 | 3 | 0 | 0 | 1 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 4 | 4 | 0 | 0 | 0 | 4 | 2018\|RI\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 44 | 2018\|RI\|zip_plus_four\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 1303 | 2018\|SC\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 18 | 2018\|SC\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2979 | 2018\|SC\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|SC\|invalid\|none |
| 0 | 5 | 0 | 2 | 0 | 0 | 1 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 82 | 2018\|SC\|zip_plus_four\|multiple |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 148 | 2018\|SC\|zip_plus_four\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 347 | 2018\|SD\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|SD\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 656 | 2018\|SD\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|SD\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 25 | 2018\|SD\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|SD\|zip_plus_four\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 38 | 2018\|SD\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1961 | 2018\|TN\|five_digit\|multiple |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 31 | 2018\|TN\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3805 | 2018\|TN\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|TN\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 154 | 2018\|TN\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|TN\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 251 | 2018\|TN\|zip_plus_four\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 4607 | 2018\|TX\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 82 | 2018\|TX\|five_digit\|none |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 15900 | 2018\|TX\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2018\|TX\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2018\|TX\|padded_four_digit\|multiple |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 322 | 2018\|TX\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 10 | 2018\|TX\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1044 | 2018\|TX\|zip_plus_four\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 175 | 2018\|UT\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 19 | 2018\|UT\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1814 | 2018\|UT\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|UT\|invalid\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 10 | 2018\|UT\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|UT\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 0 | 0 | 1 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 136 | 2018\|UT\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 3061 | 2018\|VA\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 31 | 2018\|VA\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3850 | 2018\|VA\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|VA\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 148 | 2018\|VA\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 225 | 2018\|VA\|zip_plus_four\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|VI\|five_digit\|none |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 29 | 2018\|VI\|five_digit\|single |
| 0 | 0 | 0 | 1 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2018\|VI\|invalid\|none |
| 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 2 | 2 | 2 | 2 | 2 | 2018\|VI\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 58 | 2018\|VT\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 6 | 2018\|VT\|five_digit\|none |
| 0 | 4 | 0 | 2 | 1 | 0 | 1 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 502 | 2018\|VT\|five_digit\|single |
| 0 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 3 | 2018\|VT\|invalid\|none |
| 0 | 3 | 0 | 0 | 2 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 5 | 5 | 0 | 0 | 0 | 5 | 2018\|VT\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|VT\|zip_plus_four\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 31 | 2018\|VT\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 249 | 2018\|WA\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 29 | 2018\|WA\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3973 | 2018\|WA\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|WA\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 35 | 2018\|WA\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 4 | 0 | 0 | 0 | 0 | 4 | 2018\|WA\|zip_plus_four\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 377 | 2018\|WA\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2236 | 2018\|WI\|five_digit\|multiple |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 34 | 2018\|WI\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4903 | 2018\|WI\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|WI\|invalid\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 117 | 2018\|WI\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2018\|WI\|zip_plus_four\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 271 | 2018\|WI\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 284 | 2018\|WV\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 18 | 2018\|WV\|five_digit\|none |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 886 | 2018\|WV\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|WV\|invalid\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 23 | 2018\|WV\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2018\|WV\|zip_plus_four\|none |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 70 | 2018\|WV\|zip_plus_four\|single |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 37 | 2018\|WY\|five_digit\|multiple |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 11 | 2018\|WY\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 380 | 2018\|WY\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2018\|WY\|invalid\|none |
| 0 | 3 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 0 | 0 | 3 | 2018\|WY\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 27 | 2018\|WY\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2018\|Wa\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|al\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8 | 2018\|fl\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2018\|ga\|five_digit\|multiple |
| 0 | 4 | 0 | 0 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 6 | 6 | 6 | 0 | 6 | 0 | 6 | 2018\|ga\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|ky\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|nc\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2018\|pa\|five_digit\|single |
| 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2018\|tn\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2019\|AA\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2019\|AA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|AA\|invalid\|none |
| 0 | 1 | 0 | 5 | 2 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 8 | 8 | 0 | 0 | 0 | 15 | 2019\|AK\|five_digit\|multiple |
| 0 | 0 | 0 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 119 | 2019\|AK\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1128 | 2019\|AK\|five_digit\|single |
| 0 | 1 | 0 | 5 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 7 | 2019\|AK\|zip_plus_four\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 32 | 2019\|AK\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1135 | 2019\|AL\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 31 | 2019\|AL\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2796 | 2019\|AL\|five_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 81 | 2019\|AL\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 2 | 2019\|AL\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 233 | 2019\|AL\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|AP\|five_digit\|single |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 852 | 2019\|AR\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 26 | 2019\|AR\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1547 | 2019\|AR\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 60 | 2019\|AR\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|AR\|zip_plus_four\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 104 | 2019\|AR\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|AS\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 122 | 2019\|AZ\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 61 | 2019\|AZ\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4896 | 2019\|AZ\|five_digit\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2019\|AZ\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 12 | 2019\|AZ\|zip_plus_four\|multiple |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 298 | 2019\|AZ\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2019\|Az\|five_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 2513 | 2019\|CA\|five_digit\|multiple |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 151 | 2019\|CA\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 26090 | 2019\|CA\|five_digit\|single |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2019\|CA\|padded_four_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 125 | 2019\|CA\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 9 | 2019\|CA\|zip_plus_four\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1892 | 2019\|CA\|zip_plus_four\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 2144 | 2019\|CO\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 31 | 2019\|CO\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3007 | 2019\|CO\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|CO\|padded_four_digit\|none |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2019\|CO\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 111 | 2019\|CO\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 182 | 2019\|CO\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 137 | 2019\|CT\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 27 | 2019\|CT\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4198 | 2019\|CT\|five_digit\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 8 | 0 | 0 | 0 | 0 | 15 | 2019\|CT\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 11 | 2019\|CT\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 3 | 2019\|CT\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 209 | 2019\|CT\|zip_plus_four\|single |
| 0 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2019\|Ca\|five_digit\|single |
| 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2019\|DC\|five_digit\|none |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 431 | 2019\|DC\|five_digit\|single |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2019\|DC\|padded_four_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|DC\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 44 | 2019\|DC\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 38 | 2019\|DE\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 4 | 0 | 0 | 0 | 0 | 4 | 2019\|DE\|five_digit\|none |
| 0 | 7 | 0 | 0 | 0 | 0 | 1 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 645 | 2019\|DE\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|DE\|padded_four_digit\|none |
| 0 | 3 | 0 | 0 | 0 | 0 | 0 | 2 | 3 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 0 | 0 | 3 | 2019\|DE\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 57 | 2019\|DE\|zip_plus_four\|single |
| 0 | 5 | 0 | 0 | 2 | 0 | 1 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1272 | 2019\|FL\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 83 | 2019\|FL\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 12749 | 2019\|FL\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|FL\|padded_four_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 134 | 2019\|FL\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2019\|FL\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1298 | 2019\|FL\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2019\|FM\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 2 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2019\|Fl\|five_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 3366 | 2019\|GA\|five_digit\|multiple |
| 0 | 3 | 0 | 0 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 36 | 2019\|GA\|five_digit\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4499 | 2019\|GA\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|GA\|padded_four_digit\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 249 | 2019\|GA\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2019\|GA\|zip_plus_four\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 349 | 2019\|GA\|zip_plus_four\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2019\|GU\|five_digit\|none |
| 0 | 0 | 0 | 6 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 35 | 2019\|GU\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|GU\|zip_plus_four\|none |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 3 | 3 | 3 | 3 | 3 | 3 | 2019\|GU\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|Ga\|five_digit\|single |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 10 | 2019\|HI\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1047 | 2019\|HI\|five_digit\|single |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 83 | 2019\|HI\|zip_plus_four\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 1203 | 2019\|IA\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 20 | 2019\|IA\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2928 | 2019\|IA\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|IA\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 61 | 2019\|IA\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|IA\|zip_plus_four\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 168 | 2019\|IA\|zip_plus_four\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 440 | 2019\|ID\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2019\|ID\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1031 | 2019\|ID\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 28 | 2019\|ID\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 87 | 2019\|ID\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2695 | 2019\|IL\|five_digit\|multiple |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 45 | 2019\|IL\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 9629 | 2019\|IL\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 169 | 2019\|IL\|zip_plus_four\|multiple |
| 0 | 3 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 5 | 2019\|IL\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 715 | 2019\|IL\|zip_plus_four\|single |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 2081 | 2019\|IN\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 57 | 2019\|IN\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4984 | 2019\|IN\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2019\|IN\|padded_four_digit\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 134 | 2019\|IN\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2019\|IN\|zip_plus_four\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 337 | 2019\|IN\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|In\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 577 | 2019\|KS\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 14 | 2019\|KS\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2235 | 2019\|KS\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2019\|KS\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|KS\|padded_four_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 45 | 2019\|KS\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 163 | 2019\|KS\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1609 | 2019\|KY\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 35 | 2019\|KY\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2491 | 2019\|KY\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 97 | 2019\|KY\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 154 | 2019\|KY\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 693 | 2019\|LA\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 44 | 2019\|LA\|five_digit\|none |
| 0 | 6 | 0 | 1 | 0 | 0 | 1 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2870 | 2019\|LA\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|LA\|padded_four_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 51 | 2019\|LA\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2019\|LA\|zip_plus_four\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 196 | 2019\|LA\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 441 | 2019\|MA\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 58 | 2019\|MA\|five_digit\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4521 | 2019\|MA\|five_digit\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 8 | 0 | 0 | 0 | 0 | 32 | 2019\|MA\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 37 | 2019\|MA\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 363 | 2019\|MA\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 775 | 2019\|MD\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2019\|MD\|five_digit\|none |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2705 | 2019\|MD\|five_digit\|single |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2019\|MD\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 75 | 2019\|MD\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2019\|MD\|zip_plus_four\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 276 | 2019\|MD\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 12 | 2019\|ME\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2019\|ME\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1402 | 2019\|ME\|five_digit\|single |
| 0 | 2 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 5 | 2019\|ME\|invalid\|none |
| 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2 | 2 | 0 | 0 | 0 | 2 | 2019\|ME\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|ME\|zip_plus_four\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 81 | 2019\|ME\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2019\|MH\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|MH\|padded_four_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1943 | 2019\|MI\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 26 | 2019\|MI\|five_digit\|none |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6309 | 2019\|MI\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|MI\|padded_four_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 136 | 2019\|MI\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2019\|MI\|zip_plus_four\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 447 | 2019\|MI\|zip_plus_four\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 2732 | 2019\|MN\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 32 | 2019\|MN\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6110 | 2019\|MN\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 162 | 2019\|MN\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 335 | 2019\|MN\|zip_plus_four\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1406 | 2019\|MO\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 32 | 2019\|MO\|five_digit\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3956 | 2019\|MO\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 103 | 2019\|MO\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2019\|MO\|zip_plus_four\|none |
| 0 | 3 | 0 | 1 | 3 | 0 | 1 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 290 | 2019\|MO\|zip_plus_four\|single |
| 0 | 0 | 0 | 7 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 7 | 8 | 7 | 11 | 2019\|MP\|five_digit\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 978 | 2019\|MS\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 28 | 2019\|MS\|five_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1260 | 2019\|MS\|five_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 74 | 2019\|MS\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|MS\|zip_plus_four\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 84 | 2019\|MS\|zip_plus_four\|single |
| 0 | 4 | 0 | 2 | 1 | 0 | 1 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 94 | 2019\|MT\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2019\|MT\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 689 | 2019\|MT\|five_digit\|single |
| 0 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 0 | 0 | 4 | 2019\|MT\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2019\|MT\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 0 | 0 | 1 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 72 | 2019\|MT\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2019\|Mi\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2019\|Mi\|five_digit\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 3704 | 2019\|NC\|five_digit\|multiple |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 84 | 2019\|NC\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5760 | 2019\|NC\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 226 | 2019\|NC\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2019\|NC\|zip_plus_four\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 369 | 2019\|NC\|zip_plus_four\|single |
| 0 | 1 | 0 | 5 | 2 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 8 | 8 | 0 | 0 | 0 | 125 | 2019\|ND\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 7 | 2019\|ND\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 869 | 2019\|ND\|five_digit\|single |
| 0 | 4 | 0 | 0 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 6 | 6 | 0 | 0 | 0 | 6 | 2019\|ND\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 44 | 2019\|ND\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 566 | 2019\|NE\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2019\|NE\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1307 | 2019\|NE\|five_digit\|single |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2019\|NE\|padded_four_digit\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 30 | 2019\|NE\|zip_plus_four\|multiple |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 90 | 2019\|NE\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 112 | 2019\|NH\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 10 | 2019\|NH\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1406 | 2019\|NH\|five_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 8 | 2019\|NH\|invalid\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 12 | 2019\|NH\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 89 | 2019\|NH\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 914 | 2019\|NJ\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 28 | 2019\|NJ\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4226 | 2019\|NJ\|five_digit\|single |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 72 | 2019\|NJ\|invalid\|none |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2019\|NJ\|padded_four_digit\|none |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 2 | 2 | 2019\|NJ\|padded_four_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 72 | 2019\|NJ\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 0 | 5 | 2019\|NJ\|zip_plus_four\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 385 | 2019\|NJ\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 57 | 2019\|NM\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 14 | 2019\|NM\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1198 | 2019\|NM\|five_digit\|single |
| 0 | 1 | 0 | 4 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 5 | 5 | 0 | 0 | 0 | 5 | 2019\|NM\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2019\|NM\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 93 | 2019\|NM\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 185 | 2019\|NV\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 15 | 2019\|NV\|five_digit\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2150 | 2019\|NV\|five_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 10 | 2019\|NV\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 122 | 2019\|NV\|zip_plus_four\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1621 | 2019\|NY\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 3 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 107 | 2019\|NY\|five_digit\|none |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 9471 | 2019\|NY\|five_digit\|single |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2019\|NY\|padded_four_digit\|none |
| 0 | 0 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 6 | 6 | 0 | 6 | 0 | 6 | 2019\|NY\|padded_four_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 148 | 2019\|NY\|zip_plus_four\|multiple |
| 0 | 2 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 6 | 2019\|NY\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 908 | 2019\|NY\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 3744 | 2019\|OH\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 72 | 2019\|OH\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8840 | 2019\|OH\|five_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 210 | 2019\|OH\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2019\|OH\|zip_plus_four\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 535 | 2019\|OH\|zip_plus_four\|single |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 953 | 2019\|OK\|five_digit\|multiple |
| 0 | 0 | 0 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 18 | 2019\|OK\|five_digit\|none |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1945 | 2019\|OK\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 68 | 2019\|OK\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|OK\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 145 | 2019\|OK\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 945 | 2019\|OR\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 26 | 2019\|OR\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3687 | 2019\|OR\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|OR\|padded_four_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 55 | 2019\|OR\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2019\|OR\|zip_plus_four\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 231 | 2019\|OR\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|Oh\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|Ok\|five_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 2719 | 2019\|PA\|five_digit\|multiple |
| 0 | 0 | 0 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 106 | 2019\|PA\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 9359 | 2019\|PA\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2019\|PA\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2019\|PA\|padded_four_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 169 | 2019\|PA\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 7 | 2019\|PA\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 655 | 2019\|PA\|zip_plus_four\|single |
| 0 | 0 | 0 | 5 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 0 | 0 | 560 | 2019\|PR\|five_digit\|multiple |
| 0 | 0 | 0 | 7 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2019\|PR\|five_digit\|none |
| 0 | 0 | 0 | 6 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 590 | 2019\|PR\|five_digit\|single |
| 0 | 0 | 0 | 1 | 2 | 1 | 2 | 0 | 0 | 0 | 0 | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2019\|PR\|invalid\|none |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 0 | 0 | 30 | 2019\|PR\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 7 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 72 | 2019\|PR\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|PW\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2019\|Pa\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|Pa\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 111 | 2019\|RI\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2019\|RI\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 728 | 2019\|RI\|five_digit\|single |
| 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 2 | 2019\|RI\|invalid\|none |
| 0 | 3 | 0 | 4 | 1 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 9 | 2019\|RI\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 54 | 2019\|RI\|zip_plus_four\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 5 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 1321 | 2019\|SC\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 21 | 2019\|SC\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2988 | 2019\|SC\|five_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 80 | 2019\|SC\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 193 | 2019\|SC\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 359 | 2019\|SD\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 3 | 2019\|SD\|five_digit\|none |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 662 | 2019\|SD\|five_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 29 | 2019\|SD\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 2 | 2019\|SD\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 41 | 2019\|SD\|zip_plus_four\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1996 | 2019\|TN\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 29 | 2019\|TN\|five_digit\|none |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3713 | 2019\|TN\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2019\|TN\|padded_four_digit\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 166 | 2019\|TN\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|TN\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 304 | 2019\|TN\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 4 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 4724 | 2019\|TX\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 101 | 2019\|TX\|five_digit\|none |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 15822 | 2019\|TX\|five_digit\|single |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2019\|TX\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 4 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 323 | 2019\|TX\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 8 | 2019\|TX\|zip_plus_four\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1103 | 2019\|TX\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2019\|Tx\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|Tx\|five_digit\|single |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 196 | 2019\|UT\|five_digit\|multiple |
| 0 | 0 | 0 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 12 | 2019\|UT\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1889 | 2019\|UT\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|UT\|padded_four_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 14 | 2019\|UT\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 135 | 2019\|UT\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 4 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2974 | 2019\|VA\|five_digit\|multiple |
| 0 | 0 | 0 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 36 | 2019\|VA\|five_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3776 | 2019\|VA\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 202 | 2019\|VA\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 3 | 2019\|VA\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 281 | 2019\|VA\|zip_plus_four\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2019\|VI\|five_digit\|none |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 28 | 2019\|VI\|five_digit\|single |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2019\|VI\|invalid\|none |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 2 | 2 | 2 | 2 | 2 | 2019\|VI\|zip_plus_four\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 59 | 2019\|VT\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 5 | 2019\|VT\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 617 | 2019\|VT\|five_digit\|single |
| 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 2 | 2019\|VT\|invalid\|none |
| 0 | 5 | 0 | 1 | 0 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 6 | 6 | 0 | 0 | 0 | 6 | 2019\|VT\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 33 | 2019\|VT\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 397 | 2019\|WA\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 47 | 2019\|WA\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5426 | 2019\|WA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|WA\|missing\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 30 | 2019\|WA\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2019\|WA\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 454 | 2019\|WA\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2205 | 2019\|WI\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 45 | 2019\|WI\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4759 | 2019\|WI\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2019\|WI\|padded_four_digit\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 120 | 2019\|WI\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2019\|WI\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 280 | 2019\|WI\|zip_plus_four\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 336 | 2019\|WV\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 12 | 2019\|WV\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 963 | 2019\|WV\|five_digit\|single |
| 0 | 4 | 0 | 4 | 0 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 31 | 2019\|WV\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 70 | 2019\|WV\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 37 | 2019\|WY\|five_digit\|multiple |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 8 | 0 | 0 | 0 | 0 | 43 | 2019\|WY\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 420 | 2019\|WY\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2019\|WY\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 23 | 2019\|WY\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2019\|Wa\|five_digit\|single |
| 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2019\|fl\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|nc\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|ny\|five_digit\|single |
| 0 | 1 | 0 | 0 | 2 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2019\|ny\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2019\|oh\|five_digit\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|oh\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|pa\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2019\|va\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|AA\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2020\|AA\|five_digit\|single |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 17 | 2020\|AK\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 106 | 2020\|AK\|five_digit\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1158 | 2020\|AK\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|AK\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|AK\|padded_four_digit\|single |
| 0 | 1 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2020\|AK\|zip_plus_four\|single |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 1187 | 2020\|AL\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 24 | 2020\|AL\|five_digit\|none |
| 0 | 4 | 0 | 3 | 0 | 0 | 1 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2968 | 2020\|AL\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|AL\|invalid\|none |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 26 | 2020\|AL\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 94 | 2020\|AL\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|AP\|five_digit\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 897 | 2020\|AR\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 22 | 2020\|AR\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1556 | 2020\|AR\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|AR\|invalid\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 21 | 2020\|AR\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|AR\|zip_plus_four\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 40 | 2020\|AR\|zip_plus_four\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|AS\|five_digit\|none |
| 0 | 3 | 0 | 0 | 5 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 147 | 2020\|AZ\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 71 | 2020\|AZ\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5142 | 2020\|AZ\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|AZ\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|AZ\|padded_four_digit\|single |
| 0 | 2 | 0 | 0 | 2 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 4 | 4 | 0 | 0 | 0 | 4 | 2020\|AZ\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 146 | 2020\|AZ\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|Ak\|five_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2598 | 2020\|CA\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 163 | 2020\|CA\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 28073 | 2020\|CA\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2020\|CA\|invalid\|none |
| 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 5 | 0 | 5 | 0 | 5 | 2020\|CA\|padded_four_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 63 | 2020\|CA\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|CA\|zip_plus_four\|none |
| 0 | 3 | 0 | 0 | 5 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1114 | 2020\|CA\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2167 | 2020\|CO\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 31 | 2020\|CO\|five_digit\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2710 | 2020\|CO\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|CO\|invalid\|none |
| 0 | 0 | 0 | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 5 | 0 | 5 | 0 | 5 | 2020\|CO\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 49 | 2020\|CO\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 0 | 3 | 0 | 1 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 78 | 2020\|CO\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 142 | 2020\|CT\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 27 | 2020\|CT\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4323 | 2020\|CT\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 38 | 2020\|CT\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|CT\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|CT\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 46 | 2020\|CT\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|Ca\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2020\|Ca\|five_digit\|single |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2020\|DC\|five_digit\|none |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 477 | 2020\|DC\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|DC\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|DC\|padded_four_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 14 | 2020\|DC\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 40 | 2020\|DE\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 6 | 2020\|DE\|five_digit\|none |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 670 | 2020\|DE\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|DE\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|DE\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|DE\|padded_four_digit\|single |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2 | 2 | 0 | 0 | 0 | 2 | 2020\|DE\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 24 | 2020\|DE\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1364 | 2020\|FL\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 87 | 2020\|FL\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 13199 | 2020\|FL\|five_digit\|single |
| 0 | 1 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 5 | 2020\|FL\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|FL\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|FL\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2020\|FL\|padded_four_digit\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 67 | 2020\|FL\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|FL\|zip_plus_four\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 750 | 2020\|FL\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2020\|Fl\|five_digit\|single |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 3679 | 2020\|GA\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 43 | 2020\|GA\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4954 | 2020\|GA\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|GA\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|GA\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|GA\|padded_four_digit\|none |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2020\|GA\|padded_four_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 95 | 2020\|GA\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 147 | 2020\|GA\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|GU\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2020\|GU\|five_digit\|none |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 33 | 2020\|GU\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 2020\|GU\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|Ga\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|Ga\|five_digit\|single |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 12 | 2020\|HI\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1045 | 2020\|HI\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 31 | 2020\|HI\|zip_plus_four\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1148 | 2020\|IA\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 24 | 2020\|IA\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3017 | 2020\|IA\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|IA\|invalid\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 26 | 2020\|IA\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 45 | 2020\|IA\|zip_plus_four\|single |
| 0 | 3 | 0 | 0 | 5 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 407 | 2020\|ID\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 12 | 2020\|ID\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1069 | 2020\|ID\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|ID\|invalid\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 25 | 2020\|ID\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|ID\|zip_plus_four\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 47 | 2020\|ID\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2823 | 2020\|IL\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 51 | 2020\|IL\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 9890 | 2020\|IL\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|IL\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|IL\|padded_four_digit\|single |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 75 | 2020\|IL\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|IL\|zip_plus_four\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 402 | 2020\|IL\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2066 | 2020\|IN\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 52 | 2020\|IN\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5123 | 2020\|IN\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|IN\|invalid\|none |
| 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 5 | 0 | 5 | 0 | 5 | 2020\|IN\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 57 | 2020\|IN\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 1 | 0 | 1 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 142 | 2020\|IN\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|Il\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|In\|five_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 620 | 2020\|KS\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 17 | 2020\|KS\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2392 | 2020\|KS\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|KS\|invalid\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 13 | 2020\|KS\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|KS\|zip_plus_four\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 73 | 2020\|KS\|zip_plus_four\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 1738 | 2020\|KY\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 40 | 2020\|KY\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2651 | 2020\|KY\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|KY\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|KY\|padded_four_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 43 | 2020\|KY\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 0 | 0 | 1 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 46 | 2020\|KY\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 770 | 2020\|LA\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 38 | 2020\|LA\|five_digit\|none |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2986 | 2020\|LA\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|LA\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|LA\|padded_four_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 14 | 2020\|LA\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 72 | 2020\|LA\|zip_plus_four\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 511 | 2020\|MA\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 44 | 2020\|MA\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5160 | 2020\|MA\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 0 | 98 | 2020\|MA\|invalid\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 8 | 2020\|MA\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|MA\|zip_plus_four\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 55 | 2020\|MA\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 852 | 2020\|MD\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 10 | 2020\|MD\|five_digit\|none |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3398 | 2020\|MD\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|MD\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|MD\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 6 | 6 | 0 | 6 | 0 | 6 | 2020\|MD\|padded_four_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 28 | 2020\|MD\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 103 | 2020\|MD\|zip_plus_four\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 17 | 2020\|ME\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 11 | 2020\|ME\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1333 | 2020\|ME\|five_digit\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 8 | 0 | 0 | 0 | 0 | 15 | 2020\|ME\|invalid\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 13 | 2020\|ME\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2020\|MH\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|MH\|padded_four_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 2070 | 2020\|MI\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 37 | 2020\|MI\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6645 | 2020\|MI\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2020\|MI\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|MI\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|MI\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 53 | 2020\|MI\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|MI\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 171 | 2020\|MI\|zip_plus_four\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 2950 | 2020\|MN\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 42 | 2020\|MN\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6454 | 2020\|MN\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2020\|MN\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|MN\|padded_four_digit\|none |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 2 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 70 | 2020\|MN\|zip_plus_four\|multiple |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 164 | 2020\|MN\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1537 | 2020\|MO\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 45 | 2020\|MO\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4066 | 2020\|MO\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|MO\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 26 | 2020\|MO\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|MO\|zip_plus_four\|none |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 118 | 2020\|MO\|zip_plus_four\|single |
| 0 | 0 | 0 | 7 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 7 | 8 | 7 | 10 | 2020\|MP\|five_digit\|single |
| 0 | 6 | 0 | 1 | 0 | 0 | 1 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 979 | 2020\|MS\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 28 | 2020\|MS\|five_digit\|none |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1287 | 2020\|MS\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|MS\|invalid\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 31 | 2020\|MS\|zip_plus_four\|multiple |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 31 | 2020\|MS\|zip_plus_four\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 84 | 2020\|MT\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2020\|MT\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 721 | 2020\|MT\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|MT\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|MT\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 30 | 2020\|MT\|zip_plus_four\|single |
| 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2020\|Ma\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|Mi\|five_digit\|multiple |
| 0 | 5 | 0 | 2 | 0 | 0 | 1 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 3926 | 2020\|NC\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 93 | 2020\|NC\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6100 | 2020\|NC\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2020\|NC\|invalid\|none |
| 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2020\|NC\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 72 | 2020\|NC\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|NC\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 1 | 0 | 1 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 150 | 2020\|NC\|zip_plus_four\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 126 | 2020\|ND\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 7 | 2020\|ND\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 909 | 2020\|ND\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|ND\|invalid\|none |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2 | 2 | 0 | 0 | 0 | 2 | 2020\|ND\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 28 | 2020\|ND\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 613 | 2020\|NE\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 13 | 2020\|NE\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1429 | 2020\|NE\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|NE\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|NE\|padded_four_digit\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 11 | 2020\|NE\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 36 | 2020\|NE\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 121 | 2020\|NH\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 9 | 2020\|NH\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1449 | 2020\|NH\|five_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 0 | 21 | 2020\|NH\|invalid\|none |
| 0 | 2 | 0 | 1 | 1 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 4 | 4 | 0 | 0 | 0 | 4 | 2020\|NH\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 16 | 2020\|NH\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 994 | 2020\|NJ\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 36 | 2020\|NJ\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4847 | 2020\|NJ\|five_digit\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 8 | 0 | 0 | 0 | 0 | 104 | 2020\|NJ\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|NJ\|padded_four_digit\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 2020\|NJ\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 9 | 2020\|NJ\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 78 | 2020\|NJ\|zip_plus_four\|single |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 51 | 2020\|NM\|five_digit\|multiple |
| 0 | 1 | 0 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 17 | 2020\|NM\|five_digit\|none |
| 0 | 3 | 0 | 5 | 0 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1230 | 2020\|NM\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|NM\|invalid\|none |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|NM\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 26 | 2020\|NM\|zip_plus_four\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 193 | 2020\|NV\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 17 | 2020\|NV\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2309 | 2020\|NV\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|NV\|invalid\|none |
| 0 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 0 | 0 | 4 | 2020\|NV\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 63 | 2020\|NV\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1642 | 2020\|NY\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 96 | 2020\|NY\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 10252 | 2020\|NY\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|NY\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|NY\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2020\|NY\|padded_four_digit\|none |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 9 | 2020\|NY\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 47 | 2020\|NY\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|NY\|zip_plus_four\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 299 | 2020\|NY\|zip_plus_four\|single |
| 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2020\|Ne\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 3767 | 2020\|OH\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 88 | 2020\|OH\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8988 | 2020\|OH\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2020\|OH\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|OH\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 4 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 76 | 2020\|OH\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|OH\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 1 | 0 | 1 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 201 | 2020\|OH\|zip_plus_four\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1006 | 2020\|OK\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 25 | 2020\|OK\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1996 | 2020\|OK\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|OK\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|OK\|padded_four_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 29 | 2020\|OK\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 60 | 2020\|OK\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 927 | 2020\|OR\|five_digit\|multiple |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 25 | 2020\|OR\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3613 | 2020\|OR\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|OR\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|OR\|padded_four_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 23 | 2020\|OR\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2020\|OR\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 114 | 2020\|OR\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|Oh\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|Ok\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 3 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2928 | 2020\|PA\|five_digit\|multiple |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 107 | 2020\|PA\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 10031 | 2020\|PA\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2020\|PA\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|PA\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|PA\|padded_four_digit\|none |
| 0 | 0 | 0 | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 5 | 0 | 5 | 0 | 5 | 2020\|PA\|padded_four_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 59 | 2020\|PA\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 3 | 2020\|PA\|zip_plus_four\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 211 | 2020\|PA\|zip_plus_four\|single |
| 0 | 0 | 0 | 7 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 0 | 0 | 657 | 2020\|PR\|five_digit\|multiple |
| 0 | 0 | 0 | 7 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 9 | 2020\|PR\|five_digit\|none |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 652 | 2020\|PR\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 1 | 2 | 0 | 0 | 0 | 0 | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2020\|PR\|invalid\|none |
| 0 | 0 | 0 | 6 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 0 | 0 | 24 | 2020\|PR\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 64 | 2020\|PR\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|PW\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2020\|PW\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|Pa\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 118 | 2020\|RI\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2020\|RI\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 746 | 2020\|RI\|five_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 10 | 2020\|RI\|invalid\|none |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2020\|RI\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 12 | 2020\|RI\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1417 | 2020\|SC\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 20 | 2020\|SC\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3143 | 2020\|SC\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|SC\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|SC\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2020\|SC\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 27 | 2020\|SC\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 57 | 2020\|SC\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 349 | 2020\|SD\|five_digit\|multiple |
| 0 | 1 | 0 | 5 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 7 | 2020\|SD\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 689 | 2020\|SD\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|SD\|invalid\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 14 | 2020\|SD\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|SD\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 21 | 2020\|SD\|zip_plus_four\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 2143 | 2020\|TN\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 28 | 2020\|TN\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4065 | 2020\|TN\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|TN\|invalid\|none |
| 0 | 6 | 0 | 0 | 1 | 0 | 1 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 68 | 2020\|TN\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|TN\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 148 | 2020\|TN\|zip_plus_four\|single |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 4793 | 2020\|TX\|five_digit\|multiple |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 98 | 2020\|TX\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 16077 | 2020\|TX\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2020\|TX\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|TX\|padded_four_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 140 | 2020\|TX\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 514 | 2020\|TX\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 182 | 2020\|UT\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 14 | 2020\|UT\|five_digit\|none |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1981 | 2020\|UT\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|UT\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|UT\|padded_four_digit\|none |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2020\|UT\|padded_four_digit\|single |
| 0 | 2 | 0 | 0 | 1 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 3 | 3 | 0 | 0 | 0 | 3 | 2020\|UT\|zip_plus_four\|multiple |
| 0 | 3 | 0 | 2 | 2 | 0 | 1 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 61 | 2020\|UT\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 3130 | 2020\|VA\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 32 | 2020\|VA\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3929 | 2020\|VA\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2020\|VA\|invalid\|none |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2020\|VA\|padded_four_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 85 | 2020\|VA\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 103 | 2020\|VA\|zip_plus_four\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|VI\|five_digit\|none |
| 0 | 1 | 0 | 5 | 1 | 2 | 1 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 31 | 2020\|VI\|five_digit\|single |
| 0 | 0 | 0 | 3 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2020\|VI\|invalid\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 64 | 2020\|VT\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2020\|VT\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 586 | 2020\|VT\|five_digit\|single |
| 0 | 3 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 5 | 2020\|VT\|invalid\|none |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|VT\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 1 | 0 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 5 | 5 | 5 | 0 | 5 | 0 | 5 | 2020\|VT\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 396 | 2020\|WA\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 48 | 2020\|WA\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5530 | 2020\|WA\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|WA\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 16 | 2020\|WA\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|WA\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 265 | 2020\|WA\|zip_plus_four\|single |
| 0 | 3 | 0 | 4 | 1 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 2305 | 2020\|WI\|five_digit\|multiple |
| 0 | 2 | 0 | 0 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 55 | 2020\|WI\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5064 | 2020\|WI\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|WI\|invalid\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 4 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 44 | 2020\|WI\|zip_plus_four\|multiple |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 154 | 2020\|WI\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 334 | 2020\|WV\|five_digit\|multiple |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 12 | 2020\|WV\|five_digit\|none |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 991 | 2020\|WV\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2020\|WV\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2020\|WV\|padded_four_digit\|multiple |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 11 | 2020\|WV\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 21 | 2020\|WV\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 42 | 2020\|WY\|five_digit\|multiple |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 17 | 2020\|WY\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 444 | 2020\|WY\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2020\|WY\|invalid\|none |
| 0 | 3 | 0 | 4 | 0 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 7 | 7 | 7 | 0 | 7 | 0 | 7 | 2020\|WY\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|Wi\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2020\|wv\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|AA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2021\|AE\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2021\|AE\|padded_four_digit\|none |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 17 | 2021\|AK\|five_digit\|multiple |
| 0 | 3 | 0 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 112 | 2021\|AK\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1277 | 2021\|AK\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2021\|AK\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 10 | 2021\|AK\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1242 | 2021\|AL\|five_digit\|multiple |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 33 | 2021\|AL\|five_digit\|none |
| 0 | 4 | 0 | 3 | 0 | 0 | 1 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3104 | 2021\|AL\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|AL\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 4 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 93 | 2021\|AL\|zip_plus_four\|multiple |
| 0 | 2 | 0 | 6 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 231 | 2021\|AL\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2021\|AP\|five_digit\|single |
| 0 | 0 | 0 | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2021\|AP\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 943 | 2021\|AR\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 29 | 2021\|AR\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1685 | 2021\|AR\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|AR\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 68 | 2021\|AR\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2021\|AR\|zip_plus_four\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 109 | 2021\|AR\|zip_plus_four\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2021\|AS\|five_digit\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 154 | 2021\|AZ\|five_digit\|multiple |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 57 | 2021\|AZ\|five_digit\|none |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5098 | 2021\|AZ\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2021\|AZ\|invalid\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 9 | 2021\|AZ\|zip_plus_four\|multiple |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 318 | 2021\|AZ\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|Ak\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|Al\|five_digit\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 2576 | 2021\|CA\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 191 | 2021\|CA\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 27725 | 2021\|CA\|five_digit\|single |
| 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2021\|CA\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2021\|CA\|padded_four_digit\|none |
| 0 | 0 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 6 | 6 | 0 | 6 | 0 | 6 | 2021\|CA\|padded_four_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 124 | 2021\|CA\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|CA\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1576 | 2021\|CA\|zip_plus_four\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 2338 | 2021\|CO\|five_digit\|multiple |
| 0 | 3 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 27 | 2021\|CO\|five_digit\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2894 | 2021\|CO\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|CO\|invalid\|none |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2021\|CO\|padded_four_digit\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 112 | 2021\|CO\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 153 | 2021\|CO\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 2021\|CT\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 22 | 2021\|CT\|five_digit\|none |
| 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 15 | 2021\|CT\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 87 | 2021\|CT\|invalid\|none |
| 0 | 3 | 0 | 0 | 5 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 164 | 2021\|CT\|padded_four_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 34 | 2021\|CT\|padded_four_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4252 | 2021\|CT\|padded_four_digit\|single |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|CT\|zip_plus_four\|none |
| 0 | 1 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2021\|Ca\|five_digit\|single |
| 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2021\|DC\|five_digit\|none |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1257 | 2021\|DC\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|DC\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|DC\|padded_four_digit\|single |
| 0 | 1 | 0 | 7 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 99 | 2021\|DC\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 55 | 2021\|DE\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 8 | 2021\|DE\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 704 | 2021\|DE\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|DE\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2021\|DE\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|DE\|padded_four_digit\|single |
| 0 | 1 | 0 | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 3 | 3 | 0 | 0 | 0 | 3 | 2021\|DE\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 60 | 2021\|DE\|zip_plus_four\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 1483 | 2021\|FL\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 81 | 2021\|FL\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 13531 | 2021\|FL\|five_digit\|single |
| 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2021\|FL\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2021\|FL\|padded_four_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 122 | 2021\|FL\|zip_plus_four\|multiple |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1425 | 2021\|FL\|zip_plus_four\|single |
| 0 | 3 | 0 | 1 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 7 | 7 | 0 | 0 | 0 | 7 | 2021\|Fl\|five_digit\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 52 | 2021\|Fl\|five_digit\|single |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2 | 2 | 0 | 0 | 0 | 2 | 2021\|Fl\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 17 | 2021\|Fl\|zip_plus_four\|single |
| 0 | 3 | 0 | 4 | 1 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 3956 | 2021\|GA\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 52 | 2021\|GA\|five_digit\|none |
| 0 | 3 | 0 | 0 | 5 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5030 | 2021\|GA\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2021\|GA\|invalid\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 290 | 2021\|GA\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 425 | 2021\|GA\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2021\|GU\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2021\|GU\|five_digit\|none |
| 0 | 0 | 0 | 6 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 52 | 2021\|GU\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2021\|Ga\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|Ga\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2021\|HI\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 10 | 2021\|HI\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1018 | 2021\|HI\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|HI\|invalid\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 38 | 2021\|HI\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1178 | 2021\|IA\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 18 | 2021\|IA\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3047 | 2021\|IA\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|IA\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 50 | 2021\|IA\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 124 | 2021\|IA\|zip_plus_four\|single |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 473 | 2021\|ID\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 12 | 2021\|ID\|five_digit\|none |
| 0 | 2 | 0 | 0 | 6 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1761 | 2021\|ID\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|ID\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 36 | 2021\|ID\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 86 | 2021\|ID\|zip_plus_four\|single |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 3095 | 2021\|IL\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 49 | 2021\|IL\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 10580 | 2021\|IL\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2021\|IL\|invalid\|none |
| 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|IL\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 4 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 138 | 2021\|IL\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|IL\|zip_plus_four\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 695 | 2021\|IL\|zip_plus_four\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 2125 | 2021\|IN\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 54 | 2021\|IN\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5228 | 2021\|IN\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2021\|IN\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 108 | 2021\|IN\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2021\|IN\|zip_plus_four\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 338 | 2021\|IN\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2021\|Il\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|In\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 663 | 2021\|KS\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 12 | 2021\|KS\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2481 | 2021\|KS\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|KS\|invalid\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 31 | 2021\|KS\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 146 | 2021\|KS\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1910 | 2021\|KY\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 49 | 2021\|KY\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3076 | 2021\|KY\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|KY\|invalid\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 91 | 2021\|KY\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2021\|KY\|zip_plus_four\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 164 | 2021\|KY\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 896 | 2021\|LA\|five_digit\|multiple |
| 0 | 0 | 0 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 41 | 2021\|LA\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3109 | 2021\|LA\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|LA\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|LA\|padded_four_digit\|single |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 75 | 2021\|LA\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|LA\|zip_plus_four\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 236 | 2021\|LA\|zip_plus_four\|single |
| 0 | 0 | 0 | 3 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 2021\|MA\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 38 | 2021\|MA\|five_digit\|none |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 23 | 2021\|MA\|five_digit\|single |
| 0 | 5 | 0 | 2 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 149 | 2021\|MA\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 507 | 2021\|MA\|padded_four_digit\|multiple |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 50 | 2021\|MA\|padded_four_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5323 | 2021\|MA\|padded_four_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|MA\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 901 | 2021\|MD\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 16 | 2021\|MD\|five_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3329 | 2021\|MD\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|MD\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|MD\|padded_four_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 78 | 2021\|MD\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 241 | 2021\|MD\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2021\|ME\|five_digit\|none |
| 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2021\|ME\|five_digit\|single |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 35 | 2021\|ME\|invalid\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 14 | 2021\|ME\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2021\|ME\|padded_four_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1417 | 2021\|ME\|padded_four_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|MH\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|MH\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2252 | 2021\|MI\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 32 | 2021\|MI\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 7155 | 2021\|MI\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2021\|MI\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 124 | 2021\|MI\|zip_plus_four\|multiple |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 537 | 2021\|MI\|zip_plus_four\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 2981 | 2021\|MN\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 38 | 2021\|MN\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6370 | 2021\|MN\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2021\|MN\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 132 | 2021\|MN\|zip_plus_four\|multiple |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 298 | 2021\|MN\|zip_plus_four\|single |
| 0 | 5 | 0 | 0 | 2 | 0 | 1 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1467 | 2021\|MO\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 37 | 2021\|MO\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4115 | 2021\|MO\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|MO\|invalid\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 94 | 2021\|MO\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 247 | 2021\|MO\|zip_plus_four\|single |
| 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 7 | 7 | 7 | 7 | 7 | 7 | 2021\|MP\|five_digit\|single |
| 0 | 2 | 0 | 5 | 1 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 1089 | 2021\|MS\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 27 | 2021\|MS\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1416 | 2021\|MS\|five_digit\|single |
| 0 | 0 | 0 | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2021\|MS\|invalid\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 87 | 2021\|MS\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 111 | 2021\|MS\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 105 | 2021\|MT\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2021\|MT\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 798 | 2021\|MT\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|MT\|invalid\|none |
| 0 | 2 | 0 | 1 | 2 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 5 | 5 | 0 | 0 | 0 | 5 | 2021\|MT\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2021\|MT\|zip_plus_four\|none |
| 0 | 4 | 0 | 4 | 0 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 75 | 2021\|MT\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 6 | 6 | 6 | 0 | 6 | 0 | 6 | 2021\|Ma\|padded_four_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2021\|Mi\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2021\|Ms\|five_digit\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 4089 | 2021\|NC\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 106 | 2021\|NC\|five_digit\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6343 | 2021\|NC\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|NC\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 277 | 2021\|NC\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2021\|NC\|zip_plus_four\|none |
| 0 | 3 | 0 | 0 | 5 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 445 | 2021\|NC\|zip_plus_four\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 130 | 2021\|ND\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 3 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2021\|ND\|five_digit\|none |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 922 | 2021\|ND\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2021\|ND\|invalid\|none |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2 | 2 | 0 | 0 | 0 | 2 | 2021\|ND\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 42 | 2021\|ND\|zip_plus_four\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 666 | 2021\|NE\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 11 | 2021\|NE\|five_digit\|none |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1511 | 2021\|NE\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|NE\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 28 | 2021\|NE\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 84 | 2021\|NE\|zip_plus_four\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2021\|NH\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2021\|NH\|five_digit\|none |
| 0 | 0 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 6 | 6 | 0 | 6 | 0 | 6 | 2021\|NH\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 44 | 2021\|NH\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 129 | 2021\|NH\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 9 | 2021\|NH\|padded_four_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1487 | 2021\|NH\|padded_four_digit\|single |
| 0 | 0 | 0 | 2 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 2021\|NJ\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 15 | 2021\|NJ\|five_digit\|none |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 34 | 2021\|NJ\|five_digit\|single |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 184 | 2021\|NJ\|invalid\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1050 | 2021\|NJ\|padded_four_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 35 | 2021\|NJ\|padded_four_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5180 | 2021\|NJ\|padded_four_digit\|single |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 64 | 2021\|NM\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 16 | 2021\|NM\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1339 | 2021\|NM\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2021\|NM\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|NM\|padded_four_digit\|single |
| 0 | 2 | 0 | 2 | 3 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 7 | 7 | 0 | 0 | 0 | 7 | 2021\|NM\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 106 | 2021\|NM\|zip_plus_four\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 198 | 2021\|NV\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 19 | 2021\|NV\|five_digit\|none |
| 0 | 3 | 0 | 0 | 3 | 0 | 2 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3091 | 2021\|NV\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|NV\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|NV\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 12 | 2021\|NV\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 128 | 2021\|NV\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1678 | 2021\|NY\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 92 | 2021\|NY\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 10389 | 2021\|NY\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2021\|NY\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2021\|NY\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|NY\|padded_four_digit\|none |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 12 | 2021\|NY\|padded_four_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 135 | 2021\|NY\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|NY\|zip_plus_four\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 696 | 2021\|NY\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2021\|Ne\|five_digit\|multiple |
| 0 | 3 | 0 | 1 | 0 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2021\|Ne\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 3832 | 2021\|OH\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 113 | 2021\|OH\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 9320 | 2021\|OH\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2021\|OH\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|OH\|padded_four_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 204 | 2021\|OH\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|OH\|zip_plus_four\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 591 | 2021\|OH\|zip_plus_four\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1039 | 2021\|OK\|five_digit\|multiple |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 32 | 2021\|OK\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2133 | 2021\|OK\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|OK\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 64 | 2021\|OK\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 158 | 2021\|OK\|zip_plus_four\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 937 | 2021\|OR\|five_digit\|multiple |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 22 | 2021\|OR\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3904 | 2021\|OR\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|OR\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2021\|OR\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|OR\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 46 | 2021\|OR\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2021\|OR\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 185 | 2021\|OR\|zip_plus_four\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2021\|Ok\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2021\|Or\|five_digit\|multiple |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 3031 | 2021\|PA\|five_digit\|multiple |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 105 | 2021\|PA\|five_digit\|none |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 10010 | 2021\|PA\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2021\|PA\|invalid\|none |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2021\|PA\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2021\|PA\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2021\|PA\|padded_four_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 124 | 2021\|PA\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 3 | 2021\|PA\|zip_plus_four\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 622 | 2021\|PA\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2021\|PR\|five_digit\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|PR\|five_digit\|single |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 1400 | 2021\|PR\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2021\|PW\|five_digit\|multiple |
| 0 | 2 | 0 | 1 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2021\|Pa\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2021\|RI\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2021\|RI\|five_digit\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|RI\|five_digit\|single |
| 0 | 4 | 0 | 1 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 4 | 8 | 0 | 0 | 0 | 0 | 23 | 2021\|RI\|invalid\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 121 | 2021\|RI\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2021\|RI\|padded_four_digit\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 834 | 2021\|RI\|padded_four_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 2 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1436 | 2021\|SC\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 24 | 2021\|SC\|five_digit\|none |
| 0 | 4 | 0 | 2 | 1 | 0 | 1 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3207 | 2021\|SC\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|SC\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 87 | 2021\|SC\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2021\|SC\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 259 | 2021\|SC\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 4 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 349 | 2021\|SD\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 3 | 2021\|SD\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 686 | 2021\|SD\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 25 | 2021\|SD\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2021\|SD\|zip_plus_four\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 40 | 2021\|SD\|zip_plus_four\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 2393 | 2021\|TN\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 21 | 2021\|TN\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4229 | 2021\|TN\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|TN\|invalid\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 141 | 2021\|TN\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 300 | 2021\|TN\|zip_plus_four\|single |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 5359 | 2021\|TX\|five_digit\|multiple |
| 0 | 0 | 0 | 7 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 96 | 2021\|TX\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 17645 | 2021\|TX\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2021\|TX\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2021\|TX\|padded_four_digit\|multiple |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 287 | 2021\|TX\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1204 | 2021\|TX\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2021\|Tx\|five_digit\|single |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 206 | 2021\|UT\|five_digit\|multiple |
| 0 | 1 | 0 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 26 | 2021\|UT\|five_digit\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2780 | 2021\|UT\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|UT\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 13 | 2021\|UT\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 139 | 2021\|UT\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 3162 | 2021\|VA\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 25 | 2021\|VA\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4202 | 2021\|VA\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2021\|VA\|invalid\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 227 | 2021\|VA\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 259 | 2021\|VA\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|VI\|five_digit\|single |
| 0 | 1 | 0 | 6 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 51 | 2021\|VI\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|VI\|padded_four_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2021\|VT\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|VT\|five_digit\|none |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2021\|VT\|five_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 8 | 2021\|VT\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 62 | 2021\|VT\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2021\|VT\|padded_four_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 559 | 2021\|VT\|padded_four_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2021\|Va\|five_digit\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 434 | 2021\|WA\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 51 | 2021\|WA\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5617 | 2021\|WA\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|WA\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2021\|WA\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|WA\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 24 | 2021\|WA\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 345 | 2021\|WA\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2485 | 2021\|WI\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 50 | 2021\|WI\|five_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5208 | 2021\|WI\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|WI\|invalid\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 78 | 2021\|WI\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|WI\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 256 | 2021\|WI\|zip_plus_four\|single |
| 0 | 3 | 0 | 5 | 0 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 344 | 2021\|WV\|five_digit\|multiple |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 25 | 2021\|WV\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1036 | 2021\|WV\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2021\|WV\|invalid\|none |
| 0 | 4 | 0 | 4 | 0 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 23 | 2021\|WV\|zip_plus_four\|multiple |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 81 | 2021\|WV\|zip_plus_four\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 38 | 2021\|WY\|five_digit\|multiple |
| 0 | 3 | 0 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 19 | 2021\|WY\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 434 | 2021\|WY\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2021\|WY\|invalid\|none |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2021\|WY\|zip_plus_four\|multiple |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 30 | 2021\|WY\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|Wi\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|ga\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|ky\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|mn\|five_digit\|single |
| 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 134 | 2021\|nv\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2021\|ny\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2021\|tx\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2022\|AA\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|AA\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|AE\|five_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 17 | 2022\|AK\|five_digit\|multiple |
| 0 | 0 | 0 | 7 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 116 | 2022\|AK\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1252 | 2022\|AK\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|AK\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 17 | 2022\|AK\|zip_plus_four\|single |
| 0 | 4 | 0 | 4 | 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1396 | 2022\|AL\|five_digit\|multiple |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 35 | 2022\|AL\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3488 | 2022\|AL\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2022\|AL\|invalid\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 46 | 2022\|AL\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 108 | 2022\|AL\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|AP\|five_digit\|none |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2022\|AP\|five_digit\|single |
| 0 | 0 | 0 | 6 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 12 | 2022\|AP\|invalid\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 1054 | 2022\|AR\|five_digit\|multiple |
| 0 | 0 | 0 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 23 | 2022\|AR\|five_digit\|none |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2020 | 2022\|AR\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|AR\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 35 | 2022\|AR\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 46 | 2022\|AR\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|AS\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 202 | 2022\|AZ\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 70 | 2022\|AZ\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6549 | 2022\|AZ\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2022\|AZ\|invalid\|none |
| 0 | 3 | 0 | 0 | 1 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 4 | 4 | 0 | 0 | 0 | 4 | 2022\|AZ\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 190 | 2022\|AZ\|zip_plus_four\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|Ak\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2022\|Al\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|Al\|five_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2871 | 2022\|CA\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 229 | 2022\|CA\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 31571 | 2022\|CA\|five_digit\|single |
| 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2022\|CA\|invalid\|none |
| 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 5 | 0 | 5 | 0 | 5 | 2022\|CA\|padded_four_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 85 | 2022\|CA\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2022\|CA\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1278 | 2022\|CA\|zip_plus_four\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 5 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 2754 | 2022\|CO\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 30 | 2022\|CO\|five_digit\|none |
| 0 | 5 | 0 | 0 | 2 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3377 | 2022\|CO\|five_digit\|single |
| 0 | 1 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 4 | 0 | 0 | 0 | 0 | 4 | 2022\|CO\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|CO\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 80 | 2022\|CO\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 93 | 2022\|CO\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2022\|CT\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 43 | 2022\|CT\|five_digit\|none |
| 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 5 | 0 | 5 | 0 | 5 | 2022\|CT\|five_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 0 | 109 | 2022\|CT\|invalid\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 172 | 2022\|CT\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 26 | 2022\|CT\|padded_four_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4551 | 2022\|CT\|padded_four_digit\|single |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|CT\|zip_plus_four\|none |
| 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 0 | 0 | 2 | 2022\|Ca\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2022\|Ca\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2022\|Co\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2022\|DC\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2022\|DC\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 733 | 2022\|DC\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|DC\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|DC\|padded_four_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 19 | 2022\|DC\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 74 | 2022\|DE\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2022\|DE\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 883 | 2022\|DE\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|DE\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|DE\|padded_four_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 21 | 2022\|DE\|zip_plus_four\|single |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 1752 | 2022\|FL\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 6 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 79 | 2022\|FL\|five_digit\|none |
| 0 | 3 | 0 | 1 | 3 | 0 | 1 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 16127 | 2022\|FL\|five_digit\|single |
| 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2022\|FL\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|FL\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 73 | 2022\|FL\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 838 | 2022\|FL\|zip_plus_four\|single |
| 0 | 1 | 0 | 1 | 3 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 5 | 5 | 0 | 0 | 0 | 5 | 2022\|Fl\|five_digit\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 45 | 2022\|Fl\|five_digit\|single |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 4442 | 2022\|GA\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 52 | 2022\|GA\|five_digit\|none |
| 0 | 3 | 0 | 0 | 5 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5634 | 2022\|GA\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2022\|GA\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2022\|GA\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|GA\|padded_four_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 117 | 2022\|GA\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 195 | 2022\|GA\|zip_plus_four\|single |
| 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2022\|GU\|five_digit\|none |
| 0 | 1 | 0 | 5 | 2 | 3 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 52 | 2022\|GU\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 2022\|GU\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|Ga\|five_digit\|none |
| 0 | 2 | 0 | 0 | 1 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2022\|Ga\|five_digit\|single |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2022\|HI\|five_digit\|multiple |
| 0 | 1 | 0 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 8 | 2022\|HI\|five_digit\|none |
| 0 | 3 | 0 | 4 | 1 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1309 | 2022\|HI\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|HI\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|HI\|padded_four_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 43 | 2022\|HI\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1418 | 2022\|IA\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 21 | 2022\|IA\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3712 | 2022\|IA\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|IA\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|IA\|padded_four_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 30 | 2022\|IA\|zip_plus_four\|multiple |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 70 | 2022\|IA\|zip_plus_four\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 548 | 2022\|ID\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 17 | 2022\|ID\|five_digit\|none |
| 0 | 5 | 0 | 0 | 2 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1370 | 2022\|ID\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2022\|ID\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 19 | 2022\|ID\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 49 | 2022\|ID\|zip_plus_four\|single |
| 0 | 3 | 0 | 4 | 1 | 0 | 0 | 2 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 3281 | 2022\|IL\|five_digit\|multiple |
| 0 | 2 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 51 | 2022\|IL\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 11455 | 2022\|IL\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2022\|IL\|invalid\|none |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2022\|IL\|padded_four_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 73 | 2022\|IL\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|IL\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 373 | 2022\|IL\|zip_plus_four\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2415 | 2022\|IN\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 52 | 2022\|IN\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5778 | 2022\|IN\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2022\|IN\|invalid\|none |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 71 | 2022\|IN\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|IN\|zip_plus_four\|none |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 170 | 2022\|IN\|zip_plus_four\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|Il\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 692 | 2022\|KS\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 18 | 2022\|KS\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2635 | 2022\|KS\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|KS\|invalid\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 18 | 2022\|KS\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 84 | 2022\|KS\|zip_plus_four\|single |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 2145 | 2022\|KY\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 43 | 2022\|KY\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3534 | 2022\|KY\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|KY\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|KY\|padded_four_digit\|single |
| 0 | 4 | 0 | 2 | 1 | 0 | 1 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 44 | 2022\|KY\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 87 | 2022\|KY\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 0 | 0 | 1 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 897 | 2022\|LA\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 44 | 2022\|LA\|five_digit\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3266 | 2022\|LA\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|LA\|invalid\|none |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 19 | 2022\|LA\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|LA\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 77 | 2022\|LA\|zip_plus_four\|single |
| 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2022\|La\|five_digit\|single |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 2022\|MA\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 46 | 2022\|MA\|five_digit\|none |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 21 | 2022\|MA\|five_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 0 | 183 | 2022\|MA\|invalid\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 596 | 2022\|MA\|padded_four_digit\|multiple |
| 0 | 1 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 51 | 2022\|MA\|padded_four_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5958 | 2022\|MA\|padded_four_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|MA\|zip_plus_four\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 1117 | 2022\|MD\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 15 | 2022\|MD\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3989 | 2022\|MD\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2022\|MD\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2022\|MD\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2022\|MD\|padded_four_digit\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 41 | 2022\|MD\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 139 | 2022\|MD\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2022\|ME\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2022\|ME\|five_digit\|none |
| 0 | 0 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 6 | 6 | 0 | 6 | 0 | 6 | 2022\|ME\|five_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 31 | 2022\|ME\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 19 | 2022\|ME\|padded_four_digit\|multiple |
| 0 | 1 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 9 | 2022\|ME\|padded_four_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1751 | 2022\|ME\|padded_four_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|MH\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2022\|MH\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|MH\|padded_four_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2766 | 2022\|MI\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 34 | 2022\|MI\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8504 | 2022\|MI\|five_digit\|single |
| 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2022\|MI\|invalid\|none |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2022\|MI\|padded_four_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 88 | 2022\|MI\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 338 | 2022\|MI\|zip_plus_four\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 3515 | 2022\|MN\|five_digit\|multiple |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 37 | 2022\|MN\|five_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 7479 | 2022\|MN\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2022\|MN\|invalid\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 154 | 2022\|MN\|zip_plus_four\|multiple |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 304 | 2022\|MN\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1662 | 2022\|MO\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 40 | 2022\|MO\|five_digit\|none |
| 0 | 6 | 0 | 0 | 1 | 0 | 1 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4604 | 2022\|MO\|five_digit\|single |
| 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2022\|MO\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|MO\|padded_four_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 48 | 2022\|MO\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 140 | 2022\|MO\|zip_plus_four\|single |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 10 | 2022\|MP\|five_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1181 | 2022\|MS\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 31 | 2022\|MS\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1527 | 2022\|MS\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|MS\|invalid\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 29 | 2022\|MS\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 33 | 2022\|MS\|zip_plus_four\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 112 | 2022\|MT\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 12 | 2022\|MT\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 897 | 2022\|MT\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|MT\|invalid\|none |
| 0 | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 4 | 4 | 0 | 0 | 0 | 4 | 2022\|MT\|zip_plus_four\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 38 | 2022\|MT\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 6 | 6 | 6 | 0 | 6 | 0 | 6 | 2022\|Ma\|padded_four_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2022\|Mi\|five_digit\|multiple |
| 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2022\|Mi\|five_digit\|single |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2022\|Ms\|five_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 4798 | 2022\|NC\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 115 | 2022\|NC\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 7323 | 2022\|NC\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2022\|NC\|invalid\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 150 | 2022\|NC\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2022\|NC\|zip_plus_four\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 235 | 2022\|NC\|zip_plus_four\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 140 | 2022\|ND\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 7 | 2022\|ND\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1057 | 2022\|ND\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|ND\|invalid\|none |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2022\|ND\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 26 | 2022\|ND\|zip_plus_four\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 747 | 2022\|NE\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 14 | 2022\|NE\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1581 | 2022\|NE\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2022\|NE\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2022\|NE\|padded_four_digit\|multiple |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 23 | 2022\|NE\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 38 | 2022\|NE\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2022\|NH\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|NH\|five_digit\|none |
| 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2022\|NH\|five_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 0 | 41 | 2022\|NH\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 130 | 2022\|NH\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 10 | 2022\|NH\|padded_four_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1740 | 2022\|NH\|padded_four_digit\|single |
| 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 2022\|NJ\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 89 | 2022\|NJ\|five_digit\|none |
| 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 33 | 2022\|NJ\|five_digit\|single |
| 0 | 4 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 8 | 0 | 0 | 0 | 0 | 198 | 2022\|NJ\|invalid\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1170 | 2022\|NJ\|padded_four_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 34 | 2022\|NJ\|padded_four_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5706 | 2022\|NJ\|padded_four_digit\|single |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 77 | 2022\|NM\|five_digit\|multiple |
| 0 | 3 | 0 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 12 | 2022\|NM\|five_digit\|none |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1518 | 2022\|NM\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2022\|NM\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|NM\|padded_four_digit\|single |
| 0 | 1 | 0 | 2 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 3 | 3 | 0 | 0 | 0 | 3 | 2022\|NM\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 39 | 2022\|NM\|zip_plus_four\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 230 | 2022\|NV\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 13 | 2022\|NV\|five_digit\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2818 | 2022\|NV\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|NV\|invalid\|none |
| 0 | 4 | 0 | 2 | 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 6 | 6 | 0 | 0 | 0 | 6 | 2022\|NV\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|NV\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 72 | 2022\|NV\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1898 | 2022\|NY\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 6 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 115 | 2022\|NY\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 12283 | 2022\|NY\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2022\|NY\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2022\|NY\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8 | 2022\|NY\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 72 | 2022\|NY\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 2 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2022\|NY\|zip_plus_four\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 420 | 2022\|NY\|zip_plus_four\|single |
| 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2022\|Ne\|five_digit\|single |
| 0 | 6 | 0 | 1 | 0 | 0 | 1 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 4276 | 2022\|OH\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 107 | 2022\|OH\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 10366 | 2022\|OH\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2022\|OH\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|OH\|padded_four_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 123 | 2022\|OH\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|OH\|zip_plus_four\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 298 | 2022\|OH\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1116 | 2022\|OK\|five_digit\|multiple |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 35 | 2022\|OK\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2311 | 2022\|OK\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|OK\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|OK\|padded_four_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 41 | 2022\|OK\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 74 | 2022\|OK\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1107 | 2022\|OR\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 22 | 2022\|OR\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4469 | 2022\|OR\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|OR\|invalid\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 27 | 2022\|OR\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 126 | 2022\|OR\|zip_plus_four\|single |
| 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2022\|Ok\|five_digit\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 3345 | 2022\|PA\|five_digit\|multiple |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 105 | 2022\|PA\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 11173 | 2022\|PA\|five_digit\|single |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2022\|PA\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|PA\|padded_four_digit\|none |
| 0 | 0 | 0 | 2 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 5 | 0 | 5 | 0 | 5 | 2022\|PA\|padded_four_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 78 | 2022\|PA\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 5 | 2022\|PA\|zip_plus_four\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 354 | 2022\|PA\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|PR\|five_digit\|single |
| 0 | 0 | 0 | 7 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 1332 | 2022\|PR\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|PR\|padded_four_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2022\|PW\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|PW\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|PW\|invalid\|none |
| 0 | 1 | 0 | 2 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2022\|Pa\|five_digit\|single |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2022\|RI\|five_digit\|none |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2022\|RI\|five_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 8 | 0 | 0 | 0 | 0 | 17 | 2022\|RI\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 129 | 2022\|RI\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 7 | 2022\|RI\|padded_four_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 827 | 2022\|RI\|padded_four_digit\|single |
| 0 | 6 | 0 | 0 | 1 | 0 | 1 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1576 | 2022\|SC\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 26 | 2022\|SC\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3551 | 2022\|SC\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2022\|SC\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 45 | 2022\|SC\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 121 | 2022\|SC\|zip_plus_four\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 429 | 2022\|SD\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 7 | 2022\|SD\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 796 | 2022\|SD\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|SD\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 12 | 2022\|SD\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|SD\|zip_plus_four\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 24 | 2022\|SD\|zip_plus_four\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 2644 | 2022\|TN\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 28 | 2022\|TN\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4687 | 2022\|TN\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2022\|TN\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 66 | 2022\|TN\|zip_plus_four\|multiple |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 147 | 2022\|TN\|zip_plus_four\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 6027 | 2022\|TX\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 104 | 2022\|TX\|five_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 19538 | 2022\|TX\|five_digit\|single |
| 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 5 | 2022\|TX\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|TX\|padded_four_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 138 | 2022\|TX\|zip_plus_four\|multiple |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 604 | 2022\|TX\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2022\|Tx\|five_digit\|single |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 259 | 2022\|UT\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 19 | 2022\|UT\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2687 | 2022\|UT\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|UT\|invalid\|none |
| 0 | 3 | 0 | 0 | 1 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 4 | 4 | 0 | 0 | 0 | 4 | 2022\|UT\|zip_plus_four\|multiple |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 70 | 2022\|UT\|zip_plus_four\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 3530 | 2022\|VA\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 36 | 2022\|VA\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4780 | 2022\|VA\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2022\|VA\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 5 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 119 | 2022\|VA\|zip_plus_four\|multiple |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|VA\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 157 | 2022\|VA\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2022\|VI\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 3 | 3 | 0 | 3 | 0 | 3 | 2022\|VI\|five_digit\|single |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 46 | 2022\|VI\|invalid\|none |
| 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2022\|VT\|five_digit\|none |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2022\|VT\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 13 | 2022\|VT\|invalid\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 62 | 2022\|VT\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2022\|VT\|padded_four_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 645 | 2022\|VT\|padded_four_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 474 | 2022\|WA\|five_digit\|multiple |
| 0 | 2 | 0 | 0 | 4 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 51 | 2022\|WA\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6563 | 2022\|WA\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2022\|WA\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2022\|WA\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|WA\|padded_four_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 17 | 2022\|WA\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|WA\|zip_plus_four\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 276 | 2022\|WA\|zip_plus_four\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 2604 | 2022\|WI\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 52 | 2022\|WI\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5587 | 2022\|WI\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|WI\|invalid\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 53 | 2022\|WI\|zip_plus_four\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|WI\|zip_plus_four\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 135 | 2022\|WI\|zip_plus_four\|single |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 2 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 361 | 2022\|WV\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 27 | 2022\|WV\|five_digit\|none |
| 0 | 3 | 0 | 2 | 2 | 0 | 1 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1191 | 2022\|WV\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2022\|WV\|invalid\|none |
| 0 | 3 | 0 | 5 | 0 | 0 | 0 | 2 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 11 | 2022\|WV\|zip_plus_four\|multiple |
| 0 | 3 | 0 | 4 | 1 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 35 | 2022\|WV\|zip_plus_four\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 48 | 2022\|WY\|five_digit\|multiple |
| 0 | 1 | 0 | 6 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 21 | 2022\|WY\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 517 | 2022\|WY\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2022\|WY\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2022\|WY\|zip_plus_four\|multiple |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 12 | 2022\|WY\|zip_plus_four\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|Wi\|five_digit\|single |
| 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2022\|ca\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|fl\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|ga\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|ky\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 2022\|ny\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|oh\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|tx\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2022\|wv\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2023\|AA\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2023\|AA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2023\|AE\|five_digit\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2023\|AE\|five_digit\|single |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 18 | 2023\|AK\|five_digit\|multiple |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 155 | 2023\|AK\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1595 | 2023\|AK\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 22 | 2023\|AK\|invalid\|none |
| 0 | 2 | 0 | 5 | 0 | 0 | 1 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 1542 | 2023\|AL\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 21 | 2023\|AL\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3796 | 2023\|AL\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 253 | 2023\|AL\|invalid\|none |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 0 | 2 | 2023\|AP\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2023\|AP\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1146 | 2023\|AR\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 27 | 2023\|AR\|five_digit\|none |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2177 | 2023\|AR\|five_digit\|single |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 149 | 2023\|AR\|invalid\|none |
| 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2023\|AS\|five_digit\|none |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 2 | 0 | 2 | 0 | 2 | 2023\|AS\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 239 | 2023\|AZ\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 78 | 2023\|AZ\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 7435 | 2023\|AZ\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 261 | 2023\|AZ\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 3327 | 2023\|CA\|five_digit\|multiple |
| 0 | 1 | 0 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 241 | 2023\|CA\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 35783 | 2023\|CA\|five_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 0 | 1552 | 2023\|CA\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 3099 | 2023\|CO\|five_digit\|multiple |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 38 | 2023\|CO\|five_digit\|none |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3839 | 2023\|CO\|five_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 215 | 2023\|CO\|invalid\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 195 | 2023\|CT\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 47 | 2023\|CT\|five_digit\|none |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5064 | 2023\|CT\|five_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 0 | 134 | 2023\|CT\|invalid\|none |
| 0 | 0 | 0 | 2 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 2 | 0 | 0 | 5 | 2023\|DC\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2023\|DC\|five_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 793 | 2023\|DC\|five_digit\|single |
| 0 | 6 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 40 | 2023\|DC\|invalid\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 5 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 81 | 2023\|DE\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 7 | 2023\|DE\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1075 | 2023\|DE\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 0 | 41 | 2023\|DE\|invalid\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1965 | 2023\|FL\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 129 | 2023\|FL\|five_digit\|none |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 18065 | 2023\|FL\|five_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 8 | 0 | 0 | 0 | 0 | 1282 | 2023\|FL\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2023\|FM\|five_digit\|multiple |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 4907 | 2023\|GA\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 55 | 2023\|GA\|five_digit\|none |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6266 | 2023\|GA\|five_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 0 | 427 | 2023\|GA\|invalid\|none |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2023\|GU\|five_digit\|multiple |
| 0 | 0 | 0 | 7 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2023\|GU\|five_digit\|none |
| 0 | 1 | 0 | 6 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 7 | 8 | 7 | 68 | 2023\|GU\|five_digit\|single |
| 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2023\|GU\|invalid\|none |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 13 | 2023\|HI\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1536 | 2023\|HI\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 45 | 2023\|HI\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1580 | 2023\|IA\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 21 | 2023\|IA\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4073 | 2023\|IA\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 131 | 2023\|IA\|invalid\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 665 | 2023\|ID\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 23 | 2023\|ID\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1617 | 2023\|ID\|five_digit\|single |
| 0 | 5 | 0 | 1 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 85 | 2023\|ID\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 3632 | 2023\|IL\|five_digit\|multiple |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 0 | 51 | 2023\|IL\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 12719 | 2023\|IL\|five_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 606 | 2023\|IL\|invalid\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 2704 | 2023\|IN\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 59 | 2023\|IN\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6410 | 2023\|IN\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 405 | 2023\|IN\|invalid\|none |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 814 | 2023\|KS\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 15 | 2023\|KS\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3156 | 2023\|KS\|five_digit\|single |
| 0 | 5 | 0 | 0 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 142 | 2023\|KS\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2383 | 2023\|KY\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 47 | 2023\|KY\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3862 | 2023\|KY\|five_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 208 | 2023\|KY\|invalid\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1006 | 2023\|LA\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 45 | 2023\|LA\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3669 | 2023\|LA\|five_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 0 | 137 | 2023\|LA\|invalid\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 694 | 2023\|MA\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 87 | 2023\|MA\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 7026 | 2023\|MA\|five_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 233 | 2023\|MA\|invalid\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 1218 | 2023\|MD\|five_digit\|multiple |
| 0 | 2 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 17 | 2023\|MD\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4419 | 2023\|MD\|five_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 0 | 202 | 2023\|MD\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 20 | 2023\|ME\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 17 | 2023\|ME\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1882 | 2023\|ME\|five_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 49 | 2023\|ME\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2023\|MH\|five_digit\|multiple |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 3129 | 2023\|MI\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 6 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 49 | 2023\|MI\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 9610 | 2023\|MI\|five_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 613 | 2023\|MI\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 3895 | 2023\|MN\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 39 | 2023\|MN\|five_digit\|none |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8427 | 2023\|MN\|five_digit\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 8 | 0 | 0 | 0 | 0 | 404 | 2023\|MN\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1883 | 2023\|MO\|five_digit\|multiple |
| 0 | 1 | 0 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 37 | 2023\|MO\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5188 | 2023\|MO\|five_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 270 | 2023\|MO\|invalid\|none |
| 0 | 0 | 0 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 6 | 8 | 6 | 13 | 2023\|MP\|five_digit\|single |
| 0 | 4 | 0 | 2 | 1 | 0 | 1 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1272 | 2023\|MS\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 34 | 2023\|MS\|five_digit\|none |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1629 | 2023\|MS\|five_digit\|single |
| 0 | 3 | 0 | 1 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 89 | 2023\|MS\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 158 | 2023\|MT\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 12 | 2023\|MT\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1091 | 2023\|MT\|five_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 42 | 2023\|MT\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 5354 | 2023\|NC\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 115 | 2023\|NC\|five_digit\|none |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8021 | 2023\|NC\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 478 | 2023\|NC\|invalid\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 2 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 177 | 2023\|ND\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2023\|ND\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1190 | 2023\|ND\|five_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 0 | 42 | 2023\|ND\|invalid\|none |
| 0 | 1 | 0 | 0 | 7 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 8 | 8 | 0 | 0 | 0 | 874 | 2023\|NE\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 14 | 2023\|NE\|five_digit\|none |
| 0 | 3 | 0 | 4 | 1 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1864 | 2023\|NE\|five_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 0 | 99 | 2023\|NE\|invalid\|none |
| 0 | 3 | 0 | 2 | 2 | 0 | 1 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 148 | 2023\|NH\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 13 | 2023\|NH\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1871 | 2023\|NH\|five_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 0 | 59 | 2023\|NH\|invalid\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 1450 | 2023\|NJ\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 80 | 2023\|NJ\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 7202 | 2023\|NJ\|five_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 0 | 244 | 2023\|NJ\|invalid\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 83 | 2023\|NM\|five_digit\|multiple |
| 0 | 2 | 0 | 5 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 23 | 2023\|NM\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1746 | 2023\|NM\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 57 | 2023\|NM\|invalid\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 2 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 275 | 2023\|NV\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 22 | 2023\|NV\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3341 | 2023\|NV\|five_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 111 | 2023\|NV\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2135 | 2023\|NY\|five_digit\|multiple |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 114 | 2023\|NY\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 13720 | 2023\|NY\|five_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 0 | 546 | 2023\|NY\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 4902 | 2023\|OH\|five_digit\|multiple |
| 0 | 0 | 0 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 111 | 2023\|OH\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 11479 | 2023\|OH\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 0 | 616 | 2023\|OH\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1292 | 2023\|OK\|five_digit\|multiple |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 40 | 2023\|OK\|five_digit\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2649 | 2023\|OK\|five_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 0 | 164 | 2023\|OK\|invalid\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1315 | 2023\|OR\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 6 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 39 | 2023\|OR\|five_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5276 | 2023\|OR\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 188 | 2023\|OR\|invalid\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 3766 | 2023\|PA\|five_digit\|multiple |
| 0 | 3 | 0 | 2 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 108 | 2023\|PA\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 12615 | 2023\|PA\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 620 | 2023\|PA\|invalid\|none |
| 0 | 1 | 0 | 7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 0 | 0 | 721 | 2023\|PR\|five_digit\|multiple |
| 0 | 0 | 0 | 7 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 13 | 2023\|PR\|five_digit\|none |
| 0 | 0 | 0 | 7 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 7 | 8 | 7 | 800 | 2023\|PR\|five_digit\|single |
| 0 | 0 | 0 | 5 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 36 | 2023\|PR\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 1 | 2023\|PW\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 167 | 2023\|RI\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 14 | 2023\|RI\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1011 | 2023\|RI\|five_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 38 | 2023\|RI\|invalid\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1824 | 2023\|SC\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 25 | 2023\|SC\|five_digit\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4115 | 2023\|SC\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 228 | 2023\|SC\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 519 | 2023\|SD\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 6 | 2023\|SD\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 976 | 2023\|SD\|five_digit\|single |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 60 | 2023\|SD\|invalid\|none |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 2904 | 2023\|TN\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 31 | 2023\|TN\|five_digit\|none |
| 0 | 2 | 0 | 2 | 3 | 0 | 1 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5228 | 2023\|TN\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 310 | 2023\|TN\|invalid\|none |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 6883 | 2023\|TX\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 113 | 2023\|TX\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 21576 | 2023\|TX\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 0 | 1205 | 2023\|TX\|invalid\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 267 | 2023\|UT\|five_digit\|multiple |
| 0 | 0 | 0 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 26 | 2023\|UT\|five_digit\|none |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3097 | 2023\|UT\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 118 | 2023\|UT\|invalid\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 4046 | 2023\|VA\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 62 | 2023\|VA\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5516 | 2023\|VA\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 0 | 384 | 2023\|VA\|invalid\|none |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 2023\|VI\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2023\|VI\|five_digit\|none |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 54 | 2023\|VI\|five_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2023\|VI\|invalid\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 71 | 2023\|VT\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 11 | 2023\|VT\|five_digit\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 719 | 2023\|VT\|five_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 18 | 2023\|VT\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 603 | 2023\|WA\|five_digit\|multiple |
| 0 | 0 | 0 | 7 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 70 | 2023\|WA\|five_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 7938 | 2023\|WA\|five_digit\|single |
| 0 | 4 | 0 | 1 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 4 | 8 | 0 | 0 | 0 | 0 | 338 | 2023\|WA\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2835 | 2023\|WI\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 60 | 2023\|WI\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6324 | 2023\|WI\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 300 | 2023\|WI\|invalid\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 408 | 2023\|WV\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 30 | 2023\|WV\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1315 | 2023\|WV\|five_digit\|single |
| 0 | 3 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 93 | 2023\|WV\|invalid\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 52 | 2023\|WY\|five_digit\|multiple |
| 0 | 1 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 23 | 2023\|WY\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 671 | 2023\|WY\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 8 | 0 | 0 | 0 | 0 | 24 | 2023\|WY\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2024\|AA\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2024\|AA\|five_digit\|none |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2024\|AA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|AE\|five_digit\|none |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 2 | 2 | 1 | 2 | 1 | 2 | 2024\|AE\|five_digit\|single |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 8 | 8 | 0 | 0 | 0 | 21 | 2024\|AK\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 118 | 2024\|AK\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1628 | 2024\|AK\|five_digit\|single |
| 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|AK\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1643 | 2024\|AL\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 39 | 2024\|AL\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4161 | 2024\|AL\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2024\|AL\|padded_four_digit\|single |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2024\|AP\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|AP\|invalid\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1246 | 2024\|AR\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 26 | 2024\|AR\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2279 | 2024\|AR\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2024\|AS\|five_digit\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 1 | 0 | 1 | 2024\|AS\|five_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 237 | 2024\|AZ\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 81 | 2024\|AZ\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 7750 | 2024\|AZ\|five_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 7 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 3330 | 2024\|CA\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 226 | 2024\|CA\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 36887 | 2024\|CA\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|CA\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|CA\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2024\|CA\|padded_four_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 3166 | 2024\|CO\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 41 | 2024\|CO\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4033 | 2024\|CO\|five_digit\|single |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2024\|CO\|padded_four_digit\|single |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 2024\|CT\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 15 | 2024\|CT\|five_digit\|none |
| 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8 | 2024\|CT\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|CT\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 202 | 2024\|CT\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 24 | 2024\|CT\|padded_four_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5176 | 2024\|CT\|padded_four_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2024\|DC\|five_digit\|multiple |
| 0 | 0 | 0 | 7 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2024\|DC\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 840 | 2024\|DC\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|DC\|padded_four_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 92 | 2024\|DE\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 7 | 2024\|DE\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1074 | 2024\|DE\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|DE\|padded_four_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2135 | 2024\|FL\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 122 | 2024\|FL\|five_digit\|none |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 19395 | 2024\|FL\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2024\|FL\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|FL\|padded_four_digit\|none |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2024\|FL\|padded_four_digit\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 5331 | 2024\|GA\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 57 | 2024\|GA\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6572 | 2024\|GA\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|GA\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2024\|GA\|padded_four_digit\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2024\|GU\|five_digit\|multiple |
| 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2024\|GU\|five_digit\|none |
| 0 | 1 | 0 | 6 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 71 | 2024\|GU\|five_digit\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2024\|HI\|five_digit\|multiple |
| 0 | 1 | 0 | 5 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 7 | 2024\|HI\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1687 | 2024\|HI\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1639 | 2024\|IA\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 24 | 2024\|IA\|five_digit\|none |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4183 | 2024\|IA\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|IA\|padded_four_digit\|none |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 739 | 2024\|ID\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 19 | 2024\|ID\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1686 | 2024\|ID\|five_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 3694 | 2024\|IL\|five_digit\|multiple |
| 0 | 2 | 0 | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 50 | 2024\|IL\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 13084 | 2024\|IL\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|IL\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2929 | 2024\|IN\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 65 | 2024\|IN\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 7050 | 2024\|IN\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2024\|IN\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2024\|IN\|padded_four_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 834 | 2024\|KS\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 15 | 2024\|KS\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3323 | 2024\|KS\|five_digit\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2024\|KS\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2464 | 2024\|KY\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 37 | 2024\|KY\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4047 | 2024\|KY\|five_digit\|single |
| 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 2 | 2024\|KY\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2024\|KY\|padded_four_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1098 | 2024\|LA\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 39 | 2024\|LA\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3957 | 2024\|LA\|five_digit\|single |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2024\|LA\|padded_four_digit\|single |
| 0 | 0 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 2024\|MA\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 15 | 2024\|MA\|five_digit\|none |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 34 | 2024\|MA\|five_digit\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 698 | 2024\|MA\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 56 | 2024\|MA\|padded_four_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 7232 | 2024\|MA\|padded_four_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1239 | 2024\|MD\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 21 | 2024\|MD\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4549 | 2024\|MD\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|MD\|padded_four_digit\|none |
| 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2024\|MD\|padded_four_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2024\|ME\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2024\|ME\|five_digit\|none |
| 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8 | 2024\|ME\|five_digit\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2024\|ME\|invalid\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 22 | 2024\|ME\|padded_four_digit\|multiple |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 13 | 2024\|ME\|padded_four_digit\|none |
| 0 | 5 | 0 | 0 | 2 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1947 | 2024\|ME\|padded_four_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2024\|MH\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2024\|MH\|padded_four_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 3282 | 2024\|MI\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 47 | 2024\|MI\|five_digit\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 10596 | 2024\|MI\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|MI\|invalid\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 3963 | 2024\|MN\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 50 | 2024\|MN\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8457 | 2024\|MN\|five_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2094 | 2024\|MO\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 38 | 2024\|MO\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5781 | 2024\|MO\|five_digit\|single |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 15 | 2024\|MP\|five_digit\|single |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1399 | 2024\|MS\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 3 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 34 | 2024\|MS\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1813 | 2024\|MS\|five_digit\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2024\|MS\|padded_four_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 166 | 2024\|MT\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 12 | 2024\|MT\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1136 | 2024\|MT\|five_digit\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2024\|MT\|padded_four_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 5632 | 2024\|NC\|five_digit\|multiple |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 110 | 2024\|NC\|five_digit\|none |
| 0 | 3 | 0 | 3 | 2 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8598 | 2024\|NC\|five_digit\|single |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2024\|NC\|padded_four_digit\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 177 | 2024\|ND\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 7 | 2024\|ND\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1204 | 2024\|ND\|five_digit\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 902 | 2024\|NE\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 11 | 2024\|NE\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2038 | 2024\|NE\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2024\|NE\|padded_four_digit\|single |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 2024\|NH\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2024\|NH\|five_digit\|none |
| 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 4 | 0 | 4 | 2024\|NH\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|NH\|invalid\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 166 | 2024\|NH\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 10 | 2024\|NH\|padded_four_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1853 | 2024\|NH\|padded_four_digit\|single |
| 0 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 2024\|NJ\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 26 | 2024\|NJ\|five_digit\|none |
| 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 27 | 2024\|NJ\|five_digit\|single |
| 0 | 1 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 3 | 0 | 0 | 0 | 0 | 3 | 2024\|NJ\|invalid\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 5 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 1515 | 2024\|NJ\|padded_four_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 53 | 2024\|NJ\|padded_four_digit\|none |
| 0 | 5 | 0 | 2 | 0 | 0 | 1 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 7097 | 2024\|NJ\|padded_four_digit\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 90 | 2024\|NM\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 23 | 2024\|NM\|five_digit\|none |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1853 | 2024\|NM\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2024\|NM\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2024\|NM\|padded_four_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 279 | 2024\|NV\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 27 | 2024\|NV\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3562 | 2024\|NV\|five_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2256 | 2024\|NY\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 120 | 2024\|NY\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 14222 | 2024\|NY\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|NY\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2024\|NY\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|NY\|padded_four_digit\|none |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8 | 2024\|NY\|padded_four_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 4962 | 2024\|OH\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 129 | 2024\|OH\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 11721 | 2024\|OH\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2024\|OH\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|OH\|padded_four_digit\|none |
| 0 | 0 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2024\|OH\|padded_four_digit\|single |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 2 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 1380 | 2024\|OK\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 35 | 2024\|OK\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2760 | 2024\|OK\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|OK\|padded_four_digit\|none |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2024\|OK\|padded_four_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1394 | 2024\|OR\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 28 | 2024\|OR\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5447 | 2024\|OR\|five_digit\|single |
| 0 | 0 | 0 | 7 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2024\|OR\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2024\|OR\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2024\|OR\|padded_four_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 3747 | 2024\|PA\|five_digit\|multiple |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 112 | 2024\|PA\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 13154 | 2024\|PA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|PA\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2024\|PA\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2024\|PA\|padded_four_digit\|none |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 13 | 2024\|PA\|padded_four_digit\|single |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2024\|PR\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2024\|PR\|five_digit\|none |
| 0 | 0 | 0 | 3 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 5 | 5 | 0 | 5 | 0 | 5 | 2024\|PR\|five_digit\|single |
| 0 | 1 | 0 | 7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 1573 | 2024\|PR\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2024\|PW\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|PW\|invalid\|none |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2024\|RI\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 4 | 2024\|RI\|five_digit\|none |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2024\|RI\|five_digit\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 170 | 2024\|RI\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2024\|RI\|padded_four_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1064 | 2024\|RI\|padded_four_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2023 | 2024\|SC\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 28 | 2024\|SC\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4462 | 2024\|SC\|five_digit\|single |
| 0 | 0 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2024\|SC\|padded_four_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 536 | 2024\|SD\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 10 | 2024\|SD\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 983 | 2024\|SD\|five_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 3181 | 2024\|TN\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 27 | 2024\|TN\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5574 | 2024\|TN\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2024\|TN\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 7274 | 2024\|TX\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 134 | 2024\|TX\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 23690 | 2024\|TX\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|TX\|padded_four_digit\|none |
| 0 | 0 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 7 | 7 | 0 | 7 | 0 | 7 | 2024\|TX\|padded_four_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 283 | 2024\|UT\|five_digit\|multiple |
| 0 | 2 | 0 | 5 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 25 | 2024\|UT\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3231 | 2024\|UT\|five_digit\|single |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 4299 | 2024\|VA\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 63 | 2024\|VA\|five_digit\|none |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5610 | 2024\|VA\|five_digit\|single |
| 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 3 | 0 | 3 | 0 | 3 | 2024\|VA\|padded_four_digit\|single |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2024\|VI\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 2 | 0 | 2 | 0 | 2 | 2024\|VI\|five_digit\|single |
| 0 | 0 | 0 | 7 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 51 | 2024\|VI\|invalid\|none |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2024\|VT\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2024\|VT\|five_digit\|none |
| 0 | 0 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 6 | 6 | 0 | 6 | 0 | 6 | 2024\|VT\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 80 | 2024\|VT\|padded_four_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2024\|VT\|padded_four_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 738 | 2024\|VT\|padded_four_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 615 | 2024\|WA\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 59 | 2024\|WA\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8139 | 2024\|WA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2024\|WA\|invalid\|none |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2024\|WA\|padded_four_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2923 | 2024\|WI\|five_digit\|multiple |
| 0 | 3 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 55 | 2024\|WI\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6623 | 2024\|WI\|five_digit\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 477 | 2024\|WV\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 33 | 2024\|WV\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1427 | 2024\|WV\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2024\|WV\|padded_four_digit\|single |
| 0 | 3 | 0 | 0 | 5 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 54 | 2024\|WY\|five_digit\|multiple |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 24 | 2024\|WY\|five_digit\|none |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 702 | 2024\|WY\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2025\|AA\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 0 | 2 | 0 | 2 | 2025\|AA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2025\|AE\|five_digit\|single |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 14 | 2025\|AK\|five_digit\|multiple |
| 0 | 2 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 131 | 2025\|AK\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1672 | 2025\|AK\|five_digit\|single |
| 0 | 2 | 0 | 4 | 2 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 8 | 8 | 0 | 0 | 0 | 1633 | 2025\|AL\|five_digit\|multiple |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 33 | 2025\|AL\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4034 | 2025\|AL\|five_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1219 | 2025\|AR\|five_digit\|multiple |
| 0 | 1 | 0 | 5 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 31 | 2025\|AR\|five_digit\|none |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2259 | 2025\|AR\|five_digit\|single |
| 0 | 0 | 0 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2025\|AS\|five_digit\|none |
| 0 | 0 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 3 | 3 | 0 | 3 | 0 | 3 | 2025\|AS\|five_digit\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 236 | 2025\|AZ\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 64 | 2025\|AZ\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8164 | 2025\|AZ\|five_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 3417 | 2025\|CA\|five_digit\|multiple |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 241 | 2025\|CA\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 40221 | 2025\|CA\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 3202 | 2025\|CO\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 36 | 2025\|CO\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3974 | 2025\|CO\|five_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 183 | 2025\|CT\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 44 | 2025\|CT\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5093 | 2025\|CT\|five_digit\|single |
| 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 2 | 2025\|DC\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2025\|DC\|five_digit\|none |
| 0 | 6 | 0 | 0 | 1 | 0 | 1 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 880 | 2025\|DC\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 81 | 2025\|DE\|five_digit\|multiple |
| 0 | 2 | 0 | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 7 | 0 | 0 | 0 | 0 | 7 | 2025\|DE\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1099 | 2025\|DE\|five_digit\|single |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 2092 | 2025\|FL\|five_digit\|multiple |
| 0 | 0 | 0 | 0 | 7 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 131 | 2025\|FL\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 19031 | 2025\|FL\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 1 | 0 | 1 | 2025\|FM\|five_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 5219 | 2025\|GA\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 50 | 2025\|GA\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6606 | 2025\|GA\|five_digit\|single |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2025\|GU\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 6 | 0 | 0 | 0 | 0 | 6 | 2025\|GU\|five_digit\|none |
| 0 | 0 | 0 | 5 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 82 | 2025\|GU\|five_digit\|single |
| 0 | 1 | 0 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 6 | 2025\|HI\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2124 | 2025\|HI\|five_digit\|single |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 8 | 0 | 0 | 0 | 1619 | 2025\|IA\|five_digit\|multiple |
| 0 | 1 | 0 | 6 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 17 | 2025\|IA\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4328 | 2025\|IA\|five_digit\|single |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 773 | 2025\|ID\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 18 | 2025\|ID\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1715 | 2025\|ID\|five_digit\|single |
| 0 | 4 | 0 | 0 | 4 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 3795 | 2025\|IL\|five_digit\|multiple |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 51 | 2025\|IL\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 13221 | 2025\|IL\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 2846 | 2025\|IN\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 61 | 2025\|IN\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6848 | 2025\|IN\|five_digit\|single |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 783 | 2025\|KS\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 17 | 2025\|KS\|five_digit\|none |
| 0 | 3 | 0 | 0 | 5 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3154 | 2025\|KS\|five_digit\|single |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2391 | 2025\|KY\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 23 | 2025\|KY\|five_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3973 | 2025\|KY\|five_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 1027 | 2025\|LA\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 34 | 2025\|LA\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3915 | 2025\|LA\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 654 | 2025\|MA\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 70 | 2025\|MA\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6569 | 2025\|MA\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1173 | 2025\|MD\|five_digit\|multiple |
| 0 | 1 | 0 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 31 | 2025\|MD\|five_digit\|none |
| 0 | 5 | 0 | 3 | 0 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4472 | 2025\|MD\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 19 | 2025\|ME\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 16 | 2025\|ME\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1951 | 2025\|ME\|five_digit\|single |
| 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 2025\|MH\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2025\|MH\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 3207 | 2025\|MI\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 48 | 2025\|MI\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 10446 | 2025\|MI\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 4075 | 2025\|MN\|five_digit\|multiple |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 48 | 2025\|MN\|five_digit\|none |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8791 | 2025\|MN\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 2008 | 2025\|MO\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 33 | 2025\|MO\|five_digit\|none |
| 0 | 2 | 0 | 1 | 5 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5565 | 2025\|MO\|five_digit\|single |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 14 | 2025\|MP\|five_digit\|single |
| 0 | 5 | 0 | 2 | 0 | 0 | 1 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1324 | 2025\|MS\|five_digit\|multiple |
| 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 24 | 2025\|MS\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1658 | 2025\|MS\|five_digit\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 166 | 2025\|MT\|five_digit\|multiple |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 10 | 2025\|MT\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1125 | 2025\|MT\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 5636 | 2025\|NC\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 99 | 2025\|NC\|five_digit\|none |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8490 | 2025\|NC\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 176 | 2025\|ND\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 8 | 2025\|ND\|five_digit\|none |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 2 | 2 | 2 | 2 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1246 | 2025\|ND\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 881 | 2025\|NE\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 12 | 2025\|NE\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1965 | 2025\|NE\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 155 | 2025\|NH\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 18 | 2025\|NH\|five_digit\|none |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1809 | 2025\|NH\|five_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 1393 | 2025\|NJ\|five_digit\|multiple |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 89 | 2025\|NJ\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6635 | 2025\|NJ\|five_digit\|single |
| 0 | 1 | 0 | 3 | 4 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 8 | 8 | 0 | 0 | 0 | 107 | 2025\|NM\|five_digit\|multiple |
| 0 | 2 | 0 | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 18 | 2025\|NM\|five_digit\|none |
| 0 | 3 | 0 | 1 | 4 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1874 | 2025\|NM\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 259 | 2025\|NV\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 21 | 2025\|NV\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3606 | 2025\|NV\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 2171 | 2025\|NY\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 114 | 2025\|NY\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 14211 | 2025\|NY\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 5036 | 2025\|OH\|five_digit\|multiple |
| 0 | 0 | 0 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 128 | 2025\|OH\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 11858 | 2025\|OH\|five_digit\|single |
| 0 | 3 | 0 | 2 | 3 | 0 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 8 | 8 | 0 | 0 | 0 | 1332 | 2025\|OK\|five_digit\|multiple |
| 0 | 2 | 0 | 1 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 35 | 2025\|OK\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 2547 | 2025\|OK\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 5 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 1348 | 2025\|OR\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 39 | 2025\|OR\|five_digit\|none |
| 0 | 7 | 0 | 1 | 0 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5350 | 2025\|OR\|five_digit\|single |
| 0 | 5 | 0 | 0 | 3 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 3620 | 2025\|PA\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 124 | 2025\|PA\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 12539 | 2025\|PA\|five_digit\|single |
| 0 | 0 | 0 | 5 | 2 | 2 | 1 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 0 | 0 | 779 | 2025\|PR\|five_digit\|multiple |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 18 | 2025\|PR\|five_digit\|none |
| 0 | 0 | 0 | 7 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 965 | 2025\|PR\|five_digit\|single |
| 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 2 | 2 | 2 | 2 | 2 | 2025\|PW\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 167 | 2025\|RI\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 12 | 2025\|RI\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1024 | 2025\|RI\|five_digit\|single |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 6 | 7 | 0 | 0 | 0 | 7 | 8 | 8 | 0 | 0 | 0 | 1936 | 2025\|SC\|five_digit\|multiple |
| 0 | 0 | 0 | 1 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 19 | 2025\|SC\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 4359 | 2025\|SC\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 550 | 2025\|SD\|five_digit\|multiple |
| 0 | 1 | 0 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 10 | 2025\|SD\|five_digit\|none |
| 0 | 4 | 0 | 2 | 1 | 0 | 1 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 933 | 2025\|SD\|five_digit\|single |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 3147 | 2025\|TN\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 30 | 2025\|TN\|five_digit\|none |
| 0 | 6 | 0 | 0 | 2 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5505 | 2025\|TN\|five_digit\|single |
| 0 | 4 | 0 | 1 | 3 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 7998 | 2025\|TX\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 108 | 2025\|TX\|five_digit\|none |
| 0 | 4 | 0 | 1 | 2 | 0 | 1 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 24471 | 2025\|TX\|five_digit\|single |
| 0 | 5 | 0 | 0 | 2 | 0 | 1 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 302 | 2025\|UT\|five_digit\|multiple |
| 0 | 1 | 0 | 4 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 19 | 2025\|UT\|five_digit\|none |
| 0 | 4 | 0 | 3 | 1 | 0 | 0 | 4 | 4 | 4 | 4 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 3308 | 2025\|UT\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 4 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 4216 | 2025\|VA\|five_digit\|multiple |
| 0 | 2 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 62 | 2025\|VA\|five_digit\|none |
| 0 | 5 | 0 | 2 | 1 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 5634 | 2025\|VA\|five_digit\|single |
| 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 2025\|VI\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 3 | 0 | 0 | 0 | 0 | 3 | 2025\|VI\|five_digit\|none |
| 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 8 | 8 | 8 | 8 | 8 | 61 | 2025\|VI\|five_digit\|single |
| 0 | 6 | 0 | 1 | 1 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 78 | 2025\|VT\|five_digit\|multiple |
| 0 | 0 | 0 | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 14 | 2025\|VT\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 707 | 2025\|VT\|five_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 4 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 643 | 2025\|WA\|five_digit\|multiple |
| 0 | 0 | 0 | 2 | 5 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 72 | 2025\|WA\|five_digit\|none |
| 0 | 7 | 0 | 0 | 1 | 0 | 0 | 7 | 7 | 7 | 7 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 8664 | 2025\|WA\|five_digit\|single |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 8 | 8 | 0 | 0 | 0 | 2871 | 2025\|WI\|five_digit\|multiple |
| 0 | 1 | 0 | 1 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 8 | 0 | 0 | 0 | 0 | 57 | 2025\|WI\|five_digit\|none |
| 0 | 8 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 8 | 8 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 6618 | 2025\|WI\|five_digit\|single |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 6 | 8 | 8 | 0 | 0 | 0 | 444 | 2025\|WV\|five_digit\|multiple |
| 0 | 2 | 0 | 2 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 8 | 0 | 0 | 0 | 0 | 23 | 2025\|WV\|five_digit\|none |
| 0 | 6 | 0 | 2 | 0 | 0 | 0 | 6 | 6 | 6 | 6 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 1351 | 2025\|WV\|five_digit\|single |
| 0 | 4 | 0 | 2 | 2 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 4 | 8 | 8 | 0 | 0 | 0 | 47 | 2025\|WY\|five_digit\|multiple |
| 0 | 3 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 8 | 0 | 0 | 0 | 0 | 21 | 2025\|WY\|five_digit\|none |
| 0 | 5 | 0 | 1 | 2 | 0 | 0 | 5 | 5 | 5 | 5 | 0 | 8 | 8 | 8 | 0 | 8 | 0 | 644 | 2025\|WY\|five_digit\|single |

## Provenance audits and source layout

Initial whole-raw-tree audit exit 1 found exactly one unrecorded authoritative owner workbook at `hud/ZIP-COUNTY_122025.xlsx`; no hash mismatch or other discrepancy. Original bytes were first recorded, never replaced, with manual-import retrieval-time proxy 2026-10-13T14:18:53+00:00, hash 554379b618f21380bed6777a9c69845ac138843c1a57f951886d605bc9611c68, size 2,462,769. Prescribed import copied the immutable bytes to the reference path recorded above. Original manual download time is unknown. Premeasurement and postacquisition audits exit 0 with zero discrepancies. No IPUMS contents were inspected except the authorized whole-tree file hashing audit, and this finding settles neither IPUMS provenance interpretation nor V4–V7.

Original filename is `ZIP-COUNTY_122025.xlsx` (2025Q4). Delivered header uses GEOID rather than COUNTY; reader aliases only a validated ZIP-COUNTY filename. Full reader validation accepted 54,571 rows / 39,494 ZIPs, including 8 recognized short noncounty out-of-scope zero-business rows retained without fake zero padding. CT codes use 09110–09190 planning regions. The owner first mentioned ZIP-TRACT, which was rejected as a prerequisite; no tract workbook enters measurement. HUD API was mentioned as a future acquisition option only; no credentials/API implementation are used.

Official sources: [OSHA ITA](https://www.osha.gov/itadata), [HUD USPS crosswalk](https://www.huduser.gov/portal/datasets/usps_crosswalk.html), official Census NAICS workbook URLs and Census geocoder catalog/response endpoints recorded in the input inventory above. The parser's full-file expected title counts passed for all three vintages; there is no substituted local title lookup. Parent/edge/concordance reference tables remain Stage 4.

Census response acquisition timestamps, hashes and catalogs above pin cached bytes. Mutable Public_AR_Current address ranges may change between batches or resumed acquisitions; catalog caching pins request options, not a frozen address-source snapshot. All three batches belong to the same verified request run. Offline replay reproduces the cached comparison, not a claim that a fresh service call would return identical matches.

The reproducible report column `n_proposed_assignable` retains its original measurement name; after owner approval it reports the adopted rule's assignable sample rows. Owner D8 corrected returned-county scope gates, measured under a new code hash/run; cached source bytes and adopted A1–A4 are unchanged.

## Adopted amendments — owner, 2026-10-13

The owner approved the following complete plan A1–A4 blocks as proposed on 2026-10-13. They are applied to R2.3 and R2.6–R2.8 in the source spec, retaining the following delivered-file paragraphs from plan 2.

  **A1 — R2.3 introductory correction.** Replace the opening through its first
  `*(verified; ITA)*` marker with:

  > **R2.3** Stack all years into one establishment-year table keyed on
  > `year_filing_for`, harmonizing delivered-format and dictionary changes:
  > `establishment_id`, present from 2016 and documented as the summary-to-case
  > link from the 2023 data; the split of size code `2` into `21` and `22` from
  > the 2023 data; and NAICS codes that may be 2012, 2017, or 2022 vintage from
  > the 2023 data, identified by `naics_year`. *(verified; ITA;
  > specs/findings/v1-v3-ita-verification.md — owner, plan 3, 2026-10-13)*

  Keep the following delivered-file paragraphs from plan 2.

  **A2 — R2.6 open-marker replacement.** Replace the sentence beginning
  `What the field actually contains` and ending `discharged by V1)*.` with:

  > V1 measured the field's content by year; its results and denominators are
  > recorded in `specs/findings/v1-v3-ita-verification.md`. The matching key
  > uses NFKC, Unicode casefold and collapsed/trimmed whitespace, preserving
  > punctuation and the original delivered string. Empty keys and exact
  > placeholder keys `n/a`, `na`, `none`, `unknown`, `not applicable`,
  > `not specified`, `-`, `--`, and `.` are flagged. Identity to any official
  > 2012, 2017 or 2022 NAICS title at levels 2–6 is flagged as copied text;
  > native-vintage identity is also reported, with unknown vintage kept
  > unknown. Suspected mojibake is flagged rather than automatically repaired.
  > Employer grouping uses a usable EIN, else a non-empty normalized company
  > name, with name fallback and reconstructed EIN marked separately; blank
  > employer fields never form a shared employer. Unknown-employer rows
  > retain that flag and do not participate in employer deduplication.
  > *(verified; specs/findings/v1-v3-ita-verification.md — owner, plan 3,
  > 2026-10-13)*

  **A3 — R2.7 replacement.** Replace its full paragraph with:

  > **R2.7** Link establishments across years using `establishment_id` as a
  > candidate in every delivered year. A confirmed link requires a unique ID
  > in each year, the same usable unreconstructed EIN, and the same normalized
  > full address. Exact duplicate rows collapse for linkage only; competing
  > same-ID records remain ambiguous. A changed-ID fallback requires a unique
  > match on usable unreconstructed EIN plus normalized establishment name
  > and full address in both years. Missing or reconstructed EINs, incomplete
  > addresses and conflicting keys are reported separately as weaker or
  > unresolved evidence, not counted as confirmed links. The required
  > 2023→2024 and 2023→2025 persistence/address comparisons and earlier-year
  > diagnostics are recorded in `specs/findings/v1-v3-ita-verification.md`.
  > `ein` with `company_name` also supports multi-unit firm diagnostics for
  > R7.2; company-name fallback does not establish EIN-based co-ownership.
  > *(verified; specs/findings/v1-v3-ita-verification.md — owner, plan 3,
  > 2026-10-13)*

  **A4 — R2.8 replacement.** Replace its full paragraph with:

  > **R2.8** Assign each establishment a county from its address, then derive
  > state, CBSA, division and region under R6. Use a cached Census exact
  > street-address geography match in the common ACS2025 county frame first;
  > otherwise use a HUD ZIP–county fallback only when exactly one county has
  > positive business-address share and its county geography is compatible.
  > Unmatched, non-exact, ambiguous, zero-business-share, out-of-scope and
  > incompatible-vintage results are retained with flags; no largest-share
  > county or old-Connecticut-county shortcut supplies a headline assignment.
  > The stratified comparison, reference quarter, Census benchmark/vintage,
  > conditional county agreement and limitations are recorded in
  > `specs/findings/v1-v3-ita-verification.md`. Stage 6 applies this adopted
  > rule to the full establishment table; Stage 3's sample is verification
  > evidence only. *(verified; specs/findings/v1-v3-ita-verification.md —
  > owner, plan 3, 2026-10-13)*


## Owner decision

The owner approved A1–A4 as proposed on 2026-10-13 after reviewing the complete actual finding. No replacement default or software change was required, so the measured run retains its original code/dependency provenance. Low early-year EIN confirmation remains unknown evidence under the conservative rule. This adoption settles V1–V3's rule choices; full-table county assignment, targets and later-stage work remain separate planned work.
