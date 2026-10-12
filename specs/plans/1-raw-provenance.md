# Raw Provenance and Safe Re-runs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/embedding-evaluation-data-spec-roadmap.md, Stage 1 — on plan
> completion, tick the stage and re-validate later stages against what shipped.

**Goal:** Every raw file has a manifest entry, and no command can overwrite or reconvert a delivered file.

**Architecture:** Two new modules underpin the stage. `paths` lays out one data root: `raw/`, `derived/` and `preview/`. `manifest` keeps an append-only JSON Lines file with one entry per raw file, and refuses to record a path a second time. A shared `ipums_delivery` module gives every IPUMS extract a fresh `raw/<source>/<set>/<collection>_<number>/` directory, writes the submitted definition there, downloads into it and records every file. Each command then converts to Parquet under `derived/`. `osha` records its downloads and stops reconverting. A one-off `raw_backfill` module moves the existing tree into this layout and records it, and it runs once against real data, behind an owner gate.

**Tech Stack:** Python 3.14, Typer, ipumspy 0.8.2, httpx 0.28.1, Polars, pytest, Hypothesis, Behave, ruff. No new dependencies.

**Spec:** `specs/embedding-evaluation-data-spec.md`. Stage 1 covers R1.4, R1.2, R1.3, R4.3 and Rollout. The spec stays live after this plan: per the roadmap's Completion section, it retires with the roadmap. Plan Completion Protocol step 5 must therefore not move it.

## Global Constraints

- R1.4: "Raw downloads are immutable and kept as delivered: ITA zip and CSV files; IPUMS `.csv.gz` data with its `.xml` DDI codebook and the submitted definition (`extract.json`). A manifest records each raw file's source URL or IPUMS sample IDs, extract number, retrieval time, SHA-256, and client version. Transformations read raw files and write derived Parquet; nothing edits a raw file."
- R1.2: the IPUMS API key "is never written to a file, a log, or a manifest."
- R4.3: "Exclude monthly samples before January 2025".
- R9.1: "ipumspy's readers return pandas and are not used. Ingestion streams each CSV to Parquet with polars, keeping alphanumeric code columns as strings. Transformations are lazy polars with method-style expressions."
- R9.2: "Tests use fixtures, with no network and no credentials."
- R8.1: "IPUMS microdata are never committed to a repository". `data/` is gitignored and stays so, including `data/raw/manifest.jsonl`.
- Data root (D1): `--data-dir`, default `<project-root>/data`, holds `raw/<source>/`, `derived/<source>/`, `preview/<source>/` and `raw/manifest.jsonl`. A dry run never writes under `raw/`.
- Style: single-quoted strings, `'''` docstrings, 99 columns, and ruff rules E, F, I and Q. `src/embedding_data/acs_benchmark_extract.py` uses **2-space** indentation; every other file, including all new modules and all tests, uses 4. If `ruff check` reorders imports, accept `uv run --locked ruff check --fix .`.
- Test seams: `IpumsApiClient` and `DOTENV_PATH` must stay module globals of `acs_benchmark_extract` and `cps_benchmark_extract`, looked up at call time. OSHA tests patch `make_client`. Every test that reaches a live code path patches both IPUMS seams.
- Never run `cps` (apart from `--help`), `acs` without `--dry-run`, or `osha` against the network. Tests cover them. The pre-commit hook runs the full pytest suite on every commit, so every task's commit must leave the suite green.
- Baseline before Task 1: `uv run --locked pytest` shows 44 passed, and `uv run --locked behave` shows 2 scenarios passed.

## Decisions

- **D1** (owner, planning, 2026-10-12): one `--data-dir` root (default `<project-root>/data`) replaces `--out` on `acs`, `cps` and `osha`. Raw files go under `raw/<source>`, derived Parquet under `derived/<source>`, and dry-run definitions under `preview/<source>`, never in raw. Applied in: Global Constraints; Tasks 2, 3, 5.
- **D2** (owner, roadmap, 2026-10-12): the raw files delivered before the manifest existed are backfilled, each entry with its SHA-256 and extract number. Retrieval time (file mtime) and client version (`uv.lock`) are flagged as proxies. Applied in: Tasks 6, 7; Task 8 (spec amendment to R1.4).
- **D3** (owner, roadmap, 2026-10-12): converted Parquet moves out of `data/raw`. Applied in: Tasks 2, 3, 5, 6.
- **D4** (owner, roadmap, 2026-10-12): the spec records registration as complete, along with the 2026-10-12 submissions. Applied in: Task 8 (spec amendment).
- **D5** (owner, plan review, 2026-10-12): the plan is approved as written, including the planning defaults below and Task 8's five spec amendments word for word. Task 8 applies them without asking again. Applied in: Task 8.

**Planning defaults (approved at plan review, D5):**
- **One manifest file.** It is `data/raw/manifest.jsonl`, gitignored with the data, and its paths are relative to `data/raw`.
- **Every raw file is manifested.** That is 17 files in today's tree: 5 × (`extract.json`, `.csv.gz`, `.xml`) plus the 2 OSHA files. The roadmap's "seven pre-existing raw files" are the five `.csv.gz` files and the two OSHA files, and Task 7 checks each of them by name.
- **The R4.3 floor sits at the CLI boundary only.** `parse_month` and `select_samples` stay pure, because the Hypothesis properties call them with 2023–2024 months.
- **OSHA converts only when the derived Parquet is absent.**
- **`raw_backfill` stays in the tree.** It is a tested `python -m` module, not a console command, and it is a no-op on a tree that is already migrated.

---

### Task 1: Data layout and raw manifest

**Files:**
- Create: `src/embedding_data/paths.py`
- Create: `src/embedding_data/manifest.py`
- Create: `tests/test_manifest.py`
- Modify: `tests/conftest.py` (add a `data_directory` fixture; keep `output_directory` until Task 5)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `paths.PROJECT_ROOT: Path`, `paths.DATA_DIR: Path`.
  - `paths.raw_dir(data_dir: Path, source: str) -> Path`, `paths.derived_dir(...)` and `paths.preview_dir(...)`: `data_dir/'raw'|'derived'|'preview'/source`.
  - `paths.manifest_path(data_dir: Path) -> Path`: `data_dir/'raw/manifest.jsonl'`.
  - `manifest.ManifestEntry`, a frozen dataclass with fields `path: str`, `sha256: str`, `size: int`, `retrieved_at: str` (ISO 8601 UTC, seconds), `client: str` and `client_version: str`. Optional fields default as follows: `source_url: str | None = None`, `collection: str | None = None`, `extract_number: int | None = None`, `samples: tuple[str, ...] = ()` and `proxies: tuple[str, ...] = ()`.
  - `manifest.sha256_file(file: Path) -> str`.
  - `manifest.describe_file(file: Path, raw_root: Path, *, retrieved_at: datetime, client: str, client_version: str, source_url=None, collection=None, extract_number=None, samples: Iterable[str] = (), proxies: Iterable[str] = ()) -> ManifestEntry`. The path is recorded relative to `raw_root`, and a naive `retrieved_at` raises `ValueError`.
  - `manifest.read_manifest(manifest_path: Path) -> list[ManifestEntry]`, which returns `[]` when the file is absent.
  - `manifest.append_entries(manifest_path: Path, entries: Iterable[ManifestEntry]) -> None`. It raises `ValueError` and writes nothing when any path is already recorded or repeated, and it is a no-op for no entries.
  - `manifest.entry_for(manifest_path: Path, raw_file: Path) -> ManifestEntry`, which raises `KeyError` when the file is not recorded.

- [ ] **Step 1: Add the `data_directory` fixture**

In `tests/conftest.py`, append after the `output_directory` fixture:

```python
@pytest.fixture
def data_directory(tmp_path):
    return tmp_path / 'data'
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_manifest.py`:

```python
import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from embedding_data import manifest, paths

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ABC_SHA256 = 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
RETRIEVED_AT = datetime(2026, 10, 12, 16, 50, 59, tzinfo=UTC)


@pytest.fixture
def raw_file(data_directory):
    file = paths.raw_dir(data_directory, 'acs') / 'core/usa_00001/usa_00001.xml'
    file.parent.mkdir(parents=True)
    file.write_bytes(b'abc')
    return file


def describe(file, data_directory, *, retrieved_at=RETRIEVED_AT, **provenance):
    return manifest.describe_file(
        file,
        paths.manifest_path(data_directory).parent,
        retrieved_at=retrieved_at,
        client='ipumspy',
        client_version='0.8.2',
        **provenance,
    )


def test_layout_keeps_raw_derived_and_preview_under_one_root(tmp_path):
    assert paths.DATA_DIR == PROJECT_ROOT / 'data'
    assert paths.raw_dir(tmp_path, 'acs') == tmp_path / 'raw/acs'
    assert paths.derived_dir(tmp_path, 'acs') == tmp_path / 'derived/acs'
    assert paths.preview_dir(tmp_path, 'acs') == tmp_path / 'preview/acs'
    assert paths.manifest_path(tmp_path) == tmp_path / 'raw/manifest.jsonl'


def test_sha256_file_streams_a_known_digest(raw_file):
    assert manifest.sha256_file(raw_file) == ABC_SHA256


def test_describe_file_records_path_hash_and_provenance_in_utc(raw_file, data_directory):
    eastern = timezone(timedelta(hours=-4))

    entry = describe(
        raw_file,
        data_directory,
        retrieved_at=datetime(2026, 10, 12, 12, 50, 59, tzinfo=eastern),
        collection='usa',
        extract_number=1,
        samples=['us2023a', 'us2024a'],
    )

    assert entry == manifest.ManifestEntry(
        path='acs/core/usa_00001/usa_00001.xml',
        sha256=ABC_SHA256,
        size=3,
        retrieved_at='2026-10-12T16:50:59+00:00',
        client='ipumspy',
        client_version='0.8.2',
        collection='usa',
        extract_number=1,
        samples=('us2023a', 'us2024a'),
    )


def test_describe_file_rejects_a_naive_retrieval_time(raw_file, data_directory):
    with pytest.raises(ValueError, match='timezone-aware'):
        describe(raw_file, data_directory, retrieved_at=datetime(2026, 10, 12, 16, 50, 59))


def test_read_manifest_is_empty_before_the_first_download(data_directory):
    assert manifest.read_manifest(paths.manifest_path(data_directory)) == []


def test_appending_nothing_leaves_no_manifest(data_directory):
    manifest_path = paths.manifest_path(data_directory)

    manifest.append_entries(manifest_path, [])

    assert not manifest_path.exists()


def test_entries_round_trip_as_one_json_line_each_in_recording_order(raw_file, data_directory):
    manifest_path = paths.manifest_path(data_directory)
    pdf = paths.raw_dir(data_directory, 'osha') / 'dictionary.pdf'
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b'%PDF')
    first = describe(raw_file, data_directory, collection='usa', extract_number=1)
    second = describe(
        pdf, data_directory, source_url='https://www.osha.gov/dictionary.pdf',
        proxies=['retrieved_at'],
    )

    manifest.append_entries(manifest_path, [first])
    manifest.append_entries(manifest_path, [second])

    assert manifest.read_manifest(manifest_path) == [first, second]
    lines = manifest_path.read_text().splitlines()
    assert [json.loads(line)['path'] for line in lines] == [first.path, 'osha/dictionary.pdf']


def test_a_recorded_path_is_never_recorded_again(raw_file, data_directory):
    manifest_path = paths.manifest_path(data_directory)
    manifest.append_entries(manifest_path, [describe(raw_file, data_directory)])
    recorded = manifest_path.read_bytes()
    raw_file.write_bytes(b'replaced')

    with pytest.raises(ValueError, match='usa_00001.xml is already recorded'):
        manifest.append_entries(manifest_path, [describe(raw_file, data_directory)])

    assert manifest_path.read_bytes() == recorded


def test_a_duplicate_within_one_append_writes_nothing(raw_file, data_directory):
    manifest_path = paths.manifest_path(data_directory)
    entry = describe(raw_file, data_directory)

    with pytest.raises(ValueError, match='already recorded'):
        manifest.append_entries(manifest_path, [entry, entry])

    assert not manifest_path.exists()


def test_entry_for_finds_a_raw_file_by_location(raw_file, data_directory):
    manifest_path = paths.manifest_path(data_directory)
    entry = describe(raw_file, data_directory)
    manifest.append_entries(manifest_path, [entry])

    assert manifest.entry_for(manifest_path, raw_file) == entry
    with pytest.raises(KeyError, match='usa_00002.xml'):
        manifest.entry_for(manifest_path, raw_file.with_name('usa_00002.xml'))
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_manifest.py -v`
Expected: collection error, `ImportError: cannot import name 'manifest' from 'embedding_data'`.

- [ ] **Step 4: Write `paths.py`**

Create `src/embedding_data/paths.py`:

```python
'''Data locations under one root: immutable raw downloads, derived Parquet, and previews.

    <data>/raw/manifest.jsonl   one entry per raw file (embedding_data.manifest)
    <data>/raw/<source>/        downloads, kept as delivered
    <data>/derived/<source>/    Parquet converted from raw files
    <data>/preview/<source>/    dry-run extract definitions, overwritten freely
'''

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'


def raw_dir(data_dir: Path, source: str) -> Path:
    return data_dir / 'raw' / source


def derived_dir(data_dir: Path, source: str) -> Path:
    return data_dir / 'derived' / source


def preview_dir(data_dir: Path, source: str) -> Path:
    return data_dir / 'preview' / source


def manifest_path(data_dir: Path) -> Path:
    return data_dir / 'raw' / 'manifest.jsonl'
```

