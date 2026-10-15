# Stage 7: actual IPUMS extract verification

Measured 2026-10-15 against the five deliveries submitted on 2026-10-12.
This finding adopts the observed V4/V5 delivery identities, V6 industry scheme
matrix, V7 literal-CSV weight rule and the ACS/CPS portion of V10. It does not
adopt absent flag applicability, undocumented special-code mappings or later
analytical outputs. Whole-branch review and roadmap completion are separate gates.

The full-file schema and ordered-value comparisons pass for all five deliveries.
The public verifiers establish bundle integrity; the machine measurement status is
`unresolved`, preserving external source-interpretation requirements and missing
metadata. The evidence-backed decisions below are separate from those conservative
machine fields. No bundle was edited to turn an unknown into a passing result.

## Selected runs, software and preservation

The explicit production root is `/Users/lowell/Projects/embedding-data/data`.
Selection is `derived/ipums/stage7-selection.json`, with exactly the public
`delivery` and `parquet` fields for the following five profiles. All existing
Parquets were measured in place. No conversion recovery, new IPUMS submission,
upstream builder or historical data repair was used.

| Profile | Delivery | Rows | Columns | Parquet SHA-256 |
| --- | --- | --- | --- | --- |
| acs/core | usa_00001 | 3,206,859 | 147 | c07f9e7abe2c5dfdb8f9488a1f574d4cf49ab7945c3ad2ffc9daec5eaba47d10 |
| acs/five_year | usa_00003 | 7,456,212 | 148 | c5846bde221e7785051a4a4075aa6a71cc267a1f4497168a96df05d7c50f78fe |
| acs/vintage | usa_00002 | 1,575,420 | 146 | b6ffab7bd974f72b4fbc913f261779f5ce3145a915849bf92e946bb6b649240d |
| cps/asec | cps_00002 | 276,854 | 209 | fdb5dd128c1ff29df952d87257f96aee84b137a99e13ddd08d17ce373afbfa3d |
| cps/monthly | cps_00001 | 922,115 | 43 | a17ef2065d122a02fd188445404beadf9d003f11eb111e1d8b6ddee224875727 |

Parquet paths are `derived/<profile>/<delivery>.parquet`; raw triples are `raw/<profile>/<delivery>/{extract.json,<delivery>.xml,<delivery>.csv.gz}`. All fifteen raw input hashes follow.

| Profile | Raw filename | SHA-256 |
| --- | --- | --- |
| acs/core | extract.json | 5394b7d0cbcec71cecd849ec50d171e8c0c76abf2c56baefc8f66e7d203dc9f0 |
| acs/core | usa_00001.xml | ce129099372484716d693c106f0cdee92f4d7c7372acd0fbcd68ae1e7c28ad7d |
| acs/core | usa_00001.csv.gz | dbb8abfb4dbf452f09a12452d79dfb039fbde651af7f9a5bd875210c2805911c |
| acs/five_year | extract.json | 5c49e4c56bc0f404a83d61c01f8c32296e62aa643a874bdf4277119b8e1fce39 |
| acs/five_year | usa_00003.xml | 3658e08209eac0bc3432f50985bd99f91b7d6991f72e4c134be6088e4bffaa22 |
| acs/five_year | usa_00003.csv.gz | defca652f18e1e04d85e057b81bcd8b435902ca7a0dd689f8ba73c311662b227 |
| acs/vintage | extract.json | 0941b8409e55ed9d2d655b633e5bcb2c8660951cbcb0b28dd65fd055a1130cb4 |
| acs/vintage | usa_00002.xml | 0276884128a98e8ffbc7c230fa0666512aae833d644bbaf41dd2a99c301b5001 |
| acs/vintage | usa_00002.csv.gz | cda19c04e961aaa86e687d22a8f355905efe90a393f0c8d71de624556e71b8b8 |
| cps/asec | extract.json | 24f14ab93646a41c6aba35ee660443a7e100725a389a105f5710cc26d973954d |
| cps/asec | cps_00002.xml | 414aff1f8c55e1801796cc71fc68eba1d3ac37c50bf7f730c0f1028c49d219ca |
| cps/asec | cps_00002.csv.gz | fb5974a0fab2610f7f54f0a8da1711870a7dd1fa8ad1b56c2509ece0bad29213 |
| cps/monthly | extract.json | 39ac20b191d920d93bb2b927d80cb79043d2bd55a68db6c382634c1ffde47793 |
| cps/monthly | cps_00001.xml | 1cda03634b618a3551f1526432e2a60bd7d281e0fff04ba7b2398597110f4970 |
| cps/monthly | cps_00001.csv.gz | 16f8e81246c170de3209d403250702afadc1b3e070faafbef6cfd7b418535d81 |

Selected reference snapshot: `stage7_ipums_references_20261015_r2`, parser `ipums-public-references-v3`.
Selected measurement: `stage7_ipums_verification_20261015_r2`; replay: `stage7_ipums_verification_20261015_r2_replay`.
Software commit recorded by both runs: `e0222e265998ace2c71345eab08616acfbd07c0f`.
Python 3.14.0; ipumspy 0.8.2;
Polars 2.0.0; PyArrow 23.0.1;
HTTPX 0.28.1; fastexcel 0.21.0.
`uv.lock` SHA-256: `f57c3280a7c8286711bf6804ca4c02f0a19619c9db52f33941b9c5b996cba8e5`.
`inputs.json` freezes every relevant source-file hash and dependency version;
the Git commit is informational rather than a substitute for those file hashes.

| Inventory | SHA-256 |
| --- | --- |
| stage7_ipums_verification_20261015_r2/outputs.json | db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc |
| stage7_ipums_verification_20261015_r2/inputs.json | ac78654adf0682e41a7509bb1847aa5aa224c09f553805c8b8d745e23e7c522d |
| stage7_ipums_verification_20261015_r2_replay/outputs.json | 06ea5a11cf3144f0adc7bb99ddf1d91ad13608e2fefab0b0c0bf7a7e629f6d57 |
| stage7_ipums_verification_20261015_r2_replay/inputs.json | c2515368791833a4530e980ad09ecb2ba4ab060596847d40dc754e39e38738dd |
| stage7_ipums_references_20261015_r2/receipt.json | 3163968dde603ba53f807976dd09b9e40d73235a98c6f36e4e02c67ec4239c9c |

Both public `verify` invocations with the detached output pins exited 0 and
reported `status=verified`, `measurement_status=unresolved`. `compare-runs`
exited 0: all eight aggregate tables compare exactly in order, with equal report
and weight interpretation content. Input timestamps/run identities are allowed to
vary. Full-file fidelity was never replaced by sampling. Timing and durable
independent reconciliation evidence are recorded below before final adoption.

The before-state inventory froze 2,460 files: all selected raw/Parquet inputs and
all existing Stage 2–6 OSHA, codes, geography and targets files. The original 2,864
manifest entries remain an exact byte prefix. The audit and all frozen hashes
pass after measurement. Manifest growth is exactly 56 records: the diagnostic v2
snapshot's 25 originals + POST body + receipt (27), and the selected v3 snapshot's
27 originals + POST body + receipt (29). Request bodies and generated receipts
are separately accounted provenance records, not additional public originals.
The prior diagnostic snapshot and runs remain immutable.

Earlier runs `stage7_ipums_verification_20261015` and its `_replay` had exact
full-file parity and aggregate replay, but diagnosed an acceptance bug: legitimate
unnumbered REPWTP helpers were counted as unexpected numbered replicates. The
reviewed correction excludes only that helper; it cannot satisfy REPWTP80/160,
and malformed/extra replicate names still fail. The two extra documentary sources
required a fresh v3 registry and snapshot. The old outputs pins are
`62039dd143d14601610de7908b61eb04bc5c209b431d67d2213df3780bfd505f` and
`fbf7000134d0f4eda7b195d239b450f15fe9ae93d78f0c6e73beaab452f5332a`.
They belong to the old frozen software contract; current v3 verification is not a
claim to revalidate those historical v2 bundles.

Preserved selected upstream pins: Stage 2 summary
`6335cda7adb40a41c4a11d57d22048999449ac8d078a2ec0291f0198cd9136a8`;
Stage 4 output inventory `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`;
Stage 5 output inventory `5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d`;
Stage 6 preparation `84b29be17bae26e4cd7bb372108f95641936be4b73b794667957ed39de990d48`,
target `084292b6835eb09ce27ecc4a3aef03a6f43bfe7b39b815665c29190a431e2473`,
and replay `78fd21e37ba0c5b1cd396ff0961b557650788fdccd3c84a911e8c6c3b7fabe71`.

## Frozen public originals and source limits

Every cited public source below is the exact original in
`raw/references/ipums-verification/stage7_ipums_references_20261015_r2/`.
The table gives its registered URL and content hash; the receipt pins its filename,
size, method, body where applicable and provenance. The imports preserve bytes and
record local import time as a retrieval-time proxy. Direct BLS access previously
returned 403; native browser Save Link As preserved its original download bytes,
with original HTTP headers unavailable. The two protected ACS queries were already
acquired into private preflight storage. No credential was read and no network
request occurred during production import, cached acquire, measure or verify.
The two supplemental industry originals were acquired unauthenticated on
2026-10-15, inspected in TEMP, then imported after the closed registry extension.
The generated receipt is not an original and does not self-hash.

