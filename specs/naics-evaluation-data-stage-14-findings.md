# NAICS evaluation data — Stage 14 findings: USAspending vendor links

Status: Stage 14 in progress. Task 1 (document checks) is recorded below, read on
2026-11-18. The owner closed E6 on 2026-11-19 (see "E6 status"). Task 9 (acquisition and
preflight) is recorded in "Preflight", run on 2026-11-19.

Stage 14 of `specs/naics-evaluation-data-roadmap.md` builds O6 from
`specs/completed/usaspending-vendor-links.md` under `specs/plans/completed/15-usaspending-vendor-links.md`.

## Document checks

Task 1 reads documents as data. No code and no data file exist yet. Scratch files lived in
new directories under `/private/tmp/stage14-docs.*`, outside the repository and the data
root. Nothing is registered or saved under the data root. The findings hold field names,
enum values, code lines, counts and hashes. They hold no row value from any real file.

### Read log

| Source | Read how | Read on |
|---|---|---|
| `fedspendingtransparency/usaspending-api`, commit `c2b82690eb044e130afc80b546343a2af0b4af1a` (committed 2026-11-10T20:53:48Z) | `gh api repos/.../contents/<path>?ref=<commit>`; no usaspending.gov page opened, no API call | 2026-11-18 |
| `fedspendingtransparency/usaspending-website`, commit `55d52c6f16d5fec49b754fa273d26caf7687073e` (committed 2026-11-13T15:10:02Z), file `src/js/components/about/Licensing.jsx` | same | 2026-11-18 |
| `https://open.gsa.gov/api/sam-entity-extracts-api/` | `curl`, HTML read as data | 2026-11-18 |
| `https://open.gsa.gov/api/sam-entity-extracts-api/v1/openapi.yaml` | `curl` (not in the plan's list) | 2026-11-18 |
| `https://open.gsa.gov/api/entity-api/` | `curl` | 2026-11-18 |
| Layout spreadsheet `SAM Master Extract Mapping v6.0 Public File V2 Layout.xlsx`, 42,368 bytes, SHA-256 `b09d694eefbd621c63f64ec58062acde23271cc05874f5964283429f6883ec0d` | `curl` after the owner's go-ahead; read with `zipfile` and `xml.etree.ElementTree` under `python3 -I` | 2026-11-18 |
| Sample file `SAM_PUBLIC_MONTHLY_V2_20200414.ZIP`, 10,202,817 bytes, SHA-256 `db7a5edb06347fed79b8cbd6c95a425f4bc4c0fd5b7d23771662d62bc36bc8c6`, from `.../v1/sample-files/` | `curl` after the owner's go-ahead (not in the plan's list); read under `python3 -I`, with no row value printed | 2026-11-18 |
| The owner's print of the SAM.gov terms, as the spec summarizes it (`specs/completed/usaspending-vendor-links.md`, "The owner's print of the SAM.gov terms") | The owner said on 2026-11-18 that this print counts as the live read | 2026-11-18 |

### Step 1: USAspending API source

1. **Request fields.** The route is `POST /api/v2/bulk_download/awards/`. The view
   (`usaspending_api/download/v2/year_limited_downloads.py`) sets `constraint_type` to
   `year`, so the request reaches `AwardDownloadValidator._handle_custom_award_download`.
   The body takes `filters` (required), `columns` and `file_format` (`csv`, `tsv` or
   `pstxt`, default `csv`). `filters` takes `agencies`, `date_range`, `date_type`
   (`action_date` or `last_modified_date`), `prime_award_types` and `sub_award_types`
   (`grant` or `procurement`). An `agencies` entry whose `name` is `All`, in any letter
   case, is dropped. So `[{"type": "awarding", "tier": "toptier", "name": "All"}]` selects
   all agencies.
2. **Subawards only.** `prime_awards` joins `download_types` only when `prime_award_types`
   is non-empty. An absent or empty `prime_award_types` keeps it out. The code raises only
   when both type lists are absent. The validator never sets `include_data_dictionary` or
   `include_file_description`, so the generator adds no data dictionary or description
   file for this route. The ZIP holds the CSV parts only, as read from source. The real
   member list is a Task 9 data check.
3. **366-day check.** `get_date_range_length` returns `(end - start).days`. The request is
   refused when that value is greater than 366. FY2024 (2023-10-01 to 2024-09-30) gives
   365 and passes. FY2025 and FY2026 give 364.
4. **E4 filter read: passes.** `date_type: action_date` reaches
   `SubawardSearchTimePeriod`. That class maps `action_date` to `sub_action_date` and
   builds `sub_action_date >= start_date` and `sub_action_date <= end_date`. The generator
   also turns `date_signed` into `action_date` for subawards. So the filter uses the
   subaward's own action date. The subaward index drops rows whose `sub_action_date` is null
   (`subaward_search.py`, `bs.sub_action_date IS NOT NULL`). The index fiscal year is
   `YEAR(sub_action_date + interval '3 months')`, which equals the plan's fiscal-year rule.
   The `sub_award_types` filter is `terms` on `prime_award_group`, and the index sets that
   to `procurement` when `subaward_type = 'sub-contract'`.
