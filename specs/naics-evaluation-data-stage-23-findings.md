# NAICS evaluation data — Stage 23 findings: protocol section for the USAspending vendor links

Stage 23 of `specs/naics-evaluation-data-roadmap.md` holds its Exit (2026-11-23). The owner
approved the stage spec `specs/completed/evaluation-protocol-usaspending-vendor-links.md` on
2026-11-23 ("Approve"). Its section is Section 5 of `specs/evaluation-protocol.md`. Stage 23 has
no plan.

**What the section states.**

| Exit item | Section 5 |
| --- | --- |
| Evidence: runs, pins and minimums | Run `stage14_vendor_links_20261122_r2`, pin `248943dc…7a2be`, and the hashes of `vendor_links.parquet` and `vendor_link_marginals.parquet`. The Stage 21 minimums: 4 for `supplier_share` (2,315 of 8,307 rows) and 3 for `buyer_share` (2,234 of 8,307 rows) |
| Assignment: who decides the split | naics-embedder's relatedness spec, or the spec to which it assigns the family, once the owner names it in Section 5 (VL4). The family judges only (P10). No part selects, and no part is read before the one opening (P11) |
| Conditions | VL1 to VL8 |
| Who decides the scores | The same consuming spec: the measures read, the null model, the scores, the reference and margin rules and the decision rule. It fixes them before it reads any value (VL3) |

**Owner decisions this stage.** P8 and P9 are taken by the Stage 25 design, so these ids
start at P10.

| Id | Decision |
| --- | --- |
| P10 | Judge only. No part of the family selects. The R8.4 exclusion stays whole |
| P11 | All at the opening. Inside the one opening, the reference arms are scored first, fixed rules pick the reference and set the margin, and only then are candidates scored |

**Measured cost.** One design session on 2026-11-23. One subagent read the draft as a builder:

| Subagent | Model | Tokens | Wall time |
| --- | --- | ---: | ---: |
| Builder check of the stage spec | Opus | 165,625 | 173 s |

The check raised three points. The owner settled one (P11). The other two are marked as my
calls in the stage spec: the ids P10 and P11, and an Assignment that allows a new panel spec,
because the relatedness panel at `2b2029c` reads co-ownership only and refuses one-direction
pairs (§4.2).

**Data reads.** Read-only, with no embedder output read, on the selected run:

1. The SHA-256 of `outputs.json` and of the two pinned Parquets, recomputed from the bytes on
   disk. Each equals its inventory value.
2. The kept rows under the two minimums: 2,315 and 2,234 rows, 1,785 cells with both rows kept,
   42 and 15 kept rows with the intra-group label. These equal the V9 decision.
3. The `universe` column: one value in all 16,614 rows, equal to `report.json`'s.
4. A split of the 689 industries under naics-embedder's committed salt at `2b2029c`: 339
   validation and 350 sealed. 1,165 of the 2,268 kept off-diagonal `supplier_share` rows have
   one industry in each part. The count describes the evidence and sets no rule.

No full-data command ran and no file was downloaded or written under `data/`.

**For later work.**
- **naics-embedder.** A roadmap resume can record that Section 5 exists, with the role "judge
  only". G4 opens for the family only after the owner names the consuming spec in Section 5.
  That spec's margin rule for this family differs from the relatedness spec's §4.6: the
  reference and the margin come from the reference arms inside the one opening.
- **Stage 25.** Its proposed TRI section is also numbered Section 5. Whichever merges second
  renumbers its section at the merge.

**Not claimed.** No score, ranking or split result for an embedder. No source, test or data
file changed. R8.4's text is unchanged. No vendor-link row trains or selects.
