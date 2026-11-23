# Deferred items

## 1-raw-provenance — 2026-10-12
- [x] ACS and CPS convert-if-absent (manifest audit sibling, final review Minor): if
      `csv_to_parquet` fails after `ipums_delivery.deliver()` has recorded a delivery (a Polars
      error, out of memory on the five-year extract), the only recovery is to resubmit, which
      can take hours; `osha` converts when the Parquet is absent, ACS and CPS do not. Their
      `csv_to_parquet` (`src/embedding_data/acs_benchmark_extract.py`,
      `src/embedding_data/cps_benchmark_extract.py`) also write the Parquet directly, with no
      `.part` file, unlike `osha_benchmark_download.csv_to_parquet`. See
      specs/plans/completed/1-raw-provenance.md. Size: quick-fix. Done when: both modules write
      Parquet through a `.part` rename and a re-run converts any delivered `.csv.gz` that lacks
      its Parquet without submitting a new extract. Target: Stage 7. → done in [plan 7](plans/completed/7-ipums-extract-verification.md):
      explicit offline `--convert-only` verifies all selected raw triples, retains existing
      Parquets and publishes validated exclusive `.part` output with no-replacement hard
      linking (stronger than overwriting rename). `tests/test_ipums_conversion.py` covers
      repeatability, offline credentials/client boundaries, failure cleanup and occupied
      paths. The [actual finding](findings/stage-7-ipums-extract-verification.md) measures
      existing Parquets; no production recovery was necessary.
- [x] Manifest audit (final review recommendation) → done in plan 3: nothing checks that every file under
      `data/raw` has an entry or that each entry's hash still matches its file, and
      `manifest.entry_for` (`src/embedding_data/manifest.py`) returns an entry without
      re-hashing the file it cites. Several failure paths (a crash between the staging rename
      and the append in `ipums_delivery.deliver`, a hand-edited raw file) are only caught by
      such an audit. Size: plan. Done when: an audit command or function lists unrecorded raw
      files and hash mismatches, and `entry_for` (or the output-manifest writer) verifies the
      hash before citing it. Target: Stage 3.
- [x] Legacy `extract.json` version (final review Minor): the five backfilled
      `data/raw/*/*/*/extract.json` files carry `"version": null` because they were written
      before submission, while deliveries made after Stage 1 carry the API version. Size:
      quick-fix. Revisit if: a stage reads the `version` field of `extract.json`; until then
      readers must not rely on it. Target: Stage 7. → done in [plan 7](plans/completed/7-ipums-extract-verification.md):
      `ipums_ddi.read_definition` explicitly preserves null/absent versions, covered by
      `tests/test_ipums_ddi.py`; the [actual finding](findings/stage-7-ipums-extract-verification.md)
      records all five API versions as unknown, independently of citation/DDI/client
      versions. Immutable historical definitions were not rewritten.
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
- [x] Industry half of the R2.9 filing-rule flag (plan D2, P8): `flag_below_filing_size`
      covers the size half only. The rule's industry lists (29 CFR 1904 Subpart E App. A and
      Subpart B App. A) use fixed NAICS vintages and no concordance exists yet, so prefix
      matching now would mis-flag establishments. See
      specs/plans/completed/2-ita-300a-summaries.md (P8); touches `add_flags` in
      `src/embedding_data/ita_summary.py`. Size: plan. Done when: R2.9's industry half is
      evaluated with concordance candidate sets. Target: Stage 4. → done in plan 4.
      Delivered separately by `filing_rules` in `ita_300a_canonical.parquet`, with
      candidate unanimity and independent legacy/reference provenance flags;
      `ita_summary.add_flags` and Stage 2 source bytes remain unchanged.
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

