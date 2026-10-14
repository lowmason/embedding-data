# Target contract and ITA area-mix slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish verified county assignments for all 2016–2025 ITA source rows and a conditional 2023 county-by-native-NAICS-2022 establishment-share target, with a reusable target writer and an offline V12 fixture path.

**Architecture:** Verify explicitly selected immutable Stage 4/5 bundles, freeze row-to-request identity offline, acquire Census evidence through a separate resumable command, and replay that evidence offline into an immutable assignment/target bundle. Keep selected-input verification, request preparation/acquisition, assignment, the shared schema/writer, and the ITA estimator in focused modules. Reuse existing protocol and reference contracts without calling the Stage 3 sample runner or rebuilding production inputs.

**Tech Stack:** Python >=3.14; existing Polars >=2.0.0, httpx >=0.28.1, Typer >=0.27.3 and fastexcel >=0.21.0; pytest/Hypothesis; standard-library hashlib, json, csv, pathlib and dataclasses. No dependency or lockfile changes.

**Spec:** [specs/target-contract-ita-area-mix.md](../target-contract-ita-area-mix.md). Read it alongside the [source spec](../embedding-evaluation-data-spec.md), the [Stage 4 finding](../findings/v11-ita-naics-mapping.md), the [Stage 5 finding](../findings/stage-5-geography-reference-build.md), and completed plans 3–5's Handoff sections.

> Roadmap: specs/embedding-evaluation-data-spec-roadmap.md, Stage 6 — on plan completion, tick the stage and re-validate later stages against what shipped.

## Global Constraints

The following requirements are copied verbatim from the stage spec:

- "Assign counties across the entire ten-year ITA establishment table, 2016–2025."
- "Prove the target pipeline with 2023 establishment shares within each county, using six-digit NAICS 2022."
- "Preserve source-row order and multiplicity, including exact duplicates and repeated establishment IDs."
- "The counting unit is a submitted establishment-year record, not an independently confirmed unique establishment."
- "Employment, hours and filing-rule flags remain diagnostics rather than target filters."
- "Crosswalked and unresolved industry values remain excluded."
- "Give each included record weight one, report cell counts, and use null standard errors with `se_method='none'`."
- "No count threshold is set or passed here."
- "Run IDs are required arguments, not a latest-run lookup or an implicit alias:"
- "Do not mix runs."
- "Do not call `osha`, `build_summary_table` or verification `sample` to prepare Stage 6."
- "Leave source summaries and all previous bundles and verification runs unchanged."
- "Stage 6 supports only `--year 2023`; another year fails before publication."
- "An input with no eligible 2023 records fails before publishing an empty target."
- "There is no automatic acquisition from `prepare-ita` or `build-ita`."
- "An occupied final or staging name fails without overwriting it; a leftover `.part` is an interrupted run that must be inspected and removed before a new attempt."
- "Code/dependency changes to preparation or assignment invalidate resume/build and require new preparation; there is no silent mixed-version resume."
- "Keep acquisition sequential with the existing client timeout/error behavior."
- "A transport or validation failure stops the invocation; an explicit re-run resumes from verified completed batches."
- "Do not add blind retries or change a frozen request to make a response pass."
- "Incomplete raw `.part` downloads are never cited."
- "HUD cardinality is evaluated on all original positive candidates before scope checks."
- "Largest-share selection, zero-share selection and invented old-Connecticut bridges never supply assignments."
- "Reject overlapping appended column names or a schema mismatch."
- "Nullable filing decisions do not become false."
- "Do not coerce source null flags to false."
- "No row claims to pass a size gate."
- "Manifest appends outside this run do not invalidate an otherwise unchanged set of cited files; validate the cited entries and pinned input bytes."
- "No network or credentials are used by offline commands."
- "Raw downloads and prior production artifacts remain immutable, and requests/assignments stay in the gitignored local data tree."
- "A fixture result cannot satisfy the production milestone."

Source-spec R9.1 also applies: "Transformations are lazy polars with method-style expressions." Use lazy scans/joins/aggregations and sinks for the full establishment table; collect only bounded references, distinct submitted requests, parsed response batches and aggregate diagnostics. Do not collect all source dictionaries or loop over 3,206,055 source rows in Python. Codes remain strings; use selected graph membership rather than prefix-derived target values. Keep the administrative 2025, CBSA July 2023, HUD 2025Q4 and mutable Census Current frames distinct.

This plan creates no ACS/CPS transformations, extra target years/families, geographic/industry rollup targets, employment weighting, crosswalk-included variants, establishment linkage/deduplication, historical geography, or V9 gate. No evaluation target enters embedder training, architecture tuning or model selection. Every test command supplies a temporary data root; no default test reads the real data tree or root `.env`.

## Decisions

- **D1** (owner, plan review, 2026-10-14): Approve plan 6 as written, including its five implementation defaults. Applied in: Tasks 1–8 and Global Constraints. The owner's design decisions remain recorded in the stage spec; no spec amendment is introduced.
- **D2** (owner, plan review, 2026-10-14): Execute the approved plan via subagent-driven-development in a fresh session. Applied in: Tasks 1–8 and Plan review and execution boundary.
- **D3** (owner, execution preflight, 2026-10-14): Use one implementation-registry test helper in `tests/target_fixtures.py` with explicit local autouse fixture wrappers in Tasks 2–3, resolving the duplicated-logic review conflict. The helper is invoked only by those local wrappers, never by global conftest or V12. Applied in: Tasks 2–3.

- **D4** (owner, transport recovery, 2026-10-14): Amend Stage 6 to a 1,000-record operational Census batch limit in a new preparation, preserving the original frozen run. The Census service maximum remains 10,000 and Stage 3 is unchanged. Apply a minimal preparation-only default change, verify the unpatched production default and boundary, and review it before preparing. New preparation `stage6_ita_assignment_20261014_1000`; acceptance targets `stage6_ita_area_mix_20261014_1000` and `_replay`. The original `stage6_ita_assignment_20261014` and its four raw controls stay byte-identical with their original software contract. All original tuples/source-row mappings and upstream selections remain equal; diagnostic subsets cannot populate production evidence. Resume Task 8 Steps 2–6 under this amendment; preserve all original acceptance criteria. Expected observed workload is 1,114 batches (1,113 × 1,000 + 538).

---

## Entry evidence and approved implementation choices

Prepared on `main` at `2035d1f8d91bf68b2a004a9d96be1c5a558ecfaf`, initially clean. The writing-plans entry check reports highest ID 5, next free 6 and no collisions across refs/worktrees. Fresh planning baseline: **532 pytest passed, one network canary deselected; one Behave feature/two scenarios/ten steps passed; ruff passed; offline lock check resolved 63 packages and passed.** No production acquisition/build was performed while planning.

Concrete implementation defaults:

1. Use `ita-request-v1` plus a NUL byte and compact UTF-8 JSON of exactly four submitted strings for SHA-256 request identity. Null submitted fields become empty strings. Source ZIP normalization alone uses Stage 3's `zip_key`; delivered street/city/state are unchanged.
2. Pin the two selected production `outputs.json` checksums in the selected-input registry. A different run must supply its own explicit detached checksum through optional `--codes-outputs-sha256` / `--geography-outputs-sha256` preparation options. Tests supply fixture checksums; no fixture bypass skips verification.
3. Store immutable per-batch JSON receipts next to their raw responses. A receipt contains the request hash, catalog citations/options, response citation and original response acquisition time. Publish an aggregate acquisition completion inventory only after every batch verifies.
4. Freeze preparation/assignment software separately from estimator/writer software. Changing a preparation, acquisition, assignment, validation or shared I/O dependency invalidates resume/build; changing only `ita_area_mix.py` or `target_contract.py` permits a new target run against the same frozen evidence, with new implementation provenance.
5. Use one explicit unassigned reason per precedence outcome; keep overlapping flags independently. Selected-year disjoint partitions are `unassigned_geography`, `assigned_excluded_industry`, `eligible`. A source row excluded for both geography and industry belongs to the first partition while the report retains the mapping-status cross-tabulation.

## Existing seams and traps

- `code_build.py:21` supplies `SUMMARY_SCHEMA`; `ita_naics_mapping.py:8` supplies `MAPPING_SCHEMA`; `filing_rules.py` supplies `FILING_COLUMNS`. Their ordered concatenation is the exact 38-column canonical schema. `code_build.validate_canonical` is useful but does not prove every native-state invariant or physical row order.
- Stage 4/5 `outputs.json` files map filenames to `{sha256, size}`. Parquet row counts/schemas are in `report.json['tables']`. Verify both; do not assume the older inventory already embeds schemas.
- `code_build.check_source` checks a full-row multiset, not physical source order. Stage 6 additionally compares the canonical table's first 24 columns to the selected source in physical order, including duplicate multiplicity. Do not run a builder to verify a selected bundle.
- Stage 4 `inputs.json['raw']` does not cite the two summary dictionaries. Explicitly verify/cite `raw/osha/summary/summary_data_dictionary.pdf` and `raw/osha/summary/ITA_Data_Dictionary.pdf`. These are documentary provenance; no PDF parser is needed.
- `ita_verification_run.py:21–27` defines service URL/options, batch limit and the 600-second client; `ita_county_verification.parse_geocodes` returns `row_key, geocode_status, match_type, county_geoid`. Adapt names, preserve its status/null conventions, and enforce exact IDs against each frozen request file.
- Never call `ita_verification_run.prepare` or `stratified_sample`: they rebuild/deduplicate/sample the source. Never use linkage `with_keys`/`address_key` to identify submitted addresses.
- `geography_hud.LOOKUP_SCHEMA` and `geography_tables.COUNTY_SCHEMA` are the exact appended schemas. The old `zip_candidates` cannot represent absent versus zero-business ZIPs or the selected county-inventory contract.
- Use `geography_references.safe_path` / `occupied` and the ASCII run-ID convention. Do not copy `geography_build`'s whole-manifest-hash gate: unrelated appends are permitted here.
- `tests/code_fixtures.seed_code_tree` currently creates only 2022/2023 concorded rows; add a fixture-only option for all-year raw source rows. Existing default callers must retain identical behavior.

## File map and ownership

| File | Responsibility |
| --- | --- |
| `src/embedding_data/target_io.py` | Safe named staging, canonical JSON, file/Parquet inventories, pinned-byte and citation checks |
| `src/embedding_data/target_inputs.py` | Selected Stage 4/5 bundle verification, source parity and typed node validation |
| `src/embedding_data/ita_assignment_prepare.py` | Frozen full-row index, submitted tuple identity, deterministic request files and preparation verification |
| `src/embedding_data/ita_assignment_acquire.py` | Explicit sequential Census acquisition, immutable batch receipts, cached replay |
| `src/embedding_data/ita_assignment.py` | Full-table county precedence, exact appended schema and independent assignment diagnostics |
| `src/embedding_data/target_contract.py` | Shared `targets-v1` schema, general validation and sorted Parquet writer |
| `src/embedding_data/ita_area_mix.py` | Native-2022 eligibility, county denominators, flag support, ITA-specific validation/reporting |
| `src/embedding_data/ita_target_build.py` | Offline orchestration, target-run provenance/inventories, atomic combined publication |
| `src/embedding_data/targets_cli.py`, `src/embedding_data/cli.py` | Three explicit commands and command-group registration |
| `tests/code_fixtures.py`, `tests/target_fixtures.py` | Original-layout all-year fixture source, existing official-layout reference construction, Census fixture transport |
| `tests/test_target_io.py`, `tests/test_target_inputs.py` | Byte inventories, selected bundle/schema/graph/raw/source parity failures |
| `tests/test_ita_assignment_prepare.py`, `tests/test_ita_assignment_acquire.py`, `tests/test_ita_assignment.py` | Identity, acquisition/resume/replay and county rules |
| `tests/test_target_contract.py`, `tests/test_ita_area_mix.py` | Shared versus family validation and handwritten estimands |
| `tests/test_ita_target_build.py`, `tests/test_targets_cli.py`, `tests/test_target_contract_v12.py` | Immutable publication, CLI and extensible raw-to-target fixture path |
| `README.md`, `CLAUDE.md` | Shipped commands and reusable consumer boundaries |
| `specs/findings/stage-6-ita-area-mix-build.md` | Measured production milestone and detached inventories |

No production source/reference/verification module needs refactoring. Existing Stage 2–5 implementations, their data and `pyproject.toml`/`uv.lock` stay unchanged. `tests/code_fixtures.py` is the only existing fixture implementation edited. Workers own only their task's listed files, are not alone in the codebase, and must preserve others' edits. Execute Tasks 1–8 in order; task-scoped implementation reviews follow each task, and final branch review precedes completion/integration. Start execution in an isolated checkout using using-git-worktrees; this plan itself does not create one.

## Durable testing strategy

