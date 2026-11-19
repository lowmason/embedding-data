'''Build, verify and compare the ACS wage microdata bundles on the fixture chain.'''

import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest
from acs_mapping_fixtures import forbid_external_access
from acs_wage_fixtures import CONTROLS, DUPLICATED_CONTROL, copy_template, wage_mapping

from embedding_data import (
    acs_wage_bundle,
    acs_wage_inputs,
    acs_wage_rules,
    manifest,
    paths,
    target_io,
)
from embedding_data.acs_wage_bundle import (
    FILES,
    INPUT_FIELDS,
    compare_runs,
    ordered_compare,
    verify_bundle,
)

# AGE marker to the expected values of its control rows. AGE 48 has no wage and is absent.
# AGE 49 also holds the highest 2024 wage of its state, so its top-code flag is not asserted.
EXPECTED_CONTROLS = {
    41: {'flag_headline': True},
    42: {'flag_any_allocated': True, 'flag_headline': False},
    43: {'flag_any_allocated': True, 'flag_headline': True},
    44: {'flag_full_time_full_year': False, 'flag_headline': False},
    45: {'flag_full_time_full_year': False, 'flag_headline': False},
    46: {'flag_wage_salary': False, 'flag_headline': False},
    47: {'flag_wage_salary': False, 'flag_headline': False},
    48: None,
    49: {'YEAR': 2024, 'industry_node_code': '811192', 'flag_headline': True},
    50: {'flag_incwage_topcoded': True, 'flag_headline': True},
}


def reverse(plan):
    return plan.reverse()


def drop_last_row(plan):
    return plan.head(plan.select(pl.len()).collect().item() - 1)


def all_headline(plan):
    return plan.with_columns(pl.lit(True).alias('flag_headline'))


def unknown_node(plan):
    return plan.with_columns(pl.lit('999999').alias('industry_node_code'))


def swap_first_columns(plan):
    names = plan.collect_schema().names()
    return plan.select(names[1], names[0], *names[2:])


DISTORTIONS = {
    'reverse': reverse,
    'drop_last_row': drop_last_row,
    'all_headline': all_headline,
    'unknown_node': unknown_node,
    'carried_type': lambda plan: plan.with_columns(pl.col('AGE').cast(pl.Int32)),
    'new_type': lambda plan: plan.with_columns(pl.col('log_wage_2010').cast(pl.Float32)),
    'order': swap_first_columns,
    'extra': lambda plan: plan.with_columns(pl.lit(1).alias('extra')),
    'missing': lambda plan: plan.drop('GQ'),
}