- [ ] **Step 5: Write `manifest.py`**

Create `src/embedding_data/manifest.py`:

```python
'''Append-only manifest of raw downloads (spec R1.4).

One JSON object per line and one line per raw file. Paths are POSIX paths relative
to the manifest's directory (data/raw), so the manifest survives moving the
project. Raw files are immutable, so a path is recorded once: a second entry for
the same path is refused rather than superseding the first. `proxies` names the
fields whose values were reconstructed after retrieval rather than recorded at it.
'''

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class ManifestEntry:
    path: str
    sha256: str
    size: int
    retrieved_at: str
    client: str
    client_version: str
    source_url: str | None = None
    collection: str | None = None
    extract_number: int | None = None
    samples: tuple[str, ...] = ()
    proxies: tuple[str, ...] = ()


def sha256_file(file: Path) -> str:
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def describe_file(
    file: Path,
    raw_root: Path,
    *,
    retrieved_at: datetime,
    client: str,
    client_version: str,
    source_url: str | None = None,
    collection: str | None = None,
    extract_number: int | None = None,
    samples: Iterable[str] = (),
    proxies: Iterable[str] = (),
) -> ManifestEntry:
    '''Hash one raw file and pair it with where, when, and how it was retrieved.'''
    if retrieved_at.tzinfo is None:
        raise ValueError('retrieved_at must be timezone-aware')
    return ManifestEntry(
        path=file.relative_to(raw_root).as_posix(),
        sha256=sha256_file(file),
        size=file.stat().st_size,
        retrieved_at=retrieved_at.astimezone(UTC).isoformat(timespec='seconds'),
        client=client,
        client_version=client_version,
        source_url=source_url,
        collection=collection,
        extract_number=extract_number,
        samples=tuple(samples),
        proxies=tuple(proxies),
    )


def read_manifest(manifest_path: Path) -> list[ManifestEntry]:
    '''Every recorded raw file, in recording order; empty before the first download.'''
    if not manifest_path.exists():
        return []
    entries = []
    for line in manifest_path.read_text().splitlines():
        record = json.loads(line)
        record['samples'] = tuple(record['samples'])
        record['proxies'] = tuple(record['proxies'])
        entries.append(ManifestEntry(**record))
    return entries


def append_entries(manifest_path: Path, entries: Iterable[ManifestEntry]) -> None:
    '''Append entries, refusing all of them if any path is already recorded.'''
    entries = list(entries)
    if not entries:
        return
    recorded = {entry.path for entry in read_manifest(manifest_path)}
    for entry in entries:
        if entry.path in recorded:
            raise ValueError(f'{entry.path} is already recorded in {manifest_path}')
        recorded.add(entry.path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open('a') as stream:
        stream.writelines(json.dumps(asdict(entry)) + '\n' for entry in entries)


def entry_for(manifest_path: Path, raw_file: Path) -> ManifestEntry:
    '''The entry recorded for raw_file, so output manifests can cite it by hash.'''
    path = raw_file.relative_to(manifest_path.parent).as_posix()
    for entry in read_manifest(manifest_path):
        if entry.path == path:
            return entry
    raise KeyError(f'{path} is not recorded in {manifest_path}')
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_manifest.py -v`
Expected: 10 passed.

- [ ] **Step 7: Run the full suite and lint**

Run: `uv run --locked pytest -q && uv run --locked ruff check .`
Expected: `54 passed`; `All checks passed!`

- [ ] **Step 8: Commit**

```bash
git add src/embedding_data/paths.py src/embedding_data/manifest.py tests/test_manifest.py tests/conftest.py
git commit -m "feat(manifest): add the append-only raw manifest and data-root layout"
```

---

### Task 2: Shared IPUMS delivery, and the ACS command on `--data-dir`

**Files:**
- Create: `src/embedding_data/ipums_delivery.py`
- Modify: `src/embedding_data/acs_benchmark_extract.py` (2-space indent)
- Modify: `tests/test_acs_benchmark_extract.py` (full replacement)
- Modify: `tests/test_cli.py` (`test_acs_dry_run_neither_reads_key_nor_creates_client`)
- Modify: `README.md` (ACS section), `CLAUDE.md` (Commands block)

**Interfaces:**
- Consumes: `paths.*`, `manifest.describe_file`, `manifest.append_entries` and `manifest.read_manifest` (Task 1).
- Produces:
  - `ipums_delivery.extract_name(collection: str, number: int) -> str`, for example `'usa_00001'`.
  - `ipums_delivery.write_preview(extract: MicrodataExtract, data_dir: Path, source: str, set_name: str) -> Path`, which writes `preview/<source>/<set>/extract.json`.
  - `ipums_delivery.deliver(client, extract: MicrodataExtract, data_dir: Path, source: str, set_name: str) -> Path`. It submits, makes a new `raw/<source>/<set>/<collection>_<number>/` (raising `FileExistsError` if it exists), writes the submitted `extract.json` there, waits, downloads, records every file in the manifest, and returns the extract directory.
  - `ipums_delivery.parquet_path(data_dir: Path, source: str, set_name: str, csv_gz: Path) -> Path`, which returns `derived/<source>/<set>/<name>.parquet`.
  - ACS: `csv_to_parquet(csv_gz: Path, parquet_path: Path) -> Path`, and `main(extracts, data_dir, dry_run)` with the option `--data-dir`; `--out` is gone.

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_acs_benchmark_extract.py` with:

```python
import gzip
import hashlib
import json
from datetime import datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest
import typer
from typer.main import get_command

from embedding_data import acs_benchmark_extract as benchmark
from embedding_data import manifest, paths

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_CSV = 'INDNAICS,OCCSOC,INCWAGE_CPIU_2010\n31M,1110XX,12.5\n'
pytestmark = pytest.mark.usefixtures('cli_runner')


def cli_app():
    app = getattr(benchmark, 'app', None)
    assert isinstance(app, typer.Typer)
    return app


def tree(root):
    '''Every file under root with its bytes, to prove a run left them untouched.'''
    return {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}


@pytest.fixture
def run_live(cli_runner, data_directory, dotenv_path):
    '''Run the ACS command for real against a fake IPUMS client that numbers the extract.'''
    dotenv_path.write_text('IPUMS_API_KEY=dotenv-test-key\n')

    def invoke(arguments=(), *, extract_id=123):
        def download_fixture(extract, *, download_dir):
            name = f'usa_{extract.extract_id:05d}'
            with gzip.open(download_dir / f'{name}.csv.gz', 'wt') as csv_file:
                csv_file.write(FIXTURE_CSV)
            (download_dir / f'{name}.xml').write_text('<codeBook/>\n')

        with (
            patch.object(benchmark, 'DOTENV_PATH', dotenv_path),
            patch.object(benchmark, 'IpumsApiClient', autospec=True) as client_factory,
        ):
            client = client_factory.return_value
            client.submit_extract.side_effect = lambda extract: setattr(extract, '_id', extract_id)
            client.download_extract.side_effect = download_fixture
            result = cli_runner.invoke(
                cli_app(), [*arguments, '--data-dir', str(data_directory)]
            )
        return result, client_factory

    return invoke


def test_default_paths_point_to_project_root():
    command = get_command(cli_app())
    with command.make_context('benchmark', ['--dry-run']) as context:
        assert context.params['data_dir'] == PROJECT_ROOT / 'data'
    assert benchmark.DOTENV_PATH == PROJECT_ROOT / '.env'


def test_help_describes_the_benchmark(cli_runner):
    result = cli_runner.invoke(cli_app(), ['--help'])

    assert result.exit_code == 0, result.output
    assert 'IPUMS USA extracts' in result.output


def test_dry_run_defaults_to_core_without_credentials(cli_runner, data_directory):
    result = cli_runner.invoke(cli_app(), ['--dry-run', '--data-dir', str(data_directory)])

    assert result.exit_code == 0, result.output
    definition = json.loads((data_directory / 'preview/acs/core/extract.json').read_text())
    assert set(definition['samples']) == {'us2023a', 'us2024a'}
    assert definition['dataFormat'] == 'csv'
    assert definition['dataQualityFlags']
    assert not (data_directory / 'raw').exists()


def test_dry_run_accepts_multiple_extracts(cli_runner, data_directory):
    result = cli_runner.invoke(
        cli_app(),
        ['core', 'vintage', 'five_year', '--dry-run', '--data-dir', str(data_directory)],
    )

    assert result.exit_code == 0, result.output
    for name, samples in benchmark.SAMPLE_SETS.items():
        preview = data_directory / 'preview/acs' / name / 'extract.json'
        assert set(json.loads(preview.read_text())['samples']) == set(samples), name


def test_unknown_extract_exits_before_writing_files(cli_runner, data_directory):
    result = cli_runner.invoke(
        cli_app(), ['unknown', '--dry-run', '--data-dir', str(data_directory)],
    )

    assert result.exit_code == 2, result.output
    assert 'unknown extract(s): unknown' in result.output
    assert not data_directory.exists()


@pytest.mark.parametrize('contents', [None, 'IPUMS_API_KEY=\n'], ids=['missing', 'empty'])
def test_missing_or_empty_key_exits_with_dotenv_instructions(
    cli_runner, data_directory, dotenv_path, contents,
):
    app = cli_app()
    if contents is not None:
        dotenv_path.write_text(contents)
    with patch.object(benchmark, 'DOTENV_PATH', dotenv_path):
        result = cli_runner.invoke(app, ['--data-dir', str(data_directory)])

    assert result.exit_code == 1, result.output
    assert 'IPUMS_API_KEY' in result.output
    assert str(dotenv_path) in result.output
    assert not data_directory.exists()


@pytest.mark.parametrize(
    'environment_key', [None, 'environment-test-key'], ids=['dotenv', 'environment'],
)
def test_dotenv_key_is_loaded_with_environment_taking_precedence(
    run_live, monkeypatch, environment_key,
):
    if environment_key is not None:
        monkeypatch.setenv('IPUMS_API_KEY', environment_key)

    result, client_factory = run_live()

    assert result.exit_code == 0, result.output
    client_factory.assert_called_once_with(environment_key or 'dotenv-test-key')


def test_delivery_gets_its_own_raw_directory_and_converts_outside_raw(
    run_live, data_directory,
):
    result, _ = run_live()

    assert result.exit_code == 0, result.output
    extract_directory = data_directory / 'raw/acs/core/usa_00123'
    assert sorted(path.name for path in extract_directory.iterdir()) == [
        'extract.json', 'usa_00123.csv.gz', 'usa_00123.xml',
    ]
    definition = json.loads((extract_directory / 'extract.json').read_text())
    assert list(definition['samples']) == ['us2023a', 'us2024a']
    derived = data_directory / 'derived/acs/core'
    assert sorted(path.name for path in derived.iterdir()) == ['usa_00123.parquet']
    assert pl.read_parquet(derived / 'usa_00123.parquet').row(0) == ('31M', '1110XX', 12.5)
    raw_files = [path for path in (data_directory / 'raw').rglob('*') if path.is_file()]
    assert [path for path in raw_files if path.suffix in {'.parquet', '.csv'}] == []


def test_every_delivered_file_is_recorded_in_the_raw_manifest(run_live, data_directory):
    result, _ = run_live()

    assert result.exit_code == 0, result.output
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [entry.path for entry in entries] == [
        'acs/core/usa_00123/extract.json',
        'acs/core/usa_00123/usa_00123.csv.gz',
        'acs/core/usa_00123/usa_00123.xml',
    ]
    for entry in entries:
        delivered = data_directory / 'raw' / entry.path
        assert entry.sha256 == hashlib.sha256(delivered.read_bytes()).hexdigest()
        assert entry.size == delivered.stat().st_size
        assert (entry.collection, entry.extract_number) == ('usa', 123)
        assert entry.samples == ('us2023a', 'us2024a')
        assert (entry.client, entry.client_version) == ('ipumspy', version('ipumspy'))
        assert (entry.source_url, entry.proxies) == (None, ())
        assert datetime.fromisoformat(entry.retrieved_at).utcoffset() == timedelta(0)


def test_a_second_run_leaves_the_earlier_delivery_untouched(run_live, data_directory):
    first, _ = run_live(extract_id=123)
    assert first.exit_code == 0, first.output
    earlier = tree(data_directory / 'raw/acs/core/usa_00123')
    parquet = data_directory / 'derived/acs/core/usa_00123.parquet'
    converted = (parquet.read_bytes(), parquet.stat().st_mtime_ns)

    second, _ = run_live(extract_id=124)

    assert second.exit_code == 0, second.output
    assert tree(data_directory / 'raw/acs/core/usa_00123') == earlier
    assert (parquet.read_bytes(), parquet.stat().st_mtime_ns) == converted
    assert (data_directory / 'derived/acs/core/usa_00124.parquet').exists()
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [entry.extract_number for entry in entries] == [123] * 3 + [124] * 3


def test_an_existing_extract_directory_is_never_overwritten(run_live, data_directory):
    first, _ = run_live(extract_id=123)
    assert first.exit_code == 0, first.output
    before = tree(data_directory)

    second, client_factory = run_live(extract_id=123)

    assert isinstance(second.exception, FileExistsError), second.output
    client_factory.return_value.download_extract.assert_not_called()
    assert tree(data_directory) == before


def test_the_api_key_reaches_no_file_and_no_output(run_live, data_directory):
    result, _ = run_live()

    assert result.exit_code == 0, result.output
    assert 'dotenv-test-key' not in result.output
    for path, contents in tree(data_directory).items():
        assert b'dotenv-test-key' not in contents, path
