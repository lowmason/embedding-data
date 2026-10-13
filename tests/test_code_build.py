import json

import polars as pl
import pytest
from code_fixtures import seed_code_tree
from polars.testing import assert_frame_equal

from embedding_data import code_build, ita_summary, manifest, paths

def test_bundle_retains_duplicates_source_bytes_and_logical_determinism(tmp_path):
    registry = seed_code_tree(tmp_path)
    source = paths.derived_dir(tmp_path, 'osha') / ita_summary.TABLE_NAME
    pl.read_parquet(source).reverse().write_parquet(source)
    original_hash = manifest.sha256_file(source)
    one = code_build.build(tmp_path, 'fixture_one', registry=registry)
    two = code_build.build(tmp_path, 'fixture_two', registry=registry)
    assert manifest.sha256_file(source) == original_hash
    output = pl.read_parquet(one / 'ita_300a_canonical.parquet')
    assert output.height == 4
    assert_frame_equal(output.select(ita_summary.COLUMNS), pl.read_parquet(source))
    for filename in one.glob('*.parquet'):
        assert_frame_equal(pl.read_parquet(filename), pl.read_parquet(two / filename.name))
    diagnostics = json.loads((one / 'report.json').read_text())
    assert diagnostics['input_rows'] == 4
    checksums = json.loads((one / 'outputs.json').read_text())
    assert checksums['ita_300a_canonical.parquet']['sha256'] == manifest.sha256_file(
        one / 'ita_300a_canonical.parquet'
    )
    with pytest.raises(ValueError, match='exists'):
        code_build.build(tmp_path, 'fixture_one', registry=registry)


@pytest.mark.parametrize(
    'mutation, message',
    [
        (lambda df: df.with_columns(pl.lit('Changed').alias('company_name')), 'multiset'),
        (lambda df: df.slice(1), 'multiset'),
        (lambda df: pl.concat([df, df.head(1)]), 'multiset'),
        (lambda df: df.drop('naics_code'), 'schema'),
        (lambda df: df.with_columns(extra=pl.lit(1)), 'schema'),
        (lambda df: df.with_columns(pl.col('id').cast(pl.String)), 'schema'),
        (lambda df: df.with_columns(naics_year=pl.lit(1997, dtype=pl.Int64)), 'multiset'),
    ],
)
def test_changed_source_refused(tmp_path, mutation, message):
    registry = seed_code_tree(tmp_path)
    source = paths.derived_dir(tmp_path, 'osha') / ita_summary.TABLE_NAME
    mutation(pl.read_parquet(source)).write_parquet(source)
    original = source.read_bytes()
    with pytest.raises(ValueError, match=message):
        code_build.build(tmp_path, 'bad', registry=registry)
    assert source.read_bytes() == original
    assert not (paths.derived_dir(tmp_path, 'codes') / 'bad').exists()


@pytest.mark.parametrize('missing', [False, True])
def test_reference_bytes_verified_before_build(tmp_path, missing):
    from embedding_data import code_references as cr

    registry = seed_code_tree(tmp_path)
    original = cr.reference_path(tmp_path, registry['naics_2002'])
    if missing:
        original.unlink()
    else:
        original.write_bytes(b'corrupt')
    with pytest.raises((ValueError, FileNotFoundError)):
        code_build.build(tmp_path, 'bad', registry=registry)
    assert not (paths.derived_dir(tmp_path, 'codes') / 'bad').exists()


@pytest.mark.parametrize('name', ['../escape', '', '.hidden', 'x/y', 'á', 'run.part'])
def test_unsafe_run_ids_refused(tmp_path, name):
    with pytest.raises(ValueError, match='run ID'):
        code_build.build(tmp_path, name)


