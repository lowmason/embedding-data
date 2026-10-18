# ACS Codes and Area Allocation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

Roadmap: specs/embedding-evaluation-data-spec-roadmap.md, Stage 8 — on plan completion, tick the stage and re-validate later stages against what shipped.

**Status: PLAN FOR REVIEW (2026-10-17)** — implementation has not begun.

**Goal:** Produce verified, row-preserving ACS classification companions and
population allocation references for all three selected deliveries, with measured
V8 and ACS V11 findings and an independent offline replay.

**Architecture:** Add a separate Stage 8 module command and focused modules for
pinned input selection, public reference evidence, strict classification mapping,
geographic factors, role interpretation, companion annotation and immutable
publication. Build small reusable lookups first, then annotate each existing
Parquet with lazy many-to-one joins. A detached verifier and independent aggregate
reconciler gate adoption; Stage 9 owns estimates and eligibility.

**Tech Stack:** Python >=3.14; the locked Polars 2.0.0, fastexcel 0.21.0,
httpx 0.28.1 and Typer stack; pytest/Hypothesis; stdlib csv, decimal, hashlib,
html.parser, json, pathlib, dataclasses, ctypes, tempfile, zipfile and
xml.etree.ElementTree. No dependency,
project configuration or lock change.

**Spec:** [Approved Stage 8 spec](../acs-codes-area-allocation.md), approved in
writing by the owner on 2026-10-16; [source requirements](../embedding-evaluation-data-spec.md)
R3.9, R3.11 crosswalks, R5.1 ACS, R5.3, R5.4 ACS comparator, R6.3, V8 and
ACS V11. R3.10 supplies role keys. Read both specs and the Stage 4, 5 and 7
completed plans' Handoff sections before executing.

## Global Constraints

The following Stage 8 requirements apply verbatim:

- "Use the existing Polars, fastexcel, httpx and Typer stack."
- "Production microdata transforms are lazy Polars with method-style expressions; small public reference tables may be eager."
- "No personal skill directory is a runtime input."
- "All IPUMS microdata and companion Parquets remain local under ignored `data/`; only aggregate findings and public-reference descriptions enter git."
- "Mapping outputs remain evaluation inputs and never become embedder training or model-selection data."
- "No mapping join may expand, drop or reorder person rows."
- "Do not materialize a cross-product of candidate industries, occupations or geographic roles."
- "Do not round factors for storage or repair a missing intersection by renormalizing the remainder."
- "A cached acquisition verifies and returns without HTTP."
- "Build, verify and comparison are offline."
- "No latest-run alias or mixed-run fallback is allowed."
- "An unparseable code fails the build."

Additional binding execution constraints:

- Production root, including from a worktree, is
  `/Users/lowell/Projects/embedding-data/data`. Every command passes `--data-dir`.
- Only acquire/import may retrieve public originals. No Stage 8 command loads
  `.env`, requests credentials or constructs an IPUMS API client. Tests deny all
  three as well as socket/HTTP access outside mocked acquisition tests.
- Consume selected inputs in place. Never call extract submission, conversion
  recovery, upstream builders, `osha`, verification `sample`, Census geocoding
  or a target build to prepare this stage. Converter calls are fixture-only.
- Leave Stage 7's entire `SOFTWARE_FILES` unchanged, including `cli.py`,
  `__init__.py`, `paths.py`, `target_io.py`, `manifest.py`, extraction/conversion,
  shared reference helpers, `pyproject.toml` and `uv.lock`. Leave every other
  upstream frozen executing file unchanged too. No top-level CLI registration.
- No upstream inventory/status rewrite or quiet upstream remeasurement. If a
  shared software change is indispensable, record the deviation and its fresh
  upstream verification requirement before implementing it.
- Preserve Q-prefixed source columns, original ordered schemas, raw strings,
  duplicate multiplicity and delivery-specific missingness/types. No annual
  record borrows a five-year flag. Missing evidence stays unavailable.
- Classification possibilities are unweighted. A singleton never clears
  aggregation, partial-category, source-recoding or vintage-crosswalk provenance.
  Only the explicitly approved OCCSOC `559830` may be a documented special with
  no candidates; this supplies no CPS special-code authority.
- Validate complete originals before scope filtering. Scope is 50 states + DC;
  reference Puerto Rico rows remain measured exclusions. Keep 2020 population,
  2020 PUMA definitions, 2022 county composition, 2025 administrative inventory
  and July 2023 MSA delineations distinct. Never relabel legacy CT counties.
- Reference tables have explicit natural-key sorting and null ordering. Every
  list is typed, nonnull and free of null elements; candidate/reference/reason
  sets are sorted and distinct. Path lists retain root-to-leaf order.
- Integer populations reconcile exactly; factor closure tolerance is `1e-12`.
  Published percentage/factor rounding is a separate diagnostic with explicit
  decimal bounds. An absent relation is not a retained zero-population relation.
- Refuse occupied finals/partials, unsafe paths and symlinks. Failures publish
  no mapping bundle, change no earlier run and clean only owned temporary files.
- Stage 8 does not implement Stage 9–13, ACS universes, headline inclusion,
  target families, employment-weighted code allocation, pooling, replicate SEs,
  worker profiles, V9 or complete eight-family V12 acceptance.
- Stage 8 remains unticked until software, full-data measurements, independent
  replay/reconciliation, preservation checks and reviews pass. Planning does
  not retire the spec or update the roadmap.

## Decisions

- **D1** (owner, brief, 2026-10-16): The written spec is approved. Plan Stage 8
  only, commit the reviewable plan, and stop before implementation. Applied in:
  Global Constraints and the execution handoff.
- **D2** (owner, plan review, 2026-10-17): Separate append-only manifest
  preservation from immutable whole-file checks. Require explicit regressions
  for a fully accounted append passing and a prior-byte mutation failing.
  Applied in: Task 9 and the measured acceptance matrix.

---

## Entry evidence and selected identities

Planning baseline: `d6909f50c86f5640218c49bce27e78cf5e7402f1` on `main`, clean
working tree. The writing-plans entry check examined branches, remote refs and
worktrees: highest ID 7, next free 8, no collision or existing plan for this spec.
The implementation defaults below are proposed engineering choices, not additional
owner decisions or a claim of production acceptance. Planning resumed on
2026-10-17 at the same Git baseline, with only this untracked draft present.
The entry recheck found this allocated plan 8, no collisions and no other plan
for this spec; its reported next free ID 9 does not renumber the existing draft.

| Selected input | Explicit identity | Detached SHA-256 |
| --- | --- | --- |
| codes | `derived/codes/stage4_v11_20261013_r2` | `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |
| geography | `derived/geography/stage5_geography_20261014` | `5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d` |
| IPUMS verification | `derived/ipums/verification/stage7_ipums_verification_20261015_r2` | `db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc` |
| Stage 7 references, `ipums-public-references-v3` | `raw/references/ipums-verification/stage7_ipums_references_20261015_r2/receipt.json` | `3163968dde603ba53f807976dd09b9e40d73235a98c6f36e4e02c67ec4239c9c` |

The first three pins authenticate `outputs.json`; the fourth authenticates a
receipt. The selected Stage 7 finding supplies adopted interpretations separately
from its expected machine `measurement_status=unresolved`.

| Profile | Existing relative Parquet | Rows / original columns | SHA-256 |
| --- | --- | --- | --- |
| `acs/core` | `derived/acs/core/usa_00001.parquet` | 3,206,859 / 147 | `c07f9e7abe2c5dfdb8f9488a1f574d4cf49ab7945c3ad2ffc9daec5eaba47d10` |
| `acs/five_year` | `derived/acs/five_year/usa_00003.parquet` | 7,456,212 / 148 | `c5846bde221e7785051a4a4075aa6a71cc267a1f4497168a96df05d7c50f78fe` |
| `acs/vintage` | `derived/acs/vintage/usa_00002.parquet` | 1,575,420 / 146 | `b6ffab7bd974f72b4fbc913f261779f5ce3145a915849bf92e946bb6b649240d` |

Total: **12,238,491 source rows**, with no person-row deduplication. Raw triples
are the manifested `extract.json`, matching `.xml` and `.csv.gz` under
`raw/acs/<set>/<delivery>/`. Obtain all exact hashes, sizes, ordered schemas and
citations from the verified Stage 7 `inputs.json['deliveries']`; do not reconstruct
them from filenames or update its five-profile selection.

Observed metadata confirms YEAR/SAMPLE/IND/OCC and all six geographic source keys
are Int64. INDNAICS/OCCSOC are String. MULTYEAR is Int64 in five-year and absent
elsewhere. QMIGRAT1 is String in core, Int64 in five-year, and absent in vintage.
The [Stage 7 flag evidence](../findings/stage-7-ipums-extract-verification.md#allocation-flags-and-actual-typedomain-traps)
governs applicability and the all-null 2023 core partition.

### Existing interfaces to reuse without editing

| Interface | Reuse / limitation |
| --- | --- |
| `classification_tables.NODE_SCHEMA`, `EDGE_SCHEMA`, `PATH_SCHEMA`; `naics_tables(titles, vintage)` | Canonical paths are node-ID lists; reconstruct native-2017 paths in memory from selected `naics_native_nodes`. Published `code_paths` contains only NAICS 2022/SOC 2018. |
| `naics_relationships.validate_relationships(relations, structures)`; `candidates(relations, source_vintage, source_code, target_vintage)` | Validate all four bridges, not a sliced last bridge; traverse the complete relation without code-equality shortcuts. |
| `geography_tables.COUNTY_SCHEMA`, `CBSA_SCHEMA`, `identifier(level, code)` | Use selected county and typed CBSA nodes. CBSA state membership is a set, not a state parent. |
| `ipums_verification_run.verify_bundle(directory, data_dir, *, expected_outputs_sha256)` | Required first check; it rechecks all five selected deliveries and exact current upstream software/dependencies. Its conservative substantive status is expected. |
| `ipums_references.check_references(data_dir, reference_id)` | Verify/cite existing originals in place. Its closed registry and industry `code/title` parser do not supply Stage 8 NAICS membership. |
| `target_io.relative_file`, `file_record`, `inventory`, `verify_inventory`, `verify_raw`, `write_json` | Read-only reuse. Add an exact immediate-path set check, including directories. `verify_inventory` alone overlooks extra empty directories. |
| `manifest.entry_for(manifest_path, raw_file)` | Verifies current bytes and size; `recorded_entry_for` is not integrity evidence. |
| `ipums_parity.compare_ordered(expected, actual, *, chunk_size=16384)` | Bounded full ordered comparison of schemas, values and duplicates. Use for original prefixes and eight-table replay. |
| `ipums_conversion.convert(csv_gz, parquet_path, source)` | Fixture raw-to-Parquet seam only. |

Do not call `target_inputs.select`: it is coupled to ITA source/table checks.
Do not import private upstream bundle selectors as the Stage 8 API. Reuse schema
constants, then verify the complete selected inventories, declared versions,
recorded table schemas/counts, raw citations and compatibility in the new selector.
The ITA parser and its unresolved-source exception do not implement ACS rules.

## File responsibilities and task dependency order

All `src/embedding_data/` files below are **new**. Existing shared software is
read-only. Tests use new files rather than widening frozen production registries.

| File | Responsibility / first task |
| --- | --- |
| `src/embedding_data/acs_mapping_contract.py` | Eight exact table schemas, keys, enums, versions and common immutable selection types; Task 1 |
| `src/embedding_data/acs_mapping_inputs.py` | Detached upstream selection, source identities and protected input/software rechecks; Task 1 |
| `src/embedding_data/acs_mapping_io.py` | Caller-owned staging and atomic no-replacement directory publication; Task 1 |
| `src/embedding_data/acs_mapping_references.py` | Closed Stage 8 public registry, acquisition/import, receipts and cache verification; Task 2 |
| `src/embedding_data/acs_code_references.py` | Strict original-layout classification relations, expression parser and evidence/conflict validation; Task 3 |
| `src/embedding_data/acs_code_mapping.py` | Scheme selection, code lookups, native/canonical candidates, reasons and flags; Task 4 |
| `src/embedding_data/acs_area_references.py` | Strict Geocorr/composition/MSA originals and public role/state rules; Task 5 |
| `src/embedding_data/acs_geography_factors.py` | Integer populations, residence and shared work/migration county factors, V8 and MSA coverage; Task 5 |
| `src/embedding_data/acs_area_mapping.py` | Role-specific observed-key interpretation and source-geography provenance; Task 6 |
| `src/embedding_data/acs_mapping_companions.py` | Lazy source-preserving annotation, prefix fidelity and partition diagnostics; Task 7 |
| `src/embedding_data/acs_mapping_bundle.py` | Build, reread validation, frozen inventories, public verification and comparison; Task 8 |
| `src/embedding_data/acs_mapping.py` | Separate `python -m` Typer command group; Task 8 |
| `scripts/reconcile_stage8.py` | Independent populations/code frequencies/status/preservation calculations; Task 9 |
| `tests/acs_mapping_fixtures.py`, `tests/fixtures/acs_mapping/` | Genuine public layout excerpts and explicit synthetic raw deliveries; Tasks 1–8 |
| `tests/test_acs_mapping_contract.py`, `tests/test_acs_mapping_inputs.py`, `tests/test_acs_mapping_io.py`, `tests/test_acs_mapping_references.py` | Input trust, schema and lifecycle failures; Tasks 1–2 |
| `tests/test_acs_code_references.py`, `tests/test_acs_code_mapping.py` | Source-backed membership/parser/vintage tests; Tasks 3–4 |
| `tests/test_acs_area_references.py`, `tests/test_acs_geography_factors.py`, `tests/test_acs_area_mapping.py` | Geographic originals, arithmetic and role statuses; Tasks 5–6 |
| `tests/test_acs_mapping_companions.py`, `tests/test_acs_mapping_bundle.py`, `tests/test_acs_mapping_cli.py`, `tests/test_acs_mapping_v12.py` | Preservation, publication, offline integration and replay; Tasks 7–8 |
| `tests/test_stage8_reconciliation.py` | Independent reconciler against hand-calculated fixture truth; Task 9 |
| `README.md`, `CLAUDE.md` | Usage, shipped interfaces and limits; Task 8 onward, after verifying they are outside upstream frozen inventories |
| `specs/findings/stage-8-acs-codes-area-allocation.md` | Actual measured production finding; Task 9 |

Execute Tasks 1–10 in order, with a test/review checkpoint and a small commit at
each task. Task 3 and Task 5 have independent parser responsibilities after
Tasks 1–2, but integrate and gate them in the stated order. In a subagent-driven
execution, assign a worker exclusive ownership of that task's files, tell it
others may be working, and never let it revert another worker's edits.

## Frozen `acs-mapping-v1` table contract

Freeze these definitions in Task 1, before writers. Version constants:
`FORMAT_VERSION='acs-mapping-v1'`, `REFERENCE_VERSION='acs-mapping-references-v1'`,
`CODE_RULE_VERSION='acs-code-rules-v1'`, `AREA_RULE_VERSION='acs-area-rules-v1'`.
Change a rule version and use new reference/run identities if accepted evidence
or semantics change; never repair published inventories in place.

Use the following exact ordered Polars schema definitions. `?` in prose means
nullable values of the declared dtype, not a different dtype. No Null/Object
columns, inferred empty-list types or untyped flags are allowed.

```python
import polars as pl

S, I, F, B = pl.String, pl.Int64, pl.Float64, pl.Boolean
LS = pl.List(S)
LLS = pl.List(LS)

