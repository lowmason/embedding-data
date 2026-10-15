# IPUMS Extract Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when the owner chooses inline execution at the handoff. Steps use checkbox syntax for tracking.

> Roadmap: specs/embedding-evaluation-data-spec-roadmap.md, Stage 7 — on plan completion, tick the stage and re-validate later stages against what shipped.

**Goal:** Verify the five delivered IPUMS extracts with reproducible V4–V7 and
ACS/CPS V10 evidence, record the resulting interpretation rules, and make a
failed CSV conversion recoverable without another IPUMS submission.

**Architecture:** Keep immutable public-reference acquisition separate from
offline verification. Parse delivery definitions and DDI metadata, compare raw
CSV with existing Parquet in bounded ordered batches, and produce only aggregate
acceptance, storage, industry-scheme and employment diagnostics. A named run
freezes selected deliveries, public references, software and outputs; a second
offline run must reproduce the aggregate results before the finding is adopted.

**Tech Stack:** Python >=3.14; existing Polars >=2.0.0, ipumspy >=0.8.2,
httpx >=0.28.1, Typer >=0.27.3 and fastexcel >=0.21.0; pytest/Hypothesis;
stdlib gzip, shutil, tempfile, csv, decimal, json, hashlib, dataclasses and
xml.etree.ElementTree. No new dependency or lockfile change.

**Spec:** [Source spec](../embedding-evaluation-data-spec.md), scoped to Stage 7
of the [roadmap](../embedding-evaluation-data-spec-roadmap.md): V4–V7,
V10 (ACS/CPS), R3.2/R3.5/R4.5/R4.9/R4.11 and Design provenance XA/XC.
Read completed plans 1 and 3's Handoff sections and the Stage 7-targeted items
in [deferred items](../deferred_items.md).

## Global Constraints

The following source-spec requirements apply verbatim:

- "Raw downloads are immutable and kept as delivered"
- "Transformations are lazy polars with method-style expressions."
- "Every transformation is deterministic and runs offline from raw files."
- "Tests use fixtures, with no network and no credentials."
- "Store IND, OCC, INDLY, and OCCLY as zero-padded four-character strings"
- "CPS totals use WTFINL, not the composite weight behind official estimates, so record the gap rather than tuning it away."
- "No target and no ITA description enters training, curriculum construction, hard-negative mining, or model selection for an embedder it evaluates."

The code identifiers in the preceding quotations are rendered without the
source's inline-code delimiters; their spelling and values are unchanged.

Repository constraints also apply: microdata stay in the gitignored local data
tree; share aggregates only; use the source-specific existing indentation.
Never print person rows, IDs, raw CSV examples, environment contents or keys.
Keep module-global DOTENV_PATH and IpumsApiClient test seams. Do not invoke
ipumspy's pandas microdata readers. Metadata-only parsing is permitted.

Stage boundaries:

- Use the five 2026-10-12 deliveries. V5 uses those real submissions, definitions,
  delivered DDI and headers; do not submit new extracts to repeat acceptance.
- Public-reference acquisition is explicit and uses no authentication. Offline
  commands neither load the root .env nor create an IPUMS client.
- Do not call ACS/CPS acquisition, OSHA, build_summary_table, verification sample,
  or any Stage 4–6 builder to prepare this stage.
- Leave the raw originals, existing derived Parquets and Stage 2–6 artifacts
  unchanged. Conversion recovery creates only missing derived outputs.
- No ACS code parser, PUMA allocation, CPS panel linkage, concordance builder,
  target family, replicate-SE helper or V9 threshold is built here.
- All five complete deliveries must be checked; a fixture or metadata inventory
  alone cannot complete the production gate.
- Source classification vintage, dataset citation version, DDI version,
  ipumspy package version and API extract version are separate fields.
- Missing flags, NIU and unknown metadata never become false, zero, a known
  vintage or evidence of acceptance by default.
- Differences from published totals are reported with explicit universes,
  periods, units and source vintages. Never choose a weight factor to minimize
  those differences or use a closeness threshold as the acceptance gate.

## Decisions

- **D1** (owner, plan review, 2026-10-15): "Approved." Approve this plan as
  written, including its six implementation defaults and the conditional
  R4.6 amendment wording. Applied in: Tasks 1–7 and Global Constraints.
  The amendment still requires the measured field/year matrix specified in
  Task 7; an unresolved finding does not become verified by this approval.
- **D2** (owner, execution handoff, 2026-10-15): "Handoff prompt for new session."
  Execute the approved plan via subagent-driven-development in a fresh
  session. Applied in: execution entry and Self-review and execution handoff.

---

## Entry evidence and proposed defaults

Prepared on main at a48149d, with a clean working tree, one existing local
commit ahead of origin/main. The plan-ID check returned highest 6, next free 7,
no collisions. Before the pause in planning, the unchanged tree passed:
883 pytest tests, one network canary deselected; two Behave scenarios / ten
steps; ruff; offline lock check (63 packages). No production measurement,
public-reference acquisition, IPUMS request or file modification was performed
to establish the metadata observations below.

Metadata-only inspection found these existing selections:

| Source/set | Delivery | Derived path under data/ | Metadata rows | Columns |
| --- | --- | --- | ---: | ---: |
| acs/core | usa_00001 | derived/acs/core/usa_00001.parquet | 3,206,859 | 147 |
| acs/vintage | usa_00002 | derived/acs/vintage/usa_00002.parquet | 1,575,420 | 146 |
| acs/five_year | usa_00003 | derived/acs/five_year/usa_00003.parquet | 7,456,212 | 148 |
| cps/monthly | cps_00001 | derived/cps/monthly/cps_00001.parquet | 922,115 | 43 |
| cps/asec | cps_00002 | derived/cps/asec/cps_00002.parquet | 276,854 | 209 |

Each raw directory is raw/<source>/<set>/<delivery>/ and contains
extract.json, <delivery>.xml and <delivery>.csv.gz. All fifteen files have
manifest entries; the production run must reverify hashes rather than trust
this inventory. Every requested name appeared in DDI and Parquet metadata;
neither observed row composition nor CSV storage has yet been verified.

Implementation defaults (approved in D1):

1. Add --convert-only to ACS/CPS. It recovers missing Parquets from complete
   manifested deliveries under the selected sets without reading credentials,
   contacting a catalog, submitting, or touching an existing Parquet.
2. Use a public IPUMS USA sample-ID catalog snapshot for V4. No authenticated
   catalog call is needed. Current public catalog information does not
   reconstruct the historical release available on the submission date.
3. Treat CSV values as numeric values as delivered only after the raw lexical,
   DDI and totals evidence agrees. Record any unresolved storage ambiguity;
   never mechanically divide by the DDI implied-decimal exponent.
4. Check ASEC IND and INDLY separately for 2025 and 2026 against both official
   2017 and 2022 Census industry lists. Require documentation plus
   discriminating evidence; membership in overlapping code sets alone does not
   establish a vintage. Defer any required concordance construction to Stage 11.
5. Compare civilian employed ACS residents age 16+ by state/year with
   B23025_004E, then average 2023/2024. Compare CPS age-16+ civilian employed
   persons by delivered month with BLS LNU02000000, NSA, converting thousands
   to persons. Include allocated records in these totals diagnostics.
