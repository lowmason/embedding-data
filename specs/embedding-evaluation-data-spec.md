# Embedding evaluation data

> For agentic workers: REQUIRED NEXT SKILL: derive-roadmap — do not plan this
> spec directly and do not split it into per-subsystem plans.

This specification defines the evaluation data for `naics-embedder` and its
planned SOC and geography siblings: what is downloaded, from where, and how it
is transformed into benchmark targets that measure how industries, occupations,
and places relate in practice. It covers three sources — OSHA Injury Tracking
Application establishment summaries, American Community Survey microdata through
IPUMS USA, and Current Population Survey microdata through IPUMS CPS — plus the
code harmonization, geography hierarchy, and output tables they share. The
*evaluation protocol* that scores embeddings against these targets is
deliberately excluded and belongs to a successor spec (see Out of scope). Every
input is free to access and every output is an aggregate; no paid data and no
microdata release is required to run, test, or reproduce any requirement here.

## Design provenance

This spec synthesizes one design session, held 2026-10-12, which selected the
sources, samples, and variables, and the extract scripts and variable sheets
that session produced. Facts about each source were checked against its
documentation during the session.

**Locator scheme.** Requirements cite their basis by locator:

| Locator | Source | Standing |
| --- | --- | --- |
| **D** | Design session, 2026-10-12 | Binding for the choices made there: sources, samples, variables, universes. |
| **XA** | `acs_benchmark_extract.py`, with `acs_benchmark_samples_variables.xlsx` | Executable ACS extract definition. Dry-run tested; not yet submitted to IPUMS. |
| **XC** | `cps_benchmark_extract.py`, with `cps_benchmark_samples_variables.xlsx` | Executable CPS extract definition. Sample selection tested against a mocked catalog only. |
| **ITA** | OSHA ITA data page and Summary Data Dictionary (`osha.gov/itadata`) | Primary documentation for R2. |
| **USA** | IPUMS USA variable, geography, and terms pages (`usa.ipums.org`) | Primary documentation for R3. |
| **CPS** | IPUMS CPS variable and code pages (`cps.ipums.org`) | Primary documentation for R4. |
| **BLS** | BLS CPS technical documentation; Census CPS industry and occupation classification page | Classification change dates and code lists. |

**Provenance markers.** *(chosen; D)* marks a decision from the session.
*(verified; …)* marks a documented fact checked on 2026-10-12. *(implemented;
…)* marks a requirement already encoded in a script. *(added at synthesis)*
marks a requirement proposed while writing this spec and not discussed in the
session; treat these as proposals to accept or strike. *(open — …)* marks a fact
or number that only verification or measurement can settle.

**Adjudication status.** The session's choices were made interactively with the
project owner; there were no external reviews to adjudicate. The design
environment could not reach the IPUMS API, so every fact that only a live
request can confirm carries an *(open)* marker discharged in Verification.

**Scripts and spec.** XA and XC implement R3.5 and R4.5. Where a script and this
spec disagree, this spec governs and the script is corrected.

**Relationship to `naics-embedder`.** This spec adds evaluation data only. It
changes nothing about the embedder's architecture, curriculum, or training data,
and R8.4 keeps its tables out of all three.

**Naming.** Filed as `embedding-evaluation-data.md` rather than
`naics-benchmark.md`: the same tables evaluate the SOC and geography embedders,
and the file defines data, not the benchmark protocol.

## Problem

`naics-embedder` is built to respect the NAICS hierarchy — a Lorentz hyperboloid
projection and a structure-aware curriculum — so scoring it only against that
hierarchy rewards reproducing its own training signal. Two industries can sit
far apart in the tree and close together in practice: they hire the same
occupations, locate in the same places, and trade workers. The same holds for
occupations and places. Measuring that requires microdata, and four gaps stand
in the way:

- **No free establishment universe.** The closest public U.S. file, the Census
  synthetic Longitudinal Business Database, carries 3-digit SIC codes, no
  geography, and synthetic values, and is available only by application. Every
  free establishment file with real employment is the byproduct of a program
  with its own selection rule (D).
