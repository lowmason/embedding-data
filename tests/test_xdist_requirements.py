'''The hook's out-of-lock parallel runner must not drift from uv.lock.'''

import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / 'tests/xdist-requirements.txt'


def pins(text):
    '''Exact name==version pins; any other requirement form is refused.'''
    result = {}
    for line in text.splitlines():
        line = line.split('#', 1)[0].strip()
        if line:
            name, separator, version = line.partition('==')
            if not separator or not version or any(c in version for c in '<>=!~;, '):
                raise ValueError(f'not an exact pin: {line}')
            result[name.lower()] = version
    return result


def lock_mismatches(requirements, lock):
    locked = {package['name']: package['version'] for package in lock['package']}
    return {name: (version, locked[name]) for name, version in pins(requirements).items()
            if name in locked and locked[name] != version}


def test_overlay_pins_match_uv_lock():
    lock = tomllib.loads((ROOT / 'uv.lock').read_text())
    assert lock_mismatches(REQUIREMENTS.read_text(), lock) == {}


def test_overlay_pins_xdist_and_shadowed_pytest():
    pinned = pins(REQUIREMENTS.read_text())
    assert {'pytest-xdist', 'execnet', 'pytest', 'pluggy'} <= pinned.keys()


def test_mismatch_with_lock_is_reported():
    lock = {'package': [{'name': 'pytest', 'version': '9.1.1'}]}
    assert lock_mismatches('pytest==9.2.0\n', lock) == {'pytest': ('9.2.0', '9.1.1')}


@pytest.mark.parametrize('line', ['pytest>=9.1.1', 'pytest', 'pytest==9.1.1,<10'])
def test_inexact_requirement_is_refused(line):
    with pytest.raises(ValueError, match='not an exact pin'):
        pins(line)