```

In `tests/test_cli.py`, replace `test_acs_dry_run_neither_reads_key_nor_creates_client` with:

```python
def test_acs_dry_run_neither_reads_key_nor_creates_client(
    cli_runner, data_directory, dotenv_path,
):
    dotenv_path.write_text('IPUMS_API_KEY=dotenv-test-key\n')
    with (
        patch.object(acs_extract, 'DOTENV_PATH', dotenv_path),
        patch.object(acs_extract, 'IpumsApiClient', autospec=True) as client_factory,
    ):
        result = cli_runner.invoke(
            cli.app, ['acs', '--dry-run', '--data-dir', str(data_directory)]
        )

        assert 'IPUMS_API_KEY' not in os.environ

    assert result.exit_code == 0, result.output
    client_factory.assert_not_called()
    definition = json.loads((data_directory / 'preview/acs/core/extract.json').read_text())
    assert set(definition['samples']) == {'us2023a', 'us2024a'}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_acs_benchmark_extract.py tests/test_cli.py -v`
Expected: FAIL. `test_default_paths_point_to_project_root` fails with `KeyError: 'data_dir'`, and the invocation tests exit 2 with `No such option: --data-dir`.

- [ ] **Step 3: Write `ipums_delivery.py`**

Create `src/embedding_data/ipums_delivery.py`:

```python
'''Shared IPUMS flow: preview a definition, or submit, download, and record an extract.

A dry run writes the definition under preview/. A real run gives every extract
its own raw directory, raw/<source>/<set>/<collection>_<number>/, holding the
submitted definition (extract.json) and the delivered .csv.gz and .xml, and
records each file in the raw manifest. Extract numbers are never reused, so a
re-run writes a new directory and never overwrites or reconverts an earlier one.
'''

import json
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import typer
from ipumspy import IpumsApiClient, MicrodataExtract

from embedding_data import manifest, paths


def extract_name(collection: str, number: int) -> str:
    '''IPUMS names an extract's files <collection>_<five-digit number>, e.g. usa_00001.'''
    return f'{collection}_{number:05d}'


def write_definition(definition: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(definition, indent=2))
    return path


def write_preview(extract: MicrodataExtract, data_dir: Path, source: str, set_name: str) -> Path:
    '''Write the definition a real run would submit; previews are overwritten freely.'''
    preview = paths.preview_dir(data_dir, source) / set_name / 'extract.json'
    return write_definition(extract.build(), preview)


def deliver(
    client: IpumsApiClient,
    extract: MicrodataExtract,
    data_dir: Path,
    source: str,
    set_name: str,
) -> Path:
    '''Submit and download an extract into its own new raw directory, then record its files.'''
    client.submit_extract(extract)
    typer.echo(f'{set_name}: submitted extract {extract.extract_id}, waiting')
    set_dir = paths.raw_dir(data_dir, source) / set_name
    set_dir.mkdir(parents=True, exist_ok=True)
    extract_dir = set_dir / extract_name(extract.collection, extract.extract_id)
    # An existing directory is an earlier delivery: fail rather than write into it.
    extract_dir.mkdir()
    definition = extract.build()
    write_definition(definition, extract_dir / 'extract.json')
    client.wait_for_extract(extract)
    client.download_extract(extract, download_dir=extract_dir)
    retrieved_at = datetime.now(UTC)

    manifest_path = paths.manifest_path(data_dir)
    manifest.append_entries(
        manifest_path,
        [
            manifest.describe_file(
                file,
                manifest_path.parent,
                retrieved_at=retrieved_at,
                client='ipumspy',
                client_version=version('ipumspy'),
                collection=extract.collection,
                extract_number=extract.extract_id,
                samples=definition['samples'],
            )
            for file in sorted(extract_dir.iterdir())
        ],
    )
    return extract_dir


def parquet_path(data_dir: Path, source: str, set_name: str, csv_gz: Path) -> Path:
    '''Where the Parquet converted from a delivered .csv.gz goes, outside raw/.'''
    name = csv_gz.name.removesuffix('.csv.gz')
    return paths.derived_dir(data_dir, source) / set_name / f'{name}.parquet'