Mock only HTTP, time and an injected final-validation mutation; actual parsers, lazy transformations, manifests, inventories and Parquet I/O run. Tasks 2–3 additionally use an explicit unit-test implementation-module registry while later assignment/acquisition files do not yet exist; it hashes actual existing code, and its exact registry is frozen/verified. Task 7 removes this unit boundary and tests the complete production software inventory. No production option bypasses a missing implementation module. All new tests are ordinary offline fixture tests, unmarked. Production acceptance is an explicit command sequence outside pytest. Preserve the existing network exclusion/unknown-marker error; no new live canary or broad marker changes.

| Invariant | Cheapest layer and fixture | Task |
| --- | --- | --- |
| Detached inventory exact set/hash/size, schema/version/row counts, raw citations and typed graph relationships | Tiny real fixture bundles, one mutation per case | 1 |
| Summary/canonical physical prefix parity; duplicate rows/repeated IDs survive | Index-aligned small canonical/source frames | 1–2 |
| Exact submitted tuple hashing, collision refusal, m:1 mapping, contiguous UInt64 row identity and 10,000-row batches | Handwritten strings plus boundary fixture of 10,001 distinct requests | 2 |
| Catalog names resolved uniquely, arbitrary returned IDs used, exact response-ID cover, per-batch immutable receipt/resume | MockTransport, two/three small batches and malformed original response bodies | 3 |
| Delivered-state and exact-excluded vetoes; compatible exact wins; singleton fallback after non-exact/incompatible; all HUD flags retained | Handwritten rule matrix plus published Stage 5 fixture lookup | 4 |
| Exact 38-column prefix and appended physical schemas/order, no join fanout, source-row order | Tiny assignment frame, duplicate source rows, metro/micro/non-CBSA references | 4 |
| Shared schema/key/metadata/finite/count/SE rules independent of ITA | Handwritten target frames including feature units and values above one | 5 |
| C/D estimand, preserved duplicates, diagnostic-only anomalies, true/null flag support, empty diagnostics | Hand-calculated 2023 cells/zero-eligible county plus all-year exclusions | 6 |
| Original raw→harmonization→official-layout codes/geography→frozen requests→Census originals→assignment→target→manifest | Reusable all-year tmp fixture pipeline; network/credential barrier during offline phases | 7 |
| Occupied/partial/no-eligible/final mutation cannot publish; replay logical rows/JSON; unrelated manifest append allowed | Tmp integration tree and publication-boundary mutation | 7 |
| Measured real all-year accounting, output inventories, cache replay, protected artifacts and zero-discrepancy audit | Explicit selected real-root acceptance | 8 |

Focused commands appear per task. The default/pre-merge command group is:

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest -m 'not network'
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked behave
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked ruff check .
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv lock --offline --check
```

No CI exists. Run the full group at Tasks 3, 7 and 8, recording observed results. Do not substitute historical baseline counts for fresh evidence.

---

### Task 1: Verify explicitly selected bundles and their source/raw contracts

**Files:** Create `src/embedding_data/target_io.py`, `src/embedding_data/target_inputs.py`, `tests/target_fixtures.py`, `tests/test_target_io.py`, `tests/test_target_inputs.py`. Modify `tests/code_fixtures.py:126–222` only to separate reference seeding from its current default source seeding.

**Interfaces:**

- `target_io.stage(root: Path, run_id: str, data_dir: Path) -> tuple[Path, Path]` validates safe run name/path, refuses occupied final/staging, creates staging and returns `(final, staging)`.
- `target_io.write_json(file: Path, value: object) -> None`; `file_record(file: Path) -> dict`; `inventory(directory: Path, names: list[str]) -> dict`; `verify_inventory(directory: Path, expected: dict, names: set[str]) -> None` verify hash/size and optional Parquet rows/schema. `verify_raw(data_dir: Path, citations: list[dict]) -> list[dict]` verifies exact cited ManifestEntries using `entry_for`.
- `target_inputs.select(data_dir: Path, codes_run: str, geography_run: str, *, codes_outputs_sha256: str | None = None, geography_outputs_sha256: str | None = None) -> SelectedInputs`.
- `SelectedInputs` is a frozen dataclass with `summary: Path`, `canonical: Path`, `codes: dict[str, Path]`, `geography: dict[str, Path]`, `provenance: dict`. It has `verify(data_dir: Path) -> None`, which rechecks pinned selection/citations/source parity without running upstream builders.
- `target_inputs.validate_native(canonical: pl.LazyFrame, nodes: pl.DataFrame) -> None` rejects contradictory native states, scalar/candidate/node assertions and missing/wrong typed nodes, including on rows outside 2023.
- Fixture seam: `seed_code_tree(data_dir: Path, *, include_summary: bool = True)`; default behavior unchanged. `target_fixtures.seed_inputs(data_dir: Path) -> SelectedInputs` writes all ten raw summary years/dictionaries, builds fixture Stage 4/5 bundles through their real builders, and calls `select` with explicit fixture detached hashes.

- [ ] **Step 1: Add the fixture-only split and the failing selected-input tests.** Move the existing source-writing loop and `build_summary_table` call under `if include_summary:`; keep all reference construction intact. Use this concrete fixture composition. `golden_source_rows` is defined by Task 6's complete fixture recipe and must be present now because the earlier tests consume it; Task 6 adds the estimator assertions, not the source fixture for the first time.

```python
def seed_inputs(data_dir: Path) -> SelectedInputs:
    code_registry = seed_code_tree(data_dir, include_summary=False)
    for year, rows in golden_source_rows().items():
        write_release(data_dir, year, year_file(year, rows))
    for name in ['summary_data_dictionary.pdf', 'ITA_Data_Dictionary.pdf']:
        file = data_dir / 'raw/osha/summary' / name
        file.write_bytes(b'%PDF-1.4\n% Fixture documentary evidence\n%%EOF\n')
        entry = manifest.describe_file(
            file, data_dir / 'raw', retrieved_at=datetime(2026, 10, 14, tzinfo=UTC),
            client='fixture', client_version='1')
        manifest.append_entries(paths.manifest_path(data_dir), [entry])
    ita_summary.build_summary_table(data_dir)
    codes = code_build.build(data_dir, 'fixture_codes', registry=code_registry)
    geography_registry = seed_geography_tree(data_dir)
    geography = geography_build.build(data_dir, 'fixture_geography', registry=geography_registry)
    return select(data_dir, 'fixture_codes', 'fixture_geography',
                  codes_outputs_sha256=manifest.sha256_file(codes / 'outputs.json'),
                  geography_outputs_sha256=manifest.sha256_file(geography / 'outputs.json'))
```

Import the existing fixture builders explicitly from `code_fixtures`, `geography_fixtures` and `ita_fixtures`, and the new selected-input API. Dictionary fixture bytes are documentary stand-ins, never claimed to be parsed official PDFs. No production PDF parser or dependency is introduced. Use fixture codes from those modules rather than adding production code lists.

```python
def test_selected_inputs_verify_without_rebuilding(tmp_path, monkeypatch):
    from target_fixtures import seed_inputs
    from embedding_data import ita_summary

    selected = seed_inputs(tmp_path)
    before = selected.canonical.read_bytes()
    monkeypatch.setattr(ita_summary, 'build_summary_table',
                        lambda *a, **k: pytest.fail('production source rebuilt'))
    selected.verify(tmp_path)
    assert selected.canonical.read_bytes() == before
    assert len(pl.scan_parquet(selected.canonical).collect_schema()) == 38
    raw = {r['path'] for r in selected.provenance['raw']}
    assert 'osha/summary/summary_data_dictionary.pdf' in raw
    assert 'osha/summary/ITA_Data_Dictionary.pdf' in raw


@pytest.mark.parametrize('defect', [
    'detached_hash', 'file_hash', 'size', 'missing_file', 'extra_file',
    'schema', 'row_count', 'raw_bytes', 'source_hash', 'source_order',
    'canonical_order', 'native_flags', 'native_node_level', 'geography_edge',
])
def test_selected_input_defects_are_refused(tmp_path, defect):
    from target_fixtures import corrupt_selected, seed_inputs

    selected = seed_inputs(tmp_path)
    corrupt_selected(tmp_path, selected, defect)
    with pytest.raises((ValueError, FileNotFoundError)):
        selected.verify(tmp_path)
```

`corrupt_selected(data_dir, selected, defect) -> None` owns exact test mutations: alter the named pin/file/stat/schema/report/raw/source/canonical/graph property, recomputing lower-level inventories only when testing a higher-level semantic defect. Preserve the original expected detached checksum except where a test deliberately supplies a new checksum to reach semantic validation. Add direct tests that unrelated raw manifest appends succeed, cited entry changes fail, fixture checksum omission fails, symlink/unsafe/occupied paths fail, and round-trip inventory order is stable.

- [ ] **Step 2: Run red.**

Run: `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_target_io.py tests/test_target_inputs.py -q`.

Expected: import/API failure for the new target modules; existing code/geography tests still collect. A fixture setup failure unrelated to the proposed API is not the intended red signal.

- [ ] **Step 3: Implement strict I/O and selected-input verification.** The inventory primitives are:

```python
def file_record(file: Path) -> dict:
    record = {'sha256': manifest.sha256_file(file), 'size': file.stat().st_size}
    if file.suffix == '.parquet':
        frame = pl.scan_parquet(file)
        record.update(rows=frame.select(pl.len()).collect().item(),
                      columns=list(frame.collect_schema()),
                      schema={c: str(t) for c, t in frame.collect_schema().items()})
    return record


def write_json(file: Path, value: object) -> None:
    file.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                               allow_nan=False) + '\n', encoding='utf-8')


def verify_raw(data_dir: Path, citations: list[dict]) -> list[dict]:
    manifest_file = paths.manifest_path(data_dir)
    verified = []
    for citation in sorted(citations, key=lambda r: r['path']):
        file = manifest_file.parent / citation['path']
        current = json.loads(json.dumps(asdict(manifest.entry_for(manifest_file, file))))
        if current != citation:
            raise ValueError(f'{file}: cited raw provenance changed')
        verified.append(current)
    return verified


def require_source_parity(summary: Path, canonical: Path) -> None:
    left = pl.scan_parquet(summary).with_row_index('_row')
    right = pl.scan_parquet(canonical).select(ita_summary.COLUMNS).with_row_index('_row')
    if left.collect_schema() != right.collect_schema():
        raise ValueError('canonical source prefix schema differs')
    joined = left.join(right, on='_row', how='full', coalesce=True, suffix='_canonical',
                       validate='1:1')
    different = pl.any_horizontal([
        pl.col(c).ne_missing(pl.col(c + '_canonical')) for c in ita_summary.COLUMNS
    ])
    n_left = left.select(pl.len()).collect().item()
    n_right = right.select(pl.len()).collect().item()
    if n_left != n_right or joined.filter(different).select(pl.len()).collect().item():
        raise ValueError('source/canonical physical row order or multiplicity differs')
