import dataclasses
import json
import shutil
import subprocess
import sys
from dataclasses import asdict

import polars as pl
import pytest
from target_fixtures import corrupt_selected, seed_inputs

from embedding_data import (
    code_build,
    ita_establishment_inputs,
    ita_summary,
    manifest,
    paths,
    target_inputs,
    target_io,
)
from embedding_data.ita_establishment_inputs import SelectedCodes, merge_citations, select_codes

RUN = 'fixture_codes'


def pin_of(seeded):
    return seeded.provenance['codes']['outputs_sha256']


def select_seeded(tmp_path, seeded):
    return select_codes(tmp_path, RUN, codes_outputs_sha256=pin_of(seeded))


def codes_directory(data_dir):
    return data_dir / 'derived/codes' / RUN


def repin(directory):
    '''Record the bytes of every inventory file in outputs.json, as corrupt_selected does.'''
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


def edit_table(directory, name, change, *, record_schema=False):
    '''Rewrite one Parquet, optionally record its new schema in the report, and repin.'''
    file = directory / (name + '.parquet')
    change(pl.read_parquet(file)).write_parquet(file)
    if not record_schema:
        return repin(directory)
    schema = {column: str(dtype) for column, dtype in pl.read_parquet(file).schema.items()}
    return edit_json(directory, 'report.json',
                     lambda report: report['tables'][file.name].update(schema=schema))


def edit_inputs(change):
    return lambda data_dir, directory: edit_json(directory, 'inputs.json', change)


def edit_report(change):
    return lambda data_dir, directory: edit_json(directory, 'report.json', change)


def drop_key(key):
    return lambda value: value.pop(key)


def drop_citation(value):
    value['raw'] = [c for c in value['raw'] if '/2023/' not in c['path']]


def alter_citation(value):
    value['raw'][-1]['client'] = 'changed'


def unrecord_citation(value):
    value['raw'][-1]['path'] = 'references/naics/never_recorded.xlsx'


def point_source_at_a_copy(data_dir, directory):
    summary = data_dir / 'derived/osha' / ita_summary.TABLE_NAME
    shutil.copyfile(summary, summary.with_name('copy.parquet'))
    return edit_json(directory, 'inputs.json', lambda value: value['source_parquet'].update(
        path='derived/osha/copy.parquet'))


def change_reference_bytes(data_dir, directory):
    file = data_dir / 'raw/references/naics/fixture_2022.xlsx'
    file.write_bytes(file.read_bytes() + b'changed')
    return None


def reverse_columns(frame):
    return frame.select(frame.columns[::-1])


def narrow_vintage(frame):
    return frame.with_columns(pl.col('vintage').cast(pl.Int32))


def snapshot_tree(root):
    return {file.relative_to(root).as_posix(): (file.stat().st_size, file.stat().st_mtime_ns)
            for file in root.rglob('*')}


def test_selects_pinned_codes_bundle(tmp_path):
    seeded = seed_inputs(tmp_path)
    selected = select_seeded(tmp_path, seeded)
    assert isinstance(selected, SelectedCodes)
    assert set(selected.tables) == set(target_inputs.CODE_SCHEMAS)
    assert selected.provenance['source_rows'] == 21
    raw = {citation['path'] for citation in selected.provenance['raw']}
    releases = ita_summary.summary_files(tmp_path)
    assert len(releases) == 10
    assert {file.relative_to(tmp_path / 'raw').as_posix() for file in releases.values()} <= raw


def test_selection_records_paths_and_provenance(tmp_path):
    seeded = seed_inputs(tmp_path)
    pin = pin_of(seeded)
    selected = select_seeded(tmp_path, seeded)
    directory = codes_directory(tmp_path)
    assert (selected.data_dir, selected.codes_run, selected.codes_outputs_sha256) == (
        tmp_path, RUN, pin)
    assert selected.directory == directory
    assert selected.tables == {
        name: directory / (name + '.parquet') for name in target_inputs.CODE_SCHEMAS}
    assert selected.summary == tmp_path / 'derived/osha' / ita_summary.TABLE_NAME
    provenance = selected.provenance
    assert set(provenance) == {
        'codes', 'raw', 'source_parquet', 'canonical', 'source_years', 'source_rows'}
    assert provenance['codes'] == {
        'run_id': RUN, 'outputs_sha256': pin,
        'outputs': json.loads((directory / 'outputs.json').read_text())}
    assert provenance['source_parquet'] == {
        'path': 'derived/osha/ita_300a_summary.parquet', **target_io.file_record(selected.summary)}
    assert provenance['canonical'] == {
        'path': 'derived/codes/fixture_codes/ita_300a_canonical.parquet',
        **target_io.file_record(selected.tables['ita_300a_canonical'])}
    assert provenance['source_years'] == list(range(2016, 2026))
    assert type(provenance['source_rows']) is int