- **Codes arrive at mixed depth and mixed vintage.** ACS reports some industries
  and occupations only at aggregated levels; CPS reports Census codes with no
  NAICS or SOC strings; ITA has mixed three NAICS vintages since its 2023 data
  (USA, CPS, ITA).
- **Geography is not a tree.** Metropolitan areas cross state lines, non-metro
  counties belong to none, and the worker microdata identify PUMAs rather than
  counties (D, USA).
- **Imputed values look like observed ones.** The Census Bureau allocates
  missing codes, crosswalks older respondents' industry codes in multi-year
  files, and assigns 2020 PUMAs to pre-2022 respondents; CPS carries codes
  forward under dependent interviewing. Left unflagged, each manufactures
  relatedness (USA, CPS).

## Core principle

**Relatedness is observed, never assumed.** Every benchmark target is computed
from records in the three sources. No target is derived from the NAICS, SOC, or
geographic code structure, because that structure is what the embeddings are
trained on; the formal trees enter only as node and edge tables, used by tasks
that say they test hierarchy consistency. Values a source imputed — Census
allocations, crosswalked codes, allocated PUMAs, dependent-coded carry-forwards
— are flagged at ingestion and excluded from headline targets unless a
requirement says otherwise.

This principle governs code parsing (R5), geography (R6), and every target
family (R7).

## Requirements

### R1 — Sources and access

**R1.1** The required path draws on exactly three sources:

| Source | Unit | Years | Role |
| --- | --- | --- | --- |
| OSHA Injury Tracking Application (ITA), Form 300A summaries | Establishment-year | 2016–2025 | Employment, hours, NAICS, address, and employer-written industry text |
| American Community Survey (ACS) PUMS, via IPUMS USA | Person (worker) | 2023–2024 core | Staffing patterns, area mixes, worker profiles, commuting and migration flows |
| Current Population Survey (CPS), via IPUMS CPS | Person-month panel and ASEC | 2025 on | Job-change flows, last-year versus current job, job-related state migration |

ITA supplies establishments; ACS and CPS supply the workers behind
establishments' industries and occupations. *(chosen; D)*

**R1.2** All three sources are free. ITA files are U.S. government works
published for public use. IPUMS requires an account registered for each
collection and an API key, read from `IPUMS_API_KEY`; the key is never written
to a file, a log, or a manifest. *(verified; ITA, USA — key handling added at
synthesis)*

**R1.3** Register IPUMS USA with the statement agreed in the session (539
characters), and reuse it for IPUMS CPS with CPS named as the source:

> I am developing an evaluation benchmark for embeddings of industry (NAICS),
> occupation (SOC), and geographic hierarchies. Such embeddings are usually
> tested only against the formal code trees. From ACS PUMS industry and
> occupation codes, geography (PUMAs crosswalked to counties and metro areas),
> and worker characteristics, I will build aggregate measures of how industries,
> occupations, and places relate in practice and test whether embedding
> distances track them. Outputs are aggregate only; I will not attempt to
> identify individuals.

*(chosen; D)*

**R1.4** Raw downloads are immutable and kept as delivered: ITA zip and CSV
files; IPUMS `.csv.gz` data with its `.xml` DDI codebook and the submitted
definition (`extract.json`). A manifest records each raw file's source URL or
IPUMS sample IDs, extract number, retrieval time, SHA-256, and client version.
Transformations read raw files and write derived Parquet; nothing edits a raw
file. *(added at synthesis; `extract.json` implemented in XA, XC)*

### R2 — OSHA ITA establishment summaries

**R2.1** Acquire every Form 300A summary file from 2016 through the current year
from the ITA data page. The current-year file grows while submissions continue —
the 2025 file covers submissions through 2026-08-31 — so record its through-date
and re-acquire until OSHA moves it to the historical list. *(verified; ITA)*

**R2.2** **ITA is a program-selected subset, not a frame.** Filing is required
of establishments with 250 or more employees outside the partially exempt
industries and of those with 20–249 employees in a designated industry list;
about 385,000 establishments filed for 2023. OSHA retains filings from
establishments that were not required to submit and does not validate employee
counts. Every ITA target states this universe, and none is described as
representative of all establishments. *(verified; ITA)*

