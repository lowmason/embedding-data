# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Builds aggregate evaluation targets for industry (NAICS), occupation (SOC), and geography embeddings from three sources: OSHA ITA Form 300A summaries, ACS via IPUMS USA, and CPS via IPUMS CPS. `specs/embedding-evaluation-data-spec.md` is the source of truth. So far the IPUMS extract scripts (define → submit → download → CSV-to-Parquet), the OSHA Form 300A summary acquisition with its stacked establishment-year table, and an OSHA case-detail download (download → CSV-to-Parquet) exist; every raw file is recorded in an append-only manifest (`data/raw/manifest.jsonl`); canonical NAICS/SOC graphs, NAICS concordances, ITA candidate mapping and filing-universe diagnostics are built. Geography allocation, ACS/CPS code parsers, targets and the shared target writer remain planned.

## Commands

```bash
uv sync --locked            # Python 3.14 env + dev deps (pytest, hypothesis, behave, ruff, pre-commit)
uv run --locked pytest      # unit + property tests (testpaths = tests/)
uv run --locked pytest tests/test_cps_benchmark_extract.py::test_monthly_start_option_filters_catalog
uv run --locked behave      # Gherkin acceptance scenarios in features/
uv run --locked behave -n "Preview monthly samples from a later start"
uv run --locked pytest -m network   # live osha.gov page canary; deselected by default
uv lock --check
uv run embedding-data acs core --dry-run --data-dir "$(mktemp -d)"   # offline: no key, no network
uv run --locked ruff check .                 # lint: E, F, isort, single quotes; 99 columns
uv run --locked pre-commit install           # once per clone
uv run --locked pre-commit run --all-files
```

Pre-commit runs the pre-commit-hooks file checks, `ruff-check --fix`, and the full pytest suite under coverage (`COVERAGE_THRESHOLD`, default 0). Its ruff `rev` must match the ruff version in `uv.lock`. yapf is configured in `pyproject.toml` but is a manual tool, not a hook: running it reindents the ACS module to 4 spaces. There is no type checker or CI.

**Expected baseline:** the full pytest suite (the one `network` canary deselected) and every Behave scenario pass; any failure is a regression.

## Architecture

**Extract modules are commands of one console entry point.** `embedding-data = "embedding_data.cli:app"` registers each module's `main` directly (`acs`, `cps`, `osha`) rather than mounting its Typer `app` with `add_typer`, which would add a `main` subcommand. The top-level `@app.callback()` supplies its help and keeps it a command group, and its `pretty_exceptions_show_locals=False` keeps the API key out of tracebacks. Each module keeps its own single-command `app` for tests. `pyproject.toml` is the only dependency list (the modules carry no PEP 723 blocks). `paths.PROJECT_ROOT = Path(__file__).resolve().parents[2]` assumes the `src/embedding_data/` layout and an editable install, uv's default. `paths.py` also fixes the data layout under `--data-dir` (default `paths.DATA_DIR`): `raw/<source>/`, `raw/manifest.jsonl`, `derived/<source>/`, `preview/<source>/`.

**Shared flow.** `build_extract()` returns an `ipumspy.MicrodataExtract` (CSV, data-quality flags). `--dry-run` writes its definition to `data/preview/<source>/<set>/extract.json`, never under `raw/`. Otherwise `ipums_delivery.deliver()` submits, then stages the delivery of `<name>` (`<collection>_<number>`) in a new `data/raw/<source>/<set>/<name>.part/`; an existing `<name>/` or `<name>.part/` fails the run, because raw downloads are immutable. It writes the submitted `extract.json` into staging, waits, downloads the `.csv.gz` and `.xml` into it, and renames it to `<set>/<name>/` only when all three files are there, so a `.part` directory is an interrupted delivery (not recorded, not a delivery). It then appends exactly those three files, and nothing else in the directory, to `data/raw/manifest.jsonl` (`manifest.py`: SHA-256, extract number, sample IDs, retrieval time, client version). `csv_to_parquet()` then streams each `.csv.gz` to a temporary CSV under `data/derived/<source>/<set>/` and lazily sinks Parquet beside it. Code columns stay strings: ACS `INDNAICS`/`OCCSOC` through schema overrides (values like `31M`, `1110XX`); CPS `IND`/`OCC`/`INDLY`/`OCCLY` zero-padded to four characters. Re-running submits a new extract into a new directory; there is no resume.

**CPS sample IDs come from the live IPUMS catalog, never a hardcoded list.** `select_samples()` keeps one sample per month, preferring the `b` basic file over the `s` supplement, and takes ASEC from 2025 on regardless of `--start`. So a CPS `--dry-run` still needs `IPUMS_API_KEY` and network access; an ACS `--dry-run` is fully offline. Apart from `--help`, do not run CPS commands, ACS without `--dry-run`, or `osha` unless the user asks — the IPUMS commands call the API with the real key, and `osha` downloads up to about 730 MB from osha.gov into the real data tree.

