'''Hermetic delivered-DDI optional-label and domain regressions.'''

import importlib.util
from pathlib import Path

import pytest

@pytest.fixture
def delivered_categories():
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'stage9_independent_estimates.py'
    spec = importlib.util.spec_from_file_location('independent_ddi_tests', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.delivered_categories


@pytest.mark.parametrize('namespace', ['', ' xmlns="urn:ddi:synthetic"'])
def test_delivered_categories_matches_nullable_frozen_metadata(
    tmp_path, delivered_categories, namespace
):
    xml = tmp_path / 'synthetic.xml'
    xml.write_text(
        f"""<codeBook{namespace}><dataDscr><var name="OCC">
          <catgry><catValu>0000</catValu></catgry>
          <catgry><catValu>0001</catValu><labl /></catgry>
          <catgry><catValu>0002</catValu><labl>  \n  </labl></catgry>
          <catgry><catValu>0010</catValu><labl>  Managers  </labl></catgry>
          <catgry><catValu>31M</catValu><labl>  Skilled <em>workers</em> group  </labl></catgry>
        </var><var name="IND">
          <catgry><catValu>0110</catValu><labl>  Agriculture  </labl></catgry>
        </var></dataDscr></codeBook>""",
        encoding='utf-8',
    )
    frozen_metadata = {
        'OCC': {
            '0000': None,
            '0001': None,
            '0002': None,
            '0010': 'Managers',
            '31M': 'Skilled workers group',
        },
        'IND': {'0110': 'Agriculture'},
    }

    assert delivered_categories(xml) == frozen_metadata


@pytest.mark.parametrize(
    ('variables', 'message'),
    [
        ('<var name="OCC"/><var name="OCC"/>', 'duplicate delivered DDI variable'),
        (
            '<var name="OCC"><catgry><catValu>0010</catValu></catgry>'
            '<catgry><catValu>0010</catValu></catgry></var>',
            'invalid delivered DDI domain',
        ),
        ('<var name="OCC"><catgry><labl>Managers</labl></catgry></var>',
         'invalid delivered DDI domain'),
    ],
)
def test_delivered_categories_rejects_invalid_domains(
    tmp_path, delivered_categories, variables, message
):
    xml = tmp_path / 'invalid.xml'
    xml.write_text(f'<codeBook><dataDscr>{variables}</dataDscr></codeBook>', encoding='utf-8')

    with pytest.raises(ValueError, match=message):
        delivered_categories(xml)
