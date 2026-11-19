'''The Stage 14 codes selector: the NAICS 2022 national industries of the pinned Stage 4 bundle.

Every mutated bundle is a copy of `derived/codes/<run>` alone in a fresh data root, so each
case also shows that the selector reads nothing outside the bundle.
'''

import dataclasses
import json
import re
import shutil
import subprocess
import sys

import polars as pl
import pytest
from vendor_link_fixtures import no_live_sam, seed_codes_bundle  # noqa: F401

from embedding_data import (
    classification_tables,
    code_build,
    manifest,
    target_inputs,
    target_io,
    vendor_link_codes,
)

UNSAFE_RUN = 'unsafe selected run ID'
BAD_PIN = 'invalid detached checksum'
PIN_DIFFERS = 'detached inventory checksum differs'
EXTRA_FILE = 'missing or extra inventory files'
HASH_DIFFERS = 'naics_edges.parquet: inventory hash or size differs'
INPUTS_VERSION = 'inputs.json schema version differs'
REPORT_VERSION = 'report.json schema version differs'
RUN_IDENTITY = 'inputs.json run identity differs'
NODE_SCHEMA = 'naics_nodes.parquet: ordered schema differs'
NODE_REPORT = 'naics_nodes.parquet: rows or schema differ from the report'
NODE_PREFIX = 'naics_nodes.parquet: a national-industry node ID lacks the 2022 prefix'
NODE_REPEAT = 'naics_nodes.parquet: a national-industry node ID repeats'
CHANGED = 'selected codes inputs changed'
NATIONAL = 'naics:2022:national_industry:'
OTHER_TABLES = [name for name in vendor_link_codes.CODE_TABLES if name != 'naics_nodes']


@pytest.fixture(scope='module')
def codes(tmp_path_factory):
    root = tmp_path_factory.mktemp('codes')
    run, pin = seed_codes_bundle(root / 'data', root / 'originals')
    return root / 'data', run, pin


def exactly(message):
    return pytest.raises(ValueError, match=f'^{re.escape(message)}$')


def bundle_copy(codes, tmp_path):
    '''Copy the codes bundle alone into a fresh data root: the data root and the bundle.'''
    data_dir, run, _ = codes
    copy = tmp_path / 'data'
    directory = copy / 'derived/codes' / run
    shutil.copytree(data_dir / 'derived/codes' / run, directory)
    return copy, directory


def repin(directory):
    '''Record the bytes of every inventory file in `outputs.json` and return the new pin.'''
    outputs_file = directory / 'outputs.json'
    outputs = json.loads(outputs_file.read_text())
    for name, stats in outputs.items():
        file = directory / name
        stats.update(sha256=manifest.sha256_file(file), size=file.stat().st_size)
    target_io.write_json(outputs_file, outputs)
    return manifest.sha256_file(outputs_file)


def edit_json(directory, name, change):
    file = directory / name
    value = json.loads(file.read_text())
    change(value)
    target_io.write_json(file, value)
    return repin(directory)


def edit_nodes(directory, change, *, sync_report=True):
    '''Rewrite `naics_nodes.parquet`, record it in the report unless told not to, and repin.'''
    file = directory / 'naics_nodes.parquet'
    frame = change(pl.read_parquet(file))
    frame.write_parquet(file)
    if not sync_report:
        return repin(directory)
    schema = {name: str(dtype) for name, dtype in frame.schema.items()}
    return edit_json(directory, 'report.json', lambda report: report['tables'][
        'naics_nodes.parquet'].update(rows=frame.height, schema=schema))


def node_row(node_id, *, system='naics', vintage=2022, level='national_industry'):
    return pl.DataFrame({'node_id': [node_id], 'system': [system], 'vintage': [vintage],
                         'level': [level], 'code': ['x'], 'title': ['Fixture']},
                        schema=vendor_link_codes.NODE_SCHEMA)


def with_rows(*rows):
    return lambda frame: pl.concat([frame, *rows])


def flip_last_byte(file):
    body = bytearray(file.read_bytes())
    body[-1] ^= 1
    file.write_bytes(bytes(body))


def national_ids(directory):
    nodes = pl.read_parquet(directory / 'naics_nodes.parquet')
    return set(nodes.filter(
        pl.col('system').eq('naics'), pl.col('vintage').eq(2022),
        pl.col('level').eq('national_industry'))['node_id'])


