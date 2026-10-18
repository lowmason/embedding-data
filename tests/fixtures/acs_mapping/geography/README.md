# Public geography fixtures

`ct-inventory.json` preserves the exact unchanged nine-region Connecticut county-to-state
Geocorr preflight original inspected on 2026-10-16 as lossless `body_base64`. Source SHA-256:
`9931fe26b2bb829b3c5a388a8d5fa78812ebcf7d45a7b2d077856d408cce39c0`.
`ct-county-control.csv` retains the original header, descriptive-label row and all nine
data rows, stripping only trailing ASCII whitespace to satisfy repository hooks. Its
separate transformed fixture SHA-256 is recorded in the metadata; tests verify both
hashes and the exact source-to-fixture transformation.
The registered source is <https://mcdc.missouri.edu/cgi-bin/broker>; the precise CT-only
query is committed under `geocorr_county_totals_request` in the sibling
`reference-layouts.json`. It is layout/inventory evidence, never national denominators.

`ct-inventory.json` describes that public source and the explicit transformation used
to supply the nine current CT planning-region codes and names to the synthetic
Gazetteer fixture. The source bytes and transformed original-layout CSV are independently hash-checked in tests.

`population_case` in `tests/acs_mapping_fixtures.py` creates separate synthetic population
truth in the exact registered composition, MSA workbook and Geocorr CSV layouts. Those
small files receive their own honest local receipt hashes. Numeric populations and
synthetic MSA 10000/micropolitan CBSA 20000 are arithmetic examples, not public estimates.
The Stage 5 graph is assembled from matching typed synthetic county/CBSA membership and
its raw county ZIP has a real local manifest entry. The fixture uses the real
`SelectedInputs` type at the reader-unit boundary without replacing its `verify` method.
It does not claim raw-to-upstream-to-mapping integration acceptance.
