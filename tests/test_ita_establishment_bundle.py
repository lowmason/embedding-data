import json
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import httpx
import polars as pl
import pytest
from ita_establishment_fixtures import FIXTURE_BASIS, seed_establishment_inputs
from target_fixtures import forbid_external_access

from embedding_data import (
    ita_co_ownership,
    ita_establishment_bundle,
    ita_establishment_expected,
    ita_establishment_inputs,
    ita_establishment_links,
    ita_index_references,
    ita_references,
    ita_summary,
    ita_text_pairs,
    manifest,
    paths,
    target_contract,
    target_io,
)
from embedding_data.ita_establishment_bundle import (
    CONTRACTS,
    FILES,
    SOFTWARE_FILES,
    TABLES,
    build,
    compare_runs,
    freeze_software,
    ordered_equal,
    run_directory,
    verify_bundle,
)
from embedding_data.ita_establishment_expected import ADOPTED_BASIS

FIRST = 'first'
INPUT_FIELDS = {
    'run_id', 'contracts', 'codes', 'source_parquet', 'canonical', 'raw', 'index_references',
    'expectations', 'rules', 'software', 'execution',
}


def build_run(data_dir, inputs, run_id, **overrides):
    options = dict(
        codes_run=inputs.codes_run,
        codes_outputs_sha256=inputs.codes_outputs_sha256,
        index_registry=inputs.index_registry,
        expectations=inputs.expectations,
    )
    options.update(overrides)
    return build(data_dir, run_id, **options)


@pytest.fixture(scope='module')
def seeded(tmp_path_factory):
    '''One seeded data root with the published run `first`, shared by the module.'''
    root = tmp_path_factory.mktemp('establishment')
    data_dir = root / 'data'
    inputs = seed_establishment_inputs(data_dir, root / 'originals')
    return SimpleNamespace(data_dir=data_dir, inputs=inputs,
                           first=build_run(data_dir, inputs, FIRST))


@pytest.fixture
def fresh(tmp_path):
    '''A seeded data root of its own, for tests that change cited inputs.'''
    data_dir = tmp_path / 'data'
    inputs = seed_establishment_inputs(data_dir, tmp_path / 'originals')
    return SimpleNamespace(data_dir=data_dir, inputs=inputs)


def run_root(data_dir):
    return run_directory(data_dir, FIRST).parent


def tree(root):
    '''Every path under root, with the bytes of each file.'''
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in sorted(root.rglob('*'))
    }


def read(directory, name):
    return json.loads((directory / name).read_text())


def copy_bundle(seeded, destination, name=FIRST):
    target = destination / name
    shutil.copytree(run_directory(seeded.data_dir, FIRST), target)
    return target


def repin(directory):
    '''Rewrite outputs.json for the current bundle bytes and return its new pin.'''
    target_io.write_json(directory / 'outputs.json', target_io.inventory(directory, list(FILES)))
    return manifest.sha256_file(directory / 'outputs.json')


def edit_json(directory, name, change):
    value = read(directory, name)
    change(value)
    target_io.write_json(directory / name, value)
    return repin(directory)


def edit_text(directory, name, change):
    file = directory / name
    file.write_text(change(file.read_text()))
    return repin(directory)


def edit_table(directory, name, change):
    file = directory / (name + '.parquet')
    change(pl.read_parquet(file)).write_parquet(file)
    return repin(directory)


def first_row(column, value):
    '''Replace the value of one column in the first row only.'''
    return lambda frame: frame.with_columns(
        pl.when(pl.int_range(pl.len()).eq(0)).then(pl.lit(value)).otherwise(pl.col(column))
        .cast(frame.schema[column]).alias(column)
    )


def keys_anywhere(value):
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in keys_anywhere(item)}
    if isinstance(value, list):
        return {key for item in value for key in keys_anywhere(item)}
    return set()


def strings_anywhere(value):
    if isinstance(value, dict):
        return {text for item in value.values() for text in strings_anywhere(item)}
    if isinstance(value, list):
        return {text for item in value for text in strings_anywhere(item)}
    return {value} if isinstance(value, str) else set()


def adopt_fixture(monkeypatch, seeded):
    '''Make the fixture summary, its Stage 3 values and its registry the adopted ones.'''
    summary = paths.derived_dir(seeded.data_dir, 'osha') / ita_summary.TABLE_NAME
    monkeypatch.setattr(ita_establishment_expected, 'ADOPTED_SOURCE', {
        'path': 'derived/osha/ita_300a_summary.parquet',
        'sha256': manifest.sha256_file(summary),
        'size': summary.stat().st_size,
    })
    monkeypatch.setattr(ita_establishment_expected, 'ADOPTED',
                        replace(seeded.inputs.expectations, basis=ADOPTED_BASIS))
    monkeypatch.setattr(ita_index_references, 'REGISTRY', seeded.inputs.index_registry)


def test_build_publishes_complete_bundle(seeded):
    directory = run_directory(seeded.data_dir, FIRST)
    assert {path.name for path in directory.iterdir()} == {*FILES, 'outputs.json'}
    assert seeded.first == {
        'run_id': FIRST,
        'directory': str(directory),
        'outputs_sha256': manifest.sha256_file(directory / 'outputs.json'),
    }
    target_contract.validate_targets(pl.scan_parquet(directory / 'ita_co_ownership.parquet'))
    assert read(directory, 'report.json')['reproduction']['basis'] == FIXTURE_BASIS
    assert read(directory, 'inputs.json')['expectations']['basis'] == FIXTURE_BASIS
    members = pl.read_parquet(directory / 'ita_text_pair_members.parquet')
    source = seeded.inputs.expectations.source_records
    assert members['source_row'].to_list() == list(range(source))


