'''CPS job-flow bundles: build, verify and compare, on a small hand-made monthly and ASEC case.'''

import json
import math
import platform
import shutil
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import polars as pl
import pytest
from cps_flow_fixtures import (
    JOB_FLOW_CPSID,
    JOB_FLOW_CPSIDV,
    JOB_FLOW_PEOPLE,
    asec_row,
    job_flow_rows,
    monthly_row,
    no_live_clients,  # noqa: F401
    offline_guards,
    seed_upstreams,
)
from polars.testing import assert_frame_equal
from vendor_link_fixtures import module_file, subprocess_modules

from embedding_data import (
    cps_flow_bundle,
    cps_flow_estimation,
    cps_flow_inputs,
    cps_flow_lists,
    cps_flow_references,
    cps_flow_targets,
    cps_flow_units,
    cps_flow_weights,
    manifest,
    paths,
    target_contract,
    target_io,
)
from embedding_data.cps_flow_bundle import (
    FILES,
    SCHEMA_VERSION,
    SOFTWARE_FILES,
    TABLES,
    build,
    compare_runs,
    freeze_software,
    run_directory,
    verify_bundle,
)

FIRST = 'first'
IND, OCC = 'feature:cps_industry_category:', 'feature:cps_occupation_category:'
DIMENSIONS = ('industry', 'occupation')
INPUT_FIELDS = {'run_id', 'contracts', 'upstream', 'deliveries', 'rules', 'divisors', 'bootstrap',
                'software', 'execution'}
LINK_MONTHS = [
    '2025-01>2025-02', '2025-02>2025-03', '2025-03>2025-04', '2025-04>2025-05',
    '2025-05>2025-06', '2025-06>2025-07', '2025-07>2025-08', '2025-08>2025-09',
    '2025-11>2025-12', '2025-12>2026-01', '2026-01>2026-02', '2026-02>2026-03',
    '2026-03>2026-04', '2026-04>2026-05', '2026-05>2026-06', '2026-06>2026-07',
    '2026-07>2026-08', '2026-08>2026-09']
EE_IND_SENS, EE_IND_STRICT = 'monthly_ee:industry:sensitivity', 'monthly_ee:industry:strict'
EE_OCC_SENS, EE_OCC_STRICT = 'monthly_ee:occupation:sensitivity', 'monthly_ee:occupation:strict'
UE_IND_SENS, UE_IND_STRICT = 'monthly_ue:industry:sensitivity', 'monthly_ue:industry:strict'
UE_OCC_SENS, UE_OCC_STRICT = 'monthly_ue:occupation:sensitivity', 'monthly_ue:occupation:strict'
# The spec's guard table, by later-month EMPSAME/ACTSAME: (industry, occupation).
SPEC_GUARDS = {
    **{f'01/{actsame}': ('changed', 'changed') for actsame in ('01', '02', '96', '97', '99')},
    '02/01': ('same', 'same'), '02/02': ('same', 'changed'),
    **{f'02/{actsame}': ('same', 'unusable') for actsame in ('96', '97', '99')},
    **{f'{empsame}/{actsame}': ('unusable', 'unusable') for empsame in ('96', '97', '99')
       for actsame in ('01', '02', '96', '97', '99')},
}
_QCODE = {'0': 'nonallocation', '1': 'edited', '2': 'edited', '3': 'edited', '4': 'allocated',
          '5': 'allocated', '6': 'allocated', '7': 'longitudinal'}
_QEMPSTAT = {'0': 'nonallocation', '1': 'edited', '2': 'edited', '3': 'edited',
             '4': 'allocated', '5': 'allocated', '6': 'longitudinal'}
FLAG_CLASSES = {
    'monthly': {'QEMPSTAT': _QEMPSTAT, 'QIND': _QCODE, 'QOCC': _QCODE},
    'asec': {'QEMPSTAT': _QEMPSTAT, 'QIND': _QCODE, 'QOCC': _QCODE,
             'QOCCLY': {'0': 'nonallocation', '1': 'allocated'}},
}
# The SD3 funnels of the case, by hand from `JOB_FLOW_PEOPLE` and `JOB_FLOW_ASEC`.
UE_FUNNEL = {'weight_null': 1, 'weight_zero': 1, 'origin_new_worker_22': 1,
             'origin_not_unemployed_21': 12, 'destination_not_employed': 1,
             'code_not_in_universe': 1, 'eligible': 4}
ASEC_FUNNEL = {'weight_nonpositive': 1, 'not_employed': 1, 'last_year_code_not_in_universe': 1,
               'current_code_not_in_universe': 1, 'same_category': 1, 'eligible': 3}
FUNNELS = {
    'monthly_ee:industry': {'weight_null': 1, 'weight_zero': 1, 'not_employed_both': 8,
                            'code_not_in_universe': 1, 'guard_unusable': 2,
                            'no_change_reported': 3, 'coding_noise': 2, 'eligible': 3},
    'monthly_ee:occupation': {'weight_null': 1, 'weight_zero': 1, 'not_employed_both': 8,
                              'code_not_in_universe': 2, 'guard_unusable': 3,
                              'no_change_reported': 2, 'coding_noise': 1, 'eligible': 3},
    'monthly_ue:industry': UE_FUNNEL, 'monthly_ue:occupation': UE_FUNNEL,
    'asec_retro:industry': ASEC_FUNNEL, 'asec_retro:occupation': ASEC_FUNNEL,
}
PRODUCTS = {
    'E1': [EE_IND_SENS, EE_IND_STRICT, EE_OCC_SENS, EE_OCC_STRICT],
    'E2': [EE_OCC_SENS, EE_OCC_STRICT],
    'E8': [EE_IND_SENS],
    'E15': [EE_IND_SENS, EE_IND_STRICT, EE_OCC_SENS, EE_OCC_STRICT],
    'U1': [UE_IND_SENS, UE_IND_STRICT, UE_OCC_SENS, UE_OCC_STRICT],
    'U2': [UE_IND_SENS, UE_IND_STRICT, UE_OCC_SENS, UE_OCC_STRICT],
    'U3': [UE_IND_SENS, UE_OCC_SENS],
    'U8': [UE_IND_SENS, UE_IND_STRICT, UE_OCC_SENS],
}
# The households with an eligible link of each monthly product (OD6).
HOUSEHOLDS = {'monthly_ee': (101, 102, 108), 'monthly_ue': (201, 202, 203, 208)}


def seed(root: Path, changes: dict | None = None, *, monthly=(), asec=()):
    rows, people = job_flow_rows(changes)
    return seed_upstreams(root, monthly=[*rows, *monthly], asec=[*people, *asec])


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    '''One seeded data root with the published run `first`, shared by the module.'''
    seeded = seed(tmp_path_factory.mktemp('cps_flow_bundle'))
    first = build(seeded.data_dir, FIRST, seeded.request)
    return SimpleNamespace(data_dir=seeded.data_dir, request=seeded.request, first=first,
                           directory=Path(first['directory']))


@pytest.fixture(scope='module')
def replay(built):
    '''A second published run of the same inputs, in the shared data root.'''
    return build(built.data_dir, 'replay', built.request)