```

`stage` uses regex `[A-Za-z0-9][A-Za-z0-9_-]*`, Stage 5 `safe_path`/`occupied`, exclusive `staging.mkdir()` and no cleanup of somebody else's staging. `inventory` sorts exact relative POSIX file paths, excludes itself, and calls `file_record`. Allow the preparation's `requests/batch_00000.csv` relative paths; reject absolute paths, empty components, `..`, escapes and symlinked files/parents. `verify_inventory` requires exactly the supplied recursive file set, compares each required field and Parquet physical column order; dictionary equality alone does not establish order. Preserve schema order with an explicit list of column names alongside JSON's sorted schema mapping. Existing upstream reports lack that list: compare actual column order to imported schema constants.

`select` pins production identities/checksums exactly as the spec states. Load inventories only after verifying detached hashes, require twelve Stage 4 Parquets plus `inputs.json`/`report.json` (14 entries), and six Stage 5 Parquets plus those JSONs (8 entries). Reject extra/missing final files. For every Parquet compare actual hash/size with `outputs.json`, rows/schema with `report.json['tables']`, and exact ordered known schema. Build the Stage 4 schema map by importing `NODE_SCHEMA`, `EDGE_SCHEMA`, `PATH_SCHEMA`, relationship/rule/label/membership/lookup schemas and `{**SUMMARY_SCHEMA, **MAPPING_SCHEMA, **FILING_COLUMNS}`; use `geography_build.SCHEMAS` for Stage 5. Require `codes-ita-v1`, `geography-v1`, matching input `run_id`, and Stage 5 reference-frame values.

Verify every raw citation from both bundles plus the documentary dictionaries; deduplicate by path only after asserting identical citations. Verify the source hash/size against Stage 4 `source_parquet` and actual source-file inventory. Check all canonical source files cite those raw releases, both 38-column schema and prefix parity, sorted nonnull candidate lists, unknown-vintage no-scalar/mismatch/crosswalk invariants, and native status consistency. For a native row require `naics_year=2022`, identical delivered/canonical six-digit code, singleton candidate equal to that code, matching NAICS 2022 national-industry node, and false crosswalk/ambiguity/unresolved flags. Native contradictions fail rather than being silently filtered.

Validate selected classification forests/paths and concordance endpoint membership with existing validators; validate the geography graph with `validate_graph`, typed county/CBSA reference memberships against its edges/nodes, and exact HUD lookup equality to `geography_hud.lookup(hud_zip_county)`. This verifies both all-positive cardinality and eligible fallback membership. Do not call the classification forest validator on geography. Reconstruct small reference expectations if necessary; do not rebuild or rewrite any selected bundle. `SelectedInputs.verify` repeats pinned byte and semantic checks at preparation/build publication boundaries.

- [ ] **Step 4: Run green and the upstream fixture regressions.**

Run: `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_target_io.py tests/test_target_inputs.py tests/test_code_build.py tests/test_geography_build.py -q`.

Expected: all selected-input mutations fail before any publication; all unchanged upstream tests pass. Record actual test count/output.

- [ ] **Step 5: Commit.**

```bash
git add src/embedding_data/target_io.py src/embedding_data/target_inputs.py tests/code_fixtures.py tests/target_fixtures.py tests/test_target_io.py tests/test_target_inputs.py
git commit -m "feat(targets): verify selected code and geography inputs"
```

### Task 2: Freeze all-year row identity and deterministic Census requests

**Files:** Create `src/embedding_data/ita_assignment_prepare.py`, `tests/test_ita_assignment_prepare.py`. Extend `tests/target_fixtures.py` with submitted-tuple edge cases only.

**Interfaces:** Consumes `SelectedInputs` and Task 1 I/O. Produces `prepare(data_dir: Path, assignment_run_id: str, codes_run: str, geography_run: str, *, codes_outputs_sha256: str | None = None, geography_outputs_sha256: str | None = None) -> Path`; `check_preparation(data_dir: Path, assignment_run_id: str) -> PreparedInputs`; `request_id(fields: tuple[str, str, str, str]) -> str`; `validate_batch(file: Path, request_index: pl.DataFrame) -> list[str]`.

`PreparedInputs` is a frozen dataclass with `directory: Path`, `selected: SelectedInputs`, `inputs: dict`, `source_index: Path`, `request_index: Path`, `batches: tuple[Path, ...]`. `check_preparation` is read-only and returns only after inventory, software, selected input, row/request and CSV validation. Both acquisition and offline build call it. Fixture helper `prepared_tree(data_dir: Path, *, batch_limit: int = 10_000) -> PreparedInputs` composes `seed_inputs` and preparation. For small boundary tests it uses `unittest.mock.patch.object` around preparation's batch-limit constant only during creation, recording that limit in preparation metadata; verification reconstructs slices from that frozen limit and still enforces the service maximum of 10,000.

- [ ] **Step 1: Write identity and batching failures.**

Preparation fingerprints acquisition/assignment implementation files that land in Tasks 3–4. Keep this task independently testable without adding placeholder production modules: put the shared implementation-registry helper in `tests/target_fixtures.py` and install its local autouse wrapper **only in `tests/test_ita_assignment_prepare.py`** (D3). Its record uses the exact test registry and actual hashes; `check_preparation` compares against that same registry. Once the files exist, the fixture naturally includes them. Production always requires the complete constant tuple; Task 7's tests do not install this fixture.

```python
def install_implemented_software_boundary(monkeypatch):
    import importlib.util
    from embedding_data import ita_assignment_prepare as preparation

    modules = tuple(name for name in preparation.FROZEN_MODULES
                    if importlib.util.find_spec('embedding_data.' + name) is not None)
    monkeypatch.setattr(preparation, 'FROZEN_MODULES', modules)
```

The local test-module wrapper is:

```python
@pytest.fixture(autouse=True)
def implemented_software_boundary(monkeypatch):
    from target_fixtures import install_implemented_software_boundary

    install_implemented_software_boundary(monkeypatch)
```

```python
def test_submission_identity_keeps_multiplicity_and_exact_strings(tmp_path):
    from target_fixtures import seed_inputs
    from embedding_data.ita_assignment_prepare import prepare

    selected = seed_inputs(tmp_path)
    directory = prepare(tmp_path, 'requests', 'fixture_codes', 'fixture_geography',
                        codes_outputs_sha256=selected.provenance['codes']['outputs_sha256'],
                        geography_outputs_sha256=selected.provenance['geography']['outputs_sha256'])
    source = pl.read_parquet(selected.canonical)
    index = pl.read_parquet(directory / 'source_index.parquet')
    requests = pl.read_parquet(directory / 'request_index.parquet')
    assert index.schema == {'source_row': pl.UInt64, 'request_id': pl.String}
    assert index['source_row'].to_list() == list(range(source.height))
    assert requests['n_source_rows'].sum() == source.height
    assert index.height == source.height
    assert requests['request_id'].n_unique() == requests.height
    duplicate_rows = source.with_row_index('source_row').filter(pl.col('id').eq(23001))
    assert duplicate_rows.height == 2
    assert index.filter(pl.col('source_row').is_in(duplicate_rows['source_row'].to_list()))[
        'request_id'].n_unique() == 1


def test_linkage_equivalent_delivered_strings_have_distinct_requests():
    from embedding_data.ita_assignment_prepare import request_id

    assert request_id(('1 Main St', 'Town', 'AL', '00001')) != request_id(
        ('1 MAIN ST', 'Town', 'AL', '00001'))
    assert request_id(('1 Main St ', 'Town', 'AL', '00001')) != request_id(
        ('1 Main St', 'Town', 'AL', '00001'))
    assert request_id(('a,b', 'c', '', '')) != request_id(('a', 'b,c', '', ''))
```

Add tests for null→empty submission equivalence while source nulls survive, Unicode/quotes/newlines, ZIP+4 and invalid ZIP normalization, incomplete and delivered-excluded tuples still requested, forced request-hash collision, 10,001 distinct tuples yielding 10,000+1 requests, headerless UTF-8 CSV exact field order, and corrupted/missing/index/batch/software/lock/dependency inputs. Inject a constant hash function to prove collision detection compares tuples, not just request counts. A change confined to estimator implementation is allowed; change to assignment/preparation dependencies fails. A later unrelated manifest append succeeds.

- [ ] **Step 2: Run red.**

Run: `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_ita_assignment_prepare.py -q`.

Expected: new preparation API missing; no Census request and no source rebuild.

- [ ] **Step 3: Implement identity/index preparation and complete frozen inventories.** Use these exact physical schemas/serialization:

```python
IDENTITY_VERSION = 'ita-request-v1'
SCHEMA_VERSION = 'ita-assignment-inputs-v1'
SUBMITTED = ['street', 'city', 'state', 'zip']
SOURCE_INDEX_SCHEMA = {'source_row': pl.UInt64, 'request_id': pl.String}
REQUEST_INDEX_SCHEMA = {
    'request_id': pl.String, **{c: pl.String for c in SUBMITTED},
    'n_source_rows': pl.UInt64,
}


def request_id(fields: tuple[str, str, str, str]) -> str:
    payload = json.dumps(list(fields), ensure_ascii=False, separators=(',', ':'),
                         allow_nan=False).encode('utf-8')
    return hashlib.sha256(IDENTITY_VERSION.encode('ascii') + b'\0' + payload).hexdigest()


def request_frames(canonical: pl.LazyFrame) -> tuple[pl.LazyFrame, pl.LazyFrame]:
    submitted = canonical.with_row_index('source_row').with_columns(
        pl.col('source_row').cast(pl.UInt64),
    ).select(
        'source_row', pl.col('street_address').fill_null('').alias('street'),
        pl.col('city').fill_null(''), pl.col('state').fill_null(''),
        pl.col('zip_code').map_elements(zip_key, return_dtype=pl.String).fill_null('').alias('zip'),
    )
    requests_frame = submitted.group_by(SUBMITTED).agg(
        n_source_rows=pl.len().cast(pl.UInt64),
    ).with_columns(request_id=pl.struct(SUBMITTED).map_elements(
        lambda row: request_id(tuple(row[c] for c in SUBMITTED)), return_dtype=pl.String,
    )).select(list(REQUEST_INDEX_SCHEMA)).sort('request_id').collect()
    if requests_frame['request_id'].n_unique() != requests_frame.height:
        raise ValueError('request ID collision between distinct submitted tuples')
    requests = requests_frame.lazy()
    source_index = submitted.join(requests.select('request_id', *SUBMITTED),
                                  on=SUBMITTED, how='left', validate='m:1').select(
        list(SOURCE_INDEX_SCHEMA)).sort('source_row')
    return source_index, requests
```

Import `zip_key` from `ita_verification`; do not use NFKC/casefold/linkage helpers. Materialize the request index once before joining it back, so the Python SHA callback runs once per unique tuple. Sink `source_index.parquet` in physical source order, request index in request-ID order. `source_row` is associated with the pinned canonical SHA-256 in `inputs.json`, never represented as a globally unique establishment key.

Write `requests/batch_00000.csv`, numbered from zero, with `csv.writer` over slices of at most the existing `BATCH_LIMIT=10_000`, `newline=''`, UTF-8, default CSV quoting, no header, `[request_id, street, city, state, zip]`. For `validate_batch`, `csv.reader` must find exactly five strings, a nonempty 64-character lowercase hex ID per row, no repeated IDs, no header, the exact frozen request-index tuples and their recomputed IDs in expected sorted contiguous slices. Return IDs in CSV order. Empty request files fail. Confirm total `n_source_rows` equals canonical row count and source-index height, source row indices are exactly contiguous/nonduplicated, every mapping references one request, and request-group counts agree with the index.

`inputs.json` records contract/identity/ZIP-normalization versions, canonical source key/hash, both selected detached inventories and transitive verified raw citations, implementation/dependency/Python/lock hashes, exact source/request index hashes, per-batch path/hash/size/row count, source years/totals and distinct request count. `outputs.json` inventories `inputs.json`, both Parquets and every request file, excludes itself and rejects extra files. Freeze preparation/assignment modules plus reused identity/parser/reference/manifest dependencies as a named software contract; record CLI/entry-point hashes separately. Use canonical JSON, include a reproducible execution commit, and record whether fixture inputs were used.

Use this explicit dependency inventory (hash each module's actual `__file__` under the execution checkout; do not hash `.pyc` files). Freeze Python and installed `embedding-data`, `polars`, `fastexcel`, `httpx`, `typer` versions plus `uv.lock` SHA-256. CLI/entry-point hashes are recorded for provenance; the enforced preparation contract is the following implementation set, with estimator/writer modules deliberately separate:

```python
FROZEN_MODULES = (
    'target_io', 'target_inputs', 'ita_assignment_prepare', 'ita_assignment_acquire',
    'ita_assignment', 'ita_verification', 'ita_county_verification', 'ita_verification_run',
    'ita_references', 'geography_hud', 'geography_tables', 'geography_parsers',
    'geography_references', 'geography_build', 'classification_tables', 'code_build',
    'code_references', 'filing_rules', 'ita_naics_mapping', 'naics_relationships',
    'ita_summary', 'ita_catalog', 'osha_encoding', 'osha_benchmark_download', 'manifest', 'paths',
)
TARGET_MODULES = ('target_contract', 'ita_area_mix', 'ita_target_build', 'targets_cli', 'cli')
```

Target-run provenance hashes the union of both groups. Resume/build compare the frozen group and its dependency contract; rebuilding an estimator alone records the new target group without retroactively altering preparation's frozen inventory.

`check_preparation` verifies the detached inventory and all indexes/CSV contracts, software dependency/lock versions, selected input bytes and hashes on every call. It recomputes the source-to-submitted mapping against the canonical source without modifying it. Reject unsupported versions or a source-year inventory other than exactly 2016–2025. Before rename, repeat selected/cited/software checks and confirm no occupied final name appeared. Leave failed staging intact.

- [ ] **Step 4: Run green.**

Run: `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_ita_assignment_prepare.py tests/test_target_inputs.py -q`.

Expected: exact identity/order/count checks pass; every corrupted or mixed-software preparation refuses resume/build; no HTTP client is called.

- [ ] **Step 5: Commit.**

```bash
git add src/embedding_data/ita_assignment_prepare.py tests/test_ita_assignment_prepare.py tests/target_fixtures.py
git commit -m "feat(ita): freeze full-table Census request identities"
```

### Task 3: Acquire and resume immutable full-table Census evidence

**Files:** Create `src/embedding_data/ita_assignment_acquire.py`, `tests/test_ita_assignment_acquire.py`. Extend `tests/target_fixtures.py` with a real `httpx.MockTransport` Census protocol fixture.

**Interfaces:** Consumes `check_preparation`, exact frozen request files and the existing Census parser/client constants. Produces `acquire(data_dir: Path, assignment_run_id: str) -> Path`, returning the completed acquisition inventory; `read_evidence(data_dir: Path, prepared: PreparedInputs) -> Evidence`, fully offline; and `parse_response(text: str, expected_ids: list[str]) -> pl.DataFrame`.

`Evidence` is a frozen dataclass with `responses: pl.LazyFrame` (nonnull unique `request_id`, `geocode_status`, nullable `match_type`, `geocode_county_geoid`, all String), `provenance: dict`, and `verify() -> None`. `responses` is formed from verified batch-sized parsed frames, concatenated without a source-row join; the builder joins it m:1 to the row index. Record methods/options/times separately in provenance.

- [ ] **Step 1: Write acquisition, cache/resume and malformed-response tests.** `target_fixtures.census_client(requests: list[dict], *, fail_batch: int | None = None) -> httpx.Client` serves catalogs with deliberately nonhistorical IDs (benchmark `7`, vintage `999`) and generates valid original response CSVs from uploaded request IDs. It chooses fixture outcomes by exact submitted street strings. Patch the acquisition module's `make_client`; exercise the real form construction, parser and receipts.

This test module also needs the local software boundary until Task 4's assignment implementation exists. Add the explicit local wrapper directly in `tests/test_ita_assignment_acquire.py` using the shared helper from Task 2 (D3); do not install it in global conftest or invoke it from the V12 fixture path:

```python
@pytest.fixture(autouse=True)
def implemented_software_boundary(monkeypatch):
    from target_fixtures import install_implemented_software_boundary

    install_implemented_software_boundary(monkeypatch)