def test_verify_authenticates_pin_first(seeded, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('select_codes ran before the pin was authenticated')

    monkeypatch.setattr(ita_establishment_inputs, 'select_codes', forbidden)
    with pytest.raises(ValueError, match='detached inventory checksum differs'):
        verify_bundle(run_directory(seeded.data_dir, FIRST), seeded.data_dir,
                      expected_outputs_sha256='0' * 64)


def test_verify_detects_table_tamper(seeded, tmp_path):
    directory = copy_bundle(seeded, tmp_path)
    pin = edit_table(directory, 'ita_text_pairs', first_row('representative_string', 'tampered'))
    with pytest.raises(ValueError, match='ita_text_pairs: published table differs'):
        verify_bundle(directory, seeded.data_dir, expected_outputs_sha256=pin)


def test_occupied_names_refused(seeded):
    root = run_root(seeded.data_dir)
    before = tree(root)
    with pytest.raises(ValueError, match='already exists'):
        build_run(seeded.data_dir, seeded.inputs, FIRST)
    assert tree(root) == before
    (root / 'occupied.part').mkdir()
    with pytest.raises(ValueError, match='already exists'):
        build_run(seeded.data_dir, seeded.inputs, 'occupied')
    assert tree(root) == {**before, 'occupied.part': None}
    (root / 'occupied.part').rmdir()


def test_leftover_staging_is_refused_and_untouched(seeded):
    leftover = run_root(seeded.data_dir) / 'killed.part'
    leftover.mkdir()
    (leftover / 'records.parquet').write_bytes(b'bytes of a killed build')
    with pytest.raises(ValueError, match='already exists'):
        build_run(seeded.data_dir, seeded.inputs, 'killed')
    assert tree(leftover) == {'records.parquet': b'bytes of a killed build'}
    assert not run_directory(seeded.data_dir, 'killed').exists()
    result = build_run(seeded.data_dir, seeded.inputs, 'fresh_after_kill')
    assert {path.name for path in Path(result['directory']).iterdir()} == {*FILES, 'outputs.json'}


def test_failure_cleans_only_own_staging(seeded, monkeypatch):
    root = run_root(seeded.data_dir)
    before = tree(root)

    def failing(records):
        raise ValueError('estimate failed')

    monkeypatch.setattr(ita_co_ownership, 'estimate', failing)
    with pytest.raises(ValueError, match='estimate failed'):
        build_run(seeded.data_dir, seeded.inputs, 'failed')
    assert not (root / 'failed.part').exists()
    assert not (root / 'failed').exists()
    assert tree(root) == before


def test_reproduction_mismatch_fails_build(seeded):
    expected = seeded.inputs.expectations
    v2 = {pair: dict(cells) for pair, cells in expected.v2.items()}
    v2[(2024, 2025)]['n_same_ein_address'] += 1
    with pytest.raises(ValueError, match='V2 reproduction differs'):
        build_run(seeded.data_dir, seeded.inputs, 'mismatch',
                  expectations=replace(expected, v2=v2))
    assert not run_directory(seeded.data_dir, 'mismatch').exists()
    assert not (run_root(seeded.data_dir) / 'mismatch.part').exists()


def test_adopted_source_gate(seeded, monkeypatch):
    production = ita_index_references.REGISTRY
    adopt_fixture(monkeypatch, seeded)
    registry = seeded.inputs.index_registry
    with pytest.raises(ValueError, match='takes no explicit expectations'):
        build_run(seeded.data_dir, seeded.inputs, 'adopted_explicit')
    other = {**registry, 'naics_index_2012': replace(registry['naics_index_2012'],
                                                     url='https://other.test/index.xlsx')}
    with pytest.raises(ValueError, match='adopted source requires the production index registry'):
        build_run(seeded.data_dir, seeded.inputs, 'adopted_other', expectations=None,
                  index_registry=other)
    result = build_run(seeded.data_dir, seeded.inputs, 'adopted', expectations=None)
    directory = Path(result['directory'])
    assert read(directory, 'report.json')['reproduction']['basis'] == ADOPTED_BASIS
    verified = verify_bundle(directory, seeded.data_dir,
                             expected_outputs_sha256=result['outputs_sha256'])
    assert verified['reproduction']['basis'] == ADOPTED_BASIS
    monkeypatch.setattr(ita_index_references, 'REGISTRY', production)
    with pytest.raises(ValueError, match='production index registry'):
        verify_bundle(directory, seeded.data_dir, expected_outputs_sha256=result['outputs_sha256'])


def test_changed_software_refused_before_publication(seeded, monkeypatch):
    real = ita_establishment_bundle.freeze_software
    calls = []

    def changing():
        calls.append(True)
        frozen = real()
        return frozen if len(calls) == 1 else {**frozen, 'python': 'changed'}

    monkeypatch.setattr(ita_establishment_bundle, 'freeze_software', changing)
    with pytest.raises(ValueError, match='software changed'):
        build_run(seeded.data_dir, seeded.inputs, 'software')
    assert len(calls) == 2
    assert not run_directory(seeded.data_dir, 'software').exists()
    assert not (run_root(seeded.data_dir) / 'software.part').exists()


def test_compare_runs_equal_and_unequal(seeded, tmp_path):
    replay = build_run(seeded.data_dir, seeded.inputs, 'replay')
    first = run_directory(seeded.data_dir, FIRST)
    result = compare_runs(first, Path(replay['directory']))
    assert result['equal'] is True
    assert result['report_equal'] is True
    assert result['trust_established'] is False
    assert set(result['tables']) == set(TABLES)
    tampered = tmp_path / 'replay'
    shutil.copytree(replay['directory'], tampered)
    edit_table(tampered, 'co_ownership_support', first_row('j_2023', 0))
    unequal = compare_runs(first, tampered)
    assert unequal['equal'] is False
    assert unequal['tables']['co_ownership_support']['values_equal'] is False
    assert unequal['trust_established'] is False


def test_software_files_cover_loaded_modules():
    code = '\n'.join([
        'import json, sys',
        'from pathlib import Path',
        'import embedding_data.ita_establishment_bundle',
        'from embedding_data import paths',
        'names = [n for n in sys.modules if n == "embedding_data" '
        'or n.startswith("embedding_data.")]',
        'files = sorted(Path(sys.modules[n].__file__).resolve()'
        '.relative_to(paths.PROJECT_ROOT).as_posix() for n in names)',
        'print(json.dumps({"files": files, "dotenv": "dotenv" in sys.modules, '
        '"ipumspy": "ipumspy" in sys.modules}))',
    ])
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
                            check=True)
    loaded = json.loads(result.stdout)
    assert loaded['dotenv'] is False
    assert loaded['ipumspy'] is False
    assert {*loaded['files'], 'pyproject.toml', 'uv.lock'} == set(SOFTWARE_FILES)


