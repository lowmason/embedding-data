'''Ordered annotation fidelity and independent source-allocation provenance.'''
from dataclasses import replace

import polars as pl
import pytest
from acs_mapping_fixtures import companion_case as companion_case
from acs_mapping_fixtures import population_case as population_case  # noqa: F401
from acs_mapping_fixtures import role_case as role_case  # noqa: F401
from test_acs_code_references import (  # noqa: F401
    code_originals,
    evidence,
    graphs,
    offline,
    public_monkeypatch,
    selected,
)

from embedding_data.acs_mapping_contract import ANNOTATION_SCHEMA
from embedding_data.ipums_parity import compare_ordered

def test_join_streams_and_preserves_ordered_nested_payloads():
    from embedding_data.acs_mapping_companions import _join

    left = pl.DataFrame({'key': ['B', 'A', 'A', None, 'missing'],
                         'ordinal': [0, 1, 2, 3, 4]},
                        schema={'key': pl.String, 'ordinal': pl.Int64}).lazy()
    right = pl.DataFrame(
        {'key': ['A', 'B'], 'candidates': [['a', 'b'], []],
         'paths': [[['root', 'a'], ['root', 'b']], []]},
        schema={'key': pl.String, 'candidates': pl.List(pl.String),
                'paths': pl.List(pl.List(pl.String))},
    )
    joined = _join(left, right, ['key'])
    expected = left.join(right.lazy(), on=['key'], how='left', validate='m:1',
                         maintain_order='left', nulls_equal=False, coalesce=True).collect()
    actual = joined.collect(engine='streaming')
    assert actual.equals(expected)
    assert actual['ordinal'].to_list() == [0, 1, 2, 3, 4]
    assert actual['candidates'].to_list() == [[], ['a', 'b'], ['a', 'b'], None, None]
    assert actual['paths'].to_list() == [[], [['root', 'a'], ['root', 'b']],
                                        [['root', 'a'], ['root', 'b']], None, None]
    physical = joined.show_graph(plan_stage='physical', engine='streaming',
                                 raw_output=True, show=False)
    assert 'in-memory-join' not in physical
    assert 'equi-join' in physical


@pytest.mark.parametrize('keys', [['key'], ['key', 'vintage']])
def test_join_rejects_duplicate_complete_lookup_keys_before_execution(keys):
    from embedding_data.acs_mapping_companions import _join

    right = pl.DataFrame({'key': [None, None, 'A', 'A'], 'vintage': [2022] * 4,
                          'payload': ['null-one', 'null-two', 'first', 'second']})
    left = pl.DataFrame({'key': ['unmatched'], 'vintage': [2022]}).lazy()
    with pytest.raises(pl.exceptions.ComputeError, match='m:1'):
        left.join(right.lazy(), on=keys, how='left', validate='m:1',
                  nulls_equal=False).collect()
    with pytest.raises(ValueError, match='duplicate.*lookup.*key') as error:
        _join(left, right, keys)
    assert all(key in str(error.value) for key in keys)


@pytest.mark.parametrize('keys', [['key'], ['key', 'vintage']])
@pytest.mark.parametrize('empty_lookup', [False, True])
def test_join_preserves_nonmatching_null_keys_and_empty_lookup(keys, empty_lookup):
    from embedding_data.acs_mapping_companions import _join

    right = pl.DataFrame(
        {'key': [None, None, 'A'], 'vintage': [2022, 2022, 2022],
         'payload': ['null-one', 'null-two', 'matched']},
        schema={'key': pl.String, 'vintage': pl.Int64, 'payload': pl.String},
    )
    if len(keys) == 2:
        right = pl.concat([right, pl.DataFrame(
            {'key': ['A', 'A', None, None], 'vintage': [None] * 4,
             'payload': ['partial-one', 'partial-two', 'null-three', 'null-four']},
            schema=right.schema)])
    if empty_lookup:
        right = right.head(0)
    left = pl.DataFrame({'key': [None, 'A', 'A', None],
                         'vintage': [2022, None, 2022, None]},
                        schema={'key': pl.String, 'vintage': pl.Int64}).lazy()
    expected = left.join(right.lazy(), on=keys, how='left', validate='m:1',
                         maintain_order='left', nulls_equal=False, coalesce=True).collect()
    actual = _join(left, right, keys).collect(engine='streaming')
    assert actual.equals(expected)
    assert actual['payload'].to_list() == (
        [None] * 4 if empty_lookup else
        [None, 'matched' if len(keys) == 1 else None, 'matched', None])