```

```python
def test_sequential_resume_preserves_first_receipt(tmp_path, monkeypatch):
    from target_fixtures import prepared_tree, census_client
    from embedding_data import ita_assignment_acquire as acquisition

    prepared = prepared_tree(tmp_path, batch_limit=3)
    calls = []
    monkeypatch.setattr(acquisition, 'make_client',
                        lambda: census_client(calls, fail_batch=1))
    with pytest.raises(httpx.TransportError):
        acquisition.acquire(tmp_path, 'fixture_assignment')
    raw = tmp_path / 'raw/references/census-geocoder/ita-assignment/fixture_assignment'
    receipts = sorted(raw.glob('*.receipt.json'))
    assert len(receipts) == 1
    original = receipts[0].read_bytes()
    monkeypatch.setattr(acquisition, 'make_client', lambda: census_client(calls))
    completion = acquisition.acquire(tmp_path, 'fixture_assignment')
    assert completion.exists()
    assert receipts[0].read_bytes() == original
    posts = [c for c in calls if c['method'] == 'POST']
    assert all(c['benchmark'] == '7' and c['vintage'] == '999' for c in posts)
    assert sum(c['request_sha256'] == posts[0]['request_sha256'] for c in posts) == 1
    monkeypatch.setattr(acquisition, 'make_client',
                        lambda: pytest.fail('cached acquisition opened a client'))
    acquisition.acquire(tmp_path, 'fixture_assignment')
    assert acquisition.read_evidence(tmp_path, prepared).responses.collect().height > 0


@pytest.mark.parametrize('body', [
    'wrong,"",No_Match\n', 'one,"",No_Match\none,"",No_Match\n',
    'one,"",Match,Exact\n', 'one,"",Unknown\n', ',"",No_Match\n', '',
    'one,"",No_Match\nextra,"",No_Match\n',
])
def test_response_defects_fail_instead_of_becoming_unmatched(body):
    from embedding_data.ita_assignment_acquire import parse_response

    with pytest.raises(ValueError):
        parse_response(body, ['one'])
```

Add missing/ambiguous catalog-name cases, no assumed historical option IDs, extra/missing/repeated/malformed response IDs, response hash/size changes, request or catalog/selection/receipt tampering, incomplete raw `.part`, occupied/unrecorded raw files, no client construction on fully cached acquisition, interrupted partial batch, changed software, and missing completion inventory. Every failure identifies run/batch/path without echoing submitted strings. Verify any validation error stops immediately with no subsequent batch call and no cited invalid response.

Test the publication crash windows explicitly: a manifested valid response with a missing receipt may complete its receipt from the already frozen selection and original manifest time; an unrecorded published response or receipt is refused, never overwritten/re-downloaded. Missing or changed previously manifested bytes are refused. A recorded receipt absent from disk also fails. Earlier Stage 3 verification files are never used as an implicit cache.

- [ ] **Step 2: Run red.**

Run: `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_ita_assignment_acquire.py -q`.

Expected: missing acquisition API. MockTransport handles explicit fixture acquisition only; preparation remains offline.

- [ ] **Step 3: Implement the protocol adapter and per-batch receipt state machine.**

```python
def parse_response(text: str, expected_ids: list[str]) -> pl.DataFrame:
    frame = parse_geocodes(text)
    if (len(expected_ids) != len(set(expected_ids)) or
            frame.height != len(expected_ids) or
            set(frame['row_key']) != set(expected_ids)):
        raise ValueError('Census response IDs do not exactly cover frozen batch')
    return frame.rename({'row_key': 'request_id',
                         'county_geoid': 'geocode_county_geoid'}).sort('request_id')


def choose_options(benchmarks: dict, vintages: dict) -> dict:
    benchmark = [r for r in benchmarks['benchmarks'] if r['benchmarkName'] == BENCHMARK]
    vintage = [r for r in vintages['vintages'] if r['vintageName'] == VINTAGE]
    if len(benchmark) != 1 or len(vintage) != 1:
        raise ValueError('required Census benchmark/vintage unavailable or ambiguous')
    return {'benchmark_name': BENCHMARK, 'benchmark_id': str(benchmark[0]['id']),
            'vintage_name': VINTAGE, 'vintage_id': str(vintage[0]['id'])}
```

Use `GEOCODER`, `BENCHMARK='Public_AR_Current'`, `VINTAGE='ACS2025_Current'` and `make_client` from Stage 3, without changing them. Download `/benchmarks` first, uniquely resolve the benchmark, then `/vintages?benchmark=<returned_id>`; snapshot catalogs under this assignment's raw namespace. Factor catalog selection so duplicate/missing benchmark names fail before requesting vintages. Validate catalog JSON structure and IDs as nonempty scalar strings/numbers. Freeze `catalog-selection.json` with verified catalog citations, names/IDs, first-invocation `acquisition_started_at` and preparation detached hash **before the first POST**. Existing selection requires matching preparation and verified original catalogs; never reselect from the live service during resume.

For each sorted frozen batch, use `<request_sha256>.csv` and `<request_sha256>.receipt.json` under `raw/references/census-geocoder/ita-assignment/<assignment_run_id>/`. Match Stage 3's POST exactly: `files={'addressFile': (request.name, file_handle, 'text/csv')}`, `data={'benchmark': selected_id, 'vintage': selected_id}`, endpoint `/geographies/addressbatch`. Read from the frozen request file; do not reconstruct a slightly different POST body or change an address. Keep requests sequential, 600-second client behavior, no retry loop.

The response is validated before publication; publish using exclusive `.part` creation, safe destination checks, byte-length verification when a Content-Length is provided, no-overwrite final publication (the Stage 5 exclusive-file/hard-link convention), then `record_download`. Receipt fields are:

```python
def batch_receipt(prepared: PreparedInputs, request: Path, selection: Path,
                  options: dict, response_entry: dict) -> dict:
    expected_ids = validate_batch(request, pl.read_parquet(prepared.request_index))
    return {
        'schema_version': 'ita-assignment-receipt-v1',
        'assignment_run_id': prepared.directory.name,
        'preparation_outputs_sha256': manifest.sha256_file(prepared.directory / 'outputs.json'),
        'request': {'path': request.relative_to(prepared.directory).as_posix(),
                    **file_record(request), 'rows': len(expected_ids)},
        'selection_sha256': manifest.sha256_file(selection),
        'options': options, 'response': response_entry,
        'acquired_at': response_entry['retrieved_at'],
    }
```

Store the full normalized ManifestEntry under `response`. Record generated selection/receipt JSONs in the raw manifest with an explicit generated-metadata client identity and no claim that these JSONs came from Census. Every raw acquisition time is the response's original `retrieved_at`, not resume/build time. Preserve it byte-for-byte in an existing receipt.

On resume, validate preparation/software first, then all present catalogs/selection/responses/receipts and exact IDs before fetching anything missing. If a valid manifested response exists without a receipt, reconstruct its receipt only from the preexisting immutable selection and the original response ManifestEntry; do not invent an acquisition time. An existing unrecorded file requires inspection; do not silently adopt it. Validate every existing expected artifact before constructing a client; fully cached completion returns without opening one.

When all batches verify, publish manifest-covered `acquisition.json` containing sorted request/receipt/catalog/selection/response inventories, min/max original response acquisition times, original selection's acquisition start and successful completion end. Do not rewrite it on cached calls. A failed invocation may leave valid completed batches; no completion inventory claims missing batches. `read_evidence` requires completion, verifies every hash/size/citation/option/request ID afresh, reparses responses offline, and proves union coverage is exactly the distinct request index. It exposes no-match/tie as retained parser states. Record the mutable Current-frame limit verbatim from the spec in acquisition and target provenance.

- [ ] **Step 4: Run green and the first full milestone checkpoint.**

Run: `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_ita_assignment_acquire.py tests/test_ita_assignment_prepare.py tests/test_ita_verification_run.py -q`, then the full pytest/Behave/ruff/lock command group above.

Expected: fixture acquisitions/resume/replay pass, invalid batches never publish an original response/receipt as valid, and all Stage 3 tests remain unchanged/passing. Record results and any deviations before proceeding.

- [ ] **Step 5: Commit.**

```bash
git add src/embedding_data/ita_assignment_acquire.py tests/test_ita_assignment_acquire.py tests/target_fixtures.py
git commit -m "feat(ita): acquire resumable Census assignment evidence"
```

### Task 4: Assign counties without dropping or multiplying source rows

**Files:** Create `src/embedding_data/ita_assignment.py`, `tests/test_ita_assignment.py`. Add a rule-matrix builder to `tests/target_fixtures.py`.

**Interfaces:** Consumes canonical LazyFrame, frozen `source_index`, unique parsed evidence, selected HUD lookup and county references. Produces `assign(canonical: pl.LazyFrame, source_index: pl.LazyFrame, responses: pl.LazyFrame, hud_lookup: pl.DataFrame, counties: pl.DataFrame) -> pl.LazyFrame`; `assignment_schema(canonical_schema: pl.Schema) -> dict`; `validate_assignments(frame: pl.LazyFrame, canonical: pl.LazyFrame, counties: pl.DataFrame) -> None`; `assignment_report(frame: pl.LazyFrame) -> dict`. Contract version is `ita-assignment-v1`.

- [ ] **Step 1: Write the explicit rule matrix and row/schema preservation tests.** The fixture helper `assignment_case(census_status, match_type, returned_county, zip_code, state)` returns the actual assigned single row using selected fixture references. The following expected outcomes are handwritten:

```python
@pytest.mark.parametrize('status,kind,returned,zip_code,state,method,chosen', [
    ('Match', 'Exact', '01001', '00003', 'AL', 'census_exact', '01001'),
    ('Match', 'Exact', '01001', '00005', 'AL', 'census_exact', '01001'),
    ('Match', 'Non_Exact', '51510', '00001', 'AL', 'hud_singleton', '01001'),
    ('No_Match', None, None, '00001', 'AL', 'hud_singleton', '01001'),
    ('Tie', None, None, '00001', 'AL', 'hud_singleton', '01001'),
    ('Match', 'Exact', '01999', '00001', 'AL', 'hud_singleton', '01001'),
    ('Match', 'Exact', '09001', '00001', 'AL', 'hud_singleton', '01001'),
    ('Match', 'Exact', '72001', '00001', 'AL', 'unassigned', None),
    ('Match', 'Exact', '01001', '00001', ' PR ', 'unassigned', None),
    ('No_Match', None, None, '00003', 'AL', 'unassigned', None),
    ('No_Match', None, None, '00002', 'AL', 'unassigned', None),
    ('No_Match', None, None, '99999', 'AL', 'unassigned', None),
    ('Match', 'Exact', '51001', '99999', 'VA', 'census_exact', '51001'),
    ('Match', 'Exact', '09110', '99999', 'CT', 'census_exact', '09110'),
])
def test_adopted_county_precedence(status, kind, returned, zip_code, state, method, chosen):
    from target_fixtures import assignment_case

    row = assignment_case(status, kind, returned, zip_code, state)
    assert row['assignment_method'] == method
    assert row['county_geoid'] == chosen