@pytest.fixture(scope='module')
def template(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patches:
        yield wage_mapping(tmp_path_factory.mktemp('wage-bundle-template'), patches)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    forbid_external_access(monkeypatch)


@pytest.fixture
def chain(template, tmp_path):
    return copy_template(template, tmp_path)


def build(chain, run_id):
    return acs_wage_bundle.build(
        chain['data_dir'],
        run_id,
        mapping_run=chain['mapping_run'],
        mapping_outputs_sha256=chain['mapping_outputs_sha256'],
        codes_run=chain['codes_run'],
        codes_outputs_sha256=chain['codes_outputs_sha256'],
    )


def built(chain, run_id='first'):
    return Path(build(chain, run_id)['directory'])


def verify(chain, directory, pin):
    return verify_bundle(directory, chain['data_dir'], expected_outputs_sha256=pin)


def sha256(file):
    return manifest.sha256_file(file)


def stage8_core(chain):
    return (chain['data_dir'] / 'derived/acs/mapping' / chain['mapping_run']
            / 'acs_core_canonical.parquet')


def runs_root(chain):
    return chain['data_dir'] / 'derived/acs/wage-microdata'


def digests(directory):
    '''Every file under the directory, by relative path, with its bytes.'''
    return {path.relative_to(directory).as_posix(): path.read_bytes()
            for path in sorted(directory.rglob('*')) if path.is_file()}


def entries(directory):
    return sorted(path.name for path in directory.iterdir())


def forbidden(*args, **kwargs):
    raise AssertionError('a bundle file was read before its detached pin was checked')


def distort(monkeypatch, name):
    original = acs_wage_rules.wage_persons
    monkeypatch.setattr(acs_wage_rules, 'wage_persons',
                        lambda core: DISTORTIONS[name](original(core)))


def rehash(directory):
    '''Rewrite a bundle's inventory after an edit, and return the new detached pin.'''
    target_io.write_json(directory / 'outputs.json', target_io.inventory(directory, list(FILES)))
    return sha256(directory / 'outputs.json')


def change_age(directory):
    '''Rewrite the first row's AGE in the bundle's table, keeping its schema.'''
    file = directory / 'acs_wage_persons.parquet'
    first = pl.int_range(pl.len()) == 0
    pl.read_parquet(file).with_columns(
        pl.when(first).then(pl.col('AGE') + 1).otherwise(pl.col('AGE')).alias('AGE')
    ).write_parquet(file)


def edit_json(directory, name, mutate):
    file = directory / name
    value = json.loads(file.read_text())
    mutate(value)
    target_io.write_json(file, value)


def git(*args):
    return subprocess.run(['git', *args], cwd=paths.PROJECT_ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


def test_ordered_compare_streams_and_counts():
    base = pl.DataFrame({'a': [1, 2, 3, 4, 5], 'b': ['v', 'w', 'x', 'y', 'z']})
    last_changed = base.with_columns(
        pl.when(pl.col('a') == 5).then(pl.lit('changed')).otherwise(pl.col('b')).alias('b'))
    zero = base.with_columns(pl.when(pl.col('a') == 3).then(0).otherwise(pl.col('a')).alias('a'))
    null = base.with_columns(
        pl.when(pl.col('a') == 3).then(None).otherwise(pl.col('a')).alias('a'))
    pairs = [
        (base, base),
        (base, last_changed),
        (base, pl.concat([base, base.tail(1)])),
        (base, base.rename({'b': 'c'})),
        (null, zero),
    ]
    compared = [ordered_compare(first.lazy(), second.lazy(), chunk_size=2)
                for first, second in pairs]
    results = [(result['schema_equal'], result['values_equal']) for result in compared]
    assert results == [(True, True), (True, False), (True, False), (False, False),
                       (True, False)]


def test_ordered_compare_counts_every_row_of_each_side():
    five = pl.LazyFrame({'a': [1, 2, 3, 4, 5]})
    six = pl.LazyFrame({'a': [1, 2, 3, 4, 5, 6]})
    renamed = pl.LazyFrame({'b': [1, 2, 3]})
    first_changed = pl.LazyFrame({'a': [0, 2, 3, 4, 5]})
    compared = [ordered_compare(first, second, chunk_size=2)
                for first, second in ((five, six), (six, five), (five, renamed),
                                      (first_changed, five), (five, five))]
    assert [(result['first_rows'], result['second_rows'], result['values_equal'])
            for result in compared] == [(5, 6, False), (6, 5, False), (5, 3, False),
                                        (5, 5, False), (5, 5, True)]
    assert ordered_compare(five, five) == {'schema_equal': True, 'values_equal': True,
                                           'first_rows': 5, 'second_rows': 5}


@pytest.mark.parametrize('chunk_size', [0, -2, True, 2.0])
def test_ordered_compare_refuses_a_chunk_size_that_is_not_a_positive_integer(chunk_size):
    frame = pl.LazyFrame({'a': [1]})
    with pytest.raises(ValueError, match='chunk_size must be a positive integer'):
        ordered_compare(frame, frame, chunk_size=chunk_size)


def test_run_directory_names_the_bundle_path(tmp_path):
    assert acs_wage_bundle.run_directory(tmp_path, 'r1_x-2') == (
        tmp_path / 'derived/acs/wage-microdata/r1_x-2')


@pytest.mark.parametrize('run_id', ['', '../first', '.hidden', 'a/b', 'first.part', '-first',
                                    None])
def test_run_directory_refuses_an_unsafe_id(tmp_path, run_id):
    with pytest.raises(ValueError, match='unsafe run ID'):
        acs_wage_bundle.run_directory(tmp_path, run_id)


def test_build_publishes_the_exact_file_set_and_pin(chain):
    result = build(chain, 'first')
    directory = Path(result['directory'])
    assert sorted(p.name for p in directory.iterdir()) == sorted([*FILES, 'outputs.json'])
    assert result['outputs_sha256'] == sha256(directory / 'outputs.json')


def test_build_returns_the_run_and_its_published_inventory(chain):
    result = build(chain, 'first')
    directory = runs_root(chain) / 'first'
    assert result == {'run_id': 'first', 'directory': str(directory),
                      'outputs_sha256': sha256(directory / 'outputs.json')}
    assert json.loads((directory / 'outputs.json').read_text()) == (
        target_io.inventory(directory, list(FILES)))
    assert entries(runs_root(chain)) == ['first']


def test_rows_are_the_stage8_earners_in_order(chain):
    directory = built(chain)
    core = pl.read_parquet(stage8_core(chain)).filter(pl.col('INCWAGE') > 0)
    persons = pl.read_parquet(directory / 'acs_wage_persons.parquet')
    assert persons['source_row'].to_list() == core['source_row'].to_list()


def test_control_rows_get_their_expected_flags(chain):
    persons = pl.read_parquet(built(chain) / 'acs_wage_persons.parquet')
    for age in CONTROLS:
        rows = persons.filter(pl.col('AGE') == age)
        expected = EXPECTED_CONTROLS[age]
        if expected is None:
            assert rows.height == 0, age
        else:
            copies = 2 if age == DUPLICATED_CONTROL else 1
            assert rows.select(list(expected)).to_dicts() == [expected] * copies, age


def test_report_holds_counts_and_no_run_identity(chain):
    directory = built(chain)
    report = json.loads((directory / 'report.json').read_text())
    assert set(report) == {'contract', 'rows', 'funnel', 'flags', 'categories',
                           'headline_categories', 'shared_nodes', 'node_levels'}
    text = json.dumps(report)
    assert 'first' not in text and 'created_at' not in text and 'commit' not in text


def test_report_is_the_summary_of_the_published_table(chain):
    directory = built(chain)
    summary = acs_wage_rules.summarize(pl.scan_parquet(directory / 'acs_wage_persons.parquet'))
    assert json.loads((directory / 'report.json').read_text()) == json.loads(json.dumps(summary))


def test_inputs_record_pins_labels_rules_software_and_execution(chain):
    before = datetime.now(UTC)
    directory = built(chain)
    after = datetime.now(UTC)
    inputs = json.loads((directory / 'inputs.json').read_text())
    selected = acs_wage_inputs.select_wage_inputs(
        chain['data_dir'], chain['mapping_run'],
        mapping_outputs_sha256=chain['mapping_outputs_sha256'],
        codes_run=chain['codes_run'], codes_outputs_sha256=chain['codes_outputs_sha256'])
    assert set(inputs) == INPUT_FIELDS
    assert inputs['run_id'] == 'first'
    assert inputs['contract'] == acs_wage_rules.CONTRACT == 'acs-wage-microdata-v1'
    assert inputs['mapping'] == selected.provenance['mapping']
    assert (inputs['mapping']['run_id'], inputs['mapping']['outputs_sha256']) == (
        chain['mapping_run'], chain['mapping_outputs_sha256'])
    assert inputs['codes'] == selected.provenance['codes']
    assert (inputs['codes']['run_id'], inputs['codes']['outputs_sha256']) == (
        chain['codes_run'], chain['codes_outputs_sha256'])
    assert inputs['ddi'] == selected.provenance['ddi']
    assert inputs['labels'] == acs_wage_rules.DDI_LABELS
    assert inputs['rules'] == acs_wage_rules.RULES
    assert inputs['software'] == json.loads(json.dumps(acs_wage_inputs.freeze_software()))
    execution = inputs['execution']
    assert set(execution) == {'commit', 'dirty', 'created_at'}
    assert execution['commit'] == git('rev-parse', 'HEAD')
    assert execution['dirty'] is bool(git('status', '--porcelain', '--untracked-files=normal'))
    created = datetime.fromisoformat(execution['created_at'])
    assert created.utcoffset().total_seconds() == 0
    assert before <= created <= after


@pytest.mark.parametrize(('status', 'dirty'), [('', False), (' M src/x.py\n?? y.py\n', True)])
def test_execution_reads_head_and_status_from_the_repository(chain, monkeypatch, status, dirty):
    original, calls = subprocess.run, []

    def fake_run(args, **kwargs):
        if args[:1] != ['git']:
            return original(args, **kwargs)
        calls.append((args, kwargs.get('cwd')))
        stdout = {'rev-parse': 'c' * 40 + '\n', 'status': status}[args[1]]
        return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr='')

    monkeypatch.setattr(subprocess, 'run', fake_run)
    execution = json.loads((built(chain) / 'inputs.json').read_text())['execution']
    assert (execution['commit'], execution['dirty']) == ('c' * 40, dirty)
    assert calls == [
        (['git', 'rev-parse', 'HEAD'], paths.PROJECT_ROOT),
        (['git', 'status', '--porcelain', '--untracked-files=normal'], paths.PROJECT_ROOT),
    ]


@pytest.mark.parametrize('name', ['first', 'first.part'])
def test_occupied_run_path_is_refused_and_untouched(chain, name):
    occupied = runs_root(chain) / name
    occupied.mkdir(parents=True)
    (occupied / 'kept.txt').write_bytes(b'kept\n')
    with pytest.raises(ValueError, match='run or staging name already exists'):
        build(chain, 'first')
    assert digests(runs_root(chain)) == {f'{name}/kept.txt': b'kept\n'}
    assert entries(runs_root(chain)) == [name]


def test_leftover_part_blocks_only_its_own_run_id(chain):
    leftover = runs_root(chain) / 'first.part'
    leftover.mkdir(parents=True)
    (leftover / 'acs_wage_persons.parquet').write_bytes(b'partial rows')
    before = digests(leftover)
    with pytest.raises(ValueError, match='run or staging name already exists'):
        build(chain, 'first')
    assert digests(leftover) == before
    assert entries(runs_root(chain)) == ['first.part']
    result = build(chain, 'second')
    assert Path(result['directory']) == runs_root(chain) / 'second'
    assert digests(leftover) == before
    assert entries(runs_root(chain)) == ['first.part', 'second']


def test_failed_build_removes_only_its_staging(chain, monkeypatch):
    built(chain)
    other = runs_root(chain) / 'other.part'
    other.mkdir()
    (other / 'report.json').write_bytes(b'{}\n')
    before = digests(runs_root(chain))

    def failing(persons):
        raise RuntimeError('summary failed')

    monkeypatch.setattr(acs_wage_rules, 'summarize', failing)
    with pytest.raises(RuntimeError, match='summary failed'):
        build(chain, 'second')
    assert entries(runs_root(chain)) == ['first', 'other.part']
    assert digests(runs_root(chain)) == before


def test_cleanup_refuses_a_staging_path_that_became_a_symlink(chain, monkeypatch):
    staging = runs_root(chain) / 'first.part'
    moved = chain['data_dir'].parent / 'moved'
    original = acs_wage_rules.summarize

    def swapping(persons):
        summary = original(persons)
        staging.rename(moved)
        staging.symlink_to(moved, target_is_directory=True)
        return summary

    monkeypatch.setattr(acs_wage_rules, 'summarize', swapping)
    with pytest.raises(ValueError, match='symlink'):
        build(chain, 'first')
    assert staging.is_symlink()
    assert 'acs_wage_persons.parquet' in entries(moved)


@pytest.mark.parametrize('distortion', ['reverse', 'drop_last_row'])
def test_build_refuses_reordered_or_missing_staged_rows(chain, monkeypatch, distortion):
    distort(monkeypatch, distortion)
    with pytest.raises(ValueError, match='staged rows differ from the earners'):
        build(chain, 'first')
    assert entries(runs_root(chain)) == []


@pytest.mark.parametrize('distortion', ['carried_type', 'new_type', 'order', 'extra', 'missing'])
def test_build_refuses_a_staged_schema_other_than_the_contract(chain, monkeypatch, distortion):
    distort(monkeypatch, distortion)
    with pytest.raises(ValueError, match='staged schema differs from the contract'):
        build(chain, 'first')
    assert entries(runs_root(chain)) == []


@pytest.mark.parametrize(('distortion', 'message'), [
    ('all_headline', 'headline row breaks a headline rule'),
    ('unknown_node', 'industry node is not a Stage 4 NAICS 2022 node'),
])
def test_build_runs_the_headline_and_node_checks(chain, monkeypatch, distortion, message):
    distort(monkeypatch, distortion)
    with pytest.raises(ValueError, match=message):
        build(chain, 'first')
    assert entries(runs_root(chain)) == []


@pytest.mark.parametrize(('change', 'message'), [
    ('inputs', 'selected inputs changed'),
    ('software', 'executing software changed before publication'),
])
def test_build_rechecks_inputs_and_software_before_publication(chain, monkeypatch, change,
                                                               message):
    original = acs_wage_rules.summarize

    def changing(persons):
        if change == 'inputs':
            core = stage8_core(chain)
            core.write_bytes(core.read_bytes() + b'\0')
        else:
            monkeypatch.setattr(acs_wage_inputs, 'SOFTWARE_FILES',
                                acs_wage_inputs.SOFTWARE_FILES[:-1])
        return original(persons)

    monkeypatch.setattr(acs_wage_rules, 'summarize', changing)
    with pytest.raises(ValueError, match=message):
        build(chain, 'first')
    assert entries(runs_root(chain)) == []


@pytest.mark.parametrize(('change', 'message'), [
    ('final', 'final run name already exists'),
    ('extra', 'staged bundle files differ from the bundle file set'),
])
def test_build_checks_the_staged_names_and_the_final_before_the_rename(chain, monkeypatch,
                                                                     change, message):
    original = acs_wage_rules.summarize

    def changing(persons):
        if change == 'final':
            (runs_root(chain) / 'first').mkdir()
        else:
            (runs_root(chain) / 'first.part' / 'extra.txt').write_bytes(b'extra\n')
        return original(persons)

    monkeypatch.setattr(acs_wage_rules, 'summarize', changing)
    with pytest.raises(ValueError, match=message):
        build(chain, 'first')
    expected = ['first'] if change == 'final' else []
    assert entries(runs_root(chain)) == expected
    assert digests(runs_root(chain)) == {}


def test_build_and_verify_never_collect_person_rows(chain, monkeypatch):
    # A frame that holds person rows has a `source_row` column. Batches of a streamed
    # comparison and sinks do not pass through these three functions.
    held = []
    collect, collect_all, read_parquet = pl.LazyFrame.collect, pl.collect_all, pl.read_parquet

    def note(frame):
        if isinstance(frame, pl.DataFrame) and 'source_row' in frame.columns and frame.height:
            held.append(frame.height)
        return frame

    monkeypatch.setattr(pl.LazyFrame, 'collect',
                        lambda self, *args, **kwargs: note(collect(self, *args, **kwargs)))
    monkeypatch.setattr(pl, 'collect_all', lambda frames, *args, **kwargs: [
        note(frame) for frame in collect_all(frames, *args, **kwargs)])
    monkeypatch.setattr(pl, 'read_parquet',
                        lambda *args, **kwargs: note(read_parquet(*args, **kwargs)))
    result = build(chain, 'first')
    verify(chain, Path(result['directory']), result['outputs_sha256'])
    assert held == []


def test_symlinked_run_root_is_refused(chain):
    elsewhere = chain['data_dir'].parent / 'elsewhere'
    elsewhere.mkdir()
    runs_root(chain).symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        build(chain, 'first')
    assert list(elsewhere.iterdir()) == []


def test_importing_the_bundle_loads_only_listed_software():
    probe = 'import sys, embedding_data.acs_wage_bundle; print("\\n".join(sorted(sys.modules)))'
    loaded = set(subprocess.run([sys.executable, '-c', probe], check=True, capture_output=True,
                                text=True).stdout.split())
    assert not loaded & {'dotenv', 'ipumspy'}
    files = {'src/embedding_data/' + (name.partition('.')[2] or '__init__') + '.py'
             for name in loaded if name.partition('.')[0] == 'embedding_data'}
    assert 'src/embedding_data/acs_wage_bundle.py' in files
    assert files <= set(acs_wage_inputs.SOFTWARE_FILES)


def test_verify_passes_with_the_pin(chain):
    result = build(chain, 'first')
    directory = Path(result['directory'])
    persons = pl.read_parquet(directory / 'acs_wage_persons.parquet')
    assert verify(chain, directory, result['outputs_sha256']) == {
        'run_id': 'first',
        'outputs_sha256': result['outputs_sha256'],
        'mapping_run': chain['mapping_run'],
        'codes_run': chain['codes_run'],
        'rows': persons.height,
        'headline_rows': persons['flag_headline'].sum(),
    }


def test_verify_refuses_a_wrong_pin_before_reading_inputs(chain, monkeypatch):
    directory = built(chain)
    monkeypatch.setattr(acs_wage_inputs, 'read_json', forbidden)
    with pytest.raises(ValueError, match='detached inventory checksum differs'):
        verify(chain, directory, '0' * 64)


@pytest.mark.parametrize('pin', ['', '0' * 63, '0' * 65, 'g' * 64, 'A' * 64, None])
def test_verify_refuses_a_malformed_pin_before_any_read(tmp_path, monkeypatch, pin):
    monkeypatch.setattr(acs_wage_inputs, 'read_json', forbidden)
    with pytest.raises(ValueError, match='invalid detached checksum'):
        verify_bundle(acs_wage_bundle.run_directory(tmp_path, 'first'), tmp_path,
                      expected_outputs_sha256=pin)


def test_verify_refuses_a_rehashed_edit(chain):
    directory = built(chain)
    change_age(directory)
    pin = rehash(directory)
    with pytest.raises(ValueError, match='differs from the recomputation'):
        verify(chain, directory, pin)


@pytest.mark.parametrize(('file', 'mutate', 'message'), [
    ('report.json', lambda report: report['rows'].update(total=report['rows']['total'] + 1),
     'published report differs from the recomputation'),
    ('inputs.json', lambda inputs: inputs['rules'].update(flag_headline='Every row.'),
     'recorded inputs differ from the recomputation'),
    ('inputs.json', lambda inputs: inputs['ddi'].update(size=inputs['ddi']['size'] + 1),
     'recorded inputs differ from the recomputation'),
    ('inputs.json', lambda inputs: inputs.pop('labels'), 'recorded inputs are malformed'),
    ('inputs.json', lambda inputs: inputs.update(note='extra'), 'recorded inputs are malformed'),
    ('inputs.json', lambda inputs: inputs.update(contract='acs-wage-microdata-v0'),
     'recorded contract differs'),
    ('inputs.json', lambda inputs: inputs.update(codes='stage4'), 'recorded inputs are malformed'),
    ('inputs.json', lambda inputs: inputs['mapping'].pop('outputs_sha256'),
     'recorded inputs are malformed'),
], ids=['report_count', 'rules', 'ddi', 'no_labels', 'extra_field', 'contract',
        'codes_not_an_object', 'no_mapping_pin'])
def test_verify_refuses_a_rehashed_json_forgery(chain, file, mutate, message):
    directory = built(chain)
    edit_json(directory, file, mutate)
    with pytest.raises(ValueError, match=message):
        verify(chain, directory, rehash(directory))


def test_verify_refuses_a_renamed_copy(chain):
    result = build(chain, 'first')
    copy = shutil.copytree(result['directory'], runs_root(chain) / 'renamed')
    with pytest.raises(ValueError, match='recorded run ID differs from the directory'):
        verify(chain, copy, result['outputs_sha256'])


@pytest.mark.parametrize('extra', ['file', 'directory'])
def test_verify_refuses_an_extra_entry(chain, extra):
    result = build(chain, 'first')
    directory = Path(result['directory'])
    if extra == 'file':
        (directory / 'notes.txt').write_bytes(b'note\n')
    else:
        (directory / 'scratch').mkdir()
    with pytest.raises(ValueError, match='bundle file set differs'):
        verify(chain, directory, result['outputs_sha256'])


def test_verify_refuses_inexact_inventory_records(chain):
    directory = built(chain)
    outputs = target_io.inventory(directory, list(FILES))
    for key in ('rows', 'columns', 'schema'):
        del outputs['acs_wage_persons.parquet'][key]
    target_io.write_json(directory / 'outputs.json', outputs)
    with pytest.raises(ValueError, match='output inventory records differ'):
        verify(chain, directory, sha256(directory / 'outputs.json'))


def test_verify_refuses_an_unrehashed_edit(chain):
    result = build(chain, 'first')
    directory = Path(result['directory'])
    change_age(directory)
    with pytest.raises(ValueError, match='acs_wage_persons.parquet: inventory hash or size'):
        verify(chain, directory, result['outputs_sha256'])


def test_verify_refuses_changed_software(chain, monkeypatch):
    result = build(chain, 'first')
    monkeypatch.setattr(acs_wage_inputs, 'SOFTWARE_FILES', acs_wage_inputs.SOFTWARE_FILES[:-1])
    with pytest.raises(ValueError, match='executing software differs from the build'):
        verify(chain, Path(result['directory']), result['outputs_sha256'])


def test_verify_refuses_a_part_directory(chain, monkeypatch):
    result = build(chain, 'first')
    part = shutil.copytree(result['directory'], runs_root(chain) / 'first.part')
    monkeypatch.setattr(acs_wage_inputs, 'read_json', forbidden)
    with pytest.raises(ValueError, match='an interrupted bundle is not published'):
        verify(chain, part, result['outputs_sha256'])


@pytest.mark.parametrize(('distortion', 'message'), [
    ('reverse', 'published rows differ from the earners'),
    ('drop_last_row', 'published rows differ from the earners'),
    ('all_headline', 'headline row breaks a headline rule'),
    ('unknown_node', 'industry node is not a Stage 4 NAICS 2022 node'),
])
def test_verify_runs_the_row_checks_on_the_published_table(chain, monkeypatch, distortion,
                                                           message):
    # The recomputation makes the same mistake, so only verify's own checks can refuse.
    directory = built(chain)
    plan = acs_wage_rules.wage_persons(pl.scan_parquet(stage8_core(chain)))
    DISTORTIONS[distortion](plan).collect().write_parquet(directory / 'acs_wage_persons.parquet')
    pin = rehash(directory)
    distort(monkeypatch, distortion)
    with pytest.raises(ValueError, match=message):
        verify(chain, directory, pin)


def test_replay_compares_equal(chain):
    first, replay = built(chain, 'first'), built(chain, 'replay')
    rows = pl.read_parquet(first / 'acs_wage_persons.parquet').height
    assert rows > 0
    assert compare_runs(first, replay) == {
        'equal': True,
        'table': {'schema_equal': True, 'values_equal': True, 'first_rows': rows,
                  'second_rows': rows},
        'report_equal': True,
        'trust_established': False,
    }


def outside_runs(data_dir):
    '''Every path under the data directory outside the wage-microdata runs, with file bytes.'''
    runs = data_dir / 'derived/acs/wage-microdata'
    return {path.relative_to(data_dir).as_posix(): path.read_bytes() if path.is_file() else None
            for path in sorted(data_dir.rglob('*')) if not path.is_relative_to(runs)}


def test_build_verify_and_compare_write_only_their_runs(chain):
    before = outside_runs(chain['data_dir'])
    first = build(chain, 'first')
    verify(chain, Path(first['directory']), first['outputs_sha256'])
    replay = build(chain, 'replay')
    verify(chain, Path(replay['directory']), replay['outputs_sha256'])
    assert compare_runs(Path(first['directory']), Path(replay['directory']))['equal'] is True
    assert outside_runs(chain['data_dir']) == before
    assert entries(runs_root(chain)) == ['first', 'replay']


def test_compare_reports_a_rehashed_edit_as_unequal(chain):
    first, replay = built(chain, 'first'), built(chain, 'replay')
    change_age(replay)
    rehash(replay)
    result = compare_runs(first, replay)
    assert (result['equal'], result['table']['schema_equal'], result['table']['values_equal'],
            result['report_equal'], result['trust_established']) == (
                False, True, False, True, False)


def test_compare_reports_a_rehashed_report_edit_as_unequal(chain):
    first = built(chain)
    replay = shutil.copytree(first, runs_root(chain) / 'replay')
    edit_json(replay, 'report.json',
              lambda report: report['rows'].update(total=report['rows']['total'] + 1))
    rehash(replay)
    result = compare_runs(first, replay)
    assert (result['equal'], result['table']['values_equal'], result['report_equal']) == (
        False, True, False)


@pytest.mark.parametrize('side', ['first', 'second'])
def test_compare_refuses_an_inventory_mismatch(chain, side):
    first = built(chain)
    replay = shutil.copytree(first, runs_root(chain) / 'replay')
    change_age(first if side == 'first' else replay)
    with pytest.raises(ValueError, match='inventory'):
        compare_runs(first, replay)


@pytest.mark.parametrize('side', ['first', 'second'])
def test_compare_refuses_an_unpublished_side(chain, side):
    first = built(chain)
    part = shutil.copytree(first, runs_root(chain) / 'replay.part')
    pair = (part, first) if side == 'first' else (first, part)
    with pytest.raises(ValueError, match='compared bundles must be published'):
        compare_runs(*pair)
