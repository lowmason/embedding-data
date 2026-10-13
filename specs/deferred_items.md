# Deferred items

## 1-raw-provenance — 2026-10-12
- [ ] ACS and CPS convert-if-absent (manifest audit sibling, final review Minor): if
      `csv_to_parquet` fails after `ipums_delivery.deliver()` has recorded a delivery (a Polars
      error, out of memory on the five-year extract), the only recovery is to resubmit, which
      can take hours; `osha` converts when the Parquet is absent, ACS and CPS do not. Their
      `csv_to_parquet` (`src/embedding_data/acs_benchmark_extract.py`,
      `src/embedding_data/cps_benchmark_extract.py`) also write the Parquet directly, with no
      `.part` file, unlike `osha_benchmark_download.csv_to_parquet`. See
      specs/plans/completed/1-raw-provenance.md. Size: quick-fix. Done when: both modules write
      Parquet through a `.part` rename and a re-run converts any delivered `.csv.gz` that lacks
      its Parquet without submitting a new extract. Target: Stage 7.
- [ ] Manifest audit (final review recommendation): nothing checks that every file under
      `data/raw` has an entry or that each entry's hash still matches its file, and
      `manifest.entry_for` (`src/embedding_data/manifest.py`) returns an entry without
      re-hashing the file it cites. Several failure paths (a crash between the staging rename
      and the append in `ipums_delivery.deliver`, a hand-edited raw file) are only caught by
      such an audit. Size: plan. Done when: an audit command or function lists unrecorded raw
      files and hash mismatches, and `entry_for` (or the output-manifest writer) verifies the
      hash before citing it. Target: Stage 3.
- [ ] Legacy `extract.json` version (final review Minor): the five backfilled
      `data/raw/*/*/*/extract.json` files carry `"version": null` because they were written
      before submission, while deliveries made after Stage 1 carry the API version. Size:
      quick-fix. Revisit if: a stage reads the `version` field of `extract.json`; until then
      readers must not rely on it. Target: Stage 7.
- [ ] `raw_backfill` hardening (Codex P2, review Minors): the pre-move checks accept a
      destination whose ancestor is a regular file (for example `derived/acs`), so files can
      move before `mkdir` fails and the retry then skips them; a set directory without a
      top-level `.csv.gz` is treated as migrated and a stray file there is left unrecorded and
      unreported; `Path.rename` overwrites silently on POSIX (destinations are distinct by
      construction). See `src/embedding_data/raw_backfill.py` `check_plan` and
      `plan_ipums_set`. Deferred because Task 7 already migrated the only legacy tree. Size:
      quick-fix. Revisit if: `raw_backfill` is run on another legacy tree, or the module is
      edited again.
- [ ] `raw_backfill` message wording (Task 6 review Minors): `occupied()` tells the user to
      delete "<source> (or <destination>)" for a derived Parquet, but deleting the destination
      means `osha` never rebuilds it, so a legacy-typed Parquet persists; its example "because
      `osha` converted the raw CSV" is wrong for an IPUMS collision; `check_plan` does not
      reject a path repeated within one batch of entries (cannot happen today).
      `tests/test_raw_backfill.py` pins the "(or ...)" text. Size: quick-fix. Revisit if:
      `raw_backfill` is edited again.
- [ ] `osha.is_recorded` duplicates `manifest.entry_for`'s path logic
      (`src/embedding_data/osha_benchmark_download.py`; final review Minor). Size: quick-fix.
      Done when: `is_recorded` calls `entry_for` and catches `KeyError`, or the lookup lives
      in `manifest.py`.
- [ ] `check_appendable` and its tests (re-review Minors, `src/embedding_data/manifest.py`):
      the parameter is typed `Iterable` but iterated once, so a generator passed to both
      `check_appendable` and `append_entries` leaves `append_entries` writing nothing; called on
      an empty list it still reads the manifest, which `append_entries` skips. The
      malformed-manifest test asserts only `isinstance(..., OSError)` in
      `tests/test_acs_benchmark_extract.py`; there is no direct unit test in
      `tests/test_manifest.py`. The CLAUDE.md Shared flow paragraph and the
      `ipums_delivery.py` docstring do not say that hashing and the manifest check precede the
      rename. Size: quick-fix. Done when: the parameter is a `Sequence` (or returns early on
      empty input), the assertion names the patched error, a unit test exists, and the docs
      state the order.
