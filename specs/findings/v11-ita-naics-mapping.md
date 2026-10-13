# V11 (ITA): measured canonical mapping and filing diagnostics

Measured 2026-10-13 against the full local dataset, using execution commit
`ccd138fcf8606085cf3d13821bf01f86ab35f7f2`, run `stage4_v11_20261013_r2`
and schema/transformation version `codes-ita-v1`. The immutable bundle is
`data/derived/codes/stage4_v11_20261013_r2/`. This records actual produced outputs,
not fixture results or a preflight substitute. Stage 4 completion and whole-branch
review are separate controller gates.

## Scope, interpretation and limitations

This finding implements the ITA portion of [the source spec](../embedding-evaluation-data-spec.md)
R2.5/R2.9/R5.1/R5.2/R5.4 and the [Stage 4 design](../completed/code-tables-ita-naics-mapping.md).
The [source preflight](stage-4-ita-code-preflight.md) and
[rule-reference preflight](stage-4-filing-rule-reference-preflight.md) explain the
owner-adopted source exception and bounded legacy-label interpretation.
All 3,206,055 source rows survive with every original column and duplicate
multiplicity unchanged. Separate 100,000-row comparisons verify source order,
including the final 6,055-row slice; no establishment row values are reported here.

Known-vintage codes absent from their native structure remain
`invalid_native_code`, even when another supported vintage contains them.
Unknown-vintage codes retain the union of possibilities supported by 2012/2017/2022,
without assuming the true vintage belongs to that set. Even singleton unknown
unions never assert a canonical scalar or node ID. Native codes/vintages and all
Stage 2 flags remain unchanged. Empty candidate lists assert no resolution;
multiple candidates remain sorted unweighted possibilities. A deepest common
ancestor describes the candidate set, not a fully observed aggregate industry.
Singleton crosswalks retain the crosswalk flag; code equality never bypasses an
official relationship. No industry is imputed from a title, allocated, selected
by weights, or preferred as one side of an uncertain relation.

The ITA exception explicitly accounts for source defects; it does not relax
R5.3/V11's later ACS/CPS parsing completeness. Relatedness remains observed,
never assumed: formal trees cannot produce targets. Geography, ACS/CPS parsers,
target builders, the shared target writer and headline-inclusion decisions
remain their existing later-stage responsibilities. Crosswalk and other imputation
flags remain available for the source spec's headline exclusions.

The exemption publication has 82 labels, including `5173` and `5181`, absent
from 2007 but present in 2002. Only these two labels use the complete official
2002-to-2007 bridge; 2002/2007 are auxiliary rule references, not new ITA native
vintages. The bridge conservatively retains covered and uncovered predecessors.
The sole mixed rule-native leaf is 2007 `517110`, with `[false, true]` membership.
This is the adopted reference interpretation, not external confirmation of OSHA's
intended treatment of individual establishments within a merged industry.

Filing evaluation traverses directly to each rule vintage and preserves all
possibilities within each native interpretation before unioning outcomes. A
nullable industry result is determinate only under unanimity. Class 1 asserts
below-size outside status without industry membership; missing size stays null.
Reference ambiguity and bridged-label flags persist even when the final result
is determinate. Industry diagnostics do not overwrite the Stage 2 below-size flag.

Rules use the nominal submission cycle (filing year plus one): designated 2012
for 2016–2022 data and designated 2017 for 2023 onward. The original and revised
designated rules take effect 2017-01-01 and 2024-01-01; the 2007 exemption list
is effective 2015-01-01. Actual submission timestamps are unavailable, so late
filings may not follow this nominal binding. These flags describe the filing
universe and do not establish that observed submissions were improper.

## Verification and publication boundary

All ten new originals were hashed against the approved import inventory, including
the three matching classification-skill source-cache manifest hashes; the three
existing title originals were checked against the raw manifest. Registered
`codes import-reference` retained complete official bytes and recorded local import
time as a retrieval-time proxy. A shipped `codes acquire` replay found all thirteen
references cached, therefore downloaded none. A second registered CLI replay with HTTP send forbidden
confirmed zero HTTP calls and unchanged raw-manifest bytes during the original
measurement. Original pre/post-build and fresh-run audits returned
`0 raw provenance discrepancies`. No private data were transmitted.

The offline build verified the selected ten raw releases, contiguous source years,
exact Stage 2 schema, and year-by-year full-column multiset parity against raw
harmonization. It never called `build_summary_table`, `prepare`, or `sample`.
Additional acceptance verified both canonical forests, all expected graph/rule counts,
exact canonical schema, expected source-defect states, row accounting, all raw,
source, implementation and lock hashes, every output checksum/size, and all 25
protected source/Stage 3 hashes. No measurement discrepancy required a code or dependency change. Final branch
review identified an independent CLI exception gap: native fastexcel workbook
errors needed the same clean exit-2 diagnostic as other parser failures. The
reviewed fix in execution commit `ccd138f` changes CLI error handling only; it
changes no mapping, filing, reference or dependency behavior. The code-change
evidence policy required this fresh run rather than replacing earlier outputs.
The earlier `stage4_v11_20261013` bundle remains available, and all fifteen of
its files were snapshotted before this build and verified byte-identical afterward.
The complete fresh aggregate report equals the earlier report, and runtime and
dependency versions also match. Fresh input/output hashes are recorded below.
The canonical Parquet physical bytes differ between runs; a further 33-slice
comparison verifies every column, including mapping and filing fields, is logically
identical in source order. Physical writer bytes are not the determinism contract.

Strict parser/build gates reject malformed nonmissing ITA codes (anything other
than six ASCII digits), unsupported nonnull vintages, missing/corrupt originals,
ambiguous headers, duplicate/missing graph nodes or titles, orphan/cyclic parentage,
incomplete concordance endpoints, unmatched rule labels outside the explicit
allowlist, missing lookup/membership rows, unsupported filing years and stale
source parity. Existing final or staging run names are refused. These refusal
paths are fixture-tested; the actual successful build exercised validation on
pinned references, not deliberate corruption of the real tree. Staging is published
only after validation; source and prior runs are never replaced.