# Additional coverage beyond the plan tests.

def test_run_directory_is_under_the_osha_targets_root(tmp_path):
    assert run_directory(tmp_path, 'run_1') == (
        tmp_path / 'derived' / 'osha' / 'establishment-targets' / 'run_1')
    for unsafe in ('../escape', '.hidden', 'a/b', ''):
        with pytest.raises(ValueError, match='unsafe run ID'):
            run_directory(tmp_path, unsafe)


ORDERED = pl.LazyFrame(
    {'n': [1, 2, None], 'labels': [['a'], [], None]},
    schema={'n': pl.Int64, 'labels': pl.List(pl.String)},
)
ORDERED_CASES = {
    'identical': (ORDERED, True, True, 3),
    'null_against_value': (ORDERED.with_columns(pl.col('n').fill_null(3)), True, False, 3),
    'list_value': (ORDERED.with_columns(labels=pl.Series([['a'], ['b'], None])), True, False, 3),
    'row_order': (ORDERED.reverse(), True, False, 3),
    'extra_null_row': (pl.concat([ORDERED, pl.LazyFrame({'n': [None], 'labels': [None]},
                                                        schema=ORDERED.collect_schema())]),
                       True, False, 4),
    'dtype': (ORDERED.with_columns(pl.col('n').cast(pl.Int32)), False, False, 3),
    'column_order': (ORDERED.select('labels', 'n'), False, False, 3),
}


@pytest.mark.parametrize('case', ORDERED_CASES)
def test_ordered_equal_compares_order_values_and_schema(case):
    second, schema_equal, values_equal, rows = ORDERED_CASES[case]
    assert ordered_equal(ORDERED, second) == {
        'schema_equal': schema_equal,
        'values_equal': values_equal,
        'first_rows': 3,
        'second_rows': rows,
    }


def test_ordered_equal_accepts_empty_frames():
    empty = ORDERED.clear()
    assert ordered_equal(empty, empty) == {
        'schema_equal': True, 'values_equal': True, 'first_rows': 0, 'second_rows': 0}


def test_verify_accepts_published_bundle(seeded, monkeypatch):
    before = tree(seeded.data_dir)
    directory = run_directory(seeded.data_dir, FIRST)
    real = ita_co_ownership.estimate
    during = []

    def observe(records):
        during.append(tree(seeded.data_dir))
        return real(records)

    monkeypatch.setattr(ita_co_ownership, 'estimate', observe)
    verified = verify_bundle(directory, seeded.data_dir,
                             expected_outputs_sha256=seeded.first['outputs_sha256'])
    report = read(directory, 'report.json')
    assert verified == {
        'run_id': FIRST,
        'outputs_sha256': seeded.first['outputs_sha256'],
        'reproduction': report['reproduction'],
        'rows': {name: pl.scan_parquet(directory / (name + '.parquet'))
                 .select(pl.len()).collect().item() for name in TABLES},
    }
    assert report['reproduction'] == {'basis': FIXTURE_BASIS, 'source_records': 'equal',
                                      'v1': 'equal', 'v2': 'equal'}
    assert during == [before]
    assert tree(seeded.data_dir) == before