5. **Download columns (contract subawards, the `d1` list in
   `download_column_historical_lookups.py`, key `subaward_search`).** These are hints.
   Task 9 data decide.

   | Need | Header name |
   |---|---|
   | Prime UEI | `prime_awardee_uei` |
   | Prime parent UEI | `prime_awardee_parent_uei` |
   | Subcontractor UEI | `subawardee_uei` |
   | Subcontractor parent UEI | `subawardee_parent_uei` |
   | Subaward action date | `subaward_action_date` |
   | Subaward amount | `subaward_amount` |
   | Subaward type | `subaward_type` |
   | Report identifier | `subaward_sam_report_id` |
   | Prime award NAICS | `prime_award_naics_code` |
   | Subaward NAICS | none in the `d1` list |

   The type column carries `sub-contract` for a contract subaward (the index maps it to
   `procurement`). The load SQL upper-cases the parent UEI and the report identifier in the
   index. Whether the CSV does too is a Task 9 data check.
6. **Status response.** `GET /api/v2/download/status?file_name=<name>` returns `status`,
   `message`, `file_name`, `file_url`, `total_size`, `total_columns`, `total_rows` and
   `seconds_elapsed`. The contract lists four `status` values: `failed`, `finished`,
   `ready`, `running`. The code returns the job's status name, and the lookup table holds
   eight: `ready`, `running`, `finished`, `failed`, `queued`, `resumed`, `created`,
   `uploading`. The fetched code sets only the first four. The `file_url` is an absolute S3
   URL in production and a local path only when the server runs locally. The contract's
   status example shows a relative path. A same-day repeat of an identical request returns
   the cached job, which may already be `finished`.
7. **Splitting.** One download splits into parts of at most 1,000,000 rows
   (`EXCEL_ROW_LIMIT`). Each part repeats the header. Parts are named
   `<data file name>_<n>.csv` with `n` from 1, and all are zipped together
   (`partition_large_delimited_file`, `split_and_zip_data_files`). The partition writer
   uses Python's `csv.writer` with the default `\r\n` line terminator. Quoted values may
   hold newlines.

**`REQUEST_BODY`** (FY2024 shown; Task 2 changes only the two dates for FY2025 and FY2026):

```json
{"filters": {"sub_award_types": ["procurement"], "date_type": "action_date",
             "date_range": {"start_date": "2023-10-01", "end_date": "2024-09-30"},
             "agencies": [{"type": "awarding", "tier": "toptier", "name": "All"}]},
 "file_format": "csv"}
```

This equals the plan's draft. Only the values differ by year.

### Step 2: Entity Extracts API page

- **Endpoint.** `https://api.sam.gov/data-services/v1/extracts`. The key parameter is
  `api_key`.
- **Request form for one public monthly V2 UTF-8 file** (the page's example, with the
  `charset` form):
  `https://api.sam.gov/data-services/v1/extracts?api_key={API KEY}&fileType=ENTITY&sensitivity=PUBLIC&frequency=MONTHLY&date=MM/YYYY&charset=UTF8`.
  Permitted `charset` values are `ASCII`, `UTF8` and `UTF-8`, default `ASCII`. `date` for
  monthly files is `MM/YYYY` (the page prints `MM/YYY`). A request by name uses
  `fileName=<name>` alone.
- **File names.** Monthly UTF-8 public: `SAM_PUBLIC_UTF-8_MONTHLY_V2_YYYYMMDD.ZIP`. The
  ASCII form is `SAM_PUBLIC_MONTHLY_V2_YYYYMMDD.ZIP`. The monthly files come out on the first
  Sunday of each month after 7 AM Eastern. The date in the name is the generation date.
  The `.dat` file inside carries the same date.
- **Contents.** The monthly files hold all active entities and entities that expired in
  the last 6 months.
- **Response.** The page says a successful response returns data in JSON format. It does
  not say whether the file comes directly or by redirect. The OpenAPI file lists status
  codes 200, 201, 401, 403 and 404 and no redirect. The plan's reader handles a ZIP body
  or one redirect. The real response form is a Task 9 observation.
- **Retention (E5).** The page does not say how many past monthly files are kept. Its
  examples use April 2022, and the change log removed older sample files. Unknown until
  Task 9.
- **Rate limits (E5).** A non-federal user with no role gets 10 requests a day. A
  non-federal user with a role gets 1,000. The plan assumes 10.
- **Key.** A user takes the personal `Public API Key` from the account details page on
  SAM.gov. A one-time password goes to the account's email address. The page states no
  expiry or rotation. The terms do (see Step 4).
- **Layout link.** `Public Extract Layout` is
  `v1/SAM Master Extract Mapping v6.0 Public File V2 Layout.xlsx` on the same host. The
  page change log says v3.3 (2023-06-27) updated the mapping to "Effective June 2023".

### Step 3: Extract layout (E5 read)

1. **Name and version.** `SAM Master Extract Mapping v6.0 Public File V2 Layout`. Sheets:
   `Data Element Mapping`, `STRING Clarification`, `Drop Down List`.
