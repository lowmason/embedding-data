# embedding-data

Evaluation data for embeddings of industries, occupations, and U.S. geography.
The project supports `naics-embedder` and planned SOC and geography embedders by
building aggregate measures of observed relationships: who industries employ,
where people work, and how workers move between jobs and places.

The [evaluation-data specification](specs/embedding-evaluation-data-spec.md)
defines the sources, samples, transformations, and planned outputs. Embedding
training and the protocol for scoring embeddings are separate from this project.

## Current state

The repository currently implements IPUMS ACS and CPS extract definitions,
submission, download, and CSV-to-Parquet conversion, run as the `acs` and `cps`
commands of the `embedding-data` Typer CLI. The `osha` command acquires
every OSHA ITA Form 300A summary file from 2016 on and stacks them into one
establishment-year table, and downloads the case-detail CSV and its dictionary.

The `codes` command builds NAICS 2022 and SOC 2018 classification graphs, full
NAICS concordances, candidate mappings and filing-universe diagnostics in a
separate immutable ITA bundle. The [measured V11 finding](specs/findings/v11-ita-naics-mapping.md)
records the full-data run and its unresolved source codes. Geography references and
the shared target writer are implemented. The [measured Stage 6 finding](specs/findings/stage-6-ita-area-mix-build.md)
records full-data ITA assignment, the 2023 area-mix target and exact cached replay.
Stage 8 ACS code parsing and PUMA allocation are measured and science-sealed;
the [Stage 8 finding](specs/findings/stage-8-acs-codes-area-allocation.md) records
the three profile companions in each of two full-data bundles, replay and independent
reconciliation. Repository completion is recorded in that finding, the
[retired plan](specs/plans/completed/8-acs-codes-area-allocation.md) and the
[roadmap](specs/embedding-evaluation-data-spec-roadmap.md). CPS code parsing,
person-month linkage and other target families remain planned. Raw downloads are
recorded in `data/raw/manifest.jsonl`.
The OSHA case-detail files are acquired but feed no target; the specification's
establishment data are the Form 300A summaries.

The five 2026-10-12 deliveries have now been measured in full, with exact ordered
CSV-to-Parquet parity and aggregate replay. The [Stage 7 finding](specs/findings/stage-7-ipums-extract-verification.md)
records sample/variable acceptance, literal CSV weight storage, the ASEC industry
scheme matrix, missing flag/metadata limits and published employment gaps.
Bundle integrity is verified; conservative machine interpretation fields remain
unresolved where the finding must supply external source review.

## IPUMS recovery and delivered-data verification

`--convert-only` recovers missing Parquets from complete, manifested deliveries
without loading credentials, contacting IPUMS or resubmitting extracts. Pass the
intended root explicitly, particularly in a worktree:

```sh
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data acs core --convert-only --data-dir /Users/lowell/Projects/embedding-data/data
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data cps monthly --convert-only --data-dir /Users/lowell/Projects/embedding-data/data
```

Select one or more existing sets. Omitting sets selects ACS `core`, or both CPS
sets (`monthly` and `asec`). To recover all ACS sets, explicitly pass
`core vintage five_year` before `--convert-only`.
Recovery preflights every selected raw triple and manifest identity before writing.
Existing final Parquets are retained; occupied `.part` paths and symlinks fail.
A unique decompression scratch directory and exclusive `.part` output precede
validated, no-replacement publication. Only owned scratch/partial files are cleaned
on failure. `--dry-run` and CPS `--start` cannot be combined with recovery.
Normal acquisition still submits a new immutable delivery. Recovery was fixture
tested; the Stage 7 production verification used all five existing Parquets.

Public references have a closed registry. Explicit acquisition/import is separate
from offline measurement:

```sh
uv run --locked embedding-data ipums acquire-references NEW_REFERENCE_ID --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked embedding-data ipums import-reference NEW_REFERENCE_ID KIND /path/to/exact-official-original --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked embedding-data ipums measure NEW_RUN_ID --references COMPLETE_REFERENCE_ID --selection /path/to/selection.json --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked embedding-data ipums verify NEW_RUN_ID --outputs-sha256 PRINTED_OUTPUTS_SHA256 --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked embedding-data ipums measure NEW_REPLAY_ID --references COMPLETE_REFERENCE_ID --selection /path/to/selection.json --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked embedding-data ipums compare-runs NEW_RUN_ID NEW_REPLAY_ID --data-dir /Users/lowell/Projects/embedding-data/data
```

The public command `acquire-references` verifies a complete cache without network;
missing originals require explicit acquisition. Only the two registered ACS1
queries use Census credentials (see Public ACS reference access). Other identities
are unauthenticated. The v3 registry contains 27 originals; the exact BLS POST body
is the 28th receipt input, and the generated receipt is the 29th separately
manifested file. Imports preserve original bytes and record local import time as
a retrieval-time proxy. Do not resave workbooks or import HTML challenge pages.

Selection JSON maps all five profile keys to `delivery` and root-relative `parquet`:
`{"acs/core":{"delivery":"usa_00001","parquet":"derived/acs/core/usa_00001.parquet"}}`
is one entry; measurement requires all five. The selected complete example is
`data/derived/ipums/stage7-selection.json`. The finding records both selected r2
runs and their actual detached pins. Verify each run with its own printed pin;
comparison alone does not establish external detached trust.

`measure` checks raw manifest provenance, full delivered schema/value parity,
required names, every numbered replicate, sample/flag coverage, exact decimal
weights, industry membership and published employment gaps. It writes eight
aggregate Parquets and four JSON files in a fresh immutable verification directory.
A full-file mismatch fails publication; failed measurement staging remains for
inspection. Occupied final/staging IDs require a fresh ID, never historical repair.
Changed relevant software or reference schema requires a new snapshot/run selection.
`verify` reports integrity separately from the measurement's `pass`, `fail` or
`unresolved` interpretation status. Do not translate unresolved metadata into success.