Commands used from the execution checkout (all uv commands prefixed with
`UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache`):

```bash
uv run --offline --locked embedding-data codes import-reference KIND ORIGINAL --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked embedding-data codes acquire --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked embedding-data audit --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked embedding-data codes build stage4_v11_20261013_r2 --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked python .sdd/4-code-tables-ita-naics-mapping/accept-full-data.py stage4_v11_20261013_r2
uv run --offline --locked pytest
uv run --offline --locked behave
uv run --offline --locked ruff check .
uv lock --offline --check
```

Milestone results: 476 passed, 1 network test deselected; 1 Behave feature,
2 scenarios and 10 steps passed; Ruff passed; lock check resolved 63 packages.

## Input provenance and software

The following raw citations include the original official URLs. Hashes cover
archived bytes; source URLs identify provenance and need not remain byte-stable.
These records cite Census full structures/concordances, the BLS SOC 2018 original,
and complete GovInfo Federal Register publications rather than derived skill CSVs.

| path | bytes | SHA-256 | official source |
| --- | --- | --- | --- |
| osha/summary/2016/ITA Data CY 2016.zip | 12106381 | 9f41c720fb02f78788f1090e5fc885fdb09343fc349c4ae4c80cc9165d83742f | https://www.osha.gov/sites/default/files/ITA%20Data%20CY%202016.zip |
| osha/summary/2017/ITA Data CY 2017.zip | 14682864 | 354fb246be90d6bac3d4a7c94e44f90d40f1d3ff73f911d37691ae98a87de0fb | https://www.osha.gov/sites/default/files/ITA%20Data%20CY%202017.zip |
| osha/summary/2018/ITA Data CY 2018.zip | 16970794 | 0bd2e8475a5766baba8883a1258a92168c43c5ff551c853b1992641814b4dc2f | https://www.osha.gov/sites/default/files/ITA%20Data%20CY%202018.zip |
| osha/summary/2019/ITA Data CY 2019.zip | 18898257 | bf93ea7312bfe34d903c1272f15c785a61b8c8bbc6df6e09f0d3fe372205ac6e | https://www.osha.gov/sites/default/files/ITA%20Data%20CY%202019.zip |
| osha/summary/2020/ITA-Data-CY-2020.zip | 19480392 | eb704f2cc343adc7710b48204015ac11c3018fae684f44747158d731e713899b | https://www.osha.gov/sites/default/files/ITA-Data-CY-2020.zip |
| osha/summary/2021/ITA-data-cy2021.zip | 19431073 | 5a11abc7c085f07f08f130c25bf78c85581b2379fb8b514f728bfcdf5d61b4a3 | https://www.osha.gov/sites/default/files/ITA-data-cy2021.zip |
| osha/summary/2022/ITA-data-cy2022.zip | 19730409 | e396af8038d40d74b96ebb6ee9b561bbcb8907ee66adff089402a676c919e6ef | https://www.osha.gov/sites/default/files/ITA-data-cy2022.zip |
| osha/summary/2023/ITA_300A_Summary_Data_2023_through_12-31-2024.zip | 24143043 | 25da8bc426db219a7a5fe872e73830afebdfac87c460f8cf6561658e7103b487 | https://www.osha.gov/sites/default/files/ITA_300A_Summary_Data_2023_through_12-31-2024.zip |
| osha/summary/2024/ITA_300A_Summary_Data_2024_through_12-31-2025.zip | 23855931 | 4cbce7ea32dd4060f442a528670936e552d1b731925f320d9d25a168f9b60b1d | https://www.osha.gov/sites/default/files/ITA_300A_Summary_Data_2024_through_12-31-2025.zip |
| osha/summary/2025/ITA_300A_Summary_Data_2025_through_08-31-2026.csv | 88383913 | 9ea2ee5d7265cddf753d22633af17d4aaba4ab81629341462a8c9912d19a99fc | https://www.osha.gov/sites/default/largefiles/ITA_300A_Summary_Data_2025_through_08-31-2026.csv |
| references/filing-rules/2014-21514.htm | 347880 | 3418238856a56bf0da7bac73a1a07535a4f098e3212287a35048602968855a87 | https://www.govinfo.gov/content/pkg/FR-2014-09-18/html/2014-21514.htm |
| references/filing-rules/2016-10443.htm | 524902 | ed7ea8e8533236ea0fcbafcb703f38007b75e97b472789f9a2ded55eac958866 | https://www.govinfo.gov/content/pkg/FR-2016-05-12/html/2016-10443.htm |
| references/filing-rules/2023-15091.htm | 718918 | fd0ae1f1c1462adf2863c2107da32e2a4d1d486503433f347237867edd401551 | https://www.govinfo.gov/content/pkg/FR-2023-07-21/html/2023-15091.htm |
| references/naics/2002_to_2007_NAICS.xls | 161280 | a4b00b2195e318420962ba52b77f3c3122e83d893a9f804e820c151847ec85b1 | https://www.census.gov/naics/concordances/2002_to_2007_NAICS.xls |
| references/naics/2007_to_2012_NAICS.xls | 171520 | 302b8abcd78881f1ea5aa4c6c9104811bf8fa10d57b48d492939de5cacc8cfc5 | https://www.census.gov/naics/concordances/2007_to_2012_NAICS.xls |
| references/naics/2012_NAICS_Structure.xls | 254976 | 50eba48db4e11f863e015d4d2bbaaf618565bd94ef9b019fe62b9bbaddbaaafb | https://www.census.gov/naics/2012NAICS/2012_NAICS_Structure.xls |
| references/naics/2012_to_2017_NAICS.xlsx | 58543 | 17f463f7e8385df1cc762fadf0dd5c25910aa27034ca96275a906608399188f5 | https://www.census.gov/naics/concordances/2012_to_2017_NAICS.xlsx |
| references/naics/2017_NAICS_Structure.xlsx | 95610 | 662b5a2bdff10938997acd7f59f84331527d6f06ff24d5533331581a00a94aad | https://www.census.gov/naics/2017NAICS/2017_NAICS_Structure.xlsx |
| references/naics/2017_to_2022_NAICS.xlsx | 59656 | 4662cc7ed9e7f3fb8a968e9504a7d06e448f5b65a349996a5627439df193eb30 | https://www.census.gov/naics/concordances/2017_to_2022_NAICS.xlsx |
| references/naics/2022_NAICS_Structure.xlsx | 88218 | 217c9e0d4d74e7517bc288f5f308b73aa0de5ee787976a6dd222412be28ada22 | https://www.census.gov/naics/2022NAICS/2022_NAICS_Structure.xlsx |
| references/naics/naics07.xls | 252416 | 9eaa1fc4681ad22296b8f09603dc3674605eeb13b0fd631811d51704e1c2f463 | https://www.census.gov/naics/reference_files_tools/2007/naics07.xls |
| references/naics/naics_2_6_02.txt | 111445 | b05cb32865d9267eaca4c2df45b89605c02320c5d1794b0ba0304e2c1741edaf | https://www.census.gov/naics/reference_files_tools/2002/naics_2_6_02.txt |
| references/soc/soc_structure_2018.xlsx | 51367 | ade08af40923266f3a854842e888ca3e93c15b26a147c20a2b12a61f4c4f4077 | https://www.bls.gov/soc/2018/soc_structure_2018.xlsx |