def select(data_dir, run, pin):
    return vendor_link_codes.select_nodes(data_dir, run, codes_outputs_sha256=pin)


def test_constants_match_stage4():
    assert set(vendor_link_codes.CODE_TABLES) == set(target_inputs.CODE_SCHEMAS)
    assert vendor_link_codes.NODE_SCHEMA == classification_tables.NODE_SCHEMA
    assert vendor_link_codes.CODES_SCHEMA_VERSION == code_build.SCHEMA_VERSION


def test_select_nodes_reads_the_national_industries(codes):
    data_dir, run, pin = codes
    selected = vendor_link_codes.select_nodes(data_dir, run, codes_outputs_sha256=pin)
    assert len(selected.node_ids) == 1012
    assert 'naics:2022:national_industry:541511' in selected.node_ids


def test_select_nodes_reads_no_ita_data(codes, tmp_path):
    data_dir, run, pin = codes
    copy = tmp_path / 'data'
    shutil.copytree(data_dir, copy)
    summary = copy / 'derived/osha/ita_300a_summary.parquet'
    assert summary.is_file()
    assert (copy / 'raw/osha').is_dir()
    summary.unlink()
    shutil.rmtree(copy / 'raw/osha')
    assert select(copy, run, pin).node_ids == select(data_dir, run, pin).node_ids


@pytest.mark.parametrize('mutation', ['run_id', 'pin_syntax', 'wrong_pin', 'extra_file',
                                      'changed_byte', 'schema_version', 'recorded_run_id'])
def test_select_nodes_refuses(codes, tmp_path, mutation):
    _, run, pin = codes
    copy, directory = bundle_copy(codes, tmp_path)
    message = {'run_id': UNSAFE_RUN, 'pin_syntax': BAD_PIN, 'wrong_pin': PIN_DIFFERS,
               'extra_file': EXTRA_FILE, 'changed_byte': HASH_DIFFERS,
               'schema_version': INPUTS_VERSION, 'recorded_run_id': RUN_IDENTITY}[mutation]
    if mutation == 'run_id':
        run = '../x'
    elif mutation == 'pin_syntax':
        pin = pin[:63]
    elif mutation == 'wrong_pin':
        pin = '0' * 64
    elif mutation == 'extra_file':
        (directory / 'extra.txt').write_text('x')
    elif mutation == 'changed_byte':
        flip_last_byte(directory / 'naics_edges.parquet')
    elif mutation == 'schema_version':
        pin = edit_json(directory, 'inputs.json',
                        lambda inputs: inputs.update(schema_version='codes-ita-v0'))
    else:
        pin = edit_json(directory, 'inputs.json',
                        lambda inputs: inputs.update(run_id='other_run'))
    with exactly(message):
        select(copy, run, pin)


def test_verify_detects_a_later_change(codes, tmp_path):
    _, run, pin = codes
    copy, directory = bundle_copy(codes, tmp_path)
    selected = select(copy, run, pin)
    assert selected.verify() is None
    flip_last_byte(directory / 'naics_nodes.parquet')
    with exactly(CHANGED):
        selected.verify()


def test_the_constants_are_the_briefed_literals():
    assert vendor_link_codes.CODE_TABLES == (
        'naics_nodes', 'naics_edges', 'soc_nodes', 'soc_edges', 'naics_native_nodes',
        'naics_concordance', 'filing_rules', 'code_paths', 'filing_rule_labels',
        'filing_rule_membership', 'ita_naics_lookup', 'ita_300a_canonical')
    assert vendor_link_codes.INVENTORY_NAMES == {
        *(name + '.parquet' for name in vendor_link_codes.CODE_TABLES),
        'inputs.json', 'report.json'}
    assert len(vendor_link_codes.INVENTORY_NAMES) == 14
    assert list(vendor_link_codes.NODE_SCHEMA.items()) == [
        ('node_id', pl.String), ('system', pl.String), ('vintage', pl.Int64),
        ('level', pl.String), ('code', pl.String), ('title', pl.String)]
    assert vendor_link_codes.NODE_PREFIX == NATIONAL
    assert vendor_link_codes.CODES_SCHEMA_VERSION == 'codes-ita-v1'
    assert vendor_link_codes.RUN_ID.pattern == '[A-Za-z0-9][A-Za-z0-9_-]*'
    assert vendor_link_codes.PIN.pattern == '[0-9a-f]{64}'