6. Publish immutable aggregate runs under derived/ipums/verification/<run_id>/.
   Acquisition snapshots live separately under raw/references/ipums-verification/
   <reference_id>/. Explicit selections replace latest-directory discovery.

## Existing seams and traps

- ACS csv_to_parquet at src/embedding_data/acs_benchmark_extract.py:97 and
  CPS's at src/embedding_data/cps_benchmark_extract.py:127 currently sink
  directly to the final path. Their main functions convert only a new delivery.
  ipums_delivery.deliver always submits; it is not a recovery function.
- Reuse ipums_delivery.parquet_path(data_dir, source, set_name, csv_gz).
  Reuse manifest.entry_for for verified citations, never recorded_entry_for.
  Use manifest_audit.audit and the existing audit CLI for whole-tree checks.
- target_io supplies exclusive stage, write_json, file_record, inventory,
  verify_inventory and verify_raw. Reuse these public utilities without
  importing ITA preparation merely to obtain a software inventory.
- All five definitions have version=null. The files were written before
  submission; keep API extract version unknown. Their manifest retrieval times
  and client versions are explicitly proxies. Never rewrite that history.
- DDI SAMPLE categories are broad catalogs, not delivered sample frequencies.
  CPS deliveries have no SAMPLE column. Use observed YEAR/MONTH, plus the
  requested IDs and DDI study notes/time periods.
- The five-year sample is requested as us2024c; the DDI study note identifies
  2020–2024 ACS 5-year and SAMPLE category 202403. Preserve MULTYEAR when checking
  actual records; do not confuse it with the release year.
- ACS core/five-year have QMIGRAT1; vintage lacks it. Core infers it as String,
  five-year as Int64. Measure the delivered domain; do not coerce the core flag
  or declare the vintage observations unallocated.
- Requested REPWTP is a helper/placeholder, not an individual replicate.
  Verify the exact 1–80 or 1–160 expansion; wildcard REPWTP* would include the
  helper. Negative replicate weights are not automatically invalid.
- DDI generic fixed-width instructions and its .dat descriptor do not establish
  CSV scaling. Inspect every delivered weight family, including automatic
  household weights, but do not sum repeated household weights across person
  records as if those sums were household totals.
- Monthly EMPSAME codes 1=No, 2=Yes; ACTSAME codes 1=Yes, 2=No. Preserve DDI
  categories and document their different meanings for Stage 11. Do not build
  adjacent-month pairs here. Neither EARNWT nor LNKFW1MWT has a nonzero sentinel
  documented in the local DDI; do not invent one. Zero has a documented
  out-of-universe meaning.
- Monthly October 2025 is absent. The delivery has 20 months, January 2025
  through September 2026 with that gap. An absent month is not a zero total.
- Official ASEC 2025 source documentation describes a 2017 NAICS-based list;
  ASEC 2026 describes 2022. IPUMS INDLY prose and UH source pages are not fully
  synchronized. Source documentation alone does not prove the harmonized
  delivered IND/INDLY values preserve that source scheme.
- Installed Polars 2.0.0 supports collect_batches(chunk_size=16384,
  maintain_order=True, lazy=True, engine='streaming'). DataFrame.equals permits
  equivalent values with different dtypes: explicitly compare ordered schemas.
  Its iterator exposes no public stop/close method in this installed version.
  Drain on an ordinary mismatch; do not invent cancellation methods.

## File map and ownership

| File | Responsibility |
| --- | --- |
| src/embedding_data/ipums_conversion.py | Shared temporary decompression, source scan, atomic conversion and verified offline recovery |
| src/embedding_data/acs_benchmark_extract.py; cps_benchmark_extract.py | Preserve converter wrappers; expose --convert-only before credential/client handling |
| src/embedding_data/ipums_ddi.py | Pure definition/DDI metadata parsing and variable/sample contracts |
| src/embedding_data/ipums_parity.py | Ordered typed raw-CSV/Parquet comparison with bounded batches |
| src/embedding_data/ipums_references.py | Explicit immutable public snapshots/import and strict reference parsers |
| src/embedding_data/ipums_acceptance.py | V4/V5 observed sample, universe, variable/flag/replicate diagnostics |
| src/embedding_data/ipums_weights.py | CSV lexical weight diagnostics and explicit interpretation records |
| src/embedding_data/ipums_industry.py | V6 field/year code inventories and official-list comparison |
| src/embedding_data/ipums_totals.py | V7/V10 comparable ACS/CPS totals and signed gaps |
| src/embedding_data/ipums_verification_run.py | Selection, input/software provenance, orchestration, verification and replay |
| src/embedding_data/ipums_cli.py; cli.py | Public-reference and offline verification commands |
| tests/ipums_fixtures.py | Synthetic delivery definitions/DDI/CSV and tiny public-source fixtures |
| tests/test_ipums_conversion.py; existing ACS/CPS tests | Atomic/recovery and preserved normal invocation behavior |
| tests/test_ipums_ddi.py; test_ipums_parity.py | Metadata contracts and ordered typed fidelity failures |
| tests/test_ipums_references.py | Public parser/transport/import and immutable-cache contracts |
| tests/test_ipums_acceptance.py; test_ipums_weights.py | Complete acceptance and documented storage diagnostics |
| tests/test_ipums_industry.py; test_ipums_totals.py | Scheme ambiguity and handwritten comparator arithmetic |
| tests/test_ipums_verification_run.py; test_ipums_cli.py | Full synthetic run/replay, mutation refusal and CLI isolation |
| specs/findings/stage-7-ipums-extract-verification.md | Actual evidence, adopted rules, limitations and pins |
| README.md; CLAUDE.md; source spec; deferred items; this plan; roadmap | Shipped interfaces and completion handoff |

Workers own only their task's files. They are not alone in the codebase and must
preserve other edits. Execute Tasks 1–7 in order, with a task-scoped review gate
after each. Use using-git-worktrees at execution entry; this planning session
does not create a worktree. Always pass the real data root explicitly for
production commands in a worktree.

## Durable test strategy

Use develop-testing-strategy before implementing tests, and clean-code /
clean-coder before Python edits. The invariants below are the durable test plan.
Mock only HTTP, clocks and deliberately injected write failures; run real XML,
CSV, Polars, workbook, manifest and inventory code on synthetic inputs. No
production microdata or extracts are copied into tests. Public-source fixtures
must be tiny synthetic layouts or bounded public metadata excerpts.

| Invariant | Cheapest falsifying test / fixture | Task |
| --- | --- | --- |
| Failed conversion cannot publish a final, overwrite an existing file, or leak temporary files | Tiny gzip plus sink failure; existing final/partial/symlink | 1 |
| Recovery does not read .env or call any IPUMS method; selected sets only; existing outputs stay byte/mtime identical | Complete manifested synthetic triple, missing output, patched boundaries that raise | 1 |
| Legacy version stays unknown; requested/automatic names, DDI exponent and labels stay distinct | Tiny namespace-qualified DDI and definition JSON | 2 |
| Ordered schema, order, multiplicity and all values match independent CSV and Parquet paths | Unequal batch boundaries; swapped rows; duplicate loss; trailing row; dtype mismatch; nulls | 2 |
| Public source identity, period, units and required columns cannot silently drift | Official-layout workbook/JSON/HTML fixtures; one mutation each | 3 |
| Cache/import refuses unmanifested, changed, missing, incomplete or wrong-identity originals | MockTransport and manifest/hash mutations | 3 |
| Requested sample membership, universe and complete replicate expansion are checked against observed records | Small ACS/CPS frames including an absent month and missing flag | 4 |
| Fixed-width implied decimals do not cause CSV double division; all weight families are inventoried | CSV weights with actual decimal points, zero, negative replicate and helper REPWTP | 5 |
| Scheme ambiguity and source/harmonized uncertainty remain explicit | Shared code, 2017-only code, 2022-only code, NIU and malformed/outside code | 5 |
| Units, civilian universes and annual averaging are correct; gaps are not normalized away | Hand-calculated two-year/two-state ACS and two-month CPS totals | 5 |
| Offline run/replay uses only pinned selected inputs; mutation/missing/extra outputs fail verification | Full synthetic data root, network/client methods that raise | 6 |
| Fixture success cannot satisfy a production finding | Explicit actual-five-delivery checklist and independent reconciliation | 7 |