2. **Framing.** The spreadsheet does not state the delimiter, the quoting or the BOF and
   EOF lines. It names `END OF RECORD INDICATOR` (field 142, value `!end`). The sample file
   shows the framing below. It is a 2020 file, so it is evidence of the format and not of the
   live extract. Task 9 confirms each item on the real file, and a mismatch stops the stage.
   - Delimiter: `|`. Each data line holds exactly 141 `|`, so 142 fields. The last
     field is `!end`.
   - Quoting: none. 13 data lines hold a `"` inside a value, so a reader must not apply
     quote rules.
   - Line terminator: `\r\n`. The last line (EOF) has no terminator after it.
   - First line: `BOF PUBLIC V2 00000000 20200414 0084774 0005510`.
   - Last line: `EOF PUBLIC V2 00000000 20200414 0084774 0005510`.
   - The two counts in those lines (`0084774`, `0005510`) do not equal the 71,176 data
     lines of the sample, so a reader must not treat them as a record count.
   - One ZIP member, `SAM_PUBLIC_MONTHLY_V2_20200414.dat`, 42,392,570 bytes, ASCII.
3. **Fields per data record.** 142.
4. **Positions (1-based).**

   | Field | Position | Layout text |
   |---|---:|---|
   | `UNIQUE ENTITY ID` | 1 | `STRING`, `ALPHANUMERIC`, 12 |
   | `SAM EXTRACT CODE` | 6 | 1 character. Monthly values: `A` (active), `E` (expired) |
   | `LAST UPDATE DATE` | 10 | `STRING`, `YYYYMMDD`, 8 |
   | `D&B OPEN DATA FLAG` | 24 | `Y or N` |
   | `PRIMARY NAICS` | 33 | `STRING`, 6 |
   | `NAICS CODE COUNTER` | 34 | `Numeric`, 4 |
   | `NAICS CODE STRING` | 35 | `~` separated, up to 12,000. Each item is a 6-digit code plus a `Y`, `N` or `E` flag |
   | `ENTITY EVS SOURCE` | 122 | `STRING`, 10. Layout sample value `D&B` |
   | `END OF RECORD INDICATOR` | 142 | `!end` |

   In the sample, position 10 is 8 digits on every data line and position 33 is 6 digits
   or empty. Position 6 holds only `A` and `E`. Position 122 is empty on every sample line,
   so whether the live public extract fills it is a Task 9 check.
5. **D&B Open Data positions.** The terms list legal business name, street address, city,
   state or province, ZIP, country and county code. The layout has no county code field.
   `restricted_positions` for Task 5: 12 (legal business name), 16 and 17 (physical
   address lines), 18 (city), 19 (state or province), 20 and 21 (ZIP and ZIP+4) and 22
   (country code). The registry adds 13 to 15 (DBA name, division name, division number)
   to be safe. The reader never reads any of them.

### Step 4: Terms (E6 read)

Quotes are short. Nothing here is legal advice.

1. **SAM.gov terms and key rotation.** From the owner's print as the spec summarizes it:
   data access is allowed only through the APIs and extracts at `open.gsa.gov/api/` and
   `sam.gov/data-services`. Automated gathering and scraping of the website are prohibited.
   Public sharing is allowed only for data from public versions of the APIs. The personal
   key is never shared and is rotated every 90 days. D&B Open Data needs written
   attribution and no bulk sharing. NAICS is not in the D&B Open Data list.
2. **D&B terms on `open.gsa.gov/api/entity-api/`.** "D&B Open Data" means legal business
   name, street address, city, state or province, country and county, ZIP and country code
   elements. The data applies to entity records last updated before 4/4/2022. Users "shall
   not access, use or disseminate D&B Open Data in bulk", with "bulk" meaning amounts
   usable as an original source or substitute. D&B Open Data needs written attribution.
   Harvesting content from "the website", bots and spiders included, is prohibited. The
   Entity API shows the EVS source `D&B` on those records.
3. **Redistribution of public entity data.** The extracts page and the Entity API page hold
   no statement on redistribution beyond the D&B terms above. The statement on
   `sam.gov/data-services` is **not read** (the owner pastes SAM.gov pages, and has not).
4. **USAspending terms.** The live About and Terms page is **not read**. The owner said not
   to open it. As a partial substitute, the website's source file `Licensing.jsx` at the
   commit above says the data may be copied, adapted, redistributed or otherwise used for
   non-commercial or commercial purposes, "subject to the Limitation on Permissible Use of
   Dun & Bradstreet". The page also says the site code is CC0. This is repository text, not
   the live page.
5. **SAM.gov Terms of Use, full page.** The owner pasted the whole page on 2026-11-19, and
   the Restricted Data Use section a second time. It has seven sets of terms, and "all of
   the terms apply". Data Access: software may connect to "some SAM.gov data" with
   permission, and the page names the APIs and extracts at `open.gsa.gov/api/` and
   `sam.gov/data-services` as the routes. It bars bots and data-gathering tools that use
   the SAM.gov login, and bars web scraping. Public sharing is allowed only for data from
   public versions of APIs. Restricted Data Use: the plain explanation says D&B Open Data
   may not be *shared* in bulk. The legal language says a user shall not *access, use or
   disseminate* it in bulk, meaning amounts usable as an original source or a substitute
   for the D&B product. Users agree to both texts. D&B data other than D&B Open Data may
   not be used for commercial, resale or marketing purposes. Records that carry D&B data
   are those last updated before 2022-04-04 and they show EVS source `D&B`. The page holds
   no statement on UEI-level rows or aggregates beyond the public-version rule.

