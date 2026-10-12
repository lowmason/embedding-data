# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Builds aggregate evaluation targets for industry (NAICS), occupation (SOC), and geography embeddings from three sources: OSHA ITA Form 300A summaries, ACS via IPUMS USA, and CPS via IPUMS CPS. `specs/embedding-evaluation-data-spec.md` is the source of truth. Only the IPUMS extract scripts exist so far (define → submit → download → CSV-to-Parquet); OSHA ingestion, code parsing, geography allocation, targets, and manifests are planned, not built.

## Commands

```bash
uv sync --locked            # Python 3.14 project env + dev deps (pytest, hypothesis, behave)
uv run --locked pytest      # unit + property tests (testpaths = tests/)
uv run --locked pytest tests/test_cps_benchmark_extract.py::test_monthly_start_option_filters_catalog
uv run --locked behave      # Gherkin acceptance scenarios in features/
uv run --locked behave -n "Preview monthly samples from a later start"
uv lock --check
uv run embedding-data acs core --dry-run --out "$(mktemp -d)"   # offline: no key, no network
```

No linter, formatter, type checker, or CI is configured.

**Expected baseline:** the full pytest suite and every Behave scenario pass; any failure is a regression.

## Architecture

**Extract modules are commands of one console entry point.** `embedding-data = "embedding_data.cli:app"` registers each module's `main` directly (`acs`, `cps`) rather than mounting its Typer `app` with `add_typer`, which would add a `main` subcommand. The top-level `@app.callback()` supplies its help and keeps it a command group, and its `pretty_exceptions_show_locals=False` keeps the API key out of tracebacks. Each module keeps its own single-command `app` for tests. `pyproject.toml` is the only dependency list (the modules carry no PEP 723 blocks). `PROJECT_ROOT = Path(__file__).resolve().parents[2]` assumes the `src/embedding_data/` layout and an editable install, uv's default.

**Shared flow.** `build_extract()` returns an `ipumspy.MicrodataExtract` (CSV, data-quality flags); its definition is written to `<out>/<set>/extract.json`. Unless `--dry-run`, the script submits, waits, downloads, and `csv_to_parquet()` streams each `.csv.gz` to a temporary CSV and lazily sinks Parquet, keeping the `.csv.gz` and deleting the temporary CSV. Code columns stay strings: ACS `INDNAICS`/`OCCSOC` through schema overrides (values like `31M`, `1110XX`); CPS `IND`/`OCC`/`INDLY`/`OCCLY` zero-padded to four characters. Re-running submits a new extract; there is no resume.

**CPS sample IDs come from the live IPUMS catalog, never a hardcoded list.** `select_samples()` keeps one sample per month, preferring the `b` basic file over the `s` supplement, and takes ASEC from 2025 on regardless of `--start`. So a CPS `--dry-run` still needs `IPUMS_API_KEY` and network access; an ACS `--dry-run` is fully offline. Apart from `--help`, do not run CPS commands, or ACS without `--dry-run`, unless the user asks — they call the IPUMS API with the real key.

**Credentials.** Both modules load the root `.env` (`DOTENV_PATH`) with python-dotenv; an exported `IPUMS_API_KEY` takes precedence. ACS loads it only without `--dry-run`, because its definitions need no catalog. Output defaults to `data/raw/acs` and `data/raw/cps` under the project root.

**Test seams.** Tests and Behave steps patch the module-level `IpumsApiClient` (autospec) and `DOTENV_PATH` with `patch.object`, so both must remain module globals looked up at call time. The `cli_runner` fixture in `tests/conftest.py` removes `IPUMS_API_KEY` from the environment. The root `.env` holds a real key: a new test that does not patch both `DOTENV_PATH` and `IpumsApiClient` can load it and make live IPUMS requests.

## Spec rules

- Where a script and the spec disagree, the spec governs; fix the script.
- The spec's header names `derive-roadmap` as the required next skill: do not plan the spec directly or split it into per-subsystem plans. Plans and finished specs go in `specs/plans/`, `specs/plans/completed/`, and `specs/completed/`.
- Facts marked *(open — …)* are settled by the spec's Verification items (V1–V12), not by assumption. Never describe planned targets as built, or fixture or partial-extract results as benchmarks.

Invariants for new code (details in the spec):

- **Relatedness is observed, never assumed.** No target is derived from NAICS, SOC, or geographic code structure; formal trees appear only as node and edge tables.
- Imputed values — Census allocations (Q-prefixed flags), crosswalked codes, allocated PUMAs, CPS dependent-interviewing carry-forwards — are flagged at ingestion and excluded from headline targets.
- Mixed-depth codes are parsed into candidate sets, never truncated or guessed; an unparseable code fails the build. Vintage concordances keep one-to-many relationships as flagged candidate sets.
- Geography is typed node and edge tables (county → state → division → region, and county → CBSA), never a single tree. PUMAs map to counties through population-weighted factors, never majority assignment.
- Raw downloads are immutable. Transformations are deterministic, offline, lazy Polars with method-style expressions; ipumspy's pandas readers are not used.
- IPUMS microdata never leave the machine or enter git (`data/` is gitignored); only aggregates are shared. The API key is never written to a file, log, or manifest. Benchmark tables never become embedder training data (R8.4).
- ITA is a program-selected filing universe, not a frame. The files under `data/raw/osha/` are case-detail data, not the Form 300A summaries that R2 requires.

## Conventions

Single-quoted strings and `'''` docstrings. Indentation differs by file — the CPS module and all tests use 4 spaces, the ACS module uses 2 — so match the file being edited.