def test_raw_provenance_lists_verified_citations_sorted_by_path(tmp_path):
    seeded = seed_inputs(tmp_path)
    raw = select_seeded(tmp_path, seeded).provenance['raw']
    assert [citation['path'] for citation in raw] == sorted(c['path'] for c in raw)
    for citation in raw:
        current = manifest.entry_for(paths.manifest_path(tmp_path),
                                     tmp_path / 'raw' / citation['path'])
        assert citation == json.loads(json.dumps(asdict(current)))
    bundle = json.loads((codes_directory(tmp_path) / 'inputs.json').read_text())
    assert raw == bundle['raw']


def test_selected_codes_is_immutable(tmp_path):
    selected = select_seeded(tmp_path, seed_inputs(tmp_path))
    with pytest.raises(dataclasses.FrozenInstanceError):
        selected.codes_run = 'other'


def test_needs_no_geography(tmp_path):
    seeded = seed_inputs(tmp_path)
    shutil.rmtree(tmp_path / 'derived/geography/fixture_geography')
    assert select_seeded(tmp_path, seeded).provenance['source_rows'] == 21


def test_needs_no_geography_bundle_or_originals(tmp_path, monkeypatch):
    seeded = seed_inputs(tmp_path)
    shutil.rmtree(tmp_path / 'derived/geography')
    shutil.rmtree(tmp_path / 'raw/references/geography')
    shutil.rmtree(tmp_path / 'raw/references/hud')
    for name in ('select', '_bundle', '_validate_geography'):
        monkeypatch.setattr(target_inputs, name, lambda *a, **k: pytest.fail('needs geography'))
    assert select_seeded(tmp_path, seeded).provenance['source_rows'] == 21


@pytest.mark.parametrize('defect', [
    'detached_hash', 'file_hash', 'size', 'missing_file', 'extra_file', 'schema', 'row_count',
    'raw_bytes', 'source_hash', 'source_order', 'canonical_order', 'native_flags',
    'native_node_level',
])
def test_selected_defects_are_refused(tmp_path, defect):
    seeded = seed_inputs(tmp_path)
    corrupt_selected(tmp_path, seeded, defect)
    with pytest.raises((ValueError, FileNotFoundError)):
        select_seeded(tmp_path, seeded)


@pytest.mark.parametrize(('edit', 'message'), [
    pytest.param(edit_inputs(lambda value: value.update(schema_version='codes-ita-v0')),
                 'schema version', id='inputs-schema-version'),
    pytest.param(edit_report(lambda value: value.update(schema_version='codes-ita-v0')),
                 'schema version', id='report-schema-version'),
    pytest.param(edit_inputs(lambda value: value.update(run_id='other_run')),
                 'run identity', id='inputs-run-id'),
    pytest.param(edit_inputs(drop_key('source_parquet')), 'required fields',
                 id='inputs-missing-key'),
    pytest.param(edit_report(drop_key('tables')), 'required fields', id='report-missing-key'),
    pytest.param(edit_report(lambda value: value['tables'].pop('soc_edges.parquet')),
                 'report table', id='report-missing-table'),
    pytest.param(edit_report(lambda value: value['tables'].update(
        {'extra.parquet': {'rows': 0, 'schema': {}}})), 'report table', id='report-extra-table'),
    pytest.param(lambda d, c: edit_table(c, 'soc_edges', reverse_columns), 'ordered schema',
                 id='column-order'),
    pytest.param(lambda d, c: edit_table(c, 'naics_nodes', narrow_vintage, record_schema=True),
                 'ordered schema', id='column-type'),
    pytest.param(edit_inputs(drop_citation), 'source release', id='citation-missing'),
    pytest.param(edit_inputs(alter_citation), 'provenance changed', id='citation-changed'),
    pytest.param(edit_inputs(unrecord_citation), 'not recorded', id='citation-unrecorded'),
    pytest.param(change_reference_bytes, 'differs', id='reference-bytes'),
    pytest.param(point_source_at_a_copy, 'source path', id='source-path'),
    pytest.param(edit_inputs(lambda value: value['source_parquet'].update(
        size=value['source_parquet']['size'] + 1)), 'source hash or size', id='source-size'),
    pytest.param(edit_inputs(lambda value: value['source_parquet'].update(sha256='0' * 64)),
                 'source hash or size', id='source-sha256'),
])
def test_bundle_defects_are_refused_with_a_fixed_reason(tmp_path, edit, message):
    seeded = seed_inputs(tmp_path)
    pin = edit(tmp_path, codes_directory(tmp_path)) or pin_of(seeded)
    with pytest.raises(ValueError, match=message):
        select_codes(tmp_path, RUN, codes_outputs_sha256=pin)


