# Stage 5 production geography reference build

Measured 2026-10-14 after implementation; schema `geography-v1`.

Selected bundle: `data/derived/geography/stage5_geography_20261014/`.
Execution-date run IDs use 20261014 in place of the planning-date 20261013 examples.

Logical-repeat bundle: `data/derived/geography/stage5_geography_20261014_repeat/`.
Detached outputs.json SHA-256: `5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d`.

All four original citations, software hashes, lock identity and eight detached output entries were verified. Source summary and all captured Stage 3/4 files are unchanged; the first bundle retained its nine original physical hashes after the second build.

## Original citations

| Path | Edition | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| raw/references/geography/2023/list1_2023.xlsx | July 2023 | 143798 | `952c4b1e78acbb54e6ec9412434b7602fedacbf021736351a63c181bdb753629` |
| raw/references/geography/2025/2025_Gaz_counties_national.zip | 2025 | 138993 | `4c90d0f805779923b5958ab13d0c1e9b99fe4932b786bfcf75dd739bb2dcb4ea` |
| raw/references/hud/2025Q4/ZIP-COUNTY_122025.xlsx | 2025Q4 | 2462769 | `554379b618f21380bed6777a9c69845ac138843c1a57f951886d605bc9611c68` |
| raw/references/geography/2025/state-geocodes-v2025.xlsx | 2025 | 14700 | `327c7fa3dfeb6526b20cd3d1cef7f471ec08316e92b183f12c5b168bfed7da84` |

## Exact schemas and counts

```json
{
  "cbsa_reference.parquet": {
    "rows": 925,
    "schema": {
      "cbsa_code": "String",
      "cbsa_id": "String",
      "cbsa_title": "String",
      "cbsa_type": "String",
      "cbsa_vintage": "Int64",
      "n_counties": "Int64",
      "state_fips": "List(String)"
    }
  },
  "county_reference.parquet": {
    "rows": 3144,
    "schema": {
      "cbsa_code": "String",
      "cbsa_id": "String",
      "cbsa_role": "String",
      "cbsa_type": "String",
      "cbsa_vintage": "Int64",
      "county_geoid": "String",
      "county_id": "String",
      "county_title": "String",
      "county_vintage": "Int64",
      "division_code": "String",
      "division_id": "String",
      "division_title": "String",
      "region_code": "String",
      "region_id": "String",
      "region_title": "String",
      "state_fips": "String",
      "state_id": "String",
      "state_title": "String",
      "state_usps": "String"
    }
  },
  "geography_edges.parquet": {
    "rows": 5048,
    "schema": {
      "child_id": "String",
      "edge_type": "String",
      "parent_id": "String"
    }
  },
  "geography_nodes.parquet": {
    "rows": 4133,
    "schema": {
      "code": "String",
      "level": "String",
      "node_id": "String",
      "system": "String",
      "title": "String",
      "vintage": "Int64"
    }
  },
  "hud_zip_county.parquet": {
    "rows": 54571,
    "schema": {
      "bus_ratio": "Float64",
      "county_geoid": "String",
      "county_in_frame": "Boolean",
      "flag_county_incompatible": "Boolean",
      "flag_county_legacy_ct": "Boolean",
      "flag_county_out_of_scope": "Boolean",
      "noncounty_geography": "Boolean",
      "zip_key": "String"
    }
  },
  "hud_zip_lookup.parquet": {
    "rows": 39494,
    "schema": {
      "business_counties": "List(String)",
      "dominant_candidates": "List(String)",
      "eligibility_status": "String",
      "flag_zip_has_incompatible": "Boolean",
      "flag_zip_has_out_of_scope": "Boolean",
      "flag_zip_legacy_ct": "Boolean",
      "flag_zip_multiple_counties": "Boolean",
      "flag_zip_zero_business": "Boolean",
      "max_business_ratio": "Float64",
      "n_business_counties": "Int64",
      "n_hud_rows": "Int64",
      "zip_dominant_county": "String",
      "zip_fallback_county": "String",
      "zip_key": "String",
      "zip_single_candidate": "String"
    }
  }
}
```

## Graph, scope and HUD diagnostics

```json
{
  "cbsa_types": [
    {
      "cbsa_type": "metropolitan",
      "n_cbsas": 387,
      "n_counties": 1186
    },
    {
      "cbsa_type": "micropolitan",
      "n_cbsas": 538,
      "n_counties": 658
    }
  ],
  "graph_validation": "passed",
  "hud_candidate_diagnostics": {
    "flag_county_incompatible": 0,
    "flag_county_legacy_ct": 0,
    "flag_county_out_of_scope": 329,
    "noncounty_geography": 8
  },
  "hud_statuses": [
    {
      "eligibility_status": "eligible",
      "n_zips": 29174
    },
    {
      "eligibility_status": "multiple_counties",
      "n_zips": 6843
    },
    {
      "eligibility_status": "out_of_scope",
      "n_zips": 140
    },
    {
      "eligibility_status": "zero_business",
      "n_zips": 3337
    }
  ],
  "hud_unexpected_in_scope_county_codes": 0,
  "hud_zip_diagnostics": {
    "flag_zip_has_incompatible": 0,
    "flag_zip_has_out_of_scope": 182,
    "flag_zip_legacy_ct": 0,
    "flag_zip_multiple_counties": 6843,
    "flag_zip_zero_business": 3337
  },
  "multi_state_cbsas": 59,
  "non_cbsa_counties": 1300,
  "schema_version": "geography-v1",
  "source_scope_exclusions": {
    "cbsa_codes_without_scoped_members": 10,
    "county_rows": 78,
    "membership_rows": 71,
    "state_rows": 0
  }
}
```

## Limits and downstream contract

The administrative frame is 2025, OMB membership is July 2023, and HUD is 2025Q4. This is a common-frame reference, not historical county geography for older filing addresses. Both metropolitan and micropolitan CBSAs are included; no CBSA has a forced state parent. County inventory includes counties with no CBSA membership and counties without positive HUD share.

HUD rows/ratios and every ZIP are retained. Positive candidates are counted before scope/compatibility checks; mixed valid/excluded candidates remain ambiguous. Dominant shares are diagnostic. Only an eligible original singleton supplies zip_fallback_county. Missing ZIP and all-zero ZIP are distinct. Scope/legacy/noncounty flags remain independent.

Stage 6 must verify and select this complete bundle, preserve Stage 3 exact Census-first precedence and delivered-state exclusion, and perform full establishment assignment. Stage 8 owns PUMA allocation/V8. No relatedness target or allocation is inferred here. Future Census Current calls may change; these reference bytes do not freeze address-service responses.

Requirements: [source spec](../embedding-evaluation-data-spec.md) R2.8/R6.1/R6.2/R6.4 and the Stage 5 design. Layout evidence: [preflight](stage-5-geography-reference-preflight.md).