def test_bundle_records_inputs_report_and_inventory(seeded):
    directory = run_directory(seeded.data_dir, FIRST)
    inputs = read(directory, 'inputs.json')
    assert set(inputs) == INPUT_FIELDS
    assert inputs['run_id'] == FIRST
    assert inputs['contracts'] == CONTRACTS
    assert {key: inputs['codes'][key] for key in ('run_id', 'outputs_sha256')} == {
        'run_id': seeded.inputs.codes_run, 'outputs_sha256': seeded.inputs.codes_outputs_sha256}
    codes = run_directory(seeded.data_dir, FIRST).parents[2] / 'codes' / seeded.inputs.codes_run
    assert inputs['codes']['outputs'] == read(codes, 'outputs.json')
    raw_paths = [citation['path'] for citation in inputs['raw']]
    assert raw_paths == sorted(set(raw_paths))
    titles = {'references/naics/' + url.rsplit('/', 1)[1]
              for url in ita_references.TITLE_FILES.values()}
    indexes = {'references/' + reference.relative
               for reference in seeded.inputs.index_registry.values()}
    assert titles | indexes <= set(raw_paths)
    entries = {entry.path: entry for entry in manifest.read_manifest(
        paths.manifest_path(seeded.data_dir))}
    for citation in inputs['raw']:
        assert citation == json.loads(json.dumps(asdict(entries[citation['path']])))
    assert inputs['index_references'] == json.loads(json.dumps(
        {kind: asdict(reference) for kind, reference in seeded.inputs.index_registry.items()}))
    assert inputs['expectations'] == seeded.inputs.expectations.to_json()
    assert set(inputs['rules']) == {'headline', 'co_ownership', 'links'}
    assert inputs['software'] == freeze_software()
    assert set(inputs['execution']) == {'commit', 'dirty', 'created_at'}

    report = read(directory, 'report.json')
    assert report['contracts'] == CONTRACTS
    assert report['size_gate'] == 'pending'
    assert report['universe'] == ita_co_ownership.UNIVERSE
    assert report['limits'] and all(isinstance(text, str) and text for text in report['limits'])
    assert not keys_anywhere(report) & {'run_id', 'created_at', 'commit', 'sha256',
                                        'outputs_sha256'}
    assert FIRST not in strings_anywhere(report)
    outputs = read(directory, 'outputs.json')
    assert outputs == target_io.inventory(directory, list(FILES))
    for name in TABLES:
        record = outputs[name + '.parquet']
        assert report['tables'][name] == {
            key: record[key] for key in ('rows', 'columns', 'schema')}
    assert [row['year_filing_for'] for row in report['v1_by_year']] == list(range(2016, 2026))
    assert [row['year_filing_for'] for row in report['index_by_year']] == list(
        range(2016, 2026))
    assert set(report['links']['pairs']) == {
        f'{base}-{later}' for base, later in ita_establishment_expected.YEAR_PAIRS}
    assert {'n_pairs', 'n_records'} <= set(report['pairs'])
    assert {'N', 'n_cells'} <= set(report['co_ownership'])


def test_verify_refuses_unpublished_name_and_malformed_pin(seeded, tmp_path):
    partial = copy_bundle(seeded, tmp_path, name=FIRST + '.part')
    with pytest.raises(ValueError, match='not published'):
        verify_bundle(partial, seeded.data_dir, expected_outputs_sha256=seeded.first[
            'outputs_sha256'])
    with pytest.raises(ValueError, match='invalid detached checksum'):
        verify_bundle(run_directory(seeded.data_dir, FIRST), seeded.data_dir,
                      expected_outputs_sha256=seeded.first['outputs_sha256'].upper())


def add_directory(directory):
    (directory / 'extra').mkdir()
    return manifest.sha256_file(directory / 'outputs.json')


def change_unpinned(directory):
    (directory / 'report.json').write_text(
        (directory / 'report.json').read_text().replace('"pending"', '"changed"'))
    return manifest.sha256_file(directory / 'outputs.json')


def drop_inventory_schema(directory):
    outputs = read(directory, 'outputs.json')
    for name in TABLES:
        for key in ('rows', 'columns', 'schema'):
            del outputs[name + '.parquet'][key]
    target_io.write_json(directory / 'outputs.json', outputs)
    return manifest.sha256_file(directory / 'outputs.json')


LAYOUT_CASES = {
    'extra_directory': (add_directory, 'bundle file set differs'),
    'unpinned_change': (change_unpinned, 'inventory hash or size differs'),
    'inventory_without_schema': (drop_inventory_schema, 'output inventory records differ'),
}


@pytest.mark.parametrize('case', LAYOUT_CASES)
def test_verify_refuses_bundle_layout(seeded, tmp_path, monkeypatch, case):
    def forbidden(*args, **kwargs):
        raise AssertionError('select_codes ran before the bundle layout was checked')

    change, message = LAYOUT_CASES[case]
    directory = copy_bundle(seeded, tmp_path)
    pin = change(directory)
    monkeypatch.setattr(ita_establishment_inputs, 'select_codes', forbidden)
    with pytest.raises(ValueError, match=message):
        verify_bundle(directory, seeded.data_dir, expected_outputs_sha256=pin)


def duplicate_key(text):
    return text.replace('{\n', '{\n  "size_gate": "pending",\n', 1)


def not_a_number(text):
    return text.replace('"size_gate": "pending"', '"size_gate": NaN', 1)


def extra_newline(text):
    return text + '\n'


JSON_CASES = {
    'report_duplicate_key': ('report.json', duplicate_key, 'duplicate JSON key'),
    'report_nan': ('report.json', not_a_number, 'non-finite JSON number'),
    'report_noncanonical': ('report.json', extra_newline, 'report.json: not canonical JSON'),
    'inputs_noncanonical': ('inputs.json', extra_newline, 'inputs.json: not canonical JSON'),
    'outputs_noncanonical': ('outputs.json', extra_newline, 'outputs.json: not canonical JSON'),
    'report_not_json': ('report.json', lambda text: 'not json\n', 'report.json: not valid JSON'),
    'report_not_object': ('report.json', lambda text: '[]\n', 'report.json: not a JSON object'),
}


@pytest.mark.parametrize('case', JSON_CASES)
def test_verify_reads_json_strictly(seeded, tmp_path, case):
    name, change, message = JSON_CASES[case]
    directory = copy_bundle(seeded, tmp_path)
    file = directory / name
    file.write_text(change(file.read_text()))
    pin = manifest.sha256_file(directory / 'outputs.json')
    if name != 'outputs.json':
        outputs = read(directory, 'outputs.json')
        outputs[name] = target_io.file_record(file)
        target_io.write_json(directory / 'outputs.json', outputs)
        pin = manifest.sha256_file(directory / 'outputs.json')
    with pytest.raises(ValueError, match=message):
        verify_bundle(directory, seeded.data_dir, expected_outputs_sha256=pin)