def test_join_requires_materialized_small_lookup():
    from embedding_data.acs_mapping_companions import _join

    left = pl.DataFrame({'key': ['A']}).lazy()
    with pytest.raises(TypeError, match='materialized.*DataFrame'):
        _join(left, left, ['key'])


def write_case(case, output):
    from embedding_data.acs_mapping_companions import annotate_source, write_companion

    frame = annotate_source(case.source, case.codes, case.areas, case.factors)
    assert isinstance(frame, pl.LazyFrame)
    assert 'Parquet SCAN' in frame.explain()
    write_companion(frame, case.source, output)
    return pl.read_parquet(output)


def test_annotations_preserve_order_types_duplicates_and_missing_flags(companion_case, tmp_path):
    from embedding_data.acs_mapping_companions import validate_companion

    for profile, case in companion_case.profiles.items():
        output = tmp_path / (profile + '.parquet')
        result = write_case(case, output)
        original = pl.scan_parquet(case.source.parquet)
        names = original.collect_schema().names()
        assert list(result.schema.items()) == [*original.collect_schema().items(),
                                               *ANNOTATION_SCHEMA.items()]
        assert compare_ordered(original, pl.scan_parquet(output).select(names))['values_equal']
        assert result['source_row'].to_list() == list(range(result.height))
        assert result['source_parquet_sha256'].unique().to_list() == [
            case.source.parquet_record['sha256']]
        assert result.select(names).row(0) == result.select(names).row(-1)
        for flag in ['QIND', 'QOCC', 'QMIGRAT1']:
            assert (flag in result.columns) == (flag in names)
            if flag in names:
                assert result[flag].equals(pl.read_parquet(case.source.parquet)[flag])
        assert validate_companion(case.source, output, case.codes, case.areas,
                                  case.factors)['values_equal']


def test_flags_are_delivery_specific_and_do_not_invent_applicability(companion_case, tmp_path):
    core = write_case(companion_case, tmp_path / 'core.parquet')
    assert core['industry_source_allocation_status'].to_list() == [
        'allocated', 'not_allocated_or_niu', 'unavailable', 'unavailable',
        'not_allocated_or_niu', 'allocated']
    assert core['occupation_source_allocated'].to_list() == [None, True, None, None, None, None]
    assert core['migration_source_allocation_status'].to_list() == ['unavailable'] * 6
    assert core['QMIGRAT1'].dtype == pl.String
    five = write_case(companion_case.profiles['five_year'], tmp_path / 'five.parquet')
    assert five['QMIGRAT1'].dtype == pl.Int64
    assert five['migration_source_allocated'].to_list() == [None, True, None, None, None, None]
    assert five['flag_source_industry_recoded'].to_list() == [True, True, True, False, False, True]
    assert five['residence_flag_source_geography_recoded'].to_list() == [
        True, True, False, False, False, True]
    assert core['industry_flag_partial'].all()
    assert core['industry_canonical_scalar_code'].null_count() == 6
    assert core['occupation_mapping_status'].to_list() == ['documented_special'] * 6
    assert core['residence_flag_geographic_allocation'].all()
    assert core['residence_flag_fractional_split'].to_list() == [
        True, False, True, True, True, True]
    assert core['workplace_area_status'].to_list() == [
        'applicable', 'applicable', 'niu_or_unidentifiable', 'foreign', 'territory', 'applicable']