### E6 status

E6 asks three things. The table says what the reads so far show.

| Question | Result so far |
|---|---|
| Does a statement restrict publishing aggregates or UEI-level rows derived from public subaward or public entity data? | None found in the reads above. The D&B limit covers D&B Open Data fields. UEI is not in that list, and the stage keeps none of those fields. |
| Does a statement forbid the API access the two acquisition commands use? | None found. The terms name the extracts API as a permitted route. USAspending's live terms are unread. |
| Does a statement forbid downloading the public extract, which carries name and address fields, for this use? | None found. **Interpretive point for the owner:** the D&B terms bar access to D&B Open Data "in bulk". The public extract carries those fields for records last updated before 2022-04-04. The stage never keeps, uses or publishes them. Whether downloading the extract at all is "access" is a reading, not a finding. The owner decided it on 2026-11-19 (below). |

**Owner close-out (2026-11-19).** The owner pasted the full SAM.gov Terms of Use (Step 4,
item 5) and answered "Yes, close E6" to this question: close E6 with the Terms page as the
controlling statement and accept the D&B reading? A yes records three things:

1. The Terms page is the controlling statement on redistribution. It shows no restriction
   on publishing UEI-level rows or aggregates, beyond sharing only data from public
   versions of APIs. The stage uses the public extract only.
2. The owner waives the separate `sam.gov/data-services` page and the live USAspending
   terms page. The owner had already said not to open the USAspending page.
3. The owner accepts downloading and holding the raw public extract under `data/`
   (git-ignored, never shared) as consistent with the D&B terms. The reader keeps only the
   registered positions, no D&B Open Data field enters any frame, table, report or printed
   line, and no record last updated before 2022-04-04 gives an industry. The words of the
   two texts differ (the explanation says "share", the legal language says "access, use or
   disseminate"), and the owner's yes is the reading, not a finding.

E6 is closed by the owner's decision. Tests, the reads and this record do not mark it
passed. A later statement that meets an E6 stop condition reopens it.

### Step 5: Decision

No Owner Checkpoint 3 stop applies:

- E6 shows no statement that meets its stop condition in the reads made. It stays open as
  above.
- `action_date` filters on the subaward action date (Step 1, item 4).
- The layout has the UEI (position 1), the primary NAICS (33) and the last update date (10).

No owner question from Step 5 applies. Prime awards can be kept out of the ZIP, and the
request body equals the draft.

### Items for later tasks

- **Task 2.** The status values: the plan's rule raises on anything but `ready`, `running`,
  `finished` and `failed`. The lookup table holds `queued`, `resumed`, `created` and
  `uploading` too. Keep the rule, and test the "other value" path. A relative `file_url` is
  not a usable download URL, so refuse it.
- **Task 5.** Write `sam_extract_layout.json` from Step 3: 142 fields, `|`, no quotes, `\r\n`
  lines, BOF and EOF prefixes `BOF PUBLIC V2 00000000 ` and `EOF PUBLIC V2 00000000 `, no
  count check, no terminator after the last line, `!end` at 142, and the positions and
  restricted positions above.
- **Task 6.** Subaward CSV parts come as `<name>_<n>.csv` and may hold quoted newlines.
- **Task 9.** Check: the ZIP member list, the header names against Step 1 item 5 (the
  subaward NAICS column is absent from the `d1` list), the type value `sub-contract`, parent
  UEI letter case, the extract framing, EVS source values, and the retention and response
  form of the extract API.

## Preflight

Task 9 fetched the four raw files, read their headers and measured the real data with the
draft registry. All of it ran on 2026-11-19. The preflight script is read-only. It prints
counts, shapes and header names, and no row value. Scratch files lived under
`/private/tmp/claude-501/`, outside the repository and the data root. The registry is
`src/embedding_data/usaspending_subaward_headers.json`, committed with this section.

### Raw files

Snapshot label `2026-11-19`. Extract month `2026-10`. Every file is under `data/raw/` and
is recorded in `raw/manifest.jsonl`. Each SHA-256 below equals its manifest entry.

| File | Bytes | SHA-256 |
|---|---:|---|
| `sam/entity-extract/public-monthly-v2/2026-10/SAM_PUBLIC_UTF-8_MONTHLY_V2_20261005.ZIP` | 150,113,940 | `cbb7363ec16d774030805e3cebd53b6970c542014f51362b69d93556a7d063f6` |
| `usaspending/subcontracts/2026-11-19/FY2024/All_Subawards_2026-11-19_H12M46S47368855.zip` | 55,050,781 | `4926b10cf6bc055e814bbd12d9caac228674cb212608864fed14ea8c3c312e5b` |
| `usaspending/subcontracts/2026-11-19/FY2025/All_Subawards_2026-11-19_H12M27S45273786.zip` | 37,724,326 | `f3951726f1c6f350e47ec1c088da32fb5c9f7b0363a49a06af8097746ecc7c17` |
| `usaspending/subcontracts/2026-11-19/FY2026/All_Subawards_2026-11-19_H12M00S15714527.zip` | 27,255,097 | `c5d8b07a416274618fdc5a07db288cfcdc959a65f8618f85786e0ee2c1dc7fcb` |

The three subaward files came from `acquire-subawards` with the owner's go-ahead. The owner
chained FY2025 and FY2026 after FY2024, with the host-rule check before each. The extract
came from the owner's browser download, imported with `import-sam-extract` (a manual-import
entry).

