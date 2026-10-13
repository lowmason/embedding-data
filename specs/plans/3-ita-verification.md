# ITA Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when the owner chooses inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/embedding-evaluation-data-spec-roadmap.md, Stage 3 — on plan
> completion, tick the stage and re-validate later stages against what shipped.

**Goal:** Discharge V1, V2 and V3 with reproducible measurements and recorded
decisions, and close the deferred manifest audit before any ITA target is built.

**Architecture:** Strengthen verified raw citation without losing the existing
missing-file lookup. A small reference module acquires official NAICS files and
records manually acquired HUD files; separate offline text/link and county
comparison modules produce aggregate diagnostics. Network acquisition of Census
geocodes is explicit and cached, so report generation never calls a service.
The final task records the measured decisions and the later-stage handoff.

**Tech Stack:** Python 3.14, Polars 2.0, httpx, Typer, stdlib Unicode/CSV/JSON/SHA-256,
pytest, ruff. Add `fastexcel` for the official XLS and XLSX inputs; uv.lock pins it.

**Spec:** `specs/embedding-evaluation-data-spec.md`: V1–V3, R2.6–R2.8 and the
Stage 3 correction to R2.3. R1.4 and R9.2 govern provenance and replay. The shared
spec remains live; do not retire it with this stage's plan.

**Planning baseline:** `main` at `02ad88b`, 2026-10-13. Fresh offline baseline:
212 pytest tests passed (one network test deselected), two Behave scenarios
passed, and ruff passed. Plan allocator: next free 3, no collisions.
No Stage 3 investigation result or method decision is established by this plan.

**Plan self-review:** requirement/interface/placeholder checks completed.
Extracted Python examples compiled and passed 229 offline tests (one network
test deselected) in a temporary copy with the existing regression suite; ruff
passed for the new modules/tests. The title reader also parsed the cached
official XLS/XLSX structures at all three expected counts. These are planning
checks, not Stage 3 implementation or full-data investigation results.

## Global Constraints

- R1.4: "Raw downloads are immutable and kept as delivered" and "Transformations read raw files and write derived Parquet; nothing edits a raw file."
- R9.1: "Transformations are lazy polars with method-style expressions."
- R9.2: "Every transformation is deterministic and runs offline from raw files. Tests use fixtures, with no network and no credentials."
- R2.6: "Keep the original string and add a normalized matching key (Unicode and whitespace normalized, case folded)."
- R2.6: "Deduplicate on employer (`ein`, else `company_name`) and normalized description before building pairs". This stage measures that grouping; it does not build pairs.
- R2.5: "missing stays missing and is never imputed from the description."
- R2.9: "Flag, never drop, implausible records". Keep the source table intact; report both row-level and deduplicated diagnostics explicitly.
- R6.2: "Connecticut's planning regions are its county-equivalents throughout, matching the 2023 delineations."
- R6.4: "Exclude Puerto Rico and the island areas from the hierarchy."
- R8.1: "Only aggregate targets leave the machine they were built on, and IPUMS microdata are never committed to a repository."
- R8.3: "ITA files are public, so ITA-derived tables may contain establishment-level rows."
- R8.4: "Benchmark tables are never training data."
- Rollout: "Planned targets are never described as built, and no result from a fixture or a partial extract is reported as a benchmark."
- No ACS/CPS requests, IPUMS transformations, AWS operations, or credential changes. The manifest audit may read and hash all raw files locally.
- Code style: four spaces, single quotes, `'''` docstrings, 99 columns; ruff E/F/I/Q. All CLI tests pass `--data-dir` explicitly.

## Decisions

- **D1** (owner, plan review, 2026-10-13): include the manual HUD download as
  an execution prerequisite. Code imports the downloaded original workbook;
  it does not request, store or use a HUD credential. Applied in: P6,
  Tasks 2 and 6.
- **D2** (owner, plan review, 2026-10-13): "Approved. Can you please provide
  a handoff prompt?" The plan is approved for execution, including P1–P10
  and Task 6's proposed amendment wording A1–A4. Task 6's evidence-dependent
  adoption checkpoint remains required before adopting measured rules or
  applying verified markers. Applied in: Tasks 1–6 and the execution handoff.

- **D3** (owner, execution prerequisite, 2026-10-13): selected
  `data/raw/hud/ZIP-COUNTY_122025.xlsx`, quarter 2025Q4. The earlier ZIP-TRACT
  workbook is not the ZIP-county prerequisite and is not used. The actual
  ZIP-COUNTY header is GEOID, accepted only with its validated original filename;
  eight recognized short out-of-scope zero-BUS geographies are retained and flagged.
  Applied in: Task 2 compatibility follow-up and Task 6 input acquisition.
- **D4** (owner, Task 3 review checkpoint, 2026-10-13): approved evaluating
  address tuple multiplicity on all exact-distinct yearly rows before eligible-ID
  filtering; approved excluding null IDs from cohort/link confirmation and reporting
  original missing-ID row counts. Applied in: Task 3 fix round 1.
- **D5** (owner, Task 4 review checkpoint, 2026-10-13): approved explicit
  `<missing-state>` sampling strata while retaining delivered fields, and normalized
  state keys for scope exclusions. Applied in: Task 4 fix round 1.
- **D6** (owner, Task 5 review checkpoint, 2026-10-13): approved exact request-ID
  validation before publishing/manifests for Census responses, with invalid-response
  retry and cached no-network acquisition regressions. Applied in: Task 5 fix round 1.
- **D7** (owner, Task 6 measured evidence checkpoint, 2026-10-13): approved
  A1–A4 as proposed after reviewing the complete actual V1–V3 finding. Adopted
  the R2.3 introductory correction, R2.6 normalization/title/employer rules,
  R2.7 conservative all-year candidate-ID linkage, and R2.8 exact Census
  ACS2025 geography first with compatible single-positive-BUS HUD fallback.
  Applied in: source spec R2.3/R2.6–R2.8, finding, README and CLAUDE. No
  replacement default or software change required; measurement provenance retained.

The defaults below are approved for execution; measurement-dependent
decisions are adopted only at Task 6's evidence checkpoint.

## Approved execution defaults

- **P1 — Interfaces:** `embedding-data audit` is read-only. Reference acquisition
  and investigations run through explicit module functions and the commands in
  Tasks 5–6; `osha` retains its existing set interface.
- **P2 — Reference inputs:** official Census NAICS structures, 2012/2017/2022,
  at all levels 2–6, with ranged sectors intact. Compare descriptions against
  any official title across these three vintages; also report native-vintage
  title identity separately, with unknown vintage as unknown.
- **P3 — Text:** NFKC, Unicode casefold, collapse whitespace, trim. Preserve
  punctuation and the delivered original. Flag suspected mojibake, never repair
  it automatically. Initial exact placeholder vocabulary is in Task 3; examine
  frequent residual keys before adopting the final vocabulary.
- **P4 — Employer:** valid nine-digit EIN, with an eight-digit numeric EIN
  left-padded and separately flagged; malformed/missing EIN falls back to the
  normalized non-empty company name. Missing both means unknown employer, never
  one shared blank employer. Company fallback is weaker evidence and cannot
  establish EIN-based co-ownership. Inspect zero/repeated-digit EIN frequencies
  at the evidence checkpoint before accepting them as employer identifiers.
- **P5 — Linkage:** exact duplicate rows collapse only in linkage diagnostics;
  competing records for the same establishment ID are ambiguous. No fuzzy name
  or address matching. Measure the required 2023→2024 and 2023→2025 cohorts and
  extend the same diagnostics to consecutive earlier years. Missing EIN never
  counts as evidence that two employers match.
- **P6 — V3:** use the free HUD ZIP–county workbook, proposed quarter 2025 Q4,
  plus Census street-address batch geocoding. HUD access requires a free login:
  the owner obtains the workbook, and code imports its original bytes without
  handling a HUD password or token. If another local quarter is chosen, record
  its exact release name before execution. Do not substitute ZCTAs.
- **P7 — Sample:** deterministic SHA-256 ranking, eight distinct source rows
  per `(filing year, state, ZIP format, ZIP business-county count class)` stratum,
  taking all smaller strata. Exact duplicates have their own diagnostic count.
  Report stratum populations/inclusion probabilities and weighted population
  summaries separately from raw sample percentages.
- **P8 — Geography:** request `Public_AR_Current` / `ACS2025_Current`, after
  checking and caching the service's available benchmark/vintage lists. Save
  responses immutably. The Current address benchmark can change: offline replay
  uses saved responses. Acquisition can resume missing batches for the same
  frozen requests, retaining each response's acquisition timestamp. A run may
  therefore combine service snapshots; cached catalog names/IDs do not freeze
  the address benchmark. Report its date range and this limitation. A fresh
  comparison against Current uses a new run, never replaces saved responses.
  Flag legacy Connecticut county codes in the HUD file as incomparable; no
  many-to-one conversion from old counties to planning regions.
- **P9 — Proposed county rule for evidence review:** Census exact address
  match first; fallback only to a single positive-business-share county in the
  ZIP crosswalk, and only with compatible county geography. Multiple counties,
  ties, zero business ratios, and unmatched addresses stay unresolved/flagged.
  A largest-business-share county is a comparison diagnostic, not an adopted
  assignment. This hybrid requires the explicit R2.8 amendment in Task 6.
- **P10 — Completion:** evidence and rules, not production targets. Tick Stage 3
  only after the finding, adopted amendments, audit closure and whole-plan review.
  Put the compatibility review of later stages in the retired plan's Handoff;
  amendments to later roadmap entries occur at the next derive-roadmap resume.

## File responsibilities

| File | Responsibility |
| --- | --- |
| `src/embedding_data/manifest.py` | Pure recorded lookup and verified citation |
| `src/embedding_data/manifest_audit.py` | Whole-raw-tree discrepancy report and audit CLI |
| `src/embedding_data/ita_references.py` | Immutable official reference acquisition/import and title parsing |
| `src/embedding_data/ita_verification.py` | Normalization, V1 and V2 aggregate measurements |
| `src/embedding_data/ita_county_verification.py` | Sample, HUD candidates, cached Census response parsing and V3 measurements |
| `src/embedding_data/ita_verification_run.py` | Explicit acquire/measure commands, report artifacts and input inventory |
| `tests/test_manifest_audit.py`, `tests/test_manifest.py` | Provenance and audit invariants |
| `tests/test_ita_references.py` | Reference parser/acquisition contracts |
| `tests/test_ita_verification.py` | Text and linkage denominators/collisions |
| `tests/test_ita_county_verification.py`, `tests/test_ita_verification_run.py` | Sampling, county comparison and offline replay |
| `specs/findings/v1-v3-ita-verification.md` | Actual measurements, denominators, limitations and adopted decisions |
| README, CLAUDE, source spec, deferred items, roadmap, this plan | Documentation and completion handoff |

## Test strategy and milestones

The fast suite uses invented rows and `httpx.MockTransport`; it never reads the
real data tree. No new live tests are needed for a one-time investigation.

| Invariant | Cheapest check / fixture | Milestone |
| --- | --- | --- |
| Cited hash is current; audit lists unrecorded, changed, missing, duplicate entries | Temporary raw tree; existing missing-file OSHA regression tests | Task 1 |
| Recorded/missing files are never replaced; reference layouts fail loudly | Tiny byte streams and header tables | Task 2 |
| Blank employers never become one firm; titles/keys use identical normalization | Tiny Unicode/title/employer frames | Task 3 |
| Linkage cannot fan out; null EIN is unknown; duplicate and conflicting IDs differ | Hand-calculated multi-year frame | Task 3 |
| Sample independent of input order; all strata represented; stable identity despite record-ID collisions | Reordered/duplicated fixture frame | Task 4 |
| Match coverage and agreement have distinct denominators; ambiguous ZIPs and CT vintage differences retained | Small HUD table and Census CSV variants | Task 4 |
| No request during measure; cached provenance mismatch fails; repeated outputs agree | Temporary source releases through offline report run | Task 5 |
| Full years, real audit, required cohorts, sample counts and versions recorded | Explicit live acquisition, then offline full-data measurement | Task 6 |

Run `uv run --locked pytest` (the existing `not network` default),
`uv run --locked behave`, `uv run --locked ruff check .`, and `uv lock --check`
at the final code milestone. Use `UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache`
if the sandbox cannot write the default uv cache. No new CI configuration.

Execution starts in an isolated worktree via using-git-worktrees, on
`stage-3-ita-verification` cut from the reviewed plan revision. The real data tree
stays at `/Users/lowell/Projects/embedding-data/data`; pass it explicitly for
Task 6. Do not duplicate gigabytes of data into a worktree. Read both the source
spec and plan 2's Handoff before Task 1. Follow tasks in order, with each task's
verification as the milestone checkpoint.

---

### Task 1: Whole-tree audit and verified raw citations

**Files:** Modify `src/embedding_data/manifest.py:108`,
`src/embedding_data/osha_benchmark_download.py:106`,
`src/embedding_data/ita_summary.py:365`, `src/embedding_data/cli.py`,
`tests/test_manifest.py`; create `src/embedding_data/manifest_audit.py` and
`tests/test_manifest_audit.py`.

