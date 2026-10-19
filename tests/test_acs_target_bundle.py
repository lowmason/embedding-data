'''Detached authority, semantic reconstruction and exclusive Stage9 publication.'''

import hashlib
import json
import shutil

import polars as pl
import pytest
from acs_target_fixtures import target_runs as _target_runs  # noqa: F401

from embedding_data import acs_target_bundle as bundle
from embedding_data import target_io
from embedding_data.acs_mapping_inputs import _read_json

def verify(directory, runs, pin=None):
    return bundle.verify_bundle(
        directory,
        runs['data_dir'],
        expected_outputs_sha256=pin
        or hashlib.sha256((directory / 'outputs.json').read_bytes()).hexdigest(),
        mapping_run=runs['mapping_run'],
        expected_mapping_outputs_sha256=runs['mapping_pin'],
    )


def _two_detached_verifiers_and_exact_eight_table_replay(target_runs):
    for directory in (target_runs['first'], target_runs['replay']):
        assert {p.name for p in directory.iterdir()} == set(bundle.FILES) | {'outputs.json'}
        assert verify(directory, target_runs)['status'] == 'verified'
    compared = bundle.compare_runs(
        target_runs['first'],
        target_runs['replay'],
        data_dir=target_runs['data_dir'],
        mapping_run=target_runs['mapping_run'],
        expected_mapping_outputs_sha256=target_runs['mapping_pin'],
    )
    assert compared['equal'] is True
    assert len(compared['tables']) == 8
    assert compared['substantive_report_equal'] is True
    assert compared['trust_established'] is False
    report = _read_json(target_runs['first'] / 'report.json')
    assert len(report['products']) == 50
    assert all('empty_reason' in row for row in report['products'])


def copied_bundle(tmp_path, runs):
    directory = tmp_path / runs['first'].name
    shutil.copytree(runs['first'], directory)
    return directory


def _pin_precedes_malformed_input_parsing(tmp_path, target_runs):
    directory = copied_bundle(tmp_path, target_runs)
    (directory / 'inputs.json').write_text('{broken')
    with pytest.raises(ValueError, match='SHA|sha|pin|checksum'):
        verify(directory, target_runs, '0' * 64)


def _rehashed_semantic_corruption_is_rejected(tmp_path, target_runs, kind):
    directory = copied_bundle(tmp_path, target_runs)
    mutations = {
        'target': ('targets_observed', 'value'),
        'support': ('target_support', 'denominator_mass'),
        'replicate37': ('replicate_estimates', 'estimate'),
        'unit': ('target_units', 'code_source_token'),
        'diagnostic': ('eligibility_diagnostics', 'n_unweighted'),
        'residual': ('allocation_residuals', 'weighted_mass'),
        'missing_se': ('target_support', 'se_reason'),
        'order': ('targets_observed', None),
    }
    if kind in mutations:
        name, column = mutations[kind]
        path = directory / (name + '.parquet')
        frame = pl.read_parquet(path)
        assert frame.height
        if kind == 'order':
            frame = frame.reverse()
        else:
            condition = (
                pl.col('replicate').eq(37)
                if kind == 'replicate37'
                else pl.int_range(pl.len()).eq(0)
            )
            value = pl.lit('fabricated') if kind in {'unit', 'missing_se'} else pl.col(column) + 1
            frame = frame.with_columns(
                pl.when(condition).then(value).otherwise(pl.col(column)).alias(column)
            )
        frame.write_parquet(path)
    elif kind == 'orphan_unit':
        path = directory / 'target_units.parquet'
        frame = pl.read_parquet(path)
        orphan = frame.filter(pl.col('unit_type').eq('county')).head(1).with_columns(
            pl.lit('geography:2025:county:99999').alias('unit'),
            pl.lit('geography:2025:county:99999').alias('node_id'),
            pl.lit('99999').alias('node_code'))
        assert orphan.height == 1
        pl.concat([frame, orphan]).sort('unit_type', 'unit').write_parquet(path)
    elif kind == 'extra':
        (directory / 'extra').write_text('extra')
    else:
        path = directory / ('inputs.json' if kind == 'rules' else 'report.json')
        content = _read_json(path)
        if kind == 'rules':
            content['rules']['version'] = 'fabricated'
        else:
            content['products'][0]['target_rows'] += 1
        path.write_text(json.dumps(content))
    (directory / 'outputs.json').unlink()
    target_io.write_json(
        directory / 'outputs.json', target_io.inventory(directory, list(bundle.FILES))
    )
    with pytest.raises(ValueError):
        verify(directory, target_runs)


@pytest.mark.parametrize('run_id', ['', '../escape', 'x.part', '/absolute'])
def test_unsafe_ids_refused(tmp_path, run_id):
    with pytest.raises(ValueError):
        bundle.run_directory(tmp_path, run_id)