CODE_SCHEMA = {
    'code_lookup_id': S, 'system': S, 'source_scheme': S,
    'native_vintage': I, 'canonical_vintage': I,
    'paired_census_code': S, 'source_token': S, 'mapping_status': S,
    'native_node_id': S, 'native_finest_candidates': LS,
    'canonical_finest_candidates': LS, 'canonical_candidate_paths': LLS,
    'canonical_common_node_id': S, 'canonical_scalar_code': S,
    'canonical_scalar_node_id': S, 'aggregation_type': S,
    'aggregation_markers': LS, 'aggregation_reason_status': S,
    'aggregation_reasons': LS, 'special_reason': S,
    'flag_aggregate': B, 'flag_partial': B, 'flag_exception': B,
    'flag_vintage_crosswalk': B, 'flag_reference_ambiguity': B,
    'reference_ids': LS, 'reference_locators': LS, 'rule_version': S,
}
AREA_SCHEMA = {
    'area_lookup_id': S, 'profile': S, 'sample_id': S,
    'release_year': I, 'component_year': I, 'role': S,
    'source_state_code': S, 'source_area_code': S,
    'state_fips': S, 'area_code': S, 'area_type': S,
    'puma_vintage': I, 'area_status': S, 'status_reason': S,
    'factor_key': S, 'flag_source_geography_recoded': B,
    'source_allocation_evidence_status': S,
    'reference_ids': LS, 'reference_locators': LS, 'rule_version': S,
}
COUNTY_FACTOR_SCHEMA = {
    'factor_key': S, 'area_type': S, 'state_fips': S, 'area_code': S,
    'county_geoid': S, 'county_node_id': S,
    'intersection_population': I, 'area_population': I, 'county_population': I,
    'factor': F, 'published_area_factor': F, 'published_county_factor': F,
    'population_year': I, 'puma_vintage': I, 'county_composition_year': I,
    'county_inventory_vintage': I, 'flag_geographic_allocation': B,
    'flag_fractional_split': B, 'reference_ids': LS, 'reference_locators': LS,
}
MSA_FACTOR_SCHEMA = {
    'state_fips': S, 'puma_code': S, 'msa_code': S, 'msa_node_id': S,
    'puma_population': I, 'msa_population': I, 'intersection_population': I,
    'puma_to_msa_factor': F, 'msa_to_puma_factor': F,
    'published_percent_puma': F, 'published_percent_msa': F,
    'population_year': I, 'puma_vintage': I, 'msa_delineation': S,
    'county_inventory_vintage': I, 'flag_geographic_allocation': B,
    'flag_fractional_split': B, 'reference_ids': LS, 'reference_locators': LS,
}
MSA_COVERAGE_SCHEMA = {
    'state_fips': S, 'puma_code': S, 'puma_population': I,
    'msa_population': I, 'non_msa_population': I,
    'msa_fraction': F, 'non_msa_fraction': F,
    'population_year': I, 'puma_vintage': I, 'msa_delineation': S,
    'reference_ids': LS, 'reference_locators': LS,
}
```

Natural keys and sort order:

- Code: `(system, source_scheme, paired_census_code, source_token)`.
- Area: `(profile, sample_id, release_year, component_year, role,
  source_state_code, source_area_code)`.
- County factors: `(area_type, state_fips, area_code, county_geoid)`.
- MSA factors: `(state_fips, puma_code, msa_code)`.
- MSA coverage: `(state_fips, puma_code)`.

Use `.sort(keys, nulls_last=False)` for each reference table. Lookup IDs are
SHA-256 of UTF-8 canonical JSON arrays of the complete natural key, with JSON
null distinct from an empty string; check ID uniqueness against unique natural
keys. `factor_key` hashes `(area_type, state_fips, area_code, 2020)`.
`canonical_candidate_paths[i]` is the selected official path for
`canonical_finest_candidates[i]`; never sort the nodes within a path.

Nullable CODE fields: native node, common node, scalar code/node, special reason.
For a published numeric official node, retain its declared native node/depth,
including when it has only one finest descendant. For a non-node aggregate,
the native node is its deepest supported common official native ancestor, if
one exists; it describes containment, not equality to that whole category.
Preserve candidates and every aggregate/partial flag alongside it. No shared
root is invented for candidates from different trees.
Only `mapped` and `documented_special` occur in this lookup. Missing source codes
get companion `missing` status, no lookup ID, empty typed candidate lists and
separate counts; malformed nonmissing codes fail. Missing and special never
count as mapped. `aggregation_reason_status` is `documented`, `unknown` or
`not_applicable`; reasons are source-supported `category_design` and/or
`disclosure`, otherwise an empty list plus `unknown` and the inspected locators.

AREA nullable fields: raw lexical source-state/area representations where null
is documented, normalized state/area, factor key and source recoding flag where
applicability cannot be determined. Every observed row still has a cited,
nonnull `area_status` and reason. Allowed statuses: `applicable`,
`niu_or_unidentifiable`, `foreign`, `territory`, `documented_unavailable`.
Unexplained nulls or invalid pairs are errors, not another successful status.
Factor keys are nonnull only for applicable in-scope keys.

COUNTY_FACTOR published factors are nullable only for derived work/migration
rows, where no direct published factor exists. `flag_geographic_allocation=True`
for every factor use, including factor one. `flag_fractional_split` means the
area has more than one positive county intersection; a retained zero row alone
does not imply a split. For MSA factors it means `0 < intersection < puma_population`.
All populations and frame fields are nonnull. No denominator may be zero.

The three companion schemas consist of the exact ordered source schema followed
by the following ordered suffix. Build the suffix with the code below:

```python
IDENTITY_SCHEMA = {
    'source_parquet_sha256': S, 'source_row': pl.UInt64,
    'acs_profile': S, 'acs_sample_id': S, 'acs_release_year': I,
    'acs_component_year': I, 'industry_delivered_scheme': S,
    'industry_interview_scheme': S, 'occupation_delivered_scheme': S,
    'flag_source_industry_recoded': B,
    'industry_source_allocation_status': S,
    'occupation_source_allocation_status': S,
    'industry_source_allocated': B, 'occupation_source_allocated': B,
    'migration_source_allocation_status': S, 'migration_source_allocated': B,
    'source_flag_reference_ids': LS,
}
CODE_ANNOTATIONS = ('code_lookup_id', 'source_token', 'mapping_status',
    'native_vintage', 'canonical_vintage', 'paired_census_code',
    'native_node_id', 'native_finest_candidates', 'canonical_finest_candidates',
    'canonical_candidate_paths', 'canonical_common_node_id',
    'canonical_scalar_code', 'canonical_scalar_node_id', 'aggregation_type',
    'aggregation_markers', 'aggregation_reason_status', 'aggregation_reasons',
    'special_reason', 'flag_aggregate', 'flag_partial', 'flag_exception',
    'flag_vintage_crosswalk', 'flag_reference_ambiguity',
    'reference_ids', 'reference_locators', 'rule_version')
ROLE_ANNOTATIONS = ('area_lookup_id', 'state_fips', 'area_code', 'area_type',
    'puma_vintage', 'area_status', 'status_reason', 'factor_key',
    'flag_source_geography_recoded', 'source_allocation_evidence_status',
    'reference_ids', 'reference_locators', 'rule_version')
ANNOTATION_SCHEMA = dict(IDENTITY_SCHEMA)
for prefix in ('industry', 'occupation'):
    ANNOTATION_SCHEMA.update({f'{prefix}_{name}': CODE_SCHEMA[name]
                              for name in CODE_ANNOTATIONS})
for prefix in ('residence', 'workplace', 'migration'):
    ANNOTATION_SCHEMA.update({f'{prefix}_{name}': AREA_SCHEMA[name]
                              for name in ROLE_ANNOTATIONS})
    ANNOTATION_SCHEMA.update({f'{prefix}_flag_geographic_allocation': B,
                              f'{prefix}_flag_fractional_split': B})
```

These loops define the full suffix, not permission to add inferred source
columns. The suffix has exactly 114 fields, giving selected companion widths
261 core / 262 five-year / 260 vintage. Original columns may not collide with
any suffix name. Derived source
allocation Booleans are nullable: true for a documented applicable allocated
value, false only with evidence of applicable nonallocation, null when the flag
is absent/null or combines NIU with an unresolved applicability state. Status
strings distinguish `allocated`, `not_allocated`, `not_allocated_or_niu`,
`not_applicable` and `unavailable`. Preserve the raw Q values regardless.

Core annual 2023/2024 uses release/component year 2023/2024 respectively.
Vintage annual 2022 uses 2022. Five-year uses release 2024 and MULTYEAR component
2020–2024. Its delivered industry scheme is NAICS 2022 throughout; interview
scheme records documented 2017 for pre-2023 components and 2022 thereafter,
without reconstructing the pre-recoding value. Source recoding provenance is
separate from Stage 8's native-2017 concordance flag. Delivered occupation is
SOC 2018 throughout. All selected geographic roles use 2020 definitions;
source-assigned 2020 geography is flagged on five-year components before 2022.

## Public reference layout evidence

Planning inspection uses public originals in temporary storage only. These paths
are not implementation inputs and must never appear in a production receipt.
Acquire/import and manifest the production originals in Task 2. The exact public
layouts below were inspected again on 2026-10-16 and agree with the spec pins.

| Registered kind | Official URL / exact layout | Inspected SHA-256 |
| --- | --- | --- |
| `county_composition_2022` | [County composition XLS](https://usa.ipums.org/usa/resources/volii/county_migpuma_pwpuma_2022.xls); sheet `MIGPUMA-POWPUMA 2022 Lookup`, header row 0; columns `State of Residence (ST)`, `County of Residence`, `Place of Work State (PWSTATE2) or Migration State (MIGPLAC1)`, `PWPUMA00 or MIGPUMA1`; 3,222 data rows | `bd42f18ee36a10d91404be78106e60c613b6ec8ce53e9bc5860753af497ffadf` |
| `puma_composition_2020` | [PUMA composition XLS](https://usa.ipums.org/usa/resources/volii/puma_migpuma1_pwpuma00_2020.xls); sheet `PUMA_POWPUMA_MIGPUMA`, header row 0; same state/group columns, second column `PUMA`; 2,486 data rows | `022e4784cb08dcf01acfa4f680564cd26ba79e867f6643ee683577fde0b37a5d` |
| `msa_puma_2023_2020` | [MSA/PUMA XLSX](https://usa.ipums.org/usa/resources/volii/MSA2023_PUMA2020_crosswalk.xlsx); sheet `MSA2023_PUMA2020_crosswalk`, 2,358 data rows; exact eleven headers below | `80763eaf73cbda1b59818bdbf7650058eebbe18fa8a697599e645b3df235258f` |
| `geocorr_form` | [Current form](https://mcdc.missouri.edu/applications/geocorr2022.html); GET form `/cgi-bin/broker`, source `g1_=puma22`, target `g2_=county`, `wtvar=pop20`; `CTcounty` is a separate legacy selector | `96ce8006b044529e8c23209e3d17de8921df2465dabaa3dd216c8367c0e94b40` |
| CT-only CSV layout evidence | Temporary request, response page and CSV; 27 data rows plus names and descriptive-label rows; not a nationwide input or V8 finding | `57a0937d0a8961efd61ecc1c382d3b34d6dfddca303169c610b8786ac0734e8e` |

MSA raw headers, preserving spaces until exact layout validation:

```python
MSA_HEADERS = ['MSA Code', 'MSA Title', 'State FIPS Code', 'State Name',
    'PUMA Code', 'PUMA Name', 'MSA 2020 Population ', 'PUMA 2020 Population ',
    ' Intersection 2020 Population ', 'Percent MSA Population',
    'Percent PUMA Population']
GEOCORR_HEADERS = ['state', 'puma22', 'county', 'stab', 'CountyName',
                   'PUMA22name', 'pop20', 'afact2', 'afact']