def rename_copy(seeded, tmp_path):
    directory = copy_bundle(seeded, tmp_path, name='renamed')
    return directory, seeded.first['outputs_sha256']


def edit_copy(name, change):
    def apply(seeded, tmp_path):
        directory = copy_bundle(seeded, tmp_path)
        return directory, edit_json(directory, name, change)
    return apply


def set_path(*keys_and_value):
    *keys, value = keys_and_value

    def change(document):
        for key in keys[:-1]:
            document = document[key]
        document[keys[-1]] = value
    return change


def delete_path(*keys):
    def change(document):
        for key in keys[:-1]:
            document = document[key]
        del document[keys[-1]]
    return change


RECORDED_CASES = {
    'renamed': (rename_copy, 'recorded run ID differs from the directory'),
    'input_contracts': (edit_copy('inputs.json', set_path('contracts', 'links', 'other')),
                        'contract versions differ'),
    'report_contracts': (edit_copy('report.json', set_path('contracts', 'pairs', 'other')),
                         'contract versions differ'),
    'missing_field': (edit_copy('inputs.json', delete_path('rules')),
                      'recorded inputs are malformed'),
    'malformed_reference': (
        edit_copy('inputs.json', delete_path('index_references', 'naics_index_2012', 'sheet')),
        'recorded inputs are malformed'),
    'codes_pin': (edit_copy('inputs.json', set_path('codes', 'outputs_sha256', '0' * 64)),
                  'detached inventory checksum differs'),
    'claimed_adopted_basis': (edit_copy('inputs.json',
                                        set_path('expectations', 'basis', ADOPTED_BASIS)),
                              'a bundle of another source must not claim the adopted basis'),
    'recorded_index_pin': (
        edit_copy('inputs.json', set_path('index_references', 'naics_index_2022', 'sha256',
                                          'f' * 64)),
        'SHA-256 differs from the registered original'),
    'software': (edit_copy('inputs.json', set_path('software', 'python', 'other')),
                 'executing software differs from the build'),
    'rules': (edit_copy('inputs.json', set_path('rules', 'links', 'other')),
              'recorded inputs differ from the recomputation'),
    'raw': (edit_copy('inputs.json', lambda inputs: inputs['raw'].pop()),
            'recorded inputs differ from the recomputation'),
    'report': (edit_copy('report.json', set_path('size_gate', 'passed')),
               'published report differs from the recomputation'),
}


@pytest.mark.parametrize('case', RECORDED_CASES)
def test_verify_refuses_recorded_differences(seeded, tmp_path, case):
    prepare, message = RECORDED_CASES[case]
    directory, pin = prepare(seeded, tmp_path)
    with pytest.raises(ValueError, match=message):
        verify_bundle(directory, seeded.data_dir, expected_outputs_sha256=pin)


def test_verify_requires_adopted_expectations_and_registry(seeded, monkeypatch, tmp_path):
    production = ita_index_references.REGISTRY
    adopt_fixture(monkeypatch, seeded)
    result = build_run(seeded.data_dir, seeded.inputs, 'adopted_edited', expectations=None)
    directory = tmp_path / 'adopted_edited'
    shutil.copytree(result['directory'], directory)

    def change(inputs):
        inputs['expectations']['v1']['2016']['n_rows'] += 1

    pin = edit_json(directory, 'inputs.json', change)
    with pytest.raises(ValueError, match='an adopted bundle must record the adopted expectations'):
        verify_bundle(directory, seeded.data_dir, expected_outputs_sha256=pin)
    monkeypatch.setattr(ita_index_references, 'REGISTRY', production)
    with pytest.raises(ValueError,
                       match='an adopted bundle must record the production index registry'):
        verify_bundle(Path(result['directory']), seeded.data_dir,
                      expected_outputs_sha256=result['outputs_sha256'])


def no_publication(data_dir, run_id):
    return (not run_directory(data_dir, run_id).exists()
            and not (run_root(data_dir) / (run_id + '.part')).exists())


def test_build_refuses_extra_staging_file(seeded, monkeypatch):
    real = target_io.write_json

    def stray(file, value):
        real(file, value)
        if file.name == 'report.json':
            (file.parent / 'stray.txt').write_text('stray')

    monkeypatch.setattr(target_io, 'write_json', stray)
    with pytest.raises(ValueError, match='staged bundle files differ'):
        build_run(seeded.data_dir, seeded.inputs, 'stray')
    assert no_publication(seeded.data_dir, 'stray')


def test_build_refuses_final_that_appears_before_publication(seeded, monkeypatch):
    real = ita_establishment_bundle.freeze_software
    final = run_directory(seeded.data_dir, 'appeared')
    calls = []

    def appear():
        calls.append(True)
        if len(calls) == 2:
            final.mkdir()
        return real()

    monkeypatch.setattr(ita_establishment_bundle, 'freeze_software', appear)
    with pytest.raises(ValueError, match='final run name already exists'):
        build_run(seeded.data_dir, seeded.inputs, 'appeared')
    assert final.is_dir() and not any(final.iterdir())
    assert not (run_root(seeded.data_dir) / 'appeared.part').exists()
    final.rmdir()


SERIALIZED_CASES = {
    'unvalidated_value': ('ita_text_pairs.parquet', first_row('representative_string', 'x'),
                          'ita_text_pairs: serialized table differs from the in-memory result'),
    'validator': ('ita_text_pairs.parquet',
                  lambda frame: frame.with_columns(pl.col('n_records').add(1)),
                  'pair record counts do not sum to the record count'),
    'link_validator': ('ita_establishment_links.parquet',
                       lambda frame: frame.with_columns(pl.col('status').replace(
                           'no_candidate', 'unknown_status')),
                       'link statuses are not link statuses'),
    'co_ownership_validator': ('co_ownership_support.parquet',
                               lambda frame: frame.with_columns(pl.col('j_employers').add(1)),
                               'co-ownership support counts disagree with the targets'),
}


