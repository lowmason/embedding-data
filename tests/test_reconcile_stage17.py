'''The independent Stage 17 reconciler, on the fixture chain and on small typed rows.'''

import ast
import importlib.util
import json
import math
import operator
import os
import shutil
import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest
from acs_mapping_fixtures import forbid_external_access
from acs_wage_fixtures import copy_template, core_frame, core_row, wage_mapping

from embedding_data import acs_wage_bundle, manifest, target_io
from embedding_data.acs_wage_bundle import FILES

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'reconcile_stage17.py'
PERSONS = 'acs_wage_persons.parquet'
HEADLINE_Q = ('QINCWAGE', 'QIND', 'QOCC', 'QUHRSWOR', 'QWKSWORK2', 'QAGE', 'QSEX', 'QEDUC',
              'QCLASSWK')
NEW = ('log_wage_2010', 'industry_node_code', 'industry_node_level',
       'industry_delivered_node_code', 'flag_industry_shared_node', 'flag_any_allocated',
       'flag_incwage_topcoded', 'flag_full_time_full_year', 'flag_wage_salary', 'flag_headline')
ROWS_DIFFER = 'person rows differ from the Stage 8 earners'
SCHEMA_DIFFERS = 'person table schema differs from the contract'
MALFORMED = 'recorded inputs are malformed'


def load_script():
    assert SCRIPT.is_file(), 'independent reconciler is missing'
    spec = importlib.util.spec_from_file_location('reconcile_stage17', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def template(tmp_path_factory):
    '''One chain with one published build named `first`, shared by the module's tests.'''
    with pytest.MonkeyPatch.context() as patches:
        forbid_external_access(patches)
        chain = wage_mapping(tmp_path_factory.mktemp('reconcile-stage17'), patches)
        built = acs_wage_bundle.build(
            chain['data_dir'], 'first', mapping_run=chain['mapping_run'],
            mapping_outputs_sha256=chain['mapping_outputs_sha256'], codes_run=chain['codes_run'],
            codes_outputs_sha256=chain['codes_outputs_sha256'])
    return chain | {'first_pin': built['outputs_sha256']}


@pytest.fixture
def chain_build(template, tmp_path):
    '''Task 4's chain plus one build named `first`, copied so that a test can forge it.'''
    return copy_template(template, tmp_path)


@pytest.fixture
def script():
    return load_script()


def bundle(chain):
    return chain['data_dir'] / 'derived/acs/wage-microdata/first'


def mapping_directory(chain):
    return chain['data_dir'] / 'derived/acs/mapping' / chain['mapping_run']


def codes_directory(chain):
    return chain['data_dir'] / 'derived/codes' / chain['codes_run']


def run_script(chain, pin=None, run='first'):
    '''Run `reconcile` in a subprocess. Return its exit status and its one JSON line, parsed.'''
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), 'reconcile', '--data-dir', str(chain['data_dir']),
         '--run', run, '--outputs-sha256', pin or chain['first_pin']],
        cwd=ROOT, capture_output=True, text=True, check=False)
    assert completed.stderr == ''
    lines = completed.stdout.splitlines()
    assert len(lines) == 1
    result = json.loads(lines[0])
    assert lines[0] == json.dumps(result, sort_keys=True)
    return completed.returncode, result


def run_main(script, capsys, chain, pin=None, run='first'):
    '''Run `reconcile` through the loaded script's `main`. Return its status and its line.'''
    status = script.main(['reconcile', '--data-dir', str(chain['data_dir']), '--run', run,
                          '--outputs-sha256', pin or chain['first_pin']])
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    result = json.loads(lines[0])
    assert lines[0] == json.dumps(result, sort_keys=True)
    return status, result


def refused(reason, run='first'):
    return {'check': 'persons', 'run': run, 'equal': False, 'reason': reason}


def rehash(directory):
    '''Rewrite a bundle's inventory after an edit, and return the new detached pin.'''
    target_io.write_json(directory / 'outputs.json', target_io.inventory(directory, list(FILES)))
    return manifest.sha256_file(directory / 'outputs.json')


def forge_persons(chain, change):
    '''Rewrite the person table through `change`, then the inventory. Return the new pin.'''
    file = bundle(chain) / PERSONS
    change(pl.read_parquet(file)).write_parquet(file)
    return rehash(bundle(chain))


def edit_json(file, change):
    value = json.loads(file.read_text())
    change(value)
    target_io.write_json(file, value)


def forge_json(chain, name, change):
    '''Rewrite one bundle JSON file through `change`, then the inventory. Return the new pin.'''
    edit_json(bundle(chain) / name, change)
    return rehash(bundle(chain))


def update(column, function, rows=(0,)):
    '''A change that applies `function` to one column at the given row positions.'''
    def change(frame):
        values = frame[column].to_list()
        for position in rows:
            values[position] = function(values[position])
        return frame.with_columns(pl.Series(column, values, dtype=frame.schema[column]))
    return change


def forge_upstream(chain, directory, table, change, field):
    '''Rewrite one upstream table, its inventory record and the bundle's recorded pin for it.

    `field` is the `inputs.json` field that records the upstream run (`mapping` or `codes`).
    Return the bundle's new detached pin.
    '''
    file = directory / table
    change(pl.read_parquet(file)).write_parquet(file)
    outputs = json.loads((directory / 'outputs.json').read_text())
    outputs[table].update(sha256=manifest.sha256_file(file), size=file.stat().st_size)
    target_io.write_json(directory / 'outputs.json', outputs)
    pin = manifest.sha256_file(directory / 'outputs.json')
    return forge_json(chain, 'inputs.json',
                      lambda inputs: inputs[field].update(outputs_sha256=pin, outputs=outputs))


def plus_one(value):
    return value + 1


def append_byte(file):
    file.write_bytes(file.read_bytes() + b'\0')


# The plan's tests.

def test_reconciler_imports_no_embedding_data_module():
    tree = ast.parse(SCRIPT.read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or '')
            imported.update(f'{node.module}.{alias.name}' for alias in node.names)
    assert imported
    assert not {name for name in imported if name.split('.')[0] == 'embedding_data'}


def test_reconcile_reports_equal_on_a_fixture_build(chain_build):
    status, result = run_script(chain_build)
    persons = pl.read_parquet(bundle(chain_build) / PERSONS)
    assert status == 0
    assert result == {'check': 'persons', 'run': 'first', 'equal': True, 'rows': persons.height,
                      'headline_rows': persons['flag_headline'].sum(), 'mismatches': {}}
    assert 0 < result['headline_rows'] < result['rows']