All new tests are ordinary offline tests; no new marker or live canary.
Preserve the existing unknown-marker error and default network exclusion.
The complete repository checks are:

~~~bash
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked pytest
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked behave
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked ruff check .
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv lock --offline --check
~~~

## Milestones

- M1, Tasks 1–2: missing conversions recover offline; exact typed fidelity and
  metadata contracts have synthetic failure tests.
- M2, Tasks 3–5: public evidence is versioned and pure measurements have
  handwritten expected results.
- M3, Task 6: a full synthetic run and replay pass with the network blocked.
- M4, Task 7: actual five-delivery evidence, public comparators, independent
  reconciliation, adopted finding, final review and completion protocol.

Do not label a milestone complete from a code review alone. Record the commands,
results and deviations in the execution ledger; run verification-before-completion
before claiming a gate passed.

### Task 1: Atomic conversion and explicit offline recovery

**Files:** Create ipums_conversion.py and test_ipums_conversion.py; modify the
two extract modules and their tests. Keep ipums_delivery.deliver unchanged.

**Interfaces:**

- decompressed_csv(csv_gz: Path, directory: Path) -> ContextManager[Path] owns a
  TemporaryDirectory under the supplied derived directory and removes it.
- scan_delivered_csv(csv_path: Path, source: str) -> pl.LazyFrame reproduces
  the existing source scanner, overrides, inference window and CPS zero-padding.
  Keep source overrides/constants in this module and re-export them from the
  existing modules if their tests/importers need the names; avoid circular imports.
- convert(csv_gz: Path, parquet_path: Path, source: str) -> Path never changes
  an existing final or pre-existing partial.
- recover(data_dir: Path, source: str, sets: list[str]) -> list[Path] verifies
  every selected complete delivery triple before writing missing outputs.

- [ ] **Step 1: Write failing observable recovery and atomicity tests.**

  Create synthetic gzip data, matching XML/definition, and three real manifest
  entries in tmp_path. Include both source types and a second selected set.
  Use the real conversion path. One CLI test must set DOTENV_PATH to a file
  whose loader raises and patch IpumsApiClient to raise on construction.

  ~~~python
  result = cli_runner.invoke(
      module.app, [set_name, '--convert-only', '--data-dir', str(tmp_path)]
  )
  assert result.exit_code == 0, result.output
  assert pl.read_parquet(output).to_dicts() == expected
  before = (output.read_bytes(), output.stat().st_mtime_ns)
  result = cli_runner.invoke(
      module.app, [set_name, '--convert-only', '--data-dir', str(tmp_path)]
  )
  assert result.exit_code == 0, result.output
  assert (output.read_bytes(), output.stat().st_mtime_ns) == before
  ~~~

  The fixture supplies module, set_name, output and handwritten expected rows.
  Also test a raw hash mismatch, missing XML, unrecorded definition, symlink,
  existing partial, no complete delivery, another set, and an interrupted raw
  delivery ending in .part. Interrupted directories are never converted;
  whole-tree audit reports them separately.

- [ ] **Step 2: Run the new tests red.**

  Run pytest tests/test_ipums_conversion.py and the two extract test modules
  with the offline locked prefix above. Expected: unsupported --convert-only
  or missing shared conversion behavior; preserve the actual failure output.

- [ ] **Step 3: Implement the shared conversion/recovery and CLI branch.**

  Decompress in a caller-owned temporary directory. Acquire the derived
  <name>.parquet.part path with exclusive creation before sinking. Installed
  Polars 2.0.0 accepts that binary handle and leaves its lifetime to the caller;
  a synthetic planning check confirmed this behavior. The publication core is:

  ~~~python
  def publish_parquet(frame: pl.LazyFrame, destination: Path) -> Path:
      partial = destination.with_name(destination.name + '.part')
      if destination.exists() or destination.is_symlink():
          raise FileExistsError(destination)
      stream = partial.open('xb')
      try:
          with stream:
              frame.sink_parquet(stream, maintain_order=True, lazy=False)
          pl.scan_parquet(partial).select(pl.len()).collect()
          os.link(partial, destination)
      finally:
          partial.unlink(missing_ok=True)
      return destination
  ~~~

  Import os, Path and Polars in the module. Safe-path and destination-parent
  preflight runs before this helper; the exclusive open is outside the cleanup
  try so this invocation never removes somebody else's partial. os.link refuses
  an occupied final atomically. Do not use replace on a possibly occupied final.
  Preserve the same ordered schema and values as the existing conversion.

  Discover only immediate raw/<source>/<set>/<collection>_<digits>/ deliveries.
  Verify safe paths, the three expected files and their collection/extract/sample
  manifest identity. Preflight all selected deliveries before converting any.
  Do not use a recursive glob that admits interrupted downloads.

  The CLI branch runs after set-name validation and before credential handling:

  ~~~python
  if convert_only:
      if dry_run:
          raise typer.BadParameter('--convert-only cannot be combined with --dry-run')
      for parquet in ipums_conversion.recover(data_dir, 'acs', extracts):
          typer.echo(f'wrote {parquet}')
      return
  ~~~

  Use source='cps' in CPS. A nondefault CPS --start with --convert-only is
  rejected as an inapplicable acquisition filter; do not silently reinterpret
  an existing delivery as a narrower extract. Preserve existing defaults and
  normal new-submission behavior. Keep existing csv_to_parquet wrappers calling
  the shared converter, preserving callers and indentation.

- [ ] **Step 4: Run green and record M1 recovery evidence.**

  Run the new tests, existing ACS/CPS/property tests, and ruff. A synthetic
  failure after writing partial bytes must leave neither a new final nor an
  owned staging path. Existing final/raw/other-set byte hashes stay unchanged.

- [ ] **Step 5: Commit the focused change.**

  Commit message: fix(ipums): recover missing conversions without resubmission.
  List the exact modified files in git add; do not include production data.

### Task 2: Delivery metadata and full ordered conversion fidelity

**Files:** Create ipums_ddi.py, ipums_parity.py, tests/ipums_fixtures.py,
test_ipums_ddi.py and test_ipums_parity.py. Reuse Task 1's scanner/decompression.

**Interfaces:**

- read_definition(file: Path) -> dict validates collection, sample keys,
  variable keys, CSV format, quality flags and case selections. Preserve
  nullable API version rather than infer it.
