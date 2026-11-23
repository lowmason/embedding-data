# NAICS evaluation data — Stage 16 findings: protocol sections for ITA co-ownership and the 2023 area mix

Stage 16 of `specs/naics-evaluation-data-roadmap.md` holds its Exit (2026-11-23). The owner
approved the stage spec `specs/completed/evaluation-protocol-ita-relatedness.md` on 2026-11-23
("Approve the design"). Its sections are Sections 3 and 4 of `specs/evaluation-protocol.md`.
Stage 24 merged first as Section 2, so this stage renumbered its sections at the merge. Stage 16
has no plan.

**What the sections state.**

| Exit item | Co-ownership (Section 3) | 2023 area mix (Section 4) |
| --- | --- | --- |
| Evidence: run and pin | `stage10_ita_establishment_20261116_r1`, pin `e19b0d58…8b09df`, and the hashes of `ita_co_ownership.parquet` and `co_ownership_marginals.parquet` | `stage6_ita_area_mix_20261014_1000_csv`, pin `084292b6…1e2473`, and the hash of `ita_area_mix.parquet` |
| Assignment: who decides the split | naics-embedder's relatedness spec (`2b2029c`). The validation part selects, for the relatedness artifact only. The sealed part judges once | No split. It may train the relatedness embedding, after the owner's R8.4 decision (G1). It never judges or selects |
| Conditions | CO1 to CO8 | AM1 to AM6 |
| Who decides the scores | naics-embedder's relatedness spec, including the null model and the choice of scores | No score |

**Owner decisions this stage.**

| Id | Decision |
| --- | --- |
| P4 | G6 in, G1 out. Selection may read co-ownership's validation part. R8.4 is unchanged |
| P5 | Every sealed co-ownership score also states the crossing share and a sensitivity score on pairs with both industries sealed (CO4) |
| P6 | Two thin sections, with the design history in the stage spec |
| P7 | The retired Stage 10 spec gets one dated pointer for G6, as it did for G2 |

**Measured cost.** One design session on 2026-11-23. One subagent read the draft as a
builder:

| Subagent | Model | Tokens | Wall time |
| --- | --- | ---: | ---: |
| Builder check of the stage spec | Opus | 188,187 | 368 s |

The check raised three points. The owner settled one (P7). The other two are marked as my
calls in the stage spec.

**Data reads.** Read-only, with no embedder output read:

1. The SHA-256 of both `outputs.json` files and of the three pinned Parquets, recomputed from
   the bytes on disk. Each equals its inventory value.
2. A count of co-owned pairs under naics-embedder's committed split salt (at `2b2029c`). 9,842
   of 19,576 pairs (50.3%) have one industry in each part. 5,159 have both in the sealed part.

No full-data command ran and no file was downloaded or written under `data/`.

**For later work.**
- **naics-embedder.** A roadmap resume can record G4 as open for co-ownership and the area mix,
  and G6 as open. G1 stays closed. CO4 asks its relatedness spec for one new report, the
  within-sealed sensitivity score, before its sealed opening.
- **Stages 23 and 25.** Section 3 is their model. At `2b2029c` the relatedness spec lets TRI
  join as a second judge, but lists USAspending subawards as unassigned. So Stage 23 finds no
  consuming spec yet.
- **R8.4 (G1).** A separate owner decision. The relatedness spec names the 2023 area mix as
  the one family that trains.

**Not claimed.** No score, ranking or split result for an embedder. No source, test or data
file changed. R8.4's text is unchanged. No co-ownership row trains, and the area mix trains
nothing until G1 opens.