```

Geocorr `afact` is PUMA-conditioned and `afact2` county-conditioned even when the
second factor appears first in the physical CSV. Four-decimal published fractions
have absolute rounding tolerance `0.00005 + 1e-12`; MSA's four-decimal percentages
have tolerance `0.00005 + 1e-12` on the **0–100** scale. Parse lexical Decimal
values first; fewer displayed decimals such as `1` or `100` do not relax this
bound. Integer numerator/denominator agreement remains exact.

For the full production Geocorr request, select every form state including PR
(52 entries) so full composition originals can reconcile before applying scope.
Use deterministic state-FIPS order and repeated `state` query keys. Freeze form,
exact ordered parameters/query bytes, response HTML and generated CSV. Include
all empty controls; the preflight confirmed the following successful payload:

```python
GEOCORR_CONTROLS = [
    ('_PROGRAM', 'apps.geocorr2022.sas'), ('_SERVICE', 'MCDC_long'),
    ('_debug', '0'), ('g1_', 'puma22'), ('g2_', 'county'), ('wtvar', 'pop20'),
    ('nozerob', '1'), ('fileout', '1'), ('filefmt', 'csv'), ('lstfmt', 'html'),
    ('title', ''), ('afacts2', 'on'), ('counties', ''), ('metros', ''),
    ('places', ''), ('oropt', ''), ('latitude', ''), ('longitude', ''),
    ('distance', ''), ('kiloms', '0'), ('locname', ''),
]
```

The inspected CT preflight used POST with these controls plus `state=Ct09`;
production follows the captured form's GET method and records that method.
Both the query response's version (`1.9`, revised 2026-08-31) and the form's
displayed version (`1.8`) are retained, not silently equated. Generated links
may have trailing ASCII whitespace; normalize that documented HTML attribute
padding before an allowlisted same-authority fetch. Require processing-completed
evidence, expected header/label rows and nonempty valid records; an HTTP 200 SAS
error page is a failure, never an empty relation or an automatic retry.

Workplace specials are `00000` NIU/unidentifiable and `00001` outside US/PR;
migration additionally uses `00002` prior PR residence. Preserve the distinct
meaning of migration `00000` (under age one or same house), with no inferred
zero-flow record. Freeze the [PWPUMA00](https://usa.ipums.org/usa-action/variables/PWPUMA00),
[MIGPUMA1](https://usa.ipums.org/usa-action/variables/MIGPUMA1),
[PWSTATE2](https://usa.ipums.org/usa-action/variables/PWSTATE2),
[MIGPLAC1](https://usa.ipums.org/usa-action/variables/MIGPLAC1),
[PUMA](https://usa.ipums.org/usa-action/variables/PUMA) and
[MULTYEAR](https://usa.ipums.org/usa-action/variables/MULTYEAR) pages and their
codes/comparability evidence. The delivered DDI was also inspected on
2026-10-17: PWSTATE2 has two-digit domestic codes (`01` Alabama), `72` Puerto
Rico and `80` abroad; MIGPLAC1 has three-digit domestic codes (`001` Alabama),
`110` Puerto Rico and `150` Canada. All are Int64 in the original Parquets.
The composition workbook's three-digit group-state representation is a separate
reference encoding. Map each representation through its own documented
correspondence; do not pad every role identically or read MIGPLAC1 `110` as a
domestic state. Foreign codes never pass a numeric/zfill conversion into
domestic states. The original DDI has no enumerated PWPUMA00/MIGPUMA1 categories,
so their special meanings require the public role documentation as well.

### Independent geographic control totals

In addition to the complete PUMA/county intersections, freeze two Geocorr control
queries with the same 52-state universe, population weight and empty controls:
PUMA→state (`g1_=puma22`, `g2_=state`) and county→state (`g1_=county`,
`g2_=state`). Their `pop20` columns independently provide whole-PUMA and
whole-county denominators. This prevents a missing intersection from passing
closure merely because the implementation sums the remaining rows.

CT-only GET preflights were inspected on 2026-10-16:

| Control | CSV SHA-256 | Exact header order / data rows |
| --- | --- | --- |
| PUMA totals | `80bb08f1d97e7dbba8fa2df551ab3bf9a3d23f65d2182ff49afd6d38be43c1c2` | `state,puma22,stab,PUMA22name,pop20,afact2,afact`; 25 data rows after the two header/label rows |
| County totals | `9931fe26b2bb829b3c5a388a8d5fa78812ebcf7d45a7b2d077856d408cce39c0` | `county,state,stab,CountyName,pop20,afact2,afact`; 9 data rows after the two header/label rows |

Neither CT slice is a production denominator source. The complete queries and
their exact request/response/CSV originals are required in the production
snapshot. Check PUMA and county key sets against the independent composition
originals, and check all integer totals before scope filtering. Retain any
explicit zero-population intersection; the selected positive-block query does
not promise to enumerate relationships with no positive-population blocks.

### Classification originals, membership and reference conflict gate

These public bytes/layouts were inspected on 2026-10-16. They must be
reacquired/imported under the production receipt. Temporary preflight storage
was absent when planning resumed; the plan retains identities/layouts rather
than depending on temporary files. Hash changes require a fresh inspected
edition and explicit rule/registry review before parser implementation proceeds.
Worksheet locators below are one-based when cited as rows; parser header
discovery requires exactly one match to the registered header tuple.

| Kind | Official original, exact sheet and layout | Inspected SHA-256 |
| --- | --- | --- |
| `ipums_ind_pairs` | [Paired industry XLSX](https://usa.ipums.org/usa/resources/volii/ind_indnaics_crosswalk_2023.xlsx), `Sheet1`, 476×16; current IND columns F/G for 2018–2022 / 2023–2027, corresponding INDNAICS N/O, title P | `4d3f571905a9eddd905213878351c284ecf80ee48733e79cb9375181d70679a8` |
| `ipums_ind_tokens` | [Token industry XLSX](https://usa.ipums.org/usa/resources/volii/indnaics_crosswalk_2023.xlsx), `Sheet 1`, 476×10; current token columns H/I, title J | `96c767a70c1bf707d828fb186e4711a58b9dff73dc2bba99a7038127e75048c0` |
| `pums_industry_2017` | [2018 ACS PUMS/SIPP XLSX](https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2018-ACS-PUMS-and-2018-SIPP-Public-Use-Industry-Code-List.xlsx), `ACS`, 379×5; B description, C `2017 Industry Code`, D `2017 NAICS Code`, E `2017 NAICS Based Code`; `SIPP` is a different sheet | `6f569f8bfcd1955db2f75ed4ec31dc836dea7faebf24375567107b725967f4d2` |
| `pums_industry_2022` | [2023 ACS PUMS/2024 SIPP XLSX](https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2023-ACS-PUMS-and-2024-SIPP-Public-Use-Industry-Code-List.xlsx), `ACS`, 373×5; equivalent 2022 columns | `e6f9ec64ed2519c667a032d9766b460e50cf0ac085b7dd00ae97a98dc588816d` |
| `ipums_occ_pairs` | [Paired occupation XLSX](https://usa.ipums.org/usa/resources/volii/occ_occsoc_crosswalk_2000_onward.xlsx), `Codes without Descriptions`, 837×16, current OCC H / OCCSOC O / title P; `Codes with Descriptions`, 837×30, current OCC N / OCCSOC AB, changes O/AC, title AD | `f95672c481af85302bc2f445888e2f5e493afffa6d88a5ca042b66a39cfc34f1` |
| `census_occupation_2018` | [Full Census occupation XLSX](https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2018-occupation-code-list-and-crosswalk.xlsx), `2018 Census Occ Code List`, 667×4; B title, C Census code, D SOC expression, 570 distinct four-digit rows; preserve `2010 to 2018 Crosswalk ` sheet's trailing space | `fca2818d691c32777a4cd733a9ab77c8c5bd47adcacd7ac3aa149bebd45b5f7f` |
| `pums_occupation_2018` | [ACS PUMS occupation XLSX](https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2018-ACS-PUMS-and-2018-SIPP-Public-Use-Occupation-Code-List.xlsx), `ACS`, 886×3; headers `2018 Census PUMS Occupation Code`, `2018 SOC Code`, `Description (2018 Census Occupation Code)`; 530 categories including 9920 | `20cc7112cf96c7a3648b579cc0b2af239bea1c9094885a0d986959888695fe0a` |
| `pums_annual_2024` | [2024 annual code lists XLS](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/code_lists/ACSPUMS2024CodeLists.xls), `Industry` 373×5 and `Occupation` 886×3; occupation heading still names 2023, so product identity is separately registered | `f8c945c383322f123b5d409fd1cd1352f23ace3c0ffff5de0bc1cf414886d40d` |
| `pums_five_year_2024` | [2020–2024 code lists XLSX](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/code_lists/ACSPUMS2020_2024CodeLists.xlsx), `Industry` 373×5, `OCCP & SOCP` 886×3, `IND README` 80×4, `2017 to 2022 IND Crosswalk` 386×14 and `IND Recodes & Conversion Rates` 242×20 | `634fdd565249d72f09a8f75d82fe4193b20a09d898ef64a4b8e8039348d52994` |
| `pums_annual_guide` | [2024 PUMS guide](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/2024ACS_PUMS_User_Guide.pdf), section VIII.I and adjacent code representation/mapping sections | `70d485604dfd89534eef7d491a219ab7d336f98e724732985a0a859eac5d9787` |
| `pums_five_year_guide` | [2020–2024 guide](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/2020_2024ACS_PUMS_User_Guide.pdf), physical pages 18–19, sections VIII.I–L | `77f9b74efef7cb9d3eb8ffa4dc875df9e15765432d6134ead3691a5fe8b35e1a` |

Cite the Stage 7 2017/2022 full Census industry workbooks in place, with hashes
from its verified receipt. Those full lists contain 0480, absent from the PUMS
lists, and cannot substitute for them. The same-release five-year `IND README`
rows 12–14 documents single-vintage delivered industry; rows 20–32 describe
already-applied conversion. Preserve source recoding provenance; never apply
those rates again as Stage 8 weights.

Also register the following exact HTML identities and freeze returned bytes in
the new receipt: IPUMS variable pages `INDNAICS`, `OCCSOC`, `IND` and `OCC` at
`https://usa.ipums.org/usa-action/variables/<NAME>`; the code/legend pages
[industry tokens](https://usa.ipums.org/usa/volii/indnaics.shtml),
[paired industry](https://usa.ipums.org/usa/volii/indtoindnaics.shtml),
[SOC 2018 tokens](https://usa.ipums.org/usa/volii/occsoc18.shtml) and
[paired occupation](https://usa.ipums.org/usa/volii/occtooccsoc18.shtml).
Their crosswalk tables use `table.condensed`, two header rows and shorter
section-heading rows. Grouped header cells are not individual data columns.
For docs without an inspected fixed hash in this plan, record the actual bytes,
content/layout checks and receipt pin before freezing the production snapshot.
PDFs are pinned documentary evidence with reviewed section locators, not a
new PDF runtime dependency or a reason to alter the frozen lock.

**Reviewable authority default:** use the registered Census **ACS PUMS** rows as
the industry pair/membership authority for the declared scheme; use IPUMS for
token/marker semantics and keep its current paired-industry workbook/HTML as
diagnostic evidence. This is a bounded response to the exact defects below,
not a generic source precedence rule or permission to ignore contradictions.
Keep all rejected assertions and their locators in the reference diagnostics.
If plan review does not approve these roles, Task 3 must stop on the conflict.
Any new unexplained disagreement, active-authority contradiction or source-pair
mismatch fails. No source value is corrected, relabelled or waived under the
ITA source-defect exception.

The inspected IPUMS workbook rows 7–8 associate 0190→1133 and 0270→113M,
where the applicable Census PUMS tables associate 0190→113M and 0270→1133.
Utilities rows 21/23 similarly interchange 0590/0680 between 22132 and 221MP.
The preflight compared **every observed industry pair**, after checking all
three source hashes:

| Profile | Component/pair keys | Rows | Census PUMS mismatches | Distinct pair conflicts / missing pairs in current IPUMS table |
| --- | ---: | ---: | ---: | --- |
| core | 528 | 3,206,859 | 0 | 16 / 21, affecting 102,722 / 97,635 rows |
| five-year | 1,320 | 7,456,212 | 0 | 16 / 21, affecting 243,305 / 230,641 rows |
| vintage | 269 | 1,575,420 | 0 | 15 / 11, affecting 50,964 / 22,378 rows |

These are design diagnostics, not ACS V11 closure. Reproduce them in the measured
finding, retaining pair/component versus distinct-pair grains. Occupation had
529 observed OCC/OCCSOC pairs per profile and zero pair mismatches against the
current IPUMS occupation workbook; candidate membership still needs the separate
PUMS/full-Census/SOC relations.

Source-backed fixture cases, with exact candidate sets obtained by resolving the
published expressions against the selected official structures:

| Scheme / token / paired Census code | Published ACS relation / expected result |
| --- | --- |
| 2022 `111` / `0170` | row 25, coarse node 111; every official finest descendant |
| 2022 `22132` / `0680` | row 207, coarse node; singleton `221320`, still coarse |
| 2022 `113M` / `0190` | row 27, `1131, 1132` → `113110,113210` |
| 2022 `311M1` / `1070`; `311M2` / `1280` | rows 46/53, `3111,3112` versus `3117,3119`; different sets of nine finest descendants |
| 2022 `2211P` / `0570`; `2212P` / `0580` | rows 203/204, 2211 versus 2212 scope; latter singleton `221210`, partial provenance retained |
| 2022 `221MP` / `0590` | row 205, `Pts. 2211,2212`; eleven supported possibilities, multiple and partial flags |
| 2022 `22S` / `0690` | row 208, `Part of 22`; explicit sector/unspecified/partial semantics |
| 2022 `3118Z` / `1270` | row 52, `3118 exc. 311811` → `311812,311813,311821,311824,311830` |
| 2022 `3219ZM` / `3875` | row 119, exclude 321991/321992 → `321911,321912,321918,321920,321999` |
| 2022 `332MZ` / `2980` | row 96, `3325,3326,3329 exc. 332992,332993,332994`; retain all ten supported finest members |
| 2022 `333MS` / `3291`; `33MS` / `2990`; `3MS` / `3990` | rows 103/97/124; explicit roots/part clauses. `33MS` means part of 331 and 332, not the entire nominal 33 prefix |
| 2017 `928110P1`–`928110P7` versus 2022 `92811P1`–`92811P7` | distinct eight/seven-character source tokens; each possible finest member `928110`, branch suffix and partial provenance retained |
| SOC 2018 `1110XX` / `0010` | ACS rows 17–20 → `11-1011,11-1031` |
| SOC 2018 `15124X` / `1065` | ACS rows 103–106 → `15-1242,15-1243` |
| SOC 2018 `1721XX` / `1520` versus `1721YY` / `1530` | ACS rows 140–147 → `17-2151,17-2171` versus `17-2161,17-2199`; X/Y sets differ |
| SOC 2018 `1940YY` / `1970` | ACS rows 205–211, nested `Combines:` blocks → `19-4061,19-4071,19-4092,19-4099` |
| SOC 2018 `291210` / `3090` | ACS rows 320–336, thirteen detailed physicians, including the official overflow children of `29-1210` |
| SOC 2018 `559830` / `9830` | ACS row 879 and guide pseudo-code evidence; empty native/canonical candidates, null nodes/scalars |

The occupation sheet's row 884 explains highlighting for confidentiality
combinations. In the inspected XLSX, `1110XX` cells A17:C17 use fill 3, whose
`xl/styles.xml` is solid theme 7/tint `0.79998168889431442`. Use stdlib ZIP/XML
to resolve cell style→fill and the sheet's legend; fastexcel values discard it.
`15124X` already aggregates the full Census 1065 category (full-list row 94),
so its category-design membership has explicit evidence; absence of highlighting
alone never identifies a reason. Record `disclosure` for supported highlighted
PUMS combinations and `category_design` only when the original Census category
and documentation support it. This describes mapping provenance, not a claim
about why Census originally designed every category. Unresolved per-code reasons
stay `unknown` with inspected locators. Fixtures must include both documented
cases and an unknown case; missing styles/contradictory legends fail rather
than clearing a reason.

## Task execution

Commands below run from the repository/worktree root with
`UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache`. Use `uv run --offline --locked`
for Python/tests; `--offline` controls package fetching, so the explicit network
denial tests remain necessary. Each red step must fail for the new missing or
incorrect behavior, then pass after implementation. Do not accept an unrelated
fixture/setup failure as the red evidence. Record the command and observed result
at each checkpoint; review the task diff before committing.

New test modules import `pytest`, `polars as pl` and the exact module APIs named
in their task's Interfaces block at file scope. Fixture implementations live in
`tests/acs_mapping_fixtures.py` or the test file named by the task; no snippet
assumes an undocumented production helper or a fixture-only acceptance bypass.
Create each Task 1–8 source/test file only during execution, not while reviewing
this plan.

### Task 1: Pinned input trust, typed contracts and exclusive publication

**Files:**

- Create: `src/embedding_data/acs_mapping_contract.py`
- Create: `src/embedding_data/acs_mapping_inputs.py`
- Create: `src/embedding_data/acs_mapping_io.py`
- Create: `tests/acs_mapping_fixtures.py`
- Create: `tests/test_acs_mapping_contract.py`
- Create: `tests/test_acs_mapping_inputs.py`
- Create: `tests/test_acs_mapping_io.py`
- Read: `src/embedding_data/{classification_tables,naics_relationships,geography_tables,target_inputs,target_io,ipums_verification_run}.py`
- Read: `tests/{code_fixtures,geography_fixtures,test_ipums_verification_run,test_target_inputs,test_ipums_conversion}.py`

**Interfaces:**

- Produces immutable `SelectionRequest` with codes/geography/IPUMS run IDs,
  independently supplied output pins and Stage 7 reference receipt pin.
- `select_inputs(data_dir: Path, request: SelectionRequest) -> SelectedInputs`.
  `SelectedInputs.sources: dict[str, SourceInput]` contains exactly the three
  ACS profiles; `.codes` and `.geography` map all published table names to Paths;
  `.provenance` is JSON-serializable; `.verify() -> None` repeats the same checks.
  Its other frozen fields are `.data_dir:Path`, `.request:SelectionRequest` and
  `.software:dict`; no caller mutates selected provenance after validation.
- `SourceInput` fields: `profile:str`, `delivery_id:str`, `parquet:Path`,
  `parquet_record:dict`, `raw_citations:list[dict]`, `definition:dict`, `ddi:dict`.
- `freeze_software() -> dict` freezes explicit executing files, Python version/
  implementation, every installed distribution version and lock hash.
- `reserve_run(data_dir: Path, run_id: str) -> tuple[Path, Path]` returns
  `(final, owned_staging)` under `derived/acs/mapping`.
- `publish_directory(staging: Path, final: Path) -> None` atomically refuses
  replacement; only after caller revalidation. Reuse it for reference snapshot
  publication with explicitly supplied safe paths.
- Fixture `seed_selected_inputs(tmp_path: Path, monkeypatch) -> FixtureInputs`;
  `FixtureInputs` has `.data_dir`, `.request`, `.sources` and `.upstream_pins`.
  It uses synthetic manifested raw triples and actual fixture Stage 4/5/7 builds,
  never production data, mocked upstream verification or a fixture bypass.

- [ ] **Step 1: Write trust/schema/race regression tests.** Implement the new
  fixture using the existing `code_fixtures.seed_code_tree`,
  `geography_fixtures.seed_geography_tree`, `test_ipums_acceptance.delivery` and
  the genuine DDI/definition construction pattern in
  `tests/test_ipums_verification_run.py`. Keep all five Stage 7 profiles in its
  upstream verification; only then select the three ACS deliveries. Assign
  explicit fixture detached pins. Exercise these new public interfaces:

  ```python
  def test_wrong_upstream_pin_is_rejected(tmp_path, monkeypatch):
      from dataclasses import replace
      from acs_mapping_fixtures import seed_selected_inputs
      from embedding_data.acs_mapping_inputs import select_inputs

      fixture = seed_selected_inputs(tmp_path, monkeypatch)
      bad = replace(fixture.request, ipums_outputs_sha256='0' * 64)
      with pytest.raises(ValueError, match='detached'):
          select_inputs(fixture.data_dir, bad)

  def test_publication_does_not_replace_a_concurrent_empty_directory(tmp_path):
      from embedding_data.acs_mapping_io import publish_directory

      staging, final = tmp_path / 'run.part', tmp_path / 'run'
      staging.mkdir()
      (staging / 'report.json').write_text('{}\n')
      final.mkdir()
      with pytest.raises(FileExistsError):
          publish_directory(staging, final)
      assert final.is_dir() and list(final.iterdir()) == []
      assert (staging / 'report.json').read_text() == '{}\n'
  ```

  Add parameter cases for each selected hash/size/schema/count/raw citation,
  malformed/duplicate JSON keys, extra file/empty directory, wrong run/version,
  mixed reference frames, alternate run without a pin, unsafe ID, symlinked
  ancestor, occupied `.part`, concurrent input/software mutation and dependency
  drift. Check empty lists retain `List(String)` and paths `List(List(String))`;
  wrong nullability, duplicate lookup keys, unsorted candidates and missing
  candidate paths are rejected. A legitimate unrelated append to the manifest
  must not invalidate selected raw citations.

- [ ] **Step 2: Run the new focused tests and inspect the red failures.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_mapping_contract.py tests/test_acs_mapping_inputs.py tests/test_acs_mapping_io.py -q
  ```

  Expected before implementation: failures naming missing Stage 8 interfaces;
  existing upstream fixture checks pass.

- [ ] **Step 3: Implement exact contracts and input checks, then the exclusive
  publication primitive.** Materialize the frozen schema section above. Verify
  the Stage 7 detached pin using its public verifier first; copy its verified
  delivery metadata into `SourceInput`, retaining its substantive unresolved
  status. Independently verify the selected Stage 7 receipt pin. For Stage 4/5,
  follow the complete inventory checks demonstrated in `target_inputs._bundle`
  without invoking that private function or ITA selection. Verify all files in
  each upstream bundle, schemas, report counts, raw citations and source hashes;
  use only the needed tables after the complete inventory passes.

  Define frozen types and complete detached-file check as follows:

  ```python
  from dataclasses import dataclass
  from pathlib import Path
  import re

  from embedding_data import manifest

  @dataclass(frozen=True)
  class SelectionRequest:
      codes_run: str
      codes_outputs_sha256: str
      geography_run: str
      geography_outputs_sha256: str
      ipums_run: str
      ipums_outputs_sha256: str
      ipums_references_receipt_sha256: str

  def require_detached(file: Path, expected_sha256: str) -> None:
      if not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
          raise ValueError('invalid detached checksum')
      if manifest.sha256_file(file) != expected_sha256:
          raise ValueError('detached inventory checksum differs')
  ```

  `select_inputs` returns only after verifying all the fields above. Its
  `.verify()` calls the same public selector with the frozen request and compares
  the resulting provenance, file records and ordered schemas. Freeze every new
  Stage 8 module, its CLI and every reused executing helper explicitly; do not
  discover the inventory with an open-ended filesystem glob. Include relevant
  selected upstream software inventories and compare them without rewriting.

  Use same-filesystem no-replacement directory rename rather than a guarded
  `Path.rename`, which can replace a concurrently appearing empty directory.
  The supported project platforms are Darwin/arm64 and Linux/x86_64. The native
  core is:

  ```python
  import ctypes
  import errno
  import os
  import sys

  def publish_directory(staging: Path, final: Path) -> None:
      libc = ctypes.CDLL(None, use_errno=True)
      if sys.platform == 'darwin':
          rename, cwd, flag = libc.renameatx_np, -2, 4
      elif sys.platform == 'linux' and hasattr(libc, 'renameat2'):
          rename, cwd, flag = libc.renameat2, -100, 1
      else:
          raise OSError(errno.ENOSYS, 'exclusive directory publication unavailable')
      rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                         ctypes.c_char_p, ctypes.c_uint]
      rename.restype = ctypes.c_int
      result = rename(cwd, os.fsencode(staging), cwd, os.fsencode(final), flag)
      if result:
          error = ctypes.get_errno()
          raise OSError(error, os.strerror(error), str(final))
  ```

  Darwin constants/signature were checked against the installed SDK's
  `sys/fcntl.h` and `sys/stdio.h`. Linux uses `RENAME_NOREPLACE`. Refuse ENOSYS,
  EXDEV or unavailable native guarantees; do not fall back to replacement.
  `reserve_run` reuses safe path checks, exclusive `.mkdir()` and ownership
  tracking; recheck parents before calling the primitive. Catch failures at the
  caller and remove only the directory it successfully reserved.

- [ ] **Step 4: Run the focused tests and adjacent trust/parity tests.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_mapping_contract.py tests/test_acs_mapping_inputs.py tests/test_acs_mapping_io.py tests/test_target_inputs.py tests/test_ipums_verification_run.py tests/test_ipums_parity.py -q
  ```

  Expected: all pass, including actual local native no-replacement tests and
  both supported-platform dispatch/error tests. Check only intended new files
  changed and no upstream frozen file changed.

- [ ] **Step 5: Review and commit the deliverable.**

  ```bash
  git add src/embedding_data/acs_mapping_contract.py src/embedding_data/acs_mapping_inputs.py src/embedding_data/acs_mapping_io.py tests/acs_mapping_fixtures.py tests/test_acs_mapping_contract.py tests/test_acs_mapping_inputs.py tests/test_acs_mapping_io.py
  git commit -m "feat(acs): verify pinned mapping inputs and exclusive publication"
  ```

### Task 2: Complete public reference registry, imports and cache integrity

**Files:**

- Create: `src/embedding_data/acs_mapping_references.py`
- Create: `tests/test_acs_mapping_references.py`
- Create: `tests/fixtures/acs_mapping/reference-layouts.json`
- Modify: `tests/acs_mapping_fixtures.py`
- Read: `src/embedding_data/{ipums_references,geography_references,manifest}.py`

**Interfaces:**

- `Reference` immutable fields: `kind:str`, `filename:str`, `authority_url:str`,
  `edition:str`, `parser_contract:str`, `authority_role:str`, `sha256:str|None`.
- `ReferenceSnapshot` immutable fields: `reference_id:str`, `directory:Path`,
  `files:dict[str,Path]`, `receipt:dict`, `receipt_sha256:str`.
- `acquire_references(data_dir: Path, reference_id: str, *, client: httpx.Client | None = None) -> ReferenceSnapshot`.
- `import_reference(data_dir: Path, reference_id: str, kind: str, original: Path) -> dict`.
  Registered Geocorr imports also require their request/form/response original
  kinds; no CSV-only receipt may claim complete reproducibility.
- `check_references(data_dir: Path, reference_id: str, *, expected_receipt_sha256: str) -> ReferenceSnapshot`.
  This is offline and requires the external receipt pin.

- [ ] **Step 1: Write acquisition/import and cache failure tests.** Provide
  genuine-layout public excerpts with recorded authority, original hash, sheet/
  table locator and excerpt transformation in `reference-layouts.json`. Only
  synthetic microdata may appear in fixtures. Test every selected destination
  before the first HTTP request or import write. Use a counted MockTransport:

  ```python
  def test_cached_acquisition_never_constructs_an_http_client(snapshot, monkeypatch):
      from embedding_data import acs_mapping_references as refs

      def forbidden(*args, **kwargs):
          raise AssertionError('cached reference acquisition contacted HTTP')

      monkeypatch.setattr(refs, 'make_client', forbidden)
      again = refs.acquire_references(snapshot.data_dir, snapshot.reference_id)
      assert again.receipt_sha256 == snapshot.receipt_sha256
  ```

  Define fixture `snapshot` as a test wrapper with `data_dir:Path`,
  `reference_id:str` and `receipt_sha256:str`, using a fully registered fixture
  import set and explicit computed fixture pins; never bypass receipt checking.
  Test changed cached bytes, missing recorded files, unrecorded destination,
  unexpected originals, conflicting import, symlink/partial names, malformed
  workbook/HTML and HTTP-200 application errors. Import time is a flagged proxy.
  Test request-byte preservation, generated link padding, receipt pin tampering
  and manifest delta accounting. Partial snapshots cannot be used by build.

- [ ] **Step 2: Run the focused red tests.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_mapping_references.py -q
  ```

  Expected: missing new lifecycle interfaces or explicit cache/integrity failures.

- [ ] **Step 3: Implement the closed registry and transactional boundary.**
  Register the exact classification originals/authority roles in the classification
  evidence section, all geographic originals above, geographic role/state pages,
  2024 annual/five-year delivered-scheme documentation, Geocorr help/form and the
  full population queries. Cite verified Stage 4/7 originals in place by manifest
  citation and pinned receipt/bundle, without duplicating their registry.

  A receipt records `reference_id`, `reference_version`, `originals` keyed by
  registered kind (URL, edition, authority role, parser contract, hash, size,
  retrieval/import proxy), `request_files`, `raw_citations` and a full file
  inventory excluding the receipt itself. Manifest the generated receipt
  separately. Its detached checksum is returned and copied to independent
  measurement controls/finding; never infer trust from a receipt's own fields.

  The complete cached path must precede transport creation:

  ```python
  def acquire_references(data_dir, reference_id, *, client=None):
      directory = reference_directory(data_dir, reference_id)
      if directory.exists():
          return check_cached_snapshot(data_dir, reference_id)
      preflight_destinations(data_dir, reference_id)
      if client is not None:
          return acquire_missing(data_dir, reference_id, client)
      with make_client() as owned_client:
          return acquire_missing(data_dir, reference_id, owned_client)
  ```

  Define `reference_directory(data_dir: Path, reference_id: str) -> Path`,
  `check_cached_snapshot(data_dir: Path, reference_id: str) -> ReferenceSnapshot`,
  `preflight_destinations(data_dir: Path, reference_id: str) -> None`,
  `make_client() -> httpx.Client` and
  `acquire_missing(data_dir: Path, reference_id: str, client: httpx.Client) -> ReferenceSnapshot`
  in this module.
  The cached checker verifies the immutable receipt's manifest entry, complete
  registry, original/request bytes and their citations; a supplied build pin
  is additionally checked by `check_references`.

  Preflight checks the full destination and recorded-path set, including
  absent-but-recorded files. Downloads stream into exclusively owned partials;
  validate transport completion, content type/application success and actual
  original layouts before no-replacement publication and manifest recording.
  A failed acquisition retains already manifested evidence and refuses
  silent overwrite/recovery; inspect it and choose a fresh reference ID.
  An intentionally incomplete explicit import set may receive further missing
  registered kinds after full-set preflight; occupied per-file partials or a
  conflicting/complete snapshot still refuse writes. No incomplete set is usable
  by build or cached acquisition. A
  manifest-append failure must be reported as unrecorded evidence, never a
  usable snapshot. Only a complete manifested receipt enables build. Mapping
  bundle failures still leave no final bundle. Do not delete evidence owned by
  a prior invocation to make a rerun succeed.

  Geocorr requests have a fixed scoped state list and explicit exact query bytes.
  Preserve every request, response page and returned original CSV. Do not retry
  an application-error response as empty data. If direct public GET is blocked,
  import exact browser bytes with identity/proxy metadata; no credential request.

- [ ] **Step 4: Run lifecycle and existing manifest/audit tests.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_mapping_references.py tests/test_manifest.py tests/test_manifest_audit.py -q
  ```

  Expected: all pass, zero real HTTP calls, exact manifest prefix preservation
  and cached transport count zero. Record the reference kind/file list in the
  test fixture metadata; all runtime inputs live inside the selected data root.

- [ ] **Step 5: Review and commit the deliverable.**

  ```bash
  git add src/embedding_data/acs_mapping_references.py tests/test_acs_mapping_references.py tests/acs_mapping_fixtures.py tests/fixtures/acs_mapping
  git commit -m "feat(acs): freeze public mapping reference snapshots"
  ```

### Task 3: Strict classification evidence and supported native membership

**Files:**

- Create: `src/embedding_data/acs_code_references.py`
- Create: `tests/test_acs_code_references.py`
- Create: `tests/fixtures/acs_mapping/classification/`
- Modify: `tests/acs_mapping_fixtures.py`
- Read: selected canonical/native nodes, original Census/IPUMS workbooks/pages,
  `src/embedding_data/{classification_tables,naics_relationships}.py`

**Interfaces:**

- `read_code_evidence(snapshot: ReferenceSnapshot, selected: SelectedInputs) -> CodeEvidence`.
- `CodeEvidence.membership: pl.DataFrame` has ordered fields
  `system:String, source_scheme:String, paired_census_code:String,
  source_token:String, native_finest_code:String, native_node_id:String,
  aggregation_type:String, aggregation_markers:List(String), flag_partial:Boolean,
  flag_exception:Boolean, reference_ids:List(String), reference_locators:List(String)`.
  Its grain is one supported finest member per source key. `native_node_id` may
  be null for a non-node aggregate. Preserve a complete per-key metadata table
  for reasons and `559830`, which has no membership row.
  Define `CodeEvidence` in `acs_code_references.py` as a frozen dataclass with
  `.membership:pl.DataFrame`, `.metadata:pl.DataFrame` and `.diagnostics:dict`.
  Metadata has one row per source key, the mapping/aggregation/reason/special
  fields of `CODE_SCHEMA`, and nonnull reference ID/locator lists; only fields
  that claim a canonical mapping are deferred to Task 4.
- `parse_membership_expression(expression: str, nodes: pl.DataFrame, paths: pl.DataFrame) -> list[str]`.
- `validate_paired_keys(observed: pl.DataFrame, evidence: CodeEvidence) -> None`.
  Every nonmissing observed `(scheme, IND/OCC, token)` must match explicit
  authoritative paired evidence; references alone do not excuse source mismatch.

- [ ] **Step 1: Write genuine-layout membership and contradiction tests.**
  Extract bounded actual rows and layout from every selected original; preserve
  their table/sheet/header structures and evidence locators. Include numeric
  coarse categories, every M/P/S/Z marker and actual combinations/discriminating
  suffixes; OCC X/Y and their PUMS collapses; source padding; malformed syntax;
  positive and excluded constituents; unknown/documented aggregation reasons;
  the exact military special. Use official parentage, including SOC overflow.

  ```python
  def test_paired_industry_disagreement_is_not_merged(code_originals, selected):
      from embedding_data.acs_code_references import read_code_evidence

      with pytest.raises(ValueError, match='contradictory paired'):
          read_code_evidence(code_originals.with_conflicting_authority(), selected)

  def test_remainder_keeps_only_documented_constituents(code_originals, selected):
      from embedding_data.acs_code_references import read_code_evidence

      evidence = read_code_evidence(code_originals.snapshot, selected)
      members = evidence.membership.filter(pl.col('source_scheme').eq('naics2022')
          .and_(pl.col('paired_census_code').eq('3875'))
          .and_(pl.col('source_token').eq('3219ZM')))
      assert sorted(members['native_finest_code']) == [
          '321911', '321912', '321918', '321920', '321999']
      assert not {'321991', '321992'} & set(members['native_finest_code'])
  ```

  `code_originals` is a fixture wrapper exposing a snapshot and
  `.with_conflicting_authority()`, which rewrites a **synthetic fixture** relation
  into two active contradictory authoritative rows and recalculates only fixture
  raw/receipt pins. `.snapshot` is the otherwise complete genuine-layout fixture
  snapshot, using selected official finest nodes for the literal candidates
  above. Keep expected memberships literal; never generate them by calling the
  production parser.

- [ ] **Step 2: Run the reference parser tests red.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_code_references.py -q
  ```

  Expected: new parser/relationship validation fails; the expected memberships
  are fixed from primary sources before implementation.

- [ ] **Step 3: Implement source-specific relations and bounded expression grammar.**
  Validate exact sheet/header editions and row keys. Parse the official Census
  NAICS/SOC membership expressions, numeric nodes and source-token correspondences
  separately. Resolve published whole nodes through actual selected descendant
  paths; resolve explicit unions/ranges/exclusions against the official finest
  set. A range is a bounded official code interval, not a numeric enumeration of
  nonexistent codes. Carry `part` clauses as partial support and never pretend
  the whole finest category is fully observed. The core set operation is:

  ```python
  def resolve_union_and_exclusion(included: list[set[str]],
                                  excluded: list[set[str]]) -> list[str]:
      positive = set().union(*included)
      negative = set().union(*excluded)
      if not positive or not negative.issubset(positive):
          raise ValueError('unsupported aggregation expression')
      result = sorted(positive - negative)
      if not result:
          raise ValueError('empty classification membership')
      return result
  ```

  In `parse_membership_expression`, tokenize only attested separators, whole-code
  references, explicit coarse references, ranges, `part` and exclusion clauses
  from the inspected editions. Reject leftover text, unknown endpoints and an
  unsupported grammar. Keep original expression text and exact row/column
  locators. Neither title matching nor generic X/Y/letter wildcard expansion is
  an admissible membership source. Resolve PUMS-specific occupation collapses
  using their explicit full-Census correspondence before SOC expansion. Full
  Census occupation rows alone do not define the PUMS list.

  Explicitly test the published `31,32,33` union against the official combined
  sector `31-33`; do not require nonexistent separate sector nodes or infer a
  generic first-two-digit parent rule. Resolve `33MS` through its explicitly
  named 331/332 scopes, not that combined manufacturing sector.

  Proposed authority roles and the known conflicting rows are stated in the
  classification evidence section for plan review. Implement exactly that bounded
  disposition only after plan approval. Otherwise raise `contradictory paired`
  before mapping. Store rejected diagnostic reference assertions separately in
  the report, never blend them into an authoritative relation. Any contradiction
  between active authorities, missing member, other undocumented special or
  observed official-pair mismatch remains a publication failure.

  Per-code documented reasons require a specific published locator. Where none
  is published, record `unknown`, an empty reason list and the exact references
  inspected. Generic explanation that X codes can have either reason does not
  determine a particular X code. Synthetic rule-unit tests may exercise both
  documented reason branches but must be labelled synthetic evidence; do not
  manufacture a source-backed per-code disclosure reason.

- [ ] **Step 4: Run membership, official-parentage and relation tests.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_code_references.py tests/test_classification_tables.py tests/test_naics_relationships.py -q
  ```

  Expected: genuine-layout memberships exactly match primary evidence; all
  malformed/contradictory/unsupported cases fail. No source value was rewritten.

- [ ] **Step 5: Review and commit the deliverable.**

  ```bash
  git add src/embedding_data/acs_code_references.py tests/test_acs_code_references.py tests/acs_mapping_fixtures.py tests/fixtures/acs_mapping/classification
  git commit -m "feat(acs): parse source-backed classification membership"
  ```

### Task 4: Scheme-aware classification lookups and independent provenance

**Files:**

- Create: `src/embedding_data/acs_code_mapping.py`
- Create: `tests/test_acs_code_mapping.py`
- Modify: `tests/acs_mapping_fixtures.py`
- Read: `src/embedding_data/{classification_tables,naics_relationships,acs_code_references,acs_mapping_contract}.py`

**Interfaces:**

- `scheme_for(profile: str, sample_id: str, release_year: int, component_year: int) -> dict[str, str | int | bool]` returns delivered/interview schemes and independent source recoding flags.
  Its keys are `industry_delivered_scheme`, `industry_interview_scheme`,
  `occupation_delivered_scheme`, `native_industry_vintage`,
  `native_occupation_vintage` and `flag_source_industry_recoded`. Scheme strings
  are `naics2017`, `naics2022` and `soc2018`, matching lookup `source_scheme`.
- `observed_code_keys(sources: dict[str, SourceInput]) -> pl.DataFrame` collects
  only distinct small classification keys/counts from lazy scans, retaining
  profile/sample/component partitions for reporting.
- `build_code_lookup(observed: pl.DataFrame, evidence: CodeEvidence, selected: SelectedInputs) -> pl.DataFrame` returns `CODE_SCHEMA`.
- `validate_code_lookup(frame: pl.DataFrame, evidence: CodeEvidence, selected: SelectedInputs) -> None` reconstructs asserted candidates/paths/scalars/reasons.

- [ ] **Step 1: Write vintage/scalar/special regression tests.**

  ```python
  def test_same_code_content_change_traverses_the_full_relation(split_case):
      result = split_case.build_lookup()
      row = result.row(0, named=True)
      assert row['canonical_finest_candidates'] == ['111112', '111113']
      assert row['flag_vintage_crosswalk'] is True
      assert row['canonical_scalar_node_id'] is None

  def test_documented_special_has_no_classification_claim(military_case):
      row = military_case.build_lookup().row(0, named=True)
      assert row['source_token'] == '559830'
      assert row['mapping_status'] == 'documented_special'
      assert row['native_finest_candidates'] == []
      assert row['canonical_finest_candidates'] == []
      assert row['canonical_candidate_paths'] == []
      assert row['native_node_id'] is None
      assert row['canonical_scalar_node_id'] is None
      assert row['canonical_common_node_id'] is None
      assert row['special_reason'] and row['reference_locators']
  ```

  `split_case` uses the already defined `code_fixtures.toy_reference_tables()`
  2017 `111112` split; it is clearly synthetic arithmetic truth.
  `military_case` uses the genuine PUMS-guide special evidence and paired OCC
  metadata. Both are `FixtureCodeCase` instances defined in
  `tests/acs_mapping_fixtures.py`, with `.observed:pl.DataFrame`,
  `.evidence:CodeEvidence`, `.selected:SelectedInputs` and
  `.build_lookup() -> pl.DataFrame` calling the real `build_code_lookup` with
  those three fields. Add annual 2022→2017, annual 2023/2024→2022, five-year pre-2023
  component→delivered-2022 with source recoding, and all SOC→2018 cases.
  Test singleton crosswalk, exact finest source versus partial/aggregate singleton,
  roots with no common ancestor, padded tokens, malformed internal characters,
  preserved suffixes, absent flags and every other purported special failing.

- [ ] **Step 2: Run the lookup tests red.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_code_mapping.py -q
  ```

  Expected: missing scheme/lookup behavior, with native membership fixtures valid.

- [ ] **Step 3: Implement deterministic mapping without row-level expansion.**
  Remove only documented outer ASCII space padding from a separate token;
  `raw` remains the exact original source column. Normalize paired Census codes
  at the documented width into separate strings. Fail over-width, sign, decimal,
  internal whitespace or unsupported characters. Select schemes solely from
  verified sample/product metadata. For every native-2017 finest possibility,
  compute the full canonical union:

  ```python
  from embedding_data.naics_relationships import candidates

  def canonical_naics_candidates(relations: pl.DataFrame,
                                  native_vintage: int,
                                  native_codes: list[str]) -> list[str]:
      result = set()
      for code in native_codes:
          result.update(candidates(relations, native_vintage, code, 2022))
      if not result:
          raise ValueError('uncovered canonical classification relation')
      return sorted(result)

  def common_path_node(paths: list[list[str]]) -> str | None:
      common = []
      for level in zip(*paths):
          if len(set(level)) != 1:
              break
          common.append(level[0])
      return common[-1] if common else None
  ```

  Native membership must already have passed Task 3, and complete relationship
  endpoints must already have passed Task 1. For SOC, use selected workbook-derived
  paths. Retain an explicitly published numeric native node at its declared
  depth; for a non-node aggregate compute its supported common native ancestor
  from native paths without dropping constituent/exclusion/partial provenance.
  The special path bypasses classification expansion **only** for exact
  `559830` with its expected scheme/paired evidence and reason; produce the
  required null fields and typed empty lists. Never pass it to common ancestry.

  An exact finest source category can assert a scalar only if its native category
  is fully observed and the canonical interpretation is supported one-to-one in
  both directions. A numeric coarse code or M/P/S/Z/X/Y aggregate remains an
  aggregate even if its resulting candidate list has length one. Keep source
  category/markers, partial/exception flags, canonical paths and reference
  ambiguity independently. Source-vintage recoding lives in companion metadata,
  not in the deduplicated code key. Set counts by profile/component so one shared
  lookup cannot erase source-specific provenance.

- [ ] **Step 4: Run reference and mapping tests together.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_code_references.py tests/test_acs_code_mapping.py tests/test_naics_relationships.py -q
  ```

  Expected: supported complete candidates, zero guessed scalar assignments,
  explicit special/unknown-reason partitions and all refusals pass.

- [ ] **Step 5: Review and commit the deliverable.**

  ```bash
  git add src/embedding_data/acs_code_mapping.py tests/test_acs_code_mapping.py tests/acs_mapping_fixtures.py
  git commit -m "feat(acs): map native classifications with complete flagged candidates"
  ```

### Task 5: Population references, county factors, V8 and MSA residuals

**Files:**

- Create: `src/embedding_data/acs_area_references.py`
- Create: `src/embedding_data/acs_geography_factors.py`
- Create: `tests/test_acs_area_references.py`
- Create: `tests/test_acs_geography_factors.py`
- Create: `tests/fixtures/acs_mapping/geography/`
- Modify: `tests/acs_mapping_fixtures.py`
- Read: selected Stage 5 county/CBSA tables and its pinned full county original;
  the exact composition/Geocorr/MSA originals identified above.

**Interfaces:**

- `read_area_evidence(snapshot: ReferenceSnapshot, selected: SelectedInputs) -> AreaEvidence`.
  `AreaEvidence` is an immutable dataclass defined in `acs_area_references.py`
  with `.intersections`, `.puma_totals`, `.county_totals`, `.puma_groups`,
  `.county_groups`, `.msa_intersections` (all small typed `pl.DataFrame`s),
  `.reference_provenance:dict` and `.scope_states:tuple[str,...]`.
- `read_full_county_original(selected: SelectedInputs) -> pl.DataFrame` in the
  same module reads the exact raw county original cited by the selected Stage 5
  inputs, after integrity checks. Use its excluded PR rows to validate complete
  public references before filtering; do not invent PR hierarchy nodes.
- Internal intersection fields are `state_fips:String, puma_code:String,
  county_geoid:String, intersection_population:Int64,
  published_area_factor:Float64, published_county_factor:Float64,
  reference_ids:List(String), reference_locators:List(String)`.
  PUMA/county controls have their complete natural key and `population:Int64`.
  Composition frames retain residence-state/PUMA or residence-state/county,
  native three-digit group-state code, normalized group-state FIPS and group
  code, with source locators. MSA fields match the population/percentage fields
  of `MSA_FACTOR_SCHEMA` before adding canonical node IDs and frame annotations.
- `build_factor_tables(evidence: AreaEvidence, selected: SelectedInputs) -> FactorTables`.
  `FactorTables` is an immutable dataclass in `acs_geography_factors.py` with
  `.county`, `.msa`, `.coverage:pl.DataFrame` and `.diagnostics:dict`.
- `validate_factor_tables(factors: FactorTables, evidence: AreaEvidence, selected: SelectedInputs) -> None`.
  Reconstruct numerators/denominators from original reference frames; Float64
  sums alone are insufficient.

- [ ] **Step 1: Write genuine-layout and hand-calculated regression tests.**
  Create fixture `population_case` in `tests/acs_mapping_fixtures.py`, returning
  `.evidence` and `.selected`. It contains this explicit synthetic population
  truth, in the genuine original layouts:

  | Residence PUMA | Population intersections | Whole population | POW/MIG group |
  | --- | --- | ---: | --- |
  | state 01 / 00100 | 01001:60, 01003:40 | 100 | state 001 / 00100 |
  | state 01 / 00200 | 01003:300 | 300 | state 001 / 00100 |
  | state 09 / 20100 | 09110:200 | 200 | state 009 / 20100 |

  Independent controls: county 01001=60, 01003=340, 09110=200.
  Synthetic MSA 10000 contains county 01001 and CT 09110 (population 260);
  01003 belongs to a typed micropolitan CBSA 20000, so PUMA 00200 is wholly
  non-MSA. The selected fixture Stage 5 bundle contains these exact county/CBSA
  nodes and roles, not production IDs with mocked validation.

  ```python
  def test_work_group_uses_populations_not_mean_puma_shares(population_case):
      from embedding_data.acs_geography_factors import build_factor_tables

      factors = build_factor_tables(population_case.evidence, population_case.selected)
      group = factors.county.filter(
          pl.col('area_type').eq('work_migration')
          .and_(pl.col('state_fips').eq('01'))
          .and_(pl.col('area_code').eq('00100'))).sort('county_geoid')
      assert group['intersection_population'].to_list() == [60, 340]
      assert group['area_population'].to_list() == [400, 400]
      assert group['factor'].to_list() == pytest.approx([0.15, 0.85], abs=1e-12)

  def test_wholly_non_msa_puma_keeps_its_full_residual(population_case):
      from embedding_data.acs_geography_factors import build_factor_tables

      factors = build_factor_tables(population_case.evidence, population_case.selected)
      row = factors.coverage.filter(pl.col('state_fips').eq('01').and_(
          pl.col('puma_code').eq('00200'))).row(0, named=True)
      assert (row['puma_population'], row['msa_population'],
              row['non_msa_population']) == (300, 0, 300)
      assert row['non_msa_fraction'] == 1.0
  ```

  Check residence factors 0.6/0.4; PUMA 00100 MSA fraction 0.6, reverse 60/260,
  residual 40; CT MSA fraction 1, reverse 200/260. Include all nine CT planning
  regions in a public original-layout inventory fixture, not just this arithmetic
  case. Add foreign/PR validation before scope filtering; native state code
  representations; integer/negative/null/duplicate populations; zero denominators;
  retained zero intersections; each published-factor rounding boundary; 0–100
  percentages; unexpected headers/sheets and legacy CT counties.

  Delete the 40-person intersection while retaining its 100-person independent
  PUMA control: build must fail. Delete a whole PUMA or county control: fail.
  Put one county in two groups, or make a PUMA-derived group disagree with
  county composition: reject union-only derivation and preserve the diagnostic.

- [ ] **Step 2: Run the area reference and factor tests red.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_area_references.py tests/test_acs_geography_factors.py -q
  ```

  Expected: missing new parsers/factor behavior, with fixed literal arithmetic
  expectations. An incorrect 0.30/0.70 mean-of-PUMA-fractions result must fail.

- [ ] **Step 3: Implement strict originals and integer-first factors.**
  Read each workbook with fastexcel, preserve strings, validate exact registered
  sheet/header identity and unique source/target pairs. Read Geocorr with stdlib
  CSV, validating both names and descriptive-label rows before strict casts.
  Normalize domestic states through documented correspondence, not arbitrary
  last-two-digit truncation. Validate all complete PUMA/county keys and populations
  against controls/compositions before scope filtering.

  For residence, require intersection sums by PUMA and county to equal their
  independent control populations exactly. Join those controls, then calculate
  `factor=intersection_population/area_population` as Float64 with no stored
  rounding. Check original `afact` and `afact2` against the two conditioning
  denominators within their published precision bound. Keep explicit zero rows.

  The shared work/migration calculation uses these exact relations:

  ```python
  def work_group_populations(intersections: pl.DataFrame,
                            puma_groups: pl.DataFrame,
                            puma_totals: pl.DataFrame) -> pl.DataFrame:
      puma_key = ['state_fips', 'puma_code']
      group_key = ['group_state_fips', 'group_code']
      numerators = (intersections.join(puma_groups, on=puma_key, validate='m:1')
          .group_by(*group_key, 'county_geoid')
          .agg(pl.col('intersection_population').sum()))
      denominators = (puma_groups.join(puma_totals, on=puma_key, validate='1:1')
          .group_by(group_key).agg(pl.col('population').sum().alias('area_population')))
      return (numerators.join(denominators, on=group_key, validate='m:1')
          .with_columns(pl.col('intersection_population').cast(pl.Float64)
              .truediv(pl.col('area_population')).alias('factor')))
  ```

  Run full V8 checks **before** invoking that core: every resident PUMA belongs
  to exactly one group; county composition is unique in the county→group
  direction; PUMA-derived county/group memberships agree with the independent
  county composition; county sums and group totals reconcile exactly. Include
  zero rows in relationship diagnostics. If a county is split, preserve source
  rows/locators in aggregate diagnostic evidence and refuse union-only derivation
  for that unit. Obtain an official population-intersection original and extend
  the reviewed reference contract before completing that case; no majority
  selection or equal weights. V8 stays unadopted while any case is unresolved.

  For MSA, validate unique intersections, consistent whole populations and exact
  MSA intersection closure over the complete original before filtering PR.
  Compare every PUMA total with the Geocorr PUMA control. Require scoped MSA
  codes to be typed **metropolitan** nodes in the selected Stage 5 inventory.
  Calculate both directional fractions from integers. Start coverage with every
  scoped PUMA control, left-join MSA sums, and use zero only when a complete,
  validated MSA reference confirms absence. `non_msa_population=N(p)-sum(n)`
  must be nonnegative; never rescale. Record metro/micro distinctions and no
  joint-probability or individual-location claim.

- [ ] **Step 4: Run the geographic and selected upstream geography tests.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_area_references.py tests/test_acs_geography_factors.py tests/test_geography_tables.py tests/test_geography_parsers.py -q
  ```

  Expected: exact integer agreement, all required factor sums within `1e-12`,
  explicit MSA residuals, retained zero relationships and split-county refusals.
  Validate every published reference table against its frozen schema and sort key.

- [ ] **Step 5: Review and commit the deliverable.**

  ```bash
  git add src/embedding_data/acs_area_references.py src/embedding_data/acs_geography_factors.py tests/test_acs_area_references.py tests/test_acs_geography_factors.py tests/acs_mapping_fixtures.py tests/fixtures/acs_mapping/geography
  git commit -m "feat(acs): derive conserved PUMA county and MSA population factors"
  ```

### Task 6: Three role lookups with documented scope and source provenance

**Files:**

- Create: `src/embedding_data/acs_area_mapping.py`
- Create: `tests/test_acs_area_mapping.py`
- Modify: `src/embedding_data/acs_area_references.py`
- Modify: `tests/acs_mapping_fixtures.py`
- Read: pinned role/state documentation, source DDI and Stage 7 flag evidence.

**Interfaces:**

- `read_role_rules(snapshot: ReferenceSnapshot) -> pl.DataFrame` in
  `acs_area_references.py`: one explicit rule per registered role/state/area
  special or domestic state correspondence, with reference IDs/locators and
  applicability/frame conditions. Conflicting rules fail.
- `observed_area_keys(sources: dict[str, SourceInput]) -> pl.DataFrame` collects
  only distinct profile/sample/release/component/role/raw-state/raw-area keys
  and source counts, using each role's own documented normalization.
- `build_area_lookup(observed: pl.DataFrame, rules: pl.DataFrame, evidence: AreaEvidence, factors: FactorTables) -> pl.DataFrame` returns `AREA_SCHEMA`.
- `validate_area_lookup(lookup: pl.DataFrame, observed: pl.DataFrame, factors: FactorTables) -> None` checks one interpretation per key, cited statuses and complete factors for applicable keys.

- [ ] **Step 1: Write role/state/status tests with exact expected outcomes.**

  ```python
  @pytest.mark.parametrize(('role', 'state', 'area', 'status'), [
      ('workplace', '00', '00000', 'niu_or_unidentifiable'),
      ('workplace', '80', '00001', 'foreign'),
      ('migration', '000', '00000', 'niu_or_unidentifiable'),
      ('migration', '150', '00001', 'foreign'),
      ('migration', '110', '00002', 'territory'),
  ])
  def test_documented_role_specials_have_no_domestic_factors(
          role_case, role, state, area, status):
      observed = role_case.observed(role=role, state=state, area=area)
      lookup = build_area_lookup(observed, role_case.rules,
                                 role_case.evidence, role_case.factors)
      row = lookup.row(0, named=True)
      assert row['area_status'] == status
      assert row['factor_key'] is None
      assert row['reference_ids'] and row['reference_locators']
  ```

  Fixture `role_case` uses `population_case`, public role/state rule excerpts and
  synthetic keys. Its `.observed(role, state, area)` returns a one-row frame with
  the complete observed-area schema, for `acs/core` / `us2024a` / 2024.
  The state/place values above have the documented labels in the selected
  delivered DDI, independently of the area special-code meanings. Unknown
  state/place values fail rather than becoming a synthetic foreign category.

  Add valid residence `(01,00100)`, workplace `(01,00100)` and migration `(001,00100)`;
  same area number in a different state; invalid state/area pairing; incompatible
  county; unexplained null; unavailable metadata only where documented; unknown
  special; and five-year components 2020/2021 versus 2022–2024. Two roles sharing
  a factor table must retain distinct lookup IDs, source columns and citations.

- [ ] **Step 2: Run the role lookup tests red.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_area_mapping.py -q
  ```

  Expected: missing role normalization/status/provenance behavior.

- [ ] **Step 3: Implement observed-key interpretation and factor coverage.**
  Parse only the six role source columns into separate normalized representations;
  retain their original values/types in companions. Documented width validation
  precedes padding. Classify specials through role/state rules, then applicable
  domestic keys through the complete compositions and factor inventory. A missing
  compatible key is a build error, not `documented_unavailable`.

  The factor coverage gate is:

  ```python
  def require_factor_coverage(applicable: pl.DataFrame,
                              county_factors: pl.DataFrame) -> None:
      totals = county_factors.group_by('factor_key').agg(
          pl.col('factor').sum().alias('factor_sum'))
      joined = applicable.select('factor_key').unique().join(
          totals, on='factor_key', how='left', validate='1:1')
      if joined.filter(pl.col('factor_sum').is_null().or_(
              pl.col('factor_sum').sub(1.0).abs().gt(1e-12))).height:
          raise ValueError('applicable area has missing or incomplete county factors')
  ```

  `validate_area_lookup` additionally checks exact integer controls, so a factor
  sum alone cannot excuse missing intersections. Assign factor keys by normalized
  area type/state/code/vintage; never join the three roles into a person-level
  factor cross-product. All valid factor uses retain allocation provenance even
  when their single factor is one. Nonapplicable roles have no factor-use claim.
  Distinguish actual fractional splits with positive-support counts.

  Use documented 2020 definitions for all selected products. Flag source-assigned
  2020 geography for pre-2022 five-year components where a defined area applies;
  its documented frame reassignment is separate from person-level Q evidence.
  Missing source-allocation evidence stays unavailable. Keep PWPUMA00 `00000`
  NIU/unidentifiable and migration `00000` under-one/same-house meanings distinct
  in reasons; neither becomes no migration or zero flows. Preserve TRANWORK and
  work-from-home records for Stage 9's eligibility decision.

- [ ] **Step 4: Run role/reference/factor tests together.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_area_mapping.py tests/test_acs_area_references.py tests/test_acs_geography_factors.py -q
  ```

  Expected: every observed key has exactly one status, all applicable keys have
  complete factors, source-assigned geography remains flagged and unknown keys
  are rejected. Disjoint role status counts sum to each profile's row total.

- [ ] **Step 5: Review and commit the deliverable.**

  ```bash
  git add src/embedding_data/acs_area_mapping.py src/embedding_data/acs_area_references.py tests/test_acs_area_mapping.py tests/acs_mapping_fixtures.py
  git commit -m "feat(acs): interpret geographic roles with explicit scope and provenance"
  ```

### Task 7: Ordered companions, source flags and reconciled partitions

**Files:**

- Create: `src/embedding_data/acs_mapping_companions.py`
- Create: `tests/test_acs_mapping_companions.py`
- Modify: `tests/acs_mapping_fixtures.py`
- Read: `src/embedding_data/ipums_parity.py`, the verified source schemas/DDI,
  frozen annotation schemas and the Task 4/6 lookup APIs.

**Interfaces:**

- `annotate_source(source: SourceInput, code_lookup: pl.DataFrame, area_lookup: pl.DataFrame, factors: FactorTables) -> pl.LazyFrame`.
- `write_companion(frame: pl.LazyFrame, source: SourceInput, destination: Path) -> dict` writes only into caller-owned staging, rereads and returns `target_io.file_record`.
- `validate_companion(source: SourceInput, companion: Path, code_lookup: pl.DataFrame, area_lookup: pl.DataFrame, factors: FactorTables) -> dict` includes full ordered original-prefix parity, identity and mapping/role validation.
- `companion_diagnostics(source: SourceInput, companion: Path) -> dict` returns
  JSON-safe aggregate counts, disjoint primary-status partitions and independent
  overlapping provenance-flag counts. No person values or IDs enter reports.

- [ ] **Step 1: Write fidelity/flag and join-failure regression tests.**
  Fixture `companion_case` contains all three profiles built through the actual
  converter, one exact duplicate source row, padded INDNAICS, a partial singleton,
  an OCCSOC special, five-year MULTYEAR components, unavailable flags and all role
  outcomes. It exposes `.source`, `.codes`, `.areas`, `.factors` for one profile
  and `.profiles` for the complete case.

  ```python
  def test_annotations_preserve_order_types_duplicates_and_missing_flags(
          companion_case, tmp_path):
      from embedding_data.acs_mapping_companions import annotate_source, write_companion
      from embedding_data.ipums_parity import compare_ordered

      case = companion_case
      output = tmp_path / 'companion.parquet'
      frame = annotate_source(case.source, case.codes, case.areas, case.factors)
      write_companion(frame, case.source, output)
      original = pl.scan_parquet(case.source.parquet)
      original_names = original.collect_schema().names()
      assert compare_ordered(original, pl.scan_parquet(output).select(original_names))[
          'values_equal'] is True
      result = pl.read_parquet(output)
      assert result['source_row'].dtype == pl.UInt64
      assert result['source_row'].to_list() == list(range(result.height))
      assert result['source_parquet_sha256'].unique().to_list() == [
          case.source.parquet_record['sha256']]
  ```

  Add an independent exact original-prefix schema assertion, duplicate/order
  mutations, reserved-name collision, duplicate lookup key, missing classification
  lookup, unmatched applicable role, source source-row reordering and tampered
  annotations. Check source QIND/QOCC/QMIGRAT1 values and types exactly. For core
  2023 all-null QMIGRAT1, derived migration allocation is unavailable/null;
  vintage has no newly fabricated QMIGRAT1 column; five-year Int64 flags remain
  Int64. Geography factor one and code singleton do not clear provenance.

- [ ] **Step 2: Run the companion tests red.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_mapping_companions.py -q
  ```

  Expected: missing annotation/fidelity behavior, not a change to source types.

- [ ] **Step 3: Implement lazy many-to-one annotation and bounded fidelity.**
  Reject collisions with every final suffix and temporary join-key name before
  scanning. Add zero-based ordinal identity before any join. Original columns
  are never cast, trimmed, replaced or renamed. Scheme/paired-code/token keys
  are temporary separate expressions; join only small unique lookups with
  `validate='m:1'`, `maintain_order='left'` and checked null-key semantics.
  Do not explode candidates or join county-factor rows onto person rows.

  Use this row identity/prefix-preserving core:

  ```python
  def indexed_source(source: SourceInput) -> pl.LazyFrame:
      frame = pl.scan_parquet(source.parquet)
      reserved = set(ANNOTATION_SCHEMA)
      if reserved.intersection(frame.collect_schema().names()):
          raise ValueError('source columns collide with ACS annotations')
      return (frame.with_row_index('source_row')
          .with_columns(pl.col('source_row').cast(pl.UInt64),
              pl.lit(source.parquet_record['sha256']).alias('source_parquet_sha256')))

  def require_original_prefix(source: SourceInput, companion: Path) -> dict:
      from embedding_data.ipums_parity import compare_ordered

      expected = pl.scan_parquet(source.parquet)
      names = expected.collect_schema().names()
      actual = pl.scan_parquet(companion)
      if actual.collect_schema().names()[:len(names)] != names:
          raise ValueError('original ordered schema prefix changed')
      result = compare_ordered(expected, actual.select(names))
      if not result['schema_equal'] or not result['values_equal']:
          raise ValueError('original source values, types, order or multiplicity changed')
      return result
  ```

  `annotate_source` computes release/component/sample metadata from the verified
  source metadata and scheme registry, joins industry and occupation separately,
  then the three role lookups separately. Project exactly `original_names +
  list(ANNOTATION_SCHEMA)`; remove every temporary join key. For documented missing
  classifications only, produce `missing` status with typed empty lists and null
  mapping nodes. Other unmatched keys fail. Derive per-role factor-use/split flags
  from the unique factor-key summary, without multiplying source rows.

  Decode each source Q field using that delivery's DDI and the recorded field/
  applicability contract. Do not apply a generic nonzero test. Preserve
  `not_allocated_or_niu` where applicable nonallocation cannot be established;
  absence/null is unavailable. Keep source classification allocation, source
  vintage recoding, Stage 8 concordance, source geography recoding and Stage 8
  geographic allocation independent. No family inclusion/exclusion is decided.

  `write_companion` uses lazy `sink_parquet` into its exclusively owned destination,
  then `validate_companion` checks exact schema, full prefix parity, sequential
  UInt64 identity, fixed source hash, join statuses and exact lookup annotations.
  Report primary classification mapped/special/missing partitions separately from
  aggregate/partial/crosswalk flags that may overlap. Every role's status counts
  and every source/sample/component partition must reconcile to source totals.

- [ ] **Step 4: Run all annotation and upstream parity/conversion tests.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_mapping_companions.py tests/test_acs_code_mapping.py tests/test_acs_area_mapping.py tests/test_ipums_parity.py tests/test_ipums_conversion.py -q
  ```

  Expected: full fixture fidelity, deterministic row order, correct typed suffix
  and no person-row expansion. Inspect query plans to confirm production person
  tables stay lazy; small public references/lookups may be eager.

- [ ] **Step 5: Review and commit the deliverable.**

  ```bash
  git add src/embedding_data/acs_mapping_companions.py tests/test_acs_mapping_companions.py tests/acs_mapping_fixtures.py
  git commit -m "feat(acs): publish row-preserving canonical companion annotations"
  ```

### Task 8: Complete offline bundle, separate module CLI and fixture V12 path

**Files:**

- Create: `src/embedding_data/acs_mapping_bundle.py`
- Create: `src/embedding_data/acs_mapping.py`
- Create: `tests/test_acs_mapping_bundle.py`
- Create: `tests/test_acs_mapping_cli.py`
- Create: `tests/test_acs_mapping_v12.py`
- Modify: `src/embedding_data/acs_mapping_inputs.py` (final executing-file inventory)
- Modify: `tests/acs_mapping_fixtures.py`
- Modify: `README.md` (new Stage 8 commands and interpretation limits)
- Modify: `CLAUDE.md` (describe shipped software separately from data acceptance)
- Read: existing frozen CLI/error-handling, publication and parity helpers.

**Interfaces:**

- `run_directory(data_dir: Path, run_id: str) -> Path` resolves only safe explicit IDs.
- `build(data_dir: Path, run_id: str, request: SelectionRequest, reference_id: str, *, expected_reference_receipt_sha256: str) -> dict` returns
  `{run_id, directory, outputs_sha256}` only after publication; the JSON response
  is suitable for an external, gitignored build-control receipt.
- `verify_bundle(directory: Path, data_dir: Path, *, expected_outputs_sha256: str) -> dict` returns verified integrity plus **separate** measured mapping/factor
  gate status and explicit limitations. It never edits the bundle.
- `compare_runs(first: Path, second: Path) -> dict` returns ordered logical
  eight-table equality and substantive-report equality, independently of trust.
- `run_acs_mapping_v12(data_dir: Path, monkeypatch) -> dict[str,Path]` in
  `tests/acs_mapping_fixtures.py` creates fixture raw definitions/DDI/CSVs, uses
  the unchanged converter, builds fixture upstream evidence and two Stage 8
  runs, and verifies both with independently captured build-response pins.
  This is a later V12 extension seam, not a target-family or full V12 claim.

Required module commands, with explicit IDs and data root:

```text
python -m embedding_data.acs_mapping acquire-references REFERENCE_ID --data-dir ROOT
python -m embedding_data.acs_mapping import-reference REFERENCE_ID KIND ORIGINAL --data-dir ROOT
python -m embedding_data.acs_mapping build RUN_ID --references REFERENCE_ID --references-sha256 RECEIPT_PIN --codes-run CODES_ID --codes-outputs-sha256 CODES_PIN --geography-run GEOGRAPHY_ID --geography-outputs-sha256 GEOGRAPHY_PIN --ipums-run IPUMS_ID --ipums-outputs-sha256 IPUMS_PIN --ipums-references-sha256 IPUMS_RECEIPT_PIN --data-dir ROOT
python -m embedding_data.acs_mapping verify RUN_ID --outputs-sha256 EXTERNAL_PIN --data-dir ROOT
python -m embedding_data.acs_mapping compare-runs FIRST_ID SECOND_ID --data-dir ROOT
```

The uppercase names in this CLI synopsis are argument names; Task 9 supplies
fully selected production invocations and obtains new pins from external control
receipts. No default selection of a latest run is permitted.

- [ ] **Step 1: Write bundle/CLI/V12 red tests and network guards.**

  ```python
  def test_complete_raw_to_mapping_bundle_and_replay(tmp_path, monkeypatch):
      from acs_mapping_fixtures import run_acs_mapping_v12
      from embedding_data.acs_mapping_bundle import compare_runs

      runs = run_acs_mapping_v12(tmp_path / 'data', monkeypatch)
      result = compare_runs(runs['first'], runs['replay'])
      assert result['equal'] is True
      assert set(result['tables']) == {
          'acs_code_lookup', 'acs_area_lookup', 'puma_county_factors',
          'puma_msa_factors', 'puma_msa_coverage', 'acs_core_canonical',
          'acs_five_year_canonical', 'acs_vintage_canonical'}
      assert all(item['values_equal'] for item in result['tables'].values())
      assert result['substantive_report_equal'] is True
  ```

  Install a fixture `forbid_external_access(monkeypatch)` in
  `tests/acs_mapping_fixtures.py` that raises on socket connections, HTTP client
  creation, dotenv functions, credential readers and IPUMS API construction.
  Patch module-global extract seams as well as library functions, preserving the
  repository test pattern. Only mocked acquisition tests may construct HTTP.
  Pass `--data-dir` on every CLI test.

  Mutation matrix: upstream/source/reference bytes or citation changed; missing
  or extra file/directory; schema/list/null/row-order/duplicate/count change;
  forged inventory with a newly computed local pin; wrong **external** pin;
  changed executing file, Python/dependency/lock; input mutation just before
  publication; occupied final/partial; concurrent final creation; write/reread
  failure. Preserve earlier bundle bytes and caller-unowned files in every case.
  Comparison must detect changed candidate order, flags, populations, source
  order and substantive report content. Test CLI exit codes and no traceback
  person values. Repeated cached acquire must have zero HTTP.

- [ ] **Step 2: Run integration tests red.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_mapping_bundle.py tests/test_acs_mapping_cli.py tests/test_acs_mapping_v12.py -q
  ```

  Expected: missing complete Stage 8 orchestration/CLI/replay behavior; no network
  or credential access is tolerated to make fixtures pass.

- [ ] **Step 3: Implement the bundle transaction, independent verifier and CLI.**
  Validate selections/references and construct all small evidence/lookups/factors
  before writing person outputs. Reserve caller-owned staging, write the five
  reference Parquets sorted by complete natural keys, then the three lazy
  companions with unchanged original prefixes. Reread every output and rerun
  schema/value/mapping/role/factor checks; write finite JSON only.

  Required JSON shapes:

  - `inputs.json`: `schema_version`, `run_id`, `created_at`,
    `git_commit_informational`, `selected_upstreams`, `sources`, `references`,
    `rules`, `frames`, `software`. Freeze every selected detached pin, raw/source/
    reference hash and size, ordered schema, scheme/rule/transform version and
    executing-file/Python/dependency/lock identity.
  - `report.json`: `schema_version`, `run_id`, `created_at`, `tables`,
    `classifications`, `areas`, `factors`, `v8`, `limits`. Tables record ordered
    schemas/row counts, not newly generated physical output hashes. Each other
    section holds the explicit reconciled diagnostics in the acceptance matrix.
  - `outputs.json`: exactly ten file records, for eight Parquets plus inputs and
    report, excluding itself. The final bundle has exactly eleven files and no
    extra directories. Each Parquet record includes SHA-256, size, ordered
    columns/schema and row count.

  Finalize `freeze_software`'s explicit executing inventory with these twelve
  Stage 8 module basenames: `acs_mapping_contract`, `acs_mapping_inputs`,
  `acs_mapping_io`, `acs_mapping_references`, `acs_code_references`,
  `acs_code_mapping`, `acs_area_references`, `acs_geography_factors`,
  `acs_area_mapping`, `acs_mapping_companions`, `acs_mapping_bundle`,
  `acs_mapping`. Carry the immutable upstream inventories and include every
  reused executing helper, including classification/relationship/geography/
  parity/I/O helpers. Do not use a directory glob or freeze only a Git commit.
  Verify the exact explicit file set in tests, with no missing CLI/helper.

  Publish only after the final checks:

  ```python
  def publish_validated(staging: Path, final: Path, selected: SelectedInputs,
                        snapshot: ReferenceSnapshot, data_dir: Path) -> dict:
      selected.verify()
      check_references(data_dir, snapshot.reference_id,
                       expected_receipt_sha256=snapshot.receipt_sha256)
      records = target_io.inventory(staging, [
          'acs_code_lookup.parquet', 'acs_area_lookup.parquet',
          'puma_county_factors.parquet', 'puma_msa_factors.parquet',
          'puma_msa_coverage.parquet', 'acs_core_canonical.parquet',
          'acs_five_year_canonical.parquet', 'acs_vintage_canonical.parquet',
          'inputs.json', 'report.json'])
      target_io.write_json(staging / 'outputs.json', records)
      pin = manifest.sha256_file(staging / 'outputs.json')
      publish_directory(staging, final)
      return {'run_id': final.name, 'directory': str(final), 'outputs_sha256': pin}
  ```

  `build` checks the same captured software fingerprint again immediately before
  this function; it owns and cleans staging on failure. `verify_bundle` first
  authenticates the externally pinned inventory, then checks the strict complete
  file set, output records, selected input/source/reference/software integrity
  and all semantic/preservation checks from raw references. A forged
  inventory's self-computed checksum is not accepted as its authority.

  Compare all eight logical tables using `ipums_parity.compare_ordered`, checking
  ordered schemas/values without requiring identical physical Parquet bytes.
  Report comparison omits only the top-level `run_id` and `created_at` fields:

  ```python
  def substantive_report(report: dict) -> dict:
      return {key: value for key, value in report.items()
              if key not in {'run_id', 'created_at'}}
  ```

  No recursive removal of similarly named fields or provenance flags. Comparison
  does not establish detached trust: verify each run separately before adopting
  replay. CLI uses a new Typer `app` with callback and
  `if __name__ == '__main__': app()`. Acquisition/import return public metadata;
  build returns the response above as JSON; verify/compare return aggregate JSON.
  Success is exit 0; logical comparison mismatch exits 1; validation/acquisition
  failure exits 2 with safe metadata-only diagnostics. Suppress unsanitized
  parser exception chains/locals. Leave `cli.py` and `__init__.py` untouched.

- [ ] **Step 4: Run Stage 8 integration and existing CLI/V12 readiness tests.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_acs_mapping_bundle.py tests/test_acs_mapping_cli.py tests/test_acs_mapping_v12.py tests/test_cli.py tests/test_ipums_cli.py tests/test_target_contract_v12.py -q
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python -m embedding_data.acs_mapping --help
  ```

  Expected: all pass; help lists exactly the five required Stage 8 commands and
  does not load environment files or construct clients. README documents commands,
  external receipt/output pins, offline boundaries, occupied-path recovery and
  interpretation limits. CLAUDE describes software readiness without claiming
  full-data acceptance. Check all upstream frozen software hashes again.

- [ ] **Step 5: Review and commit the deliverable.**

  ```bash
  git add src/embedding_data/acs_mapping_bundle.py src/embedding_data/acs_mapping.py src/embedding_data/acs_mapping_inputs.py tests/test_acs_mapping_bundle.py tests/test_acs_mapping_cli.py tests/test_acs_mapping_v12.py tests/acs_mapping_fixtures.py README.md CLAUDE.md
  git commit -m "feat(acs): verify immutable offline mapping bundles and replay"
  ```

### Task 9: Independent reconciliation and full-data acceptance finding

**Files:**

- Create: `scripts/reconcile_stage8.py`
- Create: `tests/test_stage8_reconciliation.py`
- Create: `specs/findings/stage-8-acs-codes-area-allocation.md`
- Modify: `README.md`, `CLAUDE.md` (selected measured runs/pins only after gates pass)
- Read: all selected upstream evidence and the exact Stage 8 outputs.
- Local only: new controls under
  `data/derived/acs/mapping-controls/stage8_acceptance_20261017/`, a new
  `raw/references/acs-mapping/stage8_acs_references_20261017/` snapshot and
  `derived/acs/mapping/stage8_acs_mapping_20261017{,_replay}/`.

**Interfaces:**

- Independent script `freeze(data_dir: Path, control_dir: Path) -> dict` records
  every existing regular raw/derived file's relative path, SHA-256 and size,
  excluding the new caller-owned controls directory and `raw/manifest.jsonl`
  from the immutable whole-file inventory. Save the manifest's exact bytes,
  original byte length and SHA-256 as a separate prefix control, plus
  software/reconciler identities. The saved manifest hash authenticates those
  prefix bytes; it is not an expected hash of the entire post-acquisition
  manifest. Refuse symlinks and an occupied control ID; never read root `.env`
  or any credential store.
- `reconcile(data_dir: Path, run_id: str, outputs_sha256: str, control_dir: Path) -> dict` independently authenticates the supplied pin and calculates source
  code frequencies, status/flag counts, populations and preservation checks.
- `preservation(data_dir: Path, control_dir: Path) -> dict` verifies every file
  in the immutable inventory against its frozen whole-file hash and size.
  Separately authenticate the saved manifest prefix's length/hash and require
  the current manifest to begin with exactly those bytes, checking this before
  parsing records. Reject truncation or any prior-byte mutation with
  `ValueError` containing `manifest prefix`. Inventory and account for every
  suffix record and new raw path against the complete Stage 8 snapshot receipt,
  independently checking hashes, sizes, unique paths and exact record counts.
  On success return `manifest_prefix_equal:bool`, `protected_files_equal:bool`,
  `manifest_appends_accounted:bool` (all true) and `appended_record_count:int`.
  Any mismatch raises `ValueError`; legitimate accounted appends do not fail
  because the manifest's current whole-file size or SHA-256 differs.
- CLI subcommands `freeze`, `reconcile`, `preservation`, each with explicit
  `--data-dir` and `--control-dir`; reconcile also requires `--run-id` and
  `--outputs-sha256`. Commands emit aggregate JSON and nonzero exit on mismatch.
- This script imports **no Stage 8 builder/parser/validator**. Use independent
  stdlib CSV/JSON/hash and fastexcel/Polars calculations from original references
  and source Parquets. Its own source/test/version hashes belong to the separate
  reconciliation inventory. It is not called to produce the mapping bundle.

- [ ] **Step 1: Write the independent reconciler tests.** Load the script with
  `importlib.util.spec_from_file_location` from the repository's exact script
  path in fixture `reconciliation_module`; expose its three public functions.
  Use the same explicit arithmetic truth as Task 5, then deliberately mutate
  a companion frequency, a population and an earlier protected raw file.

  ```python
  def test_independent_reconciliation_and_prefix_preservation(
          reconciliation_module, tmp_path, monkeypatch):
      from acs_mapping_fixtures import seed_selected_inputs, build_fixture_mapping

      fixture = seed_selected_inputs(tmp_path, monkeypatch)
      controls = tmp_path / 'controls'
      reconciliation_module.freeze(fixture.data_dir, controls)
      result = build_fixture_mapping(fixture, 'independent')
      measured = reconciliation_module.reconcile(
          fixture.data_dir, 'independent', result['outputs_sha256'], controls)
      assert measured['code_frequencies_equal'] is True
      assert measured['population_reconciliation_equal'] is True
      assert measured['role_status_counts_equal'] is True
      preserved = reconciliation_module.preservation(fixture.data_dir, controls)
      assert preserved['manifest_prefix_equal'] is True
      assert preserved['protected_files_equal'] is True

  def test_legitimate_manifest_append_passes_preservation(
          reconciliation_module, tmp_path, monkeypatch):
      from acs_mapping_fixtures import seed_selected_inputs, build_fixture_mapping

      fixture = seed_selected_inputs(tmp_path, monkeypatch)
      manifest_path = fixture.data_dir / 'raw/manifest.jsonl'
      prefix = manifest_path.read_bytes()
      assert prefix
      controls = tmp_path / 'controls'
      reconciliation_module.freeze(fixture.data_dir, controls)
      build_fixture_mapping(fixture, 'accounted_append')
      current = manifest_path.read_bytes()
      assert current.startswith(prefix)
      appended = current[len(prefix):]
      assert appended
      preserved = reconciliation_module.preservation(fixture.data_dir, controls)
      assert preserved['manifest_prefix_equal'] is True
      assert preserved['protected_files_equal'] is True
      assert preserved['manifest_appends_accounted'] is True
      assert preserved['appended_record_count'] == len(appended.splitlines())

  def test_manifest_prior_byte_mutation_fails_preservation(
          reconciliation_module, tmp_path, monkeypatch):
      import json
      import pytest
      from acs_mapping_fixtures import seed_selected_inputs, build_fixture_mapping

      fixture = seed_selected_inputs(tmp_path, monkeypatch)
      manifest_path = fixture.data_dir / 'raw/manifest.jsonl'
      prefix = manifest_path.read_bytes()
      controls = tmp_path / 'controls'
      reconciliation_module.freeze(fixture.data_dir, controls)
      build_fixture_mapping(fixture, 'prior_byte_mutation')
      current = manifest_path.read_bytes()
      assert current.startswith(prefix) and len(current) > len(prefix)
      changed = bytearray(current)
      changed[prefix.index(b': ') + 1] = ord('\t')
      assert len(changed) == len(current)
      assert changed[:len(prefix)] != prefix
      assert changed[len(prefix):] == current[len(prefix):]
      assert [json.loads(line) for line in changed[:len(prefix)].splitlines()] == [
          json.loads(line) for line in prefix.splitlines()]
      manifest_path.write_bytes(changed)
      with pytest.raises(ValueError, match='manifest prefix'):
          reconciliation_module.preservation(fixture.data_dir, controls)
  ```

  `build_fixture_mapping(fixture: FixtureInputs, run_id: str) -> dict` is a plain
  helper in `tests/acs_mapping_fixtures.py` that imports the complete registered
  fixture reference set through Task 2's real lifecycle into a fresh snapshot
  named `<run_id>_references`, captures its receipt pin independently and calls
  the real Stage 8 build with it. Those reference/receipt manifest appends occur
  during this helper call, after `freeze`; `seed_selected_inputs` supplies only
  the earlier upstream inputs. It performs no monkeypatched acceptance or source
  bypass. The mutation case changes one JSON whitespace byte in the old prefix
  while preserving parsed records, total length and the legitimate suffix;
  semantic JSON equality cannot satisfy exact-byte preservation. Add wrong
  external pin, truncated manifest, appended unaccounted raw record, omitted
  county intersection and altered special/unknown reason counts.

- [ ] **Step 2: Run reconciler tests red.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_stage8_reconciliation.py -q
  ```

  Expected: missing independent calculations; the writer's own verification
  cannot stand in for these tests.

- [ ] **Step 3: Implement independent calculations, then test them green.**
  Freeze controls before any production acquisition. Use streaming SHA-256 and
  keep `raw/manifest.jsonl` out of the immutable whole-file comparisons. Verify
  its saved prefix bytes against their frozen length/hash, require the current
  manifest to be at least that long and compare its first saved-length bytes
  exactly before parsing any records. A truncation or prior-byte change fails;
  a larger current manifest is allowed when its suffix is fully accounted.
  After acquisition, require every appended record to correspond to a registered
  Stage 8 original, request, response or generated receipt. Independently hash
  and size every new raw file; reconcile unique paths and the exact file set and
  record count to the snapshot receipt, including the separately manifested
  receipt itself. Do not compare the current whole-manifest hash/size with the
  saved prefix hash/length or relax whole-file checks for any other frozen file.

  Independent source code frequency calculation, retaining source profile and
  sample/component partition, begins with:

  ```python
  def source_code_frequencies(file: Path, paired: str, token: str) -> pl.DataFrame:
      frame = pl.scan_parquet(file)
      component = 'MULTYEAR' if 'MULTYEAR' in frame.collect_schema() else 'YEAR'
      return (frame.select('YEAR', 'SAMPLE',
                  pl.col(component).alias('component_year'),
                  pl.col(paired).cast(pl.String).str.zfill(4).alias('paired_code'),
                  pl.col(token).str.strip_chars(' ').alias('source_token'))
          .group_by('YEAR', 'SAMPLE', 'component_year', 'paired_code', 'source_token')
          .len().sort('YEAR', 'SAMPLE', 'component_year', 'paired_code', 'source_token',
                      nulls_last=False).collect())
  ```

  Compare these with independently grouped companion original columns and with
  companion mapping-status/key frequencies. Separately count `559830`, missing,
  mapped and unparseable states; unknown aggregation reasons; candidate lengths;
  original Q types/value counts; and source-recoding/allocation flags. Check the
  companion's lookup assertions against the authenticated reference tables, but
  do not call the production mapper to generate expected source frequencies.

  Read original Geocorr CSV and independent total-control CSVs with stdlib CSV;
  sum integer intersections with Python integers keyed by full state/area/county.
  Independently pool PUMA populations through the original composition rows and
  check county→group direction. Compute MSA totals/residuals from original
  workbook columns and verify the published output populations/Float64 factors.
  Reconcile observed role statuses using the registered documentation and DDI
  source-state codes; never infer all non-US codes by numeric range. Return
  disjoint status counts, closure maxima and explicit failure counts.

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_stage8_reconciliation.py -q
  ```

  Expected: all pass, including acceptance of the legitimate append, rejection
  of the prior-byte mutation and deliberately wrong but internally
  self-consistent writer outputs. Review/commit the independent script/tests
  before measuring:

  ```bash
  git add scripts/reconcile_stage8.py tests/test_stage8_reconciliation.py tests/acs_mapping_fixtures.py
  git commit -m "test(acs): reconcile mapping populations and statuses independently"
  ```

- [ ] **Step 4: Freeze the actual before-state and verify selected inputs.**
  Inspect occupied run/reference/control names; if any exist, preserve them and
  select fresh IDs with a recorded plan deviation. The following are proposed
  first IDs, not permission to overwrite evidence. Run from the implementation
  worktree with production `--data-dir` explicitly. Record available disk space
  and source sizes before building two companions sets; estimate output/staging
  needs from fixture/first-output measurements and stop on insufficient space.

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python scripts/reconcile_stage8.py freeze --data-dir /Users/lowell/Projects/embedding-data/data --control-dir /Users/lowell/Projects/embedding-data/data/derived/acs/mapping-controls/stage8_acceptance_20261017
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data ipums verify stage7_ipums_verification_20261015_r2 --outputs-sha256 db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc --data-dir /Users/lowell/Projects/embedding-data/data
  ```

  Expected: a new immutable before-state inventory/prefix control and Stage 7
  `status=verified`, with expected `measurement_status=unresolved`. Call the new
  `select_inputs` with all listed Stage 4/5/7 pins to validate complete inventories
  before acquiring references. No upstream rebuild or status edit is justified
  by a failure. Run the full repository checks in Task 10 before freezing final
  production software if they have not yet passed at this checkpoint.

- [ ] **Step 5: Acquire/import the complete actual references and prove cache isolation.**

  ```bash
  set -o noclobber
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python -m embedding_data.acs_mapping acquire-references stage8_acs_references_20261017 --data-dir /Users/lowell/Projects/embedding-data/data > /Users/lowell/Projects/embedding-data/data/derived/acs/mapping-controls/stage8_acceptance_20261017/references.json
  ```

  Here package resolution is offline; the explicit acquisition command alone
  intentionally makes the registered public requests. Expected response fields:
  `reference_id`, `directory`, `receipt_sha256`. Check every actual original's
  hash/size/layout against the plan's registered edition. Keep `noclobber` enabled
  in the same shell for all subsequent control-output redirections; inspect and
  choose fresh controls rather than replace a previously captured detached pin.
  If direct access is blocked, use `import-reference` with exact browser originals saved under their
  registered filenames in the new control directory's `public-originals/`;
  record retrieval-time proxies. Do not resave XLS/XLSX in Excel. A failed
  acquisition/occupied partial requires inspection and a fresh reference ID;
  never silently resume it or import evidence into an old frozen snapshot.

  Re-run cached acquisition with `make_client` patched to raise, record
  `http_client_calls=0`, and compare its receipt pin to the independently saved
  `references.json`. Reproduce the classification reference conflict matrix;
  confirm approved reference roles and every observed official pair. Validate
  the complete 52-state geography originals before scope filtering. If there is
  an unexpected membership gap, county split, namespace change or application
  error, preserve diagnostics and stop that gate; fixtures cannot substitute.

- [ ] **Step 6: Build the first complete production mapping bundle.** Read the
  reference pin from the **external** acquisition response; capture the builder's
  returned pin in another external control file. Use the same shell for these
  variable definitions and invocations:

  ```bash
  stage8_control_dir=/Users/lowell/Projects/embedding-data/data/derived/acs/mapping-controls/stage8_acceptance_20261017
  stage8_reference_pin=$(UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python -c 'import json, pathlib; print(json.loads(pathlib.Path("/Users/lowell/Projects/embedding-data/data/derived/acs/mapping-controls/stage8_acceptance_20261017/references.json").read_text())["receipt_sha256"])')
  stage8_build_args=(--references stage8_acs_references_20261017 --references-sha256 "$stage8_reference_pin" --codes-run stage4_v11_20261013_r2 --codes-outputs-sha256 15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a --geography-run stage5_geography_20261014 --geography-outputs-sha256 5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d --ipums-run stage7_ipums_verification_20261015_r2 --ipums-outputs-sha256 db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc --ipums-references-sha256 3163968dde603ba53f807976dd09b9e40d73235a98c6f36e4e02c67ec4239c9c --data-dir /Users/lowell/Projects/embedding-data/data)
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python -m embedding_data.acs_mapping build stage8_acs_mapping_20261017 "${stage8_build_args[@]}" > "$stage8_control_dir/build-first.json"
  stage8_first_pin=$(UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python -c 'import json, pathlib; print(json.loads(pathlib.Path("/Users/lowell/Projects/embedding-data/data/derived/acs/mapping-controls/stage8_acceptance_20261017/build-first.json").read_text())["outputs_sha256"])')
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python -m embedding_data.acs_mapping verify stage8_acs_mapping_20261017 --outputs-sha256 "$stage8_first_pin" --data-dir /Users/lowell/Projects/embedding-data/data > "$stage8_control_dir/verify-first.json"
  ```

  Expected: all eight tables, all **12,238,491** source rows preserved in the
  3,206,859 / 7,456,212 / 1,575,420 companions, and every measured gate below
  passing. The first-file inspection is a checkpoint, not permission to weaken
  any full-file gate. Keep public checksums/control responses outside the bundle;
  never replace them with a checksum calculated solely from its current contents.

- [ ] **Step 7: Build and verify a second named offline replay.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python -m embedding_data.acs_mapping build stage8_acs_mapping_20261017_replay "${stage8_build_args[@]}" > "$stage8_control_dir/build-replay.json"
  stage8_replay_pin=$(UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python -c 'import json, pathlib; print(json.loads(pathlib.Path("/Users/lowell/Projects/embedding-data/data/derived/acs/mapping-controls/stage8_acceptance_20261017/build-replay.json").read_text())["outputs_sha256"])')
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python -m embedding_data.acs_mapping verify stage8_acs_mapping_20261017_replay --outputs-sha256 "$stage8_replay_pin" --data-dir /Users/lowell/Projects/embedding-data/data > "$stage8_control_dir/verify-replay.json"
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python -m embedding_data.acs_mapping compare-runs stage8_acs_mapping_20261017 stage8_acs_mapping_20261017_replay --data-dir /Users/lowell/Projects/embedding-data/data > "$stage8_control_dir/compare-runs.json"
  ```

  Expected: both detached verifiers pass; all eight ordered logical tables and
  substantive report content are exactly equal. Physical Parquet hashes may
  differ. An executing code/reference/dependency correction requires fresh
  selected run IDs and fresh full acceptance, leaving earlier runs untouched.

- [ ] **Step 8: Reconcile independently, reverify preservation and audit the whole tree.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python scripts/reconcile_stage8.py reconcile --run-id stage8_acs_mapping_20261017 --outputs-sha256 "$stage8_first_pin" --data-dir /Users/lowell/Projects/embedding-data/data --control-dir "$stage8_control_dir" > "$stage8_control_dir/reconciliation.json"
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python scripts/reconcile_stage8.py preservation --data-dir /Users/lowell/Projects/embedding-data/data --control-dir "$stage8_control_dir" > "$stage8_control_dir/preservation.json"
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data audit --data-dir /Users/lowell/Projects/embedding-data/data
  ```

  Expected: independent frequency/population/status counts agree; every protected
  earlier raw/derived file and source schema/hash is unchanged; the old manifest
  is an exact byte prefix; every append is accounted; whole-tree audit exits 0
  with zero discrepancies. Re-run selected upstream public/new-selector integrity
  checks against their original pins after acceptance. Do not call builders.

- [ ] **Step 9: Write and commit the actual measured finding.** The finding must
  contain the exact selected first/replay/reference IDs; detached pins; full raw,
  public-reference, executing-software and ten-file output inventories with
  hashes/sizes; all eight ordered output schemas (including original source
  prefixes); Python/dependency/lock identities; independent control/reconciler
  hashes and aggregate results; measured durations and software-review status.
  Include every acceptance matrix value, V8 full-source checks and any split,
  unknown-reason counts, source flag partitions and explicit limits. Only public
  metadata and aggregates enter git. Do not copy a companion, raw person row,
  source person ID or private control directory into the repository.

  Mark software completion separately from production data acceptance. At this
  checkpoint the finding may say measured gates passed while whole-branch review
  and completion protocol remain pending. Do not tick Stage 8 yet.

  ```bash
  git add specs/findings/stage-8-acs-codes-area-allocation.md README.md CLAUDE.md
  git commit -m "docs(acs): record measured Stage 8 mapping and allocation acceptance"
  ```

### Task 10: Reviews, measured marker update and Stage 8 completion protocol

**Files:**

- Modify after gates pass: `specs/embedding-evaluation-data-spec.md` (measured
  R6.3/V8 citation only), `specs/findings/stage-8-acs-codes-area-allocation.md`
  (final check/review record), this plan and `specs/deferred_items.md` if needed.
- Modify only on actual completion: `specs/embedding-evaluation-data-spec-roadmap.md`.
- Retire only on actual completion: this plan to
  `specs/plans/completed/8-acs-codes-area-allocation.md`; its exclusively
  implemented Stage 8 spec to `specs/completed/acs-codes-area-allocation.md`.
- The source specification and roadmap remain live. No Stage 9–13 software or
  complete marker is part of this task.

**Interfaces:**

- Consumes all measured acceptance evidence, resolved task reviews, a final
  whole-branch review and the writing-plans Plan Completion Protocol.
- Produces actual Stage 8 completion markup, measured source-spec citations,
  retired plan/spec and a shipped `Handoff to later stages` for Stages 9–13.

- [ ] **Step 1: Run the applicable repository checks and inspect complete output.**

  ```bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked behave
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked ruff check .
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv lock --check --offline
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pre-commit run --all-files
  ```

  Expected: full pytest and every Behave scenario pass (the opt-in live network
  canary remains deselected); Ruff/lock/hooks pass; no frozen software edit or
  hidden data addition. Run this suite before production freeze as well if the
  integrated code has not yet passed. Repeat after corrections/new failures,
  not merely as a substitute for reviewing results. Existing always-run commit
  coverage checks remain required.

- [ ] **Step 2: Request and resolve final whole-branch review.** Apply
  requesting-code-review, supplying the approved spec, this plan, full diff,
  measured finding and independent acceptance evidence. Per-task review does
  not replace this gate. Apply receiving-code-review critically to feedback.
  Run relevant tests after fixes. If any fix changes frozen executing software,
  reference schema or dependency identity, return to Task 9 for fresh named
  production builds/replay and reconciliations; old runs remain immutable.
  Update the finding with the resolved review and check results.

- [ ] **Step 3: Replace R6.3's open marker only when measured evidence supports it.**
  If full-source V8 finds no split counties and reconciles all units, replace
  exactly:

  ```text
  Whether the 2020 vintage kept the
  county-line rule is *(open — resolved by verification, not argument, discharged
  by V8)*.
  ```

  with:

  ```text
  The selected 2020 definitions satisfy the whole-county rule under the full-source
  county-to-group and population reconciliation checks. *(verified; V8;
  [measured Stage 8 finding](findings/stage-8-acs-codes-area-allocation.md))*.
  ```

  Only this measured citation/status update is proposed, not an assumption about
  unmeasured vintages or an amendment to source allocation quality. If splits are
  found, do not use that replacement: finish the official population-intersection
  route required by the spec and record the actual split rule/finding before
  proposing accurate replacement wording for review. Required unresolved V8
  work cannot be deferred while marking Stage 8 complete. Add a measured V8
  finding citation to its Verification item, preserving the documented split
  requirement and ACS-only V11 scope; do not close CPS V11 or full V12.

- [ ] **Step 4: Apply the resolve-before-defer completion gate and write actual handoff.**
  Batch unresolved owner decisions before markup; finish newly unblocked work.
  Then tick completed plan steps once, annotate actual deviations/skips and
  update earlier deferred items this plan implemented. New deferrals require
  self-contained paths, reason, `Size` and closure condition. No required
  production/reference/verification gate is silently moved to a later stage.

  Add `## Handoff to later stages` based on shipped APIs, schemas, selected pins,
  actual deviations/refusals (including reverted interim interfaces) and any
  specific deferred-backlog section. Revalidate **every** later Stage 9–13:

  - Stage 9: exact companions/code/role/factor API, IDs, schema/nullability and
    independent ambiguity/special/source-imputation/source-recoding/allocation
    flags. Retains membership, eligibility, workplace work-from-home exclusion,
    estimates, pooling, uncertainty and family V12 responsibility.
  - Stage 10: preserved selected ITA inputs and behavior; report actual shared
    API effects only. An ACS change authorizes no upstream ITA rebuild.
  - Stage 11: retained CPS mapping/linkage and unresolved 2026 9890 authority;
    ACS 559830 grants no CPS bypass. Preserve canonical parentage and relation APIs.
  - Stage 12: ACS through Stage 9's later helpers and CPS through Stage 11;
    Stage 8 alone supplies no worker-profile estimator or eligibility rule.
  - Stage 13: vintage comparator complete flagged candidates, source/target
    reference frames and selected physical inventories, distinct from logical
    replay. Comparator targets, citations, V9 and full eight-family V12 stay here.

  Cite the approved spec instead of restating it. Tick and stamp Stage 8 in the
  roadmap only now, pointing at the plan's retired path. Leave all later stage
  boxes unchanged. The actual handoff, rather than planning defaults, is the
  evidence derive-roadmap uses to amend later entries at the next resume.

- [ ] **Step 5: Triage backlog, retire plan/spec and stop this stage.** Run the
  writing-plans backlog statistics command and report open count/closure rate/
  aged tail. If its rubric triggers triage, present the read-only proposal; do
  not execute dispositions without owner direction. Commit completion markup
  and handoff, then retire plan/spec in one `chore(specs): retire plan 8` commit,
  correcting relative links for their deeper locations. Confirm no other live
  plan implements the Stage 8 spec before moving it; keep source spec/roadmap live.
  Apply finishing-a-development-branch to the owner's chosen integration and
  worktree cleanup, with no automatic next-stage planning. End with a resume-
  roadmap handoff. This protocol is for **implementation completion**, not for
  the current planning-only commit.

## Measured acceptance matrix

Every gate below is observable and required before implementation completion.
Fixtures demonstrate software behavior; only Task 9's actual measurements adopt
data findings. A source/reference contradiction is a failed gate, not an empty
candidate set, zero population or successful exclusion.

| Gate | Measurement / exact acceptance | Implementing tasks |
| --- | --- | --- |
| Selected trust | Stage 4/5/7 inventories, receipt pins, complete raw citations, hashes/sizes/schemas and unchanged software/dependencies all verify | 1, 8–9 |
| Reference completeness | All registered originals/request/response bytes and independent PUMA/county controls present; no unaccounted new manifest records; cached HTTP count 0 | 2, 5, 9 |
| Classification membership | Genuine M/P/S/Z/combinations/suffixes, numeric coarse nodes, X/Y/nested collapses and official parentage; zero unsupported relation endpoints or unexplained pair mismatches | 3–4, 9 |
| ACS V11 | Zero unparseable nonmissing codes across all 12,238,491 rows; every true classification mapped; missing separately counted; 559830 separately unmapped with empty candidates/null nodes | 4, 7–9 |
| Special cross-check | Remeasure design counts core 5,204 / five-year 14,799 / vintage 3,405 for 559830; any disagreement against pinned source bytes is investigated, not adjusted away | 4, 7, 9 |
| Aggregation reasons | Publish documented category-design/disclosure counts and explicit unknown counts with locators; no invented motive or X/Y wildcard membership | 3–4, 7, 9 |
| Vintage/provenance | Annual 2022 NAICS 2017; annual 2023/2024 NAICS 2022; delivered five-year NAICS 2022 with separate interview/source recoding; SOC 2018; singleton flags persist | 3–4, 7, 9 |
| Original fidelity | Exact ordered prefix schemas, values and duplicate multiplicity, sequential UInt64 source rows and correct source SHA; all three exact source counts preserved | 7–9 |
| Source flags | Every original Q field/value/type unchanged, including core String/all-null 2023 QMIGRAT1, five-year Int64 and vintage absence; unavailable evidence stays null/unavailable | 6–9 |
| Geographic roles | Complete observed key inventory; disjoint applicable/NIU/foreign/territory/documented-unavailable counts per role/profile/component reconcile to source totals; no unexplained null or unknown key | 5–9 |
| Residence factors | Exact integer intersections and independent PUMA/county closure; every applicable scoped key covered; each factor sum differs from one by at most 1e-12 | 5–9 |
| V8 | Full PUMA→group and county→group checks, original/scope counts, derived membership agreement and population reconciliation; no unresolved county split or fabricated weight | 5, 9–10 |
| Frame compatibility | All nine CT planning regions; no legacy county relabel; complete county inventory, metro/micro types and non-CBSA status preserved; distinct vintages/year fields | 5–9 |
| MSA intersections | All published intersections retained before scope; exact whole-MSA and whole-PUMA integer agreement; both conditioning directions correct; residual includes PUMAs absent from MSA rows, never rescaled | 5, 9 |
| Published rounding | Geocorr fraction and MSA percentage rounding checked at their explicit bounds, independently of integer/factor closure | 5, 9 |
| Atomic publication | No replacement of occupied/racing final; no final mapping bundle on failure; only owned temporary files cleaned; no upstream mutation | 1, 8 |
| Offline chain | Actual fixture raw CSV/DDI/definitions → unchanged converter → three companions and inventories; network/credentials denied; no target-family closure claimed | 8 |
| Detached trust / replay | Two public verifiers use external control pins; all eight ordered logical tables and substantive reports exactly equal; physical-byte equality not required | 8–9 |
| Independent reconciliation | Independent source code/flag/status frequencies, population controls/group/MSA/residual arithmetic agree; script/evidence identities recorded | 9 |
| Preservation / repository | Immutable inventory excludes `raw/manifest.jsonl`; every other earlier protected file unchanged; saved manifest bytes remain an exact prefix with every append accounted; legitimate-append and prior-byte-mutation regressions pass; whole-tree audit zero; pytest/Behave/Ruff/lock/hooks/reviews pass | 9–10 |

## Self-review and execution handoff

Before committing this planning artifact, check the approved spec section by
section against the matrix and task interfaces. Scan for unresolved implementation
stand-ins, inconsistent type/function names and unnamed fixtures. Verify the
verbatim roadmap header and all selected pins, validate local Markdown links,
parse every Python block for syntax, and confirm only the plan changed. The
planning commit must not create source modules, production references, mapping
runs, a finding, roadmap completion markup or spec retirement.

Planning self-review on 2026-10-17 mapped each approved spec section to the task
and acceptance matrix. All 24 Python blocks parse, all 34 shell blocks pass
`bash -n`, existing local Markdown links resolve, and the required header occurs
once verbatim. Executing the schema declarations confirms the five reference
schemas and 114-field companion suffix; the unequal-population arithmetic
example produces exactly 0.15/0.85. Source-schema widths, task order, selected
pins, explicit new-module inventory and reference-role/unknown-reason gates were
checked for consistency. These are plan checks, not Stage 8 software/data gates.

Review defaults proposed by this plan:

1. Exact typed schemas and deterministic lookup/factor IDs, with source-prefix
   fidelity and materialized companions rather than person-level cross-products.
2. The bounded Census PUMS industry pair/membership authority, preserving the
   contradictory IPUMS pair table as explicit diagnostic evidence. This is
   supported by the complete observed-pair preflight, not a generic preference.
3. Three complete Geocorr queries for intersections and independent PUMA/county
   controls, full 52-state validation then explicit 50-state-plus-DC publication.
4. Role-specific delivered state code rules, separately from composition encodings;
   style/legend evidence for documented OCCSOC reasons; unknown where unsupported.
5. Separate module CLI, unchanged upstream frozen software and native exclusive
   directory publication with a refusal on unsupported guarantees.
6. Proposed dated production/reference/control IDs, inspect-before-use and new IDs
   for occupied paths or substantive corrections; measured gates, not fixtures,
   authorize completion.

Plan review precedes execution. Recommended after approval: start a **fresh
session** and execute task-by-task via subagent-driven-development, with focused
ownership and two-stage review. The reference, classification, geography and
publication boundaries have distinct failure modes that benefit from separate
review gates. Inline execution via executing-plans is available if the owner
chooses it. This planning session commits the plan and stops; it does not choose
or start implementation, tick Stage 8 or plan Stage 9.
