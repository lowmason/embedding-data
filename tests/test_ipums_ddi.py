import importlib

import pytest
from ipums_fixtures import ddi_xml, definition, write_ddi, write_definition

def test_metadata_preserves_order_scales_categories_and_namespaces(tmp_path):
    metadata = importlib.import_module('embedding_data.ipums_ddi')
    result = metadata.read_ddi(write_ddi(tmp_path))
    assert [variable['name'] for variable in result['variables']] == [
        'SAMPLE', 'PERWT', 'REPWTP1', 'REPWTP2', 'INDNAICS',
    ]
    assert [variable['implied_decimals'] for variable in result['variables']] == [0, 2, 4, 4, 0]
    assert result['variables'][0]['categories'] == [
        {'value': '001', 'label': 'us2023a'},
        {'value': '002', 'label': 'us2024a'},
        {'value': '003', 'label': 'us1900a not delivered'},
    ]
    assert result['variables'][1]['label'] == 'Person weight'
    assert result['variables'][1]['instructions'] == [
        'Divide stored values by 100.', 'Preserve decimals.',
    ]
    assert result['variables'][-1]['categories'] == [{'value': '31M', 'label': 'Manufacturing'}]
    assert result['ddi_version'] == '2.5'
    assert result['citation'] == 'Synthetic citation version 17.0.'
    assert result['dataset_version'] == 'fixture dataset v17.0'
    assert result['dataset_version_date'] == '2026-10-12'
    assert result['study_notes'] == [
        'us2023a: delivered synthetic sample', 'us2024a: delivered synthetic sample',
    ]
    assert result['time_notes'] == [
        {'kind': 'timePrd', 'text': '2023-2024', 'event': 'start', 'date': '2023'},
        {'kind': 'collDate', 'text': None, 'event': 'single', 'date': '2026-10-12'},
    ]
    submitted = metadata.read_definition(write_definition(tmp_path))
    assert list(submitted['samples']) == ['us2023a', 'us2024a']
    assert 'REPWTP' in submitted['variables']
    assert 'REPWTP' not in [variable['name'] for variable in result['variables']]


def test_definition_preserves_unknown_version_quality_flags_and_selections(tmp_path):
    metadata = importlib.import_module('embedding_data.ipums_ddi')
    delivered = definition()
    assert metadata.read_definition(write_definition(tmp_path, delivered)) == delivered
    delivered.pop('version')
    assert metadata.read_definition(write_definition(tmp_path, delivered))['version'] is None


@pytest.mark.parametrize('field,value', [
    ('collection', 'unsupported'), ('collection', None), ('dataFormat', 'fixed_width'),
    ('samples', []), ('samples', {}), ('samples', {'': {}}),
    ('samples', {'us2023a': []}), ('variables', []), ('variables', {}),
    ('variables', {'': {}}), ('variables', {'PERWT': []}),
    ('dataQualityFlags', 'true'), ('dataQualityFlags', None), ('version', []),
])
def test_definition_rejects_invalid_required_fields(tmp_path, field, value):
    metadata = importlib.import_module('embedding_data.ipums_ddi')
    contents = definition()
    contents[field] = value
    with pytest.raises(ValueError):
        metadata.read_definition(write_definition(tmp_path, contents))


@pytest.mark.parametrize('field', ['collection', 'samples', 'variables', 'dataFormat'])
def test_definition_rejects_absent_required_fields(tmp_path, field):
    metadata = importlib.import_module('embedding_data.ipums_ddi')
    contents = definition()
    contents.pop(field)
    with pytest.raises(ValueError):
        metadata.read_definition(write_definition(tmp_path, contents))


@pytest.mark.parametrize('settings', [
    {'dataQualityFlags': 'false'}, {'caseSelections': []},
    {'caseSelections': {'general': '1'}}, {'caseSelections': {'general': [1]}},
    {'caseSelections': {'': ['1']}},
])
def test_definition_rejects_malformed_variable_options(tmp_path, settings):
    metadata = importlib.import_module('embedding_data.ipums_ddi')
    contents = definition()
    contents['variables']['EMPSTAT'].update(settings)
    with pytest.raises(ValueError):
        metadata.read_definition(write_definition(tmp_path, contents))


def test_optional_unknown_metadata_never_becomes_false_zero_or_known(tmp_path):
    metadata = importlib.import_module('embedding_data.ipums_ddi')
    contents = definition()
    contents.pop('dataQualityFlags')
    contents['variables']['EMPSTAT'].pop('dataQualityFlags')
    submitted = metadata.read_definition(write_definition(tmp_path, contents))
    assert submitted['dataQualityFlags'] is None
    assert submitted['variables']['EMPSTAT']['dataQualityFlags'] is None
    xml = '<codeBook xmlns="ddi:codebook:2_5"><dataDscr><var name="PERWT"/></dataDscr></codeBook>'
    result = metadata.read_ddi(write_ddi(tmp_path, xml))
    assert result == {
        'ddi_version': None,
        'variables': [{'name': 'PERWT', 'label': None, 'implied_decimals': None,
                       'categories': [], 'instructions': []}],
        'study_notes': [], 'time_notes': [], 'citation': None,
        'dataset_version': None, 'dataset_version_date': None,
    }


@pytest.mark.parametrize('old,new', [
    ('name="INDNAICS"', 'name="PERWT"'), ('<catValu>002</catValu>', '<catValu>001</catValu>'),
    ('dcml="2"', 'dcml="2.0"'), ('dcml="2"', 'dcml="-2"'),
    ('dcml="2"', 'dcml="2e1"'), ('name="PERWT"', 'name=""'),
    ('<catValu>001</catValu>', '<catValu/>'),
])
def test_ddi_rejects_ambiguous_or_malformed_metadata(tmp_path, old, new):
    metadata = importlib.import_module('embedding_data.ipums_ddi')
    with pytest.raises(ValueError):
        metadata.read_ddi(write_ddi(tmp_path, ddi_xml().replace(old, new)))


@pytest.mark.parametrize('xml', ['<codeBook/>', '<wrong/>', '<codeBook><dataDscr/></codeBook>'])
def test_ddi_rejects_missing_required_structure(tmp_path, xml):
    metadata = importlib.import_module('embedding_data.ipums_ddi')
    with pytest.raises(ValueError):
        metadata.read_ddi(write_ddi(tmp_path, xml))