- read_ddi(file: Path) -> dict returns ordered variables, per-variable label,
  implied_decimals, categories, instructions, study/time notes and dataset
  citation/version. Use ElementTree and namespace-aware element names.
- compare_ordered(expected: pl.LazyFrame, actual: pl.LazyFrame,
  *, chunk_size: int = 16384) -> dict returns schema_equal, values_equal,
  expected_rows and actual_rows; never returns records or offending person IDs.
- verify_conversion(csv_gz: Path, parquet: Path, source: str,
  temporary_directory: Path) -> dict builds an independent expected CSV scan
  and compares it with the existing Parquet.

- [ ] **Step 1: Write failing DDI, legacy-version and parity tests.**

  Include a generic SAMPLE dictionary containing more samples than delivered,
  quality flags at extract and variable levels, helper REPWTP plus expanded
  names, dcml values 0/2/4, string codes and a null API version.
  For parity use an independently written Parquet rather than creating both
  sides with the converter under test.

  ~~~python
  expected = pl.DataFrame({'code': ['0001', '0001', None], 'weight': [1.25, 2.5, 0.0]})
  actual = pl.DataFrame({'code': ['0001', '0001', None], 'weight': [1.25, 2.5, 0.0]})
  report = compare_ordered(expected.lazy(), actual.lazy(), chunk_size=2)
  assert report == {
      'schema_equal': True, 'values_equal': True, 'expected_rows': 3, 'actual_rows': 3
  }
  changed_type = actual.with_columns(pl.col('weight').cast(pl.Int64))
  assert not compare_ordered(expected.lazy(), changed_type.lazy())['schema_equal']
  ~~~

  Add swapped unequal rows, duplicate loss, trailing rows, unequal batch
  boundaries, empty batches, nulls, float differences and a column-order
  difference. Test ACS alphanumeric preservation and CPS pre-cast zero-padding.

- [ ] **Step 2: Run the targeted tests red.**

  Expected missing modules/functions. No test reads the real data tree.

- [ ] **Step 3: Implement metadata parsing and the bounded comparison.**

  Reject duplicate DDI variable names/category values, malformed exponents,
  non-CSV definitions, unsupported sources and missing required metadata.
  An absent API version is allowed and recorded as unknown; absent required
  names are diagnostics/failures at Task 4, not silently filled metadata.

  Compare ordered list(schema.items()) first. With equal schemas, collect
  independent ordered batches with the installed Polars options recorded
  above. Hold one current frame and offset per iterator; compare slices of
  min(left_remaining, right_remaining), advance the consumed side(s), and
  count total rows. Ordinary mismatch sets values_equal=False but drains both
  iterators before deleting the temporary CSV. Unequal EOF fails. Never join,
  sort or collect a whole delivery. Do not cast the actual Parquet to hide a
  mismatch. On schema mismatch, count each stream separately without claiming
  value parity.

  This proves typed logical order/multiplicity/value fidelity. It does not
  prove physical Parquet byte equality or IEEE NaN payload/signed-zero identity.
  Pin Polars through the lock and software inventory because collect_batches
  is an unstable API. Chunk size bounds application-held rows, not all scanner
  buffers or process memory.

- [ ] **Step 4: Run green and record M1 metadata/parity evidence.**

  Run the Task 1–2 tests and ruff. Confirm a dtype-only mutation fails even
  where DataFrame.equals would accept equivalent numeric values.

- [ ] **Step 5: Commit.**

  Commit message: feat(ipums): verify delivery metadata and ordered conversion fidelity.

### Task 3: Immutable public evidence and strict parsers

**Files:** Create ipums_references.py and test_ipums_references.py; add small
public-layout fixtures to tests/ipums_fixtures.py or tests/fixtures/ipums/.

**Interfaces:**

- acquire(data_dir: Path, reference_id: str) -> Path downloads only registered
  public sources into a new snapshot, validates them, and manifests originals.
- import_reference(data_dir: Path, reference_id: str, kind: str,
  original: Path) -> Path supports blocked public downloads without changing
  source identity; import time is explicitly a proxy.
- check_references(data_dir: Path, reference_id: str) -> dict verifies a
  completed receipt and each cited original; no network or implicit refresh.
- parse_sample_catalog(file: Path) -> dict[str, str].
- parse_industry_list(file: Path, vintage: int) -> pl.DataFrame returns
  code:String, title:String; preserve code/title/vintage identity.
- parse_acs_levels(file: Path, year: int) -> pl.DataFrame returns
  year:Int64, state_fips:String, published:Float64, units:String.
- parse_bls_levels(file: Path) -> pl.DataFrame returns
  year:Int64, month:Int64, published:Float64, units:String and source footnotes.

Registered primary-source identities:

| Kind | Official URL / acquisition |
| --- | --- |
| usa_samples | https://usa.ipums.org/usa-action/samples/sample_ids |
| census_industry_2017 | https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2017-industry-code-list-with-crosswalk.xlsx |
| census_industry_2022 | https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2022-Census-Industry-Code-List-with-Crosswalk.xlsx |
| acs_2023_employment | https://api.census.gov/data/2023/acs/acs1?get=NAME,B23025_004E&for=state:* |
| acs_2024_employment | https://api.census.gov/data/2024/acs/acs1?get=NAME,B23025_004E&for=state:* |
| cps_employment | POST https://api.bls.gov/publicAPI/v1/timeseries/data/ with the exact JSON body below |
| bls_series_metadata | https://download.bls.gov/pub/time.series/ln/ln.series |
| bls_a1_metadata | https://www.bls.gov/news.release/empsit.t01.htm |
| asec_2025_documentation | https://www2.census.gov/programs-surveys/cps/techdocs/cpsmar25.pdf |
| asec_2026_documentation | https://www2.census.gov/programs-surveys/cps/techdocs/cpsmar26.pdf |

~~~json
{"seriesid":["LNU02000000"],"startyear":"2025","endyear":"2026"}
~~~

Freeze the POST request bytes alongside its response, URL, method and retrieval
time; the raw manifest source_url alone cannot describe a POST. No registration
key is sent. The v1 response does not carry descriptive units; verify
LNU02000000 and its NSA status against the frozen series metadata, and
thousands-of-persons / civilian age-16+ interpretation against frozen A-1
metadata. If the service refuses, returns incomplete years or its public
limits change, stop and report the actual response. Do not substitute an
unverified GET query. A bounded download/import from the official BLS ln bulk
directory is an alternative only with its full source/vintage/units recorded.

Also snapshot the public metadata pages needed to interpret accepted variables,
storage and source schemes. Keep a closed registry of explicit URL identities:
USA PERWT, REPWTP and the B23025 group metadata; CPS WTFINL, EARNWT, LNKFW1MWT,
ASECWT, REPWTP, IND, INDLY, UH_IND_A10, UH_INDLYR_A10, EMPSAME and ACTSAME.
Their source locations are in the evidence appendix below. No authenticated
page or IPUMS microdata endpoint is a fallback.

