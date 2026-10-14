import polars as pl
import pytest
from polars.testing import assert_frame_equal

from embedding_data import target_contract as tc
from embedding_data.target_io import file_record

def target_rows():
    rows = []
    for code, share, count in [('111111', 0.75, 3), ('111112', 0.25, 1)]:
        rows.append(dict(source='fixture', family='area_mix', unit_a_type='county',
                         unit_a='geography:2025:county:01001',
                         unit_b_type='naics_national_industry',
                         unit_b='naics:2022:national_industry:' + code,
                         measure='fixture_share', value=share, se=None, se_method='none',
                         n_unweighted=count, n_weighted=float(count), sample_set='fixture',
                         vintage='naics=2022;county=2025', universe='Fixture conditional universe',
                         flags=[]))
    return pl.DataFrame(rows, schema=tc.TARGET_SCHEMA)


@pytest.mark.parametrize('lazy', [False, True])
def test_exact_schema_and_keys(lazy):
    frame = target_rows()
    assert list(tc.TARGET_SCHEMA) == ['source', 'family', 'unit_a_type', 'unit_a',
        'unit_b_type', 'unit_b', 'measure', 'value', 'se', 'se_method', 'n_unweighted',
        'n_weighted', 'sample_set', 'vintage', 'universe', 'flags']
    assert tc.SCHEMA_VERSION == 'targets-v1'
    assert tc.TARGET_KEY_COLUMNS == [c for c in tc.TARGET_SCHEMA if c not in
                                   {'value', 'se', 'n_unweighted', 'n_weighted', 'flags'}]
    tc.validate_targets(frame.lazy() if lazy else frame)
    tc.validate_targets(frame.head(0))


@pytest.mark.parametrize('column', list(['source', 'family', 'unit_a_type', 'unit_a',
    'unit_b_type', 'unit_b', 'measure', 'value', 'se', 'se_method', 'n_unweighted',
    'n_weighted', 'sample_set', 'vintage', 'universe', 'flags']))
def test_rejects_schema_changes(column):
    frame = target_rows()
    variants = [frame.drop(column), frame.select(list(reversed(frame.columns))),
                frame.with_columns(pl.lit(1 if tc.TARGET_SCHEMA[column] == pl.String
                                          else 'wrong type').alias(column)),
                frame.with_columns(pl.lit('extra').alias('extra'))]
    for variant in variants:
        if list(variant.schema.items()) == list(tc.TARGET_SCHEMA.items()):
            continue
        with pytest.raises(ValueError, match='schema'):
            tc.validate_targets(variant)


@pytest.mark.parametrize('column', [c for c in ['source', 'family', 'unit_a_type', 'unit_a',
    'unit_b_type', 'unit_b', 'measure', 'value', 'se_method', 'n_unweighted', 'n_weighted',
    'sample_set', 'vintage', 'universe', 'flags']])
def test_rejects_null_required_columns(column):
    with pytest.raises(ValueError):
        tc.validate_targets(target_rows().with_columns(
            pl.lit(None, dtype=tc.TARGET_SCHEMA[column]).alias(column)))


@pytest.mark.parametrize('column', ['source', 'family', 'unit_a_type', 'unit_a',
    'unit_b_type', 'unit_b', 'measure', 'se_method', 'sample_set', 'vintage', 'universe'])
def test_rejects_blank_metadata(column):
    with pytest.raises(ValueError):
        tc.validate_targets(target_rows().with_columns(pl.lit(' \t').alias(column)))


@pytest.mark.parametrize('kind,value', [
    ('county', 'geography:2025:state:01001'), ('county', 'geography:25:county:01001'),
    ('county', 'unknown:2025:county:01001'), ('county', 'geography:2025:county: '),
    ('age', 'feature:income:mean'), ('age', 'feature:age: '), ('age', 'feature:age'),
    ('soc_major', 'soc:2020:minor:11'), ('naics_sector', 'naics:2022:industry:11')])
def test_rejects_invalid_typed_ids(kind, value):
    for side in ['a', 'b']:
        with pytest.raises(ValueError, match='unit'):
            tc.validate_targets(target_rows().with_columns(
                pl.lit(kind).alias('unit_' + side + '_type'),
                pl.lit(value).alias('unit_' + side)))


@pytest.mark.parametrize('column,value', [('value', float('nan')), ('value', float('inf')),
    ('value', -float('inf')), ('n_weighted', float('nan')), ('n_weighted', float('inf')),
    ('n_weighted', -1.0)])
def test_rejects_invalid_numeric_domains(column, value):
    with pytest.raises(ValueError):
        tc.validate_targets(target_rows().with_columns(pl.lit(value).alias(column)))


@pytest.mark.parametrize('method,se,valid', [('none', None, True), ('none', 0.0, False),
    ('replicate', 0.0, True), ('replicate', None, False), ('bootstrap', 0.5, True),
    ('bootstrap', -1.0, False), ('other', None, False), ('bootstrap', float('inf'), False),
    ('replicate', float('nan'), False)])