**The extract was wrapped twice.** The owner's file
`SAM_PUBLIC_UTF-8_MONTHLY_V2_20261005.ZIP` (150,133,435 bytes, SHA-256
`d732f9753f87ed67eb53edcc7b057f2486817befeadf54d1b65f12c06019352d`) is an outer ZIP with
one member. That member is a ZIP of the same name (150,113,940 bytes), and `unzip -t` found
no error in it. With the owner's go-ahead, only the inner ZIP was imported, because it is
the file the layout describes. The outer file stays in `/private/tmp/sam-download/`, outside
the data root, and is not recorded.

**The real member name differs from the 2020 sample.** The inner ZIP holds one member,
`SAM_PUBLIC_UTF-8_MONTHLY_V2_20261005_897fa9aa54ba4f0fa78f34a447e93956.dat` (572,225,486
bytes). It has a `UTF-8` tag and a 32-character hex suffix. The Task 5 pattern refused it.
Task 9a changed the registry pattern to
`SAM_PUBLIC_UTF-8_MONTHLY_V2_[0-9]{8}_[0-9a-f]{32}\.dat` and pinned the refused forms.

**Preservation.** Before the first write, the manifest was 1,550,435 bytes with SHA-256
`956b9feff2fe1be7035f1ef4785e1485f4ba7f1a51cc25ceda4b55f0f20b0b1b`. After the four
writes it has 3,017 lines and 1,552,347 bytes, and its first 1,550,435 bytes still hash to
that value. `embedding-data audit` ran before and after: exit 0, 0 raw provenance
discrepancies each time.

### Members and registry

Each subaward ZIP holds one CSV member and no readme. All three members are valid UTF-8,
have no byte-order mark and have no ragged row.

| Year | Member | Bytes | Records |
|---|---|---:|---:|
| FY2024 | `All_Contracts_Subawards_2026-11-19_H13M50S12_1.csv` | 415,901,702 | 227,284 |
| FY2025 | `All_Contracts_Subawards_2026-11-19_H12M28S47_1.csv` | 298,568,503 | 177,666 |
| FY2026 | `All_Contracts_Subawards_2026-11-19_H12M01S15_1.csv` | 195,020,180 | 117,644 |

The header row has 118 cells and is identical in all three years. The registry pattern is
`All_Contracts_Subawards_[0-9]{4}-[0-9]{2}-[0-9]{2}_H[0-9]{2}M[0-9]{2}S[0-9]+_[0-9]+\.csv`.
It matches each member (`re.fullmatch`). The date format is `%Y-%m-%d`. The mapped cells are
the same in every year:

| Field | Header cell |
|---|---|
| `prime_uei` | `prime_awardee_uei` |
| `prime_parent_uei` | `prime_awardee_parent_uei` |
| `sub_uei` | `subawardee_uei` |
| `sub_parent_uei` | `subawardee_parent_uei` |
| `action_date` | `subaward_action_date` |
| `amount` | `subaward_amount` |
| `subaward_type` | `subaward_type` |
| `report_id` | `subaward_sam_report_id` |
| `prime_naics` | `prime_award_naics_code` |
| `subaward_naics` | none (missing in all three years) |

The download has no subaward NAICS column. The missing-field list is `subaward_naics`
alone, and it does not stop the stage. The `subaward_naics_equal_prime` diagnostic is
therefore null in every year. Four of the 118 header cells (the sixth to the ninth) hold
upper-case letters. Two of them (`COVID-19`) also hold a hyphen. The first `headers` run
withheld the header for that reason, and Task 9b relaxed the name guard to
`[A-Za-z][A-Za-z0-9_-]*`.

### E4: subaward reports

All three years use the same shapes. Every action date has the shape `9999-99-99`. The
preflight prints the ten most frequent amount shapes. They cover 99.3% of FY2024 rows,
99.2% of FY2025 rows and 99.4% of FY2026 rows, and each is an optional minus sign, digits,
a dot and two digits. The rarer shapes are not printed. No amount fails to parse
(`amount_unparseable` is 0 in each year). Every `subaward_type` is `sub-contract` (227,284,
177,666 and 117,644 rows).