Source Parquet:

```json
{
  "path": "derived/osha/ita_300a_summary.parquet",
  "sha256": "6335cda7adb40a41c4a11d57d22048999449ac8d078a2ec0291f0198cd9136a8",
  "size": 139930636
}
```

Dependency versions and Python runtime:

```json
{
  "dependencies": {
    "embedding-data": "0.1.0",
    "fastexcel": "0.21.0",
    "httpx": "0.28.1",
    "polars": "2.0.0",
    "typer": "0.27.3"
  },
  "pyproject_sha256": "0efd4c90ae3efb90d84e25fa8cec8242d870a702109e0abb1bea843753521594",
  "python": "3.14.0 (main, Oct 14 2025, 21:10:22) [Clang 20.1.4 ]",
  "uv_lock_sha256": "f57c3280a7c8286711bf6804ca4c02f0a19619c9db52f33941b9c5b996cba8e5"
}
```

Implementation SHA-256 inventory:

| file | SHA-256 |
| --- | --- |
| src/embedding_data/classification_tables.py | 856d92efe38a98bd7f047f4b96e40368e1bda6da3c052ccf2fde952b4c9803d3 |
| src/embedding_data/code_build.py | 0cfc516da2ce05412306f2c8046b37bb2b8b1177501616839a8196c5014a99c2 |
| src/embedding_data/code_references.py | c6fd782cc408ce3db9053296ccab0652878bfa88a1f8cebbac46772ac8b5d728 |
| src/embedding_data/filing_rules.py | 23d9fad2ed790c6c8fe382b71dfb31ded49f27736d3a84e4f707d184e89fbc9a |
| src/embedding_data/ita_catalog.py | 325d4e132719f56a2e94049323ecd1763281df69ee60eae356259fea9b951f58 |
| src/embedding_data/ita_naics_mapping.py | bde4a9ddde83b05a9b056631c53601aaeb0f539cae6fd99b49f2edc9cc9b897c |
| src/embedding_data/ita_references.py | 2fbb723fdec6a712b76e82a687de76cc631b023e6ff8520419d9c920588b452c |
| src/embedding_data/ita_summary.py | 082ccabe0ab00d7b03fcfbaea5e2622fced83b4cf1cdef2d51b9a5f5d05f6229 |
| src/embedding_data/manifest.py | b734f4a81923838f21eed010350ddcc8c5b1a632d5defb6d115925273ab36b80 |
| src/embedding_data/naics_relationships.py | e674cb5370d1b8582735e83fb035bc4efbd0ab5b0f0dfc5cc2a82bba1aa25254 |
| src/embedding_data/osha_encoding.py | 4e3efe187e25e1d2dd894207b9d7bdb719ae5543c740c208df401174e7ee6307 |
| src/embedding_data/paths.py | 9adc720b3dfe07a5801e41f5f1b7cbe1d1a9d2620b4c983ef5babc63d811a014 |

Additional CLI implementation hashes (not included in the build-generated implementation inventory):

| file | SHA-256 |
| --- | --- |
| src/embedding_data/codes_cli.py | e52b213e5dec5098ad6a7f91c0ccb428f00a4f59f1560dd410a788283f2a9dd7 |
| src/embedding_data/cli.py | 04bed79c10fad08a46aac670aa2934ddc861b5a6c9416e4738cb32505b8a3ebb |

## Bundle inventory and exact schemas

`outputs.json` is detached: it covers all twelve Parquet tables plus `inputs.json` and `report.json`, and excludes itself to avoid self-reference. Its own SHA-256 is `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`. JSON records use the `codes-ita-v1` contract; `inputs.json` records the run ID. List types are nonnull for candidates/matching vintages. Schemas below list columns in physical Parquet order. Canonical scalar fields are nullable. Mapping and reference-provenance flags are nonnullable; filing-industry and combined filing-rule flags are nullable. Source nullability is preserved.

