# NAICS evaluation data — Stage 25 findings: protocol section for the TRI parent links

Stage 25 of `specs/naics-evaluation-data-roadmap.md` holds its Exit (2026-11-23). The owner
approved the stage spec `specs/completed/evaluation-protocol-tri-parent-links.md` on 2026-11-23
("Approve the design"). Its section is Section 6 of `specs/evaluation-protocol.md`. Stage 23
merged first as Section 5, so this stage took Section 6 at the rebase. Stage 25 has no plan.

**What the section states.**

| Exit item | Section 6 |
| --- | --- |
| Evidence: run, pin and minimum | Run `stage5_tri_parent_links_20261121_r1`, pin `65159b83…b10f8b`, and the hashes of `tri_parent_links.parquet` and `tri_parent_link_marginals.parquet`. The Stage 22 minimum: 1 on `n_unweighted`, met by 14,204 of 14,204 rows |
| Assignment: who decides the split | naics-embedder's relatedness spec, as its owner amends it. The validation part selects, for the relatedness artifact only (P8). The sealed part judges once |
| Conditions | TR1 to TR9 |
| Who decides the scores | The same spec: the null model, the scores, the treatment of absent cells, the references, TRI's own margin record and the decision rule |

**Owner decisions this stage.** Stage 23 took P10 and P11, so the two rulings after the builder
check are P12 and P13.

| Id | Decision |
| --- | --- |
| P8 | Allow selection. TRI's validation part may select, for naics-embedder's relatedness artifact only, as CO3 allows for co-ownership. R8.4 is unchanged |
| P9 | One thin section, with the design history in the stage spec |
| P12 | No real read until the owner names in Section 6 the relatedness spec's commit that admits TRI (TR8), as W7 and VL4 do |
| P13 | The retired TRI spec gets one dated pointer after its anti-goal on model selection |

**Measured cost.** One design session on 2026-11-23. One subagent read the draft as a builder:

| Subagent | Model | Tokens | Wall time |
| --- | --- | ---: | ---: |
| Builder check of the stage spec | Opus | 180,052 | 266 s |

The check raised three points. The owner settled one (P12, asked together with P13). It also
found the clash with the Stage 23 branch over the section number and the ids, which the rebase
settled. The third point is marked as my call in the stage spec: TR6 states the overlap with
co-ownership.

**Data reads.** Read-only, with no embedder output read, on the selected runs:

1. The SHA-256 of `outputs.json` and of the two pinned Parquets, recomputed from the bytes on
   disk. Each equals its inventory value.
2. A split of the industries under naics-embedder's committed salt at `2b2029c`. The script
   first reproduced Stage 16's co-ownership counts exactly. For TRI: 359 industries (173
   validation, 186 sealed), 7,102 pairs, 3,557 (50.1%) with one industry in each part and 2,048
   with both sealed. 2,497 TRI pairs are also co-owned pairs in Section 3's table. The counts
   describe the evidence and set no rule.

No full-data command ran and no file was downloaded or written under `data/`.

**For later work.**
- **naics-embedder.** An amendment of the relatedness spec can admit TRI as a second judge and
  cite Section 6. The owner then names that commit in Section 6 before any real read (TR8). TRI
  needs its own margin record first, and TR4 asks for the mirror-pair report of CO4.
- **Track B.** It has no later stage. O11 stays parked in `specs/deferred_items.md`.

**Not claimed.** No score, ranking or split result for an embedder. No source, test or data
file changed. R8.4's text is unchanged. No TRI row trains.
