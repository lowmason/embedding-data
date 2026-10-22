# ACS targets

> Required next skill: writing-plans in a fresh session, after owner review
> of this committed specification. Do not implement during brainstorming.

The owner approved the architecture, scope and eligibility, estimation, outputs,
and verification sections on 2026-10-19. This document records that design;
Stage 9 implementation and measured acceptance remain planned.

## Scope and governing contracts

Stage 9 of [the roadmap](embedding-evaluation-data-spec-roadmap.md) implements
R3.6, R3.7, R3.8, R3.10, R3.11 use, and the staffing-pattern, area-mix,
commuting and migration ACS rows of R7.2 in
[the source spec](embedding-evaluation-data-spec.md). R7.1, R7.4, R8 and R9
govern outputs, provenance, disclosure, leakage and offline operation.

Primary targets preserve observed ACS industry/occupation categories and native
PUMA geography. Complete canonical candidate mappings accompany category units.
Evidence-supported canonical-leaf views and population-allocated county/MSA
area mixes are separate products. County/MSA commuting or migration flows are
out of scope: marginal population factors supply no joint endpoint allocation.

Use the existing Polars, Typer and dependency stack. Production transformations
are deterministic lazy Polars; small public reference tables may be eager.
Keep family definitions small and explicit. Shared components own authenticated
selection, universe/evidence rules, aggregation, pooling, replicate estimation,
projections and bundle publication/verification. A configuration language or
general target framework is unnecessary.

The following remain outside this stage:

- Worker profiles and CPS cross-sections: Stage 12.
- Five-year and 2022 vintage comparator targets, V9 minimum cell counts and
  complete eight-family V12 acceptance: Stage 13.
- CPS linkage and job-change flows: Stage 11; ITA target additions: Stage 10.
- Embedding scoring, group-embedding methods and evaluation thresholds: the
  successor evaluation-protocol specification.
- Microdata release, upstream rebuilding and any embedder training use.

## Selected inputs and trust boundary

