The deliverable map, as of 2026-11-19 at `8b25f4b`. Stage numbers refer to [the roadmap](naics-evaluation-data-roadmap.md). A stage is "ready" when its `Consumes` are met:

| embedding-data deliverable | Status | 1. Relatedness | 2. Text→code | 3. Economic | Still blocked by |
|---|---|---|---|---|---|
| ITA text–code pairs | Built and replayed, count gate met (minimum 1). 18,188 of 239,364 headline pairs are not copied taxonomy text | No | **Yes.** Validation part selects, sealed part judges, no pair trains. Reads follow [the evaluation protocol](evaluation-protocol.md), Section 1 | No | Nothing in this repository. naics-embedder must resume its roadmap and re-read its gates |
| ITA co-ownership | Built and replayed, count gate met | **Yes.** Role not assigned | No | No | Its own section in [the evaluation protocol](evaluation-protocol.md), which roadmap Stage 16 writes. R8.4, if it trains |
| ITA area mix, 2023 | Built and replayed, count gate met | **Yes.** Role not assigned | No | No | Its own section in [the evaluation protocol](evaluation-protocol.md), which roadmap Stage 16 writes. R8.4, if it trains |
| ACS staffing patterns | On hold (three failed full builds). Roadmap Stage 9, ready | **Yes** | No | No | Stage 9: the cause of the failed builds, then its build. Its count gate is old Stage 13, deferred |
| ACS workplace area mix | On hold. Roadmap Stage 9, ready | **Yes** | No | No | Stage 9, then its count gate (old Stage 13, deferred) |
| ACS and CPS worker profiles | Deferred (old Stage 12) | **Yes** | No | Possible later wage panel (my inference) | Roadmap Stages 9 and 11 first. Then its build and its count gate |
| ACS wage microdata (person level) | Built and replayed (Stage 17). No count gate yet (O23) | No | No | **Yes.** It judges and never trains (R8.4). naics-embedder reads it in place on this machine under its pin (R8.1) | Its section in [the evaluation protocol](evaluation-protocol.md) (O24), its count gate (O23) and naics-embedder's wage panel spec |
| CPS job-change flows | Not started. Roadmap Stage 11, ready | **Yes** | No | No | Stage 11: the 2026 meaning of `9890`, then its build. Its count gate is old Stage 13, deferred |
| EPA TRI parent links | Not built. Roadmap Stage 5, ready | **Yes** | No | No | Stage 5. Its count gate is outcome O13, on the Ranked list |
| USAspending subawards with SAM.gov NAICS | Built (Stage 14, 2026-11-22), run `stage14_vendor_links_20261122_r2`. Not replayed. No count gate yet | **Yes** | No | No | The resume after Stage 14 (replay check, acceptance finding, headline minimum count, the D2 rule). Its section in [the evaluation protocol](evaluation-protocol.md) (O18). R8.4, if it trains |
| BEA input–output tables | Not built. Roadmap Stage 15, ready | **Yes, non-headline** | No | No | Stage 15 |
| ACS commuting and migration flows, CPS state migration | ACS flows: on hold, in Stage 9's scope. CPS state migration: deferred (old Stage 12) | No (geography embedder only) | No | No | Not applicable |
| NAICS 2022 node, edge and path tables | Built | Join key only | Join key only | No | Nothing |
| ITA cross-year establishment links | Built | No (support table) | No | No | Nothing |
| Geography bundle | Built | Supports the area mixes | No | No | Nothing |