For these deliveries, use literal CSV weights without applying DDI decimal
exponents again. ASEC IND/INDLY use the verified 2022 industry scheme in both
2025 and 2026, with 9890 retained outside official lists and its 2026 meaning
unresolved. Raw short codes and Parquet zero-padding, unknown legacy API versions,
QMIGRAT1 gaps/types, guard NIU categories and missing linkage weights remain
explicit. The finding supplies source-backed interpretation; parsers, concordance
mapping, linkage rates, SEs, PUMA allocation and new targets remain later work.

## Classification references and canonical ITA bundles

Use the three registered commands with an explicit data root:

```bash
uv run --locked embedding-data codes acquire --data-dir /Users/lowell/Projects/embedding-data/data
uv run --locked embedding-data codes import-reference soc_2018 /path/to/soc_structure_2018.xlsx --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked embedding-data codes build NEW_RUN_ID --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked embedding-data audit --data-dir /Users/lowell/Projects/embedding-data/data
```

`acquire` verifies cached originals and downloads only missing references. Missing
BLS originals require `BLS_CONTACT_EMAIL` for the contact-bearing User-Agent.
If Census/BLS/GovInfo blocks access, save the complete official original from its
public download and use `import-reference KIND FILE`; preserve its bytes rather
than resaving a workbook or importing a challenge page. Imports record the official
URL, hash and local import time, flagged as a retrieval-time proxy. Reference
identities and expected counts are registered in `code_references.REGISTRY`.

`build` runs offline from manifested originals and the existing Stage 2 summary.
It refuses stale source/raw parity, malformed codes, corrupt or incomplete
references, and an occupied final or `.part` run name. Choose a fresh ID; never
replace an earlier bundle. Publication under `data/derived/codes/NEW_RUN_ID/`
follows validation in staging. Failed staging remains available for investigation.
Neither the source summary nor Stage 3 verification artifacts are rewritten.
In a restricted workspace prefix commands with
`UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache`; `--offline` prevents uv
resolution downloads and is appropriate once dependencies and originals exist.

The measured `stage4_v11_20261013_r2` bundle uses schema `codes-ita-v1` and retains
all 3,206,055 source rows and original columns, in source order. It remeasures
reviewed code `ccd138f` after a CLI workbook-error diagnostic fix; the earlier
`stage4_v11_20261013` bundle remains byte-identical. Its 69,035
unresolved rows remain explicit; 373 unknown-vintage rows have supported
candidate unions, which never assert a canonical scalar even when singleton.
Crosswalk flags persist for singleton mappings. Nullable filing flags retain
candidate disagreement; rule-reference ambiguity and legacy-label provenance
remain independent of the final outcome. Filing periods use the nominal year-plus-one
cycle because actual submission dates are unavailable. These diagnostics describe
the filing universe and do not establish that an observed filing was improper.

`inputs.json` pins raw/source/code/lock provenance and dependency versions;
`report.json` provides aggregate diagnostics and exact schemas; `outputs.json`
checksums all twelve Parquet tables and both other JSON files, excluding itself.
The [finding](specs/findings/v11-ita-naics-mapping.md) lists every filename,
checksum, mapping state and limitation. Relatedness remains observed: no targets
are inferred from classification edges, and this ITA source exception does not
relax ACS/CPS parsing or later headline-target inclusion requirements.

## Geography reference bundles

`geography acquire` verifies every registered destination before downloading missing
official Census originals. HUD 2025Q4 is imported separately when absent:

```bash
uv run embedding-data geography import-reference hud_2025q4 ZIP-COUNTY_122025.xlsx --data-dir data
uv run embedding-data geography acquire --data-dir data
uv run --offline --locked embedding-data geography build NEW_RUN_ID --data-dir data
```

Use the intended data root explicitly when running from a worktree. Existing originals,
final run names and `.part` names are immutable. Cached acquisition makes no HTTP request;
build is offline and refuses missing or changed manifested inputs. Changed original bytes
require a distinct source identity and recorded decision.

Each `derived/geography/<run_id>/` bundle contains six Parquets: `geography_nodes`,
`geography_edges`, `county_reference`, `cbsa_reference`, `hud_zip_county`, and
`hud_zip_lookup`, plus `inputs.json`, `report.json`, and detached `outputs.json`.
Select a complete run explicitly and verify its inventories; there is no latest alias.
The [production finding](specs/findings/stage-5-geography-reference-build.md) records
the selected run, original hashes, schemas, counts and limitations.

Administrative nodes use the 2025 frame. Both July 2023 metropolitan and micropolitan
CBSA memberships are present; counties outside all CBSAs remain in the county reference.
Administrative edges and county-to-CBSA edges are separate typed relationships. HUD
2025Q4 retains all candidates and ZIPs, including zero-business ZIPs. Only an original,
compatible positive singleton is eligible for fallback; a dominant share is diagnostic.
Missing ZIPs differ from present all-zero ZIPs. The Stage 6 commands below use these references for assignment; PUMA
allocation remains planned; these references do not assert historical address geography.

## ITA assignment and 2023 area-mix targets