```

Also assert all six territory prefixes, returned-county flags independent of exactness, usable Census despite excluded/ambiguous HUD, original candidate lists/flags preserved, tied maxima never choose, zero-business versus absent defaults, legacy CT independent from incompatibility, unexpected in-scope county, complete/partial/blank requests, metro/micro/non-CBSA and cross-state CBSA attributes. Exact source-prefix equality/order, UInt64 index continuity and row counts must survive duplicate source rows and repeated establishment IDs. Overlapping schema names, response/index fanout or missing request coverage fail rather than manufacturing `No_Match`.

- [ ] **Step 2: Run red.**

Run: `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_ita_assignment.py -q`.

Expected: assignment API missing; existing Stage 3 report behavior is not patched to satisfy these tests.

- [ ] **Step 3: Implement lazy joins and the exact precedence.** Establish the schema in this order: all 38 canonical fields; `source_row`, `request_id`; `zip_key`, `geocode_status`, `match_type`, `geocode_county_geoid`; all `LOOKUP_SCHEMA` fields except `zip_key`; all `COUNTY_SCHEMA` fields; `assignment_method`, `assignment_reason`; the six new flags in spec order. Detect overlaps before joining.

Add a temporary contiguous row index to the canonical scan, cast UInt64 and join the frozen source index `1:1`; join responses `m:1` on request ID with full expected-coverage checks. Normalize ZIP only through existing `zip_key`. Left join the selected HUD table `m:1`. For absent joins, fill lookup counts with typed Int64 zero, list fields with `pl.lit([], dtype=pl.List(pl.String))`, lookup Boolean flags with false, status with `'absent'`, and scalar candidate/max/fallback fields with null. Do not fill other source Boolean nulls.

The chosen county expression is:

```python
def county_choice(inventory: list[str]) -> tuple[pl.Expr, pl.Expr, pl.Expr]:
    delivered_veto = pl.col('flag_delivered_state_out_of_scope')
    exact = pl.col('geocode_status').eq('Match').and_(pl.col('match_type').eq('Exact')).fill_null(False)
    excluded = pl.col('flag_geocode_county_out_of_scope')
    compatible = pl.col('geocode_county_geoid').is_in(inventory).fill_null(False)
    hud = pl.col('eligibility_status').eq('eligible')
    choice = (pl.when(delivered_veto).then(pl.lit(None, dtype=pl.String))
              .when(exact.and_(excluded)).then(pl.lit(None, dtype=pl.String))
              .when(exact.and_(compatible)).then(pl.col('geocode_county_geoid'))
              .when(hud).then(pl.col('zip_fallback_county'))
              .otherwise(pl.lit(None, dtype=pl.String)))
    method = (pl.when(delivered_veto.or_(exact.and_(excluded))).then(pl.lit('unassigned'))
              .when(exact.and_(compatible)).then(pl.lit('census_exact'))
              .when(hud).then(pl.lit('hud_singleton')).otherwise(pl.lit('unassigned')))
    reason = (pl.when(delivered_veto).then(pl.lit('delivered_state_out_of_scope'))
              .when(exact.and_(excluded)).then(pl.lit('exact_census_out_of_scope'))
              .when(exact.and_(compatible)).then(pl.lit('exact_census_compatible'))
              .when(hud).then(pl.lit('eligible_hud_singleton'))
              .otherwise(pl.concat_str(pl.lit('no_compatible_county:'),
                                       pl.col('eligibility_status'))))
    return choice, method, reason
```

Delivered-state veto uses `.str.strip_chars().str.to_uppercase().is_in(['PR','VI','GU','AS','MP','UM']).fill_null(False)` only for the scope decision. Raw delivered state remains untouched. Returned-county scope uses the six prefixes for **every** parsed county; incompatible is nonnull, in-scope and absent from selected inventory; legacy CT uses Stage 5's `^090[0-9]{2}$` independently. `flag_request_incomplete` is any submitted field empty or whitespace-only after null substitution and ZIP normalization; this diagnostic may test `.str.strip_chars().eq('')`, while request serialization keeps the exact submitted strings. Add a whitespace-only delivered-field test. `flag_assignment_hud` is method equality. Required flags are nonnull Boolean.

Join the chosen geoid to selected `county_reference` with `validate='m:1'`, drop temporary choice/key columns, select the exact ordered schema, sort by `source_row`. Reject missing required county joins; all county reference fields are null when unassigned. Validate that source-row count/index/order and the canonical prefix are unchanged and all assigned attributes match the selected reference. Preserve optional null CBSA fields and both CBSA types/roles; derive no scalar CBSA state parent.

`assignment_report` returns top-level `input_rows`, year-by-reason/method partitions summing exactly to source rows; separate raw geocode status/match-type coverage; separate delivered and returned scope partitions; and true/null counts for every Boolean diagnostic by year. Label reason partitions as disjoint and flags as overlapping. Include compatible exact, non-exact, tie, no-match and legacy/incompatible/out-of-scope diagnostics without interpreting them as county accuracy.

- [ ] **Step 4: Run green and retained geography regressions.**

Run: `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_ita_assignment.py tests/test_geography_hud.py tests/test_geography_tables.py tests/test_ita_county_verification.py -q`.

Expected: the rule matrix, exact 38-column prefix, appended schema/order and all independent flags pass; source row counts/multiplicity/order remain exact.

- [ ] **Step 5: Commit.**

```bash
git add src/embedding_data/ita_assignment.py tests/test_ita_assignment.py tests/target_fixtures.py
git commit -m "feat(ita): assign all source rows under adopted county rules"
```

### Task 5: Implement the family-independent targets-v1 contract and writer

**Files:** Create `src/embedding_data/target_contract.py`, `tests/test_target_contract.py`.

**Interfaces:** Consumes an exact-schema `pl.LazyFrame` or `pl.DataFrame`. Produces ordered constants `TARGET_SCHEMA`, `TARGET_KEY_COLUMNS`, `SCHEMA_VERSION='targets-v1'`; `validate_targets(frame: pl.LazyFrame) -> None`; `write_targets(frame: pl.LazyFrame, destination: Path) -> dict`, returning the published Parquet file record. This writes only a file within the caller's staging directory; Task 7 owns run publication and manifest construction.

- [ ] **Step 1: Write general contract tests independent of ITA eligibility.** Define `target_fixtures.target_rows() -> pl.DataFrame` with this valid exact typed fixture. Test every required column/type/order, null/blank metadata, invalid/mismatched typed IDs, null/nonfinite value/count, nonfinite/negative SE, duplicate keys even when estimate/count/flags differ, null flags/list elements, blank flag strings, and unsorted/duplicate flags. The validator rejects noncanonical flag lists; producers must supply sorted/distinct lists before writing.

```python
def target_rows() -> pl.DataFrame:
    from embedding_data.target_contract import TARGET_SCHEMA

    rows = []
    for code, share, count in [('111111', 0.75, 3), ('111112', 0.25, 1)]:
        rows.append({
            'source': 'fixture', 'family': 'area_mix',
            'unit_a_type': 'county', 'unit_a': 'geography:2025:county:01001',
            'unit_b_type': 'naics_national_industry',
            'unit_b': 'naics:2022:national_industry:' + code,
            'measure': 'fixture_share', 'value': share, 'se': None, 'se_method': 'none',
            'n_unweighted': count, 'n_weighted': float(count), 'sample_set': 'fixture',
            'vintage': 'naics=2022;county=2025', 'universe': 'Fixture conditional universe',
            'flags': [],
        })
    return pl.DataFrame(rows, schema=TARGET_SCHEMA)
```

```python
def test_writer_has_general_se_and_feature_semantics(tmp_path):
    from target_fixtures import target_rows
    from embedding_data.target_contract import TARGET_SCHEMA, write_targets

    frame = target_rows().head(1).with_columns(
        pl.lit('worker_profile').alias('family'),
        pl.lit('age').alias('unit_b_type'), pl.lit('feature:age:mean').alias('unit_b'),
        pl.lit('mean_age').alias('measure'), pl.lit(42.5).alias('value'),
        pl.lit(1.2, dtype=pl.Float64).alias('se'), pl.lit('replicate').alias('se_method'),
        pl.lit(10.5).alias('n_weighted'), pl.lit([], dtype=pl.List(pl.String)).alias('flags'),
    )
    output = tmp_path / 'target.parquet'
    write_targets(frame.lazy(), output)
    result = pl.read_parquet(output)
    assert result.schema == TARGET_SCHEMA
    assert result['value'].item() == 42.5
    assert result['n_weighted'].item() == 10.5


@pytest.mark.parametrize('method,se,valid', [
    ('none', None, True), ('none', 0.0, False),
    ('replicate', 0.0, True), ('replicate', None, False),
    ('bootstrap', 0.5, True), ('bootstrap', -1.0, False),
    ('other', None, False),
])
def test_shared_se_contract(method, se, valid):
    from target_fixtures import target_rows
    from embedding_data.target_contract import validate_targets

    frame = target_rows().with_columns(pl.lit(method).alias('se_method'),
                                       pl.lit(se, dtype=pl.Float64).alias('se'))
    if valid:
        validate_targets(frame.lazy())
    else:
        with pytest.raises(ValueError):
            validate_targets(frame.lazy())
```

The profile-like row above tests a generic writer interface only; it is not a profile estimator or evidence that a later family exists. Add shuffled-input deterministic sort and serialized read-back tests. Do not impose a [0,1] range, integer weighted counts, observed-leaf lookup or minimum support in this shared module.

- [ ] **Step 2: Run red.**

Run: `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_target_contract.py -q`.

Expected: target contract missing.

- [ ] **Step 3: Implement the exact long schema and generic checks.**

```python
SCHEMA_VERSION = 'targets-v1'
TARGET_SCHEMA = {
    'source': pl.String, 'family': pl.String,
    'unit_a_type': pl.String, 'unit_a': pl.String,
    'unit_b_type': pl.String, 'unit_b': pl.String, 'measure': pl.String,
    'value': pl.Float64, 'se': pl.Float64, 'se_method': pl.String,
    'n_unweighted': pl.UInt64, 'n_weighted': pl.Float64,
    'sample_set': pl.String, 'vintage': pl.String, 'universe': pl.String,
    'flags': pl.List(pl.String),
}
TARGET_KEY_COLUMNS = [c for c in TARGET_SCHEMA
                      if c not in {'value', 'se', 'n_unweighted', 'n_weighted', 'flags'}]


def valid_unit(kind: str, value: str) -> bool:
    if value.startswith('feature:'):
        parts = value.split(':', 2)
        return len(parts) == 3 and parts[1] == kind and bool(parts[2].strip())
    parts = value.split(':', 3)
    if len(parts) != 4 or not re.fullmatch(r'[0-9]{4}', parts[1]) or not parts[3].strip():
        return False
    system, level = parts[0], parts[2]
    return ((system == 'geography' and kind == level) or
            (system in {'naics', 'soc'} and kind == system + '_' + level))


def write_targets(frame: pl.LazyFrame, destination: Path) -> dict:
    validate_targets(frame)
    if destination.exists() or destination.is_symlink():
        raise ValueError(f'{destination}: target file already exists')
    frame.sort(TARGET_KEY_COLUMNS).sink_parquet(destination)
    published = pl.scan_parquet(destination)
    validate_targets(published)
    return file_record(destination)