@pytest.mark.parametrize('suffix', ['', '.part'])
@pytest.mark.parametrize('symlink', [False, True])
def test_occupied_run_names_refused(tmp_path, suffix, symlink):
    root = paths.derived_dir(tmp_path, 'codes')
    root.mkdir(parents=True)
    occupied = root / ('occupied' + suffix)
    if symlink:
        occupied.symlink_to(tmp_path / 'absent')
    else:
        occupied.mkdir()
        (occupied / 'marker').write_text('retain')
    with pytest.raises(ValueError, match='exists'):
        code_build.build(tmp_path, 'occupied')
    assert occupied.is_symlink() if symlink else (occupied / 'marker').read_text() == 'retain'


def test_sink_failure_retains_prior_run_source_and_refuses_staging(tmp_path, monkeypatch):
    registry = seed_code_tree(tmp_path)
    first = code_build.build(tmp_path, 'first', registry=registry)
    frozen = {p.name: p.read_bytes() for p in first.iterdir()}
    source = paths.derived_dir(tmp_path, 'osha') / ita_summary.TABLE_NAME
    original = source.read_bytes()

    def fail(*args, **kwargs):
        raise OSError('injected disk write failure')

    monkeypatch.setattr(pl.LazyFrame, 'sink_parquet', fail)
    with pytest.raises(OSError, match='injected'):
        code_build.build(tmp_path, 'failed', registry=registry)
    assert source.read_bytes() == original
    assert frozen == {p.name: p.read_bytes() for p in first.iterdir()}
    root = paths.derived_dir(tmp_path, 'codes')
    assert not (root / 'failed').exists()
    assert (root / 'failed.part').is_dir()
    assert not list((root / 'failed.part').glob('**/*.csv'))
    with pytest.raises(ValueError, match='exists'):
        code_build.build(tmp_path, 'failed', registry=registry)


def test_new_selected_raw_release_refused(tmp_path):
    from ita_fixtures import write_release

    registry = seed_code_tree(tmp_path)
    directory = paths.raw_dir(tmp_path, 'osha') / 'summary/2023'
    (directory / 'fixture_2023.zip').unlink()
    write_release(tmp_path, 2023)
    with pytest.raises(ValueError, match='stale Stage 2'):
        code_build.build(tmp_path, 'stale', registry=registry)
    assert not (paths.derived_dir(tmp_path, 'codes') / 'stale').exists()


def test_source_year_inventory_must_be_contiguous(tmp_path):
    from ita_fixtures import write_release

    registry = seed_code_tree(tmp_path)
    write_release(tmp_path, 2025)
    (paths.raw_dir(tmp_path, 'osha') / 'summary/2023/fixture_2023.zip').unlink()
    (paths.raw_dir(tmp_path, 'osha') / 'summary/2023').rmdir()
    with pytest.raises(ValueError, match='incomplete source year inventory'):
        code_build.build(tmp_path, 'gap', registry=registry)
    assert not (paths.derived_dir(tmp_path, 'codes') / 'gap').exists()


def replace_fixture_raw(data_dir, old, new):
    from zipfile import ZipFile

    for file in (paths.raw_dir(data_dir, 'osha') / 'summary').glob('*/*.zip'):
        with ZipFile(file) as archive:
            text = archive.read('fixture.csv').decode()
        with ZipFile(file, 'w') as archive:
            archive.writestr('fixture.csv', text.replace(old, new))
    manifest_file = paths.manifest_path(data_dir)
    entries = [json.loads(line) for line in manifest_file.read_text().splitlines()]
    for entry in entries:
        file = manifest_file.parent / entry['path']
        entry['sha256'] = manifest.sha256_file(file)
        entry['size'] = file.stat().st_size
    manifest_file.write_text(''.join(json.dumps(entry) + '\n' for entry in entries))


@pytest.mark.parametrize('code', ['11111', '１１１１１２', '11111X'])
def test_matching_raw_malformed_code_refused(tmp_path, code):
    registry = seed_code_tree(tmp_path)
    replace_fixture_raw(tmp_path, '111112', code)
    source = paths.derived_dir(tmp_path, 'osha') / ita_summary.TABLE_NAME
    pl.read_parquet(source).with_columns(naics_code=pl.lit(code)).write_parquet(source)
    with pytest.raises(ValueError, match='not six digits'):
        code_build.build(tmp_path, 'bad', registry=registry)
    assert not (paths.derived_dir(tmp_path, 'codes') / 'bad').exists()