@pytest.mark.parametrize(('run_id', 'edit_pin', 'message'), [
    pytest.param('../x', lambda pin: pin, 'run ID', id='run-traversal'),
    pytest.param('fixture_codes/..', lambda pin: pin, 'run ID', id='run-trailing-traversal'),
    pytest.param('fixture_codes\n', lambda pin: pin, 'run ID', id='run-trailing-newline'),
    pytest.param('-fixture_codes', lambda pin: pin, 'run ID', id='run-leading-hyphen'),
    pytest.param('', lambda pin: pin, 'run ID', id='run-empty'),
    pytest.param(RUN, lambda pin: pin[:63], 'checksum', id='pin-63-characters'),
    pytest.param(RUN, lambda pin: pin + '0', 'checksum', id='pin-65-characters'),
    pytest.param(RUN, lambda pin: pin.upper(), 'checksum', id='pin-uppercase'),
    pytest.param(RUN, lambda pin: 'g' * 64, 'checksum', id='pin-not-hex'),
    pytest.param(RUN, lambda pin: '0' * 64, 'checksum differs', id='pin-wrong-digest'),
])
def test_unsafe_run_id_and_pin_refused(tmp_path, run_id, edit_pin, message):
    seeded = seed_inputs(tmp_path)
    with pytest.raises(ValueError, match=message):
        select_codes(tmp_path, run_id, codes_outputs_sha256=edit_pin(pin_of(seeded)))