- [ ] **Step 1: Inspect public layouts, then write failing parser/cache tests.**

  Before defining workbook/parser fixtures, inspect the actual registered
  public originals in task-owned temporary storage. This public-only preflight
  does not touch raw/ or call an IPUMS API; save the URLs/hashes/observed sheet
  and header identities in the ledger. Use these observed layouts for fixtures,
  rather than guessing a workbook header. If a source cannot be inspected,
  stop that parser task with the actual access failure; do not invent a layout.

  Use a sample-ID HTML table, a two-row JSON Census response, a BLS response
  with REQUEST_SUCCEEDED plus units checked against series documentation, and
  tiny official-layout 2017/2022 workbook sheets. Mutate required headers,
  duplicate code labels, an invalid state, wrong year, M13 annual averages,
  unexpected series ID, failed status, HTML masquerading as a workbook and
  missing selected months. Preserve legitimate footnotes rather than drop them.

- [ ] **Step 2: Run tests red, then implement strict parse contracts.**

  Use Step 1's verified public workbook headers as parser anchors.
  Keep the original full Census lists distinct from ACS PUMS lists;
  identify the code/title columns by verified headers and sheet identity,
  not first-two-columns guessing. Retain only supported four-character Census
  industry leaves and documented special codes in separate metadata. Refuse
  conflicting duplicate labels or a vintage mismatch.

  ACS levels must be nonnegative finite numbers for 50 states plus DC;
  explicitly retain/report any PR row but exclude it from the comparison.
  BLS levels must name the requested NSA series and monthly periods, with
  source units of thousands. Do not fabricate the missing October 2025.

- [ ] **Step 3: Implement explicit acquisition/import and receipts.**

  Use httpx with sequential requests, browser user agent where needed, bounded
  timeout and no blind retries. Write downloaded bytes to exclusively owned
  partials, validate public identities before publication, and append verified
  manifest entries. A completed snapshot has a receipt listing the exact
  originals, request bodies, URLs, hashes, sizes, retrieval times and parser
  version. Exclude the receipt from its own inventory.

  Cached complete snapshots are checked without contacting a service. Occupied
  incomplete snapshots, unmanifested files, changed cached bytes, missing
  recorded files and symlinks fail before acquisition. Do not silently replace
  references at the same path when a public URL changes.

  The PDF originals are documentary evidence. Do not add a runtime PDF parsing
  dependency. Verify their bytes and record inspected appendix/page references
  in the finding; use the pdf skill when inspecting them during execution.

- [ ] **Step 4: Run green and commit.**

  Run test_ipums_references.py and existing manifest/audit tests. MockTransport
  must cover the POST body and a recorded successful response. Cached replay
  must work with make_client patched to raise.
  Commit message: feat(ipums): freeze official verification reference snapshots.

### Task 4: V4/V5 acceptance and observed extract composition

**Files:** Create ipums_acceptance.py and test_ipums_acceptance.py.

**Interfaces:** measure_acceptance(definition: dict, ddi: dict,
frame: pl.LazyFrame, source: str, set_name: str, sample_catalog: dict) -> dict
returns named aggregate frames and a JSON status record. It accepts Task 2's
parsed metadata and Task 3's public catalog, never makes an HTTP call.

- [ ] **Step 1: Write failing acceptance tests with explicit expected sets.**

  Cover all five source/set profiles. Exact replicate names are:

  ~~~python
  acs_replicates = {f'REPWTP{number}' for number in range(1, 81)}
  asec_replicates = {f'REPWTP{number}' for number in range(1, 161)}
  assert 'REPWTP' not in acs_replicates | asec_replicates
  ~~~

  Missing REPWTP80 or REPWTP160 and an extra out-of-range replicate must fail
  completeness. A generic DDI category for an absent sample must not satisfy
  observed sample membership. A missing requested REGION or CLASSWLY fails;
  missing automatic QMIGRAT1 is retained as missing coverage, not a successful
  allocation check. Include nontrivial quality-flag values stored as strings.

- [ ] **Step 2: Run tests red and implement the aggregate acceptance checks.**

  Compare definition requested names, DDI names, raw header and actual Parquet
  ordered schema. Record required detailed variables, actual Q flags and
  inflation-adjusted wage additions. Parent REPWTP does not satisfy expansion.
  Never claim an unknown earlier rejected request did not happen; the finding
  says which submitted requests are evidenced by these deliveries.

  Report row counts by extract, observed year/month and, for ACS, SAMPLE and
  MULTYEAR. Require the requested ACS sample IDs/labels and observed SAMPLE
  values to agree with the pinned catalog and relevant study notes. For CPS
  reconcile requested sample months with observed YEAR/MONTH and DDI time
  metadata, keeping monthly and ASEC separate. Report absent months explicitly.

  Verify ACS general EMPSTAT=1 and monthly LABFORCE=2 delivery selections.
  ASEC has no case selection. Unexpected values are errors or unresolved
  diagnostics requiring explicit disposition, never silently filtered before
  acceptance. Inventory automatic flags per sample/year, preserving unknown
  applicability. Inspect QMIGRAT1 lexical/category frequency aggregates without
  modifying source types or creating replacement observations.

  Produce these bounded artifacts, with exact ordered schemas recorded in
  their inventories:
  variable_inventory.parquet, sample_counts.parquet, flag_coverage.parquet.
  Include extract/source/set keys in each. No person identifier is an output.

- [ ] **Step 3: Run green and commit.**

  Run test_ipums_acceptance.py and Task 2's tests.
  Commit message: feat(ipums): measure accepted variables and delivered sample composition.

### Task 5: Weight storage, ASEC schemes and comparable employment totals

**Files:** Create ipums_weights.py, ipums_industry.py, ipums_totals.py and
their three test modules. Keep these pure measurement units separate.

**Interfaces:**

- measure_weights(csv_path: Path, ddi: dict, source: str,
  set_name: str) -> tuple[pl.DataFrame, dict] returns aggregate lexical/numeric
  storage diagnostics and an interpretation-evidence record.
- industry_frequencies(frame: pl.LazyFrame, ddi: dict,
  lists: dict[int, pl.DataFrame]) -> pl.DataFrame groups ASEC IND/INDLY
  separately by YEAR and joins official list membership/labels.
- acs_employment(frame: pl.LazyFrame) -> pl.DataFrame returns annual
  civilian-employed resident counts weighted with PERWT by STATEFIP.
- cps_employment(frame: pl.LazyFrame) -> pl.DataFrame returns monthly
  civilian-employed counts weighted with WTFINL.
- compare_levels(measured: pl.DataFrame, published: pl.DataFrame,
  keys: list[str]) -> pl.DataFrame returns matched levels, signed absolute gap,
  signed relative gap and explicit unmatched rows.

  The employment input frames use the raw-CSV measurement scan with weight
  columns parsed as exact Decimal values after lexical precision is established.
  Other columns retain the verified source interpretation. This is separate
  from Task 2's original-converter scan, which must preserve the historical
  Parquet dtypes for parity.

- [ ] **Step 1: Write failing storage and scheme tests.**

  Use raw lexical CSV fixtures with 123.4500 and 0.0000 under dcml=4;
  an integer ACS replicate under dcml=0; helper REPWTP; an automatic household
  weight; and a negative ASEC replicate. Expected values stay 123.45 and 0,
  not 0.012345 and 0. Negative replicate support is reported, not rejected.
  An undocumented sentinel-like large value is reported as unexplained rather
  than discarded.

  For industry use two small lists with one shared code and one exclusive code
  each. Include documented NIU, an outside code and 2025/2026 observations.
  Exact membership outcomes must stay distinct:

  ~~~python
  codes_2017, codes_2022 = {'1110', '2220'}, {'1110', '3330'}
  assert '1110' in codes_2017 & codes_2022
  assert '2220' in codes_2017 - codes_2022
  assert '3330' in codes_2022 - codes_2017
  ~~~

  A shared code alone yields an ambiguous membership verdict. A code in neither
  list remains outside, separate from documented NIU; do not pad or reinterpret
  malformed values into valid codes. Preserve the original delivered code and
  source dictionary meaning.

