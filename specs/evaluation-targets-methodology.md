# Embedding evaluation targets methodology

> For agentic workers: when specs/evaluation-targets-critique.md exists beside
> this file, REQUIRED SKILL: describe-critique-methodology (synthesize mode) —
> do not draft a spec directly.

This document describes, in mathematics and prose, how aggregate *evaluation
targets* are built for vector embeddings of three code systems: industries
(North American Industry Classification System, NAICS 2022), occupations
(Standard Occupational Classification, SOC 2018) and U.S. places (counties and
the areas built from them). An embedding trained to respect a formal code tree
is rewarded, not tested, when it is scored against that tree: two industries
far apart in the tree can hire the same occupations, locate in the same places
and trade workers. The targets therefore record how industries, occupations
and places co-occur in observed records — which occupations an industry
employs, where establishments and workers are, which jobs and places people
move between, how employers describe their own industry, and which industries
one employer operates. A later, not yet written, scoring protocol will compare
embedding distances with these targets. This description ends at the targets,
their support and their uncertainty.

Status as of 2026-10-18. Every component carries one or more of these labels:

- **Measured** — built and run on the complete delivered data.
- **Designed** — a detailed design exists; nothing is built.
- **Required** — inputs, universes and inclusion rules are fixed as
  requirements, but no estimator design has been written.
- **Open** — a quantity the requirements say must be set by measurement.

Quoted magnitudes are empirical properties of the delivered inputs and of the
one built target, not benchmark results. Names in parentheses, such as
EMPSAME, are the public sources' own documentation names, given so that a
reviewer can check a source fact.

**Constraints.** Every input is free and public, and only aggregates leave
the machine they are built on; restricted-use files are out of scope. The
design premise is that targets are computed from record-level data —
establishment filings and survey microdata — rather than taken from published
aggregate tables.

**Sources.**

| Source | Record | Window | Records | Contributes |
| --- | --- | --- | --- | --- |
| Establishment filings: annual injury-and-illness summaries (OSHA Form 300A) submitted to the federal Injury Tracking Application | Establishment-year submission | Filing years 2016–2025 | 3,206,055 (394,234 in 2023) | Industry code, address, employment, hours, employer-written industry text, employer identifiers |
| Resident survey: American Community Survey public-use microdata (IPUMS USA), employed persons | Person-year | Core: 2023 and 2024 one-year samples, pooled; alternative: 2020–2024 five-year sample; comparator: 2022 one-year sample | 3,206,859 core; 7,456,212 five-year; 1,575,420 comparator | Staffing patterns, area mixes, worker profiles, commuting and migration |
| Panel survey: Current Population Survey (IPUMS CPS) monthly basic files (labor-force members) and Annual Social and Economic Supplement (all persons) | Person-month; person-year | Monthly January 2025–September 2026 (October 2025 was never collected); supplements 2025 and 2026 | 20 months of 44–49 thousand persons; 142,125 and 134,729 supplement persons | Job-change transitions, retrospective job change, state migration, cross-checks |

**Principles that bind every component.**

1. *Relatedness is observed, never assumed.* No target value is computed from
   a code tree. The formal trees appear only as separate node and edge tables,
   for tasks that say they test hierarchy consistency.
2. *Imputed values are flagged at ingestion and excluded from headline
   targets*: source allocations, vintage-translated codes, source-assigned
   areas and dependent-interviewing carry-forwards. Resident-survey targets are
   built a second time with source allocations included, as a sensitivity
   variant.
3. *Ambiguity is carried, never resolved by choice.* A code that can stand for
   several finest codes becomes a set of possibilities; geography is a typed
   graph with two paths rather than a tree; no majority or largest-share rule
   places a record.
4. *Evaluation data never train.* No target or employer description enters
   the training, curriculum, hard-negative mining or model selection of an
   embedder it evaluates. A family used for tuning is split first, and only its
   held-out part is reported as evaluation.

## Component inventory

| Component (by methodological role) | Estimand / output | Consumes | Status |
| --- | --- | --- | --- |
| **K1** Cross-vintage, mixed-depth classification resolution | Per delivered code: an unweighted canonical candidate set, a status, a determinate finest code where one exists, provenance indicators | Official classification structures and concordances; survey code lists and crosswalks | Measured for establishment codes; Designed for the resident survey; Required for the panel survey |
| **K2** Establishment filing frame | Harmonized submission records: size class, vintage attribution, plausibility indicators, filing-rule possibilities | Filing records; regulatory industry lists; K1 | Measured |
| **K3** Establishment address-to-county assignment | One county, or an explicit unassigned state with its reason, per record | K2 addresses; street-address geocoder responses; ZIP business-address shares; county frame | Measured |
| **K4** Survey-area population allocation | Area-to-county population factors (residence; workplace and migration); area-to-metropolitan intersection fractions and non-metropolitan residuals | Census 2020 population intersections; published area compositions; county frame | Designed |
| **K5** Establishment area-mix estimator | Within-county shares of submitted records by six-digit industry, filing year 2023 | K1–K3 | Measured |
| **K6** Establishment identity and text estimators | Cross-year establishment links; description–industry pairs; within-employer industry co-occurrence | K1, K2 | Linkage and text-cleaning rules adopted and measured as diagnostics; both targets Required |
| **K7** Resident-survey estimators | Staffing patterns; workplace area mixes; worker profiles; commuting flows; migration flows | Resident survey; K1; K4 | Required; inputs verified |
| **K8** Panel-survey estimators | Employer- and duty-change transition flows (monthly and annual retrospective); state migration with a job-related subset; staffing and earnings cross-checks | Panel survey; K1 | Required; inputs verified |
| **K9** Uncertainty, support and reliability gate | Standard error and its method per target; unweighted and weighted support; minimum support for headline use | Design and replicate weights; K5, K7, K8 | Support reporting Measured (K5); SE methods Required; minimum Open |

## Composition

Symbols are defined in the shared Notation table below and in each
component's own Notation table.

The components do not combine into one score. They form a layered pipeline
whose last layer is a set of parallel target families, each consumed
separately by the scoring protocol.

**Record annotation (K1–K4).** Each source record $i$ keeps every delivered
value and gains annotations computed deterministically from it and from frozen
public references:

$$
\tilde{\imath} = \big(i,\; K_i,\; J_i,\; \sigma_i,\; \kappa^\star_i,\; o^\star_i,\; \mathbf{z}_i,\; \{\gamma^{\varrho}_i\}_{\varrho}\big).
$$

Annotation never drops, duplicates or reorders records, so every exclusion is
an eligibility decision of an estimator and every published count reconciles
to source totals. An establishment record has one geographic role, its
address, with $\gamma_i(c) = \mathbb{1}[\hat{c}_i = c]$ from K3. A survey
record has, for each role, either a documented non-applicable status or a
population allocation from K4:
$\gamma^{\mathrm{res}}_i(c) = f(p^{\mathrm{res}}_i, c)$,
$\gamma^{\mathrm{work}}_i(c) = h(q^{\mathrm{work}}_i, c)$ and
$\gamma^{\mathrm{mig}}_i(c) = h(q^{\mathrm{mig}}_i, c)$. When defined,
$\sum_c \gamma^{\varrho}_i(c) = 1$.

**Estimation (K5–K8).** Every pairwise family built or planned so far is a
weighted total, or a ratio of weighted totals, over annotated records:

$$
\hat\theta_\varphi(a,b) \;=\; \frac{\sum_i w_i\, E^\varphi_i\, A^\varphi_i(a)\, B^\varphi_i(b)}{\sum_i w_i\, E^\varphi_i\, A^\varphi_i(a)} .
$$

Membership $A^\varphi_i(a)$ or $B^\varphi_i(b)$ is an indicator for a
determinate code, a determinate county or a feature value, and a population
factor $\gamma^{\varrho}_i$ for a county reached through a survey area.
Shares within a row unit sum to one whenever every eligible record has
$\sum_b B^\varphi_i(b) = 1$. Flows take $A$ at the origin observation and $B$
at the destination observation; profiles take $B$ as a feature indicator, or
replace the ratio by a weighted quantile. A survey total for a county is
therefore a population-weighted mixture of area totals:

$$
\hat N(c, b) = \sum_{q} h(q,c)\, \hat N(q, b),
\qquad
\hat N(q,b) = \sum_i w_i\, E_i\, \mathbb{1}\big[q^{\mathrm{work}}_i = q\big]\, B_i(b).
$$

Candidate sets carry no weights, so a record whose code is not determinate
cannot contribute fractionally to several codes. The one built family (K5)
excludes such records. For the survey families the treatment is undecided:
exclusion, or a unit defined at the source's own aggregate category (K1-Q3,
S2).

**Geographic rollups.** Establishment counts roll up exactly along the
administrative path (county, state, division, region) and along CBSA
membership. Survey quantities for metropolitan areas use the direct
area-to-metropolitan fractions $f^{\mathrm{M}}(p,\mu)$ rather than county
rollups; the two routes stay distinguishable and are never combined as if they
were independent probabilities. Commuting and migration flows are defined
between the surveys' own areas or states, without allocation.

**Uncertainty (K9).** A survey target's standard error comes from recomputing
the same estimator under every replicate weight set (resident survey,
supplement) or bootstrap resample (monthly panel), holding K1–K4 annotations
fixed. Only marginal standard errors are published; no covariance across
targets or families is.

**Interface to the scoring protocol.** Each target row carries its source,
family, unit types and identifiers, measure, value, standard error and its
method, unweighted and weighted support, sample set, vintages, a universe
statement and flags. In the built family, companion tables give each row
unit's denominator and, for every diagnostic indicator, its positive true and
unknown support in each cell and denominator, and a row's flags name the
indicators with nonzero support; the survey families' companions are not yet
designed. Because supports are published, the protocol can renormalize, for
example from shares within a county to an industry's distribution across
counties. The code and geography graphs are published separately as node and
edge tables.

## Cross-component assumptions

1. **One canonical vintage per system suffices.** Industries are expressed in
   NAICS 2022, occupations in SOC 2018, places in a 2025 county frame;
   sources coded otherwise reach these only through unweighted possibility
   sets (K1). *If it fails* — if the canonical vintage fits a source's period
   poorly — translated records lose resolution or are excluded, and families
   built from differently coded years stop being comparable.