```

`validate_targets` first compares exact ordered schema to `TARGET_SCHEMA` and rejects unexpected/missing/reordered/cast columns. All columns except `se` are nonnull, including the flags list and its elements. Every String metadata field has nonempty `.str.strip_chars()`. Apply `valid_unit` once per distinct `(unit_a_type, unit_a)` and `(unit_b_type, unit_b)` pair; this syntax/type check is intentionally independent of selected node membership. Family validators own actual systems/vintages/levels and reference membership. Check finite `value`, finite/nonnegative `n_weighted`, permitted methods and the exact SE nullability/domain rules. UInt64 enforces the physical unweighted-count domain. Check flags equal list-sort/list-unique canonical form and contain only nonempty strings. Group by all `TARGET_KEY_COLUMNS`, fail on any count above one. The writer must not silently cast types, repair metadata, merge duplicate rows or compute SEs. Return inventory of the actual serialized file and validate read-back order/schema/count.

- [ ] **Step 4: Run green.**

Run: `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_target_contract.py -q`.

Expected: exact schema/keys/SE/flags and future feature syntax pass; invalid cases fail for the stated contract, not an accidental exception.

- [ ] **Step 5: Commit.**

```bash
git add src/embedding_data/target_contract.py tests/test_target_contract.py tests/target_fixtures.py
git commit -m "feat(targets): add shared long-schema writer and validation"
```

### Task 6: Estimate conditional county industry shares and retain diagnostic support

**Files:** Create `src/embedding_data/ita_area_mix.py`, `tests/test_ita_area_mix.py`. Finalize `tests/target_fixtures.py`'s handwritten all-year golden dataset.

**Interfaces:** Consumes validated `ita-assignment-v1` LazyFrame, selected NAICS node table and year. Produces `estimate(assignments: pl.LazyFrame, nodes: pl.DataFrame, *, year: int = 2023) -> AreaMix`; `validate_area_mix(result: AreaMix, nodes: pl.DataFrame, counties: pl.DataFrame) -> None`; constants `DENOMINATOR_SCHEMA`, `FLAG_COUNT_SCHEMA`, `ESTIMATOR_VERSION='ita-area-mix-v1'`, `UNIVERSE`. `AreaMix` is a frozen dataclass with `targets: pl.LazyFrame`, `denominators: pl.LazyFrame`, `flag_counts: pl.LazyFrame`, `report: dict`.

**Golden fixture recipe:** `seed_inputs` uses these exact 2023 records in order. Start with `ita_fixtures.record`, override `id` and `establishment_id` with the shown ID, `naics_code`/`naics_year`, street/state/ZIP; use city `Fixture Town`. Other fields use ordinary valid fixture defaults. The duplicate row is an exact copy of its predecessor. For every other year 2016–2025, use one `111111` row at `Exact A`/AL/`00001`, with the year's delivered vintage (pre-2023 dictionary→2012; 2024/25 explicitly 2022). Thus the all-year fixture has 21 source rows. Reference titles remain explicitly synthetic fixtures.

| ID | NAICS / delivered vintage | Street / state / ZIP | Special fact |
| --- | --- | --- | --- |
| 23001 | 111111 / 2022 | Exact A / AL / 00001 | Ordinary native row |
| 23001 | 111111 / 2022 | Exact A / AL / 00001 | Exact duplicate, counted again |
| 23003 | 111112 / 2022 | Exact A / AL / 00001 | employees `0`, hours `-1`, size `1`; included despite diagnostics |
| 23004 | 111111 / 2022 | No match / AL / 00001 | HUD singleton supplies 01001 |
| 23005 | 111112 / 2022 | Exact B / VA / 00004 | Census supplies 51510 despite tied HUD |
| 23006 | 111111 / 2017 | Exact A / AL / 00001 | Singleton concordance excluded |
| 23007 | 999999 / 2022 | Exact A / AL / 00001 | Known-vintage mismatch excluded |
| 23008 | 111111 / 0 | Exact A / AL / 00001 | Unknown vintage singleton excluded |
| 23009 | 111111 / 2022 | No match / AL / 00003 | Mixed-scope multiple positive HUD counties; unassigned |
| 23010 | 111111 / 2022 | Exact excluded / AL / 00001 | Exact returned 72001 vetoes HUD |
| 23011 | 111111 / 2022 | Exact A / PR / 00001 | Delivered-state veto |
| 23012 | 111111 / 2017 | Exact C / VA / 99999 | Assigned 51001; county has zero eligible rows |

The mock Census service returns exact counties A=01001, B=51510, C=51001, excluded=72001; `No match` returns `No_Match`. Unknown non-golden strings used by identity tests return no-match; rule-matrix tests supply their own explicit responses. Build both selected fixture bundles from actual original-layout fixture inputs. Do not mutate a published canonical table to create ordinary golden data.

The exact source fixture implementation, added in Task 1, is:

```python
def golden_source_rows() -> dict[int, list[dict[str, str]]]:
    years = {year: [record(year, naics_code='111111', naics_year='2022',
                            street_address='Exact A', city='Fixture Town',
                            state='AL', zip_code='00001')]
             for year in range(2016, 2026)}
    specifications = [
        ('23001', '111111', '2022', 'Exact A', 'AL', '00001'),
        ('23001', '111111', '2022', 'Exact A', 'AL', '00001'),
        ('23003', '111112', '2022', 'Exact A', 'AL', '00001'),
        ('23004', '111111', '2022', 'No match', 'AL', '00001'),
        ('23005', '111112', '2022', 'Exact B', 'VA', '00004'),
        ('23006', '111111', '2017', 'Exact A', 'AL', '00001'),
        ('23007', '999999', '2022', 'Exact A', 'AL', '00001'),
        ('23008', '111111', '0', 'Exact A', 'AL', '00001'),
        ('23009', '111111', '2022', 'No match', 'AL', '00003'),
        ('23010', '111111', '2022', 'Exact excluded', 'AL', '00001'),
        ('23011', '111111', '2022', 'Exact A', 'PR', '00001'),
        ('23012', '111111', '2017', 'Exact C', 'VA', '99999'),
    ]
    years[2023] = [record(2023, id=identifier, establishment_id=identifier,
                          naics_code=code, naics_year=vintage, street_address=street,
                          city='Fixture Town', state=state, zip_code=zipcode)
                   for identifier, code, vintage, street, state, zipcode in specifications]
    years[2023][2].update(annual_average_employees='0', total_hours_worked='-1', size='1')
    return years
```

The old raw formats omit delivered `naics_year` and real harmonization supplies 2012. Fixture helper `assigned_tree(data_dir: Path) -> tuple[pl.LazyFrame, pl.DataFrame, pl.DataFrame]` prepares requests, acquires fixture responses through MockTransport and calls the actual assignment API, returning `(assignments, selected_naics_nodes, selected_county_reference)`. It is available for estimator unit integration; focused rule-matrix tests use the smaller `assignment_case` instead.

- [ ] **Step 1: Write hand-calculated estimator tests and the full diagnostic matrix.**

```python
def test_county_conditioned_shares_count_duplicate_submissions(tmp_path):
    from target_fixtures import assigned_tree
    from embedding_data.ita_area_mix import estimate

    assignments, nodes, counties = assigned_tree(tmp_path)
    result = estimate(assignments, nodes, year=2023)
    target = result.targets.collect()
    observed = target.select('unit_a', 'unit_b', 'value', 'n_unweighted', 'n_weighted').rows()
    assert observed == [
        ('geography:2025:county:01001', 'naics:2022:national_industry:111111', 0.75, 3, 3.0),
        ('geography:2025:county:01001', 'naics:2022:national_industry:111112', 0.25, 1, 1.0),
        ('geography:2025:county:51510', 'naics:2022:national_industry:111112', 1.0, 1, 1.0),
    ]
    assert result.denominators.collect().select(
        'county_id', 'n_assigned', 'n_eligible', 'n_excluded_industry').rows() == [
        ('geography:2025:county:01001', 7, 4, 3),
        ('geography:2025:county:51001', 1, 0, 1),
        ('geography:2025:county:51510', 1, 1, 0),
    ]
    assert target['se'].null_count() == 3
    assert target['se_method'].to_list() == ['none'] * 3
    assert all('size_gate_pending' in flags for flags in target['flags'].to_list())
    assert result.report['selected_year_partition'] == {
        'source': 12, 'unassigned_geography': 3,
        'assigned_excluded_industry': 4, 'eligible': 5,
    }
    counts = result.flag_counts.collect()
    assert counts.filter(
        pl.col('scope').eq('numerator') & pl.col('county_id').eq('geography:2025:county:01001') &
        pl.col('naics_2022_node_id').eq('naics:2022:national_industry:111112') &
        pl.col('flag_name').eq('flag_hours_per_employee') & pl.col('flag_state').eq('null')
    )['n'].item() == 1
```

Add tests for true/null flags in both scopes, denominator-only flags carried by every target cell in that county, `naics_year_from_dictionary` discovery, no Boolean coercion, exact typed empty flag-count output, source anomaly retention, outside-rule and null filing-decision retention, crosswalk/unknown/mismatch exclusions, node type/vintage/level failures, contradictory native scalar/flags rejected, invalid year rejected, no eligible rows refused before target publication, zero-eligible counties retained, no zero/supportless synthetic cells, and `1e-12` normalization tolerance. A small property test repeats or permutes source rows and verifies exact support preservation or invariance of logical sorted results, respectively; do not copy the estimator into the expected-value calculation.

- [ ] **Step 2: Run red.**

Run: `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_ita_area_mix.py -q`.

Expected: missing estimator API; no employment-weighted estimator or code-ancestor fallback is introduced.

- [ ] **Step 3: Implement the lazy eligibility, observed-cell counts and companion tables.**

```python
ESTIMATOR_VERSION = 'ita-area-mix-v1'
DENOMINATOR_SCHEMA = {
    'sample_set': pl.String, 'county_id': pl.String,
    'n_assigned': pl.UInt64, 'n_eligible': pl.UInt64, 'n_excluded_industry': pl.UInt64,
}
FLAG_COUNT_SCHEMA = {
    'scope': pl.String, 'county_id': pl.String, 'naics_2022_node_id': pl.String,
    'flag_name': pl.String, 'flag_state': pl.String, 'n': pl.UInt64,
}
UNIVERSE = (
    'OSHA ITA Form 300A is a program-selected filing subset, not a frame representative '
    'of all establishments; voluntary/outside-rule filings are retained and reported '
    'employment is unvalidated. This target counts submitted 2023 establishment-year '
    'records with preserved duplicate multiplicity, valid native NAICS 2022 industries '
    'and adopted compatible county assignments in the common 2025 frame, within the '
    '50 states and DC. It is conditional on that eligibility population.'
)


def eligible_industry() -> pl.Expr:
    return (pl.col('naics_mapping_status').eq('native_2022')
            .and_(pl.col('naics_2022_node_id').is_not_null())
            .and_(pl.col('flag_naics_crosswalked').not_())
            .and_(pl.col('flag_naics_ambiguous').not_())
            .and_(pl.col('flag_naics_unresolved').not_())).fill_null(False)


def support_flags(eligible: pl.LazyFrame) -> pl.LazyFrame:
    boolean_columns = [c for c, t in eligible.collect_schema().items() if t == pl.Boolean]
    frames = []
    for scope, keys in [('numerator', ['county_id', 'naics_2022_node_id']),
                        ('denominator', ['county_id'])]:
        for flag in boolean_columns:
            for state in ['true', 'null']:
                selected = pl.col(flag).eq(True) if state == 'true' else pl.col(flag).is_null()
                counts = eligible.filter(selected).group_by(keys).agg(
                    n=pl.len().cast(pl.UInt64),
                ).with_columns(pl.lit(scope).alias('scope'), pl.lit(flag).alias('flag_name'),
                               pl.lit(state).alias('flag_state'))
                if scope == 'denominator':
                    counts = counts.with_columns(
                        pl.lit(None, dtype=pl.String).alias('naics_2022_node_id'))
                frames.append(counts.select(list(FLAG_COUNT_SCHEMA)))
    if not frames:
        return pl.DataFrame(schema=FLAG_COUNT_SCHEMA).lazy()
    return pl.concat(frames).sort(['scope', 'county_id', 'naics_2022_node_id',
                                   'flag_name', 'flag_state'], nulls_last=False)
```

Run `validate_native` over the input before eligibility selection. Require exactly `year=2023`. The eligibility population is selected-year rows with an assigned county and `eligible_industry()` true; node membership/scalar/native consistency was validated, not repaired. Materialize eligible input once into staging or use an intentionally shared collected aggregate plan to avoid rereading the full table once per Boolean flag; implement support flags with one lazy unpivot/group operation if needed, preserving this function's observable schema and null semantics. Do not spill outside the run's staging.

Compute assigned county totals for **all assigned 2023 rows**; compute eligible totals and observed `(county_id, naics_2022_node_id)` counts from the same eligible population. UInt64 counts, left join eligible totals onto assigned totals with zero filling, `n_excluded_industry=n_assigned-n_eligible`, literal `sample_set='ita_300a_2023'`; select exact denominator schema and sort by `sample_set, county_id`. Group observed cells only, join D(a), value C/D; never form a Cartesian product. No eligible rows raises ValueError.

For flags, group positive true/null support counts only, use exact typed empty outputs when all counts are empty, and discover every Boolean source/assignment diagnostic from the schema, including `naics_year_from_dictionary` (no `flag_`-only restriction). Denominator support uses D(a)'s eligible contributors, not every assigned row. Ineligible rows' flags remain in coverage diagnostics. Build each target's labels from its positive numerator support plus its county's denominator support; sorted/distinct `<scope>:<flag_name>:<flag_state>` plus `size_gate_pending`. Null/true support counts must not exceed their cell/county support; their labels mean some contributors, not unanimous flags.

Emit target metadata exactly as in the spec: `osha_ita`, `area_mix`, `county`, selected county node ID, `naics_national_industry`, selected leaf ID, `establishment_share`, null Float64 SE, `none`, UInt64 C, Float64 C, `ita_300a_2023`, `naics=2022;county=2025`, `UNIVERSE`, flags. Select `TARGET_SCHEMA` physical order and sort by its key columns. `validate_area_mix` calls the shared validator, verifies all metadata/node memberships and positive observed support, exact numerator/denominator agreement, C≤D, n_weighted=float(C), null SE/none, (0,1] shares and per-county sums within `1e-12`; county denominators with D=0 emit no target.

Report all-year source/assigned/eligible/excluded counts, selected-year mapping-status × assignment-status, exact full-canonical-record duplicate **excess** `sum(group_size-1)` and duplicate-group counts (exclude appended row identity from grouping), repeated nonnull `id` and `establishment_id` group/row/excess counts separately, county D and cell C distributions (`min, p25, median, p75, p95, max`, total count), method coverage and true/null counts by year. All-year eligibility is a coverage diagnostic under the same native industry/county rule, not an extra target-year build. Do not label repeated IDs as confirmed duplicate establishments. Source, unassigned, assigned-ineligible and eligible totals must reconcile exactly; overlapping flags/cross-tabs are separate.

- [ ] **Step 4: Run green.**

Run: `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_ita_area_mix.py tests/test_target_contract.py tests/test_ita_assignment.py -q`.

Expected: the three target rows and three county denominators above match exactly, anomaly row remains included, all exclusions reconcile, positive true/null supports and flags agree, and no size gate is imposed.

- [ ] **Step 5: Commit.**

```bash
git add src/embedding_data/ita_area_mix.py tests/test_ita_area_mix.py tests/target_fixtures.py
git commit -m "feat(ita): estimate 2023 county establishment shares"
```

### Task 7: Publish the immutable combined bundle, expose commands and seed V12

**Files:** Create `src/embedding_data/ita_target_build.py`, `src/embedding_data/targets_cli.py`, `tests/test_ita_target_build.py`, `tests/test_targets_cli.py`, `tests/test_target_contract_v12.py`. Modify `src/embedding_data/cli.py:8–18,32–33` to register the group. Finalize `tests/target_fixtures.py`'s end-to-end helper.

**Interfaces:** Consumes Tasks 1–6. Produces `ita_target_build.build(data_dir: Path, assignment_run_id: str, target_run_id: str, *, year: int = 2023) -> Path`; `ita_target_build.verify_bundle(directory: Path, data_dir: Path) -> dict` (offline, returns verified report); and the three spec commands. `target_fixtures.run_ita_v12(data_dir: Path, monkeypatch) -> Path` is the later-family harness extension point, not a registry/framework for unimplemented estimators.

- [ ] **Step 1: Write publication and CLI tests before implementing orchestration.**

```python
def test_build_manifest_and_cached_replay(tmp_path, monkeypatch):
    from target_fixtures import acquired_tree, forbid_external_access
    from embedding_data.ita_target_build import build, verify_bundle
    from embedding_data.target_contract import TARGET_SCHEMA

    acquired_tree(tmp_path, monkeypatch)
    forbid_external_access(monkeypatch)
    first = build(tmp_path, 'fixture_assignment', 'first', year=2023)
    second = build(tmp_path, 'fixture_assignment', 'second', year=2023)
    assert set(p.name for p in first.iterdir()) == {
        'ita_county_assignments.parquet', 'ita_area_mix.parquet',
        'county_denominators.parquet', 'target_flag_counts.parquet',
        'inputs.json', 'report.json', 'outputs.json',
    }
    a = pl.read_parquet(first / 'ita_area_mix.parquet')
    b = pl.read_parquet(second / 'ita_area_mix.parquet')
    assert a.schema == TARGET_SCHEMA
    assert a.equals(b)
    assert verify_bundle(first, tmp_path)['selected_year_partition']['eligible'] == 5
    for name in ['ita_county_assignments', 'county_denominators', 'target_flag_counts']:
        assert pl.read_parquet(first / (name + '.parquet')).equals(
            pl.read_parquet(second / (name + '.parquet')))
    outputs = json.loads((first / 'outputs.json').read_text())
    assert len(outputs) == 6 and 'outputs.json' not in outputs
    for name in ['ita_county_assignments.parquet', 'ita_area_mix.parquet',
                 'county_denominators.parquet', 'target_flag_counts.parquet']:
        assert {'sha256', 'size', 'rows', 'schema', 'columns'} <= outputs[name].keys()