@pytest.mark.parametrize('case', SERIALIZED_CASES)
def test_build_checks_serialized_tables(seeded, monkeypatch, case):
    name, change, message = SERIALIZED_CASES[case]
    real = pl.LazyFrame.sink_parquet
    rewriting = []

    def corrupt(self, path, *args, **kwargs):
        result = real(self, path, *args, **kwargs)
        # DataFrame.write_parquet sinks through this method too, so rewrite only once.
        if Path(path).name == name and not rewriting:
            rewriting.append(path)
            change(pl.read_parquet(path)).write_parquet(path)
        return result

    monkeypatch.setattr(pl.LazyFrame, 'sink_parquet', corrupt)
    run_id = 'serialized_' + case
    with pytest.raises(ValueError, match=message):
        build_run(seeded.data_dir, seeded.inputs, run_id)
    assert no_publication(seeded.data_dir, run_id)


def change_summary(data_dir, registry):
    summary = paths.derived_dir(data_dir, 'osha') / ita_summary.TABLE_NAME
    summary.write_bytes(summary.read_bytes() + b'changed')


def change_index_citation(data_dir, registry):
    reference = registry['naics_index_2022']
    relative = 'references/' + reference.relative
    file = paths.manifest_path(data_dir)
    lines = []
    for line in file.read_text().splitlines():
        entry = json.loads(line)
        if entry['path'] == relative:
            entry['retrieved_at'] = '2000-01-01T00:00:00+00:00'
            line = json.dumps(entry)
        lines.append(line)
    file.write_text('\n'.join(lines) + '\n')


def change_registry_pin(data_dir, registry):
    reference = registry['naics_index_2022']
    registry['naics_index_2022'] = replace(reference, size=reference.size + 1)


RECHECK_CASES = {
    'codes_inputs': (change_summary, 'selected codes inputs changed'),
    'raw_citation': (change_index_citation, 'cited raw provenance changed'),
    'index_pin': (change_registry_pin, 'size differs from the registered original'),
}


@pytest.mark.parametrize('case', RECHECK_CASES)
def test_build_rechecks_inputs_before_publication(fresh, monkeypatch, case):
    change, message = RECHECK_CASES[case]
    registry = dict(fresh.inputs.index_registry)
    real = target_io.write_json

    def changing(file, value):
        real(file, value)
        if file.name == 'report.json':
            change(fresh.data_dir, registry)

    monkeypatch.setattr(target_io, 'write_json', changing)
    with pytest.raises(ValueError, match=message):
        build_run(fresh.data_dir, fresh.inputs, 'rechecked', index_registry=registry)
    assert no_publication(fresh.data_dir, 'rechecked')


def test_conflicting_raw_citations_fail_build(seeded, monkeypatch):
    real = ita_index_references.citations

    def conflicting(data_dir, *, registry):
        title = 'references/naics/' + ita_references.TITLE_FILES[2022].rsplit('/', 1)[1]
        entry = asdict(manifest.entry_for(paths.manifest_path(data_dir),
                                          paths.manifest_path(data_dir).parent / title))
        return [*real(data_dir, registry=registry), {**entry, 'client': 'other'}]

    monkeypatch.setattr(ita_index_references, 'citations', conflicting)
    with pytest.raises(ValueError, match='conflicting citations'):
        build_run(seeded.data_dir, seeded.inputs, 'conflicting')
    assert no_publication(seeded.data_dir, 'conflicting')


def test_symlinked_staging_is_never_removed(seeded, monkeypatch, tmp_path):
    decoy = tmp_path / 'decoy'
    staging = run_root(seeded.data_dir) / 'swapped.part'

    def swap(*args, **kwargs):
        staging.rename(decoy)
        (decoy / 'kept.txt').write_text('kept')
        staging.symlink_to(decoy, target_is_directory=True)
        raise ValueError('stop after the swap')

    monkeypatch.setattr(ita_establishment_inputs, 'select_codes', swap)
    with pytest.raises(ValueError, match='symlink'):
        build_run(seeded.data_dir, seeded.inputs, 'swapped')
    assert (decoy / 'kept.txt').read_text() == 'kept'
    staging.unlink()


def test_symlinked_scratch_is_never_removed(seeded, monkeypatch, tmp_path):
    decoy = tmp_path / 'decoy'
    real = target_contract.write_targets

    def swap(frame, destination):
        scratch = destination.parent / '.scratch'
        scratch.rename(decoy)
        scratch.symlink_to(decoy, target_is_directory=True)
        return real(frame, destination)

    monkeypatch.setattr(target_contract, 'write_targets', swap)
    with pytest.raises(ValueError, match='symlink'):
        build_run(seeded.data_dir, seeded.inputs, 'scratch_swapped')
    assert (decoy / 'records.parquet').is_file()
    assert no_publication(seeded.data_dir, 'scratch_swapped')


def test_build_keeps_scratch_inside_its_staging(seeded, monkeypatch):
    staging = run_root(seeded.data_dir) / 'scratched.part'
    seen = []

    def observe(records):
        seen.append(sorted(path.relative_to(staging).as_posix()
                           for path in staging.rglob('*')))
        raise ValueError('observed')

    monkeypatch.setattr(ita_co_ownership, 'estimate', observe)
    with pytest.raises(ValueError, match='observed'):
        build_run(seeded.data_dir, seeded.inputs, 'scratched')
    assert seen == [['.scratch', '.scratch/records.parquet']]
    assert no_publication(seeded.data_dir, 'scratched')


