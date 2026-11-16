# Evidence sources for six uncovered uses

> Next step: the owner promotes Ranked-list items O6–O11 of
> `specs/naics-evaluation-data-roadmap.md` to stages, one stage for each source
> below. Each stage designs its own tables (brainstorming), then plans its build.
> Do not plan this document as a whole. Do not download or build from it.

Status: for owner review, Stage 2 design session, 2026-11-16. The owner made
the decisions in Owner decisions. Calls marked "My call" are proposals for the
owner to check. No file was downloaded. Every fact below comes from a public HTML page read on 2026-11-16,
or is marked *unverified*.

## Intent

### Decision 2 (recorded here, its Home)

The owner listed what naics-embedder's blended industry-relatedness embedding is
for (naics-embedder `specs/naics-artifact-redesign.md`, U18). On 2026-11-14 the
owner said: "for now, disregard graph embedding uses for which
~/Projects/embedding-data have no coverage--but for those uses (firm-level data,
input-output tables), provide a blurb I can use with brainstorming in that repo."
Asked which uses the work covers, the owner answered "All six."

| Use, in the owner's words | Data it needs | Coverage before this spec |
|---|---|---|
| KYB and anomaly detection: "Comparing a company's self-reported NAICS code against the embedding of its transaction network or vendor graph" | firm-to-firm transactions or vendor links | none |
| Peer and competitor detection: "often combined with subsidiary ownership graphs" | links between a parent and its subsidiaries, across EINs | partial: R7.2 co-ownership covers the industries that one EIN operates together, not links between EINs |
| Holding-company classification: "aggregating the graph embeddings of its child entities" | the same ownership links, with each subsidiary's NAICS | partial: same |
| Supply-chain dependency: "NAICS codes are connected via input-output tables or B2B transaction graphs" | directed industry-to-industry flows of goods, services or payments | worker flows only: R7.2 job-change flows (planned, not built) |
| Look-alike prospecting: "embed customer industry graphs" | firm-to-customer-industry links | none |
| Co-visitation and foot traffic: "predict which types of businesses people visit sequentially" | visit sequences between establishment types | partial: R7.2 area mix gives co-location, not visits |

Decision 1 (one blended space, judged on held-out families) is recorded in
naics-embedder, not here.

### Why

naics-embedder judges its relatedness embedding on whole evidence families that
it never trained on. This repository has no evidence for these six uses. Without
evidence, nobody can tell whether the embedding serves them. This spec names, for
each use, a free source that could supply the missing data, or records that none
exists. A later stage fetches and builds each named source.

### Goals

- Each of the six uses gets one named free source, or an *uncovered* verdict with
  the sources considered and why each fails.
- Each named source has enough detail to rank its build: what it observes, its
  unit, its route to NAICS 2022, its population, access and terms, the R7.1
  fields it lacks, its size where known, and its open checks.
- The spec states how it amends R1.1 and the other three-source lines of
  `specs/embedding-evaluation-data-spec.md` (the source spec).

### Non-goals

- Target tables, schemas and measures. Each later stage designs its own.
- Fetching any file, creating any account, or building anything.
- Scoring, null models or data splits. These belong to the successor
  evaluation-protocol spec.
- The R8.4 training-role amendment. It is a separate owner decision after
  naics-embedder's spec proposes which families train.

### Anti-goals

The design fails, even if each source works, when it:

- Reaches NAICS through a category-to-industry mapping that this project writes.
- Treats a company-name match as ownership or as a vendor link.
- Fills a missing standard error or count in a published aggregate.
- Changes the definition of an existing R7.2 family, or edits R2.6.
- Admits a paid source, or a source whose terms forbid publishing aggregates.

## Owner decisions

| Date | Decision | Words |
|---|---|---|
| 2026-11-16 | Free data only. A use with no free source is recorded as uncovered, with the sources considered and why each fails. | Roadmap Stage 2, default 1 |
| 2026-11-16 | A new spec under `specs/` states how it amends R1.1 and the other three-source lines. | Roadmap Stage 2, default 2 |
| 2026-11-16 | Published aggregates are admitted under a stated exception. Missing fields are named and flagged, never filled. | Roadmap Stage 2, default 3 |
| 2026-11-16 | Coverage rule: a source that covers part of a use counts, with its limits named and flagged. Exception: if reaching NAICS needs a mapping this project writes, the use stays uncovered. | "A, with that exception" |
| 2026-11-16 | Approach: fewest sources (option 1). | "Option 1" |
| 2026-11-16 | BEA targets are admitted as flagged non-headline evidence. Headline use waits for the evaluation-protocol spec or a NAICS 2022 benchmark. | "Non-headline" |
| 2026-11-16 | TRI parent links form a new family, keyed by TRI parent. R7.2 co-ownership stays within one EIN. | "New family" |