| filename | rows | bytes | SHA-256 |
| --- | --- | --- | --- |
| code_paths.parquet | 3572 | 24742 | ca764663db2337e340b2de60f0507be888fa3a4c06b67cd5e312f929c8d25db9 |
| filing_rule_labels.parquet | 213 | 3341 | 349372e5e2e340469622c53acbf42b3fb58b52066ea3953d155475f2037ed7df |
| filing_rule_membership.parquet | 3297 | 9842 | 1485c190c5e6d8019f07939240773e14c9dc039111c2c10ae32207ad214d4796 |
| filing_rules.parquet | 1624 | 6698 | 5f362737c57b7f512d8b1bc710548776c7658b1bc778f98f810279a0d46cd1d9 |
| inputs.json | — | 17978 | 0b76c93e87f6c097eb20ca33257d3715a5a88ee83150d918e78be09930c1fc10 |
| ita_300a_canonical.parquet | 3206055 | 156025783 | 2c64e783c8874cbe78809c0629a08faa7a0bf965d7680279350a64928a1f32ab |
| ita_naics_lookup.parquet | 4109 | 42902 | b1dfb33644c413ba33698fbf26c1316507382077ae73226ef5c3626d5bc287c8 |
| naics_concordance.parquet | 4603 | 19640 | 5384c1c81e973940f459c8cd9210335c5a1da6f5302c47f9fb5338bed9b262d6 |
| naics_edges.parquet | 2105 | 12492 | caade9029e658f023f75056c0e7ebb2f9fa0d285bd91d43a32b65c2ec84d8e9c |
| naics_native_nodes.parquet | 11199 | 67980 | e0734a9a89bfdf2b9049f1dbff074f124165f79e86bf933a0c9875bdaeebd54d |
| naics_nodes.parquet | 2125 | 33378 | 8a0b39dae23802c4a129fe1f89c12ae5c9c7a88eef2d3f9c292f4f4979bc229a |
| report.json | — | 38114 | 56dfb18ab93f244f4294c015cab38905ca3e3cbf822730e922747dcc6b89f29a |
| soc_edges.parquet | 1424 | 7036 | 38a224322b1b5f08835a17a1f9e0ddf2592c2e3b343e8cfbe9525f2d176cae28 |
| soc_nodes.parquet | 1447 | 22379 | 7a2259678719b1fc9d5c0cf3809023d6a87bdb4d6aed4b788e2f266e0586d356 |

### code_paths.parquet

| column | dtype |
| --- | --- |
| node_id | String |
| path | List(String) |

### filing_rule_labels.parquet

| column | dtype |
| --- | --- |
| rule_id | String |
| vintage | Int64 |
| listed_code | String |
| label_vintage | Int64 |
| flag_rule_label_legacy | Boolean |
| source_file | String |

### filing_rule_membership.parquet

| column | dtype |
| --- | --- |
| rule_id | String |
| vintage | Int64 |
| code | String |
| effective_from | Date |
| effective_to | Date |
| source_file | String |
| membership_candidates | List(Boolean) |
| flag_rule_label_bridged | Boolean |

### filing_rules.parquet

| column | dtype |
| --- | --- |
| rule_id | String |
| vintage | Int64 |
| code | String |
| effective_from | Date |
| effective_to | Date |
| source_file | String |

### ita_300a_canonical.parquet

| column | dtype |
| --- | --- |
| year_filing_for | Int64 |
| id | Int64 |
| establishment_id | Int64 |
| establishment_name | String |
| company_name | String |
| ein | String |
| street_address | String |
| city | String |
| state | String |
| zip_code | String |
| naics_code | String |
| naics_year | Int64 |
| naics_year_from_dictionary | Boolean |
| industry_description | String |
| establishment_type | Int64 |
| size | Int64 |
| size_class | Int64 |
| annual_average_employees | Int64 |
| total_hours_worked | Int64 |
| flag_employment | Boolean |
| flag_hours_per_employee | Boolean |
| flag_below_filing_size | Boolean |
| flag_naics_year_unknown | Boolean |
| source_file | String |
| naics_mapping_status | String |
| naics_matching_vintages | List(Int64) |
| naics_2022_candidates | List(String) |
| naics_2022_code | String |
| naics_2022_node_id | String |
| naics_deepest_common_node_id | String |
| flag_naics_crosswalked | Boolean |
| flag_naics_ambiguous | Boolean |
| flag_naics_unresolved | Boolean |
| filing_industry_status | String |
| flag_outside_filing_industry | Boolean |
| flag_outside_filing_rule | Boolean |
| flag_filing_rule_label_bridged | Boolean |
| flag_filing_reference_ambiguous | Boolean |

### ita_naics_lookup.parquet

| column | dtype |
| --- | --- |
| naics_code | String |
| naics_year | Int64 |
| naics_mapping_status | String |
| naics_matching_vintages | List(Int64) |
| naics_2022_candidates | List(String) |
| naics_2022_code | String |
| naics_2022_node_id | String |
| naics_deepest_common_node_id | String |
| flag_naics_crosswalked | Boolean |
| flag_naics_ambiguous | Boolean |
| flag_naics_unresolved | Boolean |

### naics_concordance.parquet

| column | dtype |
| --- | --- |
| source_vintage | Int64 |
| target_vintage | Int64 |
| source_code | String |
| target_code | String |
| link_type | String |
| source_file | String |

### naics_edges.parquet

| column | dtype |
| --- | --- |
| child_id | String |
| parent_id | String |
| edge_type | String |

### naics_native_nodes.parquet

| column | dtype |
| --- | --- |
| node_id | String |
| system | String |
| vintage | Int64 |
| level | String |
| code | String |
| title | String |

### naics_nodes.parquet

| column | dtype |
| --- | --- |
| node_id | String |
| system | String |
| vintage | Int64 |
| level | String |
| code | String |
| title | String |

### soc_edges.parquet

| column | dtype |
| --- | --- |
| child_id | String |
| parent_id | String |
| edge_type | String |

