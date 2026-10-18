'''Bundle safety and detached verification boundary.'''

import pytest

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    from acs_mapping_fixtures import forbid_external_access

    forbid_external_access(monkeypatch)


def test_run_directory_rejects_traversal(tmp_path):
    from embedding_data.acs_mapping_bundle import run_directory

    with pytest.raises(ValueError):
        run_directory(tmp_path, '../other')


def test_external_pin_is_checked_before_reading_inputs(tmp_path):
    from embedding_data.acs_mapping_bundle import verify_bundle

    directory = tmp_path / 'run'
    directory.mkdir()
    (directory / 'outputs.json').write_text('{}')
    with pytest.raises(ValueError, match='detached'):
        verify_bundle(directory, tmp_path, expected_outputs_sha256='0' * 64)


@pytest.fixture(scope='module')
def authenticated(tmp_path_factory):
    from acs_mapping_fixtures import run_acs_mapping_v12

    with pytest.MonkeyPatch.context() as patch:
        yield run_acs_mapping_v12(tmp_path_factory.mktemp('mapping-bundle') / 'data', patch)


@pytest.fixture
def copied(authenticated, tmp_path):
    import json
    import shutil

    root = tmp_path / 'data'
    shutil.copytree(authenticated['data_dir'], root)
    pin = json.loads(authenticated['first_control'].read_text())['outputs_sha256']
    return root, root / 'derived/acs/mapping/first', pin


def repin(directory):
    from embedding_data import manifest, target_io
    from embedding_data.acs_mapping_bundle import FILES

    target_io.write_json(directory / 'outputs.json', target_io.inventory(directory, list(FILES)))
    return manifest.sha256_file(directory / 'outputs.json')


@pytest.mark.parametrize('mutation', [
    'pin', 'raw', 'source', 'reference', 'citation', 'extra', 'directory', 'missing',
    'schema', 'count', 'order', 'duplicate', 'candidate_order', 'list_null',
    'flag', 'population', 'report', 'software', 'python', 'dependency', 'lock',
    'inventory_schema', 'json_duplicate', 'json_nonfinite',
])
def test_verifier_reconstructs_semantics_after_local_repin(copied, mutation):
    import json

    import polars as pl

    from embedding_data import target_io
    from embedding_data.acs_mapping_bundle import verify_bundle

    root, directory, pin = copied
    if mutation == 'pin':
        pin = '0' * 64
    elif mutation == 'raw':
        file = next(root.glob('raw/acs/core/*/*.csv.gz'))
        file.write_bytes(file.read_bytes() + b'changed')
    elif mutation == 'source':
        file = next(root.glob('derived/acs/core/*.parquet'))
        pl.read_parquet(file).reverse().write_parquet(file)
    elif mutation == 'reference':
        file = next(root.glob('raw/references/acs-mapping/*/*.html'))
        file.write_bytes(file.read_bytes() + b'changed')
    elif mutation == 'extra':
        (directory / 'extra').write_text('caller bytes')
    elif mutation == 'directory':
        (directory / 'extra').mkdir()
    elif mutation == 'missing':
        (directory / 'report.json').unlink()
    elif mutation in {'schema', 'count', 'order', 'duplicate', 'flag'}:
        file = directory / 'acs_core_canonical.parquet'
        frame = pl.read_parquet(file)
        if mutation == 'schema':
            frame = frame.drop('source_row')
        elif mutation == 'count':
            frame = frame.head(1)
        elif mutation == 'order':
            frame = frame.reverse()
        elif mutation == 'duplicate':
            frame = pl.concat([frame.head(1), frame.head(1), frame.tail(1)])
        else:
            frame = frame.with_columns(~pl.col('industry_flag_aggregate'))
        frame.write_parquet(file)
        pin = repin(directory)
    elif mutation in {'candidate_order', 'list_null'}:
        file = directory / 'acs_code_lookup.parquet'
        frame = pl.read_parquet(file)
        name = 'canonical_finest_candidates'
        frame = frame.with_columns(
            pl.col(name).list.reverse() if mutation == 'candidate_order'
            else pl.lit(None, dtype=pl.List(pl.String)).alias(name))
        frame.write_parquet(file)
        pin = repin(directory)
    elif mutation == 'population':
        file = directory / 'puma_county_factors.parquet'
        pl.read_parquet(file).with_columns(
            (pl.col('intersection_population') + 1)).write_parquet(file)
        pin = repin(directory)
    elif mutation == 'report':
        file = directory / 'report.json'
        value = json.loads(file.read_text())
        value['limits']['full_data_acceptance'] = True
        target_io.write_json(file, value)
        pin = repin(directory)
    elif mutation == 'inventory_schema':
        file = directory / 'outputs.json'
        value = json.loads(file.read_text())
        value['acs_core_canonical.parquet'].pop('schema')
        target_io.write_json(file, value)
        from embedding_data import manifest
        pin = manifest.sha256_file(file)
    else:
        file = directory / 'inputs.json'
        value = json.loads(file.read_text())
        if mutation == 'citation':
            value['sources']['acs/core']['raw_citations'][0]['client'] = 'forged'
        elif mutation == 'software':
            value['software']['files']['src/embedding_data/acs_mapping.py']['sha256'] = '0' * 64
        elif mutation == 'python':
            value['software']['python'] = 'changed'
        elif mutation == 'dependency':
            value['software']['dependencies']['polars'] = 'changed'
        elif mutation == 'lock':
            value['software']['uv_lock_sha256'] = '0' * 64
        target_io.write_json(file, value)
        if mutation == 'json_duplicate':
            file.write_text(file.read_text().rstrip()[:-1] + ', "run_id": "first"}')
        elif mutation == 'json_nonfinite':
            file.write_text(file.read_text().rstrip()[:-1] + ', "extra": NaN}')
        pin = repin(directory)
    before = {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}
    with pytest.raises((ValueError, OSError, KeyError, pl.exceptions.PolarsError)):
        verify_bundle(directory, root, expected_outputs_sha256=pin)
    assert before == {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}