def test_reconcile_counts_a_changed_carried_value(chain_build):
    # forged bundle: one AGE changed, inventory and pin rewritten
    pin = forge_persons(chain_build, update('AGE', plus_one))
    status, result = run_script(chain_build, pin)
    assert status == 1
    assert result['equal'] is False and result['mismatches'] == {'AGE': 1}


def test_reconcile_counts_a_changed_flag(chain_build):
    # The first row is not a headline row; the forgery marks it as one.
    pin = forge_persons(chain_build, update('flag_headline', operator.not_))
    status, result = run_script(chain_build, pin)
    assert status == 1
    assert result['equal'] is False and result['mismatches'] == {'flag_headline': 1}


def test_reconcile_refuses_a_wrong_pin(chain_build):
    status, result = run_script(chain_build, '0' * 64)
    assert status == 1
    assert result == refused('detached pin differs')


def drop_last_row(frame):
    return frame.head(frame.height - 1)


def extra_row(frame):
    '''One more row after the last, still in increasing source order.'''
    return pl.concat([frame, frame.tail(1).with_columns(pl.col('source_row') + 1)])


@pytest.mark.parametrize('change', [drop_last_row, extra_row], ids=['missing', 'extra'])
def test_reconcile_refuses_a_missing_or_extra_row(chain_build, change):
    pin = forge_persons(chain_build, change)
    status, result = run_script(chain_build, pin)
    assert status == 1
    assert result == refused(ROWS_DIFFER)


# Additional coverage beyond the plan tests.

def test_reconciler_imports_only_the_standard_library_and_polars():
    tree = ast.parse(SCRIPT.read_text())
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            roots.add(node.module.split('.')[0])
    assert 'polars' in roots
    assert roots <= set(sys.stdlib_module_names) | {'polars'}


def test_reconcile_loads_no_embedding_data_module_while_it_runs(chain_build):
    code = '\n'.join([
        'import importlib.util, json, sys',
        'spec = importlib.util.spec_from_file_location("reconcile_stage17", sys.argv[1])',
        'module = importlib.util.module_from_spec(spec)',
        'spec.loader.exec_module(module)',
        'status = module.main(sys.argv[2:])',
        'print(json.dumps(sorted(sys.modules)))',
    ])
    completed = subprocess.run(
        [sys.executable, '-c', code, str(SCRIPT), 'reconcile', '--data-dir',
         str(chain_build['data_dir']), '--run', 'first', '--outputs-sha256',
         chain_build['first_pin']], cwd=ROOT, capture_output=True, text=True, check=True)
    result, modules = completed.stdout.splitlines()
    assert json.loads(result)['equal'] is True
    assert not [name for name in json.loads(modules)
                if name.split('.')[0] in {'embedding_data', 'dotenv', 'ipumspy'}]


def test_script_exit_status_follows_equal_on_an_unequal_result(chain_build):
    pin = forge_persons(chain_build, update('SEX', plus_one))
    status, result = run_script(chain_build, pin)
    assert (status, result['equal'], result['mismatches']) == (1, False, {'SEX': 1})


CARRIED_CASES = {
    'first_column': ('source_parquet_sha256', lambda value: 'b' * 64),
    'weight': ('REPWTP40', plus_one),
    'float': ('INCWAGE_CPIU_2010', lambda value: value + 0.5),
    'list': ('industry_canonical_finest_candidates', lambda value: [*value, '999999']),
    'native_node': ('industry_native_node_id', lambda value: value + 'x'),
    'last_column': ('QDEGFIELD', plus_one),
}


@pytest.mark.parametrize('case', CARRIED_CASES)
def test_reconcile_counts_a_changed_value_in_every_carried_group(script, capsys, chain_build,
                                                                 case):
    column, function = CARRIED_CASES[case]
    pin = forge_persons(chain_build, update(column, function))
    status, result = run_main(script, capsys, chain_build, pin)
    assert (status, result['equal'], result['mismatches']) == (1, False, {column: 1})


NEW_CASES = {
    'log_wage_2010': (lambda value: value + 0.5, {}),
    'industry_node_code': (lambda value: 'x', {'unknown_node': 1}),
    'industry_node_level': (lambda value: 'x', {}),
    # Sector 11 is an ancestor of the first row's node 113, but it has several children.
    'industry_delivered_node_code': (lambda value: '11', {'delivered_node_chain': 1}),
    **{name: (operator.not_, {}) for name in NEW if name.startswith('flag_')},
}


@pytest.mark.parametrize('column', NEW_CASES)
def test_reconcile_counts_a_changed_new_column(script, capsys, chain_build, column):
    function, node_checks = NEW_CASES[column]
    pin = forge_persons(chain_build, update(column, function))
    status, result = run_main(script, capsys, chain_build, pin)
    assert (status, result['equal']) == (1, False)
    assert result['mismatches'] == {column: 1, **node_checks}


def test_reconcile_counts_mismatches_per_column(script, capsys, chain_build):
    def change(frame):
        return update('SEX', plus_one)(update('AGE', plus_one, rows=(0, 1))(frame))

    pin = forge_persons(chain_build, change)
    status, result = run_main(script, capsys, chain_build, pin)
    assert (status, result['mismatches']) == (1, {'AGE': 2, 'SEX': 1})


def test_reconcile_compares_at_most_twenty_columns_at_a_time(script, capsys, chain_build,
                                                            monkeypatch):
    compared = []
    original = script.differences

    def recording(first, second, names):
        compared.append(tuple(names))
        return original(first, second, names)

    monkeypatch.setattr(script, 'differences', recording)
    status, result = run_main(script, capsys, chain_build)
    assert (status, result['equal']) == (0, True)
    columns = pl.scan_parquet(bundle(chain_build) / PERSONS).collect_schema().names()
    assert sorted(name for names in compared for name in names) == sorted(
        name for name in columns if name != 'source_row')
    assert max(len(names) for names in compared) <= 20


def raise_middle_step_2023(report):
    step = report['funnel'][2]
    assert step['step'] == 'full_time_full_year'
    step['by_year']['2023'] += 1


def raise_headline_total(report):
    step = report['funnel'][-1]
    assert step['step'] == 'headline'
    step['total'] += 1


def drop_last_step(report):
    report['funnel'].pop()


@pytest.mark.parametrize('change', [raise_middle_step_2023, raise_headline_total,
                                    drop_last_step], ids=['by_year', 'total', 'dropped_step'])