```

- [ ] **Step 4: Move the ACS command onto `--data-dir` (2-space indentation)**

In `src/embedding_data/acs_benchmark_extract.py`, replace the docstring paragraph

```
Requires an IPUMS USA account and IPUMS_API_KEY in the project-root .env
(~/Projects/embedding-data/.env; https://account.ipums.org/api_keys). An exported
IPUMS_API_KEY takes precedence. --dry-run needs neither the key nor network
access. Downloads default to data/raw/acs under the project root, with one
subdirectory per extract set.
```

with

```
Requires an IPUMS USA account and IPUMS_API_KEY in the project-root .env
(~/Projects/embedding-data/.env; https://account.ipums.org/api_keys). An exported
IPUMS_API_KEY takes precedence. --dry-run needs neither the key nor network
access; it writes each definition to data/preview/acs/<set>/extract.json. A real
run gives each extract its own directory, data/raw/acs/<set>/usa_<number>/, with
the submitted extract.json and the delivered .csv.gz and .xml; records each file
in data/raw/manifest.jsonl; and writes Parquet to data/derived/acs/<set>/.
--data-dir moves the whole data root (default: data/ under the project root).
```

Replace the import block and constants, from `import gzip` through the line `DEFAULT_OUTPUT_DIR = PROJECT_ROOT / 'data' / 'raw' / 'acs'`, with:

```python
import gzip
import os
import shutil
from pathlib import Path
from typing import Annotated

import polars as pl
import typer
from dotenv import load_dotenv
from ipumspy import IpumsApiClient, MicrodataExtract

from embedding_data import ipums_delivery, paths

DOTENV_PATH = paths.PROJECT_ROOT / '.env'
```

Replace `csv_to_parquet` and `main`, from `def csv_to_parquet(csv_gz: Path) -> Path:` through the end of `main`'s body (the line before `if __name__ == '__main__':`), with:

```python
def csv_to_parquet(csv_gz: Path, parquet_path: Path) -> Path:
  '''Stream-decompress an IPUMS .csv.gz beside parquet_path, then sink it to Parquet lazily.'''
  parquet_path.parent.mkdir(parents=True, exist_ok=True)
  csv_path = parquet_path.with_suffix('.csv')
  try:
    with gzip.open(csv_gz, 'rb') as src, csv_path.open('wb') as dst:
      shutil.copyfileobj(src, dst, length=16 * 1024 * 1024)
    (
      pl.scan_csv(csv_path, schema_overrides=SCHEMA_OVERRIDES, infer_schema_length=100_000)
      .sink_parquet(parquet_path)
    )
  finally:
    csv_path.unlink(missing_ok=True)
  return parquet_path


@app.command(help=__doc__.splitlines()[0])
def main(
  extracts: Annotated[
    list[str] | None,
    typer.Argument(help=f'one or more of: {", ".join(SAMPLE_SETS)} (default: core)'),
  ] = None,
  data_dir: Annotated[
    Path,
    typer.Option('--data-dir', help='Data root holding raw/, derived/, and preview/.'),
  ] = paths.DATA_DIR,
  dry_run: Annotated[
    bool,
    typer.Option('--dry-run', help='Write definitions to preview/ without submitting.'),
  ] = False,
) -> None:
  extracts = extracts or ['core']

  unknown = sorted(set(extracts).difference(SAMPLE_SETS))
  if unknown:
    raise typer.BadParameter('unknown extract(s): ' + ', '.join(unknown), param_hint='extracts')

  # Definitions need no catalog lookup, so a dry run reads no key and stays offline.
  client = None
  if not dry_run:
    load_dotenv(dotenv_path=DOTENV_PATH)
    api_key = os.environ.get('IPUMS_API_KEY')
    if not api_key:
      typer.echo(
        f'Set IPUMS_API_KEY in {DOTENV_PATH} (https://account.ipums.org/api_keys).', err=True
      )
      raise typer.Exit(code=1)
    client = IpumsApiClient(api_key)

  for name in extracts:
    extract = build_extract(name)
    if client is None:
      preview = ipums_delivery.write_preview(extract, data_dir, 'acs', name)
      typer.echo(f'{name}: wrote {preview}')
      continue

    extract_dir = ipums_delivery.deliver(client, extract, data_dir, 'acs', name)
    for csv_gz in sorted(extract_dir.glob('*.csv.gz')):
      parquet = ipums_delivery.parquet_path(data_dir, 'acs', name, csv_gz)
      typer.echo(f'{name}: wrote {csv_to_parquet(csv_gz, parquet)}')
```

`SAMPLE_SETS`, `VARIABLE_GROUPS`, `SCHEMA_OVERRIDES`, `build_extract`, `app` and the `__main__` guard stay as they are. `import json` goes, because the definition is now written by `ipums_delivery`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_acs_benchmark_extract.py tests/test_cli.py -v`
Expected: all passed.

- [ ] **Step 6: Update the ACS docs**

In `README.md`, replace

```
The default destination is `<project-root>/data/raw/acs/`, with one
subdirectory per set. Use `--out PATH` to override it. Conversion preserves
`INDNAICS` and `OCCSOC` as strings, including aggregated codes such as `31M`
and `1110XX`.
```

with

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
```

In `CLAUDE.md`, replace

```
uv run embedding-data acs core --dry-run --out "$(mktemp -d)"   # offline: no key, no network
```

with

```
uv run embedding-data acs core --dry-run --data-dir "$(mktemp -d)"   # offline: no key, no network
```

- [ ] **Step 7: Run the full suite, Behave and lint**

Run: `uv run --locked pytest -q && uv run --locked behave && uv run --locked ruff check .`
Expected: all pytest passed, 2 scenarios passed, `All checks passed!`. CPS and OSHA still use `--out` at this point.

- [ ] **Step 8: Commit**

```bash
git add src/embedding_data/ipums_delivery.py src/embedding_data/acs_benchmark_extract.py tests/test_acs_benchmark_extract.py tests/test_cli.py README.md CLAUDE.md
git commit -m "feat(acs): deliver each extract into its own raw directory and record it"
```

---

### Task 3: The CPS command on `--data-dir`

**Files:**
- Modify: `src/embedding_data/cps_benchmark_extract.py`
- Modify: `tests/test_cps_benchmark_extract.py` (full replacement)
- Modify: `tests/test_cli.py` (`test_cps_dry_run_reaches_cps_module`)
- Modify: `features/environment.py`, `features/steps/cps_dry_run.py`
- Modify: `README.md` (CPS section), `CLAUDE.md` (Shared flow, Credentials)

**Interfaces:**
- Consumes: `ipums_delivery.write_preview`, `deliver` and `parquet_path` (Task 2); `manifest.read_manifest` and `paths.manifest_path` (Task 1).
- Produces: CPS `csv_to_parquet(csv_gz: Path, parquet_path: Path) -> Path`, and `main(extracts, start, data_dir, dry_run)` with the option `--data-dir`; `--out` is gone.

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_cps_benchmark_extract.py` with:

```python
import gzip
import hashlib
import json
from itertools import count
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest
import typer
from typer.main import get_command

from embedding_data import cps_benchmark_extract as benchmark
from embedding_data import manifest, paths

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CATALOG = {
    'cps2024_12b': 'December 2024 Basic Monthly',
    'cps2025_01s': 'January 2025 Supplement',
    'cps2025_01b': 'January 2025 Basic Monthly',
    'cps2025_03s': 'March 2025 ASEC',
    'cps2024_03s': 'March 2024 ASEC',
    'cps2026_03s': 'March 2026 ASEC',
    'cps2026_08b': 'August 2026 Basic Monthly',
    'cps2026_09s': 'September 2026 Supplement',
}


@pytest.fixture
def cli_app():
    app = getattr(benchmark, 'app', None)
    assert isinstance(app, typer.Typer)
    return app


@pytest.fixture
def run_cli(cli_app, cli_runner, data_directory, dotenv_path):
    dotenv_path.write_text('IPUMS_API_KEY=dotenv-test-key\n')

    def invoke_cli(arguments, *, catalog=None, download=None):
        extract_ids = count(123)
        with (
            patch.object(benchmark, 'DOTENV_PATH', dotenv_path),
            patch.object(benchmark, 'IpumsApiClient', autospec=True) as client_factory,
        ):
            client = client_factory.return_value
            client.get_all_sample_info.return_value = (
                SAMPLE_CATALOG if catalog is None else catalog
            )
            client.submit_extract.side_effect = (
                lambda extract: setattr(extract, '_id', next(extract_ids))
            )
            client.download_extract.side_effect = download
            result = cli_runner.invoke(
                cli_app, [*arguments, '--data-dir', str(data_directory)]
            )
        return result, client_factory

    return invoke_cli


def preview(data_directory, name):
    return json.loads((data_directory / 'preview/cps' / name / 'extract.json').read_text())


def write_delivery(extract, *, download_dir):
    '''Fake IPUMS delivery: the data file and codebook, named for the extract number.'''
    name = f'cps_{extract.extract_id:05d}'
    if download_dir.parent.name == 'monthly':
        csv = 'IND,OCC\n170,20\n'
    else:
        csv = 'IND,OCC,INDLY,OCCLY,INCWAGE_CPIU_2010\n170,20,770,30,12.5\n'
    with gzip.open(download_dir / f'{name}.csv.gz', 'wt') as csv_file:
        csv_file.write(csv)
    (download_dir / f'{name}.xml').write_text('<codeBook/>\n')


def test_default_paths_point_to_project_root(cli_app):
    command = get_command(cli_app)
    with command.make_context('benchmark', ['--dry-run']) as context:
        assert context.params['data_dir'] == PROJECT_ROOT / 'data'
        assert context.params['start'] == '2025-01'
    assert benchmark.DOTENV_PATH == PROJECT_ROOT / '.env'


def test_help_describes_cps_options(cli_app, cli_runner):
    result = cli_runner.invoke(cli_app, ['--help'])

    assert result.exit_code == 0, result.output
    assert 'IPUMS CPS extracts' in result.output
    assert '--start' in result.output


def test_dry_run_loads_key_and_writes_monthly_and_asec_definitions(run_cli, data_directory):
    result, client_factory = run_cli(['--dry-run'])

    assert result.exit_code == 0, result.output
    client_factory.assert_called_once_with('dotenv-test-key')
    client_factory.return_value.get_all_sample_info.assert_called_once_with('cps')
    client_factory.return_value.submit_extract.assert_not_called()
    expected_samples = {
        'monthly': ['cps2025_01b', 'cps2026_08b', 'cps2026_09s'],
        'asec': ['cps2025_03s', 'cps2026_03s'],
    }
    for name, samples in expected_samples.items():
        definition = preview(data_directory, name)
        assert list(definition['samples']) == samples
        assert definition['collection'] == 'cps'
        assert definition['dataQualityFlags']
    assert not (data_directory / 'raw').exists()


def test_monthly_start_option_filters_catalog(run_cli, data_directory):
    result, _ = run_cli(['monthly', '--start', '2026-08', '--dry-run'])

    assert result.exit_code == 0, result.output
    assert list(preview(data_directory, 'monthly')['samples']) == ['cps2026_08b', 'cps2026_09s']
    assert not (data_directory / 'preview/cps/asec').exists()


def test_exported_key_takes_precedence(run_cli, data_directory, monkeypatch):
    monkeypatch.setenv('IPUMS_API_KEY', 'environment-test-key')
    result, client_factory = run_cli(['asec', '--dry-run'])

    assert result.exit_code == 0, result.output
    client_factory.assert_called_once_with('environment-test-key')
    assert (data_directory / 'preview/cps/asec/extract.json').exists()


@pytest.mark.parametrize('contents', [None, 'IPUMS_API_KEY=\n'], ids=['missing', 'empty'])
def test_missing_or_empty_key_fails_even_for_dry_run(
    run_cli, data_directory, dotenv_path, contents,
):
    if contents is None:
        dotenv_path.unlink()
    else:
        dotenv_path.write_text(contents)
    result, client_factory = run_cli(['--dry-run'])

    assert result.exit_code == 1, result.output
    assert 'IPUMS_API_KEY' in result.output
    assert str(dotenv_path) in result.output
    client_factory.assert_not_called()
    assert not data_directory.exists()


def test_unknown_extract_fails_before_loading_catalog(run_cli, data_directory):
    result, client_factory = run_cli(['unknown', '--dry-run'])

    assert result.exit_code == 2, result.output
    assert 'unknown extract(s): unknown' in result.output
    client_factory.assert_not_called()
    assert not data_directory.exists()


def test_empty_catalog_reports_missing_samples(run_cli, data_directory):
    result, _ = run_cli(['monthly', '--dry-run'], catalog={})

    assert result.exit_code == 1, result.output
    assert 'monthly: no matching samples' in result.output
    assert not data_directory.exists()


def test_deliveries_convert_outside_raw_with_zero_padded_census_codes(run_cli, data_directory):
    result, _ = run_cli(['monthly', 'asec'], download=write_delivery)

    assert result.exit_code == 0, result.output
    for name, extract_name, expected in (
        ('monthly', 'cps_00123', ('0170', '0020')),
        ('asec', 'cps_00124', ('0170', '0020', '0770', '0030', 12.5)),
    ):
        derived = data_directory / 'derived/cps' / name
        assert sorted(path.name for path in derived.iterdir()) == [f'{extract_name}.parquet']
        assert pl.read_parquet(derived / f'{extract_name}.parquet').row(0) == expected
        extract_directory = data_directory / 'raw/cps' / name / extract_name
        assert sorted(path.name for path in extract_directory.iterdir()) == [
            f'{extract_name}.csv.gz', f'{extract_name}.xml', 'extract.json',
        ]
    assert list((data_directory / 'raw').rglob('*.parquet')) == []


def test_every_delivered_file_is_recorded_with_its_samples(run_cli, data_directory):
    result, _ = run_cli(['monthly', 'asec'], download=write_delivery)

    assert result.exit_code == 0, result.output
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [(entry.path, entry.extract_number) for entry in entries] == [
        ('cps/monthly/cps_00123/cps_00123.csv.gz', 123),
        ('cps/monthly/cps_00123/cps_00123.xml', 123),
        ('cps/monthly/cps_00123/extract.json', 123),
        ('cps/asec/cps_00124/cps_00124.csv.gz', 124),
        ('cps/asec/cps_00124/cps_00124.xml', 124),
        ('cps/asec/cps_00124/extract.json', 124),
    ]
    for entry in entries:
        delivered = data_directory / 'raw' / entry.path
        assert entry.sha256 == hashlib.sha256(delivered.read_bytes()).hexdigest()
        assert entry.collection == 'cps'
    assert [entry.samples for entry in entries[::3]] == [
        ('cps2025_01b', 'cps2026_08b', 'cps2026_09s'),
        ('cps2025_03s', 'cps2026_03s'),
    ]


def test_the_api_key_reaches_no_file_and_no_output(run_cli, data_directory):
    result, _ = run_cli(['monthly', 'asec'], download=write_delivery)

    assert result.exit_code == 0, result.output
    assert 'dotenv-test-key' not in result.output
    for path in data_directory.rglob('*'):
        if path.is_file():
            assert b'dotenv-test-key' not in path.read_bytes(), path
```

In `tests/test_cli.py`, replace `test_cps_dry_run_reaches_cps_module` with:

```python
def test_cps_dry_run_reaches_cps_module(cli_runner, data_directory, dotenv_path):
    dotenv_path.write_text('IPUMS_API_KEY=dotenv-test-key\n')
    arguments = [
        'cps', 'monthly', '--start', '2026-08', '--dry-run', '--data-dir', str(data_directory),
    ]
    with (
        patch.object(cps_extract, 'DOTENV_PATH', dotenv_path),
        patch.object(cps_extract, 'IpumsApiClient', autospec=True) as client_factory,
    ):
        client_factory.return_value.get_all_sample_info.return_value = SAMPLE_CATALOG
        result = cli_runner.invoke(cli.app, arguments)

    assert result.exit_code == 0, result.output
    client_factory.assert_called_once_with('dotenv-test-key')
    client_factory.return_value.submit_extract.assert_not_called()
    definition = json.loads((data_directory / 'preview/cps/monthly/extract.json').read_text())
    assert list(definition['samples']) == ['cps2026_08b', 'cps2026_09s']
```

In `features/environment.py`, replace

```python
    context.output_directory = Path(temporary_directory.name) / 'extracts'
```

with

```python
    context.data_directory = Path(temporary_directory.name) / 'data'
```

In `features/steps/cps_dry_run.py`:

- In `preview_extracts`, replace `arguments.extend(['--dry-run', '--out', str(context.output_directory)])` with `arguments.extend(['--dry-run', '--data-dir', str(context.data_directory)])`.
- Add this helper above `check_definition_samples`:

```python
def preview_path(context, name):
    return context.data_directory / 'preview/cps' / name / 'extract.json'
```

- In both `check_definition_samples` and `check_missing_definition`, replace `definition_path = context.output_directory / name / 'extract.json'` with `definition_path = preview_path(context, name)`.
- Replace the body of `check_no_extract_requests` with:

```python
    context.client.submit_extract.assert_not_called()
    context.client.wait_for_extract.assert_not_called()
    context.client.download_extract.assert_not_called()
    assert not (context.data_directory / 'raw').exists()
    assert list(context.data_directory.rglob('*.parquet')) == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_cps_benchmark_extract.py tests/test_cli.py -v; uv run --locked behave`
Expected: pytest FAIL, with `KeyError: 'data_dir'` and `No such option: --data-dir`. Behave fails both scenarios with exit code 2.

- [ ] **Step 3: Move the CPS command onto `--data-dir`**

In `src/embedding_data/cps_benchmark_extract.py`, replace the docstring lines

```
Requires an IPUMS CPS account and IPUMS_API_KEY in the project-root .env
(~/Projects/embedding-data/.env; https://account.ipums.org/api_keys). An exported
IPUMS_API_KEY takes precedence. Downloads default to data/raw/cps under the
project root, with one subdirectory per extract set.
```

with

```
Requires an IPUMS CPS account and IPUMS_API_KEY in the project-root .env
(~/Projects/embedding-data/.env; https://account.ipums.org/api_keys). An exported
IPUMS_API_KEY takes precedence. --dry-run writes each definition to
data/preview/cps/<set>/extract.json. A real run gives each extract its own
directory, data/raw/cps/<set>/cps_<number>/, with the submitted extract.json and
the delivered .csv.gz and .xml; records each file in data/raw/manifest.jsonl; and
writes Parquet to data/derived/cps/<set>/. --data-dir moves the whole data root.
```

Replace the import block and constants, from `import gzip` through `DEFAULT_OUTPUT_DIR = PROJECT_ROOT / 'data' / 'raw' / 'cps'`, with:

```python
import gzip
import os
import re
import shutil
from pathlib import Path
from typing import Annotated

import polars as pl
import typer
from dotenv import load_dotenv
from ipumspy import IpumsApiClient, MicrodataExtract

from embedding_data import ipums_delivery, paths

DOTENV_PATH = paths.PROJECT_ROOT / '.env'
```

Replace `csv_to_parquet` with:

```python
def csv_to_parquet(csv_gz: Path, parquet_path: Path) -> Path:
    '''Stream-decompress an IPUMS .csv.gz beside parquet_path, then sink it to Parquet lazily.'''
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path = parquet_path.with_suffix('.csv')
    try:
        with gzip.open(csv_gz, 'rb') as src, csv_path.open('wb') as dst:
            shutil.copyfileobj(src, dst, length=16 * 1024 * 1024)
        lf = pl.scan_csv(csv_path, schema_overrides=SCHEMA_OVERRIDES, infer_schema_length=100_000)
        codes = [c for c in CODE_COLUMNS if c in lf.collect_schema().names()]
        if codes:
            lf = lf.with_columns(pl.col(codes).cast(pl.String).str.zfill(4))
        lf.sink_parquet(parquet_path)
    finally:
        csv_path.unlink(missing_ok=True)
    return parquet_path
```

In `main`, replace the `out` parameter

```python
    out: Annotated[
        Path,
        typer.Option('--out', help='Directory for extract downloads.'),
    ] = DEFAULT_OUTPUT_DIR,
```

with

```python
    data_dir: Annotated[
        Path,
        typer.Option('--data-dir', help='Data root holding raw/, derived/, and preview/.'),
    ] = paths.DATA_DIR,
```

and the `dry_run` help string `'Write definitions without submitting.'` with `'Write definitions to preview/ without submitting.'`. Then replace the loop, from `    for name in extracts:` to the end of `main`, with:

```python
    for name in extracts:
        samples = select_samples(catalog, name, start_month)
        if not samples:
            typer.echo(f'{name}: no matching samples in the IPUMS CPS catalog', err=True)
            raise typer.Exit(code=1)
        extract = build_extract(name, samples)
        summary = f'{name}: {len(samples)} samples, {samples[0]} to {samples[-1]}'
        if dry_run:
            preview = ipums_delivery.write_preview(extract, data_dir, 'cps', name)
            typer.echo(f'{summary}; wrote {preview}')
            continue

        typer.echo(summary)
        extract_dir = ipums_delivery.deliver(client, extract, data_dir, 'cps', name)
        for csv_gz in sorted(extract_dir.glob('*.csv.gz')):
            parquet = ipums_delivery.parquet_path(data_dir, 'cps', name, csv_gz)
            typer.echo(f'{name}: wrote {csv_to_parquet(csv_gz, parquet)}')
```

`import json` goes. Everything above the loop in `main`, and `parse_month`, `select_samples` and `build_extract`, stay unchanged.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_cps_benchmark_extract.py tests/test_cps_properties.py tests/test_cli.py -v && uv run --locked behave`
Expected: all passed; 2 scenarios passed.

- [ ] **Step 5: Update the CPS and shared-flow docs**

In `README.md`, replace

```
The default destination is `<project-root>/data/raw/cps/`, with `monthly/` and
`asec/` subdirectories. Use `--out PATH` to override it. CPS stores industry and
occupation as Census codes; conversion pads `IND`, `OCC`, `INDLY`, and `OCCLY`
to four-character strings. Mapping them to NAICS and SOC remains a later step.
```

with

```
Files follow the ACS layout. Dry-run definitions go to
`data/preview/cps/<set>/extract.json`. Each delivered extract gets its own
`data/raw/cps/<set>/cps_<number>/` and is recorded in `data/raw/manifest.jsonl`,
and Parquet goes to `data/derived/cps/<set>/`. `--data-dir PATH` moves the whole
data root. CPS stores industry and occupation as Census codes; conversion pads
`IND`, `OCC`, `INDLY`, and `OCCLY` to four-character strings. Mapping them to
NAICS and SOC remains a later step.
```

In `CLAUDE.md`, replace the whole `**Shared flow.**` paragraph with:

```
**Shared flow.** `build_extract()` returns an `ipumspy.MicrodataExtract` (CSV, data-quality flags). `--dry-run` writes its definition to `data/preview/<source>/<set>/extract.json`, never under `raw/`. Otherwise `ipums_delivery.deliver()` submits, then creates a new `data/raw/<source>/<set>/<collection>_<number>/`; an existing one fails the run, because raw downloads are immutable. It writes the submitted `extract.json` there, waits, downloads the `.csv.gz` and `.xml` into it, and appends every file to `data/raw/manifest.jsonl` (`manifest.py`: SHA-256, extract number, sample IDs, retrieval time, client version). `csv_to_parquet()` then streams each `.csv.gz` to a temporary CSV under `data/derived/<source>/<set>/` and lazily sinks Parquet beside it. Code columns stay strings: ACS `INDNAICS`/`OCCSOC` through schema overrides (values like `31M`, `1110XX`); CPS `IND`/`OCC`/`INDLY`/`OCCLY` zero-padded to four characters. Re-running submits a new extract into a new directory; there is no resume.
```

and in the `**Credentials.**` paragraph replace `Output defaults to `data/raw/acs` and `data/raw/cps` under the project root.` with ``--data-dir` defaults to `data/` under the project root (`paths.DATA_DIR`).`

- [ ] **Step 6: Run the full suite and lint**

Run: `uv run --locked pytest -q && uv run --locked ruff check .`
Expected: all passed; `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add src/embedding_data/cps_benchmark_extract.py tests/test_cps_benchmark_extract.py tests/test_cli.py features/environment.py features/steps/cps_dry_run.py README.md CLAUDE.md
git commit -m "feat(cps): deliver each extract into its own raw directory and record it"
```

---

### Task 4: Refuse CPS monthly starts before January 2025 (R4.3)

**Files:**
- Modify: `src/embedding_data/cps_benchmark_extract.py`
- Modify: `tests/test_cps_benchmark_extract.py`, `tests/test_cli.py`
- Modify: `README.md` (CPS table row)

**Interfaces:**
- Consumes: `parse_month` (unchanged).
- Produces: `cps_benchmark_extract.MONTHLY_FIRST = '2025-01'`. A `--start` earlier than it raises `typer.BadParameter` (exit 2) before the key is read.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cps_benchmark_extract.py`:

```python
@pytest.mark.parametrize('start', ['2024-12', '2020-01'])
@pytest.mark.parametrize('mode', [[], ['--dry-run']], ids=['live', 'dry-run'])
def test_a_start_before_january_2025_is_refused_before_the_key_is_read(
    run_cli, data_directory, start, mode,
):
    result, client_factory = run_cli(['monthly', '--start', start, *mode])

    assert result.exit_code == 2, result.output
    assert f'{start} is before 2025-01' in result.output
    client_factory.assert_not_called()
    assert not data_directory.exists()
```

Append to `tests/test_cli.py`:

```python
def test_cps_start_before_2025_exits_non_zero(cli_runner, data_directory, dotenv_path):
    with (
        patch.object(cps_extract, 'DOTENV_PATH', dotenv_path),
        patch.object(cps_extract, 'IpumsApiClient', autospec=True) as client_factory,
    ):
        result = cli_runner.invoke(
            cli.app, ['cps', '--start', '2024-12', '--data-dir', str(data_directory)]
        )

    assert result.exit_code != 0
    assert '2024-12 is before 2025-01' in result.output
    client_factory.assert_not_called()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_cps_benchmark_extract.py tests/test_cli.py -k "before" -v`
Expected: FAIL. Without the floor, the `test_cps_benchmark_extract.py` cases exit 0, because 2024-12 and 2020-01 select catalog samples normally. The `test_cli.py` case exits 1, because it has no key. None of them prints `is before 2025-01`.

- [ ] **Step 3: Implement the floor**

In `src/embedding_data/cps_benchmark_extract.py`, below `ASEC_FIRST_YEAR = 2025`, add:

```python
# January 2025 is the first month on the 2022 Census industry codes (spec R4.3).
MONTHLY_FIRST = '2025-01'
```

Change the `start` option's default from `'2025-01'` to `MONTHLY_FIRST`. In `main`, directly after the `if unknown:` block and before `load_dotenv(...)`, insert:

```python
    start_month = parse_month(start)
    if start_month < parse_month(MONTHLY_FIRST):
        raise typer.BadParameter(
            f'{start} is before {MONTHLY_FIRST}, the first month on 2022 Census industry codes',
            param_hint="'--start'",
        )
```

and delete the later line `    start_month = parse_month(start)` that follows `catalog = client.get_all_sample_info('cps')`.

In the module docstring, replace

```
monthly: every basic monthly sample from --start (default 2025-01, the first
    month on the 2022 Census industry codes; occupation has used 2018 codes since
```

with

```
monthly: every basic monthly sample from --start (default and earliest 2025-01, the
    first month on the 2022 Census industry codes; occupation has used 2018 codes since
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_cps_benchmark_extract.py tests/test_cps_properties.py tests/test_cli.py -v && uv run --locked behave`
Expected: all passed; 2 scenarios passed. The Hypothesis properties still pass, because `parse_month` and `select_samples` are unchanged.

- [ ] **Step 5: Update the README row**

In `README.md`, replace the cell text `Catalog samples from `--start`, default `2025-01`; excludes ASEC` with `Catalog samples from `--start`, default and earliest `2025-01` (an earlier start is refused); excludes ASEC`.

- [ ] **Step 6: Run the full suite and lint**

Run: `uv run --locked pytest -q && uv run --locked ruff check .`
Expected: all passed; `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add src/embedding_data/cps_benchmark_extract.py tests/test_cps_benchmark_extract.py tests/test_cli.py README.md
git commit -m "feat(cps): refuse monthly starts before January 2025"
```

---

### Task 5: The OSHA command records downloads and converts once, outside raw

**Files:**
- Modify: `src/embedding_data/osha_benchmark_download.py`
- Modify: `tests/test_osha_benchmark_download.py` (full replacement)
- Modify: `tests/conftest.py` (remove `output_directory`)
- Modify: `README.md` (OSHA section), `CLAUDE.md` (Architecture `PROJECT_ROOT` sentence, OSHA paragraph)

**Interfaces:**
- Consumes: `paths.*` and `manifest.describe_file`, `append_entries` and `read_manifest` (Task 1).
- Produces:
  - `osha.csv_to_parquet(csv_path: Path, parquet_path: Path) -> Path`, whose temporary UTF-8 copy and `.part` file sit beside `parquet_path`.
  - `osha.main(data_dir)` with the option `--data-dir`.
  - `osha.DICTIONARY_URL`, `osha.CSV_URL` and `osha.file_name(url) -> str`, unchanged and used by Task 6.

- [ ] **Step 1: Write the failing tests**

Replace `tests/test_osha_benchmark_download.py` with:

```python
import datetime
import hashlib
from functools import partial
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

import httpx
import polars as pl
import pytest
import typer
from typer.main import get_command

from embedding_data import manifest, paths
from embedding_data import osha_benchmark_download as osha

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_NAME = 'ITA_Case_Detail_Data_2025_through_08-31-2026.csv'
PARQUET_NAME = CSV_NAME.replace('.csv', '.parquet')
DICTIONARY_NAME = 'case_detail_data_dictionary_2026.pdf'
PDF_BYTES = b'%PDF-1.6 fixture'

# One delivered row in miniature: a 4-digit ZIP that lost its leading zero upstream,
# an EIN with a leading zero, OSHA's 00-9900 placeholder SOC, an Int32-overflowing
# hours total, and a narrative mixing a Windows-1252 apostrophe with a UTF-8 one.
CSV_BYTES = (
    b'ID,ein,zip_code,naics_code,Size,total_hours_worked,date_of_incident,'
    b'date_of_death,time_of_incident,SOC_code,SOC_probability,'
    b'Unexpected_NAICS_SOC_Combo,New_nar_what_happened\r\n'
    b'1669828,012345678,2134,622110,22,5050596989,6/9/2025,,5:00,00-9900,0.91495013,'
    b'Y?,didn\x92t see the resident\xe2\x80\x99s cane\r\n'
)


@pytest.fixture
def cli_app():
    app = getattr(osha, 'app', None)
    assert isinstance(app, typer.Typer)
    return app


def streamed(body, content_length=None):
    '''A response whose body arrives over the transport, as it does from the network.'''
    length = len(body) if content_length is None else content_length
    return httpx.Response(
        200, headers={'Content-Length': str(length)}, stream=httpx.ByteStream(body)
    )


def osha_server(request):
    '''Serve the two files, refusing non-browser user agents as OSHA's CDN does.'''
    if not request.headers['User-Agent'].startswith('Mozilla/5.0'):
        return httpx.Response(403, html='<h1>403 ERROR</h1>')
    if request.url == osha.CSV_URL:
        return streamed(CSV_BYTES)
    if request.url == osha.DICTIONARY_URL:
        return streamed(PDF_BYTES)
    return httpx.Response(404)


def no_requests(request):
    raise AssertionError(f'unexpected request for {request.url}')


@pytest.fixture
def run_cli(cli_app, cli_runner, data_directory):
    def invoke_cli(handler=osha_server):
        client_factory = partial(osha.make_client, transport=httpx.MockTransport(handler))
        with patch.object(osha, 'make_client', client_factory):
            return cli_runner.invoke(cli_app, ['--data-dir', str(data_directory)])

    return invoke_cli


def test_default_data_root_is_under_project_root(cli_app):
    command = get_command(cli_app)
    with command.make_context('osha', []) as context:
        assert context.params['data_dir'] == PROJECT_ROOT / 'data'


def test_production_client_uses_http2_and_browser_user_agent():
    # Building the real client fails if the h2 extra is missing; nothing is requested.
    with osha.make_client() as client:
        assert client.headers['User-Agent'] == osha.USER_AGENT
        assert client.follow_redirects


def test_downloads_both_files_to_raw_and_writes_typed_parquet_to_derived(
    run_cli, data_directory,
):
    result = run_cli()

    assert result.exit_code == 0, result.output
    raw = data_directory / 'raw/osha'
    assert (raw / CSV_NAME).read_bytes() == CSV_BYTES
    assert (raw / DICTIONARY_NAME).read_bytes() == PDF_BYTES
    assert sorted(path.name for path in raw.iterdir()) == sorted([CSV_NAME, DICTIONARY_NAME])
    derived = data_directory / 'derived/osha'
    assert sorted(path.name for path in derived.iterdir()) == [PARQUET_NAME]

    data = pl.read_parquet(derived / PARQUET_NAME)
    assert data.schema == {
        'ID': pl.Int64,
        'ein': pl.String,
        'zip_code': pl.String,
        'naics_code': pl.String,
        'Size': pl.Int64,
        'total_hours_worked': pl.Int64,
        'date_of_incident': pl.Date,
        'date_of_death': pl.Date,
        'time_of_incident': pl.Time,
        'SOC_code': pl.String,
        'SOC_probability': pl.Float64,
        'Unexpected_NAICS_SOC_Combo': pl.String,
        'New_nar_what_happened': pl.String,
    }
    assert data.row(0) == (
        1669828, '012345678', '2134', '622110', 22, 5050596989,
        datetime.date(2025, 6, 9), None, datetime.time(5, 0),
        '00-9900', 0.91495013, 'Y?', 'didn’t see the resident’s cane',
    )


def test_each_download_is_recorded_with_its_url_hash_and_client(run_cli, data_directory):
    result = run_cli()

    assert result.exit_code == 0, result.output
    entries = manifest.read_manifest(paths.manifest_path(data_directory))
    assert [(entry.path, entry.source_url) for entry in entries] == [
        (f'osha/{DICTIONARY_NAME}', osha.DICTIONARY_URL),
        (f'osha/{CSV_NAME}', osha.CSV_URL),
    ]
    for entry, body in zip(entries, [PDF_BYTES, CSV_BYTES], strict=True):
        assert entry.sha256 == hashlib.sha256(body).hexdigest()
        assert entry.size == len(body)
        assert (entry.client, entry.client_version) == ('httpx', version('httpx'))
        assert (entry.collection, entry.extract_number, entry.samples) == (None, None, ())
        assert entry.proxies == ()
        retrieved_at = datetime.datetime.fromisoformat(entry.retrieved_at)
        assert retrieved_at.utcoffset() == datetime.timedelta(0)


def test_existing_raw_files_are_neither_downloaded_nor_recorded_again(run_cli, data_directory):
    raw = data_directory / 'raw/osha'
    raw.mkdir(parents=True)
    (raw / CSV_NAME).write_bytes(CSV_BYTES)
    (raw / DICTIONARY_NAME).write_bytes(PDF_BYTES)

    result = run_cli(no_requests)

    assert result.exit_code == 0, result.output
    assert (data_directory / 'derived/osha' / PARQUET_NAME).exists()
    assert manifest.read_manifest(paths.manifest_path(data_directory)) == []


def test_a_second_run_neither_downloads_nor_reconverts(run_cli, data_directory):
    first = run_cli()
    assert first.exit_code == 0, first.output
    parquet = data_directory / 'derived/osha' / PARQUET_NAME
    converted = (parquet.read_bytes(), parquet.stat().st_mtime_ns)
    recorded = paths.manifest_path(data_directory).read_bytes()

    second = run_cli(no_requests)

    assert second.exit_code == 0, second.output
    assert 'not converting again' in second.output
    assert (parquet.read_bytes(), parquet.stat().st_mtime_ns) == converted
    assert paths.manifest_path(data_directory).read_bytes() == recorded


def test_refused_download_leaves_no_file(tmp_path):
    destination = tmp_path / CSV_NAME
    refusing = httpx.MockTransport(lambda request: httpx.Response(403))

    with osha.make_client(transport=refusing) as client, pytest.raises(httpx.HTTPStatusError):
        osha.download(client, osha.CSV_URL, destination)

    assert list(tmp_path.iterdir()) == []


def test_truncated_download_leaves_no_file(tmp_path):
    destination = tmp_path / CSV_NAME
    truncating = httpx.MockTransport(lambda request: streamed(b'ID\r\n', content_length=100))

    with osha.make_client(transport=truncating) as client, pytest.raises(httpx.HTTPError):
        osha.download(client, osha.CSV_URL, destination)

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        (b'plain ascii\r\n', 'plain ascii\r\n'),
        (b'resident\xe2\x80\x99s\r\n', 'resident’s\r\n'),
        (b'didn\x92t\r\n', 'didn’t\r\n'),
        (b'Garc\xeda, \x93quoted\x94 \x96 dash\r\n', 'García, “quoted” – dash\r\n'),
        (b'didn\x92t see the resident\xe2\x80\x99s cane', 'didn’t see the resident’s cane'),
    ],
    ids=['ascii', 'utf8', 'cp1252', 'cp1252-accents-and-punctuation', 'mixed-in-one-line'],
)
def test_decode_line_reads_utf8_and_windows_1252(raw, expected):
    assert osha.decode_line(raw) == expected


def test_decode_line_fails_on_a_byte_undefined_in_windows_1252():
    with pytest.raises(UnicodeDecodeError):
        osha.decode_line(b'neither UTF-8 nor cp1252: \x81\r\n')


def test_conversion_fails_on_an_unparseable_typed_value(tmp_path):
    csv_path = tmp_path / 'raw' / CSV_NAME
    csv_path.parent.mkdir()
    csv_path.write_bytes(b'ID,date_of_incident\r\n1,2025-06-09\r\n')
    derived = tmp_path / 'derived'

    with pytest.raises(pl.exceptions.InvalidOperationError):
        osha.csv_to_parquet(csv_path, derived / PARQUET_NAME)

    assert sorted(path.name for path in csv_path.parent.iterdir()) == [CSV_NAME]
    assert list(derived.iterdir()) == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_osha_benchmark_download.py -v`
Expected: FAIL. You should see `KeyError: 'data_dir'`, `No such option: --data-dir`, and a `TypeError` from `csv_to_parquet()` taking one positional argument.

- [ ] **Step 3: Implement**

In `src/embedding_data/osha_benchmark_download.py`, replace the docstring lines

```
Usage:
    uv run embedding-data osha
    uv run embedding-data osha --out /tmp/osha

Downloads default to data/raw/osha under the project root. A file that already
exists there is kept as delivered and not downloaded again; the CSV's name carries
its submission through-date, so a later OSHA release arrives under a new name.
```

with

```
Usage:
    uv run embedding-data osha
    uv run embedding-data osha --data-dir /tmp/osha-data

Raw files go to data/raw/osha, and each download is recorded in
data/raw/manifest.jsonl with its URL, retrieval time, SHA-256, and httpx version.
A file that already exists there is kept as delivered and not downloaded again;
the CSV's name carries its submission through-date, so a later OSHA release
arrives under a new name. The Parquet goes to data/derived/osha and is built only
when absent; delete it to rebuild. --data-dir moves the whole data root.
```

and the lines

```
The CSV mixes encodings: most non-ASCII text is Windows-1252, a few rows are UTF-8.
It is transcoded to a temporary UTF-8 copy and sunk to Parquet next to the raw
file. Code columns stay strings even where the data dictionary calls them numeric
```

with

```
The CSV mixes encodings: most non-ASCII text is Windows-1252, a few rows are UTF-8.
It is transcoded to a temporary UTF-8 copy beside the Parquet and sunk to Parquet.
Code columns stay strings even where the data dictionary calls them numeric
```

Replace the import block and the two path constants, from `import codecs` through `DEFAULT_OUTPUT_DIR = PROJECT_ROOT / 'data' / 'raw' / 'osha'`, with:

```python
import codecs
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from typing import Annotated
from urllib.parse import urlsplit

import httpx
import polars as pl
import polars.selectors as cs
import typer

from embedding_data import manifest, paths
```

Replace `csv_to_parquet` with:

```python
def csv_to_parquet(csv_path: Path, parquet_path: Path) -> Path:
    '''Transcode the raw CSV to a temporary UTF-8 copy beside parquet_path; sink typed Parquet.'''
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    utf8_path = parquet_path.with_suffix('.utf8.csv')
    partial = parquet_path.with_name(parquet_path.name + '.part')
    try:
        # Splitting on b'\n' is safe for both encodings: neither uses 0x0A inside a character.
        with csv_path.open('rb') as src, utf8_path.open('w', encoding='utf-8', newline='') as dst:
            dst.writelines(decode_line(line) for line in src)

        lf = pl.scan_csv(utf8_path, infer_schema=False).with_columns(
            cs.by_name(INTEGER_COLUMNS, require_all=False).cast(pl.Int64),
            cs.by_name(FLOAT_COLUMNS, require_all=False).cast(pl.Float64),
            cs.by_name(DATE_COLUMNS, require_all=False).str.to_date('%m/%d/%Y'),
            cs.by_name(TIME_COLUMNS, require_all=False).str.to_time('%H:%M'),
        )
        lf.sink_parquet(partial)
        partial.replace(parquet_path)
    finally:
        utf8_path.unlink(missing_ok=True)
        partial.unlink(missing_ok=True)
    return parquet_path
```

Replace `main` with:

```python
@app.command(help=__doc__.splitlines()[0])
def main(
    data_dir: Annotated[
        Path,
        typer.Option('--data-dir', help='Data root holding raw/ and derived/.'),
    ] = paths.DATA_DIR,
) -> None:
    raw = paths.raw_dir(data_dir, 'osha')
    raw.mkdir(parents=True, exist_ok=True)
    manifest_path = paths.manifest_path(data_dir)
    with make_client() as client:
        for url in (DICTIONARY_URL, CSV_URL):
            destination = raw / file_name(url)
            if destination.exists():
                typer.echo(f'{destination.name}: exists, keeping it as delivered')
                continue
            download(client, url, destination)
            entry = manifest.describe_file(
                destination,
                manifest_path.parent,
                retrieved_at=datetime.now(UTC),
                client='httpx',
                client_version=version('httpx'),
                source_url=url,
            )
            manifest.append_entries(manifest_path, [entry])

    csv_path = raw / file_name(CSV_URL)
    parquet_path = paths.derived_dir(data_dir, 'osha') / csv_path.with_suffix('.parquet').name
    if parquet_path.exists():
        typer.echo(f'{parquet_path.name}: exists, not converting again')
        return
    typer.echo(f'wrote {csv_to_parquet(csv_path, parquet_path)}')
```

In `tests/conftest.py`, delete the `output_directory` fixture. First confirm nothing still uses it: `grep -rn output_directory tests features` should print nothing.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_osha_benchmark_download.py tests/test_cli.py -v`
Expected: all passed.

- [ ] **Step 5: Update the OSHA docs**

In `README.md`, replace everything from `The `osha` command needs no account or key. It downloads two files from osha.gov` through `command sends a browser `User-Agent`.` with:

````markdown
The `osha` command needs no account or key. It downloads two files from osha.gov
over HTTP/2 into `data/raw/osha/`, records each in `data/raw/manifest.jsonl`
with its URL, retrieval time, SHA-256, and `httpx` version, and converts the CSV
to Parquet in `data/derived/osha/`:

| File | Contents |
| --- | --- |
| `raw/osha/ITA_Case_Detail_Data_2025_through_08-31-2026.csv` | One row per recordable injury or illness filed for 2025 (`year_of_filing`) and submitted through 2026-08-31; some incident dates fall in 2024 |
| `raw/osha/case_detail_data_dictionary_2026.pdf` | OSHA's field definitions for the CSV |
| `derived/osha/ITA_Case_Detail_Data_2025_through_08-31-2026.parquet` | The CSV with typed columns |

```bash
uv run embedding-data osha
uv run embedding-data osha --data-dir /tmp/osha-data
```

A raw file that already exists is kept as delivered and not downloaded again,
and the Parquet is built only when it is absent; delete it to rebuild.
Downloads are written to a `.part` file and renamed only when complete.
osha.gov refuses non-browser user agents with HTTP 403, so the command sends a
browser `User-Agent`.
````

In `CLAUDE.md`, replace the sentence

```
`PROJECT_ROOT = Path(__file__).resolve().parents[2]` assumes the `src/embedding_data/` layout and an editable install, uv's default.
```

with

```
`paths.PROJECT_ROOT = Path(__file__).resolve().parents[2]` assumes the `src/embedding_data/` layout and an editable install, uv's default. `paths.py` also fixes the data layout under `--data-dir` (default `paths.DATA_DIR`): `raw/<source>/`, `raw/manifest.jsonl`, `derived/<source>/`, `preview/<source>/`.
```

and replace the whole `**OSHA download.**` paragraph with:

```
**OSHA download.** `osha` needs no key. osha.gov's CloudFront returns 403 to non-browser user agents, so `USER_AGENT` is a browser string. Existing files in `data/raw/osha` are never re-downloaded (raw immutability). Downloads go to `.part`, are renamed only after `num_bytes_downloaded` matches `Content-Length`, and are then recorded in the raw manifest. The CSV mixes Windows-1252 and UTF-8 bytes, sometimes within one line; `decode_line` transcodes it to a temporary UTF-8 CSV that is cast strictly (codes stay strings) and sunk to `data/derived/osha`, only when that Parquet is absent. Without existing files, a run downloads about 475 MB.
```

- [ ] **Step 6: Run the full suite, Behave and lint**

Run: `uv run --locked pytest -q && uv run --locked behave && uv run --locked ruff check .`
Expected: all passed; 2 scenarios passed; `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add src/embedding_data/osha_benchmark_download.py tests/test_osha_benchmark_download.py tests/conftest.py README.md CLAUDE.md
git commit -m "feat(osha): record downloads and convert once, outside raw"
```

---

### Task 6: One-off backfill of the pre-manifest raw tree

**Files:**
- Create: `src/embedding_data/raw_backfill.py`
- Create: `tests/test_raw_backfill.py`
- Modify: `README.md` (Current state, Files and planned outputs, Project layout), `CLAUDE.md` (What this repo is; new Raw provenance paragraph)

**Interfaces:**
- Consumes: `paths.*` and `manifest.describe_file`, `append_entries`, `read_manifest` and `sha256_file` (Task 1); `osha_benchmark_download.DICTIONARY_URL`, `CSV_URL` and `file_name` (Task 5).
- Produces:
  - `raw_backfill.backfill(data_dir: Path, lock_path: Path) -> list[ManifestEntry]`. It validates and hashes everything, then moves files and appends entries, and returns the entries appended (`[]` on a migrated tree).
  - `raw_backfill.app`, a single-command Typer app with `--data-dir`, run as `python -m embedding_data.raw_backfill`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_raw_backfill.py`:

```python
import gzip
import json
import os
from datetime import UTC, datetime

import pytest

from embedding_data import manifest, paths, raw_backfill
from embedding_data import osha_benchmark_download as osha

LOCK = '''version = 1

[[package]]
name = "httpx"
version = "0.28.1"

[[package]]
name = "ipumspy"
version = "0.8.2"
'''
DEFINED = datetime(2026, 10, 12, 16, 41, 39, tzinfo=UTC).timestamp()
DELIVERED = datetime(2026, 10, 12, 16, 50, 59, tzinfo=UTC).timestamp()
PROXIES = ('retrieved_at', 'client_version')
OSHA_CSV = osha.file_name(osha.CSV_URL)
OSHA_PDF = osha.file_name(osha.DICTIONARY_URL)
OSHA_PARQUET = OSHA_CSV.replace('.csv', '.parquet')


def write_legacy_extract(data_dir, source, set_name, name, samples):
    '''One extract as the pre-manifest commands left it: four files side by side.'''
    set_dir = paths.raw_dir(data_dir, source) / set_name
    set_dir.mkdir(parents=True)
    definition = set_dir / 'extract.json'
    definition.write_text(json.dumps({
        'description': f'{source.upper()} embedding benchmark: {set_name}',
        'collection': name.split('_')[0],
        'samples': {sample: {} for sample in samples},
    }))
    (set_dir / f'{name}.csv.gz').write_bytes(gzip.compress(f'{name}\n1\n'.encode()))
    (set_dir / f'{name}.xml').write_text(f'<codeBook>{name}</codeBook>\n')
    (set_dir / f'{name}.parquet').write_bytes(f'PAR1 {name}'.encode())
    os.utime(definition, (DEFINED, DEFINED))
    for suffix in ('.csv.gz', '.xml'):
        os.utime(set_dir / f'{name}{suffix}', (DELIVERED, DELIVERED))


@pytest.fixture
def legacy(data_directory, tmp_path):
    '''A pre-Stage-1 data tree and a uv.lock; returns (data_dir, lock_path).'''
    write_legacy_extract(data_directory, 'acs', 'core', 'usa_00001', ['us2023a', 'us2024a'])
    write_legacy_extract(data_directory, 'cps', 'monthly', 'cps_00001', ['cps2025_01b'])
    osha_dir = paths.raw_dir(data_directory, 'osha')
    osha_dir.mkdir(parents=True)
    (osha_dir / OSHA_CSV).write_bytes(b'ID\r\n1\r\n')
    (osha_dir / OSHA_PDF).write_bytes(b'%PDF-1.6 fixture')
    (osha_dir / OSHA_PARQUET).write_bytes(b'PAR1 osha')
    for name in (OSHA_CSV, OSHA_PDF):
        os.utime(osha_dir / name, (DELIVERED, DELIVERED))
    lock_path = tmp_path / 'uv.lock'
    lock_path.write_text(LOCK)
    return data_directory, lock_path


def tree(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }


def test_raw_files_move_into_extract_directories_and_parquet_leaves_raw(legacy):
    data_dir, lock_path = legacy
    before = tree(data_dir)

    raw_backfill.backfill(data_dir, lock_path)

    after = tree(data_dir)
    moved = {
        'raw/acs/core/extract.json': 'raw/acs/core/usa_00001/extract.json',
        'raw/acs/core/usa_00001.csv.gz': 'raw/acs/core/usa_00001/usa_00001.csv.gz',
        'raw/acs/core/usa_00001.xml': 'raw/acs/core/usa_00001/usa_00001.xml',
        'raw/acs/core/usa_00001.parquet': 'derived/acs/core/usa_00001.parquet',
        'raw/cps/monthly/extract.json': 'raw/cps/monthly/cps_00001/extract.json',
        'raw/cps/monthly/cps_00001.csv.gz': 'raw/cps/monthly/cps_00001/cps_00001.csv.gz',
        'raw/cps/monthly/cps_00001.xml': 'raw/cps/monthly/cps_00001/cps_00001.xml',
        'raw/cps/monthly/cps_00001.parquet': 'derived/cps/monthly/cps_00001.parquet',
        f'raw/osha/{OSHA_PARQUET}': f'derived/osha/{OSHA_PARQUET}',
    }
    expected = {moved.get(path, path): contents for path, contents in before.items()}
    expected['raw/manifest.jsonl'] = after['raw/manifest.jsonl']
    assert after == expected


def test_every_raw_file_is_recorded_with_its_proxies_flagged(legacy):
    data_dir, lock_path = legacy

    appended = raw_backfill.backfill(data_dir, lock_path)

    assert manifest.read_manifest(paths.manifest_path(data_dir)) == appended
    raw = data_dir / 'raw'
    assert [entry.path for entry in appended] == [
        'acs/core/usa_00001/extract.json',
        'acs/core/usa_00001/usa_00001.csv.gz',
        'acs/core/usa_00001/usa_00001.xml',
        'cps/monthly/cps_00001/extract.json',
        'cps/monthly/cps_00001/cps_00001.csv.gz',
        'cps/monthly/cps_00001/cps_00001.xml',
        f'osha/{OSHA_PDF}',
        f'osha/{OSHA_CSV}',
    ]
    for entry in appended:
        assert entry.sha256 == manifest.sha256_file(raw / entry.path)
        assert entry.proxies == PROXIES
    data = appended[1]
    assert data == manifest.ManifestEntry(
        path='acs/core/usa_00001/usa_00001.csv.gz',
        sha256=data.sha256,
        size=(raw / data.path).stat().st_size,
        retrieved_at='2026-10-12T16:50:59+00:00',
        client='ipumspy',
        client_version='0.8.2',
        collection='usa',
        extract_number=1,
        samples=('us2023a', 'us2024a'),
        proxies=PROXIES,
    )
    assert appended[0].retrieved_at == '2026-10-12T16:41:39+00:00'
    assert appended[3].samples == ('cps2025_01b',)
    assert appended[-1] == manifest.ManifestEntry(
        path=f'osha/{OSHA_CSV}',
        sha256=appended[-1].sha256,
        size=len(b'ID\r\n1\r\n'),
        retrieved_at='2026-10-12T16:50:59+00:00',
        client='httpx',
        client_version='0.28.1',
        source_url=osha.CSV_URL,
        proxies=PROXIES,
    )


def test_a_migrated_tree_is_left_as_it_is(legacy):
    data_dir, lock_path = legacy
    raw_backfill.backfill(data_dir, lock_path)
    before = tree(data_dir)

    assert raw_backfill.backfill(data_dir, lock_path) == []
    assert tree(data_dir) == before


def make_definition_newer(data_dir):
    later = DELIVERED + 60
    os.utime(data_dir / 'raw/cps/monthly/extract.json', (later, later))


def point_definition_at_another_set(data_dir):
    definition = data_dir / 'raw/cps/monthly/extract.json'
    definition.write_text(json.dumps({
        'description': 'CPS embedding benchmark: asec', 'collection': 'cps', 'samples': {},
    }))
    os.utime(definition, (DEFINED, DEFINED))


def remove_codebook(data_dir):
    (data_dir / 'raw/cps/monthly/cps_00001.xml').unlink()


def add_second_extract(data_dir):
    (data_dir / 'raw/cps/monthly/cps_00002.csv.gz').write_bytes(gzip.compress(b'x'))


@pytest.mark.parametrize(
    ('corrupt', 'error', 'message'),
    [
        (make_definition_newer, ValueError, 'newer than cps_00001.csv.gz'),
        (point_definition_at_another_set, ValueError, 'does not define the monthly extract'),
        (remove_codebook, FileNotFoundError, 'cps_00001.xml'),
        (add_second_extract, ValueError, '2 extracts share one extract.json'),
    ],
    ids=['later-dry-run', 'wrong-set', 'missing-codebook', 'two-extracts'],
)
def test_a_doubtful_legacy_set_stops_the_backfill_before_anything_moves(
    legacy, corrupt, error, message,
):
    data_dir, lock_path = legacy
    corrupt(data_dir)
    before = tree(data_dir)

    with pytest.raises(error, match=message):
        raw_backfill.backfill(data_dir, lock_path)

    # cps/monthly is checked after acs/core, so an untouched tree proves nothing moved early.
    assert tree(data_dir) == before


def test_the_command_reports_what_it_recorded(legacy, cli_runner):
    data_dir, _ = legacy

    result = cli_runner.invoke(raw_backfill.app, ['--data-dir', str(data_dir)])

    assert result.exit_code == 0, result.output
    assert 'recorded acs/core/usa_00001/usa_00001.csv.gz' in result.output
    assert '8 entries appended to' in result.output
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --locked pytest tests/test_raw_backfill.py -v`
Expected: collection error, `ImportError: cannot import name 'raw_backfill' from 'embedding_data'`.

- [ ] **Step 3: Implement**

Create `src/embedding_data/raw_backfill.py`:

```python
'''Move raw files delivered before the raw manifest existed into its layout and record them.

Run once from the project root, after the Stage 1 commands are in place:

    uv run --locked python -m embedding_data.raw_backfill

Before Stage 1 each IPUMS set directory held one extract side by side
(extract.json, <name>.csv.gz, <name>.xml, and a converted <name>.parquet), and
data/raw/osha held its Parquet beside the CSV. This moves each extract's raw
files into <set>/<name>/, moves every Parquet under data/derived, and records
each raw file in data/raw/manifest.jsonl. Retrieval time and client version were
not recorded at download, so entries use the file's modification time and the
uv.lock version and flag both as proxies. Every check and hash runs before the
first file moves, and a tree already migrated is left as it is.
'''

import json
import re
import tomllib
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from embedding_data import manifest, osha_benchmark_download, paths

app = typer.Typer(add_completion=False, pretty_exceptions_show_locals=False)

LEGACY_DATA = re.compile(r'^(usa|cps)_(\d{5})\.csv\.gz$')
PROXIES = ('retrieved_at', 'client_version')


@dataclass(frozen=True)
class Move:
    source: Path
    destination: Path


def locked_version(lock_path: Path, package: str) -> str:
    '''The version uv.lock pins for package.'''
    for entry in tomllib.loads(lock_path.read_text())['package']:
        if entry['name'] == package:
            return entry['version']
    raise KeyError(f'{package} is not in {lock_path}')


def modified_at(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, UTC)


def plan_ipums_set(
    data_dir: Path, source: str, set_name: str, ipumspy_version: str,
) -> tuple[list[Move], list[manifest.ManifestEntry]]:
    '''Moves and manifest entries for one legacy set directory; none once it is migrated.'''
    set_dir = paths.raw_dir(data_dir, source) / set_name
    data_files = sorted(set_dir.glob('*.csv.gz'))
    if not data_files:
        return [], []
    if len(data_files) > 1:
        raise ValueError(f'{set_dir}: {len(data_files)} extracts share one extract.json')
    data = data_files[0]
    match = LEGACY_DATA.match(data.name)
    if match is None:
        raise ValueError(f'{data}: not an IPUMS extract file name')
    collection, number = match[1], int(match[2])
    name = data.name.removesuffix('.csv.gz')
    definition = set_dir / 'extract.json'
    codebook = set_dir / f'{name}.xml'
    for required in (definition, codebook):
        if not required.exists():
            raise FileNotFoundError(f'{required}: missing beside {data.name}')
    submitted = json.loads(definition.read_text())
    if (
        submitted['collection'] != collection
        or not submitted['description'].endswith(f': {set_name}')
    ):
        raise ValueError(f'{definition} does not define the {set_name} extract {name}')
    # The definition is written before submission; a dry run after the download rewrites it.
    if modified_at(definition) >= modified_at(data):
        raise ValueError(f'{definition} is newer than {data.name}: it may be a later dry run')

    raw_root = paths.manifest_path(data_dir).parent
    extract_dir = set_dir / name
    moves, entries = [], []
    for file in (definition, data, codebook):
        move = Move(file, extract_dir / file.name)
        entry = manifest.describe_file(
            file,
            raw_root,
            retrieved_at=modified_at(file),
            client='ipumspy',
            client_version=ipumspy_version,
            collection=collection,
            extract_number=number,
            samples=submitted['samples'],
            proxies=PROXIES,
        )
        moves.append(move)
        entries.append(replace(entry, path=move.destination.relative_to(raw_root).as_posix()))
    parquet = set_dir / f'{name}.parquet'
    if parquet.exists():
        moves.append(Move(parquet, paths.derived_dir(data_dir, source) / set_name / parquet.name))
    return moves, entries


def plan_osha(
    data_dir: Path, httpx_version: str, recorded: set[str],
) -> tuple[list[Move], list[manifest.ManifestEntry]]:
    '''Moves for the OSHA Parquet, and entries for OSHA downloads not yet recorded.'''
    raw = paths.raw_dir(data_dir, 'osha')
    raw_root = paths.manifest_path(data_dir).parent
    moves = [
        Move(parquet, paths.derived_dir(data_dir, 'osha') / parquet.name)
        for parquet in sorted(raw.glob('*.parquet'))
    ]
    entries = []
    for url in (osha_benchmark_download.DICTIONARY_URL, osha_benchmark_download.CSV_URL):
        file = raw / osha_benchmark_download.file_name(url)
        if file.exists() and file.relative_to(raw_root).as_posix() not in recorded:
            entries.append(
                manifest.describe_file(
                    file,
                    raw_root,
                    retrieved_at=modified_at(file),
                    client='httpx',
                    client_version=httpx_version,
                    source_url=url,
                    proxies=PROXIES,
                )
            )
    return moves, entries


def backfill(data_dir: Path, lock_path: Path) -> list[manifest.ManifestEntry]:
    '''Migrate a legacy raw tree and record its files; return the entries appended.'''
    manifest_path = paths.manifest_path(data_dir)
    recorded = {entry.path for entry in manifest.read_manifest(manifest_path)}
    ipumspy_version = locked_version(lock_path, 'ipumspy')
    moves, entries = [], []
    for source in ('acs', 'cps'):
        source_dir = paths.raw_dir(data_dir, source)
        if not source_dir.exists():
            continue
        for set_dir in sorted(path for path in source_dir.iterdir() if path.is_dir()):
            set_moves, set_entries = plan_ipums_set(
                data_dir, source, set_dir.name, ipumspy_version
            )
            moves += set_moves
            entries += set_entries
    osha_moves, osha_entries = plan_osha(data_dir, locked_version(lock_path, 'httpx'), recorded)
    moves += osha_moves
    entries += osha_entries

    for move in moves:
        if move.destination.exists():
            raise FileExistsError(f'{move.destination} exists; not moving {move.source} onto it')
    for move in moves:
        move.destination.parent.mkdir(parents=True, exist_ok=True)
        move.source.rename(move.destination)
    manifest.append_entries(manifest_path, entries)
    return entries


@app.command(help=__doc__.splitlines()[0])
def main(
    data_dir: Annotated[
        Path,
        typer.Option('--data-dir', help='Data root holding raw/ and derived/.'),
    ] = paths.DATA_DIR,
) -> None:
    entries = backfill(data_dir, paths.PROJECT_ROOT / 'uv.lock')
    for entry in entries:
        typer.echo(f'recorded {entry.path} ({entry.size:,} bytes)')
    typer.echo(f'{len(entries)} entries appended to {paths.manifest_path(data_dir)}')


if __name__ == '__main__':
    app()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/test_raw_backfill.py -v`
Expected: 8 passed (3 single tests, 4 parametrized cases and 1 CLI test).

- [ ] **Step 5: Update the cross-cutting docs**

In `README.md`, replace

```
OSHA Form 300A ingestion, classification concordances, geography allocation,
person-month linkage, aggregate targets, and provenance manifests are planned.
```

with

```
OSHA Form 300A ingestion, classification concordances, geography allocation,
person-month linkage, aggregate targets, and output manifests are planned. Raw
downloads are already recorded in `data/raw/manifest.jsonl`.
```

Replace the paragraph that begins `After a successful download and conversion, each extract directory contains its` and ends `and retrieval manifests are not implemented.` with:

```
All commands share one data root, `data/` by default (`--data-dir`):

| Path | Contents |
| --- | --- |
| `raw/manifest.jsonl` | One JSON line per raw file: path, SHA-256, size, retrieval time, client and version, and either the source URL or the IPUMS collection, extract number, and sample IDs |
| `raw/acs/<set>/usa_<number>/`, `raw/cps/<set>/cps_<number>/` | One delivered IPUMS extract: the submitted `extract.json`, the `.csv.gz` data, and the `.xml` DDI codebook |
| `raw/osha/` | OSHA downloads as delivered |
| `derived/<source>/` | Parquet converted from raw files |
| `preview/<source>/<set>/extract.json` | Dry-run definitions, overwritten by the next dry run |

Raw files are never edited, overwritten, or re-downloaded, and each path is
recorded once. Files delivered before the manifest existed were moved into this
layout by `uv run --locked python -m embedding_data.raw_backfill`. Their entries
use the file modification time and the `uv.lock` client version, both flagged in
`proxies`. Downloads are not resumable: re-running an IPUMS command submits a
new extract.
```

In the Project layout block, replace

```
src/embedding_data/cli.py                    embedding-data console entry point
```

with

```
src/embedding_data/cli.py                    embedding-data console entry point
src/embedding_data/paths.py                  Data root layout: raw/, derived/, preview/
src/embedding_data/manifest.py               Append-only raw-file manifest (SHA-256 and provenance)
src/embedding_data/ipums_delivery.py         Shared IPUMS preview, submission, download, and recording
src/embedding_data/raw_backfill.py           One-off migration of pre-manifest raw files
```

and replace

```
data/raw/acs/                                Default ACS output location
data/raw/cps/                                Default CPS output location
data/raw/osha/                               OSHA case-detail downloads and Parquet
```

with

```
data/raw/                                    Raw downloads as delivered, and manifest.jsonl
data/derived/                                Parquet converted from raw files
data/preview/                                Dry-run extract definitions
```

In `CLAUDE.md`, replace `OSHA Form 300A ingestion, code parsing, geography allocation, targets, and manifests are planned, not built.` with `Every raw file is recorded in an append-only manifest (`data/raw/manifest.jsonl`); OSHA Form 300A ingestion, code parsing, geography allocation, targets, and output manifests are planned, not built.` Then insert this paragraph after the `**OSHA download.**` paragraph:

```
**Raw provenance.** `manifest.append_entries()` refuses a path already recorded, so each raw file maps to one hash for good; `manifest.entry_for()` looks an entry up for output manifests to cite. `raw_backfill.py` is a one-off (`python -m embedding_data.raw_backfill`) that moved the files delivered before the manifest into this layout; their entries flag `retrieved_at` and `client_version` as proxies. On a migrated tree it does nothing.
```

- [ ] **Step 6: Run the full suite, Behave and lint**

Run: `uv run --locked pytest -q && uv run --locked behave && uv run --locked ruff check .`
Expected: all passed; 2 scenarios passed; `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add src/embedding_data/raw_backfill.py tests/test_raw_backfill.py README.md CLAUDE.md
git commit -m "feat(manifest): add the one-off backfill for pre-manifest raw files"
```

---

### Task 7: Migrate the real data tree (owner gate)

This task changes the real, gitignored data tree and commits nothing. **The controller session runs it, never a dispatched subagent**, because it needs the owner's explicit yes. It runs from the branch's checkout after Task 6 is committed, and before the branch merges: the stage cannot be stamped complete without the migrated tree.

`data/` is gitignored, so a git worktree has none, and `paths.DATA_DIR` there points at an empty tree. Every command below therefore names the real root explicitly: `REAL_DATA=/Users/lowell/Projects/embedding-data/data`, set again in each step, because shell state does not carry over between commands. Run the commands from the checkout that holds Tasks 1–6 (the worktree, if one is in use), and never from a checkout that lacks `raw_backfill`.

**Files:** none in git; `$REAL_DATA/raw/**` and `$REAL_DATA/derived/**` on disk.

**Interfaces:**
- Consumes: `raw_backfill` (Task 6) and `manifest.read_manifest` and `sha256_file` (Task 1).
- Produces: `data/raw/manifest.jsonl` with 17 entries; the five extracts in `data/raw/<source>/<set>/<name>/`; six Parquet files under `data/derived/`.

- [ ] **Step 1: Get the go-ahead**

Ask your human partner, in these words: "Task 7 migrates the real data now, before the branch merges. It moves the files under `/Users/lowell/Projects/embedding-data/data/raw` into per-extract directories, moves six Parquet files to `data/derived`, and appends 17 entries to a new `data/raw/manifest.jsonl`. Proceed?" Do not continue without an explicit yes.

- [ ] **Step 2: Record the pre-run state**

```bash
REAL_DATA=/Users/lowell/Projects/embedding-data/data
test -e "$REAL_DATA/raw/manifest.jsonl" && echo 'manifest exists: stop and ask' || echo 'no manifest yet'
find "$REAL_DATA/raw" -type f ! -name '*.parquet' ! -name '.DS_Store' -exec shasum -a 256 {} + \
  | awk '{print $1}' | sort > "${TMPDIR:-/tmp}/raw-before.sha256"
wc -l < "${TMPDIR:-/tmp}/raw-before.sha256"
find "$REAL_DATA/raw" -name '*.parquet' | sort
```

Expected:
- `no manifest yet`, then `17`.
- Six Parquet paths under `$REAL_DATA/raw`: `acs/core/usa_00001.parquet`, `acs/five_year/usa_00003.parquet`, `acs/vintage/usa_00002.parquet`, `cps/asec/cps_00002.parquet`, `cps/monthly/cps_00001.parquet` and `osha/ITA_Case_Detail_Data_2025_through_08-31-2026.parquet`.

Any other result: stop and report to your human partner.

- [ ] **Step 3: Run the backfill**

Run: `REAL_DATA=/Users/lowell/Projects/embedding-data/data; uv run --locked python -m embedding_data.raw_backfill --data-dir "$REAL_DATA"`
Expected: 17 `recorded …` lines, then `17 entries appended to /Users/lowell/Projects/embedding-data/data/raw/manifest.jsonl`. A count of `0` means it ran against the wrong root: stop. If it raises, nothing has moved. Report the message to your human partner and stop.

- [ ] **Step 4: Verify hashes, coverage, and the seven deliveries**

```bash
REAL_DATA=/Users/lowell/Projects/embedding-data/data
uv run --locked python - "$REAL_DATA" "${TMPDIR:-/tmp}/raw-before.sha256" <<'EOF'
import sys
from pathlib import Path

from embedding_data import manifest, paths

manifest_path = paths.manifest_path(Path(sys.argv[1]))
raw = manifest_path.parent
entries = manifest.read_manifest(manifest_path)
before = Path(sys.argv[2]).read_text().split()
assert sorted(entry.sha256 for entry in entries) == sorted(before), 'hash multiset changed'
for entry in entries:
    assert manifest.sha256_file(raw / entry.path) == entry.sha256, entry.path
    assert entry.proxies == ('retrieved_at', 'client_version'), entry.path
on_disk = sorted(
    path.relative_to(raw).as_posix()
    for path in raw.rglob('*')
    if path.is_file() and path.name not in {'manifest.jsonl', '.DS_Store'}
)
assert on_disk == sorted(entry.path for entry in entries), 'a raw file is unrecorded'
by_path = {entry.path: entry for entry in entries}
for path in [
    'acs/core/usa_00001/usa_00001.csv.gz',
    'acs/vintage/usa_00002/usa_00002.csv.gz',
    'acs/five_year/usa_00003/usa_00003.csv.gz',
    'cps/monthly/cps_00001/cps_00001.csv.gz',
    'cps/asec/cps_00002/cps_00002.csv.gz',
    'osha/ITA_Case_Detail_Data_2025_through_08-31-2026.csv',
    'osha/case_detail_data_dictionary_2026.pdf',
]:
    entry = by_path[path]
    print(path, entry.sha256[:12], entry.extract_number, entry.source_url or entry.samples[0])
print(len(entries), 'entries verified')
EOF
find "$REAL_DATA/raw" -name '*.parquet'
find "$REAL_DATA/derived" -name '*.parquet' | sort
```

Expected:
- Seven lines. The IPUMS lines show extract numbers 1, 2, 3, 1 and 2 with their first sample ID; the OSHA lines show `None` and their URL.
- `17 entries verified`.
- No output from the first `find`.
- Six paths from the second.

- [ ] **Step 5: Check that a dry run leaves raw alone**

```bash
REAL_DATA=/Users/lowell/Projects/embedding-data/data
uv run embedding-data acs core --dry-run --data-dir "$REAL_DATA"
find "$REAL_DATA/raw" -type f -newer "$REAL_DATA/raw/manifest.jsonl"
```

Expected: `core: wrote /Users/lowell/Projects/embedding-data/data/preview/acs/core/extract.json`, and no output from `find`.

- [ ] **Step 6: Report**

Nothing is committed, because `data/` is gitignored. Paste the Step 4 output into the task report.

---

### Task 8: Spec amendment (owner-approved wording) and final verification

**Files:**
- Modify: `specs/embedding-evaluation-data-spec.md`

**Interfaces:**
- Consumes: nothing.
- Produces: the spec records registration, the 2026-10-12 deliveries and the backfill proxies. Its status header is untouched.

- [ ] **Step 1: Apply the five amendments exactly**

Edit 1 — Locator table. Replace

```
| **XA** | `acs_benchmark_extract.py`, with `acs_benchmark_samples_variables.xlsx` | Executable ACS extract definition. Dry-run tested; not yet submitted to IPUMS. |
| **XC** | `cps_benchmark_extract.py`, with `cps_benchmark_samples_variables.xlsx` | Executable CPS extract definition. Sample selection tested against a mocked catalog only. |
```

with

```
| **XA** | `acs_benchmark_extract.py`, with `acs_benchmark_samples_variables.xlsx` | Executable ACS extract definition. Dry-run tested; first submitted 2026-10-12 *(owner, plan 1, 2026-10-12)*. |
| **XC** | `cps_benchmark_extract.py`, with `cps_benchmark_samples_variables.xlsx` | Executable CPS extract definition. Sample selection tested against a mocked catalog; first submitted 2026-10-12 *(owner, plan 1, 2026-10-12)*. |
```

Edit 2 — R1.3. Replace

```
> identify individuals.

*(chosen; D)*
```

with

```
> identify individuals.

*(chosen; D)* Both collections approved the registration, and the account's
first extracts were delivered on 2026-10-12 (see Rollout). *(owner, plan 1,
2026-10-12)*
```

Edit 3 — R1.4. Replace

```
Transformations read raw files and write derived Parquet; nothing edits a raw
file. *(added at synthesis; `extract.json` implemented in XA, XC)*
```

with

```
Transformations read raw files and write derived Parquet; nothing edits a raw
file. *(added at synthesis; `extract.json` implemented in XA, XC)* Files
delivered before the manifest existed are recorded with their modification time
and the `uv.lock` client version, each flagged as a proxy. *(owner, plan 1,
2026-10-12)*
```

Edit 4 — Rollout, first paragraph. Replace

```
**IPUMS registration blocks the most.** R3 and R4 cannot start until both
collections approve the account, so submit the R1.3 statement first.
```

with

```
**IPUMS registration is complete.** Both collections approved the account, and
five extracts were submitted and delivered on 2026-10-12: ACS `usa_00001`
(core), `usa_00002` (vintage), and `usa_00003` (five-year), and CPS `cps_00001`
(monthly) and `cps_00002` (ASEC). *(owner, plan 1, 2026-10-12)*
```

Edit 5 — Rollout, last paragraph. Replace

```
XA and XC were tested offline only: dry runs, a mocked sample catalog, and
synthetic conversions. Their first live submissions are V5. Planned targets are
never described as built, and no result from a fixture or a partial extract is
reported as a benchmark.
```

with

```
XA and XC were tested offline (dry runs, a mocked sample catalog, and synthetic
conversions) before their first live submissions on 2026-10-12. Those
submissions are V5's evidence; V4 and V5 stay open until their results are
recorded, and no delivered extract is trusted before then. *(owner, plan 1,
2026-10-12)* Planned targets are never described as built, and no result from a
fixture or a partial extract is reported as a benchmark.
```

- [ ] **Step 2: Verify the amendments landed and nothing else changed**

Run: `grep -c 'owner, plan 1' specs/embedding-evaluation-data-spec.md && git diff --stat specs/embedding-evaluation-data-spec.md && head -4 specs/embedding-evaluation-data-spec.md`
Expected: `6` (XA, XC, R1.3, R1.4, Rollout ×2). The diff touches only that file. The header still reads `> For agentic workers: REQUIRED NEXT SKILL: derive-roadmap — do not plan this`.

- [ ] **Step 3: Commit**

```bash
git add specs/embedding-evaluation-data-spec.md
git commit -m "docs(specs): record IPUMS registration, first deliveries, and backfill proxies"
```

- [ ] **Step 4: Final verification**

```bash
uv run --locked pytest -q
uv run --locked behave
uv run --locked ruff check .
uv lock --check
uv run embedding-data acs core --dry-run --data-dir "$(mktemp -d)"
uv run embedding-data cps --help
grep -rn -- '--out' README.md CLAUDE.md src tests features
```

Expected:
- `grep`: no output, so no stale `--out` mention remains.
- pytest: all passed, 0 failed.
- Behave: `2 scenarios passed, 0 failed`.
- ruff: `All checks passed!`
- `uv lock --check`: exits 0.
- The ACS dry run prints `core: wrote /…/preview/acs/core/extract.json`.
- `cps --help` lists `--data-dir` and `--start`, and does not list `--out`.

Then run the Plan Completion Protocol, including step 3a (roadmap handoff). Leave the spec in place at step 5.