@pytest.mark.parametrize('mutation', ['candidate_order', 'flag', 'population', 'source_order',
                                      'report', 'nested_run_id'])
def test_comparison_detects_every_substantive_change(copied, mutation):
    import json
    import shutil

    import polars as pl

    from embedding_data import target_io
    from embedding_data.acs_mapping_bundle import compare_runs

    _, first, _ = copied
    second = first.with_name('comparison')
    shutil.copytree(first, second)
    if mutation in {'report', 'nested_run_id'}:
        file = second / 'report.json'
        report = json.loads(file.read_text())
        if mutation == 'report':
            report['limits']['full_data_acceptance'] = True
        else:
            report['limits']['run_id'] = 'substantive nested identity'
        target_io.write_json(file, report)
    else:
        table, name = {
            'candidate_order': ('acs_code_lookup', 'canonical_finest_candidates'),
            'flag': ('acs_core_canonical', 'industry_flag_aggregate'),
            'population': ('puma_county_factors', 'intersection_population'),
            'source_order': ('acs_core_canonical', 'source_row'),
        }[mutation]
        file = second / (table + '.parquet')
        frame = pl.read_parquet(file)
        if mutation == 'candidate_order':
            frame = frame.with_columns(pl.col(name).list.reverse())
        elif mutation == 'flag':
            frame = frame.with_columns(~pl.col(name))
        elif mutation == 'population':
            frame = frame.with_columns(pl.col(name) + 1)
        else:
            frame = frame.reverse()
        frame.write_parquet(file)
    assert compare_runs(first, second)['equal'] is False


def test_exact_bundle_and_explicit_executing_inventory(authenticated):
    import json

    from embedding_data.acs_mapping_inputs import SOFTWARE_FILES

    directory = authenticated['first']
    assert len(list(directory.iterdir())) == 11
    records = json.loads((directory / 'outputs.json').read_text())
    assert len(records) == 10
    expected_stage8 = {
        'acs_mapping_contract', 'acs_mapping_inputs', 'acs_mapping_io',
        'acs_mapping_references', 'acs_code_references', 'acs_code_mapping',
        'acs_area_references', 'acs_ct_population', 'acs_geography_factors', 'acs_area_mapping',
        'acs_mapping_companions', 'acs_mapping_bundle', 'acs_mapping'}
    assert {p.removeprefix('src/embedding_data/').removesuffix('.py') for p in SOFTWARE_FILES
            if p.startswith('src/embedding_data/acs_') and
            p != 'src/embedding_data/acs_benchmark_extract.py'} == expected_stage8
    for family in ('codes', 'geography'):
        selected = json.loads((directory / 'inputs.json').read_text())[
            'selected_upstreams']['provenance'][family]['inputs']['implementation']
        assert set(selected).issubset(SOFTWARE_FILES)
    assert {'src/embedding_data/ipums_parity.py', 'src/embedding_data/target_io.py',
            'src/embedding_data/classification_tables.py',
            'src/embedding_data/naics_relationships.py'}.issubset(SOFTWARE_FILES)


@pytest.mark.parametrize('occupied_name', ['third', 'third.part'])
def test_occupied_names_preserve_caller_files(copied, occupied_name):
    import json

    from embedding_data.acs_mapping_bundle import build
    from embedding_data.acs_mapping_contract import SelectionRequest

    root, first, _ = copied
    occupied = first.with_name(occupied_name)
    occupied.mkdir()
    (occupied / 'sentinel').write_text('caller owned')
    inputs = json.loads((first / 'inputs.json').read_text())
    with pytest.raises(FileExistsError):
        build(root, 'third', SelectionRequest(**inputs['selected_upstreams']['request']),
              inputs['references']['reference_id'],
              expected_reference_receipt_sha256=inputs['references']['receipt_sha256'])
    assert (occupied / 'sentinel').read_text() == 'caller owned'