- [ ] `ipums_delivery.deliver` rename re-check (re-review note): the final-directory check runs
      before a wait that can last hours, so an empty `<name>/` created in the meantime would
      be replaced silently by `staging.rename`. Extract numbers are unique, so only manual
      interference could do this. Size: quick-fix. Revisit if: anything other than `deliver`
      starts writing under `data/raw/<source>/<set>/`.
- [ ] Malformed `--start` (Task 4 review Minor): `cps --start abc` raises a raw `ValueError`
      from `parse_month` in `src/embedding_data/cps_benchmark_extract.py`, before the key is
      read. Size: quick-fix. Done when: it exits 2 with a `typer.BadParameter` message.
- [ ] `retrieved_at` is the download's completion time (Task 5 review Minor): for the 475 MB
      OSHA file and the IPUMS `.csv.gz`, `datetime.now(UTC)` is taken after the download
      returns, so the manifest records when the file arrived, not when retrieval began. Size:
      quick-fix. Revisit if: a stage compares retrieval times against an IPUMS or OSHA
      release date; otherwise note "download completed" in the README manifest description.
- [ ] Blank-line style (Task 1 and Task 2 review Minors): `manifest.py` and
      `ipums_delivery.py` have one blank line where PEP 8 wants two before the first top-level
      definition; ruff's selected rules do not flag it. Size: quick-fix. Done when: both files
      have two blank lines there.

## 2-ita-300a-summaries — 2026-10-13
- [ ] Industry half of the R2.9 filing-rule flag (plan D2, P8): `flag_below_filing_size`
      covers the size half only. The rule's industry lists (29 CFR 1904 Subpart E App. A and
      Subpart B App. A) use fixed NAICS vintages and no concordance exists yet, so prefix
      matching now would mis-flag establishments. See
      specs/plans/completed/2-ita-300a-summaries.md (P8); touches `add_flags` in
      `src/embedding_data/ita_summary.py`. Size: plan. Done when: R2.9's industry half is
      evaluated with concordance candidate sets. Target: Stage 4.
- [ ] Same-name replacement at the source (plan P11): OSHA re-posted the 2016-2020 zips on
      2025-11-25 and the 2023 and 2024 zips on 2026-05-20 with `_v2` members, under unchanged
      names. A path has one manifest entry forever, so `osha summary`
      (`src/embedding_data/osha_benchmark_download.py`) never fetches a refreshed file under
      an old name. Size: quick-fix. Revisit if: OSHA re-posts a file under an existing name
      and a stage needs the revision.
- [ ] Dictionary-link gaps in `acquire_summary` (`src/embedding_data/osha_benchmark_download.py`;
      final-review fix wave): a dictionary file name is date-checked only after its download,
      and a traversal or malformed dictionary link is refused before any download but exits
      with a traceback, not a clean exit, because dictionary destinations are built by
      `file_name` outside `acquire_summary`'s `try`. No real dictionary name carries a
      through-date. Size: quick-fix. Revisit if: OSHA publishes a dated or oddly named
      dictionary link.
- [ ] Stage 2 test and hardening gaps (task-review Minors, triaged ship): (a)
      `manifest.describe_file` accepts a `datetime` for `through_date` and would write a full
      timestamp, and no test pins `through_date` as None when omitted; (b)
      `ita_catalog.check_complete` takes `max(years)` before any empty guard (unreachable
      through `parse_catalog`); (c) no test for a null `year_filing_for` or for `transcode` on
      an unknown suffix; (d) no test for missing hours beside zero employees (which of
      `flag_employment` and `flag_hours_per_employee` wins); (e) a year directory holding only
      `.part` or `.DS_Store` raises a misleading "cannot choose one of []" error, and neither
      it nor the empty-root error is tested; (f) no case-detail first-run test pins its
      request list; (g) no test mixes two non-null scientific-notation widths in one column or
      feeds `inf`/`NaN` (both probed by hand, and they pass); (h) the stacked-build test
      does not assert flag values end to end (add a fixture row with `naics_year` `0`); (i)
      an `establishment_type` whose only digits are superscripts (Unicode category No) has
      no `\d` match, so D13 nulls it instead of failing. Files:
      `tests/test_ita_summary.py`, `tests/test_ita_catalog.py`,
      `tests/test_manifest.py`, `tests/test_osha_benchmark_download.py`. Size: quick-fix.
      Done when: each gap has a test or a recorded decision to accept it.
