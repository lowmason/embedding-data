# NAICS evaluation data — Stage 2 findings: evidence sources for six uncovered uses

Stage 2 of `specs/naics-evaluation-data-roadmap.md` holds its Exit (2026-11-16). The
owner approved the committed spec `specs/uncovered-uses-evidence-sources.md` on
2026-11-16 (commits `918c7fe`, `2fd489d`). Stage 2 has no plan.

**Verdicts.** Each covered verdict holds only while its open checks pass. Each build
stage settles its checks in a preflight before it trusts any data.

| Use | Outcome | Verdict | Source | Open checks |
|---|---|---|---|---|
| KYB and anomaly detection | O6 | Covered, partial | USAspending subawards, joined by UEI to SAM.gov entity NAICS | E4–E6 |
| Peer and competitor detection | O7 | Covered, partial, new family | EPA TRI facility → highest-level parent | E7–E9 |
| Holding-company classification | O8 | Covered, partial, new family | Same TRI parent links | E7–E9 |
| Supply-chain dependency | O9 | Covered, partial, non-headline | BEA 2017 benchmark input–output tables | E1–E3 |
| Look-alike prospecting | O10 | Covered, partial, non-headline | Same BEA tables, read downstream | E1–E3 |
| Co-visitation and foot traffic | O11 | Uncovered | None. ATUS is the nearest miss. | — |

**Owner decisions this stage.** The coverage rule: partial coverage counts, but a
mapping this project writes disqualifies a source. Approach: fewest sources. BEA is
non-headline. TRI parent links are a new family, not part of co-ownership.

**Measured cost.** One design session. Four subagents read documentation pages:

| Subagent | Model | Tokens | Wall time |
|---|---|---:|---:|
| Co-visitation research | Sonnet | 139,439 | 404 s |
| Ownership research | Sonnet | 168,756 | 684 s |
| Industry-flow research | Sonnet | 151,101 | 711 s |
| Builder check of the spec | Opus | 133,306 | 297 s |

**Downloads.** No file was downloaded, and no account was created. The permission
layer blocked five fetches (four PDFs and one API glossary endpoint) and one web
search. No content was read from them. ffiec.gov, the Federal Reserve's NIC site,
returned HTTP 403 to automated reads.

**For later stages.**
- Three builds cover five uses: TRI (O7, O8), BEA (O9, O10), and USAspending with
  SAM.gov (O6). Each build's first step is the preflight on its open checks. If a
  check fails, the stage stops, and the owner marks the use uncovered or promotes a
  named alternate.
- O6 needs a SAM.gov account that the owner creates. E6, SAM.gov's terms on
  Dun & Bradstreet data, is the likeliest failure.
- Each adopting stage adds its R7.2 row and applies its part of the source-spec
  amendment. Stage 3's minimum count covers only Stage 1's families and the 2023
  ITA area mix.
- TRI parent links and ITA co-ownership measure close relations. Neither should
  judge an embedding that the other trained.

**Not claimed.** No source was fetched or tested. Facts rest on public HTML pages
read on 2026-11-16, and the spec marks every other claim *unverified*. No target
was built. No output feeds embedder training or model selection (R8.4).