2. **Units of different depth are comparable.** Establishment filings resolve
   industries to six-digit finest codes. The surveys code industries and
   occupations in Census categories, many of which stand for sets of finest
   codes: at least 38% of core resident-survey workers carry an industry value
   marked as an aggregate. *If it fails:* cross-source checks at the finest
   level are undefined, and the protocol must score embeddings of finest codes
   against targets measured on sets of them.
3. **One retrospective geographic frame suffices.** Counties (2025), CBSAs
   (July 2023 delineation), ZIP business-address shares (one quarter, 2025Q4),
   microdata-area definitions (2020) and allocation populations (2020 Census)
   apply to records from 2016 through 2026. *If it fails:* where boundaries,
   ZIP composition or population changed, records are placed in a frame they
   did not inhabit; Connecticut's counties, for example, were replaced by
   planning regions in 2022.
4. **Allocation does not depend on who is allocated.** Survey-area-to-county
   factors are total-population shares, identical for every industry,
   occupation and worker. *If it fails:* county-level survey mixes inside
   multi-county areas are population-weighted mixtures rather than local
   compositions.
5. **Residents stand in for jobs.** Workplace areas are divided among their
   counties by resident population. *If it fails:* job-dense counties receive
   too little workplace employment and residential counties too much.
6. **Families with different universes, counting units and periods measure
   one relatedness.** They draw on unweighted submission records of a
   program-selected set (filing year 2023); design-weighted civilian employed
   persons (interviews through 2023–2024); labor-force members of a monthly
   panel (January 2025–September 2026); and all persons in an annual
   supplement asked about the previous calendar year. *If it fails* — if
   relatedness shifts over 2023–2026, or the universes differ in
   composition — families disagree for reasons unrelated to relatedness.
7. **Complete-case exclusion is ignorable.** Headline targets drop
   source-imputed items, translated codes and records without a determinate
   code or place. This assumes missingness is ignorable within the cells being
   compared (missing at random given the cell). *If it fails:* when
   imputation, translation or placement failure rates vary across compared
   units, headline shares carry selection bias; sensitivity variants show its
   direction, not its size. The exclusions compound: 17.8% of 2023 filings fall
   out of the one built target, 9.7% for want of a county and 8.1% for want of
   a native code.
8. **Indeterminate codes can be excluded rather than split.** Candidate sets
   carry no weights. A record enters a code unit only when its code is
   determinate, or, for survey families, possibly at its own aggregate
   category (undecided). *If it fails:* excluded records are not random — in
   2024 and 2025, 36–41% of filings declare 2012-vintage codes.
9. **Marginal sampling uncertainty is enough.** Code mapping, county
   assignment and area allocation are treated as fixed; no covariance across
   targets or families is published. *If it fails:* a protocol that
   correlates many targets with embedding distances understates its
   uncertainty if it treats targets as independent, and ignores classification
   and placement uncertainty entirely.
10. **Targets are independent of the embedders' training material.** Code
    structure never generates a target, and evaluation tables never become
    training data. *If it fails* — if an embedder's training corpus contains
    the same official titles or structure — text–code pairs whose description
    copies a title measure memorization rather than generalization.
11. **Transformations are reproducible from frozen inputs.** Every
    transformation is a deterministic function of frozen inputs, except that
    the street-address geocoder answers against a current address frame that
    changes over time. *If it fails* — to the extent that the frame changes —
    county assignment is reproducible only by replaying cached responses, not
    by a fresh query.
12. **Published values suffice for the scoring protocol.** Each family
    publishes values normalized in one direction, such as shares within a
    county, with support counts, on the expectation that the protocol derives
    relatedness from them. *If it fails:* quantities not recoverable from
    published values and supports — employment-weighted variants,
    replicate-level estimates, covariances — require rebuilding the targets.

## Notation

| Symbol | Meaning | Domain / units |
| --- | --- | --- |
| $i$ | A source record: one submitted establishment-year summary, or one person observation (person-year in the resident survey and the supplement, person-month in the monthly panel) | index |
| $\mathcal{R}_{\mathrm{E}}$, $\mathcal{R}_{\mathrm{A}}$, $\mathcal{R}_{\mathrm{C}}$, $\mathcal{R}_{\mathrm{S}}$ | Record sets: establishment filings, resident survey, monthly panel, annual supplement | sets of records |
| $\tilde{\imath}$ | Record $i$ with its annotations | annotated record |
| $t$, $t_i$ | A period (a year, or a month in the panel); the reference period of record $i$: filing year, survey year or survey month | year or month |
| $\mathcal{I}$, $\mathcal{O}$ | Canonical industry forest (NAICS 2022: 2,125 nodes, 1,012 finest codes) and occupation forest (SOC 2018: 1,447 nodes, 867 detailed occupations); child-to-parent edges, no invented root | node sets |
| $\Lambda(\cdot)$ | Finest codes of a forest, or the finest-level descendants of a node | set of codes |
| $K_i$, $J_i$ | Canonical industry and occupation candidate sets of record $i$: every finest canonical code its delivered code can stand for, unweighted | $K_i \subseteq \Lambda(\mathcal{I})$, $J_i \subseteq \Lambda(\mathcal{O})$ |
| $\kappa^\star_i$, $o^\star_i$ | Determinate canonical industry and occupation of record $i$, defined only when the record's own scheme observes that finest code (K1) | finest code, or undefined |
| $\sigma_i$ | Mapping status of record $i$'s code: native; translated; known-vintage mismatch; unknown vintage with or without supported candidates; missing; documented special | categorical |
| $\mathbf{z}_i$ | Source-imputation and translation indicators of record $i$: source allocation of an item, vintage translation of a code, source-assigned microdata area, dependent-interviewing carry-forward | each 0, 1 or unavailable |
| $\mathcal{C}$, $c$ | County-equivalents of the common 2025 frame: the 50 states and DC, 3,144 units including nine Connecticut planning regions; $c$ is one of them | set; county |
| $\mathcal{C}^{\mathrm{out}}$ | County-equivalents of Puerto Rico and the island areas, outside scope | set |
| $\mathrm{state}(c)$, $\mathrm{div}(c)$, $\mathrm{reg}(c)$ | Administrative parents of county $c$: state, census division, census region | nodes |
| $\mathcal{M}$ | Core-based statistical areas (CBSAs) of the July 2023 delineation: 387 metropolitan, 538 micropolitan | set |
| $\mathrm{cbsa}(c)$ | CBSA containing county $c$, with its type (metropolitan or micropolitan) and the county's role (central or outlying); none for 1,300 counties; 59 CBSAs cross state lines | $\mathcal{M} \cup \{\varnothing\}$ |
| $\varrho$ | Geographic role: establishment address, residence, workplace, residence one year ago | categorical |
| $\gamma^{\varrho}_i(c)$, $\gamma_i(c)$ | Membership mass of record $i$ in county $c$ for role $\varrho$; the role superscript is dropped for a record with a single role | $[0,1]$; sums to one over $c$ when defined |
| $w_i$ | Final weight: one for a filing record; for survey records the person weight (PERWT), monthly final weight (WTFINL), supplement weight (ASECWT) or earner-study weight (EARNWT) | persons |
| $w^{(k)}_i$ | $k$-th replicate weight (REPWTP1 through REPWTP80 in the resident survey; 1 through 160 in the supplement) | persons; may be negative |
| $R$ | Number of replicate weights: 80 (resident survey) or 160 (supplement) | count |
| $Y$ | Number of pooled annual samples: 2 for the 2023–2024 core | count |
| $\varphi$ | Target family: staffing pattern, area mix, worker profile, job-change flow, commuting flow, migration flow, text–code pair, co-ownership | categorical |
| $a$, $b$ | Row and column units of a pairwise target: codes, counties or areas, feature values | unit identifiers |
| $E^\varphi_i$, $E_i$ | Eligibility of record $i$ for family $\varphi$ (universe, imputation, code-determinacy and geographic conditions jointly); $E_i$ when the family is clear | $\{0,1\}$ |
| $A^\varphi_i(a)$, $B^\varphi_i(b)$, $A_i$, $B_i$ | Membership of record $i$ in row unit $a$ and column unit $b$: an indicator, or a population factor for an allocated area; superscript dropped when the family is clear, subscript $it$ for person $i$ in month $t$ | $[0,1]$ |
| $\theta_\varphi(a,b)$, $\hat\theta_\varphi(a,b)$ | Target estimand and its estimate | share, rate, count or quantile |
| $\hat N(\cdot,\cdot)$ | Weighted total of eligible records for a unit pair | weighted persons or records |
| $\widehat{\mathrm{se}}$ | Estimated standard error; method replicate, bootstrap or none | units of $\hat\theta$ |
| $n_\varphi(a,b)$, $\tilde n_\varphi(a,b)$ | Unweighted and weighted support of a target cell | records; weighted records |
| $n_{\min}$ | Minimum unweighted support for headline use | records (Open) |
| $\mathbb{1}[\cdot]$ | Indicator function | $\{0,1\}$ |

## Per-component descriptions

### K1 — Cross-vintage, mixed-depth classification resolution

Status: Measured for all establishment codes; Designed for the resident
survey; Required for the panel survey.

#### Notation

| Symbol | Meaning | Domain / units |
| --- | --- | --- |
| $x_i$ | Delivered industry or occupation code of record $i$, as a logical string with letters, padding and leading zeros preserved | string |
| $v_i$ | Declared native vintage of an establishment industry code; $\varnothing$ when absent or not one of 2012, 2017, 2022 | year |
| $\mathcal{I}_v$ | NAICS structure of vintage $v$: 2012, 2017 and 2022 as native schemes; 2002 and 2007 only to interpret regulatory lists (K2) | forest |
| $\mathcal{T}_{v \to v'}$ | Official concordance between finest codes of vintages $v$ and $v'$, read as a relation, forward or reverse; $\mathcal{T}_{v\to v'}[S]$ is the image of a set $S$ | $\subseteq \Lambda(\mathcal{I}_v) \times \Lambda(\mathcal{I}_{v'})$ |
| $\nu$ | A node of a classification forest | node |
| $\alpha(K)$ | Deepest common ancestor in $\mathcal{I}$ of every member of $K$; none when the members share no sector | node or $\varnothing$ |
| $\kappa_i$, $o_i$ | Latent true finest canonical industry and occupation of record $i$ | finest codes |

