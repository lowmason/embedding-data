import polars as pl
import pytest

from embedding_data import acs_mapping_contract as contract_module
from embedding_data.acs_mapping_contract import companion_schema, lookup_id, validate_table

def test_exact_typed_suffix_and_empty_lists():
    c = contract_module
    assert c.FORMAT_VERSION == 'acs-mapping-v1'
    assert len(c.ANNOTATION_SCHEMA) == 114
    frame = pl.DataFrame(schema=c.CODE_SCHEMA)
    assert frame.schema['native_finest_candidates'] == pl.List(pl.String)
    assert frame.schema['canonical_candidate_paths'] == pl.List(pl.List(pl.String))
    validate_table('code', frame)


def code_row():
    c = contract_module
    row = {name: ([] if isinstance(dtype, pl.List) else
                  False if dtype == pl.Boolean else 2022 if dtype == pl.Int64 else 'x')
           for name, dtype in c.CODE_SCHEMA.items()}
    row.update(rule_version=c.CODE_RULE_VERSION, aggregation_reason_status='not_applicable',
               system='naics', source_scheme='naics_2022', paired_census_code='0170',
               source_token='111111', mapping_status='mapped',
               canonical_finest_candidates=['111111'],
               canonical_candidate_paths=[['root', 'leaf']])
    row['code_lookup_id'] = lookup_id([row[k] for k in c.NATURAL_KEYS['code']])
    return row


@pytest.mark.parametrize('defect', ['null', 'null_element', 'duplicate', 'unsorted', 'paths',
                                   'wrong_id', 'schema'])
def test_lookup_rejects_invalid_contract(defect):
    c, row = contract_module, code_row()
    rows = [row]
    if defect == 'null':
        row['system'] = None
    elif defect == 'null_element':
        row['reference_ids'] = [None]
    elif defect == 'duplicate':
        rows.append(row.copy())
    elif defect == 'unsorted':
        row['canonical_finest_candidates'] = ['b', 'a']
        row['canonical_candidate_paths'] = [['b'], ['a']]
    elif defect == 'paths':
        row['canonical_candidate_paths'] = []
    elif defect == 'wrong_id':
        row['code_lookup_id'] = 'wrong'
    frame = pl.DataFrame(rows, schema=c.CODE_SCHEMA)
    if defect == 'schema':
        frame = frame.with_columns(pl.lit(None).alias('source_token'))
    with pytest.raises(ValueError):
        validate_table('code', frame)


def test_key_hash_distinguishes_null_from_empty_string():
    assert lookup_id([None]) != lookup_id([''])


def test_valid_lookup_preserves_path_order():
    c = contract_module
    frame = pl.DataFrame([code_row()], schema=c.CODE_SCHEMA)
    validate_table('code', frame)
    assert frame['canonical_candidate_paths'].to_list() == [[['root', 'leaf']]]


def test_table_sort_uses_null_first_natural_keys():
    c = contract_module
    row = code_row()
    other = row.copy()
    other['source_token'] = '000000'
    other['code_lookup_id'] = lookup_id([other[k] for k in c.NATURAL_KEYS['code']])
    with pytest.raises(ValueError, match='sort'):
        validate_table('code', pl.DataFrame([row, other], schema=c.CODE_SCHEMA))


def test_companion_schema_preserves_source_order_and_rejects_collisions():
    c = contract_module
    source = {'QFLAG': pl.String, 'YEAR': pl.Int64}
    result = companion_schema(source)
    assert list(result.items())[:2] == list(source.items())
    assert list(result.items())[2:] == list(c.ANNOTATION_SCHEMA.items())
    with pytest.raises(ValueError):
        companion_schema({'source_row': pl.Int64})


@pytest.mark.parametrize('column,value', [
    ('aggregation_reason_status', 'unsupported'), ('aggregation_reasons', ['unsupported']),
    ('rule_version', 'unsupported'), ('mapping_status', 'unsupported')])
def test_code_enumerations_are_closed(column, value):
    c, row = contract_module, code_row()
    row[column] = value
    with pytest.raises(ValueError):
        validate_table('code', pl.DataFrame([row], schema=c.CODE_SCHEMA))


def test_only_approved_documented_special_has_no_candidates():
    c, row = contract_module, code_row()
    row.update(system='soc', source_scheme='soc_2018', source_token='559830',
               mapping_status='documented_special', special_reason='documented',
               canonical_finest_candidates=[], canonical_candidate_paths=[],
               native_finest_candidates=[])
    row['code_lookup_id'] = lookup_id([row[k] for k in c.NATURAL_KEYS['code']])
    validate_table('code', pl.DataFrame([row], schema=c.CODE_SCHEMA))
    row['source_token'] = '999999'
    row['code_lookup_id'] = lookup_id([row[k] for k in c.NATURAL_KEYS['code']])
    with pytest.raises(ValueError):
        validate_table('code', pl.DataFrame([row], schema=c.CODE_SCHEMA))


def reference_row(kind):
    c = contract_module
    return {name: ([] if isinstance(dtype, pl.List) else
                   True if dtype == pl.Boolean else 2020 if dtype == pl.Int64 else
                   1.0 if dtype == pl.Float64 else 'x')
            for name, dtype in c.SCHEMAS[kind].items()}


@pytest.mark.parametrize('status,key', [('applicable', None), ('foreign', 'unexpected')])
def test_area_factor_key_nullability_depends_on_status(status, key):
    c, row = contract_module, reference_row('area')
    row.update(area_status=status, factor_key=key)
    row['area_lookup_id'] = lookup_id([row[k] for k in c.NATURAL_KEYS['area']])
    with pytest.raises(ValueError):
        validate_table('area', pl.DataFrame([row], schema=c.AREA_SCHEMA))


@pytest.mark.parametrize('column', ['published_area_factor', 'published_county_factor'])
def test_published_county_factor_nullability_depends_on_area_type(column):
    c, row = contract_module, reference_row('county_factor')
    row.update(area_type='residence', **{column: None})
    with pytest.raises(ValueError):
        validate_table('county_factor', pl.DataFrame([row], schema=c.COUNTY_FACTOR_SCHEMA))
    row['area_type'] = 'work_migration'
    validate_table('county_factor', pl.DataFrame([row], schema=c.COUNTY_FACTOR_SCHEMA))