def test_symlinked_codes_root_is_refused(tmp_path):
    seeded = seed_inputs(tmp_path)
    root = tmp_path / 'derived/codes'
    root.rename(tmp_path / 'elsewhere')
    root.symlink_to(tmp_path / 'elsewhere', target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        select_seeded(tmp_path, seeded)


@pytest.mark.parametrize('change', [
    pytest.param(lambda f: f.filter(pl.col('year_filing_for').ne(2016)), id='missing-first'),
    pytest.param(lambda f: f.filter(pl.col('year_filing_for').ne(2020)), id='missing-middle'),
    pytest.param(lambda f: f.filter(pl.col('year_filing_for').ne(2025)), id='missing-last'),
    pytest.param(lambda f: pl.concat([f, f.filter(pl.col('year_filing_for').eq(2025)).with_columns(
        year_filing_for=pl.lit(2026, dtype=pl.Int64))]), id='extra-after'),
    pytest.param(lambda f: pl.concat([f, f.filter(pl.col('year_filing_for').eq(2016)).with_columns(
        year_filing_for=pl.lit(2015, dtype=pl.Int64))]), id='extra-before'),
])
def test_source_years_must_be_exactly_2016_through_2025(tmp_path, monkeypatch, change):
    seeded = seed_inputs(tmp_path)
    real = code_build.check_source
    monkeypatch.setattr(code_build, 'check_source', lambda data_dir, work: (
        lambda checked: (change(checked[0]), checked[1]))(real(data_dir, work)))
    with pytest.raises(ValueError, match='2016 through 2025'):
        select_seeded(tmp_path, seeded)


@pytest.mark.parametrize('change', [
    pytest.param(lambda citations: [{**citations[0], 'client': 'other'}, *citations[1:]],
                 id='differs'),
    pytest.param(lambda citations: [*citations, {**citations[0], 'path': 'osha/summary/9/x.zip'}],
                 id='not-in-bundle'),
])
def test_source_citations_must_equal_the_bundle_citations(tmp_path, monkeypatch, change):
    seeded = seed_inputs(tmp_path)
    real = code_build.check_source
    monkeypatch.setattr(code_build, 'check_source', lambda data_dir, work: (
        lambda checked: (checked[0], change(checked[1])))(real(data_dir, work)))
    with pytest.raises(ValueError, match='source release'):
        select_seeded(tmp_path, seeded)


def test_source_check_runs_twice_in_a_temporary_directory_outside_the_data_tree(
        tmp_path, monkeypatch):
    seeded = seed_inputs(tmp_path)
    real = code_build.check_source
    seen = []

    def spy(data_dir, work):
        assert work.is_dir() and not any(work.iterdir())
        assert work != data_dir and not work.is_relative_to(data_dir)
        seen.append(work)
        return real(data_dir, work)

    monkeypatch.setattr(code_build, 'check_source', spy)
    select_seeded(tmp_path, seeded)
    assert len(seen) == 2
    assert not any(work.exists() for work in seen)


def test_selection_writes_nothing_under_the_data_tree(tmp_path):
    seeded = seed_inputs(tmp_path)
    before = snapshot_tree(tmp_path)
    select_seeded(tmp_path, seeded)
    assert snapshot_tree(tmp_path) == before


def test_snapshots_that_differ_are_refused(tmp_path, monkeypatch):
    seeded = seed_inputs(tmp_path)
    real = ita_establishment_inputs._snapshot
    calls = []

    def changing(*args):
        selected = real(*args)
        calls.append(selected)
        if len(calls) == 2:
            return dataclasses.replace(
                selected, provenance={**selected.provenance, 'source_rows': 22})
        return selected

    monkeypatch.setattr(ita_establishment_inputs, '_snapshot', changing)
    with pytest.raises(ValueError, match='changed during validation'):
        select_seeded(tmp_path, seeded)
    assert len(calls) == 2


def test_verify_accepts_an_unchanged_selection(tmp_path):
    selected = select_seeded(tmp_path, seed_inputs(tmp_path))
    assert selected.verify() is None


def test_verify_detects_change(tmp_path):
    seeded = seed_inputs(tmp_path)
    selected = select_seeded(tmp_path, seeded)
    edit_json(codes_directory(tmp_path), 'report.json', lambda report: report.update(note='x'))
    with pytest.raises(ValueError, match='selected codes inputs changed'):
        selected.verify()


def test_verify_compares_the_reselection_with_the_selected_value(tmp_path):
    selected = select_seeded(tmp_path, seed_inputs(tmp_path))
    altered = dataclasses.replace(
        selected, provenance={**selected.provenance, 'source_rows': 22})
    with pytest.raises(ValueError, match='^selected codes inputs changed$'):
        altered.verify()


def test_merge_citations_sorts_by_path_and_collapses_equal_citations():
    late = {'path': 'b/late', 'sha256': '1'}
    early = {'path': 'a/early', 'sha256': '2'}
    assert merge_citations([late, early], [dict(late)]) == [early, late]


@pytest.mark.parametrize('groups', [
    pytest.param([[{'path': 'a', 'sha256': '1'}], [{'path': 'a', 'sha256': '2'}]],
                 id='across-groups'),
    pytest.param([[{'path': 'a', 'sha256': '1'}, {'path': 'a', 'sha256': '2'}]],
                 id='within-a-group'),
])
def test_merge_citations_refuses_a_path_cited_twice_with_different_content(groups):
    with pytest.raises(ValueError, match='conflicting citations'):
        merge_citations(*groups)


def test_selector_loads_no_ipums_or_dotenv_module():
    code = ('import sys; import embedding_data.ita_establishment_inputs as m; '
            'bad = [n for n in sys.modules if n.split(".")[0] in {"dotenv", "ipumspy"} '
            'or n.startswith(("embedding_data.ipums", "embedding_data.acs"))]; '
            'sys.exit(1 if bad else 0)')
    assert subprocess.run([sys.executable, '-c', code], check=False).returncode == 0