### soc_nodes.parquet

| column | dtype |
| --- | --- |
| node_id | String |
| system | String |
| vintage | Int64 |
| level | String |
| code | String |
| title | String |

## Reference graph and rule measurements

| vintage | nodes | finest | sectors |
| --- | --- | --- | --- |
| 2002 | 2341 | 1179 | 20 |
| 2007 | 2328 | 1175 | 20 |
| 2012 | 2209 | 1065 | 20 |
| 2017 | 2196 | 1057 | 20 |
| 2022 | 2125 | 1012 | 20 |

Canonical NAICS: 2,125 nodes, 2,105 edges, 20 roots and 1,012 finest codes. SOC: 1,447 nodes, 1,424 edges, 23 roots and 867 detailed codes. Combined paths: 3,572. Ranged NAICS sectors `31-33`, `44-45`, `48-49` each remain one node. Edges point child to parent, roots have no parent and no invented root is added; this classification single-parent constraint does not constrain later CBSA geography.

| source_vintage | target_vintage | link_type | len |
| --- | --- | --- | --- |
| 2002 | 2007 | 1:1 | 1142 |
| 2002 | 2007 | 1:m | 11 |
| 2002 | 2007 | m:1 | 24 |
| 2002 | 2007 | m:m | 23 |
| 2007 | 2012 | 1:1 | 986 |
| 2007 | 2012 | 1:m | 7 |
| 2007 | 2012 | m:1 | 183 |
| 2007 | 2012 | m:m | 8 |
| 2012 | 2017 | 1:1 | 1045 |
| 2012 | 2017 | 1:m | 3 |
| 2012 | 2017 | m:1 | 16 |
| 2012 | 2017 | m:m | 5 |
| 2017 | 2022 | 1:1 | 928 |
| 2017 | 2022 | 1:m | 5 |
| 2017 | 2022 | m:1 | 120 |
| 2017 | 2022 | m:m | 97 |

| definite_members | label_bridge_codes | legacy_labels | listed_groups | mixed_memberships | rule_id | rule_native_codes | nonmembers |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 689 | 0 | 0 | 66 | 0 | designated_2012 | 1065 | 376 |
| 683 | 0 | 0 | 65 | 0 | designated_2017 | 1057 | 374 |
| 252 | 4 | 2 | 82 | 1 | partially_exempt_2007 | 1175 | 922 |

All four direct full concordances cover every finest endpoint on both sides. Composed canonical candidates deduplicate only identical final codes; direct pairs retain source provenance. The complete membership table includes every rule-native code, with the definite table exactly its `[true]` projection.

## Full-data mapping and filing measurements

| naics_mapping_status | len |
| --- | --- |
| concorded | 2313539 |
| invalid_native_code | 66365 |
| native_2022 | 823481 |
| unknown_vintage_candidates | 373 |
| unknown_vintage_unmapped | 2297 |

There are zero missing source codes and 69,035 unresolved rows: 66,365 known-vintage mismatches plus 2,670 unknown vintages (373 supported candidate unions and 2,297 unsupported). These counts are disjoint states; provenance flags overlap. Every mapping, filing and candidate-count partition below totals 3,206,055.

### Mapping states by filing year

| year_filing_for | n | naics_mapping_status |
| --- | --- | --- |
| 2016 | 213432 | concorded |
| 2016 | 1546 | invalid_native_code |
| 2017 | 257540 | concorded |
| 2017 | 2218 | invalid_native_code |
| 2018 | 280813 | concorded |
| 2018 | 8721 | invalid_native_code |
| 2019 | 280168 | concorded |
| 2019 | 10307 | invalid_native_code |
| 2020 | 288231 | concorded |
| 2020 | 5160 | invalid_native_code |
| 2021 | 301664 | concorded |
| 2021 | 16314 | invalid_native_code |
| 2022 | 338902 | concorded |
| 2022 | 7897 | invalid_native_code |
| 2023 | 33643 | concorded |
| 2023 | 358294 | native_2022 |
| 2023 | 2297 | unknown_vintage_unmapped |
| 2024 | 171908 | concorded |
| 2024 | 4343 | invalid_native_code |
| 2024 | 222166 | native_2022 |
| 2024 | 203 | unknown_vintage_candidates |
| 2025 | 147238 | concorded |
| 2025 | 9859 | invalid_native_code |
| 2025 | 243021 | native_2022 |
| 2025 | 170 | unknown_vintage_candidates |

### Candidate-count distributions by filing year

| year_filing_for | candidate_count | n |
| --- | --- | --- |
| 2016 | 0 | 1546 |
| 2016 | 1 | 208726 |
| 2016 | 2 | 4244 |
| 2016 | 3 | 11 |
| 2016 | 8 | 2 |
| 2016 | 39 | 256 |
| 2016 | 42 | 193 |
| 2017 | 0 | 2218 |
| 2017 | 1 | 252533 |
| 2017 | 2 | 4466 |
| 2017 | 3 | 22 |
| 2017 | 8 | 4 |
| 2017 | 39 | 317 |
| 2017 | 42 | 198 |
| 2018 | 0 | 8721 |
| 2018 | 1 | 274755 |
| 2018 | 2 | 5473 |
| 2018 | 3 | 128 |
| 2018 | 8 | 7 |
| 2018 | 39 | 291 |
| 2018 | 42 | 159 |
| 2019 | 0 | 10307 |
| 2019 | 1 | 274500 |
| 2019 | 2 | 5170 |
| 2019 | 3 | 40 |
| 2019 | 8 | 4 |
| 2019 | 39 | 267 |
| 2019 | 42 | 187 |
| 2020 | 0 | 5160 |
| 2020 | 1 | 282927 |
| 2020 | 2 | 4852 |
| 2020 | 3 | 55 |
| 2020 | 8 | 7 |
| 2020 | 39 | 216 |
| 2020 | 42 | 174 |
| 2021 | 0 | 16314 |
| 2021 | 1 | 299570 |
| 2021 | 2 | 1703 |
| 2021 | 3 | 56 |
| 2021 | 8 | 3 |
| 2021 | 39 | 143 |
| 2021 | 42 | 189 |
| 2022 | 0 | 7897 |
| 2022 | 1 | 334626 |
| 2022 | 2 | 3880 |
| 2022 | 3 | 97 |
| 2022 | 8 | 14 |
| 2022 | 39 | 118 |
| 2022 | 42 | 167 |
| 2023 | 0 | 2297 |
| 2023 | 1 | 387283 |
| 2023 | 2 | 4067 |
| 2023 | 3 | 140 |
| 2023 | 8 | 14 |
| 2023 | 39 | 116 |
| 2023 | 42 | 317 |
| 2024 | 0 | 4343 |
| 2024 | 1 | 389986 |
| 2024 | 2 | 3690 |
| 2024 | 3 | 286 |
| 2024 | 8 | 7 |
| 2024 | 39 | 82 |
| 2024 | 42 | 226 |
| 2025 | 0 | 9859 |
| 2025 | 1 | 386154 |
| 2025 | 2 | 3935 |
| 2025 | 3 | 57 |
| 2025 | 8 | 8 |
| 2025 | 39 | 87 |
| 2025 | 42 | 188 |