The reviewed command surface separates offline preparation, explicit public Census
acquisition and offline target construction. Always name the real root in a worktree:

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data targets prepare-ita stage6_ita_assignment_20261014_1000_csv --codes-run stage4_v11_20261013_r2 --geography-run stage5_geography_20261014 --data-dir /Users/lowell/Projects/embedding-data/data
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data targets acquire-ita stage6_ita_assignment_20261014_1000_csv --data-dir /Users/lowell/Projects/embedding-data/data
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data targets build-ita stage6_ita_assignment_20261014_1000_csv stage6_ita_area_mix_20261014_1000_csv --year 2023 --data-dir /Users/lowell/Projects/embedding-data/data
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data targets build-ita stage6_ita_assignment_20261014_1000_csv stage6_ita_area_mix_20261014_1000_csv_replay --year 2023 --data-dir /Users/lowell/Projects/embedding-data/data
```

`uv --offline` prevents package fetching; `acquire-ita` still deliberately makes
Census HTTP calls. Preparation and build make no downloads and use no credentials.
One preparation freezes the full 2016–2025 source-row index, distinct submitted
address requests and software inventories under
`derived/osha/assignment-inputs/<assignment_run_id>/`. Acquisition is sequential,
with the existing 600-second client timeout. It stores catalogs, raw responses and
receipts under `raw/references/census-geocoder/ita-assignment/<assignment_run_id>/`.
After a transport or validation failure, inspect the failure and explicitly rerun
the same acquisition command to resume from verified completed batches. Do not
alter requests, substitute frames or add blind retries. Changed preparation or
assignment software/dependencies require a new preparation selection.

Stage 6 preparation partitions requests into batches of at most 1,000 records;
Stage 3's default and the Census service maximum remain 10,000. Execution correction
D5 adds backslash escaping to Stage 6's headerless UTF-8 CSV while retaining doubled
quotes and field order (ID, street, city, state, ZIP). Logical submitted strings,
request IDs and source-row mappings are unchanged. The wire bytes double literal
backslashes; requests without them remain byte-identical. The measured prior request
inventory contains 42 literal backslashes across 29 batches.

The selected production run uses the fresh `_1000_csv` preparation above.
These are the commands that produced it; the existing immutable run names must not
be overwritten or rerun as new preparations. Preserve both
`stage6_ita_assignment_20261014` and
`stage6_ita_assignment_20261014_1000`, including the latter's 283 completed raw batches,
with their original software and bytes. Never edit or reinterpret those frozen runs,
or import cached or diagnostic responses into the new acquisition. The measured
1,113,538 distinct requests produced 1,114 completed fresh batches (1,113 of 1,000
plus 538); these are batch counts, not total HTTP calls. Sequential execution,
Current options, the 600-second timeout and explicit verified resume are unchanged.
The [measured finding](specs/findings/stage-6-ita-area-mix-build.md) records the exact
preparation/first/replay detached pins, source and software inventories, 3,206,055
preserved source rows, 126,958 target cells and 324,191 eligible 2023 records.
Both public verifiers and exact ordered four-table replay passed; the 3,069 county
denominators include four zero-eligible counties with no target cells. Final
repository checks and reviews are tracked separately in that finding.

Run IDs are immutable: occupied final or `.part` names fail. Inspect interrupted
staging and choose an explicit fresh ID; never overwrite an existing run. Selected
upstream runs have pinned detached `outputs.json` hashes. Alternate upstream runs
require `--codes-outputs-sha256 SHA256` and/or
`--geography-outputs-sha256 SHA256` on `prepare-ita`, paired with their explicit
`--codes-run` and `--geography-run` IDs. Never rebuild the source summary, run
verification `sample`, or change earlier bundles to prepare these commands.

Each target bundle under `derived/targets/<target_run_id>/` has exactly seven files:
`ita_county_assignments.parquet`, `ita_area_mix.parquet`,
`county_denominators.parquet`, `target_flag_counts.parquet`, `inputs.json`,
`report.json` and `outputs.json`. Assignments preserve the 38 canonical columns,
source order and every submitted record, including duplicates and repeated IDs.
The unique grain is `source_row`; an ID is not a confirmed unique establishment.
The common administrative county frame is 2025; CBSA membership is July 2023,
HUD is 2025Q4, and Census Current address data remain mutable across batches.
These frames do not reconstruct historical geography.

Only `--year 2023` is supported for targets. Each eligible submitted record counts
one, using a valid native six-digit NAICS 2022 industry and an adopted compatible
county assignment. Census exact assignment takes precedence; compatible HUD
original positive singletons are allowed and flagged. Crosswalked, unresolved or
ambiguous industry values and unassigned geography are excluded. Employment,
hours and nullable filing-rule flags remain diagnostics, never target filters.

The 16-column `targets-v1` schema carries typed county/industry units, metadata,
`value`, null `se`, `se_method='none'`, support counts and sorted flags. Observed
cell shares divide eligible cell counts by eligible county counts; no synthetic
zero cells or minimum count gate is applied. `n_unweighted` and `n_weighted` are
cell supports. County denominators retain assigned, eligible and excluded-industry
counts, including counties with zero eligible records. Flag counts record positive
true/null support for each numerator and denominator; labels such as
`numerator:flag_assignment_hud:true` indicate some support, not that all records
carry the flag. Every target has `size_gate_pending`; V9 remains pending.

This is conditional on a program-selected filing universe with unvalidated
reported employment and preserved duplicate multiplicity. Coverage establishes
neither county accuracy nor representativeness of all establishments. Inputs and
reports record citations, hashes, versions and disjoint coverage alongside
overlapping diagnostics. `outputs.json` hashes the other six files; its checksum
is detached. Cached replay must match ordered logical rows and canonical JSON
apart from documented run IDs, creation times and consequential inventories.
Physical Parquet hashes describe each particular serialization.

## Data sources

| Source | Samples or coverage | Purpose |
| --- | --- | --- |
| [OSHA Injury Tracking Application](https://www.osha.gov/itadata), Form 300A summaries | 2016–2025 | Establishment employment, hours, location, NAICS codes, employer descriptions, and firm structure |
| IPUMS USA / ACS | 2023–2024 core; optional 2022 comparator and 2020–2024 five-year sample | Staffing patterns, worker profiles, area mixes, commuting, and migration |
| IPUMS CPS | Monthly samples from January 2025; ASEC samples from 2025 | Job transitions, earnings profiles, and state migration |

OSHA ITA is a program-selected set of establishments. Targets built from it must
describe that filing universe rather than claim to represent every establishment.
Actual CPS sample availability comes from the IPUMS catalog at runtime.

## Setup

Install [uv](https://docs.astral.sh/uv/) and use Python **3.14 or later** for the
project environment. Run commands from the repository root:

```bash
uv sync --locked
```

The repository's `.python-version` selects Python 3.14 for this environment.

The main libraries are `ipumspy` for IPUMS requests, `httpx` (with HTTP/2) for
OSHA downloads, Polars for conversion, Typer for the CLI, and `python-dotenv` for
credential loading.

Register for both IPUMS USA and IPUMS CPS, then create an
[IPUMS API key](https://account.ipums.org/api_keys). The same key is used for
both collections once the account has access to them.

Create `.env` at the repository root, for example
`~/Projects/embedding-data/.env`:

```dotenv
IPUMS_API_KEY=your-api-key
```

Use the root `.env`, even if another `.env` exists under `src/embedding_data/`.
Both commands load the root file with `python-dotenv`; an exported
`IPUMS_API_KEY` takes precedence.

## Public ACS reference access

Stage 7's two public aggregate queries need a Census API key, separate from the
IPUMS key. Use the [official Census key registration page](https://api.census.gov/data/key_signup.html)
and follow the activation instructions sent by Census. Keep the value out of
chat, shell command arguments, shell history and saved command output.

After the D3 security review, run the public-original preflight in a local
terminal. An existing local `.env` containing `CENSUS_API_KEY` can be supplied
explicitly; this helper reads only that field with interpolation disabled and
never modifies or copies the file. An exported `CENSUS_API_KEY` takes precedence.
There is no automatic root `.env` discovery. Use a fresh private temporary output
directory; the directory must not exist yet and its parent must already exist:

```sh
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked \
  python -m embedding_data.ipums_census_access \
  --env-file /Users/lowell/Projects/embedding-data/.env \
  --output-dir /private/tmp/stage7-acs-originals-review
