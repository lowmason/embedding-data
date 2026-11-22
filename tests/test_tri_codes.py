'''The TRI codes selector: the pinned Stage 4 NAICS 2022 national-industry nodes.'''

import dataclasses
import json
import shutil

import polars as pl
import pytest
from tri_fixtures import seed_codes_bundle

from embedding_data import (
    classification_tables,
    code_build,
    manifest,
    target_inputs,
    target_io,
    tri_codes,
)

NODES = 'naics_nodes.parquet'
FIRST = 'naics:2022:national_industry:111110'


@pytest.fixture(scope='module')
def codes(tmp_path_factory):
    root = tmp_path_factory.mktemp('codes')
    run, pin = seed_codes_bundle(root / 'data', root / 'originals')
    return root / 'data', run, pin


def copy_bundle(data_dir, run, tmp_path):
    '''Copy only the codes bundle into a new data root that a test may change.'''
    root = tmp_path / 'data'
    shutil.copytree(data_dir / 'derived/codes' / run, root / 'derived/codes' / run)
    return root, root / 'derived/codes' / run


def repin(directory):
    '''Record the bytes of every inventoried file in outputs.json, and return its new pin.'''
    outputs_file = directory / 'outputs.json'
    outputs = json.loads(outputs_file.read_text())
    for name, record in outputs.items():
        file = directory / name
        record.update(sha256=manifest.sha256_file(file), size=file.stat().st_size)
    target_io.write_json(outputs_file, outputs)
    return manifest.sha256_file(outputs_file)


def edit_json(directory, name, change):
    '''Replace one JSON file by `change(value)`, then repin the bundle.'''
    file = directory / name
    target_io.write_json(file, change(json.loads(file.read_text())))
    return repin(directory)


def edit_nodes(directory, change):
    '''Rewrite naics_nodes.parquet, make report.json agree with it, then repin the bundle.'''
    file = directory / NODES
    frame = change(pl.read_parquet(file))
    frame.write_parquet(file)
    record = {'rows': frame.height, 'schema': {c: str(t) for c, t in frame.schema.items()}}
    return edit_json(directory, 'report.json', lambda report: {
        **report, 'tables': {**report['tables'], NODES: record}})


def row(node_id, system, vintage, level):
    return {'node_id': node_id, 'system': system, 'vintage': vintage, 'level': level,
            'code': node_id.rsplit(':', 1)[-1], 'title': 'Synthetic'}


def test_constants_match_stage4():
    assert set(tri_codes.CODE_TABLES) == set(target_inputs.CODE_SCHEMAS)
    assert tri_codes.NODE_SCHEMA == classification_tables.NODE_SCHEMA
    assert tri_codes.CODES_SCHEMA_VERSION == code_build.SCHEMA_VERSION


def test_select_nodes_reads_the_national_industries(codes):
    data_dir, run, pin = codes
    selected = tri_codes.select_nodes(data_dir, run, codes_outputs_sha256=pin)
    assert len(selected.node_ids) == 1012
    assert 'naics:2022:national_industry:111110' in selected.node_ids


def test_select_nodes_reads_no_ita_data(codes, tmp_path):
    data_dir, run, pin = codes
    copy = tmp_path / 'data'
    shutil.copytree(data_dir, copy)
    (copy / 'derived/osha/ita_300a_summary.parquet').unlink()
    shutil.rmtree(copy / 'raw/osha')
    selected = tri_codes.select_nodes(copy, run, codes_outputs_sha256=pin)
    expected = tri_codes.select_nodes(data_dir, run, codes_outputs_sha256=pin)
    assert selected.node_ids == expected.node_ids


# A case changes a private copy of the bundle, then returns the run and pin to select with.
def case_run_id(directory, run, pin):
    return '-' + run, pin


def case_pin_syntax(directory, run, pin):
    return run, pin.upper()


def case_wrong_pin(directory, run, pin):
    return run, '0' * 64


def case_extra_file(directory, run, pin):
    (directory / 'extra.txt').write_text('extra')
    return run, pin