## 7-ipums-extract-verification — 2026-10-15
- [ ] Clarify the 2026 ASEC industry code `9890` before Stage 11 mapping. The
      actual IND/INDLY counts are 13/286 in 2026 and 7/339 in 2025. The frozen
      2025 source appendix labels it Military, while both full Census lists,
      the 2025-onward IPUMS codebook and the 2026 appendix omit it. Do not infer
      its 2026 meaning or invent a valid native leaf. See
      `specs/findings/stage-7-ipums-extract-verification.md` (V6) and
      `specs/plans/completed/7-ipums-extract-verification.md` (Handoff, Stage 11).
      Touches the later CPS category/parser and mapping work under R4/R5/V11;
      no Stage 7 microdata parser was built. Size: plan. Done when: authoritative
      field/year-specific evidence resolves the 2026 category and Stage 11 has
      regression-tested explicit special/mapping behavior retaining original
      values and provenance, with no silent leaf assignment or headline inclusion.
      → planned 2026-11-18: specs/naics-evaluation-data-roadmap.md

## embedding-evaluation-data-spec-roadmap — 2026-11-16
- [ ] ACS targets (old Stage 9): ACS staffing-pattern, workplace area-mix,
      commuting and migration targets in the shared schema (spec R3.6–R3.8,
      R3.10, R3.11 and the ACS rows of R7.2). Parked with the roadmap on
      2026-11-16, because the owner chose the ITA NAICS targets as the first
      answer. Plan 9 (`specs/plans/9-acs-targets.md`) has Tasks 1–9 merged at
      `3c3ccd0`. Its Task 10 is on hold after three failed full builds
      (`stage9_acs_targets_20261019_r1`, `_20261021_r2`, `_20261021_r3`, each
      `.part` only) and eight probes. Plan 10 (untracked, only in the
      `codex/acs-targets-design` worktree) and 12 unpushed commits on that
      branch hold the throughput work. Both plans stay on hold outside any
      roadmap (owner, 2026-11-16). See
      `specs/completed/embedding-evaluation-data-spec-roadmap.md` (Stage 9) and
      `specs/findings/stage-9-acs-targets.md`. Size: plan. Done when: a Stage 9
      ACS target bundle, with its universe, pooling, replicate-SE and
      allocation-flag helpers, is published and verified on real data, or the
      owner retires plan 9.
      → planned 2026-11-18: specs/naics-evaluation-data-roadmap.md
- [ ] CPS panel linkage and job-change flows (old Stage 11): CPS codes mapped
      to NAICS and SOC, linked person-month pairs, and occupation→occupation and
      industry→industry job-change flows (spec R4.3, R4.6–R4.9, R4.11, R5.1, the
      job-change row of R7.2 and V11 for CPS). Parked on 2026-11-16, because the
      owner chose the ITA NAICS targets as the first answer. Not started. The
      `9890` item in section `7-ipums-extract-verification` closes first. See
      `specs/completed/embedding-evaluation-data-spec-roadmap.md` (Stage 11).
      Size: design. Done when: the CPS code mapping, the linked person-month
      pairs and the CPS weight and SE helpers exist, and job-change flows are
      built on real data.
      → planned 2026-11-18: specs/naics-evaluation-data-roadmap.md
- [ ] Worker profiles and CPS cross-sections (old Stage 12): worker profiles,
      the CPS staffing check and CPS state-migration targets (spec R4.4,
      R4.10–R4.12 and the worker-profile, staffing and migration rows of R7.2).
      Parked on 2026-11-16, because the owner chose the ITA NAICS targets as the
      first answer. It needs the ACS helpers of old Stage 9 and the CPS helpers of
      old Stage 11. See `specs/completed/embedding-evaluation-data-spec-roadmap.md`
      (Stage 12). Size: design. Done when: profile tables in the
      feature-for-`unit_b` schema and ASEC state-to-state flows with the
      job-related subset are built on real data.
- [ ] Full build, size gate and comparators (old Stage 13): the V9 headline
      minimum count for all families, the complete eight-family V12 offline
      contract test, the five-year and 2022 vintage comparators, and IPUMS
      citations (spec V9, V12, R3.2, R3.3, R7.3, R8.2). Parked on 2026-11-16.
      Stage 3 of `specs/naics-evaluation-data-roadmap.md` sets the minimum count
      for the ITA NAICS targets only. This item covers the other families and the
      rest of old Stage 13. See
      `specs/completed/embedding-evaluation-data-spec-roadmap.md` (Stage 13).
      Size: design. Done when: a recorded decision sets the minimum count for the
      remaining families, V12 covers all eight families offline, the comparators
      are built, and IPUMS citations appear in README and the output manifests.