**R2.3** Stack all years into one establishment-year table keyed on
`year_filing_for`, harmonizing three dictionary changes introduced with the 2023
data: `establishment_id`, added to link summary and case-detail files; the split
of size code `2` into `21` and `22`; and NAICS codes that may be 2012, 2017, or
2022 vintage, identified by `naics_year`. *(verified; ITA)*

**R2.4** Retain `establishment_name`, `establishment_id`, `ein`, `company_name`,
`street_address`, `city`, `state`, `zip_code`, `naics_code`, `naics_year`,
`industry_description`, `establishment_type`, `size`,
`annual_average_employees`, `total_hours_worked`, and `year_filing_for`. Injury
and illness counts stay in the raw files; they are not benchmark inputs.
*(chosen; D)*

**R2.5** Map every NAICS code to the 2022 vintage under R5.4. ITA validates
codes as six-digit at submission and publishes invalid codes as missing; missing
stays missing and is never imputed from the description. *(verified; ITA —
no-imputation rule added at synthesis)*

**R2.6** `industry_description` is the employer's own free text from the 300A
form, up to 300 characters. Keep the original string and add a normalized
matching key (Unicode and whitespace normalized, case folded). Flag empty and
placeholder entries, and entries identical to an official NAICS title, since a
copied title is not independent text. Deduplicate on employer (`ein`, else
`company_name`) and normalized description before building pairs, because
multi-unit filers can stamp one description on every establishment. Expect
descriptions coarser than their codes — one posted 300A pairs "Healthcare" with
621610 — so every pair carries the full 2022 code path (R5.2) and can be scored
at each level. *(chosen; D)* What the field actually contains — how often it is
empty, copied, or repeated within an employer — is *(open — resolved by
verification, not argument, discharged by V1)*.

**R2.7** Link establishments across years. From the 2023 data,
`establishment_id` is the candidate key; earlier years link on `ein` plus
normalized name and address. `ein` with `company_name` also reconstructs
multi-unit firm structure for R7.2. Whether `establishment_id` persists across
years for the same establishment is *(open — resolved by verification, not
argument, discharged by V2)*.

**R2.8** Assign each establishment a county from its address, then derive state,
CBSA, division, and region under R6. The method — a ZIP-to-county crosswalk or
geocoding the street address — is *(open — resolved by verification, not
argument: match rate and county agreement on a sample decide it, discharged by
V3)*. *(added at synthesis)*

**R2.9** Flag, never drop, implausible records: hours per employee outside a
plausible annual range, zero or missing employment, and establishments whose
size and industry place them outside the filing rule. *(added at synthesis)*

### R3 — ACS microdata through IPUMS USA

**R3.1** **Core samples: 2023 ACS (`us2023a`) and 2024 ACS (`us2024a`),
pooled.** Both are natively coded on all three layers: industry on 2022 NAICS,
occupation on 2018 SOC, and geography on 2020 PUMAs, in use from 2022 responses
on. Add the 2025 ACS when IPUMS posts it. *(chosen; D; verified USA)*

**R3.2** **Large-n alternative: the 2020–2024 ACS 5-year sample.** It is about
2.5 times the size of the pooled core, but its consistency is partly imputed:
the Census Bureau crosswalks earlier respondents' industry codes into the final
year's scheme, and since the 2023 5-year file it assigns pre-2022 respondents a
2020 PUMA by an undocumented method. Use it only for cells the core cannot
support, keep `MULTYEAR`, and report every result built on it next to the same
result on its 2023–2024 records. *(chosen; D; verified USA)* The IPUMS sample
ID, expected to be `us2024c`, is *(open — resolved by verification, not
argument, discharged by V4)*.

**R3.3** **Vintage comparator, optional: 2022 ACS (`us2022a`).** It shares the
core's SOC and PUMA vintages but uses 2017 NAICS, which makes it a test of
whether NAICS embeddings hold up across a vintage change. *(chosen; D)*