def test_compare_runs_refuses_unpublished_or_uninventoried(seeded, tmp_path):
    first = run_directory(seeded.data_dir, FIRST)
    partial = copy_bundle(seeded, tmp_path, name='copy.part')
    with pytest.raises(ValueError, match='published'):
        compare_runs(first, partial)
    changed = copy_bundle(seeded, tmp_path, name='changed')
    change_unpinned(changed)
    with pytest.raises(ValueError, match='inventory hash or size differs'):
        compare_runs(changed, first)
    with pytest.raises(ValueError, match='compared bundles must be published'):
        compare_runs(first, tmp_path / 'absent')
    uninventoried = copy_bundle(seeded, tmp_path, name='uninventoried')
    (uninventoried / 'outputs.json').unlink()
    with pytest.raises(ValueError, match='outputs.json: bundle JSON file is missing'):
        compare_runs(first, uninventoried)


def test_compare_runs_reports_a_report_difference(seeded, tmp_path):
    first = run_directory(seeded.data_dir, FIRST)
    edited = copy_bundle(seeded, tmp_path, name='edited')
    edit_json(edited, 'report.json', set_path('size_gate', 'passed'))
    result = compare_runs(first, edited)
    assert result['report_equal'] is False
    assert result['equal'] is False
    assert all(table['values_equal'] and table['schema_equal']
               for table in result['tables'].values())


def test_contract_constants():
    assert TABLES == (
        'ita_establishment_links', 'ita_text_pairs', 'ita_text_pair_codes',
        'ita_text_pair_members', 'naics_2022_paths', 'ita_co_ownership',
        'co_ownership_marginals', 'co_ownership_support',
    )
    assert FILES == (*(name + '.parquet' for name in TABLES), 'inputs.json', 'report.json')
    assert CONTRACTS == {
        'links': 'ita-establishment-links-v1',
        'pairs': 'ita-text-pairs-v1',
        'co_ownership': 'ita-co-ownership-v1',
        'index': 'naics-index-v1',
        'targets': 'targets-v1',
    }
    assert CONTRACTS == {
        'links': ita_establishment_links.LINKS_VERSION,
        'pairs': ita_text_pairs.PAIRS_VERSION,
        'co_ownership': ita_co_ownership.CO_OWNERSHIP_VERSION,
        'index': ita_index_references.INDEX_VERSION,
        'targets': target_contract.SCHEMA_VERSION,
    }


def test_freeze_software_records_files_python_and_dependencies():
    frozen = freeze_software()
    assert set(frozen) == {
        'files', 'python', 'python_full', 'implementation', 'dependencies', 'uv_lock_sha256'}
    assert list(frozen['files']) == list(SOFTWARE_FILES)
    for name, record in frozen['files'].items():
        file = paths.PROJECT_ROOT / name
        assert record == {'sha256': manifest.sha256_file(file), 'size': file.stat().st_size}
    assert frozen['uv_lock_sha256'] == manifest.sha256_file(paths.PROJECT_ROOT / 'uv.lock')
    assert frozen['python'] == platform.python_version()
    assert frozen['python_full'] == sys.version
    assert frozen['implementation'] == platform.python_implementation()
    assert frozen['dependencies']['polars'] == pl.__version__


def test_fixture_bundle_covers_each_case(seeded):
    '''The golden releases yield every case that the fixture table names.'''
    directory = run_directory(seeded.data_dir, FIRST)
    pairs = pl.read_parquet(directory / 'ita_text_pairs.parquet')
    codes = pl.read_parquet(directory / 'ita_text_pair_codes.parquet')

    def keys(condition):
        return sorted(pairs.filter(condition)['description_key'].to_list())

    assert 'soybean farming' in keys(pl.col('flag_copied_title_any'))
    assert keys(pl.col('flag_copied_index_any')) == [
        'soybean farming', 'wholesale -- see type of product']
    assert keys(pl.col('flag_placeholder')) == ['n/a']
    assert pairs.filter(pl.col('pair_kind').eq('unknown_employer')).height == 1
    assert pairs.filter(pl.col('n_records_ein_padded').gt(0))['employer_key'].to_list() == [
        'ein:023456789', 'ein:023456789']
    mixed = pairs.filter(pl.col('employer_key').eq('ein:012345678'))
    assert mixed['flag_headline'].to_list() == [True]
    mixed_codes = codes.join(mixed.select('pair_id'), on='pair_id')
    assert sorted(mixed_codes.select('naics_year', 'flag_headline_basis').rows()) == [
        (2012, False), (2022, True)]
    conflict = pairs.filter(pl.col('flag_headline_codes_conflict'))
    assert conflict['employer_key'].to_list() == ['ein:345678912']

    targets = pl.read_parquet(directory / 'ita_co_ownership.parquet')
    cell = targets.filter(pl.col('unit_a').eq('naics:2022:national_industry:238220'),
                          pl.col('unit_b').eq('naics:2022:national_industry:722511'))
    assert cell.select('n_unweighted', 'flags').rows() == [
        (1, [ita_co_ownership.PADDED_LABEL, ita_co_ownership.SIZE_LABEL])]

    links = pl.read_parquet(directory / 'ita_establishment_links.parquet')

    def linked(status):
        return links.filter(pl.col('status').eq(status)).select(
            'base_year', 'later_year', 'base_establishment_id').rows()

    assert linked('confirmed_same_id') == [(2023, 2024, 501)]
    assert (2019, 2020, 2019) in linked('confirmed_changed_id')
    assert linked('conflict') == [(2024, 2025, 701), (2024, 2025, 702)]