## Coverage rule

A source covers a use when all four hold:

1. It observes the relation the use needs, or the nearest relation that the
   source records. Its limits are named and flagged. Partial coverage includes a
   selected population, coarse official codes, and industry-level data in place
   of firm-level data.
2. Each record reaches NAICS 2022 through a native NAICS code, an official
   published concordance, or a join on a shared official identifier. R5 then
   gives a candidate set, never a guess.
3. Access is free. A free account or a free API key is allowed, as IPUMS already
   requires. The account is the owner's to create.
4. Its terms allow aggregates to leave the machine (R8.1). Its test fixtures can
   be redistributed or made synthetic (R9.2).

A use stays uncovered when its only route to NAICS is a mapping that this
project would write. A company-name match never establishes a link.

## Approaches

| Approach | What it does | Trade-off | Decision |
|---|---|---|---|
| 1. Fewest sources | One source for each use. Three sources serve five uses. Alternates are recorded as considered. | Three later builds. Coverage is narrower: TRI industries, federal contractors and BEA's 402 industries. | **Chosen** |
| 2. Widest coverage | Option 1, plus FFIEC NIC and IRS Form 990 Schedule R beside TRI, and the BLS annual input-output matrices beside BEA. | Covers more of NAICS. Five or six builds. NIC refuses automated reads and its NAICS field is not confirmed. | Rejected |
| 3. Strictest | Names only sources that need no account and have no unconfirmed field: BEA and TRI. | KYB becomes uncovered. Two builds. | Rejected |

## Verdicts

| Use | Roadmap outcome | Verdict | Source |
|---|---|---|---|
| Supply-chain dependency | O9 | Covered, partial, non-headline | BEA input–output tables |
| Look-alike prospecting | O10 | Covered, partial, non-headline | BEA input–output tables |
| KYB and anomaly detection | O6 | Covered, partial | USAspending subawards with SAM.gov entity NAICS |
| Peer and competitor detection | O7 | Covered, partial | EPA TRI facility parent links |
| Holding-company classification | O8 | Covered, partial | EPA TRI facility parent links |
| Co-visitation and foot traffic | O11 | **Uncovered** | none |

Two pairs of uses share one source. Supply chain and look-alike read the same BEA
table in two directions. Peer and holding-company read the same TRI parent links.
For held-out judging, each pair is one evidence family, not two. If one use's
table trains the embedding, the other use's table cannot judge it.

## Source 1: BEA input–output tables (supply chain, look-alike)

- **Publisher.** Bureau of Economic Analysis (BEA), Input-Output Accounts.
- **Observes.** Flows of each commodity to each using industry and to final
  demand (Use table), and each industry's output by commodity (Make or Supply
  table). Read by column, the Use table gives each industry's inputs (supply
  chain). Read by row, it gives each commodity's buyers (customer industries).
- **Direction.** Supplier → buyer. A Use entry is commodity `c` → using industry
  `j`. BEA codes each detail commodity with the code of its primary industry.
