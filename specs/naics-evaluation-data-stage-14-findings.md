# NAICS evaluation data — Stage 14 findings: USAspending vendor links

Status: Stage 14 in progress. Task 1 (document checks) is recorded below, read on
2026-11-18. E6 is open: two reads are outstanding (see "E6 status").

Stage 14 of `specs/naics-evaluation-data-roadmap.md` builds O6 from
`specs/usaspending-vendor-links.md` under `specs/plans/15-usaspending-vendor-links.md`.

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
| The owner's print of the SAM.gov terms, as the spec summarizes it (`specs/usaspending-vendor-links.md`, "The owner's print of the SAM.gov terms") | The owner said on 2026-11-18 that this print counts as the live read | 2026-11-18 |

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

### E6 status

E6 asks three things. The table says what the reads so far show.

| Question | Result so far |
|---|---|
| Does a statement restrict publishing aggregates or UEI-level rows derived from public subaward or public entity data? | None found in the reads above. The D&B limit covers D&B Open Data fields. UEI is not in that list, and the stage keeps none of those fields. |
| Does a statement forbid the API access the two acquisition commands use? | None found. The terms name the extracts API as a permitted route. USAspending's live terms are unread. |
| Does a statement forbid downloading the public extract, which carries name and address fields, for this use? | None found. **Interpretive point for the owner:** the D&B terms bar access to D&B Open Data "in bulk". The public extract carries those fields for records last updated before 2022-04-04. The stage never keeps, uses or publishes them. Whether downloading the extract at all is "access" is a reading, not a finding. |

Outstanding: the `sam.gov/data-services` statement and the live USAspending page. The
design never marks E6 passed. Task 9 does not start until the owner closes both reads or
waives them, and decides the interpretive point.

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