- [ ] **Step 2: Write failing handwritten totals tests.**

  ACS fixture: state 01 civilian employment 100 in 2023 and 140 in 2024,
  plus military weight 900 and an under-16 record. Annual outputs are 100/140;
  the two-year annual average is 120. Include EMPSTATD 10, 11 and 12 as
  civilian categories; 13/14/15 are military. Require AGE>=16 and EMPSTAT=1.
  Preserve an unexpected category as a diagnostic.

  CPS fixture: employed EMPSTAT 10/12, AGE>=16, weights summing to 2000;
  unemployed EMPSTAT 20 and military EMPSTAT 1 do not enter. A published
  LNU02000000 value of 1.9 thousand becomes 1900 persons; expected signed gap
  is +100, relative gap 100/1900. Zero/missing published levels retain null
  relative gaps with an explicit reason, not infinity or a fabricated zero.

- [ ] **Step 3: Run all three test modules red.**

  Preserve missing-module or failed-contract evidence before implementation.

- [ ] **Step 4: Implement storage diagnostics and explicit scale evidence.**

  Scan weight columns as strings from raw CSV for counts with explicit decimal
  points, lexical precision, null/blank/non-numeric values and ranges; use
  lazy numeric scans for bounded summaries and totals. Record original DDI
  exponents separately. Compare raw numeric values with their existing
  Parquet equivalents through Task 2, covering every individual replicate.
  Also record totals under the documented alternative fixed-width factor
  10**(-implied_decimals), strictly as a diagnostic.

  The adopted rule is supported by raw representation, CSV-specific software
  evidence and appropriate totals, never selected by best benchmark fit.
  For reproducible reductions, parse raw numeric weight strings into Decimal
  with precision 38 and the observed maximum fractional precision per column;
  reject unsupported exponent notation or excess precision rather than round.
  Aggregate those exact values and cast only the final display estimates to
  Float64. This fixed-point representation changes no units and is unrelated
  to applying an implied-decimal divisor. Test equal totals across input order
  and batch boundaries. Do not sum binary Float64 weights and promise exact
  replay when parallel reduction order can change the low bits.
  Household weights and linkage/replicate weights lack a directly comparable
  published employment total in these universes; document that limit.
  Check their own lexical representation, design/universe documentation and
  consistency, without claiming WTFINL validates every weight family.
  Check all individual replicates; summarize their factor/dispersion by family
  while retaining per-variable results.

  Do not build CPS links, compute SEs or silently use EARNWT/ASECWT as
  cross-sectional monthly employment weights. No new weight column is written
  into existing Parquets. Publish weight_diagnostics.parquet and weight_rules.json.

- [ ] **Step 5: Implement scheme and totals measurements.**

  Publish industry_frequencies.parquet for IND and INDLY by ASEC YEAR, with
  frequencies, documented special status, each list's membership and label.
  Support an evidence matrix with documented source scheme, delivered
  harmonization evidence, discriminating-code support, overlap ambiguity and
  resulting native-vintage verdict. An out-of-2022 code signals Stage 11
  compatibility/concordance work; it is not resolved to a preferred candidate.

  Publish employment_comparisons.parquet with per-year ACS state levels,
  pooled annual-average levels and each delivered CPS monthly level.
  Include all allocatable records for comparable universes. State codes remain
  strings; PR/island scope is explicit. These are residence comparisons,
  independent of later workplace target eligibility.

  The core formulas are:

  ~~~python
  def employment_gaps(frame: pl.LazyFrame) -> pl.LazyFrame:
      return frame.with_columns(
          gap=pl.col('measured').sub(pl.col('published')),
      ).with_columns(
          relative_gap=pl.when(pl.col('published').is_not_null().and_(pl.col('published').ne(0)))
          .then(pl.col('gap').truediv(pl.col('published')))
          .otherwise(None)
      )
  ~~~

  Require explicit period/unit matching before this function. Preserve all
  unmatched observations and source footnotes. Keep BLS noncollection/missing
  October 2025 separate from zero and distinguish the mutable reference
  snapshot from the historical delivered extracts.

- [ ] **Step 6: Run green, document M2 evidence and commit.**

  Run the three new test modules, Tasks 2–4 tests and ruff.
  Commit message: feat(ipums): measure weight storage industry vintages and employment gaps.

### Task 6: Frozen offline run, verifier and complete synthetic replay

**Files:** Create ipums_verification_run.py, ipums_cli.py,
test_ipums_verification_run.py, test_ipums_cli.py; modify cli.py.

**Interfaces:**

- measure(data_dir: Path, run_id: str, reference_id: str,
  selection_file: Path) -> Path validates and freezes exact selected inputs,
  computes Task 2/4/5 outputs and atomically publishes a named run.
- verify_bundle(directory: Path, data_dir: Path, *,
  expected_outputs_sha256: str) -> dict validates the detached inventory,
  exact output set, schemas/rows, cited raw bytes, selected Parquet hashes and
  frozen software/dependency identity.
- compare_runs(first: Path, second: Path) -> dict compares the logical
  ordered aggregate outputs and interpretation results while keeping
  run-specific timestamps/physical inventory hashes separate.

CLI:

~~~text
embedding-data ipums acquire-references REFERENCE_ID --data-dir ROOT
embedding-data ipums import-reference REFERENCE_ID KIND ORIGINAL --data-dir ROOT
embedding-data ipums measure RUN_ID --references REFERENCE_ID --selection FILE --data-dir ROOT
embedding-data ipums verify RUN_ID --outputs-sha256 SHA256 --data-dir ROOT
embedding-data ipums compare-runs FIRST_ID SECOND_ID --data-dir ROOT
~~~

- [ ] **Step 1: Write the complete synthetic raw-to-report test red.**

  Seed all five profiles with tiny manifested definitions/DDI/gzip CSV,
  independently converted or deliberately corrupted Parquets and public
  references. No fixture-specific production bypass is allowed. Patch
  IPUMS client construction, dotenv loading and HTTP creation to raise during
  measure/verify/replay. Assert exact handwritten sample/variable/weight/
  scheme/totals results, not merely that files exist.

- [ ] **Step 2: Implement explicit selections and software provenance.**

  The selection file is an object mapping each exact source/set to its delivery
  ID and derived relative path. Require exactly the five selected profiles;
  reject duplicate/missing/extra profiles, traversal, symlinks and .part names.
  Use Task 1 safe path/provenance checks and target_io for staging/inventories.
  Record the selection file's bytes/hash, verified raw entries, Parquet
  bytes/schema/row counts and the completed reference receipt.

  inputs.json freezes all executing IPUMS verification/conversion/DDI/reference
  modules, shared path/manifest/inventory modules, CLI, pyproject/uv.lock,
  Python/dependency versions and git commit when available. File hashes remain
  the executing-code evidence even when the tree is uncommitted. Do not infer
  executing software merely from a repository commit label. Do not hash the
  whole mutable raw manifest as an all-future-input gate; reverify selected
  entries and permit unrelated legitimate appends.

