'''The independent Stage 17 reconciler, on the fixture chain and on small typed rows.'''

import ast
import importlib.util
import json
import math
import operator
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