@pytest.mark.parametrize(
    'kind', ['duplicate_code', 'missing_code', 'duplicate_area', 'missing_area']
)
def test_lookup_failures_refuse_annotation(companion_case, kind):
    from embedding_data.acs_mapping_companions import annotate_source

    case = companion_case
    codes, areas = case.codes, case.areas
    if kind == 'duplicate_code':
        codes = pl.concat([codes, codes.head(1)])
    elif kind == 'missing_code':
        codes = codes.filter(pl.col('source_token').ne('2212P'))
    elif kind == 'duplicate_area':
        areas = pl.concat([areas, areas.head(1)])
    else:
        areas = areas.filter(pl.col('profile').ne('acs/core'))
    with pytest.raises(ValueError):
        annotate_source(case.source, codes, areas, case.factors).collect()


@pytest.mark.parametrize('column', ['source_row', 'industry_mapping_status', '__acs_pair'])
def test_source_reserved_name_collisions(companion_case, tmp_path, column):
    from embedding_data.acs_mapping_companions import annotate_source

    case = companion_case
    file = tmp_path / 'collision.parquet'
    pl.read_parquet(case.source.parquet).with_columns(pl.lit('occupied').alias(column)).write_parquet(
        file)
    with pytest.raises(ValueError, match='collid'):
        annotate_source(replace(case.source, parquet=file), case.codes, case.areas, case.factors)


@pytest.mark.parametrize('mutation', ['reverse', 'drop', 'duplicate', 'schema', 'ordinal', 'hash',
                                     'mapping', 'factor', 'flag'])
def test_validation_refuses_fidelity_and_annotation_mutations(companion_case, tmp_path, mutation):
    from embedding_data.acs_mapping_companions import validate_companion

    case = companion_case
    output = tmp_path / 'original.parquet'
    result = write_case(case, output)
    if mutation == 'reverse':
        result = result.reverse()
    elif mutation == 'drop':
        result = result.head(5)
    elif mutation == 'duplicate':
        result = pl.concat([result.head(1), result])
    elif mutation == 'schema':
        result = result.select('QIND', pl.exclude('QIND'))
    else:
        field, value = {'ordinal': ('source_row', 3),
                        'hash': ('source_parquet_sha256', 'tampered'),
                        'mapping': ('industry_flag_partial', False),
                        'factor': ('residence_flag_fractional_split', False),
                        'flag': ('industry_source_allocated', False)}[mutation]
        result = result.with_columns(pl.lit(value).cast(result.schema[field]).alias(field))
    result.write_parquet(output)
    with pytest.raises(ValueError):
        validate_companion(case.source, output, case.codes, case.areas, case.factors)


def test_diagnostic_partitions_reconcile_and_keep_overlapping_provenance(companion_case, tmp_path):
    import json

    from embedding_data.acs_mapping_companions import companion_diagnostics

    output = tmp_path / 'companion.parquet'
    write_case(companion_case, output)
    report = companion_diagnostics(companion_case.source, output)
    assert report['rows'] == 6
    for counts in report['primary_statuses'].values():
        assert sum(counts.values()) == 6
    assert sum(p['rows'] for p in report['partitions']) == 6
    assert report['provenance_flags']['industry_flag_partial']['true'] == 6
    assert report['provenance_flags']['industry_flag_aggregate']['true'] == 6
    encoded = json.dumps(report, allow_nan=False)
    assert 'source_row' not in encoded
    assert '559830' not in encoded


def test_writer_refuses_occupied_and_symlink_paths(companion_case, tmp_path):
    from embedding_data.acs_mapping_companions import annotate_source, write_companion

    case = companion_case
    frame = annotate_source(case.source, case.codes, case.areas, case.factors)
    output = tmp_path / 'occupied.parquet'
    output.write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        write_companion(frame, case.source, output)
    assert output.read_bytes() == b'keep'
    link = tmp_path / 'link.parquet'
    link.symlink_to(tmp_path / 'absent')
    with pytest.raises(ValueError):
        write_companion(frame, case.source, link)


def source_variant(case, tmp_path, frame):
    from embedding_data import target_io

    file = tmp_path / 'variant.parquet'
    frame.write_parquet(file)
    return replace(case.source, parquet=file, parquet_record=target_io.file_record(file))