**R3.4** Exclude Puerto Rico Community Survey samples; Puerto Rico is not in a
census region or division. *(chosen; D)*

**R3.5** The extract is employed persons (general `EMPSTAT` code 1), delivered
as CSV with IPUMS data quality flags and an inflation-adjusted wage,
`INCWAGE_CPIU_2010`:

| Role | Variables |
| --- | --- |
| Weights | `PERWT`, `REPWTP`; `MULTYEAR` in the 5-year sample only |
| Industry | `INDNAICS`, `IND` |
| Occupation | `OCCSOC`, `OCC` |
| Universe | `EMPSTAT`, `CLASSWKR`, `GQ` |
| Worker profile | `EDUC`, `DEGFIELD`, `DEGFIELD2`, `INCWAGE`, `INCEARN`, `UHRSWORK`, `WKSWORK2`, `AGE`, `SEX` |
| Residence geography | `STATEFIP`, `REGION`, `PUMA`, `COUNTYFIP`, `MET2023`, `MET2023ERR` |
| Workplace geography | `PWSTATE2`, `PWPUMA00`, `PWMET23`, `PWMET23ERR`, `TRANWORK`, `TRANTIME` |
| Migration geography | `MIGRATE1`, `MIGPLAC1`, `MIGPUMA1`, `MIGMET23` |

*(chosen; D; implemented XA)* Whether the IPUMS API accepts every name,
including the replicate-weight request, is *(open — resolved by verification,
not argument, discharged by V5)*.

**R3.6** The headline universe is civilian employed persons at their current
job, all classes of worker; `EMPSTATD` removes the armed forces, which general
code 1 includes. A second universe, private wage and salary workers
(`CLASSWKRD`), is built for comparison with establishment-based statistics.
*(chosen; D — second universe added at synthesis)*

**R3.7** When pooling *k* one-year samples, divide `PERWT` and
`REPWTP1`–`REPWTP80` by *k* for annual-average totals; shares are unaffected.
Standard errors use the replicate weights with the successive-difference factor
4/80. *(chosen; D)*

**R3.8** Exclude records whose `IND` or `OCC` was allocated by the Census
Bureau, as marked by the Q-prefixed flags, from headline targets, and build each
target a second time with them included as a sensitivity check. *(chosen; D —
Core principle)*

**R3.9** Parse `INDNAICS` and `OCCSOC` under R5.3, reading both as strings.
*(chosen; D; implemented XA)*

**R3.10** Keep three geographic roles distinct: residence (`STATEFIP` with
`PUMA`), workplace (`PWSTATE2` with `PWPUMA00`), and residence one year ago
(`MIGPLAC1` with `MIGPUMA1`). Area-by-industry and area-by-occupation mixes use
workplace geography, because that is where establishments are. A worker whose
`TRANWORK` is work-from-home has a workplace coded as home and is excluded from
workplace mixes by default. *(chosen; D)*

**R3.11** Never assign metros with `MET2023` alone. It names a metro only where
that metro holds a majority of the PUMA's population, and it omits MSAs whose
combined match error reaches 15%. Allocate with the IPUMS crosswalks of every
PUMA–MSA intersection and its population, and with population-weighted
PUMA-to-county factors (Geocorr 2022) for counties. *(verified; USA)*

### R4 — CPS microdata through IPUMS CPS

**R4.1** **Monthly panel: every basic monthly sample from January 2025.**
January 2025 is the first month on the 2022 Census industry codes, and
occupation has used the 2018 Census codes since January 2020, so the window
matches the ACS core's vintages. Sample IDs come from the IPUMS sample catalog,
never a hardcoded list: monthly IDs end in `b` or `s` depending on whether a
supplement ran, and October 2025 was never collected and will not be. *(chosen;
D; verified BLS, CPS; implemented XC)*

**R4.2** **ASEC: every ASEC from 2025 on.** The 2026 ASEC enters when IPUMS
posts it. *(chosen; D; implemented XC)*

**R4.3** Exclude monthly samples before January 2025, and never form a
transition spanning December 2024 to January 2025; it crosses the industry code
change. *(verified; BLS)*