def test_reconcile_compares_the_funnel_with_the_report(script, capsys, chain_build, change):
    pin = forge_json(chain_build, 'report.json', change)
    status, result = run_main(script, capsys, chain_build, pin)
    assert (status, result['equal'], result['mismatches']) == (1, False, {'funnel': 1})


def test_a_subcommand_is_required(script):
    with pytest.raises(SystemExit) as exit_info:
        script.main([])
    assert exit_info.value.code == 2


def test_reconcile_counts_a_node_missing_from_the_stage4_table(script, capsys, chain_build):
    # Only the control row at AGE 49 joins at node 811192.
    pin = forge_upstream(chain_build, codes_directory(chain_build), 'naics_nodes.parquet',
                         lambda nodes: nodes.filter(pl.col('code') != '811192'), 'codes')
    status, result = run_main(script, capsys, chain_build, pin)
    assert (status, result['equal'], result['mismatches']) == (1, False, {'unknown_node': 1})


SCHEMA_CASES = {
    'carried_type': lambda frame: frame.with_columns(pl.col('AGE').cast(pl.Int32)),
    'new_type': lambda frame: frame.with_columns(pl.col('log_wage_2010').cast(pl.Float32)),
    'missing': lambda frame: frame.drop('GQ'),
    'extra': lambda frame: frame.with_columns(pl.lit(1).alias('extra')),
    'order': lambda frame: frame.select(frame.columns[1], frame.columns[0], *frame.columns[2:]),
}


@pytest.mark.parametrize('case', SCHEMA_CASES)
def test_reconcile_refuses_a_schema_other_than_the_contract(script, capsys, chain_build, case):
    pin = forge_persons(chain_build, SCHEMA_CASES[case])
    status, result = run_main(script, capsys, chain_build, pin)
    assert (status, result) == (1, refused(SCHEMA_DIFFERS))


def repeat_first_row(frame):
    '''The first row twice and the last row missing: the row count is unchanged.'''
    return pl.concat([frame.head(1), frame.head(frame.height - 1)])


def swap_first_rows(frame):
    return pl.concat([frame.slice(1, 1), frame.head(1), frame.slice(2)])


def duplicate_last_row(frame):
    return pl.concat([frame, frame.tail(1)])


@pytest.mark.parametrize('change', [repeat_first_row, swap_first_rows, duplicate_last_row],
                         ids=['repeated', 'swapped', 'duplicated'])
def test_reconcile_refuses_reordered_or_repeated_rows(script, capsys, chain_build, change):
    # Each keeps the set of source rows or the row count, so only an ordered check refuses.
    pin = forge_persons(chain_build, change)
    status, result = run_main(script, capsys, chain_build, pin)
    assert (status, result) == (1, refused(ROWS_DIFFER))


def test_reconcile_refuses_a_stage8_source_row_that_is_not_unique(script, capsys, chain_build):
    # Stage 8 and the bundle carry the same repeated key, so only a one-to-one check refuses.
    def repeat_key(frame):
        return update('source_row', lambda value: 0, rows=(1,))(frame)

    forge_upstream(chain_build, mapping_directory(chain_build), 'acs_core_canonical.parquet',
                   repeat_key, 'mapping')
    pin = forge_persons(chain_build, repeat_key)
    status, result = run_main(script, capsys, chain_build, pin)
    assert (status, result) == (1, refused(ROWS_DIFFER))


@pytest.mark.parametrize('name', [PERSONS, 'inputs.json', 'report.json'])
def test_reconcile_checks_the_pin_before_any_bundle_file(script, capsys, chain_build, name):
    (bundle(chain_build) / name).write_bytes(b'garbled')
    status, result = run_main(script, capsys, chain_build, '0' * 64)
    assert (status, result) == (1, refused('detached pin differs'))


@pytest.mark.parametrize('name', [PERSONS, 'inputs.json', 'report.json'])
def test_reconcile_refuses_a_bundle_file_that_differs_from_its_inventory(script, capsys,
                                                                       chain_build, name):
    append_byte(bundle(chain_build) / name)
    status, result = run_main(script, capsys, chain_build)
    assert (status, result) == (1, refused('bundle file differs from its inventory'))


def wrong_pin(field):
    def change(inputs):
        inputs[field]['outputs_sha256'] = '0' * 64
    return change


@pytest.mark.parametrize(('field', 'reason'), [('mapping', 'Stage 8 pin differs'),
                                               ('codes', 'Stage 4 pin differs')])
def test_reconcile_refuses_a_recorded_upstream_pin_that_differs(script, capsys, chain_build,
                                                                field, reason):
    pin = forge_json(chain_build, 'inputs.json', wrong_pin(field))
    status, result = run_main(script, capsys, chain_build, pin)
    assert (status, result) == (1, refused(reason))


@pytest.mark.parametrize(('upstream', 'table', 'reason'), [
    (mapping_directory, 'acs_core_canonical.parquet',
     'Stage 8 core table differs from its inventory'),
    (codes_directory, 'naics_nodes.parquet', 'Stage 4 table differs from its inventory'),
    (codes_directory, 'naics_edges.parquet', 'Stage 4 table differs from its inventory'),
], ids=['core', 'nodes', 'edges'])
def test_reconcile_refuses_an_upstream_table_that_differs_from_its_record(
        script, capsys, chain_build, upstream, table, reason):
    append_byte(upstream(chain_build) / table)
    status, result = run_main(script, capsys, chain_build)
    assert (status, result) == (1, refused(reason))


RECORDED_CASES = {
    'no_codes': lambda inputs: inputs.pop('codes'),
    'codes_not_an_object': lambda inputs: inputs.update(codes='stage4'),
    'no_mapping_pin': lambda inputs: inputs['mapping'].pop('outputs_sha256'),
    # Both resolve to the recorded runs' own directories, so only the run ID check refuses.
    'unsafe_mapping_run': lambda inputs: inputs['mapping'].update(run_id='../mapping/mapping'),
    'unsafe_codes_run': lambda inputs: inputs['codes'].update(
        run_id='../codes/' + inputs['codes']['run_id']),
}


@pytest.mark.parametrize('case', RECORDED_CASES)
def test_reconcile_refuses_malformed_recorded_inputs(script, capsys, chain_build, case):
    pin = forge_json(chain_build, 'inputs.json', RECORDED_CASES[case])
    status, result = run_main(script, capsys, chain_build, pin)
    assert (status, result) == (1, refused(MALFORMED))