@pytest.fixture(scope='module')
def changed(tmp_path_factory):
    '''A run of the case with one link weight changed in its last decimal place.'''
    seeded = seed(tmp_path_factory.mktemp('changed_weight'), {'E1': {'LNKFW1MWT': '1500.1235'}})
    result = build(seeded.data_dir, FIRST, seeded.request)
    return Path(result['directory'])


def run_root(data_dir: Path) -> Path:
    return run_directory(data_dir, FIRST).parent


def tree(root: Path) -> dict:
    '''Every path under root, with the bytes of each file.'''
    return {path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
            for path in sorted(root.rglob('*'))}


def read(directory: Path, name: str) -> dict:
    return json.loads((directory / name).read_text())


def table(directory: Path, name: str) -> pl.DataFrame:
    return pl.read_parquet(directory / (name + '.parquet'))


def normalized(value):
    return json.loads(json.dumps(value))


def copy_root(built, tmp_path: Path) -> Path:
    destination = tmp_path / 'data'
    shutil.copytree(built.data_dir, destination, symlinks=True)
    return destination


def copy_bundle(built, destination: Path, name: str = FIRST) -> Path:
    target = destination / name
    shutil.copytree(built.directory, target)
    return target


def repin(directory: Path) -> str:
    '''Rewrite outputs.json for the current bundle bytes and return its new pin.'''
    target_io.write_json(directory / 'outputs.json', target_io.inventory(directory, list(FILES)))
    return manifest.sha256_file(directory / 'outputs.json')


def edit_json(directory: Path, name: str, change) -> str:
    value = read(directory, name)
    change(value)
    target_io.write_json(directory / name, value)
    return repin(directory)


def edit_table(directory: Path, name: str, change) -> str:
    file = directory / (name + '.parquet')
    change(pl.read_parquet(file)).write_parquet(file)
    return repin(directory)


def change_first(column: str, change):
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


def no_publication(data_dir: Path, run_id: str) -> bool:
    return (not run_directory(data_dir, run_id).exists()
            and not (run_root(data_dir) / (run_id + '.part')).exists())


def total(*weights: str, k: int) -> float:
    return float(sum(Decimal(weight) for weight in weights)) / k


def person(name: str) -> int:
    return JOB_FLOW_CPSIDV + list(JOB_FLOW_PEOPLE).index(name) + 1


def household(number: int) -> int:
    return JOB_FLOW_CPSID + number


def target_values(directory: Path) -> dict:
    rows = table(directory, 'cps_job_flows').iter_rows(named=True)
    return {(row['universe'], row['unit_a'], row['unit_b'], row['measure']): row
            for row in rows}


# Plan tests.

def test_build_publishes_exactly_the_bundle_files(built):
    directory = built.directory
    assert directory == run_directory(built.data_dir, FIRST)
    names = {path.name for path in directory.iterdir()}
    assert names == {*FILES, 'outputs.json'}
    assert len(names) == 9
    outputs = read(directory, 'outputs.json')
    assert set(outputs) == set(FILES)
    assert 'outputs.json' not in outputs
    assert outputs == target_io.inventory(directory, list(FILES))
    assert built.first == {
        'run_id': FIRST,
        'directory': str(directory),
        'outputs_sha256': manifest.sha256_file(directory / 'outputs.json'),
    }


def test_occupied_final_or_partial_name_fails_before_writing(built):
    leftover = run_root(built.data_dir) / 'killed.part'
    leftover.mkdir()
    (leftover / 'cps_job_flows.parquet').write_bytes(b'bytes of a killed build')
    before = tree(built.data_dir)
    for run_id in (FIRST, 'killed'):
        with pytest.raises(ValueError, match='run or staging name already exists'):
            build(built.data_dir, run_id, built.request)
        assert tree(built.data_dir) == before
    shutil.rmtree(leftover)


def fail_estimate(monkeypatch):
    def failing(records, variant):
        raise ValueError('estimate failed')
    monkeypatch.setattr(cps_flow_estimation, 'estimate_asec', failing)
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
def test_failure_cleans_only_its_own_staging(failure, built, monkeypatch):
    root = run_root(built.data_dir)
    neighbor = root / 'neighbor.part'
    neighbor.mkdir()
    (neighbor / 'kept.txt').write_text('kept')
    before = tree(root)
    message = failure(monkeypatch)
    with pytest.raises(ValueError, match=message):
        build(built.data_dir, 'failed', built.request)
    assert tree(root) == before
    assert no_publication(built.data_dir, 'failed')
    shutil.rmtree(neighbor)


def append_byte(file: Path) -> None:
    file.write_bytes(file.read_bytes() + b' ')


