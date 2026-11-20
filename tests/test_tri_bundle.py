'''TRI parent-link bundles: build, verify and compare, on a small synthetic three-year window.'''

import json
import platform
import re
import shutil
import sys
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import dotenv
import httpx
import polars as pl
import pytest
from tri_fixtures import (
    module_file,
    seed_codes_bundle,
    seed_tri_files,
    subprocess_modules,
    tri_row,
    write_tri_csv,
)

from embedding_data import (
    code_build,
    ita_summary,
    manifest,
    paths,
    target_contract,
    target_io,
    tri_bundle,
    tri_codes,
    tri_facility_years,
    tri_layout,
    tri_parent_industries,
    tri_parent_link_targets,
    tri_raw,
    tri_reader,
)
from embedding_data.tri_bundle import (
    CONTRACTS,
    FILES,
    LIMITS,
    RULES,
    SOFTWARE_FILES,
    TABLES,
    build,
    compare_runs,
    freeze_software,
    ordered_equal,
    run_directory,
    verify_bundle,
)

FIRST = 'first'
DAY = date(2025, 11, 5)
OTHER_DAY = date(2025, 12, 1)
LAYOUTS = tri_layout.load_layouts()
# Made-up D&B numbers, nine digits each, that no count or code of the fixture contains.
DNB = {'pine': '918273645', 'pine_b': '936271845', 'quartz': '945362718',
       'rock': '954637281', 'loose': '963728154'}
NUMBERS = tuple(DNB.values())
INPUT_FIELDS = {'run_id', 'contracts', 'codes', 'raw', 'processed_as_of', 'window', 'layouts',
                'rules', 'software', 'execution'}
OWN_REPORT_KEYS = {'contracts', 'processed_as_of', 'by_year', 'parents', 'tables', 'limits',
                   'universe', 'size_gate'}
RENAMED = '17. RENAMED PARENT CELL'
SPEC_LIMITS = (
    'TRI is a program-selected population, mostly industrial. No product here represents all '
    'establishments or firms.',
    'A facility can contain several establishments. One primary code per facility hides the '
    'others. Secondary codes are diagnostics only.',
    'The parent is the top of the U.S. tree only. The middle of the tree is lost. One global '
    'firm can appear as several U.S. parents, because the foreign parent is not used for '
    'grouping.',
    'If E8 confirms that the standardized name shows the current owner, pooled years reflect '
    'ownership at the snapshot date, not as of each December 31. The D&B sensitivity count '
    'shows how much the grouping matters.',
    "EPA's standardization can split one parent under two names or merge two. This project "
    'cannot measure either. A self-owned facility that actually has a parent can only lower '
    '`J`.',
    'Codes are self-reported and unvalidated.',
    '`n(a)` pools presence over three years. `J(a,b)` requires the same year.',
    'State and municipal parents stay in, because no field marks them. Federal facilities are '
    'out.',
    'EPA revises earlier years. A later snapshot is a new run with a new pin.',
    'TRI parent links and ITA co-ownership measure close relations. Neither should judge an '
    'embedding that the other trained.',
    'Counts come from all filed forms, not a sample. Standard errors are `none`.',
)


def window_rows() -> dict[int, list[dict[str, str]]]:
    '''Three years of forms: two multi-industry parents, a federal facility and exclusions.

    Pine is in 325110 and 325120 in 2022 and 2024 and in 325110 and 562211 in 2023, but its
    second facility reports another D&B number, so the D&B sensitivity splits it. Rock is in
    324110 and 325110 in 2023 and 2024. Quartz's 2022 facility in 325110 is federal, so the
    federal sensitivity adds a second owner to that cell. Quartz is in 324110 and 325199 in
    2024, where one of T012's two forms gives no parent (a mixed blank). T003 owns itself,
    T008 has a code outside NAICS 2022, T010 names two parents, T011 has no primary code and
    T013 has two.
    '''
    pine = dict(standardized_parent='Pine Holdings', parent_name='Pine Holdings LLC',
                parent_dnb=DNB['pine'])
    pine_b = dict(pine, parent_dnb=DNB['pine_b'])
    rock = dict(standardized_parent='Rock Inc', parent_name='Rock Incorporated',
                parent_dnb=DNB['rock'])
    quartz = dict(standardized_parent='Quartz Corp', parent_name='Quartz Corp',
                  parent_dnb=DNB['quartz'])
    alone = dict(standardized_parent='NA', parent_name='NA', parent_dnb='NA')
    return {
        2022: [
            tri_row(2022, 'T001', primary_naics='325110', state='TX', **pine),
            tri_row(2022, 'T002', primary_naics='325120', state='TX', **pine_b),
            tri_row(2022, 'T003', primary_naics='331110', state='OH', **alone),
            tri_row(2022, 'T004', primary_naics='325110', state='TX', federal=True, **quartz),
            tri_row(2022, 'T005', primary_naics='324110', state='PR', naics_2='325110',
                    **quartz),
            tri_row(2022, 'T013', primary_naics='325110', state='TX', **rock),
            tri_row(2022, 'T013', primary_naics='325120', state='TX', **rock),
        ],
        2023: [
            tri_row(2023, 'T001', primary_naics='325110', state='TX', **pine),
            tri_row(2023, 'T001', primary_naics='325110', state='TX', form='A', **pine),
            tri_row(2023, 'T002', primary_naics='562211', state='TX', **pine_b),
            tri_row(2023, 'T006', primary_naics='324110', state='LA', **rock),
            tri_row(2023, 'T007', primary_naics='325110', state='LA',
                    standardized_foreign_parent='Global SA', **rock),
            tri_row(2023, 'T008', primary_naics='336111', state='MI', **pine),
            tri_row(2023, 'T009', primary_naics='325211', state='NJ', standardized_parent='',
                    parent_name='Loose Owner', parent_dnb=DNB['loose']),
        ],
        2024: [
            tri_row(2024, 'T001', primary_naics='325110', state='TX', **pine),
            tri_row(2024, 'T002', primary_naics='325120', state='TX', **pine_b),
            tri_row(2024, 'T003', primary_naics='331110', state='OH', **alone),
            tri_row(2024, 'T005', primary_naics='324110', state='PR', **quartz),
            tri_row(2024, 'T006', primary_naics='324110', state='LA', **rock),
            tri_row(2024, 'T007', primary_naics='325110', state='LA', **rock),
            tri_row(2024, 'T010', primary_naics='325211', state='NJ', **pine),
            tri_row(2024, 'T010', primary_naics='325211', state='NJ', **rock),
            tri_row(2024, 'T011', primary_naics='', state='TX', **rock),
            tri_row(2024, 'T012', primary_naics='325199', state='TX', **quartz),
            tri_row(2024, 'T012', primary_naics='325199', state='TX', form='A', **alone),
        ],
    }


def seed_window(data_dir: Path, originals: Path, processed_as_of: date,
                header_2023: str | None = None) -> None:
    '''Import the window: 2022 and 2024 as plain files, 2023 with a byte order mark.

    `header_2023` replaces the 2023 standardized-parent header cell, to record a changed
    header.
    '''
    rows = window_rows()
    seed_tri_files(data_dir, originals, {2022: rows[2022], 2024: rows[2024]}, processed_as_of)
    odd = originals / 'odd' / tri_raw.file_name(2023)
    odd.parent.mkdir(parents=True, exist_ok=True)
    write_tri_csv(odd, 2023, rows[2023], bom=True)
    if header_2023 is not None:
        odd.write_bytes(odd.read_bytes().replace(
            b'17. STANDARD PARENT CO NAME', header_2023.encode(), 1))
    tri_raw.import_file(data_dir, 2023, odd, processed_as_of=processed_as_of)