def test_reconcile_refuses_an_unsafe_run_id(script, capsys, chain_build):
    # The path resolves to the published run, so only the run ID check refuses.
    run = '../wage-microdata/first'
    status, result = run_main(script, capsys, chain_build, run=run)
    assert (status, result) == (1, refused('unsafe run ID', run=run))


def test_reconcile_prints_a_fixed_reason_for_an_unreadable_input(chain_build):
    # The garbled table keeps a matching inventory record, so the read itself fails.
    file = bundle(chain_build) / PERSONS
    file.write_bytes(b'not a parquet file')
    edit_json(bundle(chain_build) / 'outputs.json', lambda outputs: outputs[PERSONS].update(
        sha256=manifest.sha256_file(file), size=file.stat().st_size))
    pin = manifest.sha256_file(bundle(chain_build) / 'outputs.json')
    status, result = run_script(chain_build, pin)
    assert (status, result) == (1, refused('reconciliation failed'))


# The recomputation on small typed Stage 8 rows.

def derived(script, rows):
    return script.derive(core_frame(rows)).collect()


FLAG_CASES = {
    'employee': ({}, {'flag_any_allocated': False, 'flag_full_time_full_year': True,
                      'flag_wage_salary': True, 'flag_headline': True}),
    'hours_34': ({'UHRSWORK': 34}, {'flag_full_time_full_year': False, 'flag_headline': False}),
    'hours_35': ({'UHRSWORK': 35}, {'flag_full_time_full_year': True, 'flag_headline': True}),
    'weeks_5': ({'WKSWORK2': 5}, {'flag_full_time_full_year': False, 'flag_headline': False}),
    **{f'class_{code}': ({'CLASSWKRD': code}, {'flag_wage_salary': True, 'flag_headline': True})
       for code in (22, 23, 25, 27, 28)},
    **{f'class_{code}': ({'CLASSWKRD': code}, {'flag_wage_salary': False,
                                               'flag_headline': False})
       for code in (13, 14, 29)},
    **{f'{name}_allocated': ({name: 4}, {'flag_any_allocated': True, 'flag_headline': False})
       for name in HEADLINE_Q},
    'QDEGFIELD_allocated': ({'QDEGFIELD': 4}, {'flag_any_allocated': True,
                                               'flag_headline': True}),
    # Any value other than 0 is allocated, not only 4.
    'QUHRSWOR_code_3': ({'QUHRSWOR': 3}, {'flag_any_allocated': True, 'flag_headline': False}),
    'QDEGFIELD_code_1': ({'QDEGFIELD': 1}, {'flag_any_allocated': True, 'flag_headline': True}),
}


@pytest.mark.parametrize('case', FLAG_CASES)
def test_flags_follow_the_rules(script, case):
    changes, expected = FLAG_CASES[case]
    assert derived(script, [core_row(**changes)]).select(list(expected)).to_dicts() == [expected]


def test_rows_are_the_earners_in_source_order(script):
    rows = [core_row(INCWAGE=wage) for wage in (5, 0, -1, None, 7)]
    assert derived(script, rows)['source_row'].to_list() == [0, 4]


def test_the_highest_wage_of_each_state_and_year_is_top_coded(script):
    cells = [(1, 2023, 100), (1, 2023, 200), (1, 2023, 200), (2, 2023, 150), (1, 2024, 50),
             (1, 2024, 100), (2, 2024, 0)]
    rows = [core_row(STATEFIP=state, YEAR=year, INCWAGE=wage) for state, year, wage in cells]
    assert derived(script, rows)['flag_incwage_topcoded'].to_list() == [
        False, True, True, True, False, True]


def test_a_node_is_shared_when_another_earner_category_has_it(script):
    cells = [('A', 'n1', 1), ('B', 'n1', 1), ('C', 'n2', 1), ('C', 'n2', 1), ('D', 'n2', 0),
             ('E', 'n3', 1)]
    rows = [core_row(INDNAICS=category, industry_canonical_common_node_id=f'naics:2022:x:{node}',
                     INCWAGE=wage) for category, node, wage in cells]
    frame = derived(script, rows)
    assert frame['flag_industry_shared_node'].to_list() == [True, True, False, False, False]
    assert frame['flag_headline'].to_list() == [False, False, True, True, True]


def test_a_node_is_shared_across_the_years_of_the_file(script):
    # The file's rows pool both years. Only the top code reads state and year.
    node = {'industry_canonical_common_node_id': 'naics:2022:x:n1'}
    rows = [core_row(INDNAICS='A', **node), core_row(INDNAICS='B', YEAR=2024, **node)]
    assert derived(script, rows)['flag_industry_shared_node'].to_list() == [True, True]


def test_node_codes_and_level_are_the_parts_of_the_ids(script):
    rows = [
        core_row(industry_canonical_common_node_id='naics:2022:sector:31-33',
                 industry_native_node_id='naics:2022:sector:31-33'),
        core_row(industry_canonical_common_node_id='naics:2022:national_industry:623110',
                 industry_native_node_id='naics:2022:industry_group:6231'),
    ]
    columns = ['industry_node_code', 'industry_node_level', 'industry_delivered_node_code']
    assert derived(script, rows).select(columns).rows() == [
        ('31-33', 'sector', '31-33'), ('623110', 'national_industry', '6231')]


def test_log_wage_is_the_natural_log_as_float64(script):
    values = [40000.0, 12345.5]
    frame = derived(script, [core_row(INCWAGE_CPIU_2010=value) for value in values])
    assert frame.schema['log_wage_2010'] == pl.Float64
    assert frame['log_wage_2010'].to_list() == [math.log(value) for value in values]


def test_funnel_steps_are_cumulative_and_list_every_year(script):
    shared = {'industry_canonical_common_node_id': 'naics:2022:x:n2'}
    rows = [
        core_row(),
        core_row(QINCWAGE=4),
        core_row(QDEGFIELD=4),
        core_row(UHRSWORK=30),
        core_row(CLASSWKRD=14),
        core_row(INDNAICS='B', **shared),
        core_row(INDNAICS='C', **shared),
        core_row(YEAR=2024, QIND=4),
    ]

    def step(name, first, second):
        return {'step': name, 'total': first + second,
                'by_year': {'2023': first, '2024': second}}

    assert script.funnel(script.derive(core_frame(rows))) == [
        step('earners', 7, 1),
        step('no_headline_allocation', 6, 0),
        step('full_time_full_year', 5, 0),
        step('wage_salary', 4, 0),
        step('headline', 2, 0),
    ]