def test_corrupt_bridge_refused_even_when_source_codes_all_missing(tmp_path):
    from code_fixtures import pair_sheet, write_xlsx

    from embedding_data import code_references as cr

    registry = seed_code_tree(tmp_path)
    replace_fixture_raw(tmp_path, '111112', '')
    ita_summary.build_summary_table(tmp_path)  # Temporary fixture setup only.
    file = cr.reference_path(tmp_path, registry['concordance_2002_2007'])
    write_xlsx(
        file, [list(row) for row in pair_sheet(2002, 2007, [('111111', '111111')]).iter_rows()]
    )
    # Update only fixture provenance to exercise relationship validation, not the hash gate.
    mf = paths.manifest_path(tmp_path)
    entries = [json.loads(line) for line in mf.read_text().splitlines()]
    for entry in entries:
        if entry['path'] == file.relative_to(mf.parent).as_posix():
            entry['sha256'] = manifest.sha256_file(file)
            entry['size'] = file.stat().st_size
    mf.write_text(''.join(json.dumps(entry) + '\n' for entry in entries))
    with pytest.raises(ValueError, match='coverage'):
        code_build.build(tmp_path, 'bad', registry=registry)
    assert not (paths.derived_dir(tmp_path, 'codes') / 'bad').exists()


def test_complete_bundle_schemas_checksums_and_provenance(tmp_path, monkeypatch):
    from embedding_data import classification_tables as ct
    from embedding_data import filing_rules as fr
    from embedding_data import ita_naics_mapping as im
    from embedding_data import naics_relationships as nr

    registry = seed_code_tree(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError('production build must never rebuild the source')

    monkeypatch.setattr(ita_summary, 'build_summary_table', forbidden)
    run = code_build.build(tmp_path, 'complete', registry=registry)
    expected_schemas = {
        'naics_nodes': ct.NODE_SCHEMA,
        'naics_edges': ct.EDGE_SCHEMA,
        'soc_nodes': ct.NODE_SCHEMA,
        'soc_edges': ct.EDGE_SCHEMA,
        'naics_native_nodes': ct.NODE_SCHEMA,
        'naics_concordance': nr.RELATION_SCHEMA,
        'filing_rules': fr.RULE_SCHEMA,
        'code_paths': ct.PATH_SCHEMA,
        'filing_rule_labels': fr.LABEL_SCHEMA,
        'filing_rule_membership': fr.MEMBERSHIP_SCHEMA,
        'ita_naics_lookup': im.LOOKUP_SCHEMA,
        'ita_300a_canonical': {
            **code_build.SUMMARY_SCHEMA,
            **im.MAPPING_SCHEMA,
            **fr.FILING_COLUMNS,
        },
    }
    assert {file.name for file in run.iterdir()} == {
        *(name + '.parquet' for name in expected_schemas),
        'inputs.json',
        'report.json',
        'outputs.json',
    }
    diagnostics = json.loads((run / 'report.json').read_text())
    checksums = json.loads((run / 'outputs.json').read_text())
    assert set(checksums) == {p.name for p in run.iterdir()} - {'outputs.json'}
    for name, checksum in checksums.items():
        assert checksum == {
            'sha256': manifest.sha256_file(run / name),
            'size': (run / name).stat().st_size,
        }
    for name, schema in expected_schemas.items():
        frame = pl.read_parquet(run / (name + '.parquet'))
        assert frame.schema == schema
        assert diagnostics['tables'][name + '.parquet'] == {
            'rows': frame.height,
            'schema': {name: str(dtype) for name, dtype in schema.items()},
        }
    for partition in ['mapping', 'filing', 'candidate_counts']:
        assert sum(row['n'] for row in diagnostics[partition]) == 4
    assert len(diagnostics['rule_counts']) == 3
    inventory = json.loads((run / 'inputs.json').read_text())
    assert inventory['schema_version'] == diagnostics['schema_version'] == 'codes-ita-v1'
    assert inventory['run_id'] == 'complete'
    assert set(inventory['references']) == set(registry)
    assert len(inventory['raw']) == len(registry) + 2
    assert inventory['source_parquet']['sha256'] == manifest.sha256_file(
        paths.derived_dir(tmp_path, 'osha') / ita_summary.TABLE_NAME
    )
    for relative, digest in inventory['implementation'].items():
        assert digest == manifest.sha256_file(paths.PROJECT_ROOT / relative)
    assert inventory['uv_lock_sha256'] == manifest.sha256_file(paths.PROJECT_ROOT / 'uv.lock')
    assert set(inventory['dependencies']) == {
        'embedding-data',
        'polars',
        'fastexcel',
        'httpx',
        'typer',
    }


@pytest.mark.parametrize('changed', ['source', 'manifest', 'destination'])
def test_changes_at_publication_boundary_refused(tmp_path, monkeypatch, changed):
    registry = seed_code_tree(tmp_path)
    report = code_build.report

    def change_during_report(table):
        result = report(table)
        if changed == 'source':
            source = paths.derived_dir(tmp_path, 'osha') / ita_summary.TABLE_NAME
            pl.read_parquet(source).reverse().write_parquet(source)
        elif changed == 'manifest':
            mf = paths.manifest_path(tmp_path)
            mf.write_text(mf.read_text().replace('\n', ' \n'))
        else:
            destination = paths.derived_dir(tmp_path, 'codes') / 'race'
            destination.mkdir()
            (destination / 'marker').write_text('competing writer')
        return result

    monkeypatch.setattr(code_build, 'report', change_during_report)
    with pytest.raises(ValueError, match='changed during build|destination appeared'):
        code_build.build(tmp_path, 'race', registry=registry)
    final = paths.derived_dir(tmp_path, 'codes') / 'race'
    if changed == 'destination':
        assert {file.name for file in final.iterdir()} == {'marker'}
    else:
        assert not final.exists()


@pytest.mark.parametrize(
    'mutation, message',
    [
        (lambda df: df.with_columns(naics_mapping_status=pl.lit(None, dtype=pl.String)), 'null'),
        (
            lambda df: df.with_columns(
                naics_2022_candidates=pl.lit(None, dtype=pl.List(pl.String))
            ),
            'null',
        ),
        (lambda df: df.with_columns(flag_naics_ambiguous=pl.lit(False)), 'mapping state'),
        (lambda df: df.with_columns(naics_mapping_status=pl.lit('invented')), 'mapping state'),
        (lambda df: df.with_columns(naics_mapping_status=pl.lit('missing_code')), 'mapping state'),
        (
            lambda df: df.with_columns(
                naics_year=pl.lit(None, dtype=pl.Int64), naics_2022_code=pl.lit('111112')
            ),
            'mapping state',
        ),
        (lambda df: df.with_columns(extra=pl.lit(1)), 'schema'),
    ],
)
def test_invalid_canonical_output_refused(tmp_path, mutation, message):
    from embedding_data.filing_rules import FILING_COLUMNS
    from embedding_data.ita_naics_mapping import MAPPING_SCHEMA

    registry = seed_code_tree(tmp_path)
    run = code_build.build(tmp_path, 'source', registry=registry)
    invalid = tmp_path / 'invalid.parquet'
    mutation(pl.read_parquet(run / 'ita_300a_canonical.parquet')).write_parquet(invalid)
    schema = {**code_build.SUMMARY_SCHEMA, **MAPPING_SCHEMA, **FILING_COLUMNS}
    with pytest.raises(ValueError, match=message):
        code_build.validate_canonical(invalid, schema)