- **Unit and levels.** Industry. Detail level has 402 industries. Summary level
  has 71, underlying summary 138, sector 15. Detail tables exist only for
  benchmark years ending in 2 or 7, from 2007. Annual tables have 71 industries.
  [guide](https://www.bea.gov/resources/guide-interactive-industry-input-output-accounts-tables),
  [products](https://bea.gov/products/input-output-accounts-data)
- **Vintage.** The latest benchmark is 2017. Its Supply and Use tables were
  released on 2023-09-28. Annual tables for 2017–2022 and requirements tables
  followed on 2024-02-01.
  [updates](https://www.bea.gov/information-updates-national-income-and-product-accounts)
  No 2022 benchmark date was found. Do not assume one.
- **Route to NAICS 2022.** BEA's classification "now follows the 2017 NAICS"
  ([2023 update](https://apps.bea.gov/scb/issues/2023/11-november/1123-nea-comprehensive-update.htm)).
  BEA publishes an industry-code-to-NAICS concordance as a spreadsheet (not
  opened). The official Census NAICS 2017→2022 concordance, already built by
  Stage 4, then gives each BEA code a NAICS 2022 candidate set. No mapping is
  written here.
- **Population.** The whole U.S. economy, as an estimate. Not records.
- **Access.** Tables download with no account
  ([data page](https://www.bea.gov/industry/input-output-accounts-data)). BEA asks
  for a citation ([guidelines](https://www.bea.gov/help/guidelines-for-citing-bea)).
- **Missing R7.1 fields.** Standard error, unweighted count and weighted count.
  These are flagged under the published-aggregate exception, never filled.
- **Headline status.** Non-headline (owner, 2026-11-16). Three existing rules
  keep BEA out of headline use: crosswalked codes are excluded (Core principle),
  most BEA codes stand for a set of NAICS codes, and V9 gates headline use by an
  unweighted count that BEA lacks. Headline use waits for the evaluation-protocol
  spec or a NAICS 2022 benchmark.
- **Size.** Small: a few detail tables. *Estimate.*
- **Limits.** Industry level, not firm level. A commodity basis, not an
  industry-by-industry basis. Coarser than six-digit NAICS: one BEA code stands
  for a set of NAICS codes. Special codes (for example scrap, used goods,
  noncomparable imports and government) may have no NAICS member *(unverified)*.
  The 2017 benchmark predates NAICS 2022.
- **Open checks** (the build stage settles each before it trusts the data):
  - **E1.** The concordance's NAICS edition, its depth, and its treatment of
    special codes. Fetching the spreadsheet needs the owner's go-ahead.
  - **E2.** BEA's reuse terms for the tables.
  - **E3.** Whether BEA has scheduled a 2022 benchmark, which would decide
    between building now on 2017 and waiting.

## Source 2: USAspending subawards with SAM.gov entity NAICS (KYB)

- **Publishers.** U.S. Treasury (USAspending.gov) and GSA (SAM.gov).
- **Observes.** A federal prime awardee hires a subawardee. This is a vendor
  link between two firms, with an amount.
- **Direction.** Supplier → buyer: subawardee → prime awardee.
- **Unit and identifiers.** Firm, by UEI (Unique Entity ID). Each firm's industry
  is its self-reported primary NAICS (`primaryNaics`) and NAICS list
  (`naicsList`) in its SAM registration. Both fields have public sensitivity.
  [Entity API](https://open.gsa.gov/api/entity-api/)
- **Not the firm's industry.** The NAICS code on a federal contract classifies
  the product or service bought, not the vendor
  ([FAR 19.102](https://www.acquisition.gov/far/19.102)). It must not stand for
  either firm's industry.
- **Route to NAICS 2022.** Native NAICS. Federal procurement adopted NAICS 2022
  on 2022-10-01
  ([SBA rule](https://www.federalregister.gov/documents/2022/09/29/2022-20513/small-business-size-standards-adoption-of-2022-north-american-industry-classification-system-for)).
  Earlier records use NAICS 2017 and need the Stage 4 concordance.
- **Population.** Federal prime awardees and their reported subawardees above
  the reporting threshold. SAM-registered firms only.
- **Access.** SAM.gov entity data needs a free account and a personal API key.
  The default limit for a non-federal user with no role is 10 requests a day. A
  monthly public extract file exists.
  [Extracts API](https://open.gsa.gov/api/sam-entity-extracts-api/) USAspending
  bulk access without an account is *unverified*.
- **Terms.** SAM.gov terms restrict bulk use of Dun & Bradstreet data
  ([terms](https://sam.gov/about/terms-of-use)). Whether publishing aggregates is
  allowed is *unverified*.
- **Missing R7.1 fields.** Standard error. Counts can be computed from records.
- **Size.** Unknown. The build stage measures it.
- **Limits.** Federal contractors only. SAM NAICS is the firm's current
  self-reported registration, not its industry on the subaward date. Self-reported
  codes are unvalidated, which is also what the KYB use tests.
- **Open checks:**
  - **E4.** Subaward field names for the prime and subawardee UEIs, and whether
    a subawardee NAICS field exists. Third-party pages and GSA's own subaward API
    page disagree.
  - **E5.** Whether the SAM public extract carries `primaryNaics` and
    `naicsList` by UEI, whether past extracts exist, and the rate limits.
  - **E6.** SAM.gov and USAspending terms on publishing aggregates, including
    the Dun & Bradstreet restriction.
- **Owner gates.** The owner creates the SAM.gov account. The key is read from
  the environment and never written to a file, a log or a manifest, like
  `IPUMS_API_KEY`.

## Source 3: EPA TRI facility parent links (peer, holding company)

- **Publisher.** U.S. Environmental Protection Agency, Toxics Release Inventory
  (TRI).
- **Observes.** Each reporting facility names its parent company. By
  regulation, the parent is "the highest-level company (or companies) of the
  facility's ownership hierarchy as of December 31" of the reporting year. A
  foreign parent is reported separately. A 50:50 joint venture is its own
  parent. ([40 CFR 372.3](https://www.law.cornell.edu/cfr/text/40/372.3))
- **Direction.** Facility → parent. Two industries are related when one parent
  has facilities in both. This links different EINs, which the Stage 10
  co-ownership family cannot hold.
- **Unit and identifiers.** Facility. "A facility may contain more than one
  establishment" (40 CFR 372.3). The parent's Dun & Bradstreet number
  (`PARENT_CO_DB_NUM`) and EPA's own standardized parent name
  (`STANDARDIZED_PARENT_COMPANY`) appear in EPA's file documentation
  *(unverified: search summary of a PDF)*. Foreign-parent fields start with
  reporting year 2023 *(unverified)*.
- **Route to NAICS 2022.** Native facility NAICS *(field name and edition by
  year unverified)*. Years coded in NAICS 2017 need the Stage 4 concordance.
- **Population.** Facilities in TRI-covered industries above TRI's employee and
  chemical thresholds: mostly manufacturing, mining, utilities and waste
  *(unverified: no HTML page read states the covered industries)*.
- **Access.** One CSV file for each year, 1987–2024, with no account mentioned.
  [Basic data files](https://www.epa.gov/toxics-release-inventory-tri-program/tri-basic-data-files-calendar-years-1987-present)
- **Terms.** No terms are stated on the page. EPA data are U.S. government works
  *(public-domain status unverified)*.
- **Missing R7.1 fields.** Standard error. Counts can be computed from records.
- **Size.** Unknown. The build stage measures it.
- **Limits.** TRI industries only. The parent's own industry is not reported, so
  holding-company evidence gives each parent's mix of child industries, not its
  label. The children are facilities, not subsidiaries. One parent is reported,
  the top one, so the middle of the ownership tree is lost.
- **Open checks:**
  - **E7.** The facility NAICS field names, primary and secondary codes, and
    the NAICS edition for each reporting year.
  - **E8.** The parent identifier fields, how often they are blank or "NA", and
    how EPA assigns the standardized parent name. The build stage groups
    facilities by an identifier or by EPA's standardized name, never by a name
    match of its own.
  - **E9.** EPA's terms for the basic data files.

## Uncovered: co-visitation and foot traffic

No free source observes visit sequences between business types and reaches NAICS
without a mapping that this project would write. Sources considered:

| Source | What it observes | Why it fails |
|---|---|---|
| American Time Use Survey (ATUS), BLS | Ordered diary episodes with a place type: restaurant or bar, grocery store, other store or mall, bank, gym, post office, place of worship, library and others ([MLR 2018](https://www.bls.gov/opub/mlr/2018/article/what-is-the-impact-of-recoding-travel-activities-in-the-american-time-use-survey.htm)) | No official route from place types to NAICS. The lexicon pages never mention NAICS ([lexicons](https://www.bls.gov/tus/lexicons.htm)). A mapping would be written here. Nearest miss. |
| National Household Travel Survey (NHTS), FHWA | Trips with a purpose, such as "Buy meals" or "Health care visit" | Purposes, not places. No NAICS route. |
| Advan Weekly Patterns (formerly SafeGraph Patterns) | Native NAICS, plus brands visited on the same day ([dictionary](https://docs.advanresearch.com/advan_data_dictionaries.md)) | Paid. Same-day co-occurrence, not a sequence. |
| Placer.ai | Foot traffic | Terms allow internal use only ([terms](https://www.placer.ai/terms-of-service/)). |
| Foursquare Open Source Places, OpenStreetMap | Place listings | Co-location only. No visits. No NAICS. |
| Consumer Expenditure Survey diary, BLS | Purchases by day | Same-day purchases, not visits. The official concordance maps to PCE products, not NAICS ([concordance](https://www.bls.gov/cex/cepceconcordance.htm)). |
| Google COVID-19 Community Mobility Reports | Six coarse place categories | No sequences. Discontinued on 2022-10-15. |

A future source would change this verdict if it records visit order and either
codes places by NAICS or has an official mapping to NAICS.

## Sources considered and not adopted

| Source | Use | Why not adopted |
|---|---|---|
| FFIEC NIC, Federal Reserve | Peer, holding company | Option 2 alternate. Bank holding company structure with ownership shares and EINs *(unverified: third-party guide only)*. Finance only. Its NAICS field is not confirmed, and ffiec.gov returned HTTP 403 to automated reads. |
| IRS Form 990 Schedule R | Peer, holding company | Option 2 alternate. Filer EIN → related EIN with ownership share ([instructions](https://www.irs.gov/instructions/i990sr)). Nonprofits only. No NAICS: needs a join to ITA by EIN. |
| GLEIF Level 2 | Peer, holding company | CC0 parent links, but no industry code and no EIN ([terms](https://www.gleif.org/en/meta/lei-data-terms-of-use)). |
| SEC Exhibit 21 | Peer, holding company | Subsidiary names only ([17 CFR 229.601](https://www.law.cornell.edu/cfr/text/17/229.601)). Needs name matching. SIC, not NAICS. |
| SAM.gov owner fields, USAspending parent UEI | Peer, holding company | Public owner fields give a name and CAGE code only. The UEI hierarchy is restricted. One ultimate parent for each firm. |
| DOL Form 5500 | Peer, holding company | NAICS-based business code, but no ownership link *(unverified: third-party copy of the instructions)*. |
| BLS input–output matrices | Supply chain, look-alike | Option 2 alternate. Annual, derived from BEA ([page](https://www.bls.gov/emp/data/input-output-matrix.htm)). Its NAICS route sits in a ZIP file and is not confirmed. |
| SEC major-customer disclosures | Look-alike, KYB | Customers are company-specific XBRL members with no identifier ([DQC 0109](https://xbrl.us/data-rule/dqc_0109/)). |
| Census Commodity Flow Survey | Supply chain | Records shipments by origin and destination. The survey page names no destination industry ([about](https://www.census.gov/programs-surveys/cfs/about.html)). That destination is a place only is *unverified*: the data dictionary is a spreadsheet, not opened. |
| Open Supply Hub | KYB, supply chain | Share-alike license and no NAICS ([FAQ](https://info.opensupplyhub.org/faqs)). |
| State open-checkbook payments | KYB | No NAICS field found. The government is the buyer. |

The source spec's own rejected list (Out of scope) stays unchanged. No source on
it is proposed again.

## Rules for every new family

- **Observed, never assumed.** Each relation comes from the source's records or
  published tables. No relation comes from NAICS code structure.
- **R5 candidate sets.** A coarse or older code becomes a NAICS 2022 candidate
  set through official concordances only. Nothing is truncated or guessed.
- **Direction.** Flows are stored directed. Supplier → buyer is the convention
  for BEA and subawards. *(My call: R7.4 states no direction.)*
- **Published aggregates.** A BEA value is taken as published. Fields it lacks
  are null and flagged. A share that divides a published value by a published
  row or column total is allowed, because it adds no assumption. No coefficient
  that needs a modeling assumption (for example, industry-by-industry
  requirements under a technology assumption) is derived beyond what BEA
  publishes. *(My call.)*
- **R8.4.** Each new family is specified as an evaluation target under R8.4 as
  written. Its role may change after the separate R8.4 owner decision.
- **Licensing.** Aggregates leave the machine only if E2, E6 or E9 confirm the
  terms allow it. Fixtures are synthetic unless the terms allow redistribution.
- **Verdicts are conditional.** Each covered verdict holds only while its open
  checks pass. Each build stage starts with a preflight that settles its checks
  before any data is trusted. If a check fails a coverage condition, the stage
  stops. The owner then records the use as uncovered or promotes a named
  alternate, and this spec's verdict table is amended. A failed terms check never
  becomes "build it but keep the aggregates local". *(My call.)*
- **R7.2 and verification.** Each adopting stage adds its family as an R7.2
  row. V12's offline contract test then covers it. V9's count gate covers it
  where the family has counts. *(My call.)*
- **Process.** Each source's first build follows the lighter process the owner
  chose for Stage 1: one build, `verify`, an independent reconciler and a
  one-screen findings file. Replay and a long-form finding go to a later
  hardening stage. The owner can choose otherwise when promoting each stage.
  *(My call.)*
- **Existing families.** No existing R7.2 family changes. TRI parent links
  become a new family, keyed by TRI parent, not part of co-ownership (owner,
  2026-11-16). The TRI stage does not wait for Stage 4's acceptance of Stage 10.
  TRI parent links and ITA co-ownership measure close relations: industries that
  one owner operates together. Neither should judge an embedding that the other
  trained.
- **R2.6.** No edit to R2.6.

## Source spec amendment

This spec states the amendment. It does not edit the source spec or
`CLAUDE.md`. The first later stage that adopts a source applies the matching
text through its own plan. Each later stage adds only its own source.
*(My call.)*

1. **Introduction** ("It covers three sources"). After the sentence that lists
   the three sources, add: "Evidence sources admitted by
   [the evidence-sources spec](uncovered-uses-evidence-sources.md) add further
   families, each adopted by its own roadmap stage."
2. **Core principle** ("computed from records in the three sources"). Replace
   with "computed from records in the admitted sources (R1.1), or taken as
   published from an admitted published aggregate (R7.5)."
3. **R1.1** ("exactly three sources"). Replace with "three core sources" and
   add one row for each adopted evidence source: its unit, years and role.
4. **R1.2** ("All three sources are free"). Replace with "All sources are
   free. A free account or API key is allowed. Its key is handled like
   `IPUMS_API_KEY`."
5. **New R7.5 — published-aggregate exception.** "A target taken from a
   published aggregate table keeps the published value. It names each R7.1 or
   R7.3 field the publisher does not supply, sets it to null and flags it. It
   never fills or models that field." *(owner, Stage 2 default 3, 2026-11-16)*
6. **R7.2.** Add one row for each adopted family: built from, units, and what
   it evaluates.
7. **CLAUDE.md** ("from three sources"). The adopting stage updates this line
   when it ships.

## Methodological limits

- Every named source covers a selected or aggregated part of its use. None
  observes the whole economy at firm level.
- BEA's 2017 benchmark predates NAICS 2022. Its codes are coarser than six
  digits.
- SAM NAICS codes are self-reported and current, not dated to the subaward.
- TRI parents are the top of each ownership tree only. TRI covers mostly
  industrial sectors.
- Two pairs of uses share one source each, so the six uses give at most three
  independent new families. TRI parent links also sit close to ITA
  co-ownership.
- BEA evidence is non-headline. Supply chain and look-alike have no headline
  evidence until the evaluation-protocol spec or a NAICS 2022 benchmark changes
  that.
- Co-visitation stays uncovered.

## Left to each build stage

- Table design: units, measures, schemas and flags, under R7.1, R7.4 and R7.5.
- Year windows. Prefer years coded natively in NAICS 2022, as Stage 10 did.
- Whether TRI's family measure mirrors Stage 10's directional co-ownership share.
- Open checks E1–E9 for its source, before it trusts any data.
- Each file fetch and each account, with the owner's go-ahead.

## Rollout and later-stage handoff

Roadmap: specs/naics-evaluation-data-roadmap.md, Stage 2 — on plan completion, tick the stage and re-validate later stages against what shipped.

- Stage 2 has no plan. Its Exit is this committed, owner-approved spec and
  `specs/naics-evaluation-data-stage-2-findings.md`.
- Three builds cover five uses: BEA (O9, O10), TRI (O7, O8), and USAspending
  with SAM.gov (O6). O11 needs no build.
- The owner re-ranks Track B after Stage 2 reports.