## naics-evaluation-data-roadmap — 2026-11-16
- [ ] Co-visitation evidence (Track B, O11): no free source records visit
      sequences between business types and reaches NAICS without a mapping this
      project would write. ATUS is the nearest miss: ordered diary episodes, but
      its place types have no official route to NAICS. Advan and Placer.ai are
      paid or internal-use only. NHTS records trip purpose, not place. Parked by
      the owner on 2026-11-16. See `specs/uncovered-uses-evidence-sources.md`
      (Uncovered: co-visitation) and `specs/naics-evaluation-data-stage-2-findings.md`.
      Size: design. Revisit if: the owner names a free source that records visit
      order and either codes visited places by NAICS or has an official
      published mapping to NAICS.

## 12-ita-naics-minimum-counts Step 4b review — 2026-11-17
- [ ] Stale spec path in the V9 measurement script: the docstring of
      `scripts/measure_ita_minimum_counts.py` (line 7) names
      `specs/ita-naics-minimum-counts.md`, which moved to
      `specs/completed/ita-naics-minimum-counts.md` when plan 12 retired (Codex
      P3, Step 4b review). Carried because the script is frozen at rule commit
      `d15384f`: any edit breaks that tie, and under OC3 forces both real runs
      again. The fix is a one-line docstring edit. Size: trivial. Done when: the
      docstring names the retired path, in the same commit as the next change
      that already requires a new rule commit and both real runs.

## 15-usaspending-vendor-links — 2026-11-22
- [x] D2 cost in the vendor-links bundle (final review, owner kept D2 on
      2026-11-22): a blank or invalid last update date makes a firm
      `dnb_era_record`. A read-only count showed that 6,403 firms get no industry
      from this rule alone. Each holds exactly one valid NAICS 2022 code and an
      active registration. Without D2 the eligible firms would number 38,981, not
      32,578. A rule that counts a blank date on an active registration as after
      the cutoff would give them back. It needs the owner's decision and a new
      run, because it changes `src/embedding_data/vendor_link_pairs.py`, which
      `verify` hashes. See `specs/naics-evaluation-data-stage-14-findings.md`
      ("The cost of D2") and `specs/plans/completed/15-usaspending-vendor-links.md`
      (Handoff). Size: design. Done when: the owner's resume decision after Stage 14
      keeps D2 or approves a changed rule, and an approved rule has a new run that
      passes `verify`, the independent reconciler and the preservation checks.
      → done at the resume after Stage 14 (owner, 2026-11-22, "Approve as drafted"):
      D2 stays, so no new run is needed. See the roadmap, Choices made.
- [ ] Live `acquire-sam-extract` request never tried (final review, owner ruled
      defer): the request form `date=MM%2FYYYY` and the response shape were never
      tried against the real Entity Extracts API, because the owner used the
      browser path. A first live use needs the owner's key and spends one of the
      10 daily requests. See `src/embedding_data/sam_access.py` and
      `specs/plans/completed/15-usaspending-vendor-links.md` (Task 3 ruling on the
      wire URL). Size: quick-fix. Revisit if: the owner runs `acquire-sam-extract`
      for a later extract month and the request is refused or the response differs
      from what `sam_access.py` reads.
- [ ] Stale spec path in the vendor-links reconciler: the docstring of
      `scripts/reconcile_usaspending_vendor_links.py` (line 6) names
      `specs/usaspending-vendor-links.md`, which moved to
      `specs/completed/usaspending-vendor-links.md` when plan 15 retired. Carried
      because the findings file names the script by its commit `9fd0a5b`, and a
      docstring edit would leave the script that ran differing from the one in the
      tree. The fix is a one-line docstring edit. Size: quick-fix.
      Done when: the docstring names the retired path, in the same commit as the
      next change to the script.