def case_changed_byte(directory, run, pin):
    file = directory / 'inputs.json'
    data = bytearray(file.read_bytes())
    data[len(data) // 2] ^= 1
    file.write_bytes(bytes(data))
    return run, pin


def case_missing_file(directory, run, pin):
    (directory / 'soc_nodes.parquet').unlink()
    return run, pin


def inputs(change):
    return lambda directory, run, pin: (run, edit_json(directory, 'inputs.json', change))


def report(change):
    return lambda directory, run, pin: (run, edit_json(directory, 'report.json', change))


def nodes(change):
    return lambda directory, run, pin: (run, edit_nodes(directory, change))


def refuse(codes, tmp_path, case, message):
    data_dir, run, pin = codes
    root, directory = copy_bundle(data_dir, run, tmp_path)
    run, pin = case(directory, run, pin)
    with pytest.raises(ValueError, match=message):
        tri_codes.select_nodes(root, run, codes_outputs_sha256=pin)


REFUSALS = {
    'run_id': (case_run_id, 'unsafe selected run ID'),
    'pin_syntax': (case_pin_syntax, 'invalid detached checksum'),
    'wrong_pin': (case_wrong_pin, 'detached inventory checksum differs'),
    'extra_file': (case_extra_file, 'missing or extra inventory files'),
    'changed_byte': (case_changed_byte, 'inventory hash or size differs'),
    'schema_version': (inputs(lambda value: {**value, 'schema_version': 'codes-ita-v0'}),
                       'inputs.json: schema version differs'),
    'recorded_run_id': (inputs(lambda value: {**value, 'run_id': 'another_run'}),
                        'inputs.json: run identity differs'),
}


@pytest.mark.parametrize('mutation', ['run_id', 'pin_syntax', 'wrong_pin', 'extra_file',
                                      'changed_byte', 'schema_version', 'recorded_run_id'])
def test_select_nodes_refuses(codes, tmp_path, mutation):
    refuse(codes, tmp_path, *REFUSALS[mutation])


def with_record(**changes):
    '''Change report.json's record of naics_nodes.parquet.'''
    def change(value):
        record = {**value['tables'][NODES], **changes}
        return {**value, 'tables': {**value['tables'], NODES: record}}
    return change


def without_key(key):
    return lambda value: {k: v for k, v in value.items() if k != key}


def edit_outputs(directory, change):
    '''Replace outputs.json by `change(value)` and return the new pin.'''
    file = directory / 'outputs.json'
    target_io.write_json(file, change(json.loads(file.read_text())))
    return manifest.sha256_file(file)


def case_pinned_without_a_table(directory, run, pin):
    '''A bundle that is consistent with its own pin, but lacks one of the twelve tables.'''
    (directory / 'soc_edges.parquet').unlink()
    return run, edit_outputs(directory, without_key('soc_edges.parquet'))


def case_pinned_with_an_extra_file(directory, run, pin):
    '''A bundle that is consistent with its own pin, but holds a thirteenth file.'''
    file = directory / 'extra.txt'
    file.write_text('extra')
    record = {'sha256': manifest.sha256_file(file), 'size': file.stat().st_size}
    return run, edit_outputs(directory, lambda outputs: {**outputs, file.name: record})


def reordered(frame):
    return frame.select(frame.columns[::-1])


def narrowed(frame):
    return frame.with_columns(pl.col('vintage').cast(pl.Int32))


def widened(frame):
    return frame.with_columns(pl.lit('x').alias('extra'))


def prefix_lost(frame):
    return frame.with_columns(
        pl.when(pl.col('node_id') == FIRST).then(pl.lit('naics:2017:national_industry:111110'))
        .otherwise(pl.col('node_id')).alias('node_id'))


def level_lost(frame):
    return frame.with_columns(
        pl.when(pl.col('node_id') == FIRST).then(pl.lit('naics:2022:industry:11111'))
        .otherwise(pl.col('node_id')).alias('node_id'))


def id_missing(frame):
    return frame.with_columns(
        pl.when(pl.col('node_id') == FIRST).then(pl.lit(None, dtype=pl.String))
        .otherwise(pl.col('node_id')).alias('node_id'))


def id_repeated(frame):
    return pl.concat([frame, frame.filter(pl.col('node_id') == FIRST)])


NARROWED_SCHEMA = {**{c: str(t) for c, t in tri_codes.NODE_SCHEMA.items()}, 'vintage': 'Int32'}

MORE_REFUSALS = {
    'run_id_empty': (lambda directory, run, pin: ('', pin), 'unsafe selected run ID'),
    'run_id_dot': (lambda directory, run, pin: ('run.codes', pin), 'unsafe selected run ID'),
    'run_id_suffix': (lambda directory, run, pin: (run + '/..', pin), 'unsafe selected run ID'),
    'inventory_file_missing': (case_missing_file, 'missing or extra inventory files'),
    'inventory_pinned_without_a_table': (case_pinned_without_a_table,
                                         'missing or extra inventory files'),
    'inventory_pinned_with_an_extra_file': (case_pinned_with_an_extra_file,
                                            'missing or extra inventory files'),
    'pin_short': (lambda directory, run, pin: (run, pin[:-1]), 'invalid detached checksum'),
    'pin_long': (lambda directory, run, pin: (run, pin + '0'), 'invalid detached checksum'),
    'report_schema_version': (
        report(lambda value: {**value, 'schema_version': 'codes-ita-v0'}),
        'report.json: schema version differs'),
    'inputs_not_an_object': (inputs(list), 'inputs.json: not an object'),
    'inputs_without_version': (inputs(without_key('schema_version')),
                               'inputs.json: not an object'),
    'inputs_without_run': (inputs(without_key('run_id')), 'inputs.json: not an object'),
    'report_not_an_object': (report(list), 'report.json: not an object'),
    'report_without_tables': (report(without_key('tables')), 'report.json: not an object'),
    'report_tables_not_an_object': (report(lambda value: {**value, 'tables': [NODES]}),
                                    'report.json tables: not an object'),
    'report_without_nodes_record': (
        report(lambda value: {**value, 'tables': {}}),
        'report.json tables: not an object'),
    'report_record_not_an_object': (
        report(lambda value: {**value, 'tables': {**value['tables'], NODES: ['rows', 'schema']}}),
        'report.json naics_nodes.parquet: not an object'),
    'report_record_without_rows': (
        report(lambda value: {**value, 'tables': {
            **value['tables'], NODES: without_key('rows')(value['tables'][NODES])}}),
        'report.json naics_nodes.parquet: not an object'),
    'report_record_without_schema': (
        report(lambda value: {**value, 'tables': {
            **value['tables'], NODES: without_key('schema')(value['tables'][NODES])}}),
        'report.json naics_nodes.parquet: not an object'),
    'nodes_columns_reordered': (nodes(reordered), 'naics_nodes: ordered schema differs'),
    'nodes_vintage_narrowed': (nodes(narrowed), 'naics_nodes: ordered schema differs'),
    'nodes_column_added': (nodes(widened), 'naics_nodes: ordered schema differs'),
    'report_rows': (report(with_record(rows=1)), 'naics_nodes: rows or schema differ'),
    'report_schema': (report(with_record(schema=NARROWED_SCHEMA)),
                      'naics_nodes: rows or schema differ'),
    'node_id_prefix': (nodes(prefix_lost), 'naics_nodes: a node ID lacks the prefix'),
    'node_id_level': (nodes(level_lost), 'naics_nodes: a node ID lacks the prefix'),
    'node_id_missing': (nodes(id_missing), 'naics_nodes: a node ID lacks the prefix'),
    'node_id_repeated': (nodes(id_repeated), 'naics_nodes: a node ID repeats'),
}


@pytest.mark.parametrize('mutation', list(MORE_REFUSALS))
def test_select_nodes_refuses_each_further_check(codes, tmp_path, mutation):
    refuse(codes, tmp_path, *MORE_REFUSALS[mutation])


def test_select_nodes_keeps_only_native_2022_national_industries(codes, tmp_path):
    data_dir, run, pin = codes
    root, directory = copy_bundle(data_dir, run, tmp_path)
    others = pl.DataFrame([
        row('naics:2017:national_industry:999991', 'naics', 2017, 'national_industry'),
        row('soc:2022:national_industry:999992', 'soc', 2022, 'national_industry'),
        row('naics:2022:industry:999993', 'naics', 2022, 'industry'),
    ], schema=tri_codes.NODE_SCHEMA)
    pin = edit_nodes(directory, lambda frame: pl.concat([frame, others]))
    assert pl.read_parquet(directory / NODES).height == pl.read_parquet(
        data_dir / 'derived/codes' / run / NODES).height + 3
    selected = tri_codes.select_nodes(root, run, codes_outputs_sha256=pin)
    expected = tri_codes.select_nodes(data_dir, run, codes_outputs_sha256=codes[2])
    assert selected.node_ids == expected.node_ids
    assert len(selected.node_ids) == 1012


def test_select_nodes_reads_nothing_outside_the_bundle(codes, tmp_path):
    data_dir, run, pin = codes
    root, directory = copy_bundle(data_dir, run, tmp_path)
    assert [path.name for path in root.iterdir()] == ['derived']
    assert [path.name for path in (root / 'derived').iterdir()] == ['codes']
    selected = tri_codes.select_nodes(root, run, codes_outputs_sha256=pin)
    assert len(selected.node_ids) == 1012


def test_select_nodes_is_repeatable(codes):
    data_dir, run, pin = codes
    first = tri_codes.select_nodes(data_dir, run, codes_outputs_sha256=pin)
    second = tri_codes.select_nodes(data_dir, run, codes_outputs_sha256=pin)
    assert first == second
    assert isinstance(first.node_ids, frozenset)
    assert all(node_id.startswith(tri_codes.NODE_PREFIX) for node_id in first.node_ids)


def test_selected_nodes_are_frozen(codes):
    data_dir, run, pin = codes
    selected = tri_codes.select_nodes(data_dir, run, codes_outputs_sha256=pin)
    with pytest.raises(dataclasses.FrozenInstanceError):
        selected.node_ids = frozenset()


def test_provenance_cites_the_pinned_inventory(codes):
    data_dir, run, pin = codes
    selected = tri_codes.select_nodes(data_dir, run, codes_outputs_sha256=pin)
    outputs = json.loads((data_dir / 'derived/codes' / run / 'outputs.json').read_text())
    provenance = selected.provenance()
    assert provenance == {'run_id': run, 'outputs_sha256': pin, 'outputs': outputs}
    assert set(provenance['outputs']) == tri_codes.INVENTORY_NAMES
    assert selected.outputs == outputs


def test_verify_accepts_an_unchanged_bundle(codes):
    data_dir, run, pin = codes
    selected = tri_codes.select_nodes(data_dir, run, codes_outputs_sha256=pin)
    assert selected.verify() is None


def test_verify_detects_a_later_change(codes, tmp_path):
    data_dir, run, pin = codes
    root, directory = copy_bundle(data_dir, run, tmp_path)
    selected = tri_codes.select_nodes(root, run, codes_outputs_sha256=pin)
    selected.verify()
    case_changed_byte(directory, run, pin)
    with pytest.raises(ValueError, match='selected codes nodes changed'):
        selected.verify()


def test_verify_wraps_a_missing_bundle(codes, tmp_path):
    data_dir, run, pin = codes
    root, directory = copy_bundle(data_dir, run, tmp_path)
    selected = tri_codes.select_nodes(root, run, codes_outputs_sha256=pin)
    shutil.rmtree(directory)
    with pytest.raises(ValueError, match='selected codes nodes changed'):
        selected.verify()


@pytest.mark.parametrize('difference', [{'node_ids': frozenset()}, {'outputs': {}}])
def test_verify_refuses_a_selection_that_differs_from_the_bundle(codes, difference):
    data_dir, run, pin = codes
    selected = tri_codes.select_nodes(data_dir, run, codes_outputs_sha256=pin)
    stale = dataclasses.replace(selected, **difference)
    with pytest.raises(ValueError, match='selected codes nodes changed'):
        stale.verify()