| Kind / frozen filename | Official source | SHA-256 |
| --- | --- | --- |
| acs_2023_b23025_metadata / acs_2023_b23025_metadata.html | [official original](https://api.census.gov/data/2023/acs/acs1/groups/B23025.html) | a3cb7d13a8160e1097643293e630eaee7063c3b93361071686b827141cd53181 |
| acs_2023_employment / acs_2023_employment.json | [official original](https://api.census.gov/data/2023/acs/acs1?get=NAME,B23025_004E&for=state:*) | d08a131f1afe94ea12e290e9f1baef11dc6769267b3c5dce100f1a5fd8b5ab7b |
| acs_2024_b23025_metadata / acs_2024_b23025_metadata.html | [official original](https://api.census.gov/data/2024/acs/acs1/groups/B23025.html) | cda68e39244518aaaa2f4a22314b8e9227e144a5cacd71029db5ac129c7ca8fb |
| acs_2024_employment / acs_2024_employment.json | [official original](https://api.census.gov/data/2024/acs/acs1?get=NAME,B23025_004E&for=state:*) | af9f67d4c0bf13c906ac7503dd315d37e19b41ae75cc263cbfc04bc22d0b982a |
| asec_2025_documentation / asec_2025_documentation.pdf | [official original](https://www2.census.gov/programs-surveys/cps/techdocs/cpsmar25.pdf) | 7f0cb9f791f2737ad12fd552b8cb201f4d1de266eac160322597344e73499fb4 |
| asec_2026_documentation / asec_2026_documentation.pdf | [official original](https://www2.census.gov/programs-surveys/cps/techdocs/cpsmar26.pdf) | 8f6d4c10ae5e720449ae23fdf739bb7812aff8102218d7c013be8ce737125107 |
| bls_a1_metadata / bls_a1_metadata.html | [official original](https://www.bls.gov/news.release/empsit.t01.htm) | 34186c7332fb9d44948f10f47746b5bd841a8dfdea9b480ea5434ad2cf04d37f |
| bls_series_metadata / bls_series_metadata.txt | [official original](https://download.bls.gov/pub/time.series/ln/ln.series) | 4e3dbfbed7cd0037983fec5a481fd9527592a6ab9da8e112e03ff583c02ef54c |
| census_industry_2017 / census_industry_2017.xlsx | [official original](https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2017-industry-code-list-with-crosswalk.xlsx) | 479161190aedc0a64529f930d34a21f18e1950609332defe4967e4e3f129c816 |
| census_industry_2022 / census_industry_2022.xlsx | [official original](https://www2.census.gov/programs-surveys/demo/guidance/industry-occupation/2022-Census-Industry-Code-List-with-Crosswalk.xlsx) | c9d2e004b2735c3975f0768e7dac704df6d2e0b36b24d33f5dbc7109cab5628c |
| cps_actsame / cps_actsame.html | [official original](https://cps.ipums.org/cps-action/variables/ACTSAME) | 771bc3b7bdf7235b9aca8bca0100f65ba88e59f7e163328a8cae4596a897ee59 |
| cps_asecwt / cps_asecwt.html | [official original](https://cps.ipums.org/cps-action/variables/ASECWT) | c387d30687ea0baccba8e2cb6533632df54c06385c51d7990f1ef46d22977498 |
| cps_earnwt / cps_earnwt.html | [official original](https://cps.ipums.org/cps-action/variables/EARNWT) | 8a3fc7e6322c0dcfad0a1367d35dbd4dffe1d5b25e44e2bdfb3da8e4308a6250 |
| cps_employment / cps_employment.json | [official original](https://api.bls.gov/publicAPI/v1/timeseries/data/) | 9d35973aab898c4609e52f22a4ae08c78b0e00f8cdecadb22a7d52ffcadb3779 |
| cps_empsame / cps_empsame.html | [official original](https://cps.ipums.org/cps-action/variables/EMPSAME) | b21016d96655db15549af725e21112fa039ae00eb6cd7226d4c0a69da5f5be85 |
| cps_ind / cps_ind.html | [official original](https://cps.ipums.org/cps-action/variables/IND) | b86fde7a5cb3bdb704756ff28928b669f0b0be81f5b7b8742a23d2bdf5a76823 |
| cps_indly / cps_indly.html | [official original](https://cps.ipums.org/cps-action/variables/INDLY) | 53250bcf9fa624235e9b0ca70a7f26a6a781751c994af8e5dfff68d77afcebcd |
| cps_industry_2025_codes / ind_2025_codes.shtml | [official original](https://cps.ipums.org/cps/codes/ind_2025_codes.shtml) | 28b64ba7cad2911d3c776c1610039b320c02533c469ae55337afa9552da3a816 |
| cps_jan2025_industry_documentation / IndustryCodes_Jan2025.pdf | [official original](https://www2.census.gov/programs-surveys/cps/methodology/IndustryCodes_Jan2025.pdf) | b990eb54c8e4af81e23f0cc94959b260b0cd448f5794d955152c49cb0f7ac7c1 |
| cps_lnkfw1mwt / cps_lnkfw1mwt.html | [official original](https://cps.ipums.org/cps-action/variables/LNKFW1MWT) | e5fe8c74f43b61cef7cdb4f7fb13bbb68ae5aa0264cb078219c92c75e96931a7 |
| cps_repwtp / cps_repwtp.html | [official original](https://cps.ipums.org/cps-action/variables/REPWTP) | ac1427dc6b22ef4ef4a9d38889cf2a73606a2fb93799f32e1e1e517f52a3fab5 |
| cps_uh_ind_a10 / cps_uh_ind_a10.html | [official original](https://cps.ipums.org/cps-action/variables/UH_IND_A10) | 172162cc700d8b5c35490387a5dfb0ed578832bc92778b27fbd1b76e332904f7 |
| cps_uh_indlyr_a10 / cps_uh_indlyr_a10.html | [official original](https://cps.ipums.org/cps-action/variables/UH_INDLYR_A10) | 7198f1e97d8b412a65c8ab4544f3e66eaaa0b84e81be0a745478b96969e2b90c |
| cps_wtfinl / cps_wtfinl.html | [official original](https://cps.ipums.org/cps-action/variables/WTFINL) | 58bdce16157389d5838a605104cfc4b379b173d47fe1da71a79170c551d1952d |
| usa_perwt / usa_perwt.html | [official original](https://usa.ipums.org/usa-action/variables/PERWT) | 7197daac939cdc47b70c349f9f25226bfb67052d203dd49acc97204d050e786b |
| usa_repwtp / usa_repwtp.html | [official original](https://usa.ipums.org/usa-action/variables/REPWTP) | 9c1f857740aaffbff0687365154b978fe8f11b074a071df79344ed929970d285 |
| usa_samples / usa_samples.html | [official original](https://usa.ipums.org/usa-action/samples/sample_ids) | 0dba4f5079774d6a1ccd3f1757436536a4551c917b0645d1fcd9137f3d11b6bc |

Actual workbook layouts were inspected before adoption: sheets
`2017 Census Industry Code List` and `2022 Census Ind Code List ` (trailing
space retained) contain 270 and 265 distinct industry leaves respectively,
including seven military categories. Their 273/268 four-character source rows
include repeated 0770/7570 headings and the separately retained 9920 special row;
these are not extra industry leaves. Complete original sheets remain frozen. The IPUMS supplemental HTML has one `dl.list-fixed-dt`, 266
unique four-digit code/label pairs and the heading “Industry Codes: 2025 onward
(2022 Census Classification Scheme)”; its code set is the 265 industry leaves in
the frozen 2022 workbook plus 9920. It does not contain 0000 or 9890.
These documentary references do not build an ACS parser or a CPS concordance.

## V4 and V5: observed sample and variable acceptance

The frozen USA catalog identifies `us2024c` as the 2020–2024 ACS five-year
sample. Its submitted definition, DDI SAMPLE label, delivered YEAR=2024 and
SAMPLE=202403 agree. MULTYEAR explicitly preserves all five component years.
This verifies sample identity, not native classification/geography for every
component respondent, nor an allocation procedure.

| Profile | Sample ID | YEAR | MONTH | SAMPLE | MULTYEAR | Rows |
| --- | --- | --- | --- | --- | --- | --- |
| acs/core | us2023a | 2023 | — | 202301 | — | 1,598,838 |
| acs/core | us2024a | 2024 | — | 202401 | — | 1,608,021 |
| acs/five_year | us2024c | 2024 | — | 202403 | 2020 | 1,194,039 |
| acs/five_year | us2024c | 2024 | — | 202403 | 2021 | 1,479,894 |
| acs/five_year | us2024c | 2024 | — | 202403 | 2022 | 1,575,420 |
| acs/five_year | us2024c | 2024 | — | 202403 | 2023 | 1,598,838 |
| acs/five_year | us2024c | 2024 | — | 202403 | 2024 | 1,608,021 |
| acs/vintage | us2022a | 2022 | — | 202201 | — | 1,575,420 |
| cps/asec | cps2025_03s | 2025 | 3 | — | — | 142,125 |
| cps/asec | cps2026_03s | 2026 | 3 | — | — | 134,729 |
| cps/monthly | cps2025_01b | 2025 | 1 | — | — | 48,398 |
| cps/monthly | cps2025_02s | 2025 | 2 | — | — | 47,937 |
| cps/monthly | cps2025_03b | 2025 | 3 | — | — | 46,469 |
| cps/monthly | cps2025_04b | 2025 | 4 | — | — | 47,202 |
| cps/monthly | cps2025_05s | 2025 | 5 | — | — | 46,614 |
| cps/monthly | cps2025_06s | 2025 | 6 | — | — | 46,692 |
| cps/monthly | cps2025_07b | 2025 | 7 | — | — | 46,613 |
| cps/monthly | cps2025_08s | 2025 | 8 | — | — | 48,585 |
| cps/monthly | cps2025_09s | 2025 | 9 | — | — | 48,338 |
| cps/monthly | cps2025_11s | 2025 | 11 | — | — | 44,788 |
| cps/monthly | cps2025_12s | 2025 | 12 | — | — | 44,630 |
| cps/monthly | cps2026_01s | 2026 | 1 | — | — | 44,347 |
| cps/monthly | cps2026_02b | 2026 | 2 | — | — | 45,445 |
| cps/monthly | cps2026_03b | 2026 | 3 | — | — | 43,791 |
| cps/monthly | cps2026_04s | 2026 | 4 | — | — | 45,416 |
| cps/monthly | cps2026_05s | 2026 | 5 | — | — | 45,967 |
| cps/monthly | cps2026_06s | 2026 | 6 | — | — | 45,349 |
| cps/monthly | cps2026_07s | 2026 | 7 | — | — | 44,957 |
| cps/monthly | cps2026_08s | 2026 | 8 | — | — | 45,483 |
| cps/monthly | cps2026_09s | 2026 | 9 | — | — | 45,094 |

Every requested variable and required automatic/detailed variable is present in
both DDI and Parquet, in delivered order; full raw-header parity passes. Required
missing names, unexpected selected rows, missing requested samples and missing
numbered replicates are all zero. Each ACS profile has REPWTP1–REPWTP80; ASEC has
REPWTP1–REPWTP160. The unnumbered REPWTP availability helper is constant 1 in all four deliveries, retained separately
and never treated as a weight or a substitute for the expansion. CLASSWLY is
accepted in ASEC and REGION in both CPS deliveries. INCWAGE_CPIU_2010 is delivered
for the requested inflation-adjustment option. These are the actual submissions'
acceptance results; earlier requests and future API behavior are not inferred.

Requested-name sets, excluding automatically delivered fields:

- `acs/core` (34): `AGE`, `CLASSWKR`, `COUNTYFIP`, `DEGFIELD`, `DEGFIELD2`, `EDUC`, `EMPSTAT`, `GQ`, `INCEARN`, `INCWAGE`, `IND`, `INDNAICS`, `MET2023`, `MET2023ERR`, `MIGMET23`, `MIGPLAC1`, `MIGPUMA1`, `MIGRATE1`, `OCC`, `OCCSOC`, `PERWT`, `PUMA`, `PWMET23`, `PWMET23ERR`, `PWPUMA00`, `PWSTATE2`, `REGION`, `REPWTP`, `SEX`, `STATEFIP`, `TRANTIME`, `TRANWORK`, `UHRSWORK`, `WKSWORK2`.

- `acs/five_year` (35): `AGE`, `CLASSWKR`, `COUNTYFIP`, `DEGFIELD`, `DEGFIELD2`, `EDUC`, `EMPSTAT`, `GQ`, `INCEARN`, `INCWAGE`, `IND`, `INDNAICS`, `MET2023`, `MET2023ERR`, `MIGMET23`, `MIGPLAC1`, `MIGPUMA1`, `MIGRATE1`, `MULTYEAR`, `OCC`, `OCCSOC`, `PERWT`, `PUMA`, `PWMET23`, `PWMET23ERR`, `PWPUMA00`, `PWSTATE2`, `REGION`, `REPWTP`, `SEX`, `STATEFIP`, `TRANTIME`, `TRANWORK`, `UHRSWORK`, `WKSWORK2`.

- `acs/vintage` (34): `AGE`, `CLASSWKR`, `COUNTYFIP`, `DEGFIELD`, `DEGFIELD2`, `EDUC`, `EMPSTAT`, `GQ`, `INCEARN`, `INCWAGE`, `IND`, `INDNAICS`, `MET2023`, `MET2023ERR`, `MIGMET23`, `MIGPLAC1`, `MIGPUMA1`, `MIGRATE1`, `OCC`, `OCCSOC`, `PERWT`, `PUMA`, `PWMET23`, `PWMET23ERR`, `PWPUMA00`, `PWSTATE2`, `REGION`, `REPWTP`, `SEX`, `STATEFIP`, `TRANTIME`, `TRANWORK`, `UHRSWORK`, `WKSWORK2`.

- `cps/asec` (25): `AGE`, `ASECWT`, `CLASSWKR`, `CLASSWLY`, `COUNTY`, `CPSIDP`, `CPSIDV`, `EDUC`, `EMPSTAT`, `INCWAGE`, `IND`, `INDLY`, `LABFORCE`, `METFIPS`, `MIGRATE1`, `MIGSTA1`, `OCC`, `OCCLY`, `REGION`, `REPWTP`, `SEX`, `STATEFIP`, `UHRSWORKLY`, `WHYMOVE`, `WKSWORK1`.

- `cps/monthly` (25): `ACTSAME`, `AGE`, `CLASSWKR`, `COUNTY`, `CPSIDP`, `CPSIDV`, `EARNWEEK2`, `EARNWT`, `EDUC`, `ELIGORG`, `EMPSAME`, `EMPSTAT`, `HOURWAGE2`, `IND`, `LABFORCE`, `LNKFW1MWT`, `METFIPS`, `MISH`, `OCC`, `PAIDHOUR`, `REGION`, `SEX`, `STATEFIP`, `UHRSWORK1`, `WTFINL`.

Automatic nonflag, nonreplicate names (the full ordered schemas and every numbered replicate are in `variable_inventory.parquet` and `inputs.json`):

- `acs/core`: `CBSERIAL`, `CLASSWKRD`, `CLUSTER`, `DEGFIELD2D`, `DEGFIELDD`, `EDUCD`, `EMPSTATD`, `HHWT`, `INCWAGE_CPIU_2010`, `MIGRATE1D`, `PERNUM`, `SAMPLE`, `SERIAL`, `STRATA`, `YEAR`.

- `acs/five_year`: `CBSERIAL`, `CLASSWKRD`, `CLUSTER`, `DEGFIELD2D`, `DEGFIELDD`, `EDUCD`, `EMPSTATD`, `HHWT`, `INCWAGE_CPIU_2010`, `MIGRATE1D`, `PERNUM`, `SAMPLE`, `SERIAL`, `STRATA`, `YEAR`.

- `acs/vintage`: `CBSERIAL`, `CLASSWKRD`, `CLUSTER`, `DEGFIELD2D`, `DEGFIELDD`, `EDUCD`, `EMPSTATD`, `HHWT`, `INCWAGE_CPIU_2010`, `MIGRATE1D`, `PERNUM`, `SAMPLE`, `SERIAL`, `STRATA`, `YEAR`.

- `cps/asec`: `ASECFLAG`, `ASECWTH`, `CPSID`, `INCWAGE_CPIU_2010`, `MONTH`, `PERNUM`, `SERIAL`, `YEAR`.

- `cps/monthly`: `ASECFLAG`, `CPSID`, `HWTFINL`, `MONTH`, `PERNUM`, `SERIAL`, `YEAR`.

ACS selection is general EMPSTAT=1, including armed forces until the V10 civilian
filter is applied. Monthly selection is LABFORCE=2; ASEC has no case selection
and retains all persons. All twenty requested monthly samples are observed;
October 2025 is neither requested nor observed. No replacement definition or new
real delivery is needed to settle the measured requested-name questions.

Known metadata versions are separate from source classifications. All five
legacy definitions have API `version:null`; that remains unknown. Each has root
`dataQualityFlags:true` and variable-level false settings, which are retained as
submitted metadata rather than overwritten. DDI schema version is 2.5; the
DDI dataset-version element has no text and date 2026-10-12. Citation prose names
IPUMS USA Version 16.0 (DOI 10.18128/D010.V16.0) or CPS Version 13.0
(DOI 10.18128/D030.V13.0). Manifest acquisition client is ipumspy 0.8.2. None of
these supplies the missing API extract version.

DDI structured dates are incomplete: core has only 2023, ASEC only March 2025,
and monthly only January 2025. The remaining requested periods are observed in
the data and named in study notes; they do not become inferred structured DDI
dates. CPS sample-type metadata stays unknown in the machine acceptance report,
and ASEC study-note matching stays unknown despite readable “ASEC 2025/2026”
notes. These metadata limits explain `unresolved`, independently of accepted names.

### Allocation flags and actual type/domain traps

Present Q-prefixed fields, as distinct from an assumed universal flag set:

- `acs/core`: `QAGE`, `QCLASSWK`, `QDEGFIELD`, `QEDUC`, `QEMPSTAT`, `QINCBUS`, `QINCEARN`, `QINCWAGE`, `QIND`, `QMIGPLC1`, `QMIGRAT1`, `QOCC`, `QPWSTAT2`, `QSEX`, `QTRANTIM`, `QTRANWOR`, `QUHRSWOR`, `QWKSWORK2`.

- `acs/five_year`: `QAGE`, `QCLASSWK`, `QDEGFIELD`, `QEDUC`, `QEMPSTAT`, `QINCBUS`, `QINCEARN`, `QINCWAGE`, `QIND`, `QMIGPLC1`, `QMIGRAT1`, `QOCC`, `QPWSTAT2`, `QSEX`, `QTRANTIM`, `QTRANWOR`, `QUHRSWOR`, `QWKSWORK2`.

- `acs/vintage`: `QAGE`, `QCLASSWK`, `QDEGFIELD`, `QEDUC`, `QEMPSTAT`, `QINCBUS`, `QINCEARN`, `QINCWAGE`, `QIND`, `QMIGPLC1`, `QOCC`, `QPWSTAT2`, `QSEX`, `QTRANTIM`, `QTRANWOR`, `QUHRSWOR`, `QWKSWORK2`.

- `cps/asec`: `QAGE`, `QCLASSWK`, `QCLASSWL`, `QEDUC`, `QEMPSTAT`, `QIND`, `QLABFORC`, `QMIGRAT1`, `QMIGRAT1G`, `QMIGST1B`, `QOCC`, `QOCCLY`, `QSEX`, `QUHRSWORKLY`, `QWHYMOVE`, `QWKSWORK`.

- `cps/monthly`: `QAGE`, `QEARNWEE`, `QEDUC`, `QEMPSTAT`, `QHOURWAG`, `QIND`, `QLABFORC`, `QOCC`, `QPAIDHOU`, `QSEX`, `QUHRSWORK1`.

ASEC has QOCCLY but no QINDLY. A missing allocation flag is unavailable evidence,
not an unallocated observation. DDI labels and applicability must be interpreted
per source/field; generic applicability remains unknown in `flag_coverage.parquet`.
For example ACS QIND=0 combines original entry and NIU, while CPS QIND=0 combines
no change, children and armed forces. CPS QOCCLY allocated is 1, whereas ASEC
QIND/QOCC allocated is 4. Monthly QIND/QOCC also contain codes 2, 3, 5, 6 and 7
(edit/allocation/longitudinal categories), so a shared nonzero Boolean is invalid.

QMIGRAT1 has the following complete observed partitions. “Unavailable” is retained
as missing evidence, not converted to false; the same name has different domains
between USA and CPS.

| Profile | Year / component | Present / dtype | Value | DDI label | Rows |
| --- | --- | --- | --- | --- | --- |
| acs/core | 2023 | True / String | null | unavailable | 1,598,838 |
| acs/core | 2024 | True / String | 0 | Not allocated | 1,448,662 |
| acs/core | 2024 | True / String | 4 | Allocated | 159,359 |
| acs/five_year | 2020 | True / Int64 | 0 | Not allocated | 1,090,770 |
| acs/five_year | 2020 | True / Int64 | 4 | Allocated | 103,269 |
| acs/five_year | 2021 | True / Int64 | 0 | Not allocated | 1,336,771 |
| acs/five_year | 2021 | True / Int64 | 4 | Allocated | 143,123 |
| acs/five_year | 2022 | True / Int64 | 0 | Not allocated | 1,424,988 |
| acs/five_year | 2022 | True / Int64 | 4 | Allocated | 150,432 |
| acs/five_year | 2023 | True / Int64 | 0 | Not allocated | 1,443,462 |
| acs/five_year | 2023 | True / Int64 | 4 | Allocated | 155,376 |
| acs/five_year | 2024 | True / Int64 | 0 | Not allocated | 1,448,662 |
| acs/five_year | 2024 | True / Int64 | 4 | Allocated | 159,359 |
| acs/vintage | 2022 | False / None | null | unavailable | 1,575,420 |
| cps/asec | 2025 | True / Int64 | 0 | NIU, or not changed | 108,547 |
| cps/asec | 2025 | True / Int64 | 1 | Migration status assigned from householder | 12,510 |
| cps/asec | 2025 | True / Int64 | 2 | Migration status assigned from spouse | 4,022 |
| cps/asec | 2025 | True / Int64 | 3 | Migration status allocated from matrix mob | 16,602 |
| cps/asec | 2025 | True / Int64 | 4 | Migration status assigned from parents | 444 |
| cps/asec | 2026 | True / Int64 | 0 | NIU, or not changed | 103,913 |
| cps/asec | 2026 | True / Int64 | 1 | Migration status assigned from householder | 11,527 |
| cps/asec | 2026 | True / Int64 | 2 | Migration status assigned from spouse | 3,875 |
| cps/asec | 2026 | True / Int64 | 3 | Migration status allocated from matrix mob | 15,012 |
| cps/asec | 2026 | True / Int64 | 4 | Migration status assigned from parents | 402 |

Core QMIGRAT1 is String: all 2023 values are null, while 2024 has strings 0/4.
The separate 2022 vintage extract omits the column entirely, even though the
five-year product has Int64 0/4 for MULTYEAR=2022. Product-specific evidence must
stay separate; five-year flags cannot backfill the annual delivery.

ACS INDNAICS stays String of delivered length 8. Edge-whitespace counts are
3,206,859 core; 1,561,054 vintage; 7,456,212 five-year. Alphabetic-token counts
are respectively 1,223,538; 593,404; 2,830,916. OCCSOC is String length 6 with no
edge whitespace and alphabetic counts 437,634; 211,905; 1,008,732. These aggregate
observations establish later parser hazards; no string was trimmed or interpreted
here. CPS IND/OCC/INDLY/OCCLY stay four-character strings in the existing Parquets.

## V6: field- and year-specific ASEC industry evidence

The source scheme and the delivered scheme are separate propositions. The frozen
2025 ASEC appendix A-1 (physical PDF p131) says 2017 industry codes starting
January 2020 and explicitly names both source PEIOIND and INDUSTRY. Its 2026
counterpart (physical p145, printed p1) says 2022 starting January 2025. The
older 2025 appendix is therefore inconsistent with the official update and
actual delivered discriminators; it is not silently relabeled or discarded.

The additional [Census January 2025 document](https://www2.census.gov/programs-surveys/cps/methodology/IndustryCodes_Jan2025.pdf),
physical p1, explicitly applies the 2022 industry classification starting January
2025 to **both** ASEC PEIOIND and INDUSTRY in the person record. This is direct
field-specific evidence; INDLY's reference job year is not inferred from YEAR or
from current-job IND. The frozen [IPUMS 2025-onward codebook](https://cps.ipums.org/cps/codes/ind_2025_codes.shtml)
identifies the delivered 2022 classification and labels all 33 discriminators.
The frozen IND and INDLY variable descriptions say original CPS industry coding
is retained; their comparability prose and INDLY's 2020+ link lag this update.
UH_IND_A10/UH_INDLYR_A10 also retain older 2020–2024 links despite their 2020–2026
titles. These stale links are documented limits, not evidence for a 2017 verdict.
DDI IND links the 2025+ list; DDI INDLY links the older 2020+ list. Neither DDI
contains category labels for actual IND/INDLY values, so no DDI-label proof is
claimed. Agreement of the explicit source-field update, original-code retention,
the current codebook and four discriminating actual frequency sets supports the
2022 native scheme for each measured cell.

The generic industry table deliberately keeps `native_vintage:null`,
`native_verdict:unresolved`, source/harmonization `external_required`. This manual
source reconciliation is the adoption record; machine aggregates remain immutable.
Shared code overlap alone would be inconclusive. All four cells contain the same
33 distinct 2022-only industry codes and zero 2017-only codes.

Raw lexical evidence also remains distinct from storage semantics: the aggregate
helper sees unpadded CSV strings of one to three digits as `malformed`; the full
conversion comparison confirms the documented zero-padding in existing Parquets.
There are no blank/null/nondigit/whitespace industry values in these four cells.
The following normalized-membership counts are an aggregate reconciliation using
that already verified padding rule, not a rewrite or a new production parser.

| Year / field | Rows | Raw short numeric | Zero / source NIU | Shared after padding | 2022-only rows | 9890 outside lists | Native scheme |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2025 IND | 142125 | 79020 | 71388 | 64007 | 6723 | 7 | 2022 |
| 2025 INDLY | 142125 | 77355 | 69665 | 65167 | 6954 | 339 | 2022 |
| 2026 IND | 134729 | 75402 | 68215 | 60212 | 6289 | 13 | 2022 |
| 2026 INDLY | 134729 | 73901 | 66679 | 61344 | 6420 | 286 | 2022 |

Raw unpadded shared-membership counts are respectively 56,375; 57,477; 53,025;
54,122. Raw-short and padded membership columns are alternative views and must
not be added. Zero is documented NIU in the source field dictionaries; its raw
short spelling does not supply a DDI special label. Code 9890 is outside both
full official industry leaf lists and outside the new IPUMS 2025+ list.
The 2025 ASEC appendix A-9 (physical p139) explicitly labels 9890 Military;
A-12/13 (physical pp142/143) repeats it in detailed/major recodes. Those anchors
support the 2025 source label. The 2026 appendix does **not** contain 9890, so
2026 continued-use meaning remains undocumented in the frozen sources. Retain
all four counts separately and do not invent a 2026 label, NAICS mapping or
concordance. This special-code limitation does not overturn the field's
2022 industry scheme, and does not authorize using that code in a later target.

Every observed 2022-only discriminator follows, with the official 2022 workbook
label. Counts are whole-delivery field/year aggregates.

| Code | 2022 official label | 2025 IND | 2025 INDLY | 2026 IND | 2026 INDLY |
| --- | --- | --- | --- | --- | --- |
| 4681 | Other motor vehicle dealers | 63 | 63 | 50 | 56 |
| 4691 | Automotive parts, accessories, and tire retailers | 222 | 233 | 199 | 211 |
| 4771 | Furniture and home furnishings retailers | 200 | 209 | 174 | 177 |
| 4796 | Electronics and appliance retailers | 181 | 194 | 152 | 145 |
| 4871 | Building material and supplies dealers, except hardware retailers | 471 | 493 | 411 | 399 |
| 4881 | Hardware retailers | 128 | 120 | 104 | 105 |
| 4891 | Lawn and garden equipment and supplies retailers | 158 | 164 | 147 | 146 |
| 4973 | Convenience retailers and vending machine operators | 155 | 166 | 182 | 166 |
| 4981 | Specialty food retailers | 98 | 110 | 118 | 108 |
| 4991 | Beer, wine, and liquor retailers | 85 | 89 | 58 | 59 |
| 5071 | Pharmacies and drug retailers | 369 | 375 | 308 | 297 |
| 5081 | Health and personal care, except pharmacies and drug, retailers | 220 | 234 | 185 | 193 |
| 5171 | Clothing and clothing accessories retailers | 371 | 381 | 328 | 367 |
| 5181 | Shoe retailers | 65 | 79 | 45 | 52 |
| 5191 | Jewelry, luggage, and leather goods retailers | 72 | 72 | 74 | 87 |
| 5276 | Sporting goods, and hobby, toy, and game retailers | 218 | 237 | 231 | 237 |
| 5281 | Sewing, needlework, and piece goods retailers | 28 | 26 | 12 | 15 |
| 5296 | Musical instrument and supplies retailers | 9 | 11 | 15 | 16 |
| 5371 | Book retailers and news dealers | 31 | 48 | 35 | 35 |
| 5382 | Department stores | 164 | 168 | 109 | 119 |
| 5392 | Warehouse clubs, supercenters, and other general merchandise retailers | 1377 | 1401 | 1342 | 1402 |
| 5471 | Florists | 55 | 52 | 53 | 53 |
| 5481 | Office supplies and stationery retailers | 42 | 34 | 33 | 36 |
| 5491 | Used merchandise retailers | 111 | 118 | 119 | 137 |
| 5571 | Gift, novelty, and souvenir retailers | 61 | 71 | 45 | 66 |
| 5581 | Other miscellaneous retailers | 271 | 264 | 236 | 247 |
| 5791 | Not specified retail trade | 213 | 193 | 224 | 187 |
| 6471 | Newspaper publishers | 44 | 52 | 34 | 39 |
| 6481 | Periodical, book, and directory and mailing list, and other publishers | 68 | 80 | 58 | 62 |
| 6671 | Broadcasting and content providers | 191 | 185 | 230 | 226 |
| 6781 | Web search portals and all other information services | 37 | 39 | 35 | 43 |
| 6871 | Monetary authorities-central bank, and commercial banking | 819 | 854 | 795 | 779 |
| 6881 | Credit unions, and savings institutions and other depository credit intermediation | 126 | 139 | 148 | 153 |

R4.6's 2022 industry requirement is retained; its conditional alternate wording
is unnecessary for these four verified field/year schemes. Stage 11 must still
implement full Census-to-NAICS candidate mappings, retain source-native fields,
handle specials and unresolved mappings explicitly, and apply any vintage
concordance actually needed by later inputs. No ASEC field is recoded merely
because its job refers to the previous calendar year.

## V7: CSV/DDI/Parquet weight interpretation

**Adopt literal CSV values, factor 1, for every delivered weight family and every
numbered replicate.** DDI implied-decimal exponents describe fixed-width notation;
they are separate from the decimals already written in CSV. Installed ipumspy
0.8.2 `readers.py` divides in its fixed-width branch but returns the CSV decimal
expansion unchanged. Only its source was inspected; no pandas microdata reader
was used. Exact lexical Decimal38 scans, DDI instructions, all-column ordered
Parquet parity and the frozen family-specific IPUMS documentation support this
rule. Employment closeness was not used to select a divisor.

`weight_diagnostics.parquet` has 416 individual rows: 400 numbered replicates,
four separately identified availability helpers and twelve other weights.
Every numbered replicate was scanned and checked, not merely the endpoints or
a representative. `weight_rules.json` retains its generic `production_adoption:
pending` and `external_required_per_weight_family`; this finding supplies the
external interpretation without mutating that machine record. Unknown API
versions have no bearing on CSV scale.

Nonreplicate weight diagnostics below are whole-delivery storage summaries, not
estimates of a common population. Blank and nonnumeric counts are zero for every
actual weight. Zero/negative/null values are not silently excluded.

| Profile | Weight | DDI exponent | CSV scale | Exact sum | Min | Max | Null | Zero |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| acs/core | HHWT | 2 | 1 | 329815685.0 | 1.0 | 2300.0 | 0 | 0 |
| acs/core | PERWT | 2 | 1 | 334347780.0 | 1.0 | 2300.0 | 0 | 0 |
| acs/five_year | HHWT | 2 | 1 | 158950326.0 | 1.0 | 713.0 | 0 | 0 |
| acs/five_year | PERWT | 2 | 1 | 162543024.0 | 1.0 | 986.0 | 0 | 0 |
| acs/vintage | HHWT | 2 | 1 | 160959505.0 | 1.0 | 3118.0 | 0 | 0 |
| acs/vintage | PERWT | 2 | 1 | 164087679.0 | 1.0 | 3118.0 | 0 | 0 |
| cps/asec | ASECWT | 4 | 2 | 676244535.11 | 96.94 | 25980.67 | 0 | 0 |
| cps/asec | ASECWTH | 4 | 2 | 655470520.91 | 114.56 | 20464.02 | 0 | 0 |
| cps/monthly | EARNWT | 4 | 4 | 3408410535.8753 | 0.0000 | 169764.2664 | 0 | 693555 |
| cps/monthly | HWTFINL | 4 | 4 | 3330467669.4886 | 150.0268 | 40047.1463 | 0 | 0 |
| cps/monthly | LNKFW1MWT | 4 | 4 | 2318680779.4062 | 0.0000 | 31630.9417 | 93432 | 271196 |
| cps/monthly | WTFINL | 4 | 4 | 3433083507.5580 | 148.3259 | 40047.1463 | 0 | 0 |

Every replicate in each following family has the same listed DDI exponent and observed CSV scale; sums range over individual replicate columns. Zero and negative counts sum over weight cells, not unique people.

| Profile | Replicates | DDI exponent | CSV scale | Minimum | Maximum | Exact sum range | Null | Zero cells | Negative cells |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| acs/core | 80 | 0 | 0 | -4419 | 8978 | 334267250 to 334596730 | 0 | 282495 | 3063 |
| acs/five_year | 80 | 0 | 0 | -892 | 1464 | 162532793 to 162637579 | 0 | 3488774 | 8830 |
| acs/vintage | 80 | 0 | 0 | -830 | 5350 | 164018292 to 164233447 | 0 | 131203 | 725 |
| cps/asec | 160 | 4 | 4 | -617.5357 | 54948.2039 | 676112835.6764 to 676378314.8735 | 0 | 0 | 132 |

Family evidence and use limits:

- USA PERWT and DDI identify person weights; HHWT identifies household weights
  requiring one representative per household. HHWT is repeated on person rows,
  so its displayed sum is not a household total. Core pooling divides person and
  replicate weights by two for annual-average estimates; five-year weights are
  not interchangeable with stacked annual component weights.
- USA REPWTP and CPS REPWTP documentation explicitly allow negative replicate
  values and limit their use to variance estimation. All observed negatives are
  retained. The 80/160 expansions and fixed-width exponents are separately
  checked; no SE helper or new variance estimate was built here.
- CPS WTFINL is the final person weight for monthly cross-sections. HWTFINL is
  household-specific and cannot be benchmarked by summing person records. The
  frozen WTFINL documentation supplies the monthly population/weight context.
- CPS EARNWT is used with ELIGORG for the outgoing-rotation earner study, not
  the whole labor-force extract. ELIGORG eligible/ineligible counts are
  196,192/725,923; EARNWT has 693,555 zero values. These are distinct domains.
- CPS LNKFW1MWT requires eligible adjacent-month links. It has 93,432 nulls:
  every selected September 2025 row (48,338) and September 2026 row (45,094),
  including all MISH groups. It also has 271,196 zeros. The absence is retained;
  no linked-pair denominator or linkage rate was computed.
- CPS ASECWT and `ASECWTH` are person/household
  supplement weights, including the ASEC sample design and oversample, rather
  than monthly WTFINL. The all-person ASEC contains children and military.
  These totals cannot validate annual employment without another explicit
  universe; no ASEC published-total benchmark is claimed.

Automatic household weights are supported by their delivered DDI descriptions;
requested person/linkage/earnings/replicate families also have the frozen public
variable originals above. No undocumented sentinel was removed and no arbitrary
magnitude threshold declared an extreme invalid. The high earnings/linkage and
replicate values remain data, with design-specific use limits. Dividing CSV by
DDI exponents would, for example, turn core PERWT 334,347,780 into 3,343,477.8;
that alternative is a recorded diagnostic, never an adopted correction.

### Job-change guard coverage

DDI EMPSAME uses 1=No, 2=Yes; ACTSAME uses 1=Yes, 2=No. EMPSAME counts are
11,973 No; 534,116 Yes; 191 refused; 111 don't know; 375,724 NIU. ACTSAME
counts are 522,057 Yes; 7,339 No; 28 refused; 91 don't know; 392,600 NIU.
MISH 1/5 have 227,363 EMPSAME NIU plus three delivered Yes exceptions (two/one).
Retain these source-universe exceptions rather than manufacturing a usable link.
The frozen documentation explains dependent interviewing and NIU gaps; a code
change alone is not job-change evidence. These are unlinked coverage counts,
not job-change rates, valid-pair shares or causal effects.

## V10: published employment comparisons

All displayed gaps are signed **measured minus published**, in persons; relative
gap is gap/published and shown as a percent. Source periods and residence scope
are explicit. No closeness threshold is an acceptance gate and no weights were
retuned. Exact Decimal sums and divisors remain in the Parquet comparison table;
rounded display percentages do not replace them.

ACS uses core PERWT, AGE>=16, EMPSTAT=1, EMPSTATD in 10/11/12. Armed-forces
13/14/15 and under-16 records are excluded, with no allocation, workplace or
future target filter. The core comparison excludes 27,471 military records. The comparator is each year's frozen ACS1 B23025_004E,
civilian employed residents age 16+, 50 states and DC. Pooled values are the
exact sum of 2023 and 2024 divided by two, for both measured and published.
Every one of the 153 annual/pooled state cells is matched; no eligible weight
is missing, and unexpected employment-status counts are zero. Published Puerto
Rico is retained separately as outside the selected geography: 1,185,629 (2023),
1,213,487 (2024), 1,199,558 (pooled), without a measured value or invented gap.
The table uses state FIPS to avoid ambiguous state names.

| State FIPS | Period | Measured persons | Published persons | Gap persons | Gap % |
| --- | --- | --- | --- | --- | --- |
| 01 | 2023 | 2,296,765 | 2,297,941 | -1,176 | -0.051176 |
| 01 | 2024 | 2,340,398 | 2,344,294 | -3,896 | -0.166191 |
| 01 | 2023–2024 pooled | 2,318,581.5 | 2,321,117.5 | -2,536 | -0.109258 |
| 02 | 2023 | 341,251 | 345,460 | -4,209 | -1.218375 |
| 02 | 2024 | 341,059 | 342,028 | -969 | -0.283310 |
| 02 | 2023–2024 pooled | 341,155 | 343,744 | -2,589 | -0.753177 |
| 04 | 2023 | 3,498,086 | 3,493,543 | 4,543 | 0.130040 |
| 04 | 2024 | 3,609,923 | 3,606,425 | 3,498 | 0.096994 |
| 04 | 2023–2024 pooled | 3,554,004.5 | 3,549,984 | 4,020.5 | 0.113254 |
| 05 | 2023 | 1,382,782 | 1,375,551 | 7,231 | 0.525680 |
| 05 | 2024 | 1,405,954 | 1,399,240 | 6,714 | 0.479832 |
| 05 | 2023–2024 pooled | 1,394,368 | 1,387,395.5 | 6,972.5 | 0.502560 |
| 06 | 2023 | 19,034,218 | 19,026,566 | 7,652 | 0.040217 |
| 06 | 2024 | 19,252,452 | 19,240,700 | 11,752 | 0.061079 |
| 06 | 2023–2024 pooled | 19,143,335 | 19,133,633 | 9,702 | 0.050707 |
| 08 | 2023 | 3,154,589 | 3,151,694 | 2,895 | 0.091855 |
| 08 | 2024 | 3,190,695 | 3,182,088 | 8,607 | 0.270483 |
| 08 | 2023–2024 pooled | 3,172,642 | 3,166,891 | 5,751 | 0.181598 |
| 09 | 2023 | 1,880,294 | 1,884,125 | -3,831 | -0.203330 |
| 09 | 2024 | 1,903,143 | 1,903,478 | -335 | -0.017599 |
| 09 | 2023–2024 pooled | 1,891,718.5 | 1,893,801.5 | -2,083 | -0.109990 |
| 10 | 2023 | 507,462 | 504,329 | 3,133 | 0.621221 |
| 10 | 2024 | 508,404 | 508,349 | 55 | 0.010819 |
| 10 | 2023–2024 pooled | 507,933 | 506,339 | 1,594 | 0.314809 |
| 11 | 2023 | 383,592 | 385,274 | -1,682 | -0.436572 |
| 11 | 2024 | 388,592 | 389,016 | -424 | -0.108993 |
| 11 | 2023–2024 pooled | 386,092 | 387,145 | -1,053 | -0.271991 |
| 12 | 2023 | 10,738,239 | 10,731,195 | 7,044 | 0.065640 |
| 12 | 2024 | 11,209,323 | 11,202,980 | 6,343 | 0.056619 |
| 12 | 2023–2024 pooled | 10,973,781 | 10,967,087.5 | 6,693.5 | 0.061033 |
| 13 | 2023 | 5,349,388 | 5,346,554 | 2,834 | 0.053006 |
| 13 | 2024 | 5,463,470 | 5,463,559 | -89 | -0.001629 |
| 13 | 2023–2024 pooled | 5,406,429 | 5,405,056.5 | 1,372.5 | 0.025393 |
| 15 | 2023 | 664,042 | 667,835 | -3,793 | -0.567955 |
| 15 | 2024 | 689,184 | 686,176 | 3,008 | 0.438371 |
| 15 | 2023–2024 pooled | 676,613 | 677,005.5 | -392.5 | -0.057976 |
| 16 | 2023 | 937,980 | 936,279 | 1,701 | 0.181677 |
| 16 | 2024 | 965,419 | 965,244 | 175 | 0.018130 |
| 16 | 2023–2024 pooled | 951,699.5 | 950,761.5 | 938 | 0.098658 |
| 17 | 2023 | 6,321,190 | 6,329,130 | -7,940 | -0.125452 |
| 17 | 2024 | 6,406,673 | 6,415,320 | -8,647 | -0.134787 |
| 17 | 2023–2024 pooled | 6,363,931.5 | 6,372,225 | -8,293.5 | -0.130151 |
| 18 | 2023 | 3,385,460 | 3,387,230 | -1,770 | -0.052255 |
| 18 | 2024 | 3,404,956 | 3,406,179 | -1,223 | -0.035905 |
| 18 | 2023–2024 pooled | 3,395,208 | 3,396,704.5 | -1,496.5 | -0.044057 |
| 19 | 2023 | 1,649,964 | 1,654,280 | -4,316 | -0.260899 |
| 19 | 2024 | 1,671,679 | 1,674,133 | -2,454 | -0.146583 |
| 19 | 2023–2024 pooled | 1,660,821.5 | 1,664,206.5 | -3,385 | -0.203400 |
| 20 | 2023 | 1,474,745 | 1,477,593 | -2,848 | -0.192746 |
| 20 | 2024 | 1,496,328 | 1,497,364 | -1,036 | -0.069188 |
| 20 | 2023–2024 pooled | 1,485,536.5 | 1,487,478.5 | -1,942 | -0.130557 |
| 21 | 2023 | 2,088,581 | 2,085,354 | 3,227 | 0.154746 |
| 21 | 2024 | 2,104,812 | 2,102,332 | 2,480 | 0.117964 |
| 21 | 2023–2024 pooled | 2,096,696.5 | 2,093,843 | 2,853.5 | 0.136281 |
| 22 | 2023 | 2,028,347 | 2,030,949 | -2,602 | -0.128117 |
| 22 | 2024 | 2,063,543 | 2,064,084 | -541 | -0.026210 |
| 22 | 2023–2024 pooled | 2,045,945 | 2,047,516.5 | -1,571.5 | -0.076752 |
| 23 | 2023 | 710,677 | 708,660 | 2,017 | 0.284622 |
| 23 | 2024 | 716,576 | 713,799 | 2,777 | 0.389045 |
| 23 | 2023–2024 pooled | 713,626.5 | 711,229.5 | 2,397 | 0.337022 |
| 24 | 2023 | 3,193,690 | 3,194,028 | -338 | -0.010582 |
| 24 | 2024 | 3,253,736 | 3,249,570 | 4,166 | 0.128202 |
| 24 | 2023–2024 pooled | 3,223,713 | 3,221,799 | 1,914 | 0.059408 |
| 25 | 2023 | 3,747,965 | 3,754,447 | -6,482 | -0.172649 |
| 25 | 2024 | 3,836,257 | 3,831,790 | 4,467 | 0.116577 |
| 25 | 2023–2024 pooled | 3,792,111 | 3,793,118.5 | -1,007.5 | -0.026561 |
| 26 | 2023 | 4,820,230 | 4,822,997 | -2,767 | -0.057371 |
| 26 | 2024 | 4,880,114 | 4,879,201 | 913 | 0.018712 |
| 26 | 2023–2024 pooled | 4,850,172 | 4,851,099 | -927 | -0.019109 |
| 27 | 2023 | 3,055,587 | 3,048,320 | 7,267 | 0.238394 |
| 27 | 2024 | 3,075,389 | 3,056,310 | 19,079 | 0.624250 |
| 27 | 2023–2024 pooled | 3,065,488 | 3,052,315 | 13,173 | 0.431574 |
| 28 | 2023 | 1,277,413 | 1,278,422 | -1,009 | -0.078925 |
| 28 | 2024 | 1,314,228 | 1,314,226 | 2 | 0.000152 |
| 28 | 2023–2024 pooled | 1,295,820.5 | 1,296,324 | -503.5 | -0.038841 |
| 29 | 2023 | 3,067,837 | 3,071,350 | -3,513 | -0.114380 |
| 29 | 2024 | 3,078,560 | 3,082,178 | -3,618 | -0.117385 |
| 29 | 2023–2024 pooled | 3,073,198.5 | 3,076,764 | -3,565.5 | -0.115885 |
| 30 | 2023 | 562,975 | 562,372 | 603 | 0.107224 |
| 30 | 2024 | 574,450 | 571,950 | 2,500 | 0.437101 |
| 30 | 2023–2024 pooled | 568,712.5 | 567,161 | 1,551.5 | 0.273555 |
| 31 | 2023 | 1,042,626 | 1,041,138 | 1,488 | 0.142921 |
| 31 | 2024 | 1,036,152 | 1,045,068 | -8,916 | -0.853150 |
| 31 | 2023–2024 pooled | 1,039,389 | 1,043,103 | -3,714 | -0.356053 |
| 32 | 2023 | 1,556,677 | 1,556,587 | 90 | 0.005782 |
| 32 | 2024 | 1,595,815 | 1,598,223 | -2,408 | -0.150667 |
| 32 | 2023–2024 pooled | 1,576,246 | 1,577,405 | -1,159 | -0.073475 |
| 33 | 2023 | 769,941 | 765,872 | 4,069 | 0.531290 |
| 33 | 2024 | 768,051 | 769,380 | -1,329 | -0.172736 |
| 33 | 2023–2024 pooled | 768,996 | 767,626 | 1,370 | 0.178472 |
| 34 | 2023 | 4,782,864 | 4,785,505 | -2,641 | -0.055187 |
| 34 | 2024 | 4,865,027 | 4,867,170 | -2,143 | -0.044030 |
| 34 | 2023–2024 pooled | 4,823,945.5 | 4,826,337.5 | -2,392 | -0.049561 |
| 35 | 2023 | 950,501 | 947,670 | 2,831 | 0.298733 |
| 35 | 2024 | 957,316 | 954,860 | 2,456 | 0.257210 |
| 35 | 2023–2024 pooled | 953,908.5 | 951,265 | 2,643.5 | 0.277893 |
| 36 | 2023 | 9,607,077 | 9,600,693 | 6,384 | 0.066495 |
| 36 | 2024 | 9,726,790 | 9,737,212 | -10,422 | -0.107033 |
| 36 | 2023–2024 pooled | 9,666,933.5 | 9,668,952.5 | -2,019 | -0.020881 |
| 37 | 2023 | 5,227,142 | 5,230,146 | -3,004 | -0.057436 |
| 37 | 2024 | 5,375,550 | 5,369,487 | 6,063 | 0.112916 |
| 37 | 2023–2024 pooled | 5,301,346 | 5,299,816.5 | 1,529.5 | 0.028859 |
| 38 | 2023 | 408,887 | 410,066 | -1,179 | -0.287515 |
| 38 | 2024 | 416,587 | 419,172 | -2,585 | -0.616692 |
| 38 | 2023–2024 pooled | 412,737 | 414,619 | -1,882 | -0.453911 |
| 39 | 2023 | 5,806,927 | 5,784,101 | 22,826 | 0.394633 |
| 39 | 2024 | 5,878,255 | 5,855,326 | 22,929 | 0.391592 |
| 39 | 2023–2024 pooled | 5,842,591 | 5,819,713.5 | 22,877.5 | 0.393104 |
| 40 | 2023 | 1,849,146 | 1,847,746 | 1,400 | 0.075768 |
| 40 | 2024 | 1,893,068 | 1,883,561 | 9,507 | 0.504735 |
| 40 | 2023–2024 pooled | 1,871,107 | 1,865,653.5 | 5,453.5 | 0.292310 |
| 41 | 2023 | 2,092,232 | 2,099,913 | -7,681 | -0.365777 |
| 41 | 2024 | 2,127,507 | 2,123,643 | 3,864 | 0.181951 |
| 41 | 2023–2024 pooled | 2,109,869.5 | 2,111,778 | -1,908.5 | -0.090374 |
| 42 | 2023 | 6,402,519 | 6,400,011 | 2,508 | 0.039187 |
| 42 | 2024 | 6,498,906 | 6,506,979 | -8,073 | -0.124067 |
| 42 | 2023–2024 pooled | 6,450,712.5 | 6,453,495 | -2,782.5 | -0.043116 |
| 44 | 2023 | 560,994 | 559,742 | 1,252 | 0.223674 |
| 44 | 2024 | 579,332 | 579,286 | 46 | 0.007941 |
| 44 | 2023–2024 pooled | 570,163 | 569,514 | 649 | 0.113957 |
| 45 | 2023 | 2,520,221 | 2,516,719 | 3,502 | 0.139149 |
| 45 | 2024 | 2,583,464 | 2,578,529 | 4,935 | 0.191388 |
| 45 | 2023–2024 pooled | 2,551,842.5 | 2,547,624 | 4,218.5 | 0.165586 |
| 46 | 2023 | 478,557 | 472,581 | 5,976 | 1.264545 |
| 46 | 2024 | 478,140 | 480,631 | -2,491 | -0.518277 |
| 46 | 2023–2024 pooled | 478,348.5 | 476,606 | 1,742.5 | 0.365606 |
| 47 | 2023 | 3,441,523 | 3,442,420 | -897 | -0.026057 |
| 47 | 2024 | 3,538,577 | 3,525,120 | 13,457 | 0.381746 |
| 47 | 2023–2024 pooled | 3,490,050 | 3,483,770 | 6,280 | 0.180264 |
| 48 | 2023 | 14,931,335 | 14,926,761 | 4,574 | 0.030643 |
| 48 | 2024 | 15,261,024 | 15,259,450 | 1,574 | 0.010315 |
| 48 | 2023–2024 pooled | 15,096,179.5 | 15,093,105.5 | 3,074 | 0.020367 |
| 49 | 2023 | 1,756,072 | 1,758,060 | -1,988 | -0.113079 |
| 49 | 2024 | 1,796,967 | 1,798,140 | -1,173 | -0.065234 |
| 49 | 2023–2024 pooled | 1,776,519.5 | 1,778,100 | -1,580.5 | -0.088887 |
| 50 | 2023 | 342,375 | 345,752 | -3,377 | -0.976712 |
| 50 | 2024 | 354,399 | 348,622 | 5,777 | 1.657096 |
| 50 | 2023–2024 pooled | 348,387 | 347,187 | 1,200 | 0.345635 |
| 51 | 2023 | 4,321,582 | 4,318,000 | 3,582 | 0.082955 |
| 51 | 2024 | 4,372,903 | 4,381,889 | -8,986 | -0.205071 |
| 51 | 2023–2024 pooled | 4,347,242.5 | 4,349,944.5 | -2,702 | -0.062116 |
| 53 | 2023 | 3,892,463 | 3,887,150 | 5,313 | 0.136681 |
| 53 | 2024 | 3,972,276 | 3,964,612 | 7,664 | 0.193310 |
| 53 | 2023–2024 pooled | 3,932,369.5 | 3,925,881 | 6,488.5 | 0.165275 |
| 54 | 2023 | 758,138 | 757,305 | 833 | 0.109995 |
| 54 | 2024 | 771,843 | 766,794 | 5,049 | 0.658456 |
| 54 | 2023–2024 pooled | 764,990.5 | 762,049.5 | 2,941 | 0.385933 |
| 55 | 2023 | 3,060,289 | 3,056,531 | 3,758 | 0.122950 |
| 55 | 2024 | 3,096,343 | 3,090,398 | 5,945 | 0.192370 |
| 55 | 2023–2024 pooled | 3,078,316 | 3,073,464.5 | 4,851.5 | 0.157851 |
| 56 | 2023 | 285,324 | 285,046 | 278 | 0.097528 |
| 56 | 2024 | 295,506 | 297,101 | -1,595 | -0.536854 |
| 56 | 2023–2024 pooled | 290,415 | 291,073.5 | -658.5 | -0.226232 |

Across ACS cells the signed gap ranges from −10,422 to +22,929 persons,
and relative gaps from −1.218375% to +1.657096%. Annual products and the pooled
core are compared only within matching definitions; the vintage and five-year
profiles are not relabeled as annual core benchmarks.

CPS monthly uses WTFINL, AGE>=16 and EMPSTAT in 10/12, civilian
noninstitutional employed residents, 50 states/DC. It excludes unemployed,
military and 2,069 under-16 records, with no allocation/earnings/linkage restriction.
The official BLS LNU02000000 series is not seasonally adjusted, in thousands of
persons; published values are multiplied by 1,000 before comparison. The series
metadata and frozen A-1 page establish units, universe and residence basis.
WTFINL differs from the composite estimator behind official totals; the measured
positive gaps are recorded, not tuned away. The public snapshot can contain
revisions and population-control updates unavailable at the original extract
release. Matching calendar periods does not establish a common publication vintage.

Every available month follows. October 2025 remains unavailable, not zero.
Its published observation carries footnote 9 (2025 lapse in appropriations).
January 2025 has footnote 1 for updated population controls; January 2026 has
footnote 12 for revised updated population controls. Other months have the
source's empty footnote object. There are no missing eligible weights or
unexpected status values in the measured monthly employment cells.

| Month | Measured persons | Published persons | Gap persons | Gap % | Footnote |
| --- | --- | --- | --- | --- | --- |
| 2025-01 | 163,379,760.1655 | 162,347,000 | 1,032,760.1655 | 0.636144 | [{"code": "1", "text": "Data affected by changes in population controls."}] |
| 2025-02 | 163,342,276.4885 | 162,544,000 | 798,276.4885 | 0.491114 | [{}] |
| 2025-03 | 163,953,811.5332 | 163,412,000 | 541,811.5332 | 0.331562 | [{}] |
| 2025-04 | 164,754,057.05 | 164,069,000 | 685,057.05 | 0.417542 | [{}] |
| 2025-05 | 163,993,643.8435 | 163,401,000 | 592,643.8435 | 0.362693 | [{}] |
| 2025-06 | 164,736,362.1957 | 163,883,000 | 853,362.1957 | 0.520714 | [{}] |
| 2025-07 | 165,014,946.6527 | 163,799,000 | 1,215,946.6527 | 0.742341 | [{}] |
| 2025-08 | 164,599,324.937 | 163,288,000 | 1,311,324.937 | 0.803075 | [{}] |
| 2025-09 | 165,053,351.9697 | 163,894,000 | 1,159,351.9697 | 0.707379 | [{}] |
| 2025-10 | unavailable | unavailable | unavailable | unavailable | [{"code": "9", "text": "Data unavailable due to the 2025 lapse in appropriations."}] |
| 2025-11 | 165,004,557.6285 | 164,066,000 | 938,557.6285 | 0.572061 | [{}] |
| 2025-12 | 164,469,406.2697 | 163,720,000 | 749,406.2697 | 0.457737 | [{}] |
| 2026-01 | 162,239,726.5672 | 161,670,000 | 569,726.5672 | 0.352401 | [{"code": "12", "text": "January 2026 estimates were revised to incorporate updated population controls. For more information, see www.bls.gov/cps/documentation.htm#pop."}] |
| 2026-02 | 162,542,131.3814 | 162,153,000 | 389,131.3814 | 0.239978 | [{}] |
| 2026-03 | 163,221,515.312 | 162,764,000 | 457,515.312 | 0.281091 | [{}] |
| 2026-04 | 163,475,434.4089 | 162,781,000 | 694,434.4089 | 0.426607 | [{}] |
| 2026-05 | 163,756,733.6199 | 162,897,000 | 859,733.6199 | 0.527777 | [{}] |
| 2026-06 | 163,241,023.974 | 162,722,000 | 519,023.974 | 0.318964 | [{}] |
| 2026-07 | 163,659,728.2384 | 162,800,000 | 859,728.2384 | 0.528089 | [{}] |
| 2026-08 | 163,603,854.1917 | 162,667,000 | 936,854.1917 | 0.575934 | [{}] |
| 2026-09 | 164,485,569.4457 | 163,439,000 | 1,046,569.4457 | 0.640343 | [{}] |

CPS gaps range from +389,131.3814 to +1,311,324.937 persons (+0.239978%
to +0.803075%). Employment comparison is evidence about the selected estimator
and universe, not accuracy, representativeness or an embedder benchmark.

## Aggregate artifact inventory

The selected canonical bundle has eight Parquets plus `inputs.json`, `report.json`,
`weight_rules.json` and detached `outputs.json`. The latter hashes the other eleven
files and excludes itself. Only aggregate and metadata artifacts are published;
no person rows or identifiers enter Git.

| Artifact | Rows where applicable | SHA-256 |
| --- | --- | --- |
| conversion_parity.parquet | 5 | 526ebb753ae05cff427f3280b53b1d50ca1594afd231505af6eea605d3281c7c |
| employment_comparisons.parquet | 177 | 861f378fc602d2b9b80cf215e19e0177c367f0a8ab4de29dc260ae21cdcc2da0 |
| flag_coverage.parquet | 1474 | 0ce43baa1401cde66d5675177e08251d2681cb18b6393602bc3341d484d1d4f1 |
| industry_frequencies.parquet | 1039 | b734f73f58c944daab6bc8f961ace97ff631cee9dceead53a0ec9d6cad0a5922 |
| inputs.json | — | ac78654adf0682e41a7509bb1847aa5aa224c09f553805c8b8d745e23e7c522d |
| report.json | — | 049caa2b0d82c4eb4152838c8ae3b591a8468ca7dfb7407412c0c899b3f375ad |
| sample_counts.parquet | 30 | fab8ba0afe8604019101028cd1b09131c56e760c59f00f92c68d8dc8469c4cf7 |
| variable_inventory.parquet | 693 | 6023da18ab8cf7b4ce8885fddd13acc8e6e38b9ef104d3f0645f380f07f28538 |
| verification_checks.parquet | 21 | bf4feb22eba027ee0bd9a06a4143783785188699c49d3c4793773d60cacef45d |
| weight_diagnostics.parquet | 416 | e43d11fa298031ef311a87019226208c4fbb1af8cac963de15e0cac14f0702fa |
| weight_rules.json | — | 608cd69afdc0feaf8c385609fc17bb7fbb3e72036e1699cd098559e4656bac70 |

## Reconciliation and final checks

An independent agent reconstructed expectations from all 13,437,460 raw rows
using stdlib and lazy Polars, without importing application measurement functions
or using application output values to construct expectations. Both final bundles
passed **10,941 assertions each**, with zero mismatches. Another **2,472 exact
CSV-to-derived Decimal comparisons** covered sums, extrema, null/zero/negative
counts for all **412 actual weight columns**. All 30 partitions, every replicate,
all 1,039 raw industry frequency rows, and all 177 employment comparison records
reconcile. The validator independently checked input/output/reference pins and
source-codebook agreement. Its verdict is PASS-WITH-WARNINGS: documented
source contradictions, special-code semantics and estimator/use limits remain.
This is independent numerical/source reconciliation, not a claim that all
machine interpretation fields have become known.

Durable aggregate-only evidence lives under the production root at
`derived/ipums/verification-evidence/stage7_ipums_verification_20261015_r2/`.
Twelve files are inventoried: the independent report, five reproducible scripts,
five aggregate JSON results and the explicit copy allowlist. `inventory.json`
excludes itself; its detached SHA-256 is
`b146f9d13efa9191050f856772191335ce2ab3b738d371fc6a02aa17c6daa719`.
The independent report SHA-256 is
`7c8f48853fbf7de275d74c97eb0b63914bca7c62b9a8728f0497f7ecd1d69424`.
Only explicitly allowlisted files were copied after matching every hash/size;
no decompressed microdata remains in this evidence directory.

Separate execution/source evidence is retained at
`derived/ipums/verification-evidence/stage7_ipums_verification_20261015_r2_execution/`.
Its detached inventory SHA-256 is
`1da5ab38786d582f095b744b56ff9fa0be57cf96673be0e8f2c09bd7800ca831`,
covering 44 files: original before-state inventory, public acquisition proof,
import/measurement/verifier/replay/audit logs, aggregate context results, source
page renders and executed scripts. It also preserves the supplemental acquisition
receipt and PDF text used by the independent source check. Its README explains
how to stage temporary copies of historical scripts and adapt their output paths
without writing into frozen evidence directories. Original public bytes remain
in the manifested v3 snapshot. All four diagnostic/selected bundle inventories
were separately checked against their recorded pins after the final measurements.
This is auxiliary
evidence and does not alter the canonical twelve-file verification bundles.

Commands used the explicit production root and the locked offline environment.
Primary timing was 85.45 seconds real / 500.61 user / 11.10 system; replay was
82.22 / 506.52 / 10.89 seconds. Peak resident memory was unavailable because the
platform denies the timing utility's kernel query; the successful final runs
used portable `/usr/bin/time -p`. Earlier `time -l` wrappers returned 1 after
successful diagnostic publication; their separate public verifier/compare logs
establish the diagnostic results. No memory figure is inferred.

```sh
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data ipums acquire-references stage7_ipums_references_20261015_r2 --data-dir /Users/lowell/Projects/embedding-data/data
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data ipums measure stage7_ipums_verification_20261015_r2 --references stage7_ipums_references_20261015_r2 --selection /Users/lowell/Projects/embedding-data/data/derived/ipums/stage7-selection.json --data-dir /Users/lowell/Projects/embedding-data/data
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data ipums measure stage7_ipums_verification_20261015_r2_replay --references stage7_ipums_references_20261015_r2 --selection /Users/lowell/Projects/embedding-data/data/derived/ipums/stage7-selection.json --data-dir /Users/lowell/Projects/embedding-data/data
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data ipums verify stage7_ipums_verification_20261015_r2 --outputs-sha256 db129a788daa312408f793df1b94fa3f211190a5541fc17ae87b96e84df913dc --data-dir /Users/lowell/Projects/embedding-data/data
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data ipums verify stage7_ipums_verification_20261015_r2_replay --outputs-sha256 06ea5a11cf3144f0adc7bb99ddf1d91ad13608e2fefab0b0c0bf7a7e629f6d57 --data-dir /Users/lowell/Projects/embedding-data/data
UV_CACHE_DIR=/private/tmp/embedding-data-uv-cache uv run --offline --locked embedding-data ipums compare-runs stage7_ipums_verification_20261015_r2 stage7_ipums_verification_20261015_r2_replay --data-dir /Users/lowell/Projects/embedding-data/data
```

These are executed provenance commands, not instructions to overwrite occupied
runs. A future measurement uses fresh IDs and the applicable software contract.
Ruff, offline lock check and Behave passed (one feature, two scenarios, ten steps).
The normal commit invokes the full coverage suite; its actual result is recorded
in the implementation handoff. Final whole-branch review and completion protocol
remain controller-owned. The five verified source-spec clauses are scoped to
these actual deliveries; other open markers and later requirements are retained.

## Consequences and limits for later stages

- Stage 8 can consume these exact ACS identities, ordered variable/replicate
  schemas, flag domains and delivery-specific missingness. It must implement
  mixed-depth code parsing and PUMA allocation later; literal strings, including
  whitespace/alphabetic categories, stay available beside derived mappings.
- Stage 9 inherits factor-1 CSV values and explicit pooling/universe rules. This
  verification supplies neither estimation/allocation helpers nor a new target.
- Stage 10 receives no new ITA behavior; all prior source/bundle pins remain intact.
- Stage 11 consumes the four-cell 2022 ASEC matrix, full Census references and
  special-code limits. Preserve 9890 outside-list status; its 2026 meaning is
  unresolved. Future mappings/concordances retain candidate sets and provenance.
  Monthly guard categories, MISH exceptions and missing linkage weights must
  be interpreted before any panel transitions are built.
- Stage 12 receives verified current/ASEC variable and weight coverage through
  later helpers. No metro eligibility, linkage rate, job-change flow or SE is
  established by these unlinked coverage measurements.
- Stage 13 receives reproducible aggregate evidence, source/version limits and
  the measured V4–V7/V10 portion. Citations, comparators, V9 thresholds and full
  V12 family construction remain later work. There is no causal or accuracy
  inference, and no target/ITA description may enter training or model selection
  for the embedder it evaluates.

Stage 7's roadmap checkbox, final whole-branch review and plan retirement are
controlled separately; this finding does not claim those workflow gates ran.