| Measure | FY2024 | FY2025 | FY2026 | Total |
|---|---:|---:|---:|---:|
| Rows | 227,284 | 177,666 | 117,644 | 522,594 |
| `usable` | 227,218 | 177,666 | 117,644 | 522,528 |
| `uei_unusable` | 66 | 0 | 0 | 66 |
| `action_date_invalid` | 0 | 0 | 0 | 0 |
| `outside_window` | 0 | 0 | 0 | 0 |
| Blank prime UEI | 66 | 0 | 0 | 66 |
| Blank sub UEI | 0 | 0 | 0 | 0 |
| Malformed UEI (prime, sub) | 0, 0 | 0, 0 | 0, 0 | 0, 0 |
| Rows outside the file year | 0 | 0 | 0 | 0 |
| Duplicate rows | 0 | 0 | 0 | 0 |
| Distinct report IDs | 227,284 | 177,666 | 117,644 | 522,594 |
| Unparseable amounts | 0 | 0 | 0 | 0 |
| Negative amounts, in the ten printed shapes | 4,956 | 4,584 | 1,694 | 11,234 |

The 66 unusable reports all have a blank prime UEI and all sit in FY2024. The spec sums
every usable amount as a diagnostic, so negative amounts need no rule. The negative counts
are a lower bound, because the rarer shapes are not printed.

Rows by action month. Each file holds its own fiscal year, October to September.

| Month | FY2024 | FY2025 | FY2026 |
|---|---:|---:|---:|
| Oct | 23,209 | 18,744 | 12,892 |
| Nov | 17,329 | 15,203 | 10,309 |
| Dec | 17,690 | 14,364 | 10,960 |
| Jan | 21,500 | 14,604 | 9,143 |
| Feb | 22,103 | 13,480 | 9,870 |
| Mar | 20,375 | 14,722 | 11,269 |
| Apr | 18,122 | 14,622 | 10,893 |
| May | 17,139 | 13,949 | 9,897 |
| Jun | 17,290 | 12,671 | 10,247 |
| Jul | 16,429 | 16,249 | 9,726 |
| Aug | 17,122 | 12,202 | 6,508 |
| Sep | 18,976 | 16,856 | 5,930 |

The last two months of FY2026 are lower (6,508 and 5,930). The snapshot is 2026-11-19, so
late reports may still be missing. This is an observation. It is not a check.

### E5: extract and join

**Framing.** The BOF line is `BOF PUBLIC V2 00000000 20261005 0905712 0008359` and the EOF
line has the same text after `EOF`. Both match the committed prefixes. The first count
equals the 905,712 data lines. The 2020 sample's counts did not, so the reader still does
not use them as a record count. Every data line ends with `!end`.

**Skipped lines.** 905,436 data lines have 142 fields. 276 lines (0.030%) have 143 to 155
fields (143: 89, 144: 124, 145: 38, 146: 8, 147: 3, 148: 12, 154: 1, 155: 1). The layout
has no quoting, so a pipe inside a text field is the likely cause. That cause is not
proven. 239 of the 276 lines have a last update date on or after 2022-04-04 and 37 have an
invalid date. 249 are active and 27 are expired. They hold 273 distinct UEIs, and 16 of
these appear on subaward reports (one as a prime, 16 as a subcontractor). None of the 16
has a readable record elsewhere, so all 16 count as `not_in_sam`.

| Extract measure | Value |
|---|---:|
| Rows read | 905,436 |
| Skipped lines (`unreadable_lines`) | 276 |
| Registration status `A` / `E` / `A~E` | 820,073 / 85,362 / 1 |
| UEIs with 1 / 2 / 3 or more rows | 891,558 / 5,933 / 440 |
| Last update year 2023 / 2024 / 2025 / 2026 | 1 / 3 / 133,711 / 670,466 |
| Last update blank or invalid | 101,255 |
| EVS source blank / `D&B` / `E&Y` | 80,802 / 422 / 824,212 |
| Primary NAICS blank | 248,453 |
| Primary NAICS well formed (in the 2022 list) | 656,983 (656,932) |
| Primary NAICS malformed (read or unread rows) | 0 (0) |

The EVS source position is filled in the real extract. The 2020 sample left it empty.

**Firms.** 48,989 distinct UEIs sit on usable reports. 2,939 are primes and 47,676 are
subcontractors, so 1,626 are both.

| Firm status | All | Prime | Subcontractor |
|---|---:|---:|---:|
| `eligible` | 32,578 | 2,380 | 31,552 |
| `not_in_sam` | 8,671 | 59 | 8,630 |
| `dnb_era_record` | 6,457 | 498 | 6,211 |
| `naics_missing` | 1,283 | 2 | 1,283 |
| `naics_conflict` | 0 | 0 | 0 |
| `naics_not_2022` | 0 | 0 | 0 |

6,411 firms have a blank or invalid last update date on at least one row. The owner's D2
rule makes each of them `dnb_era_record`. No valid last update date is before 2022-04-04
(the earliest year is 2023). So the date rule fires on invalid dates alone, and EVS source
`D&B` explains the other 46 firms. This costs about 13% of all firms their industry. The
extract carries EVS source `D&B` on only 422 rows. The cost does not reach a trigger.

