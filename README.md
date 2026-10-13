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
records the full-data run and its unresolved source codes. Geography allocation,
ACS/CPS code parsers, person-month linkage, aggregate targets and the shared
target writer remain planned. Raw downloads are recorded in
`data/raw/manifest.jsonl`.
The OSHA case-detail files are acquired but feed no target; the specification's
establishment data are the Form 300A summaries.

The extract workflows have been checked with offline definitions and synthetic
fixtures. Live IPUMS sample and variable acceptance remains to be verified.

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

The measured `stage4_v11_20261013` bundle uses schema `codes-ita-v1` and retains
all 3,206,055 source rows and original columns, in source order. Its 69,035
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
accuracy or a full-table assignment; targets and full production assignment remain
planned.

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
estimates, cell counts, and input hashes. These targets are not yet built.

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