@pytest.mark.parametrize('failure', ['write', 'reread', 'concurrent_final', 'source', 'software'])
def test_publication_failure_cleans_only_owned_staging(copied, monkeypatch, failure):
    import json

    from embedding_data import acs_mapping_bundle as bundle
    from embedding_data.acs_mapping_contract import SelectionRequest

    root, first, pin = copied
    inputs = json.loads((first / 'inputs.json').read_text())
    before = {p.name: p.read_bytes() for p in first.iterdir()}
    if failure == 'write':
        def fail(*args, **kwargs):
            raise OSError('write failed')
        monkeypatch.setattr(bundle, 'write_companion', fail)
    elif failure == 'reread':
        def fail(*args, **kwargs):
            raise ValueError('reread failed')
        monkeypatch.setattr(bundle, '_validate_outputs', fail)
    else:
        original = bundle.publish_validated
        def mutate(staging, final, selected, snapshot, data_dir):
            if failure == 'concurrent_final':
                final.mkdir()
                (final / 'sentinel').write_text('concurrent owner')
            elif failure == 'source':
                source = selected.sources['acs/core'].parquet
                source.write_bytes(source.read_bytes() + b'changed')
            else:
                freeze = bundle.freeze_software
                def changed():
                    value = freeze()
                    value['python'] = 'changed'
                    return value
                monkeypatch.setattr(bundle, 'freeze_software', changed)
            return original(staging, final, selected, snapshot, data_dir)
        monkeypatch.setattr(bundle, 'publish_validated', mutate)
    with pytest.raises((ValueError, OSError)):
        bundle.build(root, 'third', SelectionRequest(**inputs['selected_upstreams']['request']),
                     inputs['references']['reference_id'],
                     expected_reference_receipt_sha256=inputs['references']['receipt_sha256'])
    assert not first.with_name('third.part').exists()
    if failure == 'concurrent_final':
        assert (first.with_name('third') / 'sentinel').read_text() == 'concurrent owner'
    else:
        assert not first.with_name('third').exists()
    assert before == {p.name: p.read_bytes() for p in first.iterdir()}


def test_comparison_rejects_symlinked_artifacts(copied):
    import shutil

    from embedding_data.acs_mapping_bundle import compare_runs

    _, first, _ = copied
    second = first.with_name('symlink_comparison')
    shutil.copytree(first, second)
    file = second / 'acs_code_lookup.parquet'
    file.unlink()
    file.symlink_to(first / file.name)
    with pytest.raises(ValueError, match='symlink'):
        compare_runs(first, second)


def historical_software_case():
    import sys

    from embedding_data import manifest
    from embedding_data.acs_mapping_inputs import SOFTWARE_ROOT

    name = 'src/embedding_data/cli.py'
    current = '32a86b3d07bf112fabc1edb01fd10a966e840c185642e55d00f35dfd435220b3'
    inputs = {
        'implementation': {
            name: '68778e16b7cc051745c1e34d3dee6a9fc044fd12b1f78103773984503e9f9742'},
        'dependencies': {}, 'python': sys.version,
        'uv_lock_sha256': manifest.sha256_file(SOFTWARE_ROOT / 'uv.lock')}
    context = {
        'family': 'geography', 'run_id': 'stage5_geography_20261014',
        'outputs_sha256': '5584b122d45a3617e731f7179d53e9625eb67fd15515d0cd7a5dab366132290d',
        'stage7_run_id': 'fixture_verified_stage7', 'stage7_outputs_sha256': 'a' * 64,
        'stage7_software': {'files': {name: {'sha256': current}}},
        'stage8_software': {'files': {name: {'sha256': current}}},
    }
    return inputs, context


def test_exact_owner_approved_historical_cli_rule_retains_original_inventory():
    from copy import deepcopy

    from embedding_data.acs_mapping_inputs import _upstream_software

    inputs, context = historical_software_case()
    before = deepcopy(inputs)
    diagnostic, = _upstream_software(inputs, context=context)
    assert inputs == before
    assert diagnostic['rule'] == 'stage8-owner-d5-historical-geography-cli'
    assert diagnostic['historical_creator_sha256'] == inputs['implementation'][
        'src/embedding_data/cli.py']
    assert diagnostic['executing_sha256'] == context['stage7_software']['files'][
        'src/embedding_data/cli.py']['sha256']
    assert diagnostic['historical_entrypoint_executed'] is False


