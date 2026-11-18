# USAspending vendor links

> Next step: writing-plans in a fresh session against this file. Do not fetch
> any USAspending or SAM.gov file, call either API or use a SAM.gov key, and do
> not build, before the plan exists and the owner gives the go-ahead for each
> write.

Status: draft for owner review, 2026-11-18. Stage 14 design session of
[the roadmap](naics-evaluation-data-roadmap.md). The owner chose the four
decisions below on 2026-11-18. Calls marked "My call" were made in the session
or while writing this file. A builder check by a separate reviewer raised two
questions on 2026-11-18. One became owner decision 4 (malformed codes). The
other is a process call: the document checks run before any download (see
[Preflight](#preflight-open-checks-e4e6)). No data file was downloaded, no API
was called and no key was used for this design.

## Scope and governing contracts

Stage 14 builds Source 2 of
[the evidence-sources spec](uncovered-uses-evidence-sources.md) (the Stage 2
spec) once on real data and verifies it. It serves one use:

- **O6, KYB and anomaly detection.** "Comparing a company's self-reported NAICS
  code against the embedding of its transaction network or vendor graph." The
  evidence is a vendor link between two firms: a federal prime contractor that
  reports a subcontract to a subcontractor. Each firm's industry is its own
  self-reported primary NAICS code in its SAM.gov registration.

naics-embedder's relatedness embedding is "one embedding of the 2,125 codes, at
the industry level", and "firm graphs stay with the users who hold them"
(naics-embedder `specs/naics-artifact-redesign.md`, Req 27). So the target is
industry × industry. Firm-level rows are support only.

The Stage 2 spec's "Rules for every new family" govern this stage. R5, R7.1,
R7.4, R8 and R9 of [the source spec](embedding-evaluation-data-spec.md) govern
codes, outputs, provenance, disclosure, leakage and offline operation. The
Stage 10 spec ([completed](completed/ita-establishment-targets.md)) is the
model for the measure. The Stage 5 spec ([TRI parent links](tri-parent-links.md))
is the model for the bundle, the commands, the preflight and the host rule.

### Owner decisions (2026-11-18)

| # | Decision | Choice | Words |
|---|---|---|---|
| 1 | Population | **Contract subawards only.** These are the subcontracts that prime contractors report under FFATA. Sub-grants are out. | "Contracts only" |
| 2 | Window | **Fiscal years (FY) 2024–2026 by subaward action date**, October 2023 to September 2026. One SAM.gov snapshot, taken at acquisition. | "FY2024–FY2026" |
| 3 | Measure | **Firm shares, mirroring Stage 10.** Each firm counts once in each count. | "Firm shares" |
| 4 | Malformed codes | **Keep R5.3 strict.** A malformed SAM.gov primary NAICS code on a firm that the build reads fails the build. The preflight counts such codes first. No source-spec exception. | "Keep R5.3 strict" |

Two facts from the owner on 2026-11-18:

- The SAM.gov account exists (roadmap, Stage 14 `Consumes`).
- The owner asked for the URL to get the personal API key. So the key did not
  exist yet when this spec was written. It is a precondition of the SAM.gov
  acquisition, not of the design (see [Key handling](#key-handling)).

### Proposals played back and not corrected (2026-11-18)

The session played these back to the owner before decisions 2 and 3. The owner
did not correct them. Approval of this spec confirms them.

- A link is one distinct pair of a prime UEI and a subcontractor UEI with at
  least one usable report in the window. Each pair counts once, however many
  reports or dollars it has. Dollar amounts go only in a support table.
- Each firm's industry is its primary NAICS code in one SAM.gov public monthly
  extract, joined by UEI. The code must be a NAICS 2022 national industry in
  the Stage 4 nodes. The firm's other NAICS codes and the subaward's own NAICS
  field are diagnostics.
- These stay out of the headline cells: a firm linked to itself, a blank UEI or
  one with no usable SAM record (never matched by name), and links inside one
  corporate group as the reported parent UEIs show.

### Out of scope

- The replay build, a full-data `compare-runs`, the long-form acceptance finding
  and the headline minimum count. The owner decides at the resume after this
  stage reports (roadmap, Stage 14 `Leaves out`). Every target row keeps
  `size_gate_pending`.
- Scoring, null-model normalization, data splits and acceptance thresholds: the
  family's protocol section, O18. The family is not scored until that section
  exists (protocol, "Families with no section").
- The R8.4 training-role amendment: a separate owner decision after
  naics-embedder's spec.
- Sub-grants, prime awards without subawards, the NAICS code of a contract as a
  firm's industry, and fiscal years before 2024 or after 2026.
- Firm names, addresses and any other Dun & Bradstreet (D&B) Open Data field.
- Any SAM.gov API other than the Entity Extracts API. Any FOUO or sensitive
  data, or a role that grants it.
- Any change to a frozen module, an earlier stage's artifact or a raw file.

## Intent

naics-embedder judges its industry-relatedness embedding on evidence families
it never trained on. This repository has no evidence of vendor relations
between firms. The KYB use asks whether a firm's own industry code fits the
industries of the firms it buys from and sells to. Federal subcontract reports
observe such links between two identified firms. SAM.gov gives each firm's
self-reported industry. Two industries are close in practice when firms in one
often sell to firms in the other. The NAICS tree can place them far apart.

### Goals

- One verified bundle that relates NAICS 2022 industries as supplier and buyer
  through observed federal subcontracts, as firm shares in both directions.
- Counts, marginals, pair counts and dollar sums that let a later minimum count
  and O18 choose scores with no rebuild.
- A preflight that settles open checks E4–E6 before any data is trusted.
- A key that never reaches a file, a log, a manifest, an output or git.

### Non-goals

- A firm-level KYB score or an anomaly label. naics-embedder and its users own
  firm graphs.
- Coverage outside federal prime contractors and the subcontractors they report.
- Any score, threshold or embedding comparison.

### Anti-goals

The design fails, even if it runs, when it:

- Uses the NAICS code of a contract or a subaward record as a firm's industry.
  A contract code classifies the thing bought, not the vendor
  ([FAR 19.102](https://www.acquisition.gov/far/19.102)).
- Matches firms by name, or joins anything other than an exact UEI.
- Reads a D&B Open Data field into any derived table, or publishes one, or uses
  a SAM.gov record last updated before 2022-04-04. The raw extract is kept as
  delivered (R1.4). It stays on this machine, and no step reads its name or
  address fields.
- Writes the SAM.gov key anywhere, or prints it.
- Lets links inside one corporate group into the headline cells.
- Lets a code that is not a native NAICS 2022 national industry enter a
  headline cell.
- Derives a relation from NAICS code structure.
- Edits a frozen module or an earlier stage's artifact.
- Lets any table feed embedder training, curriculum, hard-negative mining or
  model selection (R8.4).

## What the design session found

Read on 2026-11-18 from public HTML pages and public GitHub source pages. No
data file, PDF or spreadsheet was opened, and no API was called. A research
subagent read most pages through a tool that returns summaries. So every field
name below is *unverified* until E4 or E5 records the real header or layout.

1. **USAspending holds both subaward kinds in one model.** The subaward search
   model gives `subaward_type` as `sub-contract` or `sub-grant`. The download
   types are `sub_contracts` and `sub_grants`
   ([usaspending-api](https://github.com/fedspendingtransparency/usaspending-api),
   `download/lookups.py` and the `subaward_search` delta SQL).
2. **USAspending's subaward model has the fields the link needs.** The model
   column names are `awardee_or_recipient_uei` (prime),
   `sub_awardee_or_recipient_uei` (subcontractor), `sub_ultimate_parent_uei`,
   `subaward_amount`, `sub_action_date` and `sub_fiscal_year`. These are
   database names, not the CSV headers of a download
   ([`subaward_search.py`](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/search/models/subaward_search.py)).
   A prime parent UEI field was not confirmed.
3. **The subaward's NAICS is probably the prime contract's code.** The model
   has a `sub_naics` field. A DeCA page on FSRS says the predominant NAICS code
   of the main contract "will appear". SAM.gov's subcontract upload request has
   no NAICS input
   ([subawards bulk upload API](https://open.gsa.gov/api/subawards-bulkupload-api/)).
   *Inference, unverified.* Whatever E4 finds, this design never uses it as a
   firm's industry.
4. **Bulk subaward data come from Custom Award Data downloads.** A download
   request can name `sub_awards`, and the request validation rejects a date
   range longer than one year. So the build needs one download for each fiscal
   year. No account or key is documented. Whether the Award Data Archive holds
   subawards is *unverified*.
5. **Subaward reporting moved from FSRS.gov to SAM.gov on 2025-03-08.**
   USAspending now receives the subaward file from SAM.gov
   ([sam.gov/fsrs](https://sam.gov/fsrs); Treasury TFM Volume 1, Part 2,
   Chapter 6000). The window spans this change.
6. **Subaward data quality is weak.** The Data Broker runs no field-level or
   cross-file validation on the subaward files (Treasury TFM, paraphrase). GAO
   found about 26% of non-COVID grant subawards to be likely duplicates, and
   implausibly large amounts
   ([GAO-24-106237](https://www.gao.gov/products/GAO-24-106237)). Primes are
   legally responsible for the data. These findings are about grants. Contract
   subawards are *unmeasured*.
7. **The SAM.gov public entity extract is monthly only.** "These files contain
   all active entities and entities expired in the last 6 months." A past
   month can be requested by date. How many past months are kept is not stated
   ([Entity Extracts API](https://open.gsa.gov/api/sam-entity-extracts-api/)).
   A UTF-8 variant of the public monthly V2 file exists. The column positions
   of the primary NAICS and the NAICS code string come only from a search
   summary of a layout PDF *(unverified)*.
8. **Rate limits.** A non-federal user with no role gets 10 requests a day, and
   1,000 with a role (Entity Extracts API page). One extract is one request.
9. **The key comes from the Account Details page.** "must obtain the API Key
   from the https://sam.gov/workspace/profile/account-details page", after a
   one-time password sent by email (Entity Extracts API page). The page states
   no expiry.
10. **D&B data.** SAM.gov shows the Entity Validation Service (EVS) source as
    D&B for registrations last updated before 2022-04-04. The Entity Management
    API has an `evsSource` field, with "D&B" and "E&Y" seen in examples labeled
    FOUO. Whether the public extract carries it is *unverified*. The D&B terms
    on the [Entity API page](https://open.gsa.gov/api/entity-api/) say users
    "shall not access, use or disseminate D&B Open Data in bulk".
11. **SAM.gov keeps registration data for ten years**
    ([records retention](https://sam.gov/announcements/entity-records-retention)).
12. **Registration states.** The Entity Management API shows Active, Inactive
    and "ID Assigned". An ID Assigned entity has a UEI but no full
    registration, so it has no NAICS code. Subcontractors need a UEI but not a
    full registration. So join coverage on the subcontractor side is the main
    data risk.
13. **USAspending's own terms were not read.** Its About and Terms pages render
    through JavaScript that calls the USAspending API. GAO-19-72 says Treasury
    added licensing information to the site in August 2019. E6 reads it.

**The owner's print of the SAM.gov terms.** At the owner's request, the resume
session reviewed the owner's print of
`https://sam.gov/workspace/profile/sign-terms-of-use` on 2026-11-18 (accepted
that day). That reading, which is not legal advice, found:

- Data access is allowed only through the APIs and extracts at
  `https://open.gsa.gov/api/` and `https://sam.gov/data-services`. Automated
  gathering and scraping of the website are prohibited, and so is use of the
  SAM.gov login for data mining or extraction tools.
- Data may be shared publicly only from public versions of the APIs. FOUO and
  sensitive APIs are for internal U.S. Government use.
- The personal API key must never be shared, and must be rotated every 90 days.
- D&B Open Data (name, address, city, state, county code, ZIP, country) needs
  written attribution and no bulk sharing. NAICS is not in that list. Other D&B
  data may not be used for commercial, resale or marketing purposes.

This design depends on that reading only through E6, which re-reads the live
terms. The design never marks E6 passed.

**Consequence for the roadmap.** The roadmap's `Consumes` for Stage 14 lists
the Stage 4 concordances. SAM.gov registrations are current and coded in NAICS
2022, so Stage 14 reads only the Stage 4 bundle's `naics_nodes.parquet` and
does not read its concordance (see [Firm table](#firm-table)). Plan completion
re-validates the roadmap against this. Two texts still say the account is
missing: the O6 cost note in the roadmap and the USAspending row of
`specs/deliverable-map.md`. The roadmap's Stage 14 entry governs. This session
edits neither.

## Approaches

### Build approach

| Approach | What it does | Trade-off | Decision |
|---|---|---|---|
| 1. Standalone command group, one bundle | New `python -m embedding_data.usaspending_vendor_links` with acquisition, import, build, verify and compare commands. New modules import reused ones. | Matches Stages 8–10 and Stage 5. Leaves every frozen module unchanged. Needs no new dependency. | **Chosen.** The only sensible way (my call) |
| 2. New commands in the Stage 10 module | Reuses Stage 10's wiring. | Stage 10 records its module hashes. Edits make its `verify` fail. | Rejected |
| 3. Nested project with its own lock | Isolates dependencies. | Only needed for a new dependency. Polars, httpx and the standard `zipfile` module are enough. | Rejected |

### Measure

| Approach | What each row holds | Trade-off | Decision |
|---|---|---|---|
| 1. Firm shares | The share of suppliers in `s` with at least one buyer in `d`, and the share of buyers in `d` with at least one supplier in `s` | Mirrors Stage 10 and Stage 5, so one approach to scoring can serve three families. One large prime cannot dominate a cell. `n_unweighted` counts independent firms. Shares do not sum to 1. | **Chosen** (owner, 2026-11-18) |
| 2. Link shares | The share of `s` suppliers' firm pairs that go to `d` buyers, and the reverse | Proper conditional distributions, like a BEA Use table read by row or column. One prime with many subcontractors can dominate its industry's column. | Rejected. The support table keeps pair counts, so O18 can compute link shares with no rebuild |

## Selected inputs and trust boundary

### Inputs

| Input | Identity | Use |
|---|---|---|
| USAspending contract subaward downloads | One Custom Award Data download for each of FY2024, FY2025 and FY2026, all under one snapshot label, manifest-recorded | Firm pairs, dates, parent UEIs, amounts |
| SAM.gov public entity extract | One public monthly V2 extract, UTF-8 variant, manifest-recorded | Each firm's primary NAICS, NAICS list, status and dates |
| Stage 4 codes bundle | `stage4_v11_20261013_r2`, detached `outputs.json` SHA-256 `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` | `naics_nodes.parquet`: the 1,012 NAICS 2022 national-industry node IDs |

### Codes selection

**My call:** Stage 14 has its own codes selector, with the same steps as
Stage 5's. It checks the run ID and pin syntax, authenticates the detached pin,
verifies the bundle inventory with `target_io.verify_inventory`, checks the
schema version and run identity, and reads `naics_nodes.parquet`. It does not
call Stage 10's `select_codes`, which also re-checks the ITA source summary.
If Stage 5's selector has merged and serves unchanged, the plan may import it.

### Reused interfaces

Stage 14 imports these and never edits them:

- `target_contract.write_targets`, `validate_targets`, `TARGET_SCHEMA` and
  `TARGET_KEY_COLUMNS` (Stage 6).
- `target_io` (`stage`, `relative_file`, `file_record`, `inventory`,
  `verify_inventory`, `write_json`).
- `manifest` (`describe_file`, `append_entries`, `entry_for`, `sha256_file`).
- `paths`.
- The Stage 10 fixture helper that builds a real Stage 4 bundle
  (`tests/ita_establishment_fixtures.py`), for the V12 fixture.

`ipums_census_access` is the model for key handling. Its `read_credential`
reads `CENSUS_API_KEY` only, so Stage 14 writes its own credential reader on
the same pattern. It may import a helper from that module only if the helper
serves unchanged.

### Frozen modules

Stage 6's `FROZEN_MODULES` and `TARGET_MODULES`, the Stage 7–9 software files,
the Stage 10 modules recorded in its bundle's `SOFTWARE_FILES`, `cli.py` and
`code_references.py` stay unchanged. So does any test file that an earlier
stage hashes. Stage 14 adds modules only. If the plan finds that a reused
function cannot serve unchanged, it stops and asks the owner.

### What Stage 14 does not consume

- The Stage 4 concordance, ITA data, geography bundles, Stage 6 assignments,
  Stage 7–9 IPUMS artifacts, Stage 10 bundles and Stage 5 TRI bundles.
- No upstream builder runs.

## Raw files

### Acquisition and import

Four commands write raw files. Each write needs the owner's go-ahead.

- `acquire-subawards FY --snapshot DATE` (network, no key) requests a Custom
  Award Data download of contract subawards for one fiscal year, filtered by
  subaward action date from October 1 to September 30. It polls the request's
  status at a fixed interval and downloads the ZIP file that the request
  returns. The plan's first task fixes the request body from the USAspending
  API documentation.
- `acquire-sam-extract --month YYYY-MM` (network, key) requests the public
  monthly V2 UTF-8 extract for that month through the Entity Extracts API only.
  It never reads a SAM.gov web page, because the terms forbid scraping.
- `import-subawards FY FILE --snapshot DATE` (offline) registers a file that
  the owner downloaded from USAspending's Custom Award Data page in a browser.
- `import-sam-extract FILE --month YYYY-MM` (offline) registers an extract that
  the owner downloaded in a browser from SAM.gov Data Services. This path needs
  no key in this repository's process.

Each download goes to `.part` and is renamed only after its length matches
`Content-Length`, then recorded. An import's `retrieved_at` is the import time,
flagged as a proxy, as Stage 3 does for HUD. All four refuse an existing path.
Raw files are never replaced.

**My call: the snapshot label.** `--snapshot DATE` is a date that the operator
chooses for one set of three subaward downloads. The three downloads may run on
different days. Each manifest entry records its own retrieval time.

### Key handling

The SAM.gov key is needed only by `acquire-sam-extract`. **My calls,** on the
pattern of `ipums_census_access`:

- The key is read from the environment variable `SAM_API_KEY`, from an
  explicit `--env-file`, or from a hidden prompt (`--prompt`) in a local
  terminal. It never populates the process environment from a file.
- The key is added only to the request URL sent on the wire. The manifest's
  `source_url` is the URL without the key.
- Transport logging is muted while the key is in use, because HTTPX logs wire
  URLs.
- A response body or redirect URL that contains the key is refused, and
  nothing from it is written.
- An error message never contains the key or the wire URL.
- Every other command loads no environment file, reads no credential and
  constructs no HTTP client.

The owner gets the key from `https://sam.gov/workspace/profile/account-details`
and keeps it outside the repository. The terms that the owner accepted require
rotation every 90 days. E6 re-reads this. If the acquisition runs more than 90
days after the key was made, the owner makes a new key first.

### Layout and manifest

**My calls:**

- `data/raw/usaspending/subcontracts/<snapshot>/FY<YYYY>/<file name>`.
- `data/raw/sam/entity-extract/public-monthly-v2/<YYYY-MM>/<file name>`.

Each file is kept as delivered (a ZIP). A later snapshot or month lands beside
the earlier one. The manifest entry records the key-free source URL (null for
an import), retrieval time, SHA-256, size, client and version. The snapshot
label and the extract month live in the path. `through_date` stays null.

### Snapshot selection

`build` takes `--snapshot DATE` and `--sam-month YYYY-MM`. For each window
year it selects the one manifested subaward file under that snapshot. It
selects the one manifested extract under that month. A missing or extra file
fails the build. The window is the constant FY2024–2026. The build refuses any
other window.

### Reading

- Every column is read as a string. Codes and UEIs stay strings (R9.1).
- A registry constant records the exact header row of the subaward CSV for each
  window year, taken from the preflight. The build maps the columns it needs by
  exact header text. A changed header fails the build.
- **My call:** a download ZIP may hold more than one CSV file. The build reads
  every CSV member of the ZIP, each with the recorded header, and the registry
  records the member-name pattern. Any other member fails the build.
- A second registry constant records the extract layout: the column positions
  of the fields the build reads, taken from GSA's layout document during E5. A
  changed layout version or a row with the wrong field count fails the build.
- The build reads only the extract fields named in
  [Firm table](#firm-table). It never selects a name, address or other D&B
  Open Data field.
- Every subaward row must have the type `sub-contract`. Any other value fails
  the build, because the download asked for contract subawards only.

Columns used from the subaward file (names *unverified* until E4): prime UEI,
prime parent UEI if present, subcontractor UEI, subcontractor parent UEI,
subaward action date, subaward amount, subaward type, a report identifier if
present, and the subaward's NAICS field (diagnostic).

## Preflight: open checks E4–E6

The preflight has two parts, as in Stage 5. **My calls:**

- **Document checks**, marked "(read)" below. They run first, before any
  acquisition or import, because they need no data. The operator reads the
  named pages and records the URL, the read date and a short quote in the
  findings file. Reading GSA's extract layout document (a PDF or spreadsheet)
  needs the owner's go-ahead. These documents are not manifest-registered and
  are not stored under the data root, because no build step reads them.
- **Data checks.** They run after the four raw files are recorded and before
  any build. A script, `scripts/preflight_usaspending_sam.py`, reads only the
  manifested files and the pinned Stage 4 nodes, offline, and prints a JSON
  report.

**My call: why the document checks come first.** The public extract carries
name and address columns on every row, and the D&B terms forbid bulk access to
D&B Open Data. Whether downloading the public extract is allowed is an E6
question. If E6 fails, the stage stops before any raw file exists, so no
recorded raw file ever needs removal. Removing a recorded raw file is outside
this design and would need its own owner decision.

The results of both parts go into the Stage 14 findings file. The covered
verdict holds only while these checks pass. A failed check stops the stage.
The owner then records O6 as uncovered or promotes a named alternate, and the
Stage 2 spec's verdict table is amended. A trigger below stops the stage until
the owner decides. It is not an acceptance threshold.

| Check | Measures and records | Stops the stage when |
|---|---|---|
| **E4** subawards | Each year's exact header row. The fields for the prime UEI, the subcontractor UEI, both parent UEIs, the action date, the amount, the type, a report identifier and the subaward NAICS. The date field that the download filter used (read). Rows by type. Blank and malformed UEI rates by side. Rows whose action date falls outside the file's fiscal year. Duplicate rows (identical in every column). Rows by month, to show the March 2025 move to SAM.gov. The share of rows whose subaward NAICS equals the prime contract's NAICS, where both exist (diagnostic). | A window year has no prime UEI, subcontractor UEI or action date field. The download filter does not select by subaward action date (owner decides). No parent UEI field exists on either side, because the corporate-group rule depends on it (owner decides). |
| **E5** SAM.gov extract | The layout version and the column positions of UEI, primary NAICS, NAICS code string, registration status, last update date and EVS source if present (read, from GSA's layout document). Rows per UEI. Rows by registration status. The last-update-date distribution. EVS source values if present. The share of primary codes that are NAICS 2022 national industries. Join coverage: the share of distinct prime UEIs and of distinct subcontractor UEIs in the window that reach an eligible SAM record. How many past monthly files the API keeps, and the rate limits (read). | The extract has no UEI or primary NAICS field. The extract has no last update date, because the D&B rule depends on it. A firm that the build reads has a malformed primary code (see [Firm table](#firm-table)). The owner decides with the counts in hand. More than 1% of the distinct UEIs on usable reports that have a primary code have one outside the NAICS 2022 national-industry set (trigger). Fewer than half of the distinct prime UEIs, or of the distinct subcontractor UEIs, reach an eligible SAM record (trigger). |
| **E6** terms | The live SAM.gov terms of use, the D&B terms on the Entity API page and the key-rotation rule (read). USAspending's terms or licensing page, read in a browser (read). Any statement on SAM.gov Data Services or open.gsa.gov about redistribution of public entity data (read). | A statement restricts publishing aggregates or UEI-level rows derived from public subaward data or public entity data. A statement forbids the API access that `acquire-subawards` or `acquire-sam-extract` uses. A statement forbids downloading the public extract, which carries name and address fields, for this use. A failed terms check never becomes "build it but keep the aggregates local" (Stage 2 rule). |

**My call: the two coverage triggers.** Primes must be registered in SAM.gov to
hold a contract, so low prime coverage points to a wrong join or layout.
Subcontractors may hold a UEI only, so their coverage is the open question. One
half is a level at which the target would describe a minority of the observed
links. The owner then decides whether to go on.

## Subaward reports

### Report rules

Each row of the three subaward files is one report. The build reads every row
and assigns it one report status. Statuses are disjoint and checked in this
order:

1. `uei_unusable`: the prime or the subcontractor UEI is blank or does not
   match `^[A-Z0-9]{12}$` after stripping surrounding whitespace.
2. `action_date_invalid`: the action date is blank or not a valid date.
3. `outside_window`: the action date's fiscal year is outside 2024–2026. The
   fiscal year of a date is the calendar year of the date plus three months.
4. `usable`.

Only usable reports form pairs. A report outside its file's fiscal year but
inside the window still counts, under its own fiscal year. **My call:** the
build counts duplicate rows but does not remove them, because a pair counts
once either way.

### Corporate groups

A pair is intra-group when any usable report of the pair shows one of these,
with each parent UEI valid under the UEI rule:

- The subcontractor's parent UEI equals the prime UEI.
- The prime's parent UEI equals the subcontractor UEI.
- Both parent UEIs are present and equal.

**My call:** one report is enough, because the parent fields are reported, and
an absent parent does not prove that no group exists. Intra-group pairs leave
the headline cells and enter a sensitivity count. A blank parent UEI never
forms a group.

## Firm table

Each distinct UEI on a usable report gets one firm status from the SAM.gov
extract. Statuses are disjoint and checked in this order:

1. `not_in_sam`: no extract row has this UEI.
2. `dnb_era_record`: an extract row for this UEI has a last update date before
   2022-04-04, or an EVS source of D&B where the field exists.
3. `naics_missing`: no row gives a primary NAICS code.
4. `naics_conflict`: the rows give more than one distinct primary code.
5. `naics_not_2022`: the one code is six digits but is not a NAICS 2022
   national industry in the selected Stage 4 nodes. This is a known vintage
   mismatch, not a parse failure (R5.4).
6. `eligible`.

**Malformed codes fail the build (R5.3, owner decision 4).** A primary code is
malformed when it does not match `^[0-9]{6}$` after stripping surrounding
whitespace. If any row of a UEI that reaches steps 3–5 gives a malformed
primary code, the build fails. Steps 3–5 cover every UEI on a usable report
that is in the extract and is not a `dnb_era_record`, because those are the
firms whose codes the build reads. E5 counts these codes first, so the stop
comes in the preflight, before any build. Codes on other extract rows, the
firm's other codes and the subaward's NAICS field are diagnostics. They are
counted and never fail the build.

**My call on several rows for one UEI.** The extract may hold more than one row
for one UEI, for example one for each EFT indicator *(unverified)*. Rows that
agree on the primary code give one firm. Rows that disagree are kept, flagged
and excluded. No value is picked. This follows Stage 5.

**My call on registration status.** Active and expired rows in the extract are
used alike, because an expired firm's code is still its last self-report. The
status is a diagnostic.

**My call on old codes.** A primary code outside NAICS 2022 is excluded, not
mapped through the Stage 4 concordance. A crosswalked code cannot enter a
headline cell (Core principle), and a registration is current, so such codes
should be rare. E5 counts them.

The firm's NAICS code string (its other codes, with any small-business flags)
is parsed for diagnostics only. The report counts firms whose primary code is
missing from their own code string.

## Pair table and eligibility

Usable reports are grouped into distinct pairs of (prime UEI, subcontractor
UEI). Each pair gets one pair status. Statuses are disjoint and checked in this
order:

1. `self_link`: the prime UEI equals the subcontractor UEI.
2. `intra_group`: the pair is intra-group (see [Corporate groups](#corporate-groups)).
3. `prime_ineligible`: the prime's firm status is not `eligible`.
4. `sub_ineligible`: the subcontractor's firm status is not `eligible`.
5. `eligible`.

An eligible pair has a supplier industry `s` (the subcontractor's node) and a
buyer industry `d` (the prime's node).

## Vendor-link target (O6)

### Estimand

Let `P` be the set of eligible pairs `(p, u)`, where `p` is the prime and `u`
the subcontractor. Let `ind(x)` be firm `x`'s NAICS 2022 node. Then:

- `n_sup(s)` = number of subcontractors `u` with `ind(u) = s` in some pair in `P`.
- `n_buy(d)` = number of primes `p` with `ind(p) = d` in some pair in `P`.
- `S(s,d)` = number of subcontractors `u` with `ind(u) = s` that have at least
  one pair in `P` with a prime in `d`.
- `B(s,d)` = number of primes `p` with `ind(p) = d` that have at least one pair
  in `P` with a subcontractor in `s`.
- `L(s,d)` = number of pairs in `P` with a subcontractor in `s` and a prime in `d`.

Each firm counts at most once in each count, however many reports, pairs,
years or dollars it has. A firm that is a prime in one pair and a subcontractor
in another counts in each role. The window is pooled. Each firm has one
industry, from one snapshot, so no same-year condition applies.

For each ordered pair `(s,d)` with `L(s,d) > 0`, emit two target rows.
The diagonal `s = d` is emitted, because a firm that buys from its own industry
is observed evidence. No zero cells are emitted. `0 < value ≤ 1`.

| `measure` | `unit_a` | `unit_b` | `value` | `n_unweighted` |
|---|---|---|---|---|
| `supplier_share` | `s` | `d` | `S(s,d) / n_sup(s)` | `S(s,d)` |
| `buyer_share` | `s` | `d` | `B(s,d) / n_buy(d)` | `B(s,d)` |

**Direction.** `unit_a` is always the supplier industry and `unit_b` the buyer
industry, as the Stage 2 spec's supplier → buyer rule says. The direction lives
in this rule and in `measure`, because `targets-v1` ties each unit type to its
node level (`target_contract.valid_unit`). Rows `(s,d)` and `(d,s)` are
different cells.

The intra-group sensitivity recomputes `S`, `B`, `L`, `n_sup` and `n_buy` with
`intra_group` pairs admitted.

### Target rows

`vendor_links.parquet`, written by `target_contract.write_targets`:

| Column | Value |
|---|---|
| `source` | `usaspending_sam` |
| `family` | `vendor_links` |
| `unit_a_type`, `unit_b_type` | `naics_national_industry` |
| `unit_a`, `unit_b` | Supplier and buyer NAICS 2022 national-industry node IDs from the selected bundle |
| `measure` | `supplier_share` or `buyer_share` |
| `value` | As in the estimand table |
| `se`, `se_method` | null, `none` |
| `n_unweighted` | As in the estimand table |
| `n_weighted` | `float(n_unweighted)` |
| `sample_set` | `usaspending_subcontracts_fy2024_2026` |
| `vintage` | `naics=2022` |
| `universe` | Statement below |
| `flags` | `size_gate_pending`, plus the support label below |

Support label: add `numerator:intra_group_sensitivity:true` when the
row's count under the intra-group sensitivity differs from its `n_unweighted`.

Universe statement (one string, with the snapshot label and the extract month
filled in): "USAspending.gov contract subaward reports (FFATA subcontracts)
with subaward action dates in federal fiscal years 2024–2026, downloaded under
snapshot <date>, joined by UEI to the SAM.gov public monthly entity extract of
<month>. The population is federal prime contractors and the subcontractors
they report, not a frame of firms or of business-to-business trade. A link is
a distinct prime–subcontractor pair. Links within one corporate group, as the
reported parent UEIs show, are excluded. Industries are each firm's
self-reported primary NAICS 2022 code in SAM.gov at the extract date, not at
the subaward date. Links, codes and amounts are self-reported and
unvalidated."

### Companion tables

`vendor_link_marginals.parquet`, one row per node with `n_sup > 0` or
`n_buy > 0`, sorted by `node_id`:

| Column | Type | Meaning |
|---|---|---|
| `node_id` | String | Industry |
| `n_suppliers` | UInt64 | `n_sup(node)` |
| `n_buyers` | UInt64 | `n_buy(node)` |
| `n_supplier_pairs` | UInt64 | Eligible pairs with a subcontractor in this industry |
| `n_buyer_pairs` | UInt64 | Eligible pairs with a prime in this industry |
| `n_suppliers_partial` | UInt64 | Subcontractors in `n_sup` that also have a pair excluded as `prime_ineligible` |
| `n_buyers_partial` | UInt64 | Primes in `n_buy` that also have a pair excluded as `sub_ineligible` |
| `n_suppliers_including_intra_group` | UInt64 | `n_sup` under the intra-group sensitivity |
| `n_buyers_including_intra_group` | UInt64 | `n_buy` under the intra-group sensitivity |

Partial counterparty sets are measured per industry, not per cell, as in
Stage 10. A firm with a pair excluded because its counterparty is ineligible
may trade with an industry that the target cannot see. It can only be missing
from some `S` or `B`. It can never inflate one.

`vendor_link_support.parquet`, one row per directed cell, sorted by `unit_a`,
`unit_b`:

| Column | Type | Meaning |
|---|---|---|
| `unit_a`, `unit_b` | String | Same node IDs as the target rows |
| `s_suppliers` | UInt64 | `S(s,d)` |
| `b_buyers` | UInt64 | `B(s,d)` |
| `l_pairs` | UInt64 | `L(s,d)` |
| `l_fy2024`, `l_fy2025`, `l_fy2026` | UInt64 | Pairs in `L(s,d)` with a usable report in that fiscal year |
| `s_including_intra_group`, `b_including_intra_group`, `l_including_intra_group` | UInt64 | The same counts under the intra-group sensitivity |
| `amount_sum` | Decimal | Sum of the delivered amounts of the usable reports of the cell's eligible pairs |
| `n_reports` | UInt64 | Usable reports of the cell's eligible pairs |

**My call on amounts.** `amount_sum` is a diagnostic. It sums every usable
report as delivered, duplicates included, because no reliable report key is
known. A report with a blank or unparseable amount adds nothing to the sum, and
the report counts such reports. No target uses amounts.

Cells that exist only under the intra-group sensitivity are counted in the
report, not listed.

### Pair table

**My call:** `vendor_link_pairs.parquet` holds one row for each distinct
(prime UEI, subcontractor UEI) pair with at least one usable report, sorted by
`prime_uei`, `sub_uei`. It lets `verify`, the
reconciler and O18 work from firm pairs with no rebuild.

| Column | Type | Meaning |
|---|---|---|
| `prime_uei`, `sub_uei` | String | UEIs as delivered, stripped |
| `n_reports` | UInt64 | Usable reports |
| `n_fy2024`, `n_fy2025`, `n_fy2026` | UInt64 | Usable reports by fiscal year |
| `prime_status`, `sub_status` | String | Firm status |
| `prime_node_id`, `sub_node_id` | String | NAICS 2022 node ID, null unless that firm is eligible |
| `flag_intra_group` | Boolean | The pair is intra-group |
| `pair_status` | String | Pair status |
| `amount_sum` | Decimal | As in the support table, for this pair |

The table holds UEIs, codes, counts and amounts only. UEIs and amounts are in
USAspending's public data. The table holds no name, address or other D&B Open
Data field. **My call:** whether it may leave the machine is part of E6, like
every other table.

### Validation

Beyond `validate_targets`, a family validator checks:

- Every unit is a NAICS 2022 national-industry node in the selected bundle.
- Each `(s,d)` has exactly one `supplier_share` and one `buyer_share` row.
- `1 ≤ S(s,d) ≤ n_sup(s)`, `1 ≤ B(s,d) ≤ n_buy(d)`, and
  `max(S, B) ≤ L ≤ S × B`.
- Each `value` equals its ratio within floating tolerance.
- For each `s`, the sum of `L(s,d)` over `d` equals `n_supplier_pairs(s)`. For
  each `d`, the sum over `s` equals `n_buyer_pairs(d)`.
- The support, marginal and pair tables agree with the target rows.

## Bundle, commands and provenance

### Module and commands

**My call on names:** module `embedding_data.usaspending_vendor_links`, run as
`uv run python -m embedding_data.usaspending_vendor_links`. It is separate from
the frozen top-level CLI. The plan may split it into several new modules.

| Command | Network | Key | Purpose |
|---|---|---|---|
| `acquire-subawards FY --snapshot DATE` | Yes | No | Download one fiscal year of contract subawards |
| `acquire-sam-extract --month YYYY-MM` | Yes | Yes | Download one public monthly extract |
| `import-subawards FY FILE --snapshot DATE` | No | No | Register an owner-downloaded subaward file |
| `import-sam-extract FILE --month YYYY-MM` | No | No | Register an owner-downloaded extract |
| `build RUN_ID --codes-run ID --codes-outputs-sha256 PIN --snapshot DATE --sam-month YYYY-MM` | No | No | Build one immutable bundle |
| `verify RUN_ID --outputs-sha256 PIN` | No | No | Authenticate the pin, then recompute and compare every table |
| `compare-runs FIRST SECOND` | No | No | Exact logical comparison of two bundles, omitting run ID and time |

Every command takes an explicit `--data-dir`. Every production command passes
`--data-dir /Users/lowell/Projects/embedding-data/data`. Offline commands load
no environment file, read no credential, construct no HTTP client and run no
upstream builder. Success prints one sorted JSON line. Failure prints a short,
fixed reason with the command, run ID and path, and exits 2. It never prints row
content or a key. Unequal comparison exits 1.

### Bundle

**My call on location:** `data/derived/usaspending/vendor-links/<RUN_ID>/`.

| File | Contents |
|---|---|
| `vendor_links.parquet` | `targets-v1` rows (O6) |
| `vendor_link_marginals.parquet` | Industry marginals |
| `vendor_link_support.parquet` | Cell support |
| `vendor_link_pairs.parquet` | Firm pairs |
| `inputs.json` | Selection and provenance |
| `report.json` | Accounting and distributions |
| `outputs.json` | Detached inventory of the other six files |

`outputs.json` records the byte size, SHA-256, row count and exact schema of
every Parquet, and the hashes of both other JSON files. It excludes itself. The
findings file records its detached checksum.

`inputs.json` records:

- The codes run ID, detached pin and verified inventory.
- `manifest.entry_for` citations for the three subaward files and the extract,
  with the snapshot label and extract month.
- The window, and the versions of the header registry and the extract layout
  registry.
- Contract versions `vendor-link-pairs-v1`, `vendor-links-v1` and `targets-v1`.
- Implementation hashes of the new modules and every reused module, dependency
  versions, Python version, `uv.lock` hash, execution commit and dirty flag.

`report.json` records, by fiscal year where it applies:

- Reports by report status, in disjoint partitions that sum to the rows read.
- Distinct UEIs by role and firm status, and pairs by pair status, each in
  disjoint partitions.
- Join coverage: the shares of distinct prime UEIs and subcontractor UEIs that
  are eligible.
- Extract rows by registration status, UEIs with several rows, and the EVS
  source values if present.
- Duplicate report rows, reports with a blank or unparseable amount, and
  reports by month.
- Firms whose primary code is missing from their own code string.
- The diagonal: cells with `s = d` and their share of `L`.
- Cells that exist only under the intra-group sensitivity.
- The distributions of `n_unweighted` for each measure, for a later minimum
  count (the V9 handoff), and of subcontractors per prime and primes per
  subcontractor.

### Run boundary and failure

- `build` stages into an exclusive `<RUN_ID>.part` and renames only after every
  check passes. An existing final or partial name fails and is never reused.
- `build` rechecks the pinned inputs and the software identity just before
  publication. Any change fails the run.
- Failure cleans only the run's own staging.
- Expected data states are retained diagnostics, not failures: unusable
  reports, ineligible firms, excluded pairs and duplicate rows.
- Changed raw bytes, a changed header or layout, a wrong field count, a
  subaward type other than `sub-contract`, a malformed primary code on a firm
  that the build reads, row loss or multiplication and
  invalid estimates are failures.

## Verification and acceptance

### Automated tests

Write the failing tests first. Small typed frames cover:

- Each report status, each firm status and each pair status, and their order.
- The UEI rule, the fiscal-year rule and the window.
- Each of the three corporate-group conditions, and a blank parent that forms
  no group.
- Several extract rows for one UEI, agreeing and disagreeing.
- The D&B rule at 2022-04-03 and 2022-04-04.
- One count per firm, a firm in both roles, the diagonal, and a prime with many
  subcontractors where firm shares and pair counts differ.
- The intra-group sensitivity and its support label.
- Partial counterparty sets.
- A malformed primary code on a firm that the build reads fails the build. The
  same code on an unread extract row, in a firm's other codes or in the
  subaward's NAICS field is only counted.
- Header and layout refusal, a sub-grant row, occupied run names, changed pins
  and changed software.
- `compare-runs` equal and unequal.

**Key tests.** With `httpx.MockTransport`, `acquire-sam-extract` must:

- send the key only in the wire URL;
- leave it out of the manifest, every log record, every printed line, every
  error message and every written file;
- refuse a response or redirect that echoes it.

Every offline command must read no key and construct no client, as Stage 9's
tests check.

**V12 extension.** A fixture chain with no network: synthetic subaward CSVs in
the recorded header layout and a synthetic extract in the recorded layout,
imported into a temporary data directory, a real Stage 4 bundle from the
Stage 10 fixture helper, then `build`, `verify`, a second `build` and
`compare-runs`. **My call:** the subaward and extract files are synthetic, with
made-up UEIs and no name or address values. The fixture contains at least: a
self-link, an intra-group pair by each of the three conditions, a subcontractor
not in SAM.gov, a record last updated before 2022-04-04, a missing code, a code
conflict, a well-formed code outside NAICS 2022, a malformed code on an extract
row that no usable report reaches, a blank UEI, a malformed UEI, a report
outside the window, a duplicate row, a diagonal cell, a firm in both roles, a
prime with several subcontractors in one industry, and a report in each fiscal
year. Fixture results are software readiness, never benchmarks.

### Independent reconciler

`scripts/reconcile_usaspending_vendor_links.py` is written separately from the
build modules and does not import them. It reads the four cited raw files and
the pinned Stage 4 nodes directly. It recomputes the report, firm and pair
statuses, `n_sup`, `n_buy`, `S`, `B`, `L`, the intra-group sensitivity, the
partial counts and `amount_sum`. It compares them exactly with the bundle and
reports equal or unequal.

### Host rule

- Run one acquisition at a time, because `manifest.append_entries` checks and
  then appends with no lock. Each of the four raw files is one acquisition.
  Run one full-data build at a time.
- Before each acquisition and each full-data build, confirm with the owner that
  no other stage's acquisition or build is running, and run
  `pgrep -fl 'embedding_data|embedding-data'`. Stop if it shows another run.
- **My call: no write inside a Stage 9 freeze window**, as in Stage 5. Each
  go-ahead also confirms that no Stage 9 freeze window is open. Also run
  `pgrep -fl 'embedding_data\.acs_targets|stage9_independent|reconcile_stage9'`
  and stop if it prints anything.
- Each production write needs the owner's go-ahead first: each file fetch or
  import, the build, and any cleanup of a failed run's staging.
- Before `acquire-sam-extract`, the owner confirms that the key exists and is
  less than 90 days old.

### Full-data acceptance

1. Run the preflight's document checks (E4's filter read, E5's layout and API
   reads, and E6). Record them in the findings file. Stop on a failed check.
2. Acquire or import the three subaward files and the extract. Record their
   hashes.
3. Run the preflight's data checks. Record E4 and E5 in the findings file. Stop
   on a failed check or a trigger.
4. Build the first run with a fresh ID under `/usr/bin/time -l`, to measure wall
   time and maximum RSS.
5. Verify it with its detached pin.
6. Run the independent reconciler. It must report equal.
7. Confirm preservation. Every earlier raw file is byte-identical. The manifest
   keeps its earlier bytes as a prefix. The raw audit
   (`uv run embedding-data audit --data-dir ...`) reports zero discrepancies.
   The Stage 2 summary and the Stage 4, Stage 6 and Stage 10 bundles, and any
   Stage 5 bundle, are byte-identical.
8. Write `specs/naics-evaluation-data-stage-14-findings.md`: the run ID, the
   pin, the snapshot label, the extract month, the wall time, maximum RSS and
   bundle size of the real run, the preflight outcomes, join coverage and the
   main counts.

No replay build runs in this stage.

## Methodological limits

- The population is federal prime contractors and the subcontractors they
  report. It is not all firms or all business-to-business trade.
- Industries are SAM.gov registrations at the extract date. A firm whose
  industry changed after a subaward counts under its new code. A firm whose
  registration expired more than 6 months before the extract is missing.
- A subcontractor with a UEI only has no code. Its links are lost. Join coverage
  measures this loss.
- Codes, links and amounts are self-reported and unvalidated. That codes are
  self-reported is also what the KYB use tests.
- One primary code per firm hides a firm's other industries. Other codes are
  diagnostics only.
- Corporate groups are seen only through reported parent UEIs. A group with no
  reported parent stays in the headline cells.
- One firm can hold several UEIs. This project cannot join them.
- The window spans the move of subaward reporting from FSRS.gov to SAM.gov on
  2025-03-08. Counts by year and month show any break, but no correction is
  made.
- USAspending revises its data. A later snapshot is a new run with a new pin.
- Counts come from all reports, not a sample. Standard errors are `none`.
- Vendor links, TRI parent links and ITA co-ownership measure different
  relations. Excluding intra-group pairs keeps vendor links apart from
  ownership. The protocol section, O18, decides which families may judge one
  another.

## Source spec amendment

The plan applies this amendment to
[the source spec](embedding-evaluation-data-spec.md) and `CLAUDE.md` when the
stage ships. It follows the Stage 2 spec's amendment list.

**Always (Stage 14's own items).**

- Item 4 (R1.2). Replace "All three sources are free." with the Stage 2 spec's
  exact text: "All sources are free. A free account or API key is allowed. Its
  key is handled like `IPUMS_API_KEY`." The rest of R1.2 stays.
- Item 3, a new R1.1 row:

  | Source | Unit | Years | Role |
  | --- | --- | --- | --- |
  | USAspending.gov contract subawards, joined by UEI to the SAM.gov public entity extract | Prime–subcontractor firm pair | Fiscal years 2024–2026, one SAM.gov monthly snapshot | Industries linked as supplier and buyer through federal subcontracts |

- Item 6, a new R7.2 row, marked *(owner, Stage 14 design, 2026-11-18;
  [stage spec](usaspending-vendor-links.md))*:

  | Family | Built from | Units | Evaluates |
  | --- | --- | --- | --- |
  | Vendor links | USAspending subcontracts; SAM.gov entity NAICS | supplier industry → buyer industry, as firm shares | NAICS |

- **My call:** after R8.3, add: "USAspending subaward data and the SAM.gov
  public entity extract are public. Tables derived from them may contain UEI
  pairs. They read no Dun & Bradstreet Open Data field, use no SAM.gov record
  last updated before 2022-04-04, and publish no name or address." The plan adds
  this only if E6 passes.

**Only if no other stage has applied them first.** Stages 5, 14 and 15 share
these. The first of them to merge its build applies them (roadmap, Choices
made). Before it edits, the plan checks `main`. If the source spec's
introduction already contains "Evidence sources admitted by", these are done,
and the plan adds only Stage 14's items.

- Item 1 (introduction), item 2 (Core principle), and item 7 (`CLAUDE.md`,
  "from three sources"), with the Stage 2 spec's exact text.
- The wording change in item 3: "exactly three sources" becomes "three core
  sources".

Item 5 (R7.5 published aggregates) belongs to Stage 15.

## Left to the builder

- The split of the new code into modules, and the function names.
- The exact subaward header registry, once E4 records the headers.
- The extract layout registry, once E5 reads GSA's layout document.
- The USAspending request body and polling interval, from its API
  documentation.
- The Entity Extracts API request form for a monthly public file.
- Report key names beyond those named here.
- The README section with the command contract. Run pins in README and
  `CLAUDE.md` wait for a hardening stage, if the owner promotes one.
- The plan number. Several stages are planned in parallel, so take the next
  free number when the plan is written.

## Rollout and later-stage handoff

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 14 — on plan completion, tick the stage and re-validate later stages against what shipped.

- Software readiness (tests and the V12 fixture) comes before full-data
  acceptance. Do not tick Stage 14 on design or planning completion.
- The roadmap re-validation notes that Stage 14 did not consume the Stage 4
  concordance, and that the O6 cost note and `specs/deliverable-map.md` still
  say the account is missing (see
  [What the design session found](#what-the-design-session-found)).
- The shipped handoff gives:
  - **The resume after Stage 14:** the run ID, pin, snapshot label and extract
    month, so a replay build could use the same raw files, and the
    `n_unweighted` distributions in `report.json` for a minimum count.
  - **O18 (USAspending protocol section):** the firm counts, pair counts and
    marginals for any null model, the intra-group sensitivity label, the
    universe statement, join coverage, the diagonal, and the R8.4 exclusion
    from training and model selection.

After the owner approves this committed spec, use a fresh session with
writing-plans against `specs/usaspending-vendor-links.md`. This conversation is
not a dependency.