**OSHA download.** `osha` needs no key and takes sets like the IPUMS commands: `summary`, `case-detail`, or both by default. osha.gov's CloudFront returns 403 to non-browser user agents, so `USER_AGENT` is a browser string. `summary` reads the ITA data page (`ita_catalog`) for every `<year> Summary Data` link from 2016 on and refuses a page that lists a year twice, skips a year, names an impossible through-date, or gives the current file no through-date. Each file goes to `raw/osha/summary/<year>/` under OSHA's name; the current year's name carries its through-date, so a later release lands beside the earlier one as a new manifest entry with `through_date`. A summary file on disk but unrecorded stops the run, because `raw_backfill` records only the case-detail files, and so, before any download, does a year whose files plus the listed one leave `ita_summary.latest_release_name` no single latest release (an undated file beside another, or two with one through-date). `ita_summary.build_summary_table` then rebuilds `derived/osha/ita_300a_summary.parquet` on every run (never convert-once) from each year's latest-through-date file, harmonizing size (`size_class` merges 21/22 into 2; 2 is never split), `naics_year` (2012 from the dictionary before 2023, marked; a vintage outside 2012/2017/2022 becomes null and is flagged, `flag_naics_year_unknown`), and the R2.9 flags; an `establishment_type` with no digit becomes null; scientific-notation `total_hours_worked` (`8.62847E+11`) is read as the whole number it spells; structure it cannot harmonize fails the build, and an unrecorded input, or one whose SHA-256 differs from its manifest entry, fails it too. For both sets, existing files in `data/raw/osha` are never re-downloaded (raw immutability), and a file absent but still recorded makes the run exit 1 before that set downloads anything, naming the start of the recorded SHA-256. `case-detail` warns about an unrecorded existing file (its suggested `--data-dir` shell-quoted) and converts its CSV only when that Parquet is absent. Downloads go to `.part`, are renamed only after `num_bytes_downloaded` matches `Content-Length`, and are then recorded. The CSVs mix Windows-1252 and UTF-8 bytes, sometimes within one line; `osha_encoding.decode_line` transcodes them to temporary UTF-8 CSVs that are cast strictly (codes stay strings). A first summary run downloads about 258 MB, a case-detail run about 475 MB.

**Raw provenance.** `manifest.append_entries()` refuses a path already recorded, so each raw file maps to one hash for good; `manifest.entry_for()` looks an entry up for output manifests to cite. `raw_backfill.py` is a one-off (`python -m embedding_data.raw_backfill`) that moved the files delivered before the manifest into this layout; their entries flag `retrieved_at` and `client_version` as proxies. On a migrated tree it moves nothing, but it still records the OSHA case-detail files missing from the manifest (what the `osha` warning points to). Every check runs before the first move, but a failure after files moved (a failing rename, or `append_entries` failing after the renames) is not recoverable by re-running, because a fully moved set no longer has a top-level `.csv.gz` and is skipped; verify the tree and manifest by hand.

**Credentials.** Both modules load the root `.env` (`DOTENV_PATH`) with python-dotenv; an exported `IPUMS_API_KEY` takes precedence. ACS loads it only without `--dry-run`, because its definitions need no catalog. `--data-dir` defaults to `data/` under the project root (`paths.DATA_DIR`).

**ITA audit and verification.** `uv run embedding-data audit --data-dir data` is
read-only and exits 1 on a discrepancy. `manifest.entry_for` verifies file hashes;
`recorded_entry_for` only looks up recorded provenance for restoration/existence
diagnostics. The separate `uv run python -m embedding_data.ita_verification_run`
command group takes `--data-dir`: `references` and `geocode` acquire public data;
`import-hud WORKBOOK QUARTER` imports an official HUD ZIP-to-county workbook;
`sample HUD RUN_ID` and `measure RUN_ID` are offline. `sample` rebuilds the source
table once under the Stage 2 source/hash contract, freezes the deterministic
sample and headerless batch requests, and records input/code hashes and dependency
versions. `measure` never rebuilds the table or recontacts Census; changed
sample/table/request bytes fail. Runs write measurement reports, not target
tables, under `derived/osha/verification/<run_id>/`; raw references and Census
responses remain immutable under `raw/references/` and are manifest-covered.
HUD `retrieved_at` is local import time and is flagged as a proxy, not the original
browser download time. Census Current catalogs identify request options but do
not freeze address-source data across batches or resumed acquisition. Software
completion and fixture reports do not adopt V1–V3 decisions.