#### Problem formulation and data-generating story

Each record carries an industry code $x_i$ (and, in the surveys, an
occupation code) whose meaning depends on the scheme the source used. The
latent quantity is the record's true finest canonical code, $\kappa_i \in
\Lambda(\mathcal{I})$ or $o_i \in \Lambda(\mathcal{O})$. The delivered value
is a deterministic function of a latent native code — translated, coarsened
or corrupted — in three ways:

- *Vintage translation.* Establishment codes are NAICS 2012, 2017 or 2022.
  Before filing year 2023 the data dictionary declares 2012 for every record;
  from 2023 each record declares its vintage, which is sometimes blank or
  invalid. The resident-survey comparator uses NAICS 2017. A canonical code is
  reachable only through official concordances, which are many-to-many.
- *Depth coarsening.* The resident survey publishes some industries and
  occupations only above the finest level. Its industry strings mark
  aggregates with letters — several codes (M), part of a code (P), not
  specified within a sector (S), exception (Z) — and numeric strings shorter
  than six digits are aggregates too. Its occupation strings use X or Y
  placeholders, aggregated either because no Census occupation category
  matches one SOC code or because fewer than 10,000 people nationwide hold the
  detailed occupation; the first reflects category design, the second
  disclosure. The panel survey publishes only Census category codes, each
  standing for one or more NAICS or SOC codes.
- *Defects.* An establishment record may declare a vintage whose structure
  does not contain its code, or carry a code with no usable vintage.

The estimand is the possibility set

$$
K_i = \big\{\kappa \in \Lambda(\mathcal{I}) : \kappa \text{ is consistent with } (x_i, v_i) \text{ under official relations}\big\},
$$

with no probability distribution over its members, together with a status
$\sigma_i$ and provenance indicators. The determinate code $\kappa^\star_i$
exists only when the record's own scheme observes that finest code.

#### Estimation / inference procedure

Each distinct key (scheme, code, paired Census category) is resolved once and
joined back to its records.

1. **Syntax.** Establishment codes must be six ASCII digits. Survey codes must
   match the source's documented token grammar after removing documented
   padding only; letters, suffix digits and leading zeros are never removed.
   A malformed value fails the build.
2. **Native resolution.** With known vintage $v$: if $x_i \in
   \Lambda(\mathcal{I}_v)$ the native set is $\{x_i\}$; if $x_i$ names a
   coarser official node $\nu$ it is $\Lambda(\nu)$; a lettered or placeholder
   aggregate resolves through the source's published constituent relations or
   aggregation expressions, keeping partial-category and exclusion meaning.
   Title matching, wildcard expansion and digit prefixes are never membership
   evidence.
3. **Translation.** $K_i = \mathcal{T}_{v\to2022}[\text{native set}]$, with
   $\mathcal{T}_{2012\to2022} = \mathcal{T}_{2017\to2022} \circ
   \mathcal{T}_{2012\to2017}$ composed over every path. Equal code strings in
   two vintages never bypass the relation, because a code's content can change
   while its string does not.
4. **Unknown vintage.** $K_i = \bigcup_{v:\ x_i \in \Lambda(\mathcal{I}_v)}
   \mathcal{T}_{v\to2022}[\{x_i\}]$ over the three supported vintages, marked
   unresolved even when the union is a single code.
5. **Known-vintage mismatch** ($x_i \notin \Lambda(\mathcal{I}_{v_i})$):
   $K_i = \varnothing$, unresolved, even when another vintage contains $x_i$.
6. **Survey specials.** One documented occupation pseudo-code (military, rank
   not specified) gets $J_i = \varnothing$ and its own status, counted apart
   from both mapped and unparseable values. Any other unsupported survey value
   fails the build.
7. **Determinate code.** $\kappa^\star_i$ is defined only for a valid native
   finest code, or for a survey finest category with a documented one-to-one
   interpretation. Candidate-set size alone never defines it.
8. **Set description.** $\alpha(K_i)$ is recorded as a description of the set;
   it is never treated as an observed aggregate.
9. **Provenance.** A crosswalk indicator (a vintage relation was traversed; it
   persists when the result is a single code), an ambiguity indicator
   ($\lvert K_i \rvert > 1$), an unresolved indicator, the aggregation type and
   markers, and for aggregated occupations the documented reason — category
   design, disclosure, or unknown with its documentary provenance.
10. **Scheme selection** follows verified product metadata, never whichever
    vintage happens to contain a token. Annual 2023 and 2024 samples use NAICS
    2022, the annual 2022 sample NAICS 2017. The 2020–2024 five-year product
    uses its release's 2022 scheme for every component year because the
    Census Bureau recoded earlier respondents; that recoding enters
    $\mathbf{z}_i$. Occupations use SOC 2018. The panel survey uses the Census
    2022 industry and 2018 occupation category lists from January 2025,
    mapped through the full Census lists' NAICS and SOC equivalents rather
    than the resident survey's public-use crosswalk, which differs slightly.
11. **Consistency.** A survey record's paired Census category and NAICS- or
    SOC-based string must agree under the product's published correspondence;
    a contradiction fails the build. Occupation parentage comes from the
    official structure's published nesting, not from code digits.

Measured on all 3,206,055 establishment records (2016–2025): 823,481 native
(25.7%); 2,313,539 translated from 2012 or 2017 (72.2%); 66,365 known-vintage
mismatches (2.1%); 373 unknown vintage with supported candidates; 2,297
unknown vintage without; none missing. In each year 94–98% of records have
exactly one candidate, under 2% have two or three, and a few hundred have 39
or 42. Native codes are 90.9% of 2023 filings but only 55.7% of 2024 and 60.7%
of 2025 filings, because 41.2% and 36.1% of those declare 2012. Most
known-vintage mismatches are valid finest codes in another supported vintage
(9,769 of 9,859 in 2025).

Design input for the resident survey: at least 38% of core worker records
carry an industry value containing a letter marker, and at least 14% an
occupation value containing one; 5,204 core records carry the military
pseudo-code.

#### Assumptions and limitations

1. **Official relations are complete and correct.** *If it fails:* a missing
   correspondence shrinks $K_i$ and silently excludes records downstream; a
   spurious one inflates it.
2. **Unweighted possibilities suffice.** No employment or other weight is
   attached to a candidate. *If it fails* — if a family needs fractional
   membership — there is no basis for it here; ambiguous records must be
   excluded or kept at an aggregate unit.
3. **Declared vintages are trusted.** A known-vintage mismatch is never
   corrected by another vintage. *If it fails* — if mismatches are mostly
   mislabeled vintages, as their validity elsewhere suggests — recoverable
   records are discarded.
4. **An unknown vintage lies among the three supported.** Nothing in the
   record can confirm it. *If it fails:* the union omits the true code.
5. **Survey aggregate membership is exactly what the source publishes.** Where
   per-code evidence of an occupation's aggregation reason is absent, the
   reason is recorded as unknown, never inferred. *If it fails* — if published
   relations are incomplete — candidate sets are wrong without detection.
6. **Survey categories can be compared with finest codes.** The Census
   industry and occupation categories behind both surveys frequently map to
   several finest codes. *If it fails:* survey-derived units cannot be
   compared with establishment-derived units at the finest level
   (Cross-component assumption 2).
7. **The five-year product's recoded industries are correct.** They rest on a
   Census procedure that is not independently validated, and are flagged, not
   checked. *If it fails:* five-year results inherit the recoding's errors.

#### Evaluation criteria

- Every delivered value lands in exactly one status, and the status partition
  reconciles to record totals. The surveys admit zero unparseable values (the
  build fails otherwise); the establishment source instead reports unresolved
  counts explicitly.
- Every reference is structurally valid: official node counts; acyclic forests
  in which every non-root node has one parent and each multi-code sector
  (31–33, 44–45, 48–49) is one node; valid concordance endpoints with complete
  finest-code coverage on both sides.
- Hand-authored expected candidate sets for splits, merges, reshuffles, code
  reuse and two-step translations, rather than sets regenerated by the same
  algorithm.
- Mapping preserves record counts, order and duplicate multiplicity.

#### Open questions for the reviewer

- **K1-Q1.** Is an unweighted possibility set the right interface between code
  harmonization and evaluation, compared with attaching published or estimated
  concordance weights such as employment-weighted crosswalks?
- **K1-Q2.** Should a known-vintage mismatch that is a valid finest code in
  another supported vintage be admitted as a translated record with a flag,
  rather than left unresolved?
- **K1-Q3.** In the survey families, should a record with an aggregate code
  enter a unit defined at its own source category (a set of finest codes), be
  excluded, or be handled otherwise? How have others scored embeddings of
  finest codes against targets measured on aggregates?

### K2 — Establishment filing frame

Status: Measured.

#### Notation

| Symbol | Meaning | Domain / units |
| --- | --- | --- |
| $j$ | An establishment (latent identity) | index |
| $S_{jt}$, $\kappa_{jt}$ | True peak employment and true finest industry of establishment $j$ in year $t$ | persons; finest code |
| $\mathrm{req}(S, \kappa, t)$ | Whether the filing rule in force for year $t$ requires a submission | $\{0,1\}$ |
| $r^{\mathrm{c}}_{jt}$, $r^{\mathrm{v}}_{jt}$ | Unknown propensities to submit when required (compliance) and when not required (voluntary) | $[0,1]$ |
| $\mathrm{sz}_i$ | Harmonized peak-employment size class: 1 (under 20), 2 (20–249), 3 (250 or more) | $\{1,2,3\}$ |
| $\bar{e}_i$ | Reported annual average number of employees | persons |
| $H_i$ | Reported total hours worked in the year | hours |
| $\mathcal{D}_v$ | Designated-industry list for 20–249-employee establishments, in its own vintage: $v = 2012$ for filing years 2016–2022, $v = 2017$ from 2023 | set of codes |
| $\mathcal{X}$ | Partially exempt industry list, NAICS 2007, including two published labels that exist only in NAICS 2002 | set of codes |
| $\Pi_{\mathcal{D}}(\nu)$, $\Pi_{\mathcal{X}}(\nu)$ | Membership possibility set of a list-vintage finest code $\nu$ in each list | $\subseteq \{0,1\}$ |
| $P_{\mathcal{D}}$, $P_{\mathcal{X}}$ | Membership possibilities of one interpretation of a record's code, pooled over the list-vintage codes it reaches | $\subseteq \{0,1\}$ |
| $(v, x)$ | One reference-supported interpretation of a record's industry code: a native vintage and a finest code of it (K1) | vintage, code |
| $o(d, \chi, \mathrm{sz})$ | Outside-the-rule indicator for designated membership $d$, exempt membership $\chi$ and size class $\mathrm{sz}$ | $\{0,1\}$ |
| $\Omega_i$ | Possible outside-the-rule outcomes of record $i$ across its supported interpretations | $\subseteq \{0,1\}$ |