def flip_byte(file: Path) -> None:
    data = bytearray(file.read_bytes())
    data[len(data) // 2] ^= 1
    file.write_bytes(bytes(data))


PIN_CHANGES = {
    'codes_outputs': lambda data_dir, request: append_byte(
        data_dir / 'derived/codes' / request.codes_run / 'outputs.json'),
    'cps_receipt': lambda data_dir, request: append_byte(
        data_dir / cps_flow_references.SNAPSHOT_ROOT / request.cps_receipt / 'receipt.json'),
    'monthly_parquet': lambda data_dir, request: flip_byte(
        data_dir / 'derived/cps/monthly/cps_00001.parquet'),
}


@pytest.mark.parametrize('change', ['software', *PIN_CHANGES])
def test_pins_and_software_are_rechecked_before_publication(change, built, tmp_path,
                                                            monkeypatch):
    data_dir = copy_root(built, tmp_path)
    if change == 'software':
        real, calls = cps_flow_bundle.freeze_software, []

        def changing():
            calls.append(True)
            frozen = real()
            return frozen if len(calls) == 1 else {**frozen, 'python': 'changed'}

        monkeypatch.setattr(cps_flow_bundle, 'freeze_software', changing)
        message = 'executing software changed before publication'
    else:
        real_write = target_io.write_json

        # The change lands after the weighted sources closed, just before the recheck.
        def changing(file, value):
            real_write(file, value)
            if file.name == 'report.json':
                PIN_CHANGES[change](data_dir, built.request)

        monkeypatch.setattr(target_io, 'write_json', changing)
        message = 'selected inputs changed'
    with pytest.raises(ValueError, match=message):
        build(data_dir, 'rechecked', built.request)
    if change == 'software':
        assert len(calls) == 2
    assert no_publication(data_dir, 'rechecked')


def test_verify_accepts_the_published_bundle(built):
    pin = built.first['outputs_sha256']
    verified = verify_bundle(built.directory, built.data_dir, expected_outputs_sha256=pin)
    report = read(built.directory, 'report.json')
    assert verified == {
        'run_id': FIRST,
        'outputs_sha256': pin,
        'rows': {name: report['tables'][name]['rows'] for name in TABLES},
    }
    assert verified['rows'] == {name: table(built.directory, name).height for name in TABLES}
    assert all(rows > 0 for rows in verified['rows'].values())


def test_verify_refuses_a_wrong_pin_a_changed_table_and_a_changed_upstream_pin(built, tmp_path):
    with pytest.raises(ValueError, match='detached inventory checksum differs'):
        verify_bundle(built.directory, built.data_dir, expected_outputs_sha256='0' * 64)
    changed_table = copy_bundle(built, tmp_path / 'table')
    pin = edit_table(changed_table, 'cps_job_flows', change_first('value', lambda c: c + 1))
    with pytest.raises(ValueError, match='cps_job_flows: published table differs'):
        verify_bundle(changed_table, built.data_dir, expected_outputs_sha256=pin)
    changed_pin = copy_bundle(built, tmp_path / 'pin')
    pin = edit_json(changed_pin, 'inputs.json',
                    set_path('upstream', 'codes_run', 'outputs_sha256', '1' * 64))
    with pytest.raises(ValueError, match='codes_run: detached checksum differs'):
        verify_bundle(changed_pin, built.data_dir, expected_outputs_sha256=pin)
    data_dir = copy_root(built, tmp_path)
    append_byte(data_dir / 'derived/codes' / built.request.codes_run / 'outputs.json')
    with pytest.raises(ValueError, match='codes_run: detached checksum differs'):
        verify_bundle(run_directory(data_dir, FIRST), data_dir,
                      expected_outputs_sha256=built.first['outputs_sha256'])


def software_copy(tmp_path: Path, changed: str | None) -> Path:
    '''Copy every software file, and append a comment line to `changed`.'''
    copy = tmp_path / 'software'
    for name in SOFTWARE_FILES:
        (copy / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(paths.PROJECT_ROOT / name, copy / name)
    if changed is not None:
        (copy / changed).write_text((copy / changed).read_text() + '\n# changed\n')
    return copy


@pytest.mark.parametrize('changed', [None, 'src/embedding_data/cps_flow_guards.py', 'uv.lock'])
def test_a_changed_software_file_makes_verify_refuse(changed, built, tmp_path, monkeypatch):
    monkeypatch.setattr(cps_flow_bundle, 'SOFTWARE_ROOT', software_copy(tmp_path, changed))
    pin = built.first['outputs_sha256']
    if changed is None:
        assert verify_bundle(built.directory, built.data_dir,
                             expected_outputs_sha256=pin)['run_id'] == FIRST
        return
    with pytest.raises(ValueError, match='executing software differs from the build'):
        verify_bundle(built.directory, built.data_dir, expected_outputs_sha256=pin)


def test_build_verify_and_compare_make_no_protected_access(built, monkeypatch):
    counts = offline_guards(monkeypatch)
    result = build(built.data_dir, 'offline', built.request)
    directory = Path(result['directory'])
    verify_bundle(directory, built.data_dir, expected_outputs_sha256=result['outputs_sha256'])
    assert compare_runs(built.directory, directory)['equal'] is True
    assert counts == {'network': 0, 'environment_file': 0, 'live_client': 0}


def test_two_builds_compare_equal_and_a_changed_weight_compares_unequal(built, replay, changed):
    second = Path(replay['directory'])
    result = compare_runs(built.directory, second)
    assert result['equal'] is True
    assert result['report_equal'] is True
    assert result['trust_established'] is False
    assert list(result['tables']) == list(TABLES)
    report = read(built.directory, 'report.json')
    for name in TABLES:
        rows = report['tables'][name]['rows']
        assert result['tables'][name] == {'schema_equal': True, 'values_equal': True,
                                          'first_rows': rows, 'second_rows': rows}
    unequal = compare_runs(built.directory, changed)
    assert unequal['equal'] is False
    assert unequal['trust_established'] is False
    assert unequal['tables']['cps_job_flows']['values_equal'] is False
    assert unequal['tables']['cps_category_units']['values_equal'] is True


def test_the_fixture_exercises_every_spec_case(built):
    report = read(built.directory, 'report.json')
    for product, reasons in FUNNELS.items():
        assert all(report['funnels'][product][reason] >= 1 for reason in reasons)
    targets = table(built.directory, 'cps_job_flows')
    special = (pl.col('unit_a').is_in([IND + '9890', OCC + '9840'])
               | pl.col('unit_b').is_in([IND + '9890', OCC + '9840']))
    specials = targets.filter(special)
    monthly = specials.filter(pl.col('sample_set') == 'cps-basic-2025-01-to-2026-09')
    assert IND + '9890' in monthly['unit_a'].to_list()
    assert OCC + '9840' in monthly['unit_a'].to_list()
    assert all('special_military' in flags for flags in specials['flags'])
    assert set(specials['universe']) == {'monthly_ue:sensitivity', 'asec_retro:sensitivity'}
    assert not any('special_military' in flags for flags in targets.filter(~special)['flags'])
    assert report['guard_source_exceptions'] == {'empsame_in_mish_1_or_5': 2}
    assert report['linkage']['two_month'] == {
        '2025-09>2025-11': {'cpsidv': 1, 'cpsidp': 1, 'other_gap_matches': 1}}
    asec = targets.filter(pl.col('sample_set') == 'cps-asec-2025-2026')
    assert asec.height and all('unguarded_upper_bound' in flags for flags in asec['flags'])


def test_software_files_equal_the_measured_import_closure():
    loaded = subprocess_modules('embedding_data.cps_flow_bundle')
    closure = {module_file(module) for module in loaded} | {'pyproject.toml', 'uv.lock'}
    assert closure <= set(SOFTWARE_FILES)


# Additional tests beyond the plan.

def test_software_files_are_sorted_existing_and_name_every_flow_module():
    assert list(SOFTWARE_FILES) == sorted(set(SOFTWARE_FILES))
    assert all((paths.PROJECT_ROOT / name).is_file() for name in SOFTWARE_FILES)
    flow_modules = {f'src/embedding_data/cps_flow_{name}.py' for name in (
        'bundle', 'estimation', 'guards', 'inputs', 'linkage', 'lists', 'references',
        'targets', 'units', 'weights')}
    assert flow_modules <= set(SOFTWARE_FILES)


def test_contract_constants_and_run_directory(tmp_path):
    assert SCHEMA_VERSION == 'cps-job-flows-v1' == cps_flow_targets.SCHEMA_VERSION
    assert TABLES == ('cps_job_flows', 'cps_category_units', 'cps_flow_support',
                      'cps_flow_replicates', 'cps_flow_diagnostics', 'cps_linked_pairs')
    assert FILES == (*(name + '.parquet' for name in TABLES), 'inputs.json', 'report.json')
    assert cps_flow_bundle.SOFTWARE_ROOT == paths.PROJECT_ROOT
    assert list(cps_flow_bundle.LINK_MONTHS) == LINK_MONTHS
    assert len(LINK_MONTHS) == cps_flow_estimation.MONTHLY_K
    assert run_directory(tmp_path, 'run_1') == tmp_path / 'derived/cps/job-flows/run_1'
    assert run_directory(str(tmp_path), 'A-2') == tmp_path / 'derived/cps/job-flows/A-2'
    for unsafe in ('', '_run', '-run', 'a/b', '../a', 'a b', 'a.b', None, 3):
        with pytest.raises(ValueError, match='unsafe run ID'):
            run_directory(tmp_path, unsafe)


def test_freeze_software_records_files_python_and_dependencies():
    frozen = freeze_software()
    assert set(frozen) == {'files', 'python', 'python_full', 'implementation', 'dependencies',
                           'uv_lock_sha256'}
    assert list(frozen['files']) == list(SOFTWARE_FILES)
    for name, record in frozen['files'].items():
        assert record == target_io.file_record(paths.PROJECT_ROOT / name)
    assert frozen['python'] == platform.python_version()
    assert frozen['python_full'] == sys.version
    assert frozen['implementation'] == platform.python_implementation()
    assert frozen['dependencies']['polars'] == pl.__version__
    assert list(frozen['dependencies']) == sorted(frozen['dependencies'])
    assert frozen['uv_lock_sha256'] == manifest.sha256_file(paths.PROJECT_ROOT / 'uv.lock')


def test_inputs_record_the_selection_rules_divisors_and_bootstrap(built):
    inputs = read(built.directory, 'inputs.json')
    assert set(inputs) == INPUT_FIELDS
    selected = cps_flow_inputs.select_inputs(built.data_dir, built.request)
    assert inputs['run_id'] == FIRST
    assert inputs['contracts'] == cps_flow_targets.CONTRACTS == {
        'bundle': 'cps-job-flows-v1', 'references': 'cps-job-flows-references-v1',
        'targets': 'targets-v1'}
    assert inputs['upstream'] == normalized(selected.provenance['upstream'])
    assert inputs['deliveries'] == normalized(selected.provenance['deliveries'])
    rules = inputs['rules']
    assert set(rules) == {'guards', 'flag_classes', 'value_classes', 'ddi', 'funnels', 'flags'}
    assert rules['ddi'] == {
        'monthly': normalized(cps_flow_inputs.check_ddi('monthly', selected.monthly.ddi)),
        'asec': normalized(cps_flow_inputs.check_ddi('asec', selected.asec.ddi))}
    assert rules['ddi']['monthly']['EMPSAME'] == {
        '1': 'No', '2': 'Yes', '96': 'Refused', '97': "Don't know", '99': 'NIU'}
    assert rules['guards'] == {reading: {'industry': industry, 'occupation': occupation}
                               for reading, (industry, occupation) in SPEC_GUARDS.items()}
    assert rules['flag_classes'] == FLAG_CLASSES
    assert rules['value_classes'] == {
        'not_in_universe': '0000', 'specials': {'industry': '9890', 'occupation': '9840'},
        'refused_statuses': ['no_naics_equivalent', 'no_soc_equivalent'],
        'fields': {'monthly': {'IND': 'industry', 'OCC': 'occupation'},
                   'asec': {'IND': 'industry', 'OCC': 'occupation', 'INDLY': 'industry',
                            'OCCLY': 'occupation'}}}
    assert rules['funnels'] == {product: [*reasons] for product, reasons in {
        'monthly_ee': ('weight_null', 'weight_zero', 'not_employed_both',
                       'code_not_in_universe', 'guard_unusable', 'no_change_reported',
                       'coding_noise', 'eligible'),
        'monthly_ue': ('weight_null', 'weight_zero', 'origin_new_worker_22',
                       'origin_not_unemployed_21', 'destination_not_employed',
                       'code_not_in_universe', 'eligible'),
        'asec_retro': ('weight_nonpositive', 'not_employed', 'last_year_code_not_in_universe',
                       'current_code_not_in_universe', 'same_category', 'eligible')}.items()}
    assert rules['flags'] == ['bootstrap_approximate', 'size_gate_pending', 'special_military',
                              'unguarded_upper_bound']
    assert inputs['divisors'] == {'monthly_k': 18, 'asec_k': 2, 'link_months': LINK_MONTHS,
                                  'asec_periods': ['asec-2025', 'asec-2026']}
    assert inputs['bootstrap'] == {'seed': 20261123, 'replicates': 200,
                                   'scope': cps_flow_bundle.BOOTSTRAP_SCOPE}
    assert 'union' in inputs['bootstrap']['scope']
    assert inputs['software'] == freeze_software()
    assert set(inputs['execution']) == {'commit', 'dirty', 'created_at'}


def test_inputs_are_recorded_in_the_form_json_reads_back(built):
    selected = cps_flow_inputs.select_inputs(built.data_dir, built.request)
    ddi = {'monthly': cps_flow_inputs.check_ddi('monthly', selected.monthly.ddi),
           'asec': cps_flow_inputs.check_ddi('asec', selected.asec.ddi)}
    assert 1 in ddi['monthly']['EMPSAME']
    recorded = read(built.directory, 'inputs.json')
    inputs = cps_flow_bundle._inputs(FIRST, selected, ddi, freeze_software(),
                                     recorded['execution'])
    assert inputs == recorded
    assert '1' in inputs['rules']['ddi']['monthly']['EMPSAME']


def test_tables_have_their_contract_schemas(built):
    targets = table(built.directory, 'cps_job_flows')
    assert list(targets.schema.items()) == list(target_contract.TARGET_SCHEMA.items())
    target_contract.validate_targets(targets)
    keys = targets.select(target_contract.TARGET_KEY_COLUMNS).rows()
    assert keys == sorted(keys)
    for name, schema in cps_flow_targets.COMPANION_SCHEMAS.items():
        assert list(table(built.directory, name).schema.items()) == list(schema.items())


def test_targets_are_the_hand_computed_pooled_flows(built):
    values = target_values(built.directory)

    def value(universe, unit_a, unit_b, measure='average_total'):
        return values[(universe, unit_a, unit_b, measure)]['value']

    # Monthly flows use the earlier month's LNKFW1MWT and k = 18.
    assert value('monthly_ee:strict', IND + '0170', IND + '1370') == total('1500.1234', k=18)
    assert value('monthly_ee:strict', IND + '0170', IND + '1370', 'forward_share') == 1.0
    assert value('monthly_ee:sensitivity', IND + '0170', IND + '1370', 'forward_share') == (
        total('1500.1234', k=18) / total('1500.1234', '2400.5000', k=18))
    assert ('monthly_ee:strict', IND + '0170', IND + '3070', 'average_total') not in values
    assert value('monthly_ee:sensitivity', IND + '0170', IND + '3070') == total(
        '2400.5000', k=18)
    assert value('monthly_ee:strict', OCC + '0010', OCC + '2200') == total('1200.5000', k=18)
    assert value('monthly_ee:strict', OCC + '0020', OCC + '0010') == total('2100.2500', k=18)
    assert (('monthly_ee:sensitivity', IND + '0170', IND + '1380', 'average_total')
            not in values)
    assert value('monthly_ue:strict', IND + '1370', IND + '1370') == total(
        '1350.0000', '1850.0000', k=18)
    stay = values[('monthly_ue:strict', IND + '1370', IND + '1370', 'average_total')]
    assert stay['n_unweighted'] == 2 and stay['n_weighted'] == total(
        '1350.0000', '1850.0000', k=18)
    assert value('monthly_ue:sensitivity', IND + '9890', IND + '0170') == total(
        '1450.0000', k=18)
    assert value('monthly_ue:sensitivity', OCC + '9840', OCC + '0010', 'forward_share') == (
        total('1450.0000', k=18) / total('1450.0000', '1850.0000', k=18))
    # ASEC uses ASECWT, k = 2, and the 160 replicates for the SE.
    point = total('3000.5000', k=2)
    found = values[('asec_retro:sensitivity', IND + '0170', IND + '1370', 'average_total')]
    assert found['value'] == point
    replicates = [total(f'{3000 + number}.5000', k=2) for number in range(1, 161)]
    assert found['se'] == math.sqrt(
        4 / 160 * math.fsum((value - point) ** 2 for value in replicates))
    assert found['se_method'] == 'replicate'
    assert value('asec_retro:sensitivity', OCC + '0020', OCC + '2200') == total(
        '2600.0000', k=2)
    rows = table(built.directory, 'cps_flow_replicates').filter(
        (pl.col('product') == 'asec_retro') & (pl.col('dimension') == 'industry')
        & (pl.col('unit_a') == '0170') & (pl.col('unit_b') == '1370'))
    assert rows['replicate'].to_list() == list(range(1, 161))
    assert rows['numerator'].to_list() == replicates
    universes = set(table(built.directory, 'cps_job_flows')['universe'])
    assert universes == {'monthly_ee:strict', 'monthly_ee:sensitivity', 'monthly_ue:strict',
                         'monthly_ue:sensitivity', 'asec_retro:sensitivity'}


def test_support_rows_name_the_contributing_periods(built):
    support = table(built.directory, 'cps_flow_support').filter(
        (pl.col('product') == 'monthly_ue') & (pl.col('dimension') == 'industry')
        & (pl.col('policy') == 'strict') & (pl.col('kind') == 'cell')
        & (pl.col('unit_a') == '1370'))
    assert support.select('period', 'n_unweighted', 'mass').rows() == [
        ('2025-01>2025-02', 1, 1350.0), ('2026-03>2026-04', 1, 1850.0)]
    asec = table(built.directory, 'cps_flow_support').filter(
        (pl.col('product') == 'asec_retro') & (pl.col('kind') == 'cell'))
    assert set(asec['period']) == {'asec-2025', 'asec-2026'}


def selected_units(built) -> pl.DataFrame:
    '''The unit registry recomputed from the selected files, outside the bundle code.'''
    selected = cps_flow_inputs.select_inputs(built.data_dir, built.request)
    delivered = {'industry': set(), 'occupation': set()}
    for delivery, fields in ((selected.monthly, ('IND', 'OCC')),
                             (selected.asec, ('IND', 'OCC', 'INDLY', 'OCCLY'))):
        frame = pl.read_parquet(delivery.parquet)
        for field in fields:
            dimension = 'industry' if field.startswith('IND') else 'occupation'
            delivered[dimension].update(frame[field].to_list())
    request = built.request
    return cps_flow_units.build_units(
        cps_flow_lists.read_industry_list(selected.industry_workbook),
        cps_flow_lists.read_occupation_list(selected.occupation_workbook),
        naics_nodes=pl.read_parquet(selected.naics_nodes),
        soc_nodes=pl.read_parquet(selected.soc_nodes), paths=pl.read_parquet(selected.code_paths),
        pums=cps_flow_units.read_pums_lists(selected.pums_lookup), delivered=delivered,
        evidence=cps_flow_references.special_evidence(selected.cps_receipt),
        references={'industry': request.stage7_receipt, 'occupation': request.stage8_receipt,
                    'special': request.cps_receipt})


def test_units_come_from_the_selected_lists_nodes_and_receipts(built):
    units = table(built.directory, 'cps_category_units')
    assert_frame_equal(units, selected_units(built))
    by_status = {(row['unit_type'], row['status'] == 'special_military'): row['reference_id']
                 for row in units.iter_rows(named=True)}
    request = built.request
    assert by_status == {
        ('cps_industry_category', False): request.stage7_receipt,
        ('cps_occupation_category', False): request.stage8_receipt,
        ('cps_industry_category', True): request.cps_receipt,
        ('cps_occupation_category', True): request.cps_receipt}
    checks = dict(units.filter(pl.col('x_cross_check').is_not_null())
                  .select('code', 'x_cross_check').iter_rows())
    assert checks == {'8025': 'equal', '8225': 'strict_subset'}
    assert units.filter(pl.col('code') == '0170')['candidates'].to_list() == [['211120']]


def test_report_counts_value_classes_links_weights_and_funnels(built):
    report = read(built.directory, 'report.json')
    assert report['run_id'] == FIRST
    assert report['value_classes'] == {
        'monthly/IND': {'mapped': 42, 'not_in_universe': 4, 'special': 2},
        'monthly/OCC': {'mapped': 40, 'not_in_universe': 5, 'special': 3},
        'asec/IND': {'mapped': 7, 'not_in_universe': 1, 'special': 0},
        'asec/OCC': {'mapped': 7, 'not_in_universe': 1, 'special': 0},
        'asec/INDLY': {'mapped': 6, 'not_in_universe': 1, 'special': 1},
        'asec/OCCLY': {'mapped': 6, 'not_in_universe': 1, 'special': 1}}
    assert report['specials'] == {'monthly/IND/2025': 2, 'monthly/OCC/2025': 2,
                                  'monthly/OCC/2026': 1, 'asec/INDLY/2026': 1,
                                  'asec/OCCLY/2026': 1}
    assert report['linkage'] == {
        'one_month': {'2025-01>2025-02': {'cpsidv': 19, 'cpsidp': 18, 'other_gap_matches': 1},
                      '2026-03>2026-04': {'cpsidv': 2, 'cpsidp': 2, 'other_gap_matches': 0}},
        'two_month': {'2025-09>2025-11': {'cpsidv': 1, 'cpsidp': 1, 'other_gap_matches': 1}}}
    assert report['weights'] == {'null': 1, 'zero': 1, 'positive': 19}
    assert report['funnels'] == FUNNELS
    assert report['usable_guard_share'] == {
        'monthly_ee:industry': 9 / 11, 'monthly_ee:occupation': 8 / 11,
        'monthly_ue': 'not_applicable', 'asec_retro': 'not_applicable'}
    zero = {'0': 1}
    counts = {'10': {'0': 6}, '12': zero, '21': zero}
    assert report['asec_flags_by_empstat'] == {
        'QIND': counts, 'QOCC': counts, 'QEMPSTAT': counts,
        'QOCCLY': {'10': {'0': 5, '1': 1}, '12': zero, '21': zero}}
    assert report['x_categories'] == {'equal': 1, 'strict_subset': 1,
                                      'not_delivered_no_pums_list': 0}


def diagnostics(built, topic: str) -> dict:
    rows = table(built.directory, 'cps_flow_diagnostics').filter(pl.col('topic') == topic)
    return {(row['product'], row['dimension'], row['reason']): row['count']
            for row in rows.iter_rows(named=True)}


def test_guards_evidence_and_specials_are_counted_over_their_populations(built):
    assert diagnostics(built, 'guard') == {
        ('monthly_ee', 'industry', 'changed'): 4, ('monthly_ee', 'industry', 'same'): 5,
        ('monthly_ee', 'industry', 'unusable'): 2,
        ('monthly_ee', 'occupation', 'changed'): 5, ('monthly_ee', 'occupation', 'same'): 3,
        ('monthly_ee', 'occupation', 'unusable'): 3,
        ('monthly_ee', 'industry', 'noise_after_duty_change'): 1,
        (None, None, 'empsame_in_mish_1_or_5'): 2}
    evidence = {key: count for key, count in diagnostics(built, 'evidence').items()
                if key[0] != 'asec_retro'}
    assert evidence == {
        ('monthly_ee', 'industry', 'flag:QIND:allocated'): 1,
        ('monthly_ee', 'industry', 'special_military'): 2,
        ('monthly_ee', 'occupation', 'flag:QOCC:edited'): 1,
        ('monthly_ee', 'occupation', 'special_military'): 3,
        ('monthly_ue', 'industry', 'flag:QIND:allocated'): 1,
        ('monthly_ue', 'industry', 'special_military'): 2,
        ('monthly_ue', 'occupation', 'flag:QOCC:edited'): 1,
        ('monthly_ue', 'occupation', 'special_military'): 3}
    assert diagnostics(built, 'special') == {
        ('monthly_ee', 'industry', 'special_end'): 2,
        ('monthly_ee', 'occupation', 'special_end'): 3,
        ('monthly_ue', 'industry', 'special_end'): 2,
        ('monthly_ue', 'occupation', 'special_end'): 3,
        ('asec_retro', 'industry', 'special_end'): 1,
        ('asec_retro', 'occupation', 'special_end'): 1}
    assert diagnostics(built, 'weight') == {(None, None, 'null'): 1, (None, None, 'zero'): 1,
                                            (None, None, 'positive'): 19}


def test_linked_pairs_hold_the_monthly_links_and_their_products(built):
    pairs = table(built.directory, 'cps_linked_pairs')
    linked = [name for name in JOB_FLOW_PEOPLE if name not in ('L2', 'L3')]
    assert sorted(pairs['CPSIDV'].to_list()) == sorted(person(name) for name in linked)
    rows = {row['CPSIDV']: row for row in pairs.iter_rows(named=True)}
    assert {name: rows[person(name)]['products'] for name in linked} == {
        name: PRODUCTS.get(name, []) for name in linked}
    two_month = rows[person('L1')]
    assert (two_month['link_type'], two_month['weight_a'], two_month['weight_status']) == (
        'two_month', None, 'not_linkable')
    assert (two_month['month_a'], two_month['month_b']) == ('2025-09', '2025-11')
    assert rows[person('E1')]['weight_a'] == float(Decimal('1500.1234'))
    assert rows[person('E1')]['CPSID'] == household(101)
    assert (rows[person('E9')]['weight_a'], rows[person('E9')]['weight_status']) == (None, 'null')
    assert (rows[person('E10')]['weight_a'], rows[person('E10')]['weight_status']) == (
        0.0, 'zero')
    assert {name for name in TABLES if 'CPSIDV' in table(built.directory, name).columns} == {
        'cps_linked_pairs'}


def numerators(built, product, dimension, unit_a, unit_b) -> list[float]:
    rows = table(built.directory, 'cps_flow_replicates').filter(
        (pl.col('product') == product) & (pl.col('dimension') == dimension)
        & (pl.col('policy') == 'strict') & (pl.col('unit_a') == unit_a)
        & (pl.col('unit_b') == unit_b))
    assert rows['replicate'].to_list() == list(range(1, 201))
    return rows['numerator'].to_list()


def drawn(product: str, number: int, weight: str) -> list[float]:
    '''The bootstrap numerators of a one-link cell, from the product's household list.'''
    households = sorted(household(found) for found in HOUSEHOLDS[product])
    draws = cps_flow_estimation.household_draws(households).filter(
        pl.col('CPSID') == household(number)).sort('replicate')['draws']
    return [float(Decimal(weight) * count) / 18 for count in draws]


def test_bootstrap_draws_one_household_list_per_product(built, monkeypatch):
    # Strict cells read the product's draws, though their own households are fewer.
    assert numerators(built, 'monthly_ee', 'industry', '0170', '1370') == drawn(
        'monthly_ee', 101, '1500.1234')
    assert numerators(built, 'monthly_ue', 'occupation', '0010', '7000') == drawn(
        'monthly_ue', 201, '1250.0000')
    real, calls = cps_flow_estimation.household_draws, []

    def counted(households, **options):
        calls.append(households)
        return real(households, **options)

    monkeypatch.setattr(cps_flow_estimation, 'household_draws', counted)
    build(built.data_dir, 'draws', built.request)
    assert calls == [sorted(household(found) for found in HOUSEHOLDS[product])
                     for product in ('monthly_ee', 'monthly_ue')]


def test_report_and_inputs_hold_no_person_identifier(built):
    monthly, asec = job_flow_rows()
    identifiers = {str(row[name]) for row in (*monthly, *asec)
                   for name in ('CPSID', 'CPSIDV', 'CPSIDP')}
    for name in ('report.json', 'inputs.json', 'outputs.json'):
        text = (built.directory / name).read_text()
        assert not any(identifier in text for identifier in identifiers)
    for name in TABLES:
        if name != 'cps_linked_pairs':
            assert not {'CPSID', 'CPSIDV', 'CPSIDP'} & set(table(built.directory, name).columns)


REFUSED_ROWS = {
    'monthly_industry_9920': (dict(monthly=[monthly_row(CPSIDV=5, EMPSTAT=21, IND='9920')]),
                              'delivered code has no equivalent'),
    'monthly_occupation_9830': (dict(monthly=[monthly_row(CPSIDV=5, EMPSTAT=21, OCC='9830')]),
                                'delivered code has no equivalent'),
    'asec_industry_9920': (dict(asec=[asec_row(IND='9920')]),
                           'delivered code has no equivalent'),
    'asec_last_year_industry_9920': (dict(asec=[asec_row(INDLY='9920')]),
                                     'delivered code has no equivalent'),
    'asec_last_year_occupation_9830': (dict(asec=[asec_row(OCCLY='9830')]),
                                       'delivered code has no equivalent'),
    'asec_occupation_9830': (dict(asec=[asec_row(OCC='9830')]),
                             'delivered code has no equivalent'),
    'link_after_the_window': (dict(monthly=[
        monthly_row(CPSIDV=5, YEAR=2026, MONTH=9, MISH=1),
        monthly_row(CPSIDV=5, YEAR=2026, MONTH=10, MISH=2)]),
        'a one-month link falls outside the frozen link months'),
    'october_2025': (dict(monthly=[
        monthly_row(CPSIDV=5, YEAR=2025, MONTH=9, MISH=1),
        monthly_row(CPSIDV=5, YEAR=2025, MONTH=10, MISH=2)]),
        'a one-month link falls outside the frozen link months'),
    'asec_year_outside': (dict(asec=[asec_row(YEAR=2024)]),
                          'an ASEC year falls outside the frozen periods'),
    'asec_year_after': (dict(asec=[asec_row(YEAR=2027)]),
                        'an ASEC year falls outside the frozen periods'),
}


@pytest.mark.parametrize('case', REFUSED_ROWS)
def test_build_refuses_rows_outside_its_rules(case, tmp_path):
    rows, message = REFUSED_ROWS[case]
    seeded = seed(tmp_path, **rows)
    with pytest.raises(ValueError, match=message) as error:
        build(seeded.data_dir, 'refused', seeded.request)
    assert str(JOB_FLOW_CPSIDV) not in str(error.value)
    assert no_publication(seeded.data_dir, 'refused')


def other_name(built, tmp_path):
    return copy_bundle(built, tmp_path, 'other'), None, 'recorded run ID differs'


def recorded(change, message):
    def prepare(built, tmp_path):
        directory = copy_bundle(built, tmp_path)
        name, edit = change
        return directory, edit_json(directory, name, edit), message
    return prepare


RECORDED_CASES = {
    'run_name': other_name,
    'run_id': recorded(('inputs.json', set_path('run_id', 'other')), 'recorded run ID differs'),
    'missing_field': recorded(('inputs.json', delete_path('divisors')),
                              'recorded inputs are malformed'),
    'extra_field': recorded(('inputs.json', set_path('request', {})),
                            'recorded inputs are malformed'),
    'upstream_id_type': recorded(('inputs.json', set_path('upstream', 'codes_run', 'run_id', 3)),
                                 'recorded inputs are malformed'),
    'upstream_missing': recorded(('inputs.json', delete_path('upstream', 'cps_receipt')),
                                 'recorded inputs are malformed'),
    'contracts': recorded(('inputs.json', set_path('contracts', 'bundle', 'cps-job-flows-v0')),
                          'contract versions differ'),
    'report_contracts': recorded(
        ('report.json', set_path('contracts', 'targets', 'targets-v0')),
        'contract versions differ'),
    'software': recorded(('inputs.json', set_path('software', 'python', '0.0.0')),
                         'executing software differs from the build'),
    'upstream_pin': recorded(
        ('inputs.json', set_path('upstream', 'cps_receipt', 'receipt_sha256', '2' * 64)),
        'cps_receipt: detached checksum differs'),
    'rules': recorded(('inputs.json', set_path('rules', 'flags', ['size_gate_pending'])),
                      'recorded inputs differ from the recomputation'),
    'divisors': recorded(('inputs.json', set_path('divisors', 'monthly_k', 19)),
                         'recorded inputs differ from the recomputation'),
    'bootstrap': recorded(('inputs.json', set_path('bootstrap', 'seed', 1)),
                          'recorded inputs differ from the recomputation'),
    'deliveries': recorded(('inputs.json', set_path('deliveries', 'monthly', 'samples', [])),
                           'recorded inputs differ from the recomputation'),
    'report': recorded(
        ('report.json', set_path('funnels', 'asec_retro:industry', 'eligible', 4)),
        'published report differs from the recomputation'),
    'report_run_id': recorded(('report.json', set_path('run_id', 'other')),
                              'published report differs from the recomputation'),
}


@pytest.mark.parametrize('case', RECORDED_CASES)
def test_verify_refuses_recorded_differences(case, built, tmp_path):
    directory, pin, message = RECORDED_CASES[case](built, tmp_path)
    pin = pin or manifest.sha256_file(directory / 'outputs.json')
    with pytest.raises(ValueError, match=message):
        verify_bundle(directory, built.data_dir, expected_outputs_sha256=pin)


def test_verify_accepts_a_copy_with_its_recorded_execution(built, tmp_path):
    directory = copy_bundle(built, tmp_path)
    assert verify_bundle(directory, built.data_dir,
                         expected_outputs_sha256=built.first['outputs_sha256'])['run_id'] == FIRST


TABLE_CHANGES = {
    'cps_job_flows': change_first('value', lambda c: c + 1),
    'cps_category_units': change_first('label', lambda c: c + ' (changed)'),
    'cps_flow_support': change_first('mass', lambda c: c + 1),
    'cps_flow_replicates': change_first('numerator', lambda c: c + 1),
    'cps_flow_diagnostics': change_first('count', lambda c: c + 1),
    'cps_linked_pairs': change_first('mish_a', lambda c: c + 1),
}


@pytest.mark.parametrize('name', TABLES)
def test_verify_detects_each_table_tamper(name, built, tmp_path):
    directory = copy_bundle(built, tmp_path)
    pin = edit_table(directory, name, TABLE_CHANGES[name])
    with pytest.raises(ValueError, match=f'{name}: published table differs'):
        verify_bundle(directory, built.data_dir, expected_outputs_sha256=pin)


def add_directory(directory):
    (directory / 'extra').mkdir()


def add_file(directory):
    (directory / 'extra.txt').write_text('extra')


def drop_report(directory):
    (directory / 'report.json').unlink()


def rewrite_outputs(change):
    def edit(directory):
        outputs = read(directory, 'outputs.json')
        change(outputs)
        target_io.write_json(directory / 'outputs.json', outputs)
    return edit


def raw_outputs(text_of):
    def edit(directory):
        file = directory / 'outputs.json'
        file.write_text(text_of(file.read_text()))
    return edit


LAYOUT_CASES = {
    'extra_directory': (add_directory, 'bundle file set differs'),
    'extra_file': (add_file, 'bundle file set differs'),
    'missing_file': (drop_report, 'bundle file set differs'),
    'inventory_rows': (rewrite_outputs(set_path('cps_job_flows.parquet', 'rows', 1)),
                       'inventory hash, size, rows or ordered schema differs'),
    'inventory_hash': (rewrite_outputs(set_path('report.json', 'sha256', '3' * 64)),
                       'report.json: inventory hash or size differs'),
    'inventory_schema_dropped': (rewrite_outputs(delete_path('cps_flow_support.parquet',
                                                             'schema')),
                                 'output inventory records differ'),
    'not_canonical': (raw_outputs(lambda text: json.dumps(json.loads(text)) + '\n'),
                      'outputs.json: not canonical JSON'),
    'duplicate_key': (raw_outputs(lambda text: '{"report.json": {}, ' + text.lstrip()[1:]),
                      'duplicate JSON key'),
}


@pytest.mark.parametrize('case', LAYOUT_CASES)
def test_verify_refuses_bundle_layout_before_reading_inputs(case, built, tmp_path, monkeypatch):
    directory = copy_bundle(built, tmp_path)
    change, message = LAYOUT_CASES[case]
    change(directory)
    pin = manifest.sha256_file(directory / 'outputs.json')

    def unread(*args, **kwargs):
        raise AssertionError('verify read the upstreams before the bundle layout')

    monkeypatch.setattr(cps_flow_inputs, 'select_inputs', unread)
    with pytest.raises(ValueError, match=message):
        verify_bundle(directory, built.data_dir, expected_outputs_sha256=pin)


def test_verify_refuses_an_unpublished_name_and_a_malformed_pin(built, tmp_path):
    staged = copy_bundle(built, tmp_path, FIRST + '.part')
    pin = built.first['outputs_sha256']
    with pytest.raises(ValueError, match='an interrupted bundle is not published'):
        verify_bundle(staged, built.data_dir, expected_outputs_sha256=pin)
    for pin in ('abc', 'A' * 64, None):
        with pytest.raises(ValueError, match='invalid detached checksum'):
            verify_bundle(built.directory, built.data_dir, expected_outputs_sha256=pin)


def test_verify_recomputes_outside_the_data_root_and_changes_nothing(built, monkeypatch):
    real, scratches = cps_flow_weights.weighted_sources, []

    def spied(selected, scratch):
        scratches.append(Path(scratch))
        return real(selected, scratch)

    monkeypatch.setattr(cps_flow_weights, 'weighted_sources', spied)
    before = tree(built.data_dir)
    verify_bundle(built.directory, built.data_dir,
                  expected_outputs_sha256=built.first['outputs_sha256'])
    assert tree(built.data_dir) == before
    [scratch] = scratches
    assert not scratch.resolve().is_relative_to(built.data_dir.resolve())
    assert not scratch.exists()


def test_build_keeps_its_scratch_inside_its_staging_and_removes_it(built, monkeypatch):
    real, scratches = cps_flow_weights.weighted_sources, []

    def spied(selected, scratch):
        scratches.append(Path(scratch))
        assert Path(scratch).is_dir()
        return real(selected, scratch)

    monkeypatch.setattr(cps_flow_weights, 'weighted_sources', spied)
    result = build(built.data_dir, 'scratch', built.request)
    assert scratches == [run_root(built.data_dir) / 'scratch.part' / '.scratch']
    assert not scratches[0].exists()
    assert {path.name for path in Path(result['directory']).iterdir()} == {*FILES, 'outputs.json'}


def write_changed_targets(monkeypatch):
    real = target_contract.write_targets

    def changed(frame, destination):
        return real(frame.with_columns(pl.col('value') + 1), destination)
    monkeypatch.setattr(target_contract, 'write_targets', changed)
    return 'cps_job_flows'


def write_short_diagnostics(monkeypatch):
    real = pl.DataFrame.write_parquet

    def short(frame, file, *args, **kwargs):
        if Path(file).name == 'cps_flow_diagnostics.parquet':
            frame = frame.head(frame.height - 1)
        return real(frame, file, *args, **kwargs)
    monkeypatch.setattr(pl.DataFrame, 'write_parquet', short)
    return 'cps_flow_diagnostics'


@pytest.mark.parametrize('writer', [write_changed_targets, write_short_diagnostics])
def test_build_checks_the_serialized_tables(writer, built, monkeypatch):
    name = writer(monkeypatch)
    with pytest.raises(ValueError, match=f'{name}: serialized table differs'):
        build(built.data_dir, 'serialized', built.request)
    assert no_publication(built.data_dir, 'serialized')


def test_build_refuses_a_stray_staged_file_and_a_final_that_appears(built, monkeypatch):
    real = target_io.write_json

    def stray(file, value):
        real(file, value)
        if file.name == 'report.json':
            (file.parent / 'stray.txt').write_text('stray')

    monkeypatch.setattr(target_io, 'write_json', stray)
    with pytest.raises(ValueError, match='staged bundle files differ from the bundle file set'):
        build(built.data_dir, 'stray', built.request)
    assert no_publication(built.data_dir, 'stray')

    def appearing(file, value):
        real(file, value)
        if file.name == 'outputs.json':
            run_directory(built.data_dir, 'appearing').mkdir()

    monkeypatch.setattr(target_io, 'write_json', appearing)
    with pytest.raises(ValueError, match='final run name already exists'):
        build(built.data_dir, 'appearing', built.request)
    final = run_directory(built.data_dir, 'appearing')
    assert final.is_dir() and not any(final.iterdir())
    assert not (run_root(built.data_dir) / 'appearing.part').exists()
    final.rmdir()


def test_compare_runs_refuses_unpublished_or_uninventoried(built, tmp_path):
    staged = copy_bundle(built, tmp_path, FIRST + '.part')
    with pytest.raises(ValueError, match='compared bundles must be published'):
        compare_runs(built.directory, staged)
    with pytest.raises(ValueError, match='compared bundles must be published'):
        compare_runs(tmp_path / 'absent', built.directory)
    missing = copy_bundle(built, tmp_path / 'missing')
    (missing / 'cps_flow_support.parquet').unlink()
    with pytest.raises(ValueError, match='missing or extra inventory files'):
        compare_runs(built.directory, missing)


def test_compare_runs_reports_a_report_difference(built, tmp_path):
    directory = copy_bundle(built, tmp_path)
    edit_json(directory, 'report.json', set_path('weights', 'zero', 2))
    result = compare_runs(built.directory, directory)
    assert result['report_equal'] is False
    assert result['equal'] is False
    assert all(comparison['values_equal'] for comparison in result['tables'].values())


def test_ordered_equal_counts_a_null_against_a_value_order_and_dtype():
    first = pl.LazyFrame({'a': [1, None], 'b': ['x', 'y']})
    assert cps_flow_bundle.ordered_equal(first, first) == {
        'schema_equal': True, 'values_equal': True, 'first_rows': 2, 'second_rows': 2}
    filled = pl.LazyFrame({'a': [1, 2], 'b': ['x', 'y']})
    for one, other in ((first, filled), (filled, first)):
        assert cps_flow_bundle.ordered_equal(one, other)['values_equal'] is False
    reordered = pl.LazyFrame({'a': [None, 1], 'b': ['y', 'x']})
    assert cps_flow_bundle.ordered_equal(first, reordered)['values_equal'] is False
    narrower = first.with_columns(pl.col('a').cast(pl.Int32))
    swapped = first.select('b', 'a')
    for other in (narrower, swapped):
        assert cps_flow_bundle.ordered_equal(first, other) == {
            'schema_equal': False, 'values_equal': False, 'first_rows': 2, 'second_rows': 2}
    assert cps_flow_bundle.ordered_equal(first, first.head(1)) == {
        'schema_equal': True, 'values_equal': False, 'first_rows': 2, 'second_rows': 1}


def fake_git(status: str, calls: list):
    def check_output(args, cwd, text):
        calls.append((tuple(args), cwd, text))
        return {'rev-parse': 'abc123\n', 'status': status}[args[1]]
    return check_output


@pytest.mark.parametrize('status, dirty', [('', False), (' M src/x.py\n', True)])
def test_execution_records_the_commit_and_whether_the_checkout_is_dirty(status, dirty,
                                                                       monkeypatch):
    calls = []
    monkeypatch.setattr(cps_flow_bundle.subprocess, 'check_output', fake_git(status, calls))
    execution = cps_flow_bundle._execution()
    assert execution['commit'] == 'abc123'
    assert execution['dirty'] is dirty
    assert datetime.fromisoformat(execution['created_at']).tzinfo is not None
    assert calls == [
        (('git', 'rev-parse', 'HEAD'), paths.PROJECT_ROOT, True),
        (('git', 'status', '--porcelain', '--untracked-files=normal'), paths.PROJECT_ROOT, True)]