**R4.4** CPS geography is consistent at the state level throughout. Metro codes
are mid-transition: rotation groups entering from May 2025 carry 2020-based CBSA
codes and the rest 2010-based codes until the phase-in completes in August 2026,
and Connecticut now uses planning-region CBSAs. Metro-level CPS targets use
August 2026 and later months, or only households whose entry month — the first
six digits of `CPSIDP` — is May 2025 or later. *(verified; CPS)*

**R4.5** Two extracts, delivered as CSV with IPUMS data quality flags:

| Role | `monthly`: labor force members (`LABFORCE` = 2) | `asec`: all persons |
| --- | --- | --- |
| Panel | `CPSIDP`, `CPSIDV`, `MISH` | `CPSIDP`, `CPSIDV` |
| Weights | `WTFINL`, `LNKFW1MWT`, `EARNWT` | `ASECWT`, `REPWTP` |
| Jobs | `IND`, `OCC`, `CLASSWKR`, `EMPSAME`, `ACTSAME` | `IND`, `OCC`, `CLASSWKR`, `INDLY`, `OCCLY`, `CLASSWLY` |
| Labor force | `LABFORCE`, `EMPSTAT`, `UHRSWORK1` | `LABFORCE`, `EMPSTAT`, `WKSWORK1`, `UHRSWORKLY` |
| Earnings | `EARNWEEK2`, `HOURWAGE2`, `PAIDHOUR`, `ELIGORG` | `INCWAGE`, with `INCWAGE_CPIU_2010` |
| Worker profile | `AGE`, `SEX`, `EDUC` | `AGE`, `SEX`, `EDUC` |
| Geography | `STATEFIP`, `REGION`, `METFIPS`, `COUNTY` | `STATEFIP`, `REGION`, `METFIPS`, `COUNTY` |
| Migration | — | `MIGRATE1`, `MIGSTA1`, `WHYMOVE` |

*(chosen; D; implemented XC)* Whether the API accepts `CLASSWLY` and `REGION`,
the two names not confirmed in the CPS documentation, is *(open — resolved by
verification, not argument, discharged by V5)*.

**R4.6** IPUMS CPS carries Census codes, not NAICS or SOC strings. Store `IND`,
`OCC`, `INDLY`, and `OCCLY` as zero-padded four-character strings and map them
through the Census code lists for the 2022 industry and 2018 occupation
classifications, which give each category's NAICS or SOC equivalent. Do not
reuse the IPUMS USA `IND`-to-`INDNAICS` crosswalk for CPS codes: it reflects ACS
PUMS codes, which differ slightly from the full Census lists. *(verified; BLS,
USA; padding implemented XC)*

**R4.7** Link person-months on `CPSIDV`, which joins only records whose sex and
race match and whose age changes plausibly; keep `CPSIDP` for a linkage-rate
comparison, and order each person's records by `MISH`. September-to-November
2025 pairs are two-month links: flag them and keep them out of month-to-month
rates. `LNKFW1MWT` is missing for September 2025 months-in-sample 1–7.
*(verified; CPS)*

**R4.8** **A code change is a transition only when the respondent says the job
changed.** Under dependent interviewing, last month's industry and occupation
are carried forward when the respondent reports the same employer and unchanged
duties. Count an employment-to-employment transition only when `EMPSAME` reports
a different employer or `ACTSAME` reports changed duties; code differences
without either are flagged as coding noise and excluded. `EMPSAME` is undefined
in months-in-sample 1 and 5 and has documented not-in-universe gaps, so every
transition target reports the share of linked pairs with a usable flag.
Unemployment-to-employment transitions use the industry and occupation the
unemployed report for their last job. *(verified; CPS)*

**R4.9** ASEC transitions run from the longest job in the previous calendar year
(`INDLY`, `OCCLY`) to the current job (`IND`, `OCC`) among the currently
employed. Whether `INDLY` in the 2025 ASEC uses the same 2022 scheme as `IND` is
*(open — resolved by verification, not argument, discharged by V6)*.