**The cost of D2, measured on 2026-11-22.** The owner approved a read-only check that
printed counts only. D2 alone makes 6,403 firms `dnb_era_record`. D2 alone means a blank or
invalid last update date, no valid date before 2022-04-04 and no EVS source `D&B` on any
row. Each of the 6,403 holds exactly one primary code, and that code is in the NAICS 2022
list. Each is an active (`A`) registration. So without D2 these firms would be `eligible`,
and the eligible firms would number 38,981 and not 32,578. The 1,272 expired firms all have
valid last update dates. The owner kept D2 on 2026-11-22. The cost stays: 6,403 firms with
one valid, current-looking code have no industry in this bundle. A later rule that counts a
blank date on an active registration as after the cutoff would give them back. That rule
needs the owner's decision and a new run.

**Join coverage** (eligible firms over firms of the role):

| Role | Pooled | FY2024 | FY2025 | FY2026 |
|---|---:|---:|---:|---:|
| Prime | 0.810 (2,380 of 2,939) | 0.814 (1,745 of 2,145) | 0.807 (1,708 of 2,116) | 0.816 (1,379 of 1,690) |
| Subcontractor | 0.662 (31,552 of 47,676) | 0.677 (20,112 of 29,716) | 0.708 (19,936 of 28,159) | 0.726 (17,082 of 23,522) |

**Trigger.** The share of firms with a primary code outside the 2022 list is 0 of 32,578
(0.0). By year it is 0 of 20,928 (FY2024), 0 of 20,808 (FY2025) and 0 of 17,825 (FY2026).
The plan's trigger is a share above 1% or a coverage below 0.5 for either role. Neither
holds.

### Outcomes of stops and asks

`measure` ended with `ok: true`, `stops: []` and `asks: []`. The plan's other stop
conditions:

- **A ZIP member that is not a subaward CSV.** None. Each subaward ZIP holds one CSV member.
- **A year that is not valid UTF-8.** None.
- **An extract that differs from the committed layout.** Two differences. (1) The member
  name had a hex suffix and the ZIP was wrapped twice. The owner approved importing the
  inner ZIP, and Task 9a fixed the pattern. (2) 276 data lines have the wrong field count.
  The owner decided on 2026-11-19: "Skip and count them." The reader skips such lines and
  counts them (`unreadable_lines`, `unreadable_firms`). This overrides the spec's rule that a
  wrong field count fails the build, for that rule only. Task 16 amends the spec text. The
  framing prefixes, the delimiter and the 142-field layout otherwise match.
- **A date or amount shape the registry cannot express.** None.
- **A missing optional field.** `subaward_naics`, recorded above. It does not stop.