def test_delivered_null_classification_has_typed_empty_claims(companion_case, tmp_path):
    from embedding_data.acs_mapping_companions import annotate_source, validate_companion

    case = companion_case
    source = source_variant(case, tmp_path, pl.read_parquet(case.source.parquet).with_columns(
        pl.when(pl.int_range(pl.len()).eq(1)).then(pl.lit(None, dtype=pl.String))
        .otherwise(pl.col('INDNAICS')).alias('INDNAICS')))
    case = type(case)(**{**vars(case), 'source': source})
    result = write_case(case, tmp_path / 'missing.parquet')
    row = result.row(1, named=True)
    assert row['industry_mapping_status'] == 'missing'
    assert row['industry_paired_census_code'] == '0580'
    for field in ['canonical_finest_candidates', 'native_finest_candidates',
                  'canonical_candidate_paths', 'reference_ids', 'aggregation_markers']:
        assert row['industry_' + field] == []
    for field in ['native_node_id', 'canonical_scalar_code', 'canonical_common_node_id']:
        assert row['industry_' + field] is None
    assert result['industry_source_allocated'][1] is None
    assert isinstance(annotate_source(source, case.codes, case.areas, case.factors), pl.LazyFrame)
    assert validate_companion(source, tmp_path / 'missing.parquet', case.codes, case.areas,
                              case.factors)['annotations_equal']


@pytest.mark.parametrize('field,value', [('INDNAICS', ' '), ('INDNAICS', '999999'),
                                        ('IND', '-1'), ('PUMA', -1)])
def test_unparseable_or_unmatched_source_keys_fail(companion_case, tmp_path, field, value):
    from embedding_data.acs_mapping_companions import annotate_source

    case = companion_case
    source = source_variant(case, tmp_path, pl.read_parquet(case.source.parquet).with_columns(
        pl.lit(value).alias(field)))
    with pytest.raises(ValueError):
        annotate_source(source, case.codes, case.areas, case.factors).collect()


def test_changed_source_order_cannot_reuse_verified_source_hash(companion_case):
    from embedding_data.acs_mapping_companions import annotate_source

    case = companion_case
    frame = pl.read_parquet(case.source.parquet)
    frame.reverse().write_parquet(case.source.parquet)
    with pytest.raises(ValueError, match='source hash'):
        annotate_source(case.source, case.codes, case.areas, case.factors)


def test_allocation_requires_same_delivery_ddi_evidence(companion_case, tmp_path):
    from copy import deepcopy
    from types import SimpleNamespace

    case = companion_case
    ddi = deepcopy(case.source.ddi)
    for variable in ddi['variables']:
        if variable['name'] == 'QIND':
            for category in variable['categories']:
                if category['value'] == '4':
                    category['label'] = 'Missing'
    source = replace(case.source, ddi=ddi)
    changed = SimpleNamespace(**{**vars(case), 'source': source})
    result = write_case(changed, tmp_path / 'no-authority.parquet')
    assert result['industry_source_allocated'].null_count() == result.height
    assert result['QIND'].equals(pl.read_parquet(source.parquet)['QIND'])
    ddi['variables'] = [v for v in ddi['variables'] if v['name'] != 'QIND']
    result = write_case(changed, tmp_path / 'absent-authority.parquet')
    assert result['industry_source_allocation_status'].to_list() == ['unavailable'] * 6


def test_missing_applicable_factors_fail(companion_case):
    from embedding_data.acs_mapping_companions import annotate_source

    case = companion_case
    factors = replace(case.factors, county=case.factors.county.head(0))
    with pytest.raises(ValueError, match='missing or incomplete'):
        annotate_source(case.source, case.codes, case.areas, factors)


def test_failed_writer_cleans_only_owned_file_and_refuses_partials(companion_case, tmp_path):
    from embedding_data.acs_mapping_companions import annotate_source, write_companion

    case = companion_case
    frame = annotate_source(case.source, case.codes, case.areas, case.factors)
    output = tmp_path / 'bad.parquet'
    with pytest.raises(ValueError, match='order or multiplicity'):
        write_companion(frame.reverse(), case.source, output)
    assert not output.exists()
    partial = output.with_name(output.name + '.part')
    partial.write_bytes(b'keep earlier partial')
    with pytest.raises(FileExistsError):
        write_companion(frame, case.source, output)
    assert partial.read_bytes() == b'keep earlier partial'