# The spec item 6 node checks on a small forest. A non-hierarchy edge from A2 to A11 and a
# 2017 node V must be ignored.
FOREST = {'A1': 'A', 'A2': 'A', 'A11': 'A1', 'A111': 'A11', 'A1111': 'A111', 'A1112': 'A111',
          'B1': 'B', 'B11': 'B1', 'B12': 'B1', 'B111': 'B11'}
NODE_CASES = {
    'itself': ('A111', 'A111', None),
    'parent': ('A111', 'A11', None),
    'branching_join_node': ('A111', 'A1', None),
    'branching_delivered_node': ('A111', 'A', 'delivered_node_chain'),
    'branching_intermediate_node': ('B111', 'B', 'delivered_node_chain'),
    'single_child_parent': ('B111', 'B11', None),
    'delivered_below_the_join_node': ('A11', 'A111', 'delivered_node_chain'),
    'sibling': ('A1111', 'A1112', 'delivered_node_chain'),
    'unrelated': ('A111', 'B', 'delivered_node_chain'),
    'unknown_join_code': ('Z', 'A', 'unknown_node'),
    'unknown_delivered_code': ('A', 'Z', 'unknown_node'),
    'other_vintage': ('V', 'V', 'unknown_node'),
    'null': (None, None, 'unknown_node'),
}


def forest():
    codes = sorted({*FOREST, *FOREST.values()})
    node = 'naics:2022:x:{}'.format
    nodes = pl.DataFrame({
        'node_id': [node(code) for code in codes] + ['naics:2017:x:V'],
        'system': ['naics'] * (len(codes) + 1),
        'vintage': [2022] * len(codes) + [2017],
        'level': ['x'] * (len(codes) + 1),
        'code': [*codes, 'V'],
    })
    pairs = [*FOREST.items(), ('A2', 'A11')]
    edges = pl.DataFrame({
        'child_id': [node(child) for child, _ in pairs],
        'parent_id': [node(parent) for _, parent in pairs],
        'edge_type': ['hierarchy'] * len(FOREST) + ['crosswalk'],
    })
    return nodes, edges


@pytest.mark.parametrize('case', NODE_CASES)
def test_node_checks_follow_spec_item_6(script, case):
    code, delivered, failure = NODE_CASES[case]
    expected = {'unknown_node': 0, 'delivered_node_chain': 0}
    if failure:
        expected[failure] = 3
    assert script.node_failures([(code, delivered, 3)], *forest()) == expected


def test_node_checks_count_rows_over_every_pair(script):
    pairs = [('A111', 'A1', 2), ('A111', 'A', 3), ('Z', 'A', 4), ('B111', 'B', 5)]
    assert script.node_failures(pairs, *forest()) == {'unknown_node': 4,
                                                      'delivered_node_chain': 8}


# The preservation controls (spec item 7): `freeze` and `preservation`.

CONTROL_ROOT = 'derived/acs/wage-microdata-controls'
WAGE_RUNS = 'derived/acs/wage-microdata'
STAGE8_CORE = 'derived/acs/mapping/mapping/acs_core_canonical.parquet'
MANIFEST = 'raw/manifest.jsonl'
RUNS = 'first,replay'
UNSAFE_CONTROL = 'unsafe control directory'
CONTROL_EXISTS = 'control directory exists'
WRONG_TREES = 'raw or derived is not a directory'
PIN_DIFFERS = 'freeze pin differs'


@pytest.fixture
def chain(template, tmp_path):
    '''The fixture chain before any build, copied so that a test can freeze and change it.'''
    copied = copy_template(template, tmp_path)
    shutil.rmtree(copied['data_dir'] / WAGE_RUNS)
    return copied


@pytest.fixture(scope='module')
def frozen_template(template, tmp_path_factory):
    '''The chain frozen before any build, then built twice into the runs `first` and `replay`.'''
    copied = copy_template(template, tmp_path_factory.mktemp('stage17-preservation'))
    data_dir = copied['data_dir']
    shutil.rmtree(data_dir / WAGE_RUNS)
    status, frozen = run_freeze(data_dir)
    assert status == 0
    with pytest.MonkeyPatch.context() as patches:
        forbid_external_access(patches)
        for run in ('first', 'replay'):
            acs_wage_bundle.build(
                data_dir, run, mapping_run=copied['mapping_run'],
                mapping_outputs_sha256=copied['mapping_outputs_sha256'],
                codes_run=copied['codes_run'],
                codes_outputs_sha256=copied['codes_outputs_sha256'])
    return copied | {'freeze_pin': frozen['freeze_sha256'], 'freeze_files': frozen['files']}


@pytest.fixture
def frozen(frozen_template, tmp_path):
    '''The frozen and built chain, copied so that a test can damage it.'''
    return copy_template(frozen_template, tmp_path)


def run_control(command, data_dir, *arguments):
    '''Run a preservation subcommand in a subprocess. Return its status and its one JSON line.'''
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), command, '--data-dir', str(data_dir), *arguments],
        cwd=ROOT, capture_output=True, text=True, check=False)
    assert completed.stderr == ''
    lines = completed.stdout.splitlines()
    assert len(lines) == 1
    result = json.loads(lines[0])
    assert lines[0] == json.dumps(result, sort_keys=True)
    return completed.returncode, result


def control_dir(data_dir, name='first'):
    return data_dir / CONTROL_ROOT / name


def run_freeze(data_dir, control=None):
    return run_control('freeze', data_dir, '--control-dir',
                       str(control or control_dir(data_dir)))


def run_preservation(data_dir, pin, runs=RUNS, control=None):
    return run_control('preservation', data_dir, '--control-dir',
                       str(control or control_dir(data_dir)), '--freeze-sha256', pin, '--runs',
                       runs)


def control_refusal(command, reason):
    return {'check': command, 'reason': reason, 'status': 'refused'}


def checked(**changes):
    '''A clean result on the frozen chain after its two builds, with some fields changed.'''
    return {'status': 'preserved', 'changed': [], 'missing': [], 'added': [],
            'manifest_equal': True, 'runs': ['first', 'replay']} | changes


def tree(data_dir):
    '''Every path under the data directory, files and directories, without any content.'''
    return sorted(path.relative_to(data_dir).as_posix() for path in data_dir.rglob('*'))