def test_the_node_ids_are_the_national_industry_rows_of_the_nodes_table(codes):
    data_dir, run, pin = codes
    selected = select(data_dir, run, pin)
    assert isinstance(selected.node_ids, frozenset)
    assert selected.node_ids == national_ids(data_dir / 'derived/codes' / run)
    assert all(node_id.startswith(NATIONAL) for node_id in selected.node_ids)
    assert (selected.data_dir, selected.codes_run, selected.codes_outputs_sha256) == (
        data_dir, run, pin)


def test_select_nodes_needs_only_the_codes_bundle(codes, tmp_path):
    _, run, pin = codes
    copy, _ = bundle_copy(codes, tmp_path)
    assert sorted(path.name for path in copy.iterdir()) == ['derived']
    assert len(select(copy, run, pin).node_ids) == 1012


@pytest.mark.parametrize('table', OTHER_TABLES)
def test_no_other_table_is_read(codes, tmp_path, table):
    data_dir, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    pl.DataFrame({'unrelated': [1, 2, 3]}).write_parquet(directory / (table + '.parquet'))
    pin = repin(directory)
    assert select(copy, run, pin).node_ids == national_ids(data_dir / 'derived/codes' / run)


def test_a_row_added_to_the_nodes_table_is_selected(codes, tmp_path):
    _, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    added = NATIONAL + '999990'
    pin = edit_nodes(directory, with_rows(node_row(added)))
    selected = select(copy, run, pin)
    assert added in selected.node_ids
    assert len(selected.node_ids) == 1013


@pytest.mark.parametrize('other', [
    pytest.param(node_row('naics:2017:national_industry:999991', vintage=2017), id='vintage'),
    pytest.param(node_row('soc:2022:national_industry:999992', system='soc'), id='system'),
    pytest.param(node_row('naics:2022:industry:9999', level='industry'), id='level'),
    pytest.param(node_row('naics:2022:national_industry:999993', system=None), id='no-system'),
    pytest.param(node_row('naics:2022:national_industry:999994', level=None), id='no-level'),
])
def test_rows_outside_the_filter_are_not_selected(codes, tmp_path, other):
    data_dir, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    pin = edit_nodes(directory, with_rows(other))
    assert select(copy, run, pin).node_ids == national_ids(data_dir / 'derived/codes' / run)


@pytest.mark.parametrize('node_id', [
    pytest.param('naics:2022:industry:5415', id='other-level'),
    pytest.param('naics:2017:national_industry:541511', id='other-vintage'),
    pytest.param('soc:2022:national_industry:541511', id='other-system'),
    pytest.param('NAICS:2022:national_industry:541511', id='upper-case'),
    pytest.param(' ' + NATIONAL + '541511', id='leading-space'),
    pytest.param('x' + NATIONAL + '541511', id='prefix-inside'),
    pytest.param('541511', id='bare-code'),
    pytest.param('', id='empty'),
    pytest.param(None, id='null'),
])
def test_a_node_id_without_the_prefix_is_refused(codes, tmp_path, node_id):
    _, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    pin = edit_nodes(directory, with_rows(node_row(node_id)))
    with exactly(NODE_PREFIX):
        select(copy, run, pin)


def test_a_repeated_node_id_is_refused(codes, tmp_path):
    _, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    pin = edit_nodes(directory, with_rows(node_row(NATIONAL + '541511')))
    with exactly(NODE_REPEAT):
        select(copy, run, pin)


def test_a_node_id_repeated_outside_the_national_industries_is_accepted(codes, tmp_path):
    data_dir, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    repeated = node_row('naics:2022:industry:5415', level='industry')
    pin = edit_nodes(directory, with_rows(repeated, repeated))
    assert select(copy, run, pin).node_ids == national_ids(data_dir / 'derived/codes' / run)


def reverse_columns(frame):
    return frame.select(frame.columns[::-1])


