# NAICS evaluation data — Stage 15 findings: BEA input-output tables

Status: Stage 15 is stopped at Task 5 (Owner Checkpoint 5). Tasks 1 to 4 are committed.
The preflight `measure` run on the real files lists three stops and one ask. The owner
chose on 2026-11-23 to stop the stage and to record O9 and O10 as uncovered. Tasks 6 to 14
did not start. The document checks E1 to E3 are not done.

Stage 15 of `specs/naics-evaluation-data-roadmap.md` builds O9 and O10 from
`specs/bea-input-output-tables.md` under `specs/plans/22-bea-input-output-tables.md`.

## Preflight

### Preservation baseline

Before the fetch, on 2026-11-23:

- `data/raw/manifest.jsonl`: 1,552,347 bytes, SHA-256
  `72232204e21ee406134e2fb3a6d8d5b50d26295af94116fcaa46d8cdaed20efe`.
- `embedding-data audit --data-dir /Users/lowell/Projects/embedding-data/data` printed
  `0 raw provenance discrepancies`.

### Raw files

The owner approved the fetch. `bea_io_tables acquire --snapshot 2026-11-23` downloaded both
files. It needed no browser import. The host-rule checks showed no other acquisition, build
or Stage 9 job.

| File | Path under the data root | Bytes | SHA-256 | Source |
|---|---|---|---|---|
| Use tables | `raw/bea/input-output/2026-11-23/AllTablesIO.zip` | 16,335,444 | `ab316fa88157f8a96270334b1a6afa664fcf39a6c94f9c8e4ad061d930e81918` | `https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesIO.zip` |
| Concordance | `raw/bea/input-output/2026-11-23/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx` | 61,081 | `6e25267ff60ccedc0808c14153b0cdeb566a7f5e9097536c70c2b9694ef5ff47` | `https://www.bea.gov/sites/default/files/2023-10/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx` |

### The Use table

One workbook holds the 2017 detail Use table before redefinitions at producers' value:
member `IOUse_Before_Redefinitions_PRO_2017_Detail.xlsx`, sheet `2017` (414 rows, 427
columns). Its title row reads "Use Table, Before Redefinitions, Producers' Value, 2017". The
After-Redefinitions and PUR members are other tables and were not chosen.

- Header: three text rows and one blank row. Code row 5, title row 4, first value row 6,
  first value column 2. Code column 0, title column 1.
- 408 row codes and 423 column codes. 406 are Use codes. Value-added rows are `V00100`,
  `V00200`, `V00300`. Total rows are `T005`, `T006`, `T008`. The intermediate total column
  is `T001`. There are 20 final-demand columns, `F01000` to `F10S00`.
- Cell forms: 59,643 numbers, 112,941 empty cells, 0 other texts. No text zero marker
  exists.
- 7 negative interior cells.

### The concordance

Sheet `NAICS Codes`, 510 rows. The header text and the column title read "2017 NAICS". The
sheet holds one NAICS token on each row, so no separator occurs in any cell. Detail code
column 6, NAICS column 11, first row 5.

- NAICS codes by digit count: 2 digits, 2; 3 digits, 39; 4 digits, 128; 5 digits, 138;
  6 digits, 164.
- `n.a.` marks 16 BEA codes with no NAICS member. The rate is 0.0394, below the 5% ask
  threshold.
- Partial marker `*` follows `23` on 12 construction codes. `23` and `531` are each listed
  under more than one BEA code.
- Every NAICS token is in `nodes_2017` of codes run `stage4_v11_20261013_r2` (pin
  `15b958467f22a06efcfa4fbd968e1e4c9a37ab490a3ec1d670709ca6fcfe9c3a`).
- Every Use code is in the concordance, and every concordance code is in the Use table.

### Measured stops and ask

`measure` exited 1 on a draft layout (member, sheet, positions and roles as above, `n.a.` as
no-member text, `*` as partial marker). The draft is local only (`.sdd` is not committed).

| Item | Count | What the real file shows |
|---|---|---|
| Stop: `concordance_repeated_codes` | 93 | A detail code with several NAICS codes repeats on each row. The layout models only a blank code cell on a continuation row. |
| Stop: `use_cells_right_of_block` | 802 | Two columns after `F10S00` have a title and no code: "Total Final Uses (GDP)" and "Total Commodity Output" (401 rows each). The layout has no place for them. |
| Stop: `line_outside_gap_bound` | 1 | Commodity `448000`: published total 24, gap 4, 3 cells. The bound `0.5 × (3 + 1)` is 2. |
| Ask: `several_zero_forms` | 112,941 empty, 5,720 numeric `0` | Zero appears as an empty cell and as the number 0. |

For scale, the largest other commodity gap is 25 on a total of 10,172 (`333318`, 133 cells).
The largest industry gap is -15 on a total of 356,474 (`GSLGO`, 243 cells). Both are inside
the bound.

The stops come from the real file, not from a fault in a reader. The plan says never to
relax the reader to fit. Changing the layout model or the bound needs an owner decision and
a plan amendment.

## Decision

On 2026-11-23 the owner chose to stop Stage 15 at the preflight and to record O9 and O10 as
uncovered. The stage does not tick on the roadmap. No bundle exists. The branch keeps Tasks 1
to 4 and this file.

## Not done

- E1 (concordance edition from BEA's own page), E2 (BEA reuse terms) and E3 (2022 detail
  tables) are not read. Only the Task 1 Step 1 request of the E3 page was approved.
- The production layout `src/embedding_data/bea_io_layout.json` does not exist.
- Tasks 6 to 14 did not start. No target table, code table or published total was built.

## R8.4

No table of this stage feeds embedder training, curriculum, hard-negative mining or model
selection. This file holds counts only.