### Mapping provenance by filing year

| year_filing_for | flag_naics_ambiguous | flag_naics_crosswalked | flag_naics_unresolved |
| --- | --- | --- | --- |
| 2016 | 4706 | 213432 | 1546 |
| 2017 | 5007 | 257540 | 2218 |
| 2018 | 6058 | 280813 | 8721 |
| 2019 | 5668 | 280168 | 10307 |
| 2020 | 5304 | 288231 | 5160 |
| 2021 | 2094 | 301664 | 16314 |
| 2022 | 4276 | 338902 | 7897 |
| 2023 | 4654 | 33643 | 2297 |
| 2024 | 4291 | 172111 | 4546 |
| 2025 | 4275 | 147408 | 10029 |

### Filing outcomes and reference provenance by filing year

Each row is a disjoint combination of filing status, nullable industry/rule results and the two independent reference-provenance flags. `null` is preserved explicitly.

| year_filing_for | filing_industry_status | flag_filing_reference_ambiguous | flag_filing_rule_label_bridged | flag_outside_filing_industry | flag_outside_filing_rule | n |
| --- | --- | --- | --- | --- | --- | --- |
| 2016 | candidate_disagreement | True | True | null | null | 307 |
| 2016 | determinate | False | False | False | False | 159692 |
| 2016 | determinate | False | False | True | True | 17920 |
| 2016 | determinate | False | True | True | True | 30 |
| 2016 | determinate | True | True | True | True | 285 |
| 2016 | invalid_native_code | False | False | null | null | 1285 |
| 2016 | not_applicable_below_size | False | False | null | True | 35459 |
| 2017 | candidate_disagreement | True | True | null | null | 155 |
| 2017 | determinate | False | False | False | False | 192564 |
| 2017 | determinate | False | False | True | True | 24174 |
| 2017 | determinate | False | True | True | True | 28 |
| 2017 | determinate | True | True | True | True | 221 |
| 2017 | invalid_native_code | False | False | null | null | 1217 |
| 2017 | not_applicable_below_size | False | False | null | True | 41399 |
| 2018 | candidate_disagreement | True | True | null | null | 210 |
| 2018 | determinate | False | False | False | False | 209010 |
| 2018 | determinate | False | False | True | True | 27382 |
| 2018 | determinate | False | True | True | True | 43 |
| 2018 | determinate | True | True | True | True | 184 |
| 2018 | invalid_native_code | False | False | null | null | 8479 |
| 2018 | not_applicable_below_size | False | False | null | True | 44226 |
| 2019 | candidate_disagreement | True | True | null | null | 148 |
| 2019 | determinate | False | False | False | False | 216032 |
| 2019 | determinate | False | False | True | True | 23699 |
| 2019 | determinate | False | True | True | True | 31 |
| 2019 | determinate | True | True | True | True | 175 |
| 2019 | invalid_native_code | False | False | null | null | 9908 |
| 2019 | not_applicable_below_size | False | False | null | True | 40482 |
| 2020 | candidate_disagreement | True | True | null | null | 151 |
| 2020 | determinate | False | False | False | False | 212517 |
| 2020 | determinate | False | False | True | True | 25492 |
| 2020 | determinate | False | True | True | True | 28 |
| 2020 | determinate | True | True | True | True | 176 |
| 2020 | invalid_native_code | False | False | null | null | 4578 |
| 2020 | not_applicable_below_size | False | False | null | True | 50449 |
| 2021 | candidate_disagreement | True | True | null | null | 148 |
| 2021 | determinate | False | False | False | False | 227877 |
| 2021 | determinate | False | False | True | True | 26608 |
| 2021 | determinate | False | True | True | True | 48 |
| 2021 | determinate | True | True | True | True | 191 |
| 2021 | invalid_native_code | False | False | null | null | 15634 |
| 2021 | not_applicable_below_size | False | False | null | True | 47472 |
| 2022 | candidate_disagreement | True | True | null | null | 110 |
| 2022 | determinate | False | False | False | False | 250277 |
| 2022 | determinate | False | False | True | True | 28617 |
| 2022 | determinate | False | True | True | True | 91 |
| 2022 | determinate | True | True | True | True | 193 |
| 2022 | invalid_native_code | False | False | null | null | 7040 |
| 2022 | not_applicable_below_size | False | False | null | True | 60471 |
| 2023 | candidate_disagreement | False | False | null | null | 6699 |
| 2023 | candidate_disagreement | False | True | null | null | 7 |
| 2023 | candidate_disagreement | True | True | null | null | 291 |
| 2023 | determinate | False | False | False | False | 267828 |
| 2023 | determinate | False | False | True | True | 33347 |
| 2023 | determinate | False | True | True | True | 84 |
| 2023 | determinate | True | True | True | True | 658 |
| 2023 | not_applicable_below_size | False | False | null | True | 83403 |
| 2023 | unknown_vintage_unmapped | False | False | null | null | 1917 |
| 2024 | candidate_disagreement | False | False | null | null | 15009 |
| 2024 | candidate_disagreement | False | True | null | null | 21 |
| 2024 | candidate_disagreement | True | True | null | null | 159 |
| 2024 | determinate | False | False | False | False | 259174 |
| 2024 | determinate | False | False | True | True | 32073 |
| 2024 | determinate | False | True | True | True | 72 |
| 2024 | determinate | True | True | True | True | 1561 |
| 2024 | invalid_native_code | False | False | null | null | 3924 |
| 2024 | not_applicable_below_size | False | False | null | True | 86627 |
| 2025 | candidate_disagreement | False | False | null | null | 2746 |
| 2025 | candidate_disagreement | False | True | null | null | 32 |
| 2025 | candidate_disagreement | True | True | null | null | 164 |
| 2025 | determinate | False | False | False | False | 249831 |
| 2025 | determinate | False | False | True | True | 33488 |
| 2025 | determinate | False | True | True | True | 69 |
| 2025 | determinate | True | True | True | True | 1156 |
| 2025 | invalid_native_code | False | False | null | null | 8988 |
| 2025 | not_applicable_below_size | False | False | null | True | 103814 |