**R4.10** Migration targets are state-to-state flows from `MIGSTA1` to
`STATEFIP`, with a job-related subset defined by `WHYMOVE`: new job or transfer,
looking for work, easier commute, and other job-related reasons. *(verified;
CPS)*

**R4.11** Use `WTFINL` for monthly cross-sections, `LNKFW1MWT` for
adjacent-month links, `EARNWT` with `ELIGORG` imposed for earner-study
variables, and `ASECWT` for the ASEC. Replicate weights exist only for the ASEC:
160 of them, with successive-difference factor 4/160. Basic monthly files carry
no design variables, so monthly standard errors come from a household-cluster
bootstrap and are labeled approximate. *(verified; CPS — bootstrap added at
synthesis)* How the CSV files store weights that carry implied decimals in the
DDI is *(open — resolved by verification, not argument, discharged by V7)*.

**R4.12** Earnings after March 2023 are released only rounded, so use
`EARNWEEK2` and `HOURWAGE2` throughout. `HOURWAGE2` topcodes change monthly;
apply the lowest topcode across the months analyzed. *(verified; CPS)*

### R5 — Industry and occupation codes

**R5.1** The canonical vintages are NAICS 2022 and SOC 2018. Every record keeps
its source-native code beside the canonical mapping. *(chosen; D)*

**R5.2** Build node and edge tables for each system from the official structure
files. NAICS has five levels, with the multi-code sectors 31–33, 44–45, and
48–49 each represented as one sector node; SOC has major group, minor group,
broad occupation, and detailed occupation. *(added at synthesis)*

**R5.3** **Mixed-depth codes are parsed, never truncated or guessed.** Each
parsed code carries its deepest resolved node, the set of finest-level codes it
can stand for, and an aggregation type. For `INDNAICS` the types follow the
IPUMS legend: multiple NAICS codes (`M`), part of a NAICS code (`P`), not
specified within a sector (`S`), and exception (`Z`). For `OCCSOC`, a code
aggregated with `X` records which of two reasons applies — no exact match to a
Census occupation code, or fewer than 10,000 people nationwide — because the
first reflects Census category design and the second disclosure. An unparseable
code fails the build. *(verified; USA)*

**R5.4** Vintage concordances — ITA's 2012 and 2017 codes, and the 2022 ACS
comparator's 2017-based codes — carry one-to-many and many-to-many relationships
as flagged candidate sets. No relationship is resolved by picking one side.
*(added at synthesis)*

### R6 — Geography hierarchy

**R6.1** **Geography is two paths, not one chain.** Counties nest strictly in
states, census divisions, and census regions. Counties also belong to CBSAs
under the 2023 OMB delineations, which can cross state lines, and non-metro
counties belong to no metropolitan area. Represent geography as node and edge
tables with typed edges, never as a single tree. The non-tree structure is
deliberate: it stress-tests hyperbolic embeddings that assume tree-like
geometry. *(chosen; D)*

**R6.2** Connecticut's planning regions are its county-equivalents throughout,
matching the 2023 delineations. *(added at synthesis; consistent with CPS)*

**R6.3** Microdata areas map to counties through population-weighted allocation
factors, never through majority assignment alone. Residence PUMAs split large
counties and pool small ones. Place-of-work PUMAs follow county lines under the
standards introduced with the 2010 vintage, and 2020 place-of-work PUMAs are
identical to 2020 migration PUMAs, so commuting and migration flows share one
set of county-based units. *(verified; USA)* Whether the 2020 vintage kept the
county-line rule is *(open — resolved by verification, not argument, discharged
by V8)*.

**R6.4** Exclude Puerto Rico and the island areas from the hierarchy. *(chosen;
D)*

### R7 — Benchmark targets and outputs

**R7.1** Every target is an aggregate carrying a point estimate, a standard
error and its method (replicate, bootstrap, or none), unweighted and weighted
counts, and its source, sample set, code vintage, and universe. *(chosen; D)*

**R7.2** Target families:

| Family | Built from | Units | Evaluates |
| --- | --- | --- | --- |
| Staffing pattern | ACS; CPS as a check | industry × occupation shares | NAICS, SOC |
| Area mix | ACS workplace geography; ITA | area × industry, area × occupation | NAICS, SOC, geography |
| Worker profile | ACS; CPS earner study | code × education, field of degree, wage quantiles, hours, weeks, age, sex | NAICS, SOC |
| Job-change flows | CPS monthly panel; ASEC | occupation → occupation, industry → industry | NAICS, SOC |
| Commuting flows | ACS | residence PUMA → workplace PUMA | geography |
| Migration flows | ACS; CPS ASEC | PUMA → PUMA; state → state, with a job-related subset | geography |
| Text–code pairs | ITA | employer description → NAICS code path | NAICS |
| Co-ownership | ITA | industry × industry within an employer (`ein`) | NAICS |

The co-ownership family is *(added at synthesis)*; the others are *(chosen; D)*.

**R7.3** Every target reports its unweighted count. The minimum count for
headline use is *(open — resolved by measurement, not argument, discharged by
V9)*; it is set from observed distributions, not picked here.

**R7.4** Outputs are Parquet. Pairwise families share one long schema —
`source`, `family`, `unit_a_type`, `unit_a`, `unit_b_type`, `unit_b`, `measure`,
`value`, `se`, `se_method`, `n_unweighted`, `n_weighted`, `sample_set`,
`vintage`, `universe`, `flags` — and profiles use the same schema with a feature
in place of `unit_b`. Hierarchies (R5.2, R6.1) and ITA pairs are separate
tables. Each output has a manifest listing its raw inputs by hash and its code,
crosswalk, and transformation versions. *(added at synthesis)*

### R8 — Licensing, disclosure, and leakage

**R8.1** IPUMS terms prohibit redistributing the data without permission, apart
from subsets published to meet a journal's data requirements. Only aggregate
targets leave the machine they were built on, and IPUMS microdata are never
committed to a repository. If microdata-level release is ever needed, build from
the Census Bureau's own public-domain PUMS files instead. *(verified; USA)*

**R8.2** Cite IPUMS USA and IPUMS CPS as their terms require. *(verified; USA)*

**R8.3** ITA files are public, so ITA-derived tables may contain
establishment-level rows. *(verified; ITA)*

**R8.4** **Benchmark tables are never training data.** No target and no ITA
description enters training, curriculum construction, hard-negative mining, or
model selection for an embedder it evaluates. A family used for tuning is split
first, and only its held-out part is reported as evaluation. *(added at
synthesis)*

### R9 — Pipeline conventions

**R9.1** Extracts are defined in code with ipumspy against IPUMS API version 2
and requested as CSV; ipumspy's readers return pandas and are not used.
Ingestion streams each CSV to Parquet with polars, keeping alphanumeric code
columns as strings. Transformations are lazy polars with method-style
expressions. Scripts carry inline dependency metadata and run with `uv run`.
*(implemented; XA, XC)*

**R9.2** Every transformation is deterministic and runs offline from raw files.
Tests use fixtures, with no network and no credentials. *(added at synthesis)*

## Verification

Observable outcomes. Each `(open)` marker above is discharged by exactly one
bullet here.

- **V1 — ITA description content** *(discharges R2.6)*. For each year, report
  the length distribution of `industry_description`, its empty and placeholder
  shares, the share identical to a NAICS title, and repetition within employer.
  Adopt the cleaning rules in a recorded decision.
- **V2 — ITA establishment ID persistence** *(discharges R2.7)*. For
  establishments in the 2023 data, measure the share whose `establishment_id`
  reappears in 2024 and 2025 with the same `ein` and address, and the share of
  address matches carrying a different ID.
- **V3 — ITA county assignment** *(discharges R2.8)*. On a stratified sample,
  compare a ZIP-to-county crosswalk with address geocoding; record match rates
  and county agreement, and adopt the method in a recorded decision.
- **V4 — ACS 5-year sample ID** *(discharges R3.2)*. List the IPUMS USA catalog
  and confirm the ID and description of the 2020–2024 5-year sample; correct XA
  if it is not `us2024c`.