def test_shared_se_contract(method, se, valid):
    frame = target_rows().with_columns(pl.lit(method).alias('se_method'),
                                      pl.lit(se, dtype=pl.Float64).alias('se'))
    if valid:
        tc.validate_targets(frame)
    else:
        with pytest.raises(ValueError):
            tc.validate_targets(frame)


@pytest.mark.parametrize('flags', [[None], [''], [' '], ['b', 'a'], ['a', 'a']])
def test_rejects_noncanonical_flags(flags):
    with pytest.raises(ValueError, match='flags'):
        tc.validate_targets(target_rows().with_columns(
            pl.lit(flags, dtype=pl.List(pl.String)).alias('flags')))


def test_duplicate_keys_ignore_estimate_counts_and_flags():
    original = target_rows().head(1)
    different = original.with_columns(pl.lit(9.0).alias('value'),
        pl.lit(9, dtype=pl.UInt64).alias('n_unweighted'), pl.lit(9.5).alias('n_weighted'),
        pl.lit(['different'], dtype=pl.List(pl.String)).alias('flags'))
    with pytest.raises(ValueError, match='duplicate'):
        tc.validate_targets(pl.concat([original, different]))


def test_writer_general_feature_semantics(tmp_path):
    frame = target_rows().head(1).with_columns(pl.lit('worker_profile').alias('family'),
        pl.lit('age').alias('unit_b_type'), pl.lit('feature:age:mean:adult').alias('unit_b'),
        pl.lit('mean_age').alias('measure'), pl.lit(42.5).alias('value'),
        pl.lit(1.2, dtype=pl.Float64).alias('se'), pl.lit('replicate').alias('se_method'),
        pl.lit(10.5).alias('n_weighted'))
    destination = tmp_path / 'target.parquet'
    assert tc.write_targets(frame, destination) == file_record(destination)
    assert_frame_equal(pl.read_parquet(destination), frame)


def test_writer_sorts_deterministically(tmp_path):
    frame = target_rows()
    first, second = tmp_path / 'first.parquet', tmp_path / 'second.parquet'
    tc.write_targets(frame.lazy(), first)
    record = tc.write_targets(frame.reverse(), second)
    assert first.read_bytes() == second.read_bytes()
    assert record['rows'] == frame.height
    assert record['columns'] == frame.columns
    assert_frame_equal(pl.read_parquet(second), frame.sort(tc.TARGET_KEY_COLUMNS))


@pytest.mark.parametrize('occupied', ['file', 'directory', 'dangling_symlink'])
def test_writer_refuses_occupied_destination(tmp_path, occupied):
    destination = tmp_path / 'target.parquet'
    if occupied == 'file':
        destination.write_bytes(b'existing')
    elif occupied == 'directory':
        destination.mkdir()
    else:
        destination.symlink_to(tmp_path / 'missing')
    with pytest.raises(ValueError, match='exists'):
        tc.write_targets(target_rows(), destination)
    if occupied == 'file':
        assert destination.read_bytes() == b'existing'
    elif occupied == 'directory':
        assert destination.is_dir()
    else:
        assert destination.is_symlink()


def test_writer_does_not_publish_invalid_rows(tmp_path):
    destination = tmp_path / 'target.parquet'
    with pytest.raises(ValueError):
        tc.write_targets(target_rows().with_columns(pl.lit(float('nan')).alias('value')),
                         destination)
    assert not destination.exists()


@pytest.mark.parametrize('kind,value', [
    ('county', 'geography:0000:county:unknown:payload'),
    ('soc_arbitrary', 'soc:9999:arbitrary:unknown'),
    ('age', 'feature:age:mean:adult'),
    ('naics_arbitrary', 'naics:0000:arbitrary:unknown')])
def test_shared_ids_do_not_impose_family_membership(kind, value):
    tc.validate_targets(target_rows().head(1).with_columns(pl.lit(kind).alias('unit_b_type'),
                                                  pl.lit(value).alias('unit_b'),
                                                  pl.lit(-42.5).alias('value')))


@pytest.mark.parametrize('name', ['targets', 'targets.PARQUET'])
def test_writer_inventory_does_not_depend_on_destination_suffix(tmp_path, name):
    frame = target_rows()
    destination = tmp_path / name
    record = tc.write_targets(frame, destination)
    assert record['rows'] == frame.height
    assert record['columns'] == frame.columns
    assert record['schema'] == {column: str(dtype) for column, dtype in frame.schema.items()}
    assert record['sha256'] == file_record(destination)['sha256']
    assert record['size'] == destination.stat().st_size
    assert_frame_equal(pl.read_parquet(destination), frame.sort(tc.TARGET_KEY_COLUMNS))