@pytest.mark.parametrize('change', [
    pytest.param(reverse_columns, id='column-order'),
    pytest.param(lambda frame: frame.with_columns(pl.col('vintage').cast(pl.Int32)),
                 id='column-type'),
    pytest.param(lambda frame: frame.with_columns(extra=pl.lit('x')), id='extra-column'),
    pytest.param(lambda frame: frame.drop('title'), id='missing-column'),
    pytest.param(lambda frame: frame.rename({'code': 'Code'}), id='renamed-column'),
])
@pytest.mark.parametrize('sync_report', [True, False], ids=['report-matches', 'report-stale'])
def test_the_node_schema_must_be_exact_and_ordered(codes, tmp_path, change, sync_report):
    _, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    pin = edit_nodes(directory, change, sync_report=sync_report)
    with exactly(NODE_SCHEMA):
        select(copy, run, pin)


def drop_a_row(frame):
    return frame.head(frame.height - 1)


def tables_missing(report):
    del report['tables']


def tables_not_an_object(report):
    report['tables'] = []


def entry_missing(report):
    del report['tables']['naics_nodes.parquet']


def entry_not_an_object(report):
    report['tables']['naics_nodes.parquet'] = 'rows'


def rows_one_more(report):
    report['tables']['naics_nodes.parquet']['rows'] += 1


def rows_missing(report):
    del report['tables']['naics_nodes.parquet']['rows']


def schema_differs(report):
    report['tables']['naics_nodes.parquet']['schema']['vintage'] = 'Int32'


def schema_missing(report):
    del report['tables']['naics_nodes.parquet']['schema']


def schema_extra_column(report):
    report['tables']['naics_nodes.parquet']['schema']['extra'] = 'String'


@pytest.mark.parametrize('edit', [
    tables_missing, tables_not_an_object, entry_missing, entry_not_an_object, rows_one_more,
    rows_missing, schema_differs, schema_missing, schema_extra_column,
])
def test_the_nodes_must_equal_the_report(codes, tmp_path, edit):
    _, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    pin = edit_json(directory, 'report.json', edit)
    with exactly(NODE_REPORT):
        select(copy, run, pin)


def test_the_nodes_rows_must_equal_the_report(codes, tmp_path):
    _, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    pin = edit_nodes(directory, drop_a_row, sync_report=False)
    with exactly(NODE_REPORT):
        select(copy, run, pin)


def inputs_version_dropped(directory):
    return edit_json(directory, 'inputs.json', lambda inputs: inputs.pop('schema_version'))


def report_version_dropped(directory):
    return edit_json(directory, 'report.json', lambda report: report.pop('schema_version'))


def run_identity_dropped(directory):
    return edit_json(directory, 'inputs.json', lambda inputs: inputs.pop('run_id'))


@pytest.mark.parametrize(('edit', 'message'), [
    pytest.param(lambda d: edit_json(d, 'inputs.json', lambda value: value.update(
        schema_version='codes-ita-v0')), INPUTS_VERSION, id='inputs-version'),
    pytest.param(lambda d: edit_json(d, 'inputs.json', lambda value: value.update(
        schema_version='codes-ita-v1 ')), INPUTS_VERSION, id='inputs-version-padded'),
    pytest.param(inputs_version_dropped, INPUTS_VERSION, id='inputs-version-dropped'),
    pytest.param(lambda d: edit_json(d, 'report.json', lambda value: value.update(
        schema_version='codes-ita-v0')), REPORT_VERSION, id='report-version'),
    pytest.param(report_version_dropped, REPORT_VERSION, id='report-version-dropped'),
    pytest.param(lambda d: edit_json(d, 'inputs.json', lambda value: value.update(
        run_id='other_run')), RUN_IDENTITY, id='run-identity'),
    pytest.param(run_identity_dropped, RUN_IDENTITY, id='run-identity-dropped'),
])
def test_the_schema_version_and_run_identity_are_checked(codes, tmp_path, edit, message):
    _, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    with exactly(message):
        select(copy, run, edit(directory))


@pytest.mark.parametrize('name', ['outputs.json', 'inputs.json', 'report.json'])
def test_a_json_file_that_is_not_an_object_is_refused(codes, tmp_path, name):
    _, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    if name == 'outputs.json':
        (directory / name).write_text('[]')
        pin = manifest.sha256_file(directory / name)
    else:
        pin = edit_json_text(directory, name, '[]')
    with exactly(f'{name}: not a JSON object'):
        select(copy, run, pin)