**Adopted ITA rules (owner, 2026-10-13).** The actual
[V1–V3 finding](specs/findings/v1-v3-ita-verification.md) settles R2.6–R2.8.
Keep delivered strings; keys use NFKC, casefold and collapsed whitespace, with
exact placeholder and official 2012/2017/2022 title flags. Employer fallback and
reconstructed EIN remain explicit; blank employers never form a shared group.
Use establishment IDs as all-year candidates; confirm only unique-ID links with
the same usable unreconstructed EIN and complete normalized full address. Changed-ID
fallback also requires uniquely matched EIN/name/address tuples. County assignment
uses an exact cached Census ACS2025 geography match first, then a compatible HUD
single-positive-BUS county (reviewed quarter 2025Q4); dominant-share selection is
diagnostic only. Preserve ambiguity, scope and incompatible-vintage flags, including
legacy CT counties. Check the chosen returned county against territory prefixes
60/66/69/72/74/78 for assignment and both returned counties for comparison,
in addition to delivered-state exclusions; retain separate method scope counts.
The scope correction is measured in `v1_v3_20261013_scopefix` using verified
original response bytes and receipt metadata from `v1_v3_20261013`.
Sample comparisons are not county accuracy, a county hierarchy
or full-table target construction. Each run records its own code/dependency hashes
and all cached batches; fresh acquisition can differ under mutable Current data.

**Canonical classification and ITA bundle (Stage 4).** `codes acquire` verifies
cached references and acquires missing official originals; missing BLS downloads
require `BLS_CONTACT_EMAIL`. `codes import-reference KIND FILE` imports exact
public original bytes with a registered official identity and proxy import time.
Use `uv run --offline --locked embedding-data codes build NEW_RUN_ID --data-dir
/Users/lowell/Projects/embedding-data/data` for the offline build; always supply
the intended root, especially in a worktree. Restricted workspaces use
`UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache`. Never call `osha`,
`build_summary_table` or verification `sample` to prepare a codes build: it reads
and checks the existing source against selected raw releases without rewriting it.
Existing run or `.part` names fail and earlier bundles remain immutable.

The [actual V11 finding](specs/findings/v11-ita-naics-mapping.md) records
`stage4_v11_20261013_r2`, `codes-ita-v1`, all 3,206,055 rows, all original columns
and verified row order. This selected run remeasures reviewed code `ccd138f`
after the CLI workbook-error diagnostic fix; the earlier `stage4_v11_20261013`
bundle remains byte-identical. Classification forests have child-to-parent `hierarchy`
edges and no invented root; their single-parent validator is classification-specific.
Sorted candidate lists retain every official possibility. Known-vintage mismatches
remain unresolved with empty candidates; unknown-vintage unions retain uncertainty
and never populate canonical scalar/node IDs. Singleton crosswalks remain flagged.
Filing flags are nullable under disagreement; bridged legacy-label and reference
ambiguity flags persist independently of a determinate result. The published
exemption labels `5173` and `5181` use the bounded official 2002-to-2007 bridge;
2007 `517110` retains mixed membership. Nominal filing cycles cannot resolve late
submission timing. These diagnostics do not judge whether a submission was improper.

The bundle contains twelve Parquet tables plus `inputs.json`, `report.json` and
`outputs.json`; the last hashes the other fourteen files and excludes itself.
The finding records its detached checksum. Raw originals/source/code/lock hashes,
dependency versions, schemas and aggregates support later provenance; this is not
the R7 target writer. Source summary and Stage 3 file hashes must remain unchanged.
Geography, ACS/CPS parsing, targets and headline-inclusion decisions retain their
later-stage scope and the source spec's Core principle and stricter V11 contract.

**Test seams.** Tests and Behave steps patch the module-level `IpumsApiClient` (autospec) and `DOTENV_PATH` with `patch.object`, so both must remain module globals looked up at call time. OSHA tests patch `make_client` with a `partial` that injects an `httpx.MockTransport`; fake responses must use `stream=httpx.ByteStream(...)`, because a `content=` body is preloaded and leaves `num_bytes_downloaded` at 0. OSHA summary tests serve the recorded ITA page `tests/fixtures/osha/itadata.html` and bodies from `tests/ita_fixtures.year_file`, one per published file format; `write_release` places and records a raw summary file. The `cli_runner` fixture in `tests/conftest.py` removes `IPUMS_API_KEY` from the environment. The root `.env` holds a real key: a new test that does not patch both `DOTENV_PATH` and `IpumsApiClient` can load it and make live IPUMS requests. Every command test must also pass `--data-dir` (the `data_directory` fixture): `--data-dir` defaults to the real `data/` tree through a Typer default bound at import, so patching `paths.DATA_DIR` cannot redirect it, and a stray test would write fake extracts into `data/raw` and append fake entries to the append-only manifest.

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
- ITA is a program-selected filing universe, not a frame. The Form 300A summaries that R2 requires are under `data/raw/osha/summary/`; the case-detail files directly under `data/raw/osha/` feed no target.

## Conventions

Single-quoted strings and `'''` docstrings. Indentation differs by file — the CPS module and all tests use 4 spaces, the ACS module uses 2 — so match the file being edited.
