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
submission, download, and CSV-to-Parquet conversion. The CPS CLI uses Typer;
the saved ACS script uses `argparse`.

OSHA Form 300A ingestion, classification concordances, geography allocation,
person-month linkage, aggregate targets, and provenance manifests are planned.
The existing OSHA case-detail files under `data/raw/osha/` are a different input
from the Form 300A summaries required by the specification.

The extract workflows have been checked with offline definitions and synthetic
fixtures. Live IPUMS sample and variable acceptance remains to be verified.

## Data sources

| Source | Samples or coverage | Purpose |
| --- | --- | --- |
| [OSHA Injury Tracking Application](https://www.osha.gov/itadata), Form 300A summaries | 2016–2025, planned | Establishment employment, hours, location, NAICS codes, employer descriptions, and firm structure |
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

The main libraries are `ipumspy` for IPUMS requests, Polars for conversion,
Typer for the CPS CLI, and `python-dotenv` for CPS credential loading. The CPS
script also declares its own dependencies and Python minimum of 3.11 in inline
metadata; `uv run` creates a separate script environment for it. See
[uv's script documentation](https://docs.astral.sh/uv/guides/scripts/).

Register for both IPUMS USA and IPUMS CPS, then create an
[IPUMS API key](https://account.ipums.org/api_keys). The same key is used for
both collections once the account has access to them.

Create `.env` at the repository root, for example
`~/Projects/embedding-data/.env`:

```dotenv
IPUMS_API_KEY=your-api-key
```

Use the root `.env`, even if another `.env` exists under `src/embedding_data/`.
CPS loads the root file with `python-dotenv`; an exported `IPUMS_API_KEY` takes
precedence. ACS currently reads only the process environment, so its download
commands below use `uv run --env-file .env`.

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
uv run src/embedding_data/acs_benchmark_extract.py core --dry-run --out data/raw/acs
```

Submit the core extract, wait for completion, download it, and convert it:

```bash
uv run --env-file .env src/embedding_data/acs_benchmark_extract.py core --out data/raw/acs
```

Request all three sets:

```bash
uv run --env-file .env src/embedding_data/acs_benchmark_extract.py core vintage five_year --out data/raw/acs
```

The explicit `--out` is needed to use this project's intended raw-data layout:
the current ACS script otherwise defaults to `data/ipums`. Each set gets its
own subdirectory. Conversion preserves `INDNAICS` and `OCCSOC` as strings,
including aggregated codes such as `31M` and `1110XX`.

## CPS extracts

The script is currently saved as `src/embedding_data/cps_benchmarl_extract.py`, with
that spelling. Use the filename below rather than the alternate spelling in
the specification.

| Name | Selection | Universe |
| --- | --- | --- |
| `monthly` | Catalog samples from `--start`, default `2025-01`; excludes ASEC and prefers a basic sample when both variants exist | Labor-force members, `LABFORCE` = 2 |
| `asec` | ASEC catalog samples from 2025 onward; unaffected by `--start` | All persons |

With no extract names, both sets are requested. CPS dry runs **require the API
key and network access** because they retrieve the sample catalog; they write
definitions without submitting extracts.

```bash
# Inspect the CLI without contacting IPUMS.
uv run src/embedding_data/cps_benchmarl_extract.py --help

# Retrieve the catalog and write definitions for monthly and ASEC.
uv run src/embedding_data/cps_benchmarl_extract.py --dry-run

# Preview only monthly samples from August 2026 onward.
uv run src/embedding_data/cps_benchmarl_extract.py monthly --start 2026-08 --dry-run

# Submit, wait, download, and convert both sets.
uv run src/embedding_data/cps_benchmarl_extract.py

# Download only monthly samples from August 2026 onward.
uv run src/embedding_data/cps_benchmarl_extract.py monthly --start 2026-08
```

The default destination is `<project-root>/data/raw/cps/`, with `monthly/` and
`asec/` subdirectories. Use `--out PATH` to override it. CPS stores industry and
occupation as Census codes; conversion pads `IND`, `OCC`, `INDLY`, and `OCCLY`
to four-character strings. Mapping them to NAICS and SOC remains a later step.

## Files and planned outputs

After a successful download and conversion, each extract directory contains its
definition (`extract.json`), downloaded IPUMS files (`.csv.gz` and `.xml` DDI
codebook), and a converted `.parquet` file. A dry run writes only the definition.
The scripts retain the compressed data and delete the temporary decompressed
CSV after conversion. Re-running submits a new extract; resumable downloads
and retrieval manifests are not implemented.

The specification calls for aggregate Parquet targets covering staffing
patterns, area mixes, worker profiles, job-change flows, commuting, migration,
employer text–code pairs, and industry co-ownership. It also calls for NAICS
2022 and SOC 2018 mappings, typed geography edges, allocation flags, uncertainty
estimates, cell counts, and input hashes. These targets are not yet built.

Benchmark data stay separate from embedder training and model selection.
IPUMS microdata remain local and must not be committed or redistributed as
project outputs. Share aggregate targets and cite the collections under the
[IPUMS USA terms](https://usa.ipums.org/usa/terms.shtml) and
[IPUMS CPS terms](https://cps.ipums.org/cps/terms.shtml). `.env` is ignored by
Git; `data/` is not currently ignored, so keep microdata out of staged changes.
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

The CPS checks cover CLI defaults, credential loading, catalog selection,
dry-run behavior, and Parquet conversion. The property tests generate valid
months and sample catalogs to check date boundaries, chronological ordering,
basic-sample preference, and the ASEC year cutoff. Behave runs the real CLI
against a fixture catalog and temporary output files, replacing the IPUMS client
so it cannot make live requests. The starter test strategy is recorded in
[specs/cps-test-strategy.md](specs/cps-test-strategy.md).

The ACS tests currently expect a Typer and dotenv interface that the saved ACS
script does not provide; the full suite has known ACS failures until the
script and tests are aligned. Fixture checks do not confirm live IPUMS variable
acceptance or survey totals.

## Project layout

```text
specs/embedding-evaluation-data-spec.md      Full data requirements and verification tasks
src/embedding_data/acs_benchmark_extract.py  ACS extract definitions and downloader
src/embedding_data/cps_benchmarl_extract.py  CPS catalog selection and downloader
tests/                                       Offline unit, property, and conversion checks
features/                                    Behave CPS dry-run acceptance scenarios
data/raw/acs/                                ACS files when downloaded with --out above
data/raw/cps/                                Default CPS output location
data/raw/osha/                               Existing OSHA case-detail inputs
pyproject.toml                               Project dependencies and Python requirement
uv.lock                                      Project dependency lockfile
```

The `embedding-data` console entry point is currently package scaffolding. Run the
extract scripts directly using the commands above.