## 16-usaspending-vendor-links — 2026-11-22
- [x] Stale outcome number in CLAUDE.md (final review, declined to judge, outside
      the plan's Step 3 insert): the last sentence of the "USAspending vendor links
      (roadmap Stage 14)" section (`CLAUDE.md`, line 465) says "no headline minimum
      count (O18) exists yet". The roadmap's resume after Stage 14 (2026-11-22) made
      the USAspending headline minimum count O26, and O18 is the protocol section
      (`specs/naics-evaluation-data-roadmap.md`, outcome rows O18 and O26). The
      frozen Stage 14 findings (line 584) use the old label and stay unedited.
      Size: quick-fix. Done when: that CLAUDE.md sentence names O26 for the minimum
      count, in the commit that records O26's decision or in an earlier docs commit.

## 18-tri-parent-links — 2026-11-22
- [ ] Stale spec path in the TRI reconciler: the docstring of
      `scripts/reconcile_tri_parent_links.py` (line 3) names `specs/tri-parent-links.md`,
      which moved to `specs/completed/tri-parent-links.md` when plan 13 retired. Carried
      because plan 18 left the script unedited (Settled Default 3), and an edit would leave
      the script in the tree differing from the one that reconciled the first run. The
      script is not in `tri_bundle.SOFTWARE_FILES`, so `verify` does not hash it. See
      `specs/findings/stage-5-tri-parent-links.md`, "Corrections to earlier text".
      Size: quick-fix. Done when: the docstring names the retired path, in the same commit
      as the next change to the script.
- [x] Stale TRI row in the deliverable map: the row "EPA TRI parent links" of
      `specs/deliverable-map.md` (line 13 at plan 18) still says "Not built. Roadmap Stage 5,
      ready". Stage 5 completed on 2026-11-21, and plan 18 recorded its replay (run
      `stage5_tri_parent_links_20261121_r1_replay`, `specs/findings/stage-5-tri-parent-links.md`).
      Plan 18 did not edit the file, because plan 17 edits another line of it (Settled
      Default 7). Size: quick-fix. Done when: the row says that Stage 5 is built and replayed
      and names the two runs, in the commit that next edits `specs/deliverable-map.md`.
      Done in PR 52 (`11fcf80`, 2026-11-22), which names both runs in the row.

## 19-usaspending-minimum-counts — 2026-11-23
- [ ] Stale spec path in the Stage 21 measurement script: the docstring of
      `scripts/measure_usaspending_minimum_counts.py` (line 8) names
      `specs/usaspending-minimum-counts.md`, which moved to
      `specs/completed/usaspending-minimum-counts.md` when plan 19 retired. Carried
      because the script is frozen at rule commit `588ae5a`: any edit breaks that tie
      and, under OC3, forces both real runs again. The fix is a one-line docstring
      edit. `specs/tri-minimum-counts.md` (line 26) names the same old path, and it
      belongs to plan 20. Size: quick-fix. Done when: the docstring names the retired
      path, in the same commit as the next change that already requires a new rule
      commit and both real runs.

## 20-tri-minimum-counts — 2026-11-23
- [ ] Stale spec path in the Stage 22 measurement script: the docstring of
      `scripts/measure_tri_minimum_counts.py` (line 6) names `specs/tri-minimum-counts.md`,
      which moved to `specs/completed/tri-minimum-counts.md` when plan 20 retired. Carried
      because the script is frozen at rule commit `b282dd7`: any edit breaks that tie and,
      under OC3, forces both real runs again. The fix is a one-line docstring edit. Size:
      quick-fix. Done when: the docstring names the retired path, in the same commit as the
      next change that already requires a new rule commit and both real runs.
- [ ] The Stage 22 measurement script builds the help text of `main` from
      `__doc__.splitlines()[0]` (`scripts/measure_tri_minimum_counts.py`, in `main`). Python
      strips docstrings under `-OO`, so the command would fail at startup there. Nothing runs
      it that way today. Carried because the script is frozen at rule commit `b282dd7`. Size:
      quick-fix. Revisit if: a later fix to the script requires a new rule commit and both
      real runs.