```

Alternatively, replace `--env-file ...` with `--prompt` to enter the key through
hidden terminal input. If hidden input is unavailable or cancelled, the command
fails without accepting echoed input. Do not supply a key value as an argument.

This explicit command makes exactly the registered 2023 and 2024 ACS1
`NAME,B23025_004E` / `state:*` requests. It saves the unmodified response bytes
and credential-free URL, hash, size and retrieval time in the new directory.
It prints only output paths and public-original hashes. Redirects are refused;
a response echoing the credential is rejected before its bytes are written.
An interrupted output directory remains occupied: inspect it and choose a fresh
path for another attempt. A preflight download provides evidence for actual
layout inspection; full-registry reference readiness and production acceptance
remain separate gates. ACS level parsing now validates the inspected official
response layout; the selected complete v3 snapshot and actual delivery verification are now
recorded in the [Stage 7 finding](specs/findings/stage-7-ipums-extract-verification.md).

Normal explicit reference acquisition accepts the same existing local file via
`ipums acquire-references REFERENCE_ID --census-env-file /path/to/existing.env`
(or `acquire(data_dir, reference_id, census_env_file=Path(...))`). Only uncached
acquisition of the two ACS query identities resolves Census credentials.
Imports, cached checks, offline measurement and module imports never read that
file or the Census environment key. Other public references remain unauthenticated.
`uv --offline` controls dependency fetching; the explicit preflight still makes
HTTP requests.

## ITA verification commands

Audit the raw manifest without changing files:

```sh
uv run embedding-data audit --data-dir data
```

`audit` is read-only and exits 1 on a discrepancy. The manifest's `entry_for`
verifies file bytes against recorded hashes; `recorded_entry_for` only looks up
records for restoration and existence diagnostics.

Run the separate verification module with an explicit data directory:

```sh
uv run python -m embedding_data.ita_verification_run references --data-dir data
uv run python -m embedding_data.ita_verification_run import-hud /path/ZIP-COUNTY.xlsx 2025Q4 --data-dir data
uv run python -m embedding_data.ita_verification_run sample data/raw/references/hud/2025Q4/ZIP-COUNTY.xlsx run-1 --data-dir data
uv run python -m embedding_data.ita_verification_run geocode run-1 --data-dir data
uv run python -m embedding_data.ita_verification_run measure run-1 --data-dir data
```

`references` and `geocode` acquire public data. `import-hud` copies a manually
downloaded official HUD ZIP-to-county workbook into immutable raw references;
its `retrieved_at` is the local import time, flagged as a proxy, rather than the
original browser download time. `sample` and `measure` run offline. `sample`
rebuilds the source table once using the Stage 2 source/hash contract and records
raw provenance, sample/table/request hashes, dependency versions, and code hashes.
`measure` never rebuilds the table or recontacts Census; changed sample, table,
or request bytes fail, as do changed code or dependencies.

Each run lives in `derived/osha/verification/<run_id>/`, containing
`sample.parquet`, headerless batch `requests/*.csv`, `inputs.json`,
`geocoding.json`, `reports.json`, V1 and quality Parquets by year, V2 JSON,
V3 strata Parquet, and `finding.md`. Census catalogs and batch responses remain
under `raw/references/`, covered by the raw manifest. Current Census address data
can change between batches or resumed acquisitions; recorded catalogs identify
request options rather than a frozen address-source snapshot. Reports are
measurements, not target tables; fixture results do not establish benchmarks or
adopt verification decisions.

The owner adopted the actual [V1–V3 finding](specs/findings/v1-v3-ita-verification.md)
on 2026-10-13. Matching preserves delivered text and uses NFKC, Unicode casefold
and collapsed whitespace, with exact placeholder/title flags and explicit employer
fallback/reconstructed-EIN flags. Establishment IDs are candidates in every year;
confirmation requires unique IDs, the same usable unreconstructed EIN and complete
normalized address. County assignment uses an exact cached Census match in ACS2025
first, then a compatible HUD county only when exactly one has positive business
share (reviewed reference: 2025Q4). Assignment checks the chosen returned county
and excludes territory prefixes 60/66/69/72/74/78 as well as excluded delivered
states; comparison checks both returned counties. Scope diagnostics remain
separate from coverage. The corrected evidence run is `v1_v3_20261013_scopefix`,
replaying the original cached responses with their original receipts.
Ambiguous, unmatched, scope and vintage results
remain flagged. The finding reports raw and weighted sample evidence, not county
accuracy or a full-table assignment. The separate [Stage 6 production finding](specs/findings/stage-6-ita-area-mix-build.md)
records the later full-table assignment and conditional 2023 target.

## ACS extracts

| Name | IPUMS sample IDs | Use |
| --- | --- | --- |
| `core` | `us2023a`, `us2024a` | Default, pooled 2023–2024 ACS |
| `vintage` | `us2022a` | Optional industry-classification vintage comparator |
| `five_year` | `us2024c` | Larger 2020–2024 sample; this sample ID still needs live confirmation |

All extracts select employed persons using general `EMPSTAT` code 1, request
data-quality flags, and include the inflation-adjusted wage
`INCWAGE_CPIU_2010`. The general employed category includes armed forces;
the civilian-only universe described in the specification requires a later
filter. The five-year extract additionally requests `MULTYEAR`.

Write definitions without credentials or a network request:

```bash
uv run embedding-data acs core --dry-run
```

Submit the core extract, wait for completion, download it, and convert it:

```bash
uv run embedding-data acs core
```

Request all three sets:

```bash
uv run embedding-data acs core vintage five_year
```

A dry run writes each definition to `data/preview/acs/<set>/extract.json` and
touches nothing under `data/raw`. A real run gives each extract its own
directory, `data/raw/acs/<set>/usa_<number>/`, holding the submitted
`extract.json`, the delivered `.csv.gz` data and the `.xml` DDI codebook. It
records each file's SHA-256, extract number, sample IDs, retrieval time and
ipumspy version in `data/raw/manifest.jsonl`, and writes the converted Parquet
to `data/derived/acs/<set>/usa_<number>.parquet`. A re-run submits a new
extract into a new directory, so an earlier delivery is never overwritten or
reconverted. `--data-dir PATH` moves the whole data root (default
`<project-root>/data`). Conversion preserves `INDNAICS` and `OCCSOC` as
strings, including aggregated codes such as `31M` and `1110XX`.

## CPS extracts

| Name | Selection | Universe |
| --- | --- | --- |
| `monthly` | Catalog samples from `--start`, default and earliest `2025-01` (an earlier start is refused); excludes ASEC and prefers a basic sample when both variants exist | Labor-force members, `LABFORCE` = 2 |
| `asec` | ASEC catalog samples from 2025 onward; unaffected by `--start` | All persons |

With no extract names, both sets are requested. CPS dry runs **require the API
key and network access** because they retrieve the sample catalog; they write
definitions without submitting extracts.

```bash
# Inspect the CLI without contacting IPUMS.
uv run embedding-data cps --help

# Retrieve the catalog and write definitions for monthly and ASEC.
uv run embedding-data cps --dry-run

# Preview only monthly samples from August 2026 onward.
uv run embedding-data cps monthly --start 2026-08 --dry-run

# Submit, wait, download, and convert both sets.
uv run embedding-data cps

# Download only monthly samples from August 2026 onward.
uv run embedding-data cps monthly --start 2026-08
```

Files follow the ACS layout. Dry-run definitions go to
`data/preview/cps/<set>/extract.json`. Each delivered extract gets its own
`data/raw/cps/<set>/cps_<number>/` and is recorded in `data/raw/manifest.jsonl`,
and Parquet goes to `data/derived/cps/<set>/`. `--data-dir PATH` moves the whole
data root. CPS stores industry and occupation as Census codes; conversion pads
`IND`, `OCC`, `INDLY`, and `OCCLY` to four-character strings. Mapping them to
NAICS and SOC remains a later step.

## OSHA Form 300A summaries

`uv run embedding-data osha summary` reads the [ITA data page](https://www.osha.gov/itadata)
and downloads every file it lists as `<year> Summary Data` from 2016 on, plus the two
summary data dictionaries, over HTTP/2:

| Path | Contents |
| --- | --- |
| `raw/osha/summary/<year>/<OSHA's file name>` | That year's summary file as delivered: a zip holding one CSV through 2024, a CSV for the current year |
| `raw/osha/summary/summary_data_dictionary.pdf`, `ITA_Data_Dictionary.pdf` | OSHA's field definitions (2024 on; 2016–2023) |
| `derived/osha/ita_300a_summary.parquet` | One row per establishment-year, all years stacked |

The current year's file name carries its submission through-date
(`..._2025_through_08-31-2026.csv`). OSHA renames the file as it grows, so a later
release is downloaded beside the earlier one and recorded as a new manifest entry with
its `through_date`; the earlier file and entry are untouched. The run refuses a page
that lists a year twice, skips a year, names a through-date that is not a real date, or
gives the current year's file no through-date; a summary file found on disk but missing
from the manifest; and, before downloading anything, a year whose files would leave no
single latest release (an undated file beside another, or two with one through-date). A
file OSHA replaces under an unchanged name is not detected.

The table is rebuilt on every run from each year's latest release. It keeps the
specification's R2.4 columns plus OSHA's record `id`, the raw file it came from
(`source_file`, the manifest path), and these harmonized columns:

- `size_class`: the split of size code `2` (20–249 employees) into `21` and `22` is
  documented from the 2023 data, but the 2022 file already carries 227 rows of `21` and
  65 of `22`, and later files still use `2` for some establishments. `size` keeps the
  native code; `size_class` merges `21` and `22` back into `2`.
- `naics_year`: files before 2023 lack it; OSHA's dictionary says those years use 2012
  NAICS, so they get 2012 with `naics_year_from_dictionary` set. A delivered vintage
  other than 2012, 2017, or 2022 (the 2024 file carries `0`, the 2025 file `0` and
  `2025`) becomes null; the code is kept.
- `flag_employment`, `flag_hours_per_employee` (outside 500–4,000 hours per average
  employee), and `flag_below_filing_size` (under 20 employees). Flagged rows are kept.
  `flag_naics_year_unknown` marks a NAICS code left without a vintage; it records
  provenance, not implausibility.

Codes, names, addresses, ZIP codes, and EINs stay as delivered, except that an
`establishment_type` with no digit (one 2019 row holds an industry title) becomes null
and `total_hours_worked` in scientific notation (four rows in the 2024 and 2025 files,
such as `8.62847E+11`) is read as the whole number it spells. A file the harmonization
does not cover stops the build rather than being guessed at, as does a raw file whose
SHA-256 differs from its manifest entry. After the build the command prints rows per
year beside OSHA's published submission counts. A full first run downloads about 258 MB.

## OSHA case-detail download

`uv run embedding-data osha case-detail` needs no account or key. It downloads two files from osha.gov
over HTTP/2 into `data/raw/osha/`, records each in `data/raw/manifest.jsonl`
with its URL, retrieval time, SHA-256, and `httpx` version, and converts the CSV
to Parquet in `data/derived/osha/`:

| File | Contents |
| --- | --- |
| `raw/osha/ITA_Case_Detail_Data_2025_through_08-31-2026.csv` | One row per recordable injury or illness filed for 2025 (`year_of_filing`) and submitted through 2026-08-31; some incident dates fall in 2024 |
| `raw/osha/case_detail_data_dictionary_2026.pdf` | OSHA's field definitions for the CSV |
| `derived/osha/ITA_Case_Detail_Data_2025_through_08-31-2026.parquet` | The CSV with typed columns |

```bash
uv run embedding-data osha case-detail
uv run embedding-data osha case-detail --data-dir /tmp/osha-data
```

A raw file that already exists is kept as delivered and not downloaded again,
and one missing from the manifest is reported on stderr, not recorded. A raw
file that is absent but still recorded in the manifest is not downloaded again
either: the command exits with an error, before any request, so the original
can be restored.
The Parquet is built only when it is absent; delete it to rebuild.
Downloads are written to a `.part` file and renamed only when complete.
osha.gov refuses non-browser user agents with HTTP 403, so the command sends a
browser `User-Agent`.

The CSV mixes encodings: most non-ASCII text is Windows-1252, and a few rows are
UTF-8. Conversion decodes both into UTF-8 Parquet. Code columns (`zip_code`,
`ein`, `naics_code`, `SOC_code`, `case_number`) stay strings even where the
dictionary calls them numeric. `zip_code` arrives without leading zeros (for
example `2134`); conversion does not restore them. Counts become `Int64`, the
three date columns `Date`, and the two time columns `Time`. A value that does not
parse stops the conversion.

These are case-detail records from Forms 300 and 301; they feed no target. The delivered file
differs from its dictionary: the dictionary lists `created_timestamp` and the
OIICS `*_pred` columns, while the CSV has `date_submitted` and no OIICS columns;
unassigned SOC codes read `00-9900` rather than `00-9999`; and
`Unexpected_NAICS_SOC_Combo` also takes the value `Y?`.

## Files and planned outputs

All commands share one data root, `data/` by default (`--data-dir`):

| Path | Contents |
| --- | --- |
| `raw/manifest.jsonl` | One JSON line per raw file: path, SHA-256, size, retrieval time, client and version, and either the source URL or the IPUMS collection, extract number, and sample IDs |
| `raw/acs/<set>/usa_<number>/`, `raw/cps/<set>/cps_<number>/` | One delivered IPUMS extract: the submitted `extract.json`, the `.csv.gz` data, and the `.xml` DDI codebook |
| `raw/osha/` | OSHA downloads as delivered; summaries under `raw/osha/summary/<year>/` |
| `derived/<source>/` | Parquet converted from raw files |
| `preview/<source>/<set>/extract.json` | Dry-run definitions, overwritten by the next dry run |

Raw files are never edited, overwritten, or re-downloaded, and each path is
recorded once. Files delivered before the manifest existed were moved into this
layout by `uv run --locked python -m embedding_data.raw_backfill`. Their entries
use the file modification time and the `uv.lock` client version, both flagged in
`proxies`. An IPUMS delivery is staged in `<set>/<name>.part/` and renamed to
`<set>/<name>/` only when its `extract.json`, `.csv.gz` and `.xml` are all
there, so a `.part` directory is an interrupted delivery: it is not recorded
and is not a delivery. Only those three files are recorded; anything else in
the directory is not. Downloads are not resumable: re-running an IPUMS command
submits a new extract.

The specification calls for aggregate Parquet targets covering staffing
patterns, area mixes, worker profiles, job-change flows, commuting, migration,
employer text–code pairs, and industry co-ownership. It also calls for NAICS
2022 and SOC 2018 mappings, typed geography edges, allocation flags, uncertainty
estimates, cell counts, and input hashes. The ITA area-mix command is implemented;
production acceptance is recorded separately. The other families remain planned.

Benchmark data stay separate from embedder training and model selection.
IPUMS microdata remain local and must not be committed or redistributed as
project outputs. Share aggregate targets and cite the collections under the
[IPUMS USA terms](https://usa.ipums.org/usa/terms.shtml) and
[IPUMS CPS terms](https://cps.ipums.org/cps/terms.shtml). `.env` and `data/` are
ignored by Git.
The specification permits establishment-level rows in ITA-derived outputs.

## Checks

`uv sync --locked` installs the development dependencies, including
[Hypothesis](https://hypothesis.readthedocs.io/en/latest/quickstart.html) for
generated-input property tests and
[Behave](https://behave.readthedocs.io/en/stable/tutorial/) for Given/When/Then
acceptance scenarios. The unit and property tests use
[pytest](https://docs.pytest.org/en/stable/).

Run the CPS fixture and property tests without network access or real credentials:

```bash
uv run --locked pytest tests/test_cps_benchmark_extract.py tests/test_cps_properties.py -v
```

Run the Behave scenarios for default and monthly-only CPS dry-runs:

```bash
uv run --locked behave
```

Run the full suite and check the project lockfile:

```bash
uv run --locked pytest
uv lock --check
```

Install the [pre-commit](https://pre-commit.com/) hooks once per clone. They
check whitespace and file syntax, run [Ruff](https://docs.astral.sh/ruff/) with
autofix, and run the pytest suite under coverage before each commit:

```bash
uv run --locked pre-commit install
uv run --locked pre-commit run --all-files
```

The CPS checks cover CLI defaults, credential loading, catalog selection,
dry-run behavior, and Parquet conversion. The property tests generate valid
months and sample catalogs to check date boundaries, chronological ordering,
basic-sample preference, and the ASEC year cutoff. Behave runs the real CLI
against a fixture catalog and temporary output files, replacing the IPUMS client
so it cannot make live requests. The starter test strategy is recorded in
[specs/cps-test-strategy.md](specs/cps-test-strategy.md).

The ACS tests cover the same CLI defaults, credential loading, offline dry
runs, and conversion. Fixture checks do not confirm live IPUMS variable
acceptance or survey totals.

## Project layout

```text
specs/embedding-evaluation-data-spec.md      Full data requirements and verification tasks
src/embedding_data/acs_benchmark_extract.py  ACS extract definitions and downloader
src/embedding_data/cps_benchmark_extract.py  CPS catalog selection and downloader
src/embedding_data/osha_benchmark_download.py The osha command: Form 300A and case-detail downloads
src/embedding_data/ita_catalog.py            Form 300A releases listed on the ITA data page
src/embedding_data/ita_summary.py            Stacked, harmonized, flagged Form 300A table
src/embedding_data/osha_encoding.py          Mixed UTF-8 / Windows-1252 line decoding
src/embedding_data/cli.py                    embedding-data console entry point
src/embedding_data/paths.py                  Data root layout: raw/, derived/, preview/
src/embedding_data/manifest.py               Append-only raw-file manifest (SHA-256 and provenance)
src/embedding_data/ipums_delivery.py         Shared IPUMS preview, submission, download, and recording
src/embedding_data/raw_backfill.py           One-off migration of pre-manifest raw files
tests/                                       Offline unit, property, and conversion checks
features/                                    Behave CPS dry-run acceptance scenarios
data/raw/                                    Raw downloads as delivered, and manifest.jsonl
data/derived/                                Parquet converted from raw files
data/preview/                                Dry-run extract definitions
pyproject.toml                               Project dependencies and Python requirement
uv.lock                                      Project dependency lockfile
```


### ACS classification and population allocation (Stage 8 software)

The separate module commands use explicit run IDs, an explicit local data root and
external control pins. They consume selected Stage 4, 5 and 7 bundles in place.
Only `acquire-references` retrieves public originals; `import-reference` registers
local public original bytes. A complete cached reference snapshot is checked without
constructing an HTTP client. Build, verification and comparison are offline; none
loads `.env`, requests credentials or constructs an IPUMS API client.

```bash
uv run --offline --locked python -m embedding_data.acs_mapping acquire-references REFERENCE_ID --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked python -m embedding_data.acs_mapping import-reference REFERENCE_ID KIND ORIGINAL --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked python -m embedding_data.acs_mapping build RUN_ID --references REFERENCE_ID --references-sha256 RECEIPT_PIN --codes-run CODES_ID --codes-outputs-sha256 CODES_PIN --geography-run GEOGRAPHY_ID --geography-outputs-sha256 GEOGRAPHY_PIN --ipums-run IPUMS_ID --ipums-outputs-sha256 IPUMS_PIN --ipums-references-sha256 IPUMS_RECEIPT_PIN --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked python -m embedding_data.acs_mapping verify RUN_ID --outputs-sha256 EXTERNAL_PIN --data-dir /Users/lowell/Projects/embedding-data/data
uv run --offline --locked python -m embedding_data.acs_mapping compare-runs FIRST_ID SECOND_ID --data-dir /Users/lowell/Projects/embedding-data/data
```

Uppercase tokens are required explicit selections for a new run. `uv --offline`
restricts package fetching; the acquisition command itself can
retrieve public references. Reference receipts and upstream `outputs.json` files need
independently captured pins. Build emits JSON with `run_id`, `directory` and
`outputs_sha256`; save this response outside the bundle in a gitignored control
receipt. Verification requires that external output pin before trusting local records.
Owner decision D5 preserves the selected historical Stage 5 creator CLI record only
for `stage5_geography_20261014` and its exact approved detached output pin. The
current CLI hash must also agree with strictly verified Stage 7 and frozen
Stage 8 executing software. The original upstream inventory
is retained with explicit compatibility diagnostics; every other software,
dependency, Python/lock, source/reference and table check stays strict.
Comparison checks ordered logical contents of all eight tables and substantive report
content; it does not establish trust. Verify both runs separately before adopting a
replay. Exit codes are 0 for success, 1 for logical mismatch and 2 for validation or
acquisition failure, with metadata-only error output.

Each run under `data/derived/acs/mapping/RUN_ID/` has eight Parquets plus
`inputs.json`, `report.json` and `outputs.json`. The inventory covers the other ten
files. The three companions preserve original columns, strings, delivery-specific
Q flags, types, duplicate multiplicity and person row order, followed by a typed
annotation suffix. Reference tables retain sorted distinct unweighted classification
possibilities, root-to-leaf candidate paths and cited geography statuses. Factors use
2020 population and PUMA definitions, 2022 county composition, the 2025 county inventory
and July 2023 MSA delineations as separate frames. Geographic allocation and fractional
splits remain explicit; allocation does not infer an individual's county or MSA.

Existing final or `.part` names are refused. Inspect caller-owned interrupted paths
and choose a fresh explicit run ID; do not overwrite an earlier bundle or repair it
in place. Failed builds clean only their owned staging. The public verifier reconstructs
mappings, factors and all companion annotations from pinned originals and selected
sources, and checks current executing software and dependencies.

Fixture software readiness is separate from Stage 8 full-data science. The
raw-to-converter-to-authenticated-upstreams fixture exercises replay, preservation and
integrity gates; it does not establish V9 or complete eight-family V12 acceptance.
The selected full-data runs are `stage8_acs_mapping_20261018_r7` and
`stage8_acs_mapping_20261018_r7_replay`, under control
`stage8_acceptance_20261018_r7`. Their external `outputs.json` pins are
`1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4`
and `a115c5f7e2691ecbffe763bd1b6b9780fb6a71bc512a2691cf4014f9857b3565`.
At executing source `1542f8d8f1db2e55f28b9cfec4b1306739589ce8`, both detached
verifiers, eight-table/report replay and both full independent reconciliations passed
for 12,238,491 source rows. The immutable external science seal is
`b09d1a56308f09d6e99f97070c02ffbbc0523d6c595f7901bb0e01a999bd3ddf`;
its 880-file control inventory has SHA-256
`7af71e3b57c6c07867224259f49563c20e0cd3b75e1d99f54b4cea4f92cc221a`.
The [measured Stage 8 finding](specs/findings/stage-8-acs-codes-area-allocation.md)
keeps the first-build timing-wrapper limit and distinguishes the immutable
seal's historical `adoption=false` from completed repository adoption. Mapping
outputs are evaluation inputs, never embedder training or model-selection data.
Stage 9 now provides the offline target software described below; its full-data
measurement and scientific acceptance remain later-stage work.

### ACS target families (Stage 9 software)

The standalone `python -m embedding_data.acs_targets` module has exactly `build`,
`verify` and `compare-runs`. All run offline against an explicit `--data-dir`; they
consume authenticated Stage 8 mapping and Stage 4/5/7 selections in place. They do
not acquire data, load environment files, rebuild upstreams or refresh selections.
Stage 9 software readiness uses a tiny synthetic manifested raw CSV/DDI chain,
unchanged conversion and real builders/selectors through four ACS families plus
independent detached verification and exact replay. Full-data measurement, independent
reconciliation, science acceptance and roadmap completion remain pending. Fixtures
are software checks, never scientific acceptance or microdata publications.

The explicit selected upstream identities are:

| Selection | Run | External SHA-256 |
| --- | --- | --- |
| Mapping | `stage8_acs_mapping_20261018_r7` | `1ec9701092f576b122b01464cdb6fa3fbee49db030e4ad3df7b64e621b8e75f4` |
| Codes | `stage4_v11_20261013_r2` | `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |
| Geography | `stage5_geography_20261014` | `5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d` |
| IPUMS verification | `stage7_ipums_verification_20261015_r2` | `db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc` |
| IPUMS reference receipt | `stage7_ipums_references_20261015_r2` | `3163968dde603ba53f807976dd09b9e40d73235a98c6f36e4e02c67ec4239c9c` |

These commands describe the software interface; production execution belongs to the
later full-data checkpoint. Substitute the recorded identities above for uppercase
upstream tokens, fresh explicit target IDs, and independently saved target pins:

```bash
uv run --offline --locked python -m embedding_data.acs_targets build RUN_ID --data-dir /Users/lowell/Projects/embedding-data/data --mapping-run MAPPING_ID --mapping-outputs-sha256 MAPPING_PIN --codes-run CODES_ID --codes-outputs-sha256 CODES_PIN --geography-run GEOGRAPHY_ID --geography-outputs-sha256 GEOGRAPHY_PIN --ipums-run IPUMS_ID --ipums-outputs-sha256 IPUMS_PIN --ipums-references-sha256 IPUMS_RECEIPT_PIN
uv run --offline --locked python -m embedding_data.acs_targets verify RUN_ID --data-dir /Users/lowell/Projects/embedding-data/data --mapping-run MAPPING_ID --mapping-outputs-sha256 MAPPING_PIN --outputs-sha256 TARGET_EXTERNAL_PIN
uv run --offline --locked python -m embedding_data.acs_targets compare-runs FIRST_ID SECOND_ID --data-dir /Users/lowell/Projects/embedding-data/data --mapping-run MAPPING_ID --mapping-outputs-sha256 MAPPING_PIN
```

Build emits aggregate success JSON with the detached `outputs_sha256`; save it outside
the bundle. Verify authenticates that external target inventory pin before trusting
bundle content and rederives all eight ordered tables. Compare checks exact ordered
logical tables and substantive reports, excluding only top-level run ID/time; it does
not establish trust. Verify both runs with their own detached pins first. Success
exits 0, unequal comparison exits 1 and validation failure exits 2 with the fixed
`ACS target validation failed.` diagnostic. No exception row values are printed.

Each fresh `data/derived/acs/targets/RUN_ID/` contains eight Parquets:
`targets_observed`, `targets_canonical`, `targets_allocated_area_mix`, `target_units`,
`target_support`, `replicate_estimates`, `eligibility_diagnostics` and
`allocation_residuals`, plus `inputs.json`, `report.json` and `outputs.json`. Only the
first three use the unchanged ordered `targets-v1` contract. Evidence is aggregate;
person/household identifiers and source-position audit rows are never published.
Occupied final/partial names, symlinks, unsafe IDs, mixed selections, stale executing
software, unpinned inputs and changed sources are refused. Failed builds publish no
new final and clean only their exclusively owned temporary paths.

Native observed products retain delivered categories. Strict evidence requires each
family's documented nonallocation/applicability; sensitivity retains applicable
allocated, edited or unavailable evidence with flags. Civilian employment is exactly
EMPSTATD10/12; private wage/salary additionally requires CLASSWKRD22/23. Staffing
retains temporarily absent workers. Workplace mixes and commuting require at-work,
applicable domestic endpoints and applicable non-home transport (NIU is excluded).
Migration requires domestic movers MIGRATE1 2/3, from prior work/migration PUMA to
current residence PUMA; this is geographic movement, not prior-job or job-related
movement. Strict migration and matched sensitivity use annual 2024 (k=1); pooled
migration sensitivity uses 2023–2024 (k=2). Other products use 2023–2024 (k=2).

Canonical staffing and workplace mixes require frozen supported NAICS six-digit/SOC
detailed scalar leaves and recompute supported-subset denominators. Prefixes,
candidates and common ancestors cannot supply leaves; crosswalk/imputation provenance
cannot enter strict canonical products. County/MSA products allocate only observed
workplace mixes using work/migration population factors followed by typed county/CBSA
membership. They provide no allocated flows or canonical allocated products. Keep
2020 population/PUMAs, 2022 county composition, the 2025 county inventory (including
all nine Connecticut planning regions) and July 2023 delineations distinct.
Micropolitan and no-CBSA residual mass remain separate; MSA mass is not renormalized.

PERWT supplies point estimates; exactly REPWTP1–80 supply sampling variance at literal
CSV factor 1. Native weighted masses aggregate in Decimal before Float64 publication;
annual-average totals divide by k once. Signed replicate weights and ratios are
retained. Only `annual_average_total` and `forward_share` are published, for positive
full-weight cells. Shares condition on identified eligible pairs and denominators
use each numerator's exact restrictions. Allocation-conditional sampling SEs quantify
neither allocation error nor mapping uncertainty. All targets retain
`size_gate_pending`; no minimum count is chosen. Evaluation inputs must never be used
for embedder training, mining or model selection.