@pytest.mark.parametrize('mutation', [
    'old_hash', 'new_hash', 'run', 'pin', 'family', 'missing_stage7', 'wrong_stage7',
    'missing_stage8', 'wrong_stage8', 'other_implementation', 'dependency', 'python', 'lock',
])
def test_historical_cli_rule_rejects_every_unapproved_combination(monkeypatch, mutation):
    from embedding_data import acs_mapping_inputs as inputs_module

    inputs, context = historical_software_case()
    name = 'src/embedding_data/cli.py'
    if mutation == 'old_hash':
        inputs['implementation'][name] = '0' * 64
    elif mutation == 'new_hash':
        original = inputs_module.manifest.sha256_file
        monkeypatch.setattr(inputs_module.manifest, 'sha256_file',
            lambda file: '0' * 64 if file.name == 'cli.py' else original(file))
    elif mutation == 'run':
        context['run_id'] = 'another_run'
    elif mutation == 'pin':
        context['outputs_sha256'] = '0' * 64
    elif mutation == 'family':
        context['family'] = 'codes'
    elif mutation.startswith('missing_'):
        context[mutation.removeprefix('missing_') + '_software'] = {}
    elif mutation.startswith('wrong_'):
        context[mutation.removeprefix('wrong_') + '_software']['files'][name]['sha256'] = '0' * 64
    elif mutation == 'other_implementation':
        inputs['implementation']['src/embedding_data/manifest.py'] = '0' * 64
    elif mutation == 'dependency':
        inputs['dependencies']['polars'] = 'changed'
    elif mutation == 'python':
        inputs['python'] = 'changed'
    else:
        inputs['uv_lock_sha256'] = '0' * 64
    with pytest.raises(ValueError):
        inputs_module._upstream_software(inputs, context=context)


def test_current_fixture_geography_needs_no_compatibility_exception(authenticated):
    import json

    inputs = json.loads((authenticated['first'] / 'inputs.json').read_text())
    assert inputs['selected_upstreams']['provenance']['geography']['software_compatibility'] == []


@pytest.mark.parametrize('table,column', [
    ('acs_code_lookup', 'native_vintage'),
    ('acs_area_lookup', 'release_year'),
    ('puma_county_factors', 'intersection_population'),
    ('puma_msa_factors', 'intersection_population'),
    ('puma_msa_coverage', 'puma_population'),
])
def test_reconstructed_reference_dtypes_reject_self_consistent_local_repin(copied, table, column):
    import json

    import polars as pl

    from embedding_data import target_io
    from embedding_data.acs_mapping_bundle import verify_bundle

    root, directory, _ = copied
    file = directory / (table + '.parquet')
    expected = pl.read_parquet(file)
    mutated = expected.with_columns(pl.col(column).cast(pl.Int32))
    assert mutated.equals(expected)  # Equal numeric values alone cannot enforce the contract.
    assert list(mutated.schema.items()) != list(expected.schema.items())
    mutated.write_parquet(file)
    report_file = directory / 'report.json'
    report = json.loads(report_file.read_text())
    record = target_io.file_record(file)
    report['tables'][table] = {key: record[key] for key in ('columns', 'schema', 'rows')}
    target_io.write_json(report_file, report)
    pin = repin(directory)
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    with pytest.raises(ValueError, match='ordered schema'):
        verify_bundle(directory, root, expected_outputs_sha256=pin)
    assert before == {p.name: p.read_bytes() for p in directory.iterdir()}


def test_reference_write_dtype_corruption_prevents_publication(copied, monkeypatch):
    import json
    from pathlib import Path

    import polars as pl

    from embedding_data import acs_mapping_bundle as bundle
    from embedding_data.acs_mapping_contract import SelectionRequest

    root, first, _ = copied
    inputs = json.loads((first / 'inputs.json').read_text())
    original = pl.DataFrame.write_parquet
    def corrupt(frame, file, *args, **kwargs):
        if isinstance(file, Path) and file.name == 'puma_county_factors.parquet':
            frame = frame.with_columns(pl.col('intersection_population').cast(pl.Int32))
        return original(frame, file, *args, **kwargs)

    monkeypatch.setattr(pl.DataFrame, 'write_parquet', corrupt)
    before = {p.name: p.read_bytes() for p in first.iterdir()}
    with pytest.raises(ValueError, match='ordered schema'):
        bundle.build(root, 'dtype_corruption',
                     SelectionRequest(**inputs['selected_upstreams']['request']),
                     inputs['references']['reference_id'],
                     expected_reference_receipt_sha256=inputs['references']['receipt_sha256'])
    assert not first.with_name('dtype_corruption').exists()
    assert not first.with_name('dtype_corruption.part').exists()
    assert before == {p.name: p.read_bytes() for p in first.iterdir()}
