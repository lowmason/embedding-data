import csv
import json
from unittest.mock import patch

import polars as pl
import pytest
from target_fixtures import prepared_tree, seed_inputs, submitted_edge_cases

from embedding_data import manifest, target_io

@pytest.fixture(autouse=True)
def implemented_software_boundary(monkeypatch):
    from target_fixtures import install_implemented_software_boundary

    install_implemented_software_boundary(monkeypatch)


def test_submission_identity_keeps_multiplicity_and_exact_strings(tmp_path):
    prepared = prepared_tree(tmp_path, batch_limit=2)
    source = pl.read_parquet(prepared.selected.canonical)
    index = pl.read_parquet(prepared.source_index)
    requests = pl.read_parquet(prepared.request_index)
    assert index.schema == {'source_row': pl.UInt64, 'request_id': pl.String}
    assert index['source_row'].to_list() == list(range(source.height))
    assert requests['n_source_rows'].sum() == source.height == index.height
    assert requests['request_id'].n_unique() == requests.height
    duplicate_rows = source.with_row_index('source_row').filter(pl.col('id').eq(23001))
    assert duplicate_rows.height == 2
    assert index.filter(pl.col('source_row').is_in(duplicate_rows['source_row'].to_list()))[
        'request_id'].n_unique() == 1
    assert prepared.inputs['batch_limit'] == 2
    assert prepared.inputs['fixture_inputs'] is True
    assert prepared.directory == tmp_path / 'derived/osha/assignment-inputs/requests'
    assert len(prepared.inputs['execution_commit']) == 40


def test_linkage_equivalent_delivered_strings_have_distinct_requests():
    from embedding_data.ita_assignment_prepare import request_id

    assert request_id(('1 Main St', 'Town', 'AL', '00001')) != request_id(
        ('1 MAIN ST', 'Town', 'AL', '00001'))
    assert request_id(('1 Main St ', 'Town', 'AL', '00001')) != request_id(
        ('1 Main St', 'Town', 'AL', '00001'))
    assert request_id(('a,b', 'c', '', '')) != request_id(('a', 'b,c', '', ''))


def test_submitted_edge_cases_preserve_source_and_csv(tmp_path):
    from embedding_data.ita_assignment_prepare import request_frames, validate_batch, write_batches

    source = submitted_edge_cases()
    before = source.clone()
    index, requests = request_frames(source.lazy())
    index, requests = index.collect(), requests.collect()
    assert source.equals(before)
    assert index['request_id'][0] == index['request_id'][1] == index['request_id'][6]
    assert requests.filter(pl.col('street').eq('1 Main St'))['zip'].item() == '12345'
    assert requests.filter(pl.col('street').eq('1 Main St '))['zip'].item() == '01234'
    assert requests.filter(pl.col('state').eq('PR')).height == 1
    records = write_batches(tmp_path, requests, 10_000)
    file = tmp_path / records[0]['path']
    assert 'Café'.encode() in file.read_bytes()
    with file.open(newline='', encoding='utf-8') as stream:
        rows = list(csv.reader(stream, escapechar='\\', doublequote=True, strict=True))
    assert rows == [list(row) for row in requests.select(
        'request_id', 'street', 'city', 'state', 'zip').iter_rows()]
    assert validate_batch(file, requests) == requests['request_id'].to_list()


def test_hash_collision_fails(monkeypatch):
    from embedding_data import ita_assignment_prepare as preparation

    monkeypatch.setattr(preparation, 'request_id', lambda fields: 'a' * 64)
    with pytest.raises(ValueError, match='collision'):
        preparation.request_frames(submitted_edge_cases().lazy())


def test_service_batch_boundary(tmp_path):
    from embedding_data.ita_assignment_prepare import request_frames, validate_batch, write_batches

    source = pl.DataFrame({'street_address': [str(i) for i in range(10_001)]}).with_columns(
        pl.lit('').alias('city'), pl.lit('').alias('state'), pl.lit('').alias('zip_code'))
    _, requests = request_frames(source.lazy())
    requests = requests.collect()
    records = write_batches(tmp_path, requests, 10_000)
    assert [r['rows'] for r in records] == [10_000, 1]
    assert [r['path'] for r in records] == ['requests/batch_00000.csv',
                                          'requests/batch_00001.csv']
    for start, record in zip((0, 10_000), records, strict=True):
        assert len(validate_batch(tmp_path / record['path'], requests.slice(start, 10_000))) \
            == record['rows']


