# BEA input–output tables

> Next step: writing-plans in a fresh session against this file. Do not fetch
> any BEA file, and do not build, before the plan exists and the owner gives
> the go-ahead for each write.

Status: draft for owner review. Stage 15 design session of
[the roadmap](naics-evaluation-data-roadmap.md), 2026-11-23. The owner made the
four decisions below in this session. Calls marked "My call" were made while
writing this file. A builder check by a separate reviewer raised six questions
on 2026-11-23. One became owner decision 4. The other five are answered in
place as calls. No BEA file was fetched for this design. Facts come from
public HTML pages read on 2026-11-23, or are marked *unverified*.

## Scope and governing contracts

Stage 15 builds Source 1 of
[the evidence-sources spec](uncovered-uses-evidence-sources.md) (the Stage 2
spec) once on real data and verifies it. It serves two uses from one evidence
family, read from one BEA table in two directions:

- **O9, supply-chain dependency.** For each buying industry, the share of its
  intermediate inputs that comes from each commodity.
- **O10, look-alike prospecting.** For each commodity, the share of its
  intermediate use that goes to each buying industry.

The Stage 2 spec's "Rules for every new family" govern this stage. R5, R7.1,
R7.4, R8 and R9 of [the source spec](embedding-evaluation-data-spec.md) govern
codes, outputs, provenance, disclosure, leakage and offline operation. The TRI
spec ([completed](completed/tri-parent-links.md)) is the model for the bundle,
the commands, the preflight and the acceptance steps.

### Owner decisions (2026-11-23)