Additional per-year vintage/provenance totals and explicit null results:

| year_filing_for | flag_naics_year_unknown | flag_filing_rule_label_bridged | flag_filing_reference_ambiguous | industry_null | rule_null |
| --- | --- | --- | --- | --- | --- |
| 2016 | 0 | 622 | 592 | 37051 | 1592 |
| 2017 | 0 | 404 | 376 | 42771 | 1372 |
| 2018 | 0 | 437 | 394 | 52915 | 8689 |
| 2019 | 0 | 354 | 323 | 50538 | 10056 |
| 2020 | 0 | 355 | 327 | 55178 | 4729 |
| 2021 | 0 | 387 | 339 | 63254 | 15782 |
| 2022 | 0 | 394 | 303 | 67621 | 7150 |
| 2023 | 2297 | 1040 | 949 | 92317 | 8914 |
| 2024 | 203 | 1813 | 1720 | 105740 | 19113 |
| 2025 | 170 | 1421 | 1320 | 115744 | 11930 |

### Native-mismatch and singleton-support diagnostics

Known mismatch support elsewhere is diagnostic only and never repairs the recorded vintage. Unknown singleton support retains unresolved status and null scalar/node IDs. These categories describe subsets of the preceding states.

| year_filing_for | rows | known_mismatch_absent_all | known_mismatch_valid_elsewhere | unknown_singleton | missing_size |
| --- | --- | --- | --- | --- | --- |
| 2016 | 214978 | 771 | 775 | 0 | 0 |
| 2017 | 259758 | 1465 | 753 | 0 | 0 |
| 2018 | 289534 | 516 | 8205 | 0 | 0 |
| 2019 | 290475 | 2444 | 7863 | 0 | 0 |
| 2020 | 293391 | 1081 | 4079 | 0 | 0 |
| 2021 | 317978 | 809 | 15505 | 0 | 0 |
| 2022 | 346799 | 1716 | 6181 | 0 | 0 |
| 2023 | 394234 | 0 | 0 | 0 | 0 |
| 2024 | 398620 | 281 | 4062 | 203 | 0 |
| 2025 | 400288 | 90 | 9769 | 170 | 0 |

## Protected source and Stage 3 preservation

All following paths (relative to the actual data root) matched before imports and after acceptance, including sizes. The inventory covers every file in both existing verification runs plus the source summary.