**Interfaces:** Consumes `read_manifest`, `sha256_file`, `paths.manifest_path`.
Produces `recorded_entry_for(Path, Path) -> ManifestEntry` (lookup only),
verified `entry_for(Path, Path) -> ManifestEntry`, and
`audit(Path) -> list[AuditIssue]` with sorted discrepancy records.

- [ ] **Step 1: Write failing provenance/audit tests.** Append to the manifest
  tests using their existing `describe` helper:

```python
def test_entry_for_verifies_present_bytes(raw_file, data_directory):
    file = paths.manifest_path(data_directory)
    entry = describe(raw_file, data_directory)
    manifest.append_entries(file, [entry])
    raw_file.write_bytes(b'changed')
    with pytest.raises(ValueError, match='SHA-256 .*differs'):
        manifest.entry_for(file, raw_file)
    raw_file.unlink()
    assert manifest.recorded_entry_for(file, raw_file) == entry
    with pytest.raises(FileNotFoundError):
        manifest.entry_for(file, raw_file)
```

  Create the audit tests:

```python
from datetime import UTC, datetime

from embedding_data import cli, manifest, manifest_audit, paths

def test_audit_reports_all_discrepancies_without_mutation(tmp_path):
    root = tmp_path / 'raw'
    root.mkdir()
    files = [root / name for name in ('changed.csv', 'missing.xml', 'ok.zip')]
    for file in files:
        file.write_bytes(b'original')
    entries = [
        manifest.describe_file(
            file,
            root,
            retrieved_at=datetime(2026, 10, 13, tzinfo=UTC),
            client='fixture',
            client_version='1',
        ) for file in files
    ]
    file = paths.manifest_path(tmp_path)
    manifest.append_entries(file, entries)
    before = file.read_bytes()
    files[0].write_bytes(b'modified')
    files[1].unlink()
    (root / 'unrecorded.csv').write_bytes(b'unknown')
    (root / 'extract.part').mkdir()
    (root / 'extract.part/interrupted.csv').write_bytes(b'incomplete')
    (root / '.DS_Store').write_bytes(b'finder')
    issues = manifest_audit.audit(tmp_path)
    assert [(item.path, item.kind) for item in issues] == [
        ('changed.csv', 'hash_mismatch'),
        ('extract.part/interrupted.csv', 'unrecorded'),
        ('missing.xml', 'missing'),
        ('unrecorded.csv', 'unrecorded'),
    ]
    assert file.read_bytes() == before
    assert files[0].read_bytes() == b'modified'

def test_audit_command_exits_nonzero_on_discrepancy(cli_runner, tmp_path):
    (tmp_path / 'raw').mkdir()
    (tmp_path / 'raw/stray.csv').write_bytes(b'x')
    result = cli_runner.invoke(manifest_audit.app, ['--data-dir', str(tmp_path)])
    assert result.exit_code == 1
    assert 'unrecorded' in result.output and 'stray.csv' in result.output
    top_level = cli_runner.invoke(cli.app, ['audit', '--data-dir', str(tmp_path)])
    assert top_level.exit_code == 1
    assert 'unrecorded' in top_level.output and 'stray.csv' in top_level.output
```

- [ ] **Step 2: Run RED.** `uv run --locked pytest tests/test_manifest.py tests/test_manifest_audit.py -q`.
  Expected failure: missing `recorded_entry_for` / module / verification behavior.

- [ ] **Step 3: Implement verified lookup and audit.** Rename the current lookup
  to `recorded_entry_for`, change it to reject duplicate matching entries, and
  add verified citation below it:

```python
def recorded_entry_for(manifest_path: Path, raw_file: Path) -> ManifestEntry:
    '''Find provenance even when the file is absent; never use this to cite bytes.'''
    path = raw_file.relative_to(manifest_path.parent).as_posix()
    matches = [item for item in read_manifest(manifest_path) if item.path == path]
    if not matches:
        raise KeyError(f'{path} is not recorded in {manifest_path}')
    if len(matches) != 1:
        raise ValueError(f'{path} is recorded more than once in {manifest_path}')
    return matches[0]

def entry_for(manifest_path: Path, raw_file: Path) -> ManifestEntry:
    '''Return a citation only after verifying the file's current bytes.'''
    entry = recorded_entry_for(manifest_path, raw_file)
    actual = sha256_file(raw_file)
    if actual != entry.sha256:
        raise ValueError(
            f'{entry.path}: SHA-256 {actual[:12]}... differs from the '
            f'{entry.sha256[:12]}... recorded in {manifest_path}; the raw file has '
            'changed since it was downloaded'
        )
    if raw_file.stat().st_size != entry.size:
        raise ValueError(f'{entry.path}: size differs from its manifest entry')
    return entry
```

  In `refuse_replacement`, change only its lookup to `recorded_entry_for`.
  In `build_summary_table`, keep `entry_for` and delete its now-redundant
  `sha256_file` comparison. Preserve the existing error wording above.
  Apply these exact edits:

```diff
--- a/src/embedding_data/osha_benchmark_download.py
+++ b/src/embedding_data/osha_benchmark_download.py
@@
-    recorded = manifest.entry_for(manifest_path, raw_file)
+    recorded = manifest.recorded_entry_for(manifest_path, raw_file)
--- a/src/embedding_data/ita_summary.py
+++ b/src/embedding_data/ita_summary.py
@@
             entry = manifest.entry_for(manifest_path, raw_file)
-            sha256 = manifest.sha256_file(raw_file)
-            if sha256 != entry.sha256:
-                raise ValueError(
-                    f'{entry.path}: SHA-256 {sha256[:12]}... differs from the '
-                    f'{entry.sha256[:12]}... recorded in {manifest_path}; the raw file has '
-                    'changed since it was downloaded'
-                )
             utf8_path = Path(work) / f'{year}.csv'
```

  The new audit module:

```python
'''Report raw provenance discrepancies without repairing or changing files.'''

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import typer

from embedding_data import manifest, paths

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)

@dataclass(frozen=True)
class AuditIssue:
    path: str
    kind: str

def audit(data_dir: Path) -> list[AuditIssue]:
    file = paths.manifest_path(data_dir)
    root = file.parent
    entries = manifest.read_manifest(file)
    counts = Counter(item.path for item in entries)
    issues = [AuditIssue(path, 'duplicate_entry') for path, n in counts.items() if n > 1]
    for item in entries:
        relative = Path(item.path)
        if relative.is_absolute() or '..' in relative.parts:
            issues.append(AuditIssue(item.path, 'invalid_path'))
            continue
        raw = root / relative
        if raw.is_symlink():
            issues.append(AuditIssue(item.path, 'symlink'))
        elif not raw.is_file():
            issues.append(AuditIssue(item.path, 'missing'))
        elif manifest.sha256_file(raw) != item.sha256:
            issues.append(AuditIssue(item.path, 'hash_mismatch'))
        elif raw.stat().st_size != item.size:
            issues.append(AuditIssue(item.path, 'size_mismatch'))
    for raw in root.rglob('*'):
        if raw == file or raw.name == '.DS_Store':
            continue
        if raw.is_file() or raw.is_symlink():
            relative = raw.relative_to(root).as_posix()
            if relative not in counts:
                issues.append(AuditIssue(relative, 'unrecorded'))
    return sorted(set(issues), key=lambda item: (item.path, item.kind))

@app.command()
def main(data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')) -> None:
    try:
        issues = audit(data_dir)
    except (OSError, ValueError, TypeError, KeyError) as error:
        typer.echo(f'audit failed: {error}', err=True)
        raise typer.Exit(code=1) from error
    for issue in issues:
        typer.echo(json.dumps(asdict(issue), sort_keys=True))
    typer.echo(f'{len(issues)} raw provenance discrepancies')
    if issues:
        raise typer.Exit(code=1)

if __name__ == '__main__':
    app()
```

  Register in `cli.py` by adding the module import and:

```diff
--- a/src/embedding_data/cli.py
+++ b/src/embedding_data/cli.py
@@
-from embedding_data import acs_benchmark_extract, cps_benchmark_extract, osha_benchmark_download
+from embedding_data import (
+    acs_benchmark_extract,
+    cps_benchmark_extract,
+    manifest_audit,
+    osha_benchmark_download,
+)
```

```python
app.command('audit', help=manifest_audit.__doc__.splitlines()[0])(manifest_audit.main)
```

  An interrupted `.part` file is reported as unrecorded, rather than hidden by
  the audit; empty staging directories contain no raw file and are not entries.
  `.DS_Store` is filesystem metadata, the sole file exclusion besides the manifest.

- [ ] **Step 4: Run GREEN and the existing regressions.**
  `uv run --locked pytest tests/test_manifest.py tests/test_manifest_audit.py tests/test_osha_benchmark_download.py tests/test_ita_summary.py tests/test_cli.py -q`.
  Require the missing-recorded-file tests and changed-summary-byte refusal to pass.
  Include these additional failing tests in Step 1, then re-run them here:

```python
def test_clean_tree_and_duplicate_manifest_entry(tmp_path):
    file = tmp_path / 'raw/ok.csv'
    file.parent.mkdir(parents=True)
    file.write_bytes(b'original')
    entry = manifest.describe_file(
        file,
        file.parent,
        retrieved_at=datetime(2026, 10, 13, tzinfo=UTC),
        client='fixture',
        client_version='1',
    )
    ledger = paths.manifest_path(tmp_path)
    manifest.append_entries(ledger, [entry])
    assert manifest_audit.audit(tmp_path) == []
    ledger.write_text(ledger.read_text() * 2)
    assert manifest_audit.audit(tmp_path) == [
        manifest_audit.AuditIssue('ok.csv', 'duplicate_entry')
    ]
```

- [ ] **Step 5: Commit.**
  `git add src/embedding_data/manifest.py src/embedding_data/manifest_audit.py src/embedding_data/osha_benchmark_download.py src/embedding_data/ita_summary.py src/embedding_data/cli.py tests/test_manifest.py tests/test_manifest_audit.py`
  then `git commit -m 'feat(provenance): audit raw files and verify citations'`.

### Task 2: Manifested official references and fail-loud title parser

**Files:** Create `src/embedding_data/ita_references.py` and
`tests/test_ita_references.py`; modify `pyproject.toml` and `uv.lock`.

**Interfaces:** Consumes verified `manifest.entry_for` and existing
`osha_benchmark_download.download(client, url, destination)` / `record_download`.
Produces `acquire_titles(data_dir: Path) -> list[Path]`,
`import_hud(data_dir: Path, workbook: Path, quarter: str) -> Path`,
`parse_titles(raw: pl.DataFrame, vintage: int) -> pl.DataFrame`, and
`read_titles(data_dir: Path) -> pl.DataFrame` with
`vintage: Int64, code: String, title: String`. Quarter syntax is `YYYYQ[1-4]`.
`read_hud(file: Path) -> pl.DataFrame` validates the manual workbook before import.