def build_run(state, run_id, *, data_dir=None, **overrides):
    options = dict(codes_run=state.codes_run, codes_outputs_sha256=state.codes_pin,
                   processed_as_of=DAY)
    options.update(overrides)
    return build(state.data_dir if data_dir is None else data_dir, run_id, **options)


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    '''One seeded data root with the published run `first`, shared by the module.'''
    root = tmp_path_factory.mktemp('tri_bundle')
    data_dir = root / 'data'
    codes_run, codes_pin = seed_codes_bundle(data_dir, root / 'codes-originals')
    seed_window(data_dir, root / 'originals', DAY)
    state = SimpleNamespace(data_dir=data_dir, codes_run=codes_run, codes_pin=codes_pin)
    state.first = build_run(state, FIRST)
    state.directory = Path(state.first['directory'])
    return state


@pytest.fixture(scope='module')
def replay(built):
    '''A second published run of the same inputs, in the shared data root.'''
    return build_run(built, 'replay')


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


def copy_root(built, tmp_path):
    '''A copy of the whole shared data root that a test may change.'''
    destination = tmp_path / 'data'
    shutil.copytree(built.data_dir, destination, symlinks=True)
    return destination


def copy_bundle(built, destination, name=FIRST):
    target = destination / name
    shutil.copytree(built.directory, target)
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


def edit_table(directory, name, change):
    file = directory / (name + '.parquet')
    change(pl.read_parquet(file)).write_parquet(file)
    return repin(directory)


def change_first(column, change):
    '''Replace the value of one column in the first row only.'''
    return lambda frame: frame.with_columns(
        pl.when(pl.int_range(pl.len()).eq(0)).then(change(pl.col(column)))
        .otherwise(pl.col(column)).cast(frame.schema[column]).alias(column))


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


def no_publication(data_dir, run_id):
    return (not run_directory(data_dir, run_id).exists()
            and not (run_root(data_dir) / (run_id + '.part')).exists())


def normalized(value):
    return json.loads(json.dumps(value))


def recomputed(built, scratch, layouts=LAYOUTS):
    '''The stage functions run directly on the recorded window, outside the bundle code.'''
    files = tri_raw.select_files(built.data_dir, DAY)
    nodes = tri_codes.select_nodes(built.data_dir, built.codes_run,
                                   codes_outputs_sha256=built.codes_pin)
    lazy_rows, transcoded = tri_reader.read_window(files, layouts, scratch)
    rows = lazy_rows.collect().lazy()
    frame = tri_facility_years.reduce(rows, layouts, nodes.node_ids)
    links = tri_parent_link_targets.estimate(frame, processed_as_of=DAY)
    industries = tri_parent_industries.build_parent_industries(frame)
    return SimpleNamespace(files=files, nodes=nodes, rows=rows, transcoded=transcoded,
                           frame=frame, links=links, industries=industries,
                           year_report=tri_facility_years.year_report(rows, frame, layouts))


def other_header_layouts():
    '''Valid layouts whose 2023 header names one cell differently from the recorded files.'''
    document = tri_layout.layouts_json(LAYOUTS)
    year = document['years']['2023']
    year['header'] = [RENAMED if cell == '17. STANDARD PARENT CO NAME' else cell
                      for cell in year['header']]
    year['columns']['standardized_parent'] = RENAMED
    return tri_layout.parse_layouts(document)


def wider_dnb_layouts():
    '''Valid layouts that also read `NONE` as no D&B number, so they fit the files too.'''
    document = tri_layout.layouts_json(LAYOUTS)
    for year in document['years'].values():
        year['values']['no_dnb'] = ['NA', 'NONE']
    return tri_layout.parse_layouts(document)


# Plan tests.

def test_build_publishes_the_exact_file_set_and_detached_pin(built):
    directory = built.directory
    assert directory == run_directory(built.data_dir, FIRST)
    names = {path.name for path in directory.iterdir()}
    assert names == {*FILES, 'outputs.json'}
    assert len(names) == 8
    outputs = read(directory, 'outputs.json')
    assert set(outputs) == set(FILES)
    assert 'outputs.json' not in outputs
    assert outputs == target_io.inventory(directory, list(FILES))
    assert built.first == {
        'run_id': FIRST,
        'directory': str(directory),
        'outputs_sha256': manifest.sha256_file(directory / 'outputs.json'),
    }