Read [completed plan 8 and its Handoff](plans/completed/8-acs-codes-area-allocation.md#handoff-to-later-stages)
and the [measured Stage 8 finding](findings/stage-8-acs-codes-area-allocation.md#handoff-to-later-stages--actual-apis).
These records, rather than provisional plan interfaces, define shipped APIs,
exact schemas, historical compatibility and the selected physical inventories.
Also consume the Stage 4, 5, 6 and 7 Handoffs cited by roadmap Stage 9.

The source data root is explicitly `/Users/lowell/Projects/embedding-data/data`.
All commands require an explicit data root; a worktree default is insufficient.
No production-data command runs as part of writing this specification.

| Input | Selected identity | Detached SHA-256 |
| --- | --- | --- |
| Stage 8 first mapping | `stage8_acs_mapping_20261018_r7` | `1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4` |
| Stage 8 replay | `stage8_acs_mapping_20261018_r7_replay` | `a115c5f7e2691ecbffe763bd1b6b9780fb6a71bc512a2691cf4014f9857b3565` |
| Stage 4 codes | `stage4_v11_20261013_r2` | `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |
| Stage 5 geography | `stage5_geography_20261014` | `5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d` |
| Stage 7 verification | `stage7_ipums_verification_20261015_r2` | `db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc` |
| Stage 7 reference receipt | `stage7_ipums_references_20261015_r2` | `3163968dde603ba53f807976dd09b9e40d73235a98c6f36e4e02c67ec4239c9c` |

Stage 8 mappings live under `derived/acs/mapping/<run_id>/`. Authenticate the
explicit selected bundle with `acs_mapping_bundle.verify_bundle(directory,
data_dir, expected_outputs_sha256=...)` before consuming its companions, code
and area lookups, county factors, MSA factors and MSA coverage. The replay is
independent evidence, not a fallback or a source of mixed-run tables.

Preserve the seven-field Stage 8 `SelectionRequest`,
`acs_mapping_inputs.select_inputs(...).verify()`, and all upstream checks.
The Stage 9 selector must bind the authenticated Stage 8 recorded upstream
selection to that request. A latest alias, inferred pin, or integrity-only
check of individual Parquets is insufficient.

The three authenticated ACS source/companion identities are:

| Profile | Delivery | Original rows | Original Parquet SHA-256 |
| --- | --- | ---: | --- |
| Core | `usa_00001` | 3,206,859 | `c07f9e7abe2c5dfdb8f9488a1f574d4cf49ab7945c3ad2ffc9daec5eaba47d10` |
| Five-year | `usa_00003` | 7,456,212 | `c5846bde221e7785051a4a4075aa6a71cc267a1f4497168a96df05d7c50f78fe` |
| Vintage | `usa_00002` | 1,575,420 | `b6ffab7bd974f72b4fbc913f261779f5ce3145a915849bf92e946bb6b649240d` |

Only the core produces Stage 9 targets. The selector may authenticate the
other delivered profiles and the selected CPS inputs under existing upstream
contracts; authentication does not authorize new target families or periods.

Source identity is `(source_parquet_sha256, source_row)`, with zero-based
UInt64 positions within each source Parquet. Preserve source order, all
original values and duplicate multiplicity. A position is not person linkage.
Do not expand or rewrite companions during estimation.

Code lookup natural keys remain `(system, source_scheme, paired_census_code,
source_token)`. Area lookup keys remain `(profile, sample_id, release_year,
component_year, role, source_state_code, source_area_code)`. Keep these keys
distinct from the stable unit identifiers used by aggregate targets.

Preserve the narrow historical Stage 5 creator-hash compatibility approved in
plan 8 D5. No new stale-software exception follows. Stage 7 unresolved machine
fields and Stage 8 conservative adoption fields remain unchanged; their
findings separately record adoption.

## Scope and eligibility

### Product matrix

Every family is built for both universes and both source-evidence policies.
The extra migration product provides a comparison at a matched period.

| Family/product | Source-evidence policy | Annual samples | Pool divisor |
| --- | --- | --- | ---: |
| Staffing and native workplace mixes | Strict and sensitivity | 2023, 2024 | 2 |
| Native commuting | Strict and sensitivity | 2023, 2024 | 2 |
| Native headline migration | Strict | 2024 | 1 |
| Matched migration sensitivity | Sensitivity | 2024 | 1 |
| Pooled migration sensitivity | Sensitivity | 2023, 2024 | 2 |
| County/MSA area mixes | Strict and sensitivity | 2023, 2024 | 2 |

Canonical views cover staffing and native workplace mixes at the same periods
and evidence policies, with an additional supported-leaf restriction.

Strict-evidence county/MSA products remain population-allocated views. They
are not native-geography headline products. All headline descriptions state
which universe, family, period and required source evidence they mean.

### Universes

- `civilian_employed`: the selected employed source restricted to `EMPSTATD`
  10 (At work) or 12 (Has job, not working). Armed forces are excluded.
- `private_wage_salary`: the civilian universe restricted to `CLASSWKRD` 22
  (Wage/salary, private) or 23 (Wage/salary at non-profit). Incorporated and
  unincorporated self-employed workers are outside this comparison universe.

Freeze these owner-adopted category sets against each selected delivered DDI.
Do not infer membership from a numeric range or a historical general category.
Do not add a household-only, group-quarters, earnings or hours restriction.
These are current-job worker targets; migration does not establish a prior
job or a job-related reason for moving.

### Family definitions and measures

Each family defines usable values, pair units and a denominator group:

| Family | Pair | Additional eligibility | Forward-share denominator |
| --- | --- | --- | --- |
| Staffing pattern | Observed industry -> observed occupation | Both observed categories usable; temporarily absent workers remain eligible | All eligible occupations within the same observed industry |
| Workplace industry mix | Workplace PUMA -> observed industry | Applicable domestic workplace; valid non-home transportation category | All eligible observed industries within that workplace PUMA |
| Workplace occupation mix | Workplace PUMA -> observed occupation | Same workplace and transportation requirements; occupation usable | All eligible observed occupations within that workplace PUMA |
| Commuting | Residence PUMA -> workplace PUMA | Both domestic endpoints applicable; valid non-home transportation category | All eligible workplace destinations within the residence PUMA |
| Migration | Prior migration PUMA -> current residence PUMA | Domestic mover, `MIGRATE1` 2 or 3; both endpoints applicable | All eligible current destinations within the prior migration PUMA |

Workplace industry mixes also require their industry category to be usable.
The two workplace mixes share family `area_mix`; their distinct unit types
and units identify the code dimension.

For workplace mixes and commuting, restrict to the at-work civilian category
and a delivered applicable transportation value other than `TRANWORK` 80
(Worked at home). N/A is not evidence of non-home work. Keep work-from-home
excluded in sensitivity products too. This follows the last-week-worker
universe of the transportation variable, rather than assigning temporarily
absent workers an inferred workplace or commute.

Migration includes identifiable domestic movers. Stayers, unknown movement,
foreign/territory origins and NIU/unidentifiable endpoints receive separate
diagnostics. Never infer a prior residence PUMA, turn unavailable geography
into no migration, or manufacture a stayer self-loop. Residence and migration
PUMA definitions differ; equal numeric codes do not identify the same area.

Publish only `annual_average_total` and `forward_share`. Shares describe
distributions among the eligible records with the required pair identified.
They are not migration probabilities, population-wide migration rates,
reverse conditional shares or joint population shares.

Every denominator uses exactly the same universe, evidence policy, period,
projection restrictions and eligible records as its numerator. Missing flow
endpoints are diagnostic exclusions, never zero flows or denominator-only
workers. Published cells require positive full-weight support; do not densify
the unobserved Cartesian product into asserted zero estimates.

### Required source-allocation evidence

Strict headline eligibility requires usable evidence supporting nonallocation
for this explicit required set:

| Applicability | Required delivered flags |
| --- | --- |
| Every family and both universes | `QEMPSTAT`, `QIND`, `QOCC` |
| Private wage-and-salary universe additionally | `QCLASSWK` |
| Workplace mixes and commuting additionally | `QPWSTAT2`, `QTRANWOR` |
| Migration additionally | `QMIGRAT1`, `QMIGPLC1` |

Interpret a flag using its own delivered DDI/domain and the applicable family
universe. In these selected ACS deliveries, documented zero values support
nonallocation only after the associated substantive field is applicable and
usable. In particular, QIND and some universe flags combine original entry
with NIU; their zero alone is not a global clean-record assertion.

Keep separately classified nonallocation, allocated, edited/failed-edit,
unavailable, and not-applicable evidence, including per-variable raw-value
counts and references. QMIGPLC1 includes failed-edit categories, so a generic
nonzero-is-allocated Boolean is prohibited. Unknown labels or unexpected
nonmissing flag values fail rule validation rather than being guessed.

The selected 2023 core has all-null String QMIGRAT1; 2024 has documented
String 0/4 values. Consequently strict headline migration uses 2024 only.
Never copy five-year flag evidence into an annual record or convert missing
flag evidence to false. Preserve independent source-imputation, source-recoding,
classification and geographic-allocation evidence from Stage 8.

Sensitivity includes known allocated, edited and unavailable-evidence cases
that satisfy the same substantive universe and family endpoint rules. Keep
those inclusion reasons separate in diagnostics; a record may have more than
one reason. Sensitivity does not repair a missing endpoint or category.

Undelivered PUMA-specific allocation evidence remains explicitly unavailable.
The required delivered-flag checks do not certify every geographic field free
of source imputation. Applying a reference factor always retains geographic
allocation provenance, independently of source Q evidence and fractional split.

Retain the approved ACS-only OCCSOC 559830 special as an observed category
where otherwise eligible, with empty canonical candidates and null canonical
nodes. Civilian eligibility comes from EMPSTATD, not a guessed repair of this
special. Report any such civilian/special combination separately.

### Separate projections

Canonical staffing/native-area views require supported scalar canonical nodes
at NAICS six-digit / SOC detailed resolution for every code dimension used.
Use the frozen scalar mapping and declared node-table level, not the number
of candidates, a common ancestor, a code prefix or a chosen crosswalk side.
Retain all aggregate, partial, exception, reference-ambiguity and crosswalk
flags even when a scalar exists. Crosswalked/imputed observations cannot be
promoted into strict headline eligibility.

Recompute canonical-view denominators on the supported subset. Report coverage
loss against the corresponding observed-category product. No candidate
cross-product, equal weighting, employment-based classification allocation or
implicit hierarchy rollup is part of this design.

County/MSA views allocate only workplace area mixes. Use the selected
work/migration-PUMA county factors for workplace groups, then selected typed
county-to-CBSA membership for metropolitan rollups. Residence-PUMA MSA factors
are not workplace factors. Keep their different conditioning directions and
geographic frames explicit if used for reference reconciliation.

Preserve all non-MSA mass; it includes micropolitan areas as well as counties
outside any CBSA. Distinguish these residual categories and never renormalize
listed MSAs to exhaust a workplace group. Do not assign metros from MET2023,
PWMET23 or MIGMET23. Keep 2020 population/PUMAs, 2022 county composition,
2025 county inventory and July 2023 delineations distinct, including all nine
Connecticut planning regions.

## Shared estimation

### Exact weights and annual-average pooling

Adopt Stage 7 literal CSV weights at factor 1. DDI implied decimals describe
fixed-width storage, not an additional divisor. Use `measure_weights` and
`scan_numeric_csv(csv_path, diagnostics, source)` for their shipped lexical
Decimal38 scan contract, not as an inherited estimator. Own the temporary
CSV lifetime with `ipums_conversion.decompressed_csv`.

Align the 81 weight columns with companion source positions and verify exact
row counts/order before aggregation. This separate scan does not rewrite or
reinterpret the original-converter fidelity evidence. Reject invalid numeric
values, missing required weights, exponent/scale violations or Decimal overflow.
PERWT supplies point estimates; exactly REPWTP1 through REPWTP80 supply
variance replicates. REPWTP itself is only an availability helper.

For each declared product with k annual samples, divide PERWT and each
numbered replicate by k. The approved core uses k=2; 2024-only migration uses
k=1. k belongs to the declared product, not the nonempty support years of a
particular cell. Retain negative replicate weights, without clipping or
dropping records on that basis. Household weights are not person estimators.

Aggregate native weighted masses with Decimal arithmetic before Float64
publication. Use deterministic, ordered reductions wherever fixed Float64
population factors enter; a replay must not depend on hash/group scheduling.

### Point estimates and replicate SEs

For eligible records i, cell membership c and matching denominator membership d:

```text
cell_total = sum_i(PERWT_i * c_i) / k
denominator_total = sum_i(PERWT_i * d_i) / k
forward_share = cell_total / denominator_total

For r = 1..80, recompute the complete statistic with REPWTP_r instead of PERWT.
SE(theta) = sqrt((4 / 80) * sum_r((theta_r - theta_full)^2))
```

Pooling is the source specification R3.7 contract. A share is the ratio of
pooled totals, not the mean of annual shares. Replicate numerator and
denominator both change; independently combining their SEs loses covariance.
Eligibility, category membership and reference factors stay fixed across
replicates. No model-based uncertainty or alternative cross-year covariance
construction is introduced by this stage.

Store full and all 80 replicate aggregates. Apply workplace-to-county factors
to the native full/replicate aggregates and then roll allocated counties into
MSAs. Each allocated measure is recomputed at its own denominator grain.
Sampling SEs are conditional on fixed factors; they do not quantify allocation
error, mapping uncertainty, nonresponse bias or classification probabilities.

### Support and undefined estimates

- `n_unweighted` counts contributing source positions, preserving duplicate
  multiplicity. Do not divide it by k or call it unique people.
- In allocated cells it counts input records with positive allocation support;
  this is explicitly labeled input support and is not additive across areas.
  Zero-factor rows supply no support. Keep fractional support mass separately.
- `n_weighted` is cell weighted mass for both target measures. Record the
  denominator weighted mass and unweighted support in the support table.
- A nonpositive full-sample denominator has no defined forward share. Record
  its reason and support diagnostic; do not publish a fabricated point value.
- When the point share is defined but any replicate ratio is undefined, keep
  the point with `se=null`, `se_method=none` and an explicit reason plus the
  affected replicate numbers. Never drop replicates or substitute another SE.
- Zero replicate denominator or nonfinite ratio makes that replicate
  undefined. Finite signed replicate results are retained, even outside the
  full-sample share range; do not clip negative replicate weights or ratios.
- Invalid input weights and nonfinite full estimates fail the build. A defined
  finite SE uses all 80 replicates and `se_method=replicate`.
- All targets retain `size_gate_pending`; no minimum count is chosen here.

## Outputs, identities and publication

Publish one immutable eleven-file bundle under `derived/acs/targets/<run_id>/`.
There are eight Parquets and three JSON files:

| File | Required content and identifying grain |
| --- | --- |
| `targets_observed.parquet` | All four primary families, declared universes/evidence policies/periods, totals and forward shares |
| `targets_canonical.parquet` | Supported canonical-leaf staffing and native area mixes with their own denominators and coverage |
| `targets_allocated_area_mix.parquet` | County and metropolitan area mixes, preserving source-evidence policy and allocation provenance |
| `target_units.parquet` | Unique `(unit_type, unit)` registry with complete code/area identity and mapping provenance |
| `target_support.parquet` | Cell and denominator counts/masses, annual contributions, allocation support and undefined-point reasons |
| `replicate_estimates.parquet` | Full statistic keys and every numbered replicate numerator, denominator, estimate, status/reason |
| `eligibility_diagnostics.parquet` | Aggregates by source/profile/year/family/base universe/evidence policy/view and reason |
| `allocation_residuals.parquet` | Workplace-group/code/evidence/universe/period non-MSA totals and all 80 replicates, distinguishing micro/no-CBSA residuals |
| `inputs.json` | Selected identities, citations, complete rules/registries, frames and software/dependencies |
| `report.json` | Substantive aggregate reconciliation, coverage, SE availability and acceptance limits |
| `outputs.json` | Schemas, row counts, sizes and hashes of the other ten files; excludes itself |

Only the three target tables use the exact ordered `target_contract.TARGET_SCHEMA`.
Reuse `TARGET_KEY_COLUMNS`, `validate_targets` and `write_targets(frame,
destination)` unchanged. The writer handles one sorted file in caller-owned
staging and returns its serialized inventory; the ACS bundle owns publication.

The auxiliary tables have versioned, fixed ordered schemas recorded in the
inventory. Their logical grains above and the following cross-table rules are
binding; planning specifies the concrete ordered columns/dtypes before tests:

- One support record per view/statistic key/annual component, plus explicitly
  typed denominator-status records where no point target can be emitted.
- Replicate records retain their view/statistic key and exact replicate number
  1..80; undefined estimates are nullable with nonnull status/reason. Defined
  estimates have a nonnull finite value and no undefined reason.
- Eligibility funnels have one disjoint first-exclusion partition that
  reconciles to source totals; separate evidence counts may overlap and are
  explicitly labeled. Never sum overlapping counts as disjoint exclusions.
- All auxiliary joins are bounded by declared natural keys; no unaccounted
  duplicate keys, nullable list containers or null candidate-list elements.
- Output evidence is aggregate. No person identifiers, source positions,
  household keys or microdata rows appear in the bundle audit tables.

### Unit and target metadata

Observed industry and occupation units use the existing generic feature-unit
syntax, with types `acs_industry_category` and `acs_occupation_category` and
stable identifiers derived from the Stage 8 `code_lookup_id`. These are
delivered categories, not fabricated canonical nodes. Their registry retains
every Stage 8 code lookup field, including source scheme and paired Census
code, source/token identity, candidates and aligned paths, special and aggregation
reasons/statuses, independent flags and reference locators.

Geographic units use the existing typed geography syntax, keyed by state,
area code and definition vintage. Types `residence_puma` and
`work_migration_puma` distinguish physical definitions; family direction and
role evidence distinguish workplace from migration use. County/MSA and
canonical classification units reuse selected Stage 4/5 node IDs exactly.

Freeze the target metadata registry in inputs:

- Source `acs`; families `staffing_pattern`, `area_mix`, `commuting_flow`,
  `migration_flow`; measures `annual_average_total`, `forward_share`.
- `universe` combines the base universe and evidence policy, for example
  `civilian_employed:strict` or `private_wage_salary:sensitivity`.
- `sample_set` explicitly identifies annual-core-2023-2024 or annual-2024,
  with the corresponding sample IDs and pooling divisor in its registry.
- `vintage` identifies the actual code and geographic definitions relevant
  to that view; the registry retains their separate frame fields.
- `flags` retain sorted, distinct provenance/limitations and never alone
  identify an evidence variant. TARGET_KEY_COLUMNS excludes flags.

A logical statistic key is the shared target key without `se_method`, plus
its view. Emit at most one SE method for each such statistic; undefined-SE
status cannot create competing target rows. Auxiliary records identify the
view explicitly because the same units can appear in separate target files.

### Commands and failure behavior

A standalone `python -m embedding_data.acs_targets` command group exposes
`build`, `verify` and `compare-runs`. Require explicit data root, mapping run
and detached mapping pin; verification requires the detached target inventory
pin. Do not register this group by changing the frozen top-level CLI.

Build/verify/comparison are offline, do not load environment files and do not
construct live IPUMS/geocoder clients. No upstream builder, acquisition,
conversion recovery, or automatic reference refresh prepares a run.

Reject unsafe run IDs, symlinks and occupied finals/partials. Publish from
exclusive caller-owned staging only after validation and fresh input/software
rechecks, using a no-replacement publication boundary. A failure leaves no
new final bundle; inspect occupied paths and use a fresh run ID. Cleanup may
remove only temporary files owned by the current execution.

Authenticate the external inventory pin before trusting any bundle content.
Logical comparison checks all eight ordered tables and substantive report
content, excluding only top-level run ID and creation time. It establishes
neither physical authentication nor byte equality of every serialized file.

## Verification and acceptance

The implementation plan must map each invariant to a check layer, fixture and
exact command before implementation. Hermetic tests join the normal pytest
suite; do not require production data or create a new marker/default-suite
exclusion. Actual full-data measurement is a separate explicit offline run.
No new dependency or test-configuration edit is needed for this design.

### Automated invariant strategy

| Invariant | Cheapest check layer / fixture |
| --- | --- |
| Ordered schema, unit membership, unique statistic keys and evidence metadata | Small table/serialization tests, including flags-only collision rejection |
| Eligibility by universe/family/evidence policy | Tiny hand-labeled source/DDI cases covering every required Q flag, NIU, edited, allocated and missing states |
| Correct periods and matched migration sensitivity | 2023 null-QMIGRAT1 and 2024 known-evidence cases, with independently specified expected products |
| Correct totals, ratios, pooling and all 80 SE contributions | Hand-calculated unequal annual populations, k=1/k=2, interior replicate changes and negative weights |
| Explicit undefined estimates | Zero full/replicate denominators, finite signed replicate ratios and missing-SE reason/replicate checks |
| No fan-out or false deduplication | Repeated identical source rows at distinct positions, ambiguous candidates and positive/zero geographic factors |
| Canonical projections preserve uncertainty and coverage | Scalar-versus-singleton cases, partial/crosswalk flags and unmapped 559830 |
| Area allocation conserves full and replicate mass | Small rational county factors, cross-state MSA, micro/no-CBSA residuals and all nine CT-region controls |
| Preservation and exclusive publication | Pin/file/rule mutation, manifest-prefix mutation, occupied paths, symlink and publication-race cases |
| Real raw-to-target V12 extension and replay | Synthetic manifested deliveries through real existing acquisition-free upstream builders/selectors/converter/mapping and all four family estimators |

Expected estimator values must be independently calculated, not generated by
the production estimator or its eligibility helpers. Small fixtures test
mathematical properties and contracts rather than internal call ordering.

Extend the authenticated Stage 8 V12 fixture and the Stage 6 raw-to-target seam
`tests.target_fixtures.run_ita_v12(data_dir, monkeypatch) -> Path` as applicable.
Run real conversion, Stage 4/5/7/8 selection and mapping, Stage 9 estimation,
manifests, replay and detached verification. No copied finished graph,
production microdata fixture or mocked selected-input object replaces this
chain. Block network, environment-file access and live client construction;
all actual external-access counters must be zero. Fixture success demonstrates
software readiness, not production scientific acceptance.

### Detached verification, full-data replay and independent reconciliation

Before completion, build fresh first/replay Stage 9 bundles from the selected
full core data. Capture each detached output pin independently; both public
verifiers must pass. Ordered values/schemas of all eight tables and substantive
reports must agree exactly after the stated run/time omission.

A separate full-data acceptance calculation reads selected source evidence
without production eligibility or estimation helpers. Authenticate metadata
and reference bytes, then independently reconcile:

1. Source counts, exact raw-to-companion weight alignment, all required flag
   domains/partitions, annual support and disjoint exclusion-funnel closure.
2. Both universes, all periods/evidence variants and every family denominator.
3. Native weighted totals from Decimal arithmetic, forward shares and every
   numbered replicate numerator, denominator, statistic and SE.
4. Canonical supported-leaf membership, retained provenance and coverage loss.
5. County allocation, metropolitan rollups and non-MSA mass for full and all
   replicate weights, including zero-factor and absent-MSA cases.
6. Undefined-point/SE reasons, affected replicate numbers and nonempty/empty
   product counts. Never omit failing cells or relabel an unavailable SE.

Schemas, identities, keys and counts are exact checks. Native sums must agree
in Decimal arithmetic before Float64 publication. For independent numerical
comparisons, shares use absolute tolerance 1e-12; allocated masses and SEs use
`abs(actual - expected) <= 1e-8 + 1e-12 * abs(expected)`. Freeze these bounds
before measurement. Failed checks require investigation, not wider tolerances.
Independent numerical tolerance does not relax exact logical replay.

Record actual source selection, pins, executing code/lock/dependencies,
independent calculation identity, all support distributions, excluded mass,
coverage, residuals and unavailable-SE partitions in a committed aggregate
finding. Published-reference comparisons must use matched universe/period
definitions and preserve gaps; never tune eligibility to make totals agree.

### Preservation and repository checks

Inventory selected upstream files and the existing raw-manifest prefix before
measurement; verify both afterwards. Keep manifest append accounting separate
from immutable file checks. No upstream rebuild, older seal/status rewrite or
new compatibility exception is part of Stage 9 acceptance.

Require full offline repository checks in the implementation worktree:

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked behave
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked ruff check .
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv lock --offline --check
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache UV_OFFLINE=1 uv run --offline --locked pre-commit run --all-files
```

The existing network canary remains deselected by the repository pytest
configuration. Tests always use temporary data roots and guarded metadata;
none may reach the real data tree or environment file. Retain normal commit
hooks. Require independent review of implementation and measured findings.

Stage 9 acceptance requires authenticated full-data first/replay bundles,
public verification, exact logical replay, independent reconciliation,
preservation, complete repository checks and recorded review. Document any
legitimate empty products and unavailable SEs explicitly; neither fixture
readiness nor a successful process exit alone accepts the science.

## Methodological sources and limits

The selected delivered DDI files and Stage 7/8 findings are frozen runtime
authority for labels, flag types and measured identities. The following public
primary documentation was checked during design on 2026-10-19:

- [IPUMS EMPSTAT](https://usa.ipums.org/usa-action/variables/EMPSTAT): civilian
  employment interpretation, current-job reference and ACS employment universe.
- [IPUMS CLASSWKR](https://usa.ipums.org/usa-action/variables/CLASSWKR): worker
  classes, including nonprofit and incorporated self-employment distinctions.
- [IPUMS TRANWORK](https://usa.ipums.org/usa-action/variables/TRANWORK): primary
  means of transportation and the last-week-worker universe.
- [IPUMS MIGRATE1](https://usa.ipums.org/usa-action/variables/MIGRATE1): domestic
  movement, same-house and unavailable migration distinctions.
- [IPUMS REPWTP](https://usa.ipums.org/usa-action/variables/REPWTP) and
  [replicate FAQ](https://usa.ipums.org/usa/repwt.shtml): all 80 weights, SDR
  variance estimation and legitimate negative replicate values.
- [2024 Census PUMS User Guide, section VII](https://www2.census.gov/programs-surveys/acs/tech_docs/pums/2024ACS_PUMS_User_Guide.pdf):
  recompute each statistic with each replicate and apply the 4/80 SDR factor.

These citations support their stated definitions and single-estimator SDR
calculation. The annual pooling rule remains the explicit chosen contract of
source-spec R3.7; no claim of independent validation of a different pooled
survey design follows. Runtime operation uses pinned local evidence, not live
pages. Mapping possibilities are not probabilities; allocated geography is not
individual location; source-evidence filtering does not remove survey bias.

## Rollout and later-stage handoff

Roadmap: specs/embedding-evaluation-data-spec-roadmap.md, Stage 9 — on plan completion, tick the stage and re-validate later stages against what shipped.

Keep this as one Stage 9 implementation cycle. The plan must preserve the
approved scope and selected upstream contracts, implement the automated test
strategy, and separate software readiness from full-data scientific acceptance.
Do not tick Stage 9 or retire this spec on design/planning completion.

The shipped Handoff must give exact schemas/APIs, pins, rules and limits for:

- Stage 12: reusable ACS universe/evidence, pooling, replicate and allocation
  helpers; no worker-profile estimator is supplied merely by having them.
- Stage 13: reusable estimation/uncertainty contracts while preserving the
  five-year weights, MULTYEAR recoding and vintage candidate provenance.
  Comparator targets, citations, V9 and full eight-family V12 remain there.
- Stages 10 and 11: preserved shared writer and upstream identities; no new
  ITA eligibility, CPS parser/linkage rule or source-scheme shortcut.

After this committed spec receives written-spec approval, use a fresh session
with writing-plans against `specs/acs-targets.md`. Carry the spec and roadmap
Stage 9 contracts forward; the brainstorming dialogue is not a dependency.