- [ ] **Step 3: Implement bounded offline orchestration/publication.**

  Verify selected citations, source/derived hashes and metadata before
  measurement. Check full ordered CSV/Parquet fidelity for every delivery.
  An actual mismatch prevents an accepted bundle and names the failed
  delivery without printing rows; keep diagnostic staging for inspection.
  Do not overwrite or repair historical Parquets automatically.

  Produce the eight aggregate Parquets from Tasks 4–5, weight_rules.json,
  inputs.json and report.json. The eight Parquets are variable_inventory,
  sample_counts, flag_coverage, weight_diagnostics, industry_frequencies,
  employment_comparisons, conversion_parity and verification_checks.
  The last two summarize Task 2 and named gate outcomes. report.json records
  status and unresolved evidence; it may honestly be unresolved. outputs.json
  inventories the preceding eleven files and excludes itself. Print its
  detached SHA-256 after publication.

  Recheck selected raw/Parquet/reference/software hashes before final
  publication so a concurrent mutation cannot hide behind initial validation.
  An occupied final or staging name fails; a replay uses a fresh ID. Publish
  only aggregates, never temporary decompressed CSVs.

- [ ] **Step 4: Add mutation and CLI-isolation tests; run green.**

  Mutate one raw byte, existing Parquet, selected reference, software inventory,
  output schema, output count, output byte and detached checksum separately.
  Each verifier must fail. A new unrelated valid manifest append must pass.
  Extra/missing output files fail. Verify callbacks never require credentials
  and all CLI errors exit cleanly without microdata in tracebacks.
  Replay under identical inputs must equal the first run's ordered aggregate
  outputs. Different run metadata need not have equal physical hashes.

- [ ] **Step 5: Run the complete repository checks and commit.**

  Record M3 and fix regressions before proceeding.
  Commit message: feat(ipums): publish reproducible offline extract verification runs.

### Task 7: Measure the five deliveries, adopt findings and complete Stage 7

**Files:** Create specs/findings/stage-7-ipums-extract-verification.md; modify
README.md, CLAUDE.md, source spec, deferred items, roadmap and this plan only
after the evidence/review gates below. No production microdata enter git.

- [ ] **Step 1: Freeze the actual selection and before-state inventory.**

  Use /Users/lowell/Projects/embedding-data/data explicitly. Write a local
  gitignored selection JSON for the five delivery/path rows in Entry evidence.
  Record the 15 raw hashes, five existing Parquet hashes and the selected
  Stage 2–6 source/bundle pins before running anything. Run the whole-tree audit.
  Do not call acquisition or builders to make this check pass.

  Example production selection entry:

  ~~~json
  {"acs/core":{"delivery":"usa_00001","parquet":"derived/acs/core/usa_00001.parquet"}}
  ~~~

  The actual selection file must include all five profiles from the entry
  table, using the same shape; the one-entry example is intentionally not a
  runnable production selection.

- [ ] **Step 2: Acquire and inspect the actual public references.**

  Run acquire-references stage7_ipums_references_20261015 with the explicit
  root. The executor must inspect real workbook sheets/headers and metadata
  identities and update parser tests if the actual official layout differs.
  Preserve original bytes and record any transport/import limitations.
  Inspect the 2025/2026 ASEC documentation appendices and distinguish source
  coding from harmonization; consult classification-codes and bls-data-context.
  Every claimed source fact in the finding cites the frozen original and URL.

- [ ] **Step 3: Run production measurement and exact aggregate replay.**

  ~~~bash
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data ipums measure stage7_ipums_verification_20261015 --references stage7_ipums_references_20261015 --selection /Users/lowell/Projects/embedding-data/data/derived/ipums/stage7-selection.json --data-dir /Users/lowell/Projects/embedding-data/data
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data ipums measure stage7_ipums_verification_20261015_replay --references stage7_ipums_references_20261015 --selection /Users/lowell/Projects/embedding-data/data/derived/ipums/stage7-selection.json --data-dir /Users/lowell/Projects/embedding-data/data
  UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data ipums compare-runs stage7_ipums_verification_20261015 stage7_ipums_verification_20261015_replay --data-dir /Users/lowell/Projects/embedding-data/data
  ~~~

  Use fresh IDs if occupied; inspect existing runs rather than overwrite.
  Run each public verifier with its actual printed detached checksum and the
  explicit root. Report elapsed time and peak-memory observations if available;
  do not weaken full-file fidelity to a sample because the five-year file is
  large. Relevant software changes require new measured runs.

- [ ] **Step 4: Independently reconcile the actual aggregates.**

  Use a small independent local script/read-only analysis to reconcile raw and
  derived row totals, observed sample/month partitions, exact 80/160 replicate
  coverage, representative and all-family weight scaling summaries, ACS
  state/year employment and CPS monthly employment sums. Hand-inspect the
  aggregate discriminating-code lists against official workbook labels and
  source documentation; record inconclusive overlap explicitly.

  Re-run the audit and before-state hash checks. Raw originals, existing
  Parquets and Stage 2–6 selected artifacts must remain unchanged. The
  acquisition manifest may grow by exactly the new public originals.
  A successful fixture suite or matching two calls to the same flawed function
  is not this independent reconciliation.

- [ ] **Step 5: Write the measured finding and resolve adoption gates.**

  The finding contains:

  - actual selection, date, software/code/lock versions, detached input/output
    pins and the two public verifier/replay results;
  - V4 catalog identity and observed five-year SAMPLE/MULTYEAR composition;
  - V5 requested/accepted/automatic names, complete replicate ranges, flag
    coverage gaps and real delivered selection checks;
  - V6 current/last-year ASEC field/year verdicts with documented schemes,
    discriminating frequencies, overlap limits and required Stage 11 work;
  - V7 per-weight CSV/DDI/Parquet interpretation evidence, adopted numerical
    rule and exactly which universe/design comparisons were possible;
  - V10 every ACS state/year and pooled gap, every available monthly CPS gap,
    units, scope, footnotes, absent October and publication-vintage limits;
  - legacy API-version unknownness versus known citation/DDI/client versions;
  - actual QMIGRAT1 missing/type/domain findings and their downstream effect;
  - explicit limits: no target, no linkage rate/job-change flow, no causal or
    accuracy inference from coverage, no completed V11 parser or V12 family.

  Batch any unresolved owner decisions into one review request backed by the
  concrete measurements. If source/harmonized-vintage evidence or a required
  storage rule remains unresolved, keep its marker and Stage 7 open. Do not
  label an unknown vintage verified merely to close the stage.

  If V4/V5 proves an extract definition is incorrect, add the smallest
  source-definition correction with a failing offline definition test and
  rerun its checks. Preserve all existing deliveries. A correction that needs
  a replacement real delivery is an owner decision backed by the measured
  missing evidence; do not resubmit automatically or mark the corrected
  definition as accepted before delivery evidence exists.