def test_public_prepare_defaults_to_thousand_record_batches(tmp_path, monkeypatch):
    import target_fixtures
    from ita_fixtures import record

    from embedding_data import ita_assignment_prepare as preparation
    from embedding_data import ita_verification_run

    target_fixtures.forbid_external_access(monkeypatch)
    years = target_fixtures.golden_source_rows()
    years[2023] = [record(
        2023, id=str(23000 + number), establishment_id=str(23000 + number),
        naics_code='111111', naics_year='2022',
        street_address='Exact A' if number == 0 else f'{number} Café \\ "A", Floor 2',
        city='Fixture Town', state='AL', zip_code='00001') for number in range(1001)]
    years[2023].append(years[2023][0].copy())
    monkeypatch.setattr(target_fixtures, 'golden_source_rows', lambda: years)
    selected = seed_inputs(tmp_path)
    preparation.prepare(
        tmp_path, 'requests', 'fixture_codes', 'fixture_geography',
        codes_outputs_sha256=selected.provenance['codes']['outputs_sha256'],
        geography_outputs_sha256=selected.provenance['geography']['outputs_sha256'])
    prepared = preparation.check_preparation(tmp_path, 'requests')
    assert prepared.inputs['batch_limit'] == 1000
    assert [batch['rows'] for batch in prepared.inputs['batches']] == [1000, 1]
    assert [batch['path'] for batch in prepared.inputs['batches']] == [
        'requests/batch_00000.csv', 'requests/batch_00001.csv']
    assert prepared.inputs['source_years'] == list(range(2016, 2026))
    assert prepared.inputs['distinct_requests'] == 1001
    assert preparation.SERVICE_BATCH_LIMIT == ita_verification_run.BATCH_LIMIT == 10_000

    source = pl.read_parquet(prepared.selected.canonical)
    index = pl.read_parquet(prepared.source_index)
    requests = pl.read_parquet(prepared.request_index)
    assert source.height == prepared.inputs['source_rows'] == index.height == 1011
    assert index['source_row'].to_list() == list(range(source.height))
    assert index['request_id'].to_list() == [preparation.request_id(row) for row in
        source.select('street_address', 'city', 'state', 'zip_code').iter_rows()]
    assert requests['n_source_rows'].sum() == source.height
    assert requests.filter(pl.col('street').eq('Exact A'))['n_source_rows'].item() == 11
    csv_rows = []
    for start, file in zip((0, 1000), prepared.batches, strict=True):
        expected = requests.slice(start, 1000)
        with file.open(newline='', encoding='utf-8') as stream:
            rows = list(csv.reader(stream, escapechar='\\', doublequote=True, strict=True))
        assert rows == [list(row) for row in expected.select(
            'request_id', 'street', 'city', 'state', 'zip').iter_rows()]
        assert preparation.validate_batch(file, expected) == expected['request_id'].to_list()
        csv_rows.extend(rows)
    assert [row[0] for row in csv_rows] == sorted(requests['request_id'].to_list())


def test_verification_uses_frozen_batch_limit(tmp_path, monkeypatch):
    from embedding_data import ita_assignment_prepare as preparation

    target_limit = 10_000
    prepared = prepared_tree(tmp_path, batch_limit=target_limit)
    monkeypatch.setattr(preparation, 'BATCH_LIMIT', 1)
    checked = preparation.check_preparation(tmp_path, 'requests')
    assert checked.inputs['batch_limit'] == target_limit
    assert checked.batches == prepared.batches


@pytest.mark.parametrize('defect', ['empty', 'header', 'short', 'repeat', 'order', 'tuple', 'id'])
def test_batch_rejects_invalid_rows(tmp_path, defect):
    from embedding_data.ita_assignment_prepare import request_frames, validate_batch

    _, requests = request_frames(submitted_edge_cases().lazy())
    requests = requests.collect()
    rows = [list(row) for row in requests.select(
        'request_id', 'street', 'city', 'state', 'zip').iter_rows()]
    if defect == 'empty':
        rows = []
    elif defect == 'header':
        rows.insert(0, ['request_id', 'street', 'city', 'state', 'zip'])
    elif defect == 'short':
        rows[0].pop()
    elif defect == 'repeat':
        rows[1] = rows[0]
    elif defect == 'order':
        rows.reverse()
    elif defect == 'tuple':
        rows[0][1] += 'changed'
    else:
        rows[0][0] = rows[0][0].upper()
    file = tmp_path / 'batch.csv'
    with file.open('w', newline='', encoding='utf-8') as stream:
        csv.writer(stream).writerows(rows)
    with pytest.raises(ValueError):
        validate_batch(file, requests)


def repin_preparation(prepared):
    directory = prepared.directory
    inputs = json.loads((directory / 'inputs.json').read_text())
    inputs['source_index'] = target_io.file_record(prepared.source_index)
    inputs['request_index'] = target_io.file_record(prepared.request_index)
    for batch in inputs['batches']:
        batch.update(target_io.file_record(directory / batch['path']))
    target_io.write_json(directory / 'inputs.json', inputs)
    names = ['inputs.json', 'source_index.parquet', 'request_index.parquet',
             *[batch['path'] for batch in inputs['batches']]]
    target_io.write_json(directory / 'outputs.json', target_io.inventory(directory, names))


