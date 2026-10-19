'''Authentic public D7/D8 assertions and bounded policy mutations; no production reads.'''
import csv
import gzip
import hashlib
import importlib.util
import io
import json
from collections import defaultdict
from pathlib import Path

import pytest
from acs_mapping_fixtures import forbid_external_access, genuine_geocorr_bytes

from embedding_data import acs_area_references, acs_code_references

PUBLIC = Path(__file__).parent / 'fixtures/acs_mapping/classification'


@pytest.fixture(params=['runtime', 'independent'])
def rules(request, monkeypatch):
    forbid_external_access(monkeypatch)
    if request.param == 'runtime':
        return acs_area_references, acs_code_references
    script = Path(__file__).resolve().parents[1] / 'scripts/reconcile_stage8.py'
    spec = importlib.util.spec_from_file_location('source_rules_reconciler', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, module


@pytest.fixture
def public_files(tmp_path):
    files = {p.stem: p for p in PUBLIC.glob('*.xlsx')}
    records = json.loads((PUBLIC / 'd8-originals.provenance.json').read_text())
    for kind, record in records.items():
        archive = (PUBLIC / record['archive']).read_bytes()
        assert hashlib.sha256(archive).hexdigest() == record['archive_sha256']
        body = gzip.decompress(archive)
        assert hashlib.sha256(body).hexdigest() == record['original_sha256']
        assert len(body) == record['original_size']
        file = tmp_path / record['archive'].removesuffix('.gz')
        file.write_bytes(body)
        files[kind] = file
    return files


def geocorr_rows():
    body = genuine_geocorr_bytes()
    reader = csv.DictReader(io.StringIO(body.decode('cp1252')))
    next(reader)
    rows = list(reader)
    return body, rows


def test_all_authentic_geocorr_rounding_assertions(rules):
    area, _ = rules
    body, rows = geocorr_rows()
    pumas, counties = defaultdict(int), defaultdict(int)
    for row in rows:
        pumas[row['state'], row['puma22']] += int(row['pop20'])
        counties[row['county']] += int(row['pop20'])
    rejected = []
    for number, row in enumerate(rows, 3):
        for column, denominator in [('afact', pumas[row['state'], row['puma22']]),
                                    ('afact2', counties[row['county']])]:
            diagnostic = area.geocorr_rounding_assertion(
                hashlib.sha256(body).hexdigest(), number, row, column,
                int(row['pop20']), denominator)
            if diagnostic:
                rejected.append(diagnostic)
    assert [(r['row'], r['column'], r['literal_token'], r['numerator'], r['denominator'])
            for r in rejected] == [(1136, 'afact', '0.669 ', 87018, 130062),
                                  (2428, 'afact', '0.5432 ', 84414, 155387),
                                  (2662, 'afact2', '0.1252', 108182, 863728)]
    assert all(r['cause'] == 'unknown' and r['disposition'] == 'rejected_assertion'
               for r in rejected)


@pytest.mark.parametrize('change', ['pin', 'row', 'state', 'puma22', 'county', 'token',
                                    'numerator', 'denominator', 'column'])
@pytest.mark.parametrize('cell', [(1136, 'afact', 87018, 130062),
                                  (2428, 'afact', 84414, 155387),
                                  (2662, 'afact2', 108182, 863728)])
def test_d7_rejects_each_changed_assertion_tuple(rules, change, cell):
    area, _ = rules
    body, rows = geocorr_rows()
    number, column, numerator, denominator = cell
    row = dict(rows[number - 3])
    pin = hashlib.sha256(body).hexdigest()
    if change == 'pin':
        pin = hashlib.sha256(body + b'\n').hexdigest()
    elif change == 'row':
        number += 1
    elif change in ('state', 'puma22', 'county'):
        row[change] = {'state': '99', 'puma22': '99999', 'county': '99999'}[change]
    elif change == 'token':
        value = row[column]
        row[column] = value.strip() if value.endswith(' ') else value + ' '
    elif change == 'numerator':
        numerator -= 1
    elif change == 'denominator':
        denominator += 1
    else:
        other_column = 'afact2' if column == 'afact' else 'afact'
        row[other_column] = row[column]
        column = other_column
    with pytest.raises(ValueError, match='rounding'):
        area.geocorr_rounding_assertion(pin, number, row, column, numerator, denominator)


def test_authentic_d8_rejected_literals_and_full_support(rules, public_files):
    _, code = rules
    rejected = code.rejected_occupation_html(public_files)
    assert [(r['row'], r['literal_code'], r['literal_token'], r['supported_code'])
            for r in rejected] == [(692, '790', '519160', '7905'),
                                  (789, '9051', '532031', '9050'),
                                  (843, '9820', '553010', '9825')]
    assert [r['title'] for r in rejected] == [
        'Computer Numerically Controlled Tool Operators And Programmers',
        'Flight Attendants',
        'Military Enlisted Tactical Operations and Air/Weapons Specialists and Crew Members']
    assert all(len(r['supporting_assertions']) == 6 for r in rejected)
    if hasattr(code, 'occupation_pair_validation'):
        assert code.occupation_pair_validation(public_files) == rejected


@pytest.mark.parametrize('change', ['pin', 'key', 'token', 'title', 'locator', 'other'])
def test_d8_freshly_repinned_html_mutations_rejected(rules, public_files, tmp_path, change):
    _, code = rules
    body = public_files['occupation_pairs_html'].read_text()
    if change == 'pin':
        body += '\n'
    elif change == 'key':
        body = body.replace('>790<', '>7901<')
    elif change == 'token':
        body = body.replace('>519160<', '>519161<')
    elif change == 'title':
        body = body.replace('Computer Numerically Controlled Tool Operators And Programmers',
                            'Wrong occupation title')
    elif change == 'locator':
        body = '<tr><td>extra row</td></tr>' + body
    else:
        body = body.replace('>111011<', '>111012<')
    assert body != public_files['occupation_pairs_html'].read_text()
    file = tmp_path / 'freshly-repinned.html'
    file.write_text(body)
    public_files['occupation_pairs_html'] = file
    with pytest.raises(ValueError, match='occupation|D8'):
        code.rejected_occupation_html(public_files)


@pytest.mark.parametrize('kind', ['ipums_occ_pairs', 'census_occupation_2018',
                                 'pums_occupation_2018', 'pums_annual_2024',
                                 'pums_five_year_2024'])
def test_d8_requires_every_exact_supporting_original(rules, public_files, tmp_path, kind):
    _, code = rules
    file = tmp_path / ('repinned-' + public_files[kind].name)
    file.write_bytes(public_files[kind].read_bytes() + b'\n')
    public_files[kind] = file
    with pytest.raises(ValueError, match='occupation.*pin'):
        code.rejected_occupation_html(public_files)