def edit_json_text(directory, name, text):
    (directory / name).write_text(text)
    return repin(directory)


@pytest.mark.parametrize(('run_id', 'edit_pin'), [
    pytest.param('../x', lambda pin: pin, id='traversal'),
    pytest.param('fixture_codes/..', lambda pin: pin, id='trailing-traversal'),
    pytest.param('fixture_codes\n', lambda pin: pin, id='trailing-newline'),
    pytest.param('fixture codes', lambda pin: pin, id='space'),
    pytest.param('-fixture_codes', lambda pin: pin, id='leading-hyphen'),
    pytest.param('_fixture_codes', lambda pin: pin, id='leading-underscore'),
    pytest.param('', lambda pin: pin, id='empty'),
])
def test_an_unsafe_run_id_is_refused_before_anything_is_read(tmp_path, run_id, edit_pin):
    with exactly(UNSAFE_RUN):
        select(tmp_path, run_id, edit_pin('a' * 64))


@pytest.mark.parametrize('edit_pin', [
    pytest.param(lambda pin: pin[:63], id='63-characters'),
    pytest.param(lambda pin: pin + '0', id='65-characters'),
    pytest.param(lambda pin: pin.upper(), id='uppercase'),
    pytest.param(lambda pin: 'g' * 64, id='not-hex'),
    pytest.param(lambda pin: pin + '\n', id='trailing-newline'),
    pytest.param(lambda pin: ' ' + pin[1:], id='space'),
    pytest.param(lambda pin: '', id='empty'),
])
def test_a_pin_of_the_wrong_shape_is_refused_before_anything_is_read(tmp_path, edit_pin):
    with exactly(BAD_PIN):
        select(tmp_path, 'fixture_codes', edit_pin('a' * 64))


def test_a_run_id_is_refused_before_a_pin_of_the_wrong_shape(tmp_path):
    with exactly(UNSAFE_RUN):
        select(tmp_path, '../x', 'short')


def test_a_symlinked_codes_root_is_refused(codes, tmp_path):
    _, run, pin = codes
    copy, directory = bundle_copy(codes, tmp_path)
    root = directory.parent
    root.rename(tmp_path / 'elsewhere')
    root.symlink_to(tmp_path / 'elsewhere', target_is_directory=True)
    with pytest.raises(ValueError, match='symlink in registered destination'):
        select(copy, run, pin)


def remove_a_table_from_the_bundle(directory):
    (directory / 'code_paths.parquet').unlink()
    outputs = json.loads((directory / 'outputs.json').read_text())
    del outputs['code_paths.parquet']
    target_io.write_json(directory / 'outputs.json', outputs)
    return repin(directory)


def list_an_extra_file_in_the_bundle(directory):
    (directory / 'extra.txt').write_text('x')
    outputs = json.loads((directory / 'outputs.json').read_text())
    outputs['extra.txt'] = {'sha256': '0', 'size': 0}
    target_io.write_json(directory / 'outputs.json', outputs)
    return repin(directory)


@pytest.mark.parametrize(
    'edit', [remove_a_table_from_the_bundle, list_an_extra_file_in_the_bundle],
    ids=['table-removed', 'extra-file-listed'])
def test_the_inventory_must_name_exactly_the_bundle_files(codes, tmp_path, edit):
    _, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    with exactly(EXTRA_FILE):
        select(copy, run, edit(directory))


def test_the_pin_is_checked_before_the_inventory(codes, tmp_path):
    _, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    (directory / 'extra.txt').write_text('x')
    with exactly(PIN_DIFFERS):
        select(copy, run, '0' * 64)


def test_the_inventory_is_checked_before_the_versions(codes, tmp_path):
    _, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    pin = edit_json(directory, 'inputs.json',
                    lambda inputs: inputs.update(schema_version='codes-ita-v0'))
    (directory / 'extra.txt').write_text('x')
    with exactly(EXTRA_FILE):
        select(copy, run, pin)


def test_the_versions_are_checked_before_the_node_schema(codes, tmp_path):
    _, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    edit_nodes(directory, reverse_columns)
    pin = edit_json(directory, 'inputs.json',
                    lambda inputs: inputs.update(schema_version='codes-ita-v0'))
    with exactly(INPUTS_VERSION):
        select(copy, run, pin)