The URLs are official Census structure files, verified against the
[NAICS page](https://www.census.gov/naics/), and the source cache/parser of
the classification-codes skill. Do not substitute the Nonemployer Statistics
industry descriptions: that program's coverage is not the full NAICS structure.
[Polars' calamine engine](https://docs.pola.rs/api/python/version/1/reference/api/polars.read_excel.html)
reads both XLS and XLSX via fastexcel without pandas.

- [ ] **Step 1: Write the failing parser/acquisition tests.**

```python
import httpx
import polars as pl
import pytest

from embedding_data import ita_references, manifest, paths

def test_title_parser_handles_preamble_ranges_and_trilateral_marker():
    raw = pl.DataFrame(
        {
            'a': ['2017 NAICS Structure', '2017 NAICS Code', '31-33', '332312'],
            'b': [None, '2017 NAICS Title', 'ManufacturingT', 'Fabricated Structural Metal'],
            'c': [None, 'Change Indicator', None, None],
        }
    )
    titles = ita_references.parse_titles(raw, 2017)
    assert titles.to_dicts() == [
        {
            'vintage': 2017,
            'code': '31-33',
            'title': 'Manufacturing'
        },
        {
            'vintage': 2017,
            'code': '332312',
            'title': 'Fabricated Structural Metal'
        },
    ]
    with pytest.raises(ValueError, match='header'):
        ita_references.parse_titles(raw, 2022)

def test_reference_replay_never_requests_again(tmp_path):
    requested = []

    def respond(request):
        requested.append(str(request.url))
        return httpx.Response(200, stream=httpx.ByteStream(b'fixture bytes'))

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        file = ita_references.fetch_reference(
            tmp_path,
            client,
            'https://www.census.gov/fixture.xls',
            'naics/fixture.xls',
        )
        before = paths.manifest_path(tmp_path).read_bytes()
        again = ita_references.fetch_reference(
            tmp_path,
            client,
            'https://www.census.gov/fixture.xls',
            'naics/fixture.xls',
        )
        assert again == file
        assert requested == ['https://www.census.gov/fixture.xls']
        assert paths.manifest_path(tmp_path).read_bytes() == before
        file.unlink()
        with pytest.raises(FileNotFoundError):
            ita_references.fetch_reference(
                tmp_path,
                client,
                'https://www.census.gov/fixture.xls',
                'naics/fixture.xls',
            )
        assert len(requested) == 1

def test_manual_hud_import_validates_and_records_import_time_proxy(tmp_path, monkeypatch):
    workbook = tmp_path / 'ZIP_COUNTY_122025.xlsx'
    workbook.write_bytes(b'original manual workbook')
    monkeypatch.setattr(
        pl, 'read_excel', lambda *args, **kwargs: pl.DataFrame(
            {
                'ZIP': ['2134'],
                'COUNTY': ['25025'],
                'BUS_RATIO': ['1.0'],
            }
        )
    )
    file = ita_references.import_hud(tmp_path, workbook, '2025Q4')
    assert file.read_bytes() == workbook.read_bytes()
    entry = manifest.entry_for(paths.manifest_path(tmp_path), file)
    assert entry.client == 'manual-import'
    assert entry.proxies == ('retrieved_at', )
    before = paths.manifest_path(tmp_path).read_bytes()
    assert ita_references.import_hud(tmp_path, workbook, '2025Q4') == file
    assert paths.manifest_path(tmp_path).read_bytes() == before
    monkeypatch.setattr(
        pl, 'read_excel', lambda *args, **kwargs: pl.DataFrame({'HTML': ['login']})
    )
    with pytest.raises(ValueError, match='columns missing'):
        ita_references.import_hud(tmp_path, workbook, '2025Q3')
    assert paths.manifest_path(tmp_path).read_bytes() == before
```

- [ ] **Step 2: Run RED.** `uv run --locked pytest tests/test_ita_references.py -q`.
  Expected failure: new module is absent.

- [ ] **Step 3: Add fastexcel and implement references.** Run `uv add fastexcel`;
  commit the dependency and lock with this task. Do not upgrade other dependencies.
  Create the module:

```python
'''Acquire immutable official ITA verification references and read NAICS titles.'''

import re
import shutil
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import httpx
import polars as pl

from embedding_data import manifest, paths
from embedding_data.osha_benchmark_download import download, record_download

TITLE_FILES = {
    2012: 'https://www.census.gov/naics/2012NAICS/2012_NAICS_Structure.xls',
    2017: 'https://www.census.gov/naics/2017NAICS/2017_NAICS_Structure.xlsx',
    2022: 'https://www.census.gov/naics/2022NAICS/2022_NAICS_Structure.xlsx',
}
HUD_SOURCE = 'https://www.huduser.gov/portal/datasets/usps_crosswalk.html'
CODE_PATTERN = r'^(?:[0-9]{2,6}|31-33|44-45|48-49)$'

def reference_path(data_dir: Path, relative: str) -> Path:
    return paths.raw_dir(data_dir, 'references') / relative

def existing_reference(data_dir: Path, file: Path) -> bool:
    try:
        manifest.recorded_entry_for(paths.manifest_path(data_dir), file)
    except KeyError:
        if file.exists():
            raise ValueError(f'{file}: exists without recorded provenance') from None
        return False
    manifest.entry_for(paths.manifest_path(data_dir), file)
    return True

def fetch_reference(data_dir: Path, client: httpx.Client, url: str, relative: str) -> Path:
    file = reference_path(data_dir, relative)
    if existing_reference(data_dir, file):
        return file
    file.parent.mkdir(parents=True, exist_ok=True)
    download(client, url, file)
    record_download(paths.manifest_path(data_dir), file, url)
    return file

def acquire_titles(data_dir: Path) -> list[Path]:
    destinations = [
        reference_path(data_dir, 'naics/' + url.rsplit('/', 1)[1]) for url in TITLE_FILES.values()
    ]
    for file in destinations:
        existing_reference(data_dir, file)
    with httpx.Client(http2=True, follow_redirects=True, timeout=120) as client:
        return [
            fetch_reference(data_dir, client, url, 'naics/' + url.rsplit('/', 1)[1])
            for url in TITLE_FILES.values()
        ]

def import_hud(data_dir: Path, workbook: Path, quarter: str) -> Path:
    if not re.fullmatch(r'[0-9]{4}Q[1-4]', quarter):
        raise ValueError('quarter must be YYYYQ1 through YYYYQ4')
    read_hud(workbook)
    file = reference_path(data_dir, f'hud/{quarter}/{workbook.name}')
    if existing_reference(data_dir, file):
        if manifest.sha256_file(workbook) != manifest.sha256_file(file):
            raise ValueError('this quarter/name already records different bytes')
        return file
    file.parent.mkdir(parents=True, exist_ok=True)
    partial = file.with_name(file.name + '.part')
    try:
        shutil.copyfile(workbook, partial)
        partial.replace(file)
    finally:
        partial.unlink(missing_ok=True)
    entry = manifest.describe_file(
        file,
        paths.manifest_path(data_dir).parent,
        retrieved_at=datetime.now(UTC),
        client='manual-import',
        client_version=version('embedding-data'),
        source_url=HUD_SOURCE,
        proxies=('retrieved_at', ),
    )
    manifest.append_entries(paths.manifest_path(data_dir), [entry])
    return file

def read_hud(file: Path) -> pl.DataFrame:
    raw = pl.read_excel(file, read_options={'dtypes': 'string'})
    raw.columns = [name.strip().upper() for name in raw.columns]
    if not {'ZIP', 'COUNTY', 'BUS_RATIO'}.issubset(raw.columns):
        raise ValueError('HUD ZIP/COUNTY/BUS_RATIO columns missing')
    result = raw.lazy().select(
        zip_key=pl.col('ZIP').str.strip_chars().str.replace(r'\.0$', '').str.zfill(5),
        county_geoid=pl.col('COUNTY').str.strip_chars().str.replace(r'\.0$', '').str.zfill(5),
        bus_ratio=pl.col('BUS_RATIO').cast(pl.Float64, strict=True),
    ).sort('zip_key', 'county_geoid').collect()
    invalid = result.filter(
        pl.col('zip_key').str.contains(r'^[0-9]{5}$').not_().or_(
            pl.col('county_geoid').str.contains(r'^[0-9]{5}$').not_()
        ).or_(pl.col('bus_ratio').is_null()).or_(pl.col('bus_ratio').is_finite().not_()).or_(
            pl.col('bus_ratio').is_between(0, 1).not_()
        )
    )
    if invalid.height or result.is_empty() or result.select('zip_key',
                                                            'county_geoid').is_duplicated().any():
        raise ValueError('invalid or duplicate HUD candidates')
    return result

def parse_titles(raw: pl.DataFrame, vintage: int) -> pl.DataFrame:
    for index, row in enumerate(raw.rows()):
        cells = [str(value).strip() for value in row if value is not None]
        heading = ' | '.join(cells).lower()
        if len(cells) >= 2 and all(token in heading for token in (str(vintage), 'code', 'title')):
            names = [
                str(value).strip() if value is not None else f'column_{i}'
                for i, value in enumerate(row)
            ]
            body = raw.slice(index + 1)
            body.columns = names
            break
    else:
        raise ValueError(f'{vintage}: NAICS header not found')
    code_columns = [name for name in names if 'code' in name.lower()]
    title_columns = [name for name in names if 'title' in name.lower()]
    if len(code_columns) != 1 or len(title_columns) != 1:
        raise ValueError(f'{vintage}: ambiguous code/title header')
    result = (
        body.lazy().select(
            vintage=pl.lit(vintage, dtype=pl.Int64),
            code=pl.col(code_columns[0]).cast(pl.String
                                              ).str.strip_chars().str.replace(r'\.0$', ''),
            title=pl.col(title_columns[0]).cast(pl.String).str.strip_chars(),
        ).filter(pl.col('code').str.contains(CODE_PATTERN)).with_columns(
            title=pl.col('title').str.replace(r'([a-z)])T$', '${1}')
        ).sort('code').collect()
    )
    if result.is_empty() or result['code'].n_unique() != result.height:
        raise ValueError(f'{vintage}: empty or duplicate NAICS codes')
    if result['title'].null_count() or result.filter(pl.col('title').eq('')).height:
        raise ValueError(f'{vintage}: missing title')
    return result

def read_titles(data_dir: Path) -> pl.DataFrame:
    frames = []
    expected = {2012: (2209, 1065), 2017: (2196, 1057), 2022: (2125, 1012)}
    for vintage, url in TITLE_FILES.items():
        file = reference_path(data_dir, 'naics/' + url.rsplit('/', 1)[1])
        manifest.entry_for(paths.manifest_path(data_dir), file)
        raw = pl.read_excel(file, has_header=False, read_options={'dtypes': 'string'})
        frame = parse_titles(raw, vintage)
        actual = (frame.height, frame.filter(pl.col('code').str.len_chars().eq(6)).height)
        if actual != expected[vintage]:
            raise ValueError(f'{vintage}: structure counts changed: {actual}')
        frames.append(frame)
    return pl.concat(frames).sort('vintage', 'code')
```

  The structure count invariants come from classification-codes' authoritative
  cached structures. A changed count is a layout/content checkpoint, not a
  reason to silently truncate the reference. This stage emits title tables,
  not the parent/edge/concordance tables Stage 4 will build.

- [ ] **Step 4: Run GREEN.** `uv run --locked pytest tests/test_ita_references.py -q`
  and `uv lock --check`. Exercise the full XLS/XLSX reader at Task 6; the
  offline parser test uses a tiny in-memory representation of the header layout.

- [ ] **Step 5: Commit.**
  `git add src/embedding_data/ita_references.py tests/test_ita_references.py pyproject.toml uv.lock`
  then `git commit -m 'feat(ita): acquire and validate official verification references'`.

### Task 3: V1 text content and V2 linkage measurements

**Files:** Create `src/embedding_data/ita_verification.py` and
`tests/test_ita_verification.py`.

**Interfaces:** Consumes a stacked `pl.LazyFrame` and Task 2's title frame.
Produces `with_keys(lf) -> pl.LazyFrame`, `description_report(lf, titles) -> pl.DataFrame`,
`link_report(lf, base_year, later_year) -> dict`, and `quality_report(lf) -> pl.DataFrame`.
No normalization changes the source Parquet.

- [ ] **Step 1: Write tests with hand-calculated results.**

```python
import polars as pl

from embedding_data import ita_verification as verify

def rows(records):
    base = {
        'year_filing_for': 2023,
        'id': 1,
        'establishment_id': 10,
        'ein': '012345678',
        'company_name': 'Acme',
        'establishment_name': 'Plant',
        'street_address': '1 Main St',
        'city': 'Town',
        'state': 'MA',
        'zip_code': '02134',
        'industry_description': 'Steel',
        'naics_year': 2022,
        'naics_code': '332312',
        'source_file': 'osha/fixture.csv',
    }
    return pl.DataFrame([{**base, **item} for item in records]).lazy()

def test_unicode_and_employer_missingness():
    assert verify.normalize_key('  STRAßE\u00a0Steel  ') == 'strasse steel'
    out = verify.with_keys(
        rows(
            [
                {
                    'ein': None,
                    'company_name': None
                },
                {
                    'id': 2,
                    'ein': '12345678',
                    'industry_description': ' N/A '
                },
            ]
        )
    ).collect()
    assert out['employer_key'].to_list() == [None, 'ein:012345678']
    assert out['flag_ein_padded'].to_list() == [False, True]
    assert out['flag_placeholder'].to_list() == [False, True]

def test_description_repetition_never_groups_unknown_employers():
    lf = rows(
        [
            {
                'industry_description': ' Manufacturing '
            },
            {
                'id': 2,
                'industry_description': 'MANUFACTURING'
            },
            {
                'id': 3,
                'ein': None,
                'company_name': None,
                'industry_description': None
            },
            {
                'id': 4,
                'ein': None,
                'company_name': None,
                'industry_description': 'N/A'
            },
        ]
    )
    titles = pl.DataFrame({'vintage': [2022], 'code': ['31-33'], 'title': ['Manufacturing']})
    report = verify.description_report(lf, titles).row(0, named=True)
    assert report['n_rows'] == 4
    assert report['n_empty'] == 1 and report['n_placeholder'] == 1
    assert report['n_copied_any'] == 2 and report['n_employer_unknown'] == 2
    assert report['n_repeat_rows'] == 2 and report['n_repeat_excess'] == 1

def test_link_denominators_null_ein_collisions_and_changed_id():
    lf = rows(
        [
            {},
            {},  # Exact duplicate, one cohort ID after collapsing.
            {
                'id': 2,
                'establishment_id': 20,
                'ein': None,
                'street_address': '2 Main St'
            },
            {
                'id': 3,
                'establishment_id': 30,
                'street_address': '3 Main St'
            },
            {
                'year_filing_for': 2024,
                'id': 4
            },
            {
                'year_filing_for': 2024,
                'id': 5,
                'establishment_id': 20,
                'ein': None,
                'street_address': '2 Main St'
            },
            {
                'year_filing_for': 2024,
                'id': 6,
                'establishment_id': 31,
                'street_address': '3 Main St'
            },
        ]
    )
    out = verify.link_report(lf, 2023, 2024)
    assert out['n_cohort_ids'] == 3 and out['n_unique_cohort_ids'] == 3
    assert out['n_reappeared'] == 2 and out['n_same_ein_address'] == 1
    assert out['n_reappeared_ein_unknown'] == 1
    assert out['n_unique_address_matches'] == 2
    assert out['n_address_matches_different_id'] == 1
    conflict = pl.concat(
        [lf, rows([
            {
                'year_filing_for': 2024,
                'id': 7,
                'street_address': 'Other Street'
            },
        ])]
    )
    assert verify.link_report(conflict, 2023, 2024)['n_same_ein_address'] == 0
```

- [ ] **Step 2: Run RED.** `uv run --locked pytest tests/test_ita_verification.py -q`.

- [ ] **Step 3: Implement keys and reports.**

```python
'''Offline measurements for ITA text content and establishment linkage.'''

import re
import unicodedata

import polars as pl

PLACEHOLDERS = frozenset(
    {'n/a', 'na', 'none', 'unknown', 'not applicable', 'not specified', '-', '--', '.'}
)

def normalize_key(value: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())

def key(column: str) -> pl.Expr:
    return pl.col(column).fill_null('').map_elements(normalize_key, return_dtype=pl.String)

def ein_key(value: str) -> str | None:
    compact = value.strip().replace('-', '')
    if not re.fullmatch(r'[0-9]{8,9}', compact):
        return None
    padded = compact.zfill(9)
    return None if len(set(padded)) == 1 else padded

def zip_key(value: str) -> str | None:
    value = value.strip()
    if re.fullmatch(r'[0-9]{4,5}', value):
        return value.zfill(5)
    if re.fullmatch(r'[0-9]{9}|[0-9]{5}-[0-9]{4}', value):
        return value[:5]
    return None

def zip_format(value: str) -> str:
    value = value.strip()
    if not value:
        return 'missing'
    if re.fullmatch(r'[0-9]{5}', value):
        return 'five_digit'
    if re.fullmatch(r'[0-9]{4}', value):
        return 'padded_four_digit'
    if re.fullmatch(r'[0-9]{9}|[0-9]{5}-[0-9]{4}', value):
        return 'zip_plus_four'
    return 'invalid'

def with_keys(lf: pl.LazyFrame) -> pl.LazyFrame:
    return (
        lf.with_columns(
            description_key=key('industry_description'),
            company_key=key('company_name'),
            name_key=key('establishment_name'),
            street_key=key('street_address'),
            city_key=key('city'),
            state_key=key('state'),
            ein_key=pl.col('ein').fill_null('').map_elements(ein_key, return_dtype=pl.String),
            zip_key=pl.col('zip_code').fill_null('').map_elements(zip_key, return_dtype=pl.String),
            zip_format=pl.col('zip_code').fill_null('').map_elements(
                zip_format, return_dtype=pl.String
            ),
            flag_ein_padded=pl.col('ein').fill_null('').str.strip_chars().str.replace_all('-', '')
            .str.contains(r'^[0-9]{8}$'),
            flag_suspected_mojibake=pl.col('industry_description').fill_null('').str.contains(
                'Ã|Â|�'
            ),
        ).with_columns(
            employer_key=pl.when(pl.col('ein_key').is_not_null()).then(
                pl.concat_str(pl.lit('ein:'), pl.col('ein_key'))
            ).when(pl.col('company_key').ne('')).then(
                pl.concat_str(pl.lit('company:'), pl.col('company_key'))
            ).otherwise(None),
            flag_empty=pl.col('description_key').eq(''),
            flag_placeholder=pl.col('description_key').is_in(PLACEHOLDERS),
            address_key=pl.when(
                pl.col('street_key').ne('').and_(pl.col('city_key').ne('')).and_(
                    pl.col('state_key').ne('')
                ).and_(pl.col('zip_key').is_not_null())
            ).then(pl.concat_str('street_key', 'city_key', 'state_key', 'zip_key',
                                 separator='|')).otherwise(None),
        )
    )

def description_report(lf: pl.LazyFrame, titles: pl.DataFrame) -> pl.DataFrame:
    normalized_titles = titles.with_columns(title_key=key('title'))
    any_keys = normalized_titles['title_key'].unique().to_list()
    native = normalized_titles.select('vintage', 'title_key').unique().lazy()
    annotated = (
        with_keys(lf).with_columns(flag_copied_any=pl.col('description_key').is_in(any_keys)).join(
            native.with_columns(native_match=pl.lit(True)),
            left_on=['naics_year', 'description_key'],
            right_on=['vintage', 'title_key'],
            how='left',
            validate='m:1'
        )
    )
    repeats = (
        annotated.filter(
            pl.col('employer_key').is_not_null().and_(pl.col('description_key').ne(''))
        ).group_by('year_filing_for', 'employer_key', 'description_key').agg(n=pl.len()).group_by(
            'year_filing_for'
        ).agg(
            n_repeat_rows=pl.col('n').filter(pl.col('n').gt(1)).sum(),
            n_repeat_excess=pl.col('n').sub(1).sum(),
        )
    )
    length = pl.col('industry_description').fill_null('').str.len_chars()
    return (
        annotated.group_by('year_filing_for').agg(
            n_rows=pl.len(),
            n_empty=pl.col('flag_empty').sum(),
            n_placeholder=pl.col('flag_placeholder').sum(),
            n_copied_any=pl.col('flag_copied_any').sum(),
            n_native_title_match=pl.col('native_match').fill_null(False).sum(),
            n_vintage_unknown=pl.col('naics_year').is_null().sum(),
            n_employer_unknown=pl.col('employer_key').is_null().sum(),
            n_employer_company=pl.col('employer_key').str.starts_with('company:'
                                                                      ).fill_null(False).sum(),
            n_ein_padded=pl.col('flag_ein_padded').sum(),
            n_mojibake=pl.col('flag_suspected_mojibake').sum(),
            length_min=length.min(),
            length_p25=length.quantile(0.25, interpolation='nearest'),
            length_p50=length.quantile(0.50, interpolation='nearest'),
            length_p75=length.quantile(0.75, interpolation='nearest'),
            length_p95=length.quantile(0.95, interpolation='nearest'),
            length_max=length.max(),
        ).join(repeats, on='year_filing_for', how='left', validate='1:1').with_columns(
            pl.col('n_repeat_rows', 'n_repeat_excess').fill_null(0)
        ).with_columns(
            share_empty=pl.col('n_empty').truediv(pl.col('n_rows')),
            share_placeholder=pl.col('n_placeholder').truediv(pl.col('n_rows')),
            share_copied_any=pl.col('n_copied_any').truediv(pl.col('n_rows')),
            share_repeat_rows=pl.col('n_repeat_rows').truediv(pl.col('n_rows')),
            share_repeat_excess=pl.col('n_repeat_excess').truediv(pl.col('n_rows')),
            share_employer_unknown=pl.col('n_employer_unknown').truediv(pl.col('n_rows')),
            share_native_title_match=pl.when(pl.col('n_rows').gt(pl.col('n_vintage_unknown'))).then(
                pl.col('n_native_title_match').truediv(
                    pl.col('n_rows').sub(pl.col('n_vintage_unknown'))
                )
            ).otherwise(None),
        ).sort('year_filing_for').collect()
    )

def quality_report(lf: pl.LazyFrame) -> pl.DataFrame:
    columns = lf.collect_schema().names()
    raw_counts = lf.group_by('year_filing_for').agg(n_rows=pl.len())
    unique_counts = lf.unique(subset=columns).group_by('year_filing_for').agg(
        n_distinct_rows=pl.len()
    )
    return (
        with_keys(lf).group_by('year_filing_for').agg(
            n_company_empty=pl.col('company_key').eq('').sum(),
            n_ein_unusable=pl.col('ein_key').is_null().sum(),
            n_zip_unusable=pl.col('zip_key').is_null().sum(),
            n_distinct_record_ids=pl.col('id').n_unique(),
            n_distinct_establishment_ids=pl.col('establishment_id').n_unique(),
        ).join(raw_counts, on='year_filing_for', validate='1:1'
               ).join(unique_counts, on='year_filing_for', validate='1:1').with_columns(
                   n_exact_duplicate_excess=pl.col('n_rows').sub(pl.col('n_distinct_rows'))
               ).sort('year_filing_for').collect()
    )

def unique_ids(lf: pl.LazyFrame, year: int) -> pl.LazyFrame:
    return (
        with_keys(lf.filter(pl.col('year_filing_for').eq(year)).unique()).with_columns(
            n_id_rows=pl.len().over('establishment_id')
        ).filter(pl.col('n_id_rows').eq(1))
    )

def link_report(lf: pl.LazyFrame, base_year: int, later_year: int) -> dict:
    columns = ['establishment_id', 'ein', 'ein_key', 'flag_ein_padded', 'name_key', 'address_key']
    cohort = unique_ids(lf, base_year).select(columns)
    later = unique_ids(lf, later_year).select(columns)
    later = later.with_columns(id_present=pl.lit(True))
    joined = cohort.join(later, on='establishment_id', how='left', suffix='_later', validate='1:1')
    present = pl.col('id_present').fill_null(False)
    known_ein = pl.col('ein_key').is_not_null().and_(pl.col('ein_key_later').is_not_null())
    same = known_ein.and_(pl.col('ein_key').eq(pl.col('ein_key_later')))
    unreconstructed = pl.col('flag_ein_padded').not_().and_(pl.col('flag_ein_padded_later').not_())
    same_address = pl.col('address_key').is_not_null().and_(
        pl.col('address_key').eq(pl.col('address_key_later'))
    )
    counts = joined.select(
        n_unique_cohort_ids=pl.len(),
        n_reappeared=present.sum(),
        n_same_ein_address=same.and_(same_address).and_(unreconstructed).fill_null(False).sum(),
        n_same_ein_address_including_padded=same.and_(same_address).fill_null(False).sum(),
        n_same_raw_ein_address=same.and_(same_address).and_(pl.col('ein').eq(pl.col('ein_later'))
                                                            ).fill_null(False).sum(),
        n_reappeared_ein_unknown=present.and_(known_ein.not_()).sum(),
        n_reappeared_ein_conflict=present.and_(known_ein).and_(
            pl.col('ein_key').ne(pl.col('ein_key_later'))
        ).sum(),
        n_reappeared_address_conflict=present.and_(same_address.not_()).fill_null(False).sum(),
    ).collect().row(0, named=True)
    address_columns = ['ein_key', 'name_key', 'address_key']

    def unique_addresses(frame):
        return (
            frame.filter(
                pl.col('ein_key').is_not_null().and_(pl.col('flag_ein_padded').not_()).and_(
                    pl.col('address_key').is_not_null()
                ).and_(pl.col('name_key').ne(''))
            ).with_columns(n_address=pl.len().over(address_columns)).filter(
                pl.col('n_address').eq(1)
            )
        )

    addresses = unique_addresses(cohort).join(
        unique_addresses(later),
        on=address_columns,
        how='inner',
        suffix='_later',
        validate='1:1',
    ).select(
        n_unique_address_matches=pl.len(),
        n_address_matches_different_id=pl.col('establishment_id').ne(
            pl.col('establishment_id_later')
        ).sum(),
    ).collect().row(0, named=True)
    n_ids = lf.filter(pl.col('year_filing_for').eq(base_year)).select(
        pl.col('establishment_id').n_unique()
    ).collect().item()
    cohort_ids = lf.filter(pl.col('year_filing_for').eq(base_year)
                           ).select('establishment_id').unique()
    later_ids = lf.filter(pl.col('year_filing_for').eq(later_year)
                          ).select('establishment_id').unique()
    n_raw_reappeared = cohort_ids.join(later_ids, on='establishment_id',
                                       how='inner').select(pl.len()).collect().item()
    output = {
        'base_year': base_year,
        'later_year': later_year,
        'n_cohort_ids': n_ids,
        'n_raw_reappeared': n_raw_reappeared,
        **counts,
        **addresses
    }
    output['share_raw_reappeared'] = n_raw_reappeared / n_ids if n_ids else None
    output['share_same_ein_address'] = counts['n_same_ein_address'] / n_ids if n_ids else None
    address_n = addresses['n_unique_address_matches']
    output['share_address_matches_different_id'
           ] = addresses['n_address_matches_different_id'] / address_n if address_n else None
    return output
```

  The explicit `id_present` sentinel counts a reappearing ID even when the
  target address is unusable. A field's completeness is not row existence.

  Report each integer's denominator in Task 6. Description flags overlap;
  do not sum them as a partition. A known-vintage title rate uses known-vintage
  rows, while `n_copied_any / n_rows` covers unknown vintages conservatively.
  `n_repeat_excess` is the number removed by employer/description dedup among
  non-empty descriptions with usable employer keys; unknown-employer rows
  never join one another. No raw `ein`, description or address is overwritten.

- [ ] **Step 4: Run GREEN.** `uv run --locked pytest tests/test_ita_verification.py -q`.
  Add the following explicit sentinel regression before passing this milestone:

```python
def test_reappearing_id_with_unusable_address_is_still_present():
    lf = rows([{}, {'year_filing_for': 2024, 'id': 2, 'street_address': ''}])
    out = verify.link_report(lf, 2023, 2024)
    assert out['n_reappeared'] == 1
    assert out['n_same_ein_address'] == 0
```

- [ ] **Step 5: Commit.**
  `git add src/embedding_data/ita_verification.py tests/test_ita_verification.py`
  then `git commit -m 'feat(ita): measure description content and conservative ID linkage'`.

### Task 4: Reproducible V3 sample and offline county comparison

**Files:** Create `src/embedding_data/ita_county_verification.py` and
`tests/test_ita_county_verification.py`.

**Interfaces:** Consumes Task 3's keys and a manifested HUD workbook. Produces
`read_hud(file: Path) -> pl.DataFrame`, `zip_candidates(frame) -> pl.DataFrame`,
`stratified_sample(lf, candidates, per_stratum=8) -> pl.DataFrame`,
`parse_geocodes(text: str) -> pl.DataFrame`, and
`county_report(sample, geocodes) -> tuple[pl.DataFrame, dict]`.
Sample rows have stable `row_key`, `stratum`, `population_n`, `sample_n`,
`inclusion_probability`, and `sample_weight`, beside delivered fields/keys.

Sources: [HUD crosswalk documentation](https://www.huduser.gov/portal/datasets/usps_crosswalk.html)
defines `BUS_RATIO` and identifies the login requirement, quarterly snapshots,
multi-county ZIPs and absent PO-box-only ZIPs.
[Census API](https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html)
defines the geography batch format and its 10,000-address limit.
[Census FAQ](https://www2.census.gov/geo/pdfs/maps-data/data/Census_Geocoder_FAQ.pdf)
warns that batch match counts can vary with service load: immutable response
caching is essential. Address-range coordinates are interpolated; `Exact`
means the service's address-match class, not verified rooftop coordinates.

- [ ] **Step 1: Write the failing sample and response tests.** Reuse `rows`
  from Task 3 by placing it in `tests/ita_verification_fixtures.py` and importing
  it into both test modules; move the helper unchanged, not the tests.

```python
import polars as pl
import pytest
from ita_verification_fixtures import rows
from polars.testing import assert_frame_equal

from embedding_data import ita_county_verification as county

def hud_rows():
    return pl.DataFrame(
        {
            'zip_key': ['02134', '02135', '02135', '06001'],
            'county_geoid': ['25025', '25025', '25017', '09003'],
            'bus_ratio': [1.0, 0.6, 0.4, 1.0],
        }
    )

def test_candidates_retain_ambiguity_and_ct_vintage():
    result = county.zip_candidates(hud_rows()).sort('zip_key')
    assert result['n_business_counties'].to_list() == [1, 2, 1]
    assert result['zip_single_county'].to_list() == ['25025', None, None]
    assert result['flag_zip_legacy_ct'].to_list() == [False, False, True]

def test_sample_is_stable_with_duplicate_and_conflicting_record_ids():
    lf = rows(
        [
            {}, {}, {
                'industry_description': 'Other'
            }, {
                'id': 2,
                'zip_code': 'bad'
            }, {
                'year_filing_for': 2024,
                'id': 3
            }
        ]
    )
    candidates = county.zip_candidates(hud_rows())
    sample = county.stratified_sample(lf, candidates, per_stratum=1)
    shuffled = county.stratified_sample(lf.collect().reverse().lazy(), candidates, per_stratum=1)
    assert_frame_equal(sample, shuffled)
    assert sample['row_key'].n_unique() == sample.height
    assert sample.height == 3
    assert sorted(sample['population_n'].to_list()) == [1, 1, 2]
    assert sample['sample_weight'].sum() == 4

def test_parser_supports_matches_no_matches_and_ties():
    text = (
        'a,"1 Main St,Town,MA,02134",Match,Exact,matched,"-71,42",7,L,25,025,1,1\n'
        'b,"bad",No_Match\n'
        'c,"ambiguous",Tie\n'
    )
    result = county.parse_geocodes(text)
    assert result['county_geoid'].to_list() == ['25025', None, None]
    with pytest.raises(ValueError, match='duplicate'):
        county.parse_geocodes(text + 'b,"bad",No_Match\n')

def test_coverage_and_agreement_use_separate_denominators():
    sample = county.stratified_sample(
        rows(
            [
                {},
                {
                    'id': 2,
                    'zip_code': '02135'
                },
                {
                    'id': 3,
                    'zip_code': 'bad'
                },
                {
                    'id': 4,
                    'zip_code': '06001',
                    'state': 'CT'
                },
            ]
        ), county.zip_candidates(hud_rows())
    )
    geocodes = sample.select('row_key').with_columns(
        geocode_status=pl.lit('Match'),
        match_type=pl.lit('Exact'),
        county_geoid=pl.when(pl.Series(sample['state'].to_list()).eq('CT')
                             ).then(pl.lit('09110')).otherwise(pl.lit('25025')),
    )
    _, result = county.county_report(sample, geocodes)
    assert result['n_sample'] == 4
    assert result['n_geocode_exact'] == 4
    assert result['n_zip_covered'] == 3
    assert result['n_zip_single_compatible'] == 1
    assert result['n_joint_dominant_comparable'] == 2
    assert result['n_joint_dominant_agree'] == 2
    assert result['n_ct_incomparable'] == 1
    assert result['n_joint_single_comparable'] == 1
    assert result['n_joint_single_agree'] == 1
    assert result['share_zip_single_compatible'] == 0.25
    assert result['share_joint_single_agree'] == 1.0

def test_status_scope_and_incompatible_geocoder_are_reported():
    sample = county.stratified_sample(
        rows(
            [
                {},
                {
                    'id': 2
                },
                {
                    'id': 3
                },
                {
                    'id': 4
                },
                {
                    'id': 5,
                    'state': 'PR'
                },
                {
                    'id': 6,
                    'state': 'CT',
                    'zip_code': '06001'
                },
            ]
        ), county.zip_candidates(hud_rows())
    )
    statuses = [
        ('Match', 'Exact', '25025'), ('Match', 'Non_Exact', '25025'), ('No_Match', None, None),
        ('Tie', None, None), ('Match', 'Exact', '72001'), ('Match', 'Exact', '09003')
    ]
    geocodes = sample.sort('id').select('row_key').hstack(
        pl.DataFrame(
            statuses,
            schema=['geocode_status', 'match_type', 'county_geoid'],
            orient='row',
        )
    )
    _, result = county.county_report(sample, geocodes)
    assert result['n_geocode_non_exact'] == 1
    assert result['n_geocode_no_match'] == 1
    assert result['n_geocode_tie'] == 1
    assert result['n_geocode_legacy_ct'] == 1
    assert result['n_out_of_scope'] == 1
    assert result['n_proposed_assignable'] == 4
    assert result['share_joint_single_agree'] == 1.0
```

- [ ] **Step 2: Run RED.** `uv run --locked pytest tests/test_ita_county_verification.py -q`.

- [ ] **Step 3: Implement the county comparison module.**

```python
'''Sample and compare ITA county methods offline from manifested references/responses.'''

import csv
import hashlib
import io
import json
import re

import polars as pl

from embedding_data.ita_references import read_hud  # noqa: F401 - county input interface
from embedding_data.ita_verification import with_keys

SAMPLE_SALT = 'embedding-data:V3:2026-10-13:v1'
OUT_OF_SCOPE_STATES = ('PR', 'VI', 'GU', 'AS', 'MP', 'UM')

def zip_candidates(frame: pl.DataFrame) -> pl.DataFrame:
    positive = frame.lazy().filter(pl.col('bus_ratio').gt(0))
    maxima = pl.col('bus_ratio').eq(pl.col('bus_ratio').max())
    return (
        positive.group_by('zip_key').agg(
            n_business_counties=pl.len(),
            business_counties=pl.col('county_geoid').sort(),
            max_business_ratio=pl.col('bus_ratio').max(),
            dominant_candidates=pl.col('county_geoid').filter(maxima).sort(),
            flag_zip_legacy_ct=pl.col('county_geoid').str.starts_with('090').any(),
        ).with_columns(
            zip_dominant_county=pl.when(pl.col('dominant_candidates').list.len().eq(1)).then(
                pl.col('dominant_candidates').list.first()
            ).otherwise(None),
            zip_single_county=pl.when(
                pl.col('n_business_counties').eq(1).and_(pl.col('flag_zip_legacy_ct').not_())
            ).then(pl.col('business_counties').list.first()).otherwise(None),
        ).sort('zip_key').collect()
    )

def content_key(row: dict) -> str:
    text = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def stratified_sample(
    lf: pl.LazyFrame, candidates: pl.DataFrame, per_stratum: int = 8
) -> pl.DataFrame:
    if per_stratum < 1:
        raise ValueError('per_stratum must be positive')
    columns = sorted(lf.collect_schema().names())
    population = (
        with_keys(lf.unique()).with_columns(
            row_key=pl.struct(columns).map_elements(content_key, return_dtype=pl.String)
        ).join(candidates.lazy(), on='zip_key', how='left', validate='m:1').with_columns(
            n_business_counties=pl.col('n_business_counties').fill_null(0),
            flag_zip_legacy_ct=pl.col('flag_zip_legacy_ct').fill_null(False)
        ).with_columns(
            county_count_class=pl.when(pl.col('n_business_counties').eq(0)
                                       ).then(pl.lit('none')).when(
                                           pl.col('n_business_counties').eq(1)
                                       ).then(pl.lit('single')).otherwise(pl.lit('multiple')),
            rank_key=pl.col('row_key').map_elements(
                lambda value: hashlib.sha256((SAMPLE_SALT + value).encode()).hexdigest(),
                return_dtype=pl.String,
            ),
        ).with_columns(
            stratum=pl.concat_str(
                pl.col('year_filing_for').cast(pl.String),
                'state',
                'zip_format',
                'county_count_class',
                separator='|',
            )
        ).with_columns(population_n=pl.len().over('stratum')).sort(
            'stratum', 'rank_key', 'row_key'
        ).group_by('stratum', maintain_order=True).head(per_stratum).with_columns(
            sample_n=pl.len().over('stratum')
        ).with_columns(
            inclusion_probability=pl.col('sample_n').truediv(pl.col('population_n')),
            sample_weight=pl.col('population_n').truediv(pl.col('sample_n'))
        )
    )
    return population.sort('stratum', 'row_key').collect()

def parse_geocodes(text: str) -> pl.DataFrame:
    records = []
    for row in csv.reader(io.StringIO(text)):
        if not row:
            continue
        if len(row) < 3 or row[2] not in ('Match', 'No_Match', 'Tie'):
            raise ValueError('unrecognized Census batch response')
        status = row[2]
        match_type = row[3] if status == 'Match' and len(row) >= 4 else None
        geoid = None
        if status == 'Match':
            if len(row) < 12 or not re.fullmatch(r'[0-9]{2}', row[8]) or not re.fullmatch(
                r'[0-9]{3}', row[9]
            ):
                raise ValueError('Census geography match lacks valid state/county codes')
            geoid = row[8] + row[9]
        records.append((row[0], status, match_type, geoid))
    result = pl.DataFrame(
        records,
        schema={
            'row_key': pl.String,
            'geocode_status': pl.String,
            'match_type': pl.String,
            'county_geoid': pl.String,
        },
        orient='row'
    )
    if result['row_key'].n_unique() != result.height:
        raise ValueError('duplicate Census response ID')
    return result

def county_report(sample: pl.DataFrame, geocodes: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    sample_ids = set(sample['row_key'].to_list())
    if sample_ids != set(geocodes['row_key'].to_list()) or geocodes.height != sample.height:
        raise ValueError('sample/response IDs do not match exactly')
    compared = (
        sample.lazy().join(geocodes.lazy(), on='row_key', validate='1:1').with_columns(
            flag_out_of_scope=pl.col('state').is_in(OUT_OF_SCOPE_STATES),
            flag_geocode_legacy_ct=pl.col('county_geoid').str.starts_with('090').fill_null(False),
            geocode_non_exact=pl.col('geocode_status').eq('Match').and_(
                pl.col('match_type').ne('Exact')
            ).fill_null(False),
            geocode_no_match=pl.col('geocode_status').eq('No_Match'),
            geocode_tie=pl.col('geocode_status').eq('Tie'),
            zip_covered=pl.col('n_business_counties').gt(0),
            zip_single_compatible=pl.col('zip_single_county').is_not_null(),
        ).with_columns(
            geocode_exact=pl.col('geocode_status').eq('Match').and_(
                pl.col('match_type').eq('Exact')
            ).and_(pl.col('county_geoid').is_not_null()).and_(
                pl.col('flag_geocode_legacy_ct').not_()
            ).fill_null(False),
        ).with_columns(
            joint_dominant_comparable=pl.col('geocode_exact').and_(
                pl.col('zip_dominant_county').is_not_null()
            ).and_(pl.col('flag_zip_legacy_ct').not_()).and_(pl.col('flag_out_of_scope').not_()),
            joint_single_comparable=pl.col('geocode_exact').and_(pl.col('zip_single_compatible'))
            .and_(pl.col('flag_out_of_scope').not_()),
            proposed_assignable=pl.col('geocode_exact').or_(pl.col('zip_single_compatible')).and_(
                pl.col('flag_out_of_scope').not_()
            ),
        ).with_columns(
            joint_dominant_agree=pl.col('joint_dominant_comparable').and_(
                pl.col('county_geoid').eq(pl.col('zip_dominant_county'))
            ).fill_null(False),
            joint_single_agree=pl.col('joint_single_comparable').and_(
                pl.col('county_geoid').eq(pl.col('zip_single_county'))
            ).fill_null(False),
        )
    )
    flags = {
        'n_geocode_exact': 'geocode_exact',
        'n_zip_covered': 'zip_covered',
        'n_zip_single_compatible': 'zip_single_compatible',
        'n_joint_dominant_comparable': 'joint_dominant_comparable',
        'n_joint_dominant_agree': 'joint_dominant_agree',
        'n_joint_single_comparable': 'joint_single_comparable',
        'n_joint_single_agree': 'joint_single_agree',
        'n_proposed_assignable': 'proposed_assignable',
        'n_geocode_non_exact': 'geocode_non_exact',
        'n_geocode_no_match': 'geocode_no_match',
        'n_geocode_tie': 'geocode_tie',
        'n_geocode_legacy_ct': 'flag_geocode_legacy_ct',
        'n_ct_incomparable': 'flag_zip_legacy_ct',
        'n_out_of_scope': 'flag_out_of_scope',
    }
    strata = (
        compared.group_by('stratum').agg(
            population_n=pl.col('population_n').first(),
            n_sample=pl.len(),
            **{
                name: pl.col(column).sum()
                for name, column in flags.items()
            },
        ).sort('stratum').collect()
    )
    overall = compared.select(
        n_sample=pl.len(),
        n_population=pl.col('sample_weight').sum(),
        **{
            name: pl.col(column).sum()
            for name, column in flags.items()
        },
        **{
            'weighted_' + name: pl.col(column).cast(pl.Float64).mul(pl.col('sample_weight')).sum()
            for name, column in flags.items()
        },
    ).collect().row(0, named=True)
    denominators = {name: 'n_sample' for name in flags}
    denominators.update(
        n_joint_dominant_agree='n_joint_dominant_comparable',
        n_joint_single_agree='n_joint_single_comparable'
    )
    for name, denominator in denominators.items():
        total = overall[denominator]
        overall['share_' + name[2:]] = overall[name] / total if total else None
        weighted_total = (
            overall['n_population']
            if denominator == 'n_sample' else overall['weighted_' + denominator]
        )
        overall['weighted_share_' + name[2:]] = (
            overall['weighted_' + name] / weighted_total if weighted_total else None
        )
    return strata, overall
```

  County coverage means at least one positive business-ratio county; it is
  different from a single usable assignment. The dominant-county comparison
  excludes tied maxima and incompatible Connecticut codes. Show agreement for
  single-county ZIPs as an additional diagnostic at Task 6; no single-county
  conversion is applied to ambiguous ZIPs by this investigation.

- [ ] **Step 4: Run GREEN.** `uv run --locked pytest tests/test_ita_verification.py tests/test_ita_county_verification.py -q`.
  Assert sorted sample rows and stratum counts agree across input reorderings.

- [ ] **Step 5: Commit.**
  `git add src/embedding_data/ita_county_verification.py tests/test_ita_county_verification.py tests/ita_verification_fixtures.py tests/test_ita_verification.py`
  then `git commit -m 'feat(ita): compare county methods on a reproducible stratified sample'`.

### Task 5: Explicit acquisition and fully offline report runner

**Files:** Create `src/embedding_data/ita_verification_run.py` and
`tests/test_ita_verification_run.py`; modify README and CLAUDE command/provenance
paragraphs. No new top-level extract command besides Task 1's `audit`.

**Interfaces:** Consumes Tasks 1–4. Produces a run directory under
`data/derived/osha/verification/<run_id>/` with `sample.parquet`, headerless batch
`requests/*.csv`, `inputs.json`, `geocoding.json`, `reports.json`, per-year V1 and
quality Parquets, V2 JSON, V3 strata Parquet, and `finding.md`. Raw reference and
response files remain under `raw/references/`; the raw manifest covers them.

- [ ] **Step 1: Write the failing offline runner test.**

```python
import csv
import io
import json
import re

import httpx
import polars as pl
import pytest
from ita_fixtures import record, write_release, year_file

from embedding_data import ita_references as refs
from embedding_data import ita_verification_run as run
from embedding_data import paths
from embedding_data.osha_benchmark_download import record_download

def test_raw_summary_to_cached_offline_reports(tmp_path, monkeypatch):
    monkeypatch.setattr(run, 'BATCH_LIMIT', 3)
    for year in range(2016, 2026):
        write_release(
            tmp_path, year,
            year_file(year, [record(year, state='MA', city='Town', establishment_id='10')])
        )
    for url in refs.TITLE_FILES.values():
        file = refs.reference_path(tmp_path, 'naics/' + url.rsplit('/', 1)[1])
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b'fixture workbook boundary')
        record_download(paths.manifest_path(tmp_path), file, url)
    hud = refs.reference_path(tmp_path, 'hud/2025Q4/fixture.xlsx')
    hud.parent.mkdir(parents=True, exist_ok=True)
    hud.write_bytes(b'fixture HUD workbook boundary')
    record_download(paths.manifest_path(tmp_path), hud, refs.HUD_SOURCE)
    # Only small-workbook I/O boundaries are replaced; real raw harmonization,
    # normalization, sampling, response parsing and report transforms run.
    monkeypatch.setattr(
        refs, 'read_titles', lambda _: pl.DataFrame(
            {
                'vintage': [2022],
                'code': ['31-33'],
                'title': ['Manufacturing'],
            }
        )
    )
    monkeypatch.setattr(
        run.county, 'read_hud', lambda _: pl.DataFrame(
            {
                'zip_key': ['02134'],
                'county_geoid': ['25025'],
                'bus_ratio': [1.0],
            }
        )
    )
    directory = run.prepare(tmp_path, hud, 'fixture')
    batches = sorted((directory / 'requests').glob('*.csv'))
    assert len(batches) == 4
    assert all(len(list(csv.reader(file.open()))) <= 3 for file in batches)

    def respond(request):
        if request.url.path.endswith('/benchmarks'):
            return httpx.Response(
                200,
                stream=httpx.ByteStream(
                    json.dumps(
                        {
                            'benchmarks': [{
                                'id': '4',
                                'benchmarkName': 'Public_AR_Current',
                            }]
                        }
                    ).encode()
                )
            )
        if request.url.path.endswith('/vintages'):
            return httpx.Response(
                200,
                stream=httpx.ByteStream(
                    json.dumps({
                        'vintages': [{
                            'id': '425',
                            'vintageName': 'ACS2025_Current',
                        }]
                    }).encode()
                )
            )
        output = io.StringIO()
        writer = csv.writer(output)
        filename = re.search(rb'filename="([^"]+)"', request.content).group(1).decode()
        with (directory / 'requests' / filename).open(newline='') as stream:
            row_keys = [row[0] for row in csv.reader(stream)]
        for row_key in row_keys:
            writer.writerow(
                [
                    row_key, 'address', 'Match', 'Exact', 'matched', '-71,42', '7', 'L', '25',
                    '025', '1', '1'
                ]
            )
        return httpx.Response(200, content=output.getvalue().encode())

    monkeypatch.setattr(
        run, 'make_client', lambda: httpx.Client(transport=httpx.MockTransport(respond))
    )
    run.acquire_geocodes(tmp_path, 'fixture')
    monkeypatch.setattr(
        run, 'make_client', lambda: (_ for _ in ()).throw(AssertionError('network'))
    )
    before = paths.manifest_path(tmp_path).read_bytes()
    first = run.measure(tmp_path, 'fixture')
    second = run.measure(tmp_path, 'fixture')
    assert first == second
    assert first['v3_overall']['n_sample'] == 10
    assert {item['year_filing_for'] for item in first['v1']} == set(range(2016, 2026))
    assert paths.manifest_path(tmp_path).read_bytes() == before
    assert all(
        item['n_same_ein_address'] == 1 for item in first['v2'] if item['base_year'] == 2023
    )
    original = batches[0].read_bytes()
    batches[0].write_bytes(original + b'changed')
    with pytest.raises(ValueError, match='input changed'):
        run.measure(tmp_path, 'fixture')
    batches[0].write_bytes(original)
    with monkeypatch.context() as patch:
        patch.setattr(run, 'version', lambda _: 'changed')
        with pytest.raises(ValueError, match='dependency version changed'):
            run.measure(tmp_path, 'fixture')
    sha256_file = run.manifest.sha256_file
    with monkeypatch.context() as patch:
        patch.setattr(
            run.manifest, 'sha256_file', lambda file: (
                'changed' if file.name == 'ita_verification.py' else sha256_file(file)
            )
        )
        with pytest.raises(ValueError, match='code changed'):
            run.measure(tmp_path, 'fixture')
```

- [ ] **Step 2: Run RED.** `uv run --locked pytest tests/test_ita_verification_run.py -q`.

- [ ] **Step 3: Implement the runner.**

```python
'''Explicit ITA reference/geocode acquisition and offline verification reports.'''

import csv
import json
import re
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

import httpx
import polars as pl
import typer

from embedding_data import ita_county_verification as county
from embedding_data import ita_references as refs
from embedding_data import ita_summary, manifest, paths
from embedding_data import ita_verification as verify
from embedding_data.osha_benchmark_download import record_download

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)
GEOCODER = 'https://geocoding.geo.census.gov/geocoder'
BENCHMARK = 'Public_AR_Current'
VINTAGE = 'ACS2025_Current'
BATCH_LIMIT = 10_000

def make_client() -> httpx.Client:
    return httpx.Client(http2=True, follow_redirects=True, timeout=600)

def run_dir(data_dir: Path, run_id: str) -> Path:
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', run_id):
        raise ValueError('run_id must contain only letters, digits, hyphens and underscores')
    return paths.derived_dir(data_dir, 'osha') / 'verification' / run_id

def write_json(file: Path, value) -> None:
    file.write_text(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + '\n')

def source_entries(data_dir: Path, table: Path, hud: Path) -> list[dict]:
    raw_root = paths.manifest_path(data_dir).parent
    summary_paths = pl.scan_parquet(table).select('source_file').unique().collect()['source_file']
    files = [raw_root / name for name in summary_paths]
    files.extend(
        refs.reference_path(data_dir, 'naics/' + url.rsplit('/', 1)[1])
        for url in refs.TITLE_FILES.values()
    )
    files.append(hud)
    return [
        asdict(manifest.entry_for(paths.manifest_path(data_dir), file))
        for file in sorted(set(files))
    ]

def prepare(data_dir: Path, hud: Path, run_id: str) -> Path:
    directory = run_dir(data_dir, run_id)
    if directory.exists():
        raise ValueError(f'{directory}: run already exists; use a new run_id')
    manifest.entry_for(paths.manifest_path(data_dir), hud)
    titles = refs.read_titles(data_dir)
    table = ita_summary.build_summary_table(data_dir)
    candidates = county.zip_candidates(county.read_hud(hud))
    sample = county.stratified_sample(pl.scan_parquet(table), candidates)
    inventory = source_entries(data_dir, table, hud)
    directory.mkdir(parents=True)
    sample.write_parquet(directory / 'sample.parquet')
    requests = directory / 'requests'
    requests.mkdir()
    for start in range(0, sample.height, BATCH_LIMIT):
        file = requests / f'{start // BATCH_LIMIT:04d}.csv'
        with file.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream)
            for row in sample.slice(start, BATCH_LIMIT).iter_rows(named=True):
                writer.writerow(
                    [
                        row['row_key'], row['street_address'] or '', row['city'] or '',
                        row['state'] or '', row['zip_key'] or ''
                    ]
                )
    write_json(
        directory / 'inputs.json', {
            'raw_inputs': inventory,
            'hud_path': hud.relative_to(paths.manifest_path(data_dir).parent).as_posix(),
            'table_sha256': manifest.sha256_file(table),
            'sample_sha256': manifest.sha256_file(directory / 'sample.parquet'),
            'requests': {
                file.name: manifest.sha256_file(file)
                for file in sorted(requests.glob('*.csv'))
            },
            'algorithm': 'ita-verification-v1',
            'sample_salt': county.SAMPLE_SALT,
            'per_stratum': 8,
            'versions': {
                name: version(name)
                for name in ('polars', 'httpx', 'fastexcel')
            },
            'title_counts': titles.group_by('vintage').len().sort('vintage').to_dicts(),
            'code_sha256': {
                file.name: manifest.sha256_file(file)
                for file in (
                    Path(verify.__file__),
                    Path(county.__file__),
                    Path(refs.__file__),
                    Path(__file__),
                    Path(manifest.__file__),
                    Path(ita_summary.__file__),
                )
            },
        }
    )
    return directory

def check_inputs(data_dir: Path, directory: Path) -> dict:
    inputs = json.loads((directory / 'inputs.json').read_text())
    raw_root = paths.manifest_path(data_dir).parent
    for item in inputs['raw_inputs']:
        current = manifest.entry_for(paths.manifest_path(data_dir), raw_root / item['path'])
        if current.sha256 != item['sha256']:
            raise ValueError('input inventory differs from current raw provenance')
    checks = {
        directory / 'sample.parquet': inputs['sample_sha256'],
        paths.derived_dir(data_dir, 'osha') / ita_summary.TABLE_NAME: inputs['table_sha256']
    }
    checks.update(
        {
            directory / 'requests' / name: digest
            for name, digest in inputs['requests'].items()
        }
    )
    for file, expected in checks.items():
        if manifest.sha256_file(file) != expected:
            raise ValueError(f'{file}: verification input changed')
    for name, expected in inputs['code_sha256'].items():
        if manifest.sha256_file(Path(__file__).parent / name) != expected:
            raise ValueError(f'{name}: verification code changed; prepare a new run')
    for name, expected in inputs['versions'].items():
        if version(name) != expected:
            raise ValueError(f'{name}: dependency version changed; prepare a new run')
    return inputs

def acquire_geocodes(data_dir: Path, run_id: str) -> None:
    directory = run_dir(data_dir, run_id)
    inputs = check_inputs(data_dir, directory)
    raw_relative = f'census-geocoder/{run_id}'
    responses = []
    with make_client() as client:
        benchmarks = refs.fetch_reference(
            data_dir, client, GEOCODER + '/benchmarks', raw_relative + '/benchmarks.json'
        )
        options = json.loads(benchmarks.read_text())['benchmarks']
        matches = [item for item in options if item['benchmarkName'] == BENCHMARK]
        if len(matches) != 1:
            raise ValueError('requested Census benchmark unavailable or ambiguous')
        benchmark_id = matches[0]['id']
        vintages = refs.fetch_reference(
            data_dir, client, GEOCODER + f'/vintages?benchmark={benchmark_id}',
            raw_relative + '/vintages.json'
        )
        options = json.loads(vintages.read_text())['vintages']
        matches = [item for item in options if item['vintageName'] == VINTAGE]
        if len(matches) != 1:
            raise ValueError('requested Census geography vintage unavailable or ambiguous')
        vintage_id = matches[0]['id']
        for name, request_hash in sorted(inputs['requests'].items()):
            request_file = directory / 'requests' / name
            destination = refs.reference_path(data_dir, raw_relative + f'/{request_hash}.csv')
            if not refs.existing_reference(data_dir, destination):
                with request_file.open('rb') as stream:
                    response = client.post(
                        GEOCODER + '/geographies/addressbatch',
                        data={
                            'benchmark': benchmark_id,
                            'vintage': vintage_id
                        },
                        files={'addressFile': (name, stream, 'text/csv')}
                    )
                response.raise_for_status()
                county.parse_geocodes(response.text)
                partial = destination.with_name(destination.name + '.part')
                try:
                    partial.write_bytes(response.content)
                    partial.replace(destination)
                finally:
                    partial.unlink(missing_ok=True)
                record_download(
                    paths.manifest_path(data_dir), destination,
                    GEOCODER + '/geographies/addressbatch'
                )
            with request_file.open(newline='', encoding='utf-8') as stream:
                expected_ids = {row[0] for row in csv.reader(stream)}
            parsed = county.parse_geocodes(destination.read_text())
            if expected_ids != set(parsed['row_key'].to_list()):
                raise ValueError('Census batch response IDs differ from request IDs')
            responses.append(
                asdict(manifest.entry_for(paths.manifest_path(data_dir), destination))
            )
    write_json(
        directory / 'geocoding.json', {
            'benchmark': BENCHMARK,
            'benchmark_id': benchmark_id,
            'vintage': VINTAGE,
            'vintage_id': vintage_id,
            'responses': responses,
            'catalogs': [
                asdict(manifest.entry_for(paths.manifest_path(data_dir), file))
                for file in (benchmarks, vintages)
            ],
            'acquisition_start': min(item['retrieved_at'] for item in responses),
            'acquisition_end': max(item['retrieved_at'] for item in responses),
            'benchmark_snapshot_limit': (
                'Current address data can change between batches, including resumed acquisition; '
                'catalogs identify the request options, not a frozen address-source snapshot.'
            ),
        }
    )

def markdown_table(records: list[dict]) -> str:
    if not records:
        return '(No rows.)\n'
    columns = list(records[0])

    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')

    return '\n'.join(
        [
            '| ' + ' | '.join(columns) + ' |',
            '| ' + ' | '.join('---' for _ in columns) + ' |',
            *['| ' + ' | '.join(cell(row[name]) for name in columns) + ' |' for row in records],
        ]
    ) + '\n'

def measure(data_dir: Path, run_id: str) -> dict:
    directory = run_dir(data_dir, run_id)
    inputs = check_inputs(data_dir, directory)
    geocoding = json.loads((directory / 'geocoding.json').read_text())
    raw_root = paths.manifest_path(data_dir).parent
    frames = []
    for item in [*geocoding['catalogs'], *geocoding['responses']]:
        entry = manifest.entry_for(paths.manifest_path(data_dir), raw_root / item['path'])
        if entry.sha256 != item['sha256']:
            raise ValueError('geocoding inventory differs from raw provenance')
    for item in geocoding['responses']:
        frames.append(county.parse_geocodes((raw_root / item['path']).read_text()))
    lf = pl.scan_parquet(paths.derived_dir(data_dir, 'osha') / ita_summary.TABLE_NAME)
    descriptions = verify.description_report(lf, refs.read_titles(data_dir))
    quality = verify.quality_report(lf)
    pairs = sorted(set([(year, year + 1) for year in range(2016, 2025)] + [(2023, 2025)]))
    links = [verify.link_report(lf, first, second) for first, second in pairs]
    strata, overall = county.county_report(
        pl.read_parquet(directory / 'sample.parquet'), pl.concat(frames)
    )
    result = {
        'inputs': inputs,
        'geocoding': geocoding,
        'v1': descriptions.to_dicts(),
        'quality': quality.to_dicts(),
        'v2': links,
        'v3_overall': overall,
        'v3_strata': strata.to_dicts()
    }
    descriptions.write_parquet(directory / 'v1.parquet')
    quality.write_parquet(directory / 'quality.parquet')
    strata.write_parquet(directory / 'v3-strata.parquet')
    write_json(directory / 'v2.json', links)
    write_json(directory / 'reports.json', result)
    text = '# ITA V1–V3 measurements\n\nMeasurement report; decisions are not yet adopted.\n\n'
    text += '## Inputs and versions\n\n```json\n' + json.dumps(
        {
            'inputs': inputs,
            'geocoding': geocoding
        }, indent=2, sort_keys=True
    ) + '\n```\n\n'
    for heading, records in [
        ('V1', result['v1']), ('Quality', result['quality']), ('V2', result['v2']),
        ('V3 sample totals', [overall])
    ]:
        text += f'## {heading}\n\n' + markdown_table(records) + '\n'
    text += (
        '## Interpretation\n\nCounts retain their denominators. V1 flags overlap. '
        'V2 confirms only unique-ID links with a known matching EIN and address. '
        'V3 coverage differs from assignment and conditional agreement. '
        'Weighted V3 summaries estimate the distinct-row sampling population; '
        'they are not unweighted sample percentages or accuracy estimates.\n'
    )
    (directory / 'finding.md').write_text(text)
    return result

@app.command('references')
def references_command(data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')) -> None:
    refs.acquire_titles(data_dir)

@app.command('import-hud')
def import_hud_command(
    workbook: Path, quarter: str, data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')
) -> None:
    typer.echo(refs.import_hud(data_dir, workbook, quarter))

@app.command('sample')
def sample_command(
    hud: Path, run_id: str, data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')
) -> None:
    typer.echo(prepare(data_dir, hud, run_id))

@app.command('geocode')
def geocode_command(
    run_id: str, data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')
) -> None:
    acquire_geocodes(data_dir, run_id)

@app.command('measure')
def measure_command(
    run_id: str, data_dir: Path = typer.Option(paths.DATA_DIR, '--data-dir')
) -> None:
    result = measure(data_dir, run_id)
    typer.echo(f"measured {sum(row['n_rows'] for row in result['v1']):,} ITA rows")

if __name__ == '__main__':
    app()
```

  Add these exact facts to README/CLAUDE: `audit` is read-only and exits 1 on a
  discrepancy; `entry_for` verifies hashes and `recorded_entry_for` is only for
  restoration/existence diagnostics; verification `references` and `geocode`
  acquire public data, while `sample` and `measure` are offline. A `measure`
  never rebuilds the table or recontacts Census; changed sample/table/request
  bytes fail. The source table is rebuilt once in `sample`, with the same
  source/hash contract as Stage 2. Reports are measurements, not target tables.
  HUD's `retrieved_at` is the local import time, flagged as a proxy; it is not
  presented as the original browser download time.

- [ ] **Step 4: Run GREEN and the full code milestone.**
  `uv run --locked pytest`, `uv run --locked behave`,
  `uv run --locked ruff check .`, `uv lock --check`.
  This completes software, not V1–V3; no stage checkbox changes yet.

- [ ] **Step 5: Commit.**
  `git add src/embedding_data/ita_verification_run.py tests/test_ita_verification_run.py README.md CLAUDE.md`
  then `git commit -m 'feat(ita): replay provenance-backed verification reports offline'`.

### Task 6: Measure the actual files, adopt rules, amend the spec and hand off

**Files:** Create `specs/findings/v1-v3-ita-verification.md`; amend
`specs/embedding-evaluation-data-spec.md`, `specs/deferred_items.md`, this plan,
and `specs/embedding-evaluation-data-spec-roadmap.md`. Update README/CLAUDE with
the adopted rules and finding link. The only result committed is the aggregate
finding; raw references, public-address sample and cached responses stay in
the ignored `data/` tree.

**Interfaces:** Consumes verified software and actual acquisitions from Tasks
1–5. Produces the Stage 3 exit artifacts and exact downstream contracts. This
task has an evidence-dependent owner checkpoint: approval of the plan does not
pre-approve a finding that has not yet been measured.

- [ ] **Step 1: Resolve the manual HUD prerequisite.** D1 authorizes the
  prerequisite. The owner downloads the official ZIP–county workbook for the
  reviewed quarter through [HUD's download login](https://www.huduser.gov/portal/datasets/usps_crosswalk.html).
  Obtain its local path; no credential is requested by this pipeline. Check
  the file/quarter selection and record its original filename in the finding.
  If the quarter differs from P6, log that owner choice before sampling.
  All earlier fixture/software tasks can proceed without the workbook.

- [ ] **Step 2: Run the live provenance and reference checks.** From the
  execution worktree, set these task-specific variables (the actual HUD
  filename below is the expected 2025 Q4 release; substitute the owner's
  selected local path if its filename differs):

```bash
ITA_DATA_DIR=/Users/lowell/Projects/embedding-data/data
ITA_HUD_WORKBOOK=/Users/lowell/Downloads/ZIP_COUNTY_122025.xlsx
ITA_VERIFY_RUN=v1_v3_20261013
uv run --locked embedding-data audit --data-dir "$ITA_DATA_DIR"
uv run --locked python -m embedding_data.ita_verification_run references --data-dir "$ITA_DATA_DIR"
uv run --locked python -m embedding_data.ita_verification_run import-hud "$ITA_HUD_WORKBOOK" 2025Q4 --data-dir "$ITA_DATA_DIR"
```

  Record the audit's actual exit code/discrepancies. Never make it green by
  replacing a recorded hash. An issue in an investigation input must be
  resolved from authoritative bytes before measurement. An unrelated IPUMS
  issue is reported explicitly and handed to Stage 7; the audit feature's
  deferred-item contract is about detection and verified citation, not silently
  repairing the entire raw tree. Refuse HTML/login content pretending to be a
  workbook. Title parsing must pass the full-file count checks from Task 2.

- [ ] **Step 3: Prepare the frozen sample, acquire its responses, then measure offline.**

```bash
ITA_HUD_RAW="$ITA_DATA_DIR/raw/references/hud/2025Q4/$(basename "$ITA_HUD_WORKBOOK")"
uv run --locked python -m embedding_data.ita_verification_run sample "$ITA_HUD_RAW" "$ITA_VERIFY_RUN" --data-dir "$ITA_DATA_DIR"
uv run --locked python -m embedding_data.ita_verification_run geocode "$ITA_VERIFY_RUN" --data-dir "$ITA_DATA_DIR"
uv run --locked python -m embedding_data.ita_verification_run measure "$ITA_VERIFY_RUN" --data-dir "$ITA_DATA_DIR"
uv run --locked embedding-data audit --data-dir "$ITA_DATA_DIR"
```

  These are the stage's authorized public-data acquisitions after plan review;
  do not introduce another routine permission gate. The geocoder receives only
  the sample's public ITA address fields, not EINs, company text or IPUMS rows.
  Commands may take minutes; poll ongoing commands in intervals of at most
  60 seconds and report completed batches/progress. On a service refusal, retain
  earlier responses and resume missing batches from the same verified requests.
  Report each batch's manifest acquisition timestamp and the overall date range.
  Resumption can combine revisions of the mutable Current address benchmark;
  catalog caching does not remove that limitation. A fresh comparison uses a
  new run identifier. Never turn partial acquisition into a full-sample claim.

- [ ] **Step 4: Inspect denominators and descriptive results before choosing rules.**
  Run the following offline inspection (change only the run identifier if it
  was reviewed differently):

```python
import json
from pathlib import Path

import polars as pl

from embedding_data import ita_verification as verify, ita_county_verification as county

directory = Path(
    '/Users/lowell/Projects/embedding-data/data/derived/osha/verification/v1_v3_20261013'
)
report = json.loads((directory / 'reports.json').read_text())
assert {row['year_filing_for'] for row in report['v1']} == set(range(2016, 2026))
assert {(row['base_year'], row['later_year'])
        for row in report['v2']}.issuperset({(2023, 2024), (2023, 2025)})
table = directory.parents[1] / 'ita_300a_summary.parquet'
lf = pl.scan_parquet(table)
for column in ('id', 'establishment_id'):
    collisions = (
        lf.unique().group_by('year_filing_for',
                             column).agg(n=pl.len()).filter(pl.col('n').gt(1)).group_by(
                                 'year_filing_for'
                             ).agg(n_conflicting_keys=pl.len(), n_rows=pl.col('n').sum()).sort(
                                 'year_filing_for'
                             ).collect()
    )
    print(column, collisions)
keys = verify.with_keys(lf)
print(
    keys.group_by('year_filing_for', 'zip_format').len().sort('year_filing_for',
                                                              'zip_format').collect()
)
print(
    keys.filter(pl.col('flag_empty').not_().and_(pl.col('flag_placeholder').not_())).group_by(
        'description_key'
    ).len().sort('len', descending=True).head(30).collect()
)
print(keys.group_by('ein').len().sort('len', descending=True).head(20).collect())
sample = pl.read_parquet(directory / 'sample.parquet')
assert sample['row_key'].n_unique() == sample.height
assert sample['sample_weight'].sum() == sample.select('stratum', 'population_n'
                                                      ).unique()['population_n'].sum()
print('sample rows', sample.height, 'strata', sample['stratum'].n_unique())
print(report['v3_overall'])
```

  This diagnostic reads public ITA data locally. Commit only aggregates and
  selected non-identifying examples needed to explain a rule; no public-address
  request or IPUMS microdata is committed. In particular:

  - V1: report per-year original-length quantiles, empty/placeholder/title
    shares, known-vintage identity, unknown-employer share, repetition rows and
    excess rows. Inspect frequent residual descriptions before accepting the
    finite vocabulary. Generic valid descriptions are not automatically junk.
  - V2: report ID reappearance separately from confirmed EIN/address links;
    use all distinct cohort IDs for persistence, eligible unique ID pairs as
    an additional denominator, and uniquely matched addresses for changed-ID
    shares. Distinguish exact duplicate rows, conflicting record IDs and
    conflicting establishment IDs, including 2021. Show normalized/padded EIN
    sensitivity separately from unreconstructed EIN confirmation. Missing EIN
    is unknown evidence. Do not assert that an address mismatch proves a
    different establishment: relocation is a limitation of the conservative rule.
  - V3: record every stratum's population/sample size, each method's coverage
    on all sampled rows, exact versus non-exact/tie/no-match results, single
    versus multiple/zero-business-share ZIP candidates, conditional agreement
    for single-county and dominant-county diagnostics, and scope/vintage
    exclusions. Record unweighted sample shares and population-weighted
    estimates separately. Agreement is comparative evidence, not accuracy.
    CT legacy county differences are not ordinary method errors. The 2025
    geography frame applied to older filing addresses is a deliberate common
    reference, not a claim about their historical county boundaries.

  Extend the committed finding with these diagnostics from actual results.
  The temporary inspection is not a substitute for provenance checks or the
  reproducible `reports.json` artifact.

- [ ] **Step 5: Present one evidence checkpoint and adopt rules.** Copy the
  generated `finding.md` into `specs/findings/v1-v3-ita-verification.md`, then
  add the denominator definitions, per-year shares, strata summary, method
  limitations, audit results and the proposed amendment text below. Present
  the actual finding and the proposed cleaning, linkage and county decisions
  as one approve-or-amend request. Do not insert verified markers or tick the
  roadmap while this checkpoint is unanswered. If measurements contradict a
  default, propose a concrete replacement backed by the finding; log the
  owner answer in `## Decisions`, apply the code/test correction, and repeat
  the full relevant measurement under a new run ID/code version. Do not carry
  an obsolete code hash forward as provenance for changed rules.

  The proposed amendments are complete wording for review, not measured facts.
  Approved alternatives replace these blocks before they are applied.

  **A1 — R2.3 introductory correction.** Replace the opening through its first
  `*(verified; ITA)*` marker with:

  > **R2.3** Stack all years into one establishment-year table keyed on
  > `year_filing_for`, harmonizing delivered-format and dictionary changes:
  > `establishment_id`, present from 2016 and documented as the summary-to-case
  > link from the 2023 data; the split of size code `2` into `21` and `22` from
  > the 2023 data; and NAICS codes that may be 2012, 2017, or 2022 vintage from
  > the 2023 data, identified by `naics_year`. *(verified; ITA;
  > specs/findings/v1-v3-ita-verification.md — owner, plan 3, 2026-10-13)*

  Keep the following delivered-file paragraphs from plan 2.

  **A2 — R2.6 open-marker replacement.** Replace the sentence beginning
  `What the field actually contains` and ending `discharged by V1)*.` with:

  > V1 measured the field's content by year; its results and denominators are
  > recorded in `specs/findings/v1-v3-ita-verification.md`. The matching key
  > uses NFKC, Unicode casefold and collapsed/trimmed whitespace, preserving
  > punctuation and the original delivered string. Empty keys and exact
  > placeholder keys `n/a`, `na`, `none`, `unknown`, `not applicable`,
  > `not specified`, `-`, `--`, and `.` are flagged. Identity to any official
  > 2012, 2017 or 2022 NAICS title at levels 2–6 is flagged as copied text;
  > native-vintage identity is also reported, with unknown vintage kept
  > unknown. Suspected mojibake is flagged rather than automatically repaired.
  > Employer grouping uses a usable EIN, else a non-empty normalized company
  > name, with name fallback and reconstructed EIN marked separately; blank
  > employer fields never form a shared employer. Unknown-employer rows
  > retain that flag and do not participate in employer deduplication.
  > *(verified; specs/findings/v1-v3-ita-verification.md — owner, plan 3,
  > 2026-10-13)*

  **A3 — R2.7 replacement.** Replace its full paragraph with:

  > **R2.7** Link establishments across years using `establishment_id` as a
  > candidate in every delivered year. A confirmed link requires a unique ID
  > in each year, the same usable unreconstructed EIN, and the same normalized
  > full address. Exact duplicate rows collapse for linkage only; competing
  > same-ID records remain ambiguous. A changed-ID fallback requires a unique
  > match on usable unreconstructed EIN plus normalized establishment name
  > and full address in both years. Missing or reconstructed EINs, incomplete
  > addresses and conflicting keys are reported separately as weaker or
  > unresolved evidence, not counted as confirmed links. The required
  > 2023→2024 and 2023→2025 persistence/address comparisons and earlier-year
  > diagnostics are recorded in `specs/findings/v1-v3-ita-verification.md`.
  > `ein` with `company_name` also supports multi-unit firm diagnostics for
  > R7.2; company-name fallback does not establish EIN-based co-ownership.
  > *(verified; specs/findings/v1-v3-ita-verification.md — owner, plan 3,
  > 2026-10-13)*

  **A4 — R2.8 replacement.** Replace its full paragraph with:

  > **R2.8** Assign each establishment a county from its address, then derive
  > state, CBSA, division and region under R6. Use a cached Census exact
  > street-address geography match in the common ACS2025 county frame first;
  > otherwise use a HUD ZIP–county fallback only when exactly one county has
  > positive business-address share and its county geography is compatible.
  > Unmatched, non-exact, ambiguous, zero-business-share, out-of-scope and
  > incompatible-vintage results are retained with flags; no largest-share
  > county or old-Connecticut-county shortcut supplies a headline assignment.
  > The stratified comparison, reference quarter, Census benchmark/vintage,
  > conditional county agreement and limitations are recorded in
  > `specs/findings/v1-v3-ita-verification.md`. Stage 6 applies this adopted
  > rule to the full establishment table; Stage 3's sample is verification
  > evidence only. *(verified; specs/findings/v1-v3-ita-verification.md —
  > owner, plan 3, 2026-10-13)*

  Apply the approved blocks without another confirmation. If execution is on
  a later date, use that actual adoption date in the markers and decision log.
  The verified markers cite the committed finding; do not remove V1–V3 from
  the Verification section, which remains the audit trail of their contracts.

- [ ] **Step 6: Verify the exit requirements and commit the finding/amendments.**
  Require a readable committed finding with all ten V1 years, both required
  V2 comparisons, V3 stratum/match/agreement evidence, raw input hashes,
  dependency/code versions, official source links, adopted rules and audit
  results. Require no open marker on R2.6/R2.7/R2.8, and actual official title
  inputs recorded under the manifest. Check the `Manifest audit` Done-when
  against Task 1's implementation and both positive/mismatch tests.
  Run the full code milestone checks from Task 5, then:

```bash
git add specs/findings/v1-v3-ita-verification.md specs/embedding-evaluation-data-spec.md README.md CLAUDE.md
git commit -m 'docs(ita): record V1-V3 evidence and adopted verification rules'
```

- [ ] **Step 7: Review the whole plan before completion markup.** Use
  requesting-code-review for concurrent code-reviewer and independent Codex
  reviews against the plan and source spec, from `git merge-base main HEAD`.
  Review uncommitted changes as well if any exist. Resolve the merged findings
  through receiving-code-review, re-run affected checks/measurements, and commit
  fixes. Do not defer an unanswered method choice; it is a Stage 3 exit blocker.

- [ ] **Step 8: Complete the plan and re-validate later stages against what shipped.**
  Run writing-plans' Plan Completion Protocol: resolve-before-defer, tick
  completed steps and add deviation notes, tick the earlier `Manifest audit`
  item with `→ done in plan 3`, and append only genuine remaining deferred
  items. Add `## Handoff to later stages` using the compatibility checklist
  below and actual interfaces/decisions. Then tick Stage 3 in the roadmap and
  add its completion stamp pointing at
  `specs/plans/completed/3-ita-verification.md`. Include the Handoff section
  pointer in the stamp; the stage is not marked complete by creating this plan.

  | Later stage | Re-validate from shipped artifacts and adopted finding |
  | --- | --- |
  | Stage 4 | Exact manifested official structure filenames/URLs/hashes and parsed title schema. State that parent/edge/concordance tables are still Stage 4. Include unknown-vintage title comparison behavior and any parser/count refusal. |
  | Stage 5 | Adopted county method, HUD quarter, Census benchmark/geography frame, planning-region compatibility, retained county ambiguity, and which full production references still need acquisition. A V3 sample is not the county hierarchy. |
  | Stage 6 | Sample/request/response schemas, verified citation versus lookup, chosen assignment/fallback/flag rules, scope exclusions and geocoding replay limits. Full-table county assignment and target manifests remain Stage 6. |
  | Stage 7 | Whole-tree audit interface and actual non-ITA discrepancies if any, reference import-time proxy convention, and the fact that this stage does not settle V4–V7 or trust IPUMS transformations. |
  | Stage 10 | Exact normalization/title/placeholder rules, employer fallback/padded-EIN sensitivity, unique/collision linkage policy, early-year coverage and unknown-employer limitations. No text pairs or co-ownership target shipped here. |

  Derive the Handoff from the execution ledger, deviation notes and finding,
  including any interim interface that was introduced then reverted. Cite
  R2/R5/R6/R7 rather than restating them. Reconciliation of later roadmap
  entries belongs to the next derive-roadmap resume; do not plan a later stage
  in this execution session.

- [ ] **Step 9: Backlog health, retirement and integration handoff.** Run
  `uv run --no-project --python 3.13 python /Users/lowell/.agents/skills/writing-plans/scripts/deferred_stats.py`
  from the repo root (use the writable uv cache if needed). Report its summary;
  if the rubric's size/age trigger fires, present its read-only triage proposal.
  Retire only this plan via `git mv` to `specs/plans/completed/` in the
  `chore(specs): retire plan 3` commit. The source spec and roadmap remain live.
  Use finishing-a-development-branch to select integration deliberately and
  clean up the worktree after integration. End with the outcome-specific
  roadmap resume handoff, naming no later stage to execute in this session.