def test_verify_passes_then_refuses_a_changed_byte_report_or_pin(built, tmp_path):
    pin = built.first['outputs_sha256']
    verified = verify_bundle(built.directory, built.data_dir, expected_outputs_sha256=pin)
    report = read(built.directory, 'report.json')
    assert verified == {
        'run_id': FIRST,
        'outputs_sha256': pin,
        'processed_as_of': DAY.isoformat(),
        'rows': {name: report['tables'][name]['rows'] for name in TABLES},
    }
    byte = copy_bundle(built, tmp_path / 'byte')
    file = byte / 'tri_facility_years.parquet'
    data = bytearray(file.read_bytes())
    data[len(data) // 2] ^= 1
    file.write_bytes(bytes(data))
    with pytest.raises(ValueError, match='tri_facility_years.parquet: inventory hash or size'):
        verify_bundle(byte, built.data_dir, expected_outputs_sha256=pin)
    changed = copy_bundle(built, tmp_path / 'report')
    changed_pin = edit_json(changed, 'report.json', set_path('size_gate', 'passed'))
    with pytest.raises(ValueError, match='published report differs from the recomputation'):
        verify_bundle(changed, built.data_dir, expected_outputs_sha256=changed_pin)
    with pytest.raises(ValueError, match='detached inventory checksum differs'):
        verify_bundle(built.directory, built.data_dir, expected_outputs_sha256='0' * 64)


def flip_raw_byte(built, tmp_path):
    data_dir = copy_root(built, tmp_path)
    file = tri_raw.raw_path(data_dir, 2022, DAY)
    data = bytearray(file.read_bytes())
    data[-2] ^= 1
    file.write_bytes(bytes(data))
    return data_dir, 'raw_byte', {}


def changed_header(built, tmp_path):
    data_dir = copy_root(built, tmp_path)
    seed_window(data_dir, tmp_path / 'originals', OTHER_DAY, header_2023=RENAMED)
    return data_dir, 'header', {'processed_as_of': OTHER_DAY}


def occupied_final(built, tmp_path):
    return built.data_dir, FIRST, {}


def wrong_codes_pin(built, tmp_path):
    return built.data_dir, 'codes_pin', {'codes_outputs_sha256': '0' * 64}


def other_layout(built, tmp_path):
    return built.data_dir, 'other_layout', {'layouts': other_header_layouts()}


REFUSALS = {
    'raw_byte': (flip_raw_byte, 'raw file changed'),
    'header': (changed_header, 'changed header'),
    'occupied_final': (occupied_final, 'run or staging name already exists'),
    'codes_pin': (wrong_codes_pin, 'detached inventory checksum differs'),
    'other_layout': (other_layout, 'changed header'),
}


@pytest.mark.parametrize('change', ['raw_byte', 'header', 'occupied_final',
                                    'codes_pin', 'other_layout'])
def test_build_refuses(change, built, tmp_path):
    prepare, message = REFUSALS[change]
    data_dir, run_id, overrides = prepare(built, tmp_path)
    root = run_root(data_dir)
    before = tree(root)
    with pytest.raises(ValueError, match=message) as error:
        build_run(built, run_id, data_dir=data_dir, **overrides)
    assert not any(number in str(error.value) for number in NUMBERS)
    assert not (root / (run_id + '.part')).exists()
    assert tree(root) == before
    if change != 'occupied_final':
        assert not run_directory(data_dir, run_id).exists()


def test_leftover_staging_is_refused_and_untouched(built, tmp_path):
    leftover = run_root(built.data_dir) / 'killed.part'
    leftover.mkdir()
    (leftover / 'tri_parent_links.parquet').write_bytes(b'bytes of a killed build')
    with pytest.raises(ValueError, match='run or staging name already exists'):
        build_run(built, 'killed')
    assert tree(leftover) == {'tri_parent_links.parquet': b'bytes of a killed build'}
    assert not run_directory(built.data_dir, 'killed').exists()
    result = build_run(built, 'fresh_after_kill')
    assert {path.name for path in Path(result['directory']).iterdir()} == {*FILES, 'outputs.json'}
    assert tree(leftover) == {'tri_parent_links.parquet': b'bytes of a killed build'}


def test_software_change_before_publication_fails_without_a_final(monkeypatch, built):
    real = tri_bundle.freeze_software
    calls = []

    def changing():
        calls.append(True)
        frozen = real()
        return frozen if len(calls) == 1 else {**frozen, 'python': 'changed'}

    monkeypatch.setattr(tri_bundle, 'freeze_software', changing)
    with pytest.raises(ValueError, match='executing software changed before publication'):
        build_run(built, 'software')
    assert len(calls) == 2
    assert no_publication(built.data_dir, 'software')


def fail_estimate(monkeypatch):
    def failing(frame, *, processed_as_of):
        raise ValueError('estimate failed')
    monkeypatch.setattr(tri_parent_link_targets, 'estimate', failing)
    return 'estimate failed'


def fail_report(monkeypatch):
    real = target_io.write_json

    def failing(file, value):
        if file.name == 'report.json':
            raise ValueError('report failed')
        real(file, value)
    monkeypatch.setattr(target_io, 'write_json', failing)
    return 'report failed'


@pytest.mark.parametrize('failure', [fail_estimate, fail_report])
def test_failure_removes_only_its_own_staging(failure, built, monkeypatch):
    root = run_root(built.data_dir)
    neighbor = root / 'neighbor.part'
    neighbor.mkdir()
    (neighbor / 'kept.txt').write_text('kept')
    before = tree(root)
    message = failure(monkeypatch)
    with pytest.raises(ValueError, match=message):
        build_run(built, 'failed')
    assert tree(root) == before
    assert no_publication(built.data_dir, 'failed')
    shutil.rmtree(neighbor)


def test_compare_runs_equal_and_unequal(built, replay, tmp_path):
    second = Path(replay['directory'])
    result = compare_runs(built.directory, second)
    assert result['equal'] is True
    assert result['report_equal'] is True
    assert result['trust_established'] is False
    assert list(result['tables']) == list(TABLES)
    for name in TABLES:
        rows = read(built.directory, 'report.json')['tables'][name]['rows']
        assert result['tables'][name] == {'schema_equal': True, 'values_equal': True,
                                          'first_rows': rows, 'second_rows': rows}
    tampered = tmp_path / 'replay'
    shutil.copytree(second, tampered)
    edit_table(tampered, 'tri_parent_link_support', change_first('j_2023', lambda c: c.add(1)))
    unequal = compare_runs(built.directory, tampered)
    assert unequal['equal'] is False
    assert unequal['report_equal'] is True
    assert unequal['tables']['tri_parent_link_support']['values_equal'] is False
    assert all(unequal['tables'][name]['values_equal'] for name in TABLES
               if name != 'tri_parent_link_support')
    assert unequal['trust_established'] is False


def test_report_has_no_run_identity(built):
    text = (built.directory / 'report.json').read_text()
    report = json.loads(text)
    execution = read(built.directory, 'inputs.json')['execution']
    assert not keys_anywhere(report) & {
        'run_id', 'created_at', 'commit', 'dirty', 'execution', 'sha256', 'outputs_sha256',
        'directory', 'path', 'paths', 'raw', 'software'}
    strings = strings_anywhere(report)
    assert not any(FIRST in text_value for text_value in strings)
    assert execution['commit'] not in text
    assert execution['created_at'] not in text
    assert str(built.data_dir) not in text
    assert not any(part in text for part in ('derived/', 'raw/', 'epa_tri/', '.csv'))
    assert not any(number in text for number in NUMBERS)


def test_software_files_cover_the_bundle_import_closure():
    loaded = subprocess_modules('embedding_data.tri_bundle')
    assert {module_file(m) for m in loaded} <= set(tri_bundle.SOFTWARE_FILES)


# Additional tests beyond the plan.

def test_software_files_equal_the_measured_closure():
    closure = {module_file(module)
               for name in ('embedding_data.tri_bundle', 'embedding_data.tri_parent_links')
               for module in subprocess_modules(name)}
    assert set(SOFTWARE_FILES) == closure | {
        'src/embedding_data/tri_layouts.json', 'pyproject.toml', 'uv.lock'}
    assert list(SOFTWARE_FILES) == sorted(set(SOFTWARE_FILES))
    assert all((paths.PROJECT_ROOT / name).is_file() for name in SOFTWARE_FILES)


def test_importing_the_bundle_loads_no_dotenv_or_ipumspy():
    loaded = subprocess_modules('embedding_data.tri_bundle', prefix=None)
    assert 'embedding_data.tri_bundle' in loaded
    assert 'dotenv' not in loaded
    assert 'ipumspy' not in loaded
    assert not any(name.startswith(('dotenv.', 'ipumspy.')) for name in loaded)


def test_module_file_maps_package_modules_to_their_source_files():
    assert module_file('embedding_data') == 'src/embedding_data/__init__.py'
    assert module_file('embedding_data.tri_bundle') == 'src/embedding_data/tri_bundle.py'
    assert module_file('embedding_data.paths') == 'src/embedding_data/paths.py'
    for module in ('polars', 'embedding_data_other', 'other.embedding_data'):
        with pytest.raises(ValueError, match='not a module of embedding_data'):
            module_file(module)


def test_subprocess_modules_reads_a_fresh_interpreter():
    assert 'embedding_data.tri_bundle' in sys.modules
    loaded = subprocess_modules('embedding_data.tri_layout')
    assert {'embedding_data', 'embedding_data.tri_layout', 'embedding_data.tri_raw'} <= loaded
    assert 'embedding_data.tri_bundle' not in loaded
    assert all(name.startswith('embedding_data') for name in loaded)
    everything = subprocess_modules('embedding_data.tri_layout', prefix=None)
    assert {'json', 'httpx', 'embedding_data.tri_layout'} <= everything
    assert 'polars' not in loaded
    assert loaded == {name for name in everything if name.startswith('embedding_data')}
    assert subprocess_modules('embedding_data.tri_layout', prefix='embedding_data.tri_') == {
        name for name in everything if name.startswith('embedding_data.tri_')}


def test_contract_constants():
    assert TABLES == ('tri_parent_links', 'tri_parent_link_marginals', 'tri_parent_link_support',
                      'tri_parent_industries', 'tri_facility_years')
    assert FILES == (*(name + '.parquet' for name in TABLES), 'inputs.json', 'report.json')
    assert CONTRACTS == {'facility_years': 'tri-facility-years-v1',
                         'parent_links': 'tri-parent-links-v1', 'targets': 'targets-v1',
                         'headers': 'tri-headers-v1'}
    assert CONTRACTS == {'facility_years': tri_facility_years.CONTRACT,
                         'parent_links': tri_parent_link_targets.CONTRACT,
                         'targets': target_contract.SCHEMA_VERSION,
                         'headers': tri_layout.LAYOUT_VERSION}


def test_limits_are_the_spec_bullets_and_rules_are_one_sentence_each():
    assert LIMITS == SPEC_LIMITS
    assert set(RULES) == {'facility_year', 'eligibility', 'owner', 'measure'}
    for text in RULES.values():
        assert isinstance(text, str) and text.endswith('.')
        assert '. ' not in text and '\n' not in text and '  ' not in text
    assert 'reporting year and TRIFD' in RULES['facility_year']
    assert RULES['eligibility'].startswith('An eligible facility-year has exactly one primary')
    assert 'parent:<standardized name>' in RULES['owner']
    assert 'J(a,b) / n(a)' in RULES['measure']


def test_run_directory_is_under_the_parent_links_root(tmp_path):
    assert run_directory(tmp_path, 'run_1') == (
        tmp_path / 'derived' / 'epa_tri' / 'parent-links' / 'run_1')
    assert run_directory(str(tmp_path), 'A-2') == (
        tmp_path / 'derived' / 'epa_tri' / 'parent-links' / 'A-2')
    for unsafe in ('../escape', '.hidden', 'a/b', '', '_lead', 'run.part', 'x y', None, 5):
        with pytest.raises(ValueError, match='unsafe run ID'):
            run_directory(tmp_path, unsafe)


ORDERED = pl.LazyFrame(
    {'n': [1, 2, None], 'labels': [['a'], [], None]},
    schema={'n': pl.Int64, 'labels': pl.List(pl.String)},
)
ORDERED_CASES = {
    'identical': (ORDERED, True, True, 3),
    'null_against_value': (ORDERED.with_columns(pl.col('n').fill_null(3)), True, False, 3),
    'value_against_null': (ORDERED.with_columns(
        n=pl.Series([None, 2, None], dtype=pl.Int64)), True, False, 3),
    'list_value': (ORDERED.with_columns(labels=pl.Series([['a'], ['b'], None])), True, False, 3),
    'row_order': (ORDERED.reverse(), True, False, 3),
    'extra_null_row': (pl.concat([ORDERED, pl.LazyFrame({'n': [None], 'labels': [None]},
                                                        schema=ORDERED.collect_schema())]),
                       True, False, 4),
    'fewer_rows': (ORDERED.head(2), True, False, 2),
    'dtype': (ORDERED.with_columns(pl.col('n').cast(pl.Int32)), False, False, 3),
    'column_order': (ORDERED.select('labels', 'n'), False, False, 3),
    'column_name': (ORDERED.rename({'n': 'm'}), False, False, 3),
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
    assert list(frozen['dependencies']) == sorted(frozen['dependencies'])


def test_bundle_records_its_inputs(built):
    inputs = read(built.directory, 'inputs.json')
    assert set(inputs) == INPUT_FIELDS
    assert inputs['run_id'] == FIRST
    assert inputs['contracts'] == CONTRACTS
    nodes = tri_codes.select_nodes(built.data_dir, built.codes_run,
                                   codes_outputs_sha256=built.codes_pin)
    assert inputs['codes'] == normalized(nodes.provenance())
    assert inputs['codes']['run_id'] == built.codes_run
    assert inputs['codes']['outputs_sha256'] == built.codes_pin
    files = tri_raw.select_files(built.data_dir, DAY)
    assert inputs['raw'] == tri_raw.citations(built.data_dir, files)
    assert [citation['path'] for citation in inputs['raw']] == [
        f'epa_tri/basic/{year}/2025-11-05/{year}_us.csv' for year in (2022, 2023, 2024)]
    assert inputs['processed_as_of'] == '2025-11-05'
    assert inputs['window'] == [2022, 2023, 2024]
    assert inputs['layouts'] == tri_layout.layouts_json(LAYOUTS)
    assert inputs['rules'] == RULES
    assert inputs['software'] == freeze_software()
    execution = inputs['execution']
    assert set(execution) == {'commit', 'dirty', 'created_at'}
    assert re.fullmatch(r'[0-9a-f]{40}', execution['commit'])
    assert isinstance(execution['dirty'], bool)
    assert datetime.fromisoformat(execution['created_at']).utcoffset() is not None


def test_bundle_report_holds_the_stage_reports(built, tmp_path):
    report = read(built.directory, 'report.json')
    expected = recomputed(built, tmp_path / 'scratch')
    assert expected.transcoded == [2023]
    assert set(report) == OWN_REPORT_KEYS | set(expected.links.report)
    assert report['contracts'] == CONTRACTS
    assert report['processed_as_of'] == '2025-11-05'
    assert list(report['by_year']) == ['2022', '2023', '2024']
    assert report['by_year'] == normalized({
        year: {**counts, 'transcoded': year == '2023'}
        for year, counts in expected.year_report.items()})
    assert [report['by_year'][year]['transcoded'] for year in ('2022', '2023', '2024')] == [
        False, True, False]
    for key, value in expected.links.report.items():
        assert report[key] == normalized(value)
    assert report['parents'] == normalized(
        tri_parent_industries.parent_report(expected.industries, expected.frame))
    outputs = read(built.directory, 'outputs.json')
    assert list(report['tables']) == sorted(TABLES)
    for name in TABLES:
        record = outputs[name + '.parquet']
        assert report['tables'][name] == {key: record[key] for key in ('rows', 'columns',
                                                                       'schema')}
    assert report['limits'] == list(SPEC_LIMITS)
    assert report['universe'] == tri_parent_link_targets.UNIVERSE.format(date='2025-11-05')
    assert report['size_gate'] == 'pending'


def test_published_tables_equal_the_stage_functions(built, tmp_path):
    expected = recomputed(built, tmp_path / 'scratch')
    tables = {
        'tri_parent_links': expected.links.targets,
        'tri_parent_link_marginals': expected.links.marginals,
        'tri_parent_link_support': expected.links.support,
        'tri_parent_industries': expected.industries,
        'tri_facility_years': tri_facility_years.public(expected.frame),
    }
    for name in TABLES:
        published = pl.read_parquet(built.directory / (name + '.parquet'))
        assert published.equals(tables[name]), name
        assert published.schema == tables[name].schema
    targets = tables['tri_parent_links']
    target_contract.validate_targets(targets)
    assert targets.height == 8
    flags = set(targets['flags'].explode())
    assert {tri_parent_link_targets.DNB_LABEL, tri_parent_link_targets.FEDERAL_LABEL,
            tri_parent_link_targets.SIZE_LABEL} == flags
    facility_years = tables['tri_facility_years']
    assert facility_years['n_forms'].sum() == sum(len(rows) for rows in window_rows().values())


def test_expected_data_states_are_retained_diagnostics(built):
    '''Excluded facility-years, mixed blanks and self-owned facilities stay in the bundle.'''
    facility_years = pl.read_parquet(built.directory / 'tri_facility_years.parquet')
    reasons = facility_years.filter(pl.col('exclusion_reason').is_not_null()).select(
        'reporting_year', 'trifd', 'exclusion_reason').rows()
    assert sorted(reasons) == [
        (2022, 'T004', 'federal'), (2022, 'T013', 'naics_conflict'),
        (2023, 'T008', 'naics_not_2022'), (2024, 'T010', 'parent_conflict'),
        (2024, 'T011', 'naics_missing')]
    mixed = facility_years.filter(pl.col('flag_parent_mixed_blank'))
    assert mixed.select('reporting_year', 'trifd', 'owner_key').rows() == [
        (2024, 'T012', 'parent:Quartz Corp')]
    assert facility_years.filter(pl.col('trifd') == 'T003')['owner_key'].to_list() == [
        'facility:T003', 'facility:T003']
    targets = pl.read_parquet(built.directory / 'tri_parent_links.parquet')
    quartz = ('naics:2022:national_industry:324110', 'naics:2022:national_industry:325199')
    assert {quartz, quartz[::-1]} <= set(targets.select('unit_a', 'unit_b').rows())


def test_build_refuses_a_reporting_year_mismatch(built, tmp_path):
    data_dir = copy_root(built, tmp_path)
    rows = window_rows()
    rows[2024] = [*rows[2024], tri_row(2024, 'T099', primary_naics='325110',
                                       reporting_year='2023')]
    seed_tri_files(data_dir, tmp_path / 'originals', rows, OTHER_DAY)
    with pytest.raises(ValueError, match='reporting year mismatch'):
        build_run(built, 'year_mismatch', data_dir=data_dir, processed_as_of=OTHER_DAY)
    assert no_publication(data_dir, 'year_mismatch')


def cell_strings(frame: pl.DataFrame) -> set[str]:
    '''Every string cell of the frame, list elements included.'''
    found = set()
    for name, dtype in frame.schema.items():
        column = frame[name]
        if dtype == pl.List(pl.String):
            column = column.explode()
        if column.dtype == pl.String:
            found |= set(column.drop_nulls())
    return found


def test_no_dnb_number_leaves_the_build(built):
    for name in TABLES:
        frame = pl.read_parquet(built.directory / (name + '.parquet'))
        assert not any(column.startswith('_') for column in frame.columns), name
        strings = cell_strings(frame)
        assert not any(number in text for text in strings for number in NUMBERS), name
    facility_years = pl.read_parquet(built.directory / 'tri_facility_years.parquet')
    assert list(facility_years.schema) == list(tri_facility_years.TABLE_SCHEMA)
    for name in ('inputs.json', 'report.json', 'outputs.json'):
        text = (built.directory / name).read_text()
        assert not any(number in text for number in NUMBERS), name
    assert not any(number in json.dumps(built.first) for number in NUMBERS)
    assert not any(path.name == '.scratch' for path in run_root(built.data_dir).rglob('*'))


def test_build_keeps_its_scratch_inside_its_staging_and_removes_it(built, monkeypatch):
    staging = run_root(built.data_dir) / 'scratched.part'
    real = tri_parent_link_targets.estimate
    seen = []

    def observe(frame, *, processed_as_of):
        seen.append(sorted(path.relative_to(staging).as_posix() for path in staging.rglob('*')))
        copy = staging / '.scratch' / '2023.utf8.csv'
        seen.append(any(number in copy.read_text() for number in NUMBERS))
        return real(frame, processed_as_of=processed_as_of)

    monkeypatch.setattr(tri_parent_link_targets, 'estimate', observe)
    result = build_run(built, 'scratched')
    assert seen == [['.scratch', '.scratch/2023.utf8.csv'], True]
    assert {path.name for path in Path(result['directory']).iterdir()} == {*FILES, 'outputs.json'}


def test_the_targets_go_through_the_shared_target_writer(built, monkeypatch):
    real = target_contract.write_targets
    written = []

    def observe(frame, destination):
        written.append(Path(destination).name)
        return real(frame, destination)

    monkeypatch.setattr(target_contract, 'write_targets', observe)
    result = build_run(built, 'writer')
    assert written == ['tri_parent_links.parquet']
    published = pl.read_parquet(Path(result['directory']) / 'tri_parent_links.parquet')
    assert published.equals(pl.read_parquet(built.directory / 'tri_parent_links.parquet'))


def colliding_estimate(monkeypatch):
    real = tri_parent_link_targets.estimate

    def colliding(frame, *, processed_as_of):
        result = real(frame, processed_as_of=processed_as_of)
        return replace(result, report={**result.report, 'tables': {}})

    monkeypatch.setattr(tri_parent_link_targets, 'estimate', colliding)


def colliding_year_report(monkeypatch):
    real = tri_facility_years.year_report

    def colliding(rows, frame, layouts):
        return {year: {**counts, 'transcoded': True}
                for year, counts in real(rows, frame, layouts).items()}

    monkeypatch.setattr(tri_facility_years, 'year_report', colliding)


@pytest.mark.parametrize('collision', [colliding_estimate, colliding_year_report])
def test_report_key_collision_fails_the_build(collision, built, monkeypatch):
    collision(monkeypatch)
    with pytest.raises(ValueError, match='report keys collide'):
        build_run(built, 'collision')
    assert no_publication(built.data_dir, 'collision')


def test_verify_authenticates_the_pin_first(built, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('select_nodes ran before the pin was authenticated')

    monkeypatch.setattr(tri_codes, 'select_nodes', forbidden)
    with pytest.raises(ValueError, match='detached inventory checksum differs'):
        verify_bundle(built.directory, built.data_dir, expected_outputs_sha256='0' * 64)


def add_directory(directory):
    (directory / 'extra').mkdir()
    return manifest.sha256_file(directory / 'outputs.json')


def add_nested_file(directory):
    (directory / 'tri_parent_links.parquet.d').mkdir()
    (directory / 'tri_parent_links.parquet.d' / 'x').write_text('x')
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
    'nested_file': (add_nested_file, 'bundle file set differs'),
    'unpinned_change': (change_unpinned, 'inventory hash or size differs'),
    'inventory_without_schema': (drop_inventory_schema, 'output inventory records differ'),
}


@pytest.mark.parametrize('case', LAYOUT_CASES)
def test_verify_refuses_bundle_layout_before_reading_inputs(built, tmp_path, monkeypatch, case):
    def forbidden(*args, **kwargs):
        raise AssertionError('select_nodes ran before the bundle layout was checked')

    change, message = LAYOUT_CASES[case]
    directory = copy_bundle(built, tmp_path)
    pin = change(directory)
    monkeypatch.setattr(tri_codes, 'select_nodes', forbidden)
    with pytest.raises(ValueError, match=message):
        verify_bundle(directory, built.data_dir, expected_outputs_sha256=pin)


def test_verify_refuses_an_unpublished_name_and_a_malformed_pin(built, tmp_path):
    partial = copy_bundle(built, tmp_path, name=FIRST + '.part')
    pin = built.first['outputs_sha256']
    with pytest.raises(ValueError, match='not published'):
        verify_bundle(partial, built.data_dir, expected_outputs_sha256=pin)
    for malformed in (pin.upper(), pin[:-1], pin + '0', None):
        with pytest.raises(ValueError, match='invalid detached checksum'):
            verify_bundle(built.directory, built.data_dir, expected_outputs_sha256=malformed)
    with pytest.raises(ValueError, match='detached inventory checksum differs'):
        verify_bundle(tmp_path / 'absent', built.data_dir, expected_outputs_sha256=pin)


def duplicate_key(text):
    return text.replace('{\n', '{\n  "size_gate": "pending",\n', 1)


def not_a_number(text):
    return text.replace('"size_gate": "pending"', '"size_gate": NaN', 1)


JSON_CASES = {
    'report_duplicate_key': ('report.json', duplicate_key, 'duplicate JSON key'),
    'report_nan': ('report.json', not_a_number, 'non-finite JSON number'),
    'report_noncanonical': ('report.json', lambda text: text + '\n',
                            'report.json: not canonical JSON'),
    'report_unsorted': ('report.json',
                        lambda text: json.dumps(dict(reversed(json.loads(text).items())),
                                                indent=2, ensure_ascii=False) + '\n',
                        'report.json: not canonical JSON'),
    'inputs_noncanonical': ('inputs.json', lambda text: text + '\n',
                            'inputs.json: not canonical JSON'),
    'outputs_noncanonical': ('outputs.json', lambda text: text + '\n',
                             'outputs.json: not canonical JSON'),
    'report_not_json': ('report.json', lambda text: 'not json\n', 'report.json: not valid JSON'),
    'report_not_object': ('report.json', lambda text: '[]\n', 'report.json: not a JSON object'),
}


@pytest.mark.parametrize('case', JSON_CASES)
def test_verify_reads_json_strictly(built, tmp_path, case):
    name, change, message = JSON_CASES[case]
    directory = copy_bundle(built, tmp_path)
    file = directory / name
    file.write_text(change(file.read_text()))
    if name != 'outputs.json':
        outputs = read(directory, 'outputs.json')
        outputs[name] = target_io.file_record(file)
        target_io.write_json(directory / 'outputs.json', outputs)
    pin = manifest.sha256_file(directory / 'outputs.json')
    with pytest.raises(ValueError, match=message):
        verify_bundle(directory, built.data_dir, expected_outputs_sha256=pin)


def renamed_copy(built, tmp_path):
    return copy_bundle(built, tmp_path, name='renamed'), built.first['outputs_sha256']


def edit_copy(name, change):
    def apply(built, tmp_path):
        directory = copy_bundle(built, tmp_path)
        return directory, edit_json(directory, name, change)
    return apply


def add_field(inputs):
    inputs['extra'] = True


RECORDED_CASES = {
    'renamed': (renamed_copy, 'recorded run ID differs from the directory'),
    'input_contracts': (edit_copy('inputs.json', set_path('contracts', 'headers', 'other')),
                        'contract versions differ'),
    'report_contracts': (edit_copy('report.json', set_path('contracts', 'targets', 'other')),
                         'contract versions differ'),
    'report_without_contracts': (edit_copy('report.json', delete_path('contracts')),
                                 'contract versions differ'),
    'missing_field': (edit_copy('inputs.json', delete_path('rules')),
                      'recorded inputs are malformed'),
    'extra_field': (edit_copy('inputs.json', add_field), 'recorded inputs are malformed'),
    'malformed_date': (edit_copy('inputs.json', set_path('processed_as_of', 'November 5')),
                       'recorded inputs are malformed'),
    'date_not_text': (edit_copy('inputs.json', set_path('processed_as_of', 20251105)),
                      'recorded inputs are malformed'),
    'codes_not_object': (edit_copy('inputs.json', set_path('codes', [])),
                         'recorded inputs are malformed'),
    'codes_run_not_text': (edit_copy('inputs.json', set_path('codes', 'run_id', 5)),
                           'recorded inputs are malformed'),
    'codes_pin_not_text': (edit_copy('inputs.json', set_path('codes', 'outputs_sha256', 5)),
                           'recorded inputs are malformed'),
    'codes_without_pin': (edit_copy('inputs.json', delete_path('codes', 'outputs_sha256')),
                          'recorded inputs are malformed'),
    'codes_pin': (edit_copy('inputs.json', set_path('codes', 'outputs_sha256', '0' * 64)),
                  'detached inventory checksum differs'),
    'other_snapshot': (edit_copy('inputs.json', set_path('processed_as_of', '2025-12-01')),
                       'missing or extra raw file'),
    'layouts': (edit_copy('inputs.json',
                          set_path('layouts', 'years', '2023', 'values', 'no_dnb',
                                   ['NA', 'NONE'])),
                'recorded layouts differ from the supplied layouts'),
    'software': (edit_copy('inputs.json', set_path('software', 'python', 'other')),
                 'executing software differs from the build'),
    'rules': (edit_copy('inputs.json', set_path('rules', 'owner', 'other')),
              'recorded inputs differ from the recomputation'),
    'raw': (edit_copy('inputs.json', lambda inputs: inputs['raw'].pop()),
            'recorded inputs differ from the recomputation'),
    'window': (edit_copy('inputs.json', set_path('window', [2022, 2023])),
               'recorded inputs differ from the recomputation'),
    'codes_outputs': (edit_copy('inputs.json', set_path('codes', 'outputs', {})),
                      'recorded inputs differ from the recomputation'),
    'report': (edit_copy('report.json', set_path('size_gate', 'passed')),
               'published report differs from the recomputation'),
    'report_by_year': (edit_copy('report.json', set_path('by_year', '2023', 'transcoded', False)),
                       'published report differs from the recomputation'),
}


@pytest.mark.parametrize('case', RECORDED_CASES)
def test_verify_refuses_recorded_differences(built, tmp_path, case):
    prepare, message = RECORDED_CASES[case]
    directory, pin = prepare(built, tmp_path)
    with pytest.raises(ValueError, match=message):
        verify_bundle(directory, built.data_dir, expected_outputs_sha256=pin)


TABLE_TAMPERS = {
    'tri_parent_links': change_first('value', lambda c: c.add(1.0)),
    'tri_parent_link_marginals': change_first('n_owners_dnb', lambda c: c.add(1)),
    'tri_parent_link_support': change_first('j_2023', lambda c: c.add(1)),
    'tri_parent_industries': change_first('f_2024', lambda c: c.add(1)),
    'tri_facility_years': change_first('flag_parent_mixed_blank', pl.Expr.not_),
}


@pytest.mark.parametrize('name', TABLES)
def test_verify_detects_each_table_tamper(built, tmp_path, name):
    directory = copy_bundle(built, tmp_path)
    pin = edit_table(directory, name, TABLE_TAMPERS[name])
    with pytest.raises(ValueError, match=name + ': published table differs'):
        verify_bundle(directory, built.data_dir, expected_outputs_sha256=pin)


def test_verify_refuses_layouts_other_than_the_recorded_ones(built):
    wider = wider_dnb_layouts()
    result = build_run(built, 'wider', layouts=wider)
    directory = Path(result['directory'])
    assert read(directory, 'inputs.json')['layouts'] == tri_layout.layouts_json(wider)
    verified = verify_bundle(directory, built.data_dir,
                             expected_outputs_sha256=result['outputs_sha256'], layouts=wider)
    assert verified['run_id'] == 'wider'
    with pytest.raises(ValueError, match='recorded layouts differ from the supplied layouts'):
        verify_bundle(directory, built.data_dir, expected_outputs_sha256=result['outputs_sha256'])
    with pytest.raises(ValueError, match='recorded layouts differ from the supplied layouts'):
        verify_bundle(built.directory, built.data_dir,
                      expected_outputs_sha256=built.first['outputs_sha256'], layouts=wider)


def test_verify_recomputes_outside_the_data_root_and_changes_nothing(built, monkeypatch):
    before = tree(built.data_dir)
    real = tri_reader.read_window
    scratches = []
    during = []

    def observe(files, layouts, scratch):
        scratches.append(Path(scratch))
        result = real(files, layouts, scratch)
        during.append(tree(built.data_dir))
        return result

    monkeypatch.setattr(tri_reader, 'read_window', observe)
    verify_bundle(built.directory, built.data_dir,
                  expected_outputs_sha256=built.first['outputs_sha256'])
    assert len(scratches) == 1
    assert not scratches[0].resolve().is_relative_to(built.data_dir.resolve())
    assert not scratches[0].exists()
    assert during == [before]
    assert tree(built.data_dir) == before


def broken_reduce(real):
    def reduce(rows, layouts, node_ids):
        return change_first('n_forms', lambda c: c.add(1))(real(rows, layouts, node_ids))
    return reduce


def broken_estimate(real):
    def estimate(frame, *, processed_as_of):
        result = real(frame, processed_as_of=processed_as_of)
        return replace(result, support=result.support.with_columns(pl.col('j_owners').add(1)))
    return estimate


def broken_industries(real):
    def build_parent_industries(frame):
        return real(frame).reverse()
    return build_parent_industries


RECOMPUTED_CASES = {
    'facility_years': (tri_facility_years, 'reduce', broken_reduce,
                       'n_forms differ from source rows'),
    'parent_links': (tri_parent_link_targets, 'estimate', broken_estimate,
                     'support count differs from the target count'),
    'parent_industries': (tri_parent_industries, 'build_parent_industries', broken_industries,
                          'key not unique and sorted'),
}


@pytest.mark.parametrize('case', RECOMPUTED_CASES)
def test_verify_validates_the_recomputation(built, monkeypatch, case):
    module, name, breaker, message = RECOMPUTED_CASES[case]
    monkeypatch.setattr(module, name, breaker(getattr(module, name)))
    with pytest.raises(ValueError, match=message):
        verify_bundle(built.directory, built.data_dir,
                      expected_outputs_sha256=built.first['outputs_sha256'])


def test_build_refuses_a_stray_staged_file(built, monkeypatch):
    real = target_io.write_json

    def stray(file, value):
        real(file, value)
        if file.name == 'report.json':
            (file.parent / 'stray.txt').write_text('stray')

    monkeypatch.setattr(target_io, 'write_json', stray)
    with pytest.raises(ValueError, match='staged bundle files differ'):
        build_run(built, 'stray')
    assert no_publication(built.data_dir, 'stray')


def test_build_refuses_a_final_that_appears_before_publication(built, monkeypatch):
    real = tri_bundle.freeze_software
    final = run_directory(built.data_dir, 'appeared')
    calls = []

    def appear():
        calls.append(True)
        if len(calls) == 2:
            final.mkdir()
        return real()

    monkeypatch.setattr(tri_bundle, 'freeze_software', appear)
    with pytest.raises(ValueError, match='final run name already exists'):
        build_run(built, 'appeared')
    assert final.is_dir() and not any(final.iterdir())
    assert not (run_root(built.data_dir) / 'appeared.part').exists()
    final.rmdir()


SERIALIZED_CASES = {
    'facility_years_validator': ('tri_facility_years.parquet',
                                 change_first('n_forms', lambda c: c.add(1)),
                                 'n_forms differ from source rows'),
    'facility_years_row_loss': ('tri_facility_years.parquet',
                                lambda frame: frame.slice(1),
                                'n_forms differ from source rows'),
    'facility_years_duplicate_row': ('tri_facility_years.parquet',
                                     lambda frame: pl.concat([frame, frame.head(1)]),
                                     'key not unique and sorted'),
    'facility_years_order': ('tri_facility_years.parquet',
                             change_first('state_values', lambda c: pl.lit(['ZZ'])),
                             'tri_facility_years: serialized table differs'),
    'targets_validator': ('tri_parent_links.parquet',
                          lambda frame: frame.with_columns(pl.col('value').mul(0.5)),
                          'value differs from the cell count over the owner count'),
    'marginals_order': ('tri_parent_link_marginals.parquet',
                        change_first('n_owners_dnb', lambda c: c.add(1)),
                        'tri_parent_link_marginals: serialized table differs'),
    'support_validator': ('tri_parent_link_support.parquet',
                          lambda frame: frame.with_columns(pl.col('j_owners').add(1)),
                          'support count differs from the target count'),
    'industries_validator': ('tri_parent_industries.parquet',
                             change_first('n_facility_years', lambda c: c.add(1)),
                             'counts differ from the facility-years'),
}


@pytest.mark.parametrize('case', SERIALIZED_CASES)
def test_build_checks_the_serialized_tables(built, monkeypatch, case):
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
        build_run(built, run_id)
    assert rewriting
    assert no_publication(built.data_dir, run_id)


def change_codes(data_dir):
    (report,) = (data_dir / 'derived' / 'codes').glob('*/report.json')
    report.write_text(report.read_text() + ' ')


def change_citation(data_dir):
    file = paths.manifest_path(data_dir)
    relative = tri_raw.raw_path(data_dir, 2024, DAY).relative_to(file.parent).as_posix()
    lines = []
    for line in file.read_text().splitlines():
        entry = json.loads(line)
        if entry['path'] == relative:
            entry['retrieved_at'] = '2000-01-01T00:00:00+00:00'
            line = json.dumps(entry)
        lines.append(line)
    file.write_text('\n'.join(lines) + '\n')


def change_raw(data_dir):
    file = tri_raw.raw_path(data_dir, 2022, DAY)
    data = bytearray(file.read_bytes())
    data[-2] ^= 1
    file.write_bytes(bytes(data))


def add_raw(data_dir):
    (tri_raw.snapshot_dir(data_dir, 2024, DAY) / 'extra.csv').write_text('extra')


RECHECK_CASES = {
    'codes': (change_codes, 'selected codes nodes changed'),
    'raw_citation': (change_citation, 'cited raw provenance changed'),
    'raw_byte': (change_raw, 'raw file changed'),
    'raw_extra': (add_raw, 'missing or extra raw file'),
}


@pytest.mark.parametrize('case', RECHECK_CASES)
def test_build_rechecks_its_inputs_before_publication(built, tmp_path, monkeypatch, case):
    change, message = RECHECK_CASES[case]
    data_dir = copy_root(built, tmp_path)
    real = target_io.write_json

    def changing(file, value):
        real(file, value)
        if file.name == 'report.json':
            change(data_dir)

    monkeypatch.setattr(target_io, 'write_json', changing)
    with pytest.raises(ValueError, match=message):
        build_run(built, 'rechecked', data_dir=data_dir)
    assert no_publication(data_dir, 'rechecked')


def test_symlinked_staging_is_never_removed(built, monkeypatch, tmp_path):
    decoy = tmp_path / 'decoy'
    staging = run_root(built.data_dir) / 'swapped.part'

    def swap(*args, **kwargs):
        staging.rename(decoy)
        (decoy / 'kept.txt').write_text('kept')
        staging.symlink_to(decoy, target_is_directory=True)
        raise ValueError('stop after the swap')

    monkeypatch.setattr(tri_codes, 'select_nodes', swap)
    with pytest.raises(ValueError, match='symlink'):
        build_run(built, 'swapped')
    assert (decoy / 'kept.txt').read_text() == 'kept'
    staging.unlink()


def test_symlinked_scratch_is_never_removed(built, monkeypatch, tmp_path):
    decoy = tmp_path / 'decoy'
    real = target_contract.write_targets

    def swap(frame, destination):
        scratch = destination.parent / '.scratch'
        scratch.rename(decoy)
        scratch.symlink_to(decoy, target_is_directory=True)
        return real(frame, destination)

    monkeypatch.setattr(target_contract, 'write_targets', swap)
    with pytest.raises(ValueError, match='symlink'):
        build_run(built, 'scratch_swapped')
    assert (decoy / '2023.utf8.csv').is_file()
    assert no_publication(built.data_dir, 'scratch_swapped')


def test_compare_runs_refuses_unpublished_or_uninventoried(built, tmp_path):
    partial = copy_bundle(built, tmp_path, name='copy.part')
    with pytest.raises(ValueError, match='compared bundles must be published'):
        compare_runs(built.directory, partial)
    with pytest.raises(ValueError, match='compared bundles must be published'):
        compare_runs(partial, built.directory)
    changed = copy_bundle(built, tmp_path, name='changed')
    change_unpinned(changed)
    with pytest.raises(ValueError, match='inventory hash or size differs'):
        compare_runs(changed, built.directory)
    with pytest.raises(ValueError, match='compared bundles must be published'):
        compare_runs(built.directory, tmp_path / 'absent')
    uninventoried = copy_bundle(built, tmp_path, name='uninventoried')
    (uninventoried / 'outputs.json').unlink()
    with pytest.raises(ValueError, match='outputs.json: bundle JSON file is missing'):
        compare_runs(built.directory, uninventoried)


def test_compare_runs_reports_a_report_difference(built, tmp_path):
    edited = copy_bundle(built, tmp_path, name='edited')
    edit_json(edited, 'report.json', set_path('size_gate', 'passed'))
    result = compare_runs(built.directory, edited)
    assert result['report_equal'] is False
    assert result['equal'] is False
    assert all(table['values_equal'] and table['schema_equal']
               for table in result['tables'].values())


def test_compare_runs_ignores_run_identity(built, replay):
    first = read(built.directory, 'inputs.json')
    second = read(Path(replay['directory']), 'inputs.json')
    assert first['run_id'] != second['run_id']
    assert first['execution']['created_at'] != second['execution']['created_at']
    assert compare_runs(built.directory, Path(replay['directory']))['equal'] is True


def test_build_verify_and_compare_are_offline(built, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('an offline command reached outside')

    monkeypatch.setattr(httpx.Client, '__init__', forbidden)
    monkeypatch.setattr(httpx.AsyncClient, '__init__', forbidden)
    monkeypatch.setattr(tri_raw, 'acquire', forbidden)
    monkeypatch.setattr(tri_raw, 'make_client', forbidden)
    monkeypatch.setattr(dotenv, 'load_dotenv', forbidden)
    monkeypatch.setattr(dotenv, 'dotenv_values', forbidden)
    monkeypatch.setattr(code_build, 'build', forbidden)
    monkeypatch.setattr(ita_summary, 'build_summary_table', forbidden)
    result = build_run(built, 'offline')
    directory = Path(result['directory'])
    verified = verify_bundle(directory, built.data_dir,
                             expected_outputs_sha256=result['outputs_sha256'])
    assert verified['run_id'] == 'offline'
    assert compare_runs(built.directory, directory)['equal'] is True


def fake_git(status, calls):
    '''A stand-in for `subprocess.check_output` that answers the two git calls of a build.

    `status` holds porcelain lines. Like git, the stand-in leaves out the untracked (`??`)
    lines when the call asks for `--untracked-files=no`.
    '''
    def check_output(args, **kwargs):
        calls.append((tuple(args), Path(kwargs['cwd'])))
        if args[:2] == ['git', 'rev-parse']:
            return 'f' * 40 + '\n'
        assert args[:3] == ['git', 'status', '--porcelain']
        untracked = '--untracked-files=no' not in args
        return ''.join(line + '\n' for line in status.splitlines()
                       if untracked or not line.startswith('??'))
    return check_output


EXECUTION_CASES = {
    'modified': (' M src/embedding_data/tri_bundle.py', True),
    'untracked': ('?? notes.txt', True),
    'clean': ('', False),
}


@pytest.mark.parametrize('case', EXECUTION_CASES)
def test_execution_records_the_commit_and_whether_the_checkout_is_dirty(case, monkeypatch):
    status, dirty = EXECUTION_CASES[case]
    calls = []
    monkeypatch.setattr(tri_bundle.subprocess, 'check_output', fake_git(status, calls))
    execution = tri_bundle._execution()
    assert execution['dirty'] is dirty
    assert execution['commit'] == 'f' * 40
    assert datetime.fromisoformat(execution['created_at']).utcoffset() == timedelta(0)
    assert {cwd for _, cwd in calls} == {paths.PROJECT_ROOT}


def test_build_records_the_execution_it_measured(built, monkeypatch):
    calls = []
    monkeypatch.setattr(tri_bundle.subprocess, 'check_output', fake_git('?? notes.txt', calls))
    result = build_run(built, 'dirty_build')
    directory = Path(result['directory'])
    execution = read(directory, 'inputs.json')['execution']
    assert execution['commit'] == 'f' * 40
    assert execution['dirty'] is True
    verified = verify_bundle(directory, built.data_dir,
                             expected_outputs_sha256=result['outputs_sha256'])
    assert verified['run_id'] == 'dirty_build'
    assert read(directory, 'inputs.json')['execution'] == execution


def test_build_and_verify_use_the_stage_5_selector_and_read_no_ita_data(built, monkeypatch):
    '''Spec lines 192 and 196: the TRI codes selector alone, and no ITA source or raw file.'''
    selections = []
    touched = []
    real_select = tri_codes.select_nodes

    def select(data_dir, codes_run, *, codes_outputs_sha256):
        selections.append((codes_run, codes_outputs_sha256))
        return real_select(data_dir, codes_run, codes_outputs_sha256=codes_outputs_sha256)

    def recording(real):
        def call(source, *args, **kwargs):
            touched.append(Path(source).absolute())
            return real(source, *args, **kwargs)
        return call

    def forbidden(*args, **kwargs):
        raise AssertionError('Stage 5 read the ITA source')

    monkeypatch.setattr(tri_codes, 'select_nodes', select)
    monkeypatch.setattr(code_build, 'check_source', forbidden)
    for module, name in ((manifest, 'sha256_file'), (pl, 'scan_parquet'),
                         (pl, 'read_parquet'), (pl, 'scan_csv')):
        monkeypatch.setattr(module, name, recording(getattr(module, name)))
    result = build_run(built, 'stage5_selector')
    directory = Path(result['directory'])
    verify_bundle(directory, built.data_dir, expected_outputs_sha256=result['outputs_sha256'])
    assert selections
    assert set(selections) == {(built.codes_run, built.codes_pin)}
    data_dir = built.data_dir.absolute()
    allowed = (data_dir / 'derived' / 'codes' / built.codes_run,
               run_root(built.data_dir).absolute(), data_dir / 'raw' / 'epa_tri' / 'basic')
    inside = [path for path in touched if path.is_relative_to(data_dir)]
    assert any(path.is_relative_to(allowed[2]) for path in inside)
    assert [path for path in inside
            if not any(path.is_relative_to(root) for root in allowed)] == []
    raw = read(directory, 'inputs.json')['raw']
    assert len(raw) == 3
    assert all(citation['path'].startswith('epa_tri/basic/') for citation in raw)