@pytest.mark.parametrize('occupied', ['final', 'partial', 'parent_symlink', 'final_symlink'])
def test_occupied_paths_preserved(tmp_path, occupied):
    root = tmp_path / 'derived/acs/targets'
    root.mkdir(parents=True)
    final, partial = root / 'existing', root / 'existing.part'
    if occupied == 'parent_symlink':
        root.rmdir()
        other = tmp_path / 'other'
        other.mkdir()
        root.symlink_to(other, target_is_directory=True)
    elif occupied == 'final_symlink':
        final.symlink_to(tmp_path / 'absent', target_is_directory=True)
    else:
        path = final if occupied == 'final' else partial
        path.mkdir()
        (path / 'sentinel').write_text('preserve')
    with pytest.raises((ValueError, FileExistsError)):
        bundle.build(
            tmp_path, 'existing', 'mapping', expected_mapping_outputs_sha256='0' * 64, request=None
        )
    if occupied in {'final', 'partial'}:
        assert (path / 'sentinel').read_text() == 'preserve'


def _publication_race_and_post_derivation_rule_mutation(target_runs, monkeypatch):
    original = bundle.derive_tables
    root = bundle.run_directory(target_runs['data_dir'], 'race').parent
    unrelated = root / 'unrelated.tmp'
    unrelated.write_text('preserve')

    def race(selected, scratch):
        result = original(selected, scratch)
        (root / 'race').mkdir()
        return result

    monkeypatch.setattr(bundle, 'derive_tables', race)
    with pytest.raises(FileExistsError):
        bundle.build(
            target_runs['data_dir'],
            'race',
            target_runs['mapping_run'],
            expected_mapping_outputs_sha256=target_runs['mapping_pin'],
            request=target_runs['request'],
        )
    assert list((root / 'race').iterdir()) == []
    assert not (root / 'race.part').exists()
    assert unrelated.read_text() == 'preserve'


def _post_derivation_changes_publish_no_final(target_runs, monkeypatch, mutation):
    from dataclasses import replace

    run_id = 'changed_' + mutation
    original = bundle.derive_tables
    original_freeze = bundle.freeze_target_software
    original_rules = bundle.read_rules
    source = None
    source_bytes = None

    def change_after_derivation(selected, scratch):
        nonlocal source, source_bytes
        result = original(selected, scratch)
        if mutation == 'software':

            def changed_software():
                return original_freeze() | {'python_full': 'changed'}

            monkeypatch.setattr(bundle, 'freeze_target_software', changed_software)
        elif mutation == 'rules':
            monkeypatch.setattr(
                bundle,
                'read_rules',
                lambda value: replace(original_rules(value), version='changed'),
            )
        else:
            source = selected.upstream.sources['acs/core'].parquet
            source_bytes = source.read_bytes()
            source.write_bytes(source_bytes + b'changed')
        return result

    monkeypatch.setattr(bundle, 'derive_tables', change_after_derivation)
    try:
        with pytest.raises((ValueError, pl.exceptions.PolarsError)):
            bundle.build(
                target_runs['data_dir'],
                run_id,
                target_runs['mapping_run'],
                expected_mapping_outputs_sha256=target_runs['mapping_pin'],
                request=target_runs['request'],
            )
    finally:
        if source is not None:
            source.write_bytes(source_bytes)
    final = bundle.run_directory(target_runs['data_dir'], run_id)
    assert not final.exists()
    assert not final.with_name(run_id + '.part').exists()
    assert not list(final.parent.glob(run_id + '-scratch-*'))


def _strict_json_rejects_rehashed_non_json(tmp_path, target_runs, content):
    directory = copied_bundle(tmp_path, target_runs)
    (directory / 'inputs.json').write_text(content)
    target_io.write_json(
        directory / 'outputs.json', target_io.inventory(directory, list(bundle.FILES))
    )
    with pytest.raises(ValueError):
        verify(directory, target_runs)


def _member_symlinks_are_refused(tmp_path, target_runs, member):
    directory = copied_bundle(tmp_path, target_runs)
    destination = tmp_path / 'outside'
    path = directory / member
    path.rename(destination)
    path.symlink_to(destination)
    with pytest.raises(ValueError, match='symlink'):
        verify(directory, target_runs)


def _compare_does_not_authenticate_target_inventory(target_runs):
    result = bundle.compare_runs(
        target_runs['first'],
        target_runs['replay'],
        data_dir=target_runs['data_dir'],
        mapping_run=target_runs['mapping_run'],
        expected_mapping_outputs_sha256=target_runs['mapping_pin'],
    )
    assert result['trust_established'] is False


def _owned_staging_rejects_injected_json_symlink(target_runs, monkeypatch, tmp_path):
    original = bundle.derive_tables
    outside = tmp_path / 'outside.json'
    outside.write_text('preserve')

    def inject(selected, scratch):
        tables = original(selected, scratch)
        final = bundle.run_directory(selected.data_dir, 'injected')
        (final.with_name('injected.part') / 'inputs.json').symlink_to(outside)
        return tables

    monkeypatch.setattr(bundle, 'derive_tables', inject)
    with pytest.raises(ValueError, match='symlink'):
        bundle.build(
            target_runs['data_dir'],
            'injected',
            target_runs['mapping_run'],
            expected_mapping_outputs_sha256=target_runs['mapping_pin'],
            request=target_runs['request'],
        )
    assert outside.read_text() == 'preserve'
    assert not bundle.run_directory(target_runs['data_dir'], 'injected').exists()


