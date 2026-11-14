Use the brainstorming skill in `~/Projects/embedding-data` on new evidence sources. Read `specs/embedding-evaluation-data-spec.md` at main `147802f` first. Produce a design, sized by brainstorming, for sources that would supply the data missing for the uses in Decision 2. Stop at the owner-approved, committed spec. Do not plan, download data or build.

## Decisions

**Decision 1 (context only; recorded elsewhere).**
- *You said (2026-11-14, in a naics-embedder session):* "go with one blended space". This chose between two offered options, one blended space or one view per relation. The chosen option was described as: "You get one table and one cosine, easy to publish and use. Each use gets distances partly shaped by relations it doesn't care about. It can be judged with the data you have: train on some edge families, and judge on the families held out." Asked next whether one source could train and another judge, or one source be split at random, the owner said: "Agreed with different families, falling back to one split."
- *Reading:* naics-embedder's "type 1" artifact is one industry-relatedness embedding over the 2,125 NAICS 2022 codes. It trains on NAICS tree edges plus some embedding-data families. It is judged on whole families held out from its training, chosen from a different source where possible. Where no other family can judge, one family is split, part training and part judging.
- *Home:* naics-embedder's revised representation-split spec, being brainstormed there.
- *Approval:* there. Record nothing for it here. Its conflict with R8.4 is under Leave alone.

**Decision 2.**
- *You said (2026-11-14):* "for now, disregard graph embedding uses for which ~/Projects/embedding-data have no coverage--but for those uses (firm-level data, input-output tables), provide a blurb I can use with brainstorming in that repo." The uses, from the owner's list of what type 1 is for (owner's words in quotes; the other columns are the sender's reading):

  | Use | Data it needs | Nearest existing coverage |
  |---|---|---|
  | KYB and anomaly detection: "Comparing a company's self-reported NAICS code against the embedding of its transaction network or vendor graph" | firm-to-firm transactions or vendor links | none |
  | Peer and competitor detection: "often combined with subsidiary ownership graphs" | links between a parent and its subsidiaries, across EINs | partial: R7.2 co-ownership (line 521) covers the industries one EIN operates together, not parent-subsidiary links |
  | Holding-company classification: "aggregating the graph embeddings of its child entities" | the same ownership links, with each subsidiary's NAICS | partial: same |
  | Supply-chain dependency: "NAICS codes are connected via input-output tables or B2B transaction graphs" | directed industry-to-industry flows of goods, services or payments | worker flows only: R7.2 job-change flows, industry → industry (line 517) |
  | Look-alike prospecting: "embed customer industry graphs" | firm-to-customer-industry links | none |
  | Co-visitation and foot traffic: "predict which types of businesses people visit sequentially" | visit sequences between establishment types | partial: R7.2 area mix gives co-location, not visits |

  Asked whether the partly covered uses (peer, holding-company, co-visitation) are in scope, the owner answered "All six."
- *Reading:* this session looks for sources of the missing data for all six uses. Whether naics-embedder's type 1 ignores these uses meanwhile is recorded in naics-embedder, not here.
- *Home:* the new spec's intent and scope section: the uses and the data each lacks.
- *Approval:* the owner's review of that spec.

## Defaults to flag

Raise these with the owner as the first scope questions. Do not proceed on them silently.

1. **Free data only?** R1.2 (line 117) and lines 14-16: "Every input is free to access ... no paid data". Commercial transaction graphs and foot-traffic panels are usually paid.
   - *Recommended default:* keep free-only. If no free source covers a use, record the use as uncovered, with the sources considered and why each fails. That is an acceptable result.
   - *Effect if wrong:* the uses that need paid data stay uncovered, or the project takes on licensing terms it was built to avoid.
2. **New spec, or an amendment of this one?** The spec fixes the source count at three (lines 9, 91, 106, 117; `CLAUDE.md:7`), and its header routes it to derive-roadmap (lines 3-4).
   - *Recommended default:* a new spec under `specs/` that states how it amends R1.1 and the other three-source lines, committed through the repository's usual workflow.
   - *Effect if wrong:* two specs disagree on the source list, or the approved spec is rewritten under a brainstorm.
