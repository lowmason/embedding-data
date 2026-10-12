# CPS starter test strategy

Add Hypothesis, Behave, and pytest as development dependencies. Migrate the
existing `unittest` suite to native pytest tests and fixtures. This initial
coverage exercises existing CPS behavior; it does not change extraction rules
or the ACS interface.

## Invariants and fixtures

| Invariant | Layer | Fixture |
| --- | --- | --- |
| Parsing a valid `YYYY-MM` preserves its year and month | Hypothesis unit test | Generated valid months, including January and December |
| Monthly selection includes the start month and excludes earlier samples and ASEC | Hypothesis unit test | Generated catalog around a start month |
| Each available monthly period appears once, in chronological order | Hypothesis unit test | Generated basic and supplement pairs in varying insertion orders |
| A basic sample wins over a supplement for the same month | Hypothesis unit test | Generated duplicate periods |
| ASEC selection uses 2025 onward and is independent of the monthly start | Hypothesis unit test | Generated ASEC years and starts, with explicit 2024/2025 cases |
| A dry-run writes the requested definitions without submitting or downloading | Behave CLI test | Handwritten catalog, temporary output directory, fake IPUMS client |
| `--start` changes monthly selection without writing an unrequested ASEC extract | Behave CLI test | Same catalog, later start month |

All tests are fast and offline. Hypothesis uses deterministic generation, with
explicit examples at the important boundaries. Behave runs the real Typer CLI
and extract builder; only the external IPUMS client is replaced. Scenario
resources are cleaned up independently. No real credentials or data are used.

## Execution and verification

1. Record the existing suite baseline before changing dependencies.
2. Add development dependencies and regenerate `uv.lock`.
3. Write properties and Gherkin scenarios before their step implementations.
4. Verify test sensitivity with temporary, in-memory faults; do not alter
   production extraction code for this task.
5. Run the focused CPS suite, Behave, the full unit suite, and lockfile checks.
6. Migrate unit and property tests to pytest per the user's follow-up request,
   preserve all assertions, and verify the same invariants and failure causes.

Commands suitable for a future CI job (no CI configuration currently exists):

```bash
uv sync --locked
uv run --locked pytest tests/test_cps_benchmark_extract.py tests/test_cps_properties.py -v
uv run --locked behave
uv lock --check
```

No slow or network markers are needed for this coverage. The baseline unit suite
had seven pre-existing ACS failures because its tests expect a Typer interface
that the ACS script does not provide. Parametrization may change the reported
number of cases, but those expectations remain. Report the ACS failures
separately and retain them rather than skipping them.