def frozen_files(data_dir):
    '''Every regular file under raw and derived but the manifest and the two stage trees.'''
    skipped = (data_dir / WAGE_RUNS, data_dir / CONTROL_ROOT)
    return {
        path.relative_to(data_dir).as_posix():
            {'sha256': manifest.sha256_file(path), 'size': path.stat().st_size}
        for tree_name in ('raw', 'derived') for path in sorted((data_dir / tree_name).rglob('*'))
        if path.is_file() and path != data_dir / MANIFEST
        and not any(path.is_relative_to(tree_path) for tree_path in skipped)
    }


def flip_a_byte(file):
    '''Change one byte in the middle of a file and keep its size.'''
    content = bytearray(file.read_bytes())
    content[len(content) // 2] ^= 1
    file.write_bytes(content)


def a_raw_file(data_dir):
    '''The first raw file by path, other than the manifest.'''
    return min(path.relative_to(data_dir).as_posix() for path in (data_dir / 'raw').rglob('*')
               if path.is_file() and path.name != 'manifest.jsonl')


def change_stage8_byte(data_dir):
    flip_a_byte(data_dir / STAGE8_CORE)
    return {'changed': [STAGE8_CORE]}


def add_stray_derived_file(data_dir):
    # The name starts like the run tree's, so a prefix test on the name would skip it.
    stray = 'derived/acs/wage-microdata-extra.txt'
    (data_dir / stray).write_text('stray')
    return {'added': [stray]}


def append_manifest_line(data_dir):
    with (data_dir / MANIFEST).open('a') as stream:
        stream.write('{}\n')
    return {'manifest_equal': False}


def leave_part_directory(data_dir):
    (data_dir / WAGE_RUNS / 'replay2.part').mkdir()
    return {'added': [f'{WAGE_RUNS}/replay2.part'], 'runs': ['first', 'replay', 'replay2.part']}


def remove_raw_file(data_dir):
    path = a_raw_file(data_dir)
    (data_dir / path).unlink()
    return {'missing': [path]}


def change_raw_byte(data_dir):
    path = a_raw_file(data_dir)
    flip_a_byte(data_dir / path)
    return {'changed': [path]}


def grow_a_derived_file(data_dir):
    file = data_dir / STAGE8_CORE
    file.write_bytes(file.read_bytes() + b'\0')
    return {'changed': [STAGE8_CORE]}


def add_stray_raw_file(data_dir):
    (data_dir / 'raw' / 'stray.txt').write_text('stray')
    return {'added': ['raw/stray.txt']}


def remove_derived_file(data_dir):
    (data_dir / STAGE8_CORE).unlink()
    return {'missing': [STAGE8_CORE]}


def rewrite_manifest_with_the_same_size(data_dir):
    flip_a_byte(data_dir / MANIFEST)
    return {'manifest_equal': False}


def remove_manifest(data_dir):
    (data_dir / MANIFEST).unlink()
    return {'manifest_equal': False}


def add_an_unnamed_run(data_dir):
    (data_dir / WAGE_RUNS / 'third').mkdir()
    return {'added': [f'{WAGE_RUNS}/third'], 'runs': ['first', 'replay', 'third']}


def add_a_stray_file_among_the_runs(data_dir):
    (data_dir / WAGE_RUNS / 'notes.txt').write_text('stray')
    return {'added': [f'{WAGE_RUNS}/notes.txt'], 'runs': ['first', 'notes.txt', 'replay']}


def remove_a_named_run(data_dir):
    shutil.rmtree(data_dir / WAGE_RUNS / 'replay')
    return {'missing': [f'{WAGE_RUNS}/replay'], 'runs': ['first']}


def change_stage4_byte(data_dir):
    path = min(path.relative_to(data_dir).as_posix()
               for path in (data_dir / 'derived/codes').rglob('*.parquet'))
    flip_a_byte(data_dir / path)
    return {'changed': [path]}


def change_add_and_remove_many(data_dir):
    # A file and a run in each list: the lists are sorted over files and runs together.
    removed = a_raw_file(data_dir)
    (data_dir / removed).unlink()
    shutil.rmtree(data_dir / WAGE_RUNS / 'replay')
    (data_dir / WAGE_RUNS / 'third').mkdir()
    (data_dir / 'raw' / 'stray.txt').write_text('stray')
    flip_a_byte(data_dir / STAGE8_CORE)
    return {'changed': [STAGE8_CORE], 'added': [f'{WAGE_RUNS}/third', 'raw/stray.txt'],
            'missing': [f'{WAGE_RUNS}/replay', removed], 'runs': ['first', 'third']}


def test_preserved_after_a_fixture_build(frozen):
    status, result = run_preservation(frozen['data_dir'], frozen['freeze_pin'])
    assert (status, result) == (0, checked())
    assert frozen['freeze_files'] > 0
    assert sorted(path.name for path in (frozen['data_dir'] / WAGE_RUNS).iterdir()) == [
        'first', 'replay']


@pytest.mark.parametrize('damage', ['change_stage8_byte', 'add_stray_derived_file',
                                    'append_manifest_line', 'leave_part_directory',
                                    'remove_raw_file'])
def test_preservation_reports_each_kind_of_change(frozen, damage):
    expected = {
        'change_stage8_byte': change_stage8_byte,
        'add_stray_derived_file': add_stray_derived_file,
        'append_manifest_line': append_manifest_line,
        'leave_part_directory': leave_part_directory,
        'remove_raw_file': remove_raw_file,
    }[damage](frozen['data_dir'])
    exit_code, result = run_preservation(frozen['data_dir'], frozen['freeze_pin'])
    assert result['status'] == 'changed' and exit_code == 1
    assert result == checked(status='changed', **expected)


OTHER_DAMAGE = {
    function.__name__: function for function in (
        change_raw_byte, change_stage4_byte, grow_a_derived_file, add_stray_raw_file,
        remove_derived_file, rewrite_manifest_with_the_same_size, remove_manifest,
        add_an_unnamed_run, add_a_stray_file_among_the_runs, remove_a_named_run,
        change_add_and_remove_many)
}


@pytest.mark.parametrize('damage', OTHER_DAMAGE)
def test_preservation_reports_every_other_kind_of_change(frozen, damage):
    expected = OTHER_DAMAGE[damage](frozen['data_dir'])
    exit_code, result = run_preservation(frozen['data_dir'], frozen['freeze_pin'])
    assert exit_code == 1
    assert result == checked(status='changed', **expected)


def test_preservation_leaves_the_files_of_the_named_runs_and_the_control_directory_free(frozen):
    data_dir = frozen['data_dir']
    flip_a_byte(data_dir / WAGE_RUNS / 'first' / 'inputs.json')
    (data_dir / WAGE_RUNS / 'replay' / 'extra.bin').write_bytes(b'extra')
    (data_dir / WAGE_RUNS / 'first' / 'nested').mkdir()
    (control_dir(data_dir) / 'notes.txt').write_text('notes')
    (data_dir / CONTROL_ROOT / 'other').mkdir()
    status, result = run_preservation(data_dir, frozen['freeze_pin'])
    assert (status, result) == (0, checked())


@pytest.mark.parametrize(('runs', 'changes'), [
    ('first', {'added': [f'{WAGE_RUNS}/replay']}),
    ('first,replay,third', {'missing': [f'{WAGE_RUNS}/third']}),
    ('replay,first', {}),
], ids=['an_unnamed_run', 'an_absent_named_run', 'any_order'])
def test_preservation_needs_exactly_the_named_runs(frozen, runs, changes):
    status, result = run_preservation(frozen['data_dir'], frozen['freeze_pin'], runs=runs)
    assert status == (1 if changes else 0)
    assert result == checked(status='changed' if changes else 'preserved', **changes)


@pytest.mark.parametrize('runs', ['first.part', '../first', '', 'first,bad name', 'first,,replay'],
                         ids=['part', 'path', 'empty', 'one_unsafe', 'empty_item'])
def test_preservation_refuses_an_unsafe_run_name(frozen, runs):
    status, result = run_preservation(frozen['data_dir'], frozen['freeze_pin'], runs=runs)
    assert (status, result) == (1, control_refusal('preservation', 'unsafe run ID'))


def test_frozen_runs_stay_without_being_named(chain_build):
    data_dir = chain_build['data_dir']
    status, frozen = run_freeze(data_dir)
    assert status == 0
    shutil.copytree(bundle(chain_build), data_dir / WAGE_RUNS / 'replay')
    status, result = run_preservation(data_dir, frozen['freeze_sha256'], runs='replay')
    assert (status, result) == (0, checked())
    shutil.rmtree(bundle(chain_build))
    status, result = run_preservation(data_dir, frozen['freeze_sha256'], runs='replay')
    assert (status, result) == (1, checked(status='changed', missing=[f'{WAGE_RUNS}/first'],
                                           runs=['replay']))


def test_a_part_directory_that_was_frozen_still_fails_the_check(chain_build):
    data_dir = chain_build['data_dir']
    (data_dir / WAGE_RUNS / 'old.part').mkdir()
    status, frozen = run_freeze(data_dir)
    assert status == 0
    shutil.copytree(bundle(chain_build), data_dir / WAGE_RUNS / 'replay')
    status, result = run_preservation(data_dir, frozen['freeze_sha256'], runs='replay')
    assert (status, result) == (1, checked(status='changed', added=[f'{WAGE_RUNS}/old.part'],
                                           runs=['first', 'old.part', 'replay']))


def test_freeze_records_every_file_outside_the_excluded_trees(chain_build):
    data_dir = chain_build['data_dir']
    earlier = data_dir / CONTROL_ROOT / 'earlier'
    earlier.mkdir(parents=True)
    (earlier / 'freeze.json').write_text('{}')
    expected = frozen_files(data_dir)
    manifest_file = data_dir / MANIFEST
    status, result = run_freeze(data_dir)
    file = control_dir(data_dir) / 'freeze.json'
    assert status == 0
    assert result == {'freeze_sha256': manifest.sha256_file(file), 'files': len(expected)}
    assert json.loads(file.read_text()) == {
        'files': expected,
        'manifest': {'sha256': manifest.sha256_file(manifest_file),
                     'size': manifest_file.stat().st_size,
                     'lines': manifest_file.read_bytes().count(b'\n')},
        'runs': ['first'],
    }
    assert manifest_file.read_bytes().endswith(b'\n')
    assert STAGE8_CORE in expected and a_raw_file(data_dir) in expected
    assert MANIFEST not in expected
    assert not [path for path in expected if path.startswith((WAGE_RUNS, CONTROL_ROOT))]
    assert any(bundle(chain_build).iterdir())


def test_freeze_before_any_build_records_no_runs(chain):
    status, _result = run_freeze(chain['data_dir'])
    assert status == 0
    record = json.loads((control_dir(chain['data_dir']) / 'freeze.json').read_text())
    assert record['runs'] == []


CONTROL_PLACES = {
    'existing': (lambda data_dir, outside: control_dir(data_dir), CONTROL_EXISTS),
    'other_parent': (lambda data_dir, outside: data_dir / 'derived/acs/controls/first',
                     UNSAFE_CONTROL),
    'nested': (lambda data_dir, outside: control_dir(data_dir) / 'inner', UNSAFE_CONTROL),
    'unsafe_id': (lambda data_dir, outside: control_dir(data_dir, 'first.v1'), UNSAFE_CONTROL),
    'part_suffix': (lambda data_dir, outside: control_dir(data_dir, 'first.part'),
                    UNSAFE_CONTROL),
    'the_controls_root': (lambda data_dir, outside: data_dir / CONTROL_ROOT, UNSAFE_CONTROL),
    'outside_the_data_dir': (lambda data_dir, outside: outside / CONTROL_ROOT / 'first',
                             UNSAFE_CONTROL),
}


@pytest.mark.parametrize('case', CONTROL_PLACES)
def test_freeze_refuses_an_existing_or_misplaced_control_dir(chain, tmp_path, case):
    data_dir = chain['data_dir']
    place, reason = CONTROL_PLACES[case]
    path = place(data_dir, tmp_path / 'outside')
    if reason == CONTROL_EXISTS:
        path.mkdir(parents=True)
    before = tree(data_dir)
    status, result = run_freeze(data_dir, control=path)
    assert (status, result) == (1, control_refusal('freeze', reason))
    assert tree(data_dir) == before
    assert not (tmp_path / 'outside').exists()


@pytest.mark.skipif(os.geteuid() == 0, reason='a superuser can read an unreadable file')
def test_freeze_hashes_every_file_before_it_creates_the_control_directory(chain):
    data_dir = chain['data_dir']
    unreadable = data_dir / a_raw_file(data_dir)
    unreadable.chmod(0)
    try:
        before = tree(data_dir)
        status, result = run_freeze(data_dir)
    finally:
        unreadable.chmod(0o644)
    assert (status, result) == (1, control_refusal('freeze', 'freeze failed'))
    assert tree(data_dir) == before


def test_freeze_twice_with_the_same_control_dir_is_refused(chain):
    assert run_freeze(chain['data_dir'])[0] == 0
    file = control_dir(chain['data_dir']) / 'freeze.json'
    before = file.read_bytes()
    status, result = run_freeze(chain['data_dir'])
    assert (status, result) == (1, control_refusal('freeze', CONTROL_EXISTS))
    assert file.read_bytes() == before


def link_in_raw(data_dir):
    os.symlink(data_dir / MANIFEST, data_dir / 'raw' / 'link.txt')
    return 'symlink in the walk: raw/link.txt'


def link_to_a_directory(data_dir):
    os.symlink(data_dir / 'raw', data_dir / 'derived' / 'linked')
    return 'symlink in the walk: derived/linked'


def broken_link(data_dir):
    os.symlink(data_dir / 'nowhere', data_dir / 'raw' / 'broken')
    return 'symlink in the walk: raw/broken'


def link_inside_a_run(data_dir):
    run = data_dir / WAGE_RUNS / 'first'
    run.mkdir(parents=True)
    os.symlink(data_dir / MANIFEST, run / 'link.txt')
    return f'symlink in the walk: {WAGE_RUNS}/first/link.txt'


def raw_as_a_link(data_dir):
    (data_dir / 'raw').rename(data_dir / 'raw_real')
    os.symlink(data_dir / 'raw_real', data_dir / 'raw')
    return 'symlink in the walk: raw'


def pipe_in_raw(data_dir):
    os.mkfifo(data_dir / 'raw' / 'pipe')
    return 'not a regular file in the walk: raw/pipe'


WALK_CASES = {function.__name__: function for function in (
    link_in_raw, link_to_a_directory, broken_link, link_inside_a_run, raw_as_a_link,
    pipe_in_raw)}


@pytest.mark.parametrize('case', WALK_CASES)
def test_freeze_refuses_a_symlink_or_other_entry_in_the_walk(chain, case):
    data_dir = chain['data_dir']
    reason = WALK_CASES[case](data_dir)
    before = tree(data_dir)
    status, result = run_freeze(data_dir)
    assert (status, result) == (1, control_refusal('freeze', reason))
    assert tree(data_dir) == before


@pytest.mark.parametrize('case', WALK_CASES)
def test_preservation_refuses_a_symlink_or_other_entry_in_the_walk(chain, case):
    data_dir = chain['data_dir']
    status, frozen = run_freeze(data_dir)
    assert status == 0
    reason = WALK_CASES[case](data_dir)
    status, result = run_preservation(data_dir, frozen['freeze_sha256'], runs='first')
    assert (status, result) == (1, control_refusal('preservation', reason))


TREE_CASES = {
    'neither': ((), WRONG_TREES),
    'no_raw': (('derived',), WRONG_TREES),
    'no_derived': (('raw',), WRONG_TREES),
    'no_manifest': (('raw', 'derived'), 'manifest is missing'),
}


@pytest.mark.parametrize('case', TREE_CASES)
def test_freeze_refuses_a_data_directory_without_the_expected_files(tmp_path, case):
    directories, reason = TREE_CASES[case]
    for name in directories:
        (tmp_path / name).mkdir()
    status, result = run_freeze(tmp_path)
    assert (status, result) == (1, control_refusal('freeze', reason))
    assert not (tmp_path / CONTROL_ROOT).exists()


def test_preservation_refuses_a_wrong_freeze_pin(chain):
    data_dir = chain['data_dir']
    status, frozen = run_freeze(data_dir)
    assert status == 0
    # The tree is damaged twice over, and a symlink would refuse the walk, so only a pin
    # check that comes first gives this reason.
    remove_raw_file(data_dir)
    link_in_raw(data_dir)
    status, result = run_preservation(data_dir, '0' * 64, runs='first')
    assert (status, result) == (1, control_refusal('preservation', PIN_DIFFERS))
    assert frozen['freeze_sha256'] != '0' * 64


def test_preservation_refuses_a_control_directory_without_a_freeze_record(chain):
    data_dir = chain['data_dir']
    status, frozen = run_freeze(data_dir)
    assert status == 0
    (control_dir(data_dir) / 'freeze.json').unlink()
    status, result = run_preservation(data_dir, frozen['freeze_sha256'], runs='first')
    assert (status, result) == (1, control_refusal('preservation', PIN_DIFFERS))
    other = control_dir(data_dir, 'absent')
    status, result = run_preservation(data_dir, frozen['freeze_sha256'], runs='first',
                                      control=other)
    assert (status, result) == (1, control_refusal('preservation', PIN_DIFFERS))


def test_preservation_refuses_a_misplaced_control_directory(chain, tmp_path):
    data_dir = chain['data_dir']
    status, frozen = run_freeze(data_dir)
    assert status == 0
    # The copy holds the pinned record, so only the placement check refuses.
    elsewhere = tmp_path / 'elsewhere' / 'first'
    shutil.copytree(control_dir(data_dir), elsewhere)
    status, result = run_preservation(data_dir, frozen['freeze_sha256'], runs='first',
                                      control=elsewhere)
    assert (status, result) == (1, control_refusal('preservation', UNSAFE_CONTROL))


def test_preservation_prints_a_fixed_reason_for_an_unreadable_record(chain):
    data_dir = chain['data_dir']
    assert run_freeze(data_dir)[0] == 0
    file = control_dir(data_dir) / 'freeze.json'
    file.write_bytes(b'not json at all')
    status, result = run_preservation(data_dir, manifest.sha256_file(file), runs='first')
    assert (status, result) == (1, control_refusal('preservation', 'preservation failed'))


@pytest.mark.parametrize(('content', 'lines'), [
    (b'', 0), (b'a\n', 1), (b'a\nb', 2), (b'a\nb\n', 2), (b'\n\n\n', 3), (b'abcdefghij\n', 1),
], ids=['empty', 'one', 'unterminated', 'two', 'blank_lines', 'longer_than_a_chunk'])
def test_manifest_facts_count_lines_across_chunks(script, monkeypatch, tmp_path, content, lines):
    monkeypatch.setattr(script, 'READ_SIZE', 4)
    (tmp_path / 'raw').mkdir()
    (tmp_path / MANIFEST).write_bytes(content)
    assert script.manifest_facts(tmp_path) == {
        'sha256': manifest.sha256_file(tmp_path / MANIFEST), 'size': len(content),
        'lines': lines}