| path | bytes | unchanged SHA-256 |
| --- | --- | --- |
| derived/osha/ita_300a_summary.parquet | 139930636 | 6335cda7adb40a41c4a11d57d22048999449ac8d078a2ec0291f0198cd9136a8 |
| derived/osha/verification/v1_v3_20261013/finding.md | 22675 | 00d67972199489df8b87ea788a0ee78f859b0f17ac83c7056cfdd52d10ec618e |
| derived/osha/verification/v1_v3_20261013/geocoding.json | 3181 | c049ad05596f951b4f455da88d3a3d947cbdd1f067a62351160d0ebe2710b51b |
| derived/osha/verification/v1_v3_20261013/inputs.json | 8742 | b05a9317e04b6561c3d0fd6bc24e0c8c3f2a77f4754c473e8718d0de14e3a0b2 |
| derived/osha/verification/v1_v3_20261013/quality.parquet | 3881 | cc047abfbf240396c8f69fb26b23ce0304ae213df4721dfcc06e01fc68158b36 |
| derived/osha/verification/v1_v3_20261013/reports.json | 1907252 | 7772749f2a144f7b87ad8e3c68c8f76091bee1aee0818065e4023f8056f9ccfb |
| derived/osha/verification/v1_v3_20261013/requests/0000.csv | 1044010 | 926bb0cea8e783e4a80dcf5c5bf54130a75267dfbb17b9da3429d5653a2c1437 |
| derived/osha/verification/v1_v3_20261013/requests/0001.csv | 1040413 | 9631f974891dd379c30a276388e2932d3e663c896edef85bc0afa4a7b12e8072 |
| derived/osha/verification/v1_v3_20261013/requests/0002.csv | 66287 | 213084b85ffea6e76bfe40923bd38d8870ffc33bcecb12cab3cca08b38732062 |
| derived/osha/verification/v1_v3_20261013/sample.parquet | 3932310 | e0d84bb7e9561cf2646f89242222185cb537875db94864f217d3d73a94638af7 |
| derived/osha/verification/v1_v3_20261013/v1.parquet | 10393 | 64015ed14a3bd4b53d71738e17f7f32690d68c1b695473184a253dce03b719d9 |
| derived/osha/verification/v1_v3_20261013/v2.json | 7236 | 00bd72b430bec21611c812382c0546539dcc6537c54dde6bb7236b5b299cac54 |
| derived/osha/verification/v1_v3_20261013/v3-strata.parquet | 35558 | caa6d97616765d0032c74f6c546a9c3b53aea17ee11142bd202c25fe9e5bc94f |
| derived/osha/verification/v1_v3_20261013_scopefix/finding.md | 30172 | 5a3e82f5c43f1629eb90746493ff68596376860910614e03663424cd3b24ae35 |
| derived/osha/verification/v1_v3_20261013_scopefix/geocoding.json | 9690 | a6e2fb0861961eae5086c407beb9b9e49d036237ca30c789e29087f5d2490634 |
| derived/osha/verification/v1_v3_20261013_scopefix/inputs.json | 8742 | 93aa3a73abcc97b6c278b5773a4424a9258934e0d0cc4b0086895aabccfeee67 |
| derived/osha/verification/v1_v3_20261013_scopefix/quality.parquet | 3881 | cc047abfbf240396c8f69fb26b23ce0304ae213df4721dfcc06e01fc68158b36 |
| derived/osha/verification/v1_v3_20261013_scopefix/reports.json | 2296439 | 744503f4c3b7334ab16b3e5538dd47e65718c61bde0bad4da475d58aa61c20d7 |
| derived/osha/verification/v1_v3_20261013_scopefix/requests/0000.csv | 1044010 | 926bb0cea8e783e4a80dcf5c5bf54130a75267dfbb17b9da3429d5653a2c1437 |
| derived/osha/verification/v1_v3_20261013_scopefix/requests/0001.csv | 1040413 | 9631f974891dd379c30a276388e2932d3e663c896edef85bc0afa4a7b12e8072 |
| derived/osha/verification/v1_v3_20261013_scopefix/requests/0002.csv | 66287 | 213084b85ffea6e76bfe40923bd38d8870ffc33bcecb12cab3cca08b38732062 |
| derived/osha/verification/v1_v3_20261013_scopefix/sample.parquet | 3932310 | e0d84bb7e9561cf2646f89242222185cb537875db94864f217d3d73a94638af7 |
| derived/osha/verification/v1_v3_20261013_scopefix/v1.parquet | 10393 | 64015ed14a3bd4b53d71738e17f7f32690d68c1b695473184a253dce03b719d9 |
| derived/osha/verification/v1_v3_20261013_scopefix/v2.json | 7236 | 00bd72b430bec21611c812382c0546539dcc6537c54dde6bb7236b5b299cac54 |
| derived/osha/verification/v1_v3_20261013_scopefix/v3-strata.parquet | 37300 | 252895d349483c8e95c10db76f5dec373edcb8ac34186602c2f1783ddb9ace34 |

## Earlier immutable run preservation

The following fifteen files under `derived/codes/stage4_v11_20261013/` matched their pre-remeasurement SHA-256 and size after the new run completed. This older run used execution commit `fdfeaa1df3b5b0273d6fa86481e84b34404e2e01`; the selected run is now `stage4_v11_20261013_r2`.

| filename | bytes | unchanged SHA-256 |
| --- | --- | --- |
| filing_rules.parquet | 6698 | 5f362737c57b7f512d8b1bc710548776c7658b1bc778f98f810279a0d46cd1d9 |
| ita_300a_canonical.parquet | 155974239 | 31b4e30539ab3eacd7cf684569ee8dbc86b21d6fabbcc1882e281603afa82467 |
| report.json | 38114 | 56dfb18ab93f244f4294c015cab38905ca3e3cbf822730e922747dcc6b89f29a |
| naics_concordance.parquet | 19640 | 5384c1c81e973940f459c8cd9210335c5a1da6f5302c47f9fb5338bed9b262d6 |
| soc_edges.parquet | 7036 | 38a224322b1b5f08835a17a1f9e0ddf2592c2e3b343e8cfbe9525f2d176cae28 |
| ita_naics_lookup.parquet | 42902 | b1dfb33644c413ba33698fbf26c1316507382077ae73226ef5c3626d5bc287c8 |
| naics_edges.parquet | 12492 | caade9029e658f023f75056c0e7ebb2f9fa0d285bd91d43a32b65c2ec84d8e9c |
| outputs.json | 1874 | 55c357dcb6c57ffec2509019da439a7c9f477d6181becc6142071ea8537b5822 |
| filing_rule_labels.parquet | 3341 | 349372e5e2e340469622c53acbf42b3fb58b52066ea3953d155475f2037ed7df |
| naics_nodes.parquet | 33378 | 8a0b39dae23802c4a129fe1f89c12ae5c9c7a88eef2d3f9c292f4f4979bc229a |
| inputs.json | 17975 | 9a301fb3b3799f819d326f4171fdbf1ec197047aea8f25738fc5333721fa655f |
| code_paths.parquet | 24742 | ca764663db2337e340b2de60f0507be888fa3a4c06b67cd5e312f929c8d25db9 |
| naics_native_nodes.parquet | 67980 | e0734a9a89bfdf2b9049f1dbff074f124165f79e86bf933a0c9875bdaeebd54d |
| soc_nodes.parquet | 22379 | 7a2259678719b1fc9d5c0cf3809023d6a87bdb4d6aed4b788e2f266e0586d356 |
| filing_rule_membership.parquet | 9842 | 1485c190c5e6d8019f07939240773e14c9dc039111c2c10ae32207ad214d4796 |