| # | Decision | Choice |
|---|---|---|
| 1 | What the bundle holds | **Direct shares only** (option A). Industry buyers are target rows. Final demand stays in a side table as published totals. No total-requirements table. |
| 2 | Table design | **Accepted as proposed** ("Nothing missing"). The 2017 detail Use table, before redefinitions, at producer prices. Three measures. Rows keyed by BEA code. NAICS 2022 candidate sets in a code table. Special codes and the diagonal kept and flagged. Missing statistics null and flagged. See [Use targets](#use-targets-o9-and-o10). |
| 3 | Build approach | **New BEA modules and a new contract module for published aggregates** (approach 1). See [Approaches](#approaches). |
| 4 | What passes E2 | **An explicit BEA statement, or else 17 U.S.C. § 105 with no BEA restriction.** See [the preflight](#preflight-open-checks-e1e3). |

### Out of scope

- A replay build, a full-data `compare-runs`, a long-form acceptance finding,
  and README and `CLAUDE.md` run pins. The roadmap does not stage these for
  BEA. The owner decides at the resume after this stage reports.
- A headline minimum count. BEA publishes no counts, and the family is
  non-headline (owner, 2026-11-16).
- Scoring, null models, data splits and acceptance thresholds: the family's
  protocol section, O19. The family is not scored until that section exists
  (protocol, "Families with no section").
- The R8.4 training-role amendment: a separate owner decision after
  naics-embedder's spec.
- Final-demand buyers as target rows, total-requirements tables, the Make or
  Supply table, after-redefinitions tables, purchaser-price tables, the
  supply-use framework tables, the summary (71) and underlying (138) annual
  tables, and any benchmark other than 2017.
- Any change to a frozen module, an earlier stage's artifact or a raw file.

## Intent

naics-embedder judges its industry-relatedness embedding on evidence families
that it never trained on. This repository has no evidence for supply-chain
dependency or look-alike prospecting. BEA's Use table records, for the whole
U.S. economy, how much of each commodity each industry buys. Two industries
are close in a supply chain when one buys much of the other's output. Two
industries look alike to a seller when they buy the same commodities. The
NAICS tree can place either pair far apart.

At naics-embedder `2b2029c` the methodology gives input–output families "no
role yet". This stage builds the evidence so that the family's protocol
section (O19) can assign it later.

### Goals

- One verified bundle of directed commodity → industry shares (O9 and O10),
  with each value as BEA publishes it.
- A code table that takes each BEA code to a NAICS 2022 candidate set through
  official concordances only.
- A published-aggregate contract that keeps the long-schema columns of R7.4
  and allows the null counts that R7.5 requires.
- A preflight that settles open checks E1–E3 before any data is trusted.

### Non-goals

- Firm-level links. BEA estimates are industry aggregates.
- Six-digit NAICS 2022 targets. A BEA code stays the unit.
- Any score, threshold or embedding comparison.

### Anti-goals

The design fails, even if it runs, when it:

- Splits a BEA value among NAICS codes, or writes any mapping from a BEA code
  to NAICS that BEA's concordance and the Stage 4 concordance do not give.
- Fills a standard error or a count that BEA does not publish.
- Derives a coefficient that needs a modeling assumption beyond a published
  value divided by a published total.
- Derives a relation from NAICS code structure.
- Edits `target_contract.py` or any other frozen module, or an earlier stage's
  artifact.
- Lets any table feed embedder training, curriculum, hard-negative mining or
  model selection (R8.4).

## What the design session found

Read on 2026-11-23 from public HTML pages. No BEA file was fetched.

1. **2017 is still the latest benchmark.** BEA's Input-Output Accounts page
   says detailed benchmark tables, "produced roughly every five years", have
   402 industries. Annual tables have 71
   ([BEA](https://www.bea.gov/data/industries/input-output-accounts-data)). No
   2022 benchmark release date was found.
2. **The annual detail is coarser.** Annual underlying detail tables have 138
   industries, not 402 *(unverified: search summary. BEA's
   [underlying estimates](https://www.bea.gov/node/22626) page, read directly,
   does not state it)*. If so, the 2017 benchmark is the only table near
   six-digit NAICS.
3. **Annual tables update each September.** The 2026 annual update has shipped
   ([iTable page](https://www.bea.gov/itable/input-output)). The 2017 detail
   values can change only in a comprehensive update.
4. **The concordance is one spreadsheet.** The iTable page links "BEA Industry
   and Commodity Codes and NAICS Concordance", at
   `https://www.bea.gov/sites/default/files/2023-10/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx`.
   Its 2023-10 path fits the 2017 benchmark, which follows NAICS 2017. Not
   opened.
5. **The table needed exists at detail.** BEA's old data page now says that
   "Make-Use-Import (Before Redefinitions)" tables "are now in BEA's
   Input-Output Interactive Data Application"
   ([migration note](https://www.bea.gov/industry/input-output-accounts-data)).
   A 2017 Use table before redefinitions at producer value with 402 industries
   is listed there *(unverified: search summary)*. USEPA's `useeior` reads a
   2017 detail table of this kind from BEA's static `AllTablesIO.zip`
   ([BEAData.R](https://rdrr.io/github/USEPA/useeior/src/data-raw/BEAData.R)).
   The exact file name and sheet layout are *unverified*. If E1 finds no such
   table at 402 industries, the stage stops for the owner.
6. **BEA asks for citation.** "Citations are appreciated and appropriate". A
   reference must not suggest that BEA endorses a product
   ([guidelines](https://www.bea.gov/help/guidelines-for-citing-bea)). No
   reuse restriction was found. E2 settles this.
7. **`targets-v1` cannot hold BEA rows.** `target_contract.validate_targets`
   refuses null `n_unweighted` and `n_weighted`. `target_contract.py` is in
   the hashed software of TRI, USAspending, Stage 6 and Stage 10, so an edit
   makes their `verify` refuse their selected runs.
8. **No new dependency.** `fastexcel` is already in `pyproject.toml`. Stage 4
   reads official workbooks with it. Tests already write XLSX fixtures with
   `zipfile` (`tests/code_fixtures.py`).
9. **Stage 4 holds what the code table needs.** `naics_native_nodes.parquet`
   holds the NAICS 2017 nodes (11,199 nodes over vintages 2002–2022).
   `naics_concordance.parquet` holds 1,150 official six-digit 2017→2022 rows:
   928 `1:1`, 5 `1:m`, 120 `m:1` and 97 `m:m`. `naics_nodes.parquet` holds the
   NAICS 2022 nodes. `naics_edges.parquet` covers NAICS 2022 only.
10. **V12 is tested per family.** Each family has its own V12 fixture test, for
    example `tests/test_tri_v12.py`. No shared test assumes `targets-v1` for
    every family, so BEA's V12 extension is a new test file.

## Approaches

| Approach | What it does | Trade-off | Decision |
|---|---|---|---|
| 1. New BEA modules and a published-aggregate contract | New `python -m embedding_data.bea_io_tables` command group. New `published_target_contract.py` keeps the `targets-v1` columns and allows null counts on flagged rows. | Leaves every frozen module unchanged. Keeps R7.4 as written. Readers accept one more schema version with the same columns. | **Chosen** (owner, 2026-11-23) |
| 2. Edit `target_contract.py` | One contract for all families. | Breaks `verify` for four selected families. Each needs a fresh run and new owner gates. | Rejected |
| 3. Wide matrices outside the long schema | Keeps BEA's own layout. | R7.4 needs another amendment. Readers lose the common row format. | Rejected |

## Selected inputs and trust boundary

### Inputs

| Input | Identity | Use |
|---|---|---|
| BEA detail Use table | 2017 benchmark, before redefinitions, producer value, 402 industries, one snapshot, manifest-recorded | Commodity → industry values and published totals |
| BEA concordance | "BEA Industry and Commodity Codes and NAICS Concordance", same snapshot, manifest-recorded | BEA code → NAICS 2017 codes, and code titles |
| Stage 4 codes bundle | `stage4_v11_20261013_r2`, detached `outputs.json` SHA-256 `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` | `naics_native_nodes.parquet` (NAICS 2017 nodes), `naics_concordance.parquet` (2017→2022 rows), `naics_nodes.parquet` (NAICS 2022 node IDs) |

If E1 finds that BEA publishes the 2017 detail Use table only inside a ZIP
archive, the raw file is the archive, and the build reads the one member that
E1 names. **My call.**

### Codes selection

**My call:** Stage 15 has its own codes selector, like TRI's. It checks the run
ID and pin syntax, authenticates the detached pin, verifies the bundle
inventory with `target_io.verify_inventory`, checks the schema version and run
identity, and reads the three Parquets named above. It reads no ITA data and
calls no Stage 10 or TRI selector.

### Reused interfaces

Stage 15 imports these and never edits them:

- `target_contract.TARGET_SCHEMA` and `TARGET_KEY_COLUMNS`, for the column
  list only. Stage 15 does not call `validate_targets` or `write_targets`.
- `target_io` (`stage`, `relative_file`, `file_record`, `inventory`,
  `verify_inventory`, `write_json`).
- `manifest` (`describe_file`, `append_entries`, `entry_for`, `sha256_file`).
- `paths`.
- The Stage 10 fixture helper that builds a real Stage 4 bundle
  (`tests/ita_establishment_fixtures.py`), for the V12 fixture.

### Frozen modules

Stage 6's `FROZEN_MODULES` and `TARGET_MODULES`, the Stage 7–9 software files,
the files in the selected Stage 10, Stage 17, TRI and USAspending bundles'
software lists, `cli.py` and `code_references.py` stay unchanged. So does any
test file that an earlier stage hashes. Stage 15 adds modules only. If the plan
finds that a reused function cannot serve unchanged, it stops and asks the
owner.

### What Stage 15 does not consume

- ITA data, IPUMS artifacts, the Stage 5 geography bundle, and the Stage 6,
  Stage 10, Stage 17, TRI and USAspending bundles.
- No upstream builder runs.

## Raw BEA files

### Acquisition and import

- `acquire --snapshot DATE` downloads the two files (network). It writes each
  file to `.part`, renames it only after its length matches `Content-Length`,
  then records it. It refuses a response with no `Content-Length`, as TRI's
  does. The plan's first task finds the exact URLs from BEA's pages. Each
  download needs the owner's go-ahead.
- `import-file KIND FILE --snapshot DATE` registers a file that the owner
  downloaded in a browser (offline). `KIND` is `use-detail` or `concordance`.
  Its `retrieved_at` is the import time, flagged as a proxy, as Stage 3 does
  for HUD.
- Both refuse an existing path. Raw files are never replaced.

### Layout and manifest

**My call:** `data/raw/bea/input-output/<snapshot>/<BEA file name>`. The
snapshot is the operator's acquisition date. A later download lands beside
the earlier one under its own date. The manifest entry records the source URL
(null for an import), retrieval time, SHA-256, size, client and version.
`through_date` stays null, because BEA states no "processed as of" date.

### Snapshot selection

`build` takes `--snapshot DATE`. It selects the one manifested Use table and the
one manifested concordance under that date. A missing or extra file fails the
build.

### Reading

- Sheets are read with `fastexcel` through Polars. Every cell is read as a
  string first. Codes stay strings (R9.1).
- A registry constant records the exact sheet name, the header rows, the code
  and title columns, and the codes of the total rows and columns, taken from
  E1. A changed layout fails the build.
- A value cell is a number, or the zero marker that E1 records. Any other text
  fails the build.
- The concordance's NAICS cells are parsed by the exact token forms that E1
  records, for example separators, partial markers or "n.a." text. A form
  not in the registry fails the build. **My call.**
- Values are dollars in millions, as published. They are stored as
  `Float64`. **My call.**

## Preflight: open checks E1–E3

The preflight runs after the two files are recorded and before any build. It
has two parts, as TRI's did. **My calls:**

- **Data checks.** A script, `scripts/preflight_bea.py`, reads only the
  manifested files and the pinned Stage 4 Parquets, offline, and prints a JSON
  report.
- **Document checks**, marked "(read)" below. The operator reads the named BEA
  pages and records the URL, the read date and a short quote in the findings
  file. These pages are not manifest-registered, because no build step reads
  them. Reading a BEA PDF needs the owner's go-ahead.

Each covered verdict holds only while these checks pass. A failed check stops
the stage. The owner then records O9 and O10 as uncovered or promotes a named
alternate, and the Stage 2 spec's verdict table is amended.

| Check | Measures and records | Stops the stage when |
|---|---|---|
| **E1** concordance and layout | The concordance's sheets, header row and NAICS edition. Its depth: NAICS codes by digit count. Its markers, if any, for partial membership. Its rows for special codes, and which have no NAICS member. NAICS codes listed under more than one BEA code. The Use table's sheet name, header rows, commodity and industry code lists, final-demand columns, value-added rows and total codes. The zero marker. Negative cells. For each commodity row and industry column, the gap between the published total and the sum of the published cells. Whether every Use table code is in the concordance. Whether every NAICS 2017 code in the concordance is in `naics_native_nodes.parquet`. | The concordance names a NAICS edition other than 2017. A concordance entry has a form other than a plain code or a plain code with a partial marker (see [Code table](#code-table)). A concordance NAICS code is not an official NAICS 2017 code. More than 5% of BEA codes have no NAICS member (**my call:** a trigger to ask the owner, not an acceptance threshold). The largest total gap exceeds the rounding bound of [Validation](#validation). No 2017 detail Use table before redefinitions at producer value with about 402 industries exists. |
| **E2** terms | BEA's reuse terms or public-domain statement for the tables and its date (read). Its citation guidance (read). Which basis passes E2: a BEA statement, or 17 U.S.C. § 105 (owner decision 4). | E2 passes on an explicit BEA reuse or public-domain statement. With none, it passes on 17 U.S.C. § 105, because BEA is a federal agency and its tables are U.S. government works, provided that no BEA statement restricts reuse (owner, 2026-11-23). It stops the stage when a BEA statement restricts publishing aggregates. A failed terms check never becomes "build it but keep the aggregates local" (Stage 2 rule). |
| **E3** 2022 benchmark | BEA's published schedule for the 2022 benchmark, if any (read). Whether any 2022 detail table has been released. | BEA has released 2022 detail Use tables. The owner then chooses between 2017 and 2022. **My call:** a scheduled but unreleased date is recorded and does not stop the stage. |

## Code table

`bea_io_codes.parquet`, one row per BEA detail code that appears in the Use
table as a commodity row or an industry column, sorted by `bea_code`:

| Column | Type | Meaning |
|---|---|---|
| `bea_code` | String | BEA detail code, as published |
| `title` | String | BEA's title, from the Use table's own label |
| `commodity_unit`, `industry_unit` | String | The `unit_a` and `unit_b` strings of [Target rows](#target-rows), or null where the code does not appear in that role |
| `is_commodity`, `is_industry` | Boolean | Where the code appears in the Use table |
| `naics_2017_published` | List(String) | The NAICS codes BEA's concordance lists, as published, sorted |
| `naics_2017_candidates` | List(String) | Six-digit NAICS 2017 national-industry node IDs, sorted |
| `naics_2022_candidates` | List(String) | NAICS 2022 national-industry node IDs from `naics_nodes.parquet`, sorted |
| `flags` | List(String) | Sorted, unique |

Rules:

- **My call:** the title comes from the Use table, so every code has one even
  if the concordance leaves it out. A Use table code that the concordance does
  not list gets empty candidate sets and the flags `not_in_concordance` and
  `no_naics_member`. It is expected data, such as a special code, not a
  failure. E1 lists these codes for the owner.
- **My call:** a concordance entry is parsed only in two forms: a plain NAICS
  code, or a plain NAICS code with the partial marker that E1 records. A range,
  an exclusion, a wildcard or any other form stops the stage at E1 for an
  owner decision, because expanding it would compute a set that BEA did not
  list. "n.a." or a blank, if E1 records it, means no member.
- A published six-digit code is its own NAICS 2017 candidate. A shorter code
  becomes the set of NAICS 2017 national industries whose node sits under it
  in `naics_native_nodes.parquet`. NAICS defines its own hierarchy by code
  prefix, so this is the official tree, not a mapping written here. **My
  call.** It is R5's parse of a mixed-depth code. It derives no relation.
- Each NAICS 2017 candidate goes to NAICS 2022 through the Stage 4
  2017→2022 rows. All targets are kept. Nothing is truncated or guessed.
- Flags: `no_naics_member` (empty published list), `naics_partial_member` (if
  E1 finds a partial marker), `naics_shared` (a NAICS 2017 code listed under
  more than one BEA code), `naics_expanded` (a published code shorter than six
  digits), `crosswalk_one_to_many`, `crosswalk_many_to_one` and
  `crosswalk_many_to_many` (from the Stage 4 link types `1:m`, `m:1` and `m:m`),
  `naics_2022_unmapped` (a NAICS 2017 candidate with no 2017→2022
  row).

## Use targets (O9 and O10)

### Estimand

Let `U(c,j)` be the published Use value of commodity `c` bought by industry
`j`, over the industry columns only. Let `T_c` be the published total
intermediate use of commodity `c` (its row total over industries). Let `T_j` be
the published total intermediate inputs of industry `j` (its column total over
commodities). Then:

- `input_share(c,j) = U(c,j) / T_j`: the share of `j`'s intermediate inputs
  that is commodity `c` (O9).
- `customer_share(c,j) = U(c,j) / T_c`: the share of `c`'s intermediate use
  that industry `j` buys (O10).

Both denominators are published totals. No total is recomputed. Published
cells are rounded, so a share column sums to 1 only up to BEA's rounding. The
report records each gap.

### Target rows

`bea_io_use_targets.parquet`, written by the new published-aggregate writer.
One row for each nonzero published cell and each of three measures:

| Column | Value |
|---|---|
| `source` | `bea_io` |
| `family` | `bea_io_use` |
| `unit_a_type` | `bea_commodity_2017_detail` |
| `unit_a` | `feature:bea_commodity_2017_detail:<c>`, where `<c>` is the BEA code |
| `unit_b_type` | `bea_industry_2017_detail` |
| `unit_b` | `feature:bea_industry_2017_detail:<j>`, where `<j>` is the BEA code |

**My call on unit strings:** `target_contract.valid_unit` accepts a typed
`feature:<kind>:<value>` string, or a `naics`, `soc` or `geography` node ID. A
BEA code is neither a NAICS node nor a geography, so the `feature:` form keeps
`valid_unit` unchanged and adds no third exception to the contract. The code
table gives each BEA code its two unit strings, so a reader joins on them.
| `measure` | `use_value_usd_millions`, `input_share` or `customer_share` |
| `value` | `U(c,j)`, `U(c,j)/T_j` or `U(c,j)/T_c` |
| `se`, `se_method` | null, `none` |
| `n_unweighted`, `n_weighted` | null |
| `sample_set` | `bea_io_2017_benchmark_detail_use_before_redefinitions_producer` |
| `vintage` | `bea_io=2017_benchmark` |
| `universe` | Statement below |
| `flags` | Below |

Direction is supplier → buyer: `unit_a` supplies, `unit_b` buys (Stage 2 rule).

Flags on every row: `count_not_published`, `non_headline`,
`published_aggregate`, `se_not_published`. Flags on some rows:

- `diagonal`: `unit_a` equals `unit_b`. An industry buying its own main
  commodity is observed and kept. A reader may drop it.
- `negative_value`: `U(c,j)` is negative.
- `share_outside_unit_interval`: a share lies below 0 or above 1. A positive
  cell can exceed its total when other cells in its line are negative, or by
  rounding in a short line. **My call:** this is flagged data, not a failure.
  The total-gap check already catches a misread line.
- `share_denominator_not_positive`: the share's published total is zero or
  negative. The share `value` is then null. **My call:** the row stays, so
  the three measures keep the same cells.
- `unit_a_no_naics_member`, `unit_b_no_naics_member`: from the code table.

Rows carry no `size_gate_pending` flag, because no count exists to gate.
**My call.** This breaks a convention: every target of every other family
keeps `size_gate_pending` (`CLAUDE.md`). `non_headline` and
`count_not_published` take its place, because no minimum count can ever apply
to a family with no counts.

Zero cells are not stored. The code table lists every commodity and industry,
so a zero is recoverable.

Universe statement (one string, with the snapshot date filled in): "BEA
benchmark input-output accounts, 2017 detail Use table before redefinitions at
producer prices, retrieved <snapshot>. Values are BEA estimates for the whole
U.S. economy in millions of dollars, as published, not counts of records. BEA
codes follow NAICS 2017 and often stand for several NAICS industries. BEA
publishes no standard errors or counts."

### Totals table

`bea_io_totals.parquet` keeps, as published, every nonblank cell of the Use
table that is not a commodity × industry cell. These are the total rows and
columns, the final-demand columns, the value-added rows and the corner cells
where two of them meet. Long form, sorted by `row_code`, `column_code`:

| Column | Type | Meaning |
|---|---|---|
| `row_code`, `column_code` | String | BEA's codes for the cell's row and column |
| `row_title`, `column_title` | String | BEA's labels |
| `row_role`, `column_role` | String | `commodity`, `industry`, `final_demand`, `value_added` or `total` |
| `value` | Float64 | Millions of dollars, as published |

**My call:** two role columns hold the corner cells with no special case. The
roles come from the layout registry that E1 records.

A reader can rescale a share to total use or total output from this table,
with no rebuild. No value in it becomes a target row.

### Published-aggregate contract

**My call on names:** module `published_target_contract.py`, schema version
`targets-published-v1`.

- The column names, order and types equal `target_contract.TARGET_SCHEMA`,
  imported unchanged.
- Every rule of `validate_targets` holds, except one. `n_unweighted` and
  `n_weighted` may be null, only together, and only on a row whose flags
  contain `count_not_published` and `published_aggregate`.
- `value` may be null only on a row flagged `share_denominator_not_positive`.
- `se` is null and `se_method` is `none` on a row flagged `se_not_published`.
- Its writer stages the Parquet, validates it, and records the schema version,
  as `write_targets` does for `targets-v1`.

This is R7.5's contract. A later published-aggregate family can reuse it.

### Validation

The build fails when:

- A commodity row or industry column has a gap between its published total and
  the sum of its published cells larger than the rounding bound. **My call:**
  the bound is `0.5 × (k + 1)` million dollars, where `k` is the number of
  cells summed. A larger gap means a misread row or column.
- A code is duplicated, a code in the Use table is missing from the code
  table, or the three measures do not cover the same cells.
- A share lies outside `[0, 1]` and the row has no
  `share_outside_unit_interval` flag.

## Bundle, commands and provenance

### Module and commands

**My call on names:** module `embedding_data.bea_io_tables`, run as
`uv run python -m embedding_data.bea_io_tables`. It is separate from the frozen
top-level CLI. The plan may split it into several new modules.

| Command | Network | Purpose |
|---|---|---|
| `acquire --snapshot DATE` | Yes | Download the Use table and the concordance |
| `import-file KIND FILE --snapshot DATE` | No | Register an owner-downloaded file |
| `build RUN_ID --codes-run ID --codes-outputs-sha256 PIN --snapshot DATE` | No | Build one immutable bundle |
| `verify RUN_ID --outputs-sha256 PIN` | No | Authenticate the pin, then recompute and compare every table |
| `compare-runs FIRST SECOND` | No | Exact logical comparison of two bundles, omitting run ID and time |

Every command takes an explicit `--data-dir`. Every production command passes
`--data-dir /Users/lowell/Projects/embedding-data/data`. Offline commands load
no environment file, read no credential, construct no HTTP client and run no
upstream builder. Success prints one sorted JSON line. Failure prints only
`BEA input-output <command> failed: <reason>; run <run_id>; path <path>` and
exits 2. It never prints row content. Unequal comparison exits 1.
`compare-runs` is built and fixture-tested in this stage, so a later hardening
stage only runs it.

### Bundle

**My call on location:** `data/derived/bea/input-output/<RUN_ID>/`.

| File | Contents |
|---|---|
| `bea_io_use_targets.parquet` | `targets-published-v1` rows (O9, O10) |
| `bea_io_codes.parquet` | Code table |
| `bea_io_totals.parquet` | Published totals, final demand and value added |
| `inputs.json` | Selection and provenance |
| `report.json` | Accounting and distributions |
| `outputs.json` | Detached inventory of the other five files |

`outputs.json` records the byte size, SHA-256, row count and exact schema of
every Parquet, and the hashes of both other JSON files. It excludes itself. The
findings file records its detached checksum.

`inputs.json` records:

- The codes run ID, detached pin and verified inventory.
- `manifest.entry_for` citations for the two BEA files, with the snapshot date.
- The layout registry version.
- Contract versions `bea-io-codes-v1`, `bea-io-totals-v1` and
  `targets-published-v1`.
- A `SOFTWARE_FILES` record like TRI's: the hashes of the new modules, every
  reused module, `pyproject.toml` and `uv.lock`, the dependency versions, the
  Python version, the execution commit and the dirty flag.

`report.json` records:

- Commodity, industry, final-demand and value-added code counts.
- Nonzero cells, zero cells, negative cells and diagonal cells.
- Cells and value whose commodity or industry has no NAICS member.
- The largest total gap and the number of rows and columns at each gap size.
- Code-table counts by flag, and by number of NAICS 2017 and NAICS 2022
  candidates.
- The distributions of `input_share` and `customer_share`, for O19.

### Run boundary and failure

- `build` stages into an exclusive `<RUN_ID>.part` and renames only after every
  check passes. An existing final or partial name fails and is never reused.
- `build` rechecks the pinned inputs and the software identity just before
  publication. Any change fails the run.
- Failure cleans only the run's own staging.
- Expected data states are retained diagnostics, not failures: special codes,
  negative cells, the diagonal and nonpositive denominators.
- Changed raw bytes, a changed layout, a gap above the bound and invalid
  values are failures.

## Verification and acceptance

### Automated tests

Write the failing tests first. Small typed frames cover:

- Both shares, both denominators, and nonzero-cell selection.
- The diagonal, negative cells and nonpositive denominators.
- The code table: six-digit codes, shorter codes, special codes, shared codes,
  and 2017→2022 one-to-many and many-to-one links.
- The published-aggregate contract: null counts allowed only with both flags,
  null shares only with their flag, and every `targets-v1` rule otherwise.
- Layout refusal, an unknown cell text, a gap above the bound, occupied run
  names, changed pins and changed software.
- `compare-runs` equal and unequal.

**V12 extension.** A fixture chain with no network: synthetic XLSX files in the
layout that E1 records, written with `zipfile` as `tests/code_fixtures.py`
does, `import-file` into a temporary data directory, a real Stage 4 bundle from
the Stage 10 fixture helper, then `build`, `verify`, a second `build` and
`compare-runs`. **My call:** the fixtures are synthetic even if E2 allows
redistribution, because a small synthetic table can hold every case. It holds
at least a special code, a shorter NAICS code, a shared NAICS code, a
one-to-many 2017→2022 link, a diagonal cell, a negative cell, a zero total and
a rounding gap inside the bound. Fixture results are software readiness, never
benchmarks.

### Independent reconciler

`scripts/reconcile_bea_io_tables.py` is written separately from the build
modules and does not import `embedding_data`. It uses the standard library and
Polars. It reads the two cited raw files and the pinned Stage 4 Parquets
directly. It recomputes the code table, the three measures, the totals table
and the report counts. It compares them exactly with the bundle and reports
equal or unequal.

### Host rule

- Run one acquisition at a time, because `manifest.append_entries` checks and
  then appends with no lock. Run one full-data build at a time.
- Before each acquisition and each full-data build, confirm with the owner that
  no other stage's acquisition or build is running, and run
  `pgrep -fl 'embedding_data|embedding-data'`. Stop if it shows another run.
- No write inside a Stage 9 freeze window. Each go-ahead also confirms that no
  Stage 9 freeze window is open. Also run
  `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`
  and stop if it prints anything.
- Each production write needs the owner's go-ahead first: each file fetch or
  import, the build, and any cleanup of a failed run's staging.

### Full-data acceptance

1. Acquire or import the two files. Record their hashes.
2. Run the preflight. Record E1–E3 in the findings file. Stop on a failed check.
3. Build the first run with a fresh ID under `/usr/bin/time -l`, to measure wall
   time and maximum RSS.
4. Verify it with its detached pin.
5. Run the independent reconciler. It must report equal.
6. Confirm preservation. Every earlier raw file is byte-identical. The manifest
   keeps its earlier bytes as a prefix. The raw audit
   (`uv run embedding-data audit --data-dir ...`) reports zero discrepancies.
   The Stage 4 bundle is byte-identical.
7. Write `specs/naics-evaluation-data-stage-15-findings.md`: the run ID, the
   pin, the snapshot date, the wall time, maximum RSS and bundle size of the
   real run, the preflight outcomes and the main counts.

No replay build runs in this stage.

## Methodological limits

- BEA values are estimates for the whole economy, not records. They carry no
  sampling error that BEA publishes, and no count.
- The table is at industry level, not firm level.
- The basis is commodity by industry. Each detail commodity carries its main
  industry's code, but an industry also makes secondary products. Before
  redefinitions, those stay in the industry that made them.
- At producer prices, trade and transport margins appear as purchases of trade
  and transport commodities. Wholesale, retail and transport therefore supply
  almost every industry.
- One BEA code often stands for several NAICS industries. A relation between
  two BEA codes is not a relation between any two of their NAICS members.
- The 2017 benchmark predates NAICS 2022. Its codes reach NAICS 2022 only
  through two concordances.
- Supply chain and look-alike read one table. For held-out judging they are
  one family. If one trains, the other cannot judge.
- The family is non-headline (owner, 2026-11-16).

## Source spec amendment

The plan applies this amendment to
[the source spec](embedding-evaluation-data-spec.md) and `CLAUDE.md` when the
stage ships. It follows the Stage 2 spec's amendment list. Items 1, 2, 4 and 7,
and the wording change in item 3, are already applied. Stage 15 adds item 5 and
its own rows.

- Item 5, a new **R7.5** after R7.4: "A target taken from a published
  aggregate table keeps the published value. It names each R7.1 or R7.3 field
  the publisher does not supply, sets it to null and flags it. It never fills
  or models that field. Such targets use the R7.4 columns under schema
  version `targets-published-v1`." The first three sentences are the Stage 2
  spec's text, *(owner, Stage 2 default 3, 2026-11-16)*. The last follows from
  the owner's pick of approach 1, *(owner, Stage 15 design, 2026-11-23)*.
- Item 3, a new R1.1 row:

  | Source | Unit | Years | Role |
  | --- | --- | --- | --- |
  | BEA benchmark input–output accounts, detail Use table | BEA detail commodity × industry | 2017 benchmark | Published commodity flows to buying industries (non-headline) |

- Item 6, a new R7.2 row, marked *(owner, Stage 15 design, 2026-11-23;
  [stage spec](bea-input-output-tables.md))*:

  | Family | Built from | Units | Evaluates |
  | --- | --- | --- | --- |
  | Input–output use | BEA 2017 benchmark Use table | commodity → buying industry, as input and customer shares | NAICS (non-headline) |

- **My call:** after R8.3, add: "BEA input–output tables are public. Tables
  derived from them may contain every published cell. They cite BEA." The plan
  adds this only if E2 passes, and names the basis that passed it: BEA's
  statement or 17 U.S.C. § 105.
- `CLAUDE.md`: name the BEA family in "What this repo is", and add a section
  for its command group like the TRI section.

## Left to the builder

- The split of the new code into modules, and the function names.
- The exact URLs, file names, sheet names and the layout registry, once E1
  records them.
- Report key names beyond those named here.
- The README section with the command contract. Run pins wait for the owner's
  decision on hardening.
- The plan number. Take the next free number when the plan is written.

## Rollout and later-stage handoff

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 15 — on plan completion, tick the stage and re-validate later stages against what shipped.

- Acquisition and the preflight (full-data acceptance steps 1 and 2) come first,
  because the V12 fixture uses the layout that E1 records. Software readiness
  (tests and the V12 fixture) then comes before the full-data build. Do not
  tick Stage 15 on design or planning completion.
- The shipped handoff gives:
  - **The resume after Stage 15:** the run ID, pin and snapshot date, so a
    hardening stage, if the owner stages one, can replay with the same raw
    files and `compare-runs`.
  - **O19 (BEA protocol section):** the share distributions, the totals table,
    the code-table flags, the universe statement, the non-headline status, and
    the R8.4 exclusion from training and model selection.

After the owner approves this committed spec, use a fresh session with
writing-plans against `specs/bea-input-output-tables.md`. This conversation is
not a dependency.