- **V5 — IPUMS variable acceptance** *(discharges R3.5 and R4.5)*. Submit the
  core ACS extract and both CPS extracts. Record any rejected name — the
  replicate-weight requests, `CLASSWLY`, and `REGION` are the likeliest — and
  correct the scripts.
- **V6 — ASEC industry-last-year scheme** *(discharges R4.9)*. Compare `INDLY`
  code frequencies in the 2025 ASEC with the 2022 Census industry code list.
  Codes outside the list mean the ASEC transition target needs a concordance
  under R5.4.
- **V7 — weight storage in CSV** *(discharges R4.11)*. For each weight the DDI
  defines with implied decimals, confirm how the CSV stores it and that weighted
  totals land near published levels before any target uses it.
- **V8 — 2020 place-of-work PUMA boundaries** *(discharges R6.3)*. Check the
  2020 place-of-work PUMA definitions against county boundaries. Any split
  county gets allocation factors, as residence PUMAs do.
- **V9 — minimum cell counts** *(discharges R7.3)*. After the first full build,
  report unweighted-count distributions for every family and set the headline
  minimum in a recorded decision. Until then, no target is described as passing
  or failing a size gate.
- **V10 — totals reproduction**. Compare ITA rows per year with OSHA's published
  submission counts, ACS pooled employment by state with published ACS
  estimates, and CPS monthly employment with BLS levels. CPS totals use
  `WTFINL`, not the composite weight behind official estimates, so record the
  gap rather than tuning it away.
- **V11 — code parsing completeness**. Every `INDNAICS`, `OCCSOC`, and mapped
  CPS code in the extracts parses to a node or a candidate set; an unparseable
  code fails the build.
- **V12 — offline contract test**. From fixture raw files through Parquet
  conversion, code parsing, geography allocation, one target per family, and the
  manifest, with no network and no credentials.

## Out of scope

- **Embedder training and methods.** Architecture, curriculum, hard-negative
  mining, and training data are unaffected; R8.4 keeps evaluation data out of
  them.
- **Evaluation protocol.** Distance measures, rank correlations, hierarchical
  scoring of text–code pairs, data splits, and acceptance thresholds are a
  distinct subsystem. **Successor spec required before any embedder is scored.**
  R7 delivers the targets it consumes.
- **Sources considered and not adopted** (D):
  - SBA Paycheck Protection Program loans: borrower-level, a 2020–21 snapshot,
    with applicant-reported job counts.
  - OSHA enforcement inspections: selected on being inspected.
  - SBA 7(a) and 504 loans: "jobs supported" is a program metric, not a
    headcount.
  - Mexico's DENUE: banded employment and SCIAN codes, outside the U.S.
    geography.
  - The Census synthetic LBD: 3-digit SIC, no geography, synthetic values,
    access by application.
  - Statistics Canada's Open Database of Businesses: municipal categories, not
    employer text.
  - SBA Small Business Search: firm-written narratives, but no bulk download
    found.
  - H-1B LCA and PERM disclosure files: filer-chosen 4- to 6-digit NAICS codes;
    candidates for a later mixed-depth extension.
- **Puerto Rico and the island areas** (R3.4, R6.4).
- **Microdata release** (R8.1).

## Rollout

**IPUMS registration blocks the most.** R3 and R4 cannot start until both
collections approve the account, so submit the R1.3 statement first.

ITA needs no account, so it goes first and carries the vertical slice that
proves this spec: one ITA year through R2 harmonization, R5 code mapping, R6
county assignment, one area-mix target, and its manifest. The ACS core follows,
with V4 and V5 run before any download is trusted, and then CPS. CPS metro-level
targets need August 2026 and later months (R4.4); the rest of R4 runs on the
current window.

V9 sets the cell-count gate after the first full build and before any embedder
is scored.

XA and XC were tested offline only: dry runs, a mocked sample catalog, and
synthetic conversions. Their first live submissions are V5. Planned targets are
never described as built, and no result from a fixture or a partial extract is
reported as a benchmark.