def test_the_node_schema_is_checked_before_the_report(codes, tmp_path):
    _, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    pin = edit_nodes(directory, lambda frame: frame.with_columns(pl.col('vintage').cast(pl.Int32)),
                     sync_report=False)
    with exactly(NODE_SCHEMA):
        select(copy, run, pin)


def test_the_report_is_checked_before_the_node_ids(codes, tmp_path):
    _, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    pin = edit_nodes(directory, with_rows(node_row('541511')), sync_report=False)
    with exactly(NODE_REPORT):
        select(copy, run, pin)


def test_the_prefix_is_checked_before_a_repeat(codes, tmp_path):
    _, run, _ = codes
    copy, directory = bundle_copy(codes, tmp_path)
    repeated = node_row('541511')
    pin = edit_nodes(directory, with_rows(repeated, repeated))
    with exactly(NODE_PREFIX):
        select(copy, run, pin)


def test_verify_returns_none_for_an_unchanged_selection(codes):
    data_dir, run, pin = codes
    assert select(data_dir, run, pin).verify() is None


@pytest.mark.parametrize('change', [
    pytest.param(lambda directory: flip_last_byte(directory / 'naics_nodes.parquet'),
                 id='nodes-byte'),
    pytest.param(lambda directory: flip_last_byte(directory / 'soc_edges.parquet'),
                 id='other-table-byte'),
    pytest.param(lambda directory: (directory / 'extra.txt').write_text('x'), id='extra-file'),
    pytest.param(lambda directory: (directory / 'report.json').unlink(), id='file-removed'),
    pytest.param(lambda directory: (directory / 'outputs.json').unlink(),
                 id='outputs-removed'),
    pytest.param(lambda directory: shutil.rmtree(directory), id='bundle-removed'),
])
def test_verify_refuses_a_later_change_with_one_fixed_reason(codes, tmp_path, change):
    _, run, pin = codes
    copy, directory = bundle_copy(codes, tmp_path)
    selected = select(copy, run, pin)
    change(directory)
    with exactly(CHANGED):
        selected.verify()


@pytest.mark.parametrize('field', ['node_ids', 'outputs'])
def test_verify_compares_the_reselection_with_the_selected_value(codes, field):
    data_dir, run, pin = codes
    selected = select(data_dir, run, pin)
    altered = {'node_ids': selected.node_ids - {NATIONAL + '541511'},
               'outputs': {**selected.outputs, 'extra.json': {}}}[field]
    with exactly(CHANGED):
        dataclasses.replace(selected, **{field: altered}).verify()


def test_provenance_is_the_run_the_pin_and_the_outputs(codes):
    data_dir, run, pin = codes
    selected = select(data_dir, run, pin)
    outputs = json.loads((data_dir / 'derived/codes' / run / 'outputs.json').read_text())
    assert selected.outputs == outputs
    assert selected.provenance() == {'run_id': run, 'outputs_sha256': pin,
                                     'outputs': outputs}


def test_a_selection_is_frozen_and_has_the_briefed_fields(codes):
    data_dir, run, pin = codes
    selected = select(data_dir, run, pin)
    assert [field.name for field in dataclasses.fields(selected)] == [
        'data_dir', 'codes_run', 'codes_outputs_sha256', 'outputs', 'node_ids']
    with pytest.raises(dataclasses.FrozenInstanceError):
        selected.codes_run = 'other'


def test_the_selector_imports_no_upstream_builder_or_credential_library():
    # `target_io` loads `ita_summary` through `ita_references`, so that module is not listed.
    code = ('import sys; import embedding_data.vendor_link_codes as m; '
            'bad = sorted(n for n in sys.modules if n.split(".")[0] in {"dotenv", "ipumspy"} '
            'or n in {"embedding_data.code_build", "embedding_data.target_inputs", '
            '"embedding_data.classification_tables"} '
            'or n.startswith(("embedding_data.ita_establishment", "embedding_data.ipums", '
            '"embedding_data.acs"))); print(bad); sys.exit(1 if bad else 0)')
    done = subprocess.run([sys.executable, '-c', code], check=False, capture_output=True,
                          text=True)
    assert (done.returncode, done.stdout.strip()) == (0, '[]')