def test_json_write_refuses_existing_or_symlink_file(tmp_path):
    outside = tmp_path / 'outside'
    outside.write_text('preserve')
    link = tmp_path / 'linked'
    link.symlink_to(outside)
    with pytest.raises(ValueError, match='symlink'):
        bundle._write_json(link, {'changed': True})
    with pytest.raises(FileExistsError):
        bundle._write_json(outside, {'changed': True})
    assert outside.read_text() == 'preserve'


def test_authenticated_bundle_lifecycle_and_adversarial_reconstruction(target_runs, tmp_path):
    _two_detached_verifiers_and_exact_eight_table_replay(target_runs)
    _pin_precedes_malformed_input_parsing(tmp_path / 'wrong-pin', target_runs)
    for kind in (
        'target',
        'support',
        'replicate37',
        'missing_se',
        'unit',
        'rules',
        'diagnostic',
        'residual',
        'report',
        'order',
        'extra',
        'orphan_unit',
    ):
        _rehashed_semantic_corruption_is_rejected(tmp_path / kind, target_runs, kind)
    for i, content in enumerate(
        ('{"duplicate":1,"duplicate":2}', '{"value":NaN}', '{"value":Infinity}')
    ):
        _strict_json_rejects_rehashed_non_json(tmp_path / ('json-' + str(i)), target_runs, content)
    for member in ('inputs.json', 'target_support.parquet'):
        location = tmp_path / ('symlink-' + member)
        location.mkdir()
        _member_symlinks_are_refused(location, target_runs, member)
    with pytest.MonkeyPatch.context() as patch:
        _publication_race_and_post_derivation_rule_mutation(target_runs, patch)
    for mutation in ('software', 'rules', 'input'):
        with pytest.MonkeyPatch.context() as patch:
            _post_derivation_changes_publish_no_final(target_runs, patch, mutation)
    with pytest.MonkeyPatch.context() as patch:
        _owned_staging_rejects_injected_json_symlink(target_runs, patch, tmp_path)


def test_serialized_conservation_measures_annual_full_and_pooled_replicates():
    from acs_target_fixtures import projection_case

    from embedding_data.acs_target_estimation import estimate
    from embedding_data.acs_target_projection import allocate_area_mix

    fixture = projection_case()
    estimates = [estimate(fixture['native'])]
    residuals = None
    for key in ('county_product', 'msa_product'):
        allocated, output = allocate_area_mix(fixture['native'], fixture['factors'],
                                               fixture['counties'], fixture[key])
        estimates.append(estimate(allocated))
        if key == 'msa_product':
            residuals = output.collect()
    frames = {'target_support': pl.concat([item['support'].collect() for item in estimates]),
              'replicate_estimates': pl.concat(
                  [item['replicates'].collect() for item in estimates]),
              'allocation_residuals': residuals}
    measured = bundle._allocation_conservation(frames)
    assert measured['serialized_check_count'] == 166
    assert measured['serialized_failure_count'] == 0
    assert len(measured['measurements']) == 166
    full = [row for row in measured['measurements'] if row['component_year'] == 0
            and row['replicate'] == 0]
    assert {row['check'] for row in full} == {'native_to_county', 'county_to_msa_and_residuals'}
    assert all(row['expected_mass'] == 320 and row['actual_mass'] == 320 for row in full)
    split = next(row for row in full if row['check'] == 'county_to_msa_and_residuals')
    assert (split['metropolitan_mass'], split['micropolitan_mass'],
            split['no_cbsa_mass']) == (150, 50, 120)
    interior = [row for row in measured['measurements'] if row['replicate'] == 37]
    assert all(row['expected_mass'] == -28 and row['actual_mass'] == -28 for row in interior)
    assert not [row for row in measured['measurements']
                if row['component_year'] and row['replicate']]
    broken = dict(frames)
    broken['allocation_residuals'] = residuals.with_columns(
        (pl.col('weighted_mass') + 1).alias('weighted_mass'))
    with pytest.raises(ValueError, match='conservation'):
        bundle._allocation_conservation(broken)


def test_verifier_scratch_uses_physical_os_temp_base(tmp_path, monkeypatch):
    physical = tmp_path / 'physical-temp'
    physical.mkdir()
    alias = tmp_path / 'os-temp-alias'
    alias.symlink_to(physical, target_is_directory=True)
    monkeypatch.setattr(bundle, 'gettempdir', lambda: str(alias), raising=False)
    with bundle._verification_scratch() as scratch:
        assert scratch.parent == physical
        bundle.safe_path(scratch)
        assert scratch.is_dir()
    assert list(physical.iterdir()) == []
    assert alias.is_symlink()