@pytest.mark.parametrize('defect', ['bytes', 'missing', 'extra', 'source_index', 'counts',
                                  'batch', 'version', 'years', 'software', 'lock', 'dependency'])
def test_corruption_refuses_check(tmp_path, defect):
    from embedding_data.ita_assignment_prepare import check_preparation

    prepared = prepared_tree(tmp_path)
    if defect == 'bytes':
        prepared.source_index.write_bytes(prepared.source_index.read_bytes() + b'changed')
    elif defect == 'missing':
        prepared.batches[0].unlink()
    elif defect == 'extra':
        (prepared.directory / 'extra').write_text('extra')
    elif defect == 'source_index':
        pl.read_parquet(prepared.source_index).reverse().write_parquet(prepared.source_index)
        repin_preparation(prepared)
    elif defect == 'counts':
        pl.read_parquet(prepared.request_index).with_columns(
            pl.col('n_source_rows').add(1)).write_parquet(prepared.request_index)
        repin_preparation(prepared)
    elif defect == 'batch':
        prepared.batches[0].write_text('')
        repin_preparation(prepared)
    else:
        inputs = prepared.inputs
        if defect == 'version':
            inputs['identity_version'] = 'future'
        elif defect == 'years':
            inputs['source_years'] = [2023]
        elif defect == 'software':
            inputs['software']['implementation']['ita_verification'] = '0' * 64
        elif defect == 'lock':
            inputs['software']['uv_lock_sha256'] = '0' * 64
        else:
            inputs['software']['dependencies']['polars'] = '0'
        target_io.write_json(prepared.directory / 'inputs.json', inputs)
        repin_preparation(prepared)
    with pytest.raises((ValueError, FileNotFoundError)):
        check_preparation(tmp_path, 'requests')


def test_source_changed_and_manifest_append(tmp_path):
    from datetime import UTC, datetime

    from embedding_data import paths
    from embedding_data.ita_assignment_prepare import check_preparation

    prepared = prepared_tree(tmp_path)
    extra = tmp_path / 'raw/unrelated.txt'
    extra.write_text('unrelated')
    manifest.append_entries(paths.manifest_path(tmp_path), [manifest.describe_file(
        extra, tmp_path / 'raw', retrieved_at=datetime(2026, 10, 14, tzinfo=UTC),
        client='fixture', client_version='1')])
    check_preparation(tmp_path, 'requests')
    prepared.selected.canonical.write_bytes(prepared.selected.canonical.read_bytes() + b'changed')
    with pytest.raises(ValueError):
        check_preparation(tmp_path, 'requests')


def test_estimator_change_allowed_frozen_dependency_change_rejected(tmp_path, monkeypatch):
    from embedding_data import ita_assignment_prepare as preparation

    prepared_tree(tmp_path)
    original = manifest.sha256_file

    def changed_hash(file):
        if file.name in ('cli.py', 'ita_area_mix.py'):
            return '0' * 64
        return original(file)

    monkeypatch.setattr(manifest, 'sha256_file', changed_hash)
    preparation.check_preparation(tmp_path, 'requests')
    monkeypatch.setattr(manifest, 'sha256_file', lambda file:
                        '0' * 64 if file.name == 'ita_verification.py' else original(file))
    with pytest.raises(ValueError, match='software'):
        preparation.check_preparation(tmp_path, 'requests')


def test_preparation_never_rebuilds_or_uses_http_and_is_exclusive(tmp_path):
    from embedding_data import ita_assignment_prepare as preparation

    selected = seed_inputs(tmp_path)
    kwargs = {family + '_outputs_sha256': selected.provenance[family]['outputs_sha256']
              for family in ('codes', 'geography')}
    with patch('embedding_data.ita_summary.build_summary_table', side_effect=AssertionError), \
            patch('httpx.Client', side_effect=AssertionError):
        preparation.prepare(tmp_path, 'requests', 'fixture_codes', 'fixture_geography', **kwargs)
        preparation.check_preparation(tmp_path, 'requests')
        with pytest.raises(ValueError, match='exists'):
            preparation.prepare(
                tmp_path, 'requests', 'fixture_codes', 'fixture_geography', **kwargs)