The owner's words, on 2026-11-19: "Yes, close E6" (close E6, see "E6 status"), "Yes, import
inner ZIP" (import the inner ZIP only), "Approved for both" (the subaward downloads and the
member-pattern change), "Yes, chain both" (FY2025 then FY2026) and "Skip and count them"
(the 276 lines). The owner also chose the snapshot label `2026-11-19` and the extract month
`2026-10`. The owner left the extract path open ("Either one, just give me detailed
instructions"), and the controller chose the browser path.

Not checked here: the retention and response form of the extract API. The browser path was
used, so `acquire-sam-extract` was not run.

## Full-data build

The owner gave the go-ahead for the first build on 2026-11-21 and for the second on
2026-11-22. Each time the owner confirmed that no Stage 9 freeze window was open. The
host-rule checks before each build printed nothing.

The selected run is the second build, `r2`. The first build, `r1`, is superseded. The final
review found that `sam_raw.import_file` and `sam_raw.acquire` recorded any ZIP with a
fitting file name. A browser download of the extract can be a ZIP around the real ZIP. The
build refuses such a file, and a recorded raw file is never replaced, so the month would
be used up for good. The fix checks the ZIP member before the file is recorded. It changes
`sam_raw.py`, which is part of the bundle's recorded software, so `verify` now refuses `r1`
(exit 2). The owner chose "Fix now, rebuild" on 2026-11-22. `r1` stays on disk, unchanged,
and nothing cites it. The `report.json` of `r2` equals that of `r1` on every path. The
`inputs.json` files differ only in `execution`, `run_id` and `software`. So every count in
this document is the same for both runs.

The same fix wave closed the preflight script (`scripts/preflight_usaspending_sam.py`).
Its two extract tallies, the registration status and the EVS source, now count as coded
only inside a closed domain: `A`, `E`, `A~E` and blank for the status, and `D&B`, `E&Y` and
blank for the source. A layout that has drifted can no longer make the script print a name
or a UEI. `A~E` is a status code that the real extract holds once (see "E5: extract and
join"). The preflight is not part of the bundle's software.

| Item | Value |
|---|---|
| Run ID | `stage14_vendor_links_20261122_r2` |
| Detached pin (SHA-256 of `outputs.json`) | `248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be` |
| Snapshot label, extract month | `2026-11-19`, `2026-10` |
| Codes run and pin | `stage4_v11_20261013_r2`, `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a` |
| Built at | commit `1eddb3e`, `dirty: false`, 2026-11-22 19:43 UTC |
| Cost | `build` 29.6 s and 961 MB peak resident memory; `verify` 28.8 s and 955 MB; the bundle is 1,720 KB |

**Checks.** `verify` exited 0 with rows 689 (marginals), 107,994 (pairs), 8,307 (support)
and 16,614 (targets). The independent reconciler
(`scripts/reconcile_usaspending_vendor_links.py`, commit `9fd0a5b`) exited 0 with
`equal` true on all 87 checks, in 23.6 s and 375 MB. It reports 522,594 reports, 522,528
usable, 48,989 firms, 107,994 pairs, 8,307 cells and 276 unreadable lines. Preservation
passed: the manifest starts with the Task 9 baseline and holds exactly the four Stage 14
entries after it; `embedding-data audit` exited 0 with 0 raw provenance discrepancies; the
ITA summary has its recorded SHA-256 and size; and the Stage 4, Stage 6, Stage 10 and
Stage 5 bundles each have their pin and pass `verify_inventory`. The same checks passed
for `r1` before the fix. No replay of `r2` was built.

**On `r1`, the first reconciler run refused.** The reconciler read the extract at CRLF only, as the
layout note says. The delivered extract has 905,713 LF bytes, no CRLF and no CR. The
reconciler saw one line and stopped with `extract framing differs`. The build already
split at LF and dropped one CR, so it was right. The owner approved a fix on 2026-11-22.
The reconciler now ends a line at LF and drops one CR before it. This cost one more fix
round of Task 14 and no rebuild, because the reconciler is not part of the bundle's
software.
The layout note's `\r\n` is wrong for the delivered file.

**Reports by status** (all 522,594 reports, by file year): `usable` 522,528 (FY2024
227,218; FY2025 177,666; FY2026 117,644) and
`uei_unusable` 66 (all blank prime UEIs in FY2024). No report is `action_date_invalid` or
`outside_window`. There are no duplicate rows and no unparseable amounts.

**Firms.** 48,989 distinct UEIs on usable reports. The firm status counts and join coverage
are in "E5: extract and join" and did not change. `mixed_blank` and `code_not_in_string`
are both 0 on the real data, so the real run does not test the reading of either rule. The
code string has 3,181,441 entries. Each has six digits, and 38.5% (1,225,609) carry no flag
letter. The layout note says each item has a flag, so the rule reads the flag as optional
(the controller's ruling in Task 14).

**Pairs.** 107,994 distinct pairs: `eligible` 67,524, `sub_ineligible` 22,569,
`prime_ineligible` 17,722, `intra_group` 147 and `self_link` 32. The eligible pairs have
28,410 suppliers and 2,215 buyers. The sensitivity that keeps intra-group pairs has 67,629
pairs, 28,434 suppliers and 2,218 buyers.

**Targets.** 8,307 cells in 689 industries, two measures each, so 16,614 target rows.
7 cells exist only under the intra-group sensitivity. The diagonal (supplier and buyer in
the same industry) holds 88 cells and 6,180 pairs, 9.2% of all pairs. Partial counts over
the industries: 5,692 suppliers and 1,513 buyers also have a pair excluded as
`prime_ineligible` or `sub_ineligible` respectively.

**What is not claimed.** These are counts of reports and firms from one snapshot and one
monthly extract. They are not benchmarks and not a frame of firms or trade. Every target
keeps `size_gate_pending`. No headline minimum count (O18) and no protocol section exist yet.

## For the resume and O18

- **Run for a replay.** Run `stage14_vendor_links_20261122_r2`, pin
  `248943dc5603f8e035b0f1c49bf624a36ed702b70eb6b961a35b64ee97c7a2be`, snapshot `2026-11-19`,
  extract month `2026-10`. The three subaward files and the extract in `data/raw/` are
  manifest-recorded, so a replay build can use the same bytes.
- **Minimum count.** `n_unweighted` per cell has median 1 (buyer share) and 2 (supplier
  share), p90 6 and 11, maximum 260 and 1,101. 4,810 of 8,307 buyer-share cells and 4,025
  supplier-share cells have `n_unweighted` 1. `size_gate_pending` stays on every row.
- **Counts for a null model.** Firm counts, pair counts and the marginals (689 industries
  with `n_suppliers`, `n_buyers`, pair counts, partial counts and the intra-group
  versions) are in `report.json` and `vendor_link_marginals.parquet`.
- **Intra-group label.** 71 of the 16,614 rows carry `numerator:intra_group_sensitivity:true`.
  These are the rows whose count under the sensitivity differs from `n_unweighted`. Every
  row carries `size_gate_pending`. Intra-group pairs are excluded from the headline cells
  and counted in the sensitivity.
- **Universe.** The statement in `report.json` (`universe`) is the one the spec fixes.
- **Join coverage.** Prime 0.810 and subcontractor 0.662 pooled. The loss is mostly
  `not_in_sam` (8,671 firms) and `dnb_era_record` (6,457 firms).
- **Diagonal.** 88 cells and 6,180 pairs (9.2%).
- **R8.4.** No output of this stage may feed embedder training, curriculum, hard-negative
  mining or model selection. `vendor_link_pairs.parquet` holds UEI pairs and stays on this
  machine. The release of any table is the owner's decision (E6).
