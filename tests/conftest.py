import os
from unittest.mock import patch

import pytest
from hypothesis import settings
from typer.testing import CliRunner

pytest.register_assert_rewrite('acs_mapping_fixtures')

# The parallel pre-commit hooks select this profile (--hypothesis-profile=parallel). Their
# workers share the CPU, so a wall-clock deadline measures contention, not the code: under
# load, test_enrichment_preserves_current_order_and_multiplicity took 209-303 ms against
# the default 200 ms. Other runs keep the default profile and its deadline.
settings.register_profile('parallel', deadline=None)

# Tests that build a full upstream chain (raw delivery through Stage 4/5/7/8 bundles, then
# Stage 9 or reconciliation work), each at least 60 s in the 2026-11-14 serial coverage run.
# Together they were 70% of its summed test time. The pre-commit hook deselects them with
# -m 'not slow' and the pre-push / pre-merge-commit hook runs them. They are marked here,
# not in their files, because Stage 8 freezes some test files and Stage 9 owns others.
# An ID that stops matching only makes that test run at commit time again.
SLOW_TESTS = frozenset({
    'tests/test_acs_target_bundle.py::'
    'test_authenticated_bundle_lifecycle_and_adversarial_reconstruction',
    'tests/test_acs_targets_reconciliation.py::'
    'test_genuine_before_build_freeze_independent_reconciliation_and_mutations',
    'tests/test_acs_target_v12.py::test_raw_to_all_four_acs_families_is_offline_and_replayable',
    'tests/test_acs_targets_reconciliation_spill.py::'
    'test_genuine_disk_oracle_lifetimes_unknown_views_and_late_drift',
    'tests/test_acs_target_tables.py::'
    'test_complete_assembly_and_adversarial_cross_table_invariants',
    'tests/test_acs_target_assembly_spill.py::'
    'test_real_fifty_product_derive_write_and_source_independent_lifetimes',
    'tests/test_acs_target_weights.py::'
    'test_exact_weights_keep_positions_duplicates_and_literal_units',
    'tests/test_acs_ct_population.py::'
    'test_v2_national_raw_to_bundle_replay_and_independent_reconciliation',
})


def pytest_configure(config):
    config.addinivalue_line(
        'markers', 'slow: builds a full upstream bundle chain; deselected by the pre-commit '
        'hook, run by the pre-push and pre-merge-commit hook')


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.nodeid.partition('[')[0] in SLOW_TESTS:
            item.add_marker(pytest.mark.slow)

@pytest.fixture
def cli_runner():
    with patch.dict(os.environ):
        os.environ.pop('IPUMS_API_KEY', None)
        os.environ.pop('PYTHON_DOTENV_DISABLED', None)
        yield CliRunner()


@pytest.fixture
def dotenv_path(tmp_path):
    return tmp_path / '.env'


@pytest.fixture
def data_directory(tmp_path):
    return tmp_path / 'data'