@pytest.mark.parametrize('defect', ['software', 'selected', 'occupied'])
def test_publication_rechecks_inputs_and_leaves_failed_staging(tmp_path, monkeypatch, defect):
    from embedding_data import ita_assignment_prepare as preparation

    selected = seed_inputs(tmp_path)
    kwargs = {family + '_outputs_sha256': selected.provenance[family]['outputs_sha256']
              for family in ('codes', 'geography')}
    original_check = preparation._check_directory

    def change_after_validation(*args):
        result = original_check(*args)
        if defect == 'software':
            monkeypatch.setattr(preparation, 'software_contract', lambda: {})
        elif defect == 'selected':
            selected.summary.write_bytes(selected.summary.read_bytes() + b'changed')
        else:
            final = tmp_path / 'derived/osha/assignment-inputs/requests'
            final.mkdir()
            (final / 'occupied').write_text('preserve')
        return result

    monkeypatch.setattr(preparation, '_check_directory', change_after_validation)
    with pytest.raises(ValueError):
        preparation.prepare(tmp_path, 'requests', 'fixture_codes', 'fixture_geography', **kwargs)
    root = tmp_path / 'derived/osha/assignment-inputs'
    assert (root / 'requests.part/inputs.json').exists()
    if defect == 'occupied':
        assert (root / 'requests/occupied').read_text() == 'preserve'
    else:
        assert not (root / 'requests').exists()


def test_failed_staging_and_unsafe_ids_are_rejected(tmp_path):
    from embedding_data.ita_assignment_prepare import check_preparation, prepare

    staging = tmp_path / 'derived/osha/assignment-inputs/requests.part'
    staging.mkdir(parents=True)
    with pytest.raises(ValueError, match='exists'):
        prepare(tmp_path, 'requests', 'fixture_codes', 'fixture_geography')
    with pytest.raises(ValueError, match='unsafe'):
        check_preparation(tmp_path, '../requests')


@pytest.mark.parametrize('limit', [0, 10_001, True])
def test_frozen_batch_limit_cannot_exceed_service_boundary(tmp_path, limit):
    from embedding_data.ita_assignment_prepare import check_preparation

    prepared = prepared_tree(tmp_path)
    prepared.inputs['batch_limit'] = limit
    target_io.write_json(prepared.directory / 'inputs.json', prepared.inputs)
    repin_preparation(prepared)
    with pytest.raises(ValueError, match='batch limit'):
        check_preparation(tmp_path, 'requests')


@pytest.mark.parametrize('street,city', [
    ('A\\B\\"C"', 'Town'),
    ('A\\B', 'Town\\Center'),
    ('Café, "A"\\B', 'Town'),
    ('Line 1\nLine 2\\', 'Town\r\nCenter'),
    ('Plain, "quoted"', 'Café'),
    (None, None),
])
def test_census_escape_reader_receives_exact_submitted_strings(tmp_path, street, city):
    import hashlib
    import io

    from embedding_data import ita_assignment_prepare as preparation

    source = pl.DataFrame({'street_address': [street, street], 'city': [city, city],
                          'state': [None, None], 'zip_code': [None, None]},
                         schema={name: pl.String for name in
                                 ['street_address', 'city', 'state', 'zip_code']})
    before = source.clone()
    fields = [street or '', city or '', '', '']
    payload = json.dumps(fields, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    identifier = hashlib.sha256(b'ita-request-v1\0' + payload).hexdigest()
    index, requests = preparation.request_frames(source.lazy())
    requests = requests.collect()
    assert index.collect().to_dicts() == [
        {'source_row': 0, 'request_id': identifier},
        {'source_row': 1, 'request_id': identifier}]
    assert requests['n_source_rows'].to_list() == [2]
    records = preparation.write_batches(tmp_path, requests, 1000)
    file = tmp_path / records[0]['path']
    # External wire contract is independent of the production dialect constant.
    with file.open(newline='', encoding='utf-8') as stream:
        delivered = list(csv.reader(stream, escapechar='\\', doublequote=True, strict=True))
    assert delivered == [[identifier, *fields]]
    original = io.StringIO(newline='')
    csv.writer(original).writerow([identifier, *fields])
    assert file.read_bytes() == original.getvalue().encode().replace(b'\\', b'\\\\')
    assert preparation.validate_batch(file, requests) == [identifier]
    assert source.equals(before)


@pytest.mark.parametrize('street', ['A\\B', 'A\\B\\"C"'])
def test_validator_rejects_unescaped_backslashes_contradicting_id(tmp_path, street):
    from embedding_data import ita_assignment_prepare as preparation

    source = pl.DataFrame({'street_address': [street], 'city': ['Town'],
                          'state': ['AL'], 'zip_code': ['00001']})
    _, requests = preparation.request_frames(source.lazy())
    requests = requests.collect()
    file = tmp_path / 'old.csv'
    with file.open('w', newline='', encoding='utf-8') as stream:
        csv.writer(stream).writerows(requests.select('request_id', *preparation.SUBMITTED).rows())
    with pytest.raises((ValueError, csv.Error)):
        preparation.validate_batch(file, requests)