3. **Published aggregates.** Input-output tables are published aggregates with no records, standard errors or unweighted counts. The Core principle says targets are "computed from records in the three sources" (lines 90-91). R7.1 (line 506) requires a standard error and counts, and R7.3 (line 525) an unweighted count.
   - *Recommended default:* admit published aggregates under a stated exception, with the missing fields named and flagged, not filled.
   - *Effect if wrong:* input-output data are excluded without a decision, or the evidence contract weakens for every family.

## Constraints and traps

- **Direction:** R7.2 writes its flows as a → b (lines 517-519). R7.4's schema (line 529) has `unit_a` and `unit_b` but states no direction convention. The approved Stage 10 spec emits co-ownership as a directional share in both directions. Store new flows directed.
- **Observed, never assumed** (lines 90-91): no target is derived from code structure. A new family must meet this.
- **Rejected sources** (lines 636-651): don't re-propose one without a new reason. H-1B LCA and PERM files (line 650) are noted as candidates for a later mixed-depth extension.
- **Ownership crosses EINs.** R7.2's co-ownership is within one EIN (line 521), and a company-name fallback does not establish it (lines 247-248). A parent-subsidiary source links different EINs, which that family cannot hold. Stage 10 is defining the family now. Whether an ownership source joins it or becomes a new family is the owner's question, after Stage 10 ships.
- **Codes:** a new source must reach NAICS 2022 through R5 (line 448). Input-output tables from BEA (the Bureau of Economic Analysis) use BEA industry codes, coarser than six-digit NAICS and on an older NAICS basis. This is an unverified lead: check BEA's current benchmark tables and their NAICS concordance.
- **Licensing:** the repository is public (`lowmason/embedding-data`). Derived data stay in the gitignored `data/`, but code, specs and committed test fixtures are public, and R9.2 (lines 567-568) makes every test run from fixtures. A new source's terms must allow aggregates to leave the machine (R8.1, line 539), and its fixtures must be redistributable or synthetic. R8.3 (line 547) shows that "every output is an aggregate" is not universal.
- **Shared spec edits:** Stage 10's plan amends R2.6 in the same source spec (Stage 10 spec, "Source spec amendment"). Keep this spec's edits away from R2.6.

## Owner gates

- New (the sender's, matching this runtime's rules): no downloads and no account sign-ups. Reading a source's public documentation pages is allowed. Ask the owner before fetching any file, including a concordance.
- The spec's own gates: Rollout (line 655) and Verification (line 570).

## Leave alone

- **R8.4 and its restatements:** R8.4 (lines 550-554), `CLAUDE.md:229` and `:333`, `README.md:629`, `:778` and `:870`, `specs/evaluation-targets-methodology.md:64-67` and `:222-224`, and the Stage 10 spec's anti-goal (its line 124). Decision 1 needs some families to train type 1, and its fallback splits one family between training and judging. R8.4 forbids the first as written. The roadmap gives tuning splits to the successor evaluation-protocol spec (`specs/embedding-evaluation-data-spec-roadmap.md:128`). That amendment is a separate owner decision, taken after naics-embedder's spec proposes which families train. Specify new families as evaluation targets under R8.4 as written, and note that their role may change.
- **naics-embedder:** read its specs if useful, edit nothing.
- **Other worktrees:** `codex/acs-targets-design` (Stage 9 ACS targets; 10 commits ahead of main and 6 behind; an untracked `specs/plans/10-acs-targets.md`) and `claude/nervous-maxwell-7ab7f8` (the owner-approved Stage 10 spec, 3 commits ahead). Read the Stage 10 spec with `git show claude/nervous-maxwell-7ab7f8:specs/ita-establishment-targets.md`. Edit neither.
- **Existing R7.2 families:** don't change their definitions.

Brief: `~/.cache/agent-skills/handoffs/embedding-data/2026-11-14-uncovered-graph-uses.md`. Record Decision 2 in its Home. The naics-embedder session records Decision 1, so do not write there. Then this brief is disposable.