- [ ] **Step 6: Apply evidence-backed source-spec and command documentation.**

  Replace only the five Stage 7 open-marker clauses with verified markers that
  cite the finding and the specific measured result. Keep their surrounding
  behavioral requirements. Update XA/XC standing to cite actual delivered
  verification evidence; distinguish it from the 2026-10-12 submission date.
  Rollout records that the measured deliveries were checked, without claiming
  planned ACS/CPS transformations exist.

  If V6 establishes a field/year source scheme other than the unqualified
  2022 assumption in R4.6, the proposed exact R4.6 replacement is:

  > IPUMS CPS carries Census codes, not NAICS or SOC strings. Store IND, OCC,
  > INDLY, and OCCLY as zero-padded four-character strings. Monthly IND from
  > January 2025 uses the 2022 Census industry list. ASEC IND and INDLY use
  > the field- and year-specific schemes verified in
  > specs/findings/stage-7-ipums-extract-verification.md; map each native
  > scheme through its official Census list and retain any required R5.4
  > vintage concordance as flagged candidate sets. Occupation maps through
  > the 2018 Census occupation list. Do not reuse the IPUMS USA
  > IND-to-INDNAICS crosswalk for CPS codes: it reflects ACS PUMS codes,
  > which differ slightly from the full Census lists.

  Tag that amendment (owner, plan 7, actual approval date) only after approval;
  record the owner decision in this plan. Do not apply it without the measured
  matrix. Resolve any contradictory requirement through the same gate.

  README documents --convert-only, explicit public acquisition/import,
  offline measure/verify/replay, storage/vintage limits and the finding.
  CLAUDE documents actual reusable interfaces. Tick convert-if-absent in the
  deferred backlog only when its tests/behavior satisfy Done when. Close the
  legacy-version item with the verified nullable-reader contract and a pointer
  to this plan; never by rewriting immutable definitions.

- [ ] **Step 7: Final checks, whole-branch review and completion protocol.**

  Run all repository checks from the test strategy; resolve final review
  findings using receiving-code-review. Use requesting-code-review for the
  final whole-branch review. Check both software and actual measured gates.

  Then run writing-plans' Plan Completion Protocol before branch integration:
  resolve-before-defer; mark only executed steps; record deviations; tick
  closed earlier backlog items; add self-contained new deferrals if needed;
  record backlog health; retire this plan in one chore(specs): retire plan 7
  commit. The shared source spec remains live and is not retired.

  Add the actual Handoff to later stages and tick/stamp Stage 7 only once
  software checks, measured finding and adoption gates are resolved.
  Revalidate Stages 8–13 in that Handoff:

  - Stage 8 consumes verified ACS profiles, exact sample/variable/flag schemas
    and code/string/type traps; missing flags remain unavailable evidence.
  - Stage 9 consumes explicit CSV weight interpretation and comparable ACS
    totals universes; verification does not supply estimation/allocation helpers.
  - Stage 10 inherits no new ITA behavior; earlier immutable contracts stand.
  - Stage 11 consumes the ASEC field/year scheme matrix, full official Census
    references, their APIs/pins, monthly gap and DDI guard/weight semantics.
    Identify any necessary native-vintage concordance work without building it.
  - Stage 12 consumes verified current/ASEC variable and weight coverage through
    later helpers; no inherited claim of metro eligibility, linkage or SEs.
  - Stage 13 consumes reproducible evidence/pins, limits and the closed V4–V7/
    V10 portion; citations, comparators, V9 and full V12 remain its work.

  Include any traps/deviations/deferred items in the actual handoff bullets.
  Execution writes this Handoff; derive-roadmap amends later roadmap entries
  at the subsequent resume. If a stage must be added/split/reordered, surface
  one approve-or-amend question under derive-roadmap instead of silently changing
  the partition.

  Finish using finishing-a-development-branch with the integration decision
  taken explicitly; remove the managed execution worktree when appropriate.
  End with "Next: resume the roadmap." Do not plan another stage here.

## Evidence appendix for execution

These are research leads verified during planning, not measured production
outcomes. Acquire immutable public snapshots before citing them as run inputs.

- [Public IPUMS sample IDs](https://usa.ipums.org/usa-action/samples/sample_ids)
  lists us2024c, 2020–2024 ACS 5-year.
- [USA PERWT](https://usa.ipums.org/usa-action/variables/PERWT) and
  [USA REPWTP](https://usa.ipums.org/usa-action/variables/REPWTP).
- [CPS weights](https://cps.ipums.org/cps/repwt.shtml),
  [WTFINL](https://cps.ipums.org/cps-action/variables/WTFINL),
  [LNKFW1MWT](https://cps.ipums.org/cps-action/variables/LNKFW1MWT),
  [EARNWT](https://cps.ipums.org/cps-action/variables/EARNWT),
  [ASECWT](https://cps.ipums.org/cps-action/variables/ASECWT),
  [REPWTP](https://cps.ipums.org/cps-action/variables/REPWTP).
- [IND](https://cps.ipums.org/cps-action/variables/IND),
  [INDLY](https://cps.ipums.org/cps-action/variables/INDLY),
  [ASEC current source](https://cps.ipums.org/cps-action/variables/UH_IND_A10),
  [ASEC last-year source](https://cps.ipums.org/cps-action/variables/UH_INDLYR_A10).
  A source-variable association alone does not establish harmonized coding.
- [2025 ASEC documentation](https://www2.census.gov/programs-surveys/cps/techdocs/cpsmar25.pdf),
  Appendix A, printed A-1 / PDF page 131; and
  [2026 ASEC documentation](https://www2.census.gov/programs-surveys/cps/techdocs/cpsmar26.pdf),
  Appendix A / PDF page 145. Reinspect actual frozen editions/page numbering.
- [EMPSAME](https://cps.ipums.org/cps-action/variables/EMPSAME),
  [ACTSAME](https://cps.ipums.org/cps-action/variables/ACTSAME) and
  [IPUMS staff explanation](https://forum.ipums.org/t/actsame-variable/6452)
  document guard/universe semantics. Stage 11 builds links and usable-pair
  shares; Stage 7 retains categories and relevant coverage evidence.
- [2023 B23025 metadata](https://api.census.gov/data/2023/acs/acs1/groups/B23025.html)
  and [2024 metadata](https://api.census.gov/data/2024/acs/acs1/groups/B23025.html):
  B23025_004E, civilian employed population age 16+.
- [BLS public API v1](https://www.bls.gov/developers/api_signature.htm),
  [BLS CPS series directory](https://download.bls.gov/pub/time.series/ln/) and
  [employment table A-1](https://www.bls.gov/news.release/empsit.t01.htm).
  The planning environment did not verify a successful live BLS API response.
- [COMPWT](https://cps.ipums.org/cps-action/variables/COMPWT) explains why the
  specified WTFINL comparison need not reproduce composite published levels.
- Installed ipumspy readers.py CSV handling documents already expanded CSV
  decimals. Use this as software evidence alongside delivered raw lexical
  diagnostics and matching totals, not as a substitute for V7.

## Self-review and execution handoff

Before presenting this plan, check coverage of every Stage 7 Spec/Produces/Exit
clause, the two Stage 7-targeted backlog items, every public identity, function
name/type and artifact count. Search for unresolved placeholders and fix them.
No Stage 7 completion box or verified marker is changed by planning.

Plan review settled the six defaults and the conditional R4.6 amendment wording
in D1. D2 selects a fresh execution session via subagent-driven-development:
conversion, metadata/parity, public evidence and the measurement units each
merit a separate focused review. Preserve the measured adoption gates in Task 7.

This plan is the zero-context execution handoff. No planning chat history,
uncommitted private note or task in another chat is required to execute it.
