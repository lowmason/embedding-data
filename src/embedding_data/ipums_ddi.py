'''Read delivered IPUMS definition and DDI metadata without reading microdata.'''

import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET

def read_definition(file: Path) -> dict:
    '''Validate submitted settings, retaining unknown API version and flag metadata.'''
    definition = json.loads(file.read_text())
    if not isinstance(definition, dict):
        raise ValueError('extract definition must be an object')
    if definition.get('collection') not in {'usa', 'cps'}:
        raise ValueError('unsupported extract collection')
    if definition.get('dataFormat') != 'csv':
        raise ValueError('extract definition must request CSV')
    for field in ('samples', 'variables'):
        settings = definition.get(field)
        if not isinstance(settings, dict) or not settings:
            raise ValueError(f'extract definition requires {field}')
        for name, options in settings.items():
            if not name.strip() or not isinstance(options, dict):
                raise ValueError(f'invalid {field} entry')
    version = definition.setdefault('version', None)
    if version is not None and (isinstance(version, bool) or not isinstance(version, (str, int))):
        raise ValueError('invalid API extract version')
    definition['dataQualityFlags'] = _quality_flags(definition)
    for options in definition['variables'].values():
        options['dataQualityFlags'] = _quality_flags(options)
        selections = options.get('caseSelections', {})
        if not isinstance(selections, dict):
            raise ValueError('caseSelections must be an object')
        for kind, codes in selections.items():
            if (
                not kind.strip() or not isinstance(codes, list)
                or any(not isinstance(code, str) for code in codes)
            ):
                raise ValueError('caseSelections must map selection names to string lists')
    return definition


def _quality_flags(settings: dict) -> bool | None:
    if 'dataQualityFlags' in settings and not isinstance(settings['dataQualityFlags'], bool):
        raise ValueError('dataQualityFlags must be boolean when present')
    return settings.get('dataQualityFlags')


def _text(element: ET.Element | None) -> str | None:
    if element is None:
        return None
    return ''.join(element.itertext()).strip() or None


def _variable(element: ET.Element, namespace: str) -> dict:
    name = element.get('name')
    if name is None or not name.strip():
        raise ValueError('DDI variable requires a name')
    exponent = element.get('dcml')
    if exponent is not None and not re.fullmatch(r'[0-9]+', exponent):
        raise ValueError('DDI dcml must be a nonnegative integer exponent')
    categories = []
    seen_values = set()
    for category in element.findall(f'{namespace}catgry'):
        value = _text(category.find(f'{namespace}catValu'))
        if value is None or value in seen_values:
            raise ValueError('DDI category values must be present and unique per variable')
        seen_values.add(value)
        categories.append({'value': value, 'label': _text(category.find(f'{namespace}labl'))})
    instruction_tags = {f'{namespace}{tag}' for tag in ('txt', 'notes', 'codInstr', 'qstn')}
    return {
        'name': name,
        'label': _text(element.find(f'{namespace}labl')),
        'implied_decimals': None if exponent is None else int(exponent),
        'categories': categories,
        'instructions': [
            text for child in element if child.tag in instruction_tags
            if (text := _text(child)) is not None
        ],
    }


def read_ddi(file: Path) -> dict:
    '''Preserve ordered metadata; optional absent fields remain explicitly unknown.'''
    root = ET.parse(file).getroot()
    namespace = root.tag.partition('}')[0] + '}' if root.tag.startswith('{') else ''
    if root.tag != f'{namespace}codeBook':
        raise ValueError('DDI requires a codeBook root')
    variables = [
        _variable(element, namespace)
        for element in root.findall(f'{namespace}dataDscr/{namespace}var')
    ]
    if not variables:
        raise ValueError('DDI requires variable metadata')
    names = [variable['name'] for variable in variables]
    if len(set(names)) != len(names):
        raise ValueError('DDI variable names must be unique')
    study = root.find(f'{namespace}stdyDscr')
    result = {
        'ddi_version': root.get('version'), 'variables': variables,
        'study_notes': [], 'time_notes': [], 'citation': None,
        'dataset_version': None, 'dataset_version_date': None,
    }
    if study is not None:
        result['study_notes'] = [
            text for note in study.findall(f'{namespace}stdyInfo/{namespace}notes')
            if (text := _text(note)) is not None
        ]
        summary = study.find(f'{namespace}stdyInfo/{namespace}sumDscr')
        if summary is not None:
            result['time_notes'] = [
                {'kind': element.tag.removeprefix(namespace), 'text': _text(element),
                 **element.attrib}
                for element in summary
                if element.tag in {f'{namespace}timePrd', f'{namespace}collDate'}
            ]
        result['citation'] = _text(study.find(
            f'{namespace}dataAccs/{namespace}useStmt/{namespace}citReq',
        ))
        version = study.find(f'{namespace}citation/{namespace}verStmt/{namespace}version')
        result['dataset_version'] = _text(version)
        result['dataset_version_date'] = None if version is None else version.get('date')
    return result