def change_first(column, change):
    return lambda frame: frame.with_columns(
        pl.when(pl.int_range(pl.len()).eq(0)).then(change(pl.col(column)))
        .otherwise(pl.col(column)).cast(frame.schema[column]).alias(column)
    )


TABLE_TAMPERS = {
    'ita_establishment_links': change_first('flag_id_reappears_elsewhere', pl.Expr.not_),
    'ita_text_pairs': change_first('representative_string', lambda c: pl.lit('tampered')),
    'ita_text_pair_codes': change_first('n_records', lambda c: c.add(1)),
    'ita_text_pair_members': change_first('pair_id', lambda c: pl.lit('tampered')),
    'naics_2022_paths': change_first('node_id', lambda c: pl.lit('tampered')),
    'ita_co_ownership': change_first('value', lambda c: c.add(1.0)),
    'co_ownership_marginals': change_first('n_records', lambda c: c.add(1)),
    'co_ownership_support': change_first('j_2023', lambda c: c.add(1)),
}


@pytest.mark.parametrize('name', TABLES)
def test_verify_detects_each_table_tamper(seeded, tmp_path, name):
    directory = copy_bundle(seeded, tmp_path)
    pin = edit_table(directory, name, TABLE_TAMPERS[name])
    with pytest.raises(ValueError, match=name + ': published table differs'):
        verify_bundle(directory, seeded.data_dir, expected_outputs_sha256=pin)


def broken_pairs(real):
    def build_pairs(records, nodes, code_paths):
        result = real(records, nodes, code_paths)
        return replace(result, pairs=result.pairs.with_columns(pl.col('n_records').add(1)))
    return build_pairs


def broken_links(real):
    def build_links(records):
        result = real(records)
        return replace(result, links=result.links.with_columns(
            pl.col('status').replace('no_candidate', 'unknown_status')))
    return build_links


def broken_co_ownership(real):
    def estimate(records):
        result = real(records)
        return replace(result, support=result.support.with_columns(pl.col('j_employers').add(1)))
    return estimate


RECOMPUTED_CASES = {
    'pairs': (ita_text_pairs, 'build_pairs', broken_pairs,
              'pair record counts do not sum to the record count'),
    'links': (ita_establishment_links, 'build_links', broken_links,
              'link statuses are not link statuses'),
    'co_ownership': (ita_co_ownership, 'estimate', broken_co_ownership,
                     'co-ownership support counts disagree with the targets'),
}


@pytest.mark.parametrize('case', RECOMPUTED_CASES)
def test_verify_validates_the_recomputation(seeded, monkeypatch, case):
    module, name, breaker, message = RECOMPUTED_CASES[case]
    monkeypatch.setattr(module, name, breaker(getattr(module, name)))
    with pytest.raises(ValueError, match=message):
        verify_bundle(run_directory(seeded.data_dir, FIRST), seeded.data_dir,
                      expected_outputs_sha256=seeded.first['outputs_sha256'])


def test_unrecorded_reference_original_is_a_validation_failure(seeded):
    registry = dict(seeded.inputs.index_registry)
    registry['naics_index_2012'] = replace(registry['naics_index_2012'],
                                           relative='naics/unrecorded.xlsx')
    with pytest.raises(ValueError, match='a reference original is not recorded'):
        build_run(seeded.data_dir, seeded.inputs, 'unrecorded', index_registry=registry)
    assert no_publication(seeded.data_dir, 'unrecorded')


def remove_index_entry(data_dir, registry):
    relative = 'references/' + registry['naics_index_2022'].relative
    file = paths.manifest_path(data_dir)
    lines = [line for line in file.read_text().splitlines()
             if json.loads(line)['path'] != relative]
    file.write_text('\n'.join(lines) + '\n')


@pytest.mark.parametrize('moment', ['before_inputs', 'before_publication'])
def test_unrecorded_citation_mid_build_is_a_validation_failure(fresh, monkeypatch, moment):
    registry = fresh.inputs.index_registry
    if moment == 'before_inputs':
        real_targets = target_contract.write_targets

        def write_targets(frame, destination):
            remove_index_entry(fresh.data_dir, registry)
            return real_targets(frame, destination)

        monkeypatch.setattr(target_contract, 'write_targets', write_targets)
    else:
        real_json = target_io.write_json

        def write_json(file, value):
            real_json(file, value)
            if file.name == 'report.json':
                remove_index_entry(fresh.data_dir, registry)

        monkeypatch.setattr(target_io, 'write_json', write_json)
    with pytest.raises(ValueError, match='a cited raw file is not recorded'):
        build_run(fresh.data_dir, fresh.inputs, 'unrecorded_' + moment)
    assert no_publication(fresh.data_dir, 'unrecorded_' + moment)


def test_build_verify_and_compare_use_no_network_or_credentials(seeded, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('offline command attempted external access')

    forbid_external_access(monkeypatch)
    monkeypatch.setattr(ita_index_references, 'make_client', forbidden)
    monkeypatch.setattr(httpx.Client, '__init__', forbidden)
    monkeypatch.setattr(httpx.AsyncClient, '__init__', forbidden)
    result = build_run(seeded.data_dir, seeded.inputs, 'offline')
    directory = Path(result['directory'])
    verified = verify_bundle(directory, seeded.data_dir,
                             expected_outputs_sha256=result['outputs_sha256'])
    assert verified['run_id'] == 'offline'
    assert compare_runs(run_directory(seeded.data_dir, FIRST), directory)['equal'] is True