@pytest.mark.parametrize('command', ['prepare-ita', 'acquire-ita', 'build-ita'])
def test_targets_command_help(cli_runner, command, tmp_path):
    from embedding_data.cli import app

    result = cli_runner.invoke(app, ['targets', command, '--help'])
    assert result.exit_code == 0
    assert '--data-dir' in result.stdout
```

`acquired_tree(data_dir: Path, monkeypatch) -> PreparedInputs` composes `prepared_tree`, patches only acquisition's client to the fixture MockTransport, completes acquisition and returns the prepared selection. `forbid_external_access(monkeypatch) -> None` patches socket connection attempts and acquisition/Stage 3 client factories to fail, patches both `dotenv.load_dotenv` and the ACS/CPS modules' bound `load_dotenv`/`IpumsApiClient` names to fail, redirects their `DOTENV_PATH` globals to a nonexistent fixture path, and removes provider/IPUMS key variables without reading them. Preparation/build modules have no client factory to patch: test that their calls reach no network boundary. Apply the barrier before offline preparation in a scoped monkeypatch context, release only the factory barrier for MockTransport acquisition, then reinstate it for build. Existing upstream fixture construction remains offline. Add explicit CLI invocation tests with temporary `--data-dir` for success and actionable errors; acquisition alone may use the mock client. Do not invoke a default real-root CLI in any test.

Add parameterized build refusals: unsupported year, no eligible 2023 rows, unsafe or occupied final/staging names, missing acquisition completion, modified source/canonical/bundle/request/catalog/receipt/response/software bytes, native/node contradictions, index/response join fanout, and last-moment mutation before rename. Every failure leaves no final target directory and preserves earlier outputs. Reject stderr/stdout containing fixture addresses on error. An unrelated manifested file append at the final check must succeed. Replaying the same frozen assignment into a new target run yields equal logical Parquets; canonical JSON differs only in explicitly enumerated target-run IDs/execution provenance times, and consequent inventories of those changed JSONs. Existing artifact bytes remain identical.

Assert that the unpatched production software registry is complete and every named file exists in the Task 7/V12 tests. Change the recorded assignment implementation checksum and require resume/build refusal; change only estimator implementation and require a new target-run inventory with the same verified preparation. Earlier Tasks 2–3's partial-development test registry must not leak into these tests or any command.

- [ ] **Step 2: Run red.**

Run: `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_ita_target_build.py tests/test_targets_cli.py tests/test_target_contract_v12.py -q`.

Expected: new orchestration/group missing; the V12 test must fail until the real production functions are connected, not pass through mocked transforms.

- [ ] **Step 3: Implement offline staged orchestration and exact output provenance.** `build` validates year and safe IDs first, calls `check_preparation` and `read_evidence`, selects already frozen code/geography inputs, calls `assign`, sinks/revalidates the all-year assignment, calls `estimate`/`validate_area_mix`, writes target through `write_targets`, and writes the two typed companion Parquets. Reopen every serialized file for exact schema/order, row counts and family/assignment validation. Only temporary work owned by this staging directory may be removed before inventory; failed `.part` stays inspectable.

The output file set and their ordering keys are:

| File | Logical order / inventory rule |
| --- | --- |
| `ita_county_assignments.parquet` | `source_row`, exact source prefix and appended schema |
| `ita_area_mix.parquet` | `TARGET_KEY_COLUMNS`, exact `targets-v1` schema |
| `county_denominators.parquet` | `sample_set, county_id`, exact denominator schema |
| `target_flag_counts.parquet` | `scope, county_id, naics_2022_node_id, flag_name, flag_state`, null first |
| `inputs.json` | Canonical sorted-key UTF-8 JSON, no NaN |
| `report.json` | Canonical JSON with explicit disjoint partitions/overlapping diagnostics |
| `outputs.json` | Six other file records, including Parquet rows, schema and physical columns; excludes itself |

`inputs.json` contains these concrete fields; consumers must not infer provenance from directory naming:

```python
contracts = {
    'preparation': 'ita-assignment-inputs-v1', 'assignment': 'ita-assignment-v1',
    'target_schema': 'targets-v1', 'estimator': 'ita-area-mix-v1',
    'request_identity': 'ita-request-v1',
}
reference_frames = {
    'administrative': '2025', 'cbsa': 'July 2023', 'hud': '2025Q4',
    'census_benchmark': 'Public_AR_Current', 'census_vintage': 'ACS2025_Current',
}
```

Also record assignment/target run IDs/year, execution commit and clean/dirty state, fixture status, exact eligibility/counting/duplicate-preservation/no-size-gate/universe rules; source summary and canonical physical hashes/sizes; both selected bundle IDs, detached hashes and complete inventories; all preparation file inventories/detached hash and original software contract; catalogs/selection/receipts/responses/completion citations and original acquisition times; selected returned option IDs; implementation, dependency/Python and lock hashes for this target run; code/crosswalk/normalization/assignment/estimator versions. Include a top-level sorted/deduplicated `raw` array verified with `entry_for` covering **every** consumed source-file value in all ten years, both dictionaries, all transitive code/geography originals and all acquisition metadata/originals. Add `target_source_files` as the explicit 2023 raw source subset. Do not substitute only derived hashes or a whole-manifest checksum for raw citations.

Use `assignment_report` plus `AreaMix.report` for `report.json`, with exact table inventories and coverage limits. Recheck preparation, evidence, selected inputs, cited raw entries and current target software/lock after writing, immediately before final publication. Check exact file set/inventory plus final path safety/occupancy, then rename staging to final. No raw manifest append is performed by an offline build. `verify_bundle` runs these byte/schema/row/estimate/provenance checks on the published bundle; it does not acquire/rebuild anything.

- [ ] **Step 4: Add the command group and offline V12 harness.** Follow the existing codes/geography CLI exception style; do not print local variables or submitted addresses. Use this command signature surface:

```python
app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)


@app.command('prepare-ita')
def prepare_ita(
    assignment_run_id: str,
    codes_run: str = typer.Option(..., '--codes-run'),
    geography_run: str = typer.Option(..., '--geography-run'),
    data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir'),
    codes_outputs_sha256: str | None = typer.Option(None, '--codes-outputs-sha256'),
    geography_outputs_sha256: str | None = typer.Option(None, '--geography-outputs-sha256'),
) -> None:
    try:
        result = preparation.prepare(
            data_dir, assignment_run_id, codes_run, geography_run,
            codes_outputs_sha256=codes_outputs_sha256,
            geography_outputs_sha256=geography_outputs_sha256)
    except (ValueError, KeyError, OSError) as error:
        typer.echo(f'ITA preparation failed: {error}', err=True)
        raise typer.Exit(1) from None
    typer.echo(str(result))


@app.command('acquire-ita')
def acquire_ita(
    assignment_run_id: str,
    data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir'),
) -> None:
    try:
        result = acquisition.acquire(data_dir, assignment_run_id)
    except (ValueError, KeyError, OSError, httpx.HTTPError) as error:
        typer.echo(f'ITA acquisition failed: {error}', err=True)
        raise typer.Exit(1) from None
    typer.echo(str(result))


@app.command('build-ita')
def build_ita(
    assignment_run_id: str, target_run_id: str,
    year: int = typer.Option(2023, '--year'),
    data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir'),
) -> None:
    try:
        result = builder.build(data_dir, assignment_run_id, target_run_id, year=year)
    except (ValueError, KeyError, OSError) as error:
        typer.echo(f'ITA target build failed: {error}', err=True)
        raise typer.Exit(1) from None
    typer.echo(str(result))
```

Here `preparation`, `acquisition`, `builder` are explicit imports of `ita_assignment_prepare`, `ita_assignment_acquire`, `ita_target_build`. The `...` token in Typer's required option default is the actual required-value sentinel, not omitted implementation. Import/register `targets_cli` in `cli.py` with `app.add_typer(targets_cli.app, name='targets')` alongside the existing groups. Preserve top-level and group help. Validate IDs/options with path-safe error messages before touching raw files.

The V12 test's full path is:

```python
def test_ita_raw_to_target_contract_offline(tmp_path, monkeypatch):
    from target_fixtures import run_ita_v12
    from embedding_data.ita_target_build import verify_bundle

    bundle = run_ita_v12(tmp_path, monkeypatch)
    report = verify_bundle(bundle, tmp_path)
    assert report['input_rows'] == 21
    assert report['selected_year_partition'] == {
        'source': 12, 'unassigned_geography': 3,
        'assigned_excluded_industry': 4, 'eligible': 5,
    }
    assert pl.read_parquet(bundle / 'ita_area_mix.parquet').height == 3
```

`run_ita_v12` composes `seed_inputs`, real offline preparation, fixture-only MockTransport acquisition, then client/socket/dotenv barriers and real offline build. Assert original summaries/dictionaries/code/geography/Census bytes appear in verified provenance and source order/multiplicity survives. Do not mock harmonization, canonical mapping, geography parsing, assignment, estimator, writer or manifest. Later family stages add their own raw-to-target test beside this test, reusing generic writer/inventory checks; they do not make this test pretend to cover all eight families.

- [ ] **Step 5: Run green and the second full checkpoint.**

Run: `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest tests/test_ita_target_build.py tests/test_targets_cli.py tests/test_target_contract_v12.py -q`, then the full pytest/Behave/ruff/lock group. Run `uv run --offline --locked embedding-data targets --help` and all three subcommand helps with the cache override; they must not access data/network.

Expected: all focused/full checks pass with observed counts recorded; fixture V12 is complete for this family only. Run task review and a whole-branch code review before production preparation so required software changes land before its identity is frozen. Review/fix code now; if later code changes affect the frozen preparation/assignment contract, create new preparation rather than bypassing its version gate.

- [ ] **Step 6: Commit.**

```bash
git add src/embedding_data/ita_target_build.py src/embedding_data/targets_cli.py src/embedding_data/cli.py tests/test_ita_target_build.py tests/test_targets_cli.py tests/test_target_contract_v12.py tests/target_fixtures.py
git commit -m "feat(targets): publish offline ITA bundles and seed V12"
```

### Task 8: Measure the real all-year assignment and 2023 target, document and hand off

**Files:** Modify `README.md`, `CLAUDE.md`. Create `specs/findings/stage-6-ita-area-mix-build.md`. At successful completion, update/retire this plan, its stage spec, `specs/deferred_items.md` if needed and the Stage 6 entry in `specs/embedding-evaluation-data-spec-roadmap.md` through writing-plans' completion protocol. Raw and derived production outputs remain in ignored `data/`.

**Interfaces:** Consumes reviewed shipped APIs from Tasks 1–7 and the explicit selected real inputs. Produces the measured finding, selected immutable assignment/target inventories and a consumer Handoff identifying the actual shipped APIs and their limits. This task is a production acceptance gate, not another estimator task. Do not mark it complete if acquisition/build is incomplete or blocked externally.

- [ ] **Step 1: Document the reviewed command surface before freezing production software.** Put these concrete examples in README, explaining one-time full-table preparation/acquisition, cached resume, offline replay, all-year assignment versus 2023-only target and where files live:

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data targets prepare-ita stage6_ita_assignment_20261014_1000 --codes-run stage4_v11_20261013_r2 --geography-run stage5_geography_20261014 --data-dir /Users/lowell/Projects/embedding-data/data
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data targets acquire-ita stage6_ita_assignment_20261014_1000 --data-dir /Users/lowell/Projects/embedding-data/data
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data targets build-ita stage6_ita_assignment_20261014_1000 stage6_ita_area_mix_20261014_1000 --year 2023 --data-dir /Users/lowell/Projects/embedding-data/data
```