#### Problem formulation and data-generating story

The universe of interest is U.S. establishments; the observed set is not a
sample from it. The regulator requires an annual electronic summary from
establishments with 250 or more employees outside a list of partially exempt
industries, and from establishments with 20–249 employees in a list of
designated industries. It keeps voluntary submissions and does not validate
employee counts. For establishment $j$ in year $t$,

$$
\Pr(\text{submission}_{jt}) = \mathrm{req}(S_{jt}, \kappa_{jt}, t)\, r^{\mathrm{c}}_{jt} + \big(1 - \mathrm{req}(S_{jt}, \kappa_{jt}, t)\big)\, r^{\mathrm{v}}_{jt},
$$

with both propensities unknown. A submission can repeat (exact duplicates,
repeated account-scoped identifiers), and the current year's file keeps
growing until submissions close.

Each record reports an establishment name; an account-scoped establishment
identifier, reissued when an account profile is re-created; an employer
identification number (EIN), missing on nearly all 2016–2018 records; a
company name; a street address; an industry code with, from 2023, its declared
vintage; an employer-written industry description; an establishment type; a
peak-size code; $\bar{e}_i$; and $H_i$.

The estimand of this component is the harmonized record set with its
diagnostics, not a population quantity.

#### Estimation / inference procedure

1. **Stack** all filing years, one record per submitted row, duplicates
   retained.
2. **Size.** Delivered peak-size codes {1, 2, 21, 22, 3} become $\mathrm{sz}_i
   \in \{1,2,3\}$ by merging the 2023-onward subdivisions 21 and 22 into class
   2. Class 2 is never split, because undivided code 2 persists beside its
   subdivisions.
3. **Vintage.** Before 2023, NAICS 2012 is supplied by the data dictionary and
   marked as dictionary-supplied; from 2023 the declared vintage is used; any
   other declared value becomes unknown and is flagged. No record is dropped.
4. **Plausibility indicators** (flag, never drop): employment zero or missing;
   $H_i / \bar{e}_i \notin [500, 4000]$ annual hours per average employee —
   about 10 to 77 hours a week — or hours missing, undefined where employment
   is flagged; and below routine filing size ($\mathrm{sz}_i = 1$).
5. **Filing-rule possibilities.** For each reference-supported interpretation
   $(v, x)$ of the record's code (K1), translate directly into each list's own
   vintage and pool the reached codes' membership possibilities:
   $P_{\mathcal{D}} = \bigcup_{\nu \in
   \mathcal{T}_{v \to v_{\mathcal{D}}}[\{x\}]} \Pi_{\mathcal{D}}(\nu)$ and
   $P_{\mathcal{X}} = \bigcup_{\nu \in \mathcal{T}_{v \to 2007}[\{x\}]}
   \Pi_{\mathcal{X}}(\nu)$, where $v_{\mathcal{D}}$ is the designated list's
   vintage for the filing year. The
   rule version is bound to the nominal submission cycle (filing year plus
   one), because submission dates are not delivered. The two 2002-vintage
   exemption labels are bridged through the official 2002-to-2007 relation, so
   the one 2007 code whose predecessors are only partly covered has
   possibilities $\{0,1\}$. With

   $$
   o(d,\chi,\mathrm{sz}) = \begin{cases} 1 & \mathrm{sz} = 1,\\ 1 - d\,(1-\chi) & \mathrm{sz} = 2,\\ \chi & \mathrm{sz} = 3, \end{cases}
   \qquad
   \Omega_i = \bigcup_{(v,x)} \big\{ o(d,\chi,\mathrm{sz}_i) : d \in P_{\mathcal{D}},\ \chi \in P_{\mathcal{X}} \big\},
   $$

   the outside-the-rule result is the single element of $\Omega_i$ when
   $\lvert \Omega_i \rvert = 1$ and undetermined otherwise — never coerced to
   "inside". A status records why a result is undetermined: candidate
   disagreement, missing code, known-vintage mismatch, unsupported unknown
   vintage or missing size. Provenance indicators for a bridged label and for
   a $\{0,1\}$ membership persist even when the result is determinate.

Measured, filing year 2023 (394,234 records): 29.8% are determinately
outside the nominal rule — 21.2% by size alone, below routine filing size,
and 8.6% by industry — and 2.3% are undetermined; 4.5% have implausible hours
per employee. Submission counts exceed the regulator's published counts where
one exists: 394,234 against 385,488 published at an earlier cutoff for 2023,
and 398,620 against "over 390,000" for 2024. The 2016–2025 files hold 214,978
to 400,288 records a year.

#### Assumptions and limitations

1. **Submissions are usable as records.** Employment and hours are
   unvalidated; duplicates and repeated identifiers are retained. *If it
   fails* — if a downstream use needs establishments rather than submissions —
   every count overstates multiply-submitting establishments.
2. **Records follow the nominal submission cycle.** *If it fails:* a late
   filing is evaluated under the wrong rule version.
3. **A partly covered industry is undetermined, not guessed.** A merged
   industry with covered and uncovered predecessors yields an undetermined
   result. *If it fails* — if the regulator intended a whole-industry reading —
   some records are undetermined that could be determinate.
4. **A fixed band separates plausible hours.** The 500–4,000-hour band is a
   heuristic, not estimated. *If it fails:* legitimate extreme establishments
   are flagged, or implausible ones pass.
5. **Outside-rule records are genuine.** They are kept, and the diagnostics do
   not judge whether a submission was improper. *If it fails* — if
   outside-rule records are mostly misreported size or industry — they
   contaminate every target.
6. **The rule's industry selection is ignorable.** Among 20–249-employee
   establishments, the filing rule, not the economy, sets the industry
   composition of required filings. *If it fails:* the selection propagates
   into every establishment target as apparent relatedness.

#### Evaluation criteria

- Submission counts per year compared with the regulator's published counts;
  gaps are recorded, never tuned away.
- After harmonization, class 2 never co-occurs with its subdivisions; every
  flagged record is retained; every delivered value is accounted for.
- Rule-boundary checks at the 2022/2023 filing-year change, peak size against
  average employment, and unanimous, disagreeing and bridged possibility
  cases.

#### Open questions for the reviewer

- **K2-Q1.** About 30% of 2023 submissions are outside the nominal filing rule.
  Should establishment targets keep them (broader, less rule-shaped coverage),
  drop them (a cleaner rule-defined universe), or report both?
- **K2-Q2.** Is there a principled correction for the rule's industry
  selection — for example, restricting to the 250-or-more size class, which the
  rule selects by size alone outside exempt industries — when filings are used
  as relatedness evidence?

### K3 — Establishment address-to-county assignment

Status: Measured for all ten filing years.

#### Notation

| Symbol | Meaning | Domain / units |
| --- | --- | --- |
| $c^\ast_i$ | Latent true county of the establishment behind record $i$ | county |
| $z_i$ | Five-digit ZIP key normalized from the delivered ZIP | string |
| $\beta(z,c)$ | Share of ZIP $z$'s business addresses lying in county $c$, from one quarter (2025Q4) | $[0,1]$ |
| $\mathcal{B}(z)$ | Counties with positive business-address share in ZIP $z$, counted before any scope or compatibility filter | set of counties |
| $e_i$ | Geocoder outcome for record $i$'s submitted address: status (match, no match, tie) and match type (exact, non-exact) | categorical |
| $c^{\mathrm{G}}_i$ | County returned with a geocoder match | county code |
| $\hat{c}_i$ | Assigned county | $\mathcal{C} \cup \{\varnothing\}$ |
| $u$ | Stratum of the verification sample | index |
| $M_u$, $m_u$ | Population and sample record counts of stratum $u$ | records |

#### Problem formulation and data-generating story

The latent quantity is the county $c^\ast_i \in \mathcal{C}$ of the
establishment behind each record. Observed are the delivered address (street,
city, state, ZIP) and two imperfect instruments:

- a street-address geocoder (the Census Bureau's public batch geocoder),
  matching against a national address-range frame that the service updates
  over time and returning a status, a match type and a county in the 2025
  geography;
- a ZIP-to-county table (the HUD–USPS ZIP crosswalk's business-address ratio)
  giving $\beta(z,c)$, the share of ZIP $z$'s business addresses in county $c$,
  for one quarter (2025Q4).

The estimand is an assignment $\hat{c}_i$ that equals $c^\ast_i$ whenever it
is made, with an explicit reason whenever it is not.

#### Estimation / inference procedure

Identical submitted address tuples are queried once; every record receives
its tuple's response. Precedence, evaluated top to bottom:

$$
\hat{c}_i =
\begin{cases}
\varnothing & \text{the delivered state is Puerto Rico or an island area},\\
\varnothing & e_i \text{ is an exact match and } c^{\mathrm{G}}_i \in \mathcal{C}^{\mathrm{out}},\\
c^{\mathrm{G}}_i & e_i \text{ is an exact match and } c^{\mathrm{G}}_i \in \mathcal{C},\\
c & \mathcal{B}(z_i) = \{c\} \text{ and } c \in \mathcal{C},\\
\varnothing & \text{otherwise.}
\end{cases}
$$

$\mathcal{B}(z) = \{c : \beta(z,c) > 0\}$ counts every positive candidate
before scope filtering, so a ZIP with one in-scope and one excluded candidate
remains ambiguous. Non-exact matches, ties, the largest-share county and any
bridge from Connecticut's retired counties never assign; they remain
diagnostics. An exact in-scope match is not overridden by an ambiguous ZIP,
and a non-exact or incompatible match does not block an eligible
single-county ZIP. State, division, region and CBSA follow from $\hat{c}_i$.
Every record keeps its raw geocoder outcome, its ZIP candidates and its
assignment reason.

**Verification before adoption.** A stratified sample of exact-distinct
records, with strata defined by filing year, delivered state, ZIP format and
the number of positive-business candidate counties (none, one, several), took
at most eight records per stratum in a fixed pseudo-random order, weighted
$M_u / m_u$: 20,628 records in 3,378 strata, representing 3,204,828 records.
Weighted coverage was 64.4% for an exact compatible geocode, 76.6% for a
single compatible ZIP county, and 91.1% for the adopted rule. Where both
instruments name a county, they agree on 4,717 of 4,718 sampled records
(99.98%; 99.9994% weighted); the largest-share county agrees with an exact
geocode on 97.1% (98.2% weighted). Agreement between two instruments is not
accuracy, and no external truth set was used.

Measured on the full table, 2016–2025: 64.5% exact geocode, 26.4% single-county
ZIP, 9.1% unassigned. In 2023: 257,226 exact, 98,840 single-county ZIP and
38,168 unassigned of 394,234; 78% of the unassigned 2023 records sit in ZIPs
with several positive-business counties. Each year 20–23% of records receive
only a non-exact geocoder match.

#### Assumptions and limitations

1. **An exact match names the right county.** Not validated externally. *If it
   fails:* errors enter targets undetected.
2. **A single-county ZIP names the right county,** using one quarter's
   business-address shares for addresses filed over ten years. *If it fails*
   — new ZIPs, changed delivery areas, or establishments outside the ZIP's
   business-address pattern — fallback assignments are wrong.
3. **The delivered address is the establishment's physical location,** not a
   mailing or headquarters address. *If it fails:* records are placed where
   their paperwork is handled.
4. **Unassigned records are ignorable.** *If it fails:* unassigned records,
   concentrated in ZIPs spanning several counties and in addresses with only a
   non-exact match, are not spread evenly across places or industries, so
   every establishment target is biased toward places with simpler ZIP
   geography.
5. **The 2025 county frame fits every year.** Historical boundaries are not
   reconstructed. *If it fails:* old addresses in changed counties are
   misplaced or unassignable.
6. **The geocoder's answers are stable enough to reuse.** The service's
   address frame changes over time. *If it fails:* a fresh query can disagree
   with the cached responses, so assignment is reproducible only by replay.

#### Evaluation criteria

- Coverage and reasons by year, method and scope, in disjoint partitions that
  reconcile to record counts.
- Instrument agreement on the stratified sample, raw and design-weighted with
  explicit denominators, interpreted as consistency, not accuracy.
- Scope vetoes and frame-compatibility checks on both the delivered state and
  each returned county.

#### Open questions for the reviewer

- **K3-Q1.** Non-exact geocoder matches, 20–23% of records, never assign.
  Is a non-exact match usually right at county level, and should it be used?
- **K3-Q2.** Instead of excluding records in multi-county ZIPs, should they be
  allocated fractionally by business-address share, or multiply imputed, with
  the fractional mass reported?
- **K3-Q3.** What external validation — a hand-verified sample, a second
  geocoder — would turn instrument agreement into an accuracy estimate?

### K4 — Survey-area population allocation

Status: Designed.

#### Notation

| Symbol | Meaning | Domain / units |
| --- | --- | --- |
| $p$ | Residence microdata area: a 2020 public-use microdata area, identified together with its state | area |
| $q$ | Workplace and migration area: a 2020 place-of-work area, identical to the 2020 migration area; a union of residence areas | area |
| $n(p,c)$ | 2020 Census population in the intersection of area $p$ and county $c$ | persons |
| $N(p)$ | 2020 population of area $p$, $\sum_c n(p,c)$ | persons |
| $f(p,c)$ | Residence allocation factor | $[0,1]$ |
| $h(q,c)$ | Workplace and migration allocation factor | $[0,1]$ |
| $\mu$ | Metropolitan statistical area (July 2023 delineation) | area |
| $n(p,\mu)$, $N(\mu)$ | 2020 population of the intersection of $p$ and $\mu$, and of $\mu$ | persons |
| $f^{\mathrm{M}}(p,\mu)$ | Area-to-metropolitan allocation fraction | $[0,1]$ |
| $\rho(p)$ | Non-metropolitan residual of area $p$ | $[0,1]$ |

#### Problem formulation and data-generating story

Survey records never identify counties. They identify state-and-area pairs in
three roles: residence area $p$ (2020 microdata areas of at least about
100,000 residents, nested in states, which split large counties and pool small
ones), workplace area $q$ (2020 place-of-work areas) and residence one year
ago (2020 migration areas, the same units as place-of-work areas). The
published composition tables list 2,486 residence areas grouped into 1,027
workplace and migration areas, before Puerto Rico is excluded. Each
workplace area is a union of residence areas and, under the documented
standard, a union of whole counties; whether 2020 areas kept that standard is
open until measured. The latent quantity is each worker's county of residence,
work or prior residence. Published: 2020 Census block populations aggregated to
area-by-county intersections (Geocorr 2022), area compositions (IPUMS
place-of-work and migration area definitions), and the intersections of
residence areas with metropolitan areas (an IPUMS 2023-delineation crosswalk).

The estimand is the set of allocation factors — the share of an area's 2020
population lying in each county or metropolitan area — used as expected
membership masses, not as individual locations.

#### Estimation / inference procedure

- **Residence:** $f(p,c) = n(p,c) / N(p)$ from integer intersection
  populations. Published rounded factors are kept only as checks, and a missing
  intersection is never repaired by renormalizing the rest.
- **Workplace and migration:**

  $$
  h(q,c) = \frac{\sum_{p \in q} n(p,c)}{\sum_{p \in q} N(p)} .
  $$

  The population sums, not an average of constituent factors, carry the
  weighting. A full-table check confirms that every county lies in exactly one
  workplace area. Where a county is split between areas, the union-based factor
  is refused for the affected units until an official intersection population
  exists; no weight is fabricated.
- **Metropolitan:** $f^{\mathrm{M}}(p,\mu) = n(p,\mu) / N(p)$ for every
  published intersection, with the non-metropolitan residual
  $\rho(p) = 1 - \sum_\mu f^{\mathrm{M}}(p,\mu)$ published rather than
  rescaled away, and the metropolitan-conditioned fraction $n(p,\mu) / N(\mu)$
  kept separately. Micropolitan membership exists only through county-to-CBSA
  membership. The survey's own metropolitan code (MET2023), which names a
  metropolitan area only where it holds a majority of an area's population and
  omits areas whose combined match error reaches 15%, is a diagnostic only.
- **Statuses.** For every record and role: applicable with factors; not in
  universe; unidentifiable; foreign; territory. A non-applicable value never
  becomes a domestic county or a zero flow, and never enters a factor's
  denominator. Work-from-home status is kept for K7's eligibility rule.
- **Distinct frames.** Population 2020; area definitions 2020; county
  composition 2022; county inventory 2025; metropolitan delineation July 2023.
  Identifier compatibility, including Connecticut's nine planning regions, is
  required; historical boundary identity is not claimed.

#### Assumptions and limitations

1. **Characteristics are homogeneous within an area.** Every worker
   characteristic is distributed across an area's counties in proportion to
   total population. *If it
   fails:* county-level survey mixes are mixtures, and variation within an area
   cannot be recovered.
2. **Residents stand in for jobs** (Cross-component assumption 5). Workplace
   areas are divided by residential population. *If it fails:* job-rich
   counties are under-allocated.
3. **2020 population serves 2022–2024 records** and the 2020–2024 five-year
   product. *If it fails:* growth since 2020 shifts true shares.
4. **2020 workplace areas consist of whole counties.** *If it fails* for some
   areas, the affected units lack factors until official intersections are
   obtained.
5. **Source-assigned areas are correct.** In the five-year product the Census
   Bureau assigned 2020 areas to pre-2022 respondents by an undocumented
   method; these are flagged in $\mathbf{z}_i$, not validated. *If it fails:*
   five-year geography inherits the assignment's errors.
6. **Allocation factors are known exactly.** No uncertainty is propagated from
   allocation. *If it fails:* allocated targets look more precise than they
   are.

#### Evaluation criteria

- Integer closure $\sum_c n(p,c) = N(p)$; factor closure to one within
  $10^{-12}$; workplace-area populations reconcile with their residence areas.
- Derived county membership of workplace areas agrees with the independent
  county composition table.
- Metropolitan intersection populations close on metropolitan totals; area
  totals reconcile with the residence population reference; published
  percentages agree with integer counts within stated rounding bounds.
- Every applicable record and role has complete factors; non-applicable
  statuses are counted separately; all partitions reconcile.

#### Open questions for the reviewer

- **K4-Q1.** For workplace areas made of several whole counties, should
  allocation use job counts — county employment, or county-by-industry
  employment from an establishment-based source — instead of residents?
- **K4-Q2.** Should survey area mixes be published only at native area level,
  leaving any county comparison to the protocol, rather than as allocated
  county mixtures?
- **K4-Q3.** Is population-share allocation to metropolitan areas sound, given
  that the survey's single-majority code is rejected precisely because it
  misplaces population?

### K5 — Establishment area-mix estimator

Status: Measured for filing year 2023.

#### Notation

| Symbol | Meaning | Domain / units |
| --- | --- | --- |
| $C(a,b)$ | Eligible submitted records in county $a$ with industry $b$ | records |
| $D(a)$ | Eligible submitted records in county $a$ | records |

#### Problem formulation and data-generating story

The population is the finite set of eligible 2023 submission records. Each has
a determinate county and a determinate native six-digit industry:

$$
E_i = \mathbb{1}[t_i = 2023]\;\mathbb{1}[\sigma_i = \text{native}]\;\mathbb{1}\big[\kappa^\star_i \text{ defined, with no crosswalk, ambiguity or unresolved indicator}\big]\;\mathbb{1}[\hat{c}_i \in \mathcal{C}].
$$

The estimand is a descriptive statistic of that set:

$$
\theta(a,b) = \frac{C(a,b)}{D(a)},
\qquad
C(a,b) = \sum_{i \in \mathcal{R}_{\mathrm{E}}} E_i\, \mathbb{1}[\hat{c}_i = a]\, \mathbb{1}[\kappa^\star_i = b],
\qquad
D(a) = \sum_{i \in \mathcal{R}_{\mathrm{E}}} E_i\, \mathbb{1}[\hat{c}_i = a].
$$

It is not an estimate of the industry composition of all establishments; every
target row carries a universe statement saying so.

#### Estimation / inference procedure

Count and divide, with $w_i = 1$. Only observed cells, $C(a,b) > 0$, are
emitted, without synthetic zeros; both the unweighted and the weighted support
of a cell equal $C(a,b)$. The standard error is null with method "none": no
claim is made about precision for a population the filings do not represent.
Plausibility
and filing-rule indicators are counted, never used as filters. A denominator
table gives, per county, assigned, eligible and industry-excluded records
(assigned = eligible + industry-excluded), including counties with assigned
records but none eligible. A support table gives, for every diagnostic
indicator, its positive true and unknown counts in each cell and each county
denominator; a target row's flags name every indicator with nonzero support,
meaning that some — not all — contributing records carry it. Every row is
labeled as awaiting the reliability gate (K9).

Measured: of 394,234 records, 356,066 are assigned a county and 38,168 are
not; of the assigned, 31,875 are excluded by industry status, leaving 324,191
eligible (234,697 placed by exact geocode, 89,494 by single-county ZIP). There
are 126,958 cells over 3,065 counties and 978 of the 1,012 six-digit
industries; 3,069 counties have denominators, four of them with no eligible
records. Eligible records per county: median 23, 95th percentile 493, maximum
7,880. Records per cell: median 1, 75th percentile 2, 95th percentile 8,
maximum 695. Within-county share sums differ from one by less than
$5 \times 10^{-15}$.

#### Assumptions and limitations

1. **A submission is an acceptable counting unit.** Duplicates and repeated
   identifiers are kept; they are negligible in 2023 but not in every year.
   *If it fails* — if establishments are the intended unit —
   multiply-submitting establishments are overweighted.
2. **Records count equally regardless of size.** A 20-employee and a
   5,000-employee establishment count the same. *If it fails* — if relatedness
   is about where work happens — the share describes establishment counts, not
   employment.
3. **Native-only eligibility is ignorable.** Translated codes (8.5% of 2023
   filings) and unknown vintages (0.6%) are excluded. *If it fails:* the
   exclusion is not random — it removes filers who kept older codes.
4. **Complete-case geography is ignorable.** The 9.7% of 2023 records without
   a county are excluded. *If it fails:* county mixes over-represent places
   with simple ZIP geography (K3, assumption 4).
5. **The rule's industry selection is ignorable** (K2, assumption 6). *If it
   fails:* every county's mix over-represents designated industries among its
   small establishments.
6. **The finite filing set is the population.** Values are exact for it, so
   no standard error is given. *If it fails* — when the values are read as
   measurements of a stable industry–place relationship — they are noisy,
   mostly single-record cells whose noise is unquantified.
7. **One year represents the relationship.** 2023 is used because it has the
   most native NAICS 2022 records. *If it fails:* single-year idiosyncrasies
   are not averaged out.

#### Evaluation criteria

- Hand-calculated fixtures for numerators, denominators and preserved
  duplicates.
- Disjoint partitions reconcile: eligible + industry-excluded + unassigned =
  source records.
- Shares sum to one within each county with eligible records; every referenced
  county and industry exists in the reference graphs with the expected level.
- Coverage is reported separately from accuracy and from representativeness;
  no support threshold is applied until the gate is set.

#### Open questions for the reviewer

- **K5-Q1.** Which is the better relatedness signal: submission shares,
  employment-weighted shares (employment is reported but unvalidated), or
  shares of deduplicated establishments?
- **K5-Q2.** With a median of one record per cell, should the target carry a
  model-based uncertainty — for example multinomial sampling within a county
  given $D(a)$ — or be shrunk, for example by a Dirichlet–multinomial prior
  toward the state or national industry mix?
- **K5-Q3.** Should translated single-candidate records, and the 2024 and 2025
  filing years, be admitted to enlarge support?

### K6 — Establishment identity and text estimators

Status: Cross-year linkage and description-cleaning rules adopted and measured
as diagnostics; the text–code pair and co-ownership targets are Required.

#### Notation

| Symbol | Meaning | Domain / units |
| --- | --- | --- |
| $\eta_i$ | Account-scoped establishment identifier, reissued when an account profile is re-created | identifier |
| $\mathrm{EIN}_i$ | Employer identification number as delivered; usable when syntactically plausible and not reconstructed by zero-padding | identifier or missing |
| $\mathrm{nm}_i$, $\lambda_i$ | Normalized establishment name; normalized full address (street, city, state, ZIP) | strings |
| $\tau_i$ | Employer-written industry description, up to 300 characters | string |
| $\tilde{\tau}_i$ | Matching key of $\tau_i$: NFKC normalization, Unicode case folding, whitespace collapsed and trimmed, punctuation kept | string |
| $\epsilon_i$ | Employer key: usable EIN, else non-empty normalized company name; undefined when both are blank | key or undefined |

#### Problem formulation and data-generating story

*Identity.* Establishments persist across filing years, but $\eta_i$ is
account-scoped, EINs are missing in early years, and addresses change or are
reformatted. The latent quantity is which records in two years belong to one
establishment; observed are $(\eta_i, \mathrm{EIN}_i, \mathrm{nm}_i,
\lambda_i)$.

*Text.* $\tau_i$ is the employer's own description of its industry. It is
often coarser than the code (one posted summary pairs "Healthcare" with a
six-digit home-health code), sometimes a copied official title, and often
stamped identically on every establishment of a multi-unit employer. The pair
$(\tau_i, K_i)$ is a noisy label: the code is self-reported and unvalidated.

*Co-ownership.* An employer operating establishments in industries $b$ and
$b'$ is evidence that $b$ and $b'$ are related through ownership.

Estimands: links between the records of two years that represent one
establishment (confirmed, weaker or unresolved); deduplicated pairs of a
description and its candidate code paths; and within-employer industry
co-occurrence, whose measure is not yet defined.

#### Estimation / inference procedure

**Linkage (adopted rule).** A candidate link shares $\eta_i$ in both years. A
confirmed link additionally requires $\eta_i$ to be unique in each year (exact
duplicate rows collapse for linkage only), the same usable unreconstructed
EIN, and the same $\lambda_i$. A changed-identifier link requires a unique
match on (usable unreconstructed EIN, $\mathrm{nm}_i$, $\lambda_i$) in both
years. Missing or reconstructed EINs, incomplete addresses and conflicting
keys are reported as weaker or unresolved evidence, never as confirmed. EIN
usability is a syntactic check only. How links feed the two targets, for
example through cross-year deduplication, is not designed.

**Text–code pairs (Required).** Compute $\tilde{\tau}_i$ and indicators for an
empty key; an exact placeholder from a finite list ("n/a", "na", "none",
"unknown", "not applicable", "not specified", "-", "--", "."); identity with
any official NAICS title at levels 2–6 in 2012, 2017 or 2022 (copied text;
identity with the record's own vintage is reported separately); and suspected
mis-encoded text, which is flagged, not repaired. Deduplicate on
$(\epsilon_i, \tilde{\tau}_i)$ before forming pairs; records with undefined
$\epsilon_i$ never form a shared group. Each pair carries the full canonical
path of every candidate in $K_i$, so it can be scored at every level;
unresolved records assert no determinate code or path.

**Co-ownership (Required).** Industry-by-industry co-occurrence among
establishments sharing an EIN. A company-name match does not establish
co-ownership. The measure, its normalization and the handling of candidate
sets are not designed.

Measured diagnostics by filing year: empty descriptions 6.1–8.0%; copied
official titles 14.8–22.4%; records repeating an employer-and-description key
53.1–58.8%; unknown employer 1.1–10.7%. Of the 2023 establishment
identifiers, 55.8% reappear in 2024 and 45.7% in 2025, and confirmed links
cover 40.7% and 33.9%; these are shares of identifiers, not of confirmed
establishments. Among uniquely matched (EIN, name, address) tuples, 8.5% and
9.2% changed identifier. With EINs missing on 99–100% of 2016–2018 records,
early years yield almost no confirmed links — none for 2016 to 2017, although
129,292 identifiers reappear.

#### Assumptions and limitations

1. **Same EIN and address means the same establishment.** *If it fails:*
   relocated establishments go unlinked, and co-located distinct
   establishments of one employer can be merged.
2. **An EIN identifies the owner.** EINs are tax-filing entities; one firm may
   hold several. *If it fails:* co-ownership within EIN misses relationships
   across a firm's EINs.
3. **Self-reported codes are the labels.** *If it fails* — when the employer
   chose the code carelessly — text–code pairs contain label noise unrelated
   to the description.
4. **Descriptions are independent of the code,** except where copied from an
   official title. *If it fails:* text–code agreement partly reflects how the
   filing form presents codes.
5. **An employer's repeated description is one observation.** *If it fails* —
   if repetition carries information — weighting is lost.
6. **Rule-shaped co-occurrence is ignorable.** Which of an employer's
   establishments file is shaped by the filing rule (K2, assumption 6). *If it
   fails:* co-ownership pairs over-represent designated industries.

#### Evaluation criteria

- Linkage diagnostics by year pair — reappearance, confirmed,
  changed-identifier and weaker evidence — each with its denominator.
- Description-content shares by year; deduplication accounting that reconciles
  to records.
- Every pair keeps the original string, its key and every indicator.

#### Open questions for the reviewer

- **K6-Q1.** How should co-ownership be normalized: raw co-occurrence
  counts, or observed co-occurrence relative to a null model such as the
  hypergeometric expectation given industry frequencies?
- **K6-Q2.** Should copied-title descriptions be excluded from text–code
  evaluation altogether, given that embedders may be trained on official
  titles?
- **K6-Q3.** Is deterministic linkage on exact address equality appropriate,
  or should probabilistic record linkage with reported match probabilities be
  used?

### K7 — Resident-survey estimators

Status: Required; inputs verified.

#### Notation

| Symbol | Meaning | Domain / units |
| --- | --- | --- |
| $p^{\mathrm{res}}_i$, $q^{\mathrm{work}}_i$, $q^{\mathrm{mig}}_i$ | Residence area, workplace area and area of residence one year ago of person $i$ | areas, or a non-applicable status |
| $\omega_i$ | Work-from-home indicator: means of transportation to work is "worked from home" (TRANWORK) | $\{0,1\}$ |
| $U_i$ | Universe indicator: civilian employed at the current job, all classes of worker (headline); private wage and salary workers (comparison) | $\{0,1\}$ |
| $Q^{\mathrm{ind}}_i$, $Q^{\mathrm{occ}}_i$ | Source allocation indicators for industry and occupation (QIND, QOCC), interpreted per product | 0, 1 or unavailable |
| $y_i$ | A worker feature: education, field of degree, wage and salary income, usual hours, weeks worked, age, sex | categorical or numeric |
| $\hat F_a$ | Weighted distribution function of a numeric feature among eligible workers of unit $a$ | $[0,1]$ |
| $\pi$ | Quantile level | $(0,1)$ |

#### Problem formulation and data-generating story

The resident survey is a stratified, clustered probability sample of housing
units and group quarters. Person weights $w_i$ are calibrated to population
controls, and 80 replicate weights $w^{(k)}_i$ follow a successive-difference
design. The extract keeps employed persons, armed forces included until the
universe filter removes them. For each worker it reports the industry and
occupation as Census categories with their NAICS- and SOC-based strings; class
of worker; detailed employment status; education; first and second field of
degree; wage and salary income and an inflation-adjusted version; earnings;
usual hours; weeks worked; age; sex; residence state and area; workplace state
and area; means of transportation, including work from home, and travel time;
residence one year ago; and a source allocation indicator for each item. Three
products are used: the core (2023 and 2024 one-year samples); the 2020–2024
five-year sample, about 2.3 times the core's size but with recoded industries
and source-assigned areas for pre-2022 respondents; and the 2022 one-year
comparator, coded in NAICS 2017.

Estimands, each built in a headline variant and an allocation-included
variant:

- **Staffing pattern:** $\theta(a,b)$ = share of universe workers in industry
  unit $a$ who are in occupation unit $b$.
- **Workplace area mix:** share of workers in work area $a$ who are in
  industry (or occupation) unit $b$, with work-from-home workers excluded by
  default. For a county,

  $$
  \hat\theta(c,b) = \frac{\sum_i w_i\, E_i\, \gamma^{\mathrm{work}}_i(c)\, B_i(b)}{\sum_i w_i\, E_i\, \gamma^{\mathrm{work}}_i(c)},
  \qquad E_i \text{ including } \omega_i = 0 .
  $$

- **Worker profile:** for code unit $a$, the distribution of each feature
  $y_i$ — shares of education levels, fields of degree, sex and age groups, and
  weighted quantiles $\hat F_a^{-1}(\pi) = \inf\{y : \hat F_a(y) \ge \pi\}$
  of wages, hours and weeks.
- **Commuting flows:** residence area $p$ to workplace area $q$,
  $\hat N(p, q) = \sum_i w_i\, E_i\, \mathbb{1}[p^{\mathrm{res}}_i = p]\,
  \mathbb{1}[q^{\mathrm{work}}_i = q]$.
- **Migration flows:** area one year ago to current area.

Which area levels are published (native areas, allocated counties,
metropolitan areas) and which measure each flow family reports (count,
origin-conditional rate, or another normalization) are not designed.

#### Estimation / inference procedure

1. **Universe.** Headline $U_i = 1$ for civilian employed persons at their
   current job, all classes of worker; a comparison universe of private wage
   and salary workers, built for comparison with establishment-based
   statistics.
2. **Pooling.** For annual-average totals the core uses $w_i / Y$ and
   $w^{(k)}_i / Y$ with $Y = 2$; shares are unaffected.
3. **Imputation.** Headline eligibility requires $Q^{\mathrm{ind}}_i = 0$ and
   $Q^{\mathrm{occ}}_i = 0$; the sensitivity variant drops that requirement.
   Indicator codes are interpreted per product and item, because a shared
   "nonzero means allocated" rule is invalid across sources; an item without
   an indicator is unavailable evidence, never "not allocated".
4. **Codes and places.** Candidate sets from K1; geographic roles from K4;
   metropolitan areas through direct intersections, never through the survey's
   majority code.
5. **Estimators.** Ratios of weighted totals in the generic form; weighted
   quantiles for numeric features.
6. **Five-year product** only for cells the core cannot support; each such
   result is reported beside the same result computed on that product's
   2023–2024 records.
7. **Comparator.** The 2022 one-year sample (NAICS 2017) tests whether
   industry embeddings hold up across a classification-vintage change.
8. **Weights** are used as delivered: the delimited values already include
   the implied decimals documented for fixed-width files.
9. **Standard errors** by replication (K9).

Measured inputs: every requested item is delivered, including all 80
replicates; state civilian employment at age 16 and over reproduces published
one-year estimates with signed gaps from −1.22% to +1.66% across 153 annual and
pooled state cells; negative replicate weights occur and are retained for
variance use only.

#### Assumptions and limitations

1. **Allocation exclusion is ignorable** within compared cells. *If it fails:*
   because the Census Bureau imputes missing industry and occupation from
   similar respondents, and allocation rates differ across groups, excluding
   allocated records shifts the composition of every cell.
2. **Two pooled years estimate a 2023–2024 annual average.** *If it fails:*
   change within the window blurs the target.
3. **Excluding work from home is ignorable** in workplace mixes. *If it
   fails* — because remote-work shares differ by industry, occupation and
   area — workplace mixes over-represent on-site work.
4. **The coded workplace is where the job is.** *If it fails* — for mobile or
   multi-site jobs — workplace geography is noisy.
5. **K4's allocation assumptions hold** for every allocated area target. *If
   it fails:* allocated county mixes are population-weighted mixtures of their
   areas' mixes.
6. **Census categories can serve as units** (K1, assumption 6). *If it
   fails:* resident-survey targets cannot be compared with establishment
   targets at the finest level.

#### Evaluation criteria

- Totals reproduce published estimates, with gaps recorded rather than tuned.
- Each five-year result is compared with its 2023–2024 counterpart; the
  vintage comparator tests robustness to the NAICS 2017-to-2022 change.
- Headline and allocation-included variants are compared.
- The panel survey's staffing pattern is a cross-source check (K8).

#### Open questions for the reviewer

- **K7-Q1.** Which measure should flow families report: counts,
  origin-conditional rates, or flows relative to those expected under
  independence?
- **K7-Q2.** Should allocated records be excluded with the remaining weights
  recalibrated to control totals, rather than simply dropped?
- **K7-Q3.** Should work-from-home workers be excluded, reported as a separate
  family, or placed at residence?

### K8 — Panel-survey estimators

Status: Required; inputs verified.

#### Notation

| Symbol | Meaning | Domain / units |
| --- | --- | --- |
| $(i,t)$ | Person $i$ observed in month $t$ | observation |
| $\mathcal{L}$ | Validated adjacent-month links $\big((i,t),(i,t+1)\big)$ | set of pairs |
| $\mathrm{mis}_{it}$ | Month in sample | 1–8 |
| $g^{\mathrm{emp}}_{it}$, $g^{\mathrm{act}}_{it}$ | Respondent's report, relative to the previous month, of the same employer (EMPSAME) and of the same usual activities and duties (ACTSAME): same, changed, or unusable | categorical |
| $\ell_{it}$ | Adjacent-month linking weight (LNKFW1MWT) | persons |
| $K^{\mathrm{ly}}_i$, $J^{\mathrm{ly}}_i$ | Candidate sets for the industry and occupation of the longest job in the previous calendar year (supplement) | sets of finest codes |
| $\mathrm{st}_i$, $\mathrm{st}^{-}_i$ | Current state and state one year ago (supplement) | states |
| $s$, $s'$ | Destination and origin states of a migration flow | states |
| $\psi_i$ | Main reason for moving (WHYMOVE) | categorical |

#### Problem formulation and data-generating story

The monthly basic files come from a rotating household panel: each household
is interviewed for four consecutive months, rests eight, and returns for four
($\mathrm{mis}_{it} = 1, \ldots, 8$). The extract holds labor-force members.
Weights are the final monthly weight, the adjacent-month linking weight and an
earner-study weight with its eligibility indicator; the public files carry no
design variables. Under dependent interviewing, when a respondent reports the
same employer and unchanged duties, last month's industry and occupation are
carried forward, so a code change without a reported job change is a coding
artifact. The annual supplement covers all persons, with its own weight, 160
replicate weights, and codes for both the current job and the longest job in
the previous calendar year.

The window opens in January 2025, when the panel's industry categories moved
to the 2022 Census list (occupations have used the 2018 list since 2020); no
transition may span December 2024 to January 2025. October 2025 was never
collected, so September-to-November 2025 pairs are two-month links.

Estimands:

- **Monthly job-change flows:** from (industry, occupation) at $t$ to
  (industry, occupation) at $t+1$, among linked pairs employed in both months
  with a reported change:
  $\hat N(a \to b) = \sum_{((i,t),(i,t+1)) \in \mathcal{L}} \ell_{it}\,
  \mathbb{1}[g^{\mathrm{emp}}_{it} = \text{changed} \lor g^{\mathrm{act}}_{it}
  = \text{changed}]\, A_{it}(a)\, B_{i,t+1}(b)$; and unemployment-to-employment
  flows from the last job's codes to the new job's.
- **Annual retrospective flows:** longest job last year to current job among
  the currently employed, $\hat N(a \to b) = \sum_i w_i\, E_i\,
  A^{\mathrm{ly}}_i(a)\, B_i(b)$, with $A^{\mathrm{ly}}_i$ built from
  $K^{\mathrm{ly}}_i$ and $J^{\mathrm{ly}}_i$.
- **State migration:** $\hat N(s' \to s) = \sum_i w_i\, E_i\,
  \mathbb{1}[\mathrm{st}^{-}_i = s']\, \mathbb{1}[\mathrm{st}_i = s]$, and a
  job-related subset restricted to $\psi_i \in$ {new job or transfer, looking
  for work, easier commute, other job-related}.
- **Cross-checks:** a staffing pattern compared with the resident survey's,
  and earner profiles.

The measure for flows (counts or rates) is not designed.

#### Estimation / inference procedure

1. **Linkage.** Adjacent months link on the validated person identifier, which
   joins records only when sex and race agree and age changes plausibly; the
   raw identifier is kept for a linkage-rate comparison; each person's records
   are ordered by month in sample.
2. **Guard.** A code change counts as an employment-to-employment transition
   only when $g^{\mathrm{emp}}_{it}$ or $g^{\mathrm{act}}_{it}$ reports a
   change; code differences without either are coding noise and are excluded.
   The guard is undefined in months in sample 1 and 5 and has other
   not-in-universe gaps, so every transition target reports the share of
   linked pairs with a usable guard.
3. **Two-month links** are flagged and kept out of month-to-month rates.
4. **Weights.** Final weight for monthly cross-sections; linking weight for
   adjacent-month links; earner weight with its eligibility imposed for
   earnings; supplement weight for supplement estimands.
5. **Earnings.** Since March 2023 earnings are released only rounded, so the
   rounded weekly-earnings and hourly-wage items are used throughout, with the
   lowest monthly hourly-wage top code across the analyzed months applied to
   all of them.
6. **Metropolitan targets** use only August 2026 and later months, or
   households whose entry month is May 2025 or later, because metropolitan
   codes are mid-transition between delineations until the phase-in completes.
7. **Codes** from K1 (Census categories to candidate sets). Industry code 9890,
   labeled military in 2025 documentation and undocumented in 2026, remains
   unresolved and is never mapped by assumption.
8. **Standard errors:** supplement by replication; monthly by a
   household-cluster bootstrap, labeled approximate (K9).

Measured inputs: 20 monthly samples and two supplements. Across 922,115
monthly records, the same-employer item reads "changed" 11,973 times, "same"
534,116, refused or unknown 302, and not in universe 375,724; the same-duties
item reads "changed" 7,339, "same" 522,057, and not in universe 392,600. Three
delivered same-employer values fall in months in sample 1 or 5, where the item
should be undefined; they are kept as source exceptions. The linking weight is
missing on every September 2025 and September 2026 record. In both supplement
years the current-job and last-year industry fields use the 2022 scheme: 33
codes that exist only in the 2022 list occur, and no 2017-only code does.
Monthly employment exceeds published levels by +0.24% to +0.80%, because the
final weight differs from the composite estimator behind official totals; the
gap is recorded, not tuned. These are unlinked coverage counts, not transition
rates.

#### Assumptions and limitations

1. **Guards are reported accurately.** *If it fails* — a respondent reports the
   same employer after a change — transitions are undercounted; spurious
   reports of change overcount them.
2. **Link validation removes false links, and linking weights correct for
   attrition** between adjacent months. *If it fails:* flows mix different
   people or over-represent stayers.
3. **Retrospective code differences reflect job changes.** The supplement
   compares the two jobs' codes with no respondent guard. *If it fails* — if
   its two jobs are coded independently — code differences include coding
   noise counted as job change.
4. **A household-cluster bootstrap approximates the design variance** without
   strata or primary sampling units. *If it fails:* monthly standard errors
   are too small.
5. **Rotation-group and month-in-sample effects are negligible.** *If it
   fails:* transition rates differ by rotation position for reasons of
   measurement.
6. **Final-weight levels are adequate for shares and flows.** The final weight
   differs from the composite estimator behind official totals, and measured
   levels sit 0.24–0.80% above them. *If it fails* — if the difference is not
   uniform across groups — shares and flows inherit a group-specific bias.

#### Evaluation criteria

- The share of linked pairs with a usable guard; a linkage-rate comparison
  between the validated and raw identifiers; two-month links excluded; no
  December 2024 to January 2025 pair can form.
- Monthly totals compared with published levels, gaps recorded.
- Panel staffing pattern compared with the resident survey's.

#### Open questions for the reviewer

- **K8-Q1.** Does the respondent guard undercount true employer changes, as
  employer-to-employer flow research using this item has examined, and
  should a correction be applied?
- **K8-Q2.** For retrospective supplement transitions, which lack a guard,
  should code differences be discounted, guarded by another item, or reported
  as an upper bound?
- **K8-Q3.** What bootstrap design — strata, rotation structure, number of
  replicates — is adequate for the monthly files without design variables?

### K9 — Uncertainty, support and reliability gate

Status: support reporting Measured for K5; standard-error methods Required;
the minimum support $n_{\min}$ is Open.

#### Notation

| Symbol | Meaning | Domain / units |
| --- | --- | --- |
| $\hat\theta^{(k)}$ | Estimate recomputed with replicate weights $w^{(k)}$ | units of $\hat\theta$ |
| $\widehat{V}$ | Estimated sampling variance | squared units of $\hat\theta$ |
| $L$ | Number of bootstrap resamples | count |
| $\hat\theta^{*(l)}$ | Estimate from the $l$-th household bootstrap resample | units of $\hat\theta$ |

#### Problem formulation and data-generating story

Survey estimates carry sampling error under their designs; the establishment
filings are not a probability sample; support counts show how many records
stand behind each value. Estimands: a standard error and its method for every
target, its unweighted and weighted support, and a minimum unweighted support
$n_{\min}$ per family below which a target is not used as a headline.

#### Estimation / inference procedure

- **Replication** (resident survey, $R = 80$; supplement, $R = 160$):

  $$
  \widehat{V}(\hat\theta) = \frac{4}{R} \sum_{k=1}^{R} \big(\hat\theta^{(k)} - \hat\theta\big)^2,
  \qquad
  \widehat{\mathrm{se}} = \widehat{V}^{1/2},
  $$

  with the whole estimator — numerator, denominator, quantile — recomputed
  under each replicate. For the pooled core, the $k$-th replicate estimate uses
  each year's $k$-th replicate weight divided by $Y$ over the stacked records.
- **Bootstrap** (monthly panel): resample households with replacement $L$
  times, recompute, and take $\widehat{\mathrm{se}}$ as the standard deviation
  of $\hat\theta^{*(l)}$; labeled approximate. Strata and $L$ are not designed.
- **None** (establishment targets): null standard error.
- **Support:** $n_\varphi(a,b)$ and $\tilde n_\varphi(a,b)$ on every target
  row.
- **Gate:** after the first full build, examine the distribution of unweighted
  support in every family and set $n_{\min}$ in a recorded decision. Until
  then no target is described as passing or failing, and every establishment
  row is labeled as awaiting the gate.

#### Assumptions and limitations

1. **Sampling dominates uncertainty.** Mapping, assignment, allocation,
   nonresponse and measurement error are not quantified. *If it fails:*
   intervals are too narrow.
2. **Replication is valid for these nonlinear estimators** — ratios and
   quantiles. *If it fails* for small cells: variance estimates are unstable.
3. **Pairing replicate $k$ across pooled years** is valid because the two
   years' designs are independent. *If it fails:* pooled standard errors are
   biased.
4. **A count threshold measures reliability.** *If it fails:* a cell with
   large support can still be imprecise (high weight variation), and a small
   one precise.
5. **Marginal standard errors suffice.** *If it fails:* any downstream
   statistic that combines targets cannot be given valid uncertainty.

#### Evaluation criteria

- Replicate standard errors recompute the full estimator; every target
  reports its method and support. No calibration of replicate standard errors
  against published margins of error for matching published tables is
  currently specified.
- The gate is set from observed support distributions, after the first full
  build, in a recorded decision.

#### Open questions for the reviewer

- **K9-Q1.** Should reliability be a support count, a coefficient of variation
  or margin-of-error rule, shrinkage, or precision weighting inside the
  scoring protocol instead of a hard gate?
- **K9-Q2.** Should small-area models (area-level shrinkage with survey
  variances) be used for county and area mixes?
- **K9-Q3.** Should targets publish replicate-level estimates, or covariances,
  so that the protocol can carry uncertainty into rank correlations between
  targets and embedding distances?

## Open questions for the reviewer

Ranked by how much the answer could change the design.

- **S1. Estimand choice.** The families publish within-unit shares, flows and
  profiles with their supports, leaving relatedness to the scoring protocol.
  Should the targets instead, or also, be established relatedness indices —
  co-agglomeration or co-location indices, labor-flow relatedness measured
  against flows expected under independence, staffing-pattern similarity,
  ownership coherence — and which normalizations are considered robust when
  the aim is to evaluate learned representations?
- **S2. Mixed resolution.** How should leaf-level embeddings be scored against
  targets defined on sets of finest codes (the survey categories), and how
  should establishment and survey families be compared when they resolve
  units at different depths?
- **S3. Complete-case exclusion throughout.** Indeterminate codes, unplaced
  records and imputed items are all handled by exclusion, with sensitivity
  variants where available. For an evaluation benchmark, would multiple
  imputation or fractional allocation with propagated uncertainty be
  preferable, and where?
- **S4. Record-level premise.** Is building every target from record-level
  data the right premise when published complete-coverage aggregates exist —
  county-by-industry establishment counts, industry-by-occupation employment
  matrices, origin–destination workplace employment? Which families would
  such tables serve better, and which would they contaminate, for example by
  being produced through the same classification structures?
- **S5. Selected establishment data.** What framing or correction makes a
  program-selected, partly voluntary filing set usable as relatedness evidence
  (K2-Q1, K2-Q2)?
- **S6. Uncertainty into the protocol.** What should targets publish so that
  downstream statistics — rank correlations against embedding distances —
  carry valid uncertainty (K9-Q3)?
- **S7. Reliability gate.** Is a support threshold chosen from observed
  distributions defensible, compared with design-based reliability rules or
  shrinkage (K9-Q1)?
- **S8. Leakage beyond the tables.** Beyond excluding targets from training,
  how should the benchmark guard against embedders pretrained on the same
  official titles, definitions or published tables (K6-Q2)?
- **S9. Time.** Are 2023 filings, 2023–2024 resident surveys and 2025–2026
  panels close enough to treat as one relatedness regime, or should families
  be indexed by period?