`uv --offline` prevents package fetching; the acquisition subcommand still deliberately makes Census HTTP calls. State that explicitly next to the example. README text must include: submitted-record counts including duplicates; conditional program-selected universe and unvalidated employment; native-2022 eligibility; adopted HUD singleton support; no SE/none; size_gate_pending; separate 2025/2023/2025Q4/Current frames; no automatic downloads from offline commands; immutable run IDs/partial inspection; exact alternate-run checksum options. Explain output schemas/flag support/denominators and that no county-accuracy or representativeness claim follows from coverage.

Update CLAUDE.md's architecture/status to describe verified shipped commands and protected-input constraints. Link the new production finding only after it exists. Keep planned later ACS/CPS/family work described as planned. Commit docs with `git add README.md CLAUDE.md` and `git commit -m "docs(targets): describe reviewed ITA build workflow"` before production preparation; record that commit as execution provenance. No further relevant software edits may slip into a cached resume.

- [ ] **Step 2: Capture protected inventories and verify real inputs read-only.** From the execution checkout, keep the real data root explicit. First run this inventory script, redirecting its JSON to `/private/tmp/embedding-data-stage6-protected-before.json` (outside git). It must cover the whole Stage 3 verification tree, source table and complete Stage 4/5 bundle trees, including raw prior reference bytes via their cited manifest entries:

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked python - <<'PY' > /private/tmp/embedding-data-stage6-protected-before.json
import json
from pathlib import Path
from embedding_data import manifest
root = Path('/Users/lowell/Projects/embedding-data/data')
protected = [root / 'derived/osha/ita_300a_summary.parquet']
protected.extend(root / 'raw' / entry.path
                 for entry in manifest.read_manifest(root / 'raw/manifest.jsonl'))
for name in ['derived/osha/verification', 'raw/references/census-geocoder',
             'derived/codes', 'derived/geography', 'derived/targets',
             'derived/osha/assignment-inputs']:
    directory = root / name
    if directory.exists():
        protected.extend(p for p in directory.rglob('*') if p.is_file())
print(json.dumps({p.relative_to(root).as_posix(): {'sha256': manifest.sha256_file(p),
                  'size': p.stat().st_size} for p in sorted(set(protected))},
                 sort_keys=True, indent=2))
PY
```

Also copy the manifest snapshot before acquisition, preserving its exact original bytes:

```bash
cp /Users/lowell/Projects/embedding-data/data/raw/manifest.jsonl /private/tmp/embedding-data-stage6-manifest-before.jsonl
```

The before-inventory includes only files present now; new Stage 6 files later under the raw Census parent are allowed. It is not a requirement that the raw manifest's whole-file hash remain constant during acquisition. Also run `target_inputs.select` on the real root with the two explicit selected runs and confirm detached hashes match the spec. Inspect the returned source year counts (2016–2025), total **3,206,055**, unchanged source/canonical physical parity, valid upstream inventories and raw dictionary citations. No builder/sample/download runs in this preflight.

- [ ] **Step 3: Run real offline preparation and record the observed workload.** Run README's exact `prepare-ita` command. Record its source/index/request inventories, software/dependency/commit/lock inventories, rows and actual distinct tuple/batch counts. Compare the actual count to the design estimate **1,113,538 tuples**, explaining any measured difference rather than asserting the estimate is a completed-call count. Under D4, at 1,000/request batch the estimate implies 1,114 batches (1,113 full plus 538 records); use the actual new frozen files to count work. Verify the source and request indexes are logically identical to the preserved original preparation, and include its complete directory plus four raw controls in the protected before/after inventory. Include incomplete and delivered-excluded requests as required. Verify prepared file hashes before acquiring.

If planned run names already exist, verify their contents and either resume a matching preparation or choose an explicit new safe suffixed run ID and record that actual selection everywhere. Never remove/overwrite an occupied final or `.part` to force the example names through. A leftover `.part` remains an inspection task; it is not evidence of successful preparation.

- [ ] **Step 4: Acquire all frozen batches, then perform offline build and cached replay.** Run README's exact `acquire-ita` command (the only live service step). Keep progress at batch granularity and preserve completed receipt evidence. A transport/validation failure stops; rerun that same command explicitly to resume verified missing work. No blind retries, alternate options or edits to frozen request files. If the required catalog option is missing, stop and report the requirement as blocked pending evidence/owner direction; do not substitute another frame or claim Stage 6 complete.

Once acquisition verifies every batch, run README's exact `build-ita` command. Run a second offline build from the same assignment inputs:

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data targets build-ita stage6_ita_assignment_20261014_1000 stage6_ita_area_mix_20261014_1000_replay --year 2023 --data-dir /Users/lowell/Projects/embedding-data/data
```

Prove replay equality for all four Parquets by schema, ordered logical rows and exact counts. Compare JSON after removing only the documented target-run IDs/execution times and the consequential inventories/checksums of those files. Catalog/receipt/response acquisition times, options and hashes must remain identical. Report physical Parquet checksums as per-run inventories; do not claim them stable across future library versions. Run `verify_bundle` on both outputs and record detached `outputs.json` SHA-256 checksums.

- [ ] **Step 5: Reconcile production evidence and protected bytes.** Use a read-only verification script against the selected target bundle to assert:

```python
assert assignments.select(pl.len()).collect().item() == 3_206_055
assert assignments.select(pl.col('source_row').n_unique()).collect().item() == 3_206_055
assert assignments.select(pl.col('source_row').min()).collect().item() == 0
assert assignments.select(pl.col('source_row').max()).collect().item() == 3_206_054
assert target.select(pl.col('n_unweighted').sum()).collect().item() == eligible_2023
assert denominators.select(pl.col('n_eligible').sum()).collect().item() == eligible_2023
assert denominators.filter(
    pl.col('n_assigned').ne(pl.col('n_eligible') + pl.col('n_excluded_industry'))
).select(pl.len()).collect().item() == 0
assert target.filter(pl.col('se').is_not_null()).select(pl.len()).collect().item() == 0
assert target.filter(pl.col('se_method').ne('none')).select(pl.len()).collect().item() == 0
assert target.filter(
    pl.col('flags').list.contains('size_gate_pending').not_()
).select(pl.len()).collect().item() == 0
```

For that script, bind `assignments`, `target`, `denominators` with `pl.scan_parquet` for their exact published filenames; bind `eligible_2023` to `verify_bundle(bundle, root)['selected_year_partition']['eligible']`, independently cross-checked from the assignment eligibility count. Assert per-county share sums within `1e-12`, all metadata and typed node references, all denominator/flag-count schema and support invariants through the public validators. Include all source year/source-file totals, method/reason/scope coverage, native and excluded industry statuses, all flag true/null counts, duplicate/repeated-ID diagnostics, county and cell distributions. Do not write target numbers into the finding until these checks pass.

Reload the protected-before JSON and compare each recorded path's current size/hash exactly; report zero changed/missing protected files. Also preserve the original manifest bytes in `/private/tmp/embedding-data-stage6-manifest-before.jsonl` before acquisition and verify the final manifest begins with exactly those bytes, permitting appended entries. Independently reverify every cited prior raw file through `entry_for`; newly appended manifest entries do not excuse any prior byte change. Run the whole-tree audit:

```bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data audit --data-dir /Users/lowell/Projects/embedding-data/data
```

Expected: exit 0 with zero discrepancies. Inspect actual output; a failed audit is not waived by target validation.

- [ ] **Step 6: Commit the measured finding and fresh repository checks.** The finding must contain actual selected run IDs, input/preparation/catalog/response/receipt/software inventories and execution commit, returned Census options/acquisition start/end, output inventories and detached checksum, all-ten-year row accounting and immutable-input comparison, 2023 coverage/eligibility/denominators/flag/duplicate/cell distributions, V12 fixture scope and real cached replay evidence. Distinguish conditional coverage from county accuracy and representativeness. State Current-service variability, common-frame historical limit, native-only/year-only slice, retained diagnostics and pending V9 gate. Never title fixture results or native source counts as completed production targets.

Run the full pytest/Behave/ruff/lock group once more after final code/docs/review fixes, recording fresh results. Run final requesting-code-review against the actual branch/spec/plan and resolve findings. Required changes to frozen preparation/assignment software require a new preparation/acquisition selection; estimator-only changes can use a new target run with explicit new code provenance. Update the finding to the final verified selection. Then:

```bash
git add README.md CLAUDE.md specs/findings/stage-6-ita-area-mix-build.md
git commit -m "docs(targets): record measured Stage 6 ITA build"
```

- [ ] **Step 7: Run completion protocol and prepare the later-stage handoff.** Before marking anything complete, apply writing-plans' resolve-before-defer gate. Ask about genuinely owner-blocked leftovers; implement those unblocked by answers; consciously defer only qualifying independent leftovers with closure conditions. Do not defer the required real production milestone and label Stage 6 complete.

When Tasks 1–8 and review/evidence are actually complete, tick plan steps and annotate deviations, update/tick qualifying deferred items, and write `## Handoff to later stages` with actual selected bundles/inventories and shipped APIs. Identify what Stages 9–13 consume: generic target schema/validation/writer; per-family unit membership/estimator/uncertainty responsibilities; denominator/flag support meanings; V12 extension point; ITA assignment identity and duplicate multiplicity; separation from Stage 10 text pairs/linkage; pending V9 gate and all-family coverage. Cite the stage spec and actual deviations/traps rather than restating requirements. Never invent a next-stage design.

Tick only Stage 6 and add its exact completion stamp in the roadmap. Run backlog statistics and any required read-only triage. Retire this plan to `specs/plans/completed/6-target-contract-ita-area-mix.md` and, absent another live plan for it, its completed stage spec to `specs/completed/target-contract-ita-area-mix.md`; fix relative links at the deeper paths. Commit protocol edits before merge/PR, then use finishing-a-development-branch for the deliberate integration/worktree cleanup decision. End with the resume-roadmap handoff; do not plan a later stage in this execution session.

## Plan review and execution boundary

The owner approved this plan as written on 2026-10-14 (D1) and selected subagent-driven-development in a fresh session (D2). No checklist is marked complete at handoff because these are implementation steps, not planning accomplishments; the receiving execution session records subsequent progress in its durable ledger.

Execute in the selected fresh session with subagent-driven-development: Tasks 1–7 have distinct artifacts and reviewable contract boundaries, while dependencies still require ordered execution. Read this plan and the stage spec afresh; model selection follows the host's available models and the user's project preferences.

## Spec coverage self-review

| Stage-spec section | Implementing tasks / completion gate |
| --- | --- |
| Scope/adopted design; selected inputs and inherited contracts | Global Constraints, Tasks 1/4/6/8; no source rebuild, guessed candidates or extra target years |
| Pipeline boundary; preparation/request identity | Tasks 1–2/7; exact explicit selection, all-row UInt64 identity, atomic new runs |
| Census acquisition/offline replay | Task 3; exact IDs/catalogs, immutable per-batch receipts, version checks and no automatic network |
| Full-table assignment/artifact | Task 4; ordered canonical prefix, complete HUD/county attributes, precedence/independent flags |
| Area mix/coverage; shared contract | Tasks 5–6; handwritten C/D, diagnostic-only anomalies, counts/SE/flags/denominators, general writer |
| Manifest/error/publication | Tasks 1–3/7; transitive raw citations, schemas/physical hashes/versions, cached evidence, exact seven-file bundle |
| Verification 1–5 / V12 seed | Test strategy and Tasks 1–7; mutation/refusal tests, fixture originals, credential/network barriers, logical replay |
| Verification 6 / production completion | Task 8; all-ten-year real assignment, measured 2023 target/finding, protected hashes, whole-tree audit |
| Rollout/later-stage handoff | Task 8 Step 7; only Stage 6 closes, actual APIs feed later families, R7.3 count reporting only and V9 pending |

No uncovered stage requirement identified. Planning verification checks the verbatim header stamp, eight ordered tasks, unchecked execution steps, Python-listing syntax, local links and absence of prose placeholders; it does not claim that the future implementation or production outputs exist.
